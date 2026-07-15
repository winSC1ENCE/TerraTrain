.DEFAULT_GOAL := help
SHELL         := /bin/bash
BACKEND_DIR   := apps/backend
FRONTEND_DIR  := apps/frontend

.PHONY: help setup dev dev-backend dev-frontend build down clean logs \
        pull-models-cpu pull-models-gpu pull-models-max \
        migrate migrate-new migrate-down migrate-history \
        seed ingest-papers test-ollama \
        test test-backend test-unit \
        lint format typecheck check \
        build-backend build-frontend \
        logs-backend logs-ollama logs-frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ── Bootstrap ─────────────────────────────────────────────────────────────────
setup: ## First-time setup: .env, docker services, models, migrate, seed
	@[ -f .env ] || (cp env.example .env && echo "Created .env from env.example — fill in secrets before running!")
	docker compose up -d postgres ollama
	@echo "Waiting for Ollama to be ready..."
	@until docker compose exec ollama ollama list > /dev/null 2>&1; do sleep 3; done
	$(MAKE) pull-models-gpu
	uv sync
	$(MAKE) migrate
	$(MAKE) seed
	@echo ""
	@echo "Setup complete. Run 'make dev' to start all services."

pull-models-cpu: ## Pull Ollama models for CPU / low VRAM (qwen2.5:7b)
	docker compose exec ollama ollama pull qwen2.5:7b
	docker compose exec ollama ollama pull nomic-embed-text

pull-models-gpu: ## Pull Ollama models for RTX 2080 Ti / 11 GB VRAM (qwen2.5:14b) [default]
	docker compose exec ollama ollama pull qwen2.5:14b
	docker compose exec ollama ollama pull nomic-embed-text

pull-models-max: ## Pull large Ollama models requiring 24+ GB VRAM (llama3.3:70b)
	docker compose exec ollama ollama pull llama3.3:70b
	docker compose exec ollama ollama pull nomic-embed-text

# ── Development ───────────────────────────────────────────────────────────────
dev: ## Start all services with hot reload
	docker compose up

dev-backend: ## Start backend only (postgres must be running)
	docker compose up -d postgres
	PYTHONPATH=$(BACKEND_DIR)/src uv run uvicorn terratrain.main:app \
	  --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend dev server
	cd $(FRONTEND_DIR) && npm run dev

dev-gpu: ## Start all services with GPU-enabled Ollama
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up

# ── Build ─────────────────────────────────────────────────────────────────────
build: ## Build all Docker images
	docker compose build

build-backend: ## Build backend image only
	docker compose build backend

build-frontend: ## Build frontend image only
	docker compose build frontend

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Apply all pending Alembic migrations
	PYTHONPATH=$(BACKEND_DIR)/src uv run alembic \
	  --config $(BACKEND_DIR)/alembic.ini upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="add foo table")
	@[ -n "$(MSG)" ] || (echo "Usage: make migrate-new MSG='description'" && exit 1)
	PYTHONPATH=$(BACKEND_DIR)/src uv run alembic \
	  --config $(BACKEND_DIR)/alembic.ini revision --autogenerate -m "$(MSG)"

migrate-down: ## Roll back the last migration
	PYTHONPATH=$(BACKEND_DIR)/src uv run alembic \
	  --config $(BACKEND_DIR)/alembic.ini downgrade -1

migrate-history: ## Show Alembic migration history
	PYTHONPATH=$(BACKEND_DIR)/src uv run alembic \
	  --config $(BACKEND_DIR)/alembic.ini history --verbose

# ── Data / AI ─────────────────────────────────────────────────────────────────
seed: ## Seed DB with development fixtures
	PYTHONPATH=$(BACKEND_DIR)/src uv run python scripts/seed_db.py

ingest-papers: ## Ingest PDFs from data/papers/ into pgvector
	PYTHONPATH=$(BACKEND_DIR)/src uv run python scripts/ingest_papers.py

test-ollama: ## Smoke-test Ollama connectivity and model availability
	PYTHONPATH=$(BACKEND_DIR)/src uv run python scripts/test_ollama.py

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run full test suite with coverage
	uv run pytest tests/ -v \
	  --cov=$(BACKEND_DIR)/src \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov

test-backend: ## Run all backend tests
	uv run pytest tests/backend/ -v

test-unit: ## Run unit tests only (no DB or network)
	uv run pytest tests/backend/unit/ -v

# ── Code Quality ──────────────────────────────────────────────────────────────
lint: ## Lint with ruff
	uv run ruff check $(BACKEND_DIR)/src/ tests/ scripts/

format: ## Auto-format with ruff
	uv run ruff format $(BACKEND_DIR)/src/ tests/ scripts/

typecheck: ## Type-check with mypy
	uv run mypy $(BACKEND_DIR)/src/

check: lint typecheck ## Run all static checks

# ── Docker Lifecycle ──────────────────────────────────────────────────────────
down: ## Stop all services
	docker compose down

clean: ## Stop services and remove all volumes — DESTROYS ALL DATA
	docker compose down -v
	@echo "All volumes removed."

logs: ## Follow logs for all services
	docker compose logs -f

logs-backend: ## Follow backend logs
	docker compose logs -f backend

logs-frontend: ## Follow frontend logs
	docker compose logs -f frontend

logs-ollama: ## Follow Ollama logs
	docker compose logs -f ollama
