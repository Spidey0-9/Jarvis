"""Shared permission enum for securing sensitive operations in JARVIS OS.

Permissions define the access boundaries for features such as voice, vision,
automation, files, networking, and terminal control. Keeping them in the domain
layer allows plugins, agents, and future security policy layers to share the same
permission vocabulary.
"""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    """Represents a permission that can be granted to an agent or plugin."""

    SYSTEM = "SYSTEM"
    """Access to critical system-level operations and platform controls."""

    VOICE = "VOICE"
    """Permission to use voice input or voice output features."""

    VISION = "VISION"
    """Permission to analyze images, screenshots, or camera streams."""

    AUTOMATION = "AUTOMATION"
    """Permission to automate desktop or application interactions."""

    FILES = "FILES"
    """Permission to read, write, or manage file system resources."""

    NETWORK = "NETWORK"
    """Permission to access network resources and remote services."""

    DATABASE = "DATABASE"
    """Permission to access databases and structured storage."""

    CAMERA = "CAMERA"
    """Permission to access camera hardware or visual capture devices."""

    MICROPHONE = "MICROPHONE"
    """Permission to record audio from microphone input."""

    TERMINAL = "TERMINAL"
    """Permission to execute terminal commands and shell operations."""

    NOTIFICATIONS = "NOTIFICATIONS"
    """Permission to display notifications or alert the user."""

    PLUGINS = "PLUGINS"
    """Permission to install, configure, or manage plugins and extensions."""

    MEMORY = "MEMORY"
    """Permission to access long-term or contextual memory storage."""

    SECURITY = "SECURITY"
    """Permission to manage security policies, permissions, or protected actions."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all enum values for validation, UI binding, and serialization."""
        return tuple(member.value for member in cls)
