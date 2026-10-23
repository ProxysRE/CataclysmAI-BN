#!/usr/bin/env python3
"""Verify original layouts, weighted alternatives and unresolved vertical geometry."""
import json
from collections import Counter
from prepare_survivor_geometry import OUT, MAPS, STRUCTURAL, sources, prepare, flatten

prepare(check=True)
files, palettes, reused = sources()
entries = json.loads((OUT / 'SURVIVOR_SHELLS.json').read_text())
report = json.loads((OUT / 'SURVIVOR_GEOMETRY_REPORT.json').read_text())
original = [e for es in files.values() for e in es if e.get('type') == 'mapgen'
            and (set(flatten(e.get('om_terrain', []))) & MAPS or e.get('nested_mapgen_id') in STRUCTURAL)]
maps = [e for e in entries if 'om_terrain' in e]
assert len(maps) == 11 and len(original) == 16
assert report['special_cells'] == {'Locked LMOE Shelter': 2, 'Cabin_prepper': 3,
                                    'cabin_liam': 5, 'survivor_forest_camp': 1, 'cemetery_lacroix': 5}
for source in original:
    key = 'om_terrain' if 'om_terrain' in source else 'nested_mapgen_id'
    matches = [e for e in entries if e.get(key) == source[key]]
    if source.get('om_terrain') == ['survivor_forest_camp']:
        matches = [e for e in matches if e.get('weight', 1000) == source.get('weight', 1000)]
    assert matches
    for entry in matches:
        assert entry['object'].get('rows') == source['object'].get('rows')
        assert entry['object'].get('rotation') == source['object'].get('rotation')
    if source.get('om_terrain') == ['cabin_prepper']:
        assert len(matches) == 2 and [e['weight'] for e in matches] == [500, 500]
        assert sum(e['weight'] for e in matches) == source.get('weight', 1000)
        assert matches[0]['object']['terrain']['>'] == matches[1]['object']['terrain']['>'] == 't_stairs_down'
    else:
        assert len(matches) == 1
        assert matches[0].get('weight', 1000) == source.get('weight', 1000)
    if source.get('nested_mapgen_id', '').startswith('leather_tent'):
        assert matches[0]['object']['furniture'] == source['object']['furniture']
        if source['nested_mapgen_id'] != 'leather_tent_5x5_S':
            assert not matches[0]['object'].get('place_nested')
upward = [p for e in entries if e['type'] == 'mapgen' for p in e['object'].get('place_nested', []) if p.get('z', 0)]
assert len(upward) == 3 and all(p['z'] == 1 for p in upward)
assert Counter(i['type'] for i in report['geometry_issues']) == {
    'nested_vertical_offset_not_supported_by_pinned_BN': 3,
    'fallback_predecessor_needs_BN_adaptation': 2,
    'dynamic_mapgen_weight_needs_BN_adaptation': 1}
assert not report['native_embedded'] and not report['runtime_validated']
assert all(e['occurrences'] == [0, 0] for e in entries if e['type'] == 'overmap_special')
assert len(json.loads((OUT / 'SURVIVOR_LATER_LAYERS.json').read_text())) > len(entries)
print('PASS: five specials, 16 placements, 11 maps; correlated cabin alternatives and all three vertical blockers retained')
