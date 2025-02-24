from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


class Document(BaseModel):
    content: str


class Message(BaseModel):
    content: str
    role: str = "user"


@router.post("/documents/")
async def add_document(document: Document):
    """Add a document to the RAG system."""
    result = await chat_service.add_document(document.content)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/messages/")
async def send_message(message: Message):
    """Send a message and get an AI response."""
    return await chat_service.send_message(message.content, message.role)


@router.get("/search/")
async def search_documents(query: str):
    """Search for similar documents."""
    return await chat_service.search_similar_documents(query)
