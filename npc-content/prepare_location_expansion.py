#!/usr/bin/env python3
"""Reconcile existing BN sites; only the reviewed nuclear shoreline is installed."""
import base64
import copy
import difflib
import gzip
import hashlib
import json
from pathlib import Path

from prepare_community_layers import ROOT as LAYERS, read_bundle

ROOT = Path(__file__).resolve().parent / 'location_expansion'
NUCLEAR = 'data/json/overmap/overmap_special/nuclear_plant.json'
BN_PIN = 'c621aaf42fa182473aad10feea2b55647704dcf1'
DDA_PIN = 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'


def sources():
    raw = gzip.decompress(base64.b64decode((ROOT / 'SOURCE_BUNDLE.json.gz.base64').read_bytes(), validate=True))
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
    if hashlib.sha256(raw).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Location source bundle checksum mismatch')
    files = json.loads(raw)
    if set(files) != set(manifest['files']):
        raise ValueError('Location source manifest mismatch')
    for path, text in files.items():
        if hashlib.sha256(text.encode()).hexdigest() != manifest['files'][path]['sha256']:
            raise ValueError('Location source drift: ' + path)
    return files


def cells(special):
    result = {}
    for cell in special['overmaps']:
        key = tuple(cell['point'])
        if key in result:
            raise ValueError('Duplicate special cell: ' + str(key))
        result[key] = cell
    return result


def delta(baseline, incoming):
    old, new = cells(baseline), cells(incoming)
    return {
        'added': [v for k, v in new.items() if k not in old],
        'changed': [{'baseline': old[k], 'source': v} for k, v in new.items() if k in old and old[k] != v],
        'baseline_only': [v for k, v in old.items() if k not in new],
    }


def semantic_diff(old, new, path=''):
    if isinstance(old, dict) and isinstance(new, dict):
        return [d for key in sorted(old.keys() | new.keys())
                for d in semantic_diff(old.get(key), new.get(key), path + '/' + key)]
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [{'path': path, 'baseline_count': len(old), 'source_count': len(new)}]
        return [d for i, (a, b) in enumerate(zip(old, new))
                for d in semantic_diff(a, b, path + '/' + str(i))]
    return [] if old == new else [{'path': path, 'baseline': old, 'source': new}]


def nuclear_merge(baseline, incoming):
    """24 water cells only. Keep BN reactors, trains, loot and placement policy."""
    if len(baseline) != 1 or baseline[0].get('id') != 'nuclear power plant':
        raise ValueError('Unexpected BN nuclear special')
    changes = delta(baseline[0], incoming[0])
    water = [c for c in changes['added'] if c.get('overmap', '').startswith('river_')]
    expected = {(x, y, 0): 'river_west' if x == 2 else 'river_east' if x == 13 else 'river_south'
                for y in (8, 9) for x in range(2, 14)}
    if {tuple(c['point']): c['overmap'] for c in water} != expected or len(water) != 24:
        raise ValueError('Re-review changed DDA nuclear shoreline')
    result = copy.deepcopy(baseline)
    result[0]['overmaps'].extend(copy.deepcopy(water))
    cells(result[0])
    return result, water, changes


def nuclear_patch():
    files = sources()
    text = files['bn/' + NUCLEAR]
    baseline = json.loads(text)
    merged, water, changes = nuclear_merge(baseline, json.loads(files['dda/' + NUCLEAR]))
    anchor = '\n    ],\n    "connections":'
    if text.count(anchor) != 1:
        raise ValueError('Re-review nuclear source formatting')
    additions = ''.join(',\n      { "point": [ %d, %d, %d ], "overmap": "%s" }' % (*c['point'], c['overmap']) for c in water)
    output = text.replace(anchor, additions + anchor)
    if json.loads(output) != merged:
        raise ValueError('Nuclear minimal patch mismatch')
    patch = ''.join(difflib.unified_diff(text.splitlines(keepends=True), output.splitlines(keepends=True), 'a/' + NUCLEAR, 'b/' + NUCLEAR))
    return patch, output, changes


def prepare():
    files = sources()
    patch, output, changes = nuclear_patch()
    (ROOT / 'merged').mkdir(exist_ok=True)
    (ROOT / 'merged/nuclear_plant.json').write_text(output)
    nuclear_report = {
        'operation': 'replace_existing_special', 'id': 'nuclear power plant',
        'native_patch': True, 'runtime_validated': False,
        'baseline_cells': len(json.loads(files['bn/' + NUCLEAR])[0]['overmaps']),
        'merged_cells': len(json.loads(output)[0]['overmaps']),
        'installed_change': '24 DDA shoreline cells using existing BN rotated river terrain',
        'preserved': ['all BN buildings and underground levels', 'BN power grid and reactor mechanics',
                      'occurrence and location constraints', 'all road connections', 'all BN palettes and mapgen'],
        'deferred': {**changes, 'added': [c for c in changes['added'] if not c.get('overmap', '').startswith('river_')]},
        'source_file_differences': {
            path[4:]: semantic_diff(json.loads(files['bn/' + path[4:]]), json.loads(text))
            for path, text in files.items() if path.startswith('dda/')},
    }
    # The full Hub geometry is a candidate, not a second special or a runnable mod.
    bundle = read_bundle(LAYERS)
    special_path = 'data/json/overmap/overmap_special/specials.json'
    old = next(e for e in json.loads(bundle['bn/' + special_path]) if e.get('id') == 'hub_01')
    new = next(e for e in json.loads(bundle['dda/' + special_path]) if e.get('id') == 'hub_01')
    changes = delta(old, new)
    candidate = copy.deepcopy(old)
    # Incoming cells replace geometry at the same coordinate. BN-only cells are retained
    # and explicitly reported for review, never silently removed.
    combined = cells(old)
    combined.update(cells(new))
    candidate['overmaps'] = list(combined.values())
    candidate_dir = ROOT / 'hub_candidate'
    candidate_dir.mkdir(exist_ok=True)
    (candidate_dir / 'hub_01_special.json').write_text(json.dumps([candidate], indent=2) + '\n')
    paths = ['data/json/mapgen/robofachq_static.json',
             'data/json/mapgen/robofaq_locs/robofac_hq_chunks.json',
             'data/json/mapgen/robofaq_locs/robofac_mission_chunks.json',
             'data/json/mapgen_palettes/robofachq.json',
             'data/json/overmap/overmap_terrain/overmap_terrain_robofachq.json']
    for path in paths:
        (candidate_dir / Path(path).name).write_text(bundle['dda/' + path])
    basement = [c for c in new['overmaps'] if c['point'][2] == -1]
    report = {'bn_pin': BN_PIN, 'dda_pin': DDA_PIN, 'nuclear': nuclear_report,
              'hub': {'operation': 'replace_existing_special_and_mapgen', 'native_patch': False,
                      'installable': False, 'baseline_cells': len(old['overmaps']),
                      'source_cells': len(new['overmaps']), 'candidate_cells': len(combined),
                      'changes': changes, 'new_z_minus_1': basement,
                      'retained_policy': {k: v for k, v in old.items() if k != 'overmaps'},
                      'candidate_source_files': paths,
                      'required_before_install': ['review BN-only geometry against new larger maps',
                          'resolve palette/item/monster/NPC dependencies',
                          'adapt DDA mapgen and overmap terrain schemas',
                          'review elevators and stairs across every affected floor',
                          'native data loading, generation and save/reload tests'],
                      'note': 'z=-1 contains the foyer/security/control rooms, not the residential floor'}}
    (ROOT / 'LOCATION_EXPANSION_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = prepare()
    print('Nuclear shoreline: 24 existing-terrain cells; Hub replacement candidate: %d cells, not installed' % report['hub']['candidate_cells'])
