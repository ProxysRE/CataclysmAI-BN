#!/usr/bin/env python3
"""Exercise portable archive provenance and reject incomplete/stale installations."""
import json
from pathlib import Path
import tempfile
import zipfile

from merge_existing_locations import prepare
from prepare_radio_stations import MAP as RADIO_MAP, CITY as RADIO_CITY, PAYLOAD as RADIO_PAYLOAD, prepare_data
from prepare_location_expansion import nuclear_patch, NUCLEAR
from prepare_hub_elevator import MUTATIONS, PAYLOAD, payload as hub_payload, replacements
from package_windows_npc import ROOT, digest, package, verify_install


def check():
    _, _, merged, _ = prepare()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        installed = root / 'CBN_DDA_NPC_DEV'
        _, radio_payload, _ = prepare_data()
        from prepare_tower_expansions import prepare_data as tower_data, PAYLOAD as HOTEL_PAYLOAD
        radio_maps, hotel_payload = tower_data()
        from prepare_shopping_plaza import prepare_data as plaza_data, PAYLOAD as PLAZA_PAYLOAD
        from compare_location_catalog import read_sources
        plaza_payload, _ = plaza_data(json.loads(read_sources()[0]['bn/' + RADIO_CITY]))
        from prepare_rural_churches import prepare_data as church_data, PAYLOAD as CHURCH_PAYLOAD
        from prepare_xedra_creature import payload as creature_data, PAYLOAD as CREATURE_PAYLOAD
        from prepare_xedra_gear import definitions as gear_data, PAYLOAD as GEAR_PAYLOAD
        from prepare_karting import prepare_data as karting_data, PAYLOAD as KARTING_PAYLOAD
        from prepare_eldercare import native_data as eldercare_data, PAYLOAD as ELDERCARE_PAYLOAD
        from prepare_farm_supply import prepare_data as farm_data, PAYLOAD as FARM_PAYLOAD
        from prepare_terminal_archives import native_data as archive_data, PAYLOAD as ARCHIVE_PAYLOAD
        from prepare_eldercare_assets import native_data as asset_data, PAYLOAD as ASSET_PAYLOAD
        from prepare_shared_casing import payload as shared_casing_data, TARGET as SHARED_CASING_TARGET
        from prepare_militia import native_data as militia_data, PAYLOAD as MILITIA_PAYLOAD
        from prepare_eldercare_groups import native_data as groups_data, PAYLOAD as GROUPS_PAYLOAD
        from prepare_civilians import native_data as civilian_data, PAYLOAD as CIVILIAN_PAYLOAD, LEGACY_CORE, mod_sources, lua_payload
        from prepare_eldercare_fauna import native_data as fauna_data, PAYLOAD as FAUNA_PAYLOAD
        from prepare_eldercare_loot import native_data as loot_data, PAYLOAD as LOOT_PAYLOAD
        payload = {
            SHARED_CASING_TARGET: json.dumps(shared_casing_data()).encode(),
            MILITIA_PAYLOAD: json.dumps(militia_data()).encode(),
            GROUPS_PAYLOAD: json.dumps(groups_data()).encode(),
            CIVILIAN_PAYLOAD: json.dumps(civilian_data()).encode(),
            FAUNA_PAYLOAD: json.dumps(fauna_data()).encode(),
            LOOT_PAYLOAD: json.dumps(loot_data()).encode(),
            ASSET_PAYLOAD: json.dumps(asset_data()).encode(),
            ARCHIVE_PAYLOAD: json.dumps(archive_data()).encode(),
            FARM_PAYLOAD: json.dumps(farm_data()).encode(),
            ELDERCARE_PAYLOAD: json.dumps(eldercare_data()).encode(),
            KARTING_PAYLOAD: json.dumps(karting_data()).encode(),
            GEAR_PAYLOAD: json.dumps(gear_data()).encode(),
            CREATURE_PAYLOAD: json.dumps(creature_data()).encode(),
            CHURCH_PAYLOAD: json.dumps(church_data()).encode(),
            PLAZA_PAYLOAD: json.dumps(plaza_payload).encode(),
            HOTEL_PAYLOAD: json.dumps(hotel_payload).encode(),
            RADIO_MAP: radio_maps[RADIO_MAP].encode(),
            RADIO_CITY: radio_maps[RADIO_CITY].encode(),
            RADIO_PAYLOAD: json.dumps(radio_payload).encode(),
            NUCLEAR: nuclear_patch()[1].encode(),
            MUTATIONS: replacements()[MUTATIONS].encode(),
            PAYLOAD: json.dumps(hub_payload()).encode(),
            'cataclysm-bn-tiles.exe': b'MZ-test-executable',
            'LICENSE.txt': b'fixture',
            'gfx/fixture.txt': b'fixture',
            'data/shaders/fixture.spv': b'fixture',
            'lang/mo/ru_RU/LC_MESSAGES/cataclysm-bn.mo': b'fixture',
            'data/json/npcs/dda_lighthouse_community.json': (ROOT / 'native/dda_lighthouse_community.json').read_bytes(),
            'data/json/mapgen/nested/dda_lighthouse_encounter.json': (ROOT / 'native/mapgen/dda_lighthouse_encounter.json').read_bytes(),
            'data/json/mapgen/chemical_lab.json': json.dumps(merged).encode(),
            'data/json/items/dda_quest_usb.json': (ROOT / 'native/dda_quest_usb.json').read_bytes(),
            'data/json/items/dda_545_casing.json': (ROOT / 'native/dda_545_casing.json').read_bytes(),
            'data/json/items/dda_quest_props.json': (ROOT / 'native/dda_quest_props.json').read_bytes(),
        }
        payload.update({'data/mods/Civilians/' + name: text.encode() for name, text in mod_sources().items() if name != 'civilians.json'})
        payload['data/mods/Civilians/main.lua'] = lua_payload().encode()
        for relative, data in payload.items():
            path = installed / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        output = root / 'package.zip'
        package(installed, output, 'a' * 40)
        with zipfile.ZipFile(output) as archive:
            assert archive.testzip() is None
            build = json.loads(archive.read('CBN_DDA_NPC_DEV/DDA_PORT_BUILD.json'))
            assert build['source_head'] == 'a' * 40
            for relative in payload:
                assert archive.read('CBN_DDA_NPC_DEV/' + relative) == payload[relative]
                assert build['files'][relative] == digest(installed / relative)
        assert output.with_suffix('.zip.sha256').read_text().split()[0] == digest(output)
        for mutation in ('missing_translation', 'stale_map', 'stale_nuclear', 'stale_eldercare', 'stale_farm', 'stale_archives', 'stale_assets', 'stale_loot', 'stale_fauna', 'stale_civilians', 'stale_groups', 'stale_militia', 'stale_civilian_lua', 'legacy_civilians', 'stale_shared_casing', 'user_data'):
            if mutation == 'missing_translation':
                path = installed / 'lang/mo/ru_RU/LC_MESSAGES/cataclysm-bn.mo'
                path.unlink()
            elif mutation == 'stale_map':
                path = installed / 'data/json/mapgen/chemical_lab.json'
                path.write_text('[]')
            elif mutation == 'stale_nuclear':
                path = installed / NUCLEAR
                path.write_text('[]')
            elif mutation == 'stale_shared_casing':
                path = installed / SHARED_CASING_TARGET
                path.write_text('[]')
            elif mutation == 'legacy_civilians':
                path = installed / LEGACY_CORE
                path.write_text('[]')
            elif mutation == 'stale_militia':
                path = installed / MILITIA_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_civilian_lua':
                path = installed / 'data/mods/Civilians/main.lua'
                path.write_text(mod_sources()['main.lua'])
            elif mutation == 'stale_groups':
                path = installed / GROUPS_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_civilians':
                path = installed / CIVILIAN_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_fauna':
                path = installed / FAUNA_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_loot':
                path = installed / LOOT_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_assets':
                path = installed / ASSET_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_archives':
                path = installed / ARCHIVE_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_farm':
                path = installed / FARM_PAYLOAD
                path.write_text('[]')
            elif mutation == 'stale_eldercare':
                path = installed / ELDERCARE_PAYLOAD
                path.write_text('[]')
            else:
                path = installed / 'save'
                path.mkdir()
            try:
                verify_install(installed)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid installation accepted: ' + mutation)
            if mutation == 'user_data':
                path.rmdir()
            elif mutation == 'legacy_civilians':
                path.unlink()
            else:
                path.write_bytes(payload[path.relative_to(installed).as_posix()])
        try:
            package(installed, installed / 'recursive.zip', 'a' * 40)
        except ValueError:
            pass
        else:
            raise AssertionError('Archive inside its input directory accepted')
    print('PASS: portable archive payload, provenance, checksums and installation rejection checks')


if __name__ == '__main__':
    check()
