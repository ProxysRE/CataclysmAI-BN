#!/usr/bin/env python3
"""Stage large urban locations independently of later content."""
import argparse,copy,hashlib,json
from collections import Counter
from pathlib import Path
from prepare_geometry_layer import ROOT,OUT,extract
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
SOURCE=OUT/'urban_sources'
PIN='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
TARGETS={'police_dept','textile_mill_museum','supermarket'}
UTILITIES=('roof_4x4_utility','roof_4x4_utility_1','roof_6x6_utility')


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
            names=list(flatten(e['om_terrain']))
            if not any(n.startswith(('police_dept','textile_mill_museum','supermarket'))for n in names):continue
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
    registrations={}
    catalog,_=read_sources()
    for path,text in catalog.items():
        if not path.startswith('dda/'):continue
        for e in json.loads(text):
            if e.get('type')in ('overmap_special','city_building')and e.get('id')in TARGETS:
                registrations[e['id']]=copy.deepcopy(e)
                e=copy.deepcopy(e)
                if e['type']=='city_building':
                    e['source_registration_type']=e['type'];e['type']='overmap_special'
                original.append(e)
            elif e.get('type')=='overmap_terrain':
                names=[n for n in flatten(e.get('id',[]))if n in mapped]
                if names:e=copy.deepcopy(e);e['id']=names;original.append(e)
    assert {e['id']for e in original if e['type']=='overmap_special'}==TARGETS
    entries,later,issues=extract(original,UTILITIES)
    aliases={n:'dda_geo_urban_'+n for n in UTILITIES}
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(entries)
    for e in entries:
        if e['type']=='overmap_special':
            later.append({'source_registration':registrations[e['id']]})
            if 'source_registration_type'in e:e.pop('source_registration_type')
            e['occurrences']=[0,0]
            if 'priority'in e:later.append({'source':e['id'],'field':'priority','value':e.pop('priority')})
        elif e['type']=='overmap_terrain'and 'travel_cost_type'in e:
            later.append({'source':e['id'],'field':'travel_cost_type','value':e.pop('travel_cost_type')})
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
    report={'status':'urban_geometry_staging_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),'world_maps':sum('om_terrain'in e for e in entries),'unique_omt':len(mapped),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'source_city_registration':'Police department and museum retain verbatim city_building registrations in the later-layer archive; shell registrations are zero-occurrence special candidates only','inline_mapping_projection':mapping_projection,'unresolved_typed_refs':missing,'geometry_issues':issues,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'deferred_structural_nested':['11x11_gym_open: carpet terrain and palette dependencies retained in authenticated basement_nested.json; resolve before native embedding'],
      'limits':['Not in native preview; generation and schema validation pending','Later-layer furnishings, loot, inhabitants, camp fields and quests retained separately','Existing BN external cells retain stock generation','No completion credit before native tests']}
    for name,value in [('URBAN_SHELLS.json',entries),('URBAN_LATER_LAYERS.json',later),('URBAN_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print(json.dumps({k:v for k,v in report.items()if k!='inline_mapping_projection'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
