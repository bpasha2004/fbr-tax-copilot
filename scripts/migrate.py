"""Forward-compatible database migration and index creation."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.shared.models import get_engine, init_db


def main() -> None:
    init_db()
    engine = get_engine()
    statements = [
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_reference ON payments(provider, reference)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_idempotency ON payments(provider, idempotency_key)",
        "CREATE INDEX IF NOT EXISTS ix_payments_provider_txn ON payments(provider, provider_transaction_id)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except SQLAlchemyError as exc:
                raise RuntimeError(f"Database migration failed for statement: {statement}") from exc

    print("Database migration complete")


if __name__ == "__main__":
    main()
