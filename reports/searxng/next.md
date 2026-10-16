---
sha: "0ce72dd2ccd6bd06d21e6afd1844455c98719605"
created: 2026-10-16
updated: 2026-10-16
---

# Next Session Plan: searxng

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, 기준 SHA 기록
- [x] 질의 실행 핵심 경로: `search/__init__.py` (병렬 호출·timeout), `processors/online.py` (HTTP 전송·오류 처리), `results.py` (병합·점수·그룹화)
- [x] engine 어댑터 형태: `engines/wikipedia.py`, `engines/brave.py`의 `request`·`response`
- [x] JSON 출력(`webapp.py`, `webutils.py:get_json_response`)과 기본 설정에서 비활성인 점
- [x] 질의 확장 로직 없음

사용자 판단으로 주요 기능 수준에서 분석을 마쳤다. 구조도·실행 흐름 그림과 질문 문서는 만들지 않았다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 결과 중복 판단 hash가 무엇을 기준으로 하는가 (`result_types`의 `__hash__`)
- [ ] engine suspend 시간 규칙과 해제 방식 (`SuspendedStatus`)
- [ ] 서버 시작 시 engine 초기화가 하는 일
- [ ] 봇 제한(`botdetection`, `limiter`)의 실제 동작, plugin·answerer 동작
- [ ] 프라이버시 처리가 코드에서 어떻게 구현되는가

---

## 3. 기능 스펙 후보

없음. 분석을 이어간다면 "engine 병렬 호출과 부분 실패 처리"가 진입점·핵심 처리·실패 처리가 모두 확인된 상태라 첫 후보다.

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `searx/result_types/` | `MainResult.__hash__` | 중복 판단 기준 |
| `searx/search/processors/abstract.py` | `SuspendedStatus`, `EngineProcessor.initialize` | suspend 규칙, 초기화 |
| `searx/limiter.py`, `searx/botdetection/` | — | 봇 제한 동작 |

---

## 5. 참고 사항 및 후속 제안

- 사용자의 주식 데이터 수집은 주기적 저장 방식이라 SearXNG(질문 시점 호출)와 구조가 달라 설계 참고 가치는 낮다고 판단했다. 가져올 만한 패턴은 engine 어댑터(`request`/`response`), 출처별 timeout, 오류 출처 건너뛰기, 실패 출처 목록 반환, 출처별 weight.
- 같은 방향의 비교는 이미 분석한 rsshub, folo가 더 가깝다.
