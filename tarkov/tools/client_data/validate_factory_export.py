#!/usr/bin/env python3
"""Validate an exported collider ZIP, without UnityPy or the game installation."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(value):
    require(isinstance(value,str) and re.fullmatch(r'-?\d+',value), 'Object ID must be a decimal string')
    require(-(2**63)<=int(value)<2**63,'Object ID outside signed 64-bit range')
    return value


def finite(values):
    return all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values)


def validate(path, baseline=None):
    with zipfile.ZipFile(path) as archive:
        expected={'report.json','colliders.jsonl','meshes.jsonl'}
        require(len(archive.namelist())==3 and set(archive.namelist())==expected,'Unexpected/duplicate ZIP members')
        require(archive.testzip() is None,'ZIP CRC mismatch')
        report=json.loads(archive.read('report.json'))
        require(report['schema_version']==1,'Unsupported export schema')
        require(report['complete_for_selected_serialized_colliders'] is True and not report['issues'],
                'Export is partial or reports unresolved data')
        require(report['selected_scenes'] and set(report['scene_counts'])==set(report['selected_scenes']),
                'Selected scene is missing')
        mesh_lengths={}
        vertices=triangles=0
        with archive.open('meshes.jsonl') as stream:
            for line in stream:
                mesh=json.loads(line)
                key=(mesh['file'],identity(mesh['path_id']))
                require(key not in mesh_lengths,'Duplicate Mesh identity')
                vs,ts=mesh['vertices'],mesh['triangles']
                require(vs and ts,'Empty Mesh')
                require(all(len(v)==3 and finite(v) for v in vs),'Invalid/non-finite Mesh vertex')
                require(all(len(t)==3 and all(type(i) is int and 0<=i<len(vs) for i in t) for t in ts),
                        'Mesh triangle index out of range')
                mesh_lengths[key]=len(vs)
                vertices+=len(vs)
                triangles+=len(ts)
        require((len(mesh_lengths),vertices,triangles)==
                (report['mesh_counts']['decoded'],report['mesh_counts']['vertices'],report['mesh_counts']['triangles']),
                'Mesh totals disagree with report')
        scene_counts=collections.Counter()
        eligible=collections.Counter()
        primitive=collections.Counter()
        collider_ids=set()
        references=null_meshes=0
        with archive.open('colliders.jsonl') as stream:
            for line in stream:
                c=json.loads(line)
                key=(c['scene'],identity(c['component_path_id']))
                identity(c['gameobject_path_id'])
                require(key not in collider_ids,'Duplicate collider identity')
                collider_ids.add(key)
                require(c['scene'] in report['selected_scenes'],'Unknown collider scene')
                scene_counts[c['scene']]+=1
                mat=c['world_matrix']
                require(len(mat)==4 and all(len(row)==4 and finite(row) for row in mat) and mat[3]==[0,0,0,1],
                        'Invalid world transform')
                require(type(c['layer']) is int and 0<=c['layer']<32,'Invalid layer')
                require(all(type(c[k]) is bool for k in ('active_in_hierarchy','enabled','is_trigger')),'Invalid state flags')
                if c['type']=='MeshCollider':
                    require(not c.get('mesh_reference_error'),'Unresolved Mesh reference error')
                    if c['mesh'] is not None:
                        ref=c['mesh']
                        require((ref['file'],identity(ref['path_id'])) in mesh_lengths,'Unresolved Mesh reference')
                        references+=1
                    else:
                        null_meshes+=1
                else:
                    require(c['type'] in ('BoxCollider','SphereCollider','CapsuleCollider'),'Unknown primitive collider')
                    primitive[c['type']]+=1
                    for field in ('m_Center','m_Size'):
                        if field in c:
                            require(set(c[field])==set('xyz') and finite(c[field].values()),'Invalid primitive vector')
                    for field in ('m_Radius','m_Height','m_Direction'):
                        if field in c:
                            require(finite([c[field]]),'Invalid primitive scalar')
                if c['active_in_hierarchy'] and c['enabled'] and not c['is_trigger']:
                    eligible[str(c['layer'])+':'+c['type']]+=1
        require(all(scene_counts[s]==v['colliders'] for s,v in report['scene_counts'].items()),
                'Collider totals disagree with report')
        matched=0
        if baseline:
            for name,meta in baseline['files'].items():
                require(report['source_files'].get(name)==meta,'Client source differs from baseline: '+name)
                matched+=1
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):
            h.update(block)
    return {'schema_version':1,'evidence':'serialized_export_integrity_not_runtime_navigation',
            'archive_sha256':h.hexdigest(),'scenes':len(scene_counts),'colliders':sum(scene_counts.values()),
            'resolved_mesh_references':references,'null_mesh_components':null_meshes,
            'unique_meshes':len(mesh_lengths),'vertices':vertices,'triangles':triangles,
            'primitive_colliders':dict(primitive),'eligible_by_layer_and_type':dict(eligible),
            'prior_source_hashes_matched':matched,
            'limits':['Does not prove custom behaviour, runtime activation or door states',
                      'Completeness concerns the explicitly selected scenes only',
                      'Day/night scenes must not be blindly overlaid for gameplay']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('zip',type=Path)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=validate(args.zip,json.loads(args.baseline.read_text()) if args.baseline else None)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(args.output)
