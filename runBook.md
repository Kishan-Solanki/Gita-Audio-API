# Garbh Journey — Gita Audio API: Operational Runbook

**Document Version:** 1.0.0  
**Target Environment:** Production & Staging  
**Application:** Garbh Journey Gita Audio Backend API  
**Last Updated:** November 2026  

---

## Table of Contents
1. [Architecture & System Topology](#1-architecture--system-topology)
2. [Server & System Prerequisites](#2-server--system-prerequisites)
3. [Configuration & Environment Variables](#3-configuration--environment-variables)
4. [Deployment Procedures](#4-deployment-procedures)
5. [Database Operations & Migrations](#5-database-operations--migrations)
6. [Audio Management & Streaming](#6-audio-management--streaming)
7. [Content & Editorial Seeding](#7-content--editorial-seeding)
8. [Monitoring, Health Checks & Logging](#8-monitoring-health-checks--logging)
9. [Scaling & Performance Tuning](#9-scaling--performance-tuning)
10. [Backup, Retention & Disaster Recovery](#10-backup-retention--disaster-recovery)
11. [Security & Access Control](#11-security--access-control)
12. [Troubleshooting & Incident Runbooks](#12-troubleshooting--incident-runbooks)
13. [Routine Maintenance Checklist](#13-routine-maintenance-checklist)
14. [Rollback Procedures](#14-rollback-procedures)

---

## 1. Architecture & System Topology

The Garbh Journey backend consists of three primary containerized components orchestrated via Docker Compose:

```
[Mobile Client (Flutter/React Native)]
           |
           v (HTTPS: 443 / HTTP: 80)
   +---------------+
   |     nginx     |
   +---------------+
     |           \
     |            \ Direct static byte-range streaming (/audio/)
     |             v
     |      +------------------+
     |      | Persistent Disk  |
     |      |   /data/audio/   |
     |      +------------------+
     |
     v Reverse proxy (API requests: /api/v1/...)
+-----------------------------+
|    FastAPI (Uvicorn Workers)|
|         Port 8000           |
+-----------------------------+
               |
               v (AsyncPG pool)
+-----------------------------+
|   PostgreSQL 16 (pg_trgm)   |
|         Port 5432           |
+-----------------------------+
```

### Critical Separation of Concerns
1. **Audio Streaming**: `nginx` serves audio files (`/audio/chNN/slNN.mp3`) directly from disk using native HTTP Range requests (RFC 7233). FastAPI **never** streams audio bytes directly in production to prevent blocking Python async event loops.
2. **REST API**: FastAPI handles all business logic, user auth, pregnancy week calculations, non-guilt streak tracking, search, and JSON metadata.

---

## 2. Server & System Prerequisites

### Hardware Requirements
- **CPU**: 2 vCPU minimum (4 vCPU recommended for high search concurrency)
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk**: 20 GB SSD root + Audio storage partition
  - Gita audio footprint: 700 shloks × 30s @ 64-96 kbps ≈ 170 MB - 250 MB total.
- **Network**: Unmetered or high bandwidth egress.

### Software Requirements
- Ubuntu 22.04 LTS or Debian 12
- Docker 24.0+ & Docker Compose v2.20+
- `ffmpeg` & `ffprobe` (for audio registration script)
- PostgreSQL client (`postgresql-client-16`) for manual management

---

## 3. Configuration & Environment Variables

All settings are configured through environment variables or a `.env` file mounted into containers:

| Variable | Type | Default | Production Requirement | Purpose |
|---|---|---|---|---|
| `DATABASE_URL` | String | `postgresql+asyncpg://...` | **Required** | Async connection string for PostgreSQL |
| `JWT_SECRET` | String | `CHANGE-ME...` | **Required** (64-char hex) | Secret key for HS256 JWT signing |
| `JWT_ALGORITHM` | String | `HS256` | Fixed | Cryptographic algorithm |
| `ACCESS_TOKEN_MINUTES` | Integer | `30` | 15–30 | Expiry lifetime of access tokens |
| `REFRESH_TOKEN_DAYS` | Integer | `30` | 30 | Expiry lifetime of refresh tokens |
| `AUDIO_ROOT` | Path | `/data/audio` | Fixed | Absolute mount path of MP3 files |
| `AUDIO_BASE_URL` | URL | `http://localhost:8000/audio` | `https://api.yourdomain.com/audio` | Base URL returned in audio track responses |
| `AUDIO_HOST_DIR` | Path | `./data/audio` | `/opt/garbh/audio` | Host directory bind-mounted to `/data/audio` |
| `POSTGRES_USER` | String | `postgres` | Custom username | Database admin username |
| `POSTGRES_PASSWORD` | String | `postgres` | Strong random password | Database admin password |
| `POSTGRES_DB` | String | `gita` | `gita` | Database name |
| `ENV` | String | `development` | `production` | Switches structured JSON logs on/off |
| `CORS_ORIGINS` | JSON list | `["*"]` | `["https://app.garbhjourney.com"]` | Allowed CORS origins for web clients |

Generate a production `JWT_SECRET`:
```bash
openssl rand -hex 32
```

---

## 4. Deployment Procedures

### Initial Setup (Clean Server)

```bash
# 1. Clone repository
git clone https://github.com/your-org/gita-audio-api.git /opt/garbh-api
cd /opt/garbh-api

# 2. Setup environment
cp deploy/.env.example deploy/.env
nano deploy/.env  # Configure secure passwords and domain URLs

# 3. Create audio directory on host
sudo mkdir -p /data/audio
sudo chown -R $USER:$USER /data/audio

# 4. Launch containers
cd deploy
docker compose up -d --build

# 5. Verify container health
docker compose ps
docker compose logs -f api
```

### Running Initial Migrations and Seed Data

```bash
# Apply database migrations
docker compose exec api alembic upgrade head

# Import Bhagavad Gita 18 chapters & validate 700 verses count
docker compose exec api python scripts/import_gita_text.py

# Import pregnancy week themes (Weeks 1 to 40)
docker compose exec api python scripts/seed_weeks.py

# Import editorial translations and maternal guidance
docker compose exec api python scripts/import_translations.py --file data/seed/translations_template.csv
```

---

## 5. Database Operations & Migrations

### Connecting to PostgreSQL CLI

```bash
docker compose exec db psql -U postgres -d gita
```

### Checking Data Counts
```sql
SELECT count(*) FROM chapters;           -- Must return 18
SELECT sum(verses_count) FROM chapters;  -- Must return 700
SELECT count(*) FROM week_themes;        -- Must return 40
SELECT count(*) FROM users;
```

### Applying Migrations
```bash
docker compose exec api alembic upgrade head
```

### Generating a New Migration
When SQLAlchemy models are modified in `app/db/models/`:
```bash
docker compose exec api alembic revision --autogenerate -m "describe_changes"
docker compose exec api alembic upgrade head
```

### Rolling Back a Migration
```bash
docker compose exec api alembic downgrade -1
```

---

## 6. Audio Management & Streaming

### Directory Hierarchy
Audio files must reside on the server under `AUDIO_ROOT` with zero-padded chapter and verse numbers:
```
/data/audio/
├── ch01/
│   ├── sl01.mp3
│   ├── sl02.mp3
│   └── sl47.mp3
├── ch02/
│   ├── sl01.mp3
│   ├── sl47.mp3
│   └── sl72.mp3
...
└── ch18/
    ├── sl01.mp3
    └── sl78.mp3
```

### Standard Encoding Specification
All audio files must be standardized prior to uploading for consistent latency and minimal mobile bandwidth:
- **Format**: MP3 (MPEG-1 Audio Layer III)
- **Channels**: Mono (1 channel)
- **Bitrate**: 64 kbps (or 96 kbps for vocal clarity with tanpura)
- **Sample Rate**: 44.1 kHz

Batch conversion using `ffmpeg`:
```bash
ffmpeg -i input_master.wav -ac 1 -b:a 64k -ar 44100 -vn output_ch02_sl47.mp3
```

### Audio Registration & Metadata Ingestion
Once MP3 files are placed in `/data/audio/`, execute the registration script:

```bash
# Dry run first to preview new/modified tracks
docker compose exec api python scripts/register_audio.py --dry-run

# Execute registration with waveform peak calculation
docker compose exec api python scripts/register_audio.py --peaks
```

The script:
1. Validates files against the pattern `chNN/slNN.mp3`.
2. Probes duration and bitrate via `ffprobe`.
3. Computes SHA-256 hash.
4. Increments the `version` integer if the SHA-256 changed (alerting mobile clients to re-download cached files).
5. Populates `audio_tracks` in the database.

### Verifying HTTP Range Requests
Mobile scrubbers require HTTP `206 Partial Content`:
```bash
curl -I -H "Range: bytes=0-1024" http://localhost/audio/ch02/sl47.mp3
```
Expected response:
```http
HTTP/1.1 206 Partial Content
Accept-Ranges: bytes
Content-Range: bytes 0-1024/252000
Content-Type: audio/mpeg
```

---

## 7. Content & Editorial Seeding

### Safety & Medical Disclaimer Rule
> **IMPORTANT:** Content must **never** make medicinal, physiological, or scientific claims regarding fetal development, brain frequencies, or medical outcomes. All themes and reflections must remain focused on maternal calm, peace, mindfulness, and traditional Sanskrit spiritual heritage.

### Editorial CSV Formats
- `data/seed/translations_template.csv`: Contains `literal_meaning`, `simple_explanation`, `reflection_prompt`, and `bonding_practice`.
- `data/seed/chapters_editorial.csv`: Contains `maternal_theme_en` and `maternal_theme_hi`.

---

## 8. Monitoring, Health Checks & Logging

### Health Probes
| Endpoint | Type | Expected Status | Check Description |
|---|---|---|---|
| `GET /health` | Liveness | `200 OK` | Process is running |
| `GET /health/ready` | Readiness | `200 OK` | Database connection pool active |

Curl check:
```bash
curl -s http://localhost/health/ready | jq .
```
Expected output:
```json
{
  "status": "ok",
  "database": "connected",
  "version": "1.0.0"
}
```

### Structured JSON Logging
In production (`ENV=production`), all logs are emitted in JSON with an injected `request_id` (`X-Request-ID`).
Example log entry:
```json
{"event": "app_error", "code": "NOT_FOUND", "message": "Shlok 2.99 not found", "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "level": "warning", "timestamp": "2026-11-22T14:00:00Z"}
```

View live logs:
```bash
docker compose logs -f --tail=100 api
```

---

## 9. Scaling & Performance Tuning

1. **Uvicorn Worker Processes**:  
   Inside `deploy/Dockerfile`, default is 4 workers (`-w 4`). Set worker count to `(2 * CPU cores) + 1`:
   ```bash
   gunicorn app.main:app -w 5 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
2. **PostgreSQL Connection Pool**:  
   In `app/db/session.py`, pool size defaults to 20 with `max_overflow=10`. Adjust if concurrent API clients exceed 200 req/sec.
3. **CDN Integration for Audio**:  
   When daily active audio streaming exceeds server bandwidth, put Cloudflare or AWS CloudFront in front of `/audio/` and update:
   ```env
   AUDIO_BASE_URL=https://cdn.garbhjourney.com/audio
   ```

---

## 10. Backup, Retention & Disaster Recovery

### Automated Nightly Database Backup
Setup a cron job on the host system (`crontab -e`):
```bash
0 2 * * * /usr/bin/docker compose -f /opt/garbh-api/deploy/docker-compose.yml exec -T db pg_dump -U postgres gita | gzip > /opt/backups/gita_$(date +\%F).sql.gz
```

### Backup Retention Policy
- Keep daily backups for 14 days.
- Keep weekly backups for 8 weeks.
- Keep monthly backups for 12 months.

### Restoring from Backup
```bash
# Decompress and restore
gunzip < /opt/backups/gita_2026-11-22.sql.gz | docker compose exec -T db psql -U postgres -d gita
```

### Audio Directory Sync
Sync `/data/audio` to secondary remote storage (e.g. S3 or cold storage server):
```bash
rsync -avz --delete /data/audio/ backup-server:/storage/garbh-audio-backup/
```

---

## 11. Security & Access Control

1. **JWT Rotation**: Access tokens expire in 30 minutes. Refresh tokens are single-use (rotated on every `/auth/refresh` request) and stored as SHA-256 hashes in `refresh_tokens`.
2. **Rate Limiting**: Auth endpoints (`/auth/login`, `/auth/register`) and `/search` are throttled to prevent brute-force attacks.
3. **Admin Endpoints**: Gated behind `is_admin == True` flag on the `users` table.
4. **HTTPS / TLS**: Always terminate TLS at nginx using Certbot or Cloudflare Origin Certificates.

---

## 12. Troubleshooting & Incident Runbooks

### Incident 1: API Returns 500 Internal Server Error
1. Inspect container logs:
   ```bash
   docker compose logs -f --tail=50 api
   ```
2. Check database readiness:
   ```bash
   curl http://localhost/health/ready
   ```
3. If database is unreachable, check DB container status:
   ```bash
   docker compose ps db
   docker compose logs --tail=50 db
   ```

### Incident 2: Audio File Fails to Play on Mobile (404 Not Found)
1. Check if the audio file exists on host:
   ```bash
   ls -la /data/audio/ch02/sl47.mp3
   ```
2. Check file permissions:
   ```bash
   sudo chmod -R 755 /data/audio
   ```
3. Check if nginx container can access the file:
   ```bash
   docker compose exec nginx ls -la /data/audio/ch02/sl47.mp3
   ```

### Incident 3: Search Query Slow or Failing
1. Ensure the PostgreSQL `pg_trgm` extension is active:
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```
2. Re-index GIN indexes:
   ```sql
   REINDEX TABLE shloks;
   REINDEX TABLE shlok_content;
   ```

---

## 13. Routine Maintenance Checklist

- [ ] **Weekly**: Review disk space usage (`df -h`).
- [ ] **Weekly**: Verify backup integrity by test-restoring to a local test DB.
- [ ] **Monthly**: Run `VACUUM ANALYZE` on PostgreSQL to optimize query plans.
- [ ] **Quarterly**: Rotate internal service passwords and secrets.

---

## 14. Rollback Procedures

If a deployment causes regression:
1. Revert container image to previous tag:
   ```bash
   docker compose down
   git checkout <previous_stable_commit>
   docker compose up -d --build
   ```
2. Rollback DB schema if needed:
   ```bash
   docker compose exec api alembic downgrade -1
   ```
3. Confirm system health:
   ```bash
   curl http://localhost/health/ready
   ```
