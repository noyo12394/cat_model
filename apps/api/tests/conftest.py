from __future__ import annotations

import pytest

from app.db.memory_repository import MemoryRepository


@pytest.fixture
def repo() -> MemoryRepository:
    """A fresh repository per test - avoids cross-test state via the
    process-wide lru_cache singleton used by the running API."""
    return MemoryRepository()
