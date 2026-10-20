"""Run three separate BN processes over closed copies of a disposable test world."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def run(bn: Path, output: Path) -> None:
    executable = bn / "build/bin/cata_test"
    with tempfile.TemporaryDirectory(prefix="trkv-cold-", dir=output) as scratch:
        root = Path(scratch).resolve()
        source = None
        phases = [
            ("write", "[tarkov_cold_write]", None, True),
            ("active", "[tarkov_cold_read]", "cold_read_active", True),
            ("cleanup", "[tarkov_cold_read]", "cold_read_cleanup", False),
        ]
        for name, tag, stage, keep in phases:
            manifest = root / (name + ".world")
            report = output / ("tarkov-cold-" + name + ".xml")
            log = output / ("tarkov-cold-" + name + ".log")
            env = os.environ.copy()
            for key in ("TRKV_COLD_SOURCE", "TRKV_COLD_STAGE", "TRKV_COLD_MANIFEST"):
                env.pop(key, None)
            env["TRKV_COLD_MANIFEST"] = str(manifest)
            if source is not None:
                env["TRKV_COLD_SOURCE"] = str(source)
                env["TRKV_COLD_STAGE"] = stage
            command = [str(executable), "--mods=trkv_raid_core", tag,
                       "--user-dir=" + str(root / name), "--rng-seed", "20261020",
                       "--reporter", "junit", "--out", str(report)]
            if keep:
                command.append("--trkv-keep-world")
            print("Tarkov cold process: " + name, flush=True)
            try:
                with log.open("w") as stream:
                    subprocess.run(command, cwd=bn, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, timeout=900, check=True)
            finally:
                if log.exists():
                    print(log.read_text(errors="replace")[-16000:], flush=True)
            document = ET.parse(report)
            if len(document.findall(".//testcase")) != 1:
                raise RuntimeError("Expected exactly one cold testcase: " + name)
            if document.findall(".//failure") or document.findall(".//error"):
                raise RuntimeError("Cold testcase failed: " + name)
            if keep:
                source = Path(manifest.read_text().strip()).resolve()
                if not source.is_relative_to(root) or not source.is_dir():
                    raise RuntimeError("Exported world is not a disposable fixture")
        print("PASS cold active load, cold cleanup replay, stash, equipment and next raid", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bn", type=Path)
    args = parser.parse_args()
    run(args.bn.resolve(), args.bn.resolve().parent)
