"""Normalize all boundary whitespace and require redistribution evidence.

Rebuild derived keys without rewriting canonical names or identifiers. A newly
colliding key aborts the migration atomically; never merge or delete such rows.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_quality"
down_revision = "0003_search"
branch_labels = None
depends_on = None

OLD_KEY = (
    "lower(regexp_replace(btrim(normalize(name, NFKC)), '[[:space:]]+', ' ', 'g'))"
)
NEW_KEY = (
    "lower(btrim(regexp_replace(normalize(name, NFKC), '[[:space:]]+', ' ', 'g')))"
)
# Frozen migration definitions; never import live model metadata here.
KEYS = (
    ("brands", "uq_brands_name_key", ("name_key",), ()),
    ("fragrance_families", "uq_families_name_key", ("name_key",), ()),
    ("notes", "uq_notes_name_key", ("name_key",), ()),
    ("accords", "uq_accords_name_key", ("name_key",), ()),
    (
        "brand_aliases",
        "uq_brand_aliases_key",
        ("brand_id", "name_key"),
        (("ix_brand_aliases_name_key", ("name_key",)),),
    ),
    (
        "note_aliases",
        "uq_note_aliases_key",
        ("note_id", "name_key"),
        (("ix_note_aliases_name_key", ("name_key",)),),
    ),
    (
        "fragrances",
        None,
        (),
        (
            ("ix_fragrances_name_key", ("name_key",)),
            ("ix_fragrances_brand_name", ("brand_id", "name_key")),
        ),
    ),
    ("perfumers", None, (), (("ix_perfumers_name_key", ("name_key",)),)),
)


def rebuild_keys(expression: str, strict: bool) -> None:
    for table, unique, columns, indexes in KEYS:
        op.drop_constraint(f"ck_{table}_name", table, type_="check")
        if unique:
            op.drop_constraint(unique, table, type_="unique")
        for name, _ in indexes:
            op.drop_index(name, table_name=table)
        op.drop_column(table, "name_key")
        op.add_column(
            table,
            sa.Column(
                "name_key",
                sa.Text(),
                sa.Computed(expression, persisted=True),
                nullable=False,
            ),
        )
        if unique:
            op.create_unique_constraint(unique, table, list(columns))
        for name, fields in indexes:
            op.create_index(name, table, list(fields))
        check = "length(btrim(name)) > 0"
        if strict:
            check += " AND length(name_key) > 0"
        op.create_check_constraint(f"ck_{table}_name", table, check)


def upgrade() -> None:
    rebuild_keys(NEW_KEY, True)
    op.add_column(
        "source_records", sa.Column("redistribution_evidence", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_records_redistribution_evidence",
        "source_records",
        "redistribution_status <> 'approved' OR (redistribution_evidence IS NOT NULL AND length(btrim(redistribution_evidence)) > 0)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_records_redistribution_evidence", "source_records", type_="check"
    )
    op.drop_column("source_records", "redistribution_evidence")
    rebuild_keys(OLD_KEY, False)
