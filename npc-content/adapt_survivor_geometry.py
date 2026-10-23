#!/usr/bin/env python3
"""Close physical survivor-shell references without hiding vertical blockers."""
import argparse
import copy
import hashlib
import json
from prepare_geometry_layer import ROOT, OUT
from prepare_survivor_geometry import prepare as stage
from prepare_regional_locations import index_entries
from prepare_container_yards import required
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'survivor_adaptation_sources'
ALIASES = {
    'f_large_skin_wall': 'f_large_canvas_wall',
    'f_large_skin_door': 'f_large_canvas_door',
    'f_large_skin_groundsheet': 'f_large_groundsheet',
    'f_skin_center_groundsheet': 'f_center_groundsheet',
    't_carpet_metal_purple': 't_carpet_purple',
    't_tree_very_dead': 't_tree_dead',
    'rural_road_forest_ns': 'rural_road_forest_north',
    't_canvas_roof': 'dda_geo_frontier_canvas_roof',
}


def adapt(value):
    if isinstance(value, str):
        return ALIASES.get(value, value)
    if isinstance(value, list):
        return [adapt(x) for x in value]
    if isinstance(value, dict):
        return {k: adapt(x) for k, x in value.items()}
    return value


def prepare(check=False):
    stage(check=True)
    manifest = json.loads((SOURCE / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['bn_commit'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    stock = {}
    for path, record in manifest['files'].items():
        raw = (SOURCE / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == record['blob_sha'], path
        stock.update({e['id']: e for e in json.loads(raw) if 'id' in e})
    assert stock['f_large_canvas_wall']['move_cost_mod'] == -1
    door = stock['f_large_canvas_door']; opened = stock[door['open']]
    assert 'DOOR' in door['flags'] and door['move_cost_mod'] == -1
    assert opened['close'] == door['id'] and opened['move_cost_mod'] >= 0
    for floor in ('f_center_groundsheet', 'f_large_groundsheet'):
        assert stock[floor]['move_cost_mod'] == 0 and 'NOCOLLIDE' in stock[floor]['flags']
    original = json.loads((OUT / 'SURVIVOR_SHELLS.json').read_text())
    entries = adapt(copy.deepcopy(original))
    raw_report = json.loads((OUT / 'SURVIVOR_GEOMETRY_REPORT.json').read_text())
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    own = index_entries(entries)
    # Reuse the already embedded, source-authenticated canvas roof. This
    # candidate is for the combined preview, not a standalone content mod.
    frontier = json.loads((OUT / 'FRONTIER_ADAPTED_SHELL.json').read_text())
    roof = next(e for e in frontier if e.get('id') == ALIASES['t_canvas_roof'])
    assert roof['type'] == 'terrain'
    dependencies = {('terrain', roof['id'])}
    # The existing BN rotating forest-road type supplies its north variant.
    from compare_location_catalog import read_sources
    road = next(e for p, text in read_sources()[0].items() if p.startswith('bn/')
                for e in json.loads(text) if e.get('type') == 'overmap_terrain'
                and e.get('id') == 'rural_road_forest')
    assert 'LINEAR' not in road.get('flags', [])
    generated = {('overmap_terrain', 'rural_road_forest_north')}
    missing = sorted(required(entries) - own - core - dependencies - generated)
    assert not missing, missing
    assert len(entries) == len(original)
    for source, entry in zip(original, entries):
        if source['type'] == 'mapgen':
            assert source['object'].get('rows') == entry['object'].get('rows')
            assert source.get('weight') == entry.get('weight')
            assert source['object'].get('rotation') == entry['object'].get('rotation')
            assert adapt(source['object']) == entry['object']
    report = {
        'status': 'physical_counterparts_closed_vertical_adaptation_pending',
        'native_embedded': False, 'runtime_validated': False,
        'aliases': ALIASES, 'unresolved_typed_refs': missing,
        'shared_preview_dependencies': sorted(dependencies),
        'generated_BN_overmap_variants': sorted(generated),
        'geometry_issues': raw_report['geometry_issues'],
        'core_identity_intersections': sorted(own & core),
        'bundled_mod_identity_intersections': sorted(own & mods),
        'counterpart_differences': [
            'Heavy canvas substitutes leather walls and doors; BN physical and interaction behavior is retained',
            'BN large/center groundsheets substitute skin groundsheets; no leather material parity claimed',
            'Ordinary BN purple carpet substitutes metal-backed source carpet; destruction material differs',
            'BN dead tree substitutes very dead source tree',
            'Forest-road north is the rotating BN counterpart for DDA ns orientation',
        ],
        'limits': ['Raw source identities still overlap BN; this candidate cannot be installed directly',
                   'All three upward placements remain intact and unsupported until explicit floor adaptation',
                   'Two fallback forest predecessors and the dynamic camp weight remain pending',
                   'Typed reference closure is not native schema or traversal acceptance',
                   'No native patch change or completion credit'],
    }
    for name, value in [('SURVIVOR_ADAPTED_SHELL.json', entries), ('SURVIVOR_ADAPTATION_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check:
            assert path.read_text() == text, path
        else:
            path.write_text(text)
    print('PASS: survivor/Lacroix physical references close; original geometry, weights and vertical blockers preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
