"""
Payment Router
Provides configured payment instructions for domestic wallets and bank transfers.
It does not implement or simulate a payment gateway.

Supported methods:
  - JazzCash (configured MSISDN)
  - EasyPaisa (configured MSISDN)
  - Raast (SBP instant payment — IBAN-based IBFT)
  - Bank Transfer (conventional IBFT)

"""
from dataclasses import dataclass

from config.settings import settings


@dataclass
class PaymentRoute:
    method: str
    recipient_label: str
    account_identifier: str   # MSISDN for wallets, IBAN for bank
    amount_pkr: float
    reference: str
    instructions: str
    qr_payload: str | None = None


# ── Configured payment destinations ───────────────────────────────────────────
# These are payment instructions, not a payment gateway. No transaction is
# considered successful until a real provider/bank confirmation is received.

PAYMENT_CONFIG = {
    "jazzcash": {
        "msisdn": settings.JAZZCASH_MSISDN,
        "merchant_id": settings.JAZZCASH_MERCHANT_ID,
        "label": "JazzCash Wallet",
    },
    "easypaisa": {
        "msisdn": settings.EASYPAISA_MSISDN,
        "merchant_id": settings.EASYPAISA_MERCHANT_ID,
        "label": "EasyPaisa Wallet",
    },
    "raast": {
        "iban": settings.RAAST_IBAN,
        "bank_name": settings.RAAST_BANK_NAME,
        "account_name": settings.RAAST_ACCOUNT_NAME,
        "label": "Raast (SBP Instant Transfer)",
    },
    "bank": {
        "iban": settings.BANK_IBAN,
        "bank_name": settings.BANK_NAME,
        "account_name": settings.BANK_ACCOUNT_NAME,
        "swift": settings.BANK_SWIFT,
        "label": "Bank Transfer (IBFT)",
    },
}


class PaymentRouter:
    """
    Provides configured payment instructions. It deliberately does not pretend
    to be a JazzCash/EasyPaisa/Raast gateway: settlement requires a real
    provider integration or manual confirmation.
    """

    def route(
        self,
        amount_pkr: float,
        client_type: str,
        reference: str,
        preferred_method: str | None = None,
    ) -> list[PaymentRoute]:
        if amount_pkr <= 0:
            raise ValueError("amount_pkr must be greater than zero")
        if client_type not in {"individual", "business", "firm"}:
            raise ValueError("client_type must be individual, business, or firm")
        if not reference.strip():
            raise ValueError("reference must not be empty")

        allowed_methods = (
            {"jazzcash", "easypaisa"} if client_type == "individual"
            else {"raast", "bank"}
        )
        if preferred_method is not None:
            if preferred_method not in {"jazzcash", "easypaisa", "raast", "bank"}:
                raise ValueError("unsupported preferred payment method")
            if preferred_method not in allowed_methods:
                raise ValueError(
                    f"payment method '{preferred_method}' is not valid for client_type '{client_type}'"
                )

        methods = (
            ["jazzcash", "easypaisa"] if client_type == "individual"
            else ["raast", "bank"]
        )
        if preferred_method:
            methods = [preferred_method] + [m for m in methods if m != preferred_method]

        routes = []
        for method in methods:
            cfg = PAYMENT_CONFIG[method]
            identifier = cfg.get("msisdn") or cfg.get("iban")
            if not identifier:
                continue

            if method in {"jazzcash", "easypaisa"}:
                instructions = (
                    f"Send PKR {amount_pkr:,.0f} to {cfg['label']} "
                    f"({identifier}). Use reference: {reference}. "
                    "Confirm the transaction using the provider receipt/reference."
                )
            else:
                instructions = (
                    f"Transfer PKR {amount_pkr:,.0f} to {cfg['account_name']} "
                    f"via {cfg['label']} ({identifier}). "
                    f"Use reference: {reference} and retain the transaction ID."
                )

            routes.append(PaymentRoute(
                method=method,
                recipient_label=cfg["label"],
                account_identifier=identifier,
                amount_pkr=amount_pkr,
                reference=reference,
                instructions=instructions,
                qr_payload=None,
            ))

        return routes

    def to_dict(self, routes: list[PaymentRoute]) -> list[dict]:
        return [
            {
                "method": r.method,
                "recipient": r.recipient_label,
                "account": r.account_identifier,
                "amount_pkr": r.amount_pkr,
                "reference": r.reference,
                "instructions": r.instructions,
                "qr_payload": r.qr_payload,
            }
            for r in routes
        ]
