"""Add fee reconciliation fields and remove the publicly seeded RFID secret."""

from sqlalchemy import inspect, text


def upgrade(connection):
    inspector = inspect(connection)
    if inspector.has_table("fee_transaction"):
        columns = {column["name"] for column in inspector.get_columns("fee_transaction")}
        additions = (
            ("reconciliation_status", "VARCHAR(20) NOT NULL DEFAULT 'confirmed'"),
            ("reconciled_by_id", "INTEGER REFERENCES user(id)"),
            ("reconciled_at", "VARCHAR(26)"),
            ("reconciliation_note", "TEXT"),
        )
        for name, definition in additions:
            if name not in columns:
                connection.execute(text(f"ALTER TABLE fee_transaction ADD COLUMN {name} {definition}"))

    if inspector.has_table("rfid_device"):
        # Retire only the known migration-seeded credential. Real devices must
        # be provisioned with unique secrets configured in the server environment.
        connection.execute(text(
            "DELETE FROM rfid_device WHERE device_id = 'MAIN_GATE_01' "
            "AND device_token = 'muhura-gate-token-2026'"
        ))
