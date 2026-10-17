#!/usr/bin/env python3
"""Regression checks for map projection and preservation of restricted Hub access."""
import copy
import json

from audit_hub_access import access_sources, audit, project, review


def must_reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('Invalid projection accepted')


def check():
    # Multi-OMT maps can begin at negative coordinates. Their local row offsets
    # must not be confused with the special's overmap coordinates.
    entry = {'om_terrain': [['west', 'east']], 'object': {
        'rows': ['e' + '.' * 47] * 24, 'terrain': {'.': 't_floor'}}}
    special = {'overmaps': [
        {'point': [2, -2, -1], 'overmap': 'west_north'},
        {'point': [3, -2, -1], 'overmap': 'east_north'},
        {'point': [8, 8, -1], 'overmap': 'unrelated_west'},
    ]}
    tiles, info = project(entry, special, {'terrain': {'e': 't_elevator'}})
    assert info['origin_omt'] == [2, -2, -1]
    assert tiles[(48, -48, -1)] == 't_elevator'
    assert len(tiles) == 48 * 24
    altered = copy.deepcopy(entry)
    altered['object']['rows'][0] = '.'
    must_reject(lambda: project(altered, special, {}))
    altered = copy.deepcopy(special)
    altered['overmaps'][0]['overmap'] = 'west_east'
    must_reject(lambda: project(entry, altered, {}))
    altered = copy.deepcopy(entry)
    altered['om_terrain'] = ['west', 'east']
    must_reject(lambda: project(altered, special, {}))
    # BN searches for opposite stairs within the same OMT when exact XY misses.
    checked = review({(-1, -1, 0): 't_stairs_down', (-2, -1, -1): 't_stairs_up',
                      (24, 0, 0): 't_elevator_control_robofac_down',
                      (25, 0, 0): 't_elevator', (25, 0, -1): 't_elevator'})
    stair = next(s for s in checked['stairs'] if s['point'][2] == 0)
    assert not stair['same_xy_pair'] and stair['bn_same_omt_candidates'] == [[-2, -1, -1]]
    assert checked['controls'][0]['required_destination'] == -1
    assert checked['controls'][0]['destination_shaft_present']
    files = access_sources()
    definitions = json.loads(files['dda/data/json/furniture_and_terrain/terrain-mechanisms.json'])
    for direction, adjustment in (('up', 1), ('down', -1)):
        terrain = next(e for e in definitions if e.get('id') == 't_elevator_control_robofac_' + direction)
        action = terrain['examine_action']
        assert action['type'] == 'effect_on_condition'
        eoc, = action['effect_on_conditions']
        assert eoc['condition'] == {'u_has_trait': 'PROF_HUB01_ANCILLIARY'}
        assert eoc['effect'][0]['z_adjust'] == adjustment
        assert 'u_teleport' in eoc['effect'][2]
        assert 'UNAUTHORIZED' in eoc['false_effect']['u_message']
    bn_source = files['bn/src/iexamine_elevator.cpp']
    assert 'on_elevator_try_use' in bn_source
    assert 'elevator::choose_floor( examp, this_omt, sm_orig )' in bn_source
    bn_stairs = files['bn/src/game.cpp'].split('game::find_stairs(', 1)[1].split('game::find_or_make_stairs(', 1)[0]
    assert 'overmap_terrain_tiles()' in bn_stairs and 'project_combine( omt_start, rel )' in bn_stairs
    result = audit()
    dda = result['sides']['dda']
    restricted = [c for c in dda['controls'] if 'required_destination' in c]
    assert len(restricted) == 6 and all(c['destination_shaft_present'] for c in restricted)
    assert len(dda['stairs']) == 28 and len(dda['ramps']) == 44
    assert sum(bool(s['bn_same_omt_candidates']) for s in dda['stairs']) == 24
    assert result['access_policy']['automatic_mapping_allowed'] is False
    assert result['installable'] is False
    print('PASS: Hub map origins, negative coordinates, floor offsets, BN stair lookup, six restricted panels and exact source authorization preserved')


if __name__ == '__main__':
    check()
