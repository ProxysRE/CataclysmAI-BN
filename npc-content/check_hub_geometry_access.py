#!/usr/bin/env python3
"""Project navigation terrain for source-derived native geometry expectations."""
import argparse,json
from prepare_geometry_layer import ROOT,OUT
from prepare_hub_geometry import prepare as prepare_hub
from prepare_community_layers import read_bundle,ROOT as COMMUNITY_ROOT
from audit_hub_access import project,review,matrix,terrain_base


def analyze():
    es=json.loads((OUT/'HUB_ADAPTED_SHELL.json').read_text())
    special=next(e for e in es if e['type']=='overmap_special')
    tiles={};maps=[]
    for e in es:
        if e['type']!='mapgen':continue
        ids={n for row in matrix(e) for n in row}
        for z in sorted({c['point'][2] for c in special['overmaps'] if terrain_base(c.get('overmap','')) in ids}):
            projected,info=project(e,{'overmaps':[c for c in special['overmaps'] if c['point'][2]==z]}, {})
            assert not tiles.keys()&projected.keys()
            tiles.update(projected);maps.append(info)
    nav={p:t for p,t in tiles.items() if t.startswith(('t_elevator','t_stairs_','t_ramp_'))}
    access=review(tiles)
    directional=[c for c in access['controls'] if 'required_destination'in c]
    assert len(directional)==6 and all(c['destination_shaft_present'] for c in directional)
    bundle=read_bundle(COMMUNITY_ROOT)
    old=next(e for e in json.loads(bundle['bn/data/json/overmap/overmap_special/specials.json']) if e.get('id')=='hub_01')
    oldpoints={tuple(c['point']) for c in old['overmaps']}
    newpoints={tuple(c['point']) for c in special['overmaps']}
    return {'runtime_validated':False,'navigation':[{ 'point':list(p),'terrain':t }for p,t in sorted(nav.items())],
      'projection':maps,'access':access,'bn_only_special_coordinates':sorted(oldpoints-newpoints),
      'limits':['No BN-only placement coordinates does not prove BN map contents are identical','Several source controls intentionally have no nearby projected shaft; preserved as source, not declared functional','Unpaired stairs at projection boundaries may connect to unprojected/external maps; no synthetic stairs added','Same-OMT stair search candidates are not proof of actual character travel']}


def prepare(check=False):
    prepare_hub(check=True)
    report=analyze();text=json.dumps(report,indent=2,ensure_ascii=True)+'\n';path=OUT/'HUB_ACCESS_GEOMETRY.json'
    if check:assert path.read_text()==text,path
    else:path.write_text(text)
    print('Hub access: 6 restricted directional controls have destination shafts; 28 stairs and 44 ramps projected; native generation still required')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
