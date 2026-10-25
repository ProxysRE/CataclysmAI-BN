"""Runner/installer protocol tests. These do NOT execute or compile BN."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parents[2]/'tools/locations'
sys.path.insert(0,str(TOOLS))
import install_native_probe as installer
import run_native_probe as runner


class Protocol(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.bn=self.base/'bn'
        (self.bn/'data/mods').mkdir(parents=True)
        (self.bn/'tests').mkdir()
        self.sha=patch('subprocess.check_output',return_value=installer.BN_SHA+'\n')
        self.sha.start()
        self.addCleanup(self.sha.stop)
        installer.install(self.bn)
        self.exe=self.bn/'test-executable'
        self.exe.write_bytes(b'protocol-test-only')
        self.output=self.base/'output'
        self.commands=[]

    def fake_process(self,args,**kwargs):
        self.commands.append(args)
        path=Path(args[args.index('--out')+1])
        path.write_text(f'<testsuites><testsuite tests="1" failures="0" errors="0">'
                        f'<testcase name="{runner.CASE}"/></testsuite></testsuites>')
        return subprocess.CompletedProcess(args,0)

    def test_three_fresh_seeds_and_isolated_userdirs(self):
        with patch.object(runner.subprocess,'run',side_effect=self.fake_process):
            receipt=runner.run(self.bn,self.exe,self.output,[1,2,3])
        data=json.loads(receipt.read_text())
        self.assertEqual([r['seed'] for r in data['runs']],[1,2,3])
        dirs=[next(a for a in c if a.startswith('--user-dir=')) for c in self.commands]
        self.assertEqual(len(set(dirs)),3)
        self.assertTrue(all(a.endswith('/user') for a in dirs))

    def test_existing_installed_mod_is_not_overwritten(self):
        target=self.bn/'data/mods/trkv_locations_dev/mapgen.json'
        before=target.read_bytes()
        with self.assertRaises(FileExistsError):
            installer.install(self.bn)
        self.assertEqual(target.read_bytes(),before)

    def test_changed_installed_mod_is_rejected_before_execution(self):
        (self.bn/'data/mods/trkv_locations_dev/mapgen.json').write_text('[]')
        with patch.object(runner.subprocess,'run') as execute:
            with self.assertRaisesRegex(ValueError,'Installed mod differs'):
                runner.run(self.bn,self.exe,self.output,[1])
            execute.assert_not_called()

    def test_missing_fresh_xml_and_old_receipt_are_rejected(self):
        self.output.mkdir()
        (self.output/'location-native-1.xml').write_text('<old/>')
        receipt=self.output/'location-native-receipt.json'
        receipt.write_text('{}')
        with patch.object(runner.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
            with self.assertRaises(FileNotFoundError):
                runner.run(self.bn,self.exe,self.output,[1])
        self.assertFalse(receipt.exists())

    def test_nonzero_process_cannot_pass_with_valid_xml(self):
        def fail(args,**kwargs):
            self.fake_process(args,**kwargs)
            return subprocess.CompletedProcess(args,9)
        with patch.object(runner.subprocess,'run',side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError):
                runner.run(self.bn,self.exe,self.output,[1])
        self.assertFalse((self.output/'location-native-receipt.json').exists())

    def test_skipped_empty_wrong_and_failed_xml_are_rejected(self):
        path=self.base/'result.xml'
        for body in [
            '<testsuites/>',
            '<testsuite tests="0"/>',
            '<testsuite tests="1"><testcase name="wrong"/></testsuite>',
            f'<testsuite tests="1"><testcase name="{runner.CASE}"><skipped/></testcase></testsuite>',
            f'<testsuite tests="1"><testcase name="{runner.CASE}"><failure/></testcase></testsuite>',
            f'<testsuite tests="1" errors="1"><testcase name="{runner.CASE}"/></testsuite>',
        ]:
            with self.subTest(body=body):
                path.write_text(body)
                with self.assertRaises(ValueError):
                    runner.validate_report(path)

    def test_install_rolls_back_only_its_new_files_on_failure(self):
        clean=self.base/'rollback-bn'
        (clean/'data/mods').mkdir(parents=True)
        (clean/'tests').mkdir()
        original=Path.write_text
        def fail(path,*args,**kwargs):
            if path.name=='trkv_location_fixture.inc':
                raise OSError('simulated full disk')
            return original(path,*args,**kwargs)
        sentinel=clean/'tests/unrelated.cpp'
        sentinel.write_text('untouched')
        with patch.object(Path,'write_text',new=fail):
            with self.assertRaises(OSError):
                installer.install(clean)
        self.assertEqual(sentinel.read_text(),'untouched')
        self.assertFalse((clean/'data/mods/trkv_locations_dev').exists())
        self.assertFalse((clean/'tests/trkv_location_constructor_test.cpp').exists())


if __name__=='__main__':
    unittest.main()
