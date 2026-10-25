"""Read-only inventory of an installed Tarkov data folder; Python standard library.

Does not launch/inject into the game, unpack assets, read account files, or
upload anything. Output contains relative paths, sizes and bundle header versions.
"""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import struct


def bundle_header(data):
    signature,sep,tail=data.partition(b'\0')
    if not sep or signature not in (b'UnityFS',b'UnityWeb',b'UnityRaw') or len(tail)<4:
        return None
    version=struct.unpack('>I',tail[:4])[0]
    strings=tail[4:].split(b'\0',2)
    return {'signature':signature.decode('ascii'),'format':version,
            'unity_version':strings[0].decode('ascii',errors='replace'),
            'revision':strings[1].decode('ascii',errors='replace') if len(strings)>1 else ''}


def inventory(root):
    root=Path(root).resolve()
    data=root if root.name.lower()=='escapefromtarkov_data' else root/'EscapeFromTarkov_Data'
    if not data.is_dir():
        raise ValueError('EscapeFromTarkov_Data not found; choose the installed game folder')
    entries,errors=[],[]
    for directory,dirs,files in os.walk(data,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not (Path(directory)/d).is_symlink()
                       and not getattr(Path(directory)/d,'is_junction',lambda:False)())
        for name in sorted(files):
            path=Path(directory)/name
            if path.is_symlink():continue
            relative=path.relative_to(data).as_posix()
            suffix=path.suffix.lower()
            # Inventory scene/resource containers and manifests, never Managed DLLs,
            # launcher profiles, account settings, logs, saves or arbitrary files.
            top_level=path.parent==data
            selected=(suffix=='.bundle' or
                      ('streamingassets/' in relative.lower() and suffix in ('.json','.manifest')) or
                      (top_level and (name.lower().startswith(('level','sharedassets','globalgamemanagers','resources.assets')))))
            if not selected:continue
            try:
                row={'path':relative,'bytes':path.stat().st_size}
                if suffix=='.bundle':
                    with path.open('rb') as stream: header=bundle_header(stream.read(256))
                    row['bundle_header']=header
                entries.append(row)
            except OSError as exc:
                errors.append({'path':relative,'error':type(exc).__name__,'errno':exc.errno})
    return {'schema_version':1,'purpose':'local_container_inventory_not_extracted_geometry',
            'root_label':'EscapeFromTarkov_Data','file_count':len(entries),
            'total_selected_bytes':sum(r['bytes'] for r in entries),
            'unity_versions':dict(Counter(r['bundle_header']['unity_version'] for r in entries if r.get('bundle_header'))),
            'factory_name_matches':[r['path'] for r in entries if 'factory' in r['path'].lower()],
            'files':entries,'errors':errors,
            'limits':['A filename hit does not establish a complete Factory dependency set',
                      'Scene hierarchy, transforms, colliders and runtime states are not extracted']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_folder',type=Path)
    parser.add_argument('--output',type=Path,default=Path('tarkov_client_inventory.json.gz'))
    args=parser.parse_args()
    result=inventory(args.game_folder)
    # Exclusive create: never replace an earlier inventory or a game file.
    with args.output.open('xb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed:
            compressed.write((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(f"Files: {result['file_count']}; Factory name matches: {len(result['factory_name_matches'])}")
    print(f"Saved: {args.output.resolve()}")


if __name__=='__main__':main()
