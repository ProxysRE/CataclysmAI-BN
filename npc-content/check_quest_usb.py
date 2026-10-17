#!/usr/bin/env python3
"""Verify source conversion and whole-catalog duplicate/inheritance guards."""
import copy
import json
from pathlib import Path
import tempfile

from prepare_quest_usb import ROOT, check_baseline, check_generated


def check():
    check_generated()
    graph = json.loads((ROOT / 'quest_dependencies/QUEST_ITEM_GRAPH.json').read_text())
    original = next(n['definition'] for n in graph['nodes'] if n['namespace'] == 'item' and n['id'] == 'usb_drive')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        folder = root / 'data/json/items/deep'
        folder.mkdir(parents=True)
        parent = folder / 'unrelated_filename.json'
        parent.write_text(json.dumps([original]))
        check_baseline(root)
        collision = folder / 'elsewhere.json'
        collision.write_text(json.dumps([{'type': 'TOOL', 'id': 'usb_drive_nano'}]))
        try:
            check_baseline(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Duplicate ID in a different file was accepted')
        collision.unlink()
        changed = copy.deepcopy(original)
        changed['weight'] = '200 g'
        parent.write_text(json.dumps([changed]))
        try:
            check_baseline(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed BN parent was accepted without review')
    print('PASS: whole-catalog USB ID and baseline-parent drift guards')


if __name__ == '__main__':
    check()
