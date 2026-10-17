#!/usr/bin/env python3
"""Guard location comparisons against renamed categories and mutable labels."""
from compare_location_catalog import compare, normalized, physical_refs, static_summary


def check():
    sample = {'overmaps': {'piece': {'overmap': 'actual_north'}},
              'phases': [{'overmap': 'piece'}]}
    assert list(physical_refs(sample)) == ['actual_north']
    assert normalized('literal_west', {'literal_west': True}) == 'literal_west'
    summary = static_summary({'overmaps': [
        {'point': [0, 0, -1], 'overmap': 'basement_north'},
        {'point': [1, 0, 0], 'locations': ['land']}]})
    assert summary == {'terrain_placements': 1, 'constraint_records': 1, 'z_levels': [-1]}
    report = compare()
    groups = {g['name']: g for g in report['reviewed_groups']}
    assert not any('nuclear power plant' in i for g in groups.values() for i in g['source_identities'])
    assert groups['Hub 01']['evidence'][0]['source_summary']['terrain_placements'] == 100
    assert groups['Hub 01']['evidence'][0]['source_summary']['constraint_records'] == 2
    assert groups['Лагерь FEMA']['analogue_summaries']['overmap_special:FEMA_camp']['terrain_placements'] == 9
    assert groups['Новые торговые и бытовые варианты']['status'] == 'needs_mapgen_rename_review'
    assert report['registration_counts'] == {'dda': 729, 'bn': 641}
    print('PASS: full core registration/terrain catalog, mutable template exclusion, typed identities, constraint counts and reviewed-gap gates')


if __name__ == '__main__':
    check()
