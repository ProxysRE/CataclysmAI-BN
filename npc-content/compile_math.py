#!/usr/bin/env python3
"""Compile the DDA arithmetic used by artisan services to a bounded expression IR.

No expressions are executed. Unsupported syntax fails explicitly. The output
requires the native BN compatibility layer; it is not stock BN JSON.
"""
import ast
import json
import re


def compile_node(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return {"op": "literal", "value": node.value}
    if isinstance(node, ast.Name) and node.id.startswith("u_"):
        return {"op": "variable", "name": node.id[2:]}
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
        if name in {"ceil", "has_var"} and len(node.args) == 1 and not node.keywords:
            argument = compile_node(node.args[0])
            if name == "has_var" and argument.get("op") != "variable":
                raise ValueError("has_var requires a variable")
            return {"op": name, "args": [argument]}
        if name == "time" and len(node.args) == 1 and not node.keywords and isinstance(node.args[0], ast.Constant):
            duration = node.args[0].value
            if duration == "now":
                return {"op": "now"}
            match = re.fullmatch(r"(\d+)\s*(s|m|h|d)", str(duration))
            if match:
                return {"op": "literal", "value": int(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]}
        if name == "time_since" and len(node.args) == 1:
            variable = compile_node(node.args[0])
            if variable.get("op") != "variable":
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
    assignment = re.fullmatch(r"(u_\w+)\s*(\+=|-=|=(?!=))\s*(.+)", expression)
    if assignment:
        target, operator, rhs = assignment.groups()
        compiled = compile_node(ast.parse(rhs, mode="eval").body)
        if operator != "=":
            compiled = {"op": "add" if operator == "+=" else "subtract", "args": [{"op": "variable", "name": target[2:]}, compiled]}
        return {"target": target[2:], "expression": compiled}
    return {"expression": compile_node(ast.parse(expression, mode="eval").body)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression")
    args = parser.parse_args()
    print(json.dumps(compile_expression(args.expression), indent=2))
