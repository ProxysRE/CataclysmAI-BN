#!/usr/bin/env python3
"""Build reviewed replacements from BN maps, never additive duplicate map variants."""
import copy
import hashlib
import json
from pathlib import Path

from prepare_community_layers import ROOT, read_bundle


def load_support(root):
    folder = root / 'merge_sources'
    manifest = json.loads((folder / 'MANIFEST.json').read_text())
    result = {}
    for name, metadata in manifest.items():
        raw = (folder / name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != metadata['git_blob_sha']:
            raise ValueError('Reviewed palette checksum mismatch: ' + name)
        result[name] = json.loads(raw)
    return result


def merge_chemist(baseline, source, support):
    """Carry over DDA's occupied chair, retain the BN roof and all other map data."""
    merged = copy.deepcopy(baseline)
    target = next(e for e in merged if e.get('om_terrain') == ['chemical_lab_ocu'])
    original = target['object']
    incoming = next(e for e in source if e.get('om_terrain') == ['chemical_lab_ocu'])['object']
    placement, = incoming['place_npcs']
    if placement != {'class': 'NPC_cabin_chemist', 'x': 16, 'y': 8}:
        raise ValueError('Re-review changed DDA chemist placement')
    if original.get('npcs') != {'@': {'class': 'NPC_cabin_chemist'}}:
        raise ValueError('Re-review changed BN chemist placement')
    cells = [(x, y) for y, row in enumerate(original['rows'])
             for x, symbol in enumerate(row) if symbol == '@']
    if cells != [(16, 8)] or 'place_npcs' in original:
        raise ValueError('Chemist must occur exactly once at the reviewed coordinate')
    for name in ('bn_cabin.json', 'dda_cabin.json'):
        palette = next(e for e in support[name] if e.get('id') == 'cabin_palette')
        if palette['furniture'].get('c') != 'f_chair':
            raise ValueError('Re-review chair semantics in ' + name)
    if incoming['rows'][8][16] != 'c':
        raise ValueError('DDA chemist no longer occupies a chair')
    row = original['rows'][8]
    original['rows'][8] = row[:16] + 'c' + row[17:]
    del original['npcs']
    original['place_npcs'] = [copy.deepcopy(placement)]
    return merged


def prepare(root=ROOT):
    files = read_bundle(root)
    support = load_support(root)
    baseline_path = 'bn/data/json/mapgen/chemical_lab.json'
    source_path = 'dda/data/json/mapgen/chemist_holdout/chemical_lab.json'
    baseline = json.loads(files[baseline_path])
    source = json.loads(files[source_path])
    merged = merge_chemist(baseline, source, support)
    text = files[baseline_path]
    replacements = {
        '"......-~~#A     @ #~-..."': '"......-~~#A     c #~-..."',
        '"npcs": { "@": { "class": "NPC_cabin_chemist" } }':
            '"place_npcs": [ { "class": "NPC_cabin_chemist", "x": 16, "y": 8 } ]',
    }
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise ValueError('BN map formatting changed; re-review minimal replacement')
        text = text.replace(old, new)
    if json.loads(text) != merged:
        raise ValueError('Minimal map patch differs from the reviewed semantic merge')
    destination = root / 'merged' / 'chemical_lab.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    report = {
        'release_ready': False,
        'runtime_validated': False,
        'included_in_native_patch': True,
        'installation': 'Replace the original BN mapgen file; never load this beside it',
        'target': 'data/json/mapgen/chemical_lab.json',
        'baseline': baseline_path,
        'source': source_path,
        'changes': ['DDA chair at (16,8)', 'One explicit chemist spawn at the original BN position'],
        'preserved': ['Every BN map variant including the roof', 'BN heater symbol at (12,13)',
                      'Groundcover probabilities', 'Palettes, stock, faction ownership',
                      'Existing overmap special and occurrence frequency'],
        'deferred_source_zones': source[0]['object']['place_zones'],
        'deferred_reason': 'Zone IDs and shop consumers require native compatibility review',
        'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    }
    (root / 'EXISTING_LOCATION_MERGES.json').write_text(json.dumps(report, indent=2) + '\n')
    return baseline, source, merged, support


if __name__ == '__main__':
    prepare()
    print('Prepared one replacement map file; no new location or NPC occurrence added')
