#!/usr/bin/env python3
"""Verify that bulk conversion loses no definitions, identities or blocked source."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

from prepare_community_layers import ROOT, identities, prepare


def main():
    report = prepare(ROOT)
    files = json.loads(gzip.decompress(base64.b64decode((ROOT/'SOURCE_BUNDLE.json.gz.base64').read_text())))
    blockers = {(x['file'], x['index']) for x in report['blocked']}
    total = 0
    for name, content in files.items():
        if not name.startswith('dda/'):
            continue
        original = json.loads(content)
        staged = json.loads((ROOT/'staging'/name.removeprefix('dda/')).read_text())
        assert len(staged) == len(original), name
        for index, (before, after) in enumerate(zip(original, staged)):
            assert before['type'] == after['type'], (name, index)
            assert identities(before) == identities(after), (name, index)
            if (name, index) in blockers:
                assert before == after, (name, index, 'Blocked definition was modified')
            if before['type'] == 'npc':
                assert before.get('name_unique') == after.get('name_unique'), (name, index)
                assert before.get('chat') == after.get('chat'), (name, index)
        total += len(original)
    assert total == report['totals']['definitions']
    assert set(report['groups']) == {'robofac','godco','campus','militia','bunker_shop',
                                   'cabin_chemist','lumbermill_employees','scrap_trader'}
    # The baseline Hub and Godco are real conflicts, not packages to overwrite.
    assert any(x['source'].startswith('dda/data/json/npcs/robofac/') for x in report['overlaps'])
    assert any(x['source'].startswith('dda/data/json/npcs/godco/') for x in report['overlaps'])
    first = hashlib.sha256((ROOT/'LAYER_REPORT.json').read_bytes()).hexdigest()
    prepare(ROOT)
    assert first == hashlib.sha256((ROOT/'LAYER_REPORT.json').read_bytes()).hexdigest()
    assert not report['runtime_validated'] and not report['release_ready']
    print(f'PASS: {total} definitions retained, {len(blockers)} blocked originals preserved, deterministic report and BN overlap detection')


if __name__ == '__main__':
    main()
