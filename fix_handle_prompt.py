import re

with open('cells/gateway/rest.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_handle = '''        if not prompt_text:
            return {"error": "empty_prompt", "output": "[Error: empty prompt received]"}

        mcp_cell = getattr(self._gateway, "_mcp", None)
        full_system = system
        if not no_tools and mcp_cell:
            full_system = system + "\\n\\n" + TOOL_INSTRUCTIONS

        current_prompt = prompt_text
        final_response = ""

        MAX_TOOL_ITERATIONS = 3

        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            # Safety cap
            MAX_PROMPT_LEN = 30000
            if len(current_prompt) > MAX_PROMPT_LEN:
                current_prompt = current_prompt[:MAX_PROMPT_LEN] + "\\n\\n[...truncated by backend]"

            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    payload = {
                        "model": model,
                        "prompt": current_prompt,
                        "stream": False,
                    }
                    if full_system:
                        payload["system"] = full_system

                    options = {}
                    if temperature is not None:
                        options["temperature"] = temperature
                    if context_length:
                        options["num_ctx"] = context_length
                    if options:
                        payload["options"] = options

                    # Force unload after generation to guarantee zero models between agents
                    payload["keep_alive"] = 0

                    res = await client.post(
                        f"{settings.ollama_host}/api/generate",
                        json=payload,
                        timeout=180,
                    )
                    if res.status_code != 200:
                        return {
                            "error": f"ollama_http_{res.status_code}",
                            "output": f"Ollama returned HTTP {res.status_code}: {res.text[:500]}",
                            "model": model,
                        }
                    data = res.json()
                    response_text = data.get("response", "").strip()
                    if not response_text:
                        return {
                            "output": "[Model returned empty response — try again or check Ollama logs]",
                            "model": model,
                            "done": data.get("done", False),
                        }

                    final_response = response_text

                    if no_tools or not mcp_cell or iteration >= MAX_TOOL_ITERATIONS:
                        break

                    tool_calls = self._extract_tool_calls(response_text)
                    if not tool_calls:
                        break

                    tool_results = []
                    for tc in tool_calls:
                        args = tc["args"]
                        # Resolve relative paths against workspace folder
                        if workspace_folder:
                            wf = Path(workspace_folder)
                            for key in ("path", "dest"):
                                if key in args:
                                    val = args[key]
                                    if isinstance(val, str):
                                        if not Path(val).is_absolute():
                                            args[key] = str(wf / val)

                        result = await mcp_cell.invoke(tc["preset"], args)
                        tool_results.append({"call": tc, "result": result})

                    current_prompt = self._build_continuation_prompt(prompt_text, response_text, tool_results)
                    # After first turn, simplify system prompt
                    full_system = system + "\\nContinue based on the tool results. Do not use more tools unless necessary."

            except httpx.ConnectError as e:
                return {
                    "error": "ollama_not_reachable",
                    "output": f"Cannot connect to Ollama at {settings.ollama_host}. Make sure 'ollama serve' is running.",
                    "model": model,
                }
            except Exception as e:
                return {"error": str(e), "output": f"[Error: {str(e)}]", "model": model}

        return {
            "output": final_response,
            "model": model,
            "done": True,
        }'''

new_handle = '''        if not prompt_text:
            return {"error": "empty_prompt", "output": "[Error: empty prompt received]"}

        mcp_cell = getattr(self._gateway, "_mcp", None)
        full_system = system
        tools_enabled = not no_tools and mcp_cell is not None
        if tools_enabled:
            full_system = system + "\\n\\n" + TOOL_INSTRUCTIONS

        logger.info("stage=A received_prompt=%s model=%s tools_enabled=%s", prompt_text[:200], model, tools_enabled)

        current_prompt = prompt_text
        final_response = ""
        any_tool_executed = False

        MAX_TOOL_ITERATIONS = 3

        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            # Safety cap
            MAX_PROMPT_LEN = 30000
            if len(current_prompt) > MAX_PROMPT_LEN:
                current_prompt = current_prompt[:MAX_PROMPT_LEN] + "\\n\\n[...truncated by backend]"

            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    payload = {
                        "model": model,
                        "prompt": current_prompt,
                        "stream": False,
                    }
                    if full_system:
                        payload["system"] = full_system

                    options = {}
                    if temperature is not None:
                        options["temperature"] = temperature
                    if context_length:
                        options["num_ctx"] = context_length
                    if options:
                        payload["options"] = options

                    # Force unload after generation to guarantee zero models between agents
                    payload["keep_alive"] = 0

                    logger.info("stage=B ollama_request iteration=%s prompt_len=%s system_len=%s", iteration, len(current_prompt), len(full_system or ""))

                    res = await client.post(
                        f"{settings.ollama_host}/api/generate",
                        json=payload,
                        timeout=180,
                    )
                    if res.status_code != 200:
                        logger.info("stage=G ollama_error status=%s", res.status_code)
                        return {
                            "error": f"ollama_http_{res.status_code}",
                            "output": f"Ollama returned HTTP {res.status_code}: {res.text[:500]}",
                            "model": model,
                        }
                    data = res.json()
                    response_text = data.get("response", "").strip()
                    logger.info("stage=B model_response_len=%s", len(response_text))
                    if not response_text:
                        return {
                            "output": "[Model returned empty response — try again or check Ollama logs]",
                            "model": model,
                            "done": data.get("done", False),
                        }

                    final_response = response_text

                    if not tools_enabled or iteration >= MAX_TOOL_ITERATIONS:
                        break

                    tool_calls = self._extract_tool_calls(response_text)
                    logger.info("stage=C tools_detected=%s count=%s", bool(tool_calls), len(tool_calls))

                    # PHASE 7 — Force tool execution for explicit tool requests
                    if not tool_calls:
                        forced = self._force_tool_detection(prompt_text)
                        if forced:
                            logger.info("stage=C_forced forced_tool=%s", forced["preset"])
                            tool_calls = [forced]

                    if not tool_calls:
                        break

                    tool_results = []
                    for tc in tool_calls:
                        args = tc["args"]
                        # Resolve relative paths against workspace folder
                        if workspace_folder:
                            wf = Path(workspace_folder)
                            for key in ("path", "dest"):
                                if key in args:
                                    val = args[key]
                                    if isinstance(val, str):
                                        if not Path(val).is_absolute():
                                            args[key] = str(wf / val)

                        logger.info("stage=D dispatching_mcp=%s args=%s", tc["preset"], json.dumps(args))
                        result = await mcp_cell.invoke(tc["preset"], args)
                        logger.info("stage=E tool_result=%s", json.dumps(result)[:500])
                        tool_results.append({"call": tc, "result": result})
                        any_tool_executed = True

                    current_prompt = self._build_continuation_prompt(prompt_text, response_text, tool_results)
                    logger.info("stage=F context_after_tool prompt_len=%s", len(current_prompt))
                    # After first turn, simplify system prompt
                    full_system = system + "\\nContinue based on the tool results. Do not use more tools unless necessary."

            except httpx.ConnectError as e:
                logger.info("stage=G ollama_connect_error")
                return {
                    "error": "ollama_not_reachable",
                    "output": f"Cannot connect to Ollama at {settings.ollama_host}. Make sure 'ollama serve' is running.",
                    "model": model,
                }
            except Exception as e:
                logger.info("stage=G exception=%s", str(e))
                return {"error": str(e), "output": f"[Error: {str(e)}]", "model": model}

        # PHASE 11 — Hallucination prevention
        if any_tool_executed:
            logger.info("stage=H final_response_tools_used=%s", any_tool_executed)
        else:
            logger.info("stage=H final_response_no_tools")

        return {
            "output": final_response,
            "model": model,
            "done": True,
        }'''

if old_handle not in content:
    print('ERROR: old_handle not found')
    idx = content.find('if not prompt_text:')
    print(repr(content[idx:idx+200]))
    raise SystemExit(1)

content = content.replace(old_handle, new_handle)
print('Fixed _handle_prompt')

with open('cells/gateway/rest.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
