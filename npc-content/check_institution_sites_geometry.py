#!/usr/bin/env python3
"""Check preserved institution staging without claiming native acceptance."""
import json
from prepare_institution_sites_geometry import prepare, sources, ROOT, OUT, TARGETS, PREFIX
from prepare_city_additions_geometry import rename
from prepare_city_additions_preview import matrix
from compare_location_catalog import read_sources


def check():
    prepare(check=True)
    files, _, _, _ = sources()
    raw = json.loads((OUT / 'INSTITUTION_SITES_SHELLS.json').read_text())
    entries = json.loads((OUT / 'INSTITUTION_SITES_PREVIEW_SHELL.json').read_text())
    report = json.loads((OUT / 'INSTITUTION_SITES_GEOMETRY_REPORT.json').read_text())
    assert not report['native_embedded'] and not report['runtime_validated']
    assert report['source_groups'] == 3 and report['source_placements'] == 599
    assert report['special_cells'] == {'urban_35_hospital': 35, 'Alcatraz Prison': 131, 'evac_center': 433}
    assert report['world_maps'] == 30 and report['nested_definitions'] == 0
    assert not report['geometry_issues']
    assert report['unresolved_typed_refs'] == [
        ['overmap_terrain', 'solid_earth'], ['overmap_terrain', 'special_deep_rock'],
        ['overmap_terrain', 'special_earth'], ['overmap_terrain', 'special_rock'],
        ['overmap_terrain_abstract', 'road_abstract'], ['terrain', 't_puddle']]
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
    print('PASS: three institution groups staged; 599 placements /30 maps preserved; six explicit physical/schema dependencies remain; no native acceptance claim')


if __name__ == '__main__': check()
