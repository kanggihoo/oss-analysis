---
sha: "63f62b2cafdaf0c30d9a409eae9d08b8d7ea272e"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/core/ops/search.ts
  - src/core/ops/search-exact.ts
  - src/core/ops/image.ts
  - src/core/ops/context.ts
  - src/core/search/hybrid.ts
  - src/core/search/hybrid/request.ts
  - src/core/search/hybrid/arms.ts
  - src/core/search/hybrid/rank.ts
  - src/core/search/hybrid/keyword-only.ts
  - src/core/search/hybrid/cache-stages.ts
  - src/core/search/mode.ts
  - src/core/search/fusion-lists.ts
  - src/core/search/rrf-page-fusion.ts
  - src/core/search/intent-weights.ts
  - src/core/search/query-intent.ts
  - src/core/search/cosine-rescore.ts
  - src/core/search/dedup.ts
  - src/core/search/rerank.ts
  - src/core/search/expansion.ts
  - src/core/search/token-budget.ts
  - src/core/search/sql-ranking.ts
  - src/core/search/keyword-statement.ts
  - src/core/search/title-statement.ts
  - src/core/search/vector-statement.ts
  - src/core/search/eval-pool-depth.ts
  - src/core/search/source-boost.ts
  - src/core/search/recency-decay.ts
  - src/core/search/metadata-boost-gate.ts
  - src/core/search/read-policy-sql.ts
  - src/core/search/private-visibility.ts
  - src/core/search/safe-chunks.ts
  - src/core/search/snippet-cap.ts
  - src/core/search/lean-rows.ts
  - src/core/search/score-contract.ts
  - src/core/search/facts-arm.ts
  - src/core/search/query-arms.ts
  - src/core/search/evidence-delivery.ts
  - src/core/search/keyword-paging.ts
  - src/core/search/query-cache.ts
  - src/core/search/query-cache-gate.ts
  - src/core/search/exact-scan.ts
  - src/core/search/by-image.ts
  - src/core/pglite-engine.ts
  - src/core/postgres-engine.ts
  - src/core/engine.ts
  - src/core/types.ts
  - src/core/quarantine.ts
  - src/core/embedding-disabled.ts
  - src/cli/main.ts
  - src/cli/command-route.ts
  - src/core/ops/facts.ts
  - src/core/think/gather.ts
  - src/core/search/query-prefix.ts
  - src/core/search/output-redaction.ts
  - src/core/search/title-match.ts
  - src/core/search/hybrid/alias-resolved.ts
  - src/core/search/hybrid/degraded.ts
  - src/core/search/provenance-demotion.ts
  - src/core/search/config-values.ts
  - src/core/engine-sql/titles.ts
  - src/core/source-id.ts
  - src/commands/config.ts
depends:
  - ./engine-and-schema.md
  - ./ai-gateway.md
  - ./page-storage-and-import.md
status: ready
reimplementation: 미실행
---

# 하이브리드 검색 (search · query · search_exact · 이미지 질의)

> 질의 문자열(또는 이미지)을 받아 키워드·제목·벡터 후보를 RRF로 합치고 재점수·중복 제거·(선택) 리랭크·한도 절단을 거쳐, 소스 격리와 삭제·격리 규칙을 지킨 **청크 행 목록**(slug, 청크 텍스트, 점수, 출처 필드)을 돌려주는 기능이다. 모드 번들(conservative/balanced/tokenmax)이 한도·확장·리랭크 기본값을 정하고, 키가 없으면 키워드만으로 돌아가며, `search_exact`는 순위 없이 리터럴 전수 조회를 한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표는 `query "<질문>"`(CLI `ask`는 별칭) 기본 호출이다. 가정: 모드 balanced, 임베딩 키와 리랭커 키가 있음. `search`는 1.4 R-11의 차이만 갖는다. 3번의 두 갈래는 병렬이다.

1. **입구**: 매개변수 검증 → 소스 범위(R-40) → 비공개·격리·삭제 가시성 옵션 → 호출별 `mode`(로컬 호출자만, R-02) 해석.
2. `hybridSearchCached` → (의미 캐시는 하드 비활성이라 건너뜀, R-70) → `hybridSearch`.
3. **요청 해석**: 모드 번들 + 설정 덮어쓰기로 노브 확정(R-03, R-04) → 질의 의도 정규식 분류(R-13) → `limit`(R-05)과 arm당 후보 풀 크기(R-06).
4. **후보 arm(병렬)**
   - ① 키워드 arm(청크 FTS)와 제목 arm(페이지 제목 FTS)는 **원 질의**로 돈다(R-20, R-21).
   - ② 벡터 쪽: (확장이 켜졌을 때만 변형 생성, R-24) → 질의 임베딩 → 벡터 arm(질의·변형마다, R-22).
5. **결합**: 벡터 arm이 비어 있지 않으면 키워드 OR 완화 행 제거 → 가중 RRF(R-30, R-31) → 코사인 재점수(R-32) → 사후 부스트(R-33).
6. **정리**: 페이지 중복 제거(R-34) → 리랭크(상위 `topNIn`, R-35) → `limit` 슬라이스(R-36) → 토큰 예산(R-37).
7. **op 계층(query)**: 별칭 fan-out(부가) → 사실 행(R-52) → 신뢰도 등급 메타(부가) → 대화형 페이지 증거 전달(R-51) → 비밀 마스킹 → 청크 글자 상한(R-50) → 원격 호출자는 lean 필드로 투영(R-53) → 반환.

키가 없으면 3번 ②가 시작되지 않고 5의 벡터 결합·재점수와 6의 리랭크가 빠진다(R-60). 이 흐름이 질문 ③의 앞 절반이다: 검색은 **청크를 후보로 모아 페이지 단위로 투표시키고, 상위 N개 청크 행(기본 10/25/50, 토큰 예산 안)만 LLM이 읽을 형태로 돌려준다**. 점수 컷은 기본으로 없다(R-36).

### 1.2 범위·통합 지점

- 제공: `search`, `query`(= `ask`), `search_exact`, `query`의 `image` 분기와 `search_by_image`, 모드 번들·노브 해석, 의미 캐시의 키·TTL·무효화 규칙(현재 하드 비활성), 키 없음·실패 때의 동작, 소스 격리와 삭제·격리 규칙의 검색 적용.
- 제외(이유):
  - **부가 단계**(아래 표). 각각 별도 상태(링크 그래프, 별칭 표, 피드백 저장소, 사실 표)나 별도 기능을 읽는 단계라 이 스펙의 코어 계약(arm → RRF → 재점수 → dedup → 리랭크 → 절단 → 예산)과 분리했다. 기본 설치에서 켜진 단계는 행을 끼우거나 순서를 바꿀 수 있으므로 **이 스펙의 코어만으로는 기본 설치의 출력과 바이트 단위로 같아지지 않는다**(코어 계약만 재현 범위).
  - CJK 질의의 키워드 SQL 세부(`cjk-keyword-sql.ts`): CJK이면 청크 텍스트 LIKE/ILIKE 용어 AND 매칭으로 바뀐다는 사실만 R-20에 둔다. 언어별 변형이라 제외.
  - 멀티모달 임베딩 호출(`embedMultimodal*`)·교차 모달 라우팅(`crossModal`, `unified_multimodal`): ai-gateway 스펙이 제외한 호출이고, 기본값에서 `image`/`both` 라우팅은 이미지 임베딩이 있는 브레인에서만 켜진다. 경계만 R-81.
  - 진단·관측: `explain`, `explain_target`, `search_stats`, `search_tune`, 텔레메트리, 평가 캡처, `held_files`·`projection_readiness`·`coverage` 응답 메타. 결과 행 목록을 바꾸지 않는다.
  - 메모리 verbs `recall`(지도 11행)과 `think`(7행)가 이 검색을 부르는 지점은 R-90 한 줄만.
- 부가 단계(코어 밖). "기본"은 `balanced`/`query` 기준. 각 근거는 2.1.

  | 단계 | 기본 | 효과 한 줄 |
  |---|---|---|
  | 별칭 fan-out | 켜짐(`search.alias_fanout_max` 4) | 질의가 이름을 가리키면 그 엔티티의 다른 이름으로 키워드 검색을 더 해 최대 8페이지를 상위 2개 뒤에 끼움 |
  | 생성 페이지 강등 | 켜짐(`search.demote_generated=false`로 끔) | gbrain이 쓴 요약 페이지(`dream_generated`, `extract_receipt`)를 엔티티를 가리키는 질의에서 같은 엔티티의 원본 기록보다 ×0.5로 내림 |
  | 별칭 hop / 정확 조회 계층 | 켜짐 | 질의가 별칭·slug·정확 제목이면 그 페이지를 끼우거나 1위로 올림 |
  | collapse / rank priors | 켜짐(`search.collapse`, `search.rank_priors`) | 쌍둥이·리다이렉트·사본 페이지를 한 슬롯으로 접고, 조직>사람 등 곱셈 사전 적용 |
  | 관계 arm·플래너·재고정·슬롯 | balanced·tokenmax 켜짐 | 관계형 질문이면 타입 간선에서 후보를 만들어 RRF에 4번째 목록으로 넣음 |
  | graph signals | balanced·tokenmax 켜짐 | 상위 페이지 사이 링크로 ×1.05/×1.10/×0.95 |
  | 피드백 단계 | 켜짐(평가 없으면 무변화) | 학습된 페이지 가중으로 순서 점수 ×[1-λ, 1+λ] |
  | 신뢰도 등급(CRAG) | 메타만 | 결과 신뢰 등급을 메타에 붙임. 에스컬레이션·`think` 자동 실행은 기본 꺼짐 |
  | 증거 전달(`return_unit`) | 대화형 히트가 있을 때만 | 결과를 청크 대신 창·절·전체 페이지로 넓힘(R-51에 경계) |
  | 사실 예약(temporal), 엔티티 앵커, 적응 반환, autocut | 꺼짐 | 번들·설정으로 켤 때만 |
  | System One `decide` | 꺼짐 | 설정 `decide.*`가 있을 때만 |
  | 교차 모달 라우팅 | 의도가 image이고 멀티모달 모델·이미지 벡터가 있을 때 | 이미지 벡터 arm 추가, 키워드 arm 생략 |

- 외부 의존·선행 계약:
  - [ai-gateway](./ai-gateway.md): 질의 임베딩 `embedQuery`(ai-gateway R-23, 캐시 512개·10분), `isAvailable`·`diagnoseEmbedding`(키 없음 판정, ai-gateway R-05·R-26), 확장 `expand`(ai-gateway R-40·R-41, 실패해도 `[query]`, 예산이 막지 않음 R-61), 리랭크 `rerank`(ai-gateway R-50~R-52, `RerankError`의 `reason`), 기본 리랭커 모델 `voyage:rerank-3-lite`(ai-gateway R-04).
  - [engine-and-schema](./engine-and-schema.md) 1.3: `pages`·`content_chunks`·`sources`·`config`의 컬럼 의미, `searchKeyword`·`searchTitles`·`searchVector` 엔진 메서드 군, `deleted_at`·`search_vector`·`text_projection_revision` 의미.
  - [page-storage-and-import](./page-storage-and-import.md): 청크는 `compiled_truth`·`timeline`·`fenced_code` 순서로 만들어지고(page-storage R-17), 격리 페이지는 청크가 0개이며(page-storage R-17), 저널 경로는 NULL 벡터로 커밋한 뒤 effect가 임베딩을 채운다(page-storage R-21, R-22). 그래서 벡터가 아직 NULL인 청크는 키워드 arm에만 잡힌다.
  - 호출자가 제공: 정수 `limit`, 소스 범위가 실린 `OperationContext`(`remote`, `sourceId`, `auth.allowedSources`), 엔진.
- 소유 상태·부작용: 검색 자체는 읽기 전용이다. 부수 쓰기는 반환 페이지의 `last_retrieved_at` 갱신(fire-and-forget, `bumpLastRetrievedAt`), 텔레메트리·감사 JSONL(리랭크 실패), 의미 캐시 `query_cache` 쓰기(현재 비활성). 프로세스 내 캐시: 질의 임베딩 LRU(ai-gateway), 모드 설정 스냅샷(호출당 1회 읽음).

### 1.3 인터페이스와 데이터 의미

연산(모두 `scope: read`, 변경 없음). 파라미터는 원문 이름.

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `search` (CLI `gbrain search <query>`) | `query`(필수), `limit`(기본 20), `offset`, `match`(`hybrid`\|`keyword`), `cursor`, `mode`(로컬만), `source_id`, `types`, `where`, `snippet_chars`, `return_unit`, `return_window`, `token_budget`, `salience`, `recency`, `fields`, `min_trust` → 행 목록 + 응답 메타 | "저렴한" 하이브리드: 확장 없음. 기본 20행 |
| `query` (CLI `gbrain query`, 별칭 `ask`) | `query` 또는 `image`(base64)+`image_mime`, `limit`, `offset`, `types`, `where`, `snippet_chars`, `return_unit`, `return_window`, `token_budget`, `expand`, `detail`(`low`\|`medium`\|`high`), `fields`, `mode`(로컬만), `lang`, `symbol_kind`, `near_symbol`, `walk_depth`, `salience`, `recency`, `since`, `until`, `source_id`, `cross_modal`, `embedding_column`, `adaptive_return`, `autocut`, `relational`, `min_trust`, `explain*` → 행 목록 + 메타 | `query`와 `image` 둘 다 없으면 `invalid_params`. `limit`이 비었거나 0이면 모드 한도 |
| `search_exact` (CLI `gbrain search --exact`) | `phrase`(필수, ≤500자), `case_sensitive`, `source_id`, `types`, `slug_prefix`, `limit`(기본 100, 최대 1000), `after`, `max_seconds`(기본 30, 최대 120), `min_trust` → `{phrase, case_sensitive, matches[], complete, incomplete_reasons, resume_after, pages_scanned, unreadable, excluded_slug_prefixes, latency_ms}` | 순위 없음 |
| `search_by_image` | `image_path`(로컬만)\|`image_url`\|`image_data`(정확히 하나), `image_mime`, `query`(텍스트 보정), `limit`(기본 20), `offset`, `source_id` → 이미지 청크 행 | 경계만(R-81) |

**결과 행(청크 행)**: 하나는 한 페이지의 한 청크다. 코어 필드(타입은 `SearchResult`, C-26): `slug`, `page_id`, `title`, `type`, `chunk_text`, `chunk_source`(`compiled_truth`\|`timeline`\|`fenced_code`), `chunk_id`, `chunk_index`, `score`, `stale`, `source_id`(소스 격리 후 사용 키는 `(source_id, slug)`), 선택 `effective_date`·`effective_date_source`. 그 위에 진단·표지 필드(`cosine`, `base_score`, `rerank_score`, `keyword_hit`, 각종 `*_boost`, `evidence`, `superseded`, `unverified`, `content_flag`, `trust_tier` 등)가 붙을 수 있다. 사실 행(R-52)은 `result_type:'fact'`와 `fact_id`·`follow_up`을 갖고 page 필드는 없다. 원격 호출자의 기본 투영(lean)은 R-53.

**설정 키(DB `config` 평면, `gbrain config set <key> <값>`)**. 원문 이름·기본값·잘못된 값 처리는 R-02~R-04에 둔다.

| 키 | 의미 | 기본 |
|---|---|---|
| `search.mode` | 번들 선택 | 없으면 `balanced` |
| `search.mcp_keyword_only` | `search`를 키워드 전용으로 강제(질의 텍스트가 임베딩 공급자에 안 나감). `'true'`만 유효 | 꺼짐 |
| `search.<노브>` | 번들 노브 덮어쓰기. 이름 표는 C-03(`KNOB_CONFIG_KEY`) | 번들 값 |
| `search.source_boosts` | slug 접두 가중 덮어쓰기(`prefix:factor,…`, `none`이면 기본 표 폐기). 환경변수 `GBRAIN_SOURCE_BOOST`가 이김 | C-25 기본 표 |
| `search.remote_private_pages` | `visible`\|`true`\|`1`이면 원격 호출자에게도 `visibility: private` 페이지 노출 | 숨김 |
| `embedding_query_prefix` | 질의 임베딩 앞에 붙일 지시문(키워드·저장 벡터에는 안 붙음) | 없음 |
| `search.query_facts_arm` | 사실 행 켜기(`false\|off\|0\|no`면 끔) | 켜짐 |
| `agent.search_snippet_chars` | 서브에이전트 호출자의 청크 글자 상한 | 300 |

환경변수: `GBRAIN_QUERY_EMBED_TIMEOUT_MS`(질의 임베딩 데드라인, 기본 6000), `GBRAIN_SOURCE_BOOST`, `GBRAIN_SEARCH_EXCLUDE`(하드 제외 접두 추가), `GBRAIN_SEARCH_SALVAGE=off`(부분 실패 구제와 예산 failsafe 끔), `GBRAIN_REMOTE_PRIVATE_PAGES=1`.

### 1.4 행동 규칙과 남은 질문

검증 수준 표기: "코드 확인"은 구현부를 읽음, "실행 확인"은 `agent-memory/artifacts/gbrain/search-demos/demo-pure.mts`(deno, 순수 함수와 줄 범위 발췌, 대체물은 스크립트 머리말)로 돌려 확인. 브레인 DB·공급자 호출은 실행하지 못했다(확인 한계).

**A. 진입·모드·한도**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | CLI `ask <질문>` | `query`로 바꿔 실행한다. `search --exact "<구>"`는 `--exact` 인자를 떼고 `search-exact`로 라우팅된다(`cli/command-route.ts:11-14`) | 코드 확인 |
| R-02 | 모드 선택 | 키 `search.mode`(DB `config`)의 값을 trim+소문자로 읽어 `conservative`·`balanced`·`tokenmax` 중 하나면 그 번들, 없거나 알 수 없는 값이면 `balanced`(오류 없음). 호출별 `mode`는 **로컬 신뢰 호출자(`ctx.remote === false`)만** 유효하고 알 수 없는 값이면 `invalid_params`(허용값 안내). 원격 호출자는 `query`에서 `mode`가 조용히 무시되고, `search`에서는 비어 있지 않은 `mode`가 `search_mode_local_only` 오류다. `gbrain config set search.mode <값>`은 모드 값을 검증하지 않고 쓴다(set 시점 검증 대상은 일부 다른 `search.*` 키뿐, `config-values.ts`) (C-02, C-03, C-22, C-23) | 실행 확인 (해석) + 코드 확인 (호출자 신뢰·오류) |
| R-03 | 번들 값 | 세 번들은 44개 노브를 모두 정하고 **8개만 다르다**: `tokenBudget` 4000 / 12000 / 없음, `searchLimit` 10 / 25 / 50, `reranker_enabled` 꺼짐 / 켜짐 / 켜짐, `reranker_top_n_in` 30 / 25 / 50, `graph_signals` 꺼짐 / 켜짐 / 켜짐, `contextual_retrieval` `none` / `title` / `per_chunk_synopsis`, `relationalRetrieval` 꺼짐 / 켜짐 / 켜짐, `relational_planner` 꺼짐 / 켜짐 / 켜짐. 나머지는 셋 다 같다: `expansion` 꺼짐, `autocut` 꺼짐, `reranker_model` `voyage:rerank-3-lite`, `reranker_top_n_out` null(절단 없음), `reranker_timeout_ms` 5000, `intentWeighting` 켜짐, `keywordOrFallback` 켜짐, `title_boost` 1.25, `collapse`·`rank_priors` 켜짐, `metadata_boost_gate` `lexical`, `cache_*`(0.92 / 3600초 / 켜짐 표시이지만 R-70), `expansion_variant_budget` null. 값 원본은 C-01 | 실행 확인 (`demo-pure` mode 4항목) + 코드 확인 |
| R-04 | 노브 우선순위 | 호출별 인자 → 설정 키(`search.<…>`, 이름은 C-03) → 번들. 설정 값 파싱: 오래된 불리언 키(`cache.enabled`, `intentWeighting`, `keywordOrFallback`, `expansion`, `reranker.enabled`, `graph_signals`, `autocut`, `relational_retrieval` 등)는 `1` 또는 `true`(대소문자 무시)만 참이고 **그 밖의 문자열(`on`·`yes` 포함)은 거짓**이다. 새 불리언 키(`relational_planner`, `relational_orient_onehop`, `collapse`, `rank_priors`)는 `true`·`1`·`on` / `false`·`0`·`off`만 인식하고 그 밖은 무시한다. 숫자 키(`searchLimit`, `tokenBudget`, `reranker.top_n_in`, `reranker.timeout_ms`, `cache.ttl_seconds`)는 양의 정수가 아니면 무시하고 번들 값으로 간다. `reranker.top_n_out`은 `''`·`null`·`none`이면 절단 없음. `reranker.model`은 trim 후 비면 무시. `reranker.timeout_ms`는 호출·설정 값이 없으면 레시피 `default_timeout_ms`, 그것도 없으면 5000(voyage 레시피는 선언 없음) (C-02, C-03) | 실행 확인 (우선순위·무효 모드) + 코드 확인 (파싱) |
| R-05 | 반환 행 수 | `search`: `limit`(생략·0이면 **20**, 모드 무관). `query`: `limit` 생략·0이면 모드의 `searchLimit`(10/25/50, 설정 `search.searchLimit`이 덮어씀)이고 이미지 분기도 같은 값을 쓴다. 원격 호출자는 모드를 못 골라 설정된 모드가 적용된다. `search`의 `offset`은 10,000 초과면 `search_offset_over_cap`. 실제 반환은 `limit` **이하**다(R-34~R-37에서 줄어듦) (C-22) | 코드 확인 |
| R-06 | arm당 후보 풀 | 각 arm이 가져오는 후보 수 = `min(max(2×limit, 50, offset+limit), 100)`(100은 `MAX_SEARCH_LIMIT`). 키워드 엔진은 그 안에서 `3×limit`를 SQL로 가져와 페이지당 최고 청크 1개로 접은 뒤 자른다. 벡터는 HNSW 후보 `offset+max(5×limit, 100)`개를 가져와 페이지당 최고 청크로 접는다(여기서 limit은 arm 풀 크기이고 hybrid는 arm에 offset을 주지 않는다). 그래서 `limit`이 100을 넘어도 결합 전 arm 풀은 100에서 멈춘다 (C-05, C-20, C-22) | 실행 확인 (풀 크기 수식) + 코드 확인 |

**B. 요청 해석·의도**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | 단계 순서 | `types`가 빈 배열이면 즉시 `[]`. 그 외 순서는 1.1이다: 요청 해석 → (키워드·제목 arm ∥ 벡터 쪽) → 관계 arm(부가) → [키워드 전용 분기 R-60] → 결합 → 재점수 → 사후 부스트 → dedup → [호출자가 명시한 `detail=low`가 0건이면 `detail=high`로 한 번 재실행] → 리랭크 → 반환 풀 정리 → 슬라이스 → 토큰 예산. 호출자 `onMeta`에는 벡터 사용 여부·확장 적용 여부·`degraded` 단계 목록이 간다 (C-06) | 코드 확인 |
| R-11 | `search`와 `query`의 차이 | `search`는 `expansion:false`를 고정 전달하고(설정 `search.expansion`도 무시), 한도 기본 20, `match:"keyword"`와 `search.mcp_keyword_only`가 있으며, 사실 행·신뢰도 등급·CRAG를 만들지 않는다. **리랭커는 끄지 않는다**(모드 번들이 켜져 있으면 `search`도 리랭크). `query`는 확장을 호출 인자·설정·번들 순으로 정하고 사실 행(R-52)·신뢰도 등급을 만든다. 둘 다 별칭 fan-out(부가)과 응답 메타를 만든다 (C-22) | 코드 확인 |
| R-12 | `detail` | 호출자가 명시한 `low`: SQL이 `compiled_truth` 청크만 보고 RRF 뒤 compiled_truth 청크 점수에 ×2.0. 자동 판정 `low`(의도 entity): SQL 필터 없이 ×1.2 기울임. `high`: 소스 가중 표를 1.0으로 우회하고 compiled_truth 부스트 없음. 생략은 `medium`(의도가 정함). 명시 `low`가 0건이면 `high`로 재실행한다. 부스트는 정규화 뒤에 곱하며, 미검증 스텁 페이지와 청크 없는 제목 행은 제외 (C-06, C-13, C-20) | 실행 확인 (×2.0, ×1.2) + 코드 확인 |
| R-13 | 의도 분류 | 질의 정규식 은행으로 `intent`(`temporal`→`event`→`concept`→`entity`→`general` 순 판정)와 `suggestedDetail`(entity→low, temporal·event→high, 나머지 없음), 추천 recency·salience(`today` 등 strong, 최근성 어휘 on, 정의형 질문은 off), 모달리티(image 어휘일 때만 image)를 정한다. 의도는 키워드·벡터 가중(R-31)과 정확 일치 가산에 쓰인다. 호출자 인자 `detail`·`recency`·`salience`가 있으면 그것이 이긴다. `search.intent_patterns`(JSON)로 은행을 추가할 수 있다(추가만 가능) (C-07, C-08) | 실행 확인 (분류 8사례) + 코드 확인 |

**C. 후보 arm**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 키워드 arm | 원 질의로 `content_chunks.search_vector @@ websearch_to_tsquery('<FTS 언어, 기본 english>', 질의)`(텍스트 청크만, `modality='text'`), 점수 `ts_rank × 소스 가중`(C-25), 페이지당 최고 청크 1개. CJK 질의는 `chunk_text` LIKE/ILIKE 용어 AND 매칭으로 바뀐다. 엄격 매칭이 0행이고 `keywordOrFallback`이 켜져 있으면(기본) OR-of-terms로 **한 번만** 재시도하고 행마다 `keyword_relaxed`를 붙인다. 질의에 따옴표나 `-용어`가 있거나 서로 다른 단어가 2개 미만이면 재시도 없음. Postgres는 후보 5만 행 상한(`KEYWORD_RANK_CANDIDATES`)에 닿으면 `degraded: keyword_candidates_incomplete`. arm 실패(시간 초과 포함)는 빈 목록 + `degraded: keyword_arm_failed`로 계속하며, 키워드·제목 둘 다 DB 접근 불가 오류면 던진다 (C-10, C-20) | 실행 확인 (OR 폴백 빌더, 질의 술어 문자열) + 코드 확인 |
| R-21 | 제목 arm | 원 질의로 `pages.search_vector`(제목 가중 A + 타임라인 앞부분 C)를 페이지 단위로 매칭, 정렬 `정확 제목 일치 우선 → 점수 → page_id`. 대표 청크는 compiled_truth 우선·가장 앞 청크이고, 청크 없는 페이지도 `chunk_id 0`·빈 텍스트 행으로 잡힌다. 원격(안전 청크) 호출자는 제목 가중 A만 매칭. 제목 후보가 있으면 키워드와 같은 k로 RRF에 참여한다. 엄격 매칭이 0행이면 키워드 arm과 같은 OR 완화를 한 번 재시도하고(제목 어휘만, `keyword_relaxed` 표지), `lang`·`symbol_kind` 필터가 있으면 제목 arm은 아예 빈 목록이다. 실패는 빈 목록 + `degraded: title_arm_failed` (C-11) | 코드 확인 |
| R-22 | 벡터 arm | `embedQuery`(ai-gateway R-23)로 질의를 임베딩(앞에 `embedding_query_prefix`, 데드라인 6초, 남은 시간이 적어도 최소 2초 보장). 후보는 `embedding IS NOT NULL`·텍스트 모달리티이고 청크의 `model`이 현재 임베딩 모델과 같으며 저장 해시(`embedded_text_hash`)가 현재 본문 해시와 같거나 NULL인 행이고(임베딩 마이그레이션 전 브레인은 예외 분기), 점수 `(1 − cosine 거리) × 소스 가중`, 페이지당 최고 청크 1개. NULL 벡터 청크는 나오지 않는다(page-storage R-21·R-22). 확장 변형마다 임베딩·벡터 arm을 따로 돌리고, 일부 임베딩이나 arm이 실패해도 살아남은 것으로 계속한다 (`degraded: expansion_partial`, `vector_arm_failed`, `rescore_skipped`). 전부 실패하면 R-61 (C-12, C-21) | 코드 확인 |
| R-23 | 소스 가중·하드 제외 | 점수에 slug 접두 가중을 곱한다(가장 긴 접두 우선, 기본 표 C-25: `originals/` 1.5, `writing/` 1.4, `concepts/` 1.3, `people/`·`companies/`·`deals/` 1.2, `meetings/` 1.1, `daily/` 0.8, `media/x/` 0.7, `openclaw/chat/`·`archive/` 0.5, `extracts/` 0.3 등). 미검증 스텁은 가중 1.0. `detail=high`면 가중 전체가 1.0. `test/`·`attachments/`·`.raw/`는 항상 제외(환경변수 `GBRAIN_SEARCH_EXCLUDE`로 추가, `include_slug_prefixes`로 빼기) (C-25) | 실행 확인 (표·병합·`none`·제외 목록) |
| R-24 | 쿼리 확장 | **기본 꺼짐**. `query`에서 호출 `expand=true`이거나 설정 `search.expansion`이 참이면 켜진다(모든 번들이 거짓, `expand=false`가 최우선). `search`·메모리 verbs는 고정 꺼짐. 이미지 모달리티 질의는 건너뜀. 확장 함수 `expandQuery`: 단어 수(CJK 인지)가 3 미만이면 호출 없이 `[query]`; 확장 provider를 쓸 수 없으면(ai-gateway R-40, 키 없음) 호출 없이 `[query]`; 성공이면 `[원 질의, 변형…]` 소문자·trim 기준 중복 제거 후 **최대 3개**(변형 ≤2), 질의는 500자·코드 펜스·태그·`ignore:`류 접두를 제거해 모델에 보내고 출력은 제어문자 제거·500자 절단. 어떤 오류든 `[query]`. 변형은 **벡터 arm에만** 쓰이고 키워드·제목 arm은 원 질의만 쓴다. 변형 RRF 가중은 `expansion_variant_budget`(번들 null이면 원 질의와 같은 가중 1, 숫자 b면 비어 있지 않은 변형 목록마다 `b/개수`). `expandFn`이 던지면 원 질의만 쓰고 `degraded: expansion_failed` (C-09, C-13, C-14, C-20) | 실행 확인 (expandQuery 5사례, compose 가중) + 코드 확인 |

**D. 결합·재점수·정리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | RRF | 목록 i의 행 순위 r(0부터)의 표는 `weight_i / (k_i + r)`. **페이지 단위 투표**: 한 목록이 같은 페이지를 여러 번 내도 그 목록의 최고 순위 한 번만 센다. 페이지 합계 점수는 그 페이지의 lead 청크(자기 표가 가장 큰 청크, 동률은 먼저 본 목록=벡터 쪽)가 갖고 같은 페이지의 다른 청크는 자기 표만 갖는다. 전체를 최댓값으로 나눠 0~1로 정규화하고, compiled_truth 부스트(R-12)를 곱한 뒤 `점수 → 자기 표` 내림차순 정렬. 키 `(source_id, slug, chunk_id)` (C-13) | 실행 확인 (`demo-pure` RRF 7항목) |
| R-31 | k·가중 | 기본 `RRF_K=60`. 의도 가중(C-08: entity 키워드 1.15, event 키워드 1.20·벡터 0.95, concept 키워드 0.9·벡터 1.2, 그 외 1.0)이 `k = 60/가중`으로 들어가 키워드·제목 목록과 벡터 목록의 k가 갈린다. 목록 순서·k: 벡터 arm들(원 질의 → 변형), 키워드(`keywordK`), 제목(`keywordK`, 비면 생략), 관계(`60`, 부가). 텍스트 벡터 arm에 비지 않은 목록이 있으면 `keyword_relaxed` 행은 결합 전에 버려지고(`relaxed_dropped` 메타), 없으면 그대로 투표한다. `metadata_boost_gate=lexical`(전 번들): 키워드·제목·관계 목록에 행이 하나도 없으면(벡터만 투표) R-33의 메타데이터 부스트를 건너뛴다 (C-08, C-13, C-14) | 실행 확인 (k 값, compose) + 코드 확인 |
| R-32 | 코사인 재점수 | 질의 임베딩이 있으면 결합 결과 각 청크의 임베딩 cosine을 DB에서 계산(실패하면 JS 폴백, 둘 다 실패하면 입력 그대로)해 `score = 0.7 × (score/최대) + 0.3 × cosine`로 바꾸고 `cosine`을 기록·내림차순 정렬한다. 임베딩을 못 읽은 행은 cosine 0으로 계산해 같은 척도에 놓는다. 읽은 행이 하나도 없으면 입력 그대로. 원 질의 임베딩이 실패한 경우(변형만 살아남음)는 건너뜀 (C-15) | 실행 확인 (0.85/0.62/0.175, 폴백 3분기) |
| R-33 | 사후 부스트(곱셈, 순서대로) | 이 순서로 `score`에 곱한다. ① 백링크 `1+0.05·ln(1+수)` ② salience(켜졌을 때 `1+k·ln(1+점수)`, on 0.15 / strong 0.30) ③ recency(접두별 반감기 표 C-27, `1+계수·반감기/(반감기+일수)`, strong은 계수 ×1.5)와 event·diary 타입 가산(on 1.15 / strong 1.25) ④ 제목 구문 가산 ×1.25(질의가 제목 전체이거나, 내용어가 2개 이상인 질의가 제목 안의 연속 토큰 구간일 때) ⑤ graph signals(부가) ⑥ alias-resolved ×1.05 ⑦ 대체된 페이지(supersedes 링크 대상) ×0.5와 `superseded` 표지. 그 뒤 의도별 정확 일치 가산(slug·제목이 질의와 같거나 질의 안에 언급되면 ×1.25(entity)/×1.10(event), general·temporal에서 멀티토큰 제목이 질의 주제면 ×1.18)을 곱하고 재정렬한다. 의도·질의에 따라 salience·recency는 꺼져 있다(R-13). 읽기 실패한 단계는 건너뛴다 (C-16, C-27) | 코드 확인 (식·상수) |
| R-34 | dedup | 순서: ① 페이지(소스+slug)당 점수 상위 3청크 ② 같은 페이지 안에서 단어 집합 Jaccard > 0.85인 청크 제거(다른 페이지의 비슷한 청크는 유지) ③ 결과에 타입이 2종 이상일 때만 한 타입이 `ceil(0.6×개수)`를 못 넘게 ④ 페이지당 최대 2청크 ⑤ 위 결과에 compiled_truth 청크가 없는 페이지에는 사전 후보 중 최고 compiled_truth 청크를 **덧붙임**(2청크 상한을 넘을 수 있음) → 점수 내림차순. 같은 slug라도 소스가 다르면 다른 페이지 (C-17) | 실행 확인 (dedup 5사례) |
| R-35 | 리랭크 | 번들이 켜져 있으면(또는 호출 `reranker` 인자가 켜면) dedup 결과의 **상위 `topNIn`개**(30/25/50)의 `chunk_text`(없으면 제목, 최대 약 1400토큰/6000자로 절단)를 `질의`와 함께 ai-gateway `rerank`(ai-gateway R-50~R-52, 타임아웃 5000ms)에 보낸다. 공급자가 준 `{index, relevanceScore}` 순서로 머리를 재배열하고(정확히 같은 점수는 입력 순서 유지) `rerank_score`·`reranker_delta`를 찍고, `topNIn` 밖 꼬리는 원래 순서로 뒤에 붙이며, 공급자가 빠뜨린 머리 항목은 머리 끝에 원래 순서로 붙인다. `topNOut`(null)이 양수면 그 길이로 자른다. 전체 호출 실패는 모두 **입력 그대로 반환**한다: 키 없음(`no_key`)은 감사 기록 없이 `degraded: reranker_skipped`, 시간 초과·권한·한도·네트워크·예산 소진·기타 오류는 감사 JSONL + `degraded: rerank_failed`(이유 `timeout\|auth\|rate_limited\|unreachable\|budget\|provider_error`), 200 응답이지만 빈 배열·비배열이면 `degraded: rerank_passthrough`. 던지지 않는다. 호출 뒤 순서 점수에 rank prior·피드백(부가)이 곱해질 수 있다 (C-18, C-19) | 실행 확인 (재정렬·동률·절단·실패 5계열·통과 2종·미호출 3분기) |
| R-36 | 절단 | 반환 풀을 `slice(offset, offset+limit)`로 자른다(점수 컷 없음). 기본 번들은 autocut·적응 반환이 꺼져 있다(켜면 리랭크 점수 낙차에서 자르되 최소 1개 유지). 식별·관계 주입 단계(부가)가 끼운 행은 이 풀에 이미 들어 있다 (C-18) | 코드 확인 |
| R-37 | 토큰 예산 | 모드의 `tokenBudget`(4000/12000/없음, 호출 `token_budget`이 `query`에서 청크 모드일 때 덮어씀)이 있으면 순서대로 행을 담는다. 행 비용 = 제목과 청크 텍스트 각각의 `ceil(비CJK 글자/4) + CJK 글자 수`의 합(관계 간선 비용 포함). 담을 수 없는 행은 **건너뛰고** 다음 행으로 계속하며(머리가 들어간 뒤), 첫 행 하나가 예산보다 크면 그 행을 **복사해 제목·본문을 잘라** 1행만 반환한다(`budget_truncated`, 원본 불변). 예산이 없거나 0 이하면 무동작. 메모리 verbs의 `packToBudget`은 첫 초과에서 멈춘다 (C-19) | 실행 확인 (budget 5항목) |

**E. 반환 형태·한도**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | 청크 글자 상한 | 호출 `snippet_chars`(0=무제한)가 이긴다. 없으면 서브에이전트 호출자는 `agent.search_snippet_chars`(기본 300), 그 외는 **8000자**(`RESULT_CHUNK_CHARS`)로 `chunk_text`를 자르고 `… [truncated N chars — get_page <slug> …]` 표지를 붙인다. 복사본을 자르므로 캐시·평가 기록은 원본을 본다 (C-26) | 실행 확인 (우선순위, 표지) |
| R-51 | 증거 전달 | `return_unit` 기본은 `auto`(설정 `search.return_unit`이 있으면 그 값): 히트 중에 대화형 페이지(타입 `conversation`·`transcript`·`chat`·`meeting`·`slack*`·`imessage*`, slug `chat/`·`conversations/`)가 **있을 때만** 청크 대신 페이지 단위 증거(기본 예산 24000토큰, 원격 최대 32000)로 바뀌고, 없으면 청크 경로 그대로다(`search.long_page_unit`이 켜진 브레인만 긴 비대화 페이지도 확장). `return_unit:"chunk"`거나 `query`의 `token_budget`이 숫자이면 청크 경로. 전달 규칙 본문은 부가 단계 (C-31) | 코드 확인 (기본 판정) / 부가 (본문) |
| R-52 | 사실 행(`query`만) | `search.query_facts_arm`이 꺼지지 않았고(기본 켜짐) `offset`·`types`·`where`·`since`·`until`·`lang`·`symbol_kind`·`near_symbol`이 모두 없을 때, 질의와 맞는 **활성 사실**(`expired_at` 없음, 소스 범위·원격은 `world` 가시성)을 **최대 3개**를 `limit`의 남는 칸과 토큰 예산의 남는 몫에만 행으로 덧붙인다(페이지 행을 밀어내지 않음). 사실 매칭 = 엔티티 페이지 지목 또는 질의 임베딩 cosine ≥ 0.6 또는 내용어의 절반 이상 일치(최소 2개, 내용어가 1개면 1개), 최신 `valid_from` 순. 사실 행 점수는 페이지 행 최저 점수 바로 아래. 오류·후보 없음이면 결과 무변화 (C-29) | 코드 확인 |
| R-53 | 응답 필드 투영 | 원격 호출자의 기본은 lean(`fields:"lean"`): `slug`, `title`, `type`, `chunk_text`, `score`(유효숫자 4자리), `effective_date(_source)`, `source_id`, `chunk_id`, `evidence`, `create_safety`, 안전·출처 표지(`unverified`, `content_flag`, `status`, `superseded*`, `trust_tier`, `origin` 등)만 남기고 `page_id`, `chunk_index`, `chunk_source`, `cosine`, `base_score`, `*_boost`, `rerank_score`는 뺀다. 로컬 신뢰 호출자는 항상 full. 반환 직전 `score`를 반환 순서에 맞춘다: 리랭크된 목록이면 리랭크 점수(× rank prior)를 `score`로, 점수 없는 주입 행은 이웃 값을 받고 누적 최솟값으로 비증가를 보장하며 원래 값은 `fused_score`에 남긴다. 모든 텍스트 필드는 비밀 패턴 마스킹을 거친다(필드당 64 KiB·응답 1 MiB 초과분은 `<REDACTED:output_limit>`) (C-26) | 실행 확인 (lean, score 계약) + 코드 확인 (마스킹) |

**F. 실패·키 없음**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 임베딩을 쓸 수 없음: `isAvailable('embedding')`가 거짓(ai-gateway R-05 임베딩 모델 미설정·R-26 필수 키 없음 포함) 또는 브레인이 임베딩을 끔(`embedding_disabled`) | `hybridSearch`가 질의 임베딩을 시도하지 않는다(질의 텍스트가 공급자로 나가지 않음). 키워드(+제목+관계) arm만 사용한다: 제목·관계 목록이 있으면 k=60으로 RRF, 없으면 키워드 목록 그대로 → 사후 부스트 → dedup → (부가) → 슬라이스 → 토큰 예산. **리랭크와 코사인 재점수는 일어나지 않는다.** 메타 `vector_enabled:false`, `degraded: embed_unavailable`(이유 `no_provider` 또는 `embedding_disabled`), 키워드가 0건이면 `keyword_zero`. 호출은 성공한다 | 코드 확인 |
| R-61 | 임베딩은 가능하나 이번 호출의 모든 질의 임베딩 또는 벡터 arm이 **실패**(성공했지만 빈 결과인 목록은 해당 없음: 그 경우 정상 경로로 가고 완화 키워드 행이 그대로 투표한다) | R-60과 같은 키워드 폴백 경로(`searchVectorFallback`), 리랭크·코사인 재점수 없음. 실패 이유는 `embed_timeout`(데드라인 포함 시간 초과) 또는 `embed_unavailable`(공급자 오류)로 stderr에 한 번 경고. 변형만 일부 실패하면 R-22의 구제 | 코드 확인 |
| R-62 | 리랭커 키·공급자 문제 | R-35의 fail-open. 임베딩 키는 있고 리랭커 키만 없는 설치는 벡터 arm은 돌고 리랭크만 `reranker_skipped`로 빠진다. 기본 리랭커가 `voyage:rerank-3-lite`라 필요한 키는 Voyage 키(ai-gateway R-51) | 코드 확인 |
| R-63 | 확장 실패 | R-24: 어떤 실패도 원 질의로 계속한다. `BudgetExhausted`는 확장을 막지 못한다(ai-gateway R-61) | 코드 확인 |
| R-64 | 보조 단계 실패 | 사후 부스트의 읽기, 코사인 재점수, 사실 행, 키워드 총수 계산(`keyword_count_unavailable`)의 실패는 그 단계만 건너뛰고 결과는 반환한다. DB 접근 불가(키워드·제목 둘 다)만 던져진다(R-20). 질의 임베딩 `AIConfigError`(차원 불일치 등)는 벡터 arm 실패로 흡수되어 R-61로 간다 | 코드 확인 |
| R-65 | `search`에서 `search.mcp_keyword_only`가 `'true'`이거나 `match:"keyword"` | `hybridSearch`를 거치지 않는다. 원 질의로 `searchKeyword`(엄격 FTS, OR 폴백 없음, 소스 가중 적용)를 `limit`·`offset`로 직접 부르고 `dedupResults`만 적용한다. 제목 arm·RRF·리랭크·모드 토큰 예산 없음. `match:"keyword"`는 페이지 단위로 열거하며 `total`·`truncated`·`next`(키셋 커서)를 준다 | 코드 확인 |

**G. 소스 격리·가시성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 소스 범위 결정(`sourceScopeOpts`) | 우선순위: **연합 배열**(`ctx.auth.allowedSources`가 비어 있지 않음) > **단일 소스**(`ctx.sourceId`) > **없음**(전체). 빈 배열 `allowedSources: []`는 "필터 없음"으로 해석되지 않는다: 단일 소스가 있으면 그것을, 없고 호출자가 원격이면 `permission_denied`("No readable source is granted")를 던진다. 신뢰된 로컬 호출자에서 빈 배열 + 단일 소스 없음은 `{}`(전체). `ctx.sourceId === '__none__'`이면 `no_source_grant` 오류. `'__all__'`: 로컬 신뢰 호출자는 `{}`(전체), 원격은 리터럴로 남아 어떤 실제 소스와도 일치하지 않아 빈 결과. 호출 `source_id`는 `resolveRequestedScope`가 처리한다: 원격이 자기 권한 밖 id를 주면 `permission_denied`, 아니면 `{sourceId}`. 검색 op는 호출 `source_id`가 없거나 `__all__`이고 연합 grant가 없으며 결과가 단일 소스일 때, 전송 계층이 계산한 연합 집합(`localFederatedSourceIds`, 원소 2개 이상)이 있으면 그 집합으로 넓힌다. 호출 `source_id`가 가리키는 소스가 없으면(보관됨 포함) 오류. 원격이면서 `auth`도 `sourceId`도 없는 컨텍스트는 `{}`를 낸다(이 경우 실제 서버가 `auth`를 채우는지는 미확인) (C-23) | 실행 확인 (`sourceScopeOpts` 10사례) + 코드 확인 |
| R-41 | 범위가 SQL에 닿는 모양 | 모든 arm이 `source_id = ANY(sourceIds)`(배열이 비어 있지 않을 때) → 아니면 `source_id = sourceId` → 아니면 조건 없음 순으로 같은 규칙을 쓴다. 따라서 **엔진 층에 빈 배열이 직접 들어오면 필터 없음(전체)이 되므로** 안전은 R-40의 사다리가 빈 배열을 만들지 않는 데 있다(`allowedSources`가 비면 그 배열을 쓰지 않음). 배열과 단일이 함께 있으면 배열이 이긴다. 키워드·제목·벡터 어느 것도 `min_trust`·`where`·`types` 등 다른 필터와 AND로 결합한다 (C-10, C-11, C-12) | 실행 확인 (where 절 모양 5사례) |
| R-42 | 삭제·격리·보관·기타 제외 | 키워드·제목·벡터 arm(과 `search_exact`)은 모두 같은 가시성 절을 쓴다: `deleted_at IS NULL`(소프트 삭제 제외), 현재 텍스트 투영(`text_projection_revision = knowledge_revision`, 청크 질의는 본문 세대 조건 추가), 소스가 보관(archived)되지 않음, frontmatter에 `quarantine` 키가 없음(격리 페이지, 청크가 원래 0개라 이중 방어), `pinned_question` 키가 없음. 요청에 따라 추가: 원격이면 `visibility: private`(및 파생 원자·질문 페이지 등) 제외(설정 `search.remote_private_pages`가 `visible\|true\|1`이거나 `GBRAIN_REMOTE_PRIVATE_PAGES=1`이면 노출), 원격이면 `chunker_version ≥ 4`인 안전 청크만, `min_trust`·`suppressFlagged`가 있으면 신뢰 등급 필터. `content_flag`(의심 콘텐츠)는 제외하지 않고 행에 표지만 붙는다 (C-24) | 실행 확인 (절 문자열) + 코드 확인 |

**H. 의미 캐시**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-70 | `hybridSearchCached`의 캐시 | **현재 기준 SHA에서 의미 결과 캐시는 하드 비활성**이다: `semanticResultCacheAvailable()`이 항상 `false`라 조회·저장·무효화가 모두 실행되지 않고(`cache_stats` 응답도 `enabled:false`), `query_cache` 테이블은 읽히지 않는다. 번들의 `cache_*` 값은 존재하지만 효과가 없다. 래퍼는 모드 해석과 토큰 예산(호출 인자일 때)만 한다 (C-28) | 실행 확인 (`semanticResultCacheAvailable() === false`) + 코드 확인 |
| R-71 | (비활성 상태의) 캐시 계약 | 켜져 있다면: 키 = `sha256("<scope>::<질의>::<knobsHash>")` 앞 32자(`scope` = 연합 `__set__:<정렬된 id>` / 단일 id / 없음 `__unscoped__`), `knobsHash`는 번들·덮어쓰기·정규화한 호출 인자(모드, 한도, 리랭크, 예산 등)의 해시(`KNOBS_HASH_VERSION` 31)라 모드가 다르면 다른 행. 조회: 같은 scope·knobs 행 중 질의 임베딩 코사인 유사도 ≥ **0.92**(설정 `search.cache.similarity_threshold`, 범위 0.5~0.999로 보정)이고 `생성+TTL > now`(기본 **3600초**, `search.cache.ttl_seconds`, 상한 30일)이며 무효화 게이트를 통과하는 후보 5개 중 저장 질의 텍스트가 문자 이분(bigram) Dice ≥ 0.5(또는 정규화 동일)인 가장 가까운 행. 무효화 게이트: 1층 `page_generation_clock_seq.last_value <= 저장 시점 값`(그 뒤 pages에 쓰기가 없음)이면 통과, 아니면 2층으로 저장된 `(page_id → generation)` 스냅샷이 비어 있지 않고 모든 페이지가 삭제되지 않았으며 세대가 그대로여야 통과. 저장: 결과가 0건이거나 벡터가 쓰이지 않았거나 질의 임베딩이 없으면 안 저장하고, 저하(degraded) 실행은 TTL 60초. 오류는 모두 미스로 삼킴 (C-28) | 실행 확인 (id·가드·scope 키) + 코드 확인 (SQL·게이트) |

**I. `search_exact`·이미지·경계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-80 | `search_exact` | 구의 단어를 순서대로, 단어 사이 임의 공백(줄바꿈 포함)을 허용해 청크 `chunk_text`에서 리터럴(형태소·구두점 변형 없음) 매칭하고 대소문자는 `case_sensitive`가 아니면 무시한다. 순위 없이 `page_id` 순으로 **매칭 페이지당** `matching_chunks`와 최대 3개 스니펫(앞뒤 80자)을 돌려준다. 범위·가시성은 ranked 검색과 같다(R-40~R-42, 하드 제외 접두 포함, 원격은 안전 청크만). 완전성: 범위 안 페이지를 모두 읽고 읽지 못한 페이지가 없을 때만 `complete:true`. 아니면 `incomplete_reasons`에 `deadline`·`limit`(둘 다 `resume_after`로 이어서 호출) 또는 `unreadable_pages`(청크 없음 `unchunked`, 투영 지연 `projection_pending`, 원격 미봉인 `unsealed`, 한 페이지가 시간 초과 `scan_timeout`)를 담고 해당 페이지를 `unreadable`에 열거한다. 입력 검증 실패는 `invalid_params` (C-30) | 실행 확인 (구 패턴, 스캔 4분기, 필터 문자열) |
| R-81 | 이미지 질의 | `query`의 `image` 분기: 이미지를 멀티모달 임베딩해 `embedding_image` 컬럼 벡터 검색만 한다(키워드·RRF·리랭크 없음). 한도는 R-05, 소스 범위·`types`·`where`·날짜·비공개 규칙은 텍스트 경로와 같다. 임베딩이 꺼진 브레인은 공급자 호출 전에 거부. `search_by_image`(`searchByImage`): 이미지 1벡터를 `embedding_image`에서 `min(2×limit,100)`개 가져와 dedup 후 `limit`(기본 20), 텍스트 `query`를 함께 주면 텍스트 벡터도 같은 컬럼에서 가져와 가중 RRF(이미지 0.6 / 텍스트 0.4, 모드 노브)로 합친 뒤 dedup. 원격 호출자는 `image_path` 거부, 일일 이미지 예산 예약 후 호출. 입력 이미지 로더(SSRF 방어, 크기 상한)는 경계만 (C-31) | 코드 확인 |
| R-90 | 메모리 verbs·`think` 경계 | `recall`의 페이지 검색 팔은 `hybridSearchCached`를 `expansion:false`, 호출자 `limit`, 소스·비공개 규칙 그대로 불러 같은 파이프라인을 쓴다(키·임베딩이 없으면 `searchKeyword` 직접 호출로 대체하고 리랭크 없음, 계획된 관계 체인 질문만 예외). `think`의 수집은 `hybridSearch`(캐시 래퍼 없음)를 `expansion:false`·넓은 한도로 부른다. 둘 다 이 스펙의 코어를 소비할 뿐 자기 결과 가공(사실·이유·합성)은 각자 스펙이다 | 코드 확인 |

- 불변식: (1) 반환 행은 호출자의 소스 범위·삭제·격리·보관 규칙(R-40~R-42)을 넘지 않는다(엔진 층 빈 `sourceIds` 입력은 예외, R-41). (2) 키가 없거나 공급자가 실패해도 검색은 던지지 않고 키워드 결과(필요하면 빈 목록)를 degraded 표지와 함께 돌려준다(R-35, R-60~R-64). 예외는 DB 접근 불가와 `invalid_params`·`permission_denied` 같은 호출 오류. (3) 한 페이지의 반환 청크는 기본 2개(+compiled_truth 덧붙임 1개) 이하다(R-34). (4) 기본 설정에서 결과는 `limit`·토큰 예산·dedup으로만 줄고 점수로는 안 잘린다(R-36).
- 미결정: 없음. (부가 단계와 CJK 키워드 SQL은 1.2에서 범위 밖으로 선언했고 미결정이 아니다.)
- 확인 한계:
  - `bun`이 없고 DB·공급자를 호출하지 않았다. 실행 확인은 `deno`로 순수 함수만 돌린 것이다(`agent-memory/artifacts/gbrain/search-demos/`): 실제 모듈을 import한 것(RRF 누적, 가중 목록 구성, 의도 가중, dedup, 토큰 예산, 코사인 재점수(가짜 엔진), 질의 의도 분류, 소스 가중, SQL 절 빌더, 스니펫·lean 행·점수 계약, 의미 캐시의 id·가드, `search_exact` 스캔(가짜 엔진))과 줄 범위를 잘라 실행한 것(`rrfFusionWeighted`·`cacheScopeKey`, 모드 번들·`resolveSearchMode`, `applyReranker`(가짜 공급자), `expandQuery`(가짜 gateway), `sourceScopeOpts`)을 구분했고 대체물은 스크립트 머리말에 있다. 토큰 추정은 rerank 절단 데모에서 `len/4` 대체다.
  - SQL 문장을 PGLite·Postgres에서 실제로 돌리지 않았다. 키워드 SQL은 두 엔진을 모두 읽었고 같은 구조(3×limit, 페이지 최고 청크, OR 폴백)이다. HNSW 반복 스캔·후보 확대·인덱스 워크 같은 벡터 후보 수집 전략(`vector-statement.ts`의 `scopeScan`, `indexWalk`)은 결과 집합 정의가 아니라 후보 수집 최적화로 보고 읽지 않았다.
  - 외부 공급자(Voyage rerank, 임베딩, 확장 모델)의 실제 응답은 확인하지 못했다. 계약은 ai-gateway 스펙이 정한다.
  - 부가 단계 본문(별칭 fan-out, 별칭 hop·정확 조회, collapse, rank priors, 관계 arm, graph signals, 피드백, CRAG, 증거 전달, System One)은 읽지 않았다. 각 단계의 기본 켜짐 여부와 한 줄 효과는 파일 머리 주석과 호출 지점으로 확인했다.

### 1.5 필수 코드 참조

라이선스: MIT(overview 1절). 인용 가능. 줄 번호는 기준 SHA.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/search/mode.ts:80-86, 480-689` `SEARCH_MODES`, `MODE_BUNDLES`, `DEFAULT_SEARCH_MODE`; 값 상수 `ai/defaults.ts:19` `DEFAULT_RERANKER_MODEL`, `search/crag.ts:291,294` `DEFAULT_RERANK_GATE`·`DEFAULT_RERANK_GATE_MIN_GAP`, `search/relational-rerank-pin.ts:75` `DEFAULT_RELATIONAL_RERANK_PIN` | 세 번들의 노브 44개 값 전부(표로 풀지 않고 코드로 가져감). 값 상수는 `'voyage:rerank-3-lite'`, `'off'`, 0.05, 3 | R-03 |
| C-02 | `src/core/search/mode.ts:866-944` `resolveSearchMode` | 모드 문자열 정규화, 호출→설정→번들 우선순위, 무효 모드는 balanced, `reranker_timeout_ms`의 레시피 기본값 끼움(`mode.ts:72-78`은 레시피에 선언이 있을 때만 값을 줌) | R-02, R-04 |
| C-03 | `src/core/search/mode.ts:1316-1566, 1576-1633, 1657-1704` `loadOverridesFromConfig`, `KNOB_CONFIG_KEY`, `SEARCH_MODE_KEY`, `loadSearchModeConfig`, `parseBoolKnob` | 노브 이름↔설정 키 표, 값 파싱 규칙, 설정 한 번 읽기(스냅샷). 이 범위 안의 `normalizeExpansionVariantBudget`는 C-13, 그 외 정규화 함수(autocut·관계·키워드 신뢰·게이트)는 부가 단계 노브 | R-04 |
| C-04 | `src/core/search/hybrid/request.ts:105-337` `resolveHybridRequest` | 요청 해석(모드 해석 입력, 의도→가중·detail, `limit`, `innerLimit`, `searchOpts` 필터 전달 목록, 소스·가시성 옵션 전달) | R-05, R-06, R-12, R-13, R-41 |
| C-05 | `src/core/search/eval-pool-depth.ts:28-37` `searchLimitCap`, `perArmPoolLimit`; `src/core/engine.ts:802-810` `MAX_SEARCH_LIMIT`, `clampSearchLimit`; `src/core/search/hybrid.ts:57-67` `RRF_K`, `PRE_FUSION_POOL_FLOOR` | arm 풀 크기 수식, 엔진의 limit 보정(0·NaN·음수는 기본값, 상한 100) | R-06 |
| C-06 | `src/core/search/hybrid.ts:1070-1171, 1195-1356` `hybridSearch`, `hybridSearchCached`; `hybrid/degraded.ts:1-41` | 단계 호출 순서, 키워드 전용 분기 조건, `detail=low` 재실행, 래퍼의 캐시 건너뛰기·예산·메타 합성(부가 단계 본문 제외) | R-10, R-12, R-60, R-70 |
| C-07 | `src/core/search/query-intent.ts:83-293, 481-555, 589-617, 642-737` 의도·최근성·salience·모달리티·개념 정규식 은행, `matches`, `matchesBank`, `classifyQuery`, `classifyQueryIntent`, `intentToDetail`, `isConceptShapedQuery` | 의도·detail·recency·salience·모달리티 정규식 은행과 판정 순서 | R-13 |
| C-08 | `src/core/search/intent-weights.ts:48-125, 127-245` 의도 가중 표, `effectiveRrfK`, `applyExactMatchBoost`, `applyTitleMentionBoost`, `applyAliasMentionBoost`; `title-match.ts` 전체 | 의도별 키워드·벡터 가중, `k=기준/가중`, 정확 일치·제목 언급·별칭 언급 가산 | R-13, R-31, R-33 |
| C-09 | `src/core/search/hybrid/arms.ts:204-262` `resolveModalityAndQueries`; `src/core/search/expansion.ts:16-85` | 확장 조건, 질의 목록 불변식(첫 원소는 원 질의, 중복 제거), 확장 질의·출력 sanitize, 최대 3개 | R-24 |
| C-10 | `src/core/search/hybrid/arms.ts:47-126` `runLexicalArms`; `src/core/pglite-engine.ts:1403-1543` / `src/core/postgres-engine.ts:1010-1210` `searchKeyword`; `src/core/search/keyword-statement.ts:43-85` `buildKeywordMatch`; `src/core/search/sql-ranking.ts:280-296, 337-390` `collapseWebsearchDashRuns`, `buildOrFallbackWebsearchQuery`, `orFallbackTokens` | 키워드 arm 질의·점수·페이지 최고 청크·후보 3×limit·OR 폴백·fail-open | R-20, R-41 |
| C-11 | `src/core/search/title-statement.ts:56-150` `buildSearchTitlesStatement`; `src/core/engine-sql/titles.ts:70-100` | 제목 arm SQL(정확 제목 우선, 대표 청크, 원격 가중 A) | R-21 |
| C-12 | `src/core/search/vector-statement.ts:291-507` `buildVectorSearchStatement` | 벡터 후보 조건(임베딩 NOT NULL·모달리티·모델 일치·가시성), cosine 점수, 페이지 최고 청크, `innerLimit` | R-22 |
| C-13 | `src/core/search/fusion-lists.ts:93-146, 169-225` `composeFusionLists`, `normalizeExpansionVariantBudget`; `src/core/search/rrf-page-fusion.ts:18-132` `accumulateRrf`; `src/core/search/hybrid.ts:57-58, 101-132, 1449-1485` `RRF_K`, `COMPILED_TRUTH_BOOST`, `compiledTruthFusionBoost`, `compiledTruthBoost`, `rrfFusionWeighted` | RRF 알고리즘, 페이지 투표·lead 청크, 정규화·부스트·정렬, 목록 역할별 k·가중 | R-12, R-24, R-30, R-31 |
| C-14 | `src/core/search/hybrid/rank.ts:38-192` `fuseArms` | 완화 행 제거 조건, 목록 구성, 재점수·부스트 호출 순서, 메타데이터 게이트 | R-31, R-32, R-33 |
| C-15 | `src/core/search/cosine-rescore.ts:37-117` | 재점수 식 `0.7·정규화RRF+0.3·cosine`, 폴백 3분기 | R-32 |
| C-16 | `src/core/search/hybrid.ts:247-458, 539-696, 770-832`; `hybrid/alias-resolved.ts:15-55`; `metadata-boost-gate.ts:100-166`; `title-match.ts` 전체(`isTitlePhraseMatch`) | 백링크·salience·recency·chronicle·제목·alias-resolved·supersede 식과 순서, 메타데이터 게이트 | R-31, R-33 |
| C-17 | `src/core/search/dedup.ts:32-307` | dedup 4+1 계층과 상수(상위 3, Jaccard 0.85, 타입 0.6, 페이지당 2, compiled_truth 덧붙임, 분할 페이지 클러스터 6) | R-34 |
| C-18 | `src/core/search/hybrid/rank.ts:283-364, 367-488, 491-542` `rerankAndPin`, `sizeReturnPool`, `finalizeHybridResults`; `src/core/search/rerank.ts:90-110, 123-271` `capRerankDoc`, `applyReranker` | 리랭크 입력·출력·fail-open·재정렬 규칙, autocut 위치, 슬라이스, 예산 호출 | R-35, R-36, R-37 |
| C-19 | `src/core/search/token-budget.ts:44-48, 77-82, 109-111, 128-227` | 토큰 추정, 행 비용, 예산 담기·건너뛰기·첫 행 절단 failsafe, `GBRAIN_SEARCH_SALVAGE` | R-37 |
| C-20 | `src/core/search/hybrid/keyword-only.ts:25-235` `searchWithoutEmbeddings`, `searchVectorFallback` | 키워드 전용 두 경로의 처리 순서와 degraded 표지 | R-60, R-61 |
| C-21 | `src/core/search/hybrid.ts:995-1067` `embedQueryBounded`; `src/core/search/hybrid/arms.ts:315-565` `runVectorArms`; `src/core/search/query-prefix.ts:13-24` | 질의 임베딩 데드라인(6초·최소 2초), 변형별 임베딩, 살아남기(allSettled), 실패 이유 코드 | R-22, R-61 |
| C-22 | `src/core/ops/search.ts:90-95, 689-840, 842-1249` `resolveEffectiveLimit`, `search`, `query` 핸들러; `src/core/search/keyword-paging.ts:34, 74-105` `SEARCH_OFFSET_CAP`, `parseSearchPaging` | op 입구 순서, `search`와 `query` 한도·확장·모드 규칙, 호출 인자 전달 목록 | R-02, R-05, R-11 |
| C-23 | `src/core/ops/context.ts:649-672, 812-842, 976-992, 1218-1226` `sourceScopeOpts`, `resolveRequestedScope`, `federatedSearchScope`, `resolvePerCallMode`; `src/core/source-id.ts:45,54` | 소스 범위 사다리, 빈 배열·센티널 처리, 호출 `source_id` 검증, 호출별 모드 신뢰 | R-02, R-40 |
| C-24 | `src/core/search/sql-ranking.ts:176-218` `buildVisibilityClause`; `src/core/search/read-policy-sql.ts:7-35` `hasReadPolicy`, `pageReadFilter`; `src/core/quarantine.ts:50-52`; `src/core/search/safe-chunks.ts:39-46, 103-106`; `src/core/search/private-visibility.ts:319-340` | 삭제·격리·보관·투영·비공개·안전 청크 절 | R-42 |
| C-25 | `src/core/search/source-boost.ts:18-144`; `src/core/search/sql-ranking.ts:67-136` `buildSourceFactorCase`, `buildHardExcludeClause` | 접두 가중 기본 표·병합, 하드 제외 접두 | R-23 |
| C-26 | `src/core/types.ts:843-1157` `SearchResult`; `src/core/search/snippet-cap.ts:30-90`; `src/core/search/lean-rows.ts:40-90`; `src/core/search/score-contract.ts:20-60`; `src/core/ops/search.ts:120-149` `searchOutput`; `src/core/search/output-redaction.ts:1-12` | 행 필드, 청크 글자 상한과 표지, lean 필드 목록, 점수 순서 계약, 출력 단계 순서, 마스킹 상한 | R-50, R-53 |
| C-27 | `src/core/search/recency-decay.ts:39-82` | recency 반감기·계수 기본 표와 폴백(90일, 0.3) | R-33 |
| C-28 | `src/core/search/query-cache.ts:35, 80-170, 208-350, 455-513` `semanticResultCacheAvailable`, `cacheRowId`, `cacheTextGuard`, `lookup`, `store`, `loadCacheConfig`; `src/core/search/query-cache-gate.ts:163-188` `CACHE_GATE_WHERE_CLAUSE`; `src/core/search/hybrid.ts:1202-1210, 1252-1255, 1320-1353, 1364, 1402-1407` | 캐시 비활성 스위치, 키·유사도·TTL·텍스트 가드·무효화 게이트·저장 조건 | R-70, R-71 |
| C-29 | `src/core/search/query-arms.ts:17-33`; `src/core/search/facts-arm.ts:33-35, 70-86, 153-170, 235-242` | 사실 행 조건·최대 3행·여유 칸에만 추가·점수 위치·기본 켜짐 | R-52 |
| C-30 | `src/core/ops/search-exact.ts:15-109`; `src/core/search/exact-scan.ts:43-231` | 입력 검증, 구 패턴, 가시성·범위, 스캔 루프와 완전성·재개 계약 | R-80 |
| C-31 | `src/core/search/evidence-delivery.ts:48-64, 226-290, 312-328` `resolveEvidencePlan`, `conversationSignal`, `effectivePlan`; `src/core/search/by-image.ts:49-134` `searchByImage`; `src/core/ops/image.ts:19-150` | 증거 전달 기본 판정, 이미지 질의 라우팅·가중 RRF | R-51, R-81 |
| C-32 | `src/core/ops/facts.ts:518-537, 1426-1440`; `src/core/think/gather.ts:166-206` | recall·think가 검색을 부르는 인자 | R-90 |

### 1.6 수락 사례

출처: 사례별 표기. "실행"은 `agent-memory/artifacts/gbrain/search-demos/demo-pure.mts` 출력(`demo-pure.out.2026-10-23.json`)에서 값을 가져온 것이고, "도출"은 구현에서 도출했고 실행하지 않았다. 의존을 가짜로 바꾼 사례는 가짜인 부분을 적었고 그래서 검증하지 않는 것(공급자 응답, 실제 SQL)이 있다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-30 | 벡터 목록 [A#1(ct), B#2(ct), A#3(timeline)], 키워드 목록 [B#2, C#4(timeline)], 둘 다 k=60, 부스트 없음 | 순서 B#2=1.0000, A#1=0.5041, C#4=0.4959, A#3=0.4879. A는 벡터 목록에서 두 청크를 내도 페이지 표는 한 번(1/60) | 실행 |
| T-02 | R-12, R-30 | T-01 입력, 명시 `low` / 자동 low | 명시: B#2=2.0, A#1=1.0083(compiled_truth ×2 후). 자동: B#2=1.2, A#1=0.6050. 청크 없는 제목 행은 부스트 1 | 실행 |
| T-03 | R-24, R-31 | 원 질의 + 변형 2개(비지 않음), 예산 null / 1 / 0.5 | null: 모든 목록 가중 없음(1). 1: 변형 각 w=0.5. 0.5: 각 w=0.25. 키워드 k를 50으로 주면 title·keyword k=50, relational k=60 | 실행 |
| T-04 | R-32 | fused 점수 [0.04, 0.02, 0.01], cosine {1:0.5, 2:0.9}, 3번 청크는 읽히지 않음 | 점수 0.8500 / 0.6200 / 0.1750(cosine 0 처리). 아무것도 안 읽히면 입력 객체 그대로, SQL 실패면 JS 폴백, 둘 다 실패면 입력 그대로 | 실행 (가짜 엔진) |
| T-05 | R-34 | 한 페이지의 timeline 청크 4개와 compiled_truth 1개 | p#1, p#2, p#5(상위 2 + compiled_truth 덧붙임). Jaccard 0.909인 같은 페이지 청크는 제거되고 다른 페이지의 같은 문장은 유지. 타입 2종 10행이면 `note` 6·`company` 2. 타입 1종이면 상한 미적용 | 실행 |
| T-06 | R-37 | 예산 250, 행 비용 100/500/100 | 첫·셋째 행 유지(둘째 건너뜀), used=200. 첫 행만 1000토큰이면 예산 100에서 복사본 1행, `truncated:true`, used=100, 원본 4000자 그대로. 예산 없음/0/음수는 무동작 | 실행 |
| T-07 | R-35 | 풀 [A..E], `topNIn`=4, 공급자 순서 [C,A,D,B] | C, A, D, B, E(꼬리 E 유지), `reranker_delta` [2,-1,1,-2]. 동점 3개는 입력 순서. `topNOut`=3이면 3행 | 실행 (가짜 공급자) |
| T-08 | R-35, R-62 | 가짜 공급자가 `no_key` / timeout / auth / rate_limit / network / 일반 오류 / 빈 배열 / 비배열 | 모두 입력 그대로. `no_key`는 `reranker_skipped`·감사 0행, 나머지는 `rerank_failed`(이유 코드 `timeout`·`auth`·`rate_limited`·`provider_error`) + 감사 행, 빈/비배열은 `rerank_passthrough`(`empty_result_set`/`malformed_shape`) | 실행 (가짜 공급자) |
| T-09 | R-24, R-63 | `expandQuery("acme revenue")`(2단어), 확장 불가, 정상(변형 4개 중복 포함), gateway 오류 | `["acme revenue"]`(gateway 0회), `[질의]`(0회), `[원, "ACME revenue growth rate", "sales trend of acme"]`(대소문자 중복 제거, 변형 2개), `[질의]` | 실행 (가짜 gateway) |
| T-10 | R-02, R-03, R-04 | `resolveSearchMode` 호출 | tokenmax 번들에서 설정 `searchLimit:7`·`reranker_enabled:false`, 호출 `searchLimit:3` → 3, 리랭크 꺼짐. `mode:'turbo'` → balanced(`mode_valid:false`), `'  TokenMax '` → tokenmax, 모드 없음 → balanced. 번들 키 44개 중 차이 나는 8개 | 실행 |
| T-11 | R-40 | `sourceScopeOpts`: ① 원격 `sourceId:'a'` + 허용 `[x,y]` ② 원격 허용 `[]`, 단일 소스 없음 ③ 로컬 허용 `[]`, 단일 없음 ④ 원격 `sourceId:'__all__'` ⑤ `'__none__'` | ① `{sourceIds:[x,y]}` ② `permission_denied` ③ `{}` ④ `{sourceId:'__all__'}`(어떤 소스도 일치 안 함) ⑤ `no_source_grant` | 실행 |
| T-12 | R-41, R-42 | 키워드 질의 술어 빌더에 `sourceIds:['a','b']` / `[]` / `sourceId:'a'` / 없음, 가시성 절 | 소스 절은 배열·단일일 때만 생김, 빈 배열·없음은 없음, 둘 다 있으면 배열. 가시성 절에 `deleted_at IS NULL`, `NOT s.archived`, `quarantine`, `pinned_question`, 현재 투영 조건이 있고 원격이면 `chunker_version`·private 필터가 추가 | 실행 |
| T-13 | R-20 | OR 폴백 빌더: `acme revenue growth` / `acme` / `"acme revenue"` / `acme -revenue` / `Acme acme OR growth AND x` | `acme OR revenue OR growth` / null / null / null / `Acme OR growth OR x`. 300단어는 256단어로 잘림 | 실행 |
| T-14 | R-13, R-33 | 의도 분류 | `who is alice-example` entity/low, `when did we last meet acme` temporal/high, `acme raised $5M announcement` event/high, `what is the ownership economy` concept/없음, `catch me up on acme today` general·recency strong·salience on, `show me photos of the offsite` modality image | 실행 |
| T-15 | R-50, R-53 | `resultChunkCap`, `leanRow`, `scoresFollowRank` | 상한: 명시 0→0, 없음→8000, 서브에이전트→300. lean 행은 slug·title·type·chunk_text·chunk_id·score(4자리)·source_id·effective_date만. 리랭크 목록 [b(.8), a(.4), 점수 없음 c]의 score는 .8, .4, .4이고 원래 값은 `fused_score` | 실행 |
| T-16 | R-70, R-71 | 의미 캐시 모듈 호출 | `semanticResultCacheAvailable()`=false. `cacheRowId`는 같은 입력 같은 id(32자), knobs가 다르면 다른 id. 텍스트 가드: 정규화 동일·Dice 통과는 true, 무관한 질의는 false. scope 키: 연합 `__set__:a,b`, 단일 `a`, 없음 `__unscoped__` | 실행 |
| T-17 | R-80 | `search_exact` 스캔(가짜 엔진, 배치 2페이지): 페이지 3개 모두 매칭 / limit 2 / 가운데 페이지가 `unchunked` / 마감 시각 지남 | `complete:true` / `limit`·`resume_after:2` / 매칭 s1·s3, `unreadable_pages`, `unreadable.total:1` / `deadline`, `resume_after:0`. 구 패턴 `quarterly[[:space:]]+board[[:space:]]+pack` | 실행 (가짜 엔진, 실제 SQL 미검증) |
| T-18 | R-60, R-62 | 임베딩 키 없는 브레인에서 `query "…"`, balanced | 벡터·리랭크 없이 키워드(+제목) 결과, 메타 `vector_enabled:false`·`degraded:[embed_unavailable(no_provider)]`(키워드 0건이면 `keyword_zero`도), 오류 없음 | 도출 (미실행) |
| T-19 | R-60, R-62 | 임베딩 키는 있고 Voyage 키 없음, balanced | 벡터 arm·RRF·재점수 수행, 리랭크만 `reranker_skipped`, 호출 성공 | 도출 (미실행) |
| T-20 | R-40, R-42 | 소스 s1의 페이지 P가 소프트 삭제 / frontmatter `quarantine` / 소스 archived, 호출자 범위 s1 | 세 경우 모두 `search`·`query`·`search_exact` 결과에 P가 없다(청크가 남아 있어도) | 도출 (미실행) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@63f62b2 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | `cli/main.ts:361-364`(`ask` → `query`), `ops/search-exact.ts:2`, `cli/main.ts:365-367`, `cli/command-route.ts:11-14` | 코드 읽기 |
| R-02, R-04 | C-02, C-03, C-23; `ops/context.ts:1218-1226`; `search/keyword-paging.ts:74-105`; `commands/config.ts:1439-1466`(`search.mode` 쓰기: 값 검증 없음, `search.mode_source` 기록) | `demo-pure` mode·무효 모드 사례. 설치 시 첫 모드 선택(`init --search-mode`, `mode-advice.ts`)은 값을 DB에 쓰는 경계만 확인 |
| R-03 | C-01, `demo-pure.out`의 `mode: MODE_BUNDLES…`, `mode: knobs that differ…` | 값은 발췌 모듈 실행 결과(상수 4개는 값만 주입) |
| R-05, R-06 | `ops/search.ts:90-95, 727, 1032`; `search/hybrid/request.ts:195-197`; `eval-pool-depth.ts:28-37`; `engine.ts:802-809`; `pglite-engine.ts:1405-1414`; `vector-statement.ts:295-296`; `keyword-paging.ts:34, 74-105` | 수식은 `demo-pure` 실행. 결합 후 합집합이 100을 넘는지는 추론 |
| R-10, R-11 | C-06, C-22(`search` handler `ops/search.ts:760-836` vs `query` `1017-1078`) | 코드 흐름 읽기 |
| R-12 | `hybrid.ts:91-132`; `hybrid/request.ts:223-230`; `sql-ranking.ts:67-77`; `keyword-statement.ts:68`; `hybrid.ts:1155-1157` | 부스트 수치는 실행(T-02) |
| R-13 | C-07, C-08, `demo-pure` intent | 은행은 실제 모듈로 실행 |
| R-20 | C-10; `arms.ts:80-110`; `postgres-engine.ts:1195-1211` | OR 빌더·술어는 실행, 엔진 SQL은 읽기만 |
| R-21 | C-11 | 읽기만 |
| R-22 | C-12, C-21; `ai-gateway.md` R-23 | 읽기만. 후보 수집 최적화 경로는 읽지 않음 |
| R-23 | C-25; `demo-pure` source boost | 실행 |
| R-24 | C-09; `ops/search.ts:1037-1038, 800-803`; `mode.ts:122`; `ai-gateway.md` R-40, R-41 | expandQuery는 발췌 실행(T-09) |
| R-30, R-31 | C-13, C-14, C-08 | 실행(T-01~T-03) |
| R-32 | C-15 | 실행(T-04) |
| R-33 | C-16, C-27, C-08 | 식·상수는 코드 확인. 실행하지 않음 |
| R-34 | C-17 | 실행(T-05) |
| R-35 | C-18, `ai-gateway.md` R-50~R-52, R-04 | 실행(T-07, T-08, 가짜 공급자) |
| R-36 | `rank.ts:445-470, 505-506`; `mode.ts:331, 339` | 읽기만 |
| R-37 | C-19 | 실행(T-06) |
| R-50 | C-26 | 실행(T-15) |
| R-51 | C-31 | 기본 판정 코드 확인(`evidence-delivery.ts:226-328`). 전달 본문 미열람 |
| R-52 | C-29 | 읽기만 |
| R-53 | C-26 | 실행(T-15) |
| R-60, R-61 | C-20, C-21, `hybrid.ts:1095-1134`, `embedding-disabled.ts:34-40`, `ai-gateway.md` R-05·R-26 | 읽기만(T-18은 도출) |
| R-62, R-63, R-64 | C-18, C-09, `arms.ts:255-258`, `hybrid/degraded.ts` | 읽기 + T-08 |
| R-40 | C-23, `demo-pure` scope | 실행(T-11). 원격·`auth` 없음은 호출자 코드(HTTP·MCP 서버) 미열람 |
| R-41, R-42 | C-24, C-10~C-12, `read-policy-sql.ts` | 실행(T-12) |
| R-70, R-71 | C-28 | `semanticResultCacheAvailable` 값은 실행. SQL·게이트는 읽기 |
| R-80 | C-30 | 실행(T-17, 가짜 엔진) |
| R-81 | C-31; `ops/search.ts:946-992` | 읽기만 |
| R-90 | C-32 | 읽기만 |
| 문서와 구현의 차이 | `CLAUDE.md`와 `docs/guides/search-modes.md`는 "semantic result reuse is disabled"라고 쓰고, 코드(`query-cache.ts:35`)도 같다. 반면 `MODE_BUNDLES`의 `cache_*`와 `cache_stats` 응답 주석은 켜진 것처럼 보인다. 구현(비활성)이 사실이다 | 코드 확인 |

### 2.2 코드 읽는 순서

1. `ops/search.ts`의 `search`(689)와 `query`(842) 핸들러에서 인자 전달과 op 계층 후처리를 본다.
2. `search/hybrid.ts:1070-1171`의 `hybridSearch`가 단계 순서의 원본이다. 단계 본문은 `search/hybrid/*.ts`(request → arms → rank → keyword-only)로 나뉜다.
3. 결합 알고리즘은 `rrf-page-fusion.ts`와 `fusion-lists.ts`, 정리는 `dedup.ts`, `rerank.ts`, `token-budget.ts`.
4. 모드는 `mode.ts`의 `MODE_BUNDLES`와 `resolveSearchMode`. 설정 키 이름은 `KNOB_CONFIG_KEY`.
5. 가시성은 `sql-ranking.ts`의 `buildVisibilityClause`.
- 구현 전략: 벡터 쪽과 키워드·제목 쪽을 병렬로 시작하고 `joinVectorSide`에서 합친다. 한 arm의 실패는 단계별 `degraded` 표지로 남기고 계속한다. 의미 캐시와 `search.expansion`처럼 "있지만 꺼진" 기능이 많아 노브 이름이 실제 효과와 어긋날 수 있으니 번들 값과 호출 경로 둘 다 확인해야 한다.
