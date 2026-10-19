"""Rights-aware aliases, trigram indexes and collection admission intents."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_enrichment"
down_revision = "0006_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL-bundled extension; never remove a shared extension on downgrade.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "fragrance_aliases",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "name_key",
            sa.Text(),
            sa.Computed(
                "lower(btrim(regexp_replace(normalize(name, NFKC), '[[:space:]]+', ' ', 'g')))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "fragrance_id",
            sa.UUID(),
            sa.ForeignKey("fragrances.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "fragrance_id", "name_key", name="uq_fragrance_aliases_key"
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0 AND length(name_key) > 0",
            name="ck_fragrance_aliases_name",
        ),
    )
    op.create_index(
        "ix_fragrance_aliases_fragrance_id", "fragrance_aliases", ["fragrance_id"]
    )
    for table in ("fragrances", "brands", "brand_aliases", "fragrance_aliases"):
        op.create_index(
            f"ix_{table}_trigram",
            table,
            ["name_key"],
            postgresql_using="gin",
            postgresql_ops={"name_key": "gin_trgm_ops"},
        )
    op.create_table(
        "enrichment_intents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("request_digest", sa.Text(), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column(
            "fragrance_id",
            sa.UUID(),
            sa.ForeignKey("fragrances.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "collection_run_id",
            sa.UUID(),
            sa.ForeignKey("collection_runs.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("diagnostic", sa.Text()),
        sa.UniqueConstraint("provider", "request_digest", name="uq_enrichment_request"),
        sa.CheckConstraint(
            "status IN ('pending','running','review','failed','blocked')",
            name="ck_enrichment_status",
        ),
    )
    op.create_index(
        "ix_enrichment_pending", "enrichment_intents", ["status", "next_allowed_at"]
    )


def downgrade() -> None:
    op.drop_table("enrichment_intents")
    for table in ("fragrances", "brands", "brand_aliases", "fragrance_aliases"):
        op.drop_index(f"ix_{table}_trigram", table_name=table)
    op.drop_table("fragrance_aliases")
