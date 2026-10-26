"""Run the isolated real-BN NPC probe on either Linux or Windows."""
import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from run_native_checks import validate_report


def run_case(bn: Path, executable: Path, output: Path, tag: str = "[tarkov_npc_legacy]", suffix: str = "") -> None:
    output.mkdir(parents=True, exist_ok=True)
    report, log = output / f"tarkov-npc{suffix}.xml", output / f"tarkov-npc{suffix}.log"
    report.unlink(missing_ok=True)
    env = os.environ.copy()
    # SDL's dummy video driver cannot initialize the Linux Vulkan compute backend.
    # Preserve explicit runner settings; use the previously verified offscreen backend.
    env.setdefault("SDL_VIDEODRIVER", "dummy" if os.name == "nt" else "offscreen")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    command = [str(executable), "--mods=trkv_raid_core", tag, "--rng-seed", "20261020",
               "--reporter", "junit", "--out", str(report)]
    try:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(command, cwd=bn, env=env, stdout=stream,
                           stderr=subprocess.STDOUT, timeout=900, check=True)
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
    validate_report(report)
    print("PASS native NPC probe: " + str(report), flush=True)


CASES = (("[tarkov_npc_legacy]", ""),) + tuple(
    (f"[tarkov_pair_{mode}]", "-" + mode)
    for mode in ("maneuver", "target_hidden", "buddy_hidden", "expired", "reload", "reload_reverse", "hazard")
)


def run(bn: Path, executable: Path, output: Path) -> None:
    # BN's Lua mod storage survives clear_all_state between Catch testcases.
    # Separate processes isolate scenarios; compilation still happens only once.
    # Remove ALL prior reports before starting, including not-yet-executed cases.
    output.mkdir(parents=True, exist_ok=True)
    for _, suffix in CASES:
        (output / f"tarkov-npc{suffix}.xml").unlink(missing_ok=True)
    failures = []
    for tag, suffix in CASES:
        try:
            run_case(bn, executable, output, tag, suffix)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, RuntimeError, ET.ParseError) as error:
            failures.append((tag, error))
            print(f"FAIL native NPC scenario {tag}: {error}", flush=True)
    if failures:
        names = ", ".join(tag for tag, _ in failures)
        raise RuntimeError(f"NPC scenarios failed ({len(failures)}/{len(CASES)}): {names}") from failures[0][1]
    print(f"PASS all {len(CASES)} isolated NPC scenarios", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bn", type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.bn.resolve(), args.executable.resolve(), args.output.resolve())
