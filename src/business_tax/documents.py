"""
Business Tax — Mandatory Document Validator
Required documents for non-salaried individual / AOP return filing.
"""
from dataclasses import dataclass


@dataclass
class DocumentCheck:
    document: str
    required: bool
    present: bool
    legal_basis: str
    consequence_if_missing: str

    @property
    def ok(self) -> bool:
        return not self.required or self.present


BUSINESS_REQUIRED_DOCUMENTS = [
    {
        "key":        "ntn",
        "name":       "National Tax Number (NTN) Certificate",
        "required":   True,
        "legal_basis": "ITO 2001, Section 181 — NTN mandatory for all business taxpayers",
        "consequence": "Cannot file business return. Higher WHT rates apply (non-filer rates).",
    },
    {
        "key":        "bank_statement",
        "name":       "Business Bank Statements (all accounts, 12 months)",
        "required":   True,
        "legal_basis": "ITO 2001, Section 177 — Record keeping obligation; FBR IRIS wealth statement reconciliation",
        "consequence": "Income under-declaration risk. FBR may estimate income based on bank credits.",
    },
    {
        "key":        "accounts",
        "name":       "Annual Accounts / Statement of Accounts (P&L, Balance Sheet)",
        "required":   True,
        "legal_basis": "ITO 2001, Section 174 — Maintenance of accounts; audited for turnover > 25M",
        "consequence": "Return may be treated as defective. Turnover above Rs. 25M requires audited accounts.",
    },
    {
        "key":        "sales_tax",
        "name":       "Sales Tax Returns (if registered — turnover > 10M threshold)",
        "required":   False,
        "legal_basis": "Sales Tax Act 1990, Section 26 — Monthly return filing; cross-matched by FBR",
        "consequence": "Discrepancy between income tax turnover and sales tax returns triggers audit notice.",
    },
    {
        "key":        "advance_tax_challans",
        "name":       "Advance Tax Payment Challans (Sec. 147 — quarterly payments)",
        "required":   False,
        "legal_basis": "ITO 2001, Section 147 — Advance tax due quarterly for estimated income",
        "consequence": "Default surcharge under Section 205 if advance tax not paid. Penalty up to 100% of tax.",
    },
    {
        "key":        "wht_certificates",
        "name":       "WHT Certificates from Clients (Sec. 153 deductions)",
        "required":   False,
        "legal_basis": "ITO 2001, Section 153 — WHT on services/goods; Rule 43 certificate issuance",
        "consequence": "Cannot claim WHT credit without certificate. Excess tax paid without refund eligibility.",
    },
]


class BusinessDocumentValidator:
    """Validates mandatory documents for business individual return filing."""

    def validate(self, submitted: list[str]) -> dict:
        submitted_lower = [s.lower().strip() for s in submitted]
        checks = []

        for doc in BUSINESS_REQUIRED_DOCUMENTS:
            present = any(doc["key"] in s for s in submitted_lower)
            checks.append(DocumentCheck(
                document=doc["name"],
                required=doc["required"],
                present=present,
                legal_basis=doc["legal_basis"],
                consequence_if_missing=doc["consequence"],
            ))

        missing_required = [c for c in checks if c.required and not c.present]

        return {
            "all_clear":        len(missing_required) == 0,
            "missing_required": [c.document for c in missing_required],
            "checklist": [
                {
                    "document":    c.document,
                    "required":    c.required,
                    "present":     c.present,
                    "status":      "OK" if c.ok else "MISSING",
                    "legal_basis": c.legal_basis,
                    "if_missing":  c.consequence_if_missing,
                }
                for c in checks
            ],
        }
