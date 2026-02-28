# 🔐 Authentication Plan — PurityProp AI

## 📌 Overview

This project uses a **custom JWT-based authentication system** built with:

- **Backend**: FastAPI + python-jose (JWT) + passlib (bcrypt hashing)
- **Frontend**: React Context API + Axios interceptors
- **Database**: MongoDB (via Odmantic ODM) for user storage

No third-party auth service (Firebase, Supabase, Auth0) is used. All authentication logic is self-hosted and fully controlled.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                    │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Login.jsx   │   │ Register.jsx │   │ AuthContext   │  │
│  │  (UI Form)   │   │  (UI Form)   │   │ (State Mgmt) │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘  │
│         │                  │                   │          │
│         └──────────────────┼───────────────────┘          │
│                            │                              │
│                    Axios + Interceptors                   │
│                    (Auto Token Attach)                    │
└────────────────────────────┼──────────────────────────────┘
                             │ HTTPS
┌────────────────────────────┼──────────────────────────────┐
│                      BACKEND (FastAPI)                    │
│                            │                              │
│  ┌─────────────────────────▼──────────────────────────┐   │
│  │              auth_routes.py (API Layer)             │   │
│  │  POST /api/auth/register                           │   │
│  │  POST /api/auth/login                              │   │
│  │  POST /api/auth/refresh                            │   │
│  │  GET  /api/auth/me                                 │   │
│  └─────────────────────────┬──────────────────────────┘   │
│                            │                              │
│  ┌─────────────────────────▼──────────────────────────┐   │
│  │              auth.py (Core Logic)                   │   │
│  │  • hash_password()     → SHA256 + bcrypt            │   │
│  │  • verify_password()   → SHA256 + bcrypt verify     │   │
│  │  • create_access_token()  → JWT (30 min)            │   │
│  │  • create_refresh_token() → JWT (7 days)            │   │
│  │  • verify_token()      → JWT decode + validate      │   │
│  │  • get_current_user()  → Token → DB lookup          │   │
│  └─────────────────────────┬──────────────────────────┘   │
│                            │                              │
│  ┌─────────────────────────▼──────────────────────────┐   │
│  │              MongoDB (User Collection)              │   │
│  │  • email (unique, indexed)                          │   │
│  │  • hashed_password                                  │   │
│  │  • name                                             │   │
│  │  • created_at                                       │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

## 🔑 Authentication Flow (Step-by-Step)

### 1. User Registration

```
Frontend                          Backend                         MongoDB
   │                                │                               │
   │  POST /api/auth/register       │                               │
   │  {email, password, name}       │                               │
   │ ─────────────────────────────► │                               │
   │                                │  Check if email exists        │
   │                                │ ─────────────────────────────►│
   │                                │  ◄─── No duplicate ──────────│
   │                                │                               │
   │                                │  hash_password(password)      │
   │                                │  SHA256 → bcrypt              │
   │                                │                               │
   │                                │  Save User document           │
   │                                │ ─────────────────────────────►│
   │                                │  ◄─── User saved ────────────│
   │                                │                               │
   │                                │  create_access_token()        │
   │                                │  create_refresh_token()       │
   │                                │                               │
   │  ◄──────────────────────────── │                               │
   │  {access_token, refresh_token, │                               │
   │   user: {id, email, name}}     │                               │
   │                                │                               │
   │  Store tokens in localStorage  │                               │
   │  Set user in AuthContext       │                               │
   │  Redirect to Dashboard         │                               │
```

### 2. User Login

```
Frontend                          Backend                         MongoDB
   │                                │                               │
   │  POST /api/auth/login          │                               │
   │  {email, password}             │                               │
   │ ─────────────────────────────► │                               │
   │                                │  Find user by email           │
   │                                │ ─────────────────────────────►│
   │                                │  ◄─── User document ─────────│
   │                                │                               │
   │                                │  verify_password(             │
   │                                │    input_password,            │
   │                                │    stored_hash                │
   │                                │  )                            │
   │                                │                               │
   │                                │  ✅ Match → Generate tokens   │
   │                                │  ❌ Fail  → 401 Unauthorized  │
   │                                │                               │
   │  ◄──────────────────────────── │                               │
   │  {access_token, refresh_token, │                               │
   │   user: {id, email, name}}     │                               │
   │                                │                               │
   │  Store tokens in localStorage  │                               │
   │  Set user in AuthContext       │                               │
   │  Redirect to Dashboard         │                               │
```

### 3. Authenticated Request (Any Protected Route)

```
Frontend                              Backend
   │                                    │
   │  GET /api/auth/me                  │
   │  Header: Authorization: Bearer     │
   │         <access_token>             │
   │ ──────────────────────────────────►│
   │    (Token auto-attached via        │
   │     Axios interceptor)             │
   │                                    │  verify_token(access_token)
   │                                    │  Decode JWT → Extract user_id
   │                                    │  DB lookup → Find User
   │                                    │
   │                                    │  ✅ Valid → Return user data
   │                                    │  ❌ Expired → 401
   │  ◄────────────────────────────────│
   │  {id, email, name, created_at}     │
```

### 4. Token Refresh (Automatic)

```
Frontend                              Backend
   │                                    │
   │  Any API call → 401 Unauthorized   │
   │  ◄────────────────────────────────│
   │                                    │
   │  (Axios interceptor catches 401)   │
   │                                    │
   │  POST /api/auth/refresh            │
   │  {refresh_token: <stored_token>}   │
   │ ──────────────────────────────────►│
   │                                    │  Verify refresh_token
   │                                    │  Check type == "refresh"
   │                                    │  Generate new access_token
   │                                    │
   │  ◄────────────────────────────────│
   │  {access_token (new),              │
   │   refresh_token (same), user}      │
   │                                    │
   │  Update localStorage               │
   │  Retry original failed request     │
```

### 5. Logout

```
Frontend
   │
   │  Remove "token" from localStorage
   │  Remove "refresh_token" from localStorage
   │  Set user = null
   │  Set token = null
   │  Redirect to Login page
```

---

## 🗃️ Database Schema (User Model)

**Collection**: `user`  
**ODM**: Odmantic `Model`

```python
class User(Model):
    email: str        # Unique, Indexed
    hashed_password: str
    name: str
    created_at: datetime  # Auto-set on creation
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `_id` | ObjectId | Auto-generated | MongoDB primary key |
| `email` | string | `unique=True, index=True` | User's email address |
| `hashed_password` | string | Required | SHA256 + bcrypt hashed password |
| `name` | string | Required | User's display name |
| `created_at` | datetime | Default: `utcnow()` | Account creation timestamp |

---

## 🔒 Security Implementation

### Password Hashing (Double-Layer)

```
User Password
     │
     ▼
SHA-256 Hash (first layer)
     │
     ▼
Base64 Encode
     │
     ▼
bcrypt Hash (second layer, with salt)
     │
     ▼
Stored in MongoDB
```

**Why double hashing?**
- SHA-256 normalizes the password length (prevents bcrypt's 72-byte limit issue)
- bcrypt provides salting and adaptive cost factor

### JWT Token Structure

**Access Token** (Short-lived):
```json
{
  "sub": "user_object_id",
  "exp": "current_time + 30 minutes"
}
```

**Refresh Token** (Long-lived):
```json
{
  "sub": "user_object_id",
  "type": "refresh",
  "exp": "current_time + 7 days"
}
```

### Token Configuration

| Setting | Value | Source |
|---------|-------|--------|
| Algorithm | `HS256` | `config.py` |
| Secret Key | Environment variable | `.env → JWT_SECRET_KEY` |
| Access Token Expiry | 30 minutes | `config.py` |
| Refresh Token Expiry | 7 days (10,080 min) | `config.py` |

---

## 📁 File Structure

### Backend Files

| File | Purpose |
|------|---------|
| `backend/app/auth.py` | Core auth logic (hashing, JWT, token verification) |
| `backend/app/auth_routes.py` | API endpoints (register, login, refresh, me) |
| `backend/app/models.py` | User model (MongoDB schema) |
| `backend/app/schemas.py` | Pydantic request/response schemas |
| `backend/app/config.py` | JWT settings (secret, expiry, algorithm) |

### Frontend Files

| File | Purpose |
|------|---------|
| `frontend/src/context/AuthContext.jsx` | Auth state management + API calls |
| `frontend/src/pages/Login.jsx` | Login UI form |
| `frontend/src/pages/Register.jsx` | Registration UI form |

---

## 🛡️ Frontend Auth Features

### AuthContext Provides:

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `user` | Object/null | Current logged-in user data |
| `token` | String/null | Current access token |
| `loading` | Boolean | Auth state loading indicator |
| `login(email, password)` | Function | Login and store tokens |
| `register(name, email, password)` | Function | Register and auto-login |
| `logout()` | Function | Clear tokens and user state |
| `isAuthenticated` | Boolean | Quick auth check (`!!user`) |

### Axios Interceptors:

1. **Request Interceptor**: Auto-attaches `Authorization: Bearer <token>` to every API call
2. **Response Interceptor**: Catches `401` errors, attempts token refresh, retries failed request

### Token Storage:

| Key | Storage | Content |
|-----|---------|---------|
| `token` | `localStorage` | JWT access token |
| `refresh_token` | `localStorage` | JWT refresh token |

---

## 🔄 API Endpoints Summary

### POST `/api/auth/register`
- **Request**: `{ email, password, name }`
- **Validation**: Password min 8 chars, Name min 2 chars
- **Response**: `{ access_token, refresh_token, token_type, user }`
- **Status**: `201 Created`

### POST `/api/auth/login`
- **Request**: `{ email, password }`
- **Response**: `{ access_token, refresh_token, token_type, user }`
- **Error**: `401 Invalid email or password`

### POST `/api/auth/refresh`
- **Request**: `{ refresh_token }`
- **Response**: `{ access_token, refresh_token, user }`
- **Error**: `401 Invalid token type / User not found`

### GET `/api/auth/me`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response**: `{ id, email, name, created_at }`
- **Error**: `401 Invalid or expired token`

---

## ⚙️ Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `JWT_SECRET_KEY` | Signs/verifies all JWT tokens | `your-super-secret-key-here` |
| `DATABASE_URL` | MongoDB connection (stores users) | `mongodb+srv://...` |

---

## 📊 Security Checklist

- [x] Passwords hashed with SHA-256 + bcrypt (double layer)
- [x] JWT tokens with configurable expiry
- [x] Refresh token rotation supported
- [x] Unique email constraint (prevents duplicate accounts)
- [x] HTTPBearer security scheme (standard Authorization header)
- [x] Auto-logout on invalid/expired tokens
- [x] No sensitive data exposed in API responses
- [x] Environment-based secret key (not hardcoded)
- [x] CORS whitelist configured
- [ ] Rate limiting on auth endpoints (not implemented)
- [ ] Email verification on registration (not implemented)
- [ ] Password reset flow (not implemented)

---

*Document generated on: 2026-02-19*  
*Project: PurityProp AI — Tamil Nadu Real Estate Assistant*
