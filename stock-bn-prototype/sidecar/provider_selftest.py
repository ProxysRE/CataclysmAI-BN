#!/usr/bin/env python3
"""Offline tests for the real model provider. No API request is made."""

from __future__ import annotations

import os
from types import SimpleNamespace

from memory import MemoryExchange, MemoryView
from providers import (
    DEFAULT_OPENAI_MODEL,
    MAX_PROMPT_HISTORY,
    MemoryProbeProvider,
    OpenAIProvider,
    build_openai_payload,
    create_provider,
    extract_openai_text,
)


def main() -> int:
    request = SimpleNamespace(
        npc_id="42",
        npc_name="Old Guard",
        player_name="Survivor",
        player_text="Ты помнишь, что я говорил?",
        current_turn="day 2",
        context_version=1,
        context={
            "npc": {
                "id": "42",
                "name": "Old Guard",
                "personality": {
                    "aggression": 2,
                    "bravery": 5,
                    "collector": 1,
                    "altruism": -2,
                },
                "opinion_of_player": {
                    "trust": 3,
                    "fear": -1,
                    "anger": 0,
                    "value": 2,
                    "owed": 0,
                },
                "relationship": {
                    "enemy": False,
                    "following": False,
                    "player_ally": False,
                },
                "state": {"pain": 0, "morale": 0},
            },
            "player": {"name": "Survivor", "state": {"pain": 0, "morale": 0}},
            "world": {"current_turn": "day 2", "npc_danger_assessment": 0.0},
        },
    )
    memory = MemoryView(
        npc_id="42",
        npc_name="Old Guard",
        exchanges=(
            MemoryExchange(
                request_id="42_1",
                turn="day 1",
                player_text="Запомни: мой любимый цвет — красный",
                npc_text="Ладно, запомню.",
            ),
            MemoryExchange(
                request_id="42_2",
                turn="day 1",
                player_text="Проверка памяти",
                npc_text="[MEM:Old Guard] previous_exchanges=1; last_player=...",
            ),
        ),
    )

    payload = build_openai_payload(request, memory, DEFAULT_OPENAI_MODEL)
    assert payload["model"] == DEFAULT_OPENAI_MODEL
    assert payload["store"] is False
    assert payload["reasoning"]["effort"] == "low"
    assert payload["max_output_tokens"] == 512
    assert "Запомни: мой любимый цвет — красный" in payload["input"]
    assert "Ладно, запомню." in payload["input"]
    assert "PLAYER: Проверка памяти" in payload["input"]
    assert "[MEM:Old Guard]" not in payload["input"]
    assert request.player_text in payload["input"]
    assert request.npc_name in payload["instructions"]

    long_memory = MemoryView(
        npc_id="42",
        npc_name="Old Guard",
        exchanges=tuple(
            MemoryExchange(
                request_id=f"42_{index}",
                turn=f"turn {index}",
                player_text=f"old-player-{index}",
                npc_text=f"old-npc-{index}",
            )
            for index in range(MAX_PROMPT_HISTORY + 3)
        ),
    )
    bounded = build_openai_payload(request, long_memory, DEFAULT_OPENAI_MODEL)["input"]
    assert "old-player-0" not in bounded
    assert "old-player-2" not in bounded
    assert "old-player-3" in bounded
    assert f"old-player-{MAX_PROMPT_HISTORY + 2}" in bounded

    raw_response = {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": "Красный. Я помню."}
                ],
            }
        ]
    }
    assert extract_openai_text(raw_response) == "Красный. Я помню."
    assert extract_openai_text({"output_text": "  Прямой ответ.  "}) == "Прямой ответ."

    no_key = OpenAIProvider(api_key="", model="gpt-test")
    missing = no_key.respond(request, memory)
    assert missing.error is not None
    assert "API key" in missing.error

    bridge_request = SimpleNamespace(
        npc_id="bridge_test",
        npc_name="Bridge Test",
        player_text="ping",
        context_version=0,
    )
    bridge = no_key.respond(bridge_request, memory)
    assert bridge.error is None
    assert bridge.text == "[ECHO:Bridge Test] ping"

    old_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ.pop("OPENAI_API_KEY", None)
        assert isinstance(create_provider("memory"), MemoryProbeProvider)
        os.environ["OPENAI_API_KEY"] = "unit-test-key"
        assert isinstance(create_provider("memory"), OpenAIProvider)
    finally:
        if old_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = old_key

    print("[CataclysmAI] provider self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
