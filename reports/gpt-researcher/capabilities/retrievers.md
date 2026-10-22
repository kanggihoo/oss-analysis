---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/actions/retriever.py
  - gpt_researcher/actions/query_processing.py
  - gpt_researcher/agent.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/retrievers/__init__.py
  - gpt_researcher/retrievers/base.py
  - gpt_researcher/retrievers/utils.py
  - gpt_researcher/retrievers/tavily/tavily_search.py
  - gpt_researcher/retrievers/duckduckgo/duckduckgo.py
  - gpt_researcher/retrievers/custom/custom.py
  - gpt_researcher/retrievers/pubmed_central/pubmed_central.py
  - gpt_researcher/retrievers/searx/searx.py
  - gpt_researcher/retrievers/arxiv/arxiv.py
  - gpt_researcher/retrievers/semantic_scholar/semantic_scholar.py
  - gpt_researcher/retrievers/openalex/openalex.py
  - gpt_researcher/retrievers/google/google.py
  - gpt_researcher/retrievers/bing/bing.py
  - gpt_researcher/retrievers/brave/brave.py
  - gpt_researcher/retrievers/serper/serper.py
  - gpt_researcher/retrievers/serpapi/serpapi.py
  - gpt_researcher/retrievers/searchapi/searchapi.py
  - gpt_researcher/retrievers/exa/exa.py
  - gpt_researcher/retrievers/bocha/bocha.py
  - gpt_researcher/retrievers/crw/crw.py
  - gpt_researcher/retrievers/groundroute/groundroute.py
  - gpt_researcher/retrievers/getxapi/getxapi.py
  - gpt_researcher/retrievers/xquik/xquik.py
  - gpt_researcher/retrievers/mcp/__init__.py
  - gpt_researcher/retrievers/mcp/retriever.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/browser.py
  - gpt_researcher/skills/deep_research.py
  - backend/server/server_utils.py
  - pyproject.toml
  - tests/test_research_conductor_retrieval.py
depends: []
status: draft
reimplementation: 미실행
---

# 검색 Retriever 패밀리

> `RETRIEVER` 설정(또는 호출자가 준 `headers`)의 쉼표 구분 이름으로 검색 어댑터 클래스 목록을 고르고, 서브쿼리마다 그 어댑터들을 차례로 불러 얻은 결과를 "스크랩할 URL"과 "이미 본문을 가진 결과"로 나눠 돌려주는 기능이다.

<!--
용어: retriever(어댑터) = 쿼리 문자열을 받아 검색 결과 목록을 돌려주는 클래스. 여기서는 `gpt_researcher/retrievers/<이름>/` 아래 구현과 플러그인이 등록한 클래스를 모두 가리킨다.
prefetched = 어댑터가 본문(`raw_content`)까지 이미 가져와서 스크랩이 필요 없는 결과.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. `GPTResearcher`를 만들 때 한 번 `get_retrievers(headers, cfg)`가 설정 이름을 클래스 목록으로 바꿔 `researcher.retrievers`에 둔다. 헤더가 설정보다 먼저이고, 못 찾은 이름은 조용히 Tavily로 바뀐다(R-01~R-07).
2. 연구가 시작되면 첫 번째 retriever 하나만으로 "계획용 초기 검색"을 한 번 한다. 이 결과는 서브쿼리 계획에 쓰이고, 조건이 맞으면 같은 결과를 본문 확보에도 다시 쓴다(R-14).
3. 서브쿼리마다 `_search_relevant_source_urls`가 retriever를 목록 순서대로 하나씩 만들고(`query`, `query_domains`만 넘김), `search(max_results=…)`를 스레드에서 실행한다(R-08, R-09).
4. 결과 항목마다 URL을 꺼내고, 어댑터의 `requires_scraping` 선언(없으면 `raw_content` 길이 100 초과 여부)으로 "스크랩할 URL"과 "prefetched"로 가른다(R-10, R-11).
5. 스크랩할 URL은 이미 방문한 것을 빼고 무작위로 섞는다. prefetched는 방문 기록과 출처 목록에 올리되 중복 제거는 하지 않는다(R-12).
6. 스크랩할 URL은 스크래퍼에 넘기고, 돌아온 페이지 목록 뒤에 prefetched를 이어 붙여 컨텍스트 선별 쪽에 넘긴다(R-12). 어댑터 하나가 실패해도 나머지는 계속된다(R-13).

### 1.2 범위·통합 지점

- 제공:
  - 이름 → 어댑터 클래스 해석(내장 21개 + 플러그인 entry point)과 설정·헤더에 따른 선택 규칙.
  - 어댑터 공통 계약(생성자, `search()` 반환 형식, `requires_scraping` 선언과 길이 기반 레거시 판정).
  - 호출부(`ResearchConductor`)가 결과를 해석하고 정리하는 규칙과 실패 처리.
  - 어댑터별 필요한 환경변수·패키지·반환 방식·실패 방식 표(1.3).
  - 어댑터 4개(tavily, duckduckgo, custom, pubmed_central)의 구현은 C-ID로 넘긴다.
- 제외:
  - 나머지 어댑터 17개(searx, arxiv, semantic_scholar, openalex, google, bing, brave, serper, serpapi, searchapi, exa, bocha, crw, groundroute, getxapi, xquik, mcp)의 외부 API 요청 형식과 응답 변환. 이 스펙은 공통 계약과 1.3 표까지만 맡고, 각 어댑터 파일은 C-ID로 넘기지 않는다(지시된 패밀리 범위. 재현에 필요하면 미결정 M-01).
  - 스크래핑 본체(`../capabilities/scrapers.md`), MCP 내부 동작(`../capabilities/mcp-client.md`), 서브쿼리 계획·컨텍스트 선별·보고서(`../capabilities/research-pipeline.md` 등), LLM 제공자와 `Config` 로딩.
  - `ResearchConductor._search`(`skills/researcher.py:975`): 레포 소스 어디서도 호출하지 않는 미사용 메서드다(R-17).
- 외부 의존·선행 계약(스펙으로 쓰지 않고 경계만 정의):
  - 스크래퍼. 입력은 URL 문자열 목록이고, 정상 결과는 페이지 딕셔너리 목록이다. 실패 처리와 항목 필드는 `../capabilities/scrapers.md`가 정하며, prefetched가 같은 목록에 붙으므로 항목은 최소한 `url`·`raw_content`를 가질 것이다(추론). 이 기능은 `scraper_manager.browse_urls(urls)`를 부르기만 한다. (코드 확인: `skills/browser.py:37-47`, `researcher.py:965`)
  - MCP 어댑터. 입력은 `query`와 `researcher`이고, 정상 결과는 `title`·`href`·`body` 항목 목록이며 실패하면 빈 목록이다(`mcp-client.md`가 정함). 이 기능은 이름에 `mcpretriever`가 들어간 클래스를 "URL을 주지 않는 어댑터"로 보고 URL 수집 단계에서 건너뛴다(R-15).
  - 설정 객체 `cfg`: `retrievers`(리스트), `max_search_results_per_query`(기본 5, `config/variables/default.py:22`). 키 원문 이름만 쓰고 로딩은 설정 스펙이 맡는다.
  - 호출자: `headers`(사전), `query_domains`(문자열 리스트), `visited_urls`(집합), `add_research_sources()`.
- 소유 상태·부작용:
  - `researcher.retrievers`(클래스 목록)는 `GPTResearcher` 생성 때 한 번 정해진다.
  - 호출부는 `researcher.visited_urls`에 URL을 넣고, prefetched 결과는 `add_research_sources([{"url": …}])`로 출처에 올린다.
  - 어댑터는 외부 서비스에 HTTP 요청을 보낸다. 상태를 저장하지 않는다(인스턴스는 호출마다 새로 만든다).
  - 대부분의 어댑터가 `print`로 진단 문구를 표준 출력에 쓴다(로거를 쓰는 곳도 있음).

### 1.3 인터페이스와 데이터 의미

**공통 계약**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `get_retriever(name)` | string → 클래스 또는 None | 내장 이름이면 해당 클래스, 아니면 플러그인에서 찾고, 없으면 None. 이름 → 클래스 대응은 C-01. |
| `get_retrievers(headers, cfg)` | map, 설정 → 클래스 리스트 | 항상 길이 1 이상의 클래스 리스트를 돌려준다. 순서와 중복은 입력 그대로이고 이름 하나당 클래스 하나다. |
| `get_default_retriever()` | → 클래스 | `TavilySearch`. |
| 설정 키 `RETRIEVER` | string | 쉼표 구분 이름 목록. 기본값 `"tavily"`. 환경변수가 설정 파일 값보다 우선한다(R-05). |
| 헤더 `retrievers` / `retriever` | string | 쉼표 구분 목록 / 이름 하나. 설정보다 우선한다(R-03). 이 레포의 파이프라인은 헤더를 어댑터 생성자에 넘기지 않는다(R-08). |
| entry point 그룹 | `gpt_researcher.retrievers` | 항목 이름이 retriever 이름, 값이 클래스. 설치된 패키지가 등록한다(R-02). |
| 생성자 | `Adapter(query, query_domains=…)` | `query`는 위치 인자, `query_domains`는 키워드 인자(문자열 리스트, 없으면 빈 리스트 또는 None). MCP 어댑터만 `researcher=`를 추가로 받는다(R-08). 어댑터가 `**kwargs`를 받지 않으면 다른 키워드는 TypeError가 된다. |
| `search(max_results=N)` | → 결과 리스트 | `max_results`는 키워드로 전달된다. 항상 list를 돌려줘야 한다(None이면 호출부가 실패, R-14). 블로킹 호출이어도 된다(호출부가 스레드에서 실행). |
| 결과 항목 | map | URL은 `href` 또는 `url`(둘 다 있으면 `href` 우선). 이어서 쓰이는 필드는 URL과 `raw_content`뿐이고 `body`·`title`은 호출부가 버린다(R-10). 계획용 초기 검색 결과만 원본 항목 전체가 계획 단계로 간다(R-14). |
| `requires_scraping` | bool, 선택 | 클래스 속성 또는 property. `True`면 결과는 스크랩할 URL, `False`면 `raw_content`에 본문이 이미 있다. 선언하지 않으면 길이 100 초과 판정으로 내려간다(R-11). `BaseRetriever`를 상속할 필요는 없고 내장 어댑터 중 상속한 것도 없다(R-16). |
| 호출부 반환 | `(urls: list[string], prefetched: list[{url, raw_content}])` | `_search_relevant_source_urls`의 반환값. `urls`는 방문하지 않은 것만, 섞인 순서(R-12). |

**어댑터별 요약** (읽은 범위. 키 이름은 원문. "미선언"은 `requires_scraping`을 정의하지 않았다는 뜻이고 R-11의 레거시 판정을 받는다)

| 이름 | 필요한 환경변수·패키지 | `requires_scraping` | 반환 항목 | `query_domains` | 실패 시 | 검증 |
|---|---|---|---|---|---|---|
| tavily | `TAVILY_API_KEY`(없으면 경고 후 빈 키로 진행, 헤더 `tavily_api_key`도 읽음) | `True` | `{href, body}` | `include_domains`로 전달, `site:` 연산자도 변환 | 모든 예외를 삼키고 `[]` | 코드 확인(C-11) |
| duckduckgo | 패키지 `ddgs`(생성자에서 없으면 ImportError), 키 불필요 | `True` | `{href, body[:100], title?}` | 무시(TODO) | ddgs 예외를 삼키고 `[]` | 코드 확인(C-12) |
| custom | `RETRIEVER_ENDPOINT`(필수, 없으면 생성자가 ValueError), `RETRIEVER_ARG_*`(쿼리 인자로 전달) | `False` | `{url, raw_content}` | 무시 | 요청·JSON 오류와 비리스트 응답은 `[]` | 코드 확인(C-13) |
| pubmed_central | `NCBI_API_KEY`(선택, 없으면 경고), `PUBMED_DB`(기본 `pmc`), `PUBMED_ARG_*` | `False` | `{href, url, body, raw_content, title}` | 무시 | 검색 실패는 `[]`, 기사 하나의 실패는 그 기사만 건너뜀 | 코드 확인(C-14) |
| searx | `SEARX_URL`(필수, 없으면 생성자가 예외) | `True` | `{href, body[:100]}` | 무시(TODO) | `search()`가 요청·JSON 오류를 **예외로 던짐** | 코드 확인 |
| arxiv | 패키지 `arxiv`(모듈 최상단에서 import) | 미선언 | `{title, href(pdf_url, 없으면 entry_id), body(summary)}` | 무시 | 예외를 삼키고 `[]` | 코드 확인 |
| semantic_scholar | 키 없음 | 미선언 | 오픈 액세스 PDF가 있는 논문만 `{title, href(PDF URL), body(abstract)}` | 무시 | `[]` | 코드 확인 |
| openalex | `OPENALEX_EMAIL`, `OPENALEX_API_KEY`(둘 다 선택) | 미선언 | `{title, href(OA PDF → 랜딩 페이지 → id), body}` | 무시 | `[]` | 코드 확인 |
| google | `GOOGLE_API_KEY`, `GOOGLE_CX_KEY`(둘 다 필수, 없으면 생성자 예외. 헤더 `google_api_key`·`google_cx_key`가 우선) | 미선언 | `{title, href, body}`, youtube.com 제외 | `(site:a OR site:b) 쿼리`로 변환 | 응답 파싱 실패는 `[]`, 요청 예외는 **그대로 던짐** | 코드 확인 |
| bing | `BING_API_KEY`(필수) | 미선언 | `{title, href, body}`, youtube.com 제외 | 무시(TODO) | `[]` | 코드 확인 |
| brave | `BRAVE_API_KEY`(필수) | 미선언 | `{title, href, body}` | 무시(TODO) | `[]` | 코드 확인 |
| serper | `SERPER_API_KEY`(필수), 선택 `SERPER_REGION`·`SERPER_LANGUAGE`·`SERPER_TIME_RANGE`·`SERPER_EXCLUDE_SITES`·`SERPER_API_BASE` | 미선언 | `{title, href, body}` | `site:` OR 연결을 쿼리에 덧붙임 | 응답 파싱 실패는 `[]`, 요청 예외는 **그대로 던짐** | 코드 확인 |
| serpapi | `SERPAPI_API_KEY`(필수) | 미선언 | `{title, href, body}`, youtube.com 제외 | `site:` OR 연결을 쿼리에 덧붙임 | `[]` | 코드 확인 |
| searchapi | `SEARCHAPI_API_KEY`(필수) | 미선언 | `{title, href, body}`, youtube.com 제외 | `(site:a OR site:b) 쿼리` | 비200과 예외 모두 경고 후 `[]` | 코드 확인 |
| exa | 패키지 `exa_py`(생성자에서 확인), `EXA_API_KEY`(필수) | 미선언 | `{href, body(text 또는 summary)}` | `include_domains`로 전달 | `[]` | 코드 확인 |
| bocha | `BOCHA_API_KEY`(필수, `os.environ[...]`이라 없으면 KeyError) | 미선언 | `{title, href, body}` | 무시 | `[]` | 코드 확인 |
| crw | `CRW_API_KEY`(없으면 경고, 빈 키), `CRW_API_URL`(기본 `https://fastcrw.com/api`), 헤더 `crw_api_key`·`crw_api_url` | 미선언 | `{href, body(markdown 또는 description)}` | 저장만 하고 사용 안 함 | `[]` | 코드 확인 |
| groundroute | `GROUNDROUTE_API_KEY`(필수, 헤더 `groundroute_api_key`도 읽음) | 미선언 | `{href, body}` | 저장만 하고 사용 안 함 | `[]` | 코드 확인 |
| getxapi | `GETXAPI_API_KEY`(필수) | 미선언 | X 게시물을 `{title, href(x.com 링크), body}`로 | 저장만 하고 사용 안 함 | `[]` | 코드 확인 |
| xquik | `XQUIK_API_KEY`(필수) | 미선언 | getxapi와 같은 모양 | 저장만 하고 사용 안 함 | `[]` | 코드 확인 |
| mcp | `mcp_configs`가 있는 researcher 필요(없으면 `cfg`가 없어 생성자가 ValueError). 패키지 `langchain_mcp_adapters` | (이 기능에서는 판정하지 않음, R-15) | `title`·`href`·`body` 항목 | 사용 안 함 | `search_async`가 예외를 삼키고 `[]` | 생성자·반환 형식만 코드 확인, 나머지는 미확인(`mcp-client.md`) |

내장 어댑터가 하나도 `BaseRetriever`를 상속하지 않고, `requires_scraping`을 선언한 것은 위 표의 `True`·`False` 5개(tavily, duckduckgo, searx, custom, pubmed_central)뿐이다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `get_retriever(name)`에 내장 이름(`google, searx, searchapi, serpapi, serper, duckduckgo, bing, brave, bocha, arxiv, tavily, groundroute, exa, crw, semantic_scholar, pubmed_central, custom, mcp, xquik, openalex, getxapi`)을 줌 | C-01의 대응표대로 클래스를 돌려준다(이름은 대소문자·공백을 구분한다). `docstring`의 지원 목록에는 `bocha`, `groundroute`가 빠져 있지만 `match`에는 있고, 구현이 기준이다. `retrievers/` 디렉터리 이름 21개와 `match` 이름 21개는 같다. | 코드 확인 |
| R-02 | 내장 이름이 아닌 이름 | entry point 그룹 `gpt_researcher.retrievers`에서 그 이름의 항목을 찾아 첫 항목만 `load()`하고 그 결과를 돌려준다. 로드가 예외를 던지면 경고 로그만 남기고 None. 항목이 없으면 None. 내장 이름이 항상 먼저다. | 코드 확인 |
| R-03 | `get_retrievers(headers, cfg)` | 이름 출처를 다음 순서로 고르고 첫 번째 참인 것만 쓴다: ① `headers["retrievers"]`(쉼표 분리) ② `headers["retriever"]`(이름 하나) ③ `cfg.retrievers`(문자열이면 쉼표 분리, 리스트면 그대로) ④ `cfg.retriever`(이름 하나) ⑤ 기본 retriever. `Config`는 항상 길이 1 이상의 `cfg.retrievers`를 만들므로 ④, ⑤는 `Config` 객체에서는 도달하지 않는다. 헤더에 값이 있으면 설정은 읽지 않는다. | 코드 확인 |
| R-04 | 이름 목록 정리 | 각 이름의 앞뒤 공백을 지우고 빈 이름을 버린다. 남은 이름이 없으면 `[TavilySearch]`. 남으면 이름마다 `get_retriever(name)`을 부르고 None이면 **그 이름만** `TavilySearch`로 바꾼다(경고·로그 없음). 순서와 중복을 그대로 둔다(`"tavily,tavily"`는 두 개). | 코드 확인 |
| R-05 | `Config` 초기화 | `RETRIEVER`는 환경변수가 설정 값보다 우선하고 둘 다 없으면 `"tavily"`. 쉼표 분리·공백 제거 후 모든 이름이 `retrievers/` 하위 디렉터리 이름이거나 플러그인 이름이어야 한다. 하나라도 아니면 경고를 `print`하고 목록 **전체**를 `["tavily"]`로 바꾼다(이름 단위 폴백이 아님). 이 검증은 이름만 보고 플러그인을 로드하지 않는다. | 코드 확인 |
| R-06 | MCP와 목록 | `mcp_configs`를 받은 `GPTResearcher`는 `get_retrievers`보다 먼저 `cfg.retrievers`에 `"mcp"`를 덧붙인다(없을 때만). 헤더가 `retrievers`/`retriever`를 주면 ③이 읽히지 않으므로 `"mcp"`는 목록에 없다. `MCPRetriever`는 `langchain_mcp_adapters` import 실패 시 `None`이 되고, 그러면 `get_retriever("mcp")`가 None이라 R-04에 따라 조용히 Tavily가 된다. | 코드 확인 |
| R-07 | 모듈 import | `get_retriever`는 이름마다 `from gpt_researcher.retrievers import <클래스>`를 부르고, 이 패키지 `__init__`은 모든 어댑터 모듈을 한꺼번에 import한다. 그래서 `arxiv` 같은 최상단 import가 실패하면 어떤 이름을 골라도 ImportError가 `get_retrievers`를 통해 `GPTResearcher` 생성까지 전파된다(`get_retrievers`는 잡지 않는다). `ddgs`·`exa_py`는 생성자에서 늦게 확인하므로 그 어댑터를 쓸 때만 실패한다. 실제로 import해 본 것은 아니다. | 코드 확인(정적) |
| R-08 | 서브쿼리 검색의 호출 규약 | 어댑터는 `retriever_class(query, query_domains=query_domains)`로 만든다(`query_domains`는 None이면 `[]`로 바꿔 넘긴다). `headers`는 넘기지 않는다. 그래서 `tavily_api_key`, `google_api_key` 같은 헤더 키는 이 경로에서 읽히지 않고 환경변수만 쓰인다. 계획용 초기 검색도 같은 방식이고 MCP 어댑터에만 `researcher=`가 붙는다. `search`는 `asyncio.to_thread`로 실행된다. | 코드 확인 |
| R-09 | 요청 결과 수 | 서브쿼리 검색과 계획용 초기 검색은 `max_results=cfg.max_search_results_per_query`(기본 5)를 키워드로 넘긴다. Deep Research의 계획 검색(`generate_research_plan`)은 `max_results`를 넘기지 않아 각 어댑터의 기본값이 쓰인다. `custom`은 `max_results`를 쓰지 않는다. | 코드 확인 |
| R-10 | 결과 항목 읽기(서브쿼리 경로) | 항목마다 `url = item.get("href") or item.get("url")`, `raw_content = item.get("raw_content")`만 읽는다. URL이 없으면 그 항목은 버린다. `body`, `title`은 이후 단계로 가지 않는다. 항목에 `.get`이 없으면(딕셔너리가 아님) 예외가 되어 R-13으로 간다. | 코드 확인 |
| R-11 | `requires_scraping` 판정 | 인스턴스에서 `getattr(retriever, "requires_scraping", None)`를 읽는다(property도 지원). `True`: 항목마다 URL을 스크랩 대상에 넣고 `raw_content`는 아무리 길어도 무시한다. `False`: `raw_content`가 참이면 prefetched로, 비어 있으면 URL을 스크랩 대상으로 넣는다. 그 외(None, 미선언, 참/거짓이 아닌 값): `raw_content`가 참이고 길이가 100을 넘으면 prefetched, 아니면 스크랩 대상. 길이 판정은 `raw_content`만 보고 `body` 길이는 보지 않는다. | 코드 확인 |
| R-12 | 결과 정리 | prefetched 항목은 `{url, raw_content}`로 만들고 `add_research_sources([{"url": url}])`와 `visited_urls.add(url)`를 한다. 이미 방문한 URL이어도 걸러내지 않고, prefetched끼리의 중복도 제거하지 않는다. 스크랩 대상 URL은 모든 retriever를 돈 뒤 `_get_new_urls`로 `visited_urls`에 없는 것만 남기고(같은 목록 안의 중복도 첫 번째만) 남긴 것을 `visited_urls`에 넣은 다음 `random.shuffle`한다. 호출 측(`_scrape_data_by_urls`)은 스크랩 결과 목록 뒤에 prefetched를 `extend`하고, 벡터 저장소가 있으면 합친 목록을 저장소에 적재한다. | 코드 확인(순서·중복은 원본 테스트 `tests/test_research_conductor_retrieval.py`도 열람, 실행 안 함) |
| R-13 | 서브쿼리 경로의 실패 | retriever 하나의 생성·검색·결과 순회에서 예외가 나면 오류 로그만 남기고 그 retriever만 건너뛴다. 순회 중 예외가 나면 그 전에 모은 URL과 prefetched는 남는다. `search()`가 빈 값(`[]`·None)이면 그냥 다음 retriever로 간다. 모든 retriever가 실패하면 `([], [])`이고 예외는 전파되지 않는다. retriever는 병렬이 아니라 목록 순서대로 하나씩 실행된다. | 코드 확인 |
| R-14 | 계획용 초기 검색 | `get_search_results`는 `retrievers[0]`만 만들어 검색하고 결과를 가공하지 않고 돌려준다. 생성·검색 예외를 **잡지 않으므로** 키 누락 같은 생성자 예외나 `searx`·`google`·`serper`의 요청 예외는 연구 시작 단계에서 `conduct_research` 밖으로 전파된다. 결과는 로그에서 `len()`을 하므로 `search()`가 None을 주면 TypeError가 난다. 이 결과가 비어 있지 않고 호출자가 `scraped_data`를 주지 않았다면, 같은 결과를 다시 검색하지 않고 `_search_relevant_source_urls(initial_results=…)`로 R-10~R-12와 같은 분류·스크랩을 거쳐 컨텍스트 1개를 더 만든다. 이때도 첫 retriever를 인스턴스화해 `requires_scraping`을 읽고(생성 예외는 R-13처럼 처리되어 그 컨텍스트가 비게 됨), 첫 retriever가 MCP이면 건너뛴다. | 코드 확인 |
| R-15 | MCP 판별 | 클래스 이름을 소문자로 바꿨을 때 `"mcpretriever"`를 포함하면 MCP 어댑터로 본다(내장은 `MCPRetriever`). 서브쿼리 URL 수집(R-13)과 초기 결과 재사용에서 건너뛴다. MCP 결과는 `ResearchConductor`의 별도 MCP 경로가 처리하고 이 스펙은 그 경로를 다루지 않는다. | 코드 확인(건너뛰는 위치만), 내부는 미확인 |
| R-16 | 미선언 어댑터 | `requires_scraping`을 정의하지 않은 내장 어댑터 16개(1.3 표에서 "미선언"인 15개와 mcp)는 R-11의 마지막 분기를 받는다. mcp를 뺀 15개는 읽은 범위에서 이들은 `raw_content` 키를 돌려주지 않으므로 결과가 전부 스크랩 대상이 된다. 서드파티·사용자 정의 retriever도 같다. `BaseRetriever`(`base.py`)는 계약 설명용 선택 베이스이고 `search`가 추상 메서드, `requires_scraping` 기본값이 `True`이지만, 호출부는 상속 여부를 보지 않고 속성만 읽는다. | 코드 확인 |
| R-17 | `ResearchConductor._search` | `skills/researcher.py:975`의 `_search(retriever, query)`는 레포 소스에 호출부가 없다. 호출하면 `headers`, `websocket`, `researcher` 키워드를 모든 어댑터에 넘기므로 `**kwargs`를 받지 않는 어댑터는 TypeError를 내고 메서드는 `[]`를 돌려준다. | 코드 확인(호출부 없음은 `gpt_researcher`·`backend`·`multi_agents` 검색 결과, 동작은 정적 읽기) |
| R-18 | 어댑터의 공통 실패 관례 | 생성자는 필수 키·URL이 없으면 예외를 던진다(google, bing, brave, serper, serpapi, searchapi, exa, groundroute, getxapi, xquik, searx, custom, bocha, mcp). tavily·crw는 키가 없어도 경고만 하고 계속하며, 뒤이은 요청이 실패하면 `[]`가 된다. `search()`는 대부분 예외를 삼키고 `[]`를 돌려주지만 searx(요청·JSON 오류)와 google·serper(요청 예외)는 그대로 던진다. 이 차이가 R-13(경로 안에서는 건너뜀)과 R-14(전파)에서 다르게 보인다. | 코드 확인(표의 어댑터별 읽은 범위) |
| R-19 | tavily 상세 | C-11이 규칙이다. 요약: 검색 쿼리에서 `site:도메인`을 뽑아 `include_domains`로 옮기고 400자로 자르며 `search_depth="basic"`, `include_raw_content=False`로 요청한다. 결과는 `url`·`content`를 `href`·`body`로 바꾸고 `url`이 없는 항목은 버린다. 응답이 dict가 아니거나 결과가 비면 내부에서 예외를 만들었다가 잡아서 `[]`로 끝난다. | 코드 확인 |
| R-20 | duckduckgo·custom·pubmed_central 상세 | duckduckgo는 ddgs 결과의 키 이름 차이(`href`/`link`/`url`, `body`/`snippet`/`description`)를 정규화하고 `body`를 100자로 자른다(C-12). custom은 `GET RETRIEVER_ENDPOINT`에 `RETRIEVER_ARG_*`와 `query`를 붙여 JSON 리스트를 받아 `{url, raw_content}`로 정리하고 `raw_content`가 없으면 `body`로 대신한다(C-13). pubmed_central은 esearch로 ID를 얻고 efetch로 기사마다 XML을 받아 본문을 만든다(C-14). | 코드 확인 |

- 불변식:
  - `get_retrievers`는 항상 비어 있지 않은 클래스 리스트를 돌려준다(R-03, R-04).
  - 서브쿼리 경로의 반환 `urls`는 `visited_urls`에 없던 URL뿐이고 호출 뒤에는 전부 `visited_urls`에 들어 있다(R-12). prefetched URL도 호출 뒤 `visited_urls`에 들어 있다.
  - `requires_scraping is True`인 어댑터의 URL은 `raw_content` 길이와 관계없이 스크랩 대상이다(R-11).
- 미결정:
  - M-01 (1.2 제외 범위): 어댑터 17개(searx, arxiv, semantic_scholar, openalex, google, bing, brave, serper, serpapi, searchapi, exa, bocha, crw, groundroute, getxapi, xquik, mcp)의 요청·응답 변환 코드는 이 스펙이 C-ID로 넘기지 않는다. 이 스펙만으로 그 어댑터를 같은 요청 형식으로 재현할 수는 없다. 어댑터를 어디까지 재현할지는 호출자가 정해야 하고, 필요한 어댑터는 C-ID를 추가하거나 별도 스펙을 쓴다. 영향: 1.3 표의 키 이름·반환 모양·실패 방식까지는 이 스펙으로 구현할 수 있다.
- 확인 한계:
  - 실행하지 않았다. 모든 규칙은 정적으로 읽은 결과이고 외부 서비스(Tavily, ddgs, NCBI 등)의 실제 응답은 확인하지 못했다. 어댑터가 가정하는 응답 필드는 "클라이언트가 그렇게 가정했다"는 증거일 뿐이다.
  - 플러그인 entry point는 이 레포의 `pyproject.toml`·`setup.py`가 등록하지 않는다(`entry-points`·`entry_points` 검색 결과 없음). 외부 패키지가 실제로 등록한 사례와 로드 시 클래스가 만족해야 할 계약 외의 제약은 확인하지 못했다.
  - 서버·프런트엔드가 `headers`에 `retrievers`/`retriever`를 어떻게 채우는지는 보지 않았다. 서버는 웹소켓 JSON의 `headers` 필드를 그대로 `GPTResearcher`에 넘기고(`backend/server/server_utils.py:417`), 프런트엔드 소스에서 `retrievers`를 쓰는 곳은 찾지 못했다.

### 1.5 필수 코드 참조

라이선스: overview 1절에 따라 LICENSE는 Apache License 2.0이고 `pyproject.toml`은 MIT로 표기해 어긋난다. 인용 허용 여부를 이 분석에서 판단하지 않았으므로 C-ID는 위치만 가리키고 원문을 옮기지 않았다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/actions/retriever.py:49-136` `get_retriever` | 이름 → 클래스 대응표(`match`). 모든 분기가 `gpt_researcher.retrievers`에서 클래스를 import한다. `case _`가 플러그인으로 넘어간다. | R-01, R-07 |
| C-02 | `gpt_researcher/actions/retriever.py:13`, `:139-147` `RETRIEVER_ENTRY_POINT_GROUP`, `_load_plugin_retriever` | entry point 그룹 이름과 로드 규칙(첫 항목만, 실패하면 경고 후 None). | R-02 |
| C-03 | `gpt_researcher/actions/retriever.py:150-204` `get_retrievers`, `get_default_retriever` | 헤더·설정 우선순위, 공백 정리, 이름 단위 Tavily 폴백. | R-03, R-04 |
| C-04 | `gpt_researcher/config/config.py:69-75`, `:184-197` `parse_retrievers` | `RETRIEVER` 환경변수 우선, 이름 검증, 하나라도 무효면 전체 `["tavily"]`. 기본값은 `config/variables/default.py:4`. | R-05 |
| C-05 | `gpt_researcher/retrievers/utils.py:62-120` `VALID_RETRIEVERS`, `get_all_retriever_names`, `get_plugin_retriever_names` | 유효한 이름 = `retrievers/` 하위 디렉터리 이름 + 플러그인 이름. `VALID_RETRIEVERS`(끝에 `mock` 포함)는 디렉터리 읽기가 실패할 때만 쓰인다. | R-05 |
| C-06 | `gpt_researcher/retrievers/base.py:35-61` `BaseRetriever` | `requires_scraping: bool = True` 기본값과 `search(max_results)` 추상 선언, 계약 설명. 파일 위쪽 독스트링(1-30행)이 길이 판정이 생긴 배경을 설명한다. | R-11, R-16 |
| C-07 | `gpt_researcher/skills/researcher.py:851-934` `_search_relevant_source_urls` | 서브쿼리 경로의 인스턴스화, 검색, 항목 분류(R-10, R-11), 실패 처리, 정리. | R-08~R-13, R-15 |
| C-08 | `gpt_researcher/skills/researcher.py:813-834` `_get_new_urls` | `visited_urls`에 없는 URL만 남기고 그 자리에서 `visited_urls`에 추가(verbose일 때만 로그 스트림). | R-12 |
| C-09 | `gpt_researcher/skills/researcher.py:936-973` `_scrape_data_by_urls` | URL 스크랩 결과 뒤에 prefetched를 이어 붙이고 벡터 저장소에 적재. | R-12 |
| C-10 | `gpt_researcher/actions/query_processing.py:44-81` `get_search_results`, `gpt_researcher/skills/researcher.py:50-65` `_get_initial_search_results`, `:384-392` | 계획용 초기 검색의 생성자 인자, `max_results` 조건부 전달, 예외 비전파, 초기 결과 재사용 조건. | R-08, R-09, R-14 |
| C-11 | `gpt_researcher/retrievers/tavily/tavily_search.py:14-15`, `:18-62`, `:108-156` `TavilySearch` | 기본 retriever의 키 조회, `site:` 변환, 쿼리 400자 제한, 결과 정규화와 실패 처리. 요청 본문은 `:83-100`. | R-19 |
| C-12 | `gpt_researcher/retrievers/duckduckgo/duckduckgo.py:19-82` `Duckduckgo` | ddgs 필드 정규화, `body` 100자 절단, `max_results` 상한 보장. | R-20 |
| C-13 | `gpt_researcher/retrievers/custom/custom.py:6-92` `CustomRetriever` | 엔드포인트 환경변수, `RETRIEVER_ARG_*` 수집, 응답 정리, `requires_scraping = False`. | R-20 |
| C-14 | `gpt_researcher/retrievers/pubmed_central/pubmed_central.py:14-44`, `:46-141`, `:143-171` `PubMedCentralSearch` | 환경변수와 기본값, esearch 실패(None → 빈 목록)와 efetch 기사별 실패 처리, XML에서 제목·초록·본문을 뽑는 방법, URL 만드는 규칙, `requires_scraping = False`. | R-20 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 R-12의 일부만 열람, 실행하지 않음). 검색 서버·API 키 없이 확인할 수 있게 가짜 어댑터 클래스와 가짜 `cfg`를 쓴다고 가정한 사례이며, 대체물로 검증하지 않는 것은 외부 서비스의 실제 응답이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-04, R-05 | `RETRIEVER` 환경변수 없음, 헤더 `{}` | `get_retrievers` 결과는 `[TavilySearch]`. |
| T-02 | R-03, R-04 | 헤더 `{"retrievers": "tavily, exa"}`, `cfg.retrievers=["duckduckgo"]` | `[TavilySearch, ExaSearch]`. 설정은 쓰이지 않고 공백은 제거된다. |
| T-03 | R-04 | 헤더 `{"retriever": "nope"}` | `[TavilySearch]`, 경고 없음. 이름이 `"tavily,nope"`이면 `[TavilySearch, TavilySearch]`. |
| T-04 | R-05 | 환경변수 `RETRIEVER="duckduckgo,nope"`로 `Config`를 만듦 | 경고가 출력되고 `cfg.retrievers == ["tavily"]`(duckduckgo도 사라진다). |
| T-05 | R-02 | entry point `gpt_researcher.retrievers`에 `myeng`이 등록됨 / 같은 이름이 `tavily`로 등록됨 | `get_retriever("myeng")`은 그 클래스, `get_retriever("tavily")`는 내장 `TavilySearch`. |
| T-06 | R-02, R-04 | 등록된 플러그인 `load()`가 예외를 던짐 | `get_retriever`가 None을 돌려주고 경고 로그 1건, `get_retrievers`는 그 이름을 `TavilySearch`로 바꾼다. |
| T-07 | R-11 | 어댑터 `requires_scraping=True`가 `{"href": u, "raw_content": "x"*500}`을 돌려줌 | `urls == [u]`, `prefetched == []`. |
| T-08 | R-11, R-12 | `requires_scraping=False`, 결과 `{"url": u, "raw_content": "x"*500}` 한 건, `visited_urls`는 빈 집합 | `urls == []`, `prefetched == [{"url": u, "raw_content": …}]`, `visited_urls == {u}`, 출처에 `{"url": u}`가 추가된다. 같은 어댑터로 두 번째 서브쿼리를 불러도 prefetched에 u가 다시 들어간다. |
| T-09 | R-11 | `requires_scraping=False`인 어댑터가 `raw_content`가 빈 문자열인 항목을 돌려줌 | 그 URL은 스크랩 대상. |
| T-10 | R-11 | 선언 없는 어댑터: `raw_content` 길이 101 / 100 / 키 없음(`body` 300자) 세 항목 | 101자만 prefetched이고 나머지 둘은 스크랩 대상. |
| T-11 | R-10 | 항목 `{"url": a, "href": b}` / `{"title": "t"}` | 첫 항목은 `b`를 쓰고, `url`도 `href`도 없는 항목은 버려진다. |
| T-12 | R-12 | retriever 두 개가 같은 URL을 `requires_scraping=True`로 돌려줌 | `urls`에 한 번만 나오고 `visited_urls`에 들어간다. 같은 URL이 다음 서브쿼리에서 다시 나오면 `urls`에서 빠진다. |
| T-13 | R-13 | 첫 retriever의 `search`가 예외, 둘째는 정상 | 오류 로그 1건, 둘째의 결과가 반환되고 예외는 전파되지 않는다. 두 retriever 모두 실패하면 `([], [])`. |
| T-14 | R-13 | retriever 생성자가 필수 키 누락으로 예외 | 서브쿼리 경로에서는 로그 후 건너뜀. |
| T-15 | R-14 | `retrievers[0]`의 생성자가 키 누락으로 예외, 연구 시작 | 계획용 초기 검색에서 예외가 전파되어 서브쿼리 단계에 들어가지 못한다. |
| T-16 | R-14, R-15 | `retrievers=[MCPRetriever, TavilySearch]` | 초기 결과를 재사용하는 단계는 MCP이면 빈 컨텍스트, 서브쿼리 URL 수집은 MCP를 건너뛰고 Tavily만 실행한다. |
| T-17 | R-09 | `max_search_results_per_query=5`로 서브쿼리 경로 호출 | 어댑터의 `search`가 `max_results=5` 키워드로 불린다. |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, `actions/retriever.py:25-44`(독스트링 목록), `retrievers/__init__.py:1-21`, `retrievers/` 디렉터리 목록 | `match` 분기 수와 디렉터리 수가 21개로 같은지 직접 세었다. 문서와 구현의 차이: ① 독스트링 지원 목록에 `bocha`, `groundroute`가 없다(구현에는 있음). ② `utils.py:62-84`의 `VALID_RETRIEVERS`에는 `mock`이 있지만 `match`에 없고 플러그인으로 찾지 못하면 Tavily가 된다. |
| R-02 | C-02, `retrievers/utils.py:110-120` | 정적 읽기. entry point 등록 패키지는 레포 안에서 확인하지 못했다. |
| R-03 | C-03(`:161-179`) | `cfg.retriever` 분기가 도달 불가인 근거는 `config.py:69-75`에서 `cfg.retrievers`를 항상 비어 있지 않은 리스트로 만든다는 점이다. 같은 조건을 만족하지 않는 사용자 정의 `cfg`는 가정하지 않았다. |
| R-04 | C-03(`:181-193`) | `get_default_retriever().__name__`(`"TavilySearch"`)을 이름으로 쓰는 ⑤ 분기는 R-03에서 도달 불가이므로 따로 정하지 않았다. 참고로 그 이름은 `match`에 없어 결국 `or get_default_retriever()`로 Tavily가 된다. |
| R-05 | C-04, C-05 | 정적 읽기. `print`로 경고하므로 로그 시스템에는 남지 않는다. |
| R-06 | `agent.py:172-176`, `:296-320` `_process_mcp_configs`, `retrievers/mcp/__init__.py:11-32`, `retrievers/__init__.py:18` | 헤더가 우선이라 `"mcp"`가 안 붙는 경우는 R-03과 `_process_mcp_configs`가 `cfg.retrievers`만 바꾼다는 점의 조합에서 따진 것이다. |
| R-07 | C-01, `retrievers/__init__.py`, `retrievers/arxiv/arxiv.py:1`, `duckduckgo.py:30-33`, `exa/exa.py:10-17`, `pyproject.toml`의 의존성 | 실제 import를 실행하지 않았다. 문서와 구현의 차이: `pyproject.toml`에는 `arxiv`와 `duckduckgo-search`는 있으나 `ddgs`는 없고(`requirements.txt`에는 `ddgs`가 있음) `duckduckgo` 어댑터는 `ddgs`를 요구한다. `pyproject`만으로 설치하면 duckduckgo 생성자가 ImportError를 낼 수 있다는 점은 정적으로만 판단했다. |
| R-08 | C-07 `:869`, `:873-875`, C-10, `retrievers/tavily/tavily_search.py:27-45`(`headers`를 받지만 호출부가 안 줌) | 호출부 어디서도 `headers=`를 어댑터 생성자에 넘기지 않음을 `researcher.py:869`, `query_processing.py:62-72`로 확인. `tavily_api_key` 헤더 지원은 문서화된 경로 밖에서 어댑터를 직접 만들 때만 의미가 있다(추론). |
| R-09 | C-10, `config/variables/default.py:22`, `skills/deep_research.py:297-310` | `Config`가 `max_search_results_per_query`를 환경변수 `MAX_SEARCH_RESULTS_PER_QUERY`로 덮을 수 있는 규칙은 설정 스펙 범위로 확인하지 않았다. |
| R-10 | C-07 `:890-895` | 정적 읽기. |
| R-11 | C-07 `:887`, `:897-926`, C-06, `tests/test_research_conductor_retrieval.py`의 사례명 | 문서와 구현의 차이: `duckduckgo.py:4-19`, `searx.py:4-19`의 주석은 "`raw_content`/`body`가 100자를 넘으면 prefetched로 본다"고 설명하지만 구현(`researcher.py:916`)은 `raw_content`만 본다. 두 어댑터는 이제 `requires_scraping=True`를 선언하므로 100자 절단은 분류에는 영향이 없고 계획용 초기 검색 결과의 `body`만 짧아지게 한다(추론: 계획 프롬프트에 어떻게 쓰이는지는 `plan_research_outline`을 읽지 않아 미확인). `base.py:15`의 `if url and raw_content and len(raw_content) > 100:` 형태도 실제 코드와 조금 다르다(실제는 `url` 검사가 앞 단계에 있고 `elif raw_content and len(raw_content) > 100`). |
| R-12 | C-07 `:897-934`, C-08, C-09, `tests/test_research_conductor_retrieval.py:84-130` | 테스트의 "두 번째 서브쿼리에도 prefetched가 1건 나온다"는 읽기(실행 안 함)가 코드 읽기와 일치한다. `browse_urls`는 스크랩 결과를 출처에 올리고(`skills/browser.py:57`) prefetched는 호출부가 올린다. |
| R-13 | C-07 `:861-880`, `:927-928` | 정적 읽기. 반환 후 호출부에서 `random.shuffle`되므로 URL 순서는 의미가 없다. |
| R-14 | C-10, `skills/researcher.py:365-366`, `:384-392`, `:836-848` `_get_context_from_initial_results` | `_get_initial_search_results`가 `try` 블록 밖에 있음(`:365`는 `:384`의 `try`보다 앞)과 `agent.py:343-406`에 예외 처리가 없음을 확인했다. 이 예외를 서버 쪽이 어떻게 처리하는지는 범위 밖이다. |
| R-15 | C-07 `:864-865`, `:836-839` | `mcpretriever` 문자열 비교는 `skills/researcher.py` 곳곳에 반복된다(`:140`, `:312`, `:538`, `:838`, `:864`). 이 스펙은 이 파일의 URL 수집 경로만 다뤘다. |
| R-16 | `grep`으로 `requires_scraping` 정의 위치 확인: tavily, duckduckgo, searx(`True`), custom, pubmed_central(`False`) 5곳. `BaseRetriever` 상속은 없음(`context/retriever.py`의 `BaseRetriever`는 LangChain 클래스로 무관) | 1.3 표의 어댑터 읽기에서 `raw_content`를 돌려주는 것은 custom과 pubmed_central뿐임을 확인했다. mcp는 반환 형식만 봤다. |
| R-17 | `skills/researcher.py:975-1055`, `grep` 결과(`gpt_researcher`, `backend`, `multi_agents` 어디에도 `._search(`로 conductor를 부르는 곳 없음) | 호출하면 TypeError가 난다는 판단은 어댑터 생성자 시그니처를 읽은 결과(getxapi·xquik·mcp는 `**kwargs`를 받아 예외가 안 남)이고 실행하지 않았다. 사용자 지시문은 `_search`를 호출부로 지목했지만 실제 경로는 R-08~R-14의 두 함수다. |
| R-18 | 1.3 표의 파일들. 생성자 예외: google `:26-52`, bing `:253-264`, brave `:289-301`, serper `:45-56`, exa `:167-182`, bocha `:23` 등 | 어댑터마다 읽은 범위는 `search()` 전체와 생성자다. 외부 서비스 응답이 실제로 어떤 형태인지는 미확인. |
| R-19 | C-11 | 정적 읽기. |
| R-20 | C-12, C-13, C-14 | 정적 읽기. pubmed의 `PUBMED_DB=pubmed`일 때 검색어에 `AND (ffrft[filter] OR pmc[filter])`가 붙고 efetch는 항상 `db=pmc`를 쓴다는 점도 C-14 범위다. |
| T-01~T-17 | 해당 R-ID의 근거 | 모두 구현에서 도출했고 실행하지 않았다. 대체물로 쓴 가짜 어댑터·`cfg`가 검증하지 않는 것: 실제 HTTP 응답, 실제 스크래퍼, 실제 entry point 설치. |

### 2.2 코드 읽는 순서

1. `actions/retriever.py`(이름 해석과 선택)에서 `Config`의 `parse_retrievers`(`config.py:184`)로 간다.
2. `skills/researcher.py:50-65`(초기 검색) → `:851-934`(분류) → `:936-973`(스크랩과 합치기) 순서로 읽는다.
3. `retrievers/base.py` 독스트링으로 `requires_scraping`이 생긴 이유를 읽고, tavily(URL만 주는 대표) → custom(본문을 주는 대표) → pubmed_central 순으로 어댑터를 읽는다.

원본의 구현 전략: 어댑터는 호출마다 새로 만들고 재사용하지 않는다. 블로킹 HTTP 호출은 `asyncio.to_thread`로 밀어 이벤트 루프를 막지 않는다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

## 적용 메모

없음.
