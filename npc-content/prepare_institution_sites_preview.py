#!/usr/bin/env python3
"""Prepare oriented institution access fixtures, including every context cell."""
import argparse
import collections
import json
from prepare_institution_sites_geometry import prepare as stage, OUT, PREFIX, strip_direction
from prepare_city_additions_preview import matrix, fixed


def prepare(check=False):
    stage(check=True)
    entries = json.loads((OUT / 'INSTITUTION_SITES_PREVIEW_SHELL.json').read_text())
    variants = collections.defaultdict(list)
    for e in entries:
        if 'om_terrain' not in e: continue
        obj = e['object']
        assert not obj.get('rotation', 0) and not obj.get('predecessor_mapgen')
        assert not any(obj.get(k) for k in ('set', 'place_terrain', 'place_nested', 'nested'))
        for gy, row in enumerate(matrix(e)):
            for gx, name in enumerate(row):
                cells = {}
                for y in range(24):
                    for x in range(24):
                        glyph = obj['rows'][gy * 24 + y][gx * 24 + x] if 'rows' in obj else None
                        ter = fixed(obj.get('terrain', {}).get(glyph, obj.get('fill_ter')))
                        if ter and ter != 't_null' and not ter.startswith('t_region_'):
                            cells[x, y] = ter
                variants[name].append(cells)
    stable = {}
    for name, alternatives in variants.items():
        stable[name] = {p: t for p, t in alternatives[0].items()
                        if all(a.get(p) == t for a in alternatives[1:])}
    fixtures = {}; vertical = {}; air_excluded = []
    for special in (e for e in entries if e['type'] == 'overmap_special'):
        world = {}; points = []
        for cell in special['overmaps']:
            if 'overmap' not in cell: continue # Constraint-only route entry remains in registration.
            original = cell['overmap']; name = strip_direction(original)
            turns = next((i for i, d in enumerate(('north', 'east', 'south', 'west'))
                          if original.endswith('_' + d)), 0)
            omx, omy, z = cell['point']
            rotated = {}
            for (x, y), terrain in stable.get(name, {}).items():
                for _ in range(turns): x, y = 23 - y, x
                rotated[x, y] = terrain
                world[omx * 24 + x, omy * 24 + y, z] = terrain
            controls = [(x, y, t) for (x, y), t in sorted(rotated.items()) if t != 't_open_air']
            selected = {(x, y, t) for x, y, t in controls
                        if any(k in t for k in ('stairs', 'ladder', 'ramp', 'elevator', 'slope', 'door', 'reader'))}
            if controls:
                selected.update(controls[i] for i in {0, len(controls)//4, len(controls)//2,
                                                     3*len(controls)//4, len(controls)-1})
            for x, y, t in sorted(selected):
                points.append(dict(omt_x=omx, omt_y=omy, x=x, y=y, z=z, terrain=t))
            # Exact air requires roof resolution. No air check is silently
            # assigned where lower source/regional/stock context is uncertain.
            air_excluded += [dict(special=special['id'], omt=original, point=[x, y, z])
                             for (x, y), t in rotated.items() if t == 't_open_air']
        fixtures[special['id']] = points
        links = []
        for (x, y, z), terrain in sorted(world.items()):
            if not any(k in terrain for k in ('stairs_up', 'ladder_up', 'slope_up')): continue
            upper = world.get((x, y, z + 1), '')
            if any(k in upper for k in ('stairs_down', 'ladder_down', 'slope_down')):
                links.append(dict(x=x, y=y, lower_z=z, lower=terrain, upper=upper))
        vertical[special['id']] = links
    assert len(fixtures) == 3 and all(fixtures.values())
    report = dict(status='institution_fixtures_embedded_pending_windows',
                  native_embedded=True, runtime_validated=False,
                  layout_cases=3, source_placements=599, fixture_checks=fixtures,
                  fixture_point_count=sum(map(len, fixtures.values())), vertical_links=vertical,
                  vertical_link_count=sum(map(len, vertical.values())),
                  unsampled_source_air_count=len(air_excluded),
                  limits=['Every own context tile must receive non-null and empty-loot checks when embedded',
                          'Fixed terrain expectations intersect all variants; hospital south rotation preserved',
                          'Source air omitted from fixed sampling because BN can create automatic roofs',
                          'All fixed doors and stairs retained; matched vertical endpoints checked on both floors',
                          'No full player traversal or interaction claim'])
    path = OUT / 'INSTITUTION_SITES_PREVIEW_REPORT.json'
    text = json.dumps(report, indent=2) + '\n'
    if check: assert path.read_text() == text, path
    else: path.write_text(text)
    print(f'Institution fixtures: 3 layouts /599 cells, {report["fixture_point_count"]} fixed points, {report["vertical_link_count"]} matched vertical links')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true'); prepare(p.parse_args().check)
