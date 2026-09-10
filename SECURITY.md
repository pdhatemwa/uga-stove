# Security and Privacy

UGA Stove contains beneficiary names, telephone numbers, household locations, coordinates, signature evidence, and carbon waiver records. Treat the system as a personal data system, not a public dashboard with a login screen attached as decoration.

## Implemented controls

i. Passwords are hashed with Argon2 and are never stored in plain text.

ii. API access uses signed, expiring JWT bearer tokens. Password changes increment the token version and invalidate existing sessions.

iii. RBAC is enforced in the API, not merely by hiding buttons in Streamlit.

iv. Distribution officers can be restricted to their assigned distribution point.

v. Stakeholder accounts receive only aggregate dashboard data. They cannot query names, phone numbers, IDs, coordinates, PDFs, or exports.

vi. Household IDs, stove serials, household to distribution, and stove to distribution relationships have database unique constraints.

vii. Corrections require a reason and expected record version. Concurrent edits are rejected instead of silently overwriting each other.

viii. Record creation, correction, user creation, distribution point creation, password change, signature capture, signature review, and import activity are audited.

ix. Evidence uploads accept only validated JPEG, PNG, or PDF content, enforce a size limit, re encode images to remove metadata, and record a SHA 256 digest.

x. API responses carry no store, content type, frame, referrer, and camera policy headers. Production Caddy adds HTTPS and HSTS.

xi. Real data, environment secrets, local evidence, and backups are excluded from Git by default.

## Required production controls

i. Replace every placeholder in `.env`. Use a unique database password, a random JWT secret, and a one time bootstrap administrator password.

ii. Run only through HTTPS. Do not send passwords or beneficiary data over plain HTTP outside local development.

iii. Put login rate limiting at Caddy, a cloud web application firewall, or an API gateway. The starter deliberately avoids an unreliable in process limiter because multiple workers would not share its state.

iv. Use an S3 compatible private bucket for evidence in production, or encrypt and back up the attached evidence volume. Never make the bucket public.

v. Restrict server administration with SSH keys, host firewall rules, automatic security updates, and named administrator accounts.

vi. Define retention periods for household records, signature evidence, rejected import files, audit logs, and backups. Delete only through an approved records management process.

vii. Encrypt backups, keep at least one copy outside the server, and perform a restore test. A backup that has never been restored is merely a hopeful file.

viii. Review user access at least monthly during distribution and immediately disable departed or reassigned users.

ix. Do not display live coordinates or personal details on stakeholder screens or presentation projectors.

x. Obtain an approved privacy notice and beneficiary consent language that covers the actual processing, carbon project obligations, evidence photograph, access, retention, and contact procedure.

## Signature statement

The workflow records evidence that a physical form was signed. The timestamp, witness, authenticated capturing user, record verification code, and file hash strengthen traceability. They do not automatically create a qualified or cryptographic digital signature. Legal and project assurance teams should approve the wording, evidentiary procedure, retention period, and use of thumbprints before rollout.

## Incident response minimum

i. Disable the affected account and increment its token version.

ii. Preserve application, proxy, database, and audit logs.

iii. Identify which records and evidence objects were accessed or changed.

iv. Rotate exposed secrets and restore only from a verified clean backup where necessary.

v. Follow the organization's approved personal data breach assessment and notification process.

