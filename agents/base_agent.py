"""Abstract base class for all JARVIS OS agents.

This module defines the core contract that every agent must implement. It keeps
agent behavior consistent across the system and enables the orchestrator to work
through a stable interface instead of coupling to concrete agent classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional, Sequence

from .agent_status import AgentStatus
from .agent_types import AgentType


class BaseAgent(ABC):
    """Abstract interface for every agent in JARVIS OS."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: Optional[Iterable[str]] = None,
        agent_type: AgentType = AgentType.SYSTEM,
    ) -> None:
        """Initialize the common agent identity and lifecycle fields."""
        self.id: str = agent_id
        self.name: str = name
        self.description: str = description
        self.capabilities: tuple[str, ...] = tuple(capabilities or ())
        self.status: AgentStatus = AgentStatus.INITIALIZING
        self.agent_type: AgentType = agent_type

    @abstractmethod
    def initialize(self) -> None:
        """Prepare the agent for operation and transition it to a ready state."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources and transition the agent to an offline state."""

    @abstractmethod
    def can_handle(self, task: dict[str, Any]) -> bool:
        """Return whether this agent can process the provided task."""

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> Any:
        """Execute the provided task and return the result payload."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the agent is healthy and ready for work."""

    def set_status(self, status: AgentStatus) -> None:
        """Update the current agent status."""
        self.status = status

    def supports_capability(self, capability: str) -> bool:
        """Return whether the agent advertises a given capability."""
        return capability in self.capabilities

    def __repr__(self) -> str:
        """Return a human-readable representation of the agent."""
        return f"{self.__class__.__name__}(name={self.name!r}, status={self.status.value!r})"
