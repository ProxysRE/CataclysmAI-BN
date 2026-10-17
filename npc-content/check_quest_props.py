#!/usr/bin/env python3
"""Check the demilled item's bounded adaptation and explicit metadata retention."""
import copy
import json
from pathlib import Path
import tempfile

from prepare_quest_props import adapt_demilled, check_baseline, check_generated, native_price
from prepare_quest_usb import verified_graph


def check():
    check_generated()
    source = next(n['definition'] for n in verified_graph()['nodes'] if n['namespace'] == 'item' and n['id'] == 'broken_kord')
    items, report = adapt_demilled(source)
    result, = items
    assert result['name'] == source['variants'][0]['name']
    for key in ('id', 'description', 'flags', 'material', 'weight', 'volume', 'category'):
        assert result[key] == source[key]
    assert report['unrepresented_dimensions']['longest_side'] == source['longest_side']
    assert report['legacy_source_name'] == source['name']
    assert report['source_variants'] == source['variants']
    assert native_price('2 kUSD 500 USD') == '2500 USD'
    assert native_price('1 USD 25 cent') == '125 cent'
    for change in ('extra_variant', 'mechanical_variant'):
        modified = copy.deepcopy(source)
        if change == 'extra_variant':
            modified['variants'].append(dict(modified['variants'][0], id='different'))
        else:
            modified['variants'][0]['weight'] = '100 g'
        try:
            adapt_demilled(modified)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsupported variant accepted: ' + change)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / 'data/json/items/test.json'
        path.parent.mkdir(parents=True)
        fallback = {'type': 'GUN', 'id': 'ak47'}
        path.write_text(json.dumps([fallback]))
        check_baseline(root)
        path.write_text(json.dumps([fallback, {'type': 'GENERIC', 'id': 'broken_kord'}]))
        try:
            check_baseline(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Duplicate demilled rifle was accepted')
    print('PASS: quest prop field fidelity, retained presentation/dimensions, variant and baseline guards')


if __name__ == '__main__':
    check()
