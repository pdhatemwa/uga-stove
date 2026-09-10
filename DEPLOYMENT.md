# Deployment Guide

## Pilot architecture

Use one reputable virtual private server with at least two CPU cores, 4 GB RAM, SSD storage, Ubuntu LTS, Docker Engine, Docker Compose, a fixed domain, and routine off server backups. For the small initial volume this is sufficient. A managed PostgreSQL database and private S3 compatible evidence bucket are preferable when budget permits.

Do not use a free host that sleeps, deletes local files, or replaces its filesystem. That is usually the source of the “works today, dead on Thursday” genre of deployment.

## Production checklist

i. Point the chosen domain to the server public IP.

ii. Allow inbound TCP ports 80 and 443. Restrict SSH to authorized administrators. Do not publish PostgreSQL.

iii. Copy `.env.example` to `.env` and set production values:

```text
APP_ENV=production
APP_BASE_URL=https://stoves.your-domain.org
DOMAIN=stoves.your-domain.org
DATABASE_URL=postgresql+psycopg://uga_stove:STRONG_PASSWORD@db:5432/uga_stove
JWT_SECRET=LONG_RANDOM_VALUE
BOOTSTRAP_ADMIN_USERNAME=chosen-admin-name
BOOTSTRAP_ADMIN_PASSWORD=one-time-strong-password
```

iv. For object storage, set:

```text
EVIDENCE_STORAGE=s3
S3_ENDPOINT_URL=https://your-private-object-storage-endpoint
S3_BUCKET=uga-stove-evidence
S3_ACCESS_KEY_ID=restricted-service-account
S3_SECRET_ACCESS_KEY=restricted-secret
S3_REGION=your-region
```

The service account should have access only to the named private bucket.

v. Start the production profile:

```bash
docker compose --profile production up --build -d
```

vi. Check service health:

```bash
docker compose ps
docker compose logs --tail=200 api web caddy
```

vii. Sign in, change the bootstrap administrator password, create the three official distribution points, then create named user accounts. Remove the bootstrap password from `.env` after the account exists and restart the services.

viii. Run a dry import of the legacy export. Resolve duplicate identifiers and map every accepted legacy distribution label to an official point. Only then enable commit.

## Backup and restore

Create a database backup:

```bash
make backup
```

Copy the resulting encrypted backup to a separate protected location. If using the local evidence volume, back it up at the same checkpoint as PostgreSQL so that evidence metadata and files remain consistent.

Example restore into a new empty database:

```bash
docker compose exec -T db createdb -U uga_stove uga_stove_restore
docker compose exec -T db pg_restore -U uga_stove -d uga_stove_restore --clean --if-exists < backup.dump
```

Test the restored database before changing the production connection.

## Updates

i. Create a fresh database backup.

ii. Pull or copy the reviewed release.

iii. Run automated tests.

iv. Build and start the release. Alembic applies forward database migrations before the API starts.

v. Check health, login, lookup, dashboard, PDF, and signature upload.

vi. Keep the previous application image until the new release is accepted. Database changes must be rolled back only with a reviewed migration and verified backup.

## Monitoring

Monitor the public HTTPS URL, `/health/live`, `/health/ready`, disk use, PostgreSQL volume use, backup age, container restart count, login failures at the proxy, API error rate, and evidence upload failures. Send alerts to more than one responsible person.

## Connectivity reality

The current Streamlit client requires a live data connection. Test all three distribution points with the actual mobile networks, devices, and peak user load before launch. If outages are frequent, commission the offline capture extension described in `ARCHITECTURE.md` before claiming full Kobo replacement.

