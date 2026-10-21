#!/usr/bin/env python3
"""Reject incomplete preview terrain before native compilation, including the panel regression."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REQUIRED={'symbol','color','move_cost','name','description'}

def validate(e):
    assert e['type']=='terrain'
    assert 'copy-from'not in e,('Preview terrain must be concrete',e['id'])
    assert REQUIRED<=e.keys(),(e['id'],sorted(REQUIRED-e.keys()))


def check():
    entries=json.loads((ROOT/'native/dda_geometry_preview.json').read_text())
    terrain=[e for e in entries if e['type']=='terrain']
    assert len(terrain)==7
    for e in terrain:validate(e)
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
    print('PASS: seven concrete preview terrain definitions; panel physical data preserved; old copy-from and missing-symbol forms rejected')

if __name__=='__main__':check()
