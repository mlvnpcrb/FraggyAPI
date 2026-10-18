"""Bounded raster decoding and private content-addressed storage."""

import hashlib
import io
import os
import re
import stat
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_DIMENSION = 4096
MAX_PIXELS = 12_000_000
FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


class MediaError(ValueError):
    """Static, sanitized operator errors."""


def read_local(path: Path) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise MediaError("regular_file_required")
            data = handle.read(MAX_BYTES + 1)
        if not data or len(data) > MAX_BYTES:
            raise MediaError("image_size_limit")
        return data
    except OSError as exc:
        raise MediaError("image_file_unavailable") from exc


def optimize(
    data: bytes, declared_mime: str
) -> tuple[str, dict[str, bytes], dict[str, tuple[int, int]]]:
    if not data or len(data) > MAX_BYTES:
        raise MediaError("image_size_limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as probe:
                if (
                    FORMATS.get(probe.format or "") != declared_mime
                    or getattr(probe, "n_frames", 1) != 1
                ):
                    raise MediaError("image_format_or_animation_denied")
                width, height = probe.size
                if (
                    min(width, height) < 32
                    or max(width, height) > MAX_DIMENSION
                    or width * height > MAX_PIXELS
                ):
                    raise MediaError("image_dimension_limit")
                probe.verify()
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as original:
                original.load()
                oriented = ImageOps.exif_transpose(original)
                # A new pixel-only image strips EXIF, ICC, comments and metadata.
                clean = Image.new("RGBA", oriented.size)
                clean.paste(oriented.convert("RGBA"))
                renditions: dict[str, bytes] = {}
                sizes: dict[str, tuple[int, int]] = {}
                for preset, bound in (("display", 1200), ("thumb", 320)):
                    resized = clean.copy()
                    resized.thumbnail((bound, bound), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    resized.save(output, "WEBP", quality=85, method=4)
                    renditions[preset] = output.getvalue()
                    sizes[preset] = resized.size
                return hashlib.sha256(data).hexdigest(), renditions, sizes
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise MediaError("invalid_image") from exc


def location(root: Path, digest: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise MediaError("invalid_content_hash")
    if root.is_symlink():
        raise MediaError("unsafe_media_directory")
    return root / (digest + ".webp")


def store(root: Path, data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = location(root, digest)
    try:
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
    except FileExistsError:
        if read_local(path) != data:
            raise MediaError("content_address_collision")
        return digest
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return digest


def read_blob(root: Path, digest: str) -> bytes:
    data = read_local(location(root, digest))
    if hashlib.sha256(data).hexdigest() != digest:
        raise MediaError("corrupt_media_blob")
    return data
