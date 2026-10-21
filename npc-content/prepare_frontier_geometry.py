#!/usr/bin/env python3
"""Stage four linked frontier locations independently of their later content."""
import argparse,copy,hashlib,json
from collections import Counter
from pathlib import Path
from prepare_geometry_layer import ROOT,OUT,extract,glyphs
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
SOURCE=OUT/'frontier_sources'
PIN='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
TARGETS={'isolated_road','gun_show','balthazar_bunker','limnological_station'}
UTILITIES=('roof_4x4_utility','roof_4x4_utility_1')


def prepare(check=False):
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text());assert manifest['dda_commit']==PIN
    files={}
    for name,digest in manifest['files'].items():
        raw=(SOURCE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,name
        files[name]=json.loads(raw)
    assert len(files)==7
    shared=shared_sources()
    palettes={e['id']:e for name,es in shared.items()if name.startswith('dda/')for e in es if e.get('type')=='palette'}
    palettes.update({e['id']:e for name,es in files.items()for e in es if e.get('type')=='palette'})
    original=[];mapping_projection=[]
    for name,es in files.items():
        for e in es:
            if e.get('type')!='mapgen'or 'om_terrain'not in e:continue
            e=copy.deepcopy(e);e['object']=expand(e['object'],palettes);o=e['object']
            assert not o.get('palettes'),(name,o.get('palettes'))
            # Inline mapping terrain is real geometry, not later-layer furnishing.
            for glyph,piece in o.get('mapping',{}).items():
                for key in ('terrain','furniture'):
                    if key not in piece:continue
                    assert glyph not in o.get(key,{})or o[key][glyph]==piece[key],(glyph,key)
                    o.setdefault(key,{})[glyph]=copy.deepcopy(piece[key])
                    mapping_projection.append({'map':e['om_terrain'],'glyph':glyph,'field':key,'value':piece[key]})
            original.append(e)
    mapped={n for e in original for n in flatten(e['om_terrain'])}
    for es in shared.values():
        for e in es:
            if e.get('nested_mapgen_id')in UTILITIES:original.append(copy.deepcopy(e))
    catalog,_=read_sources()
    for path,text in catalog.items():
        if not path.startswith('dda/'):continue
        for e in json.loads(text):
            if e.get('type')=='overmap_special'and e.get('id')in TARGETS:original.append(copy.deepcopy(e))
            elif e.get('type')=='overmap_terrain':
                names=[n for n in flatten(e.get('id',[]))if n in mapped]
                if names:e=copy.deepcopy(e);e['id']=names;original.append(e)
    assert {e['id']for e in original if e['type']=='overmap_special'}==TARGETS
    entries,later,issues=extract(original,UTILITIES)
    aliases={n:'dda_geo_frontier_'+n for n in UTILITIES}
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(entries)
    for e in entries:
        if e['type']=='overmap_special':
            later.append({'source_special':next(x for x in original if x.get('type')=='overmap_special'and x['id']==e['id'])})
            e['occurrences']=[0,0]
            if 'priority'in e:later.append({'source':e['id'],'field':'priority','value':e.pop('priority')})
        elif e['type']=='overmap_terrain'and 'travel_cost_type'in e:
            later.append({'source':e['id'],'field':'travel_cost_type','value':e.pop('travel_cost_type')})
    bymap={n:e for e in entries if 'om_terrain'in e for n in flatten(e['om_terrain'])}
    declared={n for e in entries if e['type']=='overmap_terrain'for n in flatten(e['id'])}
    assert mapped==declared,(mapped-declared,declared-mapped)
    for a,b in zip(original,entries):
        if a['type']=='mapgen':assert a['object']['rows']==b['object']['rows']
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        rows=e['object']['rows'];assert len(rows)==24*len(matrix)and all(len(row)==24*len(matrix[0])for row in rows),e['om_terrain']
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id'])for r in mod_cache()['records']};own=index_entries(entries)
    missing=sorted(required(entries)-own-core)
    report={'status':'four_location_geometry_staging_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),'world_maps':sum('om_terrain'in e for e in entries),'unique_omt':len(mapped),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'inline_mapping_projection':mapping_projection,'unresolved_typed_refs':missing,'geometry_issues':issues,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'limits':['Not in native preview; generation and schema validation pending','Later-layer furnishings, loot, inhabitants, camp fields and quests retained separately','Existing BN external cells retain stock generation','No completion credit before native tests']}
    for name,value in [('FRONTIER_SHELLS.json',entries),('FRONTIER_LATER_LAYERS.json',later),('FRONTIER_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print(json.dumps({k:v for k,v in report.items()if k!='inline_mapping_projection'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
