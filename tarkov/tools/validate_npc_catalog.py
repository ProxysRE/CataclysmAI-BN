"""Validate the current technical combat classes, including inherited definitions.

This checks project authoring rules, not BN item compatibility or runtime behavior.
"""
import json
from pathlib import Path


def validate(entries: list[dict]) -> None:
    classes, groups = {}, set()
    for entry in entries:
        if entry.get("type") == "npc_class":
            ident = entry["id"]
            if ident in classes:
                raise ValueError(f"Duplicate NPC class: {ident}")
            classes[ident] = entry
        elif entry.get("type") == "item_group":
            groups.add(entry["id"])

    def resolve(ident, chain=()):
        if ident in chain or ident not in classes:
            raise ValueError(f"Invalid NPC inheritance: {chain} -> {ident}")
        current = classes[ident]
        if current.get("traits", "EMPTY_GROUP") != "EMPTY_GROUP" or any(
            current.get(key) for key in ("mutation_rounds", "bionics", "spells")
        ):
            raise ValueError(f"{ident}: non-project traits/mutations/bionics/spells in inheritance")
        for skill in current.get("skills", []):
            level = skill.get("level")
            if ("bonus" in skill or not isinstance(level, dict) or set(level) != {"constant"}
                    or type(level["constant"]) is not int or level["constant"] < 0):
                raise ValueError(f"{ident}: random/bonus skill distribution in inheritance")
        parent = current.get("copy-from")
        # Our checked fields are complete objects/lists when overridden. This is
        # deliberately not a general implementation of BN's JSON inheritance.
        return {**(resolve(parent, (*chain, ident)) if parent else {}), **current}

    def bounded_fields(owner, data, fields, low, high):
        if not isinstance(data, dict) or set(data) != set(fields):
            raise ValueError(f"{owner}: incomplete/unknown profile fields")
        if any(type(v) is not int or not low <= v <= high for v in data.values()):
            raise ValueError(f"{owner}: profile value outside {low}..{high}")

    combat = [name for name in classes if name.startswith("TRKV_COMBAT_")]
    if not combat:
        raise ValueError("No technical combat classes")
    for ident in combat:
        definition = resolve(ident)
        profile = definition.get("attribute_profile")
        if not isinstance(profile, dict) or set(profile) != {"stats", "personality", "hit_points"}:
            raise ValueError(f"{ident}: combat class requires a complete attribute profile")
        bounded_fields(ident, profile["stats"], ("strength", "dexterity", "intelligence", "perception"), 1, 100)
        bounded_fields(ident, profile["personality"], ("aggression", "bravery", "collector", "altruism"), -100, 100)
        bounded_fields(ident, profile["hit_points"], ("head", "torso", "arm_l", "arm_r", "leg_l", "leg_r"), 1, 10000)
        for field in ("weapon_override", "worn_override", "carry_override"):
            group = definition.get(field)
            if group not in groups and not (field == "carry_override" and group == "EMPTY_GROUP"):
                raise ValueError(f"{ident}: missing project {field}; vanilla fallback is forbidden")
        skills = definition.get("skills", [])
        if not skills or skills[0] != {"skill": "ALL", "level": {"constant": 0}}:
            raise ValueError(f"{ident}: skills must start with explicit ALL=0")
    for entry in entries:
        if entry.get("type") == "npc" and str(entry.get("class", "")).startswith("TRKV_COMBAT_"):
            resolve(entry["class"])


def check_directory(directory: Path) -> None:
    entries = [entry for path in directory.glob("*.json") for entry in json.loads(path.read_text())]
    validate(entries)


if __name__ == "__main__":
    check_directory(Path(__file__).resolve().parents[1] / "mods/trkv_raid_core")
    print("PASS controlled combat NPC profiles, inheritance and project equipment references")
