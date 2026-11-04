---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/core/oa.py
  - src/hyperresearch/core/scholar.py
  - src/hyperresearch/core/config.py
  - src/hyperresearch/scholar/base.py
  - src/hyperresearch/scholar/providers/core_oa.py
  - src/hyperresearch/cli/fetch.py
  - src/hyperresearch/cli/fetch_batch.py
  - src/hyperresearch/cli/note.py
  - src/hyperresearch/core/agent_docs.py
  - src/hyperresearch/models/note.py
  - src/hyperresearch/core/db.py
  - src/hyperresearch/web/base.py
  - src/hyperresearch/web/pdf.py
  - src/hyperresearch/web/safe_http.py
depends:
  - web-providers.md
  - source-quality.md
  - scholar-search.md
status: ready
---

# OA 전문 복구

> 논문 DOI가 붙은 페이지를 가져왔는데 본문이 얇거나(abstract·paywall 안내문) 아예 읽지 못했을 때, Unpaywall → Europe PMC → CORE 순으로 합법 오픈액세스(OA) 사본을 찾아 그 본문으로 노트를 만들고, 바뀐 사실을 본문 배너·frontmatter `oa_*`·명령 출력에 남긴다. 복구하지 못하면 아무것도 바꾸지 않는다.

<!--
읽은 코드: core/oa.py 전체, core/scholar.py(extract_doi와 _fetch_json·_http_get_json), core/config.py ScholarSettings, scholar/base.py의 env_key·fetch_text·fetch_json, scholar/providers/core_oa.py, cli/fetch.py·cli/fetch_batch.py의 호출 부분, cli/note.py의 note show `oa` 블록, core/agent_docs.py의 OA 안내문.
실행한 것: 없음(읽기만). Unpaywall·Europe PMC·CORE의 실제 응답은 확인하지 못했고 코드가 가정한 필드만 쓴다.
-->

## 1부. 동작 설명

용어를 먼저 정리한다.

- **OA(오픈액세스) 사본**: 저자·저장소·출판사가 무료로 공개한 논문 본문.
- **DOI**: 논문 식별자(`10.xxxx/...`). OA 복구는 DOI가 있어야만 시작한다. arXiv id(`arXiv:...`)도 DOI 자리에 들어오지만 OA 조회 대상이 아니다.
- **치환(substituted)**: 얇은 페이지를 OA 본문으로 바꾼 경우. **구조(rescued)**: 소스를 아예 읽지 못해(403·로그인 벽·봇 벽·fetch 예외) OA 사본만으로 노트를 만든 경우.
- **resolver**: OA 사본의 위치를 알려 주는 외부 API. `unpaywall`·`europepmc`·`core` 셋이다.
- **후보(`OALocation`)**: resolver가 알려 준 사본 하나. `kind`가 본문을 얻는 방법을 정한다: `pdf`(내려받아 pymupdf), `jats`(Europe PMC 구조 XML), `coretext`(CORE 레코드의 `fullText`), `page`(일반 웹 페이지를 provider로).

### 1.1 한눈에 보는 흐름

1. fetch 계층이 DOI를 얻는다(`extract_doi`, R-04). 가져온 결과가 로그인 벽·정크 검사를 통과한 뒤에도 얇으면 `recover_full_text`를, 소스를 읽지 못했거나 벽·정크에 걸렸으면 `rescue_full_text`를 부른다(R-01, R-03).
2. 얇은지는 본문 길이 < `oa_min_full_text_chars`(6000) 이거나 본문 어디에든 paywall 문구가 있는지로 정한다(R-02).
3. 후보를 만든다: Unpaywall(이메일이 설정돼 있을 때만) → Europe PMC → CORE(`CORE_API_KEY`가 있을 때만) 순서(R-05~R-08). 모든 API 응답은 볼트의 `api_cache`에 캐시된다(R-09).
4. 후보를 앞에서부터 보며 URL 안전 검사(`check_oa_url`, R-10)를 통과한 것만 최대 3번(`oa_max_attempts`) 시도한다. 각 시도는 `kind`에 맞게 본문을 얻고 정크가 아니며 "원래 본문보다 길고 6000자 이상"일 때만 채택한다(R-11, R-12).
5. 채택되면 호출자가 `(대체 결과, 후보)`를 받아 노트 본문 맨 위에 배너를 붙이고 `oa_*` frontmatter를 쓰고 출력에 `oa` 블록을 싣는다(R-15~R-17). 채택된 후보가 없거나 어디서든 오류가 나면 호출자가 원래 가진 결과를 그대로 쓴다(R-13).
6. 나중에 `note show`가 DB의 `oa_*` 열로 `oa` 블록을 구조적으로 보여 준다(R-19).

### 1.2 범위·통합 지점

- 제공: 복구 조건 판정, 후보 순회와 선택, JATS→마크다운 변환, 대체 사실 표시(배너·frontmatter·출력 필드), 복구 실패 시 무변경.
- 제외(경계만):
  - 웹 provider·PDF lane·SSRF 관문: [web-providers](web-providers.md)가 제공한다. 이 스펙은 `fetch_pdf(url, fetch_settings)`(성공 시 `WebResult`+`raw_bytes`, 실패는 None, 인증서 거부는 예외), `provider.fetch(url)`, `WebResult.looks_like_junk(junk_gates)`, `safe_get`·`check_url`을 그 계약대로 쓴다.
  - fetch 흐름 전체(중복 거부, 로그인 벽·정크 판정, 노트 쓰기): [fetch-engine](fetch-engine.md). 이 스펙은 복구 호출 지점의 입력·출력만 정의한다.
  - 학술 API 캐시·HTTP 계층: `core/scholar.py`의 `_fetch_json`·`_http_get_json`(소스 품질 점수와 공유)과 `scholar/base.py`의 `fetch_json`(학술 검색 클라이언트와 공유)은 입력(URL, TTL, 헤더) → 출력(JSON 또는 None, 429가 예산을 넘으면 `RateLimitedError`)과 `api_cache` 사용을 C-ID로 가져가기만 하고 풀어 쓰지 않는다. [scholar-search](scholar-search.md), capabilities/source-quality.md.
  - 노트 스키마·DB(`notes.oa_*` 열, `api_cache` 테이블): [vault-store](vault-store.md). 이 스펙은 `oa_*` 필드 이름과 값만 정한다.
- 외부 의존: `[scholar]` 설정, 환경변수 `CORE_API_KEY`, 볼트 DB 연결(`vault.db`)과 `vault.config.ranking.api_cache_ttl_days`(기본 30일), `vault.config.fetch`·`vault.config.junk`, 호출자가 만든 web provider `prov`(없으면 `page` 후보를 건너뜀).
- 소유 상태·부작용: 노트·파일을 직접 쓰지 않는다(호출자가 쓴다). 부작용은 `api_cache` 행 추가·교체(Unpaywall·Europe PMC·CORE 검색 응답)와 PDF lane의 전역 실패 기억(web-providers)뿐이다. CORE `/works/{id}` 본문과 JATS 본문은 캐시하지 않는다.

### 1.3 인터페이스와 데이터 의미

**설정 `[scholar]`**(`ScholarSettings`, C-05)

| 키 | 기본값 | 의미 |
|---|---|---|
| `oa_recovery` | `true` | 끄면 복구·구조 모두 하지 않는다. |
| `contact_email` | `""` | Unpaywall 약관상 필요한 연락 이메일. 비면 Unpaywall을 건너뛴다. |
| `oa_min_full_text_chars` | `6000` | "얇다"의 기준이자 후보를 채택하는 최소 길이. |
| `oa_prefer_published` | `true` | Unpaywall 후보를 출판본 > 수락본 > 제출본 순으로 정렬. |
| `oa_max_attempts` | `3` | 한 번의 복구에서 시도할 후보 수(검사를 통과한 것만 센다). |
| `oa_rescue_blocked` | `true` | 소스를 아예 읽지 못한 경우에도 시도(구조). |

**환경변수** `CORE_API_KEY`: 호출 시점마다 읽는다. 없으면 CORE를 조용히 건너뛴다.

**`OALocation`**(C-06): `url`, `resolver`(`unpaywall`|`europepmc`|`core`), `kind`(`pdf`|`jats`|`coretext`|`page`), `version`(`publishedVersion`|`acceptedVersion`|`submittedVersion`|None), `license`(None 가능), `host_type`(`publisher`|`repository`|None). `is_version_of_record`는 `version == "publishedVersion"`.

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `recover_full_text(vault, prov, url, doi, result)` | → `(result, location)` | 치환 시도. `location`이 None이면 `result`는 인자 그대로다. 예외를 던지지 않는다. |
| `rescue_full_text(vault, prov, url, doi)` | → `(result, location)` 또는 `(None, None)` | 구조 시도. 읽은 결과가 없으므로 이길 기준 길이는 0. |
| `needs_oa_recovery(result, settings)` | → bool | R-02. |
| `iter_oa_candidates(conn, doi, ttl_days, *, email, prefer_published, fresh)` | → `OALocation` 제너레이터 | 앞이 더 좋은 후보. |
| `check_oa_url(url)` | → `(ok, reason)` | R-10. |
| `jats_to_markdown(xml_text)` | → string 또는 None | R-14. |
| `recovery_notice(loc, original_url, original_chars, *, blocked_reason=None)` | → string | 본문 앞에 붙일 배너(끝에 개행 하나). |
| `oa_frontmatter(loc, *, kind)` | → map | `oa_*` frontmatter 필드. |

**노트 frontmatter `oa_*`**(S2의 일부, 소유는 vault-store): `oa_url`(본문이 실제로 온 곳), `oa_source`(resolver), `oa_recovery_kind`(`substituted`|`rescued`), 값이 있을 때만 `oa_version`·`oa_license`. 이 필드가 있어도 `source`는 요청한 URL 그대로다.

**명령 출력의 `oa` 필드**: `fetch`(`data["oa"]`): `url`, `resolver`, `version`, `license`, `replaced_chars`(치환 전 본문 글자 수, 구조는 0), `kind`, `nothing_from_source`(구조일 때 true), `blocked_reason`(구조일 때 이유). `fetch-batch`: 각 `notes_created[]` 항목에 같은 필드(`replaced_chars` 제외), 최상위에 `oa_recovered`(복구 노트 수)·`oa_rescued`(그중 구조 수). 복구가 없으면 `oa` 키가 없다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `recover_full_text` 호출 | `vault.config.scholar`가 없거나 `doi`가 비었거나 `needs_oa_recovery`가 false면 `(result, None)`을 돌려준다. 아니면 후보를 시도(R-11)하고, 채택하면 `(recovered, loc)`, 아니면 `(result, None)`. 기준 길이는 `len(result.content)`. | 코드 확인 |
| R-02 | `needs_oa_recovery(result, settings)` | 순서대로: `oa_recovery`가 꺼져 있으면 false → `raw_content_type == "application/pdf"`면 false(이미 전문으로 간주) → `len(content) < oa_min_full_text_chars`면 true → 소문자 본문 **전체**에 paywall 문구 9개 중 하나라도 있으면 true → false. 문구: `purchase pdf`, `buy this article`, `purchase this article`, `rent this article`, `purchase access`, `subscribe to access`, `sign in to continue reading`, `access through your institution`, `get access to the full`. 오탐은 캐시된 API 호출 한 번이라는 비용으로 허용한다. | 코드 확인 |
| R-03 | `rescue_full_text` 호출 | `scholar` 설정이 없거나 `doi`가 비었거나 `oa_recovery` 또는 `oa_rescue_blocked`가 꺼져 있으면 `(None, None)`. 아니면 후보를 시도(기준 길이 0, 대체 제목 None). | 코드 확인 |
| R-04 | `extract_doi(url, raw_html, content)` | 우선순위: ① 호스트에 `doi.org`가 있고 경로에서 `10.\d{4,9}/…` 정규식이 맞으면 그 DOI ② URL에서 `arxiv.org/(abs\|pdf)/NNNN.NNNNN(vN)` → `arXiv:<id>` ③ `raw_html`의 `citation_doi`·`dc.identifier` 메타 태그의 `10.…` ④ `content` 앞 20000자의 `DOI:` 표지 뒤 DOI. 아무것도 없으면 None. 결과는 앞뒤 공백·끝의 `.,;` 제거. 구조 시도에서는 호출자가 `content`를 넘기지 않아 ①~③만 쓴다(막힌 페이지 본문에는 믿을 DOI가 없으므로). | 코드 확인 |
| R-05 | `iter_oa_candidates(doi,…)` | `doi`가 비었거나 `arxiv:`로 시작하면(대소문자 무시) 후보 없음. 아니면 순서대로: Unpaywall 후보들(이메일이 있을 때만) → Europe PMC 후보(최대 1개) → CORE 후보들(키가 있을 때만). 단 호출자 `_try_candidates`는 `list(...)`로 한꺼번에 소비하므로 세 resolver 조회가 모두 먼저 일어나고, 그 과정의 어떤 예외든 후보 전체를 버리고 `(None, None)`이 된다(2.1). | 코드 확인 |
| R-06 | Unpaywall 후보 | URL `https://api.unpaywall.org/v2/<quote(doi, safe='')>?email=<quote(email)>`을 `_fetch_json`으로 조회(429 소진은 후보 없음). 응답이 없거나 `is_oa`가 거짓이면 없음. 위치 목록 = `best_oa_location`(있으면 맨 앞) + `oa_locations`(중복 제외). 정렬 키 `(PDF URL 없음 ? 1 : 0, prefer_published일 때 version 순위 published 0·accepted 1·submitted 2·그 외 3, 아니면 0)`의 안정 정렬. 그 순서로 먼저 모든 위치의 `url_for_pdf`를 `kind="pdf"`로, 이어서 모든 위치의 `url`을 `kind="page"`로 내되 같은 URL은 한 번만. 각 후보는 `resolver="unpaywall"`, 위치의 `version`·`license`·`host_type`(빈 값은 None). | 코드 확인 |
| R-07 | Europe PMC 후보 | URL `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"<doi>"(퍼센트 인코딩)&format=json&resultType=core&pageSize=1`. 첫 결과의 `isOpenAccess == "Y"`이고 `pmcid`가 있어야 한다. 후보는 `url=…/rest/<pmcid>/fullTextXML`, `kind="jats"`, `version="publishedVersion"`(Europe PMC가 출판본만 서빙한다는 가정), `license=결과.license`, `host_type="repository"`. `/fullTextPDF`는 404라서 쓰지 않는다. | 코드 확인(서비스 가정은 주석 근거) |
| R-08 | CORE 후보 | `CORE_API_KEY`가 없거나 `scholar.providers.core_oa` import가 실패하면 없음. `fetch_json`으로 `https://api.core.ac.uk/v3/search/works/?q=doi:"<doi>"&limit=1&exclude=fullText`(헤더 `Authorization: Bearer <key>`, TTL·캐시 사용)을 조회해 첫 결과 `rec`를 쓴다(예외·비-dict·빈 결과는 후보 없음). `version`은 `documentType`·`fieldOfStudy`에 `preprint`가 있으면 `submittedVersion`, 아니면 None(출판본이라고 짐작하지 않음). `license`는 `rec.license` 문자열이면 그것, 아니면 None. 후보 순서: ① `rec.id`로 `…/v3/works/<id>`, `kind="coretext"` ② `rec.downloadUrl`(비지 않을 때) `kind="pdf"` ③ `rec.sourceFulltextUrls`를 `looks_like_pdf`(경로가 `.pdf`로 끝나거나 쿼리에 `pdf`)이면 `pdf` 아니면 `page`. 같은 URL은 한 번. 모두 `resolver="core"`, `host_type="repository"`. | 코드 확인 |
| R-09 | resolver API 호출 | Unpaywall·Europe PMC는 `core/scholar._fetch_json`, CORE 검색은 `scholar/base.fetch_json`을 쓴다. 둘 다 캐시 우선(`api_cache` URL 키, `ranking.api_cache_ttl_days` 이내면 캐시 응답), 캐시가 없으면 호스트별 최소 간격을 두고 요청한다. 성공한 응답만 캐시한다. `_fetch_json`은 429를 최대 3번 시도(Retry-After가 0~60초면 그만큼, 아니면 2초·4초 대기)하고 소진하면 `RateLimitedError`, 그 밖의 실패는 None. `RateLimitedError`는 "이 resolver에는 후보가 없다"로 처리된다. 요청 User-Agent는 `hyperresearch (mailto:research@example.com)`(고정 문자열, Unpaywall 쿼리의 `email`과 별개). | 코드 확인 |
| R-10 | `check_oa_url(url)` | 거부(`(False, 이유)`): 파싱 불가 / 스킴이 `http`·`https`가 아님 / userinfo(`user:pw@`) 포함 / 호스트 없음 / 호스트에 `.`이 없고 IP 리터럴도 아님(`localhost`, `metadata`) / `check_url(url)`이 `SafeHTTPError` 또는 `OSError`(사설·예약 주소, 파서 불일치, DNS 실패). 사용자의 `allow_private_hosts`는 적용하지 않는다(내부 미러는 OA 위치가 될 수 없다). 통과하면 `(True, "")`. | 코드 확인 |
| R-11 | `_try_candidates` 순회 | 후보를 순서대로 보며, 후보마다 먼저 시도 횟수가 `oa_max_attempts`에 이미 도달했는지 보고 도달했으면 순회를 끝낸다. 그다음 `check_oa_url`을 부르고, 거부는 경고 로그만 남기고 시도 횟수에 세지 않고 다음 후보로 간다. 통과한 후보는 시도 횟수를 1 올리고 시도한다. 본문 획득(R-12)이 예외이거나 None이면 다음 후보. `looks_like_junk(junk_gates)`가 사유를 주면 다음 후보. 길이 `L = len(content)`가 기준 길이 이하면 다음 후보("줄어들면 안 된다"), `L < oa_min_full_text_chars`여도 다음 후보("레코드 페이지가 전문 행세를 못 하게"). 둘을 모두 넘는 첫 후보를 `(result, loc)`로 채택. 끝까지 없으면 `(None, None)`. | 코드 확인 |
| R-12 | 후보 `kind`별 본문 획득 | `pdf`: `web.pdf.fetch_pdf(loc.url, vault.config.fetch)`(SSRF 관문·크기·TLS는 web-providers 규칙, 실패는 None). `jats`: `safe_get(url, max_bytes=25MiB, timeout=60, User-Agent 위 고정 문자열)`가 상태 200이면 본문 텍스트를 `jats_to_markdown`으로 변환(실패면 None), 결과 `WebResult(url=loc.url, title=…, content=마크다운)`. 제목은 마크다운 첫 줄이 `# `로 시작하면 그것, 아니면 호출자가 준 대체 제목, 그것도 없으면 `"Untitled"`. `coretext`: 키를 다시 읽어 `fetch_json(None, url, headers=…)`(캐시 없음)으로 `/works/{id}`를 받아 `fullText`를 본문으로 쓴다. 비었거나 CORE의 비인증 자리표시 문구(`not available for public api users`로 시작, 대소문자 무시)면 None. 제목은 응답 `title`(비어 있지 않으면) 아니면 대체 제목 아니면 `"Untitled"`. `page`: `prov`가 있으면 `prov.fetch(loc.url)`, 없으면 이 후보를 건너뜀. jats·coretext의 `WebResult`는 `fetched_at`이 생성 시각이다. | 코드 확인 |
| R-13 | 불변식: 복구는 fetch를 실패시키지 않는다 | `recover_full_text`/`rescue_full_text`는 어떤 오류에도 예외를 던지지 않고 호출자가 가진 결과를 그대로 둔다. 구조는 실패를 노트로 바꾸기만 하고 반대는 없다. 치환은 본문을 줄이지 않는다(R-11). | 코드 확인(구조 시도 중 `list(iter…)`·후보 순회의 예외는 잡지만, `settings` 읽기 같은 앞부분 예외는 호출자에게 갈 수 있다는 가능성은 추론) |
| R-14 | `jats_to_markdown(xml)` | XML 파싱 실패는 None. 출력은 줄 목록을 `\n`으로 이은 문자열(앞뒤 공백 제거, 비면 None): ① `.//front//article-title` 텍스트가 있으면 `# 제목` ② `.//front//abstract`가 있으면 `## Abstract`와 그 안의 모든 `<p>`(비지 않은 것) ③ 루트 바로 아래 `<body>`가 없으면 여기서 끝, 있으면 깊이 2부터 순회: `<sec>`은 직계 `<title>`이 있으면 `#`×min(깊이,6)+제목, 자식 `<sec>`은 깊이+1로 재귀; `<p>`·`<disp-quote>`는 한 줄 단락; `<fig>`·`<table-wrap>`은 `<caption>`을 `*캡션*`; `<list>`는 모든 `<list-item>`을 `- 항목`으로 쓰고 뒤에 빈 줄. 참고문헌·이해상충 등 뒷부분은 버린다. 블록 텍스트는 하위 텍스트를 이어 모은 뒤 공백을 하나로 접는다. `xref`·`label`·`table-wrap-foot`·`fn`·`graphic`·`media` 요소는 하위 내용만 버리고 뒤따르는 텍스트(tail)는 유지한다. | 코드 확인 |
| R-15 | 대체 배너 `recovery_notice` | 마크다운 인용(`> `) 줄들 뒤에 개행 하나. 치환(`blocked_reason` 없음): `> [!] **Open-access full text substituted.**`, `> The body below is **<what>**, retrieved from <<url>> via <resolver>.`, `> It is NOT the content of <원 URL>, which returned only <N:,> characters (an abstract or paywall page).`. 구조(`blocked_reason` 있음): `> [!] **Recovered from an open-access copy. The source URL was never read.**`, `> <원 URL> could not be retrieved (<이유 한 줄>).`, `> Everything below — including the title and author metadata — is **<what>**, retrieved from <<url>> via <resolver>. NOTHING in this note came from the source URL.`. 공통으로 `license`가 있으면 `> Licence reported by <resolver>: \`<license>\`.`, `version`이 `publishedVersion`이 아니면(미상 포함) `> **Quote this source with care** — …` 한 줄. `<what>`은 version별 문구(출판본 / 수락본 / 제출 프리프린트 / "an open-access copy of unrecorded version"), 이유 문장은 줄바꿈을 공백으로 접고 160자 초과 시 159자+`…`로 자른다(인용 블록이 깨지지 않게). 문구 원문은 C-10. | 코드 확인 |
| R-16 | `oa_frontmatter(loc, kind)` | `{"oa_url": loc.url, "oa_source": loc.resolver, "oa_recovery_kind": kind}`에 `loc.version`이 있으면 `oa_version`, `loc.license`가 있으면 `oa_license`를 더한다. | 코드 확인 |
| R-17 | 호출자(`fetch`)의 복구 배치 | 구조: fetch가 예외를 던졌을 때(이유 `fetch failed: <예외>`, DOI는 URL에서만), 로그인 벽일 때(`login wall: <제목>`, DOI는 URL+`raw_html` 메타), 정크일 때(이유 = 정크 사유, 같은 DOI 규칙) 시도한다. 성공하면 이후의 로그인 벽·정크 검사는 건너뛰고 구조 결과로 노트를 만든다. 치환: 두 검사를 통과한 결과에 `extract_doi(url, raw_html, content)`로 DOI를 얻어 `recover_full_text`를 부른다(그래서 300자 미만 얇은 페이지는 정크로 먼저 걸려 치환이 아니라 구조 경로를 탄다). 채택되면 노트의 `source`·`source_domain`은 요청 URL 쪽(구조는 URL의 netloc)을 유지하고, 제목·본문·`fetched_at`·`content_hash`·단어 수·`raw_bytes`(PDF 후보일 때)는 복구된 `WebResult` 것을 쓴다. 본문은 `[suggested-by 빵부스러기] + 본문` 앞에 배너를 붙인다. `fetch-batch`는 정크 검사가 없으므로 구조는 fetch 예외·로그인 벽에서만, 치환은 DOI가 있는 모든 결과에서 한다(상세는 fetch-engine). | 코드 확인 |
| R-18 | 구조·치환의 title/author | 호출자가 노트 제목을 `--title`, 복구 결과의 `title`, URL 마지막 경로 조각, `"Untitled"` 순으로 고르므로, 치환에서도 제목은 원래 소스가 아니라 복구 본문에서 온 값이 된다(PDF는 첫 쪽의 10자 넘는 첫 줄, JATS는 article-title, CORE는 레코드 `title`, 웹 페이지는 그 페이지 제목). 작성자(`author` 메타데이터)는 노트에 저장되지 않는다. | 코드 확인 |
| R-19 | `note show`의 `oa` 블록 | 노트 행의 `oa_url`이 비어 있지 않으면 `data["oa"] = {url, resolver(=oa_source), version, license, body_is_not_from_source: true, kind(=oa_recovery_kind), nothing_from_source: kind == "rescued"}`. 이 블록은 `<untrusted-source>` 울타리 밖에 있고, 본문 속 배너는 울타리 안에 있다. 에이전트용 안내문은 `oa` 블록을 권위 있는 쪽으로 읽으라고 한다. | 코드 확인 |

- 불변식: 복구는 가져온 결과를 줄이지 않는다. 복구가 일어났다면 `oa_*` frontmatter·배너·출력의 `oa`가 항상 함께 있다. 복구가 없으면 셋 다 없다. 호출자가 DOI를 건네지 않으면 복구는 시작하지 않는다.
- 미결정: 없음.
- 확인 한계: Unpaywall·Europe PMC·CORE의 실제 응답 필드(`is_oa`, `oa_locations[].url_for_pdf`, `resultList.result[].isOpenAccess`·`pmcid`, CORE `results[].downloadUrl`·`sourceFulltextUrls` 등)는 코드가 가정한 이름이고 웹 검색으로 대조하지 않았다. 코드를 실행하지 않았다.

### 1.5 필수 코드 참조

라이선스: MIT(인용 가능). 경로는 `repos/hyperresearch/src/hyperresearch/` 기준이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `core/scholar.py:40-94` `DOI_RE`·`ARXIV_URL_RE`·`META_DOI_RE`·`BODY_DOI_RE`·`_clean_doi`·`extract_doi` | DOI 추출 정규식과 우선순위 | R-04 |
| C-02 | `core/oa.py:83-101` | version 순위표, paywall 문구 | R-02, R-06 |
| C-03 | `core/oa.py:133-179` `check_oa_url`·`_is_ip_literal` | 후보 URL 거부 규칙 | R-10 |
| C-04 | `core/oa.py:187-207` `needs_oa_recovery` | 복구 조건 | R-02 |
| C-05 | `core/config.py:163-194` `ScholarSettings` | `[scholar]` 키·기본값, 읽기는 `config.py:312` | R-01, R-03 |
| C-06 | `core/oa.py:104-125` `OALocation` | 후보 자료형 | R-05~R-08 |
| C-07 | `core/oa.py:215-348` `iter_oa_candidates`·`_unpaywall_candidates`·`_resolve_europepmc` | 후보 순서·URL·정렬 | R-05~R-07 |
| C-08 | `core/oa.py:355-476` `_core_*`·`_core_candidates`, `scholar/providers/core_oa.py:104-138`, `:141-159`, `:336-354` | CORE 후보·URL 구성·자리표시 문구·pdf 모양 판정 | R-08, R-12 |
| C-09 | `core/oa.py:479-632` `_fetch_core_text`·`_http_get_text`·`_jats_block_text`·`jats_to_markdown` | CORE 본문, JATS 변환 | R-12, R-14 |
| C-10 | `core/oa.py:639-727` `_VERSION_PROSE`·`_one_line`·`recovery_notice`·`oa_frontmatter` | 배너 문구 원문, frontmatter 필드 | R-15, R-16 |
| C-11 | `core/oa.py:735-882` `_fetch_jats`·`_try_candidates`·`recover_full_text`·`rescue_full_text` | 순회·채택 기준·진입점 | R-01, R-03, R-11~R-13 |
| C-12 | `core/scholar.py:52-60`, `:102-120`, `:198-276` `_HOST_DELAY`·`RateLimitedError`·`_http_get_json`·`_fetch_json` | 캐시 우선 JSON 조회, 429 재시도, 호스트 간격 | R-09 |
| C-13 | `scholar/base.py:80-86`, `:189-275` `env_key`·`_http_get`·`_throttle`·`fetch_text`·`fetch_json` | CORE 호출용 캐시 우선 조회(헤더 지원) | R-08, R-09 |
| C-14 | `cli/note.py:199-221` | `note show`의 `oa` 블록 | R-19 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(코드를 실행하지 않고 읽어서 정함). API 응답은 가정한 모양의 대체값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `oa_min_full_text_chars=6000`. 본문 5999자 / 본문 6000자(paywall 문구 없음) / 본문 20000자이고 중간에 `Purchase this article` / `raw_content_type="application/pdf"`인 100자 본문 / `oa_recovery=false`인 100자 본문 | true / false / true / false / false. |
| T-02 | R-05 | `doi="arXiv:2501.01234"` 또는 `""` | 후보 없음. `recover_full_text`는 `(result, None)`. |
| T-03 | R-05, R-06 | `contact_email` 비어 있음, `CORE_API_KEY` 없음, DOI가 Europe PMC OA(`isOpenAccess="Y"`, `pmcid="PMC123"`) | 후보 하나: `…/PMC123/fullTextXML`, `jats`, `publishedVersion`. |
| T-04 | R-06 | Unpaywall 응답: `best_oa_location` A(PDF 없음, 출판본, url `a`), `oa_locations`에 B(PDF `b.pdf`, 제출본), C(PDF `c.pdf`, 출판본) | 정렬 결과 [C, B, A]. 후보 순서: `c.pdf`(pdf), `b.pdf`(pdf), 이어서 각 위치의 `url`(page)을 C, B, A 순으로. `oa_prefer_published=false`면 정렬 키의 두 번째 값이 모두 0이라 [B와 C(둘 다 PDF 있음, 원래 순서 B, C), A]가 된다. |
| T-05 | R-11 | 원래 본문 2000자. 후보1 본문 150자 / 후보2 5000자 / 후보3 40000자 | 후보1(정크 판정: 300자 미만), 후보2(6000자 미만)는 건너뛰고 후보3 채택. |
| T-06 | R-11 | 검사를 통과한 후보 4개가 모두 HTTP 403 | 3번째까지 시도 후 중단, 4번째는 시도하지 않음. `(None, None)`. 검사에서 거부된 후보는 3번에 안 셈. |
| T-07 | R-10 | `check_oa_url("http://user:pw@example.org/p.pdf")`, `("http://metadata/x")`, `("ftp://x.org/a")`, `("http://10.0.0.5/a.pdf")` | 각각 `(False, "credentials embedded in URL")`, `(False, "non-public hostname 'metadata'")`, `(False, "scheme 'ftp' is not http(s)")`, `(False, "refusing URL … non-public address 10.0.0.5")`. |
| T-08 | R-14 | `<p>Widgets matter <xref>[1]</xref> a great deal.</p>`가 `body` 아래 | 한 줄 `Widgets matter a great deal.`(xref 텍스트는 사라지고 tail은 남음). |
| T-09 | R-15, R-16 | 치환, `loc=OALocation(url="https://x.org/p.pdf", resolver="unpaywall", kind="pdf", version="acceptedVersion", license="cc-by")`, 원 URL `https://pub.com/a`, 원 본문 1800자 | 배너 첫 줄 `> [!] **Open-access full text substituted.**`, `1,800 characters`, `Licence reported by unpaywall: \`cc-by\`.`, `Quote this source with care` 줄 포함. frontmatter 추가: `oa_url`, `oa_source: unpaywall`, `oa_recovery_kind: substituted`, `oa_version: acceptedVersion`, `oa_license: cc-by`. |
| T-10 | R-15, R-17 | 구조: 소스 fetch가 `HTTP 403 fetching …`으로 실패해 OA 후보가 채택됨 | 배너 첫 줄 `> [!] **Recovered from an open-access copy. The source URL was never read.**`, 둘째 줄에 `could not be retrieved (fetch failed: HTTP 403 …)`. `oa_recovery_kind: rescued`, 명령 출력 `oa.nothing_from_source: true`, `replaced_chars: 0`. |
| T-11 | R-12 | CORE `/works/{id}` 응답의 `fullText`가 `"Not available for public API users."` | 본문 None이라 이 후보는 건너뛰고 다음 후보로. |
| T-12 | R-13, R-17 | 복구 후보가 없고 소스는 얇은 페이지(2000자)를 정상 반환 | 노트는 원래 얇은 본문 그대로, `oa_*`·배너·출력 `oa` 모두 없음. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@aece65f) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-11(`oa.py:835-856`) | 직접 읽음. |
| R-02 | C-04, C-02 | 직접 읽음. |
| R-03 | C-11(`oa.py:859-882`) | 직접 읽음. |
| R-04 | C-01, `cli/fetch.py:335-350`, `:411-416`, `cli/fetch_batch.py:173` | 정규식과 호출 인자를 직접 읽음. |
| R-05 | C-07, C-11(`:765-776`) | 직접 읽음. **문서와 구현의 차이**: `iter_oa_candidates` docstring과 모듈 docstring은 "Europe PMC와 CORE는 앞 resolver가 소진됐을 때만 지연 조회한다(each extra API call only happens when every earlier resolver's copies have been exhausted)"고 쓰나, `_try_candidates`는 `list(iter_oa_candidates(...))`로 즉시 모두 소비한다(`oa.py:765-776`). 즉 Unpaywall 후보가 채택되더라도 Europe PMC·CORE 조회가 먼저 일어난다. 결과 선택은 달라지지 않는다(캐시되는 호출만 늘어난다). 구현을 사실로 썼다. |
| R-06 | C-07(`oa.py:265-313`) | 직접 읽음. 응답 필드 이름은 가정. |
| R-07 | C-07(`oa.py:316-348`) | 직접 읽음. |
| R-08 | C-08 | 직접 읽음. |
| R-09 | C-12, C-13 | 직접 읽음. 두 HTTP 계층이 별개(재시도·리다이렉트·헤더 방식이 다름)라는 점은 코드 차이다: `core/scholar.py`는 수동 리다이렉트·429 재시도, `scholar/base.py`는 `follow_redirects=True`·재시도 없음. |
| R-10 | C-03 | 직접 읽음. `check_url` 규칙은 web-providers R-09. |
| R-11 | C-11(`oa.py:753-832`) | 직접 읽음. `looks_like_junk`가 첫 2000자의 "cloudflare", "captcha", "access denied" 같은 단어에도 걸리므로(web-providers·fetch-engine) OA 본문이 이런 단어로 시작하면 거부된다는 귀결은 코드에서 따라간 것이다. |
| R-12 | C-09, C-08, C-11(`oa.py:735-750`) | 직접 읽음. |
| R-13 | `core/oa.py:38-53`(불변식 선언), C-11 | 불변식은 주석 선언이고, `recover_full_text` 안의 try/except는 `_try_candidates` 안에만 있다. `scholar` 설정이 없거나 `needs_oa_recovery`가 예외를 던지는 경우는 보호되지 않는다(`getattr(vault.config, "scholar", None)` 후 바로 호출). 그런 예외 경로는 현실적으로 없다고 추론. |
| R-14 | C-09(`oa.py:546-632`) | 직접 읽음. |
| R-15 | C-10(`oa.py:639-711`) | 문구는 원문 그대로 인용 가능(라이선스). |
| R-16 | C-10(`oa.py:714-727`) | 직접 읽음. |
| R-17 | `cli/fetch.py:318-350`, `:352-361`, `:363-409`, `:414-434`, `:436-502`, `:634-669`, `cli/fetch_batch.py:154-272`, `:325-359` | 직접 읽음. 호출 순서의 상세는 fetch-engine. |
| R-18 | `cli/fetch.py:437`, `models/note.py:84-125`, `core/config.py:391-394`(주석), `core/agent_docs.py:105-136`(안내문) | **문서와 구현의 차이**: `config.py` 주석·`agent_docs.py`는 치환 노트의 "title and author metadata are still the source's"(구조는 제목·저자까지 OA 사본)라고 쓰나, `fetch.py:430,437`은 복구 후 `result`를 복구 결과로 바꾼 다음 `note_title = title or result.title`을 정하므로 제목이 복구 쪽에서 온다. `author`는 어느 경우든 `NoteMeta`에 필드가 없어 저장되지 않는다. 구현을 사실로 썼다. |
| R-19 | C-14, `core/db.py:55-63`, `core/sync.py:451-481`, `core/agent_docs.py:105-136` | 직접 읽음. |
| T-01~T-12 | R-ID별 코드 | 모두 실행하지 않고 코드를 따라가 도출했다. T-04의 정렬은 `sorted`의 안정성에 의존한다. |

`resolve_oa`(`oa.py:248-262`)는 후보 첫 번째만 돌려주는 공개 함수지만 어디서도 호출되지 않는다(`grep -rn resolve_oa`).

### 2.2 코드 읽는 순서

`core/oa.py` 모듈 docstring(불변식) → `needs_oa_recovery` → `iter_oa_candidates` → 세 resolver → `_try_candidates` → `recover_full_text`·`rescue_full_text` → `recovery_notice`·`oa_frontmatter` → 호출부 `cli/fetch.py:318-350, 414-434`.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. gpt-researcher에는 OA 복구에 해당하는 기능이 없다(확인하지 않음).

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-05, R-18 | (검토 항목) 후보를 지연 조회로 바꾸고, 치환 노트의 제목은 원 소스 것을 유지할지 정한다 | 원본은 주석과 달리 eager 조회이고 제목이 복구 쪽에서 온다 | T-04·T-05 순서는 같고 API 호출 수와 제목 규칙(R-18)이 바뀐다 |
