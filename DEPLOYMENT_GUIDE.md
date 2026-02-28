# PurityProp AI — Production Deployment Guide

## Architecture

```
[Vercel]  ← Frontend (React/Vite static files)
    ↓ HTTPS API calls
[Render]  ← Backend (FastAPI + gunicorn + Docker)
    ↓ Async PostgreSQL
[Supabase] ← Database + Auth + pgvector
```

---

## Step 1 — Deploy Backend to Render (FREE)

### 1.1 Go to Render
Open: https://dashboard.render.com

### 1.2 Create New Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repo: `purityprop26-AI/PurityPropAI`
3. Configure:
   - **Name**: `purityprop-api`
   - **Region**: Singapore (closest to India)
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./Dockerfile`
   - **Plan**: Free

### 1.3 Set Environment Variables
In the Render dashboard, add these env vars:

| Variable | Value | Where to find |
|----------|-------|---------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres` | Supabase → Settings → Database → Connection String |
| `SUPABASE_URL` | `https://YOUR_PROJECT.supabase.co` | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | `eyJ...` | Supabase → Settings → API → anon public |
| `GROQ_API_KEY` | `gsk_...` | https://console.groq.com/keys |
| `APP_ENV` | `production` | Type this exactly |
| `DEBUG` | `false` | Type this exactly |

### 1.4 Deploy
Click **"Create Web Service"** → Render auto-builds and deploys.

**Your backend URL will be**: `https://purityprop-api.onrender.com`

> **Note**: Free tier sleeps after 15 min inactivity. First request takes ~30s to wake up.

---

## Step 2 — Deploy Frontend to Vercel (FREE)

### 2.1 Go to Vercel
Open: https://vercel.com/new

### 2.2 Import Repository
1. Click **"Import Git Repository"**
2. Select `purityprop26-AI/PurityPropAI`
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 2.3 Set Environment Variables
| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://purityprop-api.onrender.com` (your Render backend URL) |
| `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth client ID |

### 2.4 Deploy
Click **"Deploy"** → Vercel builds and deploys automatically.

**Your frontend URL will be**: `https://puritypropai.vercel.app` (or custom domain)

---

## Step 3 — Update CORS (After Both Deploy)

Once you have your production URLs, update `backend/app/config.py` → `cors_origins` list:

```python
cors_origins: List[str] = [
    "https://puritypropai.vercel.app",    # ← Your Vercel URL
    "https://purityprop.com",             # ← Custom domain (if any)
    "http://localhost:5173",              # ← Local dev
]
```

This is already done — check if your Vercel URL matches what's in `config.py`.

---

## Step 4 — Enable GitHub Actions CI/CD

The pipeline at `.github/workflows/ci.yml` runs automatically on push to `main`:
- ✅ Linting
- ✅ Confidence engine tests
- ✅ Frontend build
- ✅ Docker image build + push to GitHub Container Registry

**No manual setup needed** — it activates automatically after the first push.

---

## Step 5 — Verify Production

### Backend Health
```
curl https://purityprop-api.onrender.com/
```
Expected: `{"status": "alive", "version": "2.0.0"}`

### Database Health
```
curl https://purityprop-api.onrender.com/api/health/db
```
Expected: `{"status": "ready", "database": "connected"}`

### Chat Test
```
curl -X POST https://purityprop-api.onrender.com/api/sessions -H "Content-Type: application/json" -d "{}"
```
Use the returned `session_id` to test chat.

---

## Optional: Custom Domain

### For Vercel (Frontend)
1. Go to Vercel → Project Settings → Domains
2. Add `purityprop.com`
3. Update DNS: Add CNAME record pointing to `cname.vercel-dns.com`

### For Render (Backend)
1. Go to Render → Service Settings → Custom Domains
2. Add `api.purityprop.com`
3. Update DNS: Add CNAME record pointing to your Render URL

---

## Monitoring (Optional but Recommended)

### Sentry (Free tier: 5K errors/month)
1. Go to https://sentry.io → Create project → Python/FastAPI
2. Get DSN: `https://xxx@sentry.io/xxx`
3. Add to Render env vars: `SENTRY_DSN=https://xxx@sentry.io/xxx`
4. Install: `pip install sentry-sdk[fastapi]`

### UptimeRobot (Free: 50 monitors)
1. Go to https://uptimerobot.com
2. Add HTTP monitor: `https://purityprop-api.onrender.com/`
3. Check interval: 5 minutes (also keeps Render from sleeping!)
