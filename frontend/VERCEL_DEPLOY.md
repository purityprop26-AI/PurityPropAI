# Vercel Frontend Deployment Guide

## ✅ Backend Already Deployed
Your backend is live at: **https://purityprop.onrender.com**

## 📋 Pre-Deployment Checklist

### 1. Environment Configuration
I've created these files for you:
- ✅ `.env.production` - Production API URL (Render backend)
- ✅ `.env.development` - Local development API URL
- ✅ `vercel.json` - Vercel routing configuration
- ✅ `src/api/client.js` - Centralized API client (optional upgrade)

### 2. Update Frontend Code (Optional)
If you want to use the centralized API client, update your components to import from `src/api/client.js` instead of using axios directly. **This is optional - your current code will work fine.**

---

## 🚀 Deployment Steps

### Step 1: Push Frontend Changes to GitHub
```bash
cd frontend
git add .
git commit -m "Add Vercel deployment configuration"
git push
```

### Step 2: Deploy to Vercel

#### Option A: Using Vercel Dashboard (Recommended)
1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **"Add New Project"**
3. Select your repository: `Naveenkumar-0814/PurityPropAI`
4. Configure project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add Environment Variable:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://purityprop.onrender.com`
6. Click **"Deploy"**

#### Option B: Using Vercel CLI
```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend folder
cd frontend

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### Step 3: Configure Custom Domain (Optional)
1. In Vercel dashboard, go to your project
2. Click **Settings** → **Domains**
3. Add your custom domain

---

## 🔧 Troubleshooting

### CORS Errors
If you see CORS errors, update your backend CORS settings in `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-domain.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Connection Issues
- Verify `VITE_API_URL` is set correctly in Vercel environment variables
- Check that your Render backend is running
- Test API endpoint: `https://purityprop.onrender.com/api/health`

---

## ✨ After Deployment

Your app will be live at: `https://your-project-name.vercel.app`

Test the following:
- ✅ User registration
- ✅ User login
- ✅ Chat functionality
- ✅ Session persistence (refresh token)

---

## 📝 Important Notes

1. **Free Tier Limits**:
   - Vercel: Unlimited bandwidth, 100GB/month
   - Render: Backend may sleep after 15 min of inactivity (first request takes ~30s to wake)

2. **Environment Variables**:
   - Never commit `.env` files to GitHub
   - Always use Vercel dashboard to set production env vars

3. **Updates**:
   - Push to GitHub → Vercel auto-deploys
   - No manual redeployment needed!
