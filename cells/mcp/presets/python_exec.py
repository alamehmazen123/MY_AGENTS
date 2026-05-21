"""cells/mcp/presets/python_exec.py — Sandboxed Python execution in isolated worker."""
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

SCHEMA = {
    "name": "python_exec",
    "description": "Execute Python code safely with restricted builtins.",
    "parameters": {"code": {"type": "string"}},
    "required": ["code"],
}


def handle(args: dict) -> dict:
    code = args.get("code", "")
    if not code:
        return {"error": "missing_code"}
    try:
        safe_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
                "bytearray": bytearray, "bytes": bytes, "chr": chr, "dict": dict,
                "divmod": divmod, "enumerate": enumerate, "filter": filter,
                "float": float, "format": format, "frozenset": frozenset,
                "hasattr": hasattr, "hash": hash, "hex": hex, "id": id,
                "int": int, "isinstance": isinstance, "issubclass": issubclass,
                "iter": iter, "len": len, "list": list, "map": map, "max": max,
                "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
                "print": print, "range": range, "repr": repr, "reversed": reversed,
                "round": round, "set": set, "slice": slice, "sorted": sorted,
                "str": str, "sum": sum, "tuple": tuple, "type": type, "zip": zip,
            }
        }
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, safe_globals, {})
        return {"stdout": stdout_buffer.getvalue(), "stderr": stderr_buffer.getvalue()}
    except Exception:
        return {"error": traceback.format_exc()}
