with open('cells/gateway/rest.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        if any(k in lowered for k in ("read file", "show file", "file content", "contents of", "what is in")):
            m = re.search(r'(?:file\\s+)([\\w\\-/.\\\\]+\\.\\w+)', lowered)
            if m:
                return {"preset": "file_explorer", "args": {"action": "read", "path": m.group(1)}, "raw": "[[forced]]"}'''

new = '''        if any(k in lowered for k in ("read file", "show file", "file content", "contents of", "what is in")) or lowered.startswith("read "):
            m = re.search(r'(?:file\\s+)([\\w\\-/.\\\\]+\\.\\w+)', lowered)
            if not m and lowered.startswith("read "):
                # Try to grab the word after "read"
                m = re.search(r'^read\\s+([\\w\\-/.\\\\]+\\.\\w+)', lowered)
            if m:
                return {"preset": "file_explorer", "args": {"action": "read", "path": m.group(1)}, "raw": "[[forced]]"}'''

if old not in content:
    print('ERROR: old not found')
    idx = content.find('"read file"')
    print(repr(content[idx-50:idx+300]))
    raise SystemExit(1)

content = content.replace(old, new)
print('Fixed _force_tool_detection')

with open('cells/gateway/rest.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
