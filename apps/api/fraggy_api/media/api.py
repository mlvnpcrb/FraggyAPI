"""No public uploads, static mount, redirects or remote hotlinks."""

import asyncio
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..catalog_api import demo_enabled, fragrance_visible, release_visible
from ..database import get_session
from ..models import FragranceRelease, MediaAsset
from ..public_rights import read_access
from .processing import MediaError, read_blob
from .service import permitted, query

router = APIRouter(prefix="/api/v1/media", tags=["approved media"])


@router.get("/{identity}/{preset}")
async def image(
    identity: UUID,
    preset: Literal["display", "thumb"],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    access = await read_access(session, demo_enabled(request))
    row = (
        await session.execute(
            query().where(MediaAsset.id == identity, fragrance_visible(access))
        )
    ).one_or_none()
    try:
        if row is None:
            raise MediaError("image_not_found")
        if row[5] is not None:
            from sqlalchemy import select

            visible = await session.scalar(
                select(FragranceRelease.id).where(
                    FragranceRelease.id == row[5].id, release_visible(access)
                )
            )
            if visible is None:
                raise MediaError("release_not_public")
        _, metadata = permitted(row, demo=access.demo)
        data = await asyncio.to_thread(
            read_blob,
            request.app.state.settings.media_root,
            metadata.renditions[preset].sha256,
        )
    except MediaError:
        raise HTTPException(404, "Image unavailable") from None
    return Response(
        content=data,
        media_type="image/webp",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Content-Disposition": 'inline; filename="bottle.webp"',
        },
    )
