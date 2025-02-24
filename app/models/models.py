from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: str
    created_at: datetime


class ChatBase(BaseModel):
    title: str
    description: Optional[str] = None


class ChatCreate(ChatBase):
    pass


class ChatRead(ChatBase):
    id: str
    created_at: datetime
    updated_at: datetime


class MessageBase(BaseModel):
    content: str
    role: str = "user"
    chat_id: str


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: str
    created_at: datetime
