#!/usr/bin/env python3
"""Integrate the complete DDA circuit using BN mapgen, vehicles and containers."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from prepare_regional_locations import build, references, index_entries
from quest_dependency_graph import namespace, ids
from bn_loot_containers import package_groups

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'karting'
PAYLOAD = 'data/json/dda_karting_circuit.json'
GROUPS = ['cash_register_full', 'cash_register_looted', 'cash_register_empty', 'cash_register_random']


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / name).read_text() for name in manifest['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][path]['sha256']
    return files


def prepare_data():
    files = sources()
    result = copy.deepcopy(build()['karting.json'])
    for e in result:
        if e['type'] == 'mapgen':
            e['method'] = 'json'
            for machine in e['object'].get('vendingmachines', {}).values():
                assert machine.pop('lootable') is True  # BN's existing place_vending behavior.
        if e['type'] == 'vehicle':
            for location in e['parts']:
                location['parts'] = ['xlframe_vertical' if p == 'xlframe#vertical' else p for p in location['parts']]
        if e['type'] == 'overmap_special':
            for cell in e.get('overmaps', []):
                if cell.get('overmap') == 's_lot_no_sidewalk_south':
                    cell['overmap'] = 's_lot'  # BN parking lot is NO_ROTATE.
            e['flags'] = ['UNIQUE' if f == 'OVERMAP_UNIQUE' else f for f in e['flags']]
            for connection in e.get('connections', []):
                assert connection.pop('terrain') == 'road'
                connection['connection'] = 'local_road'
    source_groups = json.loads(files['dda/data/json/itemgroups/cash_register.json'])
    for source in source_groups:
        if source.get('id') not in GROUPS:
            continue
        group = copy.deepcopy(source)
        if group['id'] == 'cash_register_full':
            # BN money_bundle is 250 ml, not an individual banknote. Three
            # bundles fit the original 1 L cash drawer without overflow.
            group['items'] = [{'item': 'money_bundle', 'prob': 80, 'count': [1, 3]}]
        elif group['id'] == 'cash_register_looted':
            group['items'] = [{'item': 'money_bundle', 'prob': 15, 'count': 1}, ['survnote', 4]]
        result.append(group)
    cash = copy.deepcopy(next(e for e in json.loads(files['dda/data/json/items/generic.json']) if e.get('id') == 'cash_register'))
    cash['type'] = 'CONTAINER'
    pocket = cash.pop('pocket_data')[0]
    assert pocket['max_contains_volume'] == '1 L' and pocket['rigid'] is True
    cash['contains'] = pocket['max_contains_volume']
    cash['rigid'] = True
    cash['bashing'] = cash.pop('melee_damage')['bash']
    cash.pop('to_hit')  # DDA structured grip/balance schema has no BN equivalent.
    cash.pop('longest_side')
    cash.pop('flags')
    result.append(cash)
    return package_groups(result)


def required_refs(payload):
    refs = {r for e in payload if e['type'] == 'mapgen' for r in references(e['object'])}
    for e in payload:
        if e['type'] == 'vehicle':
            for location in e['parts']:
                for part in location['parts']:
                    refs.add(('vehicle_part', part if isinstance(part, str) else part['part']))
                    if isinstance(part, dict) and part.get('fuel'):
                        refs.add(('item', part['fuel']))
        if e['type'] == 'item_group':
            refs.update(references({'items': {'_': {'item': e}}}))
        if e['type'] in ('GENERIC', 'CONTAINER'):
            if 'copy-from' in e:
                refs.add(('item', e['copy-from']))
            material = e.get('material', [])
            refs.update(('material', m) for m in ([material] if isinstance(material, str) else material))
    return refs - {('nested_mapgen', 'null')}


def validate_bn(root, payload):
    files = sources()
    for path, text in files.items():
        if path.startswith('bn/'):
            assert (root / path[3:]).read_text(encoding='utf-8') == text, 'Pinned BN baseline drift: ' + path
    validate_json_only(root, payload)


def prepare(check=False, bn_source=None, bn_data=None):
    payload = prepare_data()
    from check_placement_terrain import check_placements
    check_placements(payload)
    if bn_source:
        validate_bn(bn_source, payload)
    elif bn_data:
        # Fast CI has JSON only; C++ baselines are preserved for review and
        # checked separately by the native build before applying the patch.
        files = sources()
        for path, text in files.items():
            if path.startswith('bn/data/'):
                assert (bn_data / path[3:]).read_text(encoding='utf-8') == text, path
        validate_json_only(bn_data, payload)
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    path = ROOT / 'native/dda_karting_circuit.json'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)


def validate_json_only(root, payload):
    # Same ID closure/collision logic, without requiring sparse checkout to
    # contain C++ files. Never weakens JSON validation.
    # validate_bn's source comparison is deliberately separate from closure.
    index = set()
    money_definition = None
    paths = sorted((root / 'data/json').rglob('*.json'))
    assert len(paths) > 100
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data if isinstance(data, list) else [data]
        index.update(index_entries(entries))
        for entry in entries:
            if namespace(entry) == 'item' and entry.get('id') == 'money_bundle':
                money_definition = entry
    new_ids = {(namespace(e), i) for e in payload for i in ids(e)}
    assert not new_ids & index, sorted(new_ids & index)
    assert not (required_refs(payload) - index - new_ids), sorted(required_refs(payload) - index - new_ids)
    assert ('item', 'money_bundle') in index
    expected_money = next(e for e in json.loads(sources()['bn/data/json/items/generic.json']) if e.get('id') == 'money_bundle')
    assert money_definition == expected_money, 'BN money bundle definition drift'
    print('PASS: native karting typed dependency closure against all BN JSON')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    p.add_argument('--bn-data', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source, a.bn_data)
