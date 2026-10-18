#!/usr/bin/env python3
"""Guard complete staged farm-shop geometry and BN-specific adaptations."""
import copy
import json
from collections import Counter
from prepare_farm_supply import ROOT, prepare, prepare_data, sources, MAP_GROUPS, SUPPLY_GROUPS, dependency_refs
from prepare_regional_locations import index_entries, BUILTIN_IDS
from prepare_karting import prepare_data as karting_data
from prepare_regional_locations import build, references
from quest_dependency_graph import namespace, ids
from export_bn_ids import read_cache

payload = prepare_data()
original = build()['farm_supply.json']
old_maps = [e for e in original if e['type'] == 'mapgen']
maps = [e for e in payload if e['type'] == 'mapgen' and e.get('nested_mapgen_id') != '1x1_bash']
assert len(old_maps) == len(maps) == 4
for old, new in zip(old_maps, maps):
    for key in ('rows', 'fill_ter', 'rotation', 'place_monster', 'place_corpses', 'place_liquids', 'place_nested', 'nested', 'set'):
        assert old['object'].get(key) == new['object'].get(key), (old.get('om_terrain'), key)
    assert old.get('om_terrain') == new.get('om_terrain')
    if 'rows' in new['object']:
        assert len(new['object']['rows']) == 48
        assert {len(r) for r in new['object']['rows']} == {48}
    if 'furniture' in new['object']:
        assert 'm' not in new['object']['furniture']
        assert new['object']['terrain']['m'] == 't_atm'
        assert 'f_chest_minifreezer' not in json.dumps(new['object']['furniture'])
assert not any('travel_cost_type' in e for e in payload)
identity = [(namespace(e), i) for e in payload for i in ids(e)]
assert len(identity) == len(set(identity))
assert sum(len(row) for e in maps for row in e.get('om_terrain', [])) == 12
base_groups = set(MAP_GROUPS + SUPPLY_GROUPS + ['ammo_hunting', 'box_of_batteries_unopened', 'child_hats', 'supplies_woodcrafts', 'discount_cards'])
packed = set(SUPPLY_GROUPS + ['cattlefodder_bag_canvas_50', 'birdfood_bag_canvas_60', 'box_of_batteries_unopened'])
assert {e['id'] for e in payload if e['type'] == 'item_group'} == base_groups | {g + '_contents' for g in packed}
assert not any('container-item' in e for e in payload if e['type'] == 'item_group')
assert {e['id'] for e in payload if e['type'] == 'GENERIC'} == {'pallet', 'rock_large'}
assert not any(e.get('id') in ('banknotes', 'coins', 'money_one', 'coin_penny', 'money_bundle') for e in payload)
for name in SUPPLY_GROUPS:
    group = next(e for e in payload if e.get('id') == name)
    assert group['entries'][0]['item'] == ('30gal_barrel' if name == 'quicklime_barrel' else 'bag_canvas')
    contents = next(e for e in payload if e.get('id') == name + '_contents')
    assert 'charges' in contents['items'][0] and 'count' not in contents['items'][0]
# The candidate retains the source corpse feature; the new native action
# must pass runtime checks before this map is installed.
assert sum(len(e['object'].get('place_corpses', [])) for e in maps) == 1
assert ('item_group', 'guns_rifle_common_display') in references(maps[0]['object'])
assert any(e.get('nested_mapgen_id') == '1x1_bash' for e in payload)
prepare(check=True)
print('PASS: both full farm variants, common roof, source damage/corpse records, BN charge units and currency reuse; native payload prepared; runtime checks pending')

cache = read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')
assert cache['bn_pin'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
index = set(map(tuple, cache['identifiers']))
new = index_entries(payload) - BUILTIN_IDS
shared = index_entries(karting_data()) - BUILTIN_IDS
assert not new & (index | shared)
assert not dependency_refs(payload) - index - new - shared
assert not any(e.get('id') in ('helmet_riding', 'rock_flaking', 'flint', 't_carpet_concrete_red') for e in payload)
assert 'helmet_bike_modified' not in json.dumps(payload)
assert ('item', 'helmet_bike') in dependency_refs(payload)
dremel = next(e for e in payload if e.get('id') == 'dremel')
assert dremel['copy-from'] == 'angle_grinder' and dremel['power_draw'] == 175000
assert len(dremel['qualities']) == 6
wrapper = next(e for e in payload if e.get('id') == 'box_of_batteries_unopened')
assert wrapper['entries'] == [{'item': 'box_medium', 'contents-group': 'box_of_batteries_unopened_contents'}]
batteries = next(e for e in payload if e.get('id') == 'box_of_batteries_unopened_contents')
assert {e['item'] for e in batteries['items']} <= {'light_minus_battery_cell', 'light_battery_cell', 'medium_battery_cell'}
capacities = {'light_minus_battery_cell': 50, 'light_battery_cell': 100, 'medium_battery_cell': 500}
volumes = {'light_minus_battery_cell': 50, 'light_battery_cell': 100, 'medium_battery_cell': 500}
for entry in batteries['items']:
    assert entry['charges'] == capacities[entry['item']]
    assert entry['count'] * volumes[entry['item']] <= 3000
for e in payload:
    if e['type'] == 'item_group':
        refs = references({'items': {'_': {'item': e}}})
        assert ('item_group', 'banknotes') not in refs and ('item_group', 'coins') not in refs
print('PASS: full pinned BN ID cache; direct dependency closure with BN counterparts; native corpse action prepared, Windows runtime checks pending')

from prepare_mapgen_corpses import prepare as check_corpse_action
check_corpse_action()
