#!/usr/bin/env python3
"""Check the reviewed patch boundary, not merely the map's JSON syntax."""
import copy

from merge_existing_locations import merge_chemist, prepare


def check():
    baseline, source, merged, support = prepare()
    assert len(merged) == len(baseline)
    restored = copy.deepcopy(merged)
    obj = next(e for e in restored if e.get('om_terrain') == ['chemical_lab_ocu'])['object']
    assert obj.pop('place_npcs') == source[0]['object']['place_npcs']
    assert obj['rows'][8][16] == 'c'
    row = obj['rows'][8]
    obj['rows'][8] = row[:16] + '@' + row[17:]
    obj['npcs'] = {'@': {'class': 'NPC_cabin_chemist'}}
    assert restored == baseline, 'Unreviewed BN content changed during merge'
    for mutate in ('duplicate', 'palette', 'position'):
        b, d, p = copy.deepcopy((baseline, source, support))
        if mutate == 'duplicate':
            b[0]['object']['place_npcs'] = [{'class': 'NPC_cabin_chemist', 'x': 16, 'y': 8}]
        elif mutate == 'palette':
            next(e for e in p['bn_cabin.json'] if e.get('id') == 'cabin_palette')['furniture']['c'] = 'f_counter'
        else:
            d[0]['object']['place_npcs'][0]['x'] = 17
        try:
            merge_chemist(b, d, p)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsafe change accepted: ' + mutate)
    print('PASS: BN variants preserved, exactly one chemist, drift and duplicate guards')


if __name__ == '__main__':
    check()
