---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-22
updated: 2026-10-22
---

# gbrain Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/garrytan/gbrain`
- **기준 SHA**: `63f62b2c` (2026-10-22, `master`), `VERSION` 0.60.371.0 (`package.json`, `VERSION`)
- **작업트리 상태**: Clean (`artifacts/gbrain/repo-metadata.txt`)
- **분석 목적**: 미지정(요청문에 목적 없음). 기능 지도까지는 "학습(기능 파악)"으로 진행하고, 범위 승인 때 목적을 다시 확인한다.
- **라이선스**: MIT (Copyright 2026 Garry Tan) — `LICENSE`. 하위 디렉터리에 별도 LICENSE가 있다: `third-party/company-brain/LICENSE`(MIT, Matt Zimak, 같은 폴더 `NOTICE.md`), `examples/skillpack-reference/LICENSE`(MIT 제목만 있고 본문은 "(edit me)" 자리표시자), `native/locks/vendor/node-v22.15.0/LICENSE`(Node.js 라이선스 전문), `vendor/postgres/UNLICENSE`(postgres.js 벤더 복사본).
- **언어/규모**: TypeScript, Bun ≥ 1.4 전제(`engines.bun`). 추적 파일 12,864개(test 6,482 / src 3,257 / docs 1,417 / evals 518 / scripts 399 / skills 235 / plugin 139 / plugin-variants 125 / recipes 69). 의존성에 `@electric-sql/pglite`(WASM Postgres), `@modelcontextprotocol/sdk`, `ai` + `@ai-sdk/*`, `web-tree-sitter`가 있다.
- **분석 대상 제품**: 루트 패키지 `gbrain`(`bin: gbrain → src/cli.ts`, `main: src/core/index.ts`, 공개 subpath exports 25개). 중첩·별도 배포 단위: `admin/`(`gbrain-admin`, React 19 + Vite 대시보드, `src/admin-embedded.ts`로 바이너리에 내장), `native/locks/`(C Node-API 애드온, 플랫폼별 prebuild), `plugin/`·`plugin-variants/`(스킬 트리, 생성물), `.claude-plugin/`·`.codex-plugin/`·`openclaw.plugin.json`(플러그인 매니페스트), `recipes/agent-voice/`(JS 번들), `vendor/postgres/`(벤더), `third-party/company-brain/`(외부 기여 코드).
- **배포 방식**: README는 npm 배포가 아니라고 명시한다(`bun install -g github:garrytan/gbrain`). 컴파일 바이너리는 `bun build --compile`(`package.json` `build`). 설치 경로는 이 문서 범위 밖.
- **스펙 범위**: 아직 승인 전

---

## 2. 프로젝트 개요

README 첫 줄의 주장: "이미 쓰는 에이전트에 사용자가 통제하는 메모리를 준다." 마크다운 페이지를 PGLite(기본, 내장) 또는 Postgres + pgvector에 색인하고, 키워드·벡터 하이브리드 검색, 타입 있는 링크 그래프, 사실(facts)·주장(takes) 메모리, 인용 달린 합성 답변(`think`), 백그라운드 정리 사이클(`dream`)을 CLI와 MCP(stdio·HTTP+OAuth)로 노출한다. (출처: `README.md` 3~35, 387~414줄 — 주장이고, 아래 지도가 코드로 대조한 범위다.)

핵심 설계 세 가지(코드로 확인한 것):
1. **계약 우선**: `src/core/operations.ts`는 244줄짜리 등록부이고 정의는 `src/core/ops/*`(약 60개 파일)에 있다. CLI·MCP·`--tools-json`이 같은 `Operation`에서 생성된다. `OperationContext.remote`가 필수이고 `false`일 때만 신뢰한다(`src/core/ops/contract.ts` `OperationContext` 425줄, `remote` 450줄). 코드 확인.
2. **저널을 거치는 쓰기**: `put_page`·`edit_page`·`append_page` 등은 DB에 직접 쓰지 않고 `src/core/persistence/`의 쓰기 코디네이터(`submitPageMutation`)를 거친다. 이 디렉터리는 약 400개 파일이다. 코드 확인(진입부), 소비자 쪽은 미탐색.
3. **두 엔진 하나의 인터페이스**: `BrainEngine`(`src/core/engine.ts` 2,848줄)을 `PGLiteEngine`과 `PostgresEngine`이 구현하고, 공통 SQL은 `src/core/engine-sql/`에 둔다. 코드 확인.

### 기능 지도

<!--
검증 수준 표기: "코드 확인(진입점)" = 진입점 심볼을 grep으로 확인하고 호출 연결을 읽음. "보고 확인" = 서브에이전트가 읽은 내용을 메인 세션이 진입점 일부만 재확인함.
"추론" = 파일 헤더·이름으로 판단. 스펙 단계(4장)에서 R-ID 단위로 다시 붙인다.
-->

> 조사 방식: 영역 6개(저장·쓰기 / 검색·그래프 / 메모리 / 수집·소스 / 서빙·접근 / 잡·운영·스킬)를 서브에이전트가 읽기 전용으로 조사했고, 메인 세션이 아래 항목을 코드에서 다시 확인했다: `createEngine` 기본값, `put_page`→`submitPageMutation`, `LATEST_SCHEMA_VERSION`, 소스 해석 7단계, `IngestionDaemon` 미연결, 사이클 단계 수, `remote:false` 설정 위치, 발행 게이트 위치, scope 유니온, 검색 모드 번들 값, `facts` DDL 위치. 나머지 행의 세부는 서브에이전트 보고 기준이다.

#### A. 저장소와 쓰기

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 엔진 선택·스키마·마이그레이션 | `gbrain init`/연결 시 설정으로 PGLite 또는 Postgres 엔진을 만들고 스키마를 적용·마이그레이션. SQLite 미지원, down 마이그레이션 없음 | `src/core/engine-factory.ts` `createEngine`, `src/core/migrate.ts` `runMigrations`, `PGLiteEngine.initSchema`, `PostgresEngine.initSchema`, `src/schema.sql` | 없음 | 핵심 | `capabilities/engine-and-schema.md` · 미작성 | 코드 확인(진입점·기본값·버전 264) |
| 2. 페이지 쓰기 저널 | 전체 교체(`put_page`), 부분 수정(`edit_page`), 덧붙임(`append_page`), 일괄(`put_pages`), 큰 페이지 분할 업로드, 태그·타임라인, `capture`. `expected_revision`·`request_id`로 충돌 감지·재전송 안전 | `src/core/ops/pages.ts` `put_page`, `src/core/persistence/page-mutations.ts` `submitPageMutation`, `persistence/journal.ts` `admitWrite`, `ops/page-edit.ts`, `ops/page-append.ts`, `ops/page-batch.ts`, `ops/page-upload.ts`, `commands/capture.ts` | 1, 공유 계약(소스 격리·쓰기 저널) | 핵심 | `capabilities/page-write-journal.md` · 미작성 | 코드 확인(진입부), 저널 소비자 미탐색 |
| 3. 마크다운 파싱·청킹·임베딩과 import/export | `gbrain import <dir>`·`put_page`가 frontmatter 파싱, 타임라인 분리, 청킹, 임베딩, 페이지·청크 기록(content_hash로 건너뜀). `embed`로 누락 벡터 보충, `export`로 마크다운 내보내기 | `src/commands/import.ts` `runImport`, `src/core/import-file.ts` `importFromContent`, `src/core/markdown.ts` `parseMarkdown`, `src/core/chunkers/recursive.ts`, `src/commands/embed.ts` `runEmbed`, `src/commands/export.ts` `runExport` | 1, 38 | 핵심 | `capabilities/markdown-import-pipeline.md` · 미작성 | 코드 확인(진입점), 청킹 내부 미확인 |
| 4. 페이지 읽기·버전·삭제·영구 삭제 | `get_page`/`list_pages`, 버전 이력과 되돌리기(`history`/`revert`), soft delete 후 복구, 72시간 뒤 purge | `ops/pages.ts` `get_page`·`delete_page`·`restore_page`·`purge_deleted_pages`, `ops/admin.ts` `get_versions`·`revert_version`, `persistence/page-purge.ts` | 2 | 핵심 | `capabilities/page-lifecycle.md` · 미작성 | 코드 확인(진입점) |
| 5. 파일 첨부 저장소 | `file_upload`/`file_list`/`file_url`로 바이너리를 local·S3·Supabase 저장소에 두고 `files` 행 기록. 저장소 미설정이면 거부 | `ops/files.ts`, `commands/files.ts` `runFiles`, `src/core/storage.ts` `createStorage` | 1 | 핵심 | `capabilities/file-attachments.md` · 미작성 | 보고 확인(op 이름), 백엔드 추론 |

#### B. 검색·합성·그래프

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 6. 하이브리드 검색 | `search`(저렴한 top-20), `query`/`ask`(모드별 한도·확장·리랭크·사실 행), `search_exact`(리터럴 전수), 이미지 질의. 모드 번들 conservative/balanced/tokenmax, 의미 캐시 | `src/core/ops/search.ts` `search`·`query`, `src/core/search/hybrid.ts` `hybridSearch`·`hybridSearchCached`, `search/mode.ts` `MODE_BUNDLES`, `ops/search-exact.ts`, `search/by-image.ts` | 3 | 핵심 | `capabilities/hybrid-search.md` · 미작성 | 코드 확인(단계 순서·모드 값), 단계 내부 일부 미확인 |
| 7. 합성 답변 (`think`/`synthesize`) | 질문 → 페이지·takes·그래프 수집 → LLM이 인용 달린 답과 빈틈을 반환. 로컬 CLI만 `--save`·`--take`. 키 없으면 수집 결과만 반환 | `src/core/think/index.ts` `runThink`, `think/gather.ts` `runGather`, `commands/think.ts` `runThinkCli`, `ops/takes.ts` `think` | 6, 11, 38 | 핵심 | `capabilities/think-synthesis.md` · 미작성 | 코드 확인(진입점·수집 스트림) |
| 8. 링크 그래프 | put·sync가 본문·frontmatter·코드 참조에서 타입 있는 링크 추출(LLM 없음). 링크 add/remove/조회, 그래프 순회, 고아·미작성 대상·랭킹, 재조정, 모순 제안 | `src/core/link-extraction.ts` `extractPageLinks`, `ops/links.ts`, `commands/graph-query.ts`, `ops/orphans.ts`, `ops/graph-rank.ts`, `commands/reconcile-links.ts`, `commands/edge-proposals.ts` | 2, 3 | 핵심 | `capabilities/link-graph.md` · 미작성 | 코드 확인(진입점) |
| 9. 인사이트 조회 | `whoknows`(전문가 랭킹), `salience`, `anomalies`, `find_trajectory`. 전부 LLM 없음 | `commands/whoknows.ts` `findExperts`, `ops/salience.ts`, `ops/insights.ts` `find_experts`·`find_trajectory` | 6, 11 | 핵심 | `capabilities/insight-queries.md` · 미작성 | 코드 확인(진입점) |
| 10. 코드 인텔리전스 | 코드 파일을 tree-sitter로 심볼 청킹하고 호출·참조 간선을 만든 뒤 `code-def/refs/callers/callees`, `code_blast`, `code_flow` 질의, `reindex-code` | `src/core/chunkers/code.ts` `chunkCodeTextFull`, `core/code-chunks.ts`, `ops/code-intel.ts`, `commands/code-def.ts`, `commands/reindex-code.ts` | 3 | 핵심 | `capabilities/code-intelligence.md` · 미작성 | 코드 확인(진입점) |

#### C. 메모리 계층

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 11. 메모리 verbs 7개와 프로토콜 | `remember`·`recall`·`entity`·`synthesize`·`forget`·`context_pack`·`delta`(모두 `protocol_version: 1`). `--surface verbs`로 이것만 노출. `gbrain protocol conformance` | `src/core/verbs.ts` `VERB_NAMES`·`verbOperations`, `ops/facts.ts` `recall`·`context_pack`·`delta`, `commands/recall.ts` `runRecall`, `commands/protocol.ts` | 2, 6 | 핵심 | `capabilities/memory-verbs.md` · 미작성 | 코드 확인(진입점) |
| 12. 사실 추출·자동 캡처 | 대화 한 턴에서 LLM이 사실을 뽑아 hot memory에 저장(코사인 빠른 경로 → 분류기 중복 제거 → 삽입). 훅·compaction·세션 종료로 자동 캡처(`memory.auto_writeback`) | `ops/facts.ts` `extract_facts`, `core/facts/backstop.ts` `runFactsPipeline`, `facts/extract.ts` `extractFactsFromTurnWithOutcome`, `commands/extract-conversation-facts.ts` | 11, 38 | 핵심 | `capabilities/fact-extraction.md` · 미작성 | 보고 확인(진입점 grep) |
| 13. 신뢰 등급·격리·영구 삭제 | 신뢰 6등급과 `min_trust`, owner의 `trust review/confirm`, `quarantine`, `forget --purge`(드라이런 영수증·타이핑 토큰, MCP 불가) | `core/trust/tier.ts`, `commands/trust.ts`, `ops/trust.ts` `confirm_memory`, `core/quarantine.ts`, `commands/forget-purge.ts` `runForgetPurge`, `core/facts/purge.ts` | 11 | 핵심 | `capabilities/trust-and-purge.md` · 미작성 | 보고 확인 |
| 14. takes·belief ledger·calibration | 페이지 `## Takes` 펜스의 주장 add/update/supersede/resolve, 스코어카드·보정 곡선, belief 이벤트 원장(`delta {beliefs}`), 보정 프로필 | `commands/takes.ts` `runTakes`, `ops/takes.ts`, `commands/beliefs.ts`, `core/belief/`, `ops/calibration.ts` | 2 | 핵심 | `capabilities/takes-and-beliefs.md` · 미작성 | 보고 확인 |
| 15. Life Chronicle·온톨로지 | `day`/`on-this-day`/`since`/`last-seen`, 엔티티 차원 값(`facts.dimension`)의 `ontology` 조회·제안·충돌, 사이클 단계 `chronicle`의 사건 자동 추출 | `ops/chronicle.ts`, `core/chronicle/`, `engine.getOntology` | 11, 12 | 핵심 | `capabilities/chronicle-ontology.md` · 미작성 | 보고 확인 |
| 16. 주변 맥락 push | 사용자 프롬프트 훅이 ≤3 페이지·hot facts·reflex 포인터를 ≤8KB로 주입, `volunteer_context`/`watch`, `compile-context`가 `.claude/gbrain-context.md` 등 생성 | `core/context/turn-context.ts` `assembleTurnContext`, `commands/hook.ts` `runHook`, `ops/insights.ts` `volunteer_context`, `commands/watch.ts`, `commands/compile-context.ts` | 11, 37 | 핵심 | `capabilities/ambient-context.md` · 미작성 | 보고 확인 |
| 17. 고정 질문 | `questions pin/list/status/refresh/unpin` — 인용 달린 답을 최신으로 유지하고 문장별 stale 표시 | `core/questions/service.ts` `pinQuestion`·`refreshQuestion`, `ops/questions.ts` | 6, 7 | 핵심 | `capabilities/pinned-questions.md` · 미작성 | 보고 확인 |
| 18. 열린 루프(`waiting`/`loops`) | Gmail 스레드 상태에서 "누가 나를 기다리나"를 결정론으로 감지하고 LLM으로 약속 추출, `loops done/drop/mute` | `ops/loops.ts` `open_loops`, `core/google/loop-detect.ts`, `core/google/loops-extract.ts`, `core/loops/loops-store.ts` | 23 | 핵심 | `capabilities/open-loops.md` · 미작성 | 보고 확인 |

#### D. 데이터 수집과 소스

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 19. 소스·브레인 토폴로지 | `sources add/list/…`로 한 브레인 안의 레포를 등록하고, `mounts`로 다른 브레인 DB를 연결. `--source`·`--brain` 해석 우선순위 | `commands/sources.ts` `runSources`, `core/source-resolver.ts` `resolveSourceWithTier`(7단계), `core/brain-resolver.ts` `resolveBrainId`, `commands/mounts.ts` | 1 | 핵심 | `capabilities/sources-and-brains.md` · 미작성 | 코드 확인(7단계·진입점) |
| 20. git/마크다운 sync | `gbrain sync`가 소스 레포를 pull해 변경 파일을 import(삭제→이름변경→import→마무리), 앵커 커밋, 락, 보류·실패 장부 | `commands/sync.ts` `runSync`, `commands/sync/perform.ts` `performSync`, `sync/incremental.ts` | 19, 3 | 핵심 | `capabilities/git-sync.md` · 미작성 | 코드 확인(진입·분기), 내부 미탐색 |
| 21. 추출(링크·타임라인·멘션)과 enrich | `extract links/timeline/all`, `--stale` 증분, `extract mentions --explain`, `enrich`가 얇은 인물·회사 페이지를 다시 씀 | `commands/extract.ts` `runExtract`, `core/mentions/pass.ts`, `core/timeline-extract.ts`, `commands/enrich.ts` `runEnrichCore` | 3, 8 | 핵심 | `capabilities/extraction-and-enrich.md` · 미작성 | 보고 확인(헤더 수준) |
| 22. 대화 기록 수집 | `transcripts ingest`가 Claude Code·Codex 등 세션 로그·챗 내보내기를 대화 페이지로, `connectors sync`가 ChatGPT·Claude 계정 이력을 가져옴 | `core/transcripts/ingest.ts` `runTranscriptsIngest`, `commands/transcripts.ts`, `core/connectors/sync.ts`, `commands/connectors/` | 3 | 핵심 | `capabilities/transcript-ingestion.md` · 미작성 | 보고 확인(커넥터는 추론) |
| 23. Google 커넥터·자격 증명 vault | `google setup/connect`로 OAuth 후 `sync`가 Gmail·캘린더·연락처를 마크다운으로 구체화. `creds`는 로컬 vault | `commands/google.ts` `runGoogle`, `core/google/google-source.ts` `runGoogleSync`, `core/creds/vault.ts`, `commands/creds.ts` | 19, 20 | 핵심 | `capabilities/google-connector.md` · 미작성 | 보고 확인(URL·진입점), 외부 동작 미확인 |
| 24. GitHub 소스 | `sources add --kind github` 후 sync가 이슈·PR·레포 카드를 페이지로 | `core/github-source.ts` `runGitHubSync`, `commands/sync/connector.ts` | 19, 20 | 핵심 | `capabilities/github-source.md` · 미작성 | 추론(진입점만) |
| 25. company-brain 소스 | `sources inspect/connect`로 기존 사내 마크다운 레포를 계획 검토 후 연결, 커밋된 블롭만 sync | `commands/company-brain-connect.ts`, `core/company-brain/runtime.ts` `performCompanyBrainSync` | 19, 20 | 핵심 | `capabilities/company-brain-source.md` · 미작성 | 보고 확인(진입점) |
| 26. 연동 레시피 | `integrations list/show/doctor/install` — 레시피는 YAML frontmatter가 붙은 마크다운(에이전트가 읽는 설치 지시), `agent-voice`만 JS 번들 | `commands/integrations.ts` `runIntegrations`, `recipes/*.md`, `recipes/agent-voice/` | 없음 | 부속 | `capabilities/integration-recipes.md` · 미작성 | 코드 확인(디스패처) |

#### E. 서빙과 접근 제어

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 27. 연산 계약·CLI 생성·MCP stdio·표면 | 하나의 `Operation`이 CLI 명령·MCP 도구·`--tools-json`이 된다. `gbrain serve`(stdio), `--surface full/starter/verbs`, `request_tools` | `core/operations.ts`, `core/ops/contract.ts` `Operation`, `cli/main.ts` `runCli`, `cli/command-table.ts` `CLI_COMMANDS`, `mcp/server.ts` `startMcpServer`, `mcp/surface.ts` `filterOpsForSurface`, `mcp/dispatch.ts` `dispatchToolCall` | 없음 | 핵심 | `capabilities/operation-contract-and-mcp.md` · 미작성 | 코드 확인(진입점·scope 6종·`remote:false` 위치) |
| 28. HTTP MCP·OAuth·권한 | `serve --http`가 POST `/mcp`를 OAuth 2.1/베어러로 받고 scope→표면→소스 격리→핸들러 순으로 검사. `auth`·`mcp grant`로 클라이언트·토큰·권한 관리 | `commands/serve-http.ts` `runServeHttp`, `serve-http-mcp.ts` `callMcpTool`, `core/oauth-provider.ts`, `core/scope.ts`, `core/grants/`, `commands/auth.ts` | 27 | 핵심 | `capabilities/http-mcp-oauth.md` · 미작성 | 코드 확인(검사 순서), OAuth 내부 미확인 |
| 29. 원격 연결 | `mcp expose`(Tailscale), `agent register`/`mcp grant`, `connect`, thin client(`init --mcp-only`)가 원격 브레인의 op를 호출, 로컬 CLI 소켓 | `commands/mcp-expose.ts`, `commands/harness-connect.ts`, `core/mcp-client.ts` `callRemoteTool`, `cli/main.ts` `runThinClientRouted`, `core/cli-socket/server.ts` | 28 | 핵심 | `capabilities/remote-connection.md` · 미작성 | 보고 확인(헤더·진입점) |
| 30. 관리자 대시보드 | 소유자가 부트스트랩 토큰으로 로그인해 에이전트·요청 로그·잡·클라이언트·권한을 관리하는 React SPA | `admin/src/pages/`, `commands/serve-http-spa.ts` `mountSpa`, `scripts/build-admin-embedded.ts`, `commands/serve-http-admin-api.ts` | 28 | 부속 | `capabilities/admin-dashboard.md` · 미작성 | 보고 확인(라우트·내장 방식), 페이지 내부 미확인 |

#### F. 백그라운드·운영

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 31. 잡 큐(Minions)와 에이전트 실행 | `jobs submit/work/…`, `agent run`이 `subagent` 잡을 제출하고 워커가 LLM 루프를 실행. 보호된 잡 이름은 MCP에서 제출 불가 | `commands/jobs.ts` `runJobs`, `core/minions/queue.ts` `MinionQueue`, `minions/worker.ts`, `commands/agent.ts`, `minions/handlers/subagent.ts` | 1 | 핵심 | `capabilities/job-queue.md` · 미작성 | 코드 확인(진입점·구조) |
| 32. dream 사이클·autopilot | `dream`이 30단계를 한 번 실행, `autopilot`이 반복 제출하는 데몬(launchd/systemd/cron 설치), `maintain`·`status` | `commands/dream.ts` `runDream`, `core/cycle.ts` `runCycle`·`ALL_PHASES`, `core/cycle/phase-table.ts`, `commands/autopilot.ts` `runAutopilot`, `commands/status.ts` | 31, 각 단계의 기능 | 핵심 | `capabilities/dream-cycle.md` · 미작성 | 코드 확인(단계 목록 30개), 단계 본문 미확인 |
| 33. 점검·복구·업그레이드·백업 | `doctor`(검사 약 161개, JSON), `repair`, `db-repair`, `pglite-repair`, `apply-migrations`, `upgrade`, `backup`, `advisor` | `commands/doctor.ts` `runDoctor`, `doctor/registry.ts`, `commands/repair.ts`, `commands/upgrade.ts`, `commands/backup.ts`, `core/advisor/run.ts` | 1 | 부속 | `capabilities/ops-tooling.md` · 미작성 | 보고 확인(레지스트리·헤더) |
| 34. 스키마 팩 | 페이지 타입 분류(`gbrain-base-v2` 등)를 팩으로 선언하고 `schema detect/suggest/use`로 사용자 팩을 만든다. 쓰기·추출·전문가 라우팅이 활성 팩을 따른다 | `commands/schema.ts`, `core/schema-pack/load-active.ts` `loadActivePack`, `core/ops/schema-packs.ts` | 2, 3 | 핵심 | `capabilities/schema-packs.md` · 미작성 | 코드 확인(파일·op 이름), 동작 추론 |
| 35. 스킬 | 스킬 = `skills/<name>/SKILL.md`(frontmatter + 지침 prose). `RESOLVER.md`로 라우팅, `check-resolvable`·`routing-eval`·`skillify`·`skillpack`·공유 스킬(`put_skill` 등) | `skills/manifest.json`(75개), `skills/RESOLVER.md`, `core/skillpack/`, `core/shared-skills/`, `commands/check-resolvable.ts` | 27 | 핵심 | `capabilities/skills.md` · 미작성 | 코드 확인(구조), 도구 내부 추론 |
| 36. 에이전트 온보딩 | `setup claude-code`·`setup codex`가 브레인·MCP·훅 구성, `bootstrap`(개인 에이전트 부트스트랩), `hook`(fail-open), 플러그인 트리 생성기 | `commands/setup.ts` `runSetup`, `commands/bootstrap.ts`, `commands/hook.ts` `runHook`, `scripts/generate-plugin-tree.ts`, `plugin/`, `.claude-plugin/` | 27, 16 | 핵심 | `capabilities/agent-onboarding.md` · 미작성 | 보고 확인(헤더) |
| 37. AI 게이트웨이·설정·예산 | 임베딩·확장·채팅·리랭크를 25개 provider 레시피로 라우팅. `config`, `providers`, `models`, `pricing`, 예산 추적기 | `core/ai/gateway.ts` `embed`·`chat`·`rerank`, `core/ai/recipes/`, `commands/config.ts`, `core/budget/budget-tracker.ts` | 없음 | 핵심 | `capabilities/ai-gateway.md` · 미작성 | 코드 확인(export), provider 내부 미확인 |

#### G. 선택 기능·주변 도구

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 38. skillopt | `skillopt <skill>` — 벤치마크 과제로 SKILL.md를 LLM이 고쳐 쓰고 held-out 점수가 오를 때만 채택 | `commands/skillopt.ts`, `core/skillopt/orchestrator.ts` | 35, 37 | 부속 | `capabilities/skillopt.md` · 미작성 | 보고 확인(헤더) |
| 39. 평가·벤치 | `eval`(qrels, brainbench, longmemeval, 회귀 게이트), `bench` | `commands/eval.ts` `runEvalCommand`, `src/eval/`, `commands/bench.ts` | 6 | 부속 | `capabilities/evals.md` · 미작성 | 추론(디스패치) |
| 40. OpenClaw 플러그인·컨텍스트 엔진 | OpenClaw 호스트에 컨텍스트 엔진을 등록하고 MCP 서버·스킬 목록을 선언 | `src/openclaw-context-engine.ts`, `openclaw.plugin.json`, `core/context-engine.ts` | 27 | 부속 | `capabilities/openclaw-plugin.md` · 미작성 | 코드 확인(파일 머리), 나머지 미확인 |
| 41. decide(System One) | 리랭크·의도·근거 등 9개 슬롯에 외부 분류기나 LLM을 끼우는 선택 장치(`decide enable/calibrate/…`) | `commands/decide.ts`, `core/ai/decide/`, `core/think/decide.ts` | 6, 7 | 부속 | `capabilities/decide.md` · 미작성 | 보고 확인(슬롯 목록) |
| 42. brainstorm·lsd | 가까운 집합과 먼 집합을 LLM이 교차해 아이디어를 내고 루브릭으로 평가 | `commands/brainstorm.ts`, `core/brainstorm/` | 6, 37 | 부속 | `capabilities/brainstorm.md` · 미작성 | 추론(헤더) |
| 43. founder scorecard | `founder scorecard <slug>` — 타입 있는 사실과 해결된 takes를 집계(LLM 없음) | `commands/founder-scorecard.ts` `runFounder` | 14 | 부속 | `capabilities/founder-scorecard.md` · 미작성 | 추론(헤더) |
| 44. book-mirror | 챕터 폴더를 읽기 전용 서브에이전트로 챕터별 개인화해 한 페이지로 조립(비용 추정 후 확인) | `commands/book-mirror.ts` `runBookMirrorCmd` | 31, 37 | 부속 | `capabilities/book-mirror.md` · 미작성 | 추론(헤더) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 연산 계약과 신뢰 경계: `Operation`, `OperationContext`(`remote` 필수·fail-closed, `transport`), `scope` 6종(`read`·`write`·`admin`·`sources_admin`·`users_admin`·`agent`), `localOnly`·`cliOnly` | 2~44 거의 전부 | `src/core/ops/contract.ts` `Operation`(735)·`OperationContext`(425), `src/core/scope.ts` | `capabilities/operation-contract-and-mcp.md`(27행과 같은 문서) | 코드 확인 |
| 소스 격리: `sourceScopeOpts(ctx)` 우선순위(연합 배열 > 단일 소스 > 없음), 빈 배열은 "전체"가 아님 | 2, 6~8, 11, 14, 28 | `src/core/ops/context.ts` `sourceScopeOpts`(649) | 27행 문서에 포함할지 별도 문서로 뺄지는 스펙 단계에서 결정 | 보고 확인 |
| 페이지·소스 식별과 리비전: `(source_id, slug)` 유일성, `PageSnapshot.revision`(= `expected_revision`) | 2~4, 8, 20 | `src/core/types.ts` `Page`·`PageInput`, `src/core/page-state/types.ts` | 2행 문서에 포함 | 보고 확인 |
| 쓰기 요청 저널: `request_id`, `WriteAdmission`, 영수증(`write_pending`, `source_changed`) | 2, 11, 12, 20, 33 | `src/core/persistence/journal.ts` `admitWrite`, `persistence/params.ts` | 2행 문서에 포함 | 보고 확인 |

**대조한 범위와 미탐색 영역**
- 대조: README 기능·설치 절, `package.json`(scripts·exports·bin), `src/cli/command-table.ts`의 CLI 전용 명령 약 128개 이름, `docs/TOOL_CATALOG.md`(생성 문서, MCP 도구 161개·25개 영역)의 영역 이름, `src/core/operations.ts`의 op 클러스터 등록, 6개 영역 서브에이전트 조사.
- 문서와 구현의 차이(구현을 사실로 적는다):
  - README는 PGLite가 기본 엔진이라고 하지만 `createEngine`은 `config.engine || 'postgres'`로 fallback한다. PGLite는 `gbrain init`이 설정에 쓰기 때문에 기본이 된다. (코드 확인: `src/core/engine-factory.ts:12`, `src/core/config.ts:739`)
  - `src/commands/dream.ts` 머리 주석은 "full 6-phase cycle"이지만 `ALL_PHASES`는 30개다(`src/core/cycle.ts:127`). (코드 확인)
  - `source-resolver.ts`의 해석 단계는 7개(`SOURCE_TIER_NAMES`)인데 같은 파일 주석은 "1-6 priority"다. (코드 확인)
  - CLAUDE.md는 `scope`가 `read|write|admin`이라고 하지만 타입은 6종이고, `remote:false`는 `src/cli.ts`가 아니라 `src/cli/main.ts:1527`에서 설정한다. (코드 확인)
  - 발행 게이트(`mcp.publish_skills`·`mcp.publish_advisor`)는 목록 단계(`isCallable`, `dispatch.ts:565`)와 스킬 카탈로그 핸들러 안(`assertPublishEnabled`)에서만 걸리고 `dispatchToolCall`은 `publishGateKey`를 보지 않는다. (코드 확인: 위 두 위치와 `skills-catalog.ts:65`)
  - `src/core/ingestion/daemon.ts`의 `IngestionDaemon`은 `src/` 안에서 자기 파일 말고는 참조하지 않아 이 SHA에서 CLI·서버에 연결되지 않았다. `/ingest` 웹훅 라우트(`serve-http-webhooks.ts:295`)는 있다. (코드 확인: 참조 grep)
  - `facts`·`takes` 테이블 DDL은 `src/schema.sql`이 아니라 마이그레이션(`v045-facts-hot-memory-v0-31.ts` 등)에 있다. (코드 확인: facts)
  - `skills/manifest.json`의 `version`은 0.32.3.0으로 패키지 버전 0.60.371.0과 다르다. (코드 확인)
  - 서브에이전트 보고만 있는 차이(메인 세션 미재확인): `cli/main.ts:1851` 근처 thin-client 거부 안내가 `code-def` 등에 "MCP op이 아직 없다"고 하지만 `ops/code-intel.ts`에 op이 있다. `mcp/surface.ts` 머리 주석의 starter "~20 ops"와 달리 본문은 약 40개다. `docs/ENGINES.md`에 SQLite 설명이 남아 있다. `docs/guides/ambient-writeback.md`는 "기본 꺼짐"이라 하지만 `memory.auto_writeback`이 미설정이어도 compaction 수확·세션 종료 추출은 돈다고 한다.
- 미탐색(열지 않은 영역과 이유):
  - 지도 단계라 본문을 열지 않은 것: `src/core/persistence/*`의 소비자·sync·topology(약 400파일), `engine-sql/*`와 두 엔진 내부, `schema-migrations/v*.ts` 본문 263개, `doctor/checks/*` 145개, `cycle/*` 단계 본문, `facts/*`(약 60개), `search/*` 단계 내부, `core/ai/recipes/*`.
  - 영역 보고에서 빠졌거나 이름만 확인한 명령: `onboard`, `features`, `claw-test`, `friction`, `report`, `git`, `storage`(tiering), `reindex*` 계열, `projections`, `integrity`, `publish`, `lint`, `frontmatter`, `models`, `cache`, `repos`, `core`, `eval-*` 세부, `reinit-pglite`, `migrate-engine`, `migrate-embeddings`, `retrieval-upgrade`, `sweep`, `status-funnel`.
  - 문서·배포: `docs/` 전체(1,417개), `evals/`(518개), `scripts/`(399개, CI·검사 스크립트), `test/`(6,482개)는 기본 정책대로 열지 않았다. `docs/architecture/key-files/*`(합계 약 2.7MB)는 후보 자료로만 취급하고 열지 않았다.
  - Memorable 통합(`docs/memorable-agents.md`, `integrations.memorable.*`), 호스티드 gbrain.io 연동, `native/locks/`의 C 구현(README만 읽음. 지도에서는 2행의 선행 인프라로 다룬다)은 행으로 만들지 않았다.
  - 외부 시스템(Google·GitHub·ChatGPT·Claude.ai·Tailscale·Voyage 등)의 실제 동작은 모두 `미확인`이다. 클라이언트 코드의 존재만 확인했다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도입니다. 실행 흐름도는 만들지 않았습니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 호출 진입면(CLI·MCP·HTTP·훅)과 연산 계약, 쓰기 저널, 엔진, 검색·메모리·수집·백그라운드 계층의 관계 |

검증 결과(세 가지를 구분한다):
- **산출물 검증**: `archify deliver … --quality showcase` 통과(검사 9/9, 구성 오류 0·경고 0). 명세 sha256 `24f79a78…`, HTML sha256 `bb67b885…`.
- **브라우저 확인**: `visual-check` 통과(1440×900·1600×1000·1920×1080·2048×1320, light·dark에서 `scrollHeight == innerHeight`). 부산물은 `artifacts/gbrain/structure-visual-check/`.
- **시각 검토**: 메인 세션이 1440×900 light 스크린샷 한 장만 봤다. dark와 큰 해상도 스크린샷은 보지 않았다. `meta.locale`을 생략해 뷰어 UI와 `<html lang>`은 영어로 나온다.
- 그림은 읽기 계층(검색·그래프·think·메모리 verbs·facts)을 한 노드로 묶었다. 간선이 한 통로에 겹쳐 가독성 검사를 통과하지 못해서 묶었고, 아래 표에서 따로 설명한다. 스킬(마크다운 지침)·스키마 팩·관리자 대시보드·플러그인은 그리지 않았다.

### 그림 해설

그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다. 호출은 왼쪽 호출자에서 오른쪽 저장소 쪽으로 흐른다.

**읽는 순서**
1. 왼쪽 `에이전트·사용자` → `CLI 디스패처` 또는 `MCP 서버`: 같은 연산이 두 입구로 들어온다.
2. 가운데 `연산 계약·신뢰 경계`: 입구가 달라도 여기서 같은 `Operation` 정의를 실행한다. 입구가 `remote` 값을 정해 넘긴다.
3. 오른쪽 위 `읽기 계층` → `BrainEngine`(그리고 점선으로 `AI 게이트웨이`): 검색·메모리·합성은 읽고, LLM·임베딩이 필요할 때만 게이트웨이를 부른다.
4. 오른쪽 가운데 `쓰기 저널` → `import 파이프라인`, `BrainEngine`: 쓰기 op은 저널을 거쳐 파싱·청킹·임베딩 후 엔진에 기록된다.
5. 오른쪽 아래 `수집·소스`와 `잡 큐·dream 사이클`: 파일·외부 데이터를 import 파이프라인에 넣고, 사이클이 그 sync 단계를 주기적으로 돌린다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 에이전트·사용자 | 터미널 명령, MCP 클라이언트 호출, 하네스 훅(`gbrain hook …`)이 호출자다 | argv, MCP `tools/call` | `src/cli.ts` `cliFastPath`(help·version만 처리 후 `cli/main.ts`를 동적 import) | 코드 확인 |
| CLI 디스패처 | `Operation`에서 CLI 명령을 만들고, 그 밖의 CLI 전용 명령(약 128개)을 표에서 찾아 실행. 신뢰된 로컬 호출로 컨텍스트를 만든다 | argv → `OperationContext{remote:false}` | `src/cli/main.ts` `runCli`, 컨텍스트 생성 `main.ts:1527`, `src/cli/command-table.ts` `CLI_COMMANDS` | 코드 확인 |
| MCP 서버 | stdio(`gbrain serve`)와 HTTP(`serve --http`, OAuth 2.1)로 도구 목록·호출을 받는다. 표면(`full/starter/verbs`)과 scope로 걸러 `remote:true` 컨텍스트를 만든다 | `tools/call` → op 결과·오류 봉투 | `src/mcp/server.ts` `startMcpServer`(stdio는 `remote: true, transport: 'stdio'` 408줄), `src/commands/serve-http-mcp.ts` `callMcpTool`, `src/mcp/dispatch.ts` `dispatchToolCall` | 코드 확인(HTTP 호출 순서는 보고 확인) |
| 연산 계약·신뢰 경계 | 한 곳(`operations`)에 모은 op 정의. 각 op은 `scope`(6종), `localOnly`, `cliOnly`, `mutating` 등을 갖고, 소스 격리 함수(`sourceScopeOpts`)와 `remote` fail-closed 규칙이 여기서 적용된다 | 입구가 만든 `OperationContext` → 핸들러 호출 | `src/core/operations.ts` `operations`, `src/core/ops/contract.ts` `Operation`·`OperationContext`, `src/core/ops/context.ts` `sourceScopeOpts` | 코드 확인 |
| 읽기 계층 | 하이브리드 검색(키워드+벡터+RRF+후처리+리랭크), `think` 합성, 메모리 verbs·facts·takes 조회, 링크 그래프 순회. 엔진에서 읽고 필요할 때만 게이트웨이를 부른다 | 질의 → 순위 매긴 청크·사실·인용 답 | `src/core/search/hybrid.ts` `hybridSearch`, `src/core/think/index.ts` `runThink`, `src/core/verbs.ts` `verbOperations`, `src/core/ops/facts.ts` `recall` | 코드 확인(진입점), 단계 내부 일부 미확인 |
| 쓰기 저널 | `put_page`·`edit_page`·`append_page` 등을 `request_id`·`expected_revision`과 함께 접수하고 영수증을 돌려준다. 준비 단계에서 `importFromContent`를 호출한다 | 쓰기 op → 영수증(`write_pending`, `revision_conflict` 등) | `src/core/persistence/page-mutations.ts` `submitPageMutation`, `persistence/page-prepare.ts:822`, `persistence/journal.ts` `admitWrite`, `engine.transaction` 사용(`persistence/*.ts`) | 코드 확인(진입부·호출), 저널 소비자·효과 적용은 미탐색 |
| import 파이프라인 | 마크다운 frontmatter 파싱, 타임라인 분리, 청킹(코드는 tree-sitter), 임베딩, 버전 스냅샷 | 마크다운 텍스트 → 페이지·청크·태그 | `src/core/import-file.ts` `importFromContent`, `src/core/markdown.ts` `parseMarkdown`, `src/core/chunkers/` | 코드 확인(진입점·호출 위치), 청킹 내부 미확인 |
| 수집·소스 | `sources`로 레포를 등록하고 `sync`가 변경 파일을 import로 넘긴다. Google·GitHub·대화 기록 같은 커넥터도 마크다운 페이지로 구체화해 같은 경로로 넣는다 | 레포·외부 계정 → 파일 import 호출 | `src/commands/sync.ts` `runSync`, `commands/sync/perform.ts` `performSync`, `src/core/source-resolver.ts` | 코드 확인(진입·분기), 커넥터 외부 동작 미확인 |
| BrainEngine | 페이지·청크·링크·사실 등을 저장하는 인터페이스. `PGLiteEngine`(WASM, 기본)과 `PostgresEngine`(+pgvector)이 구현하고 공통 SQL은 `engine-sql/`에 둔다. 연결 시 스키마와 마이그레이션 적용 | SQL, 트랜잭션, `initSchema` | `src/core/engine.ts` `BrainEngine`, `src/core/engine-factory.ts` `createEngine`, `src/core/migrate.ts` `runMigrations` | 코드 확인(진입점), 엔진 내부 미탐색 |
| AI 게이트웨이 | 임베딩·쿼리 확장·채팅·리랭크를 provider 레시피로 라우팅한다. 그림은 읽기 계층에서 나가는 점선만 그렸고, import 파이프라인(임베딩)·사실 추출(채팅)도 같은 게이트웨이를 쓴다 | 텍스트 → 벡터·응답 | `src/core/ai/gateway.ts` `embed`·`chat`·`rerank`, `src/core/embedding.ts`(게이트웨이 래퍼) | 코드 확인(export), provider 내부 미확인 |
| 잡 큐·dream 사이클 | Postgres/PGLite에 저장되는 잡 큐와 워커. `dream`/`autopilot`이 `ALL_PHASES` 30단계(lint, sync, 추출, 임베딩, purge 등)를 순서대로 돌린다 | 잡 제출·완료, 사이클 보고서 | `src/core/minions/queue.ts` `MinionQueue`, `src/core/cycle.ts` `runCycle`·`runPhaseSync`(→`performSync`), `src/commands/autopilot.ts` | 코드 확인(진입점·sync 연결), 단계 본문 미확인 |

**실행 흐름은 그리지 않았다.** 대표 흐름(페이지 쓰기 → 검색)은 스펙 단계의 통합 검토 4항목에서 글로 잇는다.

**미확인 영역**
- 그림에 넣지 않은 것: 스킬(`skills/`)·스키마 팩·관리자 대시보드(`admin/`)·플러그인 트리·OpenClaw 컨텍스트 엔진·native 락 애드온. 모두 지도 행(30, 34~36, 40)에서 다룬다.
- 읽기 계층의 `think` 수집 5개 스트림 중 하나(앵커 페이지 조회)는 `think/gather.ts` 머리 주석의 "four retrievers"와 다르다(코드 확인: `searchTakesVector`·`traversePaths`·`getPage` 호출, 나머지는 보고 확인).
- 그림에서 그리지 않은 간선: 사이클이 사실 추출·임베딩 등 다른 단계를 실행하는 관계, 수집·소스에서 쓰기 저널로 가는 managed 경로(`sync/perform.ts`의 `performManagedBranch`), 커넥터에서 외부 서비스로 가는 네트워크 호출.
- `persistence/`의 저널 소비자(약 400파일)는 열지 않았다. "쓰기 저널 → 엔진" 간선은 `persistence/*.ts`의 `engine.transaction` 호출로 확인했지만, 어떤 순서로 무엇을 쓰는지는 미확인이다.

---

## 4. 질문 (Questions)

사용자 질문의 답입니다. 확정된 동작은 기능 스펙에 반영하고 여기서는 결론만 적습니다.

- [Q1: gbrain이 무엇이고, Claude 같은 에이전트의 기본 메모리와 무엇이 다른가](./questions/q1-what-it-is-vs-builtin-memory.md) - *마크다운이 원본이고 DB는 재생성 가능한 색인. 차이는 저장 형식이 아니라 공유(MCP)·검색·출처 필수·철회 장부에 있음. 실행 확인은 안 함. 후속: 엔티티 없이 저장한 사실은 DB에만 있음(4절).*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md) (범위 승인 후 작성)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸
