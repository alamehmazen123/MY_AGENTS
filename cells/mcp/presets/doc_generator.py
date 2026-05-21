"""cells/mcp/presets/doc_generator.py — Extract docstrings and signatures."""
import ast
from pathlib import Path


def handle(args: dict) -> dict:
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = Path(path_str).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return {"error": "file_not_found"}
        content = p.read_text(encoding="utf-8", errors="replace")
        docs = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    docs.append({
                        "name": node.name,
                        "type": type(node).__name__,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                    })
        except SyntaxError:
            pass
        return {"path": str(p), "docs": docs, "count": len(docs)}
    except Exception as e:
        return {"error": str(e)}
