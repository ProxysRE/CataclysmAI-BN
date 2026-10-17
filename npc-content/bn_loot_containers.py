#!/usr/bin/env python3
"""Translate DDA group-level packaging to BN item contents-group modifiers."""
import copy
import json
from pathlib import Path


def package_groups(entries):
    result = []
    for original in entries:
        if original.get('type') != 'item_group' or 'container-item' not in original:
            result.append(original)
            continue
        contents = copy.deepcopy(original)
        container = contents.pop('container-item')
        contents['id'] += '_contents'
        result.append({'type': 'item_group', 'id': original['id'], 'subtype': 'collection',
                       'entries': [{'item': container, 'contents-group': contents['id']}]})
        result.append(contents)
    return result


def check_source(bn_source=None):
    review = json.loads((Path(__file__).resolve().parent / 'counterparts/LOOT_SOURCE_REVIEW.json').read_text())
    assert review['bn_pin'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    assert 'container-item' not in review['load_item_group_excerpt']
    assert 'name + "-group"' in review['load_sub_ref_excerpt']
    if bn_source:
        actual = (bn_source / review['source_file']).read_text(encoding='utf-8')
        assert review['load_item_group_excerpt'] in actual
        assert review['load_sub_ref_excerpt'] in actual
    print('PASS: BN contents-group packing uses the pinned item factory API')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn-source', type=Path)
    check_source(p.parse_args().bn_source)
