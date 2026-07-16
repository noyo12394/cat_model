from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.memory_repository import MemoryRepository, get_repository


def repo_dep() -> MemoryRepository:
    return get_repository()


def settings_dep() -> Settings:
    return get_settings()
