# Intent vs Implementation Mismatch Patterns

의도와 구현이 불일치하는 일반적인 패턴들입니다.

## Pattern 1: 이름과 역할 불일치

### 증상
```
파일: agents/gateway.md
tools: []
실제 동작: MCP 도구를 직접 호출하지 않음, 문서 역할만 수행
```

### 질문
- "gateway라는 이름이 암시하는 역할과 실제 역할이 다르지 않은가?"
- "agents/ 디렉토리에 있어야 하는가?"

### 해결 방안
| 옵션 | 설명 |
|-----|-----|
| 역할 변경 | 실제 gateway 기능 구현 (MCP 호출 등) |
| 위치 변경 | docs/ 또는 references/로 이동 |
| 이름 변경 | 실제 역할을 반영하는 이름으로 변경 |

---

## Pattern 2: 선언과 동작 불일치

### 증상
```yaml
# frontmatter
skills: skill-a, skill-b, skill-c

# body
실제로 skill-a만 사용됨
skill-b, skill-c는 언급도 없음
```

### 질문
- "왜 skill-b, skill-c를 선언했는가?"
- "나중에 쓰려고 했다면 왜 아직 안 쓰는가?"
- "불필요하다면 왜 제거하지 않았는가?"

### 해결 방안
1. 실제 사용하는 스킬만 선언
2. 또는 선언한 스킬을 실제로 활용하는 로직 추가

---

## Pattern 3: 문서와 코드 비동기화

### 증상
```markdown
## Important: Use Gateway Pattern
모든 MCP 호출은 gateway를 통해야 합니다.

Task:
  agent: serena-gateway
  prompt: "..."
```

하지만 실제 아키텍처는:
- 메인 세션에서 직접 MCP 호출
- gateway는 더 이상 중개 역할 안 함

### 질문
- "아키텍처가 변경되었는데 문서는 왜 안 바뀌었는가?"
- "이 문서를 읽는 사람이 혼란스럽지 않겠는가?"

### 해결 방안
1. 문서를 현재 아키텍처에 맞게 업데이트
2. 구 아키텍처 섹션 완전 제거 (주석 처리도 안 됨)

---

## Pattern 4: 위치와 역할 불일치

### 일반적인 기대
| 위치 | 기대 역할 |
|-----|----------|
| agents/ | Task로 호출되는 독립 에이전트 |
| skills/ | Skill()로 로드되는 컨텍스트 |
| commands/ | /command로 실행되는 워크플로우 |
| docs/ | 참조 문서 |

### 불일치 예시
```
agents/documentation-only.md  # 실제론 문서
skills/executable-script/     # 실제론 에이전트처럼 동작
```

### 해결 방안
- 역할에 맞는 디렉토리로 이동
- 또는 역할을 디렉토리 의미에 맞게 변경

---

## Detection Checklist

분석 시 확인할 항목:

- [ ] 모든 agents/*.md가 tools: 필드에 도구를 가지고 있는가?
- [ ] frontmatter skills 선언과 본문 Skill() 사용이 일치하는가?
- [ ] 문서에 "구 방식", "이전 아키텍처" 언급이 없는가?
- [ ] 파일명/폴더명이 실제 역할을 반영하는가?
