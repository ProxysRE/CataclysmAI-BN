#!/usr/bin/env python3
"""Build a typed quest-item graph from the preserved DDA candidate source.

Unavailable definitions remain explicit obligations. A BN name overlap is not
proof of compatibility; runtime loading is required before package release.
"""
import argparse
import base64
import collections
import gzip
import hashlib
import json
from pathlib import Path

ITEM_TYPES = {'ITEM', 'AMMO', 'ARMOR', 'GENERIC', 'GUN', 'GUNMOD', 'MAGAZINE',
              'TOOL', 'TOOL_ARMOR', 'COMESTIBLE', 'BOOK', 'BIONIC_ITEM', 'BATTERY',
              'ENGINE', 'PET_ARMOR', 'TOOLMOD', 'WHEEL'}
ROOTS = ('broken_kord', 'kord', 'casket74mag', '545_ap', 'nano_fabricator_encryption_code')


def namespace(entry):
    kind = entry.get('type', '')
    return 'item' if kind in ITEM_TYPES else kind


def ids(entry):
    value = entry.get('id', entry.get('abstract', []))
    return [value] if isinstance(value, str) else value


def names(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from names(child)
    elif isinstance(value, dict):
        yield from value.keys()


def references(entry):
    """Only schema-defined reference positions; never display text or enum values."""
    fields = {'copy-from': 'item', 'looks_like': 'item', 'default_container': 'item',
              'revert_to': 'item', 'default_mods': 'item', 'built_in_mods': 'item',
              'ammo': 'ammunition_type', 'ammo_type': 'ammunition_type',
              'category': 'ITEM_CATEGORY', 'material': 'material', 'flags': 'json_flag',
              'ammo_effects': 'ammo_effect', 'ascii_picture': 'ascii_art'}
    for field, target in fields.items():
        for identifier in names(entry.get(field, [])):
            if target == 'ammunition_type' and identifier == 'NULL':
                continue  # DDA/BN enum sentinel, not a data definition.
            yield target, identifier, field
    for pocket in entry.get('pocket_data', []):
        for identifier in names(pocket.get('item_restriction', [])):
            yield 'item', identifier, 'pocket_data.item_restriction'
        for identifier in names(pocket.get('ammo_restriction', {})):
            yield 'ammunition_type', identifier, 'pocket_data.ammo_restriction'
    # Legacy magazine declarations remain typed if present in preserved data.
    for ammo, magazines in entry.get('magazines', []):
        yield 'ammunition_type', ammo, 'magazines.ammo'
        for identifier in magazines:
            yield 'item', identifier, 'magazines.items'


def build(files, roots=ROOTS, bn_candidates=()):
    index = collections.defaultdict(list)
    for path, entries in sorted(files.items()):
        for position, entry in enumerate(entries):
            for identifier in ids(entry):
                index[(namespace(entry), identifier)].append((path, position, entry))
    pending = collections.deque(('item', name) for name in roots)
    seen, selected, edges, obligations = set(), {}, [], []
    overlaps = set(bn_candidates)
    while pending:
        key = pending.popleft()
        if key in seen:
            continue
        seen.add(key)
        matches = index.get(key, [])
        if not matches:
            obligations.append({'namespace': key[0], 'id': key[1],
                                'status': 'resolve_against_pinned_BN' if key[1] in overlaps
                                else 'source_definition_not_in_candidate_archive'})
            continue
        if len(matches) != 1:
            raise ValueError(f'Ambiguous typed definition: {key}: {len(matches)} matches')
        path, position, entry = matches[0]
        selected[key] = {'source': path, 'position': position, 'definition': entry}
        if key[0] != 'item':
            continue  # Support definitions are preserved; their schemas need separate resolvers.
        for target, identifier, field in references(entry):
            child = (target, identifier)
            edges.append({'from': list(key), 'to': list(child), 'field': field})
            pending.append(child)
    nodes = [{'namespace': key[0], 'id': key[1], **value} for key, value in sorted(selected.items())]
    return {'roots': list(roots), 'nodes': nodes, 'edges': sorted(edges, key=lambda e: (e['from'], e['field'], e['to'])),
            'obligations': sorted(obligations, key=lambda e: (e['namespace'], e['id'])),
            'support_definition_schema_review_required': sorted({node['namespace'] for node in nodes if node['namespace'] != 'item'}),
            'release_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    raw = gzip.decompress(base64.b64decode((root / 'dependencies/dependencies.json.gz.base64').read_text()))
    manifest = json.loads((root / 'dependencies/DEPENDENCIES.json').read_text())
    if hashlib.sha256(raw).hexdigest() != manifest['payload_sha256']:
        raise ValueError('Preserved dependency payload checksum mismatch')
    files = json.loads(raw)
    baseline_path = root / 'quest_dependencies/BN_REFERENCE_SNAPSHOT.json'
    if baseline_path.exists():
        for snapshot in json.loads(baseline_path.read_text()):
            files['BN/' + snapshot['source']] = snapshot['definitions']
    report = build(files, bn_candidates=manifest['existing_BN_candidates_for_semantic_review'])
    report['source_sha256'] = manifest['payload_sha256']
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'QUEST_ITEM_GRAPH.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"Typed graph: {len(report['nodes'])} definitions, {len(report['edges'])} edges, {len(report['obligations'])} explicit resolution obligations")


if __name__ == '__main__':
    main()
