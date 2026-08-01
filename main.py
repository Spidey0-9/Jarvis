"""Application bootstrap for JARVIS OS.

This is the top-level entry point for the desktop operating system. It creates
and initializes the orchestration layer, configures the runtime services, and
starts the application lifecycle.
"""

from __future__ import annotations

from core.config import configure
from core.logger import configure_logging, get_logger
from core.orchestrator import get_orchestrator


def bootstrap() -> None:
    """Initialize the application runtime and start the orchestrator."""
    configure()
    configure_logging()
    logger = get_logger("bootstrap")
    logger.info("Bootstrapping JARVIS OS")

    orchestrator = get_orchestrator()
    orchestrator.start()


if __name__ == "__main__":
    bootstrap()
