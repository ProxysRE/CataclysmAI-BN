#!/usr/bin/env python3
"""Guard source-dependent adaptations exposed by the Windows geometry run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sources():
    root = ROOT / 'geometry_layer/runtime_sources'
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['pins'] == {'bn': 'c621aaf42fa182473aad10feea2b55647704dcf1',
                                'dda': 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    files = {path: (root / path).read_text(encoding='utf-8') for path in manifest['files']}
    for path, text in files.items():
        raw = text.encode('utf-8')
        assert hashlib.sha256(raw).hexdigest() == manifest['files'][path]['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == manifest['files'][path]['blob_sha'], path
    return files


def validate_barrier(entries):
    barrier = 'dda_geo_research_f_LIXA_unfold_barrier'
    world = next(e for e in entries if e.get('om_terrain') == 'dda_geo_LIXA_device_1')
    obj = world['object']
    assert not any(a.get('id') == barrier for a in obj.get('set', [])), 'Barrier remains in BN early set phase'
    placed = [p for p in obj.get('place_furniture', []) if p.get('furn') == barrier]
    expected = [{'furn': barrier, 'x': x, 'y': 9} for x in range(6, 22)]
    assert placed == expected, 'Incomplete source barrier line'
    # Reproduce the exact interference: source compressor terrain is a WALL and
    # BN jmapgen_terrain clears preexisting furniture there. These are not cells
    # to remove from the acceptance test; DDA places its set line after terrain.
    terrain = {e['id']: e for e in entries if e['type'] == 'terrain'}
    walls = [p for p in expected if 'WALL' in terrain.get(
        obj['terrain'][obj['rows'][p['y']][p['x']]], {}).get('flags', [])]
    assert [(p['x'], p['y']) for p in walls] == [(12, 9), (15, 9)]


def check():
    files = sources()
    bn = files['bn/src/mapgen/mapgen.cpp']
    dda = files['dda/src/mapgen.cpp']
    generate = bn.split('void mapgen_function_json::generate(', 1)[1].split('void mapgen_function_json_nested::nest', 1)[0]
    assert generate.index('elem.apply(active_md') < generate.index('objects.apply(active_md')
    terrain = bn.split('class jmapgen_terrain:', 1)[1].split('class jmapgen_ter_furn_transform:', 1)[0]
    assert 'TFLAG_WALL' in terrain and 'dat.m.furn_set(point_omt_ms(x.get(), y.get()), f_null)' in terrain
    assert 'return mapgen_phase::furniture' in bn.split('class jmapgen_furniture:', 1)[1].split('class jmapgen_terrain:', 1)[0]
    phases = dda.split('static ret_val<void> apply_mapgen_in_phases(', 1)[1].split('void mapgen_function_json::generate', 1)[0]
    assert 'for( mapgen_phase phase : all_enum_values<mapgen_phase>() )' in phases
    assert 'elem.phase() != phase' in phases and 'objects.apply( md, phase' in phases
    phase = dda.split('mapgen_phase jmapgen_setmap::phase()', 1)[1].split('bool jmapgen_setmap::apply', 1)[0]
    assert 'case JMAPGEN_SETMAP_LINE_FURN:' in phase and 'return mapgen_phase::furniture;' in phase
    bash = files['bn/src/map/map.cpp'].split('auto map::bash_ter_success(', 1)[1].split('spawn_items(p,', 1)[0]
    assert 'else if (bash.ter_set)' in bash and 'ter_set(p, t_open_air);' in bash
    entries = json.loads((ROOT / 'native/dda_geometry_preview.json').read_text(encoding='utf-8'))
    validate_barrier(entries)
    # Reject the old early-phase representation even with all sixteen test
    # expectations still present: assertions must check the corrected payload.
    import copy
    probe = copy.deepcopy(entries)
    obj = next(e for e in probe if e.get('om_terrain') == 'dda_geo_LIXA_device_1')['object']
    obj.pop('place_furniture')
    obj['set'] = [{'line': 'furniture', 'id': 'dda_geo_research_f_LIXA_unfold_barrier',
                   'x': 6, 'y': 9, 'x2': 21, 'y2': 9}]
    try:
        validate_barrier(probe)
    except AssertionError:
        pass
    else:
        raise AssertionError('Early barrier phase regression accepted')
    print('PASS: pinned DDA/BN mapgen phase and implicit-air rules; complete late-phase LIXA barrier; early-phase regression rejected')


if __name__ == '__main__':
    check()
