#!/usr/bin/env python3
"""Explicit BN counterparts authorized by the user's approximate-port policy."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from export_bn_ids import read_cache

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'counterparts'
# Namespace is retained here. Group-to-item and furniture-to-terrain changes
# need schema-aware conversion in the owning adapter, not string replacement.
MAPPINGS = {
    ('MONSTER', 'mon_zombie_medical'): ('mon_zombie_nurse', 'Reuse the existing BN medical zombie and its own attacks, loot and evolution.'),
    ('furniture', 'f_ergometer_mechanical'): ('f_ergometer', 'Existing BN rowing exercise machine and training interaction.'),
    ('furniture', 'f_treadmill_mechanical'): ('f_treadmill', 'Existing BN treadmill; training retains BN power requirements.'),
    ('furniture', 'f_foot_locker_aluminum'): ('f_foot_locker', 'Existing metal foot locker; use BN material and dismantling yields.'),
    ('item', 'buttonshirt'): ('dress_shirt', 'Existing BN button-down shirt.'),
    ('item', 'denim_shirt'): ('longshirt', 'Existing long-sleeved everyday shirt; fabric and armor use BN values.'),
    ('item', 'jeans_skinny'): ('jeans', 'Existing jeans; no separate fit variant needed.'),
    ('item_group', 'SUS_fridge_bachelor'): ('SUS_fridge', 'Existing household refrigerator loot.'),
    ('item_group', 'SUS_office_mess'): ('office_mess', 'Existing office clutter and supplies.'),
    ('item_group', 'SUS_trash_floor'): ('trash_cart', 'Existing BN mixed refuse, also used by the farm adapter.'),
    ('item_group', 'SUS_trash_trashcan'): ('trash_cart', 'Existing BN mixed refuse; exact trash distribution may differ.'),
    ('item_group', 'tools_common_small'): ('tools_common', 'Existing common household tools; BN size mix retained.'),
    ('item_group', 'tools_workshop'): ('tools_mechanic', 'Existing workshop and mechanic tools.'),
    ('item_group', 'misc_smoking_legal'): ('misc_smoking', 'Existing smoking supplies; retain the BN tobacco/cannabis distribution.'),
    ('terrain', 't_soil'): ('t_dirt', 'Existing bare soil terrain.'),
}


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['bn_pin'] == 'c621aaf42fa182473aad10feea2b55647704dcf1'
    raw = gzip.decompress(base64.b64decode(''.join((FOLDER / p).read_text() for p in manifest['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][path]
        json.loads(text)
    return files


def adapt_entry(entry, used=None):
    # All selected IDs are unique across these namespaces. Only exact scalar
    # references change; human text and top-level declaration identities stay.
    aliases = {source: target for (_, source), (target, _) in MAPPINGS.items()}
    assert len(aliases) == len(MAPPINGS)
    used = used if used is not None else set()
    def walk(value, top=False):
        if isinstance(value, str):
            if value in aliases:
                used.add(value)
            return aliases.get(value, value)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: v if k in ('name', 'description', 'text', 'dynamic_line') or k.startswith('//') or
                    (top and k in ('id', 'abstract')) else walk(v) for k, v in value.items()}
        return value
    return walk(entry, top=True)


def check(bn_source=None):
    files = sources()
    index = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    for (kind, original), (target, reason) in MAPPINGS.items():
        assert (kind, target) in index, (kind, original, target)
        assert reason
    if bn_source:
        for path, text in files.items():
            assert (bn_source / path[3:]).read_text(encoding='utf-8') == text, path
    print('PASS: 15 explicit counterpart mappings; stock BN target identifiers and archived source checksums')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn-source', type=Path)
    check(p.parse_args().bn_source)
