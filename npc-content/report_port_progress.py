#!/usr/bin/env python3
"""Reproducible template coverage; never equate staged JSON with completed NPCs."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
from export_bn_ids import read_cache
ROOT=Path(__file__).resolve().parent
VERIFIED={'NPC_lighthouse_girl','NPC_lighthouse_man','NPC_lighthouse_woman','NPC_survivor_lighthouse','MILITIA_MERCHANT','MILITIA_GUARD1'}
CHECKPOINT={'head':'a379269eee36b2545909d9418d18c95ee0af3052','run':39328860166,
            'source_core_cases':73,'source_core_assertions':11030,'source_mod_cases':10,'source_mod_assertions':2224,
            'installed_core_cases':73,'installed_core_assertions':11030,'installed_mod_cases':10,'installed_mod_assertions':2224,
            'result':'success','artifact':'https://github.com/ProxysRE/CataclysmAI-BN/actions/runs/39328860166/artifacts/12226743444'}


def npc_ids(entries):
    result=set()
    for entry in entries:
        if isinstance(entry,dict) and entry.get('type')=='npc':
            identifiers=entry['id']
            result.update(identifiers if isinstance(identifiers,list) else [identifiers])
    return result


def source_templates():
    """Read preserved inputs only, independent of generated staging directories."""
    result=set()
    root=ROOT/'layers'
    manifest=json.loads((root/'SOURCE_MANIFEST.json').read_text())
    raw=gzip.decompress(base64.b64decode((root/'SOURCE_BUNDLE.json.gz.base64').read_text()))
    assert hashlib.sha256(raw).hexdigest()==manifest['bundle_sha256']
    files=json.loads(raw)
    assert set(files)==set(manifest['files'])
    for name,content in files.items():
        data=content.encode()
        record=manifest['files'][name]
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==record['git_blob_sha'],name
        if not name.startswith('dda/'):
            continue  # BN files are comparison inputs, not selected DDA templates.
        selected=record.get('selection')
        result |= npc_ids(e for i,e in enumerate(json.loads(content)) if selected is None or i in selected)
    for package in ('lighthouse','island_prison'):
        root=ROOT/package
        manifest=json.loads((root/'SOURCE_MANIFEST.json').read_text())
        for name,digest in manifest['files'].items():
            data=(root/'upstream'/name).read_bytes()
            assert hashlib.sha256(data).hexdigest()==digest,name
            result |= npc_ids(json.loads(data))
    manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    raw=gzip.decompress(base64.b64decode((ROOT/'isolated_road_source.json.gz.base64').read_text()))
    assert hashlib.sha256(raw).hexdigest()==manifest['source_payload_sha256']
    for entries in json.loads(raw).values():
        result |= npc_ids(entries)
    # Count only the explicitly selected boss from its authenticated source,
    # not every other raider archived alongside it or a generated candidate.
    from prepare_container_yard_cargo import sources, definition
    result |= npc_ids([definition(sources(),'dda','hells_raiders_boss')])
    return result


def embedded():
    result=set()
    for section in (ROOT/'artisan_engine.patch').read_text().split('--- /dev/null\n+++ b/')[1:]:
        target,body=section.split('\n',1)
        if not target.startswith('data/json/') or not target.endswith('.json'):continue
        body=body.split('\n--- ',1)[0]
        data=json.loads(''.join(l[1:] for l in body.splitlines(True) if l.startswith('+')))
        for e in data:
            if e.get('type')=='npc':result.add(e['id'])
    return result


def report():
    summary=json.loads((ROOT/'layers/LAYER_SUMMARY.json').read_text())
    groups={name:v['definitions'].get('npc',0) for name,v in summary['groups'].items() if v['definitions'].get('npc',0)}
    selected=source_templates()
    active=embedded()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    assert len(selected)==83 and sum(groups.values())==73
    assert VERIFIED <= active <= selected
    return {'scope':'Distinct NPC template IDs in already selected community packages, including generic guards; not all DDA characters or the full agreed future scope',
            'all_dda_denominator_known':False,'started_template_count':len(selected),'started_template_ids':sorted(selected),
            'bulk_staged_groups':groups,'other_selected_groups':{'lighthouse':4,'island_prison':3,'isolated_road':2,'container_yard_raider_leader':1},
            'already_declared_in_bn_core':sorted(n for n in selected if ('npc',n) in core),
            'native_embedded_ids':sorted(active),'native_embedded_count':len(active),'native_embedded_template_coverage_percent':round(100*len(active)/len(selected),1),
            'verified_template_ids':sorted(VERIFIED),'verified_template_load_count':len(VERIFIED),'verified_template_load_coverage_percent':round(100*len(VERIFIED)/len(selected),1),
            'embedded_awaiting_native_verification':sorted(active-VERIFIED),'verified_checkpoint':CHECKPOINT,
            'full_quest_chain_completion':'Not established by template loading or shared-engine tests; manual/full lifecycle validation is still required',
            'excluded_from_npc_counts':'Six existing Civilians monster types with dialogue; source archives; dialogue topics; npc_class definitions; multiple guard spawns of one template',
            'location_scope':'51 accepted missing/partial location groups. Do not divide map files, OMT cells or roof variants by that denominator.'}


def prepare(check=False):
    data=report();text=json.dumps(data,indent=2)+'\n';path=ROOT/'PORT_PROGRESS.json'
    if check:assert path.read_text()==text,path
    else:path.write_text(text)
    print(f"NPC template coverage: {data['verified_template_load_count']}/{data['started_template_count']} ({data['verified_template_load_coverage_percent']}%) native-load verified; {data['native_embedded_count']} embedded, including pending additions. Full-DDA percentage unknown.")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
