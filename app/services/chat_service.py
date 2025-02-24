from typing import List, Optional
from datetime import datetime
from llama_index.core import VectorStoreIndex, ServiceContext, Document
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings


class ChatService:
    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )

        # Create collection if it doesn't exist
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

    async def add_document(self, content: str) -> dict:
        """Add a document to the RAG system."""
        try:
            document = Document(text=content)
            self.index.insert(document)
            return {"status": "success", "message": "Document added successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def send_message(self, message: str, role: str = "user") -> dict:
        """Send a message and get an AI response."""
        try:
            # Create query engine
            query_engine = self.index.as_query_engine(
                service_context=self.service_context, similarity_top_k=3
            )

            # Generate response
            response = query_engine.query(message)

            return {"role": "assistant", "content": str(response)}
        except Exception as e:
            return {"role": "assistant", "content": f"Error: {str(e)}"}

    async def search_similar_documents(self, query: str) -> List[str]:
        """Search for similar documents using the query engine."""
        try:
            query_engine = self.index.as_query_engine()
            response = query_engine.query(query)
            if hasattr(response, "source_nodes"):
                return [node.text for node in response.source_nodes]
            return []
        except Exception as e:
            return [f"Error: {str(e)}"]
