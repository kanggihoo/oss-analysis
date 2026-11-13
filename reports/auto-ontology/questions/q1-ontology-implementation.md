---
sha: "c447003f72a822301e927196a4ecb5b597c308d5"
created: 2026-11-10
updated: 2026-11-10
sources:
  - auto_ontology/dal/schema.py
  - auto_ontology/semantic/compile.py
  - auto_ontology/semantic/pipeline.py
  - auto_ontology/semantic/visit_enter.py
  - auto_ontology/semantic/term_extractor.py
  - auto_ontology/semantic/deterministic.py
  - auto_ontology/semantic/semantic_fk.py
  - auto_ontology/semantic/sql_attribute_suggester.py
  - auto_ontology/semantic/bridge_tables.py
  - auto_ontology/semantic/embed.py
  - auto_ontology/semantic/models.py
  - auto_ontology/semantic/domain.py
  - auto_ontology/dal/terms.py
  - auto_ontology/dal/attributes.py
  - auto_ontology/dal/exploration.py
  - auto_ontology/retrieval/text_to_sql/agents/candidates_retrieval.py
  - auto_ontology/retrieval/text_to_sql/agents/candidates_preparation.py
  - auto_ontology/retrieval/text_to_sql/agents/sql_from_semantic.py
  - auto_ontology/server/terms/service.py
  - README.md
---

# [Q1] 이 온톨로지는 어떻게 구현되어 있는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 항목마다 표기. 실행(Docker, NIM 호출)은 하지 않았고 모두 정적 읽기다.

---

## 1. 질문 및 결론

- **질문**: Auto Ontology가 말하는 "온톨로지"는 무엇으로 이루어져 있고, 원본 DB에서 어떻게 만들어지며, 질문에 답할 때 어떻게 쓰이는가?
- **핵심 결론**:
  1. 학술적 의미의 온톨로지(클래스 계층, `IS_A`·`PART_OF`)가 아니다. **"테이블 하나당 비즈니스 용어(Term) 하나 + 컬럼 별칭(ColumnAttribute) + 컬럼끼리의 의미적 FK 연결"로 된 평평한 시맨틱 레이어**이고, 그래프 DB가 아니라 **Postgres 관계형 테이블과 간선 테이블**에 저장된다. LLM 프롬프트가 `IS_A`·`PART_OF`·`ROLE` 관계를 만들지 말라고 명시한다(`코드 확인`).
  2. 만드는 일은 LLM 호출 4종(term 추출, FK 판정, SQL attribute 제안, bridge table SQL)과 **결정적 코드**(컬럼 프로파일링, 선언된 FK 처리, 이름 정규화, 값 겹침 검증)가 번갈아 한다. LLM 출력은 항상 후처리로 걸러 내고, LLM이 실패하면 테이블 이름 기반 폴백으로 간다(`코드 확인`).
  3. 질문 때는 이 레이어를 **임베딩 검색 → 앵커 컬럼 선택 → 테이블 사이 BFS 조인 경로**로 읽어 SQL 프롬프트에 넣는다. 사람이 certify한 플래그는 **DB와 UI에는 있지만 검색·SQL 생성 경로에서는 읽지 않는다**(`코드 확인`: 아래 6절). README의 "certified definitions에 대해 검증"은 코드에서 확인하지 못했다.

---

## 2. 무엇으로 이루어져 있나

Wide World Importers 예시로 보면(README 사례. 아래 이름은 설명용이며 실제 출력은 실행하지 않았다):

```text
테이블 sales.invoicelines (원본 DB의 물리 테이블)
   │ REPRESENTS (table__term)
   ▼
Term "Invoice Line"  ── synonyms, description, name_certified, description_certified
   │ PROPERTY_OF (column_attribute__term, attribute당 Term 1개로 UNIQUE)
   ├─ ColumnAttribute "Extended Price"  ← column__has_attribute ← 컬럼 invoicelines.extendedprice
   ├─ ColumnAttribute "Quantity"        ← 컬럼 invoicelines.quantity
   └─ SqlAttribute "Margin" (expression: SUM(...))   ← sql_attribute__term

컬럼 invoicelines.stockitemid (FK)
   └─ SEMANTIC_FK (column__semantic_fk) ──▶ ColumnAttribute "Stock Item Id" (stockitems 쪽 Term "Stock Item"에 속함)
```

| 개념 | 테이블 | 의미 | 검증 |
|---|---|---|---|
| Term | `term` (`name`, `description`, `source`, `synonyms`, 두 certified 플래그, `UNIQUE(name, source)`) | 비즈니스 개념. 테이블 하나가 Term 하나를 `REPRESENTS`한다(`table__term`) | 코드 확인 |
| ColumnAttribute | `column_attribute` (`name`, `source_column`, `term_name`, `table_id`, `certified`; 병합 키 5개 UNIQUE) | 컬럼에 붙이는 사용자 친화 이름·설명. 컬럼과는 `column__has_attribute`, Term과는 `column_attribute__term`(attribute당 Term 하나) | 코드 확인 |
| SEMANTIC_FK | `column__semantic_fk` (`use_in_join_paths`) | "이 컬럼은 다른 테이블의 저 ColumnAttribute를 가리킨다". 선언된 FK가 없어도 LLM·임베딩으로 추론해 만든다 | 코드 확인 |
| SqlAttribute | `sql_attribute` (`name` 전역 UNIQUE, `expression`, `source` ∈ `manual/sql/table/bridgeTable`, `certified`) | 검토된 SQL 표현식(마진, 롤링 합계 등). Term에 붙고(`sql_attribute__term`) SQL 본문은 `sql_query`로 간다(`sql_attribute__sql`) | 코드 확인 |
| CustomAnalysis | `custom_analysis` (`name` UNIQUE) + `custom_analysis__sql` | 사람이 쓴 이름 있는 SQL. Term과 별개로 검색 후보가 된다 | 코드 확인(스키마), 추론(용도) |

**Term 사이에 직접 간선 테이블은 없다.** `schema.py`의 테이블 목록에 `term__term` 같은 것이 없고, Term 간 관계 화면은 `column__semantic_fk`에서 파생한다(`dal/exploration.py:278`, `dal/terms.py:1471`이 이 테이블을 읽는다. `코드 확인`: 두 지점의 select, `추론`: 파생 방식 전체).

**저장 방식 두 가지 눈여겨볼 점** (`코드 확인`, `dal/schema.py` 주석):
- 간선 이름(`REPRESENTS`, `PROPERTY_OF`, `HAS_ATTRIBUTE`, `SEMANTIC_FK`)은 그래프 DB 시절의 이름이 남은 것이다. 지금은 일반 Postgres 테이블이고, `column__has_attribute`와 `column__semantic_fk`를 **일부러 한 테이블로 합치지 않았다**("이 컬럼이 속성의 인스턴스" vs "이 컬럼이 속성을 참조"는 의미와 카디널리티가 다르다).
- 조인 경로 탐색용 뷰 `join_path_edge`는 `SEMANTIC_FK`를 **한 방향으로만** 내보낸다. 양방향이면 같은 대상을 가리키는 두 `customer_id` 컬럼이 서로 조인되는 것처럼 보이는 가짜 경로가 생기기 때문이다.

---

## 3. 어떻게 만들어지나 (시맨틱 컴파일)

진입은 `run_semantic_compilation`(`semantic/compile.py:33`)이다. 순서는 **term 컴파일 → FK 해석 → SQL attribute 제안 → bridge table** 네 단계이고, 취소되면 term 컴파일이 끝난 뒤 나머지 세 단계는 건너뛴다(`코드 확인`).

### 3.1 단계 1: 테이블별 term 컴파일 (`process_table`, `visit_enter.py:753`)

테이블이 이미 Term을 가지고 있으면 건드리지 않는다. 처리 대상은 `fetch_all_tables_without_term`이 돌려주는 테이블뿐이므로 **증분 컴파일**이다(`pipeline.py:143`, `코드 확인`). 대상 테이블은 정규 순서로 정렬되고, 워커 3개가 병렬로 돌린다.

한 테이블에서 일어나는 일(`코드 확인`):

1. **프로파일링**: 컬럼마다 샘플 행과(설정이 켜져 있으면) `SELECT DISTINCT`로 `sample_values`·`is_unique`·날짜 `format`을 구해 컬럼에 저장한다. 웨어하우스가 응답하지 않으면 breaker가 열려 이번 실행의 나머지 테이블은 샘플링을 건너뛴다.
2. **FK 탐지**: 선언된 FK + LLM이 컬럼 이름·샘플로 FK 같은 컬럼을 추가로 제안한다(`suggest_potential_foreign_keys`). 이 결과는 저장하지 않고 "FK 컬럼은 속성 후보에서 뺀다"는 데만 쓴다. 컬럼이 3개 이상이고 LLM이 junction(연결 테이블)이라 하고 FK 컬럼이 2개 이상이어야만 `mark_table_as_junction`을 호출한다(한번 true면 지우지 않는다).
3. **속성 후보 만들기**(`column_attribute_specs`, `deterministic.py`): FK 컬럼을 뺀 나머지 컬럼마다 `source_column`·`datatype`·설명을 만든다. 설명이 필요한 컬럼은 15개씩 묶어 LLM이 한 문장으로 쓴다(배치 크기 `_DESCRIPTION_BATCH_SIZE = 15`, 어떤 컬럼이 "필요"한지의 조건은 읽지 않았다: `추론`). 날짜 컬럼은 저장 형식(`format:`)을 설명 뒤에 붙인다. 샘플 값은 날짜가 아닐 때만 설명에 붙인다.
4. **Term 제안**(`extract_term`, `term_extractor.py`): LLM에 한 번 묻는다. 시스템 프롬프트의 핵심 규칙은 이렇다.
   - 테이블당 Term **하나를 강하게 선호**한다. 두 개는 "서로 관련 없는 두 엔티티의 진짜 junction"일 때만 허용하고, 핵심 필드·메타데이터·감사 필드를 나누지 말라고 한다.
   - Term 이름은 공백이 있는 사용자 친화 이름(`Purchase Order`)이다. 모든 후보 컬럼을 정확히 한 Term에 배정하고 `display_name`을 붙인다.
   - `IS_A`·`PART_OF`·`ROLE` 관계는 제안하지 않는다.
   - 이름에 `ARC`·`HIST`·`STAGING` 같은 변형 접미어가 있으면 `display_name` 앞에 `Archived`·`Historical`을 붙인다.
   - 데이터베이스별 도메인 요약(`domains`·`core_entities`·`business_rules`, `semantic/domain.py`)이 있으면 프롬프트에 끼워 넣는다. 파일(`<database>.json`)이 없으면 건너뛴다.
   - 설명에서 "also known as", 괄호 약어 등 **글자로 적힌** 별칭만 따로 한 번 더 LLM으로 뽑아 `synonyms`로 둔다(추측 금지 프롬프트).
5. **정제**(`_sanitize_result`): 이름이 `^[A-Z][A-Za-z0-9]*( [A-Za-z][A-Za-z0-9]*)*$` 형식이 아니거나 `unnamed/unknown/none`이면 테이블 이름에서 만든 폴백(`to_term_name`)으로 바꾼다. 허용되지 않은 컬럼·중복 배정은 버리고, 배정 안 된 컬럼은 첫 Term에 붙인다. 결과가 비면 "Business entity represented by table X"라는 폴백 Term을 만든다. **LLM이 아무리 이상한 답을 줘도 모든 컬럼은 정확히 하나의 Term에 속한다.**
6. **저장**(`_commit_terms` → `upsert_table_term`, `merge_column_attribute`): 이름이 다른 테이블의 Term과 충돌하면 테이블의 풀 카탈로그 신원(database·schema·table)으로 **한정(qualify)한 이름**으로 저장한다. 충돌 때 어느 테이블이 원래 이름을 가지는지가 실행마다 달라지지 않도록 저장 순서만 정규 순서 큐(`_OrderedCommitQueue`)로 직렬화하고, LLM 호출은 병렬로 둔다.
7. **임베딩**: 저장 직후 같은 테이블의 Term·ColumnAttribute를 읽어 `SemanticEmbedder.embed_term`으로 벡터 저장소에 쓴다(5절).

### 3.2 단계 2: 의미적 FK 해석 (`resolve_semantic_fks`, `semantic_fk.py:91`)

속성 후보에서 뺀 FK 컬럼마다 "어느 ColumnAttribute를 가리키는가"를 정한다(`코드 확인`).

1. 선언된 FK가 있으면 **대상 컬럼의 ColumnAttribute를 바로** 연결한다. 같은 테이블을 가리키는 선언은 자기 참조라 버린다.
2. 없으면 컬럼 문맥을 임베딩해 의미 VDB에서 **가장 비슷한 ColumnAttribute 5개**를 찾고(FK 자신의 테이블 후보는 제외), LLM에게 "확신할 때만 하나 고르고 아니면 null"을 시킨다. LLM이 포기하면 라이브 DB를 조회해 **샘플 값이 겹치는 후보**로 폴백한다.
3. 끝나면 `prune_disjoint_semantic_fks`가 **값이 한 개도 안 겹치는 추론 간선을 지운다**(`SELECT ... WHERE col IN (SELECT 대상컬럼 ...) LIMIT 1`). 겹침이 적다는 것은 증거가 못 되므로 0일 때만 지우고, 소스 컬럼이 전부 NULL이어도 지운다.
4. 같은 소스 테이블의 여러 컬럼이 같은 대상을 가리키면(주문 테이블의 `OrderedBy`·`ApprovedBy` 같은) LLM이 **기본 조인 관계 하나**를 고른다(`select_semantic_fk_join_defaults`).

### 3.3 단계 3: SQL attribute 제안 (`suggest_sql_attributes`)

Term마다 그 테이블들에 연결된 **쿼리 이력**(`sql_query`)에서 `sqlglot`으로 표현식을 뽑는다(WHERE/ON 조건, 집계, 함수, CASE, HAVING, UNION 분기). 상위 10개를 LLM에 보여 "이름을 붙일 만한 것이 있는가"를 묻고, 있으면 `create_sql_attribute`로 저장한 뒤 새로 쓴 노드만 임베딩한다.

> **알려진 버그(코드가 스스로 적어 둠)**: 표현식을 사용 빈도로 순위 매기는 `_usage_score`는 **항상 `0.0`을 돌려준다.** 점수 함수가 `count_monthly_YYYY_MM`을 찾는데 실제 쓰는 이름은 `count_8_2026` 형식이라 한 번도 맞은 적이 없다. 그래서 "상위 10개"는 사용량 순이 아니라 딕셔너리 삽입 순이다. 주석이 "고치지 말 것, 별도 변경으로 하라"고 못박았다(`코드 확인`, `sql_attribute_suggester.py` `_usage_score` docstring).

### 3.4 단계 4: bridge table (`build_bridge_tables_sql_attributes`)

컬럼이 **전부 FK**인 순수 연결 테이블은 Term을 만들지 않는다. LLM이 구조적 조인 SQL을 만들고, 그 FK 대상 테이블들을 `REPRESENTS`하는 Term들 중 설명과 **재랭킹(RERANK 모델)**으로 더 잘 맞는 쪽에 SqlAttribute(`source = 'bridgeTable'`)로 붙인다(`코드 확인`: 모듈 docstring, `추론`: 재랭킹 호출 세부).

---

## 4. 모델이 맡는 일과 맡지 않는 일

| 일 | 누가 | 검증 |
|---|---|---|
| 컬럼 프로파일링, 선언된 FK 처리, 이름 정규화·폴백, Term 이름 충돌 해소, 값 겹침으로 FK 간선 제거, junction을 한번 true면 유지 | 결정적 코드 | 코드 확인 |
| Term 이름·설명, 컬럼 표시 이름, 컬럼 설명, FK 후보, junction 여부, 별칭 추출, FK 대상 고르기, 기본 조인 선택, SQL attribute 제안, bridge SQL | LLM(`REASONING`; 구조화 출력) | 코드 확인(호출 지점은 3절 각 모듈), 추론(모델 역할 배정) |
| 임베딩·유사 후보 검색 | `EMBED` 모델 + pgvector | 코드 확인 |
| bridge SqlAttribute를 붙일 Term 고르기 | `RERANK` 모델 | 코드 확인(docstring) |

---

## 5. 벡터 저장소에 무엇을 넣나 (`semantic/embed.py` `_build_rows`)

의미 VDB 행은 두 종류 이상이다(`코드 확인`).

| label | 임베딩할 텍스트 | 메타데이터 |
|---|---|---|
| `Term` | `Term: <name>. <description>` | `name`, `database_name`, `schema_names`, `id` |
| `ColumnAttribute` | `ColumnAttribute: <name> of Term <term><(synonyms)>. <description><샘플 값 블록>` | `term_name`, `source_column`, `table_id`, `table_name`, `is_unique`, `data_type`, `id` |

- **Term의 동의어는 ColumnAttribute 텍스트에 붙는다.** "Customer (Client, Buyer)" 같은 별칭이 속성 검색에 걸리게 하려는 것이다.
- 질문 쪽 검색은 `Term`·`ColumnAttribute`·`SqlAttribute`·`CustomAnalysis` label로 나눠 묻는다(`candidates_retrieval.py` docstring, `코드 확인`). 임베딩 모델이 없으면(`EMBED_API_KEY` 미설정) 컴파일은 임베딩 없이 진행된다(`build_semantic_embedder`가 `None`).
- 사람이 term·컬럼 속성을 고치면 VDB 행을 다시 임베딩하고, **certified 플래그만 바뀐 경우는 임베딩을 건너뛴다**(`server/terms/service.py` `update_column_attribute` docstring, `코드 확인`).

---

## 6. 질문 때 쓰이는 방식 (질의 에이전트가 온톨로지를 읽는 경로)

1. `CandidateRetrievalAgent`: 질문에서 뽑은 **엔티티마다** 의미 VDB에서 ColumnAttribute를 찾고, evidence 전체로 한 번 더 찾는다. `CustomAnalysis`와 `SqlAttribute`는 질문 전체로 한 번씩 **top 3**을 찾는다. 질문의 subject가 있으면 Term top-1도 찾는다(`코드 확인`).
2. `CandidatePreparationAgent`: 찾은 ColumnAttribute를 저장소에서 컬럼·테이블 문맥과 Term 동의어로 보강한다. 후보가 둘 이상이면 LLM이 **앵커 속성**(질문의 주제)을 하나 고른다(`_identify_anchor`, 후보 1개면 LLM 없이 그것을 앵커로).
3. 앵커 컬럼에서 나머지 후보 컬럼까지 `find_join_path`를 호출한다. 이 함수는 **테이블 사이 BFS**다. 모든 `SEMANTIC_FK` 관계를 "FK 컬럼 테이블 → 소유 컬럼 테이블" 간선으로 만들고, 역방향(소유 → FK)은 소유 컬럼이 그 테이블의 **선언된 PK일 때만** 추가한다. 최대 hop은 `(MAX_PATH_DEPTH + 2) // 4 = (30+2)//4 = 8`이다. 다른 데이터베이스 사이 경로는 거부한다(`코드 확인`).
4. 앵커 테이블의 FK가 가리키는 같은 hub를 공유하는 형제 테이블은 선택적으로(`_HUB_SIBLING_EXPANSION_ENABLED`, 환경변수 `HUB_SIBLING_EXPANSION_ENABLED` 기본 `false` — 기본으로는 꺼져 있다) 후보에 더하고, 연결 테이블·pairwise bridge도 관련 테이블에 강제 유지한다(`코드 확인`: 코드 주석).
5. `SQLFromCandidatesAgent`: 앵커 속성, `attribute_join_paths`, 관련 테이블, 관련 쿼리, `SqlAttribute`·`CustomAnalysis` 문자열, `term_synonyms`를 프롬프트에 넣어 SQL을 만든다(`코드 확인`).

**certify가 이 경로에 영향을 주는가?** `certified`가 나오는 파일은 `server/`(UI·API), `dal/`(집계·저장·검색 화면), `retrieval/text_to_sql/db_probe/literal_check.py`(주석에 단어만 등장)뿐이다. `retrieval/data_access/`·`vdb/`·`candidates_*`·`sql_from_semantic.py`에는 `certified`가 없다(`grep`, `코드 확인`). 즉 **certify는 사람을 위한 상태 표시이고, 인증된 정의만 쓰거나 우선하는 로직은 이 SHA에 없다.**

---

## 7. 이 구현에서 눈여겨볼 설계 선택

- **"온톨로지"의 폭을 의도적으로 좁혔다.** 테이블당 Term 하나, 계층·상속 없음, 개념 간 관계는 FK에서 파생. 대신 컬럼 → 개념 매핑과 조인 경로의 **정확성**에 공을 들인다(값 겹침 검증, PK 방향 규칙, junction 처리).
- **LLM을 믿지 않는 구조.** 구조화 출력(Pydantic) + 정제 + 폴백 + 결정적 검증(값 겹침). 예: 정규식에 안 맞는 Term 이름은 버리고, 빈 결과는 테이블 이름 폴백, 확신 없는 FK는 `null`.
- **증분·재개 가능.** 이미 Term이 있는 테이블은 다시 처리하지 않으므로, 사람이 고친 이름·설명이 재컴파일로 덮어써지지 않는다. 카탈로그의 테이블·컬럼 설명도 `coalesce(new, existing)`로 큐레이션된 값이 우선한다(`dal/datasources.py` `apply_metadata_batch` docstring, `코드 확인`).
- **동시성 설계**: LLM 호출은 병렬, 이름 충돌 소유권을 정하는 커밋은 정규 순서로 직렬(`_OrderedCommitQueue.skip`은 취소 시 워커를 붙잡지 않으려고 대기 없이 건너뜀).
- **죽은 흔적**: `SeedSelectionResult`(시드 테이블 BFS)와 `PotentialFkResult` 등 모델이 남아 있으나 현재 파이프라인은 "flat table-by-table"이라고 스스로 밝힌다(`pipeline.py` docstring). 시드 선택이 쓰이는지는 확인하지 않았다(`미확인`).

---

## 8. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 저장 모델 | `auto_ontology/dal/schema.py` | `term`(456), `column_attribute`(487), `column__semantic_fk`(576), `sql_attribute`(599), `join_path_edge`(뷰) | 테이블·간선·제약·주석 |
| 컴파일 진입 | `auto_ontology/semantic/compile.py` | `run_semantic_compilation` | 4단계 순서, 취소 시 후반 건너뜀 |
| 테이블별 컴파일 | `auto_ontology/semantic/pipeline.py`, `visit_enter.py` | `compile_semantic_layer`, `process_table` | 증분·병렬·정규 순서 커밋 |
| Term 제안 | `auto_ontology/semantic/term_extractor.py` | `_SYSTEM`, `extract_term`, `_sanitize_result`, `_fallback_result` | 프롬프트 규칙과 정제 |
| 속성 후보 | `auto_ontology/semantic/deterministic.py` | `column_attribute_specs`, `to_term_name` | FK 제외, 설명·형식 |
| FK 해석 | `auto_ontology/semantic/semantic_fk.py` | `resolve_semantic_fks`, `prune_disjoint_semantic_fks` | 선언·VDB+LLM·프로빙·가지치기 |
| SQL attribute | `auto_ontology/semantic/sql_attribute_suggester.py`, `bridge_tables.py` | `suggest_sql_attributes`, `_usage_score`, `build_bridge_tables_sql_attributes` | 쿼리 이력 → 제안 / 순수 FK 테이블 |
| 임베딩 | `auto_ontology/semantic/embed.py` | `SemanticEmbedder.embed_term`, `_build_rows` | VDB 행 형식 |
| 조인 경로 | `auto_ontology/dal/attributes.py` | `find_join_path`(1037), `_find_table_join_hops`(792), `MAX_PATH_DEPTH`(49) | BFS와 PK 방향 규칙 |
| 질문 때 읽기 | `auto_ontology/retrieval/text_to_sql/agents/candidates_retrieval.py`, `candidates_preparation.py`, `sql_from_semantic.py` | `CandidateRetrievalAgent`, `_identify_anchor`, `SQLFromCandidatesAgent` | 검색·앵커·프롬프트 |
| certify 집계 | `auto_ontology/dal/terms.py` | `_certification` | `certified/partial/pending` 롤업(UI용) |

---

## 9. 검증 과정 및 실행 결과

- **수행한 것**: `sed`·`grep`으로 위 파일의 해당 구간을 읽었다. 실행·빌드·모델 호출은 하지 않았다. 테스트 파일은 열지 않았다.
- **직접 확인한 부정 주장**: "certified가 검색 경로에 없다"는 `grep -rln certified auto_ontology`로 파일 목록을 얻어 `retrieval/` 쪽 파일을 확인한 결과다(`literal_check.py`는 주석의 단어만).
- **README와의 차이**: README "Validate: check generated queries against certified definitions"는 이 SHA 코드에서 확인하지 못했다. 서버가 SQL을 SqlAttribute·조인 경로·값 검증(`db_probe`)과 대조하는 로직은 있지만 certify 여부로 거르지는 않는다(`코드 확인`).
- **예시의 한계**: 2절 그림의 이름(`Invoice Line` 등)은 README의 사례 기반 설명용이고 실제 컴파일 출력이 아니다.

---

## 10. 남은 질문 및 추가 조사 사항

- [ ] `suggest_potential_foreign_keys`(`fk_suggester.py`)가 이름·샘플로 FK를 판정하는 프롬프트와 결정적 폴백 규칙 — 현재는 모델 목록만 확인
- [ ] 쿼리 이력(`sql_query`)은 누가 채우는가: 수집 단계(`catalog/query_stats.py`)인가, 채팅이 남기는가? 사용 카운터(`total_counter`) 갱신 경로
- [ ] `SqlAttribute`를 의미 VDB에 임베딩하는 지점과 검색 시 필터(`database_name`, 존 권한)
- [ ] Term 이름 충돌 한정 규칙의 정확한 문자열 형식(`upsert_table_term` 이후 부분)
- [ ] `find_anchor_hub_siblings`·`find_kept_table_bridges`의 규칙(hub-sibling 확장은 기본 off로 확인함)
- [ ] 모델 import/export가 이 구조를 어떻게 직렬화하는가(`server/model_interchange/schemas.py`)
