"""
RAG Query API — Grounding & Confidence Gate Endpoint
─────────────────────────────────────────────────────
Exposes the retrieval layer (rag/retriever.py) directly, independent of
the tax-calculation flow. This is the endpoint that answers: "is this
answer actually grounded in an authoritative FBR document, or should
the system refuse and escalate to a human?"

Every response returns:
  - confidence:  top similarity score for the best-matching chunk
  - escalate:    True if confidence is below CONFIDENCE_THRESHOLD —
                  callers MUST NOT treat the answer as authoritative
                  when this is True
  - citations:   exact document/section/page references for the
                  chunks that were used, so every claim is traceable
                  back to source text

This separation exists so grounding can be evaluated and tuned on its
own — independent of the AI explanation layer that consumes it.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rag.retriever import CONFIDENCE_THRESHOLD, FBRRetriever

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    query:          str            = Field(..., examples=["What is the tax rate for salaried income of 2,000,000?"])
    taxpayer_type:  str | None  = Field(None, examples=["salaried"])
    tax_year:       str | None  = Field(None, examples=["2026-27"])
    top_k:          int            = Field(5, ge=1, le=20)


class RAGChunkResponse(BaseModel):
    citation:           str
    similarity_score:   float
    text:                str


class RAGQueryResponse(BaseModel):
    query:              str
    confidence:         float
    escalate:           bool
    reason:             str
    threshold:          float
    chunks:             list[RAGChunkResponse]


@router.post("/query", response_model=RAGQueryResponse)
def query_rag(request: RAGQueryRequest):
    """
    Run retrieval + confidence gating for a raw query, without going
    through tax calculation. Useful for debugging retrieval quality,
    tuning the confidence threshold, and evaluating grounding directly.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    retriever = FBRRetriever()
    result = retriever.retrieve(
        query=request.query,
        top_k=request.top_k,
        taxpayer_type=request.taxpayer_type,
        tax_year=request.tax_year,
    )

    return RAGQueryResponse(
        query=request.query,
        confidence=result["confidence"],
        escalate=result["escalate"],
        reason=result["reason"],
        threshold=CONFIDENCE_THRESHOLD,
        chunks=[
            RAGChunkResponse(
                citation=r.citation,
                similarity_score=round(r.similarity_score, 4),
                text=r.chunk.text,
            )
            for r in result["chunks"]
        ],
    )


@router.get("/documents")
def list_indexed_documents():
    """Returns all document names currently indexed in the vector store."""
    retriever = FBRRetriever()
    return {"documents": retriever.store.get_document_names(), "count": retriever.store.count()}
