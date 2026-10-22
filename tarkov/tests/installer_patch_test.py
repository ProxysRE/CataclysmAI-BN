"""Exercise the real git patch command across Windows checkout EOL combinations."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from install_into_bn import apply_engine_patch  # noqa: E402


class PatchCheckoutTest(unittest.TestCase):
    def test_checkout_newlines(self):
        for filename, target_name, expected in (
            ("0001-restore-bounds-to-target-dimension.patch", "src/savegame.cpp",
             "MAPBUFFER_REGISTRY.get( current_dimension_id_ ).set_pocket_info( pocket_info );"),
            ("0002-expose-active-npc-spawn.patch", "src/catalua_bindings_game_creatures.cpp", '"spawn_npc_at"'),
        ):
            patch = (ROOT / "patches" / filename).read_bytes().replace(b"\r\n", b"\n")
            # Both pinned patches contain one hunk; reconstruct its original context.
            lines = patch.decode().splitlines()
            self.assertEqual(sum(line.startswith("@@") for line in lines), 1)
            start = int(lines[3].split()[1][1:].split(",")[0])
            fragment = [line[1:] for line in lines[4:] if line.startswith((" ", "-"))]
            source = ("\n" * (start - 1) + "\n".join(fragment) + "\n").encode()
            for src_crlf in (False, True):
                for patch_crlf in (False, True):
                    for autocrlf in ("false", "true"):
                        with self.subTest(patch=filename, source_crlf=src_crlf, patch_crlf=patch_crlf, autocrlf=autocrlf):
                            with tempfile.TemporaryDirectory(prefix="trkv-patch-test-") as tmp:
                                bn = Path(tmp)
                                (bn / "src").mkdir()
                                subprocess.run(["git", "init", "-q", tmp], check=True)
                                subprocess.run(["git", "-C", tmp, "config", "core.autocrlf", autocrlf], check=True)
                                target = bn / target_name
                                target.write_bytes(source.replace(b"\n", b"\r\n") if src_crlf else source)
                                patch_path = bn / "fix.patch"
                                patch_path.write_bytes(patch.replace(b"\n", b"\r\n") if patch_crlf else patch)
                                apply_engine_patch(bn, patch_path)
                                self.assertIn(expected, target.read_text(encoding="utf-8"))



if __name__ == "__main__":
    unittest.main()
