#!/usr/bin/env python3
"""Translate proven BN-compatible constructs; retain and report unresolved ones."""
import argparse
import ast
import collections
import json
import math
import operator
import re
from pathlib import Path
from compile_math import compile_expression


def constant(expression):
    """Evaluate arithmetic literals only; never execute source text."""
    operations = {ast.Add: operator.add, ast.Sub: operator.sub,
                  ast.Mult: operator.mul, ast.Div: operator.truediv}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ceil" and len(node.args) == 1 and not node.keywords:
            return math.ceil(visit(node.args[0]))
        raise ValueError("Not constant arithmetic")

    return visit(ast.parse(expression, mode="eval").body)


def expand_eocs(value, definitions, counts, variables=None, stack=()):
    variables = variables or {}
    if isinstance(value, list):
        return [expand_eocs(entry, definitions, counts, variables, stack) for entry in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"context_val"} and value["context_val"] in variables:
        return variables[value["context_val"]]
    if "run_eocs" in value:
        if set(value) - {'run_eocs', 'variables'}:
            raise ValueError('Scheduled or extended EOC calls require native lifecycle support')
        names = value["run_eocs"]
        names = [names] if isinstance(names, str) else names
        context = {**variables, **value.get("variables", {})}
        effects = []
        for name in names:
            if not isinstance(name, str):
                raise ValueError('Inline EOC definitions require native lifecycle support')
            if name not in definitions or name in stack:
                raise ValueError(f"Unknown or recursive EOC: {name}")
            definition = definitions[name]
            if definition.get('eoc_type', 'ACTIVATION') != 'ACTIVATION' or 'recurrence' in definition:
                raise ValueError(f'Non-activation EOC requires native lifecycle support: {name}')
            if not isinstance(definition.get('condition', {}), dict):
                raise ValueError(f'Conditional EOC cannot be statically expanded: {name}')
            required = definition.get("condition", {}).get("expects_vars", [])
            if set(required) - context.keys():
                raise ValueError(f"Missing EOC context for {name}")
            if definition.get("condition", {}) and (not required or set(definition['condition']) != {'expects_vars'}):
                raise ValueError(f"Conditional EOC cannot be statically expanded: {name}")
            expanded = expand_eocs(definition["effect"], definitions, counts, context, stack + (name,))
            for entry in expanded if isinstance(expanded, list) else [expanded]:
                effects.extend(entry if isinstance(entry, list) else [entry])
            counts["inlined_eoc_calls"] += 1
        return effects
    result = {}
    for key, entry in value.items():
        if key == "math":
            expressions = []
            for expression in entry:
                if isinstance(expression, str):
                    for name, literal in variables.items():
                        if type(literal) in (int, float):
                            expression = re.sub(r"\b_" + re.escape(name) + r"\b", str(literal), expression)
                expressions.append(expression)
            result[key] = expressions
        else:
            expanded = expand_eocs(entry, definitions, counts, variables, stack)
            if key == "effect" and isinstance(expanded, list):
                expanded = [part for item in expanded for part in (item if isinstance(item, list) else [item])]
            result[key] = expanded
    return result


def adapt(value, counts):
    if isinstance(value, dict) and set(value) == {"concatenate"}:
        counts["dynamic_line_concatenation"] += 1
        return {"and": adapt(value["concatenate"], counts)}
    if isinstance(value, dict) and ("yes" in value or "no" in value):
        # Conditional dynamic lines contain the predicate and both text arms in
        # one object. Translate the predicate without discarding either arm.
        predicate = {key: entry for key, entry in value.items() if key not in {"yes", "no"}}
        if predicate:
            translated = adapt(predicate, counts)
            return {**translated, **{key: adapt(value[key], counts) for key in ("yes", "no") if key in value}}
    if isinstance(value, list):
        return [adapt(entry, counts) for entry in value]
    if not isinstance(value, dict):
        return value
    if "math" in value and len(value["math"]) == 1:
        expression = value["math"][0]
        if isinstance(expression, str):
            skill = re.fullmatch(r"u_skill\('([a-zA-Z0-9_]+)'\)\s*>=\s*(\d+)", expression.strip())
            if skill:
                counts["native_skill_threshold"] += 1
                return {"u_has_skill": {"skill": skill[1], "level": int(skill[2])}}
            match = re.fullmatch(r"u_(\w+)\s*(==|!=|>=|<=|>|<|\+=|-=|=)\s*(.+)", expression)
            if match:
                name, operation, rhs = match.groups()
                try:
                    number = constant(rhs)
                except (ValueError, SyntaxError, ZeroDivisionError):
                    number = None
                if number is not None and math.isfinite(number):
                    if operation == "=":
                        counts["constant_numeric_assignment"] += 1
                        return {"u_add_var": name, "value": str(number)}
                    # BN's adjustment/comparison handlers use stoi on the old
                    # variable, discarding fractional artisan credit. Keep all
                    # reads and updates in the native numeric bridge.
            compiled = compile_expression(expression)
            counts["native_expression"] += 1
            if compiled.get('target_kind') == 'npc_opinion':
                compiled.pop('target_kind')
                return {'dda_set_npc_opinion': compiled}
            if "target" in compiled:
                return {"dda_set_variable": compiled}
            return {"dda_expression": compiled["expression"]}
    for source in ("set_string_var", "copy_var"):
        target = value.get("target_var", {})
        if source == 'set_string_var' and isinstance(value.get(source), str) and set(target) == {'global_val'}:
            if set(value) != {'set_string_var', 'target_var'}:
                raise ValueError('Extended global string assignment requires separate support')
            counts['global_string_assignment'] += 1
            return {'dda_set_global_string': {'target': target['global_val'], 'value': value[source]}}
        if source in value and isinstance(value[source], str) and set(target) == {"u_val"}:
            counts["constant_string_assignment"] += 1
            return {"u_add_var": target["u_val"], "value": value[source]}
    if "compare_string" in value:
        operands = value["compare_string"]
        if len(operands) == 2:
            literal = next((part for part in operands if isinstance(part, str)), None)
            variable = next((part for part in operands if isinstance(part, dict)), None)
            if literal is not None and variable is not None and len(variable) == 1:
                if 'global_val' in variable and isinstance(variable['global_val'], str):
                    counts['global_string_equality'] += 1
                    return {'dda_global_string': {'name': variable['global_val'], 'value': literal}}
                for source, target in [("u_val", "u_has_var"), ("npc_val", "npc_has_var")]:
                    if source in variable and isinstance(variable[source], str):
                        counts["string_equality"] += 1
                        return {target: variable[source], "value": literal}
    result = {key: adapt(entry, counts) for key, entry in value.items()}
    if "u_assign_activity" in result:
        if set(result) != {"u_assign_activity", "duration"} or result["u_assign_activity"] != "ACT_MEASURE" or result["duration"] != "10 minutes":
            raise ValueError(f"Unported activity effect: {result}")
        counts["dda_assign_activity"] += 1
        return {"dda_assign_activity": {"activity": "ACT_MEASURE", "duration_seconds": 600}}
    if "u_add_faction_trust" in result:
        if set(result) != {"u_add_faction_trust"} or type(result["u_add_faction_trust"]) is not int:
            raise ValueError(f"Unported faction trust effect: {result}")
        counts["dda_add_faction_trust"] += 1
        return {"dda_add_faction_trust": result["u_add_faction_trust"]}
    if "u_set_fac_relation" in result:
        if set(result) - {"u_set_fac_relation", "set_value_to"} or not isinstance(result["u_set_fac_relation"], str):
            raise ValueError(f"Unported faction relationship: {result}")
        counts["dda_set_faction_relation"] += 1
        return {"dda_set_faction_relation": {"relation": result["u_set_fac_relation"],
                                              "enabled": result.get("set_value_to", True)}}
    def item_reference(item):
        if isinstance(item, str):
            return {"id": item}
        if isinstance(item, dict) and set(item) == {"u_val"}:
            return {"variable": item["u_val"]}
        raise ValueError(f"Unsupported artisan item reference: {item}")

    def item_count(count):
        if type(count) in (int, float):
            return {"op": "literal", "value": count}
        if isinstance(count, dict) and set(count) == {"u_val"}:
            return {"op": "variable", "name": count["u_val"]}
        if isinstance(count, dict) and set(count) == {"dda_expression"}:
            return count["dda_expression"]
        raise ValueError(f"Unsupported artisan item count: {count}")

    if "switch" in result and isinstance(result["switch"], dict):
        if set(result) != {"switch", "cases"}:
            raise ValueError(f"Unported switch options: {result}")
        cases = []
        for entry in result["cases"]:
            if set(entry) != {"case", "effect"}:
                raise ValueError(f"Unported case options: {entry}")
            cases.append({"threshold": item_count(entry["case"]), "effect": entry["effect"]})
        counts["dda_switch"] += 1
        return {"dda_switch": {"expression": item_count(result["switch"]), "cases": cases}}

    for source, target in [("u_spawn_item", "dda_give_item"),
                           ("u_sell_item", "dda_transfer_item")]:
        if source in result and (source == "u_spawn_item" or isinstance(result.get("count"), dict)):
            allowed = {source, "count"}
            if source == "u_spawn_item":
                allowed.add("container")
            if set(result) - allowed:
                raise ValueError(f"Unported item effect options: {result}")
            counts[target] += 1
            specification = {"item": item_reference(result[source]),
                             "count": item_count(result.get("count", 1))}
            if "container" in result:
                if not isinstance(result["container"], str) or not result["container"]:
                    raise ValueError("Reward container must be a nonempty static ID")
                specification["container"] = result["container"]
                counts["contained_reward"] += 1
            return {target: specification}
    if "u_has_items" in result and isinstance(result["u_has_items"].get("count"), dict):
        specification = result["u_has_items"]
        if set(specification) != {"item", "count"} or set(result) != {"u_has_items"}:
            raise ValueError(f"Unported item condition options: {result}")
        counts["dda_has_items"] += 1
        return {"dda_has_items": {"item": item_reference(specification["item"]),
                                  "count": item_count(specification["count"])}}
    if result.get("type") == "npc" and result.get("mission") == "SHOPKEEP":
        result["mission"] = 3
        counts["npc_shopkeep_enum"] += 1
    if result.get("type") == "npc" and result.get("mission") == "GUARD_PATROL":
        result["mission"] = 8
        counts["npc_guard_patrol_enum"] += 1
    if result.get("type") == "npc" and result.get("mission") == "GUARD":
        result["mission"] = 7
        counts["npc_guard_enum"] += 1
    if result.get("type") == "npc_class":
        groups = result.get("shopkeeper_item_group")
        if isinstance(groups, list) and len(groups) == 1 and "group" in groups[0]:
            unsupported = set(groups[0]) - {"group", "rigid"}
            if unsupported:
                raise ValueError(f"Unsupported shop group options: {sorted(unsupported)}")
            result["dda_shop_rigid"] = groups[0].get("rigid", False)
            result["dda_shop_restock_interval"] = result.pop("restock_interval", "6 days")
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
                   "u_add_faction_trust",
                   "u_spawn_item", "set_string_var", "copy_var", "u_assign_activity"}

    def inspect(value):
        if isinstance(value, dict):
            for key, entry in value.items():
                if key in unsupported:
                    unresolved[key] += 1
                inspect(entry)
        elif isinstance(value, list):
            for entry in value:
                inspect(entry)

    sources = {source: json.loads(source.read_text()) for source in sorted(args.source.rglob("*.json"))}
    definitions = {entry["id"]: entry for entries in sources.values() for entry in entries if entry.get("type") == "effect_on_condition"}
    for source, entries in sources.items():
        entries = [entry for entry in entries if entry.get("type") != "effect_on_condition"]
        data = adapt(expand_eocs(entries, definitions, counts), counts)
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
