#!/usr/bin/env python3
"""Count accepted location groups by demonstrated geometry-generation scope."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Match source identities, never positional catalog indices (which can shift).
VERIFIED={
 'overmap_special:campus':('native/dda_geometry_preview.json','All five campus layout cases passed source and installed generation'),
 'overmap_special:Militia Lodge':('native/dda_grey_moose_lodge.json','Complete lodge floors and roof'),
 'overmap_special:Island prison':('native/dda_geometry_preview.json','Namespaced shell preview; all special cells'),
 'overmap_special:church_rural':('native/dda_rural_church.json','Ordinary church plus XEDRA shell preview'),
 'overmap_special:nursing_home':('native/dda_eldercare_locations.json','Both nursing-home variants; optional Civilians data'),
 'overmap_special:retirement_community':('native/dda_eldercare_locations.json','Complete retirement community; optional Civilians data'),
 'overmap_special:Farm Supply Store':('native/dda_farm_supply.json','Normal and looted store geometry'),
 'overmap_special:lighthouse_island_small':('native/dda_small_lighthouse.json','All six levels'),
 'overmap_special:o_karting_l':('native/dda_karting_circuit.json','Track, ramps, stairs and roof'),
 'overmap_special:hub_01':('native/dda_geometry_preview.json','Namespaced Hub shell; all 100 placed cells and navigation terrain'),
 'city_building:station_radio':('native/dda_radio_station_towers.json','Approved tower-floor extension; stock BN buildings retained'),
}


def prepare(check=False):
    catalog=json.loads((ROOT/'location_catalog/REVIEWED_GROUPS.json').read_text())
    groups=[g for g in catalog if g['status'] in ('absent_specific_location_or_variant','expanded_or_older_version')]
    assert len(groups)==51
    validation=json.loads((ROOT/'lighthouse/VALIDATION.json').read_text())
    checkpoint=validation['checkpoint']
    assert checkpoint['status']=='success' and checkpoint['geometry_test_cases']>=3
    assert 'hub_01'in validation['geometry_preview']['packages']
    rows=[];seen=set()
    for g in groups:
        found=set(g['source_identities'])&VERIFIED.keys()
        assert len(found)<=1
        row={'name':g['name'],'source_identities':g['source_identities'],'state':'not_counted_as_generation_verified'}
        if found:
            key=next(iter(found));seen.add(key);evidence,scope=VERIFIED[key]
            assert (ROOT/evidence).exists()
            row.update(state='native_generation_verified_scope',evidence=evidence,scope=scope)
        elif 'overmap_special:campus'in g['source_identities']:
            r=json.loads((ROOT/'geometry_layer/CAMPUS_ADAPTATION_REPORT.json').read_text())
            assert not r['unresolved_typed_refs']
            row.update(state='prepared_pending_native_generation',evidence='geometry_layer/CAMPUS_ADAPTATION_REPORT.json',scope='All 26 first-layer maps; awaiting five native layout tests')
        rows.append(row)
    assert seen==VERIFIED.keys()
    verified=sum(r['state']=='native_generation_verified_scope'for r in rows)
    prepared=sum(r['state']=='prepared_pending_native_generation'for r in rows)
    report={'metric':'Unweighted accepted location groups with demonstrated geometry-generation scope',
      'accepted_groups':len(groups),'catalog_groups_deferred_for_rename_review':len(catalog)-len(groups),
      'verified_groups':verified,'verified_percent':round(100*verified/len(groups),1),
      'additional_prepared_groups':prepared,'verified_plus_prepared_percent':round(100*(verified+prepared)/len(groups),1),
      'evidence_checkpoint':checkpoint,'rows':rows,
      'limits':['Not percentage of all DDA content, source lines, map tiles or work hours','Groups have very different sizes; this is a transparent coarse meter','Generation-tested scopes include isolated previews and approved additions to existing BN locations','Not a claim of full player traversal, quest completion or final release acceptance','Other partially staged packages are not credited as finished','A pending new patch does not invalidate historical evidence, but must pass its own tests']}
    text=json.dumps(report,indent=2,ensure_ascii=False)+'\n';path=ROOT/'geometry_layer/PROGRESS.json'
    if check:assert path.read_text()==text,path
    else:path.write_text(text)
    print(f'Geometry generation scope verified: {verified}/{len(groups)} = {report["verified_percent"]}%; +{prepared} prepared group = {report["verified_plus_prepared_percent"]}% including pending work')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
