"""Configuration management for JARVIS OS.

This module centralizes access to application settings from JSON files and
environment variables. It is intentionally dependency-light so it can be used
by the bootstrapping layer and by individual subsystems.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration container for JARVIS OS."""

    app_name: str = "JARVIS OS"
    version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: str = "data"
    plugins_enabled: bool = True
    ai_provider: str = "ollama"
    voice_enabled: bool = True
    automation_enabled: bool = True
    ui_enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Load and expose structured configuration for the application."""

    _instance: Optional["ConfigManager"] = None

    def __new__(cls, *args, **kwargs) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_dir: Optional[str | Path] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._config_dir = Path(config_dir or self._default_config_dir())
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._config_dir / "settings.json"
        self._config = self._load()

    def _default_config_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "config"

    def _load(self) -> AppConfig:
        defaults = AppConfig()
        loaded_settings: Dict[str, Any] = {}

        if self._config_path.exists():
            try:
                with self._config_path.open("r", encoding="utf-8") as handle:
                    loaded_settings = json.load(handle)
            except json.JSONDecodeError:
                loaded_settings = {}

        merged = {**defaults.__dict__, **loaded_settings}
        merged["settings"] = {**defaults.settings, **loaded_settings.get("settings", {})}

        return AppConfig(**merged)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value from the runtime configuration."""
        return getattr(self._config, key, default)

    def get_settings(self) -> Dict[str, Any]:
        """Return the auxiliary settings dictionary."""
        return dict(self._config.settings)

    def update(self, **kwargs: Any) -> None:
        """Update configuration values in memory and on disk."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        self._save()

    def _save(self) -> None:
        payload = {
            "app_name": self._config.app_name,
            "version": self._config.version,
            "debug": self._config.debug,
            "environment": self._config.environment,
            "log_level": self._config.log_level,
            "data_dir": self._config.data_dir,
            "plugins_enabled": self._config.plugins_enabled,
            "ai_provider": self._config.ai_provider,
            "voice_enabled": self._config.voice_enabled,
            "automation_enabled": self._config.automation_enabled,
            "ui_enabled": self._config.ui_enabled,
            "settings": self._config.settings,
        }

        with self._config_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def get_config(self) -> AppConfig:
        """Return the active configuration object."""
        return self._config


def configure(config_dir: Optional[str | Path] = None) -> ConfigManager:
    """Configure and return the shared configuration manager."""
    return ConfigManager(config_dir=config_dir)


def get_config() -> AppConfig:
    """Convenience accessor for the shared configuration."""
    return ConfigManager().get_config()


def get_setting(key: str, default: Any = None) -> Any:
    """Convenience accessor for a single setting."""
    return ConfigManager().get(key, default)


__all__ = ["AppConfig", "ConfigManager", "configure", "get_config", "get_setting"]
