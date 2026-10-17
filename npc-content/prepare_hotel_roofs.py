#!/usr/bin/env python3
"""Prepare source-backed hotel roof caps without replacing existing BN interiors."""
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from compare_location_catalog import read_sources

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'hotel_roofs'
CITY = 'data/json/overmap/multitile_city_buildings.json'
COMMERCIAL = 'data/json/overmap/overmap_terrain/overmap_terrain_commercial.json'


def sources():
    raw = gzip.decompress(base64.b64decode((FOLDER / 'SOURCE_BUNDLE.base64').read_bytes(), validate=True))
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for side, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][side]
    return files


def prepare_data(city_text=None):
    files = sources()
    catalog, _ = read_sources()
    bn_maps, dda_maps = [json.loads(files[side]) for side in ('bn', 'dda')]
    cap = copy.deepcopy(next(e for e in dda_maps if 'hotel_tower_6_1_9' in str(e.get('om_terrain'))))
    cap['method'] = 'json'
    # A roof cap closes the two existing stair/generator enclosures. There is
    # no additional living floor and no invented stair access to the cap.
    rows = cap['object']['rows']
    below = next(e for e in bn_maps if 'hotel_tower_roof_1_9' in str(e.get('om_terrain')))['object']['rows']
    assert len(rows) == len(below) == 24
    assert all(len(row) == 72 for row in rows + below)
    footprint = [(x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c != ' ']
    assert len(footprint) == 60
    for x, y in footprint:
        assert below[y][x] in '#_+H>', (x, y, below[y][x])
    omt = copy.deepcopy(next(e for e in json.loads(catalog['bn/' + COMMERCIAL])
                            if 'hotel_tower_roof_1_9' in e.get('id', [])))
    omt['id'] = cap['om_terrain'][0]
    city = json.loads(city_text or catalog['bn/' + CITY])
    dda_city = json.loads(catalog['dda/' + CITY])
    changes = {}
    for name in ('hotel_1', 'hotel_2', 'hotel_3'):
        target = next(e for e in city if e.get('id') == name)
        original = copy.deepcopy(target)
        incoming = next(e for e in dda_city if e.get('id') == name)
        extra = [copy.deepcopy(e) for e in incoming['overmaps'] if e['point'][2] == 5]
        assert len(extra) == 3
        for e in extra:
            lower_id = e['overmap'].replace('hotel_tower_6_', 'hotel_tower_roof_')
            lower = next(p for p in target['overmaps'] if p['overmap'] == lower_id)
            # BN has a one-OMT forecourt absent from the DDA placement layout.
            e['point'] = lower['point'][:2] + [5]
            assert not any(p['point'] == e['point'] for p in target['overmaps'])
        target['overmaps'].extend(extra)
        assert target['overmaps'][:-3] == original['overmaps']
        changes[name] = extra
    return [omt, cap], city, {'status': 'prepared_not_installed_or_runtime_validated',
        'scope': 'two technical-enclosure roof caps, not a new inhabited storey',
        'existing_BN_mapgen_entries_preserved': len(bn_maps),
        'roof_footprint_cells': len(footprint), 'placements': changes,
        'dependencies_reused': ['generic_city_building', 'roof_palette'],
        'pending': ['native patch composition with radio city edits', 'Windows generation tests']}


def prepare():
    payload, city, report = prepare_data()
    for name, value in [('PAYLOAD.json', payload), ('CITY_CANDIDATE.json', city), ('PORT_REPORT.json', report)]:
        (FOLDER / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8', newline='\n')
    return payload, city, report


if __name__ == '__main__':
    prepare()
    print('Prepared hotel roof caps; not installed in the native build')
