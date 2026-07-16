# =============================================================
# Stage 1 — Development
#   docker compose up (uses the 'dev' target by default)
#   Hot-reload support via uvicorn --reload
# =============================================================
FROM python:3.11-slim AS dev

WORKDIR /app

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# To prevent pip from resolving NVIDIA CUDA dependencies for torch:
# We make the PyTorch CPU repository the PRIMARY index-url, and PyPI the EXTRA index-url.
# This forces pip to pull torch metadata from the CPU registry (which has no CUDA dependencies),
# while still allowing all other packages to be installed from PyPI.
RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================
# Stage 2 — Production
# =============================================================
FROM python:3.11-slim AS prod

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
