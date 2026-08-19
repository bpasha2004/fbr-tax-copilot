"""
Multi-Client Agency Dashboard — Data Layer
Provides advisor-scoped client management operations on the SQLite schema.
One advisor → N clients. Each client has full calculation history.
"""
from datetime import datetime, timezone

from sqlalchemy import insert, select, update

from src.shared.models import (
    clients,
    get_engine,
    tax_calculations,
)


class AdvisorDashboard:
    """
    All operations are scoped to a single advisor_id.
    Enforces multi-tenant isolation at the query level.
    """

    def __init__(self, advisor_id: int):
        self.advisor_id = advisor_id
        self.engine     = get_engine()

    # ── Client management ─────────────────────────────────────────────────────

    def list_clients(self, active_only: bool = True) -> list[dict]:
        """Return all clients for this advisor."""
        with self.engine.connect() as conn:
            q = select(clients).where(clients.c.advisor_id == self.advisor_id)
            if active_only:
                q = q.where(clients.c.active == True)
            rows = conn.execute(q).mappings().all()
            return [dict(r) for r in rows]

    def get_client(self, client_id: int) -> dict | None:
        """Get a single client (enforces advisor ownership)."""
        with self.engine.connect() as conn:
            q = select(clients).where(
                (clients.c.id == client_id) &
                (clients.c.advisor_id == self.advisor_id)
            )
            row = conn.execute(q).mappings().first()
            return dict(row) if row else None

    def create_client(
        self,
        full_name: str,
        taxpayer_type: str,
        tax_year: str = "2026-27",
        cnic: str | None = None,
        ntn: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        annual_income: float | None = None,
        notes: str | None = None,
    ) -> int:
        """Create a new client profile. Returns new client_id."""
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(clients).values(
                    advisor_id=self.advisor_id,
                    full_name=full_name,
                    taxpayer_type=taxpayer_type,
                    tax_year=tax_year,
                    cnic=cnic,
                    ntn=ntn,
                    email=email,
                    phone=phone,
                    annual_income=annual_income,
                    notes=notes,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            return result.inserted_primary_key[0]

    def update_client(self, client_id: int, **fields) -> bool:
        """Update client fields. Enforces advisor ownership."""
        if not self.get_client(client_id):
            return False
        fields["updated_at"] = datetime.now(timezone.utc)
        with self.engine.begin() as conn:
            conn.execute(
                update(clients)
                .where(
                    (clients.c.id == client_id) &
                    (clients.c.advisor_id == self.advisor_id)
                )
                .values(**fields)
            )
        return True

    def deactivate_client(self, client_id: int) -> bool:
        """Soft-delete: marks client inactive."""
        return self.update_client(client_id, active=False)

    # ── Calculation history ───────────────────────────────────────────────────

    def save_calculation(self, client_id: int, calc_result: dict) -> int:
        """Persist a tax calculation result for a client."""
        if not self.get_client(client_id):
            raise PermissionError(f"Client {client_id} not found for advisor {self.advisor_id}")
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(tax_calculations).values(
                    client_id=client_id,
                    advisor_id=self.advisor_id,
                    taxpayer_type=calc_result.get("taxpayer_type"),
                    tax_year=calc_result.get("tax_year"),
                    annual_income=calc_result.get("annual_income"),
                    tax_payable=calc_result.get("tax_payable"),
                    effective_rate=calc_result.get("effective_rate"),
                    rule_applied=calc_result.get("rule_applied"),
                    ca_verified=calc_result.get("ca_verified", False),
                    iris_entries=calc_result.get("iris_entries"),
                    document_check=calc_result.get("document_check"),
                    calculated_at=datetime.now(timezone.utc),
                )
            )
            return result.inserted_primary_key[0]

    def get_client_history(self, client_id: int, limit: int = 20) -> list[dict]:
        """Return last N calculations for a client."""
        if not self.get_client(client_id):
            return []
        limit = max(1, min(int(limit), 100))
        with self.engine.connect() as conn:
            q = (
                select(tax_calculations)
                .where(tax_calculations.c.client_id == client_id)
                .order_by(tax_calculations.c.calculated_at.desc())
                .limit(limit)
            )
            rows = conn.execute(q).mappings().all()
            return [dict(r) for r in rows]

    # ── Dashboard summary ─────────────────────────────────────────────────────

    def get_dashboard_summary(self) -> dict:
        """Aggregate stats for the advisor's agency dashboard."""
        client_list = self.list_clients(active_only=True)
        total       = len(client_list)
        by_type     = {}
        for c in client_list:
            t = c.get("taxpayer_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "advisor_id":      self.advisor_id,
            "total_clients":   total,
            "clients_by_type": by_type,
            "clients":         client_list,
        }
