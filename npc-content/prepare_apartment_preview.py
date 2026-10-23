#!/usr/bin/env python3
"""Prepare namespaced apartment payload and source-derived native expectations."""
import argparse
import collections
import copy
import hashlib
import json

from adapt_apartment_geometry import prepare as adapt
from prepare_apartment_geometry import OUT, ROOT
from prepare_regional_locations import flatten, index_entries, BUILTIN_IDS
from prepare_container_yards import required
from check_geometry_runtime_rules import sources as runtime_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache


def runtime_evidence():
    root = OUT / 'apartment_runtime_sources'
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['bn_commit'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    files = {}
    for path, info in manifest['files'].items():
        raw = (root / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == info['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == info['blob_sha'], path
        files[path] = raw.decode('utf-8')
    bn = runtime_sources()['bn/src/mapgen/mapgen.cpp']
    assert 'case direction::ABOVECENTER: return "above";' in files['bn/src/line.cpp']
    neighbor = files['bn/src/mapgen/mapgendata.cpp'].split('auto mapgendata::neighbor_at(direction', 1)[1]
    assert 'case direction::ABOVECENTER:\n            return above();' in neighbor
    check = bn.split('class neighbor_oter_check', 1)[1].split('class neighbor_join_check', 1)[0]
    assert 'all_enum_values<direction>()' in check and 'dat.neighbor_at(dir)' in check
    assert 'ot_match_type::contains' in check
    loader = bn.split('void load_mapgen(const JsonObject& jo)', 1)[1].split('mapgen_function_json_base::', 1)[0]
    assert 'load_and_add_mapgen_function(jo, mapgenid, offset, total);' in loader
    assert 'offset.x()++;' in loader and 'offset.x() = 0;' in loader
    add = bn.split('void load_and_add_mapgen_function(', 1)[1].split('static void load_nested_mapgen', 1)[0]
    assert 'oter_mapgen.add(id_base, f)' in add
    assert 'm_offset.x() = grid_offset.x() * mapgensize.x();' in bn
    return manifest


def matrix(e):
    omt = e['om_terrain']
    return [[omt]] if isinstance(omt, str) else [omt] if isinstance(omt[0], str) else omt


def singleton(value):
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value if isinstance(value, str) else None


def prepare(check=False):
    adapt(check=True)
    evidence = runtime_evidence()
    full = json.loads((OUT / 'APARTMENT_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    ar = json.loads((OUT / 'APARTMENT_ADAPTATION_REPORT.json').read_text(encoding='utf-8'))
    reachable = set(ar['reachable_nested_identities'])
    selected = [copy.deepcopy(e) for e in full if 'nested_mapgen_id' not in e or e['nested_mapgen_id'] in reachable]
    own_omt = {n for e in selected if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    aliases = {}
    for name in sorted(own_omt):
        aliases[name] = name if name.startswith('dda_geo_') else 'dda_geo_' + name
        for direction in ('north', 'east', 'south', 'west'):
            aliases[name + '_' + direction] = aliases[name] + '_' + direction
    for e in selected:
        if e['type'] == 'overmap_special':
            aliases[e['id']] = 'dda_geo_' + e['id'].lower()

    def rename(value):
        if isinstance(value, str):
            return aliases.get(value, value)
        if isinstance(value, list):
            return [rename(x) for x in value]
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        return value

    # This includes neighbors.above, not merely registration IDs. Otherwise BN
    # would look for the original DDA type above a namespaced preview garage.
    entries = rename(selected)
    own = index_entries(entries)
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    assert not (own - BUILTIN_IDS) & (core | mods)
    assert not required(entries) - own - core
    nested = collections.defaultdict(list)
    for e in entries:
        if 'nested_mapgen_id' in e:
            nested[e['nested_mapgen_id']].append(e)
    world = [e for e in entries if 'om_terrain' in e]
    variants = collections.defaultdict(list)
    conditional = collections.defaultdict(list)
    excluded = 0
    for e in world:
        obj = e['object']
        assert obj.get('rotation', 0) == 0
        grid = matrix(e)
        mask = set()
        for place in obj.get('place_nested', []):
            assert not place.get('z', 0), place
            refs = {n for t, n in required([{'type': 'mapgen', 'object': {'place_nested': [place]}}]) if t == 'nested_mapgen'}
            if place.get('neighbors'):
                assert set(place['neighbors']) == {'above'} and len(refs) == 1
                provider = nested[next(iter(refs))]
                assert len(provider) == 1 and provider[0]['object']['mapgensize'] == [1, 1]
                value = singleton(next(iter(provider[0]['object']['terrain'].values())))
                assert value == 't_stairs_up'
                x, y = place['x'], place['y']
                assert isinstance(x, int) and isinstance(y, int)
                conditional[grid[y // 24][x // 24]].append({'x': x % 24, 'y': y % 24,
                    'neighbors_above': place['neighbors']['above'], 'terrain': value,
                    'else_terrain': singleton(obj['terrain'][obj['rows'][y][x]])})
            sizes = [p['object']['mapgensize'] for n in refs for p in nested[n]]
            radius = max((max(size) for size in sizes), default=0)
            xr = place['x'] if isinstance(place['x'], list) else [place['x'], place['x']]
            yr = place['y'] if isinstance(place['y'], list) else [place['y'], place['y']]
            mask.update((x, y) for x in range(xr[0], xr[-1] + radius) for y in range(yr[0], yr[-1] + radius))
        # Used symbol nests also conservatively mask their full possible bounds.
        for y, row in enumerate(obj['rows']):
            for x, glyph in enumerate(row):
                if glyph not in obj.get('nested', {}):
                    continue
                piece = obj['nested'][glyph]
                refs = {n for t, n in required([{'type': 'mapgen', 'object': {'nested': {'x': piece}}}]) if t == 'nested_mapgen'}
                radius = max((max(p['object']['mapgensize']) for n in refs for p in nested[n]), default=0)
                mask.update((px, py) for px in range(x, x + radius) for py in range(y, y + radius))
        for gy, row in enumerate(grid):
            for gx, name in enumerate(row):
                points = set()
                for y in range(24):
                    for x in range(24):
                        px, py = gx * 24 + x, gy * 24 + y
                        glyph = obj['rows'][py][px]
                        value = singleton(obj.get('terrain', {}).get(glyph))
                        if not value or not any(part in value for part in ('stairs', 'ladder', 'ramp', 'elevator')):
                            continue
                        if (px, py) in mask:
                            excluded += 1
                            continue
                        points.add((x, y, value))
                variants[name].append({'source_slot': [gx, gy], 'points': points, 'weight': e.get('weight', 1000)})
    navigation = {name: [{'x': x, 'y': y, 'terrain': t} for x, y, t in sorted(set.intersection(*(v['points'] for v in choices)))]
                  for name, choices in variants.items()}
    fixture_checks = {}
    condition_counts = collections.Counter()
    for special in (e for e in entries if e['type'] == 'overmap_special'):
        cells = {tuple(c['point']): c['overmap'] for c in special['overmaps']}
        points = []
        for cell in special['overmaps']:
            x, y, z = cell['point']
            name = cell['overmap']
            base, turns = name, 0
            for k, suffix in enumerate(('_north', '_east', '_south', '_west')):
                if name.endswith(suffix) and name[:-len(suffix)] in variants:
                    base, turns = name[:-len(suffix)], k
                    break
            for p in navigation.get(base, []):
                px, py = p['x'], p['y']
                for _ in range(turns):
                    px, py = 23 - py, px
                points.append({'omt_x': x, 'omt_y': y, 'z': z, 'x': px, 'y': py, 'terrain': p['terrain']})
            for p in conditional.get(base, []):
                above = cells.get((x, y, z + 1))
                assert above is not None, ('Conditional stair fixture requires explicit above context', special['id'], cell)
                enabled = any(n in above for n in p['neighbors_above'])
                terrain = p['terrain'] if enabled else p['else_terrain']
                assert terrain is not None, ('No deterministic negative expectation', p)
                px, py = p['x'], p['y']
                for _ in range(turns):
                    px, py = 23 - py, px
                points.append({'omt_x': x, 'omt_y': y, 'z': z, 'x': px, 'y': py, 'terrain': terrain,
                               'conditional_stair': enabled, 'above': above})
                condition_counts['positive' if enabled else 'negative'] += 1
        fixture_checks[special['id']] = points
    assert condition_counts['positive'] and condition_counts['negative'], condition_counts
    report = {'status': 'apartment_preview_embedded_pending_windows', 'native_embedded': True, 'runtime_validated': False,
        'world_maps': len(world), 'own_omt': len(variants), 'nested_identities': len(nested),
        'nested_definitions': sum(map(len, nested.values())), 'aliases': aliases,
        'runtime_source_evidence': evidence, 'navigation': navigation,
        'navigation_points': sum(map(len, navigation.values())), 'random_overlay_exclusions': excluded,
        'multi_omt_variants': {n: [{'source_slot': v['source_slot'], 'weight': v['weight']} for v in vs]
                               for n, vs in variants.items() if len(vs) > 1},
        'conditional_nested': dict(conditional), 'conditional_fixture_counts': dict(condition_counts),
        'fixture_checks': fixture_checks, 'fixture_check_count': sum(map(len, fixture_checks.values())),
        'unresolved_typed_refs': [],
        'limits': ['Optional native preview integration prepared; source/installed Windows generation is pending; no completion credit',
                   'BN source supports above-neighbor matching and additive multi-OMT variants; runtime assertions still pending',
                   'Deterministic navigation uses intersections across all repeated-ID slices, excluding random nested footprints',
                   'All-floor player traversal, elevator functions, furnishing and later content remain pending']}
    for name, value in (('APARTMENT_PREVIEW_SHELL.json', entries), ('APARTMENT_PREVIEW_REPORT.json', report)):
        text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        path = OUT / name
        if check:
            assert path.read_text(encoding='utf-8') == text, path
        else:
            path.write_text(text, encoding='utf-8')
    print('Apartment preview candidate:', len(world), 'world maps;', report['nested_definitions'],
          'nested variants;', report['fixture_check_count'], 'fixture points;', dict(condition_counts), 'conditional stairs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
