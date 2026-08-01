"""Shared priority enum for tasks, scheduling, and routing in JARVIS OS.

Priorities provide a consistent way to rank the urgency of work across the
platform. Keeping this in the domain layer allows the scheduler, task router,
and future automation systems to compare and reason about work in a uniform way.
"""

from __future__ import annotations

from enum import Enum


class Priority(str, Enum):
    """Represents the urgency or importance of a task."""

    CRITICAL = "CRITICAL"
    """Work that requires immediate attention and fast execution."""

    HIGH = "HIGH"
    """Important work that should be handled promptly."""

    NORMAL = "NORMAL"
    """Standard priority work with expected turnaround."""

    LOW = "LOW"
    """Less urgent work that can be deferred when necessary."""

    BACKGROUND = "BACKGROUND"
    """Low-impact work that should run opportunistically when resources are available."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all enum values for validation, UI binding, and serialization."""
        return tuple(member.value for member in cls)

    @classmethod
    def rank(cls, priority: "Priority") -> int:
        """Return a comparable numeric rank for scheduling and ordering logic."""
        order = {
            cls.CRITICAL: 5,
            cls.HIGH: 4,
            cls.NORMAL: 3,
            cls.LOW: 2,
            cls.BACKGROUND: 1,
        }
        return order.get(priority, 0)
