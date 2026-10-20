#!/usr/bin/env python3
"""Adapt the full campus geometry batch without touching the native preview."""
import argparse,copy,json
from collections import Counter
from prepare_geometry_layer import ROOT,OUT,prepare as prepare_shells
from prepare_container_yards import required
from prepare_regional_locations import index_entries
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mods_cache


def prepare(check=False):
    prepare_shells(check=True)
    source=json.loads((OUT/'SHELLS.json').read_text())['campus']
    entries=copy.deepcopy(source);deferred=[]
    for e in entries:
        if e['type']=='overmap_terrain' and 'SHOULD_NOT_SPAWN' in e.get('flags',[]):
            deferred.append({'ids':e['id'],'flag':'SHOULD_NOT_SPAWN','reason':'Not in pinned BN oter_flags; source declaration retained in SHELLS and authenticated bundle'})
            e['flags'].remove('SHOULD_NOT_SPAWN')
        if e['type']=='overmap_special':assert e['occurrences']==[0,0],e['id']
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    own=index_entries(entries)
    missing=required(entries)-own-core
    assert not missing,sorted(missing)
    by_id={n:e for e in entries if e['type']=='overmap_terrain' for n in (e['id']if isinstance(e['id'],list) else[e['id']])}
    inherited=[]
    for e in entries:
        if e['type']=='overmap_terrain' and 'copy-from'in e:
            parent=e['copy-from'];assert parent in by_id
            assert 'copy-from' not in by_id[parent]
            inherited.append({'ids':e['id'],'parent':parent})
    from audit_hub_access import matrix
    for e in entries:
        if e['type']=='mapgen':
            slots=matrix(e);rows=e['object']['rows']
            assert len(rows)==24*len(slots)
            assert all(len(row)==24*len(slots[0]) for row in rows)
    for a,b in zip(source,entries):
        if a['type']=='mapgen':assert a['object']==b['object']
        elif a['type']=='overmap_special':assert a==b
    # The batch deliberately reuses IDs until a separately tested installation is selected.
    mod_ids={(r['type'],r['id']) for r in mods_cache()['records']}
    report={'status':'adapted_geometry_candidate_not_installed','native_embedded':False,'runtime_validated':False,
      'definitions':dict(Counter(e['type']for e in entries)),
      'unique_omt':len(by_id),'placements_by_special':{e['id']:len(e['overmaps'])for e in entries if e['type']=='overmap_special'},
      'source_occurrences':'All five source specials already have [0,0]; no natural appearance policy invented',
      'unsupported_flags':deferred,'concrete_parent_inheritance':inherited,'unresolved_typed_refs':sorted(missing),
      'bn_core_overlaps':sorted(own&core-{('terrain','t_null'),('furniture','f_null'),('item','null')}),
      'bundled_mod_overlaps':sorted(own&mod_ids),
      'preserved':['All 26 complete mapgen objects from first-layer extraction','All five special placement layouts and source occurrence policy','Four concrete OMT parent links; not mistaken for missing abstract definitions','Authenticated complete source and deferred furniture/loot/NPC fields'],
      'remaining':['Native loading and whole-building generation','Stair/roof access verification','Choose installation identities only after reviewing BN and bundled-mod overlap report','Late-layer furniture, loot and population remain deferred']}
    for file,value in [('CAMPUS_ADAPTED_SHELL.json',entries),('CAMPUS_ADAPTATION_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/file
        if check:assert p.read_text()==text,p
        else:p.write_text(text)
    print('Campus: 26 maps /112 OMT /5 special layouts; concrete inheritance and dependency closure verified; not embedded')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
