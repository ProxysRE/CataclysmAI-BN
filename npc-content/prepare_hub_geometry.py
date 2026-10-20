#!/usr/bin/env python3
"""Resolve the Hub shell against authenticated BN counterparts, without installing it."""
import argparse,copy,hashlib,json
from prepare_geometry_layer import ROOT,OUT,prepare as prepare_shells
from prepare_container_yards import required
from prepare_regional_locations import index_entries
from compare_location_catalog import read_sources
from export_bn_ids import read_cache

ALIASES={'t_zebra':'t_pavement_y','t_strconc_floor_olight':'t_thconc_floor_olight','t_secretdoor_concrete_c':'t_secretdoor_metal_c'}

def prepare(check=False):
    prepare_shells(check=True)
    entries=copy.deepcopy(json.loads((OUT/'SHELLS.json').read_text())['hub_01'])
    catalog,_=read_sources()
    source_path='dda/data/json/overmap/overmap_terrain/overmap_terrain_transportation.json'
    road=next(e for e in json.loads(catalog[source_path]) if e.get('abstract')=='road_abstract')
    parent=next(e for e in json.loads(catalog['dda/data/json/overmap/overmap_terrain/overmap_terrain_abstract.json']) if e.get('abstract')==road['copy-from'])
    assert road['copy-from']=='generic_transportation' and 'copy-from' not in parent
    # Only BN-supported presentation fields are inherited; there are no structural flags.
    assert not set(road)&{'flags','spawns','mapgen'} and not set(parent)&{'flags','spawns','mapgen'}
    inherited={**parent,**road}
    for e in entries:
        if e['type']=='overmap_terrain' and e.get('copy-from')=='road_abstract':
            e.pop('copy-from')
            for k in ('color','looks_like'):e.setdefault(k,inherited[k])
    def walk(v):
        if isinstance(v,str):return ALIASES.get(v,v)
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
        return v
    entries=walk(entries)
    deferred_flags=[]
    deferred_schema=[]
    for e in entries:
        if e['type']=='overmap_special' and 'priority' in e:
            deferred_schema.append({'id':e['id'],'field':'priority','source_value':e.pop('priority')})
        if e['type']=='overmap_terrain' and isinstance(e.get('name'),dict):
            deferred_schema.append({'ids':e['id'],'field':'name','source_value':e['name']})
            e['name']=e['name']['str']
        if e['type']=='overmap_terrain' and 'SHOULD_NOT_SPAWN' in e.get('flags',[]):
            deferred_flags.append({'ids':e['id'],'flag':'SHOULD_NOT_SPAWN'})
            e['flags'].remove('SHOULD_NOT_SPAWN')
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    own=index_entries(entries)
    project_entries=json.loads((ROOT/'native/dda_hub_elevator_access.json').read_text())
    project=index_entries(project_entries)
    assert {('terrain','t_elevator_control_robofac_up'),('terrain','t_elevator_control_robofac_down')}<=project
    # Resolve inherited flags from the pinned BN declarations, not substring guesses.
    omt={}
    for p,text in catalog.items():
        if not p.startswith('bn/'):continue
        for e in json.loads(text):
            if e.get('type')=='overmap_terrain':
                ids=e.get('id',[]);ids=[ids] if isinstance(ids,str) else ids
                for n in ids:omt[n]=(p,e)
    def flags(n,trail=()):
        assert n not in trail,n
        p,e=omt[n]
        if 'flags' in e:return e['flags']
        return flags(e['copy-from'],trail+(n,)) if 'copy-from'in e else []
    generated={};refs=required(entries)
    for kind,n in sorted(refs-core-own-project):
        if kind!='overmap_terrain':continue
        for suffix in ('_north','_east','_south','_west'):
            if n.endswith(suffix) and n[:-len(suffix)] in omt:
                base=n[:-len(suffix)];f=flags(base)
                assert not {'NO_ROTATE','LINEAR'}&set(f),(n,f)
                generated[(kind,n)]={'base':base,'declaration':omt[base][0],'inherited_flags':f}
        if n=='subway_ns':
            assert 'LINEAR'in flags('subway')
            generated[(kind,n)]={'base':'subway','declaration':omt['subway'][0],'inherited_flags':flags('subway')}
    missing=refs-core-own-project-set(generated)
    assert not missing,sorted(missing)
    for e in entries:
        if e['type']=='mapgen':
            original=next(x for x in json.loads((OUT/'SHELLS.json').read_text())['hub_01'] if x.get('om_terrain')==e.get('om_terrain'))
            assert e['object']['rows']==original['object']['rows']
    provenance=json.loads((OUT/'HUB_REUSE_SOURCES.json').read_text())
    assert provenance['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    from prepare_eldercare_assets import ALIASES as EXISTING_COUNTERPARTS
    assert ALIASES['t_zebra']==EXISTING_COUNTERPARTS[('terrain','t_zebra')][0]
    bn={e['id']:e for p,es in provenance['files'].items() if p.startswith('bn/') for e in es}
    assert bn['t_thconc_floor_olight']['light_emitted']==120
    assert bn['t_secretdoor_metal_c']['open']=='t_secretdoor_metal_o' and bn['t_secretdoor_metal_o']['close']=='t_secretdoor_metal_c'
    report={'status':'adapted_geometry_candidate_not_installed','native_embedded':False,'runtime_validated':False,
      'counterparts':ALIASES,'differences':['Crosswalk uses BN yellow road markings, not DDA zebra artwork','Overhead light retains intensity 120; floor destruction, roof and local lighting follow BN thick-concrete floor','Secret passage retains BN closed/open door mechanics; appearance/material/drops are metal instead of DDA concrete'],
      'unsupported_omt_flags_preserved_in_source':deferred_flags,'schema_adaptations':deferred_schema,
      'road_inheritance':{'source':source_path,'source_abstract':road,'source_parent':parent,'applied_fields':['color','looks_like'],'not_ported':['travel_cost_type','land_use_code','vision_levels']},
      'generated_external_omt':{n:p for (t,n),p in sorted(generated.items())},
      'existing_project_terrain':sorted(n for t,n in refs&project if t=='terrain'),
      'project_provider_sha256':hashlib.sha256((ROOT/'native/dda_hub_elevator_access.json').read_bytes()).hexdigest(),
      'unresolved_typed_refs':sorted(missing),'mapgen_definitions':sum(e['type']=='mapgen' for e in entries),
      'remaining':['Native OMT flag/schema validation','Full generated map traversal and stair/elevator alignment','BN-only geometry reconciliation before replacing the existing Hub','NPCs, items, furniture and quests remain in later layers']}
    for p,v in [('HUB_ADAPTED_SHELL.json',entries),('HUB_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(v,indent=2,ensure_ascii=True)+'\n';path=OUT/p
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('Hub geometry candidate: 11 generated BN OMT identities, two existing project terrain and three stock terrain counterparts; typed closure passed; native validation pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
