"""Independent validation layer for LLM output."""
from decimal import Decimal, InvalidOperation
import re

def validate_llm_output(answer: str, audit: dict, allowed_citations: list[str]) -> dict:
    if not isinstance(answer,str) or len(answer.strip()) < 40:
        return {"valid":False,"reasons":["response_too_short"]}
    expected=str(int(float(audit.get("tax_payable",0))))
    normalized=answer.replace(',','')
    if expected not in normalized:
        return {"valid":False,"reasons":["tax_figure_mismatch"]}
    found=re.findall(r"\[([^\]]+)\]",answer)
    invalid=[c for c in found if c not in allowed_citations]
    if invalid: return {"valid":False,"reasons":["invalid_citation"]}
    forbidden={"i think","as per my knowledge","probably","maybe"}
    lower=answer.lower()
    if any(x in lower for x in forbidden): return {"valid":False,"reasons":["uncertain_language"]}
    return {"valid":True,"reasons":[],'citations':found}
