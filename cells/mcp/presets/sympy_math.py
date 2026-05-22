"""Symbolic math: simplify, solve, differentiate, integrate, evaluate (sympy)."""

SCHEMA = {
    "name": "sympy_math",
    "description": "Symbolic algebra/calculus. actions: simplify, solve, diff, integrate, evaluate.",
    "parameters": {
        "action": {"type": "string", "enum": ["simplify", "solve", "diff", "integrate", "evaluate"]},
        "expression": {"type": "string"}, "variable": {"type": "string"},
    },
    "required": ["expression"],
}


def handle(args: dict) -> dict:
    expr = (args.get("expression") or args.get("expr") or "").strip()
    if not expr:
        return {"error": "missing_expression"}
    action = args.get("action", "simplify")
    var = args.get("variable", "x")
    try:
        import sympy
        sym = sympy.symbols(var)
        e = sympy.sympify(expr)
        if action == "simplify":
            res = sympy.simplify(e)
        elif action == "solve":
            res = sympy.solve(e, sym)
        elif action == "diff":
            res = sympy.diff(e, sym)
        elif action == "integrate":
            res = sympy.integrate(e, sym)
        elif action == "evaluate":
            res = sympy.N(e)
        else:
            return {"error": "unknown_action", "action": action}
        return {"action": action, "input": expr, "result": str(res)}
    except Exception as e:
        return {"error": str(e), "expression": expr}
