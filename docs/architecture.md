# JARVIS OS Architecture

## Scheduler

`core.scheduler.Scheduler` is the asynchronous timing and lifecycle boundary for
`contracts.task.Task` instances. It uses a lock-protected priority heap and a
single background dispatcher. All due work is ordered by domain priority and
then by insertion order.

The scheduler follows dependency inversion: it consumes `TaskRouterProtocol`
and `WorkflowEngineProtocol` rather than constructing or controlling workflow
implementations. For every execution attempt it asks the Task Router for an
`ExecutionPlan`, then passes that plan to the Workflow Engine's `execute`
method. A concrete `TaskRouter` is created lazily only when callers do not inject
one.

Lifecycle methods are asynchronous:

- `start()` starts the dispatcher on the current event loop.
- `shutdown()` stops dispatch and, by default, cancels running work.
- `wait_idle()` waits for non-recurring work to reach a terminal state.

Scheduling and control methods (`schedule`, `cancel`, `pause`, and `resume`) are
synchronous, thread-safe entry points. They wake the owning event loop with
`call_soon_threadsafe`, allowing event handlers and worker threads to submit or
control work safely. `schedule` supports monotonic delays, timezone-aware wall
clock targets, fixed-delay recurrence, domain priorities, retry backoff, and
per-attempt timeouts.

The scheduler publishes lifecycle notifications through the optional
`EventBus`. Events use the `scheduler.*` and `task.*` namespaces and contain
schedule IDs, task IDs, status, priority, and attempt metadata. Subscriber
failures are isolated from dispatch and execution.

Callers can inspect state without receiving mutable scheduler internals through
`get_status()` and `get_snapshot()`. Cancellation uses lazy heap invalidation,
so pending, retrying, recurring, and running tasks share one consistent control
path.
