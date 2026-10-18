#!/usr/bin/env python3
"""Rebuild the native patch against the pinned, unmodified BN files."""
import argparse
import difflib
import hashlib
import re
import subprocess
from pathlib import Path
from merge_existing_locations import prepare as prepare_existing_locations
from prepare_location_expansion import nuclear_patch, NUCLEAR
from prepare_radio_stations import prepare as prepare_radio, MAP as RADIO_MAP, CITY as RADIO_CITY, PAYLOAD as RADIO_PAYLOAD
from prepare_tower_expansions import patch_sections as tower_patch, prepare as prepare_towers, PAYLOAD as HOTEL_PAYLOAD
from prepare_shopping_plaza import PAYLOAD as PLAZA_PAYLOAD
from prepare_rural_churches import prepare as prepare_churches, PAYLOAD as CHURCH_PAYLOAD
from prepare_xedra_creature import prepare as prepare_creature, patch_sections as creature_patch, PAYLOAD as CREATURE_PAYLOAD, CORE as CREATURE_CORE
from prepare_karting import prepare as prepare_karting, PAYLOAD as KARTING_PAYLOAD
from prepare_xedra_gear import prepare as prepare_gear, PAYLOAD as GEAR_PAYLOAD
from prepare_hub_elevator import patch_sections as hub_access_patch, prepare as prepare_hub_access, PAYLOAD as HUB_PAYLOAD, MUTATIONS

from prepare_farm_supply import prepare as prepare_farm, PAYLOAD as FARM_PAYLOAD
from prepare_eldercare import prepare as prepare_eldercare, PAYLOAD as ELDERCARE_PAYLOAD
from prepare_civilians import prepare as prepare_civilians, PAYLOAD as CIVILIAN_PAYLOAD, LEGACY_CORE, extend_chat, patch_sections as civilian_patch
from prepare_eldercare_fauna import prepare as prepare_fauna, PAYLOAD as FAUNA_PAYLOAD
from prepare_eldercare_loot import prepare as prepare_loot, PAYLOAD as LOOT_PAYLOAD
from prepare_eldercare_assets import prepare as prepare_assets, PAYLOAD as ASSET_PAYLOAD
from prepare_terminal_archives import prepare as prepare_archives, patch_sections as archive_patch, CORE as ARCHIVE_CORE, PAYLOAD as ARCHIVE_PAYLOAD
from prepare_mapgen_corpses import patch_sections as corpse_patch, CORE as CORPSE_CORE

root = Path(__file__).resolve().parent
base_files = ("condition.cpp", "npctalk.cpp", "faction.h", "faction.cpp",
              "savegame_json.cpp", "activity_type.h", "activity_type.cpp", "player_activity.cpp",
              "npc.cpp", "npc_class.cpp", "npc_class.h", "game.h", "game.cpp", "savegame.cpp")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bn-source", type=Path,
                    help="Pinned BN checkout; restore staging before rebuilding")
args = parser.parse_args()
prepare_existing_locations()
prepare_hub_access(check=True)
prepare_radio(check=True)
prepare_towers(check=True)
prepare_churches(check=True)
prepare_creature(check=True)
prepare_gear(check=True)
prepare_karting(check=True)
prepare_eldercare(check=True)
prepare_farm(check=True)
prepare_archives(check=True)
prepare_assets(check=True)
prepare_loot(check=True)
prepare_fauna(check=True)
prepare_civilians(check=True)
if args.bn_source:
    actual = subprocess.check_output(["git", "-C", str(args.bn_source), "rev-parse", "HEAD"], text=True).strip()
    if actual != "c621aaf42fa182473aad10feea2b55647704dcf1":
        raise ValueError("BN source is not the pinned base")
    for name in base_files + CREATURE_CORE + CORPSE_CORE + ARCHIVE_CORE + ("iexamine.cpp", "iexamine.h", "iexamine_elevator.cpp"):
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
    (root / "engine_staging/src/hub_elevator_access.h").unlink(missing_ok=True)
    (root / "engine_staging/src/dda_mapgen_corpses.h").unlink(missing_ok=True)
    (root / "engine_staging/src/computer_archive.h").unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_computer_archive_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging" / ARCHIVE_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / ASSET_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / LEGACY_CORE).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_civilians_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/src/civilian_chat.h").unlink(missing_ok=True)
    (root / "engine_staging/src/civilian_chat_ui.h").unlink(missing_ok=True)
    (root / "engine_staging" / FAUNA_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_eldercare_fauna_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging" / LOOT_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_eldercare_loot_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_eldercare_assets_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging" / HUB_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_radio_stations_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging" / RADIO_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / HOTEL_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / PLAZA_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / CHURCH_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / CREATURE_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / GEAR_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / KARTING_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / ELDERCARE_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging" / FARM_PAYLOAD).unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_artisan_dialogue_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/tests/dda_artisan_services_test.cpp").unlink(missing_ok=True)
    (root / "engine_staging/data/json/dda_artisan_activities.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/items/dda_quest_usb.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/items/dda_545_casing.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/items/dda_quest_props.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/dda_lighthouse_community.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/npcs/dda_lighthouse_community.json").unlink(missing_ok=True)
    (root / "engine_staging/data/json/mapgen/nested/dda_lighthouse_encounter.json").unlink(missing_ok=True)
    for relative in (Path("data/json/mapgen/dock.json"), Path("data/json/mapgen/chemical_lab.json"), Path(NUCLEAR), Path(MUTATIONS), Path(RADIO_MAP), Path(RADIO_CITY), Path(CIVILIAN_PAYLOAD)):
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
    if name == "npctalk.cpp":
        new = extend_chat("".join(new)).splitlines(keepends=True)
    parts.extend(difflib.unified_diff(old, new, "a/" + path, "b/" + path))
for name in ("artisan_expression.h", "artisan_bn_bridge.h", "artisan_items.h", "faction_food_stock.h", "lighthouse_quest_updates.h", "hub_elevator_access.h", "dda_mapgen_corpses.h", "computer_archive.h", "civilian_chat.h", "civilian_chat_ui.h",
             "dda_artisan_dialogue_test.cpp", "dda_artisan_services_test.cpp", "dda_radio_stations_test.cpp", "dda_computer_archive_test.cpp", "dda_eldercare_assets_test.cpp", "dda_eldercare_loot_test.cpp", "dda_eldercare_fauna_test.cpp", "dda_civilians_test.cpp"):
    path = ("tests/" if name.endswith("_test.cpp") else "src/") + name
    new = (root / "native" / name).read_text().splitlines(keepends=True)
    parts.extend(difflib.unified_diff([], new, "/dev/null", "b/" + path))
path = "data/json/dda_artisan_activities.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_artisan_activities.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/items/dda_quest_usb.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_quest_usb.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/items/dda_545_casing.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_545_casing.json").read_text().splitlines(keepends=True),
                                "/dev/null", "b/" + path))
path = "data/json/items/dda_quest_props.json"
parts.extend(difflib.unified_diff([], (root / "native/dda_quest_props.json").read_text().splitlines(keepends=True),
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
parts.append(nuclear_patch()[0])
parts.append(hub_access_patch())
parts.extend(difflib.unified_diff([], (root / "native/dda_hub_elevator_access.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + HUB_PAYLOAD))
parts.append(tower_patch())
parts.extend(difflib.unified_diff([], (root / "native/dda_radio_station_towers.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + RADIO_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_hotel_roof_caps.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + HOTEL_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_shopping_plaza_roofs.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + PLAZA_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_rural_church.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + CHURCH_PAYLOAD))
parts.append(creature_patch())
parts.append(corpse_patch())
parts.append(archive_patch())
parts.append(civilian_patch())
parts.extend(difflib.unified_diff([], (root / "native/dda_eldercare_fauna.json").read_text(encoding="utf-8").splitlines(keepends=True), "/dev/null", "b/" + FAUNA_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_eldercare_loot.json").read_text(encoding="utf-8").splitlines(keepends=True), "/dev/null", "b/" + LOOT_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_eldercare_assets.json").read_text(encoding="utf-8").splitlines(keepends=True), "/dev/null", "b/" + ASSET_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_terminal_archives.json").read_text(encoding="utf-8").splitlines(keepends=True), "/dev/null", "b/" + ARCHIVE_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_xedra_creature.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + CREATURE_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_xedra_activity_suits.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + GEAR_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_karting_circuit.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + KARTING_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_eldercare_support.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + ELDERCARE_PAYLOAD))
parts.extend(difflib.unified_diff([], (root / "native/dda_farm_supply.json").read_text(encoding="utf-8").splitlines(keepends=True),
                                "/dev/null", "b/" + FARM_PAYLOAD))
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
