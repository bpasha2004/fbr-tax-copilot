"""
IRIS 2.0 Portal Field Mappings — Salaried Taxpayer
Return Form: 114 (Individual Income Tax Return)
Tab path references verified against FBR IRIS 2.0 portal layout (portal labels are configurable; verify the exact labels for the selected tax year before filing).
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


SALARY_IRIS_MAP: dict[str, IRISField] = {
    # ── Tab: Income ──────────────────────────────────────────────────────────
    "gross_salary": IRISField(
        tab="Income",
        sub_tab="Salary / Wages",
        field_label="Salary, Wages and Other Perquisites Received",
        box_code=9000,
        legal_clause="ITO 2001, Section 12 r/w {source_document}, First Schedule, Part I, Division I",
        instructions="Enter total gross salary including all allowances. Obtain Form 149 from employer.",
    ),
    "exempt_salary": IRISField(
        tab="Income",
        sub_tab="Salary / Wages",
        field_label="Less: Exempt Salary Income [lower of 25% or Rs. 840,000]",
        box_code=9002,
        legal_clause="ITO 2001, Section 12(2)(c); {source_document} exemption rule — verify against the selected tax year",
        instructions="System calculates: min(gross_salary × 25%, 840,000). Do not override manually.",
    ),
    "net_taxable_salary": IRISField(
        tab="Income",
        sub_tab="Salary / Wages",
        field_label="Net Taxable Income from Salary (Box 9000 minus Box 9002)",
        box_code=9010,
        legal_clause="ITO 2001, Section 12(1)",
        instructions="Auto-computed. Verify against employer's certificate (Form 149).",
    ),
    # ── Tab: Tax Computation ─────────────────────────────────────────────────
    "tax_on_salary": IRISField(
        tab="Tax Computation",
        sub_tab="Tax on Income",
        field_label="Tax on Salary Income — Progressive Slabs",
        box_code=9200,
        legal_clause="{source_document}, First Schedule, Part I, Division I, versioned tiers",
        instructions="Auto-calculated from slab engine. Verify using slab table: T1:0%, T2:1%, T3:11%, T4:23%, T5:30%, T6:35%.",
    ),
    "tax_credits": IRISField(
        tab="Tax Computation",
        sub_tab="Tax Credits",
        field_label="Tax Credits (Education, Donation, Life Insurance, Pension)",
        box_code=9210,
        legal_clause="ITO 2001, Sections 61 (donation), 62 (investment), 63 (life ins.), 64 (pension fund)",
        instructions="Enter total credits availed. Attach supporting documentation for each credit claimed.",
    ),
    "total_tax_chargeable": IRISField(
        tab="Tax Computation",
        sub_tab="Net Tax",
        field_label="Total Tax Chargeable (Box 9200 minus Box 9210)",
        box_code=9300,
        legal_clause="ITO 2001, Section 4",
        instructions="Net tax before WHT adjustments.",
    ),
    "wht_deducted_149": IRISField(
        tab="Tax Computation",
        sub_tab="Tax Deducted / Collected",
        field_label="Tax Deducted at Source by Employer under Section 149",
        box_code=9400,
        legal_clause="ITO 2001, Section 149 — Employer withholding obligation",
        instructions="Enter total WHT deducted as shown on Form 149 / employer certificate.",
    ),
    "net_tax_payable": IRISField(
        tab="Tax Computation",
        sub_tab="Net Tax",
        field_label="Net Tax Payable / (Refundable) [Box 9300 minus Box 9400]",
        box_code=9500,
        legal_clause="ITO 2001, Section 137 — Payment of Tax",
        instructions="Positive = tax due by 30 September. Negative = refund claimable under Section 170.",
    ),
}


def build_iris_output(audit_record: dict) -> list[dict]:
    """
    Generates IRIS 2.0 filing guide from a salary tax audit record.
    Returns advisor-ready list of portal entry instructions.
    """
    income    = float(audit_record.get("annual_income", 0))
    tax       = float(audit_record.get("tax_payable", 0))
    audit_record.get("source_section", "")

    exempt = min(income * 0.25, 840_000)
    net_taxable = income - exempt

    entries = [
        {
            "tab":         SALARY_IRIS_MAP["gross_salary"].tab,
            "sub_tab":     SALARY_IRIS_MAP["gross_salary"].sub_tab,
            "field":       SALARY_IRIS_MAP["gross_salary"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['gross_salary'].box_code}",
            "value":       f"PKR {income:,.0f}",
            "legal_clause": SALARY_IRIS_MAP["gross_salary"].legal_clause.format(source_document=audit_record.get("source_document", "Applicable FBR source")),
            "note":        SALARY_IRIS_MAP["gross_salary"].instructions,
        },
        {
            "tab":         SALARY_IRIS_MAP["exempt_salary"].tab,
            "sub_tab":     SALARY_IRIS_MAP["exempt_salary"].sub_tab,
            "field":       SALARY_IRIS_MAP["exempt_salary"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['exempt_salary'].box_code}",
            "value":       f"PKR {exempt:,.0f}",
            "legal_clause": SALARY_IRIS_MAP["exempt_salary"].legal_clause.format(source_document=audit_record.get("source_document", "Applicable FBR source")),
            "note":        SALARY_IRIS_MAP["exempt_salary"].instructions,
        },
        {
            "tab":         SALARY_IRIS_MAP["net_taxable_salary"].tab,
            "sub_tab":     SALARY_IRIS_MAP["net_taxable_salary"].sub_tab,
            "field":       SALARY_IRIS_MAP["net_taxable_salary"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['net_taxable_salary'].box_code}",
            "value":       f"PKR {net_taxable:,.0f}",
            "legal_clause": SALARY_IRIS_MAP["net_taxable_salary"].legal_clause,
            "note":        SALARY_IRIS_MAP["net_taxable_salary"].instructions,
        },
        {
            "tab":         SALARY_IRIS_MAP["tax_on_salary"].tab,
            "sub_tab":     SALARY_IRIS_MAP["tax_on_salary"].sub_tab,
            "field":       SALARY_IRIS_MAP["tax_on_salary"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['tax_on_salary'].box_code}",
            "value":       f"PKR {tax:,.0f}",
            "legal_clause": SALARY_IRIS_MAP["tax_on_salary"].legal_clause.format(source_document=audit_record.get("source_document", "Applicable FBR source")),
            "note":        f"Tier applied: {audit_record.get('rule_applied', '')}. Verify from the indexed authoritative source for the selected tax year.",
        },
        {
            "tab":         SALARY_IRIS_MAP["wht_deducted_149"].tab,
            "sub_tab":     SALARY_IRIS_MAP["wht_deducted_149"].sub_tab,
            "field":       SALARY_IRIS_MAP["wht_deducted_149"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['wht_deducted_149'].box_code}",
            "value":       "As per Form 149 (obtain from employer)",
            "legal_clause": SALARY_IRIS_MAP["wht_deducted_149"].legal_clause,
            "note":        SALARY_IRIS_MAP["wht_deducted_149"].instructions,
        },
        {
            "tab":         SALARY_IRIS_MAP["net_tax_payable"].tab,
            "sub_tab":     SALARY_IRIS_MAP["net_tax_payable"].sub_tab,
            "field":       SALARY_IRIS_MAP["net_tax_payable"].field_label,
            "box":         f"Box {SALARY_IRIS_MAP['net_tax_payable'].box_code}",
            "value":       f"PKR {tax:,.0f} [less WHT from Box 9400]",
            "legal_clause": SALARY_IRIS_MAP["net_tax_payable"].legal_clause,
            "note":        SALARY_IRIS_MAP["net_tax_payable"].instructions,
        },
    ]
    return entries
