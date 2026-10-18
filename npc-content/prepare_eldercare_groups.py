#!/usr/bin/env python3
"""Compile this closed one-level DDA group graph into stock BN tables."""
import argparse
import copy
import json
import re
from pathlib import Path
from prepare_eldercare import ROOT, sources, declarations
from bn_counterparts import adapt_entry
from prepare_eldercare_fauna import adapt_references

PAYLOAD = 'data/mods/Civilians/dda_eldercare_groups.json'
NAMES = ('GROUP_CIVILIANS_STANDARD', 'GROUP_NURSING_HOME', 'GROUP_RETIREMENT_COMMUNITY')
# Optional-mod counterparts, deliberately separate from the core-only catalog.
ALIASES = {
    'mon_civilian_police_rifle': 'mon_civilian_police',
    'mon_civilian_zombiegunner': 'mon_civilian_survivor_pistol',
}


def adapt_people(entry):
    result = copy.deepcopy(entry)
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'monster' and isinstance(value, str):
                    node[key] = ALIASES.get(value, value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(result)
    return result


def originals():
    catalog = declarations(sources())
    return {name: catalog[('monstergroup', name)][1] for name in NAMES}


def hours(value):
    match = re.fullmatch(r'(\d+) days', value)
    assert match, value
    return int(match[1]) * 24


def leaf(entry, scale):
    assert set(entry) <= {'monster', 'weight', 'cost_multiplier', 'pack_size', 'starts', 'ends'}
    result = copy.deepcopy(entry)
    result['freq'] = result.pop('weight', 1) * scale
    result.setdefault('cost_multiplier', 1)
    for key in ('starts', 'ends'):
        if key in result:
            result[key] = hours(result[key])
    return result


def native_data():
    groups = originals()
    child = groups[NAMES[0]]
    denominator = sum(e.get('weight', 1) for e in child['monsters'])
    result = []
    for name, source in groups.items():
        assert set(source) <= {'id', 'type', '//', 'monsters'}
        nested = [e for e in source['monsters'] if 'group' in e]
        scale = denominator if nested else 1
        entries = []
        for entry in source['monsters']:
            if 'group' in entry:
                # DDA ignores the parent's cost and falls back to the ROOT
                # default when this subgroup produces no eligible leaf.
                # Multiple subgroup draws would require a different compiler.
                assert entry == {'group': NAMES[0], 'weight': 10, 'cost_multiplier': 0}
                entries += [leaf(e, entry['weight']) for e in child['monsters']]
            else:
                entries.append(leaf(entry, scale))
        direct = [e for e in source['monsters'] if 'monster' in e]
        default = max(direct, key=lambda e: e.get('weight', 1))['monster']
        table = {'type': 'monstergroup', 'name': name, 'default': default,
                 'freq_total': sum(e.get('weight', 1) for e in source['monsters']) * scale,
                 'monsters': entries}
        result.append(adapt_people(adapt_references(adapt_entry(table))))
    return result


def prepare(check=False):
    payload = native_data()
    from prepare_civilians import mod_sources
    from prepare_regional_locations import index_entries, BUILTIN_IDS
    from export_bn_ids import read_cache
    from audit_bn_mod_content import read_cache as mod_cache
    core = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    mod = index_entries([e for n, text in mod_sources().items() if n.endswith('.json')
                         for e in (json.loads(text) if isinstance(json.loads(text), list) else [])]) - BUILTIN_IDS
    # No new monsters, no shared evolution-table replacement.
    from prepare_eldercare import refs
    assert not {r for e in payload for r in refs(e)} - core - mod
    assert not (index_entries(payload) - BUILTIN_IDS) & (core | mod)
    assert not (index_entries(payload) - BUILTIN_IDS) & {(r['type'], r['id']) for r in mod_cache()['records']}
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    path = ROOT / 'native/dda_eldercare_groups.json'
    if check:
        assert path.read_text() == text, path
    else:
        path.write_text(text)
    print('PASS: three optional Civilians tables; stock BN schemas, weapons and AI; exact one-level weights')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    prepare(p.parse_args().check)
