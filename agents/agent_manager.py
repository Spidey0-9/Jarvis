"""Runtime manager for agent lifecycle and task dispatch in JARVIS OS.

The agent manager is responsible for initializing agents, monitoring their
health, and dispatching tasks through the shared registry. It depends on the
registry and the task contracts rather than concrete agent implementations,
which keeps the architecture extensible and decoupled.
"""

from __future__ import annotations

from typing import Any, Optional

from contracts.task import Task
from contracts.task_result import TaskResult
from domain.agent_types import AgentType
from domain.capability import Capability
from domain.permission import Permission
from .agent_registry import AgentRegistry
from .agent_status import AgentStatus
from .base_agent import BaseAgent


class AgentManager:
    """Manage lifecycle, health, and task routing for registered agents."""

    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self._registry = registry or AgentRegistry()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager's registry."""
        self._registry.register(agent)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the manager's registry."""
        self._registry.unregister(agent_id)

    def initialize_agent(self, agent: BaseAgent) -> None:
        """Initialize an agent and update its status to ready if healthy."""
        agent.set_status(AgentStatus.INITIALIZING)
        agent.initialize()
        agent.set_status(AgentStatus.READY if agent.health_check() else AgentStatus.ERROR)

    def initialize_all(self) -> list[BaseAgent]:
        """Initialize all registered agents."""
        initialized: list[BaseAgent] = []
        for agent in self._registry.list_agents():
            self.initialize_agent(agent)
            initialized.append(agent)
        return initialized

    def shutdown_agent(self, agent: BaseAgent) -> None:
        """Shutdown an agent and mark it offline."""
        agent.set_status(AgentStatus.SHUTTING_DOWN)
        agent.shutdown()
        agent.set_status(AgentStatus.OFFLINE)

    def shutdown_all(self) -> None:
        """Shutdown all registered agents."""
        for agent in self._registry.list_agents():
            self.shutdown_agent(agent)

    def pause_agent(self, agent: BaseAgent) -> None:
        """Pause an agent temporarily."""
        agent.set_status(AgentStatus.PAUSED)

    def resume_agent(self, agent: BaseAgent) -> None:
        """Resume a paused agent."""
        agent.set_status(AgentStatus.READY if agent.health_check() else AgentStatus.ERROR)

    def health_check(self, agent: BaseAgent) -> bool:
        """Return whether the agent is healthy."""
        return agent.health_check()

    def monitor_health(self) -> dict[str, bool]:
        """Return a health summary for all registered agents."""
        return {agent.id: self.health_check(agent) for agent in self._registry.list_agents()}

    def dispatch(self, task: Task) -> TaskResult:
        """Dispatch a task to the most suitable registered agent."""
        agent = self.select_agent(task)
        if agent is None:
            return TaskResult(
                task_id=task.id,
                agent_name="none",
                success=False,
                output=None,
                errors=["No suitable agent available"],
                metadata={"reason": "no_agent"},
            )

        agent.set_status(AgentStatus.BUSY)
        try:
            result = agent.execute(task.payload)
            return TaskResult(
                task_id=task.id,
                agent_name=agent.name,
                success=True,
                output=result,
                metadata={"agent_id": agent.id},
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            return TaskResult(
                task_id=task.id,
                agent_name=agent.name,
                success=False,
                output=None,
                errors=[str(exc)],
                metadata={"agent_id": agent.id, "error_type": exc.__class__.__name__},
            )
        finally:
            agent.set_status(AgentStatus.READY)

    def select_agent(self, task: Task) -> Optional[BaseAgent]:
        """Select the most appropriate agent for the supplied task."""
        candidates = [
            agent
            for agent in self._registry.list_agents()
            if agent.status == AgentStatus.READY and agent.can_handle(task.payload)
        ]

        if not candidates:
            return None

        return self._load_balance(candidates)

    def _load_balance(self, candidates: list[BaseAgent]) -> BaseAgent:
        """Choose the next agent using a simple round-robin strategy."""
        if not candidates:
            raise ValueError("No candidates provided")

        if not hasattr(self, "_round_robin_index"):
            self._round_robin_index = 0

        index = self._round_robin_index % len(candidates)
        self._round_robin_index = (self._round_robin_index + 1) % len(candidates)
        return candidates[index]

    def get_registered_agents(self) -> list[BaseAgent]:
        """Return all registered agents."""
        return self._registry.list_agents()

    def find_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """Return agents matching the provided type."""
        return self._registry.get_by_type(agent_type)

    def find_by_capability(self, capability: Capability) -> list[BaseAgent]:
        """Return agents advertising the given capability."""
        return self._registry.get_by_capability(capability)

    def find_by_status(self, status: AgentStatus) -> list[BaseAgent]:
        """Return agents matching the provided status."""
        return self._registry.get_by_status(status)

    def find_by_permission(self, permission: Permission) -> list[BaseAgent]:
        """Return agents requiring the provided permission."""
        return self._registry.get_by_permission(permission)


__all__ = ["AgentManager"]
