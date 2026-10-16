#!/usr/bin/env python3
"""Check source-preserving adaptation and fractional-credit regressions."""
import collections
import json
from pathlib import Path
from adapt_dialogue import adapt, expand_eocs
from compile_math import compile_expression

for expression, seconds in [("time('14 day')", 1209600), ("time('44 days')", 3801600),
                            ("time('30 minutes')", 1800), ("time('2 weeks')", 1209600),
                            ("time('14d')", 1209600)]:
    assert compile_expression(expression) == {'expression': {'op': 'literal', 'value': seconds}}
for field in ('anger', 'fear', 'trust', 'value'):
    read = {'op': 'npc_opinion', 'name': field}
    assert compile_expression(f'n_npc_{field}()') == {'expression': read}
    write = compile_expression(f'n_npc_{field}()++')
    assert write == {'target': field, 'target_kind': 'npc_opinion',
                     'expression': {'op': 'add', 'args': [read, {'op': 'literal', 'value': 1}]}}
    effect = adapt({'math': [f'n_npc_{field}() -= 2']}, collections.Counter())
    assert effect['dda_set_npc_opinion']['target'] == field
    assert effect['dda_set_npc_opinion']['expression']['op'] == 'subtract'
for expression in ("n_npc_anger(1)", "n_npc_anger()++ 2", "time('14 nonsense')", "time('now', unit='days')"):
    try:
        compile_expression(expression)
    except (ValueError, SyntaxError):
        pass
    else:
        raise AssertionError('Unsupported expression accepted: ' + expression)

root = Path(__file__).resolve().parent
for predicate in ({"math": ["u_done == 1"]}, {"compare_string": ["yes", {"u_val": "done"}]}):
    translated = adapt({**predicate, "yes": "accepted", "no": "waiting"}, collections.Counter())
    assert translated["yes"] == "accepted" and translated["no"] == "waiting"
entries = [entry for path in (root / "staging/upstream/npcs/isolated_road").glob("*.json")
           for entry in json.loads(path.read_text())]
eocs = {entry["id"]: entry for entry in entries if entry["type"] == "effect_on_condition"}
counts = collections.Counter()
source = [entry for entry in entries if entry["type"] != "effect_on_condition"]
result = adapt(expand_eocs(source, eocs, counts), counts)
def branch_count(value):
    if isinstance(value, dict):
        return sum(key in {"yes", "no"} for key in value) + sum(branch_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(branch_count(child) for child in value)
    return 0
assert branch_count(expand_eocs(source, eocs, collections.Counter())) == branch_count(result)
assert [entry.get("id") for entry in source] == [entry.get("id") for entry in result]
assert sum(entry["type"] == "talk_topic" for entry in result) == 55
assert counts["dda_give_item"] == 24
assert counts["dda_transfer_item"] == 2
assert counts["dda_has_items"] == 2
assert counts["dda_switch"] == 4
assert counts["dda_assign_activity"] == 1
assert counts["dda_add_faction_trust"] == 6
assert counts["dda_set_faction_relation"] == 2
assert counts["inlined_eoc_calls"] == 126
activity_source = json.loads((root / "activity_source.json").read_text())["definitions"][0]
activity_target = json.loads((root / "native/dda_artisan_activities.json").read_text())[0]
assert activity_source["based_on"] == "time"
assert activity_source["activity_level"] == "NO_EXERCISE"
for key in ("id", "type", "verb", "interruptable", "rooted", "refuel_fires", "auto_needs"):
    assert activity_source[key] == activity_target[key]
assert activity_target["no_resume"] is (not activity_source["can_resume"])

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
print("PASS: 55 topics; rewards/payments; fractional reads; 1 measurement action; 6 trust and 2 relation effects")

shops = [node for node in walk(result) if node.get("type") == "npc_class"]
assert len(shops) == 2
assert all(node["dda_shop_rigid"] is True for node in shops)
assert all(node["dda_shop_restock_interval"] == "6 days" for node in shops)
assert all(node["shopkeeper_consumption_rates"] == "basic_shop_rates" for node in shops)
try:
    adapt({"type":"npc_class", "shopkeeper_item_group":[{"group":"test", "rigid":True, "condition":True}]}, collections.Counter())
except ValueError:
    pass
else:
    raise AssertionError("Unsupported shop restrictions must not be silently dropped")
print("PASS: both artisan shops preserve rigid sampling and six-day restock; legacy metadata retained")

joined = adapt({"concatenate": [["A", "B"], ["1", "2", "3"]]}, collections.Counter())
assert joined == {"and": [["A", "B"], ["1", "2", "3"]]}
