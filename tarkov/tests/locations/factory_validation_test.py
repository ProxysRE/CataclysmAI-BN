"""Factory packaging rejection tests; these do not execute BN."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools/locations'))
import check_factory as checker
import install_factory_probe as installer
import run_native_probe as runner


class Packaging(unittest.TestCase):
    def setUp(self):
        self.manifest = checker.load(checker.OUT/'ground_manifest.json')
        self.definitions = checker.load(checker.MOD/'mapgen.json')

    def test_packaged_cells_match_geometry(self):
        rows, terrain = checker.reconstruct(self.manifest, self.definitions)
        geometry = checker.load(checker.OUT/'ground_geometry.json')
        self.assertEqual(rows, geometry['rows'])
        self.assertEqual(terrain, geometry['terrain'])

    def test_duplicate_and_missing_tiles_are_rejected(self):
        for definitions in [self.definitions[:-1], self.definitions+[self.definitions[0]]]:
            with self.assertRaises(AssertionError):
                checker.reconstruct(self.manifest, definitions)

    def test_overlap_and_misaligned_blocks_are_rejected(self):
        for origin in [self.manifest['blocks'][0]['origin'], [1, 24, 0]]:
            manifest = deepcopy(self.manifest)
            manifest['blocks'][1]['origin'] = origin
            with self.assertRaises(AssertionError):
                checker.reconstruct(manifest, self.definitions)

    def test_content_injection_is_rejected(self):
        definitions = deepcopy(self.definitions)
        definitions[0]['object']['place_monsters'] = [{'monster': 'GROUP_ZOMBIE'}]
        with self.assertRaises(AssertionError):
            checker.reconstruct(self.manifest, definitions)


class FactoryProtocol(unittest.TestCase):
    def test_factory_runner_requests_its_own_mod_and_test(self):
        with tempfile.TemporaryDirectory() as temp:
            bn = Path(temp)/'bn'
            (bn/'data/mods').mkdir(parents=True)
            (bn/'tests').mkdir()
            exe = bn/'test-executable'
            exe.write_bytes(b'protocol-test-only')
            commands = []
            def process(args, **kwargs):
                commands.append(args)
                Path(args[args.index('--out')+1]).write_text(
                    f'<testsuite tests="1"><testcase name="{installer.CASE}"/></testsuite>')
                return subprocess.CompletedProcess(args, 0)
            with patch('subprocess.check_output', return_value=installer.BN_SHA+'\n'):
                installer.install(bn)
                with patch.object(runner.subprocess, 'run', side_effect=process):
                    receipt = runner.run(bn, exe, Path(temp)/'logs', [11, 12, 13], 'factory')
                self.assertEqual(json.loads(receipt.read_text())['location'], 'factory')
                self.assertTrue(all('--mods=trkv_factory_dev' in c and '[trkv_factory]' in c for c in commands))
                with self.assertRaises(FileExistsError):
                    installer.install(bn)
                (bn/'tests/trkv_factory_fixture.inc').write_text('tampered')
                with patch.object(runner.subprocess, 'run') as execute:
                    with self.assertRaisesRegex(ValueError, 'Installed fixture differs'):
                        runner.run(bn, exe, Path(temp)/'logs', [11], 'factory')
                    execute.assert_not_called()
                self.assertFalse(receipt.exists())


if __name__ == '__main__':
    unittest.main()
