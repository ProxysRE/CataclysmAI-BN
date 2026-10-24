#!/usr/bin/env python3
"""Check all five civic groups against authenticated source layouts."""
import json
import copy
import re
from prepare_civic_sites_geometry import prepare, sources, OUT, ROOT, TARGETS, PREFIX
from prepare_civic_sites_preview import prepare as fixtures
from prepare_city_additions_preview import matrix
from prepare_city_additions_geometry import rename
from prepare_regional_locations import flatten
from compare_location_catalog import read_sources
from check_geometry_terrain_schema import validate, validate_omt


def validate_world_ids(entries):
    own = {n for e in entries if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    mapped = {n for e in entries if 'om_terrain' in e for n in flatten(e['om_terrain'])} - {'null'}
    assert own == mapped, ('Unused or undefined world mapgen', sorted(mapped - own), sorted(own - mapped))


def validate_vertical(fixtures):
    counts = {}
    for name, points in fixtures.items():
        terrain = {(p['omt_x'] * 24 + p['x'], p['omt_y'] * 24 + p['y'], p['z']): p['terrain'] for p in points}
        counts[name.removeprefix(PREFIX)] = sum(t in ('t_stairs_up', 't_ladder_up') and
            terrain.get((x, y, z + 1)) in ('t_stairs_down', 't_ladder_down', 't_stairs_updown')
            for (x, y, z), t in terrain.items())
    assert counts == {'hotel_1': 10, 'hotel_2': 10, 'hotel_3': 10, 'office_tower': 2,
                      'shopping_plaza': 0, 'zoo': 2, 'stadium': 16}, counts


def check():
    prepare(check=True); fixtures(check=True)
    files, _, _, _ = sources()
    raw = json.loads((OUT / 'CIVIC_SITES_SHELLS.json').read_text())
    entries = json.loads((OUT / 'CIVIC_SITES_PREVIEW_SHELL.json').read_text())
    report = json.loads((OUT / 'CIVIC_SITES_GEOMETRY_REPORT.json').read_text())
    points = json.loads((OUT / 'CIVIC_SITES_PREVIEW_REPORT.json').read_text())
    assert (report['source_groups'], report['world_maps'], report['nested_definitions']) == (5, 28, 11)
    assert report['source_placements'] == 239 and not report['geometry_issues'] and not report['unresolved_typed_refs']
    assert report['native_embedded'] and not report['runtime_validated']
    worlds = [e for e in raw if 'om_terrain' in e]
    assert len(worlds) == len(report['source_conservation'])
    for e, record in zip(worlds, report['source_conservation']):
        source = next(s for s in files[record['path']] if s.get('om_terrain') == record['source_omt']
                      and s.get('weight', 1000) == record['weight'])
        for field in ('rows', 'rotation', 'mapgensize'): assert e['object'].get(field) == source['object'].get(field)
        assert e.get('weight', 1000) == source.get('weight', 1000)
        grid = matrix(e); rows = e['object']['rows']
        assert len(rows) == 24 * len(grid) and all(len(row) == 24 * len(grid[0]) for row in rows)
    catalog, _ = read_sources()
    regs = {e['id']: e for path, text in catalog.items() if path.startswith('dda/')
            for e in json.loads(text) if e.get('type') == 'city_building' and e.get('id') in TARGETS}
    own = {n for e in entries if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    mapped = {n for e in entries if 'om_terrain' in e for n in flatten(e['om_terrain'])} - {'null'}
    unused = report['unplaced_grid_aliases']
    assert len(unused) == 2 and all(p['preview_mapgen_id'] == 'null' for p in unused)
    assert own == mapped and not any(n.startswith(PREFIX + 'unused_grid_') for n in mapped)
    validate_world_ids(entries)
    bad = copy.deepcopy(entries)
    next(e for e in bad if 'om_terrain' in e)['om_terrain'] = [[PREFIX + 'unused_grid_0']]
    try: validate_world_ids(bad)
    except AssertionError: pass
    else: raise AssertionError('Unused private placeholder generator accepted')
    for name, src in regs.items():
        special = next(e for e in entries if e.get('id') == PREFIX + name)
        assert special['occurrences'] == [0, 0]
        expected = rename(src['overmaps'], report['isolated_ids'])
        assert special['overmaps'] == expected
        assert len(special['overmaps']) == report['special_cells'][name]
        assert sorted({c['point'][2] for c in special['overmaps']}) == report['source_z_levels'][name]
        for c in special['overmaps']: assert c['overmap'].removesuffix('_north') in own
        checks = points['fixture_checks'][PREFIX + name]
        assert checks and len(checks) < 8000
        coordinates = {tuple(c['point']) for c in special['overmaps']}
        assert all((p['omt_x'], p['omt_y'], p['z']) in coordinates and 0 <= p['x'] < 24 and 0 <= p['y'] < 24 for p in checks)
    assert points['fixture_point_count'] == sum(map(len, points['fixture_checks'].values())) and points['layout_cases'] == 7
    assert all(e['point']['terrain'] == 't_open_air' and e['lower_source_terrain'] for e in points['automatic_roof_air_exclusions'])
    assert points['fixture_point_count'] + len(points['automatic_roof_air_exclusions']) == 2445
    validate_vertical(points['fixture_checks'])
    broken = copy.deepcopy(points['fixture_checks'])
    for p in broken[PREFIX + 'hotel_1']:
        if p['terrain'] == 't_stairs_down': p['terrain'] = 't_floor'
    try: validate_vertical(broken)
    except AssertionError: pass
    else: raise AssertionError('Broken hotel vertical links accepted')
    registry = (OUT / 'waterside_adaptation_sources/bn/src/overmap/overmap.h').read_text()
    flags = set(re.findall(r'\{"([A-Z_]+)", oter_flags::', registry.split('oter_flags_map = {', 1)[1].split('};', 1)[0]))
    for e in entries:
        if e['type'] == 'overmap_terrain':
            validate_omt(e, flags); assert e['extras'] == ''
            assert 'post_process_generators' not in e
            for field in ('delete', 'extend'): assert 'post_process_generators' not in e.get(field, {})
        elif e['type'] == 'terrain': validate(e)
        elif e['type'] == 'mapgen':
            assert not any(p.get('z', 0) for p in e['object'].get('place_nested', []))
            assert not set(e['object']) & {'place_items', 'items', 'place_monsters', 'monsters', 'place_npcs', 'vehicles', 'computers'}
    roof_source = next(e for e in json.loads((OUT / 'frontier_adaptation_sources/dda/data/json/furniture_and_terrain/terrain-roofs.json').read_text()) if e.get('id') == 't_wood_roof')
    roof = next(e for e in entries if e.get('id') == PREFIX + 'wood_roof')
    assert roof == rename(roof_source, report['physical_aliases'])
    assert report['physical_aliases']['t_retractable_gate_l'] == 't_chaingate_l'
    print('PASS: five civic groups /seven layouts, 239 exact source placements, 28 world maps, 11 structural nests and 2404 fixed fixture points; Windows generation pending')


if __name__ == '__main__': check()
