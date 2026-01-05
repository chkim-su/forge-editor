# Solution Synthesis Framework

문제 발견에서 그치지 않고, **skillmaker의 전체 지식 베이스를 활용해 해결책을 종합**합니다.

---

## 핵심 원칙

> **진단 + 처방 = 컨설팅**

| 단계 | 현재 Wizard | 현명한 Wizard |
|------|-------------|---------------|
| 1 | 문제 발견 | 문제 발견 |
| 2 | "이런 문제가 있습니다" | **왜** 이런 문제가 생겼는지 분석 |
| 3 | (끝) | 어느 스킬에서 **이 패턴을 다루는지** 식별 |
| 4 | - | 해당 스킬의 **해결책** 추출 |
| 5 | - | **구현 방법** 제안 |
| 6 | - | "실행할까요?" 제안 |

---

## Problem-Solution Mapping

발견된 문제를 skillmaker 스킬과 연결합니다.

### MCP 관련 문제

| 발견 | 패턴 인식 | 관련 스킬 | 해결책 |
|------|----------|----------|--------|
| "Gateway 패턴 실패" | MCP 접근 제약 | `mcp-gateway-patterns` | Daemon SSE 패턴 |
| "서브에이전트 MCP 접근 불가" | Claude Code 제약 | `mcp-gateway-patterns` | 데이터 위임 또는 Daemon |
| "MCP 30-60초 시작 지연" | Subprocess 오버헤드 | `mcp-gateway-patterns` | Daemon SSE (1-2초) |
| "MCP 토큰 오버헤드" | 도구 정의 비용 | `mcp-gateway-patterns` | Subprocess/Daemon 격리 |

**해결책 로드**:
```
Skill("forge-editor:mcp-gateway-patterns")
→ Read("references/daemon-shared-server.md")
```

### 스킬 설계 문제

| 발견 | 패턴 인식 | 관련 스킬 | 해결책 |
|------|----------|----------|--------|
| "SKILL.md 500단어 초과" | Progressive disclosure 위반 | `skill-design` | references/ 분리 |
| "frontmatter 누락" | 메타데이터 부재 | `skill-design` | 필수 필드 추가 |
| "skills 선언 미사용" | 미사용 기능 | `skill-design` | Skill() 호출 또는 선언 제거 |

**해결책 로드**:
```
Skill("forge-editor:skill-design")
→ Read("references/structure-rules.md")
```

### 에이전트 오케스트레이션 문제

| 발견 | 패턴 인식 | 관련 스킬 | 해결책 |
|------|----------|----------|--------|
| "에이전트에 tools: []" | 역할 혼동 | `orchestration-patterns` | 문서 vs 에이전트 재분류 |
| "Skill() 호출 없이 참조" | 스킬 로딩 누락 | `orchestration-patterns` | 명시적 Skill() 추가 |
| "다단계 워크플로우 스킬 미분리" | 컨텍스트 비효율 | `orchestration-patterns` | 단계별 스킬 로딩 |

**해결책 로드**:
```
Skill("forge-editor:orchestration-patterns")
→ Read("references/context-isolation.md")
```

### Hook 관련 문제

| 발견 | 패턴 인식 | 관련 스킬 | 해결책 |
|------|----------|----------|--------|
| "MUST/CRITICAL 키워드 but no hook" | Hookify 미준수 | `hook-templates` | PreToolUse hook 추가 |
| "Hook blocking/informational 혼재" | 정책 불일치 | `hook-templates` | 정책 통일 |
| "Hook 20개+" | 오버엔지니어링 | `hook-templates` | Hook 통합/간소화 |

**해결책 로드**:
```
Skill("forge-editor:hook-templates")
→ Read("references/full-examples.md")
```

### 워크플로우 상태 문제

| 발견 | 패턴 인식 | 관련 스킬 | 해결책 |
|------|----------|----------|--------|
| "다단계 워크플로우 상태 추적 없음" | 상태 파일 미사용 | `workflow-state-patterns` | .{workflow}-*-done 파일 |
| "Plan auto-approved" | 게이트 우회 | `workflow-state-patterns` | 명시적 승인 게이트 |

**해결책 로드**:
```
Skill("forge-editor:workflow-state-patterns")
→ Read("references/complete-workflow-example.md")
```

---

## Solution Synthesis Process

### Step 1: 문제 분류

```python
def classify_problem(finding: str) -> list[str]:
    """발견된 문제를 관련 스킬로 분류"""

    mappings = {
        "mcp|gateway|subprocess|daemon|서브에이전트.*mcp": ["mcp-gateway-patterns"],
        "skill.*design|progressive|frontmatter|references/": ["skill-design"],
        "agent|orchestration|tools:\\s*\\[\\]|Skill\\(\\)": ["orchestration-patterns"],
        "hook|PreToolUse|PostToolUse|MUST|CRITICAL": ["hook-templates"],
        "workflow|phase|stage|state|gate": ["workflow-state-patterns"],
        "activation|trigger|keyword": ["skill-activation-patterns"],
    }

    return [skill for pattern, skills in mappings.items()
            if re.search(pattern, finding, re.I)]
```

### Step 2: 관련 스킬 로드

발견된 문제에 따라 자동으로 스킬 로드:

```
For each classified_skill:
    Skill("forge-editor:{classified_skill}")
```

### Step 3: 해결책 추출

각 스킬에서 관련 reference 로드:

```markdown
## 해결책: {problem_name}

**문제**: {what was found}

**원인**: {why this happened - from skill knowledge}

**해결책**: {specific solution from skill}

**구현**:
```bash
{concrete steps}
```

**상세**: `Read("references/{relevant-file}.md")`
```

### Step 4: 실행 제안

```yaml
AskUserQuestion:
  question: "어떤 해결책을 적용할까요?"
  header: "Action"
  multiSelect: true
  options:
    - label: "{Solution 1}"
      description: "{brief description}"
    - label: "{Solution 2}"
      description: "{brief description}"
    - label: "모두 적용"
      description: "모든 권장 해결책 적용"
    - label: "나중에"
      description: "지금은 분석만"
```

---

## 출력 형식

### 철학적 분석 + 해결책 종합

```markdown
## 프로젝트 분석: {project-name}

### 발견된 문제

| # | 발견 | 분류 | 심각도 |
|---|------|------|--------|
| 1 | {finding 1} | {skill category} | 🔴 HIGH |
| 2 | {finding 2} | {skill category} | 🟡 MEDIUM |

---

### 해결책 종합

#### 🔴 문제 1: {finding 1}

**왜 이런 문제가 생겼는가?**
{root cause analysis from skillmaker knowledge}

**관련 지식**: `Skill("forge-editor:{relevant-skill}")`

**해결책**:
{specific solution}

**구현 방법**:
```bash
{concrete steps}
```

**상세 참조**: `Read("references/{file}.md")`

---

#### 🟡 문제 2: {finding 2}

...

---

### 실행 제안

다음 해결책을 적용할 수 있습니다:

1. [ ] {Solution 1} - 예상 영향: {impact}
2. [ ] {Solution 2} - 예상 영향: {impact}

**진행하시겠습니까?**
```

---

## 예시: serena-refactor 분석

### 발견

| # | 발견 | 분류 | 심각도 |
|---|------|------|--------|
| 1 | serena-gateway가 에이전트가 아닌 문서 | orchestration-patterns | 🔴 HIGH |
| 2 | 4개 에이전트가 작동 불가한 Gateway 패턴 참조 | mcp-gateway-patterns | 🔴 HIGH |
| 3 | Hook blocking/informational 불일치 | hook-templates | 🟡 MEDIUM |

### 해결책 종합

#### 🔴 문제 1-2: Gateway 패턴 실패

**왜 이런 문제가 생겼는가?**

Claude Code의 서브에이전트(Task)는 MCP 도구에 접근할 수 없습니다. 이는 Claude Code의 근본적 제약입니다.

원래 설계:
```
Main Session → Task: serena-gateway → mcp__serena__* 호출
```

실제 동작:
```
Main Session → Task: serena-gateway → MCP 도구 없음 (실패)
```

**관련 지식**: `Skill("forge-editor:mcp-gateway-patterns")`

**해결책**: Daemon SSE 패턴

```bash
# 1. Serena를 HTTP 데몬으로 시작
serena start-mcp-server --transport sse --port 8765 &

# 2. Claude Code에 등록
claude mcp add --transport sse serena-daemon http://127.0.0.1:8765

# 3. 모든 세션/서브프로세스에서 공유
```

**이점**:
- 시작 시간: 30-60초 → 1-2초
- 토큰 오버헤드: 메인 세션 0
- 상태 공유: 가능

**상세**: `Read("references/daemon-shared-server.md")`

---

#### 🟡 문제 3: Hook 정책 불일치

**관련 지식**: `Skill("forge-editor:hook-templates")`

**해결책**: 정책 통일

| 현재 | 제안 |
|------|------|
| blocking + informational 혼재 | 워크플로우 게이트는 모두 blocking |

**구현**: hooks/hooks.json에서 모든 게이트 hook을 `exit 1` (blocking)으로 통일

---

### 실행 제안

1. [ ] **serena-gateway 역할 재정의** - docs/로 이동 또는 에이전트로 재설계
2. [ ] **Daemon SSE 패턴 적용** - MCP 접근 문제 해결
3. [ ] **구 Gateway 참조 제거** - 4개 에이전트 문서 갱신
4. [ ] **Hook 정책 통일** - blocking으로 일원화

**진행하시겠습니까?**

---

## Level 2: Radical Solutions 🔥

> **"If you're confident, propose it even if it's not in existing patterns"**
> **"Idiots, this solves everything - why can't you see it?"**

When conservative solutions feel like **band-aids**, propose paradigm-shifting alternatives.

### When to Propose Radical Solutions?

| Signal | Meaning | Radical Approach |
|--------|---------|------------------|
| Same problem 3+ times | System structure issue | **Architecture redesign** |
| Exceptions outnumber rules | Rule itself is wrong | **Discard rules** |
| Workaround more complex than normal path | Constraint is irrational | **Remove constraint** |
| "That's just how it is" response | Law of inertia | **Review from first principles** |
| Compatibility cost > value | Legacy debt | **Breaking change** |

### Radical Questions Framework

```markdown
## 1. Constraint Dissolution
- "Who created this constraint? Why?"
- "What would we do without this constraint?"
- "Is the situation that created this constraint still valid?"

## 2. First Principles
- "If we redefine this problem from scratch?"
- "What is physically/logically impossible?"
- "If it's physically possible, why aren't we doing it?"

## 3. 10x Thinking
- "If there's a 10x better method, what is it?"
- "What if the current method is completely wrong?"
- "How would a competitor build this from scratch?"

## 4. Inversion
- "What happens if we don't solve this problem?"
- "How would we make this problem worse?" (do the opposite)
- "When would this feature be unnecessary?"
```

### Radical Solution Output Format

```markdown
### 🔥 Radical Solution: {proposal}

**Fundamental limits of current approach**:
{why conservative solutions won't work}

**Proposal**:
{paradigm shift or structural redesign}

**Why this is right**:
- {rationale 1}
- {rationale 2}
- {rationale 3}

**Trade-off**:
| Gains | Losses |
|-------|--------|
| {benefit 1} | {cost 1} |
| {benefit 2} | {cost 2} |

**Confidence Level**: 🟢 High | 🟡 Medium | 🔴 Exploratory

**Execution Steps**:
1. {step 1}
2. {step 2}
3. {step 3}

**Expected Impact**:
- Short-term: {immediate impact}
- Long-term: {long-term benefit}
```

### Radical Solution Examples

#### Example 1: Gateway Pattern Failure

**Conservative solution**: Workaround with Daemon SSE pattern
**Radical solution**: 

```markdown
### 🔥 Radical Solution: Discard Gateway Concept Entirely

**Fundamental limits of current approach**:
Gateway pattern assumes "centralized MCP access", but
Claude Code's subagent isolation invalidates this premise.
Daemon pattern is ultimately "a workaround to save Gateway".

**Proposal**:
Discard Gateway concept and transition to **MCP-free architecture**.
- Analyze all MCP dependencies
- For each dependency: is MCP really necessary?
- Alternatives: CLI wrapper, REST API, direct library calls

**Why this is right**:
- MCP is convenience, not necessity
- Complete elimination of MCP overhead (startup time, tokens)
- Subagent isolation problem solved at source

**Trade-off**:
| Gains | Losses |
|-------|--------|
| 0-second startup | MCP ecosystem compatibility |
| 0 token overhead | Tool autocomplete |
| Architecture simplification | MCP-based extensibility |

**Confidence Level**: 🟡 Medium (depends on project dependencies)

**Execution Steps**:
1. Extract list of MCP tool usage
2. Analyze alternatives for each tool (CLI? API? Library?)
3. Start migration with lowest-cost alternatives
4. Progressively remove MCP dependencies
```

#### Example 2: Hook Over-Complexity

**Conservative solution**: Consolidate hooks, remove unnecessary hooks
**Radical solution**:

```markdown
### 🔥 Radical Solution: Replace Hook System with LLM Self-Control

**Fundamental limits of current approach**:
Hooks assume "we don't trust the LLM".
As hooks increase, system complexity grows.
Eventually, hook management becomes a bigger problem than the original issue.

**Proposal**:
Minimize hooks and replace with **enhanced system prompts**.
- Only use hooks for things that truly need blocking
- Solve the rest with clear instructions + examples

**Why this is right**:
- Modern LLMs (Claude 3.5+) have very high instruction compliance rates
- Hook debugging cost > occasional violation cost
- Dramatic reduction in system complexity

**Confidence Level**: 🟡 Medium (depends on organization's policy on LLM trust)
```

### Rules for Proposing Radical Solutions

1. **Always present conservative solution first**
2. **Explicitly state limits** of conservative solution
3. **Honestly disclose trade-offs** of radical solution
4. **Indicate confidence level** (🟢/🟡/🔴)
5. **Choice belongs to user** - don't force
6. Radical ≠ irresponsible. **Concrete execution steps are mandatory**

---

## Automatic Skill Loading Rules

Auto-load skills when following patterns detected during analysis:

| Detection Pattern | Auto-Load |
|-------------------|-----------|
| MCP tool usage attempted | `mcp-gateway-patterns` |
| agents/ directory exists | `orchestration-patterns` |
| skills/ directory exists | `skill-design` |
| hooks/ directory exists | `hook-templates` |
| Multi-stage workflow | `workflow-state-patterns` |
| Gateway/Subprocess mentioned | `mcp-gateway-patterns` |
