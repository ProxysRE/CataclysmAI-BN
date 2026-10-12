#!/usr/bin/env python3
"""Prepare an additive island-prison port; retain unsupported definitions verbatim."""
import collections
import copy
import hashlib
import json
from pathlib import Path
from adapt_dialogue import adapt

root = Path(__file__).resolve().parent / "island_prison"
manifest = json.loads((root / "SOURCE_MANIFEST.json").read_text())
counts = collections.Counter()
blockers = []
types = collections.Counter()
for relative, digest in manifest["files"].items():
    source = root / "upstream" / relative
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Source checksum mismatch: {relative}")
    entries = json.loads(source.read_text())
    result = []
    for original in entries:
        types[original["type"]] += 1
        entry = copy.deepcopy(original)
        if relative.endswith("npcs/island_prison/prisoners.json"):
            try:
                entry = adapt(entry, counts)
            except ValueError as error:
                blockers.append({"id": original.get("id"), "reason": str(error),
                                 "source_preserved": True})
        if entry["type"] == "mapgen":
            entry["method"] = "json"
        if entry["type"] == "overmap_terrain":
            identifiers = entry["id"]
            for identifier in identifiers:
                if not identifier.startswith(("prison_island", "prison_alcatraz")):
                    continue
                variant = copy.deepcopy(entry)
                variant["id"] = identifier
                variant.pop("vision_levels", None)
                variant["see_cost"] = 5
                result.append(variant)
            continue
        result.append(entry)
    target = root / "staging" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
report = {"definitions": dict(types), "translated": dict(counts),
          "blocked_definitions": blockers,
          "required_reviews": ["faction food/relations/epilogues schema",
                               "mapgen and overmap placement dependencies", "item/trait dependency closure"],
          "runtime_validated": False, "release_ready": False}
(root / "ADAPTATION_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
