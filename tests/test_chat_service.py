import pytest
from datetime import datetime
from app.services.chat_service import ChatService, Message, Conversation


@pytest.mark.asyncio
async def test_create_conversation(chat_service):
    """Test creating a new conversation"""
    title = "Test Conversation"
    conversation = await chat_service.create_conversation(title)

    assert isinstance(conversation, Conversation)
    assert conversation.title == title
    assert isinstance(conversation.id, str)
    assert isinstance(conversation.created_at, datetime)


@pytest.mark.asyncio
async def test_add_user_message(chat_service, mock_vector_store):
    """Test adding a user message"""
    conversation_id = "1"
    content = "Hello, how are you?"

    message = await chat_service.add_message(conversation_id, content)

    assert isinstance(message, Message)
    assert message.conversation_id == conversation_id
    assert message.content.startswith("Mocked response")  # From our mock
    assert message.role == "assistant"  # We get assistant's response
    assert isinstance(message.created_at, datetime)

    # Check that vector store was called correctly
    mock_vector_store.add.assert_called()


@pytest.mark.asyncio
async def test_get_conversation_history(chat_service, mock_vector_store):
    """Test retrieving conversation history"""
    conversation_id = "1"

    # First add some messages
    await chat_service.add_message(conversation_id, "Hello")
    await chat_service.add_message(conversation_id, "How are you?")

    # Get history
    history = await chat_service.get_conversation_history(conversation_id)

    assert isinstance(history, list)
    assert len(history) > 0
    for message in history:
        assert isinstance(message, Message)
        assert message.conversation_id == conversation_id


@pytest.mark.asyncio
async def test_search_similar_messages(chat_service):
    """Test searching for similar messages"""
    query = "What is the weather like?"
    results = await chat_service.search_similar_messages(query)

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_chat_response(chat_service):
    """Test getting a chat response"""
    conversation_id = "1"
    message = "Hello, how are you?"

    response = await chat_service.chat(conversation_id, message)

    assert isinstance(response, str)
    assert response == "Mocked response"  # From our mock
