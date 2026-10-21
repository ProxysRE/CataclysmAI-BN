#!/usr/bin/env python3
"""Prepare wooden embrasure geometry without changing the native preview."""
import argparse,copy,hashlib,json
from prepare_geometry_layer import ROOT,OUT
from prepare_raider_geometry import prepare as stage
from prepare_regional_locations import flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
SOURCE=OUT/'raider_adaptation_sources'
PINS={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
ALIASES={'t_embrasure_wood':'dda_geo_raider_embrasure_wood','t_wall_wood_widened':'dda_geo_raider_wall_wood_widened','t_wood_roof':'t_flat_roof'}

def prepare(check=False):
    stage(check=True)
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text());assert manifest['pins']==PINS
    files={}
    for path,digest in manifest['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=raw.decode()
    dda=json.loads(files['dda/data/json/furniture_and_terrain/terrain-embrasures.json'])
    source={e['id']:e for e in dda};bn=json.loads(files['bn/data/json/furniture_and_terrain/terrain-walls.json'])
    assert any('CONNECT_TO_WALL'in e.get('flags',[])for e in bn)
    header=files['bn/src/map/mapdata.h']
    for flag in ('WALL','AUTO_WALL_SYMBOL','THIN_OBSTACLE','SMALL_PASSAGE','CONNECT_TO_WALL'):assert 'TFLAG_'+flag in header
    def rename(v):
        if isinstance(v,str):return ALIASES.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(json.loads((OUT/'RAIDER_SHELLS.json').read_text()));deferred=[]
    for name in ('t_embrasure_wood','t_wall_wood_widened'):
        e=rename(copy.deepcopy(source[name]))
        for field in ('connect_groups','connects_to'):
            assert e.pop(field)=='WALL'
        e['flags'].append('CONNECT_TO_WALL')
        for field in ('hit_field','destroyed_field'):
            deferred.append({'source':name,'bash_field':field,'value':e['bash'].pop(field)})
        assert 'copy-from'not in e and {'symbol','color','move_cost','name','description'}<=e.keys()
        expected=(0,90)if name=='t_embrasure_wood'else(4,60)
        assert (e['move_cost'],e['coverage'])==expected
        entries.append(e)
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']));own=index_entries(entries)
    mods={(r['type'],r['id'])for r in mod_cache()['records']};assert not(own-BUILTIN_IDS)&(core|mods)
    for e in entries[-2:]:
        assert ('terrain',e['roof'])in core
        assert ('terrain',e['bash']['ter_set'])in core|own
        for item in e['bash']['items']:assert ('item',item['item'])in core
    missing=required(entries)-own-core;assert not missing,sorted(missing)
    navigation={}
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        for y,row in enumerate(e['object']['rows']):
            for x,glyph in enumerate(row):
                terrain=e['object'].get('terrain',{}).get(glyph)
                if isinstance(terrain,str)and(terrain in ALIASES.values()or any(n in terrain for n in ('stairs','ladder','elevator'))):
                    navigation.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':terrain})
    report={'navigation':navigation,'navigation_points':sum(map(len,navigation.values())),'status':'raider_geometry_adapted_not_installed','native_embedded':False,'runtime_validated':False,
      'aliases':ALIASES,'new_terrain_definitions':2,'unresolved_typed_refs':sorted(missing),'deferred_bash_fields':deferred,
      'preserved':['Original world-map rows and placements','Wooden material flags, coverage 90/60 and movement 0/4','Two-stage source bash thresholds and item quantities'],
      'adaptations':['BN CONNECT_TO_WALL replaces source wall connectivity groups','Existing BN flat roof replaces source wooden roof; roof material is not identical','Source hit/destroyed dust and splinter field emission is deferred'],
      'remaining':['Native schema and all-floor generation','Combat cover, mounted shooting and reach-attack behavior','Bash, fire and widened-opening traversal tests'],
      'limits':['No native patch changes or percentage credit','Typed closure and static flags do not certify combat parity']}
    for name,value in [('RAIDER_ADAPTED_SHELL.json',entries),('RAIDER_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Raider geometry: wooden embrasure and widened opening prepared; native and combat checks pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
