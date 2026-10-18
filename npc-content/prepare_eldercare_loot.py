#!/usr/bin/env python3
"""Close eldercare loot and pigeon references without importing DDA global subsystems."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from export_bn_ids import read_cache
from prepare_regional_locations import references, index_entries, BUILTIN_IDS
from bn_loot_containers import package_groups
from bn_counterparts import adapt_entry

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'eldercare_loot'
PAYLOAD = 'data/json/dda_eldercare_loot.json'
PINS = {'bn': 'c621aaf42fa182473aad10feea2b55647704dcf1', 'dda': 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
SAMPLES = {
    'rabbit_sample': ('carrot', 'mutagen_rabbit'),
    'rat_sample': ('blood_tainted_concentrate', 'mutagen_rat'),
    'chiropteran_sample': ('animal_blood_concentrate', 'mutagen_beast'),
    'mouse_sample': ('animal_blood_concentrate', 'mutagen_mouse'),
    'fish_sample': ('fish', 'mutagen_fish'),
    'gastropod_sample': ('clam', 'mutagen_cephalopod'),
    'batrachian_sample': ('animal_blood_concentrate', 'mutagen_beast'),
    'insect_sample': ('assorted_bugs', 'mutagen_insect'),
    'cattle_sample': ('animal_blood_concentrate', 'mutagen_cattle'),
    'spider_sample': ('chitin_piece', 'mutagen_spider'),
    'troglobite_sample': ('animal_blood_concentrate', 'mutagen_troglobite'),
    'lizard_sample': ('scute_piece', 'mutagen_lizard'),
    'ursine_sample': ('animal_blood_concentrate', 'mutagen_ursine'),
    'beast_sample': ('animal_blood_concentrate', 'mutagen_beast'),
    'human_sample': ('meat_tainted', 'mutagen'),
    'cephalopod_sample': ('clam', 'mutagen_cephalopod'),
    'lupine_sample': ('animal_blood_concentrate', 'mutagen_lupine'),
    'feline_sample': ('animal_blood_concentrate', 'mutagen_feline'),
    'plant_sample': ('veggy', 'mutagen_plant'),
    'slime_sample': ('slime_scrap', 'mutagen_slime'),
    'bird_sample': ('feather', 'mutagen_bird'),
    'crustacean_sample': ('chitin_piece', 'mutagen_spider'),
}
ITEM_ALIASES = {'spearsling_canvas': 'spearsling', 'ballistic_vest_heavy': 'ballistic_vest_esapi',
                'level_3_vest': 'kevlar', 'armor_riot_arm': 'armguard_hard', 'armor_riot_leg': 'legguard_hard'}
GROUP_ALIASES = {'survivor_basic_feet': 'survivorzed_boots', 'survivor_basic_hands': 'survivorzed_gloves',
                 'survivor_basic_pants': 'survivorzed_bottoms', 'survivor_basic_shirt': 'survivorzed_tops',
                 'ammo_common_boxed_used': 'ammo_common'}


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert m['pins'] == PINS
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / part).read_text() for part in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == m['files'][path]
        if path.endswith('.json'):
            json.loads(text)
    return files


def find(name, game='dda'):
    entries = [e for path, text in sources().items() if path.startswith(game + '/') and path.endswith('.json')
               for e in json.loads(text) if e.get('id') == name]
    assert len(entries) == 1, (name, game, len(entries))
    return copy.deepcopy(entries[0])


def feral_drop(node):
    if isinstance(node, list):
        return [feral_drop(v) for v in node]
    if not isinstance(node, dict):
        return node
    result = {k: feral_drop(v) for k, v in node.items()}
    if 'item' in result:
        result['item'] = ITEM_ALIASES.get(result['item'], result['item'])
    if 'group' in result:
        result['group'] = GROUP_ALIASES.get(result['group'], result['group'])
    if 'damage' in result:
        damage = result.pop('damage')
        result['damage-min'], result['damage-max'] = damage if isinstance(damage, list) else (damage, damage)
    return result


def staff_effects():
    result = find('SUS_science_personal_effects')
    groups_to_items = {'civilian_memory_cards': 'mobile_memory_card', 'box_of_contact_lens_any': 'contacts',
                      'adderall_bottle_plastic_pill_prescription_1_10': 'adderall',
                      'antiparasitic_bottle_plastic_pill_prescription_1_10': 'antiparasitic',
                      'diazepam_bottle_plastic_pill_prescription_1_10': 'diazepam'}
    entries = []
    for original in result['items']:
        entry = copy.deepcopy(original)
        if isinstance(entry, list):
            if entry[0] == 'steroid_eyedrops':
                entry[0] = 'eyedrops'
        elif entry.get('group') == 'wallets_science':
            entry = {'collection': [{'item': 'cash_card'}, {'item': 'id_science'}], 'prob': entry['prob']}
        elif entry.get('group') == 'civilian_phones':
            entry['group'] = 'phones'
        elif entry.get('group') in groups_to_items:
            group = entry.pop('group')
            entry['item'] = groups_to_items[group]
            if group.endswith('_prescription_1_10'):
                entry['charges'] = [1, 10]
        entries.append(entry)
    result['items'] = entries
    return result


def refrigerator():
    result = find('lab_mutagen_ingredients_fridge')
    found = set()
    for entry in result['entries']:
        item = entry.get('item')
        if item in SAMPLES:
            found.add(item)
            entry['item'] = SAMPLES[item][0]
            if entry['item'] in ('animal_blood_concentrate', 'blood_tainted_concentrate'):
                entry['charges'] = entry.pop('count')
        # BN containers do not use DDA's sealed modifier here.
        if 'sealed' in entry:
            assert entry.pop('sealed') is False
    assert found == set(SAMPLES)
    return result


def native_data():
    lanyard = find('lanyard')
    holder = {k: copy.deepcopy(lanyard[k]) for k in ('id', 'name', 'description', 'price', 'price_postapoc',
                                                   'symbol', 'color', 'material', 'weight', 'volume', 'material_thickness')}
    holder.update(type='ARMOR', category='clothing', covers=['torso'], coverage=0, encumbrance=0,
                  warmth=0, storage='150 ml', flags=['OVERSIZE', 'BELTED', 'POWERARMOR_COMPATIBLE'])
    cigar = find('cigar_box_opened')
    cigar['container-item'] = 'box_medium'
    cigar['entries'] = [{'item': 'cigar', 'charges': [0, 25]}, {'item': 'paper', 'charges': 2, 'prob': 90},
                        {'item': 'scissors', 'prob': 50}]
    clothes = adapt_entry(find('nursing_home_clothes'))
    for branch in clothes['entries']:
        for child in branch.get('distribution', []):
            if 'variant' in child:
                assert (child['item'], child.pop('variant')) in (('dress_shirt', 'striped'), ('pants', 'pants_flag'))
    result = [staff_effects(), holder, feral_drop(find('feral_sapien_death_drops_spear')), refrigerator(), clothes]
    result += package_groups([cigar])
    original = find('mon_pigeon')
    result += [
        {'type': 'MONSTER', 'id': 'mon_pigeon', 'copy-from': 'mon_crow', 'name': original['name'],
         'description': original['description'], 'color': 'light_gray', 'petfood': original['petfood'],
         'reproduction': {'baby_egg': 'egg_pigeon', 'baby_count': 3, 'baby_timer': 32}},
        {'type': 'MONSTER', 'id': 'mon_pigeon_chick', 'copy-from': 'mon_crow_chick', 'name': {'str': 'pigeon squab'},
         'upgrades': {'age_grow': 10, 'into': 'mon_pigeon'}, 'petfood': find('mon_pigeon_chick')['petfood']},
        {'type': 'COMESTIBLE', 'id': 'egg_pigeon', 'copy-from': 'egg_chicken', 'name': find('egg_pigeon')['name'],
         'weight': '17 g', 'volume': '15 ml', 'calories': 24, 'spoils_in': '9 days', 'rot_spawn': 'GROUP_EGG_PIGEON'},
        {'type': 'monstergroup', 'name': 'GROUP_EGG_PIGEON', 'default': 'mon_pigeon_chick', 'freq_total': 1000,
         'is_animal': True, 'monsters': [{'monster': 'mon_pigeon_chick', 'freq': 1000, 'cost_multiplier': 1}]},
    ]
    return result


def dependency_refs(payload):
    refs = set()
    for entry in payload:
        if entry['type'] == 'item_group':
            refs.update(references({'items': {'_': {'item': entry}}}))
        elif entry['type'] == 'ARMOR':
            refs.add(('ITEM_CATEGORY', entry['category']))
            refs.update(('json_flag', flag) for flag in entry['flags'])
            refs.update(('material', material) for material in entry['material'])
            refs.update(('body_part', part) for part in entry['covers'])
        elif entry['type'] == 'MONSTER':
            refs.add(('MONSTER', entry['copy-from']))
            if 'upgrades' in entry:
                refs.add(('MONSTER', entry['upgrades']['into']))
            if 'reproduction' in entry:
                refs.add(('item', entry['reproduction']['baby_egg']))
        elif entry['type'] == 'COMESTIBLE':
            refs.add(('item', entry['copy-from']))
            refs.add(('monstergroup', entry['rot_spawn']))
        elif entry['type'] == 'monstergroup':
            refs.add(('MONSTER', entry['default']))
            refs.update(('MONSTER', child['monster']) for child in entry['monsters'])
    return refs


def prepare(check=False, bn_source=None):
    files = sources()
    if bn_source:
        for path, text in files.items():
            if path.startswith('bn/'):
                assert (bn_source / path[3:]).read_text(encoding='utf-8') == text, path
    payload = native_data()
    index = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    new = index_entries(payload) - BUILTIN_IDS
    assert not new & index, new & index
    for path in (ROOT / 'native').rglob('*.json'):
        if path.name == 'dda_eldercare_loot.json':
            continue
        other = json.loads(path.read_text())
        if isinstance(other, list):
            assert not new & (index_entries(other) - BUILTIN_IDS), path
    assert not dependency_refs(payload) - index - new, dependency_refs(payload) - index - new
    recipes = json.loads(files['bn/data/json/recipes/chem/mutagen.json'])
    for original, (target, recipe) in SAMPLES.items():
        assert any(e.get('result') == recipe and any(target == option[0] for alternatives in e.get('components', [])
                   for option in alternatives) for e in recipes), (original, target, recipe)
    report = {'pins': PINS, 'status': 'native_support_prepared_runtime_pending', 'definitions': len(payload),
              'sample_adaptations': [{'source': source, 'bn_item': item, 'bn_recipe': recipe} for source, (item, recipe) in SAMPLES.items()],
              'whole_locations_installed': False, 'scope': 'Loot, card-holder storage and pigeon lifecycle; no global DDA mutation, pocket, prescription or currency systems.'}
    for path, data in {ROOT / 'native/dda_eldercare_loot.json': payload, FOLDER / 'PORT_REPORT.json': report}.items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if check:
            assert path.read_text() == text, path
        else:
            path.write_text(text)
    print('PASS:', len(payload), 'eldercare loot/lifecycle definitions; all new identifiers and BN recipe ingredient mappings checked')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
