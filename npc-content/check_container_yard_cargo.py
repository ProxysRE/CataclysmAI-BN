#!/usr/bin/env python3
"""Guard cargo quantities, retained outcomes and the actual source leader."""
import copy
import json
import re
from fractions import Fraction
from prepare_container_yard_cargo import data, prepare, sources, definition, PREFIX, FOLDER
from adapt_container_yards import adapt

prepare(check=True)
maps,dependencies,changes=data();files=sources()
byid={e['id']:e for e in dependencies if isinstance(e.get('id'),str)}
nested={e['nested_mapgen_id']:e for e in maps if 'nested_mapgen_id' in e}
before=adapt()[0]
for a,b in zip(before,maps):
    if a['type']=='mapgen':
        for field in ('rows','parameters','npcs','place_npcs','faction_owner','mapgensize'):
            assert a['object'].get(field)==b['object'].get(field),field
        assert a.get('nested_mapgen_id')==b.get('nested_mapgen_id')
        assert a.get('om_terrain')==b.get('om_terrain')
    elif a['type']=='overmap_special':assert a==b
# No cargo branch was erased to close dependencies, including outstanding art,
# sunscreen, heavy machinery and the rare money branch.
assert {e['nested_mapgen_id'] for e in before if 'nested_mapgen_id' in e}==set(nested)
assert len(nested)==154  # 121 source identities plus 33 infrastructure wrappers.
for name,item,amount in [('nail_box_10lb_full','nail',230),('cig_box_cigarette_20','cig',20),('soap_packed','soap',50),('meth_bag_zipper_6','meth',6),('fertilizer_commercial_bag_canvas_60','fertilizer_commercial',60)]:
    entry=byid[PREFIX+name+'_contents']['entries'][0]
    assert entry['item']==item and entry['charges']==amount and 'count' not in entry
assert byid[PREFIX+'protein_bar_wrapped_box_contents']['entries'][0]['count']==96
assert byid[PREFIX+'twoliter_water_batch']['entries'][0]['count']==6
assert byid[PREFIX+'water_bottle_contents']['entries'][0]['charges']==8
for item in ('tampon','menstrual_pad'):
    assert byid[item]['type']=='GENERIC'
    expected=definition(files,'dda',item);expected.update(type='GENERIC',container='bag_plastic',snippet_category=PREFIX+item)
    assert byid[item]==expected
    assert byid[PREFIX+item+'_box_full_contents']['entries'][0]['count']==24
    assert byid[PREFIX+item+'_box_full']['entries'][0]['item']=='box_medium'
# Pinned fixed-volume checks are useful guards, but do not replace native item
# creation, default-container and post-modifier capacity tests.
def ml(value):
    m=re.fullmatch(r'([0-9.]+)\s*(ml|L)',value);assert m,value
    return Fraction(m[1])*(1000 if m[2]=='L' else 1)
boxes={e['id']:ml(e['contains']) for e in files['bn/data/json/items/containers.json'] if 'contains' in e}
for group,volume in [('nail_box_10lb_full',Fraction(230*250,100)),('cig_box_cigarette_20',Fraction(20*250,60)),('soap_packed',1250),('tampon_box_full',1200),('menstrual_pad_box_full',1200),('protein_bar_wrapped_box',24000)]:
    box=byid[PREFIX+group]['entries'][0]['item'];assert volume<=boxes[box],group
bank=nested['shipping_container_banknotes_1x1']['object']['items'][' ']
assert bank=={'item':PREFIX+'money_bundles','chance':95,'repeat':[10,50]}
assert Fraction(50)*ml(definition(files,'bn','money_bundle')['volume'])==12500
assert not any(e.get('id') in ('banknotes','coins') for e in dependencies)
# The leader remains a separate source NPC/class, not a renamed ordinary guard.
boss=definition(files,'dda','hells_raiders_boss');assert boss['mission']=='GUARD_PATROL'
boss['mission']=8
assert byid['hells_raiders_boss']==boss
leader=copy.deepcopy(definition(files,'dda','NC_BANDIT_LEADER'))
leader['traits']=[t for t in leader['traits'] if 'group' in t]
assert byid['NC_BANDIT_LEADER']==leader
assert len(changes['leader_equipment_groups'])==24
for name in changes['leader_equipment_groups']:
    assert byid[name]['entries']==[{'group':name.replace('NC_BANDIT_LEADER_','NC_BANDIT_',1)}]
wheels=byid[PREFIX+'wheels_no_wood']['items']
assert wheels==[e for e in definition(files,'bn','wheels')['items'] if e[0]!='wheel_wood']
report=json.loads((FOLDER/'CARGO_REPORT.json').read_text())
assert report['native_embedded'] is False and report['runtime_validated'] is False
assert report['unresolved_count']==20 and not report['core_id_overlaps'] and not report['bundled_mod_id_overlaps']
assert 'data/json/dda_container_yard' not in (FOLDER.parent/'artisan_engine.patch').read_text()
print('PASS: unchanged cargo outcomes/geometry; fixed charges and selected volume bounds; money scaling; source leader/class with 24 BN gear providers; staging only')
