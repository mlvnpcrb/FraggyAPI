"""Bounded edit-distance recheck for trigram search candidates."""

from alembic import op

revision = "0008_search_typos"
down_revision = "0007_enrichment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
    op.execute("""CREATE FUNCTION fraggy_typo_match(needle text, haystack text)
        RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
        SELECT EXISTS (SELECT 1 FROM regexp_split_to_table(haystack, '[^[:alnum:]]+') AS word
          WHERE abs(length(word)-length(needle)) <= 2
            AND levenshtein_less_equal(needle, left(word, 200), CASE WHEN length(needle)>=5 THEN 2 ELSE 1 END)
                <= CASE WHEN length(needle)>=5 THEN 2 ELSE 1 END)
        $$""")


def downgrade() -> None:
    op.execute("DROP FUNCTION fraggy_typo_match(text, text)")
    # Shared PostgreSQL extensions may be used by other applications; retain them.
