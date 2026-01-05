# 비용 최적화

## 비용 구조 (2025-12-30 검증)

### Claude Code 구독

| 플랜 | 월 비용 | 포함 사용량 |
|------|---------|------------|
| Pro | $20 | ~40-80시간 Sonnet/주 |
| Max 5x | $100 | ~140시간 Sonnet/주 |
| Max 20x | $200 | ~480시간 Sonnet/주 |

### API 직접 과금

| 모델 | 입력 (MTok) | 출력 (MTok) |
|------|-------------|-------------|
| Opus 4.5 | $5 | $25 |
| Sonnet 4 | $3 | $15 |
| Opus 4/4.1 | $15 | $75 |

## SDK 비용 = 구독 사용량

```
SDK → CLI → 구독 사용량 (추가 비용 없음)
     └─ 직접 API 호출 아님!
```

**핵심**: SDK가 CLI를 spawn하므로 구독자에게는 추가 API 비용 없음

## 비용 최적화 전략

### 1. ModelTier 선택

```python
from llm_types import ModelTier

# 비용 순서: LOW < MEDIUM < HIGH
config = LLMConfig(tier=ModelTier.LOW)  # 간단한 평가
config = LLMConfig(tier=ModelTier.MEDIUM)  # 일반 작업
config = LLMConfig(tier=ModelTier.HIGH)  # 복잡한 분석
```

### 2. 프롬프트 최소화

```python
# Bad: 긴 프롬프트
await llm.run("Please carefully analyze this command and determine if it is safe...")

# Good: 짧은 프롬프트
await llm.run("Safe? YES/NO: " + command)
```

### 3. 선택적 호출

```python
# 모든 명령에 호출하지 말고 위험 패턴만
DANGEROUS_PATTERNS = ["rm ", "sudo ", "chmod ", "DROP TABLE"]

if any(p in command for p in DANGEROUS_PATTERNS):
    result = await llm.run(f"Is this dangerous? {command}")
```

### 4. 로컬 LLM 대안

| 옵션 | 비용 | 품질 | 속도 |
|------|------|------|------|
| Claude (구독) | 포함 | 높음 | 보통 |
| ollama (로컬) | 무료 | 중간 | 느림 |
| llama.cpp | 무료 | 중간 | 느림 |

```bash
# ollama 사용 예시
RESULT=$(ollama run llama3.2 "Is this safe? $COMMAND" 2>/dev/null)
```

## type: "prompt" vs SDK

| 특성 | type: "prompt" | SDK |
|------|----------------|-----|
| 비용 | 구독 포함 | 구독 포함 |
| 속도 | 빠름 | 느림 (30초) |
| 복잡도 | 낮음 | 높음 |
| 커스터마이징 | 제한적 | 자유로움 |

**권장**: 간단한 평가는 `type: "prompt"`, 복잡한 로직은 SDK
