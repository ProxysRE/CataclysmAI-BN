#!/usr/bin/env python3
"""Adapt waterside terrain with stock BN parents; no native integration claim."""
import argparse,copy,hashlib,json
from prepare_waterside_geometry import prepare as stage
from prepare_geometry_layer import ROOT,OUT
from prepare_regional_locations import index_entries,BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE=OUT/'waterside_adaptation_sources'
PINS={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}

def prepare(check=False):
    stage(check=True)
    m=json.loads((SOURCE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'));assert m['pins']==PINS
    files={}
    for path,digest in m['files'].items():
        raw=(SOURCE/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path
        files[path]=raw.decode()
    bn={e['id']:e for path,text in files.items()if path.startswith('bn/')and path.endswith('.json')for e in json.loads(text)if e.get('type')=='terrain'}
    src={e['id']:e for e in json.loads(files['dda/data/json/furniture_and_terrain/special_use/sunken_helicopter_furniture.json'])if e.get('type')=='terrain'}
    aliases={n:'dda_geo_waterside_'+n.removeprefix('t_')for n in src}
    aliases['t_water_hot']='dda_geo_waterside_water_hot'
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    raw=json.loads((OUT/'WATERSIDE_SHELLS.json').read_text(encoding='utf-8'))
    for kind,name in sorted(required(raw)-core):
        if kind!='terrain':continue
        for base in ('t_strconc_wall','t_sconc_wall','t_concrete_wall','t_wall'):
            if name.startswith(base+'_')and ('terrain',base)in core:aliases[name]=base;break
    def rename(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [rename(x)for x in v]
        if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
        return v
    resolved={};deferred=[]
    def concrete(name,trail=()):
        if name in resolved:return copy.deepcopy(resolved[name])
        assert name not in trail,(name,trail)
        if name in bn:return copy.deepcopy(bn[name])
        s=src[name];e=concrete(s['copy-from'],trail+(name,))
        for k,v in s.items():
            if k in ('copy-from','extend','connect_groups','shoot'):continue
            e[k]=copy.deepcopy(v)
        for k,v in s.get('extend',{}).items():
            assert k=='flags'
            e[k]=list(dict.fromkeys(e.get(k,[])+v))
        if 'shoot'in s:deferred.append({'source':name,'field':'shoot','value':s['shoot'],'note':'BN parent window ranged behavior retained; DDA shoot schema not copied'})
        if 'connect_groups'in s:deferred.append({'source':name,'field':'connect_groups','value':s['connect_groups']})
        if name=='t_sunkenhelicopter_quarterpanel_n_middle':
            assert e['bash']['items']==[{'item':'lc_steel_chunk','count':[10,22]}]
            e['bash']['items'][0]['item']='steel_chunk'
        resolved[name]=copy.deepcopy(e)
        return e
    terrain=[rename(concrete(n))for n in src]
    hot=next(e for e in json.loads(files['dda/data/json/furniture_and_terrain/terrain-liquids.json'])if e.get('id')=='t_water_hot')
    water=copy.deepcopy(hot)
    for k in ('liquid_source','connect_groups'):
        deferred.append({'source':'t_water_hot','field':k,'value':water.pop(k)})
    water['id']=aliases['t_water_hot']
    assert water['examine_action']=='water_source'
    behavior=files['bn/src/map/mapbuffer.cpp']
    assert 'terrain_id.obj().examine == &iexamine::water_source'in behavior
    assert 'item::spawn("water", calendar::start_of_cataclysm, item::INFINITE_CHARGES)'in behavior
    assert '"heat_radiation"'in files['bn/src/map/mapdata.cpp']
    assert water['heat_radiation']==1
    terrain.append(water)
    known_flags={f for e in bn.values()for f in e.get('flags',[])}
    for e in terrain:
        assert 'copy-from'not in e and {'symbol','color','move_cost','name','description'}<=e.keys(),e['id']
        for flag in e.get('flags',[]):
            assert flag in known_flags or flag in files['bn/src/map/mapdata.cpp'],(e['id'],flag)
    entries=rename(raw)+terrain
    for e in entries:
        if e['type']=='mapgen'and e['object'].get('predecessor_mapgen')and e['object'].get('rows'):
            # Preserve the untouched predecessor; clear debris only where source
            # geometry paints a terrain tile, as in the verified Godco adapter.
            e['object']['remove_all']={g:{}for g,t in e['object'].get('terrain',{}).items()if t!='t_null'}
    own=index_entries(entries)
    from compare_location_catalog import read_sources
    river=next(e for path,text in read_sources()[0].items()if path=='bn/data/json/overmap/overmap_terrain/overmap_terrain_river.json'for e in json.loads(text)if e.get('id')=='river')
    assert river['copy-from']=='generic_river_bank'and 'NO_ROTATE'in river['delete']['flags']
    generated={('overmap_terrain','river_north')}
    missing=sorted(required(entries)-own-core-generated);assert not missing,missing
    mods={(e['type'],e['id'])for e in mod_cache()['records']}
    assert not (own-BUILTIN_IDS)&(core|mods)
    for e in terrain:
        assert ('terrain',e.get('roof','t_null'))in own|core|BUILTIN_IDS
        for action in ('bash','deconstruct'):
            if action not in e:continue
            assert ('terrain',e[action]['ter_set'])in own|core|BUILTIN_IDS
            for item in e[action].get('items',[]):assert ('item',item['item'])in core,item
    expected={}
    for e in entries:
        if 'om_terrain'not in e:continue
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        for y,row in enumerate(e['object'].get('rows',[])):
            for x,g in enumerate(row):
                t=e['object'].get('terrain',{}).get(g)
                if isinstance(t,str)and(t.startswith('dda_geo_waterside_')or any(k in t for k in ('stairs','ladder'))):
                    rotation=e['object'].get('rotation',0)
                    if isinstance(rotation,list):
                        assert len(e['object']['rows'])==24 and len(row)==24
                        invariant=True
                        for turns in range(rotation[0],rotation[1]+1):
                            px,py=x,y
                            for _ in range(turns):px,py=py,23-px
                            invariant &= e['object'].get('terrain',{}).get(e['object']['rows'][py][px])==t
                        if not invariant:continue
                    else:assert rotation==0
                    expected.setdefault(matrix[y//24][x//24],[]).append({'x':x%24,'y':y%24,'terrain':t})
    report={'status':'waterside_geometry_adapted_not_installed','native_embedded':False,'runtime_validated':False,
      'aliases':aliases,'new_terrain_definitions':len(terrain),'unresolved_typed_refs':missing,'generated_external_omt':['river_north'],
      'navigation':expected,'navigation_points':sum(map(len,expected.values())),'deferred_source_fields':deferred,
      'preserved':['Source map rows, underwater flags and complete stock BN parent fields','BN remove_all clears only terrain-painted predecessor glyphs; untouched lake/forest retained','Firepit trunks retained as structural nested geometry','White linoleum source fallback and same-material BN wall counterparts','Hot-water movement, water flags and heat radiation'],
      'adaptations':['BN steel_chunk replaces DDA lc_steel_chunk with unchanged quantities','Complete BN material parents replace DDA parents; BN bash/ranged behavior applies except explicit source quarterpanel bash','BN wall and water connectivity used; DDA floor connectivity deferred'],
      'scope_policy':'DDA collection temperature and liquid_source are archival only; no temperature mechanism is planned',
      'remaining':['Native schema loading and source/installed all-floor generation','Underwater swimming, breath, destruction and window shooting tests','Player stair and cottage access traversal'],
      'limits':['No native patch changes or completion credit','Source water temperature is intentionally excluded by user decision; stock BN water collection applies']}
    for name,value in [('WATERSIDE_ADAPTED_SHELL.json',entries),('WATERSIDE_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text(encoding='utf-8')==text,p
        else:p.write_text(text,encoding='utf-8')
    print('Waterside terrain dependencies closed; native geometry acceptance pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
