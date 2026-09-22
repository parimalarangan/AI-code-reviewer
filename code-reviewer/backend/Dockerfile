# syntax=docker/dockerfile:1

# ---- Base image -------------------------------------------------------------
# Slim image keeps the final container small while still being a full
# Debian-based Python environment (needed because bandit/pylint/radon are
# pure-Python and install cleanly here).
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr — both
# make container logs and debugging noticeably nicer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (separate layer) so Docker can cache this step
# and only re-run `pip install` when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code.
COPY app ./app

# Run as a non-root user for basic container security hygiene.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Basic container health check hitting our own /api/health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
