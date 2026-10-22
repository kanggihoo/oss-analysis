---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/mcp/__init__.py
  - gpt_researcher/mcp/client.py
  - gpt_researcher/mcp/tool_selector.py
  - gpt_researcher/mcp/research.py
  - gpt_researcher/mcp/streaming.py
  - gpt_researcher/mcp/README.md
  - gpt_researcher/retrievers/__init__.py
  - gpt_researcher/retrievers/mcp/__init__.py
  - gpt_researcher/retrievers/mcp/retriever.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/deep_research.py
  - gpt_researcher/agent.py
  - gpt_researcher/actions/query_processing.py
  - gpt_researcher/actions/retriever.py
  - gpt_researcher/actions/utils.py
  - gpt_researcher/prompts.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/base.py
  - gpt_researcher/config/variables/default.py
  - backend/server/server_utils.py
  - backend/server/websocket_manager.py
  - backend/report_type/detailed_report/detailed_report.py
  - pyproject.toml
  - requirements.txt
  - docs/docs/gpt-researcher/retrievers/mcp-configs.mdx
  - tests/skills/test_tavily_mcp_dedupe.py
depends:
  - ../capabilities/research-pipeline.md
status: ready
reimplementation: 미실행
---

# MCP 연동

> `mcp_configs`(MCP 서버 접속 설정 목록)를 주면 질문마다 MCP 서버의 도구 가운데 LLM이 고른 최대 3개를 LLM이 한 번 호출해 얻은 결과를 웹 컨텍스트와 합쳐 주고, `mcp_strategy`(fast / deep / disabled)로 MCP를 몇 번 실행할지 정한다.

<!--
용어
- MCP(Model Context Protocol): LLM 앱이 외부 도구·데이터 서버와 통신하는 개방형 프로토콜. 서버가 "도구"(이름, 설명, 인자)를 알려 주면 클라이언트가 호출한다.
- langchain-mcp-adapters: MCP 서버의 도구를 LangChain 도구 객체로 바꿔 주는 라이브러리. 이 기능은 `MultiServerMCPClient(서버 설정 맵)`을 만들고 `await client.get_tools()`로 도구 목록을 받는다. 이 환경에는 설치하지 못했다(확인 한계).
- stdio / http / websocket: MCP 서버에 붙는 방식. stdio는 설정한 명령으로 자식 프로세스를 띄워 표준 입출력으로 통신하고, 나머지는 URL로 접속한다.
- 사전 실행: 서브쿼리를 계획하기 전에 MCP를 먼저 한 번 돌려 결과를 캐시에 두는 단계. 원본에 이런 이름은 없고 설명을 위해 붙인 중립 이름이다(코드 주석은 "CONFIGURABLE MCP OPTIMIZATION").
- MCP 클래스: 클래스 이름을 소문자로 바꿨을 때 `mcpretriever`가 들어 있는 retriever 클래스. 내장은 `MCPRetriever` 하나다.
- 컨텍스트 항목: MCP 결과 한 건을 `{content, url, title, query, source_type}` 딕셔너리로 바꾼 것(R-13).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`GPTResearcher(query=..., mcp_configs=[...])`를 만들고 `conduct_research()`를 부르는 경우다. `RETRIEVER`는 기본값 `"tavily"`, 전략은 기본값 `fast`라고 하자.

1. 생성자가 `mcp_configs`를 저장하고, 비어 있지 않으면 `cfg.retrievers`의 끝에 `"mcp"`를 덧붙인다. 그 뒤 retriever 이름 목록을 클래스로 바꾸므로 목록은 `[TavilySearch, MCPRetriever]`가 된다. 전략은 인자·설정에서 `fast`로 정해진다(R-01~R-05).
2. `conduct_research()`가 웹 경로(`_get_context_by_web_search`)에 들어가면, 서브쿼리 계획이나 초기 검색보다 먼저 MCP를 사전 실행한다. `fast`면 원 질문으로 MCP를 한 번 돌려 결과를 conductor의 캐시에 두고, `deep`이면 아무것도 하지 않고 서브쿼리 단계로 미루며, `disabled`면 이벤트만 남긴다(R-06).
3. 서브쿼리마다 `_process_sub_query`가 돈다. 직접 Tavily와 Tavily MCP가 겹치면 MCP를 뺀다. 아니면 `fast`는 캐시를 복사해 쓰고, `deep`은 그 서브쿼리로 MCP를 새로 돌리며, `disabled`는 건너뛴다(R-07, R-12).
4. MCP를 한 번 돌린다는 것은 `MCPRetriever`를 새로 만들어 `search()`를 부르는 일이다. 안에서 MCP 서버 도구 목록을 읽고, LLM이 질문에 맞는 도구를 최대 3개 고르고(실패하면 이름 패턴 점수로 대체), LLM을 도구와 함께 딱 한 번 호출해 나온 도구 호출을 차례로 실행하고, 결과를 `{title, href, body}`로 정규화하고, LLM의 텍스트 답을 "LLM Analysis" 항목으로 덧붙이고, `max_results`개로 자른다(R-14~R-23).
5. 결과 중 본문이 있는 것을 컨텍스트 항목으로 바꾸고, 서브쿼리의 웹 컨텍스트 뒤에 `*Source: 제목 (URL)*` 인용을 붙여 이어 붙인다. MCP 항목은 컨텍스트 선별을 거치지 않는다(R-13, R-26).
6. 서브쿼리 결과는 파이프라인 규칙대로 합쳐 반환된다. MCP 쪽 실패(서버·도구·LLM·타임아웃)는 어디서든 "그 MCP 실행의 결과가 빈 목록"으로 끝나고 조사는 계속된다(R-25). 예외는 R-27이다.

### 1.2 범위·통합 지점

- 제공: `mcp_configs` 형식과 langchain-mcp-adapters 형식으로의 변환, 전략 결정과 실행 시점·횟수, MCP 결과 캐시와 잠금, 도구 자동 선택과 폴백, 도구 실행과 결과 정규화, Tavily MCP 중복 건너뛰기, 웹 컨텍스트와의 결합 형식, 클라이언트 수명, 스트리밍 이벤트, 실패 처리.
- 제외:
  - MCP 서버 본체. 별도 레포(gptr-mcp)로 옮겨졌고(`mcp-server/README.md`) 이 레포에 없다.
  - LLM 제공자 선택, `create_chat_completion`, `GenericLLMProvider.from_provider`와 `.llm.bind_tools`의 내부, `Config` 로딩, 임베딩(사용자 제외). 설정 키는 원문 이름만 쓴다.
  - 웹 검색·스크랩·컨텍스트 선별(다른 스펙). MCP가 끼어드는 곳만 R-ID로 적는다. retriever 이름을 클래스로 바꾸는 일반 규칙(`get_retrievers`)은 [retrievers.md](../capabilities/retrievers.md)가 맡고, 이 스펙은 MCP가 걸리는 곳(R-01~R-03)만 다룬다.
  - 서버 REST·WebSocket 필드의 해석은 서버 API 스펙의 몫이다. 이 스펙은 `mcp_enabled`·`mcp_strategy`·`mcp_configs`가 `GPTResearcher`까지 전달되는 경계만 R-31에 적는다.
- 외부 의존·선행 계약:

  | 대상 | 이 스펙이 주는 입력 | 정상 결과 | 실패 시 이 스펙이 보는 것 |
  |---|---|---|---|
  | 파이프라인 [research-pipeline.md](../capabilities/research-pipeline.md) | `ResearchConductor`가 `_get_context_by_web_search` 안에서 MCP 경로를 호출 | 서브쿼리별 컨텍스트 문자열(R-24 of 파이프라인)에 MCP 항목이 섞임 | MCP 쪽 실패는 파이프라인에 예외로 나가지 않는다(R-25) |
  | langchain-mcp-adapters | `MultiServerMCPClient(서버 이름 → 연결 설정 맵)` 생성, `await client.get_tools()` | 도구 객체 목록. 각 도구는 `name`, `description`, `ainvoke(args)`를 가짐 | 생성 예외는 클라이언트 없음(R-18), `get_tools()` 예외는 빈 도구 목록(R-18). 미설치는 R-03 |
  | LLM(도구 선택) | `create_chat_completion(model=STRATEGIC, messages=[user 프롬프트], temperature=0.0, llm_provider, llm_kwargs, cost_callback)` | 문자열 | 예외·빈 응답은 폴백(R-20) |
  | LLM(도구 호출) | `GenericLLMProvider.from_provider(provider, model=..., **llm_kwargs).llm.bind_tools(도구들).ainvoke(messages)` | 메시지 객체: `tool_calls`(각 `{name, args}`)와 `content` | 어느 단계든 예외면 그 실행의 결과는 빈 목록(R-22) |
  | websocket(선택) | `stream_output("logs", 이름, 문자열, websocket, ...)` | JSON 한 건 전송 | MCPStreamer는 예외를 삼킨다(R-29) |

- 소유 상태·부작용:
  - `GPTResearcher.mcp_configs`(그대로 저장), `GPTResearcher.mcp_strategy`(R-04로 정한 문자열), 인스턴스의 `cfg.retrievers`(R-01). 환경변수와 전역 상태는 건드리지 않는다.
  - `ResearchConductor._mcp_results_cache`(`None` 또는 컨텍스트 항목 리스트), `_mcp_cache_lock`(asyncio 잠금), `_mcp_query_count`(0으로 만들기만 하고 쓰지 않음). `ResearchConductor`마다 하나이므로 상세 보고서의 소제목 연구자나 Deep Research의 하위 연구자는 각자의 캐시를 가진다(R-09).
  - MCP를 한 번 실행할 때마다 `MCPRetriever`·`MCPClientManager`·`MultiServerMCPClient`를 새로 만든다. 실행 사이에 공유하는 것이 없다(R-18).
  - MCP 결과는 `research_sources`에 올리지 않는다. 이 기능이 비용을 올리는 곳은 도구 선택 LLM 호출 하나뿐이다(R-20, R-22).
  - 외부 자원: MCP 서버(stdio면 자식 프로세스, 아니면 네트워크 연결), LLM API 호출(MCP 실행 한 번당 도구 선택 1회, 도구 호출 1회).
- 파이프라인 스펙의 "MCP가 있을 때 달라지는 5곳"과 이 스펙의 대응(5곳의 MCP 쪽 동작은 이 스펙이 소유한다): 초기 검색이 MCP일 수 있음(파이프라인 R-09) → R-10, MCP만 있으면 LLM 없이 `[query]`(R-10) → R-10, 초기 컨텍스트 생략(R-16) → R-10·R-11, URL 수집에서 MCP 건너뜀(R-18) → R-11, MCP 컨텍스트를 합침(R-24) → R-07·R-26. 파이프라인의 목록에 없는 것이 하나 더 있다. 서브쿼리 계획 전의 사전 실행(R-06)이다.

### 1.3 인터페이스와 데이터 의미

**진입 인자 (`GPTResearcher.__init__`)**

| 인자 | 타입 | 의미·제약 |
|---|---|---|
| `mcp_configs` | `list[map]` 또는 없음 | 서버 설정 목록. 참(비어 있지 않음)일 때만 MCP가 켜진다. `[]`와 `None`은 같다(R-01). 복사하지 않고 같은 객체를 저장하며 `GPTResearcher.mcp_configs`로 읽힌다. |
| `mcp_strategy` | `"fast"` / `"deep"` / `"disabled"` 또는 없음 | R-04의 우선순위로 해석. 옛 이름 `"optimized"`는 `fast`, `"comprehensive"`는 `deep`. |
| `mcp_max_iterations` | `int` 또는 없음 | 폐기 예정. `mcp_strategy`가 없을 때만 읽는다: `0`은 disabled, `1`은 fast, `-1`은 deep, 그 밖의 수는 fast. |

**`mcp_configs` 항목** (원문 키 이름. 항목마다 map이어야 하며 검증은 R-19가 하는 것뿐이다)

| 키 | 타입 | 읽는 곳과 의미 |
|---|---|---|
| `name` | string | 서버 이름(변환 결과의 키). 없으면 `mcp_server_<목록 위치+1>`. 같은 이름이면 뒤의 항목이 앞을 덮어쓴다. Tavily 중복 판정(R-12)도 읽는다. |
| `command` | string | stdio에서만 쓴다. 비어 있으면 stdio 설정에 `command`가 들어가지 않는다. |
| `args` | list 또는 string | stdio에서만 쓴다. 문자열이면 공백으로 나눈다. 기본값 `[]`. 목록 원소는 검증하지 않는다. |
| `env` | map | stdio에서만 쓴다. 참일 때만 전달. 현재 프로세스 환경과 합치는지는 어댑터의 몫이다. |
| `connection_url` | string | 스킴으로 연결 방식을 정한다(아래 표). |
| `connection_type` | string | URL이 없거나 스킴이 `ws`/`wss`/`http`/`https`가 아닐 때의 연결 방식. 기본 `"stdio"`. 값을 검증하지 않고 어댑터에 그대로 넘긴다. |
| `connection_token` | string | 참이면 변환 결과의 `token` 키로 모든 연결 방식에 붙인다. |
| `connection_headers` | map | 연결 방식이 `streamable_http`·`http`·`websocket`이고 map일 때 `headers`로 전달. README·docs 표에 없고 코드에만 있다. |
| `tool_name` | string | README와 `GPTResearcher` docstring에 있지만 읽는 코드가 없다. |

연결 방식 결정(`connection_url`이 참일 때. 스킴은 소문자로 바꿔 비교하고 URL 원문은 보존):

| URL 스킴 | `transport` | `url` |
|---|---|---|
| `ws`, `wss` | `websocket` | 원문 |
| `http`, `https` | `streamable_http`(`connection_type`은 무시) | 원문 |
| 그 밖·스킴 없음 | `connection_type`(기본 `stdio`) | `connection_type`이 `websocket`·`streamable_http`·`http`일 때만 원문 |

URL이 없으면 `transport = connection_type`(기본 `stdio`)이고 `url`은 없다. 변환 결과의 필드는 `transport`, `url`, `headers`, `command`, `args`, `env`, `token`이고 C-01이 규칙이다.

**설정 키** (원문 이름. 환경변수가 같은 이름의 설정값을 덮어쓴다. 타입 변환은 파이프라인 스펙 1.3과 같다)

| 키 | 기본값 | 쓰임 |
|---|---|---|
| `MCP_STRATEGY` | `"fast"` | 전략의 설정 기본값(R-04 3순위). `GPTResearcher` 안에서는 인자가 없을 때만 읽힌다. |
| `MCP_SERVERS` | `[]` | 코드에서 `Config.get_mcp_server_config(name)`이 이름으로 찾는 용도로만 저장된다. 이 메서드의 호출처는 테스트뿐이고 `mcp_configs`를 채우지 않는다(R-24). |
| `MCP_AUTO_TOOL_SELECTION` | `True` | 읽는 코드가 없다(R-24). 도구 선택은 이 값과 무관하게 항상 일어난다. |
| `MCP_ALLOWED_ROOT_PATHS` | `[]` | 읽는 코드가 없다(R-24). 허용 경로 검사는 이 레포에 없다. |
| `MCP_USE_LLM_ARGS` | 없음 | `BaseConfig`에 타입만 있고 `DEFAULT_CONFIG`에 키가 없으며 읽는 코드도 없다. |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `5` | MCP 실행 한 번의 결과 상한(R-14, R-17). |
| `STRATEGIC_LLM` | `"openai:gpt-5.4"` | 도구 선택과 도구 호출 LLM(R-20, R-22). |

**MCP 데이터**

| 데이터 | 형태 | 의미·제약 |
|---|---|---|
| MCP 결과 항목 | `{title: string, href: string, body: string}` | `MCPRetriever.search`가 돌려주는 단위. `href`는 도구가 준 URL이 없으면 `mcp://<도구 이름>` 또는 `mcp://<도구 이름>/<번호>`이고 LLM의 텍스트 답은 `mcp://llm_analysis`. `body`는 보통 문자열이지만 LLM 답은 모델이 준 `content` 그대로라서 문자열이 아닐 수 있다(R-27). |
| 컨텍스트 항목 | `{content, url, title, query, source_type: "mcp"}` | 결과 항목에서 `body→content`, `href→url`로 옮기고 그 실행의 질문을 `query`에 넣는다. 캐시에 쌓이는 단위(R-13). |
| `MCPRetriever(query, headers=None, query_domains=None, websocket=None, researcher=None, **kwargs)` | 객체 | `researcher`에서 `mcp_configs`와 `cfg`를 꺼낸다. `headers`·`query_domains`는 저장만 하고 쓰지 않는다. |
| `search(max_results=10)` | → `list[MCP 결과 항목]` | 동기. 항상 list를 돌려주고 예외를 내지 않는다(R-16). |
| `search_async(max_results=10)` | 코루틴 → 같은 list | 같은 규칙(R-17). |

**진행 이벤트**: `MCPStreamer`는 `websocket`이 있을 때 `stream_output(type="logs", content="mcp_retriever", output=<문장>, websocket, metadata=None)`를 보낸다(`verbose`와 무관, R-29). `ResearchConductor`는 `verbose=True`일 때 `stream_output("logs", <이름>, <문장>, websocket)`을 보낸다. 이름: `mcp_disabled`, `mcp_optimization`(fast 사전 실행), `mcp_comprehensive`(deep 안내), `mcp_results_cached`, `mcp_cache_error`, `mcp_tavily_deduped`, `mcp_cache_reuse`, `mcp_comprehensive_run`, `mcp_fallback`, `context_combined`, `mcp_retrieval_stage1`, `mcp_research_complete`, `mcp_no_results`, `mcp_research_error`.

### 1.4 행동 규칙과 남은 질문

다음 표의 "실행 확인"은 소스 줄을 그대로 exec하되 MCP 서버·LLM·도구·retriever·스크랩·선별·`stream_output`을 가짜로 바꾼 실험이다(2.1, `mcp-demos/`). 가짜가 검증하지 않는 것은 1.4 끝의 확인 한계에 적었다.

**활성화와 구성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `GPTResearcher`에 truthy한 `mcp_configs`를 줌 | `self.mcp_configs`에 저장하고, `get_retrievers`를 부르기 전에 `cfg.retrievers`를 고친다(C-04): 리스트(문자열이면 쉼표로 나눠 리스트로)에 `"mcp"`가 없을 때만 끝에 덧붙이고, retrievers가 비어 있으면 `["mcp"]`로 한다. 이미 있으면 순서를 바꾸지 않는다(`RETRIEVER=mcp,tavily`면 MCP가 첫 번째로 남는다). `os.environ`은 건드리지 않는다. `[]`·`None`이면 아무것도 하지 않는다(그래서 `mcp_configs=[]`만으로는 MCP 클래스가 목록에 들어가지 않는다). | 실행 확인(소스 exec) |
| R-02 | retriever 목록에 MCP 클래스가 들어가는 조건 | `get_retrievers`가 헤더 `retrievers`/`retriever`를 먼저 읽는다. 헤더에 값이 있으면 `cfg.retrievers`(R-01이 덧붙인 `"mcp"` 포함)를 읽지 않으므로 `mcp_configs`를 줘도 MCP는 목록에 없고 실행되지 않는다. 반대로 `RETRIEVER`에 `mcp`를 적고 `mcp_configs`를 주지 않으면 MCP 클래스는 있지만 설정이 비어 `search()`가 즉시 `[]`를 돌려준다(R-15, R-16). `RETRIEVER`에 `mcp`를 중복해 적으면 클래스도 중복되고 그만큼 실행된다(R-13). | 코드 확인 (헤더 우선은 `get_retrievers`를 exec해 확인) |
| R-03 | langchain-mcp-adapters 미설치 | `mcp/__init__.py`는 `HAS_MCP_ADAPTERS=False`만 내보내고, `retrievers/mcp/__init__.py`는 `MCPRetriever = None`으로 만든다(경고 로그 한 줄). `get_retriever("mcp")`가 `None`을 돌려주므로 `get_retrievers`가 그 이름을 조용히 `TavilySearch`로 바꾼다(예: `["tavily","mcp"]` → `[Tavily, Tavily]`, `["mcp"]` → `[Tavily]`). MCP는 실행되지 않고 오류도 없다. `MCPClientManager`를 직접 쓰면 `get_or_create_client()`는 `None`, `get_all_tools()`는 `[]`(R-18). `pyproject.toml`은 `mcp`만 의존성에 넣고 `langchain-mcp-adapters`는 `requirements.txt`에만 있으므로(2.1) `pyproject.toml`만으로 설치하면 MCP가 이 경로로 꺼진다. | 실행 확인(이 환경에 미설치라서 실제 파일을 exec) |

**전략**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-04 | `GPTResearcher.mcp_strategy`를 정하는 우선순위(C-03, 생성자 마지막에 한 번) | ① `mcp_strategy` 인자가 있으면: `fast`/`deep`/`disabled`는 그대로, `optimized`→`fast`, `comprehensive`→`deep`(둘 다 경고), 그 밖의 값은 경고 후 `fast`. ② 인자가 없고 `mcp_max_iterations`가 있으면(경고) `0`→`disabled`, `1`→`fast`, `-1`→`deep`, 그 밖의 수→`fast`. ③ 둘 다 없으면 `cfg.mcp_strategy`(`MCP_STRATEGY`): 세 값 그대로, `optimized`→`fast`, `comprehensive`→`deep`, 그 밖의 값은 경고 없이 `fast`. ④ 기본 `fast`. 인자가 있으면 `mcp_max_iterations`는 무시한다(`("deep", 0)`은 `deep`). | 실행 확인(소스 exec, 17개 조합) |
| R-05 | `ResearchConductor._get_mcp_strategy`(C-06) | `researcher.mcp_strategy`가 `None`이 아니면 그 값, 아니면 `cfg.mcp_strategy`, 아니면 `"fast"`. `GPTResearcher`를 거치면 `mcp_strategy`가 항상 R-04의 세 값 중 하나라서 첫 분기만 쓰인다. 코드가 `mcp_strategy`에 다른 문자열을 직접 넣었을 때만(예: `None`으로 두고 `cfg`가 `"foo"`) 알 수 없는 값이 되고, 그러면 사전 실행은 fast처럼 캐시하는데(경고) 서브쿼리는 캐시를 쓰지 않고 서브쿼리마다 MCP를 실행한다(R-07 마지막 행): 원 질문 사전 실행 1회 + 서브쿼리 N+1회. | 실행 확인 |

**언제 몇 번 실행되는가**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `_get_context_by_web_search`의 사전 실행(C-05). 이 함수는 서브쿼리 계획·초기 검색보다 앞에서 먼저 아래를 한다. MCP 클래스 목록은 `retrievers` 중 이름에 `mcpretriever`가 들어간 것이다. | MCP 클래스가 있고 `_mcp_results_cache is None`이면 `_mcp_cache_lock`을 잡고 전략으로 가른다. `fast`: `_execute_mcp_research_for_queries([query], mcp_retrievers)`(R-13)를 한 번 부르고 반환된 리스트를 `_mcp_results_cache`에 둔다(빈 리스트도 캐시된다). `deep`: 아무것도 하지 않는다(캐시 안 함, 안내 이벤트만). `disabled`: 아무것도 하지 않는다(이벤트 `mcp_disabled`만). 그 밖의 값: 경고 후 `fast`처럼 캐시한다. `query`는 이 호출의 질문이다(일반 조사는 사용자의 질문, 소제목 연구자는 소제목). 사전 실행에는 Tavily 중복 판정(R-12)이 적용되지 않는다. | 실행 확인 |
| R-07 | `_process_sub_query`의 MCP 분기(C-07). 서브쿼리 하나를 처리할 때 Tavily 판정(R-12) 뒤에 MCP 클래스가 남아 있으면 | `disabled`: 건너뜀. `fast`이고 캐시가 `None`이 아니면: `_mcp_results_cache.copy()`(얕은 복사)를 그 서브쿼리의 MCP 컨텍스트로 쓴다(이벤트 `mcp_cache_reuse`). `deep`: `_execute_mcp_research_for_queries([sub_query], mcp_retrievers)`를 불러 그 서브쿼리 전용 결과를 쓴다. 그 밖(캐시가 `None`인 `fast`, 알 수 없는 값): 이벤트 `mcp_fallback`과 함께 같은 방식으로 그 서브쿼리를 실행한다. MCP 컨텍스트 목록과 웹 컨텍스트는 R-26으로 합쳐 서브쿼리 결과가 된다. | 실행 확인 |
| R-08 | 실행 횟수 요약(R-06, R-07, R-10의 합). N은 계획이 만든 서브쿼리 수이고 `report_type != "subtopic_report"`면 원 질문이 하나 더 붙으므로 처리 대상은 N+1개다. | 아래 표. 한 `ResearchConductor`당 횟수이고, 한 번은 `MCPRetriever.search` 한 번이다. 상세 보고서의 소제목 연구자나 Deep Research의 하위 연구자는 새 conductor라 따로 센다. 하이브리드(`report_source=hybrid`)와 문서 소스는 `_get_context_by_web_search`를 두 번 부르는데 `fast`는 잠금과 캐시 덕에 사전 실행이 한 번이고 `deep`은 패스마다 센다. | 실행 확인(표의 굵은 칸), 나머지는 코드 확인 |
| R-09 | 캐시와 잠금의 수명 | `_mcp_results_cache`는 `ResearchConductor` 생성 때 `None`이고 사전 실행(R-06)만 값을 넣는다. 지우거나 갱신하는 코드가 없어서, 같은 인스턴스에서 `conduct_research`를 다시 부르면 `fast`는 MCP를 다시 실행하지 않고 첫 질문의 MCP 결과를 다른 질문에도 쓴다. 캐시 항목의 `query`는 첫 질문이다. 잠금은 하이브리드의 두 패스가 동시에 들어와도 사전 실행을 한 번만 하게 한다(잠금 없이 같은 상황이면 두 번 실행됨을 대조 실험으로 확인). 잠금은 사전 실행 블록에서만 잡고 서브쿼리 단계는 잠금 밖이다. 캐시 항목 딕셔너리는 서브쿼리 사이에 공유된다(리스트만 복사). | 실행 확인 |
| R-10 | `retrievers[0]`이 MCP 클래스(예: `RETRIEVER=mcp` 또는 `mcp,tavily`)일 때의 초기 검색(C-23, C-24) | 서브쿼리 계획 전 초기 검색(`get_search_results`)이 전략·캐시와 무관하게 MCP를 한 번 더 실행한다: `MCPRetriever(query, query_domains=..., researcher=...)`를 만들고 `search(max_results)`를 `asyncio.to_thread`로 부른다. 이 결과는 ⓐ MCP가 `retrievers`의 유일한 원소면 쓰이지 않는다. 계획이 LLM 없이 `[query]`를 돌려주기 때문이다(`retriever_names`가 정확히 하나이고 `"MCPRetriever"`일 때만. C-24). 처리 대상은 `[query]` + 원 질문 = `[Q, Q]`(소제목 연구자는 `[Q]`)다. ⓑ 웹 retriever가 함께 있으면 서브쿼리 프롬프트의 `Context`로만 쓰이고 스크랩하지 않는다. 초기 컨텍스트는 항상 `""`다(C-25). 그래서 `disabled`여도 MCP가 첫 번째면 MCP가 한 번 실행되고 결과는 버려진다. | 실행 확인 |
| R-11 | MCP 클래스는 URL을 주지 않는 retriever로 취급 | `_search_relevant_source_urls`는 MCP 클래스를 건너뛴다(C-26). 따라서 MCP 단독이면 URL·스크랩·웹 컨텍스트가 없고(스크랩 결과가 비어 `web_context`는 `""`), 서브쿼리 결과는 MCP 항목만이거나 `""`다. | 실행 확인 |
| R-12 | Tavily MCP 중복 건너뛰기(`_tavily_mcp_redundant_with_direct`, C-09). `_process_sub_query` 맨 앞에서 한 번 판정 | 다음을 모두 만족하면 "중복"이다: MCP 클래스와 non-MCP retriever가 모두 있고, non-MCP 중에 클래스 이름이 소문자로 `tavilysearch`인 것이 있고, `researcher.mcp_configs`가 비어 있지 않고, 모든 설정이 dict이며 각각 `"<name> <args를 공백으로 이은 문자열> <command>"`를 소문자로 만든 글에 `tavily`가 들어 있다. `args`가 문자열이면 글자 단위로 이어져(`"t a v i l y"`) 못 찾고, `connection_url`·`env`는 보지 않는다. 중복이면 경고 로그와 이벤트 `mcp_tavily_deduped`를 내고 그 서브쿼리의 MCP 클래스 목록을 비워 전략과 관계없이 MCP 컨텍스트를 만들지 않는다(캐시도 쓰지 않는다). 사전 실행(R-06)에는 이 판정이 없어서 `fast`에서는 MCP가 한 번 실행되고 그 결과가 쓰이지 않는다. `deep`은 MCP 실행이 0회다. | 실행 확인 |
| R-13 | `_execute_mcp_research_for_queries(queries, mcp_retrievers)`(C-08) | 질문 순서대로, 각 질문에서 MCP 클래스를 목록 순서대로 하나씩 `_execute_mcp_research`(R-14)로 실행한다(병렬 아님. 같은 클래스가 목록에 두 번 있으면 두 번). 결과 항목 중 `body`가 비어 있지 않은 것만 컨텍스트 항목 `{content, url, title, query, source_type:"mcp"}`로 만들어 한 리스트에 모아 돌려준다(`url=href`, 없으면 `""`). 결과가 있으면 이벤트 `mcp_results_cached`를 낸다. 클래스 하나가 예외를 내면 로그와 이벤트 `mcp_cache_error`만 남기고 다음으로 간다. | 실행 확인 |
| R-14 | `_execute_mcp_research(retriever, query)`(C-10) | `retriever(query=query, headers=researcher.headers, query_domains=researcher.query_domains, websocket=researcher.websocket, researcher=researcher)`를 만들어 이벤트 `mcp_retrieval_stage1`을 낸 뒤 `retriever_instance.search(max_results=cfg.max_search_results_per_query)`를 동기로 부른다. `await`·스레드 없이 부르므로 `search`가 끝날 때까지 호출한 이벤트 루프가 멈춘다(R-16). 결과가 있으면 이벤트 `mcp_research_complete`, 없으면 `mcp_no_results`와 `[]`. 생성자·검색의 모든 `Exception`은 이벤트 `mcp_research_error`와 함께 `[]`가 된다. | 실행 확인(검색은 가짜) |

**한 번의 MCP 실행 (`MCPRetriever`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | `MCPRetriever` 생성(C-12) | `researcher`에서 `mcp_configs`(`researcher.mcp_configs or []`)와 `cfg`를 꺼낸다. `researcher`가 없거나 `cfg`가 없으면 `ValueError`(`GPTResearcher`에서는 일어나지 않는다). `MCPClientManager`, `MCPToolSelector`, `MCPResearchSkill`, `MCPStreamer`를 만들고 `_all_tools_cache = None`이다. 설정이 있으면 초기화 메시지를 스트리밍하고, 없으면 오류 로그만 남긴다(예외 없음). `headers`·`query_domains`는 읽지 않는다. | 코드 확인 |
| R-16 | `search(max_results=10)`(동기, C-14) | `mcp_configs`가 비면 `[]`. 아니면 `asyncio.get_running_loop()`가 성공하는 경우(=`_execute_mcp_research`처럼 코루틴 안에서 부른 경우)에는 새 스레드에서 새 이벤트 루프를 만들어 `search_async`를 돌리고 `future.result(timeout=300)`로 기다린다. 이 동안 호출한 루프의 다른 작업은 멈춘다. 스레드 끝에서는 남은 태스크를 취소하고(최대 5초 대기) 0.1초·0.2초 쉬며 가비지 컬렉션 후 루프를 닫는다. 300초를 넘기면 `TimeoutError`는 나지만 `with ThreadPoolExecutor`가 스레드 종료를 기다리므로 실제로는 작업이 끝난 뒤에야 반환하고 결과는 `[]`가 된다. 실행 중인 루프가 없으면 `asyncio.run(search_async(...))`. 어느 경로든 모든 `Exception`은 로그와 동기 스트리밍 후 `[]`다. | 실행 확인(타임아웃은 300을 0.3으로 치환해 확인) |
| R-17 | `search_async(max_results)`(C-13) | ① 설정 없음: 오류 이벤트 후 `[]`(`finally`의 정리도 없다). ② `_get_all_tools()`로 도구를 읽는다(R-18). 없으면 경고 후 `[]`. ③ `MCPToolSelector.select_relevant_tools(query, all_tools, max_tools=3)`(R-20). 없으면 경고 후 `[]`. ④ `MCPResearchSkill.conduct_research_with_tools(query, selected)`(R-22). ⑤ 결과가 `max_results`보다 많으면 앞에서부터 `max_results`개만 남긴다(도구 결과 뒤에 붙는 LLM Analysis 항목이 먼저 잘릴 수 있다). ⑥ 결과 수와 본문 글자 수 이벤트. ②~⑥에서 어떤 `Exception`이든 오류 이벤트와 `[]`다. ②~⑥은 어느 경우든(정상·조기 반환·예외) 끝에 `finally`에서 `client_manager.close_client()`를 부르고 그 예외는 삼킨다. 단계 이벤트 "Stage 1/2/3"이 각 단계 시작에 나간다. | 실행 확인 |
| R-18 | 클라이언트 수명(C-02) | `MCPClientManager`는 `_client_lock` 아래에서만 클라이언트를 만들고 지운다. `get_or_create_client`: 이미 있으면 그대로 반환. 어댑터가 없으면 `None`(오류 로그). `mcp_configs`가 비면 `None`. 아니면 R-19로 변환한 맵으로 `MultiServerMCPClient(맵)`을 만들어 저장하고 반환하며, 생성 예외는 `None`. `get_all_tools`: 클라이언트가 없으면 `[]`, 있으면 `await client.get_tools()`, 결과가 비면 경고 후 `[]`, 예외는 `[]`. `close_client`: 참조만 `None`으로 되돌린다(어댑터의 닫기 호출 없음. 코드 주석이 어댑터 0.1.0에 닫기·컨텍스트 매니저가 없다고 설명한다). `MCPRetriever`가 실행마다 새로 만들어지므로 연결·도구 목록은 실행 사이에 재사용되지 않는다. `_all_tools_cache`는 한 인스턴스 안에서만 의미가 있고 인스턴스당 `search_async`는 한 번뿐이다. 서버 프로세스를 언제 띄우고 닫는지는 어댑터의 몫이다. | 실행 확인(가짜 클라이언트) |
| R-19 | 설정 변환 `convert_configs_to_langchain_format`(C-01) | 변환표(1.3)와 C-01의 코드가 규칙이다. 검증은 하나뿐이다: dict가 아닌 항목은 경고 후 건너뛴다(기본 이름의 번호는 건너뛴 항목을 포함한 원래 목록 위치를 따른다). 그 밖의 값(빈 `command`, 모르는 `connection_type`, `args=None`, 형식이 틀린 URL)은 걸러내지 않고 그대로 넘겨서 어댑터 쪽 호출 단계(`get_tools`)에서 실패하면 R-18에 따라 빈 도구 목록이 된다. `connection_type="sse"`는 URL이 있어도 `url` 없이 `transport`만 넘어가므로 사실상 SSE는 쓸 수 없다(`http(s)` URL은 항상 `streamable_http`). `tool_name`은 읽지 않는다. 변환 결과의 `token` 키를 어댑터가 어떻게 해석하는지는 확인하지 못했다. | 실행 확인(소스 exec) |

**도구 자동 선택과 실행**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 도구 선택 `select_relevant_tools(query, all_tools, max_tools=3)`(C-15~C-18) | 도구가 없으면 LLM 없이 `[]`. `max_tools = min(3, 도구 수)`이고 도구가 아무리 적어도 LLM은 부른다. 입력: 도구마다 `{index(목록 위치), name, description(없으면 "No description available")}` JSON과 질문을 담은 영어 프롬프트(C-18: 정확히 `max_tools`개를 고르라고 요구, 응답 형식은 `{"selected_tools": [{index, name, relevance_score, reason}], "selection_reasoning": ...}`). 호출: STRATEGIC 모델, `temperature=0.0`, user 메시지 하나, `cost_callback=researcher.add_costs`(비용이 기록되는 유일한 MCP LLM 호출). 응답은 `json_repair.loads`로 파싱한다. 출력: `selected_tools`의 각 항목(dict만)에서 `0 <= index < 도구 수`인 도구를 LLM이 준 순서대로 모은다. 중복 index를 거르지 않고, `max_tools`를 넘겨도 자르지 않고, `name`은 index와 대조하지 않는다. 폴백(R-21)으로 가는 경우: LLM 호출 실패·빈 응답, 파싱 실패, 응답이 객체가 아님, 유효한 선택이 0개, 그리고 처리 중 어떤 예외든(예: `index`가 `"1"`·`1.0`처럼 정수가 아니면 `TypeError`가 나서 이미 고른 도구도 버리고 전체를 폴백으로 대체). `MCP_AUTO_TOOL_SELECTION`은 읽지 않는다(R-24). | 실행 확인(응답은 가짜, 파서는 json.loads로 대체) |
| R-21 | 폴백 `_fallback_tool_selection(all_tools, max_tools)`(C-17) | 이름에 패턴(`search, get, read, fetch, find, list, query, lookup, retrieve, browse, view, show, describe`)이 들어 있으면 패턴마다 +3, 설명에 들어 있으면 패턴마다 +1로 점수를 매겨 점수가 0보다 큰 도구만 점수 내림차순(동점은 원래 순서)으로 `max_tools`개 고른다. 하나도 안 맞으면 `[]`이고 그 실행은 "No relevant tools selected"로 끝난다(R-17). | 실행 확인 |
| R-22 | 도구 호출 `conduct_research_with_tools(query, selected_tools)`(C-19, C-20) | 도구가 없으면 `[]`. `GenericLLMProvider.from_provider(STRATEGIC 제공자, model=STRATEGIC 모델, **llm_kwargs)`로 모델을 만들어 `bind_tools(selected_tools)`하고 도구 이름 목록이 든 연구 프롬프트(C-19)를 user 메시지로 `ainvoke`를 **정확히 한 번** 부른다. 도구 결과를 LLM에 되돌려 주는 2번째 호출은 없다. 이 호출은 비용 콜백이 없어 `research_costs`에 안 잡힌다. 응답의 `tool_calls`를 순서대로 하나씩(병렬 아님) 처리한다: 이름으로 선택된 도구를 찾고(없으면 경고 후 건너뜀), `ainvoke(args)`(없으면 `invoke`, 그것도 없으면 호출 가능 객체) 실행하고, 결과가 거짓값(빈 문자열·빈 리스트·`None`)이면 경고 후 건너뛰고, 아니면 R-23으로 정규화해 결과에 더한다. 한 도구의 예외는 로그만 남기고 다음 호출로 간다. 마지막으로 `response.content`가 거짓이 아니면 `{title: "LLM Analysis: <질문>", href: "mcp://llm_analysis", body: response.content}`를 맨 끝에 더한다(`content`를 문자열로 바꾸지 않는다). 도구 호출이 없어도 텍스트 답이 있으면 이 항목 하나가 결과가 된다. 모델 생성·`bind_tools`·`ainvoke`의 예외(예: 도구 바인딩 미지원)는 바깥 `try`가 받아 `[]`다. | 실행 확인(LLM·도구는 가짜) |
| R-23 | 도구 결과 정규화 `_process_tool_result(tool_name, result)`(C-21) | 코드가 규칙이다. 요약: ① dict에 `structured_content` 또는 `content` 키가 있으면 MCP 래퍼로 본다. `structured_content.results`가 리스트면 dict 항목마다 한 건(`title`, `href`←`href`/`url`/`mcp://<도구>/<i>`, `body`←`body`/`content`/`str(항목)`), 리스트가 아닌 dict면 통째로 한 건. 하나도 못 만들면 `content`로 폴백한다: 리스트면 텍스트 파트를 `"\n\n"`로 이어 한 건(`title="Result from <도구>"`, `href="mcp://<도구>"`), 문자열이면 그대로, 그 밖이면 `str(result)`. ② 리스트면 dict 항목만 처리하고(비-dict는 버림) `title`과 `body`/`content`가 있으면 그 값으로, 없으면 `str(항목)`을 본문으로 일반 제목·`mcp://<도구>/<i>`로 만든다. ③ 그 밖의 dict는 한 건. ④ 나머지 타입은 `str(result)` 한 건. 처리 중 예외는 `str(result)` 한 건으로 대체. | 실행 확인 |

**설정 키의 효과**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | `MCP_SERVERS`, `MCP_AUTO_TOOL_SELECTION`, `MCP_ALLOWED_ROOT_PATHS`, `MCP_USE_LLM_ARGS`를 설정 | 동작이 바뀌지 않는다. 네 키를 읽는 코드가 이 레포의 `*.py`에 없다(`Config.get_mcp_server_config`는 `MCP_SERVERS`를 이름으로 찾지만 호출처가 테스트뿐이고, 결과가 `mcp_configs`로 가지 않는다). 따라서 `MCP_ALLOWED_ROOT_PATHS`로 MCP 서버의 파일 접근을 제한하는 코드는 이 레포에 없고(서버가 알아서 제한해야 한다), `MCP_AUTO_TOOL_SELECTION=false`여도 R-20의 LLM 도구 선택은 그대로 일어난다. MCP 서버 설정을 주는 방법은 `mcp_configs` 인자뿐이다. `MCP_STRATEGY`만 R-04에서 읽힌다. | 코드 확인(`git grep` 전수) |

**실패 처리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | MCP 서버 접속·도구 로드·도구 선택·LLM 호출·도구 실행·타임아웃 중 어디서 실패하든 | 그 MCP 실행의 반환이 `[]`이거나 일부 도구 결과만 남고, 예외는 `MCPRetriever.search` 밖으로 나오지 않는다. 결과: `fast`는 빈 리스트가 캐시되어(R-06) 다시 시도하지 않고 웹 결과만 쓰며, `deep`은 서브쿼리별로 따로 실패해 웹 결과만 남는다. 도구 호출이 일부만 실패하면 성공한 결과와 LLM Analysis 항목은 유지된다(R-22). 서버 하나가 안 뜨는 경우 다른 서버의 도구까지 잃는지는 어댑터 `get_tools()`의 동작에 달려 있고 이 코드는 `get_tools()` 예외를 한꺼번에 `[]`로 바꾼다(R-18). 어떤 경우도 `conduct_research`에 예외가 전파되지 않는다(R-27의 서브쿼리 손실은 예외가 아니라 빈 결과). | 실행 확인(가짜 MCP·도구) |

**결합과 결합 실패, 중복, 스트리밍, 경계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | 서브쿼리 결과 결합 `_combine_mcp_and_web_context(mcp_context, web_context, sub_query)`(C-11) | 부분을 이 순서로 모은다: ① `web_context`가 공백만이 아니면 `strip()`한 웹 컨텍스트. ② MCP 컨텍스트 항목 중 `content`(`strip()` 후)가 비어 있지 않은 것마다 `"<content.strip()>\n\n*Source: <title> (<url>)*"`. `url`이 비었거나 `mcp://llm_analysis`면 `"*Source: <title>*"`(괄호 없음). `title` 키가 없을 때만 `MCP Result <번호>`이고, 키가 있는데 비면 제목 없이 `*Source:  (<url>)*`가 된다. 항목들은 `"\n\n---\n\n"`로 이어 한 덩어리로 만든다. 모은 부분들을 `"\n\n"`으로 이어 반환하고 하나도 없으면 `""`. MCP 항목은 컨텍스트 선별을 거치지 않고 길이를 줄이지 않는다. | 실행 확인 |
| R-27 | MCP 컨텍스트 항목의 `content`가 문자열이 아님(예: LLM Analysis의 `response.content`가 블록 리스트) | R-26의 `content.strip()`이 `AttributeError`를 낸다. `_process_sub_query`의 바깥 `except`가 받아 그 서브쿼리 전체를 `""`로 만든다. 웹 컨텍스트가 있었어도 함께 사라지고 이벤트 `subquery_error`가 나간다. `fast`에서는 캐시된 같은 항목이 모든 서브쿼리에 들어가므로 모든 서브쿼리가 `""`가 된다. 모델 제공자가 도구 호출과 함께 리스트 형태의 `content`를 주는지는 확인하지 못했다. | 실행 확인(조건부: 리스트 본문을 가진 항목을 직접 만들어 확인), 제공자 동작은 미확인 |
| R-28 | `fast`에서 서브쿼리가 여러 개 | 모든 서브쿼리가 같은 캐시 항목을 받아 서브쿼리마다 같은 MCP 본문이 결과에 들어간다. 파이프라인이 서브쿼리 결과를 `" "`로 이어 붙이므로 최종 컨텍스트에 같은 MCP 본문이 서브쿼리 수(원 질문 포함)만큼 반복된다. 중복을 거르는 코드는 없다. | 실행 확인(서브쿼리 3개에서 3번 반복) |
| R-29 | 스트리밍 `MCPStreamer`(C-22) | `websocket`이 있을 때만 `stream_output("logs", "mcp_retriever", 메시지, websocket, metadata=data)`를 보내고, 전송 예외는 로그만 남기고 삼킨다. `websocket`이 없으면 로거에만 쓴다. `verbose`를 보지 않는다. 메시지(앞에 이모지): 초기화·서버 수, `Stage 1: Getting all available MCP tools`, `Stage 2: Selecting most relevant tools`, `Stage 3: Conducting research with selected tools`, `Loaded N total tools from MCP servers`, 경고(`No MCP tools available, skipping MCP research` 등), `MCP research completed: N results obtained (X chars)`, 오류. 동기 버전 `stream_log_sync`는 실행 중인 루프가 있으면 태스크로 예약하고 없으면 그 자리에서 실행하며, 루프를 못 얻으면 로그만 남긴다. `stream_tool_selection`·`stream_tool_execution`·`stream_info`·`stream_stage_complete`는 정의만 있고 호출처가 없다. `MCPRetriever.search`가 새 스레드·새 루프에서 `search_async`를 돌리므로 그 안의 이벤트는 websocket을 만든 루프와 다른 루프에서 전송을 시도한다. 실제로 전달되는지는 확인하지 못했다. conductor의 이벤트 이름은 1.3에 있다. | 코드 확인(전달 여부는 미확인) |
| R-30 | MCP가 쓰이는 경로 | `_get_context_by_web_search`가 실행되는 경로에서만 쓰인다: `report_source`가 web, local, hybrid, azure, langchain_documents이거나 `source_urls`에 `complement_source_urls`를 켠 경우의 보충 웹 검색. `source_urls`만 준 경로와 `langchain_vectorstore` 경로에서는 MCP 사전 실행과 서브쿼리 결합이 없다(후자는 계획 단계의 초기 검색이 MCP일 수 있다). 상세 보고서 소제목 연구자와 Deep Research의 하위 연구자는 부모의 `mcp_configs`와 `mcp_strategy`를 받아 새 `GPTResearcher`를 만들므로(R-01을 다시 거침) 각자 사전 실행과 캐시를 가진다. | 코드 확인 |
| R-31 | 서버 입구의 경계 | WebSocket 시작 메시지의 `mcp_enabled`(기본 `False`), `mcp_strategy`(기본 `"fast"`), `mcp_configs`(기본 `[]`)가 `run_agent`로 가고, 보고서 타입 객체에 `mcp_configs if mcp_enabled else None`, `mcp_strategy if mcp_enabled else None`로 전달된다. `mcp_enabled`가 거짓이면 MCP는 켜지지 않는다. | 코드 확인 |

R-08 횟수표 (`MCPRetriever.search` 호출 횟수. 굵은 칸은 실행 확인):

| 구성 | `disabled` | `fast` | `deep` |
|---|---|---|---|
| 웹 retriever + MCP(MCP가 첫 번째가 아님), 처리 대상 N+1개 | **0** | **1**(사전 실행, 원 질문) | **N+1**(소제목 연구자는 N) |
| 위 구성에서 직접 Tavily + Tavily MCP | 0 | **1**(쓰이지 않음) | **0** |
| MCP 단독(`RETRIEVER=mcp`), 처리 대상 `[Q, Q]` | **1**(초기 검색, 결과 버림) | **2**(사전 실행 1 + 초기 검색 1) | **3**(초기 검색 1 + 서브쿼리 2) |
| MCP가 첫 번째, 웹 retriever도 있음 | 1 | **2** | 1 + (N+1)(코드 읽기) |

- 불변식:
  - `MCPRetriever.search`는 `Exception`을 밖으로 내지 않고 항상 list를 돌려준다(R-16). `KeyboardInterrupt`·`CancelledError` 같은 `BaseException`은 막지 않는다.
  - `fast`에서 `_mcp_results_cache`는 `None`에서 리스트로 한 번 바뀌고 이후 바뀌지 않는다(R-09). 한 `ResearchConductor`가 `fast`에서 부르는 `MCPRetriever.search`는 사전 실행 1회와 `retrievers[0]`이 MCP일 때의 초기 검색 1회뿐이다.
  - MCP 결과는 어떤 경로로도 `visited_urls`·`research_sources`에 들어가지 않는다.
- 미결정: 없음
- 확인 한계:
  - 실제 MCP 서버·langchain-mcp-adapters·LLM·네트워크를 쓰지 않았고 어댑터는 이 환경에 설치돼 있지 않다. 그래서 어댑터 쪽 동작은 코드가 그렇게 가정했다는 증거까지만 있다: `transport` 값 `http`/`sse`가 받아들여지는지, `token` 키를 읽는지, `get_tools()`가 서버 하나의 실패로 전체를 실패시키는지, 도구 호출 때마다 세션을 새로 여는지(그래서 서버가 몇 번 뜨는지), `tool.ainvoke(args)`의 반환 형태(문자열인지 블록 리스트인지)가 그렇다. 이 스펙의 계약은 변환 결과 맵과 `get_tools()` 호출까지다.
  - 실행 확인은 소스 줄을 그대로 exec한 것이다. 가짜로 바꾼 것: MCP 서버·`MultiServerMCPClient`, LLM 응답과 `GenericLLMProvider`, 도구 객체, 검색 retriever 클래스(Tavily·MCP), 스크랩, 컨텍스트 선별, 서브쿼리 계획 LLM, `stream_output`, `json_repair`(→`json.loads`라서 코드 펜스가 붙은 JSON 복구는 실행으로 확인하지 못함). 가짜 MCP retriever의 `search`는 동기 함수이고 실제 `search`의 스레드·루프 동작은 `MCPRetriever.search` 소스를 따로 exec해 확인했다.
  - 모델 제공자가 도구 호출과 함께 문자열이 아닌 `content`를 주는지(R-27의 조건), `bind_tools`를 지원하지 않는 제공자에서 실제로 어떤 예외가 나는지는 확인하지 못했다.
  - MCPStreamer 이벤트가 다른 스레드의 루프에서 실제 websocket으로 전달되는지는 확인하지 못했다.

### 1.5 필수 코드 참조

라이선스: overview 1절을 따른다. Apache License 2.0(`LICENSE`)이고 `pyproject.toml`은 MIT로 적어 표기가 어긋난다. 이 스펙은 코드를 복사하지 않고 줄 범위만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/mcp/client.py:41-116` `MCPClientManager.convert_configs_to_langchain_format` | `mcp_configs` → 어댑터 맵 변환 전체(스킴 판별, `transport`·`url`·`headers`·`command`·`args`·`env`·`token`, 건너뛰기, 기본 이름). 짧고 자기완결적이라 그대로 따른다. | R-19 |
| C-02 | `gpt_researcher/mcp/client.py:6-39`, `:118-192` `MCPClientManager.get_or_create_client`·`close_client`·`get_all_tools` | 어댑터 import 가드(`HAS_MCP_ADAPTERS`), 잠금, 생성·캐시·참조 해제, 예외를 삼키는 방식 | R-03, R-18 |
| C-03 | `gpt_researcher/agent.py:217-281` `GPTResearcher._resolve_mcp_strategy` | 전략 우선순위와 옛 이름·`mcp_max_iterations` 변환. 호출은 `agent.py:201`(생성자 마지막) | R-04 |
| C-04 | `gpt_researcher/agent.py:171-176`, `:295-321` `_process_mcp_configs` | `mcp_configs` 저장과 `cfg.retrievers`에 `"mcp"` 덧붙이기(환경변수 미사용), `get_retrievers` 앞 순서 | R-01, R-02 |
| C-05 | `gpt_researcher/skills/researcher.py:311-362` `_get_context_by_web_search` 앞부분 | 사전 실행: MCP 클래스 추출, 잠금, 전략별 분기, 캐시 대입 | R-06, R-09 |
| C-06 | `gpt_researcher/skills/researcher.py:410-434` `_get_mcp_strategy` | 인스턴스 → 설정 → `"fast"` 순서 | R-05 |
| C-07 | `gpt_researcher/skills/researcher.py:536-603`, `:615-616`, `:654-663` `_process_sub_query` | MCP/비MCP 분리, Tavily 건너뛰기 호출, 전략별 MCP 컨텍스트 결정, 결합 호출, 예외 → `""` | R-07, R-12, R-27 |
| C-08 | `gpt_researcher/skills/researcher.py:436-490` `_execute_mcp_research_for_queries` | 컨텍스트 항목 만들기(`body` 빈 항목 제외), 순차 실행, 예외 격리, 이벤트 | R-13 |
| C-09 | `gpt_researcher/skills/researcher.py:492-517` `_tavily_mcp_redundant_with_direct` | Tavily MCP 중복 판정식 | R-12 |
| C-10 | `gpt_researcher/skills/researcher.py:665-737` `_execute_mcp_research` | `MCPRetriever` 생성 인자, 동기 `search` 호출과 `max_results`, 이벤트, 예외 → `[]` | R-14 |
| C-11 | `gpt_researcher/skills/researcher.py:739-790` `_combine_mcp_and_web_context` | 웹 → MCP 순서, 인용 문자열, 구분자, 빈 항목 처리 | R-26, R-27 |
| C-12 | `gpt_researcher/retrievers/mcp/retriever.py:44-114` `MCPRetriever.__init__`·`_get_mcp_configs`·`_get_config` | 생성자 인자, `researcher`에서 설정 꺼내기, 하위 컴포넌트 생성, 설정 없음 처리 | R-15 |
| C-13 | `gpt_researcher/retrievers/mcp/retriever.py:116-198`, `:300-324` `search_async`·`_get_all_tools` | 3단계 흐름, `max_tools=3`, 결과 자르기, `finally` 정리, 도구 목록 캐시 | R-17, R-18 |
| C-14 | `gpt_researcher/retrievers/mcp/retriever.py:201-298` `MCPRetriever.search` | 동기 래퍼: 루프 감지, 스레드·새 루프, 300초, 정리 절차, 예외 → `[]` | R-16 |
| C-15 | `gpt_researcher/mcp/tool_selector.py:37-125` `select_relevant_tools` | 도구 정보 구성, 파싱, 선택 검증, 폴백 조건 | R-20 |
| C-16 | `gpt_researcher/mcp/tool_selector.py:127-159` `_call_llm_for_tool_selection` | 도구 선택 LLM 호출 인자(STRATEGIC, `temperature=0.0`, `cost_callback`), 실패 시 빈 문자열 | R-20 |
| C-17 | `gpt_researcher/mcp/tool_selector.py:161-202` `_fallback_tool_selection` | 패턴 목록과 점수 규칙 | R-21 |
| C-18 | `gpt_researcher/prompts.py:39-83` `PromptFamily.generate_mcp_tool_selection_prompt` | 도구 선택 프롬프트 전문과 응답 JSON 형식 | R-20 |
| C-19 | `gpt_researcher/prompts.py:85-118` `PromptFamily.generate_mcp_research_prompt` | 도구 호출 프롬프트 전문 | R-22 |
| C-20 | `gpt_researcher/mcp/research.py:34-156` `conduct_research_with_tools` | LLM 한 번 호출, 도구 순차 실행과 폴백 호출 방식, LLM Analysis 항목, 예외 처리 | R-22 |
| C-21 | `gpt_researcher/mcp/research.py:158-271` `_process_tool_result` | 도구 결과 정규화 분기 전체 | R-23 |
| C-22 | `gpt_researcher/mcp/streaming.py:13-101` `MCPStreamer` | 이벤트 이름·전송 방식·예외 삼킴·메시지 문구 | R-29 |
| C-23 | `gpt_researcher/actions/query_processing.py:44-81` `get_search_results` | `retrievers[0]`이 MCP일 때 `researcher`를 넘기는 생성과 `to_thread` 호출 | R-10 |
| C-24 | `gpt_researcher/actions/query_processing.py:185-202` `plan_research_outline`의 MCP 분기, `skills/researcher.py:80-92` | MCP 단독이면 LLM 없이 `[query]` | R-10 |
| C-25 | `gpt_researcher/skills/researcher.py:836-839` `_get_context_from_initial_results` | `retrievers[0]`이 MCP이면 초기 컨텍스트 `""` | R-10 |
| C-26 | `gpt_researcher/skills/researcher.py:861-865` `_search_relevant_source_urls` | MCP 클래스를 URL 수집에서 건너뜀 | R-11 |
| C-27 | `gpt_researcher/config/variables/default.py:44-48`, `config/variables/base.py:41-45` | 네 MCP 설정 키의 기본값과 타입(읽는 코드가 없음) | R-24 |
| C-28 | `gpt_researcher/mcp/__init__.py:15-43`, `retrievers/mcp/__init__.py:11-32`, `retrievers/__init__.py:18`, `actions/retriever.py:118-121` | 미설치 시 `HAS_MCP_ADAPTERS=False`·`MCPRetriever=None`과 `get_retriever("mcp")` | R-03 |

### 1.6 수락 사례

출처: 모두 구현에서 도출했다. 원본 테스트는 열지 않았고(파일 이름만 확인, 2.1) 아래 사례는 `artifacts/gpt-researcher/mcp-demos/run_mcp_demos.py`로 실행했다. 가짜로 바꾼 부분은 1.4의 확인 한계에 적었고, 그래서 이 사례들은 실제 MCP 서버·LLM·어댑터·웹 검색의 동작을 검증하지 않는다. 사례 중 시간이 결과에 영향을 주는 것은 없다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `cfg.retrievers=["tavily"]`, `mcp_configs=[{"command":"x"}]` / `["mcp","tavily"]` / 문자열 `"tavily, exa"` / `[]` | `["tavily","mcp"]` / 그대로 / `["tavily","exa","mcp"]` / `["mcp"]`. `mcp_configs=[]`는 변경 없음. |
| T-02 | R-03 | 어댑터 미설치(`MCPRetriever=None`), `cfg.retrievers=["tavily","mcp"]` | `get_retrievers`가 `[Tavily, Tavily]`. 헤더 `{"retrievers":"tavily"}`면 `[Tavily]`. |
| T-03 | R-04 | `(mcp_strategy, mcp_max_iterations, cfg.mcp_strategy)` = `("optimized",None,-)` / `("bogus",None,"deep")` / `(None,0,-)` / `(None,-1,-)` / `(None,7,-)` / `("deep",0,-)` / `(None,None,"comprehensive")` / `(None,None,"bogus")` | `fast` / `fast` / `disabled` / `deep` / `fast` / `deep` / `deep` / `fast` |
| T-04 | R-06, R-07, R-08 | `[Tavily, MCP]`, `fast`, 계획이 `[s1,s2]`, `research_report`, MCP 가짜가 항목 2건(도구 결과 1, LLM Analysis 1) | MCP는 `"Q"` 한 번만 실행. 서브쿼리 `s1,s2,Q` 모두 캐시 재사용(이벤트 `mcp_cache_reuse` 3번). 캐시 항목은 `T:Q`와 `LLM Analysis: Q` 두 개. |
| T-05 | R-07, R-08 | 같은 구성, `deep` / `deep`+`subtopic_report` | MCP 실행 질문 `s1,s2,Q`(순서 무관 3회) / `s1,s2`(2회). 캐시 없음. |
| T-06 | R-06, R-08 | 같은 구성, `disabled` | MCP 실행 0회, 결과에 `WEB[s1]`이 있고 MCP 본문 없음, 이벤트 `mcp_disabled`. |
| T-07 | R-10, R-08 | `[MCP]` 단독, `fast` / `deep` / `disabled`, 계획 LLM 가짜(호출되지 않아야 함) | 실행 질문 `[Q,Q]` / `[Q,Q,Q]` / `[Q]`. `disabled`의 결과에 MCP 본문 없음. `[MCP, Tavily]`+`fast`는 `[Q,Q]`. |
| T-08 | R-12, R-06 | `[Tavily, MCP]`, `mcp_configs=[{"name":"tavily","command":"npx","args":["-y","tavily-mcp@0.1.2"]}]`, `fast` / `deep` | `fast`: MCP 1회 실행(사전 실행)·결과는 안 쓰임(`mcp body` 없음, 이벤트 `mcp_tavily_deduped` 3번). `deep`: 0회. |
| T-09 | R-12 | 판정 입력: `args`가 문자열 `"-y tavily-mcp"` / `connection_url`만 tavily / 서버 둘 중 하나가 tavily 아님 / non-MCP가 Exa뿐 / 설정에 비-dict / 설정 `[]` | 모두 "중복 아님". 반면 `name:"tavily-mcp"`, `args` 리스트에 tavily, `command:"/opt/tavily-mcp"`는 "중복". |
| T-10 | R-09 | `fast`, 같은 conductor에서 `_get_context_by_web_search`를 동시에 두 번 / 잠금을 no-op으로 바꾼 대조 / `deep` | MCP 1회 / 2회 / 6회(패스당 3회). |
| T-11 | R-09 | `fast`, 같은 conductor에서 질문 `"Q"` 뒤 `"OTHER"` | MCP는 `"Q"` 한 번뿐. 두 번째 결과에 `mcp body for Q`가 있고 `OTHER`용 본문은 없다. |
| T-12 | R-09, R-25 | `fast`, MCP가 빈 리스트를 돌려줌 | `_mcp_results_cache == []`(None 아님), 재실행 없음, 웹 결과만 반환. |
| T-13 | R-19 | `[{"name":"fs","command":"npx","args":"-y @x/server /tmp","env":{"K":"v"}}]` | `{"fs":{"transport":"stdio","command":"npx","args":["-y","@x/server","/tmp"],"env":{"K":"v"}}}` |
| T-14 | R-19 | `["bad", {"command":"py"}, 7]` | 키 `mcp_server_2`만 남는다(건너뛴 항목도 번호에 포함). |
| T-15 | R-19 | `{"name":"a","connection_url":"https://h/mcp","connection_type":"sse","connection_token":"tk","connection_headers":{"X":"1"}}` | `{"transport":"streamable_http","url":"https://h/mcp","headers":{"X":"1"},"token":"tk"}`. `"WSS://h/ws"`는 `websocket`, `"tcp://h:1"`+`websocket`은 `url` 포함 `websocket`, `"tcp://h:1"`만 있으면 `{"transport":"stdio"}`, URL `"h:1/sse"`에 `connection_type:"sse"`는 `{"transport":"sse"}`(url 없음). |
| T-16 | R-19 | `{"name":"a","command":"c","connection_token":"tk","connection_headers":{"X":"1"},"tool_name":"search"}` / 같은 이름 두 항목 / `args=None` | `{"transport":"stdio","command":"c","args":[],"token":"tk"}`(headers·tool_name 없음) / 뒤 항목만 남음 / `args`가 `None` 그대로. |
| T-17 | R-20 | 도구 5개, LLM 응답이 `index` 1, 0 / 같은 index 0 두 번과 1, 2 / 범위 밖 9만 / `{"index":1.0}` 포함 / `"1"` 포함 / JSON 배열 / 빈 응답 | 순서대로 `[read_file, web_search]` / 중복·초과 그대로 4개 / 폴백 / 폴백 / 폴백 / 폴백 / 폴백. 프롬프트에 `EXACTLY 3`, `No description available`이 있다. 도구 2개면 `EXACTLY 2`이고 LLM은 호출된다. 도구 0개면 LLM 호출 없음. |
| T-18 | R-21 | 폴백 입력: 이름·설명이 패턴에 안 맞는 도구 둘 / `misc("can search and fetch")`, `search_get`, `read("read it")` | `[]` / `[search_get, read, misc]` |
| T-19 | R-22 | 선택 도구 3개, 응답 `tool_calls` = `web_search`(결과: dict 하나와 문자열 하나가 든 리스트), `read_file`(예외), 없는 도구, `get`(결과 `""`), `content="my analysis"` | LLM 호출 1회. 결과 제목: 도구 결과 2건 뒤에 `LLM Analysis: Q?`. 실패·없는 도구·빈 결과는 건너뜀. 도구는 LLM이 준 `args`로 불림. `tool_calls` 없음+텍스트만이면 Analysis 한 건, 텍스트도 비면 `[]`, `ainvoke` 예외면 `[]`, 도구 0개면 LLM 호출 없이 `[]`. |
| T-20 | R-23 | 결과가 `{"structured_content":{"results":[{"title":"T","url":"u","content":"c"},"skip"]}}` / `{"structured_content":{"results":[]},"content":[{"type":"text","text":"a"},{"text":5},{"k":1},"z"]}` / `["a","b"]` / `"text"` | `[{"title":"T","href":"u","body":"c"}]` / 한 건: `title="Result from t"`, `href="mcp://t"`, `body="a\n\n5\n\n{'k': 1}\n\nz"` / `[]` / `[{"title":"Result from t","href":"mcp://t","body":"text"}]`. |
| T-21 | R-16 | 코루틴 안에서 `search()` 호출(안의 `search_async`가 0.6초 걸림), 같은 시간 동안 50ms 간격으로 올라가는 ticker 태스크 | 호출이 끝날 때까지 ticker가 0번 돈다(루프가 막힘). 루프 밖에서 부르면 `asyncio.run` 경로로 같은 결과. `timeout=300`을 0.3으로 바꾼 변형에서 `search_async`가 1초 걸리면 반환까지 1초 이상 걸리고 결과는 `[]`. |
| T-22 | R-17 | 가짜 도구 2개, 선택 1개, 연구 결과 7건, `search_async(5)` | 5건 반환(앞 5건), 선택 호출의 `max_tools`는 3, `close_client` 1회. 도구 0개/선택 0개/설정 없음은 `[]`이고(설정 없음만 `close_client` 호출 없음), 선택 예외·도구 로드 예외도 `[]`, `close_client` 예외는 삼킴. |
| T-23 | R-18 | 어댑터가 있다고 가정한 가짜 클라이언트로 `get_or_create_client` 두 번 / `get_tools` 예외 / `close_client` 뒤 다시 / 생성자 예외 / 미설치 / 설정 없음 | 같은 객체·생성 1회 / `get_all_tools`가 `[]` / 새 클라이언트(생성 2회) / `None` / `None`과 `[]` / `None`. |
| T-24 | R-14, R-25 | `deep`, MCP `search`가 예외 | 서브쿼리마다 이벤트 `mcp_research_error`, 결과에는 웹 컨텍스트만 남는다. |
| T-25 | R-26 | `mcp_context`: 본문 `"  c1  "`(URL 있음), URL이 `mcp://llm_analysis`, URL 빈 문자열, 공백뿐인 본문, 제목이 `""`이고 URL이 `mcp://tool/1`인 항목, `web_context="  web  "` | `web\n\nc1\n\n*Source: T1 (https://u)*\n\n---\n\nc2\n\n*Source: LLM Analysis*\n\n---\n\nc3\n\n*Source: T3*\n\n---\n\nc5\n\n*Source:  (mcp://tool/1)*`. 웹이 없으면 MCP만, 둘 다 없으면 `""`. |
| T-26 | R-27 | 캐시에 `content`가 `[{"type":"text","text":"blocks"}]`인 항목이 있고 웹 컨텍스트도 있는 서브쿼리 | `_process_sub_query`가 `""`를 반환한다(웹 컨텍스트 소실). |
| T-27 | R-28 | T-04와 같은 입력 | 결과 문자열에 `mcp body for Q`가 3번 나온다. |
| T-28 | R-05 | `mcp_strategy=None`, `cfg.mcp_strategy="foo"`, `[Tavily, MCP]`, 처리 대상 3개 | MCP 실행 질문 `["Q","s1","s2","Q"]`(사전 실행 1 + 서브쿼리 3). `cfg.mcp_strategy="deep"`면 `_get_mcp_strategy()`는 `"deep"`, `researcher.mcp_strategy="disabled"`가 있으면 `"disabled"`. |
| T-29 | R-24 | `MCP_AUTO_TOOL_SELECTION=false`·`MCP_ALLOWED_ROOT_PATHS=["/srv"]`로 `Config`를 만들고 `mcp_configs`로 MCP 실행 | 도구 선택 LLM 호출·실행 경로가 값이 기본일 때와 같다(키를 읽는 코드가 없다). 코드 읽기만 했고 실행하지 않았다. |
| T-30 | R-02, R-31 | 헤더 `{"retrievers":"tavily"}` + `mcp_configs` / `mcp_enabled=False` + `mcp_configs` | MCP 클래스가 목록에 없고 MCP가 실행되지 않는다 / `GPTResearcher`에 `mcp_configs=None`이 가서 MCP가 꺼진다. 앞의 것은 `get_retrievers`를 exec해 확인했고 뒤의 것은 코드 읽기다. |

## 2부. 근거

### 2.1 요구사항별 근거 지도

실행 기록: [run_mcp_demos.py](../../../artifacts/gpt-researcher/mcp-demos/run_mcp_demos.py)(소스 줄을 exec하는 하네스, 대체물 목록은 파일 머리말과 1.4 확인 한계)와 그 출력 [output-2026-10-22.txt](../../../artifacts/gpt-researcher/mcp-demos/output-2026-10-22.txt)(133개 확인 모두 PASS). 아래 "실행 A~J"는 출력의 섹션 이름이다(A 미설치·클라이언트, B 변환, C 전략, D retrievers, E 도구 선택, F 도구 실행·정규화, G `MCPRetriever`, H conductor, I Tavily 판정, J 결합).

문서와 구현의 차이(구현을 사실로 썼다):
- 공식 문서(`docs/docs/gpt-researcher/retrievers/mcp-configs.mdx`)는 "MCP를 쓰려면 `RETRIEVER`를 반드시 설정해야 한다"고 쓰지만 구현은 `mcp_configs`가 truthy면 `cfg.retrievers`에 `"mcp"`를 스스로 덧붙인다(R-01, `agent.py:307-318`). 단 헤더가 retriever를 주면 덧붙인 것이 읽히지 않는다(R-02).
- 같은 문서와 `config/variables/default.py:46-47`의 주석은 `MCP_AUTO_TOOL_SELECTION`이 도구 자동 선택을 켠다, `MCP_ALLOWED_ROOT_PATHS`가 로컬 파일 접근을 제한한다고 설명하지만 두 키를 읽는 코드가 없다. 도구 선택은 항상 하고 경로 제한은 없다(R-24, Grep 확인).
- `mcp_configs`의 `tool_name`은 `agent.py:119`와 `mcp/README.md` 표에 "특정 도구 지정"으로 있으나 읽는 코드가 없다(R-19). 반대로 `connection_headers`는 코드에만 있고 문서에 없다.
- docs·`pip install gpt-researcher`가 "MCP 의존성이 자동 설치된다"고 하지만 `pyproject.toml:105`는 `mcp`만 넣고 `langchain-mcp-adapters`는 `requirements.txt:60-62`("MCP Support (optional)")에만 있다(R-03).
- `agent.py:122`의 `connection_type` 설명은 `stdio, websocket, http`지만 구현은 값을 검증하지 않고 넘기며, `http(s)` URL이 있으면 `connection_type`을 무시하고 `streamable_http`를 쓴다. SSE는 어느 경로로도 `url`이 붙지 않는다(R-19, 실행 B).
- `mcp/README.md`는 "automatic cleanup and resource management"를 말하지만 `close_client`는 참조만 지운다(`client.py:158-166`의 주석이 그 사실을 적는다, R-18).
- docs의 "Stage 2: LLM executes research using selected tools" 설명과 달리 도구 결과를 LLM에 되돌려 주는 단계가 없고 LLM 호출은 한 번뿐이다(R-22). `retrievers/mcp/retriever.py`의 docstring은 "2-3개 도구"라고 쓰지만 실제는 상한 3이고 LLM에게 "정확히 N개"를 요구하며 초과를 자르지 않는다(R-20).
- `MCPRetriever.__init__` docstring은 `headers`가 "MCP 설정을 담는다"고 쓰지만 `headers`는 저장만 하고 설정은 `researcher.mcp_configs`에서만 꺼낸다(R-15).
- `_tavily_mcp_redundant_with_direct`의 docstring과 경고 문구("to avoid double API cost")는 직접 Tavily와 Tavily MCP를 함께 돌리는 이중 비용을 피하려는 것이라고 설명하지만, 사전 실행(R-06)에는 이 판정이 없어 `fast`에서는 MCP가 여전히 한 번 실행된다(R-12, 실행 H).
- research-pipeline 스펙의 `_get_context_by_web_search` C-11은 "서브쿼리 계획 이후"만 가리켜서 그 앞의 사전 실행(`researcher.py:311-362`)이 빠져 있다. 그 스펙의 1.1 흐름에도 이 단계가 없다(1.2에 적음).
- 기능 지도의 MCP 행은 "도구 선택·실행은 미확인"이었으나 이 스펙에서 코드와 실행으로 확인했다.

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-04, `agent.py:172-174`, `:176` | 코드를 읽고 `_process_mcp_configs`를 exec(실행 D). 문자열 retrievers 분기는 `Config`가 항상 리스트를 만든다는 점에서 일반 경로는 아님(`config.py:69-75`) |
| R-02 | `actions/retriever.py:161-193` `get_retrievers`, C-04, `agent.py:296-320`, `retrievers/mcp/retriever.py:98-100`, `:127-131` | `get_retrievers`를 exec해 헤더 우선 확인(실행 A). 설정 없는 MCP 클래스의 즉시 `[]`는 코드 읽기와 실행 G(`mcp_configs` 없음 사례) |
| R-03 | C-28, `mcp/client.py:11-15`, `:129-131`, `pyproject.toml:105`, `requirements.txt:60-62` | `mcp/__init__.py`·`retrievers/mcp/__init__.py`·`client.py`·`get_retriever`/`get_retrievers`를 실제 파일 그대로 exec(실행 A). 이 환경에 어댑터가 정말 없어서 실제 미설치 경로. 어댑터가 설치된 환경의 import 성공 경로는 실행하지 못함 |
| R-04 | C-03 | 소스 exec, 17개 조합 모두 일치(실행 C) |
| R-05 | C-06, `agent.py:201`(`mcp_strategy` 대입), 실행 H("알 수 없는 전략"·`_get_mcp_strategy`) | 알 수 없는 값은 `GPTResearcher` 밖에서만 생김(코드 읽기). 실행은 가짜 researcher |
| R-06 | C-05, `researcher.py:312-362` | 실행 H(fast/deep/disabled 횟수, 알 수 없는 값). `query`가 소제목이라는 설명은 호출 구조 읽기 |
| R-07 | C-07, `researcher.py:560-603` | 실행 H. 스크랩·선별·계획은 가짜 |
| R-08 | R-06, R-07, R-10의 합. `researcher.py:369-371`(원 질문 추가), `query_processing.py:189-199`, `researcher.py:175-188`(hybrid 두 패스) | 표의 굵은 칸은 실행 H(`[Tavily, MCP]` fast 1, deep 3, subtopic 2, disabled 0, Tavily 중복 fast 1·deep 0, MCP 단독 2/3/1). `[MCP, Tavily]`+deep 등은 코드 읽기. 하이브리드의 `deep` 6회는 실행 H(동시 두 패스) |
| R-09 | C-05, `researcher.py:34-48`, `:319-362` | 실행 H(잠금 유무 대조, 두 질문 연속, 캐시 형식·내용, 빈 결과 캐시). `_mcp_query_count`는 `__init__`에서만 쓰임(`git grep` 확인). `.copy()`가 얕은 복사라는 설명은 파이썬 규칙(추론) |
| R-10 | C-23, C-24, C-25, `researcher.py:50-66`, `:365-366`, `:388-391` | 실행 H(MCP 단독·MCP 첫 번째). `get_search_results`·`plan_research_outline`을 실제 소스로 exec했고 `to_thread`는 실제로 썼지만 MCP는 가짜 클래스 |
| R-11 | C-26, `researcher.py:906-934` | 실행 H(MCP 단독 결과에 웹 컨텍스트 없음) |
| R-12 | C-09, C-07 | 실행 I(판정 10 사례)·H(fast에서 사전 실행 낭비). `tests/skills/test_tavily_mcp_dedupe.py`는 서브쿼리 경로의 건너뛰기만 다루며(이름과 내용을 읽음, 실행하지 않음) 사전 실행은 다루지 않는다 |
| R-13 | C-08 | 실행 H(예외 격리 `mcp_cache_error`, 빈 `body` 제외는 코드 읽기와 J) |
| R-14 | C-10 | 실행 H(성공·빈 결과·예외 이벤트). 검색은 가짜 |
| R-15 | C-12, `retrievers/mcp/retriever.py:70-89` | 코드를 읽음. `headers`·`query_domains` 미사용은 파일 안 검색으로 확인(`:65-66`만 나옴) |
| R-16 | C-14 | `search`를 실제 소스로 exec(실행 G): 루프 블로킹(ticker 0회, 0.92초), 루프 밖 경로, 타임아웃 치환 변형(`timeout=300`→`0.3`, 소스의 해당 숫자만 정규식 치환, 1.31초에 `[]`). `ThreadPoolExecutor.__exit__`가 종료를 기다린다는 설명은 표준 라이브러리 규칙이고 실험이 같은 결과를 보임 |
| R-17 | C-13 | `search_async`를 실제 소스로 exec(실행 G), 하위 컴포넌트는 가짜 |
| R-18 | C-02, `retrievers/mcp/retriever.py:75`, `:300-324` | `MCPClientManager`를 실제 파일째 exec(실행 A, 가짜 클라이언트 주입). 서버 프로세스의 수명은 어댑터라 미확인 |
| R-19 | C-01 | 실행 B(13개 사례). `token`·`transport` 값을 어댑터가 어떻게 받는지는 미확인 |
| R-20 | C-15, C-16, C-18, `retrievers/mcp/retriever.py:147` | 실행 E(13개 사례). LLM과 `json_repair`는 대체, 실제 `create_chat_completion` 호출은 하지 않음 |
| R-21 | C-17 | 실행 E |
| R-22 | C-19, C-20 | 실행 F(LLM·도구 가짜). `research.py`에 `add_costs`가 없음은 `git grep`과 파일 읽기로 확인 |
| R-23 | C-21 | 실행 F(분기별 사례 10개). 실제 도구의 반환 형태는 어댑터 의존이라 미확인 |
| R-24 | C-27, `config/config.py:63-67`, `:308-325` | 네 키의 이름(대소문자 무시)을 추적 파일 전체에서 `git grep`(문서 `docs/`, `frontend/`, `tests/`는 제외): 설정 정의(`base.py`, `default.py`)와 `get_mcp_server_config`(`config.py:308-325`) 외에 읽는 곳이 없다. 테스트는 `get_mcp_server_config`와 설정값 저장만 확인한다(이름만 확인). 키가 정말 쓰이지 않는지 실행으로 비교하지는 않았다 |
| R-25 | R-13, R-14, R-16~R-18, R-20, R-22 | 위 규칙들의 실행 확인을 합친 결론. 실제 서버 장애는 확인하지 못함 |
| R-26 | C-11 | 실행 J(4 사례) |
| R-27 | C-07(`:654-663`), C-11(`:767`), C-20(`:138-144`) | 실행 H·F(리스트 본문 항목을 직접 만든 조건부 확인). 제공자의 `content` 형태는 미확인 |
| R-28 | C-07, C-11, 파이프라인 R-25 | 실행 H(3번 반복) |
| R-29 | C-22, `actions/utils.py:7-32`, `retrievers/mcp/retriever.py:85-89`, `:138-154`, `:167`, `:192` | 코드를 읽음. `stream_tool_selection`·`stream_tool_execution`·`stream_info`·`stream_stage_complete` 호출처 없음은 `git grep`으로 확인. conductor 이벤트 이름은 `researcher.py`에서 읽은 목록 |
| R-30 | `researcher.py:145-209`, `:159`, `deep_research.py:441-454`, `detailed_report.py:140-158` | 코드를 읽음 |
| R-31 | `backend/server/server_utils.py:420-422`, `websocket_manager.py:101`, `:116`, `:156-157`, `:174-175`, `basic_report.py:54-58`, `detailed_report.py:61-65` | 코드를 읽음. 서버 쪽 나머지는 서버 API 스펙의 몫 |
| T-01~T-30 | 해당 R-ID의 근거와 같다 | 모두 구현에서 도출. T-29는 실행하지 않았고, T-30의 뒤쪽 절반은 코드 읽기다. 나머지는 위 하네스로 실행했다(T-04~T-08은 H, T-09는 I, T-10~T-12는 H, T-13~T-16은 B, T-17·T-18은 E, T-19·T-20은 F, T-21·T-22는 G, T-23은 A, T-24는 H, T-25는 J, T-26·T-27·T-28은 H). 하네스의 대체물이 검증하지 않는 것은 1.4 확인 한계 |

### 2.2 코드 읽는 순서

1. `agent.py:171-176`, `:217-281`, `:295-321`: `mcp_configs`가 retriever 목록과 전략이 되는 과정.
2. `skills/researcher.py:311-362`(사전 실행) → `:520-663`(서브쿼리) → `:436-490`, `:665-737`(MCP 실행 호출) → `:739-790`(결합): conductor가 MCP를 부르는 곳.
3. `retrievers/mcp/retriever.py`(`search` → `search_async`) → `mcp/client.py`(변환·클라이언트) → `mcp/tool_selector.py`(도구 선택) → `mcp/research.py`(도구 실행·정규화): 한 번의 실행.
4. `actions/query_processing.py:44-81`, `:185-202`: MCP가 첫 번째·단독일 때의 초기 검색과 계획.

원본의 구현 전략은 "서브쿼리마다 MCP를 부르는 비용을 피하려고 기본 전략 `fast`에서 원 질문 한 번의 결과를 캐시해 모든 서브쿼리가 복사해 쓰는 것"이다(`researcher.py:311-362`의 주석 "Run MCP once with original query", "performance mode"가 그렇게 설명한다). 이것이 설계 의도라는 해석은 코드 주석에 근거한 추론이다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

## 적용 메모

없음. 이 스펙이 원본 동작으로 적은 것 중 바꿀 후보로 보이는 점(R-12의 사전 실행 낭비, R-16의 이벤트 루프 블로킹, R-27의 리스트 본문 처리, R-28의 MCP 본문 반복, R-24의 효과 없는 설정 키)은 우리 쪽 결정이 아니므로 사용자가 정하기 전에는 여기에 적지 않는다.
