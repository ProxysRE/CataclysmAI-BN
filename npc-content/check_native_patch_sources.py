#!/usr/bin/env python3
"""Reject stale embedded native files before spending time on a Windows build."""
import hashlib
import re
import difflib
from pathlib import Path
from merge_existing_locations import prepare as prepare_existing_locations
from prepare_location_expansion import nuclear_patch, NUCLEAR
from prepare_radio_stations import prepare as prepare_radio, PAYLOAD as RADIO_PAYLOAD
from prepare_tower_expansions import patch_sections as tower_patch, prepare as prepare_towers, PAYLOAD as HOTEL_PAYLOAD
from prepare_shopping_plaza import PAYLOAD as PLAZA_PAYLOAD
from prepare_rural_churches import prepare as prepare_churches, PAYLOAD as CHURCH_PAYLOAD
from prepare_hub_elevator import patch_sections as hub_access_patch, prepare as prepare_hub_access, PAYLOAD as HUB_PAYLOAD

ROOT = Path(__file__).resolve().parent


def check():
    patch = (ROOT / 'artisan_engine.patch').read_text()
    prepare_existing_locations()
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
    assert tower_patch() in patch, "Stale composed tower replacements"
    expected_hub = hub_access_patch()
    assert expected_hub in patch, "Stale Hub elevator native replacement"
    files = {
        'src/' + name: ROOT / 'native' / name
        for name in ('artisan_expression.h', 'artisan_bn_bridge.h', 'artisan_items.h',
                     'faction_food_stock.h', 'lighthouse_quest_updates.h', 'hub_elevator_access.h')
    }
    files.update({
        'tests/' + name: ROOT / 'native' / name
        for name in ('dda_artisan_dialogue_test.cpp', 'dda_artisan_services_test.cpp', 'dda_radio_stations_test.cpp')
    })
    files.update({
        HUB_PAYLOAD: ROOT / 'native/dda_hub_elevator_access.json',
        RADIO_PAYLOAD: ROOT / 'native/dda_radio_station_towers.json',
        HOTEL_PAYLOAD: ROOT / 'native/dda_hotel_roof_caps.json',
        PLAZA_PAYLOAD: ROOT / 'native/dda_shopping_plaza_roofs.json',
        CHURCH_PAYLOAD: ROOT / 'native/dda_rural_church.json',
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
