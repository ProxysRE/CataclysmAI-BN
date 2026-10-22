#!/usr/bin/env python3
"""Update only generated geometry-preview sections in the existing engine patch."""
import argparse,difflib,hashlib,re,subprocess,tempfile
from pathlib import Path
from prepare_geometry_preview import ROOT,FILES,TEST,prepare


def prepare_patch(check=False):
    prepare(check=True)
    patch_path=ROOT/'artisan_engine.patch'
    before=patch_path.read_text(encoding='utf-8');patch=before
    mapping=dict(FILES)
    mapping['tests/'+TEST]='native/'+TEST
    selected=''
    for target,source in mapping.items():
        marker='--- /dev/null\n+++ b/'+target+'\n'
        assert patch.count(marker)==1,('Expected one generated new-file section',target)
        start=patch.index(marker);end=patch.find('\n--- ',start+len(marker))
        end=len(patch)if end<0 else end+1
        section=''.join(difflib.unified_diff([], (ROOT/source).read_text(encoding='utf-8').splitlines(keepends=True),'/dev/null','b/'+target))
        patch=patch[:start]+section+patch[end:];selected+=section
    def sections(text):
        return {part.split('\n',2)[1]:part for part in re.split(r'(?m)(?=^--- )',text)if part}
    a,b=sections(before),sections(patch)
    assert set(a)==set(b)
    changed={key for key in a if a[key]!=b[key]}
    assert changed<={'+++ b/'+target for target in mapping},changed
    # Applying the new-file diffs independently checks their syntax and exact
    # bytes, without requiring a mutable checkout of the full pinned BN engine.
    with tempfile.TemporaryDirectory()as directory:
        subprocess.run(['git','apply','--check','-'],input=selected,text=True,cwd=directory,check=True)
        subprocess.run(['git','apply','-'],input=selected,text=True,cwd=directory,check=True)
        for target,source in mapping.items():
            assert (Path(directory)/target).read_bytes()==(ROOT/source).read_bytes(),target
    digest=hashlib.sha256(patch.encode('utf-8')).hexdigest()
    workflow=ROOT.parent/'.github/workflows/build-dda-npc-engine.yml'
    old=workflow.read_text(encoding='utf-8')
    new,n=re.subn(r'(Get-FileHash \$patch -Algorithm SHA256\)\.Hash\.ToLower\(\) -ne ")[a-f0-9]{64}',lambda m:m[1]+digest,old)
    assert n==1,'Expected one native patch checksum'
    if check:
        assert patch==before,'Generated geometry patch is stale'
        assert new==old,'Native workflow patch checksum is stale'
    else:
        patch_path.write_text(patch,encoding='utf-8',newline='\n')
        workflow.write_text(new,encoding='utf-8',newline='\n')
    print(f'PASS: geometry patch sections apply exactly; {len(changed)} sections changed; other engine sections preserved; SHA256 {digest}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');prepare_patch(parser.parse_args().check)
