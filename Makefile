.PHONY: help dev dev-backend dev-frontend build up down logs test lint format type-check migrate db-reset clean

# ── Help ──
help: ## Show this help
	@echo "Aevum (薪火) OS - Development Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make dev          Start all services (Docker Compose)"
	@echo "  make dev-backend  Start backend only (with hot reload)"
	@echo "  make dev-frontend Start frontend only (with hot reload)"
	@echo "  make build        Build all Docker images"
	@echo "  make up           Start all services (background)"
	@echo "  make down         Stop all services"
	@echo "  make logs         Tail logs from all services"
	@echo ""
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters (ruff + eslint)"
	@echo "  make format       Format code (black + prettier)"
	@echo "  make type-check   Type check (mypy + tsc)"
	@echo ""
	@echo "  make migrate      Run database migrations"
	@echo "  make db-reset     Reset database (destructive!)"
	@echo "  make clean        Clean build artifacts"

# ── Docker ──
dev: ## Start all services with Docker Compose
	docker-compose up

build: ## Build all Docker images
	docker-compose build

up: ## Start all services in background
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Tail logs
	docker-compose logs -f

# ── Backend ──
dev-backend: ## Start backend with hot reload
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests
	cd backend && pytest -v --cov=app --cov-report=term-missing
	cd frontend && npm test -- --run

lint: ## Run linters
	cd backend && ruff check . && black --check .
	cd frontend && npm run lint

format: ## Format code
	cd backend && ruff format . && black .
	cd frontend && npx prettier --write .

type-check: ## Type check
	cd backend && mypy app/
	cd frontend && npx tsc --noEmit

# ── Database ──
migrate: ## Run database migrations
	cd backend && alembic upgrade head

db-reset: ## Reset database (DESTRUCTIVE!)
	cd backend && alembic downgrade base && alembic upgrade head

# ── Clean ──
clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +
	find . -type d -name .next -exec rm -rf {} +
	rm -rf backend/build backend/dist backend/*.egg-info
