"""
Freelance / IT Export — Mandatory Document Validator
Required documents for Section 154A final tax filing.
PRC (Proceeds Realization Certificate) is the cornerstone document.
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


FREELANCE_REQUIRED_DOCUMENTS = [
    {
        "key":        "prc",
        "name":       "Proceeds Realization Certificate (PRC) — from authorized bank",
        "required":   True,
        "legal_basis": "ITO 2001, Section 154A(1); SBP BPRD Circular 02 of 2022 — mandatory for IT export remittances",
        "consequence": "Section 154A benefit disallowed. Full progressive income tax applies under Division II instead.",
    },
    {
        "key":        "bank_statement",
        "name":       "Bank Statement showing all foreign remittances (12 months)",
        "required":   True,
        "legal_basis": "ITO 2001, Section 177 — Record keeping; cross-matched with PRC amounts",
        "consequence": "Audit risk: FBR may demand full income tax on proceeds without PRC-bank match.",
    },
    {
        "key":        "cnic",
        "name":       "CNIC / NICOP (Self)",
        "required":   True,
        "legal_basis": "FBR IRIS NTN registration policy — mandatory for return filing",
        "consequence": "Cannot access IRIS portal without active CNIC/NTN linkage.",
    },
    {
        "key":        "client_contracts",
        "name":       "Service Contracts / Invoices with Foreign Clients",
        "required":   False,
        "legal_basis": "ITO 2001, Section 177 — Commissioner may demand during audit",
        "consequence": "On audit, FBR may re-classify remittances as non-IT if no contracts available.",
    },
    {
        "key":        "ntn_certificate",
        "name":       "NTN Certificate (Active Taxpayer List status)",
        "required":   False,
        "legal_basis": "ITO 2001, Section 181 — NTN mandatory for filers",
        "consequence": "Higher WHT rates apply if not on Active Taxpayer List (ATL).",
    },
]


class FreelanceDocumentValidator:
    """Validates mandatory PRC and supporting documents for Section 154A filing."""

    def validate(self, submitted: list[str], require_prc: bool = True) -> dict:
        submitted_lower = [s.lower().strip() for s in submitted]
        checks = []

        for doc in FREELANCE_REQUIRED_DOCUMENTS:
            present = any(doc["key"] in s for s in submitted_lower)
            checks.append(DocumentCheck(
                document=doc["name"],
                required=doc["required"],
                present=present,
                legal_basis=doc["legal_basis"],
                consequence_if_missing=doc["consequence"],
            ))

        missing_required = [c for c in checks if c.required and (require_prc or c.document.lower().find("prc") < 0) and not c.present]

        return {
            "all_clear":        len(missing_required) == 0,
            "missing_required": [c.document for c in missing_required],
            "key_warning":      (
                "PRC is missing. Section 154A benefit will be DENIED. "
                "Obtain PRC from your remittance bank immediately."
            ) if not any(c.present for c in checks if "prc" in c.document.lower()) else None,
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
