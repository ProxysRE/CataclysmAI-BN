#!/usr/bin/env python3
"""Resolve apartment physical references while keeping the full staging intact."""
import argparse
import collections
import copy
import json

from prepare_apartment_geometry import prepare as stage, OUT, ROOT
from prepare_container_yards import required
from prepare_regional_locations import index_entries, BUILTIN_IDS
from compare_location_catalog import read_sources
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache


def prepare(check=False):
    stage(check=True)
    raw = json.loads((OUT / 'APARTMENT_SHELLS.json').read_text(encoding='utf-8'))
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    counterparts = {}
    for kind, name in sorted(required(raw) - core):
        if kind != 'terrain':
            continue
        if name.startswith('t_carpet_linoleum_'):
            # BN has the underlying linoleum, without this DDA two-colour pattern.
            counterparts[name] = 't_linoleum_' + name.removeprefix('t_carpet_linoleum_').split('_')[0]
        else:
            for base in ('t_strconc_wall', 't_sconc_wall', 't_concrete_wall', 't_wall'):
                if name.startswith(base + '_') and ('terrain', base) in core:
                    counterparts[name] = base
                    break
    assert all(('terrain', n) in core for n in counterparts.values())
    isolated = {}
    for name in ('parking_2x1_0', 'parking_2x1_1'):
        isolated[name] = 'dda_geo_apartment_' + name
        for direction in ('north', 'east', 'south', 'west'):
            isolated[name + '_' + direction] = isolated[name] + '_' + direction
    aliases = {**counterparts, **isolated}

    def rename(v):
        if isinstance(v, str):
            return aliases.get(v, v)
        if isinstance(v, list):
            return [rename(x) for x in v]
        if isinstance(v, dict):
            return {k: rename(x) for k, x in v.items()}
        return v

    catalog, _ = read_sources()
    parent = next(e for p, text in catalog.items() if p.startswith('dda/')
                  for e in json.loads(text) if e.get('abstract') == 'apartments_tower_roof_any')
    deferred = []
    entries = []
    for e in rename(raw):
        if e.get('copy-from') == parent['abstract']:
            base = copy.deepcopy(parent)
            deferred.append({'source': e['id'], 'source_parent': copy.deepcopy(parent)})
            for key in ('abstract', 'vision_levels', 'mondensity', 'extras'):
                base.pop(key, None)
            assert base['see_cost'] == 'none'
            base['see_cost'] = 0
            base.update({k: v for k, v in e.items() if k != 'copy-from'})
            e = base
        if e['type'] == 'overmap_terrain' and 'SHOULD_NOT_SPAWN' in e.get('flags', []):
            deferred.append({'source': e['id'], 'field': 'flags', 'value': ['SHOULD_NOT_SPAWN'],
                             'note': 'Unsupported DDA registration policy; all candidate specials have occurrences [0,0]. Natural city generation is not installed.'})
            e['flags'] = [f for f in e['flags'] if f != 'SHOULD_NOT_SPAWN']
        entries.append(e)
    own = index_entries(entries)
    missing = sorted(required(entries) - own - core)
    assert not missing, missing
    mods = {(e['type'], e['id']) for e in mod_cache()['records']}
    assert not (own - BUILTIN_IDS) & (core | mods)
    nested = collections.defaultdict(list)
    for e in entries:
        if 'nested_mapgen_id' in e:
            nested[e['nested_mapgen_id']].append(e)
    todo = [n for t, n in required([e for e in entries if 'om_terrain' in e]) if t == 'nested_mapgen']
    reachable = set()
    while todo:
        name = todo.pop()
        if name == 'null' or name in reachable:
            continue
        assert name in nested, name
        reachable.add(name)
        todo += [n for t, n in required(nested[name]) if t == 'nested_mapgen']
    active = [e for e in entries if 'nested_mapgen_id' not in e or e['nested_mapgen_id'] in reachable]
    active_vertical = [{'source': e.get('om_terrain', e.get('nested_mapgen_id')), 'placement': p}
                       for e in active if e['type'] == 'mapgen'
                       for p in e['object'].get('place_nested', []) if p.get('z', 0) != 0]
    report = {
        'status': 'apartment_physical_adaptation_prepared_not_installed',
        'native_embedded': False, 'runtime_validated': False,
        'counterparts': counterparts, 'new_terrain_definitions': 0,
        'isolated_parking_aliases': isolated,
        'unresolved_typed_refs': missing, 'deferred_parent_fields': deferred,
        'reachable_nested_identities': sorted(reachable),
        'reachable_nested_definitions': sum(len(nested[n]) for n in reachable),
        'unused_nested_identities': sorted(set(nested) - reachable),
        'reachable_vertical_blockers': active_vertical,
        'adaptations': ['Unavailable wall paint reuses matching BN wall construction',
                        'Eight patterned carpet/linoleum variants reuse underlying white or gray BN linoleum; pattern appearance is omitted',
                        'Missing roof abstract is expanded from DDA into supported BN registration fields',
                        'Both source parking cells are retained; no unrelated stock parking lot substituted'],
        'remaining': ['Review BN above-neighbor predicate and multi-OMT duplicate-identity handling before native embedding',
                      'Native source and installed loading/generation',
                      'All-floor traversal, stair alignment, elevator operation and later content layers'],
        'limits': ['Full adapted staging retains unused greenhouse z-offset blockers',
                   'Reachability alone does not certify conditional stairs or actual player access',
                   'Not installed and no completion credit'],
    }
    for name, value in (('APARTMENT_ADAPTED_SHELL.json', entries), ('APARTMENT_ADAPTATION_REPORT.json', report)):
        text = json.dumps(value, indent=2, ensure_ascii=True) + '\n'
        path = OUT / name
        if check:
            assert path.read_text(encoding='utf-8') == text, path
        else:
            path.write_text(text, encoding='utf-8')
    print('Apartment references closed; reachable nested variants:', report['reachable_nested_definitions'],
          '; active z-offset blockers:', len(active_vertical))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
