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
