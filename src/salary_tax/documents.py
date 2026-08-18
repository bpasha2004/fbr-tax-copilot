"""
Salary Tax — Mandatory Document Validator
Required documents for salaried return filing (FBR IRIS 2.0 — Form 114).
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


SALARY_REQUIRED_DOCUMENTS = [
    {
        "key":        "form_149",
        "name":       "Employer Certificate — Form 149 (Withholding Statement)",
        "required":   True,
        "legal_basis": "ITO 2001, Section 149 r/w Rule 44 of IT Rules 2002 — Employer must issue by 31 August",
        "consequence": "Cannot claim WHT credit (Box 9400). Full slab tax applies without offset.",
    },
    {
        "key":        "cnic",
        "name":       "CNIC / NICOP (Self)",
        "required":   True,
        "legal_basis": "FBR NTN Registration Policy; mandatory for IRIS portal access",
        "consequence": "Cannot file return without verified CNIC on IRIS.",
    },
    {
        "key":        "bank_statement",
        "name":       "Bank Statement (12 months — all salary credit accounts)",
        "required":   True,
        "legal_basis": "ITO 2001, Section 177 — Commissioner may require records during audit",
        "consequence": "Required for wealth statement reconciliation (Section 116). Keep on file even if not submitted.",
    },
    {
        "key":        "investment_proof",
        "name":       "Investment / Insurance Certificates (if claiming Sec. 62/63 credits)",
        "required":   False,
        "legal_basis": "ITO 2001, Sections 62 (investment in shares/units), 63 (contribution to life insurance)",
        "consequence": "Tax credit disallowed if documentation unavailable on audit.",
    },
    {
        "key":        "rental_income_docs",
        "name":       "Rental Agreement + Rent Receipts (if any rental income)",
        "required":   False,
        "legal_basis": "ITO 2001, Section 15 — Income from Property",
        "consequence": "Undisclosed rental income triggers penalty under Section 182.",
    },
]


class SalaryDocumentValidator:
    """
    Validates which mandatory salary documents have been submitted.
    Returns advisor-facing checklist with legal basis for each requirement.
    """

    def validate(self, submitted: list[str]) -> dict:
        submitted_lower = [s.lower().strip() for s in submitted]
        checks = []

        for doc in SALARY_REQUIRED_DOCUMENTS:
            present = any(doc["key"] in s for s in submitted_lower)
            checks.append(DocumentCheck(
                document=doc["name"],
                required=doc["required"],
                present=present,
                legal_basis=doc["legal_basis"],
                consequence_if_missing=doc["consequence"],
            ))

        missing_required = [c for c in checks if c.required and not c.present]
        all_clear        = len(missing_required) == 0

        return {
            "all_clear":        all_clear,
            "missing_required": [c.document for c in missing_required],
            "checklist": [
                {
                    "document":        c.document,
                    "required":        c.required,
                    "present":         c.present,
                    "status":          "OK" if c.ok else "MISSING",
                    "legal_basis":     c.legal_basis,
                    "if_missing":      c.consequence_if_missing,
                }
                for c in checks
            ],
        }
