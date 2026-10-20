"""Fast data checks and lifecycle failure tests; NOT a substitute for BN execution."""
import json
from pathlib import Path

from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "tarkov/mods/trkv_raid_core"


def main() -> None:
    for path in MOD.glob("*.json"):
        assert isinstance(json.loads(path.read_text()), list), path
    for definition in json.loads((MOD / "mapgen.json").read_text()):
        obj = definition["object"]
        rows = obj["rows"]
        assert len(rows) == 24 and all(len(row) == 24 for row in rows)
        assert set("".join(rows)) <= set(obj["terrain"])
        # Check four-way reachability before any engine/pathfinding assumptions.
        start = (12, 12) if definition["om_terrain"] == ["trkv_test_home"] else (3, 3)
        visited, pending = {start}, [start]
        while pending:
            x, y = pending.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < 24 and 0 <= ny < 24 and rows[ny][nx] != "#" and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    pending.append((nx, ny))
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell in "DEL":
                    assert (x, y) in visited, (definition["om_terrain"], cell)
    runtime = LuaRuntime(unpack_returned_tuples=True)
    for path in [*MOD.glob("*.lua"), *(ROOT / "tarkov/tests").glob("*.lua")]:
        runtime.execute("assert(load(...))", path.read_text())
    # The tests use repository-relative dofile paths.
    import os
    os.chdir(ROOT)
    runtime.execute((ROOT / "tarkov/tests/lifecycle_test.lua").read_text())
    print("PASS JSON structure, map dimensions, symbol coverage, connectivity and Lua 5.4 syntax")


if __name__ == "__main__":
    main()
