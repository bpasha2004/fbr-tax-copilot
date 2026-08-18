"""Compatibility facade over the versioned tax-rule registry.

The source of truth is rules_engine/rules/*.json. No calculator should embed
2025/2026 slabs directly in application code.
"""
from dataclasses import replace
from decimal import Decimal
from datetime import date
import json
from pathlib import Path
from rules_engine.core import TaxRule

RULES_DIR = Path(__file__).resolve().parent / "rules"

def _load_one(path: Path) -> list[TaxRule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out=[]
    for r in data.get("rules",[]):
        out.append(TaxRule(
            rule_id=r["rule_id"], taxpayer_type=r["taxpayer_type"], tax_year=r["tax_year"],
            income_min=Decimal(r["income_min"]), income_max=Decimal(r["income_max"]),
            fixed_tax=Decimal(r["fixed_tax"]), marginal_rate=Decimal(r["marginal_rate"]),
            source_document=r["source_document"], source_section=r["source_section"],
            effective_date=date.fromisoformat(r["effective_date"]), ca_verified=bool(r.get("ca_verified",False)),
            ca_name=r.get("ca_name"), ca_verified_date=date.fromisoformat(r["ca_verified_date"]) if r.get("ca_verified_date") else None,
        ))
    return out

def load_all_rules() -> list[TaxRule]:
    rules=[]
    for path in sorted(RULES_DIR.glob("*.json")):
        rules.extend(_load_one(path))
    return rules

ALL_RULES = load_all_rules()
SALARIED_2025_26=[r for r in ALL_RULES if r.tax_year=="2025-26" and r.taxpayer_type=="salaried"]
BUSINESS_INDIVIDUAL_2025_26=[r for r in ALL_RULES if r.tax_year=="2025-26" and r.taxpayer_type=="business"]
FREELANCE_SECTION_154A=[r for r in ALL_RULES if r.tax_year=="2025-26" and r.taxpayer_type=="freelance"]

def get_rules_for_year(tax_year: str, taxpayer_type: str|None=None) -> list[TaxRule]:
    rules=[r for r in ALL_RULES if r.tax_year==tax_year]
    if taxpayer_type:
        rules=[r for r in rules if r.taxpayer_type==taxpayer_type]
    return rules

