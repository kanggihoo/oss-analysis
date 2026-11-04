---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/cli/scholar_cmd.py
  - src/hyperresearch/scholar/base.py
  - src/hyperresearch/scholar/registry.py
  - src/hyperresearch/scholar/dedup.py
  - src/hyperresearch/scholar/providers/openalex.py
  - src/hyperresearch/scholar/providers/crossref.py
  - src/hyperresearch/scholar/providers/core_oa.py
  - src/hyperresearch/scholar/providers/repec.py
  - src/hyperresearch/scholar/providers/doab.py
  - src/hyperresearch/scholar/providers/clinicaltrials.py
  - src/hyperresearch/scholar/providers/edgar.py
  - src/hyperresearch/scholar/providers/fred.py
  - src/hyperresearch/models/output.py
  - src/hyperresearch/core/db.py
depends: []
status: ready
---

# 학술 검색 클라이언트 (`hpr scholar search` / `scholar sources`)

> 질의 문자열 하나를 받아 설정된 외부 소스(최대 7개 검색 가능 + RePEc 안내)를 하나씩 조회하고, 응답을 공통 `Paper`로 바꿔 DOI·정규화 제목+연도로 병합한 JSON(또는 텍스트) 목록을 돌려준다.

<!-- 이 문서의 `~`는 research/repos/hyperresearch/src/hyperresearch/ 이다. -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 호출자(호스트 에이전트가 Bash로)가 `hpr scholar search "<질의>" [-s <slug>]... [--scope all|papers] [-n N] [--year-from Y] [--fresh] [-j]`를 실행한다. 호출 지침은 `~/core/agent_docs.py:70-90`("Academic APIs before web search")에 텍스트로 있다.
2. `--scope` 검증(잘못되면 `BAD_SCOPE`로 종료). 레지스트리에서 제공자를 고른다: 범위에 속하고, `--source`가 있으면 그 slug만, 사용 불가(키 없음 등)는 뺀다. 빠진 것의 이유는 `unavailable` 안내 문자열이 된다. 하나도 없으면 `NO_PROVIDERS`로 종료.
3. vault가 있으면 그 SQLite의 `api_cache` 테이블을 캐시로 쓴다(없으면 캐시 없이 진행).
4. 제공자를 레지스트리 순서대로 **하나씩 순차** 호출한다(`provider.search(conn, query, limit, fresh=)`). 각 호출은 호스트별 지연을 지키며 캐시 우선으로 GET한다. 한 제공자가 실패해도 `failed`에 기록하고 계속한다.
5. 모인 `Paper` 전체를 `merge_papers`로 한 작품당 한 레코드로 합친다(레지스트리 순서가 우선순위).
6. `--year-from`이 있으면 연도가 있고 그보다 오래된 레코드를 버린다. `--limit`은 제공자별 상한이며 병합 뒤 자르지 않는다.
7. 결과를 JSON 봉투(`ok/data/count/vault/timestamp`) 또는 사람용 텍스트로 출력한다.

### 1.2 범위·통합 지점 [필수]
- 제공: `scholar search`(다중 소스 병합 검색), `scholar sources`(소스 목록·사용 가능 여부), 공통 결과 형 `Paper`, 소스 8개 클라이언트(OpenAlex, Crossref, CORE, RePEc, DOAB, ClinicalTrials.gov, SEC EDGAR, FRED), 공유 캐시·호스트별 지연, 병합 규칙, `work_type` 부여.
- 제외(경계만):
  - `~/core/scholar.py`의 DOI·arXiv id 기반 인용 수·철회 보강과 DOI 추출·소스 점수화는 행 16(소스 품질)·14 소유다. 이 기능은 "찾기", 그쪽은 "이미 가진 레코드 보강"이다.
  - CORE 전문(fullText) 복구는 행 14(OA 복구) 소유다. 이 기능의 `core_oa.py`가 내보내는 `auth_headers`·`doi_search_url`·`work_url`·`full_text_from_work`·`source_fulltext_urls`·`looks_like_pdf`를 `~/core/oa.py:422-500`이 가져다 쓴다. 이 스펙은 검색 경로(`search_url`·`papers_from_response`)만 다룬다.
  - 검색 결과를 노트로 저장하는 일(행 15 볼트 저장)과 검색 결과로 URL을 가져오는 일(행 11 fetch)은 호출자 몫이다. `scholar search`는 볼트에 노트를 쓰지 않는다.
  - 호출 시점·소스 선택 판단은 행 5(폭 탐색) 등 스킬 텍스트 소유다.
- 외부 의존·선행 계약: 선행 스펙 없음. (1) 네트워크 HTTP GET(`httpx`, 리다이렉트 따라감, 타임아웃 25초). (2) 선택적 SQLite 연결과 `api_cache(url PRIMARY KEY, body, fetched_at)` 테이블(`~/core/db.py:137-141`, 스키마는 행 15 소유; 이 기능은 이 세 컬럼만 쓴다). (3) 환경변수 `HYPERRESEARCH_CONTACT_EMAIL`, `CORE_API_KEY`, `FRED_API_KEY`, `REPEC_API_KEY`. 설정 파일(`config.toml`)의 `ScholarSettings`는 **이 기능에서 쓰이지 않는다**(OA 복구용, 행 14).
- 소유 상태·부작용: `api_cache` 행(성공한 GET의 URL→본문 INSERT OR REPLACE, 즉시 commit)과 프로세스 내 호스트별 마지막 호출 시각 맵 `_last_call`. 그 외 디스크 상태 없음.

### 1.3 인터페이스와 데이터 의미 [필수]

**CLI `hpr scholar search <query>`**

| 옵션 | 타입·기본 | 의미 |
|---|---|---|
| `query`(인자, 필수) | string | 그대로 각 소스에 전달(소스별 변환은 1.4 표) |
| `--source`/`-s` | string 반복, 기본 `[]` | 제공자 slug. 비어 있으면 범위 안 전부. 값은 앞뒤 공백 제거·소문자화해 비교. 모르는 slug는 조용히 무시되고, 결과적으로 선택이 비면 `NO_PROVIDERS` |
| `--limit`/`-n` | int, 20 | **제공자별** 최대 개수. 소스마다 상한으로 잘림(1.4 R-12). 병합 뒤 전체 상한 없음 |
| `--scope` | `all`\|`papers`, `all` | `papers`=openalex·crossref·core·repec·doab만. 그 외 값은 `BAD_SCOPE`(exit 1) |
| `--year-from` | int, 없음 | 연도 있는 레코드 중 이보다 오래된 것을 병합 후 제거. 연도 없는 레코드는 남김 |
| `--fresh` | flag | 캐시 읽기 우회(쓰기는 함) |
| `--json`/`-j` | flag | 봉투 JSON 출력 |

**JSON 출력 `data`** (`success(data, count=len(results), vault=<vault root|없음>)`; `exclude_none`이므로 null 필드는 생략됨)

| 필드 | 의미 |
|---|---|
| `query`, `scope` | 입력 |
| `providers` | 실제 조회한 slug 목록(레지스트리 순서) = 병합 우선순위 |
| `per_source` | slug → 그 제공자가 돌려준 레코드 수(성공한 제공자만; 0건이어도 포함, 예외 난 제공자는 빠짐) |
| `raw_records` / `merged_records` / `returned` | 병합 전 총수 / 병합 후(연도 필터 전) 수 / 최종 `results` 길이. `merged_records`는 `--year-from` 적용 **전** 값이라 `returned`보다 클 수 있다 |
| `cached` | `vault 있음 and not --fresh` (캐시를 읽을 수 있었다는 뜻일 뿐 적중을 뜻하지 않음) |
| `failed` | `[{source, error}]` 예외 난 제공자 |
| `unavailable` | 사용 불가 제공자의 안내 문자열 목록(범위 안 전체 기준) |
| `results` | `Paper.to_dict()` 목록 |

실패 봉투: `{ok:false, error:<메시지>, error_code:"BAD_SCOPE"|"NO_PROVIDERS"}`, 종료 코드 1. 텍스트 모드는 `Error:`와 `skipped — <안내>`를 출력한다.

**`Paper`**(불변): `title`(필수)·`source`(필수, 소스 slug), `url`, `doi`(정규화된 소문자 bare DOI), `year`(int, 1000~2200 밖이면 None), `authors`(문자열 리스트), `venue`, `abstract`, `pdf_url`, `citation_count`(int, 없으면 null), `work_type`(기본 `article`), `identifier`(소스 고유 id), `extra`(문자열→문자열 맵). `to_dict`는 모든 키를 항상 낸다(JSON 봉투에서 None이 생략됨).

`work_type` 어휘: `article, preprint, book, book-chapter, thesis, report, dataset, trial, filing, series, patent, other`.

**CLI `hpr scholar sources [--scope] [-j]`**: 사용 불가 포함 전 제공자 행 `{slug, label, covers, kind("papers"|"specialist"), needs_key, available, reason}`. `kind`는 slug가 `PAPER_SLUGS`에 있느냐로만 정한다.

**환경변수와 소스 가용성**

| slug | 라벨 | 가용 조건 |
|---|---|---|
| openalex | OpenAlex | 항상 |
| crossref | Crossref | 항상 |
| core | CORE | `CORE_API_KEY` 비어 있지 않음 |
| repec | RePEc | 항상 불가(`_SEARCH_METHOD is None`) |
| doab | DOAB | 항상 |
| clinicaltrials | ClinicalTrials.gov | 항상 |
| edgar | SEC EDGAR | `HYPERRESEARCH_CONTACT_EMAIL` 비어 있지 않음(키 아님) |
| fred | FRED | `FRED_API_KEY` 비어 있지 않음 |

`HYPERRESEARCH_CONTACT_EMAIL`은 있으면 모든 요청의 User-Agent를 `hyperresearch (https://github.com/jordan-gibbs/hyperresearch) (mailto:<email>)`로 만들고(없으면 앞 부분만), OpenAlex·Crossref에는 추가로 `mailto=` 쿼리를 붙인다.

### 1.4 행동 규칙과 남은 질문 [필수]

**공통 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `--scope`가 `all`/`papers`가 아님(`search`·`sources` 모두) | 제공자 조회 전에 `BAD_SCOPE` 오류(JSON이면 봉투, 아니면 `Error:` 텍스트), exit 1 | 코드 확인 |
| R-02 | 제공자 선택이 비어 있음(`--source`가 모두 모르는/불가 slug이거나 범위에 가용 소스 없음) | `NO_PROVIDERS` 오류, 메시지는 `--source`가 있으면 "No providers available for --source a, b", 없으면 "No providers available in scope '<scope>'"; 텍스트 모드는 각 `skipped — <안내>` 추가. exit 1 | 코드 확인 |
| R-03 | 제공자 선택 | 레지스트리 순서(openalex, crossref, core, repec, doab, clinicaltrials, edgar, fred)로 정렬된 목록. `--scope papers`는 `PAPER_SLUGS`만. `--source`는 그 slug만(요청 순서는 무시, 중복도 무시). `include_unavailable`이 아니면 `available()`이 False인 것을 제외. 모듈 import·인스턴스화 실패 제공자는 조용히 빠진다 | 코드 확인 |
| R-04 | `search` 실행 중 제공자 호출 | 한 번에 하나씩 순차 호출(스레드·async 없음). `ProviderError`는 `{source, error: str(exc)}`, 그 밖의 예외는 `{source, error: "<타입명>: <메시지>"}`로 `failed`에 담고 다음으로 진행. 실패 제공자는 `per_source`에 없다. 전부 실패해도 `ok:true`에 빈 `results` | 코드 확인 |
| R-05 | 키 없는 제공자(core·fred·edgar·repec) | 선택 단계에서 제거되어 호출되지 않고, `unavailable`에 사유(`"<라벨>: set <ENV> [or ...]"`, edgar는 `SEC EDGAR: set HYPERRESEARCH_CONTACT_EMAIL — ...`, repec은 "RePEc API has no search function ..." 문구)가 남는다. 사유는 `--source` 선택과 무관하게 **범위 안 모든** 사용 불가 제공자에 대해 나온다 | 코드 확인 |
| R-06 | vault 탐색 | 현재 위치에서 vault를 찾으면 그 DB를 캐시로, `vault` 필드에 루트 경로를 넣는다. 없으면 `conn=None`으로 캐시 없이 계속(오류 아님) | 코드 확인 |
| R-07 | 캐시 읽기 | `conn`이 있고 `--fresh`가 아니면 `api_cache`에서 URL로 찾아, `fetched_at`이 30일(`DEFAULT_TTL_DAYS`) 이내면 그 본문을 반환(네트워크·지연 없음). 파싱 불가 `fetched_at`은 미스 취급 | 코드 확인 |
| R-08 | 캐시 미스·`--fresh`의 GET | 호스트(`urlparse(url).netloc.lower()`)별 최소 간격을 지키려 잠든 뒤 GET. 간격표: api.openalex.org·api.crossref.org·data/efts/www.sec.gov 0.15초, api.core.ac.uk·eutils·directory.doabooks.org 0.4, clinicaltrials.gov·api.stlouisfed.org 0.3, api.repec.org 0.5, api.semanticscholar.org 1.1, export.arxiv.org 3.0, 표에 없는 호스트 0.3. 시각 맵은 프로세스 메모리에만 있어 호출 사이에 유지되지 않는다(CLI 한 번 안에서만 유효) | 코드 확인 |
| R-09 | GET 결과 | HTTP 200이 아니거나 예외·타임아웃(25초)이면 `None`(재시도 없음, 오류 구분 없음). 200 본문만 `api_cache`에 `INSERT OR REPLACE` 후 commit. JSON 소스는 파싱 실패 시 `None`. 따라서 네트워크 실패는 `failed`가 아니라 "그 제공자 0건"으로 보인다 | 코드 확인 |
| R-10 | 응답 변환의 방어 | 필드 타입이 틀리면(리스트 자리에 문자열, bool 정수 등) 그 필드만 None/빈값. `as_int`는 bool을 거부. 제목이 없는 레코드는 버려진다(`Paper`는 `title` 필수). 연도 `coerce_year`는 int 또는 문자열 앞 4자리 숫자를 1000~2200에서만 인정 | 코드 확인 |
| R-11 | 병합 | `merge_papers(collected, precedence)`, `precedence`=조회한 slug 순서. 규칙은 R-20~R-24 | 코드 확인 |
| R-12 | `--limit` | 각 제공자에 그대로 전달되고 제공자가 자기 상한으로 `clamp_limit(limit, ceiling)`(1~상한)한다: openalex 200, crossref 100, core 100, doab 100, clinicaltrials 1000, edgar 100, fred 1000. `scholar search` 자체에는 병합 후 상한이 없다 | 코드 확인 |
| R-13 | `--year-from Y` | 병합 **후** `year is None or year >= Y`만 남긴다. `merged_records`는 필터 전 개수 | 코드 확인 |
| R-14 | 출력 순서 | 결과는 `merge_papers`의 정렬(R-24)을 그대로 따른다. 인용 수·관련도 재정렬 없음 | 코드 확인 |

**소스별 요청·변환** (공통: GET만 사용, `fetch_json`/`fetch_text` 경유, 질의는 `urllib.parse.quote` 기본 처리. 질의 앞뒤 공백은 제공자가 제거)

| ID | 소스 | 요청 | 응답 → `Paper` | 검증 수준 |
|---|---|---|---|---|
| R-30 | **openalex** (키 없음) | `GET https://api.openalex.org/works?search=<q>&per-page=<limit≤200>` + `mailto=<email>`(이메일 있을 때). 정렬·유형 필터 인자는 구현에 있으나 CLI는 쓰지 않음(기본 relevance는 `sort`를 보내지 않음). 빈 질의는 `ProviderError` | 응답 `results[]`. `title`=`display_name`∥`title`(없으면 버림). `doi`=정규화. `year`=`publication_year`. `authors`=`authorships[].author.display_name`. `venue`=`primary_location.source.display_name`∥`best_oa_location.source.display_name`. `abstract`=`abstract_inverted_index`를 (위치,단어) 쌍으로 풀어 위치순 공백 결합. `pdf_url`=`best_oa_location.pdf_url`∥`primary_location.pdf_url`. `url`=`primary.landing_page_url`∥`best_oa.landing_page_url`∥`https://doi.org/<doi>`∥OpenAlex id. `citation_count`=`cited_by_count`. `identifier`=id에서 `https://openalex.org/` 접두 제거. `work_type`=`type` 매핑표(C-03), 모르면 `other`. `extra`: `openalex_type`, `oa_status` | 코드 확인 |
| R-31 | **crossref** (키 없음) | `GET https://api.crossref.org/works?query=<q>&rows=<limit≤100>` + `mailto`. 빈 질의는 `ProviderError` | 응답 `message.items[]`. `title`=`title[]` 첫 문자열(없으면 버림), `subtitle`이 제목에 안 들어 있으면 `"제목: 부제"`. `doi`=`DOI`. `year`=`issued`→`published`→`published-print`→`published-online`의 `date-parts` 첫 값, 마지막으로 `created.date-time`. `authors`=`family`가 있으면 `"given family"`, 없으면 조직 `name`. `venue`=`container-title[0]`. `abstract`=JATS XML에서 태그를 공백으로 바꾸고 엔티티 해제, 공백 정리, 구두점 앞 공백 제거, 선행 "Abstract/Summary" 라벨 제거. `pdf_url`=`link[]` 중 `content-type`이 `application/pdf`인 첫 `URL`. `url`=`URL`∥doi.org. `citation_count`=`is-referenced-by-count`. `identifier`=doi. `work_type`=표 C-04, 모르면 `other`. `extra`: `crossref_type`, `publisher` | 코드 확인 |
| R-32 | **core** (`CORE_API_KEY` 필요) | `GET https://api.core.ac.uk/v3/search/works/?q=<q 전체 퍼센트 인코딩>&limit=<≤100>&exclude=fullText`, 헤더 `Authorization: Bearer <key>`. 키가 없으면 `ProviderError("CORE requires an API key in CORE_API_KEY")`(레지스트리가 먼저 걸러 정상 경로에선 닿지 않음) | 응답 `results[]`. `title`(없으면 버림). `doi`=정규화. `year`=`yearPublished`∥`publishedDate`. `authors`=`authors[].name`, 바이트 동일 중복 제거. `venue`=첫 비어있지 않은 `journals[].title`∥`publisher`. `abstract`. `pdf_url`=`downloadUrl`∥`sourceFulltextUrls` 중 PDF처럼 보이는 첫 URL(경로가 `.pdf`로 끝나거나 쿼리에 `pdf`). `url`=`links[type=="display"].url`∥`downloadUrl`∥`https://core.ac.uk/works/<id>`∥doi.org. `citation_count`=`citationCount`(0 포함, 음수·비정수는 None). `work_type`=`documentType`→`fieldOfStudy` 순으로 표 C-05에서 첫 매핑, 없으면 `article`. `identifier`=`id` 문자열. `extra`: `core_id`, `document_type`, `field_of_study`, `data_provider`(첫 `dataProviders[].name`) | 코드 확인 |
| R-33 | **repec** | 요청 없음. `available()`이 항상 False라 선택에서 제외되고 `unavailable` 안내(R-05)로만 보인다. `search()`는 항상 `[]` | 변환 없음. `scholar sources`에서는 `available:false`, `reason`=안내문, `needs_key:true` | 코드 확인 |
| R-34 | **doab** (키 없음) | `GET https://directory.doabooks.org/rest/search?query=<sanitized q>&expand=metadata&limit=<page>&offset=<n>`, 헤더 `Accept: application/json`. 질의 정제: `: ( ) [ ] { } ^ ~ * ? \ / ! \| +`를 공백으로, 대문자 `AND/OR/NOT`는 소문자로, 따옴표 개수가 홀수면 따옴표 전부 제거, 공백 정리. 정제 후 빈 문자열이면 `ProviderError`. 페이징: 요청당 최대 20개, 최대 100개까지 `offset += len(payload)`로 반복, 한 페이지가 요청 크기보다 짧거나 응답이 JSON 배열이 아니면 중단 | 응답=JSON 배열. 건너뜀: `type`이 있고 `"item"`이 아님, `withdrawn=="true"`, 제목 없음. 메타데이터는 `[{key,value}]`를 key→값 리스트로 접어서 읽음. `title`=`dc.title`∥`name`. `authors`=`dc.contributor.author`, 없으면 `dc.contributor.editor`(그때 `extra.authors_are_editors="true"`). `doi`=`oapen.identifier.doi`, 없으면 `dc.identifier` 중 정규식 `10.\d{4,9}/\S+` 첫 매치. `year`=`dc.date.issued`. `venue`=`publisher.name`∥`dc.publisher`. `abstract`=`dc.description.abstract`(공백 정리). `url`=`dc.identifier.uri`∥`https://directory.doabooks.org/handle/<handle>`. `pdf_url`=`oapen.identifier.downloadUrl`이 `.pdf`로 끝날 때만, 아니면 그 값은 `extra.fulltext_url`. `citation_count`=None. `work_type`=`dc.type`(`book`→book, `chapter`→book-chapter), 그 외·없음은 `book`. `identifier`=handle∥doi. `extra`: `editors`, `doab_type`, `language`(`dc.language`), `series`(`dc.relation.ispartofseries`), `isbn`(`dc.identifier.isbn`), `oapen_url`(`dc.identifier` 중 `library.oapen.org/handle/` 포함 항목) | 코드 확인 |
| R-35 | **clinicaltrials** (키 없음) | `GET https://clinicaltrials.gov/api/v2/studies?format=json&countTotal=false&query.term=<q>&pageSize=<limit≤1000>`. 빈 질의는 `[]`(오류 아님) | 응답 `studies[]`. `nctId`와 제목(`briefTitle`∥`officialTitle`) 둘 다 있어야 함. `url`=`https://clinicaltrials.gov/study/<nctId>`. `year`=`statusModule.startDateStruct.date`의 연도. `venue`=`sponsorCollaboratorsModule.leadSponsor.name`. `abstract`=`descriptionModule.briefSummary`. `authors`·`doi`·`citation_count` 없음. `work_type`=`trial`. `identifier`=nctId. `extra`: `nct_id`, `status`(`overallStatus`), `phase`(`designModule.phases`를 `/`로 결합), `study_type`, `enrollment`(정수일 때 문자열), `conditions`(앞 6개를 `; `로), `start_date`, `lead_sponsor`. 모듈이 없거나 잘못된 형이면 빈 dict로 취급 | 코드 확인 |
| R-36 | **edgar** (연락 이메일 필요) | `GET https://efts.sec.gov/LATEST/search-index?q=<q>`. 크기 인자 없음(한 페이지 100건 고정). 이메일이 없으면 요청 없이 `[]`(레지스트리가 먼저 걸러냄). 빈 질의는 `[]` | 응답 `hits.hits[]._source`. 같은 접수번호(accession) 문서는 첫 것만 남기는 중복 제거 후 `limit`(≤100)까지. 접수번호=`_source.adsh`∥`_id`의 `:` 앞부분(없으면 버림); 파일명=`_id`의 `:` 뒤. 제목은 합성: `"<display_names[0] 공백정리> — <form∥root_forms>"`, 둘 다 없으면 `"SEC filing <accession>"`, 신고일(`file_date`)이 있으면 뒤에 `" (filed <date>)"`. `url`=`https://www.sec.gov/Archives/edgar/data/<int(cik)>/<accession에서 - 제거>/<파일명>`(파일명 없으면 `.../<accession>-index.htm`), `ciks` 첫 값이 없거나 정수가 아니면 url None. `year`=신고일 연도. `venue`="U.S. Securities and Exchange Commission (EDGAR)". `abstract`=None. `work_type`=`filing`. `identifier`=accession. `extra`: `accession`, `form`, `company`, `cik`, `filed`, `file_description`, `period_ending` | 코드 확인 |
| R-37 | **fred** (`FRED_API_KEY` 필요) | `GET https://api.stlouisfed.org/fred/series/search?search_text=<q>&api_key=<key>&file_type=json&limit=<≤1000>`. **캐시를 쓰지 않는다**(`fetch_json(None, url)`; `--fresh` 무의미): 키가 URL에 있어 `api_cache`에 평문으로 남기 때문. 키·질의가 비면 `[]` | 응답 최상위 `seriess[]`(철자 그대로). `id`와 `title` 필수. 제목=`title`에 관측 시작·끝이 모두 있으면 `"<title> (<start> to <end>)"`. `url`=`https://fred.stlouisfed.org/series/<id>`. `year`=`observation_start` 연도. `venue`="Federal Reserve Economic Data". `abstract`=`notes`. `work_type`=`series`. `identifier`=id. `extra`: `series_id`, `frequency`, `units`, `seasonal_adjustment`, `observation_start`, `observation_end`, `last_updated`, `popularity`(정수일 때) | 코드 확인 |

**병합 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 각 레코드 | DOI는 `normalize_doi`(doi.org URL·`doi:` 접두 제거, 소문자, 끝의 `.,;` 제거), 제목은 `title_key`(NFKD로 결합 문자 제거 후 소문자, `[^a-z0-9]+` 전부 제거)로 지문화 | 코드 확인 |
| R-21 | 레코드를 입력 순서대로 처리 | (1) 정규화 DOI가 있고 같은 DOI 클러스터가 있으면 거기에 합친다. (2) 아니면 같은 `title_key` 후보 클러스터 중 **DOI 호환**(양쪽 DOI가 있으면 같아야 함; 하나라도 없으면 호환)이고 **연도 호환**(레코드 연도 또는 클러스터 연도들이 비어 있으면 호환, 아니면 클러스터가 아는 연도 중 하나와 차이 ≤1)인 첫 후보에 합친다. (3) 없으면 새 클러스터. DOI가 서로 다르면 제목이 같아도 절대 합치지 않는다 | 코드 확인 |
| R-22 | 클러스터가 DOI를 처음 얻음 | 그 DOI를 `by_doi`에 등록(`setdefault`)해 이후 같은 DOI 레코드가 이 클러스터로 온다. 클러스터의 DOI는 첫 번째 DOI 보유 레코드의 것으로 고정된다 | 코드 확인 |
| R-23 | 클러스터를 한 레코드로 합침 | 멤버를 (정밀도순위=`precedence`에서의 인덱스, 입력 순서)로 정렬해 `primary`=첫 멤버(제목·`source`·`work_type`을 가져옴). 멤버가 하나면 그대로. 필드별: `url`·`doi`·`venue`·`pdf_url`·`identifier`=우선순위 순으로 첫 non-None, `year`=첫 non-None, `authors`=저자 수가 가장 많은 멤버의 것(동수면 우선순위가 앞선 쪽), `citation_count`=non-None 값의 **최댓값**(전부 None이면 None), `abstract`=가장 긴 문자열(동길이면 앞선 쪽), `extra`=전 멤버 dict를 우선순위 낮은 쪽부터 덮어써 높은 쪽이 이기되 한 쪽에만 있는 키도 보존. 서로 다른 `source`가 2개 이상이면 `extra.also_in`=`"openalex,crossref"`처럼 우선순위순 쉼표 결합. `precedence`에 없는 source는 맨 뒤 | 코드 확인 |
| R-24 | 결과 순서 | 클러스터를 (합친 레코드 `source`의 우선순위 인덱스, 클러스터 첫 등장 입력 인덱스)로 정렬. 즉 openalex를 primary로 가진 작품이 먼저, 그 안에서는 입력(제공자 순서·제공자 내 순서) 순. 같은 입력이면 항상 같은 결과 | 코드 확인 |
| R-25 | 합친 레코드의 `doi` | 멤버들의 `Paper.doi` 문자열을 그대로(재정규화 없이) 고른다. 모든 제공자 구현이 이미 정규화해서 내보내므로 실제로는 같다 | 코드 확인 |

**`work_type` 부여**: 소스 자체가 정한다(전역 규칙 없음). openalex·crossref·core는 자기 vocabulary 매핑표(C-03~C-05)와 `other`/`article` 기본값, doab은 `book`/`book-chapter`(기본 `book`), clinicaltrials=`trial`, edgar=`filing`, fred=`series`. 병합 레코드의 `work_type`은 primary 멤버의 값이다(R-23). `--scope papers`는 `work_type`이 아니라 slug 집합(R-03)으로 거른다. | 코드 확인

- 불변식: `Paper`는 불변이고 병합은 새 객체를 만든다. 한 제공자의 실패는 다른 제공자의 결과를 지우지 않는다. 서로 다른 정규화 DOI를 가진 두 레코드는 같은 클러스터에 있을 수 없다. `FRED_API_KEY`는 `api_cache`에 기록되지 않는다.
- 미결정: 없음.
- 확인 한계: 외부 API의 현재 응답 모양과 속도 제한은 확인하지 않았다(코드와 주석의 "2026-09-11 확인" 문구만 근거, FRED는 원본 주석상 실제 키로 검증되지 않았다). 코드를 실행하지 않았다. 원본 테스트(`tests/test_scholar/`)는 파일명만 확인했다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `~/scholar/base.py:157-181` `normalize_doi`, `title_key`, `_DOI_PREFIX_RE`, `_TITLE_STRIP_RE` | DOI·제목 지문 정규화 | R-20 |
| C-02 | `~/scholar/base.py:34-54`, `:213-257`, `:189-210` `_HOST_DELAY`, `_throttle`, `fetch_text`, `_http_get` | 호스트 지연표, 캐시 우선 GET, TTL 30일, 200만 캐시 | R-07~R-09 |
| C-03 | `~/scholar/providers/openalex.py:56-76` `_TYPE_MAP`, `:96-123` `_invert_abstract` | OpenAlex 유형 매핑, 역색인 초록 복원 | R-30 |
| C-04 | `~/scholar/providers/crossref.py:61-91` `_TYPE_MAP`·JATS 정규식, `:109-121` `_strip_jats`, `:145-161` `_year` | Crossref 유형 매핑, 초록 정리, 연도 선택 | R-31 |
| C-05 | `~/scholar/providers/core_oa.py:47-65` `_WORK_TYPES`, `:303-310` `_work_type`, `:336-354` `source_fulltext_urls`·`looks_like_pdf` | CORE 유형 매핑·PDF 추정 | R-32 |
| C-06 | `~/scholar/providers/doab.py:101-125` `_SOLR_SPECIAL_RE`·`_sanitize`, `:127-158` `_metadata`·`_doi` | DOAB 질의 정제, 메타데이터 접기 | R-34 |
| C-07 | `~/scholar/dedup.py:29-185` 전체 | 병합 알고리즘(클러스터, 호환 판정, 필드 선택, 정렬) | R-21~R-24 |
| C-08 | `~/scholar/providers/edgar.py:91-109` `_archive_url`, `:195-206` 제목 합성 | EDGAR URL·제목 조립 | R-36 |

각 C-ID의 파일은 `research/repos/hyperresearch/src/hyperresearch/` 아래다. 나머지 규칙(요청 URL, 필드 대응)은 R-30~R-37 표가 완결적이다.

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열람하지 않음). 네트워크는 `_http_get` 대체물로 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `scholar search x --scope foo -j` | `{ok:false, error:"Unknown scope 'foo'. Use one of: all, papers", error_code:"BAD_SCOPE"}`, exit 1 |
| T-02 | R-02, R-05 | 키·이메일 환경변수 모두 없음, `-s core` | `NO_PROVIDERS`("No providers available for --source core"), exit 1 |
| T-03 | R-05, R-03 | 환경변수 모두 없음, `--scope papers -j` | `providers`=["openalex","crossref","doab"], `unavailable`에 CORE 키 안내와 RePEc 안내 두 줄 |
| T-04 | R-04 | openalex는 200, crossref 호출이 예외 `ValueError("x")` | `failed=[{source:"crossref", error:"ValueError: x"}]`, `per_source`에 openalex만, `ok:true` |
| T-05 | R-09 | crossref가 HTTP 500 | 예외도 `failed`도 아님, `per_source.crossref=0` |
| T-06 | R-21, R-23, R-24 | openalex 레코드 {doi:10.1/a, citation_count:5, abstract:"짧음"}, crossref {doi:"10.1/a", citation_count:3, abstract:"더 긴 초록입니다"} | 1건, source=openalex, citation_count=5, abstract="더 긴 초록입니다", `extra.also_in="openalex,crossref"` |
| T-07 | R-21 | 두 레코드 제목 "Deep Learning: A Review." / "deep learning a review", 연도 2019·2020, DOI 한쪽만 있음 | 병합됨(연도차 1). 연도 2019·2021이면 병합 안 됨 |
| T-08 | R-21 | 같은 제목, DOI 10.1/a 와 10.1/b | 병합 안 됨 |
| T-09 | R-13 | `--year-from 2020`, 연도 2018·None·2021 레코드 | 2018 제거, None·2021 유지. `merged_records`=3, `returned`=2 |
| T-10 | R-37, R-07 | `FRED_API_KEY` 설정, vault 있음 | `api_cache`에 `api_key=`가 들어간 URL 행이 생기지 않음 |
| T-11 | R-34 | 질의 `war AND (peace) "x` | DOAB로는 `war and peace x` 로 전송 |
| T-12 | R-36 | `_id:"0001-23-4:doc.htm"`, `adsh` 없음, `ciks:["0000320193"]` | `accession="0001-23-4"`, url=`https://www.sec.gov/Archives/edgar/data/320193/0001234/doc.htm` |
| T-13 | R-33 | `scholar sources -j` | repec 행 `available:false`, `reason`에 "no search function" 포함, `kind:"papers"` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
경로는 hyperresearch@aece65f의 `src/hyperresearch/` 기준.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-02, R-04, R-06, R-12~R-14 | `cli/scholar_cmd.py:42-167` `scholar_search` (`_SCOPES` :23, `_open_cache` :26-39) | 코드 직접 읽음. 출력 봉투 필드는 `models/output.py:11-28`(`exclude_none`은 `cli/_output.py:27-34`) |
| R-03, R-05 | `scholar/registry.py:22-97` `_REGISTRY`, `PAPER_SLUGS`, `_load`, `get_providers`, `unavailable_notes`; `scholar/base.py:328-339` | 코드 확인 |
| R-07~R-09 | C-02 (`base.py:34-257`) | 코드 확인. 지연표의 semanticscholar·arxiv·eutils 항목은 현재 소스에서 쓰이지 않음 |
| R-10 | `base.py:283-368` 방어 변환 함수들 | 코드 확인 |
| R-11, R-20~R-25 | C-07, C-01 | 코드 확인 |
| R-30 | `providers/openalex.py:160-272` | 코드 확인 |
| R-31 | `providers/crossref.py:201-305` | 코드 확인 |
| R-32 | `providers/core_oa.py:68-127`, `:162-353` | 코드 확인 |
| R-33 | `providers/repec.py:67-119` | 코드 확인 |
| R-34 | `providers/doab.py:195-322` | 코드 확인 |
| R-35 | `providers/clinicaltrials.py:90-184` | 코드 확인 |
| R-36 | `providers/edgar.py:112-235` | 코드 확인 |
| R-37 | `providers/fred.py:72-154` | 코드 확인 |
| `scholar sources` | `cli/scholar_cmd.py:170-219` | 코드 확인 |
| T-01~T-13 | 위 R-ID의 근거 | 모두 구현에서 도출, 실행하지 않음 |

**문서와 구현의 차이**
- README 57행과 feature map은 "소스 8개"라 하지만 실제로 검색 가능한 것은 7개다. RePEc는 `available()`이 항상 False다(`repec.py:84-92`). README 401행은 이를 인정한다.
- feature map·지시문의 "필요 설정"은 환경변수(`CORE_API_KEY`, `FRED_API_KEY`, `HYPERRESEARCH_CONTACT_EMAIL`)뿐이다. `~/core/config.py`의 `ScholarSettings`는 OA 복구(행 14) 설정이며 이 검색 경로에서 읽히지 않는다(`scholar/` 아래에서 `config` import 없음).
- `agent_docs.py:85`의 "ranked list"와 달리 결과는 인용 수·관련도로 재정렬되지 않고 제공자 우선순위·입력 순이다(R-24).
- `scholar sources` 텍스트 모드는 사용 불가를 모두 "needs key"로 표시한다(`scholar_cmd.py:213`). edgar(이메일)·repec(검색 불가)에는 부정확하지만 `reason` 줄이 정확한 이유를 보여 준다.
- OpenAlex·Crossref 제공자는 `sort`/`work_type` 인자를 지원하지만 CLI에서는 어떤 옵션으로도 켤 수 없다(검색 호출이 `provider.search(conn, query, limit, fresh=fresh)` 뿐, `scholar_cmd.py:95`). 호출처는 CLI 하나뿐이다.

### 2.2 코드 읽는 순서 [선택]
`cli/scholar_cmd.py` → `scholar/registry.py` → `scholar/base.py`(Paper·fetch_text·SearchProvider) → `scholar/dedup.py` → `providers/openalex.py`(대표) → 나머지 소스.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| (없음) | 없음 | | |
