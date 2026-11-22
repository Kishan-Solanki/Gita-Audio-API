# Garbh Journey — Gita Audio API

Backend REST API and direct audio streaming service for **Garbh Journey**, a mobile pregnancy (Garbh Sanskar) application centered on the **Bhagavad Gita** (18 chapters, 701 shloks in the selected IITK catalog) with Sanskrit audio recitations, Devanagari text, transliteration, maternal explanations, pregnancy week mappings, and non-guilt streak tracking.

---

## 🌟 Key Features

- **18 Chapters & 701 Shloks**: Strict validation and complete metadata for the selected catalog.
- **Direct HTTP Range Audio Streaming**: Optimized byte-range audio streaming served directly via `nginx` for instantaneous mobile audio scrubbing and offline playback.
- **Pregnancy Timeline Mapping**: 40 pregnancy weeks mapped to Garbh Sanskar themes (e.g. Week 18: *Dhriti — Inner Steadfastness*).
- **Daily Sanskar Engine**: Deterministic daily shlok selection tailored to the user's current pregnancy week and local timezone.
- **Non-Guilt Practice Streak**: Gentle habit tracking featuring a 1-day grace period (never shaming or punishing missed days).
- **Trigram Full-Text Search**: Fast search across Devanagari Sanskrit, transliteration, and English/Hindi meanings using PostgreSQL `pg_trgm`.
- **JWT Auth with Rotation**: Secure access & refresh tokens with automated rotation and revocation.
- **OpenAPI 3.1 & Interactive Docs**: Available at `/docs` (Swagger UI) and `/redoc`.

---

## 🏗️ Architecture

```
Client (Mobile App)
   │
   ├─► /audio/chNN/slNN.mp3 ──► nginx (Static files with HTTP Range 206)
   │
   └─► /api/v1/... ───────────► FastAPI (Business logic & JSON endpoints)
                                     │
                                     ▼
                               PostgreSQL 16 (Relational DB & pg_trgm)
```

---

## 🚀 Quick Start (Docker Compose)

### 1. Clone & Configure
```bash
git clone https://github.com/your-org/gita-audio-api.git
cd gita-audio-api

# Configure environment variables
cp deploy/.env.example deploy/.env
```

### 2. Start Services
```bash
cd deploy
docker compose up -d --build
```

### 3. Initialize Database & Seed Content
```bash
# Run database migrations
docker compose exec api alembic upgrade head

# Seed 18 chapters & validate 701 verses count
docker compose exec api python scripts/import_gita_text.py

# Seed 40 pregnancy weeks & shlok mappings
docker compose exec api python scripts/seed_weeks.py

# Seed editorial maternal guidance and meanings
docker compose exec api python scripts/import_translations.py
```

### 4. Verify Health Probes
```bash
curl http://localhost/health/ready
```
Output:
```json
{"status": "ok", "database": "connected", "version": "1.0.0"}
```

---

## 📖 API Documentation & Swagger

- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Interactive Spec**: `http://localhost:8000/redoc`
- **OpenAPI 3.1 YAML Specification**: [`docs/swagger.yaml`](docs/swagger.yaml)
- **Production Runbook**: [`runBook.md`](runBook.md) or [`docs/runbook.md`](docs/runbook.md)

### Endpoints Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | No | Liveness probe |
| `GET` | `/health/ready` | No | Readiness probe (database connectivity) |
| `POST` | `/api/v1/auth/register` | No | Register new user account |
| `POST` | `/api/v1/auth/login` | No | Authenticate with email/password |
| `POST` | `/api/v1/auth/refresh` | No | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Yes | Revoke refresh token |
| `GET` | `/api/v1/me` | Yes | Get current user profile |
| `PATCH` | `/api/v1/me` | Yes | Update profile (due date, lang, timezone) |
| `GET` | `/api/v1/me/favorites` | Yes | List user's favorited shloks |
| `PUT` | `/api/v1/me/favorites/{id}` | Yes | Favorite a shlok (idempotent) |
| `DELETE` | `/api/v1/me/favorites/{id}` | Yes | Unfavorite a shlok (idempotent) |
| `PUT` | `/api/v1/me/progress/{id}` | Yes | Record playback position & listen completion |
| `GET` | `/api/v1/me/progress` | Yes | 18-chapter progress summary (heard/total) |
| `GET` | `/api/v1/me/streak` | Yes | Non-guilt streak statistics (with 1-day grace) |
| `GET` | `/api/v1/me/sanskar-log` | Yes | Merged memory log of favorites & reflections |
| `GET` | `/api/v1/chapters` | Optional | All 18 chapters with maternal themes & progress |
| `GET` | `/api/v1/chapters/featured`| Optional | Chapter recommended for current week/trimester |
| `GET` | `/api/v1/chapters/{n}` | No | Chapter summary & maternal theme |
| `GET` | `/api/v1/chapters/{n}/shloks` | No | Paginated shlok list for chapter |
| `GET` | `/api/v1/chapters/{n}/playlist` | No | Ordered chapter and verse audio; optional `language` filter |
| `GET` | `/api/v1/shloks/{ch}/{v}` | Optional | Full shlok view (Devanagari, audio, meaning) |
| `GET` | `/api/v1/topics` | No | Content filter chips (calm, courage, etc.) |
| `GET` | `/api/v1/search` | No | Search Sanskrit, transliteration, or meanings |
| `GET` | `/api/v1/weeks` | No | 40-week timeline carousel data |
| `GET` | `/api/v1/weeks/{n}` | No | Week theme & recommended shloks |
| `GET` | `/api/v1/daily-sanskar` | Yes | Today's personalized shlok & practice |
| `POST` | `/api/v1/sanskar/complete` | Yes | Mark today's sanskar complete (idempotent) |
| `GET` | `/api/v1/manifest/chapters/{n}` | No | Offline audio manifest; optional `language` filter |
| `GET` | `/api/v1/manifest/weeks/{n}` | No | Offline audio manifest; optional `language` filter |
| `GET` | `/api/v1/reciters` | No | Available audio voices |
| `GET` | `/api/v1/audio/languages` | No | Languages with registered active audio |
| `GET` | `/api/v1/audio/shloks/{chapter}/{verse}` | No | Redirect to the verse MP3 for Range-capable streaming |
| `PUT` | `/api/v1/admin/chapters/{n}/theme` | Admin | Update chapter maternal theme |
| `POST` | `/api/v1/admin/audio/rescan` | Admin | Trigger audio files scan & update |

---

## 🎧 Audio File Ingestion & Streaming

Store individual recordings in `data/` in the format:
```
/data/audio/chNN/slNN.mp3
```
Docker Compose mounts the repository's `data/` directory as `/data/audio` in the API and
nginx containers. The included IITK recordings are committed in `data/chNN/slNN.mp3`. For
local development, set `AUDIO_ROOT=data` and `AUDIO_BASE_URL=http://localhost:8000/audio`.

To fetch the IITK legacy Supersite's Sanskrit verse recitations into `data/chNN/slNN.mp3`, run
`python scripts/download_iitk_audio.py --root data --delay 1`. The downloader writes
`data/iitk_audio_manifest.json` with verse references, source URLs, and SHA-256 hashes so it can
resume without redownloading existing files. The direct API stream path is
`/api/v1/audio/shloks/{chapter}/{verse}` and redirects to the static `/audio/chNN/slNN.mp3`
file so nginx can serve byte ranges. To include the track in the shlok detail `audio` field,
register it with `python scripts/register_audio.py --root data`.
Recommended audio encoding:
```bash
ffmpeg -i input.wav -ac 1 -b:a 64k -ar 44100 output.mp3
```

Scan and register chapter and verse audio tracks into the database:
```bash
python scripts/register_audio.py --root data --dry-run
# Review the summary, then rerun without --dry-run to write track metadata.
```

Audio bytes are served by nginx in Docker and support HTTP Range requests. Local development
serves files from `AUDIO_ROOT`.

The verse recordings and source URL checksums are listed in `data/iitk_audio_manifest.json`.
The downloader can fetch additional recordings from the IITK MediaWiki MP3 asset paths when
needed; the committed audio files are already available to the static audio endpoint.

---

## 🧪 Testing

Run the automated test suite using `pytest`:
```bash
pytest -v
```

---

## 📄 License
All Bhagavad Gita Sanskrit shloks are public domain. Application code is licensed under the MIT License.
