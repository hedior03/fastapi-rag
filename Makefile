.PHONY: dev docker-up docker-down docker-build clean up down build logs test-chat test-documents test-all wait-for-services

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

# Wait for services
wait-for-services:
	@echo "Waiting for services to be ready..."
	@timeout=30; \
	while ! curl -s http://localhost:8000/docs > /dev/null; do \
		if [ $$timeout -le 0 ]; then \
			echo "Timeout waiting for FastAPI server"; \
			exit 1; \
		fi; \
		echo "Waiting for FastAPI server... $$timeout seconds remaining"; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done
	@timeout=30; \
	while ! curl -s http://localhost:6333 > /dev/null; do \
		if [ $$timeout -le 0 ]; then \
			echo "Timeout waiting for Qdrant"; \
			exit 1; \
		fi; \
		echo "Waiting for Qdrant... $$timeout seconds remaining"; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done
	@echo "All services are ready!"

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
	@echo "  make test-chat       - Run chat functionality tests"
	@echo "  make test-documents  - Run document management tests"
	@echo "  make test-all        - Run all tests"
	@echo "  make help            - Show this help message"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

test-chat: wait-for-services
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
		| jq '.' && \
	echo "\nGetting chat messages (including AI response)..." && \
	sleep 2 && \
	curl -s "http://localhost:8000/api/v1/chat/chats/$$CHAT_ID/messages/" \
		-H "Content-Type: application/json" \
		| jq '.'

test-documents: wait-for-services
	@echo "1. Testing document creation..."
	@DOC_ID=$$(curl -s -X POST http://localhost:8000/api/v1/chat/documents/ \
		-H "Content-Type: application/json" \
		-d '{"content": "FastAPI is a modern web framework for building APIs.", "metadata": {"category": "framework", "language": "Python"}}' \
		| jq -r '.id') && \
	echo "\nDocument created with ID: $$DOC_ID" && \
	echo "\n2. Testing document update..." && \
	curl -X PUT "http://localhost:8000/api/v1/chat/documents/$$DOC_ID" \
		-H "Content-Type: application/json" \
		-d '{"content": "FastAPI is a modern web framework for building high-performance APIs.", "metadata": {"category": "framework", "language": "Python", "performance": "high"}}' \
		| jq '.' && \
	echo "\n3. Testing document search..." && \
	curl -s "http://localhost:8000/api/v1/chat/documents/search/?query=high+performance+framework" \
		-H "Content-Type: application/json" \
		| jq '.' && \
	echo "\n4. Testing document listing..." && \
	curl -s http://localhost:8000/api/v1/chat/documents/ \
		-H "Content-Type: application/json" \
		| jq '.' && \
	echo "\n5. Testing document deletion..." && \
	curl -X DELETE "http://localhost:8000/api/v1/chat/documents/$$DOC_ID" \
		-H "Content-Type: application/json" \
		| jq '.' && \
	echo "\n6. Verifying deletion..." && \
	curl -s http://localhost:8000/api/v1/chat/documents/ \
		-H "Content-Type: application/json" \
		| jq '.'

test-all: wait-for-services test-chat test-documents 