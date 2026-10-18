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

from bn_counterparts import check as check_counterparts, adapt_entry
check_counterparts()
adapted = build_layer(adapted=True)
assert adapted['report']['selected_definitions'] == 7
assert not adapted['report']['unresolved_transitive_references']
assert ('MONSTER', 'mon_zombie_medical') not in {k for v in adapted['source_candidates'] for k in declarations({v['source']: json.dumps([v['entry']])})}
for name in ('nursing_home', 'retirement_community'):
    for entry in maps[name + '.json']:
        converted = adapt_entry(entry)
        if entry['type'] == 'mapgen':
            assert entry['object'].get('rows') == converted['object'].get('rows')
        elif entry['type'] in ('talk_topic', 'effect_on_condition'):
            assert entry == converted
print('PASS: counterpart reuse reduces 42 source dependencies to 7; stories and map geometry unchanged')

# Preserve DDA random web strength through BN's existing integer-range type.
from prepare_mapgen_corpses import replacement
mapgen = replacement()
field = mapgen[mapgen.index('class jmapgen_field:'):mapgen.index('class jmapgen_npc:')]
assert 'jmapgen_int intensity;' in field
assert 'intensity(jsi, "intensity", 1, 1)' in field
assert 'chosen_id, intensity.get(), age' in field
assert spider['object']['place_fields'][0]['intensity'] == [1, 3]
print('PASS: source web intensity range uses BN jmapgen_int; scalar/default behavior retained')
