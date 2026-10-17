#!/usr/bin/env python3
"""Project multi-OMT Hub maps into shared coordinates before reviewing access."""
import base64
import collections
import gzip
import hashlib
import json
from pathlib import Path

from prepare_community_layers import ROOT as LAYERS, read_bundle
from prepare_location_expansion import ROOT


def access_sources():
    manifest = json.loads((ROOT / 'ACCESS_SOURCE_MANIFEST.json').read_text())
    parts = sorted(ROOT.glob('ACCESS_SOURCES.part*'))
    if [p.name for p in parts] != manifest['parts']:
        raise ValueError('Hub access source parts are missing or out of order')
    raw = gzip.decompress(base64.b64decode(b''.join(p.read_bytes() for p in parts), validate=True))
    if hashlib.sha256(raw).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Hub access source checksum mismatch')
    files = json.loads(raw)
    if set(files) != set(manifest['files']):
        raise ValueError('Hub access manifest mismatch')
    for path, text in files.items():
        if hashlib.sha256(text.encode()).hexdigest() != manifest['files'][path]['sha256']:
            raise ValueError('Hub access source drift: ' + path)
    return files


def terrain_base(identifier):
    for suffix in ('_north', '_east', '_south', '_west'):
        if identifier.endswith(suffix):
            return identifier[:-len(suffix)]
    return identifier


def matrix(entry):
    value = entry['om_terrain']
    if isinstance(value, str):
        return [[value]]
    if all(isinstance(v, str) for v in value):
        # A flat array is a set of alternative map IDs, not a horizontal layout.
        if len(value) != 1:
            raise ValueError('Review alternative map IDs before projecting')
        return [value]
    if not value or len({len(row) for row in value}) != 1:
        raise ValueError('Invalid mapgen matrix')
    return value


def project(entry, special, palette):
    slots = matrix(entry)
    rows = entry['object']['rows']
    if len(rows) != 24 * len(slots) or any(len(r) != 24 * len(slots[0]) for r in rows):
        raise ValueError('Mapgen matrix and row dimensions disagree')
    placed = {tuple(c['point']): terrain_base(c['overmap']) for c in special['overmaps'] if 'overmap' in c}
    identifiers = {name for row in slots for name in row}
    for cell in special['overmaps']:
        identifier = cell.get('overmap', '')
        if terrain_base(identifier) in identifiers and identifier.endswith(('_east', '_south', '_west')):
            raise ValueError('Hub projection needs explicit rotation support: ' + identifier)
    votes = collections.Counter()
    for (x, y, z), identifier in placed.items():
        for sy, row in enumerate(slots):
            for sx, name in enumerate(row):
                if name == identifier:
                    votes[(x - sx, y - sy, z)] += 1
    if not votes:
        return {}, {'unplaced': True, 'map': slots}
    count = max(votes.values())
    origins = [origin for origin, n in votes.items() if n == count]
    if len(origins) != 1:
        raise ValueError('Ambiguous multi-OMT map origin: ' + str(origins))
    ox, oy, z = origins[0]
    terrain = dict(palette.get('terrain', {}))
    terrain.update(entry['object'].get('terrain', {}))
    tiles, omitted = {}, []
    for sy, names in enumerate(slots):
        for sx, name in enumerate(names):
            if placed.get((ox + sx, oy + sy, z)) != name:
                omitted.append({'slot': [sx, sy], 'terrain': name})
                continue
            for y in range(24):
                for x in range(24):
                    value = terrain.get(rows[sy * 24 + y][sx * 24 + x])
                    if isinstance(value, str):
                        tiles[((ox + sx) * 24 + x, (oy + sy) * 24 + y, z)] = value
    return tiles, {'origin_omt': [ox, oy, z], 'matched_slots': count, 'omitted_slots': omitted}


def review(tiles):
    shafts = collections.defaultdict(list)
    controls, ramps, stairs = [], [], []
    for point, terrain in sorted(tiles.items()):
        if terrain == 't_elevator':
            shafts[point[:2]].append(point[2])
        if terrain.startswith('t_elevator_control'):
            controls.append({'point': list(point), 'terrain': terrain})
        if terrain.startswith('t_ramp_'):
            direction = -1 if '_down_' in terrain else 1
            other = (point[0], point[1], point[2] + direction)
            ramps.append({'point': list(point), 'terrain': terrain, 'paired_terrain': tiles.get(other),
                          'same_xy_opposite_floor_present': other in tiles,
                          'note': 'Exact same-XY terrain only; high/low ramp movement needs native generation tests'})
        if terrain in ('t_stairs_up', 't_stairs_down'):
            direction = 1 if terrain == 't_stairs_up' else -1
            other = (point[0], point[1], point[2] + direction)
            expected = 't_stairs_down' if direction == 1 else 't_stairs_up'
            stairs.append({'point': list(point), 'terrain': terrain, 'paired_terrain': tiles.get(other),
                           'same_xy_pair': tiles.get(other) == expected,
                           'bn_same_omt_candidates': [list(p) for p, value in sorted(tiles.items())
                               if p[2] == other[2] and p[0] // 24 == point[0] // 24
                               and p[1] // 24 == point[1] // 24 and value == expected],
                           'scope': 'Stock BN searches the destination OMT after an exact-XY miss; external/unprojected maps remain unknown'})
    for control in controls:
        x, y, z = control['point']
        nearby = [(xy, zs) for xy, zs in shafts.items() if z in zs and max(abs(xy[0] - x), abs(xy[1] - y)) <= 3]
        control['nearby_shaft_tiles'] = len(nearby)
        control['candidate_floors'] = sorted({floor for _, zs in nearby for floor in zs if floor != z})
        if control['terrain'].endswith('_robofac_up'):
            control['required_destination'] = z + 1
        elif control['terrain'].endswith('_robofac_down'):
            control['required_destination'] = z - 1
        if 'required_destination' in control:
            control['destination_shaft_present'] = control['required_destination'] in control['candidate_floors']
    return {'shaft_columns': len(shafts), 'shaft_tiles': sum(map(len, shafts.values())),
            'controls': controls, 'ramps': ramps, 'stairs': stairs}


def audit():
    files = read_bundle(LAYERS)
    report = {'installable': False, 'runtime_validated': False, 'sides': {},
              'projection_scope': 'Static robofachq_static.json plus its named robofachq palette; external/nested maps are not projected',
              'access_policy': {'source_trait': 'PROF_HUB01_ANCILLIARY',
                'source_behavior': 'Trait check, unauthorized popup, directional one-floor teleport through immediate EOC',
                'bn_behavior': 'Native elevator menu, nearby shaft lookup, creature/item/vehicle transport and on_elevator_try_use hook',
                'automatic_mapping_allowed': False,
                'reason': 'Public BN elevator changes both authorization and destination policy; replacing it silently is forbidden'}}
    for side in ('bn', 'dda'):
        special = next(e for e in json.loads(files[side + '/data/json/overmap/overmap_special/specials.json']) if e.get('id') == 'hub_01')
        entries = json.loads(files[side + '/data/json/mapgen/robofachq_static.json'])
        palette = next(e for e in json.loads(files[side + '/data/json/mapgen_palettes/robofachq.json']) if e['id'] == 'robofachq')
        tiles, maps = {}, []
        for entry in entries:
            identifiers = {name for row in matrix(entry) for name in row}
            floors = sorted({c['point'][2] for c in special['overmaps'] if 'overmap' in c
                             and terrain_base(c['overmap']) in identifiers})
            for floor in floors:
                subset = {'overmaps': [c for c in special['overmaps'] if c['point'][2] == floor]}
                projected, info = project(entry, subset, palette)
                if tiles.keys() & projected.keys():
                    raise ValueError('Overlapping Hub static maps')
                tiles.update(projected)
                maps.append(info)
        report['sides'][side] = {'maps': maps, 'projected_terrain_tiles': len(tiles), **review(tiles)}
    access = access_sources()
    dda_terrain = json.loads(access['dda/data/json/furniture_and_terrain/terrain-mechanisms.json'])
    relevant = [e for e in dda_terrain if e.get('id') in ('t_elevator_control_robofac_up', 't_elevator_control_robofac_down')]
    report['access_policy']['exact_source_controls'] = relevant
    traits = json.loads(access['dda/data/json/mutations/professions.json'])
    report['access_policy']['exact_source_trait'] = next(e for e in traits if e.get('id') == 'PROF_HUB01_ANCILLIARY')
    report['access_policy']['bn_elevator_reuse'] = {
        'keep': ['TFLAG_ELEVATOR shaft discovery', 'blocking-vehicle checks', 'item/creature/vehicle transport',
                 'player placement and movement hook', 'overmap rotation handling'],
        'required_extension': ['authorization before travel', 'restrict destination to the DDA up/down floor'],
        'existing_hook_limits': 'on_elevator_try_use can deny use; the current hook cannot select or filter destination floors',
        'native_code_prepared': True, 'runtime_validated': False,
        'bridge': 'Two registered directional handlers call BN elevator transport with a fixed authorized floor; exact destination shaft required'}
    (ROOT / 'HUB_ACCESS_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Hub static access projection:', {s: {'shafts': x['shaft_tiles'], 'controls': len(x['controls']), 'ramps': len(x['ramps']), 'stairs': len(x['stairs'])} for s, x in report['sides'].items()})
    return report


if __name__ == '__main__':
    audit()
