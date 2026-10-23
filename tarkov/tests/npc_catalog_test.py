"""Reject accidental fallback/randomization in inherited project combat data."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_npc_catalog import validate

entries = [entry for path in (ROOT / "mods/trkv_raid_core").glob("*.json")
           for entry in json.loads(path.read_text())]
validate(entries)


def rejected(change):
    broken = deepcopy(entries)
    classes = {entry["id"]: entry for entry in broken if entry["type"] == "npc_class"}
    change(broken, classes)
    try:
        validate(broken)
    except ValueError:
        return
    raise AssertionError("Invalid combat catalog was accepted")


rejected(lambda _, c: c["TRKV_COMBAT_TEST"].pop("weapon_override"))
rejected(lambda _, c: c["TRKV_COMBAT_FIELD"].update(carry_override="missing_project_group"))
rejected(lambda _, c: c["TRKV_COMBAT_TEST"]["attribute_profile"]["hit_points"].pop("head"))
rejected(lambda _, c: c["TRKV_COMBAT_TEST"]["skills"][1].update(level={"rng": [1, 6]}))
rejected(lambda _, c: c["TRKV_COMBAT_TEST"].update(**{"copy-from": "TRKV_COMBAT_FIELD"}))
rejected(lambda _, c: c["TRKV_COMBAT_FIELD"].update(**{"copy-from": "missing_class"}))
for field, value in (("traits", "NPC_RANDOM"), ("bionics", [{"id": "bio_power_storage", "chance": 100}]),
                     ("mutation_rounds", {"ANY": {"constant": 1}}), ("spells", [{"id": "unwanted_spell"}])):
    def change(data, classes, field=field, value=value):
        # A child empty value must not hide an additive inherited BN definition.
        parent = {"type": "npc_class", "id": "foreign_parent", field: value}
        data.append(parent)
        classes["TRKV_COMBAT_TEST"]["copy-from"] = "foreign_parent"
        classes["TRKV_COMBAT_TEST"][field] = "EMPTY_GROUP" if field == "traits" else []
    rejected(change)
print("PASS combat catalog rejects fallback, missing HP, random skills, cycles and inherited modifiers")
