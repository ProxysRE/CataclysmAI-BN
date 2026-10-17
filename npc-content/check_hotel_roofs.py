#!/usr/bin/env python3
"""Check cap geometry and additive placement against both pinned sources."""
import copy
import json
from prepare_hotel_roofs import prepare_data, prepare, sources, CITY
from prepare_radio_stations import prepare_data as radio_data
from compare_location_catalog import read_sources

catalog, _ = read_sources()
payload, city, report = prepare()
base = json.loads(catalog['bn/' + CITY])
for old, new in zip(base, city):
    expected = copy.deepcopy(old)
    if old.get('id') in ('hotel_1', 'hotel_2', 'hotel_3'):
        expected['overmaps'].extend(report['placements'][old['id']])
    assert new == expected, old.get('id')
    if old.get('id') in report['placements']:
        assert [e['point'] for e in new['overmaps'][-3:]] == [[0, 3, 5], [1, 3, 5], [2, 3, 5]]
# Compose on the radio candidate too; neither package can erase the other's
# changes to the shared city catalogue.
radio, _, _ = radio_data()
_, combined, _ = prepare_data(radio[CITY])
for original in json.loads(radio[CITY]):
    after = next(e for e in combined if e.get('id') == original.get('id'))
    if original.get('id') not in report['placements']:
        assert after == original
source_cap = next(e for e in json.loads(sources()['dda']) if 'hotel_tower_6_1_9' in str(e.get('om_terrain')))
assert payload[1]['object'] == source_cap['object']
assert payload[0]['id'] == source_cap['om_terrain'][0]
assert report['status'] == 'native_code_prepared_not_runtime_validated'
print('PASS: three hotel variants, exact DDA cap geometry, BN interiors preserved, radio composition retained')
