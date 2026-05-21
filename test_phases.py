import asyncio
import httpx

async def phase5():
    print("=== PHASE 5: Agent-A via /api/prompt ===")
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {
            "prompt": "What is 2+2? Answer with one word.",
            "model": "deepseek-coder:1.3b",
            "system": "Be concise.",
            "no_tools": True,
        }
        res = await client.post("http://localhost:8000/api/prompt", json=payload, timeout=120)
        data = res.json()
        ok = res.status_code == 200 and not data.get("error") and data.get("output")
        print("PASS" if ok else "FAIL", data.get("output", "")[:100])

async def phase6():
    print("\n=== PHASE 6: Agent-B via /api/prompt ===")
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {
            "prompt": 'Review this response: "The answer is 4." Is it correct?',
            "model": "qwen2.5-coder:7b",
            "system": "You are a senior code reviewer.",
            "no_tools": True,
        }
        res = await client.post("http://localhost:8000/api/prompt", json=payload, timeout=120)
        data = res.json()
        ok = res.status_code == 200 and not data.get("error") and data.get("output")
        print("PASS" if ok else "FAIL", data.get("output", "")[:100])

async def phase7():
    print("\n=== PHASE 7: Review chain simulation ===")
    async with httpx.AsyncClient(timeout=120) as client:
        r1 = await client.post("http://localhost:8000/api/prompt", json={
            "prompt": "What is 2+2?",
            "model": "deepseek-coder:1.3b",
            "no_tools": True,
        })
        d1 = r1.json()
        a_out = d1.get("output", "")
        print("Agent-A output:", a_out[:100])

        r2 = await client.post("http://localhost:8000/api/prompt", json={
            "prompt": f'Review this answer: "{a_out[:500]}"',
            "model": "qwen2.5-coder:7b",
            "system": "You are a senior code reviewer. Identify any errors.",
            "no_tools": True,
        })
        d2 = r2.json()
        b_out = d2.get("output", "")
        ok = bool(a_out and b_out and not d2.get("error"))
        print("PASS" if ok else "FAIL", "Agent-B output:", b_out[:100])

async def phase8():
    print("\n=== PHASE 8: MCP Execution via REST ===")
    async with httpx.AsyncClient(timeout=120) as client:
        r1 = await client.post("http://localhost:8000/api/mcp/invoke", json={
            "preset": "file_explorer",
            "args": {"action": "list", "path": "."}
        })
        d1 = r1.json()
        print("file_explorer:", d1.get("status"), d1.get("error"))

        r2 = await client.post("http://localhost:8000/api/mcp/invoke", json={
            "preset": "workspace_indexer",
            "args": {"action": "index", "path": "."}
        })
        d2 = r2.json()
        print("workspace_indexer:", d2.get("status"), d2.get("error"))

        r3 = await client.post("http://localhost:8000/api/mcp/invoke", json={
            "preset": "search_ripgrep",
            "args": {"query": "def main", "path": "."}
        })
        d3 = r3.json()
        print("search_ripgrep:", d3.get("status"), d3.get("error"))

async def phase9():
    print("\n=== PHASE 9: Folder Analysis via /api/prompt ===")
    async with httpx.AsyncClient(timeout=120) as client:
        payload = {
            "prompt": "List all Python files in the workspace. Use the file_explorer tool.",
            "model": "deepseek-coder:1.3b",
            "system": "You have access to tools. Use [[MCP:file_explorer:{...}]] to list files.",
            "no_tools": False,
            "workspace_folder": ".",
        }
        res = await client.post("http://localhost:8000/api/prompt", json=payload, timeout=120)
        data = res.json()
        print("status:", res.status_code, "error:", data.get("error"))
        print("output[:300]:", data.get("output", "")[:300])

async def phase10():
    print("\n=== PHASE 10: Winner Execution Flow ===")
    async with httpx.AsyncClient(timeout=120) as client:
        plan = '[[MCP:file_explorer:{"action":"list","path":"."}]]'
        res = await client.post("http://localhost:8000/api/execute-plan", json={
            "plan": plan,
            "workspace_folder": ".",
        })
        data = res.json()
        print("status:", data.get("status"))
        print("results:", data.get("results", [])[:2])

async def main():
    await phase5()
    await phase6()
    await phase7()
    await phase8()
    await phase9()
    await phase10()

if __name__ == "__main__":
    asyncio.run(main())
