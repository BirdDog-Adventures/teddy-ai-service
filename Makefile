.PHONY: help install dev-install test lint format run docker-build docker-up docker-down clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting"
	@echo "  make format       - Format code with black"
	@echo "  make run          - Run the service locally"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start services with Docker Compose"
	@echo "  make docker-down  - Stop Docker Compose services"
	@echo "  make clean        - Clean up cache files"

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
dev-install:
	pip install -r requirements.txt
	pre-commit install

# Run tests
test:
	pytest tests/ -v --cov=api --cov=services --cov=ml_models --cov-report=html

# Run linting
lint:
	flake8 api/ services/ ml_models/ data_connectors/ utils/
	mypy api/ services/ ml_models/ data_connectors/ utils/

# Format code
format:
	black api/ services/ ml_models/ data_connectors/ utils/ tests/

# Run the service locally
run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Build Docker images
docker-build:
	docker-compose build

# Start Docker Compose services
docker-up:
	docker-compose up -d

# Stop Docker Compose services
docker-down:
	docker-compose down

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Database migrations
migrate:
	alembic upgrade head

# Create a new migration
migration:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# Rollback migration
rollback:
	alembic downgrade -1

# Initialize database
init-db:
	python scripts/init_db.py

# Generate API documentation
docs:
	mkdocs serve

# Build documentation
docs-build:
	mkdocs build

# Run Celery worker
celery-worker:
	celery -A services.celery_app worker --loglevel=info

# Run Celery beat
celery-beat:
	celery -A services.celery_app beat --loglevel=info

# Run Flower for Celery monitoring
flower:
	celery -A services.celery_app flower

# Check code quality
quality:
	@echo "Running code quality checks..."
	@make lint
	@make test
	@echo "Code quality checks passed!"

# Development setup
dev-setup:
	@echo "Setting up development environment..."
	@make dev-install
	@cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Development setup complete!"
