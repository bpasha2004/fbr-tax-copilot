from rag.base import RetrievalResult
from rag.vector_store import get_vector_store

CONFIDENCE_THRESHOLD = 0.72

CURRENT_SOURCE_URL = "https://download1.fbr.gov.pk/Docs/20266291261044366FinanceAct2026.pdf"

def _year_source_docs(taxpayer_type: str | None, tax_year: str | None):
    if tax_year == "2026-27":
        return ["Finance Act 2026"]
    return []

# ── Document routing map ──────────────────────────────────────────────────────
# Maps taxpayer_type to:
#   query_boost   — extra terms appended to query for stronger vector signal
#   where_docs    — EXACT ChromaDB document_name values to restrict search to
#                   (None = search all documents)
#   priority_docs — partial name fragments for post-reranking within results
#
# HOW TO EXTEND FOR NEW TAX CATEGORIES:
# 1. Add entry to DOCUMENT_ROUTING with appropriate docs
# 2. Add PDF to data/documents/fbr/ and re-run ingest_documents.py
# 3. No other code changes needed
#
# EXACT document_name values (from ChromaDB metadata):
#   "2025841183918948Circularno01Of2025 26Incometax"
#   "2025629106147620Financeact2025"
#   "20258181281745641Wht Ratecard"
#   "2026226162211364Incometaxordinance2001 Amended 20.02.2026"

DOCUMENT_ROUTING: dict[str, dict] = {
    "salaried": {
        "query_boost": (
            "salaried income tax slab rates tiers table structure "
            "Division I First Schedule Part I salary section 149 "
            "1% 11% 23% 30% 35% PKR 600000 1200000 2200000 3200000 4100000"
        ),
        # Restrict to Circular + Finance Act ONLY.
        # The Ordinance (1586 chunks) introduces noise from developer tax,
        # property tax, minimum tax sections. Excluded for salaried queries.
        "where_docs": [
            "2025841183918948Circularno01Of2025 26Incometax",
            "2025629106147620Financeact2025",
        ],
        "priority_docs": ["FinanceAct2026", "Circularno01", "Financeact2025"],
    },
    "corporate": {
        "query_boost": (
            "company corporate income tax rate First Schedule Division II "
            "super tax minimum tax section 113 turnover"
        ),
        "where_docs": [
            "2025629106147620Financeact2025",
            "2026226162211364Incometaxordinance2001 Amended 20.02.2026",
        ],
        "priority_docs": ["Financeact2025", "Incometaxordinance"],
    },
    "business": {
        "query_boost": (
            "business income NTN association persons AOP SME tax rate "
            "First Schedule Division III non-salaried individual"
        ),
        "where_docs": [
            "2025629106147620Financeact2025",
            "2026226162211364Incometaxordinance2001 Amended 20.02.2026",
        ],
        "priority_docs": ["Financeact2025", "Incometaxordinance"],
    },
    "wht": {
        "query_boost": (
            "withholding tax rate WHT section 153 152 149 "
            "payment goods services contracts rate card"
        ),
        "where_docs": [
            "20258181281745641Wht Ratecard",
            "2026226162211364Incometaxordinance2001 Amended 20.02.2026",
        ],
        "priority_docs": ["Wht Ratecard", "Incometaxordinance"],
    },
    "property": {
        "query_boost": (
            "immoveable property capital gains advance tax "
            "section 236C 236K transfer purchase sale"
        ),
        "where_docs": [
            "2025629106147620Financeact2025",
            "2026226162211364Incometaxordinance2001 Amended 20.02.2026",
        ],
        "priority_docs": ["Financeact2025", "Incometaxordinance"],
    },
    # Default: no restriction, search all documents
}

REQUIRED_CURRENT_DOCS = {
    "2026-27": ["FinanceAct2026"],
}

def _has_required_current_source(document_names: list[str], tax_year: str | None) -> bool:
    required = REQUIRED_CURRENT_DOCS.get(tax_year or "")
    if not required:
        return True
    names = [x.lower().replace(" ","") for x in document_names]
    return any(any(fragment.lower().replace(" ","") in n for fragment in required) for n in names)


class FBRRetriever:
    """
    Retrieves relevant FBR document chunks for a given tax query.

    Uses ChromaDB where-filter to restrict search to authoritative documents
    per taxpayer_type before vector similarity is computed. This prevents
    large documents (e.g. 1586-chunk Ordinance) from drowning out smaller
    but more relevant documents (e.g. the 26-chunk salaried tax Circular).
    """

    def __init__(self):
        self.store = get_vector_store()

    def _build_search_query(
        self,
        query: str,
        taxpayer_type: str | None,
        tax_year: str | None,
    ) -> str:
        routing = DOCUMENT_ROUTING.get(taxpayer_type or "", {})
        boost = routing.get("query_boost", "")
        parts = []
        if boost:
            parts.append(boost)
        if tax_year:
            parts.append(f"Finance Act {tax_year} First Schedule Pakistan")
        parts.append(query)
        return " | ".join(parts)

    def _build_where_filter(self, taxpayer_type: str | None, tax_year: str | None = None) -> dict | None:
        routing = DOCUMENT_ROUTING.get(taxpayer_type or "", {})
        where_docs = list(routing.get("where_docs") or [])
        if tax_year == "2026-27":
            where_docs = ["FinanceAct2026", "2026226162211364Incometaxordinance2001 Amended 20.02.2026"]
        if not where_docs:
            return None
        return {"document_name": {"$in": where_docs}}

    def _prioritize_results(
        self,
        results: list[RetrievalResult],
        taxpayer_type: str | None,
    ) -> list[RetrievalResult]:
        """Secondary reranking within already-filtered results."""
        routing = DOCUMENT_ROUTING.get(taxpayer_type or "", {})
        priority_docs = routing.get("priority_docs", [])
        if not priority_docs:
            return results

        priority  = []
        secondary = []
        for r in results:
            citation = r.citation or ""
            if any(doc.lower() in citation.lower() for doc in priority_docs):
                priority.append(r)
            else:
                secondary.append(r)

        ordered = priority + secondary
        return ordered if ordered else results

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        taxpayer_type: str | None = None,
        tax_year: str | None = None,
    ) -> dict:
        search_query  = self._build_search_query(query, taxpayer_type, tax_year)
        where_filter  = self._build_where_filter(taxpayer_type, tax_year)

        # Fetch more than top_k so reranking has material to work with
        fetch_k = min(top_k * 3, 20)
        if tax_year in REQUIRED_CURRENT_DOCS:
            try:
                indexed_names = self.store.get_document_names()
            except (OSError, RuntimeError, ValueError):
                indexed_names = []
            if not _has_required_current_source(indexed_names, tax_year):
                return {
                    "chunks": [], "citations": [], "confidence": 0.0, "escalate": True,
                    "reason": f"Authoritative source for tax year {tax_year} is not indexed. Ingest the current FBR Finance Act before generating an explanation."
                }

        raw_results = self.store.search(
            search_query,
            top_k=fetch_k,
            where_filter=where_filter,
        )

        if not raw_results:
            return {
                "chunks":     [],
                "citations":  [],
                "confidence": 0.0,
                "escalate":   True,
                "reason":     "No documents found in vector store.",
            }

        ordered = self._prioritize_results(raw_results, taxpayer_type)[:top_k]
        # Confidence must reflect the strongest retrieval score, not the first
        # item after document-priority reranking. Otherwise a lower-scoring
        # priority document can incorrectly force escalation.
        top_score = max(r.similarity_score for r in raw_results)
        escalate = top_score < CONFIDENCE_THRESHOLD

        return {
            "chunks":     ordered,
            "citations":  [r.citation for r in ordered],
            "confidence": round(top_score, 4),
            "escalate":   escalate,
            "reason": (
                f"Confidence {top_score:.4f} below threshold {CONFIDENCE_THRESHOLD}"
                if escalate else "OK"
            ),
        }

    def get_context_string(
        self,
        query: str,
        top_k: int = 3,
        taxpayer_type: str | None = None,
        tax_year: str | None = None,
    ) -> str:
        result = self.retrieve(
            query=query,
            top_k=top_k,
            taxpayer_type=taxpayer_type,
            tax_year=tax_year,
        )
        if not result["chunks"]:
            return ""
        parts = [f"[{r.citation}]\n{r.chunk.text}" for r in result["chunks"]]
        return "\n\n---\n\n".join(parts)
    