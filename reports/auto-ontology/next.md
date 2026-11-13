---
sha: "c447003f72a822301e927196a4ecb5b597c308d5"
created: 2026-11-10
updated: 2026-11-10
---

# Next Session Plan: auto-ontology

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 고정: clone(`--depth 50`), SHA `c447003`, Apache-2.0, `artifacts/auto-ontology/repo-metadata.txt`
- [x] README 전문, `AGENTS.md`, `docs/mcp.md` 앞부분, `docs/connections.md` 앞부분, `pyproject.toml`, `mcp/README.md`
- [x] 진입점: `server/__main__.py` 라우터 등록, `ingestion_service/router.py` 라우트, `semantic/compile.py`·`pipeline.py`, `retrieval/text_to_sql/text_to_sql_graph.py`·`main.py`, `server/chat/router.py` 모듈 docstring, `mcp/.../tools.py`, `frontend/auth/auth.ts`·`proxy-backend.ts`·`proxy.ts`, `utils/model_config.py`
- [x] 모듈 docstring 일괄 조회(`semantic/`, `retrieval/` 하위, `server/` 하위, `pii_detection/`, `vdb/`, `mcp/`)
- [x] feature map 20행(핵심 17 / 부속 3), 공유 계약 4, 구조도 1장. 2026-11-10 목적(온톨로지 구현 이해)에 맞춰 재분할: 온톨로지 행 1~10은 세분, 11~20은 패밀리
- [x] Q1 작성: 온톨로지 구현(저장 스키마·컴파일 4단계·임베딩·질문 때 사용) — [q1](./questions/q1-ontology-implementation.md)
- [ ] 범위 승인 (아직 안 받음)

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [x] 분석 목적: 온톨로지 구현 이해(비교 아님) — 2026-11-10 답
- [ ] UI 연결과 `CONNECTION_STRINGS`의 우선순위가 질문 경로와 수집 경로에서 정말 다른가(`docs/connections.md` 주장, 코드 대조 안 함) — 1행 스펙에서 확인
- [ ] `retrieval/interactive/`는 어디서 쓰이는가(레포 안 호출자 없음) — 외부 `ontology-sql-eval` 레포 필요, 열지 않음
- [ ] Q1 10절의 남은 질문 6개(FK 탐지 프롬프트, 쿼리 이력 출처, SqlAttribute 임베딩 지점, Term 이름 한정 형식, hub-sibling 기본값, import/export 직렬화)
- [ ] README "certified definitions에 대해 검증"은 코드에서 확인 못 함 — certify는 검색·SQL 생성 경로에서 읽히지 않는다(Q1 6절). 다른 경로(`server/` 검증)가 있는지 7행 때 재확인
- [ ] 프런트엔드 Prisma 스키마가 같은 Postgres 인스턴스·DB를 쓰는가 — 16행에서 확인

## 3. 기능 스펙 후보

승인 전이라 후보가 아니라 권장안이다. [overview 2절 "권장 범위"](./overview.md): 행 1~10, 공유 계약 S1(별도 스펙)·S2. 3·5·10을 먼저.

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

범위 승인 후 쓸 첫 스펙: S1 `storage-schema.md`(선행 계약), 이어서 `Term·ColumnAttribute 생성` → `capabilities/term-generation.md`.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `auto_ontology/dal/schema.py` | 테이블 전부, `alembic/versions/` | S1: 컬럼 의미·제약·마이그레이션 이력 |
| `auto_ontology/semantic/fk_suggester.py` | `suggest_potential_foreign_keys` 본문·결정적 폴백 | 2행 |
| `auto_ontology/semantic/visit_enter.py` | `calculate_columns_profiling`, `_sampling_breaker` | 2행: 프로파일링 세부 |
| `auto_ontology/dal/terms.py` | `upsert_table_term`(417) 이후 | 3행: 충돌 한정 이름 형식 |
| `auto_ontology/retrieval/text_to_sql/agents/candidates_preparation.py` | `_identify_anchor`, 관련 테이블 강제 유지 규칙 | 10행 |

## 5. 참고 사항 및 후속 제안

- 대상 레포의 `CLAUDE.md`(`repos/auto-ontology/CLAUDE.md`)와 `frontend/CLAUDE.md`는 그 레포 메인테이너용 지침(커밋 메시지, PR 규칙 등)이라 이 작업에는 따르지 않았다.
- clone이 shallow(`--depth 50`)다. 기준 SHA 이전 이력이 필요하면 `git fetch --unshallow`.
- 실행(Docker Compose, NVIDIA API 키)은 하지 않았다. 스펙을 코드 기준으로 쓰므로 필요하지 않지만, 재구현 검증 때는 `nvapi-` 키와 Wide World Importers 시드(`auto-ontology-eval` 레포)가 필요하다.
- 코드량이 커서(Python 약 69,000줄) 스펙을 쓸 때 행마다 서브에이전트 병렬 작성이 알맞다. 선행이 없는 1, 2, 16행부터 가능하다.
