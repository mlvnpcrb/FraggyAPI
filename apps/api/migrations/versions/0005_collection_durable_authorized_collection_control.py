"""durable authorized collection control"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_collection"
down_revision = "0004_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_sources",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("configuration_digest", sa.Text(), nullable=False),
        sa.Column("review", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("current_run_id", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('approved','revoked')", name="ck_collection_state"
        ),
        sa.CheckConstraint(
            "interval_seconds >= 60 AND interval_seconds <= 31536000",
            name="ck_collection_interval",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_table(
        "collection_runs",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("configuration_digest", sa.Text(), nullable=False),
        sa.Column(
            "ingestion_run_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "response_digests", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("records_staged", sa.Integer(), nullable=False),
        sa.Column("records_unchanged", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running','succeeded','partial','failed','cancelled','interrupted')",
            name="ck_collection_run_status",
        ),
        sa.CheckConstraint(
            "pages >= 0 AND records_seen >= 0 AND records_staged >= 0 AND records_unchanged >= 0 AND attempts >= 0",
            name="ck_collection_run_counts",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collection_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collection_runs_collection_id"),
        "collection_runs",
        ["collection_id"],
        unique=False,
    )

    op.create_index(
        "ix_collection_due",
        "collection_sources",
        ["next_due_at"],
        postgresql_where=sa.text("enabled AND schedule_enabled"),
    )
    op.create_index(
        "uq_collection_running",
        "collection_runs",
        ["collection_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_collection_running", table_name="collection_runs")
    op.drop_index("ix_collection_due", table_name="collection_sources")
    op.drop_index(
        op.f("ix_collection_runs_collection_id"), table_name="collection_runs"
    )
    op.drop_table("collection_runs")
    op.drop_table("collection_sources")
