#!/usr/bin/env python3
"""Port a complete rural church; retain the XEDRA variant and its dependency blockers."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from compare_location_catalog import read_sources

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'rural_churches'
PAYLOAD = 'data/json/dda_rural_church.json'
MAPS = 'data/json/mapgen/'
SPECIALS = 'data/json/overmap/overmap_special/specials.json'
PUBLIC = 'data/json/overmap/overmap_terrain/overmap_terrain_public_institutional.json'


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    raw = gzip.decompress(base64.b64decode(b''.join((FOLDER / n).read_bytes() for n in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for path, value in files.items():
        data = value.encode()
        assert hashlib.sha256(data).hexdigest() == m['files'][path]['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == m['files'][path]['git_blob_sha']
    return files


def flat(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from flat(child)


def prepare_data():
    files = sources()
    catalog, _ = read_sources()
    maps = copy.deepcopy(json.loads(catalog['dda/' + MAPS + 'church_rural.json']))
    used = set(''.join(maps[0]['object']['rows']))
    palette = copy.deepcopy(json.loads(files['dda/church.json'])[0])
    palette['id'] = 'dda_rural_church_palette'
    for field in ('terrain', 'furniture', 'items', 'toilets', 'computers'):
        if field in palette:
            palette[field] = {k: v for k, v in palette[field].items() if k in used}
    for e in maps:
        e['method'] = 'json'
        obj = e['object']
        obj['palettes'] = ['dda_rural_church_palette' if p == 'church' else p for p in obj['palettes']]
        # BN has no scoped mapgen linoleum parameter. Keep the source's explicit
        # fallback, without installing a global parameter system for one colour.
        obj['palettes'] = [p for p in obj['palettes'] if p != 'parametrized_linoleum_palette']
        for symbol, value in list(obj.get('terrain', {}).items()):
            if value == 't_wood_wall_w':
                obj['terrain'][symbol] = 't_wall_w'  # BN's existing white wall.
            elif value == 't_soil':
                obj['terrain'][symbol] = 't_dirt'
            elif isinstance(value, dict) and value.get('param') == 'linoleum_color':
                assert value['fallback'] == 't_linoleum_gray'
                obj['terrain'][symbol] = value['fallback']
    templates = json.loads(catalog['dda/' + PUBLIC])
    names = {n for e in maps for n in flat(e['om_terrain'])}
    terrain = []
    for e in templates:
        ids = set(flat(e.get('id', [])))
        if not ids.intersection(names):
            continue
        assert ids <= names
        target = copy.deepcopy(e)
        target.pop('vision_levels', None)
        target['see_cost'] = 2  # BN numeric visibility schema.
        terrain.append(target)
    assert {n for e in terrain for n in flat(e['id'])} == names
    special = copy.deepcopy(next(e for e in json.loads(catalog['dda/' + SPECIALS]) if e.get('id') == 'church_rural'))
    return [palette] + terrain + maps + [special]


def dependencies(payload):
    needed = {'terrain': set(), 'furniture': set(), 'item_group': set(), 'vehicle_group': set(), 'monstergroup': set()}
    def ids(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for child in value:
                yield from ids(child)
    for e in payload:
        obj = e.get('object', e)
        for field in ('terrain', 'furniture'):
            for value in obj.get(field, {}).values():
                needed[field].update(ids(value))
        for value in obj.get('items', {}).values():
            for group in value if isinstance(value, list) else [value]:
                needed['item_group'].add(group['item'])
        for value in obj.get('vehicles', {}).values():
            needed['vehicle_group'].add(value['vehicle'])
        if 'spawns' in e:
            needed['monstergroup'].add(e['spawns']['group'])
    return needed


def prepare(check=False, bn_source=None):
    files = sources()
    payload = prepare_data()
    if bn_source:
        # Reuse BN's cathedral palette (including BN food/loot rules), roof
        # palette and native toll computer action. No existing palette is edited.
        for name in ('cathedral_palette.json',):
            p = bn_source / 'data/json/mapgen_palettes' / name
            if p.read_text(encoding='utf-8') != files['bn/' + name]:
                raise ValueError('BN reused church dependency drift: ' + name)
        declarations = {}
        for e in payload:
            kind = 'mapgen' if e['type'] == 'mapgen' else e['type']
            declarations.setdefault(kind, set()).update(flat(e.get('om_terrain', e.get('id', []))))
        available = {kind: set() for kind in dependencies(payload)}
        for p in (bn_source / 'data/json').rglob('*.json'):
            entries = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(entries, dict):
                entries = [entries]
            for e in entries:
                if not isinstance(e, dict):
                    continue
                kind = e.get('type')
                identity = set(flat(e.get('om_terrain', e.get('id', []))))
                if kind in declarations and identity.intersection(declarations[kind]):
                    raise ValueError('Church typed ID collision: ' + str(p))
                if kind in available:
                    available[kind].update(flat(e.get('id', e.get('name', []))))
        for kind, wanted in dependencies(payload).items():
            missing = wanted - available[kind]
            if missing:
                raise ValueError('Missing church dependency ' + kind + ': ' + ', '.join(sorted(missing)))
    target = ROOT / 'native/dda_rural_church.json'
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    if check:
        assert target.read_text(encoding='utf-8') == text, 'Stale rural church payload'
    else:
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
