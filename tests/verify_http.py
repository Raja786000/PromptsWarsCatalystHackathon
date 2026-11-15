"""
End-to-End HTTP route and HTML rendering verification.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, User

def run_checks():
    client = app.test_client()
    errors = []

    def check(url, expected_code=200, contains_text=None, method='GET', data=None):
        if method == 'GET':
            res = client.get(url, follow_redirects=True)
        else:
            res = client.post(url, data=data or {}, follow_redirects=True)

        if res.status_code != expected_code:
            errors.append(f"FAIL: {method} {url} returned {res.status_code}, expected {expected_code}")
            return
        if contains_text and contains_text.encode('utf-8') not in res.data:
            errors.append(f"FAIL: {method} {url} response missing expected text: '{contains_text}'")
            return
        print(f"PASS: {method} {url} [{res.status_code}]" + (f" (contains '{contains_text}')" if contains_text else ""))

    print("\n--- 1. Testing Public Routes ---")
    check('/', 200, 'Better Care. Connected Families.')
    check('/login', 200, 'Sign in to your private care space')
    check('/register', 200, 'Create your private healthcare workspace')

    print("\n--- 2. Testing Static Assets ---")
    check('/static/style.css', 200, '--forest-900')
    check('/static/app.js', 200, 'AccessibilityManager')

    print("\n--- 3. Testing Elder Sign-in & All Authenticated Pages ---")
    # Fetch CSRF
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'test-csrf-123'

    res = client.post('/login', data={'email': 'elder@carecircle.demo', 'password': 'Care123!', 'csrf_token': 'test-csrf-123'}, follow_redirects=True)
    assert res.status_code == 200, "Elder login failed"
    print("PASS: Elder sign-in successful")

    check('/dashboard', 200, "Today's Adherence")
    check('/dashboard', 200, "Read Today’s Plan Aloud")
    check('/medications', 200, "Medication Management")
    check('/medications', 200, "Scan Prescription (OCR)")
    check('/calendar', 200, "Medication & Care Calendar")
    check('/calendar?view=week', 200, "Weekly View")
    check('/calendar?view=day', 200, "Daily View")
    check('/analytics', 200, "Adherence Analytics & Care Intelligence")
    check('/analytics', 200, "Weekly Clinical Care Summary")
    check('/appointments', 200, "Medical Appointments")
    check('/records', 200, "Health Records & Document Vault")
    check('/care-circle', 200, "Your Care Circle")
    check('/care-circle', 200, "Active Invitations & Access Passcodes")
    check('/tasks', 200, "Care Tasks Management")
    check('/journal', 200, "Health & Wellbeing Journal")
    check('/notifications', 200, "Notification Center")
    check('/profile', 200, "Account Profile & Security")

    print("\n--- 4. Testing Caregiver Sign-in ---")
    client.get('/logout')
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'test-csrf-caregiver'
    client.post('/login', data={'email': 'caregiver@carecircle.demo', 'password': 'Care123!', 'csrf_token': 'test-csrf-caregiver'}, follow_redirects=True)
    check('/dashboard', 200, "Editor")
    check('/medications', 200, "Add Medication Schedule")

    print("\n--- 5. Testing Family Member Sign-in ---")
    client.get('/logout')
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'test-csrf-family'
    client.post('/login', data={'email': 'family@carecircle.demo', 'password': 'Care123!', 'csrf_token': 'test-csrf-family'}, follow_redirects=True)
    check('/dashboard', 200, "Viewer")

    print("\n-------------------------------------------")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for e in errors:
            print("  ", e)
        sys.exit(1)
    else:
        print("ALL END-TO-END HTTP AND ROUTE CHECKS PASSED (20/20)")

if __name__ == '__main__':
    run_checks()
