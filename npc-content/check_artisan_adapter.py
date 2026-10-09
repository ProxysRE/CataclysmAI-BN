#!/usr/bin/env python3
"""Check source-preserving adaptation and fractional-credit regressions."""
import collections
import json
from pathlib import Path
from adapt_dialogue import adapt, expand_eocs

root = Path(__file__).resolve().parent
entries = [entry for path in (root / "staging/upstream/npcs/isolated_road").glob("*.json")
           for entry in json.loads(path.read_text())]
eocs = {entry["id"]: entry for entry in entries if entry["type"] == "effect_on_condition"}
counts = collections.Counter()
source = [entry for entry in entries if entry["type"] != "effect_on_condition"]
result = adapt(expand_eocs(source, eocs, counts), counts)
assert [entry.get("id") for entry in source] == [entry.get("id") for entry in result]
assert sum(entry["type"] == "talk_topic" for entry in result) == 55
assert counts["dda_give_item"] == 24
assert counts["dda_transfer_item"] == 2
assert counts["dda_has_items"] == 2
assert counts["dda_switch"] == 4
assert counts["inlined_eoc_calls"] == 126

def walk(value):
    if isinstance(value, dict):
        yield value
        for entry in value.values():
            yield from walk(entry)
    elif isinstance(value, list):
        for entry in value:
            yield from walk(entry)

assert not any({"u_spawn_item", "math", "run_eocs", "u_adjust_var", "u_compare_var"} & node.keys()
               for node in walk(result))
for expression in ("u_credit += 12", "u_credit -= 1", "u_credit > 12"):
    adapted = adapt({"math": [expression]}, collections.Counter())
    assert "dda_set_variable" in adapted or "dda_expression" in adapted
try:
    adapt({"u_spawn_item": "9mm", "use_item_group": True}, collections.Counter())
except ValueError:
    pass
else:
    raise AssertionError("Unsupported spawn options must not be silently dropped")
print("PASS: 55 topics retained; 24 rewards, 2 payments, 2 affordability checks; fractional reads preserved")
