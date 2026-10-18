#!/usr/bin/env python3
"""Reject stale embedded native files before spending time on a Windows build."""
import hashlib
import re
import difflib
from pathlib import Path
from merge_existing_locations import prepare as prepare_existing_locations
from prepare_militia import prepare as prepare_militia, PAYLOAD as MILITIA_PAYLOAD
from prepare_frontage import prepare as prepare_frontage, patch_sections as frontage_patch, TARGET as FRONTAGE_TARGET, sources as frontage_sources
from prepare_location_expansion import nuclear_patch, NUCLEAR
from prepare_radio_stations import prepare as prepare_radio, PAYLOAD as RADIO_PAYLOAD
from prepare_tower_expansions import patch_sections as tower_patch, prepare as prepare_towers, PAYLOAD as HOTEL_PAYLOAD
from prepare_shopping_plaza import PAYLOAD as PLAZA_PAYLOAD
from prepare_rural_churches import prepare as prepare_churches, PAYLOAD as CHURCH_PAYLOAD
from prepare_xedra_creature import prepare as prepare_creature, patch_sections as creature_patch, PAYLOAD as CREATURE_PAYLOAD
from prepare_karting import prepare as prepare_karting, PAYLOAD as KARTING_PAYLOAD
from prepare_xedra_gear import prepare as prepare_gear, PAYLOAD as GEAR_PAYLOAD
from prepare_hub_elevator import patch_sections as hub_access_patch, prepare as prepare_hub_access, PAYLOAD as HUB_PAYLOAD

from prepare_farm_supply import prepare as prepare_farm, PAYLOAD as FARM_PAYLOAD
from prepare_eldercare import prepare as prepare_eldercare, PAYLOAD as ELDERCARE_PAYLOAD
from prepare_shared_casing import prepare as prepare_shared_casing, patch_sections as shared_casing_patch, TARGET as SHARED_CASING_TARGET
from prepare_eldercare_groups import prepare as prepare_groups, PAYLOAD as GROUPS_PAYLOAD
from prepare_civilians import prepare as prepare_civilians, PAYLOAD as CIVILIAN_PAYLOAD, LEGACY_CORE, LUA_PAYLOAD, extend_chat, patch_sections as civilian_patch
from prepare_eldercare_fauna import prepare as prepare_fauna, PAYLOAD as FAUNA_PAYLOAD
from prepare_eldercare_loot import prepare as prepare_loot, PAYLOAD as LOOT_PAYLOAD
from prepare_eldercare_assets import prepare as prepare_assets, PAYLOAD as ASSET_PAYLOAD
from prepare_terminal_archives import prepare as prepare_archives, patch_sections as archive_patch, CORE as ARCHIVE_CORE, PAYLOAD as ARCHIVE_PAYLOAD
from prepare_mapgen_corpses import patch_sections as corpse_patch

ROOT = Path(__file__).resolve().parent


def check():
    patch = (ROOT / 'artisan_engine.patch').read_text()
    prepare_existing_locations()
    prepare_frontage()
    prepare_militia(check=True)
    target = 'data/json/mapgen/chemical_lab.json'
    expected_map_patch = ''.join(difflib.unified_diff(
        (ROOT / 'layers/bn' / target).read_text().splitlines(keepends=True),
        (ROOT / 'layers/merged/chemical_lab.json').read_text().splitlines(keepends=True),
        'a/' + target, 'b/' + target))
    assert patch.count('+++ b/' + target + '\n') == 1, 'Expected one chemist replacement'
    assert expected_map_patch in patch, 'Stale reviewed chemist map patch'
    expected_nuclear, _, _ = nuclear_patch()
    assert patch.count('+++ b/' + NUCLEAR + '\n') == 1, 'Expected one nuclear replacement'
    assert expected_nuclear in patch, 'Stale nuclear shoreline patch'
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
    prepare_groups(check=True)
    prepare_shared_casing(check=True)
    talk_section = patch.split("+++ b/src/npctalk.cpp\n", 1)[1].split("\n--- ", 1)[0]
    assert talk_section.count("+#include \"civilian_chat_ui.h\"") == 1
    assert "+            show_civilian_chat( *civilians[people.ret] );" in patch
    assert shared_casing_patch() in patch
    assert patch.count("+++ b/" + SHARED_CASING_TARGET + "\n") == 1
    assert civilian_patch() in patch
    assert patch.count("+++ b/" + CIVILIAN_PAYLOAD + "\n") == 1
    assert "+++ b/" + LEGACY_CORE + "\n" not in patch
    assert corpse_patch() in patch, "Stale corpse mapgen replacement"
    assert creature_patch() in patch, "Stale configurable native ranged pull"
    assert tower_patch() in patch, "Stale composed tower replacements"
    assert frontage_patch() in patch, "Stale fixed-special constraint bridge"
    assert patch.count("+++ b/" + FRONTAGE_TARGET + "\n") == 1
    expected_hub = hub_access_patch()
    assert expected_hub in patch, "Stale Hub elevator native replacement"
    assert archive_patch() in patch, "Stale terminal archive integration"
    for name in ARCHIVE_CORE:
        assert patch.count("+++ b/src/" + name + "\n") == 1, name
    files = {
        'src/' + name: ROOT / 'native' / name
        for name in ('artisan_expression.h', 'artisan_bn_bridge.h', 'artisan_items.h',
                     'faction_food_stock.h', 'lighthouse_quest_updates.h', 'hub_elevator_access.h', 'dda_mapgen_corpses.h', 'computer_archive.h', 'civilian_chat.h', 'civilian_chat_ui.h')
    }
    files.update({
        'tests/' + name: ROOT / 'native' / name
        for name in ('dda_artisan_dialogue_test.cpp', 'dda_artisan_services_test.cpp', 'dda_radio_stations_test.cpp', 'dda_computer_archive_test.cpp', 'dda_eldercare_assets_test.cpp', 'dda_eldercare_loot_test.cpp', 'dda_eldercare_fauna_test.cpp', 'dda_civilians_test.cpp', 'dda_special_constraints_test.cpp', 'dda_militia_test.cpp')
    })
    files.update({
        HUB_PAYLOAD: ROOT / 'native/dda_hub_elevator_access.json',
        RADIO_PAYLOAD: ROOT / 'native/dda_radio_station_towers.json',
        HOTEL_PAYLOAD: ROOT / 'native/dda_hotel_roof_caps.json',
        PLAZA_PAYLOAD: ROOT / 'native/dda_shopping_plaza_roofs.json',
        CHURCH_PAYLOAD: ROOT / 'native/dda_rural_church.json',
        CREATURE_PAYLOAD: ROOT / 'native/dda_xedra_creature.json',
        GEAR_PAYLOAD: ROOT / 'native/dda_xedra_activity_suits.json',
        KARTING_PAYLOAD: ROOT / 'native/dda_karting_circuit.json',
        ELDERCARE_PAYLOAD: ROOT / 'native/dda_eldercare_support.json',
        FARM_PAYLOAD: ROOT / 'native/dda_farm_supply.json',
        ARCHIVE_PAYLOAD: ROOT / 'native/dda_terminal_archives.json',
        ASSET_PAYLOAD: ROOT / 'native/dda_eldercare_assets.json',
        FAUNA_PAYLOAD: ROOT / 'native/dda_eldercare_fauna.json',
        MILITIA_PAYLOAD: ROOT / 'native/dda_grey_moose_lodge.json',
        GROUPS_PAYLOAD: ROOT / 'native/dda_eldercare_groups.json',
        LOOT_PAYLOAD: ROOT / 'native/dda_eldercare_loot.json',
        'data/json/dda_artisan_activities.json': ROOT / 'native/dda_artisan_activities.json',
        'data/json/items/dda_quest_usb.json': ROOT / 'native/dda_quest_usb.json',
        'data/json/items/dda_545_casing.json': ROOT / 'native/dda_545_casing.json',
        'data/json/items/dda_quest_props.json': ROOT / 'native/dda_quest_props.json',
        'data/json/npcs/dda_lighthouse_community.json': ROOT / 'native/dda_lighthouse_community.json',
        'data/json/mapgen/nested/dda_lighthouse_encounter.json': ROOT / 'native/mapgen/dda_lighthouse_encounter.json',
    })
    for target, source in files.items():
        marker = '--- /dev/null\n+++ b/' + target + '\n'
        if patch.count(marker) != 1:
            raise AssertionError('Expected exactly one patch section: ' + target)
        section = patch.split(marker, 1)[1].split('\n--- ', 1)[0]
        content = ''.join(line[1:] for line in section.splitlines(keepends=True)
                          if line.startswith('+'))
        # split() removes the section's final newline when another diff follows.
        if not content.endswith('\n'):
            content += '\n'
        if content != source.read_text():
            raise AssertionError('Stale native patch: ' + target + '; run build_engine_patch.py')
    digest = hashlib.sha256((ROOT / 'artisan_engine.patch').read_bytes()).hexdigest()
    workflow_path = ROOT.parent / '.github/workflows/build-dda-npc-engine.yml'
    if not workflow_path.exists():
        workflow_path = ROOT / 'build-dda-npc-engine.yml'
    workflow = workflow_path.read_text()
    expected, = re.findall(r'Get-FileHash \$patch -Algorithm SHA256\)\.Hash\.ToLower\(\) -ne "([a-f0-9]{64})"', workflow)
    assert digest == expected, 'Windows workflow patch checksum is stale'
    print(f'PASS: all {len(files)} embedded native files and Windows patch checksum match')


if __name__ == '__main__':
    check()
