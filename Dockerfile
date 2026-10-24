# --------------------------------------------------------------------------- #
# Stage "web": build the front end with Vite.
# --------------------------------------------------------------------------- #
FROM node:22-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --------------------------------------------------------------------------- #
# Stage "app": install the Python package and serve the built front end.
# --------------------------------------------------------------------------- #
FROM python:3.11-slim AS app

# git is needed for the pulseeval git dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY trialpulse ./trialpulse
RUN pip install --no-cache-dir .

# Read-only public data and precomputed derived caches the app serves.
COPY data/raw ./data/raw
COPY data/derived ./data/derived

# Built front end from the web stage.
COPY --from=web /app/web/dist ./web/dist

# Writable audit path on Render's free tier.
ENV TP_AUDIT_PATH=/tmp/audit.sqlite3

EXPOSE 8000

CMD ["sh", "-c", "uvicorn trialpulse.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
