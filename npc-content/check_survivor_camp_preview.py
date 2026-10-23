#!/usr/bin/env python3
"""Verify camp roof composition, variant separation and untouched-forest masks."""
import copy
import json
from prepare_survivor_camp_preview import prepare, OUT, PREFIX, ANCHORS


def validate(entries, report):
    worlds = {e['om_terrain']: e for e in entries if isinstance(e.get('om_terrain'), str)}
    nests = {e['nested_mapgen_id']: e for e in entries if 'nested_mapgen_id' in e}
    assert len(worlds) == 3 and len(nests) == 4
    roof = worlds[PREFIX + 'intact_roof']['object']
    assert roof['fill_ter'] == 't_open_air'
    assert roof['rows'] == [' ' * 24] * 24 and roof['terrain'] == {' ': 't_open_air'}
    assert roof['place_nested'] == [{'chunks': [PREFIX + 'tent_5x5_roof'], 'x': x, 'y': y} for x, y in ANCHORS]
    assert not nests[PREFIX + 'leather_tent_5x5_S']['object'].get('place_nested')
    assert nests[PREFIX + 'leather_tent_5x5_S']['object']['rotation'] == [0, 3]
    square = nests[PREFIX + 'tent_5x5_roof']['object']['rows']
    for _ in range(4):
        assert square == ['#####'] * 5
        square = [''.join(row) for row in zip(*square[::-1])]
    for variant in ('intact', 'ruined'):
        name = PREFIX + variant; o = worlds[name]['object']
        anchors = [(x, y) for y, row in enumerate(o['rows']) for x, glyph in enumerate(row) if glyph in o['nested']]
        assert anchors == ANCHORS
        mask = report['loot_masks'][name]
        assert mask == ''.join('1' if glyph in o['terrain'] else '0' for row in o['rows'] for glyph in row)
        assert mask[:48] == '0' * 48
        assert o['predecessor_mapgen'] == 'forest_thick' and 'fill_ter' not in o
        assert set(o['remove_all']) == set(o['terrain'])
        assert ' ' not in o['remove_all']
        special = next(e for e in entries if e['type'] == 'overmap_special' and e['id'] == name)
        assert special['occurrences'] == [0, 0]
        expected = [{'point': [0, 0, 0], 'overmap': name + '_north'}]
        if variant == 'intact': expected.append({'point': [0, 0, 1], 'overmap': PREFIX + 'intact_roof_north'})
        assert special['overmaps'] == expected
    assert len(report['intact_expected_points']) == 90
    assert sum('terrain' in p for p in report['intact_expected_points']) == 75
    assert sum('furniture' in p for p in report['intact_expected_points']) == 15


def check():
    prepare(check=True)
    entries = json.loads((OUT / 'SURVIVOR_CAMP_PREVIEW_SHELL.json').read_text())
    report = json.loads((OUT / 'SURVIVOR_CAMP_PREVIEW_REPORT.json').read_text())
    validate(entries, report)
    full = json.loads((OUT / 'SURVIVOR_ADAPTED_SHELL.json').read_text())
    original_worlds = [e for e in full if e.get('om_terrain') == ['survivor_forest_camp']]
    for variant, original in zip(('intact', 'ruined'), original_worlds):
        new = next(e for e in entries if e.get('om_terrain') == PREFIX + variant)
        expected = copy.deepcopy(original['object']); actual = copy.deepcopy(new['object'])
        actual.pop('predecessor_mapgen'); actual.pop('remove_all')
        def unprefix(value):
            if isinstance(value, str): return value.removeprefix(PREFIX)
            if isinstance(value, list): return [unprefix(v) for v in value]
            if isinstance(value, dict): return {k: unprefix(v) for k, v in value.items()}
            return value
        assert unprefix(actual) == expected
        assert report['source_weights'][variant] == original.get('weight', 1000)
    for old in (e for e in full if e.get('nested_mapgen_id', '').startswith(('leather_tent', 'tent_'))):
        new = next(e for e in entries if e.get('nested_mapgen_id') == PREFIX + old['nested_mapgen_id'])
        assert new['object'].get('rows') == old['object'].get('rows')
        assert new['object'].get('rotation') == old['object'].get('rotation')
        assert new['object'].get('furniture') == old['object'].get('furniture')
    # These regression probes prevent moving the source canopy or clearing
    # ordinary surrounding forest merely to satisfy an empty-loot fixture.
    for mutation in ('shift_roof', 'clear_forest'):
        bad = copy.deepcopy(entries)
        if mutation == 'shift_roof':
            next(e for e in bad if e.get('om_terrain') == PREFIX + 'intact_roof')['object']['place_nested'][0]['x'] += 1
        else:
            next(e for e in bad if e.get('om_terrain') == PREFIX + 'intact')['object']['remove_all'][' '] = {}
        try: validate(bad, report)
        except AssertionError: pass
        else: raise AssertionError('Invalid camp geometry accepted: ' + mutation)
    assert report['native_embedded'] and not report['runtime_validated']
    print('PASS: source rows, random tent rotations and ruined/null weights conserved; shifted roof and blanket forest clearing rejected; 90 native expectations prepared')


if __name__ == '__main__': check()
