#!/usr/bin/env python3
"""Verify selected large-site scope before embedding it in the native preview."""
import collections,json
from prepare_large_site_preview import prepare,OUT
from prepare_container_yards import required
from check_geometry_terrain_schema import validate_locations


def check():
    prepare(check=True)
    full=json.loads((OUT/'LARGE_SITES_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    entries=json.loads((OUT/'LARGE_SITES_PREVIEW_SHELL.json').read_text(encoding='utf-8'))
    report=json.loads((OUT/'LARGE_SITES_PREVIEW_REPORT.json').read_text(encoding='utf-8'))
    assert report['nested_definitions']==222 and len(report['excluded_nested_identities'])==49
    assert not report['reachable_vertical_blockers']
    assert {e['source']for e in report['excluded_vertical_blockers']}=={'roof_6x6_greenhouse_1','roof_6x6_greenhouse_2'}
    selected={e['nested_mapgen_id']for e in entries if 'nested_mapgen_id'in e}
    assert len(selected)==140
    assert not {n for t,n in required(entries)if t=='nested_mapgen'and n!='null'}-selected
    assert not selected&set(report['excluded_nested_identities'])
    # All source layout alternatives for every used identity must remain exact.
    source_variants=collections.Counter(json.dumps(e,sort_keys=True)for e in full if e.get('nested_mapgen_id')in selected)
    chosen_variants=collections.Counter(json.dumps(e,sort_keys=True)for e in entries if 'nested_mapgen_id'in e)
    assert source_variants==chosen_variants
    roots=lambda es:[e for e in es if e['type']=='mapgen'and 'om_terrain'in e]
    assert roots(full)==roots(entries)
    specials={e['id']:e for e in entries if e['type']=='overmap_special'}
    assert sum(len(e['overmaps'])for e in specials.values())==393
    assert specials['oil_platform']['flags']==['MAN_MADE','LAKE','UNIQUE']
    assert specials['oil_platform']['locations']==['lake_surface']
    for e in full:
        if e['type']!='overmap_special':continue
        assert [(c['point'],c.get('overmap'))for c in e['overmaps']]==[(c['point'],c.get('overmap'))for c in specials[e['id']]['overmaps']]
    stock=json.loads((OUT/'waterside_adaptation_sources/bn/data/json/overmap/special_locations.json').read_text(encoding='utf-8'))
    validate_locations(entries,stock)
    assert report['navigation_points']==671
    assert report['navigation_points_excluded_for_random_nested_overlap']==58
    assert report['ordinary_water_points_omitted_for_sampling']==13025
    print('PASS: all 32 world maps and 222 reachable nested variants retained; 49 unused identities archived; BN lake predicates valid; 671 deterministic points plus all-cell non-null coverage prepared')


if __name__=='__main__':check()
