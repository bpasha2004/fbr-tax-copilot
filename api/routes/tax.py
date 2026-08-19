"""
Tax API Routes — B2B Co-Pilot Endpoints
Covers: salaried, freelance (Sec. 154A), business (Division II)
All responses include IRIS 2.0 portal field entries and document checklists.
"""
from math import isfinite

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.ollama_provider import get_ai_provider
from config.settings import settings
from src.business_tax.calculator import BusinessTaxCalculator
from src.freelance_tax.calculator import FreelanceTaxCalculator

# Feature calculators — each wraps the shared RulesEngine with its own
# document validation and IRIS output mapping (imported inside the
# calculator classes themselves, not needed directly here).
from src.salary_tax.calculator import SalaryTaxCalculator

router = APIRouter(prefix="/api/v1/tax", tags=["tax"])

def _effective_dev_mode(requested: bool) -> bool:
    if requested and settings.ENV == "production":
        raise HTTPException(status_code=403, detail="dev_mode is disabled in production.")
    return bool(requested)

def _require_finite(value: float, label: str) -> float:
    if not isfinite(value):
        raise HTTPException(status_code=422, detail=f"{label} must be finite.")
    return value


def _reject_mismatched_taxpayer_type(taxpayer_type: str) -> None:
    """
    /calculate and /explain compute salaried tax only. If a caller sets
    taxpayer_type to something else, fail loudly instead of silently
    returning a salaried number for a business or freelance query.
    """
    normalized = (taxpayer_type or "salaried").strip().lower()
    if normalized not in ("salaried", "individual"):
        redirect = {
            "business": "/api/v1/tax/business/calculate or /business/explain",
            "company": "/api/v1/tax/business/calculate or /business/explain",
            "freelance": "/api/v1/tax/freelance/calculate or /freelance/explain",
        }.get(normalized, "the matching /business or /freelance endpoint")
        raise HTTPException(
            status_code=422,
            detail=(
                f"This endpoint only calculates salaried tax. "
                f"taxpayer_type='{taxpayer_type}' should use {redirect}."
            ),
        )


# ── Request schemas ───────────────────────────────────────────────────────────

class TaxCalculateRequest(BaseModel):
    annual_income:  float           = Field(..., examples=[1200000.0])
    taxpayer_type:  str             = Field("salaried")
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    dev_mode:       bool            = Field(False)


class TaxExplainRequest(BaseModel):
    annual_income:  float           = Field(..., examples=[1200000.0])
    taxpayer_type:  str             = Field("salaried")
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    user_question:  str | None   = Field("Provide IRIS 2.0 filing entries and compliance flags.", max_length=2000)
    language:       str             = Field("english", max_length=30)
    dev_mode:       bool            = Field(False)


class FreelanceCalculateRequest(BaseModel):
    gross_export_proceeds: float    = Field(..., examples=[2400000.0], gt=0)
    atl: bool = True
    pseb_registered: bool = True
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    dev_mode:       bool            = Field(False)


class FreelanceExplainRequest(BaseModel):
    gross_export_proceeds: float    = Field(..., examples=[2400000.0], gt=0)
    atl: bool = True
    pseb_registered: bool = True
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    user_question:  str | None   = Field("Provide IRIS 2.0 entries for Section 154A filing.", max_length=2000)
    language:       str             = Field("english", max_length=30)
    dev_mode:       bool            = Field(False)


class BusinessCalculateRequest(BaseModel):
    net_business_income: float      = Field(..., examples=[3600000.0])
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    dev_mode:       bool            = Field(False)


class BusinessExplainRequest(BaseModel):
    net_business_income: float      = Field(..., examples=[3600000.0])
    tax_year:       str             = Field("2026-27")
    documents:      list[str]       = Field(default_factory=list, max_length=50)
    user_question:  str | None   = Field("Provide IRIS 2.0 entries and compliance flags.", max_length=2000)
    language:       str             = Field("english", max_length=30)
    dev_mode:       bool            = Field(False)


# ── Salaried — /calculate ─────────────────────────────────────────────────────

@router.post("/calculate")
async def calculate_tax(request: TaxCalculateRequest):
    """
    Deterministic salaried tax calculation (Division I).

    This endpoint only computes salaried tax — it does not branch on
    `taxpayer_type`. The field exists for forward compatibility and for
    catching client mistakes: if it's set to anything other than
    "salaried", the request is rejected with a pointer to the correct
    endpoint, rather than silently computing salaried tax anyway.
    Business and freelance income have their own endpoints below because
    each uses different input fields (net_business_income /
    gross_export_proceeds) and a different IRIS mapping.
    """
    _reject_mismatched_taxpayer_type(request.taxpayer_type)
    _require_finite(request.annual_income, "annual_income")
    calc = SalaryTaxCalculator(tax_year=request.tax_year, dev_mode=_effective_dev_mode(request.dev_mode))
    return calc.calculate(request.annual_income, documents=request.documents)


@router.post("/explain")
async def explain_tax(request: TaxExplainRequest):
    """
    Salaried tax calculation + AI advisor explanation with IRIS entries and document flags.
    """
    _reject_mismatched_taxpayer_type(request.taxpayer_type)
    _require_finite(request.annual_income, "annual_income")
    effective_dev_mode = _effective_dev_mode(request.dev_mode)
    calc = SalaryTaxCalculator(tax_year=request.tax_year, dev_mode=effective_dev_mode)
    audit_record = calc.calculate(request.annual_income, documents=request.documents)

    ai = get_ai_provider()
    ai_response = await ai.explain_tax_result(
        audit_record=audit_record,
        user_question=request.user_question or "Provide IRIS 2.0 filing entries and compliance flags.",
        language=request.language,
        dev_mode=effective_dev_mode,
    )

    if ai_response.get("refused"):
        return {
            **audit_record,
            "explanation":         None,
            "explanation_refused": True,
            "refusal_reason":      ai_response.get("reason"),
            "rag_confidence":      ai_response.get("confidence"),
            "rag_context_used":    False,
            "model_used":          None,
            "model_failed":        False,
            "rag_citations":       [],
        }

    return {
        **audit_record,
        "explanation":         ai_response.get("explanation"),
        "explanation_refused": False,
        "refusal_reason":      None,
        "rag_confidence":      ai_response.get("confidence"),
        "rag_context_used":    ai_response.get("rag_context_used", False),
        "model_used":          ai_response.get("model_used"),
        "model_failed":        ai_response.get("model_failed", False),
        "rag_citations":       ai_response.get("rag_citations", []),
        "hallucination_detected": ai_response.get("hallucination_detected", False),
    }


# ── Freelance / IT Exports — Section 154A ────────────────────────────────────

@router.post("/freelance/calculate")
async def calculate_freelance_tax(request: FreelanceCalculateRequest):
    """
    Section 154A Final Tax calculation for IT/software export proceeds.
    Rate: 0.25% of gross export proceeds. FINAL TAX — no further income tax.
    Returns IRIS 2.0 entries (Box 5000, 5001, 7300) + PRC document checklist.
    """
    _require_finite(request.gross_export_proceeds, "gross_export_proceeds")
    calc = FreelanceTaxCalculator(tax_year=request.tax_year, dev_mode=_effective_dev_mode(request.dev_mode), atl=request.atl, pseb_registered=request.pseb_registered)
    return calc.calculate(request.gross_export_proceeds, documents=request.documents)


@router.post("/freelance/explain")
async def explain_freelance_tax(request: FreelanceExplainRequest):
    """
    Section 154A calculation + AI advisor commentary with IRIS entries.
    """
    _require_finite(request.gross_export_proceeds, "gross_export_proceeds")
    effective_dev_mode = _effective_dev_mode(request.dev_mode)
    calc = FreelanceTaxCalculator(tax_year=request.tax_year, dev_mode=effective_dev_mode, atl=request.atl, pseb_registered=request.pseb_registered)
    audit_record = calc.calculate(request.gross_export_proceeds, documents=request.documents)

    ai = get_ai_provider()
    ai_response = await ai.explain_tax_result(
        audit_record=audit_record,
        user_question=request.user_question or "Provide IRIS 2.0 entries for Section 154A filing.",
        language=request.language,
        dev_mode=effective_dev_mode,
    )

    if ai_response.get("refused"):
        return {**audit_record, "explanation": None, "explanation_refused": True,
                "refusal_reason": ai_response.get("reason"), "rag_confidence": ai_response.get("confidence")}

    return {
        **audit_record,
        "explanation":            ai_response.get("explanation"),
        "explanation_refused":    False,
        "rag_confidence":         ai_response.get("confidence"),
        "rag_context_used":       ai_response.get("rag_context_used", False),
        "model_used":             ai_response.get("model_used"),
        "model_failed":           ai_response.get("model_failed", False),
        "rag_citations":          ai_response.get("rag_citations", []),
        "hallucination_detected": ai_response.get("hallucination_detected", False),
    }


# ── Business / Non-Salaried Individual — Division II ─────────────────────────

@router.post("/business/calculate")
async def calculate_business_tax(request: BusinessCalculateRequest):
    """
    Business individual tax calculation using the versioned First Schedule, Division II rules.
    6-tier progressive slabs: 0% → 15% → 20% → 30% → 40% → 45%.
    Returns IRIS 2.0 entries (Box 4000–4400, Box 9200, 9400–9500) + document checklist.
    """
    _require_finite(request.net_business_income, "net_business_income")
    calc = BusinessTaxCalculator(tax_year=request.tax_year, dev_mode=_effective_dev_mode(request.dev_mode))
    return calc.calculate(request.net_business_income, documents=request.documents)


@router.post("/business/explain")
async def explain_business_tax(request: BusinessExplainRequest):
    """
    Business tax calculation + AI advisor commentary with Division II IRIS entries.
    """
    _require_finite(request.net_business_income, "net_business_income")
    effective_dev_mode = _effective_dev_mode(request.dev_mode)
    calc = BusinessTaxCalculator(tax_year=request.tax_year, dev_mode=effective_dev_mode)
    audit_record = calc.calculate(request.net_business_income, documents=request.documents)

    ai = get_ai_provider()
    ai_response = await ai.explain_tax_result(
        audit_record=audit_record,
        user_question=request.user_question or "Provide IRIS 2.0 entries and compliance flags.",
        language=request.language,
        dev_mode=effective_dev_mode,
    )

    if ai_response.get("refused"):
        return {**audit_record, "explanation": None, "explanation_refused": True,
                "refusal_reason": ai_response.get("reason"), "rag_confidence": ai_response.get("confidence")}

    return {
        **audit_record,
        "explanation":            ai_response.get("explanation"),
        "explanation_refused":    False,
        "rag_confidence":         ai_response.get("confidence"),
        "rag_context_used":       ai_response.get("rag_context_used", False),
        "model_used":             ai_response.get("model_used"),
        "model_failed":           ai_response.get("model_failed", False),
        "rag_citations":          ai_response.get("rag_citations", []),
        "hallucination_detected": ai_response.get("hallucination_detected", False),
    }


# ── Health check ──────────────────────────────────────────────────────────────

@router.get("/health")
async def tax_health():
    """Check Ollama connectivity, available models, and live RAG corpus size."""
    from rag.retriever import FBRRetriever

    try:
        rag_chunks = FBRRetriever().store.count()
    except (OSError, RuntimeError, ValueError):
        rag_chunks = None  # vector store unreachable — don't fake a number

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {
            "status":           "ok",
            "ollama":           "online",
            "available_models": models,
            "rag_chunks":       rag_chunks,
            "feature_slices":   ["salary_tax", "freelance_tax", "business_tax"],
            "endpoints": {
                "salaried":  ["/api/v1/tax/calculate", "/api/v1/tax/explain"],
                "freelance": ["/api/v1/tax/freelance/calculate", "/api/v1/tax/freelance/explain"],
                "business":  ["/api/v1/tax/business/calculate", "/api/v1/tax/business/explain"],
            },
        }
    except httpx.RequestError:
        return {
            "status":           "degraded",
            "ollama":           "offline",
            "available_models": [],
            "rag_chunks":       rag_chunks,
            "feature_slices":   ["salary_tax", "freelance_tax", "business_tax"],
        }
