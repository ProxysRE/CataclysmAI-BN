#!/usr/bin/env python3
"""Validate concrete special-placement terrain IDs, including rotation rules."""
import json
from compare_location_catalog import read_sources, physical_refs
from quest_dependency_graph import ids


def check_placements(payload):
    definitions = {}
    files, _ = read_sources()
    entries = [e for path, text in files.items() if path.startswith('bn/')
               for e in json.loads(text) if e.get('type') == 'overmap_terrain']
    entries += [e for e in payload if e.get('type') == 'overmap_terrain']
    for entry in entries:
        for name in ids(entry):
            definitions[name] = entry

    def flags(name, trail=()):
        assert name not in trail, ('terrain inheritance cycle', trail, name)
        entry = definitions[name]
        inherited = flags(entry['copy-from'], trail + (name,)) if 'copy-from' in entry else set()
        result = set(entry.get('flags', inherited))
        result.update(entry.get('extend', {}).get('flags', []))
        result.difference_update(entry.get('delete', {}).get('flags', []))
        return result

    count = 0
    for entry in payload:
        if entry.get('type') not in ('overmap_special', 'city_building'):
            continue
        for reference in physical_refs(entry):
            count += 1
            if reference in definitions:
                assert 'NO_ROTATE' in flags(reference), ('bare rotatable placement', reference)
                continue
            base = next((reference[:-len(s)] for s in ('_north', '_east', '_south', '_west')
                         if reference.endswith(s)), None)
            assert base in definitions, ('missing placement terrain', reference)
            assert 'NO_ROTATE' not in flags(base), ('rotated NO_ROTATE placement', reference)
    return count


if __name__ == '__main__':
    from prepare_karting import prepare_data as karting
    from prepare_farm_supply import prepare_data as farm
    print('PASS:', check_placements(karting()) + check_placements(farm()),
          'concrete karting/farm placement terrain references and rotation rules')
