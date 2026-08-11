# syntax=docker/dockerfile:1
# =============================================================
# Build context is TradeVision-backend/ (compose sets context: ..
# relative to this file's directory).
#
# Stage layout:
#   builder -> compiles/installs deps into /opt/venv (toolchain stays here)
#   runtime -> slim base + venv + Chromium headless shell
#   dev/prod -> thin CMD-only stages on top of runtime
# =============================================================

# =============================================================
# Stage 1: Builder — installs Python deps into a relocatable venv
# =============================================================
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Compiler toolchain lives ONLY in this stage; it never reaches the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Self-contained venv so the runtime stage can copy one directory.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt

# Install the CPU-only PyTorch wheel first so the PyPI resolver in the next
# command sees `torch` as already satisfied and never pulls the CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r /tmp/requirements.txt

# Strip build-time-only fat from site-packages (~ tens of MB, no runtime impact).
#   *.pyc/__pycache__ -> regenerated on first import in the container layer
#   torch/test, *.a   -> test binaries and static libs, unused for inference
RUN find /opt/venv -type d -name '__pycache__' -prune -exec rm -rf {} + && \
    find /opt/venv -type f -name '*.pyc' -delete && \
    find /opt/venv -type f -name '*.a' -delete && \
    rm -rf /opt/venv/lib/python3.11/site-packages/torch/test

# =============================================================
# Stage 2: Runtime base — slim image, no compiler toolchain
# =============================================================
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Install ONLY the Chromium headless shell (~262MB) instead of the default
# full Chromium + shell pair (~656MB). services/scraper.py launches with
# chromium.launch(headless=True), which resolves to the shell binary.
# If you ever need headed mode or channel="chromium", drop --only-shell.
RUN playwright install --with-deps --only-shell chromium && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /root/.cache/pip

COPY . /app

EXPOSE 8000

# =============================================================
# Stage 3: Development (target: dev) — hot reload
# =============================================================
FROM runtime AS dev

ENV NODE_ENV=development

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================
# Stage 4: Production (target: prod)
# =============================================================
FROM runtime AS prod

ENV NODE_ENV=production

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
