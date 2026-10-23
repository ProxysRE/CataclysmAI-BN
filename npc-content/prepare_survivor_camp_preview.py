#!/usr/bin/env python3
"""Prepare both forest-camp debug variants with fixed, correlated tent roofs."""
import argparse
import copy
import json
from adapt_survivor_geometry import prepare as adapt
from prepare_survivor_geometry import ROOT, OUT
from prepare_regional_locations import index_entries, BUILTIN_IDS
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache
from check_geometry_runtime_rules import sources as runtime_sources

PREFIX = 'dda_geo_camp_'
TENTS = {'leather_tent_5x5_S', 'leather_tent_b_5x5_S', 'leather_tent_b_5x5_N', 'tent_5x5_roof'}
ANCHORS = [(3, 6), (17, 6), (10, 12)]


def prepare(check=False):
    adapt(check=True)
    full = json.loads((OUT / 'SURVIVOR_ADAPTED_SHELL.json').read_text())
    raw = json.loads((OUT / 'survivor_sources/data/json/mapgen/survivor_forest_camp.json').read_text())
    source_maps = [e for e in raw if e.get('om_terrain') == ['survivor_forest_camp']]
    worlds = [copy.deepcopy(e) for e in full if e.get('om_terrain') == ['survivor_forest_camp']]
    assert len(source_maps) == len(worlds) == 2
    nests = [copy.deepcopy(e) for e in full if e.get('nested_mapgen_id') in TENTS]
    assert len(nests) == 4
    intact_tent = next(e for e in nests if e['nested_mapgen_id'] == 'leather_tent_5x5_S')
    upper, = intact_tent['object'].pop('place_nested')
    assert upper == {'chunks': ['tent_5x5_roof'], 'x': 0, 'y': 0, 'z': 1}
    roof = next(e for e in nests if e['nested_mapgen_id'] == 'tent_5x5_roof')['object']
    assert roof['mapgensize'] == [5, 5] and roof['rows'] == ['#####'] * 5
    assert roof['terrain'] == {'#': 'dda_geo_frontier_canvas_roof'}
    assert intact_tent['object']['rotation'] == [0, 3]
    # A full square roof is invariant under each source tent rotation. We can
    # therefore place it independently at the same fixed source anchor.
    source_omt = next(e for e in full if e['type'] == 'overmap_terrain' and e['id'] == ['survivor_forest_camp'])
    source_special = next(e for e in full if e['type'] == 'overmap_special' and e['id'] == 'survivor_forest_camp')
    assert source_special['overmaps'] == [{'point': [0, 0, 0], 'overmap': 'survivor_forest_camp_north'}]
    entries = []; masks = {}; source_weights = {}; variant_anchors = {}
    for variant, source, world in zip(('intact', 'ruined'), source_maps, worlds):
        obj = world['object']; name = PREFIX + variant
        assert source['object']['fallback_predecessor_mapgen'] == 'forest_thick'
        assert source['object']['flags'] == ['ERASE_ALL_BEFORE_PLACING_TERRAIN']
        obj['predecessor_mapgen'] = 'forest_thick'
        obj['remove_all'] = {g: {} for g, ter in obj['terrain'].items() if ter != 't_null'}
        mask = ''.join('1' if g in obj['remove_all'] else '0' for row in obj['rows'] for g in row)
        assert len(mask) == 576 and '0' in mask and '1' in mask
        masks[name] = mask
        anchors = [(x, y) for y, row in enumerate(obj['rows']) for x, g in enumerate(row) if g in obj.get('nested', {})]
        assert anchors == ANCHORS
        variant_anchors[variant] = anchors
        source_weights[variant] = copy.deepcopy(source.get('weight', 1000))
        world['om_terrain'] = name
        # Each variant has its own debug-only OMT. Its sole mapgen has a 100%
        # chance regardless of a positive relative weight. The original
        # time-dependent intact/ruined selection is archived, not flattened in
        # a naturally generated mixed pool.
        world['weight'] = 1000
        omt = copy.deepcopy(source_omt)
        omt.update(id=name, name='survivor forest camp (' + variant + ' preview)', extras='')
        omt.pop('travel_cost_type')
        assert omt.pop('flags') == ['REQUIRES_PREDECESSOR']
        special = copy.deepcopy(source_special); special['id'] = name
        special['overmaps'][0]['overmap'] = name + '_north'
        if variant == 'intact':
            special['overmaps'].append({'point': [0, 0, 1], 'overmap': PREFIX + 'intact_roof_north'})
        entries.extend([world, omt, special])
    entries += nests
    entries += [
        {'type': 'overmap_terrain', 'id': PREFIX + 'intact_roof', 'name': 'survivor camp tent roofs',
         'sym': '+', 'color': 'green', 'see_cost': 0, 'extras': ''},
        {'type': 'mapgen', 'method': 'json', 'om_terrain': PREFIX + 'intact_roof',
         'object': {'fill_ter': 't_open_air', 'rows': [' ' * 24] * 24, 'terrain': {' ': 't_open_air'},
                    'place_nested': [{'chunks': ['tent_5x5_roof'], 'x': x, 'y': y} for x, y in ANCHORS]}}
    ]
    def rename(v):
        if isinstance(v, str): return PREFIX + v if v in TENTS else v
        if isinstance(v, list): return [rename(x) for x in v]
        if isinstance(v, dict): return {k: rename(x) for k, x in v.items()}
        return v
    entries = rename(entries)
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}; own = index_entries(entries)
    assert not (own - BUILTIN_IDS) & (core | mods)
    shared = {('terrain', 'dda_geo_frontier_canvas_roof')}
    missing = sorted(required(entries) - own - core - shared)
    assert not missing, missing
    assert all(not p.get('z', 0) for e in entries if e['type'] == 'mapgen' for p in e['object'].get('place_nested', []))
    # Authenticate the existing runtime evidence before relying on the source
    # fallback and clear-before-terrain policy.
    evidence = runtime_sources(); dda = evidence['dda/src/mapgen.cpp']; bn = evidence['bn/src/mapgen/mapgen.cpp']
    assert 'mapgendata predecessor_md( md, fallback_predecessor_mapgen_ );' in dda
    assert 'jmapgen_flags::erase_all_before_placing_terrain' in dda
    assert 'class jmapgen_remove_all' in bn and 'jo, "remove_all"' in bn
    points = []
    for x, y in ANCHORS:
        for dx, dy in ((0, 0), (4, 0), (0, 4), (4, 4)):
            points.append({'x': x + dx, 'y': y + dy, 'z': 0, 'furniture': 'f_large_canvas_wall'})
        points.append({'x': x + 2, 'y': y + 2, 'z': 0, 'furniture': 'f_center_groundsheet'})
        for dy in range(5):
            for dx in range(5): points.append({'x': x + dx, 'y': y + dy, 'z': 1, 'terrain': 'dda_geo_frontier_canvas_roof'})
    report = {
        'status': 'two_camp_variants_embedded_pending_windows', 'native_embedded': True, 'runtime_validated': False,
        'source_weights': source_weights, 'source_special': source_special,
        'variant_anchors': variant_anchors, 'loot_masks': masks,
        'source_painted_cells': {k: v.count('1') for k, v in masks.items()},
        'unresolved_typed_refs': missing, 'shared_preview_dependencies': sorted(shared),
        'source_rows_and_furniture_weights_preserved': True,
        'world_maps': 3, 'nested_maps': 4, 'special_cells': {PREFIX + 'intact': 2, PREFIX + 'ruined': 1},
        'intact_expected_points': points, 'intact_roof_tiles': 75,
        'registration_adaptations': ['REQUIRES_PREDECESSOR replaced by explicit source fallback forest_thick for isolated debug generation',
                                    'Relative time weight kept in source_weights; intact and ruined variants are separately selectable zero-occurrence debug specials'],
        'limits': ['Embedded in the native preview; source/installed generation pending, no new generation credit',
                   'Natural source time-dependent variant selection is not implemented',
                   'BN remove_all clears fields as well as furniture/items/traps, only on source-painted glyphs',
                   'Unpainted surrounding forest retains stock BN generation and its normal contents',
                   'Intact roof rotation is safe because its full 5x5 square is rotationally invariant',
                   'Ruined tents intentionally have no upper roof special; all original furniture/null weights are retained',
                   'Source monsters, corpses, loot and other later content remain in the full staging archives']}
    for name, value in [('SURVIVOR_CAMP_PREVIEW_SHELL.json', entries), ('SURVIVOR_CAMP_PREVIEW_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check: assert path.read_text() == text, path
        else: path.write_text(text)
    print('PASS: intact/ruined camp previews, three source anchors, 75 explicit roof tiles, original ruined-tent weights and untouched forest masks retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
