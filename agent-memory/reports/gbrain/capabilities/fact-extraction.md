---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-24
updated: 2026-10-24
sources:
  - src/core/ops/facts.ts
  - src/core/facts/backstop.ts
  - src/core/facts/extract.ts
  - src/core/facts/eligibility.ts
  - src/core/facts/capture-sources.ts
  - src/core/facts/capture-dedup.ts
  - src/core/facts/classify.ts
  - src/core/facts/single-prepare.ts
  - src/core/facts/supersession-threshold.ts
  - src/core/facts/writeback-config.ts
  - src/core/facts/writeback-gate.ts
  - src/core/facts/writeback-instructions.ts
  - src/core/facts/notability-filter.ts
  - src/core/facts/extraction-availability.ts
  - src/core/facts/queue.ts
  - src/core/facts/cli-process-mode.ts
  - src/core/facts/drain.ts
  - src/core/facts/drain-config.ts
  - src/core/facts/drain-scheduler.ts
  - src/core/facts/fence-write.ts
  - src/core/facts/extract-from-fence.ts
  - src/core/facts/subject-infer.ts
  - src/core/facts/subject-infer-write.ts
  - src/core/facts/visibility.ts
  - src/core/facts/event-time.ts
  - src/core/facts/absorb-log.ts
  - src/core/facts/conversation-types.ts
  - src/core/facts/conversation-windows.ts
  - src/core/facts/conversation-budget.ts
  - src/core/extraction-watermark.ts
  - src/core/persistence/effect-facts.ts
  - src/core/persistence/effect-journal.ts
  - src/core/persistence/page-advisories.ts
  - src/core/persistence/canonical-projections.ts
  - src/core/minions/handlers/facts-absorb.ts
  - src/core/minions/llm-halt-cooldown.ts
  - src/core/sweep.ts
  - src/core/context/checkpoint-harvest.ts
  - src/core/context/capture-consent.ts
  - src/core/context/corpus-segments.ts
  - src/core/context/corpus-windows.ts
  - src/mcp/context-pack-handler.ts
  - src/commands/hook.ts
  - src/commands/serve.ts
  - src/commands/sync/finalize.ts
  - src/commands/extract-conversation-facts.ts
  - src/core/cycle.ts
  - src/core/cycle/facts-drain.ts
  - src/core/cycle/extract-facts.ts
  - src/core/cycle/conversation-facts-backfill.ts
  - src/core/engine-sql/facts.ts
  - src/core/think/sanitize.ts
  - src/core/search/private-visibility.ts
  - src/mcp/server.ts
  - src/core/ai/date-grounding.ts
  - src/core/trust/taint.ts
  - src/core/write-gate.ts
  - src/core/import-file.ts
  - docs/guides/ambient-writeback.md
depends:
  - ./engine-and-schema.md
  - ./ai-gateway.md
  - ./page-storage-and-import.md
  - ./hybrid-search.md
  - ./memory-verbs.md
status: ready
reimplementation: 미실행
---

# 사실 추출·자동 캡처 (extract_facts · facts-backstop · 캡처 레인 · 대화 사실 배치)

> 에이전트가 넘긴 텍스트 한 덩어리(`extract_facts`), 페이지 쓰기, 하네스 훅이 쌓아 둔 세션 텍스트, 대화 페이지를 받아 서버의 LLM이 "저장할 사실"을 뽑고, 검증·중복 제거·엔티티 해소를 거쳐 `facts` 행(hot memory, 가능하면 엔티티 페이지의 `## Facts` 펜스까지)에 저장한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

질문 ④("어떻게 알아서 '이건 저장해야겠다'를 판단해서 저장하게 되는가")의 답은 "누가 판단하는가"가 경로마다 다르다는 것이다. 에이전트 스스로 부르는 `remember`는 [memory-verbs](./memory-verbs.md) 소관이고, 이 스펙은 **서버의 LLM이 판단하는 경로**를 다룬다. 경로 목록과 켜짐 조건은 1.3의 첫 표다.

공통 파이프라인(모든 서버 추출 경로가 `runFactsPipeline` 또는 `runFactsBackstop`으로 합류):

1. **진입 경로가 텍스트와 출처 라벨을 정한다** (R-01~R-18): `extract_facts` 도구는 `turn_text`와 `mcp:extract_facts`, 페이지 쓰기는 `compiled_truth`와 `mcp:put_page`, 훅이 쌓은 세션 텍스트는 `hook:writeback`·`hook:compact`·`sweep:corpus`.
2. **켜짐 게이트** (R-04, R-12): 킬 스위치 `facts.extraction_enabled`, 페이지 적격성(R-06), 캡처 게이트(R-12), 채팅 모델이 쓸 수 있는지(R-20).
3. **LLM 호출 1회**(필요하면 재시도 포함, R-22): 시스템 프롬프트(R-21)와 `<turn>…</turn>`로 감싼 입력(앞 8,000자, 주입 문구 무력화 사본)을 보내 JSON `{"facts":[…]}`를 받는다.
4. **출력 검증·거름** (R-23~R-25): JSON 파싱 사다리, 후보 최대 10개, 문장 500자, 정크 필터, 알 수 없는 kind는 `fact`, 신뢰도 0..1 clamp, 노터빌리티 허용 집합.
5. **사실마다 임베딩 1회** (R-26): 실패하면 `embedding=null`로 계속.
6. **엔티티 해소와 중복 제거** (R-30~R-33): 캡처 레인은 정확 지문 중복을 먼저 버리고, 그다음 사실마다 철회 여부 → 정확 지문 → 모델별 코사인 임계값 순으로 본다. LLM 분류기는 호출되지 않는다.
7. **저장** (R-40~R-46): 엔티티가 해소되고 소스에 파일 루트가 있으면 엔티티 페이지의 `## Facts` 펜스에 먼저 쓰고 DB 행을 찍는다. 아니면(기본 설치 포함) `facts` 행만 쓴다.
8. **결과**: `{inserted, duplicate, superseded(항상 0), fact_ids}` 또는 건너뜀 사유(R-02, R-03, R-50).

대표 끝-끝 흐름(가정: `memory.auto_writeback=salient`, 하네스 훅 설치, 서버 `gbrain serve` 실행 중, 채팅 키 있음): 사용자가 "I'm leaving YC next month."를 보낸다 → Stop 훅이 마지막 사용자 턴을 게이트(R-25)에 통과시켜 비밀 스캔 후 `<세션>.wb-<hash>.txt`로 쌓고 IPC로 serve에 알린다 → serve가 하베스트 큐에 넣고(R-14) DB 평면 게이트를 다시 확인 → `runFactsPipeline`(source `hook:writeback`, 필터 `medium-and-up`)이 LLM을 1회 부른다 → 뽑힌 후보를 거르고 임베딩 → 캡처 레인 중복 제거 → 엔티티 해소 → `facts` 행 INSERT(기본 설치에서는 DB 전용, visibility는 `facts.default_visibility` 미설정이면 `private`) → 파일에 `.ingested` 사이드카를 쓴다.

### 1.2 범위·통합 지점

- 제공:
  - 서버 LLM이 저장 여부를 판단하는 모든 경로의 트리거·켜짐 조건·실패 처리(R-01~R-18, R-50~R-55).
  - 추출 프롬프트의 판단 기준, 출력 검증, 노터빌리티·정크 필터(R-20~R-26).
  - 저장 전 중복 제거(캡처 레인 규칙 포함)와 `facts` 행/펜스에 쓰는 규칙(R-30~R-46).
  - 에이전트가 쓴 `## Facts` 펜스가 `facts` 행으로 투영되는 규칙(R-18). [page-storage R-23·R-60](./page-storage-and-import.md)이 이 스펙으로 넘긴 부분이다.
  - 비용 통제(R-60, R-61).
- 제외(이유):
  - **managed 쓰기 경로**(`persistence_brain.enabled`가 켜졌을 때의 `publishManagedFacts`·`prepareManagedFactsSession`, `persistence/facts-maintenance.ts`). 기본 설치에서는 꺼져 있다([page-storage R-01](./page-storage-and-import.md): `persistence_brain.enabled` 기본 `false`). 이 스펙은 unmanaged 경로를 기준으로 쓰고 managed 분기는 경계(R-45)만 둔다. **기본 설치에서 켜진 동작을 뺀 것이 아니다.**
  - **엔티티 이름 해소 함수의 본문**: [memory-verbs의 해소 체인(R-12, C-31)](./memory-verbs.md)과 미결정 M-01을 그대로 인용한다. 이 스펙에서 새로 정하는 것은 "해소 결과 `fallback_slugify`는 해소 실패로 취급한다"(R-30)뿐이다.
  - **쓰기 게이트·신뢰 등급의 판정 본문**(`write-gate.ts`, `trust/*`): 지도 13행. 이 스펙은 추출 사실이 어떤 등급·게이트 입력으로 들어가는지와 기본 모드(R-44)만 둔다.
  - **대화 사실 배치의 내부**(`conversation-parser/*`, 대화 창 클레임·영수증·managed 배치·`facts relink`): 경계와 명령 계약만 R-16에 둔다. 이 기능은 기본 꺼짐(사이클 phase)이거나 사용자가 직접 부르는 유료 명령이다.
  - **OpenClaw 컨텍스트 엔진의 컴팩션 3단계**(`context-engine.ts` rung 3): `hook:compact` 레인의 변형으로, 같은 `runFactsPipeline`을 쓴다는 사실만 R-10에 둔다. 본문은 읽지 않았다(확인 한계).
  - 훅 `session-start`·`user-prompt`(맥락 주입)와 `_meta.brain_hot_memory`: 지도 16행.
  - `consolidate`(사실 → takes 합성), dream `synthesize`: 사실을 새로 뽑지 않는다.
  - 훅의 seat·source 스탬프(#4618, #6268)와 IPC 프레임 형식, 코퍼스 사이드카 파일 형식의 세부.
- 외부 의존·선행 계약:
  - [ai-gateway](./ai-gateway.md): 채팅 `chat()`(R-30~R-34), 임베딩 `embedOne`(R-20~R-26), `isAvailable`, 예산 추적기 `BudgetTracker`·`BudgetExhausted`(R-60~R-68). 특히 추출은 앰비언트 추적기가 없으면 상한 없는 기록 전용 추적기를 건다(R-68, 이 스펙 R-52).
  - [memory-verbs](./memory-verbs.md)(draft, M-01만 남음): 펜스 행 형식(R-15), 정확 지문·코사인 대체 판정 `decideSingleFact`(R-17, C-15), 모델별 코사인 임계값, 철회 장부(R-19, R-28), `visibility` 해소(R-20), 엔티티 해소 체인(R-12), 펜스 쓰기 대상 규칙(R-13, R-14), 자동/호출 경계(R-49).
  - [page-storage-and-import](./page-storage-and-import.md): 페이지 쓰기 저널과 `persistence_effects`(R-22, R-23), 쓰기 영수증, 파일 쓰기 결정(R-02).
  - [engine-and-schema](./engine-and-schema.md) 1.3: `facts` 테이블 컬럼과 "활성 사실 = `expired_at IS NULL`".
  - [hybrid-search](./hybrid-search.md): 이 스펙은 검색을 쓰지 않는다. 사실 추출 결과가 검색에서 보이는 방식은 [memory-verbs](./memory-verbs.md) recall이다.
  - 호출자가 제공: 채팅·임베딩 키와 네트워크, 엔진, (페이지 경로) 잡 큐, (캡처 레인) 하네스 훅 설치와 실행 중인 `gbrain serve` 또는 `gbrain sweep`.
- 소유 상태·부작용: `facts` 행(`source`가 `mcp:extract_facts`·`mcp:put_page`·`sync:import`·`hook:*`·`sweep:corpus`·`cli:extract-conversation-facts`·`fence:reconcile`), 엔티티 페이지 파일의 `## Facts` 펜스와 git 커밋(파일 루트가 있을 때), `minion_jobs`의 `facts-absorb` 잡, `persistence_effects`의 `facts-backstop` effect, 코퍼스 디렉터리의 `.wb-`·세그먼트·`<세션>.txt`와 사이드카(`.in-progress`, `.ingested`, `.progress`, `.capture-off.json`), `ingest_log`의 `facts:absorb` 행, `page_extraction_state` 워터마크, `config`의 `facts.drain_state`, `~/.gbrain/facts.write_failures.jsonl`, 훅 하트비트 JSONL, 예산 감사 JSONL.

### 1.3 인터페이스와 데이터 의미

**저장을 판단하는 경로 전체** (질문 ④의 핵심 표). "기본" 열은 **기본 설치**(PGLite, `gbrain init` 직후, 하네스 훅 미설치, 설정 미변경)에서의 상태다.

| # | 경로 | 판단 주체 | 트리거 | 켜짐 조건 (설정 키 원문) | 기본 | `facts.source` | R |
|---|---|---|---|---|---|---|---|
| ① | 에이전트의 `remember`(+ `memory.auto_writeback`이 켜지면 지시문이 부추김) | 에이전트의 LLM | 에이전트가 도구를 부름 | 항상 가능. 지시문 절은 `memory.auto_writeback`=`salient`\|`all` | 도구 켜짐, 지시문 꺼짐 | 에이전트가 준 출처 문자열 | [memory-verbs R-49](./memory-verbs.md), R-17 |
| ② | `extract_facts` 도구 | 서버의 채팅 모델 | 에이전트(또는 CLI)가 `turn_text`를 넘겨 부름 | `facts.extraction_enabled` 미설정=켜짐. 전체 surface에만 노출(verbs surface에는 없음, [memory-verbs R-04](./memory-verbs.md)) | **켜짐**(채팅 키가 있어야 동작) | `mcp:extract_facts` | R-02, R-03 |
| ③ | 페이지 쓰기 백스톱 | 서버의 채팅 모델 | `put_page`·`capture`·`edit_page`·`append_page` 커밋 뒤 `facts-backstop` effect → `facts-absorb` 잡 | `facts.extraction_enabled` + 페이지 적격(R-06). `facts.page_write_notability_filter`(기본 `all`) | **켜짐**(채팅 키와 잡 실행 주체가 있어야 동작) | `mcp:put_page` | R-05~R-08 |
| ③′ | `gbrain sync` 사후 백스톱 | 서버의 채팅 모델 | sync가 건드린 페이지 1~50개 | 위와 같음 + `sync --no-extract`가 아님 | **켜짐**(sync를 쓰면) | `sync:import` | R-07 |
| ④ | Stop 훅의 턴 은행 + serve 하베스트 | 결정적 게이트(LLM 0회) 다음 서버의 채팅 모델 | Stop 이벤트마다 마지막 사용자 턴 | **`memory.auto_writeback`=`salient`\|`all`일 때만**(훅은 파일 평면, serve는 DB 평면) | 꺼짐 | `hook:writeback` | R-09, R-14 |
| ⑤a | PreCompact 훅의 세그먼트 은행 + serve 하베스트(OpenClaw 컴팩션 포함) | 서버의 채팅 모델 | 컴팩션 직전 | **하네스 훅을 설치하면 `memory.auto_writeback`이 미설정이어도 켜짐**, 명시적 `off`면 꺼짐(R-12) | 훅 미설치라 은행 자체가 없음 | `hook:compact` | R-10, R-12, R-14 |
| ⑤b | SessionEnd 훅의 전사본 은행 + 유지보수 sweep | 서버의 채팅 모델 | 세션 종료 후 sweep(serve 유휴 10분 틱, `serve --http` 코퍼스 드레인, `gbrain sweep --once`, cron/autopilot) | ⑤a와 같음 | 훅 미설치라 은행 자체가 없음 | `sweep:corpus` | R-11, R-12, R-13 |
| ⑥ | dream/autopilot 사이클의 사실 단계 | 사이클 phase `extract_facts`는 LLM 없음(펜스 → DB 동기화). `facts_drain`은 ③의 잡을 대신 실행(PGLite). `conversation_facts_backfill`은 LLM 추출 | `gbrain dream`, autopilot | `conversation_facts_backfill`은 `cycle.conversation_facts_backfill.enabled`(기본 **꺼짐**, `--once`로 1회 우회) | `extract_facts` phase와 `facts_drain`은 사이클이 돌면 실행 | `fence:reconcile` / `mcp:put_page` 등 / `cli:extract-conversation-facts` | R-15 |
| ⑦ | `gbrain extract-conversation-facts` | 서버의 채팅 모델 | 사용자가 명령 실행 | `facts.extraction_enabled`(`--override-disabled`로 우회). 비용 상한 `--max-cost-usd`(기본 5.0) | 수동 실행 | `cli:extract-conversation-facts` | R-16 |
| ⑧ | 에이전트가 쓴 `## Facts` 펜스를 가진 페이지 쓰기 | 에이전트의 LLM(서버 LLM 0회) | `put_page` 발행 트랜잭션, sync, 사이클 `extract_facts` phase | 항상(펜스가 있고 페이지가 격리되지 않았을 때) | **켜짐** | 행의 `source` 칸, 없으면 `fence:reconcile` | R-18 |

서버는 `extract_facts`를 도구 응답 뒤에 자동으로 부르지 않는다(`runFactsPipeline`·`runFactsBackstop`의 호출자는 위 경로뿐이고 `mcp/dispatch.ts`는 부르지 않는다, R-01).

**`extract_facts` 도구**(C-01): 입력은 `turn_text`*(string), `request_id`, `session_id`, `entity_hints`(string[], 앞 5개만 전달: `ENTITY_HINTS_CAP`), `is_dream_generated`(bool), `valid_from`(ISO 8601), `source_slug`, `visibility`(`private`|`world`). scope `write`. 출력은 `{inserted, duplicate, superseded, fact_ids[], entity_hints_used, entity_hints_dropped}`에 선택 필드 `write_requests`, `withdrawn_skipped`, `refused[]`, `would_dedup_same_page`가 붙거나, 건너뜀 봉투 `{inserted:0, …, skipped, reason?, agent_action?}`다.

**설정 키**(원문 이름. 값 해석은 읽는 코드가 정한다):

| 키 | 기본값 | 의미 |
|---|---|---|
| `facts.extraction_enabled` | 미설정 = 켜짐 (`false`/`0`/`no`/`off`, 대소문자 무시, 가 꺼짐) | 모든 서버 추출 경로의 킬 스위치(⑦은 `--override-disabled`로 우회) |
| `facts.extraction_model` | 없음 | 추출 모델. 해소 순서는 R-20 |
| `facts.extraction_max_tokens` | 4000 | 추출 호출의 출력 토큰 상한(양수만 유효) |
| `facts.extraction_prompt_appendix` | 없음 | 비어 있지 않으면 시스템 프롬프트 끝에 그대로 덧붙임(운영자 입력) |
| `facts.extraction_junk_filter` | 켜짐 | 정크 정규식 필터 끔 스위치 |
| `facts.extraction_missing_confidence` | 1.0 | 후보의 신뢰도가 없거나 숫자가 아닐 때 저장할 값(0..1일 때만) |
| `extraction.date_grounding` | 켜짐(`false`/`off`/`0`이 끔) | 프롬프트 변형: 상대 날짜를 관측일 기준 절대 날짜로, `valid_from` 출력 |
| `facts.attribution` | 켜짐 | 프롬프트 변형: 비서가 한 말은 별도 사실, `attributed_to` 출력 |
| `facts.default_visibility` | 미설정 → `private`(`world`만 world) | 호출자가 가시성을 안 줄 때 추출 사실의 가시성(R-43) |
| `facts.page_write_notability_filter` | `all` (`all`\|`high-only`\|`medium-and-up`만 유효) | ③의 노터빌리티 허용 집합 |
| `facts.entity_inference` | 켜짐(`off`/`false`/`0`/`no`/`disabled`가 끔) | 엔티티 없는 사실에 쓰기 시점 주체 추론(R-46) |
| `facts.supersession_thresholds` | 없음 | 모델별 코사인 임계값 덮어쓰기(JSON, 값 0 초과 1 이하 또는 `"off"`) |
| `facts.drain_budget_usd` / `facts.drain_daily_budget_usd` / `facts.drain_max_jobs` | 1 [0.01,100] / 5 [0.01,1000] / 50 [1,1000] | PGLite 자동 드레인의 실행당·24시간 USD 상한, 실행당 잡 수 |
| `memory.auto_writeback` | 미설정(= `off`와 다름, R-12) | `off`\|`salient`\|`all`. 미인식 값은 레인 보류 |
| `memory.auto_writeback_transient_ttl` | `3d` | 지시문이 일시적 사실에 에이전트가 줄 `ttl` |
| `cycle.conversation_facts_backfill.enabled` | `false` | ⑥의 대화 사실 backfill phase (그 밖의 `.max_cost_usd` 1.00, `.max_total_cost_usd` 5.00, `.max_walltime_min` 20, `.max_total_walltime_min` 30, `.types`) |
| `sync.write_through` | 켜짐 (`false`/`0`/`off`/`no`가 끔) | 꺼지면 모든 추출 사실이 DB 전용([memory-verbs R-14](./memory-verbs.md)과 같은 키) |
| 환경변수 `GBRAIN_HOOKS=0` / `GBRAIN_SWEEP=0` / `GBRAIN_LLM_HALT_COOLDOWN=0` | 미설정 | 훅 전체 중단 / serve sweep·드레인 중단 / 공급자 중단 쿨다운 끔 |

**코퍼스 파일 이름과 레인**(코드의 파서가 정한다, C-17): Stop 훅의 턴 파일 `<세션>.wb-<hash24>.txt`(→ 레인 `writeback`), PreCompact 세그먼트(→ `compact`), SessionEnd 전사본 `<세션>.txt`(→ `session_end`). 같은 턴은 같은 이름이므로 재발화해도 같은 파일이다.

**`gbrain hook <event>`**(C-22): 이벤트 `session-start`, `user-prompt`, `stop`, `session-end`, `compact`. 알 수 없는 이벤트만 종료 코드 1(usage 출력), 나머지 런타임 경로는 항상 0.

**`gbrain extract-conversation-facts`**(C-30) 옵션: `--dry-run`, `--json`, `--force`, `--yes`, `--override-disabled`, `--slug`, `--slugs a,b`, `--source-id`, `--since`, `--types`(`conversation, meeting, slack, email, imessage, imessage-daily` 부분집합), `--limit`, `--sleep`(ms, 호출 간 기본 200), `--segment-limit`, `--max-cost-usd`(기본 5.0), `--workers`/`--concurrency`.

### 1.4 행동 규칙과 남은 질문

검증 수준 표기: "코드 확인"은 구현부를 읽음. "실행 확인"은 `agent-memory/artifacts/gbrain/fact-extraction-demos/demo-pure.mts`를 deno로 돌려(출력 `demo-pure.out.2026-10-24.json`) 관찰함. 실제 모듈을 import한 것과 줄 범위를 잘라 실행한 것의 구분은 스크립트 머리말에 있다. LLM 호출·DB·SQL·훅 프로세스·IPC는 실행하지 못했다(확인 한계).

**A. 경로와 트리거**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 서버 추출의 호출자 전체 | `runFactsPipeline`(텍스트 한 덩어리 입구)의 호출자는 `extract_facts` 도구(`mode:'inline'`), sweep 코퍼스 패스, serve 하베스트(`checkpoint-harvest`), OpenClaw 컨텍스트 엔진 rung 3이다. `runFactsBackstop`(페이지 입구)의 호출자는 `facts-absorb` 잡 핸들러와 `gbrain sync` 사후 단계다. MCP 디스패치(`mcp/dispatch.ts`)·`put_page` 핸들러는 직접 부르지 않고(페이지 쓰기는 effect→잡을 거침, R-05), 도구 응답 뒤에 서버가 추출을 자동 호출하는 곳은 없다. `gbrain import`(대량 가져오기)는 사실 추출을 부르지 않고(코드 주석: 첫 가져오기 비용 급증 방지, `dream`으로 보충), `code_import`·`file_upload`는 `FactsBackstopSource` 라벨만 있고 호출자가 없다 (C-02, C-03, C-20, C-23, C-24) | 코드 확인 (호출자 grep 전수) |
| R-02 | `extract_facts` 호출 | 순서: `dry_run`이면 `{dry_run:true, action:'extract_facts'}`. 킬 스위치가 꺼졌으면 `skipped:'extraction_disabled'`(0 카운트, 오류 아님). `is_dream_generated:true`면 `skipped:'dream_generated'`(순환 방지). `valid_from`이 파싱 안 되면 `invalid_params`(조용히 now로 두지 않음). 가시성은 `visibility` 인자(`world`/`private`) > `facts.default_visibility` > `private`(R-43). `source_slug`가 있고 가시성이 `world`면 그 페이지를 읽어 비공개 페이지(또는 원격 호출자가 못 보는 페이지)면 `private`로 내린다. 그다음 `runFactsPipeline(turn_text, {source:'mcp:extract_facts', sessionId: session_id, entityHints, validFrom, sourceSlug, visibility, requestId: request_id 또는 새 UUID})`을 부른다. 성공 시 카운트와 `fact_ids`, `entity_hints_used`(= min(개수, 5)), `entity_hints_dropped`를 돌려준다 (C-01) | 코드 확인 |
| R-03 | `extract_facts`의 실패 봉투 | 파이프라인이 `chat_unavailable`로 끝나면 `skipped:'extraction_unavailable'` + `agent_action`("서버 채팅 모델이 없으니 당신이 직접 최대 약 10개를 뽑아 `remember`로, 한 호출에 주장 하나, 출처 필수, `kind`·`entity` 지정, `visibility: "<해소된 값>"` 명시"; `private`이면 "remember는 기본이 world라 생략하면 넓어진다"는 문구가 붙음). 그 밖의 비전송 실패(`refusal`·`content_filter`·`non_terminal_stop`·`malformed_output`)는 `skipped:'extraction_failed'` + `reason` + `agent_action`. 전송 실패(`provider_error`)와 두 번 잘린 출력(`truncated_output`)은 봉투가 아니라 오류로 전파된다(R-51). 이 봉투는 자동 경로를 에이전트의 `remember`로 되돌리는 연결점이다([memory-verbs R-49](./memory-verbs.md) ③) (C-01, C-04) | 코드 확인 |
| R-04 | 킬 스위치 `facts.extraction_enabled` | 미설정이면 켜짐. `false`/`0`/`no`/`off`(공백 제거·소문자)만 끔. 확인 지점: `extract_facts`(R-02), 페이지 쓰기 사전 점검·effect 큐잉·effect 디스패치(R-05), `runFactsBackstop`(R-05), 드레인(R-08), sweep 코퍼스 패스(R-13), 하베스트(R-14), `extract-conversation-facts`(`--override-disabled`로 우회, R-16). 캡처 레인은 꺼진 상태에서도 아직 쌓인 파일을 `off` 때만 retire한다(R-12) (C-06, C-18, C-24) | 코드 확인 |
| R-05 | 페이지 쓰기 → 추출 (③) | `put_page`·`capture`·`edit_page`·`append_page`의 준비 단계에서 `prepareFactsBackstop`이 `{queued:true}` 또는 `{skipped:사유}`를 영수증의 `facts_backstop`에 싣는다. 사유 순서: 제한된 작성자(슬러그 한정·위임·`extract_facts` 권한 없음) → `extraction_disabled` → 적격성 사유(R-06) → `body_unchanged`(이 쓰기가 `compiled_truth`를 바꾸지 않았고, 이전에 이미 적격했고, 이 페이지에 완료된 `facts-absorb` 잡이 있고, 대기 중인 추출이 없을 때). 예외가 나면 `backstop_error`. 변화 없는(noop) 쓰기는 `not_imported`. `queued`이면 **발행 트랜잭션 안에서** `facts-backstop` effect를 큐에 넣고(그때 킬 스위치를 다시 확인, 가시성은 `resolveDefaultVisibility`로 그 시점 값을 고정), 커밋 뒤 effect 디스패처가 같은 트랜잭션에서 권한·revision을 다시 확인해 minion 잡 `facts-absorb`를 만든다: `{slug, sourceId, source:'mcp:put_page', sessionId:'put_page:<slug>', notabilityFilter(=facts.page_write_notability_filter), visibility, persistence_request_id, page_id, revision}`, 멱등 키 `facts-absorb:write:<request_id>`, 최대 5회·지수 백오프 기준 60초. 페이지가 그새 바뀌어 revision이 다르면 `superseded`로 건너뛴다. 삭제된 페이지는 큐잉하지 않는다 (C-18) | 코드 확인 |
| R-06 | 페이지 적격성 `isFactsBackstopEligible` | 거절 사유 순서: 페이지 없음 `no_parsed_page` → 슬러그가 `wiki/agents/` 접두 `subagent_namespace` → 격리된 페이지 `quarantined` → frontmatter `dream_generated: true` `dream_generated` → frontmatter `facts_backstop`이 `false`/`0`/`no`/`off` `opted_out` → `compiled_truth` trim 길이 < 80자 `too_short` → 타입 불적격. 적격 타입: `note, meeting, slack, email, calendar-event, source, writing, media, tweet, analysis`. 슬러그가 `meetings/`·`personal/`·`daily/`로 시작하면 타입이 불적격이어도 구제. 불적격 타입의 사유는 `conversation_pipeline`(타입이 대화 사실 파이프라인 대상: `conversation`, `slack-dm-day`, `slack-thread`, `email-digest`, `imessage`, `imessage-daily`) 또는 `kind:<type>`(`concept`·`atom`·`code` 등. `concept`·`atom`은 의도적으로 제외). 이 판정은 페이지 입구(③, ③′)에만 적용되고 `extract_facts`·캡처 레인에는 적용되지 않는다 (C-11) | 코드 확인 + 실행 확인 (T-03) |
| R-07 | `gbrain sync` 사후 (③′) | sync 끝에서 `--no-extract`가 아니고 이번 실행이 건드린 페이지가 1개 이상 **50개 이하**일 때만, 페이지마다 소스 범위로 `getPage` 후 `runFactsBackstop(…, {sessionId:'sync:<slug>', source:'sync:import', mode:'queue', notabilityFilter:'high-only'})`을 부른다(페이지별 실패는 삼킴). 50개 초과면 사실 추출은 하지 않는다. `queue` 모드의 실행: (a) 한 번 쓰고 끝나는 CLI 프로세스(`isShortLivedCliProcess`)면 `facts-absorb` 잡을 만든다(멱등 키 `facts-absorb:<source>:<slug>:<본문 sha256 앞 16자>`, 5회·60초) — 잡 제출이 실패하면 (b)로 폴백. (b) 이 프로세스에서 실행: 추출 가능 여부 게이트(R-20) 뒤 인프로세스 큐에 넣는다(최대 100개, 넘치면 가장 오래된 것을 버려 `queue_overflow`를 `ingest_log`에 기록, 세션당 동시 1개로 직렬화) (C-20) | 코드 확인 + 실행 확인 (T-12) |
| R-08 | `facts-absorb` 잡을 누가 실행하나 | 잡 핸들러는 페이지를 다시 읽어(`readFactsBackstopJobPage`: 페이지 없음 `page_missing`, revision 불일치 `superseded`, 권한 상실 `permission_denied`/`source_changed`/`page_not_found`로 건너뜀) `runFactsBackstop(inline)`을 부른다. 채팅 불가: 키가 있는 워커면 `FactsExtractionError('chat_unavailable')`로 던져 재시도·실패 가시화, 키 없는 워커면 `JobDeferredError('no_key')`로 30분 뒤 재시도(시도 횟수 안 씀). 실행 주체: **Postgres**는 잡 워커(`gbrain jobs work`/supervisor). **PGLite**는 워커가 없으므로 상주 프로세스가 대신한다: stdio `gbrain serve`와 `serve --http`의 드레인 스케줄러(10분 틱마다, 직전 틱 이후 전경 활동이 없었거나 마지막 실행 후 30분이 지났을 때 한 번 실행), dream/autopilot 사이클의 `facts_drain` phase. 드레인은 한 번에 잡 하나씩, 실행당 USD 상한(`facts.drain_budget_usd`)·24시간 상한·잡 수(`facts.drain_max_jobs`)·벽시계 5분으로 멈추고, 멈춘 사유(예산·키 없음·종료·공급자 중단)는 잡을 시도 횟수 없이 대기로 둔다. 예산 소진은 오류 원인 체인에서 `BudgetExhausted`를 찾아 같은 방식으로 처리한다. 공급자가 전역으로 망가졌을 때(`auth`·`billing` 첫 발생, `rate_limit` 연속)는 워커 프로세스 안 쿨다운이 같은 공급자의 잡을 시도 없이 미룬다 (C-19, C-21) | 코드 확인 |
| R-09 | Stop 훅 (④) | `gbrain hook stop`은 엔진을 열지 않고(LLM 0회) 자기 마감 2,000ms 안에서: 파일 평면 `memory.auto_writeback`이 꺼짐 또는 미설정이면 `wb_off`로 끝 → 세션 id·트랜스크립트 경로(확인된 경로)·gbrain 자신의 claude-cli 세션 여부(맞으면 `self_capture`) → 마지막 "진짜" 사용자 턴(끝 128KB, 못 찾으면 2MB까지 재시도) → **결정적 게이트 `gateWritebackTurn`**(R-25) → 통과한 정규화 텍스트를 비밀 스캔(`redactFindings`)해 `<세션>.wb-<hash24>.txt`로 쓴다(스캐너를 못 불러오면 은행에 넣지 않음, 같은 이름 파일이나 `.ingested`가 있으면 `wb_dup`) → serve의 IPC 소켓(`hookResolveSocketForConfig`와 공유 비밀)으로 `{bankOnly:true, trigger:'writeback-bank', flushCorpusFile}` 요청. serve가 없으면 파일만 남고 sweep이 나중에 추출한다. 모든 결과는 하트비트의 사유 코드로 기록된다 (C-15, C-22) | 코드 확인 + 실행 확인 (T-01) |
| R-10 | PreCompact 훅·OpenClaw 컴팩션 (⑤a) | `gbrain hook compact`는 마감 3,000ms 안에서 마지막 20턴 창을 읽어 **먼저** 내용 주소 지정 세그먼트 파일과 원장을 쓴다(비밀 스캔을 못 하면 세그먼트를 아예 안 씀, 설정과 무관하게 모든 엔진 설정에서). 그다음 serve에 `{bankOnly:true, trigger:'compact-bank', flushCorpusFile}`을 보낸다. 대화 창에서 서 있는 엔티티를 세션 커서에 은행에 넣는 일은 16행. OpenClaw 컨텍스트 엔진은 같은 세그먼트를 스풀에 쓰고 rung 3에서 `runFactsPipeline(source:'hook:compact')`을 직접 부른다 (C-22, C-23) | 코드 확인 / OpenClaw rung 3 본문 미열람 |
| R-11 | SessionEnd 훅 (⑤b) | `gbrain hook session-end`는 트랜스크립트를 파싱해 비밀 스캔(스캐너가 없으면 스캔 없이도 쓰고 하트비트에 `scan_unavailable`) 후 `<세션>.txt`를 **원자적으로(tmp+rename)** 쓴다. 같은 세션 id는 같은 파일을 덮어쓴다(재개된 세션 dedup), 쓴 뒤 이전 `.ingested`·`.in-progress` 사이드카를 지워 sweep이 다시 처리하게 한다. 경계 창이 이미 세그먼트로 은행에 들어 있으면 마지막 경계 뒤 나머지만 쓴다(`decideCorpusMode`). 훅은 **추출하지 않는다**. 보존 기간 지난 파일 정리(`dream.synthesize.corpus_retention_days`, 기본 30일, 추출 안 된 파일은 3배). gbrain 자신의 claude-cli 세션은 은행에 넣지 않는다(`self_transcript`) (C-22) | 코드 확인 |
| R-12 | 캡처 게이트 `memory.auto_writeback` × 레인 | 게이트는 DB 평면(권위)을 읽고(`{gate:true}`, 마지막 정상 값 캐시는 쓰지 않음) 파일 평면은 드리프트 감지에만 쓴다. 레인별 결정 표(실행 확인, T-02): 미설정 → Stop 턴 `retire`, 컴팩션 `extract`, SessionEnd `extract`. 명시 `off` → 셋 다 `retire`. `salient`/`all` → 셋 다 `extract`. 미인식 값 → 셋 다 `hold`. DB 행 없음+파일 평면 켜짐(평면 드리프트) → 셋 다 `hold`. DB 행 없음+파일 평면 `off`(off 이중 쓰기 실패) → Stop 턴 `retire`, 나머지 `hold`. 읽기 실패 → 셋 다 `hold`. `extract`=레인 실행, `retire`=추출 없이 끝난 것으로 기록(`.progress`와 `writeback_off` 사이드카. 나중에 켜도 되살리지 않음), `hold`=파일을 건드리지 않고 설정이 일관돼질 때까지 둠. **즉 `docs/guides/ambient-writeback.md`가 말하는 대로, `memory.auto_writeback`이 미설정이어도 컴팩션 수확과 SessionEnd 추출은 돈다(훅 설치가 그 두 레인의 옵트인).** 캡처 시점에도 적용: 파일 평면이 `off`면 PreCompact·SessionEnd 훅이 `<파일>.capture-off.json`(브레인 id와 쌓은 턴의 해시)을 먼저 써서, 나중에 `on`이 돼도 그 턴은 추출하지 않는다. 사실 발행 직전에도 다시 확인해(`assertAmbientCaptureAdmissible`) `off`가 됐으면 `ambient_capture_off`로 버린다(명시적 `remember`·`extract_facts`는 영향 없음, 캡처 레인 `source`일 때만) (C-14, C-17) | 코드 확인 + 실행 확인 (T-02) |
| R-13 | 유지보수 sweep의 코퍼스 패스 | 실행 계기: stdio serve가 stdin 유휴 10분 틱마다 예산 3,000ms로 한 번 + 서버 시작 3초 뒤 1회(`armStartupSweep`, `GBRAIN_SWEEP=0`이면 둘 다 끔), `serve --http`의 코퍼스 드레인(10분 간격, 예산 60,000ms), `gbrain sweep --once`, cron/autopilot. 패스 순서: 코퍼스 `.txt` 후보 선택(스풀 디렉터리 먼저, 최대 `batchLimit`=20) → **캡처 게이트로 retire**(키 없음·킬 스위치보다 먼저 적용) → 추출 불가면 `keyless`로 패스 전체 건너뜀 → `extraction_disabled`면 건너뜀 → 파일마다 `.in-progress` 클레임(O_EXCL, 60분 지나면 죽은 클레임으로 재획득) → `.ingested` 재확인 → gbrain 자기 세션이면 `self_capture` 사이드카 → 게이트 재적용 → dream 산출물이면 `dream_output` 사이드카 → 파일의 소스 해소(근거 없으면 보류) → `.wb-` 파일은 한 번에(`hook:writeback`, 게이트 모드가 `salient`면 필터 `medium-and-up`), 그 밖의 파일은 턴 경계 **창**으로 나눠 창마다 `runFactsPipeline(source:'sweep:corpus', sessionId:'sweep:corpus:<파일>', visibility 미지정)`. 창 한도: 파일당 8개, sweep 전체 32개(`GBRAIN_CORPUS_WINDOWS_PER_SWEEP`), 실패 누적 시 `.progress`로 재개·죽은 창은 설정 지문이 바뀌면 한 번 재무장. 모든 창이 끝나야 `.ingested`(성공 뒤, 카운트 포함)를 쓴다. 예산은 파일·창 사이에서만 멈춘다 (C-24) | 코드 확인 |
| R-14 | serve 하베스트 (④, ⑤a의 빠른 길) | 훅의 IPC 요청을 받은 serve가 `flushCorpusFile` 이름을 검증(안전 기본 이름, `..` 금지, 같은 소스만: 다르면 `source_mismatch`)하고 `scheduleCheckpointHarvest`로 FIFO 큐(최대 8, 넘치면 `queue_full`, 같은 파일 `already_queued`)에 넣은 뒤 즉시 응답한다(LLM을 기다리지 않음). Stop 턴(레인 `writeback`)은 세션당 30회 상한(`session_cap`, serve 재시작 시 초기화, 200세션 LRU)이고 초과분은 파일이 남아 sweep이 추출한다. 실행은 클레임 → `.ingested` 확인 → 캡처 게이트 → 추출 가능·킬 스위치 → dream 산출물 → 첫 창을 60초 마감으로 `runFactsPipeline`(`hook:compact`, 컴팩션 세그먼트) 또는 `runCorpusTurn`(`hook:writeback`, `salient`면 `medium-and-up`) → 중단됐으면 아무것도 쓰지 않고 클레임 해제(재시도 가능) → 성공하면 `.ingested`(카운트 포함). `extract_skipped_*`(거절·형식 불량)는 사이드카를 쓰지 않아 sweep이 한 번 더 시도한다. 컴팩션 세그먼트는 추가로 체크포인트 링크 매니페스트를 발행한다(16행). 써야 할 파일이 쓰기 소유자 준비 전이면 5·15·45초 뒤 다시 큐에 넣는다 (C-23) | 코드 확인 |
| R-15 | dream/autopilot 사이클 | 사실과 관련된 phase 세 개. `extract_facts`: LLM 없음. 변경된 페이지의 `## Facts` 펜스를 파싱해 DB 인덱스를 펜스에 맞춘다(행 번호·claim이 같으면 제자리 갱신, 펜스에서 사라진 행은 만료·분리하고 삭제하지 않음, 파싱 경고가 있는 페이지는 기존 인덱스 유지, 펜스에 못 올린 `row_num IS NULL` 활성 행은 라이브 엔티티 페이지에 먼저 펜스로 올린 뒤 같이 동기화, 대화 추출 행은 건드리지 않음). `facts_drain`: PGLite에서만 ③의 잡을 실행(R-08), Postgres는 건너뜀, 죽은 `facts-absorb` 잡 재제출. `conversation_facts_backfill`: 기본 꺼짐(R-16). dream 사이클 자체가 기본으로 켜져 있는지는 `sweep.ts` 머리 주석("dream is disabled by default")만 읽었고 스케줄러는 열지 않았다 (C-31, C-21) | 코드 확인 (사이클 스케줄러 미열람) |
| R-16 | `extract-conversation-facts`와 대화 사실 배치 (⑦, ⑥) | 대화형 페이지(`conversation, meeting, slack, email, imessage, imessage-daily`와 별칭 타입, frontmatter `conversation_parseable: false`는 제외)를 소스 하나 단위로 읽는다. 본문(`raw_transcript` 사이드카 우선)을 대화 메시지로 파싱해 **30분 간격**으로 묶고(메시지 2개 미만 묶음 제외) 창당 최대 30메시지·렌더 6,500자로 자른다. 창마다 `extractFactsFromTurnWithOutcome`(source `cli:extract-conversation-facts`, 세션 `cli:extract-conversation-facts:<slug>`, 엔티티 힌트)을 호출한다(실패하면 페이지 전체가 실패, 부분 저장 없음). 후보의 엔티티는 저장 시점 해소기로 정규화(실패하면 엔티티 없이 보존)하고 `row_num`·`source_markdown_slug=<페이지 slug>`를 붙인 `facts` 행으로 **페이지 단위 일괄 발행**(이전 배치를 완전한 교체가 있을 때만 퇴역)하며 마지막에 터미널 감사 행을 같은 트랜잭션에 넣는다. 이 경로는 **정확/코사인 중복 제거를 하지 않고** 마크다운 펜스·페이지도 만들지 않는다. 비용: `--max-cost-usd`(기본 5.0)의 `BudgetTracker`, 예산 소진은 페이지 처리를 멈추고 중단 영수증, 호출 간 sleep 200ms, 페이지 본문 상한. 사이클 phase는 소스당 $1·전체 $5·20분/30분 상한 (C-30) | 코드 확인 (대화 파서·클레임·영수증 내부 미열람) |
| R-17 | `memory.auto_writeback`의 지시문 본문 (①을 부추김) | 값이 `salient`/`all`이면 서버 instructions 끝에 11줄 절이 붙는다([memory-verbs R-05](./memory-verbs.md)). 본문의 판단 기준: (1) 사용자가 자신·사람·프로젝트·계획에 대해 한 실질적 진술은 모두 저장 후보 (`salient`는 선호·정정·결정·약속·관계·프로젝트 상태 변화만, `all`은 직접적 사실 진술 전부이되 운영 잡담·비서 생성물·비밀·인용된 제3자 자료 제외) (2) `remember`로 한 호출에 주장 하나, `kind`와 `entity` 지정 (3) 한 턴에 사실이 여럿이면 `extract_facts`로 원문 한 번(도구가 호출 가능할 때만 안내) (4) 출처에 하네스·세션·날짜 (5) 지속 사실은 `ttl` 생략, 일시적 사실(건강·위치·여행·기분·근일 일정)은 `ttl: "<memory.auto_writeback_transient_ttl>"`이고 `extract_facts`로는 `ttl`을 못 주니 배치하지 말 것 (6) 인사·확인·새 사실 없는 질문·도구 출력·인용·붙여넣기는 건너뜀 (7) 자기 추론·진단·추측을 사용자 사실로 저장 금지, 원문 전사 금지 (8) 가시성은 해소된 자세(`facts.default_visibility` 미설정이면 `world`, 명시적 비-world면 `private`)를 모든 저장에 명시 (9) 인증된 소스 범위 안에서만, 조용히 쓴다. 서버는 이 절의 이행을 검증하지 않는다 — 저장 행위는 에이전트의 `remember`다 (C-16) | 코드 확인 + 실행 확인 (절 문구) |
| R-18 | 에이전트가 쓴 `## Facts` 펜스 → `facts` 행 (⑧) | `put_page` 계열 발행 트랜잭션이 본문의 펜스를 파싱해(펜스 행 형식은 [memory-verbs R-15](./memory-verbs.md)) 행으로 투영한다(격리된 페이지는 투영 안 함). 행 변환(`extractFactsFromFenceText`): 엔티티=페이지 slug, `source_markdown_slug`=slug, `row_num`=펜스 행 번호, `source`=행의 출처 칸(없으면 `fence:reconcile`), `valid_from`=행 값(없으면 DB 기본 now), `valid_until`=행 값; 취소선 행은 비활성: `forgotten`이거나 `superseded by`가 없는 비활성 행은 `valid_until`이 비어 있으면 오늘(UTC 자정), 만료 시각 `expired_at`은 `valid_until` 또는 오늘, `superseded by #N`은 페이지 안 행 번호로 보관했다가 삽입 때 사실 id로 해소. 발행 트랜잭션: 펜스에 더 이상 없는(행 번호+claim+visibility가 같은 행이 없는) 기존 행은 `expired_at`을 걸고 `row_num`을 NULL로 풀어 **삭제하지 않으며**(영수증의 id가 계속 유효), `cli:extract-conversation-facts` 행은 같은 행 번호를 펜스가 차지할 때만 건드린다. 새 행은 `insertFacts`(`(source_id, source_markdown_slug, row_num)` 충돌은 무시), 기존 행의 필드(kind, notability, context, 유효 기간, 신뢰도, 타입 클레임, 귀속)는 갱신. 같은 claim·출처의 중복 활성 행은 인덱스에 한 번만(`duplicateActiveFenceRows`, 서로 다른 두 화자는 중복 아님). 신뢰도가 쓴 사람보다 높은 행은 지우지 않고 보류한다(13행). 이 투영은 서버 LLM을 부르지 않는다 (C-27, C-31) | 코드 확인 + 실행 확인 (T-10) |

**B. 핵심 판단 단계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 추출 호출 전 | 입력이 비었으면(또는 `isDreamGenerated`) `{ok:true, facts:[]}`로 LLM을 부르지 않는다. 입력은 **앞 8,000자**(`MAX_TURN_TEXT_CHARS`)만 쓰고, `INJECTION_PATTERNS`로 무력화한 **프롬프트 사본**을 보낸다(저장될 사실 문장은 원문 기준, R-23). 모델: 호출자가 준 `model` 또는 `resolveFactsExtractionModel` = `facts.extraction_model` → `models.tier.reasoning` → `models.default` → `GBRAIN_MODEL` → 키 인지형 티어 기본값([ai-gateway R-08·R-09](./ai-gateway.md)). 해소 출처가 티어 기본값이거나 폴백이고 provider가 `anthropic`이면 측정된 기본 `anthropic:claude-haiku-5-5`로 바꾼다. 그 모델이 `isAvailable('chat', model)`가 아니면 LLM 없이 `chat_unavailable`. 페이지 경로는 호출 전에 같은 게이트를 한 번 더 건다(`resolveExtractionAvailability`, 실행하는 프로세스에서만) (C-06, C-09, C-32) | 코드 확인 |
| R-21 | 시스템 프롬프트가 "저장할 가치"를 정하는 방식 | 핵심 지시문: 대화 한 턴에서 개인 지식 주장을 구조화한 사실로 뽑는다. 턴은 `<turn>…</turn>`에 감싸 데이터로만 취급. 출력은 한 줄 JSON `{"facts":[{fact, kind, entity, confidence, notability, metric, value, unit, period}]}`, 산문·코드펜스 금지, 주장할 만한 것이 없으면 빈 배열이 유효. 규칙: 사용자 발언은 가능한 원문 그대로, 톤 재해석 금지. `kind`는 `event`(특정 시각에 일어났거나 예정)·`preference`(지속적 취향)·`commitment`(약속·합의·결정)·`belief`(바뀔 수 있는 의견·가설·입장)·`idea`(새 아이디어·틀·논지)·`fact`(그 외 객관적 주장). **인사·운영 잡담·질문("X는 어떻게 동작해?"는 사실이 아님)은 건너뛴다.** 원자적 주장 하나에 사실 하나, 턴당 10개 상한. `entity`는 알면 정규 slug(`people/alice-example`, `companies/acme`, `travel`), 아니면 호출자가 정규화할 표시 이름, 의미가 없으면 null. 익명 화자 라벨("Speaker A" 등)의 1인칭 주장은 `entity=null`(이름을 지어내지 말 것), 같은 턴의 3인칭 주장은 실제 엔티티를 쓴다. `confidence`는 "I am" 같은 직접 1인칭 단언이 1.0, 추론·완곡은 낮게. **`notability`가 모델에게 준 "살릴지" 기준이다**: `high`=삶의 사건(이별·사망·출생·입원)·큰 약속("I'm leaving YC")·관계 상태 변화·건강 변화·정서적 돌파·금융 결정(즉시 추출), `medium`=지속적 선호·성격이 드러나는 강한 의견·믿음(배치 처리 가능), `low`=물류적 잡음·식당 주문·일상 일정("we're at X place") — 호출자의 허용 집합에 `low`가 없으면(`high-only` 필터) 프롬프트가 "low는 통째로 건너뛰라"로 바뀌고, 있으면 "정직하게 `low`로 표기하되 저장은 호출자가 결정"이다. 수치 주장(MRR·ARR·team size·fundraise 등)은 `metric`(소문자 snake_case)·`value`(정규화한 숫자)·`unit`(`$`는 USD, 다른 통화는 그대로 보존·환산 금지)·`period`를 추가로 낸다(수치가 아니면 넷 다 null). 변형(기본 켜짐): `extraction.date_grounding`은 관측일을 알려 주고 상대 날짜를 관측일 기준 절대 날짜로 고쳐 쓰게 하며 사실마다 `valid_from`("YYYY-MM-DD" 또는 null)을 내게 한다. `facts.attribution`은 비서가 한 말(추천·답·계획)을 "Assistant recommended …"처럼 별도 사실로 남기고 사용자 수락은 명시적일 때만 별도 사실, 거절·정정된 제안은 사용자 사실이 되지 않게 하며 `attributed_to`(`user`\|`assistant`\|`other`\|null)를 내게 한다. 운영자 `facts.extraction_prompt_appendix`는 그대로 뒤에 붙는다. 사용자 메시지는 `[관측일 줄]\n<turn>\n{정리된 입력}\n</turn>\n\nExtract up to 10 facts.[ Known entity slugs the user already mentioned: <힌트 최대 5개>.] ` 형식이다. 프롬프트 전문은 C-08 (실행 확인: 두 변형의 차이는 low 처리 한 줄뿐) | 코드 확인 + 실행 확인 (T-07) |
| R-22 | 호출 파라미터와 호출 횟수 | `chat({model, system, messages:[user], maxTokens: facts.extraction_max_tokens(기본 4000), responseSchema, cacheSystem:true, abortSignal})`. `responseSchema`는 구조화 출력을 지원하는 openai 호환 레시피에서만 적용되고 나머지 공급자는 무시한다([ai-gateway R-34](./ai-gateway.md)). 호출 횟수: 1회 + `stopReason:'length'`면 **2배 토큰으로 1회 재시도**(또 잘리면 `truncated_output`) + 출력이 파싱되지 않거나 후보가 전부 무효면 "JSON만 반환" 문구를 시스템 프롬프트에 덧붙여 **1회 재시도**(그래도 안 되면 `malformed_output`). 재시도에는 캐시 표시를 안 붙인다. 채팅 폴백 체인이 설정돼 있으면 [ai-gateway R-33](./ai-gateway.md)이 적용된다. 종료 사유가 `refusal`→`refusal`, `content_filter`→`content_filter`, `end`가 아니면 `non_terminal_stop` (C-09) | 코드 확인 |
| R-23 | 출력 검증·거름 (순서) | (1) 파서 사다리 `parseExtractorJson`: 코드펜스 제거 후 JSON 파싱 → 안 되면 `{…"facts"…}` 부분 문자열 스캔 → 안 되면 `<think>` 블록을 제거해 다시. 최상위가 `facts` 배열이 아니면 null. 후보는 객체이고 `fact`·`kind`가 문자열이어야 하며 아니면 무효로 세어 버린다(경고). `confidence`는 숫자 또는 숫자 문자열만, `metric/unit/period`는 문자열, `value`는 유한 숫자만, `valid_from`은 문자열만, `attributed_to`는 세 값만(그 밖은 null). (2) **앞 10개만 본다**(`cap` = min(`maxFactsPerTurn`(어떤 호출자도 안 줌) ?? 10, 25)). (3) 문장: trim 후 비면 버림, 모델이 복사한 `[redacted]` 자리는 원문이 증명할 때 되살림(`restoreNeutralized`), **500자 초과는 497자 + `...`**. (4) `kind`가 6개 밖이면 `fact`(경고). (5) 정크 필터(켜져 있을 때): 계획 서술("Now let me…", "I'll…", "I'm going to…"; `commitment`는 이 규칙에서 면제), 대화 메타 서술("The user is asking…", "Another agent is…"), 공급자 오류문("You've hit your org's monthly spend limit." 형태로 **앵커**됨; 한도를 언급하는 지식 문장은 통과)이면 버림. (5′) 노터빌리티 허용 집합이 있으면 허용 밖·무효 등급 후보는 버림(R-24). (6) 신뢰도: 없거나 NaN → `facts.extraction_missing_confidence`(기본 1.0), 범위 밖은 0..1로 clamp. **신뢰도 최소 임계값은 없다.** (7) `notability`가 세 값이 아니면 `medium`. (8) 임베딩(R-26). (9) 엔티티: 익명 화자 라벨이거나 `null/None/n/a` 등 널 같은 문자열이면 null, 아니면 모델이 준 문자열 그대로(해소는 R-30). (10) `claim_metric`은 소문자 snake_case로 정규화(알려진 라벨은 표로 정규화), 값·단위·기간은 그대로. (11) `valid_from`은 날짜 접지 변형이 켜져 있고 유효한 날짜일 때만 채택(유효하지 않으면 버리고 추측하지 않음). `attributed_to`는 변형이 켜졌을 때만. 개인정보(PII) 필터는 없고, 비밀 패턴 스캔은 캡처 레인이 은행에 넣기 전(R-09~R-11)에만 있다 (C-07, C-09, C-10) | 코드 확인 + 실행 확인 (T-04, T-05, T-06, T-16) |
| R-24 | 호출자별 노터빌리티 허용 집합 | `notabilityFilter`: `all`(기본, 모든 등급 저장; 필터 없이 모델이 low를 정직하게 표기), `high-only`(`high`만, 프롬프트가 low 생략을 지시; **sync**), `medium-and-up`(`high`+`medium`; **Stop 턴 레인이 `salient`일 때**, 설정 `facts.page_write_notability_filter`로 페이지 쓰기에도 고를 수 있음, 기본 `all`). `high-only`는 추출 단계(허용 밖은 임베딩 전에 버림)와 사실 루프에서 한 번 더 적용된다. 잡 페이로드의 알 수 없는 값은 `all`로 강등된다. `extract_facts`·컴팩션·SessionEnd·대화 사실은 `all` (C-02, C-04, C-09) | 코드 확인 + 실행 확인 (T-15) |
| R-25 | 결정적 Stop 게이트 `gateWritebackTurn` | 훅이 은행에 넣기 전, LLM 없이 순서대로(첫 일치 승): 비었음 `empty` → 길이 < 20자(CJK가 있으면 < 10자) `too_short` → 8,000자 초과 `bulk_paste` → 붙여넣은 블록 제거 뒤 사용자 본인 말이 없으면 `pasted_content`(본인 말이 하한 미만이면 `too_short`) → 6단어 이하이면서 전체가 인사·확인 어휘면 `ack_or_greeting` → `/`로 시작 `slash_command` → 모든 문장이 `?`로 끝남 `question_only`(사실이 질문 속에 있는 것은 놓치는 정밀도 우선) → 코드펜스·`>` 인용·4칸 들여쓰기 3줄 이상을 걷어낸 잔여가 하한 미만 `quoted_or_tool_output`. 통과하면 NFC·공백 정규화 텍스트와 그 sha256 앞 24자(멱등 키)를 낸다. 모든 건너뜀은 "설계된 걸러내기"로 하트비트 outcome `ok` (C-15) | 코드 확인 + 실행 확인 (T-01) |
| R-26 | 사실 임베딩 | 걸러진 후보마다 `embedOne(factText, {inputType:'document', embeddingModel})`을 **순차로 1회씩** 부른다([ai-gateway R-20](./ai-gateway.md)). 브레인이 사실 임베딩을 껐으면(`factEmbeddingDisabled`) 부르지 않는다(사실 문장이 공급자에 가지 않음). 호출자가 임베딩 서명을 줬으면 그 모델·차원을 쓴다. `AbortError`와 호출 정책 거부는 다시 던지고, 그 밖의 실패(키 없음·공급자 오류·`embedding_model` 미설정으로 `getEmbeddingModel`이 던진 경우 포함)는 `embedding=null`로 계속한다 — 이때 코사인 중복 제거는 건너뛰고 정확 지문만 본다 (C-09) | 코드 확인 |

**C. 저장 전 중복 제거**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | 추출 뒤 처리 순서 (unmanaged) | (1) 엔티티 없는 사실에 쓰기 시점 주체 추론(R-46). (2) **캡처 레인만**: 정확 지문 중복 제거(R-31)를 사실 루프 앞에서. (3) 사실마다: 노터빌리티가 `high-only`가 아니면 버림 → 엔티티가 있으면 `resolveEntitySlugWithSource`([memory-verbs R-12 해소 체인](./memory-verbs.md), M-01)로 해소하고 **결과 출처가 `fallback_slugify`면 엔티티 없음(null)으로 취급**(`remember`가 폴백 slug를 그대로 쓰는 것과 다르다) → 이 엔티티·가시성의 **철회된 정확 주장이면 건너뜀**(`withdrawn_skipped` 카운트, [memory-verbs R-19](./memory-verbs.md)) → 정확 지문 중복(`decideSingleFact`에 임베딩 null: 같은 소스·같은 엔티티(없음끼리 포함)·같은 가시성·활성·같은 화자 호환의 지문 일치, [memory-verbs R-17](./memory-verbs.md) ①) → 코사인(R-32). 살아남은 사실이 `survived`다. 해소 결과·후보 선택의 세부 규칙(별칭·퍼지·접두 확장)은 M-01이다 (C-04) | 코드 확인 |
| R-31 | 캡처 레인 중복 제거 `dedupCapturedFacts` (`hook:writeback`·`sweep:corpus`·`hook:compact`만) | 후보를 **버리는** 조건(전부 만족): 같은 소스에 **같은 지문**의 활성 사실이 있고, (a) 같은 엔티티(둘 다 없음 포함)이거나 다른 엔티티인데 후보 문장이 그 엔티티 페이지의 제목·별칭을 단어 단위로 포함하고, (b) 보이는 범위가 맞으며(`private` 후보는 world·private과, `world` 후보는 world와만 비교), (c) 원 턴 시각 ±15분 이내이거나 같은 대화(`canonicalConversationKey`)의 캡처 레인 행이고, (d) 화자가 호환. 읽기 상한 50행. 버린 건은 `duplicate`로 세고 기존 id를 `fact_ids`에 넣는다. **코사인 ≥ 0.92이고 부정·숫자·날짜·금액 토큰이 같은 근접 중복은 버리지 않고** 그림자 카운트(`near_duplicate`)만 하트비트에 남긴다. 중복 읽기 실패는 후보를 삽입하고(fail open) 경고한다. 명시적 레인(`remember`·`extract_facts`·sync·페이지 쓰기)은 이 단계를 거치지 않는다. 코드 주석: 읽기 시점에도 같은 지문·엔티티 행을 최신 하나로 접는다(`collapseHotFacts`, 16행) (C-12) | 코드 확인 + 실행 확인 (T-08) |
| R-32 | 코사인 단계 (사실 루프 안) | 조건: 정확 지문이 안 걸렸고, 해소된 엔티티가 있고, 임베딩이 있고, 엔티티가 추론된 것이 아닐 때. 같은 엔티티의 활성 후보 최대 5개(`DEDUP_CANDIDATE_LIMIT`; 임베딩 모델·텍스트 해시·차원이 같은 것만)를 가져와 코사인이 가장 높은 하나를 `cosineVerdict`로 판정한다: 명시적 레인은 그 임베딩 모델의 보정 임계값 이상이면 `duplicate`, 임계값이 null(보정 안 된 모델)이면 **절대 중복으로 판정하지 않는다**([memory-verbs R-17](./memory-verbs.md): `voyage:voyage-4@1024`=0.95, `facts.supersession_thresholds`로 덮어쓰기). 캡처 레인은 코사인으로 **절대 `duplicate`가 아니다**. 중복이면 그 기존 사실 id로 `duplicate`를 세고 쓰지 않는다. 같은 레인·세션·가시성에서 코사인 ≥ 0.85이고 토큰이 안 갈리는 다시 쓴 문장은 `would_dedup_same_page`로 **세기만** 한다(그림자, 삭제 안 함; 코드 주석에 거짓 양성 사례 명시) (C-04, C-12, C-13) | 코드 확인 + 실행 확인 (T-08, T-09) |
| R-33 | 결과 종류와 LLM 분류기 | 이 파이프라인의 결과는 `inserted`·`duplicate` 둘이다. **`superseded`는 항상 0**: 백스톱은 `supersedeId`를 넘기지 않고 `insertFact`는 그때만 `superseded`를 낸다(대체는 `remember`의 `replaces`·코사인 판정과 펜스의 `~~…~~ superseded by #N`, R-18 경로의 몫). `classify.ts`의 LLM 중복/대체 분류기 `classifyAgainstCandidates`(코사인 빠른 경로 → Haiku급 분류 → 실패 시 0.92 폴백)는 **정의만 있고 호출자가 없다**(테스트만 사용). 따라서 이 파이프라인에서 중복 판정에 LLM을 쓰지 않는다 (C-04, C-13) | 코드 확인 (호출자 grep 전수) |

**D. 저장**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 저장 대상 결정 | 살아남은 사실을 해소된 엔티티 slug로 묶는다(엔티티 없음은 "무소속" 묶음). 소스의 `sources.local_path`가 없거나(`new init` 직후 기본), `sync.write_through`가 꺼졌거나, gbrain이 소유한 URL 클론이면 **전부 DB 전용**(`insertFact`, `row_num` NULL, 첫 번째면 소스당 1회 stderr 경고). 파일 루트가 있으면 무소속 묶음만 DB 전용, 엔티티 묶음은 펜스 쓰기(R-42). 마크다운 펜스와 페이지는 엔티티가 해소되고 파일 루트가 있을 때만 건드린다(페이지는 이미 있거나 "검증된" 엔티티일 때 스텁으로 만든다). `extract_facts`·sweep 등 어느 경로도 저널(`persistence_requests`) 접수를 거치지 않는다 — `remember`와 다른 점이다([memory-verbs R-26](./memory-verbs.md)) (C-04, C-25) | 코드 확인 |
| R-41 | DB 전용 행의 값 | `fact`, `kind`, `entity_slug`(해소 성공 시, 아니면 null), `visibility`(R-43), `notability`, `source`=경로 라벨(1.3 표), `source_session`=세션 id, `confidence`, 임베딩·모델, 타입 클레임, `attributed_to`, `valid_from` = 모델이 말한 날짜 > 호출자의 `validFrom` > 원 턴 시각(`turnAt`, 코퍼스 파일의 쓰기 시각) > 삽입 시각, `context` = `source_slug`(없으면 페이지 slug) + 주석("entity matched by bare name only (prefix expansion) — unverified, please confirm" 또는 "entity inferred from page\|mention"). 삽입은 `(source,entity)` 어드바이저리 락 아래 INSERT 한 건이고 락 안에서 중복을 다시 보지 않는다(동시 호출 사이에는 중복이 생길 수 있음, 추론). 활성 정의는 `expired_at IS NULL`([engine-and-schema](./engine-and-schema.md)) (C-04, C-26, C-28) | 코드 확인 / 동시성 결과는 추론 |
| R-42 | 펜스 쓰기 `writeFactsToFence` (파일 루트가 있을 때) | 페이지 파일 락(FS 락, 5초 대기)과 소스 파일시스템 락 아래: 철회된 주장 재확인 → 파일이 있으면 읽어 펜스 파싱 경고가 있으면 **거절**(행을 잃지 않으려고, `fence_refusal`) → DB 본문과 파일이 다르면(drift) 건드리지 않고 DB 전용으로 폴백 → 파일이 없으면 스텁 생성: 슬러그에 `/`가 없거나 해소 출처가 `fallback_slugify`/null이면 **스텁 금지**(DB 전용으로 폴백, 유령 엔티티 페이지 방지)이고, 페이지가 DB에만 있거나 삭제됐으면 스텁이 덮어쓰지 않도록 DB 전용 → `row_num = max(펜스 최대, DB의 같은 페이지 최대) + 1`부터 추가 전용으로 행 추가([memory-verbs R-15](./memory-verbs.md) 형식) → `<파일>.tmp`에 쓰고 **다시 파싱해 검증**(실패하면 .tmp를 격리용으로 남기고 DB에 안 넣음, `facts.write_failures.jsonl` 기록) → 한 DB 트랜잭션에서 페이지 본문 미러와 `insertFacts`(청크 500, `(source_id,source_markdown_slug,row_num)` 충돌 무시) 후 파일 `rename` → git 내구성이 켜졌으면 그 파일만 커밋(재시도 0·50·200ms). 페이지 저널·`putPage`를 거치지 않으므로 이 쓰기가 다시 추출을 부르지 않는다(재귀 없음) (C-25) | 코드 확인 |
| R-43 | 가시성 | 우선순위: 호출자 인자(`world`/`private`) > `facts.default_visibility` > **`private`**(미설정·읽기 실패·`world` 아닌 값은 모두 `private`, 대소문자·공백 무시). 페이지에서 나온 사실은 그 페이지보다 넓어지지 않는다(`tightenToPage` → `isDerivationPrivate`: frontmatter에 `pinned_question`이 있거나, `visibility`가 명시적 `private`이거나, `visibility`가 없고 타입이 `atom`·`question`이거나 `synthesized_by`가 있는 `concept`(파생 페이지 기본 비공개)이거나, 프라이버시 별칭 `access ∈ {private, restricted, confidential}`·`confidentiality ∈ {confidential, secret, private, restricted}`(공백 제거·소문자)를 가지면 `private`. 별칭은 `visibility`가 명시돼 있어도 적용되고, `isPrivatePage` 쪽 별칭 판정만 `visibility.honor_aliases` 설정의 영향을 받는다). 페이지 쓰기(③)는 effect 큐잉 시점의 기본값을 잡 페이로드에 고정한다. **`remember`의 기본(`world`)과 다르다.** 그래서 서버 추출 사실은 기본 설치에서 로컬 CLI만 읽을 수 있고 원격(MCP) 호출자는 못 본다([memory-verbs R-20·R-48](./memory-verbs.md)). 지시문은 반대로 미설정을 `world`로 안내한다(R-17) (C-28) | 코드 확인 + 실행 확인 (T-11) |
| R-44 | 신뢰 등급과 쓰기 게이트 (경계) | 추출 사실의 등급은 "파생 쓰기": `agent_written`을 상한으로, 입력으로 읽은 페이지 행의 등급과 호출자의 `content_origin`이 더 낮으면 그 등급으로 내려간다(채널 라벨 `derive:facts_backstop` 또는 `derive:extract_facts`). 행마다 쓰기 게이트(`decideFactWrite`)를 통과한다: 등급이 `agent_written`·`unknown`이면 `agent_mode`(`flag`\|`off`, 기본 `flag`)라 저장은 막히지 않고 의심 패턴이 검출되면 `flag` 영수증만 남는다. 입력 등급이 낮아 사실이 `external_untrusted`가 된 경우에만 `external_mode`(`quarantine`\|`flag`\|`reject`\|`off`, 기본 `flag`)가 `quarantine`·`reject`일 때 보류·거절된다(unmanaged 경로에서 막힌 행은 펜스에도 폴백 DB 행에도 안 감). 모델이 `[redacted]`를 낸 행은 원문 텍스트도 게이트에 보인다. 규칙 본문은 13행 (C-05, C-33) | 코드 확인 (기본값·분기만) |
| R-45 | managed 분기 (경계) | 브레인이 managed(`persistence_brain.enabled`)면 같은 추출·중복 제거 입력으로 `publishManagedFacts`가 내구성 영수증으로 발행한다(펜스 쓰기도 코디네이터의 사실 의도로 대체). 페이지 경로는 인프로세스 큐가 아니라 발행 아웃박스를 써야 해서 `queue` 모드로 부르면 `writer_coordinator_required`를 던진다. 본문은 범위 밖 | 코드 확인 (분기 존재만) |
| R-46 | 쓰기 시점 주체 추론 | `facts.entity_inference`가 꺼지지 않았고 사실의 엔티티가 비었을 때, **펜스에 올릴 수 있는 브레인에서만**(`local_path`가 있고 쓰기 통과가 켜진 경우) 증거로 증명되는 주체를 붙이고 `entity_inferred`(`page`: 지금 쓰는 엔티티 페이지가 주체이고 본문이 다른 엔티티를 안 부름, `mention`: 본문이 살아 있는 사실 엔티티 페이지 하나만 정확 slug·유일 basename·유일 별칭으로 부름)를 표시해 컨텍스트에 "entity inferred from …"를 남긴다. 추론된 사실은 코사인으로 버려지거나 대체되지 않는다(R-32). 모델이 이미 엔티티 이름을 줬으면(페이지가 없어도) 추론이 덮어쓰지 않는다. **기본 설치(파일 루트 없음)에서는 추론하지 않는다.** 판정 함수 본문은 `inferFactSubject`(`remember`와 공유)이고 M-01의 이웃 규칙이다 (C-04) | 코드 확인 |

**E. 실패 처리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | LLM 키가 없음 | `isAvailable('chat', model)`가 거짓이면 `chat_unavailable`. 분류: 해소된 모델의 공급자 키도 없고 채팅 가능한 어떤 공급자 키도 없으면 **keyless**(기대되는 상태): 프로세스당 한 줄 stderr 안내(`[facts] keyless: automatic fact extraction off — …`)만 하고 `ingest_log` 행을 쓰지 않는다. 키가 있는데 실패하면 **keyed**: `ingest_log`에 `facts:absorb` 행과 프로세스당 한 번의 수정 안내(`facts.extraction_model` 또는 키 설정). 설정 파일이 있는데 못 읽으면 keyless가 아니라 keyed로 분류해 재시도되게 한다. 경로별 결과: `extract_facts` → `extraction_unavailable`+`agent_action`(R-03), 페이지 잡 → 키 없는 워커는 30분 뒤 재시도(R-08), sweep → 패스 전체 `keyless` 건너뜀(캡처 retire는 먼저), 하베스트 → 사이드카 없이 `keyless`, 훅은 애초에 LLM을 안 부름 (C-05, C-19, C-24) | 코드 확인 |
| R-51 | 호출·파싱 실패의 전파 | `extractFactsFromTurnWithOutcome`은 실패를 값으로 돌려준다: `chat_unavailable`, `provider_error`, `refusal`, `content_filter`, `non_terminal_stop`, `malformed_output`, `truncated_output`. 파이프라인은 `provider_error`와 `truncated_output`을 **`FactsExtractionError`로 던진다**(메시지는 이유·모델·정제된 원인 라벨만, 공급자 본문·키는 안 담음): 인프로세스 큐의 catch가 `ingest_log`에 정밀 코드로 기록, 잡은 재시도·백오프, `extract_facts`는 오류로 보인다. 나머지는 0 카운트에 `skipped_reason`을 달아 돌려주고(keyless면 조용히, keyed면 로그 한 줄) 호출자가 정한다: sweep은 마지막 시도이므로 사이드카에 `skipped` 사유를 적어 종결, 하베스트는 사이드카를 쓰지 않아 sweep이 한 번 더 시도한다. 파싱 실패는 R-22의 재시도 1회 뒤에도 안 되면 `malformed_output`이고 일부 후보만 무효면 나머지를 쓴다 (C-05, C-09, C-19) | 코드 확인 + 실행 확인 (T-05) |
| R-52 | 예산 | 추출은 앰비언트 `BudgetTracker`가 없으면 **상한 없는 기록 전용 추적기**(라벨 `facts:<source>`)를 건다(어떤 상한도 `BudgetExhausted`를 던지지 못하고 감사 행만 남음, [ai-gateway R-61·R-68](./ai-gateway.md)). 앰비언트 추적기가 있으면 그것을 쓴다: PGLite 드레인(실행당·일일 USD 상한)과 `extract-conversation-facts`(`--max-cost-usd`)에서는 `reserve`가 `BudgetExhausted`를 던져 호출 자체가 일어나지 않는다. 드레인은 잡을 시도 횟수 없이 대기로 두고(`budget_exhausted`/`daily_budget_exhausted`/`no_pricing`), 한 페이지 최대 비용이 실행당 상한보다 크면 `job_over_budget`으로 시작하지 않는다. 단가 없는 모델은 기본 상한이면 경고 후 진행, 사용자가 상한을 정했으면 거절. 대화 추출은 `BudgetExhausted`를 감싸지 않고 다시 던져 실행을 영수증과 함께 멈춘다 (C-03, C-21, C-30) | 코드 확인 |
| R-53 | 동시·중복 호출과 멱등 | (1) 페이지 쓰기: 잡 멱등 키 `facts-absorb:write:<request_id>`, revision이 바뀌면 `superseded`; sync: 키에 본문 해시. (2) 인프로세스 큐: 세션당 동시 1, 최대 100(초과 시 가장 오래된 것 폐기). (3) 코퍼스: `.in-progress` 클레임(O_EXCL, 60분 stale)과 성공 뒤에만 쓰는 `.ingested`로 같은 파일을 두 프로세스가 중복 과금하지 않음, 클레임 아래에서 완료 재확인. (4) Stop 턴 파일 이름이 정규화한 턴의 해시라 같은 턴은 한 파일. (5) 펜스: 페이지 락, `row_num` 충돌 무시. (6) 사실 INSERT 자체는 락 안 재판정이 없다(R-41). 추출 입력 워터마크: 페이지의 `compiled_truth`가 8,000자를 넘으면 마지막 성공 추출 이후 덧붙은 꼬리만(워터마크: 바이트 위치+앞부분 sha256+파이프라인 버전) 읽고, 접두가 바뀌었거나 워터마크가 없으면 앞 8,000자를 읽고 `input_truncated` 영수증을 `page_extraction_state`에 남기며, 성공해야 워터마크를 갱신한다 (C-03, C-18, C-20, C-24, C-29) | 코드 확인 + 실행 확인 (T-12) |
| R-54 | 훅의 fail-open | `gbrain hook`의 모든 이벤트는 런타임 실패에도 종료 코드 0과 빈 stdout으로 끝나고 하트비트 JSONL(개수·시간·오류 코드만, 프롬프트·사실·slug 텍스트 없음)에 기록한다. `GBRAIN_HOOKS=0`이면 하트비트 없이 즉시 0. 엔진을 열지 않고(PGLite 단일 작성자 락), 단계마다 자체 마감(Stop 2,000ms, PreCompact 3,000ms)이 있으며 마감·IPC 실패는 `degraded`로 기록되고 은행에 쌓은 파일이 내구성 있는 산출물이라 sweep이 나중에 추출한다. 알 수 없는 이벤트만 1을 낸다 (C-22) | 코드 확인 |
| R-55 | `off`·킬 스위치와 이미 진행 중인 일 | `memory.auto_writeback off`는 이후 admit되는 모든 캡처 레인 요청을 막는다(R-12). 이미 저장된 사실, 명시적 `remember`·`extract_facts`, 의도적으로 쓴 페이지의 추출은 멈추지 않는다. 오래된 워커(재시작 전 serve, cron sweep, OpenClaw 게이트웨이)는 재시작해야 `off`를 존중한다고 `config set`이 경고한다 (C-14, C-17) | 코드 확인 |

**F. 비용 통제**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 어떤 호출이 LLM을 부르고 언제 건너뛰나 | LLM 호출 단위: 추출 호출 1회(+R-22 재시도) + 사실마다 임베딩 1회. 훅·게이트·적격성·중복 제거(정확/코사인)·펜스 투영·사이클 `extract_facts` phase는 **채팅 호출 0회**다. 건너뛰는 조건: 빈 입력, dream 산출물, `is_dream_generated`, 페이지 적격 실패(타입·80자 미만·`facts_backstop: off`·격리·`wiki/agents/`), `body_unchanged`, 사실 추출 꺼짐, 키 없음, Stop 게이트(R-25), 같은 턴 해시(`wb_dup`), 캡처 게이트 retire·hold, 파일의 `.ingested`·`self_capture`, 세션당 하베스트 30회, 대화 창 최소 메시지 2개, 이미 완료한 대화 페이지의 터미널 감사 행. 입력 크기 상한은 8,000자(R-20) | 코드 확인 |
| R-61 | 수치 상한 모음 | 후보 10개/호출, 사실 500자, 입력 8,000자, 출력 토큰 4,000(잘리면 8,000으로 1회), 엔티티 힌트 5개, 인프로세스 큐 100·세션당 동시 1, 하베스트 큐 8·작업당 60초·Stop 턴 세션당 30, sweep 파일당 창 8·전체 32·`batchLimit` 20, 드레인 실행당 $1·일일 $5·잡 50·벽시계 5분·틱 10분(최대 간격 30분), 대화 배치 기본 $5·창당 30메시지·6,500자·30분 간격, 사이클 backfill 소스당 $1·전체 $5·20/30분, 캡처 중복 창 15분·근접 0.92·그림자 0.85, 명시적 코사인 임계값은 모델별(R-32) | 코드 확인 + 실행 확인 (T-14) |

- 불변식: (1) 서버 추출은 호출자에게 보이는 `extract_facts`를 제외하면 에이전트의 도구 호출 없이도 일어나지만, 어느 경로도 `facts.extraction_enabled`가 꺼져 있으면(명시적 우회 `--override-disabled` 제외) 새 추출 호출을 하지 않는다. (2) 캡처 레인의 사실은 항상 `source`가 `hook:writeback`·`hook:compact`·`sweep:corpus` 중 하나이고 발행 직전 게이트를 다시 통과해야 한다. (3) 서버 추출 행의 `trust_tier`는 `agent_written` 이하다. (4) 추출은 저장된 페이지·사실 텍스트를 프롬프트에서만 무력화하고 저장 문장은 원문 기준이다. (5) 백스톱 결과의 `superseded`는 0이다.
- 미결정:
  - 이 스펙 자체의 미결정은 없다.
  - 선행 스펙 [memory-verbs](./memory-verbs.md)의 M-01(엔티티 이름 해소)은 R-50~R-59로 해소됐다(2026-10-24). R-30의 출처 5종(`exact_page`·`alias_exact`·`prefix_expansion`·`fuzzy_match`·`fallback_slugify`)은 그 R-ID의 값과 같다.
- 확인 한계:
  - `bun`이 없고 LLM·임베딩·DB를 호출하지 않아 추출 파이프라인 전체(`runFactsPipeline`)·잡·훅 프로세스·IPC·sweep·드레인을 끝까지 실행하지 못했다. 실행 확인은 deno로 순수 함수와 줄 범위 발췌만이다(`agent-memory/artifacts/gbrain/fact-extraction-demos/`). 후보 처리 루프(R-23의 (3)~(11) 중 문장 절단·kind 폴백·`embedOne` 호출·`valid_from` 채택)는 코드를 읽었을 뿐 실행하지 못했다.
  - SQL(`gbrain_fact_fingerprint`, `findCandidateDuplicates`, 펜스 투영 SQL, `facts_guard_inserted` 트리거)은 실행하지 않았다.
  - 모델이 실제로 이 프롬프트에 어떤 사실을 뽑아 주는지(품질)는 확인하지 못했다. 코드 주석이 가리키는 측정(Haiku 5.5 기본값, 날짜 접지·화자 귀속 변형의 평가)은 `gbrain-evals` 문서의 주장이라 **미확인**이다.
  - `dream`/autopilot 스케줄러가 기본으로 도는지, OpenClaw rung 3 본문, 대화 파서·클레임·영수증 내부, `facts relink`는 읽지 않았다.
  - 이 스펙은 훅이 설치된 상태의 동작을 하네스 설치 절차(`gbrain bootstrap`)와 분리해 기술했다. 기본 `gbrain init`이 훅을 설치하는지는 `init`이 하네스 등록 명령만 안내한다는 것까지만 확인했다(`init.ts` 1304-1340).

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 인용 가능. 줄 번호는 기준 SHA.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/ops/facts.ts:60-208` `extract_facts` | 도구 정의(파라미터·설명)·킬 스위치·dream 방어·가시성 결정·봉투 | R-02, R-03 |
| C-02 | `src/core/facts/backstop.ts:88-192, 348-522` `FactsBackstopCtx`, `runFactsBackstop` | 컨텍스트 필드·결과 형태·게이트 순서·`queue`/`inline` 분기·잡 제출 페이로드 | R-01, R-07, R-24 |
| C-03 | `src/core/facts/backstop.ts:541-578, 589-620, 649-673` `runFactsPipeline`, `runPipeline`, `runPipelineWithBody` | 텍스트 입구·페이지 워터마크 계획·기록 전용 추적기 | R-01, R-52, R-53 |
| C-04 | `src/core/facts/backstop.ts:720-1077` `runPipelineBodyInner` | 추출 → 주체 추론 → 캡처 중복 → 사실 루프(철회·정확·코사인) → 묶음·DB 전용·펜스 쓰기·폴백 | R-24, R-30~R-33, R-40, R-41, R-46 |
| C-05 | `src/core/facts/backstop.ts:219, 235-243, 256-338, 689-717` | 파생 신뢰, keyless 안내문·분류, 실패 노출, 게이트 writer | R-44, R-50, R-51 |
| C-06 | `src/core/facts/extract.ts:50-133, 143-176` | 킬 스위치·모델 해소·측정 기본값·토큰 상한·프롬프트 덧붙임·변형 읽기 | R-04, R-20, R-21 |
| C-07 | `src/core/facts/extract.ts:193-248, 337-358` | 정크 정규식 3종과 `isJunkFact`, 누락 신뢰도 읽기, 익명 화자 패턴 | R-23 |
| C-08 | `src/core/facts/extract.ts:360-455, 458, 474-519` | 시스템 프롬프트 전문(`renderExtractorSystem`, 날짜·화자 블록)과 응답 스키마 | R-21 |
| C-09 | `src/core/facts/extract.ts:605-879` `extractFactsFromTurnWithOutcome` | 호출 순서·재시도·실패 값·후보 루프·임베딩 | R-20, R-22, R-23, R-26, R-51 |
| C-10 | `src/core/facts/extract.ts:908-1022` | 파서 사다리와 후보 검증, `clampConfidence` | R-23 |
| C-11 | `src/core/facts/eligibility.ts:56-127` | 페이지 적격성 | R-06 |
| C-12 | `src/core/facts/capture-dedup.ts:34-122, 124-251` | 캡처 레인 상수, 지문 중복 규칙, 근접·그림자 규칙, `cosineVerdict`, `claimsDiverge` | R-31, R-32 |
| C-13 | `src/core/facts/single-prepare.ts:104-135`; `src/core/facts/supersession-threshold.ts:19-72`; `src/core/facts/classify.ts:51-64, 75-239` | `decideSingleFact`(정확 지문 + 코사인), 모델별 임계값, `cosineSimilarity`, 호출되지 않는 LLM 분류기 | R-30, R-32, R-33 ([memory-verbs C-15](./memory-verbs.md)와 같은 코드) |
| C-14 | `src/core/facts/writeback-config.ts:54-61, 195-277, 311-329` | 설정 키·평면 해소·레인 결정 표·`off`/미설정 안내 | R-12, R-55 |
| C-15 | `src/core/facts/writeback-gate.ts:27-147` | Stop 게이트 규칙·상수·해시 | R-09, R-25 |
| C-16 | `src/core/facts/writeback-instructions.ts:37-66` | 자동 저장 지시문 11줄 | R-17 |
| C-17 | `src/core/facts/capture-sources.ts:15-55`; `src/core/context/capture-consent.ts:1-60, 105-160`; `src/core/context/corpus-segments.ts:446-456, 500-527` | 출처 라벨 목록, 발행 직전 게이트, 캡처 시점 off 기록, 코퍼스 파일 이름·은행 | R-09, R-12 |
| C-18 | `src/core/persistence/effect-facts.ts:20-157`; `src/core/persistence/effect-journal.ts:50-55`; `src/core/persistence/page-advisories.ts:99-110` | 페이지 쓰기 → `facts-backstop` effect → `facts-absorb` 잡 | R-04, R-05, R-53 |
| C-19 | `src/core/minions/handlers/facts-absorb.ts:14-135`; `src/core/minions/llm-halt-cooldown.ts:1-40`; `src/core/facts/absorb-log.ts:40-98` | 잡 핸들러·키 없음/연기·재시도·공급자 중단 쿨다운·로그 사유 | R-08, R-50, R-51 |
| C-20 | `src/commands/sync/finalize.ts:598-641`; `src/core/facts/queue.ts:54-111`; `src/core/facts/cli-process-mode.ts:1-35` | sync 사후 백스톱, 인프로세스 큐, 한 번 쓰고 끝나는 CLI 표시 | R-07, R-53 |
| C-21 | `src/core/facts/drain-config.ts:3-26`; `src/core/facts/drain.ts:1-60, 204-410`; `src/core/facts/drain-scheduler.ts:16-17`; `src/commands/serve.ts:574-598`; `src/core/cycle/facts-drain.ts:1-54` | PGLite 자동 드레인(키·기본값·예산·연기 사유)과 호출 위치 | R-08, R-52, R-61 |
| C-22 | `src/commands/hook.ts:1-37, 130-143, 1291-1441, 1443-1612, 1615-1932` | 훅 이벤트·fail-open·마감·Stop/compact/session-end 처리 | R-09~R-11, R-54 |
| C-23 | `src/mcp/context-pack-handler.ts:145-190`; `src/core/context/checkpoint-harvest.ts:100-170, 541-650` | 하베스트 스케줄링·큐 상한·세션 상한·레인별 실행 | R-10, R-14 |
| C-24 | `src/core/sweep.ts:728-1010, 1105-1160, 1153-1155`; `src/core/context/corpus-windows.ts:45-49`; `src/commands/serve.ts:71-75, 832-892`; `src/mcp/server.ts:546-556` | 코퍼스 패스 순서·클레임·창 한도·실행 주기 | R-13, R-53 |
| C-25 | `src/core/facts/fence-write.ts:324-623, 651-663` | 펜스 쓰기(락·스텁 가드·drift·행 번호·tmp 검증·트랜잭션·git) | R-40, R-42 |
| C-26 | `src/core/engine-sql/facts.ts:81-199, 572-618` | `insertFact`(`supersedeId` 유무)와 `findCandidateDuplicates` | R-33, R-41 |
| C-27 | `src/core/facts/extract-from-fence.ts:55-282`; `src/core/persistence/canonical-projections.ts:533-600, 660-668` | 펜스 행 → `facts` 행 변환과 발행 트랜잭션의 투영 | R-18 |
| C-28 | `src/core/facts/visibility.ts:36-75`; `src/core/search/private-visibility.ts:135-162, 191-194, 255-262`; `src/core/facts/event-time.ts:1-12` | 기본 가시성, 인자 해소, 페이지 상한(비공개 판정과 프라이버시 별칭 표), `valid_from` 우선순위 | R-41, R-43 |
| C-29 | `src/core/extraction-watermark.ts:89-108` `planExtraction` | 페이지 꼬리 워터마크 계획 | R-53 |
| C-30 | `src/commands/extract-conversation-facts.ts:140-200, 1005-1140, 1224-1260, 1673-1760`; `src/core/facts/conversation-windows.ts:20-80`; `src/core/facts/conversation-types.ts:1-143`; `src/core/facts/conversation-budget.ts`; `src/core/cycle/conversation-facts-backfill.ts:1-60` | 대화 사실 배치 명령·창 분할·적격 타입·비용 상한 | R-16, R-52 |
| C-31 | `src/core/cycle/extract-facts.ts:1-60`; `src/core/cycle.ts:140-146, 2866-2900` | 사이클 `extract_facts` phase(펜스 → DB 동기화)와 phase 배치 | R-15, R-18 |
| C-32 | `src/core/think/sanitize.ts:25-72, 76-130`; `src/core/ai/date-grounding.ts:97-109` | 프롬프트 주입 무력화 패턴·복원, 상대 날짜 규칙 문구 | R-20, R-21 |
| C-33 | `src/core/trust/taint.ts:86-97`; `src/core/trust/derived-gate.ts:1-60`; `src/core/write-gate.ts:51` | 파생 쓰기 등급과 쓰기 게이트 기본 모드 | R-44 |

### 1.6 수락 사례

출처: 사례별 표기. "실행"은 `agent-memory/artifacts/gbrain/fact-extraction-demos/demo-pure.mts` 출력(`demo-pure.out.2026-10-24.json`)에서 관찰했고, "도출"은 코드에서 도출했으며 실행하지 않았다(LLM·DB·훅 필요).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-25 | `gateWritebackTurn`: `Thanks!` / `okay sounds good thanks so much` / `/compact please summarize…` / `Where should I put the config file? And how do I reload it?` / 그것에 `I moved to Berlin last month.`를 앞에 붙인 것 / 코드펜스만 / `> `로 인용만 / `x ` 4,100번 / `I'm leaving YC next month and I gave up alcohol.` / CJK 12자·6자 | `too_short` / `ack_or_greeting` / `slash_command` / `question_only` / `ok`(사실이 섞이면 통과) / `quoted_or_tool_output` / `quoted_or_tool_output` / `bulk_paste` / `ok` / `ok`·`too_short`. 공백만 다른 같은 턴은 같은 `hash24` | 실행 |
| T-02 | R-12 | DB·파일 평면 조합에 `resolveWritebackConfig({gate:true})`와 `captureGateDecision` | 미설정: Stop `retire`·컴팩션 `extract`·SessionEnd `extract`. `off`: 셋 다 `retire`. `salient`/`all`: 셋 다 `extract`. 미인식 값 `hold`. DB 없음+파일 `salient` `hold`(drift). DB 없음+파일 `off`: `retire`/`hold`/`hold`. 읽기 실패 `hold` | 실행 |
| T-03 | R-06 | `isFactsBackstopEligible`: `note` 100자 / 79자 / 80자 / `concept` / `code` / `conversation` 타입 / `concept` 타입이지만 `meetings/…` 슬러그 / `dream_generated` / `facts_backstop: off` / `wiki/agents/x` / 격리 / null | ok / `too_short` / ok / `kind:concept` / `kind:code` / `conversation_pipeline` / ok(구제) / `dream_generated` / `opted_out` / `subagent_namespace` / `quarantined` / `no_parsed_page` | 실행 |
| T-04 | R-23 | `isJunkFact`: `Now let me write an oracle…` / `I'll send the deck by Friday`(kind `commitment` vs `fact`) / `The user is asking about pricing` / `You've hit your org's monthly spend limit.` / `Alice wants a monthly spend limit of $200` / `Bob's API rate limit exceeded 1000 rpm` / `Another agent is concurrently rewriting src/a.ts` / 공백 | junk / not junk vs junk / junk / junk / not junk / not junk / junk / junk. 익명 화자: `Speaker A`·`speaker_00`·`**Participant 2:**`·`spk_0`·`Unknown`·`Guest`는 true, `Speaker Pelosi`·`Speaker Deck`·`alice`는 false | 실행 |
| T-05 | R-23, R-51 | `parseExtractorJson`: 정상 / 코드펜스 / 산문 사이 JSON / `<think>` 앞 / `no facts here` / `{"facts":[]}` / 후보 4개(`fact`만, `kind`만, 숫자 5, `kind:"weird"`+`confidence:"0.3"`+`value:"x"`+`attributed_to:"robot"`) | 후보 1개 / 1 / 1 / 1 / null / `[]` / 유효 1개(`kind:"weird"` 유지, 신뢰도 0.3, `value` null, `attributed_to` null)와 무효 3 | 실행 |
| T-06 | R-23 | `clampConfidence`: undefined·NaN·-0.5·1.7·0.42, 누락 기본 1과 0.6 | 1, 1, 0, 1, 0.42 / 0.6 | 실행 |
| T-07 | R-21 | `buildExtractorSystem(true)` vs `(false)` | 차이는 low 처리 줄 하나뿐: `Label honestly — still emit the fact with notability "low"; the caller decides storage.` vs `Skip entirely — not worth storing.`. 날짜·화자 변형을 켜면 각 블록이 끝에 붙는다 | 실행 |
| T-08 | R-31, R-32 | `cosineVerdict`: 명시적(임계값 0.95) 0.96 / 0.94 / 0.999+임계값 null; 캡처 레인 0.999(같은 주장) / 0.93 / 0.95인데 숫자 12 vs 15 / 0.9. `claimsDiverge` | `duplicate` / `distinct` / `distinct`; `near_duplicate` / `near_duplicate` / `distinct` / `distinct`(캡처 레인은 `duplicate`가 나오지 않음). `claimsDiverge`: 부정·숫자·요일은 true, `Lisbon`→`Porto`는 false(그래서 근접 중복도 삭제하지 않음) | 실행 |
| T-09 | R-32 | `resolveSupersessionThreshold`: `voyage:voyage-4`@1024 / `openai:text-embedding-3-large`@1536 / 덮어쓰기 0.97 / `"off"` / 잘못된 덮어쓰기 | 0.95(calibrated) / null(uncalibrated) / 0.97 / null / 유효한 값만 남음 | 실행 |
| T-10 | R-18 | 펜스 5행(활성 선호, `~~Lives in Tokyo~~`+`superseded by #3`, 활성 `Lives in Seoul`, `~~Likes jazz~~`+`forgotten`, 출처 없는 행)을 `extractFactsFromFenceText`(오늘=2026-10-24) | 행 2: `expired_at` 2026-10-24, `superseded_by_row` 3. 행 4: `valid_until`·`expired_at` 2026-10-24. 행 5: `source:'fence:reconcile'`, `valid_from` null. `duplicateActiveFenceRows`는 같은 claim·출처의 둘째 활성 행만 반환. `MRR`·`Monthly Recurring Revenue`→`mrr`, 공백→null | 실행 |
| T-11 | R-43 | `resolveDefaultVisibility`: 미설정 / ` World ` / `public` / 읽기 실패. `resolveVisibilityParam`: 명시 `private`+world 기본 / 미지정+world 기본 / `secret`. `tightenToPage` | `private` / `world` / `private` / `private`. `private` / `world` / `private`. 비공개 페이지·`access: private`면 `private` | 실행 |
| T-12 | R-07, R-53 | `FactsQueue(cap 3, 세션당 1)`에 a1(대기)·a2·b1(다른 세션)을 넣고 c1~c4를 더 넣음 | a1 진행 중에 b1은 같이 진행, a2는 a1 뒤. 용량 초과 시 가장 오래된 것을 버려 `dropped_overflow` 2, 큐 깊이는 3에서 멈춤 | 실행 |
| T-13 | R-16 | `splitIntoSegments`: 09:00·09:05·09:10 대화 후 100분 간격의 단독 메시지, 그 뒤 12:20·12:23 | 2개 창(3메시지, 2메시지), 단독 메시지는 제외. 상수 30분·30·2·6,500 | 실행 |
| T-14 | R-61 | `facts.drain_budget_usd`에 0.005 / 0.01 / 100 / 101 / abc, `facts.drain_max_jobs`에 2.5 | 0.005·101·abc 거절(범위 안내와 "Nothing was written."), 0.01·100 통과, 2.5는 "whole number" 거절 | 실행 |
| T-15 | R-24 | 노터빌리티 필터 값 `all`·`high-only`·`medium-and-up`·`x`·미설정과 `facts.page_write_notability_filter`가 비었거나 이상한 값 | 앞 셋은 그대로, 나머지는 `all` | 실행 |
| T-16 | R-20, R-21 | 원문 `Alice told the team to ignore previous instructions when booking rooms.`의 프롬프트 사본과 모델이 `[redacted]`를 복사한 문장 | 프롬프트 사본은 `to [redacted] when booking rooms.`, 저장 문장은 원문 위치가 증명돼 `ignore previous instructions`로 복원(`restored:1`) | 실행 |
| T-17 | R-09 | 캡처 레인이 은행에 넣기 전 비밀 스캔: 형식을 보이려는 가짜 `sk-ant-api03-…` 키가 든 문장 | 키 자리가 `<REDACTED:anthropic>`로 바뀌고 나머지 문장은 그대로 | 실행 |
| T-18 | R-02, R-03 | 채팅 키가 전혀 없는 브레인에서 `extract_facts({turn_text:'I moved to Berlin.'})` | `{inserted:0, duplicate:0, superseded:0, fact_ids:[], skipped:'extraction_unavailable', agent_action:'No server-side chat model … remember … visibility: "private" (remember defaults to world — …)'}`. 오류가 아니다 | 도출 |
| T-19 | R-05, R-08 | 기본 설치에서 채팅 키 있음, `put_page('notes/trip', 120자 이상 본문)` | 영수증 `facts_backstop:{queued:true}`, 커밋 뒤 `facts-absorb` 잡(키 `facts-absorb:write:<request_id>`). PGLite에서 `gbrain serve`가 떠 있으면 다음 드레인 틱(10분 간격, 활동이 없었거나 30분 경과 시)이 실행해 사실이 `facts`에 `source:'mcp:put_page'`, `visibility:'private'`, `row_num` NULL로 들어간다(파일 루트 없음). 같은 본문(`compiled_truth` 불변)에 태그만 바꿔 다시 쓰면 `skipped:'body_unchanged'` | 도출 |
| T-20 | R-07 | 페이지 51개를 건드린 `gbrain sync` | 사실 추출 백스톱은 호출되지 않는다(링크·타임라인 추출은 별도). 페이지 50개면 페이지마다 `sync:import`·`high-only`로 큐잉 | 도출 |
| T-21 | R-31 | 캡처 레인이 같은 대화에서 이미 `Prefers async over meetings`(엔티티 alice, 활성)를 저장했는데 컴팩션 레인이 같은 문장을 다시 뽑음 | 후보는 삽입되지 않고 `duplicate:1`, `fact_ids`에 기존 id, 콘솔에 `capture dedup: lane=hook:compact dropped a duplicate of fact #N (rule=same_entity)`. 코사인 0.96인 다른 표현은 삽입되고 그림자 카운트만 늘 수 있다 | 도출 |
| T-22 | R-30, R-40, R-42 | 파일 루트가 있는 소스에서 `entity`가 `people/nobody`(페이지 없음, 해소 `fallback_slugify`)인 사실 | 엔티티 null로 취급돼 무소속 묶음 → DB 전용 행(엔티티 없이). 펜스·스텁 페이지는 만들어지지 않는다. 해소가 `exact_page`(예: `people/alice`)이고 파일이 있으면 펜스에 새 행이 붙고 DB 행의 `row_num`·`source_markdown_slug`가 채워진다 | 도출 |
| T-23 | R-12 | 하네스 훅이 설치되어 있고 `memory.auto_writeback` 미설정인 브레인에서 세션이 끝나 sweep이 돎, 이어서 `gbrain config set memory.auto_writeback off` | 미설정이면 `<세션>.txt`가 추출된다(`sweep:corpus`). `off` 뒤에 쌓인 파일은 `writeback_off` 사이드카로 retire되어 나중에 켜도 추출되지 않는다 | 도출 (게이트 표는 T-02 실행) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@63f62b2 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02, C-03, C-20, C-23, C-24; `core/context-engine.ts:1236-1262`; `core/import-file.ts:1210-1225`(주석); 호출자 grep(`runFactsPipeline`·`runFactsBackstop`·`'file_upload'`·`'code_import'` 전체 `src/`) | 문자열 검색 전수. `mcp/dispatch.ts`가 목록에 없음을 확인 |
| R-02, R-03 | C-01 | 코드 읽기. 핸들러 실행 못 함 |
| R-04 | C-06 `extract.ts:50-55`; `effect-journal.ts:52-54`; `effect-facts.ts:96, 145`; `backstop.ts:355-361`; `sweep.ts:855-860`; `checkpoint-harvest.ts:583-592`; `extract-conversation-facts.ts:1-60` 머리 주석(`--override-disabled`) | 코드 읽기 |
| R-05 | C-18; `effect-journal.ts:50-55` | 코드 읽기. effect 디스패처 실행 못 함 |
| R-06 | C-11; demo `eligibility: isFactsBackstopEligible` | 실제 모듈 import 실행 |
| R-07 | C-20 `finalize.ts:598-641`, `backstop.ts:412-506`; demo `queue: …` | 큐는 실제 모듈 실행, sync·잡 제출은 읽기만 |
| R-08 | C-19, C-21; `drain.ts:322-410`; `drain-scheduler.ts:16-17`; `cycle/facts-drain.ts:17-33` | 코드 읽기. 드레인 루프 실행 못 함 |
| R-09 | C-15, C-22 `hook.ts:1443-1612`; `corpus-segments.ts:500-527`; demo `gate: …`, `secret-scan: …` | 게이트·스캔은 실행, 훅 프로세스·IPC는 읽기만 |
| R-10 | C-22 `hook.ts:1320-1441`; C-23; `context-engine.ts:1085-1262` | 훅은 읽기, OpenClaw rung 3은 호출부만 읽음 |
| R-11 | C-22 `hook.ts:1654-1932` | 코드 읽기 |
| R-12 | C-14 `writeback-config.ts:195-277`; C-17; `docs/guides/ambient-writeback.md:72-130`; demo `capture-gate: …` | 게이트 함수는 가짜 엔진으로 실제 모듈 실행. 문서의 표와 구현이 일치함을 확인(문서·구현 차이 없음) |
| R-13 | C-24; `corpus-windows.ts:45-49`; `serve.ts:71-75, 832-892`; `sweep.ts:1153-1155` | 코드 읽기 |
| R-14 | C-23 `context-pack-handler.ts:145-190`, `checkpoint-harvest.ts:100-170, 541-650` | 코드 읽기. 컴팩션 레인 실행부(375-450)는 sweep과 같은 구조로만 읽음 |
| R-15 | C-31; `cycle/facts-drain.ts`; `cycle/conversation-facts-backfill.ts:1-60`; `sweep.ts:14-30`(주석) | 헤더·phase 배치 읽기. 스케줄러·`runExtractFacts` 본문 미열람 |
| R-16 | C-30; `conversation-windows.ts:20-80`; `conversation-types.ts` | 명령 흐름 일부와 창 분할 읽기, 분할 함수는 실행(T-13) |
| R-17 | C-16; demo `instructions: …` | 실행 |
| R-18 | C-27; demo `fence-projection: …` | 변환 함수는 실행, 발행 SQL은 읽기만 |
| R-20 | C-06, C-09 `extract.ts:605-660`; `ai-gateway R-08·R-09` | 코드 읽기 |
| R-21 | C-08; demo `extract: 시스템 프롬프트 …` | 프롬프트 문자열을 실제 소스 줄 범위로 실행 출력 |
| R-22 | C-09 `extract.ts:660-761` | 코드 읽기 |
| R-23 | C-07, C-09 `extract.ts:762-870`, C-10; demo `extract: …` | 파서·정크·화자 판정·clamp는 실행, 후보 루프는 읽기 |
| R-24 | C-02 `backstop.ts:746-770`; `notability-filter.ts`; demo `notability: …` | 설정 해석은 실행 |
| R-25 | C-15; demo `gate: …` | 실제 모듈 실행 |
| R-26 | C-09 `extract.ts:776-827`; `embedding-disabled.ts`(호출만) | 코드 읽기 |
| R-30 | C-04 `backstop.ts:800-875`; C-13 | 코드 읽기, SQL 실행 못 함 |
| R-31 | C-12; demo `capture-dedup: …` | 순수 규칙은 줄 범위 실행, 읽기 SQL은 읽기만 |
| R-32 | C-04, C-12, C-13; demo `threshold: …` | 임계값·판정은 실행 |
| R-33 | C-26 `engine-sql/facts.ts:81-199`; `classify.ts` 전체; 호출자 grep(`classifyAgainstCandidates`는 `test/facts-classify.test.ts`, 문서, 정의 파일에만 존재) | 문자열 검색 전수 |
| R-40~R-42 | C-04 `backstop.ts:896-1077`; C-25 | 코드 읽기. 기본 설치의 `local_path` 부재는 [page-storage R-02](./page-storage-and-import.md)·[engine-and-schema R-26](./engine-and-schema.md) 인용 |
| R-43 | C-28; demo `visibility: …`; `writeback-config.ts:89-97`(지시문 자세와의 차이) | 실제 모듈 실행 |
| R-44 | C-05 `backstop.ts:235-243, 689-717`; C-33 | 기본 모드만 확인 |
| R-45 | `backstop.ts:373-381`; `fence-write.ts:331-343` | 분기만 |
| R-46 | C-04 `backstop.ts:805`; `subject-infer-write.ts:29-62`; `subject-infer.ts:1-30` | 코드 읽기 |
| R-50~R-52 | C-05, C-09, C-19, C-21, C-24; `backstop.ts:654-673` | 코드 읽기 |
| R-53 | C-18, C-20, C-24, C-29; demo `queue: …` | 큐만 실행 |
| R-54 | C-22 헤더 1-37, 각 이벤트의 `catch`와 `return 0` | 코드 읽기 |
| R-60, R-61 | 위 근거의 상수; demo `drain-config: …`, `conversation: …` | 상수는 실제 모듈 값 |
| T-01~T-17 | `demo-pure.out.2026-10-24.json`의 같은 이름 항목 | 실행 |
| 문서와 구현의 차이 | ① 지도 12행은 "분류기 중복 제거"라고 하지만 구현의 LLM 분류기 `classifyAgainstCandidates`는 호출자가 없다(R-33). ② `docs/guides/ambient-writeback.md`의 "기본 꺼짐"은 Stop 훅 턴 레인과 지시문에 대해서만 맞고 컴팩션·SessionEnd 레인은 훅이 설치되면 미설정에서도 추출한다(문서 자체가 같은 표를 싣고 있어 문서와 구현은 일치. 지도의 보고가 "기본 꺼짐"을 전체에 적용한 것이 부정확). ③ `backstop.ts` 머리 주석의 소스 목록과 5개 대체 구현 설명은 `file_upload`·`code_import`가 호출되는 것처럼 읽히지만 호출자가 없다(R-01). ④ `backstop.ts` 머리 주석은 "dedup @0.95"라고 하나 실제는 모델별 보정 임계값이고 보정 안 된 모델은 코사인으로 중복을 판정하지 않는다(R-32). 구현이 사실이다 | 코드 확인 |

### 2.2 코드 읽는 순서

1. 에이전트가 부르는 입구: `ops/facts.ts`의 `extract_facts`(60-208) → `facts/backstop.ts`의 `runFactsPipeline` → `runPipelineBodyInner`(720-1077).
2. 핵심 판단: `facts/extract.ts`의 프롬프트(360-455) → `extractFactsFromTurnWithOutcome`(605-879) → 파서(908-1022).
3. 저장 전 중복·저장: `capture-dedup.ts` → `single-prepare.ts`(104-135) → `fence-write.ts`(324-623) → `engine-sql/facts.ts`의 `insertFact`.
4. 페이지 쓰기 입구: `persistence/effect-facts.ts` → `effect-journal.ts`(50-55) → `minions/handlers/facts-absorb.ts` → `facts/drain.ts`.
5. 캡처 레인: `commands/hook.ts`(stop·compact·session-end) → `facts/writeback-gate.ts` → `mcp/context-pack-handler.ts` → `context/checkpoint-harvest.ts` → `core/sweep.ts`(코퍼스 패스) → `facts/writeback-config.ts`(게이트).
6. 대화 배치: `commands/extract-conversation-facts.ts` → `facts/conversation-windows.ts`.
- 구현 전략: 모든 서버 추출이 하나의 파이프라인 함수로 합류하고 경로별 차이는 `source` 라벨·`notabilityFilter`·`sessionId`·가시성·캡처 게이트로만 드러난다. 비용이 큰 LLM 호출 앞에는 결정적이고 싼 필터(Stop 게이트, 적격성, 길이, 해시 멱등, 워터마크)를 층으로 쌓고, 호출 뒤에는 정규식·스키마 검증·노터빌리티 필터로 거른다. 실패는 "값으로 돌려주는 것(재시도 불필요/호출자 결정)"과 "던지는 것(재시도 대상)"으로 갈라 잡 큐의 재시도·연기가 맡는다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사한 곳은 없다. 같은 레포의 [memory-verbs](./memory-verbs.md) `remember`와 정확 지문·모델별 코사인 판정 코드(`decideSingleFact`)를 공유하고, 차이는 이 스펙 R-30~R-33(철회 건너뜀·`superseded` 없음·캡처 레인 규칙)과 R-40(저널을 거치지 않음)에 있다.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-33 | LLM 중복/대체 분류기(`classify.ts`)를 구현하지 말 것, 또는 필요하면 별도 결정으로 도입 | 원본은 정의만 있고 호출하지 않는다. 원본의 결과 집합은 `inserted`·`duplicate`뿐 | 없음(원본 동작 유지) |
| R-43 | 서버 추출 사실과 에이전트 `remember`의 기본 가시성(`private` vs `world`)을 한 규칙으로 맞출지 정할 것 | 기본 설치에서 서버가 뽑은 사실은 원격 에이전트가 읽을 수 없고, `remember`로 저장한 사실은 읽을 수 있어 일관되지 않다 | 설정 의미 변경(원본에 없음) |
| R-23 | 서버 쪽 `extract_facts`·페이지 경로 입력에도 비밀 스캔을 적용할지 정할 것 | 원본은 캡처 레인이 은행에 넣기 전에만 스캔하고, 서버 추출은 그 텍스트를 그대로 공급자에게 보낸다 | 입력 전처리 추가(원본에 없음) |
