import re
from decimal import Decimal, InvalidOperation


def citation_accuracy(answer: str, allowed_citations: list[str]) -> float:
    if not allowed_citations: return 0.0
    found=re.findall(r"\[([^\]]+)\]",answer)
    return sum(x in allowed_citations for x in found)/max(1,len(found))

def figure_consistency(answer: str, expected_tax) -> bool:
    try: val=int(Decimal(str(expected_tax)))
    except (InvalidOperation,ValueError): return False
    return any(s in answer for s in {str(val),f"{val:,}",f"PKR {val:,}"})

def groundedness(answer: str, source_text: str, citations: list[str]) -> float:
    if not answer.strip() or not source_text.strip(): return 0.0
    terms={x.lower() for x in re.findall(r"\b[A-Za-z]{5,}\b", source_text)[:500]}
    words={x.lower() for x in re.findall(r"\b[A-Za-z]{5,}\b", answer)}
    overlap=len(terms&words)/max(1,len(words))
    cite_bonus=0.2 if citations else 0.0
    return min(1.0,overlap+cite_bonus)
