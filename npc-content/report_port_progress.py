#!/usr/bin/env python3
"""Reproducible template coverage; never equate staged JSON with completed NPCs."""
import argparse
import json
from pathlib import Path
from export_bn_ids import read_cache
ROOT=Path(__file__).resolve().parent
VERIFIED={'NPC_lighthouse_girl','NPC_lighthouse_man','NPC_lighthouse_woman','NPC_survivor_lighthouse'}
CHECKPOINT={'head':'e52486f7a9b5108353ef3381ba55bf72938001ef','run':39166343756,
            'source_core_cases':67,'source_core_assertions':10627,'source_mod_cases':5,'source_mod_assertions':766,
            'installed_core_cases':67,'installed_core_assertions':10627,'installed_mod_cases':5,'installed_mod_assertions':766,
            'result':'success','artifact':'https://github.com/ProxysRE/CataclysmAI-BN/actions/runs/39166343756/artifacts/12152373477'}


def templates(root):
    result=set()
    for path in root.rglob('*.json'):
        try:data=json.loads(path.read_text())
        except (ValueError,UnicodeError):continue
        if not isinstance(data,list):continue
        for e in data:
            if isinstance(e,dict) and e.get('type')=='npc':
                ids=e['id'];result.update(ids if isinstance(ids,list) else [ids])
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
    selected=templates(ROOT/'layers/staging')|templates(ROOT/'lighthouse/staging')|templates(ROOT/'island_prison')|templates(ROOT/'staging/bn_dialogue')
    active=embedded()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    assert len(selected)==82 and sum(groups.values())==73
    assert VERIFIED <= active <= selected
    return {'scope':'Distinct NPC template IDs in already selected community packages, including generic guards; not all DDA characters or the full agreed future scope',
            'all_dda_denominator_known':False,'started_template_count':len(selected),'started_template_ids':sorted(selected),
            'bulk_staged_groups':groups,'other_selected_groups':{'lighthouse':4,'island_prison':3,'isolated_road':2},
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
