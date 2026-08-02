# syntax=docker/dockerfile:1
# =============================================================
# Base Stage: Python runtime & core setup
# =============================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# STEP 1: Copy ONLY requirements.txt from context root
COPY requirements.txt /app/requirements.txt

# STEP 2: Install PyTorch CPU first, followed by remaining requirements
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    playwright install --with-deps chromium

# STEP 3: Copy remaining source code
COPY . /app

# =============================================================
# Stage 1: Development Environment (target: dev)
# =============================================================
FROM base AS dev

ENV NODE_ENV=development
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================
# Stage 2: Production Environment (target: prod)
# =============================================================
FROM base AS prod

ENV NODE_ENV=production
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]