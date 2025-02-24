from fastapi import APIRouter, HTTPException
from typing import List
from app.services.chat_service import ChatService
from app.models import (
    ChatCreate,
    ChatRead,
    MessageCreate,
    MessageRead,
    DocumentCreate,
    DocumentRead,
)

router = APIRouter()
chat_service = ChatService()


# Chat endpoints
@router.post("/chats/", response_model=ChatRead)
async def create_chat(chat: ChatCreate):
    """Create a new chat."""
    try:
        return await chat_service.create_chat(chat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/", response_model=List[ChatRead])
async def list_chats():
    """List all chats."""
    try:
        return await chat_service.list_chats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/messages/", response_model=List[MessageRead])
async def get_chat_messages(chat_id: str):
    """Get all messages in a chat."""
    try:
        return await chat_service.get_chat_messages(chat_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/chats/{chat_id}/messages/", response_model=MessageRead)
async def add_message(chat_id: str, content: str, role: str = "user"):
    """Add a message to a chat and get AI response."""
    try:
        message = MessageCreate(content=content, role=role, chat_id=chat_id)
        return await chat_service.add_message(message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Document endpoints
@router.post("/documents/", response_model=DocumentRead)
async def add_document(document: DocumentCreate):
    """Add a document to the RAG system."""
    try:
        return await chat_service.add_document(document)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents/", response_model=List[DocumentRead])
async def list_documents():
    """List all documents."""
    try:
        return await chat_service.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/search/", response_model=List[DocumentRead])
async def search_documents(query: str):
    """Search for similar documents."""
    try:
        return await chat_service.search_similar_documents(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the RAG system."""
    try:
        success = await chat_service.delete_document(doc_id)
        if success:
            return {"message": "Document deleted successfully"}
        raise HTTPException(status_code=404, detail="Document not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/documents/{doc_id}", response_model=DocumentRead)
async def update_document(doc_id: str, document: DocumentCreate):
    """Update a document in the RAG system."""
    try:
        return await chat_service.update_document(doc_id, document)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
