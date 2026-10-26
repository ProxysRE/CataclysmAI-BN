#!/usr/bin/env python3
"""Read a selected client ZIP without executing scripts or changing its files.

Requires UnityPy==1.25.4. Reports geometry availability, not BN walkability.
Only standard engine components are parsed; custom behaviours remain unknown.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import zipfile


def multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4))
             for j in range(4)] for i in range(4)]


def local_matrix(t):
    q = t['m_LocalRotation']
    x, y, z, w = (q[k] for k in ('x', 'y', 'z', 'w'))
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or abs(norm - 1) > 0.001:
        raise ValueError('Invalid/non-unit transform rotation')
    x, y, z, w = (v / norm for v in (x, y, z, w))
    r = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    s, p = t['m_LocalScale'], t['m_LocalPosition']
    return [[r[i][j] * s[k] for j, k in enumerate(('x','y','z'))] + [p[axis]]
            for i, axis in enumerate(('x','y','z'))] + [[0,0,0,1]]


def transform_point(m, p):
    return [sum(m[i][j]*p[j] for j in range(3)) + m[i][3] for i in range(3)]


def hierarchy(transforms, objects):
    cache, visiting = {}, set()

    def world(pid):
        if pid in cache:
            return cache[pid]
        if pid in visiting:
            raise ValueError('Transform parent cycle')
        visiting.add(pid)
        t = transforms[pid]
        go = t['m_GameObject']
        if go['m_FileID'] != 0:
            raise ValueError('External GameObject not resolved')
        active = objects[go['m_PathID']]['m_IsActive']
        mat = local_matrix(t)
        parent = t['m_Father']
        if parent['m_FileID'] != 0:
            raise ValueError('External parent not resolved')
        if parent['m_PathID']:
            pm, pa = world(parent['m_PathID'])
            mat, active = multiply(pm, mat), active and pa
        visiting.remove(pid)
        cache[pid] = mat, active
        return cache[pid]

    for pid in transforms:
        world(pid)
    return cache


def audit(source):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    if UnityPy.__version__ != '1.25.4':
        raise RuntimeError('Use UnityPy==1.25.4 for reproducible parsing')
    archive = zipfile.ZipFile(source)
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError('Duplicate ZIP entries')
    environments, provenance, meshes, mesh_stats = {}, {}, {}, {}
    for name in names:
        if '/' in name or '\\' in name:
            raise ValueError('Expected flat ZIP of selected level/sharedassets files')
        if not (name.startswith('level') or
                (name.startswith('sharedassets') and name.endswith('.assets'))):
            raise ValueError('Unexpected selected file: ' + name)
        raw = archive.read(name)
        environments[name] = UnityPy.load(raw)
        provenance[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        stats = collections.Counter()
        for obj in environments[name].objects:
            if obj.type.name != 'Mesh':
                continue
            data = obj.parse_as_dict()
            streamed = bool(data.get('m_StreamData', {}).get('path'))
            mesh = {'name': data['m_Name'], 'streamed': streamed}
            stats['meshes'] += 1
            if streamed:
                stats['meshes_with_external_vertex_stream'] += 1
            else:
                handler = MeshHandler(obj.parse_as_object())
                handler.process()
                vertices = handler.m_Vertices or []
                triangles = [tri for sub in handler.get_triangles() for tri in sub]
                if any(len(t) != 3 or min(t) < 0 or max(t) >= len(vertices) for t in triangles):
                    raise ValueError('Invalid mesh triangle indices')
                stats['decoded_inline_meshes'] += 1
                stats['decoded_vertices'] += len(vertices)
                stats['decoded_triangles'] += len(triangles)
                mesh['triangles'] = len(triangles)
            meshes[name, obj.path_id] = mesh
        if stats:
            mesh_stats[name] = dict(stats)
    scenes = {}
    for name, env in environments.items():
        if not name.startswith('level'):
            continue
        objects, transforms, colliders = {}, {}, []
        types = collections.Counter(o.type.name for o in env.objects)
        for obj in env.objects:
            typ = obj.type.name
            if typ not in ('GameObject','Transform','BoxCollider','MeshCollider','CapsuleCollider','SphereCollider'):
                continue
            data = obj.parse_as_dict()
            if typ == 'GameObject':
                objects[obj.path_id] = data
            elif typ == 'Transform':
                transforms[obj.path_id] = data
            else:
                colliders.append((obj.path_id, typ, data, obj.assets_file))
        worlds = hierarchy(transforms, objects)
        go_transforms = {t['m_GameObject']['m_PathID']: pid for pid,t in transforms.items()}
        states, dependencies = collections.Counter(), collections.Counter()
        examples = []
        for pid, typ, c, asset in colliders:
            gid = c['m_GameObject']['m_PathID']
            if c['m_GameObject']['m_FileID'] != 0:
                raise ValueError('External collider GameObject')
            mat, active = worlds[go_transforms[gid]]
            eligible = active and c['m_Enabled'] and not c['m_IsTrigger']
            states[typ + ':total'] += 1
            states[typ + ':active_enabled_nontrigger'] += bool(eligible)
            if typ == 'MeshCollider':
                ref = c['m_Mesh']
                fileid = ref['m_FileID']
                target = asset.externals[fileid-1].path if fileid else name
                mesh = meshes.get((target, ref['m_PathID']))
                status = ('null_reference' if not ref['m_PathID'] else
                          'missing_mesh_file_or_object' if mesh is None else
                          'missing_vertex_stream' if mesh['streamed'] else 'decoded_inline')
                states['mesh_reference:' + status] += 1
                if eligible:
                    states['eligible_mesh_reference:' + status] += 1
                    dependencies[target] += 1
            go = objects[gid]
            if eligible and len(examples) < 12 and any(k in go['m_Name'].lower() for k in ('stair','ladder')):
                examples.append({'object':go['m_Name'],'component_path_id':pid,
                                 'type':typ,'transform_origin_unity_xyz':transform_point(mat,[0,0,0])})
        scenes[name] = {'object_types':dict(types), 'world_transforms_resolved':len(worlds),
                        'active_gameobjects':sum(a for _,a in worlds.values()),
                        'colliders':dict(states),
                        'eligible_mesh_references_by_file':dict(dependencies.most_common()),
                        'stair_name_examples_not_validated_routes':examples}
    return {'schema_version':1,'parser':'UnityPy==1.25.4','files':provenance,
            'scenes':scenes,'mesh_files':mesh_stats,
            'limits':['Only selected scenes; no complete Factory reconstruction',
                      'Custom MonoBehaviours not decoded',
                      'Active/enabled/nontrigger is not a player collision-layer test',
                      'No door state, runtime activation, navigation or BN grid conversion',
                      'Transform origins are not floor heights or collider centres']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    result = audit(args.zip)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,ensure_ascii=False,indent=2)
        out.write('\n')
    print(args.output)
