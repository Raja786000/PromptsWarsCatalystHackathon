# CareCircle — Security, Privacy & Compliance Architecture

CareCircle is engineered following healthcare software design standards and OWASP Top 10 recommendations to safeguard sensitive senior healthcare routines.

---

## 1. Implemented Security Controls

### A. Authentication & Session Management
- **Cryptographic Password Hashing:** All user passwords are encrypted using PBKDF2:SHA256 with per-user salt through Werkzeug’s security helpers. No plaintext passwords exist in the database.
- **Session Protection:** Session identifiers are cryptographically signed using Flask's HMAC mechanism with `SECRET_KEY`.
- **Cookie Flags:** Configured with `SESSION_COOKIE_HTTPONLY = True` to prevent client-side JavaScript access (mitigating XSS session theft) and `SESSION_COOKIE_SAMESITE = 'Lax'` to protect against cross-site request forgery.

### B. CSRF Protection
- **Session-Based Tokens:** State-changing requests (`POST`, `PUT`, `DELETE`, `PATCH`) require a cryptographic CSRF token matching the session token.
- **Universal Form Injection:** All HTML forms across the application include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` or send `X-CSRFToken` headers.
- **Tamper Prevention:** Requests lacking a valid token are rejected with HTTP 400.

### C. Server-Side Role-Based Access Control (RBAC)
- **Granular Permissions:** Authorization is strictly enforced on the server before processing data:
  - **Elder (Owner):** Full control over their linked health profile, medication plan, appointments, and care circle.
  - **Caregiver (Editor):** Authorized to manage medication schedules, log doses, upload documents, and delegate tasks.
  - **Family (Viewer):** Restricted to read-only visibility. Attempted POST requests to medication, appointment, or task endpoints return HTTP 403 Forbidden.
- **Patient Scoping:** Database queries for medications, logs, documents, and appointments are strictly scoped to the patient profile resolved for the authenticated user, preventing cross-tenant information exposure.

### D. Medical Document Vault Security
- **Whitelist Extension Validation:** Only approved medical document extensions (`pdf`, `png`, `jpg`, `jpeg`, `txt`, `docx`, `doc`) are accepted.
- **Filename Sanitization:** Uploaded filenames are scrubbed using `werkzeug.utils.secure_filename` and stored on disk under unique random UUID hex filenames, preventing directory traversal attacks (`../../`) and file collisions.
- **File Size Restrictions:** Strict 10MB file size limit enforced before disk persistence.
- **Authenticated Download Authorization:** Direct file system links are never exposed. Document downloads require passing through authenticated route `/vault/download/<id>`, which verifies circle membership.

### E. Passcode-Based Care Circle Access
- **Cryptographic Passcodes:** Invitations generate unique alphanumeric passcodes (`CIRCLE-XXXX`).
- **Time-Bound Expiration:** Invitations automatically expire after 7 days if unaccepted.
- **Revocation:** Owners can revoke pending invitations or existing memberships at any time.

### F. Tamper-Evident Audit Trail
- **Activity Log Entity:** All critical events (dose confirmations, schedule additions, appointment completions, task updates, document uploads) record the actor ID, timestamp, and human-readable description in `ActivityLog`.
- **Dose History Audit:** Individual dose modifications preserve an audit trail note recording previous status and who made the change.

---

## 2. Healthcare & Regulatory Disclaimers

> [!IMPORTANT]
> **Prototype Statement:** CareCircle is a healthcare coordination and medication routine prototype created for the **PromptWars × Catalyst** hackathon. It is designed to assist older adults and their families with scheduling and adherence tracking.
> 
> **Not a Medical Device:** CareCircle is not a certified SaMD (Software as a Medical Device), electronic prescribing platform, or certified Electronic Health Record (EHR). It does not diagnose medical conditions, formulate clinical prescriptions, compute drug dosages, or recommend changes to doctor-prescribed treatment regimens. All medication schedules reflect data entered by authorized users based on clinician guidance.
