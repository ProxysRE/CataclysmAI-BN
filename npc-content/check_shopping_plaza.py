#!/usr/bin/env python3
"""Reject roofs over parking/vegetation and loss of existing city edits."""
import copy
import json
from prepare_shopping_plaza import sources, prepare_data, prepare, CITY
from prepare_tower_expansions import prepare_data as composed_data
from compare_location_catalog import read_sources

files = sources()
bn, dda = [json.loads(files[s]) for s in ('bn', 'dda')]
# Check every solid rooftop cell against the actual BN ground footprint.
for ground, roof, offset in [(bn[1], dda[3], 24), (bn[2], dda[4], 0)]:
    for y, row in enumerate(roof['object']['rows']):
        for x, symbol in enumerate(row):
            if symbol != ' ':
                assert ground['object']['rows'][y + offset][x] in ' |-1+5AFH', (x, y, symbol)
catalog, _ = read_sources()
base = json.loads(catalog['bn/' + CITY])
payload, city = prepare_data(base)
assert len(payload[0]['id']) == 7
for old, new in zip(base, city):
    expected = copy.deepcopy(old)
    if old.get('id') == 'shopping_plaza':
        expected['overmaps'].extend(new['overmaps'][-7:])
        assert len(new['overmaps']) == 19
    assert expected == new
outputs, _ = composed_data()
combined = json.loads(outputs[CITY])
for name in ('station_radio', 'station_radio_1'):
    assert len(next(e for e in combined if e.get('id') == name)['overmaps']) == 7
for name in ('hotel_1', 'hotel_2', 'hotel_3'):
    assert len([p for p in next(e for e in combined if e.get('id') == name)['overmaps'] if p['point'][2] == 5]) == 3
assert next(e for e in combined if e.get('id') == 'shopping_plaza') == next(e for e in city if e.get('id') == 'shopping_plaza')
for original, converted in zip(dda[3:], payload[1:]):
    assert original['object'] == converted['object']
prepare(check=True)
print('PASS: seven exact DDA plaza roofs, every solid cell supported by existing BN building, all city expansions retained')
