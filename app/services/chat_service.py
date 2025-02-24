from typing import List, Optional, Dict
from datetime import datetime
import uuid
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings as app_settings
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
        self._qdrant_client = None
        self._vector_store = None
        self._embed_model = None
        self._llm = None
        self._index = None

    @property
    def qdrant_client(self):
        if self._qdrant_client is None:
            try:
                self._qdrant_client = QdrantClient(
                    host=app_settings.QDRANT_HOST,
                    port=app_settings.QDRANT_PORT,
                    grpc_port=app_settings.QDRANT_GRPC_PORT,
                    prefer_grpc=False,
                )
                self._init_collections()
            except Exception as e:
                raise Exception(f"Failed to connect to Qdrant: {str(e)}")
        return self._qdrant_client

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = QdrantVectorStore(
                client=self.qdrant_client, collection_name="documents"
            )
        return self._vector_store

    @property
    def embed_model(self):
        if self._embed_model is None:
            self._embed_model = OpenAIEmbedding()
        return self._embed_model

    @property
    def llm(self):
        if self._llm is None:
            self._llm = OpenAI(api_key=app_settings.OPENAI_API_KEY, model="gpt-3.5-turbo")
        return self._llm

    @property
    def index(self):
        if self._index is None:
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            self._index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store
            )
        return self._index

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
        try:
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
        except Exception as e:
            raise Exception(f"Failed to create chat: {str(e)}")

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
            chat_engine = self.index.as_chat_engine(
                chat_mode="context",
                system_prompt=(
                    "You are a helpful AI assistant. Use the provided context to answer "
                    "questions about FastAPI and related technologies. If the context doesn't "
                    "contain enough information, say so and provide general information about "
                    "the topic if possible. Be concise but informative."
                ),
            )
            response = chat_engine.chat(message.content)

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

    def _refresh_index(self):
        """Force a refresh of the index."""
        self._index = None

    async def add_document(self, document: DocumentCreate) -> DocumentRead:
        """Add a document to the RAG system."""
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()

        try:
            # Create document metadata
            metadata = {
                "id": doc_id,
                "created_at": now.isoformat(),
                **document.metadata,
            }

            # Create document with metadata
            llama_doc = Document(
                text=document.content,
                metadata=metadata,
            )

            # Get embeddings for the document
            embed_model = self.embed_model
            embeddings = embed_model.get_text_embedding(document.content)

            # Store in Qdrant directly
            self.qdrant_client.upsert(
                collection_name="documents",
                points=[
                    models.PointStruct(
                        id=doc_id,
                        vector=embeddings,
                        payload={
                            "text": document.content,
                            "metadata": metadata,
                        },
                    )
                ],
            )

            # Also store in LlamaIndex for querying
            self.index.insert(llama_doc)
            self._refresh_index()

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
            # Get all documents from the vector store
            response = self.qdrant_client.scroll(
                collection_name="documents",
                limit=100,  # Adjust as needed
                with_payload=True,
                with_vectors=False,
            )

            documents = []
            for point in response[0]:
                # Extract metadata from the payload
                metadata = point.payload.get("metadata", {})
                doc_id = metadata.get("id")
                created_at_str = metadata.get("created_at")
                
                if doc_id and created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        # Filter out internal metadata
                        filtered_metadata = {
                            k: v for k, v in metadata.items() 
                            if k not in ["id", "created_at"]
                        }
                        
                        documents.append(
                            DocumentRead(
                                id=doc_id,
                                content=point.payload.get("text", ""),
                                metadata=filtered_metadata,
                                created_at=created_at,
                            )
                        )
                    except (ValueError, TypeError):
                        continue  # Skip invalid documents
                        
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

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the RAG system."""
        try:
            # Delete from Qdrant
            self.qdrant_client.delete(
                collection_name="documents",
                points_selector=models.PointIdsList(
                    points=[doc_id]
                ),
            )

            # Force index refresh to reflect changes
            self._refresh_index()

            return True
        except Exception as e:
            raise ValueError(f"Failed to delete document: {str(e)}")

    async def update_document(self, doc_id: str, document: DocumentCreate) -> DocumentRead:
        """Update an existing document in the RAG system."""
        try:
            # Check if document exists
            response = self.qdrant_client.retrieve(
                collection_name="documents",
                ids=[doc_id],
            )
            if not response:
                raise ValueError(f"Document with ID {doc_id} not found")

            # Get existing metadata
            existing_metadata = response[0].payload.get("metadata", {})
            created_at_str = existing_metadata.get("created_at")
            
            # Create updated metadata
            metadata = {
                "id": doc_id,
                "created_at": created_at_str,
                **document.metadata,
            }

            # Create document with metadata
            llama_doc = Document(
                text=document.content,
                metadata=metadata,
            )

            # Get embeddings for the document
            embed_model = self.embed_model
            embeddings = embed_model.get_text_embedding(document.content)

            # Update in Qdrant
            self.qdrant_client.upsert(
                collection_name="documents",
                points=[
                    models.PointStruct(
                        id=doc_id,
                        vector=embeddings,
                        payload={
                            "text": document.content,
                            "metadata": metadata,
                        },
                    )
                ],
            )

            # Update in LlamaIndex
            self.index.insert(llama_doc)
            self._refresh_index()

            return DocumentRead(
                id=doc_id,
                content=document.content,
                metadata=document.metadata,
                created_at=datetime.fromisoformat(created_at_str),
            )
        except Exception as e:
            raise ValueError(f"Failed to update document: {str(e)}")
