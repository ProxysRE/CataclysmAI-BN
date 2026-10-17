#!/usr/bin/env python3
"""Preserve a pinned whole-core typed ID index for systematic BN reuse."""
import argparse
import base64
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from prepare_regional_locations import index_entries

PIN = 'c621aaf42fa182473aad10feea2b55647704dcf1'


def read_cache(path):
    manifest = json.loads(path.read_text())
    encoded = ''.join((path.parent / name).read_text() for name in manifest['parts'])
    raw = gzip.decompress(base64.b64decode(encoded, validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['cache_sha256'], 'BN ID cache checksum mismatch'
    value = json.loads(raw)
    assert value['bn_pin'] == manifest['bn_pin'] == PIN
    assert value['input_fingerprint'] == manifest['input_fingerprint']
    assert len(value['identifiers']) == manifest['identifiers_count']
    return value


def build(root):
    assert subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == PIN, 'Wrong BN revision'
    paths = sorted((root / 'data/json').rglob('*.json'))
    assert len(paths) > 100
    identifiers, fingerprint = set(), hashlib.sha256()
    for path in paths:
        text = path.read_text(encoding='utf-8')
        relative = path.relative_to(root).as_posix()
        fingerprint.update((relative + '\0' + hashlib.sha256(text.encode()).hexdigest() + '\n').encode())
        data = json.loads(text)
        identifiers.update(index_entries(data if isinstance(data, list) else [data]))
    return {'bn_pin': PIN, 'scope': 'Core JSON declarations and generated vehicle-part shapes; ID presence is not semantic/runtime parity',
            'json_files': len(paths), 'input_fingerprint': fingerprint.hexdigest(),
            'identifiers': [list(row) for row in sorted(identifiers)]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn-source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--cache', required=True, type=Path)
    a = p.parse_args()
    value = build(a.bn_source)
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()
    a.output.write_bytes(raw)
    if a.cache.exists():
        assert read_cache(a.cache) == value, 'Pinned BN identifier cache drift'
    else:
        # One-time bootstrap of public source metadata through text-only API;
        # once committed, subsequent jobs validate it and emit no encoded data.
        encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
        for n, offset in enumerate(range(0, len(encoded), 60000)):
            print(f'BN_TYPED_IDS_{n:03d}:' + encoded[offset:offset + 60000])
    print('BN typed ID cache:', len(value['identifiers']), 'identities from', value['json_files'], 'JSON files')
