"""
API smoke tests. Confirms the app boots, routes are wired correctly,
and the RAG endpoint's confidence-gate contract holds at the HTTP layer
(not just inside the retriever unit tests).
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from rag.base import DocumentChunk, RetrievalResult


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_serves_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200


def _mock_chunk(score: float) -> RetrievalResult:
    chunk = DocumentChunk(
        chunk_id="c1",
        document_name="2025629106147620Financeact2025",
        source_section="S.149",
        page_number=4,
        text="Salaried individuals are taxed per Division I, First Schedule.",
        token_estimate=40,
    )
    return RetrievalResult(chunk=chunk, similarity_score=score, citation="Financeact2025, S.149, p.4")


def test_rag_query_high_confidence_does_not_escalate(client):
    with patch("api.routes.rag.FBRRetriever") as MockRetriever:
        instance = MagicMock()
        instance.retrieve.return_value = {
            "chunks": [_mock_chunk(0.9)],
            "citations": ["Financeact2025, S.149, p.4"],
            "confidence": 0.9,
            "escalate": False,
            "reason": "OK",
        }
        MockRetriever.return_value = instance

        response = client.post("/api/v1/rag/query", json={
            "query": "What is the tax rate for salaried income of 2,000,000?",
            "taxpayer_type": "salaried",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is False
    assert body["confidence"] == 0.9
    assert len(body["chunks"]) == 1
    assert body["chunks"][0]["citation"] == "Financeact2025, S.149, p.4"


def test_rag_query_low_confidence_escalates(client):
    with patch("api.routes.rag.FBRRetriever") as MockRetriever:
        instance = MagicMock()
        instance.retrieve.return_value = {
            "chunks": [_mock_chunk(0.3)],
            "citations": ["Financeact2025, S.149, p.4"],
            "confidence": 0.3,
            "escalate": True,
            "reason": "Confidence 0.3000 below threshold 0.72",
        }
        MockRetriever.return_value = instance

        response = client.post("/api/v1/rag/query", json={
            "query": "some obscure edge case not covered by the documents",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["escalate"] is True
    assert "below threshold" in body["reason"]


def test_rag_query_rejects_empty_query(client):
    response = client.post("/api/v1/rag/query", json={"query": "   "})
    assert response.status_code == 400


# ── Tax calculation correctness ─────────────────────────────────────────────
# These lock in two real bugs found by manual testing:
#   1. /calculate silently ignored taxpayer_type and always computed
#      salaried tax, even when the caller asked for "business".
#   2. Invalid input (e.g. negative income) crashed with a raw 500
#      instead of a clean 422, because ValidationError wasn't a
#      ValueError subclass and no route/global handler caught it.

def test_calculate_salaried_default(client):
    response = client.post("/api/v1/tax/calculate", json={
        "annual_income": 2000000, "taxpayer_type": "salaried", "dev_mode": True,
    })
    assert response.status_code == 200
    assert response.json()["taxpayer_type"] == "salaried"


def test_calculate_rejects_mismatched_taxpayer_type(client):
    """A caller sending taxpayer_type='business' to the salaried endpoint
    must be told to use /business/calculate — not silently given a
    salaried number under a different tax regime."""
    response = client.post("/api/v1/tax/calculate", json={
        "annual_income": 3000000, "taxpayer_type": "business", "dev_mode": True,
    })
    assert response.status_code == 422
    assert "business" in response.json()["detail"].lower()


def test_calculate_business_actually_used_when_correct_endpoint_called(client):
    response = client.post("/api/v1/tax/business/calculate", json={
        "net_business_income": 3000000, "dev_mode": True,
    })
    assert response.status_code == 200
    assert response.json()["taxpayer_type"] == "business"
    # Business and salaried tax on the same income must differ —
    # this is the number that was silently wrong before the fix.
    salaried = client.post("/api/v1/tax/calculate", json={
        "annual_income": 3000000, "taxpayer_type": "salaried", "dev_mode": True,
    }).json()
    assert response.json()["tax_payable"] != salaried["tax_payable"]


def test_calculate_negative_income_returns_clean_422_not_500(client):
    response = client.post("/api/v1/tax/calculate", json={
        "annual_income": -500, "taxpayer_type": "salaried", "dev_mode": True,
    })
    assert response.status_code == 422
    assert "negative" in response.json()["detail"].lower()


def test_business_negative_income_returns_clean_422_not_500(client):
    """Same ValidationError-not-caught bug existed on the business route too."""
    response = client.post("/api/v1/tax/business/calculate", json={
        "net_business_income": -1, "dev_mode": True,
    })
    assert response.status_code == 422


def test_freelance_negative_proceeds_returns_422(client):
    response = client.post("/api/v1/tax/freelance/calculate", json={
        "gross_export_proceeds": -1, "dev_mode": True,
    })
    assert response.status_code == 422


def test_calculate_income_over_ceiling_returns_422_not_500(client):
    response = client.post("/api/v1/tax/calculate", json={
        "annual_income": 99999999999, "taxpayer_type": "salaried", "dev_mode": True,
    })
    assert response.status_code == 422
    assert "exceeds maximum" in response.json()["detail"]
