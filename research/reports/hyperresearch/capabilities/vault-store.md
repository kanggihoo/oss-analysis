---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/core/vault.py
  - src/hyperresearch/core/db.py
  - src/hyperresearch/core/migrations.py
  - src/hyperresearch/core/sync.py
  - src/hyperresearch/core/note.py
  - src/hyperresearch/core/frontmatter.py
  - src/hyperresearch/core/patterns.py
  - src/hyperresearch/core/config.py
  - src/hyperresearch/core/embed.py
  - src/hyperresearch/core/untrusted.py
  - src/hyperresearch/models/note.py
  - src/hyperresearch/models/output.py
  - src/hyperresearch/search/fts.py
  - src/hyperresearch/search/filters.py
  - src/hyperresearch/cli/main.py
  - src/hyperresearch/cli/search.py
  - src/hyperresearch/cli/note.py
  - src/hyperresearch/cli/embed_cmd.py
  - src/hyperresearch/mcp/server.py
depends: []
status: ready
---

# 볼트 저장·동기화·검색

> 마크다운 노트 파일(frontmatter+본문)을 원본으로 두고 SQLite(FTS5 포함)를 재구성 가능한 색인으로 유지하며, 노트 쓰기·파일↔DB 동기화·키워드(+선택 임베딩) 검색·`<untrusted-source>` 울타리 출력을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. `hyperresearch init`(=`Vault.init`)이 `.hyperresearch/`(config.toml, hyperresearch.db, templates/, exports/)와 `research/{notes,index,temp}/`를 만든다. 이후 모든 명령은 `Vault.discover`로 현재 디렉터리에서 위로 올라가며 `.hyperresearch/`가 있는 폴더를 볼트 루트로 잡는다.
2. 노트를 만드는 쪽(fetch·`note new` 등)이 `write_note`로 `research/notes/<id>.md`에 frontmatter+본문 파일을 쓴다. id는 제목에서 slug로 만들고, 같은 이름이 파일이나 DB에 이미 있으면 `-2`, `-3`을 붙인다.
3. `Vault.auto_sync()`(대부분의 읽기·쓰기 명령 시작 시)나 `hyperresearch sync`가 `compute_sync_plan`으로 디스크의 `*.md`와 DB 행을 mtime→해시 순으로 비교해 add/update/delete 계획을 만든다.
4. `execute_sync`가 한 트랜잭션 안에서 삭제 → 갱신 → 추가 순으로 적용한다. 노트 한 개마다 `notes`·`note_content`·`tags`·`aliases`·`notes_fts`·`links`를 다시 만들고, 마지막에 바뀐 노트와 관련된 링크의 `target_id`를 다시 푼다.
5. `hyperresearch search`가 질의를 FTS5 문법으로 바꾸어 `notes_fts`를 BM25(칼럼 가중치)로 조회하고, 상태 배수·선택적 품질 배수를 곱해 다시 정렬한다. `--semantic`이면 임베딩 코사인 순위와 RRF로 합친다.
6. 본문을 내보내는 `search`(JSON 또는 `--include-body`)와 `note show`는 출처가 http(s)인 웹 노트 본문을 `<untrusted-source url="…">` 울타리로 감싼다. 우리 파이프라인이 만든 `interim`·`source-analysis`·`moc`·`index` 노트는 감싸지 않는다.

### 1.2 범위·통합 지점
- 제공: 볼트 발견·초기화, 노트 frontmatter 스키마(공유 계약 S2), DB 스키마·마이그레이션, `write_note`, 파일↔DB 동기화(`sync`), FTS5 검색(`search`), 선택 임베딩 검색(`embed sync`, `search --semantic`), 울타리 출력(`note show`·`search`), `status`.
- 제외:
  - 노트 CRUD·태그·토픽·배치·인덱스 페이지·export/import 등 도구 명령군은 행 19(부속)다. 여기서는 `note show`의 출력 규칙만 다룬다.
  - 노트를 실제로 만드는 호출 흐름(중복 URL 거부, 정크 판정, `sources`·`assets` 행 쓰기)은 행 11이다. 이 스펙은 `write_note` 계약까지만 정의한다.
  - `notes`의 파생 점수 칼럼(`authority_score`·`centrality_score`·`independence`·`quality_score`)을 계산하는 규칙은 `capabilities/source-quality.md`, `claims` 테이블 내용은 `capabilities/claims-store.md`, `escalations` 테이블은 행 18, `oa_*` 값을 정하는 규칙은 행 14, `sources`·`assets`·`tag_aliases`·`api_cache` 테이블의 쓰기 규칙은 각 소유 행이다. 이 스펙은 그 테이블의 DDL만 소유한다.
  - config.toml 중 `[vault]`·`[sync]`·`[search]`·`[embeddings]` 키만 다룬다. 나머지 섹션(`[pipeline]`·`[web]`·`[ranking]`·`[scholar]` 등)은 소유 행에서 다룬다.
  - `Vault.init`이 부르는 에이전트 문서 주입(`inject_agent_docs`)은 행 1의 경계다. 호출 시점과 인자(`platform`)만 이 스펙에 있다.
  - MCP 서버·웹 UI(`serve`)는 행 20이다. 두 입구가 본문을 울타리 없이 내보낸다는 사실만 R-27에 둔다.
- 외부 의존·선행 계약: 선행 스펙 없음. 파일시스템, FTS5(`porter unicode61` 토크나이저)를 지원하는 SQLite, YAML 파서, 스키마 검증 라이브러리가 필요하다. 임베딩은 선택이며 numpy와 HTTP 클라이언트, 환경변수 `VOYAGE_API_KEY`·`OPENAI_API_KEY`를 쓴다.
- 소유 상태·부작용: `.hyperresearch/config.toml`, `.hyperresearch/hyperresearch.db`(WAL 모드), `research/notes|index|temp/*.md`, DB의 13개 테이블과 FTS 가상 테이블 2개(스키마 소유자). `sync`·`auto_sync`는 DB만 바꾸고 마크다운은 바꾸지 않는다.

### 1.3 인터페이스와 데이터 의미

**노트 frontmatter (`NoteMeta`)**: 파일 맨 앞 `---` YAML 블록. 모르는 키는 읽을 때 버리고(`extra: ignore`), 파일을 다시 쓸 때(`render_note`) 사라진다.

| 필드 | 타입 | 기본값 | 허용 값·변환 | DB 반영 |
|---|---|---|---|---|
| `title` | string | 없으면 `"Untitled"` | | `notes.title` |
| `id` | string | `""` | 값이 있으면 `slugify`. 비어 있으면 읽을 때 `slugify(파일 stem)`로 채움 | `notes.id` |
| `tags` | list[string] | `[]` | 각 원소 소문자·`strip`. 직렬화 때 빈 목록은 생략 | `tags`(별칭 해소 후) |
| `created` | datetime | 지금(UTC) | ISO 문자열 | `notes.created`(`isoformat()`) |
| `updated` | datetime? | null | | `notes.updated` |
| `source` | string? | null | URL 또는 경로. http(s)면 웹 출처(울타리 대상) | `notes.source` |
| `source_domain`, `fetched_at`, `fetch_provider`, `raw_file` | string?/datetime? | null | | DB에 없음(파일에만) |
| `status` | `NoteStatus` | `draft` | 아래 어휘 | `notes.status` |
| `type` | `NoteType` | `note` | 아래 어휘 | `notes.type` |
| `tier` | `Tier`? | null | 아래 어휘 | `notes.tier` |
| `content_type` | `ContentType`? | null | 아래 어휘 | `notes.content_type` |
| `aliases` | list[string] | `[]` | 링크 해소에 쓰는 별칭. 빈 목록 생략 | `aliases` |
| `parent` | string? | null | 토픽 이름. 파일 경로를 정하지 않는다(볼트는 평평) | `notes.parent` |
| `deprecated` | bool | false | `status: deprecated`와 별개 플래그 | `notes.deprecated`(0/1) |
| `reviewed`, `expires` | datetime? | null | | `notes.reviewed`·`expires` |
| `summary` | string? | null | | `notes.summary` |
| `doi` | string? | null | DOI 또는 `arXiv:<id>` | `notes.doi` |
| `utility_score` | float? | null | 2단계 선별 점수(0~18 규약, 검증 없음) | `notes.utility_score` |
| `citation_count` | int? | null | | `notes.citation_count` |
| `venue` | string? | null | | `notes.venue` |
| `is_retracted` | bool? | null | null=미확인, false=확인했고 철회 아님, true=철회 | `notes.is_retracted`(NULL/0/1) |
| `oa_url`, `oa_source`, `oa_version`, `oa_license`, `oa_recovery_kind` | string? | null | 본문이 `source`가 아니라 오픈액세스 사본에서 왔을 때만 채움. `oa_source`는 `unpaywall\|europepmc\|core`, `oa_version`은 `publishedVersion\|acceptedVersion\|submittedVersion`, `oa_recovery_kind`는 `substituted\|rescued`(모델은 자유 문자열이고 어휘는 주석·검색 필터에만 있음) | `notes.oa_*` |

직렬화(`serialize_frontmatter`): `exclude_none` JSON 덤프(필드 선언 순서, 기본값이어도 `status`·`type`·`deprecated`는 쓴다), 빈 `tags`·`aliases`·빈 `id` 생략, `sort_keys=False`, 유니코드 유지. 파일 = `---\n<yaml>---\n` + `\n` + 본문. 읽을 때(`parse_frontmatter`)는 맨 앞 `---\s*\n … \n---\s*\n?`만 frontmatter로 보고, 없거나 매핑이 아니면 `title: "Untitled"` 기본 메타 + 전체를 본문으로 돌려준다. 어휘 밖 값(예: `status: foo`)은 검증 오류가 되어 그 파일의 읽기가 실패한다.

**어휘** (문자열 값 그대로):

| 이름 | 값 |
|---|---|
| `NoteStatus` | `draft` `review` `evergreen` `stale` `deprecated` `archive` |
| `NoteType` | `note` `raw` `index` `moc` `interim` `source-analysis` |
| `Tier` | `ground_truth` `institutional` `practitioner` `commentary` `unknown` |
| `ContentType` | `paper` `docs` `article` `blog` `forum` `dataset` `policy` `code` `book` `transcript` `review` `unknown` |

**DB 스키마** (`SCHEMA_VERSION = 13`, 전부 C-01): 연결마다 `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `row_factory = Row`. `init_schema`는 DDL(`CREATE … IF NOT EXISTS`) → FTS DDL → `_meta.schema_version`이 없을 때만 13 기록 → `migrate` → 마이그레이션 뒤 인덱스 순으로 돈다. 새 DB는 13이 바로 찍혀 마이그레이션이 비어 있다.

| 테이블(13) | 칼럼과 제약 |
|---|---|
| `_meta` | `key` PK, `value`. 키: `schema_version`, `last_sync` |
| `notes` | `id` PK, `title`, `path` UNIQUE(볼트 루트 기준 posix 상대 경로), `status` CHECK=NoteStatus 6값(기본 draft), `type` CHECK=NoteType 6값(기본 note), `tier` NULL 또는 Tier 5값, `content_type` NULL 또는 ContentType 12값, `source`, `parent`, `deprecated` int 기본 0, `reviewed`, `expires`, `word_count` int 기본 0, `summary`, `created`(NOT NULL), `updated`, `file_mtime` REAL NOT NULL, `content_hash` NOT NULL, `synced_at` NOT NULL, `doi`, `utility_score`, `authority_score`, `centrality_score`, `independence`, `citation_count` int, `venue`, `is_retracted` int(NULL 허용), `quality_score`, `oa_url`, `oa_source`, `oa_version`, `oa_license`, `oa_recovery_kind` |
| `note_content` | `note_id` PK→notes ON DELETE CASCADE, `body`(원문 마크다운), `body_plain`(`strip_markdown` 결과, FTS용) |
| `tags` | (`note_id`→notes CASCADE, `tag`) PK |
| `aliases` | (`note_id`→notes CASCADE, `alias`) PK, `alias`에 NOCASE 인덱스 |
| `links` | (`source_id`, `target_ref`, `line_number`) PK, `target_id`(NULL=미해결), `context`(줄 200자). FK 선언 없음 |
| `embeddings` | `note_id` PK→notes CASCADE, `model`(`<model>@<content_hash>` 스탬프), `dimensions`, `vector` BLOB(float32 LE), `created_at` |
| `claims` | 행 17 스펙이 소유(`capabilities/claims-store.md`). DDL은 C-01 |
| `api_cache` | `url` PK, `body`, `fetched_at` |
| `escalations` | 행 18 소유. `reason` CHECK 6값, `status` CHECK 5값, UNIQUE(url, vault_tag). DDL은 C-01 |
| `tag_aliases` | `alias` PK, `canonical` |
| `sources` | `url` PK, `note_id`→notes ON DELETE SET NULL, `domain`, `fetched_at`, `provider`, `content_hash`, `status` CHECK(`active`/`dead`/`redirected`) |
| `assets` | `id` AUTOINCREMENT, `note_id`→notes CASCADE, `type` CHECK(`image`/`screenshot`/`pdf`/`other`), `filename`, `url`, `alt_text`, `content_type`, `size_bytes`, `created_at` |

FTS 가상 테이블 2개: `notes_fts(id UNINDEXED, title, body_plain, tags, aliases)`, `claims_fts(claim_id UNINDEXED, claim, quoted_support)`. 둘 다 `tokenize='porter unicode61'`. 인덱스: `notes`의 status·type·parent·created·updated·word_count·(status,type)·(parent,status)·tier·content_type·doi·quality_score, `tags.tag`, `links.source_id`·`target_id`, `claims`·`escalations`·`sources`·`assets` 보조 인덱스(C-01).

**마이그레이션** (C-03·C-04): `MIGRATIONS[버전]`이 문자열(SQL)이거나 callable. `migrate(conn, 13)`는 저장된 버전+1부터 13까지 차례로 적용하고 버전마다 `_meta.schema_version`을 갱신한다. 버전별 내용은 2=`tag_aliases`, 3=`sources`, 4=`assets`, 5=변경 없음, 6=`tier`·`content_type` 칼럼, 7=`type`에 `interim` 추가(테이블 재생성), 8=`type`에 `source-analysis` 추가(재생성), 9=점수 칼럼·`claims`·`claims_fts`·`api_cache`, 10=`escalations`, 11=`oa_url|oa_source|oa_version|oa_license`, 12=`oa_recovery_kind`, 13=`is_retracted`를 NULL 허용으로 재생성(0은 NULL로 바꾸고 모든 노트의 `file_mtime=0`·`content_hash=''`로 지워 다음 sync가 마크다운에서 전부 복원하게 함). 신규 구현이 구버전 DB를 올릴 필요가 없으면 v13 DDL만 있으면 된다.

**볼트 레이아웃** (`Vault`, C-02): `.hyperresearch/`·`config.toml`·`hyperresearch.db`는 상수 이름. `research_dir`(config `[vault] research_dir`, 기본 `research`) 아래 `notes/`(노트), `index/`(자동 생성 인덱스 페이지), `temp/`(임시·스텁 노트, 동기화 대상), `runs/<vault_tag>/`(런 작업 공간, 동기화 대상 아님). `.hyperresearch/templates/`, `.hyperresearch/exports/`. `RUN_TAG_RE = ^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$`, `validate_run_tag` 위반은 `InvalidRunTagError`(행 9가 사용).

**함수·명령 계약**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `Vault.init(root, name="Research Base", research_dir="research", platforms=("claude",))` | → `Vault` | `.hyperresearch/`가 이미 있으면 `VaultError("Vault already initialized at …")`. 디렉터리·config·DB·`templates/note.md`를 만들고 `platforms`마다 `inject_agent_docs(root, platform=…)`(행 1 경계) |
| `Vault.discover(start=None)` | → `Vault` | cwd(또는 start)에서 위로 `.hyperresearch/` 디렉터리를 찾고, 없으면 `VaultError("No hyperresearch vault found. Run 'hyperresearch init' to create one.")` |
| `Vault.db` | → 연결 | 처음 접근 때 연결하고 `init_schema`를 항상 실행(멱등). 인스턴스에 캐시 |
| `Vault.auto_sync()` | → 없음 | config `[sync] auto_sync`(기본 true)가 거짓이면 아무것도 안 한다. 아니면 plan을 만들고 add/update/delete가 하나라도 있으면 `execute_sync` |
| `compute_sync_plan(vault, force=False)` | → `SyncPlan{to_add, to_update, to_delete, unchanged}` | R-12·R-13 |
| `execute_sync(vault, plan)` | → `SyncResult{added, updated, deleted, unchanged, errors[{path,error}], duration_ms}` | R-14~R-17 |
| `read_note(file, vault_root)` | → `Note{meta, body, path, frontmatter_broken, id_declared, content_hash(sha256 원본 바이트), word_count(body.split() 개수), outgoing_links}` | UTF-8(BOM 허용). R-07 |
| `write_note(notes_dir, title, body="", *, note_id=None, tags, status="draft", note_type="note", parent, source, summary, tier, content_type, extra_frontmatter, taken_ids)` | → 파일 경로 | R-08. 동기화는 하지 않는다 |
| `preprocess_query(raw)` / `search_fts(conn, query, *, filters, limit=20, offset=0, include_index=False, ranking, quality_ranked=False)` | → 결과 dict 목록 | R-18~R-21. 결과 키: id, title, path, status, type, tier, content_type, doi, venue, citation_count, is_retracted(bool\|None), oa_version, tags(list), created, updated, word_count, summary, quality_score, score(양수), snippet |
| `SearchFilters(...)`·`.to_sql(alias)` | → (WHERE 문자열, 파라미터) | R-20 |
| `embed_sync(vault, batch_size=32)` / `semantic_search(vault, query, limit=20, *, filters)` / `reciprocal_rank_fusion(lists, k=60)` | → `{embedded, skipped, provider, model}` / `[{id, score}]` / `[(id, score)]` | R-23·R-24 |
| `is_untrusted(source, note_type)` / `wrap_body(body, source)` | → bool / string | R-26 |

**CLI** (모든 JSON 출력은 `{ok, data, error, error_code, count, vault, timestamp}`에서 null을 뺀 객체. 오류 시 `ok:false`+`error`+`error_code`):

| 명령 | 옵션 | 동작·종료 코드 |
|---|---|---|
| `hyperresearch init [PATH=.]` | `--name/-n`(Research Base), `--dir/-d`(research), `--json/-j` | `Vault.init`. 이미 있으면 `VAULT_EXISTS`, 종료 1. 성공 data `{vault_path, name}` |
| `hyperresearch status` | `--json/-j` | auto_sync 후 노트 수(전체·status별·type별), 태그(고유 수·상위 10), 링크(전체·`target_id IS NULL`인 끊긴 수·고아 노트 수), 총 단어 수, `last_sync`. 볼트 없으면 `NO_VAULT` 종료 1 |
| `hyperresearch sync` | `--force/-f`, `--dry-run`, `--json/-j` | `auto_sync` 설정과 무관하게 `compute_sync_plan(force)` 후 실행. `--dry-run`은 `{to_add, to_update, to_delete, unchanged}`만 출력하고 쓰지 않음. 결과 `{added, updated, deleted, unchanged, errors, duration_ms}` |
| `hyperresearch search [QUERY]` | `--tag/-t`(반복, AND), `--status/-s`, `--type`, `--tier`, `--content-type`, `--doi`, `--venue`, `--min-citations`, `--retraction`(retracted\|not-retracted\|unchecked), `--oa-version`, `--parent/-p`, `--after`, `--before`(YYYY-MM-DD), `--path`(GLOB), `--min-words`, `--max-words`, `--linked-from`, `--linked-to`, `--min-inbound`, `--has-backlinks`, `--include-body`, `--no-body`, `--limit/-l`(기본 config `search_default_limit`=20), `--ranked`, `--semantic`, `--offset`(0), `--max-tokens`, `--json/-j` | R-19~R-25. 잘못된 `--tier`/`--content-type`는 `INVALID_TIER`/`INVALID_CONTENT_TYPE` 종료 1, 필터 값 오류·`--semantic`+빈 질의는 `INVALID_FILTER` 종료 1, 질의 오류는 `BAD_QUERY` 종료 2 |
| `hyperresearch note show NOTE_ID...`(루트 `show`는 숨김 별칭) | `--raw/-r`, `--meta/-m`, `--json/-j` | R-26. 없는 id: 1개면 `NOT_FOUND` 종료 1, 여러 개면 `{notes, not_found}` |
| `hyperresearch embed sync` / `embed status` | `--json/-j` | R-23. 비활성이면 `EMBEDDINGS_DISABLED` 종료 1 |

**config.toml 키(이 스펙 몫)**: `[vault] name·default_status·research_dir`, `[sync] auto_sync(true)·exclude_patterns`, `[search] title_weight(10.0) body_weight(1.0) tags_weight(5.0) aliases_weight(3.0) boost_evergreen(1.5) penalize_deprecated(0.3) penalize_stale(0.7) default_limit(20) chars_per_token(4) snippet_len(200)`, `[embeddings] provider(none\|voyage\|openai) model(빈 값=제공자 기본) body_chars(1500)`. 파일이 없으면 모두 기본값. 알 수 없는 키는 무시한다. `exclude_patterns`는 저장·읽기만 되고 동기화가 쓰지 않는다(R-12).

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Vault.discover` | cwd부터 부모로 올라가며 `.hyperresearch/` 디렉터리가 있는 첫 폴더를 루트로 쓴다. 파일시스템 루트까지 없으면 `VaultError`. DB 파일 유무는 보지 않는다(`is_initialized`만 둘 다 본다) | 코드 확인 |
| R-02 | `Vault.init` | `.hyperresearch/`가 있으면 아무것도 만들지 않고 `VaultError`. 없으면 `.hyperresearch/{templates,exports}`, `<research_dir>/{notes,index,temp}`, config.toml, DB(스키마), `templates/note.md`, `platforms`별 에이전트 문서를 만든다. `runs/`는 만들지 않는다 | 코드 확인 |
| R-03 | `Vault.db` 첫 접근 | 연결 후 `init_schema`가 매번 돈다. 새 DB: 테이블 13개+FTS 2개+`schema_version=13`. 기존 DB: 저장된 버전이 13 미만이면 `migrate`가 남은 버전만 적용(버전 스탬프는 `INSERT OR IGNORE`라 덮어쓰지 않음). 마지막에 `tier`·`content_type`·`doi`·`quality_score` 인덱스 | 코드 확인 |
| R-04 | v13 마이그레이션 | `notes.is_retracted`가 NOT NULL이면 외래키를 끄고 테이블을 재생성하며 0을 NULL로 바꾸고 모든 노트의 `file_mtime=0`, `content_hash=''`로 만들어 다음 sync가 마크다운에서 값을 복원하게 한다. 이미 NULL 허용이면 아무것도 안 한다. `is_retracted` 정의 문자열을 못 찾으면 `OperationalError` | 코드 확인 |
| R-05 | frontmatter 읽기 | R-06~R-07 규칙으로 `NoteMeta`를 만든다. YAML 문법 오류·검증 오류는 예외로 올라가고, 그 파일은 sync에서 오류 항목이 된다 | 코드 확인 |
| R-06 | id 정하기 | frontmatter `id`가 있으면 `slugify(id)`, 없으면 `slugify(파일 stem)`(`id_declared=false`). `slugify`: NFC→소문자→`[^\w\s-]` 제거(유니코드 단어 문자 유지)→공백은 `-`→연속 `-` 축약→앞뒤 `-` 제거. 비면 `"note-"+sha256(빈 문자열)[:8]`. 80자와 UTF-8 200바이트 상한으로 자르고 끝의 `-`를 뗀다 | 코드 확인 |
| R-07 | `read_note` | 내용이 `---\s*\n`으로 시작하는데 frontmatter 파싱이 실패하면 `frontmatter_broken=true`. `content_hash`는 원본 바이트의 sha256, `word_count`는 `body.split()` 개수, `outgoing_links`는 코드 제거 후 위키링크(R-16 필터) 중복 제거 목록 | 코드 확인 |
| R-08 | `write_note` | id=`slugify(note_id or title)`. `<notes_dir>/<id>.md`가 이미 있거나 id가 `taken_ids`에 있으면 후보를 `_collision_id`로 바꿔 가며(카운터 2부터) 재시도하고, 후보가 곧 파일 이름과 frontmatter id가 된다. 후보는 접미사 `-N`을 포함해 80자·200바이트 상한 안에서 `slugify`의 고정점이 되도록 앞부분을 잘라 만든다. `created`는 지금(UTC), `extra_frontmatter`는 `NoteMeta`에 덮어쓴 뒤 검증(`NoteMeta`에 없는 키는 버려진다). 부모 디렉터리는 만들되 하위 폴더는 만들지 않는다(평평) | 코드 확인 |
| R-09 | `strip_markdown`(FTS용 평문) | 코드 제거 → 제목 `#` 제거 → 강조·밑줄 제거 → `[텍스트](url)`→텍스트 → `[[a\|b]]`→b, `[[a]]`→a → 이미지→alt → 태그처럼 보이는 `<…>`만 제거(`<` 뒤가 영문자·`/`영문자·`!`·`?`) → 공백 축약 | 코드 확인 |
| R-10 | 위키링크 추출 | 코드 블록·인라인 코드를 먼저 지운 본문에서 `WIKI_LINK_RE`(`[[대상]]`, `[[대상\|표시]]`, 뒤에 `(`가 붙으면 제외)로 찾고, 대상에서 끝의 `\`를 떼고 `is_valid_wiki_link_target`이 거부하는 것(URL·앵커·절대경로, 인용 번호·`cite-3`·로마 숫자·기호 각주, 그림/표/식 참조, `{placeholder}`, 셸 조각, `..`, 괄호 짝 불일치)을 버린다 | 코드 확인 |
| R-11 | 파일 스캔 대상 | `<research_dir>` 아래 재귀 `*.md` 중 (a) `<research_dir>` 바로 아래 파일(스테이징 파일)은 제외, (b) `runs/` 아래는 제외, (c) 첫 16바이트(BOM 허용)가 `---[ \t]*\r?\n`으로 시작하지 않는 파일은 제외. 경로는 볼트 루트 기준 posix 상대 경로가 DB `path`다. `exclude_patterns` 설정은 쓰지 않는다 | 코드 확인 |
| R-12 | plan 분류 | DB에 없는 경로 → `to_add`. 있는 경로 → `force`이면 곧바로 `to_update`. 아니면 `abs(디스크 mtime − DB file_mtime) > 0.001`일 때만 원본 바이트 sha256을 `content_hash`와 비교해 다르면 `to_update`, 같으면 `unchanged`(이때 DB mtime은 갱신하지 않아 다음에도 해시를 다시 계산). mtime이 같으면 `unchanged`. 디스크에 없는 DB 경로 → `to_delete`. `research_dir`가 없으면 빈 plan | 코드 확인 |
| R-13 | `execute_sync` 전체 | `BEGIN IMMEDIATE` 한 트랜잭션. 순서: 삭제 → 갱신 → 추가 → (이름 변경으로 고아가 된 `sources.note_id`를 NULL로, `assets` 행 삭제) → 바뀐 id의 링크 재해결 → `_meta.last_sync` 기록 → commit. 파일 하나의 실패(읽기·검증·충돌)는 `errors`에 `{path, error}`로 쌓고 계속한다(해당 파일은 색인되지 않거나 이전 행 그대로라 다음 sync가 다시 시도). SQLite가 트랜잭션 전체를 이미 롤백했으면 오류에 "nothing from this sync pass was kept"를 붙이고 패스를 중단하며 added/updated/deleted를 0으로 돌린다. 그 밖의 예외는 롤백 후 다시 던진다 | 코드 확인 |
| R-14 | id 충돌·이름 변경 | 같은 패스에서 어떤 파일의 id가 이미 다른 경로의 행에 속하면 그 파일을 `id collision: '<id>' already belongs to '<path>'. Skipped to avoid silent overwrite.`로 건너뛴다. 경로는 같은데 frontmatter `id`가 바뀐 파일은 같은 행을 새 id로 옮긴다(`_rename_note_id`: 재생성 테이블(`note_content`·`tags`·`aliases`)·`links`·`notes_fts` 삭제 후 `UPDATE notes SET id`, `embeddings`·`claims`·`assets`는 새 id로 이동, `sources`·`escalations`는 URL 단위로 이동, 외래키 검사는 commit까지 지연). 단 id가 frontmatter에 선언돼 있지 않거나 frontmatter가 안 읽히면 옮기지 않고 오류로 남긴다. 새 id를 stem이 같은 새 파일이 이미 주장하면(그 파일의 URL 행이 stem으로 기록되므로) 충돌로 건너뛰고, 읽을 수 없는 후보 파일이 있으면 추측하지 않고 건너뛴다 | 코드 확인 |
| R-15 | 노트 한 개 upsert | `INSERT … ON CONFLICT(id) DO UPDATE`로 `notes`를 쓴다(파생 점수 4칼럼은 목록에 없어 보존된다: `authority_score`·`centrality_score`·`independence`·`quality_score`). `created`는 없으면 `synced_at`. `tags`는 지우고 다시 쓰되 `tag_aliases`로 해소(키는 소문자, 값 없으면 소문자 그대로). `aliases` 재작성. `note_content`는 UPSERT(`body`=원문, `body_plain`=`strip_markdown`). `notes_fts`는 삭제 후 삽입(tags·aliases는 공백으로 이은 문자열). `links`는 해당 `source_id` 행을 지우고, 코드 제거 본문을 줄 단위로 훑어 `(source, target_ref, line_number, context=줄 앞 200자)`를 `INSERT OR IGNORE`(R-10 필터) | 코드 확인 |
| R-16 | 삭제 | `to_delete` 경로의 노트: `notes_fts`·`links(source_id)`·`notes` 행을 지운다. 외래키 CASCADE가 `note_content`·`tags`·`aliases`·`embeddings`·`claims`·`assets`를 지우고 `sources.note_id`는 NULL이 된다. `claims_fts`와 `escalations` 행은 남는다 | 코드 확인 |
| R-17 | 링크 재해결 | 바뀐(추가·갱신·삭제·이름 변경 전후) id들의 `links`에서 출발한 줄과 그 id를 가리키던 줄의 `target_id`를 NULL로 만든 뒤, 모든 `target_id IS NULL` 줄을 (1) `notes.id`와 정확히 일치, (2) 대소문자 무시 id 일치, (3) 별칭(대소문자 무시), (4) 제목(대소문자 무시) 순으로 채운다. 못 찾으면 NULL로 남는다 | 코드 확인 |
| R-18 | `preprocess_query` | 대문자화한 질의에 ` AND `·` OR `·` NOT `·` NEAR(`가 있으면 원문 그대로 FTS5에 넘긴다. 아니면 `"…"`로 닫힌 구절은 그대로 두고 나머지 단어에서 `* ^ ( ) : { } "`를 지운 뒤, 글자-숫자 경계와 숫자 사이 `.`/`-`에서 쪼개(`mamba3`→`mamba 3`, `llama3.1`→`llama 3 1`) 각 조각을 `"조각"*`(접두 일치)로 만들어 공백으로 잇는다(암묵적 AND) | 코드 확인 |
| R-19 | `search_fts` 질의 | 변환 결과가 비고 필터도 없으면 `SearchQueryError`(질의에 검색할 용어가 없음). 질의가 공백이고 필터가 하나 이상이면 필터 전용 경로(`notes`만 조회, 스니펫=`summary`, score 0.0, `created DESC, id` 순). 아니면 `notes_fts MATCH ?`와 `notes` JOIN, `bm25(notes_fts, 0.0, title, body, tags, aliases)`(기본 10/1/5/3) 오름차순(낮을수록 좋음), 스니펫은 `snippet(notes_fts, 2, '>>>', '<<<', '...', 64)`. 기본으로 `type != 'index'`만 조회. `LIMIT/OFFSET`은 SQL에서 적용한다. FTS 문법 오류(`syntax error`·`malformed MATCH`·`unterminated`)는 `SearchQueryError`, 그 밖의 `OperationalError`(테이블 없음·잠금)는 그대로 올린다. 결과 `score`는 `abs(bm25)` | 코드 확인 |
| R-20 | `SearchFilters` | 모두 AND. `tags`는 태그마다 `IN (SELECT note_id FROM tags WHERE tag=?)`(소문자), `status`·`type`·`tier`·`content_type`·`parent`·`oa_version` 정확 일치, `after`/`before`는 `created >= / <=` 문자열 비교, `path_glob`은 SQLite `GLOB`, `min_words`/`max_words`, `doi`·`venue`는 `COLLATE NOCASE` 정확 일치, `min_citations`, `retraction`(`unchecked`→`is_retracted IS NULL`, `retracted`→=1, `not-retracted`→=0), 그래프 필터(`linked_from`, `linked_to`, `min_inbound`, `has_backlinks`). `retraction`이 세 값 밖, `oa_version`이 세 값 밖, `min_citations<0`이면 `ValueError` | 코드 확인 |
| R-21 | 검색 후 재정렬 | `ranking`이 주어지면(CLI는 항상 줌) `status`가 `evergreen`이면 ×`boost_evergreen`(1.5), `deprecated`면 ×0.3, `stale`이면 ×0.7을 곱하고 점수 내림차순으로 다시 정렬한다(이미 `LIMIT/OFFSET`이 적용된 결과 안에서만). `quality_ranked`(`--ranked`)이면 추가로 점수 ×`(0.5 + (quality_score 또는 0.5))`로 다시 정렬 | 코드 확인 |
| R-22 | `search` 명령 준비 | `--tier`·`--content-type`을 어휘로 먼저 검증. `SearchFilters` 생성·`--semantic`에 질의가 없는지 검증(`ValueError`→`INVALID_FILTER`). `Vault.discover` 실패→`NO_VAULT` 종료 1. `auto_sync` 후 `--limit` 기본값=config. `SearchQueryError`→`BAD_QUERY`, 종료 2. 텍스트 모드는 `id 제목 (status) 태그`와 `snippet[:snippet_len]`만 출력하고 본문은 출력하지 않는다 | 코드 확인 |
| R-23 | 본문 포함·토큰 예산 | JSON 모드이면 `--no-body`가 없는 한, 아니면 `--include-body`일 때 결과마다 `note_content.body`(원문)와 `source`를 붙인다. `--max-tokens`가 있으면 예산=`max_tokens × chars_per_token`자, 결과마다 `200 + len(title) + len(id)` + 본문 길이를 차감하고, 남은 예산이 0 이하면 거기서 끊고, 본문이 남은 예산보다 길면 `본문[:남은] + "\n... [truncated]"`와 `truncated: true`로 마지막 결과를 만들고 끊는다 | 코드 확인 |
| R-24 | 임베딩 | `embed_sync`: `[embeddings] provider`가 `none`이면 `EmbeddingError`. `type != 'index'` 노트 중 `embeddings.model`이 `<model>@<content_hash>`와 다른 것만 32개씩 보내, 텍스트=`title\nsummary(있으면)\nbody_plain[:body_chars]`로 임베딩하고 float32 LE BLOB으로 `INSERT OR REPLACE`(배치마다 commit; 반환 벡터 수가 다르면 `EmbeddingError`). 제공자 호출: voyage는 `POST https://api.voyageai.com/v1/embeddings`(기본 모델 `voyage-3-lite`), openai는 `POST https://api.openai.com/v1/embeddings`(기본 `text-embedding-3-small`), 둘 다 `{input, model}`+Bearer, 타임아웃 60초, 키 환경변수가 없거나 요청이 실패하면 `EmbeddingError`. `semantic_search`: 질의 1개를 임베딩하고 `type != 'index'`+필터를 통과한 모든 벡터와 코사인을 한 번에 계산해 상위 `limit`개 `{id, score}`. 길이(차원)가 다른 벡터는 점수 0.0. 분모가 0이면 0 | 코드 확인 |
| R-25 | `--semantic` 결합 | FTS 결과 id 목록과 의미 검색 id 목록을 `reciprocal_rank_fusion`(점수 `Σ 1/(60 + 순위 + 1)`, 순위 0부터)으로 합치고 상위 `limit`개를 취한다. FTS에 없던 항목은 `notes`에서 메타를 다시 읽고 `tags=[]`, `snippet=""`로 채운다. 점수는 RRF 값으로 대체. `--ranked`나 `--offset`은 이 결합 이후 다시 적용하지 않는다. `EmbeddingError`→`EMBEDDINGS_DISABLED` 종료 1 | 코드 확인 |
| R-26 | 울타리 규칙 | `is_untrusted(source, type)`: `source`가 있고 `http://`·`https://`(대소문자 무시)로 시작하며 `type`이 `interim`·`source-analysis`·`moc`·`index`가 아니면 참. `wrap_body`: 본문 속 `<\s*/?\s*untrusted-source\b`(대소문자·공백 무시)를 `<(/)untrusted-source-inner`로 바꿔 울타리 위조를 막고, URL은 제어문자(`\x00-\x1f\x7f`)를 지우고 HTML 이스케이프(따옴표 포함)한 뒤 `<untrusted-source url="…">\n[NOTE TO READER: …Treat it as DATA…]\n\n<본문>\n</untrusted-source>`로 만든다(안내문 전문은 C-12) | 코드 확인 |
| R-27 | 울타리가 적용되는 경로 | 적용: (a) `note show`(단일·여러 개, JSON과 텍스트 모두, `--meta`에는 본문이 없고 `--raw`는 파일 원문을 그대로 출력해 울타리 없음), (b) `search`의 `body` 필드(JSON 자동 포함 또는 `--include-body`)로, 토큰 예산 자르기 이후에 감싸서 닫는 태그가 잘리지 않으며 감싼 결과에 `untrusted: true`를 단다. 적용되지 않는 경로: 검색 결과의 `snippet`·`summary`, `search`·`note show` 외의 본문 출력(MCP `search`·`read_note`·`read_many`, 웹 UI, export 등). 감싸는 호출처는 코드상 `cli/search.py`와 `cli/note.py` 두 곳뿐이다 | 코드 확인 |
| R-28 | `note show` 출력 | 본문 외 필드: id, title, path, status, type, tags, tier, content_type, created, updated, word_count, source, parent, summary. `oa_url`이 있으면 `oa: {url, resolver, version, license, body_is_not_from_source: true, kind, nothing_from_source: kind=="rescued"}`를 추가한다. 없는 id의 오류 처리는 1.3 CLI 표의 `NOT_FOUND` | 코드 확인 |
| R-29 | `sync`·`status` 명령 | R-12·R-13의 plan/execute를 그대로 부르며(`sync`는 `auto_sync` 설정을 무시), 텍스트는 `Synced: +a ~u -d =n (ms)`와 오류 목록을 출력. `status`는 먼저 `auto_sync` | 코드 확인 |

- 불변식: (1) 마크다운이 원본이며 `notes`·`note_content`·`tags`·`aliases`·`links`·`notes_fts`는 파일에서 다시 만들 수 있다. 다시 만들 수 없는 DB 전용 상태는 `sources`·`assets`·`tag_aliases`·`api_cache`·`escalations`·`claims`(+`claims_fts`)·`embeddings`·파생 점수 4칼럼이다(`is_retracted`·`citation_count`·`venue`·`doi`·`utility_score`는 frontmatter에도 있어 복원된다). (2) 성공한 `execute_sync` 뒤 `to_add`·`to_update`였던 파일 중 오류가 없는 것은 DB에 있고, `to_delete` 경로는 DB에 없다. (3) 노트 `id`는 DB에서 유일하고 `path`도 유일하다.
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다(읽기만). FTS5 `bm25`/`snippet` 출력값과 임베딩 API의 응답 형식(`data[].embedding`)은 코드가 가정한 것이며 외부 시스템 쪽 보장은 확인하지 않았다(`미확인`).

### 1.5 필수 코드 참조
`~` = `research/repos/hyperresearch/src/hyperresearch/`

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `~/core/db.py:8-218` `SCHEMA_VERSION`, `SCHEMA_SQL`, `FTS_SQL` | 13개 테이블·인덱스·CHECK·FTS 가상 테이블 DDL 전문 | R-03 |
| C-02 | `~/core/db.py:220-256` `POST_MIGRATE_INDEXES_SQL`, `get_connection`, `init_schema` | 연결 PRAGMA, 스키마 초기화 순서 | R-03 |
| C-03 | `~/core/migrations.py:273-396` `_migrate_v13_nullable_retraction`, `MIGRATIONS`, `get_schema_version`, `migrate` | v13 테이블 재생성, 마이그레이션 진입·버전 갱신 | R-03 R-04 |
| C-04 | `~/core/migrations.py:15-271` `_migrate_v6`…`_migrate_v12`, `_MIGRATE_V10_ESCALATIONS_SQL` | 구버전 DB를 올릴 때만 필요한 단계별 변경(신규 구현이 구버전 호환을 안 하면 불필요) | R-03 |
| C-05 | `~/models/note.py:13-155` `NoteStatus`·`NoteType`·`Tier`·`ContentType`, `slugify`, `NoteMeta`, `Note` | 어휘, slug 규칙, 필드 기본값·검증 | R-05 R-06 |
| C-06 | `~/core/frontmatter.py:11-55` | 정규식, 파싱·직렬화·`render_note` | R-05 |
| C-07 | `~/core/note.py:26-172` `STUB_SUMMARY_PREFIX`, `read_note`, `_collision_id`, `indexed_note_ids`, `write_note` | 노트 읽기·쓰기·충돌 접미사 | R-06 R-07 R-08 |
| C-08 | `~/core/note.py:175-196` `strip_markdown` | FTS용 평문 변환 | R-09 |
| C-09 | `~/core/patterns.py:24`, `:60-150`, `:161-250` `WIKI_LINK_RE`, `strip_code`, `is_valid_wiki_link_target` 및 `_*_RE` | 코드 제거와 위키링크 대상 필터 전부 | R-10 |
| C-10 | `~/core/sync.py:59-145` `_has_frontmatter`, `compute_sync_plan` | 스캔 대상·mtime/해시 판정 | R-11 R-12 |
| C-11 | `~/core/sync.py:148-364` `execute_sync` | 트랜잭션·순서·오류·충돌·이름 변경 판정 | R-13 R-14 |
| C-12 | `~/core/sync.py:367-607` `_rename_note_id`, `_upsert_note_to_db`, `_delete_note_from_db`, `_resolve_links_incremental`, `_resolve_null_links` | 이름 변경 이동 표, upsert 칼럼 목록, 링크 해소 순서 | R-14 R-15 R-16 R-17 |
| C-13 | `~/search/fts.py:19-192` | 질의 변환, `search_fts` SQL, 결과 매핑, 재정렬 | R-18 R-19 R-21 |
| C-14 | `~/search/filters.py:8-136` `SearchFilters` | 필터→WHERE 변환 전부 | R-20 |
| C-15 | `~/core/embed.py:29-234` | 제공자 호출, `embed_sync`, `semantic_search`, `reciprocal_rank_fusion` | R-24 R-25 |
| C-16 | `~/cli/search.py:11-240` `search` | 옵션, 오류 코드, 결합·본문·토큰 예산·울타리 적용 순서 | R-22 R-23 R-25 R-27 |
| C-17 | `~/core/untrusted.py:19-62` | 울타리 판정·감싸기(안내문 전문 포함) | R-26 |
| C-18 | `~/cli/note.py:164-295` `note_show` | 필드 구성, `oa` 블록, 울타리 적용, `--raw/--meta` | R-27 R-28 |
| C-19 | `~/core/vault.py:12-221` | 볼트 레이아웃, `init`·`discover`·`auto_sync` | R-01 R-02 |
| C-20 | `~/core/config.py:140-152`, `:215-318` `EmbeddingSettings`, `VaultConfig`(검색·sync 기본값, `load`) | config 기본값과 TOML 키 이름 | R-19 R-21 R-24 |
| C-21 | `~/cli/main.py:15-169` `init`, `status`, `sync` | 명령 옵션·출력·오류 코드 | R-29 |
| C-22 | `~/models/output.py:11-28`, `~/cli/_output.py:25-37` | JSON 봉투와 `exclude_none` 출력 | 1.3 CLI |

### 1.6 수락 사례
출처: 모두 구현에서 도출(원본 테스트는 열지 않음). 실행하지 않은 손계산이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-18 | `preprocess_query('mamba3 python async')` | `"mamba"* "3"* "python"* "async"*` |
| T-02 | R-18 | `preprocess_query('"async await" python')` | `"async await" "python"*` |
| T-03 | R-18 | `preprocess_query('a AND b')` | 원문 `a AND b` 그대로 |
| T-04 | R-19 | `search ""`(필터 없음) | `BAD_QUERY`, 종료 2. `search "" --tag x`는 `tag x` 노트를 `created` 내림차순으로 score 0.0, 스니펫=summary로 반환 |
| T-05 | R-12 | 파일 mtime만 바뀌고 바이트 같음 | `unchanged`로 분류(DB는 그대로). 바이트가 바뀌면 `to_update`. `sync --force`는 해시 없이 모든 기존 파일이 `to_update` |
| T-06 | R-12 R-16 | DB에 있는 노트 파일을 삭제하고 sync | `to_delete`→ 노트·태그·본문·링크 소스 행 삭제, `claims` 행도 CASCADE로 삭제, `claims_fts` 행은 남음 |
| T-07 | R-14 | `a.md`와 `b.md`가 모두 `id: x` | 먼저 처리된 쪽만 색인되고 다른 쪽은 `errors`에 `id collision: 'x' already belongs to …` |
| T-08 | R-08 R-06 | `write_note(notes_dir, "Foo Bar")`를 두 번 | 첫 번째 `foo-bar.md`(id `foo-bar`), 두 번째 `foo-bar-2.md`(id `foo-bar-2`). 파일이 없어도 `taken_ids`에 `foo-bar`가 있으면 첫 호출이 이미 `foo-bar-2` |
| T-09 | R-06 | `slugify("Hello, World!")`, `slugify("!!!")` | `hello-world`, `note-e3b0c442` |
| T-10 | R-26 | 본문에 `</untrusted-source>`, url=`http://a/"b` | 본문의 닫는 태그가 `</untrusted-source-inner>`로 바뀌고 url 속성은 `http://a/&quot;b` |
| T-11 | R-26 R-27 | `source: https://x`, `type: note`로 `note show -j` / `type: interim`으로 | 앞쪽은 `body`가 울타리, `untrusted: true`. 뒤쪽은 원문, `untrusted` 키 없음 |
| T-12 | R-25 | `reciprocal_rank_fusion([["a","b"],["b","c"]])` | `[("b", 1/61+1/62≈0.0325), ("a", 1/61≈0.0164), ("c", 1/62≈0.0161)]`. b는 첫 목록 순위 1, 둘째 목록 순위 0 |
| T-13 | R-22 R-25 | `provider="none"`에서 `search foo --semantic` | `EMBEDDINGS_DISABLED`, 종료 1(FTS 질의는 이미 실행됨) |
| T-14 | R-22 | `search foo --tier bogus --json` | `{ok:false, error_code:"INVALID_TIER"}`, 종료 1 |
| T-15 | R-03 R-04 | `schema_version=12`이고 `is_retracted INTEGER NOT NULL DEFAULT 0`인 DB를 열기 | v13 적용: 0→NULL, 모든 노트 `file_mtime=0`·`content_hash=''`. 이어지는 sync가 모든 노트를 `to_update`로 처리해 frontmatter 값을 복원 |
| T-16 | R-15 | `centrality_score=0.4`인 노트의 본문만 고쳐 sync | `centrality_score`는 0.4 그대로 |
| T-17 | R-17 | 노트 A 본문 `[[Foo Bar]]`, 제목이 `foo bar`인 노트 B만 존재 | A의 링크 `target_id`는 B의 id(제목 일치, 대소문자 무시). 이후 id가 `Foo Bar`인 노트가 추가되면 id 일치가 먼저라 그쪽으로 바뀜 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
`~` = `research/repos/hyperresearch/src/hyperresearch/`, 기준 repo@aece65f.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | `~/core/vault.py:198-211` `discover`, `:75-77` `is_initialized` | 코드를 직접 읽음 |
| R-02 | `~/core/vault.py:139-196` `init`, `~/cli/main.py:15-37` | 직접 읽음. 에이전트 문서 주입 내용은 행 1 |
| R-03 | C-01, C-02, `~/core/vault.py:65-73` | 직접 읽음 |
| R-04 | C-03(`migrations.py:273-312`) | 직접 읽음 |
| R-05 | C-06, `~/core/sync.py:194-203`(오류 수집) | `yaml.safe_load` 예외를 `parse_frontmatter`가 잡지 않음을 확인 |
| R-06 | C-05(`slugify` `:56-81`), C-07(`read_note` `:47-50`), `NoteMeta.ensure_slug` `:132-137` | 직접 읽음 |
| R-07 | C-07(`read_note` `:34-71`) | 직접 읽음 |
| R-08 | C-07(`write_note` `:97-172`, `_collision_id` `:74-89`) | 직접 읽음. `author` 같은 `NoteMeta`에 없는 키는 `extra=ignore`로 버려짐(`models/note.py:139`) |
| R-09 | C-08 | 직접 읽음 |
| R-10 | C-09 | 정규식·필터 전부 읽음 |
| R-11 | C-10(`sync.py:97-116`, `:59-81`), `~/core/sync.py:53-56` `_should_exclude`·`~/core/config.py:235-240` | `exclude_patterns`와 `_should_exclude`가 코드 어디서도 호출되지 않음을 `grep`으로 확인 |
| R-12 | C-10(`sync.py:118-145`) | 직접 읽음 |
| R-13 | C-11(`sync.py:148-364`) | 직접 읽음 |
| R-14 | C-11(`sync.py:160-292`), C-12(`:367-426`) | 직접 읽음 |
| R-15 | C-12(`sync.py:429-537`) | 직접 읽음. 파생 점수 4칼럼이 INSERT/UPDATE 목록에 없음을 확인 |
| R-16 | C-12(`sync.py:540-544`), `~/core/db.py` 외래키 | CASCADE는 DDL 선언과 `PRAGMA foreign_keys=ON`(`db.py:236`)에서 추론. `claims_fts`는 `_delete_note_from_db`에 삭제문이 없음을 확인 |
| R-17 | C-12(`sync.py:547-607`) | 직접 읽음 |
| R-18 | C-13(`fts.py:19-63`) | 직접 읽음 |
| R-19 | C-13(`fts.py:66-165`) | 직접 읽음. SQLite의 실제 `bm25` 부호·`snippet` 출력은 SQLite 문서 지식(추론) |
| R-20 | C-14 | 직접 읽음 |
| R-21 | C-13(`fts.py:167-190`) | 직접 읽음 |
| R-22 | C-16(`search.py:48-130`, `:229-240`) | 직접 읽음 |
| R-23 | C-16(`search.py:176-206`) | 직접 읽음 |
| R-24 | C-15(`embed.py:59-167`, `:170-222`), `~/cli/embed_cmd.py:15-52` | 직접 읽음. 응답 형식은 코드의 가정(미확인) |
| R-25 | C-16(`search.py:132-174`), C-15(`:225-234`) | 직접 읽음 |
| R-26 | C-17 | 직접 읽음 |
| R-27 | C-16(`search.py:208-217`), C-18(`note.py:224-229`), `~/mcp/server.py:79`·`:106`·`:129` | `wrap_body`/`is_untrusted`를 `grep`해 호출처가 두 곳뿐임을 확인. README(`README.md:333`·`:341`)는 "`note show`와 `search` 두 경로"라 써서 일치하나, 같은 본문을 내보내는 MCP 경로는 울타리가 없다 |
| R-28 | C-18(`note.py:177-229`) | 직접 읽음 |
| R-29 | C-21(`main.py:40-169`) | 직접 읽음 |
| T-01~T-17 | R-ID와 같은 위치 | 손계산. 실행하지 않음 |

**문서와 구현의 차이**
- README(`README.md:248`)는 "SQLite 색인은 완전히 재구성 가능"하다고 쓰지만, `sources`·`assets`·`tag_aliases`·`api_cache`·`escalations`·`claims`·`embeddings`·파생 점수 칼럼은 마크다운에 없는 DB 전용 상태다(INSERT 지점은 `cli/fetch.py:562`·`:721`, `core/escalation.py:50`, `cli/tag.py:55` 등). DB를 지우고 `sync`하면 이들이 사라진다. 코드 확인.
- `config.toml`의 `[sync] exclude_patterns`(기본 목록 있음)는 저장·로드만 되고 동기화가 쓰지 않는다. 실제 제외는 R-11의 세 가지 하드코딩 규칙이다. 코드 확인.
- `execute_sync`는 에셋 폴더를 `vault.root / "research" / "assets"`로 고정한다(`sync.py:158`). `research_dir`을 바꾼 볼트에서는 이름 변경 때의 에셋 보존 판정이 실제 폴더와 어긋날 수 있다. 코드 확인(영향은 추론).
- `core/untrusted.py` 머리 주석은 "fetched note bodies land in subagent prompts via `hpr note show`"라서 CLI 경로만 전제한다. MCP `read_note`·`read_many`·`search`는 같은 본문을 울타리 없이 낸다(R-27). 코드 확인.

### 2.2 코드 읽는 순서
`~/core/vault.py` → `~/core/db.py`(스키마) → `~/models/note.py`·`~/core/frontmatter.py`·`~/core/note.py`(노트 형태와 쓰기) → `~/core/sync.py`(`compute_sync_plan` → `execute_sync` → `_upsert_note_to_db` → 링크 해소; 이름 변경 블록은 맨 마지막에) → `~/search/fts.py`·`filters.py` → `~/cli/search.py` → `~/core/embed.py` → `~/core/untrusted.py`·`~/cli/note.py:165`. 원본의 전략: 파일 비교는 mtime 먼저·해시는 mtime이 다를 때만(싼 검사 우선), 모든 쓰기를 한 트랜잭션+노트별 SAVEPOINT로 묶어 한 파일의 실패가 나머지를 막지 않게 한다.
