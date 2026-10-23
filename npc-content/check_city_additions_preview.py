#!/usr/bin/env python3
"""Conserve city access columns and the full native damage input matrix."""
import collections
import json
from prepare_city_additions_preview import prepare, OUT, PREFIX, native_transform_test


def check():
    prepare(check=True)
    report = json.loads((OUT / 'CITY_ADDITIONS_PREVIEW_REPORT.json').read_text())
    entries = json.loads((OUT / 'CITY_ADDITIONS_PREVIEW_SHELL.json').read_text())
    assert (report['layout_cases'], report['source_placements_in_debug_views'], report['fixture_point_count']) == (8, 37, 242)
    assert report['transform_input_count'] == 73 and report['overlay_exclusion_count'] == 6
    stairs = 0
    for special, points in report['fixture_checks'].items():
        ups = {(p['omt_x'] * 24 + p['x'], p['omt_y'] * 24 + p['y'], p['z'])
               for p in points if p['terrain'] in ('t_stairs_up', 't_ladder_up')}
        downs = {(p['omt_x'] * 24 + p['x'], p['omt_y'] * 24 + p['y'], p['z'])
                 for p in points if p['terrain'] in ('t_stairs_down', 't_ladder_down')}
        assert {(x, y, z + 1) for x, y, z in ups} == downs, (special, 'Source stair columns no longer match')
        stairs += len(ups)
        if special.startswith(PREFIX + 'urban_library_'):
            assert len(ups) == 6 and all(z == 0 for x, y, z in ups)
        if special == PREFIX + 'office_dentist': assert ups == {(6, 18, 0)}
        assert len(points) < 8000
    assert stairs == 13
    expected = []
    for e in entries:
        if e['type'] != 'ter_furn_transform': continue
        inputs = {}
        for rule in e['terrain']:
            for source in rule['valid_terrain']: inputs.setdefault(source, rule['result'])
        expected += [{'transform': e['id'], 'from': a, 'to': b} for a, b in sorted(inputs.items())]
    assert report['transform_checks'] == expected
    cpp = native_transform_test(report)
    assert cpp.count('        { "dda_geo_city_add_') == 73
    assert 'change->transform( m, p );' in cpp
    assert 'CHECK( m.ter( adjacent ) == ter_id( "t_floor" ) );' in cpp
    assert 'CHECK( m.furn( adjacent ) == furn_id( "f_chair" ) );' in cpp
    assert 'CHECK( m.furn( p ) == furn_id( "f_null" ) );' in cpp
    assert 'CHECK( m.i_at( p ).empty() );' in cpp
    print('PASS: 242 city geometry points, thirteen source stair columns and all 73 native damage inputs conserved; every own tile retains full empty-loot/non-null checks')


if __name__ == '__main__': check()
