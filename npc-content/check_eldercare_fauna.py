#!/usr/bin/env python3
"""Check source profiles, BN actor schema and unduplicated weapon drops."""
import copy
from prepare_eldercare_fauna import native_data, find, prepare, MUTANTS, GROUPS, ALIASES
from prepare_eldercare_loot import native_data as loot_data
from bn_counterparts import adapt_entry

payload = native_data()
assert len(payload) == 13
by_id = {e.get('id', e.get('name')): e for e in payload if e['type'] != 'MONSTER'}
monsters = {e['id']: e for e in payload if e['type'] == 'MONSTER'}
for name, weapon in [('mon_feral_cop', 'tonfa'), ('mon_feral_sapien_spear', 'spear_knife')]:
    mon = monsters[name]
    assert mon['starting_ammo'] == {'rock': 0}
    assert mon['special_attacks'] == [['PARROT_AT_DANGER', 5]]
    assert by_id[mon['monster_weapon']]['items'] == [[weapon, 100]]
    assert mon['copy-from'] == 'mon_feral_human_pipe'
original_outfit = next(e for e in loot_data() if e.get('id') == 'feral_sapien_death_drops_spear')
assert by_id['dda_feral_spear_outfit']['entries'] == original_outfit['entries'][1:]
assert monsters['mon_feral_sapien_spear']['death_drops'] == 'dda_feral_spear_outfit'
for name in MUTANTS:
    mon, source = monsters[name], find(name)
    for key in ('name', 'description', 'hp', 'speed', 'volume', 'weight'):
        assert mon[key] == source[key], (name, key)
    assert mon['upgrades'] is False
    assert mon['melee_damage'] == source.get('melee_damage', [])
    assert not {'HAS_MIND', 'EATS', 'PULP_PRYING', 'SMALLSLUDGETRAIL'} & set(mon['flags'])
    for attack in mon['special_attacks']:
        if isinstance(attack, dict):
            assert attack['type'] in ('melee', 'bite', 'leap')
            assert not {'range', 'condition', 'grab_data', 'throw_strength', 'infection_chance'} & attack.keys()
assert monsters['mon_mutant_mollusk']['armor_fire'] == 50
assert monsters['mon_mutant_mollusk']['armor_bullet'] == 70
assert 'CAMOUFLAGE' in monsters['mon_mutant_camouflaged']['flags']
assert monsters['mon_mutant_arthropod']['emit_fields'][0]['emit_id'] == 'dda_eldercare_web'
assert by_id['dda_eldercare_web']['field'] == 'fd_web'
for name in GROUPS:
    original, group = find(name), by_id[name]
    assert group['freq_total'] == sum(e.get('weight', 1) for e in original['monsters'])
    assert len(original['monsters']) == len(group['monsters'])
    for source, target in zip(original['monsters'], group['monsters']):
        expected = copy.deepcopy(source)
        expected['freq'] = expected.pop('weight', 1)
        expected.setdefault('cost_multiplier', 1)
        # Apply the already audited medical-zombie counterpart rule.
        assert target == adapt_entry(expected)
assert len(ALIASES) == 2
prepare(check=True)
print('PASS: six source creature profiles; three exact direct group weight tables; BN weapon ownership, actors, armor and juvenile counterparts')
