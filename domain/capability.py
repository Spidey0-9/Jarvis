"""Shared capability enum for agents, tasks, plugins, and permissions in JARVIS OS.

Capabilities represent the functional abilities that can be advertised by agents
or required by tasks. Keeping them in the domain layer makes them reusable
across orchestration, routing, plugins, and future permission systems.
"""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    """Represents a functional capability that an agent or plugin may provide."""

    CODE_GENERATION = "CODE_GENERATION"
    """Generate source code, scripts, or implementation patches."""

    CODE_REVIEW = "CODE_REVIEW"
    """Inspect code for correctness, quality, and maintainability."""

    DEBUGGING = "DEBUGGING"
    """Investigate failures and identify root causes in software systems."""

    TESTING = "TESTING"
    """Create or execute tests to validate behavior and quality."""

    DOCUMENTATION = "DOCUMENTATION"
    """Write or maintain technical documentation and explanations."""

    RESEARCH = "RESEARCH"
    """Gather information, analyze context, and produce findings."""

    UI_DESIGN = "UI_DESIGN"
    """Design user interfaces, layouts, and interaction patterns."""

    AUTOMATION = "AUTOMATION"
    """Automate application workflows, desktop actions, or repetitive tasks."""

    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    """Operate system-level actions such as launching applications or managing processes."""

    VOICE_INPUT = "VOICE_INPUT"
    """Capture, interpret, and process spoken user input."""

    VOICE_OUTPUT = "VOICE_OUTPUT"
    """Generate spoken responses or audio output for the user."""

    VISION = "VISION"
    """Understand visual scenes, screenshots, and visual context."""

    OCR = "OCR"
    """Extract text from images, screenshots, or scanned documents."""

    MEMORY = "MEMORY"
    """Store, retrieve, and reason over contextual or long-term memory."""

    SEARCH = "SEARCH"
    """Search local or remote information sources for relevant answers."""

    FILE_SYSTEM = "FILE_SYSTEM"
    """Interact with files, directories, and storage resources."""

    DATABASE = "DATABASE"
    """Read from or write to structured data stores."""

    NETWORK = "NETWORK"
    """Interact with network resources, APIs, or remote services."""

    SECURITY = "SECURITY"
    """Enforce safety, permissions, or secure execution practices."""

    TERMINAL = "TERMINAL"
    """Run terminal commands and interact with shell environments."""

    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"
    """Coordinate planning, progress tracking, and project workflows."""

    NOTIFICATIONS = "NOTIFICATIONS"
    """Send user-facing notifications or alerts."""

    PLUGIN_MANAGEMENT = "PLUGIN_MANAGEMENT"
    """Install, configure, or manage plugins and extensions."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all enum values for validation, UI binding, and serialization."""
        return tuple(member.value for member in cls)
