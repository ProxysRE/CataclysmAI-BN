#!/usr/bin/env python3
"""Guard exact source dialogue and single-monster evolution probabilities."""
from collections import defaultdict
from fractions import Fraction
from prepare_civilians import native_data, dialogue, sources, prepare, PEOPLE, upgrade_group, extend_chat, chat_source, ROOT
from prepare_eldercare_fauna import find

payload = native_data()
assert len(payload) == 4
monsters = {e['id']: e for e in payload if e['type'] == 'MONSTER'}
root = monsters['mon_civilian_panic']
assert root['aggro_character'] is False
assert root['default_faction'] == 'human'
assert root['upgrades'] == find('mon_civilian_panic')['upgrades']
assert root['zombify_into'] == 'mon_zombie'
assert root['flags'][-1] == 'GUILT'
assert root['special_attacks'] == []
assert monsters['mon_civilian_stationary']['speed'] == 20
assert monsters['mon_civilian_parent']['civilian_chat']['root'] == 'TALK_CIVILIAN_PARENT'
for name in PEOPLE:
    assert monsters[name]['name'] == find(name)['name']
for topic in sources():
    graph = dialogue(topic['id'])
    pages = {p['id']: p for p in graph['pages']}
    assert topic['id'] in pages
    for page in pages.values():
        source = next(e for e in sources() if e['id'] == page['id'])
        assert page['lines'] == ([source['dynamic_line']] if isinstance(source['dynamic_line'], str) else source['dynamic_line'])
        assert page['responses'] == [{'text': r['text'], 'target': r['topic']} for r in source['responses']]
expected = defaultdict(Fraction)
source, children = find('GROUP_CIVILIANS_UPGRADE'), find('GROUP_FERAL')
total = sum(e['weight'] for e in source['monsters'])
child_total = sum(e['weight'] for e in children['monsters'])
for row in source['monsters']:
    if 'monster' in row:
        expected[row['monster']] += Fraction(row['weight'], total)
    else:
        for child in children['monsters']:
            expected[child['monster']] += Fraction(row['weight'] * child['weight'], total * child_total)
group = upgrade_group()
actual = defaultdict(Fraction)
for row in group['monsters']:
    actual[row['monster']] += Fraction(row['freq'], group['freq_total'])
assert actual == expected
assert group['freq_total'] == 90600
chat = extend_chat(chat_source())
assert extend_chat(chat) == chat
assert 'can_chat_with_civilian( person, u )' in chat
assert 'show_civilian_chat( *civilians[people.ret] );' in chat
prepare(check=True)
print('PASS: exact read-only source graphs, neutral noncombatants, source evolution fractions and idempotent menu integration')

from prepare_eldercare_fauna import sources as fauna_sources
loader = fauna_sources()['bn/src/monstergenerator.cpp']
for mon in monsters.values():
    assert not {k for k in mon if k not in ('type', 'id', 'copy-from', 'civilian_chat') and ('"' + k + '"') not in loader}
