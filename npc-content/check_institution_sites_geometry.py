#!/usr/bin/env python3
"""Check preserved institution staging without claiming native acceptance."""
import json
from prepare_institution_sites_geometry import prepare, sources, ROOT, OUT, TARGETS, PREFIX
from prepare_city_additions_geometry import rename
from prepare_city_additions_preview import matrix
from compare_location_catalog import read_sources


def validate_fixtures(report):
    assert report['fixture_point_count'] == 1983 and report['vertical_link_count'] == 14
    assert {n.removeprefix(PREFIX): len(v) for n, v in report['vertical_links'].items()} == {
        'urban_35_hospital': 8, 'Alcatraz Prison': 4, 'evac_center': 2}
    for name, links in report['vertical_links'].items():
        points = {(p['omt_x'] * 24 + p['x'], p['omt_y'] * 24 + p['y'], p['z']): p['terrain']
                  for p in report['fixture_checks'][name]}
        for p in links:
            assert points[p['x'], p['y'], p['lower_z']] == p['lower']
            assert points[p['x'], p['y'], p['lower_z'] + 1] == p['upper']


def check():
    prepare(check=True)
    files, _, _, _ = sources()
    raw = json.loads((OUT / 'INSTITUTION_SITES_SHELLS.json').read_text())
    entries = json.loads((OUT / 'INSTITUTION_SITES_PREVIEW_SHELL.json').read_text())
    report = json.loads((OUT / 'INSTITUTION_SITES_GEOMETRY_REPORT.json').read_text())
    assert report['native_embedded'] and not report['runtime_validated']
    assert report['source_groups'] == 3 and report['source_placements'] == 599
    assert report['special_cells'] == {'urban_35_hospital': 35, 'Alcatraz Prison': 131, 'evac_center': 433}
    assert report['world_maps'] == 30 and report['nested_definitions'] == 0
    assert not report['geometry_issues']
    assert not report['unresolved_typed_refs']
    soil, puddle, cap = report['physical_definitions']
    assert soil['id'] == PREFIX + 'soil' and soil['move_cost'] == 0 and soil['roof'] == cap['id']
    assert cap['move_cost'] == 2 and cap['looks_like'] == 't_dirt' and cap['bash']['bash_below']
    assert {'WALL', 'SUPPORTS_ROOF', 'NOITEM', 'MINEABLE'} <= set(soil['flags'])
    assert puddle['id'] == PREFIX + 'puddle' and puddle['move_cost'] == 3
    assert puddle['examine_action'] == 'none' and 'liquid_source' not in puddle
    assert 'LIQUID' not in puddle['flags'] # Never imply infinite water collection.
    assert not any(k.startswith('phase_') for k in puddle)
    assert report['context_projection']['source_deep_and_empty_rock']['uniform_terrain'] == 't_rock'
    for name in report['context_projection']['source_context_ids']:
        context = next(e for e in entries if e.get('om_terrain') == PREFIX + name)
        expected = soil['id'] if name in ('solid_earth', 'special_earth') else 't_rock'
        assert context['object'] == {'fill_ter': expected}
        assert next(e for e in entries if e.get('id') == PREFIX + name)['see_cost'] == 5
    assert any(e.get('source_terrain_definition', {}).get('id') == 't_puddle'
               and e['source_terrain_definition']['examine_action'] == 'finite_water_source'
               for e in json.loads((OUT / 'INSTITUTION_SITES_LATER_LAYERS.json').read_text()))
    worlds = [e for e in raw if 'om_terrain' in e]
    assert len(worlds) == len(report['source_conservation'])
    for e, record in zip(worlds, report['source_conservation']):
        src = next(s for s in files[record['path']] if s.get('om_terrain') == record['source_omt']
                   and s.get('weight', 1000) == record['weight'])
        for field in ('rows', 'rotation', 'mapgensize'):
            assert e['object'].get(field) == src['object'].get(field), (record['path'], field)
        assert e.get('weight', 1000) == src.get('weight', 1000)
        grid = matrix(e); rows = e['object']['rows']
        assert len(rows) == 24 * len(grid) and all(len(row) == 24 * len(grid[0]) for row in rows)
    later = json.loads((OUT / 'INSTITUTION_SITES_LATER_LAYERS.json').read_text())
    catalog, _ = read_sources()
    regs = {e['id']: e for path, text in catalog.items() if path.startswith('dda/')
            for e in json.loads(text) if e.get('type') in ('overmap_special', 'city_building') and e.get('id') in TARGETS}
    for name, src in regs.items():
        special = next(e for e in entries if e.get('id') == PREFIX + name)
        # Preserve rock/lake/earth context cells and connection constraints;
        # unresolved counterparts are tracked, never removed to close the graph.
        expected = rename(src['overmaps'], report['isolated_ids'])
        expected = [{k: v for k, v in cell.items() if k not in ('camp', 'camp_name')} for cell in expected]
        assert special['overmaps'] == expected
        assert any(e.get('source_registration') == src for e in later), name
        for cell in src['overmaps']:
            for field in ('camp', 'camp_name'):
                if field in cell: assert any(e.get('source') == name and e.get('point') == cell['point'] and e.get('field') == field and e.get('value') == cell[field] for e in later)
        assert special['occurrences'] == [0, 0]
        assert sorted({c['point'][2] for c in src['overmaps'] if 'overmap' in c}) == report['source_z_levels'][name]
    assert all(not e['object'].get('place_nested') and not e['object'].get('nested') for e in entries if e['type'] == 'mapgen')
    bodybags = [e for es in files.values() for e in es if e.get('nested_mapgen_id') == 'pile_bodybag_corpses']
    assert len(bodybags) == 1 and set(bodybags[0]['object']) == {'mapgensize', 'place_items'}
    # The full late-only definition and the 70/30 source binding remain in
    # authenticated sources; geometry projects that branch to null only.
    assert bodybags[0]['object']['mapgensize'] == [3, 3]
    from prepare_institution_sites_preview import prepare as fixtures
    fixtures(check=True)
    fixture_report = json.loads((OUT / 'INSTITUTION_SITES_PREVIEW_REPORT.json').read_text())
    validate_fixtures(fixture_report)
    # A missing lower endpoint must fail even if totals in the report stay fixed.
    import copy
    bad = copy.deepcopy(fixture_report)
    key = PREFIX + 'urban_35_hospital'
    link = bad['vertical_links'][key][0]
    point = next(p for p in bad['fixture_checks'][key]
                 if (p['omt_x'] * 24 + p['x'], p['omt_y'] * 24 + p['y'], p['z']) ==
                    (link['x'], link['y'], link['lower_z']))
    point['terrain'] = 't_floor'
    try: validate_fixtures(bad)
    except AssertionError: pass
    else: raise AssertionError('Broken vertical institution endpoint accepted')
    print('PASS: three institution groups physically closed; 599 placements /30 source maps preserved; solid earth and finite-water deferral explicit; no native acceptance claim')


if __name__ == '__main__': check()
