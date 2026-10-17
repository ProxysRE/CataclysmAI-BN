#!/usr/bin/env python3
"""Adapt two quest USB items by inheriting the existing BN USB definition."""
import argparse
import copy
import json
from pathlib import Path
from quest_dependency_graph import ITEM_TYPES, build, read_source_files

ROOT = Path(__file__).resolve().parent
IDS = ('usb_drive_nano', 'nano_fabricator_encryption_code')


def definitions():
    graph = json.loads((ROOT / 'quest_dependencies/QUEST_ITEM_GRAPH.json').read_text(encoding='utf-8'))
    files, manifest = read_source_files(ROOT)
    regenerated = build(files, bn_candidates=manifest['existing_BN_candidates_for_semantic_review'])
    regenerated['source_sha256'] = manifest['payload_sha256']
    if graph != regenerated:
        raise ValueError('Quest graph differs from its checksum-verified source archive')
    source = {n['id']: n['definition'] for n in graph['nodes'] if n['namespace'] == 'item'}
    result = []
    for identifier in IDS:
        entry = copy.deepcopy(source[identifier])
        if entry['type'] != 'ITEM' or 'subtypes' in entry or 'pocket_data' in entry or 'variants' in entry:
            raise ValueError('Re-review changed USB item schema: ' + identifier)
        if entry['copy-from'] != ('usb_drive' if identifier == 'usb_drive_nano' else 'usb_drive_nano'):
            raise ValueError('Re-review changed USB inheritance: ' + identifier)
        entry['type'] = 'GENERIC'
        result.append(entry)
    return result


def check_baseline(bn_source):
    found = {}
    for path in (bn_source / 'data/json/items').rglob('*.json'):
        entries = json.loads(path.read_text(encoding='utf-8'))
        for entry in entries:
            if not isinstance(entry, dict) or entry.get('type') not in ITEM_TYPES:
                continue
            identifier = entry.get('id', entry.get('abstract'))
            identifiers = identifier if isinstance(identifier, list) else [identifier]
            for value in identifiers:
                if value in (*IDS, 'usb_drive'):
                    if value in found:
                        raise ValueError('Duplicate baseline USB identity: ' + value)
                    found[value] = entry
    if any(identifier in found for identifier in IDS):
        raise ValueError('Quest USB ID already exists in BN; merge instead of adding')
    if 'usb_drive' not in found:
        raise ValueError('Missing original BN USB parent')
    graph = json.loads((ROOT / 'quest_dependencies/QUEST_ITEM_GRAPH.json').read_text(encoding='utf-8'))
    expected = next(n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] == 'usb_drive')
    if found['usb_drive'] != expected:
        raise ValueError('BN USB parent differs from the reviewed baseline')


def check_generated():
    path = ROOT / 'native/dda_quest_usb.json'
    if json.loads(path.read_text(encoding='utf-8')) != definitions():
        raise ValueError('Stale generated quest USB definitions')
    print('PASS: both quest USB items preserve source fields and inherit BN USB behavior')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    if args.bn_source:
        check_baseline(args.bn_source)
        print('PASS: full BN item catalog has no USB ID conflicts; original parent matches')
    if args.check:
        check_generated()
    else:
        (ROOT / 'native/dda_quest_usb.json').write_text(json.dumps(definitions(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
