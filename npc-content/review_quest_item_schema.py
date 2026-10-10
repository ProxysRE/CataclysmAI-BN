#!/usr/bin/env python3
"""List schema migration obligations without dropping original item fields."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent / 'quest_dependencies'
graph = json.loads((root / 'QUEST_ITEM_GRAPH.json').read_text())
items = {node['id']: node for node in graph['nodes'] if node['namespace'] == 'item'}


def category(identifier, seen=()):
    if identifier in seen:
        raise ValueError('Inheritance cycle')
    entry = items[identifier]['definition']
    types = entry.get('subtypes', [])
    if len(types) > 1:
        return 'MULTI_SUBTYPE_REQUIRES_NATIVE_SUPPORT'
    if types:
        return types[0]
    if entry.get('type') != 'ITEM':
        return entry['type']
    if entry.get('copy-from'):
        return category(entry['copy-from'], seen + (identifier,))
    return 'GENERIC'


checks = {
    'variants': 'native item variant representation; do not discard names/descriptions',
    'pocket_data': 'translate magazine capacity and allowed magazines; audit other pocket semantics',
    'relative': 'compare relative damage/armor-penetration arithmetic against BN loader',
    'barrel_length': 'barrel length versus BN barrel volume and ranged calculations',
    'longest_side': 'dimension support in pinned BN item loader',
    'gunmod': 'nested gunmod schema',
}
review = []
for identifier, node in sorted(items.items()):
    entry = node['definition']
    review.append({'id': identifier, 'source': node['source'], 'target_type': category(identifier),
                   'checks': [message for field, message in checks.items() if field in entry],
                   'source_definition_sha256': hashlib.sha256(json.dumps(entry, sort_keys=True,
                       ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
                   'runtime_validated': False})
(root / 'ITEM_SCHEMA_REVIEW.json').write_text(json.dumps({'items': review, 'release_ready': False},
    ensure_ascii=False, indent=2) + '\n')
print(f'Reviewed inheritance and migration obligations for {len(review)} items')
