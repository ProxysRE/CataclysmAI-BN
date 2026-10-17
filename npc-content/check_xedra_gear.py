#!/usr/bin/env python3
"""Check source identities/transforms and functional coverage/seal changes."""
import copy
import json
from prepare_xedra_gear import sources, definitions, prepare
from prepare_rural_churches import sources as church_sources
from stage_xedra_church import stage

files = sources()
bn = next(e for e in json.loads(files['bn/suits_protection.json']) if e.get('id') == 'robofac_enviro_suit')
source = {e['id']: e for e in json.loads(church_sources()['dda/suits_protection.json']) if isinstance(e.get('id'), str)}
normal, casual = definitions()
assert normal['copy-from'] == bn['id']
for converted in (normal, casual):
    original = source[converted['id']]
    assert converted['name'] == original['name']
    assert converted['description'] == original['description']
    assert converted['use_action'] == original['use_action']
    assert converted['type'] == 'ARMOR'
assert normal['use_action']['target'] == casual['id']
assert casual['use_action']['target'] == normal['id']
assert casual['covers'] == ['legs', 'feet']
assert casual['delete'] == source['robofac_enviro_suit_casual']['delete']
assert set(casual['delete']['flags']) <= set(bn['flags'])
assert all(key not in normal for key in ('armor', 'material_thickness', 'encumbrance', 'pocket_data'))
assert casual['copy-from'] == normal['id']
prepare(check=True)
report = stage()
selected = {e['id'] for e in report['equipment_definitions']}
assert {'papr_half_mask', 'basic_papr_belt_off', 'basic_papr_belt_on', 'gasfilter_med', 'gasfilter_m', 'medium_battery_cell', 'heavy_battery_cell'} <= selected
assert {'battery', 'gasfilter_m'} <= {e['id'] for e in report['ammunition_type_definitions']}
assert {'PAPR_MASK_ACTIVATE', 'PAPR_MASK', 'PAPR_BLOWER'} <= {e['to'] for e in report['equipment_reference_edges'] if e['kind'] == 'native_use_action'}
materials = {e['to'] for e in report['equipment_reference_edges'] if e['from'] == 'basic_papr_belt_off' and e['kind'] == 'material'}
assert materials == {'plastic', 'rubber'}
assert not any(e['kind'] == 'material' and e['to'] in {'type', 'portion'} for e in report['equipment_reference_edges'])
assert not any('papr' in e['id'] for e in definitions())
print('PASS: source suit identities and transforms, BN armor reuse, casual seal removal, preserved PAPR component and ammunition chain')
