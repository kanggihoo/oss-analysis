---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/core/engine-factory.ts
  - src/core/config.ts
  - src/core/gbrain-env-file.ts
  - src/core/behavior-change-notice.ts
  - src/core/ai/gateway.ts
  - src/core/engine-connect.ts
  - src/core/engine.ts
  - src/core/types.ts
  - src/core/migrate.ts
  - src/core/migrate-pending.ts
  - src/core/migration-timeout.ts
  - src/core/init-schema-retry.ts
  - src/core/schema-migrations/types.ts
  - src/core/schema-migrations/latest.generated.ts
  - src/core/schema-migrations/registry.generated.ts
  - src/core/schema-migrations/v045-facts-hot-memory-v0-31.ts
  - src/core/schema-migrations/v047-facts-notability-alter.ts
  - src/core/schema-migrations/v051-facts-fence-columns.ts
  - src/core/schema-migrations/v054-cjk-wave-pages-chunker-version-and-source-path.ts
  - src/core/schema-migrations/v067-facts-typed-claim-columns.ts
  - src/core/schema-migrations/v089-facts-event-type-column.ts
  - src/core/schema-migrations/v122-facts-ontology-dimension.ts
  - src/core/schema-migrations/v145-facts-kind-idea-alter.ts
  - src/core/schema-migrations/v166-fact-embedding-identity.ts
  - src/core/schema-migrations/v167-facts-superseded-by-set-null.ts
  - src/core/schema-migrations/v215-facts-attributed-to.ts
  - src/core/schema-migrations/v177-pages-database-only-reason.ts
  - src/core/schema-migrations/v226-trust-tiers.ts
  - src/core/schema-migrations/v248-segmented-page-storage.ts
  - src/core/schema-migrations/v264-set-based-fact-insert-guards.ts
  - src/core/pglite-engine.ts
  - src/core/pglite-lock.ts
  - src/core/pglite-schema.ts
  - src/core/pglite-schema.generated.ts
  - src/core/postgres-engine.ts
  - src/core/postgres-engine/init-schema-lock.ts
  - src/core/postgres-engine/schema-lock-timeout.ts
  - src/core/db.ts
  - src/core/stored-embedding-identity.ts
  - src/core/vector-index.ts
  - src/core/fts-language.ts
  - src/core/ai/defaults.ts
  - src/core/page-state/schema.ts
  - src/core/persistence/attribution-schema.ts
  - src/core/facts/insert-guard-schema.ts
  - src/core/engine-sql/facts.ts
  - src/core/markdown.ts
  - src/commands/init.ts
  - src/cli/main.ts
  - src/schema.sql
  - scripts/build-schema.ts
  - README.md
  - docs/architecture/system-of-record.md
depends: []
status: ready
reimplementation: 미실행
---

# 엔진 선택·스키마·마이그레이션

> `~/.gbrain/config.json`(또는 환경변수)이 가리키는 PGLite(로컬 WASM Postgres) 또는 Postgres 엔진을 만들어 연결하고, 내장 스키마를 올린 뒤 번호가 붙은 마이그레이션(v2~v264)을 오름차순으로 적용해 `pages`·`content_chunks`·`facts` 등 핵심 테이블의 현재 모양을 만든다. 후속 스펙이 쓰는 핵심 테이블의 컬럼 의미는 1.3에서 공유 정의로 확정한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 설정 해석: `loadConfig()`가 `~/.gbrain/.env`(없는 변수만 채움) → `~/.gbrain/config.json` → 환경변수 `GBRAIN_DATABASE_URL`/`DATABASE_URL` 순으로 합쳐 `engine`(`pglite`|`postgres`)과 `database_url`/`database_path`를 정한다. 아무 설정도 없으면 `null`이고 CLI는 "No brain configured"로 끝낸다.
2. 엔진 생성: `createEngine(toEngineConfig(config))`가 `config.engine || 'postgres'`에 따라 `PGLiteEngine` 또는 `PostgresEngine`을 동적 import로 만든다. 그 밖의 값은 오류다.
3. 연결: `connectWithRetry`가 `engine.connect`를 부른다(최대 3회, 1s·2s 대기). PGLite는 `database_path` 디렉터리를 열고(없으면 메모리) 데이터 디렉터리 락을 잡는다. Postgres는 `database_url`로 풀을 연다.
4. 스키마 올리기: `gbrain init`은 `engine.initSchema()`를 직접(Postgres는 `runInitSchemaWithRetry`로) 부르고, 일반 명령은 `hasPendingMigrations`가 참일 때만 `tryRunPendingMigrations`로 `initSchema()`를 부른다. `initSchema()`는 (임베딩 차원·모델 결정) → 내장 스키마 블롭 재생 → `runMigrations` 순으로 간다. Postgres는 여기에 advisory lock 42, 스키마 검증·자가 치유, 좀비 HNSW 인덱스 정리가 붙는다.
5. 마이그레이션: `runMigrations`가 DB `config.version`(없으면 1)보다 큰 마이그레이션을 오름차순으로 하나씩 적용하고, 하나가 성공할 때마다 `config.version`을 그 번호로 올린다. 실패하면 그 자리에서 던지고 이미 올린 번호는 유지된다. down(되돌리기)은 없다.
6. `gbrain init`은 성공한 뒤에야 `config.json`을 쓴다(`engine`, `database_path` 또는 `database_url`, 임베딩 식별자 등).

### 1.2 범위·통합 지점

- 제공: 엔진 선택(PGLite/Postgres), 설정 해석과 저장 위치, 연결, 스키마 블롭 + 마이그레이션으로 만든 DB 모양, 핵심 테이블의 공유 정의(1.3), 후속 스펙이 쓰는 `BrainEngine` 메서드 군의 이름·의미.
- 제외:
  - 다른 약 120개 테이블(minion 큐, OAuth, eval, 저널, 신념 원장 등)의 DDL. 각 기능 스펙 소관이고 이 스펙은 이름만 언급한다. `schema.sql`이 원본이다(C-13).
  - 개별 마이그레이션 259개의 본문. 핵심 테이블을 바꾸는 것만 C-14·C-19로 가리킨다.
  - 임베딩 모델 선택·게이트웨이(`configureGateway`, 모델 ID 해석)와 `embedding_dimensions`의 출처 결정. 이 스펙은 `initSchema`가 `getEmbeddingDimensions()`/`getEmbeddingModel()`을 읽는다는 경계만 정의한다.
  - 엔진 졸업(graduation)·마운트 엔진·WAL 복구·`reinit-pglite`·`migrate-engine`·`gbrain doctor`. 연결 경로에 끼어드는 지점만 R-24에 적었다.
  - 페이지 쓰기 저널(`persistence/*`), 분할 저장(Wave B)의 동작. 컬럼 의미만 1.3에 둔다.
  - SQLite 지원(없음).
- 외부 의존·선행 계약: PGLite 쪽은 `@electric-sql/pglite`(WASM)와 번들된 `vector`, `pg_trgm`. Postgres 쪽은 서버가 pgvector를 제공해야 한다. 서버 확장 설치는 호출자 몫이다. 선행 스펙은 없다.
- 소유 상태·부작용: `~/.gbrain/config.json`(0600, 원자적 교체)과 `~/.gbrain/.gitignore`(`*`), PGLite 데이터 디렉터리와 그 옆 락 파일, DB의 모든 테이블·함수·트리거·확장, `config` 테이블의 `version`·`embedding_*` 행.

### 1.3 인터페이스와 데이터 의미

#### (가) 설정 위치와 키

| 이름 | 의미 | 기본값 | 잘못된 입력 |
|---|---|---|---|
| `GBRAIN_HOME` | 설정 홈의 부모. 실제 디렉터리는 항상 `<GBRAIN_HOME>/.gbrain` | 미설정이면 `~/.gbrain` | 상대 경로면 `GBRAIN_HOME must be an absolute path; got: …` 던짐, `..` 조각이 있으면 `GBRAIN_HOME must not contain '..' segments; …` 던짐. 공백뿐인 값은 미설정 취급 |
| `config.json` 위치 | `<설정 홈>/config.json`, 쓸 때 `0600`, tmp 파일 후 rename | — | 읽기 실패(없음·JSON 오류)는 없는 것으로 취급. 환경 URL도 없으면 `loadConfig()`가 `null` |
| `<설정 홈>/.env` | `loadConfig()`가 먼저 읽어 `process.env`에 없는 키만 채운다. 빈 값은 채우지 않음 | 없음 | 파일 없음·읽기 실패는 무시 |
| `config.json` `engine` | `"pglite"` 또는 `"postgres"` | 아래 추론 규칙 | `createEngine`이 알 수 없는 값을 거부(R-01) |
| `config.json` `database_path` | PGLite 데이터 디렉터리 | `init`이 쓰는 값은 `<설정 홈>/brain.pglite`(또는 `--path`) | 설정 파일에 없고 엔진이 pglite이면 메모리 DB로 열린다(R-13) |
| `config.json` `database_url` | Postgres 접속 문자열 | 없음 | Postgres 연결 시 없으면 `GBrainError "No database URL"`(R-14) |
| `GBRAIN_DATABASE_URL` | 최우선 접속 URL. 있으면 `engine=postgres`로 강제, `database_path` 무시 | 없음 | — |
| `DATABASE_URL` | `GBRAIN_DATABASE_URL`이 없을 때만 쓰는 접속 URL. 단 현재 디렉터리의 `.env*`에 같은 값이 적혀 있으면(Bun이 자동 로드한 것) 무시하고 stderr에 한 번 경고 | 없음 | 무시될 때 설정 파일 엔진 사용 |
| `GBRAIN_POOL_SIZE` | Postgres 풀 최대 연결 수 | 10 (`DEFAULT_POOL_SIZE_FALLBACK`) | 숫자가 아니거나 0 이하면 무시하고 10 |
| `GBRAIN_NO_RETRY_CONNECT=1` 또는 `--no-retry-connect` | 연결 재시도 끔(1회) | 재시도 3회 | `1` 이외 값은 꺼짐 아님 |
| `GBRAIN_INITSCHEMA_LOCK_TIMEOUT_SECONDS` | Postgres `initSchema` advisory lock 대기 한도 | 600초(폴 500ms, 5초마다 heartbeat) | 숫자가 아니거나 0 이하면 기본값 |
| `GBRAIN_SCHEMA_LOCK_TIMEOUT_SECONDS` | 마이그레이션·스키마 재생의 `lock_timeout` | 60초 | 숫자가 아니거나 0 이하면 기본값 |
| `GBRAIN_MIGRATE_BACKOFF_MS` | 마이그레이션 재시도 대기(테스트용) | 5000/15000/45000 ms | `parseInt` 실패 시 0 |
| `GBRAIN_MIGRATE_VERBOSE=1` | 새 설치에서도 마이그레이션 이름을 전부 출력 | 새 설치는 한 줄 요약 | — |
| `GBRAIN_FTS_LANGUAGE` | 스키마 텍스트의 `to_tsvector('english',` 리터럴을 이 값으로 치환 | `english` | `^[a-z][a-z0-9_]*$` 불일치면 경고 후 `english` |
| `GBRAIN_PGLITE_SNAPSHOT` | 메모리 DB(데이터 디렉터리 없음)일 때만 스키마 적용 후 덤프를 읽어 재생 생략 | 없음 | 파일이 없으면 경고 후 일반 초기화 |
| `GBRAIN_DIRECT_DATABASE_URL`, `GBRAIN_DISABLE_DIRECT_POOL=1\|true` | 풀러 URL에서 DDL용 직접 연결 URL 지정/끄기 | 풀러 URL에서 유도 | 이 스펙은 이름·존재만 다룬다(동작 미확인) |

설정 해석 결과 `engine`을 정하는 규칙은 C-02, 마이그레이션 번호 상수는 `LATEST_VERSION`(R-17)이다.

두 층의 설정이 있다. 파일 층(`config.json`)은 기계별 설정이고 DB 층은 `config` 테이블(`getConfig`/`setConfig`/`unsetConfig`)이다. 비동기 로더 `loadConfigWithEngine`의 우선순위는 "env > file > DB > 기본값"이다(`config.ts` 주석). 단 `embedding_model`/`embedding_dimensions`는 DB 층 병합 대상이 아니다.

#### (나) 코어 테이블 공유 정의

DDL 원본은 `schema.sql`(C-13)과 마이그레이션(C-14, C-19)이다. 아래는 컬럼 의미와 후속 스펙이 기대하는 불변식이다. "마이그레이션 전용"은 `schema.sql`의 CREATE TABLE에 없고 마이그레이션이 추가하는 컬럼이다. 새 설치도 모든 마이그레이션을 재생하므로 최종 모양에는 항상 있다(R-17).

**`sources`** — 한 DB 안의 논리 브레인(저장소). `id TEXT PK`(불변 인용 키, `[a-z0-9-]{1,32}`는 앱 계층 검증), `name UNIQUE`, `local_path`(파일 기반 소스의 git checkout 루트), `last_commit`, `last_sync_at`, `config JSONB`(`federated` 등), `archived`/`archived_at`/`archive_expires_at`(소프트 삭제), `contextual_retrieval_mode`, `trust_frontmatter_overrides`, `created_at`. 스키마가 `id='default'` 행(`federated:true`)을 시드한다. 마이그레이션 전용: `incarnation UUID NOT NULL UNIQUE`(소스 인스턴스 식별).

**`pages`** — 페이지(마크다운 파일 한 개 또는 DB 전용 항목) 한 행.

| 컬럼 | 의미 |
|---|---|
| `id SERIAL PK` | `content_chunks`·`links`·`tags`·`timeline_entries`·`raw_data`·`page_versions`가 FK로 가리킨다 |
| `source_id TEXT NOT NULL DEFAULT 'default'` | `sources(id)` FK, 소스 삭제 시 cascade |
| `slug TEXT NOT NULL` | 소스 안의 식별자. `UNIQUE(source_id, slug)`(`pages_source_slug_key`). 전역 유일 아님 |
| `type TEXT NOT NULL` | 페이지 타입 문자열(열린 집합, 스키마 팩이 정함) |
| `page_kind` | `markdown`(기본)·`code`·`image`, CHECK |
| `title` | 제목 |
| `compiled_truth TEXT` | 본문에서 타임라인 구분자 앞부분(기본 `''`). 분할 저장 페이지는 NULL |
| `timeline TEXT` | 구분자 뒷부분(기본 `''`). 분할 저장 페이지는 NULL |
| `frontmatter JSONB NOT NULL DEFAULT '{}'` | YAML frontmatter 파싱 결과 |
| `content_hash TEXT` | 가져오기 동일성 해시(NULL 가능). 중복 검사는 `content_hash` 또는 `frontmatter->>'id'` 일치 + `deleted_at IS NULL`(`findDuplicatePage`) |
| `emotional_weight REAL` | 0~1, 기본 0. 사이클 단계가 계산 |
| `created_at`, `updated_at TIMESTAMPTZ` | 행 생성·수정 시각 |
| `deleted_at` | NULL이면 살아 있음. `delete_page`는 소프트 삭제로 값을 채우고, 기본 읽기·검색은 `deleted_at IS NULL`만 본다. 72시간 뒤 purge 단계가 하드 삭제 |
| `effective_date`, `effective_date_source`, `import_filename`, `salience_touched_at` | 콘텐츠 날짜(frontmatter 우선순위 규칙), 그 출처, 가져올 때의 파일 기본 이름, 현저성 갱신 시각 |
| `last_retrieved_at`, `links_extracted_at` | 마지막 조회 시각(레거시, 현재는 `page_retrievals`가 기록), 링크·타임라인 추출 워터마크(NULL=한 번도 안 함) |
| `generation BIGINT` | 트리거가 INSERT/내용 변경 시 올리는 캐시 무효화 카운터 |
| 마이그레이션 전용 | `source_path`(소스 기준 정규 파일 경로), `chunker_version SMALLINT DEFAULT 1`, `knowledge_revision UUID`(정규 내용이 바뀌면 트리거가 새 UUID), `text_projection_revision UUID`(검색용 청크가 설치된 revision), `search_vector tsvector`(title 'A' + timeline 앞 65,536자 'C', compiled_truth 없음), `ingested_via`/`ingested_at`/`source_uri`/`source_kind`, `contextual_retrieval_mode`/`corpus_generation`/`embedding_signature`, `database_only_reason`, `links_attendance_blocked_*`, `links_extract_failure`, `emotional_weight_recomputed_at`, `trust_tier`/`write_origin`, `revision_write_*`(쓴 주체), 분할 저장 컬럼 `body_storage`·`body_bytes`·`truth_bytes`·`body_lines`·`body_generation`·`segment_count`·`segmenter_version`·`body_flags`·`truth_lead`·`timeline_lead` |

불변식: `body_storage='inline'`(기본)이면 `compiled_truth`·`timeline`이 NOT NULL, `'segmented'`면 둘 다 NULL이고 `body_bytes`가 있다(C-19 CHECK). 분할 저장의 코드 기본값은 `SEGMENTED_STORAGE_DEFAULT='on'`이다(`page-body/limits.ts:161,195`). 옛 버전 작성자가 최근에 쓴 흔적이 있으면 게이트가 막아 실제 켜짐은 브레인마다 다르다(`behavior-change-notice.ts:733`의 "기본 꺼짐" 문구는 코드와 다르다. 근거와 세부는 [page-storage-and-import.md](page-storage-and-import.md) 2.1).

**`content_chunks`** — 페이지를 쪼갠 검색 단위(청크)와 그 임베딩.

| 컬럼 | 의미 |
|---|---|
| `id SERIAL PK`, `page_id` | `pages(id)` FK, cascade. `UNIQUE(page_id, chunk_index)` |
| `chunk_index INTEGER` | 페이지 안 순번. 청크는 UPDATE하지 않고 페이지가 바뀌면 다시 INSERT한다(`updated_at` 없음) |
| `chunk_text` | 청크 본문 |
| `chunk_source` | `compiled_truth`(기본)·`timeline`·`fenced_code`(입력에는 `image_asset`도 있음) |
| `embedding vector(N)` | 텍스트 임베딩. 아직 안 만들었으면 NULL. N은 설치 시점에 정해진다(R-21) |
| `model TEXT NOT NULL` | 임베딩 모델 ID. 기본값은 설치 시점의 모델로 치환됨 |
| `token_count`, `embedded_at` | 토큰 수, 임베딩 시각 |
| `embedded_text_hash`, `embedding_input_hash` | 임베딩 당시 `md5(chunk_text)`, 임베딩 입력 출처 해시. NULL=임베딩 없음 또는 오래된 행 |
| `language`, `symbol_name`, `symbol_type`, `start_line`, `end_line`, `parent_symbol_path TEXT[]`, `doc_comment`, `symbol_name_qualified` | 코드 청크 메타. 마크다운 청크는 NULL |
| `search_vector tsvector` | 트리거가 `doc_comment`+`symbol_name_qualified`(가중 'A') + `chunk_text`('B')로 채운다 |
| `modality` | `text`(기본)·`image` |
| `embedding_image`, `embedding_multimodal vector(1024)` | 이미지·교차 모달 임베딩 |
| 마이그레이션 전용 | `embedding_pending_since`, `projected_byte_start`/`projected_byte_end`(청크가 읽기 투영 텍스트에서 차지하는 UTF-8 바이트 구간), 분할 페이지용 `occurrence_id`·`local_ordinal`·`raw_byte_start`·`raw_byte_end`·`body_generation`·`retired_generation` |

Postgres·PGLite 둘 다 `embedding`에 HNSW(`vector_cosine_ops`) 인덱스를 거는데, 차원이 2000을 넘으면 건너뛴다(정확 검색은 가능).

**`facts`** — 핫 메모리의 사실 한 건. `schema.sql`에 없고 마이그레이션 v045 핸들러가 만들고 뒤의 마이그레이션이 컬럼을 보탠다.

| 컬럼 | 의미 |
|---|---|
| `id BIGSERIAL PK`, `source_id TEXT NOT NULL DEFAULT 'default'` | `sources(id)` FK(`facts_source_id_fkey`), cascade |
| `entity_slug TEXT` | 사실의 주제인 엔티티 페이지의 slug(NULL 가능). `pages`와 FK는 없음 |
| `fact TEXT NOT NULL` | 사실 문장 |
| `kind` | `event`·`preference`·`commitment`·`belief`·`fact`(기본)·`idea`, CHECK `facts_kind_check` |
| `visibility` | `private`(기본)·`world`, CHECK |
| `notability` | `high`·`medium`(기본)·`low` |
| `context TEXT` | 부가 맥락 |
| `valid_from TIMESTAMPTZ NOT NULL DEFAULT now()`, `valid_until` | 사실이 유효한 시간 구간(이중 시간축의 유효 시간) |
| `expired_at` | NULL이면 활성. 값이 있으면 만료(삭제하지 않고 남김) |
| `superseded_by BIGINT` | 대체한 사실 id. FK `ON DELETE SET NULL`(v167) |
| `consolidated_at`, `consolidated_into BIGINT` | 야간 통합 단계가 `takes`로 올린 시각·대상 id |
| `source TEXT NOT NULL`, `source_session` | 출처 라벨(예: `mcp:put_page`, `cli:think`), 세션 ID |
| `confidence REAL` | 0~1, 기본 1.0, CHECK |
| `embedding halfvec(N)`(pgvector ≥ 0.7, 그 외 `vector(N)`), `embedded_at`, `embedding_model`, `embedded_text_hash` | 사실 임베딩과 그 식별. N은 v045 실행 시점의 `config.embedding_dimensions`(없으면 1536, 최대 4096) |
| `row_num INTEGER`, `source_markdown_slug TEXT` | 마크다운 `## Facts` 펜스 안의 행 번호와 그 페이지 slug. 둘 다 NULL이면 DB 전용(레거시) 사실. `UNIQUE(source_id, source_markdown_slug, row_num) WHERE row_num IS NOT NULL` |
| `claim_metric`, `claim_value DOUBLE PRECISION`, `claim_unit`, `claim_period`, `event_type` | 타입 있는 주장(지표)·이벤트 표지 |
| `dimension`, `value`, `value_hash`, `dim_status` | 온톨로지 차원 값. `dimension`이 NULL이면 일반 사실. `UNIQUE(source_id, entity_slug, dimension, value_hash, source_markdown_slug) WHERE dimension IS NOT NULL` |
| `attributed_to` | `user`·`assistant`·`other`·NULL(귀속 불명) |
| `created_at` | 행 생성 시각 |
| 마이그레이션 전용 부가 | `trust_tier TEXT NOT NULL DEFAULT 'unknown'`, `write_origin JSONB`, 쓴 주체 추적 `write_*`·`last_write_*`·`last_written_at` |

활성 사실의 정의는 `expired_at IS NULL`이다. INSERT 뒤에는 문장 단위 AFTER INSERT 트리거 `facts_guard_inserted`(v264)가 purge 묘비와 철회(withdrawal) 원장을 검사한다. 일치한 purge는 `purged_content` 오류로 문장을 중단시키고, 일치한 철회는 해당 행을 만료 처리한다.

**`links`** — 페이지 사이 방향 간선. `from_page_id`·`to_page_id`(둘 다 `pages(id)` cascade), `link_type TEXT NOT NULL DEFAULT ''`, `context`, `link_source`(kebab-case 출처 태그, NULL=레거시. 내부 예약값 `markdown`·`frontmatter`·`mentions`·`wikilink-resolved`, 사용자 값 `manual`), `link_kind`(`plain`·`typed_ner`·NULL), `origin_page_id`(frontmatter 간선의 원인 페이지, 삭제 시 SET NULL), `origin_field`, `resolution_type`(`qualified`·`unqualified`·NULL), `assertion_tense`(`present`·`past`·NULL), `created_at`. 유일 키는 `(from_page_id, to_page_id, link_type, link_source, origin_page_id)`이고 NULL끼리도 충돌로 본다(`NULLS NOT DISTINCT`).

**`tags`** — `page_id`, `tag`, `tag_source`(`frontmatter`=가져오기가 소유, `added`, NULL=레거시), `UNIQUE(page_id, tag)`.

**`timeline_entries`** — 구조화된 타임라인 행. `page_id`, `date DATE NOT NULL`, `source`(기본 `''`), `summary`, `detail`, `event_page_id`(이벤트 페이지 투영일 때만), `created_at`. 중복 키 `(page_id, date, md5(summary), source)`.

**`page_versions`** — 페이지 변경 시점의 스냅샷(`compiled_truth`, `frontmatter`, `snapshot_at`, 마이그레이션 전용 `title`·`type`·`timeline`·`tags`·`knowledge_revision`·`body_storage` 등). **`raw_data`** — 페이지별 사이드카 JSONB(`page_id`, `source`, `data`, `fetched_at`, `UNIQUE(page_id, source)`).

**`config`**(DB 층) — `key TEXT PK`, `value TEXT`. 스키마가 `version='1'`, `embedding_model`, `embedding_dimensions`, `chunk_strategy='semantic'`를 시드하고, PGLite 변형은 `engine='pglite'` 행도 시드한다. `version`은 적용된 마지막 마이그레이션 번호의 문자열이다.

페이지 삭제(하드)는 `content_chunks`·`links`·`tags`·`raw_data`·`timeline_entries`·`page_versions`로 cascade한다. `links.origin_page_id`는 SET NULL이다.

#### (다) 후속 스펙이 쓰는 `BrainEngine` 메서드 군

`BrainEngine`(`engine.ts`)은 두 엔진이 같은 이름·의미로 구현한다(`implements BrainEngine`). 전체를 옮기지 않고 후속 스펙이 쓰는 군만 둔다.

| 군 | 메서드 | 의미 |
|---|---|---|
| 수명주기 | `kind: 'postgres'\|'pglite'`, `connect(config)`, `disconnect()`, `reconnect()`, `initSchema()`, `transaction(fn)`, `executeRaw(sql, params)`, `runMigration(version, sql)`, `getConfig(key)`/`setConfig`/`unsetConfig` | 연결과 스키마, 트랜잭션 클론 엔진, 원시 SQL, DB 층 설정 |
| 페이지 | `getPage(slug, opts)`, `readPageSnapshot`, `putPage(slug, page, opts)`, `deletePage(slug, {sourceId})`(하드), `listPages(filters)`, `findDuplicatePage(s)` | `getPage`는 소프트 삭제된 행에 null. `putPage`는 `ON CONFLICT (source_id, slug)` 갱신이며 `opts.sourceId` 생략 시 `'default'`, 기존 본문을 빈 본문으로 덮는 것은 `allowEmptyOverwrite` 없이는 거부 |
| 청크 | `upsertChunks(slug, chunks, opts)`, `getChunks(slug, opts)`, `deleteChunks(slug)`, `getChunkPage`, `getEmbeddingsByChunkIds(ids, column?)` | `upsertChunks`는 해당 페이지의 청크 집합을 통째로 교체(단일 문장 DELETE+INSERT). `getChunks`는 기본적으로 벡터 제외 |
| 검색 | `searchKeyword(query, opts)`(페이지당 최고 청크), `searchKeywordChunks`(청크 단위), `searchTitles`(`pages.search_vector`), `searchVector(embedding, opts)` | 결과는 `SearchResult`(`slug`, `page_id`, `title`, `type`, `chunk_text`, `chunk_source`, `chunk_id`, `chunk_index`, `score`, …). 필터·점수는 검색 스펙 소관 |
| 사실 | `insertFact(input, {source_id, supersedeId?})`, `insertFacts(rows, {source_id}, opts)`, `deleteFactsForPage(slug, source_id, opts)`, `expireFact(id, opts)`, `listFactsByEntity`, `listFactsSince`, `listFactsKeyset`, `listFactsBySession`, `findCandidateDuplicates(source_id, entitySlug, factText, opts)`, `consolidateFact` | `insertFact`는 `{id, status}`(`inserted`·`superseded`·`duplicate`). `supersedeId`가 있으면 같은 트랜잭션에서 새 행 INSERT와 옛 행 `expired_at`·`superseded_by` 갱신. `insertFacts`는 펜스 행 일괄 삽입(`row_num`·`source_markdown_slug` 필수), `deleteFactsForPage`는 `(source_id, source_markdown_slug)` 기준 하드 삭제. `expireFact`는 행을 지우지 않고 만료 |
| 그래프·태그·타임라인 | `addLink`, `addLinksBatch`, `getLinks`, `getBacklinks`, `traverseGraph`, `addTag`, `getTags`, `addTimelineEntry`, `getTimeline` | `*Batch`는 `ON CONFLICT DO NOTHING`으로 실제 삽입 수를 반환 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `createEngine(config)` | 엔진 종류는 `config.engine \|\| 'postgres'`. `pglite`/`postgres`는 해당 엔진을 동적 import로 만들어 반환(PGLite WASM은 Postgres 사용자에게 로드되지 않음). 그 외 값은 `Unknown engine type: "<값>". Supported engines: postgres, pglite.`를 던지고, 값이 `sqlite`면 ` SQLite is not supported. Use pglite instead.`가 붙는다 (C-01) | 코드 확인 |
| R-02 | `createEngine` 반환 직전 | `gateway.chat()` 사용량 기록 싱크를 이 엔진의 `chat_usage_log`로 스택에 등록하고, `engine.disconnect`를 감싸 해제 시 등록도 풀게 한다. 엔진 선택과 무관한 부작용 | 코드 확인 |
| R-03 | `loadConfig()` | `<설정 홈>/.env`를 먼저 `process.env`에 병합(기존 변수 유지). `config.json`을 읽고(실패=없음), `effectiveEnvDatabaseUrl()`을 구한다. 파일도 URL도 없으면 `null`. URL이 있으면 `engine='postgres'`, `database_url=URL`, `database_path=undefined`(파일의 PGLite 선택을 덮음). 없으면 `engine = file.engine \|\| (file.database_path ? 'pglite' : 'postgres')` (C-02) | 코드 확인 |
| R-04 | `effectiveEnvDatabaseUrl()` | `GBRAIN_DATABASE_URL`이 있으면 그것. 아니면 `DATABASE_URL`인데, cwd의 `.env` 계열 파일에 같은 값이 있으면 무시(한 번 stderr 경고)하고 `undefined` (C-02) | 코드 확인 |
| R-05 | `configDir()` / `saveConfig(config)` | 디렉터리는 `<GBRAIN_HOME 또는 홈>/.gbrain`. `saveConfig`는 디렉터리 생성 → `config.json.tmp-<pid>`에 2칸 들여쓰기 JSON + 개행을 `0600`으로 쓰고 rename → chmod 시도(실패 무시) → `ensureGitignore()`(`.gitignore`가 없거나 빈 경우에만 `*\n`) | 코드 확인 |
| R-06 | `gbrain init` 엔진 결정(`--migrate-only`·`--mcp-only`·`--prefer-postgres` 제외) | `--pglite`면 PGLite. `--supabase` 또는 `--url <u>`면 Postgres. 아무 플래그도 없고 대화형이면 PGLite(cwd에 `.md`가 1000개 이상이면 Supabase 권장 문구만 출력하고 PGLite로 진행). `--non-interactive`는 `--url` 또는 `effectiveEnvDatabaseUrl()`이 없으면 `--non-interactive requires --url <connection_string> or GBRAIN_DATABASE_URL env var`를 찍고 exit 1. `--force`이고 엔진 플래그가 없으며 파일이 `engine=postgres`+`database_url`이면 그 Postgres를 보존 (C-17) | 코드 확인 |
| R-07 | `gbrain init` PGLite 경로 | `dbPath = --path \|\| <설정 홈>/brain.pglite`. `createEngine({engine:'pglite'})` → `connect({database_path, engine})` → 임베딩 차원 충돌 검사(기존 `content_chunks.embedding` 차원 ≠ 요청 차원이면 오류 종료) → `initSchema()` → 사후 차원 불변식 검사 → `config.json` 저장(`engine:'pglite'`, `database_path`, 기존 키 유지, `database_url`·`remote_mcp` 삭제). 설정 저장은 스키마 성공 뒤 | 코드 확인 |
| R-08 | `gbrain init` Postgres 경로 | `createEngine({engine:'postgres'})` → `connect({database_url})` → 같은 차원 검사 → `runInitSchemaWithRetry`(재시도 가능한 오류에 최대 5회, 기본 15초 대기, 락 차단이면 2초) → 사후 검사 → 저장(`engine:'postgres'`, `database_url`, `database_path` 제거) | 코드 확인 |
| R-09 | `gbrain init --migrate-only` | 설정을 읽어 이미 구성된 엔진에 스키마 적용만 하고 `config.json`을 쓰지 않는다. 설정이 없으면 `No brain configured`로 실패 | 코드 확인 (진입 분기·메시지 조건만. `runMigrateOnlyCore` 본문 미열람) |
| R-10 | 일반 CLI 명령의 연결 | 브레인 축이 `host`가 아니면 마운트 엔진 경로. 아니면 `loadConfig()`가 `null`이면 `no_brain` 오류로 종료. 씬 클라이언트(`remote_mcp`만 있고 `database_url` 없음)는 로컬 엔진을 열지 않는다. 그 외 `configureGateway` → `createEngine` → `connectWithRetry` → 시작 훅 | 코드 확인 |
| R-11 | `connectWithRetry(engine, config, opts)` | 시도 횟수 3(`noRetry`면 1), 간격 `1000·2^i` ms. 재시도 가능한 연결 오류(`isRetryableDbConnectError`)에서만 재시도하고, 마지막 시도거나 재시도 불가면 원래 오류를 던진다 | 코드 확인 |
| R-12 | `tryRunPendingMigrations` 게이트 | 시작 훅은 `hasPendingMigrations`(=`parseInt(config.version \|\| '1') < LATEST_SCHEMA_VERSION`, `getConfig` 실패 시 true)일 때만 `migrate.ts`를 import해 `tryRunPendingMigrations`를 호출. 이 함수는 `initSchema()`를 최대 2번(교착 SQLSTATE `40P01`/메시지 `deadlock detected`면 250ms 후 한 번 재시도), 계속 교착이면 최대 5초 동안 250ms 간격으로 `hasPending`을 폴링해 풀리면 `race_resolved`, 아니면 `persistent`. 교착 아닌 오류는 `{status:'error'}`로 돌려준다. CLI는 `persistent`·`error`를 stderr 알림으로 쓰고 명령은 계속한다(던지지 않음) (C-15, C-16) | 코드 확인 |
| R-13 | `PGLiteEngine.connect(config)` | `database_path`가 없으면 메모리 DB(데이터 영속 없음). 있으면 연결 전에 `acquireLock(dataDir)`(기본 30초 대기. 시간 안에 못 잡으면 `PgliteBusyError`("Timed out waiting for PGLite data-dir lock…"), 핸들이 `acquired:false`로 돌아오면 `Could not acquire PGLite lock. Another gbrain process is using the database.`)로 데이터 디렉터리 소유 락을 잡고 `PGlite.create({dataDir})`. 락 흔적은 네이티브 커널 락 파일 `<dataDir>.gbrain-owner.lock`, 소유자 마커 `<dataDir>.gbrain-owner.json`, 메타데이터 디렉터리 `<dataDir>/.gbrain-lock`이다. 생성이 wasm-abort로 실패하면 지속 디렉터리에 한해 WAL 자동 복구를 시도(`GBRAIN_PGLITE_WAL_REPAIR=off`면 안 함). 그 외 실패는 락을 풀고 던진다 | 코드 확인 (복구 절차 세부는 범위 밖) |
| R-14 | `PostgresEngine.connect(config)` | `poolSize`가 있으면 인스턴스 풀을 만든다(`min(poolSize, resolvePoolSize)`). 없으면 모듈 싱글턴 풀(`db.connect`)이며 `database_url`이 없으면 `GBrainError("No database URL", "database_url is missing from config", "Run gbrain init --supabase or gbrain init --url <connection_string>")`. 이미 연결된 싱글턴이 있으면 새 URL은 경고만 하고 기존 연결 사용 | 코드 확인 |
| R-15 | `initSchema()` 공통 단계 | ① `getEmbeddingDimensions()`/`getEmbeddingModel()`(게이트웨이 미설정이면 던지므로 catch로 기본값 `voyage:voyage-4`·1024) ② `readStoredEmbeddingIdentity`: `content_chunks.embedding` 컬럼이 이미 있으면 그 `vector(n)`/`halfvec(n)`의 n과 `config.embedding_model`이 위 값을 이긴다. 모델 행이 비어 있으면 던짐(`Stored embedding model is unknown…`), 차원 파싱 불가도 던짐 ③ 순방향 참조 부트스트랩(구버전 DB가 블롭이 참조할 컬럼 등을 먼저 보충) ④ 내장 스키마 블롭 재생 ⑤ `runMigrations` ⑥ 적용 수가 0보다 크면 stderr에 `N migration(s) applied` (C-10, C-11, C-12) | 코드 확인 |
| R-16 | `PostgresEngine.initSchema()` 동시성·후처리 | DDL 연결(이중 풀이면 direct 풀)에 `pg_try_advisory_lock(42)`를 500ms 간격으로 시도(기본 600초, 초과 시 보유 pid와 `pg_terminate_backend` 안내 오류), 5초마다 heartbeat 출력. 락을 잡은 연결에서 부트스트랩·블롭 재생(`lock_timeout` 래핑)·`runMigrations`·`verifySchema`(누락 컬럼을 `ADD COLUMN IF NOT EXISTS`로 치유, 못 치유하면 던짐)·좀비 HNSW(`indisvalid=false`) 정리(최선 노력)를 실행하고 finally에서 `pg_advisory_unlock(42)`. PGLite는 advisory lock 대신 R-13의 파일 락을 쓰고 `verifySchema`·좀비 정리는 하지 않는다 (C-12) | 코드 확인 (락 폴링 파라미터는 `init-schema-lock.ts`) |
| R-17 | 스키마 블롭의 정체 | Postgres 블롭은 `schema.sql`을 내장한 문자열(`SCHEMA_SQL`), PGLite 블롭은 같은 `schema.sql`에서 `build-schema`가 만든 템플릿에 PGLite 규칙(pgcrypto 제거, 일부 컬럼·인덱스·트리거를 마이그레이션으로 미룸, `config`에 `engine='pglite'` 추가, Postgres 전용 테이블 제외)을 적용한 것. 블롭이 `config.version='1'`을 심으므로 새 설치는 v2~v264 259개 전부를 재생한다(새 설치는 stderr에 `Setting up brain schema (v264)...` 한 줄, 기존 DB는 마이그레이션별 진행 줄). 따라서 최종 모양 = 블롭 + 마이그레이션이며 `facts`와 `pages` 일부 컬럼은 마이그레이션에서만 생긴다 (C-09, C-13) | 코드 확인 |
| R-18 | 차원·모델 치환 | `getPostgresSchema(dims, model)`/`getPGLiteSchema(dims, model)`: `dims`가 양의 정수가 아니면 `Invalid embedding dimensions: <dims>`를 던진다. Postgres는 `vector(1536)`→`vector(dims)`, `'text-embedding-3-large'`→모델(작은따옴표 이스케이프), `('embedding_dimensions','1536')`→dims로 치환하고, PGLite는 `__EMBEDDING_DIMS__`/`__EMBEDDING_MODEL__` 자리표시자를 치환. 둘 다 `chunkEmbeddingIndexSql`(dims>2000이면 `idx_chunks_embedding` 생략)과 `applyFtsLanguagePolicy`(`GBRAIN_FTS_LANGUAGE`가 `english`가 아니면 `to_tsvector('english',` 치환)를 적용한다. 치환은 `CREATE ... IF NOT EXISTS`이므로 이미 있는 테이블 컬럼 크기는 바꾸지 않는다(R-15의 저장 식별자 우선이 그 보호) (C-09) | 코드 확인 |
| R-19 | `runMigrations(engine)` 본 루프 | `current = parseInt(config.version \|\| '1')`. `MIGRATIONS`를 `version` 오름차순 정렬(배열 순서는 무관)해 `version > current`만 `pending`. 없으면 `{applied:0, current}`. 있으면 각각 `applyOneMigration` → 성공 후에만 `setConfig('version', String(m.version))`. 끝나면 `{applied, current: LATEST_VERSION}`. 시작 전 `checkForBlockingConnections`가 Postgres에서 5분 넘게 `idle in transaction`인 세션이 있으면 경고만 한다. 진행 메시지는 stderr (C-05) | 코드 확인 |
| R-20 | `applyOneMigration(engine, m)` | SQL은 `m.sqlFor?.[engine.kind] ?? m.sql`(빈 문자열이면 건너뜀). SQL은 `runMigrationSQLWithRetry`(3회, 5s/15s/45s 대기)로 실행하되 재시도는 statement timeout(57014)·연결 끊김 계열만. 마지막 실패는 재시도 가능 계열이면 `MigrationRetryExhausted`(보유 세션 pid·`pg_terminate_backend` 안내)로 감싸 던지고, 아니면 원 오류. SQL 성공 후 `m.handler(engine)`(트랜잭션 밖), 그 뒤 `m.verify(engine)`(예외는 false). verify 실패 시 `idempotent`(기본 true)면 SQL과 handler를 한 번 더 돌리고 경고, `idempotent:false`면 `MigrationDriftError`를 던진다. 타임아웃이면 `config.schema_migration_timeout`에 기록하고, 한 번의 전체 통과가 끝나면 지운다 (C-06) | 코드 확인 |
| R-21 | `runMigrationSQL` 실행 모양 | `m.transaction !== false`이거나 PGLite: `engine.transaction` 안에서 실행하고 Postgres는 먼저 `SET LOCAL statement_timeout = '600000'`과 `SET LOCAL lock_timeout = '<ms>ms'`(실패 무시). `transaction:false`+Postgres(`CREATE INDEX CONCURRENTLY` 등): 예약 연결을 잡아 세션 `statement_timeout`을 올리고 락 타임아웃 래퍼로 실행한 뒤 `RESET statement_timeout`. `lock_timeout` 오류는 `schemaLockBlockedError`로 바꿔 던진다 (C-07) | 코드 확인 |
| R-22 | 마이그레이션 실패·롤백 | SQL이 실패하면 그 마이그레이션의 트랜잭션이 롤백되고 `config.version`은 직전 성공 번호에 머문다. 오류는 호출자로 전파된다(`initSchema` 실패). 핸들러는 트랜잭션 밖이라 핸들러 실패 시 SQL 효과는 남지만 버전은 올라가지 않으므로 다음 실행이 같은 마이그레이션을 다시 시도한다. down 마이그레이션 인터페이스는 없다(`Migration`에 `up`에 해당하는 `sql`/`sqlFor`/`handler`/`verify`만 있음) (C-08) | 코드 확인 |
| R-23 | `runMigrations`의 자가 치유 | 매 호출마다(보류가 없어도) 최선 노력으로 ① `idx_timeline_dedup`가 `(page_id,date,md5(summary),source)`가 아니면 재생성 ② `pages_source_slug_key UNIQUE(source_id, slug)`가 없으면 추가(중복 행이 있으면 오류 메시지만) ③ `current >= 114`일 때 `links_link_source_check`를 kebab 규칙으로 복구 ④ 페이지 revision 백필 재개. 실패는 삼키고 stderr만 남긴다 | 코드 확인 |
| R-24 | 연결 경로의 주변 장치 | 엔진 졸업 게이트(`gateGraduationConnect`)가 열린 엔진을 거절할 수 있고, PGLite `initSchema` 끝에서 `registerManagedFilesystemEngine`을 호출한다. 이 스펙은 존재와 호출 위치만 정의하고 동작은 정의하지 않는다 | 코드 확인 (호출 위치) / 미확인 (동작) |
| R-25 | 마이그레이션 레지스트리 | 259개(v002~v264, v017~v019·v100 결번, v001은 블롭의 `version='1'`). `LATEST_VERSION`/`LATEST_SCHEMA_VERSION`은 최대 `version`인 264. 파일은 `schema-migrations/v<NNN>-*.ts` 한 개당 1개이고 레지스트리는 생성 파일이다 | 코드 확인 |
| R-26 | 마크다운 원본과 DB의 관계 | 원본이 파일인지 DB인지는 소스가 체크아웃 루트(`sources.local_path` 등)에 묶였는지로 갈린다. 루트가 있으면 `put_page` 계열이 같은 저널 트랜잭션에서 `<루트>/<slug>.md`도 쓰고(write-through) 파일이 원본이며 DB는 파생 인덱스다. 루트가 없으면(새 `init` 직후 기본 상태) DB가 유일한 사본이다([page-storage-and-import.md](page-storage-and-import.md) 확정). 한 마크다운 파일은 `pages` 한 행(본문은 타임라인 구분자 앞 `compiled_truth`와 뒤 `timeline`으로 분리, frontmatter는 `frontmatter`)이 되고, 거기서 `content_chunks`(청킹+임베딩), `tags`·`links`·`timeline_entries`, `## Facts` 펜스의 `facts`(`source_markdown_slug`+`row_num`), `takes`가 파생된다. DB 전용으로 존재하는 것도 있다: `database_only_reason`이 있는 페이지, `row_num IS NULL`인 사실, `raw_data`, `page_versions` 이력, `config`의 일부, 큐·토큰·로그 계열. 저장·가져오기·동기화의 실제 방향과 순서는 [page-storage-and-import.md](page-storage-and-import.md)가 정한다 | 코드 확인 (write-through 분기는 `write-through.ts`의 `no_repo_configured` 등 `skipped` 사유, 상세 R-ID는 후속 스펙. 컬럼 존재는 이 스펙의 코드 확인) |
| R-27 | 지원 엔진 | 지원 엔진은 PGLite와 Postgres뿐이다. `BrainEngine.kind`는 두 값 유니온이고 `GBrainConfig.engine`·`EngineConfig.engine`도 같다. SQLite는 `createEngine`에서 명시적으로 거절된다 | 코드 확인 |

- 불변식: (1) `config.version`은 마지막으로 성공한 마이그레이션 번호이며 적용 순서는 번호 오름차순이다. (2) 한 소스 안에서 `slug`는 유일하다. (3) `content_chunks`에서 `(page_id, chunk_index)`는 유일하다. (4) `facts`의 활성 여부는 `expired_at IS NULL`로만 정해진다. (5) 이미 있는 `content_chunks.embedding`의 차원은 `initSchema`가 바꾸지 않는다(R-15, 변경은 별도 `migrate embeddings` 경로).
- 미결정: 없음.
- 확인 한계:
  - `bun`이 설치되어 있지 않고 `agent-memory/repos/gbrain/node_modules`가 없어 PGLite 메모리 DB에 스키마를 올려 테이블 목록을 조회하는 실행은 하지 않았다. 1.3의 컬럼은 `schema.sql`과 핵심 테이블을 바꾸는 마이그레이션의 정적 읽기이고, "마이그레이션 전용" 컬럼 목록은 `ALTER TABLE ... ADD COLUMN`과 TS 스키마 조각을 검색해 모은 것이라 실제 DB의 `information_schema`와 대조하지 못했다(후속 스펙이 쓰는 핵심 컬럼은 이름이 맞다).
  - 약 120개 비핵심 테이블, 개별 마이그레이션 본문 대부분, 트리거 함수 본문(세대 증가, revision, 신뢰 계층, 쓰기 귀속)은 열지 않았다.
  - `GBRAIN_DIRECT_DATABASE_URL`/풀러 처리, `pglite_shared_buffers`, 엔진 졸업, WAL 복구 절차의 세부는 열지 않았다.
  - Postgres 실서버와 pgvector 버전별 동작(halfvec 사용 여부 분기)은 실행하지 못했고, 코드가 가정한 동작이다.

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 인용 가능.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/engine-factory.ts:9-28` `createEngine` | 엔진 선택 switch와 오류 문구 | R-01 |
| C-02 | `src/core/config.ts:677-694, 727-747` `effectiveEnvDatabaseUrl`, `loadConfig`의 엔진 추론·병합 | URL 우선순위, cwd `.env` 가드, `engine` 추론, `database_path` 해제 | R-03, R-04 |
| C-03 | `src/core/config.ts:1947-1964` `configDir` | `GBRAIN_HOME` 검증과 `.gbrain` 접미 | R-05 |
| C-04 | `src/core/config.ts:1868-1890, 1938-1945` `saveConfig`, `toEngineConfig` | 원자적 저장과 엔진 설정 투영 | R-05 |
| C-05 | `src/core/migrate.ts:394-405, 463-526` `runMigrations` | 본 루프, 신규/업그레이드 구분, 버전 기록 시점, 타임아웃 기록 | R-19, R-20 |
| C-06 | `src/core/migrate.ts:150-200, 530-602` `runMigrationSQLWithRetry`, `applyOneMigration` | 재시도, handler, verify, 드리프트 | R-20, R-22 |
| C-07 | `src/core/migrate.ts:207-265` `runMigrationSQL` | 트랜잭션 래핑과 `statement_timeout`/`lock_timeout` | R-21 |
| C-08 | `src/core/schema-migrations/types.ts:20-61` `Migration` | 마이그레이션 레코드 필드(down 없음) | R-22 |
| C-09 | `src/core/postgres-engine.ts:178-192` `getPostgresSchema`; `src/core/pglite-schema.generated.ts:2612-2627` `getPGLiteSchema`; `src/core/vector-index.ts:17-26` `chunkEmbeddingIndexSql`; `src/core/fts-language.ts:104-110` `applyFtsLanguagePolicy`; `scripts/build-schema.ts:389-440` `PGLITE_RULES` | 블롭 생성과 치환 규칙 | R-17, R-18 |
| C-10 | `src/core/stored-embedding-identity.ts:16-41` `readStoredEmbeddingIdentity` | 기존 임베딩 차원·모델이 우선 | R-15 |
| C-11 | `src/core/pglite-engine.ts:1130-1162` `PGLiteEngine.initSchema` | PGLite 스키마 적용 순서 | R-15 |
| C-12 | `src/core/postgres-engine.ts:554-658` `PostgresEngine.initSchema`; `src/core/postgres-engine/init-schema-lock.ts` `acquireInitSchemaAdvisoryLock` | Postgres 스키마 적용·락·후처리 | R-15, R-16 |
| C-13 | `src/schema.sql:26-58`(`sources`), `99-179`(`pages`), `341-391`(`content_chunks`), `536-571`(`links`), `602-609`(`tags`), `617-624`(`raw_data`), `631-646`(`timeline_entries`), `665-674`(`page_versions`), `706-716`(`config` + 시드) | 핵심 테이블 DDL 원본 | R-17, 1.3 |
| C-14 | `src/core/schema-migrations/v045-facts-hot-memory-v0-31.ts:28-179` `v045`(`factsDDL`); 컬럼 추가: `v047:32`, `v051:33-38`, `v067:23-31`, `v089:38`, `v122:20-30`, `v145:26-31`, `v166:6-7`, `v167:12-16`, `v215:21-23` | `facts` 테이블 생성과 후속 변경 | R-17, 1.3 |
| C-15 | `src/core/migrate-pending.ts:22-30` `hasPendingMigrations` | 보류 판정 | R-12 |
| C-16 | `src/core/migrate.ts:324-392` `tryRunPendingMigrations`, `isDeadlockError`; `src/cli/main.ts:2812-2856` `completeEngineStartup` | 경쟁 상태 내성 마이그레이션 실행과 알림 | R-12 |
| C-17 | `src/commands/init.ts:35-226` `runInitBranches` | `init` 엔진 결정과 가드 | R-06 |
| C-18 | `src/core/pglite-lock.ts:319-330` `acquireLock`; `src/core/pglite-engine.ts:874-892` | PGLite 데이터 디렉터리 락과 열기 순서 | R-13 |
| C-19 | `src/core/schema-migrations/v248-segmented-page-storage.ts:36-81` `COMMON_SQL`(`pages_body_storage_chk` 포함) | 분할 저장 컬럼과 NULL 불변식 | R-17, 1.3 |
| C-20 | `src/core/persistence/attribution-schema.ts:40-44` `WRITE_ATTRIBUTION_CONTENT_COLUMNS.facts` | `facts` 정규 내용 컬럼 목록 | 1.3 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(실행하지 않음, 테스트 파일 미열람).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-27 | `createEngine({engine:'sqlite'})` | `Unknown engine type: "sqlite". Supported engines: postgres, pglite. SQLite is not supported. Use pglite instead.`를 던진다 |
| T-02 | R-01 | `createEngine({})` | `PostgresEngine`(PGLite 모듈은 로드 안 됨) |
| T-03 | R-03, R-04 | `config.json = {engine:'pglite', database_path:'/x'}`, 환경 `GBRAIN_DATABASE_URL=postgres://u` | `loadConfig()` → `engine:'postgres'`, `database_url:'postgres://u'`, `database_path` undefined |
| T-04 | R-03 | 환경 URL 없음. `config.json = {database_path:'/x'}` / `{database_url:'u'}` / `{engine:'pglite'}` | 각각 `engine:'pglite'` / `'postgres'` / `'pglite'` |
| T-05 | R-03, R-10 | 설정 파일 없음, URL 환경변수 없음 | `loadConfig()`가 `null`, CLI는 `no_brain` 오류로 종료 |
| T-06 | R-04 | cwd `.env`에 `DATABASE_URL=u`가 있고 프로세스 `DATABASE_URL=u`, `GBRAIN_DATABASE_URL` 없음 | URL 무시(경고 1회), 파일 설정 엔진 사용 |
| T-07 | R-05 | `GBRAIN_HOME=rel`, `GBRAIN_HOME=/a/../b`, `GBRAIN_HOME=/tmp/x` | 처음 둘은 던짐. 마지막은 `/tmp/x/.gbrain/config.json` |
| T-08 | R-17, R-19, R-25 | 빈 PGLite(`version='1'`)에서 `initSchema()` | 259개 적용, `config.version='264'`, `runMigrations`는 `{applied:259, current:264}`, stderr에 `Setting up brain schema (v264)...` |
| T-09 | R-12, R-19 | `config.version='264'` | `hasPendingMigrations`=false, `runMigrations`는 `{applied:0, current:264}`(자가 치유만 수행) |
| T-10 | R-19 | `config.version='100'` | v101~v264 164개를 오름차순 적용, 이름·완료 줄이 stderr에 출력 |
| T-11 | R-20, R-22 | v150이 비재시도 오류로 실패 | v149까지 `config.version` 유지(`'149'`), 오류 전파, 다음 실행이 v150부터 다시 시도 |
| T-12 | R-15 | 기존 DB의 `content_chunks.embedding`이 `vector(1024)`, 게이트웨이는 1536 지정 | 스키마는 1024로 재생, 차원 변경 없음 |
| T-13 | R-18 | `getPGLiteSchema(0)`, `getPostgresSchema(2048)` | 앞은 `Invalid embedding dimensions: 0`을 던짐. 뒤는 `idx_chunks_embedding` HNSW 문장이 주석으로 대체됨 |
| T-14 | R-13 | `connect({engine:'pglite'})`에 `database_path` 없음 | 메모리 DB, 프로세스 종료 시 데이터 소실, 락 생략 |
| T-15 | R-14 | `PostgresEngine.connect({engine:'postgres'})`에 URL 없음 | `GBrainError: No database URL: database_url is missing from config. Fix: Run gbrain init --supabase or gbrain init --url <connection_string>` |
| T-16 | R-06 | `gbrain init --non-interactive`(URL 인자·환경변수 없음) | 안내 문구 출력 후 exit 1, 설정 파일은 쓰지 않음 |
| T-17 | R-07 | `gbrain init --pglite` 첫 실행 | `~/.gbrain/brain.pglite` 생성·스키마 적용 후 `config.json`에 `engine:'pglite'`, `database_path` 기록 |
| T-18 | 1.3 | 같은 소스에 `(source_id, slug)`가 같은 두 번째 `pages` INSERT / 다른 소스에 같은 slug | 앞은 유일 제약 위반(upsert면 갱신), 뒤는 성공 |
| T-19 | 1.3 | 페이지 하드 삭제 | 그 페이지의 `content_chunks`·`links`(양쪽)·`tags`·`raw_data`·`timeline_entries`·`page_versions` 삭제, 다른 페이지의 `links.origin_page_id`는 NULL |
| T-20 | 1.3 | `facts`에 `kind='todo'` 또는 `confidence=1.5` INSERT | CHECK 위반으로 실패 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@63f62b2 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, T-01, T-02 | C-01 | 코드 읽음. **README와의 차이**: README는 PGLite가 기본 엔진이라 하지만(`README.md:408` "zero-config, default") `createEngine`의 코드 기본은 `postgres`(`engine-factory.ts:10`)다. 차이를 메우는 층이 둘 있다. ① `gbrain init`의 무플래그 기본이 PGLite이고 그때 `config.json`에 `engine:'pglite'`를 쓴다(`init.ts:184-198`, `1211`). ② `loadConfig()`가 `engine` 없는 설정을 `database_path` 유무로 `pglite`/`postgres`로 추론하고 URL 환경변수가 있으면 항상 `postgres`로 덮는다(`config.ts:737-739`). 따라서 "엔진을 명시하지 않은 설정 객체"를 `createEngine`에 직접 주는 코드 경로(`createEngine({})`)만 postgres로 간다. 일반 CLI는 `loadConfig()`가 먼저 엔진을 정해 넘기므로 README와 사실상 일치하지만, 설정 없이 `DATABASE_URL`만 있으면 PGLite가 아니라 Postgres다 (코드 확인) |
| R-02 | `engine-factory.ts:30-44` | 코드 읽음 |
| R-03, R-04, T-03~T-06 | C-02; `config.ts:711-725`(`.env` 로드, 파일 읽기), `src/core/gbrain-env-file.ts:32-61` `loadGbrainEnvFile` | 코드 읽음. #427 가드 주석이 근거 설명 |
| R-05, T-07 | C-03, C-04; `config.ts:1913-1936` `ensureGitignore` | 코드 읽음 |
| R-06, T-16 | C-17(`init.ts:53-226`) | 코드 읽음. 입력 플래그 검증 `validateInitFlags`(`init.ts:229-294`)는 열지 않음 |
| R-07, T-17 | `init.ts:1077-1100, 1138-1262` `initPGLite` | 코드 읽음. 임베딩 모델 해석·키 점검(`resolveAIOptions`, `runInitEmbedCheck`)은 AI 게이트웨이 소관 |
| R-08 | `init.ts:1375-1560` `initPostgresCore`; `init-schema-retry.ts:52-78` | 코드 읽음 |
| R-09 | `init.ts:846-870` `initMigrateOnly` | 분기만 확인, `runMigrateOnlyCore` 본문 미열람 |
| R-10 | `src/cli/main.ts:2768-2800` `connectEngine`; `src/core/engine-connect.ts:76-114` `connectEngineForServe` | 코드 읽음 |
| R-11 | `db.ts:649-679` `connectWithRetry` | 코드 읽음 |
| R-12 | C-15, C-16 | 코드 읽음 |
| R-13, T-14 | C-18; `pglite-engine.ts:874-1000` | 코드 읽음. 마운트·restore·held-lock 변형(`connectForRestore`, `connectWithHeldLock`)은 열지 않음 |
| R-14, T-15 | `postgres-engine.ts:414-492`; `db.ts:515-522` | 코드 읽음 |
| R-15, T-12 | C-10, C-11, C-12; `src/core/ai/defaults.ts:15-16`; `src/core/ai/gateway.ts:837-852` `getEmbeddingModel`/`getEmbeddingDimensions`(미설정 시 `requireConfig`가 던짐 — 주석 근거) | 코드 읽음 |
| R-16 | C-12; `init-schema-lock.ts` | 코드 읽음 |
| R-17, T-08 | C-09, C-13; `src/core/pglite-schema.generated.ts:322-331`(`engine='pglite'` 시드); `migrate.ts:469-491`; `schema.sql:711-716` | 코드 읽음. 259개 = `registry.generated.ts`의 import 259줄 = `schema-migrations/v*.ts` 259개. 디렉터리 파일 수 263은 `helpers.ts`·`latest.generated.ts`·`registry.generated.ts`·`types.ts` 4개를 포함한 수다 |
| R-18, T-13 | C-09 | 코드 읽음 |
| R-19, T-08~T-10 | C-05 | 코드 읽음 |
| R-20, T-11 | C-06 | 코드 읽음 |
| R-21 | C-07; `schema-lock-timeout.ts:45-56`; `migration-timeout.ts:16-24` | 코드 읽음 |
| R-22, T-11 | C-06, C-08 | 코드 읽음. "down 없음"은 `Migration` 인터페이스 필드 전수 확인 |
| R-23 | `migrate.ts:406-461` | 코드 읽음. 세 보수 함수의 본문은 열지 않음 |
| R-24 | `engine-connect.ts:97`; `pglite-engine.ts:1161`; `pglite-engine.ts:877-891` | 호출 위치만 확인 |
| R-25 | `latest.generated.ts:7`; `registry.generated.ts`; `migrate.ts:80-82` | `ls`와 번호 정렬로 결번(17~19, 100) 계산. 버전 번호 중복 없음 |
| R-26 | `schema.sql`의 `sources`·`pages`·`raw_data` 주석, `v177-pages-database-only-reason.ts:15`, `engine.ts:2227-2262` `deleteFactsForPage` 주석, `markdown.ts:846-890` `splitBody` 주석, `README.md:410`, `docs/architecture/system-of-record.md:1-110` | 구조(컬럼 존재)는 이 스펙에서 코드 확인. "파일이 원본"이라는 `system-of-record.md`의 주장은 루트가 있는 소스에서만 성립하고 루트가 없으면 DB가 유일한 사본임을 후속 스펙이 코드로 확정했다(2026-10-23 보정: 추론 → 코드 확인) |
| R-27 | `types.ts:2327`, `engine.ts:814`, `config.ts:37`, C-01 | 코드 읽음. `docs/ENGINES.md`에 SQLite 설명이 남아 있다는 overview의 보고는 이 스펙에서 열지 않았다(코드는 거부) |
| 1.3 (나) sources~config | C-13; C-14; C-19; `page-state/schema.ts:28-80`(knowledge_revision); `types.ts:86-224` `Page`; `types.ts:678-860` `Chunk`/`ChunkInput` | 컬럼 의미는 DDL 주석·타입 주석의 서술이며 정적 읽기. `facts`의 마이그레이션 전용 부가 컬럼은 `persistence/attribution-schema.ts:26-44`와 `v226-trust-tiers.ts` |
| 1.3 (나) facts 활성·가드 | `engine-sql/facts.ts:81-165, 776-880`; `facts/insert-guard-schema.ts:1-49`; `v264` | 코드 읽음. 트리거 함수 본문 SQL은 열지 않음 |
| 1.3 (다) | `engine.ts:812-935, 1165-1250, 2160-2372` | 선언·주석 읽음. 구현(`engine-sql/*`)의 SQL은 이 스펙에서 열지 않음. `insertFact`가 `duplicate`를 실제로 돌려주는지는 이 스펙에서 확인하지 않음(엔진 주석은 허용 값으로 적고, `engine-sql/facts.ts`가 읽은 구간은 `inserted`·`superseded`만 만든다) |
| T-18~T-20 | C-13, C-14 | DDL의 제약·FK 규칙에서 도출 |

### 2.2 코드 읽는 순서

1. `src/core/engine-factory.ts` → `src/core/config.ts`(`loadConfig`, `configDir`, `saveConfig`) → `src/commands/init.ts` `runInitBranches`/`initPGLite`/`initPostgresCore`.
2. 연결: `src/core/engine-connect.ts` → `src/core/db.ts` `connectWithRetry` → `PGLiteEngine._connectInternal` / `PostgresEngine.connect`.
3. 스키마: `PGLiteEngine.initSchema`·`PostgresEngine.initSchema` → `src/core/migrate.ts` `runMigrations` → `src/core/schema-migrations/types.ts`.
4. 블롭: `src/schema.sql` → `scripts/build-schema.ts` → `src/core/pglite-schema.generated.ts`/`schema-embedded.generated.ts`.
5. `facts`: `v045` → `engine-sql/facts.ts` `insertFact`.

구현 전략 메모: 스키마 텍스트는 `schema.sql`과 TS 조각에서 생성되고(`bun run build:schema`), 마이그레이션 레지스트리도 생성 파일이다(`bun run build:schema-migrations`). 두 번째 DDL 경로가 일부러 중복되어 있다. 블롭은 새 설치의 시작 모양이고 마이그레이션은 오래된 DB를 끌어올리는 경로인데, 새 설치도 둘 다 거친다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

## 적용 메모

없음.
