# Deployment Guide: Frontend (Vercel) + Backend (Render)

This project uses a split architecture:
- **Frontend**: Single Page Application (React/Vite) hosted on **Vercel**.
- **Backend**: Python FastAPI service hosted on **Render**.

## 1. Backend Deployment (Render)

The backend MUST be deployed on Render (or any Docker-compatible PaaS) because it uses a persistent Python runtime, not Serverless Functions.

### Check `runtime.txt`
Ensure `backend/runtime.txt` matches your Python version (e.g., `python-3.11.0`).

### Environment Variables (Required on Render)
You **MUST** set these in the Render Dashboard → Environment:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API Key |
| `DATABASE_URL` | MongoDB Atlas Connection String |
| `JWT_SECRET_KEY` | Strong random string (min 32 chars) |
| `ADDITIONAL_CORS_ORIGINS` | `https://your-frontend.vercel.app` |
| `DEBUG` | `False` |

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port 10000
```

---

## 2. Frontend Deployment (Vercel)

### Environment Variables
Set this in Vercel Project Settings:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://puritypropai.onrender.com` |

(Replace `puritypropai` with your actual Render project name if different).

### Build Settings
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

## 3. Verification

1. **Verify Backend**: Visit `https://your-backend-app.onrender.com/`. You should see `{"status": "active"}`.
2. **Verify Database**: Visit `https://your-backend-app.onrender.com/api/health/db`. Should return `{"status": "ok"}`.
3. **Verify Frontend**: Open your Vercel URL. Login and Chat should work without network errors.
