#!/usr/bin/env python3
"""Guard source probabilities, BN recipe substitutions and the complete pigeon cycle."""
import json
from prepare_eldercare_loot import native_data, find, prepare, SAMPLES, feral_drop

payload = native_data()
assert len(payload) == 11
by_id = {e['id']: e for e in payload if 'id' in e}
old = find('SUS_science_personal_effects')['items']
new = by_id['SUS_science_personal_effects']['items']
assert len(old) == len(new)
def probability(e):
    return e[1] if isinstance(e, list) else e.get('prob', 100)
assert [probability(e) for e in old] == [probability(e) for e in new]
assert by_id['lanyard']['storage'] == '150 ml'
assert by_id['lanyard']['encumbrance'] == 0
assert not {'pocket_data', 'subtypes', 'armor', 'longest_side'} & by_id['lanyard'].keys()
assert by_id['cigar_box_opened']['entries'] == [{'item': 'box_medium', 'contents-group': 'cigar_box_opened_contents'}]
assert by_id['cigar_box_opened_contents']['entries'][0] == {'item': 'cigar', 'charges': [0, 25]}
assert by_id['cigar_box_opened_contents']['entries'][2] == {'item': 'scissors', 'prob': 50}
assert by_id['feral_sapien_death_drops_spear'] == feral_drop(find('feral_sapien_death_drops_spear'))
assert '"damage":' not in json.dumps(by_id['feral_sapien_death_drops_spear'])
source = find('lab_mutagen_ingredients_fridge')['entries']
converted = by_id['lab_mutagen_ingredients_fridge']['entries']
assert len(source) == len(converted)
for a, b in zip(source, converted):
    assert a.get('prob', 100) == b.get('prob', 100)
    assert b['item'] == SAMPLES.get(a['item'], (a['item'],))[0]
    assert a.get('count') == b.get('count', b.get('charges'))
assert '"variant":' not in json.dumps(by_id['nursing_home_clothes'])
assert [r.get('prob', 100) for r in by_id['nursing_home_clothes']['entries']] == [100, 100, 50]
assert by_id['mon_pigeon']['reproduction'] == {'baby_egg': 'egg_pigeon', 'baby_count': 3, 'baby_timer': 32}
assert by_id['mon_pigeon_chick']['upgrades'] == {'age_grow': 10, 'into': 'mon_pigeon'}
assert by_id['egg_pigeon']['rot_spawn'] == 'GROUP_EGG_PIGEON'
assert next(e for e in payload if e['type'] == 'monstergroup')['default'] == 'mon_pigeon_chick'
assert not any(e.get('id') in ('banknotes', 'coins', 'money_bundle', 'cash_card') for e in payload)
prepare(check=True)
print('PASS: staff odds, 22 recipe-supported sample substitutions, packed individual cigars, BN feral gear and closed pigeon lifecycle')
