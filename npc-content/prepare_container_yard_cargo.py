#!/usr/bin/env python3
"""Prepare BN cargo quantities and the source raider leader, without installing yards."""
import argparse
import base64
import copy
import gzip
import hashlib
import json
from collections import Counter
from adapt_dialogue import adapt as adapt_npc
from adapt_container_yards import adapt, FOLDER, ROOT
from prepare_container_yards import required
from prepare_regional_locations import index_entries, references, BUILTIN_IDS
from export_bn_ids import read_cache
from audit_bn_mod_content import read_cache as mod_cache, added_core_declarations

PREFIX='dda_container_yard_'
REUSE={
 'cigar_box_unopened':('cigar_box_opened','Reuse the already ported cigar box group; source sealed/full quantity is approximated by its existing contents.'),
 'magazines_akm':('display_ak47_mag','Stock BN AK magazine distribution and capacities.'),
 'new_phones':('phones','Stock BN phone models and battery charges; new-in-box state is approximated.'),
 'mundane_science':('tools_science','Stock BN laboratory equipment; source incidental chemicals/files are approximated.'),
 'dentist_supplies':('tools_medical','Stock BN medical instruments; use its broader portable medical selection.'),
}
PACKS={'duct_tape_roll','nail_box_10lb_full','cig_box_cigarette_20','coke_bag_zipper_1_8','meth_bag_zipper_6',
       'soap_packed','tampon_box_full','menstrual_pad_box_full','protein_bar_wrapped_box','twoliter_water_batch',
       'fertilizer_commercial_bag_canvas_60','tools_fishingrods_commercial','tools_fishingrods_portable','wheels_no_wood'}


def sources():
    m=json.loads((FOLDER/'CARGO_SOURCE_MANIFEST.json').read_text())
    assert m['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    raw=gzip.decompress(base64.b64decode(''.join((FOLDER/p).read_text() for p in m['parts']),validate=True))
    assert hashlib.sha256(raw).hexdigest()==m['bundle_sha256']
    files=json.loads(raw);assert set(files)==set(m['files'])
    for p,s in files.items():
        b=s.encode();r=m['files'][p]
        assert hashlib.sha256(b).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['blob_sha']
    return {p:json.loads(s) for p,s in files.items()}


def definition(files,side,name):
    values=[e for p,entries in files.items() if p.startswith(side+'/') for e in entries if e.get('id')==name]
    assert len(values)==1,(side,name,len(values))
    return copy.deepcopy(values[0])


def data():
    files=sources();maps,infrastructure,changes=adapt();extra=[];quantities=[]
    def group(name,entries,subtype='collection'):
        e={'type':'item_group','id':PREFIX+name,'subtype':subtype,'entries':entries};extra.append(e);return e['id']
    def packed(name,container,contents):
        inner=group(name+'_contents',contents)
        group(name,[{'item':container,'contents-group':inner}])
    # Charged items need explicit BN quantities, never repeated full defaults.
    assert definition(files,'bn','nail')['stack_size']==100
    assert definition(files,'dda','nail_box_10lb_full')['items'][0]['count']==230
    packed('nail_box_10lb_full','box_small',[{'item':'nail','charges':230,'container-item':'null'}])
    assert definition(files,'dda','duct_tape_roll')['items'][0]['charges']==200
    group('duct_tape_roll',[{'item':'duct_tape','charges':200}])
    assert {e['count'] for e in definition(files,'dda','cigarettes_new')['items']}=={20}
    packed('cig_box_cigarette_20','box_cigarette',[{'item':'cig','charges':20,'container-item':'null'}])
    for name,item,amount in [('coke_bag_zipper_1_8','coke',[1,8]),('meth_bag_zipper_6','meth',6)]:
        assert definition(files,'dda',name)['entries'][0]['count']==amount
        packed(name,'bag_zipper_small',[{'item':item,'charges':amount,'container-item':'null'}])
    # A BN soap bar has ten charges. Five source bars need 50, not five.
    assert definition(files,'bn','soap')['count']==10
    assert definition(files,'dda','soap_packed')['entries'][0]['count']==5
    packed('soap_packed','box_medium',[{'item':'soap','charges':50}])
    # These are missing everyday objects, not new medical/physiology mechanics.
    for item in ('tampon','menstrual_pad'):
        e=definition(files,'dda',item);assert e['type']=='ITEM'
        e['type']='GENERIC';e['container']='bag_plastic'
        snippets=e.pop('snippet_category');assert isinstance(snippets,list)
        category=PREFIX+item;e['snippet_category']=category
        extra += [e,{'type':'snippet','category':category,'text':snippets}]
        name=item+'_box_full'
        assert definition(files,'dda',name)['items'][0]['count']==24
        # 24 x 50 ml exceeds the BN 1 L small box. Keep all 24 in 3 L.
        packed(name,'box_medium',[{'item':item,'count':24,'container-item':'null'}])
    assert definition(files,'dda','fertilizer_commercial_bag_canvas_60')['entries'][0]['count']==60
    packed('fertilizer_commercial_bag_canvas_60','bag_canvas',[{'item':'fertilizer_commercial','charges':60,'container-item':'null'}])
    assert definition(files,'dda','full_box_of_evacuation_protein_bar')['entries'][0]['count']==12
    assert definition(files,'dda','protein_bar_wrapped_box')['entries'][0]['count']==8
    assert definition(files,'bn','protein_bar_evac')['volume']=='250 ml'
    packed('protein_bar_wrapped_box','box_huge',[{'item':'protein_bar_evac','count':96,'charges':1,'container-item':'null'}])
    water=definition(files,'dda','twoliter_water_batch')['entries'][0]
    assert water['charges']==8 and water['count']==6
    inner=group('water_bottle_contents',[{'item':'water_clean','charges':8,'container-item':'null'}])
    group('twoliter_water_batch',[{'item':'bottle_twoliter','contents-group':inner,'count':6}])
    # Preserve source rod selection weights, using BN rod mechanics.
    for name in ('tools_fishingrods_commercial','tools_fishingrods_portable'):
        source=definition(files,'dda',name)
        entries=copy.deepcopy(source['entries'])
        for e in entries:
            e['item']={'fishing_rod_2pc_packed':'fishing_rod_professional','fishing_rod_tele_packed':'fishing_rod_professional','plastichoboreel':'fishing_rod_basic'}.get(e['item'],e['item'])
        group(name,entries,'distribution')
    # BN's wheel pool already supplies all required kinds. Keep its weights
    # and remove only wood locally, leaving the global group unchanged.
    wheels=definition(files,'bn','wheels')
    wheels['id']=PREFIX+'wheels_no_wood'
    assert any(e[0]=='wheel_wood' for e in wheels['items'])
    wheels['items']=[e for e in wheels['items'] if e[0]!='wheel_wood'];extra.append(wheels)
    money=group('money_bundles',[{'item':'money_bundle'}])

    boss=adapt_npc(definition(files,'dda','hells_raiders_boss'),Counter())
    assert boss['mission']==8  # Existing verified BN GUARD_PATROL enum adapter.
    leader=definition(files,'dda','NC_BANDIT_LEADER')
    unsupported={'NO_BASH','RETURN_TO_START_POS','IGNORE_SOUND'}
    assert {t['trait'] for t in leader['traits'] if 'trait' in t}==unsupported
    leader['traits']=[t for t in leader['traits'] if t.get('trait') not in unsupported]
    # Reuse BN's class-specific clothing/weapon/carry selection via lightweight
    # group references, keeping the leader's source attributes and skill rolls.
    equipment=[]
    for e in files['bn/data/json/npcs/NC_BANDIT.json']:
        if e.get('type')!='item_group' or not e.get('id','').startswith('NC_BANDIT_'):continue
        n=e['id'].replace('NC_BANDIT_','NC_BANDIT_LEADER_',1);equipment.append(n)
        extra.append({'type':'item_group','id':n,'subtype':'distribution','entries':[{'group':e['id']}]})
    extra += [leader,boss]
    aliases={s:t for s,(t,r) in REUSE.items()}
    aliases.update({name:PREFIX+name for name in PACKS})
    aliases['GROUP_SLIME']='GROUP_BLOB'
    def walk(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
        return v
    maps=walk(maps)
    bank=next(e for e in maps if e.get('nested_mapgen_id')=='shipping_container_banknotes_1x1')['object']['items'][' ']
    assert bank=={'item':'banknotes','chance':95,'repeat':[200,1000]}
    bank.update(item=money,repeat=[10,50])
    quantities=[{'source':n,'native_group':PREFIX+n} for n in sorted(PACKS)]
    return maps,infrastructure+extra,{'quantity_groups':quantities,'leader_equipment_groups':equipment,
           'unsupported_leader_traits':sorted(unsupported),'money_repeat':{'source':[200,1000],'bn':[10,50],'chance':95,'max_loose_volume_ml':12500},
           'reused_groups':REUSE,'slime_counterpart':'GROUP_BLOB'}


def prepare(check=False):
    maps,dependencies,changes=data()
    core=set(map(tuple,read_cache(ROOT/'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    port=added_core_declarations((ROOT/'artisan_engine.patch').read_text())
    own=index_entries(maps+dependencies)-BUILTIN_IDS
    mods={(e['type'],e['id']) for e in mod_cache()['records']}
    assert not own&core and not own&port and not own&mods
    refs=required(maps)
    for e in dependencies:
        if e['type']=='item_group':refs.update(references({'items':{'_':{'item':e}}}))
        elif e['type']=='npc':refs.update({('npc_class',e['class']),('faction',e['faction'])})
        elif e['type']=='npc_class':
            refs.update(('trait_group',t['group']) for t in e['traits'])
            refs.update(('skill',s['skill']) for s in e['skills'] if s['skill']!='ALL')
        elif e['type']=='GENERIC':refs.add(('item',e['container']))
    unresolved=refs-core-port-own
    report={'status':'cargo_and_raider_leader_adapted_not_installed','native_embedded':False,'runtime_validated':False,
            'definitions':dict(Counter(e['type'] for e in maps+dependencies)),**changes,
            'unresolved_typed_references':sorted(unresolved),'unresolved_count':len(unresolved),
            'core_id_overlaps':sorted(own&core),'bundled_mod_id_overlaps':sorted(own&mods),
            'quantity_notes':['Source tobacco/drug/nail counts become explicit BN charges; no full-stack multiplication',
                              'Cigarette brands collapse to the stock BN cigarette; packed/telescopic rod choices reuse BN rods while retaining each selection weight',
                              'Five soap bars become 50 BN charges in a 3 L box; hygiene boxes keep 24 items in a 3 L box',
                              'Protein carton keeps all 96 rations in stock BN 40 L box; water batch keeps six 2 L bottles',
                              'Rare cash cargo keeps its branch weight and 95% cell chance; paper-count approximation of 20 bills per stock money bundle, 10..50 bundles rather than 200..1000 bundles. No denomination/value equivalence is claimed'],
            'leader_notes':['Source identity, faction, attitude, patrol mission, chat endpoint, attributes and skill distributions retained',
                            'Existing BN bandit equipment groups are referenced; no copied item definitions',
                            'Three unsupported DDA-only AI traits omitted; BN patrol/hearing/bash behavior applies. No exact DDA AI parity claim'],
            'remaining':['Resolve every listed dependency; do not drop a cargo outcome',
                         'At integration, split NPC/class definitions into data/json/npcs loading phase',
                         'Native schema loading, actual contents/container capacity and all cargo outcomes',
                         'Full site placement, vertical traversal, NPC population/ownership and manual play'],
            'reference_scope':'Explicit map leaves, item-group leaves, NPC class/trait-group/skill references; not a full native schema/functional proof'}
    for name,value in [('CARGO_LOCATIONS.json',maps),('CARGO_DEPENDENCIES.json',dependencies),('CARGO_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';path=FOLDER/name
        if check:assert path.read_text()==text,path
        else:path.write_text(text)
    print('PASS: yard cargo and source raider leader staged;',len(PACKS),'quantity/selection groups;',len(changes['leader_equipment_groups']),'BN equipment references;',len(unresolved),'typed dependencies remain; native/container verification pending')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
