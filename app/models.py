from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ChatBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None


class Chat(ChatBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List["Message"] = Relationship(back_populates="chat")


class ChatCreate(ChatBase):
    pass


class ChatRead(ChatBase):
    id: int
    created_at: datetime
    updated_at: datetime


class MessageBase(SQLModel):
    content: str
    role: str = Field(default="user")  # user or assistant
    chat_id: Optional[int] = Field(default=None, foreign_key="chat.id")


class Message(MessageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chat: Optional[Chat] = Relationship(back_populates="messages")


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    created_at: datetime
