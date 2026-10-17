#!/usr/bin/env python3
"""Reproducible, deliberately non-installed location transfer layer.

Only local palettes are expanded. Shared BN palettes remain references; their
presence alone is not semantic compatibility. No missing content is substituted.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from compare_location_catalog import read_sources, normalized, physical_refs
from quest_dependency_graph import namespace, ids

BUILTIN_IDS = {('terrain', 't_null'), ('furniture', 'f_null'), ('item', 'null')}
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'regional_locations'
SITES = {
    'small_lighthouse': ['lighthouse_small.json'],
    'karting': ['karting_l.json', 'karting_palette.json', 'cars.json'],
    'farm_supply': ['farm_supply.json', 'farm_supply_palette.json'],
    'nursing_home': ['nursing_home.json', 'nursing_home_palette.json', 'nursing_home_nested.json', 'TALK_NURSING_HOME.json'],
    'retirement_community': ['retirement_community.json', 'retirement_community_palette.json', 'TALK_RET_COMM.json'],
}
SOURCE_PATHS = {
    'TALK_RET_COMM.json': 'data/json/npcs/computers/TALK_RET_COMM.json',
    'cars.json': 'data/json/vehicles/cars.json',
    'TALK_NURSING_HOME.json': 'data/json/npcs/computers/TALK_NURSING_HOME.json',
    'lighthouse_small.json': 'data/json/mapgen/lake_buildings/lighthouse_small.json',
    'karting_l.json': 'data/json/mapgen/karting_l.json',
    'karting_palette.json': 'data/json/mapgen_palettes/karting_l.json',
    'farm_supply.json': 'data/json/mapgen/farm_supply.json',
    'farm_supply_palette.json': 'data/json/mapgen_palettes/farm_supply_palette.json',
    'nursing_home.json': 'data/json/mapgen/nursing_home.json',
    'nursing_home_palette.json': 'data/json/mapgen_palettes/nursing_home_palette.json',
    'nursing_home_nested.json': 'data/json/mapgen/nested/nursing_home_nested.json',
    'retirement_community.json': 'data/json/mapgen/retirement_community.json',
    'retirement_community_palette.json': 'data/json/mapgen_palettes/retirement_community_palette.json',
}


def flatten(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from flatten(child)


def read_bundle():
    manifest = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text())
    raw = gzip.decompress(base64.b64decode(''.join((OUT / p).read_text() for p in manifest['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(SOURCE_PATHS)
    for name, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][name]['sha256']
    return files, manifest


def expand(obj, palettes, trail=()):
    result = {}
    for name in obj.get('palettes', []):
        if name not in palettes:
            result.setdefault('palettes', []).append(name)
            continue
        assert name not in trail, ('palette cycle', trail, name)
        merge(result, expand(palettes[name], palettes, trail + (name,)))
    merge(result, {k: v for k, v in obj.items() if k not in ('type', 'id', 'palettes')})
    return result


def merge(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            target[key].update(copy.deepcopy(value))
        elif isinstance(value, list) and isinstance(target.get(key), list):
            target[key].extend(copy.deepcopy(value))
        else:
            target[key] = copy.deepcopy(value)


def references(obj):
    """Conservative typed mapgen reference positions, not a full DDA parser."""
    refs = set()
    def value(kind, data):
        if isinstance(data, str):
            refs.add((kind, data))
        elif isinstance(data, list):
            for child in data:
                value(kind, child[0] if isinstance(child, list) and len(child) == 2 and isinstance(child[1], (int, float)) else child)
        elif isinstance(data, dict):
            if kind == 'item_group' and ('entries' in data or 'items' in data):
                # An inline loot group is not an ID. Its leaves are typed:
                # item -> item, group -> item_group, containers -> item.
                for entry in data.get('entries', data.get('items', [])):
                    if isinstance(entry, list):
                        value('item', entry[0])
                    elif isinstance(entry, dict):
                        for field, target in [('item', 'item'), ('group', 'item_group'), ('container-item', 'item')]:
                            if field in entry:
                                value(target, entry[field])
                        for field in ('collection', 'distribution'):
                            if field in entry:
                                value('item_group', {'entries': entry[field]})
                if 'container-item' in data:
                    value('item', data['container-item'])
                return
            for key in ('fallback', kind, 'id') + ({'item_group': ('item', 'group'), 'monstergroup': ('monster', 'group')}.get(kind, ())):
                if key in data:
                    value(kind, data[key])
    for field, kind in [('terrain', 'terrain'), ('furniture', 'furniture'), ('items', 'item_group'),
                        ('item', 'item'), ('monsters', 'monstergroup'), ('corpses', 'monstergroup'), ('vehicles', 'vehicle'),
                        ('traps', 'trap'), ('fields', 'field_type')]:
        for data in obj.get(field, {}).values():
            value(kind, data)
    value('terrain', obj.get('fill_ter', []))
    for data in obj.get('palettes', []):
        value('palette', data)
    for field, kind, keys in [('place_items', 'item_group', ('item', 'group')),
                              ('place_item', 'item', ('item',)),
                              ('place_monsters', 'monstergroup', ('monster', 'group')),
                              ('place_monster', 'MONSTER', ('monster',)),
                              ('place_corpses', 'monstergroup', ('group',)),
                              ('place_vehicles', 'vehicle', ('vehicle',)),
                              ('place_npcs', 'npc', ('class',)),
                              ('place_nested', 'nested_mapgen', ('chunks',))]:
        for data in obj.get(field, []):
            for key in keys:
                value(kind, data.get(key, []))
    for data in obj.get('nested', {}).values():
        if isinstance(data, dict):
            value('nested_mapgen', data.get('chunks', []))
    for spawn in obj.get('place_monster', []):
        if 'group' in spawn:
            value('monstergroup', spawn['group'])
    for liquid in obj.get('place_liquids', []):
        value('item', liquid.get('liquid', []))
    for machine in list(obj.get('vendingmachines', {}).values()) + obj.get('place_vendingmachines', []):
        value('item_group', machine.get('item_group', 'default_vending_machine'))
    for computer in obj.get('place_computers', []):
        value('effect_on_condition', computer.get('eocs', []))
        value('talk_topic', computer.get('chat_topics', []))
    return sorted(refs - {('nested_mapgen', 'null')})


def index_entries(entries):
    result = set(BUILTIN_IDS)
    for e in entries:
        for identifier in ids(e):
            result.add((namespace(e) + ('_abstract' if 'id' not in e else ''), identifier))
        if e.get('type') == 'vehicle_part':
            for shape in e.get('shapes', []):
                for base in ids(e):
                    result.add(('vehicle_part', base + '_' + shape['direction']))
        if e.get('type') == 'vehicle_group':
            for identifier in ids(e):
                result.add(('vehicle', identifier))  # mapgen accepts a group or a prototype
        if e.get('type') in ('monstergroup', 'vehicle_group') and isinstance(e.get('name'), str):
            result.add((e['type'], e['name']))
        for identifier in flatten(e.get('om_terrain', [])):
            result.add(('mapgen', identifier))
        for identifier in flatten(e.get('nested_mapgen_id', [])):
            result.add(('nested_mapgen', identifier))
        for identifier in flatten(e.get('update_mapgen_id', [])):
            result.add(('update_mapgen', identifier))
    return result


def build(bn_source=None, native_payloads=()):
    files, manifest = read_bundle()
    catalog, _ = read_sources()
    sides = {s: [e for p, text in catalog.items() if p.startswith(s + '/')
                 for e in json.loads(text)] for s in ('dda', 'bn')}
    terrain = {i: e for e in sides['dda'] if e.get('type') == 'overmap_terrain' for i in ids(e)}
    bn_index = index_entries(sides['bn'])
    if bn_source:
        paths = sorted((Path(bn_source) / 'data/json').rglob('*.json'))
        if len(paths) < 100:
            raise ValueError('Full pinned BN data/json checkout required')
        for path in paths:
            data = json.loads(path.read_text(encoding='utf-8'))
            bn_index.update(index_entries(data if isinstance(data, list) else [data]))
    native_index = set()
    for path in native_payloads:
        native_index.update(index_entries(json.loads(path.read_text(encoding='utf-8'))))
    native_index -= BUILTIN_IDS
    outputs, reports = {}, []
    for site, names in SITES.items():
        entries = [e for name in names for e in json.loads(files[name])
                   if name != 'cars.json' or e.get('id') == 'go_kart']
        palettes = {e['id']: e for e in entries if e.get('type') == 'palette'}
        maps = [e for e in entries if e.get('type') == 'mapgen']
        omt = set(i for e in maps for i in flatten(e.get('om_terrain', [])))
        selected_terrain = list({json.dumps(terrain[i], sort_keys=True): terrain[i]
                                 for i in sorted(omt) if i in terrain}.values())
        specials = [e for e in sides['dda'] if e.get('type') in ('overmap_special', 'city_building')
                    and any(normalized(i, terrain) in omt for i in physical_refs(e))]
        staged = []
        for entry in entries:
            if entry.get('type') == 'palette':
                continue
            new = copy.deepcopy(entry)
            if 'object' in new:
                new['object'] = expand(new['object'], palettes)
            staged.append(new)
        staged.extend(copy.deepcopy(selected_terrain + specials))
        local_index = index_entries(staged) - BUILTIN_IDS
        refs = {ref for e in staged if e.get('type') == 'mapgen' for ref in references(e.get('object', {}))}
        for e in staged:
            if e.get('type') == 'vehicle':
                for location in e.get('parts', []):
                    for part in location.get('parts', []):
                        identifier = part if isinstance(part, str) else part['part']
                        refs.add(('vehicle_part', identifier))
                        if isinstance(part, dict) and 'fuel' in part:
                            refs.add(('item', part['fuel']))
        refs = sorted(refs)
        obligations = [{'type': kind, 'id': identifier,
                        'status': 'provided_in_site' if (kind, identifier) in local_index else
                                  'provided_by_native_port_review_adaptation' if (kind, identifier) in native_index else
                                  'bn_id_present_review_semantics' if (kind, identifier) in bn_index else
                                  'unresolved_under_scanned_type' if bn_source else 'requires_full_bn_scan'}
                       for kind, identifier in refs]
        cells = sum(len(list(flatten(e.get('om_terrain', [])))) for e in maps)
        reports.append({'site': site, 'state': 'staged_not_installed', 'mapgen_definitions': len(maps),
                        'mapgen_terrain_slots': cells, 'overmap_terrain_definitions': len(selected_terrain),
                        'placements': [e['id'] for e in specials], 'local_palettes_expanded': sorted(palettes),
                        'dependencies': obligations,
                        'additional_definitions': {kind: sum(e.get('type') == kind for e in entries) for kind in sorted({e.get('type') for e in entries} - {'mapgen', 'palette'})},
                        'source_mapgen_fields': sorted({k for e in maps for k in e.get('object', {})}),
                        'unregistered_mapgen_terrain_ids': sorted(omt - set(terrain))})
        outputs[site + '.json'] = staged
    report = {'pins': manifest['pins'], 'bn_scan': 'full_core_json' if bn_source else 'catalog_only',
              'installed': False, 'native_dependency_payloads': [p.name for p in native_payloads], 'reference_scan_scope': 'Explicit terrain/furniture/item/group/monster/vehicle/palette/nested positions, including inline loot collections; not a complete transitive loader validation.',
              'remaining': ['Resolve all shared nested/palette and item dependencies',
                            'Review BN counterparts semantically; matching ID is not parity',
                            'Adapt DDA schema, parameters, ramps and functional furniture without substitutions',
                            'Normalize placement connections and numeric vision at native integration',
                            'Run native loading, generation, stairs and placement tests before enabling'],
              'sites': reports}
    outputs['TRANSFER_REPORT.json'] = report
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bn-source', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--native-payload', type=Path, action='append', default=[])
    args = parser.parse_args()
    outputs = build(args.bn_source, args.native_payload)
    for name, value in outputs.items():
        text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        if (args.bn_source or args.native_payload) and name == 'TRANSFER_REPORT.json':
            if args.report:
                args.report.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            for site in value['sites']:
                from collections import Counter
                print(site['site'], dict(Counter(d['status'] for d in site['dependencies'])))
                print('UNRESOLVED', site['site'], [(d['type'], d['id']) for d in site['dependencies'] if d['status'] == 'unresolved_under_scanned_type'])
            continue
        path = OUT / name
        if args.check:
            assert path.read_text(encoding='utf-8') == text, name
        else:
            path.write_text(text, encoding='utf-8')
    print('Regional staging:', len(SITES), 'sites;', sum(r['mapgen_definitions'] for r in outputs['TRANSFER_REPORT.json']['sites']), 'mapgens')


if __name__ == '__main__':
    main()
