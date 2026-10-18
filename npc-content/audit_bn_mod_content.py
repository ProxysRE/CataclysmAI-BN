#!/usr/bin/env python3
"""Inventory bundled BN mods and reject unreviewed new-core ID collisions."""
import argparse
import base64
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from prepare_regional_locations import index_entries, BUILTIN_IDS
from export_bn_ids import PIN

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'dependency_catalog/BN_MOD_INDEX.json'
REVIEWS = ROOT / 'dependency_catalog/MOD_COLLISION_REVIEWS.json'


def declarations(entries):
    result = index_entries([e for e in entries if isinstance(e, dict)]) - BUILTIN_IDS
    for e in entries:
        if isinstance(e, dict) and e.get('type') == 'MONSTER_FACTION' and isinstance(e.get('name'), str):
            result.add(('MONSTER_FACTION', e['name']))
    return result


def read_cache(path=CACHE):
    m = json.loads(path.read_text())
    raw = gzip.decompress(base64.b64decode(''.join((path.parent / part).read_text() for part in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['sha256']
    data = json.loads(raw)
    assert data['bn_pin'] == m['bn_pin'] == PIN
    assert len(data['records']) == m['records']
    return data


def build(source):
    assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == PIN
    paths = sorted((source / 'data/mods').rglob('*.json'), key=lambda p: p.relative_to(source).as_posix())
    assert len(paths) > 900, 'The bundled mod tree is missing or incomplete'
    parsed, owners, fingerprint = {}, {}, hashlib.sha256()
    for path in paths:
        relative = path.relative_to(source).as_posix()
        text = path.read_text(encoding='utf-8-sig')
        fingerprint.update((relative + '\0' + hashlib.sha256(text.encode()).hexdigest() + '\n').encode())
        entries = json.loads(text)
        entries = entries if isinstance(entries, list) else [entries]
        parsed[path] = entries
        info = [e for e in entries if isinstance(e, dict) and e.get('type') == 'MOD_INFO']
        if info:
            owners[path.parent] = [{'id': e.get('id', e.get('ident')), 'dependencies': e.get('dependencies', []), 'obsolete': e.get('obsolete', False)} for e in info]
    records = {}
    for path, entries in parsed.items():
        parent = next((p for p in (path.parent, *path.parents) if p in owners), None)
        owner = owners.get(parent, [])
        for e in entries:
            if not isinstance(e, dict) or e.get('type') == 'MOD_INFO':
                continue
            label = e.get('name', '')
            if isinstance(label, dict):
                label = label.get('str', label.get('str_sp', ''))
            if not isinstance(label, str):
                label = ''
            for kind, name in declarations([e]):
                relative = path.relative_to(source).as_posix()
                records[kind, name, relative] = {'type': kind, 'id': name, 'path': relative,
                    'mods': [m['id'] for m in owner], 'name': label}
    return {'bn_pin': PIN, 'json_files': len(paths), 'fingerprint': fingerprint.hexdigest(),
            'mods': {p.relative_to(source).as_posix(): value for p, value in sorted(owners.items())},
            'records': [records[k] for k in sorted(records)]}


def added_core_declarations(patch):
    result = set()
    for section in patch.split('--- /dev/null\n+++ b/')[1:]:
        target, body = section.split('\n', 1)
        body = body.split('\n--- ', 1)[0]
        if not target.startswith('data/json/') or not target.endswith('.json'):
            continue
        text = ''.join(line[1:] for line in body.splitlines(keepends=True) if line.startswith('+'))
        entries = json.loads(text)
        result |= declarations(entries if isinstance(entries, list) else [entries])
    return result


def audit(data, patch):
    new = added_core_declarations(patch)
    overlaps = [r for r in data['records'] if (r['type'], r['id']) in new]
    reviews = json.loads(REVIEWS.read_text())
    assert reviews['bn_pin'] == PIN
    approved = {(r['type'], r['id'], r['path']) for r in reviews['reviews'] if r.get('reason')}
    unreviewed = [r for r in overlaps if (r['type'], r['id'], r['path']) not in approved]
    return {'bn_pin': PIN, 'new_core_declarations': len(new), 'mod_json_files': data['json_files'],
            'mod_records': len(data['records']), 'overlaps': overlaps, 'unreviewed': unreviewed,
            'scope': 'Exact typed IDs in all bundled mod JSON; names included for counterpart search. ID difference does not prove semantic uniqueness.'}


def emit_cache(data):
    raw = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()
    encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
    for n, off in enumerate(range(0, len(encoded), 12000)):
        print(f'BN_MOD_INDEX_{n:03d}:' + encoded[off:off + 12000])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn-source', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--search')
    a = p.parse_args()
    if a.bn_source:
        data = build(a.bn_source)
        if CACHE.exists():
            assert read_cache() == data, 'Pinned bundled-mod inventory drift'
        else:
            emit_cache(data)
    else:
        data = read_cache()
    if a.search:
        query = a.search.casefold()
        print(json.dumps([r for r in data['records'] if query in (r['id'] + ' ' + r['name'] + ' ' + r['path']).casefold()], ensure_ascii=True))
    else:
        report = audit(data, (ROOT / 'artisan_engine.patch').read_text())
        if a.report:
            a.report.write_text(json.dumps(report, indent=2) + '\n')
        print('BN_MOD_AUDIT:' + json.dumps(report, separators=(',', ':')))
        assert not report['unreviewed'], 'New core IDs overlap bundled mods; review/reuse required'
        print('PASS: all bundled mod definitions checked; no unreviewed new-core collisions')
