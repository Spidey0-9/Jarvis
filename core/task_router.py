"""Task routing layer for selecting suitable agents for a task.

The task router inspects task requirements, consults the agent registry, and
produces an execution plan describing which agents should be considered for a
future execution step. It does not execute tasks directly.
"""

from __future__ import annotations

from typing import Optional

from agents.agent_registry import AgentRegistry
from agents.agent_status import AgentStatus
from contracts.execution_plan import ExecutionPlan
from contracts.task import Task
from domain.capability import Capability


class TaskRouter:
    """Select an execution strategy and candidate agents for a task."""

    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self._registry = registry or AgentRegistry()

    def create_plan(self, task: Task, strategy: str = "capability_match") -> ExecutionPlan:
        """Create an execution plan for the supplied task."""
        candidates = self._select_candidates(task, strategy)
        selected_agents = [agent.id for agent in candidates]
        return ExecutionPlan(
            task=task,
            selected_agents=selected_agents,
            routing_strategy=strategy,
            estimated_execution_time=self._estimate_time(len(selected_agents)),
            metadata={"required_capabilities": list(task.required_capabilities)},
        )

    def _select_candidates(self, task: Task, strategy: str) -> list:
        """Select candidate agents according to the requested routing strategy."""
        healthy_agents = [
            agent
            for agent in self._registry.list_agents()
            if agent.status == AgentStatus.READY and agent.health_check()
        ]

        if not healthy_agents:
            return []

        if strategy == "round_robin":
            return self._round_robin(healthy_agents)
        if strategy == "least_busy":
            return self._least_busy(healthy_agents)
        if strategy == "highest_priority":
            return self._highest_priority(healthy_agents)
        return self._capability_match(healthy_agents, task.required_capabilities)

    def _round_robin(self, agents: list) -> list:
        """Return a simple round-robin selection from healthy agents."""
        if not agents:
            return []
        return [agents[0]]

    def _least_busy(self, agents: list) -> list:
        """Return the least busy healthy agents first."""
        return sorted(agents, key=lambda agent: agent.status.value)

    def _highest_priority(self, agents: list) -> list:
        """Return agents sorted by priority preference."""
        return sorted(agents, key=lambda agent: agent.name)

    def _capability_match(self, agents: list, required_capabilities: tuple[str, ...]) -> list:
        """Choose agents that support the required capabilities."""
        if not required_capabilities:
            return agents[:1]

        matches = [
            agent
            for agent in agents
            if any(capability in agent.capabilities for capability in required_capabilities)
        ]
        return matches[:1]

    def _estimate_time(self, count: int) -> float:
        """Return a rough execution-time estimate based on candidate count."""
        return round(0.5 * count + 0.2, 2)


__all__ = ["TaskRouter"]
