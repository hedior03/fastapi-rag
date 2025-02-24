import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from unittest.mock import MagicMock, patch
from app.core.test_config import test_settings
from app.services.chat_service import ChatService, Message, Conversation
from llama_index.core.schema import TextNode, QueryResult, NodeWithScore
from llama_index.core.llms import LLM
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import get_session
from app.models.chat import Chat

# Use PostgreSQL test database URL
TEST_DATABASE_URL = test_settings.DATABASE_URL


@pytest.fixture(autouse=True)
def clear_tables(session: Session):
    """Clear all tables before each test."""
    # Delete messages first (they reference chats)
    session.execute(text("DELETE FROM message"))
    session.execute(text("DELETE FROM chat_messages"))
    # Then delete chats
    session.execute(text("DELETE FROM chat"))
    session.commit()


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_openai_embedding():
    mock = MagicMock()
    mock.get_text_embedding.return_value = np.array([0.1] * 1536).tolist()
    return mock


@pytest.fixture
def mock_openai_chat():
    mock = MagicMock(spec=LLM)  # Use LLM spec for proper mocking
    mock.chat.return_value = "Mocked response"
    return mock


@pytest.fixture
def mock_vector_store():
    mock = MagicMock()
    mock.add.return_value = None
    # Create a mock node with score
    node = TextNode(text="test", id_="test")
    node_with_score = NodeWithScore(node=node, score=1.0)
    mock.query.return_value = [node_with_score]
    mock.as_retriever.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_session():
    mock = MagicMock()
    mock.commit.return_value = None
    mock.query.return_value.filter.return_value.first.return_value = None
    return mock


@pytest_asyncio.fixture
async def chat_service(
    mock_openai_embedding,
    mock_openai_chat,
    mock_vector_store,
):
    with (
        patch(
            "llama_index.embeddings.openai.OpenAIEmbedding",
            return_value=mock_openai_embedding,
        ),
        patch("llama_index.llms.openai.OpenAI", return_value=mock_openai_chat),
        patch(
            "llama_index.vector_stores.postgres.PGVectorStore.from_params",
            return_value=mock_vector_store,
        ),
    ):
        service = ChatService(settings_override=test_settings)
        yield service
