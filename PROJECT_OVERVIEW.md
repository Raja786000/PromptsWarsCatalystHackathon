# CareCircle — Product & Architecture Overview
**Hackathon:** PromptWars × Catalyst  
**Challenge:** Elderly Care & Medication Management Platform  
**Tagline:** *"Better Care. Connected Families. Healthier Living."*

---

## 1. Problem Statement & Mission
Aging in place and managing multiple chronic medical conditions is challenging for older adults. Fragmented medication schedules, confusing dosing regimens, missed appointments, and disconnected family members create severe safety risks and caregiver burnout.

**CareCircle** transforms senior healthcare coordination from isolated reminders into a collaborative, permission-aware digital sanctuary. The platform empowers older adults to maintain independence and dignity at the center of their care choices, while giving dedicated caregivers the tools to manage regimens and family members real-time peace of mind.

---

## 2. Product Capabilities & Modules

### 👵 1. Dignified Elder-First Experience
- **Accessibility Toolbar:** Standard, Large (+15%), and Extra-Large (+30%) typography scaling.
- **High-Contrast Mode:** One-click WCAG AAA contrast switch for individuals with visual impairments.
- **Voice Assistant:** Native speech synthesis ("Read Today's Plan Aloud") speaks the morning, afternoon, and evening routines clearly at an accessible cadence.
- **One-Tap Confirmations:** Touch-friendly dose logging with optional observation notes.

### 💊 2. Advanced Medication Management & Dose Tracking
- **Multi-Dose Schedules:** Support for complex regimens (e.g. multiple daily reminder times, morning/evening meal coordination).
- **Refill Tracking:** Automatic decrement of remaining pack doses with low-supply indicators.
- **Dose Status Engine:** Granular statuses (`Scheduled`, `Taken`, `Skipped`, `Missed`) with timestamp auditing and prevention of duplicate logs.
- **Prescription OCR Scanner:** Interactive computer-vision preview extracting drug name, dosage, frequency, and instructions with mandatory human verification before saving.

### 📅 3. Medication & Care Calendar
- **Interactive Multi-View:** Seamless switching between 7-Day Weekly and Daily Schedule views.
- **Visual Status Coding:** Green (Taken), Blue (Scheduled), Red (Missed), Amber (Skipped), Forest (Medical Visits).
- **Direct Actionability:** Click any calendar dose pill to view clinical instructions or confirm/update dose status.

### 📊 4. Adherence Analytics & Smart Care Intelligence
- **Transparent Mathematical Engine:** Computes adherence based strictly on past-due scheduled doses (excluding future doses from being marked missed prematurely).
- **Chart.js Visualizations:** 7-Day adherence trend curves, Taken vs Missed doughnut distribution, and per-medication compliance bars.
- **Rule-Based Care Intelligence:** Identifies actionable behavioral patterns (e.g., morning vs evening adherence variations, 100% compliance achievements, recent missed-dose alerts).
- **Executive Weekly Care Summary:** Formatted clinical handover report summarizing adherence, vitals, upcoming doctor visits, and open tasks—with one-click "Print Report" and "Copy to Clipboard" for physician consultations.

### 🩺 5. Doctor Appointment Coordination
- **Visit Tracking:** Clinician name, medical specialty, clinic/hospital location, date & time, reason, and preparation instructions.
- **Lifecycle Management:** Scheduled, Completed, and Cancelled statuses with historical archive.

### 👥 6. Collaborative Care Circle & Passcode Invitations
- **Role Scoping:**
  - **Elder (Owner):** Full control of profile and care decisions.
  - **Caregiver (Editor):** Manages medication schedules, logs doses, schedules clinic visits, and delegates tasks.
  - **Family (Viewer):** Real-time read-only visibility into routines, vitals, and appointments without intrusive check-in calls.
- **Passcode Access:** Generate unique, expiring invitation codes (e.g. `CIRCLE-XXXX`) for family members and aides to link their accounts upon registration.
- **Audit Trail:** Complete chronological activity feed tracking all actions taken in the care circle.

### 📋 7. Caregiver Task Delegation
- **Coordination Board:** Assign actionable responsibilities (e.g., pharmacy refill pickups, wheelchair transport arrangement, clinic paperwork preparation).
- **Priority & Due Dates:** Urgent, High, Medium, Low badges with overdue indicators.

### 📄 8. Health Records & Medical Document Vault
- **Clinical Profile:** Chronic conditions, blood group, primary physician, emergency contacts with direct phone dial.
- **Allergy Alert Banner:** High-visibility warnings for known drug allergies (e.g., Penicillin) to prevent medical errors.
- **Encrypted Document Vault:** Secure storage for laboratory results (CMP/CBC), discharge summaries, and prescription orders with authenticated download protection.

### 📝 9. Health & Wellbeing Journal
- **Daily Check-Ins:** Mood tracking (Great, Good, Neutral, Tired, Unwell), blood pressure (systolic/diastolic), heart rate, blood glucose, weight, and symptom logs.
- **Caregiver Handover Notes:** Record observations and observations across shifts.

### 🔔 10. Proactive Notifications & SMTP Reminder Worker
- **In-App Notification Center:** Unread count badges, category filters, and mark-as-read controls.
- **Proactive Email Alerts:** Dedicated background worker process (`reminder_worker.py`) monitoring doses and appointments with duplicate dispatch prevention and dry-run fallback.

---

## 3. Technical Architecture

```
carecircle/
├── app.py                      # Flask Application Server, Routes & Bootstrap
├── models.py                   # SQLAlchemy Models (12 Entities) & Audit Helpers
├── seed.py                     # Rich Demonstration Seeder for Margaret Wilson
├── reminder_worker.py          # Standalone Proactive SMTP Reminder Process
├── requirements.txt            # Python Dependencies
├── Procfile                    # Render / Gunicorn Web Process
├── render.yaml                 # Infrastructure as Code for Cloud Deployment
├── .env.example                # Environment Configuration Template
├── services/
│   ├── intelligence.py         # Care Intelligence, Adherence Metrics, Summary Generator
│   └── security.py             # CSRF Protection, RBAC, File Upload Sanitizer
├── static/
│   ├── style.css               # Complete Design System (Forest & Sage Palette, WCAG)
│   └── app.js                  # Speech Synthesis, OCR Demo, Modals, A11y Controls
├── templates/
│   ├── base.html               # Accessible Shell, Sidebar, Topbar, Modals
│   ├── index.html              # Public Landing Page & Interactive Persona Switcher
│   ├── login.html              # Sign-In with 1-Click Demo Fill
│   ├── register.html           # Registration with Role & Invite Passcode
│   ├── dashboard.html          # Overview, Schedule, Metrics, Appointments, Feed
│   ├── medications.html        # Plan, Add/Edit Modals, OCR Scanner
│   ├── calendar.html           # Week & Day Medication/Visit Calendar
│   ├── analytics.html          # Chart.js Trends, Care Intelligence, Clinical Summary
│   ├── appointments.html       # Clinic Visits, Add/Edit, Completion Tracking
│   ├── records.html            # Clinical Health Profile & Document Vault
│   ├── care_circle.html        # Collaborative Circle, Permissions, Passcode Invites
│   ├── care.html               # Alias template pointing to care_circle.html
│   ├── tasks.html              # Caregiver Task Delegation & Status
│   ├── journal.html            # Wellbeing Observations & Vitals Tracker
│   ├── notifications.html      # In-App Alerts & Email Preferences
│   ├── profile.html            # Account Profile & Password Management
│   ├── empty.html              # Unlinked User Welcome & Passcode Redemption
│   └── error.html              # Accessible 400/403/404/500 Error Handler
├── uploads/                    # Secure Medical Document Storage
└── tests/
    ├── test_carecircle.py      # Automated Unit & Integration Test Suite
    └── verify_http.py          # 20-Point End-to-End HTTP Route Verification
```

---

## 4. Demonstration Personas

All accounts use the demonstration password: **`Care123!`**

| Persona | Role | Email | Permissions | Purpose in Demo |
|---|---|---|---|---|
| **Margaret Wilson** | Elder | `elder@carecircle.demo` | Owner | Experiences high-contrast large UI, voice reader, marks doses taken, manages circle |
| **Alex Morgan** | Caregiver | `caregiver@carecircle.demo` | Editor | Manages medications, runs OCR scan, delegates care tasks, updates vitals |
| **Jamie Wilson** | Family | `family@carecircle.demo` | Viewer | Views shared schedule and appointments, reassured of Margaret's daily routine |
| **Nurse Sarah** | Invitee | `nurse.sarah@carecircle.demo` | Passcode: `CIRCLE-M789` | Demonstrates secure invitation and passcode onboarding workflow |
