---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/agent.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/browser.py
  - gpt_researcher/skills/curator.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/retrievers/mcp/retriever.py
  - gpt_researcher/actions/query_processing.py
  - gpt_researcher/actions/agent_creator.py
  - gpt_researcher/actions/web_scraping.py
  - gpt_researcher/actions/retriever.py
  - gpt_researcher/actions/utils.py
  - gpt_researcher/prompts.py
  - gpt_researcher/context/select.py
  - gpt_researcher/scraper/scraper.py
  - gpt_researcher/retrievers/base.py
  - gpt_researcher/retrievers/tavily/tavily_search.py
  - gpt_researcher/utils/llm.py
  - gpt_researcher/utils/enum.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/skills/deep_research.py
  - backend/report_type/detailed_report/detailed_report.py
depends: []
status: ready
reimplementation: 미실행
---

# 연구 파이프라인

> 질문(query) 하나를 받아 에이전트 역할을 고르고, 서브쿼리를 계획해 웹 검색·스크랩·컨텍스트 선별을 서브쿼리마다 병렬로 돌린 뒤, 모은 컨텍스트 문자열을 반환한다(보고서 작성은 하지 않는다).

<!-- 이 스펙의 근거는 모두 기준 SHA 소스를 읽어 확인한 것이다. 실행하지 않았으므로 "실행 확인"은 없다. 용어: 서브쿼리 = 원 질문을 쪼개 검색에 쓰는 질문, 컨텍스트 = 선별을 거쳐 보고서 작성에 넘기는 문자열, retriever = 검색 엔진 어댑터 클래스, 스크랩 = URL의 페이지 본문을 가져오는 일. -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`GPTResearcher(query=..., report_source="web")`를 만들고 `await conduct_research()`를 부르는 경우다.

1. `report_type`이 `"deep"`이면 이 파이프라인을 쓰지 않고 Deep Research에 맡긴다(경계만 정의).
2. `agent`와 `role`이 비어 있으면 LLM에게 질문 분야에 맞는 에이전트 이름과 역할 지시문을 고르게 한다. 실패하면 기본 에이전트를 쓴다.
3. 설정된 retriever 중 첫 번째로 원 질문을 한 번 검색한다(초기 결과).
4. 초기 결과를 참고 자료로 LLM에게 서브쿼리 목록을 만들게 하고, 목록 끝에 원 질문을 덧붙인다(`subtopic_report`는 덧붙이지 않는다).
5. 초기 결과의 페이지를 먼저 스크랩하고 원 질문으로 선별한다(초기 컨텍스트). 이 단계가 끝나야 6번이 시작된다.
6. 서브쿼리마다 동시에 다음을 한다: 모든 retriever로 검색 → 이미 본 URL을 `visited_urls`로 거르기 → 스크랩 → 서브쿼리로 컨텍스트 선별. 한 서브쿼리가 실패해도 빈 문자열이 되고 나머지는 계속된다.
7. 초기 컨텍스트와 서브쿼리 결과 중 비어 있지 않은 것을 공백 한 칸으로 이어 붙여 `context`로 삼는다. 하나도 없으면 빈 리스트를 돌려준다. `CURATE_SOURCES`가 켜져 있으면 출처 curation을 한 번 더 거친다.

### 1.2 범위·통합 지점

- 제공: 웹 검색 경로(`source_urls`가 비어 있고 `report_source == "web"`)에서 질문 → 컨텍스트 문자열까지. 에이전트 역할 선택, 서브쿼리 계획, 서브쿼리별 병렬 처리, `visited_urls` 중복 제거, 결과 합치기, 실패 시 빈 결과 반환.
- 제외:
  - 소스 모드의 분기 규칙(`local`, `hybrid`, `azure`, `langchain_documents`, `source_urls` 경로 등)은 [source-modes.md](../capabilities/source-modes.md)가 맡는다. 갈라지는 곳은 `skills/researcher.py:144-209`(R-08)이다.
  - 자체 벡터스토어 경로(`langchain_vectorstore`, `vector_store` 인자)는 사용자 제외다.
  - 검색 엔진별 동작, 스크래퍼별 동작, 컨텍스트 선별 알고리즘, MCP, Deep Research, 보고서 작성은 다른 스펙의 몫이고 아래 경계 표로만 다룬다.
  - LLM 제공자·설정(`Config`)·임베딩·비용 계산은 사용자 제외다. 설정 키는 원문 이름만 쓴다.
  - 이미지 생성은 `conduct_research` 끝에서 이 컨텍스트를 읽기만 하는 후속 단계라 제외한다(R-27).
  - 로그 파일과 JSON 로그 핸들러(`json_handler`)는 관찰용이고 결과에 영향이 없어 제외한다.
- 외부 의존과 경계:

  | 대상 | 이 스펙이 주는 입력 | 정상 결과 | 실패 시 이 스펙이 보는 것 | 상세 |
  |---|---|---|---|---|
  | retriever(검색) | 생성 `cls(query, query_domains=list)`, 호출 `.search(max_results=int)` | `list[dict]`, 각 항목은 `href` 또는 `url`을 가짐 | 서브쿼리 경로에서는 그 retriever만 건너뜀, 초기 검색에서는 예외가 밖으로 나감(R-09, R-18) | [retrievers.md](../capabilities/retrievers.md) |
  | 스크래퍼 | `BrowserManager.browse_urls(list[str])` | 본문을 얻은 페이지만 `list[dict]` | URL별 실패는 결과에서 빠지고, 스크랩 전체 예외도 빈 리스트(R-22) | [scrapers.md](../capabilities/scrapers.md) |
  | 컨텍스트 선별 | `select_context(query, pages, cfg, max_results=10, ...)` | `str` | 선별 모드 실패는 내부에서 keyword로 낮춤. 그래도 예외면 그 서브쿼리가 빈 문자열(R-24) | [context-selection.md](../capabilities/context-selection.md) |
  | LLM 호출 | `create_chat_completion(messages, model, llm_provider, ...)` | `str` | 한 호출이 최대 10회 시도한 뒤 `RuntimeError`. 시도 사이에 1, 2, 4, 8, 8, ...초(최대 8초) 대기 | 범위 밖 |
  | MCP | retriever 이름에 `mcpretriever`(소문자 비교)가 들어간 클래스 | MCP 결과를 서브쿼리 컨텍스트에 덧붙임 | MCP 오류는 건너뛰고 계속 | [mcp-client.md](../capabilities/mcp-client.md) |
  | Deep Research | `report_type == "deep"` | 쿼리 트리 조사 결과 컨텍스트 | 이 스펙은 다루지 않음(R-01) | [deep-research.md](../capabilities/deep-research.md) |
  | SourceCurator | `research_data`(연구 결과 문자열 또는 `[]`) | `list[dict]`(`Title`, `Content`, `Source`) | 실패하면 입력을 그대로 돌려줌(R-26) | 별도 스펙 없음 |

  이 스펙의 R-ID는 MCP retriever가 설정되지 않았다고 가정한다. MCP가 설정되면 달라지는 곳은 R-09(초기 검색이 MCP일 수 있음), R-10(MCP만 있으면 LLM 없이 `[query]`), R-16(초기 컨텍스트 생략), R-18(MCP 건너뜀), R-24(MCP 컨텍스트를 합침) 다섯 곳이고, 그 앞에 하나가 더 있다. 서브쿼리 계획과 초기 검색보다 먼저 도는 MCP 사전 실행(`skills/researcher.py:311-362`)이다. 이 단계와 위 다섯 곳의 자세한 규칙은 [mcp-client 스펙](mcp-client.md)(R-06 등)이 맡는다.
- 소유 상태·부작용(모두 `GPTResearcher` 인스턴스의 필드):
  - `agent`, `role`: 선택 결과로 덮어쓴다.
  - `context`: 호출마다 이 파이프라인의 결과로 덮어쓴다.
  - `visited_urls`(set): 스크랩하려고 고른 URL과 본문을 이미 받은 URL이 쌓인다. 호출을 거쳐도 비우지 않는다(R-07).
  - `research_sources`, `research_images`: 스크랩 단계가 쌓는다(스크래퍼 스펙의 영역).
  - `research_costs`, `step_costs`: LLM 호출 비용이 쌓인다(R-29).
  - 외부 자원: retriever의 검색 API, 대상 웹 사이트, LLM API.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GPTResearcher(...)` 생성자(관련 인자만) | `query: string`, `report_type: string = "research_report"`, `report_source: string = "web"`, `query_domains: list[string]`, `agent: string?`, `role: string?`, `parent_query: string = ""`, `visited_urls: set?`, `context: any?`, `headers: dict`, `verbose: bool = True`, `websocket: object?`, `**kwargs` | `report_source`가 빈 값이면 `cfg.report_source`(기본 `"web"`)를 쓴다. `visited_urls`가 `None`이 아니면 복사하지 않고 같은 객체를 쓴다. `kwargs`는 `choose_agent`와 서브쿼리 생성의 LLM 호출에 그대로 전달된다(`encoding` 키는 제거됨). 나머지 인자(`source_urls`, `documents`, `mcp_configs` 등)는 소스 모드·MCP 스펙의 것이다. |
| `conduct_research(on_progress=None)` | → `str` 또는 빈 `list` | 컨텍스트를 반환하고 `self.context`에도 저장한다. 비어 있으면 `[]`이며 `""`가 아니다(R-25). `on_progress`는 Deep Research만 쓴다. 비동기이고 취소·중간 결과 반환은 없다. |
| `choose_agent(query, cfg, parent_query, cost_callback, headers, prompt_family, **kwargs)` | → `(agent: string, role: string)` | 항상 두 문자열을 돌려주고 예외를 밖으로 내지 않는다. `headers`는 받지만 쓰지 않는다. |
| 서브쿼리 계획 `plan_research_outline(...)` | → `list[string]` | 길이 상한은 코드가 두지 않는다(R-14). 원소는 공백 제거된 비어 있지 않은 문자열이다. |
| 검색 결과 항목 | `dict`: `href` 또는 `url`(`href` 우선), 선택 `body`, 선택 `raw_content` | URL이 없는 항목은 무시한다. |
| 페이지 dict(스크랩 결과) | `{url, raw_content: string, image_urls: list, title: string}` | `raw_content`가 `None`이면 스크래퍼가 이미 제거해서 이 단계에는 오지 않는다. |
| 페이지 dict(prefetched) | `{url, raw_content: string}` | retriever가 본문까지 준 경우. `title`이 없다. |
| 서브쿼리 결과 | `string` | 선별 결과(MCP 없음)를 `.strip()`한 값. 비어 있으면 `""`. |

설정 키(환경변수가 같은 이름의 설정값을 덮어쓴다: `config/config.py:63-67`). 모두 원문 이름이다.

| 키 | 기본값 | 이 스펙에서의 쓰임 |
|---|---|---|
| `RETRIEVER` | `"tavily"` | 쉼표로 구분한 retriever 목록. 첫 번째가 초기 검색에 쓰인다. 파싱·검증·폴백은 retrievers 스펙 |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `5` | 모든 `search(max_results=...)` 호출에 전달 |
| `MAX_ITERATIONS` | `3` | 서브쿼리 프롬프트가 요청하는 개수(`0`이나 `None`이면 `3`) |
| `SMART_LLM` | `"openai:gpt-5.4"` | 에이전트 선택, 서브쿼리 생성의 마지막 폴백 |
| `STRATEGIC_LLM` | `"openai:gpt-5.4"` | 서브쿼리 생성의 1차·2차 시도 |
| `STRATEGIC_TOKEN_LIMIT` / `SMART_TOKEN_LIMIT` | `8000` / `12000` | 서브쿼리 생성 폴백의 `max_tokens` |
| `TEMPERATURE` | `0.4` | 서브쿼리 생성의 마지막 폴백에서만 사용 |
| `CURATE_SOURCES` | `False` | 켜면 R-26의 curation 수행 |
| `MAX_SCRAPER_WORKERS` | `15` | 스크랩 동시성(`WorkerPool`). 스크래퍼 스펙의 영역 |

진행 이벤트(R-28)는 대부분 `verbose=True`일 때만 나가고(예외는 R-28에 적음), `websocket`이 있으면 `{"type": "logs", "content": <이름>, "output": <문자열 또는 값>, "metadata": <값 또는 null>}` 형태로 `send_json`된다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `report_type == "deep"`이고 `deep_researcher`가 있음(생성자가 `report_type`이 `"deep"`일 때만 만듦) | 에이전트 선택과 아래 웹 파이프라인을 건너뛰고 Deep Research 스킬의 결과를 `self.context`에 넣어 반환한다. 이후의 모든 규칙은 `deep`이 아닌 경우다. | 코드 확인 |
| R-02 | `conduct_research` 호출 시 `agent`와 `role`이 둘 다 truthy | `choose_agent`를 부르지 않고 값을 유지한다. 하나라도 비면(None 또는 빈 문자열) 호출해 둘 다 결과로 덮어쓴다. | 코드 확인 (C-16) |
| R-03 | `choose_agent` 호출 | SMART_LLM으로, `temperature=0.15`, system 메시지는 `auto_agent_instructions()`(C-05), user 메시지는 `"task: {query}"`를 보낸다. `parent_query`가 있으면 query는 `"{parent_query} - {query}"`이다. 응답 JSON의 `server`를 agent로, `agent_role_prompt`를 role로 반환한다. 응답은 `json_repair.loads`로 먼저 파싱하고 객체가 아니면 `json.loads`를 시도한다. | 코드 확인 (C-06) |
| R-04 | R-03의 LLM 호출 예외, JSON 파싱 실패, `server`·`agent_role_prompt` 누락 | 예외를 밖으로 내지 않는다. `json_repair` 재파싱, 첫 `{`부터 마지막 `}`까지 정규식 추출을 차례로 시도하고, 두 키가 모두 truthy인 객체만 복구로 인정한다. 모두 실패하면 `("Default Agent", "You are an AI critical thinker research assistant. ...")`를 돌려준다(전체 문장은 C-06). LLM 호출이 10회 모두 실패하는 최악의 경우 약 55초의 대기 뒤에 기본 에이전트가 된다. | 코드 확인 (55초는 대기 규칙으로 계산한 값이라 추론) |
| R-05 | 선택된 role의 쓰임 | `plan_research`가 role을 `plan_research_outline`에 넘기지만 서브쿼리 생성에 쓰지 않는다. 따라서 이 파이프라인이 만드는 서브쿼리와 컨텍스트는 role과 무관하다. role은 `researcher.role`에 남아 `CURATE_SOURCES`의 curation(R-26)과 보고서 작성이 읽는다. | 코드 확인 |
| R-06 | `ResearchConductor.conduct_research`를 직접 호출했는데 `agent`/`role`이 비어 있음 | R-03과 같은 방식으로 `choose_agent`를 부른다(단 `**kwargs`는 넘기지 않음). `GPTResearcher`를 거치면 R-02에서 이미 채워져 실행되지 않는다. | 코드 확인 |
| R-07 | `visited_urls`, `context`의 수명 | `conduct_research` 시작에 `visited_urls`를 비우지 않는다. 생성자에 준 set은 같은 객체다(빈 set이어도 `None`이 아니면). 같은 set을 받은 여러 연구기는 서로 본 URL을 다시 가져오지 않고, 같은 인스턴스를 다시 부르면 이미 본 URL은 다시 가져오지 않는다. 생성자에 준 `context`는 쓰이지 않고 매 호출 결과로 덮어쓴다. | 코드 확인 |
| R-08 | 분기(경계) | `source_urls`가 truthy면 URL 경로로, 아니면 `report_source`를 `"web"`/`"local"`/`"hybrid"`/`"azure"`/`"langchain_documents"`/`"langchain_vectorstore"`와 순서대로 비교한다. 이 스펙은 `source_urls`가 falsy이고 `"web"`인 경로다. 어느 분기에도 맞지 않는 값(예: `"static"`)은 `research_data = []`로 끝나 컨텍스트가 `[]`가 된다. 분기 뒤에는 모든 경로가 R-26의 curation과 반환을 공유한다. | 코드 확인 |
| R-09 | 웹 경로 시작: 초기 검색 | `retrievers[0]` 하나로 원 질문을 검색한다. `query_domains`를 넘기고 `max_results = MAX_SEARCH_RESULTS_PER_QUERY`이며, 블로킹 호출이라 `asyncio.to_thread`로 실행한다. 클래스 이름에 `mcpretriever`가 있으면 `researcher`를 함께 넘겨 생성한다. 이 호출의 예외(생성자 오류 포함)는 잡히지 않아 `conduct_research` 밖으로 전파된다. 결과는 서브쿼리 계획의 참고 자료(`initial_results`)와 R-16의 입력이다. | 코드 확인 (Tavily 외 retriever가 실패를 삼키는지는 미확인. Tavily는 `[]`를 돌려줌) |
| R-10 | 서브쿼리 계획 호출 | `plan_research_outline(query, search_results=initial_results, ...)`를 부른다. `retriever_names`에 정확히 한 개가 있고 그 이름이 `"mcp"` 또는 `"MCPRetriever"`이면 LLM을 부르지 않고 `[query]`를 반환한다(C-03). 그 밖에는 `generate_sub_queries`를 호출한다. | 코드 확인 |
| R-11 | `generate_sub_queries`의 LLM 호출 | 3단 폴백(C-02). 1차: STRATEGIC_LLM, `max_tokens=None`, `reasoning_effort="medium"`. 예외 시 2차: STRATEGIC_LLM, `max_tokens=STRATEGIC_TOKEN_LIMIT`. 다시 예외 시 3차: SMART_LLM, `temperature=TEMPERATURE`, `max_tokens=SMART_TOKEN_LIMIT`. 3차도 예외면 잡지 않고 전파한다. 즉 계획 단계 실패는 빈 결과가 아니라 예외다. 응답은 `json_repair.loads`로 파싱해 R-13으로 정규화한다. | 코드 확인 |
| R-12 | 서브쿼리 프롬프트 | C-04의 문장을 따른다. 요청 개수는 `MAX_ITERATIONS or 3`이다. `report_type`이 `detailed_report` 또는 `subtopic_report`일 때만 task가 `"{parent_query} - {question}"`이다. `Context:` 부분은 `initial_results`가 비어 있지 않을 때만 들어가고(리스트를 문자열로 바꿔 삽입), 현재 UTC 날짜가 들어간다. 쿼리는 `site:` 같은 검색 연산자 없이 자연어로 쓰라고 지시한다. | 코드 확인 |
| R-13 | LLM 응답 정규화 | C-01의 규칙으로 `list[string]`을 만든다. 결과가 비고 원 질문이 공백이 아니면 `[원 질문]`으로 대체한다. | 코드 확인 |
| R-14 | 서브쿼리 개수 | 코드는 반환 목록을 `MAX_ITERATIONS`로 자르지 않는다. 프롬프트로 요청할 뿐이라 LLM이 더 많이 주면 그대로 처리한다. | 코드 확인 (LLM이 실제로 몇 개를 주는지는 미확인) |
| R-15 | 원 질문 덧붙이기 | `report_type != "subtopic_report"`이면 목록 끝에 `query`를 추가한다. 중복 제거는 없어서 LLM이 같은 문장을 내거나 R-10의 MCP 단독 경우(`[query]`)에는 같은 질문이 두 번 처리된다. | 코드 확인 |
| R-16 | 서브쿼리 병렬 처리 전 초기 컨텍스트 | `scraped_data`(웹 경로에서는 `[]`)가 비었고 `initial_results`가 비어 있지 않을 때만, 서브쿼리 처리를 시작하기 전에 순차로 실행한다. 첫 retriever 하나만 쓰고 새로 검색하지 않고 `initial_results`를 R-19~R-23 흐름에 넣은 뒤, 원 질문으로 선별해 `initial_context`로 둔다. `retrievers[0]`이 MCP이면 `""`이다. 이 안의 어떤 예외든 경고 로그 후 `""`가 된다. | 코드 확인 (C-10) |
| R-17 | 서브쿼리 병렬 | 목록 전체(원 질문 포함)에 `_process_sub_query`를 `asyncio.gather`로 동시에 실행하고 결과 순서는 목록 순서다. 동시 개수 제한은 이 단계에 없다(스크랩 동시성은 `WorkerPool`이 제한). | 코드 확인 |
| R-18 | 서브쿼리 하나의 검색 | 설정된 non-MCP retriever를 설정 순서대로 하나씩 처리한다(retriever 사이는 순차이고, 각 `search`는 스레드에서 실행). 생성은 `cls(query, query_domains=query_domains)`이며 `headers`는 넘기지 않는다. retriever별 생성·검색 예외는 로그만 남기고 다음 retriever로 넘어간다. `initial_results`가 주어진 호출(R-16)은 `retrievers[:1]`만 쓰고 검색하지 않는다. | 코드 확인 (C-07) |
| R-19 | 검색 결과 분류 | URL은 `href` 우선, 없으면 `url`이고 둘 다 없으면 무시한다. retriever 인스턴스의 `requires_scraping`이 `True`면 항상 URL 목록으로, `False`면 `raw_content`가 있을 때 prefetched로(없으면 URL 목록), 선언이 없으면 `raw_content` 길이가 100을 넘을 때만 prefetched로 분류한다. | 코드 확인 (C-07) |
| R-20 | URL 중복 제거 | URL 목록은 `visited_urls`에 없는 것만 남기고, 통과 즉시 `visited_urls`에 추가한 뒤 `random.shuffle`한다. 스크랩에 실패한 URL도 이미 추가돼 있어 같은 set을 쓰는 한 다시 시도하지 않는다. 동시에 도는 서브쿼리가 같은 URL을 내도 한 번만 통과한다(검사와 추가 사이에 `await`가 없고 이벤트 루프가 단일 스레드). | 코드 확인 (C-07, C-08) |
| R-21 | prefetched 결과 | `visited_urls` 검사를 받지 않고 항상 결과에 들어가며, `visited_urls`에 추가만 하고 `research_sources`에 `{"url": url}`을 넣는다. 같은 URL이 다른 서브쿼리에서 다시 prefetched로 오면 중복으로 들어간다. | 코드 확인 (C-07) |
| R-22 | 스크랩 | R-20을 통과한 URL 목록을 `browse_urls`에 넘기고 받은 페이지 목록 뒤에 prefetched를 이어 붙인다. 스크랩 단계는 예외를 내지 않는다(URL별 실패는 결과에서 빠지고, 스크랩 전체 예외는 빈 결과). URL 목록이 비어도 그대로 호출한다. 이 목록은 `vector_store`가 설정되면 거기에도 적재되지만 이 스펙은 다루지 않는다. | 코드 확인 (C-09) |
| R-23 | 선별 | 위 합친 목록이 비어 있지 않으면 `select_context(sub_query, pages, max_results=10)`의 결과를 web_context로 쓴다. 비어 있으면 선별하지 않고 web_context는 `""`이다. | 코드 확인 (C-12) |
| R-24 | 서브쿼리 격리와 결과 | `_process_sub_query` 안의 `Exception`은 로그 후 `""`를 반환해서 다른 서브쿼리에 영향이 없다. 정상이면 MCP 컨텍스트가 없을 때 `web_context.strip()`을, 이것이 비면 `""`를 반환한다. MCP 컨텍스트가 있으면 web_context 뒤에 빈 줄을 두고 `*Source: 제목 (URL)*`이 붙은 MCP 항목을 이어 붙인다. | 코드 확인 (MCP 결합 세부는 mcp-client 스펙) |
| R-25 | 결과 합치기와 실패 | `[initial_context, *서브쿼리 결과]` 중 truthy만 `" "`(공백 한 칸)로 이어 붙여 `str`로 반환한다. 하나도 없으면 `[]`다. 초기 컨텍스트 계산, `gather`, 합치기에서 예외가 나면 로그 후 `[]`를 반환한다. 초기 검색과 서브쿼리 계획(R-09~R-11)은 이 `try` 밖이라 예외가 전파된다. | 코드 확인 (C-11) |
| R-26 | `CURATE_SOURCES`가 true | `source_curator.curate_sources(research_data)`를 부른다. 결과가 리스트(`Title`/`Content`/`Source` dict)면 항목마다 `"Title: ...\nContent: ...\nSource: ..."`로 만들어 빈 줄 하나(`"\n\n"`)로 이어 붙인 문자열을 컨텍스트로 삼고, 아니면 반환값을 그대로 쓴다. LLM 호출·파싱이 실패하면 curation은 입력 `research_data`를 그대로 돌려주므로 컨텍스트가 유지된다. 꺼져 있으면(기본) 이 단계는 없다. | 코드 확인 (C-14) |
| R-27 | 반환과 후속 | 컨텍스트를 `self.context`에 저장해 반환한다. 반환 전에 `IMAGE_GENERATION_ENABLED`이면 컨텍스트를 읽어 이미지를 미리 계획·생성하지만(범위 밖) 컨텍스트를 바꾸지 않는다. | 코드 확인 |
| R-28 | 진행 이벤트 | `stream_output("logs", <content>, <output>, websocket, ...)`를 부른다. `planning_research` 두 번(초기 검색 시작, 계획 시작)은 `verbose`와 상관없이 항상 나가고, 나머지는 `verbose=True`일 때만 나간다. `content` 이름은 순서대로 대략 `starting_research`, `agent_generated`, `planning_research`(검색 중·계획 중 두 번), `subqueries`(`metadata`에 서브쿼리 목록), `running_subquery_research`, `added_source_url`(`metadata`에 URL), `researching`, `scraping_urls`, `scraping_content`, `scraping_images`, `scraping_complete`, `fetching_query_content`, `subquery_context_not_found`, `subquery_error`, `research_step_finalized`이다. websocket이 없거나 `output_log`가 true면 로거에도 출력한다. | 코드 확인 |
| R-29 | LLM 비용 기록 | `choose_agent`, 서브쿼리 생성, curation은 `cost_callback=add_costs`로 호출한다. `add_costs`는 숫자가 아니면 `ValueError`이고, 현재 단계(`_current_step`: 에이전트 선택 중 `"agent_selection"`, 그 뒤 `"research"`)의 `step_costs`에 누적한다. | 코드 확인 |

- 불변식:
  - 같은 `visited_urls` 객체를 쓰는 동안 R-20을 통과하는 URL은 한 번만 스크랩 대상이 된다(prefetched 제외). 전제: 단일 이벤트 루프, `visited_urls`를 이벤트 루프 스레드에서만 고친다(코드가 그렇다).
  - 웹 경로의 반환값은 비어 있지 않은 `str`이거나 `[]`이다. 단 R-26에서 curation 결과가 빈 리스트이면 `""`가 될 수 있다.
  - 이 파이프라인은 어떤 서브쿼리의 실패 때문에 다른 서브쿼리의 결과를 버리지 않는다. 계획 이전 단계(R-09~R-11)의 실패만 호출자까지 전파된다.
- 미결정: 없음
- 확인 한계:
  - 코드를 읽어서만 확인했고 실행하지 않았다(실행 확인 없음).
  - 최종 컨텍스트 문자열 안의 조각 형식(`Source:`/`Title:`/`Content:` 등)은 `select_context`의 몫이라 context-selection 스펙이 정한다. 이 스펙은 `str`이라는 점과 이어 붙이는 규칙까지 정한다.
  - LLM이 서브쿼리를 몇 개, 어떤 품질로 주는지와 외부 검색 API·웹 사이트의 실제 응답은 확인하지 못했다.

### 1.5 필수 코드 참조

라이선스: overview 1절을 따른다. Apache License 2.0(`LICENSE`)이고 `pyproject.toml`은 MIT로 적어 표기가 어긋난다. 이 스펙은 코드를 복사하지 않고 줄 범위만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/actions/query_processing.py:12-40` `_normalize_sub_queries` | LLM 파싱 결과(list / dict의 `queries`·`sub_queries`·`subQueries`·`items` / 단일 `query` / 문자열 / 그 밖)를 문자열 리스트로 바꾸고 비면 원 질문으로 대체하는 규칙 | R-13 |
| C-02 | `gpt_researcher/actions/query_processing.py:83-156` `generate_sub_queries` | STRATEGIC → STRATEGIC(토큰 한도 지정) → SMART의 3단 폴백과 각 호출의 인자 | R-11, R-12 |
| C-03 | `gpt_researcher/actions/query_processing.py:158-215` `plan_research_outline` | MCP 단독이면 `[query]`, 아니면 `generate_sub_queries`. `agent_role_prompt`는 받기만 하고 쓰지 않음 | R-05, R-10 |
| C-04 | `gpt_researcher/prompts.py:212-259` `PromptFamily.generate_search_queries_prompt` | 서브쿼리 프롬프트 전문(task 구성, context 삽입 조건, 연산자 금지 지시, 응답 형식) | R-12 |
| C-05 | `gpt_researcher/prompts.py:489-515` `PromptFamily.auto_agent_instructions` | 에이전트 선택 system 프롬프트와 세 개의 예시(Finance, Business Analyst, Travel) | R-03 |
| C-06 | `gpt_researcher/actions/agent_creator.py:18-154` `choose_agent`, `handle_json_error`, `_agent_pair_from_payload`, `extract_json_with_regex` | 파싱·복구 순서와 기본 에이전트의 이름·role 문장 | R-03, R-04 |
| C-07 | `gpt_researcher/skills/researcher.py:851-934` `_search_relevant_source_urls` | retriever 순회, 예외 격리, `requires_scraping` 3분기와 길이 100 기준, prefetched 처리, 중복 제거 호출과 셔플 | R-18~R-21 |
| C-08 | `gpt_researcher/skills/researcher.py:813-834` `_get_new_urls` | `visited_urls`에 없을 때만 추가하고 목록에 넣는 규칙 | R-20 |
| C-09 | `gpt_researcher/skills/researcher.py:936-973` `_scrape_data_by_urls` | 검색 → 스크랩 → prefetched 이어 붙이기 순서 | R-22 |
| C-10 | `gpt_researcher/skills/researcher.py:836-849` `_get_context_from_initial_results` | 초기 결과의 스크랩·선별과 예외를 `""`로 바꾸는 규칙, MCP 첫 retriever 예외 | R-16 |
| C-11 | `gpt_researcher/skills/researcher.py:364-408` `_get_context_by_web_search` (서브쿼리 계획 이후) | 초기 검색 → 계획 → 원 질문 추가 → 초기 컨텍스트 → `gather` → 합치기 → 예외 시 `[]` | R-09, R-15~R-17, R-25 |
| C-12 | `gpt_researcher/skills/researcher.py:605-613`, `:654-663` `_process_sub_query` 중 웹 경로와 예외 처리 | 스크랩 데이터가 비었을 때만 스크랩하고, 선별하고, 예외를 `""`로 바꾸는 규칙(그 사이의 MCP 처리는 mcp-client 스펙) | R-23, R-24 |
| C-13 | `gpt_researcher/skills/context_manager.py:38-64` `get_similar_content_by_query` | 선별 호출의 `max_results=10`과 인자 | R-23 |
| C-14 | `gpt_researcher/skills/researcher.py:211-229` | `CURATE_SOURCES` 후처리와 리스트→문자열 변환 형식 | R-26 |
| C-15 | `gpt_researcher/skills/browser.py:37-84` `BrowserManager.browse_urls` | 스크랩 결과를 `research_sources`에 누적하고 이미지 상위 4개를 `research_images`에 넣는 부수효과 | R-22 |
| C-16 | `gpt_researcher/agent.py:343-413` `GPTResearcher.conduct_research` | 딥 리서치 분기, 에이전트 선택, 조사 호출, 이미지 후처리 순서 | R-01, R-02, R-27 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았고 실행도 하지 않았다). retriever, 스크래퍼, `select_context`, LLM은 스텁으로 바꿔 생각한 사례이며, 그래서 실제 검색·스크랩·선별·LLM 품질은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-09~R-17, R-25 | 질문 `Q`, `research_report`, retriever 하나, 초기 검색 결과 2건, LLM이 `["A","B"]` 반환 | 서브쿼리 처리 대상은 `["A","B","Q"]`. 반환은 `initial_context`, A, B, Q의 비어 있지 않은 결과를 `" "`로 이은 문자열 |
| T-02 | R-15 | 같은 입력이지만 `report_type="subtopic_report"` | 처리 대상은 `["A","B"]`이고 `Q`는 추가되지 않는다 |
| T-03 | R-13 | `_normalize_sub_queries`에 파싱된 값으로 `{"queries": ["a"," b "]}` / `["a", ""]` / `""` / `{"query": "x"}` / `{"foo": 1}`를 줌(원 질문 `Q`) | 각각 `["a","b"]` / `["a"]` / `[Q]` / `["x"]` / `[Q]` |
| T-04 | R-20 | 서브쿼리 A와 B의 검색 결과가 같은 URL `U`를 포함 | `U`는 스크랩에 한 번만 전달되고 `visited_urls`에 `U`가 들어 있다 |
| T-05 | R-20, R-07 | `visited_urls={"U"}`를 주고 생성, 검색 결과에 `U`와 `V` | `V`만 스크랩된다. 생성자에 준 set 객체에 `V`가 추가돼 있다 |
| T-06 | R-20 | 스크랩이 `U`에서 실패(결과에서 빠짐) | `U`는 `visited_urls`에 남아 있고 같은 실행에서 다시 시도되지 않는다 |
| T-07 | R-19, R-21 | retriever가 `requires_scraping=False`이고 항목이 `raw_content`를 가짐. 같은 항목을 두 서브쿼리가 돌려줌 | 스크랩 없이 포함되고 두 서브쿼리 결과에 모두 들어간다(중복 포함) |
| T-08 | R-19 | `requires_scraping` 선언 없음, `raw_content` 길이 100 / 101인 항목 | 길이 100은 URL로 스크랩, 101은 prefetched |
| T-09 | R-18 | 두 retriever 중 첫 번째의 `search`가 예외 | 로그만 남고 두 번째 retriever 결과로 계속된다 |
| T-10 | R-24 | 서브쿼리 B의 선별(`select_context`)이 예외 | B는 `""`이고 A, Q의 결과는 반환에 포함된다 |
| T-11 | R-25 | 모든 서브쿼리와 초기 컨텍스트가 빈 결과 | 반환은 `[]`(빈 리스트), `self.context`도 `[]` |
| T-12 | R-09 | 초기 검색 호출이 예외를 냄(예: retriever 생성자가 예외) | `conduct_research`가 예외를 전파한다. 빈 결과가 아니다 |
| T-13 | R-11 | 서브쿼리 생성의 STRATEGIC 1차·2차·SMART 3차가 모두 예외 | 예외가 호출자까지 전파된다 |
| T-14 | R-11 | 1차만 예외, 2차 성공 | 2차의 응답으로 계획되고 예외는 없다. 2차 호출의 `max_tokens`는 `STRATEGIC_TOKEN_LIMIT` |
| T-15 | R-02 | `agent="X", role="Y"`로 생성 | `choose_agent`는 호출되지 않고 `agent`, `role`이 유지된다 |
| T-16 | R-04 | `choose_agent`의 LLM이 예외 / 키 하나가 없는 JSON / `{...}` 앞뒤에 설명이 붙은 JSON | 각각 `("Default Agent", 기본 role)` / 같은 기본 에이전트 / 복구한 값(`json_repair` 또는 정규식 경로, 어느 쪽이 먼저 성공하는지는 확인하지 않음) |
| T-17 | R-03 | `parent_query="P"`, `query="Q"` | LLM user 메시지는 `"task: P - Q"` |
| T-18 | R-16 | 초기 검색 결과가 `[]` | 초기 컨텍스트는 만들지 않고 서브쿼리 프롬프트에 `Context:` 부분이 없다. 계획과 서브쿼리 처리는 계속된다 |
| T-19 | R-26 | `CURATE_SOURCES=true`이고 curation LLM이 예외 | 컨텍스트는 curation 전 `research_data` 그대로 |
| T-20 | R-01 | `report_type="deep"` | `choose_agent`와 웹 파이프라인은 호출되지 않고 Deep Research의 결과가 반환된다 |
| T-21 | R-08 | `report_source="static"`, `source_urls` 없음 | 반환은 `[]` |
| T-22 | R-07 | 같은 인스턴스에서 `conduct_research`를 두 번 연속 호출(같은 검색 결과) | 두 번째 호출은 이미 본 URL을 다시 스크랩하지 않아(prefetched가 없다면) 선별할 페이지가 없고 `[]`를 반환한다. 생성자에 준 `context`는 두 호출 모두에서 결과로 덮어쓰인다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

문서와 구현의 차이(구현을 사실로 썼다):
- overview 그림 해설은 "`ResearchConductor._search`가 호출한다"고 쓰지만 웹 경로의 실제 검색은 `_search_relevant_source_urls`(`researcher.py:851`)다. `_search`(`:975`)는 `gpt_researcher/` 안에 호출처가 없다(Grep 확인). `_extract_content`, `_summarize_content`, `_update_search_progress`도 마찬가지다.
- overview 지도의 "요약 프롬프트"는 이 경로에서 쓰이지 않는다. `generate_summary_prompt`(`prompts.py:518`)는 정의만 있고 호출처가 없다.
- overview 지도는 서브쿼리를 "계획 → 병렬 처리"로만 적었지만 실제로는 계획 전에 초기 검색이 있고, 병렬 처리 전에 초기 결과를 먼저 소화한다(R-09, R-16).
- `plan_research_outline`의 docstring과 시그니처는 `agent_role_prompt`를 받는 것처럼 보이나 본문에서 쓰지 않는다(R-05).
- `_get_context_by_web_search`의 docstring은 "Returns: context: List of context"인데 실제는 `str` 또는 `[]`다(R-25).
- `generate_search_queries_prompt`의 docstring은 `max_iterations`를 "생성할 최대 쿼리 수"로 쓰지만 코드는 개수를 제한하지 않는다(R-14).
- `README.md`는 이번 스펙에서 대조하지 않았다.

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | `agent.py:191-193`(생성자), `:362-365` | 코드를 읽음 |
| R-02 | `agent.py:367-385`, C-16 | 코드를 읽음. `not (self.agent and self.role)` |
| R-03 | `actions/agent_creator.py:41-68`, `prompts.py:489-515` | 코드를 읽음 |
| R-04 | `actions/agent_creator.py:70-154` | 코드를 읽음. 10회 재시도 대기 합은 `utils/llm.py:122-135`의 `min(2**(attempt-1), 8)`로 계산한 값(1+2+4+8+8+8+8+8+8=55초, 추론) |
| R-05 | `skills/researcher.py:83-93`, `actions/query_processing.py:158-215`, `skills/curator.py:68`, `skills/writer.py:40` | `agent_role_prompt`가 `query_processing.py`에서 시그니처와 docstring에만 나온다는 것을 Grep으로 확인. writer의 사용은 한 줄만 확인했고 이 스펙 밖 |
| R-06 | `skills/researcher.py:128-137` | 코드를 읽음. `agent.py:372-381`은 `**self.kwargs`를 넘기고 여기는 넘기지 않음 |
| R-07 | `agent.py:161`, `skills/researcher.py:108-112`, `agent.py:163`, `:392`, `skills/researcher.py:212`, `backend/report_type/detailed_report/detailed_report.py:140-165`, `skills/deep_research.py:442-457` | 코드를 읽음. 상세 보고서가 `visited_urls=self.global_urls`를 넘기고 `subtopic_assistant.context`를 미리 채운 뒤 `conduct_research`가 덮어쓰는 것도 확인 |
| R-08 | `skills/researcher.py:112`, `:144-209`, `utils/enum.py:30-51` | 코드를 읽음. `static`에 대응하는 분기가 없음 |
| R-09 | `skills/researcher.py:50-66`, `:365`, `actions/query_processing.py:44-81`, `retrievers/tavily/tavily_search.py:108-156`, `config/variables/default.py:22` | 코드를 읽음. 초기 검색 호출이 `try` 밖인 것은 `researcher.py:365`(try는 `:384`부터)로 확인. 다른 retriever의 예외 처리는 읽지 않음 |
| R-10 | `skills/researcher.py:68-95`, C-03 | 코드를 읽음. 클래스 이름은 `retrievers/mcp/retriever.py:27` `MCPRetriever`, `actions/retriever.py:118` `case "mcp"` |
| R-11 | C-02, `utils/llm.py:41-162`, `config/variables/default.py:9-10`, `:15-16`, `:20` | 코드를 읽음. 폴백 로직을 코드로 추적했을 뿐 호출 흐름은 실행하지 않음 |
| R-12 | C-04, `config/variables/default.py:26` | 코드를 읽음. `PromptFamily` 하위 클래스가 이 메서드를 덮어쓰는지는 `generate_search_queries_prompt` 정의가 하나뿐임을 Grep으로 확인 |
| R-13 | C-01 | 코드를 읽음 |
| R-14 | C-01, `skills/researcher.py:366-371` | 코드를 읽음. 자르는 코드가 없음을 확인 |
| R-15 | `skills/researcher.py:369-371`, `actions/query_processing.py:189-199` | 코드를 읽음 |
| R-16 | C-10, `skills/researcher.py:386-391` | 코드를 읽음 |
| R-17 | `skills/researcher.py:392-398`, `skills/browser.py:32-35` | 코드를 읽음. 동시 개수 제한이 없음은 `gather`에 세마포어가 없다는 점으로 확인 |
| R-18 | C-07, `skills/researcher.py:861-869`, `:927-928`, `actions/query_processing.py:74` | 코드를 읽음. `for` 루프 안의 `await asyncio.to_thread`라 retriever 사이가 순차임 |
| R-19 | C-07, `retrievers/base.py:35-61` | 코드를 읽음. `requires_scraping`의 기본값 `True`는 `BaseRetriever` 상속 클래스에만 있고 상속하지 않으면 선언 없음 |
| R-20 | C-07, C-08, `skills/researcher.py:931-932` | 코드를 읽음. 검사·추가 사이 `await` 없음을 `:821-823`로 확인 |
| R-21 | `skills/researcher.py:905-913`, `:916-924` | 코드를 읽음 |
| R-22 | C-09, C-15, `actions/web_scraping.py:33-51`, `scraper/scraper.py:120-158`, `:194-281` | 코드를 읽음. 스크랩 세부 규칙(100자 미만, 차단 페이지 등)은 scrapers 스펙의 몫 |
| R-23 | C-12, C-13, `context/select.py:53-101` | 코드를 읽음 |
| R-24 | C-12, `skills/researcher.py:739-790`(`_combine_mcp_and_web_context`) | 코드를 읽음. MCP가 없을 때 `web_context.strip()`을 돌려주는 부분을 확인 |
| R-25 | C-11 | 코드를 읽음 |
| R-26 | C-14, `skills/curator.py:38-114` | 코드를 읽음. 실패 시 `source_data`를 돌려주는 부분은 `:105-114` |
| R-27 | `agent.py:392-413` | 코드를 읽음 |
| R-28 | `skills/researcher.py:114-126`, `:231-237` 외 `stream_output` 호출들, `actions/utils.py:7-32` | 코드를 읽음. 이벤트 이름은 `researcher.py`, `skills/browser.py`, `skills/context_manager.py`에서 Grep한 목록이며 순서는 대략이다 |
| R-29 | `agent.py:367-392`, `:785-806`, `actions/agent_creator.py:54`, `actions/query_processing.py:125` | 코드를 읽음 |
| T-01~T-22 | 해당 R-ID의 근거와 같다 | 구현에서 도출한 사례다. 실행하지 않았다 |

### 2.2 코드 읽는 순서

1. `agent.py:343` `GPTResearcher.conduct_research`: deep 분기, 에이전트 선택, 조사 호출.
2. `skills/researcher.py:97` `ResearchConductor.conduct_research`: 소스 분기와 curation.
3. `skills/researcher.py:298` `_get_context_by_web_search`: 초기 검색 → 계획 → `gather` → 합치기.
4. `actions/query_processing.py` → `prompts.py:212`: 서브쿼리 계획과 프롬프트.
5. `skills/researcher.py:520` `_process_sub_query` → `:936` `_scrape_data_by_urls` → `:851` `_search_relevant_source_urls`: 서브쿼리 한 개의 검색·스크랩.
6. `skills/context_manager.py:38` → `context/select.py:53`: 선별(경계).

원본의 구현 전략은 "한 번의 초기 검색을 계획 재료와 첫 스크랩 대상에 모두 쓰는 것"이다. `researcher.py:385-387`의 주석은 "나중 검색이 계획에 쓴 출처를 잃기 전에 먼저 읽는다"고 설명한다.
