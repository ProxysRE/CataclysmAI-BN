"""Run the isolated real-BN NPC probe on either Linux or Windows."""
import argparse
import os
from pathlib import Path
import subprocess

from run_native_checks import validate_report


def run(bn: Path, executable: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    report, log = output / "tarkov-npc.xml", output / "tarkov-npc.log"
    report.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    command = [str(executable), "--mods=trkv_raid_core", "[tarkov_npc]", "--rng-seed", "20261020",
               "--reporter", "junit", "--out", str(report)]
    try:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(command, cwd=bn, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, timeout=900, check=True)
    finally:
        print(log.read_text(encoding="utf-8", errors="replace")[-16000:], flush=True)
    validate_report(report)
    print("PASS native NPC probe: " + str(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bn", type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.bn.resolve(), args.executable.resolve(), args.output.resolve())
