"""Static topology/asset audit against an exact BN checkout, not a runtime test."""
import argparse
from collections import deque
from itertools import combinations
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
LOCATION = ROOT / 'locations/industrial_01'
MOD = ROOT / 'mods/trkv_locations_dev'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def catalog(bn):
    result = {}
    for path in sorted((bn / 'data/json/furniture_and_terrain').glob('*.json')):
        for obj in load(path):
            if obj.get('type') not in ('terrain', 'furniture') or 'id' not in obj:
                continue
            ids = obj['id'] if isinstance(obj['id'], list) else [obj['id']]
            for ident in ids:
                key = (obj['type'], ident)
                assert key not in result, f'duplicate asset {key}'
                result[key] = (obj, str(path.relative_to(bn)))

    def resolve(ident, trail=()):
        assert ident not in trail, f'inheritance cycle {ident}'
        obj, source = result[('furniture' if ident.startswith('f_') else 'terrain', ident)]
        merged = resolve(obj['copy-from'], (*trail, ident)) if 'copy-from' in obj else {}
        merged = {**merged, **obj, 'source': source}
        flags = set(merged.get('flags', []))
        flags |= set(obj.get('extend', {}).get('flags', []))
        flags -= set(obj.get('delete', {}).get('flags', []))
        merged['flags'] = sorted(flags)
        return merged
    return resolve


def grid():
    manifest = load(LOCATION / 'manifest.json')
    defs = load(MOD / 'mapgen.json')
    by_id = {d['om_terrain'][0]: d['object'] for d in defs}
    assert len(by_id) == len(defs) == 9
    cells = {}
    for block in manifest['blocks']:
        x0, y0, z = block['origin']
        assert z == 0 and block['size'] == [24, 24]
        obj = by_id[block['terrain_id']]
        assert set(obj) <= {'fill_ter', 'rows', 'terrain', 'furniture'}, 'unexpected mapgen content'
        assert len(obj['rows']) == 24 and all(len(row) == 24 for row in obj['rows'])
        for dy, row in enumerate(obj['rows']):
            for dx, char in enumerate(row):
                p = (x0 + dx, y0 + dy)
                assert p not in cells, f'block overlap {p}'
                assert char in obj['terrain'], f'unmapped terrain {char}'
                cells[p] = (obj['terrain'][char], obj.get('furniture', {}).get(char))
    assert set(cells) == {(x,y) for y in range(72) for x in range(72)}
    return manifest, cells


def inside(p, area):
    return all(lo <= v < hi for v, lo, hi in zip(p, area['min'], area['max']))


def route(start, target, passable, forbidden=frozenset()):
    q = deque([start])
    parent = {start: None}
    while q:
        p = q.popleft()
        if p == target:
            out = []
            while p is not None:
                out.append(p)
                p = parent[p]
            return out[::-1]
        for n in [(p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1)]:
            if n in passable and n not in forbidden and n not in parent:
                parent[n] = p
                q.append(n)
    return None


def segment(a, b):
    # Conservative sampling is a screen, not BN's sees() implementation.
    dx, dy = b[0]-a[0], b[1]-a[1]
    count = max(abs(dx), abs(dy)) * 4
    return {(round(a[0] + dx*i/count), round(a[1] + dy*i/count)) for i in range(count+1)}


def check(bn):
    m, cells = grid()
    assert subprocess.check_output(['git', '-C', str(bn), 'rev-parse', 'HEAD'], text=True).strip() == m['bn_commit']
    # A dirty asset tree would make the recorded pinned evidence misleading.
    assert not subprocess.check_output(['git', '-C', str(bn), 'status', '--porcelain', '--',
                                       'data/json/furniture_and_terrain'], text=True).strip()
    asset = catalog(bn)
    used = sorted({i for ids in cells.values() for i in ids if i})
    props = {i: asset(i) for i in used}
    passable, closed_passable, opaque_open = set(), set(), set()
    for p, (tid, fid) in cells.items():
        t, f = props[tid], props.get(fid, {})
        assert t.get('trap', 'tr_null') == 'tr_null' and not t.get('emissions')
        assert not f.get('emissions')
        t_open = asset(t['open']) if 'open' in t else t
        f_cost = f.get('move_cost_mod', 0)
        if t_open.get('move_cost', 0) > 0 and f_cost >= 0:
            passable.add(p)
        if t.get('move_cost', 0) > 0 and f_cost >= 0:
            closed_passable.add(p)
        if 'TRANSPARENT' not in t_open.get('flags', []) or (fid and 'TRANSPARENT' not in f.get('flags', [])):
            opaque_open.add(p)
    assert all((x,y) not in passable for x in range(72) for y in range(72)
               if x in (0,71) or y in (0,71)), 'perimeter leak'
    zones = {z['id']: z for z in m['zones']}
    links = {l['id']: l for l in m['connections']}
    assert len(zones) == len(m['zones']) and len(links) == len(m['connections'])
    areas = [z['area'] for z in zones.values()]
    areas += [a['area'] for a in m['spawn_areas'] + m['extraction_areas'] + m['connections']]
    for a in areas:
        assert all(isinstance(v, int) for v in a['min'] + a['max'])
        assert all(0 <= lo < hi <= limit for lo, hi, limit in zip(a['min'], a['max'], [72,72,1]))
    for zone in zones.values():
        assert zone['neighbors'] == sorted({other for c in zone['connections']
               for other in links[c]['zones'] if other != zone['id']})
        for neighbor in zone['neighbors']:
            assert zone['id'] in zones[neighbor]['neighbors']
    for l in links.values():
        points = {p for p in passable if inside((*p,0), l['area'])}
        assert points, f'blocked connection {l["id"]}'
        # A connection must actually touch walkable cells in both named zones.
        for zid in l['zones']:
            contacts = {p for p in passable if inside((*p,0), zones[zid]['area'])
                        and any(abs(p[0]-q[0])+abs(p[1]-q[1]) <= 1 for q in points)}
            assert contacts, f'connection {l["id"]} does not touch {zid}'
    entries = []
    for s in m['spawn_areas']:
        points = s['primary'] + s['fallback']
        assert len({tuple(p) for p in points}) == len(points)
        assert len(s['primary']) >= s['capacity'] and s['fallback']
        for p in points:
            assert inside(p, s['area']) and inside(p, zones[s['zone']]['area'])
            assert tuple(p[:2]) in closed_passable, f'invalid spawn {p}'
            assert route(tuple(points[0][:2]), tuple(p[:2]), closed_passable)
            entries.append(tuple(p[:2]))
    exits = []
    for e in m['extraction_areas']:
        assert not e['runtime_enabled']
        points = [p for p in closed_passable if inside((*p,0), e['area'])]
        assert len(points) >= 3 and inside([*points[0],0], zones[e['zone']]['area'])
        assert tuple(e['approach'][:2]) in closed_passable
        assert route(tuple(e['approach'][:2]), points[0], closed_passable)
        exits.append(points[0])
    for p in entries:
        for q in exits:
            assert route(p, q, passable), f'unreachable exit {p} -> {q}'
            assert route(p, q, closed_passable), f'exit requires door opening {p} -> {q}'
        for poi in m['pois']:
            assert inside(poi['position'], zones[poi['zone']]['area'])
            assert route(p, tuple(poi['position'][:2]), passable), f'unreachable POI {poi["id"]}'
    # Explicitly prove two separated longitudinal routes. Blocking each sector
    # still leaves a south-to-north route through the other sector.
    route_checks = {}
    for name, excluded in [('west_only', {p for p in cells if p[0] >= 27 and 5 <= p[1] < 60}),
                           ('hall_only', {p for p in cells if p[0] < 28 and 5 <= p[1] < 60})]:
        r = route((24,65), (24,3), passable, excluded)
        assert r, f'no independent {name} route'
        route_checks[name] = len(r)-1
    for marker in m['loot_candidates']:
        assert cells[tuple(marker['position'][:2])][1] == marker['furniture']
        a = marker['interaction_from']
        assert a and abs(a[0]-marker['position'][0])+abs(a[1]-marker['position'][1]) == 1
        assert route(entries[0], tuple(a[:2]), passable)
    for marker in m['doors']:
        t = props[cells[tuple(marker['position'][:2])][0]]
        assert not marker['locked'] and t.get('open')
    for lamp in m['lighting']:
        assert cells[tuple(lamp['position'][:2])][1] == lamp['furniture']
        assert props[lamp['furniture']]['light_emitted'] > 0
        assert 'LOCAL_LIGHT' in props[lamp['furniture']]['flags']
    # Evaluate ALL candidate points in each pair, with doors considered open.
    pairs = []
    for a, b in combinations(m['spawn_areas'], 2):
        ap = a['primary'] + a['fallback']
        bp = b['primary'] + b['fallback']
        contact = any(not (segment(x,y) & opaque_open) for x in ap for y in bp)
        shortest = min(len(route(tuple(x[:2]),tuple(y[:2]),passable))-1 for x in ap for y in bp)
        pairs.append({'areas': [a['id'], b['id']], 'static_los_clear': not contact,
                      'shortest_path_cells': shortest, 'runtime_verified': False,
                      'allowed': False})
    assert m['spawn_pair_policy'] == 'deny_unlisted'
    # No pair is enabled before the native LOS and movement checks.
    assert not any(p.get('allowed') for p in m['spawn_pairs'])
    return {'evidence': 'static_only', 'bn_commit': m['bn_commit'], 'base_commit': m['base_commit'],
            'passable_doors_open': len(passable), 'passable_doors_closed': len(closed_passable),
            'entry_points': len(entries), 'exit_regions': len(exits), 'poi_count': len(m['pois']),
            'independent_routes': route_checks, 'spawn_pair_screen': pairs,
            'assets': {i: {k: props[i].get(k) for k in ['source','move_cost','move_cost_mod','flags',
                        'open','light_emitted','coverage','bash']} for i in used},
            'not_verified': ['Загрузка JSON самим BN', 'Реальная генерация и стыки блоков', 'Поиск пути движком',
                             'Двери в движке', 'Освещение, крыша и внешний свет', 'Баллистика',
                             'Запуск на Windows', 'Визуальная оценка игроком']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bn', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check(args.bn.resolve())
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'assets'}, ensure_ascii=False, indent=2))
