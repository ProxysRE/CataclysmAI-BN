#!/usr/bin/env python3
"""Resolve frontier geometry using BN mechanisms without enabling later quests."""
import argparse,copy,hashlib,json
from prepare_geometry_layer import ROOT,OUT
from prepare_frontier_geometry import prepare as stage,TARGETS
from prepare_regional_locations import flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from prepare_hub_geometry import ALIASES as HUB_ALIASES
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
SOURCE=OUT/'frontier_adaptation_sources'
PINS={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
ALIASES={'t_canvas_roof':'dda_geo_frontier_canvas_roof','t_card_artisans':'dda_geo_frontier_artisan_reader','t_intercom_balthazar':'dda_geo_frontier_balthazar_intercom','t_secretdoor_concrete_c':HUB_ALIASES['t_secretdoor_concrete_c']}


def prepare(check=False):
    stage(check=True)
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text());assert manifest['pins']==PINS
    source={}
    for path,digest in manifest['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        for e in json.loads(raw):
            if 'id'in e:source[(path.split('/')[0],e['id'])]=e
    raw_report=json.loads((OUT/'FRONTIER_GEOMETRY_REPORT.json').read_text())
    assert not raw_report['geometry_issues']
    assert {tuple(x)for x in raw_report['unresolved_typed_refs']}=={('terrain',n)for n in ALIASES}
    original=json.loads((OUT/'FRONTIER_SHELLS.json').read_text())
    def rename(v):
        if isinstance(v,str):return ALIASES.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(copy.deepcopy(original))
    roof=copy.deepcopy(source['dda','t_canvas_roof']);roof['id']=ALIASES['t_canvas_roof'];entries.append(roof)
    panels=[]
    for src,parent in [('t_card_artisans','t_card_science'),('t_intercom_balthazar','t_intercom')]:
        dda=source['dda',src];bn=source['bn',parent]
        assert dda['move_cost']==bn['move_cost']==0
        assert dda['symbol']==bn['symbol']and dda['color']==bn['color']
        entries.append({'type':'terrain','id':ALIASES[src],'copy-from':parent,'name':dda['name'],'description':dda['description'],'examine_action':'none'})
        panels.append({'source':src,'BN_geometry_parent':parent,'preview':ALIASES[src],'source_examine_action':dda['examine_action'],'preview_examine_action':'none','reason':'Physical panel only in first layer; faction reader and NPC communication deferred, no substitute science-card or unrelated intercom behavior enabled'})
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    own=index_entries(entries);mods={(r['type'],r['id'])for r in mod_cache()['records']}
    assert not(own-BUILTIN_IDS)&(core|mods)
    for e in entries:
        if e['type']=='terrain'and 'copy-from'in e:assert ('terrain',e['copy-from'])in core
    missing=required(entries)-own-core;assert not missing,sorted(missing)
    navigation={}
    physical=set(ALIASES.values())|{'t_secretdoor_metal_c'}
    for a,b in zip(original,entries):
        if a['type']=='mapgen':assert rename(a['object'])==b['object']
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        o=e['object'];assert len(o['rows'])==24*len(matrix)and all(len(r)==24*len(matrix[0])for r in o['rows'])
        for y,row in enumerate(o['rows']):
            for x,glyph in enumerate(row):
                terrain=o.get('terrain',{}).get(glyph)
                if isinstance(terrain,str)and(terrain in physical or any(n in terrain for n in ('stairs','ladder','elevator'))):
                    navigation.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':terrain})
    report={'status':'adapted_geometry_not_runtime_validated','counterparts':ALIASES,'panel_adaptations':panels,
      'new_roof':'Exact DDA canvas terrain definition with isolated preview identity; source movement, flags and bash retained',
      'secret_door_difference':'Reuse previously reviewed BN closed/open metal secret-door pair as in Hub; material/appearance/destruction are BN metal, not concrete',
      'unresolved_typed_refs':sorted(missing),'navigation':navigation,'navigation_points':sum(map(len,navigation.values())),
      'remaining':['Source and installed native generation','Full traversal and door/ladder operation','Later-layer faction cardreader and Balthazar NPC intercom behavior'],
      'limits':['Preview has no natural placement','First layer does not provide working faction access controls or NPC intercom','No claim of concrete secret-door material parity']}
    for name,value in [('FRONTIER_ADAPTED_SHELL.json',entries),('FRONTIER_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Frontier: all four terrain obligations resolved; physical panels isolated from deferred quest behavior')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
