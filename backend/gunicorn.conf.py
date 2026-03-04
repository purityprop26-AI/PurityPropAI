# Gunicorn configuration file
import os

# Use uvicorn worker for FastAPI (ASGI) application
worker_class = "uvicorn.workers.UvicornWorker"

# Gunicorn configuration for production
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Use WEB_CONCURRENCY env var if set (Render sets this), otherwise default to 1
# DO NOT use cpu_count() — Render's free tier can't handle 17 workers
workers = int(os.environ.get("WEB_CONCURRENCY", 1))

timeout = 120  # Increase timeout for long-running LLM requests
keepalive = 5  # Keep connections alive

print(f"Using worker class: {worker_class}")
print(f"Starting {workers} worker(s) on port {bind}")
