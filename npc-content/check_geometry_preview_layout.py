#!/usr/bin/env python3
"""Compare native fixture placements to every embedded special, before compiling."""
import collections
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def check():
    from check_geometry_runtime_rules import check as check_runtime_rules
    check_runtime_rules()
    entries=json.loads((ROOT/'native/dda_geometry_preview.json').read_text(encoding='utf-8'))
    code=(ROOT/'native/dda_geometry_preview_test.cpp').read_text(encoding='utf-8')
    specials=[e for e in entries if e['type']=='overmap_special']
    count=0
    for special in specials:
        name=special['id']+'_all_floors_without_loot'
        marker='TEST_CASE( "'+name+'"'
        assert code.count(marker)==1,name
        body=code.split(marker,1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(
            r'^        \{ (-?\d+), (-?\d+), (-?\d+), "([^"]+)"',body,re.M))
        expected=[]
        for cell in special['overmaps']:
            if 'overmap' in cell:terrain=cell['overmap']
            elif special['id']=='dda_geo_sunken_helicopter':terrain=cell['locations'][0]
            else:continue
            expected.append((*map(str,cell['point']),terrain))
        assert actual==collections.Counter(expected),(name,'fixture coordinates/terrain mismatch')
        point_count=len(re.findall(r'^        \{ -?\d+, -?\d+, -?\d+, -?\d+, -?\d+, "',body,re.M))
        assert point_count<8000,(name,'oversized native initializer risks Windows stack overflow',point_count)
        assert special['occurrences']==[0,0],name
        count+=len(expected)
    assert code.count('TEST_CASE(')==len(specials)+1
    assert code.count('TEST_CASE( "dda_city_geometry_transforms_preserve_adjacent_tiles"')==1
    # A structural furniture line must be tested as furniture, not just as a
    # non-null floor. This is also independent of the terrain-point generator.
    barrier='dda_geo_research_f_LIXA_unfold_barrier'
    body=code.split('TEST_CASE( "dda_geo_physics_lab_lixa_all_floors_without_loot"',1)[1]
    for x in range(6,22):
        assert f'{{ 1, 1, {x}, 9, -4, "{barrier}", true }}' in body,x
    from check_apartment_preview import validate_neighbors
    validate_neighbors(entries)
    apartment=json.loads((ROOT/'geometry_layer/APARTMENT_PREVIEW_REPORT.json').read_text(encoding='utf-8'))
    apartment_count=0
    for special,points in apartment['fixture_checks'].items():
        marker='TEST_CASE( "'+special+'_all_floors_without_loot"'
        body=code.split(marker,1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(
            r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^"]+)"',body,re.M))
        expected=collections.Counter((str(p['omt_x']),str(p['omt_y']),str(p['x']),str(p['y']),str(p['z']),p['terrain'])for p in points)
        assert actual==expected,(special,'apartment navigation/conditional stair fixture mismatch')
        apartment_count+=len(points)
    assert apartment_count==284
    from check_survivor_preview import validate_vertical
    validate_vertical(entries)
    survivor=json.loads((ROOT/'geometry_layer/SURVIVOR_PREVIEW_REPORT.json').read_text())
    survivor_count=0
    for special,points in survivor['fixture_checks'].items():
        marker='TEST_CASE( "'+special+'_all_floors_without_loot"'
        body=code.split(marker,1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(
            r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^"]+)"',body,re.M))
        expected=collections.Counter((str(p['omt_x']),str(p['omt_y']),str(p['x']),str(p['y']),str(p['z']),p['terrain'])for p in points)
        assert actual==expected,(special,'survivor access/LMOE stamp fixture mismatch')
        survivor_count+=len(points)
    assert survivor_count==127
    from check_survivor_camp_preview import validate as validate_camp
    camp=json.loads((ROOT/'geometry_layer/SURVIVOR_CAMP_PREVIEW_REPORT.json').read_text())
    camp_payload=json.loads((ROOT/'geometry_layer/SURVIVOR_CAMP_PREVIEW_SHELL.json').read_text())
    for entry in camp_payload:assert entry in entries,('Camp payload missing/modified',entry.get('id',entry.get('om_terrain')))
    validate_camp(camp_payload,camp)
    body=code.split('TEST_CASE( "dda_geo_camp_intact_all_floors_without_loot"',1)[1].split('\nTEST_CASE(',1)[0]
    actual=collections.Counter(re.findall(
        r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^"]+)"(, true)?',body,re.M))
    expected=collections.Counter(('0','0',str(p['x']),str(p['y']),str(p['z']),p.get('terrain',p.get('furniture')),', true' if 'furniture' in p else '')for p in camp['intact_expected_points'])
    assert actual==expected,'Camp native roof/furniture expectations changed'
    for name,mask in camp['loot_masks'].items():
        body=code.split('TEST_CASE( "'+name+'_all_floors_without_loot"',1)[1].split('\nTEST_CASE(',1)[0]
        assert f'{{ 0, 0, 0, "{name}_north", "{mask}" }}' in body,('Camp empty-loot mask changed',name)
    city=json.loads((ROOT/'geometry_layer/CITY_ADDITIONS_PREVIEW_REPORT.json').read_text())
    for special,points in city['fixture_checks'].items():
        body=code.split('TEST_CASE( "'+special+'_all_floors_without_loot"',1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^"]+)"',body,re.M))
        expected=collections.Counter((str(p['omt_x']),str(p['omt_y']),str(p['x']),str(p['y']),str(p['z']),p['terrain'])for p in points)
        assert actual==expected,(special,'City native geometry points changed')
    from check_civic_sites_geometry import validate_vertical as validate_civic_vertical
    civic=json.loads((ROOT/'geometry_layer/CIVIC_SITES_PREVIEW_REPORT.json').read_text())
    civic_payload=json.loads((ROOT/'geometry_layer/CIVIC_SITES_PREVIEW_SHELL.json').read_text())
    for entry in civic_payload:assert entry in entries,('Civic payload missing/modified',entry.get('id',entry.get('om_terrain')))
    validate_civic_vertical(civic['fixture_checks'])
    for special,points in civic['fixture_checks'].items():
        body=code.split('TEST_CASE( "'+special+'_all_floors_without_loot"',1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^\"]+)"',body,re.M))
        expected=collections.Counter((str(p['omt_x']),str(p['omt_y']),str(p['x']),str(p['y']),str(p['z']),p['terrain'])for p in points)
        assert actual==expected,(special,'Civic native geometry points changed')
    assert civic['fixture_point_count']==2404
    assert len(civic['automatic_roof_air_exclusions'])==41
    from check_institution_sites_geometry import validate_fixtures
    institution=json.loads((ROOT/'geometry_layer/INSTITUTION_SITES_PREVIEW_REPORT.json').read_text())
    validate_fixtures(institution)
    for special,points in institution['fixture_checks'].items():
        body=code.split('TEST_CASE( "'+special+'_all_floors_without_loot"',1)[1].split('\nTEST_CASE(',1)[0]
        actual=collections.Counter(re.findall(r'^        \{ (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), "([^"]+)"',body,re.M))
        expected=collections.Counter((str(p['omt_x']),str(p['omt_y']),str(p['x']),str(p['y']),str(p['z']),p['terrain'])for p in points)
        assert actual==expected,(special,'Institution native oriented access points changed')
    assert len(specials)==61 and count==2436
    from prepare_city_additions_preview import native_transform_test
    assert code.endswith(native_transform_test(city)),'Native city transform matrix/behavior checks changed'
    assert city['fixture_point_count']==242 and city['transform_input_count']==73
    print(f'PASS: {len(specials)} native layouts / {count} fixture cells; 1983 institution points /14 vertical links, 2404 civic points, 242 city geometry points and all 73 native transform inputs; existing LIXA/apartment/survivor/camp assertions retained')


if __name__=='__main__':check()
