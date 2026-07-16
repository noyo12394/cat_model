"""Model card schema (section 49 required output, section 36 /models endpoints)."""

from __future__ import annotations

from pydantic import BaseModel


class ModelCard(BaseModel):
    model_id: str
    version: str
    display_name: str
    purpose: str
    method: str
    inputs: list[str]
    outputs: list[str]
    known_limitations: list[str]
    validation_status: str
    not_intended_for: list[str]
