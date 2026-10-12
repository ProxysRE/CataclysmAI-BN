#!/usr/bin/env python3
"""Check island layout references before native generation; report engine gaps."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "island_prison"
stage = root / "staging/data/json"
terrains = {x['id'] for x in json.loads((stage / 'overmap/overmap_terrain/overmap_terrain_public_institutional.json').read_text())}
generated = set()
def flatten(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from flatten(child)
for source in (stage / 'mapgen').rglob('*.json'):
    for entry in json.loads(source.read_text()):
        generated.update(flatten(entry.get('om_terrain', [])))
assert terrains == generated, {'missing_mapgen': sorted(terrains-generated), 'missing_terrain': sorted(generated-terrains)}
summaries = []
for entry in json.loads((stage / 'overmap/overmap_special/specials.json').read_text()):
    points = [tuple(cell['point']) for cell in entry['overmaps']]
    assert len(points) == len(set(points)), entry['id']
    local = [cell for cell in entry['overmaps'] if cell['overmap'].startswith(('prison_island', 'prison_alcatraz'))]
    for cell in local:
        assert cell['overmap'].removesuffix('_north') in terrains, cell
    summaries.append({'id':entry['id'], 'cells':len(points), 'prison_cells':len(local),
                      'z_levels':sorted({p[2] for p in points}),
                      'camp_cells':[cell for cell in local if 'camp' in cell]})
faction = json.loads((stage/'npcs/factions.json').read_text())[0]
epilogues = {x['id'] for entry in json.loads((stage/'snippets/epilogue_factions.json').read_text()) for x in entry['text']}
assert {x['id'] for x in faction['epilogues']} <= epilogues
report = {'terrain_ids':len(terrains), 'all_terrain_mapgen_references_resolved':True,
          'specials':summaries, 'epilogues_resolved':True,
          'engine_gaps':[
              {'feature':'prisoners camp placement', 'source':'Island prison overmap cell [0,1,0]',
               'action':'Port camp registration/ownership; preserve camp and camp_name fields'},
              {'feature':'faction nutrition and limited area claim',
               'action':'BN requires integer food_supply; DDA uses timestamped calorie/vitamin stocks and limited_area_claim. Native model/consumers must be ported; no lossy calorie-only substitution.'}],
          'external_terrain_and_location_references': ['lake_surface','lake_water_cube','lake_bed','solid_earth','empty_rock'],
          'runtime_validated':False}
(root/'PLACEMENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"PASS: {len(terrains)} terrain/mapgen IDs, both layouts, unique cells and two prisoner epilogues; native gaps retained")
