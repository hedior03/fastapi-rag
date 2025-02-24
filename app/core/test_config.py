from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Test settings with a separate Qdrant instance for testing."""

    PROJECT_NAME: str = "RAG API Test"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6334  # Different port for test instance
    OPENAI_API_KEY: str = "test-api-key"  # Mock API key for testing

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create test settings instance
test_settings = TestSettings()

# Override the main settings for tests
from app.core.config import settings

for key, value in test_settings.model_dump().items():
    setattr(settings, key, value)
