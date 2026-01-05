# Extractors and Examples

Detailed code examples and patterns for mcp-daemon-isolation.

## Formatter Pattern (Python)

```python
def format_find_symbol(content: list) -> str:
    """Transform full JSON to actionable summary."""
    if not content:
        return "No symbols found"

    lines = []
    for sym in content[:10]:  # Max 10 results
        name = sym.get("name_path", sym.get("name", "?"))
        kind = sym.get("kind", "?")
        path = sym.get("relative_path", "")
        loc = sym.get("body_location", {})
        start = loc.get("start_line", "?")
        end = loc.get("end_line", "?")

        lines.append(f"• {name} [{kind}] @ {path}:{start}-{end}")

    if len(content) > 10:
        lines.append(f"  ... +{len(content)-10} more")

    return "\n".join(lines)
```

---

## Workflow Example: Error Class Discovery

```bash
# Step 1: 요약으로 범위 파악
$ serena-query search_for_pattern "class.*Error"
Matches(45) in 12 files

# Step 2: 범위 좁히기
$ serena-query search_for_pattern "ValidationError" --path src/
Matches(3) in 1 files: • src/validators.py

# Step 3: 위치 획득
$ serena-query find_symbol "ValidationError" --mode location
src/validators.py:42:78

# Step 4: Claude가 Read로 정확한 코드만 획득
Read src/validators.py offset=42 limit=37
```

---

## CLI Extension Pattern

For other Query-Type MCPs, apply the same pattern:

```python
# 새로운 Query-Type MCP CLI 생성 템플릿
async def call_mcp(tool: str, params: dict) -> dict:
    """Generic MCP-SSE client"""
    # 1. SSE 연결
    # 2. MCP 초기화 핸드셰이크
    # 3. 도구 호출
    # 4. 결과 수신
    ...

# 도구별 포맷터 추가
FORMATTERS = {
    "db_query": format_query_result,
    "search_docs": format_search_result,
    ...
}

# --mode 옵션으로 출력 제어
# summary: 요약
# location: 위치만 (파일:라인 또는 ID)
# full: 전체 JSON
```

---

## Agent Integration Example

For Serena-based refactoring agents:

```yaml
---
name: code-explorer
description: Explore codebase with context-efficient queries
allowed-tools: ["Bash", "Read"]  # No direct MCP needed
---

# Code Explorer Agent

Use `serena-query` for exploration:

1. List directory structure:
   ```bash
   serena-query list_dir src/ --recursive
   ```

2. Find specific symbols:
   ```bash
   serena-query find_symbol ClassName --path src/
   ```

3. When details needed, read saved JSON:
   ```bash
   serena-query find_symbol Target --output /tmp/sym.json
   # Then read specific file:line from the summary
   ```
```
