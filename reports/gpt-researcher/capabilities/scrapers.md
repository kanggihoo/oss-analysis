---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/skills/browser.py
  - gpt_researcher/actions/web_scraping.py
  - gpt_researcher/scraper/scraper.py
  - gpt_researcher/scraper/__init__.py
  - gpt_researcher/scraper/utils.py
  - gpt_researcher/scraper/beautiful_soup/beautiful_soup.py
  - gpt_researcher/scraper/pymupdf/pymupdf.py
  - gpt_researcher/scraper/browser/nodriver_scraper.py
  - gpt_researcher/scraper/browser/browser.py
  - gpt_researcher/scraper/arxiv/arxiv.py
  - gpt_researcher/utils/url_security.py
  - gpt_researcher/utils/workers.py
  - gpt_researcher/utils/rate_limiter.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/config/config.py
  - gpt_researcher/agent.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/document/online_document.py
  - .env.example
  - docs/docs/gpt-researcher/gptr/config.md
depends: []
status: draft
reimplementation: 미실행
---

# 스크래퍼 패밀리

> URL 목록을 받아 각 URL에서 본문 텍스트·이미지 후보·제목을 추출하고, 안전하지 않은 URL·실패·차단 페이지·단어 목록·미추출 PDF를 결과에서 걸러 내며, 이미지는 중복을 없애 상위 몇 장만 연구 상태에 기록한다.

<!--
이 스펙의 범위: 기준 SHA의 원본 동작. 우리가 바꾸고 싶은 점은 맨 끝 "적용 메모"에만 둔다.
읽은 구현체: bs(BeautifulSoup), pymupdf(pdf), nodriver 전체, browser(selenium) 일부, arxiv 일부. 나머지는 R-22에서 미확인.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자(연구 파이프라인)가 `BrowserManager.browse_urls(urls)`를 부른다. 이 메서드는 `scrape_urls`를 통해 URL 목록 전체를 담은 `Scraper` 객체를 하나 만든다. 생성자는 URL의 중복(문자열이 완전히 같은 것)을 순서를 지키며 없애고, `SCRAPER`가 `firecrawl`·`tavily_extract`이면 필요한 패키지가 있는지 확인한다(없으면 `pip install`을 시도한다).
2. `Scraper.run()`이 URL마다 `extract_data_from_url` 태스크를 만들어 `asyncio.gather`로 동시에 돌린다. 각 태스크는 먼저 워커 풀의 세마포어(동시 실행 수 제한)를 얻고, 전역 속도 제한 간격을 기다린다.
3. 태스크는 `validate_url`로 URL 안전성을 검사한다(SSRF 방어). 통과하면 `get_scraper`로 구현체를 고른다(`.pdf` 경로 → pdf, 주소에 `arxiv.org` 포함 → arxiv, 그 밖에는 `SCRAPER` 설정값). 구현체가 `(content, image_urls, title)`을 돌려준다.
4. 내용 판정을 이 순서로 한다: 비었거나 100자 미만 → 차단 페이지 표지 → 단어 목록 → PDF 원본 바이트. 마지막 경우에는 PyMuPDF로 한 번 다시 받아 본다. 하나라도 걸리면 `raw_content`가 `None`인 실패 dict가 된다. 예외도 같은 실패 dict로 바뀐다.
5. `run()`이 `raw_content`가 `None`인 항목을 버리고, 성공한 항목만 입력 순서대로 돌려준다. 어떤 URL이 왜 빠졌는지는 호출자에게 전달되지 않는다(로그만 남는다).
6. `scrape_urls`가 성공 항목의 `image_urls`를 한 목록으로 펴서 `(scraped_data, images)`를 돌려주고 HTTP 세션을 닫는다.
7. `browse_urls`가 성공 항목 전부를 연구 소스에 기록하고, 이미지에서 중복을 없앤 최대 4장을 연구 이미지에 기록한 뒤 성공 항목 목록을 돌려준다.

### 1.2 범위·통합 지점

- 제공: URL 목록 → 본문·이미지 후보·제목. 구현 선택(`SCRAPER` 설정과 URL 형태), SSRF 방어, 동시성·속도 제한, 쓸모없는 페이지 걸러내기, 이미지 선별.
- 제외:
  - URL이 어디서 오는지(검색 Retriever, 서브쿼리, 이미 방문한 URL 제거)는 호출자의 일이다. 설명 링크: [retrievers.md](retrievers.md), [research-pipeline.md](research-pipeline.md)(둘 다 아직 없음).
  - 스크랩 결과에서 서브쿼리와 관련된 조각을 고르는 일은 [context-selection.md](context-selection.md)(아직 없음)가 맡는다. 이 스펙은 결과 dict 형식까지만 정의한다.
  - LLM 제공자와 `Config` 로딩은 범위 밖이다. 설정 키는 원문 이름으로만 쓴다.
  - firecrawl, tavily_extract, web_base_loader 구현체의 내부, arxiv·browser(selenium)의 세부는 읽지 않았다(R-22).
- 외부 의존·선행 계약:
  - 호출자는 `researcher` 객체를 준다. 이 객체는 `cfg`(`max_scraper_workers`, `scraper_rate_limit_delay`, `scraper`, `user_agent`), `verbose`, `websocket`, `get_research_images(top_k=10)`, `add_research_images`, `add_research_sources`를 가진다(`agent.py:665-698`).
  - 네트워크: HTTP GET은 `requests.Session`, DNS 조회는 `socket.getaddrinfo`로 한다. 브라우저 구현체는 zendriver(nodriver)나 selenium(browser)이 필요하다. 설정은 설정 스펙이 아직 없으므로 키·기본값만 1.3에 쓴다.
- 소유 상태·부작용:
  - `Scraper`는 호출마다 새로 만들어지고 자기 `requests.Session`(User-Agent 헤더 포함)을 가진다. `scrape_urls`가 끝날 때 닫는다.
  - `BrowserManager`는 연구 하나(`GPTResearcher` 인스턴스)당 하나이고 `WorkerPool`을 가진다. 풀 안의 세마포어와 스레드 풀은 연구마다 따로다.
  - 전역 속도 제한기는 프로세스 전체에서 하나(싱글턴)다.
  - `browse_urls`는 `researcher.research_sources`와 `researcher.research_images`를 덧붙여 바꾼다.
  - nodriver는 클래스 변수로 브라우저 풀을 가진다(최대 5개).
  - `_check_pkg`는 `pip install`로 환경을 바꿀 수 있다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `BrowserManager(researcher)` | `WorkerPool(cfg.max_scraper_workers, cfg.scraper_rate_limit_delay)` 생성 | 연구마다 하나. 기본값 `MAX_SCRAPER_WORKERS` 15, `SCRAPER_RATE_LIMIT_DELAY` 0.0(제한 없음) |
| `browse_urls(urls)` | 입력: list of string. 출력: list of 결과 dict | 성공한 URL만 담는다. 순서는 중복 제거 후 입력 순서. 실패 URL 정보는 없다 |
| `select_top_images(images, k=2)` | 입력: list of 이미지 dict, 정수 k. 출력: list of string(URL) | `browse_urls`는 `k=4`로 부른다. 기본값 2는 호출되지 않는다 |
| `scrape_urls(urls, cfg, worker_pool)` | 출력: (list of 결과 dict, list of 이미지 dict) | 두 번째는 모든 성공 항목의 `image_urls`를 이어 붙인 것(점수 정렬 아님, 중복 제거 안 함) |
| `Scraper(urls, user_agent, scraper, worker_pool)` | `.urls`(중복 제거됨), `.session`, `.run()` | `scraper`는 `SCRAPER` 값 문자열 |
| 결과 dict(성공) | `{url: string, raw_content: string, image_urls: list of 이미지 dict, title: string}` | `raw_content`는 길이 100 이상이고 판정을 통과한 것. 호출자에게 전달되는 것은 이 형태뿐 |
| 결과 dict(실패, 내부용) | `{url, raw_content: None, image_urls: [], title}` | `run()`에서 버려진다. 안전하지 않은 URL·예외는 `title`이 `""`이고, 내용 판정 거절은 구현체가 준 `title`을 남긴다 |
| 이미지 dict | `{url: string(http 또는 https 절대 URL), score: int 0~4}` | 페이지당 최대 10개(`get_relevant_images`). pdf·arxiv는 항상 빈 목록 |
| 구현체 계약 | 생성자 `(link, session)`. `scrape()` 동기 또는 `scrape_async()` 비동기. 반환 `(content: string, image_urls: list, title: string)` | `scrape_async`가 있으면 그것을 쓴다. 실패는 `("", [], "")`가 관례이나 nodriver는 예외다(R-19) |
| `SCRAPER` | string. 기본 `bs` | 값 `bs`, `browser`, `nodriver`, `firecrawl`, `tavily_extract`, `web_base_loader`, `pdf`, `arxiv` 중 하나(`pdf`·`arxiv`도 직접 쓸 수 있다). 그 밖의 값은 설정 시점이 아니라 URL마다 `Scraper not found.` 실패가 된다 |
| `MAX_SCRAPER_WORKERS` | int. 기본 15 | 연구당 동시 처리 수와 스레드 풀 크기 |
| `SCRAPER_RATE_LIMIT_DELAY` | float. 기본 0.0 | 프로세스 전체에서 요청 시작 사이의 최소 간격(초). 0 이하면 제한 없음 |
| `USER_AGENT` | string | 기본값은 Chrome 119 Edge 문자열(`default.py:21`). 세션 헤더에 들어간다. 브라우저 구현체는 자기 UA를 따로 쓴다 |
| `ALLOW_PRIVATE_URLS` | 환경변수 string. `Config` 키가 아님 | `1`, `true`, `yes`, `on`(앞뒤 공백·대소문자 무시)이면 사설 주소 검사를 건너뛴다. 매 `validate_url` 호출마다 읽는다 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Scraper`에 중복 URL이 든 목록을 준다 | 문자열이 완전히 같은 URL은 첫 번째만 남고 순서는 유지된다. 정규화(끝 슬래시, 대소문자, 프래그먼트)는 하지 않는다 | 코드 확인 (C-04) |
| R-02 | URL이 여러 개다 | 태스크는 모두 동시에 시작되지만 풀의 세마포어(크기 `max_workers`)를 얻은 것만 진행한다. 세마포어를 얻은 뒤 전역 제한기에서 `delay`가 지나기를 기다린다(제한기는 잠금 안에서 자므로 시작 시각이 `delay` 간격으로 직렬화된다). 동기 `scrape()`는 풀의 스레드 풀(크기 `max_workers`)에서 돌고, `scrape_async()`는 이벤트 루프에서 직접 await된다. 풀을 만들 때 `delay`가 숫자가 아니거나 음수면 `ValueError`다 | 코드 확인 (C-03) |
| R-03 | URL 하나의 처리 | 순서: 풀 통과 → `validate_url` → `get_scraper` → 구현체 생성 → `scrape` → 내용 판정(R-09~R-12). 도중 예외는 모두 잡혀 로그를 남기고 `title`이 `""`인 실패 dict가 된다. 한 URL의 실패는 다른 URL에 영향을 주지 않는다 | 코드 확인 (C-05) |
| R-04 | `validate_url(url)` | 아래를 어기면 `UnsafeURLError`. (a) 문자열이 아니거나 공백뿐이다. (b) 스킴이 `http`·`https`가 아니다(소문자로 비교, 스킴 없는 경로·`file://`·`ftp://` 포함). (c) 호스트가 없다. (d) 호스트를 `getaddrinfo`로 풀지 못했다. (e) 풀린 주소 중 하나라도 private·loopback·link-local·reserved·multicast·unspecified에 속한다(IPv4·IPv6 모두). 모두 통과하면 입력을 그대로 돌려준다. 거절된 URL은 경고 로그를 남기고 실패 dict(`title` `""`)가 되며 어떤 요청도 보내지 않는다 | 코드 확인 (C-06), 실행 확인(T-01~T-05) |
| R-05 | 환경변수 `ALLOW_PRIVATE_URLS`가 참 값이다 | (a)~(c) 검사는 그대로 하고, DNS 조회와 (e) 검사는 하지 않는다. 그래서 풀리지 않는 호스트도 통과한다. 참 값이 아니면(`false`, `y` 등) 검사한다 | 코드 확인 (C-06), 실행 확인(T-06) |
| R-06 | `get_scraper(link)` | 우선순위: (1) `urlparse(link).path`를 소문자로 바꿔 `.pdf`로 끝나면 `pdf`(PyMuPDF). (2) 링크 전체 문자열에 `arxiv.org`가 들어 있으면 `arxiv`. (3) 아니면 `SCRAPER` 값. 1·2번은 `SCRAPER`가 `firecrawl` 등이어도 이긴다. 표에 없는 키는 `Scraper not found.` 예외가 되어 R-03대로 실패한다 | 코드 확인 (C-07) |
| R-07 | `Scraper` 생성 시 `SCRAPER`가 `tavily_extract` 또는 `firecrawl` | `importlib.util.find_spec`으로 `tavily` 또는 `firecrawl`을 찾고, 없으면 `pip install tavily-python` 또는 `firecrawl-py`를 현재 인터프리터(`sys.executable -m pip`)로 동기 실행한다. 성공하면 캐시를 무효화하고 계속한다. 실패(`CalledProcessError`)하면 `ImportError`가 생성자에서 올라오고, `scrape_urls`가 이를 잡아 빨간 오류를 출력한 뒤 `([], [])`를 돌려준다. 즉 그 호출의 URL 전체가 소리 없이 사라진다. 다른 `SCRAPER` 값은 설치를 시도하지 않는다. 설치 확인은 `browse_urls` 호출마다(`Scraper` 생성마다) 한다 | 코드 확인 (C-04, C-08, C-09). 실제 설치는 실행하지 않음 |
| R-08 | 구현체 호출과 반환 | 구현체 클래스에 `scrape_async`가 있으면 await하고(nodriver, firecrawl), 없으면 풀의 스레드 풀에서 `scrape`를 돌린다. 반환은 `(content, image_urls, title)` 세 값이다 | 코드 확인 (C-05) |
| R-09 | `content`가 비었거나 100자 미만 | 실패. `title`은 구현체가 준 값을 남긴다. 이 검사가 가장 먼저이므로 차단 페이지·PDF 판정은 100자 이상일 때만 일어난다 | 코드 확인 (C-05) |
| R-10 | 내용의 앞 5000자(소문자로 바꾼 것)에 차단 표지 8개 중 하나가 부분 문자열로 들어 있다 | 실패(`Anti-bot/challenge page detected`). 5000자 이후에 있는 표지는 보지 않는다. 표지의 `you're`는 ASCII 따옴표이므로 둥근 따옴표는 맞지 않는다 | 코드 확인 (C-01), 실행 확인(T-07) |
| R-11 | 내용이 200,000자 이상이고 문장 끝 문자(`.`, `!`, `?`, `。`, `！`, `？`)의 비율이 1/5000 미만이다(같으면 통과) | 실패(`Word-list-like content detected`). 200,000자 미만이면 이 검사는 하지 않는다. 전체 문자를 센다 | 코드 확인 (C-02), 실행 확인(T-08) |
| R-12 | 내용이 PDF 원본 바이트로 보이고(`%PDF-`로 시작하거나, 구조 표지 5개 중 2개 이상이 대소문자 구분해 어디서든 들어 있다) 선택된 구현체가 PyMuPDF가 아니다 | PyMuPDF로 같은 URL을 한 번 더 받아 본다(풀의 스레드 풀에서 동기 실행, 속도 제한을 다시 거치지 않고, URL 검증도 다시 하지 않는다). 재시도 결과가 100자 이상이면 그것을 성공으로 돌려준다(차단 페이지·단어 목록 검사는 다시 하지 않는다). 아니면 `raw_content` `None`, `title`은 처음 구현체가 준 값으로 실패한다. 선택된 구현체가 이미 PyMuPDF이면 이 검사로 거르지 않고 내용을 그대로 성공으로 돌려준다. 이 검사는 R-10·R-11 뒤에 있다 | 코드 확인 (C-03, C-05), 실행 확인(T-09) |
| R-13 | `run()`의 결과 정리 | 각 URL의 결과 중 dict이면서 `raw_content`가 `None`이 아닌 것만 남긴다. 나머지는 버려지고 호출자에게 실패 목록·사유가 전달되지 않는다. 남은 항목의 순서는 중복 제거된 입력 순서다 | 코드 확인 (C-04) |
| R-14 | `scrape_urls` | 성공 항목마다 `image_urls`가 비어 있지 않으면 `images`에 이어 붙인다(dict가 아닌 항목은 건너뜀). 전체가 예외(생성자 포함)로 끝나면 오류를 출력하고 그 시점의 `scraped_data`(생성자·`run()`에서 터졌으면 `[]`)와 `images`를 돌려준다. 끝나면 항상 세션을 닫는다 | 코드 확인 (C-10) |
| R-15 | `browse_urls` 호출 | `verbose`면 시작·결과 수·이미지 수·완료 로그를 스트리밍한다. 성공 항목 전부를 `add_research_sources`로 기록하고(`image_urls` 포함 그대로), `select_top_images(images, k=4)` 결과를 `add_research_images`로 기록하고, 성공 항목 목록을 돌려준다. URL이 0개여도 같은 경로를 탄다(`SCRAPER`가 `firecrawl`이면 패키지 확인도 한다) | 코드 확인 (C-11) |
| R-16 | `select_top_images(images, k)` | 점수 내림차순(동점은 입력 순서)으로 훑으며, 이미지 해시가 이번 호출에서 아직 안 나왔고 URL이 연구 이미지 목록에 아직 없으면 채택한다. k개가 차면 멈춘다. 해시는 파일명(경로 마지막 조각)에 쿼리 파라미터 `url` 값을 붙여 MD5한 것이다(호스트가 달라도 파일명이 같으면 같은 이미지로 본다). 해시 계산이 실패하면(`None`) 건너뛴다. "이미 있는 이미지"는 `get_research_images()`의 기본 `top_k=10` 때문에 연구 이미지 목록의 앞 10개만 비교한다. 연구 이미지로 채택할 것을 정하는 지점은 여기뿐이다(페이지별 후보 10개 추림은 `get_relevant_images`) | 코드 확인 (C-11, C-12, C-18), 실행 확인(T-10) |
| R-17 | bs 구현체: 페이지 가져오기 | `session.get(link, timeout=10)`. 예외이거나 상태 코드가 429·500·502·503·504이면 1초 쉬고 한 번만 다시 시도한다(둘째도 실패면 포기). 그 밖의 400 이상은 재시도 없이 포기. `Content-Length`가 10MB(10×1024×1024)를 넘으면 포기(헤더가 없거나 숫자가 아니면 크기 검사 없음). 포기하면 `("", [], "")`. 리다이렉트는 `requests` 기본값대로 따라간다고 본다 | 코드 확인 (C-13). 리다이렉트 추종은 `requests` 기본 동작이라 추론 |
| R-18 | bs 구현체: 파싱 | 응답 헤더 `Content-Type`에 `charset`이 있을 때만 `response.encoding`을 인코딩으로 쓰고 아니면 BeautifulSoup이 감지하게 한다. `lxml` 파서로 파싱 → `clean_soup` → `get_text_from_soup`(본문) → `get_relevant_images` → `extract_title`. 파싱 중 예외는 `("", [], "")` | 코드 확인 (C-13, C-14) |
| R-19 | nodriver 구현체(공통 규칙의 예외) | 공유 브라우저 풀에서 브라우저를 빌려(최대 5개, 한 브라우저의 처리 수가 8 이상이면 새로 띄움, `headless=False`로 시작) 탭을 열고, 같은 도메인은 동시에 한 탭씩(대기했으면 0.6~1.2초 쉼) 처리한다. 로드 완료·유휴를 각 2초까지 기다리고 최대 500% 또는 바닥까지 스크롤한 뒤 HTML을 받아 bs와 같은 방식으로 추출한다. 추출 텍스트가 200자 미만이면 경고 로그만 남기고 그대로 돌려준다. 실패하면 빈 값이 아니라 오류 문자열을 `content`로 돌려준다(`zendriver` 미설치 `ImportError` 문구, `Browser failed to open page (returned None)`, 일반 예외의 `str(e)`). 이 문자열이 100자 이상이면 R-09를 통과해 본문으로 취급된다(zendriver 미설치 문구는 103자). 끝나면 탭을 닫고 처리 수가 0이면 브라우저를 종료한다 | 코드 확인 (C-15). 길이 103은 소스의 문자열로 센 값. 실제 브라우저는 실행하지 않음 |
| R-20 | pymupdf 구현체 | URL이면 `session`(없으면 `requests`)으로 `timeout=(5, 30)`, `stream=True` GET 후 `raise_for_status`. `SSLError`면 `verify=False`로 한 번 다시 받는다. 임시 `.pdf` 파일에 8192바이트씩 쓰고 `PyMuPDFLoader`로 읽은 뒤 임시 파일을 지운다(읽기가 실패해도). 내용은 모든 페이지의 `page_content`를 줄바꿈으로 이은 것, 이미지는 항상 `[]`, 제목은 첫 페이지 메타데이터의 `title`(없으면 `""`). 타임아웃·그 밖의 모든 예외는 메시지를 출력하고 `("", [], "")`. 크기 상한은 없다. 텍스트가 없는 스캔 PDF는 내용이 짧아 R-09로 거절된다 | 코드 확인 (C-16) |
| R-21 | 텍스트·이미지 추출 보조 함수(bs, nodriver 등이 공유) | `clean_soup`이 `script`, `style`, `footer`, `header`, `nav`, `menu`, `sidebar`, `svg` 태그와 클래스에 `nav`, `menu`, `sidebar`, `footer`가 있는 요소를 지운다. `get_text_from_soup`이 블록 요소마다 한 줄로 텍스트를 만들고(`pre` 등은 원문 유지) 줄바꿈으로 잇고 연속 공백 2개 이상을 한 칸으로 줄인다. `get_relevant_images`의 점수·건너뛰기 규칙은 C-12. 제목은 `<title>` 텍스트(없으면 `""`) | 코드 확인 (C-12, C-14는 참고). bs4 미설치로 이 함수들은 실행하지 못함 |
| R-22 | firecrawl, tavily_extract, web_base_loader, arxiv, browser(selenium) | 세부 동작은 읽지 않았다. 공통 계약의 모양만 확인했다: 모두 `(content, image_urls, title)`을 돌려주고 실패 관례는 `("", [], "")`로 보인다(`return` 줄 grep). firecrawl·tavily_extract는 API 키를 환경변수(`FIRECRAWL_API_KEY` 등)로 요구하는 것으로 보인다. selenium `BrowserScraper`는 생성자에서 selenium 미설치면 `ImportError`를 내고(R-03으로 실패 처리), `scrape()`는 예외를 삼켜 `("", [], "")`를 돌려주며, 페이지 로드 시간 초과 때는 `"Page load timed out"`(19자, R-09로 거절)을 돌려준다. arxiv는 논문 초록을 `Published: ...; Author: ...; Content: <초록>` 한 문장으로 만든다 | 일부 코드 확인(위 서술에 적은 줄) / 나머지 미확인 |
| R-23 | `filter_urls`, `process_scraped_data`, `extract_main_content` | 이 세 함수는 `web_scraping.py`에 있지만 저장소의 비테스트 코드 어디서도 호출되지 않는다. 스크랩 경로에는 도메인 제외 필터도 없다(`excluded_domains`는 `Config` 키가 아님) | 코드 확인 (grep) |
| R-24 | 호출자 쪽 상태(경계) | 호출자(`ResearchConductor`)는 대체로 `_get_new_urls`로 URL을 `visited_urls`에 먼저 넣은 뒤 스크랩을 부른다(순서 섞기도 그 전). 그래서 스크랩에 실패한 URL도 같은 연구 안에서 다시 시도되지 않는다. `_extract_content` 경로만 스크랩 뒤에 `visited_urls`를 갱신한다 | 코드 확인 (경계. `researcher.py:813-834`, `:932`, `:965`, `:1095`) |

- 불변식:
  - `browse_urls`가 돌려주는 모든 항목은 `raw_content`가 문자열이다(`None` 없음). 구현체가 PyMuPDF가 아니면 PDF 표지 판정을 통과한 것이다.
  - 같은 URL 문자열은 한 번의 `Scraper` 안에서 한 번만 가져온다. 다른 `browse_urls` 호출 사이의 중복 제거는 이 기능이 아니라 호출자가 한다.
  - 안전하지 않다고 판정된 URL에는 구현체가 만들어지지도 않는다(`ALLOW_PRIVATE_URLS`가 거짓일 때).
- 미결정:
  - R-22 · firecrawl, tavily_extract, web_base_loader의 내부 동작(요청 형식, 이미지 추출, 오류 처리, 동시성 제한)과 arxiv의 id 추출 규칙(`_ID_RE`)·네트워크 오류 처리, browser(selenium)의 쿠키·스크롤 단계는 읽지 않았다. `SCRAPER`가 이 값들일 때의 재현은 이 스펙만으로는 안 된다. `bs`, `pdf`, `nodriver`(그리고 공통 판정)만 재현 가능하다.
  - R-21 · `get_text_from_soup`, `get_relevant_images`, `clean_soup`는 소스를 읽었지만 bs4가 설치돼 있지 않아 실행하지 못했다. 구현 영향은 작지만 줄 단위 텍스트 모양은 실행 검증이 없다.
- 확인 한계:
  - 실제 네트워크 요청, 브라우저, `pip install`은 실행하지 않았다(9장: 외부 접속·새 패키지). 실행한 것은 `url_security`와 `scraper.py`의 판정 함수·`select_top_images`·`get_image_hash`를 소스 줄 그대로 불러온 오프라인 실험이다(2.1 끝 참고).
  - `validate_url`이 확인한 IP와 `requests`가 실제로 접속하는 IP가 같다는 보장은 없다. 모듈 docstring도 DNS rebinding 틈이 남는다고 적는다. 리다이렉트로 이동한 주소를 다시 검증하는 코드는 찾지 못했다(`requests` 기본 동작이 리다이렉트를 따르므로 사설 주소로 가는 리다이렉트가 막히지 않을 수 있다 — 추론, 미실행).
  - `ipaddress`의 판정은 Python 버전에 따라 다를 수 있다. 실험은 Python 3.12.13에서 했다(T-04의 100.64.0.0/10).

### 1.5 필수 코드 참조

라이선스: 인용 허용 여부는 overview 1절(Apache 2.0 LICENSE와 MIT 표기가 어긋남)을 따른다. 이 스펙은 코드를 옮겨 적지 않고 위치만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/scraper/scraper.py:31-55`, `:73-75` `_BLOCK_PAGE_MARKERS`, `_BLOCK_PAGE_CHECK_PREFIX_LEN`, `_looks_like_block_page` | 차단 표지 8개 문자열(소문자), 검사 길이 5000자, 소문자화 후 부분 문자열 검사 | R-10 |
| C-02 | `scraper.py:57-70`, `:78-82` `_MIN_LENGTH_FOR_WORDLIST_CHECK`, `_MAX_SENTENCE_DENSITY`, `_SENTENCE_ENDING_CHARS`, `_looks_like_word_list` | 단어 목록 판정 상수와 식 | R-11 |
| C-03 | `scraper.py:85-106` `_PDF_STRUCTURE_MARKERS`, `_MIN_PDF_MARKER_HITS`, `_looks_like_unextracted_pdf`; `scraper.py:284-305` `_retry_as_pdf` | PDF 구조 표지 5개, 2회 이상, `%PDF-` 접두사 검사, PyMuPDF 재시도와 100자 기준 | R-12 |
| C-04 | `scraper.py:114-158` `Scraper.__init__`, `run` | 중복 제거(`dict.fromkeys`), `_check_pkg` 호출 조건, 세션 헤더, `gather`와 결과 필터 | R-01, R-07, R-13 |
| C-05 | `scraper.py:194-281` `extract_data_from_url`, `_reject` | 풀 통과, 검증, 구현체 호출, 판정 순서, 실패 dict 모양 | R-02, R-03, R-08, R-09, R-12 |
| C-06 | `gpt_researcher/utils/url_security.py:35-57`, `:60-116` `ALLOWED_SCHEMES`, `_private_urls_allowed`, `_is_disallowed_ip`, `validate_url` | 스킴 허용, 호스트 필수, `ALLOW_PRIVATE_URLS` 참 값 목록, 금지 주소 범주, 모든 해석 주소 검사 | R-04, R-05 |
| C-07 | `scraper.py:307-352` `get_scraper` | 키-클래스 표 8개(`pdf`, `arxiv`, `bs`, `web_base_loader`, `browser`, `nodriver`, `tavily_extract`, `firecrawl`)와 선택 우선순위 | R-06 |
| C-08 | `scraper.py:160-192` `_check_pkg` | 설치 패키지명(`tavily-python`→`tavily`, `firecrawl-py`→`firecrawl`)과 설치 실행·실패 처리 | R-07 |
| C-09 | `gpt_researcher/scraper/__init__.py:1-9` | 구현체 클래스 이름의 등록(8개) | R-06 |
| C-10 | `gpt_researcher/actions/web_scraping.py:12-51` `scrape_urls` | `Scraper` 생성·실행, 이미지 펴기, 예외 삼킴, 세션 닫기 | R-14 |
| C-11 | `gpt_researcher/skills/browser.py:25-115` `BrowserManager.__init__`, `browse_urls`, `select_top_images` | 풀 생성 인자, 기록 호출 순서, `k=4`, 이미지 선별 알고리즘 | R-15, R-16 |
| C-12 | `gpt_researcher/scraper/utils.py:16-86`, `:101-120` `get_relevant_images`, `parse_dimension`, `get_image_hash` | 이미지 점수표(클래스 6개 → 4점, 크기별 3/2/1/0점, 작은 이미지 건너뜀), 페이지당 최대 10개, 해시 정의 | R-16, R-21 |
| C-13 | `gpt_researcher/scraper/beautiful_soup/beautiful_soup.py:11-104` `RETRYABLE_STATUS_CODES`, `MAX_CONTENT_BYTES`, `scrape`, `_fetch` | bs 구현체 전체: 재시도 상태 코드, 10MB 상한, 인코딩, 처리 순서 | R-17, R-18 |
| C-14 | `scraper/utils.py:88-99`, `:123-226` `extract_title`, `clean_soup`, `_block_lines`, `get_text_from_soup` | 지울 태그·클래스 목록, 블록 요소 목록, 줄 만들기, 공백 정리 | R-18, R-21 |
| C-15 | `gpt_researcher/scraper/browser/nodriver_scraper.py:136-172`, `:185-260` `get_browser`, `scrape_async` | 브라우저 풀 선택, 로드·스크롤 순서, 오류를 문자열로 돌려주는 분기 | R-19 |
| C-16 | `gpt_researcher/scraper/pymupdf/pymupdf.py:34-87` `PyMuPDFScraper.scrape` | PDF 내려받기·재시도·임시 파일·내용 이음 | R-20 |
| C-17 | `gpt_researcher/utils/workers.py:8-50`, `gpt_researcher/utils/rate_limiter.py:51-91` `WorkerPool`, `GlobalRateLimiter.configure`, `wait_if_needed` | 세마포어·스레드 풀 크기, 전역 간격 대기, 잘못된 delay의 `ValueError` | R-02 |
| C-18 | `gpt_researcher/agent.py:665-698` `get_research_images`, `add_research_images`, `add_research_sources` | 연구 이미지 조회는 앞 `top_k`(기본 10)개, 추가는 덧붙임 | R-15, R-16 |
| C-19 | `gpt_researcher/config/variables/default.py:21`, `:28-30` | `USER_AGENT`, `SCRAPER`, `MAX_SCRAPER_WORKERS`, `SCRAPER_RATE_LIMIT_DELAY` 기본값 | 1.3 |

### 1.6 수락 사례

출처: T-01~T-10은 구현에서 도출하고, 실제 소스 줄을 불러와 오프라인(네트워크·bs4 없이)으로 실행해 관찰했다(2.1 끝 참고). T-11 이후는 구현에서 도출(미실행)이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04 | `ALLOW_PRIVATE_URLS` 없음. `file:///etc/passwd`, `ftp://example.com/x`, `/etc/passwd` | 모두 `UnsafeURLError`(스킴 불허). 스킴이 없으면 메시지에 `(none)` |
| T-02 | R-04 | 같은 조건. `http://` | `UnsafeURLError`(호스트 없음) |
| T-03 | R-04 | 같은 조건. `http://127.0.0.1/`, `http://10.0.0.1/`, `http://169.254.169.254/latest/meta-data`, `http://[::1]/`, `http://0.0.0.0/`, `http://224.0.0.1/`, `http://192.0.2.1/`, `http://[::ffff:127.0.0.1]/` | 모두 `UnsafeURLError`(비공개 주소) |
| T-04 | R-04 | 같은 조건. `http://100.64.0.1/`, `http://100.100.100.200/`(CGNAT 대역 100.64.0.0/10) | 통과(거절되지 않음). 이 대역은 금지 범주에 들지 않는다. Python 3.12.13에서 관찰 |
| T-05 | R-04 | 같은 조건. `http://93.184.216.34/`, `HTTP://93.184.216.34/`, 앞뒤 공백이 있는 같은 주소, 풀리지 않는 호스트 `http://no-such-host.invalid/` | 앞 세 개는 통과(반환값은 입력 그대로, 공백 유지). 마지막은 `UnsafeURLError`(해석 실패) |
| T-06 | R-05 | `ALLOW_PRIVATE_URLS`가 `" TRUE "`일 때 `http://127.0.0.1/`, `file:///x`, `http://no-such-host.invalid/` | 첫째·셋째 통과, 둘째는 스킴 불허. 값이 `false` 또는 `y`면 `http://127.0.0.1/`은 거절 |
| T-07 | R-10 | 내용에서 `Please verify you are a human`의 시작이 4990번째 문자 근처 / 5000자 뒤 / 전부 대문자 `ATTENTION REQUIRED! \| CLOUDFLARE` / 둥근 따옴표 `Making sure you’re not a bot` | 차단 판정: 예 / 아니오 / 예 / 아니오 |
| T-08 | R-11 | 길이 200,000자에서 문장 끝 문자 0개 / 39개 / 40개 / 41개. 길이 199,999자에 0개. 한자 199,900자 + `。` 100개 | 단어 목록 판정: 예 / 예 / 아니오 / 아니오. 199,999자는 아니오. 한자 사례는 아니오 |
| T-09 | R-12 | 내용 `%PDF-1.4 abc` / `xref ... trailer` / `see the trailer` / `ENDOBJ ENDSTREAM` / ` %PDF-1.4`(앞 공백) | PDF 원본 판정: 예 / 예 / 아니오(표지 1개) / 아니오(대소문자 구분) / 아니오 |
| T-10 | R-16 | 연구 이미지 11개(`http://old/0.png`~`old/10.png`), 후보(URL, 점수): `s/a.png` 1, `s/b.png` 4, `t/b.png` 3, `old/10.png` 5, `s/c.png` 0, `s/d.png` 2, `s/e.png` 2, `old/3.png` 9. `k=4`, 그다음 `k=10` | `k=4`: `old/10.png`, `s/b.png`, `s/d.png`, `s/e.png`. `old/3.png`는 앞 10개 안이라 제외, `old/10.png`는 11번째라 비교되지 않아 채택, `t/b.png`는 `s/b.png`와 파일명이 같아 제외, `d`·`e` 동점은 입력 순서. `k=10`: 위 네 개 뒤에 `s/a.png`, `s/c.png`가 이어짐 |
| T-11 | R-01, R-13 | `Scraper`에 `[A, B, A]`를 준다(A는 성공, B는 안전하지 않은 URL) | 세션 요청은 A 한 번. `run()` 결과는 `[A의 dict]` 하나. B는 로그 경고만 남기고 결과에 없음 |
| T-12 | R-06 | `SCRAPER=bs`. 링크 `https://h.com/doc.PDF?sig=1` / `https://example.com/arxiv.org-notes` / `https://example.com/p` | 각각 PyMuPDF / arxiv / bs 구현체. `SCRAPER=foo`이면 셋째는 `Scraper not found.`로 실패(URL마다) |
| T-13 | R-12 | 구현체가 bs, 링크에 `.pdf`가 없고, 응답 본문이 `%PDF-`로 시작하는 바이너리를 텍스트로 파싱한 150자 이상 문자열. PyMuPDF 재시도가 1000자 텍스트를 줌 | 결과의 `raw_content`는 재시도가 준 1000자. 재시도도 100자 미만이면 `raw_content` `None`이라 결과에서 빠진다 |
| T-14 | R-09, R-19 | `SCRAPER=nodriver`, `zendriver` 미설치 | 구현체가 `The zendriver package is required to use NoDriverScraper. Please install it with: pip install zendriver`(103자)를 content로 돌려주고 R-09~R-12를 통과해 결과 항목의 `raw_content`가 된다 |
| T-15 | R-07, R-14 | `SCRAPER=firecrawl`, `firecrawl` 패키지 없음, `pip install`이 실패 | `ImportError`가 `scrape_urls`에서 잡혀 `([], [])`. `browse_urls`는 빈 목록을 돌려주고 연구 소스·이미지는 늘지 않는다 |
| T-16 | R-17 | bs, 첫 응답 503, 둘째 응답 200 / 첫 응답 404 / 첫 응답 예외, 둘째 예외 | 200 응답 파싱 / 재시도 없이 `("", [], "")` / `("", [], "")`. 재시도 사이는 1초 쉼 |
| T-17 | R-20 | 스캔 PDF(텍스트 층 없음)를 `.pdf` URL로 받음 | 구현체는 빈 문자열에 가까운 내용을 돌려주고 R-09로 거절된다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-04 `scraper.py:121-124` | 코드를 읽음 |
| R-02 | C-17, `scraper.py:198`, `:221-230` | 코드를 읽음. 세마포어는 `WorkerPool.__init__`에서 `asyncio.Semaphore(max_workers)`(`workers.py:28`). 제한기는 `asyncio.Lock`을 지연 생성(`rate_limiter.py:44-49`) |
| R-03 | C-05 `scraper.py:198-274` | 코드를 읽음 |
| R-04 | C-06. 같은 `validate_url`을 `document/online_document.py:42`(소스 모드의 문서 URL)도 쓴다(이 스펙 밖) | 코드를 읽고 `url_security.py` 원본 파일을 그대로 불러와 실행(T-01~T-05). `getaddrinfo`는 IP 리터럴이 대부분이라 실제 DNS는 `no-such-host.invalid`만 거침 |
| R-05 | C-06 `url_security.py:37`, `:44-45`, `:92-95` | 실행(T-06) |
| R-06 | C-07, C-09 | 코드를 읽음. `SCRAPER=foo`의 결과는 `get_scraper`의 `raise`와 R-03의 `except`를 이은 것(미실행) |
| R-07 | C-08, C-04 `scraper.py:128-131`, `web_scraping.py:34-44` | 코드를 읽음. `pip install`은 실행하지 않음 |
| R-08 | C-05 `scraper.py:221-230`, `firecrawl.py:107-121`(`scrape_async` 존재만), `nodriver_scraper.py:190` | `hasattr` 분기를 읽음 |
| R-09 | C-05 `scraper.py:232-233` | 코드를 읽음 |
| R-10 | C-01 | 실행(T-07) |
| R-11 | C-02 | 실행(T-08) |
| R-12 | C-03, C-05 `scraper.py:248-263` | 판정 함수는 실행(T-09). 재시도 흐름은 코드만 읽음(T-13 미실행) |
| R-13 | C-04 `scraper.py:153-158` | 코드를 읽음 |
| R-14 | C-10 | 코드를 읽음. `cfg`가 거짓이면 `cfg.scraper`에서 `AttributeError`가 나 같은 `except`에 잡힌다(추론) |
| R-15 | C-11 `browser.py:37-84` | 코드를 읽음 |
| R-16 | C-11 `browser.py:86-115`, C-12 `utils.py:101-120`, C-18 | 실행(T-10): `browser.py:86-115`와 `utils.py:101-120`의 원본 줄을 불러와 가짜 `researcher`로 실행 |
| R-17 | C-13 `beautiful_soup.py:58-104` | 코드를 읽음. `requests`의 리다이렉트 추종은 외부 라이브러리 기본값이라 추론 |
| R-18 | C-13 `beautiful_soup.py:32-56`, C-14 | 코드를 읽음 |
| R-19 | C-15 `nodriver_scraper.py:136-172`, `:185-260`; 도메인 대기 `:107-128`; 기본값 `max_browsers=5`, `browser_load_threshold=8`(`:18-19`) | 코드를 읽음. 103자는 소스 문자열의 길이(`:143-146`)를 셈 |
| R-20 | C-16 | 코드를 읽음. `timeout=(5, 30)`은 연결·읽기 각각의 대기 시간이고 총 시간 상한이 아니라는 점은 `requests` 동작에 대한 추론 |
| R-21 | C-12, C-14 | 코드를 읽음. 실행 못 함(bs4 미설치) |
| R-22 | `browser/browser.py:37-70`, `:207-224`; `arxiv/arxiv.py:30-68`; 각 구현체 `return` 줄 grep(`firecrawl.py`, `tavily_extract.py`, `web_base_loader.py`) | 일부만 읽음. firecrawl의 API 키 환경변수는 `firecrawl.py:25-41` 일부만 확인(`FIRECRAWL_API_KEY`) |
| R-23 | `web_scraping.py:54-120`; `grep -rn "filter_urls\|process_scraped_data\|extract_main_content"`(테스트 제외 전체), `grep -rIn "excluded_domains"` | 호출 없음은 grep으로 확인. 테스트 `tests/test_filter_urls_guards.py`, `tests/test_process_scraped_data_guards.py`가 있다는 것만 확인 |
| R-24 | `skills/researcher.py:813-834` `_get_new_urls`, `:932`, `:252`, `:965`, `:1095` | 코드를 읽음. 호출 관계는 경계 설명용 |
| T-01~T-10 | 위 R-ID의 근거 | 아래 "실행 기록"의 두 스크립트 출력 |
| T-11~T-17 | 위 R-ID의 근거 | 코드에서 도출. 미실행 |

**문서와 구현의 차이**
- `docs/docs/gpt-researcher/gptr/config.md:126`은 `SCRAPER`로 newspaper를 쓸 수 있다고 안내하지만 `SCRAPER_CLASSES`(`scraper.py:324-333`)에는 없다. `SCRAPER=newspaper`는 `Scraper not found.`로 모든 URL이 실패한다. 구현을 사실로 썼다.
- `scrape_urls`의 docstring은 `cfg`를 optional이라 하고 `cfg`가 없을 때 쓸 UA 기본값(Chrome 128 Mac)도 갖고 있지만, 바로 아래 `cfg.scraper`를 쓰므로 `cfg`가 없으면 실제로는 동작하지 않는다(`web_scraping.py:27-35`). 설정의 기본 UA는 Chrome 119 Edge 문자열이다(`default.py:21`).
- `get_scraper`의 docstring은 pdf·arxiv 분기만 말하지만 `SCRAPER` 값에 따른 선택이 본문이다. `PyMuPDFScraper.scrape`의 반환 타입 힌트는 `list[str]`이나 실제는 `[]`다.
- `browser/browser.py:68-69`의 주석은 실패를 오류 텍스트가 아니라 빈 내용으로 돌려준다고 의도를 밝히지만, nodriver는 오류 문자열을 내용으로 돌려준다(R-19). 구현을 사실로 썼다.
- 지시문의 `filter_urls`·`process_scraped_data`는 실제 파이프라인에서 쓰이지 않는다(R-23).

**실행 기록**: 아래 스크립트는 `repos/` 안 파일을 고치지 않고 읽기만 한다. 실행 스크립트와 출력은 `artifacts/gpt-researcher/scrapers-demos/`에 있다(2026-10-22 실행, Python 3.12.13).
- `artifacts/gpt-researcher/scrapers-demos/demo_scrapers.py` (출력 `demo_scrapers.out`): `url_security.py`를 파일 경로로 불러와 `validate_url`을 실행하고, `scraper.py:31-106`의 줄을 `exec`해 판정 함수 세 개를 실행했다. 대체물 없음(실제 소스 줄). 검증하지 않은 것: DNS 해석, 요청 전송.
- 같은 폴더 `demo_images.py` (출력 `demo_images.out`): `scraper/utils.py:101-120`(`get_image_hash`)과 `skills/browser.py:86-115`(`select_top_images`)를 `exec`했다. `self.researcher`는 `get_research_images`만 가진 가짜 객체다(형식을 보이려는 예시 입력). bs4가 필요한 함수는 실행하지 못했다.

### 2.2 코드 읽는 순서

1. `skills/browser.py:37-84`(`browse_urls`) → `actions/web_scraping.py:12-51`(`scrape_urls`).
2. `scraper/scraper.py:114-158`(생성자·`run`) → `:194-281`(`extract_data_from_url`) → 판정 상수(`:31-106`) → `:307-352`(`get_scraper`).
3. `utils/url_security.py:60-116`, `utils/workers.py`, `utils/rate_limiter.py`.
4. 구현체: `beautiful_soup/beautiful_soup.py`(대표) → `scraper/utils.py` → `pymupdf/pymupdf.py` → `browser/nodriver_scraper.py`.
5. 이미지: `skills/browser.py:86-115`, `scraper/utils.py:16-120`.

원본의 전략: 구현체는 URL마다 새로 만들고, 상태를 공유하는 것은 `Scraper.session`(요청 헤더)과 풀뿐이다. 판정은 구현체 밖(`Scraper`)에서 한 번에 하므로 구현체를 늘려도 판정 규칙이 같이 적용된다.

### 2.3 비교·재사용 출처

없음.

## 적용 메모

없음.
