"""Read and preview a CSV or JSON file (columns, row count, sample rows)."""
import csv
import json
import os

SCHEMA = {
    "name": "csv_json",
    "description": "Read/preview a local .csv or .json file (columns, counts, sample rows).",
    "parameters": {"path": {"type": "string"}, "limit": {"type": "integer"}},
    "required": ["path"],
}


def handle(args: dict) -> dict:
    path = args.get("path", "")
    limit = int(args.get("limit", 50) or 50)
    if not path:
        return {"error": "missing_path"}
    if not os.path.isfile(path):
        return {"error": "file_not_found", "path": path}
    try:
        if path.lower().endswith(".json"):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {"type": "json_array", "count": len(data), "preview": data[:limit]}
            if isinstance(data, dict):
                return {"type": "json_object", "keys": list(data.keys()), "data": data}
            return {"type": "json", "data": data}
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        header = rows[0] if rows else []
        body = rows[1:]
        return {"type": "csv", "columns": header, "row_count": len(body), "preview": body[:limit]}
    except Exception as e:
        return {"error": str(e), "path": path}
