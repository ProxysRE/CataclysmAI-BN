#!/usr/bin/env python3
"""Adapt the whole Grey Moose lodge community using existing BN systems."""
import argparse
import base64
import collections
import copy
import gzip
import hashlib
import json
from pathlib import Path
from adapt_dialogue import adapt
from prepare_regional_locations import expand, references, index_entries, BUILTIN_IDS
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/'militia'
# NPC construction reads enchantment values/options; match the stock NPC load phase.
PAYLOAD='data/json/npcs/dda_grey_moose_lodge.json'
ITEM_ALIASES={'case_cigar':'box_small','goggles_chem':'glasses_safety','sneakers_steel':'boots_steel'}
GROUP_ALIASES={'tools_toolbox':'tools_common','cigar_box_unopened':'cigar_box_opened'}


def selected():
    folder=ROOT/'layers'
    manifest=json.loads((folder/'SOURCE_MANIFEST.json').read_text())
    assert manifest['DDA_commit']=='c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    raw=gzip.decompress(base64.b64decode((folder/'SOURCE_BUNDLE.json.gz.base64').read_text()))
    assert hashlib.sha256(raw).hexdigest()==manifest['bundle_sha256']
    files=json.loads(raw)
    result=[]
    selected_files={}
    for path,text in files.items():
        if not path.startswith('dda/'):continue
        if not ('/militia/' in path or path.endswith('overmap_terrain_militia.json') or
                path.endswith('/npcs/factions.json') or path.endswith('/overmap_special/specials.json')):continue
        data=text.encode()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==manifest['files'][path]['git_blob_sha']
        entries=json.loads(text)
        if path.endswith('/npcs/factions.json'):
            entries=[e for e in entries if e.get('id')=='GM_militia_faction']
        if path.endswith('/overmap_special/specials.json'):
            entries=[e for e in entries if e.get('id')=='Militia Lodge']
        assert entries,path
        selected_files[path]={'blob_sha':manifest['files'][path]['git_blob_sha'],'definitions':len(entries)}
        result+=entries
    assert len(selected_files)==7
    return result,selected_files


def adapt_stock(value):
    if isinstance(value,list):
        if len(value)==2 and isinstance(value[0],str) and isinstance(value[1],int):
            return [ITEM_ALIASES.get(value[0],value[0]),value[1]]
        return [adapt_stock(v) for v in value]
    if not isinstance(value,dict):return value
    out={k:adapt_stock(v) for k,v in value.items()}
    if 'variant' in out:
        # BN has the same protective garment, without DDA's cosmetic variants.
        assert out.get('item') == 'balclava' and out['variant'] == 'black'
        out.pop('variant')
    if isinstance(out.get('item'),str):out['item']=ITEM_ALIASES.get(out['item'],out['item'])
    if isinstance(out.get('group'),str):out['group']=GROUP_ALIASES.get(out['group'],out['group'])
    return out


def native_data():
    entries,_=selected()
    palettes={e['id']:e for e in entries if e['type']=='palette'}
    result=[]
    for original in entries:
        if original['type']=='palette':continue
        e=adapt(copy.deepcopy(original),collections.Counter())
        if e['type']=='mapgen':
            e['object']=expand(e['object'],palettes)
            e['method']='json'
        elif e['type']=='overmap_terrain':
            e.pop('vision_levels',None)
            assert e['see_cost']=='high'
            e['see_cost']=5
        elif e['type']=='overmap_special':
            e.pop('priority',None)
            for c in e.get('connections',[]):
                assert c.pop('terrain')=='forest_trail'
                assert c['connection']=='forest_trail'
            assert 'GLOBALLY_UNIQUE' in e['flags']
        result.append(adapt_stock(e))
    return result


def required(payload):
    from prepare_community_layers import typed_references
    result=set()
    for e in payload:
        result.update((k,n) for k,n,_ in typed_references(e))
        if e['type']=='mapgen':
            result.update(references(e['object']))
            result.update(('faction',o['id']) for o in e['object'].get('faction_owner',[]))
        if e['type']=='item_group':result.update(references({'items':{'_':{'item':e}}}))
        if e['type']=='npc_class':
            for k in ('carry_override','worn_override','weapon_override','shopkeeper_item_group'):
                if isinstance(e.get(k),str):result.add(('item_group',e[k]))
            for t in e.get('traits',[]):
                for k,kind in (('trait','mutation'),('group','trait_group')):
                    if k in t:result.add((kind,t[k]))
            for s in e.get('skills',[]):
                if s['skill']!='ALL':result.add(('skill',s['skill']))
        if e['type']=='faction':result.update(('faction',f) for f in e.get('relations',{}))
    # Concrete rotation peers are generated from the declared terrain type.
    result={(k,n[:-6] if k=='overmap_terrain' and n.endswith('_north') else n) for k,n in result}
    return result


def prepare(check=False):
    payload=native_data()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    from prepare_eldercare_loot import native_data as loot
    provided=core|index_entries(payload+loot())
    missing=required(payload)-provided
    assert not missing,sorted(missing)
    declared=index_entries(payload)-BUILTIN_IDS
    assert not declared&core,sorted(declared&core)
    mods=mod_cache()
    collisions=declared&{(r['type'],r['id']) for r in mods['records']}
    assert not collisions,sorted(collisions)
    report={'source_files':selected()[1],'installed':False,'native_payload_prepared':True,'native_runtime_validated':False,
            'definitions':dict(collections.Counter(e['type'] for e in payload)),
            'unresolved_typed_refs':sorted(missing),'core_or_bundled_mod_collisions':sorted(collisions),
            'item_aliases':ITEM_ALIASES,'group_aliases':GROUP_ALIASES,
            'cosmetic_counterparts':{'balclava:black':'stock BN balclava; source probability retained; no DDA cosmetic variant selector'},
            'semantic_review':'Bundled Civilians NC_PROF_MILITIA is a generic class/profession, not these named community NPC templates, faction, dialogue or lodge.',
            'remaining':['Native initialization, NPC interaction/trading and full map generation','Natural placement and save/reload','GMLODGE Civilians exclusion included atomically; mod-enabled native generation validation pending']}
    outputs={ROOT/'native/dda_grey_moose_lodge.json':payload,FOLDER/'ADAPTATION_REPORT.json':report}
    for path,data in outputs.items():
        text=json.dumps(data,indent=2,ensure_ascii=True)+'\n'
        if check:assert path.read_text()==text,path
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    print('PASS: Grey Moose community, source-preserved NPC/dialogue/map identities; closed typed dependency audit; native runtime pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true')
    prepare(p.parse_args().check)
