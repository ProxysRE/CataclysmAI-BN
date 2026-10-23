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
    assert code.count('TEST_CASE(')==len(specials)
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
    print(f'PASS: {len(specials)} native layouts / {count} fixture cells match embedded special coordinates; LIXA barrier has 16 furniture assertions; apartments have {apartment_count} navigation/conditional assertions')


if __name__=='__main__':check()
