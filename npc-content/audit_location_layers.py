#!/usr/bin/env python3
"""Audit selected location placement, floors and BN layout differences."""
import json
from pathlib import Path

from prepare_community_layers import ROOT, identities, read_bundle, reference_key, selected_entries


def audit(root):
    files = read_bundle(root)
    manifest = json.loads((root/'SOURCE_MANIFEST.json').read_text())
    links = json.loads((root/'LOCATION_LINK_REPORT.json').read_text())
    requested = {x['id'] for x in links['placement_links']}
    specials = {'dda': {}, 'bn': {}}
    maps = {'dda': {}, 'bn': {}}
    for name, content in files.items():
        side = name.split('/')[0]
        entries = json.loads(content)
        chosen = selected_entries(name, entries, manifest) if side == 'dda' else enumerate(entries)
        for position, entry in chosen:
            if entry['type'] == 'overmap_special':
                specials[side][entry['id']] = entry
            for kind, identifier in identities(entry):
                if kind == 'mapgen_terrain':
                    maps[side].setdefault((kind, identifier), []).append([name, position])
    rows = []
    for identifier in sorted(requested):
        source = specials['dda'][identifier]
        baseline = specials['bn'].get(identifier)
        source_cells = {tuple(x['point']): x['overmap'] for x in source['overmaps'] if 'overmap' in x}
        if len({tuple(x['point']) for x in source['overmaps']}) != len(source['overmaps']):
            raise ValueError('Duplicate placement coordinates: ' + identifier)
        bn_cells = {tuple(x['point']): x['overmap'] for x in baseline['overmaps'] if 'overmap' in x} if baseline else {}
        missing = sorted({terrain for terrain in source_cells.values()
                          if reference_key('mapgen_terrain', terrain, maps['dda']) not in maps['dda']})
        floors = sorted({point[2] for point in source_cells})
        rows.append({'id': identifier, 'dda_tiles': len(source_cells), 'dda_z_levels': floors,
                     'dda_placement_constraints': [x for x in source['overmaps'] if 'overmap' not in x],
                     'bn_special_present': baseline is not None, 'bn_tiles': len(bn_cells),
                     'bn_z_levels': sorted({point[2] for point in bn_cells}),
                     'dda_only_coordinates': [list(x) for x in sorted(source_cells.keys()-bn_cells.keys())],
                     'bn_only_coordinates': [list(x) for x in sorted(bn_cells.keys()-source_cells.keys())],
                     'changed_terrain_coordinates': [list(x) for x in sorted(source_cells.keys() & bn_cells.keys())
                                                     if source_cells[x] != bn_cells[x]],
                     'terrain_without_selected_mapgen': missing,
                     'camp_metadata': [{'point': x['point'], 'camp': x['camp']} for x in source['overmaps'] if 'camp' in x],
                     'runtime_validated': False})
    result = {'locations': rows, 'scope': 'Exact static layout comparison against pinned BN specials; selected-map coverage is incomplete and does not prove terrain absent from BN',
              'release_ready': False}
    (root/'LOCATION_SUMMARY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(f'Audited {len(rows)} linked placements; all static coordinates unique')
    return result


if __name__ == '__main__':
    audit(ROOT)
