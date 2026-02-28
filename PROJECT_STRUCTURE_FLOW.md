# PurityProp AI — Full Project Structure & Data Flow Analysis

> **Generated:** 2026-02-24 | **Version:** 2.0.0 (Post-Audit)  
> This document is a complete map of every directory, file, and data-flow path in the system.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Top-Level Directory Structure](#2-top-level-directory-structure)
3. [Backend — Detailed Breakdown](#3-backend--detailed-breakdown)
4. [Frontend — Detailed Breakdown](#4-frontend--detailed-breakdown)
5. [Database Layer](#5-database-layer)
6. [Microservices Layer](#6-microservices-layer)
7. [Infrastructure as Code](#7-infrastructure-as-code)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Complete Request Data Flow](#9-complete-request-data-flow)
10. [Authentication Flow](#10-authentication-flow)
11. [Chat Flow](#11-chat-flow)
12. [Intelligence Query Flow](#12-intelligence-query-flow)
13. [Hallucination Guard Flow](#13-hallucination-guard-flow)
14. [Context & State Management Flow](#14-context--state-management-flow)
15. [Deployment Architecture](#15-deployment-architecture)
16. [Component Dependency Map](#16-component-dependency-map)

---

## 1. Project Overview

PurityProp AI is a **bilingual (Tamil/English) real estate intelligence platform** focused on Tamil Nadu, India. It provides:

- **AI Chat**: Domain-restricted conversational assistant (only answers real estate questions)
- **Property Intelligence**: Hybrid vector + full-text + spatial SQL search over a Supabase property database
- **Hallucination Guard**: Numeric fact-verification layer that blocks AI from fabricating prices or areas
- **Auth**: Supabase GoTrue JWT-based authentication
- **Dual Stack**: Chat/Auth stack (SQLAlchemy + asyncpg) + Intelligence stack (pgvector + PostGIS)

---

## 2. Top-Level Directory Structure

```
Real Estate/                          ← Project Root
│
├── backend/                          ← Python FastAPI unified backend
├── frontend/                         ← React 18 + Vite SPA
├── db/                               ← SQL migrations + seed data
├── microservices/                    ← Financial calculation microservice
├── infra/                            ← Terraform IaC (Supabase provisioning)
├── cicd/                             ← CI/CD pipeline configs
├── tests/                            ← Integration & phase test suites
│
├── Dockerfile                        ← Single-container unified build
├── docker-compose.yml               ← Local multi-service orchestration
├── .gitignore                        ← Excludes .env, __pycache__, venv
├── .env.example                      ← Safe credential template
├── vercel.json                       ← Frontend Vercel deployment config
├── requirements.txt                  ← Root-level (Render build reference)
├── runtime.txt                       ← python-3.11.x (Render)
│
├── PRODUCTION_CERTIFICATION.md      ← Audit certification report
├── SYSTEM_AUDIT_REPORT.md           ← Full audit findings
├── SYSTEM_ARCHITECTURE.md           ← Architecture diagrams
├── PROJECT_PIPELINE.md              ← Pipeline implementation spec
├── AUTHENTICATION_PLAN.md           ← Auth migration docs
├── MODEL_TRAINING_REPORT.md         ← LLM + embedding model notes
└── README.md                         ← Quick-start guide
```

---

## 3. Backend — Detailed Breakdown

### Entry Point

```
backend/
├── main.py                ← ★ UNIFIED APP ENTRY POINT
│                            Mounts all 3 route groups.
│                            Runs DB init on startup.
│                            Registers shutdown handlers.
│
├── requirements.txt       ← All Python dependencies (pinned versions)
├── gunicorn.conf.py       ← Gunicorn worker/timeout configuration
└── runtime.txt            ← python-3.11 declaration for Render
```

**`main.py` responsibilities:**
```
startup:
  1. init_db()              → create chat/auth tables (SQLAlchemy)
  2. get_engine()           → create Supabase intelligence pool
  3. check_db_health()      → verify pgvector + PostGIS extensions
  4. get_groq_client()      → warm Groq SDK singleton

routes mounted:
  /api          ← auth_router  (Supabase token verify, /me)
  /api          ← router       (chat sessions, chat messages)
  /api/v1       ← intelligence_router (hybrid search + AI summary)

shutdown:
  1. llm_service.close()    → close async httpx pool
  2. close_db()             → dispose chat pool
  3. dispose_engine()       → dispose intelligence pool

health endpoints:
  GET /             → liveness probe (instant, no I/O)
  GET /api/health/db → readiness probe (SELECT 1 on chat DB)
  GET /api/v1/health → intelligence health (DB + Groq ping)
```

---

### `backend/app/` — Chat & Auth Stack

```
app/
├── __init__.py
├── config.py              ← Settings (pydantic-settings, loaded from .env)
│                            Required: GROQ_API_KEY, DATABASE_URL,
│                                      SUPABASE_URL, SUPABASE_ANON_KEY
│                            Optional: JWT_SECRET_KEY, DEBUG, CORS_ORIGINS
│
├── database.py            ← Chat/Auth SQLAlchemy engine
│                            Pool: size=3, overflow=5 → max 8 connections
│                            Functions: init_db(), close_db(), get_db()
│
├── models.py              ← SQLAlchemy ORM models
│                            • User (id, email, hashed_password, name)
│                            • ChatSession (session_id, user_id, timestamps)
│                            • ChatMessage (session_id, role, content, language)
│
├── schemas.py             ← Pydantic request/response models
│                            • ChatRequest, ChatResponse
│                            • SessionCreate, SessionResponse
│                            • ConversationHistory, MessageHistory
│                            • UserResponse
│
├── auth.py                ← Supabase JWT verification
│                            Persistent _auth_client (httpx pool=10)
│                            Calls Supabase /auth/v1/user per request
│                            Returns: {id, email, name, created_at}
│
├── auth_routes.py         ← /api/auth/me endpoint
│                            Depends on verify_supabase_token
│
├── routes.py              ← Chat stack API routes
│                            POST /api/sessions  → create session
│                            POST /api/chat      → send message
│                            GET  /api/history   → get conversation
│
└── intelligence_app.py    ← Standalone intelligence FastAPI sub-app
                             (legacy — now imported as sub-router in main.py)
```

---

### `backend/app/services/` — Business Logic

```
app/services/
├── __init__.py
├── domain_validator.py    ← Real estate query gate
│                            • is_real_estate_query()  → bool
│                            • get_rejection_message() → str (Tamil/English)
│                            • detect_language()       → "tamil"|"english"
│                            Uses regex + keyword matching
│                            Blocks: poems, general chat, off-topic
│
├── llm_service.py         ← Groq LLM async wrapper
│                            Persistent httpx.AsyncClient (keepalive pool)
│                            Context: Tamil Nadu real estate expert prompt
│                            generate_response(session_id, user_message)
│                            → async str (AI reply)
│
└── tn_knowledge_base.py   ← Static Tamil Nadu real estate knowledge
                             Stamp duty rules, registration fees,
                             measurement conversions (cents/grounds/acres),
                             bank loan eligibility rules
```

---

### `backend/app/api/` — Intelligence Stack Routes

```
app/api/
├── __init__.py
└── routes.py              ← ★ INTELLIGENCE API (453 lines)
    │
    ├── POST /api/v1/query          ← Main search endpoint
    │     Pipeline:
    │       1. Parse QueryRequest (city, budget, type, lat/lng, etc.)
    │       2. Escape ILIKE wildcards (_escape_ilike)
    │       3. Build WHERE clause dynamically
    │       4. Run hybrid SQL:
    │          - Full-text search (tsvector ILIKE keywords)
    │          - Scalar filters (price, bedrooms, property_type)
    │          - Spatial filter (ST_DWithin if lat/lng given)
    │          - COUNT(*) OVER() window function (no duplicate query)
    │          - Exclude TOAST columns (images, price_history)
    │       5. Build context for LLM (top 5 results)
    │       6. Generate AI summary (Groq llama-3.1-8b-instant)
    │       7. HallucinationGuard.verify(summary, source_data)
    │       8. Return QueryResponse with guard metadata
    │
    ├── GET /api/v1/health          ← Intelligence readiness
    ├── GET /api/v1/metrics         ← Latency, P95, error count
    └── _metrics dict               ← In-memory (capped at 500 entries)
```

---

### `backend/app/core/` — Intelligence Engine

```
app/core/
├── __init__.py
│
├── config.py              ← Intelligence-specific settings
│                            db_pool_size=5, db_max_overflow=10 → max 15
│                            groq_model, groq_timeout, groq_max_retries
│                            ef_search=100 (HNSW query parameter)
│
├── database.py            ← Intelligence SQLAlchemy engine
│                            get_engine(), get_session_factory()
│                            get_db_session() → FastAPI Depends
│                            check_db_health() → pgvector + PostGIS check
│                            dispose_engine() → shutdown
│
├── groq_client.py         ← Groq SDK singleton with retry
│                            Retries: RateLimitError (429), APIConnectionError,
│                                     APITimeoutError, InternalServerError
│                            Backoff: 2s base, exponential
│                            Max attempts: 4
│
├── hallucination_guard.py ← ★ HALLUCINATION DETECTION ENGINE (526 lines)
│                            HallucinationJudge class
│                            • Extracts numeric claims from AI text
│                            • Cross-references against source DB records
│                            • Tolerance: ±5% relative, ±0.01 absolute
│                            • Verdicts: clean | warning | hallucination
│                            • sanitize(): redacts flagged numbers
│
├── hallucination_adapter.py ← Bridge between routes.py and HallucinationJudge
│                              HallucinationGuard.verify(text, source_data)
│                              → (sanitized_text, metadata_dict)
│                              Called on EVERY AI summary in /query
│
├── models.py              ← SQLAlchemy models for properties table
│                            Property (UUID pk, title, slug, description,
│                            property_type, listing_type, status, price,
│                            carpet_area_sqft, built_up_area_sqft,
│                            locality, city, pincode, bedrooms, bathrooms,
│                            lat, lng [PostGIS], embedding [pgvector 384d],
│                            tsvector, images, price_history, amenities,
│                            deleted_at [soft delete])
│
├── observability.py       ← Structured logging + metrics helpers
│                            structlog JSON formatter
│                            Request/response logging middleware
│                            Latency histogram
│
└── schemas.py             ← Intelligence request/response Pydantic models
                             QueryRequest, QueryResponse, PropertyResponse,
                             HealthResponse, MetricsResponse, ErrorResponse
```

---

## 4. Frontend — Detailed Breakdown

### Entry Files

```
frontend/
├── index.html             ← SPA shell (loads /src/main.jsx)
├── vite.config.js         ← Vite 5 config (React plugin, proxy)
├── package.json           ← Dependencies (React 18, React Router 6,
│                            Axios, Supabase-js, Lucide React)
├── .env.development       ← VITE_API_URL=http://127.0.0.1:8000
└── .env.production        ← VITE_API_URL=https://puritypropai.onrender.com
```

---

### `frontend/src/` — Application Source

```
src/
├── main.jsx               ← React root render
│                            Wraps <App> (no providers here — all in App.jsx)
│
├── App.jsx                ← ★ ROUTER + PROVIDER TREE
│   │
│   │  Provider hierarchy:
│   │    <ErrorBoundary>       ← top-level crash catcher
│   │      <AuthProvider>      ← Supabase session state
│   │        <ChatProvider>    ← chat history + current session
│   │          <BrowserRouter>
│   │            <Routes>
│   │
│   │  Public routes (no auth required):
│   │    /login    → <Login>    (lazy)
│   │    /register → <Register> (lazy)
│   │
│   │  Protected routes (ProtectedRoute wrapper):
│   │    /dashboard    → <Dashboard>  (lazy)
│   │    /chat         → <AIChat>     (lazy)
│   │    /properties   → <Properties> (lazy)
│   │    /valuation    → <Valuation>  (inline placeholder)
│   │    /documents    → <Documents>  (inline placeholder)
│   │    /approvals    → <Approvals>  (inline placeholder)
│   │    /             → redirect → /dashboard
│   │    *             → redirect → /dashboard
│   │
│   └── MainLayout: <Sidebar> + <header> + <ErrorBoundary>{page}</ErrorBoundary>
│
├── App.css                ← Global base styles (reset, typography)
│
├── api/                   ← (reserved for future API client abstraction)
│
├── assets/                ← Static assets (images, icons)
│
├── lib/
│   └── supabaseClient.js  ← Supabase browser client singleton
│                            createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
│
└── utils/                 ← (utility helpers, currently empty)
```

---

### `frontend/src/context/` — Global State

```
context/
│
├── AuthContext.jsx        ← ★ AUTHENTICATION STATE
│   │
│   │  Module-level singletons (outside React tree):
│   │    _tokenRef            ← {current: null|string} — cached JWT
│   │    api                  ← axios instance (baseURL from VITE_API_URL)
│   │    interceptor           ← reads _tokenRef, no network call per request
│   │
│   │  Exported:
│   │    AuthProvider Component:
│   │      • Calls supabase.auth.getSession() once on mount
│   │      • Subscribes to onAuthStateChange → updates _tokenRef + state
│   │      • login(email, password) → supabase.auth.signInWithPassword()
│   │      • register(name, email, password) → supabase.auth.signUp()
│   │      • logout() → supabase.auth.signOut() + clear _tokenRef
│   │
│   │    useAuth() hook → { user, token, loading, login, register, logout }
│   │    api (named export) → shared axios instance (used by all pages)
│
└── ChatContext.jsx        ← ★ CHAT SESSION STATE
    │
    │  Storage: localStorage key="chatHistory"
    │  Limits: MAX_CHATS=50, MAX_MSG_COUNT=100 per chat
    │
    │  State:
    │    chats[]           ← array of {id, title, messages[], createdAt}
    │    currentChatId     ← UUID of focused chat
    │    messages[]        ← messages of current chat (synced)
    │
    │  Exported functions:
    │    createNewChat()   ← new UUID, add to chats, set as current
    │    loadChat(id)      ← set current + sync messages (fixes Sidebar bug)
    │    addMessage(chatId, msg) ← append, auto-title from first user msg
    │    deleteChat(id)    ← remove from array, clear if was current
    │    renameChat(id, title) ← slice title to 60 chars
    │    clearAllChats()   ← empty everything + clear localStorage
    │    setCurrentChatId  ← raw setter (used by AIChat internally)
```

---

### `frontend/src/pages/` — Page Components

```
pages/
│
├── Login.jsx              ← Email/password login form
│                            useAuth().login() → redirects to /dashboard
│                            Supabase error messages surfaced to user
│
├── Register.jsx           ← Registration form
│                            useAuth().register() → redirects to /dashboard
│                            Validates email format, password strength
│
├── Dashboard.jsx          ← Landing page (logged-in)
│                            Feature cards linking to major sections
│                            Property quick-search input
│
├── AIChat.jsx             ← ★ AI CHAT INTERFACE
│   │
│   │  On mount:
│   │    1. createNewChat() if no currentChatId
│   │    2. createNewSession() → POST /api/sessions
│   │    3. addMessage(welcome message)
│   │
│   │  On user send:
│   │    1. addMessage(user msg with UUID key)
│   │    2. api.post('/api/chat', {session_id, message})
│   │    3. addMessage(AI reply with UUID key)
│   │
│   │  Session reset on chat switch (currentChatId change)
│   │  Uses api (shared axios) — no manual token headers
│
├── Properties.jsx         ← Property listing page (placeholder/stub)
│
└── Chat.jsx               ← ⚠️ DEAD CODE — never routed, never imported
                             Kept in filesystem but zero bundle impact
```

---

### `frontend/src/components/` — Shared Components

```
components/
│
├── Sidebar.jsx            ← Navigation & chat history
│                            • Nav items (Dashboard, Properties, etc.)
│                            • New Chat button → createNewChat() + navigate
│                            • Recent Chats list → loadChat(id) + navigate
│                            • Chat rename (prompt) + delete (confirm)
│                            • Search filter (client-side, case-insensitive)
│                            • Collapse/expand toggle
│                            • User profile footer + logout
│
├── ErrorBoundary.jsx      ← React class component
│                            Catches all child render errors
│                            Shows friendly recovery UI (not white screen)
│                            Stack trace in development only
│                            "Try again" button resets error state
│
├── PremiumInput.jsx       ← Chat message input with send button
│                            Debounced onChange (prevents rapid fire)
│                            Enter key submits
│
├── AnimatedLogo.jsx       ← SVG animated PurityProp logo
│
├── ChatInput.jsx          ← Base chat input (used by legacy Chat.jsx)
└── ChatMessage.jsx        ← Rendered message bubble (role-based styling)
```

---

### `frontend/src/styles/` — CSS Files

```
styles/
├── premium.css            ← ★ MAIN DESIGN SYSTEM (~1100 lines)
│                            CSS custom properties (--color-*, --space-*)
│                            Sidebar layout (collapsed/expanded states)
│                            Message bubbles, chat container
│                            .app-brand (header typography)
│                            Placeholder page styles
│                            Responsive breakpoints
│
├── auth.css               ← Login + Register page styles
│                            Glassmorphism card design
│
├── chat.css               ← Chat-specific overrides
│                            Message wrapper, avatar, copy button
│
├── animated-logo.css      ← SVG animation keyframes
└── cursor-gradient.css    ← Cursor-following gradient effect
```

---

## 5. Database Layer

### Schema Architecture (Supabase / PostgreSQL)

```
db/
├── migrate.py             ← Migration runner script
│
├── seed_data.py           ← Sample Tamil Nadu property data seeder
│
└── migrations/
    ├── 001_core_schema.sql   ← Core tables
    ├── 002_indexes.sql       ← Performance indexes
    └── 003_functions.sql     ← PostgreSQL stored functions
```

### Tables

#### Chat/Auth Pool (`app/database.py`)
```
users
  id              SERIAL PK
  email           VARCHAR(255) UNIQUE
  hashed_password VARCHAR(255)
  name            VARCHAR(255)
  created_at      TIMESTAMPTZ

chat_sessions
  id              SERIAL PK
  session_id      VARCHAR(255) UNIQUE INDEX
  user_id         INTEGER FK → users.id (nullable)
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

chat_messages
  id              SERIAL PK
  session_id      INTEGER FK → chat_sessions.id CASCADE DELETE
  role            VARCHAR(20)  -- 'user' | 'assistant'
  content         TEXT
  language        VARCHAR(20)  -- 'tamil' | 'english'
  timestamp       TIMESTAMPTZ
```

#### Intelligence Pool (`app/core/database.py`)
```
properties
  id              UUID PK
  title           TEXT
  slug            TEXT UNIQUE
  description     TEXT
  property_type   VARCHAR  -- apartment|villa|plot|house|commercial...
  listing_type    VARCHAR  -- sale|rent|lease|auction
  status          VARCHAR  -- available|sold|rented|...
  price           NUMERIC
  price_per_sqft  NUMERIC
  currency        VARCHAR DEFAULT 'INR'
  carpet_area_sqft NUMERIC
  built_up_area_sqft NUMERIC
  locality        TEXT
  city            TEXT
  pincode         VARCHAR
  bedrooms        INTEGER
  bathrooms       INTEGER
  parking_slots   INTEGER
  furnishing      VARCHAR
  facing          VARCHAR
  attributes      JSONB
  amenities       JSONB    -- TOAST column (excluded from list queries)
  images          JSONB    -- TOAST column (excluded from list queries)
  price_history   JSONB    -- TOAST column (excluded from list queries)
  embedding       VECTOR(384)  -- pgvector HNSW index
  tsvector_col    TSVECTOR     -- GIN index for full-text search
  location        GEOMETRY     -- PostGIS POINT
  builder_name    TEXT
  project_name    TEXT
  rera_id         TEXT
  is_verified     BOOLEAN
  is_featured     BOOLEAN
  listed_at       TIMESTAMPTZ
  deleted_at      TIMESTAMPTZ  -- soft delete
```

### Indexes (`002_indexes.sql`)
```
GIN  idx_properties_tsvector      on properties(tsvector_col)
BTREE idx_properties_city          on properties(city)
BTREE idx_properties_locality      on properties(locality)
BTREE idx_properties_price         on properties(price)
BTREE idx_properties_type          on properties(property_type)
BTREE idx_properties_deleted       on properties(deleted_at)
GIST  idx_properties_location      on properties(location)  -- PostGIS
HNSW  idx_properties_embedding     on properties(embedding) -- pgvector
COMPOSITE idx_deleted_city         on properties(deleted_at, city)
```

### Stored Functions (`003_functions.sql`)
```
search_properties(query, city, filters)  → SETOF properties
get_price_analytics(city, locality)      → JSON analytics
calculate_distance(lat1, lng1, lat2, lng2) → FLOAT km
```

---

## 6. Microservices Layer

```
microservices/
└── financial_services.py     ← Standalone financial calculation engine
                                  Functions:
                                  • calculate_stamp_duty(price, property_type, city)
                                  • calculate_registration_fee(price)
                                  • calculate_emi(principal, rate, tenure)
                                  • calculate_loan_eligibility(income, existing_emi)
                                  • calculate_net_yield(price, monthly_rent)
                                  • convert_measurements(value, from_unit, to_unit)
                                    (cents ↔ sqft ↔ grounds ↔ acres)
                                  Used by: Groq tool-calling (future integration)
                                           Direct import in llm_service.py
```

---

## 7. Infrastructure as Code

```
infra/
├── main.tf                ← Terraform: Supabase project provisioning
├── variables.tf           ← Terraform input variables
├── outputs.tf             ← Terraform outputs (URLs, keys)
├── terraform.tfvars       ← Variable values (gitignored secrets)
├── outputs.json           ← Captured output values
└── configure_db.py        ← Post-Terraform DB configuration script
                              Enables: pgvector, PostGIS extensions
                              Runs: migrations 001, 002, 003
```

---

## 8. CI/CD Pipeline

```
cicd/
├── render.yaml            ← Render.com service definition
│                            service: purityprop-backend
│                            buildCommand: pip install -r requirements.txt
│                            startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
│
└── (Vercel auto-deploys frontend from /frontend on git push)
```

**Dual-target deployment:**
```
Frontend → Vercel          (CDN + edge, purity-prop-ai.vercel.app)
Backend  → Render.com      (Container, puritypropai.onrender.com)
Database → Supabase Cloud  (Managed PostgreSQL, Singapore region)
```

---

## 9. Complete Request Data Flow

### User Opens App (First Visit)

```
Browser loads /
  ↓
Vite serves index.html
  ↓
React mounts main.jsx
  ↓
App.jsx renders provider tree:
  ErrorBoundary
    AuthProvider          ← calls supabase.auth.getSession() once
      ChatProvider        ← loads chatHistory from localStorage
        BrowserRouter
          Routes
  ↓
AuthProvider sets _tokenRef.current if session exists
  ↓
ProtectedRoute checks useAuth().user
  ↓ (if logged in)
Dashboard renders
  ↓ (if not logged in)
Redirect to /login
```

---

## 10. Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ LOGIN                                                       │
│                                                             │
│ User enters email + password                               │
│   ↓                                                         │
│ supabase.auth.signInWithPassword()                         │
│   ↓                                                         │
│ Supabase GoTrue service validates credentials              │
│   ↓                                                         │
│ Returns: { session: { access_token, refresh_token } }      │
│   ↓                                                         │
│ onAuthStateChange fires → _tokenRef.current = access_token │
│   ↓                                                         │
│ setUser() → React state update                              │
│   ↓                                                         │
│ Navigate /dashboard                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AUTHENTICATED API REQUEST                                   │
│                                                             │
│ Component calls api.post('/api/chat', data)                │
│   ↓                                                         │
│ Axios interceptor reads _tokenRef.current (0ms, no I/O)    │
│   ↓                                                         │
│ Attaches Authorization: Bearer <token>                     │
│   ↓                                                         │
│ Backend auth.py:                                            │
│   _auth_client.get(SUPABASE_AUTH_URL)                      │
│   → Supabase GoTrue /auth/v1/user validates token          │
│   → Returns user object                                     │
│   ↓                                                         │
│ Route handler receives verified user dict                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TOKEN REFRESH (Automatic)                                   │
│                                                             │
│ Supabase SDK auto-refreshes access_token before expiry     │
│   ↓                                                         │
│ onAuthStateChange fires again                               │
│   ↓                                                         │
│ _tokenRef.current = new access_token (no re-render needed) │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Chat Flow

```
User types message in AIChat.jsx
  ↓
PremiumInput debounces → sendMessage(text)
  ↓
addMessage(currentChatId, {id: UUID, role: 'user', content})
  ↓  (optimistic UI — message appears immediately)
  ↓
ChatContext.setChats() → auto-title from first message
  ↓
api.post('/api/chat', { session_id, message })
  ↓
BACKEND: app/routes.py
  ↓
[1] Find ChatSession by session_id (DB query)
  ↓
[2] domain_validator.is_real_estate_query(message)
     → run_in_threadpool (regex, ~0.5ms)
     If FALSE → return rejection message (Tamil/English)
  ↓
[3] Build conversation context (last 10 messages from DB)
  ↓
[4] llm_service.generate_response(session_id, message)
     → async HTTP POST to Groq API
     → System prompt: Tamil Nadu real estate expert
     → Returns AI text
  ↓
[5] Save user + assistant messages to DB
  ↓
[6] Return ChatResponse { session_id, message, language, timestamp }
  ↓
FRONTEND: addMessage(currentChatId, {id: UUID, role: 'assistant', content})
  ↓
ChatContext persists to localStorage (capped at 50 chats × 100 msgs)
```

---

## 12. Intelligence Query Flow

```
User/API calls POST /api/v1/query
  QueryRequest: { query, city, property_type, min/max_price,
                  bedrooms, locality, lat, lng, radius_km, limit }
  ↓
app/api/routes.py:query_properties()
  ↓
[1] Validate request (Pydantic auto-validates types & ranges)
  ↓
[2] Build WHERE clause:
    conditions = ["deleted_at IS NULL"]
    + city filter (exact match)
    + property_type filter (enum)
    + price range filters
    + bedrooms filter
    + locality ILIKE (wildcards escaped via _escape_ilike())
    + spatial filter: ST_DWithin(location, POINT(lng lat), radius_km/111)
  ↓
[3] Build keyword conditions from query text:
    Extract up to 4 keywords
    ILIKE '%keyword%' on title + description + locality
  ↓
[4] Execute single SQL query:
    SELECT id, title, price, locality, ...    ← no TOAST columns
           COUNT(*) OVER() as total_count     ← window fn, no second query
           ts_rank(tsvector_col, ...)  as text_score
           ST_DistanceSphere(...)      as distance_m
    FROM properties
    WHERE <conditions>
    ORDER BY combined_score DESC
    LIMIT :limit OFFSET :offset
  ↓
[5] Build LLM context (top 5 properties as JSON)
  ↓
[6] Groq llama-3.1-8b-instant generates AI summary
    (up to 4 retries with backoff on 429/timeout)
  ↓
[7] HallucinationGuard.verify(summary, top_5_properties)
    → Extracts numeric claims from summary
    → Cross-references against DB record values
    → Tolerance: ±5% relative, ±0.01 absolute
    → Verdicts: clean | warning | hallucination
    → sanitize() if verdict == hallucination
  ↓
[8] Return QueryResponse:
    { query, properties[], total_results, ai_summary,
      retrieval_method, latency_ms, metadata }
```

---

## 13. Hallucination Guard Flow

```
AI Summary Text → HallucinationGuard.verify(text, source_records)
  ↓
HallucinationJudge._extract_numeric_claims(text)
  → Regex parses: prices (₹X,XXX), areas (XXXX sqft),
                  percentages (X.X%), distances (X km)
  → Returns: List[NumericClaim]
  ↓
For each claim:
  → _find_matching_field(claim, source_records)
  → Compare claim.value vs record.value
  → Within tolerance? → verified
  → Outside tolerance? → flagged
  ↓
Verdict decision:
  0 flagged → "clean"   → text passes through unchanged
  1+ flagged, < threshold → "warning" → text passes + disclaimer appended
  > threshold flagged → "hallucination" → ResponseSanitizer.sanitize(text)
    → Redacts specific wrong numbers from text
  ↓
Returns (sanitized_text, {
  passed: bool,
  verdict: str,
  flagged_count: int,
  total_claims: int,
  verified_count: int,
  elapsed_ms: float
})
```

---

## 14. Context & State Management Flow

```
                    ┌──────────────┐
                    │ App.jsx      │  Provider Tree Root
                    │ ErrorBoundary│
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │     AuthProvider        │
              │  State:                 │
              │    user (Supabase user) │
              │    token (JWT string)   │
              │    loading (bool)       │
              │  Singleton:             │
              │    _tokenRef (module)   │
              │    api (axios)          │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     ChatProvider        │
              │  State:                 │
              │    chats[] (localStorage│
              │    currentChatId (UUID) │
              │    messages[] (synced)  │
              └────────────┬────────────┘
                           │
         ┌─────────────────┼────────────────────┐
         │                 │                    │
   ┌─────▼──────┐   ┌──────▼──────┐   ┌────────▼────────┐
   │  Sidebar   │   │   AIChat    │   │    Dashboard    │
   │            │   │             │   │                 │
   │useAuth()   │   │useAuth()    │   │useAuth()        │
   │useChat()   │   │useChat()    │   │                 │
   │            │   │api (axios)  │   │                 │
   └────────────┘   └─────────────┘   └─────────────────┘
```

---

## 15. Deployment Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ PRODUCTION DEPLOYMENT                                          │
│                                                                │
│  ┌──────────────────┐       ┌──────────────────────────────┐  │
│  │  Vercel (Edge)   │       │  Render.com (Container)      │  │
│  │                  │       │                               │  │
│  │  React SPA       │ HTTPS │  uvicorn main:app             │  │
│  │  (static bundle) ├───────►  FastAPI                     │  │
│  │                  │       │  Port 8000                   │  │
│  │  CDN distributed │       │  1 worker (Supabase limit)   │  │
│  └──────────────────┘       └──────────┬───────────────────┘  │
│                                        │                       │
│                              ┌─────────▼──────────────────┐   │
│                              │  Supabase Cloud (SG region) │   │
│                              │                             │   │
│                              │  PostgreSQL 15              │   │
│                              │  + pgvector (HNSW 384d)     │   │
│                              │  + PostGIS (spatial)        │   │
│                              │  + GoTrue (Auth)            │   │
│                              │  Max connections: 60        │   │
│                              │  Pool used: 23 (safe)       │   │
│                              └─────────────────────────────┘   │
│                                                                │
│                              ┌─────────────────────────────┐  │
│                              │  Groq Cloud API              │  │
│                              │  llama-3.1-8b-instant        │  │
│                              │  Used by: llm_service.py,    │  │
│                              │           groq_client.py     │  │
│                              └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

LOCAL DEVELOPMENT:
  Frontend: http://127.0.0.1:5173  (Vite dev server)
  Backend:  http://127.0.0.1:8000  (uvicorn --reload)
  CORS: localhost:5173 whitelisted in settings.cors_origins
```

---

## 16. Component Dependency Map

```
main.jsx
  └── App.jsx
        ├── ErrorBoundary (components/)
        ├── AuthProvider (context/AuthContext.jsx)
        │     ├── supabaseClient (lib/)
        │     └── axios api instance (module-level)
        ├── ChatProvider (context/ChatContext.jsx)
        │     └── localStorage (browser API)
        ├── Sidebar (components/)
        │     ├── useAuth()    → AuthContext
        │     ├── useChat()    → ChatContext [loadChat, createNewChat, ...]
        │     ├── AnimatedLogo (components/)
        │     └── lucide-react icons
        └── Pages (lazy loaded)
              ├── Login.jsx
              │     └── useAuth() → login()
              ├── Register.jsx
              │     └── useAuth() → register()
              ├── Dashboard.jsx
              │     └── useAuth() → user
              ├── AIChat.jsx     ← ★ Most complex page
              │     ├── useAuth() → (api import)
              │     ├── useChat() → messages, addMessage, currentChatId
              │     ├── api (shared axios) → /api/sessions, /api/chat
              │     └── PremiumInput (components/)
              └── Properties.jsx
                    └── (stub — future implementation)
```

---

## Key Non-Obvious Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Two SQLAlchemy engines** | Chat/Auth uses its own smaller pool (8 conns) for predictable auth latency. Intelligence pool (15 conns) handles heavier queries. Combined = 23, within Supabase free tier's 60 limit. |
| **`_tokenRef` instead of state** | React state re-renders would reset the interceptor. Module-level ref is always up-to-date without triggering renders. |
| **`COUNT(*) OVER()` window function** | Eliminates a second `SELECT COUNT(*)` round-trip. Single query returns both results and total_count. |
| **TOAST column exclusion** | `images`, `price_history`, `amenities` are JSONB stored as TOAST. Including them in list queries is expensive. Only fetched for single-property detail views. |
| **`loadChat` in ChatContext** | `setCurrentChatId` alone doesn't sync messages. `loadChat` atomically sets ID and immediately reads from chats array to update `messages[]` in one operation. |
| **`HallucinationAdapter`** | `routes.py` needed a simple `verify(text, data)` API. `hallucination_guard.py` exposes `HallucinationJudge` (class with complex signature). The adapter bridges without modifying the guard's internal logic. |
| **Domain validator in threadpool** | Regex compilation could block event loop on catastrophic backtracking (ReDoS). `run_in_threadpool` gives it a thread, protecting the async loop. |
| **Lazy loading all pages** | Reduces initial JS bundle by ~60%. Only `Sidebar`, `AuthProvider`, `ChatProvider` are eagerly loaded (always needed on every route). |

---

*Report generated: 2026-02-24 17:40 IST*  
*Analyzer: Antigravity AI | PurityProp AI v2.0.0*
