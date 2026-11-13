---
sha: "c447003f72a822301e927196a4ecb5b597c308d5"
created: 2026-11-10
updated: 2026-11-10
---

# auto-ontology Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/NVIDIA/auto-ontology`
- **작업트리 상태**: Clean (`artifacts/auto-ontology/repo-metadata.txt`). 기준 커밋 `c447003` (main, 2026-11-06, "Pin Python 3.12.16 in the backend and MCP images (#438)"). `--depth 50` shallow clone.
- **분석 목적**: 이 온톨로지가 **어떻게 구현되는지 이해**하는 것(사용자 답, 2026-11-10; 다른 레포와 비교하지 않음). 스펙을 어디에 쓸지는 아직 정하지 않았다. 그래서 feature map은 전체를 유지하되 권장 범위는 "온톨로지 구축·저장·사용"에 좁혔다. 주제 폴더는 만들지 않고 루트 `reports/auto-ontology/`에 둔다.
- **라이선스**: Apache-2.0 — `LICENSE`(Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES). `frontend/LICENSE`가 따로 있으나 이번에는 열지 않았다(`미확인`). 서드파티 목록은 `THIRD_PARTY_NOTICES.md`, `CONTAINER_THIRD_PARTY_NOTICES.md`(열지 않음).
- **분석 대상 제품**: 한 레포에 배포 단위가 여럿이다.
  - Python 패키지 `auto_ontology/` (pyproject `auto-ontology-server` 1.2.0): FastAPI 백엔드 `server/`(:3001), 수집·컴파일 서비스 `ingestion_service/`(:3002), 라이브러리 성격의 `catalog/`·`connectors/`·`semantic/`·`retrieval/`·`dal/`·`vdb/`·`pii_detection/`·`utils/`.
  - `frontend/`: Next.js 16 웹 UI + Better Auth + Prisma, 공개 API 게이트웨이(:3000).
  - `mcp/`: 별도 패키지 `auto-ontology-mcp`(FastMCP, :3003).
  - `skills/`: 코딩 에이전트용 스킬 3개, `helm/`·`docker-compose.yml`·`.github/workflows/`: 배포.
- **스펙 범위**: 승인 전 (권장안: 행 1~10, 공유 계약 S1·S2. 이 중 3·5·10을 먼저. 근거는 2절 "권장 범위"). 먼저 [Q1](./questions/q1-ontology-implementation.md)로 구현을 설명했고, 스펙을 쓸지는 사용자가 정한다. 승인 요청은 [handoff.md](../../handoff.md). · 제외: 없음(아직 정하지 않음)

---

## 2. 프로젝트 개요

LLM 에이전트가 기업 데이터베이스에 질문할 때 "지표 정의가 어디 있고 무슨 뜻인가"를 모르면 틀린 숫자를 낸다. Auto Ontology는 원본 DB의 메타데이터에서 **온톨로지**(term, SQL attribute, 관계)를 LLM으로 만들고, 사람이 certify한 뒤, 그 온톨로지를 근거로 text-to-SQL을 한다(`README.md` "How it works", 일부는 아래 표에서 코드 확인). 세 단계다.

1. **Generate**: 수집 서비스가 원본 DB의 스키마·컬럼 프로파일·샘플 값을 Postgres 카탈로그에 넣고(`catalog/ingest.py`), 시맨틱 컴파일이 테이블별로 term을 뽑고 FK·SQL attribute·bridge table 관계를 추가한 뒤 pgvector에 임베딩한다(`semantic/compile.py`).
2. **Certify**: 사람이 UI·API로 term·description·SQL attribute를 고치고 certify한다(`dal/terms.py`의 certification 집계).
3. **Answer**: 질문마다 LangGraph 그래프가 intent 분류 → 엔티티 추출 → 임베딩 후보 검색 → SQL 생성 → 검증·수리 → 실행 → 응답을 한다(`retrieval/text_to_sql/text_to_sql_graph.py`). 후보로 못 풀면 "답할 수 없음"을 낸다. 같은 기능을 웹 채팅, REST(`POST /api/chat/completions`, SSE), MCP(`ask_question`)가 공유한다.

코드 규모(추적 파일 1,082개): 테스트 제외 Python 약 69,000줄(`retrieval/` 29,000, `dal/` 17,000, `server/` 10,600, `connectors/` 6,800, `catalog/` 5,000, `semantic/` 4,800), MCP 약 1,400줄, 프런트엔드 TS/TSX 약 43,500줄(줄 수는 `wc -l`, `미확인`: 테스트 파일 제외 기준을 파이썬만 적용).

### Feature map

목적("온톨로지가 어떻게 구현되는가")에 맞춰 2026-11-10에 다시 잘랐다. 온톨로지를 만들고(1~8) 큐레이션하고(9) 질문 때 읽는(10~12) 영역은 스펙 하나 단위로 잘게 나누고, 목적 밖 영역(13~20)은 패밀리 한 행으로 굵게 묶었다. 이전 22행 초안과의 대응은 이 표 아래 "이전 초안과의 대응"에 있다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 카탈로그 수집 | 연결된 DB에서 스키마·테이블·컬럼·선언된 FK·쿼리 이력을 추출해 Postgres 카탈로그에 쓰고 임베딩 행을 만든다. 온톨로지의 **입력**이다. 경계: 연결 설정은 13행, term 생성은 3행 | `auto_ontology/catalog/ingest.py` `ingest_catalog`; `catalog/extract.py` `extract_tabular_db_data`; `catalog/write.py`; `catalog/query_stats.py`; `ingestion_service/ingest.py` `run_ingest` | S1 | 핵심 | `capabilities/catalog-ingestion.md` · 미작성 | 코드 확인(진입점·docstring), 추론(쿼리 이력 수집 세부 — Q1 10절 미해결) |
| 2 | 컬럼 프로파일링·FK 후보 탐지 | 컴파일 중 컬럼마다 샘플 행·`SELECT DISTINCT`·날짜 저장 형식을 구하고, 선언된 FK 외의 FK 후보 컬럼과 junction(연결) 테이블 여부를 LLM으로 판정한다. 결과는 속성 후보에서 FK를 빼는 데 쓰이고 FK 후보 자체는 저장하지 않는다 | `semantic/visit_enter.py` `calculate_columns_profiling`(406), `_sampling_breaker`; `semantic/fk_suggester.py` `suggest_potential_foreign_keys`(117), `_SYSTEM`; `semantic/date_format.py`; `dal/datasources.py` `mark_table_as_junction`(548) | 1 | 핵심 | `capabilities/column-profiling-fk-detection.md` · 미작성 | 코드 확인(호출 위치·프롬프트 앞부분), 추론(프로파일링·결정적 폴백 세부) |
| 3 | Term·ColumnAttribute 생성 | FK를 뺀 컬럼에 설명·표시 이름을 붙이고 LLM이 Term 이름·컬럼 배정을 정한다. 테이블당 Term 하나를 강하게 선호하고, 모든 컬럼은 정확히 한 Term에 속하며, 이름이 충돌하면 테이블 신원으로 한정해 저장한다 | `semantic/term_extractor.py` `extract_term`, `_sanitize_result`, `_fallback_result`; `semantic/deterministic.py` `column_attribute_specs`, `to_term_name`; `semantic/models.py`; `dal/terms.py` `upsert_table_term`(417); `dal/attributes.py` `merge_column_attribute`(57) | 2, S1, S2 | 핵심 | `capabilities/term-generation.md` · 미작성 | 코드 확인(프롬프트·정제·저장 호출), 추론(충돌 한정 이름 형식 — 읽지 않음) |
| 4 | 시맨틱 컴파일 오케스트레이션 | 컴파일 4단계(term → FK 해석 → SQL attribute → bridge)를 순서대로 돌린다. Term이 없는 테이블만(증분) 워커 3개로 병렬 처리하고 커밋은 정규 순서로 직렬화한다. 도메인 요약 JSON을 선택적으로 쓰고, 취소되면 term 이후 단계를 건너뛴다 | `semantic/compile.py` `run_semantic_compilation`(33); `semantic/pipeline.py` `compile_semantic_layer`(126), `_OrderedCommitQueue`; `semantic/cancellation.py`; `semantic/domain.py` | 2, 3, 5~8 | 핵심 | `capabilities/compilation-orchestration.md` · 미작성 | 코드 확인(순서·동시성·증분) |
| 5 | 의미적 FK 해석 | 속성에서 빠진 FK 컬럼이 어느 ColumnAttribute를 가리키는지 정한다. 선언된 FK는 바로 연결, 없으면 임베딩 후보 5개 + LLM, LLM이 포기하면 샘플 값 겹침. 마지막에 값이 하나도 안 겹치는 추론 간선을 지우고, 같은 대상을 가리키는 컬럼들 중 기본 조인을 하나 고른다 | `semantic/semantic_fk.py` `resolve_semantic_fks`(91), `prune_disjoint_semantic_fks`, `select_semantic_fk_join_defaults`; `dal/schema.py` `column__semantic_fk`, `join_path_edge` | 3, 8, S1, S2 | 핵심 | `capabilities/semantic-fk-resolution.md` · 미작성 | 코드 확인(알고리즘 docstring·가지치기 SQL), 추론(기본 조인 선택 프롬프트) |
| 6 | SQL attribute 제안 | 테이블에 연결된 쿼리 이력에서 `sqlglot`으로 표현식(조건·집계·CASE 등)을 뽑고 Term마다 상위 10개를 LLM에 보여 SqlAttribute를 제안한다. 사용량 순위 함수 `_usage_score`는 항상 0.0이다(알려진 결함) | `semantic/sql_attribute_suggester.py` `suggest_sql_attributes`, `_extract_expressions`, `_usage_score`; `server/sql_attributes/service.py` `create_sql_attribute`(214); `dal/terms.py` `fetch_terms_with_sqls`(897) | 3, 8, S1, S2 | 핵심 | `capabilities/sql-attribute-suggestion.md` · 미작성 | 코드 확인(docstring·결함 설명), 추론(LLM 프롬프트·충돌 처리) |
| 7 | bridge table SqlAttribute | 컬럼이 전부 FK인 순수 연결 테이블은 Term 없이, LLM이 만든 조인 SQL을 SqlAttribute(`source='bridgeTable'`)로 FK 대상 Term 중 재랭킹으로 더 맞는 쪽에 붙인다 | `semantic/bridge_tables.py` `build_bridge_tables_sql_attributes`; `dal/datasources.py` `fetch_bridge_table_candidates`; `utils/rerank.py` | 5, 8 | 핵심 | `capabilities/bridge-table-attributes.md` · 미작성 | 코드 확인(docstring), 추론(재랭킹 호출 세부) |
| 8 | 임베딩·벡터 저장 | Term·ColumnAttribute·SqlAttribute·CustomAnalysis를 라벨별 텍스트 형식으로 임베딩해 pgvector에 쓰고, 편집하면 다시 임베딩한다(certify만 바뀌면 건너뜀). 임베딩 키가 없으면 임베딩 없이 진행한다 | `semantic/embed.py` `SemanticEmbedder`, `_build_rows`; `vdb/postgres.py` `PostgresVDB`(137); `vdb/records.py`; `utils/embedding.py`; `utils/retriever.py`; `server/terms/service.py` `refresh_term_embeddings`(184) | S1, S2 | 핵심 | `capabilities/semantic-embedding.md` · 미작성 | 코드 확인(행 형식·재임베딩 규칙), 추론(VDB 스키마·인덱스) |
| 9 | 온톨로지 큐레이션 API | 사람이 term·컬럼 속성·SQL attribute·custom analysis를 조회·수정·certify한다. SQL 표현식은 저장 전에 검증하고, term certification은 attribute 플래그로 서버에서만 집계(`certified/partial/pending`)한다. certify는 표시용이다(Q1 6절) | `server/terms/router.py`·`service.py`; `server/sql_attributes/router.py`; `server/custom_analyses/service.py`; `dal/terms.py` `_certification`(156); `dal/attributes.py`; `dal/sql_attributes.py` | 3, 6, 8, S1 | 핵심 | `capabilities/ontology-curation.md` · 미작성 | 코드 확인(라우트·docstring), 추론(검증 세부) |
| 10 | 질의 시 온톨로지 읽기 | 질문의 엔티티마다 ColumnAttribute를, 질문 전체로 SqlAttribute·CustomAnalysis top 3을 임베딩 검색한다. 후보가 여럿이면 LLM이 앵커 속성을 고르고, 앵커 컬럼에서 나머지 후보 컬럼까지 테이블 BFS 조인 경로(최대 8 hop, PK 방향 규칙)를 구해 SQL 프롬프트용 컨텍스트로 만든다. hub-sibling 확장은 기본 꺼짐 | `retrieval/text_to_sql/agents/candidates_retrieval.py` `CandidateRetrievalAgent`(426); `agents/candidates_preparation.py` `CandidatePreparationAgent`(231), `_identify_anchor`; `dal/attributes.py` `find_join_path`(1037), `_find_table_join_hops`(792), `find_anchor_hub_siblings`(1188); `retrieval/data_access/semantic_search.py` | 3, 5, 8, S1 | 핵심 | `capabilities/ontology-retrieval.md` · 미작성 | 코드 확인(검색 단위·BFS·기본값), 추론(앵커 선택 프롬프트) |
| 11 | SQL 생성·검증·수리·실행 (패밀리) | 10행의 컨텍스트로 SQL을 만들고 파싱·값·조인 경로 검증, 오류 유형별 재구성(최대 7회), 실행, 응답을 만든다. information 질문은 도구로 메타데이터에 답한다. 한 행으로 묶은 것: `sql_from_semantic`, 검증 3종, 재구성, 실행, `db_probe/`, `information_agent`, `follow_up`, `response` | `retrieval/text_to_sql/main.py` `stream_agent_response`(421); `text_to_sql_graph.py` `create_graph`(329); `agents/sql_from_semantic.py` `SQLFromCandidatesAgent`(90); `agents/sql_parse_validation.py`; `sql_reconstruction.py`; `sql_execution.py` | 10, S2, S4 | 핵심 | `capabilities/text-to-sql-generation.md` · 미작성(범위 밖 권장) | 코드 확인(그래프 노드·재시도 상한), 추론(프롬프트·검증 규칙) |
| 12 | 답변 가능성 평가 | 질문 엔티티가 온톨로지에 덮이는 정도를 거리 필터와 1/n 커버리지로 점수화한다. 에이전트 전체를 돌리지 않는 사전 점검(MCP `check_answerable`) | `retrieval/entity_coverage/main.py` `get_coverage_response`(86); `agents/question_extraction.py`; `agents/coverage.py`; `server/metadata/service.py` `entity_coverage`(65) | 8, S2 | 핵심 | `capabilities/answerability-check.md` · 미작성(범위 밖 권장) | 코드 확인(진입점·docstring), 추론(임계값) |
| 13 | 소스 연결·수집 서비스·PII (패밀리) | 연결 문자열·UI 연결 등록과 allow/deny 범위, 10개 엔진 커넥터, Vault, 수집·컴파일 서비스(:3002: 24시간 스케줄·즉시 실행·정지·초기화), PII 탐지·태그 전파를 한 행으로 묶었다. 1·4행이 쓰는 인프라 | `connectors/registry.py` `CONNECTOR_REGISTRY`(44), `get_connectors`(256); `connectors/base.py`; `server/connections/router.py`; `ingestion_service/router.py`; `ingestion_service/scheduler.py` `IntervalScheduler`(32); `pii_detection/service.py` `detect_and_tag_pii`(140) | 없음 | 핵심 | 미작성(범위 밖 권장) | 코드 확인(레지스트리·라우트·docstring), 추론(엔진별 세부) |
| 14 | 접근 통제·태그·규칙 | 존(database·schema·table 범위)과 그룹(admin/viewer)으로 보이는 카탈로그를 정하고, 태그를 객체 5종에 붙이고, 규칙(저장한 검색 + 태그 묶음)을 수집·컴파일 뒤 재적용한다 | `server/zones/router.py`, `dal/zones.py`; `server/users/router.py`, `permissions.py`, `access.json`; `dal/users.py` `resolve_accessible_catalog_ids`(105); `server/tags/router.py`; `server/rules/router.py`; `ingestion_service/rules.py` `replay_rules`(33) | S1 | 핵심 | 미작성(범위 밖 권장) | 코드 확인(docstring·라우트), 추론(재적용 시점) |
| 15 | 탐색·검색·모델 교환 | 데이터·시맨틱 계층 그래프 탐색, 전역 검색, 온톨로지를 자체 YAML·Apache Ossie YAML로 내보내고 가져오기(가져오기는 임베딩 행을 모아 flush) | `server/exploration/router.py`; `dal/exploration.py`(`_related_tables`, `fetch_semantic_exploration_graph`(1243)); `server/search/router.py`; `server/model_interchange/router.py`·`service.py`; `dal/model_interchange.py` | 3, 6, 8, S1 | 핵심 | 미작성(범위 밖 권장) | 코드 확인(라우트·docstring), 미확인(Ossie 변환: 외부 패키지) |
| 16 | 채팅 서비스·에이전트 설정 | 대화마다 미리 띄운 에이전트 서브프로세스, 대화당 스트림 하나(409·고아 스트림 선점), 연결이 끊겨도 완주·`/chat/watch` 재접속, 차트·표 말풍선, 약어·사용자 프롬프트·SQL 타임아웃·distinct probing 등 설정 | `server/chat/router.py`; `server/chat/worker.py` `PrewarmedWorker`(214), `WarmPool`(327); `server/chat/settings_dal.py`; `infra/feature_flags.py`; `retrieval/text_to_sql/visualization/analyze.py` | 11, S3, S4 | 핵심 | 미작성(범위 밖 권장) | 코드 확인(docstring의 동시성 규칙), 추론(워커 프로토콜 세부) |
| 17 | 접근 인터페이스: 게이트웨이·MCP·웹 UI (패밀리) | Better Auth 로그인·SSO·초대·API 토큰·RBAC와 FastAPI 프록시(신뢰 헤더를 매번 새로 만듦), MCP 서버(`CURATED` 읽기 전용 도구 허용 목록), 웹 UI 화면·analytics | `frontend/auth/auth.ts` `betterAuth`(65); `frontend/auth/proxy-backend.ts` `proxyToBackend`(44); `frontend/auth/with-auth.ts`; `frontend/proxy.ts`; `mcp/auto_ontology_mcp/tools.py` `CURATED`(60); `server.py` `build_server`(187); `frontend/app/*/page.tsx` | S3 | 핵심 | 미작성(범위 밖 권장) | 코드 확인(프록시·헤더·허용 목록), 추론(SSO·OAuth), 미확인(UI 화면 동작) |
| 18 | 예측(KumoRFM) | `KUMO_RFM_API_KEY`가 있으면 predictive 질문을 호스팅 서비스 KumoRFM으로 보낸다. 연결 테이블을 업로드하며 `KUMO_MAX_TABLES`(20)·`KUMO_MAX_ROWS_PER_TABLE`로 제한. 질문 → PQL → 검증·수리·예측 | `retrieval/kumo/predictor.py`, `pql_gen.py`(1,850줄), `budget.py`, `graph_cache.py`; `agents/kumo_prediction.py`, `prediction_graph.py`; `server/pql_analyses/service.py` | 11 | 부속 | 미작성 | 코드 확인(파일·docstring), 미확인(KumoRFM 외부 동작) |
| 19 | 배포·릴리스·에이전트 스킬 | Docker Compose, Helm, CI·릴리스, OpenAPI 생성, 코딩 에이전트용 스킬 3개(`nvidia-ontology-setup/management/query`, SKILL.md·서명 파일) | `docker-compose.yml`; `helm/auto-ontology/`; `.github/workflows/`; `dev_tools/generate_backend_openapi.py`; `AGENTS.md`; `skills/*/SKILL.md` | 없음 | 부속 | 미작성 | 코드 확인(서비스·파일 목록), 미확인(Helm 값·CI·SKILL.md 본문) |
| 20 | 다턴 clarify 코디네이터 | 질문을 되묻고 SQL을 제출하는 세션 상태 기계. `server/`·`mcp/`·`dev_tools/`에서 import하는 곳이 없다 — 평가 하니스용으로 보이나 `추론` | `retrieval/interactive/coordinator.py` `create_session`(662), `step`(696); `clarify.py`; `entity_resolution.py` | 11 | 부속 | 미작성 | 코드 확인(호출자 없음: `grep`), 추론(용도) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 별도 스펙 없이 소유 행에 두는 것을 제안)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1 온톨로지·카탈로그 저장 스키마 | 1~10, 14, 15 | `dal/schema.py` (테이블 약 30개: `catalog_*`, `term`, `column_attribute`, `column__has_attribute`, `column__semantic_fk`, `sql_attribute`, `custom_analysis`, `zone`, `tag`, `rule` 등과 뷰 `join_path_edge`), `alembic/versions/` | **목적 핵심이라 별도 스펙 후보**: `capabilities/storage-schema.md` · 미작성 | 코드 확인(테이블·제약 주석), 추론(컬럼 의미 일부) |
| S2 모델 역할 설정·LLM/임베딩 호출 | 3, 5, 6, 7, 8, 11, 12 | `utils/model_config.py` `resolve`(92) (역할 REASONING·NON_REASONING·EMBED·RERANK, ENDPOINT/API_KEY/MODEL 삼중 + `DEFAULT_MODELS_*` 폴백 + 키 접두어별 기본 모델); `utils/llm_invoke.py`; `utils/embedding.py` | 소유 행 없음. 별도 스펙 또는 8행에 포함(제안) · 미작성 | 코드 확인(model_config), 추론(나머지) |
| S3 내부 사용자 신뢰 헤더 | 14, 16, 17 | `server/identity.py` `INTERNAL_USER_HEADER = "x-auto-ontology-user-id"`; `frontend/lib/internalIdentity.ts` | 소유 행 17 · 미작성 | 코드 확인 |
| S4 채팅 SSE 이벤트 | 11, 16, 17 | `retrieval/text_to_sql/main.py` `stream_agent_response`(`step`·`sql`·`result`·`error`), `server/chat/router.py`(`charts`), `docs/conversation-api.md` | 소유 행 16 · 미작성 | 코드 확인(이벤트 타입), 미확인(문서 본문) |

**이전 초안과의 대응** (22행 → 20행): 구 4 → 2·3·4로 분리, 구 5 → 5·6·7로 분리, 구 2 → 1, 구 7 → 9, 구 11 → 10(온톨로지 읽기)과 11(나머지), 구 12·13 → 11·12, 구 S3(벡터 저장) → 8행으로 승격, 구 1·3·6 → 13, 구 9 → 14, 구 8·10 → 15, 구 14·15 → 16, 구 16·17·18 → 17, 구 19 → 18, 구 20·21 → 19, 구 22 → 20. 구 S1·S2·S4·S5는 S1~S4로 번호만 바뀌었다.

**대조한 범위와 미탐색 영역**

- **대조**: README 기능 목록(Key Features, How it works, MCP, Skills, REST, Connectors, Models, Predictions), `server/__main__.py`의 `include_router` 15개, 수집 서비스 라우트 8개(health 2개 포함), 프런트엔드 `app/api/**/route.ts` 목록(약 80개), 백엔드 라우터 데코레이터 목록, MCP `CURATED` 도구 이름, `dal/schema.py` 테이블 목록, `docker-compose.yml` 서비스 목록.
- **문서와 구현의 차이**
  - README 앞부분 "NVIDIA NIM" 절은 임베딩 `nvidia/nemotron-3-embed-1b`·재랭킹 `nvidia/llama-nemotron-rerank-vl-1b-v2`라고 하고, 뒤의 "Models" 절은 `nvidia/nemotron-3.5-embed-1b`·`nvidia/nemotron-3.5-rerank-8b`라고 한다. README 안에서 서로 다르다. 코드(`utils/model_config.py`)는 3.5 쪽이다(`코드 확인`).
  - 코드의 기본 모델은 API 키 접두어로 고른다. `nvapi-`는 NIM 3.5 계열, 그 밖(키가 없을 때 포함)은 `sk-` 세트인 `inference-api.nvidia.com`의 `azure/anthropic/claude-opus-5-5`로 폴백한다(`_FALLBACK_KEY_PREFIX = "sk-"`). README는 이 폴백을 말하지 않는다(`코드 확인`).
  - README "Software Components" 앞 표는 Frontend·Backend·Ingestion·Postgres·Vault 5행이고, 뒤 표는 MCP(:3003)가 더해진 6행이다. 앞 표에 MCP가 없다. 또 `docker-compose.yml`(서비스: postgres·pgadmin·백엔드·수집·마이그레이션 2개·프런트엔드)과 `helm/auto-ontology/templates/`에는 MCP 서비스가 없다. 즉 MCP는 compose·Helm 밖에서 `uvx`로 따로 띄운다(`코드 확인`: 두 목록, `미확인`: README의 `uvx` 실행이 유일한 경로인지).
  - `docs/connections.md`: 질문 응답은 UI 연결이 있으면 그것을 쓰고 없으면 `CONNECTION_STRINGS`로 폴백하는데, 수집은 `CONNECTION_STRINGS`가 있으면 그것만 쓴다. 한 배포에서 둘 중 하나만 쓰라는 안내(`미확인`: 코드 대조 안 함, 13행 때 확인).
- **미탐색**:
  - `catalog/`의 하위 패키지 `store/`·`model/`·`parsers/`·`services/`(이름만 확인), `catalog/diff.py`·`query_stats.py`·`sql_parse.py` 본문
  - `dal/` 파일 대부분(전체 17,000줄 중 docstring만), `connectors/` 개별 엔진 구현, `retrieval/kumo/`·`interactive/` 본문
  - 프런트엔드 화면·컴포넌트 본문(43,500줄 중 `auth/`·`proxy.ts`·route 일부만), Prisma 스키마, `helm/`, `.github/workflows/`, `skills/*/SKILL.md`
  - `docs/*.md`(`mcp.md`, `connections.md`, `conversation-api.md`는 앞부분만), `DEPLOYMENT.md`
  - 테스트 172개 파일은 열지 않았다(기본 규칙).
  - 실행·빌드·외부 API 호출은 하지 않았다.

### 권장 범위 (승인 전)

목적이 "온톨로지가 어떻게 구현되는지 이해"이므로, **온톨로지를 만들고(1~8) 큐레이션하고(9) 질문 때 읽는(10) 행**을 권한다. 개요 설명은 이미 [Q1](./questions/q1-ontology-implementation.md)에 있고, 스펙은 재현 가능한 수준의 규칙·사례가 필요할 때 쓴다.

| 행 | 기능 | 구분 | 선행 | 권장 | 이유 |
|---|---|---|---|---|---|
| 1 | 카탈로그 수집 | 핵심 | S1 | ○ | 온톨로지의 입력(프로파일·쿼리 이력). Q1 미해결: 쿼리 이력 출처 |
| 2 | 컬럼 프로파일링·FK 후보 탐지 | 핵심 | 1 | ○ | FK·junction 판정이 이후 모든 관계의 출발 |
| 3 | Term·ColumnAttribute 생성 | 핵심 | 2, S1, S2 | ○ **먼저** | 온톨로지의 중심. 프롬프트·정제·폴백·이름 충돌 |
| 4 | 시맨틱 컴파일 오케스트레이션 | 핵심 | 2, 3, 5~8 | ○ | 증분·병렬·정규 순서 커밋·취소 |
| 5 | 의미적 FK 해석 | 핵심 | 3, 8, S1, S2 | ○ **먼저** | 선언 FK·VDB+LLM·값 겹침 가지치기. 이 레포의 고유 로직 |
| 6 | SQL attribute 제안 | 핵심 | 3, 8, S1, S2 | ○ | 쿼리 이력 → 표현식. `_usage_score` 결함 포함 |
| 7 | bridge table SqlAttribute | 핵심 | 5, 8 | ○ | 순수 연결 테이블 처리 |
| 8 | 임베딩·벡터 저장 | 핵심 | S1, S2 | ○ | 라벨별 텍스트 형식이 검색 품질을 정함 |
| 9 | 온톨로지 큐레이션 API | 핵심 | 3, 6, 8, S1 | ○ | certify의 실제 효과, 수정 시 재임베딩 |
| 10 | 질의 시 온톨로지 읽기 | 핵심 | 3, 5, 8, S1 | ○ **먼저** | 검색 → 앵커 → BFS 조인 경로. 온톨로지가 쓰이는 지점 |
| 11 | SQL 생성·검증·수리·실행 | 핵심 | 10 | — | 패밀리(sql_from_semantic·검증 3종·재구성·실행·db_probe·information_agent·follow_up·response). 온톨로지 구현이 아니라 소비 쪽 |
| 12 | 답변 가능성 평가 | 핵심 | 8, S2 | — | 온톨로지 커버리지 점수. 필요하면 추가 |
| 13 | 소스 연결·수집 서비스·PII | 핵심 | 없음 | — | 패밀리(커넥터 10종·Vault·수집 서비스·PII). 인프라 |
| 14 | 접근 통제·태그·규칙 | 핵심 | S1 | — | 거버넌스 |
| 15 | 탐색·검색·모델 교환 | 핵심 | 3, 6, 8, S1 | — | 조회·YAML 교환 |
| 16 | 채팅 서비스·에이전트 설정 | 핵심 | 11, S3, S4 | — | 서빙 |
| 17 | 접근 인터페이스(게이트웨이·MCP·UI) | 핵심 | S3 | — | 패밀리 |
| 18~20 | 예측 / 배포·스킬 / clarify | 부속 | — | — | 기본 제외 |

공유 계약: **S1(저장 스키마)은 목적 핵심이라 별도 스펙 `storage-schema.md`로 쓰기를 권한다.** S2(모델 역할 설정)는 3행 선행이라 별도 스펙으로 두거나 8행에 포함한다(제안). S3·S4는 범위 밖.

스펙까지 안 가고 설명만 더 필요하면 Q2, Q3 같은 질문 문서가 가볍다(예: "FK 탐지 프롬프트", "import/export 직렬화 형식").

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 질문 경로(게이트웨이 → 백엔드 → 워커)와 구축 경로(수집·컴파일 서비스 → Postgres) |

검증: archify `finalize` 4개 게이트(validate·deliver·check·browser-check) 통과, `--repo-root`로 `sources` 인용 검증 포함(자동 검사). **시각 검토는 하지 않았다.**

### 그림 해설

**읽는 순서**
1. 질문 경로: 사용자 → Next.js 게이트웨이 → FastAPI 백엔드 → 채팅 워커(질의 그래프) → 원본 DB·Postgres·모델 엔드포인트.
2. 에이전트 경로: 에이전트 하니스 → MCP 서버 → (공개 API) 게이트웨이. 이후는 1과 같다.
3. 구축 경로: 수집·컴파일 서비스 → 원본 DB(스키마 추출) → Postgres(기록).

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| Next.js 게이트웨이 | 로그인·권한 검사 후 요청을 FastAPI로 중계. 계정·세션·API 토큰은 Prisma로 Postgres에 저장 | 입력: 브라우저·REST·MCP 요청. 출력: `x-auto-ontology-user-id` 헤더를 붙인 백엔드 요청, SSE 바이트 중계 | `frontend/auth/proxy-backend.ts:proxyToBackend`, `frontend/app/api/chat/completions/route.ts:POST`, `frontend/prisma/schema.prisma` | 코드 확인(프록시·헤더), 추론(Prisma가 같은 Postgres인지: `datasource db provider = "postgresql"`만 확인) |
| MCP 서버 | 공개 API를 읽기 전용 도구로 노출 | 입력: MCP 호출. 출력: 게이트웨이로 보내는 HTTP 요청 | `mcp/auto_ontology_mcp/tools.py:CURATED`, `server.py:build_server` | 코드 확인 |
| FastAPI 백엔드 | `/api` 라우터 15개(chat·terms·zones·tags·rules·search·exploration 등)와 수집 서비스 프록시 | 입력: 내부 헤더가 붙은 요청. 출력: JSON·SSE, Postgres 읽기·쓰기, 수집 서비스 호출 | `auto_ontology/server/__main__.py:create_app`, `server/ingestion/proxy.py` | 코드 확인 |
| 채팅 워커·질의 그래프 | 대화마다 서브프로세스에서 LangGraph를 실행해 이벤트를 흘림 | 입력: 질문·대화 기록. 출력: `step`·`sql`·`result`·`error` 이벤트(+`charts`) | `server/chat/worker.py:WarmPool`, `retrieval/text_to_sql/main.py:stream_agent_response`, `text_to_sql_graph.py:create_graph` | 코드 확인 |
| 수집·컴파일 서비스 | 스케줄·API로 카탈로그 수집과 시맨틱 컴파일 실행 | 입력: 연결 정보·트리거. 출력: Postgres 기록, 202 응답 | `ingestion_service/router.py`, `semantic/compile.py:run_semantic_compilation` | 코드 확인 |
| Postgres + pgvector | 카탈로그·온톨로지·앱 데이터·벡터 저장 | SQLAlchemy Core(`dal/`)와 `PostgresVDB`가 접근 | `dal/schema.py:term`, `vdb/postgres.py:PostgresVDB` | 코드 확인(두 접근 경로), 추론(같은 DB 인스턴스: README "stored in Postgres alongside the catalog") |
| 원본 데이터베이스 | 질의 대상과 수집 대상 | 커넥터가 SQL 실행·스키마 추출 | `connectors/registry.py:CONNECTOR_REGISTRY` | 코드 확인 |
| 모델 엔드포인트 | 추론·임베딩·재랭킹 | 역할별 ENDPOINT/API_KEY/MODEL | `utils/model_config.py` | 코드 확인 |

**흐름: 질문 한 개** (구조도의 굵은 선 + 그래프 노드는 `text_to_sql_graph.py` 435~610줄)
1. 게이트웨이가 `chat:use` 권한을 검사하고 `conversation_id`가 있으면 `conversation:write`도 검사한다 (`route.ts:POST`, 코드 확인).
2. 백엔드 `/api/chat/completions`가 대화 슬롯을 점유하고 워커를 받는다. 같은 대화의 살아 있는 스트림이 있으면 409다 (`server/chat/router.py` 모듈 docstring, 코드 확인).
3. 워커 안에서 `question_intent → question_extraction → retrieve_candidates`를 지나 intent에 따라 `information_agent`(종료), 예측 경로(켜져 있을 때), 또는 `prepare_candidates → refine_evidence → construct_sql_from_candidates`로 간다 (`create_graph`, 코드 확인).
4. 검증·값 점검·재구성 루프를 돈다. 재구성이 7회에 이르면 `unconstructable_sql_response`로 끝난다 (`MAX_RECONSTRUCTION_ATTEMPTS`, 코드 확인).
5. `execute_sql_query` → `check_empty_like_result` → `format_and_respond`. `result` 이벤트 뒤에 `_pump`가 차트·표 말풍선을 만들어 `charts` 이벤트로 이어 붙인다 (`router.py:_build_charts_event`, 코드 확인).

**미확인 영역**
- 수집·컴파일이 모델 엔드포인트를 호출하는 선은 그리지 않았다(컴파일 코드는 `llm_invoke`를 쓴다고 추정, 호출 지점은 `term_extractor.py`를 열어 확인하지 않음, `추론`).
- 백엔드 → 수집 서비스 트리거 선은 생략했다(`server/ingestion/proxy.py` 존재만 확인).
- 질문 경로에서 `connectors`가 UI 연결과 `CONNECTION_STRINGS` 중 무엇을 고르는지는 13행 때 확인한다.
- Vault, KumoRFM, PII 탐지는 그림에서 뺐다(2절 표 13행 PII·Vault, 18행 KumoRFM).

---

## 4. 질문 (Questions)

- [Q1: 이 온톨로지는 어떻게 구현되어 있는가](./questions/q1-ontology-implementation.md) — *평평한 시맨틱 레이어(테이블당 Term 1 + ColumnAttribute + SEMANTIC_FK), Postgres 관계형 저장. LLM 출력은 정제·폴백·값 겹침 검증으로 걸러 내고, certify 플래그는 검색·SQL 생성 경로에서 읽지 않는다.*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸 (승인 전이라 모두 미작성)
