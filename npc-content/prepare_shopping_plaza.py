#!/usr/bin/env python3
"""Add DDA plaza roofs while retaining BN's entire ground-level generation."""
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from compare_location_catalog import read_sources

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'shopping_plaza'
MAP = 'data/json/mapgen/abandoned_shopping_plaza.json'
CITY = 'data/json/overmap/multitile_city_buildings.json'
PAYLOAD = 'data/json/dda_shopping_plaza_roofs.json'


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    raw = gzip.decompress(base64.b64decode((FOLDER / 'SOURCE_BUNDLE.base64').read_bytes(), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for side, text in files.items():
        encoded = text.encode()
        assert hashlib.sha256(encoded).hexdigest() == manifest['files'][side]['sha256']
        assert hashlib.sha1(b'blob ' + str(len(encoded)).encode() + b'\0' + encoded).hexdigest() == manifest['files'][side]['git_blob_sha']
    return files


def prepare_data(city):
    catalog, _ = read_sources()
    files = sources()
    dda = json.loads(files['dda'])
    roofs = copy.deepcopy(dda[3:])
    names = [name for e in roofs for row in e['om_terrain'] for name in row if name != 'null']
    assert len(names) == len(set(names)) == 7
    terrain = {'type': 'overmap_terrain', 'id': names, 'copy-from': 'generic_city_building',
               'name': 'abandoned shopping plaza roof', 'sym': 'O', 'color': 'dark_gray'}
    for e in roofs:
        e['method'] = 'json'
        assert e['object']['palettes'] == ['roof_palette']
        assert set(''.join(e['object']['rows'])) <= {' ', '.', '#', '5'}
    result = copy.deepcopy(city)
    target = next(e for e in result if e.get('id') == 'shopping_plaza')
    before = copy.deepcopy(target)
    incoming = next(e for e in json.loads(catalog['dda/' + CITY]) if e.get('id') == 'shopping_plaza')
    extra = [copy.deepcopy(e) for e in incoming['overmaps'] if e['point'][2] == 1]
    assert len(extra) == 7
    assert incoming['overmaps'][:12] == target['overmaps']
    for e in extra:
        assert not any(p['point'] == e['point'] for p in target['overmaps'])
        lower = e['overmap'].replace('_A', '_a').replace('_B', '_b')
        assert any(p['point'][:2] == e['point'][:2] and p['overmap'] == lower for p in target['overmaps'])
    target['overmaps'].extend(extra)
    assert target['overmaps'][:-7] == before['overmaps']
    return [terrain] + roofs, result


def prepare(check=False, bn_source=None):
    catalog, _ = read_sources()
    payload, _ = prepare_data(json.loads(catalog['bn/' + CITY]))
    if bn_source:
        if (bn_source / MAP).read_text(encoding='utf-8') != sources()['bn']:
            raise ValueError('BN shopping plaza baseline drift')
        names = set(payload[0]['id'])
        def flat(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                for child in value:
                    yield from flat(child)
        for folder in ('data/json/mapgen', 'data/json/overmap/overmap_terrain'):
            for path in (bn_source / folder).rglob('*.json'):
                entries = json.loads(path.read_text(encoding='utf-8'))
                for e in entries if isinstance(entries, list) else [entries]:
                    if names.intersection(flat(e.get('id', e.get('om_terrain', [])))):
                        raise ValueError('Plaza terrain/map ID collision: ' + str(path))
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    target = ROOT / 'native/dda_shopping_plaza_roofs.json'
    if check:
        assert target.read_text(encoding='utf-8') == text
    else:
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
