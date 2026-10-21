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
PACKAGES=('island_prison','xedra_church','hub_01','campus','godco_base','exodii','frontier')


def payloads():
    shells=json.loads((OUT/'SHELLS.json').read_text())
    report=json.loads((OUT/'REPORT.json').read_text())
    result=[]
    for name in PACKAGES:
        if name in ('exodii','frontier'):
            stem=name.upper()
            adapted=json.loads((OUT/(stem+'_ADAPTATION_REPORT.json')).read_text())
            assert not adapted['unresolved_typed_refs']
            entries=json.loads((OUT/(stem+'_ADAPTED_SHELL.json')).read_text())
        else:
            p=report['packages'][name]
            assert not p['geometry_issues'],name
        if name in ('exodii','frontier'):pass
        elif name=='godco_base':
            adapted=json.loads((OUT/'GODCO_GEOMETRY_REPORT.json').read_text())
            assert not adapted['unresolved_typed_refs']
            entries=json.loads((OUT/'GODCO_ADAPTED_BASE.json').read_text())
        elif name in ('hub_01','campus'):
            stem='HUB' if name=='hub_01' else 'CAMPUS'
            adapted=json.loads((OUT/(stem+'_ADAPTATION_REPORT.json')).read_text())
            assert not adapted['unresolved_typed_refs']
            entries=json.loads((OUT/(stem+'_ADAPTED_SHELL.json')).read_text())
        else:
            assert not p['unresolved_typed_refs'],name
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
            if e['type']=='overmap_terrain':
                e['id']=rename(e['id'])
                if e.get('copy-from') in omt:e['copy-from']=rename(e['copy-from'])
            elif e['type']=='mapgen':
                if 'om_terrain'in e:e['om_terrain']=rename(e['om_terrain'])
                else:assert e['nested_mapgen_id'].startswith(('dda_geo_godco_','dda_geo_exodii_','dda_geo_frontier_'))
            elif e['type']=='overmap_special':
                e['id']='dda_geo_'+e['id'].replace(' ','_').lower()
                e['occurrences']=[0,0] # Debug placement only; never populate normal worlds with empty shells.
                for c in e['overmaps']:
                    if 'overmap' in c:c['overmap']=rename(c['overmap'])
            elif e['type']=='terrain':
                assert e['id'].startswith(('dda_geo_exodii_','dda_geo_frontier_'))
                assert 'copy-from'not in e,('BN preview terrain requires a complete definition',e['id'])
                assert {'symbol','color','move_cost','name','description'}<=e.keys(),e['id']
            else:raise AssertionError(e['type'])
        result+=entries
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id']) for r in mod_cache()['records']}
    own=index_entries(result)
    assert not (own-BUILTIN_IDS)&(core|mods),sorted((own-BUILTIN_IDS)&(core|mods))
    hub=json.loads((OUT/'HUB_ADAPTATION_REPORT.json').read_text())
    generated={('overmap_terrain',n) for n in hub['generated_external_omt']}
    godco=json.loads((OUT/'GODCO_GEOMETRY_REPORT.json').read_text())
    generated.add(('overmap_terrain',godco['generated_BN_terrain']['id']))
    project=index_entries(json.loads((ROOT/'native/dda_hub_elevator_access.json').read_text()))
    assert not required(result)-core-own-generated-project,sorted(required(result)-core-own-generated-project)
    return {FILES[BASE+'modinfo.json']:[{'type':'MOD_INFO','id':MOD,'name':'DDA geometry preview (unfinished)','authors':['ProxysRE'],'description':'Terrain-only previews of the island prison, XEDRA church expanded Hub 01, campus, initial Godco retreat, Exodii sites, Isolated Road, gun show, Balthazar bunker and limnological station. Unfinished building geometry only: no content loot placements, inhabitants or quests. Debug placement in a test world. Surrounding forest retains BN generation.','category':'buildings','dependencies':['bn']}],FILES[BASE+'shells.json']:result}


def native_test():
    # Reuse the already compiled all-floor map fixture, retaining only its helper.
    from prepare_eldercare_sites import native_test as reference
    text=reference().split('\nTEST_CASE(',1)[0]
    text=text.replace('const char *terrain; };','const char *terrain; const char *loot_mask = nullptr; };',1)
    text=text.replace('void generate_site( int base, std::initializer_list<site_cell> cells )',
        'struct geometry_point { int omt_x; int omt_y; int x; int y; int z; const char *terrain; };\n'
        'void generate_site( int base, std::initializer_list<site_cell> cells,\n'
        '                    std::initializer_list<geometry_point> geometry = {} )')
    text=text.replace('    }\n    clear_all_state();\n}', '''        for( const auto &expected : geometry ) {
            if( expected.omt_x != column.first || expected.omt_y != column.second ) { continue; }
            INFO( "navigation terrain=" << expected.terrain << " z=" << expected.z );
            CHECK( generated.ter( tripoint_bub_ms( expected.x, expected.y, expected.z ) ) ==
                   ter_id( expected.terrain ) );
        }
    }
    clear_all_state();
}''')
    text=text.replace('CHECK( generated.ter( tripoint_bub_ms( 12, 12, cell.z ) ) != ter_id( "t_null" ) );', '''CHECK( generated.ter( tripoint_bub_ms( 12, 12, cell.z ) ) != ter_id( "t_null" ) );
            if( std::string( cell.terrain ).find( "dda_geo_" ) == 0 ) {
                for( int x = 0; x < 24; ++x ) {
                    for( int y = 0; y < 24; ++y ) {
                        const tripoint_bub_ms p( x, y, cell.z );
                        CHECK( generated.ter( p ) != ter_id( "t_null" ) );
                        if( cell.loot_mask == nullptr || cell.loot_mask[y * 24 + x] == '1' ) {
                            CHECK( generated.i_at( p ).empty() );
                        }
                    }
                }
            }''')
    entries=payloads()['native/dda_geometry_preview.json']
    from prepare_regional_locations import flatten
    predecessors={n:e['object']for e in entries if e['type']=='mapgen' and e['object'].get('predecessor_mapgen')for n in flatten(e.get('om_terrain',[]))}
    for i,special in enumerate(e for e in entries if e['type']=='overmap_special'):
        text+='\nTEST_CASE( "'+special['id']+'_all_floors_without_loot", "[dda_geometry]" )\n{\n    generate_site( '+str(4200+i*100)+', {\n'
        for c in special['overmaps']:
            if 'overmap' not in c:continue
            x,y,z=c['point'];name=c['overmap'];base=name.removesuffix('_north')
            mask=''
            if base in predecessors:
                assert name.endswith('_north')
                o=predecessors[base];assert len(o['rows'])==24 and all(len(r)==24 for r in o['rows'])
                bits=''.join('1' if o['terrain'].get(g,'t_null')!='t_null' else '0' for row in o['rows']for g in row)
                mask=', '+json.dumps(bits)
            text+=f'        {{ {x}, {y}, {z}, {json.dumps(name)}{mask} }},\n'
        frontier_specials={'dda_geo_isolated_road','dda_geo_gun_show','dda_geo_balthazar_bunker','dda_geo_limnological_station'}
        if special['id'] in frontier_specials|{'dda_geo_exodii_base','dda_geo_out-of-place_stone_barn','dda_geo_strange_warehouse'}:
            text+='    }, {\n'
            stem='FRONTIER'if special['id']in frontier_specials else 'EXODII'
            nav=json.loads((OUT/(stem+'_ADAPTATION_REPORT.json')).read_text())['navigation']
            for cell in special['overmaps']:
                name=cell.get('overmap','').removeprefix('dda_geo_').removesuffix('_north')
                x,y,z=cell['point']
                for e in nav.get(name,[]):
                    text+=f'        {{ {x}, {y}, {e["x"]}, {e["y"]}, {z}, {json.dumps(e["terrain"])} }},\n'
        if special['id']=='dda_geo_hub_01':
            text+='    }, {\n'
            nav=json.loads((OUT/'HUB_ACCESS_GEOMETRY.json').read_text())['navigation']
            for e in nav:
                x,y,z=e['point']
                text+=f'        {{ {x//24}, {y//24}, {x%24}, {y%24}, {z}, {json.dumps(e["terrain"])} }},\n'
        text+='    } );\n}\n'
    return text


def prepare(check=False):
    prepare_shells(check=True)
    from check_hub_geometry_access import prepare as check_access
    check_access(check=True)
    from prepare_campus_geometry import prepare as check_campus
    check_campus(check=True)
    from prepare_godco_geometry import prepare as check_godco
    check_godco(check=True)
    from adapt_exodii_geometry import prepare as check_exodii
    check_exodii(check=True)
    from adapt_frontier_geometry import prepare as check_frontier
    check_frontier(check=True)
    texts={p:json.dumps(v,indent=2,ensure_ascii=True)+'\n' for p,v in payloads().items()}
    texts['native/'+TEST]=native_test()
    for p,text in texts.items():
        path=ROOT/p
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('Geometry preview: seven isolated packages, no ID collisions; natural occurrences disabled; native validation pending')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');prepare(parser.parse_args().check)
