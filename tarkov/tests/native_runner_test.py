"""Prevent empty/skipped reports and stale receipts from passing the release gate."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_native_checks import run, validate_report
from run_npc_probe import run as run_npc
from run_cold_restart import run as run_cold


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

    def test_npc_probe_requires_every_independent_case(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            def incomplete(*args, **kwargs):
                (root / "tarkov-npc.xml").write_text("<testsuites><testcase/></testsuites>")
            with patch("run_npc_probe.subprocess.run", side_effect=incomplete):
                with self.assertRaises(RuntimeError):
                    run_npc(root, root / "test", root)

    def test_cold_restart_rejects_stale_or_missing_reports(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            executable = root / "test"
            executable.touch()
            report = root / "tarkov-cold-write.xml"
            report.write_text("<testsuites><testcase/></testsuites>")
            with patch("run_cold_restart.subprocess.run") as execute:
                with self.assertRaises(FileNotFoundError):
                    run_cold(root, root, executable)
                self.assertEqual(execute.call_count, 1)
                self.assertIn("[tarkov_cold_write]", execute.call_args.args[0])
                self.assertTrue(execute.call_args.kwargs["check"])
            self.assertFalse(report.exists())

    def test_varied_cold_chain_uses_three_processes_and_separate_reports(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            executable = root / "test"
            executable.touch()
            old = root / "tarkov-cold-write.xml"
            old.write_text("patrol-report")
            def success(command, **kwargs):
                env = kwargs["env"]
                self.assertEqual(env["TRKV_COLD_ENCOUNTER"], "varied")
                report = Path(command[command.index("--out") + 1])
                self.assertIn("tarkov-cold-varied-", report.name)
                report.write_text("<testsuites><testcase/></testsuites>")
                manifest = Path(env["TRKV_COLD_MANIFEST"])
                world = manifest.parent / (manifest.stem + "-world")
                world.mkdir()
                manifest.write_text(str(world))
            with patch("run_cold_restart.subprocess.run", side_effect=success) as execute:
                with redirect_stdout(io.StringIO()):
                    run_cold(root, root, executable, encounter="varied")
                self.assertEqual(execute.call_count, 3)
                self.assertIn("[tarkov_cold_write]", execute.call_args_list[0].args[0])
                self.assertEqual(execute.call_args_list[1].kwargs["env"]["TRKV_COLD_STAGE"], "cold_read_active")
                self.assertEqual(execute.call_args_list[2].kwargs["env"]["TRKV_COLD_STAGE"], "cold_read_cleanup")
            self.assertEqual(old.read_text(), "patrol-report")
            for stage in ("write", "active", "cleanup"):
                validate_report(root / f"tarkov-cold-varied-{stage}.xml")

    def test_npc_probe_propagates_failed_process_with_report(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for xml, expected in (
                ('<testsuites><testcase><failure message="ammo mismatch">30 != 60</failure></testcase></testsuites>',
                 "ammo mismatch"),
                ('<testsuites><testcase><error message="Lua failed">reload_failed: visible_target</error></testcase></testsuites>',
                 "reload_failed: visible_target"),
                ("<malformed", "Could not read NPC failure report"),
            ):
                with self.subTest(xml=xml):
                    error = subprocess.CalledProcessError(1, ["native-test"])
                    def fail(*args, **kwargs):
                        (root / "tarkov-npc.xml").write_text(xml)
                        raise error
                    output = io.StringIO()
                    with patch("run_npc_probe.subprocess.run", side_effect=fail), redirect_stdout(output):
                        with self.assertRaises(subprocess.CalledProcessError) as raised:
                            run_npc(root, root / "test", root)
                    self.assertIs(raised.exception, error)
                    self.assertIn(expected, output.getvalue())

    def test_npc_probe_selects_platform_backend_and_preserves_overrides(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            def success(*args, **kwargs):
                (root / "tarkov-npc.xml").write_text("<testsuites>" + "<testcase/>" * 8 + "</testsuites>")
            with patch.dict(os.environ, {}, clear=True):
                with patch("run_npc_probe.subprocess.run", side_effect=success) as execute:
                    run_npc(root, root / "test", root)
                    env = execute.call_args.kwargs["env"]
                    self.assertEqual(env["SDL_VIDEODRIVER"], "dummy" if os.name == "nt" else "offscreen")
                    self.assertEqual(env["SDL_AUDIODRIVER"], "dummy")
            with patch.dict(os.environ, {"SDL_VIDEODRIVER": "chosen", "SDL_AUDIODRIVER": "chosen"}):
                with patch("run_npc_probe.subprocess.run", side_effect=success) as execute:
                    run_npc(root, root / "test", root)
                    env = execute.call_args.kwargs["env"]
                    self.assertEqual(env["SDL_VIDEODRIVER"], "chosen")
                    self.assertEqual(env["SDL_AUDIODRIVER"], "chosen")

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
