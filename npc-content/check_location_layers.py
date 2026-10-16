#!/usr/bin/env python3
"""Check shared-source selection, placement provenance and reproducibility."""
import hashlib
import json

from audit_location_layers import audit
from prepare_community_layers import ROOT, identities, reference_key
from select_location_dependencies import select


def main():
    select(ROOT)
    first = hashlib.sha256((ROOT/'SOURCE_MANIFEST.json').read_bytes()).hexdigest()
    select(ROOT)
    assert first == hashlib.sha256((ROOT/'SOURCE_MANIFEST.json').read_bytes()).hexdigest()
    manifest = json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    path = 'dda/data/json/overmap/overmap_special/specials.json'
    source = json.loads((ROOT/path).read_text())
    chosen = manifest['files'][path]['selection']
    assert 0 < len(chosen) < len(source), 'Shared world catalog imported wholesale'
    data = audit(ROOT)
    names = {x['id'] for x in data['locations']}
    assert {'hub_01','New England Church Retreat','Occupied Chem Lab','Occupied Scrap Yard',
            'ws_survivor_bunker_place','Occupied Lumbermill','Militia Lodge'} <= names
    for row in data['locations']:
        assert row['dda_tiles'] > 0 and row['dda_z_levels']
        assert not row['runtime_validated']
    hub = next(x for x in data['locations'] if x['id']=='hub_01')
    assert min(hub['dda_z_levels']) < 0
    assert hub['bn_special_present']
    # Multi-OMT grids must expose every terrain, not disappear from the index.
    grid = {'type':'mapgen','om_terrain':[['a','b'],['c','d']]}
    assert identities(grid) == [('mapgen_terrain', x) for x in 'abcd']
    assert reference_key('mapgen_terrain','a_north',{('mapgen_terrain','a'):True}) == ('mapgen_terrain','a')
    assert reference_key('mapgen_terrain','absent_north',{}) == ('mapgen_terrain','absent_north')
    print('PASS: selective dependency closure, linked placements, real BN comparison and rotated/multi-OMT map indexing')


if __name__ == '__main__':
    main()
