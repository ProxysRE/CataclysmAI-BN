"""Install the isolated Factory generation probe into an exact disposable BN checkout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from check_factory import reconstruct, load, OUT, MOD, ROOT
from install_native_probe import BN_SHA

CASE = 'factory ground draft generates matching BN tiles'


def fixture():
    manifest = load(OUT/'ground_manifest.json')
    rows, terrain = reconstruct(manifest, load(MOD/'mapgen.json'))
    w, h = manifest['size']
    result = ['// Generated from committed Factory JSON; test-only.',
              f'constexpr auto factory_width = {w};', f'constexpr auto factory_height = {h};',
              f'constexpr auto factory_rows = std::array<std::string_view, {h}>{{']
    result.extend(f'    {json.dumps(row)},' for row in rows)
    result += ['};', 'auto factory_terrain(const char symbol) -> std::string_view {', '    switch (symbol) {']
    result.extend(f"        case '{c}': return {json.dumps(t)};" for c, t in sorted(terrain.items()))
    result += ['        default: return "";', '    }', '}']
    return '\n'.join(result)+'\n'


def install(bn):
    if subprocess.check_output(['git', '-C', str(bn), 'rev-parse', 'HEAD'], text=True).strip() != BN_SHA:
        raise ValueError('Wrong BN base')
    targets = [bn/'data/mods/trkv_factory_dev', bn/'tests/trkv_factory_constructor_test.cpp',
               bn/'tests/trkv_factory_fixture.inc']
    for path in targets:
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite {path}')
    header = fixture()
    source = (ROOT/'tests/locations/bn_factory_probe.cpp.inc').read_text(encoding='utf-8')
    created = []
    try:
        created.append(targets[0])
        shutil.copytree(MOD, targets[0])
        for path, content in [(targets[1], source), (targets[2], header)]:
            created.append(path)
            path.write_text(content, encoding='utf-8')
    except BaseException:
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        raise
    return targets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bn', type=Path)
    for target in install(parser.parse_args().bn.resolve()):
        print(target)
