#!/usr/bin/env python3
"""Adapt Exodii first-layer geometry to BN while retaining source staging."""
import argparse,copy,json
from prepare_geometry_layer import ROOT,OUT
from prepare_exodii_geometry import prepare as stage,STRUCTURAL
from prepare_container_yards import required
from prepare_regional_locations import index_entries,flatten,BUILTIN_IDS
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache


def prepare(check=False):
    stage(check=True)
    source=json.loads((OUT/'EXODII_SHELLS.json').read_text())
    aliases={n:'dda_geo_exodii_'+n for n in sorted(STRUCTURAL|{'t_glassed_sand'})}
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(copy.deepcopy(source));changes=[]
    for e in entries:
        if e['type']=='overmap_terrain'and isinstance(e.get('see_cost'),str):
            old=e['see_cost'];assert old in ('high','full_high')
            e['see_cost']=5;changes.append({'ids':e['id'],'field':'see_cost','source':old,'BN':5})
        if e['type']=='overmap_special':
            e['flags']=['UNIQUE'if f=='OVERMAP_UNIQUE'else f for f in e.get('flags',[])]
    # Own concrete OMT inheritance must close within the package.
    by_id={n:e for e in entries if e['type']=='overmap_terrain'for n in flatten(e['id'])}
    for e in by_id.values():
        if 'copy-from'in e:assert e['copy-from']in by_id and 'copy-from'not in by_id[e['copy-from']]
    for a,b in zip(source,entries):
        if a['type']=='mapgen':assert rename(a['object'])==b['object']
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id'])for r in mod_cache()['records']}
    own=index_entries(entries);missing=required(entries)-own-core
    assert not missing,sorted(missing)
    assert not (own-BUILTIN_IDS)&(core|mods)
    # Project deterministic navigation terrain into each global-map cell.
    navigation={}
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else omt
        o=e['object'];width=24*len(matrix[0]);height=24*len(matrix)
        assert len(o['rows'])==height and all(len(r)==width for r in o['rows'])
        for y,row in enumerate(o['rows']):
            for x,glyph in enumerate(row):
                terrain=o['terrain'].get(glyph)
                if isinstance(terrain,str)and any(n in terrain for n in ('stairs','ladder','elevator')):
                    navigation.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':terrain})
    report={'status':'adapted_exodii_geometry_native_validation_pending','aliases':aliases,'schema_adaptations':changes,
      'unresolved_typed_refs':sorted(missing),'own_omt':len(by_id),'structural_nested_maps':len(STRUCTURAL),
      'navigation':navigation,'navigation_points':sum(map(len,navigation.values())),
      'limits':['Source and installed native generation pending','No actual character stair/elevator traversal certification','Natural preview placement disabled; later layers remain staged']}
    for name,value in [('EXODII_ADAPTED_SHELL.json',entries),('EXODII_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Exodii geometry: BN visibility costs, isolated nested/terrain IDs and navigation expectations verified')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
