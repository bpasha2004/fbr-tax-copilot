from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """Single chunk of text from an FBR document."""
    chunk_id: str
    document_name: str
    source_section: str
    page_number: int
    text: str
    token_estimate: int


@dataclass
class RetrievalResult:
    """Result from vector search."""
    chunk: DocumentChunk
    similarity_score: float
    citation: str


class BaseVectorStore(ABC):
    @abstractmethod
    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        pass

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        pass