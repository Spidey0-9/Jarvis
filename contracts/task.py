"""Immutable task contract for requests flowing through JARVIS OS.

Tasks are the canonical input object for orchestration, agent execution,
plugins, automation, and voice interactions. By keeping them immutable, the
system can safely pass them through multiple layers without accidental mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable request representation for the JARVIS OS runtime."""

    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: str = "normal"
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    retry_limit: int = 0
    status: str = "pending"
    origin: str = "system"

    def with_status(self, status: str) -> "Task":
        """Return a new task instance with an updated runtime status."""
        return replace(self, status=status)
