#!/usr/bin/env python3
"""Check real-source location merges, unchanged BN behavior and drift guards."""
import argparse
import copy
import json
from pathlib import Path

from prepare_location_expansion import ROOT, NUCLEAR, cells, nuclear_merge, nuclear_patch, prepare, sources


def check(bn_source=None):
    files = sources()
    if bn_source:
        for name, text in files.items():
            if name.startswith('bn/'):
                path = bn_source / name[3:]
                if path.read_text(encoding='utf-8') != text:
                    raise ValueError('BN location source drift: ' + name)
    baseline = json.loads(files['bn/' + NUCLEAR])
    incoming = json.loads(files['dda/' + NUCLEAR])
    result, water, _ = nuclear_merge(baseline, incoming)
    assert len(water) == 24 and len(result[0]['overmaps']) == 708
    original_cells = cells(baseline[0])
    merged_cells = cells(result[0])
    assert all(merged_cells[k] == v for k, v in original_cells.items())
    assert {k: v for k, v in result[0].items() if k != 'overmaps'} == {
        k: v for k, v in baseline[0].items() if k != 'overmaps'}
    river = json.loads(files['bn/data/json/overmap/overmap_terrain/overmap_terrain_river.json'])
    # BN expands the rotating 'river' terrain into the four cardinal IDs.
    rotating = next(e for e in river if e.get('id') == 'river')
    assert 'NO_ROTATE' in rotating['delete']['flags']
    assert {c['overmap'] for c in water} <= {'river_north', 'river_east', 'river_south', 'river_west'}
    for mutation in ('duplicate', 'shoreline_drift'):
        altered = copy.deepcopy(incoming)
        if mutation == 'duplicate':
            altered[0]['overmaps'].append(copy.deepcopy(altered[0]['overmaps'][0]))
        else:
            next(c for c in altered[0]['overmaps'] if c['point'] == [2, 8, 0])['overmap'] = 'river_center'
        try:
            nuclear_merge(baseline, altered)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid source accepted: ' + mutation)
    patch, output, _ = nuclear_patch()
    assert json.loads(output) == result
    assert patch.count('+++ b/' + NUCLEAR) == 1
    report = prepare()
    hub = report['hub']
    candidate, = json.loads((ROOT / 'hub_candidate/hub_01_special.json').read_text())
    assert len(cells(candidate)) == 102
    assert hub['installable'] is False and hub['native_patch'] is False
    assert len(hub['changes']['added']) == 33 and len(hub['changes']['changed']) == 2
    assert not hub['changes']['baseline_only']
    assert len(hub['new_z_minus_1']) == 8
    assert {k: v for k, v in candidate.items() if k != 'overmaps'} == hub['retained_policy']
    print('PASS: 24 shoreline cells, all 684 BN cells and placement rules retained; 102-cell Hub candidate gated; drift/duplicate guards')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bn-source', type=Path)
    check(parser.parse_args().bn_source)
