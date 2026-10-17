#!/usr/bin/env python3
"""Archive a BN CMake installation after verifying the port's installed payload."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def verify_install(folder):
    required = (
        'cataclysm-bn-tiles.exe', 'LICENSE.txt',
        'data/json/npcs/dda_lighthouse_community.json',
        'data/json/mapgen/nested/dda_lighthouse_encounter.json',
        'data/json/mapgen/chemical_lab.json',
        'lang/mo/ru_RU/LC_MESSAGES/cataclysm-bn.mo',
        'data/json/items/dda_quest_usb.json',
        'data/json/items/dda_545_casing.json',
    )
    for relative in required:
        path = folder / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Incomplete CMake installation: ' + relative)
    with (folder / required[0]).open('rb') as executable:
        if executable.read(2) != b'MZ':
            raise ValueError('Expected a Windows executable')
    for relative in ('gfx', 'data/shaders'):
        if not any(p.is_file() for p in (folder / relative).rglob('*')):
            raise ValueError('Missing installed assets: ' + relative)
    for relative in ('save', 'config', 'npc_ci_test_user', '.git'):
        if (folder / relative).exists():
            raise ValueError('User or checkout data in installation: ' + relative)
    for source, target in (
        ('native/dda_lighthouse_community.json', required[2]),
        ('native/mapgen/dda_lighthouse_encounter.json', required[3]),
        ('native/dda_quest_usb.json', required[6]),
        ('native/dda_545_casing.json', required[7]),
    ):
        if json.loads((ROOT / source).read_text(encoding='utf-8')) != json.loads((folder / target).read_text(encoding='utf-8')):
            raise ValueError('Installed port payload differs: ' + target)
    from merge_existing_locations import prepare
    _, _, merged, _ = prepare()
    if json.loads((folder / required[4]).read_text(encoding='utf-8')) != merged:
        raise ValueError('Installed chemist map differs from the reviewed replacement')


def package(folder, output, source_head):
    folder, output = folder.resolve(), output.resolve()
    if not re.fullmatch('[a-f0-9]{40}', source_head):
        raise ValueError('Expected the complete source commit SHA')
    if output == folder or folder in output.parents:
        raise ValueError('Output archive must be outside the installation')
    verify_install(folder)
    (folder / 'DDA_PORT_README.txt').write_text(
        'CBN DDA NPC development build for Windows x64\n'
        'Extract the entire directory and run cataclysm-bn-tiles.exe.\n'
        'Includes the lighthouse community and reviewed chemist map adjustment.\n'
        'Also includes the two quest USB dependencies for the Isolated Road port.\n'
        'The 5.45x39 casing dependency is included; the live ammo and Kord rifle are still pending.\n'
        'Other staged DDA communities and the separate highway branch are not included.\n'
        'Whole quest-chain field testing is still pending.\n'
        'Build source: https://github.com/ProxysRE/CataclysmAI-BN/commit/' + source_head + '\n',
        encoding='utf-8')
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p.name != 'DDA_PORT_BUILD.json')
    manifest = {
        'source_head': source_head,
        'bn_base': 'c621aaf42fa182473aad10feea2b55647704dcf1',
        'packaging': 'Official BN CMake installation rules',
        'native_patch_sha256': digest(ROOT / 'artisan_engine.patch'),
        'files': {p.relative_to(folder).as_posix(): digest(p) for p in files},
        'full_campaign_validated': False,
    }
    (folder / 'DDA_PORT_BUILD.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(p for p in folder.rglob('*') if p.is_file()):
            archive.write(path, folder.name + '/' + path.relative_to(folder).as_posix())
    checksum = output.with_suffix(output.suffix + '.sha256')
    checksum.write_text(digest(output) + '  ' + output.name + '\n')
    print(output.name + ': installation verified, archive and SHA256 written')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-head', required=True)
    args = parser.parse_args()
    package(args.installed, args.output, args.source_head)
