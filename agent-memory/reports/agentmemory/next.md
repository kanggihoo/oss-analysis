---
sha: "70517d2bdf302a0aed11ca470151ee854e74c678"
created: 2026-10-25
updated: 2026-10-25
---

# Next Session Plan: agentmemory

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] clone·기준 SHA·라이선스(Apache 2.0, 루트와 `packages/mcp`)
- [x] 기능 지도 38행 + 공유 계약 6개 (`registerFunction("mem::*")` 160개, `api::*` 145개, MCP 도구 54개, CLI 명령표, 훅 입구 목록 대조)
- [x] 구조도 1장(`diagrams/structure.{json,html}`), 그림 해설
- [ ] 스펙 범위 승인 — **대기 중**. 승인 전에는 기능 스펙을 쓰지 않는다.

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] README 파이프라인의 "SessionStart → … → Inject"와 달리 기본값이 주입 꺼짐인 것이 의도인지 — 동작 규칙은 `config.ts:562`에서 확인됨, 의도는 `추론`
- [ ] "12 hooks"가 무엇을 센 숫자인지(훅 입구 14개, Claude 플러그인 이벤트 6개)
- [ ] `mcp/standalone.ts` `resolveHandle`이 프록시/로컬 모드를 정하는 기준
- [ ] supersede 판정 임계값(`mem::remember`가 쓰는 `jaccardSimilarity` 기준값)

---

## 3. 기능 스펙 후보

gbrain 질문 ①~④와 같은 축으로 비교하려면 아래 행이 직접 대응한다(사용자 확정 전, 제안).

| 질문 | 대응 지도 행 | 상태 |
|---|---|---|
| ① 저장 위치·방식 | 1(훅 캡처·수신함), 2(압축), 4(remember), S1(KV) | 제안 |
| ② 메모리 호출 트리거 | 10(컨텍스트 주입), 24(MCP 도구), 27(스킬·훅) | 제안 |
| ③ 필요한 것만 LLM에 건네기 | 8(하이브리드 검색), 9(스마트 검색), 10(토큰 예산) | 제안 |
| ④ 자동 저장 판단 | 1, 3(세션 수명주기), 12(통합), 15(스킬 추출) | 제안 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙은 사용자 범위 승인 뒤 정한다. 승인 전 가장 먼저 읽을 곳:

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/functions/observe.ts` | `mem::observe` 72~426 | 저장 단계 순서(dedup → privacy → 저장 → 압축 → 색인) 확정 |
| `src/functions/context.ts` | `mem::context` 37~299 | 컨텍스트 블록 종류·순서·예산 절단 규칙 |
| `src/functions/search.ts`, `src/state/hybrid-search.ts` | `mem::search`, `HybridSearch` | 가중치·그래프 스트림·리랭커 |
| `src/functions/remember.ts` | `mem::remember` | supersede 기준과 `similarTo` |

---

## 5. 참고 사항 및 후속 제안

- 원본은 iii 엔진이 필요해 `bun`/`node`만으로 서버를 띄울 수 없다. 실행 실험(9장)은 엔진 바이너리 다운로드가 필요해 사용자 확인 대상이다. 순수 함수(`jaccardSimilarity`, `stripPrivateData`, RRF 계산 등)는 발췌 실행이 가능하다.
- gbrain 스펙과 같은 기능을 다시 스펙으로 쓰게 되면 각 스펙 2.3에 상대 스펙 링크와 차이를 적는다(4장 규칙).
