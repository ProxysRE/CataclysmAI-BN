#!/usr/bin/env python3
"""Check LMOE floor composition and the four-site source conservation contract."""
import copy
import json
from prepare_survivor_preview import prepare, OUT, PREFIX, ROOF, TARGETS


def validate_vertical(entries):
    world = {}
    for e in entries:
        value = e.get('om_terrain')
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str): value = value[0]
        if isinstance(value, str): world[value] = e['object']
    nested = {e['nested_mapgen_id']: e['object'] for e in entries if 'nested_mapgen_id' in e}
    assert not world[PREFIX + 'lmoe_under_empty_prepperquest'].get('place_nested')
    assert world[PREFIX + 'lmoe']['place_nested'] == [
        {'chunks': [PREFIX + 'lmoe_exit_prepperquest_n'], 'x': 9, 'y': 17}]
    assert not nested[PREFIX + 'lmoe_exit_prepperquest_n'].get('place_nested')
    roof = world[PREFIX + ROOF]
    assert roof['fill_ter'] == 't_open_air'
    assert roof['rows'] == [' ' * 24] * 24 and roof['terrain'] == {' ': 't_open_air'}
    assert roof['place_nested'] == [{'chunks': [PREFIX + 'lmoe_exit_roof_n'], 'x': 9, 'y': 17}]
    stairs = set()
    for y, row in enumerate(world[PREFIX + 'lmoe_under_empty_prepperquest']['rows']):
        for x, glyph in enumerate(row):
            if world[PREFIX + 'lmoe_under_empty_prepperquest']['terrain'].get(glyph) == 't_stairs_up': stairs.add((x, y))
    surface_stairs = set()
    for y, row in enumerate(nested[PREFIX + 'lmoe_exit_prepperquest_n']['rows']):
        for x, glyph in enumerate(row):
            if nested[PREFIX + 'lmoe_exit_prepperquest_n']['terrain'].get(glyph) == 't_stairs_down': surface_stairs.add((x + 9, y + 17))
    assert stairs == surface_stairs == {(11, 20), (12, 20)}


def check():
    prepare(check=True)
    es = json.loads((OUT / 'SURVIVOR_PREVIEW_SHELL.json').read_text())
    r = json.loads((OUT / 'SURVIVOR_PREVIEW_REPORT.json').read_text())
    source = json.loads((OUT / 'SURVIVOR_ADAPTED_SHELL.json').read_text())
    aliases = r['aliases']
    validate_vertical(es)
    # A missing/misplaced upper stamp must fail even when all floors remain
    # non-null. These probes guard against silently restoring BN's z bug.
    for target in ('lmoe', ROOF):
        bad = copy.deepcopy(es)
        e = next(e for e in bad if e.get('om_terrain') in (PREFIX + target, [PREFIX + target]))
        e['object']['place_nested'][0]['y'] += 1
        try: validate_vertical(bad)
        except AssertionError: pass
        else: raise AssertionError('Shifted source upper stamp accepted')
    def rename(v):
        if isinstance(v, str): return aliases.get(v, v)
        if isinstance(v, list): return [rename(x) for x in v]
        if isinstance(v, dict): return {k: rename(x) for k, x in v.items()}
        return v
    for old in source:
        if old['type'] == 'mapgen':
            key = 'om_terrain' if 'om_terrain' in old else 'nested_mapgen_id'
            matches = [e for e in es if e.get(key) == rename(old[key])]
            if old.get('om_terrain') == ['survivor_forest_camp'] or old.get('nested_mapgen_id', '').startswith(('leather_tent', 'tent_')):
                assert not matches
                continue
            if old.get('om_terrain') == ['cabin_prepper']:
                matches = [e for e in matches if e['object'].get('parameters') == rename(old['object'].get('parameters'))]
            assert len(matches) == 1
            e, = matches
            assert e['object'].get('rows') == old['object'].get('rows')
            assert e.get('weight') == old.get('weight')
            expected = rename(copy.deepcopy(old['object']))
            if old.get('om_terrain') == ['lmoe']: expected['place_nested'] = e['object']['place_nested']
            if old.get('om_terrain') == ['lmoe_under_empty_prepperquest'] or old.get('nested_mapgen_id') == 'lmoe_exit_prepperquest_n': expected.pop('place_nested')
            assert e['object'] == expected
        elif old['type'] == 'overmap_special' and old['id'] in TARGETS:
            e = next(e for e in es if e.get('id') == aliases[old['id']])
            if old['id'] == 'Locked LMOE Shelter':
                assert e['overmaps'][:-1] == rename(old['overmaps'])
                assert e['overmaps'][-1] == {'point': [0, 0, 1], 'overmap': PREFIX + ROOF + '_north'}
            else: assert e['overmaps'] == rename(old['overmaps'])
    assert len(r['special_cells']) == 4 and sum(r['special_cells'].values()) == 16
    assert r['world_maps'] == 10 and r['nested_maps'] == 2
    assert r['fixture_point_count'] == 127
    points = r['fixture_checks'][PREFIX + 'locked_lmoe_shelter']
    for z, terrain in ((-1, 't_stairs_up'), (0, 't_stairs_down')):
        for x in (11, 12):
            assert {'omt_x': 0, 'omt_y': 0, 'x': x, 'y': 20, 'z': z, 'terrain': terrain} in points
    assert {'omt_x': 0, 'omt_y': 0, 'x': 11, 'y': 17, 'z': 1, 'terrain': 't_open_air'} in points
    assert all(not p.get('z', 0) for e in es if e['type'] == 'mapgen' for p in e['object'].get('place_nested', []))
    print('PASS: four source layouts conserved; LMOE stairs align at both cells; shifted upper stamps rejected; all 127 native points retained')


if __name__ == '__main__': check()
