"""Four-level source preservation and stair regression tests; no BN runtime."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/locations'))
import build_factory_stack as builder
import check_factory_stack as checker
import install_factory_stack_probe as installer
import run_native_probe as runner


class Stack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprints = builder.load(builder.OUT/'floor_blueprints.json')
        cls.plan = builder.load(builder.OUT/'vertical_plan.json')
        cls.volumes = builder.load(builder.OUT/'volume_rules.json')
        cls.manifest = builder.load(builder.OUT/'stack_manifest.json')
        cls.definitions = builder.load(builder.MOD/'mapgen.json')
        cls.grids,cls.palette = checker.reconstruct(cls.manifest,cls.definitions)

    def test_only_declared_stair_and_air_cells_change(self):
        checker.validate_source(self.grids,self.manifest,self.blueprints,self.plan,self.volumes)
        self.assertEqual(len(self.manifest['vertical_transitions']),27)
        self.assertEqual(sum(c in '<>' for rows in self.grids.values() for r in rows for c in r),54)

    def test_builder_reproduces_packaged_rows(self):
        grids,transitions = builder.construct(self.blueprints,self.plan,self.volumes)
        self.assertEqual(grids,self.grids)
        self.assertEqual(transitions,self.manifest['vertical_transitions'])

    def test_wall_cut_and_unpaired_stair_are_rejected(self):
        for edit in ['.', '>']:
            grids = {z:rows.copy() for z,rows in self.grids.items()}
            row = list(grids[0][0]);row[0]=edit;grids[0][0]=''.join(row)
            with self.assertRaises(AssertionError):
                checker.validate_source(grids,self.manifest,self.blueprints,self.plan,self.volumes)

    def test_shifted_or_skipped_level_stair_is_rejected(self):
        for offset in [1,2]:
            manifest = deepcopy(self.manifest)
            manifest['vertical_transitions'][0]['to'][2] += offset
            with self.assertRaises(AssertionError):
                checker.validate_source(self.grids,manifest,self.blueprints,self.plan,self.volumes)

    def test_rejected_plan_relations_are_not_installed(self):
        rejected = {r['source_ref'] for r in self.plan['direction_supported_candidates']
                    if r['requires_intermediate_flight_review']}
        used = {r['source_ref'] for r in self.manifest['vertical_transitions']}
        self.assertFalse(rejected & used)
        self.assertNotIn('stair-134',used)
        for r in self.manifest['vertical_transitions']:
            key = r['source_ref'],r['from'][2],r['to'][2]
            self.assertFalse(any((a['source_ref'],a['from_z'],a['to_z'])==key
                                 for a in self.plan['direction_ambiguous']))

    def test_duplicate_and_missing_mapgen_tiles_are_rejected(self):
        for definitions in [self.definitions[:-1],self.definitions+[self.definitions[0]]]:
            with self.assertRaises(AssertionError):checker.reconstruct(self.manifest,definitions)

    def test_wrong_level_and_overlapping_tiles_are_rejected(self):
        for origin in [[0,0,3],self.manifest['blocks'][0]['origin']]:
            manifest = deepcopy(self.manifest);manifest['blocks'][1]['origin']=origin
            with self.assertRaises(AssertionError):checker.reconstruct(manifest,self.definitions)

    def test_graph_does_not_climb_an_unpaired_arrow(self):
        grids={-1:['<'],0:['.']}
        report=checker.graph(grids,{'<':2,'.':2})
        self.assertEqual(report['main_size'],1)
        report=checker.graph({-1:['<'],0:['>']},{'<':2,'>':2})
        self.assertEqual(report['main_size'],2)

    def test_missing_world_type_or_extra_json_is_rejected_before_execution(self):
        for mutation in ['missing_world_type','extra_json']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                bn=Path(temp)/'bn';(bn/'data/mods').mkdir(parents=True);(bn/'tests').mkdir()
                exe=bn/'exe';exe.write_bytes(b'protocol-only')
                with patch('subprocess.check_output',return_value=installer.BN_SHA+'\n'):
                    installer.install(bn)
                    mod=bn/'data/mods/trkv_factory_stack_dev'
                    if mutation=='missing_world_type':(mod/'world_types.json').unlink()
                    else:(mod/'extra.json').write_text('[]')
                    with patch.object(runner.subprocess,'run') as execute:
                        with self.assertRaisesRegex(ValueError,'Installed mod differs'):
                            runner.run(bn,exe,Path(temp)/'logs',[7],'factory-stack')
                        execute.assert_not_called()

    def test_stack_runner_uses_its_own_mod_test_and_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            bn=Path(temp)/'bn';(bn/'data/mods').mkdir(parents=True);(bn/'tests').mkdir()
            exe=bn/'exe';exe.write_bytes(b'protocol-only')
            commands=[]
            def process(args,**kwargs):
                commands.append(args)
                Path(args[args.index('--out')+1]).write_text(
                    f'<testsuite tests="1"><testcase name="{installer.CASE}"/></testsuite>')
                return subprocess.CompletedProcess(args,0)
            with patch('subprocess.check_output',return_value=installer.BN_SHA+'\n'):
                installer.install(bn)
                with patch.object(runner.subprocess,'run',side_effect=process):
                    receipt=runner.run(bn,exe,Path(temp)/'logs',[7,8,9],'factory-stack')
                self.assertEqual(json.loads(receipt.read_text())['location'],'factory-stack')
                self.assertTrue(all('--mods=trkv_factory_stack_dev' in c and '[trkv_factory_stack]' in c for c in commands))
                with self.assertRaises(FileExistsError):installer.install(bn)
                (bn/'tests/trkv_factory_stack_fixture.inc').write_text('tampered')
                with patch.object(runner.subprocess,'run') as execute:
                    with self.assertRaisesRegex(ValueError,'Installed fixture differs'):
                        runner.run(bn,exe,Path(temp)/'logs',[7],'factory-stack')
                    execute.assert_not_called()
                self.assertFalse(receipt.exists())


if __name__=='__main__':unittest.main()
