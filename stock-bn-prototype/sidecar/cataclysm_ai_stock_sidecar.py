#!/usr/bin/env python3
"""Cataclysm AI companion prototype for an unmodified Bright Nights build.

Outbound IPC is entirely stock BN:
  Lua -> game.mod_storage -> gdebug.save_game() -> <world>/lua_state.json

Inbound IPC is also stock BN:
  Python -> data/lua/lib/catai_runtime/response_<id>.lua -> Lua require()

The current provider is deterministic ECHO. The transport is intentionally
proven before any real LLM provider is added.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MOD_ID = "cataclysm_ai"
PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class Request:
    request_id: str
    npc_id: str
    npc_name: str
    player_name: str
    player_text: str
    current_turn: str
    state_path: Path


def log(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(f"[CataclysmAI] {message}", file=stream, flush=True)


def safe_request_id(value: str) -> str:
    safe = "".join(ch for ch in value if ch.isalnum() or ch in "_-.")
    if not safe or safe != value:
        raise ValueError(f"unsafe request_id {value!r}")
    return safe


def lua_string(value: str) -> str:
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\a": "\\a",
        "\b": "\\b",
        "\f": "\\f",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\v": "\\v",
    }
    return '"' + "".join(replacements.get(ch, ch) for ch in value) + '"'


def response_file(response_dir: Path, request_id: str) -> Path:
    return response_dir / f"response_{safe_request_id(request_id)}.lua"


def publish_response(
    response_dir: Path,
    request_id: str,
    *,
    text: str = "",
    error: str | None = None,
) -> Path:
    response_dir.mkdir(parents=True, exist_ok=True)
    target = response_file(response_dir, request_id)
    temp = target.with_suffix(target.suffix + ".tmp")

    if error is None:
        payload = (
            "return { protocol = 1, request_id = "
            + lua_string(request_id)
            + ", ok = true, text = "
            + lua_string(text)
            + " }\n"
        )
    else:
        payload = (
            "return { protocol = 1, request_id = "
            + lua_string(request_id)
            + ", ok = false, error = "
            + lua_string(error)
            + " }\n"
        )

    temp.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temp, target)
    return target


def clear_stale_responses(response_dir: Path) -> None:
    response_dir.mkdir(parents=True, exist_ok=True)
    removed = 0
    for pattern in ("response_*.lua", "response_*.lua.tmp"):
        for path in response_dir.glob(pattern):
            try:
                path.unlink()
                removed += 1
            except FileNotFoundError:
                pass
    if removed:
        log(f"removed {removed} stale response file(s)")


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError, OSError):
        # Normal while BN is atomically replacing or still writing a save.
        return None
    return value if isinstance(value, dict) else None


def decode_bn_lua_object(value: Any) -> Any:
    """Decode one object produced by BN's serialize_lua_object().

    Bright Nights does not write Lua tables to lua_state.json as ordinary JSON
    objects. Each Lua key/value is tagged, e.g. {"type":"string","data":"x"},
    and nested tables use {"type":"lua_table","data":{"entries":[...]}}.
    """
    if not isinstance(value, dict):
        raise ValueError(f"invalid BN Lua value: expected object, got {type(value).__name__}")

    value_type = value.get("type")
    data = value.get("data")

    if value_type == "string":
        return str(data if data is not None else "")
    if value_type == "int":
        return int(data)
    if value_type == "float":
        return float(data)
    if value_type == "bool":
        return bool(data)
    if value_type == "lua_table":
        return decode_bn_lua_table(data)

    raise ValueError(f"unsupported BN Lua serialized type: {value_type!r}")


def decode_bn_lua_table(value: Any) -> dict[Any, Any]:
    """Decode BN's serialize_lua_table() representation into a Python dict."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"invalid BN Lua table: expected object, got {type(value).__name__}")

    entries = value.get("entries", [])
    if entries is None:
        return {}
    if not isinstance(entries, list):
        raise ValueError("invalid BN Lua table: entries is not an array")
    if len(entries) % 2 != 0:
        raise ValueError("invalid BN Lua table: entries must contain key/value pairs")

    decoded: dict[Any, Any] = {}
    for index in range(0, len(entries), 2):
        key = decode_bn_lua_object(entries[index])
        item = decode_bn_lua_object(entries[index + 1])
        try:
            decoded[key] = item
        except TypeError as exc:
            raise ValueError(f"unsupported non-hashable BN Lua table key: {key!r}") from exc
    return decoded


def request_from_state(path: Path) -> tuple[Request | None, str | None]:
    root = load_json(path)
    if root is None:
        return None, None

    serialized_mod_state = root.get(MOD_ID)
    if not isinstance(serialized_mod_state, dict):
        return None, None

    try:
        # save_world_lua_state() calls serialize_lua_table() directly for each
        # mod, so the top-level mod value is the table body ({entries:[...]}),
        # not a {type:"lua_table", data:...} wrapper.
        mod_state = decode_bn_lua_table(serialized_mod_state)
    except ValueError as exc:
        raise ValueError(f"could not decode {MOD_ID} state in {path}: {exc}") from exc

    ack = mod_state.get("ipc_ack")
    ack_id = str(ack) if ack is not None else None

    raw = mod_state.get("ipc_request")
    if not isinstance(raw, dict):
        return None, ack_id

    try:
        protocol = int(raw.get("protocol", -1))
    except (TypeError, ValueError):
        protocol = -1
    if protocol != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol in {path}: {protocol!r}")

    request_id = safe_request_id(str(raw.get("request_id", "")))
    if ack_id == request_id:
        return None, ack_id

    return (
        Request(
            request_id=request_id,
            npc_id=str(raw.get("npc_id", "")),
            npc_name=str(raw.get("npc_name", "")),
            player_name=str(raw.get("player_name", "")),
            player_text=str(raw.get("player_text", "")),
            current_turn=str(raw.get("current_turn", "")),
            state_path=path,
        ),
        ack_id,
    )


def newest_world_state(save_root: Path) -> Path | None:
    candidates: list[tuple[int, Path]] = []
    try:
        paths = save_root.glob("*/lua_state.json")
        for path in paths:
            try:
                candidates.append((path.stat().st_mtime_ns, path))
            except FileNotFoundError:
                pass
    except OSError:
        return None

    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1]


def make_response(request: Request) -> str:
    """Deterministic transport test. Replace with a real provider later."""
    return f"[ECHO:{request.npc_name}] {request.player_text}"


def run(save_root: Path, response_dir: Path, poll_seconds: float, once: bool) -> int:
    clear_stale_responses(response_dir)
    seen: set[tuple[str, str]] = set()
    last_state: Path | None = None

    log(f"save root: {save_root}")
    log(f"response modules: {response_dir}")
    log("provider: deterministic ECHO")

    while True:
        state_path = newest_world_state(save_root)
        if state_path is None:
            time.sleep(poll_seconds)
            continue

        if state_path != last_state:
            log(f"watching world state: {state_path}")
            last_state = state_path

        try:
            request, ack_id = request_from_state(state_path)
        except ValueError as exc:
            log(str(exc), error=True)
            time.sleep(poll_seconds)
            continue

        if ack_id:
            try:
                response_file(response_dir, ack_id).unlink(missing_ok=True)
            except (OSError, ValueError):
                pass

        if request is not None:
            key = (str(request.state_path), request.request_id)
            if key not in seen:
                seen.add(key)
                log(
                    f"request {request.request_id}: npc={request.npc_name!r} "
                    f"player={request.player_name!r} text={request.player_text!r}"
                )
                try:
                    response = make_response(request)
                    path = publish_response(response_dir, request.request_id, text=response)
                    log(f"published {path}")
                except Exception as exc:
                    log(
                        f"request {request.request_id} failed: "
                        f"{type(exc).__name__}: {exc}",
                        error=True,
                    )
                    try:
                        publish_response(
                            response_dir,
                            request.request_id,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    except Exception as publish_exc:
                        log(f"could not publish error response: {publish_exc}", error=True)

                if once:
                    return 0

        time.sleep(poll_seconds)


def bn_value(value: Any) -> dict[str, Any]:
    """Test-only encoder matching the subset of BN serialization we consume."""
    if isinstance(value, bool):
        return {"type": "bool", "data": value}
    if isinstance(value, int):
        return {"type": "int", "data": value}
    if isinstance(value, float):
        return {"type": "float", "data": value}
    if isinstance(value, str):
        return {"type": "string", "data": value}
    if isinstance(value, dict):
        return {"type": "lua_table", "data": bn_table(value)}
    raise TypeError(f"unsupported test value: {type(value).__name__}")


def bn_table(value: dict[Any, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for key, item in value.items():
        entries.append(bn_value(key))
        entries.append(bn_value(item))
    return {"entries": entries} if entries else {}


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="catai-test-") as tmp:
        root = Path(tmp)
        save_root = root / "save"
        world = save_root / "Test World"
        response_dir = root / "data" / "lua" / "lib" / "catai_runtime"
        world.mkdir(parents=True)

        # Match Bright Nights' real save_world_lua_state()/serialize_lua_table()
        # representation rather than a convenient ordinary-JSON approximation.
        logical_mod_state = {
            "request_seq": 7,
            "ipc_request": {
                "protocol": 1,
                "request_id": "42_7",
                "npc_id": "42",
                "npc_name": "Old Guard",
                "player_name": "Survivor",
                "player_text": "Hello | world\nagain",
                "current_turn": "day 1",
            },
        }
        state = {MOD_ID: bn_table(logical_mod_state)}
        state_path = world / "lua_state.json"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

        decoded = decode_bn_lua_table(state[MOD_ID])
        assert decoded == logical_mod_state

        request, ack = request_from_state(state_path)
        assert ack is None
        assert request is not None
        assert request.request_id == "42_7"
        assert request.player_text == "Hello | world\nagain"
        assert newest_world_state(save_root) == state_path

        response = make_response(request)
        path = publish_response(response_dir, request.request_id, text=response)
        payload = path.read_text(encoding="utf-8")
        assert 'request_id = "42_7"' in payload
        assert 'text = "[ECHO:Old Guard] Hello | world\\nagain"' in payload

        # Lua assignment to nil removes the key entirely; model the persisted
        # ACK exactly as acknowledge_response() does in the game.
        logical_mod_state.pop("ipc_request", None)
        logical_mod_state["ipc_ack"] = "42_7"
        state = {MOD_ID: bn_table(logical_mod_state)}
        state_path.write_text(json.dumps(state), encoding="utf-8")
        request, ack = request_from_state(state_path)
        assert request is None
        assert ack == "42_7"

    log("self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cataclysm AI companion for an unmodified Bright Nights build"
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        help="Root directory of the unpacked Bright Nights build",
    )
    parser.add_argument(
        "--user-dir",
        type=Path,
        help="BN user directory. Defaults to --game-dir for portable Windows builds.",
    )
    parser.add_argument(
        "--save-root",
        type=Path,
        help="Explicit save directory containing world folders",
    )
    parser.add_argument(
        "--response-dir",
        type=Path,
        help="Explicit data/lua/lib/catai_runtime directory",
    )
    parser.add_argument("--poll-ms", type=int, default=100, help="Polling period in milliseconds")
    parser.add_argument("--once", action="store_true", help="Exit after publishing one response")
    parser.add_argument("--self-test", action="store_true", help="Run transport self-test and exit")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.self_test:
        return self_test()

    if args.poll_ms < 25:
        raise SystemExit("--poll-ms must be at least 25")

    game_dir = args.game_dir.resolve() if args.game_dir else None
    user_dir = args.user_dir.resolve() if args.user_dir else game_dir

    if args.save_root:
        save_root = args.save_root.resolve()
    elif user_dir:
        save_root = user_dir / "save"
    else:
        raise SystemExit("provide --game-dir, --user-dir, or --save-root")

    if args.response_dir:
        response_dir = args.response_dir.resolve()
    elif game_dir:
        response_dir = game_dir / "data" / "lua" / "lib" / "catai_runtime"
    else:
        raise SystemExit("provide --game-dir or --response-dir")

    return run(save_root, response_dir, args.poll_ms / 1000.0, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
