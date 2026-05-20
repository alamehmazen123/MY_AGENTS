"""cells/mcp/presets/project_scaffold.py — Create project skeletons."""
from pathlib import Path
from kernel.config import settings

TEMPLATES = {
    "python": {
        "dirs": ["src", "tests", "docs"],
        "files": {
            "README.md": "# Project\n",
            "requirements.txt": "",
            "src/__init__.py": "",
        }
    },
    "node": {
        "dirs": ["src", "tests", "public"],
        "files": {
            "README.md": "# Project\n",
            "package.json": '{"name": "project", "version": "1.0.0"}',
            "src/index.js": "",
        }
    }
}


def handle(args: dict) -> dict:
    template = args.get("template", "python")
    name = args.get("name", "new_project")
    base = Path(args.get("path", str(settings.workspace_root))).expanduser().resolve()
    workspace = settings.workspace_root.expanduser().resolve()
    if not (str(base).startswith(str(workspace)) or str(base).startswith(str(Path.home()))):
        return {"error": "path_not_allowed"}

    target = base / name
    try:
        target.mkdir(parents=True, exist_ok=True)
        spec = TEMPLATES.get(template, TEMPLATES["python"])
        for d in spec.get("dirs", []):
            (target / d).mkdir(parents=True, exist_ok=True)
        for fpath, content in spec.get("files", {}).items():
            f = target / fpath
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
        return {"created": str(target), "template": template}
    except Exception as e:
        return {"error": str(e)}
