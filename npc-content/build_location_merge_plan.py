#!/usr/bin/env python3
"""Plan additive location work by identity; never install overlapping definitions."""
import collections
import hashlib
import json

from prepare_community_layers import ROOT, identities, read_bundle, reference_key, selected_entries


def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k,v in value.items() if not k.startswith('//')}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value


def fingerprint(entry):
    return hashlib.sha256(json.dumps(entry,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def map_decision(source, baseline):
    if not baseline:
        return 'resolve_baseline_before_addition'
    candidate = semantic(source)
    candidate.setdefault('method', 'json')
    for entry in baseline:
        existing = semantic(entry)
        existing.setdefault('method', 'json')
        if candidate == existing:
            return 'keep_existing_variant_set'
    return 'review_existing_variant_set'


def build(root):
    files = read_bundle(root)
    manifest = json.loads((root/'SOURCE_MANIFEST.json').read_text())
    requested = {x['id'] for x in json.loads((root/'LOCATION_LINK_REPORT.json').read_text())['placement_links']}
    specials = {'dda': {}, 'bn': {}}
    maps = {'dda': collections.defaultdict(list), 'bn': collections.defaultdict(list)}
    definitions = {}
    for name, content in files.items():
        side = name.split('/')[0]
        entries = json.loads(content)
        chosen = selected_entries(name, entries, manifest) if side == 'dda' else enumerate(entries)
        for index, entry in chosen:
            key = (name, index)
            definitions[key] = entry
            record = {'file': name, 'index': index, 'entry_sha256': fingerprint(entry)}
            if entry['type'] == 'overmap_special' and isinstance(entry.get('id'), str):
                if entry['id'] in specials[side]:
                    raise ValueError('Ambiguous special identity requires explicit load-order review: '+entry['id'])
                specials[side][entry['id']] = record
            for kind, identifier in identities(entry):
                if kind == 'mapgen_terrain':
                    maps[side][(kind, identifier)].append(record)
    locations = []
    for identifier in sorted(requested):
        source = specials['dda'][identifier]
        entry = definitions[(source['file'], source['index'])]
        baseline = specials['bn'].get(identifier)
        # Detect renamed candidates using dedicated map IDs, not generic forest/road cells.
        own_ids = {reference_key('mapgen_terrain', x['overmap'], maps['dda'])[1]
                   for x in entry['overmaps'] if 'overmap' in x and
                   reference_key('mapgen_terrain', x['overmap'], maps['dda']) in maps['dda']}
        candidates = []
        if baseline is None:
            for other_id, record in specials['bn'].items():
                other = definitions[(record['file'],record['index'])]
                matches = sorted({reference_key('mapgen_terrain', x['overmap'], maps['dda'])[1]
                                  for x in other.get('overmaps',[]) if 'overmap' in x} & own_ids)
                if matches:
                    candidates.append({'id': other_id, 'shared_map_ids': matches, 'baseline': record})
        operation = 'merge_existing_special' if baseline else 'resolve_possible_existing_special' if candidates else 'validate_new_special_candidate'
        locations.append({'id':identifier,'source':source,'baseline':baseline,
                          'renamed_candidates':candidates,'operation':operation,
                          'preserve_existing_occurrence':baseline is not None,
                          'installable':False})
    map_rows = []
    for key, sources in sorted(maps['dda'].items()):
        baseline = maps['bn'].get(reference_key(*key,maps['bn']), [])
        for source in sources:
            entry = definitions[(source['file'],source['index'])]
            existing = [definitions[(x['file'],x['index'])] for x in baseline]
            comparisons = []
            for record, old in zip(baseline, existing):
                body, previous = semantic(entry.get('object',{})), semantic(old.get('object',{}))
                comparisons.append({'baseline':record,
                    'rows_equal':isinstance(body.get('rows'),list) and body['rows'] == previous.get('rows'),
                    'changed_object_sections':sorted(k for k in body.keys()|previous.keys() if body.get(k)!=previous.get(k))})
            map_rows.append({'terrain':key[1],'source':source,'baseline_variants':baseline,
                             'operation':map_decision(entry,existing),'comparisons':comparisons,
                             'installable':False})
    result = {'locations':locations,'mapgen':map_rows,
        'summary':{'location_operations':dict(collections.Counter(x['operation'] for x in locations)),
                   'mapgen_operations':dict(collections.Counter(x['operation'] for x in map_rows))},
        'rules':['Existing special IDs require merging at the original location, never a second occurrence',
                 'Matching mapgen terrain IDs require reviewing the complete BN variant set',
                 'An absent ID in the selected map baseline is unresolved, not permission to add',
                 'Rows alone do not prove semantic equivalence; terrain legends, NPCs, items and effects also matter'],
        'baseline_scope':'All 12 pinned BN overmap_special directory files; selected mapgen files only; external definitions still require review',
        'release_ready':False}
    (root/'LOCATION_MERGE_PLAN.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    summary = {k:v for k,v in result.items() if k != 'mapgen'}
    summary['unchanged_terrain_ids'] = sorted({x['terrain'] for x in map_rows if x['operation']=='keep_existing_variant_set'})
    summary['examples'] = [x for x in map_rows if x['terrain'] in {'chemical_lab_ocu','lumbermill_1_1_ocu'}]
    (root/'LOCATION_MERGE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__ == '__main__':
    print(json.dumps(build(ROOT)['summary'],indent=2))
