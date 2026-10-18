#!/usr/bin/env python3
"""Promote the identical BN Exotic Ammo casing to one shared core definition."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
from export_bn_ids import PIN

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'shared_casing'
TARGET = 'data/mods/exotic_ammo/generic/casing.json'
CORE = 'data/json/items/dda_545_casing.json'


def source():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert m['bn_pin'] == PIN and m['path'] == TARGET
    raw = (FOLDER / 'bn_exotic_casings.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m['sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == m['blob_sha']
    return raw.decode()


def payload():
    original = json.loads(source())
    core = json.loads((ROOT / 'native/dda_545_casing.json').read_text())
    entry, = [e for e in original if e['id'] == '545_casing']
    assert core == [entry], 'Shared definition must remain exactly the existing BN item'
    return [e for e in original if e['id'] != '545_casing']


def patch_sections():
    after = json.dumps(payload(), ensure_ascii=True, indent=2) + '\n'
    return ''.join(difflib.unified_diff(source().splitlines(keepends=True), after.splitlines(keepends=True), 'a/' + TARGET, 'b/' + TARGET))


def validate_resolution(patch):
    assert patch_sections() in patch, 'Original optional-mod duplicate was not removed'
    marker = '--- /dev/null\n+++ b/' + CORE + '\n'
    assert patch.count(marker) == 1
    body = patch.split(marker, 1)[1].split('\n--- ', 1)[0]
    embedded = ''.join(line[1:] for line in body.splitlines(keepends=True) if line.startswith('+'))
    assert json.loads(embedded) == json.loads((ROOT / 'native/dda_545_casing.json').read_text())
    payload()


def prepare(check=False, bn_source=None):
    if bn_source:
        assert (bn_source / TARGET).read_text(encoding='utf-8') == source()
    text = json.dumps(payload(), ensure_ascii=True, indent=2) + '\n'
    p = ROOT / 'native/dda_exotic_casings.json'
    if check:
        assert p.read_text() == text
    else:
        p.write_text(text)
    print('PASS: existing BN 545 casing is shared unchanged; only its duplicate mod declaration is removed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source)
