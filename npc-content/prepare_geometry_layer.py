#!/usr/bin/env python3
"""Extract explicit terrain-only shells; preserve deferred source content intact."""
import argparse,copy,hashlib,json,re,unicodedata
from collections import Counter
from pathlib import Path
from prepare_regional_locations import ROOT,expand,index_entries,BUILTIN_IDS,references,flatten
from prepare_container_yards import candidate as yards,required
from adapt_container_yards import support_data
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

OUT=ROOT/'geometry_layer'
PREFIX='dda_geo_'
NAV_FURNITURE=re.compile(r'(ladder|stairs|staircase|ramp|elevator)',re.I)
GEOMETRY_FIELDS={'rows','terrain','fill_ter','mapgensize','rotation','predecessor_mapgen','predecessor_mapgen_rotation','set','place_terrain','place_furniture','parameters','nested','place_nested','palettes','flags','furniture'}
ALIASES={'t_wood_wall_w':'t_wall_w','t_wall_white':'t_wall_w','t_linoleum_white':'t_linoleum_white','t_floor_blue':'t_floor','t_floor_red':'t_floor','t_soil':'t_dirt','t_wall_metal_corrugated':'t_wall_metal_corrugated'}


def raw_sources():
    m=json.loads((ROOT/'island_prison/SOURCE_MANIFEST.json').read_text());result=[]
    for p,digest in m['files'].items():
        raw=(ROOT/'island_prison/upstream'/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
        result+=json.loads(raw)
    palettes={e['id']:e for e in result if e['type']=='palette'}
    shared=shared_sources()
    palettes.update({e['id']:e for p,entries in shared.items() if p.startswith('dda/') and not p.endswith('nested_chunks_roof.json') for e in entries if e['type']=='palette'})
    prison=[]
    for e in result:
        e=copy.deepcopy(e)
        if e['type']=='mapgen' and 'prison_island' in str(e.get('om_terrain','')):
            e['object']=expand(e['object'],palettes);prison.append(e)
        elif e['type']=='overmap_terrain':
            ids=e['id'] if isinstance(e['id'],list) else [e['id']]
            ids=[n for n in ids if n.startswith('prison_island')]
            if ids:e['id']=ids;prison.append(e)
        elif e['type']=='overmap_special' and e['id']=='Island prison':prison.append(e)
    from prepare_rural_churches import sources as church_sources
    f=church_sources();church=[]
    for name,text in f.items():
        if name.startswith('dda/'):
            for e in json.loads(text):
                if e['type']=='palette':palettes[e['id']]=e
    for e in json.loads((ROOT/'rural_churches/XEDRA_SOURCE_MAPS.json').read_text()):
        e=copy.deepcopy(e);e['object']=expand(e['object'],palettes);church.append(e)
    sp=json.loads((ROOT/'rural_churches/XEDRA_SOURCE_SPECIAL.json').read_text())
    church+=sp if isinstance(sp,list) else [sp]
    # Pull authoritative OMT declarations from the already pinned catalog.
    from compare_location_catalog import read_sources
    from prepare_regional_locations import flatten
    names={n for e in church for n in flatten(e.get('om_terrain',[]))}
    for p,text in read_sources()[0].items():
        if not p.startswith('dda/'):continue
        for e in json.loads(text):
            if e.get('type')!='overmap_terrain' or 'id' not in e:continue
            ids=e['id'] if isinstance(e['id'],list) else [e['id']]
            found=[n for n in ids if n in names]
            if found:e=copy.deepcopy(e);e['id']=found;church.append(e)
    yard=[e for e in yards() if e['type']!='mapgen' or 'om_terrain' in e or e.get('nested_mapgen_id') in ('shipping_container','containers_roof')]
    for e in yard:
        if e['type']=='mapgen':e['object']=expand(e['object'],palettes)
    from prepare_community_layers import read_bundle as community_bundle,ROOT as COMMUNITY_ROOT
    bundle=community_bundle(COMMUNITY_ROOT)
    for e in json.loads(bundle['dda/data/json/mapgen_palettes/robofachq.json']):
        palettes[e['id']]=e
    hub=[]
    for e in json.loads(bundle['dda/data/json/mapgen/robofachq_static.json']):
        e=copy.deepcopy(e);e['object']=expand(e['object'],palettes);hub.append(e)
    hub+=json.loads(bundle['dda/data/json/overmap/overmap_terrain/overmap_terrain_robofachq.json'])
    hub.append(next(e for e in json.loads(bundle['dda/data/json/overmap/overmap_special/specials.json']) if e.get('id')=='hub_01'))
    campus=[]
    for path,text in bundle.items():
        if path.startswith('dda/data/json/mapgen_palettes/campus/'):
            for e in json.loads(text):palettes[e['id']]=e
    for path,text in bundle.items():
        if path.startswith('dda/data/json/mapgen/campus/'):
            for e in json.loads(text):
                assert e['type']=='mapgen' and 'om_terrain' in e,path
                e=copy.deepcopy(e);e['object']=expand(e['object'],palettes);campus.append(e)
    campus+=json.loads(bundle['dda/data/json/overmap/overmap_special/campus.json'])
    campus+=json.loads(bundle['dda/data/json/overmap/overmap_terrain/overmap_terrain_campus.json'])
    gd=OUT/'godco_sources'
    manifest=json.loads((gd/'SOURCE_MANIFEST.json').read_text())
    assert manifest['pin']=='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    for path,digest in manifest['files'].items():
        raw=(gd/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
        for e in json.loads(raw):
            if e['type']=='palette':palettes[e['id']]=e
    godco=[]
    for e in json.loads(bundle['dda/data/json/mapgen/godco/church_retreat.json']):
        e=copy.deepcopy(e);e['object']=expand(e['object'],palettes);godco.append(e)
    for path,entries in shared.items():
        if path.startswith('dda/'):
            for e in entries:
                if e.get('nested_mapgen_id')in ('roof_4x4_utility','roof_4x4_utility_1'):godco.append(copy.deepcopy(e))
    own_names={n for e in godco for n in flatten(e.get('om_terrain',[]))}
    catalog,_=read_sources()
    for path,text in catalog.items():
        if not path.startswith('dda/'):continue
        for e in json.loads(text):
            if e.get('type')=='overmap_special' and e.get('id')=='New England Church Retreat':godco.append(copy.deepcopy(e))
            if e.get('type')!='overmap_terrain' or 'id'not in e:continue
            names=e['id'] if isinstance(e['id'],list) else [e['id']]
            selected=[n for n in names if n in own_names]
            if selected:e=copy.deepcopy(e);e['id']=selected;godco.append(e)
    return {'island_prison':prison,'xedra_church':church,'container_yards':yard,'hub_01':hub,'campus':campus,'godco_base':godco}


def glyphs(rows):
    result=[]
    for row in rows:
        for c in row:
            if unicodedata.combining(c):result[-1]+=c
            else:result.append(c)
    return set(result)


def extract(entries,structural_nested=('shipping_container','containers_roof')):
    result=[];deferred=[];issues=[]
    for original in entries:
        e=copy.deepcopy(original);t=e['type']
        if t=='mapgen':
            o=e['object'];out={};later={};used=glyphs(o.get('rows',[]))
            for k,v in o.items():
                if k.startswith('//'):continue
                if k not in GEOMETRY_FIELDS:later[k]=v;continue
                if k in ('rows','fill_ter','mapgensize','rotation','predecessor_mapgen','predecessor_mapgen_rotation','place_terrain'):
                    out[k]=v
                elif k=='terrain':out[k]={c:x for c,x in v.items() if c in used}
                elif k=='parameters':
                    out[k]={n:p for n,p in v.items() if p['type']=='ter_str_id'}
                    later[k]={n:p for n,p in v.items() if p['type']!='ter_str_id'}
                elif k=='furniture':
                    keep={c:x for c,x in v.items() if NAV_FURNITURE.search(str(x)) and c in used}
                    if keep:out[k]=keep
                    later[k]={c:x for c,x in v.items() if c not in keep}
                elif k=='nested':
                    keep={c:x for c,x in v.items() if c in used and any(n in str(x) for n in structural_nested)}
                    if keep:out[k]=keep
                    later[k]={c:x for c,x in v.items() if c not in keep}
                elif k=='place_nested':
                    keep=[x for x in v if any(n in str(x) for n in structural_nested)]
                    if keep:out[k]=keep
                    later[k]=[x for x in v if x not in keep]
                    for x in keep:
                        if x.get('z',0)!=0:issues.append({'type':'nested_vertical_offset_not_supported_by_pinned_BN','source':e.get('nested_mapgen_id',e.get('om_terrain')),'placement':copy.deepcopy(x)})
                elif k=='flags':
                    later[k]=v # Source policy flags are not declared BN mapgen flags.
                elif k=='set':
                    keep=[x for x in v if x.get('point')=='terrain' or x.get('line')=='terrain' or x.get('square')=='terrain']
                    if keep:out[k]=keep
                    later[k]=[x for x in v if x not in keep]
                elif k=='place_furniture':
                    keep=[x for x in v if NAV_FURNITURE.search(str(x))]
                    if keep:out[k]=keep
                    later[k]=[x for x in v if x not in keep]
                elif k=='palettes':
                    v=[x for x in v if x!='parametrized_linoleum_palette']
                    if v:issues.append({'type':'unexpanded_palette','names':v,'source':e.get('om_terrain')})
                    out[k]=v
            # BN diagnoses non-space glyphs even when fill_ter supplies their floor.
            # Make that exact underlying terrain explicit after deferring furniture/loot.
            bound=set(out.get('terrain',{}))|set(out.get('furniture',{}))|set(out.get('nested',{}))
            for c in sorted(used-bound-{' ','.'}):
                if 'fill_ter' in out:
                    out.setdefault('terrain',{})[c]=copy.deepcopy(out['fill_ter'])
                else:
                    assert 'nested_mapgen_id'in e and c in o.get('furniture',{}),('Undefined overlay glyph',c,e.get('nested_mapgen_id'))
                    out.setdefault('furniture',{})[c]='f_null' # Preserve underlying terrain; no furniture in this layer.
            out={k:v for k,v in out.items() if v not in ({},[])}
            assert out.get('rows')==o.get('rows')
            e['object']=out;e['method']='json'
            deferred.append({'source':{k:v for k,v in original.items() if k!='object'},'later_fields':later})
        elif t=='overmap_terrain':
            for k in ('vision_levels','spawns','extras','mondensity'):
                if k in e:deferred.append({'source':e['id'],'field':k,'value':e.pop(k)})
            if isinstance(e.get('see_cost'),str):e['see_cost']={'all_clear':0,'blends_till_outlines':2,'high':5,'medium':2,'low':1,'none':0,'spaced_high':5,'full_high':5}[e['see_cost']]
        elif t=='overmap_special':
            for connection in e.get('connections',[]):
                if 'terrain' in connection:
                    if not connection.get('connection'):
                        assert connection['terrain']=='road',connection
                        connection['connection']='local_road'
                    assert connection.get('connection'),connection
                    deferred.append({'source':e['id'],'connection_point':connection['point'],'field':'deprecated_connection_terrain','value':connection.pop('terrain')})
            for cell in e['overmaps']:
                for k in tuple(cell):
                    if k not in ('point','overmap','locations'):
                        deferred.append({'source':e['id'],'point':cell['point'],'field':k,'value':cell.pop(k)})
            e['flags']=['UNIQUE' if x=='OVERMAP_UNIQUE' else x for x in e.get('flags',[])]
        else:raise AssertionError(t)
        result.append(e)
    def walk(v):
        if isinstance(v,str):return ALIASES.get(v,v)
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):
            if v.get('param')=='linoleum_color':
                assert v.get('fallback')=='t_linoleum_gray',v
                return v['fallback']
            return {k:walk(x) for k,x in v.items()}
        return v
    return walk(result),deferred,issues


def prepare(check=False):
    OUT.mkdir(exist_ok=True);core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods={(r['type'],r['id']) for r in mod_cache()['records']}
    batches={};later={};reports={}
    walls=[e for e in support_data() if e['type']=='terrain']
    for name,original in raw_sources().items():
        structural=('shipping_container','containers_roof','roof_4x4_utility','roof_4x4_utility_1') if name=='godco_base' else ('shipping_container','containers_roof')
        entries,deferred,issues=extract(original,structural)
        support=walls if name=='container_yards' else []
        own=index_entries(entries+support)
        mapped_omt={n for e in entries if e['type']=='mapgen' for n in flatten(e.get('om_terrain',[]))}
        declared_omt={n for t,n in own if t=='overmap_terrain'}
        refs=required(entries)
        missing=refs-core-own
        # Wall definitions intentionally inherit BN metal-wall mechanics.
        for e in support:
            if 'copy-from' in e:assert ('terrain',e['copy-from']) in core|own
        reports[name]={'status':'geometry_candidate_not_native_validated','native_embedded':False,'runtime_validated':False,
                       'declared_omt_without_mapgen':sorted(declared_omt-mapped_omt),'unique_mapped_omt':len(mapped_omt),
                       'constraint_only_cells':sum('overmap' not in c for e in entries if e['type']=='overmap_special' for c in e['overmaps']),
                       'definitions':dict(Counter(e['type'] for e in entries+support)),
                       'special_cells':{e['id']:len(e['overmaps']) for e in entries if e['type']=='overmap_special'},
                       'levels':sorted({c['point'][2] for e in entries if e['type']=='overmap_special' for c in e['overmaps']}),
                       'unresolved_typed_refs':sorted(missing),'geometry_issues':issues,
                       'deferred_records':len(deferred),'rows_preserved':True,'core_overlaps_before_preview_namespacing':sorted((own-BUILTIN_IDS)&core),
                       'bundled_mod_overlaps_before_preview_namespacing':sorted((own-BUILTIN_IDS)&mods)}
        batches[name]=entries+support;later[name]=deferred
    report={'layer':1,'scope':'Terrain, structural nested layouts, typed terrain parameters and navigation-critical furniture only',
            'native_validated':False,'adaptations':{'terrain_aliases':ALIASES,'t_wood_wall_w':'BN t_wall_w, as in the existing ordinary church port','parametrized_linoleum_palette':'Use explicit source fallback t_linoleum_gray; decorative color parameter deferred','see_cost':'Source named visibility levels mapped to pinned BN integer costs','OVERMAP_UNIQUE':'BN UNIQUE flag','content_only_glyphs':'Explicitly repeat source fill_ter for glyphs whose later-layer bindings were deferred','connections':'Retain explicit connection; archive and remove deprecated terrain selector'},'packages':reports,'limits':['Cross-level nested placement is an explicit blocker until adapted; never silently ignore z','Shared BN external OMT cells retain their stock generation','Standalone preview identities and native all-floor testing required before installation','Source late-layer fields and full authenticated inputs are preserved']}
    for file,value in [('SHELLS.json',batches),('LATER_LAYERS.json',later),('REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/file
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    for name,p in reports.items():print(name,p['definitions'],'cells',p['special_cells'],'missing',p['unresolved_typed_refs'],'issues',len(p['geometry_issues']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
