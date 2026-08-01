"""Metadata registry for agents in JARVIS OS.

The registry is responsible for tracking agent registrations and supporting
lookup operations by identity, type, capability, status, and permission. It does
not instantiate agents or execute tasks; that responsibility remains with the
agent manager layer.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from domain.agent_types import AgentType
from domain.capability import Capability
from domain.permission import Permission
from .agent_status import AgentStatus
from .base_agent import BaseAgent


class AgentRegistry:
    """Registry for agent metadata and discovery."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance by its unique identifier."""
        self._agents[agent.id] = agent

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the registry by identifier."""
        self._agents.pop(agent_id, None)

    def get_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """Return an agent by its identifier, if present."""
        return self._agents.get(agent_id)

    def get_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """Return all registered agents matching the given type."""
        return [agent for agent in self._agents.values() if agent.agent_type == agent_type]

    def get_by_capability(self, capability: Capability) -> list[BaseAgent]:
        """Return all registered agents advertising the given capability."""
        return [agent for agent in self._agents.values() if capability in agent.capabilities]

    def get_by_status(self, status: AgentStatus) -> list[BaseAgent]:
        """Return all registered agents matching the given status."""
        return [agent for agent in self._agents.values() if agent.status == status]

    def get_by_permission(self, permission: Permission) -> list[BaseAgent]:
        """Return all registered agents that require or expose the given permission."""
        return [agent for agent in self._agents.values() if getattr(agent, "permissions", ()) and permission in getattr(agent, "permissions")]

    def get_healthy_agents(self) -> list[BaseAgent]:
        """Return all agents currently in a healthy ready state."""
        return [agent for agent in self._agents.values() if agent.status == AgentStatus.READY and agent.health_check()]

    def get_busy_agents(self) -> list[BaseAgent]:
        """Return all agents that are currently busy."""
        return [agent for agent in self._agents.values() if agent.status == AgentStatus.BUSY]

    def list_agents(self) -> list[BaseAgent]:
        """Return all registered agents."""
        return list(self._agents.values())

    def discover(self, discovered_agents: Iterable[BaseAgent]) -> None:
        """Register a collection of agents for later discovery and lookup."""
        for agent in discovered_agents:
            self.register(agent)

    def clear(self) -> None:
        """Remove all registered agents from the registry."""
        self._agents.clear()


__all__ = ["AgentRegistry"]
