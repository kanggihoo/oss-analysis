---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/core/quality.py
  - src/hyperresearch/core/graphrank.py
  - src/hyperresearch/core/independence.py
  - src/hyperresearch/core/similarity.py
  - src/hyperresearch/core/scholar.py
  - src/hyperresearch/core/config.py
  - src/hyperresearch/core/note.py
  - src/hyperresearch/core/runs.py
  - src/hyperresearch/cli/sources.py
  - src/hyperresearch/cli/graph.py
  - src/hyperresearch/cli/repair.py
  - src/hyperresearch/cli/lint.py
  - src/hyperresearch/cli/fetch.py
  - src/hyperresearch/skills/hyperresearch.md
  - src/hyperresearch/skills/hyperresearch-3-contradiction-graph.md
depends:
  - vault-store.md
status: ready
---

# 소스 품질: 랭킹·독립성·철회

> 노트(소스)마다 티어·유틸리티·인용 기반 권위·링크 그래프 중심성을 재정규화해 합친 `quality_score`를 계산하고, 파생 사본을 묶어 독립성 점수를 매기며, DOI 노트의 인용 수·철회 여부를 학술 API로 채우고 ship 직전 캐시 없이 다시 확인하는 명령(`sources score|retractions|independence|backfill-doi`, `graph rank`)을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. fetch가 노트를 만들 때 `tier`(URL·콘텐츠 종류 휴리스틱), `utility_score`(오케스트레이터가 준 0~18 점수), `doi`를 frontmatter에 남긴다(경계: 행 11).
2. 2단계 끝(2.7)에서 순서대로 `sources backfill-doi`(놓친 DOI 보충) → `sources score`(DOI 노트의 인용 수·venue·철회 여부를 OpenAlex/Semantic Scholar로 채우고, 권위 백분위와 `quality_score`를 다시 계산) → `graph rank`(링크 그래프 PageRank → `centrality_score`, `quality_score` 다시 계산)를 부른다.
3. 3단계(모순 그래프)의 합의 판정 전에 `sources independence --tag <tag>`가 같은 URL·거의 같은 본문·같은 통신사 보도문 소스를 묶어 `independence`를 쓴다.
4. 10단계 큐레이션은 `search --ranked`(vault-store R-21)와 `quality_score`로 좋은 소스를 우선한다. 철회 소스는 점수가 바닥(0.05)이라 자동으로 밀려난다.
5. ship 직전에 `sources retractions --tag <tag>`가 DOI가 있는 모든 노트를 캐시 없이 다시 조회한다. 그 뒤 `run finish`의 `retracted-citations` 검사가 DB의 `is_retracted = 1` 노트를 보고서가 철회 언급 없이 인용했는지 본다(경계: 행 9·10).

### 1.2 범위·통합 지점
- 제공: 점수 계산 규칙(`quality`·PageRank·권위 백분위·독립성), `sources score|retractions|independence|backfill-doi|list|check`, `graph rank`.
- 제외(경계만):
  - 노트 스키마·`notes`의 점수 칼럼 DDL·동기화가 파생 칼럼을 보존하는 규칙은 `capabilities/vault-store.md`(선행). 이 스펙은 그 칼럼에 값을 쓰는 쪽이다.
  - `tier`·`utility_score`·`doi`를 정하는 fetch 쪽 로직(`_detect_tier`, `extract_doi` 호출, `--utility-score`)은 행 11. `extract_doi`와 `backfill_dois`의 규칙만 여기 있다(R-23).
  - 학술 소스 8개의 *검색*·병합 클라이언트(`hpr scholar search`, `scholar/` 패키지)는 행 13([scholar-search](scholar-search.md))이다. 이 스펙은 DOI 한 건 조회(`lookup_metadata`)와 그 HTTP·캐시 계층(`_fetch_json`, OA 복구 행 14와 공유)의 계약만 둔다.
  - 점수를 소비하는 쪽(`search --ranked`는 vault-store, 10단계 큐레이션·합의 판정·`claims matrix` 정렬·`retracted-citations` 검사)은 R-25에 읽는 칼럼만 적는다.
  - 클레임 저장소는 `capabilities/claims-store.md`.
- 외부 의존·선행 계약: `vault-store.md`의 `Vault`·`notes`(`tier`·`utility_score`·`doi`·`citation_count`·`venue`·`is_retracted`·`authority_score`·`centrality_score`·`independence`·`quality_score`)·`links`·`tags`·`note_content`·`api_cache`·`sync`가 파생 칼럼을 지우지 않는다는 보장. 네트워크(OpenAlex·Semantic Scholar HTTPS).
- 소유 상태·부작용: `notes`의 파생 점수 4칼럼(`authority_score`·`centrality_score`·`independence`·`quality_score`, DB에만 있고 frontmatter에 없음), `citation_count`·`venue`·`is_retracted`(DB와 frontmatter 양쪽), `doi`(backfill 시 frontmatter와 DB), `api_cache` 행.

### 1.3 인터페이스와 데이터 의미

**점수 입력(모두 `notes` 칼럼)과 의미**

| 칼럼 | 값 범위 | 출처 |
|---|---|---|
| `tier` | `ground_truth\|institutional\|practitioner\|commentary\|unknown` 또는 NULL | frontmatter(fetch가 휴리스틱으로 기록, 에이전트가 고칠 수 있음) |
| `utility_score` | 0~18(규약), NULL 가능 | frontmatter(`fetch --utility-score`) |
| `authority_score` | 0~1 | `compute_authority_scores`(R-18) |
| `centrality_score` | 0~1 | `compute_centrality`(R-07) |
| `independence` | 0~1 | `compute_independence`(R-12). **`quality_score`의 입력이 아니다**(R-04) |
| `quality_score` | 0~1 또는 NULL | `compute_quality_scores`(R-01~R-03) |
| `citation_count`·`venue`·`is_retracted` | int·string·NULL/0/1 | `score_sources`(R-14~R-19). `is_retracted`: NULL=미확인, 0=확인했고 아님, 1=철회 |

**설정 `[ranking]`** (기본값, `RankingSettings`): `w_tier=0.35`, `w_utility=0.20`, `w_authority=0.25`, `w_centrality=0.20`, `tier_ground_truth=1.0`, `tier_institutional=0.85`, `tier_practitioner=0.7`, `tier_commentary=0.4`, `tier_unknown=0.6`, `retraction_floor=0.05`, `api_cache_ttl_days=30`. `[dedup] shingle_size=3`(독립성의 본문 비교에 쓰임). 알 수 없는 키는 무시된다(vault-store 1.3).

**함수**

| 연산 | 입력 → 출력 | 의미 |
|---|---|---|
| `compute_quality_for_row(ranking, tier, utility, authority, centrality, is_retracted)` | → float 또는 None | R-01·R-02 |
| `compute_quality_scores(conn, ranking)` | → 갱신 행 수(전체 노트 수) | 모든 노트의 `quality_score` 재계산 후 commit |
| `pagerank(nodes, edges, damping=0.85, max_iterations=50, convergence=1e-6)` | → `{id: 원점수}` | R-05 |
| `compute_centrality(conn)` | → 점수를 쓴 노트 수 | R-06·R-07 |
| `canonical_url(url)` | → string | R-09 |
| `compute_independence(vault, tag=None)` | → `{scored, clusters[{root, members[], size, kind}]}` | R-09~R-12 |
| `lookup_metadata(conn, doi, ttl_days, fresh=False)` | → `{citation_count, venue, is_retracted}` 또는 None | R-15 |
| `score_sources(vault, tag=None, fresh=False, limit=None)` | → `{scored, retracted[id], missing[id], rate_limited[id], authority_ranked}` | R-14~R-19 |
| `compute_authority_scores(conn)` | → 점수를 쓴 노트 수 | R-18 |
| `backfill_dois(vault, tag=None)` / `extract_doi(url, raw_html=None, content=None)` | → 새로 DOI를 얻은 노트 수 / DOI 또는 None | R-23 |
| `RateLimitedError(host, attempts)` | 예외 | 429가 재시도 예산을 넘었을 때 |

**CLI** (JSON 봉투는 vault-store 1.3, 볼트가 없으면 `NO_VAULT` 종료 1, 모두 `--json/-j`):

| 명령 | 옵션 | 출력 |
|---|---|---|
| `sources score` | `--tag/-t`, `--fresh`, `--limit/-n` | auto_sync 후 `score_sources`. data=`{scored, retracted, missing, rate_limited, authority_ranked}`. 텍스트: `Scored: N notes enriched`, 권위 순위 수, 철회 id 목록(빨강), 메타 없음 개수, 속도 제한 개수와 "set S2_API_KEY or re-run later" |
| `sources retractions` | `--tag/-t` | auto_sync 후 `score_sources(fresh=True)`. data=`{checked: scored, retracted, unresolved: len(missing), rate_limited: 개수}`. 속도 제한이 있으면 "the sweep is incomplete" 경고 |
| `sources independence` | `--tag/-t` | auto_sync 후 `compute_independence`. data=결과 그대로, `count`=클러스터 수. 텍스트: `N notes scored, M derivative cluster(s)`와 클러스터마다 `[kind] root R <- 멤버…` |
| `sources backfill-doi` | `--tag/-t` | auto_sync 후 `backfill_dois`. data=`{dois_added}` |
| `sources list` | `--domain`, `--limit/-n`(50) | `sources` 테이블을 `fetched_at` 내림차순. 항목 `{url, note_id, domain, fetched_at, provider, status}`. auto_sync 안 함 |
| `sources check URL` | | `{exists:true, url, note_id, domain, fetched_at, provider}` 또는 `{exists:false, url}` |
| `graph rank` | `--top/-n`(10) | auto_sync → `compute_centrality` → `compute_quality_scores`. data=`{ranked, top:[{id, title, centrality(소수 4자리)}]}`, `count=ranked`. top은 `centrality_score` NOT NULL을 내림차순 |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `compute_quality_for_row`, 철회 아님 | 구성요소 (가중치, 값) 목록: 티어 가중치가 있으면 `(w_tier, tier값)`, `utility_score`가 있으면 `(w_utility, clamp(utility/18, 0, 1))`, `authority_score`가 있으면 `(w_authority, clamp(authority, 0, 1))`, `centrality_score`가 있으면 `(w_centrality, clamp(centrality, 0, 1))`. 결과 = `Σ(w·v) / Σ w`(있는 구성요소의 가중치만으로 나눔, 곧 재정규화). 티어 값은 `tier_*` 설정 5개 중 해당 값, `tier`가 NULL이면 구성요소 없음 | 코드 확인 |
| R-02 | 구성요소 없음 / 가중치 합 ≤ 0 / 철회 | 구성요소가 없거나 가중치 합이 0 이하면 None. `is_retracted`가 참이면 다른 값과 무관하게 `retraction_floor`(0.05)를 돌려준다(None 판정보다 먼저) | 코드 확인 |
| R-03 | `compute_quality_scores` | 모든 노트(인덱스·스텁 포함)에 대해 `tier, utility_score, authority_score, centrality_score, is_retracted`를 읽어 R-01로 계산하고(`is_retracted`는 `bool()`이라 NULL은 철회 아님) `quality_score`를 갱신, commit. 반환은 노트 수. 값은 frontmatter에 쓰지 않으며 sync가 건드리지 않아 유지된다 | 코드 확인 |
| R-04 | 재계산 시점과 입력 | 호출처: `sources score`(R-14 끝), `graph rank`, `repair`의 4.5단계(중심성+품질). `sources independence`는 `quality_score`를 다시 계산하지 않고 `independence`도 R-01의 입력이 아니다. `independence` 칼럼을 읽는 파이썬 코드는 이 레포에 없다 | 코드 확인 |
| R-05 | `pagerank(nodes, edges)` | 노드가 없으면 `{}`. 간선은 중복 제거, 자기 루프·모르는 노드로의 간선 제외. 초기값 `1/n`, `base=(1−0.85)/n`. 반복마다 `dangling_mass`=나가는 간선이 없는 노드들의 현재 순위 합을 모든 노드에 `/n`으로 균등 분배: `new[v] = base + 0.85·(Σ_{u→v} rank[u]/outdeg(u) + dangling_mass/n)`. 한 반복의 L1 변화량이 `1e-6` 미만이면 멈추고, 최대 50번. 정규화 전 원점수를 돌려준다 | 코드 확인 |
| R-06 | `compute_centrality` 노드·간선 | 노드 = `summary`가 `"Stub for [["`로 시작하지 않는 모든 노트(인덱스·MOC·interim 포함. NULL summary는 `''`로 취급). 스텁 노트의 `centrality_score`는 먼저 0으로 리셋. 간선 = `links`에서 `target_id IS NOT NULL`인 `(source_id → target_id)`(해소된 위키링크 전부. 스텁이 끼는 간선은 노드 밖이라 R-05가 버린다). `fetch --suggested-by`는 새 노트 본문 앞에 `*Suggested by [[제안한노트]] — 이유*`를 넣어 링크가 **새 노트 → 제안한 노트** 방향으로 생긴다. 따라서 순위가 모이는 곳은 제안자 쪽이다 | 코드 확인 |
| R-07 | 정규화·저장 | 원점수를 최댓값으로 나눠 최고 노트가 1.0이 되게 하고 `centrality_score`에 쓴 뒤 commit, 반환은 점수를 쓴 노트 수. 노드가 없거나 최댓값이 0 이하이면 쓰지 않고 0을 돌려준다 | 코드 확인 |
| R-08 | `graph rank` | auto_sync → R-07 → `compute_quality_scores`(R-03) → `centrality_score IS NOT NULL` 상위 `--top`개를 `{id, title, centrality 반올림 4자리}`로 반환. 텍스트는 `Centrality computed: N notes`와 `0.xxxx id title` 줄 | 코드 확인 |
| R-09 | `canonical_url`·URL 묶기 | URL을 `strip().lower()` 한 뒤 호스트의 앞 `www.`를 떼고, 경로 끝의 `/`를 떼고, 쿼리는 값이 비지 않은 `(k,v)` 중 키가 `^(utm_\|fbclid\|gclid\|ref$\|source$)`에 맞지 않는 것만 정렬해 다시 인코딩하고, 스킴은 `https`로 통일, fragment·params는 버린다(경로·쿼리까지 소문자가 된다). 같은 정규화 URL을 가진 노트들은 첫 노트에 나머지를 합친다(`url`) | 코드 확인 |
| R-10 | 통신사 서명 묶기 | 본문(`body_plain`) 앞 1500자를 소문자로 만들어 `WIRE_MARKERS`(prnewswire, pr newswire, business wire, businesswire, globe newswire, globenewswire, (reuters), (ap), associated press, accesswire, newsfile corp) 중 튜플 순서상 처음 발견되는 것을 `marker`로 삼고, 같은 앞부분의 `[a-z0-9]{4,}` 토큰 첫 10개를 공백으로 이어 `"marker\|토큰들"`을 서명으로 쓴다. 마커가 없으면 서명 없음. 서명이 같은 노트들은 첫 노트에 합친다(`wire`) | 코드 확인 |
| R-11 | 본문 근사 중복 묶기 | 노트마다 `shingle(body_plain, n=dedup.shingle_size)`(소문자 공백 분할 단어 n-gram 집합, 단어가 n개 미만이면 전체를 한 조각, 빈 본문이면 빈 집합). 모든 쌍 `(i<j)`에서 이미 같은 클러스터면 건너뛰고, 자카드(`|∩|/|∪|`, 한쪽이 빈 집합이면 0) ≥ 0.7이면 합친다(`body`). MinHash가 아니라 정확 자카드이며 O(n²)다 | 코드 확인 |
| R-12 | 독립성 점수·출력 | 대상: `source IS NOT NULL`이고 `type != 'index'`인 노트(`--tag`이면 그 태그를 가진 노트만). R-09→R-10→R-11 순으로 union-find. 클러스터(≥2)에서 `created` 문자열 오름차순(빈 값은 `''`)으로 정렬해 첫 노트가 root(독립성 1.0), 나머지는 `round(1/클러스터 크기, 4)`. 단일 노트는 1.0. `scored`=대상 노트 수. 클러스터 항목 `{root, members(root 제외 id), size, kind}`, `kind`는 클러스터 안에서 기록된 합친 이유(`url`·`wire`·`body`)를 정렬해 `+`로 잇고 없으면 `mixed`. 대상 밖 노트의 `independence`는 그대로 | 코드 확인 |
| R-13 | `sources independence` | R-12를 부르고 결과를 출력(1.3). `--tag`가 없으면 볼트 전체를 비교하므로 O(전체²) | 코드 확인 |
| R-14 | `score_sources` 대상 | `doi IS NOT NULL`인 노트, `--tag`면 그 태그만, `fresh`가 거짓이면 `citation_count IS NULL`인 노트만, `limit`이면 앞 N개. 노트마다 `lookup_metadata`를 불러 결과가 None이면 `missing`에 id, `RateLimitedError`면 `rate_limited`에 id(갱신하지 않음, 다음 실행에서 재시도). 루프 뒤 commit → `compute_authority_scores` → `compute_quality_scores` | 코드 확인 |
| R-15 | `lookup_metadata` 라우팅 | DOI가 `arxiv:`로 시작(대소문자 무시)하면 Semantic Scholar `GET /graph/v1/paper/arXiv:<id>?fields=citationCount,venue,externalIds` → `{citation_count: citationCount, venue: venue 또는 None, is_retracted: None}`. 아니면 OpenAlex `GET https://api.openalex.org/works/doi:<DOI를 /까지 %인코딩>?select=cited_by_count,primary_location,is_retracted` → `{citation_count: cited_by_count, venue: primary_location.source.display_name 또는 None, is_retracted: bool(is_retracted, 기본 False)}`. OpenAlex가 None(404·오류·5xx 등)이면 Semantic Scholar `GET /graph/v1/paper/DOI:<DOI>?fields=citationCount,venue` → `is_retracted: None`. 마지막도 None이면 None. 속도 제한 예외는 그대로 전파 | 코드 확인 |
| R-16 | 철회 3값 보존 | 새 `is_retracted`가 None(=Semantic Scholar가 답했거나 철회 정보 없음)이고 DB의 기존 값이 1이면 True로 유지한다(OpenAlex 장애 때 `--fresh`가 철회를 지우지 않게). 기존 0은 보존하지 않는다 — NULL이 된다. 새 값이 True/False면 그대로 | 코드 확인 |
| R-17 | 노트 갱신 | 성공한 노트마다 DB `citation_count`·`venue`·`is_retracted`(NULL/0/1)를 쓰고, 노트 파일이 있으면 frontmatter를 `parse_frontmatter`→필드 대입→`render_note`로 다시 쓴다(알 수 없는 키는 사라지고, `is_retracted`가 None이면 키 생략). 파일을 쓴 뒤 DB의 `file_mtime`은 갱신하지 않으므로 다음 sync가 그 노트를 `update`한다. 철회로 판정된 노트 id는 `retracted`에 쌓인다 | 코드 확인 |
| R-18 | `compute_authority_scores` | `citation_count IS NOT NULL`인 노트 전체(태그 필터 없음, 볼트 상대)를 `log1p(citation_count)` 오름차순으로 정렬해 순위 `r`(0부터)에 `(r+1)/n`을 쓴다(n=1이면 1.0, 동점도 서로 다른 순위, 정렬은 안정). 인용 수가 없는 노트의 `authority_score`는 건드리지 않는다. 노트가 없으면 0을 돌려주고 아무것도 안 쓴다 | 코드 확인 |
| R-19 | 속도 제한과 HTTP 실패 | HTTP 계층(`_http_get_json`): `httpx.get`(타임아웃 20초, 자동 리디렉션 끔, 최대 5홉을 수동으로 따름, 매 홉 헤더 재계산), 429는 `Retry-After`(0~60초면 그 값) 아니면 2초·4초 대기하며 총 3번까지 시도한 뒤 `RateLimitedError`, 그 밖의 예외·200이 아닌 응답·JSON 오류는 None. `_fetch_json`: `api_cache`에서 `fetched_at`이 `ttl_days` 이내면 캐시를 쓰고(`fresh`이면 읽기를 건너뜀), 아니면 호스트별 최소 간격(openalex 0.15s, semanticscholar 1.1s, crossref 0.15s, unpaywall 0.15s, ebi 0.2s, 그 외 0.2s)을 지켜 호출하고 **성공 본문만** `INSERT OR REPLACE`한다. Semantic Scholar 키(`S2_API_KEY`/`SEMANTIC_SCHOLAR_API_KEY`)는 `semanticscholar.org` 호스트로 가는 요청에만 `x-api-key`로 붙는다 | 코드 확인 |
| R-20 | `sources retractions` | `score_sources(fresh=True)`로 DOI 보유 노트 전부(`citation_count`가 이미 있어도)를 캐시 없이 다시 조회한다(새 응답은 캐시에 다시 쓴다). 출력은 `{checked, retracted, unresolved, rate_limited}`. 철회 대상 목록은 출력만 하고 노트를 따로 표시하지 않는다(`is_retracted`만 갱신) | 코드 확인 |
| R-21 | ship 직전 순서(경계) | 진입 스킬이 `sources retractions --tag <tag> --json` 다음에 `run finish`를 부르게 한다. `run finish`→`verify_run`이 같은 프로세스에서 `lint._check_retracted_citations`를 부르고, 이 검사는 `is_retracted = 1`인 노트만 대상으로 하며 보고서에서 그 노트를 가리키는 `[[id]]` 앞뒤 200자에 "retract"(대소문자 무시)가 없으면 `error`를 낸다. NULL(미확인)은 막지 않는다 | 코드 확인 |
| R-22 | 2.7 순서(경계) | 2단계 끝 스킬이 `claims ingest` → `sources backfill-doi` → `sources score` → `graph rank` 순서를 지시하고 철회가 나오면 `coverage-gaps.md`에 기록하라고 한다. 이 순서 자체를 강제하는 코드는 없다(호스트가 따름) | 코드 확인(스킬 텍스트) |
| R-23 | `extract_doi`·`backfill_dois` | `extract_doi` 우선순위: (1) 호스트에 `doi.org`가 있는 URL 경로의 `10.NNNN+/…`, (2) `arxiv.org/(abs\|pdf)/NNNN.NNNN[N][vN]` → `"arXiv:<id>"`, (3) `<meta name\|property="citation_doi"\|"dc.identifier" content="[doi:]10.…">`, (4) 본문 앞 20,000자의 `DOI:? [`]10.…`. 끝의 `.,;`는 뗀다. `backfill_dois`: `doi IS NULL AND source IS NOT NULL`(+`--tag`) 노트마다 파일을 읽어 `extract_doi(source, content=본문)`(HTML 메타는 없음)로 얻으면 frontmatter `doi`를 쓰고 파일을 다시 쓰며 DB `doi`를 갱신하고 얻은 노트 수를 센다 | 코드 확인 |
| R-24 | `sources list`·`check` | `sources` 테이블(행 11이 채움)을 읽기만 한다. `check`는 URL 문자열 정확 일치 | 코드 확인 |
| R-25 | 점수 소비(경계) | `search --ranked`는 `quality_score`로 BM25 점수를 `(0.5 + q 또는 0.5)`배 한다(vault-store R-21). `claims matrix`는 `quality_score` 내림차순(NULL 뒤). 3단계 스킬은 합의 판정에 "독립성 점수 합 ≥ 3.0, 클러스터는 한 표"라 쓰고 `sources independence -j` 출력을 읽는다. 10단계 스킬은 `--ranked` 검색으로 소스를 고르게 한다. 코드는 이 소비자들의 구현이 아니라 읽는 칼럼만 제공한다 | 코드 확인 |

- 불변식: (1) `quality_score`는 NULL이거나 `[0,1]`이다(구성요소가 `[0,1]`로 clamp되고 가중치가 양수일 때. 가중치를 음수로 설정하면 보장되지 않음). (2) 철회(`is_retracted` 참)인 노트의 `quality_score`는 항상 `retraction_floor`다. (3) `independence`는 root와 단일 노트에서 1.0이다.
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다. OpenAlex·Semantic Scholar의 응답 필드(`cited_by_count`, `primary_location.source.display_name`, `is_retracted`, `citationCount`, `venue`)가 실제로 그 모양인지는 코드의 가정이며 웹으로 확인하지 않았다(미확인). 반복 PageRank의 수렴 값은 손계산 근사다.

### 1.5 필수 코드 참조
`~` = `research/repos/hyperresearch/src/hyperresearch/`

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `~/core/quality.py:22-75` | 구성요소·재정규화·철회 바닥·전체 재계산 | R-01 R-02 R-03 |
| C-02 | `~/core/config.py:75-83`, `:106-137` `DedupSettings`, `RankingSettings` | 가중치·티어 값·바닥·TTL·shingle 기본값, `tier_weight` | R-01 R-11 |
| C-03 | `~/core/graphrank.py:14-105` | PageRank, 스텁 제외, 정규화·저장 | R-05 R-06 R-07 |
| C-04 | `~/core/note.py:26-31` `STUB_SUMMARY_PREFIX`, `stub_summary` | 스텁 판별 접두 | R-06 |
| C-05 | `~/core/independence.py:26-151` | 정규화 URL, 통신사 서명, 클러스터링, 점수·출력 | R-09 R-10 R-11 R-12 |
| C-06 | `~/core/similarity.py:12-26` `shingle`, `jaccard` | 단어 n-gram, 자카드 | R-11 |
| C-07 | `~/core/scholar.py:102-276` HTTP·캐시 계층 | 429 재시도, 수동 리디렉션, 키 범위, TTL·호스트 간격 | R-19 |
| C-08 | `~/core/scholar.py:284-340` `lookup_metadata` | DOI 라우팅·필드 매핑·폴백 | R-15 |
| C-09 | `~/core/scholar.py:384-497` `compute_authority_scores`, `score_sources` | 대상 선택, 철회 보존, 파일·DB 갱신, 요약 | R-14 R-16 R-17 R-18 |
| C-10 | `~/core/scholar.py:40-94`, `:348-381` `extract_doi`, `backfill_dois` | DOI 추출 정규식·우선순위, 보충 | R-23 |
| C-11 | `~/cli/sources.py:14-253` | `sources` 명령 6개의 옵션·출력 | R-13 R-20 R-24 |
| C-12 | `~/cli/graph.py:294-342` `graph_rank` | `graph rank` | R-08 |
| C-13 | `~/cli/lint.py:200-232` `_check_retracted_citations`, `~/core/runs.py:778-801` | 철회 인용 검사와 ship gate 연결(경계) | R-21 |
| C-14 | `~/cli/repair.py:228-236` | `repair`의 점수 재계산 호출 | R-04 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(원본 테스트는 열지 않음). 손계산이며 실행하지 않았다. 기본 `[ranking]` 설정을 쓴다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 티어 `institutional`만 있고 나머지는 NULL | `0.85`(구성요소가 하나라 그 값 그대로) |
| T-02 | R-01 | 티어 `institutional`, `utility=14`, `authority=NULL`, `centrality=0.5` | 구성요소 `(0.35,0.85)`, `(0.20,14/18≈0.7778)`, `(0.20,0.5)` → `(0.2975+0.1556+0.1)/0.75 ≈ 0.7374` |
| T-03 | R-02 | 어떤 값이든 `is_retracted=1` | `0.05` |
| T-04 | R-02 | 티어·utility·authority·centrality 모두 NULL | `None`(DB에서 NULL) |
| T-05 | R-01 | `utility=30`, `authority=-0.2`, 티어 NULL | 구성요소 `(0.20, 1.0)`, `(0.25, 0.0)` → `0.2/0.45 ≈ 0.4444` |
| T-06 | R-05 R-07 | 노드 `a,b`, 간선 `a→b` | `b`=1.0, `a`≈0.54(정상 상태 해 `x=0.075+0.425y`, `y=0.075+0.85x+0.425y`의 비 `≈0.351/0.649`) |
| T-07 | R-06 | 노트 `s`의 summary가 `Stub for [[s]]`이고 다른 노트가 `[[s]]`를 링크 | `s`는 노드에서 빠지고 간선도 사라지며 `s.centrality_score=0` |
| T-08 | R-06 | `fetch X --suggested-by P`로 생긴 노트 X의 본문에 `[[P]]` | 간선 `X→P`. 다른 조건이 같으면 `P`의 중심성이 `X`보다 높다 |
| T-09 | R-09 R-12 | 노트 `u1.source=http://www.Ex.com/a/?utm_x=1`, `u2.source=https://ex.com/a`, `u1`이 먼저 생성 | 둘 다 `https://ex.com/a`. `u1.independence=1.0`, `u2=0.5`. 클러스터 `{root:"u1", members:["u2"], size:2, kind:"url"}` |
| T-10 | R-12 | 근사 중복 3개짜리 클러스터 | root 1.0, 나머지 둘 각 `0.3333`(합 1.6667) |
| T-11 | R-10 | 본문 앞부분이 모두 `(Reuters) …`와 같은 열 토큰으로 시작하는 노트 두 개 | `wire` 클러스터 하나 |
| T-12 | R-15 R-16 R-17 | DOI 노트, OpenAlex가 `cited_by_count=12`, `is_retracted=false`, venue `Nature` | DB와 frontmatter에 `citation_count=12`, `venue=Nature`, `is_retracted=false`(DB 0). `scored=1`, `retracted=[]` |
| T-13 | R-16 | DB `is_retracted=1`, OpenAlex 장애로 Semantic Scholar만 응답 | `is_retracted=True` 유지. 기존이 0이었다면 NULL로 바뀜 |
| T-14 | R-18 | 인용 수 `[0, 10, 1000]`인 노트 셋 | `authority_score` = `1/3`, `2/3`, `1.0` |
| T-15 | R-19 R-14 | 429가 세 번 연속 | 해당 노트는 `rate_limited`에 들어가고 DB·파일 변경 없음. 다른 노트는 계속 처리 |
| T-16 | R-20 | 이미 `citation_count`가 있는 DOI 노트 5개에 `sources retractions` | 5개 모두 캐시 읽기 없이 조회. 출력 `checked=5`(성공 수), 못 찾은 수는 `unresolved` |
| T-17 | R-21 | 보고서가 `[[bad-paper]]`를 "…[[bad-paper]]…"로만 인용, `bad-paper.is_retracted=1` | `retracted-citations` error. 같은 문장에 "retracted"가 있으면 통과 |
| T-18 | R-23 | `https://doi.org/10.1000/xyz.`, `https://arxiv.org/pdf/2501.01234v2` | `10.1000/xyz`, `arXiv:2501.01234v2` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
`~` = `research/repos/hyperresearch/src/hyperresearch/`, 기준 repo@aece65f.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01(`quality.py:25-53`), C-02(`config.py:106-137`) | 직접 읽음 |
| R-02 | C-01(`quality.py:33-53`) | 직접 읽음 |
| R-03 | C-01(`quality.py:56-75`), `~/core/sync.py:440-444`(sync가 4칼럼을 INSERT 목록에서 뺌) | 직접 읽음 |
| R-04 | C-12, C-09(`scholar.py:489`), C-14, `grep -rn independence`(독립성을 읽는 파이썬 코드는 `cli/sources.py`·`core/independence.py` 뿐) | grep으로 소비처 확인. 스킬 텍스트(`hyperresearch-3-contradiction-graph.md:58`)는 별도 |
| R-05 | C-03(`graphrank.py:21-58`) | 직접 읽음 |
| R-06 | C-03(`graphrank.py:61-95`), C-04, `~/cli/fetch.py:462-475`(breadcrumb), `~/core/sync.py:526-537`(링크 행 생성), vault-store R-15 | 링크 방향은 breadcrumb이 새 노트 본문에 들어가고 `links.source_id`가 본문 소유 노트라는 두 코드의 조합(추론이 아니라 두 곳을 직접 읽어 확인) |
| R-07 | C-03(`graphrank.py:94-105`) | 직접 읽음 |
| R-08 | C-12 | 직접 읽음 |
| R-09 | C-05(`independence.py:32-44`, `:91-97`) | 직접 읽음 |
| R-10 | C-05(`independence.py:26-30`, `:47-58`, `:99-107`) | 직접 읽음 |
| R-11 | C-05(`independence.py:109-118`), C-06, C-02(`DedupSettings.shingle_size`) | 직접 읽음 |
| R-12 | C-05(`independence.py:61-151`) | 직접 읽음 |
| R-13 | C-11(`sources.py:218-253`) | 직접 읽음 |
| R-14 | C-09(`scholar.py:406-449`, `:487-489`) | 직접 읽음 |
| R-15 | C-08 | 직접 읽음. 응답 필드 모양은 미확인 |
| R-16 | C-09(`scholar.py:452-460`) | 직접 읽음 |
| R-17 | C-09(`scholar.py:462-483`) | 직접 읽음 |
| R-18 | C-09(`scholar.py:384-403`) | 직접 읽음 |
| R-19 | C-07 | 직접 읽음 |
| R-20 | C-11(`sources.py:171-215`), C-09 | 직접 읽음 |
| R-21 | `~/skills/hyperresearch.md:266-269`, C-13, `~/core/runs.py:778-801` | 직접 읽음. `verify_run` 전체는 행 9 |
| R-22 | `~/skills/hyperresearch-2-width-sweep.md:226-239` | 스킬 텍스트만 읽음(호스트가 지키는지는 미확인) |
| R-23 | C-10 | 직접 읽음 |
| R-24 | C-11(`sources.py:13-97`) | 직접 읽음 |
| R-25 | `~/search/fts.py:181-190`, `~/core/claims.py:320`, `~/skills/hyperresearch-3-contradiction-graph.md:58`, `~/skills/hyperresearch-10-triple-draft.md:108-112` | 소비 위치만 확인 |
| T-01~T-18 | R-ID와 같은 위치 | 손계산. T-06은 정상 상태 해의 근사(50회 반복·1e-6이면 소수 둘째 자리까지 일치) |

**문서와 구현의 차이**
- `core/independence.py` 머리 주석과 `cli/sources.py:224-228`은 본문 비교를 "MinHash"라 하고 합의 판정에서 `independence`가 "quality composite"에 쓰인다고 쓴다. 구현은 MinHash가 아닌 정확 자카드이며(`independence.py:113-118`, `core/similarity.py`의 `minhash_signature`·`lsh_candidates`는 이 모듈이 부르지 않음), `quality_score` 계산(`quality.py`)은 `independence`를 읽지 않는다(R-04). 코드 확인.
- 3단계 스킬(`hyperresearch-3-contradiction-graph.md:58`)은 "클러스터를 한 표로 센다(독립성 점수 합 ≥ 3.0)"고 쓰지만, 구현의 점수는 root 1.0 + 나머지 각 `1/크기`라 크기 n 클러스터의 합이 `1 + (n−1)/n`(예: 5개면 1.8)이다. 한 표(=1.0)가 아니다. 코드 확인(산술). 스킬이 이를 어떻게 합산하는지는 호스트 프롬프트 층이며 행 6 소관이다.
- `core/graphrank.py` 머리 주석은 중심성이 "여러 독립 연구 사슬이 한 소스로 수렴한 정도"라 하지만, `--suggested-by` breadcrumb이 새 노트 → 제안자 방향 링크라서(R-06) 점수는 많은 노트를 제안한(= 여러 노트에서 링크되는) 소스에 모인다. 제안받은 쪽(새로 가져온 1차 소스)이 아니라 제안한 쪽이다. 코드 확인.
- `core/scholar.py:9-13`·`:473-481`은 `score_sources`가 `citation_count`·`venue`·`is_retracted`를 frontmatter에도 쓴다고 하며 맞다. 다만 이때 노트를 `render_note`로 다시 쓰므로 `NoteMeta`에 없는 키는 소실된다(R-17). 코드 확인.

### 2.2 코드 읽는 순서
`~/core/quality.py`(60줄, 공식 하나) → `~/core/graphrank.py` → `~/core/independence.py`(+`~/core/similarity.py:12-26`) → `~/core/scholar.py`의 `lookup_metadata`·`score_sources`·`compute_authority_scores`(HTTP 계층은 그다음에) → `~/cli/sources.py`·`~/cli/graph.py:294`. 원본의 전략: 점수는 모두 DB 캐시(마크다운 불변)로 두어 언제든 다시 계산하고, API 호출은 `api_cache` TTL로 건너뛰며, 철회는 알 수 없음(NULL)과 아님(0)을 구분해 "모르면 기존 철회를 지우지 않는다"는 쪽으로 보수적으로 갱신한다.
