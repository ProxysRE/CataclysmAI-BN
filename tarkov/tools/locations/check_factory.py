"""Check Factory draft packaging and static topology against pinned BN assets."""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import subprocess

from check_industrial import catalog

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'locations/factory_01'
MOD = ROOT/'mods/trkv_factory_dev'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def reconstruct(manifest, definitions):
    w, h = manifest['size']
    by_id = {d['om_terrain'][0]: d for d in definitions}
    assert len(by_id) == len(definitions) == len(manifest['blocks'])
    rows = [[None]*w for _ in range(h)]
    terrain = {}
    for block in manifest['blocks']:
        x0, y0, z = block['origin']
        assert z == 0 and block['size'] == [24, 24]
        assert x0 % 24 == y0 % 24 == 0
        assert 0 <= x0 <= w-24 and 0 <= y0 <= h-24
        definition = by_id[block['terrain_id']]
        assert set(definition) == {'type', 'om_terrain', 'method', 'object'}
        assert definition['type'] == 'mapgen' and definition['method'] == 'json'
        obj = definition['object']
        assert set(obj) == {'fill_ter', 'rows', 'terrain'}
        assert obj['fill_ter'] == 't_rock'
        assert len(obj['rows']) == 24 and all(len(r) == 24 for r in obj['rows'])
        for y, row in enumerate(obj['rows']):
            for x, c in enumerate(row):
                assert rows[y0+y][x0+x] is None, 'Overlapping blocks'
                assert c in obj['terrain']
                assert c not in terrain or terrain[c] == obj['terrain'][c]
                terrain[c] = obj['terrain'][c]
                rows[y0+y][x0+x] = c
    assert all(c is not None for row in rows for c in row), 'Missing cells'
    return [''.join(row) for row in rows], terrain


def check(bn):
    manifest, geometry = load(OUT/'ground_manifest.json'), load(OUT/'ground_geometry.json')
    assert subprocess.check_output(['git', '-C', str(bn), 'rev-parse', 'HEAD'], text=True).strip() == manifest['bn_commit']
    assert not subprocess.check_output(['git', '-C', str(bn), 'status', '--porcelain', '--',
                                       'data/json/furniture_and_terrain'], text=True).strip()
    assert hashlib.sha256((OUT/'reference/Factory.svg').read_bytes()).hexdigest() == geometry['source_sha256'] == manifest['source_sha256']
    rows, terrain = reconstruct(manifest, load(MOD/'mapgen.json'))
    assert rows == geometry['rows'] and terrain == geometry['terrain']
    assert manifest['size'] == geometry['size'] == [264, 288]
    assert manifest['svg_units_per_cell'] == geometry['svg_units_per_cell'] == .5
    assert not manifest['spawn_areas'] and not manifest['extraction_areas'] and not manifest['vertical_transitions']
    overmap = load(MOD/'overmap.json')
    definitions = {x['id']: x for x in overmap if x['type'] == 'overmap_terrain'}
    specials = [x for x in overmap if x['type'] == 'overmap_special']
    assert len(definitions) == len(overmap)-1 == len(manifest['blocks'])
    assert len(specials) == 1 and specials[0]['occurrences'] == [0, 0]
    expected = [{'point': [b['origin'][0]//24, b['origin'][1]//24, 0],
                 'overmap': b['terrain_id']} for b in manifest['blocks']]
    assert specials[0]['overmaps'] == expected
    assert set(definitions) == {b['terrain_id'] for b in manifest['blocks']}
    assert all(d['flags'] == ['NO_ROTATE'] and d['mondensity'] == 0 for d in definitions.values())
    asset = catalog(bn)
    costs = {c: asset(t)['move_cost'] for c, t in terrain.items()}
    assert all((costs[c] > 0) == (c in '.S') for c in terrain)
    unseen = {(x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if costs[c] > 0}
    sizes = []
    while unseen:
        start = unseen.pop()
        pending, count = deque([start]), 0
        while pending:
            x, y = pending.popleft()
            count += 1
            for n in [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]:
                if n in unseen:
                    unseen.remove(n)
                    pending.append(n)
        sizes.append(count)
    sizes.sort(reverse=True)
    # Compare to the independently recorded source raster audit, not to a goal
    # of one component: real source floors can require doors/vertical access.
    recorded = next(r for layer in load(OUT/'raster_audit.json')['layers']
                    if layer['layer'] == 'Ground_Floor' for r in layer['scales']
                    if r['svg_units_per_cell'] == .5)
    assert len(sizes) == recorded['components']
    assert sum(sizes) == recorded['walkable_cells']
    assert sizes[:12] == recorded['largest_components']
    report = {'evidence': 'static_packaging_and_asset_topology', 'bn_commit': manifest['bn_commit'],
              'blocks': len(manifest['blocks']), 'size': manifest['size'],
              'cells_by_symbol': dict(sorted(Counter(''.join(rows)).items())),
              'walkable_cells': sum(sizes), 'component_sizes': sizes,
              'automatic_passage_repair': False,
              'limitations': ['Не доказывает генерацию BN или маршрут НПС',
                             'Не определяет назначение раздельных участков без сверки этажей',
                             'Материалы и LOS силуэтов пока условные']}
    (OUT/'ground_static_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn', type=Path, required=True)
    check(p.parse_args().bn.resolve())
