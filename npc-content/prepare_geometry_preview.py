#!/usr/bin/env python3
"""Build an opt-in, namespaced geometry preview without late-layer content."""
import argparse,copy,json
from prepare_geometry_layer import ROOT,OUT,prepare as prepare_shells
from prepare_regional_locations import index_entries,BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

MOD='dda_geometry_preview'
BASE='data/mods/DDA_Geometry_Preview/'
FILES={BASE+'modinfo.json':'native/dda_geometry_preview_modinfo.json',BASE+'shells.json':'native/dda_geometry_preview.json'}
TEST='dda_geometry_preview_test.cpp'
PACKAGES=('island_prison','xedra_church')


def payloads():
    shells=json.loads((OUT/'SHELLS.json').read_text())
    report=json.loads((OUT/'REPORT.json').read_text())
    result=[]
    for name in PACKAGES:
        p=report['packages'][name]
        assert not p['unresolved_typed_refs'] and not p['geometry_issues'],name
        entries=copy.deepcopy(shells[name])
        own=index_entries(entries)
        omt={n for t,n in own if t=='overmap_terrain'}
        def rename(v):
            if isinstance(v,list):return [rename(x) for x in v]
            assert isinstance(v,str),v
            if v in omt:return 'dda_geo_'+v
            for suffix in ('_north','_east','_south','_west'):
                if v.endswith(suffix) and v[:-len(suffix)] in omt:return 'dda_geo_'+v
            return v
        for e in entries:
            if e['type']=='overmap_terrain':e['id']=rename(e['id'])
            elif e['type']=='mapgen':e['om_terrain']=rename(e['om_terrain'])
            elif e['type']=='overmap_special':
                e['id']='dda_geo_'+e['id'].replace(' ','_').lower()
                e['occurrences']=[0,0] # Debug placement only; never populate normal worlds with empty shells.
                for c in e['overmaps']:c['overmap']=rename(c['overmap'])
            else:raise AssertionError(e['type'])
        result+=entries
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id']) for r in mod_cache()['records']}
    own=index_entries(result)
    assert not (own-BUILTIN_IDS)&(core|mods),sorted((own-BUILTIN_IDS)&(core|mods))
    assert not required(result)-core-own,sorted(required(result)-core-own)
    return {FILES[BASE+'modinfo.json']:[{'type':'MOD_INFO','id':MOD,'name':'DDA geometry preview (unfinished)','authors':['ProxysRE'],'description':'Terrain-only previews of the island prison and XEDRA church. No loot, inhabitants or quests. Debug placement only; enable explicitly in a test world.','category':'buildings','dependencies':['bn']}],FILES[BASE+'shells.json']:result}


def native_test():
    # Reuse the already compiled all-floor map fixture, retaining only its helper.
    from prepare_eldercare_sites import native_test as reference
    text=reference().split('\nTEST_CASE(',1)[0]
    text=text.replace('CHECK( generated.ter( tripoint_bub_ms( 12, 12, cell.z ) ) != ter_id( "t_null" ) );', '''CHECK( generated.ter( tripoint_bub_ms( 12, 12, cell.z ) ) != ter_id( "t_null" ) );
            if( std::string( cell.terrain ).find( "dda_geo_" ) == 0 ) {
                for( int x = 0; x < 24; ++x ) {
                    for( int y = 0; y < 24; ++y ) {
                        const tripoint_bub_ms p( x, y, cell.z );
                        CHECK( generated.ter( p ) != ter_id( "t_null" ) );
                        CHECK( generated.i_at( p ).empty() );
                    }
                }
            }''')
    entries=payloads()['native/dda_geometry_preview.json']
    for i,special in enumerate(e for e in entries if e['type']=='overmap_special'):
        text+='\nTEST_CASE( "'+special['id']+'_all_floors_without_loot", "[dda_geometry]" )\n{\n    generate_site( '+str(4200+i*100)+', {\n'
        for c in special['overmaps']:
            x,y,z=c['point'];text+=f'        {{ {x}, {y}, {z}, {json.dumps(c["overmap"])} }},\n'
        text+='    } );\n}\n'
    return text


def prepare(check=False):
    prepare_shells(check=True)
    texts={p:json.dumps(v,indent=2,ensure_ascii=True)+'\n' for p,v in payloads().items()}
    texts['native/'+TEST]=native_test()
    for p,text in texts.items():
        path=ROOT/p
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('Geometry preview: two isolated packages, no ID collisions; natural occurrences disabled; native validation pending')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');prepare(parser.parse_args().check)
