#!/usr/bin/env python3
"""Port noncombatant source people and their pure dialogue graphs to BN."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from prepare_eldercare_fauna import find, sources as fauna_sources
from export_bn_ids import read_cache
from prepare_regional_locations import index_entries, BUILTIN_IDS

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'civilians'
PAYLOAD = 'data/json/dda_civilians.json'
PEOPLE = ('mon_civilian_panic', 'mon_civilian_stationary', 'mon_civilian_parent')


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['dda_pin'] == 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert manifest['bn_pin'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((FOLDER / name).read_bytes()).hexdigest() == digest
    return json.loads((FOLDER / 'civilian_topics.json').read_text())


def dialogue(root):
    topics = {e['id']: e for e in sources()}
    pending, pages = [root], {}
    while pending:
        name = pending.pop()
        if name in ('TALK_DONE', 'TALK_NONE') or name in pages:
            continue
        source = topics[name]
        assert set(source) <= {'type', 'id', 'dynamic_line', 'responses', 'portrait_override'}
        lines = source['dynamic_line']
        lines = [lines] if isinstance(lines, str) else lines
        assert all(isinstance(line, str) for line in lines)
        assert all(set(r) == {'text', 'topic'} for r in source['responses'])
        pages[name] = {'id': name, 'lines': lines, 'responses': [{'text': r['text'], 'target': r['topic']} for r in source['responses']]}
        pending += [r['topic'] for r in source['responses']]
    return {'root': root, 'pages': [pages[k] for k in sorted(pages)]}


def upgrade_group():
    # This group is consumed ONLY by single-monster evolution. Both engines'
    # GetRandomMonsterFromGroup ignore packs, cost and time windows here.
    source = find('GROUP_CIVILIANS_UPGRADE')
    ferals = find('GROUP_FERAL')
    total = sum(e.get('weight', 1) for e in ferals['monsters'])
    entries = []
    for entry in source['monsters']:
        if 'monster' in entry:
            entries.append({'monster': entry['monster'], 'freq': entry['weight'] * total, 'cost_multiplier': 0})
        else:
            assert entry['group'] == 'GROUP_FERAL'
            for child in ferals['monsters']:
                entries.append({'monster': child['monster'], 'freq': entry['weight'] * child['weight'], 'cost_multiplier': 0})
    return {'type': 'monstergroup', 'name': source['id'], 'default': 'mon_zombie_fat',
            'freq_total': sum(e['freq'] for e in entries), 'monsters': entries}


def native_data():
    original = find('mon_civilian_panic')
    keys = ('id', 'type', 'name', 'description', 'default_faction', 'bodytype', 'species', 'material', 'volume', 'weight', 'hp', 'speed', 'symbol', 'color', 'aggression', 'morale', 'vision_day', 'melee_dice', 'melee_dice_sides', 'melee_damage', 'harvest', 'path_settings', 'upgrades', 'dodge', 'death_drops', 'zombify_into')
    root = {key: copy.deepcopy(original[key]) for key in keys if key in original}
    root['flags'] = ['SEES', 'HEARS', 'WARM', 'HUMAN', 'CAN_OPEN_DOORS', 'PATH_AVOID_DANGER_2', 'GUILT']
    root['aggro_character'] = False
    root['death_function'] = ['NORMAL']
    root['special_attacks'] = []
    root['civilian_chat'] = dialogue(original['chat_topics'][0])
    result = [root]
    for name in PEOPLE[1:]:
        source = find(name)
        mon = {key: copy.deepcopy(source[key]) for key in ('id', 'type', 'copy-from', 'name', 'description', 'speed', 'path_settings') if key in source}
        if 'chat_topics' in source:
            mon['civilian_chat'] = dialogue(source['chat_topics'][0])
        result.append(mon)
    result.append(upgrade_group())
    return result


def extend_creature_core(result):
    result = dict(result)
    h = result['mtype.h']
    assert '#include "calendar.h"' in h
    h = h.replace('#include "calendar.h"', '#include "calendar.h"\n#include "civilian_chat.h"', 1)
    anchor = '        int grab_strength = 1;    /**intensity of the effect_grabbed applied*/'
    assert h.count(anchor) == 1
    result['mtype.h'] = h.replace(anchor, anchor + '\n        civilian_chat civilian_dialogue;')
    cpp = result['monstergenerator.cpp']
    anchor = '    optional( jo, was_loaded, "aggro_character", aggro_character, true );'
    assert cpp.count(anchor) == 1
    result['monstergenerator.cpp'] = cpp.replace(anchor, anchor + '\n    if( jo.has_object( "civilian_chat" ) ) {\n        civilian_dialogue.load( jo.get_object( "civilian_chat" ) );\n    }')
    return result


def extend_chat(text):
    if '#include "civilian_chat_ui.h"' in text:
        return text
    text = text.replace('#include "npctalk.h"', '#include "npctalk.h"\n#include "civilian_chat_ui.h"', 1)
    text = text.replace('    NPC_CHAT_COMMAND_MAGIC_VEHICLE_STOP_FOLLOW\n', '    NPC_CHAT_COMMAND_MAGIC_VEHICLE_STOP_FOLLOW,\n    NPC_CHAT_CIVILIAN\n', 1)
    anchor = '    const int available_count = available.size();'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''
    std::vector<monster *> civilians;
    for( monster &person : all_monsters() ) {
        if( can_chat_with_civilian( person, u ) ) {
            civilians.push_back( &person );
        }
    }''')
    anchor = '    nmenu.addentry( NPC_CHAT_YELL, true, \'a\','
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''    if( !civilians.empty() ) {
        nmenu.addentry( NPC_CHAT_CIVILIAN, true, 'p', _( "Talk to a nearby person" ) );
    }
''' + anchor)
    anchor = '        case NPC_CHAT_TALK: {'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''        case NPC_CHAT_CIVILIAN: {
            is_yell = false;
            is_order = false;
            uilist people;
            people.title = _( "Talk to whom?" );
            for( size_t i = 0; i < civilians.size(); ++i ) {
                people.addentry( static_cast<int>( i ), true, -1, civilians[i]->get_name() );
            }
            people.query();
            if( people.ret < 0 || static_cast<size_t>( people.ret ) >= civilians.size() ) {
                return;
            }
            show_civilian_chat( *civilians[people.ret] );
            break;
        }
''' + anchor)
    return text


def prepare(check=False, bn_source=None):
    sources()
    if bn_source:
        assert json.loads((bn_source / 'data/json/monster_factions.json').read_text(encoding='utf-8')) == json.loads((FOLDER / 'bn_monster_factions.json').read_text())
    payload = native_data()
    bn = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    new = index_entries(payload) - BUILTIN_IDS
    assert not bn & new
    from prepare_eldercare_fauna import dependency_refs, native_data as fauna_data
    shared = index_entries(fauna_data())
    refs = dependency_refs(payload)
    refs.add(('monstergroup', 'GROUP_CIVILIANS_UPGRADE'))
    assert not refs - bn - new - shared, refs - bn - new - shared
    path = ROOT / 'native/dda_civilians.json'
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)
    print('PASS: three noncombatant humans, pure dialogue graphs, exact single-monster evolution distribution')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source)
