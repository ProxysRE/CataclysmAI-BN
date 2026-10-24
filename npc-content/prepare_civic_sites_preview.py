#!/usr/bin/env python3
"""Prepare seven civic fixtures without modifying the active native candidate."""
import argparse
import collections
import json
from prepare_civic_sites_geometry import prepare as stage, OUT
from prepare_city_additions_preview import matrix, fixed
from prepare_container_yards import required


def prepare(check=False):
    stage(check=True)
    entries = json.loads((OUT / 'CIVIC_SITES_PREVIEW_SHELL.json').read_text())
    nested = collections.defaultdict(list)
    for e in entries:
        if 'nested_mapgen_id' in e: nested[e['nested_mapgen_id']].append(e)
    variants = collections.defaultdict(list); exclusions = []
    for e in entries:
        if 'om_terrain' not in e: continue
        o = e['object']; grid = matrix(e); mask = set()
        assert o.get('rotation', 0) == 0 and 'predecessor_mapgen' not in o
        def footprint(piece, xr, yr):
            refs = {n for t, n in required([{'type': 'mapgen', 'object': {'place_nested': [piece]}}]) if t == 'nested_mapgen'}
            sizes = [p['object']['mapgensize'] for n in refs for p in nested[n]]
            radius = max((max(size) for size in sizes), default=0)
            xr = xr if isinstance(xr, list) else [xr, xr]
            yr = yr if isinstance(yr, list) else [yr, yr]
            for y in range(yr[0], yr[-1] + radius):
                for x in range(xr[0], xr[-1] + radius): mask.add((x, y))
        for p in o.get('place_nested', []):
            assert not p.get('z', 0)
            footprint(p, p['x'], p['y'])
        for y, row in enumerate(o['rows']):
            for x, glyph in enumerate(row):
                if glyph in o.get('nested', {}): footprint(o['nested'][glyph], x, y)
        for gy, row in enumerate(grid):
            for gx, name in enumerate(row):
                points = set(); controls = []
                for y in range(24):
                    for x in range(24):
                        px, py = gx * 24 + x, gy * 24 + y
                        terrain = fixed(o.get('terrain', {}).get(o['rows'][py][px], o.get('fill_ter')))
                        if terrain and terrain != 't_null' and not terrain.startswith('t_region_') and (px, py) not in mask:
                            controls.append((x, y, terrain))
                        if not terrain or not any(part in terrain for part in ('stairs', 'ladder', 'ramp', 'elevator', 'slope', 'door', 'reader')): continue
                        if (px, py) in mask:
                            exclusions.append({'omt': name, 'x': x, 'y': y, 'terrain': terrain,
                                               'reason': 'Possible source nested damage/roof overlay'})
                            continue
                        points.add((x, y, terrain))
                # Small single-storey buildings need no invented staircase.
                # Five spread source terrain samples also cover their fixed
                # shell/roof surfaces when all doors are random alternatives.
                if controls:
                    points.update(controls[i] for i in sorted({0, len(controls)//4, len(controls)//2, 3*len(controls)//4, len(controls)-1}))
                variants[name].append(points)
    navigation = {n: sorted(set.intersection(*ps)) for n, ps in variants.items()}
    fixture = {}
    for e in entries:
        if e['type'] != 'overmap_special': continue
        checks = []
        for cell in e['overmaps']:
            name = cell['overmap']; turns = 0
            for index, suffix in enumerate(('_north', '_east', '_south', '_west')):
                if name.endswith(suffix): name = name[:-len(suffix)]; turns = index; break
            for x, y, terrain in navigation[name]:
                for _ in range(turns): x, y = 23 - y, x
                checks.append({'omt_x': cell['point'][0], 'omt_y': cell['point'][1],
                               'x': x, 'y': y, 'z': cell['point'][2], 'terrain': terrain})
        fixture[e['id']] = checks
    assert len(fixture) == 7 and all(fixture.values())
    report = {'status': 'civic_native_fixtures_prepared_not_embedded', 'native_embedded': False, 'runtime_validated': False,
              'fixture_checks': fixture, 'fixture_point_count': sum(map(len, fixture.values())),
              'random_overlay_navigation_exclusions': exclusions, 'overlay_exclusion_count': len(exclusions),
              'layout_cases': 7, 'source_placements': 239,
              'limits': ['Only fixed source terrain outside every possible nested overlay receives exact expectations',
                         'All own cells must retain full empty-loot and non-null checks when embedded',
                         'No full traversal, elevator operation or natural placement claim']}
    path = OUT / 'CIVIC_SITES_PREVIEW_REPORT.json'; text = json.dumps(report, indent=2, ensure_ascii=True) + '\n'
    if check: assert path.read_text() == text, path
    else: path.write_text(text)
    print(f'Civic fixtures prepared: seven layouts /239 cells, {report["fixture_point_count"]} stable geometry/access points; native embedding pending')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--check', action='store_true'); prepare(p.parse_args().check)
