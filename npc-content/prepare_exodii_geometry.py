#!/usr/bin/env python3
"""Stage authenticated Exodii geometry; never install unresolved shells."""
import argparse,copy,hashlib,json,re
from collections import Counter
from pathlib import Path
from compare_location_catalog import read_sources
from prepare_geometry_layer import ROOT,OUT,NAV_FURNITURE
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
SOURCE=OUT/'exodii_sources'
PIN='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
SPECIALS={'exodii_base','Out-of-place Stone Barn','Strange warehouse'}
STRUCTURAL={'rubik_store_base','luliya_base','weaponmaster_workshop_base'}

def prepare(check=False):
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text())
    assert manifest['dda_commit']==PIN
    files={}
    for name,digest in manifest['files'].items():
        raw=(SOURCE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
        files[name]=json.loads(raw)
    assert len(files)==9
    palettes={e['id']:e for n,es in files.items()if '/mapgen_palettes/'in n for e in es}
    original=[copy.deepcopy(e)for n,es in files.items()if '/mapgen/'in n for e in es if 'om_terrain'in e or e.get('nested_mapgen_id')in STRUCTURAL]
    mapped={n for e in original for n in flatten(e.get('om_terrain',[]))}
    catalog,_=read_sources()
    for name,text in catalog.items():
        if not name.startswith('dda/'):continue
        for source in json.loads(text):
            if source.get('type')=='overmap_special'and source.get('id')in SPECIALS:original.append(copy.deepcopy(source))
            elif source.get('type')=='overmap_terrain':
                names=list(flatten(source.get('id',[])));selected=[n for n in names if n in mapped]
                if selected:
                    e=copy.deepcopy(source);e['id']=selected;original.append(e)
    entries=[];later=[];issues=[]
    for source in original:
        e=copy.deepcopy(source)
        if e['type']=='mapgen':
            o=expand(e['object'],palettes);assert not o.get('palettes')
            terrain=copy.deepcopy(o.get('terrain',{}));furniture=copy.deepcopy(o.get('furniture',{}))
            for glyph,piece in o.get('mapping',{}).items():
                for key,target in [('terrain',terrain),('furniture',furniture)]:
                    if key in piece:
                        assert glyph not in target or target[glyph]==piece[key],(glyph,key)
                        target[glyph]=copy.deepcopy(piece[key])
            used=set(''.join(o.get('rows',[])))
            out={k:copy.deepcopy(o[k])for k in ('rows','fill_ter','mapgensize','rotation','predecessor_mapgen')if k in o}
            out['terrain']={c:v for c,v in terrain.items()if c in used}
            nav={c:v for c,v in furniture.items()if c in used and NAV_FURNITURE.search(str(v))}
            if nav:out['furniture']=nav
            nested={c:v for c,v in o.get('nested',{}).items()if c in used and any(n in str(v)for n in STRUCTURAL)}
            if nested:out['nested']=nested
            unknown=used-set(out['terrain'])-set(nav)-set(nested)-{' '}
            for c in sorted(unknown):
                if 'fill_ter'in out:out['terrain'][c]=copy.deepcopy(out['fill_ter'])
                elif c in furniture:
                    out.setdefault('furniture',{})[c]='f_null'
                    if 'om_terrain'in e:issues.append({'type':'source_world_map_has_content_only_glyph_without_fill','map':e['om_terrain'],'glyph':c})
                else:issues.append({'type':'unbound_source_glyph','map':e.get('om_terrain',e.get('nested_mapgen_id')),'glyph':c})
            later.append({'source':{k:v for k,v in source.items()if k!='object'},'expanded_source_object':o,'geometry_fields':list(out)})
            e['object']=out;e['method']='json'
            rows=out['rows'];slots=e.get('om_terrain')
            if isinstance(slots,str):width=height=24
            elif slots:width=24*len(slots[0]);height=24*len(slots)
            else:width,height=out['mapgensize']
            assert len(rows)==height and all(len(row)==width for row in rows),(e.get('om_terrain'),width,height)
        else:
            late={}
            keys=('spawns','extras','mondensity','vision_levels','travel_cost_type')if e['type']=='overmap_terrain'else ('priority',)
            for k in keys:
                if k in e:late[k]=e.pop(k)
            if late:later.append({'source':source,'deferred_fields':late})
            if e['type']=='overmap_special':
                # Staged shells must never become naturally occurring empty sites.
                e['occurrences']=[0,0]
                for c in e['overmaps']:
                    for k in list(c):
                        if k not in ('point','overmap','locations'):later.append({'special':e['id'],'point':c['point'],'field':k,'value':c.pop(k)})
        entries.append(e)
    sand=next(e for es in files.values()for e in es if e.get('id')=='t_glassed_sand')
    sand=copy.deepcopy(sand)
    sand_deferred={k:sand.pop(k)for k in ('connect_groups','connects_to')}
    entries.append(sand)
    own=index_entries(entries);core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id'])for r in mod_cache()['records']}
    declared={n for t,n in own if t=='overmap_terrain'}
    assert mapped==declared,(mapped-declared,declared-mapped)
    assert ('terrain',sand['bash']['ter_set'])in core
    missing=sorted(required(entries)-own-core)
    report={'status':'geometry_staged_not_installed','native_embedded':False,'runtime_validated':False,
      'source_commit':PIN,'source_files':len(files),'definitions':dict(Counter(e['type']for e in entries)),
      'world_maps':sum('om_terrain'in e for e in entries),'structural_nested_maps':len(STRUCTURAL),'unique_omt':len(mapped),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'new_terrain':{'id':'t_glassed_sand','reason':'Absent from pinned BN core and all bundled mods; source movement and bash behavior retained','deferred_visual_connections':sand_deferred},'unresolved_typed_refs':missing,'geometry_issues':issues,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'limits':['Not in native patch or preview; no percentage credit','Furniture, loot, inhabitants, camp registration and quests remain archived','Missing terrain must be compared to BN equivalents before importing definitions','No player traversal or full source behavior parity claim']}
    for name,value in [('EXODII_SHELLS.json',entries),('EXODII_LATER_LAYERS.json',later),('EXODII_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
