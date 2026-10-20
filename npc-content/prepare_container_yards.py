#!/usr/bin/env python3
"""Prepare both complete inland container yards and their entire cargo graph."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from prepare_regional_locations import ROOT, expand, references, index_entries, BUILTIN_IDS
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache, added_core_declarations

FOLDER=ROOT/'container_yards'
SPECIALS={'o_container_yard_inland','o_container_yard_inland_bandit'}


def sources():
    m=json.loads((FOLDER/'SOURCE_MANIFEST.json').read_text())
    assert m['dda_pin']=='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert m['bn_pin']=='c621aaf42fa182473aad10feea2b55647704dcf1'
    files={}
    for name,record in m['files'].items():
        raw=(FOLDER/'upstream'/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==record['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['git_blob_sha']
        files[name]=json.loads(raw)
    assert len(files)==3
    return files


def candidate():
    files=sources()
    original=sum(files.values(),[])
    palettes={e['id']:e for e in original if e['type']=='palette'}
    result=[]
    for e in original:
        if e['type']=='palette':continue
        e=copy.deepcopy(e)
        assert e['type']=='mapgen'
        e['method']='json'
        e['object']=expand(e['object'],palettes)
        result.append(e)
    catalog=read_sources()[0]
    entries=[e for name,text in catalog.items() if name.startswith('dda/') for e in json.loads(text)]
    result += [copy.deepcopy(e) for e in entries if e.get('type')=='overmap_terrain' and any(n.startswith('container_yard_inland') for n in (e.get('id') if isinstance(e.get('id'),list) else [e.get('id','')]))]
    selected=[copy.deepcopy(e) for e in entries if e.get('type')=='overmap_special' and e.get('id') in SPECIALS]
    assert {e['id'] for e in selected}==SPECIALS
    result += selected
    return result


def required(entries):
    result=set()
    own=index_entries(entries)
    def collect(kind,value):
        if isinstance(value,str):result.add((kind,value))
        elif isinstance(value,list):
            for v in value:collect(kind,v[0] if isinstance(v,list) and len(v)==2 and isinstance(v[1],int) else v)
        elif isinstance(value,dict):
            for key in ('default','distribution','fallback'):
                if key in value:collect(kind,value[key])
    for e in entries:
        if e['type']=='mapgen':
            obj=e['object'];result.update(references(obj))
            for param in obj.get('parameters',{}).values():
                kind={'ter_str_id':'terrain','furn_str_id':'furniture','nested_mapgen_id':'nested_mapgen'}.get(param['type'])
                assert kind,param
                collect(kind,param.get('default'))
            for p in obj.get('place_npcs',[]):collect('npc',p['class'])
            for p in obj.get('npcs',{}).values():collect('npc',p['class'])
            for p in obj.get('faction_owner',[]):collect('faction',p['id'])
            for flag in obj.get('flags',[]):collect('json_flag',flag)
            for p in obj.get('place_loot',[]):
                if 'item' in p:collect('item',p['item'])
                if 'group' in p:collect('item_group',p['group'])
            for p in obj.get('liquids',{}).values():collect('item',p['liquid'])
        elif e['type']=='overmap_terrain' and e.get('copy-from'):
            result.add(('overmap_terrain_abstract',e['copy-from']))
        elif e['type']=='overmap_special':
            for cell in e['overmaps']:
                if 'overmap' not in cell:continue # Placement constraints have no terrain ID.
                name=cell['overmap']
                # Rotatable OMT declarations generate all four directional IDs.
                # Strip only a direction whose base is actually declared here.
                for suffix in ('_north','_east','_south','_west'):
                    if name.endswith(suffix) and ('overmap_terrain',name[:-len(suffix)]) in own:
                        name=name[:-len(suffix)];break
                result.add(('overmap_terrain',name))
    return result-BUILTIN_IDS-{('nested_mapgen','null')}


def prepare(check=False):
    payload=candidate()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    local=index_entries(payload)-BUILTIN_IDS
    mods={(r['type'],r['id']) for r in mod_cache()['records']}
    port=added_core_declarations((ROOT/'artisan_engine.patch').read_text())
    missing=required(payload)-core-port-local
    originals=sum(sources().values(),[])
    source_maps=[e for e in originals if e['type']=='mapgen']
    maps=[e for e in payload if e['type']=='mapgen']
    assert len(source_maps)==len(maps)
    for a,b in zip(source_maps,maps):
        for field in ('rows','place_npcs','place_vehicles','place_monster','place_monsters','mapgensize'):
            assert a['object'].get(field)==b['object'].get(field),field
        for field in ('om_terrain','nested_mapgen_id'):
            assert a.get(field)==b.get(field),field
    geometries=[]
    for e in payload:
        if e['type']=='overmap_special':
            cells=e['overmaps'];assert len({tuple(c['point']) for c in cells})==len(cells)
            geometries.append({'id':e['id'],'placed_cells':len(cells),'levels':sorted({c['point'][2] for c in cells})})
    names=sorted({e['nested_mapgen_id'] for e in maps if 'nested_mapgen_id' in e})
    cargo_palette=next(e for es in sources().values() for e in es if e['type']=='palette')
    cargo=cargo_palette['parameters']['contents_nest']['default']['distribution']
    assert len(names)==121 and len(maps)==155
    assert not {n for n,w in cargo if n!='null'}-set(names), 'Cargo branch lost'
    report={'status':'complete_source_graph_and_palette_expansion_staged_not_installed','native_embedded':False,'runtime_validated':False,
            'source_files':list(sources()),'definitions':dict(Counter(e['type'] for e in payload)),
            'specials':geometries,'nested_layouts':names,'nested_layout_count':len(names),'cargo_choice_count':len(cargo),
            'cargo_weights_preserved':True,'palette_parameter_scope_preserved':'nest',
            'source_rows_and_npc_vehicle_placements_preserved':True,'core_id_overlaps':sorted(local&core),'bundled_mod_id_overlaps':sorted(local&mods),
            'provided_by_existing_core_port':sorted(required(payload)&port),'reference_scope':'Explicit mapgen references plus typed parameter defaults, NPC templates, liquid/item placements and overmap identities; not a complete engine/schema validation',
            'unresolved_typed_references':sorted(missing),'unresolved_count':len(missing),
            'remaining':['Review nested-mapgen parameters, per-container selection scope and shipping-container wall colors against BN',
                         'Close every missing dependency with reviewed BN reuse or an actual source port; no dropped cargo outcomes',
                         'Translate DDA packaging/charges and banknotes to stock BN money without multiplying value by bulk repeat counts',
                         'Review source furniture-array schemas, bandit roles, generators and appliances',
                         'Native loading, complete generation, natural placement and manual traversal'],
            'limits':'This is a preserved/adapted staging layer, not playable BN content. ID matches do not establish semantic parity.'}
    for path,data in {FOLDER/'STAGED_LOCATIONS.json':payload,FOLDER/'TRANSFER_REPORT.json':report}.items():
        text=json.dumps(data,indent=2,ensure_ascii=True)+'\n'
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('PASS: both whole container yards and cargo graph staged:',report['definitions'],'nested layouts=',len(names),'unresolved=',len(missing))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
