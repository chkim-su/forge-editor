# serena-query v2 설계

## 현재 한계
1. 요약만 제공 → 상세 정보 필요시 추가 작업
2. 파이프라인 미지원 → 복합 쿼리 불가
3. 캐싱 없음 → 동일 쿼리 반복

## 개선 목표
daemon의 진정한 가치 "컨텍스트 격리"를 최대한 활용

## 새로운 출력 모드

```bash
# --mode summary (기본값, 현재 동작)
$ serena-query find_symbol "Fix"
• Fix [Class] @ scripts/validate_all.py:35-49

# --mode location (위치만, Read와 연계)
$ serena-query find_symbol "Fix" --mode location
scripts/validate_all.py:35:49

# --mode structure (구조 정보, JSON)
$ serena-query find_symbol "Fix" --mode structure
{"name":"Fix","kind":"Class","path":"scripts/validate_all.py","start":35,"end":49}

# --mode full (전체 데이터, 원본 JSON)
$ serena-query find_symbol "Fix" --mode full
{"name":"Fix","kind":"Class","body":"class Fix:...","children":[...]}
```

## 파이프라인 지원

```bash
# 방법 1: stdin 입력
$ serena-query find_symbol "Fix" --mode location | \
  xargs -I{} serena-query refs {} --mode summary

# 방법 2: 체인 명령
$ serena-query chain \
    "find_symbol Fix --mode location" \
    "refs --stdin"

# 방법 3: 배치 파일
$ cat queries.txt
find_symbol Fix
refs Fix scripts/validate_all.py
$ serena-query batch queries.txt > results.json
```

## 캐시 시스템

```bash
# 결과 캐시 (세션 내)
$ serena-query find_symbol "Fix" --cache
# 캐시 재사용
$ serena-query --from-cache last --mode full

# 캐시 디렉토리
~/.serena-query-cache/
├── session_abc123/
│   ├── query_001.json
│   └── query_002.json
```

## Claude 통합 패턴

### 패턴 1: 위치 기반 Read
```
1. serena-query find_symbol "Target" --mode location
   → "src/module.py:42:89"

2. Read src/module.py offset=42 limit=48
   → 정확히 필요한 코드만
```

### 패턴 2: 구조적 탐색
```
1. serena-query get_symbols_overview src/ --depth 0
   → 전체 모듈 구조 요약

2. 관심 모듈 선택 후:
   serena-query get_symbols_overview src/target.py --depth 1
   → 특정 파일 심볼 목록

3. 특정 심볼 상세:
   serena-query find_symbol "TargetClass" --mode full
   → 전체 정보 (필요시에만)
```

### 패턴 3: 분석 자동화
```bash
# analyze.sh
#!/bin/bash
CLASS=$1
serena-query find_symbol "$CLASS" --depth 1 --mode full > /tmp/class.json
serena-query refs "$CLASS" $(jq -r '.path' /tmp/class.json) > /tmp/refs.json
# Claude는 결과 파일만 Read
```

## 구현 우선순위

1. **--mode 옵션 추가** (핵심)
   - location: Read 연계
   - full: 원본 JSON

2. **캐시 시스템**
   - 세션 내 캐싱
   - --from-cache 옵션

3. **파이프라인**
   - --stdin 지원
   - batch 명령

## 예상 효과

| 시나리오 | 현재 | v2 |
|---------|------|-----|
| 클래스 분석 | 4,300 토큰 | 200 토큰 |
| 참조 추적 | 1,500 토큰 | 50 토큰 |
| 코드베이스 탐색 | 10,000+ 토큰 | 500 토큰 |
