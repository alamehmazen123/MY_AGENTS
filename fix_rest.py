import re

with open('cells/gateway/rest.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix _extract_tool_calls
old_extract = '''    def _extract_tool_calls(self, text: str):
        import re
        import json
        pattern = re.compile(r'\\[\\[MCP:(\\w+):({.*?})\\]\\]')
        calls = []
        for match in pattern.finditer(text):
            preset = match.group(1)
            try:
                args = json.loads(match.group(2))
                calls.append({"preset": preset, "args": args, "raw": match.group(0)})
            except json.JSONDecodeError:
                continue
        return calls'''

new_extract = '''    def _extract_tool_calls(self, text: str):
        import re
        import json
        # Primary: single-line or multi-line JSON inside [[MCP:preset:{...}]]
        pattern = re.compile(r'\\[\\[MCP:(\\w+):\\s*({.*?)\\s*\\]\\]', re.DOTALL)
        calls = []
        for match in pattern.finditer(text):
            preset = match.group(1)
            try:
                args = json.loads(match.group(2))
                calls.append({"preset": preset, "args": args, "raw": match.group(0)})
            except json.JSONDecodeError:
                continue
        if not calls:
            # Fallback: match inside markdown code blocks that contain [[MCP:...]]
            md_pattern = re.compile(r'```.*?\\n(.*?)\\n```', re.DOTALL)
            for md_match in md_pattern.finditer(text):
                inner = md_match.group(1)
                for m in re.finditer(r'\\[\\[MCP:(\\w+):\\s*({.*?)\\s*\\]\\]', inner, re.DOTALL):
                    try:
                        calls.append({"preset": m.group(1), "args": json.loads(m.group(2)), "raw": m.group(0)})
                    except json.JSONDecodeError:
                        continue
        return calls'''

if old_extract not in content:
    print('ERROR: old_extract not found')
    idx = content.find('def _extract_tool_calls')
    print(repr(content[idx:idx+600]))
    raise SystemExit(1)
content = content.replace(old_extract, new_extract)
print('Fixed _extract_tool_calls')

# 2. Fix _build_continuation_prompt and add _force_tool_detection
old_build = '''    def _build_continuation_prompt(self, original_prompt: str, last_response: str, tool_results: list):
        import json
        parts = [original_prompt]
        parts.append("\\n\\n[Your previous response]\\n" + last_response)
        parts.append("\\n\\n[Tool Results]\\n")
        for tr in tool_results:
            parts.append(f"Tool: {tr['call']['preset']}")
            parts.append(f"Args: {json.dumps(tr['call']['args'])}")
            parts.append(f"Result: {json.dumps(tr['result'])}\\n")
        parts.append("Based on the tool results above, provide your final answer. Do not use more tools unless necessary.")
        return "\\n".join(parts)'''

new_build = '''    def _force_tool_detection(self, prompt_text: str):
        """PHASE 7 — Force tool execution when user explicitly requests file operations."""
        import re
        lowered = prompt_text.lower()
        # Detect explicit file_explorer requests
        if any(k in lowered for k in ("list files", "list directory", "show files", "show directory", "list current directory", "what files", "which files")):
            path = "."
            # Try to extract a path
            m = re.search(r'(?:in|under|from|at)\\s+([\\w\\-/.\\\\]+)', lowered)
            if m:
                candidate = m.group(1)
                if candidate.lower() not in ("the", "a", "this", "that", "my", "your"):
                    path = candidate
            return {"preset": "file_explorer", "args": {"action": "list", "path": path}, "raw": "[[forced]]"}
        if any(k in lowered for k in ("read file", "show file", "file content", "contents of", "what is in")):
            m = re.search(r'(?:file\\s+)([\\w\\-/.\\\\]+\\.\\w+)', lowered)
            if m:
                return {"preset": "file_explorer", "args": {"action": "read", "path": m.group(1)}, "raw": "[[forced]]"}
        if any(k in lowered for k in ("search for", "find function", "find code", "search code", "grep for")):
            query = re.sub(r'.*?(search for|find function|find code|search code|grep for)\\s+', '', lowered).strip().split()[0]
            return {"preset": "search_ripgrep", "args": {"query": query or "def", "path": "."}, "raw": "[[forced]]"}
        return None

    def _build_continuation_prompt(self, original_prompt: str, last_response: str, tool_results: list):
        import json
        parts = ["=== ORIGINAL USER REQUEST ==="]
        parts.append(original_prompt)
        parts.append("\\n=== YOUR PREVIOUS ATTEMPT ===")
        parts.append(last_response)
        parts.append("\\n=== TOOL EXECUTION RESULTS (USE THESE TO ANSWER) ===")
        for tr in tool_results:
            parts.append(f"\\nTool: {tr['call']['preset']}")
            parts.append(f"Args: {json.dumps(tr['call']['args'])}")
            parts.append(f"Result: {json.dumps(tr['result'])}")
        parts.append("\\n=== INSTRUCTION ===")
        parts.append("Using the TOOL EXECUTION RESULTS above, provide a direct answer to the ORIGINAL USER REQUEST.")
        parts.append("Do NOT describe what you would do. Do NOT explain the tools.")
        parts.append("Answer with the actual data from the results.")
        return "\\n".join(parts)'''

if old_build not in content:
    print('ERROR: old_build not found')
    idx = content.find('def _build_continuation_prompt')
    print(repr(content[idx:idx+600]))
    raise SystemExit(1)
content = content.replace(old_build, new_build)
print('Fixed _build_continuation_prompt and added _force_tool_detection')

with open('cells/gateway/rest.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
