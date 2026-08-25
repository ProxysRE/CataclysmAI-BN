"""Persistent per-world, per-NPC dialogue memory for Cataclysm AI.

The memory layer is intentionally independent of providers and transport.
It stores only validated dialogue exchanges keyed by the persistent world save
path plus the stable Bright Nights npc_id. Entries are bounded and written
atomically so a crash cannot corrupt the whole store.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MEMORY_VERSION = 1
MAX_EXCHANGES_PER_NPC = 32


@dataclass(frozen=True)
class MemoryExchange:
    request_id: str
    turn: str
    player_text: str
    npc_text: str


@dataclass(frozen=True)
class MemoryView:
    npc_id: str
    npc_name: str
    exchanges: tuple[MemoryExchange, ...]

    @property
    def exchange_count(self) -> int:
        return len(self.exchanges)

    @property
    def last_exchange(self) -> MemoryExchange | None:
        return self.exchanges[-1] if self.exchanges else None


def _world_key(state_path: Path) -> str:
    try:
        return str(state_path.resolve())
    except OSError:
        return str(state_path)


def _npc_key(request: Any) -> str:
    return f"{_world_key(request.state_path)}|npc:{request.npc_id}"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._npcs = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        root = _load_json(self.path)
        if root is None or root.get("version") != MEMORY_VERSION:
            return {}
        npcs = root.get("npcs")
        if not isinstance(npcs, dict):
            return {}

        cleaned: dict[str, dict[str, Any]] = {}
        for key, record in npcs.items():
            if not isinstance(key, str) or not isinstance(record, dict):
                continue
            npc_id = record.get("npc_id")
            npc_name = record.get("npc_name")
            history = record.get("history")
            if not isinstance(npc_id, str) or not isinstance(npc_name, str):
                continue
            if not isinstance(history, list):
                history = []

            valid_history: list[dict[str, str]] = []
            seen_ids: set[str] = set()
            for item in history[-MAX_EXCHANGES_PER_NPC:]:
                if not isinstance(item, dict):
                    continue
                request_id = item.get("request_id")
                turn = item.get("turn", "")
                player_text = item.get("player_text", "")
                npc_text = item.get("npc_text", "")
                if not all(isinstance(v, str) for v in (request_id, turn, player_text, npc_text)):
                    continue
                if not request_id or request_id in seen_ids:
                    continue
                seen_ids.add(request_id)
                valid_history.append(
                    {
                        "request_id": request_id,
                        "turn": turn,
                        "player_text": player_text,
                        "npc_text": npc_text,
                    }
                )

            cleaned[key] = {
                "npc_id": npc_id,
                "npc_name": npc_name,
                "history": valid_history,
            }
        return cleaned

    def _save(self) -> None:
        _write_json_atomic(
            self.path,
            {
                "version": MEMORY_VERSION,
                "npcs": self._npcs,
            },
        )

    def view(self, request: Any) -> MemoryView:
        record = self._npcs.get(_npc_key(request), {})
        history = record.get("history", []) if isinstance(record, dict) else []
        exchanges: list[MemoryExchange] = []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                exchanges.append(
                    MemoryExchange(
                        request_id=str(item.get("request_id", "")),
                        turn=str(item.get("turn", "")),
                        player_text=str(item.get("player_text", "")),
                        npc_text=str(item.get("npc_text", "")),
                    )
                )
        return MemoryView(
            npc_id=request.npc_id,
            npc_name=request.npc_name,
            exchanges=tuple(exchanges),
        )

    def remember_exchange(self, request: Any, npc_text: str) -> bool:
        """Store one successful dialogue exchange. Returns True when appended."""
        key = _npc_key(request)
        record = self._npcs.get(key)
        if not isinstance(record, dict):
            record = {
                "npc_id": request.npc_id,
                "npc_name": request.npc_name,
                "history": [],
            }
            self._npcs[key] = record

        record["npc_id"] = request.npc_id
        record["npc_name"] = request.npc_name
        history = record.get("history")
        if not isinstance(history, list):
            history = []
            record["history"] = history

        for item in history:
            if isinstance(item, dict) and item.get("request_id") == request.request_id:
                return False

        history.append(
            {
                "request_id": request.request_id,
                "turn": request.current_turn,
                "player_text": request.player_text,
                "npc_text": npc_text,
            }
        )
        if len(history) > MAX_EXCHANGES_PER_NPC:
            del history[:-MAX_EXCHANGES_PER_NPC]
        self._save()
        return True
