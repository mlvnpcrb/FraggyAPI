"""Public-only credit metadata; URLs and license labels never authorize use."""

import ipaddress
import re
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(min_length=1, max_length=1000)]


def safe_public_url(value: str) -> str:
    # No fetching occurs. Restrict outgoing links to ordinary public HTTPS hosts.
    if len(value) > 2048 or re.search(r"[\s\\\x00-\x1f\x7f]", value):
        raise ValueError("Unsafe public URL")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.query
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)
        or len(host) > 253
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in host.split(".")
        )
        or "." not in host
        or host.endswith((".localhost", ".local"))
    ):
        raise ValueError("Unsafe public URL")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return value
    raise ValueError("IP links are unsupported")


class Attribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Text
    text: Text
    source_url: str
    license_name: Text
    license_url: str
    copyright_holder: Text | None = None
    placement: Literal["adjacent_record", "global_footer", "other"] = "adjacent_record"
    modification_disclosure_required: bool = False
    modification_disclosure: Text | None = None
    redistribution_conditions: list[Text] = Field(default_factory=list, max_length=20)
    last_verified: date

    @field_validator("source_url", "license_url")
    @classmethod
    def url(cls, value: str) -> str:
        return safe_public_url(value)

    @field_validator(
        "provider",
        "text",
        "license_name",
        "copyright_holder",
        "modification_disclosure",
    )
    @classmethod
    def text_value(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError("Invalid public attribution text")
        return value

    def supported(self) -> bool:
        age = (datetime.now(UTC).date() - self.last_verified).days
        return (
            0 <= age <= 365
            and self.placement == "adjacent_record"
            and not self.redistribution_conditions
            and (
                not self.modification_disclosure_required
                or bool(self.modification_disclosure)
            )
        )


class PublicAttribution(Attribution):
    id: str
    fields: list[str]
