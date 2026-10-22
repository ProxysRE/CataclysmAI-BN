#!/usr/bin/env python3
"""Adapt the three large shells without hiding their cross-floor roof blocker."""
import argparse,copy,json,hashlib,re
from prepare_large_site_geometry import prepare as stage,SOURCE
from prepare_geometry_layer import ROOT,OUT
from compare_location_catalog import read_sources
from prepare_container_yards import required
from prepare_regional_locations import index_entries,BUILTIN_IDS
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache


def prepare(check=False):
    stage(check=True)
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    files={p:json.loads((SOURCE/p).read_bytes())for p in manifest['files']}
    src={e['id']:e for e in files['data/json/furniture_and_terrain/terrain-manufactured.json']if e.get('type')=='terrain'}
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    raw=json.loads((OUT/'LARGE_SITES_SHELLS.json').read_text(encoding='utf-8'))
    counterparts={'t_metal_roof':'t_metal_flat_roof','t_carpet_wood_yellow':'t_carpet_yellow',
      't_truss_pillar':'t_radio_tower','t_bollard':'t_little_column',
      'ch_steel_chunk':'steel_chunk','ch_steel_lump':'steel_lump','pipe_fittings':'pipe'}
    for kind,name in sorted(required(raw)-core):
        if kind!='terrain':continue
        for base in ('t_strconc_wall','t_sconc_wall','t_concrete_wall','t_wall'):
            if name.startswith(base+'_')and ('terrain',base)in core:counterparts[name]=base;break
    aliases=dict(counterparts)
    for n in ('t_drill_machinery','t_drill_string','t_underwater_drill_string','t_saltwater_cube'):
        aliases[n]='dda_geo_large_'+n.removeprefix('t_')
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    physical=[];deferred=[]
    for n in ('t_drill_machinery','t_drill_string','t_underwater_drill_string'):
        e=copy.deepcopy(src[n]);assert 'copy-from'not in e
        if e.get('looks_like')and ('terrain',e['looks_like'])not in core:
            deferred.append({'source':n,'field':'looks_like','value':e.pop('looks_like')})
        physical.append(rename(e))
    water_root=OUT/'waterside_adaptation_sources';wm=json.loads((water_root/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    water_path='bn/data/json/furniture_and_terrain/terrain-liquids.json';water_raw=(water_root/water_path).read_bytes()
    assert hashlib.sha256(water_raw).hexdigest()==wm['files'][water_path]
    water=copy.deepcopy(next(e for e in json.loads(water_raw)if e.get('id')=='t_water_cube'))
    source=next(e for e in files['data/json/furniture_and_terrain/terrain-liquids.json']if e.get('id')=='t_saltwater_cube')
    water.pop('//',None);water.update({k:source[k]for k in ('name','description','symbol','color','move_cost')})
    water['id']=aliases['t_saltwater_cube'];water['flags'].append('SALT_WATER');physical.append(water)
    deferred.append({'source':'t_saltwater_cube','source_definition':source,
                     'note':'Uses BN water-cube flags plus native SALT_WATER and ordinary water_source. DDA liquid temperature is excluded.'})
    catalog,_=read_sources()
    abstracts={e['abstract']:e for p,text in catalog.items()if p.startswith('dda/')for e in json.loads(text)if 'abstract'in e}
    entries=[]
    for e in rename(raw):
        parent=e.get('copy-from')
        if parent in ('generic_office_skyscraper','generic_stadium_park'):
            base=copy.deepcopy(abstracts[parent]);deferred.append({'source':e['id'],'abstract':base.copy()})
            for k in ('abstract','vision_levels','mondensity','post_process_generators'):base.pop(k,None)
            base.update({k:v for k,v in e.items()if k!='copy-from'})
            if isinstance(base.get('see_cost'),str):assert base['see_cost']=='none';base['see_cost']=0
            e=base
        entries.append(e)
    entries+=physical;own=index_entries(entries)
    registry=OUT/'waterside_adaptation_sources/bn/src/overmap/overmap.h'
    flag_block=registry.read_text(encoding='utf-8').split('oter_flags_map = {',1)[1].split('};',1)[0]
    supported_flags=set(re.findall(r'\{"([A-Z_]+)", oter_flags::',flag_block))
    for e in entries:
        if e['type']!='overmap_terrain':continue
        unknown=set(e.get('flags',[]))-supported_flags
        assert unknown<={'OCEAN'},(e['id'],unknown)
        if unknown:
            deferred.append({'source':e['id'],'field':'flags','value':sorted(unknown),'note':'BN does not implement the OCEAN overmap flag; source sea placement remains a separate integration requirement.'})
            e['flags']=[f for f in e['flags']if f in supported_flags]
    missing=sorted(required(entries)-own-core)
    for e in physical:
        assert {'symbol','color','move_cost','name','description'}<=e.keys(),e['id']
        for action in ('bash','deconstruct'):
            if action not in e:continue
            assert ('terrain',e[action]['ter_set'])in own|core|BUILTIN_IDS,e['id']
            for drop in e[action].get('items',[]):assert ('item',drop['item'])in core,drop
    mods={(e['type'],e['id'])for e in mod_cache()['records']}
    assert not (own-BUILTIN_IDS)&(core|mods)
    assert not missing,missing
    report={'status':'large_sites_physical_adaptation_prepared_not_installed','native_embedded':False,'runtime_validated':False,
      'aliases':aliases,'counterparts':counterparts,'new_terrain_definitions':len(physical),'unresolved_typed_refs':missing,
      'deferred_source_fields':deferred,'geometry_issues':json.loads((OUT/'LARGE_SITES_GEOMETRY_REPORT.json').read_text(encoding='utf-8'))['geometry_issues'],
      'preserved':['All source rows, dimensions, source-level placements and weighted room alternatives','Inactive drilling machinery, drill strings and their destruction transitions','BN submerged-water semantics and salt-water collection'],
      'adaptations':['Unavailable paint uses the same BN wall construction','Ordinary yellow carpet and metal flat roof use BN counterparts','Truss supports reuse BN radio-tower steel structure; bash thresholds and steel quantities coincide, appearance/flags differ','Bollards reuse BN small columns; source appearance/material details differ','DDA component tiers reuse stock BN steel_lump/steel_chunk; pipe_fittings drops use BN pipe with unchanged counts','Source overmap parents expanded into BN-compatible physical registration fields'],
      'remaining':['Cross-floor nested greenhouse roofs require real BN z-offset support or exact source-preserving relocation','Oil-platform ocean placement predicate and surrounding ocean context require explicit BN adaptation','Native schema/loading/generation','All-floor navigation and deep-water access'],
      'limits':['Not embedded and no completion credit','Do not install the cross-floor roof nest at the current z level','No oil-drilling system is invented; source machinery is inactive']}
    for name,value in [('LARGE_SITES_ADAPTED_SHELL.json',entries),('LARGE_SITES_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';path=OUT/name
        if check:assert path.read_text(encoding='utf-8')==text,path
        else:path.write_text(text,encoding='utf-8')
    print('Large-site physical references closed; two cross-floor greenhouse placements remain explicit native integration blockers')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
