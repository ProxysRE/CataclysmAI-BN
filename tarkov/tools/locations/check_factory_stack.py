"""Check four-level packaging, source-cell preservation and paired stair topology."""
import argparse
from collections import deque
import hashlib
from pathlib import Path
import subprocess

from check_industrial import catalog
from build_factory_stack import load, OUT, MOD
from factory_volumes import air_candidates


def reconstruct(manifest, definitions):
    w,h = manifest['size']
    grids = {z:[[None]*w for _ in range(h)] for z in manifest['levels']}
    by_id = {d['om_terrain'][0]:d for d in definitions}
    assert len(by_id) == len(definitions) == len(manifest['blocks'])
    palette = {}
    for block in manifest['blocks']:
        x0,y0,z = block['origin']
        assert z in grids and block['size'] == [24,24]
        assert x0%24 == y0%24 == 0 and 0 <= x0 <= w-24 and 0 <= y0 <= h-24
        d = by_id[block['terrain_id']]
        assert set(d) == {'type','om_terrain','method','object'} and d['type']=='mapgen' and d['method']=='json'
        obj = d['object']
        assert set(obj)=={'fill_ter','rows','terrain'} and obj['fill_ter']=='t_rock'
        assert len(obj['rows'])==24 and all(len(r)==24 for r in obj['rows'])
        for y,row in enumerate(obj['rows']):
            for x,c in enumerate(row):
                assert grids[z][y0+y][x0+x] is None
                assert c in obj['terrain']
                assert c not in palette or palette[c]==obj['terrain'][c]
                grids[z][y0+y][x0+x] = c
                palette[c] = obj['terrain'][c]
    assert all(c is not None for g in grids.values() for row in g for c in row)
    return {z:[''.join(r) for r in rows] for z,rows in grids.items()},palette


def validate_source(grids, manifest, blueprints, plan, volumes=None):
    air = air_candidates(blueprints,volumes) if volumes is not None else {}
    expected = {tuple(r['from']):'<' for r in manifest['vertical_transitions']}
    expected.update({tuple(r['to']):'>' for r in manifest['vertical_transitions']})
    assert len(expected)==2*len(manifest['vertical_transitions'])
    accepted = {(r['source_ref'],r['from_z'],r['to_z'],tuple(r['proposed_position']))
                for r in plan['direction_supported_candidates']
                if r['status']=='direction_supported_candidate' and not r['requires_intermediate_flight_review']}
    actual = set()
    for r in manifest['vertical_transitions']:
        x,y,z = r['from'];tx,ty,tz = r['to']
        assert (x,y)==(tx,ty) and tz==z+1
        actual.add((r['source_ref'],z,tz,(x,y)))
        assert grids[z][y][x]=='<' and grids[tz][y][x]=='>'
    assert actual==accepted and len(actual)==len(manifest['vertical_transitions'])
    for floor in blueprints['floors']:
        z = floor['z']
        for y,row in enumerate(floor['rows']):
            for x,c in enumerate(row):
                expected_c = expected.get((x,y,z),'~' if (x,y,z) in air else c)
                assert expected_c==grids[z][y][x], (x,y,z,'Unexpected geometry change')
                if (x,y,z) in expected:
                    assert c=='S', 'A stair cannot cut a new hole'


def graph(grids, costs):
    standing = {(x,y,z) for z,rows in grids.items() for y,row in enumerate(rows)
                for x,c in enumerate(row) if costs[c]>0}
    remaining = set(standing)
    groups = []
    while remaining:
        p = min(remaining,key=lambda v:(v[2],v[1],v[0]))
        pending,seen = deque([p]),{p}
        remaining.remove(p)
        while pending:
            x,y,z = pending.popleft()
            neighbors = [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z)]
            c = grids[z][y][x]
            if c=='<' and (x,y,z+1) in standing and grids[z+1][y][x]=='>':
                neighbors.append((x,y,z+1))
            if c=='>' and (x,y,z-1) in standing and grids[z-1][y][x]=='<':
                neighbors.append((x,y,z-1))
            for n in neighbors:
                if n in remaining:
                    remaining.remove(n);seen.add(n);pending.append(n)
        groups.append(seen)
    main = max(groups,key=lambda g:sum(p[2]==0 for p in g))
    anchor = min((p for p in main if p[2]==0),key=lambda p:(p[1],p[0]))
    return {'anchor':list(anchor),'main_size':len(main),'component_sizes':sorted(map(len,groups),reverse=True),
            'main_cells_by_level':{str(z):sum(p[2]==z for p in main) for z in sorted(grids)}}


def check(bn):
    manifest,geometry = load(OUT/'stack_manifest.json'),load(OUT/'stack_geometry.json')
    assert subprocess.check_output(['git','-C',str(bn),'rev-parse','HEAD'],text=True).strip()==manifest['bn_commit']
    assert not subprocess.check_output(['git','-C',str(bn),'status','--porcelain','--',
                                       'data/json/furniture_and_terrain'],text=True).strip()
    digest = hashlib.sha256((OUT/'reference/Factory.svg').read_bytes()).hexdigest()
    assert digest==geometry['source_sha256']==manifest['source_sha256']
    assert manifest['levels']==[-1,0,1,2] and manifest['size']==[264,288]
    grids,palette = reconstruct(manifest,load(MOD/'mapgen.json'))
    assert grids=={f['z']:f['rows'] for f in geometry['floors']} and palette==geometry['terrain']
    validate_source(grids,manifest,load(OUT/'floor_blueprints.json'),load(OUT/'vertical_plan.json'),load(OUT/'volume_rules.json'))
    overmap = load(MOD/'overmap.json')
    terrain = {d['id']:d for d in overmap if d['type']=='overmap_terrain'}
    specials = [d for d in overmap if d['type']=='overmap_special']
    assert len(terrain)==len(overmap)-1==len(manifest['blocks'])==528
    assert set(terrain)=={b['terrain_id'] for b in manifest['blocks']}
    assert all(d['flags']==['NO_ROTATE'] and d['mondensity']==0 for d in terrain.values())
    assert len(specials)==1 and specials[0]['occurrences']==[0,0]
    assert specials[0]['overmaps']==[{'point':[b['origin'][0]//24,b['origin'][1]//24,b['origin'][2]],
                                     'overmap':b['terrain_id']} for b in manifest['blocks']]
    world_types = load(MOD/'world_types.json')
    assert len(world_types)==1
    wt = world_types[0]
    assert wt['type']=='world_type' and wt['id']=='trkv_factory_probe'
    assert wt['save_prefix']=='trkv_factory_probe_' and wt['infinite_bounds'] is True
    assert wt['region_settings']=='default' and not wt['allow_npc_travel'] and not wt['allow_vehicle_travel']
    asset = catalog(bn)
    costs = {c:asset(t)['move_cost'] for c,t in palette.items()}
    assert all((costs[c]>0)==(c in '.S<>~') for c in palette)
    assert 'GOES_UP' in asset(palette['<'])['flags'] and 'GOES_DOWN' not in asset(palette['<'])['flags']
    assert 'GOES_DOWN' in asset(palette['>'])['flags'] and 'GOES_UP' not in asset(palette['>'])['flags']
    assert 'NO_FLOOR' in asset(palette['~'])['flags'] and 'TRANSPARENT' in asset(palette['~'])['flags']
    assert asset(palette['~'])['trap']=='tr_ledge'
    standing_costs = {c:(0 if 'NO_FLOOR' in asset(t)['flags'] else costs[c]) for c,t in palette.items()}
    air_count = sum(row.count('~') for rows in grids.values() for row in rows)
    assert air_count==manifest['open_air_cells']
    report = {'evidence':'static_source_preservation_and_topology','bn_commit':manifest['bn_commit'],
              'blocks':len(manifest['blocks']),'paired_stairs':len(manifest['vertical_transitions']),
              'changed_source_cells':len(manifest['vertical_transitions'])*2+air_count,
              'stair_cells':len(manifest['vertical_transitions'])*2,'open_air_cells':air_count,
              'air_cells_by_level':{str(z):sum(row.count('~') for row in rows) for z,rows in sorted(grids.items())},
              'standing_graph_excludes_no_floor':True,
              **graph(grids,standing_costs),
              'limitations':['Не проверяет движение персонажа по лестницам или путь НПС',
                             'Воздух задан в двух цеховых зонах; остальное закрыто тестовой границей; крыша и падение не проверены',
                             'Материалы и баллистика условные']}
    from build_factory_stack import write
    write(OUT/'stack_static_report.json',report)
    print(report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn',type=Path,required=True)
    check(p.parse_args().bn.resolve())
