"""Run a supplied pinned BN executable with this isolated mod and temporary user data.

Refuses to overwrite an installed mod. Does not create or edit a user save.
The executable's provenance must be established by its build pipeline; checking
source HEAD alone cannot establish that an arbitrary executable matches it.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
BN_SHA='554950f3635f50ddd1d32c6e1b6e2bdee9842bd6'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn', type=Path, required=True)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--log', type=Path, required=True)
    a=p.parse_args()
    bn, exe=a.bn.resolve(), a.exe.resolve()
    assert exe.is_file(), exe
    assert subprocess.check_output(['git','-C',str(bn),'rev-parse','HEAD'],text=True).strip()==BN_SHA
    target=bn/'data/mods/trkv_locations_dev'
    if target.exists():
        raise SystemExit(f'Refusing to overwrite installed mod: {target}')
    # Copies and removal apply only to the newly created mod directory.
    shutil.copytree(ROOT/'mods/trkv_locations_dev',target)
    try:
        with tempfile.TemporaryDirectory(prefix='trkv-location-check-') as user:
            result=subprocess.run([str(exe),'--userdir',user,'--check-mods','trkv_locations_dev'],
                                  cwd=bn,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding='utf-8',errors='replace',timeout=300)
            a.log.write_text(result.stdout,encoding='utf-8')
            result.check_returncode()
            print('BN --check-mods completed; this does not prove generation or gameplay.')
    finally:
        shutil.rmtree(target)


if __name__=='__main__':
    main()
