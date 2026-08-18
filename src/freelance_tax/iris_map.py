"""
IRIS 2.0 Portal Field Mappings — IT/Software Freelance Export Income
Return Form: 114 (Individual) — Section 154A Final Tax Regime
All figures in PKR. PRC is the primary authoritative document.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class IRISField:
    tab: str
    sub_tab: str
    field_label: str
    box_code: int
    legal_clause: str
    instructions: str


FREELANCE_IRIS_MAP: dict[str, IRISField] = {
    # ── Tab: Income from Business ────────────────────────────────────────────
    "it_export_proceeds": IRISField(
        tab="Income from Business",
        sub_tab="IT / Software Exports",
        field_label="Gross IT/Software Export Proceeds Received",
        box_code=5000,
        legal_clause="ITO 2001, Section 154A(1) — IT/Software/BPO Export Proceeds",
        instructions="Enter total gross PKR equivalent of all foreign remittances received in the tax year. Source: bank PRCs.",
    ),
    "final_tax_154a": IRISField(
        tab="Income from Business",
        sub_tab="IT / Software Exports",
        field_label="Final Tax @ 0.25% under Section 154A (Box 5000 × 0.0025)",
        box_code=5001,
        legal_clause="ITO 2001, Section 154A(2); Finance Act 2026 — Extension of Final Tax Regime for IT exports",
        instructions="Auto-calculated: gross proceeds × 0.25%. This is your TOTAL tax liability — no further income tax applies.",
    ),
    # ── Tab: Withholding Tax Adjustments ────────────────────────────────────
    "wht_154a_deducted": IRISField(
        tab="Withholding Tax Adjustments",
        sub_tab="Tax Deducted at Source",
        field_label="WHT Deducted under Section 154A by Authorized Bank",
        box_code=7300,
        legal_clause="ITO 2001, Section 154A(3) — Bank's withholding obligation on remittance",
        instructions="Enter WHT already deducted by your bank as shown on bank certificate / PRC. Reduces net payable.",
    ),
    # ── Tab: Tax Computation ─────────────────────────────────────────────────
    "net_tax_payable": IRISField(
        tab="Tax Computation",
        sub_tab="Net Tax",
        field_label="Net Tax Payable under Section 154A [Box 5001 minus Box 7300]",
        box_code=9500,
        legal_clause="ITO 2001, Section 137 read with Section 154A",
        instructions="If bank already deducted WHT, this is normally zero. If under-deducted, pay balance by 30 September.",
    ),
}


def build_iris_output(audit_record: dict) -> list[dict]:
    """
    Generates IRIS 2.0 filing guide for Section 154A final tax.
    Returns advisor-ready list of portal entry instructions.
    """
    proceeds = float(audit_record.get("annual_income", 0))
    tax      = float(audit_record.get("tax_payable", 0))

    entries = [
        {
            "tab":          FREELANCE_IRIS_MAP["it_export_proceeds"].tab,
            "sub_tab":      FREELANCE_IRIS_MAP["it_export_proceeds"].sub_tab,
            "field":        FREELANCE_IRIS_MAP["it_export_proceeds"].field_label,
            "box":          f"Box {FREELANCE_IRIS_MAP['it_export_proceeds'].box_code}",
            "value":        f"PKR {proceeds:,.0f}",
            "legal_clause": FREELANCE_IRIS_MAP["it_export_proceeds"].legal_clause,
            "note":         "Sum of all PRC amounts. Convert USD at State Bank buying rate on date of receipt.",
        },
        {
            "tab":          FREELANCE_IRIS_MAP["final_tax_154a"].tab,
            "sub_tab":      FREELANCE_IRIS_MAP["final_tax_154a"].sub_tab,
            "field":        FREELANCE_IRIS_MAP["final_tax_154a"].field_label,
            "box":          f"Box {FREELANCE_IRIS_MAP['final_tax_154a'].box_code}",
            "value":        f"PKR {tax:,.0f} (= {proceeds:,.0f} × 0.25%)",
            "legal_clause": FREELANCE_IRIS_MAP["final_tax_154a"].legal_clause,
            "note":         "FINAL TAX. No further income tax on these proceeds. Declare as exempt in 'Income' tab.",
        },
        {
            "tab":          FREELANCE_IRIS_MAP["wht_154a_deducted"].tab,
            "sub_tab":      FREELANCE_IRIS_MAP["wht_154a_deducted"].sub_tab,
            "field":        FREELANCE_IRIS_MAP["wht_154a_deducted"].field_label,
            "box":          f"Box {FREELANCE_IRIS_MAP['wht_154a_deducted'].box_code}",
            "value":        "As per bank certificate / PRC (obtain from remittance bank)",
            "legal_clause": FREELANCE_IRIS_MAP["wht_154a_deducted"].legal_clause,
            "note":         "Attach copies of all PRCs and bank WHT certificates. Must match Box 7300 exactly.",
        },
        {
            "tab":          FREELANCE_IRIS_MAP["net_tax_payable"].tab,
            "sub_tab":      FREELANCE_IRIS_MAP["net_tax_payable"].sub_tab,
            "field":        FREELANCE_IRIS_MAP["net_tax_payable"].field_label,
            "box":          f"Box {FREELANCE_IRIS_MAP['net_tax_payable'].box_code}",
            "value":        f"PKR {tax:,.0f} minus Box 7300",
            "legal_clause": FREELANCE_IRIS_MAP["net_tax_payable"].legal_clause,
            "note":         "Normally zero if bank deducted correctly. If positive, pay via PSID before filing.",
        },
    ]
    return entries
