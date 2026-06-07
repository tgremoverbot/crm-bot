from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MenuButtonCreate(BaseModel):
    label: str
    row: int = 0
    position: int = 0
    action_kind: Literal["text", "material"] = "text"
    action_material_id: uuid.UUID | None = None
    action_text: str | None = None
    is_active: bool = True


class MenuButtonUpdate(BaseModel):
    label: str | None = None
    row: int | None = None
    position: int | None = None
    action_kind: Literal["text", "material"] | None = None
    action_material_id: uuid.UUID | None = None
    action_text: str | None = None
    is_active: bool | None = None


class MenuButtonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    row: int
    position: int
    action_kind: str
    action_material_id: uuid.UUID | None
    action_text: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
