# CareCircle — Intelligent Elderly Care & Medication Management Platform

[![Hackathon](https://img.shields.io/badge/Hackathon-PromptWars_%C3%97_Catalyst-12382c)](https://docs.google.com/presentation/d/14sCbgSg-t52XPgEX8KpsEFx_6b90iPYK/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-236551)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-52b788)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-0d2820)](LICENSE)

> **"Better Care. Connected Families. Healthier Living."**

CareCircle is a connected healthcare ecosystem designed to help older adults manage their daily medications, doctor appointments, and health routines independently, while keeping family members and caregivers coordinated and informed through secure, passcode-based access.

---

## 🌟 Key Product Differentiators

1. **Elder-First Accessibility & Dignity:**
   - Multi-tier typography scaling (**A**, **A+**, **A++**) directly from the topbar.
   - One-click **High Contrast Mode** compliant with WCAG AAA readability.
   - **Voice Assistant ("Read Today's Plan Aloud"):** Speech synthesis engine speaking daily routines clearly for older adults.
2. **Intelligent Medication & Dose Tracking:**
   - Multi-dose schedules (e.g. morning, afternoon, evening, night).
   - Refill counter tracking remaining pills with low-supply indicators.
   - Dose confirmation (`Taken`, `Skipped`, `Missed`) with observation notes and duplicate prevention.
   - **Prescription OCR Scanner:** Computer vision simulation parsing medication name, dosage, and frequency with mandatory human verification before saving.
3. **Medication & Care Calendar:**
   - Dedicated **Weekly (7-Day)** and **Daily** calendar views.
   - Visual color-coded status markers with one-click dose confirmation.
4. **Adherence Analytics & Smart Care Intelligence:**
   - Transparent calculation: excludes future scheduled doses from being falsely flagged as missed.
   - Chart.js interactive trends: 7-day adherence curve, status distribution, and per-medication rates.
   - Rule-based care pattern detection (e.g. morning vs evening adherence discrepancies).
   - **Executive Weekly Care Summary:** Formatted clinical report ready for physician visits with one-click **Print** and **Copy to Clipboard**.
5. **Collaborative Care Circle & Secure Passcodes:**
   - Tiered permissions: **Elder (Owner)**, **Caregiver (Editor)**, **Family (Viewer)**.
   - Unique alphanumeric passcodes (`CIRCLE-XXXX`) with 7-day expiration for onboarding family and aides.
   - Complete tamper-evident activity audit feed.
6. **Caregiver Task Delegation:**
   - Track responsibilities: pharmacy pickups, transport coordination, paperwork review.
7. **Health Records & Document Vault:**
   - Chronic conditions, vital signs, allergy safeguards with high-visibility alerts.
   - Secure encrypted vault for lab tests (CMP/CBC), discharge summaries, and prescriptions.
8. **Health & Wellbeing Journal:**
   - Daily mood tracker, blood pressure, heart rate, blood glucose, and handover observations.
9. **Proactive Reminders & SMTP Worker:**
   - In-app notification center with unread badges.
   - Standalone background process (`reminder_worker.py`) monitoring upcoming doses, grace periods, and 24h appointment alerts with simulated dry-run fallback when SMTP is unconfigured.

---

## 👥 Demonstration Personas

All accounts use the password: **`Care123!`**

| Persona | Role | Email | Access Level | What to Observe |
|---|---|---|---|---|
| **Margaret Wilson** | Older Adult | `elder@carecircle.demo` | **Owner** | Full management, large text controls, voice reader, log taken doses |
| **Alex Morgan** | Caregiver | `caregiver@carecircle.demo` | **Editor** | Add/edit schedules, run OCR scan, delegate care tasks, update vitals |
| **Jamie Wilson** | Family Member | `family@carecircle.demo` | **Viewer** | Real-time reassurance, read-only schedule visibility, view appointments |
| **Nurse Sarah** | Invitee | `nurse.sarah@carecircle.demo` | Passcode: `CIRCLE-M789` | Redeem invitation passcode upon registration |

*The demo patient is Margaret Wilson (76 years old). All clinical records are synthetic demonstration data.*

---

## 🚀 Quick Start (Local Setup)

Python 3.10+ is recommended.

```bash
# 1. Clone or navigate to the repository
cd carecircle

# 2. Create and activate a virtual environment
# Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the application
python app.py
```

Open your browser to: **`http://127.0.0.1:5000`**

*The SQLite database (`carecircle.db`), demo accounts, and synthetic records are automatically initialized and seeded on first run.*

---

## 🧪 Automated Testing & Verification

Run the comprehensive test suite covering authentication, RBAC, dose logging, appointments, invitations, tasks, and analytics:

```bash
# Run unit & integration test suite
python tests/test_carecircle.py

# Run 20-point end-to-end HTTP route verification
python tests/verify_http.py

# Test the proactive reminder worker
python reminder_worker.py
```

---

## 📧 Proactive Email Reminders (Optional)

The application operates seamlessly in demonstration dry-run mode without SMTP credentials. To send actual email alerts:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Configure your SMTP provider credentials in `.env`:
   ```ini
   SECRET_KEY=your-random-production-secret-key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM=CareCircle <your-email@gmail.com>
   ```
3. Run the reminder worker via cron or Task Scheduler every 5 minutes:
   ```bash
   python reminder_worker.py
   ```

---

## ☁️ Production Deployment (Render / Gunicorn)

CareCircle includes native deployment configurations for Render and standard WSGI servers:

- **Procfile:** `web: gunicorn app:app`
- **render.yaml:** Pre-configured with automatic secret generation and Python runtime.

To deploy on Render:
1. Connect your repository to Render.
2. Select **New Web Service**.
3. Render automatically detects `render.yaml` and deploys using `gunicorn app:app`.

---

## 🛡️ Security & Privacy Notice

CareCircle is a healthcare management prototype created for the **PromptWars × Catalyst** challenge. It enforces server-side role validation, CSRF token checks, cryptographic password hashing, and encrypted document storage. It is not a certified medical device and does not provide clinical diagnoses, alter prescribed treatments, or calculate drug dosages. All clinical data should be verified with qualified healthcare practitioners.
