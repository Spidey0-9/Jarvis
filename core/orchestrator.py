"""Core orchestrator for JARVIS OS.

The orchestrator is the central coordinator for the application lifecycle.
It wires together configuration, logging, event dispatch, and runtime state,
then provides a structured entry point for startup and shutdown.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import ConfigManager, get_config
from .events import EventBus
from .logger import configure_logging, get_logger
from .state import GlobalStateManager


class Orchestrator:
    """Coordinate application startup, lifecycle, and agent routing."""

    _instance: Optional["Orchestrator"] = None

    def __new__(cls, *args, **kwargs) -> "Orchestrator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._config_manager = ConfigManager()
        self._event_bus = EventBus()
        self._state_manager = GlobalStateManager()
        self._logger = get_logger("orchestrator")
        self._bootstrap()

    def _bootstrap(self) -> None:
        """Initialize core services and set application defaults."""
        configure_logging(level=self._config_manager.get("log_level", "INFO"))
        self._logger = get_logger("orchestrator")
        self._logger.info("Orchestrator bootstrapping core services")

        self._state_manager.set("is_running", True)
        self._state_manager.set("session_id", "session:startup")
        self._state_manager.set("current_agent", "jarvis")

    def start(self) -> None:
        """Start the application runtime."""
        self._logger.info("Starting JARVIS OS")
        self._state_manager.set("is_running", True)
        self._event_bus.publish("system.start", source="orchestrator")

    def stop(self) -> None:
        """Stop the application runtime cleanly."""
        self._logger.info("Stopping JARVIS OS")
        self._state_manager.set("is_running", False)
        self._event_bus.publish("system.stop", source="orchestrator")

    def route(self, intent: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Route an intent to the appropriate subsystem or agent."""
        self._logger.info("Routing intent: %s", intent)
        self._event_bus.publish("intent.received", payload={"intent": intent, **(payload or {})}, source="orchestrator")
        return intent

    def get_event_bus(self) -> EventBus:
        """Return the shared event bus."""
        return self._event_bus

    def get_state_manager(self) -> GlobalStateManager:
        """Return the shared state manager."""
        return self._state_manager

    def get_config_manager(self) -> ConfigManager:
        """Return the shared configuration manager."""
        return self._config_manager


def get_orchestrator() -> Orchestrator:
    """Convenience accessor for the shared orchestrator."""
    return Orchestrator()


__all__ = ["Orchestrator", "get_orchestrator"]
