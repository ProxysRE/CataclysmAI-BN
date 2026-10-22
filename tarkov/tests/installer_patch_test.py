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
        for filename, expected in (
            ("0001-restore-bounds-to-target-dimension.patch", {"src/savegame.cpp":
             "MAPBUFFER_REGISTRY.get( current_dimension_id_ ).set_pocket_info( pocket_info );"}),
            ("0002-expose-active-npc-spawn.patch", {"src/catalua_bindings_game_creatures.cpp": '"spawn_npc_at"'}),
            ("0003-expose-npc-path-step.patch", {"src/catalua_bindings_creature.cpp": '"move_towards"'}),
            ("0004-controlled-npc-attributes.patch", {"src/npc_class.h": "npc_attribute_profile",
             "src/npc_class.cpp": '"attribute_profile"', "src/npc.cpp": "profile->strength",
             "src/character.cpp": "npc_profile_hp_"}),
        ):
            patch = (ROOT / "patches" / filename).read_bytes().replace(b"\r\n", b"\n")
            # Reconstruct original hunk contexts, including multi-file patches.
            sources, target_name, cursor = {}, None, None
            for line in patch.decode().splitlines():
                if line.startswith("--- a/"):
                    target_name = line[6:]
                    sources.setdefault(target_name, [])
                    cursor = None
                elif line.startswith("@@"):
                    cursor = int(line.split()[1][1:].split(",")[0]) - 1
                elif line.startswith(("diff --git", "+++")):
                    continue
                elif cursor is not None and line.startswith((" ", "-")):
                    source = sources[target_name]
                    while len(source) <= cursor:
                        source.append("")
                    source[cursor] = line[1:]
                    cursor += 1
            self.assertEqual(set(sources), set(expected))
            for src_crlf in (False, True):
                for patch_crlf in (False, True):
                    for autocrlf in ("false", "true"):
                        with self.subTest(patch=filename, source_crlf=src_crlf, patch_crlf=patch_crlf, autocrlf=autocrlf):
                            with tempfile.TemporaryDirectory(prefix="trkv-patch-test-") as tmp:
                                bn = Path(tmp)
                                (bn / "src").mkdir()
                                subprocess.run(["git", "init", "-q", tmp], check=True)
                                subprocess.run(["git", "-C", tmp, "config", "core.autocrlf", autocrlf], check=True)
                                for target_name, lines in sources.items():
                                    source = ("\n".join(lines) + "\n").encode()
                                    target = bn / target_name
                                    target.write_bytes(source.replace(b"\n", b"\r\n") if src_crlf else source)
                                patch_path = bn / "fix.patch"
                                patch_path.write_bytes(patch.replace(b"\n", b"\r\n") if patch_crlf else patch)
                                apply_engine_patch(bn, patch_path)
                                for target_name, marker in expected.items():
                                    self.assertIn(marker, (bn / target_name).read_text(encoding="utf-8"))



if __name__ == "__main__":
    unittest.main()
