#!/usr/bin/env python3
"""Cataclysm AI v0.1 echo sidecar.

No third-party packages are required.
This version intentionally does NOT call a real LLM: it proves the complete
Bright Nights -> external process -> Bright Nights transport first.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import time

REQUEST_NAME = "cataclysm_ai_request.txt"
RESPONSE_NAME = "cataclysm_ai_response.txt"
RESPONSE_TMP_NAME = "cataclysm_ai_response.tmp"


def find_default_config_dir() -> Path:
    here = Path(__file__).resolve().parent
    for parent in (here, *here.parents):
        candidate = parent / "config"
        if candidate.is_dir():
            return candidate
    try:
        return here.parents[3] / "config"
    except IndexError:
        return here / "config"


def parse_request(raw: str) -> tuple[str, str]:
    npc_name = "NPC"
    player_text = ""
    for line in raw.splitlines():
        if line.startswith("NPC_NAME: "):
            npc_name = line[len("NPC_NAME: "):].strip() or "NPC"
            break
    marker = "PLAYER_TEXT:\n"
    if marker in raw:
        player_text = raw.split(marker, 1)[1].strip()
    return npc_name, player_text


def build_echo_response(raw: str) -> str:
    npc_name, player_text = parse_request(raw)
    if not player_text:
        return f"[ECHO] {npc_name}: получен пустой текст."
    return f"[ECHO] {npc_name} услышал: «{player_text}». Мост Bright Nights ↔ внешний процесс работает."


def serve(config_dir: Path, poll_interval: float = 0.05) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    request_path = config_dir / REQUEST_NAME
    response_path = config_dir / RESPONSE_NAME
    response_tmp = config_dir / RESPONSE_TMP_NAME

    for stale in (response_path, response_tmp):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass

    print("Cataclysm AI 0.1 — ECHO server")
    print(f"Config dir: {config_dir}")
    print("Ожидаю реплику из Bright Nights. Ctrl+C — выход.")

    while True:
        if not request_path.exists():
            time.sleep(poll_interval)
            continue
        try:
            raw = request_path.read_text(encoding="utf-8")
            request_path.unlink(missing_ok=True)
            response = build_echo_response(raw)
            response_tmp.write_text(response, encoding="utf-8")
            os.replace(response_tmp, response_path)
            npc_name, player_text = parse_request(raw)
            print(f"\nNPC: {npc_name}")
            print(f"PLAYER: {player_text}")
            print(f"RESPONSE: {response}")
        except Exception as exc:
            error = f"CATAI_ERROR: sidecar exception: {type(exc).__name__}: {exc}"
            try:
                response_tmp.write_text(error, encoding="utf-8")
                os.replace(response_tmp, response_path)
            except Exception:
                pass
            print(error)
            time.sleep(0.2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", type=Path, default=None)
    args = parser.parse_args()
    config_dir = (args.config_dir or find_default_config_dir()).resolve()
    try:
        serve(config_dir)
    except KeyboardInterrupt:
        print("\nCataclysm AI server stopped.")


if __name__ == "__main__":
    main()
