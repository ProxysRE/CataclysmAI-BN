#!/usr/bin/env python3
"""Project the demilled quest rifle onto the existing BN generic item schema."""
import argparse
import copy
import json
import re
from pathlib import Path

from prepare_quest_usb import ROOT, scan_bn_items, verified_graph


def native_price(value):
    compact = re.sub(r'\s+', '', value)
    terms = list(re.finditer(r'(\d+)(kUSD|USD|cent)', compact))
    if not terms or ''.join(m.group() for m in terms) != compact:
        raise ValueError('Unsupported source quest-prop price')
    cents = sum(int(m[1]) * {'kUSD': 100000, 'USD': 100, 'cent': 1}[m[2]] for m in terms)
    return f'{cents // 100} USD' if cents % 100 == 0 else f'{cents} cent'


def adapt_demilled(source):
    if source.get('id') != 'broken_kord' or source.get('type') != 'ITEM':
        raise ValueError('Unexpected demilled quest item')
    result = copy.deepcopy(source)
    variants = result.pop('variants', [])
    if len(variants) != 1 or variants[0].get('id') != source['id']:
        raise ValueError('Multiple or renamed variants require separate support')
    variant = variants[0]
    if set(variant) != {'id', 'name', 'description'} or result.pop('variant_type', None) != 'gun':
        raise ValueError('Mechanical or extended variant fields require separate support')
    if variant['description'] != source['description']:
        raise ValueError('Changed variant description requires review')
    result['name'] = copy.deepcopy(variant['name'])
    length = result.pop('longest_side')
    result['type'] = 'GENERIC'
    result['looks_like'] = 'ak47'
    result['price'] = native_price(source['price'])
    report = {
        'id': source['id'],
        'native_kind': 'BN generic quest prop, not a usable gun',
        'name_policy': 'Use the sole source model name; BN has no SHOW_GUN_VARIANTS option',
        'legacy_source_name': source['name'],
        'source_variants': source['variants'],
        'source_variant_type': source['variant_type'],
        'unrepresented_dimensions': {'longest_side': length},
        'dimension_policy': 'BN uses its existing volume model; source length retained for future pocket work',
        'visual_fallback': {'source': source['looks_like'], 'BN': 'ak47'},
        'price_conversion': {'source': source['price'], 'BN': result['price']},
        'runtime_validated': False,
    }
    return [result], report


def definitions():
    graph = verified_graph()
    source = next(n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] == 'broken_kord')
    return adapt_demilled(source)


def check_baseline(bn_source):
    found = scan_bn_items(bn_source, ('broken_kord', 'ak47'))
    if 'broken_kord' in found:
        raise ValueError('Demilled Kord already exists in BN; merge instead')
    if found.get('ak47', {}).get('type') != 'GUN':
        raise ValueError('Missing stock BN rifle visual fallback')


def check_generated():
    items, report = definitions()
    for path, expected in [('native/dda_quest_props.json', items),
                           ('quest_dependencies/QUEST_PROP_PORT_REPORT.json', report)]:
        if json.loads((ROOT / path).read_text(encoding='utf-8')) != expected:
            raise ValueError('Stale generated quest prop: ' + path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    if args.bn_source:
        check_baseline(args.bn_source)
        print('PASS: full BN item scan has no demilled Kord collision; visual fallback exists')
    if args.check:
        check_generated()
        print('PASS: demilled quest item and explicit variant/dimension report match source')
    else:
        items, report = definitions()
        (ROOT / 'native/dda_quest_props.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (ROOT / 'quest_dependencies/QUEST_PROP_PORT_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
