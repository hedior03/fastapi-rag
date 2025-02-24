import pytest
import docker
from typing import Generator
import time
from app.services.chat_service import ChatService
from app.models import ChatCreate, MessageCreate, DocumentCreate
from app.core.test_config import test_settings
from tests.utils import create_test_chat, create_test_message, create_test_document
from datetime import datetime, timedelta
import os


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    return docker.from_env()


def is_qdrant_ready(container) -> bool:
    """Check if Qdrant container is ready to accept connections."""
    try:
        logs = container.logs().decode("utf-8")
        return "Qdrant is ready to accept connections" in logs
    except Exception:
        return False


@pytest.fixture(scope="session")
def qdrant_container() -> Generator[docker.models.containers.Container, None, None]:
    """Start a Qdrant container for testing."""
    client = docker.from_env()

    # Pull the Qdrant image
    client.images.pull("qdrant/qdrant:latest")

    # Create and start the container
    container = client.containers.run(
        "qdrant/qdrant:latest",
        ports={
            "6333/tcp": test_settings.QDRANT_PORT,  # Map container's 6333 to host's 6334
            "6334/tcp": test_settings.QDRANT_PORT
            + 1,  # Map container's 6334 to host's 6335
        },
        detach=True,
        remove=True,
    )

    # Wait for Qdrant to be ready
    start_time = datetime.now()
    while not is_qdrant_ready(container):
        time.sleep(1)  # Add a small delay to avoid busy waiting
        if datetime.now() - start_time > timedelta(seconds=30):
            container.stop()
            raise TimeoutError("Qdrant container failed to start within 30 seconds")

    yield container

    # Cleanup
    container.stop()


@pytest.fixture
async def chat_service(qdrant_container) -> ChatService:
    """Create a ChatService instance connected to the test Qdrant container."""
    # Ensure OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set")

    service = ChatService()
    yield service


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_rag_flow(chat_service):
    """Test the complete RAG flow with a real Qdrant instance."""
    # 1. Create a new chat
    chat = await chat_service.create_chat(
        title="Integration Test Chat", description="Testing the complete RAG flow"
    )
    assert chat["title"] == "Integration Test Chat"

    # 2. Process some test documents
    doc1 = await chat_service.process_document(
        content="Python is a high-level programming language known for its simplicity and readability.",
        metadata={"source": "test", "topic": "python"},
    )
    doc2 = await chat_service.process_document(
        content="FastAPI is a modern web framework for building APIs with Python.",
        metadata={"source": "test", "topic": "fastapi"},
    )

    assert doc1["content"] and doc2["content"]

    # 3. Search for documents
    results = await chat_service.search_documents("python programming")
    assert len(results) > 0
    assert any("Python" in result["content"] for result in results)

    # 4. Process a message that should trigger RAG
    response = await chat_service.process_message(
        chat_id=chat["id"], content="What can you tell me about Python?", role="user"
    )

    assert response["role"] == "assistant"
    assert response["chat_id"] == chat["id"]
    assert len(response["content"]) > 0

    # 5. Verify chat history
    messages = await chat_service.get_chat_messages(chat["id"])
    assert len(messages) >= 2  # User question + Assistant response

    # Verify message order and content
    user_messages = [m for m in messages if m["role"] == "user"]
    assistant_messages = [m for m in messages if m["role"] == "assistant"]

    assert len(user_messages) > 0
    assert len(assistant_messages) > 0
    assert "Python" in user_messages[0]["content"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_search_relevance(chat_service):
    """Test that document search returns relevant results."""
    # Add documents with distinct topics
    docs = [
        ("Python is great for data science and machine learning.", {"topic": "python"}),
        ("JavaScript is essential for web development.", {"topic": "javascript"}),
        ("Docker helps with containerization and deployment.", {"topic": "docker"}),
    ]

    for content, metadata in docs:
        await chat_service.process_document(content=content, metadata=metadata)

    # Search for Python-related content
    python_results = await chat_service.search_documents("python data science")
    assert len(python_results) > 0
    assert any("Python" in result["content"] for result in python_results)

    # Search for web development content
    web_results = await chat_service.search_documents("web development javascript")
    assert len(web_results) > 0
    assert any("JavaScript" in result["content"] for result in web_results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_context_maintenance(chat_service):
    """Test that the chat maintains context across multiple messages."""
    # Create a new chat
    chat = await chat_service.create_chat(
        title="Context Test Chat", description="Testing context maintenance"
    )

    # Add relevant documents
    await chat_service.process_document(
        content="FastAPI is a modern Python web framework.",
        metadata={"topic": "fastapi"},
    )

    # Send a sequence of related messages
    messages = [
        "What is FastAPI?",
        "What makes it modern?",
        "How does it compare to other frameworks?",
    ]

    previous_response = None
    for message in messages:
        response = await chat_service.process_message(
            chat_id=chat["id"], content=message, role="user"
        )

        assert response["role"] == "assistant"
        assert len(response["content"]) > 0

        if previous_response:
            # Verify that responses are different
            assert response["content"] != previous_response["content"]

        previous_response = response

    # Verify chat history maintains all messages in order
    chat_messages = await chat_service.get_chat_messages(chat["id"])
    assert (
        len(chat_messages) >= len(messages) * 2
    )  # User messages + Assistant responses
