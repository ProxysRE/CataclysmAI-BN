#!/usr/bin/env python3
"""Check candidate namespacing, repeated-ID slices and conditional stair fixtures."""
import collections
import copy
import json

from prepare_apartment_preview import prepare, OUT
from prepare_regional_locations import flatten


def validate_neighbors(entries):
    own = {name for e in entries if e['type'] == 'overmap_terrain' for name in flatten(e['id'])}
    count = 0
    for e in entries:
        if e['type'] != 'mapgen':
            continue
        for place in e['object'].get('place_nested', []):
            if 'neighbors' not in place:
                continue
            assert set(place['neighbors']) == {'above'}
            assert set(place['neighbors']['above']) <= own, ('Dangling preview above-neighbor type', place)
            count += 1
    assert count == 6


def check():
    prepare(check=True)
    raw = json.loads((OUT / 'APARTMENT_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    entries = json.loads((OUT / 'APARTMENT_PREVIEW_SHELL.json').read_text(encoding='utf-8'))
    report = json.loads((OUT / 'APARTMENT_PREVIEW_REPORT.json').read_text(encoding='utf-8'))
    ar = json.loads((OUT / 'APARTMENT_ADAPTATION_REPORT.json').read_text(encoding='utf-8'))
    assert report['world_maps'] == 31 and report['own_omt'] == 37
    assert report['nested_identities'] == 40 and report['nested_definitions'] == 83
    assert report['navigation_points'] == 113 and report['fixture_check_count'] == 284
    assert report['random_overlay_exclusions'] == 6
    assert report['conditional_fixture_counts'] == {'negative': 9, 'positive': 3}
    assert not report['unresolved_typed_refs']
    assert not report['native_embedded'] and not report['runtime_validated']

    def rename(v):
        if isinstance(v, str):
            return report['aliases'].get(v, v)
        if isinstance(v, list):
            return [rename(x) for x in v]
        if isinstance(v, dict):
            return {k: rename(x) for k, x in v.items()}
        return v

    selected = [e for e in raw if 'nested_mapgen_id' not in e or e['nested_mapgen_id'] in ar['reachable_nested_identities']]
    # Preserve complete objects and every alternative, not only rows/counts.
    assert collections.Counter(json.dumps(rename(e), sort_keys=True) for e in selected) == collections.Counter(
        json.dumps(e, sort_keys=True) for e in entries)
    specials = {e['id']: e for e in entries if e['type'] == 'overmap_special'}
    assert len(specials) == 5 and sum(len(e['overmaps']) for e in specials.values()) == 322
    for e in entries:
        if e['type'] == 'mapgen':
            assert all(not p.get('z', 0) for p in e['object'].get('place_nested', []))
        elif e['type'] == 'overmap_special':
            assert e['occurrences'] == [0, 0]
    validate_neighbors(entries)
    probe = copy.deepcopy(entries)
    obj = next(e['object'] for e in probe if e['type'] == 'mapgen' and any(
        'neighbors' in p for p in e['object'].get('place_nested', [])))
    place = next(p for p in obj['place_nested'] if 'neighbors' in p)
    place['neighbors']['above'] = ['apartment_complex_straight_stairs_odd']
    try:
        validate_neighbors(probe)
    except AssertionError:
        pass
    else:
        raise AssertionError('Original unnamespaced neighbor regression accepted')
    entrance = next(e for e in entries if 'dda_geo_apartment_complex_entrance' in set(flatten(e.get('om_terrain', []))))
    assert entrance['om_terrain'] == [['dda_geo_apartment_complex_entrance'] * 4]
    assert len(entrance['object']['rows']) == 24 and all(len(row) == 96 for row in entrance['object']['rows'])
    assert report['multi_omt_variants'] == {'dda_geo_apartment_complex_entrance': [
        {'source_slot': [i, 0], 'weight': 1000} for i in range(4)]}
    positives = set()
    negatives = 0
    for name, points in report['fixture_checks'].items():
        cells = {tuple(c['point']): c['overmap'] for c in specials[name]['overmaps']}
        signatures = [(p['omt_x'], p['omt_y'], p['z'], p['x'], p['y']) for p in points]
        assert len(signatures) == len(set(signatures)), 'Conflicting duplicate expectations'
        for p in points:
            assert (p['omt_x'], p['omt_y'], p['z']) in cells
            assert 0 <= p['x'] < 24 and 0 <= p['y'] < 24
            if 'conditional_stair' not in p:
                continue
            assert p['above'] == cells[(p['omt_x'], p['omt_y'], p['z'] + 1)]
            if p['conditional_stair']:
                assert p['terrain'] == 't_stairs_up'
                positives.add((name, p['omt_x'], p['omt_y'], p['x'], p['y']))
            else:
                assert p['terrain'] == 't_linoleum_white'
                negatives += 1
    assert positives == {('dda_geo_apartment_complex_line', 1, 1, 11, 1),
                         ('dda_geo_apartment_complex_u', 1, 1, 1, 12),
                         ('dda_geo_apartment_complex_u_alt', 3, 1, 22, 11)}
    assert negatives == 9
    print('PASS: namespaced 322-cell candidate, all 83 reachable nested alternatives and four entrance slices; '
          '284 fixture points with three positive/nine negative stair checks; native integration pending')


if __name__ == '__main__':
    check()
