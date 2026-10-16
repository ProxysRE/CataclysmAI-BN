#!/usr/bin/env python3
"""Stage whole NPC communities; never install an unvalidated batch into BN."""
import argparse
import base64
import collections
import copy
import gzip
import hashlib
import json
from pathlib import Path

from adapt_dialogue import adapt, expand_eocs

ROOT = Path(__file__).resolve().parent / 'layers'
GROUPS = ('robofac', 'godco', 'campus', 'militia', 'bunker_shop',
          'cabin_chemist', 'lumbermill_employees', 'scrap_trader')
REFERENCES = {
    'chat': 'talk_topic', 'topic': 'talk_topic', 'npc_first_topic': 'talk_topic',
    'followup': 'mission_definition', 'add_mission': 'mission_definition',
    'u_has_mission': 'mission_definition', 'mission': 'mission_definition',
    'class': 'npc_class', 'faction': 'faction', 'npc_set_fac': 'faction',
    'run_eocs': 'effect_on_condition', 'queue_eocs': 'effect_on_condition',
    'mapgen_update': 'mapgen', 'update_mapgen_id': 'mapgen',
    'om_terrain': 'overmap_terrain', 'om_special': 'overmap_special',
}


def identities(entry):
    value = entry.get('id', entry.get('abstract', entry.get('nested_mapgen_id', entry.get('update_mapgen_id'))))
    if value is None and entry.get('type') == 'mapgen':
        value = entry.get('om_terrain')
        values = value if isinstance(value, list) else [value]
        return [('mapgen_terrain', name) for name in values if isinstance(name, str)]
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
    definitions = {}
    baseline = collections.defaultdict(list)
    sources = collections.defaultdict(list)
    parsed = {name: json.loads(content) for name, content in files.items()}
    for name, entries in parsed.items():
        for index, entry in enumerate(entries):
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
        group = next((group for group in GROUPS if group in name), None)
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
        for index, original in enumerate(entries):
            types[original['type']] += 1
            for kind, identifier in identities(original):
                if (kind, identifier) in baseline:
                    report['overlaps'].append({'type': kind, 'id': identifier,
                        'source': name, 'baseline': baseline[(kind, identifier)],
                        'action': 'review_topic_merge' if kind == 'talk_topic' else 'compare_before_install'})
            for key, value, pointer in walk(original):
                if key not in REFERENCES:
                    continue
                # Numeric NPC mission enum is not a mission definition reference.
                if key == 'mission' and original['type'] == 'npc':
                    continue
                for identifier in value if isinstance(value, list) else [value]:
                    if not isinstance(identifier, str):
                        continue
                    kind = 'npc' if key == 'class' and '/place_npcs/' in pointer else REFERENCES[key]
                    if kind == 'talk_topic' and identifier in ('TALK_DONE', 'TALK_NONE'):
                        continue
                    providers = sources.get((kind, identifier), [])
                    bn = baseline.get((kind, identifier), [])
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
