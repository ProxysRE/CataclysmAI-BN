"""Prevent empty/skipped reports and stale receipts from passing the release gate."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_native_checks import run, validate_report
from run_npc_probe import run as run_npc


class NativeGateTest(unittest.TestCase):
    def test_rejects_reports_without_one_successful_case(self):
        invalid = (
            "<testsuites/>",
            "<testsuites><testcase/><testcase/></testsuites>",
            "<testsuites><testcase><skipped/></testcase></testsuites>",
            "<testsuites><testcase><failure/></testcase></testsuites>",
            "<testsuites><testcase><error/></testcase></testsuites>",
        )
        with tempfile.TemporaryDirectory() as scratch:
            report = Path(scratch) / "report.xml"
            for xml in invalid:
                with self.subTest(xml=xml):
                    report.write_text(xml)
                    with self.assertRaises(RuntimeError):
                        validate_report(report)
            report.write_text("<testsuites><testsuite><testcase/></testsuite></testsuites>")
            validate_report(report)

    def test_npc_probe_rejects_stale_or_missing_reports(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            report = root / "tarkov-npc.xml"
            report.write_text("<testsuites><testcase/></testsuites>")
            # Even a nominally successful process must write a fresh report.
            with patch("run_npc_probe.subprocess.run") as execute:
                with self.assertRaises(FileNotFoundError):
                    run_npc(root, root / "test", root)
                command = execute.call_args.args[0]
                self.assertIn("[tarkov_npc]", command)
                self.assertTrue(execute.call_args.kwargs["check"])
            self.assertFalse(report.exists())

    def test_npc_probe_propagates_failed_process_with_report(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            def fail(*args, **kwargs):
                (root / "tarkov-npc.xml").write_text("<testsuites><testcase/></testsuites>")
                raise subprocess.CalledProcessError(1, args[0])
            with patch("run_npc_probe.subprocess.run", side_effect=fail):
                with self.assertRaises(subprocess.CalledProcessError):
                    run_npc(root, root / "test", root)

    def test_failed_run_removes_previous_success_receipt(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            receipt = root / "native-checks.json"
            receipt.write_text('{"passed":true}')
            with self.assertRaises(FileNotFoundError):
                run(root, root / "missing-test", root / "missing-game", root)
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
