"""Global runtime state management for JARVIS OS.

This module holds application-wide state such as current session, active agent,
connection health, and other runtime flags. It avoids the use of global
variables by exposing a shared singleton manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class RuntimeState:
    """Mutable runtime state container."""

    session_id: Optional[str] = None
    current_agent: Optional[str] = None
    is_running: bool = False
    is_listening: bool = False
    is_speaking: bool = False
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GlobalStateManager:
    """Singleton manager for application-wide runtime state."""

    _instance: Optional["GlobalStateManager"] = None

    def __new__(cls, *args, **kwargs) -> "GlobalStateManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._state = RuntimeState()

    def get_state(self) -> RuntimeState:
        """Return the active runtime state object."""
        return self._state

    def set(self, key: str, value: Any) -> None:
        """Set a state field by name."""
        if hasattr(self._state, key):
            setattr(self._state, key, value)
            return
        self._state.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a state field by name."""
        if hasattr(self._state, key):
            return getattr(self._state, key)
        return self._state.metadata.get(key, default)

    def reset(self) -> None:
        """Reset the state to its default values."""
        self._state = RuntimeState()


__all__ = ["RuntimeState", "GlobalStateManager"]
