"""Internal write/read contracts, not new public API endpoints or export permission."""

from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)

RightsStatus = Literal["pending_review", "approved", "restricted", "synthetic"]
Concentration = Literal[
    "parfum",
    "extrait_de_parfum",
    "eau_de_parfum",
    "eau_de_toilette",
    "eau_de_cologne",
    "eau_fraiche",
    "oil",
    "other",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, frozen=True)


class BrandRead(Contract):
    id: UUID
    name: str
    slug: str
    country: str | None
    # Descriptions are excluded until a rights-aware API projection is implemented.


class FragranceRead(Contract):
    id: UUID
    brand_id: UUID
    name: str
    slug: str
    release_year: int | None = Field(ge=1000, le=2999)
    gender_positioning: str | None
    family_id: UUID | None


class ReleaseRead(Contract):
    id: UUID
    fragrance_id: UUID
    concentration: Concentration | None
    release_year: int | None = Field(ge=1000, le=2999)
    version_label: str | None
    reformulation_of_id: UUID | None


class Transformation(Contract):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class SourceRecordInput(Contract):
    source_id: UUID
    source_record_id: str = Field(min_length=1)
    source_url: str | None = None
    collected_at: AwareDatetime
    schema_version: int = Field(default=1, gt=0)
    revision: int = Field(default=1, gt=0)
    payload: dict[str, JsonValue] | None = None
    storage_status: RightsStatus = "pending_review"
    storage_evidence: str | None = None
    redistribution_status: RightsStatus = "pending_review"
    redistribution_evidence: str | None = None

    @model_validator(mode="after")
    def storage_rights(self) -> Self:
        if not self.source_record_id.strip():
            raise ValueError("Source record ID cannot be blank")
        if self.payload is not None and self.storage_status not in {
            "approved",
            "synthetic",
        }:
            raise ValueError("Payload retention requires explicit storage rights")
        if (
            self.storage_status == "approved"
            and not (self.storage_evidence or "").strip()
        ):
            raise ValueError("Approved storage requires review evidence")
        if (
            self.redistribution_status == "approved"
            and not (self.redistribution_evidence or "").strip()
        ):
            raise ValueError("Approved redistribution requires review evidence")
        return self


class FieldClaimInput(Contract):
    entity_link_id: UUID
    field_path: str = Field(min_length=1)
    value: JsonValue | None = None
    value_state: Literal["known", "unknown", "conflicting"]
    selection_status: Literal["candidate", "selected", "rejected"] = "candidate"
    collected_at: AwareDatetime
    transformations: list[Transformation] = Field(default_factory=list)
    usage_rights_status: RightsStatus = "pending_review"
    rights_evidence: str | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def claim_consistency(self) -> Self:
        if not self.field_path.strip():
            raise ValueError("Field path cannot be blank")
        if (self.value_state == "unknown") != (self.value is None):
            raise ValueError(
                "Unknown must be null; known/conflicting must preserve a value"
            )
        if (
            self.usage_rights_status == "approved"
            and not (self.rights_evidence or "").strip()
        ):
            raise ValueError("Approved reuse requires review evidence")
        return self
