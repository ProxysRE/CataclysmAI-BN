#!/usr/bin/env python3
"""Stage seven city sites, keeping whole-library variants and access damage."""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
from prepare_geometry_layer import ROOT, OUT, extract, glyphs
from prepare_regional_locations import flatten, references, index_entries, merge, BUILTIN_IDS
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'city_additions_sources'
PREFIX = 'dda_geo_city_add_'
TARGETS = {'synagogue', 'urban_library', 's_library_3', 'small_kindergarten',
           'office_dentist', 's_airsoft', 'office_warehouse_anduril'}


def sources():
    manifest = json.loads((SOURCE / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['dda_commit'] == 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
    assert manifest['bn_commit'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    files = {}; runtime = {}
    for path, record in manifest['files'].items():
        raw = (SOURCE / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == record['blob_sha'], path
        if path.endswith('.json'): files[path] = json.loads(raw)
        else: runtime[path] = raw.decode()
    shared = shared_sources(); evidence = []
    for folder, paths in (
        ('urban_sources', ('data/json/mapgen_palettes/common_parameters.json',
                           'data/json/mapgen_palettes/house_general_palette.json')),
        ('large_sites_sources', ('data/json/mapgen/nested/aux_nested.json',
                                 'data/json/mapgen/nested/shelter_nested.json'))):
        root = OUT / folder; m = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
        assert m['dda_commit'] == manifest['dda_commit']
        for path in paths:
            raw = (root / path).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == m['files'][path], path
            shared['dda/' + path] = json.loads(raw)
            evidence.append({'archive': folder, 'path': path, 'sha256': m['files'][path]})
    root = OUT / 'frontier_adaptation_sources'
    m = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    assert m['pins'] == {'bn': manifest['bn_commit'], 'dda': manifest['dda_commit']}
    for side in ('bn', 'dda'):
        path = side + '/data/json/furniture_and_terrain/terrain-mechanisms.json'
        raw = (root / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == m['files'][path], path
        shared[path] = json.loads(raw)
        evidence.append({'archive': root.name, 'path': path, 'sha256': m['files'][path]})
    palettes = {e['id']: e for path, es in shared.items() if path.startswith('dda/')
                for e in es if e.get('type') == 'palette'}
    palettes.update({e['id']: e for es in files.values() for e in es if e.get('type') == 'palette'})
    return files, shared, palettes, evidence, runtime


def expand(obj, palettes, variant, trail=()):
    result = {}
    for value in obj.get('palettes', []):
        if isinstance(value, dict):
            assert value == {'param': 'building_variant_palette'}
            assert variant in ('normal', 'vandalized')
            if variant == 'normal': continue
            value = 'standard_building_vandalized_palette'
        assert value not in trail, (trail, value)
        assert value in palettes, value
        merge(result, expand(palettes[value], palettes, variant, trail + (value,)))
    merge(result, {k: v for k, v in obj.items() if k not in ('type', 'id', 'palettes')})
    return result


def rename(value, aliases):
    if isinstance(value, str): return aliases.get(value, value)
    if isinstance(value, list): return [rename(v, aliases) for v in value]
    if isinstance(value, dict): return {k: rename(v, aliases) for k, v in value.items()}
    return value


def prepare(check=False):
    files, shared, palettes, evidence, runtime = sources()
    choice = palettes['standard_building_general_and_variant_palette']['parameters']['building_variant_palette']
    assert choice['scope'] == 'overmap_special'
    assert choice['default']['distribution'] == [['null_palette', 400], ['standard_building_vandalized_palette', 600]]
    catalog, _ = read_sources()
    registrations = {e['id']: e for path, text in catalog.items() if path.startswith('dda/')
                     for e in json.loads(text) if e.get('type') == 'city_building' and e.get('id') in TARGETS}
    assert set(registrations) == TARGETS
    mapped = {c['overmap'].removesuffix('_north') for e in registrations.values() for c in e['overmaps']}
    assert len(mapped) == 25
    urban_ground = {'urban_library_' + str(i) for i in range(1, 9)}
    variant_aliases = {variant: {name: name + '_' + variant for name in sorted(urban_ground)} for variant in ('normal', 'vandalized')}
    for aliases in variant_aliases.values():
        for name in sorted(urban_ground):
            aliases[name + '_north'] = aliases[name] + '_north'
    originals = []; conservation = []
    for path, es in files.items():
        for source in es:
            if source.get('type') != 'mapgen' or not (set(flatten(source.get('om_terrain', []))) & mapped): continue
            variants = ('normal', 'vandalized') if set(flatten(source['om_terrain'])) & urban_ground else (None,)
            for variant in variants:
                e = copy.deepcopy(source); e['object'] = expand(e['object'], palettes, variant)
                if variant: e['om_terrain'] = rename(e['om_terrain'], variant_aliases[variant])
                originals.append(e)
                conservation.append({'source_path': path, 'source_omt': source['om_terrain'],
                                     'preview_omt': e['om_terrain'], 'building_variant': variant,
                                     'weight': source.get('weight', 1000)})
    providers = [e for path, es in shared.items() if path.startswith('dda/') for e in es if 'nested_mapgen_id' in e]
    transforms = {e['id']: e for path, es in shared.items() if path.startswith('dda/')
                  for e in es if e.get('type') == 'ter_furn_transform'}
    physical = {e['nested_mapgen_id'] for e in providers if any(k in e['object'] for k in
                ('terrain', 'fill_ter', 'place_terrain', 'place_ter_furn_transforms'))
                or any(s.get('point', s.get('line', s.get('square'))) == 'terrain' for s in e['object'].get('set', []))}
    while True:
        additions = {e['nested_mapgen_id'] for e in providers
                     if any(t == 'nested_mapgen' and n in physical for t, n in references(e['object']))} - physical
        if not additions: break
        physical |= additions
    late_names = {e['nested_mapgen_id'] for e in providers} - physical | {'fire_extinguisher'}
    late_aliases = {n: 'null' for n in late_names}
    late_projected = set()
    def geometry_nests(e):
        if 'nested' in e['object']:
            used = glyphs(e['object'].get('rows', []))
            e['object']['nested'] = {g: p for g, p in e['object']['nested'].items() if g in used}
        late_projected.update(n for t, n in references(e['object']) if t == 'nested_mapgen' and n in late_names)
        for key in ('nested', 'place_nested'):
            if key in e['object']: e['object'][key] = rename(e['object'][key], late_aliases)
    for e in originals: geometry_nests(e)
    present = set()
    while True:
        wanted = {n for e in originals for t, n in references(e['object']) if t == 'nested_mapgen'} - present - {'null'}
        additions = [copy.deepcopy(e) for e in providers if e['nested_mapgen_id'] in wanted]
        if not additions:
            assert not wanted, ('Missing structural provider', wanted)
            break
        for e in additions:
            e['object'] = expand(e['object'], palettes, None); geometry_nests(e)
        originals += additions; present |= {e['nested_mapgen_id'] for e in additions}
    for e in originals:
        o = e['object']
        for glyph, piece in o.get('mapping', {}).items():
            for field in ('terrain', 'furniture'):
                if field in piece: o.setdefault(field, {})[glyph] = copy.deepcopy(piece[field])
        if 'fill_ter' not in o:
            for glyph in glyphs(o.get('rows', [])) - set(o.get('terrain', {})) - set(o.get('furniture', {})) - set(o.get('nested', {})) - {' ', '.'}:
                assert 'nested_mapgen_id' in e, (e.get('om_terrain'), glyph)
                o.setdefault('furniture', {})[glyph] = 'f_null'
    for name, source in registrations.items():
        for variant in (('normal', 'vandalized') if name == 'urban_library' else (None,)):
            e = copy.deepcopy(source); e['type'] = 'overmap_special'; e['occurrences'] = [0, 0]
            if variant:
                e = rename(e, variant_aliases[variant]); e['id'] += '_' + variant
            originals.append(e)
    for path, text in catalog.items():
        if not path.startswith('dda/'): continue
        for source in json.loads(text):
            if source.get('type') != 'overmap_terrain': continue
            names = set(flatten(source.get('id', []))) & mapped
            if not names: continue
            ordinary = sorted(names - urban_ground)
            if ordinary:
                e = copy.deepcopy(source); e['id'] = ordinary; originals.append(e)
            for variant in ('normal', 'vandalized'):
                if names & urban_ground:
                    e = copy.deepcopy(source); e['id'] = sorted(names & urban_ground)
                    originals.append(rename(e, variant_aliases[variant]))
    entries, later, issues = extract(originals, tuple(sorted(present)))
    transform_ids = set()
    for old, e in zip(originals, entries):
        if e['type'] == 'mapgen':
            assert old['object'].get('rows') == e['object'].get('rows')
            if old['object'].get('place_ter_furn_transforms'):
                e['object']['place_ter_furn_transforms'] = copy.deepcopy(old['object']['place_ter_furn_transforms'])
                transform_ids |= {p['transform'] for p in e['object']['place_ter_furn_transforms']}
        elif e['type'] == 'overmap_terrain' and 'travel_cost_type' in e:
            later.append({'source': e['id'], 'field': 'travel_cost_type', 'value': e.pop('travel_cost_type')})
    assert not issues, issues
    later += [{'source_registration': e} for e in registrations.values()]
    # Full source maps (before late-only nested projection) remain available
    # in the authenticated archives. Record the projection explicitly.
    later.append({'late_only_nested_ids_projected_to_null': sorted(late_projected)})
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    raw_entries = copy.deepcopy(entries)
    aliases = {'t_door_elocked': 't_door_locked', 't_door_elocked_alarm': 't_door_locked_alarm',
               't_door_elocked_peep': 't_door_locked_peep', 't_curtains_alarm': 't_curtains',
               't_window_domestic_alarm': 't_window_domestic', 't_window_no_curtains_alarm': 't_window_no_curtains',
               't_window_no_curtains_open_alarm': 't_window_no_curtains_open', 't_window_open_alarm': 't_window_open'}
    for kind, name in sorted(required(entries) - core):
        if kind != 'terrain': continue
        if name.startswith('t_carpet_linoleum_'):
            aliases[name] = 't_linoleum_' + name.removeprefix('t_carpet_linoleum_').split('_')[0]
        elif name.startswith(('t_carpet_wood_', 't_carpet_concrete_', 't_carpet_metal_')):
            aliases[name] = 't_carpet_' + name.rsplit('_', 1)[1]
        else:
            for base in ('t_strconc_wall', 't_sconc_wall', 't_concrete_wall', 't_wall'):
                if name.startswith(base + '_') and ('terrain', base) in core: aliases[name] = base; break
    entries = rename(entries, aliases)
    abstract = next(e for path, text in catalog.items() if path.startswith('dda/')
                    for e in json.loads(text) if e.get('abstract') == 'generic_city_building_roof')
    deferred_registration = []
    for index, e in enumerate(entries):
        if e.get('copy-from') != abstract['abstract']: continue
        base = copy.deepcopy(abstract)
        base.pop('abstract'); base.pop('delete')
        assert base['copy-from'] == 'generic_city_building_no_sidewalk'
        merge(base, {k: v for k, v in e.items() if k != 'copy-from'})
        entries[index] = base
        deferred_registration.append({'source': e['id'], 'expanded_abstract': abstract})
    mechanism_path = '/data/json/furniture_and_terrain/terrain-mechanisms.json'
    source_reader = next(e for e in shared['dda' + mechanism_path] if e.get('id') == 't_card_office_warehouse_anduril')
    stock_reader = next(e for e in shared['bn' + mechanism_path] if e.get('id') == 't_card_science')
    reader = copy.deepcopy(stock_reader)
    reader.update({k: source_reader[k] for k in ('id', 'name', 'description', 'symbol', 'color')})
    reader['examine_action'] = 'none'
    aliases[source_reader['id']] = PREFIX + 'anduril_reader'
    entries.append(reader)
    entries = rename(entries, {source_reader['id']: aliases[source_reader['id']]})
    transform_projection = []
    for name in sorted(transform_ids):
        source = transforms[name]; out = {'type': 'ter_furn_transform', 'id': name, 'terrain': []}
        skipped = []
        for rule in source['terrain']:
            valid = [n for n in rule['valid_terrain'] if ('terrain', n) in core]
            skipped += [n for n in rule['valid_terrain'] if ('terrain', n) not in core]
            if not valid: continue
            assert ('terrain', rule['result']) in core, (name, rule['result'])
            out['terrain'].append({'result': rule['result'], 'valid_terrain': valid, 'valid_flags': []})
        assert out['terrain']
        entries.append(out)
        transform_projection.append({'source_transform': copy.deepcopy(source), 'omitted_unavailable_BN_inputs': skipped})
    own = index_entries(entries); isolated = {name: PREFIX + name for kind, name in own if kind in ('overmap_terrain', 'nested_mapgen', 'ter_furn_transform')}
    for kind, name in own:
        if kind == 'overmap_terrain':
            for direction in ('north', 'east', 'south', 'west'): isolated[name + '_' + direction] = PREFIX + name + '_' + direction
        elif kind == 'overmap_special': isolated[name] = PREFIX + name
    preview = rename(entries, isolated)
    for e in preview:
        if e['type'] == 'overmap_terrain': e['extras'] = ''
    own = index_entries(preview)
    missing = sorted(required(preview) - own - core)
    assert not (own - BUILTIN_IDS) & (core | mods)
    cpp = runtime['bn/src/magic/magic_ter_fur_transform.cpp']
    assert 'valid_terrain' in cpp and 'load_transform_results(jo, "result", list)' in cpp
    report = {'status': 'seven_city_sites_prepared_pending_native_schema_and_generation',
              'native_embedded': False, 'runtime_validated': False,
              'source_sites': sorted(TARGETS), 'source_placements': sum(len(e['overmaps']) for e in registrations.values()),
              'preview_cases': sum(e['type'] == 'overmap_special' for e in preview),
              'preview_placements': sum(len(e['overmaps']) for e in preview if e['type'] == 'overmap_special'),
              'world_maps': sum('om_terrain' in e for e in preview), 'nested_definitions': sum('nested_mapgen_id' in e for e in preview),
              'building_variant_scope': {'parameter': 'building_variant_palette', 'source_scope': 'overmap_special',
                  'source_weights': [['null_palette', 400], ['standard_building_vandalized_palette', 600]],
                  'debug_variants': ['urban_library_normal', 'urban_library_vandalized'],
                  'note': 'Whole-building choices isolated across both floors; natural time/variant selection not enabled'},
              'source_conservation': conservation, 'physical_aliases': aliases,
              'deferred_registration_fields': deferred_registration,
              'physical_counterpart_differences': ['Electronic keypad wood doors use BN locked wood-door counterparts',
                  'Window alarm variants retain BN physical window/curtain states; DDA alarm behavior deferred',
                  'Anduril card reader retains source name/appearance and BN card-reader physical geometry; badge/hacking/door-unlock interaction deferred, no science-card substitution'],
              'Anduril_reader': {'source_definition': source_reader, 'BN_physical_provider': stock_reader['id'],
                                 'preview_id': aliases[source_reader['id']], 'examine_action': 'none'},
              'transform_projection': transform_projection, 'transform_count': len(transform_ids),
              'isolated_ids': dict(sorted(isolated.items())), 'unresolved_typed_refs': missing,
              'geometry_issues': issues, 'reused_sources': evidence,
              'limits': ['Geometry only; furnishings, loot, actors and interactions archived for later layers',
                         'Eight debug cases represent seven source city registrations, preserving whole-building library variation',
                         'Door/window transformations use existing BN machinery; native operation still requires runtime validation',
                         'Transforms omit source input terrain absent from BN; full original rules remain archived',
                         'Empty-loot and deterministic-navigation masks for random rooftop/damage overlays must be prepared before embedding',
                         'No new generation credit or replacement of stock BN city locations']}
    for name, value in [('CITY_ADDITIONS_SHELLS.json', raw_entries), ('CITY_ADDITIONS_LATER_LAYERS.json', later),
                        ('CITY_ADDITIONS_PREVIEW_SHELL.json', preview), ('CITY_ADDITIONS_GEOMETRY_REPORT.json', report)]:
        path = OUT / name; text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        if check: assert path.read_text() == text, path
        else: path.write_text(text)
    print(json.dumps({k: report[k] for k in ('source_placements', 'preview_cases', 'preview_placements', 'world_maps', 'nested_definitions', 'transform_count', 'unresolved_typed_refs')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
