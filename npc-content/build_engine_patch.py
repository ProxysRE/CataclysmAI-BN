#!/usr/bin/env python3
"""Rebuild the native patch against the pinned, unmodified BN files."""
import argparse
import difflib
import hashlib
import re
import subprocess
from pathlib import Path
from merge_existing_locations import prepare as prepare_existing_locations

root = Path(__file__).resolve().parent
base_files = ("condition.cpp", "npctalk.cpp", "faction.h", "faction.cpp",
              "savegame_json.cpp", "activity_type.h", "activity_type.cpp", "player_activity.cpp",
              "npc.cpp", "npc_class.cpp", "npc_class.h", "game.h", "game.cpp", "savegame.cpp")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bn-source", type=Path,
                    help="Pinned BN checkout; restore staging before rebuilding")
args = parser.parse_args()
prepare_existing_locations()
if args.bn_source:
    actual = subprocess.check_output(["git", "-C", str(args.bn_source), "rev-parse", "HEAD"], text=True).strip()
    if actual != "c621aaf42fa182473aad10feea2b55647704dcf1":
        raise ValueError("BN source is not the pinned base")
    for name in base_files:
        relative = Path("src") / name
        for directory in ("pinned", "engine_staging"):
            target = root / directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Read the pinned commit, never a possibly modified working tree.
            content = subprocess.check_output(["git", "-C", str(args.bn_source), "show", "HEAD:" + relative.as_posix()])
            target.write_bytes(content)
    for directory in ("src", "tests"):
        target = root / "engine_staging" / directory
        target.mkdir(parents=True, exist_ok=True)
    for name in ("artisan_expression.h", "artisan_bn_bridge.h", "artisan_items.h", "faction_food_stock.h", "lighthouse_quest_updates.h"):
        (root / "engine_staging/src" / name).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_artisan_dialogue_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_artisan_services_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/data/json/dda_artisan_activities.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/dda_lighthouse_community.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/npcs/dda_lighthouse_community.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/mapgen/nested/dda_lighthouse_encounter.json").unlink(missing_ok=True)
    for relative in (Path("data/json/mapgen/dock.json"), Path("data/json/mapgen/chemical_lab.json")):
        content = subprocess.check_output(["git", "-C", str(args.bn_source), "show", "HEAD:" + relative.as_posix()])
        for directory in ("pinned", "engine_staging"):
            target = root / directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    subprocess.run(["git", "apply", "--directory=engine_staging", str(root / "artisan_engine.patch")], cwd=root, check=True)
parts = []
for name in base_files:
    path = "src/" + name
    old = (root / "pinned" / path).read_text().splitlines(keepends=True)
    new = (root / "engine_staging" / path).read_text().splitlines(keepends=True)
    parts.extend(difflib.unified_diff(old, new, "a/" + path, "b/" + path))
for name in ("artisan_expression.h", "artisan_bn_bridge.h", "artisan_items.h", "faction_food_stock.h", "lighthouse_quest_updates.h",
             "dda_artisan_dialogue_test.cpp", "dda_artisan_services_test.cpp"):
    path = ("tests/" if name.endswith("_test.cpp") else "src/") + name
    new = (root / "native" / name).read_text().splitlines(keepends=True)
    parts.extend(difflib.unified_diff([], new, "/dev/null", "b/" + path))
path = "data/json/dda_artisan_activities.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_artisan_activities.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/npcs/dda_lighthouse_community.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_lighthouse_community.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/mapgen/dock.json"
parts.extend(difflib.unified_diff((root / "pinned" / path).read_text().splitlines(keepends=True),
                                (root / "lighthouse/staging" / path).read_text().splitlines(keepends=True),
                                "a/" + path, "b/" + path))
path = "data/json/mapgen/nested/dda_lighthouse_encounter.json"
parts.extend(difflib.unified_diff([], (root / "native/mapgen/dda_lighthouse_encounter.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/mapgen/chemical_lab.json"
parts.extend(difflib.unified_diff((root / "layers/bn" / path).read_text().splitlines(keepends=True),
                                (root / "layers/merged/chemical_lab.json").read_text().splitlines(keepends=True),
                                "a/" + path, "b/" + path))
payload = "".join(parts).encode()
(root / "artisan_engine.patch").write_bytes(payload)
digest = hashlib.sha256(payload).hexdigest()
workflow = root / "build-dda-npc-engine.yml"
text = workflow.read_text()
text, replacements = re.subn(r'(Get-FileHash \$patch -Algorithm SHA256\)\.Hash\.ToLower\(\) -ne ")[a-f0-9]{64}',
                            lambda match: match[1] + digest, text)
assert replacements == 1, "Expected exactly one native patch checksum"
text = text.replace('"src/artisan_bn_bridge.h", "tests/',
                    '"src/artisan_bn_bridge.h", "src/artisan_items.h", "tests/')
workflow.write_text(text)
print(digest)
