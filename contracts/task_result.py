"""Result contract for agent execution outcomes in JARVIS OS.

Agent responses should be represented through this generic contract so the
orchestrator, UI, plugins, and automation layers can consume execution results
uniformly regardless of the agent implementation behind them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


@dataclass(slots=True)
class TaskResult:
    """Generic execution result produced by an agent for a task."""

    task_id: UUID
    agent_name: str
    success: bool
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    output: Any = None
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
