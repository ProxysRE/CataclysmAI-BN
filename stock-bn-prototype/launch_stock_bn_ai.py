#!/usr/bin/env python3
"""Install and launch Cataclysm AI with an unmodified Bright Nights build.

The launcher keeps game data, user data, persistent companion state, and the
Python companion on explicit paths. A real OpenAI provider can be configured
once without putting the API key in the repository, mod files, command line, or
logs.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MOD_SOURCE = HERE / "mod" / "CataclysmAI"
SIDECAR = HERE / "sidecar" / "cataclysm_ai_stock_sidecar.py"
STATE_DIR_NAME = "cataclysm_ai"
CONFIG_FILENAME = "config.json"
CONFIG_VERSION = 1
DEFAULT_OPENAI_MODEL = "gpt-5.6-terra"


def log(message: str) -> None:
    print(f"[CataclysmAI launcher] {message}", flush=True)


def find_game_exe(root: Path) -> Path:
    direct = root / "cataclysm-bn-tiles.exe"
    if direct.is_file():
        return direct.resolve()

    matches = sorted(root.rglob("cataclysm-bn-tiles.exe"))
    if not matches:
        raise SystemExit(f"cataclysm-bn-tiles.exe was not found under {root}")
    if len(matches) > 1:
        raise SystemExit(
            "multiple cataclysm-bn-tiles.exe files were found; pass the exact game directory:\n"
            + "\n".join(f"  {path}" for path in matches)
        )
    return matches[0].resolve()


def install_mod(user_dir: Path) -> Path:
    if not MOD_SOURCE.is_dir():
        raise SystemExit(f"prototype mod source is missing: {MOD_SOURCE}")

    mods_dir = user_dir / "mods"
    destination = mods_dir / "CataclysmAI"
    mods_dir.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(MOD_SOURCE, destination)
    return destination


def ensure_runtime_dir(game_dir: Path) -> Path:
    response_dir = game_dir / "data" / "lua" / "lib" / "catai_runtime"
    response_dir.mkdir(parents=True, exist_ok=True)

    probe = response_dir / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise SystemExit(
            f"Cataclysm AI cannot write runtime responses under {response_dir}: {exc}\n"
            "Move the unpacked Bright Nights directory to a writable location."
        ) from exc
    return response_dir


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(value, dict) or value.get("version") != CONFIG_VERSION:
        return {}
    return value


def save_openai_config(path: Path, api_key: str, model: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "version": CONFIG_VERSION,
        "provider": "openai",
        "openai_api_key": api_key,
        "openai_model": model,
    }
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def resolve_openai_configuration(
    state_dir: Path,
    *,
    force_prompt: bool,
) -> tuple[str, str]:
    """Resolve API key/model without ever printing the key.

    OPENAI_API_KEY wins over the local config. The model can be overridden with
    CATAI_OPENAI_MODEL. If no key exists, an interactive normal launch offers a
    one-time hidden prompt; an empty answer keeps the deterministic memory probe.
    """
    config_path = state_dir / CONFIG_FILENAME
    config = load_config(config_path)

    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    saved_key = str(config.get("openai_api_key", "")).strip()
    api_key = env_key or saved_key

    env_model = os.environ.get("CATAI_OPENAI_MODEL", "").strip()
    saved_model = str(config.get("openai_model", "")).strip()
    model = env_model or saved_model or DEFAULT_OPENAI_MODEL

    if force_prompt or not api_key:
        if not sys.stdin.isatty():
            return api_key, model

        print()
        log("OpenAI API key is not configured for real NPC dialogue." if not api_key else "Replacing the saved OpenAI API key.")
        print("The key will be stored only in the local Cataclysm AI state directory.")
        print("Press Enter without a key to keep using the deterministic memory probe.")
        entered = getpass.getpass("OpenAI API key (hidden input): ").strip()
        if entered:
            api_key = entered
            save_openai_config(config_path, api_key, model)
            log(f"saved local OpenAI configuration: {config_path}")
        elif force_prompt and api_key:
            log("kept the existing OpenAI API key")

    return api_key, model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Cataclysm AI with an unmodified Bright Nights Windows build. "
            "Unknown arguments after '--' are forwarded to Bright Nights."
        )
    )
    parser.add_argument(
        "game_dir",
        type=Path,
        help="Directory containing cataclysm-bn-tiles.exe, or its unpacked archive root",
    )
    parser.add_argument(
        "--user-dir",
        type=Path,
        help="Explicit BN user-data directory. Defaults to the executable directory.",
    )
    parser.add_argument(
        "--install-only",
        action="store_true",
        help="Install/validate the mod and paths, but do not start BN or the companion",
    )
    parser.add_argument(
        "--configure-openai",
        action="store_true",
        help="Prompt for and replace the locally stored OpenAI API key before launch",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args, game_args = parser.parse_known_args()
    if game_args and game_args[0] == "--":
        game_args = game_args[1:]

    requested_root = args.game_dir.expanduser().resolve()
    if not requested_root.is_dir():
        raise SystemExit(f"game directory does not exist: {requested_root}")

    exe = find_game_exe(requested_root)
    game_dir = exe.parent.resolve()
    user_dir = args.user_dir.expanduser().resolve() if args.user_dir else game_dir
    user_dir.mkdir(parents=True, exist_ok=True)
    state_dir = user_dir / STATE_DIR_NAME
    state_dir.mkdir(parents=True, exist_ok=True)

    mod_dir = install_mod(user_dir)
    response_dir = ensure_runtime_dir(game_dir)

    log(f"stock executable: {exe}")
    log(f"base path: {game_dir}")
    log(f"user path: {user_dir}")
    log(f"installed mod: {mod_dir}")
    log(f"runtime responses: {response_dir}")
    log(f"persistent state: {state_dir}")

    if args.install_only:
        if game_args:
            log(f"ignoring forwarded BN arguments in --install-only mode: {game_args}")
        log("installation/path validation passed")
        return 0

    if not SIDECAR.is_file():
        raise SystemExit(f"companion script is missing: {SIDECAR}")

    api_key, model = resolve_openai_configuration(
        state_dir,
        force_prompt=args.configure_openai,
    )

    companion_env = os.environ.copy()
    if api_key:
        companion_env["OPENAI_API_KEY"] = api_key
        companion_env["CATAI_OPENAI_MODEL"] = model
        log(f"dialogue provider: OpenAI Responses API ({model})")
    else:
        companion_env.pop("OPENAI_API_KEY", None)
        log("dialogue provider: deterministic memory probe (no OpenAI API key configured)")

    companion_cmd = [
        sys.executable,
        str(SIDECAR),
        "--game-dir",
        str(game_dir),
        "--user-dir",
        str(user_dir),
    ]
    # Bright Nights' CLI parser requires option name and value as separate argv
    # entries. It does not accept --basepath=... or --userdir=....
    game_cmd = [
        str(exe),
        "--basepath",
        str(game_dir),
        "--userdir",
        str(user_dir),
        *game_args,
    ]

    log("starting Python companion")
    companion = subprocess.Popen(companion_cmd, cwd=HERE, env=companion_env)
    game = None
    try:
        # Fail before starting the game if Python cannot even initialize the sidecar.
        time.sleep(0.25)
        early_exit = companion.poll()
        if early_exit is not None:
            raise SystemExit(f"Cataclysm AI companion exited immediately with code {early_exit}")

        log("starting unmodified Bright Nights executable")
        game = subprocess.Popen(game_cmd, cwd=game_dir)

        while True:
            game_exit = game.poll()
            if game_exit is not None:
                return game_exit

            companion_exit = companion.poll()
            if companion_exit is not None:
                log(f"companion exited unexpectedly with code {companion_exit}; closing BN")
                game.terminate()
                try:
                    game.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    game.kill()
                return companion_exit if companion_exit != 0 else 1

            time.sleep(0.25)
    except KeyboardInterrupt:
        log("interrupted")
        if game is not None and game.poll() is None:
            game.terminate()
        return 130
    finally:
        if companion.poll() is None:
            companion.terminate()
            try:
                companion.wait(timeout=3)
            except subprocess.TimeoutExpired:
                companion.kill()


if __name__ == "__main__":
    raise SystemExit(main())
