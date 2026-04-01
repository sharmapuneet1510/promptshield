# ============================================================
# PromptShield Lite - CLI tool Docker image
# ============================================================

FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy workspace files
COPY pyproject.toml ./
COPY packages/promptshield-core ./packages/promptshield-core
COPY packages/promptshield-config ./packages/promptshield-config
COPY apps/promptshield-lite ./apps/promptshield-lite

# Install promptshield-lite and its dependencies
RUN uv sync --package promptshield-lite --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default: show help
ENTRYPOINT ["promptshield"]
CMD ["--help"]
