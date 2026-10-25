---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-23
updated: 2026-10-24
---

# Next Session Plan: gbrain

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 지도 44행, 구조도, Q1
- [x] 스펙 7개 `ready`: [ai-gateway](capabilities/ai-gateway.md)(37), [engine-and-schema](capabilities/engine-and-schema.md)(1), [page-storage-and-import](capabilities/page-storage-and-import.md)(2+3), [hybrid-search](capabilities/hybrid-search.md)(6), [memory-verbs](capabilities/memory-verbs.md)(11), [fact-extraction](capabilities/fact-extraction.md)(12), [ambient-context](capabilities/ambient-context.md)(16)
- [x] 통합 검토 4항목, 통합 흐름(overview 3절)
- 실행 한계: `bun`·`node_modules`가 없어 DB·핸들러·훅 본체는 실행하지 못했다. 순수 함수만 `deno`로 확인했다(`agent-memory/artifacts/gbrain/*-demos/`). 재구현 검증(4장 6번)은 하지 않았다.

## 2. 해결되지 않은 남은 질문

- [ ] Claude Code가 훅의 `additionalContext`·SessionStart stdout을 모델 컨텍스트에 넣는지, `_meta.brain_hot_memory`를 모델이 보는지(코드 주석은 "본다", `docs/protocol/MCP_META_CHANNELS.md`는 "주류 하네스는 안 준다"). 외부 시스템이라 실행으로만 확인 가능.
- [ ] LLM이 실제로 뽑아 주는 사실의 품질, 훅이 실제로 800ms 마감 안에 끝나는지.
- [ ] `gbrain put` 같은 단명 CLI가 종료 전에 embedding effect를 끝내는지(page-storage-and-import 확인 한계).

## 3. 기능 스펙 후보

승인 범위 밖이라 쓰지 않았다. 필요해지면 overview 1절 범위에 추가하고 4장으로 간다. 질문 ③과 가까운 것을 앞에 둔다.

| 기능 | 근거 | 상태 |
|---|---|---|
| 증거 전달(`assemble_evidence`, `search/evidence-delivery.ts` 1,712줄) — "LLM이 읽을 형태로 확장"하는 단계 | hybrid-search 보고, `ops/search.ts:1260` | 사용자에게 추가 여부를 물을 것(질문 ③ 직결) |
| 검색의 기본 켜진 부가 단계(별칭 fan-out, 관계형 회상, graph signals, collapse, rank priors) | hybrid-search 1.2 | 6행에 합칠지 별도 행으로 둘지 미정 |
| 신뢰 등급·쓰기 게이트(13행) | fact-extraction `backstop.ts:689-717`, `trust/taint.ts`. 기본은 flag 모드(저장을 막지 않음) | 지도 13행, 미작성 |
| 분할 저장(1 MiB 초과 페이지) | page-storage-and-import `page-body/*`, `ops/page-upload.ts` | 지도에 행 없음 |
| 관리 모드의 쓰기 소유권(`sources writer claim/…`, effect 실행기·복구) | page-storage-and-import `persistence/consumer.ts`, `effects.ts`, `ownership.ts` | 지도 19·33행에 흩어짐 |
| frontmatter 검증·복구 | `frontmatter-recovery.ts`, `markdown.ts:509-594` | 지도에 행 없음 |
| minions 잡 큐·워커·재시도(`facts-absorb` 실행 인프라) | fact-extraction `minions/handlers/facts-absorb.ts`, `facts/drain.ts` | 지도 31행, 미작성 |
| 대화 파서와 `extract-conversation-facts`, 코퍼스·세그먼트 은행·sweep | fact-extraction 경계 | 지도 22행과 겹침 |
| 멀티모달 임베딩·OCR | ai-gateway `gateway.ts:1890-2362` | 지도 3행·10행과 연결 |
| OpenClaw 컨텍스트 엔진의 reflex 레인(`buildReflexAddition`) | ambient-context `context-engine.ts:1367` | 지도 40행(부속) |
| 훅 등록·설치 경로(36행) | ambient-context R-01(이벤트 집합이 설치 경로마다 다름) | 지도 36행, 미작성 |

## 4. 다음에 볼 파일 및 함수

다음에 쓸 기능 스펙은 정해지지 않았다. 사용자가 범위를 정하면 3절에서 고른다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/core/search/evidence-delivery.ts` | `assemble_evidence`(`ops/search.ts:1260`) | 검색 결과를 LLM이 읽을 증거 형태로 만드는 규칙(후보 1순위) |
| `src/commands/setup.ts`, `commands/bootstrap.ts` | 훅 등록 | 설치 경로별 훅 이벤트 집합 |

## 5. 참고 사항 및 후속 제안

- 실행 확인을 늘리려면 사용자 승인으로 `bun`을 설치하고 PGLite 메모리 DB에서 `put_page → search → remember → recall`을 돌려 본다(워크플로 9장: 새 패키지 설치는 먼저 묻는다).
- 스펙은 모두 SHA `63f62b2c` 기준이다. 레포가 갱신되면 워크플로 5장대로 `sources`가 겹치는 스펙부터 다시 본다.
