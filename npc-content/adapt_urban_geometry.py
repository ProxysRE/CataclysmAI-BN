#!/usr/bin/env python3
"""Close urban geometry references using concrete stock BN pavement mechanics."""
import argparse,copy,hashlib,json
from prepare_urban_geometry import prepare as stage
from prepare_geometry_layer import ROOT,OUT
from prepare_regional_locations import index_entries,BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE=OUT/'urban_adaptation_sources'
PINS={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
ID='dda_geo_urban_zebra'

def prepare(check=False):
    stage(check=True)
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text())
    assert manifest['pins']==PINS
    files={}
    for path,digest in manifest['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=json.loads(raw)
    suffix='/data/json/furniture_and_terrain/terrain-floors-outdoors.json'
    source=next(e for e in files['dda'+suffix]if e.get('id')=='t_zebra')
    pavement=next(e for e in files['bn'+suffix]if e.get('id')=='t_pavement')
    crossing=copy.deepcopy(pavement)
    crossing.update({k:copy.deepcopy(source[k])for k in ('name','description','symbol','color')})
    crossing['id']=ID
    assert not crossing.get('copy-from')
    assert crossing['move_cost']==source['move_cost']==2
    assert crossing['flags']==source['flags']
    assert crossing['bash']==pavement['bash']
    aliases={'t_zebra':ID}
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(json.loads((OUT/'URBAN_SHELLS.json').read_text()))+[crossing]
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id'])for r in mod_cache()['records']};own=index_entries(entries)
    assert not (own-BUILTIN_IDS)&(core|mods)
    missing=sorted(required(entries)-own-core);assert not missing,missing
    assert ('terrain',crossing['bash']['ter_set'])in core
    for item in crossing['bash']['items']:assert ('item',item['item'])in core
    expected={}
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        for y,row in enumerate(e['object']['rows']):
            for x,glyph in enumerate(row):
                terrain=e['object'].get('terrain',{}).get(glyph)
                if isinstance(terrain,str)and(terrain==ID or any(n in terrain for n in ('stairs','ladder','elevator'))):
                    expected.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':terrain})
    report={'status':'urban_geometry_adapted_not_installed','native_embedded':False,'runtime_validated':False,
      'aliases':aliases,'new_terrain_definitions':1,'unresolved_typed_refs':missing,
      'navigation_and_marking_expectations':expected,'expectation_count':sum(map(len,expected.values())),
      'preserved':['All staged rows and 66 own OMT','Police gym carpet overlay and placement','DDA crossing name, description, white symbol and movement cost'],
      'adaptations':['Concrete BN pavement definition supplies physical and destruction mechanics','BN PAVEMENT connection replaces DDA PAVEMENT_ZEBRA grouping','Destruction leaves BN dirt instead of DDA null terrain','Unavailable wall paint variants already use BN walls of the same construction'],
      'remaining':['Native BN parameter and mapgen schema loading','All-floor source and installed generation','Player traversal and stair continuity','Tileset-specific crosswalk appearance'],
      'limits':['Typed closure is not native validation','No native patch changes or completion credit']}
    for name,value in [('URBAN_ADAPTED_SHELL.json',entries),('URBAN_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Urban geometry typed references closed; native loading and generation pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
