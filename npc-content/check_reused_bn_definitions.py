#!/usr/bin/env python3
"""Verify all selected reused BN definitions by typed identity and full content."""
import argparse
import json
from pathlib import Path
import tempfile

from prepare_quest_usb import verified_graph
from quest_dependency_graph import ids, namespace


def check_baseline(source, nodes=None):
    if nodes is None:
        nodes = verified_graph()['nodes']
    indexes = {}
    count = 0
    for node in nodes:
        if not node['source'].startswith('BN/'):
            continue
        relative = node['source'][3:]
        if relative not in indexes:
            entries = json.loads((source / relative).read_text(encoding='utf-8'))
            index = {}
            for entry in entries:
                for identifier in ids(entry):
                    index.setdefault((namespace(entry), identifier), []).append(entry)
            indexes[relative] = index
        matches = indexes[relative].get((node['namespace'], node['id']), [])
        if len(matches) != 1 or matches[0] != node['definition']:
            raise ValueError('Reused BN definition differs or is ambiguous: ' + str((node['namespace'], node['id'])))
        count += 1
    return count


def check_fixture():
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)
        parent = source / 'data/json/items/gun/shared.json'
        parent.parent.mkdir(parents=True)
        fault = {'type': 'fault', 'id': 'shared', 'description': 'stock fault'}
        item = {'type': 'GENERIC', 'id': 'shared', 'name': 'different namespace'}
        parent.write_text(json.dumps([fault, item]))
        nodes = [{'source': 'BN/data/json/items/gun/shared.json', 'namespace': kind,
                  'id': 'shared', 'definition': definition}
                 for kind, definition in [('fault', fault), ('item', item)]]
        assert check_baseline(source, nodes) == 2
        parent.write_text(json.dumps([dict(fault, description='changed'), item]))
        try:
            check_baseline(source, nodes)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed fault was confused with same-named item')
    print('PASS: typed BN reuse distinguishes fault/item identities and rejects baseline drift')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    if args.bn_source:
        print(f'PASS: {check_baseline(args.bn_source)} reused BN definitions match the pinned catalog')
    else:
        check_fixture()
