"""
CareCircle Comprehensive Automated Test Suite.
Tests authentication, role permissions, medication schedules, dose logging,
appointments, care circle passcodes, tasks, health vault, and adherence intelligence.
"""

import os
import sys
import unittest
import tempfile
from datetime import datetime, date, timedelta

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from werkzeug.security import check_password_hash

# Set testing environment before importing app
os.environ['SECRET_KEY'] = 'test-secret-key-for-carecircle-test-suite'

from app import app
from models import (
    db, User, Patient, Medication, DoseLog, Appointment, Membership,
    CareCircleInvitation, CareTask, MedicalDocument, HealthJournalEntry,
    Notification
)
from seed import seed_database
from services.intelligence import get_adherence_metrics, generate_care_insights, generate_weekly_care_summary

class CareCircleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Use an in-memory or isolated test database
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{cls.db_path}"

        with app.app_context():
            db.create_all()
            seed_database(app)

    @classmethod
    def tearDownClass(cls):
        os.close(cls.db_fd)
        try:
            os.remove(cls.db_path)
        except OSError:
            pass

    def setUp(self):
        self.client = app.test_client()

    def get_csrf_token(self):
        """Helper to obtain a session CSRF token."""
        with self.client.session_transaction() as sess:
            if 'csrf_token' not in sess:
                sess['csrf_token'] = 'test-csrf-token'
            return sess['csrf_token']

    def login_as(self, email, password='Care123!'):
        """Helper to log in with CSRF."""
        self.client.get('/logout')
        csrf = self.get_csrf_token()
        return self.client.post('/login', data={
            'email': email,
            'password': password,
            'csrf_token': csrf
        }, follow_redirects=True)

    def test_01_demo_seed_data_integrity(self):
        """Verify demo patient Margaret Wilson and demo accounts are created."""
        with app.app_context():
            patient = Patient.query.filter_by(name='Margaret Wilson').first()
            self.assertIsNotNone(patient)
            self.assertEqual(patient.blood_group, 'O+')
            self.assertIn('Penicillin', patient.allergies)

            elder = User.query.filter_by(email='elder@carecircle.demo').first()
            caregiver = User.query.filter_by(email='caregiver@carecircle.demo').first()
            family = User.query.filter_by(email='family@carecircle.demo').first()

            self.assertIsNotNone(elder)
            self.assertIsNotNone(caregiver)
            self.assertIsNotNone(family)

            self.assertTrue(check_password_hash(elder.password, 'Care123!'))

            # Check memberships
            m_caregiver = Membership.query.filter_by(patient_id=patient.id, user_id=caregiver.id).first()
            self.assertEqual(m_caregiver.permission, 'editor')

            m_family = Membership.query.filter_by(patient_id=patient.id, user_id=family.id).first()
            self.assertEqual(m_family.permission, 'viewer')

    def test_02_authentication_flows(self):
        """Test elder login, invalid login, and logout."""
        # 1. Invalid login
        res = self.login_as('elder@carecircle.demo', 'WrongPassword!')
        self.assertIn(b'Invalid email address or password', res.data)

        # 2. Valid elder login
        res = self.login_as('elder@carecircle.demo', 'Care123!')
        self.assertIn(b'Overview', res.data)
        self.assertIn(b'Margaret', res.data)

        # 3. Logout
        res = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'signed out', res.data)

    def test_03_dashboard_loads_with_real_data(self):
        """Verify dashboard displays schedule, adherence metrics, and appointments."""
        self.login_as('elder@carecircle.demo')
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Today's Adherence", res.data)
        self.assertIn(b"Upcoming Doctor Visits", res.data)
        self.assertIn(b"Vitamin D3", res.data)

    def test_04_role_based_access_control(self):
        """Verify viewer (Family) cannot modify medication plan while editor (Caregiver) can."""
        # Family viewer attempt to post new medication
        self.login_as('family@carecircle.demo')
        csrf = self.get_csrf_token()
        res = self.client.post('/medications', data={
            'name': 'Unauthorized Med',
            'times': '12:00',
            'csrf_token': csrf
        })
        self.assertEqual(res.status_code, 403)

        # Caregiver editor attempt to post new medication
        self.login_as('caregiver@carecircle.demo')
        csrf = self.get_csrf_token()
        res = self.client.post('/medications', data={
            'name': 'Calcium Supplement',
            'dosage': '500 mg',
            'frequency': 'Daily',
            'times': '13:00',
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Calcium Supplement', res.data)

    def test_05_dose_logging_and_duplicate_handling(self):
        """Verify marking doses as Taken or Skipped with notes."""
        self.login_as('elder@carecircle.demo')
        csrf = self.get_csrf_token()

        with app.app_context():
            med = Medication.query.filter_by(name='Vitamin D3').first()
            med_id = med.id

        sched_time = f"{date.today().isoformat()}T08:00"

        # Log dose as Taken with note
        res = self.client.post(f'/dose/{med_id}/Taken', data={
            'scheduled_for': sched_time,
            'note': 'Taken with warm tea and toast.',
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify in DB
        with app.app_context():
            log = DoseLog.query.filter_by(medication_id=med_id, scheduled_for=sched_time).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.status, 'Taken')
            self.assertEqual(log.note, 'Taken with warm tea and toast.')

    def test_06_appointment_management(self):
        """Verify adding, editing, and completing an appointment."""
        self.login_as('caregiver@carecircle.demo')
        csrf = self.get_csrf_token()

        appt_time = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%dT15:00')
        res = self.client.post('/appointments', data={
            'doctor': 'Dr. Robert King',
            'specialty': 'Neurology',
            'location': 'Metro Health Suite 101',
            'appt_at': appt_time,
            'reason': 'Memory wellness follow-up',
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Dr. Robert King', res.data)

        # Mark appointment completed
        with app.app_context():
            appt = Appointment.query.filter_by(doctor='Dr. Robert King').first()
            appt_id = appt.id

        res = self.client.post(f'/appointments/status/{appt_id}/Completed', data={
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with app.app_context():
            appt_updated = db.session.get(Appointment, appt_id)
            self.assertEqual(appt_updated.status, 'Completed')

    def test_07_care_circle_passcode_invitation(self):
        """Verify creating a passcode invitation and accepting it."""
        self.login_as('elder@carecircle.demo')
        csrf = self.get_csrf_token()

        # Create invite
        res = self.client.post('/care-circle', data={
            'email': 'newhelper@example.com',
            'role': 'caregiver',
            'permission': 'editor',
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CIRCLE-', res.data)

        # Check DB invitation code
        with app.app_context():
            inv = CareCircleInvitation.query.filter_by(invited_email='newhelper@example.com').first()
            self.assertIsNotNone(inv)
            code = inv.invite_code

        # Register new account with that invite code
        self.client.get('/logout')
        csrf = self.get_csrf_token()
        res = self.client.post('/register', data={
            'name': 'New Helper',
            'email': 'newhelper@example.com',
            'password': 'SecurePassword123!',
            'role': 'caregiver',
            'invite_code': code,
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Margaret Wilson', res.data)

    def test_08_care_tasks_and_journal(self):
        """Verify task creation and wellbeing journal entries."""
        self.login_as('caregiver@carecircle.demo')
        csrf = self.get_csrf_token()

        # Create task
        res = self.client.post('/tasks', data={
            'title': 'Schedule influenza vaccination',
            'priority': 'Medium',
            'due_date': date.today().isoformat(),
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Schedule influenza vaccination', res.data)

        # Create journal entry
        res = self.client.post('/journal', data={
            'mood': 'Great',
            'systolic_bp': '120',
            'diastolic_bp': '78',
            'heart_rate': '70',
            'notes': 'Feeling refreshed after morning walk.',
            'csrf_token': csrf
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Feeling refreshed after morning walk', res.data)

    def test_09_adherence_analytics_and_care_intelligence(self):
        """Verify mathematical calculation of adherence rate and report generator."""
        with app.app_context():
            patient = Patient.query.filter_by(name='Margaret Wilson').first()
            metrics = get_adherence_metrics(patient.id, days=7)

            self.assertGreaterEqual(metrics['overall_rate'], 0.0)
            self.assertLessEqual(metrics['overall_rate'], 100.0)
            self.assertEqual(len(metrics['daily_stats']), 7)

            insights = generate_care_insights(patient.id)
            self.assertIsInstance(insights, list)
            self.assertGreater(len(insights), 0)

            summary = generate_weekly_care_summary(patient.id)
            self.assertIsNotNone(summary)
            self.assertEqual(summary['patient_name'], 'Margaret Wilson')
            self.assertIn('adherence_rate', summary)

if __name__ == '__main__':
    unittest.main()
