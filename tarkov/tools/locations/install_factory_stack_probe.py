"""Install an isolated four-level Factory probe into a disposable pinned BN checkout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from check_factory_stack import reconstruct
from build_factory_stack import ROOT, MOD, OUT, load
from install_native_probe import BN_SHA

CASE = 'factory stack generates matching levels and paired stairs'


def fixture():
    manifest = load(OUT/'stack_manifest.json')
    grids,palette = reconstruct(manifest,load(MOD/'mapgen.json'))
    report = load(OUT/'stack_static_report.json')
    w,h = manifest['size']
    out = ['// Generated from committed four-level Factory JSON; test-only.',
           f'constexpr auto stack_width = {w};', f'constexpr auto stack_height = {h};',
           f'constexpr auto stack_levels = {len(grids)};',
           'constexpr auto stack_rows = std::array<std::string_view, stack_levels * stack_height>{']
    for _,rows in sorted(grids.items()):
        out.extend(f'    {json.dumps(row)},' for row in rows)
    out += ['};','auto stack_terrain(const char symbol) -> std::string_view {','    switch (symbol) {']
    out.extend(f"        case '{c}': return {json.dumps(t)};" for c,t in sorted(palette.items()))
    out += ['        default: return "";','    }','}',
            f'constexpr auto stack_expected_main_size = {report["main_size"]};',
            'const auto stack_anchor = tripoint('+','.join(map(str,report['anchor'][:2]+[report['anchor'][2]+1]))+');']
    return '\n'.join(out)+'\n'


def install(bn):
    if subprocess.check_output(['git','-C',str(bn),'rev-parse','HEAD'],text=True).strip()!=BN_SHA:
        raise ValueError('Wrong BN base')
    targets = [bn/'data/mods/trkv_factory_stack_dev',bn/'tests/trkv_factory_stack_constructor_test.cpp',
               bn/'tests/trkv_factory_stack_fixture.inc']
    for path in targets:
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite {path}')
    header = fixture()
    source = (ROOT/'tests/locations/bn_factory_stack_probe.cpp.inc').read_text(encoding='utf-8')
    created = []
    try:
        created.append(targets[0]);shutil.copytree(MOD,targets[0])
        for path,content in [(targets[1],source),(targets[2],header)]:
            created.append(path);path.write_text(content,encoding='utf-8')
    except BaseException:
        for path in reversed(created):
            if path.is_dir():shutil.rmtree(path)
            elif path.exists():path.unlink()
        raise
    return targets


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bn',type=Path)
    for target in install(p.parse_args().bn.resolve()):print(target)
