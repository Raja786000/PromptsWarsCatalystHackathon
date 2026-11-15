import os
import uuid
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from models import (
    db, User, Patient, Medication, DoseLog, Appointment, Membership,
    CareCircleInvitation, CareTask, MedicalDocument, HealthJournalEntry,
    Notification, NotificationPreference, ActivityLog
)

def create_sample_files(upload_dir):
    """Create sample placeholder documents in uploads folder."""
    os.makedirs(upload_dir, exist_ok=True)
    sample_files = [
        ("Comprehensive_Metabolic_Panel_Labcorp.pdf", "sample_lab_report.pdf", "Lab Report", 245000),
        ("Cardiology_Consultation_Dr_Chen.pdf", "sample_cardio_summary.pdf", "Medical Report", 182000),
        ("Prescription_Order_Amlodipine_Metformin.pdf", "sample_prescription.pdf", "Prescription", 98000),
    ]
    stored_names = []
    for orig, stored, cat, size in sample_files:
        path = os.path.join(upload_dir, stored)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"%PDF-1.4\n% Synthetic Demonstration Healthcare Document for CareCircle\nDocument: {orig}\nType: {cat}\nPatient: Margaret Wilson (DOB: 1948-04-12)\nGenerated for Hackathon Demo.\n")
        stored_names.append((orig, stored, cat, size))
    return stored_names

def seed_database(app):
    with app.app_context():
        db.create_all()
        # Check if already seeded
        if User.query.filter_by(email='elder@carecircle.demo').first():
            return

        # 1. Create Patient Margaret Wilson
        margaret = Patient(
            name='Margaret Wilson',
            dob='1948-04-12',
            blood_group='O+',
            allergies='Penicillin (moderate hives)',
            emergency_contact='+1 (555) 019-2831',
            emergency_contact_name='Jamie Wilson',
            emergency_contact_relation='Daughter',
            primary_physician='Dr. Maria Santos, North Wellness Pavilion',
            notes='Prefers morning clinic appointments before noon. Uses reading glasses for small print. Prefers mild reminders.'
        )
        db.session.add(margaret)
        db.session.flush()

        # 2. Create Demo Users
        password_hash = generate_password_hash('Care123!')
        elder = User(
            name='Margaret Wilson',
            email='elder@carecircle.demo',
            password=password_hash,
            role='elder',
            patient_id=margaret.id,
            phone='+1 (555) 014-9921'
        )
        caregiver = User(
            name='Alex Morgan',
            email='caregiver@carecircle.demo',
            password=password_hash,
            role='caregiver',
            phone='+1 (555) 018-4432'
        )
        family = User(
            name='Jamie Wilson',
            email='family@carecircle.demo',
            password=password_hash,
            role='family',
            phone='+1 (555) 019-2831'
        )
        db.session.add_all([elder, caregiver, family])
        db.session.flush()

        # 3. Memberships
        db.session.add_all([
            Membership(patient_id=margaret.id, user_id=caregiver.id, permission='editor'),
            Membership(patient_id=margaret.id, user_id=family.id, permission='viewer')
        ])

        # 4. Notification Preferences
        for u in [elder, caregiver, family]:
            pref = NotificationPreference(
                user_id=u.id,
                email_upcoming_dose=True,
                email_missed_dose=True,
                email_appointments=True,
                email_tasks=True,
                lead_time_minutes=15
            )
            db.session.add(pref)

        # 5. Medications
        today_iso = date.today().isoformat()
        med_vit_d = Medication(
            patient_id=margaret.id,
            name='Vitamin D3',
            dosage='1000 IU (1 capsule)',
            frequency='Daily',
            instructions='Take with morning breakfast and water',
            times='08:00',
            start_date=(date.today() - timedelta(days=60)).isoformat(),
            prescribed_by='Dr. Maria Santos',
            refill_remaining=45,
            active=True,
            created_by=elder.id,
            notes='Bone density support.'
        )
        med_amlodipine = Medication(
            patient_id=margaret.id,
            name='Amlodipine',
            dosage='5 mg (1 tablet)',
            frequency='Twice daily',
            instructions='Take with full glass of water. Monitor blood pressure weekly.',
            times='09:00, 20:00',
            start_date=(date.today() - timedelta(days=90)).isoformat(),
            prescribed_by='Dr. Sarah Chen',
            refill_remaining=22,
            active=True,
            created_by=elder.id,
            notes='Blood pressure control.'
        )
        med_metformin = Medication(
            patient_id=margaret.id,
            name='Metformin',
            dosage='500 mg (1 tablet)',
            frequency='Twice daily',
            instructions='Take immediately after morning and evening meals to minimize stomach upset',
            times='08:30, 19:30',
            start_date=(date.today() - timedelta(days=45)).isoformat(),
            prescribed_by='Dr. James Thorne',
            refill_remaining=38,
            active=True,
            created_by=elder.id,
            notes='Type 2 diabetes glycemic maintenance.'
        )
        med_atorvastatin = Medication(
            patient_id=margaret.id,
            name='Atorvastatin',
            dosage='20 mg (1 tablet)',
            frequency='Every evening',
            instructions='Take at bedtime with water',
            times='21:00',
            start_date=(date.today() - timedelta(days=120)).isoformat(),
            prescribed_by='Dr. Sarah Chen',
            refill_remaining=14,
            active=True,
            created_by=elder.id,
            notes='Cardiovascular cholesterol protection.'
        )
        med_lisinopril = Medication(
            patient_id=margaret.id,
            name='Lisinopril',
            dosage='10 mg (1 tablet)',
            frequency='Discontinued',
            instructions='Discontinued by Dr. Chen in favor of Amlodipine due to mild dry cough',
            times='08:00',
            start_date=(date.today() - timedelta(days=200)).isoformat(),
            end_date=(date.today() - timedelta(days=91)).isoformat(),
            prescribed_by='Dr. Sarah Chen',
            refill_remaining=0,
            active=False,
            created_by=elder.id,
            notes='Discontinued historical record.'
        )
        db.session.add_all([med_vit_d, med_amlodipine, med_metformin, med_atorvastatin, med_lisinopril])
        db.session.flush()

        # 6. Generate 7-day realistic historical Dose Logs
        # Past 6 days + Today
        active_meds = [med_vit_d, med_amlodipine, med_metformin, med_atorvastatin]
        now = datetime.now()
        for days_back in range(6, -1, -1):
            day_date = date.today() - timedelta(days=days_back)
            day_str = day_date.isoformat()
            for med in active_meds:
                for t in [x.strip() for x in med.times.split(',') if x.strip()]:
                    sched_time = f"{day_str}T{t}"
                    # Determine status
                    if days_back == 0:
                        # Today: compare with current hour
                        try:
                            hour = int(t.split(':')[0])
                        except Exception:
                            hour = 8
                        if hour < now.hour:
                            status = 'Taken'
                            logged_time = datetime.strptime(f"{day_str} {t}", "%Y-%m-%d %H:%M") + timedelta(minutes=7)
                            note = 'Confirmed on time.'
                        elif hour == now.hour:
                            status = 'Taken'
                            logged_time = now
                            note = 'Taken with water.'
                        else:
                            status = 'Scheduled'
                            logged_time = None
                            note = None
                    else:
                        # Past days: mostly Taken, 1 Skipped on day 2 evening, 1 Missed on day 4
                        if days_back == 2 and t == '20:00':
                            status = 'Skipped'
                            logged_time = datetime.strptime(f"{day_str} {t}", "%Y-%m-%d %H:%M") + timedelta(minutes=45)
                            note = 'Late family dinner; decided to skip per clinical guideline.'
                        elif days_back == 4 and t == '21:00':
                            status = 'Missed'
                            logged_time = datetime.strptime(f"{day_str} {t}", "%Y-%m-%d %H:%M") + timedelta(hours=3)
                            note = 'Fell asleep early before reminder.'
                        else:
                            status = 'Taken'
                            logged_time = datetime.strptime(f"{day_str} {t}", "%Y-%m-%d %H:%M") + timedelta(minutes=10)
                            note = 'Confirmed taken.'

                    if status != 'Scheduled':
                        log = DoseLog(
                            medication_id=med.id,
                            patient_id=margaret.id,
                            scheduled_for=sched_time,
                            status=status,
                            logged_by=elder.id if days_back % 2 == 0 else caregiver.id,
                            logged_at=logged_time or datetime.utcnow(),
                            confirmed_at=logged_time,
                            note=note
                        )
                        db.session.add(log)

        # 7. Appointments
        appt_upcoming_1 = Appointment(
            patient_id=margaret.id,
            doctor='Dr. Sarah Chen',
            specialty='Cardiology',
            location='Riverside Medical Centre, Suite 304',
            appt_at=(now + timedelta(days=2)).strftime('%Y-%m-%dT10:30'),
            reason='Routine 6-month cardiovascular checkup and ECG review',
            notes='Bring latest blood pressure log from the journal.',
            status='Scheduled',
            created_by=elder.id
        )
        appt_upcoming_2 = Appointment(
            patient_id=margaret.id,
            doctor='Dr. Alan Patel',
            specialty='Ophthalmology',
            location='City Eye Care Pavilion, Room 12B',
            appt_at=(now + timedelta(days=8)).strftime('%Y-%m-%dT14:15'),
            reason='Annual dilated retinal examination and vision assessment',
            notes='Requires someone to accompany Margaret home due to dilation eye drops.',
            status='Scheduled',
            created_by=caregiver.id
        )
        appt_past = Appointment(
            patient_id=margaret.id,
            doctor='Dr. Maria Santos',
            specialty='Primary Care / Geriatrics',
            location='North Wellness Pavilion, Clinic 1',
            appt_at=(now - timedelta(days=14)).strftime('%Y-%m-%dT11:00'),
            reason='Annual comprehensive physical and prescription renewals',
            notes='Vitals all within target ranges; Metformin dose renewed.',
            status='Completed',
            created_by=elder.id
        )
        db.session.add_all([appt_upcoming_1, appt_upcoming_2, appt_past])

        # 8. Care Tasks
        task1 = CareTask(
            patient_id=margaret.id,
            title='Pick up Amlodipine & Metformin refills',
            description='Collect 30-day refill prescription from Riverside Pharmacy on Main St.',
            assigned_to_id=caregiver.id,
            due_date=(date.today() + timedelta(days=1)).isoformat(),
            priority='High',
            status='Pending',
            created_by_id=elder.id
        )
        task2 = CareTask(
            patient_id=margaret.id,
            title='Arrange transport for Cardiology appointment',
            description='Drive Margaret to Riverside Medical Centre for Dr. Sarah Chen visit at 10:30 AM.',
            assigned_to_id=family.id,
            due_date=(date.today() + timedelta(days=2)).isoformat(),
            priority='High',
            status='In Progress',
            created_by_id=caregiver.id
        )
        task3 = CareTask(
            patient_id=margaret.id,
            title='Weekly pillbox organizer reload',
            description='Verify all medication compartments are filled for the upcoming week.',
            assigned_to_id=caregiver.id,
            due_date=(date.today() - timedelta(days=1)).isoformat(),
            priority='Medium',
            status='Completed',
            completed_at=datetime.utcnow() - timedelta(days=1),
            created_by_id=elder.id
        )
        db.session.add_all([task1, task2, task3])

        # 9. Health Journal
        j1 = HealthJournalEntry(
            patient_id=margaret.id,
            logged_by_id=elder.id,
            mood='Great',
            systolic_bp=122,
            diastolic_bp=80,
            heart_rate=72,
            blood_sugar=108.0,
            weight=68.5,
            symptoms='None reported. Felt energized.',
            notes='Spent 25 minutes tending the community flower garden with Jamie. Slept 8 hours soundly.',
            created_at=datetime.utcnow() - timedelta(days=1, hours=3)
        )
        j2 = HealthJournalEntry(
            patient_id=margaret.id,
            logged_by_id=caregiver.id,
            mood='Good',
            systolic_bp=128,
            diastolic_bp=84,
            heart_rate=76,
            blood_sugar=114.0,
            weight=68.7,
            symptoms='Mild fatigue in the afternoon after warmer weather.',
            notes='Encouraged extra hydration (water + electrolyte broth). Rested for 45 minutes; evening energy returned.',
            created_at=datetime.utcnow() - timedelta(days=3, hours=4)
        )
        db.session.add_all([j1, j2])

        # 10. Sample Medical Documents
        upload_dir = os.path.join(app.root_path, 'uploads')
        sample_docs = create_sample_files(upload_dir)
        for orig, stored, cat, size in sample_docs:
            doc = MedicalDocument(
                patient_id=margaret.id,
                uploaded_by_id=caregiver.id,
                title=orig.replace('_', ' ').replace('.pdf', ''),
                filename=orig,
                stored_filename=stored,
                file_type='application/pdf',
                file_size=size,
                category=cat,
                notes='Official record verified by care coordinator.'
            )
            db.session.add(doc)

        # 11. Sample Care Circle Invitation
        invitation = CareCircleInvitation(
            patient_id=margaret.id,
            invited_by_id=elder.id,
            invited_email='nurse.sarah@carecircle.demo',
            role='caregiver',
            permission='editor',
            invite_code='CIRCLE-M789',
            status='pending',
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(invitation)

        # 12. Sample In-App Notifications
        notif1 = Notification(
            user_id=elder.id,
            patient_id=margaret.id,
            title='Morning Medication Due',
            message='Time for Vitamin D3 (1000 IU) and Metformin (500 mg). Take with breakfast.',
            category='dose',
            action_url='/medications',
            is_read=False
        )
        notif2 = Notification(
            user_id=caregiver.id,
            patient_id=margaret.id,
            title='Upcoming Cardiology Visit',
            message='Dr. Sarah Chen appointment scheduled in 2 days at Riverside Medical Centre.',
            category='appointment',
            action_url='/appointments',
            is_read=False
        )
        notif3 = Notification(
            user_id=family.id,
            patient_id=margaret.id,
            title='New Care Task Assigned',
            message='Arrange transport for Cardiology appointment assigned by Alex Morgan.',
            category='task',
            action_url='/tasks',
            is_read=False
        )
        db.session.add_all([notif1, notif2, notif3])

        # 13. Activity Logs (Audit Trail)
        activities = [
            ActivityLog(
                patient_id=margaret.id,
                user_id=elder.id,
                action_type='dose_confirmed',
                description='Margaret marked Vitamin D3 (1000 IU) as Taken.',
                created_at=datetime.utcnow() - timedelta(hours=3)
            ),
            ActivityLog(
                patient_id=margaret.id,
                user_id=caregiver.id,
                action_type='task_completed',
                description='Alex Morgan completed: Weekly pillbox organizer reload.',
                created_at=datetime.utcnow() - timedelta(days=1, hours=2)
            ),
            ActivityLog(
                patient_id=margaret.id,
                user_id=elder.id,
                action_type='journal_entry',
                description='Margaret added a daily wellbeing check-in (Mood: Great, BP 122/80).',
                created_at=datetime.utcnow() - timedelta(days=1, hours=3)
            ),
            ActivityLog(
                patient_id=margaret.id,
                user_id=caregiver.id,
                action_type='document_uploaded',
                description='Alex Morgan uploaded: Comprehensive Metabolic Panel Labcorp.',
                created_at=datetime.utcnow() - timedelta(days=2)
            )
        ]
        db.session.add_all(activities)

        db.session.commit()
        print("Database initialized and seeded successfully with rich demo data.")
