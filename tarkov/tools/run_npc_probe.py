"""Run the isolated real-BN NPC probe on either Linux or Windows."""
import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from run_native_checks import validate_report


def run(bn: Path, executable: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    report, log = output / "tarkov-npc.xml", output / "tarkov-npc.log"
    report.unlink(missing_ok=True)
    env = os.environ.copy()
    # SDL's dummy video driver cannot initialize the Linux Vulkan compute backend.
    # Preserve explicit runner settings; use the previously verified offscreen backend.
    env.setdefault("SDL_VIDEODRIVER", "dummy" if os.name == "nt" else "offscreen")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    command = [str(executable), "--mods=trkv_raid_core", "[tarkov_npc]", "--rng-seed", "20261020",
               "--reporter", "junit", "--out", str(report)]
    try:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(command, cwd=bn, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, timeout=1800, check=True)
    except subprocess.CalledProcessError:
        # The JUnit reporter writes assertions to XML, not stdout. Surface them
        # on Windows too, while retaining the original failed process status.
        if report.exists():
            try:
                for failure in ET.parse(report).iter():
                    if failure.tag in ("failure", "error"):
                        print(ET.tostring(failure, encoding="unicode")[:16000], flush=True)
            except (ET.ParseError, OSError) as error:
                print("Could not read NPC failure report: " + str(error), flush=True)
        raise
    finally:
        print(log.read_text(encoding="utf-8", errors="replace")[-16000:], flush=True)
    # Legacy lifecycle plus seven independent pair cases. Catch continues after
    # a failed case, so one assertion cannot hide the other scenarios.
    validate_report(report, expected_cases=8)
    print("PASS native NPC probe: " + str(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bn", type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.bn.resolve(), args.executable.resolve(), args.output.resolve())
