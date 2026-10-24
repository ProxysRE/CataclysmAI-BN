#!/usr/bin/env python3
"""Preserve five accepted civic groups as seven isolated geometry candidates."""
import argparse
import copy
import hashlib
import json
from collections import defaultdict
from prepare_geometry_layer import ROOT, OUT, extract, glyphs
from prepare_city_additions_geometry import sources as city_sources, expand, rename
from prepare_regional_locations import flatten, references, index_entries, BUILTIN_IDS, merge
from prepare_container_yards import required
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'civic_sites_sources'
TARGETS = {'office_tower', 'hotel_1', 'hotel_2', 'hotel_3', 'zoo', 'stadium', 'shopping_plaza'}
PREFIX = 'dda_geo_civic_'


def sources():
    manifest = json.loads((SOURCE / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['dda_commit'] == 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert manifest['bn_commit'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    files = {}
    for path, record in manifest['files'].items():
        raw = (SOURCE / path).read_bytes()
        assert len(raw) == record['bytes']
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == record['blob_sha'], path
        files[path] = json.loads(raw)
    _, shared, palettes, evidence, _ = city_sources()
    root = OUT / 'large_sites_sources'; m = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    path = 'data/json/mapgen_palettes/stadium_palette.json'; raw = (root / path).read_bytes()
    assert m['dda_commit'] == manifest['dda_commit'] and hashlib.sha256(raw).hexdigest() == m['files'][path]
    shared['dda/' + path] = json.loads(raw)
    evidence.append({'archive': root.name, 'path': path, 'sha256': m['files'][path]})
    for es in [es for p, es in shared.items() if p.startswith('dda/')] + list(files.values()):
        for e in es:
            if e.get('type') == 'palette': palettes[e['id']] = e
    return files, shared, palettes, evidence


def prepare(check=False):
    files, shared, palettes, evidence = sources()
    catalog, _ = read_sources()
    registrations = {e['id']: e for p, text in catalog.items() if p.startswith('dda/')
                     for e in json.loads(text) if e.get('type') == 'city_building' and e.get('id') in TARGETS}
    assert registrations.keys() == TARGETS
    requested = {c['overmap'].removesuffix('_north') for e in registrations.values() for c in e['overmaps']}
    originals = []; conservation = []
    for path, es in files.items():
        for src in es:
            if src.get('type') != 'mapgen' or not set(flatten(src.get('om_terrain', []))) & requested: continue
            e = copy.deepcopy(src); e['object'] = expand(e['object'], palettes, None)
            originals.append(e)
            conservation.append({'path': path, 'source_omt': src['om_terrain'], 'weight': src.get('weight', 1000)})
    mapped = {n for e in originals for n in flatten(e['om_terrain'])} - {'null'}
    assert requested <= mapped, sorted(requested - mapped)
    providers = [e for es in files.values() for e in es if 'nested_mapgen_id' in e]
    providers += [e for path, es in shared.items() if path.startswith('dda/') for e in es if 'nested_mapgen_id' in e]
    physical = {e['nested_mapgen_id'] for e in providers if any(k in e['object'] for k in
                ('terrain', 'fill_ter', 'place_terrain', 'place_ter_furn_transforms')) or
                any(s.get('point', s.get('line', s.get('square'))) == 'terrain' for s in e['object'].get('set', []))}
    while True:
        added = {e['nested_mapgen_id'] for e in providers if any(t == 'nested_mapgen' and n in physical
                 for t, n in references(e['object']))} - physical
        if not added: break
        physical |= added
    late_names = {e['nested_mapgen_id'] for e in providers} - physical | {'fire_extinguisher'}
    projected = set()
    def nests(e):
        obj = e['object']
        if 'nested' in obj: obj['nested'] = {g: v for g, v in obj['nested'].items() if g in glyphs(obj.get('rows', []))}
        projected.update(n for t, n in references(obj) if t == 'nested_mapgen' and n in late_names)
        for key in ('nested', 'place_nested'):
            if key in obj: obj[key] = rename(obj[key], {n: 'null' for n in late_names})
    for e in originals: nests(e)
    present = set()
    while True:
        wanted = {n for e in originals for t, n in references(e['object']) if t == 'nested_mapgen'} - present - {'null'}
        added = [copy.deepcopy(e) for e in providers if e['nested_mapgen_id'] in wanted]
        if not added:
            assert not wanted, ('Missing structural nests', sorted(wanted))
            break
        for e in added: e['object'] = expand(e['object'], palettes, None); nests(e)
        originals += added; present |= {e['nested_mapgen_id'] for e in added}
    for e in originals:
        obj = e['object']
        for g, piece in obj.get('mapping', {}).items():
            for field in ('terrain', 'furniture'):
                if field in piece: obj.setdefault(field, {})[g] = copy.deepcopy(piece[field])
        if 'fill_ter' not in obj:
            for g in sorted(glyphs(obj.get('rows', [])) - set(obj.get('terrain', {})) - set(obj.get('furniture', {})) - set(obj.get('nested', {})) - {' ', '.'}):
                assert 'nested_mapgen_id' in e, (e.get('om_terrain'), g)
                obj.setdefault('furniture', {})[g] = 'f_null'
    for e in registrations.values():
        e = copy.deepcopy(e); e['type'] = 'overmap_special'; e['occurrences'] = [0, 0]; originals.append(e)
    for p, text in catalog.items():
        if not p.startswith('dda/'): continue
        for src in json.loads(text):
            if src.get('type') != 'overmap_terrain': continue
            found = set(flatten(src.get('id', []))) & mapped
            if found: e = copy.deepcopy(src); e['id'] = sorted(found); originals.append(e)
    entries, later, issues = extract(originals, tuple(sorted(present)))
    later += [{'source_registration': e} for e in registrations.values()]
    later.append({'late_only_nested_ids_projected_to_null': sorted(projected)})
    raw_entries = copy.deepcopy(entries)
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    aliases = {'t_metal_roof': 't_metal_flat_roof', 't_door_elocked': 't_door_locked',
               't_window_domestic_alarm': 't_window_domestic', 't_curtains_alarm': 't_curtains',
               't_bollard': 't_little_column', 't_door_metal_elocked': 't_door_metal_locked',
               't_retractable_gate_l': 't_chaingate_l', 't_wood_roof': PREFIX + 'wood_roof'}
    for kind, name in sorted(required(entries) - core):
        if kind != 'terrain': continue
        if name.startswith('t_carpet_linoleum_'): aliases[name] = 't_linoleum_' + name.removeprefix('t_carpet_linoleum_').split('_')[0]
        elif name.startswith(('t_carpet_wood_', 't_carpet_concrete_', 't_carpet_metal_')): aliases[name] = 't_carpet_' + name.rsplit('_', 1)[1]
        else:
            for base in ('t_strconc_wall', 't_sconc_wall', 't_concrete_wall', 't_wall'):
                if name.startswith(base + '_') and ('terrain', base) in core: aliases[name] = base; break
    deferred = []
    abstracts = {e['abstract']: e for p, text in catalog.items() if p.startswith('dda/')
                 for e in json.loads(text) if 'abstract' in e}
    for i, e in enumerate(entries):
        if e['type'] != 'overmap_terrain': continue
        parent = e.get('copy-from')
        if parent in ('generic_city_building_roof', 'generic_stadium_park'):
            base = copy.deepcopy(abstracts[parent]); deferred.append({'source': e['id'], 'expanded_abstract': copy.deepcopy(base)})
            base.pop('abstract'); merge(base, {k: v for k, v in e.items() if k != 'copy-from'})
            entries[i] = e = base
        for field in ('vision_levels', 'mondensity', 'post_process_generators', 'travel_cost_type'):
            if field in e: deferred.append({'source': e['id'], 'field': field, 'value': e.pop(field)})
        for field in ('extend', 'delete'):
            if 'post_process_generators' in e.get(field, {}):
                deferred.append({'source': e['id'], 'field': field + '.post_process_generators', 'value': e[field].pop('post_process_generators')})
                if not e[field]: del e[field]
        if e.get('see_cost') == 'none': e['see_cost'] = 0
    roof_root = OUT / 'frontier_adaptation_sources'; rm = json.loads((roof_root / 'SOURCE_MANIFEST.json').read_text())
    roof_path = 'dda/data/json/furniture_and_terrain/terrain-roofs.json'; roof_raw = (roof_root / roof_path).read_bytes()
    assert rm['pins']['dda'] == 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert hashlib.sha256(roof_raw).hexdigest() == rm['files'][roof_path]
    roof = copy.deepcopy(next(e for e in json.loads(roof_raw) if e.get('id') == 't_wood_roof'))
    entries.append(roof)
    evidence.append({'archive': roof_root.name, 'path': roof_path, 'sha256': rm['files'][roof_path]})
    entries = rename(entries, aliases)
    own = index_entries(entries)
    isolated = {n: PREFIX + n for kind, n in own if kind in ('overmap_terrain', 'overmap_special', 'nested_mapgen')}
    for kind, n in own:
        if kind == 'overmap_terrain':
            for d in ('north', 'east', 'south', 'west'): isolated[n + '_' + d] = PREFIX + n + '_' + d
    preview = rename(entries, isolated)
    for e in preview:
        if e['type'] == 'overmap_terrain': e['extras'] = ''
    # BN registers every string in a world-map matrix, including literal
    # null. Give dormant source slots private mapgen names so this opt-in
    # package cannot append generators to stock BN's global null identity.
    # No overmap terrain or special cell is created for these unused names.
    unplaced = []
    for e in preview:
        value = e.get('om_terrain')
        if not isinstance(value, list) or not isinstance(value[0], list): continue
        for y, row in enumerate(value):
            for x, name in enumerate(row):
                if name != 'null': continue
                name = PREFIX + 'unused_grid_' + str(len(unplaced))
                row[x] = name
                unplaced.append({'source': 'null', 'grid_x': x, 'grid_y': y, 'preview_mapgen_id': name})
    assert len(unplaced) == 2
    runtime_root = OUT / 'runtime_sources'; runtime_manifest = json.loads((runtime_root / 'SOURCE_MANIFEST.json').read_text())
    runtime_path = 'bn/src/mapgen/mapgen.cpp'; runtime_raw = (runtime_root / runtime_path).read_bytes()
    assert runtime_manifest['pins']['bn'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    assert hashlib.sha256(runtime_raw).hexdigest() == runtime_manifest['files'][runtime_path]['sha256']
    loader = runtime_raw.decode().split('void load_mapgen(const JsonObject& jo)', 1)[1].split('} else if (jo.has_string("om_terrain"))', 1)[0]
    assert 'load_and_add_mapgen_function(jo, mapgenid, offset, total);' in loader and '"null"' not in loader
    evidence.append({'archive': runtime_root.name, 'path': runtime_path, 'sha256': runtime_manifest['files'][runtime_path]['sha256']})
    own = index_entries(preview)
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    missing = sorted(required(preview) - own - core)
    assert not (own - BUILTIN_IDS) & (core | mods), sorted((own - BUILTIN_IDS) & (core | mods))
    report = {'status': 'civic_geometry_embedded_pending_windows', 'native_embedded': True, 'runtime_validated': False,
              'source_groups': 5, 'source_registrations': sorted(TARGETS), 'source_placements': sum(len(e['overmaps']) for e in registrations.values()),
              'special_cells': {e['id']: len(e['overmaps']) for e in registrations.values()},
              'source_z_levels': {e['id']: sorted({c['point'][2] for c in e['overmaps']}) for e in registrations.values()},
              'world_maps': len(conservation), 'nested_definitions': sum('nested_mapgen_id' in e for e in entries),
              'source_conservation': conservation, 'physical_aliases': aliases, 'isolated_ids': dict(sorted(isolated.items())),
              'deferred_registration_fields': deferred, 'new_terrain_definitions': 1, 'unplaced_grid_aliases': unplaced,
              'physical_counterpart_differences': ['Retractable locked gate uses BN locked chain-link gate: transparent, impassable and pickable; source visuals, retraction, cutting and damage behavior remain archived',
                  'Bollard uses BN small column; keypad metal door uses BN locked metal door; source device interactions remain deferred',
                  'Wooden roof retains exact source concrete physical definition and transitions'],
              'geometry_issues': issues, 'unresolved_typed_refs': missing, 'reused_sources': evidence,
              'limits': ['Embedded debug preview awaiting Windows generation; no progress credit', 'Full source and deferred later layers retained',
                         'Random nested rooms and damage overlays require source-derived fixture masks', 'Natural occurrence disabled']}
    for name, value in [('CIVIC_SITES_SHELLS.json', raw_entries), ('CIVIC_SITES_LATER_LAYERS.json', later),
                        ('CIVIC_SITES_PREVIEW_SHELL.json', preview), ('CIVIC_SITES_GEOMETRY_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check: assert path.read_text() == text, path
        else: path.write_text(text)
    print(json.dumps({k: report[k] for k in ('source_placements', 'special_cells', 'world_maps', 'nested_definitions', 'geometry_issues', 'unresolved_typed_refs')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--check', action='store_true'); prepare(p.parse_args().check)
