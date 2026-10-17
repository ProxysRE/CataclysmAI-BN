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
        payload = {
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
        for mutation in ('missing_translation', 'stale_map', 'stale_nuclear', 'user_data'):
            if mutation == 'missing_translation':
                path = installed / 'lang/mo/ru_RU/LC_MESSAGES/cataclysm-bn.mo'
                path.unlink()
            elif mutation == 'stale_map':
                path = installed / 'data/json/mapgen/chemical_lab.json'
                path.write_text('[]')
            elif mutation == 'stale_nuclear':
                path = installed / NUCLEAR
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
