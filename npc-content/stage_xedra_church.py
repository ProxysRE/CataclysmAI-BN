#!/usr/bin/env python3
"""Preserve the complete XEDRA church and traverse available equipment sources."""
import collections
import json
from prepare_rural_churches import FOLDER, MAPS, SPECIALS, sources
from compare_location_catalog import read_sources
from quest_dependency_graph import ITEM_TYPES, ids, references
from prepare_xedra_gear import sources as gear_sources


def stage():
    files = sources()
    files.update(gear_sources())
    catalog, _ = read_sources()
    index = {}
    support_index = {}
    support_selected = {}
    for path, text in files.items():
        if not path.startswith('dda/'):
            continue
        for e in json.loads(text):
            if e.get('type') == 'ammunition_type':
                support_index[e['id']] = (path, e)
            if e.get('type') in ITEM_TYPES:
                for name in ids(e):
                    index[name] = (path, e)
    group = next(e for e in json.loads(files['dda/NC_XEDRA_FIELD_AGENT_1.json']) if e.get('id') == 'NC_XEDRA_FIELD_AGENT_worn')
    roots = set()
    for e in group['entries']:
        roots.add(e['item'])
        roots.update(e.get('contents-item', []))
    queue = collections.deque(sorted(roots))
    seen, selected, edges, unresolved = set(), [], [], set()
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        if name not in index:
            unresolved.add(('item', name))
            continue
        path, e = index[name]
        selected.append({'id': name, 'source': path, 'definition': e})
        refs = list(references(e))
        for action in e.get('use_action', []) if isinstance(e.get('use_action'), list) else []:
            if isinstance(action, str):
                refs.append(('native_use_action', action, 'use_action'))
        refs.extend(('ammunition_type', ammo, 'tool_ammo') for ammo in e.get('tool_ammo', []))
        for action in e.get('tick_action', []):
            if isinstance(action, str):
                refs.append(('native_use_action', action, 'tick_action'))
        for p in e.get('pocket_data', []):
            if 'default_magazine' in p:
                refs.append(('item', p['default_magazine'], 'pocket_data.default_magazine'))
        def transforms(value):
            if isinstance(value, dict):
                if value.get('type') == 'transform' and isinstance(value.get('target'), str):
                    yield value['target']
                for child in value.values():
                    yield from transforms(child)
            elif isinstance(value, list):
                for child in value:
                    yield from transforms(child)
        refs.extend(('item', target, 'use_action.transform.target') for target in transforms(e.get('use_action', {})))
        for kind, target, field in refs:
            edges.append({'from': name, 'kind': kind, 'to': target, 'field': field})
            if kind == 'item':
                queue.append(target)
            elif kind == 'ammunition_type' and target in support_index:
                provider_path, definition = support_index[target]
                support_selected[target] = {'id': target, 'source': provider_path, 'definition': definition}
                if isinstance(definition.get('default'), str):
                    queue.append(definition['default'])
            else:
                unresolved.add((kind, target))
    maps = json.loads(catalog['dda/' + MAPS + 'xedra_church_rural.json'])
    special = next(e for e in json.loads(catalog['dda/' + SPECIALS]) if e.get('id') == 'xedra_church_rural')
    monster = next(e for e in json.loads(files['dda/nether.json']) if e.get('id') == 'mon_twisting_mass')
    emit = next(e for e in json.loads(files['dda/emit.json']) if e.get('id') == 'emit_twisting_mass_dust')
    field = next(e for e in json.loads(files['dda/field_type.json']) if e.get('id') == 'fd_twisting_mass_dust')
    source_tent = next(e for e in json.loads(files['dda/rural_outdoors_nested.json']) if e.get('nested_mapgen_id') == 'tent_b_5x5_S')
    bn_tent = next(e for e in json.loads(files['bn/campsite.json']) if e.get('nested_mapgen_id') == 'tent_b_5x5_S')
    report = {'status': 'staged_not_installed', 'source_mapgen_blocks': len(maps),
        'native_dependency_progress': 'Creature, particles and inert string prepared in xedra_creature; runtime pending; activity suit states prepared in xedra_gear; powered respirator and S02a suit still staged',
        'source_placement_cells': len(special['overmaps']), 'z_levels': [-1, 0, 1, 2],
        'npc_or_quest_definitions_in_these_location_sources': 0,
        'equipment_nodes_preserved': len(selected), 'equipment_edges': len(edges),
        'equipment_definitions': selected, 'equipment_reference_edges': edges,
        'ammunition_type_definitions': list(support_selected.values()),
        'unresolved_typed_references': [{'kind': k, 'id': n} for k,n in sorted(unresolved)],
        'scope_limit': 'Available-source item inheritance, transform targets, magazine defaults, tool ammunition, tick actions and typed quest-item references; not complete field, armor, enchantment or EOC closure',
        'blocking_mechanics': ['runtime validation and review of BN grab lifecycle/AI adaptation',
            'runtime validation of source dust field/emitter',
            'multi-subtype powered protective armor, material/bodypart protection and immunity flags',
            'worn item group contents and batteries', 'source tent erase-before-placement flag and BN tent geometry review'],
        'source_tent_equals_BN': source_tent == bn_tent,
        'source_monster': monster, 'source_emit': emit, 'source_field': field,
        'BN_pull_review': 'BN_RANGED_PULL_REVIEW.json',
        'source_special_policy_preserved': {'occurrences': special['occurrences'], 'flags': special['flags']},
        'placement_policy_review': 'Source XEDRA special requests 20..100 occurrences with GLOBALLY_UNIQUE; must review BN support before enabling',
        'no_substitution': 'No generic monster, inert armor or empty field-agent corpse is installed'}
    for name, value in [('XEDRA_SOURCE_MAPS.json', maps), ('XEDRA_SOURCE_SPECIAL.json', special),
                        ('XEDRA_FIELD_AGENT_GROUP.json', group), ('XEDRA_DEPENDENCY_REVIEW.json', report)]:
        (FOLDER / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report


if __name__ == '__main__':
    report = stage()
    print(f"Staged full XEDRA church and {report['equipment_nodes_preserved']} equipment definitions; native blockers retained")
