#!/usr/bin/env python3
"""Isolate four survivor/Lacroix sites and relocate fixed LMOE upper stamps."""
import argparse
import collections
import copy
import json
from adapt_survivor_geometry import prepare as adapt
from prepare_survivor_geometry import OUT, ROOT
from prepare_regional_locations import flatten, index_entries, BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

TARGETS = {'Cabin_prepper', 'cabin_liam', 'Locked LMOE Shelter', 'cemetery_lacroix'}
NESTS = {'lmoe_exit_prepperquest_n', 'lmoe_exit_roof_n'}
PREFIX = 'dda_geo_survivor_'
ROOF = 'lmoe_locked_exit_roof'


def matrix(e):
    value = e['om_terrain']
    return [[value]] if isinstance(value, str) else [value] if isinstance(value[0], str) else value


def prepare(check=False):
    adapt(check=True)
    full = json.loads((OUT / 'SURVIVOR_ADAPTED_SHELL.json').read_text())
    selected = []
    deferred = []
    for source in full:
        e = copy.deepcopy(source)
        if e['type'] == 'overmap_special' and e['id'] not in TARGETS:
            continue
        if e['type'] == 'overmap_terrain' and e['id'] == ['survivor_forest_camp']:
            continue
        if e['type'] == 'mapgen':
            if e.get('om_terrain') == ['survivor_forest_camp']:
                continue
            if 'nested_mapgen_id' in e and e['nested_mapgen_id'] not in NESTS:
                continue
            assert not isinstance(e.get('weight'), dict)
        if e['type'] == 'overmap_terrain' and 'travel_cost_type' in e:
            deferred.append({'source': e['id'], 'field': 'travel_cost_type', 'value': e.pop('travel_cost_type')})
        selected.append(e)
    underground = next(e for e in selected if e.get('om_terrain') == ['lmoe_under_empty_prepperquest'])
    surface = next(e for e in selected if e.get('om_terrain') == ['lmoe'])
    exit_stamp = next(e for e in selected if e.get('nested_mapgen_id') == 'lmoe_exit_prepperquest_n')
    lower_place, = underground['object'].pop('place_nested')
    upper_place, = exit_stamp['object'].pop('place_nested')
    assert lower_place == {'chunks': ['lmoe_exit_prepperquest_n'], 'x': 9, 'y': 17, 'z': 1}
    assert upper_place == {'chunks': ['lmoe_exit_roof_n'], 'x': 0, 'y': 0, 'z': 1}
    assert exit_stamp['object'].get('rotation', 0) == 0
    assert not surface['object'].get('place_nested')
    surface['object']['place_nested'] = [{k: copy.deepcopy(v) for k, v in lower_place.items() if k != 'z'}]
    selected += [
        {'type': 'overmap_terrain', 'id': ROOF, 'name': 'LMOE shelter roof',
         'sym': '+', 'color': 'red', 'see_cost': 0},
        {'type': 'mapgen', 'method': 'json', 'om_terrain': ROOF,
         'object': {'fill_ter': 't_open_air', 'rows': [' ' * 24] * 24,
                    'terrain': {' ': 't_open_air'},
                    'place_nested': [{'chunks': upper_place['chunks'],
                                      'x': lower_place['x'] + upper_place['x'],
                                      'y': lower_place['y'] + upper_place['y']}]}}
    ]
    special = next(e for e in selected if e.get('id') == 'Locked LMOE Shelter')
    assert special['overmaps'] == [{'point': [0, 0, 0], 'overmap': 'lmoe_north'},
                                  {'point': [0, 0, -1], 'overmap': 'lmoe_under_empty_prepperquest_north'}]
    special['overmaps'].append({'point': [0, 0, 1], 'overmap': ROOF + '_north'})
    own_omt = {n for e in selected if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    aliases = {n: PREFIX + n for n in sorted(own_omt | NESTS)}
    for n in sorted(own_omt):
        for direction in ('north', 'east', 'south', 'west'):
            aliases[n + '_' + direction] = PREFIX + n + '_' + direction
    aliases.update({n: PREFIX + n.replace(' ', '_').lower() for n in sorted(TARGETS)})

    def rename(value):
        if isinstance(value, str): return aliases.get(value, value)
        if isinstance(value, list): return [rename(v) for v in value]
        if isinstance(value, dict): return {k: rename(v) for k, v in value.items()}
        return value

    entries = rename(selected)
    for e in entries:
        if e['type'] == 'overmap_terrain': e['extras'] = ''
    own = index_entries(entries)
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    generated = {('overmap_terrain', 'rural_road_forest_north')}
    assert not (own - BUILTIN_IDS) & (core | mods)
    missing = sorted(required(entries) - own - core - generated)
    assert not missing, missing
    assert all(not p.get('z', 0) for e in entries if e['type'] == 'mapgen' for p in e['object'].get('place_nested', []))
    # Project deterministic access/door/roof points. Repeated map variants
    # contribute only their common points, retaining palette correlations.
    variants = collections.defaultdict(list)
    nested = {e['nested_mapgen_id']: e for e in entries if 'nested_mapgen_id' in e}
    for e in entries:
        if 'om_terrain' not in e: continue
        o = e['object']; grid = matrix(e); points = collections.defaultdict(set)
        for y, row in enumerate(o['rows']):
            for x, glyph in enumerate(row):
                terrain = o.get('terrain', {}).get(glyph)
                if isinstance(terrain, str) and any(word in terrain for word in ('stairs', 'ladder', 'ramp', 'slope', 'door', 'railing')):
                    points[grid[y // 24][x // 24]].add((x % 24, y % 24, terrain))
        for p in o.get('place_nested', []):
            assert set(p) == {'chunks', 'x', 'y'} and len(p['chunks']) == 1
            no = nested[p['chunks'][0]]['object']
            for ny, row in enumerate(no['rows']):
                for nx, glyph in enumerate(row):
                    terrain = no['terrain'].get(glyph)
                    if isinstance(terrain, str) and not terrain.startswith('t_region_'):
                        x, y = p['x'] + nx, p['y'] + ny
                        assert 0 <= x < 24 and 0 <= y < 24
                        points[grid[0][0]].add((x, y, terrain))
        for row in grid:
            for name in row: variants[name].append(points[name])
    navigation = {name: sorted(set.intersection(*points)) for name, points in variants.items()}
    fixture_checks = {}
    for e in entries:
        if e['type'] != 'overmap_special': continue
        fixture_checks[e['id']] = []
        for cell in e['overmaps']:
            if 'overmap' not in cell: continue
            name = cell['overmap']; turns = 0
            for index, suffix in enumerate(('_north', '_east', '_south', '_west')):
                if name.endswith(suffix): name = name[:-len(suffix)]; turns = index; break
            for x, y, terrain in navigation.get(name, []):
                for _ in range(turns): x, y = 23 - y, x
                fixture_checks[e['id']].append({'omt_x': cell['point'][0], 'omt_y': cell['point'][1],
                    'x': x, 'y': y, 'z': cell['point'][2], 'terrain': terrain})
    report = {'status': 'four_site_preview_embedded_pending_windows_generation',
              'native_embedded': True, 'runtime_validated': False,
              'aliases': aliases, 'unresolved_typed_refs': missing,
              'special_cells': {e['id']: sum('overmap' in c for c in e['overmaps']) for e in entries if e['type'] == 'overmap_special'},
              'world_maps': sum('om_terrain' in e for e in entries), 'nested_maps': len(nested),
              'LMOE_vertical_relocation': [
                  {'from_z': -1, 'to_z': 0, 'x': 9, 'y': 17, 'nested': aliases['lmoe_exit_prepperquest_n']},
                  {'from_z': 0, 'to_z': 1, 'x': 9, 'y': 17, 'nested': aliases['lmoe_exit_roof_n']}],
              'fixture_checks': fixture_checks,
              'fixture_point_count': sum(map(len, fixture_checks.values())),
              'generated_external_omt': ['rural_road_forest_north'], 'deferred_registration_fields': deferred,
              'limits': ['Forest camp and all tent variants remain in full staging, excluded from this preview',
                         'LMOE roof is an explicit additional OMT derived from source z=1 nesting; no invented geometry',
                         'LMOE quest sign and door-unlocking quest remain in later layers',
                         'No natural placement, full traversal or new completion credit before native generation']}
    for name, value in [('SURVIVOR_PREVIEW_SHELL.json', entries), ('SURVIVOR_PREVIEW_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check: assert path.read_text() == text, path
        else: path.write_text(text)
    print(f'PASS: four isolated sites, {sum(report["special_cells"].values())} placements; {report["fixture_point_count"]} native expectations; LMOE upper stamps relocated explicitly')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
