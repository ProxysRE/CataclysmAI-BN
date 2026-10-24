#!/usr/bin/env python3
"""Stage Alcatraz, the refugee center and the high-rise hospital without changing the validated native preview."""
import argparse
import copy
import hashlib
import json
from prepare_geometry_layer import ROOT, OUT, extract, glyphs
from prepare_city_additions_geometry import sources as city_sources, expand, rename
from prepare_regional_locations import flatten, references, index_entries, BUILTIN_IDS, merge
from prepare_container_yards import required
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'institution_sources'
TARGETS = {'Alcatraz Prison', 'evac_center', 'urban_35_hospital'}
PREFIX = 'dda_geo_institution_'


def strip_direction(name):
    for suffix in ('_north', '_east', '_south', '_west'):
        if name.endswith(suffix): return name[:-len(suffix)]
    return name


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
    prison_root = ROOT / 'island_prison'; pm = json.loads((prison_root / 'SOURCE_MANIFEST.json').read_text())
    assert pm['DDA_commit'] == manifest['dda_commit'] and pm['BN_commit'] == manifest['bn_commit']
    for path in ('data/json/mapgen/prison/prison_alcatraz.json', 'data/json/mapgen_palettes/prison.json'):
        raw = (prison_root / 'upstream' / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pm['files'][path], path
        files['island_prison/upstream/' + path] = json.loads(raw)
        evidence.append({'archive': 'island_prison/upstream', 'path': path, 'sha256': pm['files'][path]})
    for es in [es for p, es in shared.items() if p.startswith('dda/')] + list(files.values()):
        for e in es:
            if e.get('type') == 'palette': palettes[e['id']] = e
    return files, shared, palettes, evidence


def prepare(check=False):
    files, shared, palettes, evidence = sources()
    catalog, _ = read_sources()
    registrations = {e['id']: e for p, text in catalog.items() if p.startswith('dda/')
                     for e in json.loads(text) if e.get('type') in ('city_building', 'overmap_special') and e.get('id') in TARGETS}
    assert registrations.keys() == TARGETS
    requested = {strip_direction(c['overmap']) for e in registrations.values() for c in e['overmaps'] if 'overmap' in c}
    originals = []; conservation = []
    for path, es in files.items():
        if path == 'data/json/mapgen/special.json': continue # Context providers are adapted explicitly below.
        for src in es:
            if src.get('type') != 'mapgen' or not set(flatten(src.get('om_terrain', []))) & requested: continue
            e = copy.deepcopy(src); e['object'] = expand(e['object'], palettes, None)
            originals.append(e)
            conservation.append({'path': path, 'source_omt': src['om_terrain'], 'weight': src.get('weight', 1000)})
    mapped = {n for e in originals for n in flatten(e['om_terrain'])} - {'null'}
    external = sorted(requested - mapped)
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
    # Soil is a solid wall in these source maps, never a traversable dirt floor.
    # Project before the older generic extractor's terrain aliases are applied.
    originals = rename(originals, {'t_soil': PREFIX + 'soil'})
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
        if parent in ('generic_city_building_roof', 'road_abstract'):
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
    # The source hardcoded registration proves deep_rock and empty_rock both
    # uniformly generate t_rock. Keep special identities, avoiding natural
    # predecessor mapgen and its events. Earth contexts stay solid as well.
    context_names = ('solid_earth', 'special_earth', 'special_rock', 'special_deep_rock')
    source_context = {n: copy.deepcopy(e) for p, text in catalog.items() if p.startswith('dda/')
                      for e in json.loads(text) if e.get('type') == 'overmap_terrain'
                      for n in flatten(e.get('id', [])) if n in context_names}
    rock = next(e for p, text in catalog.items() if p.startswith('dda/')
                for e in json.loads(text) if e.get('type') == 'overmap_terrain'
                and set(flatten(e.get('id', []))) == {'empty_rock', 'deep_rock'})
    assert rock['uniform_terrain'] == 't_rock'
    assert source_context['solid_earth']['uniform_terrain'] == 't_soil'
    for name in context_names:
        src = source_context[name]
        deferred.append({'source_context_definition': src})
        omt = {k: copy.deepcopy(src[k]) for k in ('type', 'name', 'sym', 'color', 'flags')}
        omt.update(id=name, see_cost=5)
        entries.append(omt)
        terrain = PREFIX + 'soil' if name in ('solid_earth', 'special_earth') else 't_rock'
        entries.append({'type': 'mapgen', 'om_terrain': name, 'method': 'json', 'object': {'fill_ter': terrain}})
    deferred.append({'source_rock_context_definition': rock,
                     'projection': 'Same fixed t_rock geometry; no natural mapgen inheritance'})
    walls = files['data/json/furniture_and_terrain/terrain-walls.json']
    wall = next(e for e in walls if e.get('abstract') == 't_abstract_wall')
    soil = next(e for e in walls if e.get('id') == 't_soil')
    earth = next(e for e in walls if e.get('abstract') == 't_abstract_wall_earthen')
    physical_soil = {k: copy.deepcopy(wall[k]) for k in ('type', 'symbol', 'move_cost', 'coverage', 'connects_to')}
    physical_soil.update({k: copy.deepcopy(soil[k]) for k in ('name', 'description', 'roof')})
    physical_soil.update(id=PREFIX + 'soil', color=earth['color'], looks_like='t_rock',
                         flags=[f for f in wall['flags'] if f != 'AUTO_WALL_SYMBOL'])
    floor_root = OUT / 'urban_adaptation_sources'
    fm = json.loads((floor_root / 'SOURCE_MANIFEST.json').read_text())
    floor_path = 'bn/data/json/furniture_and_terrain/terrain-floors-outdoors.json'
    floor_raw = (floor_root / floor_path).read_bytes()
    assert fm['pins']['bn'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    assert hashlib.sha256(floor_raw).hexdigest() == fm['files'][floor_path]
    floors = {e['id']: e for e in json.loads(floor_raw) if e.get('type') == 'terrain'}
    earth_cap = copy.deepcopy(floors['t_dirt'])
    earth_cap.update(id=PREFIX + 'earth_cap', looks_like='t_dirt',
                     bash=copy.deepcopy(floors['t_rock_floor_no_roof']['bash']))
    physical_soil['roof'] = earth_cap['id']
    entries.append(earth_cap)
    deferred.append({'source': soil['id'], 'source_roof': soil['roof'], 'BN_roof': earth_cap,
                     'reason': 'BN automatic roofs require bash_below; use stock dirt surface and stock underground floor bashing'})
    evidence.append({'archive': floor_root.name, 'path': floor_path, 'sha256': fm['files'][floor_path]})
    # Mining yields and source-specific NATURAL_UNDERGROUND behavior belong to
    # the interaction layer. Preserve the physical wall and roof in this shell.
    entries.append(physical_soil)
    liquid_root = OUT / 'waterside_adaptation_sources'
    lm = json.loads((liquid_root / 'SOURCE_MANIFEST.json').read_text())
    liquid_path = 'dda/data/json/furniture_and_terrain/terrain-liquids.json'
    liquid_raw = (liquid_root / liquid_path).read_bytes()
    assert lm['pins']['dda'] == 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert hashlib.sha256(liquid_raw).hexdigest() == lm['files'][liquid_path]
    puddle = next(e for e in json.loads(liquid_raw) if e.get('id') == 't_puddle')
    physical_puddle = {k: copy.deepcopy(puddle[k]) for k in ('type', 'name', 'description', 'symbol', 'color', 'move_cost', 'looks_like')}
    physical_puddle.update(id=PREFIX + 'puddle', examine_action='none',
                          flags=['TRANSPARENT', 'NO_SCENT', 'SWIMMABLE', 'SHALLOW_WATER'])
    entries.append(physical_puddle)
    aliases['t_puddle'] = PREFIX + 'puddle'
    deferred += [{'source_terrain_definition': soil, 'physical_definition': physical_soil,
                  'deferred': ['Mining/bashing yield and NATURAL_UNDERGROUND behavior']},
                 {'source_terrain_definition': puddle, 'physical_definition': physical_puddle,
                  'deferred': ['Finite water inventory and collection; no infinite source substitution',
                               'DDA water temperature and freezing subsystem excluded']}]
    later += copy.deepcopy(deferred[-2:])
    evidence.append({'archive': liquid_root.name, 'path': liquid_path, 'sha256': lm['files'][liquid_path]})
    aliases = {k: v for k, v in aliases.items() if ('terrain', k) in required(entries)}
    entries = rename(entries, aliases)
    own = index_entries(entries)
    isolated = {n: PREFIX + n for kind, n in own if kind in ('overmap_terrain', 'overmap_special', 'nested_mapgen')}
    for kind, n in own:
        if kind == 'overmap_terrain':
            for d in ('north', 'east', 'south', 'west'): isolated[n + '_' + d] = PREFIX + n + '_' + d
    preview = rename(entries, isolated)
    for e in preview:
        if e['type'] == 'overmap_terrain': e['extras'] = ''
    own = index_entries(preview); own.discard(('mapgen', 'null'))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    missing = sorted(required(preview) - own - core)
    assert not (own - BUILTIN_IDS) & (core | mods), sorted((own - BUILTIN_IDS) & (core | mods))
    report = {'status': 'institution_geometry_embedded_pending_windows', 'native_embedded': True, 'runtime_validated': False,
              'source_groups': 3, 'source_registrations': sorted(TARGETS), 'source_placements': sum(sum('overmap' in c for c in e['overmaps']) for e in registrations.values()),
              'special_cells': {e['id']: sum('overmap' in c for c in e['overmaps']) for e in registrations.values()},
              'source_z_levels': {e['id']: sorted({c['point'][2] for c in e['overmaps'] if 'overmap' in c}) for e in registrations.values()},
              'world_maps': len(conservation), 'nested_definitions': sum('nested_mapgen_id' in e for e in entries),
              'source_conservation': conservation, 'physical_aliases': aliases, 'isolated_ids': dict(sorted(isolated.items())),
              'deferred_registration_fields': deferred, 'external_source_omt': external,
              'geometry_issues': issues, 'unresolved_typed_refs': missing, 'reused_sources': evidence,
              'context_projection': {'earth': PREFIX + 'soil', 'rock': 't_rock', 'see_cost': 5,
                  'source_context_ids': list(context_names), 'source_deep_and_empty_rock': rock},
              'physical_definitions': [physical_soil, physical_puddle, earth_cap],
              'limits': ['Native fixture candidate embedded; Windows generation pending; no progress credit', 'Full source and deferred later layers retained',
                         'All lake/rock/earth context cells retained; validate every floor before embedding',
                         'Soil mining yields and finite puddle water collection deferred; DDA temperature subsystem excluded', 'Natural occurrence disabled']}
    for name, value in [('INSTITUTION_SITES_SHELLS.json', raw_entries), ('INSTITUTION_SITES_LATER_LAYERS.json', later),
                        ('INSTITUTION_SITES_PREVIEW_SHELL.json', preview), ('INSTITUTION_SITES_GEOMETRY_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check: assert path.read_text() == text, path
        else: path.write_text(text)
    print(json.dumps({k: report[k] for k in ('source_placements', 'special_cells', 'world_maps', 'nested_definitions', 'geometry_issues', 'unresolved_typed_refs')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--check', action='store_true'); prepare(p.parse_args().check)
