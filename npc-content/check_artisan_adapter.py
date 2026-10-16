#!/usr/bin/env python3
"""Check source-preserving adaptation and fractional-credit regressions."""
import collections
import json
from pathlib import Path
from adapt_dialogue import adapt, expand_eocs
from compile_math import compile_expression

assert adapt({'npc_at_om_location': 'lighthouse_ground'}, collections.Counter()) == {
    'dda_at_om_location': {'actor': 'npc', 'terrain': 'lighthouse_ground'}}
try:
    adapt({'u_at_om_location': 'FACTION_CAMP_ANY'}, collections.Counter())
except ValueError:
    pass
else:
    raise AssertionError('Unimplemented camp condition accepted')

global_read = {'op': 'variable', 'name': 'hub01_shared', 'actor': 'global'}
assert compile_expression('hub01_shared') == {'expression': global_read}
assert compile_expression('hub01_shared += 1')['expression']['args'][0] == global_read
assert compile_expression('hub01_shared++')['actor'] == 'global'
assert compile_expression('has_var(hub01_shared)')['expression']['args'] == [global_read]
assert compile_expression('true')['expression'] == {'op': 'literal', 'value': 1}
assert compile_expression('false')['expression'] == {'op': 'literal', 'value': 0}
assert compile_expression("time_since('cataclysm', 'unit':'days')")['expression']['args'][0]['args'][1] == {'op':'cataclysm'}
assert compile_expression('max(exodii_mission_wh_chance, 1)')['expression']['op'] == 'max'
assert compile_expression('clamp(u_count, 0, 200)')['expression']['op'] == 'clamp'
assert compile_expression('rng(1, 3)')['expression'] == {'op': 'rng', 'args': [{'op': 'literal', 'value': 1}, {'op': 'literal', 'value': 3}]}
assert compile_expression('rand(13)')['expression'] == {'op': 'rand', 'args': [{'op': 'literal', 'value': 13}]}
for text in ('rng(1)', 'rng(1, 2, 3)', 'rand(1, 2)', 'rand(upper=13)'):
    try:
        compile_expression(text)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid random function accepted: ' + text)
assert compile_expression('n_hub01_shared')['expression']['actor'] == 'npc'
global_line = adapt({'compare_string': ['yes', {'global_val': 'hub01_trade'}],
                     'yes': 'unlocked', 'no': 'locked'}, collections.Counter())
assert global_line == {'dda_global_string': {'name': 'hub01_trade', 'value': 'yes'},
                       'yes': 'unlocked', 'no': 'locked'}
single = {'single': {'id': 'single', 'effect': {'u_add_var': 'done', 'value': 'yes'}}}
assert expand_eocs({'run_eocs': 'single'}, single, collections.Counter()) == [single['single']['effect']]
for call, definitions in [({'run_eocs': 'single', 'time_in_future': '14 days'}, single),
                          ({'run_eocs': 'recurring'}, {'recurring': {'effect': [], 'eoc_type': 'RECURRING'}}),
                          ({'run_eocs': 'extended'}, {'extended': {'effect': [], 'recurrence': '1 hour'}})]:
    try:
        expand_eocs(call, definitions, collections.Counter(), {'x': 1})
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe EOC expansion accepted')
conditional = {'id': 'conditional', 'condition': {'math': ['hub01_shared == 1']},
               'effect': {'u_add_var': 'branch', 'value': 'yes'},
               'false_effect': {'u_add_var': 'branch', 'value': 'no'}}
expanded = expand_eocs({'run_eocs': [conditional]}, {}, collections.Counter())
assert expanded[0]['dda_if']['condition'] == conditional['condition']
assert expanded[0]['dda_if']['then']['effect'] == [conditional['effect']]
assert expanded[0]['dda_if']['else']['effect'] == [conditional['false_effect']]
outer = {**conditional, 'effect': [{'run_eocs':'single'}, {'run_eocs':'single'}]}
nested = expand_eocs({'run_eocs': [outer]}, single, collections.Counter())
assert nested[0]['dda_if']['then']['effect'] == [single['single']['effect']]*2
converted = adapt(expanded, collections.Counter())
assert converted[0]['dda_if']['condition']['dda_expression']['op'] == 'equal'
chance = adapt({'if': {'one_in_chance': {'global_val':'exodii_mission_wh_chance'}},
                'then': {'npc_add_var':'directions','value':'yes'},
                'else': {'npc_add_var':'directions','value':'no'}}, collections.Counter())
assert chance['dda_if']['condition']['dda_one_in_chance']['actor'] == 'global'
assert chance['dda_if']['else']['effect'][0]['value'] == 'no'
for expression in ('v_item', '_context', 'x_unknown', 'pi = 3'):
    try:
        compile_expression(expression)
    except ValueError:
        pass
    else:
        raise AssertionError('Unsupported scope accepted: ' + expression)

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
