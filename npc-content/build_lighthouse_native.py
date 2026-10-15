#!/usr/bin/env python3
"""Build the actual NPC/quest loader checkpoint from reviewed staging."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parent
stage=root/'lighthouse/staging/data/json'
files=sorted((stage/'npcs/Lighthouse_Family').glob('*.json'))+[stage/'npcs/factions.json']
entries=[]
hashes={}
for path in files:
    entries.extend(json.loads(path.read_text()))
    hashes[path.relative_to(stage).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
assert sum(x['type']=='npc' for x in entries)==4
assert sum(x['type']=='mission_definition' for x in entries)==7
assert sum(x['type']=='talk_topic' for x in entries)==26
(root/'native/dda_lighthouse_community.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
missions={entry['id']:entry for entry in entries if entry['type']=='mission_definition'}
fixtures=['#pragma once\n\nnamespace dda_port {\n']
for label,mission_id in [('boat','MISSION_lighthouse_man_4'),('repair','MISSION_lighthouse_man_5')]:
    # The test supplies the absolute destination; om_terrain is mission routing
    # metadata, not part of the map modification payload.
    update={key:value for key,value in missions[mission_id]['end']['update_mapgen'].items() if key!='om_terrain'}
    payload=json.dumps(update,ensure_ascii=False)
    fixtures.append(f'inline constexpr char {label}_update[] = R"QUEST({payload})QUEST";\n')
fixtures.append('} // namespace dda_port\n')
(root/'native/lighthouse_quest_updates.h').write_text(''.join(fixtures))
report={'staging_sha256':hashes,'definitions':len(entries),'scope':'Actual NPC templates, topics, seven missions, class, shop group, faction and survivor update. World placement and full map package remain separate.','runtime_validated':False}
(root/'lighthouse/NATIVE_LOADER_CHECKPOINT.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Built {len(entries)} actual lighthouse definitions for native loading')
