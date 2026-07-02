from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppSettingsUpdate(BaseModel):
    default_sequence_id: UUID | None = None


class AppSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_sequence_id: UUID | None
