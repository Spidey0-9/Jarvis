"""Dependency management container for JARVIS OS kernel services.

Why this file exists
--------------------
The kernel needs a controlled way to assemble and access shared services without
hard-coding concrete implementations inside bootstrap logic or application layers.
This module provides a central registry that supports dependency injection,
lazy initialization, and explicit service ownership while keeping the runtime
thread-safe and extensible.

Why bootstrap should depend on it
--------------------------------
Bootstrap should not be responsible for constructing every kernel dependency by
hand. By depending on a service container, startup becomes declarative: the
bootstrap layer registers the required services and resolves them when needed.
This keeps initialization logic small, improves testability, and makes it easier
to replace implementations later.

Future integration with plugins
-------------------------------
The container is intentionally generic so plugin subsystems can register their own
services without modifying kernel bootstrap. In future iterations, plugins can
register providers dynamically, and the container can resolve them through the
same interface used by core services.

Responsibilities
---------------
- Store service provider factories instead of instantiating implementations eagerly.
- Register singleton or instance-backed services in a type-safe manner.
- Resolve services on demand with optional lazy initialization.
- Replace or remove services cleanly.
- Provide a thread-safe API suitable for async and concurrent startup paths.

Public API
----------
- ServiceContainer.register(provider, service_type=None, *, singleton=True)
- ServiceContainer.register_instance(instance, service_type=None)
- ServiceContainer.resolve(service_type)
- ServiceContainer.contains(service_type)
- ServiceContainer.remove(service_type)
- ServiceContainer.clear()

Dependencies
------------
This module is intentionally self-contained and only depends on the Python
standard library.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar, cast

T = TypeVar("T")


class SupportsResolve(Protocol[T]):
    """Protocol for service types that can be resolved by the container."""


@dataclass(slots=True)
class ServiceRegistration(Generic[T]):
    """Represents a registered service entry within the container."""

    provider: Callable[[], T]
    singleton: bool = True
    instance: Optional[T] = None


class ServiceContainer:
    """Central registry for dependency-injected services.

    The container never instantiates concrete services by itself. Instead, it
    stores provider factories and only invokes them when a service is resolved.
    This makes the design lazy, composable, and easy to test.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._services: dict[type[Any], ServiceRegistration[Any]] = {}

    def register(
        self,
        provider: Callable[[], T],
        service_type: Optional[type[T]] = None,
        *,
        singleton: bool = True,
    ) -> None:
        """Register a provider factory for a service type.

        Parameters
        ----------
        provider:
            A zero-argument callable that produces a service instance.
        service_type:
            The service type to register under. If omitted, the provider's return
            annotation is used when available.
        singleton:
            If True, the service will be cached after first resolution.
        """
        resolved_type = self._infer_service_type(provider, service_type)
        registration = ServiceRegistration(provider=provider, singleton=singleton)
        with self._lock:
            self._services[resolved_type] = registration

    def register_instance(self, instance: T, service_type: Optional[type[T]] = None) -> None:
        """Register a pre-built instance as a singleton service."""
        resolved_type = self._infer_service_type_from_instance(instance, service_type)
        registration = ServiceRegistration(provider=lambda: instance, singleton=True, instance=instance)
        with self._lock:
            self._services[resolved_type] = registration

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a registered service, creating it on demand when needed."""
        with self._lock:
            registration = self._services.get(service_type)
            if registration is None:
                raise KeyError(f"Service not registered: {service_type.__name__}")

            if registration.instance is not None:
                return cast(T, registration.instance)

            if registration.singleton:
                instance = registration.provider()
                registration.instance = instance
                return cast(T, instance)

            return cast(T, registration.provider())

    def contains(self, service_type: type[Any]) -> bool:
        """Return whether the container has a registration for the given type."""
        with self._lock:
            return service_type in self._services

    def remove(self, service_type: type[Any]) -> None:
        """Remove a service registration from the container."""
        with self._lock:
            self._services.pop(service_type, None)

    def clear(self) -> None:
        """Remove all registered services from the container."""
        with self._lock:
            self._services.clear()

    def _infer_service_type(self, provider: Callable[[], T], service_type: Optional[type[T]]) -> type[T]:
        if service_type is not None:
            return service_type

        annotation = self._get_return_annotation(provider)
        if annotation is None:
            raise TypeError("Service type could not be inferred; pass service_type explicitly")
        return cast(type[T], annotation)

    def _infer_service_type_from_instance(self, instance: T, service_type: Optional[type[T]]) -> type[T]:
        if service_type is not None:
            return service_type
        if not hasattr(instance, "__class__"):
            raise TypeError("Service type could not be inferred from instance")
        return cast(type[T], type(instance))

    def _get_return_annotation(self, provider: Callable[[], T]) -> Optional[type[Any]]:
        annotation = getattr(provider, "__annotations__", {}).get("return")
        if annotation is None:
            return None
        if isinstance(annotation, str):
            return None
        return annotation


__all__ = ["ServiceContainer", "ServiceRegistration"]
