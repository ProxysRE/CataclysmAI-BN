#!/usr/bin/env python3
"""Check seven city shells, correlated library states and native transform data."""
import copy
import hashlib
import json
import re
from prepare_city_additions_geometry import prepare, sources, OUT, ROOT, PREFIX, TARGETS
from prepare_regional_locations import flatten
from export_bn_ids import read_cache
from check_geometry_terrain_schema import validate as validate_terrain, validate_omt


def validate_library(entries):
    for variant in ('normal', 'vandalized'):
        e = next(e for e in entries if e.get('id') == PREFIX + 'urban_library_' + variant)
        assert len(e['overmaps']) == 12
        for cell in e['overmaps']:
            x, y, z = cell['point']
            assert x in (-1, 0) and y in (0, 1) and z in (0, 1, 2)
            if z < 2:
                assert '_' + variant + '_north' in cell['overmap']
                assert not any('_' + other + '_north' in cell['overmap'] for other in ('normal', 'vandalized') if other != variant)
            else:
                assert 'urban_library_roof_' in cell['overmap']


def check():
    prepare(check=True)
    files, shared, palettes, evidence, runtime = sources()
    entries = json.loads((OUT / 'CITY_ADDITIONS_PREVIEW_SHELL.json').read_text())
    raw = json.loads((OUT / 'CITY_ADDITIONS_SHELLS.json').read_text())
    report = json.loads((OUT / 'CITY_ADDITIONS_GEOMETRY_REPORT.json').read_text())
    assert report['source_sites'] == sorted(TARGETS)
    assert (report['source_placements'], report['preview_cases'], report['preview_placements']) == (25, 8, 37)
    assert (report['world_maps'], report['nested_definitions'], report['transform_count']) == (19, 18, 5)
    assert not report['unresolved_typed_refs'] and not report['geometry_issues']
    assert not report['native_embedded'] and not report['runtime_validated']
    validate_library(entries)
    bad = copy.deepcopy(entries)
    e = next(e for e in bad if e.get('id') == PREFIX + 'urban_library_normal')
    cell = next(c for c in e['overmaps'] if c['point'][2] == 1)
    cell['overmap'] = cell['overmap'].replace('_normal_north', '_vandalized_north')
    try: validate_library(bad)
    except AssertionError: pass
    else: raise AssertionError('Mixed whole-building library state accepted')
    worlds = [e for e in raw if 'om_terrain' in e]
    assert len(worlds) == len(report['source_conservation'])
    for e, record in zip(worlds, report['source_conservation']):
        old = next(x for x in files[record['source_path']] if x.get('om_terrain') == record['source_omt']
                   and x.get('weight', 1000) == record['weight'])
        # Repeated library layouts share a terrain ID but have different
        # weights, so each complete original row/weight pair is matched.
        assert e['object']['rows'] == old['object']['rows']
        assert e.get('weight', 1000) == old.get('weight', 1000)
        value = e['om_terrain']; grid = [[value]] if isinstance(value, str) else [value] if isinstance(value[0], str) else value
        assert len(e['object']['rows']) == 24 * len(grid)
        assert all(len(row) == 24 * len(grid[0]) for row in e['object']['rows'])
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    transforms = {e['id']: e for e in entries if e['type'] == 'ter_furn_transform'}
    referenced = {p['transform'] for e in entries if e['type'] == 'mapgen'
                  for p in e['object'].get('place_ter_furn_transforms', [])}
    assert referenced == transforms.keys() and len(referenced) == 5
    for projection in report['transform_projection']:
        source = projection['source_transform']; output = transforms[PREFIX + source['id']]
        expected = [{'result': r['result'], 'valid_terrain': [n for n in r['valid_terrain'] if ('terrain', n) in core], 'valid_flags': []}
                    for r in source['terrain'] if any(('terrain', n) in core for n in r['valid_terrain'])]
        assert output['terrain'] == expected
        for rule in output['terrain']:
            assert ('terrain', rule['result']) in core
    reader = next(e for e in entries if e.get('id') == PREFIX + 'anduril_reader')
    validate_terrain(reader)
    original = report['Anduril_reader']['source_definition']
    for field in ('name', 'description', 'symbol', 'color'): assert reader[field] == original[field]
    assert reader['examine_action'] == 'none'
    stock = next(e for e in shared['bn/data/json/furniture_and_terrain/terrain-mechanisms.json'] if e.get('id') == 't_card_science')
    changed = {'id', 'name', 'description', 'symbol', 'color', 'examine_action'}
    assert {k: v for k, v in reader.items() if k not in changed} == {k: v for k, v in stock.items() if k not in changed}
    folder = OUT / 'waterside_adaptation_sources'; m = json.loads((folder / 'SOURCE_MANIFEST.json').read_text())
    path = 'bn/src/overmap/overmap.h'; b = (folder / path).read_bytes(); assert hashlib.sha256(b).hexdigest() == m['files'][path]
    block = b.decode().split('oter_flags_map = {', 1)[1].split('};', 1)[0]
    flags = set(re.findall(r'\{"([A-Z_]+)", oter_flags::', block))
    for e in entries:
        if e['type'] == 'overmap_terrain': validate_omt(e, flags); assert e['extras'] == ''
        if e['type'] == 'overmap_special': assert e['occurrences'] == [0, 0]
        if e['type'] == 'mapgen': assert all(not p.get('z', 0) for p in e['object'].get('place_nested', []))
    print('PASS: seven source sites /eight coherent debug cases; 37 placements, all source rows/weights, five door/window transforms and physical-only Anduril reader conserved')


if __name__ == '__main__': check()
