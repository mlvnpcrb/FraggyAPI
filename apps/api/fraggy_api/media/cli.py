"""Trusted, non-production local media operators. Never downloads remote files."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..database import create_engine
from ..importing.formats import loads, read_text
from ..settings import Settings
from .processing import MediaError
from .service import (
    ImageRights,
    approve,
    garbage_collect,
    ingest,
    revoke,
    revoke_source,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    add = sub.add_parser("ingest")
    add.add_argument("link", type=UUID)
    add.add_argument("file", type=Path)
    add.add_argument("rights", type=Path)
    add.add_argument(
        "--mime", required=True, choices=["image/png", "image/jpeg", "image/webp"]
    )
    add.add_argument("--alt", required=True)
    add.add_argument("--role", choices=["primary", "gallery"], default="gallery")
    add.add_argument("--position", type=int, default=0)
    for name in ("approve", "revoke", "revoke-source"):
        command = sub.add_parser(name)
        command.add_argument("id", type=UUID)
    sub.add_parser("gc")
    for command in sub.choices.values():
        command.add_argument("--reviewer", required=True)
        command.add_argument("--reason", required=True)
    return root


async def run(args: argparse.Namespace) -> dict[str, str | int]:
    settings = Settings()
    if settings.app_env == "production" or make_url(
        settings.database_url.get_secret_value()
    ).host not in {"localhost", "127.0.0.1", "::1"}:
        raise MediaError("nonproduction_loopback_database_required")
    from ..importing.authorization import actor

    actor(args.reviewer, args.reason)
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory.begin() as session:
            if args.command == "ingest":
                rights = ImageRights.model_validate(loads(read_text(args.rights)))
                asset = await ingest(
                    session,
                    settings.media_root,
                    args.link,
                    args.file,
                    args.mime,
                    rights,
                    reviewer=args.reviewer,
                    reason=args.reason,
                    alt=args.alt,
                    role=args.role,
                    position=args.position,
                )
                return {"id": str(asset.id), "status": "pending_review"}
            if args.command == "approve":
                await approve(
                    session, settings.media_root, args.id, args.reviewer, args.reason
                )
            elif args.command == "revoke":
                await revoke(session, args.id, args.reviewer, args.reason)
            elif args.command == "revoke-source":
                count = await revoke_source(
                    session, args.id, args.reviewer, args.reason
                )
                return {"revoked": count}
            elif args.command == "gc":
                return {"removed": await garbage_collect(session, settings.media_root)}
            return {"status": "completed"}
    finally:
        await engine.dispose()


def main() -> None:
    args = parser().parse_args()
    try:
        result = asyncio.run(run(args))
    except (ValueError, OSError):
        parser().exit(
            1, "Media operation refused; verify local files, policy and IDs.\n"
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
