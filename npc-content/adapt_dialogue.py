#!/usr/bin/env python3
"""Translate proven BN-compatible constructs; retain and report unresolved ones."""
import argparse
import collections
import json
from pathlib import Path


def adapt(value, counts):
    if isinstance(value, list):
        return [adapt(entry, counts) for entry in value]
    if not isinstance(value, dict):
        return value
    if "compare_string" in value:
        operands = value["compare_string"]
        if len(operands) == 2:
            literal = next((part for part in operands if isinstance(part, str)), None)
            variable = next((part for part in operands if isinstance(part, dict)), None)
            if literal is not None and variable is not None and len(variable) == 1:
                for source, target in [("u_val", "u_has_var"), ("npc_val", "npc_has_var")]:
                    if source in variable and isinstance(variable[source], str):
                        counts["string_equality"] += 1
                        return {target: variable[source], "value": literal}
    result = {key: adapt(entry, counts) for key, entry in value.items()}
    if result.get("type") == "npc" and result.get("mission") == "SHOPKEEP":
        result["mission"] = 7
        counts["npc_shopkeep_enum"] += 1
    if result.get("type") == "npc_class":
        groups = result.get("shopkeeper_item_group")
        if isinstance(groups, list) and len(groups) == 1 and "group" in groups[0]:
            result["shopkeeper_item_group"] = groups[0]["group"]
            counts["shopkeeper_group"] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = collections.Counter()
    unresolved = collections.Counter()
    unsupported = {"math", "run_eocs", "queue_eocs", "u_set_fac_relation",
                   "u_consume_item", "u_add_faction_trust", "shopkeeper_consumption_rates"}

    def inspect(value):
        if isinstance(value, dict):
            for key, entry in value.items():
                if key in unsupported:
                    unresolved[key] += 1
                inspect(entry)
        elif isinstance(value, list):
            for entry in value:
                inspect(entry)

    for source in sorted(args.source.rglob("*.json")):
        data = adapt(json.loads(source.read_text()), counts)
        inspect(data)
        target = args.output / source.relative_to(args.source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    report = {"translated": dict(counts), "unresolved_retained": dict(unresolved),
              "release_ready": False}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ADAPTATION_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
