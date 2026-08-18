"""
Tests for the RAG confidence gate (rag/retriever.py).

These tests mock the vector store so they run without a live ChromaDB
collection or an Ollama embedding server — the goal is to verify the
gating LOGIC (when does the system trust its own retrieval, and when
does it refuse and escalate), not the embedding model itself.
"""
import pytest
from unittest.mock import patch, MagicMock

from rag.retriever import FBRRetriever, CONFIDENCE_THRESHOLD
from rag.base import DocumentChunk, RetrievalResult


def make_result(score: float, citation: str = "Financeact2025, S.149, p.4", text: str = "sample chunk text") -> RetrievalResult:
    chunk = DocumentChunk(
        chunk_id="c1",
        document_name="2025629106147620Financeact2025",
        source_section="S.149",
        page_number=4,
        text=text,
        token_estimate=50,
    )
    return RetrievalResult(chunk=chunk, similarity_score=score, citation=citation)


def make_retriever_with_mocked_store(search_return_value):
    with patch("rag.retriever.get_vector_store") as mock_get_store:
        mock_store = MagicMock()
        mock_store.search.return_value = search_return_value
        mock_get_store.return_value = mock_store
        retriever = FBRRetriever()
    return retriever


# ── Confidence gate ─────────────────────────────────────────────────────────

def test_high_confidence_does_not_escalate():
    """A strong top match should be trusted, not escalated."""
    retriever = make_retriever_with_mocked_store([make_result(0.91)])
    result = retriever.retrieve("salaried tax rate for 2,000,000")
    assert result["escalate"] is False
    assert result["confidence"] == 0.91


def test_low_confidence_escalates():
    """A weak top match must be flagged for human escalation, not presented as authoritative."""
    retriever = make_retriever_with_mocked_store([make_result(0.4)])
    result = retriever.retrieve("obscure edge case query")
    assert result["escalate"] is True
    assert "below threshold" in result["reason"]


def test_confidence_exactly_at_threshold_does_not_escalate():
    """Boundary case: the gate uses strict '<', so a score equal to the
    threshold is treated as passing, not escalated."""
    retriever = make_retriever_with_mocked_store([make_result(CONFIDENCE_THRESHOLD)])
    result = retriever.retrieve("boundary query")
    assert result["escalate"] is False


def test_confidence_just_below_threshold_escalates():
    retriever = make_retriever_with_mocked_store([make_result(CONFIDENCE_THRESHOLD - 0.0001)])
    result = retriever.retrieve("boundary query")
    assert result["escalate"] is True


def test_no_documents_found_escalates_with_zero_confidence():
    """Empty vector store / no matches must escalate, never fabricate an answer."""
    retriever = make_retriever_with_mocked_store([])
    result = retriever.retrieve("query with no matching documents")
    assert result["escalate"] is True
    assert result["confidence"] == 0.0
    assert result["chunks"] == []


# ── Document routing ─────────────────────────────────────────────────────────

def test_taxpayer_type_restricts_search_to_routed_documents():
    """Salaried queries must be restricted to the Circular + Finance Act, excluding the noisy Ordinance."""
    retriever = make_retriever_with_mocked_store([make_result(0.85)])
    where_filter = retriever._build_where_filter("salaried")
    assert where_filter == {
        "document_name": {
            "$in": [
                "2025841183918948Circularno01Of2025 26Incometax",
                "2025629106147620Financeact2025",
            ]
        }
    }


def test_unrouted_taxpayer_type_has_no_restriction():
    """Unrouted/unknown taxpayer types should search across all documents rather than fail."""
    retriever = make_retriever_with_mocked_store([make_result(0.85)])
    where_filter = retriever._build_where_filter("some_unrouted_type")
    assert where_filter is None


def test_priority_docs_are_reranked_first():
    """Within an already-filtered result set, priority documents should be ordered first."""
    retriever = make_retriever_with_mocked_store([])
    low_priority = make_result(0.8, citation="Incometaxordinance, S.1, p.1")
    high_priority = make_result(0.79, citation="Circularno01, S.2, p.2")
    ordered = retriever._prioritize_results([low_priority, high_priority], "salaried")
    assert ordered[0] is high_priority


# ── get_context_string ────────────────────────────────────────────────────────

def test_get_context_string_includes_citations():
    retriever = make_retriever_with_mocked_store([make_result(0.9, text="Salaried tax slabs apply as follows.")])
    context = retriever.get_context_string("salaried tax rate")
    assert "Financeact2025" in context
    assert "Salaried tax slabs apply as follows." in context


def test_get_context_string_empty_when_no_chunks():
    retriever = make_retriever_with_mocked_store([])
    context = retriever.get_context_string("nothing matches this")
    assert context == ""


def test_confidence_uses_best_similarity_after_priority_reranking():
    """Priority ordering must not downgrade the actual retrieval confidence."""
    retriever = make_retriever_with_mocked_store([])
    strong_non_priority = make_result(0.95, citation="Incometaxordinance, S.1, p.1")
    weaker_priority = make_result(0.73, citation="Circularno01, S.2, p.2")

    with patch.object(retriever.store, "search", return_value=[strong_non_priority, weaker_priority]):
        result = retriever.retrieve("tax query", taxpayer_type="salaried")

    assert result["chunks"][0] is weaker_priority
    assert result["confidence"] == 0.95
    assert result["escalate"] is False


def test_2026_source_filter_requires_current_finance_act():
    retriever = make_retriever_with_mocked_store([])
    assert retriever._build_where_filter("salaried", "2026-27") == {"document_name": {"$in": ["FinanceAct2026", "2026226162211364Incometaxordinance2001 Amended 20.02.2026"]}}
