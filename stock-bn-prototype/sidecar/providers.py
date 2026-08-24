"""Response providers for the stock Bright Nights companion.

The bridge transport is deliberately provider-agnostic. Providers receive the
validated request decoded from Bright Nights and return text (or a provider
error) without knowing anything about Lua modules, save files, or polling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResponse:
    text: str = ""
    error: str | None = None


class Provider(Protocol):
    name: str

    def respond(self, request: Any) -> ProviderResponse:
        """Generate one response for a validated Cataclysm AI request."""


class EchoProvider:
    """Deterministic provider used to validate the transport."""

    name = "deterministic ECHO"

    def respond(self, request: Any) -> ProviderResponse:
        return ProviderResponse(text=f"[ECHO:{request.npc_name}] {request.player_text}")


def create_provider(name: str) -> Provider:
    normalized = name.strip().lower()
    if normalized == "echo":
        return EchoProvider()
    raise ValueError(f"unknown provider {name!r}")
