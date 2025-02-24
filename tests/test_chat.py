from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Chat, ChatCreate


def test_create_chat(client: TestClient):
    chat_data = {"title": "Test Chat", "visibility": "public"}
    response = client.post("/api/v1/chats/", json=chat_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == chat_data["title"]
    assert data["visibility"] == chat_data["visibility"]
    assert "id" in data
    assert "created_at" in data


def test_read_chats(client: TestClient, session: Session):
    # Create test chats
    chat1 = Chat(title="Test Chat 1", visibility="public")
    chat2 = Chat(title="Test Chat 2", visibility="private")
    session.add(chat1)
    session.add(chat2)
    session.commit()

    response = client.get("/api/v1/chats/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Expect exactly 2 chats
    assert data[0]["title"] == "Test Chat 1"
    assert data[1]["title"] == "Test Chat 2"


def test_read_chat(client: TestClient, session: Session):
    chat = Chat(title="Test Chat", visibility="public")
    session.add(chat)
    session.commit()

    response = client.get(f"/api/v1/chats/{chat.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Chat"
    assert data["visibility"] == "public"


def test_delete_chat(client: TestClient, session: Session):
    chat = Chat(title="Test Chat", visibility="public")
    session.add(chat)
    session.commit()

    response = client.delete(f"/api/v1/chats/{chat.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

    # Verify chat is deleted
    response = client.get(f"/api/v1/chats/{chat.id}")
    assert response.status_code == 404
