---
sha: "70517d2bdf302a0aed11ca470151ee854e74c678"
created: 2026-10-25
updated: 2026-10-25
---

# agentmemory Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/rohitg00/agentmemory`
- **기준 SHA**: `70517d2b` (2026-10-23, `main`), `v0.9.30-52-g70517d2`, `package.json` version 0.9.30
- **작업트리 상태**: Clean (`agent-memory/artifacts/agentmemory/repo-metadata.txt`)
- **분석 목적**: 학습·설계 참고 — gbrain 분석과 같은 질문 ①~④(저장 위치·방식 / 메모리 호출 트리거 / 필요한 것만 LLM에 건네는 방법 / 자동 저장 판단)로 비교한다. 이번 세션은 기능 지도까지. (2026-10-25 사용자 요청: "초기 작업")
- **라이선스**: Apache License 2.0 — `LICENSE`(본문 끝에 표준 "Licensed under the Apache License, Version 2.0" 부록만 있고 저작권자 줄은 없다). `packages/mcp/LICENSE`도 Apache 2.0 텍스트다. 그 밖의 LICENSE 파일은 추적 파일에 없다(`git ls-files`). `package.json`의 `license` 필드는 `Apache-2.0`.
- **언어/규모**: TypeScript(ESM, Node ≥ 20, `engines.node`). 추적 파일 1,016개(test 310 / src 244 / website 91 / plugin 87 / assets 69 / docs 43 / READMEs 32 / scripts 27 / eval 21 / benchmark 20 / integrations 17 / deploy 17 / packages 4 / examples 3). 런타임 의존성은 `iii-sdk`·`@iii-dev/helpers` 0.22.1, `@anthropic-ai/sdk`, `@anthropic-ai/claude-agent-sdk`, `zod`, `yaml`, `json5`, `@clack/prompts`, `dotenv`(`package.json`). 코드 확인.
- **분석 대상 제품**: 루트 패키지 `@agentmemory/agentmemory`(`bin: agentmemory → dist/cli.mjs`, `main: dist/index.mjs`; 빌드 입구 `src/index.ts`·`src/cli.ts`·`src/mcp/standalone.ts`·훅 15개, `tsdown.config.ts`). 중첩·별도 배포 단위: `packages/mcp`(`@agentmemory/mcp` shim), `integrations/{pi,openclaw,hermes,filesystem-watcher}`(호스트별 직접 통합), `plugin/`(Claude Code·Codex·Devin·Cursor·Copilot·OpenCode용 매니페스트·훅·스킬 묶음), `website/`(Next.js 15 랜딩), `deploy/{fly,railway,render,coolify}`, `examples/python`, `eval/`·`benchmark/`.
- **런타임 모양**: 이 프로젝트는 단독 서버가 아니라 **iii 엔진**(별도 바이너리, 핀 0.22.1)의 *worker*로 동작한다. 엔진이 HTTP(3111)·상태 KV·큐·pubsub·cron·stream(3112)을 제공하고(`iii-config.yaml`), agentmemory는 `registerWorker`(`iii-sdk`)로 붙어 함수 `mem::*`를 등록한다(`src/index.ts`). 뷰어는 별도 포트 3113. 코드 확인.
- **스펙 범위**: 아직 승인 전. 이번 세션은 지도까지(5절 다음 단계 참조).

---

## 2. 프로젝트 개요

README 첫 줄의 주장: "코딩 에이전트가 모든 것을 기억한다. 다시 설명할 필요 없다." 에이전트의 훅(도구 사용 후, 프롬프트 제출, 세션 시작·종료 등)이 로컬 서버로 이벤트를 보내면, 서버가 비밀값을 지우고 관찰(observation)로 저장·색인해 두었다가 MCP 도구·REST·(옵션) 훅 출력으로 검색 결과를 돌려준다. 검색은 BM25 + 벡터 + 지식 그래프를 RRF(k=60)로 합친다. 저장된 관찰은 요약 → 의미 기억 → 절차 기억의 4계층으로 정리되고, 시간이 지나면 감쇠·삭제된다. 멀티 에이전트용 작업 조정(액션·리스·시그널)과 팀·mesh 동기화, 실시간 뷰어도 같은 서버에 있다. (출처: `README.md` "How It Works"·"Key Capabilities", 코드 대조는 아래 지도의 진입점. 검증: 대조한 항목만 코드 확인)

핵심 설계 네 가지(코드로 확인한 것):
1. **함수 등록 + 이벤트 트리거 구조**: 모든 기능이 `sdk.registerFunction("mem::<이름>", …)`이고(`src/` 전체에서 고유 `mem::*` 160개), REST 라우트(`src/triggers/api.ts`, `api::*` 함수 145개)·MCP(`src/mcp/server.ts`)·이벤트(`src/triggers/events.ts`)가 `sdk.trigger({function_id: "mem::…"})`로 호출한다. 코드 확인(등록부 grep, 호출 예: `events.ts:125` `mem::summarize`).
2. **훅은 REST 클라이언트**: 훅 스크립트는 로컬 서버의 `POST /agentmemory/{observe,session/start,…}`를 호출하는 독립 `.mjs`이고(`src/hooks/*.ts` → `plugin/scripts/*.mjs`로 빌드·커밋), 서버가 죽어 있으면 스풀 파일에 쌓았다가 다시 보낸다(`src/hooks/_capture.ts`, `src/capture/spool.ts`). 코드 확인(진입부).
3. **주입은 기본 꺼짐**: `AGENTMEMORY_INJECT_CONTEXT`가 `"true"`일 때만 SessionStart·PreToolUse 훅이 컨텍스트를 stdout으로 내보낸다(`src/config.ts:562` `isContextInjectionEnabled`, `src/hooks/session-start.ts:17,63`). README "Memory Pipeline"은 "Inject into conversation"까지 한 흐름처럼 쓰지만 기본 동작은 캡처만이다 — 문서와 구현의 차이로 아래에 적는다. 코드 확인.
4. **LLM 없이도 도는 기본값**: 압축은 합성(규칙 기반)이 기본이고 LLM 압축은 `AGENTMEMORY_AUTO_COMPRESS=true`일 때만(`src/config.ts:549`), 그래프 추출은 `GRAPH_EXTRACTION_ENABLED=true`일 때만(`:492`), 통합은 `CONSOLIDATION_ENABLED` 또는 LLM 공급자 감지 시(`:534`), 슬롯은 `AGENTMEMORY_SLOTS=true`일 때만(`src/functions/slots.ts:100`). 임베딩 없으면 BM25만. 코드 확인.

### 기능 지도

<!--
검증 수준 표기 (이 세션은 지도 단계):
- "코드 확인(진입점)": 진입 함수의 등록·시그니처·초반 로직(또는 설정 게이트)을 직접 읽음.
- "추론": 파일 이름·README·MCP 도구 설명으로 판단, 본문은 열지 않음.
스펙 단계(4장)에서 R-ID 단위로 다시 붙인다. 모든 행의 스펙 상태는 미작성이다(범위 승인 전).
`mem::*` 이름 뒤 숫자는 등록 줄(`registerFunction`)이다.
-->

> 조사 방식: 메인 세션이 `registerFunction`·`api_path`·MCP 도구 레지스트리·CLI 명령표·`tsdown.config.ts` 훅 목록을 grep으로 전부 모은 뒤, 아래 행의 진입점 일부를 열어 확인했다. 서브에이전트는 쓰지 않았다.

#### A. 캡처 (쓰기 경로)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 훅 캡처와 내구성 수신함 | 에이전트의 훅(도구 사용 전·후·실패, 프롬프트, 서브에이전트, 중단 등) → 로컬 서버 `POST /observe`·`/capture`. 서버 불가 시 스풀 파일에 쌓고 다음 훅이 드레인. 서버 쪽은 이벤트 ID로 중복 제거, 5분 창 SHA-256 dedup, `<private>`·키 패턴 삭제 후 원본 관찰 저장·색인 | `src/hooks/post-tool-use.ts` `main`, `src/hooks/_capture.ts` `captureObservation`, `src/capture/spool.ts`, `src/functions/capture.ts` `mem::capture`(524)·`mem::capture-drain`(557), `src/functions/observe.ts` `mem::observe`(72), `functions/privacy.ts` `stripPrivateData`, `functions/dedup.ts` `DEDUP_WINDOW_MS` | S1, S2, S4 | 핵심 | `capabilities/hook-capture.md` · 미작성 | 코드 확인(진입점·privacy 패턴·dedup 상수) / 수신함 상태 전이는 추론 |
| 2. 관찰 압축과 복구 | 원본 관찰 → 제목·서술·개념·파일을 가진 `CompressedObservation`. 기본은 규칙 기반 합성(`inferType`), LLM 압축은 opt-in. 실패한 압축은 상태를 남겨 재시도·복구 | `src/functions/compress-synthetic.ts` `buildSyntheticCompression`, `compress.ts` `mem::compress`(263), `compression-state.ts`, `compression-recovery.ts` `mem::compression-retry`(171), `prompts/compression.ts` | 1, S3 | 핵심 | `capabilities/observation-compression.md` · 미작성 | 코드 확인(진입점·게이트) |
| 3. 세션 수명주기와 요약 | `POST /session/start`·`/session/end`, Stop 훅(턴마다 end 호출). 종료 이벤트가 `mem::summarize` → (옵션) 슬롯 반성·그래프 추출 → 쿨다운 안에서만 전역 통합·결정화·스킬 추출을 비동기로 호출. 유휴 세션 확정(`session-finalize`)·오래된 세션 정리(`session-sweep`), 요약 복구·수리 | `src/triggers/events.ts` `event::session::stopped`(123)·`event::session::ended`(190), `src/functions/summarize.ts` `mem::summarize`(469), `session-finalize.ts`(65), `session-sweep.ts`, `summary-recovery.ts`(95·102), `state/session-index.ts` | 1, 2, S1 | 핵심 | `capabilities/session-lifecycle.md` · 미작성 | 코드 확인(`events.ts` 123~210 전체) / 요약 프롬프트·복구는 추론 |
| 4. 명시적 저장·삭제와 버전 | `memory_save`/`POST /remember`로 통찰·결정·패턴 저장(TTL·개념·파일·출처 관찰 연결). 비슷한 기존 메모리는 대체(supersede)하고 `similarTo` 힌트 반환, 대체된 버전은 검색 색인에서 빠지고 KV에 이력 유지. `memory_governance_delete`·`POST /forget`로 삭제 | `src/functions/remember.ts` `mem::remember`(31)·`mem::forget`(261), `state/schema.ts` `jaccardSimilarity`, `functions/relations.ts` `mem::relate`(57)·`mem::evolve`(146) | 2, S1, S2, S5 | 핵심 | `capabilities/remember-forget.md` · 미작성 | 코드 확인(시그니처·유사도 함수) / supersede 임계값은 미확인 |
| 5. 커밋 연결·브랜치 인식 | 커밋 후 훅이 세션과 커밋을 잇고(`/session/commit`), `memory_commit_lookup`·`memory_commits`로 SHA→세션 조회, 워크트리·브랜치별 세션 조회 | `src/hooks/post-commit.ts`, `src/functions/branch-aware.ts` `mem::detect-worktree`(22)·`mem::branch-sessions`(125), `api::session::commit`·`api::session::by-commit`(`triggers/api.ts`) | 3 | 핵심 | `capabilities/commit-branch-link.md` · 미작성 | 추론(훅 이름·MCP 설명) + 코드 확인(등록) |
| 6. 이미지 메모리 | 도구 출력의 base64 이미지를 디스크에 저장하고 참조 카운트를 관리, CLIP 임베딩으로 `memory_vision_search`(텍스트→스크린샷), 할당량 정리 | `src/functions/observe.ts` `extractImage`, `utils/image-store.ts`, `functions/image-refs.ts`, `vision-search.ts`, `image-quota-cleanup.ts`, `providers/embedding/clip.ts` | 1, S3 | 핵심 | `capabilities/image-memory.md` · 미작성 | 코드 확인(`extractImage`) / 나머지 추론 |
| 7. 마크다운 파일 압축 | `memory_compress_file`: 헤딩·URL·코드블록을 보존하며 파일 크기 줄임 | `src/functions/compress-file.ts` `mem::compress-file` | S3 | 부속 | `capabilities/compress-file.md` · 미작성 | 추론(MCP 설명) |

#### B. 검색과 주입

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 8. 하이브리드 검색 | `memory_recall`(`mem::search`): 질의 → BM25(어간·동의어·CJK 분절) + 벡터(임베딩 있을 때) + 그래프 순위를 RRF `k=60`으로 합치고 세션당 최대 3개로 다양화. 색인은 디스크에 주기 저장하고 벡터는 대기 로그로 크래시 복구. `agentId` 필터, 대체된 버전 제외 | `src/functions/search.ts` `mem::search`(730), `state/hybrid-search.ts` `HybridSearch`(`RRF_K` 24, `diversifyBySession` 293), `state/search-index.ts`, `state/vector-index.ts`, `state/index-persistence.ts`, `state/reranker.ts`, `functions/query-expansion.ts` | 1, S1, S3, S5 | 핵심 | `capabilities/hybrid-search.md` · 미작성 | 코드 확인(RRF 상수·다양화·등록) / 가중치·리랭커·복구 경로는 추론 |
| 9. 스마트 검색·타임라인·프로필 | `memory_smart_search`(점진 공개: 검색 → ID로 펼치기, 그래프 매칭 융합), `memory_timeline`(기준점 전후), `memory_profile`(상위 개념·파일), `memory_file_history`, `memory_patterns` | `src/functions/smart-search.ts` `mem::smart-search`(85), `timeline.ts`(14), `profile.ts`(13), `file-index.ts` `mem::file-context`(23), `patterns.ts`(26) | 8, 13 | 핵심 | `capabilities/smart-search-views.md` · 미작성 | 코드 확인(등록) / 본문 추론 |
| 10. 컨텍스트 조립·주입 | `POST /session/start`가 `mem::context`로 프로젝트 프로필·최근 요약·상위 관찰·고정 슬롯·교훈을 토큰 예산(`TOKEN_BUDGET` 기본 2000, 길이/3 추정) 안에서 블록으로 조립. 훅이 `INJECT_CONTEXT=true`일 때만 stdout으로 주입(호스트별 JSON 포맷 다름). PreToolUse `enrich`·PreCompact 재주입·슬라이딩 윈도 enrich는 별도 | `src/functions/context.ts` `mem::context`(37), `triggers/api.ts` `/session/start` 핸들러(`mem::context` 호출 약 1132줄), `src/hooks/session-start.ts` `contextPayload`, `hooks/pre-tool-use.ts`, `hooks/pre-compact.ts`, `functions/enrich.ts`(12), `sliding-window.ts` | 3, 8, 11, 14, S5 | 핵심 | `capabilities/context-injection.md` · 미작성 | 코드 확인(`mem::context` 초반·훅 게이트) / 블록 순서·pre-compact·enrich는 추론 |
| 11. 슬롯·코어 메모리 | 크기 제한이 있는 편집 가능한 고정 슬롯(`memory_slot_*`: list/get/create/append/replace/delete), 중요도 가진 코어 메모리, 자동 페이징, Stop 시 슬롯 반성(TODO·패턴·touched files). 둘 다 opt-in | `src/functions/slots.ts` `isSlotsEnabled`(100)·`mem::slot-*`(202~342), `functions/working-memory.ts` `mem::core-add`(39)·`mem::working-context`(100)·`mem::auto-page`(194) | S1 | 핵심 | `capabilities/slots-core-memory.md` · 미작성 | 코드 확인(게이트·등록) / 반성 로직은 추론 |

#### C. 기억 정제

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 12. 4계층 통합 | `memory_consolidate`/`POST /consolidate-pipeline`: 관찰 → 에피소드(요약) → 의미 → 절차로 LLM이 정리, 감쇠 일수 적용. 세션 종료 후 쿨다운 안에서 자동, 주기 타이머(기본 7,200,000ms). `mem::consolidate`는 프로젝트별 단순 통합 | `src/functions/consolidation-pipeline.ts` `mem::consolidate-pipeline`(86), `consolidate.ts`(70), `prompts/consolidation.ts`, `triggers/events.ts` `consolidationDue`, `config.ts` `isConsolidationEnabled`(534) | 3, S3 | 핵심 | `capabilities/consolidation.md` · 미작성 | 코드 확인(게이트·티어 분기 시작부) / 프롬프트·병합 규칙은 추론 |
| 13. 지식 그래프 | 관찰에서 엔티티·관계 추출(LLM, opt-in), 노드·간선·이름 색인·차수·멤버십을 KV에 저장, BFS 질의, 시간 축 그래프(`temporal-query`), 그래프 색인 마이그레이션·재개·압축, graphify 가져오기 | `src/functions/graph.ts` `mem::graph-extract`(722)·`mem::graph-query`(808)·`graph-compact`(967), `temporal-graph.ts`(163·302), `state/graph-*.ts`, `functions/graph-import.ts`, `docs/graph-search.md` | 1, S1, S3 | 핵심 | `capabilities/knowledge-graph.md` · 미작성 | 코드 확인(등록·게이트) / 색인 구조는 추론 |
| 14. 교훈·반성·인사이트 | `memory_lesson_save/recall/delete`(신뢰도 있고 중복이면 강화, 감쇠), `memory_reflect`(그래프 클러스터 → 인사이트 합성), `memory_insight_list` | `src/functions/lessons.ts` `mem::lesson-save`(91)·`recall`(175), `reflect.ts` `mem::reflect`(308)·`insight-list`(505), `docs/reflection-evidence.md` | 13, 12, S3 | 핵심 | `capabilities/lessons-reflection.md` · 미작성 | 코드 확인(시그니처) / 강화·감쇠 규칙은 추론 |
| 15. 스킬 추출 | 완료된 세션에서 절차 기억(`ProceduralMemory`)을 뽑고 `skill-match`로 재사용 | `src/functions/skill-extract.ts` `mem::skill-extract`(108)·`skill-list`(243)·`skill-match`(256) | 12, S3 | 핵심 | `capabilities/skill-extract.md` · 미작성 | 코드 확인(시그니처·완료 세션 조건) |
| 16. 보존·망각·거버넌스 | 에빙하우스식 보존 점수와 티어, 임계 미만 삭제(`retention-evict`), TTL 만료·모순·저가치 자동 삭제(`auto-forget`), 한도 초과 퇴출(`evict`), 감사 로그(월별 샤드, 보존 기간), 대량 삭제, 대체된 메모리의 연쇄 표시(`cascade-update`) | `src/functions/retention.ts`(129·294), `auto-forget.ts`(29), `evict.ts`(115), `governance.ts`(34·105·237), `audit.ts`, `cascade.ts`(12), `access-tracker.ts` | 4, 12 | 핵심 | `capabilities/retention-forgetting.md` · 미작성 | 코드 확인(시그니처·기본 임계 상수) / 점수식은 추론 |
| 17. 출처 검증·패싯 | `memory_verify`: 메모리 → 출처 관찰 → 세션까지 인용 사슬 반환. `memory_facet_tag/query`: `차원:값` 태그를 액션·메모리·관찰에 붙이고 AND/OR 질의 | `src/functions/verify.ts` `mem::verify`(11), `facets.ts` `mem::facet-tag`(54)·`facet-query`(149) | 4, 18 | 핵심 | `capabilities/verify-facets.md` · 미작성 | 코드 확인(`verify` 초반) / 패싯 질의는 추론 |

#### D. 멀티 에이전트 조정

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 18. 액션 그래프·프런티어·루틴 | 의존성 있는 작업 항목 생성·갱신(`done` 시 후행 해제), 막히지 않은 액션을 우선순위로 정렬(`frontier`)·단일 추천(`next`), 얼려 둔 루틴을 실행해 단계별 액션 생성 | `src/functions/actions.ts` `mem::action-create`(10)·`action-update`(101), `frontier.ts` `mem::frontier`(14)·`mem::next`(119), `routines.ts` `mem::routine-create`(9)·`routine-run`(90) | S1, S2 | 핵심 | `capabilities/action-graph.md` · 미작성 | 코드 확인(시그니처·검증 시작부) / 점수식은 추론 |
| 19. 외부 게이트: 체크포인트·센티널 | CI·승인·배포 같은 외부 조건이 액션을 막고 풀게 함. 센티널은 webhook·timer·threshold·pattern·approval·custom 감시자로 외부에서 트리거 | `src/functions/checkpoints.ts`(9·87), `sentinels.ts` `mem::sentinel-create`(18)·`trigger`(163)·`check`(207)·`expire`(375) | 18 | 핵심 | `capabilities/action-gates.md` · 미작성 | 코드 확인(타입 목록) / 해제 규칙은 추론 |
| 20. 스케치·결정화 | 임시 액션 그래프(TTL 기본 1시간)를 만들고 승격하거나 폐기, 완료된 액션 사슬을 LLM 다이제스트(서술·결과·파일·교훈)로 압축 | `src/functions/sketches.ts`(9·132·178·254), `crystallize.ts` `mem::crystallize`(24)·`auto-crystallize`(149) | 18, S3 | 핵심 | `capabilities/sketch-crystallize.md` · 미작성 | 코드 확인(기본 TTL·프롬프트 형식) |
| 21. 리스와 시그널 | 액션에 대한 배타적 리스(획득·갱신·반납·만료 정리)로 중복 작업 방지, 에이전트 간 메시지(스레드·타입·TTL·읽음 처리) | `src/functions/leases.ts` `mem::lease-acquire`(12), `signals.ts` `mem::signal-send`(8)·`signal-read`(60)·`signal-threads`(119) | 18 | 핵심 | `capabilities/leases-signals.md` · 미작성 | 코드 확인(등록) / 만료 규칙 추론 |
| 22. 팀 메모리와 mesh 동기화 | 팀 네임스페이스에 메모리·패턴·관찰 공유와 피드(`team-share/feed/profile`), 다른 agentmemory 인스턴스(피어)와 메모리·액션 동기화(`mesh-*`). mesh 피어 URL은 http(s)만 허용하고 사용자 정보·localhost·사설 IP(DNS 결과 포함)를 거부한다(`isAllowedUrl`) | `src/functions/team.ts` `mem::team-share`(23), `mesh.ts` `isPrivateIP`·`isAllowedUrl`·`mem::mesh-sync`(172)·`mesh-receive`(312), `config.ts` `loadTeamConfig` | 4, S1, S4 | 핵심 | `capabilities/team-mesh.md` · 미작성 | 코드 확인(검증 함수 초반) / 동기화 프로토콜은 추론 |

#### E. 입구와 배포 표면

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 23. REST API | 엔진 HTTP(3111) 위 `/agentmemory/*` 고유 경로 132개(`api_path` 143건 = 같은 경로의 GET·POST 등 포함, `api::*` 함수 145개, livez/health 포함), 베어러 비밀·origin·host 가드 | `src/triggers/api.ts` `registerApiTriggers`, `src/auth.ts` `checkRequestGuard`(115)·`timingSafeCompare`, `src/secret-store.ts` | S4 | 핵심 | `capabilities/rest-api.md` · 미작성 | 코드 확인(경로·함수 집계, 가드 시그니처) |
| 24. MCP 입구 | 도구 54개(`AGENTMEMORY_TOOLS=core`면 8개), 리소스 6, 프롬프트 3. 두 경로: 전체 서버(`mcp::tools::call` → `mem::*`)와 독립 stdio(`standalone`: 실행 시 `resolveHandle()`로 모드를 정해, 서버를 찾으면 REST로 프록시하고 못 찾으면 인메모리 KV로 7개 도구만 직접 처리. 프록시 호출이 실패하면 핸들을 무효화하고 로컬 KV로 되돌아가지만, `isProxyRequired()`이거나 인증 오류·`memory_sessions`면 되돌아가지 않고 오류) | `src/mcp/tools-registry.ts` `getAllTools`(1009)·`ESSENTIAL_TOOLS`(998), `src/mcp/server.ts` `registerMcpEndpoints`, `src/mcp/standalone.ts` `IMPLEMENTED_TOOLS`, `mcp/rest-proxy.ts`, `mcp/plugin-bridge.ts` | 8~22, S4 | 핵심 | `capabilities/mcp-surface.md` · 미작성 | 코드 확인(도구 54개 일치, 독립 모드 분기·7개 목록·폴백 조건 `standalone.ts` 497~535) / `resolveHandle` 판정 기준은 미확인 |
| 25. CLI와 엔진 구동 | `agentmemory`(서버 부팅), `init·connect·status·console·doctor·demo·upgrade·stop·remove·mcp·import-jsonl·capture·compression·graph-index`. 첫 실행 온보딩, iii 엔진 설치·설정·기동, 데이터 디렉터리 결정 | `src/cli.ts` `commands` 표(4260)·`main`, `src/cli/onboarding.ts`, `engine-install.ts`, `engine-launch.ts`, `engine-config.ts`, `src/cli-data-dir.ts`, `src/runtime-paths.ts` | S1 | 핵심 | `capabilities/cli-and-engine.md` · 미작성 | 코드 확인(명령표) / 온보딩·엔진 설치 흐름은 추론 |
| 26. 에이전트 커넥터 패밀리 | `agentmemory connect <agent>`가 호스트별 설정 파일(MCP 항목·훅·가이드라인)을 쓰고 `--dry-run`·`--force`·백업 지원. 21개 어댑터(claude-code, copilot-cli, codex, cursor, devin, gemini-cli, qwen, antigravity ×2, kiro, warp, cline, continue, zed, droid, dsh, opencode, openclaw, hermes, pi, openhuman) | `src/cli/connect/index.ts` `ADAPTERS`, `types.ts` `ConnectAdapter`, `json-mcp-adapter.ts`(공통 JSON MCP), `guidelines.ts`, 어댑터별 파일 | 25, 24 | 핵심(패밀리) | `capabilities/connect-adapters.md` · 미작성 | 코드 확인(목록 21개) / 공통 계약·개별 차이는 추론 |
| 27. 호스트 플러그인 묶음 | Claude Code·Codex·Devin·Cursor·Copilot·OpenCode가 설치하는 플러그인: 매니페스트, 훅 정의(`hooks*.json`, Claude 기준 6개 이벤트), `.mcp*.json`, 스킬 17개(호출형 9 + 참조형 8) | `plugin/plugin.json`, `plugin/hooks.json`, `plugin/hooks/hooks.{codex,copilot,devin,droid,antigravity}.json`, `plugin/scripts/*.mjs`(훅 빌드 산출물), `plugin/skills/*/SKILL.md`, `scripts/plugins/*` | 1, 24 | 핵심 | `capabilities/host-plugins.md` · 미작성 | 코드 확인(`hooks.json`·스킬 목록) / 호스트별 차이는 추론 |
| 28. 뷰어와 실시간 스트림 | `localhost:3113` 웹 뷰어(탭 12개: Overview, Memories, Lessons, Crystals, Graph, Sessions, Actions, Replay, Activity, Profile, Health, Audit — `viewer/index.html:1461~1480`). 서버는 Host 허용 목록으로 DNS rebinding을 막고 REST로 프록시. 서버→뷰어 실시간 갱신은 iii stream(`mem-live`) | `src/viewer/server.ts` `startViewerServer`, `viewer/index.html`(9,153줄 단일 파일), `state/viewer-stream.ts`, `state/viewer-counts.ts`, `triggers/viewer-streams.ts` | 23, S1 | 핵심 | `capabilities/viewer.md` · 미작성 | 코드 확인(서버 가드 주석·탭 목록) / 각 탭의 데이터 출처는 추론 |
| 29. 세션 리플레이와 JSONL 가져오기 | 저장된 세션을 이벤트 타임라인으로 재생, 에이전트 JSONL 로그(`~/.claude` 등)를 읽어 세션으로 가져오기(`import-jsonl`) | `src/functions/replay.ts` `mem::replay::load`·`mem::replay::import-jsonl`, `src/replay/jsonl-parser.ts`, `replay/timeline.ts`, `cli.ts` `runImportJsonl`, `scripts/backfill-imported-sessions.sh` | 3, 28 | 핵심 | `capabilities/session-replay.md` · 미작성 | 추론(파일명·README) + 코드 확인(등록) |
| 30. 내보내기·가져오기·브리지 | 전체 JSON export/import(큰 저장소는 페이지·컬렉션 선택), Obsidian 마크다운 내보내기, Claude Code `MEMORY.md` 읽기·프로젝트 범위 내보내기(기존 파일 보존), git 스냅샷 생성·복원, 스키마 마이그레이션 | `src/functions/export-import.ts`(128·297), `obsidian-export.ts`(242), `claude-bridge.ts`(128·165), `snapshot.ts` `gitExec`·`mem::snapshot-create`(58)·`restore`(179), `migrate.ts`(87) | 4, S1 | 핵심 | `capabilities/export-import-bridge.md` · 미작성 | 코드 확인(등록·git 호출 방식) / 형식 세부는 추론 |
| 31. 진단·헬스·자가복구 | `memory_diagnose`(액션·리스·센티널·스케치·시그널 등 점검)·`memory_heal`(막힌 상태 해제·만료 리스 정리), 프로세스 헬스 모니터(힙·CPU·연결 상태 임계), `doctor` CLI, 스트림 릴레이 프로브 | `src/functions/diagnostics.ts` `mem::diagnose`(47)·`mem::heal`(634), `src/health/monitor.ts` `registerHealthMonitor`, `health/thresholds.ts`, `src/cli/doctor-diagnostics.ts` | 18~21 | 핵심 | `capabilities/diagnostics-health.md` · 미작성 | 코드 확인(등록·헬스 수집 시작부) / 임계·수리 규칙은 추론 |

#### F. 부속 (라이브러리 본체와 별개인 배포·개발 단위)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 32. 호스트 직접 통합 | pi 확장, OpenClaw 네이티브 플러그인(메모리 슬롯 선택·대화 접근 권한), Hermes 메모리 공급자(프로필·화자별 범위), 파일 변경을 관찰로 보내는 fs-watcher | `integrations/pi/index.ts`, `integrations/openclaw/plugin.mjs`, `integrations/hermes/__init__.py`, `integrations/filesystem-watcher/watcher.mjs` | 23 | 부속 | `capabilities/host-integrations.md` · 미작성 | 추론(README) |
| 33. 평가·벤치마크 | LongMemEval·coding-life·lifecycle·recall 품질 평가(실제 CLI를 임시 홈·포트로 띄워 HTTP 어댑터로 측정), 부하(100k)·캡처 비용 벤치 | `eval/runner/*.ts`, `eval/README.md`, `benchmark/*.ts`, `docs/benchmarks/`, `src/eval/*`(런타임 품질 점수·자가 교정) | 8, 1 | 부속 | `capabilities/eval-benchmark.md` · 미작성 | 추론(README) |
| 34. 배포 템플릿 | fly·railway·render·coolify용 Dockerfile·설정. `/data` 볼륨, 첫 부팅 시 HMAC 비밀 생성, 3111만 공개 | `deploy/README.md`, `deploy/*/` | 25 | 부속 | `capabilities/deploy-templates.md` · 미작성 | 추론(README) |
| 35. 웹사이트 | Next.js 15 랜딩·비교·변경 이력 페이지, `llms.txt` | `website/app/page.tsx`, `website/README.md` | — | 부속 | `capabilities/website.md` · 미작성 | 추론(README) |
| 36. `@agentmemory/mcp` shim | `npx @agentmemory/mcp`이 본 패키지의 standalone MCP를 그대로 실행 | `packages/mcp/bin.mjs`, `packages/mcp/package.json` | 24 | 부속 | `capabilities/mcp-shim.md` · 미작성 | 추론(README) |
| 37. 파이썬 예제 | REST를 호출하는 quickstart·observe/recall 예제 | `examples/python/*.py` | 23 | 부속 | `capabilities/python-examples.md` · 미작성 | 추론 |
| 38. 개발·릴리스 스크립트 | 릴리스 게이트(패키지 상태 시작·복구·그래프 색인·스킬·OpenClaw 검증), 스킬 생성·검사, 문서 동기화, 엔진 해시, env 예시 검사 | `scripts/release-gate/*.mjs`, `scripts/skills/generate.ts`, `scripts/docs-sync.ts`, `scripts/engine-hashes.mjs` | — | 부속 | `capabilities/dev-scripts.md` · 미작성 | 추론(`package.json` scripts) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 상태 저장소와 KV 네임스페이스 | 거의 전부 | `src/state/kv.ts` `StateKV`(backend `file`\|`redis`, 업데이트 연산 `set/remove/merge`), `src/state/schema.ts` `KV`(약 70개 스코프 이름)·`STREAM`·`generateId`·`fingerprintId`, `src/state/keyed-mutex.ts` `withKeyedLock`, `iii-config.yaml`(`iii-state` file_based) | `capabilities/state-and-kv.md` · 미작성 | 코드 확인(스코프 표·설정 파일) |
| S2. 데이터 모델 | 1~22 | `src/types.ts` `Session`(1)·`RawObservation`(54)·`CompressedObservation`(94)·`Memory`(136)·`SessionSummary`(170)·`SemanticMemory`(617)·`ProceduralMemory`(631)·`GraphNode`(466)·`Action`(791)·`Lease`(828)·`Signal`(869)·`Lesson`(945)·`Insight`(963) | 스펙은 각 기능에 분산 | 코드 확인(정의 위치) |
| S3. LLM·임베딩 공급자 | 2, 6, 7, 8, 12~15, 20 | `src/providers/index.ts` `createProvider`·`createFallbackProvider`(기본 모델명 포함), `resilient.ts`·`circuit-breaker.ts`·`fallback-chain.ts`, 공급자 7종(anthropic, openai, openrouter, minimax, agent-sdk, noop, gemini — gemini는 Google의 OpenAI 호환 엔드포인트를 `OpenRouterProvider`로 호출, `providers/index.ts` `createBaseProvider`), 임베딩 `providers/embedding/*`(local, openai, gemini, cohere, voyage, openrouter, clip), `types.ts` `MemoryProvider`(220)·`EmbeddingProvider`(310) | `capabilities/providers.md` · 미작성 | 코드 확인(팩토리·기본 모델) / 서킷 브레이커 임계는 추론 |
| S4. 인증·요청 가드 | 23, 24, 25, 28, 훅 | `src/auth.ts` `checkRequestGuard`, `src/secret-store.ts` `ensureServerSecret`(98)·`resolveClientSecret`(87), 훅의 `Authorization: Bearer` | `capabilities/auth.md` · 미작성 | 코드 확인(시그니처) / 비밀 파일 위치·권한은 추론 |
| S5. 에이전트 범위와 출처 | 4, 8, 10, 22 | `src/config.ts` `getAgentId`·`isAgentScopeIsolated`(460), `mem::context` 초반의 isolated 거부 로직(`context.ts:37~70`), `types.ts` `Origin` | 스펙은 각 기능에 분산 | 코드 확인(`mem::context`) / `Origin` 부여 지점은 미탐색 |
| S6. 설정·환경변수 | 거의 전부 | `src/config.ts`(676줄: `loadConfig`·`isGraphExtractionEnabled`·`isAutoCompressEnabled`·`isConsolidationEnabled` 등 게이트), `~/.agentmemory/.env` | `capabilities/config.md` · 미작성 | 코드 확인(게이트 함수) |

**대조한 범위와 미탐색 영역**
- 대조: README의 "How It Works"(파이프라인·4계층·캡처 훅 표)·"Key Capabilities"·"Search"·"54 Tools"; `registerFunction("mem::*")` 전수(grep), REST `api_path` 집계, MCP 도구 레지스트리 54개 이름·설명, CLI `commands` 표, `plugin/hooks.json`, `tsdown.config.ts`의 훅 입구 목록, `iii-config.yaml`, 커넥터 `ADAPTERS`.
- 문서와 구현의 차이:
  1. README 파이프라인 도식은 "SessionStart → … → Inject into conversation"으로 읽히지만 주입은 `AGENTMEMORY_INJECT_CONTEXT=true`일 때만이다(기본 꺼짐, `config.ts:562`, README 환경 변수 블록도 "OFF by default"). 코드 확인.
  2. README는 "20 adapters"(`README.md:131`)라 쓰지만 `ADAPTERS`는 21개다(`src/cli/connect/index.ts`). 코드 확인.
  3. README는 "12 hooks"(`README.md:73,428,646`)라 쓰지만 훅 입구는 `tsdown.config.ts` 기준 14개(+`_capture` 헬퍼), `plugin/hooks.json`(Claude용)은 6개 이벤트만 선언한다. 어느 쪽을 "12"로 센 것인지는 미확인.
  4. README "17 skills"는 `plugin/skills/`의 디렉터리 17개(+`_shared`)와 일치한다. 코드 확인.
- 미탐색:
  - 테스트 310개 파일은 열지 않았다(기본 규칙). 사례가 필요하면 스펙 단계에서 사례명만 찾는다.
  - `src/functions/`의 83개 파일 중 helper(`access-tracker`, `observation-source*`, `disk-size-manager`, `recent-searches-sweep`, `path-guard` 등)와 `src/state/` 일부(`frame-guard`, `list-query`, `memory-utils`), `src/prompts/*` 본문, `src/telemetry/`, `src/eval/*`는 이름만 봤다.
  - `src/triggers/api.ts`(4,171줄)와 `src/mcp/server.ts`(1,808줄)의 개별 핸들러, `src/cli.ts`(4,292줄)의 온보딩·업그레이드·제거 흐름, `src/cli/connect/*` 어댑터별 본문.
  - `website/`(91개 파일), `docs/benchmarks/data/`, `READMEs/`(번역), `assets/`.
  - 외부 시스템 동작: iii 엔진 자체(별도 바이너리·레포 `iii-hq/iii`), 호스트별 훅·플러그인 사양(Claude Code, Codex 등), 임베딩·LLM 공급자 API. 모두 `미확인`으로 둔다.
  - README 벤치마크 수치(95.2% R@5, 92% 토큰 절감 등)는 재현하지 않았다. `미확인`.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도(필수)입니다. 실행 흐름도는 이번 세션에서 그리지 않았다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 호스트 → 입구 3종 → iii 엔진 → `mem::*` 함수 5묶음 → 상태 KV·공급자 |

검증 구분 (2026-10-25): `deliver`(showcase, `--repo-root` 소스 증거 검증) 통과 — 산출물 검사 9개 모두 통과, 구성 오류 0. `visual-check` 통과(1440×900·1600×1000·1920×1080·2048×1320, light·dark, 넘침 없음, 최소 노드 글자 8.4px). 시각 검토는 1440×900 light 한 장을 이미지로 직접 봤고, 나머지 크기·dark는 자동 측정만이다. 부산물은 `agent-memory/artifacts/agentmemory/structure-visual-check/`.

### 그림 해설
그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다.

**읽는 순서**
1. 왼쪽 "에이전트·사용자" → 입구 3종(훅 스크립트 / MCP / CLI)이 전부 **엔진 하나**(`iii 엔진 + REST`)로 모인다.
2. 엔진에서 오른쪽의 `mem::*` 묶음 5개로 갈라진다. 위에서부터 정제 · 캡처 · 검색 · 조정 · 내보내기.
3. 묶음들은 오른쪽의 **상태 KV·색인** 하나에 읽고 쓴다. 정제 묶음만 오른쪽 위 **공급자**(LLM·임베딩)로 점선이 간다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 에이전트·사용자 | 훅을 쏘는 코딩 에이전트, MCP 클라이언트, 터미널 사용자 | 훅 JSON(stdin), MCP `tools/call`, CLI argv | `plugin/hooks.json`(Claude 훅 6개 이벤트), `src/cli.ts` `commands` | 코드 확인 |
| 훅 스크립트·스풀 | 훅 이벤트를 받아 서버에 보내고, 서버가 안 되면 스풀에 쌓았다가 재전송 | 입력 훅 JSON → `POST /agentmemory/observe` 등. 프라이버시 삭제는 서버 쪽 `mem::observe` 경로에서도 일어남 | `src/hooks/post-tool-use.ts` `main`, `src/hooks/_capture.ts` `captureObservation`, `src/capture/spool.ts` | 코드 확인(훅 한 개 끝까지, 스풀 내부는 추론) |
| MCP 입구 | 도구 54개를 노출. 전체 서버 경로와 독립 stdio 경로 | `tools/call` → (프록시 모드면) 엔진의 REST, (로컬 모드면) 인메모리 KV | `src/mcp/tools-registry.ts` `getAllTools`, `src/mcp/standalone.ts` `resolveHandle` 사용부, `src/mcp/rest-proxy.ts` | 코드 확인(분기 존재) / 판정 기준 미확인 |
| CLI·커넥터 | 서버 부팅, `connect`로 호스트 설정 쓰기, 엔진 설치·기동, 진단 | argv → 설정 파일 쓰기, 엔진 프로세스 기동, REST 호출 | `src/cli.ts` `commands`(4260), `src/cli/connect/index.ts` `ADAPTERS`, `src/cli/engine-launch.ts` | 코드 확인(명령표·어댑터 목록) / 기동 흐름은 추론 |
| iii 엔진 + REST | 별도 바이너리가 HTTP·상태·큐·스트림을 제공하고, 이 레포는 worker로 붙어 `api::*`(REST)·`event::*`·`mcp::*` 함수를 등록해 `mem::*`를 호출 | HTTP 요청 → `sdk.trigger({function_id:"mem::…"})` | `iii-config.yaml`, `src/index.ts` `registerWorker`, `src/triggers/api.ts`(예: `/session/start` → `mem::context` 약 1132줄), `src/triggers/events.ts` | 코드 확인(우리 쪽 등록부) / 엔진 내부는 미확인 |
| 정제 | 통합(4계층), 그래프, 교훈·반성, 보존·망각 | 저장된 관찰·요약 → 의미·절차 기억·그래프·교훈. LLM 호출 | `src/functions/consolidation-pipeline.ts` `mem::consolidate-pipeline`, `graph.ts` `mem::graph-extract`, `retention.ts` | 코드 확인(진입 시그니처·게이트) |
| 캡처·압축·요약 | 관찰 수신(dedup·프라이버시), 압축, 세션 요약, 세션 종료 이벤트 처리 | 훅 payload → `Raw`/`CompressedObservation` 저장, 요약 | `src/functions/observe.ts` `mem::observe`, `compress.ts` `mem::compress`, `summarize.ts`, `triggers/events.ts` `event::session::stopped` | 코드 확인(`events.ts` 123~210) |
| 검색·컨텍스트 | 하이브리드 검색, 스마트 검색, 컨텍스트 블록 조립 | 질의 → RRF 융합 결과, 예산 안의 컨텍스트 | `src/functions/search.ts` `mem::search`, `state/hybrid-search.ts` `RRF_K`, `functions/context.ts` `mem::context` | 코드 확인(RRF 상수·등록·`mem::context` 초반) |
| 조정·팀 | 액션 그래프, 리스, 시그널, 팀 공유, mesh 동기화 | 액션·리스·시그널 레코드, 피어 간 동기화 | `src/functions/actions.ts`, `leases.ts`, `signals.ts`, `team.ts`, `mesh.ts` | 코드 확인(등록·시그니처) |
| 내보내기·진단 | export/import, Obsidian, git 스냅샷, 진단·치유 | KV ↔ JSON·마크다운·git 저장소 | `src/functions/export-import.ts`, `snapshot.ts`(`git` 실행), `diagnostics.ts` | 코드 확인(등록·git 호출 방식) |
| 상태 KV·색인 | 모든 스코프 데이터를 `StateKV`로 저장하고 BM25·벡터·그래프 색인을 메모리에 들고 디스크에 주기 저장 | `kv.get/set/list/update`, 색인 객체 | `src/state/kv.ts` `StateKV`, `src/state/schema.ts` `KV`, `src/state/index-persistence.ts` | 코드 확인(스코프 표) / 색인 저장 방식은 추론 |
| LLM·임베딩 공급자 | 압축·요약·정제용 LLM과 임베딩을 공급자별로 감싸고 폴백·서킷 브레이커 | 프롬프트 → 텍스트, 텍스트 → 벡터 | `src/providers/index.ts` `createProvider`·`createFallbackProvider`, `providers/embedding/index.ts` | 코드 확인(팩토리) / 호출처 전수는 미확인 |

**그림에서 뺀 것과 이유**
- 간선 라벨: 엔진 → 묶음 5개 간선의 `mem::*` 이름과 묶음 → 상태 KV 간선의 의미는 각 노드 부제목이 이미 담고 있어 생략했다(라벨을 달면 간격이 모자라 겹침). 호스트 → 입구 3개 간선도 호스트 부제목(훅·MCP·터미널)이 프로토콜을 말한다.
- 공급자 점선은 정제 묶음에서만 그렸다. 실제로는 캡처(LLM 압축, opt-in)·검색(임베딩 질의)·조정(결정화)도 공급자를 쓴다(`src/functions/compress.ts`, `search.ts`, `crystallize.ts`의 `provider` 인자). 레이아웃 때문에 줄인 것이고 호출 관계가 없다는 뜻이 아니다.
- 뷰어(:3113), 세션 리플레이, 호스트 플러그인·직접 통합(`plugin/`, `integrations/`), 배포·웹사이트·평가는 구조도에 넣지 않았다. 지도 28~38행에 있다.

**미확인 영역**
- iii 엔진 내부(HTTP·state·queue·stream 구현)와 `iii-sdk`의 `registerFunction`/`trigger` 계약은 이 레포 밖이다.
- `mem::*` 묶음 안의 개별 함수 호출 순서(예: 통합이 어떤 순서로 LLM을 부르는지).
- 훅 이벤트가 호스트별로 어떻게 JSON 형태가 달라지는지(`hooks/session-start.ts` `contextPayload`는 호스트별 분기를 보였지만 나머지 훅과 호스트 사양은 미확인).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸
