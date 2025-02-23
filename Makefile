.PHONY: dev db docker-up docker-down docker-build clean

# Development server
dev:
	docker-compose up -d db
	uvicorn app.main:app --reload

# Start PostgreSQL in Docker
db:
	docker-compose up -d db

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-down-v:
	docker-compose down -v

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Help
help:
	@echo "Available commands:"
	@echo "  make dev              - Start development server with hot reload"
	@echo "  make db              - Start PostgreSQL in Docker"
	@echo "  make docker-up       - Start all Docker containers"
	@echo "  make docker-down     - Stop all Docker containers"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-down-v   - Stop containers and remove volumes"
	@echo "  make clean           - Remove Python cache files"
	@echo "  make help            - Show this help message" 