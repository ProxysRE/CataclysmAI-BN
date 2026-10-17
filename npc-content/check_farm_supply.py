#!/usr/bin/env python3
"""Guard complete staged farm-shop geometry and BN-specific adaptations."""
import copy
import json
from collections import Counter
from prepare_farm_supply import prepare, prepare_data, sources, MAP_GROUPS, SUPPLY_GROUPS
from prepare_regional_locations import build, references
from quest_dependency_graph import namespace, ids

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
assert {e['id'] for e in payload if e['type'] == 'item_group'} == set(MAP_GROUPS + SUPPLY_GROUPS)
assert {e['id'] for e in payload if e['type'] == 'GENERIC'} == {'pallet'}
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
