# ============================================================
# PromptShield Enterprise API - Multi-stage Docker build
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace definition files
COPY pyproject.toml ./
COPY packages/promptshield-core ./packages/promptshield-core
COPY packages/promptshield-config ./packages/promptshield-config
COPY apps/promptshield-enterprise-api ./apps/promptshield-enterprise-api

# Install all dependencies into a virtual environment
RUN uv sync --package promptshield-enterprise-api --no-dev

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1001 promptshield && \
    useradd --uid 1001 --gid promptshield --no-create-home promptshield

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Set path to use the venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

USER promptshield

# Run Alembic migrations, then start uvicorn
CMD ["sh", "-c", \
     "alembic -c apps/promptshield-enterprise-api/alembic.ini upgrade head && \
      uvicorn promptshield_enterprise.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers ${MAX_WORKERS:-4} \
        --log-level ${LOG_LEVEL:-info}"]
