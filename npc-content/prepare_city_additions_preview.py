#!/usr/bin/env python3
"""Prepare deterministic city access points and native terrain-transform probes."""
import argparse
import collections
import json
from prepare_city_additions_geometry import prepare as stage, OUT, PREFIX
from prepare_regional_locations import flatten
from prepare_container_yards import required


def matrix(e):
    v = e['om_terrain']
    return [[v]] if isinstance(v, str) else [v] if isinstance(v[0], str) else v


def fixed(v):
    while isinstance(v, list) and len(v) == 1: v = v[0]
    return v if isinstance(v, str) else None


def native_transform_test(report):
    text = '''
TEST_CASE( "dda_city_geometry_transforms_preserve_adjacent_tiles", "[dda_geometry]" )
{
    clear_all_state();
    clear_map();
    build_test_map( ter_id( "t_floor" ) );
    auto &m = get_map();
    const tripoint_bub_ms p( 12, 12, 0 );
    const tripoint_bub_ms adjacent( 13, 12, 0 );
    struct transform_row { const char *id; const char *from; const char *to; };
    for( const auto &row : std::initializer_list<transform_row> {
'''
    for row in report['transform_checks']:
        text += '        { ' + ', '.join(json.dumps(row[k]) for k in ('transform', 'from', 'to')) + ' },\n'
    text += '''    } ) {
        INFO( row.id << " input=" << row.from );
        const ter_furn_transform_id change( row.id );
        REQUIRE( change.is_valid() );
        m.ter_set( p, ter_id( row.from ) );
        m.furn_set( p, furn_id( "f_null" ) );
        m.ter_set( adjacent, ter_id( "t_floor" ) );
        m.furn_set( adjacent, furn_id( "f_chair" ) );
        change->transform( m, p );
        CHECK( m.ter( p ) == ter_id( row.to ) );
        CHECK( m.ter( adjacent ) == ter_id( "t_floor" ) );
        CHECK( m.furn( adjacent ) == furn_id( "f_chair" ) );
        CHECK( m.furn( p ) == furn_id( "f_null" ) );
        CHECK( m.i_at( p ).empty() );
    }
    clear_all_state();
}
'''
    return text


def prepare(check=False):
    stage(check=True)
    entries = json.loads((OUT / 'CITY_ADDITIONS_PREVIEW_SHELL.json').read_text())
    nested = collections.defaultdict(list)
    for e in entries:
        if 'nested_mapgen_id' in e: nested[e['nested_mapgen_id']].append(e)
    variants = collections.defaultdict(list); exclusions = []
    for e in entries:
        if 'om_terrain' not in e: continue
        o = e['object']; grid = matrix(e); mask = set()
        assert o.get('rotation', 0) == 0 and 'predecessor_mapgen' not in o
        def footprint(piece, xr, yr):
            refs = {n for t, n in required([{'type': 'mapgen', 'object': {'place_nested': [piece]}}]) if t == 'nested_mapgen'}
            sizes = [p['object']['mapgensize'] for n in refs for p in nested[n]]
            radius = max((max(size) for size in sizes), default=0)
            xr = xr if isinstance(xr, list) else [xr, xr]
            yr = yr if isinstance(yr, list) else [yr, yr]
            for y in range(yr[0], yr[-1] + radius):
                for x in range(xr[0], xr[-1] + radius): mask.add((x, y))
        for p in o.get('place_nested', []):
            assert not p.get('z', 0)
            footprint(p, p['x'], p['y'])
        for y, row in enumerate(o['rows']):
            for x, glyph in enumerate(row):
                if glyph in o.get('nested', {}): footprint(o['nested'][glyph], x, y)
        for gy, row in enumerate(grid):
            for gx, name in enumerate(row):
                points = set(); controls = []
                for y in range(24):
                    for x in range(24):
                        px, py = gx * 24 + x, gy * 24 + y
                        terrain = fixed(o.get('terrain', {}).get(o['rows'][py][px], o.get('fill_ter')))
                        if terrain and terrain != 't_null' and not terrain.startswith('t_region_') and (px, py) not in mask:
                            controls.append((x, y, terrain))
                        if not terrain or not any(part in terrain for part in ('stairs', 'ladder', 'ramp', 'elevator', 'slope', 'door', 'reader')): continue
                        if (px, py) in mask:
                            exclusions.append({'omt': name, 'x': x, 'y': y, 'terrain': terrain,
                                               'reason': 'Possible source nested damage/roof overlay'})
                            continue
                        points.add((x, y, terrain))
                # Small single-storey buildings need no invented staircase.
                # Five spread source terrain samples also cover their fixed
                # shell/roof surfaces when all doors are random alternatives.
                if controls:
                    points.update(controls[i] for i in sorted({0, len(controls)//4, len(controls)//2, 3*len(controls)//4, len(controls)-1}))
                variants[name].append(points)
    navigation = {n: sorted(set.intersection(*ps)) for n, ps in variants.items()}
    fixture = {}
    for e in entries:
        if e['type'] != 'overmap_special': continue
        checks = []
        for cell in e['overmaps']:
            name = cell['overmap']; turns = 0
            for index, suffix in enumerate(('_north', '_east', '_south', '_west')):
                if name.endswith(suffix): name = name[:-len(suffix)]; turns = index; break
            for x, y, terrain in navigation[name]:
                for _ in range(turns): x, y = 23 - y, x
                checks.append({'omt_x': cell['point'][0], 'omt_y': cell['point'][1],
                               'x': x, 'y': y, 'z': cell['point'][2], 'terrain': terrain})
        fixture[e['id']] = checks
    transforms = []
    for e in entries:
        if e['type'] != 'ter_furn_transform': continue
        # BN's loader uses map::emplace: a repeated input keeps the first rule.
        inputs = {}
        for rule in e['terrain']:
            assert isinstance(rule['result'], str) and rule['valid_flags'] == []
            for terrain in rule['valid_terrain']: inputs.setdefault(terrain, rule['result'])
        transforms += [{'transform': e['id'], 'from': a, 'to': b} for a, b in sorted(inputs.items())]
    assert len({p['transform'] for p in transforms}) == 5
    assert len(fixture) == 8 and all(fixture.values())
    report = {'status': 'city_native_expectations_embedded_pending_windows',
              'native_embedded': True, 'runtime_validated': False,
              'fixture_checks': fixture, 'fixture_point_count': sum(map(len, fixture.values())),
              'random_overlay_navigation_exclusions': exclusions,
              'overlay_exclusion_count': len(exclusions), 'transform_checks': transforms,
              'transform_input_count': len(transforms), 'layout_cases': 8, 'source_placements_in_debug_views': 37,
              'limits': ['Terrain checks are intersections across same-OMT variants and exclude all possible nested overlays',
                         'Every own tile still requires non-null terrain and empty loot; navigation exclusions never disable those checks',
                         'Native transform probes must exercise all valid BN input terrain on a real map and leave neighboring cells unchanged',
                         'No complete traversal, natural city placement, equipment or Anduril access-control interaction claim']}
    path = OUT / 'CITY_ADDITIONS_PREVIEW_REPORT.json'; text = json.dumps(report, indent=2, ensure_ascii=True) + '\n'
    if check: assert path.read_text() == text, path
    else: path.write_text(text)
    print(f'PASS: eight city layout fixtures, {report["fixture_point_count"]} stable access/geometry points, {len(transforms)} native transform inputs; full empty-loot coverage retained')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--check', action='store_true')
    prepare(p.parse_args().check)
