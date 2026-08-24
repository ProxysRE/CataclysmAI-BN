#!/usr/bin/env python3
"""Minimal external sidecar for Cataclysm: Bright Nights AI IPC.

For this integration stage the sidecar deliberately implements only an ECHO
provider.  It watches the same request/response files used by the C++ Lua
binding, reads one UTF-8 request, and publishes one UTF-8 response atomically.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REQUEST_FILE = "cataclysm_ai_request.txt"
RESPONSE_FILE = "cataclysm_ai_response.txt"
RESPONSE_TMP_FILE = "cataclysm_ai_response.txt.tmp"
MAX_EXCHANGE_BYTES = 1024 * 1024
POLL_INTERVAL_SECONDS = 0.025


def default_config_dir() -> Path:
    """Match Bright Nights' default config directory on supported desktop OSes."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set; pass --config-dir explicitly")
        return Path(local_app_data) / "cataclysm-bn" / "config"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "cataclysm-bn"
    return Path.home() / ".config" / "cataclysm-bn"


def read_request(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > MAX_EXCHANGE_BYTES:
        raise ValueError("request_too_large")
    return data.decode("utf-8")


def make_echo_response(request: str) -> str:
    return f"[ECHO] {request}"


def publish_response(config_dir: Path, response: str) -> None:
    encoded = response.encode("utf-8")
    if len(encoded) > MAX_EXCHANGE_BYTES:
        raise ValueError("response_too_large")

    tmp_path = config_dir / RESPONSE_TMP_FILE
    response_path = config_dir / RESPONSE_FILE
    tmp_path.write_bytes(encoded)
    os.replace(tmp_path, response_path)


def serve_once(config_dir: Path, timeout_seconds: float) -> int:
    config_dir.mkdir(parents=True, exist_ok=True)
    request_path = config_dir / REQUEST_FILE
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if request_path.is_file():
            try:
                request = read_request(request_path)
                response = make_echo_response(request)
                publish_response(config_dir, response)
            except (OSError, UnicodeError, ValueError) as exc:
                print(f"sidecar error: {exc}", file=sys.stderr)
                return 2

            print(f"request: {request}")
            print(f"response: {response}")
            return 0

        time.sleep(POLL_INTERVAL_SECONDS)

    print(f"sidecar timeout waiting for {request_path}", file=sys.stderr)
    return 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cataclysm AI file-IPC sidecar")
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Bright Nights config directory; defaults to the platform BN path",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="seconds to wait for a request in --once mode",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="handle exactly one request and exit (current integration-test mode)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_dir = args.config_dir if args.config_dir is not None else default_config_dir()

    if not args.once:
        print("continuous mode is intentionally deferred; use --once for this integration stage", file=sys.stderr)
        return 4

    return serve_once(config_dir.resolve(), args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
