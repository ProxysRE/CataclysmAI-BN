"""Install constructor-only tests into a disposable, exact BN checkout.

Does not edit any existing source or project core. Run CMake configure AFTER
installation: BN discovers tests/*.cpp at configure time.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BN_SHA = '554950f3635f50ddd1d32c6e1b6e2bdee9842bd6'


def fixture():
    manifest = json.loads((ROOT/'locations/industrial_01/manifest.json').read_text(encoding='utf-8'))
    maps = json.loads((ROOT/'mods/trkv_locations_dev/mapgen.json').read_text(encoding='utf-8'))
    tiles = {m['om_terrain'][0]: m['object'] for m in maps}
    rows = [['?'] * 72 for _ in range(72)]
    terrain, furniture = {}, {}
    for block in manifest['blocks']:
        obj = tiles[block['terrain_id']]
        ox, oy, _ = block['origin']
        for y, row in enumerate(obj['rows']):
            rows[oy+y][ox:ox+24] = row
        for category, dest in [('terrain', terrain), ('furniture', furniture)]:
            for c, ident in obj.get(category, {}).items():
                if c in dest and dest[c] != ident:
                    raise ValueError(f'Inconsistent fixture symbol {c}')
                dest[c] = ident
    out = ['// Generated from the committed mapgen. No gameplay behavior is mocked.',
           'constexpr auto fixture_rows = std::array<std::string_view, 72>{']
    out.extend(f'    {json.dumps("".join(row))},' for row in rows)
    out.append('};')
    for name, mapping, default in [('terrain',terrain,''),('furniture',furniture,'f_null')]:
        out += [f'auto fixture_{name}(const char symbol) -> std::string_view {{', '    switch (symbol) {']
        out.extend(f"        case '{c}': return {json.dumps(v)};" for c,v in sorted(mapping.items()))
        out += [f'        default: return {json.dumps(default)};', '    }', '}']
    points = {
        'entries': [p for s in manifest['spawn_areas'] for p in s['primary']+s['fallback']],
        'exits': [s['area']['min'] for s in manifest['extraction_areas']],
        'pois': [p['position'] for p in manifest['pois']],
    }
    for name, coords in points.items():
        out += [f'const auto fixture_{name} = std::array<point, {len(coords)}>{{',
                *[f'    point({x}, {y}),' for x,y,_ in coords], '};']
    return '\n'.join(out)+'\n'


def install(bn):
    sha = subprocess.check_output(['git','-C',str(bn),'rev-parse','HEAD'],text=True).strip()
    if sha != BN_SHA:
        raise ValueError(f'Wrong BN base: {sha}')
    targets = [bn/'data/mods/trkv_locations_dev', bn/'tests/trkv_location_constructor_test.cpp',
               bn/'tests/trkv_location_fixture.inc']
    for path in targets:
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite {path}')
    # Finish reading inputs before beginning installation.
    header = fixture()
    source = (ROOT/'tests/locations/bn_location_probe.cpp.inc').read_text(encoding='utf-8')
    created = []
    try:
        created.append(targets[0])
        shutil.copytree(ROOT/'mods/trkv_locations_dev', targets[0])
        for path, content in [(targets[1],source),(targets[2],header)]:
            created.append(path)
            path.write_text(content,encoding='utf-8')
    except BaseException:
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        raise
    return targets


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bn',type=Path)
    a=p.parse_args()
    for target in install(a.bn.resolve()):
        print(target)
