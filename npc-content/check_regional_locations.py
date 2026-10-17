#!/usr/bin/env python3
"""Guard source geometry and typed dependency boundaries in bulk staging."""
import json
import subprocess
import sys
from quest_dependency_graph import namespace, ids
from prepare_regional_locations import ROOT, OUT, SITES, build, read_bundle, references

files, _ = read_bundle()
outputs = build()
assert sum(e.get('type') == 'talk_topic' for e in outputs['nursing_home.json']) == 59
assert sum(e.get('type') == 'effect_on_condition' for e in outputs['nursing_home.json']) == 4
assert [e['id'] for e in outputs['karting.json'] if e.get('type') == 'vehicle'] == ['go_kart']
assert {d['id'] for d in outputs['TRANSFER_REPORT.json']['sites'][3]['dependencies'] if d['type'] == 'effect_on_condition'} == {'EOC_NURSING_HOME_RECEPTIONIST', 'EOC_NURSING_HOME_RECEP_MANAGER', 'EOC_NURSING_HOME_COO', 'EOC_NURSING_HOME_SCI'}
slots = 0
for site, names in SITES.items():
    identities = [(namespace(e), identifier) for e in outputs[site + '.json'] for identifier in ids(e)]
    assert len(identities) == len(set(identities)), ('duplicate typed declaration', site)
    originals = [e for name in names for e in json.loads(files[name]) if e.get('type') == 'mapgen']
    candidates = [e for e in outputs[site + '.json'] if e.get('type') == 'mapgen']
    assert len(originals) == len(candidates)
    for original, candidate in zip(originals, candidates):
        # Includes matrix coordinates, update/nested IDs, rotation and all rows.
        assert {k: v for k, v in original.items() if k != 'object'} == {k: v for k, v in candidate.items() if k != 'object'}
        for key, value in original.get('object', {}).items():
            if key in ('rows', 'fill_ter', 'rotation', 'predecessor_mapgen') or key.startswith('place_'):
                assert candidate['object'][key] == value, (site, key)
        assert not any(p in {e.get('id') for n in names for e in json.loads(files[n]) if e.get('type') == 'palette'}
                       for p in candidate.get('object', {}).get('palettes', []))
    report = next(r for r in outputs['TRANSFER_REPORT.json']['sites'] if r['site'] == site)
    assert not report['unregistered_mapgen_terrain_ids'], site
    assert report['placements'], site
    slots += report['mapgen_terrain_slots']
assert slots == 235
assert len([e for value in outputs.values() if isinstance(value, list) for e in value if e.get('nested_mapgen_id')]) == 7
assert ('item_group', 'SUS_toilet') in references({'items': {'&': {'item': 'SUS_toilet', 'chance': 50}}})
assert ('vehicle', 'go_kart') in references({'vehicles': {'K': {'vehicle': 'go_kart'}}})
assert ('nested_mapgen', 'kitchen') in references({'nested': {'K': {'chunks': [['kitchen', 90], ['null', 10]]}}})
assert ('nested_mapgen', 'null') not in references({'nested': {'K': {'chunks': ['null']}}})
# Names, local parameter names, weights and furniture glyphs are never IDs.
assert references({'terrain': {'x': {'param': 'floor_color', 'fallback': 't_floor'}}, 'name': 'Some Name'}) == [('terrain', 't_floor')]
subprocess.run([sys.executable, str(ROOT / 'prepare_regional_locations.py'), '--check'], check=True)
print('Five complete staged sites; 235 terrain slots; source geometry preserved; not native-enabled')

with_native = build(native_payloads=[ROOT / 'native/dda_karting_circuit.json'])
farm = next(r for r in with_native['TRANSFER_REPORT.json']['sites'] if r['site'] == 'farm_supply')
for identifier in ('cash_register_random', 'cash_register_looted'):
    dependency = next(d for d in farm['dependencies'] if d['type'] == 'item_group' and d['id'] == identifier)
    assert dependency['status'] == 'provided_by_native_port_review_adaptation'
assert with_native['farm_supply.json'] == outputs['farm_supply.json']
print('PASS: shared native cash providers recognized without mutating staged farm geometry')

inline = {'items': {'X': {'item': {'subtype': 'collection', 'entries': [{'group': 'guns_rifle_common_display', 'prob': 40}, {'item': 'fishing_hook_basic', 'count': [2, 5]}, {'item': 'water_clean', 'container-item': 'bottle_plastic'}]}, 'chance': 100}}}
assert set(references(inline)) == {('item_group', 'guns_rifle_common_display'), ('item', 'fishing_hook_basic'), ('item', 'water_clean'), ('item', 'bottle_plastic')}
print('PASS: inline loot collections expose typed group/item/container dependencies')

assert references({'place_corpses': [{'group': 'FERAL_HUMANS', 'x': 7, 'y': 42}]}) == [('monstergroup', 'FERAL_HUMANS')]
assert references({'corpses': {'c': {'group': 'FERAL_HUMANS', 'age': 3}}}) == [('monstergroup', 'FERAL_HUMANS')]

retirement = outputs['retirement_community.json']
assert sum(e.get('type') == 'talk_topic' for e in retirement) == 13
assert sum(e.get('type') == 'effect_on_condition' for e in retirement) == 2
assert {e['id'] for e in retirement if e.get('type') == 'effect_on_condition'} == {'EOC_RET_COMM_HOME', 'EOC_RET_COMM_OFFICE'}
