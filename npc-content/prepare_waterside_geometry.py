#!/usr/bin/env python3
"""Stage three waterside locations; retain unadapted terrain obligations explicitly."""
import argparse,copy,hashlib,json
from collections import Counter
from prepare_geometry_layer import ROOT,OUT,extract,glyphs
from prepare_regional_locations import expand,flatten,index_entries,BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE=OUT/'waterside_sources'
TARGETS={'Hot Springs','Pottery Cottage','sunken_helicopter'}
MAPS={'hot_springs','pottery_cottage_field','pottery_cottage','pottery_cottage_field_2nd','pottery_cottage_2nd','pottery_cottage_field_roof','pottery_cottage_roof','pottery_cottage_basement','sunken_helicopter','sunken_heli_roof','nether_cucumber_lake_bed'}

def prepare(check=False):
    palettes={e['id']:e for p,es in shared_sources().items()if p.startswith('dda/')for e in es if e.get('type')=='palette'}
    for directory in (SOURCE,OUT/'urban_sources'):
        m=json.loads((directory/'SOURCE_MANIFEST.json').read_text())
        assert m['dda_commit']=='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
        for path,digest in m['files'].items():
            raw=(directory/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
            for e in json.loads(raw):
                if e.get('type')=='palette':palettes[e['id']]=e
    original=[];neutral=[]
    for path in json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text())['files']:
        for e in json.loads((SOURCE/path).read_text()):
            if e.get('type')!='mapgen' or not set(flatten(e.get('om_terrain',[])))&MAPS:continue
            e=copy.deepcopy(e);o=e['object']=expand(e['object'],palettes)
            assert not o.get('palettes'),o.get('palettes')
            # Item-only glyphs on predecessor maps must preserve the underlying terrain.
            if 'fill_ter'not in o:
                for g in sorted(glyphs(o.get('rows',[]))-set(o.get('terrain',{}))-set(o.get('furniture',{}))-set(o.get('nested',{}))-{' ','.'}):
                    o.setdefault('furniture',{})[g]='f_null';neutral.append({'map':e['om_terrain'],'glyph':g})
            original.append(e)
    mapped={n for e in original for n in flatten(e['om_terrain'])}
    assert mapped==MAPS,(mapped^MAPS)
    registrations=[]
    for path,text in read_sources()[0].items():
        if not path.startswith('dda/'):continue
        for e in json.loads(text):
            if e.get('type')=='overmap_special'and e.get('id')in TARGETS:
                registrations.append(copy.deepcopy(e));original.append(copy.deepcopy(e))
            elif e.get('type')=='overmap_terrain':
                names=set(flatten(e.get('id',[])))&mapped
                if names:e=copy.deepcopy(e);e['id']=sorted(names);original.append(e)
    assert {e['id']for e in registrations}==TARGETS
    entries,later,issues=extract(original,())
    for a,b in zip(original,entries):
        if a['type']=='mapgen':assert a['object'].get('rows')==b['object'].get('rows')
    for e in entries:
        if e['type']=='overmap_special':e['occurrences']=[0,0]
        if e['type']=='overmap_terrain'and 'travel_cost_type'in e:later.append({'source':e['id'],'field':'travel_cost_type','value':e.pop('travel_cost_type')})
    later.append({'source_registrations':registrations})
    for e in entries:
        if e['type']!='mapgen':continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        if 'rows'not in e['object']:continue
        rows=e['object']['rows'];assert len(rows)==24*len(matrix)and all(len(row)==24*len(matrix[0])for row in rows)
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(e['type'],e['id'])for e in mod_cache()['records']};own=index_entries(entries)
    report={'status':'waterside_geometry_staging_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),'unique_omt':len(mapped),
      'special_cells':{e['id']:sum('overmap'in c for c in e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_rows_preserved':True,'deferred_nested_requires_geometry_review':['firepit_5x5_2'],'neutral_predecessor_glyphs':neutral,'unresolved_typed_refs':sorted(required(entries)-own-core),
      'geometry_issues':issues,'core_id_overlaps':sorted((own-BUILTIN_IDS)&core),'bundled_mod_id_overlaps':sorted((own-BUILTIN_IDS)&mods),
      'limits':['No native integration or completion credit','Thermal-water behavior and helicopter materials require BN comparison','Source registrations and later content retained separately','Shared domestic palette definitions authenticated through urban_sources manifest']}
    for name,value in [('WATERSIDE_SHELLS.json',entries),('WATERSIDE_LATER_LAYERS.json',later),('WATERSIDE_GEOMETRY_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
