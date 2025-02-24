from typing import List, Optional, Dict
from datetime import datetime
import uuid
from llama_index.core import VectorStoreIndex, ServiceContext, Document
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.models import (
    ChatCreate,
    ChatRead,
    MessageCreate,
    MessageRead,
    DocumentCreate,
    DocumentRead,
)


class ChatService:
    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )

        # Create collections if they don't exist
        self._init_collections()

        # Initialize vector store
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client, collection_name="documents"
        )

        # Initialize embedding model
        self.embed_model = OpenAIEmbedding()

        # Initialize LLM
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-3.5-turbo")

        # Create service context
        self.service_context = ServiceContext.from_defaults(
            llm=self.llm, embed_model=self.embed_model
        )

        # Initialize index
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store, service_context=self.service_context
        )

        # Initialize chat engines dict
        self.chat_engines = {}

    def _init_collections(self):
        """Initialize Qdrant collections."""
        try:
            self.qdrant_client.get_collection("documents")
        except Exception:
            self.qdrant_client.create_collection(
                collection_name="documents",
                vectors_config=models.VectorParams(
                    size=1536,  # OpenAI embedding dimension
                    distance=models.Distance.COSINE,
                ),
            )

        try:
            self.qdrant_client.get_collection("chats")
        except Exception:
            self.qdrant_client.create_collection(
                collection_name="chats",
                vectors_config=models.VectorParams(
                    size=1,  # Dummy vector size for metadata storage
                    distance=models.Distance.COSINE,
                ),
            )

    async def create_chat(self, chat: ChatCreate) -> ChatRead:
        """Create a new chat."""
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Store chat metadata in Qdrant
        self.qdrant_client.upsert(
            collection_name="chats",
            points=[
                models.PointStruct(
                    id=chat_id,
                    vector=[0.0],  # Dummy vector
                    payload={
                        "title": chat.title,
                        "description": chat.description,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "messages": [],
                    },
                )
            ],
        )

        return ChatRead(
            id=chat_id,
            title=chat.title,
            description=chat.description,
            created_at=now,
            updated_at=now,
        )

    async def list_chats(self) -> List[ChatRead]:
        """List all chats."""
        response = self.qdrant_client.scroll(
            collection_name="chats",
            limit=100,  # Adjust as needed
        )

        chats = []
        for point in response[0]:
            chats.append(
                ChatRead(
                    id=point.id,
                    title=point.payload["title"],
                    description=point.payload["description"],
                    created_at=datetime.fromisoformat(point.payload["created_at"]),
                    updated_at=datetime.fromisoformat(point.payload["updated_at"]),
                )
            )
        return chats

    async def get_chat_messages(self, chat_id: str) -> List[MessageRead]:
        """Get all messages in a chat."""
        response = self.qdrant_client.retrieve(collection_name="chats", ids=[chat_id])

        if not response:
            return []

        messages = []
        for msg in response[0].payload["messages"]:
            messages.append(
                MessageRead(
                    id=msg["id"],
                    content=msg["content"],
                    role=msg["role"],
                    chat_id=chat_id,
                    created_at=datetime.fromisoformat(msg["created_at"]),
                )
            )
        return messages

    async def add_message(self, message: MessageCreate) -> MessageRead:
        """Add a message to a chat and get AI response."""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Get chat
        response = self.qdrant_client.retrieve(
            collection_name="chats", ids=[message.chat_id]
        )

        if not response:
            raise ValueError("Chat not found")

        chat = response[0]
        messages = chat.payload["messages"]

        # Add new message
        new_message = {
            "id": message_id,
            "content": message.content,
            "role": message.role,
            "created_at": now.isoformat(),
        }
        messages.append(new_message)

        # Get AI response
        try:
            query_engine = self.index.as_query_engine(
                service_context=self.service_context, similarity_top_k=3
            )
            response = query_engine.query(message.content)

            # Add AI response
            ai_message = {
                "id": str(uuid.uuid4()),
                "content": str(response),
                "role": "assistant",
                "created_at": datetime.utcnow().isoformat(),
            }
            messages.append(ai_message)

            # Update chat
            self.qdrant_client.upsert(
                collection_name="chats",
                points=[
                    models.PointStruct(
                        id=message.chat_id,
                        vector=[0.0],  # Dummy vector
                        payload={
                            **chat.payload,
                            "messages": messages,
                            "updated_at": datetime.utcnow().isoformat(),
                        },
                    )
                ],
            )
        except Exception as e:
            ai_message = {
                "id": str(uuid.uuid4()),
                "content": f"Error: {str(e)}",
                "role": "assistant",
                "created_at": datetime.utcnow().isoformat(),
            }
            messages.append(ai_message)

        return MessageRead(
            id=message_id,
            content=message.content,
            role=message.role,
            chat_id=message.chat_id,
            created_at=now,
        )

    async def add_document(self, document: DocumentCreate) -> DocumentRead:
        """Add a document to the RAG system."""
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()

        try:
            # Create document with metadata
            llama_doc = Document(
                text=document.content,
                metadata={
                    "id": doc_id,
                    "created_at": now.isoformat(),
                    **document.metadata,
                },
            )

            # Insert into index
            self.index.insert(llama_doc)

            return DocumentRead(
                id=doc_id,
                content=document.content,
                metadata=document.metadata,
                created_at=now,
            )
        except Exception as e:
            raise ValueError(f"Failed to add document: {str(e)}")

    async def list_documents(self) -> List[DocumentRead]:
        """List all documents."""
        try:
            response = self.qdrant_client.scroll(
                collection_name="documents",
                limit=100,  # Adjust as needed
                with_payload=True,
                with_vectors=False,
            )

            documents = []
            for point in response[0]:
                doc_metadata = point.payload.get("metadata", {})
                if "id" in doc_metadata and "created_at" in doc_metadata:
                    documents.append(
                        DocumentRead(
                            id=doc_metadata["id"],
                            content=point.payload.get("text", ""),
                            metadata={
                                k: v
                                for k, v in doc_metadata.items()
                                if k not in ["id", "created_at"]
                            },
                            created_at=datetime.fromisoformat(
                                doc_metadata["created_at"]
                            ),
                        )
                    )
            return documents
        except Exception as e:
            raise ValueError(f"Failed to list documents: {str(e)}")

    async def search_similar_documents(self, query: str) -> List[DocumentRead]:
        """Search for similar documents."""
        try:
            query_engine = self.index.as_query_engine(similarity_top_k=5)
            response = query_engine.query(query)

            documents = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    doc_metadata = node.metadata
                    if "id" in doc_metadata and "created_at" in doc_metadata:
                        documents.append(
                            DocumentRead(
                                id=doc_metadata["id"],
                                content=node.text,
                                metadata={
                                    k: v
                                    for k, v in doc_metadata.items()
                                    if k not in ["id", "created_at"]
                                },
                                created_at=datetime.fromisoformat(
                                    doc_metadata["created_at"]
                                ),
                            )
                        )
            return documents
        except Exception as e:
            raise ValueError(f"Failed to search documents: {str(e)}")
