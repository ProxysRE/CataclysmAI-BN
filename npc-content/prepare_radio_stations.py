#!/usr/bin/env python3
"""Extend two BN radio stations with relocated DDA tower geometry."""
import argparse
import base64
import copy
import difflib
import gzip
import hashlib
import json
from pathlib import Path

from compare_location_catalog import read_sources as catalog_sources

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'radio_stations'
MAP = 'data/json/mapgen/station_radio.json'
CITY = 'data/json/overmap/multitile_city_buildings.json'
PAYLOAD = 'data/json/dda_radio_station_towers.json'
OFFSETS = {'station_radio': (10, -12), 'station_radio_1': (-6, -8)}


def sources():
    raw = gzip.decompress(base64.b64decode((FOLDER / 'SOURCE_BUNDLE.base64').read_bytes(), validate=True))
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Radio source checksum mismatch')
    files = json.loads(raw)
    if set(files) != set(manifest['files']):
        raise ValueError('Radio source manifest mismatch')
    for name, text in files.items():
        if hashlib.sha256(text.encode()).hexdigest() != manifest['files'][name]['sha256']:
            raise ValueError('Radio source drift: ' + name)
    return files


def identifier(entry):
    value = entry['om_terrain']
    return value[0] if isinstance(value, list) else value


def shifted(rows, dx, dy):
    result = [list(' ' * 24) for _ in range(24)]
    for y, row in enumerate(rows):
        for x, symbol in enumerate(row):
            if symbol != ' ':
                nx, ny = x + dx, y + dy
                if not (0 <= nx < 24 and 0 <= ny < 24):
                    raise ValueError('Tower geometry outside the OMT')
                result[ny][nx] = symbol
    return [''.join(row) for row in result]


def prepare_data():
    files = sources()
    catalog, _ = catalog_sources()
    bn = json.loads(files['bn/station_radio.json'])
    dda = json.loads(files['dda/station_radio.json'])
    source_maps = {identifier(e): e for e in dda}
    merged = copy.deepcopy(bn)
    merged_maps = {identifier(e): e for e in merged}
    new_maps, changes = [], {}
    for variant, (dx, dy) in OFFSETS.items():
        roof_id = 'station_radio_roof' + ('_1' if variant.endswith('_1') else '')
        ground = merged_maps[variant]['object']
        roof = merged_maps[roof_id]['object']
        original = copy.deepcopy(ground)
        rows = [list(row) for row in ground['rows']]
        old_poles = [(x, y) for y, row in enumerate(rows) for x, s in enumerate(row) if s == '&']
        assert ground['terrain']['&'] == 't_radio_tower'
        for x, y in old_poles:
            rows[y][x] = '_'
        tower_roof = source_maps[roof_id]['object']
        poles = [(x + dx, y + dy) for y, row in enumerate(tower_roof['rows']) for x, s in enumerate(row) if s == 'R']
        ladder, = [(x + dx, y + dy) for y, row in enumerate(tower_roof['rows']) for x, s in enumerate(row) if s == '≷']
        assert len(poles) == 4
        for x, y in poles + [ladder]:
            if rows[y][x] != '_':
                raise ValueError('Tower footing would overwrite a BN building or fence')
        for x, y in poles:
            rows[y][x] = '&'
        rows[ladder[1]][ladder[0]] = '<'
        ground['rows'] = [''.join(row) for row in rows]
        assert ground['terrain']['<'] == 't_ladder_up'
        # Keep the old BN roof, roof access and random utilities. Add only the
        # tower footprint, which must lie in previously empty roof cells.
        roof_rows = [list(row) for row in roof['rows']]
        footprint = [(x, y, s) for y, row in enumerate(tower_roof['rows']) for x, s in enumerate(row)
                     if s in {'R', 'a', ',', '≷'}]
        for x, y, symbol in footprint:
            nx, ny = x + dx, y + dy
            if roof_rows[ny][nx] != ' ':
                raise ValueError('Tower would overwrite the BN roof')
            roof_rows[ny][nx] = symbol
        roof['rows'] = [''.join(row) for row in roof_rows]
        for symbol in ('R', 'a', ',', '≷'):
            assert symbol not in roof['terrain']
            roof['terrain'][symbol] = tower_roof['terrain'][symbol]
        for suffix in ('even', 'odd', 'top'):
            entry = copy.deepcopy(source_maps[variant + '_tower_' + suffix])
            entry['method'] = 'json'
            obj = entry['object']
            obj['rows'] = shifted(obj['rows'], dx, dy)
            if suffix == 'top':
                obj['terrain']['v'] = 't_ladder_down'  # BN roof palette has no v.
            for nested in obj.get('place_nested', []):
                nested['x'] += dx
                nested['y'] += dy
            new_maps.append(entry)
        changes[variant] = {'offset_from_DDA': [dx, dy], 'ladder_xy': list(ladder),
                            'old_footing_cells': old_poles, 'new_footing_cells': poles,
                            'ground_preserved_except': 'old tower footing, four relocated poles and the tower ladder',
                            'BN_computers_preserved': ground.get('computers') == original.get('computers')}
    # Use BN's established tower visibility and symbols, with explicit fields.
    base_entries = json.loads(catalog['bn/data/json/overmap/overmap_terrain/overmap_terrain.json'])
    terrain = copy.deepcopy(next(e for e in base_entries if 'radio_tower' in e.get('id', [])))
    terrain['id'] = [identifier(e) for e in new_maps]
    payload = [terrain] + new_maps
    before = catalog['bn/' + CITY]
    city = json.loads(before)
    dda_city = json.loads(catalog['dda/' + CITY])
    expected = copy.deepcopy(city)
    output = before
    for variant in OFFSETS:
        target = next(e for e in expected if e.get('id') == variant)
        incoming = next(e for e in dda_city if e.get('id') == variant)
        assert len(target['overmaps']) == 2 and len(incoming['overmaps']) == 7
        extra = incoming['overmaps'][2:]
        target['overmaps'].extend(copy.deepcopy(extra))
        roof_id = 'station_radio_roof' + ('_1' if variant.endswith('_1') else '')
        anchor = '      { "point": [ 0, 0, 1 ], "overmap": "' + roof_id + '_north" }'
        assert output.count(anchor) == 1
        lines = ['      { "point": [ 0, 0, %d ], "overmap": "%s" }' % (c['point'][2], c['overmap']) for c in extra]
        output = output.replace(anchor, anchor + ',\n' + ',\n'.join(lines))
    assert json.loads(output) == expected
    return {MAP: json.dumps(merged, ensure_ascii=True, indent=2) + '\n', CITY: output}, payload, changes


def patch_sections():
    files = sources()
    catalog, _ = catalog_sources()
    outputs, _, _ = prepare_data()
    return ''.join(''.join(difflib.unified_diff((files['bn/station_radio.json'] if path == MAP else catalog['bn/' + CITY]).splitlines(keepends=True),
                 text.splitlines(keepends=True), 'a/' + path, 'b/' + path)) for path, text in outputs.items())


def prepare(check=False, bn_source=None):
    outputs, payload, changes = prepare_data()
    if bn_source:
        files = sources()
        catalog, _ = catalog_sources()
        for path in (MAP, CITY):
            expected = files['bn/station_radio.json'] if path == MAP else catalog['bn/' + path]
            if (bn_source / path).read_text(encoding='utf-8') != expected:
                raise ValueError('Radio baseline drift: ' + path)
        # Reuse existing nested encounters and palette exactly, not duplicate IDs.
        for path in ('data/json/mapgen/radio_tower.json', 'data/json/mapgen_palettes/roof_palette.json'):
            if (bn_source / path).read_text(encoding='utf-8') != files['bn/' + path]:
                raise ValueError('Radio reused dependency drift: ' + path)
        baseline_omt = 'data/json/overmap/overmap_terrain/overmap_terrain.json'
        if (bn_source / baseline_omt).read_text(encoding='utf-8') != catalog['bn/' + baseline_omt]:
            raise ValueError('BN tower overmap terrain baseline drift')
        names = set(payload[0]['id'])
        for directory in ('data/json/overmap/overmap_terrain', 'data/json/mapgen'):
            for path in (bn_source / directory).rglob('*.json'):
                entries = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(entries, dict):
                    entries = [entries]
                for e in entries:
                    ids = e.get('id', e.get('om_terrain', []))
                    def flat(value):
                        if isinstance(value, str):
                            yield value
                        elif isinstance(value, list):
                            for child in value:
                                yield from flat(child)
                    if names.intersection(flat(ids)):
                        raise ValueError('Radio terrain/map ID already exists: ' + str(path))
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    target = ROOT / 'native/dda_radio_station_towers.json'
    if check:
        if target.read_text(encoding='utf-8') != text:
            raise ValueError('Stale radio tower payload')
    else:
        target.write_text(text, encoding='utf-8', newline='\n')
    (FOLDER / 'merged').mkdir(exist_ok=True)
    for path, contents in outputs.items():
        (FOLDER / 'merged' / Path(path).name).write_text(contents, encoding='utf-8', newline='\n')
    report = {'runtime_validated': False, 'installed_in_native_patch': True,
              'new_terrain_ids': payload[0]['id'], 'changes': changes,
              'BN_preserved': ['both buildings and computer objects', 'loot, toilets, furniture and groundcover',
                               'existing roof access and random roof utilities', 'city frequency and all other city buildings'],
              'adaptations': ['DDA tower geometry relocated into BN courtyards', 'BN roof palette and existing nested encounters reused',
                              'BN tower visibility 2 retained instead of DDA vision-level schema'],
              'pending': ['native loader and map generation', 'all four rotations, save/reload and natural city placement']}
    (FOLDER / 'PORT_REPORT.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return outputs, payload, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
    print('Radio stations: preserve BN buildings; DDA tower floors 2..6 and continuous access prepared')
