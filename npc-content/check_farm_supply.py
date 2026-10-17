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
identity = [(namespace(e), i) for e in payload for i in ids(e)]
assert len(identity) == len(set(identity))
assert sum(len(row) for e in maps for row in e.get('om_terrain', [])) == 12
assert {e['id'] for e in payload if e['type'] == 'item_group'} == set(MAP_GROUPS + SUPPLY_GROUPS + ['ammo_hunting', 'box_of_batteries_unopened', 'child_hats', 'supplies_woodcrafts', 'discount_cards'])
assert {e['id'] for e in payload if e['type'] == 'GENERIC'} == {'pallet', 'rock_large'}
assert not any(e.get('id') in ('banknotes', 'coins', 'money_one', 'coin_penny', 'money_bundle') for e in payload)
for e in payload:
    if e.get('id') in SUPPLY_GROUPS:
        if e['id'] != 'quicklime_barrel':
            assert e['container-item'] == 'bag_canvas'
        assert 'charges' in e['items'][0] and 'count' not in e['items'][0]
# The candidate deliberately retains the unsupported corpse feature. It is
# a visible integration blocker, never silently dropped from the source map.
assert sum(len(e['object'].get('place_corpses', [])) for e in maps) == 1
assert ('item_group', 'guns_rifle_common_display') in references(maps[0]['object'])
assert any(e.get('nested_mapgen_id') == '1x1_bash' for e in payload)
prepare(check=True)
print('PASS: both full farm variants, common roof, source damage/corpse records, BN charge units and currency reuse; staging only')

cache = read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')
assert cache['bn_pin'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
index = set(map(tuple, cache['identifiers']))
new = index_entries(payload) - BUILTIN_IDS
shared = index_entries(karting_data()) - BUILTIN_IDS
assert not new & (index | shared)
assert dependency_refs(payload) - index - new - shared == {('item_group', 'helmet_bike_modified')}
helmet = next(e for e in payload if e.get('id') == 'helmet_riding')
assert helmet['copy-from'] == 'helmet_bike'
dremel = next(e for e in payload if e.get('id') == 'dremel')
assert dremel['copy-from'] == 'angle_grinder' and dremel['power_draw'] == 175000
assert len(dremel['qualities']) == 6
batteries = next(e for e in payload if e.get('id') == 'box_of_batteries_unopened')
assert batteries['container-item'] == 'box_medium'
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
print('PASS: full pinned BN ID cache; only modular-helmet group remains unresolved; native corpse bridge still required')
