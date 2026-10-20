"""Give pinned tracked BN inputs stable mtimes before restoring a Ninja build cache.

The cache key includes the BN pin, installer, native test overlay and workflow.
Lua/JSON are still freshly installed and executed on every run. Only use this in
an isolated CI checkout; this is not a general incremental-build command.
"""
import os
import subprocess
import sys
from pathlib import Path

from install_into_bn import PIN


def stabilize(bn: Path) -> None:
    actual = subprocess.check_output(["git", "-C", str(bn), "rev-parse", "HEAD"], text=True).strip()
    if actual != PIN:
        raise SystemExit(f"Expected pinned BN {PIN}; found {actual}")
    timestamp = int(subprocess.check_output(
        ["git", "-C", str(bn), "show", "-s", "--format=%ct", "HEAD"], text=True))
    paths = subprocess.check_output(["git", "-C", str(bn), "ls-files", "-z"])
    count = 0
    for relative in paths.split(b"\0"):
        if not relative:
            continue
        path = bn / os.fsdecode(relative)
        if path.is_file() and not path.is_symlink():
            os.utime(path, (timestamp, timestamp))
            count += 1
    print(f"Stabilized {count} tracked BN build inputs at pinned commit time")


if __name__ == "__main__":
    stabilize(Path(sys.argv[1]).resolve())
