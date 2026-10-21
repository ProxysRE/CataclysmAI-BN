"""Run the first-layer BN lifecycle and three-process persistence checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from run_cold_restart import run as run_cold

ROOT = Path(__file__).resolve().parents[1]


def validate_report(path: Path) -> None:
    document = ET.parse(path)
    if len(document.findall(".//testcase")) != 1:
        raise RuntimeError(f"Expected exactly one executed BN testcase: {path}")
    if any(document.findall(".//" + tag) for tag in ("failure", "error", "skipped")):
        raise RuntimeError(f"BN testcase failed or was skipped: {path}")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(bn: Path, executable: Path, game: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    receipt = output / "native-checks.json"
    receipt.unlink(missing_ok=True)
    if not executable.is_file() or not game.is_file():
        raise FileNotFoundError("Build the game and native test executable before running checks")
    report, log = output / "tarkov-runtime.xml", output / "tarkov-runtime.log"
    report.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    command = [str(executable), "--mods=trkv_raid_core", "[tarkov]", "--rng-seed", "20261020",
               "--reporter", "junit", "--out", str(report)]
    try:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(command, cwd=bn, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, timeout=900, check=True)
    finally:
        print(log.read_text(encoding="utf-8", errors="replace")[-16000:], flush=True)
    validate_report(report)
    # Each reader runs in a new OS process against a closed copy of the prior world.
    previous = {key: os.environ.get(key) for key in ("SDL_VIDEODRIVER", "SDL_AUDIODRIVER")}
    try:
        os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
        run_cold(bn, output, executable)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    reports = [report, *(output / f"tarkov-cold-{stage}.xml" for stage in ("write", "active", "cleanup"))]
    for path in reports:
        validate_report(path)
    metadata = {
        "schema": 1, "passed": True, "platform": os.name,
        "bn_sha": subprocess.check_output(["git", "-C", str(bn), "rev-parse", "HEAD"], text=True).strip(),
        "project_sha": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "game_sha256": digest(game), "test_executable_sha256": digest(executable),
        "reports": {path.name: digest(path) for path in reports},
        "ui_automated": False,
    }
    receipt.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("PASS native lifecycle and full process restart; receipt: " + str(receipt), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bn", type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--game-executable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.bn.resolve(), args.executable.resolve(), args.game_executable.resolve(), args.output.resolve())
