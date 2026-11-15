"""
CareCircle Security & Permission Enforcement Service.
CSRF protection, role verification, access scoping, and safe file upload helpers.
"""
import os
import secrets
import uuid
from functools import wraps
from flask import session, request, abort, redirect, url_for, flash, has_request_context
from werkzeug.utils import secure_filename
from models import db, User, Patient, Membership

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx', 'doc'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def generate_csrf_token():
    """Ensure a CSRF token exists in the session and return it."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf():
    """Verify CSRF token for state-changing requests."""
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        session_token = session.get('csrf_token')
        if not session_token or not token or not secrets.compare_digest(token, session_token):
            abort(400, description="Invalid or missing security token (CSRF). Please refresh and try again.")

def get_current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None

def get_patient_for_user(user):
    """
    Resolve the primary patient for the current user.
    If the user is an elder, return their linked patient profile.
    If a caregiver/family member, return the patient of their membership.
    If multiple, allow selecting via session['active_patient_id'] or default to first.
    """
    if not user:
        return None
    if user.role == 'elder' and user.patient_id:
        return db.session.get(Patient, user.patient_id)

    # Check session override if user coordinates for multiple elders
    if has_request_context():
        active_id = session.get('active_patient_id')
        if active_id:
            m = Membership.query.filter_by(user_id=user.id, patient_id=active_id).first()
            if m:
                return db.session.get(Patient, m.patient_id)

    # Default to first membership
    m = Membership.query.filter_by(user_id=user.id).first()
    return db.session.get(Patient, m.patient_id) if m else None

def get_membership(user, patient_id):
    """Retrieve membership entry for a user and patient."""
    if not user or not patient_id:
        return None
    return Membership.query.filter_by(user_id=user.id, patient_id=patient_id).first()

def can_view_patient(user, patient_id):
    """Check if user is authorized to view this patient's records."""
    if not user or not patient_id:
        return False
    if user.role == 'elder' and user.patient_id == patient_id:
        return True
    return bool(Membership.query.filter_by(user_id=user.id, patient_id=patient_id).first())

def can_edit_patient(user, patient_id):
    """
    Check if user is authorized to edit schedules, appointments, tasks, or records.
    Elder has full access to their own profile.
    Caregiver with 'editor' or 'owner' permission can edit.
    Viewers cannot edit.
    """
    if not user or not patient_id:
        return False
    if user.role == 'elder' and user.patient_id == patient_id:
        return True
    membership = Membership.query.filter_by(user_id=user.id, patient_id=patient_id).first()
    return bool(membership and membership.permission in ('editor', 'owner'))

def can_manage_circle(user, patient_id):
    """
    Check if user can invite members or change circle permissions.
    Elder always can.
    Editor/owner caregivers can also assist.
    """
    return can_edit_patient(user, patient_id)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('Please sign in to access your secure care space.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_secure_upload(file_storage, upload_folder):
    """
    Safely store an uploaded file with a unique UUID filename.
    Returns (original_filename, stored_filename, file_size, content_type)
    """
    if not file_storage or file_storage.filename == '':
        raise ValueError("No file selected.")

    original_name = secure_filename(file_storage.filename)
    if not allowed_file(original_name):
        raise ValueError(f"File type not permitted. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")

    ext = original_name.rsplit('.', 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(upload_folder, stored_name)

    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(dest_path)

    file_size = os.path.getsize(dest_path)
    if file_size > MAX_FILE_SIZE:
        os.remove(dest_path)
        raise ValueError("File exceeds maximum allowed size of 10 MB.")

    content_type = file_storage.content_type or 'application/octet-stream'
    return original_name, stored_name, file_size, content_type
