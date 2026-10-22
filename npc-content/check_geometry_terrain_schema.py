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


def validate_omt(e,known):
    flags=list(e.get('flags',[]))
    for field in ('extend','delete'):flags+=e.get(field,{}).get('flags',[])
    assert set(flags)<=known,('Unsupported BN overmap flags',e.get('id'),sorted(set(flags)-known))


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
    assert len(terrain)==43
    for e in terrain:validate(e)
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
    print('PASS: concrete preview terrains, pinned BN overmap flags and placement locations; unsupported WATER/open_air and incomplete panels rejected')

if __name__=='__main__':check()
