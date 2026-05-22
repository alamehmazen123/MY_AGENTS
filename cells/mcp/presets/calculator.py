"""Evaluate arithmetic expressions safely (no eval, no network)."""
import ast
import math
import operator

SCHEMA = {
    "name": "calculator",
    "description": "Safely evaluate a math expression, e.g. '2*(3+4)**2 / 7'.",
    "parameters": {"expression": {"type": "string"}},
    "required": ["expression"],
}

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
    "floor": math.floor, "ceil": math.ceil, "abs": abs, "round": round,
    "factorial": math.factorial, "fabs": math.fabs, "pow": pow,
}
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("only numbers allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("unsupported expression element")


def handle(args: dict) -> dict:
    expr = (args.get("expression") or args.get("expr") or "").strip()
    if not expr:
        return {"error": "missing_expression"}
    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval(tree.body)
        return {"expression": expr, "result": result}
    except Exception as e:
        return {"error": str(e), "expression": expr}
