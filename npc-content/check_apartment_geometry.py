#!/usr/bin/env python3
"""Check apartment source conservation and explicit pre-integration boundaries."""
import collections
import json
import re

from prepare_apartment_geometry import prepare as stage, sources, OUT, TARGETS
from adapt_apartment_geometry import prepare as adapt
from prepare_regional_locations import flatten
from prepare_container_yards import required
from check_geometry_terrain_schema import validate_omt


def check():
    stage(check=True)
    adapt(check=True)
    original, registrations, _, _ = sources()
    raw = json.loads((OUT / 'APARTMENT_SHELLS.json').read_text(encoding='utf-8'))
    adapted = json.loads((OUT / 'APARTMENT_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    report = json.loads((OUT / 'APARTMENT_GEOMETRY_REPORT.json').read_text(encoding='utf-8'))
    ar = json.loads((OUT / 'APARTMENT_ADAPTATION_REPORT.json').read_text(encoding='utf-8'))
    aliases = report['nested_aliases']
    assert report['world_maps'] == 31 and report['unique_omt'] == 37
    assert report['nested_definitions'] == 103 and report['nested_identities'] == 60
    assert report['special_cells'] == {'apartment_complex_3x3': 37, 'apartment_complex_3x3_alt': 69,
                                      'apartment_complex_line': 62, 'apartment_complex_U': 77,
                                      'apartment_complex_U_alt': 77}
    assert sum(report['special_cells'].values()) == 322
    assert set(registrations) == TARGETS
    assert not ar['unresolved_typed_refs']

    def rename(v, mapping):
        if isinstance(v, str):
            return mapping.get(v, v)
        if isinstance(v, list):
            return [rename(x, mapping) for x in v]
        if isinstance(v, dict):
            return {k: rename(x, mapping) for k, x in v.items()}
        return v

    # Compare every map alternative, including the 48 weighted apartment-room
    # definitions. Counts alone would miss a duplicated room replacing another.
    def layouts(es, mapping):
        return collections.Counter(json.dumps(rename({k: e[k] for k in
            ('om_terrain', 'nested_mapgen_id', 'weight', 'object') if k in e}, mapping), sort_keys=True)
            for e in es if e['type'] == 'mapgen')

    physical_aliases = {**ar['counterparts'], **ar['isolated_parking_aliases']}
    assert layouts(raw, physical_aliases) == layouts(adapted, {})
    def source_layouts(es, mapping):
        return collections.Counter(json.dumps(rename({
            'identity': e.get('om_terrain', e.get('nested_mapgen_id')),
            'weight': e.get('weight', 1000),
            'rows': e['object'].get('rows'),
            'mapgensize': e['object'].get('mapgensize'),
            'rotation': e['object'].get('rotation', 0),
        }, mapping), sort_keys=True) for e in es if e['type'] == 'mapgen')
    assert source_layouts(original, aliases) == source_layouts(raw, {})
    original_world = [e for e in original if 'om_terrain' in e]
    raw_world = [e for e in raw if 'om_terrain' in e]
    assert len(original_world) == len(raw_world)
    for src, projected in zip(original_world, raw_world):
        assert src['om_terrain'] == projected['om_terrain']
        assert src['object']['rows'] == projected['object']['rows']
        omt = src['om_terrain']
        matrix = [[omt]] if isinstance(omt, str) else [omt] if isinstance(omt[0], str) else omt
        rows = src['object']['rows']
        assert len(rows) == 24 * len(matrix)
        assert all(len(row) == 24 * len(matrix[0]) for row in rows)
    for e in raw:
        if e['type'] == 'overmap_special':
            src = registrations[e['id']]
            assert e['overmaps'] == src['overmaps']
            points = [tuple(c['point']) for c in e['overmaps']]
            assert len(set(points)) == len(points)
            assert e['occurrences'] == [0, 0]
        elif e['type'] == 'mapgen':
            assert not {'items', 'item', 'place_items', 'place_loot', 'monsters', 'place_monsters',
                        'npcs', 'place_npcs', 'vehicles', 'place_vehicles', 'computers'} & e['object'].keys()
    # Six conditional garage stairs retain chunks, coordinates and above-neighbor
    # requirements exactly. This proves conservation, not BN runtime behavior.
    actual = [{'source': e['om_terrain'], 'placement': p} for e in raw_world
              for p in e['object'].get('place_nested', []) if p.get('neighbors')]
    expected = [{'source': e['om_terrain'], 'placement': rename(p, aliases)} for e in original_world
                for p in e['object'].get('place_nested', []) if p.get('neighbors')]
    assert actual == expected == report['conditional_nested_placements']
    assert len(actual) == 6
    declared = {n for e in raw if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    assert all(set(p['placement']['neighbors']['above']) <= declared for p in actual)
    nested = collections.defaultdict(list)
    for e in adapted:
        if 'nested_mapgen_id' in e:
            nested[e['nested_mapgen_id']].append(e)
    seen = set()
    todo = [n for t, n in required([e for e in adapted if 'om_terrain' in e]) if t == 'nested_mapgen']
    while todo:
        n = todo.pop()
        if n in seen or n == 'null':
            continue
        seen.add(n)
        todo += [r for t, r in required(nested[n]) if t == 'nested_mapgen']
    assert sorted(seen) == ar['reachable_nested_identities']
    assert len(seen) == 40 and sum(len(nested[n]) for n in seen) == 83
    assert not ar['reachable_vertical_blockers']
    assert all(not p.get('z', 0) for n in seen for e in nested[n]
               for p in e['object'].get('place_nested', []))
    assert len(report['geometry_issues']) == 2
    assert all(aliases[i['source']] not in seen for i in report['geometry_issues'])
    block = (OUT / 'waterside_adaptation_sources/bn/src/overmap/overmap.h').read_text(encoding='utf-8')
    block = block.split('oter_flags_map = {', 1)[1].split('};', 1)[0]
    flags = set(re.findall(r'\{"([A-Z_]+)", oter_flags::', block))
    for e in adapted:
        if e['type'] == 'overmap_terrain':
            validate_omt(e, flags)
    print('PASS: five apartment layouts, 322 placements, exact rows/weights and six conditional stairs; '
          '83 reachable nested alternatives; no active z-offset blockers; native integration pending')


if __name__ == '__main__':
    check()
