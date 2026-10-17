#!/usr/bin/env python3
"""Check casing source conversion and real-parent/duplicate guard behavior."""
import copy
import json
from pathlib import Path
import tempfile

from prepare_quest_ammo import check_baseline, check_generated
from prepare_quest_usb import verified_graph


def check():
    check_generated()
    graph = verified_graph()
    parents = [n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] in {'casing', '9mm_casing'}]
    assert len(parents) == 2
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / 'data/json/items/renamed/parents.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(parents))
        check_baseline(root)
        conflict = path.parent / 'other.json'
        conflict.write_text(json.dumps([{'type': 'GENERIC', 'id': '545_casing'}]))
        try:
            check_baseline(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Existing casing ID was accepted')
        conflict.unlink()
        changed = copy.deepcopy(parents)
        next(e for e in changed if e.get('abstract') == 'casing')['material'] = 'steel'
        path.write_text(json.dumps(changed))
        try:
            check_baseline(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed casing material was accepted')
    print('PASS: 5.45 casing source fidelity, ID conflicts and BN inheritance guards')


if __name__ == '__main__':
    check()
