"""
Business / Non-Salaried Individual Tax Calculator
Versioned First Schedule, Part I, Division II rules (2025-26 and 2026-27).
"""
import dataclasses
from decimal import Decimal

from rules_engine.core import RulesEngine, TaxInput
from rules_engine.tax_slabs import get_rules_for_year
from rules_engine.validation import validate_tax_input
from src.business_tax.documents import BusinessDocumentValidator
from src.business_tax.iris_map import build_iris_output


class BusinessTaxCalculator:

    def __init__(self, tax_year: str = "2026-27", dev_mode: bool = False):
        self.tax_year = tax_year
        self.dev_mode = dev_mode
        self._engine  = self._build_engine()

    def _build_engine(self) -> RulesEngine:
        from config.settings import settings
        bypass_ca = self.dev_mode or not settings.REQUIRE_CA_VALIDATION
        if bypass_ca:
            rules = [dataclasses.replace(r, ca_verified=True) for r in get_rules_for_year(self.tax_year, "business")]
        else:
            rules = get_rules_for_year(self.tax_year, "business")

        if not rules:
            raise ValueError(f"No business individual rules found for tax year {self.tax_year}")
        return RulesEngine(rules)

    def calculate(
        self,
        net_business_income: float,
        documents: list[str] | None = None,
    ) -> dict:
        """
        Calculate business individual tax (Division II slabs).
        Returns audit record + IRIS filing guide + document checklist.
        """
        validator = BusinessDocumentValidator()
        doc_check = validator.validate(documents or [])

        tax_input = validate_tax_input(net_business_income, "business", self.tax_year)
        result    = self._engine.calculate(tax_input)

        audit = {
            "taxpayer_type":     result.input.taxpayer_type,
            "tax_year":          result.input.tax_year,
            "annual_income":     float(result.input.annual_income),
            "taxable_income":    float(result.taxable_income),
            "tax_payable":       float(result.tax_payable),
            "effective_rate":    float(result.effective_rate),
            "rule_applied":      result.rule_applied,
            "source_document":   result.source_document,
            "source_section":    result.source_section,
            "ca_verified":       result.ca_verified,
            "calculation_steps": result.calculation_steps,
        }

        return {
            **audit,
            "iris_entries":   build_iris_output(audit),
            "document_check": doc_check,
        }
