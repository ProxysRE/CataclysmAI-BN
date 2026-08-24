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


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


class ContextProbeProvider:
    """Deterministic provider that proves the dialogue context reached Python.

    This is intentionally not an AI model. It turns selected context fields back
    into NPC speech so a live game test can validate the schema before model
    prompts, memory, or structured actions depend on it.
    """

    name = "dialogue context probe"

    def respond(self, request: Any) -> ProviderResponse:
        # Keep the synthetic bridge test stable even when this provider is the
        # default. The transport-only SUCCESS assertion should remain useful.
        if request.npc_id == "bridge_test":
            return ProviderResponse(text=f"[ECHO:{request.npc_name}] {request.player_text}")

        if request.context_version != 1:
            return ProviderResponse(
                error=f"expected dialogue context version 1, got {request.context_version!r}"
            )

        context = _mapping(request.context)
        npc = _mapping(context.get("npc"))
        personality = _mapping(npc.get("personality"))
        opinion = _mapping(npc.get("opinion_of_player"))
        relationship = _mapping(npc.get("relationship"))
        npc_state = _mapping(npc.get("state"))
        player = _mapping(context.get("player"))
        player_state = _mapping(player.get("state"))
        world = _mapping(context.get("world"))

        required = (
            npc,
            personality,
            opinion,
            relationship,
            npc_state,
            player,
            player_state,
            world,
        )
        if any(not section for section in required):
            return ProviderResponse(error="dialogue context v1 is incomplete")

        text = (
            f"[CTX:{request.npc_name}] "
            f"trust={opinion.get('trust')} fear={opinion.get('fear')} "
            f"anger={opinion.get('anger')} value={opinion.get('value')}; "
            f"aggr={personality.get('aggression')} brave={personality.get('bravery')} "
            f"altruism={personality.get('altruism')}; "
            f"ally={_bool_text(relationship.get('player_ally'))} "
            f"following={_bool_text(relationship.get('following'))} "
            f"enemy={_bool_text(relationship.get('enemy'))}; "
            f"npc_pain={npc_state.get('pain')} "
            f"player_pain={player_state.get('pain')} "
            f"danger={world.get('npc_danger_assessment')} "
            f"target={world.get('npc_current_target') or '-'} | "
            f"{request.player_text}"
        )
        return ProviderResponse(text=text)


def create_provider(name: str) -> Provider:
    normalized = name.strip().lower()
    if normalized == "echo":
        return EchoProvider()
    if normalized in {"context", "context-probe"}:
        return ContextProbeProvider()
    raise ValueError(f"unknown provider {name!r}")
