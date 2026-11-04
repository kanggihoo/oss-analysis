---
sha: "aece65f9307197119629beacf8aeaf8cc80e999a"
created: 2026-11-05
updated: 2026-11-05
sources:
  - src/hyperresearch/web/base.py
  - src/hyperresearch/web/builtin.py
  - src/hyperresearch/web/safe_http.py
  - src/hyperresearch/web/pdf.py
  - src/hyperresearch/web/crawl4ai_provider.py
  - src/hyperresearch/web/exa_provider.py
  - src/hyperresearch/web/tavily_provider.py
  - src/hyperresearch/web/parallel_provider.py
  - src/hyperresearch/web/serply_provider.py
  - src/hyperresearch/core/config.py
  - src/hyperresearch/cli/setup.py
  - src/hyperresearch/cli/config_cmd.py
  - src/hyperresearch/cli/research.py
  - src/hyperresearch/cli/fetch.py
  - src/hyperresearch/core/oa.py
  - src/hyperresearch/models/note.py
  - pyproject.toml
depends: []
status: ready
---

# 웹 프로바이더 패밀리

> URL 하나(또는 검색어 하나)를 받아 `[web] provider` 설정이 고른 구현(builtin·crawl4ai·exa·tavily·parallel·serply)으로 가져와, 모든 구현이 같은 `WebResult`(url·title·content·raw_html·metadata·media·links·screenshot·raw_bytes)로 돌려주고, 직접 HTTP를 하는 경로는 SSRF 관문(`check_url`·`safe_get`)과 PDF 공용 lane을 지나게 한다.

<!--
읽은 코드: web/ 전체(base, builtin, safe_http, pdf, crawl4ai_provider, exa, tavily, parallel, serply), core/config.py(FetchSettings·JunkGates·VaultConfig의 [web]), cli/setup.py(경계만), cli/config_cmd.py(web 키), cli/research.py(search 호출부), pyproject.toml(의존성).
실행한 것: 없음(읽기만). 외부 SDK(crawl4ai, exa-py, tavily-python, mcp)와 외부 서비스의 실제 응답은 확인하지 못했다. 코드가 가정한 형태를 쓴다.
이 스펙이 S3(`WebResult`)의 소유자다. `looks_like_login_wall`·`looks_like_junk`는 WebResult의 메서드지만 호출 흐름과 규칙은 fetch-engine 스펙이 소유한다. 이 스펙은 메서드가 쓰는 "바이너리 쓰레기" 판정(R-29)만 가진다.
-->

## 1부. 동작 설명

용어를 먼저 정리한다.

- **provider**: `fetch(url)`과 `search(query, max_results)`를 가진 객체. 이 레포에서는 6종이다.
- **lane**: 같은 URL을 가져오는 한 가지 경로. builtin의 HTML lane, 모든 provider가 공유하는 PDF lane, crawl4ai의 headless 브라우저 lane과 visible(창이 보이는) 브라우저 lane이 있다.
- **SSRF 관문**: 서버 쪽 요청 위조(SSRF)를 막으려고 URL의 스킴·호스트·해석된 IP를 검사하는 `safe_http.check_url`과, 이를 홉마다 적용하는 `safe_http.safe_get`.
- **junk 게이트(`JunkGates`)**: 가져온 본문이 캡차·오류 페이지·바이너리 쓰레기인지 가르는 임계값 묶음(`[junk]` 설정). 판정 흐름은 [fetch-engine](fetch-engine.md)에 있다.

### 1.1 한눈에 보는 흐름

1. 호출자(`fetch`·`fetch-batch`·`research` 명령, MCP `fetch_url`, OA 복구)가 `get_provider(name, profile, magic, headless, settings, gates)`를 부른다. `name`이 없거나 `"builtin"`이면 builtin이고, 그 밖에는 이름별 클래스를 만든다(R-03).
2. `provider.fetch(url)`이 `WebResult` 하나를 돌려준다(R-01, R-02). 실패는 예외로 전달한다.
3. builtin은 PDF처럼 보이는 URL이면 먼저 PDF lane을 시도하고, 아니면 `safe_get`으로 내려받아 PDF 여부를 본문 첫 바이트로 다시 확인한 뒤 HTML이면 텍스트를 뽑는다(R-15~R-18).
4. PDF lane은 `pdf_url_for`로 URL을 고치고 `safe_get`으로 내려받아 pymupdf로 쪽마다 텍스트를 뽑는다. 실패하면 이유 문자열을 남기고 HTML lane으로 넘어간다(R-19~R-22).
5. crawl4ai는 진입 URL을 `check_url`로 검사한 뒤 브라우저로 렌더링하고, 브라우저가 도착한 최종 URL을 다시 검사한다(R-23~R-28).
6. exa·tavily·parallel·serply는 URL을 제3자 API에 넘기고 응답을 `WebResult`로 옮긴다. 이 넷은 로컬 SSRF 검사를 하지 않는다(R-08, R-30~R-33).
7. `search`는 exa·tavily·parallel·serply만 지원한다. builtin·crawl4ai는 `NotImplementedError`다. `search`를 부르는 곳은 `research` 명령 하나뿐이다(R-06).

### 1.2 범위·통합 지점

- 제공: provider 6종과 등록부, `WebResult` 계약(S3), SSRF 관문, PDF 공용 lane, builtin의 HTML→텍스트 추출(코드 블록 보존 포함), 가져온 본문의 바이너리 쓰레기 판정.
- 제외(경계만):
  - 로그인 벽·정크 판정의 호출 순서, 중복 URL 거부, 노트 저장, 에스컬레이션 큐 넣기 — [fetch-engine](fetch-engine.md). 이 스펙의 provider는 "가져오기만" 하고 저장하지 않는다.
  - OA(오픈액세스) 복구가 이 스펙의 provider와 PDF lane을 후보 URL에 다시 쓰는 방식 — [oa-recovery](oa-recovery.md). 이 스펙은 `fetch_pdf`·`provider.fetch`가 그 호출에 대해 주는 결과만 정의한다.
  - `hyperresearch setup`(대화형 TUI)과 `install` — 행 1·2(범위 밖). setup이 `[web]` 설정에 무엇을 쓰는지만 R-34에 둔다.
  - 학술 API(OpenAlex 등)·임베딩 HTTP 호출: SSRF 관문을 거치지 않는 별도 경로다(R-08). 해당 스펙([scholar-search](scholar-search.md))이 소유한다.
  - 브라우저 레인(사용자의 실제 Chrome으로 막힌 URL을 비우는 에이전트) — 행 18(범위 밖).
- 외부 의존: `httpx`·`idna`·`pymupdf`는 필수 의존성. `Crawl4AI>=0.7.3`도 `pyproject.toml`의 필수 의존성 목록에 있다(extras에도 중복). `exa-py`, `tavily-python`, `mcp>=1.8`(parallel)은 extras다. `bs4`는 선언된 의존성이 아니고(crawl4ai가 끌고 오면 있다) 없으면 stdlib 파서로 내려간다(R-16, R-17). 환경변수: `EXA_API_KEY`, `TAVILY_API_KEY`, `SERPLY_API_KEY`.
- 소유 상태·부작용: provider는 파일·DB를 쓰지 않는다. 예외는 프로세스 전역 `pdf._FAILURES`(URL→실패 이유, 최대 256개, 차면 전부 비움), parallel의 모듈 전역 `_SESSION_ID`(프로세스당 uuid4 hex 하나), PDF 로깅 한 번 경고 플래그다. crawl4ai는 `~/.crawl4ai/profiles/<profile>`의 브라우저 프로필 디렉터리를 읽고 쓴다(브라우저가).

### 1.3 인터페이스와 데이터 의미

**`WebResult`(S3)** — 모든 provider와 PDF lane의 반환 타입이다. 호출자 사이에서 복사 없이 넘어가는 가변 객체이고 수명은 한 번의 fetch다.

| 필드 | 타입 | 의미·누락 규칙 |
|---|---|---|
| `url` | string | 결과가 가리키는 URL. provider마다 다르다: builtin HTML은 리다이렉트를 따라간 최종 URL, builtin PDF는 `pdf_url_for`로 고친 URL, crawl4ai 헤드리스는 요청한 URL(crawl4ai의 `result.url`), crawl4ai visible은 브라우저 최종 URL, serply fetch는 요청 URL, exa·tavily·parallel은 응답이 준 URL(R-30~R-33). |
| `title` | string | 없으면 빈 문자열(None 아님). 쓰는 쪽이 비었을 때 대체한다. |
| `content` | string | 정제된 마크다운 또는 평문. 빈 문자열일 수 있고, 그때는 junk 게이트가 거른다. |
| `fetched_at` | datetime(UTC) | 객체를 만든 시각(기본값 `now(UTC)`). 서버가 준 날짜가 아니다. |
| `raw_html` | string 또는 None | 원본 HTML. builtin HTML·crawl4ai만 채운다. 나머지는 None. DOI 메타 태그 추출에 쓰인다. |
| `metadata` | map | provider별 임의 키. 공통으로 읽는 키는 `author`(노트 저장 시도, R-02)와 `pdf_failure`(`PDF_FAILURE_KEY`)뿐이다. PDF는 `content_type`·`pages`. 없으면 빈 map. |
| `media` | list of map | 이미지 `{src, alt, score, ...}`. crawl4ai만 채운다. 없으면 `[]`. |
| `links` | list of map | `{href, text, type}`(`type`은 `internal`/`external`). crawl4ai 단건 fetch만 채운다(`fetch_many`는 비움). 없으면 `[]`. |
| `screenshot` | bytes 또는 None | PNG. crawl4ai만. |
| `raw_bytes` | bytes 또는 None | 원본 파일 바이트. PDF lane만 채운다. |
| `raw_content_type` | string 또는 None | `raw_bytes`의 MIME. PDF lane은 `application/pdf`. |
| `domain`(속성) | string | `urlparse(url).netloc`. 포트·userinfo가 있으면 그대로 포함한다. |

**등록부와 provider 계약**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `get_provider(name, profile, magic, headless, settings, gates)` | → provider | 이름 해석과 생성(R-03). 모르는 이름은 `ValueError`. |
| `provider.fetch(url)` | string → `WebResult` | 필수. 실패는 예외. |
| `provider.search(query, max_results=5)` | → list of `WebResult` | 선택. 미지원은 `NotImplementedError`. |
| `crawl4ai.fetch_many(urls)` | list → list of `WebResult` | crawl4ai만 있다. 거부·실패 URL은 결과에서 조용히 빠진다(R-28). |

**설정 키**(`.hyperresearch/config.toml`, 알 수 없는 키는 무시하고 목록은 튜플로 읽는다)

| 키 | 기본값 | 쓰는 곳 |
|---|---|---|
| `[web] provider` | `"builtin"` | 기본 provider. CLI `--provider`가 덮는다. `config set web.provider`로도 바꾼다. |
| `[web] profile` | `""` | crawl4ai 프로필 이름. 비면 프로필 없이 실행. |
| `[web] magic` | `false` | crawl4ai magic(스텔스) 모드. |
| `[fetch]`·`[junk]` | C-04, C-05 | 아래 R-05. |

**반환 규칙의 공통점**: provider는 판정(로그인 벽·정크)을 하지 않는다. 다만 `crawl4ai.fetch`는 바이너리 쓰레기가 오면 PDF lane으로 다시 가져온다(R-24).

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `WebResult` 생성 | 필수 인자는 `url`·`title`·`content`. 나머지 기본값은 C-01. `fetched_at`은 생성 시각. `domain`은 `urlparse(url).netloc`. | 코드 확인 |
| R-02 | 호출자가 결과 필드를 읽음 | 필드의 소비처: `raw_html` → DOI 메타 태그 추출·막힌 소스 복구용 DOI 탐색, `media`·`screenshot` → `--save-assets`, `raw_bytes`+`raw_content_type` → 노트 옆 원본 파일 저장(확장자 pdf/png/jpg/gif/webp만), `metadata["author"]` → 노트 `author` 시도(단 NoteMeta에 `author` 필드가 없어 저장되지 않는다, 2.1), `metadata["pdf_failure"]` → junk 판정 메시지에 덧붙임. | 코드 확인 |
| R-03 | `get_provider(name=…)` | `None`·`"builtin"` → `BuiltinProvider(settings)`. `"crawl4ai"` → `Crawl4AIProvider(profile=profile or None, magic, headless, settings, gates)`(import 실패 시 `ImportError("crawl4ai provider requires: pip install hyperresearch[crawl4ai]")`). `"exa"` → `ExaProvider()`. `"tavily"` → `TavilyProvider()`(ImportError 메시지에 extras 안내). `"parallel"` → `ParallelProvider(settings)`(같은 방식). `"serply"` → `SerplyProvider()`. 그 밖의 이름은 `ValueError("Unknown web provider: '<name>'. Available: builtin, crawl4ai, exa, tavily, parallel, serply")`. 이름 비교는 정확 일치(대소문자 구분). | 코드 확인 |
| R-04 | provider 생성 인자 | exa·tavily·serply는 인자 없이 만든다. 그래서 생성자의 튜닝 인자(Exa `search_type`·`text_max_characters`·`category`·도메인 필터, Tavily `search_depth`·`topic`·도메인 필터, Serply `fetch_content`·`max_characters`)는 설정 파일로 바꿀 수 없고 기본값이 고정이다. `headless`·`profile`·`magic`·`gates`는 crawl4ai만 쓴다(builtin의 `--visible`은 효과가 없다). | 코드 확인 |
| R-05 | `[fetch]`·`[junk]` 읽기 | 기본값과 의미는 C-04, C-05. builtin은 `max_html_bytes`·`allow_private_hosts`만 쓰고 `page_timeout_ms`·`wait_*`는 쓰지 않는다(요청 제한시간은 `safe_get` 기본 30초 고정). PDF lane은 `max_pdf_bytes`·`pdf_timeout_s`·`pdf_verify_tls`·`allow_private_hosts`·`min_pdf_bytes`를 쓴다. crawl4ai는 `page_timeout_ms`·`wait_initial_ms`·`poll_interval_ms`·`stable_checks`·`max_checks`·`browser_verify_tls`·`allow_private_hosts`. parallel은 `page_timeout_ms`를 연결·읽기 제한시간으로. 이미지 다운로드는 `max_image_bytes`·`image_timeout_s`(fetch-engine 스펙). | 코드 확인 |
| R-06 | `search(query, max_results)` | exa·tavily·parallel·serply는 R-30~R-33대로 결과 목록을 돌려준다. builtin과 crawl4ai는 `NotImplementedError`("…Use your agent's built-in search, then pipe URLs into 'hyperresearch fetch'."). 파이프라인의 검색은 호스트 에이전트의 검색 도구가 하고, provider `search`를 부르는 코드는 `cli/research.py`의 단발 `research` 명령뿐이다. | 코드 확인 |
| R-07 | exa·tavily·serply 생성 | 각각 `EXA_API_KEY`·`TAVILY_API_KEY`·`SERPLY_API_KEY` 환경변수(앞뒤 공백 제거)가 없으면 `RuntimeError`. 키는 설정 파일이 아니라 환경변수로만 받는다. parallel은 키가 없다(무계정 엔드포인트). 필요한 SDK가 없으면 `ImportError`(exa·tavily는 생성자가, parallel은 모듈 import가 일으킨다). | 코드 확인 |
| R-08 | 어떤 호출이 SSRF 관문을 지나는가 | 지나는 곳: builtin의 모든 HTTP(`safe_get`, 홉마다), PDF lane(`safe_get`), crawl4ai(진입 `check_url` + 최종 URL 재검사 + PDF는 `safe_get`), 이미지 다운로드(`safe_get`), OA 복구(`check_oa_url` + `safe_get`/PDF lane). 지나지 않는 곳: exa·tavily·parallel·serply의 `fetch(url)`(URL을 제3자 API로 보낸다. 로컬에서 사설 IP를 거르지 않는다), 학술 API(`scholar/base.py`는 `follow_redirects=True`, `core/scholar.py`는 수동 리다이렉트이지만 둘 다 관문 없음), 임베딩 호출. 즉 "모든 외부 요청이 SSRF 관문을 지난다"는 말은 성립하지 않는다(2.1). | 코드 확인 |
| R-09 | `check_url(url, allow_private_hosts)` | 아래 순서로 검사하고 하나라도 걸리면 `SafeHTTPError`. ① `urlparse` 실패(`ValueError`) ② 스킴이 `http`/`https`(소문자 비교)가 아님 ③ `urlparse`가 호스트를 못 찾음 ④ 앞쪽 C0 제어문자·공백을 떼고 `httpx.URL(...).raw_host`를 ASCII로 얻음(실패·호스트 없음이면 거부. 탭·개행 등 제어문자가 URL 중간에 있어도 `InvalidURL`로 거부) ⑤ 파서 불일치 검사: 권한부(`//` 뒤 `/?#` 전까지)에 `\`가 있으면 거부, IPv6 리터럴이면 통과, 호스트에 `%`가 있으면 거부, 마지막 라벨이 10진수/`0x` 16진수 숫자열인데 표준 점-십진 IPv4가 아니면 거부(`2130706433`, `0x7f.1`, `1.2.3.4.` 등) ⑥ 허용 목록 파싱(R-11) ⑦ 호스트가 허용 호스트명과 일치하면 즉시 통과 ⑧ 호스트를 IP로 해석(IP 리터럴은 그대로, 아니면 `getaddrinfo`. 실패는 `SafeHTTPError("DNS lookup failed …")`, 주소 0개면 거부) ⑨ 해석된 주소 중 하나라도 차단 대상(R-10)이고 허용 네트워크에 없으면 거부. | 코드 확인 |
| R-10 | 차단 IP | IPv4-mapped IPv6는 내장 IPv4로 판정, 6to4(`2002::/16`)는 내장 IPv4(비트 16~48)로 판정. 그 뒤 `is_private`·`is_loopback`·`is_link_local`·`is_multicast`·`is_reserved`·`is_unspecified` 중 하나이거나 IPv4 CGNAT(`100.64.0.0/10`)이면 차단(C-08). 호스트가 여러 주소로 해석되면 전부 통과해야 한다. | 코드 확인 |
| R-11 | `allow_private_hosts`(예: `["10.8.0.0/16","wiki.intranet","192.168.1.20"]`) | 항목이 IP·CIDR(브래킷 IPv6 포함, `strict=False`)이면 해석된 주소가 같은 버전의 그 네트워크에 속할 때만 허용한다. 아니면 호스트명 항목으로, 소문자·비ASCII는 IDNA 2008 punycode·끝 점 제거로 정규화해 정확 일치할 때 통과한다. 호스트명 일치는 주소 해석을 건너뛴다(그래서 DNS를 안 본다). 잘못된 항목(잘못된 CIDR, `%`, `host:port`, IDNA 불가)은 항목 이름을 담은 `SafeHTTPError`이고, 이 파싱이 호스트 일치 검사보다 먼저라서 관계없는 URL도 같은 오류로 막힌다. 스킴·파서 불일치 검사는 허용 호스트에도 적용된다. | 코드 확인 |
| R-12 | URL에 `user:pw@` 자격증명 | `check_url`·`safe_get`은 userinfo를 검사하지 않는다. 호스트 검사는 userinfo를 뗀 호스트에만 한다(httpx가 Basic 인증 헤더로 보낸다). 자격증명을 거부하는 곳은 OA 후보 URL 검사 `check_oa_url` 하나다(oa-recovery). | 코드 확인 |
| R-13 | `safe_get(url, max_bytes, timeout=30, max_redirects=5, headers, verify=True, allow_private_hosts)` | `max_bytes<=0`이면 `ValueError`. 기본 헤더 `User-Agent: hyperresearch/0.1`에 `headers`를 덮어 쓴다. 리다이렉트는 수동으로 따르며 최대 `max_redirects+1`번 요청한다(최초+5홉). 매 요청 전에 `check_url`. `Location`이 있으면 상대 URL을 현재 URL 기준으로 합치고, 없으면 상태코드 그대로 빈 본문을 돌려준다. 응답 `Content-Length`가 숫자이고 `max_bytes`보다 크면 본문을 읽지 않고 거부. 스트림으로 읽다가 누적이 `max_bytes`를 넘으면 거부(둘 다 `SafeHTTPError`). 6번째 리다이렉트는 `SafeHTTPError("too many redirects …")`. 반환은 `SafeResponse(url=최종 URL, status_code, headers=소문자 키, content)`이고 4xx·5xx도 예외 없이 돌려준다(호출자가 본다). `text`는 `Content-Type`의 `charset`(없으면 utf-8)으로 `errors="replace"` 디코딩하고 모르는 charset이면 utf-8. | 코드 확인 |
| R-14 | TLS 인증서 | builtin HTML lane: 항상 검증, 인증서 오류는 `CertVerificationError`(`SafeHTTPError`의 하위)로 바꿔 던진다. PDF lane: `pdf_verify_tls`(기본 true)를 따르고, 켜져 있으면 인증서 오류를 `CertVerificationError`(끄는 법 안내 문구 포함)로 던지며 검증 없는 자동 재시도는 하지 않는다. crawl4ai 헤드리스: `browser_verify_tls`(기본 true)가 켜져 있으면 crawl4ai가 붙이는 `--ignore-certificate-errors*` 실행 플래그를 제거하고, 결과의 Chromium 오류 `net::ERR_CERT*`·핀닝 오류를 `CertVerificationError`로 던진다. crawl4ai visible lane은 설정과 무관하게 인증서 오류를 무시한다. 인증서 거부는 다른 lane으로 넘기지 않는다(PDF lane의 거부는 브라우저 폴백도 하지 않고 그대로 전파). | 코드 확인 |
| R-15 | `BuiltinProvider.fetch(url)` | ① `is_pdf_url(url)`이면 `fetch_pdf`를 시도해 결과가 있으면 그대로 반환, 없으면 이유(`failure_reason`)를 기억하고 계속 ② `safe_get(url, max_bytes=max_html_bytes, allow_private_hosts)`. 예외는 그대로(인증서 오류는 R-14), 상태코드 ≥400이면 `RuntimeError("HTTP <code> fetching <url>")` ③ 본문이 `%PDF-`로 시작하거나 `Content-Type`에 `application/pdf`가 있으면 `extract_pdf(최종 URL, 바이트, …)`를 시도해 성공하면 반환, 실패하면 그 이유로 대체 ④ 아니면 `resp.text`에서 `_extract`로 `(title, content)`를 뽑아 `WebResult(url=최종 URL, raw_html=디코딩된 HTML, fetched_at=now)`를 만들고 ①·③의 실패 이유가 있으면 `metadata["pdf_failure"]`에 담는다. | 코드 확인 |
| R-16 | `_extract(html)`, `bs4` import 가능 | `html.parser`로 파싱 → `script`·`style`·`nav`·`footer`·`header`·`aside` 태그를 통째로 제거 → 제목은 `<title>`의 `.string`(중첩 태그가 있어 `.string`이 None이면 빈 문자열) → 각 `<pre>`는 안의 텍스트를 울타리 코드 블록(R-18)으로 바꾸고(비어 있으면 비움), 남은 각 `<code>`는 인라인 코드로 바꿈(비어 있으면 비움) → `get_text(separator="\n", strip=True)`(텍스트 노드마다 한 줄) → 연속 3줄 이상 빈 줄을 빈 줄 하나로. `<title>`은 제거 대상이 아니라 본문에도 남는다. | 코드 확인 |
| R-17 | `_extract(html)`, `bs4` import 불가(`ImportError`) | `HTMLParser` 기반 `_TextExtractor`(C-15)로 대신한다. 제거 태그는 `script`·`style`·`nav`·`footer`·`header`(`aside` 없음)이고 제거 상태는 깊이 카운터가 아니라 불리언 하나라서 중첩된 제거 태그의 첫 닫는 태그에서 풀린다. `p`·`br`·`div`·`h1~h6`·`li` 시작 태그마다 줄바꿈을 넣는다. 텍스트는 이어 붙이고(노드마다 줄바꿈하지 않음), 모아 둔 뒤 줄마다 `strip`·연속 빈 줄 축소. `<pre>`는 내용을 모아 울타리 코드 블록으로, `<pre>` 안의 `<br>`은 줄바꿈, 다른 태그는 무시. `<code>` 안 텍스트는 인라인 코드 span으로(공백뿐이면 버림). 블록 사이는 빈 줄 하나. 제목은 마지막 `<title>` 텍스트이고 제목 텍스트도 본문 앞에 남는다. | 코드 확인 |
| R-18 | 코드 보존 규칙(두 lane 공통) | 울타리: 코드 안 연속 백틱 중 가장 긴 길이보다 1 긴 백틱 열(최소 3)을 앞뒤에 두고 `\n<fence>\n<코드(앞뒤 개행 제거)>\n<fence>\n`. 인라인: 텍스트에 백틱이 없으면 `` `텍스트` ``, 있으면 가장 긴 백틱 열+1 길이의 열로 `<ticks> 텍스트 <ticks>`. 이유(코드가 마크다운 코드로 가야 하는 까닭): 평문으로 펴진 `[[ -n "$x" ]]` 같은 셸 조각이 위키링크 정규식에 걸려 가짜 스텁 노트를 만든 사고가 있었다. | 코드 확인(동기는 주석 근거라 추론) |
| R-19 | `is_pdf_url(url)` | URL을 소문자로 바꿔 `urlparse`한 뒤 경로가 `.pdf`로 끝나거나, 경로에 `/pdf/`·`/pdfs/`가 있거나, 호스트에 `arxiv.org`가 있고 경로에 `/pdf/` 또는 `/abs/`가 있으면 true. `pdf_url_for(url)`은 `arxiv.org/abs/`가 든 URL의 `/abs/`를 `/pdf/`로 바꾸고 `.pdf`로 안 끝나면 `.pdf`를 붙인다. | 코드 확인 |
| R-20 | `fetch_pdf_ex(url, settings)` → `(result, reason)` | ① pymupdf를 import하지 못하면 `(None, "pymupdf is not importable")`(오류 로그는 프로세스당 한 번) ② `pdf_url_for`로 URL을 바꾸고 `safe_get`(Chrome UA와 `Accept: application/pdf,…` 헤더, `max_pdf_bytes`, `pdf_timeout_s`, `pdf_verify_tls`, `allow_private_hosts`) ③ `CertVerificationError`는 전파 ④ `SafeHTTPError`는 `(None, "refused: <메시지>")` ⑤ 상태코드 ≠200은 `(None, "HTTP <code>")` ⑥ 200이면 `extract_pdf`(R-21) ⑦ 그 밖의 예외는 `(None, "extraction failed: <예외>")`. `fetch_pdf(url, settings)`는 결과만 돌려주고 이유는 URL(요청한 그대로)별로 전역 기억에 넣는다(성공이면 지움, 256개 도달 시 전부 비움). `failure_reason(url)`이 그 기억을 읽는다. | 코드 확인 |
| R-21 | `extract_pdf(url, bytes, settings, content_type)` → `(result, reason)` | 순서대로 실패: pymupdf 없음 / 바이트가 `%PDF-`로 시작하지 않음(`content-type`과 앞 8바이트를 이유에 담음. 매직 바이트가 헤더·URL보다 우선) / 크기 < `min_pdf_bytes`(100) / pymupdf가 문서를 못 엶 / 쪽 읽기 중 예외(문서는 반드시 닫음) / 텍스트가 있는 쪽이 0개(`스캔 문서일 가능성`, OCR 필요). 성공: 텍스트가 비지 않은 쪽(`page.get_text("text")`)만 모아 `"\n\n---\n\n"`로 잇는다. 제목은 첫 번째 모은 쪽의 첫 `strip` 줄 중 길이 10 초과인 것, 없으면 `"PDF: <URL 마지막 / 뒤>"`. `metadata={"content_type":"application/pdf","pages":<텍스트 있는 쪽 수>}`, `raw_bytes=원본`, `raw_content_type="application/pdf"`. | 코드 확인 |
| R-22 | PDF lane 결과를 쓰는 provider | builtin은 R-15대로 실패 시 HTML lane으로 폴백하고 이유를 `metadata["pdf_failure"]`에 싣는다. crawl4ai도 같다(R-24). 인증서 거부는 폴백하지 않는다(R-14). | 코드 확인 |
| R-23 | `Crawl4AIProvider(...)` 생성 | `profile`이 있고 `user_data_dir`이 없으면 프로필 디렉터리를 `~/.crawl4ai/profiles/<profile>`로 정하고 `use_managed_browser=True`로 그 디렉터리를 쓴다. `BrowserConfig(headless, [managed·user_data_dir], [cookies], ignore_https_errors=not browser_verify_tls)`. 실행 설정(C-26): `magic`, `simulate_user=True`, `screenshot=True`, `page_timeout=page_timeout_ms`, `wait_for="js:"+스마트 대기 JS(C-23)`, 마크다운 생성기는 `DefaultMarkdownGenerator(content_filter=PruningContentFilter())`. 브라우저는 stealth용 `UndetectedAdapter` 전략으로 띄운다. | 코드 확인 |
| R-24 | `Crawl4AIProvider.fetch(url)` | ① `check_url`(예외 전파) ② `is_pdf_url`이면 `fetch_pdf`, 실패면 이유를 기억하고 브라우저로 폴백 ③ `headless=False`이고 프로필 디렉터리가 있으면 visible lane(R-26), 아니면 헤드리스 lane(R-25)을 돌리고, 그 결과 `content`가 있고 바이너리 쓰레기(PDF 내부 표지 `endstream`·`endobj`·`/Filter`·`/FlateDecode`·`stream\nx`·`%PDF-`가 앞 `sample_window`자에 있거나 R-29 기준 초과)면 `fetch_pdf`로 다시 받아 성공하면 그 결과를 돌려준다 ④ 결과에 PDF 실패 이유가 있으면 `metadata["pdf_failure"]`에 담는다. 비동기 코루틴은 이벤트 루프가 이미 돌고 있으면 새 스레드에서 돌려 결과를 합친다(MCP 서버 안에서 쓰기 위해). | 코드 확인 |
| R-25 | 헤드리스 결과 변환 | 크롬 오류가 `net::ERR_CERT…`이면서 `success=False`면 `CertVerificationError`. 최종 URL 재검사(R-27, crawl4ai의 `redirected_url`이 있으면 그것, 없으면 `result.url`). `content`는 `fit_markdown`, 비면 `raw_markdown`, 마크다운이 문자열이면 그대로, 없으면 빈 문자열. `title=metadata.get("title","")`, `raw_html=result.html`, `metadata=result.metadata or {}`, `media=result.media["images"]`(dict일 때만), `links`는 `internal`·`external` 항목에 `type`을 붙여 이어 붙임, `screenshot`은 base64 해독(실패는 None), `url=result.url or 요청 URL`(요청 URL과 같다). | 코드 확인(crawl4ai 응답 필드는 SDK 가정) |
| R-26 | visible lane | Playwright 지속 컨텍스트로 프로필 디렉터리를 열어(창 보임, 뷰포트 1280×900, 인증서 오류 무시) `domcontentloaded`까지 이동하고 스마트 대기 JS를 돌린 뒤 HTML·제목·PNG 스크린샷·최종 URL을 얻는다. 최종 URL 재검사. HTML은 같은 마크다운 생성기로 변환해 `fit_markdown` 우선 `content`로. 반환은 `WebResult(url=최종 URL, title, content, raw_html, metadata={"title":제목}, screenshot)`이고 `media`·`links`는 비어 있다. 이 lane에는 바이너리 재확인이 없다. | 코드 확인 |
| R-27 | `_check_final_url(entry_url, final_url, settings)` | `final_url`이 없거나 진입 URL과 같으면 통과. 호스트가 진입 호스트와 같고 스킴이 http(s)이면 통과(진입 검사가 이미 보증). 아니면 `check_url(final_url)`로 검사하고 거부 시 `SafeHTTPError("browser navigation for <진입> ended at refused URL: …")`. 브라우저가 이미 보낸 요청은 막지 못하고 사설망 내용이 볼트에 들어가는 것만 막는다. | 코드 확인 |
| R-28 | `crawl4ai.fetch_many(urls)` | 각 URL을 `check_url`하고 거부된 것은 경고만 남기고 뺀다. PDF 모양 URL은 `fetch_pdf`로 직접(인증서 거부는 건너뛰며 로그, 실패는 브라우저 목록으로), 나머지는 `arun_many`로. 결과는 완료순으로 오므로 `cr.url`이 요청 집합에 있으면 그것을 URL로 삼는다. `success=False`는 건너뜀(인증서 오류면 경고). 최종 URL 재검사 실패는 그 결과를 버림. 바이너리 쓰레기면 `fetch_pdf`로 대체(인증서 거부는 그 결과를 버림). 변환은 R-25와 같으나 `links`를 채우지 않는다. 호출자에게는 실패 URL 목록이 가지 않는다. | 코드 확인 |
| R-29 | 바이너리 쓰레기 판정 | 문자 하나가 쓰레기 표지: C0 제어문자(U+0000~001F, 단 `\t \n \r \f \v` 제외), U+FFFD(대체 문자), C1 제어문자(U+0080~009F). 비ASCII 일반 글자(CJK·키릴·악센트 라틴 등)는 쓰레기가 아니다. 표본에서 쓰레기 문자 비율이 `binary_garbage_ratio`(기본 0.05)를 초과하면 true. 빈 문자열의 비율은 0. | 코드 확인 |
| R-30 | Exa | `search`: `exa.search(query, num_results, type="auto", contents={"text":{"max_characters":8000},"highlights":True})`, 결과마다 변환. `fetch`: `get_contents([url], text={"max_characters":8000})`, 결과가 없으면 `RuntimeError("Exa returned no contents for <url>")`. 변환: `content`는 `text`(공백뿐이 아님) → 없으면 `highlights`를 빈 줄로 이은 것 → 없으면 `summary`. `metadata`는 값이 있는 `author`·`published_date`·`score`·`favicon`·`image`, `highlights`가 있으면 목록으로, `summary`가 `content`와 다르면 `summary`. `url`·`title`은 응답 값(없으면 빈 문자열). 요청에 `x-exa-integration: hyperresearch` 헤더. | 코드 확인(SDK 응답 필드는 가정) |
| R-31 | Tavily | `search`: `client.search(query, max_results, search_depth="advanced", topic="general")`의 `results`. `fetch`: `client.extract(urls=[url])`의 첫 `results`, 없으면 `RuntimeError("Tavily returned no contents for <url>")`. 변환: `content`는 `content` → `raw_content` → 빈 문자열, `title` 없으면 빈 문자열, `metadata`는 `score`(None이 아니면)·`published_date`(값이 있으면). | 코드 확인(SDK 응답 필드는 가정) |
| R-32 | Serply | `search`: `GET https://api.serply.io/v1/search/?q=<질의>&num=<n>`(헤더 `X-Api-Key`, `User-Agent: hyperresearch`, 제한시간 30초, HTTP 오류는 `raise_for_status`)의 `results[:n]`. 항목 변환: `url=link`(없는 항목은 건너뜀), `title`, `content=description`(SERP 스니펫), `metadata`에 `position`·`metadata.published_time`. 기본 설정(`fetch_content=True`)에서는 각 URL을 `fetch`해 오류(`httpx.HTTPError`·`RuntimeError`)면 스니펫 유지, 성공이어도 기본 junk 게이트가 정크라고 하면 스니펫 유지, 통과하면 `content`를 가져온 본문으로 교체. `fetch`: `POST https://api.serply.io/v1/request` 본문 `{"url":…, "response_type":"markdown"}`, 응답 본문을 `strip` 후 앞 8000자, 비면 `RuntimeError("Serply returned no content for <url>")`, 반환은 `WebResult(url=요청 URL, title="", content=…)`. | 코드 확인(API 동작은 가정) |
| R-33 | Parallel | 엔드포인트 `https://search.parallel.ai/mcp`(Streamable HTTP MCP 클라이언트, 호출마다 연결을 열고 `initialize` 후 `call_tool`, 제한시간=`page_timeout_ms`). `search`: 질의를 `strip`(빈 질의는 `ValueError`)해 `objective`(≤5000자)와 `search_queries=[질의 ≤200자]`로 보내되 한도를 넘으면 단어 경계(마지막 공백)에서 자른다. 도구 `web_search`, 인자에 프로세스 공통 `session_id`. 결과 앞 `max(0,max_results)`개를 변환. `fetch`: 도구 `web_fetch`, `{"urls":[url],"full_content":True,"session_id":…}`, 결과가 비면 `RuntimeError`(`errors[0].error_type`이 있으면 `"Parallel could not fetch <url>: <type>"`, 없으면 `"Parallel returned no contents for <url>"`). 응답 해석: `isError`면 `RuntimeError("Parallel <tool> failed: …")`, `structuredContent`가 있으면 그것, 없으면 텍스트 블록을 이어 JSON(객체여야 함) 파싱. `results`가 리스트이고 모든 항목이 dict여야 한다. 변환: `url` 문자열 필수, `title`(None→빈 문자열, 문자열 아님은 오류), `content`는 `full_content`(공백 아님) 아니면 `excerpts`를 `"\n\n"`로 이은 것(문자열 목록이어야 함), 둘 다 아니면·공백이면 `RuntimeError`, `metadata["published_date"]=publish_date`. | 코드 확인(서비스 동작은 가정) |
| R-34 | `hyperresearch setup <path>`(경계) | 대화형 TTY가 아니거나 `--json`이면 `install <path> --create`를 서브프로세스로 위임한다. 대화형이면 ① crawl4ai가 import되면 "기본 provider로 쓸까요"를 묻고(없으면 builtin) ② crawl4ai를 쓰면 `~/.crawl4ai/profiles/*`(안에 `Default` 디렉터리가 있는 것)을 고르거나 새 프로필을 만든다(브라우저를 열어 로그인하고 `q`로 저장, 600초 제한, crawl4ai `BrowserProfiler`를 서브프로세스로) ③ `web_provider`·`web_profile`·`web_magic`(= crawl4ai 사용 여부)를 `config.toml`에 저장하고 훅·스킬·에이전트를 설치한다. exa·tavily·parallel·serply는 setup이 고르지 않고 설정 파일·`config set web.provider`로만 고른다. | 코드 확인 |

- 불변식: 모든 `fetch`는 실패를 예외로, 성공을 `WebResult`로 돌려준다(None 반환 없음). `check_url`/`safe_get` 경로는 홉마다 같은 검사를 적용한다. 인증서 거부(`CertVerificationError`)는 어떤 lane으로도 재시도되지 않는다.
- 미결정: 없음.
- 확인 한계: 코드를 실행하지 않았다. crawl4ai·exa-py·tavily-python·mcp 같은 SDK와 Exa·Tavily·Serply·Parallel 서비스의 실제 응답 구조, crawl4ai `result.metadata`에 어떤 키가 오는지(`title`·`author` 외), `media` 항목의 `score` 등은 코드가 그렇게 가정한다는 것까지만 확인했다(R-25, R-30~R-33). 웹 검색으로 외부 문서를 대조하지 않았다. DNS 재바인딩은 모듈 주석이 "수용한 잔여 위험"이라고 적었다(해석은 `check_url`에서, 연결은 httpx가 다시 해석).

### 1.5 필수 코드 참조

라이선스: MIT(`LICENSE`), 인용 가능(overview 1절). 경로는 `repos/hyperresearch/src/hyperresearch/` 기준이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `web/base.py:53-73` `WebResult` | 필드 이름·타입·기본값, `domain` 속성 | R-01, R-02 |
| C-02 | `web/base.py:19-50` `is_binary_garbage_char`·`binary_garbage_ratio`·`is_binary_garbage` | 바이너리 쓰레기 문자 정의와 비율 검사 | R-24, R-29 |
| C-03 | `web/base.py:185-242` `get_provider` | 이름→클래스 매핑, 생성 인자, 오류 메시지 원문 | R-03, R-04, R-07 |
| C-04 | `core/config.py:10-48` `FetchSettings` | `[fetch]` 키와 기본값(타임아웃·크기 상한·TLS·허용 호스트·스마트 대기·visible 도메인 6개) | R-05, R-13, R-14 |
| C-05 | `core/config.py:51-63` `JunkGates` | `[junk]` 키와 기본값 | R-05, R-29 |
| C-06 | `core/config.py:197-211` `_build_section`, `:242-245`, `:299-312` | 섹션 읽기(알 수 없는 키 무시, 리스트→튜플), `[web]` 키 | R-03, R-05 |
| C-07 | `web/safe_http.py:38-87` | 허용 스킴, 상수, `SafeHTTPError`·`CertVerificationError`·`SafeResponse.text` | R-13 |
| C-08 | `web/safe_http.py:90-120` `_is_blocked_ip` | 차단 IP 판정(매핑·6to4·CGNAT) | R-10 |
| C-09 | `web/safe_http.py:123-221` `_normalize_hostname`·`_resolve`·`_parse_allowlist` | 호스트 정규화, 이름 해석, 허용 목록 파싱과 오류 문구 | R-09, R-11 |
| C-10 | `web/safe_http.py:224-286` `_check_parser_agreement` | WHATWG/RFC3986 파서 불일치 거부 규칙 | R-09 |
| C-11 | `web/safe_http.py:289-351` `check_url` | 검사 순서 전체 | R-09~R-12 |
| C-12 | `web/safe_http.py:354-427` `safe_get`·`_materialize` | 수동 리다이렉트, 크기 상한, 반환 모양 | R-13 |
| C-13 | `web/builtin.py:24-58` | 울타리·인라인 코드 helper | R-18 |
| C-14 | `web/builtin.py:165-273` `BuiltinProvider.fetch`·`search`·`_get`·`_extract` | builtin 전체 흐름과 bs4 추출 | R-15, R-16, R-06 |
| C-15 | `web/builtin.py:61-152` `_TextExtractor` | stdlib 폴백 추출기 | R-17 |
| C-16 | `web/pdf.py:35-48`, `:75-139` | `is_pdf_url`, PDF 헤더, `safe_get_pdf`, `pdf_url_for` | R-14, R-19, R-20 |
| C-17 | `web/pdf.py:142-299` `extract_pdf`·`fetch_pdf_ex`·`fetch_pdf`·`failure_reason` | PDF 추출 단계와 실패 이유 문구, 실패 기억 | R-20~R-22 |
| C-18 | `web/crawl4ai_provider.py:74-120` | `_looks_like_binary`, `_smart_wait_js`(스마트 대기 JS 원문) | R-24, R-23 |
| C-19 | `web/crawl4ai_provider.py:123-225` | 인증서 플래그 제거·오류 코드 정규식·`_check_final_url` | R-14, R-27 |
| C-20 | `web/crawl4ai_provider.py:228-336` | 생성·크롤러 구성·`fetch` 흐름 | R-23, R-24 |
| C-21 | `web/crawl4ai_provider.py:338-458` | visible lane·헤드리스 변환 | R-25, R-26 |
| C-22 | `web/crawl4ai_provider.py:460-593` | `fetch_many`, `search` | R-28, R-06 |
| C-23 | `web/exa_provider.py:27-135` | Exa 요청·변환 | R-30 |
| C-24 | `web/tavily_provider.py:26-104` | Tavily 요청·변환 | R-31 |
| C-25 | `web/serply_provider.py:28-110` | Serply 엔드포인트·요청·변환 | R-32 |
| C-26 | `web/parallel_provider.py:28-233` | Parallel MCP 호출·질의 자르기·응답 해석·변환 | R-33 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(코드를 실행하지 않고 읽어서 정함). 네트워크가 필요한 사례는 DNS가 일반 공개 주소로 풀린다고 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09 | `check_url("ftp://example.com/")` | `SafeHTTPError`("only http/https"). |
| T-02 | R-09, R-10 | `check_url("http://127.0.0.1/")`, `http://[::ffff:100.64.0.1]/`, `http://[2002:7f00:1::]/` | 모두 `SafeHTTPError`(비공개 주소). 허용 목록 없음. |
| T-03 | R-09 | `check_url("http://2130706433/")`, `http://0x7f.1/`, `http://127.0.0.%31/`, `http://127.0.0.1\@evil.com/` | 모두 `SafeHTTPError`(비표준 숫자 호스트, `%`, 권한부 `\`). |
| T-04 | R-11 | `check_url("http://10.1.2.3/", ("10.0.0.0/8",))` / `check_url("http://wiki.intranet/", ("wiki.intranet",))` / 허용 목록에 `"host:8080"` | 앞 둘은 통과(뒤의 것은 DNS를 보지 않고 통과). 셋째는 어떤 URL이든 `SafeHTTPError("…drop the port")`. |
| T-05 | R-12 | `check_url("http://user:pw@8.8.8.8/")` | 통과(자격증명 검사 없음). |
| T-06 | R-13 | 첫 응답이 공개 호스트의 302 → `Location: http://169.254.169.254/` | 둘째 홉의 `check_url`에서 `SafeHTTPError`. 둘째 요청은 나가지 않는다. |
| T-07 | R-13 | 응답 `Content-Length: 30000000`, `max_bytes=10485760` | 본문을 읽지 않고 `SafeHTTPError`. `Content-Length` 없이 스트림이 상한을 넘어도 같은 오류. |
| T-08 | R-15, R-20 | builtin이 `https://example.org/paper.pdf`를 받는데 서버가 HTML 랜딩 페이지(`Content-Type: text/html`)를 돌려줌 | PDF lane은 `(None, "did not return PDF data (…)")`, builtin은 HTML lane으로 폴백해 `WebResult`를 만들고 `metadata["pdf_failure"]`에 그 이유가 있다. |
| T-09 | R-19 | `https://arxiv.org/abs/2501.01234` | `is_pdf_url`=true, 다운로드 URL은 `https://arxiv.org/pdf/2501.01234.pdf`, 성공 시 `WebResult.url`도 그 pdf URL. |
| T-10 | R-18 | `<pre>` 안 코드에 ```` ``` ````가 들어 있음 | 울타리는 백틱 4개. `<code>`에 ``` `` ```가 있으면 인라인 구분자는 백틱 3개. |
| T-11 | R-16, R-17 | `<nav>`·`<aside>`가 든 페이지 | bs4가 있으면 둘 다 제거, 없으면 `<aside>` 텍스트는 남는다. 두 경우 모두 `<title>` 텍스트가 본문에 남는다. |
| T-12 | R-30 | Exa 결과의 `text`가 공백뿐이고 `highlights=["a","b"]` | `content="a\n\nb"`, `metadata["highlights"]=["a","b"]`. |
| T-13 | R-33 | 질의가 300자(공백 포함 단어들) | `search_queries[0]`는 200자 이하로 마지막 공백 앞에서 자른 값, `objective`는 전체. |
| T-14 | R-32 | Serply `search`에서 한 URL의 `fetch`가 `httpx.HTTPError` | 그 항목은 SERP 스니펫을 `content`로 유지하고 목록에 남는다. |
| T-15 | R-03 | `get_provider("firecrawl")` | `ValueError`(Available 목록 포함). `get_provider("exa")`인데 `EXA_API_KEY`가 비어 있음 → `RuntimeError`. |
| T-16 | R-06 | `BuiltinProvider().search("q")` | `NotImplementedError`. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@aece65f) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 정의를 직접 읽음. |
| R-02 | `cli/fetch.py:329-350`(raw_html→DOI), `:442-449`(`author`), `:402-403`(pdf_failure), `:504-521`(raw_bytes), `:693-763`(media·screenshot), `models/note.py:84-125`(NoteMeta에 `author` 없음, `:139` `extra: ignore`) | `author`는 `write_note`가 `NoteMeta(**kwargs)`로 받을 때 무시된다고 코드에서 추적. 실행해 확인하지는 않음. |
| R-03 | C-03 | 분기를 직접 읽음. |
| R-04 | C-03(생성 호출), `web/exa_provider.py:37-68`, `web/tavily_provider.py:34-60`, `web/serply_provider.py:41-61`, `web/builtin.py:199-204`(`headless` 미사용) | 호출부에 인자가 없는 것을 대조. |
| R-05 | C-04, C-05, `web/builtin.py:206-216`, `web/pdf.py:100-130`, `web/crawl4ai_provider.py:90-120`, `web/parallel_provider.py:81-83` | 필드별 사용처를 grep으로 대조. |
| R-06 | `web/base.py:166-182`, 각 provider `search`, `cli/research.py:63-80`, `grep -rn "get_provider("` 결과 호출부 4곳(fetch, fetch_batch, fetcher, research) | `.search(` 호출은 `research.py:64` 하나. |
| R-07 | 각 provider 생성자(`exa:46-58`, `tavily:42-54`, `serply:48-52`), `parallel_provider.py:21-22`(import) | 키 이름은 코드 상수. |
| R-08 | `grep -rn "check_url\|safe_get\|httpx\.(get\|post\|Client)"` 결과: 관문 사용처는 builtin·pdf·crawl4ai·`cli/fetch.py:794`·`core/oa.py:144,528`. 비관문: `scholar/base.py:202`, `core/scholar.py:217`, `core/embed.py:73,86`, `serply:55`. | feature map·next.md의 미확인 질문("모든 외부 요청 호출부가 safe_get을 거치는지")에 대한 답: 거치지 않는다. exa·tavily·serply·parallel의 `fetch`는 URL을 외부 서비스에 넘기므로 로컬 관문 개념이 적용되지 않는다. |
| R-09 | C-09~C-11 | 순서를 코드에서 추적. **문서와 구현의 차이**: `check_url` docstring은 "허용 호스트에도 스킴과 DNS 검사가 적용된다"고 쓰나, 구현은 호스트명 허용 일치 시 `_resolve` 전에 `return`한다(`safe_http.py:339-340`). 스킴·파서 검사만 적용된다. 구현을 사실로 썼다. |
| R-10 | C-08 | 직접 읽음. 6to4 비트 연산(`int(ip) >> 80 & 0xFFFFFFFF`)은 읽기만 했다. |
| R-11 | C-09, C-11 | 직접 읽음. |
| R-12 | C-11, `core/oa.py:153-154`(`check_oa_url`의 자격증명 거부) | feature map 12행이 "자격증명"을 SSRF 관문 항목으로 적었지만 `check_url`에는 자격증명 검사가 없고 OA 후보 URL 검사에만 있다. `grep -rn "username\|password\|userinfo\|credential" web/` 결과 없음. |
| R-13 | C-12 | 직접 읽음. 리다이렉트 횟수는 `range(max_redirects + 1)`. |
| R-14 | `web/builtin.py:206-230`, `web/pdf.py:84-130`, `web/crawl4ai_provider.py:123-198`, `:395-409`, `:347-356`, `core/config.py:16-24` | 직접 읽음. crawl4ai 플래그 제거는 SDK 버전 0.7.3~0.9.4 범위용이라는 주석을 근거로 하고, 실제 SDK에서의 효과는 확인하지 못함. |
| R-15 | C-14 | 직접 읽음. |
| R-16 | C-14(`:237-266`) | 직접 읽음. `get_text(separator="\n")`가 노드마다 줄을 나누는 결과는 bs4 API 지식에서 추론한 것이고 실행하지 않았다(추론). |
| R-17 | C-15 | 직접 읽음. `handle_data`가 제목 텍스트 처리 뒤에 return하지 않아 본문에도 남는 점(`:119-131`)과 제거 태그가 불리언인 점(`:73-74,:82-84,:103-105`)도 코드에서 확인. |
| R-18 | C-13, 모듈 주석(`web/builtin.py:24-29`) | 동기는 주석에서 가져온 것이라 추론. |
| R-19 | C-16(`pdf.py:35-48`, `:133-139`) | 직접 읽음. |
| R-20 | C-16, C-17 | 직접 읽음. |
| R-21 | C-17(`pdf.py:142-224`) | 직접 읽음. pymupdf API 동작은 가정. |
| R-22 | C-17, `web/builtin.py:165-198`, `web/crawl4ai_provider.py:299-336` | 직접 읽음. |
| R-23 | C-20(`:231-297`), C-18 | 직접 읽음. |
| R-24 | C-20(`:299-336`), C-18, C-02 | 직접 읽음. |
| R-25 | C-21(`:395-458`) | 직접 읽음. crawl4ai의 `result.url`이 요청 URL이고 착지 URL은 `redirected_url`이라는 설명은 코드 주석(`:404-406`)이 근거. |
| R-26 | C-21(`:338-393`) | 직접 읽음. |
| R-27 | C-19(`:200-225`) | 직접 읽음. |
| R-28 | C-22(`:460-587`) | 직접 읽음. |
| R-29 | C-02, C-05 | 직접 읽음. |
| R-30~R-33 | C-23~C-26 | 직접 읽음. 외부 응답 형태는 가정. |
| R-34 | `cli/setup.py:18-186`, `:188-332` | 직접 읽음. 경계만 정리했고 `install` 본체는 읽지 않았다. |
| T-01~T-16 | R-ID별 코드 경로 | 모두 실행하지 않고 코드를 따라가 도출했다(결과 확정은 아님). 따라서 실행으로 확인한 사례가 없다. |

기타 문서와 구현의 차이: `get_provider`의 `ImportError` 문구는 crawl4ai를 extras(`hyperresearch[crawl4ai]`)로 안내하지만 `pyproject.toml`은 `Crawl4AI`를 필수 의존성에도 넣었다. `setup`의 안내문(`cli/setup.py:61,68`, "your agent's built-in WebFetch is used")은 crawl4ai가 없을 때 에이전트의 WebFetch를 쓴다고 말하지만, 설정이 가리키는 `builtin` provider는 `safe_get` 기반 자체 구현이다.

### 2.2 코드 읽는 순서

`web/base.py`(`WebResult`·`get_provider`) → `web/safe_http.py`(`check_url` → `safe_get`) → `web/pdf.py` → `web/builtin.py` → `web/crawl4ai_provider.py`(`fetch` → `_fetch_async` → `_check_final_url` → `fetch_many`) → 나머지 API provider 넷은 각각 `_to_web_result` 위주로. 구현 전략: PDF lane을 provider 바깥 공용 모듈로 뺀 것(#82)과 SSRF 관문을 한 모듈에 모은 것이 핵심이다.

### 2.3 비교·재사용 출처

gpt-researcher의 [스크래퍼 패밀리](../../gpt-researcher/capabilities/scrapers.md)와 같은 계열의 기능이다(웹 페이지 → 텍스트). 이 레포는 스크래퍼가 판정·저장과 분리된 "가져오기만" 계층이고 SSRF 관문이 있다는 점이 다르다. 상세 비교는 하지 않았다.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-08, R-12 | (결정 아님, 검토 항목) exa·tavily·parallel·serply의 `fetch(url)` 앞에도 `check_url`을 둘지, `check_url`에 자격증명 거부를 넣을지 | 원본은 로컬 관문이 없는 경로가 있고 자격증명 URL을 통과시킨다 | 적용 시 R-08, R-12, T-05가 바뀐다 |
