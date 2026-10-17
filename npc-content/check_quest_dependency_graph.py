#!/usr/bin/env python3
"""Verify namespace separation, parent traversal and explicit unresolved edges."""
from quest_dependency_graph import build

fixture = {'items.json': [
    {'type': 'ITEM', 'id': '545_ap', 'copy-from': '545', 'ascii_picture': '545_ap',
     'pocket_data': [{'pocket_type': 'MAGAZINE_WELL', 'item_restriction': ['test_mag']}],
     'name': 'not_a_dependency', 'description': 'also_not_a_dependency'},
    {'type': 'ITEM', 'id': '545', 'subtypes': ['AMMO'], 'ammo_type': ['545x39']},
    {'type': 'ITEM', 'id': 'test_mag', 'pocket_data': [{'pocket_type': 'MAGAZINE', 'ammo_restriction': {'545x39': 60}}]},
    {'type': 'ascii_art', 'id': '545_ap', 'picture': ['not_a_dependency']},
]}
result = build(fixture, roots=['545_ap'], bn_candidates=['545x39'])
assert {(node['namespace'], node['id']) for node in result['nodes']} == {
    ('item', '545_ap'), ('item', '545'), ('item', 'test_mag'), ('ascii_art', '545_ap')}
assert result['obligations'] == [{'namespace': 'ammunition_type', 'id': '545x39', 'status': 'resolve_against_pinned_BN'}]
assert result == build(fixture, roots=['545_ap'], bn_candidates=['545x39'])
ambiguous = {'bad.json': [{'type':'ITEM','id':'same'}, {'type':'GUN','id':'same'}]}
try:
    build(ambiguous, roots=['same'])
except ValueError:
    pass
else:
    raise AssertionError('Ambiguous definitions must fail rather than selecting silently')
print('PASS: typed collisions, inheritance, magazine/ammo references, display-text exclusion, deterministic output and explicit missing definitions')

weapon = {'weapon.json': [
    {'type': 'GUN', 'id': 'weapon', 'casing': 'case', 'linkage': 'NULL',
     'weapon_category': ['RIFLES'], 'faults': [{'fault': 'jam'}], 'default_mods': ['mod'],
     'magazine_adaptor': [['test_caliber', ['mag']]]},
    {'type': 'GENERIC', 'id': 'case'},
    {'type': 'GUNMOD', 'id': 'mod', 'mod_targets': ['weapon']},
    {'type': 'MAGAZINE', 'id': 'mag', 'ammo_type': 'test_caliber'},
    {'type': 'ammunition_type', 'id': 'test_caliber'},
    {'type': 'fault', 'id': 'jam'},
    {'type': 'weapon_category', 'id': 'RIFLES'},
]}
graph = build(weapon, roots=['weapon'])
assert not graph['obligations']
edges = {(tuple(e['from']), tuple(e['to']), e['field']) for e in graph['edges']}
assert (('item', 'weapon'), ('item', 'case'), 'casing') in edges
assert (('item', 'weapon'), ('fault', 'jam'), 'faults[0].fault') in edges
assert (('item', 'weapon'), ('weapon_category', 'RIFLES'), 'weapon_category') in edges
assert (('item', 'mod'), ('item', 'weapon'), 'mod_targets') in edges
assert (('item', 'weapon'), ('item', 'mag'), 'magazine_adaptor.items') in edges
assert not any(n['id'] == 'NULL' for n in graph['nodes'])
missing_fault = {'weapon.json': [e for e in weapon['weapon.json'] if e['type'] != 'fault']}
assert build(missing_fault, roots=['weapon'])['obligations'] == [
    {'namespace': 'fault', 'id': 'jam', 'status': 'source_definition_not_in_candidate_archive'}]
print('PASS: casing, fault, weapon category, module target and magazine adaptor edges; missing faults stay explicit')
