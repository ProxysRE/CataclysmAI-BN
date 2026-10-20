#!/usr/bin/env python3
"""Check reproducibility, shell/content separation and authentic layout conservation."""
import json
from prepare_geometry_layer import OUT,raw_sources,extract,prepare,NAV_FURNITURE

prepare(check=True)
shells=json.loads((OUT/'SHELLS.json').read_text())
deferred=json.loads((OUT/'LATER_LAYERS.json').read_text())
report=json.loads((OUT/'REPORT.json').read_text())
counts={}
for name,source in raw_sources().items():
    maps=[e for e in shells[name] if e['type']=='mapgen']
    originals=[e for e in source if e['type']=='mapgen']
    later=[e for e in deferred[name] if 'later_fields' in e]
    assert len(maps)==len(originals)==len(later)
    for original,shell,archive in zip(originals,maps,later):
        a,b=original['object'],shell['object']
        assert a.get('rows')==b.get('rows'),(name,'rows')
        assert all(c in set(b.get('terrain',{}))|set(b.get('furniture',{}))|set(b.get('nested',{}))|{' ','.'} for c in __import__('prepare_geometry_layer').glyphs(b.get('rows',[])))
        for c,v in b.get('terrain',{}).items():
            if c not in a.get('terrain',{}):assert v==b['fill_ter']
        assert a.get('mapgensize')==b.get('mapgensize'),(name,'dimensions')
        assert {k:v for k,v in original.items() if k!='object'}==archive['source']
        # Every non-comment source field remains in the shell or deferred archive.
        assert {k for k in a if not k.startswith('//')} <= set(b)|set(archive['later_fields'])|{'palettes','parameters','terrain','furniture','nested','place_nested','set','place_furniture'}
        for k,v in archive['later_fields'].items():
            if k not in b:assert v==a[k],(name,k,'lost source data')
        assert not ({'items','item','place_items','place_item','place_loot','place_monsters','monsters','monster','place_npcs','npcs','vehicles','place_vehicles','computers'}&set(b))
        assert all(NAV_FURNITURE.search(str(v)) for v in b.get('furniture',{}).values())
        assert all(p['type']=='ter_str_id' for p in b.get('parameters',{}).values())
    specials=[e for e in shells[name] if e['type']=='overmap_special']
    oldspecials=[e for e in source if e['type']=='overmap_special']
    for a,b in zip(oldspecials,specials):
        assert [(c['point'],c.get('overmap')) for c in a['overmaps']]==[(c['point'],c.get('overmap')) for c in b['overmaps']]
        assert all('terrain' not in c and c.get('connection') for c in b.get('connections',[]))
        assert len({tuple(c['point']) for c in b['overmaps']})==len(b['overmaps'])
    if name!='hub_01':assert not report['packages'][name]['unresolved_typed_refs']
    assert not report['packages'][name]['declared_omt_without_mapgen']
    counts[name]={'mapgen_definitions':len(maps),'special_cells':sum(len(s['overmaps']) for s in specials)}
assert not report['packages']['island_prison']['geometry_issues']
assert not report['packages']['xedra_church']['geometry_issues']
issues=report['packages']['container_yards']['geometry_issues']
assert len(issues)==1 and issues[0]['placement']['z']==1
assert issues[0]['type']=='nested_vertical_offset_not_supported_by_pinned_BN'
assert not report['native_validated']
# Regression probes: late-layer additions must be deferred, structural stairs kept.
probe={'type':'mapgen','om_terrain':'probe','object':{'rows':['X'],'terrain':{'X':'t_floor'},'furniture':{'X':'f_ladder'},'place_items':[{'item':'probe'}],'place_npcs':[{'class':'probe'}]}}
s,d,i=extract([probe]);assert not i
assert s[0]['object']['furniture']==probe['object']['furniture']
assert d[0]['later_fields']['place_items']==probe['object']['place_items']
assert d[0]['later_fields']['place_npcs']==probe['object']['place_npcs']
print('Geometry candidates: conservation/content separation checks passed; typed obligations remain explicitly reported for Hub:',counts)

# A furniture-only source glyph must retain its exact underlying floor in BN.
probe['object']['rows']=['XC'];probe['object']['fill_ter']='t_floor';probe['object']['furniture']['C']='f_chair'
s,d,i=extract([probe]);assert s[0]['object']['terrain']['C']=='t_floor'
assert d[0]['later_fields']['furniture']['C']=='f_chair'
