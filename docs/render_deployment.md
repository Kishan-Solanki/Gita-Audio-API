# 🚀 Deploying Garbh Journey Gita Audio API on Render

This guide outlines how to deploy the **Garbh Journey — Gita Audio API** (FastAPI + PostgreSQL 16 + Audio recitations) to [Render](https://render.com).

---

## 📋 Overview of What We Configured

1. **`render.yaml` (Render Blueprint)**:
   - Automated creation of **FastAPI Web Service** and **PostgreSQL Database** (`gita-db`).
   - Auto-generated `JWT_SECRET`.
   - Wired database connection string automatically.
   - Built-in health check path (`/health/ready`).
2. **`deploy/render_build.sh` (Build Script)**:
   - Installs packages and dependencies.
   - Applies database migrations with Alembic (`alembic upgrade head`).
   - Seeds initial chapters, weeks, translations, and registers audio files.
3. **Database URL compatibility (`app/core/config.py`)**:
   - Render exposes database URLs starting with `postgres://` or `postgresql://`.
   - Our configuration automatically normalizes these to `postgresql+asyncpg://` for SQLAlchemy's asynchronous driver.
4. **Static Audio Streaming**:
   - The API mounts `/audio` to serve audio directly with `AUDIO_ROOT=data`.

---

## 🛠️ Step-by-Step Deployment Instructions

### Method 1: Deploy with Render Blueprint (Recommended - 1 Click)

1. **Push your repository to GitHub or GitLab**:
   Ensure your changes including `render.yaml` and `deploy/render_build.sh` are pushed to your remote repository.

2. **Log in to [Render](https://dashboard.render.com)**.

3. **Create a Blueprint**:
   - In Render Dashboard, click **New +** > **Blueprint**.
   - Connect your GitHub repository (`gita-audio-api`).
   - Render will detect `render.yaml` automatically and display the resources it will create:
     - **Web Service**: `gita-audio-api` (Python 3.12)
     - **PostgreSQL Database**: `gita-db` (PostgreSQL 16)
   - Click **Apply**.

4. **Render handles the rest**:
   - Provisions the PostgreSQL database.
   - Builds the Python application.
   - Executes `deploy/render_build.sh` (migrating & seeding data).
   - Starts the application using Gunicorn/Uvicorn workers on port `$PORT`.

---

### Method 2: Manual Setup via Render Dashboard

If you prefer to configure services manually via the UI:

#### 1. Create PostgreSQL Database
- In Render, click **New +** > **PostgreSQL**.
- **Name**: `gita-db`
- **Database**: `gita`
- **User**: `gita_user`
- **PostgreSQL Version**: `16`
- **Plan**: Free or Starter
- Click **Create Database**.
- Once provisioned, copy the **Internal Database URL** (e.g., `postgres://gita_user:...@dpg-...:5432/gita`).

#### 2. Create Web Service
- Click **New +** > **Web Service**.
- Select your repository.
- Configure settings:
  - **Name**: `gita-audio-api`
  - **Language**: `Python 3`
  - **Branch**: `main`
  - **Build Command**: `./deploy/render_build.sh`
  - **Start Command**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
  - **Health Check Path**: `/health/ready`

#### 3. Set Environment Variables
Add the following in the **Environment** tab:

| Variable | Value | Description |
|---|---|---|
| `PYTHON_VERSION` | `3.12.0` | Python runtime version |
| `ENV` | `production` | Production mode |
| `DATABASE_URL` | `<Internal Database URL>` | From the database created above (or Supabase/Neon URL) |
| `JWT_SECRET` | *(Click 'Generate')* | 32+ character random secret |
| `AUDIO_ROOT` | `data` | Directory containing verse audio files |
| `AUDIO_BASE_URL` | `https://<your-app-name>.onrender.com/audio` | Public audio URL |
| `CORS_ORIGINS` | `["*"]` | Allowed front-end origins |

Click **Save Changes** and deploy.

---

## 💡 Important: Render Free Tier Limitations & Workarounds

### 1. Memory Limit (512 MB)
- Render Free Web Service has **512 MB RAM**.
- We configured Gunicorn with **2 workers (`-w 2`)** instead of 4 to stay well within ~250–300 MB RAM.

### 2. Cold Starts (Spin down after 15 min of inactivity)
- Free web services go to sleep if there are no requests for 15 minutes.
- The next request will take ~20–30 seconds to wake up.
- **Tip**: You can use a free pinging service like [Cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) to ping `https://<your-app>.onrender.com/health` every 10–14 minutes to keep it awake!

### 3. Render Free PostgreSQL 30-Day Expiry vs Permanent Free DB
- Render's built-in **free PostgreSQL instance expires after 30 days**.
- **Permanent 100% Free Alternative**: Use **[Supabase](https://supabase.com)** or **[Neon](https://neon.tech)** for PostgreSQL:
  1. Create a free project on [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com).
  2. Copy the connection string (e.g. `postgresql://user:pass@ep-xyz.neon.tech/gita?sslmode=require`).
  3. Set `DATABASE_URL` in Render Web Service environment variables to that connection string.
  4. Both Neon and Supabase provide **permanent free PostgreSQL** with full `pg_trgm` support!

---

## 🔍 Verifying the Deployment

Once Render finishes deploying:

1. **Check Readiness**:
   ```bash
   curl https://<your-app-name>.onrender.com/health/ready
   ```
   **Expected output:**
   ```json
   {"status": "ok", "database": "connected", "version": "1.0.0"}
   ```

2. **Check Interactive Documentation**:
   - Open `https://<your-app-name>.onrender.com/docs` (Swagger UI).
   - Test `GET /api/v1/chapters`.

3. **Check Audio Streaming**:
   - Open or curl:
     ```bash
     curl -I https://<your-app-name>.onrender.com/api/v1/audio/shloks/1/1
     ```
   - It will return `307 Temporary Redirect` to `/audio/ch01/sl01.mp3`.
   - Test byte-range support:
     ```bash
     curl -I -H "Range: bytes=0-1024" https://<your-app-name>.onrender.com/audio/ch01/sl01.mp3
     ```
     Should return `206 Partial Content`.
