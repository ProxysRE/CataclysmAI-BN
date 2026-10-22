#!/usr/bin/env python3
"""Stage XEDRA field sites and LIXA geometry with all later source content archived."""
import argparse,copy,hashlib,json
from collections import Counter
from prepare_geometry_layer import ROOT,OUT,extract,glyphs
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE=OUT/'research_sources'
TARGETS={'xedra_fishing_shack','xedra_morgantown','physics_lab_LIXA'}
TENT='tent_b_5x5_S'

def prepare(check=False):
    m=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert m['dda_commit']=='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    files={}
    for path,digest in m['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=json.loads(raw)
    palettes={e['id']:e for path,es in shared_sources().items()if path.startswith('dda/')for e in es if e.get('type')=='palette'}
    palettes.update({e['id']:e for es in files.values()for e in es if e.get('type')=='palette'})
    original=[];archive=[];projection=[]
    for path,es in files.items():
        for source in es:
            if path.endswith('rural_outdoors_nested.json')and source.get('nested_mapgen_id')!=TENT:continue
            if source.get('type')!='mapgen'or 'om_terrain'not in source:
                if source.get('type')!='palette':archive.append({'path':path,'source_definition':source})
                continue
            # The shared rural nested archive is not a fourth world-location package.
            assert not path.endswith('rural_outdoors_nested.json')
            e=copy.deepcopy(source);o=e['object']=expand(e['object'],palettes)
            assert not o.get('palettes'),(path,o.get('palettes'))
            for g,piece in o.get('mapping',{}).items():
                for key in ('terrain','furniture'):
                    if key in piece:
                        assert g not in o.get(key,{})or o[key][g]==piece[key]
                        o.setdefault(key,{})[g]=copy.deepcopy(piece[key]);projection.append({'map':e['om_terrain'],'glyph':g,'field':key})
            if 'fill_ter'not in o:
                for g in sorted(glyphs(o.get('rows',[]))-set(o.get('terrain',{}))-set(o.get('furniture',{}))-set(o.get('nested',{}))-{' ','.'}):
                    assert 'predecessor_mapgen'in o,(path,g)
                    o.setdefault('furniture',{})[g]='f_null'
            original.append(e)
    mapped={n for e in original for n in flatten(e['om_terrain'])}
    tent=next(copy.deepcopy(e)for es in files.values()for e in es if e.get('nested_mapgen_id')==TENT)
    original.append(tent)
    registrations=[]
    for path,text in read_sources()[0].items():
        if not path.startswith('dda/'):continue
        for source in json.loads(text):
            if source.get('type')=='overmap_special'and source.get('id')in TARGETS:
                registrations.append(copy.deepcopy(source));original.append(copy.deepcopy(source))
            elif source.get('type')=='overmap_terrain':
                names=set(flatten(source.get('id',[])))&mapped
                if names:e=copy.deepcopy(source);e['id']=sorted(names);original.append(e)
    assert {e['id']for e in registrations}==TARGETS
    entries,later,issues=extract(original,(TENT,))
    # The ruined tent's walls, door and floor are structural furniture.
    # Restore all weighted geometry bindings rather than flattening them to null.
    next(e for e in entries if e.get('nested_mapgen_id')==TENT)['object']['furniture']=copy.deepcopy(tent['object']['furniture'])
    def rename(v):
        if isinstance(v,str):return 'dda_geo_research_'+TENT if v==TENT else v
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    entries=rename(entries)
    for a,b in zip(original,entries):
        if a['type']=='mapgen':
            assert a['object'].get('rows')==b['object'].get('rows')
            for action in a['object'].get('set',[]):
                if action.get('id')=='f_LIXA_unfold_barrier':
                    b['object'].setdefault('set',[]).append(copy.deepcopy(action))
            for g,value in a['object'].get('furniture',{}).items():
                if value=='f_LIXA_unfold_barrier'and g in glyphs(a['object'].get('rows',[])):
                    b['object'].setdefault('furniture',{})[g]=value
    for e in entries:
        if e['type']=='overmap_special':
            e['occurrences']=[0,0]
            if 'priority'in e:later.append({'source':e['id'],'field':'priority','value':e.pop('priority')})
        elif e['type']=='overmap_terrain'and 'travel_cost_type'in e:later.append({'source':e['id'],'field':'travel_cost_type','value':e.pop('travel_cost_type')})
        elif e['type']=='mapgen'and 'om_terrain'in e:
            omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
            rows=e['object'].get('rows');assert rows
            assert len(rows)==24*len(matrix)and all(len(row)==24*len(matrix[0])for row in rows),e['om_terrain']
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(e['type'],e['id'])for e in mod_cache()['records']};own=index_entries(entries)
    later+=archive+[{'source_registrations':registrations}]
    set_refs={(action.get('point',action.get('line',action.get('square'))),action['id'])for e in entries if e['type']=='mapgen'for action in e['object'].get('set',[])if 'id'in action}
    assert all(kind in ('terrain','furniture')for kind,name in set_refs),set_refs
    missing=sorted((required(entries)|set_refs)-own-core)
    report={'status':'research_geometry_staging_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),'world_maps':sum('om_terrain'in e for e in entries),'unique_omt':len(mapped),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'structural_tent_weights_preserved':True,'structural_furniture_retained':['f_LIXA_unfold_barrier'],'inline_mapping_projection':projection,
      'unresolved_typed_refs':missing,'set_reference_audit':sorted(set_refs),'geometry_issues':issues,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'limits':['No native integration or percentage credit','LIXA z=-8 device region is disconnected by design; its access and unfolding require later mechanisms','XEDRA passcode door source and transforms are archived; no science-card substitute','Ruined tent has no source roof; do not invent one','Exact ID checks do not replace comparison to analogous BN sites','Native schema, special terrain and all-floor generation pending']}
    for name,value in [('RESEARCH_SHELLS.json',entries),('RESEARCH_LATER_LAYERS.json',later),('RESEARCH_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text(encoding='utf-8')==text,p
        else:p.write_text(text,encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
