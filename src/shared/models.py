"""Persistent schema for the FBR Tax Copilot.

The schema is deliberately money-safe (NUMERIC), tenant-scoped, and includes
session, audit, payment lifecycle, reconciliation and OAuth-state records.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.pool import StaticPool

from config.settings import settings

metadata = MetaData()
now_utc = lambda: datetime.now(timezone.utc)

advisors = Table(
    "advisors", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("google_sub", String(128), unique=True, nullable=True),
    Column("display_name", String(128), nullable=True),
    Column("phone", String(20), nullable=True),
    Column("totp_secret", String(64), nullable=True),
    Column("active", Boolean, default=True, nullable=False),
    Column("plan", String(32), default="free", nullable=False),
    Column("role", String(32), default="advisor", nullable=False),
    Column("mfa_enabled", Boolean, default=False, nullable=False),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("last_login", DateTime(timezone=True), nullable=True),
)

auditable_fields = {
    "actor_id": Integer, "action": String(64), "resource_type": String(64), "resource_id": String(128),
    "request_id": String(64), "ip_address": String(64), "metadata": JSON,
}

audit_events = Table(
    "audit_events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("actor_id", Integer, ForeignKey("advisors.id"), nullable=True),
    Column("action", String(64), nullable=False),
    Column("resource_type", String(64), nullable=False),
    Column("resource_id", String(128), nullable=True),
    Column("request_id", String(64), nullable=True),
    Column("ip_address", String(64), nullable=True),
    Column("metadata", JSON, nullable=True),
    Column("prev_hash", String(64), nullable=True),
    Column("event_hash", String(64), unique=True, nullable=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
)

clients = Table(
    "clients", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("advisor_id", Integer, ForeignKey("advisors.id"), nullable=False),
    Column("full_name", String(128), nullable=False),
    Column("cnic", String(15), nullable=True),
    Column("ntn", String(20), nullable=True),
    Column("email", String(255), nullable=True),
    Column("phone", String(20), nullable=True),
    Column("taxpayer_type", String(32), nullable=False),
    Column("tax_year", String(10), default="2026-27", nullable=False),
    Column("annual_income", Numeric(18, 2), nullable=True),
    Column("notes", Text, nullable=True),
    Column("active", Boolean, default=True, nullable=False),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("updated_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Index("ix_clients_advisor_active", "advisor_id", "active"),
)

tax_calculations = Table(
    "tax_calculations", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("client_id", Integer, ForeignKey("clients.id"), nullable=False),
    Column("advisor_id", Integer, ForeignKey("advisors.id"), nullable=False),
    Column("taxpayer_type", String(32)),
    Column("tax_year", String(10)),
    Column("annual_income", Numeric(18, 2)),
    Column("tax_payable", Numeric(18, 2)),
    Column("effective_rate", Numeric(9, 4)),
    Column("rule_applied", String(64)),
    Column("ca_verified", Boolean, default=False, nullable=False),
    Column("iris_entries", JSON, nullable=True),
    Column("document_check", JSON, nullable=True),
    Column("calculated_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Index("ix_tax_calculations_client_date", "client_id", "calculated_at"),
)

payments = Table(
    "payments", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("advisor_id", Integer, ForeignKey("advisors.id"), nullable=False),
    Column("client_id", Integer, ForeignKey("clients.id"), nullable=True),
    Column("amount_pkr", Numeric(18, 2), nullable=False),
    Column("currency", String(3), default="PKR", nullable=False),
    Column("method", String(32), nullable=False),
    Column("provider", String(32), nullable=False),
    Column("reference", String(128), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
    Column("provider_transaction_id", String(128), nullable=True),
    Column("status", String(32), default="pending", nullable=False),
    Column("settlement_status", String(32), default="unsettled", nullable=False),
    Column("refund_status", String(32), default="none", nullable=False),
    Column("refund_amount_pkr", Numeric(18, 2), nullable=True),
    Column("refunded_amount_pkr", Numeric(18, 2), nullable=False, default=0),
    Column("refund_provider_transaction_id", String(128), nullable=True),
    Column("chargeback_status", String(32), default="none", nullable=False),
    Column("retry_count", Integer, default=0, nullable=False),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("paid_at", DateTime(timezone=True), nullable=True),
    Column("settled_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("updated_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("provider_response", JSON, nullable=True),
    UniqueConstraint("provider", "idempotency_key", name="uq_payment_provider_idempotency"),
    UniqueConstraint("provider", "reference", name="uq_payment_provider_reference"),
    Index("ix_payments_advisor_status", "advisor_id", "status"),
    Index("ix_payments_provider_txn", "provider", "provider_transaction_id"),
)

payment_events = Table(
    "payment_events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("payment_id", Integer, ForeignKey("payments.id"), nullable=True),
    Column("provider", String(32), nullable=False),
    Column("event_id", String(128), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("payload", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    UniqueConstraint("provider", "event_id", name="uq_payment_event"),
)

audit_reconciliation = Table(
    "reconciliation_runs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("provider", String(32), nullable=False),
    Column("run_reference", String(128), nullable=False, unique=True),
    Column("matched", Integer, default=0, nullable=False),
    Column("amount_mismatch", Integer, default=0, nullable=False),
    Column("missing_internal", Integer, default=0, nullable=False),
    Column("missing_provider", Integer, default=0, nullable=False),
    Column("duplicate", Integer, default=0, nullable=False),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("details", JSON, nullable=True),
)

sessions = Table(
    "sessions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("advisor_id", Integer, ForeignKey("advisors.id"), nullable=False),
    Column("token_hash", String(64), unique=True, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
    Column("revoked", Boolean, default=False, nullable=False),
)

oauth_states = Table(
    "oauth_states", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("state_hash", String(64), unique=True, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used", Boolean, default=False, nullable=False),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
)


def _add_missing_columns(engine):
    """Forward migration for existing SQLite/Postgres databases.

    Runs per-column, wrapped so that a duplicate-column error from a
    concurrently-starting replica doesn't crash startup. On a single
    instance this never triggers; it matters once the API or MCP
    service is horizontally scaled and multiple replicas run this at
    boot simultaneously against the same Postgres database — without
    this, the second replica to reach a given ALTER TABLE would get a
    "column already exists" error and fail to start.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    inspector = inspect(engine)
    additions = {
        "advisors": {
            "role": "VARCHAR(32) NOT NULL DEFAULT 'advisor'",
            "mfa_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
        },
        "clients": {
            "tax_year": "VARCHAR(10) NOT NULL DEFAULT '2026-27'",
            "annual_income": "NUMERIC(18,2)",
        },
        "payments": {
            "client_id": "INTEGER",
            "currency": "VARCHAR(3) NOT NULL DEFAULT 'PKR'",
            "provider": "VARCHAR(32) NOT NULL DEFAULT 'manual'",
            "idempotency_key": "VARCHAR(128)",
            "provider_transaction_id": "VARCHAR(128)",
            "settlement_status": "VARCHAR(32) NOT NULL DEFAULT 'unsettled'",
            "refund_status": "VARCHAR(32) NOT NULL DEFAULT 'none'",
            "refund_amount_pkr": "NUMERIC(18,2)",
            "refunded_amount_pkr": "NUMERIC(18,2) NOT NULL DEFAULT 0",
            "refund_provider_transaction_id": "VARCHAR(128)",
            "chargeback_status": "VARCHAR(32) NOT NULL DEFAULT 'none'",
            "retry_count": "INTEGER NOT NULL DEFAULT 0",
            "next_retry_at": "TIMESTAMP",
            "settled_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
            "provider_response": "JSON",
        },
        "audit_events": {
            "prev_hash": "VARCHAR(64)",
            "event_hash": "VARCHAR(64)",
        },
    }
    with engine.begin() as conn:
        for table_name, cols in additions.items():
            if not inspector.has_table(table_name):
                continue
            existing = {c["name"] for c in inspect(conn).get_columns(table_name)}
            for col, ddl in cols.items():
                if col not in existing:
                    try:
                        with conn.begin_nested():  # SAVEPOINT: isolates
                            # this statement so a failure here rolls back
                            # only this ALTER, not the whole migration.
                            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}"))
                    except (ProgrammingError, OperationalError):
                        # Another replica added this column between our
                        # inspect() and this ALTER — already applied,
                        # nothing to do. Anything else still raises.
                        pass


def get_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()
    else:
        engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=1800)
    return engine


def init_db():
    engine = get_engine()
    metadata.create_all(engine)
    _add_missing_columns(engine)
    return engine
