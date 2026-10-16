#!/usr/bin/env python3
"""Preserve and adapt lighthouse dialogue, reporting unsupported effects."""
import collections
import copy
import hashlib
import json
from pathlib import Path
from adapt_dialogue import adapt

root = Path(__file__).resolve().parent / 'lighthouse'
counts = collections.Counter()
types = collections.Counter()
blocked = []
files = {}
for source in sorted((root/'upstream').rglob('*.json')):
    relative = source.relative_to(root/'upstream')
    files[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    if relative.as_posix() == 'data/json/npcs/expertise_traits.json':
        # The electrical expertise IDs already exist in the pinned BN file.
        # Keep upstream provenance, but do not duplicate BN mutation/group data.
        continue
    if relative.as_posix() == 'data/json/furniture_and_terrain/terrain-floors-indoor.json':
        # t_floor_olight already exists in BN; preserve the BN light/roof/bash
        # behavior rather than installing a competing DDA definition.
        continue
    if relative.as_posix() == 'data/json/mapgen/dock.json':
        # Preserve every BN variant and its content; augment only geometry that
        # matches the source layout used by DDA for this encounter.
        baseline = json.loads((root/'BN_DOCK_REFERENCE.json').read_text())
        result = copy.deepcopy(baseline['definitions'])
        changes = 0
        for upstream in json.loads(source.read_text()):
            spawn = upstream.get('object', {}).get('place_nested', [])
            if not any('NPC_lighthouse_man_spawn' in str(entry) for entry in spawn):
                continue
            matches = [entry for entry in result if entry.get('om_terrain') == upstream.get('om_terrain') and entry.get('object', {}).get('rows') == upstream['object'].get('rows')]
            if len(matches) != 1:
                raise ValueError('Dock encounter layout is ambiguous or differs from BN')
            matches[0]['object'].setdefault('place_nested', []).extend(copy.deepcopy(spawn))
            changes += 1
        target = root/'staging'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        counts['bn_dock_variants_augmented'] += changes
        continue
    result = []
    for original in json.loads(source.read_text()):
        types[original['type']] += 1
        try:
            entry = adapt(copy.deepcopy(original), counts)
        except (ValueError, SyntaxError) as error:
            entry = original
            blocked.append({'file':relative.as_posix(), 'id':original.get('id'), 'reason':str(error), 'source_preserved':True})
        if entry.get('id') == 'MISSION_lighthouse_man_3':
            # BN searches the origin layer unless z is explicit. The existing
            # house_04_basement is underground; preserve DDA's intended target.
            entry['start']['assign_mission_target']['z'] = -1
            counts['bn_family_basement_search_layer'] += 1
        if entry['type'] == 'mapgen':
            entry = copy.deepcopy(entry)
            entry['method'] = 'json'
        if entry['type'] == 'overmap_terrain' and isinstance(entry.get('id'), list):
            for identifier in entry['id']:
                variant = copy.deepcopy(entry)
                variant['id'] = identifier
                result.append(variant)
            continue
        result.append(entry)
    target = root/'staging'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
manifest = {'DDA_commit':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974', 'BN_commit':'c621aaf42fa182473aad10feea2b55647704dcf1', 'license':'CC-BY-SA-3.0; upstream credits retained', 'files':files}
manifest['selected_source_aliases'] = {'data/json/overmap/overmap_terrain/lighthouse_parent.json': {'upstream_path':'data/json/overmap/overmap_terrain/overmap_terrain.json', 'selected_abstract':'lighthouse_abstract'}}
(root/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
report = {'definitions':dict(types), 'translated':dict(counts), 'blocked_definitions':blocked,
          'required_reviews':['Global TALK_FRIEND/GIVE_ITEM/USE_ITEM/RADIO definitions must merge into BN topics, never replace them','Duplicate topic IDs use upstream extension semantics; no dictionary overwrite','Seven missions and lighthouse repair update mapgen require native checks','Location, camp and typed dependency closure'], 'runtime_validated':False,'release_ready':False}
(root/'ADAPTATION_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
