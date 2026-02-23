# 🏗️ PurityPropAI — Complete Project Pipeline Documentation

> **Project:** Tamil Nadu Real Estate AI Assistant (PurityPropAI)
> **Version:** 1.0.0
> **Last Updated:** 2026-02-20
> **License:** MIT

---

## 📌 Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Complete Pipeline Flow](#4-complete-pipeline-flow)
5. [Backend Pipeline (FastAPI)](#5-backend-pipeline-fastapi)
6. [Frontend Pipeline (React/Vite)](#6-frontend-pipeline-reactvite)
7. [Authentication Pipeline](#7-authentication-pipeline)
8. [AI Chat Pipeline](#8-ai-chat-pipeline)
9. [Database Pipeline](#9-database-pipeline)
10. [Deployment Pipeline](#10-deployment-pipeline)
11. [Environment & Credentials](#11-environment--credentials)
12. [Security Architecture](#12-security-architecture)
13. [API Endpoints Reference](#13-api-endpoints-reference)
14. [File Structure Map](#14-file-structure-map)
15. [Dependency List](#15-dependency-list)
16. [Local Development Setup](#16-local-development-setup)

---

## 1. Project Overview

**PurityPropAI** is a production-level, domain-restricted, multilingual AI chatbot for real estate queries specific to **Tamil Nadu, India**. It uses **Llama 3.1 8B** (via Groq Cloud API) as its AI engine and supports three languages:

- **Tamil Script** (தமிழ்)
- **Tanglish** (Tamil in English letters)
- **English**

### Core Capabilities
| Feature | Description |
|---------|-------------|
| 🏠 Domain Restriction | Only answers real estate questions; rejects off-topic queries |
| 🌐 Multilingual | Auto-detects Tamil, Tanglish, or English and responds in same language |
| 📍 TN-Focused | Tamil Nadu laws, TNRERA, DTCP, CMDA, stamp duty, registration |
| 🔐 Authentication | JWT-based login/register with access + refresh tokens |
| 💬 Session Management | Persistent chat sessions with conversation history |
| 🎨 Premium UI | Glassmorphism design with smooth animations |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              FRONTEND (React 18 + Vite)                       │  │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │  │
│  │   │  Login   │  │ Register │  │Dashboard │  │  AI Chat   │  │  │
│  │   └────┬─────┘  └────┬─────┘  └──────────┘  └─────┬──────┘  │  │
│  │        │              │                            │          │  │
│  │   ┌────▼──────────────▼────────────────────────────▼──────┐  │  │
│  │   │           AuthContext + ChatContext                     │  │  │
│  │   │           (State Management Layer)                     │  │  │
│  │   └──────────────────────┬────────────────────────────────┘  │  │
│  │                          │ Axios HTTP (HTTPS)                │  │
│  └──────────────────────────┼───────────────────────────────────┘  │
│                             │                                      │
│              Hosted on: VERCEL (purity-prop-ai.vercel.app)         │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   INTERNET (HTTPS) │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────┼──────────────────────────────────────┐
│              BACKEND (FastAPI + Python 3.11)                       │
│              Hosted on: RENDER (purityprop.onrender.com)           │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │                    main.py (FastAPI App)                       │  │
│  │    ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │    │  CORS       │  │  Auth Routes │  │  Chat Routes     │   │  │
│  │    │  Middleware  │  │  /api/auth/* │  │  /api/chat       │   │  │
│  │    └─────────────┘  └──────┬───────┘  └────────┬─────────┘   │  │
│  │                            │                    │              │  │
│  │    ┌───────────────────────▼────────────────────▼───────────┐ │  │
│  │    │                 SERVICE LAYER                           │ │  │
│  │    │  ┌──────────────┐ ┌────────────┐ ┌──────────────────┐ │ │  │
│  │    │  │ auth.py      │ │ domain_    │ │ llm_service.py   │ │ │  │
│  │    │  │ (JWT+Bcrypt) │ │ validator  │ │ (Groq API Call)  │ │ │  │
│  │    │  └──────────────┘ └────────────┘ └────────┬─────────┘ │ │  │
│  │    │                                           │            │ │  │
│  │    │  ┌────────────────────────────────────────┐│           │ │  │
│  │    │  │ tn_knowledge_base.py (Static KB)       ││           │ │  │
│  │    │  └────────────────────────────────────────┘│           │ │  │
│  │    └────────────────────────────────────────────┼───────────┘ │  │
│  └─────────────────────────────────────────────────┼─────────────┘  │
│                                                    │                │
└────────────────────────────────────────────────────┼────────────────┘
                              │                      │
                    ┌─────────▼────────┐   ┌─────────▼─────────┐
                    │  MongoDB Atlas   │   │   Groq Cloud API  │
                    │  (Cloud DB)      │   │   (Llama 3.1 8B)  │
                    │  cluster0.       │   │   api.groq.com    │
                    │  lpkvq9e.mongodb │   │                   │
                    │  .net            │   │                   │
                    └──────────────────┘   └───────────────────┘
```

---

## 3. Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 | Runtime |
| FastAPI | 0.109.0 | Web framework (ASGI) |
| Uvicorn | 0.27.0 | ASGI server |
| Gunicorn | 21.2.0 | Production process manager |
| Motor | 3.6.0 | Async MongoDB driver |
| Odmantic | 1.0.2 | Async ODM (Object-Document Mapper) |
| httpx | 0.26.0 | HTTP client for Groq API calls |
| python-jose | 3.3.0 | JWT token creation/verification |
| passlib + bcrypt | 1.7.4 / 3.2.0 | Password hashing (SHA256 + bcrypt) |
| pydantic-settings | 2.7.1 | Environment config validation |
| langdetect | 1.0.9 | Language detection |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI framework |
| Vite | 5.0.11 | Build tool & dev server |
| React Router DOM | 6.30.3 | Client-side routing |
| Axios | 1.6.5 | HTTP client |
| Lucide React | 0.309.0 | Icon library |

### Infrastructure
| Service | Purpose | URL |
|---------|---------|-----|
| Vercel | Frontend hosting | `purity-prop-ai.vercel.app` |
| Render | Backend hosting | `purityprop.onrender.com` |
| MongoDB Atlas | Cloud database | `cluster0.lpkvq9e.mongodb.net` |
| Groq Cloud | LLM API | `api.groq.com` |

---

## 4. Complete Pipeline Flow

### End-to-End Request Lifecycle

```
USER types a question
        │
        ▼
┌─ STEP 1: FRONTEND ─────────────────────────────────────┐
│  React captures input → Axios sends POST to backend     │
│  Headers: { Authorization: "Bearer <JWT>" }             │
│  Body: { session_id: "uuid", message: "user text" }     │
└────────────────────────────┬────────────────────────────┘
                             │ HTTPS
                             ▼
┌─ STEP 2: CORS MIDDLEWARE ──────────────────────────────┐
│  Validates request origin against allowed origins list   │
│  Allows: localhost, vercel.app, purityprop.com          │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 3: JWT AUTH (if protected route) ────────────────┐
│  Extracts Bearer token → Decodes with jwt_secret_key    │
│  Validates expiry → Resolves user_id from "sub" claim   │
│  Fetches User from MongoDB by ObjectId                  │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 4: DOMAIN VALIDATION ───────────────────────────┐
│  is_real_estate_query(message)                          │
│  ├─ Length check (max 1000 chars, DoS protection)       │
│  ├─ Non-real-estate indicator check (poem, joke, etc.)  │
│  ├─ Real estate keyword matching (100+ keywords)        │
│  ├─ Regex pattern matching (buy/sell/register patterns) │
│  └─ Result: (True/False, reason)                        │
│                                                         │
│  If REJECTED → detect_language() → get_rejection_msg()  │
│  → Return trilingual rejection response                 │
└────────────────────────────┬───────────────────────────┘
                             │ (if valid)
                             ▼
┌─ STEP 5: LANGUAGE DETECTION ──────────────────────────┐
│  detect_language(text)                                  │
│  ├─ Tamil Unicode check (U+0B80–U+0BFF range)          │
│  ├─ Tanglish word-boundary pattern matching             │
│  ├─ Tanglish suffix detection (la, ku, oda, ah)         │
│  └─ Default: English                                    │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 6: KNOWLEDGE BASE LOOKUP ───────────────────────┐
│  get_knowledge_context(query)                           │
│  ├─ Registration process (7-step procedure)             │
│  ├─ Required documents (buyer/seller/property)          │
│  ├─ Bank loan info (eligibility, process)               │
│  ├─ Stamp duty & fees (7% duty, 1% registration)       │
│  ├─ Measurement units (cent, ground, acre, gunta)       │
│  ├─ Authority info (TNRERA, DTCP, CMDA)                 │
│  └─ Red flags (10 warning indicators)                   │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 7: LLM CALL (Groq API) ────────────────────────┐
│  Build system prompt:                                   │
│  ├─ Domain restriction instructions                     │
│  ├─ Language-specific response rules                    │
│  ├─ Response structure template                         │
│  └─ Injected knowledge base context                     │
│                                                         │
│  Build messages array:                                  │
│  ├─ [0] System prompt                                   │
│  ├─ [1..6] Last 3 conversation exchanges (history)      │
│  └─ [last] Current user message                         │
│                                                         │
│  HTTP POST → api.groq.com/openai/v1/chat/completions   │
│  Model: llama-3.1-8b-instant                            │
│  Temperature: 0.7 | Max Tokens: 1024                    │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 8: SAVE TO DATABASE ────────────────────────────┐
│  Save user message → ChatMessage (embedded document)    │
│  Save assistant response → ChatMessage (embedded)       │
│  Update session timestamp → ChatSession.updated_at      │
│  All via Odmantic → Motor → MongoDB Atlas               │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 9: RESPONSE TO FRONTEND ────────────────────────┐
│  JSON Response:                                         │
│  {                                                      │
│    "session_id": "uuid",                                │
│    "message": "AI response text",                       │
│    "language": "tamil|tanglish|english",                │
│    "timestamp": "2026-02-20T..."                        │
│  }                                                      │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌─ STEP 10: RENDER IN UI ──────────────────────────────┐
│  ChatMessage component renders with markdown support    │
│  Message added to ChatContext state                     │
│  localStorage updated with chat history                 │
│  Auto-scroll to latest message                          │
└───────────────────────────────────────────────────────┘
```

---

## 5. Backend Pipeline (FastAPI)

### Entry Point: `backend/main.py`

```
FastAPI App Initialization
    │
    ├─ Load Settings (config.py → pydantic-settings → .env)
    │   └─ FAIL FAST if GROQ_API_KEY, DATABASE_URL, or JWT_SECRET_KEY missing
    │
    ├─ CORS Middleware (dynamic origin list + ADDITIONAL_CORS_ORIGINS env)
    │
    ├─ Include auth_router → prefix="/api"
    │   ├─ POST /api/auth/register
    │   ├─ POST /api/auth/login
    │   ├─ POST /api/auth/refresh
    │   └─ GET  /api/auth/me
    │
    ├─ Include chat_router → prefix="/api"
    │   ├─ POST /api/sessions
    │   ├─ POST /api/chat
    │   ├─ GET  /api/sessions/{id}/messages
    │   └─ GET  /api/health
    │
    ├─ GET / → Root health check
    └─ GET /api/health/db → Database connectivity check
```

### Service Layer Architecture

```
backend/app/services/
    │
    ├─ domain_validator.py
    │   ├─ REAL_ESTATE_KEYWORDS (100+ terms in English, Tamil, Tanglish)
    │   ├─ NON_REAL_ESTATE_INDICATORS (poem, joke, code, etc.)
    │   ├─ is_real_estate_query() → (bool, reason)
    │   ├─ detect_language() → "tamil" | "tanglish" | "english"
    │   └─ get_rejection_message() → trilingual rejection text
    │
    ├─ tn_knowledge_base.py
    │   ├─ TN_KNOWLEDGE_BASE dictionary (static knowledge)
    │   │   ├─ property_registration (8-step process)
    │   │   ├─ required_documents (buyer/seller/property lists)
    │   │   ├─ authorities (TNRERA, DTCP, CMDA, Sub-Registrar)
    │   │   ├─ stamp_duty_registration (rates & benefits)
    │   │   ├─ measurement_units (cent, ground, acre, gunta)
    │   │   ├─ red_flags (10 warning indicators)
    │   │   ├─ bank_loan (eligibility, process, documents)
    │   │   └─ chennai_specific (zones, authorities)
    │   └─ get_knowledge_context(query) → relevant context string
    │
    └─ llm_service.py
        ├─ LLMService class (singleton via global instance)
        ├─ _get_system_prompt(language, context) → prompt string
        ├─ generate_response(message, history) → (response, language)
        └─ Direct HTTP POST to api.groq.com (via httpx)
```

---

## 6. Frontend Pipeline (React/Vite)

### Component Hierarchy

```
<AuthProvider>                    ← JWT state management
  <ChatProvider>                  ← Chat history state (localStorage)
    <BrowserRouter>
      ├─ /login      → <Login />          (public)
      ├─ /register   → <Register />       (public)
      │
      └─ <ProtectedRoute>                 (requires JWT)
           <MainLayout>                   (Sidebar + Header)
             ├─ /dashboard   → <Dashboard />
             ├─ /chat        → <AIChat />
             ├─ /properties  → <Properties />
             ├─ /valuation   → <Valuation />     (Coming Soon)
             ├─ /documents   → <Documents />     (Coming Soon)
             └─ /approvals   → <Approvals />     (Coming Soon)
```

### State Management

| Context | Storage | Purpose |
|---------|---------|---------|
| `AuthContext` | `localStorage` (token, refresh_token) | JWT tokens, user object, login/register/logout methods |
| `ChatContext` | `localStorage` (chatHistory) | Chat list, messages, create/load/delete/rename chat |

### API Communication

```
frontend/src/api/client.js
    │
    └─ Axios instance
        ├─ baseURL = VITE_API_URL (env variable)
        ├─ Request interceptor: attaches "Bearer <token>" header
        └─ Used by AuthContext and Chat pages
```

---

## 7. Authentication Pipeline

```
┌─ REGISTER FLOW ───────────────────────────────────────┐
│                                                        │
│  User fills: name, email, password, confirmPassword    │
│  Frontend validates: min 8 chars, passwords match      │
│       │                                                │
│       ▼                                                │
│  POST /api/auth/register                               │
│       │                                                │
│       ▼                                                │
│  Check if email exists in MongoDB                      │
│       │                                                │
│       ▼                                                │
│  Hash password: SHA256 → base64 → bcrypt               │
│       │                                                │
│       ▼                                                │
│  Save User document to MongoDB                         │
│       │                                                │
│       ▼                                                │
│  Generate access_token (30 min) + refresh_token (7 d)  │
│       │                                                │
│       ▼                                                │
│  Return { access_token, refresh_token, user }          │
│       │                                                │
│       ▼                                                │
│  Frontend stores tokens in localStorage                │
│  Redirect to /dashboard                                │
└────────────────────────────────────────────────────────┘

┌─ LOGIN FLOW ──────────────────────────────────────────┐
│  POST /api/auth/login { email, password }              │
│       │                                                │
│       ▼                                                │
│  Find user by email → verify_password (SHA256+bcrypt)  │
│       │                                                │
│       ▼                                                │
│  Generate access_token + refresh_token                 │
│  Return tokens + user object                           │
└────────────────────────────────────────────────────────┘

┌─ TOKEN REFRESH FLOW ──────────────────────────────────┐
│  On 401 error → Axios interceptor auto-fires           │
│       │                                                │
│       ▼                                                │
│  POST /api/auth/refresh { refresh_token }              │
│       │                                                │
│       ▼                                                │
│  Verify refresh_token → check type="refresh"           │
│  Generate new access_token → retry original request    │
│  If refresh fails → logout()                           │
└────────────────────────────────────────────────────────┘
```

### JWT Token Structure

| Field | Access Token | Refresh Token |
|-------|-------------|---------------|
| `sub` | user ObjectId | user ObjectId |
| `exp` | +30 minutes | +7 days |
| `type` | (none) | "refresh" |
| Algorithm | HS256 | HS256 |

---

## 8. AI Chat Pipeline

```
User types message in <AIChat /> component
    │
    ├─ If no active session → POST /api/sessions (create UUID)
    │
    ▼
POST /api/chat { session_id, message }
    │
    ├─ 1. Verify session exists in MongoDB
    │
    ├─ 2. Domain Validation
    │   ├─ Length guard (max 1000 chars)
    │   ├─ Anti-topic filter (poem, joke, code, etc.)
    │   ├─ Real estate keyword scan (100+ keywords)
    │   ├─ Regex pattern matching
    │   └─ REJECT → trilingual message → save & return
    │
    ├─ 3. Language Detection
    │   ├─ Tamil Unicode range check
    │   ├─ Tanglish word patterns (15+ patterns)
    │   └─ Default: English
    │
    ├─ 4. Knowledge Base Injection
    │   └─ Keyword-triggered context blocks
    │
    ├─ 5. Groq API Call
    │   ├─ System prompt (domain + language + structure + context)
    │   ├─ Last 6 messages (3 exchanges) as history
    │   ├─ Current user message
    │   ├─ Model: llama-3.1-8b-instant
    │   └─ Temp: 0.7 | Max tokens: 1024
    │
    ├─ 6. Save to MongoDB (user msg + assistant msg as embedded docs)
    │
    └─ 7. Return JSON { session_id, message, language, timestamp }
```

---

## 9. Database Pipeline

### MongoDB Collections (via Odmantic ODM)

```
MongoDB Atlas → Database: "real_estate_ai"

Collection: "user"
┌──────────────────────────────────────┐
│ _id          : ObjectId (auto)       │
│ email        : String (unique, idx)  │
│ hashed_password : String             │
│ name         : String                │
│ created_at   : DateTime              │
└──────────────────────────────────────┘

Collection: "chat_session"
┌──────────────────────────────────────────────┐
│ _id          : ObjectId (auto)               │
│ session_id   : String (unique, indexed)      │
│ user         : Reference<User> (optional)    │
│ messages     : [EmbeddedDocument]             │
│   ├─ role    : "user" | "assistant"          │
│   ├─ content : String                        │
│   ├─ language: String (optional)             │
│   └─ timestamp: DateTime                     │
│ created_at   : DateTime                      │
│ updated_at   : DateTime                      │
└──────────────────────────────────────────────┘
```

### Connection Flow
```
config.py loads DATABASE_URL from .env
    → database.py creates AsyncIOMotorClient (lazy init)
    → Odmantic AIOEngine wraps Motor client
    → All routes use Depends(get_engine) for DI
```

---

## 10. Deployment Pipeline

### Production Architecture

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   VERCEL     │       │   RENDER     │       │ MONGODB ATLAS│
│  (Frontend)  │──────▶│  (Backend)   │──────▶│  (Database)  │
│              │ HTTPS │              │ TLS   │              │
│ Static SPA   │       │ Gunicorn +   │       │ Cluster0     │
│ React/Vite   │       │ Uvicorn      │       │              │
│ CDN delivery │       │ workers      │       │              │
└──────────────┘       └──────┬───────┘       └──────────────┘
                              │
                              │ HTTPS
                              ▼
                       ┌──────────────┐
                       │  GROQ CLOUD  │
                       │  (LLM API)   │
                       │ Llama 3.1 8B │
                       └──────────────┘
```

### Vercel Deployment (Frontend)
| Setting | Value |
|---------|-------|
| Build Command | `cd frontend && npm install && npm run build` |
| Output Directory | `frontend/dist` |
| Framework | Vite |
| Env Variable | `VITE_API_URL=https://purityprop.onrender.com` |
| Routing | SPA rewrites (`/*` → `/index.html`) |

### Render Deployment (Backend)
| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn main:app -c gunicorn.conf.py` |
| Port | 10000 |
| Workers | `CPU * 2 + 1` (UvicornWorker) |
| Timeout | 120 seconds |

### Render Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq Cloud API key |
| `DATABASE_URL` | ✅ | MongoDB Atlas connection string |
| `JWT_SECRET_KEY` | ✅ | 256-bit hex secret for JWT signing |
| `DEBUG` | ❌ | `False` in production |
| `ADDITIONAL_CORS_ORIGINS` | ❌ | Extra allowed origins |

---

## 11. Environment & Credentials

### Backend `.env` (Local Development)
```env
DATABASE_URL=mongodb+srv://<user>:<password>@cluster0.lpkvq9e.mongodb.net/real_estate_ai
DATABASE_NAME=real_estate_ai
JWT_SECRET_KEY=<64-char-hex-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=gsk_<your_groq_key>
```

### Frontend `.env.development`
```env
VITE_API_URL=https://purityprop.onrender.com
```

### Frontend `.env.production`
```env
VITE_API_URL=https://purityprop.onrender.com
```

### Credential Summary

| Credential | Type | Where Stored | Where Used | External? |
|------------|------|-------------|------------|-----------|
| Groq API Key | API Key | `.env` / Render env | `llm_service.py` | ✅ Groq Cloud |
| MongoDB URL | Connection String | `.env` / Render env | `database.py` | ✅ MongoDB Atlas |
| JWT Secret | Signing Key | `.env` / Render env | `auth.py` | ❌ Internal only |
| VITE_API_URL | URL | `.env.*` / Vercel env | Frontend Axios | ❌ Just a URL |

---

## 12. Security Architecture

### Security Layers

```
Layer 1: CORS Middleware
    └─ Whitelist of allowed origins (no wildcard *)

Layer 2: JWT Authentication (Bearer Token)
    ├─ Access Token: 30-min expiry
    ├─ Refresh Token: 7-day expiry
    └─ HS256 algorithm with 256-bit secret

Layer 3: Password Security
    └─ SHA256 pre-hash → base64 encode → bcrypt hash

Layer 4: Domain Restriction
    ├─ Input length limit (1000 chars, DoS protection)
    └─ Keyword + regex validation (real estate only)

Layer 5: Environment Security
    ├─ .env files in .gitignore (not committed)
    ├─ pydantic-settings validation (fail-fast on missing secrets)
    └─ No secrets have default values

Layer 6: Production Hardening
    ├─ DEBUG=False (disables /docs endpoint)
    ├─ Error messages don't expose internals
    └─ DB health check doesn't expose connection details
```

### What's Protected vs. Public

| Endpoint | Auth Required? |
|----------|---------------|
| `GET /` | ❌ Public |
| `GET /api/health` | ❌ Public |
| `GET /api/health/db` | ❌ Public |
| `POST /api/auth/register` | ❌ Public |
| `POST /api/auth/login` | ❌ Public |
| `POST /api/auth/refresh` | ❌ Public (needs valid refresh token) |
| `GET /api/auth/me` | ✅ Protected |
| `POST /api/sessions` | ❌ Public |
| `POST /api/chat` | ❌ Public |
| `GET /api/sessions/{id}/messages` | ❌ Public |

---

## 13. API Endpoints Reference

### Authentication

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| POST | `/api/auth/register` | `{name, email, password}` | `{access_token, refresh_token, user}` |
| POST | `/api/auth/login` | `{email, password}` | `{access_token, refresh_token, user}` |
| POST | `/api/auth/refresh` | `{refresh_token}` | `{access_token, refresh_token, user}` |
| GET | `/api/auth/me` | — (Bearer token) | `{id, email, name, created_at}` |

### Chat

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| POST | `/api/sessions` | `{}` | `{session_id, created_at}` |
| POST | `/api/chat` | `{session_id, message}` | `{session_id, message, language, timestamp}` |
| GET | `/api/sessions/{id}/messages` | — | `{session_id, messages[]}` |

### Health

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/` | `{message, status, environment}` |
| GET | `/api/health` | `{status, service, timestamp}` |
| GET | `/api/health/db` | `{status, message}` |

---

## 14. File Structure Map

```
Real Estate/
│
├── 📄 README.md                      # Project documentation
├── 📄 DEPLOYMENT_GUIDE.md            # Deployment instructions
├── 📄 PROJECT_PIPELINE.md            # This file
├── 📄 vercel.json                    # Vercel SPA config
├── 📄 package.json                   # Root package (unused)
├── 📄 runtime.txt                    # Python version
├── 📄 .gitignore                     # Git ignore rules
│
├── 📁 backend/                       # ─── PYTHON FASTAPI BACKEND ───
│   ├── 📄 main.py                    # FastAPI app entry point
│   ├── 📄 requirements.txt           # Python dependencies
│   ├── 📄 gunicorn.conf.py           # Production server config
│   ├── 📄 runtime.txt                # Python 3.11 spec
│   ├── 📄 .env                       # Local secrets (git-ignored)
│   ├── 📄 .env.example               # Template for .env
│   ├── 📄 .gitignore                 # Backend git ignore
│   │
│   ├── 📁 app/                       # Application package
│   │   ├── 📄 __init__.py            # Package init
│   │   ├── 📄 config.py              # Settings (pydantic-settings)
│   │   ├── 📄 database.py            # MongoDB connection (Motor/Odmantic)
│   │   ├── 📄 models.py              # Database models (User, ChatSession)
│   │   ├── 📄 schemas.py             # Pydantic request/response schemas
│   │   ├── 📄 auth.py                # JWT + password utilities
│   │   ├── 📄 auth_routes.py         # Auth API endpoints
│   │   ├── 📄 routes.py              # Chat API endpoints
│   │   │
│   │   └── 📁 services/              # Business logic layer
│   │       ├── 📄 __init__.py
│   │       ├── 📄 llm_service.py     # Groq API integration
│   │       ├── 📄 domain_validator.py # Real estate query filter
│   │       └── 📄 tn_knowledge_base.py # TN real estate knowledge
│   │
│   ├── 📄 check_atlas.py             # Atlas connectivity debug
│   ├── 📄 check_users.py             # User listing debug
│   ├── 📄 debug_db.py                # DB debug utility
│   ├── 📄 test_hash.py               # Password hash test
│   ├── 📄 test_mongo_connection.py   # MongoDB test
│   ├── 📄 test_register.py           # Registration test
│   └── 📄 migrate_db.py              # Database migration script
│
└── 📁 frontend/                      # ─── REACT VITE FRONTEND ───
    ├── 📄 index.html                 # HTML entry point
    ├── 📄 package.json               # Node dependencies
    ├── 📄 vite.config.js             # Vite config + dev proxy
    ├── 📄 vercel.json                # Frontend Vercel config
    ├── 📄 .env.development           # Dev API URL
    ├── 📄 .env.production            # Prod API URL
    │
    └── 📁 src/
        ├── 📄 main.jsx               # React entry point
        ├── 📄 App.jsx                # App router + layout
        ├── 📄 App.css                # Global styles
        │
        ├── 📁 api/
        │   └── 📄 client.js          # Axios instance + auth interceptor
        │
        ├── 📁 context/
        │   ├── 📄 AuthContext.jsx     # Auth state (JWT, user, login/logout)
        │   └── 📄 ChatContext.jsx     # Chat state (history, messages)
        │
        ├── 📁 components/
        │   ├── 📄 Sidebar.jsx         # Navigation sidebar
        │   ├── 📄 ChatMessage.jsx     # Message bubble component
        │   ├── 📄 ChatInput.jsx       # Message input component
        │   ├── 📄 PremiumInput.jsx    # Enhanced input component
        │   └── 📄 AnimatedLogo.jsx    # Animated brand logo
        │
        ├── 📁 pages/
        │   ├── 📄 Login.jsx           # Login page
        │   ├── 📄 Register.jsx        # Registration page
        │   ├── 📄 Dashboard.jsx       # Dashboard page
        │   ├── 📄 AIChat.jsx          # AI Chatbot page (primary)
        │   ├── 📄 Chat.jsx            # Alternative chat page
        │   └── 📄 Properties.jsx      # Properties listing page
        │
        └── 📁 styles/
            ├── 📄 premium.css         # Main design system (27KB)
            ├── 📄 chat.css            # Chat-specific styles
            ├── 📄 auth.css            # Login/Register styles
            ├── 📄 animated-logo.css   # Logo animation styles
            └── 📄 cursor-gradient.css # Cursor effect styles
```

---

## 15. Dependency List

### Backend (Python) — `requirements.txt`
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109.0 | ASGI web framework |
| uvicorn[standard] | 0.27.0 | ASGI server |
| httpx | 0.26.0 | HTTP client (Groq API calls) |
| pydantic | 2.10.4 | Data validation |
| pydantic-settings | 2.7.1 | Environment config |
| motor | 3.6.0 | Async MongoDB driver |
| odmantic | 1.0.2 | MongoDB ODM |
| python-dotenv | 1.0.0 | .env file loading |
| langdetect | 1.0.9 | Language detection |
| python-jose[cryptography] | 3.3.0 | JWT handling |
| passlib[bcrypt] | 1.7.4 | Password hashing |
| bcrypt | 3.2.0 | Bcrypt backend |
| python-multipart | 0.0.6 | Form data parsing |
| dnspython | latest | MongoDB SRV resolution |
| certifi | latest | SSL certificates |
| gunicorn | 21.2.0 | Production WSGI server |
| email-validator | 2.1.0 | Email validation |

### Frontend (Node.js) — `package.json`
| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.2.0 | UI framework |
| react-dom | 18.2.0 | React DOM renderer |
| react-router-dom | 6.30.3 | Client routing |
| axios | 1.6.5 | HTTP client |
| lucide-react | 0.309.0 | SVG icons |
| vite | 5.0.11 | Build tool |
| @vitejs/plugin-react | 4.2.1 | React HMR plugin |

---

## 16. Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Internet connection (for MongoDB Atlas + Groq API)

### Quick Start

```bash
# 1. Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Ensure .env file has valid credentials
uvicorn main:app --reload      # → http://localhost:8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                    # → http://localhost:5173
```

### Local vs Production Environment

| Aspect | Local | Production |
|--------|-------|------------|
| Frontend URL | `http://localhost:5173` | `https://purity-prop-ai.vercel.app` |
| Backend URL | `http://localhost:8000` | `https://purityprop.onrender.com` |
| Database | MongoDB Atlas (same cloud) | MongoDB Atlas (same cloud) |
| LLM | Groq Cloud (same API) | Groq Cloud (same API) |
| Debug Mode | `True` (shows /docs) | `False` (hides /docs) |
| CORS | localhost origins | Vercel + custom domain origins |

> ⚠️ **Note:** Both local and production share the same MongoDB Atlas database and Groq API. Nothing runs purely offline on your laptop.

---

*Generated on 2026-02-20 | PurityPropAI v1.0.0*
