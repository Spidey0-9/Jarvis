"""Execution plan contract for task routing outcomes in JARVIS OS.

An execution plan describes how a task should be routed to one or more agents
without executing the task itself. This keeps routing logic separate from
lifecycle management and execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from contracts.task import Task


@dataclass(slots=True)
class ExecutionPlan:
    """Represents the routing decision for a task."""

    task: Task
    selected_agents: list[str] = field(default_factory=list)
    routing_strategy: str = "capability_match"
    estimated_execution_time: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
