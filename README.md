# UGA Stove

UGA Stove is a secure stove distribution registry, field data collection application, printable form generator, signature evidence workflow, and live stakeholder dashboard for Ntungamo.

This is an operational transaction system with a controlled import pipeline. Calling the whole thing a “data pipeline” is only partly correct. The authoritative component is the transaction database. The pipeline is the route through which legacy Kobo data is validated, normalized, quarantined when necessary, and then admitted into that database.

## What is implemented

i. Household IDs and stove serial numbers are normalized before comparison. Case, spaces, underscores, and hyphens cannot be used to sneak in duplicates.

ii. PostgreSQL unique constraints provide race safe, one to one enforcement between a household, stove, and distribution.

iii. Roles include administrator, data manager, distribution officer, auditor, and stakeholder. A distribution officer may be restricted to one official distribution point. A stakeholder sees aggregate dashboard data only.

iv. New entry, record lookup, controlled correction, CSV export, and an immutable audit trail are included.

v. A two page PDF reproduces the participation form and beneficiary certificate structure, including household data, stove data, blank physical signature areas, a verification code, and a QR code.

vi. A phone or laptop camera can photograph the signed paper form. UGA Stove records the beneficiary, witness, time, optional location, file hash, and reviewer decision. No dedicated signature machine is needed.

vii. The dashboard reports distributions, unique households, unique stoves, signature status, stove sizes, distribution point totals, and activity over time.

viii. A controlled Kobo migration performs a dry run, rejects duplicate identifiers, rejects unmapped distribution point labels, and produces a downloadable rejection report.

ix. Docker Compose supplies PostgreSQL, the FastAPI service, the Streamlit interface, health checks, automatic restart policies, persistent volumes, and optional Caddy HTTPS termination.

## Quick start in VS Code

i. Extract the project and open the `uga-stove` folder in VS Code.

ii. Create the runtime configuration:

```bash
cp .env.example .env
```

iii. In `.env`, replace every placeholder password. Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

iv. Start the local system:

```bash
docker compose up --build -d
```

v. Open [http://localhost:8501](http://localhost:8501), then sign in with the bootstrap administrator credentials from `.env`.

vi. Create the three official distribution points before creating field officers or importing legacy data.

vii. Edit `config/distribution_points.example.csv` so that every legacy Kobo label maps to one of the official point codes. Run the import as a dry check first. Commit only after reviewing the rejected rows report.

## Local development without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
python -m api.bootstrap
uvicorn api.main:app --reload --port 8000
```

In a second terminal:

```bash
source .venv/bin/activate
API_BASE_URL=http://localhost:8000 streamlit run web/app.py
```

SQLite is the development default only. Use PostgreSQL for concurrent field work.

## Production link

Point a domain name to the server, set `DOMAIN` and `APP_BASE_URL=https://your-domain` in `.env`, then run:

```bash
docker compose --profile production up --build -d
```

Caddy obtains and renews HTTPS certificates. The database is not published to the internet, and the direct Streamlit port is bound to the server loopback interface.

Read `DEPLOYMENT.md` before using real beneficiary data.

## Existing data

The supplied real Kobo export is deliberately not embedded in this code archive because it contains beneficiary names, telephone numbers, coordinates, and attachment links. Place it in `data/private/` after extraction. That directory is excluded from Git.

The preliminary findings from the supplied export are in `DATA_QUALITY_FINDINGS.md`. The count and location labels do not yet agree with the stated project scope, so the first migration must remain a dry run until the official three distribution points and intended household population are confirmed.

## Tests

```bash
pytest
ruff check .
alembic check
```

The included automated tests cover normalization, role permissions, duplicate household rejection, duplicate serial rejection, lookup, dashboard totals, PDF creation, signature hashing, and the Kobo importer.

## Important limitation

This version is an online web application. It can replace Kobo for connected field collection, but it is not offline first. If the three distribution sites have unreliable connectivity, either retain a controlled offline fallback during the pilot or add a Progressive Web App capture client with an encrypted local queue and conflict aware synchronization. Pretending Streamlit works without a network would be optimism wearing a lab coat.

## Documentation

i. `ARCHITECTURE.md` explains system components, data flow, database structure, and scaling.

ii. `SECURITY.md` explains RBAC, privacy, evidence handling, audit controls, and deployment safeguards.

iii. `DEPLOYMENT.md` provides the pilot and production deployment checklist.

iv. `DATA_DICTIONARY.md` defines the principal entities and fields.

v. `DATA_QUALITY_FINDINGS.md` records the non identifying analysis of the supplied Kobo export.

