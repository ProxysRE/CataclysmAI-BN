#!/usr/bin/env python3
"""Preserve the connected eldercare content graph; enable only closed BN support."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter
from export_bn_ids import read_cache
from prepare_regional_locations import build, references, index_entries, BUILTIN_IDS
from quest_dependency_graph import namespace, ids

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'eldercare'
PAYLOAD = 'data/json/dda_eldercare_support.json'
PINS = {'dda': 'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974',
        'bn': 'c621aaf42fa182473aad10feea2b55647704dcf1'}


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['pins'] == PINS
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / p).read_text() for p in manifest['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for name, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][name]
        if name.endswith('.json'):
            json.loads(text)
    return files


def declarations(files):
    result = {}
    for path, text in files.items():
        if not path.startswith('dda/') or not path.endswith('.json'):
            continue
        for entry in json.loads(text):
            for key in index_entries([entry]) - BUILTIN_IDS:
                assert key not in result, (key, path)
                result[key] = (path, entry)
    return result


def refs(entry):
    """Typed positions used by this slice, not full DDA schema validation."""
    kind = namespace(entry)
    result = set()
    if kind == 'mapgen':
        result.update(references(entry.get('object', {})))
    elif kind == 'item_group':
        result.update(references({'items': {'_': {'item': entry}}}))
    elif kind == 'monstergroup':
        if entry.get('default') not in (None, 'mon_null'):
            result.add(('MONSTER', entry['default']))
        for spawn in entry.get('monsters', []):
            for field, target in [('monster', 'MONSTER'), ('group', 'monstergroup')]:
                if field in spawn:
                    result.add((target, spawn[field]))
    elif kind == 'MONSTER':
        for field, target in [('copy-from', 'MONSTER'), ('looks_like', 'MONSTER'),
                              ('death_drops', 'item_group'), ('harvest', 'harvest'),
                              ('burn_into', 'MONSTER')]:
            if isinstance(entry.get(field), str):
                result.add((target, entry[field]))
        for field, target in [('into', 'MONSTER'), ('into_group', 'monstergroup')]:
            if isinstance(entry.get('upgrades'), dict) and field in entry['upgrades']:
                result.add((target, entry['upgrades'][field]))
        reproduction = entry.get('reproduction', {})
        baby = reproduction.get('baby_type', {})
        if 'baby_egg' in baby:
            result.add(('item', baby['baby_egg']))
    elif kind == 'talk_topic':
        def walk(node):
            if isinstance(node, list):
                for child in node:
                    walk(child)
            elif isinstance(node, dict):
                if isinstance(node.get('topic'), str) and node['topic'] not in ('TALK_DONE', 'TALK_NONE'):
                    result.add(('talk_topic', node['topic']))
                for child in node.values():
                    walk(child)
        walk(entry.get('responses', []))
    return result


def native_data():
    files = sources()
    fish = next(e for e in json.loads(files['dda/data/json/monstergroups/fish.json']) if e.get('id') == 'GROUP_STOCKED_POND')
    # Both engines select from a fixed total, falling back when conditions fail.
    # DDA infers the highest-weight concrete entry as default when omitted.
    group = {'type': 'monstergroup', 'name': fish['id'], 'is_animal': fish['is_animal'],
             'default': max(fish['monsters'], key=lambda m: m.get('weight', 1))['monster'],
             'freq_total': sum(m.get('weight', 1) for m in fish['monsters']), 'monsters': []}
    for original in fish['monsters']:
        assert set(original) <= {'monster', 'weight', 'cost_multiplier', 'pack_size', 'conditions'}
        spawn = copy.deepcopy(original)
        spawn['freq'] = spawn.pop('weight', 1)
        spawn.setdefault('cost_multiplier', 1)
        group['monsters'].append(spawn)
    spider = next(e for e in json.loads(files['dda/data/json/mapgen/map_extras/spider.json']) if e.get('nested_mapgen_id') == 'spider_webs')
    spider = copy.deepcopy(spider)
    spider['method'] = 'json'
    return [group, spider]


def support_refs(payload):
    found = {r for e in payload for r in refs(e)}
    for e in payload:
        if e['type'] == 'mapgen':
            for field in e['object'].get('place_fields', []):
                found.add(('field_type', field['field']))
    return found


def build_layer(adapted=False):
    files = sources()
    catalog = declarations(files)
    cache = read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')
    assert cache['bn_pin'] == PINS['bn']
    bn = set(map(tuple, cache['identifiers']))
    sites = build()
    maps = [e for name in ('nursing_home', 'retirement_community') for e in sites[name + '.json']]
    from bn_counterparts import adapt_entry, MAPPINGS
    used = set()
    if adapted:
        from prepare_terminal_archives import adapt_map
        maps = [adapt_map(adapt_entry(e, used)) for e in maps if e["type"] not in ("talk_topic", "effect_on_condition")]
    provided = index_entries(maps)
    roots = {ref for entry in maps for ref in refs(entry)} - bn - provided
    # The provenance layer keeps original medical evolution; the adapted
    # layer uses the stock BN medical zombie under the user's reuse policy.
    pending = list(sorted(roots))
    selected, reused, missing, seen = {}, set(), set(), set()
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        alternatives = [key, (key[0] + '_abstract', key[1])]
        if any(k in bn for k in alternatives):
            reused.add(key)
            continue
        if key in provided:
            continue
        provider = next((catalog[k] for k in alternatives if k in catalog), None)
        if provider is None:
            missing.add(key)
            continue
        path, entry = provider
        if adapted:
            entry = adapt_entry(entry, used)
        selected[key] = {'source': path, 'entry': entry}
        pending.extend(refs(entry))
    # Aliases for one multi-ID declaration must not create duplicate entries.
    unique = {}
    for value in selected.values():
        unique[json.dumps(value['entry'], sort_keys=True)] = value
    candidates = sorted(unique.values(), key=lambda v: (namespace(v['entry']), str(ids(v['entry']))))
    return {'pins': PINS, 'installed': False, 'source_candidates': candidates,
            'counterpart_mappings_applied': [{'type': kind, 'source': source, 'bn_target': target, 'reason': reason} for (kind, source), (target, reason) in sorted(MAPPINGS.items()) if source in used],
            'report': {'root_missing_identifiers': sorted(roots),
                       'selected_definitions': len(candidates),
                       'selected_by_type': dict(Counter(v['entry']['type'] for v in candidates)),
                       'bn_declared_references_needing_semantic_review': sorted(reused),
                       'unresolved_transitive_references': sorted(missing),
                       'scope': 'Typed map references, group leaves, monster inheritance/drops/upgrades/reproduction and dialogue links; not attacks, AI, all item schema or runtime compatibility.',
                       'blockers': [('Read-only terminal story graphs use the BN computer archive bridge; whole-site generation remains pending.' if adapted else 'Source computer eocs/open_dialogue are retained for provenance; adapted graphs use BN computer archives.'),
                                    'Unmatched recursive groups, living-civilian AI and mutation branches need adaptation; source medical variants may be superseded by stock BN counterparts.',
                                    'Preserve source timed entries and group probabilities; naive flattening can change density and civilian disappearance.',
                                    'Resolve remaining dependencies, compare BN counterparts, adapt schemas and run full location generation before installing either site.']}}


def prepare(check=False, bn_source=None, bn_data=None):
    files = sources()
    if bn_source:
        for path, text in files.items():
            if path.startswith('bn/'):
                assert (bn_source / path[3:]).read_text(encoding='utf-8') == text, path
    payload = native_data()
    bn = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    if bn_data:
        bn = set(BUILTIN_IDS)
        for path in (bn_data / 'data/json').rglob('*.json'):
            entries = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(entries, list):
                bn.update(index_entries(entries))
    new = index_entries(payload) - BUILTIN_IDS
    assert not new & bn, new & bn
    assert not support_refs(payload) - bn - new, support_refs(payload) - bn - new
    layer = build_layer()
    from bn_counterparts import adapt_entry, check as check_counterparts
    check_counterparts(bn_source)
    regional = build()
    from prepare_terminal_archives import adapt_map
    adapted = {'locations': {name: [adapt_map(adapt_entry(e)) for e in regional[name + '.json'] if e['type'] not in ('talk_topic', 'effect_on_condition')] for name in ('nursing_home', 'retirement_community')},
               'dependencies': build_layer(adapted=True)}
    outputs = {FOLDER / 'ADAPTED_LOCATIONS.json': adapted, ROOT / 'native/dda_eldercare_support.json': payload,
               FOLDER / 'SOURCE_CANDIDATES.json': layer}
    for path, data in outputs.items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if check:
            assert path.read_text() == text, path
        else:
            path.write_text(text)
    print('Eldercare:', layer['report']['selected_definitions'], 'source dependencies staged;',
          len(layer['report']['unresolved_transitive_references']), 'unresolved before counterpart reuse; adapted:',
          adapted['dependencies']['report']['selected_definitions'], 'definitions,', len(adapted['dependencies']['report']['unresolved_transitive_references']), 'unresolved; two native support definitions')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    p.add_argument('--bn-data', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source, a.bn_data)
