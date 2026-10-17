#!/usr/bin/env python3
"""Port both complete farm shops using BN appliances, ATM and resource units."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from prepare_regional_locations import build, references, index_entries
from prepare_karting import prepare_data as karting_data, sources as karting_sources
from quest_dependency_graph import namespace, ids

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'farm_supply'
PAYLOAD = 'data/json/dda_farm_supply.json'
MAP_GROUPS = ['farm_supply_soil_and_sand', 'farm_supply_rocks', 'farm_supply_quicklime_and_saltpetre']
SUPPLY_GROUPS = ['sandbag', 'earthbag', 'cement_bag', 'quicklime_bag', 'quicklime_barrel', 'saltpeter_canvas_bag_part']
FURNITURE = ['f_pallet_brick', 'f_pallet_cement', 'f_stack_plank']
GROUP_ALIASES = {'SUS_fridge_breakroom': 'SUS_fridge', 'SUS_trash_dumpster': 'trash_dumpster',
                 'SUS_trash_trashcan_public': 'trash_cart'}


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / p).read_text() for p in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for name, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == m['files'][name]['sha256']
    return files


def adapt_drop(value):
    """DDA resource counts become BN ammo charges, never many full stacks."""
    if isinstance(value, list):
        return [adapt_drop(child) for child in value]
    if not isinstance(value, dict):
        return value
    out = {k: adapt_drop(v) for k, v in value.items()}
    if out.get('item') in ('material_sand', 'material_soil', 'material_cement', 'material_quicklime', 'chem_saltpetre', 'material_limestone') and 'count' in out:
        out['charges'] = out.pop('count')
    if out.get('item') == 'bag_durasack':
        out['item'] = 'bag_canvas'
    if out.get('item') == 'rock_flaking':
        out['item'] = 'flint'
    if 'damage' in out and 'item' in out:
        damage = out.pop('damage')
        out['damage-min'], out['damage-max'] = damage if isinstance(damage, list) else (damage, damage)
        out['damage-min'] = min(out['damage-min'], 4)
        out['damage-max'] = min(out['damage-max'], 4)
    return out


def materialize_terrain(identifier, entries):
    source = copy.deepcopy(next(e for e in entries if e.get('id') == identifier))
    if 'copy-from' not in source:
        return source
    parent = materialize_terrain(source.pop('copy-from'), entries)
    def merge(target, update):
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                merge(target[key], value)
            else:
                target[key] = value
    delete, extend = source.pop('delete', {}), source.pop('extend', {})
    merge(parent, source)
    for key, values in delete.items():
        parent[key] = [v for v in parent[key] if v not in values]
    for key, values in extend.items():
        parent.setdefault(key, []).extend(values)
    return parent


def prepare_data():
    files = sources()
    result = copy.deepcopy(build()['farm_supply.json'])
    for e in result:
        if e['type'] == 'mapgen':
            e['method'] = 'json'
            obj = e['object']
            if 'm' in obj.get('furniture', {}):
                assert obj['furniture'].pop('m') == 'f_atm_off'
                obj['terrain']['m'] = 't_atm'
            for glyph, furniture in obj.get('furniture', {}).items():
                if isinstance(furniture, list):
                    obj['furniture'][glyph] = ['f_minifreezer' if f == 'f_chest_minifreezer' else f for f in furniture]
            for binding in obj.get('items', {}).values():
                if isinstance(binding, dict) and isinstance(binding.get('item'), str):
                    binding['item'] = GROUP_ALIASES.get(binding['item'], binding['item'])
            for machine in obj.get('vendingmachines', {}).values():
                if 'lootable' in machine:
                    assert machine.pop('lootable') is True
        if e['type'] == 'overmap_terrain':
            e.pop('vision_levels', None)
            if isinstance(e.get('see_cost'), str):
                e['see_cost'] = 2
        if e['type'] in ('overmap_special', 'city_building'):
            if 'flags' in e:
                e['flags'] = ['UNIQUE' if f == 'OVERMAP_UNIQUE' else f for f in e['flags']]
            for c in e.get('connections', []):
                if c.pop('terrain', None) == 'road':
                    c['connection'] = 'local_road'
    result += [copy.deepcopy(e) for e in json.loads(files['dda/data/json/mapgen/nested/aux_nested.json']) if e.get('nested_mapgen_id') == '1x1_bash']
    for source in json.loads(files['dda/data/json/itemgroups/Locations_MapExtras/locations_commercial.json']):
        if source.get('id') in MAP_GROUPS:
            result.append(adapt_drop(source))
    for source in json.loads(files['dda/data/json/itemgroups/supplies.json']):
        if source.get('id') not in SUPPLY_GROUPS:
            continue
        group = adapt_drop(source)
        if group.get('container-item') in ('bag_durasack', 'bag_durasack_cement'):
            group['container-item'] = 'bag_canvas'
        result.append(group)
    for source in json.loads(files['dda/data/json/furniture_and_terrain/furniture-pallet.json']):
        if source.get('id') not in FURNITURE:
            continue
        furniture = adapt_drop(source)
        furniture['flags'] = ['SHORT' if f == 'SMALL_HIDE' else f for f in furniture['flags']]
        furniture['looks_like'] = 'f_crate_o'
        result.append(furniture)
    pallet = copy.deepcopy(next(e for e in json.loads(karting_sources()['dda/data/json/items/generic.json']) if e.get('id') == 'pallet'))
    pallet['type'] = 'GENERIC'
    result.append(pallet)
    carpet = materialize_terrain('t_carpet_concrete', json.loads(files['bn/data/json/furniture_and_terrain/terrain-floors-indoor.json']))
    carpet.update(id='t_carpet_concrete_red', color='red', looks_like='t_carpet_concrete')
    result.append(carpet)
    return result


def dependency_refs(payload):
    refs = {r for e in payload if e['type'] == 'mapgen' for r in references(e['object'])}
    def visit(value):
        if isinstance(value, list):
            for child in value:
                yield from visit(child)
        elif isinstance(value, dict):
            for key, val in value.items():
                if key in ('item', 'container-item') and isinstance(val, str):
                    yield 'item', val
                elif key == 'group' and isinstance(val, str):
                    yield 'item_group', val
                else:
                    yield from visit(val)
    for e in payload:
        if e['type'] in ('item_group', 'furniture', 'terrain'):
            refs.update(visit(e))
    return refs - {('nested_mapgen', 'null')}


def validate_bn(root, report=False):
    files = sources()
    for name, text in files.items():
        if name.startswith('bn/data/'):
            assert (root / name[3:]).read_text(encoding='utf-8') == text, name
    paths = sorted((root / 'data/json').rglob('*.json'))
    assert len(paths) > 100
    index = set()
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        index.update(index_entries(data if isinstance(data, list) else [data]))
    payload = prepare_data()
    new = {(namespace(e), i) for e in payload for i in ids(e)}
    shared = {(namespace(e), i) for e in karting_data() for i in ids(e)}
    collisions = new & (index | shared)
    missing = sorted(dependency_refs(payload) - index - new - shared)
    print('Farm dependency audit:', json.dumps({'collisions': sorted(collisions), 'unresolved': missing}))
    if not report:
        assert not collisions
        assert not missing
    return {'collisions': sorted(collisions), 'unresolved': missing, 'scope': 'Direct candidate mapgen, inline loot, supplied groups and furniture drops; runtime/schema validation pending', 'native_enabled': False}


def prepare(check=False, bn_source=None, audit=False, report_path=None):
    if bn_source:
        result = validate_bn(bn_source, audit)
        if report_path:
            report_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    text = json.dumps(prepare_data(), ensure_ascii=True, indent=2) + '\n'
    path = FOLDER / 'CANDIDATE.json'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    p.add_argument('--audit', action='store_true')
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source, a.audit, a.report)
