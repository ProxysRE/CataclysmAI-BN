#!/usr/bin/env python3
"""Port noncombatant source people and their pure dialogue graphs to BN."""
import argparse
import base64
import gzip
import difflib
import copy
import hashlib
import json
from pathlib import Path
from prepare_eldercare_fauna import find, sources as fauna_sources
from export_bn_ids import read_cache
from prepare_regional_locations import index_entries, BUILTIN_IDS

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'civilians'
PAYLOAD = 'data/mods/Civilians/civilians.json'
LEGACY_CORE = 'data/json/dda_civilians.json'
PEOPLE = ('mon_civilian_panic', 'mon_civilian_stationary', 'mon_civilian_parent', 'mon_civilian_police', 'mon_civilian_zombiefighter', 'mon_civilian_icu')
TOPICS = dict(zip(PEOPLE, ('TALK_CIVILIAN_PANIC', 'TALK_CIVILIAN_PANIC', 'TALK_CIVILIAN_PARENT', 'TALK_CIVILIAN_OFFICER', 'TALK_CIVILIAN_FIGHTER', 'TALK_CIVILIAN_ICU')))


def chat_source():
    entry = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())['npctalk']
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / n).read_text() for n in entry['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == entry['blob_sha']
    return raw.decode('utf-8')


def sources():
    chat_source()
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


def mod_sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    result = {}
    for name, digest in manifest['bn_mod_sources'].items():
        raw = (FOLDER / 'bn_mod' / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest, name
        result[name] = raw.decode('utf-8')
    return result


def mod_providers():
    result = []
    for name, text in mod_sources().items():
        if name.endswith('.json'):
            data = json.loads(text)
            result += [e for e in data if isinstance(e, dict)] if isinstance(data, list) else [data]
    return index_entries(result) - BUILTIN_IDS


def native_data():
    result = json.loads(mod_sources()['civilians.json'])
    seen = set()
    for entry in result:
        if entry.get('id') in TOPICS:
            entry['civilian_chat'] = dialogue(TOPICS[entry['id']])
            seen.add(entry['id'])
    assert seen == set(PEOPLE)
    return result


def patch_sections():
    before = mod_sources()['civilians.json']
    after = json.dumps(native_data(), ensure_ascii=True, indent=2) + '\n'
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), 'a/' + PAYLOAD, 'b/' + PAYLOAD))


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
    result['monstergenerator.cpp'] = cpp.replace(anchor, anchor + '\n    if( jo.has_object( "civilian_chat" ) ) {\n        civilian_dialogue.load( jo.get_object( "civilian_chat" ) );\n    } else {\n        civilian_dialogue = civilian_chat();\n    }')
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
        assert (bn_source / 'src/npctalk.cpp').read_text(encoding='utf-8') == chat_source()
        assert json.loads((bn_source / 'data/json/monster_factions.json').read_text(encoding='utf-8')) == json.loads((FOLDER / 'bn_monster_factions.json').read_text())
        for name, text in mod_sources().items():
            assert (bn_source / 'data/mods/Civilians' / name).read_text(encoding='utf-8') == text, name
    payload = native_data()
    original = json.loads(mod_sources()['civilians.json'])
    stripped = [{k: v for k, v in e.items() if k != 'civilian_chat'} for e in payload]
    assert stripped == original, 'Stock Civilians behavior was modified'
    path = ROOT / 'native/dda_civilians.json'
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)
    print('PASS: six dialogue additions to existing Civilians types; every original field and all spawn/evolution tables retained')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source)
