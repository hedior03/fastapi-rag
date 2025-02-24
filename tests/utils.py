from datetime import datetime
from typing import List, Dict, Any, Optional, Sequence
from unittest.mock import MagicMock, patch
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct, Distance, VectorParams
from llama_index.core.llms import (
    LLM,
    CompletionResponse,
    CompletionResponseGen,
    ChatResponse,
    ChatResponseGen,
    MessageRole,
    ChatMessage,
)
from llama_index.core.embeddings import BaseEmbedding
import uuid


def create_mock_qdrant_client() -> MagicMock:
    """Create a mock Qdrant client for testing."""
    mock_client = MagicMock()

    # Mock storage for collections and points
    mock_client._collections = {}
    mock_client._points = {"documents": [], "chats": []}

    # Mock collection creation
    def mock_create_collection(
        collection_name: str, vectors_config: Optional[VectorParams] = None, **kwargs
    ):
        mock_client._collections[collection_name] = {
            "vectors_config": vectors_config
            or VectorParams(size=1536, distance=Distance.COSINE),
            **kwargs,
        }
        mock_client._points[collection_name] = []

    mock_client.create_collection = mock_create_collection

    # Mock collection retrieval
    def mock_get_collection(collection_name: str):
        if collection_name not in mock_client._collections:
            raise ValueError(f"Collection {collection_name} not found")
        return mock_client._collections[collection_name]

    mock_client.get_collection = mock_get_collection

    # Mock point insertion
    def mock_upsert(collection_name: str, points: List[PointStruct]):
        if collection_name not in mock_client._points:
            mock_client._points[collection_name] = []
        mock_client._points[collection_name].extend(points)
        return True

    mock_client.upsert = mock_upsert

    # Mock point retrieval
    def mock_retrieve(collection_name: str, ids: List[str], **kwargs):
        if collection_name not in mock_client._points:
            return []
        points = [p for p in mock_client._points[collection_name] if p.id in ids]
        return points

    mock_client.retrieve = mock_retrieve

    # Mock scroll (list all points)
    def mock_scroll(collection_name: str, **kwargs):
        if collection_name not in mock_client._points:
            return [], None
        return [mock_client._points[collection_name]], None

    mock_client.scroll = mock_scroll

    return mock_client


def create_mock_openai():
    """Create a mock OpenAI client for testing."""
    mock_openai = MagicMock()

    def mock_embed(*args, **kwargs):
        # Return mock embeddings of correct dimension (1536 for OpenAI)
        return [0.0] * 1536

    mock_openai.embed = mock_embed
    return mock_openai


def create_mock_llama_index() -> MagicMock:
    """Create a mock LlamaIndex for testing."""
    mock_index = MagicMock()

    # Mock query engine
    mock_query_engine = MagicMock()

    def mock_query(query_text: str):
        return MockResponse(
            text=f"Mock response to: {query_text}",
            source_nodes=[
                MockSourceNode(
                    text="Mock source text",
                    metadata={
                        "id": str(uuid.uuid4()),
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
            ],
        )

    mock_query_engine.query = mock_query
    mock_index.as_query_engine.return_value = mock_query_engine

    # Mock insert
    def mock_insert(document):
        return True

    mock_index.insert = mock_insert

    return mock_index


class MockResponse:
    """Mock LlamaIndex response for testing."""

    def __init__(self, text: str, source_nodes: List[Any] = None):
        self.response = text
        self.source_nodes = source_nodes or []

    def __str__(self):
        return self.response


class MockSourceNode:
    """Mock LlamaIndex source node for testing."""

    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata


def create_test_document() -> Dict[str, Any]:
    """Create a test document."""
    return {
        "content": "Test document content",
        "metadata": {"source": "test", "topic": "testing"},
    }


def create_test_chat() -> Dict[str, Any]:
    """Create a test chat."""
    return {"title": "Test Chat", "description": "Chat for testing"}


def create_test_message(chat_id: str) -> Dict[str, Any]:
    """Create a test message."""
    return {"content": "Test message", "role": "user", "chat_id": chat_id}


def create_mock_llm() -> MagicMock:
    """Create a mock LLM that inherits from LlamaIndex's LLM class."""

    class MockLLM(LLM):
        def complete(self, prompt: str, **kwargs) -> CompletionResponse:
            return CompletionResponse(text=f"Mock response to: {prompt}")

        def stream_complete(self, prompt: str, **kwargs) -> CompletionResponseGen:
            yield CompletionResponse(text=f"Mock response to: {prompt}")

        def chat(self, messages: Sequence[ChatMessage], **kwargs) -> ChatResponse:
            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT, content="Mock chat response"
                )
            )

        def stream_chat(
            self, messages: Sequence[ChatMessage], **kwargs
        ) -> ChatResponseGen:
            yield ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT, content="Mock chat response"
                )
            )

        async def acomplete(self, prompt: str, **kwargs) -> CompletionResponse:
            return CompletionResponse(text=f"Mock async response to: {prompt}")

        async def astream_complete(
            self, prompt: str, **kwargs
        ) -> CompletionResponseGen:
            yield CompletionResponse(text=f"Mock async response to: {prompt}")

        async def achat(
            self, messages: Sequence[ChatMessage], **kwargs
        ) -> ChatResponse:
            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT, content="Mock async chat response"
                )
            )

        async def astream_chat(
            self, messages: Sequence[ChatMessage], **kwargs
        ) -> ChatResponseGen:
            yield ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT, content="Mock async chat response"
                )
            )

        @property
        def metadata(self) -> Dict[str, Any]:
            return {
                "model_name": "mock_llm",
                "context_window": 2048,
                "max_tokens": 256,
            }

    return MockLLM()


def create_mock_embedding() -> BaseEmbedding:
    """Create a mock embedding model that inherits from BaseEmbedding."""

    class MockEmbedding(BaseEmbedding):
        def _get_query_embedding(self, query: str) -> List[float]:
            return [0.0] * 1536  # OpenAI's embedding dimension

        def _get_text_embedding(self, text: str) -> List[float]:
            return [0.0] * 1536

        async def _aget_query_embedding(self, query: str) -> List[float]:
            return [0.0] * 1536

        async def _aget_text_embedding(self, text: str) -> List[float]:
            return [0.0] * 1536

        def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
            return [[0.0] * 1536 for _ in texts]

        async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
            return [[0.0] * 1536 for _ in texts]

    return MockEmbedding()


def mock_dependencies():
    """Create all necessary mocks for testing."""
    mock_qdrant = create_mock_qdrant_client()
    mock_llama = create_mock_llama_index()
    mock_llm = create_mock_llm()
    mock_embedding = create_mock_embedding()

    patches = [
        patch("app.services.chat_service.QdrantClient", return_value=mock_qdrant),
        patch(
            "app.services.chat_service.VectorStoreIndex.from_vector_store",
            return_value=mock_llama,
        ),
        patch("app.services.chat_service.OpenAIEmbedding", return_value=mock_embedding),
        patch("app.services.chat_service.OpenAI", return_value=mock_llm),
    ]

    return patches
