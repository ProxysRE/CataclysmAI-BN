#!/usr/bin/env python3
"""Validate map/mission links without claiming native loader compatibility."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent/'lighthouse'
entries=[entry for p in (root/'staging').rglob('*.json') for entry in json.loads(p.read_text())]
terrains={x['id'] for x in entries if x['type']=='overmap_terrain' and 'id' in x}
maps={x['om_terrain'] for x in entries if x['type']=='mapgen' and isinstance(x.get('om_terrain'),str)}
assert terrains == maps, {'missing_maps':sorted(terrains-maps),'missing_terrain':sorted(maps-terrains)}
updates={x['update_mapgen_id'] for x in entries if x['type']=='mapgen' and 'update_mapgen_id' in x}
missions=[x for x in entries if x['type']=='mission_definition']
assert len(missions)==7
for special in [x for x in entries if x['type']=='overmap_special']:
    points=[tuple(x['point']) for x in special['overmaps']]
    assert len(points)==len(set(points)),special['id']
def walk(value):
    if isinstance(value,dict):
        for key,child in value.items():
            yield key,child
            yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)
references={v for k,v in walk(entries) if k=='mapgen_update' and isinstance(v,str)}
missing=sorted(references-updates)
external_targets=sorted({v for k,v in walk(missions) if k=='om_terrain' and isinstance(v,str)}-terrains)
report={'terrain_mapgen_ids':len(terrains),'missions':len(missions),'update_mapgen_ids':sorted(updates),
        'missing_update_ids':missing,'external_mission_targets':external_targets,
        'schema_reviews':['NPC location and safe-space conditions','goal-condition contexts','mission NPC placement and target updates','overmap terrain abstract inheritance, risk/safety flags and travel/vision fields','camp recipes and camp engine','BN common-dialogue merging'], 'runtime_validated':False}
(root/'LINK_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
assert not missing,missing
print(f"PASS: {len(terrains)} terrain/mapgen IDs, seven missions and referenced updates; external targets reported")
