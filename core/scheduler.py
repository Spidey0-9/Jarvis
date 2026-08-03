"""Asynchronous, thread-safe task scheduling for JARVIS OS.

The scheduler owns timing and lifecycle policy while delegating routing to the
Task Router and execution to the Workflow Engine.
"""

from __future__ import annotations

import asyncio
import heapq
import inspect
import itertools
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Optional, Protocol, runtime_checkable
from uuid import UUID, uuid4

from contracts.execution_plan import ExecutionPlan
from contracts.task import Task
from domain.priority import Priority

from .events import EventBus


class ScheduledTaskStatus(str, Enum):
    """Observable lifecycle states for a scheduled task."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@runtime_checkable
class TaskRouterProtocol(Protocol):
    """Routing behavior required by the scheduler."""

    def create_plan(
        self, task: Task, strategy: str = "capability_match"
    ) -> ExecutionPlan:
        """Create an execution plan for a task."""


@runtime_checkable
class WorkflowEngineProtocol(Protocol):
    """Workflow behavior required by the scheduler."""

    def execute(self, plan: ExecutionPlan) -> Awaitable[Any] | Any:
        """Execute a routed plan and return its result."""


@dataclass(frozen=True, slots=True)
class ScheduledTaskSnapshot:
    """Immutable public view of scheduler-owned task state."""

    schedule_id: UUID
    task: Task
    status: ScheduledTaskStatus
    priority: Priority
    attempt: int
    retry_limit: int
    interval: Optional[float]
    next_run_at: Optional[datetime]
    last_error: Optional[str]


@dataclass(slots=True)
class _ScheduledTask:
    schedule_id: UUID
    task: Task
    priority: Priority
    due_at: float
    interval: Optional[float]
    retry_delay: float
    retry_backoff: float
    sequence: int
    status: ScheduledTaskStatus = ScheduledTaskStatus.SCHEDULED
    attempt: int = 0
    generation: int = 0
    last_error: Optional[str] = None
    running_task: Optional[asyncio.Task[None]] = field(default=None, repr=False)


class Scheduler:
    """Event-driven scheduler safe for async and cross-thread callers.

    Public scheduling and control methods are synchronous and lock-protected so
    event handlers and worker threads can call them. Actual task execution is
    always asynchronous on the event loop supplied by :meth:`start`.
    """

    def __init__(
        self,
        workflow_engine: WorkflowEngineProtocol,
        task_router: Optional[TaskRouterProtocol] = None,
        event_bus: Optional[EventBus] = None,
        *,
        routing_strategy: str = "capability_match",
    ) -> None:
        if not hasattr(workflow_engine, "execute"):
            raise TypeError("workflow_engine must provide an execute(plan) method")

        if task_router is None:
            from .task_router import TaskRouter

            task_router = TaskRouter()

        self._workflow_engine = workflow_engine
        self._task_router = task_router
        self._event_bus = event_bus
        self._routing_strategy = routing_strategy
        self._lock = threading.RLock()
        self._event_lock = threading.RLock()
        self._entries: dict[UUID, _ScheduledTask] = {}
        self._queue: list[tuple[float, int, UUID, int]] = []
        self._sequence = itertools.count()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._wake_event: Optional[asyncio.Event] = None
        self._dispatcher_task: Optional[asyncio.Task[None]] = None
        self._paused = False
        self._stopping = False

    @property
    def is_running(self) -> bool:
        """Return whether the background dispatcher is active."""
        with self._lock:
            return self._dispatcher_task is not None and not self._dispatcher_task.done()

    @property
    def is_paused(self) -> bool:
        """Return whether dispatch of pending work is paused."""
        with self._lock:
            return self._paused

    async def start(self) -> None:
        """Start background dispatch on the current event loop."""
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._dispatcher_task is not None and not self._dispatcher_task.done():
                if self._loop is not loop:
                    raise RuntimeError("scheduler is already running on another event loop")
                return
            self._loop = loop
            self._wake_event = asyncio.Event()
            self._stopping = False
            self._dispatcher_task = loop.create_task(
                self._dispatch_loop(), name="jarvis-scheduler-dispatcher"
            )
        self._publish("scheduler.started")

    async def shutdown(self, *, cancel_running: bool = True) -> None:
        """Stop dispatch and optionally cancel in-flight executions."""
        with self._lock:
            dispatcher = self._dispatcher_task
            if dispatcher is None:
                return
            self._stopping = True
            running = [
                entry.running_task
                for entry in self._entries.values()
                if entry.running_task is not None and not entry.running_task.done()
            ]

        self._wake()
        if dispatcher is not asyncio.current_task() and not dispatcher.done():
            dispatcher.cancel()
            await asyncio.gather(dispatcher, return_exceptions=True)
        if cancel_running:
            for task in running:
                task.cancel()
        if running:
            await asyncio.gather(*running, return_exceptions=True)

        with self._lock:
            self._dispatcher_task = None
            self._wake_event = None
            self._loop = None
            self._stopping = False
        self._publish("scheduler.stopped")

    def schedule(
        self,
        task: Task,
        *,
        delay: float = 0.0,
        run_at: Optional[datetime] = None,
        interval: Optional[float] = None,
        priority: Optional[Priority] = None,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
    ) -> UUID:
        """Schedule a task and return its scheduler-specific identifier."""
        self._validate_schedule(
            task, delay, run_at, interval, retry_delay, retry_backoff
        )
        selected_priority = priority or self._coerce_priority(task.priority)
        if not isinstance(selected_priority, Priority):
            raise TypeError("priority must be a Priority")
        with self._lock:
            entry = _ScheduledTask(
                schedule_id=uuid4(),
                task=task,
                priority=selected_priority,
                due_at=time.monotonic() + self._initial_delay(delay, run_at),
                interval=interval,
                retry_delay=retry_delay,
                retry_backoff=retry_backoff,
                sequence=next(self._sequence),
            )
            self._entries[entry.schedule_id] = entry
            self._push(entry)
        self._publish_threadsafe("task.scheduled", entry)
        self._wake()
        return entry.schedule_id

    def cancel(self, schedule_id: UUID) -> bool:
        """Cancel pending, recurring, retrying, or running scheduled work."""
        terminal = {
            ScheduledTaskStatus.CANCELLED,
            ScheduledTaskStatus.COMPLETED,
            ScheduledTaskStatus.FAILED,
            ScheduledTaskStatus.TIMED_OUT,
        }
        with self._lock:
            entry = self._entries.get(schedule_id)
            if entry is None or entry.status in terminal:
                return False
            entry.status = ScheduledTaskStatus.CANCELLED
            entry.generation += 1
            running_task = entry.running_task
        if running_task is not None and not running_task.done():
            self._call_on_loop(running_task.cancel)
        self._publish_threadsafe("task.cancelled", entry)
        self._wake()
        return True

    def pause(self) -> bool:
        """Pause new dispatch while allowing running work to finish."""
        with self._lock:
            if self._paused:
                return False
            self._paused = True
        self._publish_threadsafe("scheduler.paused")
        self._wake()
        return True

    def resume(self) -> bool:
        """Resume dispatch of queued work."""
        with self._lock:
            if not self._paused:
                return False
            self._paused = False
        self._publish_threadsafe("scheduler.resumed")
        self._wake()
        return True

    def get_status(self, schedule_id: UUID) -> Optional[ScheduledTaskStatus]:
        """Return the current status for a schedule identifier."""
        with self._lock:
            entry = self._entries.get(schedule_id)
            return entry.status if entry is not None else None

    def get_snapshot(self, schedule_id: UUID) -> Optional[ScheduledTaskSnapshot]:
        """Return an immutable snapshot of scheduled state."""
        with self._lock:
            entry = self._entries.get(schedule_id)
            if entry is None:
                return None
            next_run_at = None
            if entry.status in {
                ScheduledTaskStatus.SCHEDULED,
                ScheduledTaskStatus.RETRYING,
            }:
                remaining = max(0.0, entry.due_at - time.monotonic())
                next_run_at = datetime.now(timezone.utc) + timedelta(seconds=remaining)
            return ScheduledTaskSnapshot(
                schedule_id=entry.schedule_id,
                task=entry.task,
                status=entry.status,
                priority=entry.priority,
                attempt=entry.attempt,
                retry_limit=entry.task.retry_limit,
                interval=entry.interval,
                next_run_at=next_run_at,
                last_error=entry.last_error,
            )

    async def wait_idle(self, timeout: Optional[float] = None) -> None:
        """Wait until no non-recurring work is queued or executing."""

        async def wait_until_idle() -> None:
            while True:
                with self._lock:
                    busy = any(
                        entry.interval is None
                        and entry.status
                        in {
                            ScheduledTaskStatus.SCHEDULED,
                            ScheduledTaskStatus.RETRYING,
                            ScheduledTaskStatus.RUNNING,
                        }
                        for entry in self._entries.values()
                    )
                if not busy:
                    return
                await asyncio.sleep(0.001)

        if timeout is None:
            await wait_until_idle()
        else:
            await asyncio.wait_for(wait_until_idle(), timeout=timeout)

    async def _dispatch_loop(self) -> None:
        while True:
            with self._lock:
                if self._stopping:
                    return
                paused = self._paused
                wake_event = self._wake_event
                self._discard_stale_head()
                next_due = self._queue[0][0] if self._queue else None

            if wake_event is None:
                return
            wake_event.clear()
            if paused or next_due is None:
                await wake_event.wait()
                continue

            delay = next_due - time.monotonic()
            if delay > 0:
                try:
                    await asyncio.wait_for(wake_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                continue

            due_entries = self._take_due_entries()
            due_entries.sort(
                key=lambda item: (-Priority.rank(item.priority), item.sequence)
            )
            for entry in due_entries:
                with self._lock:
                    if entry.status not in {
                        ScheduledTaskStatus.SCHEDULED,
                        ScheduledTaskStatus.RETRYING,
                    }:
                        continue
                    entry.status = ScheduledTaskStatus.RUNNING
                    execution = asyncio.create_task(
                        self._execute(entry),
                        name=f"scheduled-task-{entry.schedule_id}",
                    )
                    entry.running_task = execution

    async def _execute(self, entry: _ScheduledTask) -> None:
        with self._lock:
            entry.attempt += 1
        self._publish("task.started", self._payload(entry))
        try:
            plan = self._task_router.create_plan(entry.task, self._routing_strategy)
            execution = self._run_workflow(plan)
            if entry.task.timeout is None:
                await execution
            else:
                await asyncio.wait_for(execution, timeout=entry.task.timeout)
        except asyncio.CancelledError:
            with self._lock:
                entry.running_task = None
                publish_cancel = entry.status is not ScheduledTaskStatus.CANCELLED
                entry.status = ScheduledTaskStatus.CANCELLED
            if publish_cancel:
                self._publish("task.cancelled", self._payload(entry))
            return
        except asyncio.TimeoutError as error:
            self._handle_failure(entry, error, timed_out=True)
            return
        except Exception as error:
            self._handle_failure(entry, error, timed_out=False)
            return

        with self._lock:
            entry.running_task = None
            if entry.status is ScheduledTaskStatus.CANCELLED:
                return
            entry.status = ScheduledTaskStatus.COMPLETED
            entry.last_error = None
        self._publish("task.completed", self._payload(entry))
        self._schedule_recurrence(entry)

    async def _run_workflow(self, plan: ExecutionPlan) -> Any:
        execute = self._workflow_engine.execute
        if inspect.iscoroutinefunction(execute):
            return await execute(plan)
        result = await asyncio.to_thread(execute, plan)
        if inspect.isawaitable(result):
            return await result
        return result

    def _handle_failure(
        self, entry: _ScheduledTask, error: BaseException, *, timed_out: bool
    ) -> None:
        error_text = str(error) or type(error).__name__
        with self._lock:
            entry.running_task = None
            if entry.status is ScheduledTaskStatus.CANCELLED:
                return
            entry.last_error = error_text
            can_retry = entry.attempt <= entry.task.retry_limit
            if can_retry:
                entry.status = ScheduledTaskStatus.RETRYING
                retry_in = entry.retry_delay * (
                    entry.retry_backoff ** (entry.attempt - 1)
                )
                entry.due_at = time.monotonic() + retry_in
                entry.generation += 1
                entry.sequence = next(self._sequence)
                self._push(entry)
            else:
                entry.status = (
                    ScheduledTaskStatus.TIMED_OUT
                    if timed_out
                    else ScheduledTaskStatus.FAILED
                )

        self._publish(
            "task.timed_out" if timed_out else "task.failed",
            self._payload(entry, error=error_text),
        )
        if can_retry:
            self._publish(
                "task.retry_scheduled", self._payload(entry, retry_in=retry_in)
            )
            self._wake()
        else:
            self._schedule_recurrence(entry)

    def _schedule_recurrence(self, entry: _ScheduledTask) -> None:
        if entry.interval is None:
            return
        with self._lock:
            if entry.status is ScheduledTaskStatus.CANCELLED or self._stopping:
                return
            entry.status = ScheduledTaskStatus.SCHEDULED
            entry.attempt = 0
            entry.due_at = time.monotonic() + entry.interval
            entry.generation += 1
            entry.sequence = next(self._sequence)
            self._push(entry)
        self._publish("task.scheduled", self._payload(entry, recurring=True))
        self._wake()

    def _take_due_entries(self) -> list[_ScheduledTask]:
        now = time.monotonic()
        result: list[_ScheduledTask] = []
        with self._lock:
            while self._queue and self._queue[0][0] <= now:
                _, _, schedule_id, generation = heapq.heappop(self._queue)
                entry = self._entries.get(schedule_id)
                if entry is not None and entry.generation == generation:
                    result.append(entry)
        return result

    def _discard_stale_head(self) -> None:
        schedulable = {
            ScheduledTaskStatus.SCHEDULED,
            ScheduledTaskStatus.RETRYING,
        }
        while self._queue:
            _, _, schedule_id, generation = self._queue[0]
            entry = self._entries.get(schedule_id)
            if (
                entry is not None
                and entry.generation == generation
                and entry.status in schedulable
            ):
                return
            heapq.heappop(self._queue)

    def _push(self, entry: _ScheduledTask) -> None:
        heapq.heappush(
            self._queue,
            (entry.due_at, entry.sequence, entry.schedule_id, entry.generation),
        )

    def _wake(self) -> None:
        with self._lock:
            loop = self._loop
            wake_event = self._wake_event
        if loop is not None and wake_event is not None and not loop.is_closed():
            loop.call_soon_threadsafe(wake_event.set)

    def _call_on_loop(self, callback: Callable[[], Any]) -> None:
        with self._lock:
            loop = self._loop
        if loop is None or loop.is_closed():
            callback()
        else:
            loop.call_soon_threadsafe(callback)

    def _publish_threadsafe(
        self, event_name: str, entry: Optional[_ScheduledTask] = None
    ) -> None:
        payload = self._payload(entry) if entry is not None else None
        self._call_on_loop(lambda: self._publish(event_name, payload))

    def _publish(
        self, event_name: str, payload: Optional[dict[str, Any]] = None
    ) -> None:
        if self._event_bus is None:
            return
        try:
            with self._event_lock:
                self._event_bus.publish(
                    event_name, payload=payload, source="scheduler"
                )
        except Exception:
            # A subscriber failure must not stop scheduling or task execution.
            return

    @staticmethod
    def _payload(entry: _ScheduledTask, **additional: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schedule_id": str(entry.schedule_id),
            "task_id": str(entry.task.id),
            "status": entry.status.value,
            "attempt": entry.attempt,
            "priority": entry.priority.value,
        }
        payload.update(additional)
        return payload

    @staticmethod
    def _coerce_priority(value: str) -> Priority:
        try:
            return Priority(value.upper())
        except ValueError as error:
            raise ValueError(f"unknown task priority: {value!r}") from error

    @staticmethod
    def _initial_delay(delay: float, run_at: Optional[datetime]) -> float:
        if run_at is None:
            return delay
        return max(0.0, (run_at - datetime.now(timezone.utc)).total_seconds())

    @staticmethod
    def _validate_schedule(
        task: Task,
        delay: float,
        run_at: Optional[datetime],
        interval: Optional[float],
        retry_delay: float,
        retry_backoff: float,
    ) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be a Task")
        if delay < 0:
            raise ValueError("delay cannot be negative")
        if run_at is not None:
            if delay != 0:
                raise ValueError("delay and run_at cannot be used together")
            if run_at.tzinfo is None or run_at.utcoffset() is None:
                raise ValueError("run_at must be timezone-aware")
        if interval is not None and interval <= 0:
            raise ValueError("interval must be greater than zero")
        if retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")
        if retry_backoff < 1:
            raise ValueError("retry_backoff must be at least 1")
        if task.retry_limit < 0:
            raise ValueError("task retry_limit cannot be negative")
        if task.timeout is not None and task.timeout <= 0:
            raise ValueError("task timeout must be greater than zero")


__all__ = [
    "ScheduledTaskSnapshot",
    "ScheduledTaskStatus",
    "Scheduler",
    "TaskRouterProtocol",
    "WorkflowEngineProtocol",
]
