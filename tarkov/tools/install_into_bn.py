"""Install the mod and optional runtime test overlay into a pinned BN checkout."""
import argparse
import shutil
import subprocess
from pathlib import Path

PIN = "554950f3635f50ddd1d32c6e1b6e2bdee9842bd6"
ROOT = Path(__file__).resolve().parents[1]


def install(bn: Path, tests: bool) -> None:
    actual = subprocess.check_output(["git", "-C", str(bn), "rev-parse", "HEAD"], text=True).strip()
    if actual != PIN:
        raise SystemExit(f"Expected BN {PIN}; found {actual}. Refusing an unverified baseline.")
    dest = bn / "data/mods/trkv_raid_core"
    if dest.exists():
        raise SystemExit(f"Destination already exists: {dest}; refusing to overwrite it.")
    shutil.copytree(ROOT / "mods/trkv_raid_core", dest)
    if tests:
        harness = bn / "tests/catalua_test.cpp"
        content = harness.read_text()
        if "TRKV_DEV01_TEST_BEGIN" in content:
            raise SystemExit("Test overlay is already installed")
        harness.write_text(content + "\n" + (ROOT / "tests/bn_harness.cpp.inc").read_text())
        shutil.copyfile(ROOT / "tests/bn_integration.lua", bn / "tests/lua/trkv_integration_test.lua")
    print(f"Installed Tarkov DEV0.1 into {bn}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bn", type=Path)
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    install(args.bn.resolve(), args.tests)
