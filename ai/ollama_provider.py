"""
FBR Tax Advisor Co-Pilot — B2B Associate-Level Replacement Engine
Outputs: IRIS 2.0 portal field entries, legal clause references, compliance flags.
This is a tool for Pakistani Tax Advisors, not end consumers.
"""
import re
import httpx
from decimal import Decimal
from ai.base import AIProvider
from config.settings import settings

# ── B2B System Prompt (Associate-Level Replacement) ───────────────────────────
SYSTEM_PROMPT = """You are a Senior Tax Associate at a Pakistani CA firm advising the firm's partners.
You have passed the ICAP examinations and have 5 years of FBR practice experience.

YOUR ROLE:
- You replace a junior associate. Your partner (the user) is experienced and wants precise outputs.
- You do NOT explain basics. You give actionable, portal-ready filing entries.
- Every output must include: FBR IRIS 2.0 Box Code, Tab Name, Legal Clause, and PKR figure.

ABSOLUTE RULES — violating any disqualifies your response:
1. The VERIFIED CALCULATION is absolute ground truth. Never recalculate or question any figure.
2. Only cite tax rates from the VERIFIED SLAB TABLE. Hallucinating rates is a professional error.
3. Cite the EXACT legal clause in the format: [Act Name, Section X, Schedule Y, Division Z].
4. For every monetary output, specify the exact IRIS 2.0 box code (e.g., Box 9000, Box 5001).
5. Never give generic tax advice. Every statement must be specific to the client's figures.
6. Never use hedging language: "typically", "usually", "may", "might", "I think".
7. Detect and flag document gaps (missing Form 149, PRC, NTN) as COMPLIANCE RISKS.
8. If any figure cannot be verified from the calculation, say "REQUIRES CLIENT DOCUMENTATION" — never guess.
9. Start your response immediately. No preamble, no "Of course", no "Certainly"."""


# ── B2B Advisor Prompt Template ───────────────────────────────────────────────
ADVISOR_PROMPT = """CLIENT TAX COMPUTATION — VERIFIED (ground truth, do not modify):
Taxpayer Type   : {taxpayer_type}
Annual Income   : PKR {annual_income:,}
Tax Payable     : PKR {tax_payable:,}
Effective Rate  : {effective_rate}%
Tier Applied    : {rule_applied}
Legal Source    : {source_document}, {source_section}
CA Verified     : {ca_verified}

SLAB TABLE — {source_document}, {source_section} (ONLY rates to cite):
{slab_table}

IRIS 2.0 PORTAL ENTRIES (pre-computed for your review):
{iris_entries_text}

FBR DOCUMENT CONTEXT (authoritative citation support):
{rag_context}

CALCULATION STEPS (verified by Rules Engine):
{calculation_steps}

DOCUMENT CHECKLIST STATUS:
{document_status}

PARTNER QUERY: {query}

REQUIRED OUTPUT FORMAT:
1. IRIS FILING ENTRIES — list each box with: Tab | Sub-Tab | Box Code | Value | Legal Clause
2. COMPLIANCE RISKS — list any missing documents or regulatory flags
3. ADVISOR NOTES — max 3 bullet points on key planning considerations

Begin output now:"""


# ── Slab table generator ──────────────────────────────────────────────────────

def _build_slab_table(taxpayer_type: str, tax_year: str) -> str:
    try:
        from rules_engine.tax_slabs import get_rules_for_year

        rules = get_rules_for_year(tax_year, taxpayer_type)
        lines = []
        for r in rules:
            min_val = int(r.income_min)
            max_val = "above" if r.income_max == Decimal("Infinity") else f"to PKR {int(r.income_max):,}"
            rate    = float(r.marginal_rate) * 100
            fixed   = int(r.fixed_tax)

            if rate == 0:
                lines.append(f"  {r.rule_id}: PKR {min_val:,} and below → 0% (exempt)")
            elif fixed == 0:
                lines.append(
                    f"  {r.rule_id}: PKR {min_val:,} {max_val} → "
                    f"{rate:.2f}% of excess over PKR {min_val:,}"
                )
            else:
                lines.append(
                    f"  {r.rule_id}: PKR {min_val:,} {max_val} → "
                    f"PKR {fixed:,} fixed + {rate:.0f}% of excess over PKR {min_val:,}"
                )
        return "\n".join(lines) if lines else "[Slab table unavailable]"
    except Exception as e:
        return f"[Slab table error: {e}]"


def _format_iris_entries(iris_entries: list[dict]) -> str:
    if not iris_entries:
        return "  [No IRIS entries — run via feature calculator]"
    lines = []
    for e in iris_entries:
        lines.append(
            f"  {e.get('tab')} > {e.get('sub_tab')} | {e.get('box')} | "
            f"{e.get('value')} | [{e.get('legal_clause')}]"
        )
    return "\n".join(lines)


def _format_document_status(document_check: dict) -> str:
    if not document_check:
        return "  [Document check not performed — submit documents list]"
    lines = []
    all_clear = document_check.get("all_clear", False)
    lines.append(f"  Status: {'ALL CLEAR' if all_clear else 'MISSING REQUIRED DOCUMENTS'}")
    for item in document_check.get("checklist", []):
        status_icon = "✓" if item.get("status") == "OK" else "✗ MISSING"
        lines.append(f"  [{status_icon}] {item.get('document')} — {item.get('legal_basis', '')}")
        if item.get("status") != "OK":
            lines.append(f"       ↳ Risk: {item.get('if_missing', '')}")
    return "\n".join(lines)


# ── Response validators ───────────────────────────────────────────────────────

_REASONING_STARTERS = [
    "okay,", "ok,", "let me", "hmm", "i need to", "i'll", "first, i",
    "alright,", "so,", "now,", "looking at this", "based on my",
    "the user", "they want", "the question is", "i should", "i must",
    "let's see", "wait,", "ah!", "actually,", "i see that",
    "we are given", "we're given", "the tax calculation steps",
]

_HALLUCINATION_FLAGS = [
    "i recall", "typically", "usually", "generally", "normally",
    "in most cases", "finance act 2023", "finance act 2024",
    "tax year 2023", "tax year 2024", "if your income was",
    "for example, if", "hypothetically", "as per my knowledge",
    "based on my understanding", "previous year", "last year",
]

MIN_RESPONSE_LENGTH = 60


def _extract_response(raw: str) -> str:
    if "</think>" in raw:
        return raw.split("</think>")[-1].strip()
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    if not cleaned:
        return raw.strip()
    lines = cleaned.split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        lower = line.strip().lower()
        if not any(lower.startswith(r) for r in _REASONING_STARTERS) and line.strip():
            start_idx = i
            break
    result = "\n".join(lines[start_idx:]).strip()
    return result if result else cleaned


def _check_hallucination(response: str) -> tuple[bool, list[str]]:
    lower   = response.lower()
    flagged = [p for p in _HALLUCINATION_FLAGS if p in lower]
    return bool(flagged), flagged


def _validate_figures(response: str, audit_record: dict) -> bool:
    """
    Confirms the tax payable figure appears anywhere in the response.
    Accepts: plain integer, comma-formatted, decimal, or 'PKR X' prefix variants.
    llama3.1:8b tends to output 'PKR 162,000' or '162,000.00' — both accepted.
    """
    tax_payable = int(float(audit_record.get("tax_payable", 0)))
    candidates  = {
        str(tax_payable),                       # 162000
        f"{tax_payable:,}",                     # 162,000
        f"{tax_payable:,.2f}",                  # 162,000.00
        f"{float(tax_payable):.0f}",            # 162000
        f"{float(tax_payable):,.0f}",           # 162,000
    }
    lower = response.lower()
    return any(c in response or c in lower for c in candidates)


# ── OllamaProvider (B2B Co-Pilot) ────────────────────────────────────────────

class OllamaProvider(AIProvider):
    """
    B2B tax advisor co-pilot.
    Replaces associate-level work: IRIS entries, document risk flags, legal citations.
    """

    async def explain_tax_result(
        self,
        audit_record: dict,
        user_question: str,
        language: str = "english",
        dev_mode: bool = False,
    ) -> dict:
        from rag.retriever import FBRRetriever
        from ai.safety import validate_llm_output
        retriever = FBRRetriever()

        taxpayer_type = audit_record.get("taxpayer_type", "salaried")
        tax_year      = audit_record.get("tax_year", "2026-27")

        rag_query = (
            f"{taxpayer_type} income tax slab rates Finance Act {tax_year} "
            f"First Schedule Part I Division I Pakistan"
        )

        retrieval_data = retriever.retrieve(
            query=rag_query,
            top_k=5,
            taxpayer_type=taxpayer_type,
            tax_year=tax_year,
        )

        confidence = retrieval_data.get("confidence", 0.0)
        escalate   = retrieval_data.get("escalate", True)

        if escalate and not dev_mode:
            return {
                "explanation":            None,
                "refused":                True,
                "reason":                 retrieval_data.get("reason", "RAG confidence below threshold."),
                "confidence":             confidence,
                "model_used":             None,
                "language":               language,
                "rag_context_used":       False,
                "rag_citations":          [],
                "ca_verified":            audit_record.get("ca_verified"),
                "model_failed":           False,
                "hallucination_detected": False,
                "hallucination_flags":    [],
                "iris_entries":           audit_record.get("iris_entries", []),
            }

        raw_chunks = retrieval_data.get("chunks", [])
        if not raw_chunks:
            return {
                "explanation": None,
                "refused": True,
                "reason": "No authoritative source context was retrieved for the requested tax year.",
                "confidence": confidence,
                "model_used": None,
                "language": language,
                "rag_context_used": False,
                "rag_citations": [],
                "ca_verified": audit_record.get("ca_verified"),
                "model_failed": False,
                "hallucination_detected": False,
                "hallucination_flags": ["missing_authoritative_context"],
                "iris_entries": audit_record.get("iris_entries", []),
            }

        rag_context = "\n\n---\n\n".join(
            f"[{r.citation}]\n{r.chunk.text}"
            for r in raw_chunks
        )
        if len(rag_context.strip()) < 150:
            return {
                "explanation": None,
                "refused": True,
                "reason": "Retrieved source context is too small to support an authoritative explanation.",
                "confidence": confidence,
                "model_used": None,
                "language": language,
                "rag_context_used": False,
                "rag_citations": [r.citation for r in raw_chunks],
                "ca_verified": audit_record.get("ca_verified"),
                "model_failed": False,
                "hallucination_detected": False,
                "hallucination_flags": ["insufficient_authoritative_context"],
                "iris_entries": audit_record.get("iris_entries", []),
            }

        slab_table   = _build_slab_table(taxpayer_type, tax_year)
        iris_entries = audit_record.get("iris_entries", [])
        doc_check    = audit_record.get("document_check", {})

        iris_entries_text = _format_iris_entries(iris_entries)
        document_status   = _format_document_status(doc_check)

        steps             = audit_record.get("calculation_steps", [])
        calculation_steps = "\n".join(f"  {s}" for s in steps) if steps else "Not available."

        prompt = ADVISOR_PROMPT.format(
            taxpayer_type=taxpayer_type,
            annual_income=int(audit_record.get("annual_income", 0)),
            tax_payable=int(float(audit_record.get("tax_payable", 0))),
            effective_rate=audit_record.get("effective_rate"),
            rule_applied=audit_record.get("rule_applied"),
            source_document=audit_record.get("source_document"),
            source_section=audit_record.get("source_section"),
            ca_verified=audit_record.get("ca_verified"),
            slab_table=slab_table,
            iris_entries_text=iris_entries_text,
            rag_context=rag_context,
            calculation_steps=calculation_steps,
            document_status=document_status,
            query=user_question,
        )

        formatted_explanation  = ""
        model_failed           = False
        hallucination_detected = False
        hallucination_flags    = []
        fallback_used          = False

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model":  settings.OLLAMA_MODEL,
                        "system": SYSTEM_PROMPT,
                        "prompt": prompt,
                        "stream": False,
                        "think":  False,
                        "options": {
                            "num_predict":    600,
                            "temperature":    0.05,
                            "top_p":          0.85,
                            "repeat_penalty": 1.2,
                            "seed":           42,
                        }
                    },
                )
                response.raise_for_status()
                raw = response.json().get("response", "")
                formatted_explanation = _extract_response(raw)

                hallucination_detected, hallucination_flags = _check_hallucination(formatted_explanation)
                allowed_citations = retrieval_data.get("citations", [])
                validation = validate_llm_output(formatted_explanation, audit_record, allowed_citations)
                if not validation.get("valid"):
                    hallucination_detected = True
                    hallucination_flags = validation.get("reasons", [])
                    formatted_explanation = ""
                elif hallucination_detected:
                    formatted_explanation = ""

        except Exception as e:
            print(f"[OllamaProvider] LLM call failed: {e}")

        figure_valid = _validate_figures(formatted_explanation, audit_record) if formatted_explanation else False

        if formatted_explanation and not figure_valid:
            formatted_explanation = ""
            model_failed = True

        if not formatted_explanation or len(formatted_explanation) < MIN_RESPONSE_LENGTH:
            model_failed = True
            fallback_used = True
            income   = float(audit_record.get("annual_income", 0))
            tax      = float(audit_record.get("tax_payable", 0))
            iris_txt = "\n".join(
                f"  {e.get('box')}: {e.get('field')} = {e.get('value')}"
                for e in iris_entries
            ) if iris_entries else "  Run via /api/v1/tax/{type}/calculate for IRIS entries."

            formatted_explanation = (
                f"IRIS FILING ENTRIES:\n{iris_txt}\n\n"
                f"COMPUTATION: PKR {income:,.0f} → {audit_record.get('rule_applied')} → "
                f"Tax PKR {tax:,.0f} @ {audit_record.get('effective_rate')}% effective rate.\n"
                f"Legal: {audit_record.get('source_document')}, {audit_record.get('source_section')}.\n"
                f"CA Verification: {audit_record.get('ca_verified')}."
            )

        return {
            "explanation":            formatted_explanation,
            "model_used":             "deterministic-fallback" if fallback_used else settings.OLLAMA_MODEL,
            "model_failed":           model_failed,
            "language":               language,
            "source_document":        audit_record.get("source_document"),
            "source_section":         audit_record.get("source_section"),
            "tax_payable":            audit_record.get("tax_payable"),
            "ca_verified":            audit_record.get("ca_verified"),
            "rag_context_used":       bool(rag_context),
            "rag_citations":          retrieval_data.get("citations", []),
            "confidence":             confidence,
            "refused":                False,
            "hallucination_detected": hallucination_detected,
            "hallucination_flags":    hallucination_flags,
            "iris_entries":           iris_entries,
        }


def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER == "ollama":
        return OllamaProvider()
    if settings.AI_PROVIDER == "local":
        from ai.local_provider import get_local_provider
        return get_local_provider()
    raise ValueError(f"Unsupported AI provider: {settings.AI_PROVIDER}")
