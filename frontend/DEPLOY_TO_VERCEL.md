# Frontend Deployment to Vercel - Quick Guide

## ✅ Backend Already Deployed
Your backend is live at: **https://purity-prop-b.vercel.app**

## 🚀 Deploy Frontend to Vercel

### Step 1: Import Project
1. Go to [vercel.com](https://vercel.com)
2. Click **"Add New..."** → **"Project"**
3. Select **PurityPropAI** repository
4. Click **"Import"**

### Step 2: Configure Settings

#### Root Directory
- Click **"Edit"** next to Root Directory
- Enter: `frontend`
- Click **"Continue"**

#### Framework Preset
- Should auto-detect as **Vite**

#### Build Settings
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Step 3: Environment Variables

Click **"Add Environment Variable"**:

| Name | Value |
|------|-------|
| `VITE_API_URL` | `https://purity-prop-b.vercel.app` |

**Important:** Select **Production** environment.

### Step 4: Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes
3. You'll get a URL like: `https://your-frontend.vercel.app`

---

## ✅ After Deployment

### Test Your Application

1. Visit your Vercel frontend URL
2. Try logging in
3. Test the chat functionality

### Update Backend CORS (if needed)

If you get CORS errors, update backend CORS settings to include your frontend URL.

---

## 🔄 Auto-Deployment

Vercel will automatically redeploy when you push to GitHub!

---

## 📝 Summary

- ✅ Backend: https://purity-prop-b.vercel.app
- ✅ Frontend: Will be at https://your-frontend.vercel.app
- ✅ Environment variables configured
- ✅ Auto-deployment enabled
