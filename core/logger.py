"""Production-grade logging utilities for JARVIS OS.

This module provides a centralized logging configuration that can be reused
across all application layers. It is designed to work in both development and
production environments without requiring global state or ad-hoc setup.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class JARVISLogger:
    """Singleton-style logger factory with file and console output."""

    _instance: Optional["JARVISLogger"] = None

    def __new__(cls, *args, **kwargs) -> "JARVISLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: Optional[str | Path] = None, level: Optional[str] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._log_dir = Path(log_dir or self._default_log_dir())
        self._log_dir.mkdir(parents=True, exist_ok=True)

        configured_level = self._resolve_level(level)
        self._level = configured_level
        self._configure_root_logger(configured_level)

    def _default_log_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "logs"

    def _resolve_level(self, level: Optional[str]) -> int:
        if level is None:
            level = os.getenv("JARVIS_LOG_LEVEL", "INFO")

        normalized = str(level).upper()
        mapping = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }
        return mapping.get(normalized, logging.INFO)

    def _configure_root_logger(self, level: int) -> None:
        root_logger = logging.getLogger("jarvis")
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        root_logger.propagate = False

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            self._log_dir / "jarvis.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    def get_logger(self, name: str = "jarvis") -> logging.Logger:
        """Return a module-specific logger instance."""
        logger = logging.getLogger(f"jarvis.{name}")
        logger.setLevel(self._level)
        logger.propagate = False
        return logger


def configure_logging(log_dir: Optional[str | Path] = None, level: Optional[str] = None) -> JARVISLogger:
    """Configure the shared logging system for the application."""
    return JARVISLogger(log_dir=log_dir, level=level)


def get_logger(name: str = "core") -> logging.Logger:
    """Convenience function for retrieving an application logger."""
    return JARVISLogger().get_logger(name)


__all__ = ["JARVISLogger", "configure_logging", "get_logger"]
