#!/usr/bin/env python3
"""Adapt XEDRA suit states to BN's existing Hub suit; preserve advanced respirator sources."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from prepare_rural_churches import sources as church_sources
from prepare_quest_usb import scan_bn_items

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'xedra_gear'
PAYLOAD = 'data/json/items/dda_xedra_activity_suits.json'
IDS = ('xedra_enviro_suit', 'xedra_enviro_suit_casual')


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    raw = gzip.decompress(base64.b64decode(b''.join((FOLDER / p).read_bytes() for p in manifest['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for name, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][name]
    return files


def definitions():
    files = church_sources()
    source = json.loads(files['dda/suits_protection.json'])
    index = {e['id']: e for e in source if isinstance(e.get('id'), str)}
    result = [copy.deepcopy(index[name]) for name in IDS]
    for e in result:
        assert e.pop('subtypes') == ['ARMOR']
        e['type'] = 'ARMOR'
    assert result[0]['copy-from'] == 'robofac_enviro_suit'
    assert result[1]['copy-from'] == 'robofac_enviro_suit_casual'
    # BN has the protective Hub suit but no casual variant. Reuse the real BN
    # armor stats and remove upper-body coverage and the source's four seal flags.
    result[1]['copy-from'] = 'xedra_enviro_suit'
    result[1]['covers'] = ['legs', 'feet']
    result[1]['delete'] = copy.deepcopy(index['robofac_enviro_suit_casual']['delete'])
    assert set(result[1]['delete']['flags']) == {'RAINPROOF', 'GAS_PROOF', 'RAD_PROOF', 'ELECTRIC_IMMUNE'}
    return result


def prepare(check=False, bn_source=None):
    if bn_source:
        baseline = json.loads(sources()['bn/suits_protection.json'])
        parent = next(e for e in baseline if e.get('id') == 'robofac_enviro_suit')
        found = scan_bn_items(bn_source, (*IDS, 'robofac_enviro_suit', 'leather_belt', 'mask_dust', 'medium_battery_cell', 'heavy_battery_cell'))
        for name in ('leather_belt', 'mask_dust', 'medium_battery_cell', 'heavy_battery_cell'):
            if name not in found:
                raise ValueError('Missing reviewed BN reuse candidate: ' + name)
        if any(name in found for name in IDS):
            raise ValueError('XEDRA activity suit already exists in BN')
        if found.get('robofac_enviro_suit') != parent:
            raise ValueError('BN protective Hub suit differs from the reviewed baseline')
    text = json.dumps(definitions(), ensure_ascii=True, indent=2) + '\n'
    target = ROOT / 'native/dda_xedra_activity_suits.json'
    if check:
        assert target.read_text(encoding='utf-8') == text
    else:
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
