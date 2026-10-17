#!/usr/bin/env python3
"""Check all church floors, source geometry, bell object and retained XEDRA obligations."""
import copy
import json
from prepare_rural_churches import prepare_data, prepare, sources, MAPS, SPECIALS
from compare_location_catalog import read_sources
from stage_xedra_church import stage

catalog, _ = read_sources()
payload = prepare_data()
maps = [e for e in payload if e['type'] == 'mapgen']
original = json.loads(catalog['dda/' + MAPS + 'church_rural.json'])
assert len(maps) == 4
for old, new in zip(original, maps):
    assert old['om_terrain'] == new['om_terrain']
    assert old['object']['rows'] == new['object']['rows']
    for field in set(old['object']) - {'palettes', 'terrain'}:
        assert old['object'][field] == new['object'][field]
    before, after = old['object'].get('terrain', {}), new['object'].get('terrain', {})
    expected = copy.deepcopy(before)
    for key, value in list(expected.items()):
        if value == 't_wood_wall_w': expected[key] = 't_wall_w'
        elif value == 't_soil': expected[key] = 't_dirt'
        elif isinstance(value, dict):
            assert value == {'param': 'linoleum_color', 'fallback': 't_linoleum_gray'}
            expected[key] = 't_linoleum_gray'
    assert after == expected
special = next(e for e in payload if e['type'] == 'overmap_special')
assert special == next(e for e in json.loads(catalog['dda/' + SPECIALS]) if e.get('id') == 'church_rural')
assert sorted({p['point'][2] for p in special['overmaps']}) == [-1, 0, 1, 2]
assert maps[1]['object']['computers']['0']['options'][0]['action'] == 'toll'
assert maps[1]['object']['rows'][6][4] == '0'
assert maps[0]['object']['rows'][7][25] == '<'
assert maps[1]['object']['rows'][7][1] == '>'
assert maps[0]['object']['rows'][21][31] == '>'
assert maps[3]['object']['rows'][21][7] == '<'
# Existing global palettes must never be replaced by this addition.
assert [e['id'] for e in payload if e['type'] == 'palette'] == ['dda_rural_church_palette']
prepare(check=True)
xedra = stage()
assert xedra['source_mapgen_blocks'] == 4
assert xedra['source_monster']['special_attacks'][0]['id'] == 'ranged_pull'
assert xedra['source_emit']['field'] == 'fd_twisting_mass_dust'
selected = {e['id'] for e in xedra['equipment_definitions']}
assert {'xedra_artifact_cleansuit', 'xedra_artifact_cleansuit_on', 'xedra_enviro_suit', 'xedra_enviro_suit_casual', 'inert_glowing_string'} <= selected
assert any(e['to'] == 'xedra_artifact_cleansuit_on' and e['field'] == 'use_action.transform.target' for e in xedra['equipment_reference_edges'])
assert not any('xedra_' in str(e.get('id', e.get('om_terrain', ''))) for e in payload)
print('PASS: complete rural church, four unchanged source layouts, matched stairs, bell terminal and preserved XEDRA dependency graph')
