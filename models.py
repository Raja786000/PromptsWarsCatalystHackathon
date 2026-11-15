import os
from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='elder') # elder, caregiver, family
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient_profile = db.relationship('Patient', foreign_keys=[patient_id], backref='linked_user', lazy=True)
    memberships = db.relationship('Membership', backref='user', cascade='all, delete-orphan', lazy=True)
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan', lazy=True)
    preferences = db.relationship('NotificationPreference', backref='user', uselist=False, cascade='all, delete-orphan', lazy=True)

class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20), nullable=True)
    blood_group = db.Column(db.String(8), nullable=True)
    allergies = db.Column(db.String(300), nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_relation = db.Column(db.String(60), nullable=True)
    primary_physician = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    medications = db.relationship('Medication', backref='patient', cascade='all, delete-orphan', lazy=True)
    dose_logs = db.relationship('DoseLog', backref='patient', cascade='all, delete-orphan', lazy=True)
    appointments = db.relationship('Appointment', backref='patient', cascade='all, delete-orphan', lazy=True)
    memberships = db.relationship('Membership', backref='patient', cascade='all, delete-orphan', lazy=True)
    tasks = db.relationship('CareTask', backref='patient', cascade='all, delete-orphan', lazy=True)
    documents = db.relationship('MedicalDocument', backref='patient', cascade='all, delete-orphan', lazy=True)
    journal_entries = db.relationship('HealthJournalEntry', backref='patient', cascade='all, delete-orphan', lazy=True)
    activities = db.relationship('ActivityLog', backref='patient', cascade='all, delete-orphan', lazy=True)

class Medication(db.Model):
    __tablename__ = 'medication'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(80), nullable=True)
    frequency = db.Column(db.String(60), default='Daily') # Daily, Twice daily, As needed, etc.
    instructions = db.Column(db.String(300), nullable=True)
    times = db.Column(db.String(200), nullable=False) # e.g. "08:00, 20:00"
    start_date = db.Column(db.String(20), nullable=True)
    end_date = db.Column(db.String(20), nullable=True)
    prescribed_by = db.Column(db.String(120), nullable=True)
    refill_remaining = db.Column(db.Integer, default=30)
    active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dose_logs = db.relationship('DoseLog', backref='medication', cascade='all, delete-orphan', lazy=True)

class DoseLog(db.Model):
    __tablename__ = 'dose_log'
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    scheduled_for = db.Column(db.String(40), nullable=False) # "YYYY-MM-DDTHH:MM"
    status = db.Column(db.String(20), nullable=False) # "Taken", "Skipped", "Missed", "Scheduled"
    logged_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(300), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    audit_history = db.Column(db.Text, nullable=True) # JSON or string notes of changes

    user = db.relationship('User', foreign_keys=[logged_by], lazy=True)

class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    appt_at = db.Column(db.String(30), nullable=False) # "YYYY-MM-DDTHH:MM"
    reason = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Scheduled') # "Scheduled", "Completed", "Cancelled"
    reminder_sent = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], lazy=True)

class Membership(db.Model):
    __tablename__ = 'membership'
    __table_args__ = (db.UniqueConstraint('patient_id', 'user_id'),)
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission = db.Column(db.String(20), default='viewer') # "owner", "editor", "viewer"
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class CareCircleInvitation(db.Model):
    __tablename__ = 'care_circle_invitation'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_email = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(20), default='family') # "caregiver", "family"
    permission = db.Column(db.String(20), default='viewer') # "editor", "viewer"
    invite_code = db.Column(db.String(32), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending') # "pending", "accepted", "revoked", "expired"
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', foreign_keys=[patient_id], lazy=True)
    inviter = db.relationship('User', foreign_keys=[invited_by_id], lazy=True)

class CareTask(db.Model):
    __tablename__ = 'care_task'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    due_date = db.Column(db.String(20), nullable=True) # "YYYY-MM-DD"
    priority = db.Column(db.String(20), default='Medium') # "Low", "Medium", "High", "Urgent"
    status = db.Column(db.String(20), default='Pending') # "Pending", "In Progress", "Completed"
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignee = db.relationship('User', foreign_keys=[assigned_to_id], lazy=True)
    creator = db.relationship('User', foreign_keys=[created_by_id], lazy=True)

class MedicalDocument(db.Model):
    __tablename__ = 'medical_document'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    filename = db.Column(db.String(255), nullable=False) # Original uploaded filename
    stored_filename = db.Column(db.String(255), unique=True, nullable=False) # Safe uuid-based storage name
    file_type = db.Column(db.String(40), nullable=False) # e.g. "application/pdf"
    file_size = db.Column(db.Integer, default=0) # Bytes
    category = db.Column(db.String(50), default='Medical Report') # "Prescription", "Lab Report", "Discharge Summary", "Insurance / ID", "Other"
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', foreign_keys=[uploaded_by_id], lazy=True)

class HealthJournalEntry(db.Model):
    __tablename__ = 'health_journal_entry'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(30), default='Good') # "Great", "Good", "Neutral", "Tired", "Unwell"
    systolic_bp = db.Column(db.Integer, nullable=True)
    diastolic_bp = db.Column(db.Integer, nullable=True)
    heart_rate = db.Column(db.Integer, nullable=True)
    blood_sugar = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    symptoms = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[logged_by_id], lazy=True)

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(30), default='system') # "dose", "appointment", "task", "circle", "system"
    action_url = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationPreference(db.Model):
    __tablename__ = 'notification_preference'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    email_upcoming_dose = db.Column(db.Boolean, default=True)
    email_missed_dose = db.Column(db.Boolean, default=True)
    email_appointments = db.Column(db.Boolean, default=True)
    email_tasks = db.Column(db.Boolean, default=True)
    lead_time_minutes = db.Column(db.Integer, default=15)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action_type = db.Column(db.String(40), nullable=False) # e.g. "dose_taken", "medication_added", etc.
    description = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', foreign_keys=[user_id], lazy=True)

class ReminderSent(db.Model):
    __tablename__ = 'reminder_sent'
    id = db.Column(db.Integer, primary_key=True)
    reminder_key = db.Column(db.String(240), unique=True, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

def log_activity(patient_id, user_id, action_type, description):
    """Safely log an activity for the patient care circle audit trail."""
    try:
        activity = ActivityLog(
            patient_id=patient_id,
            user_id=user_id,
            action_type=action_type,
            description=description
        )
        db.session.add(activity)
        db.session.commit()
    except Exception:
        db.session.rollback()

def create_notification(user_id, title, message, category='system', action_url=None, patient_id=None):
    """Create an in-app notification for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            patient_id=patient_id,
            title=title,
            message=message,
            category=category,
            action_url=action_url,
            is_read=False
        )
        db.session.add(notif)
        db.session.commit()
    except Exception:
        db.session.rollback()

def notify_circle(patient_id, title, message, category='circle', action_url=None, exclude_user_id=None):
    """Notify all members of a patient's care circle."""
    try:
        memberships = Membership.query.filter_by(patient_id=patient_id).all()
        user_ids = {m.user_id for m in memberships}
        patient = db.session.get(Patient, patient_id)
        if patient and patient.linked_user:
            for u in patient.linked_user:
                user_ids.add(u.id)
        if exclude_user_id:
            user_ids.discard(exclude_user_id)
        for uid in user_ids:
            notif = Notification(
                user_id=uid,
                patient_id=patient_id,
                title=title,
                message=message,
                category=category,
                action_url=action_url,
                is_read=False
            )
            db.session.add(notif)
        db.session.commit()
    except Exception:
        db.session.rollback()
