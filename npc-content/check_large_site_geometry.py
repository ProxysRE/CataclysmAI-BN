#!/usr/bin/env python3
"""Check source scope, nested layout conservation and explicit integration gates."""
import collections,json,re
from prepare_large_site_geometry import prepare as stage,OUT,TARGETS
from adapt_large_site_geometry import prepare as adapt
from compare_location_catalog import read_sources
from check_geometry_terrain_schema import validate,validate_omt


def check():
    stage(check=True);adapt(check=True)
    raw=json.loads((OUT/'LARGE_SITES_SHELLS.json').read_text(encoding='utf-8'))
    adapted=json.loads((OUT/'LARGE_SITES_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    report=json.loads((OUT/'LARGE_SITES_GEOMETRY_REPORT.json').read_text(encoding='utf-8'))
    ar=json.loads((OUT/'LARGE_SITES_ADAPTATION_REPORT.json').read_text(encoding='utf-8'))
    catalog,_=read_sources()
    original={e['id']:e for p,text in catalog.items()if p.startswith('dda/')for e in json.loads(text)
              if e.get('type')in ('overmap_special','city_building')and e.get('id')in TARGETS}
    for e in raw:
        if e['type']=='overmap_special':
            assert [(c['point'],c.get('overmap'))for c in e['overmaps']]==[(c['point'],c.get('overmap'))for c in original[e['id']]['overmaps']]
            assert e['occurrences']==[0,0]
        elif e['type']=='mapgen':
            assert not {'items','item','place_items','place_loot','place_monsters','monsters','place_npcs','npcs','vehicles','place_vehicles','computers'}&e['object'].keys()
    assert report['special_cells']=={'stadium_football':145,'office_skyscraper':44,'oil_platform':204}
    assert report['world_maps']==32 and report['unique_omt']==307
    assert report['nested_mapgen_definitions']==291 and report['nested_identities']==189
    # Every weighted mapgen alternative must survive the physical adaptation.
    def layouts(es):
        return collections.Counter((json.dumps(e.get('om_terrain',e.get('nested_mapgen_id'))),json.dumps(e['object'].get('rows')),e.get('weight',1000))for e in es if e['type']=='mapgen')
    assert layouts(raw)==layouts(adapted)
    assert not ar['unresolved_typed_refs']
    issues=report['geometry_issues'];assert len(issues)==2
    assert {e['source']for e in issues}=={'roof_6x6_greenhouse_1','roof_6x6_greenhouse_2'}
    assert all(e['placement']['z']==1 for e in issues)
    assert ar['geometry_issues']==issues
    # Never "fix" the unsupported upward nest by moving the roof onto the wall.
    for e in adapted:
        if e.get('nested_mapgen_id')in ('dda_geo_large_roof_6x6_greenhouse_1','dda_geo_large_roof_6x6_greenhouse_2'):
            assert e['object']['place_nested'][0]['z']==1
    block=(OUT/'waterside_adaptation_sources/bn/src/overmap/overmap.h').read_text(encoding='utf-8').split('oter_flags_map = {',1)[1].split('};',1)[0]
    flags=set(re.findall(r'\{"([A-Z_]+)", oter_flags::',block))
    for e in adapted:
        if e['type']=='terrain':validate(e)
        elif e['type']=='overmap_terrain':validate_omt(e,flags)
    water=next(e for e in adapted if e.get('id')=='dda_geo_large_saltwater_cube')
    assert 'SALT_WATER'in water['flags']and water['examine_action']=='water_source'
    assert 'liquid_source'not in water
    assert any('ocean placement'in s for s in ar['remaining'])
    print('PASS: 393 source placements, 307 own OMT, 291 nested alternatives; typed references closed; greenhouse z and ocean-placement gates remain explicit')


if __name__=='__main__':check()
