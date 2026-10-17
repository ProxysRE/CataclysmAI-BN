#!/usr/bin/env python3
"""Prepare the 5.45 casing using BN's existing generic casing implementation."""
import argparse
import copy
import json
from pathlib import Path

from prepare_quest_usb import ROOT, scan_bn_items, verified_graph


def definitions():
    graph = verified_graph()
    source = next(n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] == '545_casing')
    if source.get('type') != 'ITEM' or source.get('copy-from') != 'casing' or source.get('looks_like') != '9mm_casing':
        raise ValueError('Re-review changed 5.45 casing source schema')
    result = copy.deepcopy(source)
    result['type'] = 'GENERIC'
    return [result]


def check_baseline(bn_source):
    found = scan_bn_items(bn_source, ('545_casing', 'casing', '9mm_casing'))
    if '545_casing' in found:
        raise ValueError('5.45 casing already exists in BN; merge instead of adding')
    graph = verified_graph()
    for identifier in ('casing', '9mm_casing'):
        expected = next(n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] == identifier)
        if found.get(identifier) != expected:
            raise ValueError('BN casing parent or visual fallback changed: ' + identifier)


def check_generated():
    if json.loads((ROOT / 'native/dda_545_casing.json').read_text(encoding='utf-8')) != definitions():
        raise ValueError('Stale generated 5.45 casing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    if args.bn_source:
        check_baseline(args.bn_source)
        print('PASS: full BN item scan has no 5.45 casing conflict; parent and visual fallback match')
    if args.check:
        check_generated()
        print('PASS: 5.45 casing preserves source fields and uses stock BN casing inheritance')
    else:
        (ROOT / 'native/dda_545_casing.json').write_text(json.dumps(definitions(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
