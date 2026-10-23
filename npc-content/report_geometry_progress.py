#!/usr/bin/env python3
"""Count accepted location groups by demonstrated geometry-generation scope."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Match source identities, never positional catalog indices (which can shift).
VERIFIED={
 'overmap_special:cemetery_lacroix':('native/dda_geometry_preview.json','All four Lacroix cemetery ground cells and source roof passed source and installed generation'),
 'overmap_special:xedra_morgantown':('native/dda_geometry_preview.json','All Morgantown source cells passed source and installed generation'),
 'overmap_special:xedra_fishing_shack':('native/dda_geometry_preview.json','Fishing-shack source floor and roof passed source and installed generation'),
 'overmap_special:physics_lab_LIXA':('native/dda_geometry_preview.json','All LIXA source regions and sixteen source barrier positions passed source and installed generation; deferred device access remains separate'),
 'overmap_special:oil_platform':('native/dda_geometry_preview.json','All 204 platform source placements passed source and installed generation with BN lake context; open-water traversal remains separate'),
 'city_building:stadium_football':('native/dda_geometry_preview.json','All 145 football stadium placements passed source and installed generation'),
 'city_building:office_skyscraper':('native/dda_geometry_preview.json','All 44 skyscraper placements passed source and installed generation with reachable room definitions loaded; not exhaustive sampling of every random room variant'),
 'city_building:apartment_complex_3x3':('native/dda_geometry_preview.json','All five source apartment layouts and 322 placements passed source and installed generation, including 284 navigation and conditional-stair expectations'),
 'overmap_special:Hot Springs':('native/dda_geometry_preview.json','Hot-spring source cells passed source and installed generation with ordinary BN water collection'),
 'overmap_special:Pottery Cottage':('native/dda_geometry_preview.json','All eight cottage cells including basement and two upper levels passed source and installed generation'),
 'overmap_special:sunken_helicopter':('native/dda_geometry_preview.json','All source wreck cells and four lake-water context cells passed source and installed generation'),
 'city_building:police_dept':('native/dda_geometry_preview.json','All 30 police department cells, including rotated southern wing, passed source and installed generation'),
 'city_building:textile_mill_museum':('native/dda_geometry_preview.json','All 18 textile museum cells passed source and installed generation'),
 'overmap_special:supermarket':('native/dda_geometry_preview.json','All 18 supermarket cells passed source and installed generation'),
 'city_building:deserter_city':('native/dda_geometry_preview.json','All deserter settlement cells passed source and installed isolated geometry generation'),
 'overmap_special:drug_lab':('native/dda_geometry_preview.json','Drug lab, bandit drug lab and work camp passed source and installed all-floor generation'),
 'overmap_special:isolated_road':('native/dda_geometry_preview.json','All seven Isolated Road cells passed source and installed geometry generation'),
 'overmap_special:gun_show':('native/dda_geometry_preview.json','Both hall cells and both roof cells passed source and installed geometry generation'),
 'overmap_special:balthazar_bunker':('native/dda_geometry_preview.json','All eleven bunker cells and deterministic navigation terrain passed source and installed tests'),
 'overmap_special:limnological_station':('native/dda_geometry_preview.json','Roof, surface and all five underwater levels passed source and installed geometry tests'),
 'overmap_special:exodii_base':('native/dda_geometry_preview.json','Base, stone barn and warehouse; all source cells and projected navigation terrain'),
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
    assert {'hub_01','campus','exodii','frontier','raider','urban','research','large','apartment'}<=set(validation['geometry_preview']['packages'])
    assert checkpoint['geometry_test_cases'] >= 41 and checkpoint['installed_geometry_test_cases'] >= 41
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
