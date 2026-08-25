#!/usr/bin/env python3
"""Cataclysm AI companion for an unmodified Bright Nights build.

Outbound IPC is stock BN:
  Lua -> game.mod_storage -> gdebug.save_game() -> <world>/lua_state.json

Inbound IPC is stock BN:
  Python -> data/lua/lib/catai_runtime/response_<id>.lua -> Lua require()

Transport, persistent NPC memory, and response providers are separate layers.
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

from memory import MemoryStore
from providers import Provider, ProviderResponse, create_provider

MOD_ID = "cataclysm_ai"
PROTOCOL_VERSION = 1
CACHE_VERSION = 1
CACHE_FILENAME = "companion_cache.json"
MEMORY_FILENAME = "npc_memory.json"
CACHE_LIMIT = 256


@dataclass(frozen=True)
class Request:
    request_id: str
    npc_id: str
    npc_name: str
    player_name: str
    player_text: str
    current_turn: str
    context_version: int
    context: dict[str, Any]
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
        return None
    return value if isinstance(value, dict) else None


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def decode_bn_lua_object(value: Any) -> Any:
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

    try:
        context_version = int(raw.get("context_version", 0))
    except (TypeError, ValueError):
        context_version = 0
    raw_context = raw.get("context")
    context: dict[str, Any] = raw_context if isinstance(raw_context, dict) else {}

    return (
        Request(
            request_id=request_id,
            npc_id=str(raw.get("npc_id", "")),
            npc_name=str(raw.get("npc_name", "")),
            player_name=str(raw.get("player_name", "")),
            player_text=str(raw.get("player_text", "")),
            current_turn=str(raw.get("current_turn", "")),
            context_version=context_version,
            context=context,
            state_path=path,
        ),
        ack_id,
    )


def newest_world_state(save_root: Path) -> Path | None:
    candidates: list[tuple[int, Path]] = []
    try:
        for path in save_root.glob("*/lua_state.json"):
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


def cache_key(request: Request) -> str:
    try:
        state = str(request.state_path.resolve())
    except OSError:
        state = str(request.state_path)
    return f"{state}|{request.request_id}"


def load_response_cache(path: Path) -> dict[str, dict[str, Any]]:
    root = load_json(path)
    if root is None or root.get("version") != CACHE_VERSION:
        return {}
    entries = root.get("entries")
    if not isinstance(entries, dict):
        return {}

    cleaned: dict[str, dict[str, Any]] = {}
    for key, value in entries.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        request_id = value.get("request_id")
        text = value.get("text", "")
        error = value.get("error")
        if not isinstance(request_id, str) or not isinstance(text, str):
            continue
        # Provider/API errors are retryable and must never become sticky cached
        # responses. This also discards error entries written by older builds.
        if error is not None:
            continue
        cleaned[key] = {"request_id": request_id, "text": text, "error": None}
    return cleaned


def save_response_cache(path: Path, entries: dict[str, dict[str, Any]]) -> None:
    if len(entries) > CACHE_LIMIT:
        entries = dict(list(entries.items())[-CACHE_LIMIT:])
    write_json_atomic(path, {"version": CACHE_VERSION, "entries": entries})


def cached_result(
    cache: dict[str, dict[str, Any]], request: Request
) -> ProviderResponse | None:
    entry = cache.get(cache_key(request))
    if not entry or entry.get("request_id") != request.request_id:
        return None
    return ProviderResponse(text=str(entry.get("text", "")), error=None)


def remember_result(
    cache_path: Path,
    cache: dict[str, dict[str, Any]],
    request: Request,
    result: ProviderResponse,
) -> None:
    key = cache_key(request)
    if result.error is not None:
        # Do not cache API/config/network errors. A corrected configuration or a
        # later retry must be able to call the provider again.
        if cache.pop(key, None) is not None:
            save_response_cache(cache_path, cache)
        return

    cache.pop(key, None)
    cache[key] = {
        "request_id": request.request_id,
        "text": result.text,
        "error": None,
    }
    if len(cache) > CACHE_LIMIT:
        cache.pop(next(iter(cache)), None)
    save_response_cache(cache_path, cache)


def run(
    save_root: Path,
    response_dir: Path,
    poll_seconds: float,
    once: bool,
    provider: Provider,
    memory_store: MemoryStore,
) -> int:
    clear_stale_responses(response_dir)
    cache_path = response_dir / CACHE_FILENAME
    cache = load_response_cache(cache_path)
    # Rewrite once so error entries left by older builds are physically removed.
    if cache_path.exists():
        save_response_cache(cache_path, cache)
    seen: set[tuple[str, str]] = set()
    last_state: Path | None = None

    log(f"save root: {save_root}")
    log(f"response modules: {response_dir}")
    log(f"memory store: {memory_store.path}")
    log(f"provider: {provider.name}")
    if cache:
        log(f"loaded {len(cache)} cached response(s)")

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
            seen_key = (str(request.state_path), request.request_id)
            if seen_key not in seen:
                seen.add(seen_key)
                memory = memory_store.view(request)
                log(
                    f"request {request.request_id}: npc={request.npc_name!r} "
                    f"player={request.player_name!r} text={request.player_text!r} "
                    f"context_v={request.context_version} memory={memory.exchange_count}"
                )

                result = cached_result(cache, request)
                if result is not None:
                    log(f"replaying cached response for {request.request_id}")
                else:
                    try:
                        result = provider.respond(request, memory)
                        remember_result(cache_path, cache, request, result)
                    except Exception as exc:
                        log(
                            f"request {request.request_id} failed: "
                            f"{type(exc).__name__}: {exc}",
                            error=True,
                        )
                        result = ProviderResponse(error=f"{type(exc).__name__}: {exc}")

                # Do this for both fresh and cached successful results. If a crash
                # occurred after cache persistence but before memory persistence,
                # replay repairs memory without another provider/model call.
                if result.error is None and request.npc_id != "bridge_test":
                    try:
                        if memory_store.remember_exchange(request, result.text):
                            log(f"remembered exchange {request.request_id} for npc {request.npc_id}")
                    except Exception as exc:
                        log(f"could not persist NPC memory: {exc}", error=True)

                try:
                    path = publish_response(
                        response_dir,
                        request.request_id,
                        text=result.text,
                        error=result.error,
                    )
                    log(f"published {path}")
                except Exception as exc:
                    log(
                        f"could not publish response {request.request_id}: "
                        f"{type(exc).__name__}: {exc}",
                        error=True,
                    )

                if once:
                    return 0

        time.sleep(poll_seconds)


def bn_value(value: Any) -> dict[str, Any]:
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


def _test_context() -> dict[str, Any]:
    return {
        "npc": {
            "id": "42",
            "name": "Old Guard",
            "personality": {
                "aggression": 2,
                "bravery": 5,
                "collector": 1,
                "altruism": 4,
            },
            "opinion_of_player": {
                "trust": 3,
                "fear": 1,
                "value": 2,
                "anger": 0,
                "owed": 0,
            },
            "relationship": {
                "enemy": False,
                "following": True,
                "player_ally": True,
                "guarding": False,
                "patrolling": False,
                "travelling": False,
                "turned_hostile": False,
                "guaranteed_hostile": False,
            },
            "state": {
                "pain": 0,
                "perceived_pain": 0,
                "stamina": 1000,
                "stamina_max": 1000,
                "morale": 10,
                "hostile_anger_level": 20,
            },
        },
        "player": {
            "name": "Survivor",
            "state": {
                "pain": 4,
                "perceived_pain": 4,
                "stamina": 900,
                "stamina_max": 1000,
                "morale": 5,
            },
        },
        "world": {
            "current_turn": "day 1",
            "npc_danger_assessment": 0.25,
            "npc_current_target": "",
        },
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="catai-test-") as tmp:
        root = Path(tmp)
        save_root = root / "save"
        world = save_root / "Test World"
        response_dir = root / "data" / "lua" / "lib" / "catai_runtime"
        cache_path = response_dir / CACHE_FILENAME
        memory_path = root / "state" / MEMORY_FILENAME
        world.mkdir(parents=True)

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
                "context_version": 1,
                "context": _test_context(),
            },
        }
        state = {MOD_ID: bn_table(logical_mod_state)}
        state_path = world / "lua_state.json"
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

        decoded = decode_bn_lua_table(state[MOD_ID])
        assert decoded == logical_mod_state
        request, ack = request_from_state(state_path)
        assert ack is None and request is not None
        assert request.request_id == "42_7"
        assert request.context_version == 1
        assert request.context["npc"]["opinion_of_player"]["trust"] == 3
        assert request.context["npc"]["personality"]["bravery"] == 5
        assert request.context["player"]["state"]["pain"] == 4
        assert newest_world_state(save_root) == state_path

        memory_store = MemoryStore(memory_path)
        memory0 = memory_store.view(request)
        assert memory0.exchange_count == 0

        echo_result = create_provider("echo").respond(request, memory0)
        assert echo_result.error is None
        assert echo_result.text == "[ECHO:Old Guard] Hello | world\nagain"

        context_result = create_provider("context").respond(request, memory0)
        assert context_result.error is None
        assert context_result.text.startswith("[CTX:Old Guard] trust=3 fear=1 anger=0 value=2")
        assert "ally=true following=true enemy=false" in context_result.text

        memory_provider = create_provider("memory")
        first_result = memory_provider.respond(request, memory0)
        assert first_result.error is None
        assert "previous_exchanges=0; last_player=-" in first_result.text
        assert memory_store.remember_exchange(request, first_result.text)
        assert not memory_store.remember_exchange(request, first_result.text)

        request2 = Request(
            request_id="42_8",
            npc_id=request.npc_id,
            npc_name=request.npc_name,
            player_name=request.player_name,
            player_text="Do you remember me?",
            current_turn="day 2",
            context_version=request.context_version,
            context=request.context,
            state_path=request.state_path,
        )
        memory1 = memory_store.view(request2)
        assert memory1.exchange_count == 1
        assert memory1.last_exchange is not None
        assert memory1.last_exchange.player_text == "Hello | world\nagain"
        second_result = memory_provider.respond(request2, memory1)
        assert "previous_exchanges=1" in second_result.text
        assert "last_player=Hello | world again" in second_result.text
        assert memory_store.remember_exchange(request2, second_result.text)

        reloaded_memory = MemoryStore(memory_path).view(request2)
        assert reloaded_memory.exchange_count == 2
        assert reloaded_memory.last_exchange is not None
        assert reloaded_memory.last_exchange.player_text == "Do you remember me?"

        remember_result(cache_path, {}, request, context_result)
        replay = cached_result(load_response_cache(cache_path), request)
        assert replay == context_result

        # Errors must never survive in the idempotency cache. Verify both a fresh
        # failed result and a legacy on-disk error entry are ignored.
        error_cache: dict[str, dict[str, Any]] = {}
        remember_result(
            cache_path,
            error_cache,
            request2,
            ProviderResponse(error="temporary API failure"),
        )
        assert cached_result(error_cache, request2) is None
        legacy_key = cache_key(request2)
        write_json_atomic(
            cache_path,
            {
                "version": CACHE_VERSION,
                "entries": {
                    legacy_key: {
                        "request_id": request2.request_id,
                        "text": "",
                        "error": "HTTP 400",
                    }
                },
            },
        )
        assert load_response_cache(cache_path) == {}

        path = publish_response(
            response_dir,
            request.request_id,
            text=context_result.text,
            error=context_result.error,
        )
        payload = path.read_text(encoding="utf-8")
        assert 'request_id = "42_7"' in payload
        assert "[CTX:Old Guard]" in payload
        assert "Hello | world\\nagain" in payload

        logical_mod_state.pop("ipc_request", None)
        logical_mod_state["ipc_ack"] = "42_7"
        state = {MOD_ID: bn_table(logical_mod_state)}
        state_path.write_text(json.dumps(state), encoding="utf-8")
        old_request, ack = request_from_state(state_path)
        assert old_request is None
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
    parser.add_argument(
        "--state-dir",
        type=Path,
        help="Companion persistent state directory. Defaults to <user-dir>/cataclysm_ai.",
    )
    parser.add_argument(
        "--provider",
        default="memory",
        choices=("echo", "context", "memory"),
        help="Response provider. Persistent memory probe is the current pre-model milestone.",
    )
    parser.add_argument("--poll-ms", type=int, default=100, help="Polling period in milliseconds")
    parser.add_argument("--once", action="store_true", help="Exit after publishing one response")
    parser.add_argument("--self-test", action="store_true", help="Run transport/memory self-test and exit")
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

    if args.state_dir:
        state_dir = args.state_dir.resolve()
    elif user_dir:
        state_dir = user_dir / "cataclysm_ai"
    else:
        state_dir = save_root.parent / "cataclysm_ai"
    state_dir.mkdir(parents=True, exist_ok=True)

    try:
        provider = create_provider(args.provider)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    memory_store = MemoryStore(state_dir / MEMORY_FILENAME)
    return run(
        save_root,
        response_dir,
        args.poll_ms / 1000.0,
        args.once,
        provider,
        memory_store,
    )


if __name__ == "__main__":
    raise SystemExit(main())
