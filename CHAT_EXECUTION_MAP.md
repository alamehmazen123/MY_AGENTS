# Chat Execution Map — Agent-A Tool Execution Flow

## Overview

This document traces the exact path from `POST /chat` (or `/api/prompt`) to the final LLM response, identifying every file and decision point involved in MCP tool execution.

## Architecture Diagram

```
Frontend (React/Vite)
  ↓ POST /api/prompt
  ↓ JSON: { prompt, model, system, workspace_folder, no_tools, temperature, context_length }
cells/gateway/rest.py — RESTServer._handle_prompt()
  ↓ Build full_system = system + TOOL_INSTRUCTIONS (if no_tools=False and mcp_cell exists)
  ↓ Call Ollama /api/generate
  ↓ Response text
  ↓ _extract_tool_calls() — regex [[MCP:(\w+):({.*?})]]
  ↓ If matches: invoke mcp_cell.invoke(preset, args)
  ↓ _build_continuation_prompt() — inject tool results
  ↓ Loop back to Ollama (max 3 iterations)
  ↓ Return final response
Frontend displays response
```

## File-by-File Breakdown

### 1. Frontend Entry Point
- **File**: `frontend/src/stores/sessionStore.ts`
- **Function**: `sendPrompt()` -> `callOllama()`
- **Key Logic**: 
  - Builds prompt with attached files and workspace folder
  - Calls `/api/prompt` with `enableTools: settings.mcpToolsEnabled`
  - `no_tools: true` sent only when `enableTools === false`

### 2. API Gateway
- **File**: `cells/gateway/rest.py`
- **Class**: `RESTServer`
- **Endpoint**: `@self.app.post("/api/prompt")` -> `_handle_prompt()`
- **Key Logic**:
  - Receives prompt, model, system prompt, workspace_folder, no_tools flag
  - Prepends `TOOL_INSTRUCTIONS` to system prompt if tools enabled
  - Iterates up to `MAX_TOOL_ITERATIONS = 3`
  - Calls Ollama `/api/generate` with `stream: false`
  - Extracts tool calls via `_extract_tool_calls()`
  - Executes tools via `mcp_cell.invoke()`
  - Builds continuation prompt via `_build_continuation_prompt()`

### 3. Tool Call Extraction
- **File**: `cells/gateway/rest.py` (lines ~480-490)
- **Function**: `_extract_tool_calls()`
- **Current Regex**: `r'\[\[MCP:(\w+):({.*?)\]\]'`
- **Critical Limitation**: Does NOT match multi-line JSON (missing `re.DOTALL`)
- **Critical Limitation**: Does NOT handle whitespace after colon or before `]]`

### 4. MCP Execution Layer
- **File**: `cells/mcp/cell.py`
- **Class**: `MCPCell`
- **Function**: `invoke(preset, args)`
- **Key Logic**:
  - Validates preset exists in `MCPRegistry`
  - Enforces workspace jail via `_jail_args()`
  - Delegates to `ExecutionPool.execute()`

### 5. MCP Registry
- **File**: `cells/mcp/registry.py`
- **Class**: `MCPRegistry`
- **Function**: `register_preset()`, `list_tools()`, `has()`, `get()`
- **Status**: `file_explorer` is registered at startup in `MCPCell._load_presets()`

### 6. Process Execution
- **File**: `kernel/mcp/runtime/execution_pool.py`
- **Function**: `execute(tool, args)`
- **Status**: Isolates tool execution in worker processes

### 7. Tool Handlers
- **File**: `cells/mcp/presets/file_explorer.py`
- **Function**: `handle(args)`
- **Status**: Validated and working (used by direct MCP invoke endpoint)

### 8. Gateway Cell Wiring
- **File**: `cells/gateway/cell.py`
- **Class**: `GatewayCell`
- **Key Logic**: `gateway._mcp = CELL_REGISTRY.get("mcp")` wired in `kernel/main.py`

## Known Failure Modes

| Stage | Failure | Symptom |
|-------|---------|---------|
| A | Frontend sends `no_tools=True` | Agent never sees tool instructions |
| B | `_extract_tool_calls` regex mismatch | Agent emits `[[MCP:...]]` but backend ignores it |
| C | Model ignores system prompt | Agent explains tools instead of using them |
| D | Context injection broken | Tool runs but final answer ignores results |
| E | Workspace jail blocks path | Tool returns error even for valid requests |

## Decision Points

1. **Tool Enablement**: `if not no_tools and mcp_cell:` in `_handle_prompt`
2. **Tool Detection**: `tool_calls = self._extract_tool_calls(response_text)`
3. **Loop Termination**: `if not tool_calls: break`
4. **Iteration Cap**: `MAX_TOOL_ITERATIONS = 3`
5. **Model Unload**: `payload["keep_alive"] = 0` after every generation
