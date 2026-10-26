#!/usr/bin/env python3
"""Sample standing supports and swept-box connections in a serialized snapshot.

This is an explicit geometric model, not Unity/BN character-controller validation.
"""
import argparse
import collections
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import scipy
from scipy.spatial import ConvexHull

from analyze_factory_space import box_triangles, transformed_triangles
from validate_factory_export import validate


def closed_mesh(vertices, indices):
    # Weld exactly equal source positions, including split UV/normal vertices.
    _,inverse=np.unique(vertices,axis=0,return_inverse=True)
    faces=inverse[indices]
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    return bool(len(counts) and np.all(counts==2))


def convex_faces(vertices):
    hull=ConvexHull(vertices)
    faces=hull.simplices.copy()
    tr=vertices[faces]
    normals=np.cross(tr[:,1]-tr[:,0],tr[:,2]-tr[:,0])
    flip=np.einsum('ij,ij->i',normals,hull.equations[:,:3])<0
    faces[flip]=faces[flip][:,[0,2,1]]
    return faces


def ray_hits(triangles,x,z):
    """All non-vertical triangle intersections of an infinite vertical line."""
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    e1,e2=b-a,c-a
    den=e1[:,0]*e2[:,2]-e1[:,2]*e2[:,0]
    valid=np.abs(den)>1e-10
    ids=np.flatnonzero(valid)
    den=den[valid];p=np.array([x,z])-a[valid][:,[0,2]]
    u=(p[:,0]*e2[valid,2]-p[:,1]*e2[valid,0])/den
    v=(e1[valid,0]*p[:,1]-e1[valid,2]*p[:,0])/den
    inside=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
    y=a[ids,1]+u*e1[ids,1]+v*e2[ids,1]
    return ids[inside],y[inside]


def triangle_box_overlap(triangles,centre,half):
    """Separating-axis test: box axes, triangle normal and nine edge axes."""
    t=triangles-np.asarray(centre)
    h=np.asarray(half)
    keep=np.all(t.min(1)<=h+1e-9,axis=1)&np.all(t.max(1)>=-h-1e-9,axis=1)
    ids=np.flatnonzero(keep)
    t=t[keep]
    if not len(t):
        return ids
    edges=[t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]]
    axes=[np.cross(edges[0],edges[1])]
    axes.extend(np.cross(edge,axis) for edge in edges for axis in np.eye(3))
    for axis in axes:
        projection=np.einsum('nij,nj->ni',t,axis)
        radius=np.abs(axis)@h
        separated=(projection.min(1)>radius+1e-9)|(projection.max(1)<-radius-1e-9)
        keep[ids[separated]]=False
    return np.flatnonzero(keep)


def segment_supported(triangles,start,end,tolerance=0.2):
    """Cover a foot trace with projected triangles, clipping linear inequalities.

    Unlike midpoint sampling this cannot silently bridge a gap between supports.
    Caller selects upward/supportable faces before invoking it.
    """
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    e1,e2=b-a,c-a
    den=e1[:,0]*e2[:,2]-e1[:,2]*e2[:,0]
    good=np.abs(den)>1e-10
    a,e1,e2,den=a[good],e1[good],e2[good],den[good]
    if not len(a):return False
    p=np.asarray(start)[[0,2]]-a[:,[0,2]]
    delta=np.asarray(end)-start
    u=(p[:,0]*e2[:,2]-p[:,1]*e2[:,0])/den
    v=(e1[:,0]*p[:,1]-e1[:,2]*p[:,0])/den
    du=(delta[0]*e2[:,2]-delta[2]*e2[:,0])/den
    dv=(e1[:,0]*delta[2]-e1[:,2]*delta[0])/den
    dy=a[:,1]+u*e1[:,1]+v*e2[:,1]-start[1]
    ddy=du*e1[:,1]+dv*e2[:,1]-delta[1]
    low=np.zeros(len(a));high=np.ones(len(a));valid=np.ones(len(a),bool)
    for intercept,slope in [(u,du),(v,dv),(1-u-v,-du-dv),
                             (tolerance-dy,-ddy),(tolerance+dy,ddy)]:
        moving=np.abs(slope)>1e-12
        valid &= moving | (intercept>=-1e-8)
        bound=np.divide(-intercept,slope,out=np.zeros(len(a)),where=moving)
        low=np.where(moving&(slope>0),np.maximum(low,bound),low)
        high=np.where(moving&(slope<0),np.minimum(high,bound),high)
    valid &= low<=high+1e-8
    reach=0.0
    for i in np.argsort(low[valid]):
        left,right=low[valid][i],high[valid][i]
        if left>reach+1e-7:return False
        reach=max(reach,float(right))
        if reach>=1-1e-7:return True
    return False


class SceneGeometry:
    def __init__(self,triangles,owners,closed,source_scenes,frame,bucket=2.0,supportable=None):
        self.triangles=triangles
        self.owners=owners
        self.closed=closed
        self.source_scenes=source_scenes
        self.supportable=np.ones(len(closed),dtype=bool) if supportable is None else supportable
        self.bucket=bucket
        self.buckets=collections.defaultdict(list)
        self.rays={}
        self.cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        self.norm=np.linalg.norm(self.cross,axis=1)
        self.lo=triangles.min(1);self.hi=triangles.max(1)
        for i in np.flatnonzero(np.all(self.hi[:,[0,2]]>=frame[0],axis=1)&
                               np.all(self.lo[:,[0,2]]<=frame[1],axis=1)):
            low=np.floor(np.maximum(self.lo[i,[0,2]],frame[0])/bucket).astype(int)
            high=np.floor(np.minimum(self.hi[i,[0,2]],frame[1])/bucket).astype(int)
            for bx in range(low[0],high[0]+1):
                for bz in range(low[1],high[1]+1):
                    self.buckets[bx,bz].append(int(i))

    def query(self,lo,hi):
        a=np.floor(np.asarray(lo)[[0,2]]/self.bucket).astype(int)
        b=np.floor(np.asarray(hi)[[0,2]]/self.bucket).astype(int)
        ids=set()
        for x in range(a[0],b[0]+1):
            for z in range(a[1],b[1]+1):ids.update(self.buckets.get((x,z),()))
        ids=np.array(sorted(ids),dtype=int)
        return ids[np.all(self.hi[ids]>=lo,axis=1)&np.all(self.lo[ids]<=hi,axis=1)]

    def ray(self,x,z):
        key=(round(x,8),round(z,8))
        if key not in self.rays:
            ids=self.query([x,-math.inf,z],[x,math.inf,z])
            local,y=ray_hits(self.triangles[ids],x,z)
            self.rays[key]=ids[local],y
        return self.rays[key]

    def supports(self,x,z,scene=None):
        ids,y=self.ray(x,z)
        mask=self.cross[ids,1]>=math.cos(math.radians(35))*self.norm[ids]
        mask &= self.supportable[self.owners[ids]]
        if scene is not None:mask &= self.source_scenes[self.owners[ids]]==scene
        # Identity is retained in the final node's source-triangle references.
        order=np.argsort(y[mask]);ids,y=ids[mask][order],y[mask][order]
        result=[]
        for i,height in zip(ids,y):
            if not result or abs(height-result[-1][0])>0.002:result.append((float(height),int(i)))
        return result

    def clear_box(self,centre,half):
        centre=np.asarray(centre);half=np.asarray(half)
        ids=self.query(centre-half,centre+half)
        if len(triangle_box_overlap(self.triangles[ids],centre,half)):
            return False
        # Surface tests alone miss a body wholly contained by a closed obstacle.
        ids,y=self.ray(centre[0],centre[2])
        for owner in np.unique(self.owners[ids]):
            if not self.closed[owner]:continue
            above=np.sort(y[(self.owners[ids]==owner)&(y>centre[1]+1e-7)])
            unique=[]
            for value in above:
                if not unique or abs(value-unique[-1])>1e-6:unique.append(value)
            if len(unique)%2:return False
        return True

    def supported_edge(self,n,m):
        start=np.array([n['x'],n['y'],n['z']]);end=np.array([m['x'],m['y'],m['z']])
        ids=self.query(np.minimum(start,end)-[.2,.200001,.2],
                       np.maximum(start,end)+[.2,.200001,.2])
        keep=(self.cross[ids,1]>=math.cos(math.radians(35))*self.norm[ids])&self.supportable[self.owners[ids]]
        tr=self.triangles[ids[keep]]
        return all(segment_supported(tr,start+[dx,0,dz],end+[dx,0,dz],.200001)
                   for dx,dz in [(0,0),(-.2,-.2),(-.2,.2),(.2,-.2),(.2,.2)])


def load_geometry(export,plan):
    with zipfile.ZipFile(export) as z:
        report=json.loads(z.read('report.json'))
        player=report['layers'].index('Player')
        mask=report['serialized_layer_collision_matrix'][player]
        selected={d['export_scene'] for d in plan['modes']['day']['scenes'].values()}
        for path,entry in plan['modes']['day']['scenes'].items():
            if report['selected_scenes'].get(entry['export_scene'])!=path:
                raise ValueError('Scene plan differs from selected export: '+path)
        meshes={};shapes={};triangles=[];owners=[];metadata=[];proxies=[]
        for line in z.open('meshes.jsonl'):
            m=json.loads(line);meshes[m['file'],m['path_id']]=(np.array(m['vertices'],float),np.array(m['triangles'],int))
        for line in z.open('colliders.jsonl'):
            c=json.loads(line)
            if c['scene'] not in selected or not(mask>>c['layer']&1) or not(c['active_in_hierarchy'] and c['enabled'] and not c['is_trigger']):continue
            proxy=False
            if c['type']=='MeshCollider':
                if not c['mesh']:continue
                ref=c['mesh'];key=ref['file'],ref['path_id'],c['convex']
                if key not in shapes:
                    v,ids=meshes[key[:2]]
                    if c['convex']:ids=convex_faces(v)
                    shapes[key]=(v,ids,closed_mesh(v,ids))
                v,ids,closed=shapes[key]
            elif c['type']=='BoxCollider':
                v,ids=box_triangles(c);closed=True
            else:
                # Conservative local AABB for the eight capsule components.
                size=np.full(3,2*c['m_Radius'])
                if c['type']=='CapsuleCollider':size[c['m_Direction']]=max(c['m_Height'],2*c['m_Radius'])
                box={'m_Center':c['m_Center'],'m_Size':dict(zip('xyz',size))}
                v,ids=box_triangles(box);closed=True;proxy=True
            tr=transformed_triangles(v,ids,c['world_matrix'])
            if np.linalg.det(np.array(c['world_matrix'])[:3,:3])<0:tr=tr[:,[0,2,1]]
            owner=len(metadata);metadata.append({'scene':c['scene'],'component_path_id':c['component_path_id'],
                                                 'name':c['name'],'closed':closed,'proxy':proxy})
            if proxy:proxies.append(metadata[-1])
            triangles.append(tr);owners.append(np.full(len(tr),owner,dtype=int))
    return np.concatenate(triangles),np.concatenate(owners),metadata,proxies,report


def support_probe(geometry,scene,frame,pitch=0.5,radius=0.25,height=1.8,step=0.3,
                  all_sources=False,height_range=None):
    lo=np.floor(frame[0]/pitch)*pitch;hi=np.ceil(frame[1]/pitch)*pitch
    dims=np.ceil((hi-lo)/pitch).astype(int)
    nodes=[];by_cell=collections.defaultdict(list);rejected=collections.Counter()
    for ix in range(dims[0]):
        for iz in range(dims[1]):
            x,z=lo+(np.array([ix,iz])+0.5)*pitch
            for y,source_triangle in geometry.supports(x,z,None if all_sources else scene):
                if height_range is not None and not height_range[0]<=y<=height_range[1]:continue
                sample_heights=[y]
                for dx,dz in [(-0.2,-0.2),(-0.2,0.2),(0.2,-0.2),(0.2,0.2)]:
                    hits=[h for h,_ in geometry.supports(x+dx,z+dz) if abs(h-y)<=0.2]
                    if not hits:break
                    sample_heights.append(min(hits,key=lambda h:abs(h-y)))
                if len(sample_heights)!=5:
                    rejected['footprint_without_support']+=1;continue
                base=max(sample_heights)+0.03
                if not geometry.clear_box([x,base+height/2,z],[radius,height/2,radius]):
                    rejected['body_intersection_or_inside_closed_obstacle']+=1;continue
                index=len(nodes);by_cell[ix,iz].append(index)
                nodes.append({'x':float(x),'y':y,'z':float(z),'body_base_y':base,'source_triangle':source_triangle,
                              'grid_cell':[ix,iz]})
    edges=[]
    for cell,indices in by_cell.items():
        for delta in [(1,0),(0,1)]:
            for a in indices:
                for b in by_cell.get((cell[0]+delta[0],cell[1]+delta[1]),[]):
                    n,m=nodes[a],nodes[b]
                    if abs(n['y']-m['y'])>step:continue
                    if not geometry.supported_edge(n,m):continue
                    base=max(n['body_base_y'],m['body_base_y'])
                    clear=True
                    for k in (n,m):
                        start=k['body_base_y'];h=height+base-start
                        if not geometry.clear_box([k['x'],start+h/2,k['z']],[radius,h/2,radius]):clear=False;break
                    if not clear:continue
                    centre=[(n['x']+m['x'])/2,base+height/2,(n['z']+m['z'])/2]
                    half=[radius+abs(n['x']-m['x'])/2,height/2,radius+abs(n['z']-m['z'])/2]
                    if geometry.clear_box(centre,half):edges.append([a,b])
    adjacent=collections.defaultdict(list)
    for a,b in edges:adjacent[a].append(b);adjacent[b].append(a)
    remaining=set(range(len(nodes)));components=[]
    while remaining:
        start=min(remaining);remaining.remove(start);todo=[start];component=[]
        while todo:
            n=todo.pop();component.append(n)
            for other in adjacent[n]:
                if other in remaining:remaining.remove(other);todo.append(other)
        components.append(component)
    components.sort(key=len,reverse=True)
    return {'nodes':nodes,'edges':edges,'components':components,'rejected':dict(rejected),
            'grid_origin_xz':lo.tolist(),'grid_dimensions':dims.tolist(),
            'parameters':{'pitch':pitch,'body_square_half_width':radius,'body_height':height,'max_step':step,
                          'footprint_samples':5,'footprint_height_tolerance':0.2,'floor_offset':0.03,
                          'edge_support':'continuous_union_of_triangles_along_five_foot_traces',
                          'support_all_selected_day_scenes':all_sources,'height_range':height_range}}


def attach_sources(profile,geometry,metadata,region_scene):
    """Retain overlapping scene provenance instead of arbitrarily crediting one."""
    for node in profile['nodes']:
        ids,ys=geometry.ray(node['x'],node['z'])
        match=(np.abs(ys-node['y'])<=.002)&geometry.supportable[geometry.owners[ids]]
        match &= geometry.cross[ids,1]>=math.cos(math.radians(35))*geometry.norm[ids]
        owners=sorted(set(int(i) for i in geometry.owners[ids[match]]))
        if not owners:raise ValueError('Previously accepted support has no source')
        preferred=next((i for i in owners if metadata[i]['scene']==region_scene),owners[0])
        node.pop('source_triangle',None)
        node['source']=metadata[preferred]
        if len(owners)>1:node['coincident_sources']=[metadata[i] for i in owners]
    profile['source_provenance_revision']=2


def run(export,plan_path,output,pitch=0.5,height=1.8):
    validation=validate(export)
    plan=json.loads(plan_path.read_text())
    tri,owners,meta,proxies,report=load_geometry(export,plan)
    result={'schema_version':1,'archive_sha256':validation['archive_sha256'],'profiles':{},
            'evidence':'geometric_support_and_swept_box_model_not_runtime_navigation',
            'mode':'day','numpy_version':np.__version__,'scipy_version':scipy.__version__,
            'collision_layers':[name for i,name in enumerate(report['layers']) if
                                report['serialized_layer_collision_matrix'][report['layers'].index('Player')]>>i&1],
            'limits':['Geometric swept-box model, not Unity/BN runtime movement',
                      'Body dimensions and step are provisional Unity-unit parameters',
                      'Convex meshes use mathematical vertex hulls; PhysX cooking remains unverified',
                      'Open meshes have surface checks only; no invented infinite solid intervals',
                      'Serialized door states and missing active scenes remain unverified',
                      'A support candidate can be a roof, table or isolated ledge'],
            'conservative_shape_proxies':proxies}
    scenes=np.array([m['scene'] for m in meta]);closed=np.array([m['closed'] for m in meta])
    for name,stem in [('office','Factory_Rework_Admin_Office'),('laboratory','Factory_Rework_Laboratory')]:
        scene=next(s for s,path in report['selected_scenes'].items() if Path(path).stem==stem)
        target=tri[scenes[owners]==scene].reshape(-1,3)
        frame=np.array([target[:,[0,2]].min(0)-0.5,target[:,[0,2]].max(0)+0.5])
        geometry=SceneGeometry(tri,owners,closed,scenes,frame+np.array([[-1,-1],[1,1]]),
                               supportable=np.array([not m['proxy'] for m in meta]))
        print('Probing',name,flush=True)
        profile=support_probe(geometry,scene,frame,pitch=pitch,height=height,all_sources=True,
                              height_range=[float(target[:,1].min())-0.5,float(target[:,1].max())+0.5])
        profile['scene']=scene
        attach_sources(profile,geometry,meta,scene)
        result['profiles'][name]=profile
        print(name,'nodes',len(profile['nodes']),'edges',len(profile['edges']),
              'components',[len(c) for c in profile['components'][:8]],flush=True)
    output.mkdir(parents=True,exist_ok=False)
    (output/'support_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('export',type=Path)
    p.add_argument('--scene-plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pitch',type=float,default=0.5)
    p.add_argument('--body-height',type=float,default=1.8)
    a=p.parse_args()
    if not np.isfinite([a.pitch,a.body_height]).all() or a.pitch<=0 or a.body_height<=0:
        p.error('Pitch and body height must be positive and finite')
    run(a.export,a.scene_plan,a.output,a.pitch,a.body_height)
