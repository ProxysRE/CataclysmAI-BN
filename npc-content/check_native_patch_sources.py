#!/usr/bin/env python3
"""Reject stale embedded native files before spending time on a Windows build."""
import hashlib
import re
import difflib
from pathlib import Path
from merge_existing_locations import prepare as prepare_existing_locations

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
    files = {
        'src/' + name: ROOT / 'native' / name
        for name in ('artisan_expression.h', 'artisan_bn_bridge.h', 'artisan_items.h',
                     'faction_food_stock.h', 'lighthouse_quest_updates.h')
    }
    files.update({
        'tests/' + name: ROOT / 'native' / name
        for name in ('dda_artisan_dialogue_test.cpp', 'dda_artisan_services_test.cpp')
    })
    files.update({
        'data/json/dda_artisan_activities.json': ROOT / 'native/dda_artisan_activities.json',
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
    print('PASS: all ten embedded native files and Windows patch checksum match')


if __name__ == '__main__':
    check()
