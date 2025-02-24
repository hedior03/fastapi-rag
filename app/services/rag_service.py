from typing import List, Optional
from llama_index import VectorStoreIndex, ServiceContext
from llama_index.vector_stores import QdrantVectorStore
from llama_index.embeddings import OpenAIEmbedding
from llama_index.llms import OpenAI
from qdrant_client import QdrantClient
from app.core.config import settings


class RAGService:
    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
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

    async def process_message(self, messages: List[dict]) -> str:
        # Convert messages to string format that LlamaIndex can understand
        chat_history = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in messages[:-1]]
        )
        current_message = messages[-1]["content"]

        # Create query engine
        query_engine = self.index.as_query_engine(
            service_context=self.service_context, similarity_top_k=3
        )

        # Generate response
        if chat_history:
            response = query_engine.query(
                f"Chat history:\n{chat_history}\n\nCurrent message: {current_message}\n\n"
                "Please provide a helpful response based on the available context."
            )
        else:
            response = query_engine.query(current_message)

        return str(response)

    async def add_document(self, content: str, doc_id: Optional[str] = None):
        from llama_index import Document

        # Create document
        document = Document(text=content, doc_id=doc_id)

        # Insert into index
        self.index.insert(document)
