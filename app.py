"""
CareCircle — Intelligent Elderly Care & Medication Management Platform
PromptWars × Catalyst Challenge
Full-stack Python Flask + SQLAlchemy Healthcare Platform
"""

import os
import secrets
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, abort, send_from_directory, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db, User, Patient, Medication, DoseLog, Appointment, Membership,
    CareCircleInvitation, CareTask, MedicalDocument, HealthJournalEntry,
    Notification, NotificationPreference, ActivityLog,
    log_activity, create_notification, notify_circle
)
from seed import seed_database
from services.security import (
    generate_csrf_token, validate_csrf, get_current_user,
    get_patient_for_user, can_edit_patient, can_manage_circle,
    login_required, save_secure_upload
)
from services.intelligence import (
    get_adherence_metrics, generate_care_insights, generate_weekly_care_summary
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'carecircle-catalyst-secret-key-32chars-min!'),
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'carecircle.db')),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=12 * 1024 * 1024, # 12 MB max upload
    UPLOAD_FOLDER=UPLOAD_FOLDER
)

db.init_app(app)

# CSRF validation before each request
@app.before_request
def csrf_protect():
    # Only validate on mutating requests, exempting any pure GET/HEAD/OPTIONS
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        validate_csrf()

# Global context processors for templates
@app.context_processor
def inject_globals():
    u = get_current_user()
    p = get_patient_for_user(u) if u else None
    can_m = can_edit_patient(u, p.id) if (u and p) else False
    
    unread_count = 0
    if u:
        try:
            unread_count = Notification.query.filter_by(user_id=u.id, is_read=False).count()
        except Exception:
            unread_count = 0

    return {
        'user': u,
        'patient': p,
        'can_manage': can_m,
        'can_edit': can_m,
        'now': datetime.now,
        'today_date': date.today(),
        'csrf_token': generate_csrf_token,
        'unread_notifs_count': unread_count
    }

# ============================================================================
# Public & Authentication Routes
# ============================================================================

@app.route('/')
def index():
    """Landing page for unauthenticated visitors, dashboard for active users."""
    if get_current_user():
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session.clear()
            session['user_id'] = user.id
            generate_csrf_token()
            flash(f"Welcome back, {user.name.split()[0]}. Secure care space loaded.", 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email address or password. Please check your credentials.', 'danger')

    return render_template('login.html')

@app.route('/quick-demo-login', methods=['POST'])
def quick_demo_login():
    """One-click instant login button handler from public landing page."""
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()
    if user:
        session.clear()
        session['user_id'] = user.id
        generate_csrf_token()
        flash(f"Signed in as {user.name} ({user.role.title()}).", 'success')
        return redirect(url_for('dashboard'))
    flash("Demo account not found. Initializing demonstration database...", 'warning')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if get_current_user():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'elder')
        invite_code = request.form.get('invite_code', '').strip().upper()

        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'danger')
            return render_template('register.html')

        if role not in ('elder', 'caregiver', 'family'):
            flash('Please choose a valid care role.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please sign in.', 'danger')
            return render_template('register.html')

        patient_id = None
        patient = None

        if role == 'elder':
            # Create elder's health profile
            patient = Patient(name=name)
            db.session.add(patient)
            db.session.flush()
            patient_id = patient.id

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role,
            patient_id=patient_id
        )
        db.session.add(new_user)
        db.session.flush()

        # Create default notification preference
        pref = NotificationPreference(user_id=new_user.id)
        db.session.add(pref)

        # Check for invite code redemption
        if invite_code:
            inv = CareCircleInvitation.query.filter_by(
                invite_code=invite_code,
                status='pending'
            ).first()

            if inv and inv.expires_at >= datetime.utcnow():
                inv.status = 'accepted'
                membership = Membership(
                    patient_id=inv.patient_id,
                    user_id=new_user.id,
                    permission=inv.permission
                )
                db.session.add(membership)
                log_activity(
                    inv.patient_id, new_user.id, 'member_joined',
                    f"{new_user.name} joined the care circle using invite passcode {invite_code}."
                )
                flash(f"Successfully joined {inv.patient.name}'s care circle as {inv.permission.title()}!", 'success')

        db.session.commit()
        session.clear()
        session['user_id'] = new_user.id
        generate_csrf_token()

        flash(f"Account created successfully. Welcome to CareCircle, {name.split()[0]}!", 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out of your secure care space.', 'info')
    return redirect(url_for('login'))

# ============================================================================
# Main Dashboard
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    patient = get_patient_for_user(user)

    if not patient:
        return render_template('empty.html', user=user)

    now = datetime.now()
    today_str = now.strftime('%A, %B %d, %Y')
    today_iso = date.today().isoformat()

    # Time of day greeting
    if now.hour < 12:
        greeting = 'morning'
    elif now.hour < 17:
        greeting = 'afternoon'
    else:
        greeting = 'evening'

    # Active medications
    active_meds = Medication.query.filter_by(patient_id=patient.id, active=True).all()
    
    # Scheduled doses for today
    today_schedule = []
    overdue_doses = []
    today_logs = DoseLog.query.filter(
        DoseLog.patient_id == patient.id,
        DoseLog.scheduled_for.like(f"{today_iso}%")
    ).all()
    log_map = {l.scheduled_for: l for l in today_logs}

    taken_count = 0
    total_doses_today = 0

    for med in active_meds:
        for t in [x.strip() for x in med.times.split(',') if x.strip()]:
            sched_key = f"{today_iso}T{t}"
            total_doses_today += 1
            existing_log = log_map.get(sched_key)

            # Check overdue: past time by > 30 mins and not yet taken/skipped
            is_overdue = False
            try:
                sched_dt = datetime.strptime(f"{today_iso} {t}", "%Y-%m-%d %H:%M")
                if (now - sched_dt).total_seconds() > 1800 and (not existing_log or existing_log.status not in ('Taken', 'Skipped')):
                    is_overdue = True
            except Exception:
                pass

            status = existing_log.status if existing_log else ('Missed' if is_overdue else 'Scheduled')
            if status == 'Taken':
                taken_count += 1

            sched_item = {
                'med': med,
                'time_str': t,
                'time_formatted': datetime.strptime(t, '%H:%M').strftime('%I:%M %p') if len(t) == 5 else t,
                'scheduled_for': sched_key,
                'status': status,
                'log': existing_log
            }
            today_schedule.append(sched_item)

            if is_overdue and status != 'Taken':
                overdue_doses.append(sched_item)

    # Sort schedule by time
    today_schedule.sort(key=lambda x: x['time_str'])

    adherence_pct = round((taken_count / total_doses_today * 100), 1) if total_doses_today > 0 else 100.0

    # Upcoming appointments (next 14 days)
    upcoming_appts = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Scheduled',
        Appointment.appt_at >= now.strftime('%Y-%m-%dT%H:%M')
    ).order_by(Appointment.appt_at).limit(4).all()

    # Care tasks
    priority_tasks = CareTask.query.filter(
        CareTask.patient_id == patient.id,
        CareTask.status.in_(['Pending', 'In Progress'])
    ).order_by(CareTask.priority.desc(), CareTask.due_date).limit(4).all()
    pending_tasks_count = CareTask.query.filter_by(patient_id=patient.id, status='Pending').count()

    # Circle members
    circle_members = Membership.query.filter_by(patient_id=patient.id).all()

    # Recent activity logs (audit trail)
    recent_activities = ActivityLog.query.filter_by(patient_id=patient.id).order_by(ActivityLog.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        patient=patient,
        today_str=today_str,
        greeting_time=greeting,
        today_schedule=today_schedule,
        today_taken_doses=taken_count,
        today_total_doses=total_doses_today,
        today_adherence_rate=adherence_pct,
        active_meds_count=len(active_meds),
        upcoming_appts=upcoming_appts,
        priority_tasks=priority_tasks,
        pending_tasks_count=pending_tasks_count,
        circle_members=circle_members,
        recent_activities=recent_activities,
        overdue_doses=overdue_doses
    )

# ============================================================================
# Advanced Medication Management
# ============================================================================

@app.route('/medications', methods=['GET', 'POST'])
@login_required
def medications():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_edit_patient(user, patient.id):
            abort(403)

        name = request.form.get('name', '').strip()
        times_raw = request.form.get('times', '').strip()

        if not name or not times_raw:
            flash('Medication name and at least one reminder time are required.', 'danger')
            return redirect(url_for('medications'))

        # Clean and sort times
        times_clean = ', '.join(sorted([t.strip() for t in times_raw.split(',') if t.strip()]))

        med = Medication(
            patient_id=patient.id,
            name=name,
            dosage=request.form.get('dosage', '').strip(),
            frequency=request.form.get('frequency', 'Daily'),
            instructions=request.form.get('instructions', '').strip(),
            times=times_clean,
            start_date=request.form.get('start_date') or date.today().isoformat(),
            end_date=request.form.get('end_date') or None,
            prescribed_by=request.form.get('prescribed_by', '').strip(),
            refill_remaining=int(request.form.get('refill_remaining') or 30),
            notes=request.form.get('notes', '').strip(),
            created_by=user.id,
            active=True
        )
        db.session.add(med)
        db.session.commit()

        log_activity(patient.id, user.id, 'medication_added', f"{user.name} added medication schedule for {med.name} ({med.dosage or 'dosage'}).")
        notify_circle(patient.id, f"Medication Added: {med.name}", f"A new schedule for {med.name} was added by {user.name}.", category='dose', action_url='/medications', exclude_user_id=user.id)

        flash(f"Medication schedule for {name} saved successfully.", 'success')
        return redirect(url_for('medications'))

    show_inactive = request.args.get('show_inactive') == '1'
    active_meds = Medication.query.filter_by(patient_id=patient.id, active=True).order_by(Medication.name).all()
    inactive_meds = Medication.query.filter_by(patient_id=patient.id, active=False).order_by(Medication.name).all()

    return render_template(
        'medications.html',
        patient=patient,
        active_meds=active_meds,
        inactive_meds=inactive_meds,
        show_discontinued=show_inactive
    )

@app.route('/medications/edit/<int:med_id>', methods=['POST'])
@login_required
def edit_medication(med_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    med = db.session.get(Medication, med_id)

    if not patient or not med or med.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    med.name = request.form.get('name', med.name).strip()
    med.dosage = request.form.get('dosage', med.dosage).strip()
    med.frequency = request.form.get('frequency', med.frequency)
    times_raw = request.form.get('times', med.times).strip()
    med.times = ', '.join(sorted([t.strip() for t in times_raw.split(',') if t.strip()]))
    med.instructions = request.form.get('instructions', med.instructions).strip()
    med.prescribed_by = request.form.get('prescribed_by', med.prescribed_by).strip()
    med.refill_remaining = int(request.form.get('refill_remaining') or med.refill_remaining)
    med.notes = request.form.get('notes', med.notes).strip()

    db.session.commit()
    log_activity(patient.id, user.id, 'medication_updated', f"{user.name} updated the care plan for {med.name}.")
    flash(f"Updated schedule for {med.name}.", 'success')
    return redirect(url_for('medications'))

@app.route('/medications/toggle/<int:med_id>', methods=['POST'])
@login_required
def toggle_med_status(med_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    med = db.session.get(Medication, med_id)

    if not patient or not med or med.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    med.active = not med.active
    action = 'reactivated' if med.active else 'discontinued'
    db.session.commit()

    log_activity(patient.id, user.id, f'medication_{action}', f"{user.name} {action} {med.name}.")
    flash(f"{med.name} was {action}.", 'info')
    return redirect(url_for('medications', show_inactive=0 if med.active else 1))

@app.route('/dose/<int:med_id>/<status>', methods=['POST'])
@login_required
def dose(med_id, status):
    """Record or update dose confirmation status with audit tracking."""
    user = get_current_user()
    patient = get_patient_for_user(user)
    med = db.session.get(Medication, med_id)

    if not patient or not med or med.patient_id != patient.id:
        abort(403)

    if not can_edit_patient(user, patient.id):
        abort(403)

    if status not in ('Taken', 'Skipped', 'Missed'):
        abort(400, description="Invalid dose status.")

    sched_time = request.form.get('scheduled_for')
    if not sched_time:
        sched_time = datetime.now().strftime('%Y-%m-%dT%H:%M')

    note = request.form.get('note', '').strip()
    now_dt = datetime.utcnow()

    # Prevent duplicates & record audit changes
    existing_log = DoseLog.query.filter_by(medication_id=med.id, scheduled_for=sched_time).first()
    if existing_log:
        old_status = existing_log.status
        existing_log.status = status
        existing_log.logged_by = user.id
        existing_log.updated_at = now_dt
        if status == 'Taken':
            existing_log.confirmed_at = now_dt
        if note:
            existing_log.note = note
        existing_log.audit_history = f"{existing_log.audit_history or ''} Changed from {old_status} to {status} by {user.name} at {now_dt.isoformat()}."
    else:
        new_log = DoseLog(
            medication_id=med.id,
            patient_id=patient.id,
            scheduled_for=sched_time,
            status=status,
            logged_by=user.id,
            logged_at=now_dt,
            confirmed_at=now_dt if status == 'Taken' else None,
            note=note,
            audit_history=f"Created as {status} by {user.name} at {now_dt.isoformat()}."
        )
        db.session.add(new_log)

    # Decrement refills if taken
    if status == 'Taken' and med.refill_remaining and med.refill_remaining > 0:
        med.refill_remaining -= 1

    db.session.commit()

    log_desc = f"{user.name} recorded {med.name} dose ({sched_time.split('T')[1]}) as {status}."
    if note:
        log_desc += f" Note: '{note}'"
    log_activity(patient.id, user.id, f'dose_{status.lower()}', log_desc)

    flash(f"{med.name}: marked {status.lower()}.", 'success')
    return redirect(request.referrer or url_for('dashboard'))

# ============================================================================
# Medication & Care Calendar
# ============================================================================

@app.route('/calendar')
@login_required
def calendar():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    try:
        week_offset = int(request.args.get('week_offset', 0))
    except ValueError:
        week_offset = 0

    view_mode = request.args.get('view', 'week')
    today = date.today()
    # Compute start of the displayed week (Monday)
    start_of_current_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_current_week + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    week_range_label = f"{start_of_week.strftime('%B %d')} – {end_of_week.strftime('%B %d, %Y')}"

    # Query active medications
    active_meds = Medication.query.filter_by(patient_id=patient.id, active=True).all()

    # Query logs in the week window
    logs = DoseLog.query.filter(
        DoseLog.patient_id == patient.id,
        DoseLog.scheduled_for >= start_of_week.isoformat(),
        DoseLog.scheduled_for <= end_of_week.isoformat() + "T23:59"
    ).all()
    log_lookup = {l.scheduled_for: l for l in logs}

    # Query appointments in the week window
    appts = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appt_at >= start_of_week.isoformat(),
        Appointment.appt_at <= end_of_week.isoformat() + "T23:59"
    ).all()

    calendar_days = []
    now = datetime.now()

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_iso = current_day.isoformat()
        is_today = (current_day == today)

        # Collect scheduled doses for this day
        day_doses = []
        for med in active_meds:
            for t in [x.strip() for x in med.times.split(',') if x.strip()]:
                sched_key = f"{day_iso}T{t}"
                existing_log = log_lookup.get(sched_key)

                # Check if past due
                status = 'Scheduled'
                if existing_log:
                    status = existing_log.status
                else:
                    try:
                        dose_dt = datetime.strptime(f"{day_iso} {t}", "%Y-%m-%d %H:%M")
                        if (now - dose_dt).total_seconds() > 1800:
                            status = 'Missed'
                    except Exception:
                        pass

                day_doses.append({
                    'med_id': med.id,
                    'med_name': med.name,
                    'dosage': med.dosage,
                    'time_str': t,
                    'scheduled_for': sched_key,
                    'status': status
                })

        day_doses.sort(key=lambda x: x['time_str'])

        # Appointments on this day
        day_appts = [a for a in appts if a.appt_at.startswith(day_iso)]

        calendar_days.append({
            'date': day_iso,
            'day_name': current_day.strftime('%a'),
            'day_number': current_day.strftime('%d'),
            'full_date_label': current_day.strftime('%A, %B %d, %Y'),
            'is_today': is_today,
            'doses': day_doses,
            'appointments': day_appts
        })

    return render_template(
        'calendar.html',
        patient=patient,
        calendar_days=calendar_days,
        week_offset=week_offset,
        week_range_label=week_range_label,
        view_mode=view_mode
    )

# ============================================================================
# Adherence Analytics & Care Intelligence
# ============================================================================

@app.route('/analytics')
@login_required
def analytics():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    metrics_7d = get_adherence_metrics(patient.id, days=7)
    care_insights = generate_care_insights(patient.id)
    weekly_summary = generate_weekly_care_summary(patient.id)

    # Prepare Chart.js arrays
    chart_trend_labels = [d['label'] for d in metrics_7d['daily_stats']]
    chart_trend_values = [d['rate'] for d in metrics_7d['daily_stats']]

    return render_template(
        'analytics.html',
        patient=patient,
        metrics_7d=metrics_7d,
        care_insights=care_insights,
        weekly_summary=weekly_summary,
        chart_trend_labels=chart_trend_labels,
        chart_trend_values=chart_trend_values
    )

# ============================================================================
# Appointment Management
# ============================================================================

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_edit_patient(user, patient.id):
            abort(403)

        doctor = request.form.get('doctor', '').strip()
        appt_at = request.form.get('appt_at', '').strip()

        if not doctor or not appt_at:
            flash('Doctor name and appointment date/time are required.', 'danger')
            return redirect(url_for('appointments'))

        appt = Appointment(
            patient_id=patient.id,
            doctor=doctor,
            specialty=request.form.get('specialty', '').strip(),
            location=request.form.get('location', '').strip(),
            appt_at=appt_at,
            reason=request.form.get('reason', '').strip(),
            notes=request.form.get('notes', '').strip(),
            created_by=user.id,
            status='Scheduled'
        )
        db.session.add(appt)
        db.session.commit()

        log_activity(patient.id, user.id, 'appointment_scheduled', f"{user.name} scheduled appointment with {doctor} on {appt_at.replace('T', ' at ')}.")
        notify_circle(patient.id, f"Appointment Scheduled: {doctor}", f"Consultation scheduled for {patient.name} on {appt_at.replace('T', ' at ')}.", category='appointment', action_url='/appointments', exclude_user_id=user.id)

        flash(f"Appointment with {doctor} scheduled.", 'success')
        return redirect(url_for('appointments'))

    show_past = request.args.get('past') == '1'
    now_iso = datetime.now().strftime('%Y-%m-%dT%H:%M')

    upcoming_list = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status == 'Scheduled',
        Appointment.appt_at >= now_iso
    ).order_by(Appointment.appt_at).all()

    past_list = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        ((Appointment.appt_at < now_iso) | (Appointment.status.in_(['Completed', 'Cancelled'])))
    ).order_by(Appointment.appt_at.desc()).all()

    return render_template(
        'appointments.html',
        patient=patient,
        upcoming_list=upcoming_list,
        past_list=past_list,
        show_past=show_past
    )

@app.route('/appointments/edit/<int:appt_id>', methods=['POST'])
@login_required
def edit_appointment(appt_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    appt = db.session.get(Appointment, appt_id)

    if not patient or not appt or appt.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    appt.doctor = request.form.get('doctor', appt.doctor).strip()
    appt.specialty = request.form.get('specialty', appt.specialty).strip()
    appt.location = request.form.get('location', appt.location).strip()
    appt.appt_at = request.form.get('appt_at', appt.appt_at).strip()
    appt.reason = request.form.get('reason', appt.reason).strip()
    appt.notes = request.form.get('notes', appt.notes).strip()

    db.session.commit()
    log_activity(patient.id, user.id, 'appointment_updated', f"{user.name} updated the appointment details with {appt.doctor}.")
    flash(f"Appointment with {appt.doctor} updated.", 'success')
    return redirect(url_for('appointments'))

@app.route('/appointments/status/<int:appt_id>/<status>', methods=['POST'])
@login_required
def update_appt_status(appt_id, status):
    user = get_current_user()
    patient = get_patient_for_user(user)
    appt = db.session.get(Appointment, appt_id)

    if not patient or not appt or appt.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    if status not in ('Completed', 'Cancelled', 'Scheduled'):
        abort(400)

    appt.status = status
    db.session.commit()

    log_activity(patient.id, user.id, f'appointment_{status.lower()}', f"{user.name} marked appointment with {appt.doctor} as {status}.")
    flash(f"Appointment with {appt.doctor} marked {status}.", 'info')
    return redirect(url_for('appointments'))

# ============================================================================
# Health Records & Document Vault
# ============================================================================

@app.route('/records', methods=['GET', 'POST'])
@login_required
def records():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_edit_patient(user, patient.id):
            abort(403)

        patient.name = request.form.get('name', patient.name).strip()
        patient.dob = request.form.get('dob', patient.dob)
        patient.blood_group = request.form.get('blood_group', patient.blood_group)
        patient.allergies = request.form.get('allergies', patient.allergies).strip()
        patient.emergency_contact = request.form.get('emergency_contact', patient.emergency_contact)
        patient.emergency_contact_name = request.form.get('emergency_contact_name', patient.emergency_contact_name)
        patient.emergency_contact_relation = request.form.get('emergency_contact_relation', patient.emergency_contact_relation)
        patient.primary_physician = request.form.get('primary_physician', patient.primary_physician)
        patient.notes = request.form.get('notes', patient.notes)

        db.session.commit()
        log_activity(patient.id, user.id, 'profile_updated', f"{user.name} updated the clinical health profile for {patient.name}.")
        flash("Patient health profile saved successfully.", 'success')
        return redirect(url_for('records'))

    documents = MedicalDocument.query.filter_by(patient_id=patient.id).order_by(MedicalDocument.created_at.desc()).all()
    return render_template('records.html', patient=patient, documents=documents)

@app.route('/vault/upload', methods=['POST'])
@login_required
def upload_document():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient or not can_edit_patient(user, patient.id):
        abort(403)

    file_storage = request.files.get('document_file')
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Medical Report')
    notes = request.form.get('notes', '').strip()

    if not file_storage or not title:
        flash("Please provide a file and a document title.", 'danger')
        return redirect(url_for('records'))

    try:
        orig_name, stored_name, file_size, content_type = save_secure_upload(
            file_storage, app.config['UPLOAD_FOLDER']
        )
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('records'))

    doc = MedicalDocument(
        patient_id=patient.id,
        uploaded_by_id=user.id,
        title=title,
        filename=orig_name,
        stored_filename=stored_name,
        file_type=content_type,
        file_size=file_size,
        category=category,
        notes=notes
    )
    db.session.add(doc)
    db.session.commit()

    log_activity(patient.id, user.id, 'document_uploaded', f"{user.name} uploaded document: {title} ({category}).")
    flash(f"Document '{title}' uploaded safely to the vault.", 'success')
    return redirect(url_for('records'))

@app.route('/vault/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    doc = db.session.get(MedicalDocument, doc_id)

    if not patient or not doc or doc.patient_id != patient.id:
        abort(403)

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        doc.stored_filename,
        as_attachment=True,
        download_name=doc.filename
    )

@app.route('/vault/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    doc = db.session.get(MedicalDocument, doc_id)

    if not patient or not doc or doc.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.stored_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    title = doc.title
    db.session.delete(doc)
    db.session.commit()

    log_activity(patient.id, user.id, 'document_deleted', f"{user.name} deleted document: {title}.")
    flash(f"Document '{title}' was deleted from the vault.", 'info')
    return redirect(url_for('records'))

# ============================================================================
# Collaborative Care Circle & Invitations
# ============================================================================

@app.route('/care-circle', methods=['GET', 'POST'])
@login_required
def care_circle():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_manage_circle(user, patient.id):
            abort(403)

        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'family')
        perm = request.form.get('permission', 'viewer')

        if not email:
            flash("Please enter an email address.", 'danger')
            return redirect(url_for('care_circle'))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            if existing_user.id == user.id:
                flash("You are already part of this care circle.", 'warning')
                return redirect(url_for('care_circle'))

            existing_member = Membership.query.filter_by(patient_id=patient.id, user_id=existing_user.id).first()
            if existing_member:
                flash(f"{existing_user.name} already has access to this care circle.", 'warning')
                return redirect(url_for('care_circle'))

            # Directly link existing registered user
            membership = Membership(
                patient_id=patient.id,
                user_id=existing_user.id,
                permission=perm
            )
            db.session.add(membership)
            db.session.commit()

            log_activity(patient.id, user.id, 'member_added', f"{user.name} added {existing_user.name} to the care circle as {perm.title()}.")
            create_notification(existing_user.id, f"Added to {patient.name}'s Care Circle", f"You have been granted {perm.title()} access by {user.name}.", category='circle', action_url='/dashboard', patient_id=patient.id)

            flash(f"{existing_user.name} added to the care circle as {perm.title()}.", 'success')
            return redirect(url_for('care_circle'))

        else:
            # Generate secure passcode invitation
            code = f"CIRCLE-{secrets.token_hex(3).upper()}"
            inv = CareCircleInvitation(
                patient_id=patient.id,
                invited_by_id=user.id,
                invited_email=email,
                role=role,
                permission=perm,
                invite_code=code,
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.session.add(inv)
            db.session.commit()

            log_activity(patient.id, user.id, 'invite_created', f"{user.name} generated invitation passcode {code} for {email}.")
            flash(f"Invitation created for {email}! Passcode: {code}. Share this code so they can join.", 'success')
            return redirect(url_for('care_circle'))

    members = Membership.query.filter_by(patient_id=patient.id).all()
    pending_invites = CareCircleInvitation.query.filter_by(patient_id=patient.id, status='pending').all()
    full_activities = ActivityLog.query.filter_by(patient_id=patient.id).order_by(ActivityLog.created_at.desc()).limit(20).all()

    return render_template(
        'care_circle.html',
        patient=patient,
        members=members,
        pending_invites=pending_invites,
        full_activities=full_activities
    )

@app.route('/care-circle/permission/<int:membership_id>', methods=['POST'])
@login_required
def update_member_permission(membership_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    m = db.session.get(Membership, membership_id)

    if not patient or not m or m.patient_id != patient.id or not can_manage_circle(user, patient.id):
        abort(403)

    new_perm = request.form.get('new_permission')
    if new_perm in ('editor', 'viewer'):
        m.permission = new_perm
        db.session.commit()
        log_activity(patient.id, user.id, 'permission_changed', f"{user.name} updated {m.user.name}'s permission to {new_perm.title()}.")
        flash(f"{m.user.name}'s permission changed to {new_perm.title()}.", 'success')

    return redirect(url_for('care_circle'))

@app.route('/care-circle/revoke/<int:membership_id>', methods=['POST'])
@login_required
def revoke_member(membership_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    m = db.session.get(Membership, membership_id)

    if not patient or not m or m.patient_id != patient.id or not can_manage_circle(user, patient.id):
        abort(403)

    member_name = m.user.name
    db.session.delete(m)
    db.session.commit()

    log_activity(patient.id, user.id, 'member_revoked', f"{user.name} revoked care circle access for {member_name}.")
    flash(f"Access revoked for {member_name}.", 'info')
    return redirect(url_for('care_circle'))

@app.route('/care-circle/invite/revoke/<int:invite_id>', methods=['POST'])
@login_required
def revoke_invitation(invite_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    inv = db.session.get(CareCircleInvitation, invite_id)

    if not patient or not inv or inv.patient_id != patient.id or not can_manage_circle(user, patient.id):
        abort(403)

    inv.status = 'revoked'
    db.session.commit()
    flash(f"Invitation for {inv.invited_email} revoked.", 'info')
    return redirect(url_for('care_circle'))

@app.route('/care-circle/redeem', methods=['POST'])
@login_required
def redeem_invite_code():
    user = get_current_user()
    code = request.form.get('invite_code', '').strip().upper()

    inv = CareCircleInvitation.query.filter_by(invite_code=code, status='pending').first()
    if not inv or inv.expires_at < datetime.utcnow():
        flash("Invalid or expired invitation passcode.", 'danger')
        return redirect(url_for('dashboard'))

    inv.status = 'accepted'
    membership = Membership(
        patient_id=inv.patient_id,
        user_id=user.id,
        permission=inv.permission
    )
    db.session.add(membership)
    db.session.commit()

    log_activity(inv.patient_id, user.id, 'member_joined', f"{user.name} joined the circle using passcode {code}.")
    flash(f"Joined {inv.patient.name}'s care circle as {inv.permission.title()}!", 'success')
    return redirect(url_for('dashboard'))

# ============================================================================
# Caregiver Task Management
# ============================================================================

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_edit_patient(user, patient.id):
            abort(403)

        title = request.form.get('title', '').strip()
        if not title:
            flash("Task title is required.", 'danger')
            return redirect(url_for('tasks'))

        assigned_id = request.form.get('assigned_to_id')
        assigned_to_id = int(assigned_id) if assigned_id else None

        task = CareTask(
            patient_id=patient.id,
            title=title,
            description=request.form.get('description', '').strip(),
            assigned_to_id=assigned_to_id,
            due_date=request.form.get('due_date') or None,
            priority=request.form.get('priority', 'Medium'),
            status='Pending',
            created_by_id=user.id
        )
        db.session.add(task)
        db.session.commit()

        log_activity(patient.id, user.id, 'task_created', f"{user.name} created task: {title} (Priority: {task.priority}).")
        if assigned_to_id and assigned_to_id != user.id:
            create_notification(assigned_to_id, f"New Task: {title}", f"Assigned to you by {user.name}. Due: {task.due_date or 'No date'}.", category='task', action_url='/tasks', patient_id=patient.id)

        flash(f"Care task '{title}' created.", 'success')
        return redirect(url_for('tasks'))

    status_filter = request.args.get('status', 'all')
    base_query = CareTask.query.filter_by(patient_id=patient.id)

    all_tasks = base_query.order_by(CareTask.due_date).all()
    pending_tasks = [t for t in all_tasks if t.status in ('Pending', 'In Progress')]
    completed_tasks = [t for t in all_tasks if t.status == 'Completed']

    if status_filter == 'pending':
        filtered = pending_tasks
    elif status_filter == 'completed':
        filtered = completed_tasks
    else:
        filtered = all_tasks

    members = Membership.query.filter_by(patient_id=patient.id).all()

    return render_template(
        'tasks.html',
        patient=patient,
        filtered_tasks=filtered,
        all_tasks=all_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        status_filter=status_filter,
        members=members
    )

@app.route('/tasks/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    task = db.session.get(CareTask, task_id)

    if not patient or not task or task.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    if task.status == 'Completed':
        task.status = 'Pending'
        task.completed_at = None
    else:
        task.status = 'Completed'
        task.completed_at = datetime.utcnow()

    db.session.commit()
    log_activity(patient.id, user.id, f'task_{task.status.lower()}', f"{user.name} marked task '{task.title}' as {task.status}.")
    flash(f"Task status updated to {task.status}.", 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    task = db.session.get(CareTask, task_id)

    if not patient or not task or task.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    task.title = request.form.get('title', task.title).strip()
    task.description = request.form.get('description', task.description).strip()
    task.priority = request.form.get('priority', task.priority)
    task.due_date = request.form.get('due_date') or None

    assigned_id = request.form.get('assigned_to_id')
    task.assigned_to_id = int(assigned_id) if assigned_id else None

    db.session.commit()
    log_activity(patient.id, user.id, 'task_updated', f"{user.name} updated task: {task.title}.")
    flash("Task updated.", 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    user = get_current_user()
    patient = get_patient_for_user(user)
    task = db.session.get(CareTask, task_id)

    if not patient or not task or task.patient_id != patient.id or not can_edit_patient(user, patient.id):
        abort(403)

    title = task.title
    db.session.delete(task)
    db.session.commit()

    log_activity(patient.id, user.id, 'task_deleted', f"{user.name} deleted task: {title}.")
    flash(f"Task '{title}' removed.", 'info')
    return redirect(url_for('tasks'))

# ============================================================================
# Health & Wellbeing Journal
# ============================================================================

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def journal():
    user = get_current_user()
    patient = get_patient_for_user(user)
    if not patient:
        abort(403)

    if request.method == 'POST':
        if not can_edit_patient(user, patient.id):
            abort(403)

        sys_bp = request.form.get('systolic_bp')
        dia_bp = request.form.get('diastolic_bp')
        hr = request.form.get('heart_rate')
        bs = request.form.get('blood_sugar')

        entry = HealthJournalEntry(
            patient_id=patient.id,
            logged_by_id=user.id,
            mood=request.form.get('mood', 'Good'),
            systolic_bp=int(sys_bp) if sys_bp else None,
            diastolic_bp=int(dia_bp) if dia_bp else None,
            heart_rate=int(hr) if hr else None,
            blood_sugar=float(bs) if bs else None,
            symptoms=request.form.get('symptoms', '').strip(),
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(entry)
        db.session.commit()

        vitals_txt = f" (BP: {entry.systolic_bp}/{entry.diastolic_bp})" if (entry.systolic_bp and entry.diastolic_bp) else ""
        log_activity(patient.id, user.id, 'journal_added', f"{user.name} logged daily wellbeing check-in (Mood: {entry.mood}{vitals_txt}).")

        flash("Health journal entry saved.", 'success')
        return redirect(url_for('journal'))

    entries = HealthJournalEntry.query.filter_by(patient_id=patient.id).order_by(HealthJournalEntry.created_at.desc()).all()
    return render_template('journal.html', patient=patient, entries=entries)

# ============================================================================
# Notification Center & Preferences
# ============================================================================

@app.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    patient = get_patient_for_user(user)
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    unread_count = sum(1 for n in notifs if not n.is_read)
    pref = NotificationPreference.query.filter_by(user_id=user.id).first()

    return render_template(
        'notifications.html',
        patient=patient,
        notifications=notifs,
        unread_count=unread_count,
        pref=pref
    )

@app.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user = get_current_user()
    notif = db.session.get(Notification, notif_id)
    if notif and notif.user_id == user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(request.referrer or url_for('notifications'))

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash("All notifications marked as read.", 'info')
    return redirect(url_for('notifications'))

@app.route('/notifications/preferences', methods=['POST'])
@login_required
def update_notification_preferences():
    user = get_current_user()
    pref = NotificationPreference.query.filter_by(user_id=user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=user.id)
        db.session.add(pref)

    pref.email_upcoming_dose = ('email_upcoming_dose' in request.form)
    pref.email_missed_dose = ('email_missed_dose' in request.form)
    pref.email_appointments = ('email_appointments' in request.form)
    pref.email_tasks = ('email_tasks' in request.form)
    pref.lead_time_minutes = int(request.form.get('lead_time_minutes', 15))
    pref.updated_at = datetime.utcnow()

    db.session.commit()
    flash("Notification preferences updated successfully.", 'success')
    return redirect(url_for('notifications'))

# ============================================================================
# User Profile & Security Settings
# ============================================================================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    patient = get_patient_for_user(user)

    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'update_profile':
            user.name = request.form.get('name', user.name).strip()
            user.phone = request.form.get('phone', user.phone).strip()
            db.session.commit()
            flash("Profile information updated.", 'success')
            return redirect(url_for('profile'))

        elif action_type == 'change_password':
            current_pass = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            confirm_pass = request.form.get('confirm_password', '')

            if not check_password_hash(user.password, current_pass):
                flash("Current password incorrect.", 'danger')
                return redirect(url_for('profile'))

            if len(new_pass) < 8:
                flash("New password must be at least 8 characters.", 'danger')
                return redirect(url_for('profile'))

            if new_pass != confirm_pass:
                flash("New password and confirmation do not match.", 'danger')
                return redirect(url_for('profile'))

            user.password = generate_password_hash(new_pass)
            db.session.commit()
            flash("Password updated successfully.", 'success')
            return redirect(url_for('profile'))

    return render_template('profile.html', patient=patient)

# ============================================================================
# Error Handling
# ============================================================================

@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html', code=400, message=str(e.description or 'Bad request.')), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='You do not have authorization to view or edit this healthcare space.'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='The requested healthcare resource could not be found.'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='An internal server error occurred. Please try again.'), 500

# ============================================================================
# Application Bootstrap & Seed Initialization
# ============================================================================

with app.app_context():
    seed_database(app)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
