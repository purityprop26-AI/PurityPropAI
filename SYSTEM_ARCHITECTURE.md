# PurityProp AI — Supabase-Native Real Estate Intelligence System

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PurityProp Intelligence API                       │
│                      FastAPI (Async/uvloop)                          │
├────────────┬──────────────┬──────────────┬─────────────┬────────────┤
│  /query    │  /health     │  /metrics    │ Hallucin.   │ Observ.    │
│  POST      │  GET         │  GET         │ Judge       │ Hub        │
├────────────┴──────┬───────┴──────────────┴─────────────┴────────────┤
│   Microservices   │           Groq LLM (llama-3.1)                  │
│   ┌─────────────┐ │   ┌───────────────────────────────────────┐     │
│   │ CAGR        │ │   │ Tool-Forced System Prompts            │     │
│   │ Liquidity   │ │   │ "NEVER fabricate, NEVER extrapolate"  │     │
│   │ Absorption  │ │   │ Function calling → microservices      │     │
│   │ Distance    │ │   └───────────────────────────────────────┘     │
│   │ Forecast    │ │                                                  │
│   │ Risk        │ │                                                  │
│   └─────────────┘ │                                                  │
├───────────────────┴──────────────────────────────────────────────────┤
│                 Supabase PostgreSQL (async via asyncpg)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ pgvector │  │ PostGIS  │  │ JSONB    │  │ FTS (tsvector)       │ │
│  │ HNSW     │  │ GiST     │  │ GIN      │  │ Trigram              │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd "Real Estate"
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit with your Supabase/Groq credentials

# 3. Run migrations
python db/migrate.py

# 4. Start the server
cd backend && uvicorn app.intelligence_app:app --reload

# 5. Or use Docker
docker-compose up -d
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/query` | POST | Hybrid property search with AI summary |
| `/api/v1/health` | GET | System health (DB, extensions, Groq) |
| `/api/v1/metrics` | GET | Prometheus-compatible metrics |

### Query Request

```json
POST /api/v1/query
{
    "query": "3BHK apartments in T Nagar under 80 lakhs",
    "lat": 13.04,
    "lon": 80.23,
    "radius_km": 5,
    "property_type": "apartment",
    "min_price": 5000000,
    "max_price": 8000000,
    "limit": 10
}
```

## Project Structure

```
Real Estate/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes.py           # /query, /health, /metrics
│       ├── core/
│       │   ├── config.py           # Pydantic Settings
│       │   ├── database.py         # Async SQLAlchemy + asyncpg
│       │   ├── groq_client.py      # Groq LLM with semaphore
│       │   ├── hallucination_guard.py  # Zero-hallucination enforcement
│       │   ├── models.py           # ORM models
│       │   ├── observability.py    # Metrics, tracing, monitoring
│       │   └── schemas.py          # Pydantic request/response
│       └── intelligence_app.py     # Main FastAPI entry point
├── microservices/
│   └── financial_services.py       # 6 deterministic microservices
├── db/
│   ├── migrations/
│   │   ├── 001_core_schema.sql     # Tables, types, RLS
│   │   ├── 002_indexes.sql         # HNSW, GiST, GIN, B-tree, FTS
│   │   └── 003_functions.sql       # Triggers, hybrid search
│   └── migrate.py                  # Migration runner
├── infra/
│   └── configure_db.py             # Extension setup
├── tests/
│   ├── test_phase3.py              # Async/blocking detection
│   ├── test_phase4.py              # Microservice determinism
│   ├── test_phase5.py              # Hallucination guard
│   ├── test_phase6.py              # Docker/CI-CD
│   ├── test_phase7.py              # Observability
│   └── test_phase8.py              # Integration (end-to-end)
├── cicd/
│   ├── ci.yml                      # GitHub Actions pipeline
│   └── prometheus.yml              # Prometheus config
├── state/                          # Build phase validation records
├── Dockerfile                      # Multi-stage, non-root
├── docker-compose.yml              # Orchestration
├── requirements.txt                # Python dependencies
└── SYSTEM_ARCHITECTURE.md          # This file
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Runtime | Python 3.11, FastAPI | Async API server |
| Database | Supabase PostgreSQL 15 | Primary data store |
| Vector Search | pgvector (HNSW, dim=384) | Semantic similarity |
| Spatial | PostGIS (GiST) | Location queries |
| Full-Text | PostgreSQL tsvector + trigram | Text search + fuzzy |
| LLM | Groq (llama-3.1-8b-instant) | Natural language |
| DB Driver | asyncpg + SQLAlchemy Async | Non-blocking I/O |
| Embedding | all-MiniLM-L6-v2 (384d) | Text → vector |
| Container | Docker (multi-stage) | Deployment |
| CI/CD | GitHub Actions | Automated pipeline |
| Monitoring | Prometheus + structlog | Metrics & logs |

## Microservices

All 6 services are **deterministic** — given identical inputs, they produce
identical outputs. The LLM is forbidden from computing these values.

| Service | Input | Output | Purpose |
|---------|-------|--------|---------|
| CAGR | begin, end, years | rate, percent | Growth rate |
| Liquidity | listings, sold, days, volatility | score 0-1, rating | Market health |
| Absorption | sold, months, inventory | rate, months supply | Supply/demand |
| Distance Decay | base price, landmarks | adjusted price, premium% | Location value |
| Forecast | historical prices | 6-period forecast, trend | Price prediction |
| Risk | cagr, liquidity, absorption, volatility | score 0-1, level | Investment risk |

## Hallucination Prevention

1. **Tool-Forced Prompts**: System prompt explicitly forbids LLM self-computation
2. **Function Calling**: Groq uses strict function-calling mode for all financial calculations
3. **Numeric Cross-Referencing**: Every number in LLM output is cross-checked against tool outputs
4. **Three-Tier Verdicts**: `clean` (pass) → `warning` (flag + disclaimer) → `hallucination` (reject)
5. **Response Sanitization**: Unverified claims are flagged or the entire response is rejected

## Database Schema

### Properties Table (53 columns)
- **Vector**: `embedding vector(384)` with HNSW index (inner product)
- **Spatial**: `location geometry(Point, 4326)` with GiST index
- **JSONB**: `attributes`, `amenities`, `nearby_places`, `price_history`, `images` with GIN indexes
- **FTS**: `fts_document tsvector` with GIN index
- **27 total indexes** for optimal query performance

### Database Functions
- `hybrid_property_search()` — Weighted fusion: vector + FTS + spatial
- `get_nearby_properties()` — PostGIS spatial radius query
- `generate_property_slug()` — Auto-slug trigger
- `calculate_price_per_sqft()` — Auto-compute trigger
- `update_updated_at_column()` — Auto-timestamp trigger

## Observability

- **Metrics**: Counters, gauges, histograms (P50/P95/P99) for DB, Groq, vector ops
- **Tracing**: Correlation IDs for request-level tracing
- **Monitors**: DB, Groq, Vector Search, Hallucination — all tracked
- **Prometheus**: `/api/v1/metrics` exports Prometheus text format
- **Structured Logging**: JSON logs via structlog with context binding

## Build Phases

| Phase | Name | Status | Tests |
|-------|------|--------|-------|
| 0 | Environment Validation | ✅ | Python, venv, pip, connectivity |
| 1 | Infrastructure as Code | ✅ | Extensions, config, env |
| 2 | Database Schema | ✅ | 53 columns, 27 indexes, 5 functions |
| 3 | Async Backend | ✅ | 0 blocking calls, 7 modules, async endpoints |
| 4 | Deterministic Microservices | ✅ | 6 services, 10-run determinism |
| 5 | Zero-Hallucination | ✅ | Extraction, judge, sanitizer, prompts |
| 6 | Docker / CI-CD | ✅ | Dockerfile, compose, CI pipeline |
| 7 | Observability | ✅ | Metrics, tracing, monitors, Prometheus |
| 8 | Integration Tests | ✅ | Live DB, pipeline, concurrent, triggers |
| 9 | Documentation | ✅ | This file |
