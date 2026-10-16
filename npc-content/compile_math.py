#!/usr/bin/env python3
"""Compile the DDA arithmetic used by artisan services to a bounded expression IR.

No expressions are executed. Unsupported syntax fails explicitly. The output
requires the native BN compatibility layer; it is not stock BN JSON.
"""
import ast
import json
import re
import math


def compile_node(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return {"op": "literal", "value": node.value}
    if isinstance(node, ast.Name) and node.id in {'pi', 'π', 'e', 'true', 'false'}:
        return {'op': 'literal', 'value': {'pi': math.pi, 'π': math.pi, 'e': math.e, 'true': 1, 'false': 0}[node.id]}
    if isinstance(node, ast.Name) and node.id.startswith(("u_", "n_")):
        if node.id.startswith("n_"):
            return {"op": "variable", "name": node.id[2:], "actor": "npc"}
        return {"op": "variable", "name": node.id[2:]}
    if isinstance(node, ast.Name) and not node.id.startswith('_') and not (len(node.id) > 2 and node.id[1] == '_'):
        return {'op': 'variable', 'name': node.id, 'actor': 'global'}
    binary = {ast.Add: "add", ast.Sub: "subtract", ast.Mult: "multiply", ast.Div: "divide"}
    if isinstance(node, ast.BinOp) and type(node.op) in binary:
        return {"op": binary[type(node.op)], "args": [compile_node(node.left), compile_node(node.right)]}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return {"op": "negate", "args": [compile_node(node.operand)]}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return {"op": "not", "args": [compile_node(node.operand)]}
    comparisons = {ast.Eq: "equal", ast.NotEq: "not_equal", ast.Gt: "greater", ast.GtE: "greater_equal", ast.Lt: "less", ast.LtE: "less_equal"}
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in comparisons:
        return {"op": comparisons[type(node.ops[0])], "args": [compile_node(node.left), compile_node(node.comparators[0])]}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name in {'min', 'max', 'clamp'} and len(node.args) == (3 if name == 'clamp' else 2) and not node.keywords:
            return {'op': name, 'args': [compile_node(x) for x in node.args]}
        if name in {'n_npc_anger', 'n_npc_fear', 'n_npc_trust', 'n_npc_value'} and not node.args and not node.keywords:
            return {'op': 'npc_opinion', 'name': name.removeprefix('n_npc_')}
        if name in {"ceil", "has_var"} and len(node.args) == 1 and not node.keywords:
            argument = compile_node(node.args[0])
            if name == "has_var" and argument.get("op") != "variable":
                raise ValueError("has_var requires a variable")
            return {"op": name, "args": [argument]}
        if name == "time" and len(node.args) == 1 and not node.keywords and isinstance(node.args[0], ast.Constant):
            duration = node.args[0].value
            if duration == "now":
                return {"op": "now"}
            units = {'s': 1, 'second': 1, 'seconds': 1,
                     'm': 60, 'minute': 60, 'minutes': 60,
                     'h': 3600, 'hour': 3600, 'hours': 3600,
                     'd': 86400, 'day': 86400, 'days': 86400,
                     'week': 604800, 'weeks': 604800}
            match = re.fullmatch(r"(\d+)\s*([a-z]+)", str(duration))
            if match and match[2] in units:
                return {"op": "literal", "value": int(match[1]) * units[match[2]]}
        if name == "time_since" and len(node.args) == 1:
            variable = {'op': 'cataclysm'} if isinstance(node.args[0], ast.Constant) and node.args[0].value == 'cataclysm' else compile_node(node.args[0])
            if variable.get("op") not in {"variable", "cataclysm"}:
                raise ValueError("time_since requires a variable")
            units = {"seconds": 1, "hours": 3600, "days": 86400}
            unit = "seconds"
            for keyword in node.keywords:
                if keyword.arg != "unit" or not isinstance(keyword.value, ast.Constant) or keyword.value.value not in units:
                    raise ValueError("Unsupported time_since unit")
                unit = keyword.value.value
            return {"op": "divide", "args": [{"op": "subtract", "args": [{"op": "now"}, variable]}, {"op": "literal", "value": units[unit]}]}
    raise ValueError(f"Unsupported DDA arithmetic: {ast.dump(node)}")


def compile_expression(expression):
    expression = re.sub(r"'unit'\s*:", "unit=", expression.strip())
    if expression.startswith("!"):
        expression = "not " + expression[1:]
    opinion = re.fullmatch(r"(n_npc_(anger|fear|trust|value)\(\))\s*(\+\+|--|\+=|-=|=(?!=))\s*(.*)", expression)
    if opinion:
        target, field, operation, rhs = opinion.groups()
        if operation in ('++', '--'):
            if rhs:
                raise ValueError('Unexpected operand after opinion increment')
            rhs = '1'
            operation = '+=' if operation == '++' else '-='
        compiled = compile_node(ast.parse(rhs, mode='eval').body)
        if operation != '=':
            compiled = {'op': 'add' if operation == '+=' else 'subtract',
                        'args': [{'op': 'npc_opinion', 'name': field}, compiled]}
        return {'target': field, 'target_kind': 'npc_opinion', 'expression': compiled}
    increment = re.fullmatch(r"([A-Za-z_]\w*)\s*(\+\+|--)", expression)
    if increment:
        expression = increment[1] + (" += 1" if increment[2] == "++" else " -= 1")
    assignment = re.fullmatch(r"([A-Za-z_]\w*)\s*(\+=|-=|=(?!=))\s*(.+)", expression)
    if assignment:
        target, operator, rhs = assignment.groups()
        compiled = compile_node(ast.parse(rhs, mode="eval").body)
        if operator != "=":
            compiled = {"op": "add" if operator == "+=" else "subtract", "args": [compile_node(ast.Name(id=target)), compiled]}
        target_node = compile_node(ast.Name(id=target))
        if target_node.get('op') != 'variable':
            raise ValueError('Assignment target must be a variable')
        result = {"target": target_node['name'], "expression": compiled}
        if 'actor' in target_node:
            result['actor'] = target_node['actor']
        return result
    return {"expression": compile_node(ast.parse(expression, mode="eval").body)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression")
    args = parser.parse_args()
    print(json.dumps(compile_expression(args.expression), indent=2))
