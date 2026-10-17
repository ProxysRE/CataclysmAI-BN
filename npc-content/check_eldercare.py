#!/usr/bin/env python3
"""Guard source stories, medical/civilian dependencies and closed native support."""
import json
from prepare_eldercare import prepare, sources, build_layer, native_data, declarations, ROOT
from prepare_regional_locations import build

files = sources()
layer = build_layer()
assert layer['installed'] is False
assert layer['report']['selected_definitions'] == 42
keys = {key for value in layer['source_candidates'] for key in declarations({value['source']: json.dumps([value['entry']])})}
for key in [('monstergroup', 'GROUP_NURSING_HOME'), ('monstergroup', 'GROUP_RETIREMENT_COMMUNITY'),
            ('monstergroup', 'GROUP_CIVILIANS_STANDARD'), ('monstergroup', 'GROUP_MEDICAL_UPGRADE'),
            ('MONSTER', 'mon_zombie_medical'), ('MONSTER', 'mon_pigeon')]:
    assert key in keys, key
maps = build()
story = json.loads(files['dda/data/json/npcs/computers/TALK_RET_COMM.json'])
assert all(e in maps['retirement_community.json'] for e in story)
assert len(story) == 15
topics = {e['id'] for e in story if e['type'] == 'talk_topic'}
from prepare_eldercare import refs
assert not {r for e in story for r in refs(e)} - {('talk_topic', t) for t in topics}
# The pinned nursing-home story really has a dangling legal-page link.
# Preserve/report it rather than inventing a replacement story page.
assert ('talk_topic', 'COMP_NURSING_HOME_LEGAL') in map(tuple, layer['report']['unresolved_transitive_references'])
pond, spider = native_data()
assert pond['name'] == 'GROUP_STOCKED_POND' and pond['default'] == 'mon_fish_rainbow_trout'
assert pond['freq_total'] == 345 and len(pond['monsters']) == 8
original = next(e for e in json.loads(files['dda/data/json/monstergroups/fish.json']) if e.get('id') == pond['name'])
for a, b in zip(original['monsters'], pond['monsters']):
    a = dict(a)
    a['freq'] = a.pop('weight')
    assert a == b
assert spider['object'] == next(e['object'] for e in json.loads(files['dda/data/json/mapgen/map_extras/spider.json']) if e.get('nested_mapgen_id') == 'spider_webs')
assert set(spider) == {'type', 'nested_mapgen_id', 'method', 'object'}
prepare(check=True)
print('PASS: complete retirement story; 42 source dependencies kept separate; exact pond weights and source web field; whole sites remain uninstalled')
