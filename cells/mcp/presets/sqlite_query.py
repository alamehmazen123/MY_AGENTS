"""Run a read-only SQL query against a local SQLite database file."""
import sqlite3

SCHEMA = {
    "name": "sqlite_query",
    "description": "Run a read-only SQL query on a local SQLite .db file.",
    "parameters": {"path": {"type": "string"}, "query": {"type": "string"}},
    "required": ["path", "query"],
}


def handle(args: dict) -> dict:
    path = args.get("path", "")
    query = args.get("query", "")
    if not path or not query:
        return {"error": "missing_path_or_query"}
    try:
        # Open strictly read-only so a query can never modify the database.
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            cur = con.execute(query)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(r) for r in cur.fetchmany(200)]
        finally:
            con.close()
        return {"columns": cols, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"error": str(e), "path": path}
