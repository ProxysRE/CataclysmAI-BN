#!/usr/bin/env python3
"""Continuous geometry study, before assigning any BN floors or walkability."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import zipfile

import numpy as np


def scene_plan(metadata, report):
    import UnityPy
    if UnityPy.__version__ != '1.25.4':
        raise ValueError('Use UnityPy==1.25.4')
    lookup={v:k for k,v in report['selected_scenes'].items()}
    modes={}
    with zipfile.ZipFile(metadata) as z:
        for mode in ('day','night'):
            raw=z.read(f'factory_{mode}_preset.bundle')
            env=UnityPy.load(raw)
            objects={o.path_id:o.parse_as_dict() for o in env.objects if o.type.name=='MonoBehaviour'}
            root=next(pid for pid,d in objects.items() if d['m_Name']==f'factory_{mode}.ScenesPreset')
            paths={}
            visiting=set()
            def visit(pid):
                if pid in visiting:
                    raise ValueError('Preset child cycle')
                visiting.add(pid)
                d=objects[pid]
                for key in d['_scenesResourceKeys']:
                    path=key['path']
                    if path not in lookup:
                        raise ValueError('Preset scene absent from export: '+path)
                    paths[path]={'export_scene':lookup[path],'only_offline':bool(key['_onlyOffline'])}
                for ref in d['ChildPresets']:
                    if ref['m_FileID']:
                        raise ValueError('External child preset unresolved')
                    visit(ref['m_PathID'])
                visiting.remove(pid)
            visit(root)
            modes[mode]={'bundle_sha256':hashlib.sha256(raw).hexdigest(),
                         'scenes':paths,'active_scene_name_not_exported':objects[root]['_activeSceneName']}
    common=set(modes['day']['scenes']) & set(modes['night']['scenes'])
    return {'modes':modes,'common_scene_paths':sorted(common),
            'limits':['Active Factory_Day/Factory_Night scene outside export remains uninspected',
                      'Serialized state only; custom behaviours not evaluated']}


def box_triangles(c):
    centre=np.array([c['m_Center'][k] for k in 'xyz'])
    size=np.array([c['m_Size'][k] for k in 'xyz'])
    signs=np.array([[-1,-1,-1],[-1,-1,1],[-1,1,-1],[-1,1,1],
                    [1,-1,-1],[1,-1,1],[1,1,-1],[1,1,1]])
    v=centre+signs*size/2
    ids=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],
                  [2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return v,ids


def transformed_triangles(v,ids,matrix):
    m=np.asarray(matrix,dtype=float)
    return (v@m[:3,:3].T+m[:3,3])[ids]


def plane_segments(triangles,height,epsilon=1e-7):
    """Intersect triangles with Y=height; skip coplanar faces and point contacts."""
    d=triangles[:,:,1]-height
    mask=(d.min(1)<=epsilon)&(d.max(1)>=-epsilon)
    ts=triangles[mask];ds=d[mask];ds[np.abs(ds)<=epsilon]=0
    result=[]
    for t,dist in zip(ts,ds):
        zero=np.flatnonzero(dist==0)
        if len(zero)==3:
            continue
        if len(zero)==2:
            a,b=t[zero]
        else:
            points=[t[i] for i in zero]
            for i,j in ((0,1),(1,2),(2,0)):
                if dist[i]*dist[j]<0:
                    points.append(t[i]+(t[j]-t[i])*(-dist[i])/(dist[j]-dist[i]))
            if len(points)!=2:
                continue
            a,b=points
        if np.linalg.norm(a-b)>epsilon:
            result.append([[a[0],a[2]],[b[0],b[2]]])
    return np.asarray(result,dtype=float).reshape(-1,2,2)


def horizontal_bins(triangles,step=0.05):
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    norm=np.linalg.norm(cross,axis=1)
    keep=(norm>1e-8)&(np.abs(cross[:,1])>=0.995*norm)&(np.ptp(triangles[:,:,1],axis=1)<=0.04)
    bins=collections.Counter()
    for y,area in zip(triangles[keep,:,1].mean(1),norm[keep]*0.5):
        bins[round(float(y)/step)*step]+=float(area)
    return [{'y':round(y,5),'triangle_area_sum':round(a,4)} for y,a in sorted(bins.items())]


def analyze(export,metadata,outdir):
    # Integrity is a separate gate, using the validated archive digest.
    from validate_factory_export import validate
    validation=validate(export)
    outdir.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(export) as z:
        report=json.loads(z.read('report.json'))
        plan=scene_plan(metadata,report)
        selected=set(v['export_scene'] for v in plan['modes']['day']['scenes'].values())
        layer_ids={name:i for i,name in enumerate(report['layers'])}
        layers={layer_ids['LowPolyCollider'],layer_ids['DoorLowPolyCollider'],layer_ids['Terrain']}
        meshes={}
        for line in z.open('meshes.jsonl'):
            m=json.loads(line)
            meshes[m['file'],m['path_id']]=(m['name'],np.asarray(m['vertices'],dtype=float),np.asarray(m['triangles'],dtype=int))
        by_scene=collections.defaultdict(list)
        large_horizontal_components=collections.defaultdict(list)
        candidates=[]
        excluded=collections.Counter()
        seen={}
        duplicates=[]
        selected_counts=collections.Counter()
        for line in z.open('colliders.jsonl'):
            c=json.loads(line)
            if c['scene'] not in selected:
                excluded['other_variant']+=1;continue
            if c['layer'] not in layers:
                excluded['other_collision_layer']+=1;continue
            if not(c['active_in_hierarchy'] and c['enabled'] and not c['is_trigger']):
                excluded['inactive_disabled_or_trigger']+=1;continue
            key=(c['scene'],c['component_path_id'])
            mesh_name=''
            if c['type']=='MeshCollider' and c['mesh']:
                ref=c['mesh'];mesh_key=ref['file'],ref['path_id']
                mesh_name,v,ids=meshes[mesh_key]
                signature=('mesh',c['layer'],c['convex'],mesh_key,tuple(x for row in c['world_matrix'] for x in row))
            elif c['type']=='BoxCollider':
                v,ids=box_triangles(c)
                signature=('box',c['layer'],tuple(c['m_Center'][k] for k in 'xyz'),tuple(c['m_Size'][k] for k in 'xyz'),
                           tuple(x for row in c['world_matrix'] for x in row))
            else:
                excluded['unsupported_or_empty_shape']+=1;continue
            if signature in seen:
                duplicates.append({'kept':seen[signature],'duplicate':key})
                continue
            seen[signature]=key
            tr=transformed_triangles(v,ids,c['world_matrix'])
            by_scene[c['scene']].append(tr)
            selected_counts[c['scene']+':'+c['type']]+=1
            bins=horizontal_bins(tr)
            area=sum(b['triangle_area_sum'] for b in bins)
            if area>=20:
                large_horizontal_components[c['scene']].append(
                    {'component_path_id':c['component_path_id'],'name':c['name'],'mesh_name':mesh_name,
                     'horizontal_triangle_area_sum':area,
                     'largest_bins':sorted(bins,key=lambda b:b['triangle_area_sum'],reverse=True)[:8]})
            if re.search('stair|ladder|ramp',c['name']+' '+mesh_name,re.I):
                lo,hi=tr.reshape(-1,3).min(0),tr.reshape(-1,3).max(0)
                candidates.append({'scene':c['scene'],'component_path_id':c['component_path_id'],
                                   'name':c['name'],'mesh_name':mesh_name,'bounds_min_xyz':lo.tolist(),
                                   'bounds_max_xyz':hi.tolist(),'height_span':float(hi[1]-lo[1]),
                                   'portable_name':bool(re.search('stepladder',c['name']+' '+mesh_name,re.I)),
                                   'accepted_route':False})
    arrays={n:np.concatenate(ts) for n,ts in by_scene.items()}
    heights={n:horizontal_bins(ts) for n,ts in arrays.items()}
    # Named source scenes define the diagnostic frame, not a playable boundary.
    roi_names={sid for sid,path in report['selected_scenes'].items()
               if Path(path).stem in ('Factory_Rework_Areas','Factory_Rework_Main_Building',
                                     'Factory_Rework_Basement','Factory_Rework_Admin_Office','Factory_Rework_Laboratory')}
    roi=np.concatenate([tr for sid,tr in arrays.items() if sid in roi_names]).reshape(-1,3)
    frame={'x':[float(roi[:,0].min())-3,float(roi[:,0].max())+3],
           'z':[float(roi[:,2].min())-3,float(roi[:,2].max())+3]}
    all_triangles=np.concatenate(list(arrays.values()))
    studies={'schema_version':1,'evidence':'continuous_serialized_geometry_not_BN_mapgen',
             'numpy_version':np.__version__,'UnityPy_version':'1.25.4',
             'archive_sha256':validation['archive_sha256'],'mode':'day','scene_plan':plan,
             'analysis_layers':[report['layers'][i] for i in sorted(layers)],
             'selected_colliders':dict(selected_counts),'excluded_colliders':dict(excluded),
             'exact_duplicate_instances':duplicates,'world_triangles':len(all_triangles),
             'horizontal_bins_by_scene':heights,'stair_name_candidates':candidates,'diagnostic_frame':frame,
             'largest_horizontal_components_by_scene':{
                 n:sorted(rows,key=lambda c:c['horizontal_triangle_area_sum'],reverse=True)[:20]
                 for n,rows in large_horizontal_components.items()},
             'limits':['No walkability or floor assignment from names, height bins or cross sections',
                       'Box TRS is geometric; sheared boxes and convex cooking need engine review',
                       'Horizontal areas include roofs, ceilings, undersides and overlapping surfaces',
                       'Axes are Unity X/Y/Z, no geographic north or BN scale calibration']}
    for name,data in [('scene_plan.json',plan),('space_analysis.json',studies)]:
        (outdir/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    np.savez_compressed(outdir/'world_triangles.npz',**arrays)
    return studies,all_triangles


def preview(study,triangles,path,heights):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig,axes=plt.subplots(2,2,figsize=(14,14),layout='constrained')
    counts=[]
    for ax,height in zip(axes.flat,heights):
        seg=plane_segments(triangles,height)
        ax.add_collection(LineCollection(seg,colors='#173f50',linewidths=.45))
        ax.set(xlim=study['diagnostic_frame']['x'],ylim=study['diagnostic_frame']['z'],xlabel='Unity X',ylabel='Unity Z')
        ax.set_aspect('equal');ax.grid(alpha=.12)
        ax.set_title(f'Y = {height:g} · {len(seg)} отрезков')
        counts.append({'y':height,'segments':len(seg)})
    fig.suptitle('Завод · геометрические сечения дневного набора сцен\nЭто не назначенные этажи и не карта проходимости BN',fontsize=14)
    fig.savefig(path,dpi=150)
    plt.close(fig)
    return counts


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('export',type=Path)
    p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--heights',type=float,nargs=4,default=[-1.65,1.05,4.05,8.05])
    a=p.parse_args()
    study,tr=analyze(a.export,a.metadata,a.output)
    cuts=preview(study,tr,a.output/'sections.png',a.heights)
    (a.output/'sections.json').write_text(json.dumps(cuts,indent=2)+'\n')
    print(json.dumps({'world_triangles':study['world_triangles'],'stair_name_candidates':len(study['stair_name_candidates']),
                      'day_scenes':len(study['scene_plan']['modes']['day']['scenes']),'sections':cuts},indent=2))
