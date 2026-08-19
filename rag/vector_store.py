from config.settings import settings
from rag.base import BaseVectorStore, DocumentChunk, RetrievalResult
from rag.embeddings import embed_text_sync


class ChromaVectorStore(BaseVectorStore):
    """
    Local ChromaDB vector store for FBR documents.
    Swappable with Qdrant via config in production.

    Where-filter support:
    Pass a ChromaDB-compatible where dict to search() to restrict
    results to specific documents. Example:
        where_filter={"document_name": {"$in": ["doc1", "doc2"]}}
    If None, searches all documents.
    """

    def __init__(self, collection_name: str = "fbr_documents"):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("ChromaDB is required for live retrieval. Install dependencies with `pip install -r requirements.txt`.") from exc
        self.client = chromadb.PersistentClient(
            path=settings.CHROMADB_PATH,
        )
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def collection_exists(self, name: str) -> bool:
        try:
            self.client.get_collection(name)
            return True
        except (KeyError, RuntimeError, ValueError):
            return False

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        print(f"Embedding {len(chunks)} chunks...")
        embeddings = []
        documents  = []
        metadatas  = []
        ids        = []

        for i, chunk in enumerate(chunks):
            embedding = embed_text_sync(chunk.text)
            embeddings.append(embedding)
            documents.append(chunk.text)
            metadatas.append({
                "document_name":   chunk.document_name,
                "source_section":  chunk.source_section,
                "page_number":     chunk.page_number,
                "token_estimate":  chunk.token_estimate,
                "citation": (
                    f"{chunk.document_name}, {chunk.source_section}, p.{chunk.page_number}"
                ),
            })
            ids.append(chunk.chunk_id)

            if (i + 1) % 10 == 0:
                print(f"  Embedded {i + 1}/{len(chunks)} chunks")

        self.collection.upsert(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        print(f"Added {len(chunks)} chunks to ChromaDB")

    def search(
        self,
        query: str,
        top_k: int = 5,
        where_filter: dict | None = None,
    ) -> list[RetrievalResult]:
        """
        Search the vector store for chunks relevant to query.

        Args:
            query:        Natural language search query
            top_k:        Number of results to return
            where_filter: Optional ChromaDB metadata filter.
                          Example: {"document_name": {"$in": ["docA", "docB"]}}
                          If None, searches across all documents.

        Returns:
            List of RetrievalResult ordered by similarity score (descending)
        """
        query_embedding = embed_text_sync(query)

        total_count = self.collection.count()
        if total_count == 0:
            return []

        n_results = min(top_k, total_count)

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results":        n_results,
            "include":          ["documents", "metadatas", "distances"],
        }

        # Only pass where filter when provided — ChromaDB errors on empty where
        if where_filter:
            query_kwargs["where"] = where_filter

        results = self.collection.query(**query_kwargs)

        retrieval_results = []
        for i in range(len(results["documents"][0])):
            doc_text = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            similarity = 1 - distance

            chunk = DocumentChunk(
                chunk_id=results["ids"][0][i],
                document_name=metadata["document_name"],
                source_section=metadata["source_section"],
                page_number=metadata["page_number"],
                text=doc_text,
                token_estimate=metadata["token_estimate"],
            )

            retrieval_results.append(RetrievalResult(
                chunk=chunk,
                similarity_score=similarity,
                citation=metadata["citation"],
            ))

        return retrieval_results

    def get_document_names(self) -> list[str]:
        """
        Returns all unique document names currently indexed.
        Useful for debugging and verifying ingestion.
        """
        results = self.collection.get(include=["metadatas"])
        names = set()
        for meta in results["metadatas"]:
            names.add(meta.get("document_name", "unknown"))
        return sorted(names)

    def count(self) -> int:
        """Total number of chunks in the collection."""
        return self.collection.count()


def get_vector_store() -> BaseVectorStore:
    if settings.VECTOR_DB == "chromadb":
        return ChromaVectorStore()
    raise ValueError(f"Unsupported vector DB: {settings.VECTOR_DB}")