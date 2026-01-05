#!/usr/bin/env python3
"""Serena Agent PoC - Daemon SSE with MCP init"""

import asyncio
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: pip install httpx", file=sys.stderr)
    sys.exit(1)


async def call_serena(tool: str, params: dict, timeout: float = 30.0) -> dict:
    """Serena daemon SSE 호출 (MCP 초기화 포함)"""

    base_url = "http://localhost:8765"
    session_id = None
    initialized = False
    tool_sent = False
    msg_id = 0

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("GET", f"{base_url}/sse") as sse:
            async for line in sse.aiter_lines():
                # 1. session_id 획득
                if not session_id and line.startswith("data: ") and "session_id=" in line:
                    session_id = line.split("session_id=")[1]

                    # MCP 초기화 요청
                    msg_id += 1
                    init_msg = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "serena-agent", "version": "0.1.0"}
                        }
                    }
                    await client.post(f"{base_url}/messages/?session_id={session_id}", json=init_msg)
                    continue

                if not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])
                except:
                    continue

                # 2. 초기화 응답 수신
                if not initialized and data.get("id") == 1:
                    initialized = True
                    # initialized 알림 전송
                    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                    await client.post(f"{base_url}/messages/?session_id={session_id}", json=notif)

                    # 도구 호출
                    msg_id += 1
                    tool_msg = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "method": "tools/call",
                        "params": {"name": tool, "arguments": params}
                    }
                    await client.post(f"{base_url}/messages/?session_id={session_id}", json=tool_msg)
                    tool_sent = True
                    continue

                # 3. 도구 결과 수신
                if tool_sent and data.get("id") == msg_id:
                    return data

    return {"error": "timeout"}


def summarize(data: dict) -> str:
    """결과 요약"""
    if "error" in data:
        err = data["error"]
        return f"Error: {err.get('message', err) if isinstance(err, dict) else err}"

    result = data.get("result", {})
    content = result.get("content", [{}])[0].get("text", "")

    try:
        parsed = json.loads(content)
        if "dirs" in parsed:
            return f"📁 {len(parsed['dirs'])} dirs, 📄 {len(parsed['files'])} files"
        return f"Items: {len(parsed) if isinstance(parsed, list) else 1}"
    except:
        lines = content.strip().split("\n")
        return f"Lines: {len(lines)}" if lines and lines[0] else "Empty"


async def main():
    if len(sys.argv) < 3:
        print("Usage: serena-agent-poc.py <tool> <path> [output]")
        sys.exit(1)

    tool, path = sys.argv[1], sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else None

    params = {"relative_path": path}
    if tool == "list_dir":
        params["recursive"] = False

    result = await call_serena(tool, params)

    if output:
        Path(output).write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(summarize(result))


if __name__ == "__main__":
    asyncio.run(main())
