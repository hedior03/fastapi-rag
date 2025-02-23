# RAG API

A FastAPI-based RAG (Retrieval-Augmented Generation) API project.

## Features

- FastAPI with SQLModel integration
- Pydantic for data validation
- PostgreSQL database with Docker
- CORS middleware
- Environment variables support
- JWT authentication ready
- Alembic for database migrations

## Setup

### Local Development

1. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
uv pip install -r requirements.txt
```

3. Create a `.env` file in the root directory (optional):
```env
PROJECT_NAME=RAG API
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/rag_api
SECRET_KEY=your-secret-key-here
```

### Docker Development

1. Build and start the containers:
```bash
docker-compose up --build
```

The API will be available at http://localhost:8000, and PostgreSQL at localhost:5432

To stop the containers:
```bash
docker-compose down
```

To stop the containers and remove volumes:
```bash
docker-compose down -v
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
rag-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   └── base.py
│   ├── models/
│   ├── schemas/
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```
