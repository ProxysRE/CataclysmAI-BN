#!/usr/bin/env python3
"""Stage all five modular apartment layouts without flattening nested rooms."""
import argparse
import copy
import hashlib
import json
from collections import Counter

from prepare_geometry_layer import ROOT, OUT, extract, glyphs
from prepare_regional_locations import expand, flatten, index_entries, BUILTIN_IDS, references
from prepare_container_yards import required
from compare_location_catalog import read_sources
from bn_shared_palettes import sources as shared_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

SOURCE = OUT / 'apartment_sources'
PIN = 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'
TARGETS = {'apartment_complex_3x3', 'apartment_complex_3x3_alt',
           'apartment_complex_line', 'apartment_complex_U', 'apartment_complex_U_alt'}
LATE_NESTS = {'fire_extinguisher'}


def sources():
    manifest = json.loads((SOURCE / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['dda_commit'] == PIN
    files = {}
    for path, record in manifest['files'].items():
        raw = (SOURCE / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == record['blob_sha'], path
        files[path] = json.loads(raw)
    # Reuse already authenticated source archives, not generated adaptations.
    shared = shared_sources()
    evidence = []
    for folder, paths in (
        ('urban_sources', ('data/json/mapgen_palettes/house_general_palette.json',
                           'data/json/mapgen_palettes/common_parameters.json')),
        ('large_sites_sources', ('data/json/mapgen/nested/aux_nested.json',
                                 'data/json/mapgen/nested/shelter_nested.json')),
    ):
        root = OUT / folder
        manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        assert manifest['dda_commit'] == PIN
        for path in paths:
            raw = (root / path).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == manifest['files'][path], path
            shared['dda/' + path] = json.loads(raw)
            evidence.append({'archive': folder, 'path': path, 'sha256': manifest['files'][path]})
    root = OUT / 'waterside_adaptation_sources'
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['pins']['dda'] == PIN
    path = 'dda/data/json/mapgen/nested/house_nested.json'
    raw = (root / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest['files'][path]
    shared[path] = json.loads(raw)
    evidence.append({'archive': root.name, 'path': path, 'sha256': manifest['files'][path]})
    palettes = {e['id']: e for path, es in shared.items() if path.startswith('dda/')
                for e in es if e.get('type') == 'palette'}
    palettes.update({e['id']: e for es in files.values() for e in es if e.get('type') == 'palette'})
    originals = [copy.deepcopy(e) for path, es in files.items()
                 if '/apartment_complex/' in path for e in es if e.get('type') == 'mapgen']
    # The extended 3x3 layout places this exact two-cell parking map. Preserve
    # its source geometry rather than replacing it with an unrelated BN lot.
    originals += [copy.deepcopy(e) for e in files['data/json/mapgen/parking_lot.json']
                  if e.get('type') == 'mapgen' and 'parking_2x1_0' in set(flatten(e.get('om_terrain', [])))]
    providers = [e for path, es in shared.items() if path.startswith('dda/')
                 for e in es if 'nested_mapgen_id' in e]
    providers += [e for path, es in files.items() if '/mobile_home_park/' in path
                  for e in es if 'nested_mapgen_id' in e]
    while True:
        own = {e['nested_mapgen_id'] for e in originals if 'nested_mapgen_id' in e}
        wanted = {n for e in originals for t, n in references(expand(e['object'], palettes))
                  if t == 'nested_mapgen'} - own - LATE_NESTS - {'null'}
        additions = [copy.deepcopy(e) for e in providers if e['nested_mapgen_id'] in wanted]
        if not additions:
            assert not wanted, ('Missing structural nested providers', wanted)
            break
        originals += additions
    projection = []
    for e in originals:
        obj = e['object'] = expand(e['object'], palettes)
        assert not obj.get('palettes'), (e.get('om_terrain', e.get('nested_mapgen_id')), obj.get('palettes'))
        for g, piece in obj.get('mapping', {}).items():
            for key in ('terrain', 'furniture'):
                if key in piece:
                    assert g not in obj.get(key, {}) or obj[key][g] == piece[key]
                    obj.setdefault(key, {})[g] = copy.deepcopy(piece[key])
                    projection.append({'source': e.get('om_terrain', e.get('nested_mapgen_id')),
                                       'glyph': g, 'field': key})
        if 'fill_ter' not in obj:
            bound = set(obj.get('terrain', {})) | set(obj.get('furniture', {})) | set(obj.get('nested', {}))
            for g in sorted(glyphs(obj.get('rows', [])) - bound - {' ', '.'}):
                assert 'nested_mapgen_id' in e or 'predecessor_mapgen' in obj, g
                obj.setdefault('furniture', {})[g] = 'f_null'
    catalog, _ = read_sources()
    mapped = {n for e in originals for n in flatten(e.get('om_terrain', []))}
    registrations = {}
    for path, text in catalog.items():
        if not path.startswith('dda/'):
            continue
        for source in json.loads(text):
            if source.get('type') == 'city_building' and source.get('id') in TARGETS:
                registrations[source['id']] = copy.deepcopy(source)
                e = copy.deepcopy(source)
                e['type'] = 'overmap_special'
                originals.append(e)
            elif source.get('type') == 'overmap_terrain':
                names = set(flatten(source.get('id', []))) & mapped
                if names:
                    e = copy.deepcopy(source)
                    e['id'] = sorted(names)
                    originals.append(e)
    assert set(registrations) == TARGETS
    declared = {n for e in originals if e['type'] == 'overmap_terrain' for n in flatten(e['id'])}
    assert declared == mapped, (mapped - declared, declared - mapped)
    return originals, registrations, evidence, projection


def prepare(check=False):
    originals, registrations, evidence, projection = sources()
    nested = {e['nested_mapgen_id'] for e in originals if 'nested_mapgen_id' in e}
    entries, later, issues = extract(originals, tuple(sorted(nested)))
    aliases = {n: 'dda_geo_apartment_' + n for n in sorted(nested)}

    def rename(value):
        if isinstance(value, str):
            return aliases.get(value, value)
        if isinstance(value, list):
            return [rename(x) for x in value]
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        return value

    entries = rename(entries)
    conditionals = []
    for e in entries:
        if e['type'] == 'overmap_special':
            later.append({'source_registration': registrations[e['id']]})
            e['occurrences'] = [0, 0]
        elif e['type'] == 'overmap_terrain' and 'travel_cost_type' in e:
            later.append({'source': e['id'], 'field': 'travel_cost_type', 'value': e.pop('travel_cost_type')})
        elif e['type'] == 'mapgen':
            for place in e['object'].get('place_nested', []):
                if place.get('neighbors'):
                    conditionals.append({'source': e.get('om_terrain', e.get('nested_mapgen_id')),
                                         'placement': copy.deepcopy(place)})
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    own = index_entries(entries)
    report = {
        'status': 'apartment_geometry_staged_not_installed',
        'native_embedded': False, 'runtime_validated': False,
        'definitions': dict(Counter(e['type'] for e in entries)),
        'world_maps': sum('om_terrain' in e for e in entries),
        'unique_omt': len({n for e in entries for n in flatten(e.get('om_terrain', []))}),
        'nested_definitions': sum('nested_mapgen_id' in e for e in entries),
        'nested_identities': len(nested), 'nested_aliases': aliases,
        'special_cells': {name: len(e['overmaps']) for name, e in registrations.items()},
        'source_z_levels': {name: sorted({c['point'][2] for c in e['overmaps']}) for name, e in registrations.items()},
        'reused_authenticated_sources': evidence, 'inline_mapping_projection': projection,
        'conditional_nested_placements': conditionals, 'geometry_issues': issues,
        'unresolved_typed_refs': sorted(required(entries) - own - core),
        'core_id_overlaps': sorted((own - BUILTIN_IDS) & core),
        'bundled_mod_id_overlaps': sorted((own - BUILTIN_IDS) & mods),
        'limits': ['No native integration or completion credit',
                   'All five original city registrations are archived; no replacement of BN city generation',
                   'Conditional garage stairs, split multi-OMT variants and parameter distributions require BN review',
                   'Furniture, loot, actors and device interactions are deferred, with originals retained'],
    }
    for name, value in (('APARTMENT_SHELLS.json', entries), ('APARTMENT_LATER_LAYERS.json', later),
                        ('APARTMENT_GEOMETRY_REPORT.json', report)):
        text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        path = OUT / name
        if check:
            assert path.read_text(encoding='utf-8') == text, path
        else:
            path.write_text(text, encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'world_maps', 'unique_omt', 'nested_definitions',
                                           'special_cells', 'unresolved_typed_refs', 'geometry_issues')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
