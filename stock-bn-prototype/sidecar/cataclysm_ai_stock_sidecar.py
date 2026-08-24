#!/usr/bin/env python3
"""Stock-BN Cataclysm AI sidecar prototype.

No custom Cataclysm binary is required.

Outbound IPC:
    Lua writes structured CATAI_REQ lines through gdebug.log_info(), which land
    in config/debug.log. This process tails the log and parses new requests.

Inbound IPC:
    The sidecar atomically writes runtime/response_<request_id>.lua inside the
    CataclysmAI mod directory. Stock BN Lua reads the file with loadfile().

The prototype provider is deterministic ECHO only. Replace make_response() with
an LLM provider once the transport is proven in an official BN build.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

REQUEST_MARKER = "CATAI_REQ|"
ACK_MARKER = "CATAI_ACK|"
PROTOCOL_VERSION = "1"


@dataclass(frozen=True)
class Request:
    request_id: str
    npc_id: str
    npc_name: str
    player_name: str
    player_text: str
    current_turn: str


def log(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(f"[CataclysmAI] {message}", file=stream, flush=True)


def parse_request(line: str) -> Request | None:
    marker_at = line.find(REQUEST_MARKER)
    if marker_at < 0:
        return None

    wire = line[marker_at:].strip()
    parts = wire.split("|", 7)
    if len(parts) != 8:
        raise ValueError(f"malformed request field count: {wire!r}")

    marker, version, request_id, npc_id, npc_name, player_name, player_text, current_turn = parts
    if marker != "CATAI_REQ":
        return None
    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version {version!r}")
    if not request_id:
        raise ValueError("empty request_id")

    return Request(
        request_id=request_id,
        npc_id=npc_id,
        npc_name=unquote(npc_name),
        player_name=unquote(player_name),
        player_text=unquote(player_text),
        current_turn=unquote(current_turn),
    )


def parse_ack(line: str) -> str | None:
    marker_at = line.find(ACK_MARKER)
    if marker_at < 0:
        return None

    wire = line[marker_at:].strip()
    parts = wire.split("|", 2)
    if len(parts) != 3:
        return None
    marker, version, request_id = parts
    if marker != "CATAI_ACK" or version != PROTOCOL_VERSION:
        return None
    return request_id or None


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


def response_file(runtime_dir: Path, request_id: str) -> Path:
    safe = "".join(ch for ch in request_id if ch.isalnum() or ch in "_-.")
    if safe != request_id or not safe:
        raise ValueError(f"unsafe request_id {request_id!r}")
    return runtime_dir / f"response_{safe}.lua"


def publish_response(runtime_dir: Path, request_id: str, *, text: str = "", error: str | None = None) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    target = response_file(runtime_dir, request_id)
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


def make_response(request: Request) -> str:
    """Deterministic transport test. Replace with the real LLM provider later."""
    return f"[ECHO:{request.npc_name}] {request.player_text}"


def infer_debug_log(game_dir: Path) -> Path:
    candidates = [
        game_dir / "config" / "debug.log",
        game_dir / "debug.log",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def infer_mod_dir(game_dir: Path) -> Path:
    candidates = [
        game_dir / "mods" / "CataclysmAI",
        game_dir / "data" / "mods" / "CataclysmAI",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def follow_lines(path: Path, poll_seconds: float) -> Iterable[str]:
    """Follow a text log and tolerate creation, truncation, and replacement."""
    handle = None
    position = 0

    while True:
        if handle is None:
            try:
                handle = path.open("r", encoding="utf-8", errors="replace")
                handle.seek(0, os.SEEK_END)
                position = handle.tell()
                log(f"following {path} from byte {position}")
            except FileNotFoundError:
                time.sleep(poll_seconds)
                continue

        line = handle.readline()
        if line:
            position = handle.tell()
            yield line
            continue

        try:
            current_size = path.stat().st_size
        except FileNotFoundError:
            handle.close()
            handle = None
            time.sleep(poll_seconds)
            continue

        if current_size < position:
            handle.close()
            handle = None
            continue

        time.sleep(poll_seconds)


def run(debug_log: Path, runtime_dir: Path, poll_seconds: float, once: bool) -> int:
    seen: set[str] = set()

    log(f"debug log: {debug_log}")
    log(f"runtime dir: {runtime_dir}")
    log("provider: deterministic ECHO")

    for line in follow_lines(debug_log, poll_seconds):
        ack = parse_ack(line)
        if ack:
            try:
                path = response_file(runtime_dir, ack)
                path.unlink(missing_ok=True)
                log(f"ACK {ack}; removed {path.name}")
            except (OSError, ValueError) as exc:
                log(f"ACK cleanup failed for {ack}: {exc}", error=True)
            continue

        try:
            request = parse_request(line)
        except ValueError as exc:
            log(str(exc), error=True)
            continue

        if request is None or request.request_id in seen:
            continue
        seen.add(request.request_id)

        log(
            f"request {request.request_id}: npc={request.npc_name!r} "
            f"player={request.player_name!r} text={request.player_text!r}"
        )

        try:
            response = make_response(request)
            path = publish_response(runtime_dir, request.request_id, text=response)
            log(f"published {path}")
        except Exception as exc:  # keep the bridge alive and surface the failure to Lua
            log(f"request {request.request_id} failed: {type(exc).__name__}: {exc}", error=True)
            try:
                publish_response(runtime_dir, request.request_id, error=f"{type(exc).__name__}: {exc}")
            except Exception as publish_exc:
                log(f"could not publish error response: {publish_exc}", error=True)

        if once:
            return 0

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cataclysm AI bridge for an unmodified Bright Nights build")
    parser.add_argument("--game-dir", type=Path, help="Root directory of the unpacked Bright Nights build")
    parser.add_argument("--debug-log", type=Path, help="Explicit path to BN config/debug.log")
    parser.add_argument("--mod-dir", type=Path, help="Explicit CataclysmAI mod directory")
    parser.add_argument("--poll-ms", type=int, default=50, help="Log polling period in milliseconds")
    parser.add_argument("--once", action="store_true", help="Exit after the first request is answered")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    game_dir = args.game_dir.resolve() if args.game_dir else None
    if args.debug_log:
        debug_log = args.debug_log.resolve()
    elif game_dir:
        debug_log = infer_debug_log(game_dir)
    else:
        raise SystemExit("provide --game-dir or --debug-log")

    if args.mod_dir:
        mod_dir = args.mod_dir.resolve()
    elif game_dir:
        mod_dir = infer_mod_dir(game_dir)
    else:
        raise SystemExit("provide --game-dir or --mod-dir")

    if args.poll_ms < 10:
        raise SystemExit("--poll-ms must be at least 10")

    runtime_dir = mod_dir / "runtime"
    return run(debug_log, runtime_dir, args.poll_ms / 1000.0, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
