.PHONY: dev docker-up docker-down docker-build clean up down build logs test-chat

# Development server
dev:
	@echo "Setting up Python environment..."
	python3 -m venv .venv || true
	@echo "Installing requirements with uv..."
	uv venv .venv
	uv pip install -r requirements.txt
	@echo "Starting Qdrant service..."
	docker-compose up -d qdrant
	@echo "Starting FastAPI development server..."
	.venv/bin/python -m uvicorn app.main:app --reload

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
	docker-compose down -v
	rm -rf __pycache__
	rm -rf .pytest_cache
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
	@echo "  make docker-up       - Start all Docker containers"
	@echo "  make docker-down     - Stop all Docker containers"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-down-v   - Stop containers and remove volumes"
	@echo "  make clean           - Remove Python cache files"
	@echo "  make help            - Show this help message"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

test-chat:
	@echo "Creating a new chat..."
	@CHAT_ID=$$(curl -s -X POST http://localhost:8000/api/v1/chat/chats/ \
		-H "Content-Type: application/json" \
		-d '{"title": "Test Chat", "description": "Testing RAG capabilities"}' \
		| jq -r '.id') && \
	echo "Chat created with ID: $$CHAT_ID" && \
	echo "\nAdding a document..." && \
	curl -X POST http://localhost:8000/api/v1/chat/documents/ \
		-H "Content-Type: application/json" \
		-d '{"content": "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints.", "metadata": {}}' \
		| jq '.' && \
	echo "\nSending a message..." && \
	curl -X POST "http://localhost:8000/api/v1/chat/chats/$$CHAT_ID/messages/?content=What+can+you+tell+me+about+FastAPI%3F&role=user" \
		-H "Content-Type: application/json" \
		| jq '.' 