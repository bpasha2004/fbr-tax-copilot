"""Deterministic local AI provider for full-stack development without Ollama.
It never invents tax figures: it formats only verified calculator output.
"""
from ai.base import AIProvider
from config.settings import settings


class LocalProvider(AIProvider):
    async def explain_tax_result(self, audit_record: dict, user_question: str, language: str = "english", dev_mode: bool = False) -> dict:
        tax = int(float(audit_record.get("tax_payable", 0)))
        income = int(float(audit_record.get("annual_income", 0)))
        text = (
            f"IRIS FILING ENTRIES:\n"
            f"  Taxpayer type: {audit_record.get('taxpayer_type')}\n"
            f"  Tax year: {audit_record.get('tax_year')}\n"
            f"  Tax payable: PKR {tax:,}\n\n"
            f"COMPUTATION: PKR {income:,} → {audit_record.get('rule_applied')} → PKR {tax:,}.\n"
            f"Legal: {audit_record.get('source_document')}, {audit_record.get('source_section')}.\n"
            f"CA Verification: {audit_record.get('ca_verified')}."
        )
        return {
            "explanation": text,
            "model_used": "local-deterministic",
            "model_failed": False,
            "language": language,
            "source_document": audit_record.get("source_document"),
            "source_section": audit_record.get("source_section"),
            "tax_payable": audit_record.get("tax_payable"),
            "ca_verified": audit_record.get("ca_verified"),
            "rag_context_used": False,
            "rag_citations": [],
            "confidence": 1.0,
            "refused": False,
            "hallucination_detected": False,
            "hallucination_flags": [],
            "iris_entries": audit_record.get("iris_entries", []),
        }


def get_local_provider() -> LocalProvider:
    return LocalProvider()
