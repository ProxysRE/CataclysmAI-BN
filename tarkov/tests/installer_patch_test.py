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
            ("0005-dimension-random-npc-policy.patch", {"src/world_type.h": "bool allow_random_npcs = true;",
             "src/world_type.cpp": '"allow_random_npcs"', "src/game.cpp": "!info->world_type->allow_random_npcs"}),
            ("0006-dimension-mapgen-npc-policy.patch", {"src/world_type.h": "bool allow_mapgen_npcs = true;",
             "src/world_type.cpp": '"allow_mapgen_npcs"', "src/game.cpp": "world_types::infer_from_dimension( current_dimension_id_ )",
             "src/mapgen/mapgen.cpp": "!world->allow_mapgen_npcs"}),
            ("0007-disable-vanilla-starting-npcs.patch", {"src/game.cpp": "bool game::uses_tarkov_npc_roster()",
             "src/game.h": "void create_profession_npcs( const std::vector<npc_class_id> &classes );"}),
            ("0008-probe-npc-spawn-position.patch", {"src/catalua_bindings_game_creatures.cpp":
             '"can_place_npc_at"'}),
            ("0009-immediate-npc-hazard-action.patch", {"src/npc.h": "std::string avoid_immediate_danger();",
             "src/npcmove.cpp": "std::string npc::avoid_immediate_danger()",
             "src/catalua_bindings_creature.cpp": "SET_FX_T( avoid_immediate_danger"}),
            ("0010-anonymous-npc-hearing.patch", {"src/npctalk.cpp": 'set_value( "trkv_heard_noise"'}),
            ("0011-reachable-npc-area-entry.patch", {"src/catalua_bindings_creature.cpp": '"choose_area_entry"'}),
            ("0012-visible-npc-standoff-position.patch", {"src/catalua_bindings_creature.cpp": '"choose_standoff_position"'}),
            ("0013-npc-reload-cover.patch", {"src/catalua_bindings_creature.cpp": '"choose_reload_cover"'}),
            ("0014-creature-visibility-query.patch", {"src/catalua_bindings_creature.cpp": '"sees_creature"'}),
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
                                    target.parent.mkdir(parents=True, exist_ok=True)
                                    target.write_bytes(source.replace(b"\n", b"\r\n") if src_crlf else source)
                                patch_path = bn / "fix.patch"
                                patch_path.write_bytes(patch.replace(b"\n", b"\r\n") if patch_crlf else patch)
                                apply_engine_patch(bn, patch_path)
                                for target_name, marker in expected.items():
                                    self.assertIn(marker, (bn / target_name).read_text(encoding="utf-8"))



if __name__ == "__main__":
    unittest.main()
