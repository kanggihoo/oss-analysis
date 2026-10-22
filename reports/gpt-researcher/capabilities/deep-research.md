---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/skills/deep_research.py
  - gpt_researcher/agent.py
  - gpt_researcher/actions/query_processing.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/config/variables/base.py
  - gpt_researcher/utils/llm.py
  - gpt_researcher/utils/enum.py
  - gpt_researcher/prompts.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/retrievers/tavily/tavily_search.py
  - gpt_researcher/retrievers/duckduckgo/duckduckgo.py
  - gpt_researcher/retrievers/custom/custom.py
  - backend/report_type/basic_report/basic_report.py
  - backend/server/websocket_manager.py
  - backend/report_type/deep_research/main.py
  - backend/report_type/deep_research/README.md
  - backend/report_type/deep_research/example.py
  - docs/docs/gpt-researcher/gptr/deep_research.md
  - docs/docs/gpt-researcher/gptr/config.md
  - .claude/references/config-reference.md
  - tests/test_deep_research_parsing.py
  - tests/skills/test_deep_research_empty_results.py
  - tests/skills/test_deep_research_zero_queries.py
  - pyproject.toml
depends:
  - ../capabilities/retrievers.md
  - ../capabilities/research-pipeline.md
status: draft
reimplementation: 미실행
---

# Deep Research

> `report_type="deep"`로 만든 `GPTResearcher`가 `conduct_research()`를 받으면, 질문 하나와 설정(breadth·depth·concurrency)으로 "검색 질의 → 하위 조사 → 학습(learning) 추출 → 후속 질문으로 한 단계 더" 재귀를 돌려 학습과 출처를 모으고, 그것을 `[Source: URL]`이 붙은 컨텍스트 문자열 하나로 돌려주는 기능이다. 보고서 작성은 하지 않는다.

<!--
용어
- breadth: 한 단계(레벨)에서 만드는 검색 질의 개수. depth: 레벨 수(재귀 깊이).
- learning: 조사 결과에서 LLM이 뽑은 짧은 사실 한 줄. citation: 그 learning의 출처 URL.
- 중첩 연구자: 질의 하나를 조사하려고 새로 만드는 `GPTResearcher`(report_type은 `research_report`). 이 스펙에서는 "입력 → 정상 결과 → 실패"만 경계로 다룬다.
- 컨텍스트: 보고서 작성에 넘기는 조사 결과 문자열.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자가 `GPTResearcher(query, report_type="deep")`를 만들면 생성자가 `DeepResearchSkill`을 함께 만들고, 이때 breadth·depth·concurrency를 설정에서 한 번 읽어 둔다(R-01, R-03). `conduct_research()`는 에이전트 역할 선택(`choose_agent`)과 일반 조사 파이프라인을 건너뛰고 이 스킬의 `run()`으로 간다(R-02).
2. **계획 단계.** `run()`이 원래 질문을 모든 retriever로 한 번씩 검색(결과 개수는 어댑터 기본값)하고, 그 결과와 현재 시각을 LLM에 보여 주며 서로 다른 측면의 질문 3개를 받는다. 질문마다 답을 "Automatically proceeding with research"로 고정해 "원 질문 + 질문·답 목록" 문자열(`combined_query`)을 만든다(R-06~R-08).
3. **한 레벨의 처리.** `deep_research(combined_query, breadth, depth)`가 LLM에게 검색 질의 breadth개와 질의별 연구 목표(`researchGoal`)를 받는다. 질의마다 중첩 연구자를 만들어 `conduct_research()`로 조사하고, 그 컨텍스트에서 LLM이 learning(최대 3)과 후속 질문(최대 3)을 뽑는다. 한 레벨 안의 질의는 동시에 돌고 동시 실행 수는 세마포어로 제한한다(R-09~R-14).
4. **재귀.** `depth > 1`이면 레벨의 성공한 결과를 하나씩 순서대로(병렬 아님) 다음 레벨로 보낸다. 다음 레벨의 입력은 그 결과의 연구 목표와 후속 질문으로 만든 문자열이고, breadth는 `max(2, breadth // 2)`, depth는 1 줄어든다(R-15, R-16).
5. 각 레벨은 learning·citation·URL·컨텍스트 조각·출처를 합쳐 위로 돌려주고, 컨텍스트 조각이 25,000단어를 넘으면 앞쪽 항목부터 버린다(R-17, R-18).
6. `run()`이 learning마다 `"{learning} [Source: {URL}]"` 줄(출처가 있는 것만 `[Source]`)을 만들고 그 뒤에 컨텍스트 조각들을 이어 붙여 다시 25,000단어로 자른 뒤 `"\n"`으로 이은 문자열을 `researcher.context`에 넣고 돌려준다. `researcher.visited_urls`, `research_sources`도 결과로 바뀐다(R-19, R-20).
7. 실패는 질의 단위로 격리된다. 질의 하나가 실패하면 버리고 계속하며, 한 레벨의 모든 질의가 실패하거나 질의가 0개면 그 지점에서 재귀를 멈춘다. 반대로 계획 단계나 깊은 레벨의 질의 생성 LLM이 실패하면 `conduct_research()` 밖으로 예외가 나가고 지금까지 모은 결과는 `researcher`에 반영되지 않는다(R-21~R-24).

### 1.2 범위·통합 지점

- 제공:
  - `report_type="deep"` 분기와 그 결과(컨텍스트 문자열, `visited_urls`, `research_sources`).
  - 계획 단계, 레벨별 질의 생성, 재귀·동시성 규칙, 학습 추출, 중복 처리, 컨텍스트 단어 수 제한, 진행 콜백.
  - LLM 응답 3종의 요구 형식과 파서(JSON 복구 후 줄 형식 폴백) — C-ID로 제공.
- 제외:
  - 중첩 연구자가 질의 하나를 실제로 조사하는 일반 파이프라인(역할 선택, 서브쿼리 계획, 검색, 스크랩, 컨텍스트 선별, MCP, 출처 curation): [research-pipeline.md](../capabilities/research-pipeline.md)가 맡는다. 이 스펙은 호출 경계(R-11)만 다룬다. 스크래퍼는 [scrapers.md](../capabilities/scrapers.md), 컨텍스트 선별은 [context-selection.md](../capabilities/context-selection.md)가 맡는다.
  - 보고서 작성. 이 컨텍스트를 받아 `report_type="deep"`용 프롬프트(`generate_deep_research_prompt`, `prompts.py:418-483`, 매핑 `:858`)로 보고서를 쓰는 일은 보고서 작성 스펙의 몫이다.
  - LLM 제공자·`Config` 로딩·임베딩(사용자 제외). LLM 호출은 입력·출력 형식·실패만 경계로 정의하고 설정 키는 원문 이름만 쓴다.
  - 서버·CLI가 `report_type="deep"`을 어떻게 받아 넘기는지(서버 API 스펙). 이 스펙은 `GPTResearcher` 이후만 다룬다.
  - `backend/report_type/deep_research/example.py`: 같은 이름의 별도 `DeepResearch` 클래스를 정의한 독립 예제이고 `gpt_researcher`·`backend` 안에서 import하는 곳이 없다. 이 기능의 경로가 아니다(R-26 근거 참고).
- 외부 의존·선행 계약:
  - **retrievers 스펙**([retrievers.md](../capabilities/retrievers.md)): 계획 단계가 `researcher.retrievers`(클래스 목록)와 `get_search_results`로 검색한다. 어댑터 계약·`max_results` 기본값은 그쪽이 정한다.
  - **LLM 호출 `create_chat_completion(messages, model, temperature, max_tokens, llm_provider, reasoning_effort, llm_kwargs)`**: 입력은 `{role, content}` 메시지 목록이고 정상 결과는 응답 문자열 하나다. 응답이 비거나 호출이 실패하면 최대 10회(재시도 사이 대기 `min(2^(n-1), 8)`초) 시도하고 계속 실패하면 `RuntimeError`를 던진다(`utils/llm.py:120-162`). 이 스킬은 `cost_callback`을 넘기지 않는다(R-22).
  - **중첩 연구자 `GPTResearcher(...)`**: 입력은 R-11의 인자들이고, `await conduct_research()`의 정상 결과는 문자열 컨텍스트 또는 빈 리스트 `[]`다([research-pipeline.md](../capabilities/research-pipeline.md) R-25). 실패하면 예외를 던진다(예: 초기 검색의 생성자 오류, 일반 파이프라인 R-09).
  - **호출한 `GPTResearcher`(outer)가 가진 것**: `query`, `cfg`, `retrievers`, `websocket`, `tone`, `headers`, `visited_urls`(집합), `mcp_configs`, `mcp_strategy`, `get_costs()`, `log_handler`, `_log_event()`, `context`, `research_sources`.
- 소유 상태·부작용:
  - 스킬 인스턴스: `breadth`, `depth`, `concurrency_limit`, `visited_urls`(생성 시점의 outer 집합과 **같은 객체**), `learnings`(쓰이지 않음), `research_sources`·`context`(레벨마다 쌓이기만 하고 이 레포의 어디서도 읽지 않음).
  - outer에 쓰는 것: `context`(문자열), `visited_urls`(교체), `research_sources`(비어 있지 않을 때만 교체).
  - 중첩 연구자들은 outer의 `visited_urls` 집합을 공유한다(R-25). 중첩 연구자마다 자체 `Config`와 LLM·검색·스크랩 호출을 가지며 `websocket`을 그대로 공유해 로그를 같은 연결로 보낸다.
  - 표준 출력에 이모지가 섞인 진단 문구를 `print`하고 `logging`으로 경고·오류를 남긴다. `log_handler`가 있으면 `_log_event` 이벤트(`deep_research_initialize`·`deep_research_start`·`deep_research_costs`·`deep_research_complete`·`cost_update`)를 보낸다.

### 1.3 인터페이스와 데이터 의미

**진입·결과**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GPTResearcher(query, report_type="deep", …)` | `report_type == "deep"`이면 생성자가 스킬을 만든다 | 다른 `report_type`이면 스킬이 없다. `ReportType.DeepResearch.value == "deep"`(`utils/enum.py:27`). |
| `conduct_research(on_progress=None)` | → string | deep이면 `run()`의 결과 문자열을 `self.context`에 저장해 반환한다. 서버 경로의 `BasicReport.run`은 `on_progress` 없이 부른다. |
| `DeepResearchSkill.run(on_progress=None)` | → string | 최종 컨텍스트. 조사 결과가 하나도 없으면 빈 문자열 `""`이다(일반 파이프라인의 빈 `[]`와 다르다, R-20). |
| `deep_research(query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None)` | → map `{learnings: list[string], visited_urls: list[string] 또는 set, citations: map<learning, URL>, context: list[string], sources: list[map]}` | 재귀 단위. 호출마다 입력 목록·집합을 복사해서 쓰고 호출자의 객체는 바꾸지 않는다. `learnings`는 정상 종료 시 `set` 변환이라 순서가 정해지지 않는다. `visited_urls`는 정상 종료는 list, 조기 종료(질의 0개·전부 실패)는 입력의 복사본인 set이다. |
| `on_progress(progress)` | 동기 함수, 반환값 무시 | `ResearchProgress` 객체를 받는다. `async def`를 넘기면 코루틴이 만들어지고 await되지 않는다(R-23). |
| `ResearchProgress` | `current_depth`(시작 1), `total_depth`, `current_breadth`(시작 0), `total_breadth`, `current_query`(string 또는 null), `total_queries`(시작 0), `completed_queries`(시작 0) | `deep_research` 호출 하나마다 새 객체를 만들고 그 호출 안에서 같은 객체를 변경해서 계속 넘긴다(복사하지 않음). C-07. |

**설정 키** (원문 이름. 로딩은 설정 스펙이 맡는다)

| 키 | 타입 | 값 |
|---|---|---|
| `DEEP_RESEARCH_BREADTH` | int | `Config` 기본값 **3**(`default.py:40`). 같은 이름의 환경변수가 있으면 int로 바꿔 덮는다. 설정 JSON 파일에 같은 키를 쓰면 기본값을 덮는다. 스킬은 `cfg.deep_research_breadth`로 읽는다. |
| `DEEP_RESEARCH_DEPTH` | int | `Config` 기본값 **2**(`default.py:41`). `cfg.deep_research_depth`. |
| `DEEP_RESEARCH_CONCURRENCY` | int | `Config` 기본값 **4**(`default.py:42`). `cfg.deep_research_concurrency`. |
| (스킬 안의 `getattr` 기본값) | — | 속성이 없는 객체에서만 breadth 4, depth 2, concurrency 2. 실제 `Config`에서는 도달하지 않는다(R-03, R-04). |
| `MAX_CONTEXT_WORDS` | 상수 25000 | 설정 키가 아니라 모듈 상수(`deep_research.py:18`). 바꿀 방법이 없다. |
| 사용하는 LLM 설정 | — | `cfg.strategic_llm_provider`, `cfg.strategic_llm_model`, `cfg.reasoning_effort`, `cfg.llm_kwargs`. 세 LLM 호출 모두 STRATEGIC 모델이다. |

**LLM 호출 3종** (프롬프트 원문은 C-09~C-11. 공통: system+user 메시지 2개, `temperature=0.4`, 스트리밍·websocket·`cost_callback` 없음)

| 호출 | 요구하는 출력 | `reasoning_effort` / `max_tokens` | 파서 |
|---|---|---|---|
| 검색 질의 생성(`generate_search_queries`) | JSON 배열 `[{"query": str, "researchGoal": str}]`, 개수는 `num_queries`(= 그 레벨의 breadth) | `cfg.reasoning_effort` / 기본 4000 | `parse_search_queries_response`(C-03) |
| 계획 질문 생성(`generate_research_plan`) | JSON 객체 `{"questions": [str]}`, 개수 3 | `"high"` / 기본 4000 | `parse_follow_up_questions_response`(C-04) |
| 학습 추출(`process_research_results`) | JSON 객체 `{"learnings": [{"insight": str, "sourceUrl": str 또는 ""}], "followUpQuestions": [str]}`, 최대 3개씩 | `"high"` / 4000 | `parse_research_results_response`(C-05) |

**파서 결과 형식**: 질의 목록은 `[{query, researchGoal}]`, 질문 목록은 `[string]`, 학습 결과는 `{learnings: [string], followUpQuestions: [string], citations: map<learning, URL>}`다. 파서는 예외를 던지지 않고 못 읽으면 빈 목록(또는 빈 결과)을 돌려준다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `GPTResearcher` 생성, `report_type == "deep"` | `DeepResearchSkill(self)`를 `deep_researcher`로 만든다. 다른 `report_type`이면 `deep_researcher`는 None이다. 스킬은 생성 시점의 `researcher.websocket`, `tone`, `headers`(없으면 `{}`), `visited_urls`, `cfg.config_path`를 복사·참조해 둔다. | 코드 확인 |
| R-02 | `conduct_research(on_progress)`에서 `report_type == "deep"`이고 스킬이 있음 | `start` 이벤트를 기록한 뒤 `_current_step = "deep_research"`로 두고 `_handle_deep_research`로 간다. `choose_agent`, `ResearchConductor`, 이미지 사전 생성은 실행하지 않는다(outer의 `agent`·`role`은 채워지지 않는다). `_handle_deep_research`는 `deep_research_initialize`·`deep_research_start` 이벤트(breadth·depth·concurrency 포함), `run()`, `deep_research_complete`·`cost_update` 이벤트를 차례로 하고 `self.context`를 반환한다. `log_handler`가 없으면 이벤트는 만들어지지 않는다. | 코드 확인 |
| R-03 | 실제 `Config`로 만든 `cfg` | `Config`가 `DEFAULT_CONFIG`의 모든 키를 소문자 속성으로 설정하므로 `cfg.deep_research_breadth/depth/concurrency`는 항상 존재하고 기본값은 3/2/4다. 환경변수 `DEEP_RESEARCH_*`는 int로 바꿔 덮는다(정수가 아니면 `ValueError`). 그래서 스킬 안의 `getattr` 기본값(4/2/2)은 적용되지 않는다. | 코드 확인 (`Config`를 실제로 만들어 보지는 않음, 확인 한계) |
| R-04 | 속성이 없는 `cfg`(예: 테스트용 단순 객체) | `getattr`이 breadth 4, depth 2, concurrency 2를 쓴다. | 실행 확인 |
| R-05 | 설정 값 검증 | 검증이 없다. `depth <= 1`이면 재귀 없이 한 레벨만 돈다(`depth=0`도 한 레벨). `breadth=1, depth=2`이면 자식 레벨의 breadth는 `max(2, 1//2) = 2`다. `concurrency=0`이면 `Semaphore(0)`이라 질의 처리가 시작되지 않고 영원히 끝나지 않는다. `concurrency<0`이면 질의 생성 LLM 호출 뒤 `ValueError`가 `run` 밖으로 나간다. `breadth=0`이면 질의 0개로 끝난다(R-13). | 실행 확인 (breadth=0은 코드 확인) |
| R-06 | `run()` 시작, 계획 검색 | outer의 `researcher.query`(원 질문)로 `researcher.retrievers`를 **목록 순서대로 하나씩** `get_search_results(query, retriever, researcher=outer)`로 검색한다. `max_results`·`query_domains`를 넘기지 않으므로 어댑터 기본값이 쓰이고(예: tavily 10, duckduckgo 5, custom 5) `query_domains`는 인자를 주지 않아 None 그대로 어댑터 생성자에 전달된다. retriever 하나의 생성·검색 예외는 경고 로그만 남기고 그 retriever를 건너뛴다. 결과 항목(딕셔너리 원본)은 모두 한 리스트로 합쳐진다. MCP 어댑터면 `researcher=`가 붙는다. | 코드 확인 (`max_results` 미전달·예외 건너뜀은 실행 확인) |
| R-07 | 계획 질문 LLM 호출 | user 메시지에 원 질문, 현재 시각(`datetime.now()`를 `"%Y-%m-%d %H:%M:%S"`로), `Search results:` 아래에 합친 검색 결과 리스트의 파이썬 `repr`(길이 제한 없음)을 넣고 질문 3개를 요청한다. 응답은 C-04 파서로 읽어 최대 3개를 얻는다. 이 LLM 호출 실패(재시도 소진 `RuntimeError`)는 잡지 않아 `run` 밖으로 전파된다. 검색 결과가 비어도 LLM은 부른다. | 코드 확인 (파서는 실행 확인) |
| R-08 | 계획 질문 → `combined_query` | 질문마다 답을 `"Automatically proceeding with research"`로 둔다(사용자에게 되묻지 않음). 질문 수가 0이어도 중단하지 않고 질문·답 없이 `combined_query`로 진행한다. 문자열 형식은 C-13. | 실행 확인 |
| R-09 | `deep_research` 호출 시작 | 입력 `learnings`·`citations`·`visited_urls`를 복사하고(없으면 빈 값), 새 `ResearchProgress(depth, breadth)`를 만들어 `on_progress`가 있으면 한 번 부른다. 이어서 `generate_search_queries(query, num_queries=breadth)`를 호출하고 `progress.total_queries`를 질의 수로 정한다. | 실행 확인 |
| R-10 | 질의 생성 응답 해석 | C-02, C-03: 응답을 JSON으로 읽는다(후보: 응답 전체, 코드펜스 안, 바깥 `[...]`, 바깥 `{...}` 순으로 `json_repair.loads`가 예외 없이 읽은 첫 값). 최상위가 리스트이거나, 딕셔너리면 `queries`→`searchQueries`→`items` 중 처음 값이 있는 키의 리스트를 쓴다. 항목은 `query`·`researchGoal`이 모두 문자열이고 공백 제거 뒤 비어 있지 않을 때만 남기며(공백 제거한 값을 저장), 앞에서 `num_queries`개로 자른다. 하나도 못 얻으면 응답에서 코드펜스 표시를 지우고 줄마다 `Query:`·`Goal:`/`Research Goal:`(앞에 `-`·`*`·`번호.`/`번호)` 허용, 대소문자 무시) 쌍을 찾는 줄 파서로 내려가며, Goal이 없는 마지막 Query는 버린다. 그래도 없으면 빈 목록이다. | 실행 확인 (JSON 복구 부분은 한계 참고) |
| R-11 | 질의 하나의 처리(`process_query`) | 세마포어를 얻은 뒤 `progress.current_query`를 이 질의로 바꾸고 `on_progress`를 부른 다음, 중첩 연구자를 만든다: `query=질의`, `report_type="research_report"`, `report_source="web"`, `tone=outer 톤`, `websocket=outer 값`, `config_path=skill.config_path`, `headers=skill.headers`, `visited_urls=skill.visited_urls`(공유 집합), `mcp_configs`·`mcp_strategy`는 outer 값. `query_domains`, `source_urls`, `document_urls`, `documents`, `vector_store`, `report_format`, `log_handler`, `prompt_family`, `verbose`(기본 True)는 넘기지 않으므로 outer에 준 값은 전달되지 않고, 중첩 연구자는 `Config(config_path)`를 새로 만든다(outer `cfg`에 나중에 덮어쓴 값, 예: `BasicReport`의 `max_search_results_per_query`는 전달되지 않는다). outer의 `report_source`와 상관없이 항상 웹 소스다. 그 뒤 `await researcher.conduct_research()`(`on_progress` 없음)를 부른다. 이미지 생성이 켜져 있으면 중첩 연구자가 각자 이미지를 사전 생성한다. | 코드 확인 (인자는 실행 확인) |
| R-12 | 질의 하나의 후처리 | 중첩 컨텍스트가 비어 있어도(`[]`·빈 문자열) 학습 추출 LLM을 부른다. 그 프롬프트의 `Research results:` 뒤에는 컨텍스트가 f-string 그대로 들어가므로 빈 리스트는 `[]`로 보인다. 추출 결과(learning과 후속 질문 최대 3개씩, citations)를 만들고 `progress.completed_queries`, `current_breadth`를 1씩 올린 뒤 `on_progress`를 부른다. 질의 결과는 `{learnings, visited_urls(중첩 연구자의 집합 전체 스냅숏), followUpQuestions, researchGoal, citations, context, sources}`이고, `context`는 리스트면 `"\n"`으로 이은 문자열, 그 외는 값 또는 `""`다. `sources`는 중첩 연구자의 `research_sources`다. | 실행 확인 |
| R-13 | 질의가 0개(생성 결과 없음, `breadth=0` 포함) | 경고 로그를 남기고 즉시 반환한다. 반환은 입력으로 받은 learnings·citations·(복사한) visited_urls와 빈 `context`·`sources`이고 스킬의 `context`·`research_sources`에는 아무것도 추가하지 않는다. 재귀하지 않는다. 최상위에서 일어나면 `run()`은 `""`를 돌려준다. | 실행 확인 |
| R-14 | 동시성 | 레벨(`deep_research` 호출)마다 `asyncio.Semaphore(concurrency_limit)`을 새로 만들고 그 레벨의 질의 전부를 `asyncio.gather`로 시작하되 세마포어 안에서만 본문을 실행한다. 그래서 한 레벨 안에서 최대 `concurrency_limit`개가 동시에 돌고 결과는 질의 순서대로 모인다. 제한은 레벨 안에서만 적용된다. 한 부모의 서로 다른 결과로 들어가는 재귀(R-15)는 순차라서 전체 동시 실행 수는 이 값을 넘지 않는다(중첩 연구자 내부의 서브쿼리·스크랩 동시성은 별개). | 실행 확인 |
| R-15 | 재귀 | 레벨의 질의 처리가 끝나면 성공한 결과를 **순서대로 하나씩** 처리한다: 그 결과의 learnings·visited_urls·citations를 합치고(`context`가 있으면 문자열 항목으로, 리스트면 항목별로 추가, `sources` 추가), `depth > 1`이면 `new_breadth = max(2, breadth // 2)`, `new_depth = depth - 1`, 다음 입력을 C-12의 f-string(연구 목표 + 후속 질문을 공백으로 이은 것)으로 만들어 `deep_research`를 await한다. 돌아온 learnings로 `all_learnings`를 바꾸고 visited_urls·citations를 합치고 context·sources를 이어 붙인다. 학습은 이후 LLM 프롬프트에 들어가지 않는다(다음 레벨은 연구 목표와 후속 질문만 본다). 그 결과 `breadth=4, depth=3`이면 레벨 breadth는 4, 2, 2이고 중첩 연구자는 4 + 4×2 + 4×2×2 = 28개다. | 실행 확인 |
| R-16 | 레벨 내 전부 실패 | 질의가 있었지만 성공한 결과가 하나도 없으면 경고 로그를 남기고 입력 learnings·citations·(복사한) visited_urls와 빈 `context`·`sources`를 돌려주고 재귀하지 않는다(`depth`가 남아 있어도). 이때 중첩 연구자가 공유 집합에 넣은 URL은 이 반환에 들어 있지 않다. | 실행 확인 |
| R-17 | 레벨 종료 | 스킬의 `context`, `research_sources`에 이 레벨의 `all_context`, `all_sources`를 `extend`한다(중복이 쌓이지만 읽는 곳은 없다). `all_context`를 C-06으로 자르고(뒤쪽 항목 우선), 반환은 `learnings = list(set(all_learnings))`(중복 제거, 순서 없음), `visited_urls = list(...)`, `citations`, 자른 `context`, 자르지 않은 `sources`다. 자식 레벨이 이미 자른 컨텍스트가 부모의 `all_context`에 들어 있어 부모에서 다시 잘린다. | 실행 확인 |
| R-18 | 컨텍스트 단어 수 제한 | C-06: 단어는 공백으로 나눈 조각이고 항목이 dict면 `str(dict)`로, 리스트면 `" ".join`해서 센다. 뒤쪽 항목부터 모아 25,000단어 이하인 것만 앞쪽 순서를 유지해 남기고, 처음 보는(가장 뒤) 항목 하나가 단독으로 25,000단어를 넘으면 앞 25,000단어만 문자열로 잘라 그것만 남긴다. 중간 항목이 넘치면 그 항목과 그 앞의 모든 항목을 버린다. 단어가 0인 항목은 항상 들어간다. | 실행 확인 |
| R-19 | 최종 컨텍스트 조립(`run`) | 재귀 결과의 learnings를 반복하며 `citations[learning]`이 있으면 `"{learning} [Source: {citation}]"`, 없으면 learning 그대로 한 항목으로 만든다. 그 뒤에 결과 `context` 항목들을 이어 붙이고 C-06으로 다시 자른다(learnings가 앞이라 단어가 넘치면 먼저 버려진다). 항목은 str은 그대로, dict는 `Content` 값(없으면 `str(dict)`)으로 바꿔 `"\n"`으로 잇는다. 이 문자열을 `researcher.context`에 넣고 반환한다. 같은 learning 텍스트는 학습 목록에서 하나로 합쳐지고, citation은 같은 텍스트에 대해 나중에 들어온 것이 이긴다. | 실행 확인 (dict 분기는 현재 흐름에서 도달하지 않음, 추론: 중첩 컨텍스트는 문자열 또는 `[]`) |
| R-20 | `run` 종료 상태 | `researcher.visited_urls`를 재귀 결과의 `visited_urls`로 **교체**한다(정상 종료면 list, 조기 종료면 입력 복사본 set이라 공유 집합과 다른 객체). `results['sources']`가 비어 있지 않을 때만 `researcher.research_sources`를 그 리스트로 바꾼다. 결과가 없으면(질의 0개, 전부 실패) 반환과 `researcher.context`는 `""`다. 실행 시간과 비용을 `logger.info`로 남긴다. | 실행 확인 |
| R-21 | 질의 하나의 실패 | `process_query` 본문(중첩 연구자 생성·`conduct_research`·학습 추출 LLM·파싱·그 안의 `on_progress` 호출)에서 `Exception`이 나면 오류를 `logger.error`로 남기고 트레이스백을 `print`한 뒤 그 질의를 `None`으로 돌려준다. 다른 질의는 계속된다. 성공한 결과만 합쳐지고(진행의 `completed_queries`는 성공한 것만 올린다), 레벨 끝에서 `progress.current_breadth`는 성공 수로 맞춰진다. 취소(`CancelledError`)는 잡지 않는다. | 실행 확인 |
| R-22 | 비용 | 스킬은 어떤 LLM 호출에도 `cost_callback`을 넘기지 않고 outer의 `add_costs`를 부르지 않으며, 중첩 연구자의 비용은 그 객체에만 쌓이고 버려진다. 그래서 `run()`이 계산하는 `research_costs = researcher.get_costs() - initial_costs`는 outer의 비용이 다른 경로로 바뀌지 않는 한 0이고, `deep_research_costs`(`research_costs`, `total_costs`) 이벤트·`cost_update` 이벤트·"Total research costs" 로그는 그 값을 그대로 낸다. | 코드 확인 (cost_callback 미전달과 outer 비용 0은 실행 확인, 중첩 연구자 비용이 버려지는 부분은 코드 확인) |
| R-23 | `on_progress` | 호출 시점: ① 레벨 시작 직후(`total_queries=0`, `current_query=None`), ② 질의가 세마포어를 얻어 시작할 때(`current_query` 갱신), ③ 질의 성공 직후, ④ `gather` 끝(`current_breadth = 성공 수`). 객체는 레벨마다 하나이고 같은 객체가 변경되며 넘겨진다(값을 보관하려면 호출자가 복사해야 한다). 자식 레벨은 새 객체(`current_depth=1`, `total_depth=남은 depth`, `total_breadth=그 레벨 breadth`)를 쓰고, 부모의 `current_depth` 증가(`+= 1`)는 이후 알림이 없어 호출자에게 보이지 않는다. 호출은 동기이고 반환값은 무시한다. ②·③의 콜백이 예외를 던지면 R-21로 그 질의가 버려지고, ①·④의 콜백 예외는 `run` 밖으로 전파된다. 서버 경로(`BasicReport`)는 콜백을 넘기지 않는다. | 실행 확인 (①·②·알림 순서는 실행, ③·④의 예외 처리와 서버 경로는 코드 확인) |
| R-24 | 전파되는 실패 | 다음은 잡히지 않아 `conduct_research()`가 예외를 던진다: 계획 질문 LLM 호출 실패(R-07), 깊은 레벨을 포함한 질의 생성 LLM 호출 실패(자식 레벨 호출은 `try` 밖), 레벨 시작·끝의 `on_progress` 예외, 세마포어 생성 오류(R-05). 이때 `researcher.context`(및 `visited_urls`·`research_sources`의 교체)는 갱신되지 않아 그전의 값(초기값)에 머문다. 중첩 연구자가 공유 집합에 넣은 URL만 outer의 집합에 남는다. 부분 결과를 돌려주는 경로는 없다. | 실행 확인 |
| R-25 | URL·학습 중복 | 중첩 연구자는 모두 `skill.visited_urls`(= outer가 생성자에서 받은 집합 객체)를 받으므로, 일반 파이프라인의 URL 중복 제거(retrievers R-12)가 질의·레벨·형제 사이에 적용돼 이미 방문한 URL은 다시 스크랩되지 않는다. `deep_research`의 `visited_urls` 인자와 반환값은 별도의 복사본으로, 중복 제거에 쓰이지 않고 결과 보고에만 쓰인다. 최종 `visited_urls`는 합집합이라 중복이 없다. learning은 텍스트가 같으면 하나로 합쳐진다(`set`). `sources`와 컨텍스트 조각은 중복을 제거하지 않는다. | 실행 확인 |
| R-26 | 문서·예제 | `backend/report_type/deep_research/main.py`는 `GPTResearcher(report_type="deep")`로 `conduct_research(on_progress)`와 `write_report()`를 차례로 부르는 예제이고, `example.py`는 이 경로와 무관한 별도 클래스다. 문서·README의 기본값 표기는 구현과 다르다(2.1). | 코드 확인 |

- 불변식:
  - 한 레벨의 질의 수는 `breadth`(질의 생성기가 breadth보다 적게 주면 그 수) 이하이고, 재귀가 있으면 자식 breadth는 항상 2 이상이다(R-10, R-15).
  - 총 레벨 수는 `max(depth, 1)` 이하다(R-05, R-15).
  - 동시에 실행되는 질의 본문은 한 레벨 안에서 `concurrency_limit` 이하다(R-14).
  - 정상 종료한 `run()`의 반환은 문자열이고, 25,000단어를 넘지 않는다(R-18, R-19. 단, 첫 항목 하나가 넘치면 잘린 문자열 하나). 결과가 없으면 `""`다.
- 미결정:
  - M-01 (R-10, C-02): `json_repair.loads`가 비JSON 입력(자연어 문단, 앞뒤 설명이 붙은 JSON)에서 무엇을 돌려주는지 확인하지 못했다. 이 스킬은 "예외 없이 읽은 첫 후보"를 쓰므로 반환이 리스트·딕셔너리가 아니면(예: 빈 문자열) 다음 후보를 보지 않고 줄 파서로 내려간다. 같은 라이브러리(`json-repair`, `pyproject.toml:78`의 `>=0.44.0`)를 쓰면 같은 결과이고, 다른 복구기를 쓰면 복구 범위가 달라진다. 영향: 앞뒤에 설명이 붙은 JSON, 쉼표·따옴표 오류가 있는 JSON에서 결과가 달라질 수 있다.
- 확인 한계:
  - `json-repair`가 이 환경에 없어서 JSON "복구" 동작은 실행하지 못했다. 데모의 JSON 파서는 엄격한 `json.loads` 가짜이고, 쉼표 오류·따옴표 누락·대문자 코드펜스 복구는 원본 테스트(`tests/test_deep_research_parsing.py`)가 기대하는 값만 읽었다(실행하지 않음).
  - `agent.py`와 실제 `Config`, `GPTResearcher`는 의존성(langchain 등) 때문에 import하지 못해 실행하지 않았다. `conduct_research` 분기, `Config`의 기본값 적용은 코드 확인이다. 재귀·동시성·실패·진행 이벤트는 원본 `deep_research.py`를 그대로 실행하되 LLM, 검색, 중첩 `GPTResearcher`를 가짜로 바꿨다. 실제 LLM 응답 품질, 실제 조사 결과, 실제 비용 계산은 검증하지 않았다.
  - 중첩 연구자가 돌려주는 컨텍스트의 실제 모양(문자열이 대부분)은 일반 파이프라인 스펙을 따랐고 이 스펙에서 다시 실행하지 않았다.

### 1.5 필수 코드 참조

라이선스: overview 1절에 따라 `LICENSE`는 Apache License 2.0이고 `pyproject.toml`은 MIT로 표기해 어긋난다. 인용 허용 여부를 이 분석에서 판단하지 않았으므로 C-ID는 위치만 가리키고 원문을 옮기지 않았다. 프롬프트 문구가 결과에 영향을 주므로 C-09~C-11은 구현할 때 그대로 읽어야 한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/skills/deep_research.py:17-45` `MAX_CONTEXT_WORDS`, `JSON_BLOCK_PATTERNS`, `QUERY_LINE_PATTERN`, `GOAL_LINE_PATTERN`, `QUESTION_LINE_PATTERN`, `LEARNING_LINE_PATTERN`, `URL_PATTERN` | 25,000 상수와 JSON 후보·줄 형식·URL 정규식 전부. 줄 접두(`-`, `*`, `번호.`/`번호)`)와 대소문자 무시, 물음표로 끝나는 모든 줄을 질문으로 보는 규칙, URL이 `"`·`,`·`;`·`)`·`]`·`>` 앞에서 끝나는 규칙. | R-10, R-18, R-19 |
| C-02 | `skills/deep_research.py:48-74` `_extract_json_payloads`, `_load_repaired_json` | JSON 후보 순서(응답 전체 → 코드펜스 → 바깥 `[...]` → 바깥 `{...}`)와 중복 제거, `json_repair.loads`가 예외 없이 읽은 첫 값 반환, 모두 실패하면 None. | R-10, M-01 |
| C-03 | `skills/deep_research.py:77-122` `parse_search_queries_response` | 질의 응답 해석 전체(JSON 래퍼 키, 항목 검증·공백 제거, 개수 제한, 줄 파서 폴백). | R-10 |
| C-04 | `skills/deep_research.py:125-146` `parse_follow_up_questions_response` | 질문 응답 해석(`questions`/`followUpQuestions`/`items` 키, 요소를 `str()`로 바꾸고 공백 항목 버림, 줄 폴백은 `Question:` 접두 허용, 물음표로 끝나는 줄). | R-07 |
| C-05 | `skills/deep_research.py:149-211` `parse_research_results_response` | 학습 응답 해석(`insight`/`learning`, `sourceUrl`/`citation`, 문자열 요소, `followUpQuestions`/`questions` 키, 둘 다 비면 줄 폴백, 개수 제한, citation 맵, 줄 형식의 `Learning [URL]:`과 본문 속 URL 추출). | R-12 |
| C-06 | `skills/deep_research.py:213-237` `count_words`, `trim_context_to_word_limit` | 단어 세기와 뒤쪽 우선 자르기 알고리즘(`max_words` 기본 25000). | R-17, R-18, R-19 |
| C-07 | `skills/deep_research.py:239-247` `ResearchProgress` | 진행 객체의 필드와 초깃값. | R-23 |
| C-08 | `skills/deep_research.py:250-263` `DeepResearchSkill.__init__` | 설정을 읽는 속성 이름(`deep_research_breadth` 등)과 `getattr` 기본값, outer에서 가져오는 속성. | R-01, R-03, R-04 |
| C-09 | `skills/deep_research.py:265-296` `generate_search_queries` | 질의 생성 프롬프트(system/user 문구, JSON 스키마), 호출 인자. | R-09, R-10 |
| C-10 | `skills/deep_research.py:298-350` `generate_research_plan` | 계획 검색 호출 방식, 프롬프트(현재 시각, 검색 결과 삽입), 호출 인자(`reasoning_effort` high). | R-06, R-07 |
| C-11 | `skills/deep_research.py:352-384` `process_research_results` | 학습 추출 프롬프트와 JSON 스키마, `max_tokens=4000`, `reasoning_effort` high. | R-12 |
| C-12 | `skills/deep_research.py:386-584` `deep_research` | 레벨 처리 전체: 질의 0개·전부 실패 조기 종료, 세마포어, `process_query`(중첩 연구자 인자, 질의 결과 형식), 결과 합치기, 재귀(`next_query` 문자열 형식, `max(2, breadth // 2)`), 레벨 종료와 반환 형식, `on_progress` 호출 위치. | R-09, R-11~R-17, R-21~R-25 |
| C-13 | `skills/deep_research.py:586-655` `DeepResearchSkill.run` | 계획 → `combined_query` 문자열 형식(고정 답, `Follow - up` 철자 포함) → 재귀 호출 → 비용 계산·로그 → 학습 줄 조립 → 최종 자르기 → outer 상태 갱신 → 반환. | R-06~R-08, R-19, R-20, R-22 |
| C-14 | `gpt_researcher/agent.py:186-193`, `:343-365`, `:415-461` | 스킬 생성 조건, deep 분기(에이전트 선택·일반 파이프라인 건너뜀), `_handle_deep_research`의 이벤트 순서와 반환. | R-01, R-02 |
| C-15 | `gpt_researcher/actions/query_processing.py:44-81` `get_search_results` | 계획 검색이 쓰는 호출: MCP 판별(`researcher=` 전달), `query_domains` 변환 없음, `max_results`는 값이 있을 때만 전달, `asyncio.to_thread`로 실행. | R-06 |
| C-16 | `gpt_researcher/config/variables/default.py:39-42`, `config/variables/base.py:38-40`, `config/config.py:63-67`, `:253-278` | 설정 키·타입·기본값, 소문자 속성화, 환경변수 int 변환. | R-03 |

### 1.6 수락 사례

출처: 사례별 표기. "실행 관찰"은 `artifacts/gpt-researcher/deep-research-demos/`의 스크립트로 원본 `deep_research.py`를 실행한 결과이고(대체물: LLM, 검색, `GPTResearcher`, `json_repair`는 가짜. 출력 파일 `parsers_demo.out.txt`, `recursion_demo.out.txt`), 검증하지 않는 것은 실제 LLM 응답·실제 조사·비용 계산·JSON 복구다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-10 | 응답 `[{"query":"q1","researchGoal":"g1"},{"query":"q2","researchGoal":"g2"}]`, `num_queries=3` | 두 항목 그대로. 코드펜스 안 JSON, `{"queries":[…]}`·`{"searchQueries":[…]}` 래퍼도 같다. | 실행 관찰(parsers §1) |
| T-02 | R-10 | `researchGoal` 없음 / `query`가 공백 / `researchGoal`이 숫자 / `" ok "`+`" goal "` 항목이 섞인 배열 | `[{"query":"ok","researchGoal":"goal"}]`(공백 제거). 항목이 4개 이상이면 앞의 `num_queries`개만. | 실행 관찰 |
| T-03 | R-10 | `"1. Query: q1\n   Goal: g1\n2. Query: q2\n   Goal: g2"`, `"Query: q1\nGoal: g1\nQuery: q2"` | 앞의 것은 두 항목, 뒤의 것은 `q1`만(Goal 없는 q2는 버림). `Research Goal:` 접두와 `-` 불릿도 허용. | 실행 관찰 |
| T-04 | R-10, R-13 | `[{"query":"","researchGoal":"x"}]`, `""`, 자연어 문단 | 모두 `[]`. 이것이 레벨의 질의 생성 결과면 R-13으로 끝난다. | 실행 관찰 |
| T-05 | R-10 | `[{"query": "test query", "researchGoal": "test goal",}]`(끝 쉼표), ` ```JSON ` 대문자 코드펜스 | 복구되어 질의 1개. | 원본 테스트 열람(`tests/test_deep_research_parsing.py`), 실행 안 함(json_repair 필요) |
| T-06 | R-07 | `{"questions":["What A?","What B?"]}` / `["A?", 5, "", "  "]` / 줄 `- What A?\n- not a question` | `["What A?","What B?"]` / `["A?","5"]`(비문자열 `str()`, 공백 버림) / `["What A?"]`(물음표로 끝나는 줄만). 개수는 앞에서 `num_questions`개. | 실행 관찰 |
| T-07 | R-12 | `{"learnings":[{"insight":"I1","sourceUrl":"https://a.test"},{"insight":"I2","sourceUrl":""}],"followUpQuestions":["N1?"]}` | learnings `["I1","I2"]`, citations `{"I1":"https://a.test"}`(빈 URL은 citation 없음), 질문 `["N1?"]`. 별칭 키 `learning`/`citation`, 문자열 요소도 읽힌다. | 실행 관찰 |
| T-08 | R-12, R-19 | `learnings`와 `followUpQuestions`가 각각 4개 / 같은 insight가 URL 두 개로 두 번 | 각각 앞 3개만 / 학습 목록에는 두 번 들어가고 citation은 나중 URL이 이긴다. | 실행 관찰 |
| T-09 | R-12 | JSON 정상이지만 learnings·질문이 모두 빈 배열 / 줄 형식 `"1. Learning [https://a.test]: Insight 1\n3. Question: What next?"` / `"Learning: stuff happened at https://example.com/api/v1?key=value"` | 빈 결과(줄 폴백도 없음) / learning `Insight 1`, citation `https://a.test`, 질문 `What next?` / learning `stuff happened at`, citation은 그 URL(URL을 본문에서 제거). 큰따옴표로 감싼 URL은 따옴표 두 개가 본문에 남는다(`see "" ok`). | 실행 관찰 |
| T-10 | R-18 | `trim_context_to_word_limit(항목 6/5/4단어, max_words=10)` / 3/20/2단어 / 3/20단어 / `[]` / 단어 0인 `""` + 2단어 | `[5단어, 4단어]` / `[2단어]`(가운데가 넘치면 그 앞을 모두 버림) / `[앞 10단어]`(마지막 항목이 단독 초과) / `[]` / `["", 2단어]`. dict 항목은 `str(dict)` 단어 수로 세고, 단독 초과면 `str(dict)`를 앞 N단어로 자른 문자열이 된다. | 실행 관찰 |
| T-11 | R-01~R-03, R-09, R-14, R-15 | 설정 3/2/4(Config 기본값과 같은 값), 질의 생성이 요청한 개수만큼 주는 가짜 | `deep_research` 호출은 (depth 2, breadth 3) 한 번 → 자식 (1, 2) 세 번, 중첩 연구자 9개, LLM 호출은 계획 1·질의 생성 4·학습 추출 9, 최대 동시 실행 3. | 실행 관찰 |
| T-12 | R-15 | breadth 4, depth 3 | 레벨 breadth 4 → 2 → 2, `deep_research` 호출 (3,4) 1회, (2,2) 4회, (1,2) 8회, 중첩 연구자 28개. depth 1이면 3개(breadth 3)이고 재귀가 없다. breadth 1, depth 2이면 자식 breadth 2. | 실행 관찰 |
| T-13 | R-14 | breadth 3, depth 1, concurrency 1 / 2 | 최대 동시 실행 1 / 2. | 실행 관찰 |
| T-14 | R-04, R-03 | 속성이 없는 `cfg` / `default.py`의 `DEEP_RESEARCH_*` | breadth 4, depth 2, concurrency 2 / 3, 2, 4. | 실행 관찰(앞) + 원본 파일을 `ast`로 읽음(뒤) |
| T-15 | R-05 | concurrency 0 / -1 / depth 0 | 1초 안에 끝나지 않음 / 질의 생성 뒤 `ValueError`("Semaphore initial value must be >= 0") / 한 레벨만 실행. | 실행 관찰 |
| T-16 | R-06, R-07, R-08 | retriever 두 개, 첫 번째가 예외, 질문 생성 LLM이 질문 0개 | 계획 검색은 두 retriever 모두 `max_results` 없이 호출, 첫 번째 실패는 경고 후 건너뜀, 질문이 0개여도 `deep_research`가 실행된다. 질문 2개일 때 질의 생성 프롬프트의 입력은 `Initial Query: …\nFollow - up Questions and Answers:\n\n        Q: …\nA: Automatically proceeding with research\nQ: …` 형태다. | 실행 관찰 |
| T-17 | R-11 | 첫 중첩 연구자의 생성 인자 | `report_type="research_report"`, `report_source="web"`, `headers`는 outer의 것, `visited_urls`는 outer의 집합 객체, `mcp_configs`·`mcp_strategy`는 outer 값, `query_domains` 등은 없음. | 실행 관찰 |
| T-18 | R-21 | 중첩 연구자 하나가 예외 / 학습 추출 LLM의 첫 호출이 예외 | 그 질의의 학습·컨텍스트만 빠지고 나머지는 결과에 들어간다. | 실행 관찰 |
| T-19 | R-16, R-20 | 모든 중첩 연구자가 예외(breadth 2, depth 3) | 중첩 연구자는 2개뿐이고 `deep_research`는 한 번, 재귀 없음. `run()`은 `""`를 반환, `researcher.context == ""`, `researcher.visited_urls`는 빈 set(공유 집합과 다른 객체). 중첩 조사는 성공했는데 학습 추출이 모두 실패한 경우도 공유 집합에 URL이 있지만 outer는 빈 set이 된다. | 실행 관찰 |
| T-20 | R-13, R-20 | 최상위 질의 생성이 빈 목록 | 중첩 연구자 0개, `run()`은 `""`. | 실행 관찰 + 원본 테스트 열람(`tests/skills/test_deep_research_zero_queries.py`, 실행 안 함) |
| T-21 | R-24 | 두 번째 레벨의 질의 생성 LLM 호출(전체 두 번째 호출)이 예외 | `run`이 그 예외를 던진다. `researcher.context`는 초기값 그대로(`[]`), `research_sources`는 `[]`, 공유 `visited_urls`에는 첫 레벨 중첩 연구자의 URL만 남는다. | 실행 관찰 |
| T-22 | R-12 | 중첩 연구자가 `[]`를 돌려줌(breadth 2) | 학습 추출 LLM은 질의 수만큼 호출되고 프롬프트의 `Research results:` 뒤가 `\n[]`이다. 학습 줄은 LLM이 낸 값으로 만들어진다. | 실행 관찰 |
| T-23 | R-19, R-25 | 두 질의가 같은 learning 텍스트를 내고 각자 다른 URL을 citation으로 줌 | 최종 문자열에는 그 learning 줄이 한 번만, 나중 질의의 URL로 붙는다. `researcher.visited_urls`는 중복 없는 list. | 실행 관찰 |
| T-24 | R-17, R-18, R-19 | 중첩 컨텍스트 3개 × 12,000단어 / 2개 × 12,498단어 + 학습 줄 2개(줄당 5단어) | 첫째: 레벨 끝 자르기가 맨 앞 컨텍스트를 버려 뒤 2개가 남고 학습 줄 3개도 남는다(24,015단어). 둘째: 최종 자르기가 학습 줄을 모두 버리고 컨텍스트 2개(24,996단어)만 남는다. | 실행 관찰 |
| T-25 | R-19 | 정상 결과 | 최종 문자열의 각 학습 줄이 `learning about Q1.1 [Source: https://src.test/Q1.1]` 형식이고 순서는 일정하지 않다. | 실행 관찰 |
| T-26 | R-23 | breadth 2, depth 2, concurrency 1, 복사해 기록하는 콜백 | 레벨마다 객체가 다르다(부모 P0는 total_depth 2, 자식 P1·P2는 total_depth 1·current_depth 1). 한 레벨의 순서: (1,2,0,2,0,0,None) → 질의 1 시작 → 질의 1 성공(completed 1) → 질의 2 시작 → 질의 2 성공(completed 2) → 끝 알림(같은 값). 총 18회, 객체 3개. `async` 콜백은 await되지 않는다(경고 6건). | 실행 관찰 |
| T-27 | R-23, R-21 | 콜백이 `p.current_query == "Q1.1"`일 때 예외 / 레벨 시작 알림에서 예외 | 앞은 Q1.1만 결과에서 빠지고 계속 / 뒤는 `run`이 `ValueError`를 던진다. | 실행 관찰 |
| T-28 | R-22 | 위 정상 실행의 가짜 outer | outer `add_costs` 호출 없음, LLM 호출에 `cost_callback` 없음, `deep_research_costs` 이벤트의 `research_costs`는 `0.0`. | 실행 관찰(가짜 outer) |
| T-29 | R-02 | `report_type="deep"`으로 `conduct_research()` | `choose_agent`와 일반 파이프라인을 부르지 않고 `run()`의 문자열이 반환·저장된다. | 구현에서 도출(코드 확인, 실행 안 함) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

문서와 구현의 차이:
- **기본값 표기**: 구현(`default.py:40-42`)은 3/2/4다. `docs/.../config.md:133-135`도 3/2/4로 구현과 같다. 그러나 `docs/docs/gpt-researcher/gptr/deep_research.md:52-54, 61-63`은 breadth 4(concurrency 4)로, `backend/report_type/deep_research/README.md:50-52`와 `.claude/references/config-reference.md:110-112`는 4/2/2로 적고, 스킬 안의 `getattr` 기본값도 4/2/2다. 4/2/2는 `example.py:36-42`의 기본 인자(`breadth=4`, `depth=2`, `concurrency_limit=2`)와 같은 값이라 거기서 온 것으로 보이지만(추론) 실제 `Config`에서는 적용되지 않는다(R-03).
- **README의 "Failed queries are automatically skipped"**는 질의 단위 실패에만 맞고(R-21), 질의 생성·계획 LLM 실패는 전체 실패다(R-24).
- **`ResearchProgress` 해설**(README: "current_breadth: Current number of parallel paths")과 달리 `current_breadth`는 완료한 질의 수(성공)다(R-12, R-23).
- 코드 주석(`deep_research.py:528-530`)은 `CURATE_SOURCES`일 때 `result['context']`가 `List[dict]`라고 쓰지만, 중첩 컨텍스트는 문자열이거나 `[]`다(`researcher.py:219-229`, `:404-408`). 그래서 리스트-dict 분기는 이 경로에서 쓰이지 않는다(추론).

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `agent.py:186-193`(C-14), `deep_research.py:250-263`(C-08) | 정적 읽기. |
| R-02 | `agent.py:343-365`, `:415-461`, `:323-341` `_log_event`(로그 핸들러 없으면 이벤트 없음) | 정적 읽기. `agent.py`를 import하지 못해 실행하지 않았다. `choose_agent`가 건너뛰어지는 것은 분기 위치(`:363-365`)가 `:367-381`보다 앞이라는 점으로 확인했다. |
| R-03 | `config/config.py:63-67`(모든 키를 소문자 속성으로 설정), `:253-278` `convert_env_value`, `variables/default.py:39-42`, `variables/base.py:38-40`(타입 int) | 정적 읽기. `Config`를 실제로 만들어 보지 못했다(langchain 의존). 설정 JSON이 키를 덮는 것은 `load_config`의 `merged_config.update`(`config.py:170-173`)를 읽었다. |
| R-04 | `deep_research.py:253-255`, 실행 기록 [recursion_demo.out.txt](../../../artifacts/gpt-researcher/deep-research-demos/recursion_demo.out.txt) "B." | 속성을 지운 단순 객체로 `DeepResearchSkill`을 만들어 출력(4 2 2). `default.py` 값은 `ast`로 파일을 읽어 출력(3, 2, 4). |
| R-05 | `deep_research.py:432`(세마포어), `:540-541`, 실행 기록 "H." | 가짜 LLM으로 실행. `breadth=0`은 질의 생성 응답을 `[:num_queries]`로 자르는 코드(`:99`, `:122`)에서 도출(실행하지 않음). |
| R-06 | `deep_research.py:300-313`, `actions/query_processing.py:44-81`, `retrievers/tavily/tavily_search.py:108`·`duckduckgo/duckduckgo.py:37`·`custom/custom.py:33`(기본 `max_results`) | 어댑터 기본값은 `def search(self, max_results=…)` 줄을 읽었다. 실행 기록 "A1."(`max_results=None`), "C5."(retriever 예외 건너뜀)는 가짜 retriever. `get_search_results`는 `query_domains`를 변환하지 않고 그대로 어댑터에 넘긴다(`query_processing.py:74`). |
| R-07 | `deep_research.py:316-350`, `utils/llm.py:120-162` | 프롬프트는 읽기만 했다(실행 안 함). 파서는 T-06. LLM 실패 전파는 `generate_research_plan`에 `try`가 없고 `run`에도 없음을 읽었고, 실행 기록 "C4."는 질의 생성 쪽에서 같은 전파를 확인했다. |
| R-08 | `deep_research.py:594-600`, 실행 기록 "A1."의 프롬프트 출력, "C5." | 가짜 LLM이 받은 프롬프트를 출력해 철자(`Follow - up`)와 형식을 확인했다. |
| R-09 | `deep_research.py:397-420`, 실행 기록 "E." | 실행. |
| R-10 | C-02, C-03, 실행 기록 [parsers_demo.out.txt](../../../artifacts/gpt-researcher/deep-research-demos/parsers_demo.out.txt) §1 | JSON 복구는 확인 한계(M-01). 후보 순서는 정적 읽기. 정규식 후보 `[...]`가 `Here: [...] thanks` 같은 문장 속 배열을 읽는 사례는 엄격 `json.loads` 가짜로 실행했다. |
| R-11 | `deep_research.py:434-467`, `agent.py:138-196`(생성자가 `Config(config_path)`를 새로 만들고 `query_domains or []` 등을 기본으로 둠), `backend/report_type/basic_report/basic_report.py:62-64`(outer `cfg`만 덮음), `agent.py:398-411`(중첩 연구자의 이미지 사전 생성) | 인자 목록은 실행 기록 "A1."에서 가짜 생성자가 받은 키로 확인. 나머지는 정적 읽기. 중첩 `GPTResearcher`의 실제 동작은 research-pipeline 스펙이 맡는다. |
| R-12 | `deep_research.py:463-483`, 실행 기록 "G."(`'\n[]'`), "E." | 중첩 컨텍스트가 `[]`가 되는 경로는 `researcher.py:404-408`(research-pipeline 스펙 R-25). |
| R-13 | `deep_research.py:416-429`, 실행 기록 "C5.", 원본 테스트 `tests/skills/test_deep_research_zero_queries.py` | 테스트는 읽기만(실행 안 함). |
| R-14 | `deep_research.py:431-435`, `:492-495`, 실행 기록 "A4." | 가짜 `conduct_research`에 `sleep`을 넣어 동시 실행 수를 쟀다. |
| R-15 | `deep_research.py:522-568`, 실행 기록 "A1.", "A2.", "H." | 레벨 호출 순서와 중첩 연구자 수를 셌다. |
| R-16 | `deep_research.py:497-520`, 실행 기록 "C2.", "C2b.", 원본 테스트 `tests/skills/test_deep_research_empty_results.py`(읽기만) | 실행. 이슈 번호(#1579)는 코드 주석 인용이고 외부 확인은 하지 않았다. |
| R-17 | `deep_research.py:570-584`, 실행 기록 "D2." | 실행. `learnings` 순서가 무작위인 것은 `list(set(…))`(`:579`)에서 도출. |
| R-18 | C-06, 실행 기록 [parsers_demo.out.txt](../../../artifacts/gpt-researcher/deep-research-demos/parsers_demo.out.txt) §4, 원본 테스트(읽기만) | 실행. |
| R-19 | `deep_research.py:619-641`, 실행 기록 "A1.", "D1.", "D3." | 실행. dict 분기는 정적 읽기. |
| R-20 | `deep_research.py:642-655`, `:423-429`, `:514-520`, 실행 기록 "A1."(list), "C2.", "C2b."(set) | 실행. |
| R-21 | `deep_research.py:485-495`, 실행 기록 "C1.", "C3.", "F." | 실행. 취소 전파는 `except Exception`이라는 점에서 도출(실행 안 함). |
| R-22 | `deep_research.py:287-294`, `:341-348`, `:373-382`(`cost_callback` 인자 없음), `:592`, `:610-617`, `agent.py:761-806`(`get_costs`·`add_costs`), `utils/llm.py:147-157`(콜백이 있을 때만 비용 계산), `add_costs`·`cost_callback` 검색(`skills/deep_research.py`, `retrievers/`, `mcp/`에 없음) | 비용이 0이라는 판단은 호출 경로에서 outer `add_costs`로 가는 길이 없다는 점(정적)과 가짜 outer의 실행 기록 "A1."로 확인. outer 비용이 다른 경로(예: 호출자가 `add_costs`를 부름)로 바뀌면 `research_costs`는 그 차이가 된다. 실제 비용 계산식은 LLM 스펙 범위로 확인하지 않았다. |
| R-23 | C-07, `deep_research.py:413-414`, `:437-439`, `:469-473`, `:497-500`, `:540-543`, 실행 기록 "E.", "F.", `backend/report_type/basic_report/basic_report.py:72-75`, `backend/server/websocket_manager.py:162-178`, `backend/report_type/deep_research/main.py:8-23` | 실행. 서버 경로는 `conduct_research()`를 인자 없이 부르는 줄을 읽었다. |
| R-24 | `deep_research.py:418`, `:552-560`(자식 호출이 `try` 밖), `:594`, `:602`, `:432`, 실행 기록 "C4.", "F.", "H." | 실행. |
| R-25 | `deep_research.py:260`, `:450`, `:460`, `:525`, `:558`, `agent.py:161`, `skills/researcher.py:108-112`, `:813-834`(retrievers C-08), 실행 기록 "A1."(visited 10개 = 질의 9 + 공유 1), "D1." | 실행. 공유 집합이 같은 객체인 점은 가짜 생성자가 `kw["visited_urls"]`를 그대로 쓰도록 만든 것이라 실제 `GPTResearcher`의 동일 동작(`agent.py:161`)은 정적 읽기. |
| R-26 | `backend/report_type/deep_research/main.py:1-33`, `example.py:1-60`, `grep`(`deep_research.example`·`report_type.deep_research`를 import하는 곳 없음) | 정적 읽기. |
| T-01~T-10 | 실행 기록 `parsers_demo.out.txt` | 실행. 대체물: `json_repair`(엄격한 `json.loads`). |
| T-11~T-28 | 실행 기록 `recursion_demo.out.txt` | 실행. 대체물: LLM, 검색, 중첩 `GPTResearcher`, outer. |
| T-05, T-20(테스트 부분) | `tests/test_deep_research_parsing.py:119-135`, `tests/skills/test_deep_research_zero_queries.py` | 테스트를 읽은 것은 실행 확인이 아니다. |
| T-29 | `agent.py:343-365` | 정적 읽기. |

### 2.2 코드 읽는 순서

1. `agent.py:186-193`(스킬 생성), `:343-365`·`:415-461`(분기와 이벤트).
2. `skills/deep_research.py:586-655` `run`(계획 → 재귀 → 조립) → `:386-584` `deep_research`(레벨 처리) → `:265-384`(LLM 호출 3종) → `:20-237`(파서와 자르기).
3. `config/variables/default.py:39-42`, `config/config.py:63-67`(설정이 어떻게 속성이 되는지).

원본의 구현 전략: 재귀는 `await` 순차로 내려가고 한 레벨 안의 질의만 `gather`로 병렬이다. 조사 결과를 두 가지로 모은다 — 짧은 learning 목록(출처 맵 포함)과 질의별 컨텍스트 원문 조각. 최종 컨텍스트는 learning 줄을 앞에 두고 원문 조각을 뒤에 둔다. 단어 수 제한은 뒤쪽 우선이라 학습 줄이 먼저 잘리고, 세 LLM 응답 파서는 JSON → 줄 형식 순으로 내려가는 같은 패턴이다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다(데모 스크립트는 원본 파일을 `import`해 실행할 뿐 복사본을 두지 않았다).

## 적용 메모

없음.
