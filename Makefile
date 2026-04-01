.PHONY: install test lint format dev-lite dev-enterprise docker-up docker-down clean help

# Default target
help:
	@echo "PromptShield Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install          Install all workspace packages with uv"
	@echo "  test             Run all tests"
	@echo "  lint             Run ruff linter"
	@echo "  format           Run ruff formatter"
	@echo "  dev-lite         Run PromptShield Lite CLI"
	@echo "  dev-enterprise   Start Enterprise API with hot-reload"
	@echo "  docker-up        Start all Docker services"
	@echo "  docker-down      Stop all Docker services"
	@echo "  clean            Remove __pycache__, .pyc, dist files"

install:
	uv sync --all-packages

test:
	uv run pytest packages/ apps/promptshield-enterprise-api/tests/ -v --tb=short

test-cov:
	uv run pytest packages/ apps/promptshield-enterprise-api/tests/ -v --cov=. --cov-report=html

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy packages/promptshield-core/promptshield_core packages/promptshield-config/promptshield_config

dev-lite:
	uv run --package promptshield-lite promptshield --help

dev-enterprise:
	uv run --package promptshield-enterprise-api uvicorn promptshield_enterprise.main:app --reload --port 8000 --host 0.0.0.0

docker-up:
	docker compose -f deploy/compose/docker-compose.yml up -d

docker-down:
	docker compose -f deploy/compose/docker-compose.yml down

docker-logs:
	docker compose -f deploy/compose/docker-compose.yml logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleaned up."
