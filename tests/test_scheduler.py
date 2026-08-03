"""Tests for the asynchronous core scheduler."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import pytest

from contracts.execution_plan import ExecutionPlan
from contracts.task import Task
from core.events import Event, EventBus
from core.scheduler import ScheduledTaskStatus, Scheduler
from domain.priority import Priority


class FakeRouter:
    def __init__(self) -> None:
        self.calls: list[tuple[Task, str]] = []

    def create_plan(
        self, task: Task, strategy: str = "capability_match"
    ) -> ExecutionPlan:
        self.calls.append((task, strategy))
        return ExecutionPlan(task=task, selected_agents=["test-agent"])


class FakeWorkflowEngine:
    def __init__(
        self, outcomes: Optional[list[BaseException | Any]] = None
    ) -> None:
        self.outcomes = list(outcomes or [])
        self.calls: list[ExecutionPlan] = []

    async def execute(self, plan: ExecutionPlan) -> Any:
        self.calls.append(plan)
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        return plan.task.title


async def eventually(
    predicate: Callable[[], bool], *, timeout: float = 1.0
) -> None:
    async def poll() -> None:
        while not predicate():
            await asyncio.sleep(0.001)

    await asyncio.wait_for(poll(), timeout=timeout)


def test_routes_and_executes_delayed_task_in_background() -> None:
    async def scenario() -> None:
        router = FakeRouter()
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, router)
        await scheduler.start()
        try:
            task = Task(title="delayed")
            schedule_id = scheduler.schedule(task, delay=0.03)
            await asyncio.sleep(0.005)
            assert engine.calls == []

            await scheduler.wait_idle(timeout=1)
            assert [call.task for call in engine.calls] == [task]
            assert router.calls == [(task, "capability_match")]
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.COMPLETED
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_due_tasks_use_priority_then_fifo_order() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        scheduler.pause()
        try:
            scheduler.schedule(Task(title="low"), priority=Priority.LOW)
            scheduler.schedule(Task(title="critical-1"), priority=Priority.CRITICAL)
            scheduler.schedule(Task(title="critical-2"), priority=Priority.CRITICAL)
            scheduler.resume()
            await scheduler.wait_idle(timeout=1)
            assert [plan.task.title for plan in engine.calls] == [
                "critical-1",
                "critical-2",
                "low",
            ]
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_pause_and_resume_control_dispatch() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            assert scheduler.pause()
            assert not scheduler.pause()
            schedule_id = scheduler.schedule(Task(title="paused"))
            await asyncio.sleep(0.02)
            assert engine.calls == []
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.SCHEDULED

            assert scheduler.resume()
            assert not scheduler.resume()
            await scheduler.wait_idle(timeout=1)
            assert len(engine.calls) == 1
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_recurring_task_runs_until_cancelled() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(Task(title="recurring"), interval=0.01)
            await eventually(lambda: len(engine.calls) >= 3)
            assert scheduler.cancel(schedule_id)
            call_count = len(engine.calls)
            await asyncio.sleep(0.04)
            assert len(engine.calls) == call_count
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.CANCELLED
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_failures_retry_with_backoff_then_complete() -> None:
    async def scenario() -> None:
        events: list[Event] = []
        bus = EventBus()
        bus.subscribe("task.retry_scheduled", events.append)
        engine = FakeWorkflowEngine([RuntimeError("one"), RuntimeError("two"), "ok"])
        scheduler = Scheduler(engine, FakeRouter(), bus)
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(
                Task(title="retry", retry_limit=2),
                retry_delay=0.005,
                retry_backoff=1,
            )
            await scheduler.wait_idle(timeout=1)
            snapshot = scheduler.get_snapshot(schedule_id)
            assert snapshot is not None
            assert snapshot.status is ScheduledTaskStatus.COMPLETED
            assert snapshot.attempt == 3
            assert len(events) == 2
            assert len(engine.calls) == 3
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_retry_exhaustion_records_failure() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine([ValueError("bad"), ValueError("still bad")])
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(
                Task(title="failure", retry_limit=1), retry_delay=0
            )
            await scheduler.wait_idle(timeout=1)
            snapshot = scheduler.get_snapshot(schedule_id)
            assert snapshot is not None
            assert snapshot.status is ScheduledTaskStatus.FAILED
            assert snapshot.attempt == 2
            assert snapshot.last_error == "still bad"
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_timeout_is_reported_and_can_be_retried() -> None:
    class SlowThenFastEngine:
        def __init__(self) -> None:
            self.calls = 0

        async def execute(self, plan: ExecutionPlan) -> str:
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(0.1)
            return "done"

    async def scenario() -> None:
        engine = SlowThenFastEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(
                Task(title="timeout", timeout=0.01, retry_limit=1), retry_delay=0
            )
            await scheduler.wait_idle(timeout=1)
            assert engine.calls == 2
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.COMPLETED
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_pending_task_can_be_cancelled() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(Task(title="cancel"), delay=0.1)
            assert scheduler.cancel(schedule_id)
            assert not scheduler.cancel(schedule_id)
            await asyncio.sleep(0.12)
            assert engine.calls == []
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.CANCELLED
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_running_task_can_be_cancelled() -> None:
    class BlockingEngine:
        def __init__(self) -> None:
            self.started = asyncio.Event()
            self.cancelled = False

        async def execute(self, plan: ExecutionPlan) -> None:
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    async def scenario() -> None:
        engine = BlockingEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        try:
            schedule_id = scheduler.schedule(Task(title="running"))
            await asyncio.wait_for(engine.started.wait(), timeout=1)
            assert scheduler.cancel(schedule_id)
            await eventually(lambda: engine.cancelled)
            assert scheduler.get_status(schedule_id) is ScheduledTaskStatus.CANCELLED
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_events_include_scheduler_and_task_lifecycle() -> None:
    async def scenario() -> None:
        names: list[str] = []
        bus = EventBus()
        for name in (
            "scheduler.started",
            "task.scheduled",
            "task.started",
            "task.completed",
            "scheduler.stopped",
        ):
            bus.subscribe(name, lambda event: names.append(event.name))

        scheduler = Scheduler(FakeWorkflowEngine(), FakeRouter(), bus)
        await scheduler.start()
        scheduler.schedule(Task(title="events"))
        await scheduler.wait_idle(timeout=1)
        await scheduler.shutdown()
        assert names == [
            "scheduler.started",
            "task.scheduled",
            "task.started",
            "task.completed",
            "scheduler.stopped",
        ]

    asyncio.run(scenario())


def test_task_can_be_scheduled_from_another_thread() -> None:
    async def scenario() -> None:
        engine = FakeWorkflowEngine()
        scheduler = Scheduler(engine, FakeRouter())
        await scheduler.start()
        identifiers = []
        worker = threading.Thread(
            target=lambda: identifiers.append(
                scheduler.schedule(Task(title="threaded"))
            )
        )
        worker.start()
        worker.join(timeout=1)
        try:
            assert not worker.is_alive()
            await scheduler.wait_idle(timeout=1)
            assert len(identifiers) == 1
            assert [plan.task.title for plan in engine.calls] == ["threaded"]
        finally:
            await scheduler.shutdown()

    asyncio.run(scenario())


def test_run_at_snapshot_and_validation() -> None:
    engine = FakeWorkflowEngine()
    scheduler = Scheduler(engine, FakeRouter())
    run_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    schedule_id = scheduler.schedule(Task(title="future"), run_at=run_at)
    snapshot = scheduler.get_snapshot(schedule_id)

    assert snapshot is not None
    assert snapshot.next_run_at is not None
    assert snapshot.priority is Priority.NORMAL
    assert snapshot.retry_limit == 0
    with pytest.raises(ValueError, match="timezone-aware"):
        scheduler.schedule(Task(), run_at=datetime.now())
    with pytest.raises(ValueError, match="interval"):
        scheduler.schedule(Task(), interval=0)
    with pytest.raises(ValueError, match="unknown task priority"):
        scheduler.schedule(Task(priority="impossible"))


def test_start_and_shutdown_are_idempotent() -> None:
    async def scenario() -> None:
        scheduler = Scheduler(FakeWorkflowEngine(), FakeRouter())
        await scheduler.start()
        dispatcher = scheduler._dispatcher_task
        await scheduler.start()
        assert scheduler._dispatcher_task is dispatcher
        await scheduler.shutdown()
        await scheduler.shutdown()
        assert not scheduler.is_running

    asyncio.run(scenario())
