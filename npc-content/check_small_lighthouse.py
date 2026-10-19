#!/usr/bin/env python3
"""Check whole-site provenance, geometry, lake placement and explicit BN reuse."""
import unicodedata
from prepare_small_lighthouse import ROOT, native_data, prepare, evidence
from prepare_regional_locations import build

source=build()['small_lighthouse.json']
payload=native_data()
old=[e for e in source if e['type']=='mapgen']
new=[e for e in payload if e['type']=='mapgen']
assert len(old)==len(new)==6
for before,after in zip(old,new):
    assert before['om_terrain']==after['om_terrain']
    for key in ('rows','place_vehicles'):
        assert before['object'].get(key)==after['object'].get(key),key
    if any('v' in row for row in after['object']['rows']):
        assert after['object']['terrain']['v']=='t_ladder_down'
    assert 'G' not in after['object']['furniture']
    assert after['object']['nested']['G']['chunks']==[
        ['dda_eldercare_generator_broken',25],['dda_eldercare_generator_diesel',5],
        ['dda_eldercare_generator_military',5],['dda_eldercare_generator_gasoline',5]]
a=next(e for e in source if e['type']=='overmap_special')
b=next(e for e in payload if e['type']=='overmap_special')
assert [c['point'] for c in a['overmaps']]==[c['point'] for c in b['overmaps']]
for key in ('locations','occurrences','city_distance','city_sizes','flags'):
    assert a.get(key)==b.get(key),key
assert not any('copy-from' in e for e in payload if e['type']=='overmap_terrain')
assert {e['id'] for e in payload if e['type']=='item_group'}=={'lighthouse_rainwater','lighthouse_fuel','lighthouse_food','lighthouse_food_contents'}
assert next(e for e in payload if e.get('id')=='lighthouse_fuel')['items'][0]['charges']==[0,50000]
assert not any('container-item' in e for e in payload if e['type']=='item_group')
fixture=(ROOT/'native/dda_small_lighthouse_test.cpp').read_text()
assert 't_ladder_up_down' in fixture and 'f_grid_floodlight_off' in fixture
assert 'volume <= package->type->container->contains' in fixture
prepare(check=True)
print('PASS: six complete lighthouse maps, source lake special/boat geometry, full ladder chain, generator and container checks; native results pending')

roof=evidence()['bn/data/json/mapgen_palettes/roof_palette.json'][0]
for e in new:
    obj=e['object']
    bound={key for value in obj.values() if isinstance(value,dict) for key in value}
    if 'roof_palette' in obj.get('palettes',[]):
        bound |= {key for value in roof.values() if isinstance(value,dict) for key in value}
    glyphs=[]
    for row in obj['rows']:
        for char in row:
            if unicodedata.combining(char):glyphs[-1]+=char
            else:glyphs.append(char)
    assert not set(glyphs)-bound-{' '}, (e['om_terrain'],set(glyphs)-bound-{' '})

food=next(e for e in payload if e.get('id')=='lighthouse_food')
assert food['entries']==[{'item':'box_huge','contents-group':'lighthouse_food_contents'}]

original_food=next(e for e in source if e.get('id')=='lighthouse_food')
contents=next(e for e in payload if e.get('id')=='lighthouse_food_contents')
assert contents['subtype']==original_food['subtype']=='collection'
assert contents['entries'][:2]==original_food['entries'][:2]
assert {k:v for k,v in contents['entries'][2].items() if k!='item'}=={k:v for k,v in original_food['entries'][2].items() if k!='item'}
assert contents['entries'][2]['item']=='roasted_coffee_bean'
