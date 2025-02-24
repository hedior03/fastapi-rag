import pytest
import httpx
import time
from typing import Generator

BASE_URL = "http://localhost:8000/api/v1/chat"
TEST_TIMEOUT = 30  # seconds

def wait_for_services():
    """Wait for services to be ready."""
    start_time = time.time()
    while True:
        try:
            # Check FastAPI
            response = httpx.get(f"{BASE_URL.replace('/api/v1/chat', '')}/docs")
            if response.status_code == 200:
                # Check Qdrant
                response = httpx.get("http://localhost:6333")
                if response.status_code in [200, 404]:  # 404 is fine, means Qdrant is up but endpoint not found
                    return
        except Exception:
            if time.time() - start_time > TEST_TIMEOUT:
                pytest.fail("Services did not start within timeout")
            time.sleep(1)

@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    """Ensure all required services are running."""
    wait_for_services()

@pytest.fixture
def client() -> Generator[httpx.Client, None, None]:
    """Create a test client."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client

def test_create_chat(client: httpx.Client):
    """Test chat creation."""
    response = client.post(
        "/chats/",
        json={"title": "Test Chat", "description": "E2E Test Chat"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Chat"
    assert data["description"] == "E2E Test Chat"
    return data["id"]

def test_list_chats(client: httpx.Client):
    """Test chat listing."""
    response = client.get("/chats/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in chat for chat in data)

def test_add_document(client: httpx.Client):
    """Test document addition."""
    response = client.post(
        "/documents/",
        json={
            "content": "FastAPI is a modern web framework for building APIs.",
            "metadata": {"test": "e2e", "type": "framework"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["content"] == "FastAPI is a modern web framework for building APIs."
    assert data["metadata"] == {"test": "e2e", "type": "framework"}
    return data["id"]

def test_update_document(client: httpx.Client):
    """Test document update."""
    doc_id = test_add_document(client)
    response = client.put(
        f"/documents/{doc_id}",
        json={
            "content": "FastAPI is a modern web framework for building high-performance APIs.",
            "metadata": {"test": "e2e", "type": "framework", "updated": True}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert "high-performance" in data["content"]
    assert data["metadata"]["updated"] is True

def test_search_documents(client: httpx.Client):
    """Test document search."""
    response = client.get("/documents/search/", params={"query": "high-performance framework"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in doc for doc in data)

def test_list_documents(client: httpx.Client):
    """Test document listing."""
    response = client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in doc for doc in data)

def test_delete_document(client: httpx.Client):
    """Test document deletion."""
    doc_id = test_add_document(client)
    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document deleted successfully"

    # Verify deletion
    response = client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    assert all(doc["id"] != doc_id for doc in data)

def test_chat_conversation(client: httpx.Client):
    """Test a complete chat conversation."""
    # Create chat
    chat_id = test_create_chat(client)

    # Add a document for context
    client.post(
        "/documents/",
        json={
            "content": "FastAPI is a modern web framework with excellent performance.",
            "metadata": {"test": "e2e", "type": "framework"}
        }
    )

    # Send message
    response = client.post(
        f"/chats/{chat_id}/messages/",
        params={"content": "What can you tell me about FastAPI's performance?", "role": "user"}
    )
    assert response.status_code == 200
    message_data = response.json()
    assert message_data["role"] == "user"

    # Get chat messages
    time.sleep(2)  # Wait for AI response
    response = client.get(f"/chats/{chat_id}/messages/")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) >= 2  # User message + AI response
    assert any(msg["role"] == "assistant" for msg in messages)

def test_invalid_chat(client: httpx.Client):
    """Test invalid chat operations."""
    response = client.get("/chats/invalid-id/messages/")
    assert response.status_code == 404

def test_invalid_document(client: httpx.Client):
    """Test invalid document operations."""
    response = client.put(
        "/documents/invalid-id",
        json={
            "content": "This should fail",
            "metadata": {}
        }
    )
    assert response.status_code == 404 