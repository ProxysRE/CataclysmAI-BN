"""Mutation regressions: checker must reject materially broken generated maps."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('location_checker', ROOT/'tools/locations/check_industrial.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class Validation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        shutil.copytree(checker.LOCATION, root/'location')
        shutil.copytree(checker.MOD, root/'mod')
        self.loc, self.mod = root/'location', root/'mod'
        self.context = patch.multiple(checker, LOCATION=self.loc, MOD=self.mod)
        self.context.start()
        self.addCleanup(self.context.stop)

    def mutate(self, filename, callback):
        path = (self.loc if filename == 'manifest.json' else self.mod)/filename
        data = json.loads(path.read_text(encoding='utf-8'))
        callback(data)
        path.write_text(json.dumps(data), encoding='utf-8')

    def test_baseline(self):
        self.assertEqual(checker.check(BN)['exit_regions'], 2)

    def test_unknown_asset(self):
        self.mutate('mapgen.json', lambda ds: ds[0]['object']['terrain'].update({'#': 't_nonexistent_location_wall'}))
        with self.assertRaises(KeyError):
            checker.check(BN)

    def test_block_overlap(self):
        self.mutate('manifest.json', lambda m: m['blocks'][1].update(origin=m['blocks'][0]['origin']))
        with self.assertRaisesRegex(AssertionError, 'overlap'):
            checker.check(BN)

    def test_impassable_spawn_furniture(self):
        def obstruct(ds):
            obj = ds[0]['object']
            obj['rows'][8] = obj['rows'][8][:5] + 'X' + obj['rows'][8][6:]
            obj['terrain']['X'] = 't_thconc_floor'
            obj['furniture']['X'] = 'f_locker'
        self.mutate('mapgen.json', obstruct)
        with self.assertRaisesRegex(AssertionError, 'invalid spawn'):
            checker.check(BN)

    def test_closed_exit(self):
        def obstruct(ds):
            obj = ds[6]['object']
            for y in range(4,9):
                row = obj['rows'][y]
                obj['rows'][y] = row[:4] + '#####' + row[9:]
        self.mutate('mapgen.json', obstruct)
        with self.assertRaises(AssertionError):
            checker.check(BN)

    def test_loss_of_second_route(self):
        def obstruct(ds):
            for i in [4,5]:
                obj=ds[i]['object']
                row=obj['rows'][23]
                start=4 if i==4 else 0
                obj['rows'][23]=row[:start]+'#'*(24-start)
        self.mutate('mapgen.json', obstruct)
        with self.assertRaisesRegex(AssertionError, 'independent hall_only'):
            checker.check(BN)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bn', type=Path, required=True)
    args, remaining=parser.parse_known_args()
    BN=args.bn.resolve()
    unittest.main(argv=['industrial_validation_test.py', *remaining])
