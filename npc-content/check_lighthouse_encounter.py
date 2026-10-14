#!/usr/bin/env python3
"""Verify DDA encounter insertion preserves pinned BN dock variants."""
import copy
import json
from pathlib import Path
root=Path(__file__).resolve().parent/'lighthouse'
baseline=json.loads((root/'BN_DOCK_REFERENCE.json').read_text())['definitions']
staged=json.loads((root/'staging/data/json/mapgen/dock.json').read_text())
assert len(baseline)==len(staged)
added=[]
for before,after in zip(baseline,staged):
    restored=copy.deepcopy(after)
    old=before.get('object',{}).get('place_nested',[])
    new=after.get('object',{}).get('place_nested',[])
    if new!=old:
        additions=new[len(old):]
        assert new[:len(old)]==old
        assert additions==[{'chunks':[['NPC_lighthouse_man_spawn',25],['null',75]],'x':12,'y':21}]
        if 'place_nested' in before.get('object',{}):
            restored['object']['place_nested']=old
        else:
            del restored['object']['place_nested']
        added.extend(additions)
    assert restored==before,'Existing BN dock data changed'
assert len(added)==1
nested=json.loads((root/'staging/data/json/mapgen/nested/npc_nested_spawns.json').read_text())
assert len(nested)==1 and nested[0]['nested_mapgen_id']=='NPC_lighthouse_man_spawn'
assert nested[0]['object']['mapgensize']==[1,1]
assert nested[0]['object']['place_npcs']==[{'class':'NPC_lighthouse_man','x':0,'y':0}]
report={'bn_definitions_preserved':len(baseline),'augmented_layouts':1,'source_spawn_weight':25,'source_empty_weight':75,'spawn_cell':[12,21],'npc':'NPC_lighthouse_man','runtime_validated':False}
(root/'ENCOUNTER_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: all BN dock variants preserved; exact DDA weighted encounter and NPC spawn link retained')
