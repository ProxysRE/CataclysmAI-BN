#!/usr/bin/env python3
"""Close eldercare infrastructure and laboratory-record dependencies using BN systems."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from export_bn_ids import read_cache
from prepare_regional_locations import references, index_entries, BUILTIN_IDS
from bn_counterparts import adapt_entry

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'eldercare_assets'
PAYLOAD = 'data/json/dda_eldercare_assets.json'
PINS = {'bn': 'c621aaf42fa182473aad10feea2b55647704dcf1', 'dda': 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
ALIASES = {
    ('furniture', 'f_water_heater_family'): ('f_water_heater', 'Stock BN water tank, keg interaction and capacity.'),
    ('terrain', 't_zebra'): ('t_pavement_y', 'Stock marked pavement; BN road-marking appearance.'),
    ('terrain', 't_window_bars_noglass'): ('t_bars', 'Stock transparent metal bars without glass.'),
    ('item_group', 'SUS_trash_hardware'): ('hardware_trash', 'Stock hardware refuse.'),
    ('item_group', 'mon_feral_cop_death_drops'): ('mon_zombie_cop_death_drops', 'Stock police clothing and equipment drops; probabilities and weapons follow BN.'),
}
CROSS = {'f_console': 't_console', 'f_console_broken': 't_console_broken', 'f_hedge_short': 't_shrub'}
GENERATORS = {'f_generator_broken': 'broken', 'f_diesel_generator': 'diesel',
              'f_military_generator': 'military', 'f_12000_gasoline_generator': 'gasoline'}
GROUPS = ('common_mutation_books', 'rare_mutation_books', 'hoarder', 'lab_files_generic')


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert m['pins'] == PINS
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / p).read_text() for p in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == m['files'][path]
        if path.endswith('.json'):
            json.loads(text)
    return files


def declarations(game='dda'):
    return {e['id']: e for path, text in sources().items() if path.startswith(game + '/') and path.endswith('.json')
            for e in json.loads(text) if isinstance(e.get('id'), str)}


def adapt_references(entry):
    aliases = {source: target for (_, source), (target, _) in ALIASES.items()}
    def walk(value, top=False):
        if isinstance(value, str):
            return aliases.get(value, value)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: v if k in ('name', 'description', 'text', 'dynamic_line') or k.startswith('//') or
                    (top and k in ('id', 'abstract')) else walk(v) for k, v in value.items()}
        return value
    return walk(entry, True)


def wall_palette():
    original = copy.deepcopy(declarations()['parametrized_walls_palette'])
    aliases = {name: 't_wall_w' for name in ('t_wall_gray', 't_wall_brown', 't_wall_cyan', 't_wall_black', 't_wall_orange')}
    for material in ('t_concrete_wall', 't_strconc_wall', 't_sconc_wall'):
        aliases.update({material + suffix: material for suffix in ('_w', '_gray')})
    for parameter in original['parameters'].values():
        parameter['default']['distribution'] = [[aliases.get(name, name), weight] for name, weight in parameter['default']['distribution']]
    return original


def adapt_map(entry):
    result = adapt_references(entry)
    if result.get('type') != 'mapgen':
        return result
    obj = result['object']
    if 'parametrized_walls_palette' in obj.get('palettes', []):
        obj['palettes'].remove('parametrized_walls_palette')
        palette = wall_palette()
        # Inline into deferred mapgen; root palettes resolve IDs too early in BN.
        for field in ('parameters', 'terrain', 'nested'):
            values = copy.deepcopy(palette[field])
            values.update(obj.get(field, {}))
            obj[field] = values
    for glyph, furniture in list(obj.get('furniture', {}).items()):
        if isinstance(furniture, str) and furniture in CROSS:
            obj['furniture'].pop(glyph)
            obj.setdefault('terrain', {})[glyph] = CROSS[furniture]
        elif isinstance(furniture, list) and any(isinstance(p, list) and p[0] in GENERATORS for p in furniture):
            assert all(isinstance(p, list) and p[0] in GENERATORS for p in furniture)
            assert glyph not in obj.get('nested', {})
            obj['furniture'].pop(glyph)
            obj.setdefault('nested', {})[glyph] = {'chunks': [['dda_eldercare_generator_' + GENERATORS[name], weight] for name, weight in furniture]}
    # One-cell medical objects must not grow into neighbouring beds or walls.
    def vehicles(value):
        if isinstance(value, str):
            return {'hospital_bed_small': 'dda_eldercare_bed_small', 'medical_cart': 'dda_eldercare_medical_cart', 'van_cargo': 'dda_eldercare_cargo_van'}.get(value, value)
        if isinstance(value, list):
            return [vehicles(v) for v in value]
        if isinstance(value, dict):
            return {k: vehicles(v) for k, v in value.items()}
        return value
    for field in ('vehicles', 'place_vehicles'):
        if field in obj:
            obj[field] = vehicles(obj[field])
    return result


def native_data():
    defs = declarations()
    result = []
    for key in GROUPS:
        result.append(adapt_references(adapt_entry(copy.deepcopy(defs[key]))))
    # BN supplies one established saline item; do not import DDA infusion/EOC mechanics.
    result.append({'type': 'item_group', 'id': 'saline_bottle_random', 'subtype': 'distribution', 'items': [['saline', 100]]})
    notes = {r['item'] for r in defs['lab_files_generic']['items']}
    categories = set()
    for key in sorted(notes):
        source = copy.deepcopy(defs[key])
        assert set(source) <= {'type', 'id', 'copy-from', 'name', 'description', 'snippet_category'}
        source['type'] = 'GENERIC'
        # Use BN's verified readable-paper base for every record instead of
        # assuming DDA's `file` inheritance has identical BN semantics.
        source['copy-from'] = 'survnote'
        source.setdefault('description', defs['lab_postit_bio']['description'])
        categories.add(source['snippet_category'])
        result.append(source)
    snippets = json.loads(sources()['dda/data/json/snippets/lab.json'])
    selected = [copy.deepcopy(e) for e in snippets if e.get('category') in categories]
    assert {e['category'] for e in selected} == categories
    assert all({k for k in e if not k.startswith('//')} == {'type', 'category', 'text'} for e in selected)
    result += selected
    result += [
        {'type': 'vehicle', 'id': 'dda_eldercare_bed_small', 'name': 'small hospital bed',
         'parts': [{'x': 0, 'y': 0, 'parts': ['xlframe_vertical_2', 'wheel_10', 'bed']}]},
        {'type': 'vehicle', 'id': 'dda_eldercare_medical_cart', 'name': 'medical cart',
         'parts': [{'x': 0, 'y': 0, 'parts': ['xlframe_vertical_2', 'wheel_caster', 'veh_table']}]},
    ]
    # The BN cargo van is wider than the source parking space. Reuse the
    # stock BN camper hull (same 7x4 footprint) with a cargo interior.
    van = copy.deepcopy(declarations('bn')['camper_van'])
    van.update(id='dda_eldercare_cargo_van', name='cargo van')
    van.pop('blueprint', None)
    for tile in van['parts']:
        if tile['x'] in (-1, -2, -3) and tile['y'] in (0, 1):
            tile['parts'] = ['frame_vertical_2', 'cargo_space', 'roof']
    van['items'] = [{'x': 0, 'y': 0, 'chance': 10, 'items': ['roadmap']},
                    {'x': -3, 'y': 0, 'chance': 100, 'item_groups': ['car_kit']}]
    result.append(van)
    for kind, fuel, engine in [('diesel' , 'diesel', 'diesel_engine_v6'), ('military', 'diesel', 'diesel_engine_v6'), ('gasoline', 'gasoline', 'engine_vtwin')]:
        vehicle = 'dda_eldercare_' + kind + '_generator'
        result.append({'type': 'vehicle', 'id': vehicle, 'name': kind + ' backup generator',
                       'parts': [{'x': 0, 'y': 0, 'parts': ['frame_cover', {'part': 'tank_small', 'fuel': fuel},
                                  'small_storage_battery', engine, 'generator_7500w', 'controls_electronic', 'box']}],
                       'items': [{'x': 0, 'y': 0, 'chance': 50, 'items': ['jumper_cable']}]})
        result.append({'type': 'mapgen', 'method': 'json', 'nested_mapgen_id': 'dda_eldercare_generator_' + kind,
                       'object': {'mapgensize': [1, 1], 'place_vehicles': [{'x': 0, 'y': 0, 'vehicle': vehicle, 'chance': 100, 'rotation': 0}]}})
    result.append({'type': 'mapgen', 'method': 'json', 'nested_mapgen_id': 'dda_eldercare_generator_broken',
                   'object': {'mapgensize': [1, 1], 'terrain': {'g': 't_generator_broken'}, 'rows': ['g']}})
    return result


def dependency_refs(payload):
    refs = set()
    for entry in payload:
        if entry['type'] == 'item_group':
            refs.update(references({'items': {'_': {'item': entry}}}))
        elif entry['type'] == 'GENERIC':
            refs.add(('item', entry['copy-from']))
        elif entry['type'] == 'vehicle':
            for tile in entry['parts']:
                for part in tile['parts']:
                    refs.add(('vehicle_part', part if isinstance(part, str) else part['part']))
                    if isinstance(part, dict) and 'fuel' in part:
                        refs.add(('item', part['fuel']))
            for location in entry.get('items', []):
                refs.update(('item', item) for item in location.get('items', []))
                refs.update(('item_group', group) for group in location.get('item_groups', []))
        elif entry['type'] == 'mapgen':
            refs.update(references(entry['object']))
    return refs


def prepare(check=False, bn_source=None, bn_data=None):
    files = sources()
    if bn_source:
        for path, text in files.items():
            if path.startswith('bn/'):
                assert (bn_source / path[3:]).read_text(encoding='utf-8') == text, path
    index = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    payload = native_data()
    new = index_entries(payload) - BUILTIN_IDS
    assert not new & index, new & index
    for path in (ROOT / 'native').rglob('*.json'):
        if path.name == 'dda_eldercare_assets.json':
            continue
        other = json.loads(path.read_text())
        if isinstance(other, list):
            assert not new & (index_entries(other) - BUILTIN_IDS), path
    assert not dependency_refs(payload) - index - new, dependency_refs(payload) - index - new
    for (kind, _), (target, _) in ALIASES.items():
        assert (kind, target) in index
    for target in CROSS.values():
        assert ('terrain', target) in index
    for parameter in wall_palette()['parameters'].values():
        assert all(('terrain', name) in index for name, _ in parameter['default']['distribution'])
    if bn_source or bn_data:
        directory = bn_source or bn_data
        existing_categories = {e['category'] for p in (directory / 'data/json/snippets').rglob('*.json')
                               for e in json.loads(p.read_text(encoding='utf-8')) if e.get('type') == 'snippet'}
        assert not existing_categories & {e['category'] for e in payload if e['type'] == 'snippet'}
        existing_ids = {text['id'] for p in (directory / 'data/json/snippets').rglob('*.json')
                        for e in json.loads(p.read_text(encoding='utf-8')) if e.get('type') == 'snippet'
                        for text in e.get('text', []) if isinstance(text, dict) and 'id' in text}
        new_ids = [text['id'] for e in payload if e['type'] == 'snippet' for text in e['text']]
        assert len(new_ids) == len(set(new_ids)) and not existing_ids & set(new_ids)
    report = {'pins': PINS, 'status': 'native_support_prepared_runtime_pending',
              'definitions': len(payload), 'by_type': dict(Counter(e['type'] for e in payload)),
              'source_lab_records': 60, 'stock_aliases': [{'type': kind, 'source': name, 'target': target, 'reason': reason}
                  for (kind, name), (target, reason) in sorted(ALIASES.items())],
              'whole_locations_installed': False,
              'runtime_validation': 'Windows native and installed tests pending; manual location interaction pending'}
    for path, data in {ROOT / 'native/dda_eldercare_assets.json': payload, FOLDER / 'PORT_REPORT.json': report}.items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if check:
            assert path.read_text() == text
        else:
            path.write_text(text)
    print('PASS:', len(payload), 'eldercare asset definitions; stock BN dependency closure; whole sites remain staged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    parser.add_argument('--bn-data', type=Path)
    a = parser.parse_args()
    prepare(a.check, a.bn_source, a.bn_data)
