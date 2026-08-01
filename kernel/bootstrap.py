"""Kernel bootstrap entry point for JARVIS OS.

This module exists to provide a single, explicit initialization boundary for the
operating system runtime. It coordinates the existing core services (configuration,
logging, orchestration, and runtime state) so that the rest of the system can be
started through a stable and testable interface.

Why this file exists
--------------------
The repository already has a mature core runtime, but it lacks a dedicated kernel
layer that can own startup semantics without coupling the rest of the system to
main.py or the orchestrator directly. This module fills that gap by acting as the
first integration point for the new kernel subsystem.

Responsibilities
---------------
- Initialize shared runtime services in a predictable order.
- Create a cohesive bootstrap surface for the application kernel.
- Start the orchestrator through a dependency-injected entry point.
- Expose a small, explicit public API that can be used by higher layers or tests.

Public API
----------
- KernelBootstrap: main bootstrap service object.
- bootstrap(): convenience function for creating and running a bootstrap cycle.

Dependencies
------------
This module depends on the existing core services in the repository:
- core.config
- core.logger
- core.orchestrator

Integration points
------------------
This module is designed to be the first step toward a formal kernel subsystem and
can later be extended to invoke lifecycle, service-container, and event-driven
initialization layers without changing the public contract.

Future extensibility
--------------------
The design deliberately keeps the bootstrap surface small so additional kernel
components can be introduced later around it, including lifecycle hooks,
service registration, and dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.config import ConfigManager, configure
from core.logger import configure_logging, get_logger
from core.orchestrator import Orchestrator, get_orchestrator


@dataclass(slots=True)
class BootstrapResult:
    """Represents the outcome of a bootstrap cycle."""

    initialized: bool
    orchestrator: Optional[Orchestrator] = None


class KernelBootstrap:
    """Coordinate the startup sequence for the JARVIS OS runtime.

    The class is intentionally dependency-injected so the startup path can be
    tested and extended without hard-wiring concrete implementations.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        orchestrator_factory: Optional[Callable[[], Orchestrator]] = None,
        logger_name: str = "kernel.bootstrap",
    ) -> None:
        self._config_manager = config_manager
        self._orchestrator_factory = orchestrator_factory or get_orchestrator
        self._logger_name = logger_name
        self._logger = get_logger(self._logger_name)
        self._initialized = False
        self._orchestrator: Optional[Orchestrator] = None

    def initialize(self) -> BootstrapResult:
        """Initialize the runtime services and start the orchestrator."""
        if self._initialized:
            return BootstrapResult(initialized=True, orchestrator=self._orchestrator)

        config_manager = self._config_manager or configure()
        configure_logging(level=config_manager.get("log_level", "INFO"))
        self._logger = get_logger(self._logger_name)
        self._logger.info("Initializing JARVIS OS kernel bootstrap")

        self._orchestrator = self._orchestrator_factory()
        self._orchestrator.start()

        self._initialized = True
        self._logger.info("Kernel bootstrap completed successfully")
        return BootstrapResult(initialized=True, orchestrator=self._orchestrator)

    def bootstrap(self) -> BootstrapResult:
        """Alias for initialize for callers that prefer a shorter bootstrap API."""
        return self.initialize()

    def is_initialized(self) -> bool:
        """Return whether the bootstrap cycle has completed."""
        return self._initialized

    def get_orchestrator(self) -> Optional[Orchestrator]:
        """Return the active orchestrator instance, if one exists."""
        return self._orchestrator


def bootstrap() -> BootstrapResult:
    """Create and run a kernel bootstrap cycle using the default services."""
    return KernelBootstrap().initialize()


__all__ = ["BootstrapResult", "KernelBootstrap", "bootstrap"]
