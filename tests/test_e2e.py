import pytest
import httpx
import time
from typing import Generator, Tuple

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

@pytest.fixture(autouse=True)
def cleanup_documents(client: httpx.Client):
    """Clean up all documents before and after each test."""
    # Clean up before test
    response = client.get("/documents/")
    if response.status_code == 200:
        for doc in response.json():
            client.delete(f"/documents/{doc['id']}")
    
    yield
    
    # Clean up after test
    response = client.get("/documents/")
    if response.status_code == 200:
        for doc in response.json():
            client.delete(f"/documents/{doc['id']}")

@pytest.fixture
def test_chat(client: httpx.Client) -> str:
    """Create a test chat and return its ID."""
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

@pytest.fixture
def test_document(client: httpx.Client) -> Tuple[str, str]:
    """Create a test document and return its ID and content."""
    content = "FastAPI is a modern web framework for building high-performance APIs."
    response = client.post(
        "/documents/",
        json={
            "content": content,
            "metadata": {"test": "e2e", "type": "framework"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["content"] == content
    return data["id"], content

def test_create_chat(test_chat: str):
    """Test chat creation."""
    assert test_chat is not None and len(test_chat) > 0

def test_list_chats(client: httpx.Client, test_chat: str):
    """Test chat listing."""
    response = client.get("/chats/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in chat for chat in data)
    assert any(chat["id"] == test_chat for chat in data)

def test_add_document(test_document: Tuple[str, str]):
    """Test document addition."""
    doc_id, content = test_document
    assert doc_id is not None and len(doc_id) > 0
    assert content is not None and len(content) > 0

def test_update_document(client: httpx.Client, test_document: Tuple[str, str]):
    """Test document update."""
    doc_id, _ = test_document
    new_content = "FastAPI is a modern web framework for building blazing-fast APIs."
    response = client.put(
        f"/documents/{doc_id}",
        json={
            "content": new_content,
            "metadata": {"test": "e2e", "type": "framework", "updated": True}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["content"] == new_content
    assert data["metadata"]["updated"] is True

def test_search_documents(client: httpx.Client, test_document: Tuple[str, str]):
    """Test document search."""
    doc_id, content = test_document
    print(f"\nTesting search with document ID: {doc_id}")
    print(f"Document content: {content}")
    
    # Give the index a moment to update
    time.sleep(2)  # Increased wait time
    
    # Search for exact content
    print("\nSearching for exact content...")
    response = client.get("/documents/search/", params={"query": content})
    assert response.status_code == 200
    data = response.json()
    print(f"Search response: {data}")
    assert isinstance(data, list)
    assert len(data) > 0, "No documents found in search results"
    assert any(doc["id"] == doc_id for doc in data), f"Expected document {doc_id} not found in results"
    
    # Search for partial content
    print("\nSearching for partial content...")
    response = client.get("/documents/search/", params={"query": "modern web framework"})
    assert response.status_code == 200
    data = response.json()
    print(f"Search response: {data}")
    assert isinstance(data, list)
    assert len(data) > 0, "No documents found in search results"
    assert any(doc["id"] == doc_id for doc in data), f"Expected document {doc_id} not found in results"

def test_list_documents(client: httpx.Client, test_document: Tuple[str, str]):
    """Test document listing."""
    doc_id, _ = test_document
    response = client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("id" in doc for doc in data)
    assert any(doc["id"] == doc_id for doc in data)

def test_delete_document(client: httpx.Client, test_document: Tuple[str, str]):
    """Test document deletion."""
    doc_id, _ = test_document
    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document deleted successfully"

    # Verify deletion
    response = client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    assert all(doc["id"] != doc_id for doc in data)

def test_chat_conversation(client: httpx.Client, test_chat: str, test_document: Tuple[str, str]):
    """Test a complete chat conversation."""
    # Send message
    response = client.post(
        f"/chats/{test_chat}/messages/",
        params={"content": "What can you tell me about FastAPI's performance?", "role": "user"}
    )
    assert response.status_code == 200
    message_data = response.json()
    assert message_data["role"] == "user"

    # Get chat messages
    time.sleep(2)  # Wait for AI response
    response = client.get(f"/chats/{test_chat}/messages/")
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