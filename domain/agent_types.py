"""Shared domain enum for agent roles and responsibilities in JARVIS OS.

This module defines the canonical set of agent categories used by the broader
system, including orchestration, development, automation, memory, vision, and
voice subsystems. Keeping this in the domain layer allows multiple modules to
reuse the same terminology without duplicating enum definitions.
"""

from __future__ import annotations

from enum import Enum


class AgentType(str, Enum):
    """Represents the functional role of an agent within the platform."""

    SYSTEM = "SYSTEM"
    """Core platform agent responsible for infrastructure and lifecycle operations."""

    JARVIS = "JARVIS"
    """Primary orchestrator and user-facing coordinator for the OS experience."""

    DEVELOPER = "DEVELOPER"
    """Agent focused on implementing, refactoring, and maintaining software."""

    TESTER = "TESTER"
    """Agent responsible for validation, test creation, and quality assurance."""

    DESIGNER = "DESIGNER"
    """Agent focused on UI, experience, visual system, and interaction design."""

    RESEARCHER = "RESEARCHER"
    """Agent dedicated to investigation, information gathering, and analysis."""

    AUTOMATION = "AUTOMATION"
    """Agent responsible for desktop automation, tool execution, and workflows."""

    SECURITY = "SECURITY"
    """Agent dedicated to permissions, threat detection, and safe execution."""

    MANAGER = "MANAGER"
    """Agent that coordinates work, tracks progress, and manages priorities."""

    PLANNER = "PLANNER"
    """Agent responsible for planning, decomposition, and execution strategy."""

    ANALYST = "ANALYST"
    """Agent that evaluates information, trends, and operational implications."""

    MEMORY = "MEMORY"
    """Agent responsible for long-term memory, context retention, and data recall."""

    VISION = "VISION"
    """Agent focused on screen understanding, OCR, image analysis, and perception."""

    VOICE = "VOICE"
    """Agent responsible for speech interaction, audio processing, and conversation."""

    PLUGIN = "PLUGIN"
    """Agent or extension role that represents plugin-provided capabilities."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all enum values for validation, UI binding, and serialization."""
        return tuple(member.value for member in cls)
