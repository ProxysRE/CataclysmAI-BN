#!/usr/bin/env python3
"""Stage whole NPC communities; never install an unvalidated batch into BN."""
import argparse
import base64
import collections
import copy
import gzip
import hashlib
import json
import re
from pathlib import Path

from adapt_dialogue import adapt, expand_eocs

ROOT = Path(__file__).resolve().parent / 'layers'
GROUPS = ('robofac', 'godco', 'campus', 'militia', 'bunker_shop',
          'cabin_chemist', 'lumbermill_employees', 'scrap_trader')
REFERENCES = {
    'chat': 'talk_topic', 'topic': 'talk_topic', 'npc_first_topic': 'talk_topic',
    'followup': 'mission_definition', 'add_mission': 'mission_definition',
    'u_has_mission': 'mission_definition',
    'class': 'npc_class', 'faction': 'faction', 'npc_set_fac': 'faction',
    'run_eocs': 'effect_on_condition', 'queue_eocs': 'effect_on_condition',
    'mapgen_update': 'mapgen', 'update_mapgen_id': 'mapgen',
    'om_terrain': 'overmap_terrain', 'om_special': 'overmap_special',
    'overmap': 'overmap_terrain', 'npc_at_om_location': 'overmap_terrain',
    'u_at_om_location': 'overmap_terrain',
    'palettes': 'palette', 'chunks': 'mapgen',
}


def flat_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from flat_strings(child)


def identities(entry):
    value = entry.get('id', entry.get('abstract', entry.get('nested_mapgen_id', entry.get('update_mapgen_id'))))
    if value is None and entry.get('type') == 'mapgen':
        value = entry.get('om_terrain')
        return [('mapgen_terrain', name) for name in flat_strings(value)]
    values = value if isinstance(value, list) else [value]
    return [(entry.get('type'), name) for name in values if isinstance(name, str)]


def walk(value, pointer=''):
    if isinstance(value, dict):
        for key, child in value.items():
            path = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            yield key, child, path
            yield from walk(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, pointer + '/' + str(index))


def typed_references(entry):
    for key, value, pointer in walk(entry):
        if key == 'copy-from' and isinstance(value, str):
            yield entry['type'], value, pointer
        if key not in REFERENCES:
            continue
        kind = REFERENCES[key]
        if key == 'class' and (entry['type'] == 'mapgen' or '/place_npcs/' in pointer):
            kind = 'npc'
        for identifier in flat_strings(value):
            if key == 'chunks' and identifier == 'null':
                continue
            if kind == 'talk_topic' and identifier in ('TALK_DONE', 'TALK_NONE'):
                continue
            if kind == 'overmap_terrain' and identifier.startswith('FACTION_CAMP_'):
                continue
            yield kind, identifier, pointer
    if entry['type'] == 'mapgen':
        for index, owner in enumerate(entry.get('object', {}).get('faction_owner', [])):
            if isinstance(owner, dict) and isinstance(owner.get('id'), str):
                yield 'faction', owner['id'], f'/object/faction_owner/{index}/id'


def selected_entries(name, entries, manifest):
    indices = manifest['files'][name].get('selection')
    return [(i, entry) for i, entry in enumerate(entries) if indices is None or i in indices]


def reference_key(kind, identifier, index):
    key = (kind, identifier)
    if key not in index and kind in {'overmap_terrain', 'mapgen_terrain'}:
        base = re.sub(r'_(north|east|south|west)$', '', identifier)
        if (kind, base) in index:
            return kind, base
    return key


def read_bundle(root):
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    raw = gzip.decompress(base64.b64decode((root / 'SOURCE_BUNDLE.json.gz.base64').read_text()))
    if hashlib.sha256(raw).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Source bundle checksum mismatch')
    files = json.loads(raw)
    if set(files) != set(manifest['files']):
        raise ValueError('Source manifest file set mismatch')
    for name, content in files.items():
        data = content.encode()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != manifest['files'][name]['git_blob_sha']:
            raise ValueError('Pinned Git blob mismatch: ' + name)
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return files


def prepare(root):
    files = read_bundle(root)
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    definitions = {}
    baseline = collections.defaultdict(list)
    sources = collections.defaultdict(list)
    parsed = {name: json.loads(content) for name, content in files.items()}
    # Remove only generated outputs for now-unselected manifest sources.
    for name, entries in parsed.items():
        if name.startswith('dda/') and not selected_entries(name, entries, manifest):
            (root/'staging'/name.removeprefix('dda/')).unlink(missing_ok=True)
    for name, entries in parsed.items():
        for index, entry in selected_entries(name, entries, manifest):
            destination = baseline if name.startswith('bn/') else sources
            for identity in identities(entry):
                destination[identity].append({'file': name, 'index': index})
            if name.startswith('dda/') and entry.get('type') == 'effect_on_condition':
                identifier = entry['id']
                if identifier in definitions:
                    raise ValueError('Duplicate EOC definition: ' + identifier)
                definitions[identifier] = entry
    report = {'release_ready': False, 'runtime_validated': False,
              'baseline_scope': 'Selected BN NPC and location files, not a complete BN ID index',
              'dependency_scope': 'Selected explicit NPC/dialogue/mission/map references; item, trait and implicit engine references require later closure',
              'groups': {}, 'overlaps': [], 'references': [], 'blocked': []}
    for name, entries in parsed.items():
        if not name.startswith('dda/'):
            continue
        chosen = selected_entries(name, entries, manifest)
        if not chosen:
            continue
        group = manifest['files'][name].get('group') or next((group for group in GROUPS if group in name), None)
        if group is None and 'robofaq' in name:
            group = 'robofac'
        if group is None and 'lumbermill' in name:
            group = 'lumbermill_employees'
        if group is None:
            raise ValueError('Source has no assigned community: ' + name)
        summary = report['groups'].setdefault(group, {'files': 0, 'definitions': {},
                      'translated': {}, 'blocked': 0, 'status': 'staged_unvalidated'})
        summary['files'] += 1
        types = collections.Counter(summary['definitions'])
        counts = collections.Counter(summary['translated'])
        output = []
        for index, original in chosen:
            types[original['type']] += 1
            for kind, identifier in identities(original):
                if (kind, identifier) in baseline:
                    report['overlaps'].append({'type': kind, 'id': identifier,
                        'source': name, 'baseline': baseline[(kind, identifier)],
                        'action': 'review_topic_merge' if kind == 'talk_topic' else 'compare_before_install'})
            for kind, identifier, pointer in typed_references(original):
                providers = sources.get(reference_key(kind, identifier, sources), [])
                bn = baseline.get(reference_key(kind, identifier, baseline), [])
                report['references'].append({'file': name, 'index': index,
                    'pointer': pointer, 'type': kind, 'id': identifier,
                    'status': 'selected_source' if providers else 'selected_bn' if bn else 'external_review',
                    'source_providers': providers, 'bn_providers': bn})
            current_counts = collections.Counter()
            try:
                candidate = copy.deepcopy(original)
                # Keep EOCs as source definitions until their native lifecycle is supported.
                if original['type'] == 'effect_on_condition':
                    raise ValueError('Native EOC definition requires separate lifecycle review')
                candidate = expand_eocs(candidate, definitions, current_counts)
                candidate = adapt(candidate, current_counts)
                if candidate['type'] == 'mapgen':
                    candidate['method'] = 'json'
                    current_counts['mapgen_method'] += 1
                output.append(candidate)
                counts.update(current_counts)
            except (ValueError, SyntaxError, TypeError, KeyError) as error:
                output.append(copy.deepcopy(original))
                summary['blocked'] += 1
                report['blocked'].append({'file': name, 'index': index,
                    'ids': identities(original), 'reason': str(error), 'source_preserved': True})
        summary['definitions'] = dict(types)
        summary['translated'] = dict(counts)
        target = root / 'staging' / name.removeprefix('dda/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    report['totals'] = {'source_files': sum(x['files'] for x in report['groups'].values()),
        'definitions': sum(sum(x['definitions'].values()) for x in report['groups'].values()),
        'blocked_definitions': len(report['blocked']), 'overlap_records': len(report['overlaps']),
        'reference_records': len(report['references']),
        'external_reference_records': sum(x['status']=='external_review' for x in report['references'])}
    (root / 'LAYER_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    summary = {key: value for key, value in report.items() if key not in ('overlaps', 'references', 'blocked')}
    summary['blocker_reasons'] = dict(collections.Counter(x['reason'] for x in report['blocked']))
    (root / 'LAYER_SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    report = prepare(args.root)
    print(json.dumps({'totals': report['totals'], 'groups': report['groups']}, indent=2))


if __name__ == '__main__':
    main()
