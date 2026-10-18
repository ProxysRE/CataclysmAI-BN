#!/usr/bin/env python3
"""Guard infrastructure footprint, source generator odds, wall parameters and all lab prose."""
import copy
import json
from prepare_eldercare_assets import prepare, native_data, declarations, sources, adapt_map, wall_palette, ALIASES
from prepare_regional_locations import build
from bn_counterparts import adapt_entry

payload = native_data()
assert len(payload) == 33
by_id = {e['id']: e for e in payload if 'id' in e}
for name in ('dda_eldercare_bed_small', 'dda_eldercare_medical_cart', 'dda_eldercare_diesel_generator',
             'dda_eldercare_military_generator', 'dda_eldercare_gasoline_generator'):
    vehicle = by_id[name]
    assert len(vehicle['parts']) == 1 and vehicle['parts'][0]['x'] == vehicle['parts'][0]['y'] == 0
    assert len(vehicle['parts'][0]['parts']) == (7 if name.endswith('generator') else 3)
assert by_id['dda_eldercare_medical_cart']['parts'][0]['parts'] == ['xlframe_vertical_2', 'wheel_caster', 'veh_table']
for old_name, new_name in [('hospital_bed_small', 'dda_eldercare_bed_small'), ('medical_cart', 'dda_eldercare_medical_cart')]:
    assert {(p['x'], p['y']) for p in declarations()[old_name]['parts']} == {(p['x'], p['y']) for p in by_id[new_name]['parts']}
for name in ('common_mutation_books', 'rare_mutation_books'):
    assert by_id[name] == declarations()[name]
notes = {v['item'] for v in declarations()['lab_files_generic']['items']}
assert len(notes) == 9
for name in notes:
    original, adapted = declarations()[name], by_id[name]
    assert adapted['copy-from'] == 'survnote' and adapted['type'] == 'GENERIC'
    for field in ('name', 'snippet_category'):
        assert adapted[field] == original[field]
categories = {by_id[n]['snippet_category'] for n in notes}
original_snippets = [e for e in json.loads(sources()['dda/data/json/snippets/lab.json']) if e.get('category') in categories]
assert [e for e in payload if e['type'] == 'snippet'] == original_snippets
assert sum(len(e['text']) for e in original_snippets) == 60
van = by_id['dda_eldercare_cargo_van']
assert {(p['x'], p['y']) for p in van['parts']} == {(p['x'], p['y']) for p in declarations()['van_cargo']['parts']}
assert sum('cargo_space' in p['parts'] for p in van['parts']) == 6
source_wall = declarations()['parametrized_walls_palette']
for name, param in wall_palette()['parameters'].items():
    original = source_wall['parameters'][name]
    assert [weight for _, weight in param['default']['distribution']] == [weight for _, weight in original['default']['distribution']]
for site in ('nursing_home', 'retirement_community'):
    for original in build()[site + '.json']:
        converted = adapt_map(adapt_entry(original))
        if original['type'] != 'mapgen':
            continue
        old, new = original['object'], converted['object']
        assert old.get('rows') == new.get('rows')
        for glyph, value in old.get('furniture', {}).items():
            if isinstance(value, list) and value and isinstance(value[0], list) and value[0][0] == 'f_generator_broken':
                assert [p[1] for p in new['nested'][glyph]['chunks']] == [p[1] for p in value] == [25, 5, 5, 5]
        if 'parametrized_walls_palette' in old.get('palettes', []):
            assert new['parameters'] == wall_palette()['parameters']
            assert new['nested']['#'] == source_wall['nested']['#']
            assert not new['palettes']
prepare(check=True)
print('PASS: compact medical objects, real BN generator parts, exact weighted choices, 60 lab texts and source map rows')

for e in payload:
    if e.get('id', '').endswith('_generator'):
        assert 'box' in e['parts'][0]['parts'], 'Cable loot needs an actual cargo part'
