#!/usr/bin/env python3
"""Port both complete farm shops using BN appliances, ATM and resource units."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from prepare_regional_locations import build, references, index_entries, BUILTIN_IDS
from prepare_karting import prepare_data as karting_data, sources as karting_sources
from quest_dependency_graph import namespace, ids

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'farm_supply'
PAYLOAD = 'data/json/dda_farm_supply.json'
MAP_GROUPS = ['farm_supply_soil_and_sand', 'farm_supply_rocks', 'farm_supply_quicklime_and_saltpetre',
              'farm_supply_wire', 'farm_supply_animal_feed', 'farm_supply_riding_gear', 'farm_supply_floor_surprises',
              'cattlefodder_bag_canvas_50', 'birdfood_bag_canvas_60']
SUPPLY_GROUPS = ['sandbag', 'earthbag', 'cement_bag', 'quicklime_bag', 'quicklime_barrel', 'saltpeter_canvas_bag_part']
FURNITURE = ['f_pallet_brick', 'f_pallet_cement', 'f_stack_plank']
GROUP_ALIASES = {'SUS_fridge_breakroom': 'SUS_fridge', 'SUS_trash_dumpster': 'trash_dumpster',
                 'SUS_trash_trashcan_public': 'trash_cart', 'SUS_trash_floor': 'trash_cart', 'hiking': 'camping', 'ammo_common_loose': 'ammo_common'}


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
        return [adapt_drop(child) for child in value if not (isinstance(child, dict) and child.get('group') == 'coins')]
    if not isinstance(value, dict):
        return value
    out = {k: adapt_drop(v) for k, v in value.items()}
    if out.get('item') in ('material_sand', 'material_soil', 'material_cement', 'material_quicklime', 'chem_saltpetre', 'material_limestone') and 'count' in out:
        out['charges'] = out.pop('count')
    if isinstance(out.get('item'), str):
        out['item'] = {'cotton_patchwork': 'rag', 'lc_wire': 'wire', 'mc_wire': 'wire', 'hc_wire': 'wire', 'qt_wire': 'wire'}.get(out['item'], out['item'])
    if isinstance(out.get('group'), str):
        out['group'] = GROUP_ALIASES.get(out['group'], out['group'])
        if out['group'] == 'wallets':
            out.pop('group')
            out['item'] = 'cash_card'
        elif out['group'] == 'banknotes':
            out.pop('group')
            out['item'] = 'money_bundle'
            out['count'] = 1
        elif out['group'] in ('glue_weak_professional', 'glue_strong_professional'):
            kind = out.pop('group')
            out['item'] = 'bone_glue' if kind == 'glue_weak_professional' else 'superglue'
    if out.get('item') == 'bag_durasack':
        out['item'] = 'bag_canvas'
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
            for glyph, binding in obj.get('items', {}).items():
                obj['items'][glyph] = adapt_drop(binding)
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
    additional = {
        'dda/data/json/itemgroups/Weapons_Mods_Ammo/ammo/ammo.json': ['ammo_hunting'],
        'dda/data/json/itemgroups/electronics.json': ['box_of_batteries_unopened'],
        'dda/data/json/itemgroups/Clothing_Gear/gear_civilian.json': ['child_hats'],
        'dda/data/json/itemgroups/supplies.json': ['supplies_woodcrafts'],
        'dda/data/json/itemgroups/Clothing_Gear/wallets.json': ['discount_cards']
    }
    for path, names in additional.items():
        for original in json.loads(files[path]):
            if original.get('id') not in names:
                continue
            group = adapt_drop(original)
            if group['id'] == 'ammo_hunting':
                totals = {'ammo_rifle_common_full': 0, 'ammo_shotgun_common_full': 0, 'ammo_pistol_common_full': 0}
                for entry in original['entries']:
                    caliber = entry['group'].removeprefix('boxed_')
                    target = 'ammo_shotgun_common_full' if caliber in ('12', '20', '410') else 'ammo_pistol_common_full' if caliber in ('357', '44', '10mm', '454', '500', '50AE') else 'ammo_rifle_common_full'
                    totals[target] += entry['prob']
                group['entries'] = [{'group': name, 'prob': weight} for name, weight in totals.items()]
            elif group['id'] == 'box_of_batteries_unopened':
                group['container-item'] = 'box_medium'
                capacities = {e['id']: e['capacity'] for e in json.loads(files['bn/data/json/items/battery.json']) if 'capacity' in e and 'id' in e}
                for entry in group['items']:
                    entry['item'] = {'light_minus_disposable_cell': 'light_minus_battery_cell', 'light_cell_rechargeable': 'light_battery_cell'}.get(entry['item'], entry['item'])
                    entry['charges'] = capacities[entry['item']]
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
    stone = {e['id']: e for e in json.loads(files['dda/data/json/items/resources/stone.json']) if isinstance(e.get('id'), str)}
    for name in ('rock_flaking', 'flint'):
        original = stone[name]
        rock = {'type': 'AMMO', 'id': name, 'copy-from': 'rock' if name == 'rock_flaking' else 'rock_flaking',
                'name': original['name'], 'description': original['description']}
        if name == 'rock_flaking':
            rock.update(weight=original['weight'], volume=original['volume'], bashing=original['melee_damage']['bash'],
                        damage=original['damage'], range=original['range'], dispersion=original['dispersion'],
                        loudness=original['loudness'], count=1, stack_size=1)
        result.append(rock)
    large = copy.deepcopy(stone['rock_large'])
    large['type'] = 'GENERIC'
    large['category'] = 'rocks'
    large['bashing'] = large.pop('melee_damage')['bash']
    large.pop('longest_side')
    result.append(large)
    riding = next(e for e in json.loads(files['dda/data/json/items/armor/helmets.json']) if e.get('id') == 'helmet_riding')
    helmet = {'type': 'ARMOR', 'id': 'helmet_riding', 'copy-from': 'helmet_bike', 'looks_like': 'helmet_bike',
              'bashing': riding['melee_damage']['bash'], 'extend': {'flags': ['WATERPROOF', 'STURDY', 'SUN_GLASSES']}}
    for field in ('name', 'description', 'weight', 'volume', 'price', 'price_postapoc', 'color', 'warmth'):
        helmet[field] = riding[field]
    result.append(helmet)
    dremel = next(e for e in json.loads(files['dda/data/json/items/tool/workshop.json']) if e.get('id') == 'dremel')
    tool = {'type': 'TOOL', 'id': 'dremel', 'copy-from': 'angle_grinder', 'looks_like': 'angle_grinder',
            'bashing': dremel['melee_damage']['bash'], 'cutting': 0,
            'qualities': [[quality['id'], quality['level']] for quality in dremel['charged_qualities']],
            'power_draw': 175000}
    for field in ('name', 'description', 'weight', 'volume', 'price', 'price_postapoc', 'symbol', 'color'):
        tool[field] = dremel[field]
    result.append(tool)
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
        if e['type'] == 'item_group':
            refs.update(references({'items': {'_': {'item': e}}}))
        elif e['type'] in ('furniture', 'terrain'):
            refs.update(visit(e))
        if namespace(e) == 'item':
            if 'copy-from' in e:
                refs.add(('item', e['copy-from']))
            for quality in e.get('qualities', []):
                refs.add(('tool_quality', quality[0]))
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
    new = index_entries(payload) - BUILTIN_IDS
    shared = index_entries(karting_data()) - BUILTIN_IDS
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
