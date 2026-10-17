#!/usr/bin/env python3
"""Verify exact BN preservation and continuous relocated DDA tower geometry."""
import copy
import json
from pathlib import Path
import tempfile

from compare_location_catalog import read_sources
from prepare_radio_stations import CITY, MAP, OFFSETS, prepare, prepare_data, shifted, sources


def check():
    outputs, payload, report = prepare(check=True)
    files = sources()
    baseline = json.loads(files['bn/station_radio.json'])
    merged = json.loads(outputs[MAP])
    assert len(merged) == len(baseline) == 4
    for old, new in zip(baseline, merged):
        old, new = copy.deepcopy(old), copy.deepcopy(new)
        old['object'].pop('rows')
        new['object'].pop('rows')
        if isinstance(old['om_terrain'], str):
            for key in ('R', 'a', ',', '≷'):
                del new['object']['terrain'][key]
        assert old == new  # Including computers, stock, weight and roof encounters.
    maps = {e['om_terrain']: e['object'] for e in payload[1:]}
    for variant, info in report['changes'].items():
        x, y = info['ladder_xy']
        assert info['BN_computers_preserved']
        ground = next(e['object'] for e in merged if e['om_terrain'] == [variant])
        roof_id = 'station_radio_roof' + ('_1' if variant.endswith('_1') else '')
        roof = next(e['object'] for e in merged if e['om_terrain'] == roof_id)
        assert ground['rows'][y][x] == '<'
        assert roof['rows'][y][x] == '≷'
        for suffix in ('even', 'odd', 'top'):
            obj = maps[variant + '_tower_' + suffix]
            assert obj['rows'][y][x] == ('v' if suffix == 'top' else '≷')
            assert len(obj['rows']) == 24 and all(len(row) == 24 for row in obj['rows'])
            for entry in obj.get('place_nested', []):
                # Stock encounters are below the access cell, never over it.
                assert entry['y'] > y and entry['x'] >= 0
        old_ground = next(e['object'] for e in baseline if e['om_terrain'] == [variant])
        allowed = {tuple(p) for p in info['old_footing_cells'] + info['new_footing_cells']} | {(x, y)}
        for yy, (old, new) in enumerate(zip(old_ground['rows'], ground['rows'])):
            for xx, (a, b) in enumerate(zip(old, new)):
                assert a == b or (xx, yy) in allowed
    catalog, _ = read_sources()
    old_city, new_city = json.loads(catalog['bn/' + CITY]), json.loads(outputs[CITY])
    for old, new in zip(old_city, new_city):
        if old.get('id') in OFFSETS:
            assert new == dict(old, overmaps=new['overmaps'])
            assert new['overmaps'][:2] == old['overmaps']
            assert [c['point'][2] for c in new['overmaps']] == list(range(7))
        else:
            assert old == new
    chunks = {e['nested_mapgen_id'] for e in json.loads(files['bn/data/json/mapgen/radio_tower.json']) if 'nested_mapgen_id' in e}
    for obj in maps.values():
        for nested in obj.get('place_nested', []):
            assert {name for name, _ in nested['chunks']} <= chunks | {'null'}
    try:
        shifted(['X' + ' ' * 23] + [' ' * 24] * 23, -1, 0)
    except ValueError:
        pass
    else:
        raise AssertionError('Out-of-OMT structure was accepted')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for path, text in [(MAP, files['bn/station_radio.json']), (CITY, catalog['bn/' + CITY]),
                           ('data/json/mapgen/radio_tower.json', files['bn/data/json/mapgen/radio_tower.json']),
                           ('data/json/mapgen_palettes/roof_palette.json', files['bn/data/json/mapgen_palettes/roof_palette.json'])]:
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        omt = root / 'data/json/overmap/overmap_terrain/overmap_terrain.json'
        omt.parent.mkdir(parents=True, exist_ok=True)
        omt.write_text(catalog['bn/data/json/overmap/overmap_terrain/overmap_terrain.json'], encoding='utf-8')
        prepare(check=True, bn_source=root)
        conflict = root / 'data/json/mapgen/unrelated.json'
        conflict.write_text(json.dumps([{'type': 'mapgen', 'om_terrain': [[payload[0]['id'][0]]]}]))
        try:
            prepare(check=True, bn_source=root)
        except ValueError:
            pass
        else:
            raise AssertionError('An unrelated mapgen ID collision was accepted')
    print('PASS: two BN buildings and all other city definitions retained; six DDA tower maps, aligned ladders, reused encounters and collision guards')


if __name__ == '__main__':
    check()
