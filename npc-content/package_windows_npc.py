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
        'data/json/items/dda_quest_props.json',
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
        ('native/dda_quest_props.json', required[8]),
    ):
        if json.loads((ROOT / source).read_text(encoding='utf-8')) != json.loads((folder / target).read_text(encoding='utf-8')):
            raise ValueError('Installed port payload differs: ' + target)
    from merge_existing_locations import prepare
    _, _, merged, _ = prepare()
    if json.loads((folder / required[4]).read_text(encoding='utf-8')) != merged:
        raise ValueError('Installed chemist map differs from the reviewed replacement')

    from prepare_radio_stations import MAP as RADIO_MAP, CITY as RADIO_CITY, PAYLOAD as RADIO_PAYLOAD, prepare_data
    _, radio_payload, _ = prepare_data()
    from prepare_tower_expansions import prepare_data as tower_data, PAYLOAD as HOTEL_PAYLOAD
    radio_maps, hotel_payload = tower_data()
    for relative in (RADIO_MAP, RADIO_CITY):
        if json.loads((folder / relative).read_text(encoding='utf-8')) != json.loads(radio_maps[relative]):
            raise ValueError('Installed radio station map differs: ' + relative)
    if json.loads((folder / RADIO_PAYLOAD).read_text(encoding='utf-8')) != radio_payload:
        raise ValueError('Installed radio tower payload differs')
    if json.loads((folder / HOTEL_PAYLOAD).read_text(encoding='utf-8')) != hotel_payload:
        raise ValueError('Installed hotel roof payload differs')
    from prepare_shopping_plaza import prepare_data as plaza_data, PAYLOAD as PLAZA_PAYLOAD
    from compare_location_catalog import read_sources
    plaza_payload, _ = plaza_data(json.loads(read_sources()[0]['bn/' + RADIO_CITY]))
    if json.loads((folder / PLAZA_PAYLOAD).read_text(encoding='utf-8')) != plaza_payload:
        raise ValueError('Installed shopping plaza roofs differ')
    from prepare_rural_churches import prepare_data as church_data, PAYLOAD as CHURCH_PAYLOAD
    if json.loads((folder / CHURCH_PAYLOAD).read_text(encoding='utf-8')) != church_data():
        raise ValueError('Installed rural church payload differs')
    from prepare_xedra_creature import payload as creature_data, PAYLOAD as CREATURE_PAYLOAD
    if json.loads((folder / CREATURE_PAYLOAD).read_text(encoding='utf-8')) != creature_data():
        raise ValueError('Installed XEDRA creature dependencies differ')
    from prepare_xedra_gear import definitions as gear_data, PAYLOAD as GEAR_PAYLOAD
    if json.loads((folder / GEAR_PAYLOAD).read_text(encoding='utf-8')) != gear_data():
        raise ValueError('Installed XEDRA suit states differ')
    from prepare_karting import prepare_data as karting_data, PAYLOAD as KARTING_PAYLOAD
    if json.loads((folder / KARTING_PAYLOAD).read_text(encoding='utf-8')) != karting_data():
        raise ValueError('Installed complete karting circuit differs')
    from prepare_farm_supply import prepare_data as farm_data, PAYLOAD as FARM_PAYLOAD
    if json.loads((folder / FARM_PAYLOAD).read_text(encoding='utf-8')) != farm_data():
        raise ValueError('Installed farm supply payload differs')
    from prepare_eldercare import native_data as eldercare_data, PAYLOAD as ELDERCARE_PAYLOAD
    if json.loads((folder / ELDERCARE_PAYLOAD).read_text(encoding='utf-8')) != eldercare_data():
        raise ValueError('Installed eldercare support payload differs')
    from prepare_civilians import native_data as civilian_data, PAYLOAD as CIVILIAN_PAYLOAD
    if json.loads((folder / CIVILIAN_PAYLOAD).read_text(encoding="utf-8")) != civilian_data():
        raise ValueError("Installed civilian data differs")
    from prepare_eldercare_fauna import native_data as fauna_data, PAYLOAD as FAUNA_PAYLOAD
    if json.loads((folder / FAUNA_PAYLOAD).read_text(encoding="utf-8")) != fauna_data():
        raise ValueError("Installed eldercare fauna differs")
    from prepare_eldercare_loot import native_data as loot_data, PAYLOAD as LOOT_PAYLOAD
    if json.loads((folder / LOOT_PAYLOAD).read_text(encoding="utf-8")) != loot_data():
        raise ValueError("Installed eldercare loot differs")
    from prepare_eldercare_assets import native_data as asset_data, PAYLOAD as ASSET_PAYLOAD
    if json.loads((folder / ASSET_PAYLOAD).read_text(encoding="utf-8")) != asset_data():
        raise ValueError("Installed eldercare assets differ")
    from prepare_terminal_archives import native_data as archive_data, PAYLOAD as ARCHIVE_PAYLOAD
    if json.loads((folder / ARCHIVE_PAYLOAD).read_text(encoding="utf-8")) != archive_data():
        raise ValueError("Installed terminal archives differ")
    from prepare_hub_elevator import MUTATIONS, PAYLOAD, payload, replacements
    if json.loads((folder / PAYLOAD).read_text(encoding='utf-8')) != payload():
        raise ValueError('Installed Hub access payload differs')
    if json.loads((folder / MUTATIONS).read_text(encoding='utf-8')) != json.loads(replacements()[MUTATIONS]):
        raise ValueError('Installed Hub access mutual exclusion differs')
    from prepare_location_expansion import nuclear_patch, NUCLEAR
    if json.loads((folder / NUCLEAR).read_text(encoding='utf-8')) != json.loads(nuclear_patch()[1]):
        raise ValueError('Installed nuclear special differs from the reviewed shoreline merge')


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
        'The demilled Kord is a quest prop, not a working firearm.\n'
        'Includes 24 DDA shoreline cells at the existing BN nuclear power plant.\n'
        'Both BN radio stations retain their buildings and gain DDA tower floors through z=6.\n'
        'All three existing hotel variants gain technical-enclosure roof caps at z=5.\n'
        'The existing abandoned shopping plaza gains seven DDA roof sections at z=1.\n'
        'Includes the rural church with parking, basement, steeple and bell terminal.\n'
        'XEDRA creature, particles and glowing string are included; activity suit states are included; the XEDRA church, powered respirator and S02a suit remain staged.\n'
        'Includes normal/looted farm supply stores with roofs, ladders and BN-packaged materials and food.\n'
        'Karting cash registers use stock BN money; no DDA denominations are installed.\n'
        'Eldercare pond/web support is included; nursing-home and retirement-community maps remain staged.\n'
        'Hub restricted elevator handlers and credential are included; the expanded Hub maps are not installed yet.\n'
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
