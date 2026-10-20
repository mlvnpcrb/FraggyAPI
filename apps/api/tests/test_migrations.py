import asyncio

import asyncpg
from conftest import disposable_database, migrate
from sqlalchemy.engine import make_url


async def fingerprint(url: str) -> list[tuple]:
    dsn = (
        make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    )
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch("""SELECT table_name,column_name,data_type,is_nullable,column_default,is_generated,generation_expression
            FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position""")
        return [tuple(row) for row in rows]
    finally:
        await connection.close()


def test_disposable_migration_upgrade_downgrade_and_reupgrade() -> None:
    with disposable_database() as url:
        migrate(url, "upgrade", "0001_foundation")
        baseline = asyncio.run(fingerprint(url))
        assert {row[0] for row in baseline} == {"alembic_version"}
        migrate(url, "upgrade", "head")
        expected = asyncio.run(fingerprint(url))
        assert len({row[0] for row in expected}) == 25
        assert "0008_search_typos" in migrate(url, "current")
        assert {"collection_sources", "collection_runs"} <= {row[0] for row in expected}
        assert "No new upgrade operations detected" in migrate(url, "check")
        migrate(url, "downgrade", "0003_search")
        migrate(url, "upgrade", "head")
        assert asyncio.run(fingerprint(url)) == expected
        migrate(url, "downgrade", "0001_foundation")
        assert asyncio.run(fingerprint(url)) == baseline
        migrate(url, "upgrade", "head")
        assert asyncio.run(fingerprint(url)) == expected
        assert "No new upgrade operations detected" in migrate(url, "check")


def test_key_collision_upgrade_aborts_without_merging_or_losing_names() -> None:
    from uuid import uuid4

    import pytest

    async def add_conflict(url: str) -> list[str]:
        connection = await asyncpg.connect(
            make_url(url)
            .set(drivername="postgresql")
            .render_as_string(hide_password=False)
        )
        try:
            await connection.execute(
                "INSERT INTO brands(id,name,slug) VALUES($1,$2,$3),($4,$5,$6)",
                uuid4(),
                "Collision House",
                "collision-one",
                uuid4(),
                "\tCollision House\n",
                "collision-two",
            )
            return list(
                await connection.fetchval(
                    "SELECT array_agg(name ORDER BY slug) FROM brands"
                )
            )
        finally:
            await connection.close()

    async def names(url: str) -> list[str]:
        connection = await asyncpg.connect(
            make_url(url)
            .set(drivername="postgresql")
            .render_as_string(hide_password=False)
        )
        try:
            return list(
                await connection.fetchval(
                    "SELECT array_agg(name ORDER BY slug) FROM brands"
                )
            )
        finally:
            await connection.close()

    with disposable_database() as url:
        migrate(url, "upgrade", "0003_search")
        before = asyncio.run(add_conflict(url))
        schema_before = asyncio.run(fingerprint(url))
        with pytest.raises(AssertionError):
            migrate(url, "upgrade", "head")
        assert asyncio.run(names(url)) == before
        assert asyncio.run(fingerprint(url)) == schema_before
        assert "0003_search" in migrate(url, "current")
