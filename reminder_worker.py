"""
CareCircle Proactive Reminder Worker Process.
Periodically executed (e.g. every 5 minutes via cron or Task Scheduler).
Dispatches email reminders for:
  1. Upcoming medication doses (with configured lead-time window)
  2. Missed medication alerts (after configured grace period)
  3. Upcoming doctor appointments (~24 hours in advance)

Features:
  - Respects per-user NotificationPreference settings
  - Prevents duplicate notification dispatches via unique key tracking
  - Graceful handling when SMTP credentials are not configured
  - Clear operational logging
"""

import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

from app import app
from models import (
    db, User, Patient, Medication, DoseLog, Appointment, Membership,
    NotificationPreference, ReminderSent
)

def is_smtp_configured():
    required = ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM']
    return all(os.getenv(k) for k in required)

def send_email(to_email, subject, body_text):
    """Safely deliver email via SMTP with starttls and timeout protection."""
    if not is_smtp_configured():
        print(f"[SMTP Notice] Simulated delivery to {to_email}: '{subject}'")
        return True

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = os.environ['SMTP_FROM']
        msg['To'] = to_email
        msg.set_content(body_text)

        host = os.environ['SMTP_HOST']
        port = int(os.getenv('SMTP_PORT', '587'))
        user = os.environ['SMTP_USER']
        password = os.environ['SMTP_PASSWORD']

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)

        print(f"[SMTP Success] Sent '{subject}' to {to_email}")
        return True
    except Exception as e:
        print(f"[SMTP Error] Failed to send email to {to_email}: {e}")
        return False

def get_circle_users_with_preferences(patient_id):
    """
    Retrieve all authorized care circle users for a patient along with
    their notification preferences.
    """
    memberships = Membership.query.filter_by(patient_id=patient_id).all()
    user_ids = {m.user_id for m in memberships}

    # Include the elder patient themselves
    patient = db.session.get(Patient, patient_id)
    if patient and patient.linked_user:
        for u in patient.linked_user:
            user_ids.add(u.id)

    users = User.query.filter(User.id.in_(user_ids)).all()
    results = []
    for u in users:
        pref = NotificationPreference.query.filter_by(user_id=u.id).first()
        results.append((u, pref))
    return results

def run_reminder_cycle():
    with app.app_context():
        now = datetime.now()
        today_iso = now.strftime('%Y-%m-%d')
        notifications_sent = 0

        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Starting CareCircle proactive reminder cycle...")

        if not is_smtp_configured():
            print("[Info] SMTP credentials not configured in .env. Running in dry-run simulation mode.")

        # ====================================================================
        # 1. Upcoming and Missed Medication Reminders
        # ====================================================================
        active_medications = Medication.query.filter_by(active=True).all()

        for med in active_medications:
            patient = db.session.get(Patient, med.patient_id)
            if not patient:
                continue

            circle_recipients = get_circle_users_with_preferences(patient.id)

            for hhmm in [x.strip() for x in med.times.split(',') if x.strip()]:
                try:
                    sched_dt = datetime.strptime(f"{today_iso} {hhmm}", "%Y-%m-%d %H:%M")
                except ValueError:
                    continue

                diff_minutes = (sched_dt - now).total_seconds() / 60.0
                sched_key_base = f"{today_iso}T{hhmm}"

                # Check if dose has already been marked as Taken or Skipped
                dose_log = DoseLog.query.filter_by(medication_id=med.id, scheduled_for=sched_key_base).first()
                if dose_log and dose_log.status in ('Taken', 'Skipped'):
                    continue

                # Case A: Upcoming Dose (Within lead window: e.g. 0 to 15 minutes before)
                if 0 <= diff_minutes <= 15:
                    for user, pref in circle_recipients:
                        if pref and not pref.email_upcoming_dose:
                            continue

                        remind_key = f"dose:upcoming:{med.id}:{sched_key_base}:{user.id}"
                        if ReminderSent.query.filter_by(reminder_key=remind_key).first():
                            continue

                        subject = f"CareCircle Reminder: {med.name} due for {patient.name}"
                        body = (
                            f"Hello {user.name.split()[0]},\n\n"
                            f"This is an upcoming medication reminder for {patient.name}.\n\n"
                            f"Medication: {med.name}\n"
                            f"Dosage: {med.dosage or 'As listed in care plan'}\n"
                            f"Scheduled Time: {sched_dt.strftime('%I:%M %p')}\n"
                            f"Instructions: {med.instructions or 'Follow clinician directions.'}\n\n"
                            f"Log into CareCircle to record when the dose is taken:\n"
                            f"https://carecircle.onrender.com/dashboard\n\n"
                            f"CareCircle is a coordination assistant, not a certified medical device."
                        )

                        if send_email(user.email, subject, body):
                            db.session.add(ReminderSent(reminder_key=remind_key))
                            notifications_sent += 1

                # Case B: Possibly Missed Dose (Grace period: 30 to 90 minutes past due)
                elif -90 <= diff_minutes <= -30:
                    for user, pref in circle_recipients:
                        if pref and not pref.email_missed_dose:
                            continue

                        remind_key = f"dose:missed:{med.id}:{sched_key_base}:{user.id}"
                        if ReminderSent.query.filter_by(reminder_key=remind_key).first():
                            continue

                        subject = f"CareCircle Alert: Unconfirmed dose of {med.name} for {patient.name}"
                        body = (
                            f"Hello {user.name.split()[0]},\n\n"
                            f"The scheduled dose of {med.name} for {patient.name} at {sched_dt.strftime('%I:%M %p')} has not yet been confirmed.\n\n"
                            f"Medicine: {med.name} ({med.dosage or 'Prescribed dose'})\n"
                            f"Scheduled Time: {sched_dt.strftime('%I:%M %p')}\n\n"
                            f"Please check in with {patient.name} and record the dose status in CareCircle:\n"
                            f"https://carecircle.onrender.com/dashboard\n\n"
                            f"Note: Never double doses without clinician advice."
                        )

                        if send_email(user.email, subject, body):
                            db.session.add(ReminderSent(reminder_key=remind_key))
                            notifications_sent += 1

        # ====================================================================
        # 2. Upcoming Doctor Appointments (~24 hours in advance)
        # ====================================================================
        upcoming_appointments = Appointment.query.filter_by(status='Scheduled').all()

        for appt in upcoming_appointments:
            try:
                appt_dt = datetime.fromisoformat(appt.appt_at)
            except ValueError:
                continue

            time_until = appt_dt - now
            # Window: 23 hours to 24 hours 30 mins
            if timedelta(hours=23) <= time_until <= timedelta(hours=24, minutes=30):
                patient = db.session.get(Patient, appt.patient_id)
                if not patient:
                    continue

                circle_recipients = get_circle_users_with_preferences(patient.id)

                for user, pref in circle_recipients:
                    if pref and not pref.email_appointments:
                        continue

                    remind_key = f"appt:reminder:{appt.id}:{user.id}"
                    if ReminderSent.query.filter_by(reminder_key=remind_key).first():
                        continue

                    subject = f"CareCircle Appointment Alert: {patient.name} has a visit tomorrow"
                    body = (
                        f"Hello {user.name.split()[0]},\n\n"
                        f"Reminder: {patient.name} has an upcoming medical appointment with {appt.doctor} tomorrow.\n\n"
                        f"Date & Time: {appt_dt.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
                        f"Specialty: {appt.specialty or 'Clinical visit'}\n"
                        f"Location: {appt.location or 'Clinic'}\n"
                        f"Reason: {appt.reason or 'Consultation'}\n"
                        f"Preparation Notes: {appt.notes or 'None specified'}\n\n"
                        f"Please ensure transportation and required medical reports are arranged."
                    )

                    if send_email(user.email, subject, body):
                        db.session.add(ReminderSent(reminder_key=remind_key))
                        notifications_sent += 1

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[DB Error] Failed to commit reminder cycle records: {e}")

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Reminder cycle complete. Notifications processed: {notifications_sent}")

if __name__ == '__main__':
    run_reminder_cycle()
