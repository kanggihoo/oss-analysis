---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/core/ops/pages.ts
  - src/core/ops/page-edit.ts
  - src/core/ops/page-append.ts
  - src/core/ops/page-batch.ts
  - src/core/ops/page-upload.ts
  - src/core/ops/tags.ts
  - src/core/ops/timeline.ts
  - src/core/ops/context.ts
  - src/core/persistence/page-mutations.ts
  - src/core/persistence/journal.ts
  - src/core/persistence/model.ts
  - src/core/persistence/types.ts
  - src/core/persistence/schema.ts
  - src/core/persistence/suffixed-slug.ts
  - src/core/persistence/maintenance.ts
  - src/core/persistence/page-batch-id.ts
  - src/core/persistence/params.ts
  - src/core/persistence/preconditions.ts
  - src/core/persistence/service.ts
  - src/core/persistence/write-wait.ts
  - src/core/persistence/coordinator.ts
  - src/core/persistence/page-prepare.ts
  - src/core/persistence/canonical-projections.ts
  - src/core/persistence/effect-journal.ts
  - src/core/persistence/effect-model.ts
  - src/core/persistence/effects.ts
  - src/core/persistence/effect-git.ts
  - src/core/persistence/git-durability-policy.ts
  - src/core/persistence/unbound-source.ts
  - src/core/persistence/ownership.ts
  - src/core/persistence/semantic.ts
  - src/core/persistence/semantic-pages.ts
  - src/core/persistence/page-edit.ts
  - src/core/persistence/page-append.ts
  - src/core/persistence/page-batch.ts
  - src/core/persistence/page-upload.ts
  - src/core/persistence/large-page-guard.ts
  - src/core/page-state/types.ts
  - src/core/import-file.ts
  - src/core/import-identity.ts
  - src/core/import-screen.ts
  - src/core/markdown.ts
  - src/core/data-frontmatter.ts
  - src/core/markdown-chunks.ts
  - src/core/frontmatter-recovery.ts
  - src/core/embed-retry.ts
  - src/core/chunkers/recursive.ts
  - src/core/chunkers/token-estimate.ts
  - src/core/cjk.ts
  - src/core/remote-body.ts
  - src/core/credential-projection.ts
  - src/core/embedding-input-limit.ts
  - src/core/frontmatter-inference.ts
  - src/core/capture-content.ts
  - src/core/utils.ts
  - src/core/batch-rows.ts
  - src/core/sync.ts
  - src/core/write-through.ts
  - src/core/page-size-policy.ts
  - src/core/page-body/limits.ts
  - src/core/export-stage.ts
  - src/core/behavior-change-notice.ts
  - src/commands/import.ts
  - src/commands/embed.ts
  - src/commands/export.ts
  - src/commands/capture.ts
  - src/cli/main.ts
  - docs/architecture/system-of-record.md
depends:
  - ./engine-and-schema.md
  - ./ai-gateway.md
status: ready
reimplementation: 미실행
---

# 페이지 저장·쓰기 저널과 마크다운 import·embed·export

> 마크다운 한 편(frontmatter + 본문)을 `put_page` 계열 연산이나 `gbrain import <dir>`로 받아 `pages` 행·`tags`·`content_chunks`로 쪼개 기록하고(쓰기 저널이 `expected_revision`·`request_id`로 충돌 감지와 재전송 안전을 준다), 쓰기 연산은 조건이 맞으면 같은 트랜잭션 안에서 소스 체크아웃에 마크다운 파일도 쓰며, `embed`로 빠진 벡터를 채우고 `export`로 DB를 마크다운 파일로 내보낸다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름 A는 `put_page`(저널 경로)이고, 흐름 B는 `gbrain import <dir>`(파일 → DB 직접 경로)이다. 두 흐름은 `parseMarkdown` → 청킹 → `content_chunks` 기록을 공유하지만 임베딩 시점·파일 쓰기 여부·태그 의미가 다르다(R-16, R-22).

**흐름 A. `put_page(slug, content, expected_revision?, request_id?)`**

1. 입구 검사: 슬러그 문법·소스 쓰기 권한·24 MiB 상한·예약 필드를 검사한다(R-14, R-37). 통과하면 이 요청의 불변 "의도"(intent)가 정해진다. 같은 `request_id`의 이전 요청이 있으면 새로 쓰지 않고 그 영수증을 기다린다(R-31).
2. 접수: `persistence_requests`에 `state='queued'` 행을 넣고 호출자·브레인 단위 카운터를 예약한다(R-33). 여기까지 실패하면 아무 행도 안 생긴다.
3. 같은 프로세스의 소비자가 요청을 잡아 준비한다: 페이지 스냅샷을 읽고 `expected_revision`을 검사하고(R-32), 본문을 파싱·분리·청킹하고(임베딩은 하지 않음, R-10~R-19), 쓸 파일의 내용과 경로를 정해 디스크의 기존 파일이 DB 행과 같은지 비교한다(R-06).
4. 발행: 소스 체크아웃 락을 잡고, 되돌릴 복구 기록(기존 파일 바이트)을 먼저 남기고, DB 트랜잭션을 연다. 트랜잭션 안에서 재검사 → 파일 원자 교체(rename) → `pages`·`tags`·`content_chunks`·타임라인·사실·링크 쓰기 → 후속 작업(effect) 큐 등록 → 영수증을 `committed`로 기록한 뒤 커밋한다(R-04, R-05).
5. 커밋 뒤 effect가 돈다: 파일을 쓴 요청의 `git`(체크아웃이 "내구" 설정일 때만 실제 커밋), 청크 벡터를 채우는 `embedding`, 원격 호출자의 `links`, `facts-backstop`(R-07, R-22).
6. 호출자는 `wait_ms` 안에 `committed` 영수증을 받거나, 시간이 지나면 `write_pending` 오류를 받는다. 쓰기는 계속 진행되고 같은 `request_id`로 다시 부르면 영수증을 돌려준다(R-34).

**흐름 B. `gbrain import <dir>`(관리 모드가 아닌 브레인)**

1. 임베딩이 켜져 있고 `--no-embed`가 없으면 자격 증명을 먼저 점검하고 모자라면 중단한다(R-50).
2. 디렉터리에서 `.md`·`.mdx` 파일을 모은다(`.gitignore` 반영, 점 디렉터리·`node_modules` 등 제외, R-50).
3. 파일마다: 크기·심볼릭 링크·파일명 검사 → frontmatter 없으면 경로에서 추론 → `parseMarkdown` → 슬러그를 경로에서 도출해 frontmatter `slug`와 대조(R-25).
4. `importFromContent`: 해시 계산 → 같은 `content_hash`면 건너뜀(R-15) → 청킹 → 청크 임베딩(실패해도 텍스트는 저장, R-21) → 한 트랜잭션에서 `pages`·`tags`·`content_chunks` 교체(R-20).
5. 파일은 쓰지 않는다. 끝나면 `ingest_log` 한 줄과(변화가 있을 때) 체크포인트·git 앵커 설정을 남긴다(R-51).

### 1.2 범위·통합 지점

- 제공: 페이지 쓰기 연산 9종(`put_page`, `edit_page`, `append_page`, `put_pages`, 분할 업로드 5연산, `capture`, `add_tag`/`remove_tag`, `add_timeline_entry`)의 입력·영수증·충돌 의미; 마크다운 → `pages`/`content_chunks` 분해 규칙; `import`·`embed`·`export` 명령; 질문 ①(마크다운이 원본인가)의 답(2.1).
- 제외(이유):
  - 저널 소비자 내부(claim·lease·lane·그룹 발행·복구 스캔·백오프 숫자), `persistence/` 약 300개 파일 중 이 경로 밖: 영수증으로 관찰되는 계약만 정의했고 내부는 읽지 않았다(확인 한계).
  - 분할 저장(`page-body/*`, 1 MiB 초과 본문): 경계와 설정만 R-47에 둔다. 세그먼트 분할·매니페스트·스트리밍 import는 별도 스펙 후보다(이 스펙의 청킹·해시·임베딩 규칙은 인라인 저장 페이지 기준).
  - 관리 모드(`persistence_brain.enabled=true`)의 `import`(`managed_file_import` 요청)와 `sync`: 같은 파싱·청킹을 쓰지만 저널을 거친다. 지도 20행(git sync) 소관이고 여기서는 경계만 R-08에 적었다.
  - 신뢰 등급·쓰기 게이트·내용 위생(junk 격리)·`trust_tier` 마커·보호 펜스의 원격 가림(`sanitizeRemoteBody`의 원격 읽기 쪽)·펜스 정규화(Tier 1): 지도 13행 소관. 이 스펙은 결과(`quarantined` 페이지는 청크 0개, R-17)만 정한다.
  - `## Facts`·`## Takes` 펜스의 파싱과 `facts`·`takes` 행 투영, 링크 추출·자동 링크: 지도 12·14·8행 소관(R-23에 경계만).
  - 코드 파일 import(`importCodeFile`, tree-sitter 청커)와 이미지 import: 지도 10행. 마크다운 안의 인식된 코드 펜스를 코드 청커로 청킹하는 부분도 R-17에 존재와 출력 모양만 적고 알고리즘은 제외한다.
  - 페이지 읽기·삭제·복구·버전·purge(지도 4행). 단 `delete_page`/`restore_page`가 같은 입구를 쓴다는 사실은 R-01에 적었다.
  - 임베딩 호출 계약(배치 분할·차원·영벡터·재시도·키 없음)은 [ai-gateway](./ai-gateway.md) R-20~R-27을 인용한다. 테이블·컬럼·`putPage`/`upsertChunks` 계약은 [engine-and-schema](./engine-and-schema.md) 1.3을 인용한다.
- 외부 의존·선행 계약: 엔진은 `engine-and-schema`의 `BrainEngine`(`putPage`, `upsertChunks`, `readPageSnapshot`, `transaction`, `executeRaw`, `getConfig`)이다. 임베딩은 `ai-gateway`의 `embedBatch`(R-27)다. 파일 시스템(소스 체크아웃)과 `git` 실행 파일은 호출자 환경이 제공한다.
- 소유 상태·부작용: `pages`·`tags`·`content_chunks`·`timeline_entries`·`page_versions` 행, 저널 테이블(`persistence_requests`, `persistence_counters`, `persistence_effects`, `persistence_worktrees`, `persistence_source_bindings`, `persistence_host_bindings`, `persistence_brain`, `persistence_local_writers`; DDL은 C-05), 소스 체크아웃의 `<slug>.md` 파일과 `git` 커밋, `~/.gbrain/import-checkpoint.json`, `ingest_log`, `sync.repo_path`·`sync.last_commit`·`sync.last_run` 설정(import가 조건부로 씀, R-08), 내보내기 디렉터리.

### 1.3 인터페이스와 데이터 의미

연산 이름·파라미터는 외부 계약이므로 원문 그대로 적는다. CLI 플래그는 파라미터 이름의 `_`를 `-`로 바꾼 `--<name>`이고, 위치 인자와 stdin 대응은 `cliHints`로 정해진다(C-30).

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `put_page` (CLI `gbrain put <slug>`, stdin이 `content`) | `slug`, `content`, `expected_revision?`, `force?`, `request_id?`, `source_id?`, `allow_empty?`, `allow_shrink?`, `drop_timeline?`, `wait_ms?`, `content_origin?`, `source_kind?`/`source_uri?`/`ingested_via?`(원격 호출자 값은 서버가 덮어씀) → `committed` 영수증 | 전체 교체. 새 페이지는 `expected_revision` 생략, 기존 페이지는 현재 revision 필수(R-32). 영수증 필드는 R-34 |
| `edit_page` | `slug`, `expected_revision`(필수), `edits[1..50]{old_text,new_text}`, `within?{byte_start,byte_end}`, `source_id?`, `request_id?` → 영수증 + `diff` | 정확 문자열 치환(R-40) |
| `append_page` | `slug`, `text`(≤4 MiB), `request_id`(필수), `expected_revision?`, `expected_tail_sha256?`, `region?`(auto/truth/timeline), `separator?`(auto/none), `source_id?`, `wait_ms?` → `{slug, revision, body_bytes, appended_bytes, chunks_new, receipt}` | 끝에 덧붙임(R-41) |
| `put_pages` | `pages[1..50]{slug,content,expected_revision?,allow_empty?,allow_shrink?,drop_timeline?}`(합계 ≤8 MiB), `request_id`(필수), `source_id?`, `wait_ms?`(기본 25000) → 배치 영수증 | `pages` 생략 + `request_id`만 = 진행 조회(R-42) |
| `begin_page_upload` / `upload_page_part` / `get_page_upload` / `commit_page_upload` / `abort_page_upload` | 4 MiB 프레임 한도 안에서 조각 업로드 → 커밋 시 `put_page`/`append_page` 영수증 | R-43 |
| `capture` (CLI `gbrain capture [content]`) | `content`, `slug?`, `type?`, `who/what/where/kind/depth?`(event), `local_file?`(로컬 CLI만), `expected_revision?`, `force?`, `request_id?` → `put_page` 영수증 + `channel:'capture'`, `content_hash` | R-44 |
| `add_tag` / `remove_tag` | `slug`, `tag`, `expected_revision?`, `force?`, `request_id?` | R-45 |
| `add_timeline_entry` | `slug`, `date`(YYYY-MM-DD, 1900~2199), `summary`(한 줄), `detail?`, `source?`, 선택 `expected_revision?`/`force?`/`request_id?` | R-46 |
| `gbrain import <dir>` | 위치 인자 `<dir>`, `--no-embed`, `--workers N`, `--fresh`, `--source <id>` 또는 `--source-id <id>`, `--include-gitignored`, `--allow-noncanonical-root`, `--log-noop`, `--json` → `{status, imported, skipped, errors, chunks, total_files, unchanged, malformed_skipped, failures[], source_id, duration_s}` | R-50, R-51 |
| `gbrain embed` | `<slug>` 또는 `--all` / `--stale` / `--slugs s1 s2 …` / `--held` / `--facts` / `--images`; `--dry-run`, `--source <id>`, `--batch-size N`, `--priority recent`, `--catch-up`, `--include-null-signature`, `--background`, `--yes` / `--max-usd N`, `--pace[=mode]` → `EmbedResult{embedded, skipped, would_embed, total_chunks, pages_processed, failures, failure_samples, dryRun, chunkless_pages_healed, lock_skipped?, reason?}` | R-52 |
| `gbrain export` | `--dir <path>`(기본 `./export`), `--source <id>`, `--type <type>`, `--slug-prefix <prefix>`, `--restore-only`, `--repo <path>` → `{pages, escaped[]}` | R-53 |

공유 객체 의미(필드 뜻은 engine-and-schema 1.3 인용, 여기서는 이 기능이 정하는 값만):

- 영수증(`WriteReceipt`): `request_id`(캐노니컬 UUID), `client_request_id?`(비UUID 원문), `state`, `outcome{…}`, `write_error?`, `write_error_detail?`, `blocked_reason?`, `retry_after_ms?`(비종결일 때), `compacted?`, `created_at`, `updated_at`, `diagnostic?`. `state ∈ {queued, running, recovering, committed, conflict, failed, cancelled}`(C-06). 종결 상태는 `committed`·`conflict`·`failed`·`cancelled`.
- `put_page` 성공 `outcome`: `status`(`created_or_updated` / `skipped`(변화 없음) / `duplicate`), `slug`, `source_id`, `chunks`, `noop`, `revision`, `persistence{mode:'filesystem'|'database', file_written?, git_state?}`, `write_through{written, skipped?, warning?}`, `embedding_state`(`queued`/`disabled`/`deferred`), 해당 시 `chunk_skip_reason`(`write_skipped`/`embed_skip`/`empty_body`), `quarantined`, `projection:'pending'`(R-47), `timeline_rows_removed`, `type_warning`, `slug_advisory`.
- `revision`: 페이지의 `knowledge_revision` UUID(engine-and-schema 1.3, 정규 내용이 바뀌면 트리거가 새 UUID). 읽기 연산이 돌려주고 쓰기 연산의 `expected_revision`으로 되돌려 준다.
- 단위: 크기는 UTF-8 바이트(본문은 `compiled_truth`+`timeline`), 시간은 ms, `wait_ms` 0~30000(CLI 기본 30000, 에이전트·서버 기본 5000, C-07).

### 1.4 행동 규칙과 남은 질문

**A. 저장 위치: 파일인가 DB인가 (질문 ①)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `put_page`·`edit_page`·`append_page`·`put_pages`·`capture`·업로드 커밋·`add_tag`·`remove_tag`·`add_timeline_entry`(그리고 `delete_page`·`restore_page`·`revert_version`) | 전부 `submitPageMutation` 한 입구로 들어간다. 요청은 먼저 `persistence_requests` 행(`queued`)이 되고 소비자가 발행한다. 저널은 관리 모드 여부와 무관하게 쓰인다(`persistence_brain.enabled` 기본 `false`). 마크다운 CLI 한 번(`gbrain put`)도 이 경로이며, 프로세스 안에 소비자를 직접 띄운다 (C-01, C-02, C-05) | 코드 확인 |
| R-02 | 파일을 쓸지의 결정(`preparePageAdmission`). 순서: ① 샌드박스 서브에이전트(허용 접두 없음) → DB 전용 `subagent_sandbox` ② `sync.write_through`가 `false/0/off/no` → `disabled_by_config`(기본은 켜짐) ③ 소스 루트 = `sources.local_path`, 없고 소스가 `default`면 `sync.repo_path`. 루트도 소유 바인딩도 없으면 `no_repo_configured` ④ 루트는 있는데 바인딩이 없으면 `decideUnboundWrite`: 커넥터 소스 → DB 전용(`connector_database`), PGLite → 자동으로 소스를 claim해 바인딩을 만든다(활성화가 DB 전용으로 지정한 소스는 Postgres와 같은 규칙), Postgres → 기본은 `owner_unavailable`(`unbound_source`)로 거부하고 `persistence.unbound_write=database_only`일 때만 DB 전용(`unbound_source`) | DB 전용이면 `pages`·`content_chunks` 행만 쓰고 영수증에 `persistence.mode:'database'`, `write_through{written:false, skipped:<이유>}`가 붙는다(원격 호출자의 `no_repo_configured`에는 경고 문구). 파일을 쓰는 경우는 R-03~R-07. 위 외에도 준비 단계가 `db_only`로 선언된 경로(`gbrain.yml`)·읽기 전용 미러 소스·파일 없이 만들어진 derive 단계 페이지·원본 파일을 중복 페이지에 넘긴 페이지를 DB 전용으로 돌린다 (C-03, C-04, C-11, C-12) | 코드 확인 (PGLite 자동 claim 후 classic sync 영향은 미확인) |
| R-03 | 파일을 쓰는 경우의 경로 | 경로는 바인딩된 체크아웃 루트(`persistence_host_bindings.local_path` + 소스의 `relative_path`; claim 때 루트가 git 저장소 안이면 git 루트가 `local_path`가 된다) 기준이다. 기존 페이지는 기록된 `pages.source_path`(루트가 git 저장소 안이면 git 루트 기준 상대)를 `resolveSourceLocalFilePath`로 푼다. `source_path`가 없으면 `source_uri`의 `file://` 기록 경로, 새 페이지는 `capture --file`이 소스 안 파일이면 그 경로, 그 밖에는 `<루트>/<slug>.md`. 파일은 루트 안(`isWriteTargetContained`)이어야 하며 벗어나면 `source_changed`. 새 페이지의 첫 쓰기에서 `source_path`를 기록한다(`bindOrigin`) (C-08, C-13) | 코드 확인 |
| R-04 | 파일을 쓰는 발행의 순서 | ① 소스 체크아웃의 네이티브 락 ② 기존 파일 바이트와 해시를 담은 복구 기록을 DB에 먼저 남김 ③ DB 트랜잭션 시작 → 가드(소유 epoch, 권한, 요청 claim, 페이지 키 락, revision 재검사) 통과 후에야 ④ 파일을 임시 파일에 써서 `rename`으로 교체 ⑤ 같은 트랜잭션에서 DB 쓰기(`apply`) ⑥ effect 큐 등록 ⑦ 영수증 `committed` ⑧ 커밋 ⑨ 복구 기록 정리. 즉 **파일이 먼저 바뀌고 DB가 같은 트랜잭션에서 뒤따르며, DB 커밋이 영수증의 기준이다** (C-09) | 코드 확인 |
| R-05 | 발행 중 실패 | 가드·revision 검사(파일 교체 전)에서 실패하면 파일은 건드리지 않았다. 파일 교체 뒤 트랜잭션이 실패하거나 결과가 불확실하면 요청은 `recovering`이 되고 소유 호스트가 기록해 둔 이전 바이트를 파일에 복원하며 DB는 롤백이다. 일시적 DB 오류는 백오프 후 재시도, 그 밖의 오류는 종결 실패. 복구 중 파일이 이전·이후 바이트 어느 쪽도 아니면 건드리지 않고 `blocked_reason`(`unexpected_file_bytes` 등)으로 멈춘다 (C-09) | 코드 확인 (복구 세부 단계는 일부만) |
| R-06 | 쓰기 전 디스크 파일 상태(`prepareFileTarget`) | 파일이 있고 페이지가 이미 있으면, 파일 내용이 DB 행의 정규 비교(type, title, compiled_truth, timeline, frontmatter에서 type/title/tags/slug 제외, tags)와 같아야 한다. 다르면(밖에서 편집됨) 어느 쪽도 덮어쓰지 않고 `source_changed`, `detail:'file_database_drift'`로 거부(영수증 `conflict`). 파일이 사라졌으면 `source_changed`(`canonical_file_missing`; DB 전용 선언 페이지·derive 단계 페이지는 예외로 DB만 갱신). 페이지가 없는데 경로를 다른 파일이 차지하면 `source_changed`("An unindexed file already occupies"). 새 페이지의 경로가 `.gitignore`에 걸리고 체크아웃이 내구 설정이 아니면 DB 전용으로 발행 (C-08) | 코드 확인 |
| R-07 | 파일을 쓴 요청의 `git` effect | 커밋 뒤 effect 큐에 `git`이 들어간다(영수증 `persistence.git_state:'queued'`). 실행 때 체크아웃의 `git_durability`가 `enabled`이거나(`disabled`면 아님) 값이 없을 때 레거시 훅이 있으면 `git add -A -- <path>` + `git commit --only`(+push 시도)를 한다. 아니면 명령 없이 `{git:'skipped', reason:'durability_not_enabled'}`로 끝나고 파일은 작업트리에 쓰인 채 남는다. 실패해도 쓰기는 `committed`로 남고 effect가 재시도·5회 연속 실패 시 보류(parked)된다 (C-14, C-15, C-16) | 코드 확인 (push·재시도 세부 미열람) |
| R-08 | `gbrain import <dir>`·`sync`의 방향 | 파일 → DB 한 방향이다. `import`는 DB만 쓰고 파일을 쓰지 않는다. 비관리 브레인의 `import`가 git 저장소(`<dir>/.git`)를 읽었고 전역 앵커를 소유할 때만(`ownsGlobalSyncAnchor`) DB `config`에 `sync.last_run`과 `sync.repo_path=<dir>`를 쓰고, `sync.last_commit`(=`git rev-parse HEAD`)은 파일 실패가 없을 때만 쓴다. 따라서 `import` 뒤 기본 소스에 `put_page`하면 R-02 ③의 루트가 그 디렉터리가 되어 파일 쓰기가 시작될 수 있다. 관리 모드 브레인의 `import`는 `managed_file_import` 저널 요청으로 같은 일을 한다(제외) (C-20, C-29) | 코드 확인 |
| R-09 | `gbrain export` | DB → 파일 한 방향의 읽기 전용 스냅샷이다. R-53 | 코드 확인 |

**B. 마크다운 한 편이 행으로 쪼개지는 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | frontmatter 파싱 | BOM 제거, 첫 비공백 줄이 `---`면 frontmatter 시작(앞의 빈 줄 허용). 여는 줄의 `---` 뒤 문자열은 언어 선택자: 비어 있거나 `yaml`/`yml`/`json`만 허용, 다른 값은 `FrontmatterLanguageError`. 다음 `---`만 있는 줄이 닫힘(없으면 끝까지가 블록). 블록은 YAML(JSON 선택 시 JSON)이며 결과는 객체여야 한다(배열·스칼라는 오류). 날짜형 스칼라는 달력상 유효할 때만 `Date`. YAML 별칭 확장은 `블록 길이+65,536` 이내(초과 시 `YamlAliasBoundError`). 파싱 전에 `: `나 끝 `:`가 든 따옴표 없는 한 줄 스칼라 값은 자동으로 따옴표를 씌운다. 그래도 엄격 파싱이 실패하면 값 따옴표 복구(`recoverFrontmatter`)를 시도한다: 한 줄 값을 통째로 따옴표로 감싸는 `quote` 복구만 "복구됨"(`frontmatter_recovery.quoted`로 표시하고 import)이고, 여러 줄 접기(`fold`)·중복 키(`dup`)·닫히지 않은 `[`/`{`(`unclosed`)·보호 키(`visibility` 등)·정체성 키(`slug`,`type`,`id`,`source_id`)가 모호한 경우와 복구 불가는 `invalid_frontmatter`(사유 `yaml_parse`/`needs_interpretation`/`ambiguous_*`) 보류다. `import`는 보류 파일을 건너뛰고 사유를 알리며, 저널 경로(`put_page` 등)도 같은 보류를 `invalid_params`(`legacy_error`)로 거부한다. 보류가 아닌 읽기에서 닫히지 않은 펜스·복구 불가 YAML은 frontmatter `{}`·본문=전체로 읽힌다 (C-17, C-18, C-53) | 코드 확인 (js-yaml 부재로 `parseMarkdown` 전체는 실행 못 함, 복구 규칙은 `ruleFor`·`recoverFrontmatter`를 읽음) |
| R-11 | 파싱 결과 필드 | `type` = frontmatter `type` 문자열, 없으면 경로 접두 규칙(활성 스키마 팩이 있으면 팩의 `path_prefixes`, 없으면 내장 표 C-19), 그것도 없으면 `concept`. `title` = frontmatter `title`(trim) → 본문 첫 H1(코드 펜스 밖, `# ` 한 개) → 맨 앞 임베디드 펜스 안 `title:` → 파일명을 사람 읽는 이름으로(없으면 `Untitled`). `tags` = frontmatter `tags`(배열의 스칼라 원소 또는 쉼표 구분 문자열). `slug` = frontmatter `slug` 또는 경로에서 도출. 반환 `frontmatter`에서는 `type`·`title`·`tags`·`slug` 키를 뺀다(`comparableFrontmatter`). 결과 `compiled_truth`·`timeline`은 trim된다 (C-17, C-19) | 코드 확인 |
| R-12 | 본문을 `compiled_truth`와 `timeline`으로 나누는 규칙(`splitBody`) | 첫 구분자 줄 앞이 `compiled_truth`, 뒤가 `timeline`이고 구분자 줄은 버린다. 구분자는 코드 펜스 밖에서 우선순위 순으로: ① 줄 전체가 `<!-- timeline -->`(또는 `<!--timeline-->`) 또는 `--- timeline ---`(대소문자 무시) ② 줄 전체가 `---`이고 그 앞에 내용이 있고 다음 비어 있지 않은 줄이 `## Timeline` 또는 `## History`(대소문자 무시)일 때. **그냥 `---`는 가로줄이지 구분자가 아니다.** ③ 구분자가 없을 때만: 앞에 내용이 있는 첫 `## Timeline`/`## History` 제목 아래 구간이 날짜 글머리(`- 2024…` 형태 불릿, 들여쓴 이어쓰기 허용)만으로 된 경우, 그 구간(제목 줄 포함)만 `timeline`으로 옮기고 다음 H2부터는 `compiled_truth`에 남긴다. 위에 안 걸리면 `timeline=''`. 구분자 규칙 ②에서는 제목 줄(`## History`)이 `timeline` 쪽에 남는다 (C-52) | 실행 확인 (`demo-pure`: 구분 사례 9개) |
| R-13 | 파일·`export` 렌더(`serializeMarkdown`/`serializePageToMarkdown`) | `<frontmatter YAML>\n\n<compiled_truth>` + (timeline이 있으면 `\n\n<!-- timeline -->\n\n<timeline>`) + `\n`. frontmatter는 `type`, `title`, (태그가 있으면 `tags`), 그 뒤 저장된 frontmatter 키(예약 키 제외) 순이고, 슬러그가 경로로 되살릴 수 없거나(연속 하이픈 등) 저장된 `slug`가 다른 정체성이면 `slug:`를 찍는다. 렌더 결과는 같은 페이지로 다시 파싱된다(`slug` 줄은 파싱에서 버려지므로 정규 비교에 중립) (C-20) | 코드 확인 |
| R-14 | 입구 슬러그·크기 규칙(`put_page`·`capture`·업로드) | 슬러그는 1~255자, 분할은 `/`, 각 부분은 (글자(대소문자 무시)·`\p{M}`·`\p{N}`·`_`)로 시작하고 이후 `.`·`_`·`-` 허용, 한 부분 안에서 `:`로 이어 붙인 부분들이 가능(공백·역슬래시·`%2e`/`%2f`/`%5c`·제어문자·bidi·`..` 불가). 저장 시 소문자화. 새 슬러그가 `.md`/`.mdx`로 끝나거나(`<slug>.md.md` 방지), Windows 예약 이름·240바이트 초과 부분을 가지거나, 연속 하이픈·부분 끝 하이픈이 있으면(`hyphenFoldedSlug` 결과와 다르면) `invalid_params`로 거부하며 제안 슬러그를 준다(이미 그 슬러그를 가진 살아 있는 페이지는 경고만 하고 갱신 허용). 본문은 24 MiB(`PAGE_MAX_BYTES`)를 넘으면 접수 전에 `request_too_large`. 본문·제목에서 NUL을 제거하고 짝 없는 서로게이트를 U+FFFD로 바꾼다(`sanitizeText`) (C-21, C-22, C-23) | 코드 확인 |
| R-15 | `content_hash`와 건너뜀 | 해시 = `sha256(JSON.stringify({title, type, compiled_truth, timeline 없으면 '', frontmatter*, tags*}))`(필드 순서 고정). `frontmatter*`는 `captured_at`·`ingested_at`·`quarantine`·`content_flag`·`embed_skip`·`atoms_scan_hash`·`trust_tier`와 `tags` 키를 뺀 복사본, `tags*`는 정렬한 문자열 배열. 같은 `(source_id, slug)`의 살아 있는 행의 `content_hash`가 같고(그리고 강제 재청킹·투영 재구축·`embed_skip` 변화·신뢰 마커 변화가 없을 때) `import`는 `status:'skipped'`, 청크 0, 쓰기 없음(소스 경로 갱신만). 저널 경로는 해시가 아니라 정규 비교(R-06의 `canonical`)로 무변화를 판정해 `status:'skipped'`, `noop:true`를 내고 파일·effect를 만들지 않는다 (C-24, C-25, C-10) | 실행 확인 (`demo-pure`: 해시 불변·변화 조건) + 코드 확인 |
| R-16 | 태그와 타입 보존 | `import`(비저널)는 frontmatter 태그가 권위다: `tag_source='frontmatter'`인 행 중 frontmatter에 없는 것은 삭제하고 나머지를 `tag_source='frontmatter'`로 추가(`add_tag` 등이 만든 `added` 행·레거시 NULL 행은 지우지 않음). 저널 경로(`put_page` 등)는 **합집합만**이다: 저장된 태그 ∪ 새 frontmatter 태그를 정렬해 쓰고 태그를 지우지 않는다(`remove_tag`나 버전 되돌리기만 지운다). 기존 페이지는 새 내용에 명시적 `type:`이 없으면 저장된 `type`을 유지한다(경로 재추론 안 함). 명시적 frontmatter `type`은 덮어쓴다 (C-25, C-10) | 코드 확인 |
| R-17 | 청킹 입력과 출력 순서(마크다운) | 격리(`quarantine`) 페이지는 청크 0개. 그 밖에는 `compiled_truth`와 `timeline` 각각을 `chunkText`로 청킹한다. `chunkText`는 본문에서 `## Takes` 펜스를 통째로, `## Facts` 펜스는 `world` 가시성 행만 남기고 제거하고(`sanitizeRemoteBody`), PEM 개인키 구간을 `<REDACTED:private_key_pem>`+같은 줄 수의 개행으로 바꾼 뒤(`credentialSafeProjection`) 자른다. 출력 `ChunkInput`: `chunk_source` 순서 = `compiled_truth` 청크들 → `timeline` 청크들 → (인식된 언어 태그 코드 펜스의 `fenced_code` 청크들, 코드 청커 출력) → (신뢰 등급이 낮아 분리된 펜스 행의 표시된 청크, 지도 13행), `chunk_index`는 0부터 연속. 비어 있지 않은 청크마다 투영 텍스트의 UTF-8 바이트 구간(`projected_byte_start/end`)을 기록한다. 본문이 비면 청크 0개(`chunk_skip_reason:'empty_body'`) (C-26, C-27) | 코드 확인 + 실행 확인 (`demo-pure`: takes 제거) |
| R-18 | `chunkText` 알고리즘과 상수 | 단어 수(`countCJKAwareWords`) ≤ 300이면 전체가 한 청크. 아니면 ① 5단계 구분자로 재귀 분할(단락 `\n\n` → 줄 `\n` → 문장 `. ! ? .\n !\n ?\n`+CJK `。！？` → 절 `; : ,`+CJK `；：，、` → 공백/CJK 글자 단위) ② 조각을 탐욕적으로 합친다(한도 `ceil(300×1.5)=450`단어) ③ 청크 i(>0) 앞에 청크 i-1의 끝 50단어(문장 경계에 맞춰)를 붙인다(겹침) ④ 각 청크를 6000자·`maxTokens`(기본 2000, 추정 토큰)로 한 번 더 자른다(창 = 한도, 겹침 `min(500, 창/10)`). 단어 수는 CJK 글자가 비공백 문자의 30% 이상이면 비공백 글자 수, 아니면 공백 분리 토큰 수다. 청커 버전 `MARKDOWN_CHUNKER_VERSION=4`가 `pages.chunker_version`에 기록된다. 토큰 추정은 cl100k(tiktoken)이고 로드 실패 시 `ceil(글자수/4)` 폴백이며 CJK가 있으면 `max(추정, 글자 종류별 상한)` (C-26~C-29, C-31) | 실행 확인 (`demo-pure`: 단어 수·청크 크기·창) + 코드 확인 (tiktoken 경로는 실행 못 함) |
| R-19 | 청크 토큰 상한 `resolveMaxChunkTokens` | `GBRAIN_MAX_CHUNK_TOKENS`(양수면 64~2000으로 clamp) → 활성 임베딩 모델 레시피의 `max_input_tokens × 0.6`(64~2000 clamp) → 오류에서 학습한 모델별 상한 → 2000. 게이트웨이 미설정·모르는 provider는 2000 (C-30) | 코드 확인 |
| R-20 | 페이지·청크 행 기록(트랜잭션 안) | 기존 행이 있으면 먼저 `page_versions` 스냅샷(`createVersion`)을 남기고 `putPage`(`engine-and-schema`의 `ON CONFLICT (source_id, slug)` 갱신)로 `pages`를 쓴다(`compiled_truth`, `timeline`, `frontmatter`, `content_hash`, `effective_date*`, `import_filename`, `source_path`, 출처 열). `content_chunks`는 새 청크로 교체한다(`upsertChunks`는 페이지 단위 통째 교체, engine-and-schema 1.3): 같은 `chunk_source`·`chunk_text`이고 임베딩 입력(모델·차원·래퍼·입력 문자열)이 같은 기존 행은 그 벡터를 재사용하고 그 밖은 새로 INSERT한다(펜스 비공개 형제가 있는 페이지는 재사용 안 함). 같은 트랜잭션에서 태그(R-16)·별칭·본문의 `src/x.ts:42` 코드 참조 링크를 쓰고 `chunker_version`을 기록한다 (C-24, C-10) | 코드 확인 |
| R-21 | 청크 임베딩 호출 시점 | **`import`(비저널)**: 트랜잭션 전에 새로 필요한 청크 텍스트를 `embedBatch`(ai-gateway R-27)로 임베딩하고(문맥 래퍼가 켜진 페이지는 래퍼를 붙인 문자열), 성공한 벡터와 함께 기록한다. 임베딩이 통째로 실패하거나 일부 영벡터면 그 청크는 `embedding=NULL`로 저장하고 stderr에 `gbrain embed --stale` 안내를 쓴 뒤 import는 성공한다. `--no-embed`·`embed_skip` 페이지·1 MiB 초과 페이지는 임베딩하지 않고 NULL로 둔다. **`put_page` 등 저널 경로**: 준비 단계가 `noEmbed:true`로 청킹만 하고 NULL 벡터로 커밋하며, 임베딩은 커밋 뒤 `embedding` effect가 한다(R-22) (C-24, C-15) | 코드 확인 |
| R-22 | `embedding` effect | 커밋된 쓰기마다(변화 없음·삭제된 페이지 제외, `deferEmbedding` 아닐 때) `embedding` effect가 큐에 들어가고 `outcome.embedding_state`는 `queued`(임베딩 꺼짐이면 `disabled`)다. 실행 때 페이지 revision이 effect의 revision과 다르면 `superseded`로 끝낸다. 아니면 NULL 벡터 청크만 `embedBatch(…, {maxRetries:0})`로 임베딩해 revision이 같을 때만 설치하고(`installPageEmbeddings`, 청크·입력이 그새 바뀌었으면 일부만 설치하고 `superseded`) 페이지 `embedding_signature`를 찍는다. `embed_skip`이면 건너뜀, 영벡터가 나온 청크는 NULL로 두고 서명을 비워 `embed --stale`이 찾게 하며 effect는 `embedding_zero_norm`으로 종결 실패, 시도가 `MAX_RATE_LIMIT_RETRIES=5`를 넘으면 `embedding_attempts_exhausted`로 실패한다. effect 실패는 이미 커밋된 페이지·청크·영수증을 되돌리지 않는다(청크는 NULL 벡터로 남고 키워드 검색은 된다) (C-15, C-32) | 코드 확인 (백오프 시간·짧은 수명 CLI가 종료 전에 effect를 끝내는지는 미확인) |
| R-23 | 같은 트랜잭션의 파생 행(경계) | 발행 트랜잭션은 본문에서 `timeline_entries`(날짜 불릿·`### YYYY-MM-DD — …` 제목을 파싱, 행 키 `(date, source, summary)`), `## Facts` 펜스 → `facts`(`source_markdown_slug`+`row_num`), `## Takes` 펜스 → `takes`를 투영한다. 기존 타임라인 행의 삭제·갱신·본문에 되살림은 작성자 종류(editing/preserving/file/immutable)×행 상태 표(C-33)로 정해진다: 본문에서 지운 불릿의 행은 `put_page`가 지우고(타임라인 섹션이 아예 없는 본문은 로컬 preserving 작성자면 행을 본문으로 되살리고 `drop_timeline:true`면 지움), DB에만 있는 행은 editing·preserving 작성자가 본문에 불릿으로 되살려 쓴다. 로컬 신뢰 호출자는 같은 트랜잭션에서 자동 링크를 만들고 원격 호출자는 `links` effect(언급 링크)를 쓴다(`auto_link` 설정으로 끔). 사실 펜스 파싱·투영 규칙은 지도 12행 `fact-extraction` 스펙, 링크는 8행 스펙 소관 (C-33, C-10) | 코드 확인 (펜스 투영·링크 내부는 제외) |
| R-24 | 중복(정체성) 판정 | 같은 소스의 다른 슬러그에 같은 `content_hash` 또는 같은 frontmatter `id`가 있으면: `id`가 같고 내용(해시, 또는 제목·본문 동일)도 같고 기록된 원본 파일이 아직 있으면 `duplicate`(import는 건너뜀, `put_page`는 `status:'duplicate'`, `slug`=기존 페이지, 쓰기 없음); `id`가 같고 원본 파일이 사라졌거나 같은 파일의 다른 경로이면 `move`(import는 행 슬러그를 바꿈); `id`가 같지만 내용이 다르면(`shared_id`)·해시만 같으면(`shared_hash`) 경고하고 둘 다 색인한다. 강제 재청킹(`reindex`)은 이 검사를 건너뛴다 (C-34) | 코드 확인 |
| R-25 | `import`의 파일별 규칙(`importFromFile`) | 심볼릭 링크 → 건너뜀(`Skipping symlink`). 크기 > 24 MiB(코드 파일 5,000,000) → `file_too_large` 보류(분할 저장이 켜져 있으면 스트리밍 import로 위임, R-47). 파일명에 제어문자 또는 `.md`의 `[`·`]` → `malformed_path` 건너뜀(실패로 세지 않음). `invalid_frontmatter` 등 보류 코드는 건너뜀+사유. frontmatter가 없으면(첫 비공백 줄이 `---`가 아니면) 경로·내용에서 추론한 frontmatter를 메모리에서 앞에 붙인다(디스크 파일은 안 바뀜): 첫 일치 `DIRECTORY_RULES` 규칙(`apple notes/`, `docs/runbooks/`, `daily/calendar/` 등)의 type·source·tags, 없으면 `type: note`; 날짜는 파일명 `YYYY-MM-DD` 접두, 제목은 규칙에 따라 파일명 또는 첫 `#` 제목. 슬러그는 경로에서 `slugifyPath`로 도출하고 frontmatter `slug`와 다르면(정규화하면 같은 경우는 예외로 frontmatter 값 채택, 경로가 빈 슬러그면 frontmatter 값) `frontmatter_slug_conflict`로 건너뛴다. 빈 파일은 의도적 비우기로 보고 빈 덮어쓰기를 허용한다 (C-35, C-36) | 코드 확인 + 실행 확인 (`demo-pure`: `slugifyPath`) |

**C. 쓰기 저널**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | 단계 순서 | 입구 검사(`submitPageMutation`) → `preparePageAdmission`(예약 필드 거부, 크기 상한, `request_id`·`expected_revision` 파싱, 소스 활성 확인, 슬러그 검사·펜스, 이전 요청 조회, 캡처 가공, 편집·append 사전 검사, 파일 쓰기 결정) → `admitWrite`(`persistence_requests` INSERT) → 소비자 claim → `preparePageMutation` → `publishMutation`(R-04) → 후속 effect. `edit_page` 사전 검사는 접수 전에 `page_not_found`·`revision_conflict`·`edit_*`를 낼 수 있고 발행에서 같은 검사를 잠긴 스냅샷에 다시 한다. 입구 검사는 읽기 전용 캐시(pre-admission cache)를 쓸 수 있으나 접수 트랜잭션이 다시 확인하고 캐시가 원인인 거부는 캐시 없이 한 번 더 준비한다 (C-02, C-03, C-04) | 코드 확인 |
| R-31 | `request_id` | 생략하면 호출마다 새 UUID(재전송이 새 쓰기가 됨). UUID는 소문자로 통과, 그 외 1~128자 인쇄 가능 ASCII(공백 없음)는 고정 네임스페이스 아래 UUIDv5로 결정적 매핑되고 원문은 `client_request_id`로 영수증에 남는다. 그 밖(공백·129자 이상·비문자열)은 `invalid_params`. 키는 `(principal_kind, principal_id, request_id)`라 같은 호출자 안에서만 유일하다. 이전 요청이 있으면 권한을 다시 검사하고 `intentDigest`(operation, source_id, slug, `request_id`·`wait_ms` 제외 호출자 의도)를 비교해 같으면 새로 쓰지 않고 그 영수증을 기다려 돌려주고, 다르면 `idempotency_conflict`(이전 쓰기와 영수증은 그대로). 접수된 `request_id`와 영수증은 쓰기 한도(`lifetime_ids`)가 허용하는 한 지우지 않으며 영수증 압축은 `intent`만 비운다 (C-06, C-04) | 실행 확인 (`demo-pure`: 매핑·오류) + 코드 확인 |
| R-32 | `expected_revision`·`force` | `expected_revision`은 UUID여야 하고(아니면 `invalid_params`), `force`는 불리언이며 둘은 동시에 못 쓴다. 검사는 소비자 준비 단계와 발행 트랜잭션의 페이지 락 아래에서 각각 한다: `force:true`면 통과; 아니면 `현재 revision`(없으면 null)과 `expected_revision`(생략이면 null)이 같아야 한다. 어긋남의 코드: 페이지가 있는데 `expected_revision` 생략 → `revision_required`; 그 밖의 불일치(다른 값, 페이지가 없는데 값을 줌, 사이에 바뀜) → `revision_conflict`; 백필 안 된 행 → `revision_backfill_pending`. 이 코드들은 영수증 `state:'conflict'`로 종결된다. 병합형 쓰기(`add_tag`, `add_timeline_entry`, `takes_*`, `remember`, `force:true` 쓰기)는 `expected_revision`이 없을 때 준비 중 revision이 바뀌어도 새 페이지에 맞춰 다시 준비한다 (C-07, C-35, C-12) | 실행 확인 (`demo-pure`: `assertPageRevision` 코드 6사례) + 코드 확인 |
| R-33 | 접수 한도와 가드 | 접수 트랜잭션이 소스(활성·incarnation), 워크트리 소유, 권한을 확인하고 카운터 두 개(브레인, 호출자)를 잠가 다음을 검사한다: 미결 요청 수(호출자 100, 브레인 1000), 미결 의도 바이트(64 MiB, 256 MiB), 영구 요청 ID 수(2,000,000, 8,000,000), 영수증 예약 바이트(16 GiB, 64 GiB). 초과 시 `queue_capacity`(기다리면 풀림) 또는 `write_quota_exhausted`(호스트 설정 변경 필요). 통과하면 INSERT와 카운터 예약이 한 문장이다. 한도 숫자는 `persistence.limits.*` 설정으로 바뀐다 (C-05, C-04) | 코드 확인 |
| R-34 | 영수증과 대기 | 호출자는 접수 직후 `wait_ms`(CLI 30000, 에이전트·서버 5000, 설정 `persistence.write_wait_ms`·환경 `GBRAIN_WRITE_WAIT_MS`) 동안 요청이 종결되길 기다린다. `committed`면 `{...영수증, write_request: 영수증}`을 반환한다. 종결 실패(`conflict`/`failed`/`cancelled`)나 아직 종결 아님은 오류로 던진다: 종결 실패는 `error_code`(예: `revision_conflict`, `source_changed`, `invalid_params`, `storage_error`), 대기 시간 초과는 `write_pending`("accepted and still pending", `retry_after_ms`·진단 포함, 쓰기는 계속됨). 오류에는 `writeRequest`(영수증)가 붙는다. `blocked_reason`이 `recovery_required`·`owner_unavailable`·`unexpected_file_bytes`·`unexpected_staging_bytes` 중 하나면 기다리지 말고 소유 호스트 점검이 필요하다는 뜻이다. 코드 목록은 C-06 (C-06, C-07, C-08) | 코드 확인 |
| R-35 | 실패 종류별 사후 상태 | ① 입구에서 거부(슬러그·크기·예약 필드·권한·비활성 소스·`unbound_source`·`.md` 접미 등): 행이 안 생기고 아무것도 안 바뀐다, 호출자가 오류를 바로 받는다. ② 접수 후 준비·발행 전 거부(`revision_*`, `page_not_found`, `source_changed`(drift·점유·루트 밖), `invalid_params`, 내용 보류, `edit_*`): 요청이 종결(`conflict`: `revision_required`/`revision_conflict`/`revision_backfill_pending`/`source_changed`/`page_identity_changed`, `failed`: 그 밖, `cancelled`: `admission_paused`)되고 페이지·파일은 변하지 않으며 영수증이 남는다. ③ 파일 교체 뒤 실패: R-05(파일 복원, DB 롤백). ④ 발행 후 effect 실패: 영수증은 `committed` 그대로이고 effect만 `failed`/보류. ⑤ 같은 `request_id`·다른 내용: 접수 거부 `idempotency_conflict`. ⑥ 커밋 결과가 불확실한 채 DB가 끊김: 요청은 `recovering`이며 복구 기록이 남아 다음 소유 루프가 마무리한다. 접수 거부(`queue_capacity` 등) 후에는 같은 `request_id`로 재시도해도 안전하다 (C-09, C-10) | 코드 확인 |
| R-36 | 변화 없는 쓰기 | 새 내용의 정규 비교가 저장된 페이지와 같고 삭제 상태도 같으면(단 R-32의 revision 검사는 먼저 적용) `status:'skipped'`, `noop:true`, `chunks:0`, `chunk_skip_reason:'write_skipped'`로 `committed`가 되고 파일 교체·effect·`knowledge_revision` 변화가 없다 (C-10) | 코드 확인 |
| R-37 | 호출자 구분(`ctx.remote`) | `remote`가 엄격히 `false`일 때만 신뢰(로컬 CLI). 원격 호출자는 쓰기 소스가 인증 그랜트의 소스와 같아야 하고(아니면 `permission_denied`), `source_kind`/`source_uri`/`ingested_via`는 `mcp:<operation>`/null/`mcp:<operation>`으로 덮이고, 기존 본문이 256 KiB 초과면 `expected_revision` 필수(`force` 불가)와 "기존 본문의 50% 미만으로 줄이기"는 `allow_shrink:true` 없이 `page_shrink_refused`, 사용자 접근이 가려진 펜스 행은 되살려 병합(R-23 경계), 자동 링크 대신 `links` effect, `capture`의 `local_file`은 거부 (C-01, C-03, C-37) | 코드 확인 |

**D. 연산별 차이** (대표는 `put_page`: R-30~R-37과 같은 저널·영수증·충돌 규칙을 쓰고 아래만 다르다)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | `edit_page` | `expected_revision` 필수. 호출자의 보기(원격이면 가려진 본문)에서 `edits`를 앞에서부터 순서대로, 각 `old_text`가 **정확히 한 곳**에서 일치해야 하며 전부 적용되거나 전혀 적용되지 않는다(1~50개, `old_text` 비어 있으면 `edit_invalid`). 0곳 `edit_no_match`, 2곳 이상 `edit_ambiguous_match`, 보호 펜스(`## Facts`·`## Takes`)에 닿거나 `new_text`에 펜스 마커가 있으면 `edit_protected_span`/`edit_invalid`. `within`은 stored-body 바이트 범위 안에서만 일치를 허용. 깨진 펜스가 있는 페이지는 `edit_page`가 안 고치고 타입 있는 거부. 결과는 canonical 내용을 `put_page`처럼 발행하고 영수증에 통합 diff(최대 8 KiB, 시크릿 가림)를 담는다. 페이지가 없거나 삭제 상태면 `page_not_found` (C-38) | 코드 확인 |
| R-41 | `append_page` | `request_id` 필수, `text`는 비어 있지 않은 4 MiB 이하, NUL·짝 없는 서로게이트·펜스 마커·타임라인 구분자 줄이 있으면 `invalid_params`. 기존 페이지가 필수. `region` auto는 마지막 비어 있지 않은 영역(truth/timeline)에 붙이고 `separator` auto는 끝에 개행이 없으면 하나 넣는다. `expected_revision` 불일치 `revision_changed`, `expected_tail_sha256`(영역 마지막 ≤4096바이트의 sha256, `none`은 빈 영역) 불일치 `tail_changed`. 인라인 페이지는 새 본문을 만들어 `put_page` 발행 경로를 타고(임계 초과 시 분할 저장으로 승격), 분할 페이지는 마지막 세그먼트만 다시 나눈다(R-47). 준비 중 페이지가 움직이면 새 꼬리에 맞춰 다시 준비한다(`revision_conflict`에 한함). 원격 호출자가 truth에 덧붙이면 덧붙인 바이트만 보는 `links` effect를 큐에 넣는다 (C-39) | 코드 확인 |
| R-42 | `put_pages` | 1~50쪽, 내용 합계 ≤ 8 MiB(초과·형식 오류는 아무것도 안 쓰고 `invalid_params`), `request_id` 필수. 각 쪽은 `put_page`로 준비·접수되고 자식 `request_id`는 `UUIDv5(네임스페이스, "put_pages:v1:<배치id소문자>:<index>")`이며 한 트랜잭션에서 한꺼번에(또는 동일 authority 묶음별로) 접수되어 용량은 전체 아니면 전무다. 같은 슬러그(대소문자 무시)가 여러 쪽에 있으면 내용·옵션이 같은 반복은 한 번만 쓰고, 다르면 해당 쪽들 모두 거부(나머지는 기록). 같은 `request_id`로 크기가 다른 재호출·내용이 다른 재호출은 `idempotency_conflict`. 응답은 배치 영수증 `{batch_request_id, state: pending/committed/partial/failed, terminal, counts{total,committed,pending,failed}, next, links, pages[{index, slug, state, revision, status, error…}]}`. `pages` 없이 `request_id`만 주면 상태를 읽는다(없으면 `not_found`). 배치의 마지막 쪽이 끝나면 앞 쪽들의 `links` effect를 한 번 다시 건다(앞 쪽이 뒤 쪽을 참조하는 `[[링크]]` 해소) (C-40) | 코드 확인 |
| R-43 | 분할 업로드(1회 요청에 안 들어가는 페이지) | `begin_page_upload{slug, mode: create/replace/append, total_bytes, sha256, request_id, expected_revision?}`: `replace`는 `expected_revision` 필수, `create`는 불가·기존 페이지가 있으면 `revision_required`, `replace`/`append`는 페이지가 있어야 한다. 같은 `request_id`·같은 인자로 다시 부르면 세션을 재개하고 인자가 다르면 `idempotency_conflict`. `upload_page_part{upload_id, part, text, part_sha256}`: `part`는 `next_part`와 같아야 하고(이미 받은 조각은 같은 해시면 성공, 다르면 `idempotency_conflict`), 프레임(호출 JSON)은 `part_max_frame_bytes`(≤ 4 MiB − 4096) 이하, 누적이 `total_bytes`를 넘으면 거부. `commit_page_upload{upload_id, allow_empty?, allow_shrink?, drop_timeline?, content_origin?, wait_ms?}`: 받은 바이트가 선언과 같아야 하고 전체 sha256이 선언과 같아야 한다(다르면 세션 폐기, 아무것도 안 씀). 통과하면 `body_ref`(스테이징 참조)로 일반 `put_page`(`mode:append`는 `append_page`)를 접수한다: `request_id`는 세션의 `request_id`이고 영수증은 그 쓰기의 것이다. 세션은 유휴 1시간·하드 24시간에 만료, `abort_page_upload`로 폐기. `total_bytes`가 24 MiB를 넘는 `create`/`replace`는 분할 저장 정책의 `pages.max_bytes` 이내에서만 허용(R-47), `append`는 24 MiB 이하. 원격 호출자는 쓰기 게이트가 적용되면 24 MiB 초과를 거부한다 (C-41) | 코드 확인 |
| R-44 | `capture` | `content`가 비어 있거나(정규화 후) 앞 8 KiB에 NUL이 있으면 `invalid_params`. 슬러그 기본값은 `<접두>/<YYYY-MM-DD(UTC)>-<sha256(normalizeForHash(content)) 앞 8자>`, 접두는 `inbox`(`type:diary` → `life/diary`, `type:event` → `life/events`). `normalizeForHash` = BOM 제거·CRLF→LF·trim·NFKC. `content`는 frontmatter 병합을 거쳐 `put_page` 내용이 된다: 기존 frontmatter가 없으면 `type`(기본 `note`)·`title`(첫 비어 있지 않은 줄에서 `#` 제거, 80자 제한, 없으면 `Capture`)·`captured_via`(`capture-cli`/`capture-mcp`)·`captured_at`(지금)을 찍고 `#` 제목이 없으면 본문 앞에 `# <title>`을 붙인다; 있으면 한 블록으로 병합(`type`은 호출 인자 > 기존 > `note`, `title`·`captured_via`·`captured_at`은 기존 값 우선). 기존 `type` 선언이 스키마 팩의 선언 밖이면 거부. 그 뒤는 `put_page`와 같다(기존 슬러그를 덮으려면 `expected_revision` 또는 `force`, 같은 날 같은 내용 재캡처는 `revision_required`). 영수증에 `channel:'capture'`, `content_hash`(= `sha256(normalizeForHash(content))`)가 붙는다. 로컬 CLI의 `--file`은 파일이 소스 루트 안의 `.md`이고 슬러그가 그 경로의 슬러그와 같을 때만 그 파일을 페이지의 원본으로 묶고, 아니면 `source_uri:'cli-file'`만 남긴다 (C-42, C-43) | 코드 확인 + 실행 확인 (`demo-pure`: 슬러그·정규화·제목, `computeContentHash`는 `Bun` 대신 node sha256으로 대체) |
| R-45 | `add_tag` / `remove_tag` | 빈 태그는 `invalid_params`. 현재 태그에 `trim`한 태그를 합치거나(정렬) 뺀 집합으로 페이지를 `put_page` 경로로 다시 발행한다(파일 포함). 청크 본문이 안 바뀌므로 `embedding` effect를 큐에 넣지 않는다(`deferEmbedding`). `expected_revision`이 있으면 검사하고 없으면 현재 페이지에 병합한다(R-32). 분할 저장 페이지는 본문을 안 읽는 메타 뒤집기로 처리 (C-44) | 코드 확인 |
| R-46 | `add_timeline_entry` | `date`는 엄격한 `YYYY-MM-DD`(연 1900~2199, 실제 달력 날짜), `summary`는 한 줄·비어 있지 않고 마크다운 목록·제목 문법이 없어야 한다(왕복 불가면 `invalid_params`). 항목은 불릿으로 렌더되어 `timeline`의 날짜 위치에 끼워 넣어지고 페이지가 발행되며 같은 트랜잭션에서 `timeline_entries`에도 들어간다. 이미 같은 불릿이 있으면 `status:'skipped'`, `reason:'duplicate'`; 같은 `(date, source, summary)`가 다른 `detail`로 있으면 `invalid_params`. 커넥터·dream·크로니클 페이지처럼 스스로 본문을 재생성하는 작성자 소유 페이지에는 구체화 마커를 붙여 재생성이 지우지 않게 한다. 기록 후 쓰기 게이트가 `reject`/`quarantine`이면 거부 (C-44, C-33) | 코드 확인 |
| R-47 | 1 MiB 초과 본문(분할 저장) 경계 | 본문(compiled_truth+timeline)이 1 MiB(`PAGE_INLINE_MAX_BYTES`)를 넘으면 "큰 페이지"다: 임베딩은 쓰기와 같은 호출에서 하지 않고 NULL 벡터로 커밋한 뒤 stale 스윕·effect가 채운다(R-21). `pages.segmented_storage` 스위치가 유효하면(설정값 `on`, 또는 미설정이면 코드 기본 `on`이고, 최근 7일 안에 분할 저장을 읽지 못하는 옛 버전 작성자가 이 브레인에 쓴 흔적이 없을 때) 1 MiB 초과 본문은 `body_storage='segmented'`로 승격되어 세그먼트로 저장되고(`compiled_truth`·`timeline` NULL, 512 KiB 이하로 줄면 인라인으로 강등) 허용 본문 한도가 `pages.max_bytes`(기본 Postgres 256 MiB, PGLite 128 MiB)로 올라가며 청크·임베딩은 쓰기 뒤에 만들어져 영수증에 `projection:'pending'`/`searchable:'pending'`이 보일 수 있다. 스위치가 꺼졌거나 막히면 인라인 24 MiB가 상한이다. 세그먼트 분할·매니페스트·스트리밍은 이 스펙 밖 (C-45, C-46) | 코드 확인 (스위치 효과의 실제 동작은 실행 못 함, 문서 문구와 코드 기본값이 다름: 2.1) |

**E. 명령**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | `import` 시작과 파일 수집 | `--no-embed`가 없으면 `embedding_disabled`(deferred-setup) 브레인은 거부(`--json`이면 `embedding_disabled` 오류에 `--no-embed` 재실행 안내)하고 임베딩 자격 증명이 모자라면(`validateEmbeddingCreds`, ai-gateway R-26) 중단한다. 대상: 위치 인자 `<dir>`(없으면 사용법 출력 후 중단), 실제 경로로 정규화. 소스: `--source`/`--source-id`(둘 다 주면 값이 같아야 함, `__all__` 불가) > 환경 `GBRAIN_SOURCE` > 해석 단계 중 단독 비기본 소스 자동 선택 > `default`. 수집(`collectSyncableFiles`): git 작업트리면 `git ls-files --cached --others --exclude-standard`(tracked+untracked-not-ignored; `--include-gitignored`면 파일시스템 순회), 아니면 재귀 순회. 포함 조건: 확장자 `.md`/`.mdx`(소문자 정확 일치), 심볼릭 링크·비정규 파일 제외, 점으로 시작하는 경로 조각·`node_modules`·`vendor`·`dist`·`build`·`venv`·`.raw`·`*.raw` 제외(깊이 32 한도), 메타파일(`schema.md`, `index.md`, `log.md`, `README.md`, `RESOLVER.md` 어디서나, 루트의 `AGENTS.md`·`CLAUDE.md`)은 건너뜀(단 중첩 메타파일의 frontmatter에 `type:`/`title:` 값이 있으면 페이지로 가져옴, 설정 `sync.metafile_pages` 기본 `typed`), 파일명에 제어문자·`[`/`]`가 있으면 제외하고 개수·이름을 알린다. 목록은 정렬 후 최신 파일 먼저로 재정렬한다. 설정 `import.require_configured_root=true`면 대상이 소스의 등록 루트 안이어야 한다(`--allow-noncanonical-root`로 우회). `--workers N`(기본 1)은 Postgres+`database_url`일 때만 병렬(PGLite는 직렬) (C-47, C-48, C-49) | 코드 확인 |
| R-51 | `import` 진행·결과 | 파일마다 R-25 → R-15~R-24. 상태: `imported`(청크 수 합산), `skipped`(`unchanged`·`slug_collision`·보류·`malformed_path`), 오류는 `errors`·`failures[{path,error}]`. 체크포인트 `~/.gbrain/import-checkpoint.json`에 성공 경로를 100개마다·2분마다 저장하고 실패가 없으면 끝에서 지운다(`--fresh`이거나 관리 모드면 불러오지 않아 재개 안 함; 재개해도 파일은 해시로 다시 판정). 변화가 있거나 오류·청크가 있으면(`--log-noop`이면 항상) `ingest_log`에 `source_type:'directory'` 한 줄. R-08의 git 앵커 설정. 최종: `status`(`success`/`partial`), 사람용 요약(`N pages imported`, `N pages skipped (…)`, `N chunks created`). 중단(AbortSignal)이면 지금까지 성공한 경로를 보존하고 `ImportAbortError`. 관리 모드 브레인이면 파일을 `managed_file_import` 저널 요청으로 바꿔 접수하고(최대 32쪽·8 MiB씩 묶음) 체크포인트를 불러오지 않으며 git 앵커·`last_sync_at`을 쓰지 않는다 (C-47, C-29) | 코드 확인 |
| R-52 | `embed` | 사용법: `embed <slug>`, `--all`, `--stale`, `--slugs s1 s2 …`, `--held`, `--facts`, `--images`. 임베딩 꺼짐·자격 증명·차원 불일치는 실행 전에 거부하고(`--dry-run`은 생략) `--stale`만 있고 임베딩이 꺼진 브레인은 아무것도 안 하고 0 결과. 대상 페이지의 청크 중 벡터가 NULL(`embedded_at` 없음 또는 `embedding_is_null`)인 것만 임베딩하고(`--all`은 전부), `embed_skip` 페이지는 건너뛴다. 청크가 없는 페이지는 먼저 본문을 청킹해 청크를 만든다. 임베딩 입력은 페이지가 저장한 래핑 방식을 그대로 쓰고 호출은 ai-gateway `embedBatch`(실패 시 한 청크씩 격리 재시도, 영벡터 청크는 NULL 유지)로 한다. 설치는 revision이 그대로일 때만(페이지 가드 아래)이고 전부 성공하면 `embedding_signature`를 찍는다. `--stale`은 먼저 모델·차원 서명이 현재와 어긋난 페이지의 벡터를 NULL로 되돌린 뒤(임베딩 호출이 되는지 시험 호출로 확인한 뒤에만) 같은 경로로 채우고, 소스별 단일 실행 락을 잡으며 기본 시간 예산 30분(`GBRAIN_EMBED_TIME_BUDGET_MS`, `--catch-up`은 무제한), `--batch-size`(1~10000, 기본 2000), `--priority recent`. `--dry-run`은 호출·쓰기 없이 `would_embed`를 센다. 실패가 있으면 `failures`>0이고 CLI가 비0 종료. 유료 실행은 동의(`--yes`/`--max-usd N`)·비용 상한 대상(지도 37행 `embedCostCap`, ai-gateway R-68) (C-50) | 코드 확인 |
| R-53 | `export` | 읽기 전용 REPEATABLE READ 트랜잭션에서 `deleted_at IS NULL` 페이지를 id 순으로 읽는다. `--source`가 없으면 모든 소스, `--type`·`--slug-prefix`(리터럴 접두)로 좁힌다. 출력 파일 = `<slug>.md`(`serializeMarkdown`: R-13과 같은 렌더, 태그는 DB `tags`), `raw_data`가 있으면 `.raw/<leaf>.json` 사이드카. 슬러그가 파일 이름이 못 되면(`:`, Windows 예약 이름, 끝의 점·공백) `~`로 이스케이프한 이름과 `slug:` 줄(가져오기가 슬러그를 복원), 240바이트 초과 부분은 해시 접미사로 줄이고 가져오기가 거부한다. 경로가 대소문자·유니코드·접두 별칭 포함 충돌하면 전부 나열하고 **아무것도 게시하지 않는다**(소스별로 나눠 내보내기). 출력 디렉터리는 덮어쓰지 않는다(`--force` 없음), 예약 파일 `.gbrain-export-status`는 불완전으로 시작해 성공 게시 후에야 `COMPLETE`로 끝난다. 페이지 한 개가 32 MiB(분할 페이지는 엔진 상한 기반)를 넘거나 스냅샷 시간(10분+스트림 시간)이 넘으면 전체 실패. `--restore-only`는 저장소의 `gbrain.yml` 스토리지 설정에서 `db_only`인데 파일이 없는 페이지만 `--repo`/`--dir`로 복원한다. "DB 백업이 아니다": 삭제된 페이지·이력·영수증은 안 나간다 (C-51) | 코드 확인 |

**F. 경계 한 줄**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 마크다운의 `## Facts` 펜스(`<!--- gbrain:facts:begin -->`…`end -->`) | 이 스펙의 파이프라인에서 갈라지는 지점은 두 곳이다: (1) 청킹 직전 `sanitizeRemoteBody`가 펜스에서 `world` 가시성 행만 남기므로 비공개 사실은 `content_chunks`·임베딩에 안 들어간다(R-17). (2) 발행 트랜잭션의 `prepareCanonicalProjections`(C-33)가 펜스를 파싱해 `facts` 행으로 투영한다. 그 파싱·행 키·`row_num`·만료·가드는 지도 12행 `fact-extraction` 스펙으로 넘긴다 | 코드 확인 (경계만) |

- 불변식: (1) 파일을 쓰는 발행에서 파일 교체는 항상 DB 트랜잭션이 열린 뒤, 모든 가드·revision 검사를 통과한 뒤에 일어나고, 영수증 `committed`는 DB 커밋과 한 몸이다. (2) 파일이 DB 행과 다르면(밖에서 편집됨) 저널 쓰기는 어느 쪽도 덮어쓰지 않고 거부한다. (3) 같은 `(principal, request_id)`는 하나의 쓰기만 만든다. (4) 저널 경로의 `put_page`는 태그를 지우지 않는다. (5) `content_chunks`에서 `(page_id, chunk_index)`는 유일하고 페이지 단위로 통째 교체되며 청크 벡터가 NULL인 동안에도 키워드 검색은 된다(engine-and-schema 1.3).
- 미결정: 없음.
- 확인 한계:
  - `bun`이 없어 `agent-memory/repos/gbrain`을 실제로 실행하지 못했다. `parseMarkdown`·`importFromContent`·저널 경로는 `js-yaml`·`gray-matter`·DB 의존 때문에 실행하지 않았다. 실행 확인은 `deno`로 순수 함수만이다(`agent-memory/artifacts/gbrain/page-import-demos/`): `splitBody`(줄 범위를 잘라 실행), `chunkText`(실제 `chunkers/recursive.ts`), `contentHash`·`HASH_EPHEMERAL_FRONTMATTER_KEYS`(`utils.ts`), `parseWriteRequestId`·`parseMutationPrecondition`(`preconditions.ts`), `assertPageRevision`(`page-state/types.ts`), `slugifyPath`·`hyphenFoldedSlug`(`sync.ts`), capture 보조 함수(줄 범위를 잘라 실행하고 `Bun.CryptoHasher`만 node sha256으로 대체). 토큰 추정은 `@dqbd/tiktoken`이 없어 `len/4` 폴백으로 돌았으므로 영어 일반 텍스트의 청크 경계는 확인했지만 토큰 한도(2000)가 실제로 먼저 걸리는 경계는 확인하지 못했다.
  - 저널 소비자·복구·effect 실행기·분할 저장·관리 모드 import/sync·쓰기 게이트·펜스 정규화·링크 추출·`engine.putPage`/`upsertChunks`의 SQL은 읽지 않았다. 읽은 범위: `ops/pages.ts`(put/capture 정의), `page-mutations.ts` 전체, `journal.ts`의 접수·영수증·`completeWrite`, `service.ts` 전체, `coordinator.ts`의 `publishMutation`·실패 매핑·복구 기록, `page-prepare.ts` 전체, `effect-journal.ts`의 큐 등록, `effects.ts`의 `embedPage`, `effect-git.ts`의 `publishGitEffect`와 `stageTarget`, 각 연산 파일(`edit`·`append`·`batch`·`upload`·`tags`·`timeline`·`capture`)의 정의와 핵심 준비 함수. 미탐색: `consumer.ts`, `effect-recovery*.ts`, `recoverPublication` 이후 세부, `page-body/*`, `import-prepare.ts`, `sync-prepare.ts`, `links-preparation.ts`, `write-gate*`, `fence-repair/*`, `trust/*`.
  - 짧게 사는 CLI(`gbrain put`)가 종료 전에 큐에 든 `embedding` effect를 끝내는지(소비자 `stop()`이 진행 중 effect 작업을 기다리는 호출 `consumer.ts:1160`만 확인)와 영수증 보존 기간 기본값·`intentDigest`의 해시 함수(`digest.ts`)는 확인하지 못했다. 구현자는 어떤 결정적 해시를 써도 되고(요청 비교용), 임베딩이 effect 종료 전에 빠지면 NULL 벡터가 `embed --stale`로 채워진다는 계약만 지키면 된다.
  - PGLite 자동 claim이 이후 classic `sync`를 막는지(`unboundSourceError`의 안내문은 관리 모드가 아니면 claim이 classic sync를 막는다고 말하지만 PGLite 자동 claim 경로에서의 실제 효과는 미확인)와 `claimWorktree`의 관리 모드 분기(`runManagedSourceLifecycle`)는 열지 않았다.
  - `docs/architecture/system-of-record.md`는 도입부만 읽었고 코드로 다시 확인한 사실만 채택했다.

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 인용 가능. 줄 번호는 기준 SHA.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/ops/pages.ts:332-373` `put_page`; `687-720` `capture` | 연산 파라미터·입구 순서(dry-run, 원격 대형 페이지 가드, `submitPageMutation`) | R-01, R-37 |
| C-02 | `src/core/persistence/page-mutations.ts:216-247` `submitPageMutation`; `132-144` `pageMutationSource`; `46-59` | 입구, 캐시 재시도, 대기, 소스 쓰기 그랜트 | R-01, R-30, R-37 |
| C-03 | `src/core/persistence/page-mutations.ts:254-436` `preparePageAdmission` | 접수 전 검사 전부, 파일 쓰기 결정(389-431), `edit_page`·`append_page` 사전 검사 | R-02, R-30, R-35, R-37 |
| C-04 | `src/core/persistence/journal.ts:208-213, 232-254, 259-332` `getWriteRequest`·`intentDigest`·`assertReplayIntent`·`admitWrite`·`prepareAdmission` | 이전 요청 조회, 재전송 비교, 접수 가드 순서, 한도 검사, INSERT+예약 | R-30, R-31, R-33 |
| C-05 | `src/core/persistence/schema.ts:113-220`; `src/core/persistence/model.ts:5-141`; `src/core/persistence/effect-model.ts:67-109` | 저널 테이블 DDL(최초), `WriteRequest`·`WriteAuthority`·`RequestState`·`DEFAULT_JOURNAL_LIMITS`, `PersistenceEffect` | R-01, R-33 |
| C-06 | `src/core/persistence/preconditions.ts:9-71`; `src/core/persistence/types.ts:2-26` | `request_id` 매핑(UUIDv5 네임스페이스), `expected_revision`·`force` 파싱, 상태·오류 코드 목록 | R-31, R-32, R-34 |
| C-07 | `src/core/page-state/types.ts:84-125`; `src/core/persistence/write-wait.ts:17-27` | `PageRevisionConflictError` 코드 결정, `assertPageRevision`, 대기 기본값 | R-32, R-34 |
| C-08 | `src/core/persistence/page-prepare.ts:253-379` `prepareFileTarget`·`compareFileTarget`; `121-124` `canonical`; `159-162` | 파일 대상 결정·비교·거부 | R-03, R-06 |
| C-09 | `src/core/persistence/coordinator.ts:442-659` `publishMutation`; `396-414` `pageRecoveryRecord`; `197-218` | 발행 순서, 복구 기록, 실패 코드→상태 | R-04, R-05, R-35 |
| C-10 | `src/core/persistence/page-prepare.ts:681-990` `preparePageMutation`·`prepareInlineOrSegmentedMutation` | 준비·무변화 판정(801-811)·임포트 호출(822-845)·태그 합집합(876)·파일 렌더(878)·`apply`(916-990)·영수증 `outcome` | R-15, R-16, R-20, R-21, R-35, R-36 |
| C-11 | `src/core/persistence/unbound-source.ts:104-124` `decideUnboundWrite`; `src/core/persistence/ownership.ts:86-131` `claimWorktree` | 바인딩 없는 소스의 쓰기 규칙, 자동 claim | R-02 |
| C-12 | `src/core/persistence/coordinator.ts:373-384` `decoratePublicationOutcome`; `src/core/persistence/semantic.ts:6-30` `mayReprepare` | 영수증 `persistence`·`write_through`, 병합 쓰기 재준비 | R-02, R-32 |
| C-13 | `src/core/markdown.ts:1450-1496` `resolveSourceLocalFilePath`; `src/core/write-through.ts:256-273` `scannerSourcePath` | 기록된 `source_path` → 디스크 경로, 경로 → `source_path` | R-03 |
| C-14 | `src/core/persistence/effect-journal.ts:26-71` `queuePublicationEffects` | 큐에 들어가는 effect 종류와 조건 | R-07, R-22 |
| C-15 | `src/core/persistence/effects.ts:438-564` `embedPage`; `606-610` `exhaustEmbedding`; `src/core/embed-retry.ts:75` | 임베딩 effect | R-21, R-22 |
| C-16 | `src/core/persistence/effect-git.ts:396-415` `publishGitEffect`; `src/core/persistence/effects.ts:813-815`; `src/core/persistence/git-durability-policy.ts:31-45` | 커밋 조건(내구 정책) | R-07 |
| C-17 | `src/core/markdown.ts:318-331` `parseMarkdown`; `354-445` `parseMarkdownHead`; `203-222`; `src/core/data-frontmatter.ts:97-150` | frontmatter 읽기·언어 선택자·자동 따옴표 | R-10, R-11 |
| C-18 | `src/core/data-frontmatter.ts:1-96` | 달력 검증 타임스탬프, 별칭 확장 한도 | R-10 |
| C-19 | `src/core/markdown.ts:448-487` `parsedMarkdownFields`; `1070-1093, 1095-1097, 1114-1133, 1212-1224`; `1235-1279`; `1302-1307` | 타입·제목·태그·슬러그 도출, 내장 경로 접두 표, 예약 키 | R-11 |
| C-20 | `src/core/markdown.ts:1014-1038` `serializeMarkdown`; `1332-1371` `serializePageToMarkdown`·`slugStampedFrontmatter` | 렌더 포맷 | R-13, R-53 |
| C-21 | `src/core/ops/context.ts:190-237` `validatePageSlug`·`OP_PAGE_SLUG_RE`; `src/core/cjk.ts:43` `SLUG_WORD_CHARS`; `src/core/utils.ts:39-60` `validateSlug` | 슬러그 문법 | R-14 |
| C-22 | `src/core/persistence/suffixed-slug.ts:1-80`; `src/core/sync.ts:710-773` `slugifySegment`·`hyphenFoldedSlug`·`slugifyPath` | 새 슬러그 거부 규칙, 경로 → 슬러그 | R-14, R-25 |
| C-23 | `src/core/batch-rows.ts:70-100` `sanitizeText`; `src/core/page-size-policy.ts:16-39`; `src/core/import-screen.ts:42-46` | 정제, 크기 상수, 파일 크기 한도 | R-14, R-25 |
| C-24 | `src/core/import-file.ts:355-379, 513-529, 548-629, 633-723, 733-888` `importFromContent` | 화면 검사·정제·해시·건너뜀·청킹·임베딩·트랜잭션 기록 | R-15, R-20, R-21 |
| C-25 | `src/core/utils.ts:70-150` `HASH_EPHEMERAL_FRONTMATTER_KEYS`·`contentHash`; `src/core/import-file.ts:476-484, 819-830` | 해시 정의, 타입 보존, 태그 권위 | R-15, R-16 |
| C-26 | `src/core/markdown-chunks.ts:148-200` `overlaidChunks`·`prepareMarkdownChunks`; `src/core/chunkers/recursive.ts:110-161` `chunkText`·`chunkProjectedText` | 청크 순서·출처·투영 | R-17, R-18 |
| C-27 | `src/core/remote-body.ts:1-46` `sanitizeRemoteBody`; `src/core/credential-projection.ts:17-31` | 청킹 전 투영 | R-17 |
| C-28 | `src/core/chunkers/recursive.ts:50-56, 284-336, 357-578` | 구분자 표, 상한(`capByChars`), 재귀 분할·병합·겹침 | R-18 |
| C-29 | `src/core/cjk.ts:72-187` `countCJKAwareWords`·`wordStats`; `src/commands/import.ts:1030-1108` | 단어 수 정의, import의 git 앵커 설정 | R-18, R-08 |
| C-30 | `src/core/embedding-input-limit.ts:34-37, 95-128` `resolveMaxChunkTokens`; `src/cli/main.ts:1090-1135` | 청크 토큰 상한, CLI 플래그 이름 규칙 | R-19, 1.3 |
| C-31 | `src/core/chunkers/token-estimate.ts:20-237` | 토큰 추정 | R-18 |
| C-32 | `src/core/import-file.ts:660-724` `embedChunks`; `src/commands/embed.ts:1100-1265` `embedPage` | 인라인·수동 임베딩 | R-21, R-52 |
| C-33 | `src/core/persistence/canonical-projections.ts:58-118` `TIMELINE_DECISIONS`·`timelineRowAction`; `119-136`; `489-570` `compileCanonicalProjections`·`prepareCanonicalProjections` | 타임라인 행 처리 표, 펜스 투영 진입 | R-23, R-46, R-60 |
| C-34 | `src/core/import-identity.ts:49-94` `decideImportIdentity`·`hasMoveEvidence` | 중복·이동 판정 | R-24 |
| C-35 | `src/core/import-file.ts:1015-1203` `importFromFile` | 파일별 import 규칙 | R-25, R-32 |
| C-36 | `src/core/frontmatter-inference.ts:96-209, 276-336, 418-425` | 경로 규칙 표와 추론 | R-25 |
| C-37 | `src/core/persistence/large-page-guard.ts:18-69` | 큰 페이지 교체 가드 | R-37 |
| C-38 | `src/core/ops/page-edit.ts:1-60`; `src/core/persistence/page-edit.ts:41-100, 194-261, 347-373` | `edit_page` 규칙 | R-40 |
| C-39 | `src/core/ops/page-append.ts:1-55`; `src/core/persistence/page-append.ts:66-160, 370-435` | `append_page` 규칙 | R-41 |
| C-40 | `src/core/ops/page-batch.ts:7-40`; `src/core/persistence/page-batch.ts:32-95, 110-173, 230-308`; `src/core/persistence/page-batch-id.ts:6-17` | `put_pages` 규칙 | R-42 |
| C-41 | `src/core/ops/page-upload.ts:136-215, 217-277, 319-396`; `src/core/persistence/page-upload.ts:37-50` | 업로드 규칙 | R-43 |
| C-42 | `src/core/capture-content.ts:37-49, 162-165, 174-181, 245-298` `slugPrefixForType`·`defaultSlug`·`normalizeForHash`·`deriveTitle`·`mergeCaptureFrontmatter` | `capture` 가공 | R-44 |
| C-43 | `src/core/persistence/page-mutations.ts:150-175, 327-352` `resolveCaptureFile`·capture 가공; `src/commands/capture.ts:91-167` | `capture` 입구와 CLI 옵션 | R-44 |
| C-44 | `src/core/persistence/semantic-pages.ts:39-107`; `src/core/ops/timeline.ts:18-60`; `src/core/ops/tags.ts:14-56` | 태그·타임라인 쓰기 | R-45, R-46 |
| C-45 | `src/core/page-size-policy.ts:35-39`; `src/core/page-body/limits.ts:27-38, 145-165, 193-196, 227-258` | 분할 저장 상수·스위치·승격·강등 | R-47 |
| C-46 | `src/core/behavior-change-notice.ts:733-734` | 문서가 말하는 기본값(코드와 다름, 2.1) | R-47 |
| C-47 | `src/commands/import.ts:263-615, 721-849, 859-935, 1011-1235` `runImport` | `import` 흐름 | R-50, R-51 |
| C-48 | `src/commands/import.ts:1286-1330, 1355-1491` | 파일 수집 | R-50 |
| C-49 | `src/core/sync.ts:289-291, 366-420, 466-473, 526-531, 566-621` | 확장자·제외 디렉터리·메타파일·불량 파일명 | R-50 |
| C-50 | `src/commands/embed.ts:147-271, 449-502, 893-1070, 1674-1830, 2267-2303` | `embed` 옵션·흐름 | R-52 |
| C-51 | `src/commands/export.ts:71-199` `runExport`; `src/core/export-stage.ts:10-14, 59-87` | `export` 옵션·경로 규칙 | R-53 |
| C-52 | `src/core/markdown.ts:846-1008` `splitBody`·`findTimelineSplitIndex`·`timelineSentinelKind`·`findBareTimelineSection`; `1250` `FENCE_TOGGLE_RE` | 본문 분리 규칙 전체 | R-12 |
| C-53 | `src/core/frontmatter-recovery.ts:1-241` `recoverFrontmatter`·`ruleFor`·`PROTECTED_FRONTMATTER_KEYS`·`IDENTITY_FRONTMATTER_KEYS`; `src/core/markdown.ts:509-594` `HOLD_CODES`·`classifyImportHold` | frontmatter 복구와 import 보류 분류 | R-10, R-25 |

### 1.6 수락 사례

출처: 사례별 표기. "실행"은 `agent-memory/artifacts/gbrain/page-import-demos/demo-pure.mts` 출력(`demo-pure.out.2026-10-23.json`)에서 관찰한 값이고, "도출"은 코드에서 도출했다(실행 안 함, 테스트 파일 미열람).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-12 | 본문 `Alice is a founder.\n\n<!-- timeline -->\n\n- 2024-01-02: met` | `compiled_truth="Alice is a founder.\n"`, `timeline="\n- 2024-01-02: met"`(parseMarkdown은 둘 다 trim) | 실행 |
| T-02 | R-12 | `Part one\n\n---\n\nPart two`(가로줄) | 분리 안 됨: `compiled_truth` 전체, `timeline=""` | 실행 |
| T-03 | R-12 | `Body\n\n---\n\n## Timeline\n- 2024-05-01: a` / `Body\n---\n## History\nProse about history.` | 둘 다 `---` 줄 기준으로 분리, `## Timeline`·`## History` 제목 줄은 `timeline`에 남음 | 실행 |
| T-04 | R-12 | 구분자 없음: `Body text\n\n## Timeline\n- 2024-05-01: a\n- 2023: b\n\n## Other\nkept in truth` / `Body\n\n## History\nWe started in a garage.\n` | 앞: `## Timeline` 구간(제목 포함)만 `timeline`, `## Other`는 truth에 남음. 뒤: 분리 안 됨(산문 History) | 실행 |
| T-05 | R-12 | 펜스 안의 `<!-- timeline -->` / 첫 내용이 `## Timeline`인 본문 | 둘 다 분리 안 됨 | 실행 |
| T-06 | R-18 | 250단어 / 301단어(한 문단) | 각각 청크 1개(301단어는 한도 450 이내로 다시 합쳐짐) | 실행 |
| T-07 | R-18 | 40단어 문단 23개(≈900단어) | 청크 3개, 단어 수 440 / 490(앞 청크 끝 50단어 겹침 포함) / 90(겹침 포함) | 실행 |
| T-08 | R-18 | 공백 없는 `a`×7000 | 청크 2개: 6000자, 1500자(창 6000, 겹침 500) | 실행 |
| T-09 | R-17 | `Intro line.` + `## Takes` 펜스 + `Outro line.` | 청크 1개, 텍스트에 펜스 내용(`secret take`) 없음 | 실행 |
| T-10 | R-15 | `contentHash`에 `captured_at`·`ingested_at`·`trust_tier`만 추가 / 태그 순서만 변경 / 다른 frontmatter 키 추가 / `timeline` undefined vs `""` | 같은 해시 / 같은 해시 / 다른 해시 / 같은 해시 | 실행 |
| T-11 | R-31 | `parseWriteRequestId`: `3F6A…`(대문자 UUID), `remember-acme-1`(두 번), `has space`, 129자 | 소문자 UUID, 같은 UUIDv5 두 번(`eb4aeb5f-ba6b-54d3-8708-1b695f62e1a8`), `invalid_params`, `invalid_params` | 실행 |
| T-12 | R-32 | `assertPageRevision` 6경우: (있음, 생략), (있음, 일치), (있음, 다른 값), (없음, 생략), (없음, 값 줌), (있음, force) | `revision_required`, ok, `revision_conflict`, ok, `revision_conflict`, ok. `expected_revision`+`force` 동시 → `invalid_params`, UUID 아님 → `invalid_params` | 실행 |
| T-13 | R-25, R-14 | `slugifyPath`: `People/Alice Example.md`, `notes/v1.0.0.md`, `_index.md`, `Daily/2024-03-15 Standup.md`, `한글/메모.md`, `a--b.md`, `Café Notes.mdx` / `hyphenFoldedSlug('notes/x---y')` | `people/alice-example`, `notes/v1.0.0`, `_index`, `daily/2024-03-15-standup`, `한글/메모`, `a-b`, `cafe-notes` / `notes/x-y`(새 슬러그면 `put_page` 거부) | 실행 |
| T-14 | R-44 | `defaultSlug(normalizeForHash("  Hello\r\nWorld  "), 2026-10-23)`, `type:diary`·`event` / `deriveTitle` | `inbox/2026-10-23-35c6b9f6`, `life/diary/…`·`life/events/…` / `Hello world`(헤딩 제거), 80자 제한, 빈 입력 `Capture`(해시는 node sha256 대체) | 실행 |
| T-15 | R-02, R-04, R-07 | PGLite, 소스 `default`의 `sync.repo_path`=git 체크아웃, `put_page('notes/a', …)` 처음 | 소스 자동 claim, `<repo>/notes/a.md` 생성, `pages`·`content_chunks`(벡터 NULL) 기록, 영수증 `persistence.mode:'filesystem'`, `write_through.written:true`, `git_state:'queued'`, `embedding_state:'queued'`; `git_durability`가 없고 훅도 없으면 git effect는 `durability_not_enabled`로 끝나고 파일은 미커밋 | 도출 |
| T-16 | R-02 | 새 `gbrain init` PGLite(소스 루트·`sync.repo_path` 없음), `put_page` | `pages` 행만 생기고 파일 없음, 영수증 `write_through{written:false, skipped:'no_repo_configured'}`(원격 호출자에는 경고) | 도출 |
| T-17 | R-32, R-35 | 같은 슬러그에 `expected_revision` 없이 `put_page` 두 번째 | 두 번째 요청이 `conflict`로 종결, 오류 코드 `revision_required`, 페이지·파일 변화 없음 | 도출 |
| T-18 | R-32, R-35 | 읽은 뒤 다른 쓰기가 끼어든 `expected_revision`으로 `put_page` | `revision_conflict`, 영수증 `state:'conflict'`, 그 쓰기는 반영 안 됨 | 도출 |
| T-19 | R-31 | 같은 `request_id`·같은 인자로 재호출 / 같은 `request_id`·다른 `content` | 첫째: 새 쓰기 없이 기존 영수증 반환 / 둘째: `idempotency_conflict`, 첫 쓰기의 영수증 유지 | 도출 |
| T-20 | R-06 | 체크아웃 파일을 편집기로 바꾼 뒤(커밋·sync 전) `put_page` | `source_changed`, `detail:'file_database_drift'`, 파일·DB 둘 다 그대로, 영수증 `conflict`, 해소 방법은 `gbrain sources reconcile` | 도출 |
| T-21 | R-36 | 저장된 페이지와 정규 비교가 같은 내용으로 `put_page`(revision 일치) | `status:'skipped'`, `noop:true`, `chunk_skip_reason:'write_skipped'`, 파일·effect 없음 | 도출 |
| T-22 | R-21, R-22 | 임베딩 키 없는 상태에서 `put_page` / 같은 상태에서 `gbrain import dir` | `put_page`: 쓰기는 `committed`, `embedding_state:'queued'`(꺼짐이면 `disabled`), effect가 키 오류로 재시도 후 실패, 청크 NULL, 키워드 검색 가능. `import`: 시작 시 자격 증명 점검에서 중단(`--no-embed`로 우회), `--no-embed`면 모든 청크 NULL | 도출 |
| T-23 | R-15, R-51 | 변경 없는 디렉터리로 `import` 두 번째 | 두 번째 실행은 `imported=0`, `skipped=N`, `unchanged=N`, `chunks=0`, `ingest_log` 줄 없음(`--log-noop` 제외) | 도출 |
| T-24 | R-25 | `Daily/2024-03-15 Standup.md`에 frontmatter 없음 | `type` 규칙 일치 없으면 `note`, 날짜 `2024-03-15`, 제목은 첫 `#` 제목 또는 파일명 정리, 슬러그 `daily/2024-03-15-standup`(메모리에서만, 파일 불변) | 도출 |
| T-25 | R-16 | 기존 태그 `[a,b]` 페이지에 frontmatter `tags: [a]`로 `put_page` / `import` | `put_page`: 태그 `[a,b]` 그대로(합집합) / `import`: `tag_source='frontmatter'`인 `b`가 삭제됨(`add_tag`로 만든 태그는 유지) | 도출 |
| T-26 | R-42 | `put_pages` 51쪽 / 같은 슬러그가 내용 다르게 2쪽 | 51쪽: `invalid_params`, 아무것도 안 씀 / 2쪽: 해당 쪽들 모두 `refused`, 나머지는 기록, 배치 `state:'partial'` | 도출 |
| T-27 | R-40 | `edit_page`의 `old_text`가 본문에 2곳 / 0곳 / `## Facts` 펜스 안 | `edit_ambiguous_match` / `edit_no_match` / `edit_protected_span`, 아무것도 안 바뀜 | 도출 |
| T-28 | R-41 | `append_page`에 `request_id` 없음 / 같은 `request_id` 재전송 | 첫째: `invalid_params` / 둘째: 두 번 덧붙이지 않고 같은 영수증 | 도출 |
| T-29 | R-53 | 두 소스에 같은 슬러그 `people/a`가 있는 채 `export`(`--source` 없음) | 충돌 목록과 함께 실패, 아무것도 게시되지 않음(`--source`별로 다른 디렉터리에 내보내라고 안내) | 도출 |
| T-30 | R-25 | 파일 `notes/random.md`의 frontmatter가 `slug: people/elon` | `status:'skipped'`, `refusal.code:'frontmatter_slug_conflict'`(정규화해 같을 때만 예외 허용) | 도출 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

#### 질문 ① "마크다운으로 관리하는 것 같은데 어디에, 어떤 식으로 저장하나" 결론과 engine-and-schema R-26 대조

**결론**(코드 확인): 마크다운 파일이 항상 원본인 것도, DB가 항상 원본인 것도 아니다. 페이지가 어느 쪽에 있는지는 그 페이지의 소스(source)가 체크아웃 루트에 묶였는지로 갈린다.

1. 쓰기 연산(`put_page` 등)은 항상 DB에 `pages` 행을 쓴다. 소스가 체크아웃 루트(`sources.local_path`, 기본 소스는 `sync.repo_path`)에 묶였고 `sync.write_through`가 꺼지지 않았으면 **같은 저널 트랜잭션 안에서 `<루트>/<slug>.md` 파일도 쓴다**(파일이 먼저 원자 교체되고 DB가 뒤따름, R-04). 이때 파일과 DB 행은 같은 내용이며 이후 한쪽만 바뀌면(파일 외부 편집) 저널 쓰기는 거부한다(R-06). 파일을 쓴 요청은 커밋 뒤 `git` effect를 큐에 넣고, 체크아웃이 "내구" 설정(`git_durability=enabled` 또는 레거시 훅)일 때만 실제로 `git commit`한다(R-07).
2. 소스에 루트가 없으면(새 `gbrain init` 직후 기본 상태) 쓰기는 **DB 행만** 만들고 영수증이 `write_through.skipped:'no_repo_configured'`를 말한다. 이 페이지의 유일한 사본은 DB다(R-02).
3. `gbrain import <dir>`·`sync`는 파일 → DB 방향이다. `import`는 파일을 쓰지 않고(R-08), 파일 내용을 읽어 `pages`·`content_chunks`로 만든다. 즉 "파일이 원본"이 되려면 파일이 이미 있는 디렉터리를 import/sync하거나 소스 루트를 묶어 write-through가 파일을 만들게 해야 한다.
4. `content_chunks`(청크·임베딩)·`tags`·`timeline_entries`·`facts` 행은 페이지 본문에서 파생된 행이고 `export`는 반대로 DB를 읽어 마크다운을 쓴다(R-09, R-53). 파일 없는 DB 전용 페이지는 `export`로만 파일이 된다.
5. 임베딩은 파일에 쓰이지 않고 DB `content_chunks.embedding`에만 있다. 파일은 청크 벡터 없이도 `import`/`sync`로 다시 같은 `pages`·`content_chunks` 텍스트를 만들 수 있고, 벡터는 `embed`로 다시 채운다.

**R-26(`engine-and-schema`, 추론)과의 대조**: R-26의 "파일 기반 지식은 마크다운과 frontmatter가 원본이고 DB는 재구축 가능한 파생 인덱스"는 **루트가 묶인 소스의 파일 기반 페이지에 대해 코드로 확인**됐다(R-04, R-06, R-08). 보정할 부분 두 가지다. (a) "한 마크다운 파일은 `pages` 한 행이 된다"는 방향만이 아니라 **쓰기 연산이 DB와 파일을 같은 트랜잭션에서 동시에 쓰는 경로가 기본(write-through 켜짐)** 이며 이 경로가 `put_page`의 정식 저장이다. (b) 새 `init` 직후처럼 루트가 없는 소스의 `put_page` 페이지는 **DB가 유일한 사본**이라 R-26의 "원본=파일" 문장이 성립하지 않는다(R-26 자체도 DB 전용 예시를 들었지만 `put_page`가 그 기본 경로임은 적지 않았다). 따라서 R-26의 검증 수준은 "추론"에서 "코드 확인"으로 올리되 위 두 가지를 문장에 반영하길 제안한다. 또 engine-and-schema 1.3 불변식의 "분할 저장은 이 릴리스에서 기본은 꺼짐"은 `behavior-change-notice.ts:733`의 문구를 근거로 했는데 **코드는 `SEGMENTED_STORAGE_DEFAULT='on'`**(`page-body/limits.ts:161`, `195`)이고 옛 버전 작성자가 최근 7일 안에 쓴 흔적이 있으면 막히는 게이트(`segmentedWriterBlockers`)가 있어 실제 켜짐 여부는 브레인마다 다르다(R-47). 문서 문구와 코드가 다르므로 코드를 사실로 적고 차이를 여기에 남긴다.

#### R-ID별 근거

| R-ID / T-ID | 근거 (repo@63f62b2 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-02, C-05(`persistence_brain.enabled boolean NOT NULL DEFAULT false`, `schema.ts:117`); `ops/page-edit.ts:44-60`; `ops/pages.ts:432-473`(`delete_page`·`restore_page`) | 코드 읽음 |
| R-02, T-15, T-16 | C-03, C-11, C-12; `write-through.ts:1-40`(헤더) | 코드 읽음. 새 `init`의 소스 상태(`sources.local_path` NULL, `sync.repo_path` 미설정)는 `init.ts`에 `repo_path`·`local_path` 설정이 없음을 grep으로 확인(`init.ts` 무일치)한 추론이고 실제 새 브레인 실행은 못 함 |
| R-03 | C-08, C-13; `page-prepare.ts:288-297`(`capturedPath`, `candidate`, `isWriteTargetContained`); `page-prepare.ts:911-913`(`bindOrigin`) | 코드 읽음 |
| R-04 | C-09 (`coordinator.ts:516-535` 복구 기록, `536-613` 트랜잭션, `574-596` 파일 교체) | 코드 읽음. 파일 교체가 `publicationTransaction` 콜백 안(`apply` 호출 `599` 앞)임을 줄 순서로 확인 |
| R-05 | C-09 (`coordinator.ts:624-657` catch, `661-760` `recoverPublication`), C-12 | catch 분기와 `recoverPublication` 앞부분만 읽음 |
| R-06 | C-08 (`page-prepare.ts:334-377`) | 코드 읽음. `file_database_drift`·`canonical_file_missing`·점유 거부 메시지는 줄에서 확인 |
| R-07, T-15 | C-14, C-16; `effect-git.ts:155-160, 261, 298`(`git add -A`, `git commit --only`) | `publishGitEffect`·`gitDurabilityPolicy`를 읽음. 푸시·재시도·보류 5회(`PARK_AFTER_FAILURES`, `effect-model.ts`)는 상수만 확인 |
| R-08 | C-29(`import.ts:1030-1108`), `import-file.ts:371`(`assertUnmanagedCanonicalWriter`), `persistence/maintenance.ts:56-70` | 코드 읽음 |
| R-09, R-53, T-29 | C-51 | 코드 읽음 |
| R-10 | C-17, C-18, C-53; `markdown.ts:223-257`; `page-prepare.ts:847-857` | 코드 읽음. 실행 못 함(js-yaml 없음) |
| R-11 | C-17, C-19 | 코드 읽음 |
| R-12, T-01~T-05 | C-52; `demo-pure.mts`의 `splitBody`(markdown.ts 846-1008 + 1250을 잘라 실행) | 실행 확인. 대체물: 줄 범위를 잘라 만든 임시 모듈, `findLineOutsideFencedCode`는 실제 `fence-scan.ts` |
| R-13 | C-20 | 코드 읽음 |
| R-14 | C-21, C-22, C-23, `persistence/page-mutations.ts:280-286` | 코드 읽음. 정규식 자체는 코드 읽음, 실행 안 함 |
| R-15, T-10 | C-25, C-24; `demo-pure.mts`(`utils.ts` 실제 import) | 실행 확인(해시 불변성), 코드 확인(건너뜀 조건은 `import-file.ts:563-582`) |
| R-16, T-25 | C-10(`page-prepare.ts:876`), C-24(`import-file.ts:826-829`) | 코드 읽음 |
| R-17, T-09 | C-26, C-27; `import-file.ts:633-635` | 코드 읽음. `fencedCodeChunks`의 코드 청커(`chunkCodeText`)는 읽지 않음 |
| R-18, T-06~T-08 | C-28, C-29, C-31; `demo-pure.mts`(`chunkers/recursive.ts` 실제 import) | 실행 확인. 대체물: tiktoken 없음 → `len/4` 폴백 |
| R-19 | C-30 | 코드 읽음 |
| R-20 | C-24(`import-file.ts:733-888`), engine-and-schema 1.3 (다) | `putPage`·`upsertChunks` SQL은 읽지 않음 |
| R-21 | C-24(`import-file.ts:672-723`), C-10(`noEmbed: true`, `page-prepare.ts:823`), C-14 | 코드 읽음 |
| R-22, T-22 | C-14, C-15, C-32 | 코드 읽음. 실행 못 함 |
| R-23 | C-33; `effect-journal.ts:52-58`(facts-backstop·links 큐 조건); `page-prepare.ts:891-895` | 투영 SQL은 읽지 않음(경계) |
| R-24 | C-34; `import-file.ts:590-629` | 코드 읽음 |
| R-25, T-13, T-24, T-30 | C-35, C-36, C-22; `demo-pure.mts`(`sync.ts` 실제 import) | `slugifyPath`는 실행 확인, 나머지는 코드 확인 |
| R-30 | C-02, C-03, C-04 | 코드 읽음 |
| R-31, T-11, T-19 | C-04, C-06; `demo-pure.mts`(`preconditions.ts` 실제 import) | 실행 확인(매핑·오류), 코드 확인(재전송 분기 `page-mutations.ts:303-307`) |
| R-32, T-12, T-17, T-18 | C-06, C-07, C-12; `coordinator.ts:566`; `demo-pure.mts`(`page-state/types.ts` 실제 import) | 실행 확인(코드 결정), 코드 확인(검사 위치) |
| R-33 | C-04, C-05(`DEFAULT_JOURNAL_LIMITS`) | 코드 읽음. 설정 키는 `journal.ts:104-133`의 `persistence.limits.*` 문구 근거 |
| R-34 | `service.ts:221-307, 349-398`, `write-wait.ts:17-27`, C-06(`types.ts:8-26` 코드 목록) | 코드 읽음 |
| R-35 | C-09, C-04, `service.ts:349-398` | 코드 읽음 |
| R-36, T-21 | C-10(`page-prepare.ts:801-811`) | 코드 읽음 |
| R-37 | C-01, C-03, C-37 | 코드 읽음 |
| R-40, T-27 | C-38 | 핵심 함수(`parsePageEdits`·`applyPageEdits`)를 읽음. 분할 저장 페이지용 `prepareSegmentedEditMutation`은 제외 |
| R-41, T-28 | C-39 | 헤더·입력 검사·상수만 읽음(`prepareAppendMutation` 본문은 앞부분만). 인라인 페이지가 `put_page` 경로를 탄다는 설명은 파일 헤더 주석 근거 |
| R-42, T-26 | C-40 | 코드 읽음 |
| R-43 | C-41 | 코드 읽음(스테이징 저장 내부 `persistence/page-upload.ts`는 상수만) |
| R-44, T-14 | C-42, C-43; `demo-pure.mts` | 실행 확인(순수 함수), 코드 확인(나머지). 대체물: `computeContentHash`를 node sha256으로 |
| R-45 | C-44 | 코드 읽음 |
| R-46 | C-44, C-33 | 코드 읽음 |
| R-47 | C-45, C-46 | 코드 읽음. 승격·강등 임계는 상수, 세그먼트 내부는 제외 |
| R-50 | C-47, C-48, C-49 | 코드 읽음 |
| R-51, T-23 | C-47, C-29 | 코드 읽음 |
| R-52 | C-50 | `runEmbed`·`runEmbedCore` 앞부분·`embedPage`·`embedAllStale` 앞부분·`embedPageTexts`를 읽음. `embedAll`(`--all`)·`embedAllStale` 본문의 페이지 순회·`listStaleChunks` SQL·`--facts`/`--images`/`--held` 하위 흐름은 읽지 않음 |
| R-60 | C-33, C-27 | 경계만 |

### 2.2 코드 읽는 순서

1. 저장 위치(질문 ①): `page-mutations.ts` `preparePageAdmission`의 389-431행 → `page-prepare.ts` `prepareFileTarget`(253) → `coordinator.ts` `publishMutation`(442) → `effect-journal.ts` `queuePublicationEffects`.
2. 접수와 영수증: `ops/pages.ts` `put_page` → `page-mutations.ts` `submitPageMutation` → `journal.ts` `admitWrite`/`prepareAdmission` → `service.ts` `awaitWrite`/`writeResponse`.
3. 분해: `page-prepare.ts` `prepareInlineOrSegmentedMutation`(692) → `import-file.ts` `importFromContent`(251) → `markdown.ts` `parseMarkdown`/`splitBody` → `markdown-chunks.ts` → `chunkers/recursive.ts`.
4. 명령: `commands/import.ts` `runImport` → `import-file.ts` `importFromFile`; `commands/embed.ts` `runEmbed`; `commands/export.ts` `runExport`.

구현 전략 메모: 저널 경로는 "의도(intent)를 먼저 내구 저장하고 나중에 소비자가 발행한다"가 핵심이고 호출자의 대기(`wait_ms`)는 발행과 분리된 폴링이다. 그래서 오래 걸리는 임베딩은 쓰기의 대기 시간 밖(effect)이다. 반대로 `import`는 한 파일씩 같은 프로세스에서 임베딩까지 하고 그 결과를 한 트랜잭션에 넣는다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다. `agent-memory/artifacts/gbrain/page-import-demos/demo-pure.mts`는 실제 소스를 import하거나 줄 범위를 잘라 임시 모듈로 만들어 실행하며 복사본을 저장하지 않는다.

## 적용 메모

없음.
