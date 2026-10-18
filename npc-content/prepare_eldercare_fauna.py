#!/usr/bin/env python3
"""Adapt armed ferals and unique laboratory mutants with existing BN actors."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
import re
from pathlib import Path
from export_bn_ids import read_cache
from bn_counterparts import adapt_entry
from prepare_regional_locations import references, index_entries, BUILTIN_IDS

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'eldercare_fauna'
PAYLOAD = 'data/json/dda_eldercare_fauna.json'
PINS = {'bn': 'c621aaf42fa182473aad10feea2b55647704dcf1', 'dda': 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
ALIASES = {'mon_large_cockroach': 'mon_giant_cockroach_nymph',
           'mon_spider_cellar_small': 'mon_spider_cellar_giant_s'}
MUTANTS = ('mon_mutant_antler', 'mon_mutant_arthropod', 'mon_mutant_camouflaged', 'mon_mutant_mollusk')
GROUPS = ('GROUP_FERAL', 'GROUP_MUTANT_EVOLVED', 'GROUP_NURSING_HOME_LAB')


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert m['pins'] == PINS
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / part).read_text() for part in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == m['files'][path]
    return files


def find(name, game='dda'):
    matches = [e for path, text in sources().items() if path.startswith(game + '/') and path.endswith('.json')
               for e in json.loads(text) if e.get('id') == name]
    assert len(matches) == 1, (game, name, len(matches))
    return copy.deepcopy(matches[0])


def adapt_references(entry):
    def walk(node, top=False):
        if isinstance(node, str):
            return ALIASES.get(node, node)
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, dict):
            return {k: v if k in ('name', 'description', 'text', 'dynamic_line') or k.startswith('//') or
                    (top and k in ('id', 'abstract')) else walk(v) for k, v in node.items()}
        return node
    return walk(entry, True)


def armor(source):
    return {'armor_' + {'heat': 'fire', 'electric': 'electric'}.get(kind, kind): value
            for kind, value in source.get('armor', {}).items()}


def source_melee(name):
    source = find(name)
    allowed = ('cooldown', 'move_cost', 'damage_max_instance', 'min_mul', 'max_mul',
               'hit_dmg_u', 'hit_dmg_npc', 'miss_msg_u', 'miss_msg_npc', 'no_dmg_msg_u', 'no_dmg_msg_npc')
    result = {k: source[k] for k in allowed if k in source}
    result.update(type='melee', id='dda_' + name)
    if name == 'mutant_stinger':
        # BN's adjacent melee actor and standard poison replace DDA's ranged
        # stinger/organic-target conditions and venom damage model.
        result['effects'] = [{'id': 'poison', 'duration': 250, 'chance': 100, 'affect_hit_bp': True}]
    return result


def mutant(name):
    original = find(name)
    inherited = find('mon_mutant_antler')
    merged = dict(inherited)
    merged.update(original)
    allowed = ('id', 'name', 'description', 'bodytype', 'color', 'volume', 'weight', 'hp', 'speed',
               'aggression', 'morale', 'melee_skill', 'melee_dice', 'melee_dice_sides', 'dodge',
               'vision_day', 'vision_night', 'melee_damage', 'attack_cost', 'grab_strength', 'bleed_rate', 'harvest', 'death_drops')
    result = {k: copy.deepcopy(merged[k]) for k in allowed if k in merged}
    result.update(type='MONSTER', **{'copy-from': 'mon_mutant_experimental'}, upgrades=False)
    result.update(armor(merged))
    result['melee_damage'] = copy.deepcopy(merged.get('melee_damage', []))
    flags = set(inherited['flags']) | set(original.get('extend', {}).get('flags', []))
    flags -= set(original.get('delete', {}).get('flags', []))
    flag_aliases = {'PATH_AVOID_DANGER': 'PATH_AVOID_DANGER_2', 'SMALLSLUDGETRAIL': 'SLUDGETRAIL'}
    omitted = {'HAS_MIND', 'EATS', 'PULP_PRYING'}
    flags = {flag_aliases.get(f, f) for f in flags - omitted}
    known = set(re.findall(r'case MF_\w+: return "([A-Z0-9_]+)";', sources()['bn/src/monstergenerator.cpp']))
    assert not flags - known, flags - known
    result['flags'] = sorted(flags)
    result['aggro_character'] = False
    result['regen_morale'] = True
    result['path_settings'] = {'max_dist': 50, 'avoid_traps': True, 'avoid_sharp': True}
    result['anger_triggers'] = ['PLAYER_CLOSE', 'FRIEND_ATTACKED']
    result['fear_triggers'] = [] if name == 'mon_mutant_mollusk' else ['HURT', 'FIRE']
    if name == 'mon_mutant_antler':
        result['special_attacks'] = [source_melee('mutant_antler'), ['SMASH', 12], ['EAT_CROP', 120]]
    elif name == 'mon_mutant_arthropod':
        result['special_attacks'] = [source_melee('mutant_stinger'), ['GRAB', 10],
                                    {'type': 'bite', 'cooldown': 10, 'move_cost': 105,
                                     'damage_max_instance': original['special_attacks'][3]['damage_max_instance']}]
        result['emit_fields'] = [{'emit_id': 'dda_eldercare_web', 'delay': '5 seconds'}]
    elif name == 'mon_mutant_camouflaged':
        result['special_attacks'] = [{'type': 'leap', 'cooldown': 5, 'move_cost': 0, 'min_range': 2, 'max_range': 8},
                                    {'type': 'bite', 'cooldown': 7, 'move_cost': 115,
                                     'damage_max_instance': original['special_attacks'][2]['damage_max_instance']}, ['EAT_FOOD', 120]]
    else:
        result['special_attacks'] = [['RANGED_PULL', 10], ['GRAB', 15], ['TENTACLE', 15], ['EAT_FOOD', 120]]
    return result


def native_data():
    result = []
    for source, item, group in [('mon_feral_cop', 'tonfa', 'dda_feral_cop_weapon'),
                                 ('mon_feral_sapien_spear', 'spear_knife', 'dda_feral_spear_weapon')]:
        original = find(source)
        result.append({'type': 'item_group', 'id': group, 'subtype': 'distribution', 'items': [[item, 100]]})
        keys = ('id', 'name', 'description', 'speed', 'color', 'aggression', 'melee_skill', 'dodge', 'vision_day', 'death_drops', 'zombify_into')
        mon = {k: copy.deepcopy(original[k]) for k in keys if k in original}
        mon.update(type='MONSTER', **{'copy-from': 'mon_feral_human_pipe'}, monster_weapon=group,
                   starting_ammo={'rock': 0}, special_attacks=[['PARROT_AT_DANGER', 5]])
        if source == 'mon_feral_cop':
            mon['death_drops'] = 'mon_zombie_cop_death_drops'
        if source == 'mon_feral_sapien_spear':
            mon['death_drops'] = 'dda_feral_spear_outfit'
        mon.update(armor(original))
        result.append(mon)
    from prepare_eldercare_loot import native_data as loot_data
    outfit = copy.deepcopy(next(e for e in loot_data() if e.get('id') == 'feral_sapien_death_drops_spear'))
    assert outfit['entries'][0]['group'] == 'survivor_stabbing'
    outfit['id'] = 'dda_feral_spear_outfit'
    outfit['entries'] = outfit['entries'][1:]
    result.append(outfit)
    result += [mutant(name) for name in MUTANTS]
    for name in GROUPS:
        original = find(name)
        assert all('monster' in e and 'group' not in e for e in original['monsters'])
        total = sum(e.get('weight', 1) for e in original['monsters'])
        default = original.get('default') or max(original['monsters'], key=lambda e: e.get('weight', 1))['monster']
        group = {'type': 'monstergroup', 'name': name, 'freq_total': total, 'default': default, 'monsters': []}
        for entry in original['monsters']:
            adapted = copy.deepcopy(entry)
            adapted['freq'] = adapted.pop('weight', 1)
            adapted.setdefault('cost_multiplier', 1)
            group['monsters'].append(adapted)
        result.append(group)
    result.append({'type': 'emit', 'id': 'dda_eldercare_web', 'field': 'fd_web', 'intensity': 1, 'qty': 1, 'chance': 100})
    return [adapt_entry(e) for e in result]


def dependency_refs(payload):
    refs = set()
    for entry in payload:
        if entry['type'] == 'item_group':
            refs.update(references({'items': {'_': {'item': entry}}}))
        elif entry['type'] == 'monstergroup':
            refs.update(('MONSTER', m['monster']) for m in entry['monsters'])
            refs.add(('MONSTER', entry['default']))
        elif entry['type'] == 'emit':
            refs.add(('field_type', entry['field']))
        elif entry['type'] == 'MONSTER':
            for key, kind in [('copy-from', 'MONSTER'), ('death_drops', 'item_group'), ('monster_weapon', 'item_group'),
                              ('harvest', 'harvest'), ('zombify_into', 'MONSTER')]:
                if key in entry:
                    refs.add((kind, entry[key]))
            for emitter in entry.get('emit_fields', []):
                refs.add(('emit', emitter['emit_id']))
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
    shared = set()
    for path in (ROOT / 'native').rglob('*.json'):
        if path.name == 'dda_eldercare_fauna.json':
            continue
        other = json.loads(path.read_text())
        if isinstance(other, list):
            other_ids = index_entries(other) - BUILTIN_IDS
            assert not new & other_ids, path
            shared |= other_ids
    assert not dependency_refs(payload) - index - new - shared, dependency_refs(payload) - index - new - shared
    known_attacks = set(re.findall(r'add_hardcoded_attack\( "([A-Z0-9_]+)"', files['bn/src/monstergenerator.cpp']))
    for entry in payload:
        for attack in entry.get('special_attacks', []):
            if isinstance(attack, list):
                assert attack[0] in known_attacks
    for target in ALIASES.values():
        assert ('MONSTER', target) in index
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    path = ROOT / 'native/dda_eldercare_fauna.json'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)
    print('PASS: six creatures, two weapon groups, three direct spawn groups; stock BN actors and identifier closure')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    a = parser.parse_args()
    prepare(a.check, a.bn_source)
