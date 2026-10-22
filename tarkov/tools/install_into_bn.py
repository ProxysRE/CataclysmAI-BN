"""Install the engine fix, mod and optional tests into a pinned BN checkout."""
import argparse
import shutil
import subprocess
from pathlib import Path

PIN = "554950f3635f50ddd1d32c6e1b6e2bdee9842bd6"
ROOT = Path(__file__).resolve().parents[1]


def apply_engine_patch(bn: Path, patch: Path) -> None:
    # BN and this repository can have different checkout EOL rules on Windows.
    # Use bytes so subprocess stdin does not translate LF back to CRLF.
    data = patch.read_bytes().replace(b"\r\n", b"\n")
    for line in data.decode().splitlines():
        if not line.startswith("--- a/"):
            continue
        source = bn / line.removeprefix("--- a/")
        original = source.read_bytes()
        normalized = original.replace(b"\r\n", b"\n")
        if normalized != original:
            source.write_bytes(normalized)
    subprocess.run(["git", "-C", str(bn), "apply", "--check", "-"], input=data, check=True)
    subprocess.run(["git", "-C", str(bn), "apply", "-"], input=data, check=True)


def install(bn: Path, tests: bool) -> None:
    actual = subprocess.check_output(["git", "-C", str(bn), "rev-parse", "HEAD"], text=True).strip()
    if actual != PIN:
        raise SystemExit(f"Expected BN {PIN}; found {actual}. Refusing an unverified baseline.")
    dest = bn / "data/mods/trkv_raid_core"
    if dest.exists():
        raise SystemExit(f"Destination already exists: {dest}; refusing to overwrite it.")
    for patch in sorted((ROOT / "patches").glob("*.patch")):
        apply_engine_patch(bn, patch)
    shutil.copytree(ROOT / "mods/trkv_raid_core", dest)
    if tests:
        harness = bn / "tests/catalua_test.cpp"
        content = harness.read_text()
        if "TRKV_DEV01_TEST_BEGIN" in content:
            raise SystemExit("Test overlay is already installed")
        harness.write_text(content + "\n" + (ROOT / "tests/bn_harness.cpp.inc").read_text()
                           + "\n" + (ROOT / "tests/bn_cold_harness.cpp.inc").read_text()
                           + "\n" + (ROOT / "tests/bn_npc_harness.cpp.inc").read_text())
        shutil.copyfile(ROOT / "tests/bn_integration.lua", bn / "tests/lua/trkv_integration_test.lua")

        shutil.copyfile(ROOT / "tests/bn_npc_probe.lua", bn / "tests/lua/trkv_npc_probe.lua")

        shutil.copyfile(ROOT / "tests/npc_patrol_class.json",
                        bn / "data/mods/TEST_DATA/trkv_npc_patrol.json")

        # Test-only access to the production random-spawn entry point. Keep this
        # seam out of checkouts installed without --tests.
        header = bn / "src/game.h"
        source = header.read_text()
        anchor = "        friend class editmap;"
        if source.count(anchor) != 1:
            raise SystemExit("Pinned NPC spawn probe friend anchor changed")
        header.write_text(source.replace(anchor, anchor + "\n        friend struct trkv_npc_spawn_probe;", 1))

        # Preserve only explicitly requested test worlds in the test driver.
        driver = bn / "tests/test_main.cpp"
        source = driver.read_text()
        replacements = [
            ('const bool dont_save = check_remove_flags(arg_vec, {"-D", "--drop-world"});',
             'const bool dont_save = check_remove_flags(arg_vec, {"-D", "--drop-world"});\n'
             '    const bool trkv_keep_world = check_remove_flags(arg_vec, {"--trkv-keep-world"});'),
            ('    clear_all_state();\n\n    auto world_name = world_generator->active_world->info->world_name;',
             '    if (!trkv_keep_world) { clear_all_state(); }\n\n'
             '    auto world_name = world_generator->active_world->info->world_name;'),
            ('    if (result == 0 || dont_save) {',
             '    if (!trkv_keep_world && (result == 0 || dont_save)) {'),
        ]
        for before, after in replacements:
            if source.count(before) != 1:
                raise SystemExit("Pinned cold-restart driver anchor changed")
            source = source.replace(before, after)
        driver.write_text(source)
    print(f"Installed Tarkov DEV0.1 into {bn}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bn", type=Path)
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    install(args.bn.resolve(), args.tests)
