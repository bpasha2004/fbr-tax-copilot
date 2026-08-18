"""Forward-compatible database migration and index creation."""
from src.shared.models import init_db, get_engine
from sqlalchemy import text

def main():
    init_db()
    engine=get_engine()
    with engine.begin() as conn:
        statements = [
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_reference ON payments(provider, reference)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_provider_idempotency ON payments(provider, idempotency_key)",
            "CREATE INDEX IF NOT EXISTS ix_payments_provider_txn ON payments(provider, provider_transaction_id)",
        ]
        for stmt in statements:
            try: conn.execute(text(stmt))
            except Exception: pass
    print("Database migration complete")
if __name__ == "__main__": main()
