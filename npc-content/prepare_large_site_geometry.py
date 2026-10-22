#!/usr/bin/env python3
"""Preserve oil-platform, football-stadium and skyscraper structural geometry."""
import argparse,copy,hashlib,json
from collections import Counter
from prepare_geometry_layer import ROOT,OUT,extract,glyphs
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS,references
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE=OUT/'large_sites_sources'
TARGETS={'oil_platform','stadium_football','office_skyscraper'}
PIN='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'


def prepare(check=False):
    manifest=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['dda_commit']==PIN
    assert manifest['bn_commit']=='c621aaf42fa182473aad10feea2b55647704dcf1'
    files={}
    for path,digest in manifest['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=json.loads(raw)
    shared=shared_sources()
    domestic=OUT/'urban_sources'
    dm=json.loads((domestic/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert dm['dda_commit']==PIN
    path='data/json/mapgen_palettes/house_general_palette.json';raw=(domestic/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==dm['files'][path]
    shared['dda/'+path]=json.loads(raw)
    palettes={e['id']:e for path,es in shared.items() if path.startswith('dda/') for e in es if e.get('type')=='palette'}
    palettes.update({e['id']:e for es in files.values() for e in es if e.get('type')=='palette'})
    original=[];projection=[];overlay=[]
    for path,es in files.items():
        for source in es:
            if source.get('type')!='mapgen':continue
            if path.endswith(('aux_nested.json','shelter_nested.json')):continue
            e=copy.deepcopy(source);obj=e['object']=expand(e['object'],palettes)
            assert not obj.get('palettes'),(path,obj.get('palettes'))
            for g,piece in obj.get('mapping',{}).items():
                for key in ('terrain','furniture'):
                    if key not in piece:continue
                    assert g not in obj.get(key,{})or obj[key][g]==piece[key]
                    obj.setdefault(key,{})[g]=copy.deepcopy(piece[key])
                    projection.append({'source':e.get('om_terrain',e.get('nested_mapgen_id')),'glyph':g,'field':key})
            if 'fill_ter'not in obj:
                for g in sorted(glyphs(obj.get('rows',[]))-set(obj.get('terrain',{}))-set(obj.get('furniture',{}))-set(obj.get('nested',{}))-{' ','.'}):
                    assert 'nested_mapgen_id'in e or 'predecessor_mapgen'in obj,(path,g)
                    obj.setdefault('furniture',{})[g]='f_null'
                    overlay.append({'source':e.get('om_terrain',e.get('nested_mapgen_id')),'glyph':g})
            original.append(e)
    # Nested rooms contain walls and access paths, not only furnishings. Keep
    # their entire structural graph, including all source weighted alternatives.
    nested={e['nested_mapgen_id']for e in original if 'nested_mapgen_id'in e}
    shared_nested=[e for p,es in shared.items()if p.startswith('dda/')for e in es if 'nested_mapgen_id'in e]
    house=OUT/'waterside_adaptation_sources'
    hm=json.loads((house/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert hm['pins']['dda']==PIN
    path='dda/data/json/mapgen/nested/house_nested.json';raw=(house/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==hm['files'][path]
    shared_nested += [e for e in json.loads(raw)if 'nested_mapgen_id'in e]
    shared_nested += [e for path,es in files.items()if path.endswith(('aux_nested.json','shelter_nested.json'))for e in es if 'nested_mapgen_id'in e]
    while True:
        for e in original:e['object']=expand(e['object'],palettes)
        wanted={n for e in original if e['type']=='mapgen'for t,n in references(e['object'])if t=='nested_mapgen'}-nested-{'null'}
        additions=[copy.deepcopy(e)for e in shared_nested if e['nested_mapgen_id']in wanted]
        if not additions:break
        original+=additions;nested|={e['nested_mapgen_id']for e in additions}
    for e in original:
        obj=e['object']=expand(e['object'],palettes)
        assert not obj.get('palettes'),e.get('nested_mapgen_id')
        if 'fill_ter'not in obj:
            for g in sorted(glyphs(obj.get('rows',[]))-set(obj.get('terrain',{}))-set(obj.get('furniture',{}))-set(obj.get('nested',{}))-{' ','.'}):
                assert 'nested_mapgen_id'in e or 'predecessor_mapgen'in obj,g
                obj.setdefault('furniture',{})[g]='f_null'
                overlay.append({'source':e.get('om_terrain',e.get('nested_mapgen_id')),'glyph':g})
    mapped={n for e in original for n in flatten(e.get('om_terrain',[]))}
    registrations={}
    for path,text in read_sources()[0].items():
        if not path.startswith('dda/'):continue
        for source in json.loads(text):
            if source.get('type')in ('overmap_special','city_building')and source.get('id')in TARGETS:
                registrations[source['id']]=copy.deepcopy(source)
                e=copy.deepcopy(source);e['type']='overmap_special';original.append(e)
            elif source.get('type')=='overmap_terrain':
                names=set(flatten(source.get('id',[])))&mapped
                if names:e=copy.deepcopy(source);e['id']=sorted(names);original.append(e)
    assert set(registrations)==TARGETS
    entries,later,issues=extract(original,tuple(sorted(nested)))
    aliases={n:'dda_geo_large_'+n for n in nested}
    def rename(value):
        if isinstance(value,str):return aliases.get(value,value)
        if isinstance(value,list):return [rename(x)for x in value]
        if isinstance(value,dict):return {k:rename(v)for k,v in value.items()}
        return value
    entries=rename(entries)
    for e in entries:
        if e['type']=='overmap_special':
            later.append({'source_registration':registrations[e['id']]})
            e['occurrences']=[0,0]
            if 'priority'in e:later.append({'source':e['id'],'field':'priority','value':e.pop('priority')})
        elif e['type']=='overmap_terrain'and 'travel_cost_type'in e:
            later.append({'source':e['id'],'field':'travel_cost_type','value':e.pop('travel_cost_type')})
    declared={n for e in entries if e['type']=='overmap_terrain'for n in flatten(e['id'])}
    assert declared==mapped,(mapped-declared,declared-mapped)
    for a,b in zip(original,entries):
        if a['type']!='mapgen':continue
        assert a['object'].get('rows')==b['object'].get('rows')
        assert a['object'].get('mapgensize')==b['object'].get('mapgensize')
        expected={g:v for g,v in a['object'].get('nested',{}).items() if g in glyphs(a['object'].get('rows',[]))}
        assert rename(expected)==dict(b['object'].get('nested',{})),(a.get('om_terrain',a.get('nested_mapgen_id')),expected,b['object'].get('nested',{}))
        obj=b['object'];rows=obj.get('rows')
        if rows and 'om_terrain'in b:
            omt=b['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
            assert len(rows)==24*len(matrix)and all(len(r)==24*len(matrix[0])for r in rows),b['om_terrain']
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(e['type'],e['id'])for e in mod_cache()['records']};own=index_entries(entries)
    missing=sorted(required(entries)-own-core)
    report={'status':'large_sites_geometry_staged_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),
      'world_maps':sum('om_terrain'in e for e in entries),'unique_omt':len(mapped),
      'nested_mapgen_definitions':sum('nested_mapgen_id'in e for e in entries),'nested_identities':len(nested),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_z_levels':{e['id']:sorted({c['point'][2]for c in e['overmaps']})for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'structural_nested_preserved':sorted(nested),
      'inline_mapping_projection':projection,'neutral_overlay_glyphs':overlay,
      'unresolved_typed_refs':missing,'geometry_issues':issues,
      'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'limits':['No native integration or completion credit','All original source, weighted nested alternatives and later-layer content retained','Oil-platform deep-water access and skyscraper elevators require traversal verification','Stadium and skyscraper city registrations archived; no replacement of BN city generation']}
    for name,value in [('LARGE_SITES_SHELLS.json',entries),('LARGE_SITES_LATER_LAYERS.json',later),('LARGE_SITES_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';path=OUT/name
        if check:assert path.read_text(encoding='utf-8')==text,path
        else:path.write_text(text,encoding='utf-8')
    print(json.dumps({k:report[k]for k in ('status','world_maps','unique_omt','nested_mapgen_definitions','special_cells','unresolved_typed_refs','geometry_issues')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
