# ==============================================================================
# Stage 1: Build Frontend SPA
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package manifests for deterministic install and layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Install npm dependencies
RUN npm ci

# Copy frontend source files and Tailwind/Vite configs
COPY frontend/ ./

# Build production React bundle into /app/frontend/dist
RUN npm run build

# ==============================================================================
# Stage 2: Production Python 3.12 Slim Runtime
# ==============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

WORKDIR /app

# Install minimal base utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code, configs, and skill resources
COPY app/ ./app/
COPY config/ ./config/
COPY skills/ ./skills/

# Copy compiled frontend assets from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose Render PORT (default 10000)
EXPOSE 10000

# Default command: Web Service runs FastAPI via Uvicorn bound to 0.0.0.0:$PORT
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-10000}"]
