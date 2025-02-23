from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def on_startup():
    init_db()

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to RAG API",
        "version": settings.VERSION,
        "docs_url": "/docs",
    }

# Include API router
# from app.api.v1.api import api_router
# app.include_router(api_router, prefix=settings.API_V1_STR) 