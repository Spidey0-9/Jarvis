"""Event bus for decoupled communication within JARVIS OS.

The event bus allows modules to publish and subscribe to typed events without
creating hard dependencies between components. This is the foundation for the
orchestrator and plugin-driven architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass(slots=True)
class Event:
    """Simple application event container."""

    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


class EventBus:
    """Thread-safe-ish in-process event dispatcher."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Register a handler for a specific event name."""
        self._subscribers.setdefault(event_name, set()).add(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Remove a previously registered handler."""
        if event_name in self._subscribers:
            self._subscribers[event_name].discard(handler)

    def publish(self, event_name: str, payload: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        """Publish an event to all subscribers."""
        event = Event(name=event_name, payload=payload or {}, source=source)
        for handler in list(self._subscribers.get(event_name, set())):
            handler(event)


__all__ = ["Event", "EventBus"]
