"""
IRIS 2.0 Portal Field Mappings — Business / Non-Salaried Individual
Return Form: 114 (Individual) or 114(AOP)
{source_document}, First Schedule, Part I, Division II
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


BUSINESS_IRIS_MAP: dict[str, IRISField] = {
    # ── Tab: Income from Business ────────────────────────────────────────────
    "gross_receipts": IRISField(
        tab="Income from Business",
        sub_tab="Turnover / Receipts",
        field_label="Gross Business Receipts / Turnover",
        box_code=4000,
        legal_clause="ITO 2001, Section 18(1) — Income from Business",
        instructions="Enter total gross turnover. Must match annual accounts / bank statements.",
    ),
    "cost_of_sales": IRISField(
        tab="Income from Business",
        sub_tab="Deductions",
        field_label="Cost of Sales / Direct Costs (Sec. 22 assets / Sec. 21 expenses)",
        box_code=4100,
        legal_clause="ITO 2001, Section 21 (business expenditure) and Section 22 (depreciation)",
        instructions="Attach audited accounts or statement of accounts. Only allowable deductions per Section 21.",
    ),
    "gross_profit": IRISField(
        tab="Income from Business",
        sub_tab="Turnover / Receipts",
        field_label="Gross Profit (Box 4000 minus Box 4100)",
        box_code=4200,
        legal_clause="ITO 2001, Section 18",
        instructions="Auto-computed.",
    ),
    "admin_expenses": IRISField(
        tab="Income from Business",
        sub_tab="Deductions",
        field_label="Administrative and General Expenses",
        box_code=4300,
        legal_clause="ITO 2001, Section 20 — Deduction not otherwise provided for",
        instructions="Include rent, utilities, salaries of employees, professional fees. Exclude personal expenses.",
    ),
    "net_business_income": IRISField(
        tab="Income from Business",
        sub_tab="Net Income",
        field_label="Net Business Income (Box 4200 minus Box 4300)",
        box_code=4400,
        legal_clause="ITO 2001, Section 18(1) — Net taxable business income",
        instructions="This is the figure used for slab-rate tax computation under Division II.",
    ),
    # ── Tab: Tax Computation ─────────────────────────────────────────────────
    "tax_on_business": IRISField(
        tab="Tax Computation",
        sub_tab="Tax on Income",
        field_label="Tax on Business Income — Division II Progressive Slabs",
        box_code=9200,
        legal_clause="{source_document}, First Schedule, Part I, Division II, versioned tiers",
        instructions="Slab rates: T1:0%, T2:15%, T3:20%, T4:30%, T5:40%, T6:45%. Applied on Box 4400.",
    ),
    "advance_tax_paid": IRISField(
        tab="Tax Computation",
        sub_tab="Tax Deducted / Collected",
        field_label="Advance Tax and WHT Collected at Source",
        box_code=9400,
        legal_clause="ITO 2001, Section 147 (advance tax), Section 153 (WHT on services/goods)",
        instructions="Include advance tax paid quarterly (Sec. 147) and WHT certificates received from clients.",
    ),
    "net_tax_payable": IRISField(
        tab="Tax Computation",
        sub_tab="Net Tax",
        field_label="Net Tax Payable / (Refundable) [Box 9200 minus Box 9400]",
        box_code=9500,
        legal_clause="ITO 2001, Section 137",
        instructions="Pay positive balance via PSID/Challan by 30 September. Negative = refund under Section 170.",
    ),
}


def build_iris_output(audit_record: dict) -> list[dict]:
    """
    Generates IRIS 2.0 filing guide for business/non-salaried individual.
    Returns advisor-ready list of portal entry instructions.
    """
    income = float(audit_record.get("annual_income", 0))
    tax    = float(audit_record.get("tax_payable", 0))

    entries = [
        {
            "tab":          BUSINESS_IRIS_MAP["gross_receipts"].tab,
            "sub_tab":      BUSINESS_IRIS_MAP["gross_receipts"].sub_tab,
            "field":        BUSINESS_IRIS_MAP["gross_receipts"].field_label,
            "box":          f"Box {BUSINESS_IRIS_MAP['gross_receipts'].box_code}",
            "value":        f"PKR {income:,.0f}",
            "legal_clause": BUSINESS_IRIS_MAP["gross_receipts"].legal_clause,
            "note":         "Use net income if cost-of-sales already excluded. Otherwise enter gross turnover.",
        },
        {
            "tab":          BUSINESS_IRIS_MAP["net_business_income"].tab,
            "sub_tab":      BUSINESS_IRIS_MAP["net_business_income"].sub_tab,
            "field":        BUSINESS_IRIS_MAP["net_business_income"].field_label,
            "box":          f"Box {BUSINESS_IRIS_MAP['net_business_income'].box_code}",
            "value":        f"PKR {income:,.0f}",
            "legal_clause": BUSINESS_IRIS_MAP["net_business_income"].legal_clause,
            "note":         "This is the taxable base for Division II slab calculation.",
        },
        {
            "tab":          BUSINESS_IRIS_MAP["tax_on_business"].tab,
            "sub_tab":      BUSINESS_IRIS_MAP["tax_on_business"].sub_tab,
            "field":        BUSINESS_IRIS_MAP["tax_on_business"].field_label,
            "box":          f"Box {BUSINESS_IRIS_MAP['tax_on_business'].box_code}",
            "value":        f"PKR {tax:,.0f}",
            "legal_clause": BUSINESS_IRIS_MAP["tax_on_business"].legal_clause.format(source_document=audit_record.get("source_document", "Applicable FBR source")),
            "note":         f"Tier applied: {audit_record.get('rule_applied', '')}. Verify slab boundaries from the indexed authoritative source for the selected tax year.",
        },
        {
            "tab":          BUSINESS_IRIS_MAP["advance_tax_paid"].tab,
            "sub_tab":      BUSINESS_IRIS_MAP["advance_tax_paid"].sub_tab,
            "field":        BUSINESS_IRIS_MAP["advance_tax_paid"].field_label,
            "box":          f"Box {BUSINESS_IRIS_MAP['advance_tax_paid'].box_code}",
            "value":        "As per advance tax challans and WHT certificates",
            "legal_clause": BUSINESS_IRIS_MAP["advance_tax_paid"].legal_clause,
            "note":         "Attach Form CPR for each advance tax payment. WHT certificates from clients required.",
        },
        {
            "tab":          BUSINESS_IRIS_MAP["net_tax_payable"].tab,
            "sub_tab":      BUSINESS_IRIS_MAP["net_tax_payable"].sub_tab,
            "field":        BUSINESS_IRIS_MAP["net_tax_payable"].field_label,
            "box":          f"Box {BUSINESS_IRIS_MAP['net_tax_payable'].box_code}",
            "value":        f"PKR {tax:,.0f} minus Box 9400",
            "legal_clause": BUSINESS_IRIS_MAP["net_tax_payable"].legal_clause,
            "note":         "Generate PSID from IRIS for payment. Due 30 September for business returns.",
        },
    ]
    return entries
