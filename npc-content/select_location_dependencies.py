#!/usr/bin/env python3
"""Select related definitions from shared source files without importing them whole."""
import collections
import json
from pathlib import Path

from prepare_community_layers import ROOT, identities, read_bundle, reference_key, typed_references


def select(root):
    files = read_bundle(root)
    manifest = json.loads((root/'SOURCE_MANIFEST.json').read_text())
    entries = {}
    index = collections.defaultdict(list)
    roots = set()
    for name, content in files.items():
        if not name.startswith('dda/'):
            continue
        for position, entry in enumerate(json.loads(content)):
            key = (name, position)
            entries[key] = entry
            for identity in identities(entry):
                index[identity].append(key)
            if manifest['files'][name].get('group') != 'shared_dependencies':
                roots.add(key)
    selected = set(roots)
    root_terrain_ids = {identifier for key in roots for kind,identifier in identities(entries[key])
                        if kind == 'mapgen_terrain'}
    root_map_index = {('mapgen_terrain', identifier): True for identifier in root_terrain_ids}
    placements = []
    for key, entry in entries.items():
        if entry['type'] != 'overmap_special':
            continue
        matches = sorted({identifier for kind,identifier,_ in typed_references(entry)
                          if kind == 'overmap_terrain' and reference_key('mapgen_terrain', identifier, root_map_index) in root_map_index})
        if matches:
            selected.add(key)
            placements.append({'special': list(key), 'id': entry['id'], 'root_map_terrains': matches})
    pending = collections.deque(sorted(selected))
    edges = []
    while pending:
        source = pending.popleft()
        references = list(typed_references(entries[source]))
        for kind, identifier, pointer in references:
            # Any map declared for a referenced OMT is also a location dependency.
            targets = [(kind, identifier)]
            if kind == 'overmap_terrain':
                targets.append(('mapgen_terrain', identifier))
            for target in targets:
                providers = index.get(reference_key(*target, index), [])
                edges.append({'from': list(source), 'to': list(target),
                              'field': pointer, 'providers': [list(x) for x in providers]})
                for provider in providers:
                    if provider not in selected:
                        selected.add(provider)
                        pending.append(provider)
    for name, metadata in manifest['files'].items():
        if metadata.get('group') == 'shared_dependencies':
            metadata['selection'] = sorted(i for filename, i in selected if filename == name)
    (root/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    support = sorted(selected-roots)
    report = {'root_definitions': len(roots), 'selected_support_definitions': len(support),
              'selected_support': [{'file': name, 'index': i, 'ids': identities(entries[(name,i)])}
                                   for name,i in support],
              'edges': edges, 'placement_links': placements, 'runtime_validated': False,
              'scope': 'Typed dialogue/mission/location references, inheritance and OMT-to-mapgen links; not a complete item/monster/palette dependency closure'}
    (root/'LOCATION_LINK_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Selected {len(support)} shared definitions for {len(roots)} roots; unrelated shared definitions excluded')
    return report


if __name__ == '__main__':
    select(ROOT)
