#!/usr/bin/env python3
"""Select reachable large-site geometry and use BN lake context for the platform."""
import argparse,collections,copy,json
from prepare_large_site_geometry import OUT
from adapt_large_site_geometry import prepare as adapt
from prepare_container_yards import required
from prepare_regional_locations import flatten


def prepare(check=False):
    adapt(check=True)
    entries=json.loads((OUT/'LARGE_SITES_ADAPTED_SHELL.json').read_text(encoding='utf-8'))
    nested=collections.defaultdict(list)
    for e in entries:
        if 'nested_mapgen_id'in e:nested[e['nested_mapgen_id']].append(e)
    def reachable(roots):
        seen=set();todo=[n for t,n in required(roots)if t=='nested_mapgen']
        while todo:
            n=todo.pop()
            if n=='null'or n in seen:continue
            assert n in nested,('Missing reachable nested geometry',n)
            seen.add(n);todo.extend(k for t,k in required(nested[n])if t=='nested_mapgen')
        return seen
    world=[e for e in entries if e['type']=='mapgen'and 'om_terrain'in e]
    all_reachable=reachable(world)
    selected=[copy.deepcopy(e)for e in entries if 'nested_mapgen_id'not in e or e['nested_mapgen_id']in all_reachable]
    by_site={}
    for label,prefix in [('stadium_football','stadium_football'),('office_skyscraper','office_skyscraper'),('oil_platform','oil_platform')]:
        roots=[e for e in world if any(n.startswith(prefix)for n in flatten(e['om_terrain']))]
        seen=reachable(roots)
        by_site[label]={'world_map_definitions':len(roots),'nested_identities':sorted(seen),
                       'nested_definitions':sum(len(nested[n])for n in seen)}
    blocked=[]
    for e in selected:
        if e['type']!='mapgen':continue
        for placement in e['object'].get('place_nested',[]):
            if placement.get('z',0)!=0:blocked.append({'source':e.get('om_terrain',e.get('nested_mapgen_id')),'placement':placement})
    assert not blocked,blocked
    # BN's existing lake habitat supplies placement predicates; all platform
    # geometry and local salt-water terrains retain their source coordinates.
    habitats={'ocean_surface':'lake_surface','ocean_water_cube':'lake_water_cube','ocean_bed':'lake_bed'}
    adaptations=[]
    for e in selected:
        if e['type']!='overmap_special':continue
        if e['id']=='oil_platform':
            assert 'OCEAN'in e['flags']
            e['flags']=['LAKE'if f=='OCEAN'else f for f in e['flags']]
            adaptations.append({'site':e['id'],'field':'flags','source':['OCEAN'],'bn':['LAKE']})
        for cell in [e]+e['overmaps']:
            if 'locations'not in cell:continue
            before=cell['locations'];after=[habitats.get(n,n)for n in before]
            if before!=after:adaptations.append({'site':e['id'],'point':cell.get('point'),'source':before,'bn':after})
            cell['locations']=after
    assert {a['site']for a in adaptations}=={'oil_platform'}
    # Exact signature conservation proves that selection retains every variant
    # of a reachable identity, rather than choosing one convenient room.
    def signatures(es):
        return collections.Counter(json.dumps(e,sort_keys=True)for e in es if 'nested_mapgen_id'in e)
    assert signatures(selected)==signatures([e for e in entries if e.get('nested_mapgen_id')in all_reachable])
    navigation={};masked_points=0;water_points_omitted=0
    for e in world:
        obj=e['object'];assert obj.get('rotation',0)==0,e.get('om_terrain')
        omt=e['om_terrain'];matrix=[[omt]]if isinstance(omt,str)else [omt]if isinstance(omt[0],str)else omt
        overlays=set()
        def mask(piece,px,py):
            refs={n for t,n in required([{'type':'mapgen','object':{'nested':{'x':piece}}}])if t=='nested_mapgen'and n!='null'}
            sizes=[p['object']['mapgensize']for n in refs for p in nested[n]]
            radius=max((max(size)for size in sizes),default=0)
            xr=px if isinstance(px,list)else [px,px];yr=py if isinstance(py,list)else [py,py]
            overlays.update((x,y)for x in range(xr[0],xr[-1]+radius)for y in range(yr[0],yr[-1]+radius))
        for y,row in enumerate(obj.get('rows',[])):
            for x,g in enumerate(row):
                if g in obj.get('nested',{}):mask(obj['nested'][g],x,y)
        for piece in obj.get('place_nested',[]):mask(piece,piece['x'],piece['y'])
        for y,row in enumerate(obj.get('rows',[])):
            for x,g in enumerate(row):
                terrain=obj.get('terrain',{}).get(g);furniture=obj.get('furniture',{}).get(g)
                for value,is_furniture in ((terrain,False),(furniture,True)):
                    if not isinstance(value,str):continue
                    if not (value.startswith('dda_geo_large_')or any(n in value for n in ('stairs','ladder','ramp','elevator'))):continue
                    if (x,y)in overlays:masked_points+=1;continue
                    if value=='dda_geo_large_saltwater_cube'and (x%24,y%24)not in {(0,0),(23,0),(12,12),(0,23),(23,23)}:
                        water_points_omitted+=1;continue
                    point={'x':x%24,'y':y%24,'terrain':value}
                    if is_furniture:point['furniture']=True
                    navigation.setdefault(matrix[y//24][x//24],[]).append(point)
    ar=json.loads((OUT/'LARGE_SITES_ADAPTATION_REPORT.json').read_text(encoding='utf-8'))
    report={'status':'large_site_geometry_embedded_pending_windows','native_embedded':True,'runtime_validated':False,
      'sites':by_site,'world_maps':len(world),'nested_identities':len(all_reachable),
      'nested_definitions':sum('nested_mapgen_id'in e for e in selected),
      'excluded_nested_identities':sorted(set(nested)-all_reachable),
      'excluded_vertical_blockers':ar['geometry_issues'],'reachable_vertical_blockers':blocked,
      'habitat_adaptations':adaptations,'unresolved_typed_refs':[],
      'navigation':navigation,'navigation_points':sum(map(len,navigation.values())),
      'navigation_points_excluded_for_random_nested_overlap':masked_points,
      'ordinary_water_points_omitted_for_sampling':water_points_omitted,
      'limits':['Only source-reachable nested graph is embedded; full staging and originals retained',
                'Platform uses BN lake habitat, with source geometry and local salt water; surrounding BN lakes retain stock fresh-water behavior',
                'Natural placement remains disabled; source lake depth and all-floor traversal require separate acceptance',
                'No native generation or progress credit yet; unrelated upward-roof nests remain unsupported']}
    for name,value in [('LARGE_SITES_PREVIEW_SHELL.json',selected),('LARGE_SITES_PREVIEW_REPORT.json',report)]:
        text=json.dumps(value,indent=2,ensure_ascii=True)+'\n';p=OUT/name
        if check:assert p.read_text(encoding='utf-8')==text,p
        else:p.write_text(text,encoding='utf-8')
    print(f'Large-site preview: {len(world)} world maps, {report["nested_definitions"]} reachable nested variants; no active vertical-offset blockers')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');prepare(p.parse_args().check)
