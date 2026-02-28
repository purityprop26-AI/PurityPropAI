# ==============================================
# PurityProp AI — Multi-stage Production Dockerfile
#
# FIX [CRIT-D1/D2]: CMD now targets `main:app` (unified app) not
#                   `app.intelligence_app:app` (intelligence-only).
#                   This ensures Docker runs the exact same entry point
#                   as local development — auth, chat, and intelligence.
#
# FIX [HIGH-D3]:    Liveness probe uses GET / (no DB dependency, instant).
#                   Readiness probe is /api/health/db (DB-dependent, separate).
#                   Liveness must NEVER hit a DB endpoint.
# ==============================================

# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (not needed in runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL maintainer="PurityProp AI <dev@purityprop.com>"
LABEL description="PurityProp AI — Tamil Nadu Real Estate Intelligence Platform"
LABEL version="2.0.0"

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -s /bin/false appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# FIX [CRIT-D2]: Copy ALL application code — was missing backend/main.py
#                and only copying backend/app/ which excluded the unified entry point.
COPY backend/main.py ./main.py
COPY backend/app/ ./app/
COPY microservices/ ./microservices/

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# FIX [HIGH-D3]:  LIVENESS probe — fast, no DB dependency.
#                 Uses root / endpoint which returns instantly.
#                 NEVER use a DB-dependent endpoint for liveness.
#                 (If DB is slow, container should NOT be killed — it's still alive.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

EXPOSE ${PORT}

# FIX [CRIT-D1]: CMD now targets `main:app` — the unified FastAPI app.
#                Previously targeted `app.intelligence_app:app` which:
#                  - Excluded auth routes (/api/auth/me)
#                  - Excluded chat routes (/api/sessions, /api/chat)
#                  - Made Docker image functionally incomplete
#
# Worker count: 1 for free-tier Supabase (connection pool safety).
# Increase to 2 only if Supabase plan supports >60 connections.
CMD ["python", "-m", "gunicorn", "main:app", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "1", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--access-logfile", "-"]
