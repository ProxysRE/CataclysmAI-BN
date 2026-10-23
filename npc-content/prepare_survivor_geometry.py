#!/usr/bin/env python3
"""Stage survivor housing and Lacroix shells, retaining vertical blockers."""
import argparse
import copy
import hashlib
import itertools
import json
from collections import Counter
from fractions import Fraction

from prepare_geometry_layer import ROOT, OUT, extract, glyphs
from prepare_regional_locations import expand, flatten, index_entries, references
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'survivor_sources'
PIN = 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
TARGETS = {'Cabin_prepper', 'cabin_liam', 'survivor_forest_camp',
           'Locked LMOE Shelter', 'cemetery_lacroix'}
MAPS = {'cabin_prepper', 'cabin_prepper_shelter', 'cabin_roof_1', 'cabin_liam',
        'lmoe', 'lmoe_under_empty_prepperquest', 'survivor_forest_camp',
        'cemetery_4square_00_lacroix', 'cemetery_4square_10_lacroix',
        'cemetery_4square_01_lacroix', 'cemetery_4square_11_lacroix',
        'cemetery_4square_11_roof'}
STRUCTURAL = {'leather_tent_5x5_S', 'leather_tent_b_5x5_S',
              'leather_tent_b_5x5_N', 'tent_5x5_roof',
              'lmoe_exit_prepperquest_n', 'lmoe_exit_roof_n'}


def sources():
    manifest = json.loads((SOURCE / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['dda_commit'] == PIN
    files = {}
    for path, record in manifest['files'].items():
        raw = (SOURCE / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == record['blob_sha'], path
        files[path] = json.loads(raw)
    shared = shared_sources()
    root = OUT / 'research_sources'
    record = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    assert record['dda_commit'] == PIN
    path = 'data/json/mapgen/nested/rural_outdoors_nested.json'
    raw = (root / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record['files'][path]
    files[path] = json.loads(raw)
    palettes = {e['id']: e for p, es in shared.items() if p.startswith('dda/')
                for e in es if e.get('type') == 'palette'}
    palettes.update({e['id']: e for es in files.values() for e in es if e.get('type') == 'palette'})
    return files, palettes, {'archive': 'research_sources', 'path': path,
                             'sha256': record['files'][path]}


def variants(source, palettes):
    """Keep a whole-palette draw correlated across every glyph in its map."""
    choices = []
    for palette in source['object'].get('palettes', []):
        if isinstance(palette, str):
            choices.append([(palette, Fraction(1))])
        else:
            assert set(palette) == {'distribution'}, palette
            total = sum(weight for name, weight in palette['distribution'])
            choices.append([(name, Fraction(weight, total)) for name, weight in palette['distribution']])
    for selection in itertools.product(*choices):
        entry = copy.deepcopy(source)
        entry['object']['palettes'] = [name for name, weight in selection]
        raw_weight = source.get('weight', 1000)
        if isinstance(raw_weight, dict):
            assert all(probability == 1 for name, probability in selection)
            weight = raw_weight
        else:
            weight = Fraction(raw_weight)
            for name, probability in selection:
                weight *= probability
            assert weight.denominator == 1, weight
            weight = int(weight)
        if any(not isinstance(p, str) for p in source['object'].get('palettes', [])):
            entry['weight'] = weight
        entry['object'] = expand(entry['object'], palettes)
        assert not entry['object'].get('palettes'), entry['object'].get('palettes')
        yield entry, {'source': source.get('om_terrain', source.get('nested_mapgen_id')),
                      'palettes': [name for name, probability in selection], 'weight': weight}


def prepare(check=False):
    files, palettes, reused = sources()
    originals = [copy.deepcopy(e) for es in files.values() for e in es
                 if e.get('type') == 'mapgen' and (
                     set(flatten(e.get('om_terrain', []))) & MAPS or
                     e.get('nested_mapgen_id') in STRUCTURAL)]
    assert {e['nested_mapgen_id'] for e in originals if 'nested_mapgen_id' in e} == STRUCTURAL
    expanded = []; selections = []; later = []
    for source in originals:
        for entry, selection in variants(source, palettes):
            o = entry['object']
            for glyph, piece in o.get('mapping', {}).items():
                for key in ('terrain', 'furniture'):
                    if key in piece:
                        o.setdefault(key, {})[glyph] = copy.deepcopy(piece[key])
            # Structural furniture-only overlays must preserve the underlying tile.
            if 'fill_ter' not in o:
                for glyph in glyphs(o.get('rows', [])) - set(o.get('terrain', {})) - set(o.get('furniture', {})) - set(o.get('nested', {})) - {' ', '.'}:
                    assert 'nested_mapgen_id' in entry or o.get('fallback_predecessor_mapgen'), (entry.get('om_terrain'), glyph)
                    o.setdefault('furniture', {})[glyph] = 'f_null'
            expanded.append(entry); selections.append(selection)
    catalog, _ = read_sources(); registrations = []
    for path, text in catalog.items():
        if not path.startswith('dda/'):
            continue
        for source in json.loads(text):
            if source.get('type') == 'overmap_special' and source.get('id') in TARGETS:
                registrations.append(copy.deepcopy(source)); expanded.append(copy.deepcopy(source))
            elif source.get('type') == 'overmap_terrain':
                names = set(flatten(source.get('id', []))) & MAPS
                if names:
                    entry = copy.deepcopy(source); entry['id'] = sorted(names); expanded.append(entry)
    assert {e['id'] for e in registrations} == TARGETS
    entries, deferred, issues = extract(expanded, tuple(sorted(STRUCTURAL)))
    later.extend(deferred)
    for source, entry in zip(expanded, entries):
        if entry['type'] == 'mapgen':
            assert source['object'].get('rows') == entry['object'].get('rows')
            if isinstance(entry.get('weight'), dict):
                issues.append({'type': 'dynamic_mapgen_weight_needs_BN_adaptation',
                               'source': entry.get('om_terrain'), 'weight': entry['weight']})
            if source.get('nested_mapgen_id') in STRUCTURAL:
                entry['object']['furniture'] = copy.deepcopy(source['object'].get('furniture', {}))
                if not entry['object']['furniture']:
                    del entry['object']['furniture']
            if 'fallback_predecessor_mapgen' in source['object']:
                issues.append({'type': 'fallback_predecessor_needs_BN_adaptation',
                               'source': source.get('om_terrain'),
                               'value': source['object']['fallback_predecessor_mapgen']})
        elif entry['type'] == 'overmap_special':
            later.append({'source_registration': source})
            entry['occurrences'] = [0, 0]
            if 'priority' in entry:
                later.append({'source': entry['id'], 'field': 'priority', 'value': entry.pop('priority')})
    # Preserve all non-selected source objects, including quest signs and actors.
    later.extend({'path': path, 'source_definition': e} for path, es in files.items() for e in es
                 if e.get('type') != 'mapgen' or not (
                     set(flatten(e.get('om_terrain', []))) & MAPS or e.get('nested_mapgen_id') in STRUCTURAL))
    own = index_entries(entries)
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    assert {n for e in entries for n in flatten(e.get('om_terrain', []))} == MAPS
    for e in entries:
        if 'om_terrain' in e:
            omt = e['om_terrain']; matrix = [[omt]] if isinstance(omt, str) else [omt] if isinstance(omt[0], str) else omt
            rows = e['object']['rows']
            assert len(rows) == 24 * len(matrix) and all(len(row) == 24 * len(matrix[0]) for row in rows)
    report = {'status': 'survivor_and_lacroix_staged_with_vertical_blockers',
              'native_embedded': False, 'runtime_validated': False,
              'definitions': dict(Counter(e['type'] for e in entries)),
              'world_maps': sum('om_terrain' in e for e in entries),
              'unique_omt': len(MAPS), 'structural_nested_ids': sorted(STRUCTURAL),
              'special_cells': {e['id']: sum('overmap' in c for c in e['overmaps']) for e in registrations},
              'source_z_levels': {e['id']: sorted({c['point'][2] for c in e['overmaps'] if 'overmap' in c}) for e in registrations},
              'palette_variants': selections, 'reused_source': reused,
              'unresolved_typed_refs': sorted(required(entries) - own - core),
              'core_identity_intersections': sorted(own & core),
              'bundled_mod_identity_intersections': sorted(own & mods),
              'geometry_issues': issues, 'source_rows_preserved': True,
              'limits': ['Not installed or embedded; no completion credit',
                         'Original identifiers can overlap BN: isolate missing variants or extend existing sites before installation',
                         'Upward LMOE exit and roof placements must be adapted explicitly; never discard them',
                         'Intact leather tent roof uses unsupported nested z=1; ruined tent variants intentionally have no roof',
                         'Parameter terrain, regional groundcover and fallback predecessors need BN adaptation',
                         'Furniture, loot, actors and quest signs remain archived for later layers']}
    for name, value in [('SURVIVOR_SHELLS.json', entries), ('SURVIVOR_LATER_LAYERS.json', later), ('SURVIVOR_GEOMETRY_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check:
            assert path.read_text() == text, path
        else:
            path.write_text(text)
    print(json.dumps({k: report[k] for k in ('status', 'world_maps', 'unique_omt', 'special_cells', 'unresolved_typed_refs', 'geometry_issues')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
