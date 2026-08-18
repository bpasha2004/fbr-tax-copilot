"""IT/ITeS export tax calculator for Section 154A."""
import dataclasses
from decimal import Decimal
from rules_engine.core import RulesEngine, TaxInput
from rules_engine.tax_slabs import get_rules_for_year
from src.freelance_tax.documents import FreelanceDocumentValidator
from src.freelance_tax.iris_map import build_iris_output

def _validate(value: float, tax_year: str, atl: bool, pseb_registered: bool):
    try: proceeds=Decimal(str(value))
    except Exception as exc: raise ValueError("Export proceeds must be a valid number.") from exc
    if not proceeds.is_finite(): raise ValueError("Export proceeds must be a finite number.")
    if proceeds < 0: raise ValueError("Export proceeds cannot be negative.")
    if tax_year not in {"2025-26","2026-27"}: raise ValueError(f"Tax year {tax_year} not supported for Section 154A.")
    return TaxInput(annual_income=proceeds,taxpayer_type="freelance",tax_year=tax_year)

class FreelanceTaxCalculator:
    def __init__(self,tax_year: str="2026-27",dev_mode: bool=False,atl: bool=True,pseb_registered: bool=True):
        self.tax_year=tax_year; self.dev_mode=dev_mode; self.atl=atl; self.pseb_registered=pseb_registered; self._engine=self._build_engine()
    def _rule_code(self):
        return ("PSEB_ATL" if self.pseb_registered and self.atl else
                "PSEB_NON_ATL" if self.pseb_registered else
                "OTHER_ATL" if self.atl else "OTHER_NON_ATL")
    def _build_engine(self):
        from config.settings import settings
        code=self._rule_code()
        rules=[r for r in get_rules_for_year(self.tax_year,"freelance") if code in r.rule_id]
        if not rules: raise ValueError(f"No Section 154A rule found for {self.tax_year} / {code}")
        bypass=self.dev_mode or not settings.REQUIRE_CA_VALIDATION
        if bypass: rules=[dataclasses.replace(r,ca_verified=True) for r in rules]
        return RulesEngine(rules)
    def calculate(self,gross_export_proceeds: float,documents: list[str]|None=None)->dict:
        doc_check=FreelanceDocumentValidator().validate(documents or [], require_prc=self.pseb_registered)
        tax_input=_validate(gross_export_proceeds,self.tax_year,self.atl,self.pseb_registered)
        result=self._engine.calculate(tax_input)
        proceeds=float(result.input.annual_income); tax=float(result.tax_payable); rate=float(result.rule_applied and result.tax_payable/result.taxable_income*100) if proceeds else 0.0
        audit={
          "taxpayer_type":"freelance","tax_regime":"Section 154A — IT/ITeS Export Withholding / Final Tax","tax_year":self.tax_year,
          "gross_proceeds":proceeds,"annual_income":proceeds,"taxable_income":proceeds,"tax_payable":tax,"effective_rate":rate,
          "rule_applied":result.rule_applied,"source_document":result.source_document,"source_section":result.source_section,
          "ca_verified":result.ca_verified,"is_final_tax":True,"atl":self.atl,"pseb_registered":self.pseb_registered,
          "calculation_steps":[f"Export Proceeds (PKR): {proceeds:,.2f}",f"Applicable rate: {rate:.2f}%",f"Tax = PKR {proceeds:,.2f} × {rate/100:.6f} = PKR {tax:,.2f}","Tax treatment: final/minimum treatment depends on the applicable Section 154A rule and taxpayer status."],
        }
        return {**audit,"iris_entries":build_iris_output(audit),"document_check":doc_check}
