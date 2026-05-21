"""cells/mcp/presets/code_analyzer.py — AST-based code analysis (workspace-jailed)."""
import ast
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

SCHEMA = {
    "name": "code_analyzer",
    "description": "Parse Python files and extract functions, classes, and imports.",
    "parameters": {"path": {"type": "string"}},
    "required": ["path"],
}


def handle(args: dict) -> dict:
    path_str = args.get("path", "")
    if not path_str:
        return {"error": "missing_path"}
    try:
        p = _guard.validate(path_str)
        if not p.exists() or not p.is_file():
            return {"error": "file_not_found", "path": str(p)}

        content = p.read_text(encoding="utf-8", errors="replace")
        result = {
            "path": str(p),
            "lines": len(content.splitlines()),
            "chars": len(content),
            "functions": [],
            "classes": [],
            "imports": [],
            "syntax_error": None,
        }
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result["functions"].append({"name": node.name, "line": node.lineno})
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append({"name": node.name, "line": node.lineno})
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        result["imports"].append(alias.name)
        except SyntaxError as e:
            result["syntax_error"] = str(e)
        return result
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
