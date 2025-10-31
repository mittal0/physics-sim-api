.PHONY: help up down build test lint format clean migrate logs shell seed
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Physics Simulation API - Development Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# Docker and Docker Compose commands
up: ## Start all services with docker-compose
	@echo "$(CYAN)Starting all services...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)Services started! Check status with 'make logs'$(RESET)"

down: ## Stop all services
	@echo "$(CYAN)Stopping all services...$(RESET)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(RESET)"

build: ## Build all Docker images
	@echo "$(CYAN)Building Docker images...$(RESET)"
	docker-compose build
	docker-compose --profile build up sim-builder
	@echo "$(GREEN)Images built successfully!$(RESET)"

rebuild: ## Rebuild all images from scratch
	@echo "$(CYAN)Rebuilding all images from scratch...$(RESET)"
	docker-compose build --no-cache
	docker-compose --profile build build sim-builder --no-cache
	@echo "$(GREEN)Images rebuilt successfully!$(RESET)"

logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show logs from API service only
	docker-compose logs -f web

logs-worker: ## Show logs from worker service only
	docker-compose logs -f worker

# Database commands
migrate: ## Run database migrations
	@echo "$(CYAN)Running database migrations...$(RESET)"
	docker-compose exec web alembic upgrade head
	@echo "$(GREEN)Migrations completed!$(RESET)"

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "$(RED)Error: Please provide MESSAGE. Example: make migrate-create MESSAGE=\"add user table\"$(RESET)"; \
		exit 1; \
	fi
	docker-compose exec web alembic revision --autogenerate -m "$(MESSAGE)"

migrate-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(RESET)"
	docker-compose exec web alembic downgrade -1
	@echo "$(GREEN)Rollback completed!$(RESET)"

# Development commands
shell: ## Open a shell in the web container
	docker-compose exec web bash

shell-db: ## Open a PostgreSQL shell
	docker-compose exec db psql -U postgres -d physics_sim

shell-redis: ## Open a Redis shell
	docker-compose exec redis redis-cli

# Testing commands
test: ## Run all tests
	@echo "$(CYAN)Running all tests...$(RESET)"
	docker-compose exec web pytest tests/ -v
	@echo "$(GREEN)Tests completed!$(RESET)"

test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(RESET)"
	docker-compose exec web pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(CYAN)Running integration tests...$(RESET)"
	docker-compose exec web pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	docker-compose exec web pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(RESET)"

# Code quality commands
lint: ## Run linting (black, isort, flake8, mypy)
	@echo "$(CYAN)Running code quality checks...$(RESET)"
	docker-compose exec web black --check .
	docker-compose exec web isort --check-only .
	docker-compose exec web flake8 app sim tests
	docker-compose exec web mypy app
	@echo "$(GREEN)Linting completed!$(RESET)"

format: ## Format code with black and isort
	@echo "$(CYAN)Formatting code...$(RESET)"
	docker-compose exec web black .
	docker-compose exec web isort .
	@echo "$(GREEN)Code formatted!$(RESET)"

# Development setup commands
setup: ## Setup development environment
	@echo "$(CYAN)Setting up development environment...$(RESET)"
	cp .env.example .env
	make build
	make up
	sleep 10
	make migrate
	make seed
	@echo "$(GREEN)Development environment ready!$(RESET)"
	@echo "$(YELLOW)API available at: http://localhost:8000$(RESET)"
	@echo "$(YELLOW)API docs at: http://localhost:8000/docs$(RESET)"
	@echo "$(YELLOW)Flower at: http://localhost:5555$(RESET)"

seed: ## Seed database with sample data
	@echo "$(CYAN)Seeding database with sample data...$(RESET)"
	docker-compose exec web python scripts/seed_data.py
	@echo "$(GREEN)Database seeded!$(RESET)"

# Monitoring commands
health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@echo "API Health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "$(RED)API not responding$(RESET)"
	@echo ""
	@echo "Database:"
	@docker-compose exec db pg_isready -U postgres || echo "$(RED)Database not ready$(RESET)"
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "$(RED)Redis not responding$(RESET)"

status: ## Show status of all containers
	docker-compose ps

stats: ## Show container resource usage
	docker stats $(shell docker-compose ps -q)

# Simulation commands
test-sim: ## Test the simulation script locally
	@echo "$(CYAN)Testing simulation script...$(RESET)"
	docker run --rm -v $(PWD)/test_output:/tmp/output sim:local \
		python run_sim.py --time_steps 20 --spatial_steps 30 --end_time 0.1
	@echo "$(GREEN)Simulation test completed! Check test_output/ directory$(RESET)"

run-sim: ## Run a quick simulation test via API
	@echo "$(CYAN)Running simulation via API...$(RESET)"
	@curl -X POST "http://localhost:8000/api/v1/jobs" \
		-H "Content-Type: application/json" \
		-d '{"params": {"length": 1.0, "time_steps": 50, "diffusivity": 0.01}, "metadata": {"project": "makefile-test"}}' \
		| python -m json.tool

# Cleanup commands
clean: ## Clean up containers, volumes, and images
	@echo "$(YELLOW)Cleaning up Docker resources...$(RESET)"
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)Cleanup completed!$(RESET)"

clean-all: ## Clean up everything including images
	@echo "$(RED)Warning: This will remove ALL containers, volumes, and images!$(RESET)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v --remove-orphans --rmi all
	docker system prune -af --volumes
	@echo "$(GREEN)Complete cleanup finished!$(RESET)"

clean-artifacts: ## Clean up job artifacts
	@echo "$(CYAN)Cleaning up artifacts...$(RESET)"
	rm -rf artifacts/*
	mkdir -p artifacts
	@echo "$(GREEN)Artifacts cleaned!$(RESET)"

# Production commands
prod-up: ## Start services in production mode
	@echo "$(CYAN)Starting production services...$(RESET)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Production services started!$(RESET)"

prod-build: ## Build production images
	@echo "$(CYAN)Building production images...$(RESET)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
	@echo "$(GREEN)Production images built!$(RESET)"

# Security commands
security-check: ## Run security checks
	@echo "$(CYAN)Running security checks...$(RESET)"
	docker-compose exec web safety check
	docker-compose exec web bandit -r app/
	@echo "$(GREEN)Security checks completed!$(RESET)"

# Backup commands
backup-db: ## Backup database
	@echo "$(CYAN)Creating database backup...$(RESET)"
	docker-compose exec db pg_dump -U postgres physics_sim > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backup created!$(RESET)"

# Load testing
load-test: ## Run basic load test (requires vegeta)
	@echo "$(CYAN)Running load test...$(RESET)"
	@which vegeta > /dev/null || (echo "$(RED)vegeta not installed. Install with: go install github.com/tsenart/vegeta@latest$(RESET)" && exit 1)
	echo "GET http://localhost:8000/health" | vegeta attack -duration=30s -rate=10/s | vegeta report

# Documentation
docs: ## Generate and serve documentation
	@echo "$(CYAN)Starting documentation server...$(RESET)"
	@echo "API documentation available at: http://localhost:8000/docs"
	@echo "Press Ctrl+C to stop"
	@open http://localhost:8000/docs || true

# Environment management
env-check: ## Check environment configuration
	@echo "$(CYAN)Environment Configuration:$(RESET)"
	@echo "DATABASE_URL: $(shell grep DATABASE_URL .env 2>/dev/null || echo 'Not set')"
	@echo "REDIS_URL: $(shell grep REDIS_URL .env 2>/dev/null || echo 'Not set')"
	@echo "DEBUG: $(shell grep DEBUG .env 2>/dev/null || echo 'Not set')"
	@echo "API_PORT: $(shell grep API_PORT .env 2>/dev/null || echo 'Not set')"

# Quick development workflow
dev: ## Quick development setup (build, up, migrate)
	make build up migrate
	@echo "$(GREEN)Development environment ready!$(RESET)"

restart: ## Restart all services
	make down up

# Performance monitoring
monitor: ## Show real-time container stats
	@echo "$(CYAN)Monitoring container performance (Ctrl+C to stop)...$(RESET)"
	docker stats $(shell docker-compose ps -q) --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"