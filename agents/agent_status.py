"""Agent lifecycle states used throughout the JARVIS OS agent framework.

This module centralizes the available agent statuses so new states can be added
without changing agent implementations. By using an enum, the system can reason
about runtime readiness and lifecycle transitions in a type-safe way.
"""

from __future__ import annotations

from enum import Enum


class AgentStatus(str, Enum):
    """Represents the lifecycle and availability state of an agent."""

    INITIALIZING = "INITIALIZING"
    """The agent is being constructed or warming up."""

    READY = "READY"
    """The agent is available and can accept work."""

    BUSY = "BUSY"
    """The agent is currently processing a task."""

    WAITING = "WAITING"
    """The agent is idle and waiting for the next task."""

    PAUSED = "PAUSED"
    """The agent is temporarily suspended and not accepting work."""

    ERROR = "ERROR"
    """The agent encountered a runtime failure or degraded state."""

    OFFLINE = "OFFLINE"
    """The agent is shut down or unavailable."""

    SHUTTING_DOWN = "SHUTTING_DOWN"
    """The agent is in the process of shutting down."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all status values as a tuple for validation or UI usage."""
        return tuple(status.value for status in cls)
