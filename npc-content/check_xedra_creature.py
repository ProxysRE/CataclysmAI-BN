#!/usr/bin/env python3
"""Check exact particles and item data, scoped native edits and legacy defaults."""
import copy
import json
from prepare_xedra_creature import payload, sources, replacements, patch_sections, prepare
from prepare_rural_churches import sources as church_sources

p = payload()
church = church_sources()
for name, filename in [('fd_twisting_mass_dust', 'field_type.json'), ('emit_twisting_mass_dust', 'emit.json')]:
    original = next(e for e in json.loads(church['dda/' + filename]) if e.get('id') == name)
    if name == 'fd_twisting_mass_dust':
        original = copy.deepcopy(original)
        level = original['intensity_levels'][0]
        assert level.pop('concentration') == 1
        original['intensity_levels'] = [copy.deepcopy(level) for _ in range(3)]
    assert next(e for e in p if e.get('id') == name) == original
original = next(e for e in json.loads(church['dda/extradimensional_artifacts.json']) if e.get('id') == 'inert_glowing_string')
expected = copy.deepcopy(original);expected['type'] = 'GENERIC'
assert p[3] == expected
mon = p[2]
assert mon['hp'] == 20 and mon['speed'] == 10 and mon['grab_strength'] == 35
assert mon['special_attacks'] == [['RANGED_PULL', 20]]
assert mon['ranged_pull_options']['range'] == 5
assert mon['ranged_pull_options']['max_weight_ratio'] == 3.0
source, target = sources(), replacements()
# All stock attacks outside ranged_pull are byte-for-byte preserved.
a, b = 'bool mattack::ranged_pull( monster *z )', '\nbool mattack::grab( monster *z )'
old, new = source['bn/monattack.cpp'], target['monattack.cpp']
assert old[old.index(b):] == new[new.index(b):]
assert old[:old.index(a)] + '' == new[:new.index(a)].replace('#include "vehicle/vpart_position.h"\n', '')
assert 'int ranged_pull_range = 3;' in target['mtype.h']
assert 'float ranged_pull_weight_ratio = 0.0f;' in target['mtype.h']
for flag in ['full_range', 'use_grab_strength', 'respect_seatbelts']:
    assert 'bool ranged_pull_' + flag + ' = false;' in target['mtype.h']
assert 'foe != nullptr && foe->in_vehicle' in new
assert 'here.obstructed_by_vehicle_rotation( prev_point, i )' in new
assert 'here.creature_on_trap( *target )' in new
assert patch_sections().count('+++ b/src/') == 3
prepare(check=True)
print('PASS: adapted BN particle levels/source string, configured native pull, unchanged legacy defaults and other attacks')
