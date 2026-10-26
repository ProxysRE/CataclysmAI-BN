#!/usr/bin/env python3
"""Export serialized Factory collider geometry. Read-only, offline, no game process.

Install UnityPy==1.25.4. Use the directory containing this file together with
audit_factory_scenes.py. Output deliberately excludes textures/audio/game code.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

from audit_factory_scenes import hierarchy


def data_directory(root):
    root = Path(root).resolve()
    data = root if root.name == 'EscapeFromTarkov_Data' else root/'EscapeFromTarkov_Data'
    if not (data/'globalgamemanagers').is_file():
        raise ValueError('globalgamemanagers not found in the selected game Data directory')
    return data


def factory_scenes(settings):
    selected = [(f'level{i}', scene) for i,scene in enumerate(settings['scenes'])
                if '/factory_rework/' in scene.replace('\\','/').lower()]
    if not selected:
        raise ValueError('No Factory_Rework scenes in this build; no scene numbers guessed')
    return selected


def mesh_reference(asset_name, externals, pointer):
    pid, fid = pointer['m_PathID'], pointer['m_FileID']
    if not pid:
        return None
    if fid < 0 or fid > len(externals):
        raise ValueError('Mesh external file index out of range')
    name = externals[fid-1] if fid else asset_name
    if name != 'Library/unity default resources' and not re.fullmatch(
            r'(?:level\d+|sharedassets\d+\.assets|resources\.assets|globalgamemanagers\.assets)',name):
        raise ValueError('Unsupported/builtin mesh file reference: ' + name)
    return name, pid


def write_line(stream, record):
    stream.write((json.dumps(record,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8'))


def export(root, output):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    if UnityPy.__version__ != '1.25.4':
        raise RuntimeError('Install UnityPy==1.25.4')
    data = data_directory(root)
    source_files, issues, requests = {}, [], collections.defaultdict(set)
    scene_counts, mesh_counts = {}, collections.Counter()

    def source(name):
        relative = 'Resources/unity default resources' if name=='Library/unity default resources' else name
        path = data/relative
        if not path.resolve().is_relative_to(data):
            raise ValueError('Source escapes selected Data directory: ' + name)
        if name not in source_files:
            h = hashlib.sha256()
            with path.open('rb') as file:
                while chunk := file.read(1024*1024):
                    h.update(chunk)
            source_files[name] = {'bytes':path.stat().st_size,'sha256':h.hexdigest()}
        return path

    managers = UnityPy.load(str(source('globalgamemanagers')))
    settings = next(o.parse_as_dict() for o in managers.objects if o.type.name=='BuildSettings')
    layers = next(o.parse_as_dict()['layers'] for o in managers.objects if o.type.name=='TagManager')
    physics = next(o.parse_as_dict() for o in managers.objects if o.type.name=='PhysicsManager')
    scenes = factory_scenes(settings)
    del managers
    # ZIP mode x preserves any previous export. A failed write remains visibly partial.
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        with archive.open('colliders.jsonl','w') as stream:
            for name, scene_path in scenes:
                print('Scene:',name,scene_path.rsplit('/',1)[-1],flush=True)
                try:
                    env = UnityPy.load(str(source(name)))
                    gos, ts, colliders = {}, {}, []
                    for obj in env.objects:
                        typ = obj.type.name
                        if typ not in ('GameObject','Transform','MeshCollider','BoxCollider','CapsuleCollider','SphereCollider'):
                            continue
                        d = obj.parse_as_dict()
                        if typ=='GameObject':
                            gos[obj.path_id] = d
                        elif typ=='Transform':
                            ts[obj.path_id] = d
                        else:
                            colliders.append((obj.path_id,typ,d,obj.assets_file))
                    worlds = hierarchy(ts,gos)
                    go_ts = {t['m_GameObject']['m_PathID']:pid for pid,t in ts.items()}
                    rows = []
                    for pid,typ,d,asset in colliders:
                        go_ref = d['m_GameObject']
                        if go_ref['m_FileID']:
                            raise ValueError('External collider GameObject not resolved')
                        gid = go_ref['m_PathID']
                        g = gos[gid]
                        matrix,active = worlds[go_ts[gid]]
                        if any(not math.isfinite(v) for row in matrix for v in row):
                            raise ValueError('Non-finite world matrix')
                        row = {'scene':name,'component_path_id':str(pid),'gameobject_path_id':str(gid),
                               'name':g['m_Name'],'layer':g['m_Layer'],'type':typ,
                               'active_in_hierarchy':bool(active),'enabled':bool(d['m_Enabled']),
                               'is_trigger':bool(d['m_IsTrigger']),'world_matrix':matrix}
                        if typ=='MeshCollider':
                            try:
                                ref = mesh_reference(name,[e.path for e in asset.externals],d['m_Mesh'])
                            except ValueError as exc:
                                ref = None
                                row['mesh_reference_error'] = str(exc)
                                issues.append({'scene':name,'component_path_id':str(pid),'error':str(exc)})
                            row['mesh'] = {'file':ref[0],'path_id':str(ref[1])} if ref else None
                            row['convex'] = bool(d['m_Convex'])
                            if ref:
                                requests[ref[0]].add(ref[1])
                        else:
                            for field in ('m_Center','m_Size','m_Radius','m_Height','m_Direction'):
                                if field in d:
                                    row[field] = d[field]
                        rows.append(row)
                    for row in rows:
                        write_line(stream,row)
                    scene_counts[name] = {'gameobjects':len(gos),'colliders':len(rows)}
                except Exception as exc:
                    issues.append({'scene':name,'error':type(exc).__name__+': '+str(exc)})
        with archive.open('meshes.jsonl','w') as stream:
            for name, ids in sorted(requests.items()):
                print('Mesh file:',name,'objects:',len(ids),flush=True)
                try:
                    env = UnityPy.load(str(source(name)))
                    objects = {o.path_id:o for o in env.objects}
                except Exception as exc:
                    issues.append({'mesh_file':name,'requested_objects':len(ids),'error':type(exc).__name__+': '+str(exc)})
                    mesh_counts['unresolved'] += len(ids)
                    continue
                for pid in sorted(ids):
                    try:
                        obj = objects[pid]
                        if obj.type.name != 'Mesh':
                            raise ValueError('Reference does not identify a Mesh')
                        mesh = obj.parse_as_object()
                        resource = mesh.m_StreamData.path if mesh.m_StreamData else ''
                        if resource:
                            if not re.fullmatch(r'(?:sharedassets\d+\.assets|resources\.assets|globalgamemanagers\.assets|level\d+)\.resS',resource):
                                raise ValueError('Unsupported mesh stream path: '+resource)
                            source(resource)
                        handler = MeshHandler(mesh)
                        handler.process()
                        vertices = handler.m_Vertices or []
                        triangles = [t for sub in handler.get_triangles() for t in sub]
                        if not vertices or not triangles:
                            raise ValueError('Empty mesh geometry')
                        if any(len(t)!=3 or min(t)<0 or max(t)>=len(vertices) for t in triangles):
                            raise ValueError('Invalid triangle indices')
                        write_line(stream,{'file':name,'path_id':str(pid),'name':mesh.m_Name,
                                           'vertices':vertices,'triangles':triangles})
                        mesh_counts['decoded'] += 1
                        mesh_counts['vertices'] += len(vertices)
                        mesh_counts['triangles'] += len(triangles)
                    except Exception as exc:
                        mesh_counts['unresolved'] += 1
                        issues.append({'mesh_file':name,'path_id':str(pid),'error':type(exc).__name__+': '+str(exc)})
        report = {'schema_version':1,'purpose':'serialized_factory_colliders_not_runtime_navigation',
                  'parser':'UnityPy==1.25.4','unity_version':settings['m_Version'],
                  'selected_scenes':dict(scenes),'scene_counts':scene_counts,'mesh_counts':dict(mesh_counts),
                  'layers':layers,'serialized_layer_collision_matrix':physics['m_LayerCollisionMatrix'],
                  'source_files':source_files,'issues':issues,
                  'complete_for_selected_serialized_colliders':len(scene_counts)==len(scenes) and not issues,
                  'limits':['Includes disabled/inactive/trigger components with explicit flags',
                            'Custom behaviours, runtime door states and activation are not evaluated',
                            'Does not execute game code or attach to its process',
                            'No textures, audio, DLLs, account data or unrelated folders exported',
                            'World matrices are serialized transforms, not measured PhysX collider behaviour',
                            'Path IDs are strings to preserve 64-bit identity in JSON readers']}
        archive.writestr('report.json',json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--output',type=Path,default=Path('factory_collision_export.zip'))
    args = parser.parse_args()
    result = export(args.root,args.output)
    print('Output:',args.output)
    print('Scenes:',len(result['scene_counts']),'/',len(result['selected_scenes']))
    print('Meshes:',result['mesh_counts'])
    print('Issues:',len(result['issues']),'(see report.json inside the ZIP)')
