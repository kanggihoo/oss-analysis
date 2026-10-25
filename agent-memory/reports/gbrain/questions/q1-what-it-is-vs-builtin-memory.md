---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-22
updated: 2026-10-23
sources:
  - README.md
  - src/core/verbs.ts
  - src/core/facts-fence.ts
  - src/core/facts/fence-write.ts
  - src/core/persistence/memory-mutations.ts
  - src/core/search/hybrid.ts
  - docs/architecture/system-of-record.md
  - docs/guides/memory-boundaries.md
---

# Q1: gbrain이 무엇이고, Claude 같은 에이전트의 기본 메모리와 무엇이 다른가

## 결론

- gbrain은 "에이전트 하나에 딸린 메모리 파일"이 아니라, 에이전트 바깥에 두는 **공용 지식 저장소 + 검색 서버**다. 에이전트(Claude Code, Codex 등)가 MCP로 붙어서 `remember`(저장)·`recall`(조회)·`think`(종합 답) 같은 도구로 쓴다. (코드 확인: `src/mcp/server.ts`, `src/core/verbs.ts`)
- "마크다운으로 관리한다"는 절반만 맞다. 소스에 체크아웃 폴더(`local_path`)가 있으면 마크다운 파일이 **원본**이고 DB는 거기서 다시 만들 수 있는 **색인**이다. 폴더가 없으면(새로 `init`한 직후 기본 상태) DB 행이 유일한 사본이다. 폴더가 있어도 DB에만 있는 정보(개정 이력, 철회 장부 등)가 있어서 DB 백업이 따로 필요하다. (코드 확인: 쓰기 경로는 [page-storage-and-import 스펙](../capabilities/page-storage-and-import.md)이 확정했다. 문서 주장은 `docs/architecture/system-of-record.md` 1~25줄)
- Claude의 기본 메모리와 차이는 "저장 형식"이 아니라 **누가 읽고 쓰는가(공유), 어떻게 찾는가(검색), 어떻게 고치는가(출처·철회)** 에 있다. README도 같은 입장이다: "Muse는 이미 편집 가능한 기본 메모리가 있다. GBrain은 출처와 공유 접근이 있는 명시적이고 옮길 수 있는 기록을 더한다." (`README.md` 20줄, 저자 주장)

## 1. 작은 모형

```text
remember(fact="Alice는 비동기 회의를 선호", entity="alice", provenance="1:1 통화 2026-10-22")
  → alice 페이지 마크다운의 "## Facts" 표에 한 줄 추가   (원본)
  → DB의 facts 테이블에 같은 내용을 색인              (파생)
recall(entity="alice")  → 그 사실들을 돌려줌
forget(fact_id=…)       → 줄을 취소선으로 바꾸고 "철회 장부"에 기록 (다시 저장 불가)
```

실제 마크다운은 이런 표다 (`src/core/facts-fence.ts` 머리 주석의 형식):

```text
| # | claim                      | kind       | confidence | visibility | ... | source        |
| 2 | Prefers async over meetings | preference | 0.85       | private    | ... | OH 2026-04-29 |
| 4 | ~~Used to live in Tokyo~~   | fact       | 0.9        | private    | ... | forgotten: user asked to remove |
```

| 모형의 줄 | 실제 코드 | 검증 수준 |
|---|---|---|
| `remember(...)`에서 출처가 없으면 거부 | `src/core/verbs.ts` `remember` 핸들러: `provenance`가 없으면 `invalid_params`, 빈 값이면 `provenance_required` | 코드 확인 |
| 마크다운에 먼저, DB는 나중 | `src/core/facts/fence-write.ts` 머리 주석("markdown-first"), 현재 경로 `src/core/persistence/memory-mutations.ts`가 `parseFactsFence`·`fence`·`writeThrough`를 사용 | 코드 확인(주석과 호출 존재), 저널 소비자까지는 미추적 |
| `forget`은 취소선 + 철회 | `src/core/facts-fence.ts`의 `~~claim~~` + `forgotten:` 규칙, `docs/guides/memory-boundaries.md`("withdrawal은 물리적 삭제가 아니다", 완전 삭제는 별도 `purge`) | 코드 확인(형식·문서), `fact_withdrawals` 테이블 동작은 보고 확인 |
| `recall`이 검색을 쓴다 | `ops/facts.ts` `recall`의 `query` 인자가 `hybridSearchCached`로 페이지를 검색 | 보고 확인 |

## 2. Claude Code 기본 메모리와 비교

| 항목 | Claude Code 기본 메모리 (이 세션에서 관찰) | gbrain |
|---|---|---|
| 저장 | 사실 하나당 마크다운 파일 하나, frontmatter(`name`/`description`/`type`) + 목록 파일 `MEMORY.md` | 엔티티(사람·회사 등) 페이지 마크다운 + 그 안의 `## Facts` 표, 그리고 DB 색인 |
| 범위 | 프로젝트 경로별 폴더(`~/.claude/projects/<경로>/memory/`) — Claude Code 안에서만 | MCP 서버라 Claude Code, Codex, Cursor 등 여러 에이전트가 **같은 저장소**를 읽고 쓴다 (README 주장, 서버 코드는 확인) |
| 찾는 방법 | 목록(`MEMORY.md`)이 매 세션 컨텍스트에 실리고, 모델이 설명을 보고 관련 파일을 고른다 | 키워드 + 벡터 + 그래프 + 최근성을 섞은 하이브리드 검색. 키 없이도 키워드 검색만으로 동작 |
| 출처 | 형식 규칙 없음 (모델이 쓰기 나름) | `remember`가 출처를 필수로 요구, 사실마다 신뢰도·유효기간·공개 범위 |
| 고치기·잊기 | 파일을 고치거나 지움 | 대체(`replaces`)·만료(`ttl`)·철회(`forget`)·영구 삭제(`purge`, 소유자만)가 분리돼 있음 |
| 종합 | 없음 (읽은 걸 모델이 알아서 합침) | `think`가 여러 페이지·주장·링크를 모아 인용 달린 답과 "모르는 부분"을 돌려줌 |
| 정리 | 사용자·모델이 수동 | `dream` 사이클이 30단계(링크 추출, 사실 추출, 중복 정리 등)를 돌린다 |
| 비용 | 설치 없음 | Bun, DB(PGLite 내장 또는 Postgres), 선택적으로 임베딩·LLM 키 |

- Claude Code 열은 이 세션의 시스템 지시문과 메모리 폴더(`MEMORY.md` 목록이 컨텍스트에 실리고 파일마다 `name/description/type` frontmatter가 있음)를 보고 적었다. 검증 수준: 실행 확인(이 세션 환경).
- gbrain 열: 저장·출처·검색 단계는 코드 확인, 정리 단계 수는 `src/core/cycle.ts`의 `ALL_PHASES`(30개)를 확인했다.
- claude.ai 앱의 대화 메모리는 이 분석에서 확인하지 않았다 (미확인).

## 3. 어떤 상황에서 차이가 나는가

- **Claude Code 하나만 쓰고 메모가 수십 건**이면 기본 메모리로 충분하다. 목록이 컨텍스트에 다 들어가고 설치할 것이 없다. (추론)
- **Claude Code와 Codex를 같이 쓰거나, 노트가 수천~수만 건**이면 목록을 컨텍스트에 전부 실을 수 없다. 이때 gbrain의 검색 서버 구조가 의미가 있다. README는 저자의 운영 규모를 15.5만 페이지라고 주장한다. (미확인: 규모·성능은 실행하지 않았다)
- **출처와 정정 이력이 중요한 지식**(사람·회사·거래에 대한 기록)이면 출처 필수와 철회 장부가 차이를 만든다. (코드 확인: 출처 필수. 철회 장부는 보고 확인)

## 4. 후속 질문: "에이전트와 무관한 중앙 메모리이고 .md로 관리하는 건가?"

맞다. 다만 "중앙"과 ".md" 모두 범위를 정해야 한다.

| 말 | 정확한 범위 | 검증 수준 |
|---|---|---|
| 중앙 | gbrain 서버(또는 로컬 DB) **하나**. 에이전트들이 MCP(stdio 또는 HTTP+OAuth)로 붙는다. 서버가 여러 대면 "브레인"이 여러 개이고 `mounts`로 잇는다 | 코드 확인(`mcp/server.ts`, `serve-http*.ts`, `commands/mounts.ts`) |
| .md 파일이 있는 곳 | gbrain이 도는 머신의 "brain repo" 폴더(소스의 `local_path`). 다른 머신과 맞추는 방법은 git이다("Multi-machine sync is git") | 코드 확인(문서 `docs/architecture/system-of-record.md` 31~33줄, `sources.local_path` 사용) |
| 쓸 때 파일에도 쓴다 | 설정 `sync.write_through`(기본 켜짐, 코드에서 `'true'`가 기본)이 켜져 있고 서브에이전트 샌드박스가 아닐 때 | 코드 확인(`persistence/memory-mutations.ts` `planRememberTarget`) |
| **모든 기억이 .md다** | **아니다.** 아래 DB 전용 경우가 있다 | 코드 확인 |

.md가 아니라 DB에만 있는 것:
1. **엔티티 없이 저장한 사실**: `remember`에 `entity`를 안 주고 추론도 실패하면 `memory/unattributed`로 저장되고, 이때 `fence`가 `false`라서 파일에는 쓰지 않는다. 주석: "a fallback name remains DB-only until a real entity page exists. No placeholder page is created by remember." (`memory-mutations.ts:100~103`, 코드 확인)
2. **쓰기 설정이 꺼진 경우**와 **서브에이전트 샌드박스**: `databaseOnlyReason`이 `disabled_by_config` / `subagent_sandbox`로 기록된다. (코드 확인, 같은 함수)
3. **이력·철회 장부·토큰·잡 큐 등**: 문서의 "DB-only by design" 표. 특히 철회(forget) 결정과 belief 이력은 "마크다운으로 재구성할 수 없다"고 적혀 있다. (`docs/architecture/system-of-record.md` 79~100줄, 문서 확인)

그래서 "에이전트가 쓴 사실은 .md 표에 한 줄로 남는 것이 원칙이지만, 엔티티를 못 정한 기억은 DB에만 있다"가 정확하다.

## 5. 미확인과 다음 단계

- gbrain을 실제로 설치·실행해 `remember → recall → forget` 왕복을 확인하지 않았다(의존성 설치·DB 생성이 필요해 사용자 승인 대상, 워크플로 9장).
- 검색 품질·속도, README의 벤치마크 수치, 호스티드(gbrain.io) 동작은 미확인이다.
- 쓰기 저널이 마크다운과 DB를 어떤 순서로 쓰는지는 [page-storage-and-import 스펙](../capabilities/page-storage-and-import.md)이 다뤘다(2026-10-23). `remember`·`## Facts` 쪽 경로는 11·12행 스펙에서 다룬다.
