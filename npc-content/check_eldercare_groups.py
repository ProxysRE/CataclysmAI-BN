#!/usr/bin/env python3
"""Compare exact outcome laws, including empty subgroups and budget costs."""
from collections import defaultdict
from fractions import Fraction as F
from prepare_eldercare_groups import originals, native_data, prepare, ALIASES
from bn_counterparts import MAPPINGS

aliases = dict(ALIASES)
aliases.update({a: b for (_, a), (b, _) in MAPPINGS.items()})
groups = originals()

def alive(entry, hour, source):
    def time(key):
        value = entry.get(key, 0)
        return int(value.split()[0]) * 24 if source and value else value
    return hour > time('starts') and (not time('ends') or hour < time('ends'))

def outcomes(entry):
    lo, hi = entry.get('pack_size', [1, 1])
    name = aliases.get(entry['monster'], entry['monster'])
    return {(name, n, max(1, entry.get('cost_multiplier', 1) * n)): F(1, hi-lo+1)
            for n in range(lo, hi+1)}

def upstream(name, hour, recursive=False):
    source = groups[name]
    total = sum(e.get('weight', 1) for e in source['monsters'])
    result = defaultdict(F)
    consumed = 0
    for entry in source['monsters']:
        if not alive(entry, hour, True):
            continue
        weight = entry.get('weight', 1)
        consumed += weight
        children = upstream(entry['group'], hour, True) if 'group' in entry else outcomes(entry)
        for outcome, probability in children.items():
            result[outcome] += F(weight, total) * probability
    result[None] += F(total-consumed, total)
    if not recursive:
        default = max((e for e in source['monsters'] if 'monster' in e), key=lambda e: e.get('weight', 1))['monster']
        result[(aliases.get(default, default), 1, 1)] += result.pop(None)
    return {k: v for k, v in result.items() if v}

def compiled(table, hour):
    result = defaultdict(F)
    total = table['freq_total']
    # Enumerate every possible BN integer RNG roll; separate from recursive law.
    for roll in range(1, total+1):
        chosen = None
        for entry in table['monsters']:
            if not alive(entry, hour, False):
                continue
            if roll <= entry['freq']:
                chosen = entry
                break
            roll -= entry['freq']
        law = outcomes(chosen) if chosen else {(table['default'], 1, 1): F(1)}
        for outcome, probability in law.items():
            result[outcome] += probability / total
    return dict(result)

prepare(check=True)
# Test each boundary exactly and one hour on either side, plus late and negative time.
hours = sorted({-1, 0, 1, 9999} | {d*24+offset for d in (8,12,16,24) for offset in (-1,0,1)})
for table in native_data():
    for hour in hours:
        actual = compiled(table, hour)
        expected = upstream(table['name'], hour)
        assert actual == expected, (table['name'], hour, actual, expected)
        assert sum(actual.values()) == 1
print('PASS: 48 exact distributions: identities, pack sizes, budget costs, time boundaries and root fallback after empty subgroup')
