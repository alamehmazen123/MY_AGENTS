"""cells/mcp/presets/dependency_inspector.py — Parse dependency manifests."""
import json
from pathlib import Path
from kernel.config import settings


def handle(args: dict) -> dict:
    path_str = args.get("path", str(settings.workspace_root))
    try:
        p = Path(path_str).expanduser().resolve()
        workspace = settings.workspace_root.expanduser().resolve()
        if not (str(p).startswith(str(workspace)) or str(p).startswith(str(Path.home()))):
            return {"error": "path_not_allowed"}

        deps = {}
        req = p / "requirements.txt"
        if req.exists():
            deps["requirements_txt"] = [
                line.strip() for line in req.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
        pkg = p / "package.json"
        if pkg.exists():
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps["package_json"] = {
                "dependencies": list(data.get("dependencies", {}).keys()),
                "devDependencies": list(data.get("devDependencies", {}).keys()),
            }
        pyproject = p / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                deps["pyproject_toml"] = {
                    "dependencies": list(data.get("project", {}).get("dependencies", [])),
                }
            except Exception:
                pass
        return {"path": str(p), "dependencies": deps}
    except Exception as e:
        return {"error": str(e)}
