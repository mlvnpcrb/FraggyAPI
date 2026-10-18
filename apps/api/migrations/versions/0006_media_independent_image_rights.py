"""Independently reviewed media and content-addressed renditions.

Revision ID: 0006_media
Revises: 0005_collection
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_media"
down_revision = "0005_collection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets", sa.Column("content_sha256", sa.String(64), nullable=True)
    )
    for column in ("media_metadata", "image_policy"):
        op.add_column(
            "media_assets",
            sa.Column(
                column,
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )
    op.create_index(
        "ix_media_assets_content_sha256", "media_assets", ["content_sha256"]
    )

    op.create_check_constraint(
        "ck_media_content_hash",
        "media_assets",
        "content_sha256 IS NULL OR content_sha256 ~ '^[a-f0-9]{64}$'",
    )
    op.create_check_constraint(
        "ck_media_policy_objects",
        "media_assets",
        "jsonb_typeof(media_metadata) = 'object' AND jsonb_typeof(image_policy) = 'object'",
    )
    op.create_index(
        "uq_media_link_content_active",
        "media_assets",
        ["entity_link_id", "content_sha256"],
        unique=True,
        postgresql_where=sa.text(
            "content_sha256 IS NOT NULL AND storage_status = 'approved'"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_media_link_content_active", table_name="media_assets")
    op.drop_constraint("ck_media_policy_objects", "media_assets", type_="check")
    op.drop_constraint("ck_media_content_hash", "media_assets", type_="check")
    op.drop_index("ix_media_assets_content_sha256", table_name="media_assets")
    for column in ("image_policy", "media_metadata", "content_sha256"):
        op.drop_column("media_assets", column)
