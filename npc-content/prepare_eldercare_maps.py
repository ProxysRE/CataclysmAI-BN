#!/usr/bin/env python3
"""Prepare complete BN-schema eldercare maps without enabling world placement."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from prepare_eldercare import ROOT, PINS, prepare as prepare_dependencies
from prepare_civilians import mod_sources
from prepare_regional_locations import index_entries, BUILTIN_IDS
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache

FOLDER = ROOT / 'eldercare/native_candidate'
SITES = ('nursing_home', 'retirement_community')
LUA_MARKER = '  -- DDA eldercare maps have explicit source population tables.\n  "nursing_home",\n  "retirement_community",\n'


def candidate_lua():
    from prepare_civilians import lua_payload
    source = lua_payload()
    anchor = 'local NPC_TERRAINS = {\n'
    assert source.count(anchor) == 1
    return source.replace(anchor, anchor + LUA_MARKER, 1)


def payloads():
    layer = json.loads((ROOT / 'eldercare/ADAPTED_LOCATIONS.json').read_text())
    assert not layer['dependencies']['source_candidates']
    result = copy.deepcopy(layer['locations'])
    for entries in result.values():
        for e in entries:
            if e['type'] == 'mapgen':
                e['method'] = 'json'
                for loot in e['object'].get('place_loot', []):
                    if loot.get('group') == 'memorial':
                        loot['group'] = 'makeshift_memorial'
                for machine in e['object'].get('vendingmachines', {}).values():
                    assert machine.pop('lootable') is True
            elif e['type'] == 'overmap_terrain':
                e.pop('vision_levels', None)
                if e.get('copy-from') == 'road_abstract':
                    # Missing DDA parent is not a typed mapgen leaf reference.
                    # Use BN's own road land-use parent and retain source display.
                    e['copy-from'] = 'generic_road'
                    e.setdefault('name', 'road')
                    e.setdefault('color', 'dark_gray')
                    e.setdefault('see_cost', 0)
                    e.setdefault('looks_like', 'road')
                if isinstance(e.get('see_cost'), str):
                    # BN visibility uses numeric cost. Fine DDA categories are
                    # an intentional approximation, rather than loader input.
                    e['see_cost'] = 0 if e['see_cost'] in ('none', 'all_clear') else 2
            elif e['type'] == 'overmap_special':
                e.pop('priority', None)  # No equivalent special-priority loader.
                e['flags'] = ['UNIQUE' if f == 'OVERMAP_UNIQUE' else f
                              for f in e.get('flags', [])]
                for cell in e['overmaps']:
                    if cell.get('overmap') in tuple('s_lot_no_sidewalk_' + d for d in ('north','east','south','west')):
                        cell['overmap'] = 's_lot'  # Stock BN NO_ROTATE parking lot.
                    if cell.get('overmap') in ('sewer_sub_station','underground_sub_station'):
                        cell['overmap'] += '_west'  # Align stock BN station's surface rotation.
                for c in e.get('connections', []):
                    kind = c.pop('terrain')
                    assert c['connection'] == {'road': 'local_road', 'sewer': 'sewer_tunnel', 'subway': 'subway_tunnel'}[kind]
            else:
                raise AssertionError(('Unexpected declaration', e['type']))
    return result


def terrain_ids(entry):
    ids = entry['id']
    return ids if isinstance(ids, list) else [ids]


def schema_refs(entries):
    """Extend the existing map-leaf audit with previously uncovered positions."""
    from prepare_regional_locations import references
    refs = set()
    def value(kind, v):
        if isinstance(v, str): refs.add((kind, v))
        elif isinstance(v, list):
            for x in v:
                value(kind, x[0] if isinstance(x, list) and len(x) == 2 and isinstance(x[1], int) else x)
        elif isinstance(v, dict):
            for key in ('default', 'fallback', 'distribution'):
                if key in v: value(kind, v[key])
    for e in entries:
        if e['type'] == 'overmap_terrain':
            if 'copy-from' in e: refs.add(('overmap_terrain_abstract', e['copy-from']))
            # looks_like is a display hint, not necessarily a declared OMT.
        if e['type'] != 'mapgen': continue
        obj = e['object']
        refs.update(references(obj))
        for param in obj.get('parameters', {}).values():
            assert param['type'] == 'ter_str_id'
            value('terrain', param['default'])
        for liquid in obj.get('liquids', {}).values(): value('item', liquid['liquid'])
        for loot in obj.get('place_loot', []):
            for key, kind in (('group','item_group'),('item','item')):
                if key in loot: value(kind, loot[key])
        # "monster" palette bindings use the direct monster piece in BN.
        for binding in obj.get('monster', {}).values():
            for b in binding if isinstance(binding, list) else [binding]:
                for key, kind in (('monster','MONSTER'),('group','monstergroup')):
                    if key in b: value(kind, b[key])
    return refs


def geometry(entries):
    maps = {}
    rows_count = 0
    for e in entries:
        if e['type'] != 'mapgen' or 'om_terrain' not in e: continue
        grid = e['om_terrain']
        grid = [[grid]] if isinstance(grid, str) else ([grid] if isinstance(grid[0], str) else grid)
        rows = e['object']['rows']
        assert len(rows) == len(grid) * 24
        assert {len(row) for row in grid} == {len(grid[0])}
        assert {len(row) for row in rows} == {len(grid[0]) * 24}
        rows_count += len(rows)
        for y, line in enumerate(grid):
            for x, name in enumerate(line):
                assert name not in maps, ('Duplicate OMT mapgen', name)
                maps[name] = {'entry': e, 'offset': [x*24, y*24]}
    cells = []
    constraint_only = []
    external = []
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    evidence = json.loads((ROOT / 'eldercare/MAP_SCHEMA_EVIDENCE.json').read_text())
    external_defs = {e['id']:e for es in evidence['bn_external_terrain_sources'].values() for e in es}
    for e in entries:
        if e['type'] != 'overmap_special': continue
        seen = set()
        for cell in e['overmaps']:
            point = tuple(cell['point'])
            assert point not in seen, ('Duplicate special coordinate', e['id'], point)
            seen.add(point)
            if 'overmap' not in cell:
                assert set(cell) == {'point', 'locations'}
                constraint_only.append({'special': e['id'], **cell})
                continue
            name = cell['overmap']
            suffix = next((s for s in ('_north','_east','_south','_west') if name.endswith(s)), None)
            base = name[:-len(suffix)] if suffix else name
            if name.startswith('sewer_') and name[6:] in ('es','ew','esw','sw','ns','nes','nsw','ne','new','wn'):
                base = 'sewer'  # Verified BN LINEAR terrain; suffixes are native peers.
            if base not in maps:
                assert ('overmap_terrain', base) in core, ('Placement lacks mapgen or core provider', e['id'], base)
                assert base in external_defs, ('Missing source-reviewed external provider', base)
                flags = external_defs[base].get('flags',[])
                if base == 'sewer':
                    assert 'LINEAR' in flags
                elif suffix:
                    assert not {'LINEAR','NO_ROTATE'} & set(flags)
                else:
                    assert 'NO_ROTATE' in flags, ('Bare rotatable BN terrain', name)
                external.append({'special': e['id'], **cell})
                continue
            assert suffix == '_north', ('Unexpected rotated custom map', name)
            cells.append({'special': e['id'], 'point': list(point), 'terrain': base,
                          'mapgen_offset': maps[base]['offset']})
        for c in e.get('connections', []):
            assert tuple(c['from']) in seen, ('Connection origin outside site', e['id'], c)
            assert sum(abs(a-b) for a,b in zip(c['point'],c['from'])) == 1, c
    return {'mapgen_tiles': len(maps), 'row_count': rows_count, 'placed_cells': len(cells),
            'levels': sorted({c['point'][2] for c in cells + external}), 'cells': cells,
            'constraint_only_cells': constraint_only, 'reused_external_cells': external}


def prepare(check=False, bn_data=None):
    prepare_dependencies(check=True)
    evidence = json.loads((ROOT / 'eldercare/MAP_SCHEMA_EVIDENCE.json').read_text())
    assert evidence['bn_pin'] == PINS['bn'] and evidence['dda_pin'] == PINS['dda']
    assert evidence['bn_road']['abstract'] == 'generic_road'
    assert hashlib.sha256((ROOT / 'eldercare/MEMORIAL_SOURCE.json').read_bytes()).hexdigest() == evidence['dda_memorial_snapshot_sha256']
    if bn_data:
        for path, entries in evidence['bn_external_terrain_sources'].items():
            actual = json.loads((bn_data / path).read_text(encoding='utf-8'))
            assert all(e in actual for e in entries), path
        road = json.loads((bn_data / 'data/json/overmap/overmap_terrain/overmap_terrain_abstract.json').read_text(encoding='utf-8'))
        assert evidence['bn_road'] in road
        misc = json.loads((bn_data / evidence['bn_memorial_source']).read_text(encoding='utf-8'))
        assert evidence['bn_memorial'] in misc
    payload = payloads()
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mods = mod_cache()
    from prepare_civilians import mod_providers
    from prepare_eldercare import native_data
    from prepare_eldercare_assets import native_data as assets
    from prepare_eldercare_loot import native_data as loot
    from prepare_eldercare_fauna import native_data as fauna
    provided = core | mod_providers() | index_entries(native_data()+assets()+loot()+fauna())
    declared = index_entries(sum(payload.values(), [])) - BUILTIN_IDS
    assert not declared & core
    assert not declared & {(r['type'],r['id']) for r in mods['records']}
    reports = {}
    for site, entries in payload.items():
        unknown = schema_refs(entries) - provided - declared
        reports[site] = {'types': dict(Counter(e['type'] for e in entries)), 'geometry': geometry(entries),
                         'unresolved_extended_refs': sorted(unknown)}
        assert not unknown, (site, sorted(unknown))
    report = {'pins': PINS, 'installed': False, 'optional_mod_dependencies': ['civilians'],
              'activation_ready': False, 'fixed_special_constraint_bridge': 'Prepared in prepare_frontage.py; native validation pending', 'sites': reports, 'validation': 'Static BN schema adaptation and extended typed references; not native load or generation validation',
              'intentional_adaptations': ['BN numeric overmap visibility: none/all_clear=0, remaining categories=2',
                    'DDA road_abstract -> existing BN generic_road with source road display; no new duplicate road parent',
                    'DDA OVERMAP_UNIQUE -> BN UNIQUE; existing BN GLOBALLY_UNIQUE retained unchanged',
                    'DDA special priority omitted; other source flags retained as metadata, unsupported BN behaviors are not implied',
                    'DDA memorial loot -> stock BN makeshift_memorial: candles/photos/keepsakes; no duplicate broad memorial subsystem or imported currency',
                    'BN sewer_sub_station is rotatable; west peer matches the surface station',
                    'DDA parking-lot placements -> stock BN s_lot (NO_ROTATE), as in the karting adapter',
                    'Vending lootable=true -> stock BN vending behavior; parameters and source geometry retained'],
              'remaining': ['Native source/installed validation of the prepared fixed-special constraint bridge for three road-frontage cells',
                    'Native initialization and generation for every placed cell',
                    'Review stairs/elevators, edge alignment and placement balance in game',
                    'Install candidate Civilians main.lua exclusion change atomically with maps; source/installed Lua runtime validation']}
    outputs = {FOLDER / (site+'.json'): json.dumps(entries,indent=2,ensure_ascii=True)+'\n' for site, entries in payload.items()}
    outputs[FOLDER / 'Civilians_main.lua'] = candidate_lua()
    outputs[ROOT / 'eldercare/MAP_ADAPTATION_REPORT.json'] = json.dumps(report,indent=2)+'\n'
    for path,text in outputs.items():
        if check: assert path.read_text() == text,path
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text)
    print('PASS: complete eldercare map candidates:', {s:{k:v for k,v in r['geometry'].items() if k not in ('cells','constraint_only_cells','reused_external_cells')} for s,r in reports.items()})

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true')
    p.add_argument('--bn-data',type=Path)
    a=p.parse_args()
    prepare(a.check,a.bn_data)
