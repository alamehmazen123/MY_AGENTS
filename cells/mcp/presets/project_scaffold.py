"""cells/mcp/presets/project_scaffold.py — Create project skeletons (workspace-jailed)."""
from pathlib import Path
from kernel.security.workspace_guard import WorkspaceGuard, WorkspaceViolation
from kernel.config import settings

_guard = WorkspaceGuard(settings.workspace_root)

TEMPLATES = {
    "python": {
        "dirs": ["src", "tests", "docs"],
        "files": {"README.md": "# Project\n", "requirements.txt": "", "src/__init__.py": ""}
    },
    "node": {
        "dirs": ["src", "tests", "public"],
        "files": {"README.md": "# Project\n", "package.json": '{"name": "project", "version": "1.0.0"}', "src/index.js": ""}
    }
}

SCHEMA = {
    "name": "project_scaffold",
    "description": "Generate project templates inside the workspace.",
    "parameters": {
        "template": {"type": "string", "enum": ["python", "node"]},
        "name": {"type": "string"},
        "path": {"type": "string"},
    },
    "required": [],
}


def handle(args: dict) -> dict:
    template = args.get("template", "python")
    name = args.get("name", "new_project")
    try:
        base = _guard.validate(args.get("path", str(settings.workspace_root)))
        target = base / name
        target.mkdir(parents=True, exist_ok=True)
        spec = TEMPLATES.get(template, TEMPLATES["python"])
        for d in spec.get("dirs", []):
            (target / d).mkdir(parents=True, exist_ok=True)
        for fpath, content in spec.get("files", {}).items():
            f = target / fpath
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
        return {"created": str(target), "template": template}
    except WorkspaceViolation as e:
        return {"error": "workspace_violation", "message": str(e)}
    except Exception as e:
        return {"error": str(e)}
