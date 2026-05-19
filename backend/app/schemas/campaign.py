from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True
    default_sequence_id: UUID | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    is_active: bool | None = None
    default_sequence_id: UUID | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    default_sequence_id: UUID | None
    created_at: datetime
    updated_at: datetime
