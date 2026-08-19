import json
from datetime import datetime, timezone
from decimal import Decimal

from rules_engine.core import TaxResult


class DecimalEncoder(json.JSONEncoder):
    """Handles Decimal serialization for audit logs."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def build_audit_record(result: TaxResult) -> dict:
    """
    Builds an immutable audit record from a TaxResult.
    Every calculation must produce one of these.
    """
    return {
        "audit_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tax_year": result.input.tax_year,
        "taxpayer_type": result.input.taxpayer_type,
        "annual_income": str(result.input.annual_income),
        "rule_applied": result.rule_applied,
        "source_document": result.source_document,
        "source_section": result.source_section,
        "taxable_income": str(result.taxable_income),
        "tax_payable": str(result.tax_payable),
        "effective_rate": str(result.effective_rate),
        "ca_verified": result.ca_verified,
        "calculation_steps": result.calculation_steps,
    }


def audit_to_json(result: TaxResult) -> str:
    """Returns audit record as formatted JSON string."""
    record = build_audit_record(result)
    return json.dumps(record, indent=2, cls=DecimalEncoder)