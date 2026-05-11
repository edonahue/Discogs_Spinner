"""Abstract player backend contract shared by core use-cases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class ProviderDescriptor(TypedDict, total=False):
    """Provider metadata surfaced through readiness contracts."""

    auth_required: bool
    supported_capabilities: list[str]
    setup_url: str
    oauth_guide_url: str
    next_actions_when_unconfigured: list[str]
    can_skip_setup: bool
    can_retry_setup: bool


class PlayerBackendError(RuntimeError):
    """Base class for player backend failures."""


class PlayerDependencyError(PlayerBackendError):
    """Raised when an optional backend dependency is not available."""


class PlayerAuthError(PlayerBackendError):
    """Raised for backend authentication/configuration failures."""


class PlayerApiError(PlayerBackendError):
    """Raised when backend API requests fail."""


class PlayerPlaybackError(PlayerApiError):
    """Raised when backend playback start fails."""


class PlayerBackend(ABC):
    """Contract for playback/matching backends used by core flows."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique backend id."""

    @classmethod
    @abstractmethod
    def addon_available(cls) -> bool:
        """Whether this optional backend addon is available in this environment."""

    @abstractmethod
    def is_configured(self, *, conn=None) -> bool:
        """Whether this backend has enough configuration for authenticated use."""

    @abstractmethod
    def list_devices(self, *, conn=None) -> list[dict[str, object]]:
        """Return playable devices."""

    @abstractmethod
    def start_album_playback(
        self,
        provider_album_id: str,
        *,
        device_id: str | None = None,
        conn=None,
    ) -> None:
        """Start playback for an album on an optional device."""

    @abstractmethod
    def create_matching_client(self, *, conn=None) -> Any:
        """Return a client implementing ``search_albums`` for matching workflows."""

    @abstractmethod
    def run_oauth_login(self, **kwargs: object) -> dict[str, object]:
        """Run backend-specific auth flow (if supported)."""

    @abstractmethod
    def auth_diagnostics(self, *, conn=None, **kwargs: object) -> dict[str, object]:
        """Return backend-specific auth diagnostics safe for CLI/UI display."""

    @classmethod
    def provider_descriptor(cls) -> ProviderDescriptor:
        """Return additive provider capability metadata for readiness surfaces."""
        return {}
