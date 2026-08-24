"""Response providers for the stock Bright Nights companion.

The bridge transport is deliberately provider-agnostic. Providers receive the
validated Bright Nights request plus a read-only per-NPC memory view and return
text (or a provider error) without knowing about Lua modules, save polling, or
memory persistence details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from memory import MemoryView


@dataclass(frozen=True)
class ProviderResponse:
    text: str = ""
    error: str | None = None


class Provider(Protocol):
    name: str

    def respond(self, request: Any, memory: MemoryView) -> ProviderResponse:
        """Generate one response for a validated Cataclysm AI request."""


class EchoProvider:
    """Deterministic provider used to validate the transport."""

    name = "deterministic ECHO"

    def respond(self, request: Any, memory: MemoryView) -> ProviderResponse:
        del memory
        return ProviderResponse(text=f"[ECHO:{request.npc_name}] {request.player_text}")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


class ContextProbeProvider:
    """Deterministic provider that proves dialogue context reached Python."""

    name = "dialogue context probe"

    def respond(self, request: Any, memory: MemoryView) -> ProviderResponse:
        del memory
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


class MemoryProbeProvider:
    """Proves that the same NPC receives dialogue history across requests/restarts."""

    name = "persistent NPC memory probe"

    def respond(self, request: Any, memory: MemoryView) -> ProviderResponse:
        if request.npc_id == "bridge_test":
            return ProviderResponse(text=f"[ECHO:{request.npc_name}] {request.player_text}")

        last = memory.last_exchange
        if last is None:
            previous = "-"
        else:
            previous = last.player_text.replace("\r", " ").replace("\n", " ")
            if len(previous) > 120:
                previous = previous[:117] + "..."

        return ProviderResponse(
            text=(
                f"[MEM:{request.npc_name}] previous_exchanges={memory.exchange_count}; "
                f"last_player={previous} | {request.player_text}"
            )
        )


def create_provider(name: str) -> Provider:
    normalized = name.strip().lower()
    if normalized == "echo":
        return EchoProvider()
    if normalized in {"context", "context-probe"}:
        return ContextProbeProvider()
    if normalized in {"memory", "memory-probe"}:
        return MemoryProbeProvider()
    raise ValueError(f"unknown provider {name!r}")
