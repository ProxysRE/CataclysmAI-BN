#!/usr/bin/env python3
"""Reject incomplete preview terrain before native compilation, including the panel regression."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REQUIRED={'symbol','color','move_cost','name','description'}

def validate(e):
    assert e['type']=='terrain'
    assert 'copy-from'not in e,('Preview terrain must be concrete',e['id'])
    assert REQUIRED<=e.keys(),(e['id'],sorted(REQUIRED-e.keys()))
    for action in ('bash','deconstruct'):
        piece=e.get(action,{})
        for key in ('ter_set','ter_set_bashed_from_above'):
            assert piece.get(key)!='t_open_air',('BN requires implicit open-air result',e['id'],action,key)
        for key in ('sound_vol','sound_fail_vol'):
            if key in piece:assert isinstance(piece[key],str),('Legacy BN sound volume',e['id'],action,key)


def validate_omt(e,known):
    flags=list(e.get('flags',[]))
    for field in ('extend','delete'):flags+=e.get(field,{}).get('flags',[])
    assert set(flags)<=known,('Unsupported BN overmap flags',e.get('id'),sorted(set(flags)-known))


def validate_no_random_extras(entries):
    for e in entries:
        if e['type']=='overmap_terrain':
            assert e.get('extras')=='',('Preview can inherit random map extras',e.get('id'),e.get('copy-from'))


def roof_sources():
    result={}
    for folder,name,pin_key in (
        ('research_roof_sources','bn/data/json/furniture_and_terrain/terrain-roofs.json','bn_commit'),
        ('urban_adaptation_sources','bn/data/json/furniture_and_terrain/terrain-floors-outdoors.json',None)):
        root=ROOT/'geometry_layer'/folder
        manifest=json.loads((root/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        pin=manifest[pin_key] if pin_key else manifest['pins']['bn']
        assert pin=='c621aaf42fa182473aad10feea2b55647704dcf1'
        raw=(root/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['files'][name]
        result.update({e['id']:e for e in json.loads(raw)if e.get('type')=='terrain'})
    return result


def validate_roofs(entries,stock):
    definitions=dict(stock)
    definitions.update({e['id']:e for e in entries if e['type']=='terrain'})
    for e in entries:
        if e['type']!='terrain'or not e.get('roof'):continue
        roof=definitions.get(e['roof'])
        assert roof is not None,('Missing authenticated roof definition',e['id'],e['roof'])
        assert not roof.get('roof'),('Roof has another roof',e['id'],e['roof'])
        assert roof.get('bash',{}).get('bash_below',False),('Roof cannot be bashed from below',e['id'],e['roof'])


def validate_locations(entries,stock):
    from compare_location_catalog import read_sources
    from prepare_regional_locations import index_entries
    definitions=[e for e in entries if e['type']=='overmap_location']
    known={e['id'] for e in stock+definitions}
    core=index_entries([e for path,text in read_sources()[0].items()
                        if path.startswith('bn/') for e in json.loads(text)])
    for e in definitions:
        assert e['terrains'],e
        assert all(('overmap_terrain',n) in core for n in e['terrains']),e
    for e in entries:
        if e['type']!='overmap_special':continue
        for cell in [e]+e['overmaps']:
            missing=set(cell.get('locations',[]))-known
            assert not missing,('Unsupported BN placement locations',e['id'],cell.get('point'),sorted(missing))


def check():
    entries=json.loads((ROOT/'native/dda_geometry_preview.json').read_text())
    terrain=[e for e in entries if e['type']=='terrain']
    assert len(terrain)==47
    for e in terrain:validate(e)
    validate_no_random_extras(entries)
    # Missing overrides inherit extras=build through BN's generic city parent.
    from compare_location_catalog import read_sources
    stock={e['abstract']:e for path,text in read_sources()[0].items() if path.startswith('bn/')
           for e in json.loads(text) if 'abstract'in e}
    parent=stock['generic_city_building']['copy-from']
    assert stock[parent]['extras']=='build'
    for probe in ({'type':'overmap_terrain','id':'regression_extras','copy-from':'generic_city_building'},
                  {'type':'overmap_terrain','id':'regression_extras','extras':'build'}):
        try:validate_no_random_extras([probe])
        except AssertionError:pass
        else:raise AssertionError('Random extras inheritance regression accepted')
    validate_no_random_extras([{'type':'overmap_terrain','id':'regression_extras','extras':''}])
    template={'type':'terrain','id':'regression_open_air','symbol':'x','color':'white',
              'move_cost':2,'name':'probe','description':'probe'}
    for action,key,value in [('bash','ter_set','t_open_air'),('bash','ter_set_bashed_from_above','t_open_air'),
                             ('deconstruct','ter_set','t_open_air'),('bash','sound_vol',16)]:
        probe=dict(template);probe[action]={key:value}
        try:validate(probe)
        except AssertionError:pass
        else:raise AssertionError('Invalid destruction/sound regression accepted')
    stock_roofs=roof_sources()
    validate_roofs(entries,stock_roofs)
    for bad_roof in ('t_strconc_floor_no_roof','recursive_roof'):
        probe={'type':'terrain','id':'regression_roof_user','roof':bad_roof}
        stock=dict(stock_roofs)
        stock['recursive_roof']={'roof':'t_flat_roof','bash':{'bash_below':True}}
        try:validate_roofs([probe],stock)
        except AssertionError:pass
        else:raise AssertionError('Invalid automatic roof accepted: '+bad_roof)
    archive=ROOT/'geometry_layer/waterside_adaptation_sources'
    manifest=json.loads((archive/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    name='bn/src/overmap/overmap.h';raw=(archive/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==manifest['files'][name]
    block=raw.decode('utf-8').split('oter_flags_map = {',1)[1].split('};',1)[0]
    known=set(re.findall(r'\{"([A-Z_]+)", oter_flags::',block))
    assert 'LAKE'in known and 'WATER'not in known
    for e in entries:
        if e['type']=='overmap_terrain':validate_omt(e,known)
    name='bn/data/json/overmap/special_locations.json';raw=(archive/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==manifest['files'][name]
    stock=json.loads(raw)
    validate_locations(entries,stock)
    for point in (None,[0,0,1]):
        probe={'type':'overmap_special','id':'regression_air','overmaps':[]}
        if point is None:probe['locations']=['open_air']
        else:probe['overmaps']=[{'point':point,'locations':['open_air']}]
        try:validate_locations([probe],stock)
        except AssertionError:pass
        else:raise AssertionError('Unknown placement location accepted')
    try:validate_omt({'id':'regression_water','flags':['WATER']},known)
    except AssertionError:pass
    else:raise AssertionError('Unsupported WATER overmap flag accepted')
    bn=json.loads((ROOT/'geometry_layer/frontier_adaptation_sources/bn/data/json/furniture_and_terrain/terrain-mechanisms.json').read_text())
    by_id={e['id']:e for e in bn}
    for name,parent in [('dda_geo_frontier_artisan_reader','t_card_science'),('dda_geo_frontier_balthazar_intercom','t_intercom')]:
        panel=next(e for e in terrain if e['id']==name)
        # All physical fields, flags, roof and bash must survive concretization.
        overridden={'id','name','description','examine_action'}
        assert {k:v for k,v in panel.items()if k not in overridden}=={k:v for k,v in by_id[parent].items()if k not in overridden}
        assert panel['examine_action']=='none'
        broken={k:panel[k]for k in ('type','id','name','description','examine_action')}
        broken['copy-from']=parent
        for probe in (broken,{k:v for k,v in panel.items()if k!='symbol'}):
            try:validate(probe)
            except AssertionError:pass
            else:raise AssertionError('Incomplete terrain regression accepted')
    print('PASS: concrete terrain/roof rules, BN overmap flags and placement locations; random extras explicitly disabled; inheritance, destruction, sound and panel regressions rejected')

if __name__=='__main__':check()
