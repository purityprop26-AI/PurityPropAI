# Vercel Frontend Deployment Guide

## ✅ Prerequisites
- Backend is live at: **https://purityprop.onrender.com**
- GitHub repository: **Naveenkumar-0814/PurityPropAI**
- Vercel account (sign up at vercel.com with GitHub)

---

## 🚀 Deployment Steps

### Step 1: Sign in to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Click **"Sign Up"** or **"Log In"**
3. Choose **"Continue with GitHub"**
4. Authorize Vercel to access your GitHub account

---

### Step 2: Import Your Project
1. Click **"Add New..."** → **"Project"**
2. Find and select your repository: **PurityPropAI**
3. Click **"Import"**

---

### Step 3: Configure Project Settings

#### Framework Preset
- **Framework Preset**: `Vite`

#### Root Directory
- **Root Directory**: `frontend`
- Click **"Edit"** next to Root Directory
- Type: `frontend`
- Click **"Continue"**

#### Build Settings
- **Build Command**: `npm run build` (should be auto-detected)
- **Output Directory**: `dist` (should be auto-detected)
- **Install Command**: `npm install` (should be auto-detected)

---

### Step 4: Add Environment Variables

Click **"Environment Variables"** and add:

| Name | Value |
|------|-------|
| `VITE_API_URL` | `https://purityprop.onrender.com` |

**Important:** Make sure to add this for **Production** environment.

---

### Step 5: Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes for the build to complete
3. You'll see "Congratulations!" when done

---

## 🎉 After Deployment

### Your Live URL
Your app will be live at: `https://your-project-name.vercel.app`

### Test the Application
1. Visit your Vercel URL
2. Try logging in with your credentials
3. Test the chat functionality

---

## 🔧 Troubleshooting

### If you get CORS errors:
The backend already allows all origins (`['*']`), so this shouldn't happen.

### If routes don't work (404 on refresh):
Vercel should automatically handle SPA routing for Vite projects. If not, the `vercel.json` file in the frontend directory will handle it.

### If API calls fail:
1. Go to your Vercel project dashboard
2. Click **"Settings"** → **"Environment Variables"**
3. Verify `VITE_API_URL` is set to: `https://purityprop.onrender.com`
4. If you change it, redeploy: **"Deployments"** → **"..."** → **"Redeploy"**

---

## 🔄 Future Updates

### Auto-Deployment
Vercel automatically redeploys when you push to GitHub:
1. Make changes to your code
2. Commit and push to GitHub
3. Vercel automatically builds and deploys

### Manual Redeploy
1. Go to Vercel dashboard
2. Click on your project
3. Go to **"Deployments"** tab
4. Click **"..."** on the latest deployment
5. Click **"Redeploy"**

---

## 📝 Important Notes

- **Free Tier**: Vercel free tier includes unlimited bandwidth
- **Custom Domain**: You can add a custom domain in Settings → Domains
- **Environment Variables**: Never commit `.env` files to GitHub
- **Build Time**: Typically 1-2 minutes per deployment

---

## ✅ Checklist

- [ ] Signed in to Vercel with GitHub
- [ ] Imported PurityPropAI repository
- [ ] Set Root Directory to `frontend`
- [ ] Added `VITE_API_URL` environment variable
- [ ] Deployed successfully
- [ ] Tested login functionality
- [ ] Tested chat functionality

---

## 🆘 Need Help?

If you encounter issues:
1. Check Vercel build logs for errors
2. Verify environment variables are set correctly
3. Ensure backend is running at https://purityprop.onrender.com
4. Check browser console for errors (F12)
