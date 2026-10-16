#!/usr/bin/env python3
"""Reject duplicate-prone location plans and preserve weighted map variants."""
import json

from build_location_merge_plan import build, map_decision
from prepare_community_layers import ROOT


def main():
    manifest = json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    assert len([name for name in manifest['files'] if name.startswith('bn/data/json/overmap/overmap_special/')]) == 12
    plan = build(ROOT)
    by_id = {x['id']:x for x in plan['locations']}
    for identifier in ('Lumbermill','Occupied Lumbermill','Occupied Chem Lab','Occupied Scrap Yard',
                       'ws_survivor_bunker_place','hub_01'):
        entry = by_id[identifier]
        assert entry['baseline'] is not None, identifier
        assert entry['operation']=='merge_existing_special', identifier
        assert entry['preserve_existing_occurrence'] and not entry['installable']
    for row in plan['mapgen']:
        assert not row['installable']
        if row['baseline_variants']:
            assert row['operation'] in {'keep_existing_variant_set','review_existing_variant_set'}
        else:
            assert row['operation']=='resolve_baseline_before_addition'
    occupied = [x for x in plan['mapgen'] if x['terrain']=='lumbermill_1_1_ocu']
    assert occupied and all(x['baseline_variants'] for x in occupied)
    chem = [x for x in plan['mapgen'] if 'chemical_lab' in x['source']['file']]
    assert chem and all(x['baseline_variants'] for x in chem)
    fixture = {'type':'mapgen','om_terrain':'mill','object':{'rows':['.']}}
    assert map_decision(fixture,[fixture,{**fixture,'weight':2}])=='keep_existing_variant_set'
    assert map_decision(fixture,[])=='resolve_baseline_before_addition'
    assert not plan['release_ready']
    print('PASS: six existing BN sites require merging; map variants and missing-baseline gates preserved')
    print(json.dumps(plan['summary']))


if __name__ == '__main__':
    main()
