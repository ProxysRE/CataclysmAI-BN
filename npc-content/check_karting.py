#!/usr/bin/env python3
"""Check full circuit geometry, native adaptation and dependency preservation."""
import copy
import json
from collections import Counter
from prepare_karting import prepare_data, prepare, sources, GROUPS
from prepare_regional_locations import build, index_entries
from quest_dependency_graph import namespace, ids

payload = prepare_data()
source = build()['karting.json']
original_maps = [e for e in source if e['type'] == 'mapgen']
maps = [e for e in payload if e['type'] == 'mapgen']
assert len(maps) == 3
assert sum(len(row) for e in maps for row in e['om_terrain']) == 27
for old, new in zip(original_maps, maps):
    adapted = copy.deepcopy(new)
    adapted.pop('method')
    for value in adapted['object'].get('vendingmachines', {}).values():
        value['lootable'] = True
    assert adapted == old
    assert len(new['object']['rows']) == 72
    assert {len(row) for row in new['object']['rows']} == {72}
# Every lower half of each ramp has its matching upper-floor half at the
# exact source coordinate; both ramp heights remain distinct BN terrain.
for glyph, upper in [('u', 'D'), ('U', 'd')]:
    lower_cells = {(x, y) for y, row in enumerate(maps[0]['object']['rows']) for x, c in enumerate(row) if c == glyph}
    upper_cells = {(x, y) for y, row in enumerate(maps[1]['object']['rows']) for x, c in enumerate(row) if c == upper}
    assert lower_cells == upper_cells and len(lower_cells) == 24
lower_stairs = [(x, y) for y, row in enumerate(maps[0]['object']['rows']) for x, c in enumerate(row) if c == '<']
upper_stairs = [(x, y) for y, row in enumerate(maps[1]['object']['rows']) for x, c in enumerate(row) if c == '>']
assert lower_stairs == upper_stairs == [(36, 58)]
vehicle = next(e for e in payload if e['type'] == 'vehicle')
original_vehicle = copy.deepcopy(next(e for e in source if e['type'] == 'vehicle'))
for pos in original_vehicle['parts']:
    pos['parts'] = ['xlframe_vertical' if p == 'xlframe#vertical' else p for p in pos['parts']]
assert vehicle == original_vehicle
assert sum(len(pos['parts']) for pos in vehicle['parts']) == 16
special = copy.deepcopy(next(e for e in payload if e['type'] == 'overmap_special'))
old_special = next(e for e in source if e['type'] == 'overmap_special')
assert 'UNIQUE' in special['flags'] and 'OVERMAP_UNIQUE' not in special['flags']
special['flags'] = ['OVERMAP_UNIQUE' if f == 'UNIQUE' else f for f in special['flags']]
for c in special['connections']:
    assert c.pop('connection') == 'local_road'
    c['terrain'] = 'road'
for cell in special['overmaps']:
    if cell.get('overmap') == 's_lot':
        cell['overmap'] = 's_lot_no_sidewalk_south'
assert special == old_special
identities = [(namespace(e), i) for e in payload for i in ids(e)]
assert len(identities) == len(set(identities))
assert Counter(e['type'] for e in payload) == {'mapgen': 3, 'vehicle': 1, 'overmap_terrain': 1, 'overmap_special': 1, 'item_group': 7, 'CONTAINER': 1}
assert not any(e.get('id') == 'coin_quarter' for e in payload)
cash = next(e for e in payload if e.get('id') == 'cash_register')
assert cash['contains'] == '1 L' and cash['rigid']
assert namespace(cash) == 'item'
assert ('item', 'cash_register') in index_entries([cash])
assert not {'pocket_data', 'longest_side', 'to_hit', 'melee_damage'}.intersection(cash)
files = sources()
# The native BN frame loader creates concrete shape IDs from abstract roots.
frames = json.loads(files['bn/data/json/vehicleparts/frames.json'])
assert ('vehicle_part', 'xlframe_vertical') in index_entries(frames)
assert ('vehicle_part', 'xlframe') not in index_entries(frames)
assert not any(e['type'] == 'GENERIC' for e in payload)
assert not any(e.get('id') in ('banknotes', 'coins') for e in payload)
full = next(e for e in payload if e.get('id') == 'cash_register_full_contents')
looted = next(e for e in payload if e.get('id') == 'cash_register_looted_contents')
assert full['items'] == [{'item': 'money_bundle', 'prob': 80, 'count': [1, 3]}]
assert looted['items'] == [{'item': 'money_bundle', 'prob': 15, 'count': 1}, ['survnote', 4]]
money = next(e for e in json.loads(files['bn/data/json/items/generic.json']) if e.get('id') == 'money_bundle')
assert money['volume'] == '250 ml' and money['weight'] == '20 g'
assert money['price'] == '400 USD' and money['price_postapoc'] == '25 cent'
assert 3 * 250 <= 1000
prepare(check=True)
print('PASS: full 27-tile circuit, 48 matched ramp columns, 16-part kart, stock BN money_bundle only; no imported denominations')

assert not any('container-item' in e for e in payload if e['type'] == 'item_group')
for name in ('cash_register_full', 'cash_register_looted', 'cash_register_empty'):
    g = next(e for e in payload if e.get('id') == name)
    assert g['entries'] == [{'item': 'cash_register', 'contents-group': name + '_contents'}]
