#!/usr/bin/env python3
"""Require field-preserving integration with the bundled BN Civilians mod."""
import json
from prepare_civilians import native_data, dialogue, sources, prepare, PEOPLE, TOPICS, mod_sources, mod_providers, extend_chat, chat_source, PAYLOAD, LEGACY_CORE

original = json.loads(mod_sources()['civilians.json'])
payload = native_data()
assert len(payload) == len(original)
assert [{k: v for k, v in e.items() if k != 'civilian_chat'} for e in payload] == original
monsters = {e['id']: e for e in payload if e['type'] == 'MONSTER'}
assert sum('civilian_chat' in e for e in payload) == 6
assert monsters['mon_civilian_stationary']['speed'] == 0
assert monsters['mon_civilian_panic']['upgrades'] == {'half_life': 1, 'into_group': 'GROUP_CIVILIANS_UPGRADE'}
assert monsters['mon_civilian_panic']['default_faction'] == 'civilians'
for name in PEOPLE:
    assert monsters[name]['civilian_chat'] == dialogue(TOPICS[name])
for topic in sources():
    graph = dialogue(topic['id'])
    for page in graph['pages']:
        source = next(e for e in sources() if e['id'] == page['id'])
        assert page['lines'] == ([source['dynamic_line']] if isinstance(source['dynamic_line'], str) else source['dynamic_line'])
        assert page['responses'] == [{'text': r['text'], 'target': r['topic']} for r in source['responses']]
# Groups and Lua are archived for provenance, not regenerated or installed as overrides.
groups = json.loads(mod_sources()['monstergroup.json'])
assert any(e['name'] == 'GROUP_CIVILIANS_UPGRADE' for e in groups)
assert ('monstergroup', 'GROUP_CIVILIANS_UPGRADE') in mod_providers()
assert PAYLOAD == 'data/mods/Civilians/civilians.json'
assert LEGACY_CORE == 'data/json/dda_civilians.json'
chat = extend_chat(chat_source())
assert extend_chat(chat) == chat
assert 'can_chat_with_civilian( person, u )' in chat
assert 'show_civilian_chat( *civilians[people.ret] );' in chat
prepare(check=True)
print('PASS: no duplicated core civilians/evolution group; six exact source dialogue graphs; stock mod definitions, groups and Lua retained')

# Temporary unregistered monsters must not move through the world tracker.
from prepare_civilians import ROOT
fixture=(ROOT / "native/dda_civilians_test.cpp").read_text()
assert "person.setpos(" not in fixture
assert "monster distant_person( type, tripoint_bub_ms( 68, 60, 0 ) );" in fixture
