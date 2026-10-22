---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - backend/report_type/detailed_report/detailed_report.py
  - backend/report_type/detailed_report/README.md
  - backend/server/websocket_manager.py
  - backend/server/app.py
  - cli.py
  - gpt_researcher/agent.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/context/compression.py
  - gpt_researcher/context/lexical.py
  - gpt_researcher/context/retriever.py
  - gpt_researcher/actions/markdown_processing.py
  - gpt_researcher/actions/report_generation.py
  - gpt_researcher/utils/llm.py
  - gpt_researcher/utils/validators.py
  - gpt_researcher/utils/enum.py
  - gpt_researcher/prompts.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
depends:
  - ../capabilities/research-pipeline.md
  - ../capabilities/report-writing.md
status: ready
reimplementation: 미실행
---

# 상세 보고서

> 질문 하나를 받아 초기 연구로 하위 주제(서브토픽) 목록을 LLM에게 만들게 한 뒤, 하위 주제마다 새 `GPTResearcher`를 순차로 돌려 쓴 보고서 조각을 서론·목차·본문·결론·참고문헌 순서의 마크다운 문자열 하나로 이어 붙인다.

<!--
용어. 서브토픽 = 상세 보고서가 질문에서 뽑아내는 하위 주제 하나(`{"task": 문자열}`). 서브토픽 연구기 = 서브토픽마다 새로 만드는 `GPTResearcher`(`report_type="subtopic_report"`). 주 연구기 = `DetailedReport`가 생성자에서 만드는 `GPTResearcher`(초기 연구·서론·결론을 맡음). 컨텍스트 = 연구 파이프라인이 돌려주는 문자열(못 모으면 빈 리스트 `[]`, research-pipeline R-25). 고정 문장 = 컨텍스트가 비었을 때 보고서 대신 나오는 "I could not gather any source material ..." 문장(report-writing R-03). 헤더 트리(HeaderNode) = `extract_headers`가 만드는 `{level, text, children?}`(report-writing 1.3). 섹션(Section) = `extract_sections`가 만드는 `{section_title, written_content}`.
검증 방법. 순수 로직과 조립은 오프라인 데모 `artifacts/gpt-researcher/detailed-report-demos/demo_detailed_report.py`(출력 `demo_detailed_report.out`, 104개 검사 통과)로 실행했다. 데모는 실제 `DetailedReport` 클래스를 불러 쓰되 `GPTResearcher`는 호출 순서·인자를 기록하는 가짜로 바꿨다(그래서 연구·LLM·검색 내용은 검증하지 않고, `DetailedReport`가 무엇을 넘기고 결과로 무엇을 하는지만 검증한다). 대체 범위는 1.4 확인 한계와 2.1 "확인 방법"에 적었다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`DetailedReport(query="Q", report_type="detailed_report", report_source="web")`를 만들고 `await run()`을 부르는 경우다.

1. 생성자가 주 연구기 `GPTResearcher(report_type="research_report", ...)` 하나를 만든다. 인자로 받은 `report_type`은 저장만 한다.
2. 초기 연구: 주 연구기의 `conduct_research()`를 한 번 돌린다. 결과 컨텍스트를 `global_context`에, 연구기의 `visited_urls`(이미 본 URL 집합, 같은 객체)를 `global_urls`에 담는다.
3. 하위 주제 목록: 주 연구기의 컨텍스트를 자료로 LLM에게 `{"subtopics": [{"task": ...}, ...]}` 형식 JSON을 쓰게 하고 `[{"task": 문자열}, ...]`로 바꾼다. 개수 상한은 프롬프트 문장뿐이다. 실패하거나 비어 있으면 서브토픽 0개로 계속한다.
4. 서론: 주 연구기가 초기 컨텍스트만으로 서론을 쓴다. 서브토픽 보고서보다 먼저 쓴다.
5. 서브토픽을 목록 순서대로 하나씩(병렬 아님) 처리한다. 하나당 새 서브토픽 연구기를 만들어 연구하고(`visited_urls`는 모두가 같은 객체를 공유), 초안 제목을 LLM에게 쓰게 한 뒤(결과는 실제로 쓰이지 않는다), 앞서 쓴 섹션 중 비슷한 것(질의는 서브토픽 task 하나뿐)을 찾고, 지금까지의 헤더 트리와 함께 `write_report`에 넘겨 조각을 쓴다. 조각이 비어 있지 않으면 본문에 `"\n\n\n" + 조각`으로 이어 붙이고, 조각 안의 헤더와 섹션을 전역 상태에 쌓는다.
6. 조립: 목차는 본문만으로 만들고, 결론은 본문을 읽고 쓰고, 참고문헌은 결론 뒤에 붙인다. `서론 + "\n\n" + 목차 + "\n\n" + 본문 + "\n\n" + (결론 + 참고문헌)`이다.
7. 그 문자열을 반환한다. `DetailedReport` 안에는 `try`가 없어서 연구 단계의 예외는 `run()` 밖으로 나가고 부분 결과는 남지 않는다.

### 1.2 범위·통합 지점

- 제공: 하위 주제 목록 만들기(`get_subtopics`), 서브토픽 연구기 생성과 순차 실행, 서브토픽 사이의 중복 방지 입력(헤더 트리와 비슷한 이미 쓴 섹션), 최종 문자열 조립, 이 경로 전용의 비슷한 섹션 검색(`WrittenContentCompressor`와 키워드 대체 `rank_written_sections`), 전역 상태 갱신 규칙.
- 제외:
  - 개별 연구기가 하는 연구(검색·스크랩·선별)는 [research-pipeline.md](research-pipeline.md), 보고서·서론·결론·초안 제목의 프롬프트와 LLM 호출·마크다운 순수 함수 4개는 [report-writing.md](report-writing.md)가 정한다. 이 스펙은 그 함수를 어떤 인자로 언제 부르고 결과를 어디에 쓰는지만 정한다.
  - 소스 모드의 분기(`documents`, `document_urls`, `source_urls` 처리)는 source-modes 스펙이다. 이 스펙은 `DetailedReport`가 무엇을 넘기고 넘기지 않는지만 쓴다(R-12, R-34).
  - LLM 제공자·`Config` 로딩·임베딩 모델 생성은 범위 밖이다(사용자 제외). 설정 키는 원문 이름만 쓰고, 임베딩 모델을 만드는 `Memory.get_embeddings()`는 "성공하면 임베딩 객체, 예외를 낼 수 있음"이라는 경계로만 본다.
  - 서버(`backend/server/websocket_manager.py`)와 CLI(`cli.py`)는 이 클래스를 부르는 방식만 쓴다(R-32, R-33). 이미지 생성은 범위 밖이다(사용자 제외).
  - `backend/memory/draft.py`의 `DraftState`와 `backend/memory/research.py`의 `ResearchState`(둘 다 `TypedDict`)는 이 경로에서 쓰이지 않는다. `backend/` 안에 이 모듈을 가져오는 곳이 없다(Grep `backend.memory`, `memory.draft`). `multi_agents/memory/draft.py`에 필드가 조금 더 많은 같은 이름의 정의가 따로 있고 그것을 `multi_agents/agents/editor.py:9`가 쓴다. 상세 보고서의 상태는 `DetailedReport`의 필드(1.2)뿐이다.
- 외부 의존·선행 계약:

  | 대상 | 이 스펙이 주는 입력 | 정상 결과 | 실패 시 이 스펙이 보는 것 |
  |---|---|---|---|
  | `GPTResearcher.conduct_research()` (research-pipeline) | 생성자 인자(R-02, R-12) | 컨텍스트(`str`, 없으면 `[]`)가 `researcher.context`에, URL이 `visited_urls`에 쌓임 | 초기 검색·서브쿼리 계획 단계의 예외는 그대로 전파(research-pipeline R-09~R-11). 서브쿼리 안의 실패는 빈 결과로 삼켜짐 |
  | `GPTResearcher.write_report(existing_headers, relevant_written_contents)` | 헤더 트리 목록, 비슷한 섹션 문자열 목록 | 서브토픽 조각 문자열 | LLM 실패는 `""`, 컨텍스트가 비면 고정 문장, 프롬프트 생성 예외는 전파(report-writing R-03, R-17, R-18) |
  | `write_introduction()`, `write_report_conclusion(body)`, `get_draft_section_titles(task)` | 인자 없음 / 본문 / task | `str` / `str` / `list[str]` | LLM 실패는 `""` / `""` / `[]`(report-writing R-24~R-26) |
  | `extract_headers`, `extract_sections`, `table_of_contents`, `add_references` | 조각·본문·URL 집합 | HeaderNode 목록 / Section 목록 / 목차 문자열 / 참고문헌이 붙은 문자열 | report-writing R-27~R-30 |
  | LLM 호출(`construct_subtopics`) | 아래 R-07 | `Subtopics` 객체 | 어떤 예외든 로그만 남기고 입력 `subtopics` 리스트를 반환(R-09) |
  | 임베딩 모델(`researcher.memory.get_embeddings()`) | 인자 없음 | 임베딩 객체 | 예외면 키워드 순위로 대체(R-18) |
  | `websocket` | `await send_json(dict)`를 가진 객체 | 이벤트 전달 | 이 클래스는 전송 오류를 잡지 않음 |
- 소유 상태·부작용(모두 `DetailedReport` 인스턴스의 필드이며 한 번의 `run()`을 위한 것이다):
  - `gpt_researcher`: 주 연구기. 생성자에서 한 번 만든다.
  - `existing_headers`(list): 서브토픽마다 `{"subtopic task", "headers"}` 한 개씩 쌓인다.
  - `global_written_sections`(list): 지금까지 쓴 보고서의 섹션이 문서 순서로 쌓인다.
  - `global_urls`(set): 주 연구기의 `visited_urls`와 같은 객체다. 모든 서브토픽 연구기도 같은 객체를 쓴다.
  - `global_context`(list): 쓰기만 하고 연구·작성 입력으로는 어디서도 읽히지 않는다(R-14).
  - `research_id`: 만들기만 하고 어디서도 읽지 않는다.
  - 외부 자원: LLM API, 검색·스크랩 대상, 임베딩 API(설정된 경우), websocket 메시지. 서브토픽 연구기는 `run()`이 끝나면 버려진다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `DetailedReport(query, report_type, report_source, source_urls=[], document_urls=[], query_domains=[], config_path=None, tone="", websocket=None, subtopics=[], headers=None, complement_source_urls=False, mcp_configs=None, mcp_strategy=None, max_search_results=None)` | `query: string`, `report_type: string`, `report_source: string`(앞 셋은 필수), 나머지는 선택 | `report_type`은 `self.report_type`에 저장만 한다(주 연구기는 항상 `"research_report"`). `headers`는 `headers or {}`. 기본값 `[]`은 호출 사이에 공유되는 같은 리스트 객체다. `documents`, `vector_store`, `verbose`, `log_handler` 인자는 없다. `subtopics`는 서브토픽 연구기에만 전달되고 쓰이지 않는다(R-10). 동기 생성자이며 여기서 주 연구기가 만들어진다. |
| `run()` | → `string` | 비동기. 완료할 때까지 중간 결과를 돌려주지 않고 취소 기능도 없다. 예외는 R-27. |
| 서브토픽 항목 | `{"task": string}` | `Subtopic.task`는 `min_length=1`이다. 순서는 LLM이 낸 순서다. |
| `Subtopics`(LLM이 쓰는 JSON) | `{"subtopics": [{"task": string(1자 이상)}, ...]}` | `subtopics` 키가 없으면 빈 목록이 기본값이다. 다른 필드는 없다. |
| `existing_headers` 항목 | `{"subtopic task": string, "headers": list[HeaderNode]}` | 서브토픽 하나가 끝날 때마다 하나 추가한다. 프롬프트에는 파이썬 리스트 표기(작은따옴표 dict)로 그대로 들어간다(R-23). 조각이 비면 `headers`는 `[]`다. |
| `relevant_written_contents` | `list[string]`, 각 원소 `"Title: {section_title}\nContent: {내용}\n"` | 프롬프트에는 파이썬 표기로 들어가 줄바꿈이 두 글자 `\n`이 된다. 최대 10개이고 첫 서브토픽에서는 `[]`다. |
| `global_written_sections` | `list[Section]` | 서브토픽 조각마다 `extract_sections`의 결과를 순서대로 `extend`한다. 본문이 빈 섹션(바로 아래에 하위 헤더만 오는 헤더)은 들어가지 않는다. |
| `global_context` | `list[string]` | `_hashable_context`의 결과를 `set`으로 거른 리스트(순서 없음). 컨텍스트가 `str`이면 글자 하나씩이 원소가 된다(R-14). |
| `Subtopics` 생성 호출 `construct_subtopics(task, data, config, subtopics=[], prompt_family, **kwargs)` | `task=주 연구기 query`, `data=주 연구기 context`, `subtopics=주 연구기 subtopics(항상 [])` → `Subtopics` 또는 입력 `subtopics` 리스트 | 성공하면 pydantic 객체, 실패하면 입력 리스트를 돌려준다(둘의 타입이 다르다). 비용 콜백이 없고 재시도도 없다(LLM 호출을 `create_chat_completion`이 아니라 langchain 체인으로 한다). |

설정 키(환경변수가 같은 이름의 설정값을 덮어쓴다: `config/config.py:63-67`). 모두 원문 이름이다.

| 키 | 기본값 | 이 스펙에서의 쓰임 |
|---|---|---|
| `MAX_SUBTOPICS` | `3` | `config.max_subtopics`. 서브토픽 프롬프트의 "Limit the number of subtopics to a maximum of N"에만 들어간다. 코드가 목록을 자르지 않는다. `GPTResearcher(max_subtopics=5)` 인자는 저장만 하고 쓰이지 않는다(R-08). |
| `SMART_LLM` / `SMART_TOKEN_LIMIT` / `TEMPERATURE` | `"openai:gpt-5.4"` / `12000` / `0.4` | `construct_subtopics`의 모델, `max_tokens`, `temperature`(추론 모델이면 `temperature` 대신 `reasoning_effort="high"`). `config.llm_kwargs`가 있으면 합쳐진다. |
| `MAX_SEARCH_RESULTS_PER_QUERY` | `5` | `DetailedReport(max_search_results=...)`가 주 연구기와 모든 서브토픽 연구기의 `cfg.max_search_results_per_query`를 `int()`로 덮어쓴다(R-13). |
| `CONFIG_PATH`(환경변수) | 없음 | 주 연구기는 `config_path` 인자를, 서브토픽 연구기는 인자 없이 이 환경변수를 본다(R-12). |
| `DOC_PATH` | `"./my-docs"` | `hybrid`에서 서브토픽 연구기가 문서를 읽는 폴더(R-34). |
| `SIMILARITY_THRESHOLD` | `0.35` | 이 경로에서는 쓰이지 않는다. 비슷한 섹션 검색의 임계값은 코드에 `0.5`로 고정이다(R-17). |

진행 이벤트: `DetailedReport` 자체는 이벤트를 보내지 않는다. 주 연구기와 서브토픽 연구기가 같은 `websocket` 객체로 `{"type", "content", "output", "metadata"}`를 보낸다(R-30).

### 1.4 행동 규칙과 남은 질문

생성과 구성

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `DetailedReport(...)` 생성 | 인자를 `self.query`, `report_type`, `report_source`, `source_urls`, `document_urls`, `query_domains`, `config_path`, `tone`, `websocket`, `subtopics`, `complement_source_urls`, `max_search_results`에 그대로 저장하고 `headers`는 `headers or {}`로 저장한다. `research_id`(`"detailed_{초}_{md5(query)[:8]}"`)를 만들지만 어디서도 읽지 않는다. `report_type` 인자는 어디서도 읽지 않는다. `source_urls`·`document_urls`·`query_domains`·`subtopics`의 기본값 `[]`은 호출마다 새로 만들지 않아 인스턴스 사이에서 같은 리스트 객체다(데모는 `source_urls`로 확인). 이 클래스는 그 리스트를 바꾸지 않으므로 지금은 문제가 없다. | 실행 확인 (실제 `DetailedReport`, 가짜 연구기) |
| R-02 | 주 연구기 생성 | `GPTResearcher`를 정확히 다음 키로 만든다: `query`, `query_domains`, `report_type="research_report"`(하드코딩이라 인자 `report_type`과 무관), `report_source`, `source_urls`, `document_urls`, `config_path`, `tone`, `websocket`, `headers`, `complement_source_urls`. `mcp_configs`와 `mcp_strategy`는 `None`이 아닐 때만 키로 넣는다. `documents`, `vector_store`, `subtopics`, `agent`, `role`, `visited_urls`, `verbose`, `log_handler`, `parent_query`는 넘기지 않는다. 그래서 주 연구기는 `verbose=True`, `log_handler=None`, 새 `visited_urls` 집합, 비어 있는 `subtopics`를 갖는다. `tone`이 `Tone`이 아니면(기본 `""` 포함) 연구기 쪽에서 `Tone.Objective`가 된다(`agent.py:146`). | 실행 확인 (키 집합), 코드 확인 (`Tone` 변환) |
| R-03 | 전역 상태 초기값 | `existing_headers=[]`, `global_context=[]`, `global_written_sections=[]`, `global_urls = set(source_urls)`(`source_urls`가 truthy일 때, 아니면 빈 set)이다. 이 `global_urls`는 `run()`의 초기 연구가 끝나면 주 연구기의 `visited_urls`로 교체되므로 `run()`을 거치면 초기 시드는 남지 않는다(R-06). | 실행 확인 |
| R-13 | `max_search_results`가 `None`이 아님 | 주 연구기 생성 직후와 서브토픽 연구기마다 생성 직후(연구 전)에 `cfg.max_search_results_per_query = int(max_search_results)`를 한다. `int()`가 실패하는 값(`"abc"`)은 `ValueError`가 되어 생성자(주 연구기) 또는 서브토픽 처리 중 밖으로 나간다. `None`이면 `MAX_SEARCH_RESULTS_PER_QUERY` 설정값(기본 5)을 그대로 쓴다. 이 값은 연구 단계의 모든 검색 호출이 읽는다(research-pipeline 1.3). | 실행 확인 (스텁), 코드 확인 (`int()` 오류 위치) |

실행 순서

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-04 | `run()` | 다음 순서로 실행하고 앞 단계가 끝나야 다음 단계를 시작한다: ① 초기 연구 ② 서브토픽 목록 ③ 서론 ④ 서브토픽 보고서들 ⑤ `gpt_researcher.visited_urls.update(global_urls)`(같은 객체라 변화 없음, R-21) ⑥ 조립. 서론(③)은 서브토픽 보고서보다 먼저 쓰이므로 서브토픽의 내용을 보지 않고 주 연구기의 초기 컨텍스트만 본다. 결론(⑥)이 본문을 본다. | 실행 확인 (호출 순서 기록), 코드 확인 |
| R-05 | 서브토픽 목록 처리 | `for subtopic in subtopics: await _get_subtopic_report(subtopic)`로 한 번에 하나씩 처리한다. 병렬이 아니다. 서브토픽 하나의 연구·초안 제목·검색·작성이 모두 끝난 뒤에야 다음 서브토픽 연구기를 만든다. 따라서 뒤 서브토픽은 앞 서브토픽이 쌓은 `visited_urls`·`existing_headers`·`global_written_sections`를 본다. (서브토픽 하나 안의 서브쿼리는 연구 파이프라인이 병렬로 돌린다: research-pipeline R-17.) | 실행 확인 (await가 양보하는 가짜 연구기에서도 순서 유지), 코드 확인 |
| R-06 | 초기 연구 | 주 연구기의 `conduct_research()`를 한 번 `await`한다. 그 뒤 `global_context = 주 연구기.context`(`str` 또는 `[]`)와 `global_urls = 주 연구기.visited_urls`(같은 객체)로 둔다. 예외는 잡지 않아 `run()`이 그 예외로 끝나며 서브토픽·서론은 시작하지 않는다. 연구기가 에이전트·역할을 고르는 일도 여기서 일어난다(research-pipeline R-02). | 실행 확인, 코드 확인 |

하위 주제 목록

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | `_get_all_subtopics` → `gpt_researcher.get_subtopics()` | `verbose`면 `logs/generating_subtopics`, 호출, `logs/subtopics_generated` 이벤트를 보낸다. 호출은 `construct_subtopics(task=주 연구기.query, data=주 연구기.context, config=주 연구기.cfg, subtopics=주 연구기.subtopics, prompt_family=주 연구기.prompt_family, **주 연구기.kwargs)`다. 주 연구기는 `subtopics`를 받지 않으므로 `subtopics`는 항상 `[]`이다. 초기 컨텍스트가 `[]`여도(예: R-33) LLM은 호출된다(`data`가 `"[]"`로 들어간다). 이 호출은 비용 콜백이 없어 비용이 기록되지 않는다. | 실행 확인 (스텁 LLM), 코드 확인 (이벤트·인자) |
| R-08 | 하위 주제 생성 LLM 호출 | 프롬프트는 C-08의 문장(주제, 자료, 가능한 하위 주제 목록, "중복 없이", "최대 `{max_subtopics}`개", 순서 지시, "모든 하위 주제는 주제와 자료에 관련된 것만")과 langchain `PydanticOutputParser(Subtopics)`의 형식 안내를 합친다. `max_subtopics`는 `config.max_subtopics`(`MAX_SUBTOPICS`, 기본 3)다. 모델은 `SMART_LLM`, `max_tokens=SMART_TOKEN_LIMIT`, 추론 모델이면 `reasoning_effort="high"`, 아니면 `temperature=TEMPERATURE`, `config.llm_kwargs`가 있으면 합친다. LLM 출력은 `Subtopics` JSON으로 파싱된다. 개수 상한은 프롬프트 문장일 뿐이라 코드는 목록을 자르지 않고 중복도 지우지 않으며, `DetailedReport`도 받은 목록 전체(예: 상한 3에 5개)를 서브토픽으로 처리한다. `GPTResearcher(max_subtopics=5)` 인자는 저장만 하고 쓰이지 않는다. | 실행 확인 (스텁 체인, 인자·렌더링·무절단), 코드 확인 (`max_subtopics` 인자 미사용은 Grep) |
| R-09 | 하위 주제 생성 실패 | `construct_subtopics`는 어떤 예외(LLM 오류, JSON 파싱 오류, `task`가 빈 문자열이라 검증 실패)도 잡아 오류 로그를 남기고 입력 `subtopics`(여기서는 `[]`)를 반환한다. `subtopics` 키가 없는 JSON은 예외가 아니라 빈 `Subtopics`가 된다. `_get_all_subtopics`는 반환값이 falsy이거나 `.subtopics`가 비면(`subtopics_data and subtopics_data.subtopics`) `print(f"Unexpected subtopics data format: {subtopics_data}")`를 하고 `[]`를 반환한다. 이후 `run()`은 멈추지 않고 서브토픽 0개로 서론·목차·결론·참고문헌까지 만든다(R-26). `subtopics_data`가 비어 있지 않은 리스트(실제로는 `DetailedReport`에서 일어날 수 없음, 주 연구기의 `subtopics`가 항상 `[]`)이면 `.subtopics` 속성이 없어 `AttributeError`다. | 실행 확인 (스텁), 코드 확인 (`AttributeError` 경로는 도달 불가) |
| R-10 | `DetailedReport(subtopics=...)` 인자 | 서브토픽 연구기의 `subtopics`로만 전달된다(R-12). 서브토픽 목록은 주 연구기의 `get_subtopics`에서만 만들어지고 주 연구기는 이 인자를 받지 않으므로, 이 인자는 서브토픽 목록에도 프롬프트의 "가능한 하위 주제 목록"에도 영향을 주지 않는다. | 실행 확인 (키 집합), 코드 확인 (`subtopics`를 읽는 곳은 `writer.py:220`뿐) |
| R-11 | 서론 | 주 연구기의 `write_introduction()`을 하위 주제 목록을 얻은 직후, 서브토픽 보고서 전에 한 번 부른다. 입력은 주 연구기의 초기 컨텍스트와 질문뿐이다(report-writing R-24). 컨텍스트가 비어도 호출된다. 실패하면 `""`이고 이 스펙은 그것을 서론으로 쓴다(R-26). | 실행 확인 (호출 순서·입력), 코드 확인 |

서브토픽 하나(`_get_subtopic_report`)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | 서브토픽 연구기 생성 | `GPTResearcher`를 정확히 다음 키로 만든다: `query=서브토픽 task`, `query_domains`, `report_type="subtopic_report"`, `report_source`, `websocket`, `headers`, `parent_query=원 질문`, `subtopics=self.subtopics`, `visited_urls=self.global_urls`(복사하지 않고 같은 set 객체), `agent=주 연구기.agent`, `role=주 연구기.role`(그래서 에이전트를 다시 고르지 않는다. research-pipeline R-02), `tone`, `complement_source_urls`, `source_urls`, `mcp_configs=주 연구기.mcp_configs`, `mcp_strategy=주 연구기.mcp_strategy`(생성자가 해석을 끝낸 문자열이라 MCP를 안 써도 기본 `"fast"`). 넘기지 않는 것: `document_urls`, `documents`, `vector_store`, `config_path`, `verbose`(기본 `True`), `log_handler`(`None`), `context`, `max_subtopics`. 효과: ① `config_path`가 없어 서브토픽 연구기의 `Config`는 `CONFIG_PATH` 환경변수나 기본값을 읽는다(서버는 두 곳 모두 같은 값이라 같은 설정이 되지만, 라이브러리 호출자가 환경변수 없이 `config_path`만 주면 서브토픽은 기본 설정을 쓴다). ② `document_urls`가 없어 `hybrid`에서 서브토픽은 `DOC_PATH` 폴더를 읽는다(R-34). ③ `websocket`·`headers`·`tone`은 주 연구기와 같은 값이다. | 실행 확인 (키 집합·객체 동일성), 코드 확인 (`Config` 효과) |
| R-14 | 서브토픽 연구기가 쓰는 컨텍스트 | `subtopic_assistant.context = list(set(_hashable_context(global_context)))`로 미리 채운 뒤 `conduct_research()`를 부르지만, `conduct_research`가 `self.context`를 자기 결과로 덮어쓴다(research-pipeline R-07). 따라서 서브토픽 연구는 이전 서브토픽이나 초기 연구의 컨텍스트를 이어받지 않는다. 서브토픽 사이에 공유되는 것은 `visited_urls`(이미 본 URL을 다시 안 가져옴)뿐이다. 서브토픽이 끝나면 `global_context = list(set(_hashable_context(서브토픽 연구기.context)))`로 바꾸지만 이 값은 다음 서브토픽의 선(先)설정에만 쓰이고 그것도 덮어써지므로 최종 결과에 영향이 없다. `_hashable_context`가 리스트의 원소를 문자열로 바꾸므로 컨텍스트가 `str`이면 한 글자씩 나뉜 리스트(중복 제거 후)가 된다(규칙은 C-03). 서브토픽 연구기는 `subtopic_report`라 서브쿼리 목록에 원 질문을 덧붙이지 않고 서브쿼리 프롬프트가 `"{parent_query} - {question}"` 형태를 쓴다(research-pipeline R-12, R-15). | 실행 확인 (`_hashable_context` 규칙, 글자 단위 분해, 사후 `global_context`), 코드 확인 (덮어쓰기: `agent.py:392`, `researcher.py:212`) |
| R-15 | 공유한 `visited_urls`가 연구에 미치는 효과 | 서브토픽 연구기는 이미 본 URL을 다시 스크랩하지 않는다(research-pipeline R-20). 그래서 한 서브토픽의 검색 결과가 모두 이미 본 URL이면 스크랩할 페이지가 없고 컨텍스트가 `[]`나 `""`가 되어, 그 서브토픽은 고정 문장을 조각으로 돌려준다(report-writing R-03). 특히 `source_urls`를 주고 `complement_source_urls`를 켜지 않으면 주 연구기가 그 URL들을 이미 방문 처리했으므로 서브토픽 연구기의 URL 경로는 새 URL이 없어 컨텍스트가 `""`가 되고 모든 서브토픽이 고정 문장이 된다. `complement_source_urls=True`이면 서브토픽 연구기가 그 task로 웹 검색을 한 번 더 한다. | 코드 확인 (연쇄: `researcher.py:145-162`, `:813-834`, `select.py:53-101`의 빈 목록 처리). 이 연쇄를 하나로 이어 실행하지는 않았다 |
| R-16 | 초안 제목 | 서브토픽 연구가 끝난 뒤 `subtopic_assistant.get_draft_section_titles(task)`를 부른다. 이 함수는 `list[str]`을 돌려주는데(report-writing R-26) 코드는 `str`이 아니면 `str(리스트)`로 바꾼 뒤 `extract_headers`를 적용하고 헤더 `text`만 모은다. `str(["### A", "### B"])`는 `"['### A', '### B']"`라서 `###`가 줄 처음에 없으므로 마크다운 헤더가 아니고, 결과는 항상 `[]`다(LLM 실패의 `[]`도 `"[]"`라 같다). 따라서 초안 제목은 LLM 호출 비용과 이벤트만 일으키고 이후의 어느 단계에도 영향을 주지 않는다. 초안 제목 프롬프트의 두 인자 `main topic`과 `subtopic`은 둘 다 서브토픽 task다(서브토픽 연구기의 `query`가 task이고 `parent_query`는 전달되지 않기 때문). 컨텍스트는 서브토픽 연구기 자신의 것이다. | 실행 확인 (실제 `extract_headers`, 가짜 연구기), 코드 확인 (프롬프트 인자) |
| R-17 | 비슷한 이미 쓴 섹션 찾기 호출 | `get_similar_written_contents_by_draft_section_titles(task, 헤더 text 목록(항상 []), global_written_sections)`를 `max_results=10`으로 부른다. 질의 목록은 `[task] + 제목 목록`이라 실제로는 `[task]` 하나다. 질의마다 `asyncio.gather`로 `__get_similar_written_contents_by_query(query, written_contents, **researcher.kwargs)`(`similarity_threshold=0.5`, `max_results=10`)를 실행하고 결과 리스트를 `set`으로 합쳐 `list(set)[:10]`을 돌려준다. 집합이라 중복이 사라지고 10개를 넘으면 어느 10개가 남는지는 순서 보장이 없다(문자열 해시에 달림). `verbose`면 질의마다 `logs/fetching_relevant_written_content`를 보낸다. 서브토픽 연구기의 `kwargs`는 항상 `{}`이다(`DetailedReport`가 여분 인자를 주지 않는다). 첫 서브토픽에서는 `global_written_sections`가 비어 있다. | 실행 확인 (실제 `ContextManager`, 가짜 임베딩·압축기), 코드 확인 (순서 비결정은 `set` 의미) |
| R-18 | 질의 하나의 검색 방식(임베딩 사용 여부) | `researcher.memory.get_embeddings()`를 부른다. 예외가 나면(임베딩 모델 없음, 패키지·키 없음) 정보 로그를 남기고 `rank_written_sections(query, written_contents, max_results=10)`의 결과를 돌려준다(C-12). 예외가 없으면 `WrittenContentCompressor(documents=written_contents, embeddings, similarity_threshold=0.5)`의 `async_get_context(query, max_results=10, cost_callback=add_costs)`를 부른다. 이 클래스는 먼저 `cost_callback(estimate_embedding_cost(임베딩 모델 상수, 전체 documents))`를 부르고, `SectionRetriever`로 섹션을 문서로 바꾼 뒤 1000/100 분할과 임계값 0.5의 `EmbeddingsFilter`를 거쳐 남은 조각을 `"Title: {section_title}\nContent: {page_content}\n"` 목록(상위 `max_results`)으로 만든다(C-11). 이 경로에서 난 예외(임베딩 API 오류 등)는 잡지 않아 `run()` 전체가 실패한다(R-27). 임베딩 모델 생성 자체(`get_embeddings`)만 키워드 순위로 내려간다. | 실행 확인 (실제 `ContextManager`·`WrittenContentCompressor`, 분할기·필터는 대체물), 코드 확인 (`EmbeddingsFilter` 내부, `written_contents`가 빈 첫 서브토픽에서의 임베딩 경로 동작은 라이브러리 몫이라 미확인) |
| R-19 | 키워드 순위 `rank_written_sections` | C-12의 알고리즘이다. 섹션마다 `written_content`를 1000자(겹침 100)로 나눈 조각들을 `"{제목}\n{조각}"`으로 BM25(`k1=1.5`, `b=0.75`, IDF는 이 조각 전체에서 계산)로 점수화한다. 최고 점수가 0 이하(겹치는 단어 없음, 빈 입력)이면 `[]`다. 아니면 점수 내림차순(동점은 원래 순서)으로 최고 점수의 0.5배 이상인 조각만 `"Title: {제목}\nContent: {조각}\n"`로 만들어 앞에서 `max_results`개 돌려준다. 제목도 점수에 들어가서 제목만 맞는 섹션도 찾는다. 질의는 서브토픽 task 문자열이다. | 실행 확인 (실제 함수, 분할기 대체) |
| R-20 | 서브토픽 조각 쓰기 | `subtopic_assistant.write_report(existing_headers=self.existing_headers, relevant_written_contents=위 결과)`를 부른다. `ext_context`와 `custom_prompt`는 주지 않으므로 컨텍스트는 서브토픽 연구기 자신의 것(`""`/`[]`이면 고정 문장)이다. `existing_headers`는 복사하지 않은 같은 리스트이고 지금까지 끝난 서브토픽의 항목만 들어 있다. 반환 문자열이 조각이다(실제 보고서, 고정 문장, 또는 LLM 실패의 `""`). | 실행 확인 (인자·스냅샷), 코드 확인 |
| R-21 | `visited_urls`와 `global_urls` | `global_urls`는 주 연구기의 `visited_urls`와 같은 객체이고 모든 서브토픽 연구기가 그 객체를 직접 늘린다. 그래서 `global_urls.update(서브토픽.visited_urls)`(서브토픽 끝)와 `gpt_researcher.visited_urls.update(global_urls)`(`run()`의 ⑤)는 같은 객체에 같은 원소를 넣는 것이라 아무 변화가 없다. 결과 집합은 모든 연구기가 스크랩하려고 고른 URL 전체(스크랩에 실패한 URL 포함, research-pipeline R-20)이며, 결론 뒤 참고문헌에 이 전체가 들어간다. | 실행 확인 (객체 동일성·합집합) |
| R-22 | 서브토픽 하나가 끝난 뒤 상태 갱신 | 순서대로: ① `global_written_sections.extend(주 연구기.extract_sections(조각))` ② `global_context = list(set(_hashable_context(서브토픽.context)))` ③ `global_urls.update(...)`(R-21) ④ `existing_headers.append({"subtopic task": task, "headers": 주 연구기.extract_headers(조각)})`. 조각이 `""`이거나 고정 문장이어도 모두 수행한다(헤더·섹션이 없으니 `headers`는 `[]`이고 섹션은 늘지 않는다). `write_report`가 예외를 내면 이 갱신은 모두 일어나지 않는다. | 실행 확인 |
| R-23 | 서브토픽 간 중복 방지 흐름(요약) | 서브토픽 k의 조각을 쓸 때 프롬프트에 들어가는 것: ① 서브토픽 1~k-1의 헤더 트리 전체(R-20의 `existing_headers`, 파이썬 표기, `{'subtopic task': ..., 'headers': [{'level': 2, 'text': ..., 'children': [...]}]}`) ② 서브토픽 task와 비슷하다고 찾아낸 이미 쓴 섹션 최대 10개(R-17~R-19). 프롬프트가 그 두 목록으로 "기존 헤더를 새 소제목으로 쓰지 말 것, 이미 쓴 내용을 반복하지 말 것"을 지시하는 문구와 `max_subsections=5`·분량은 report-writing R-12가 소유한다. 이미 쓴 내용을 걸러 내는 코드는 없다(LLM이 프롬프트를 지키는지는 확인하지 못했다). 첫 서브토픽은 두 목록이 모두 `[]`다. | 실행 확인 (실제 서브토픽 프롬프트 렌더링과 `existing_headers` 쌓임), 미확인 (LLM이 중복을 실제로 피하는지) |
| R-24 | 본문에 넣는 조건 | `_generate_subtopic_reports`는 `result["report"]`가 truthy일 때만 `subtopic_reports`에 넣고 본문 문자열에 `"\n\n\n" + 조각`을 이어 붙인다. `""`인 조각은 빠지고 고정 문장은 보고서와 구별하지 않으므로 그대로 들어간다. 서브토픽 사이 구분은 `"\n\n\n"` 하나뿐(앞에 붙임)이다. 반환 튜플의 첫 원소 `subtopic_reports`는 `run()`이 버린다. | 실행 확인 |

조립과 실패

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | 조립(`_construct_detailed_report`) | ① `toc = table_of_contents(본문)` ② `conclusion = await write_report_conclusion(본문)` ③ `conclusion_with_references = add_references(conclusion, gpt_researcher.visited_urls)` ④ `report = f"{서론}\n\n{toc}\n\n{본문}\n\n{conclusion_with_references}"`(C-05). 목차는 본문만의 헤더 트리라 서론의 H1과 결론의 `## Conclusion`은 목차에 나오지 않는다. 참고문헌은 결론에만 붙고 서론·본문에는 붙지 않으며, 형식과 정렬은 report-writing R-30(`"\n\n\n## References\n\n"` + 정렬된 `- [url](url)` 줄)이다. 결론이 `""`여도 참고문헌 절은 붙는다. 본문이 `""`(서브토픽 0개 또는 모두 빠짐)이면 목차는 제목 줄(`"## Table of Contents\n\n"`)뿐이고 결론은 `""` 본문으로 그대로 요청된다. | 실행 확인 (정확한 문자열) |
| R-26 | 반환값 | `run()`은 R-25의 `report` 문자열을 돌려준다. 서론·결론·서브토픽이 모두 실패해도 예외가 아니라 구분 줄바꿈과 목차 제목, 참고문헌만 남은 문자열이다(정확한 예는 T-11). 서론이 `""`이면 보고서는 `"\n\n"`로 시작한다. | 실행 확인 |
| R-27 | 실패 전파 | `DetailedReport`에는 `try/except`가 없다. 주 연구기·서브토픽 연구기의 `conduct_research` 안의 초기 검색·계획 단계 예외(research-pipeline R-09~R-11), 연구기 생성 예외(예: `max_search_results`의 `ValueError`), 임베딩 검색 오류(R-18), `write_report`의 프롬프트 생성 예외(report-writing R-04, R-08, R-18)는 `run()`을 그 예외로 끝낸다. 부분 결과는 없다: 이미 쓴 서론과 앞 서브토픽 조각은 버려지고 결론과 참고문헌은 만들어지지 않는다. 서브토픽 하나가 예외로 실패해도 나머지를 계속 처리하는 격리는 없다. 호출자(서버·CLI)의 처리는 그쪽 스펙이다. LLM 호출 실패는 예외가 아니라 빈 조각이 된다(R-31). | 실행 확인 (스텁 연구기가 던진 예외의 전파), 코드 확인 |
| R-28 | 빈 보고서가 본문에 섞이는 경우 | 서브토픽 연구기의 컨텍스트가 비었을 때 `write_report`가 돌려주는 고정 문장(`I could not gather any source material for "<task>". ...`)은 truthy라 R-24에 의해 본문에 보고서처럼 이어 붙고, 헤더가 없어 목차·`global_written_sections`·`existing_headers`의 `headers`에는 기여하지 않는다. 결론은 그 문장이 섞인 본문을 읽고 쓴다. | 실행 확인 (가짜 연구기가 고정 문장을 반환), 코드 확인 (고정 문장 생성은 report-writing 실행 확인) |
| R-31 | LLM 호출이 실패한 조각(예외 아님) | 하위 주제 생성 실패는 R-09대로 서브토픽 0개로 이어진다. 서론이 실패하면 `""`라 보고서가 `"\n\n"`(서론 자리의 빈 문자열과 구분 줄바꿈)로 시작한다. 서브토픽 `write_report`가 실패하면 `""`라 본문에서 빠지고 그 서브토픽은 R-22의 갱신만 하고 지나간다(앞뒤 서브토픽은 계속 처리). 초안 제목이 실패하면 `[]`지만 어차피 쓰이지 않는다(R-16). 결론이 실패하면 `""`지만 참고문헌은 그대로 붙는다(R-25). 이 규칙의 근거인 "write_* 함수는 LLM 실패를 예외로 내지 않는다"는 report-writing 불변식이다. | 실행 확인 (T-09, T-11), 코드 확인 (report-writing 불변식) |

비용·이벤트·로그

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-29 | 비용 | 연구기마다 자기 `research_costs`와 `step_costs`를 쌓고 `DetailedReport`는 합산하지 않는다(`detailed_report.py`에 비용 접근이 없다). 주 연구기에는 초기 연구, 서론, 결론의 비용이 쌓이고 서론·결론은 `write_report`를 거치지 않아 단계 이름이 `"research"`로 귀속된다(report-writing R-22). 서브토픽 연구기의 연구·초안 제목·본문·임베딩 추정 비용은 그 연구기 안에만 쌓이고 버려진다. `construct_subtopics`는 비용을 기록하지 않는다. 서버(`app.py:357`)와 CLI(`cli.py:226`)가 보고하는 비용은 `researcher.gpt_researcher.get_costs()`, 즉 주 연구기 값이라 서브토픽 비용은 빠진다. 반면 `visited_urls`는 합쳐져서(R-21) 서버의 `visited_urls`와 CLI의 `sources_count`에 서브토픽 URL까지 들어간다. | 코드 확인 (비용 접근 Grep, 호출처 줄) |
| R-30 | 이벤트와 websocket | `DetailedReport`는 이벤트를 만들지 않는다. 주 연구기와 모든 서브토픽 연구기가 같은 `websocket` 객체로 이벤트를 보낸다(서버에서는 `CustomLogsHandler`). `verbose`가 기본 `True`라 모든 연구기가 `logs` 이벤트를 보낸다. 대략의 순서: 초기 연구의 이벤트들 → `generating_subtopics`, `subtopics_generated` → `writing_introduction`, `introduction_written` → 서브토픽마다 [연구 이벤트들(`starting_research` 등), `generating_draft_sections`, `draft_sections_generated`, `fetching_relevant_written_content`(질의마다, 사실상 1회), `selected_images`(스크랩 이미지가 있으면), `writing_report`, `report_written`] → `writing_conclusion`, `conclusion_written`. 보고서 글 조각(`{"type":"report","output":조각}`, report-writing R-19)은 서론, 서브토픽 조각들, 결론의 순서로 스트리밍되고, 목차와 참고문헌은 스트리밍되지 않으며 반환 문자열에만 있다. 그래서 스트림을 이어 붙인 글과 반환값은 목차·참고문헌 유무와 위치가 다르다. 마지막 완료 이벤트는 `DetailedReport`가 보내지 않는다. `log_handler`는 누구에게도 전달되지 않아 `on_research_step` 기록은 없다. 직접 출력은 R-09의 `print` 하나뿐이다. | 코드 확인 (이벤트 이름·순서는 `writer.py`, `context_manager.py`, `researcher.py`의 `stream_output` 호출). 이벤트를 실제로 받아 보지 않았다 |

호출 경계(서버·CLI)와 소스 모드

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | 서버가 부름(`websocket_manager.py:144-159`) | `report_type == "detailed_report"`이면 `DetailedReport(query=task, query_domains, report_type=report_type, report_source, source_urls, document_urls, tone, config_path, websocket=logs_handler, headers, mcp_configs=mcp_configs if mcp_enabled else None, mcp_strategy=...if mcp_enabled else None, max_search_results)`를 만들고 `report = await researcher.run()`의 문자열을 쓴다. `return_researcher`가 켜져 있으면 `researcher.gpt_researcher`(주 연구기)를 돌려주고 REST 경로는 그 연구기의 `get_source_urls()`, `get_costs()`, `visited_urls`를 응답에 넣는다(R-29). `tone`은 `Tone` 열거형, `websocket`은 `CustomLogsHandler`다(웹소켓이 없는 REST 경로 `app.py:334-347`도 `run_agent`를 `websocket=None`으로 부르지만 `CustomLogsHandler`를 만들어 넘기므로 연구기가 보는 `websocket`은 항상 그 객체다). REST 경로는 `source_urls=[]`, `document_urls=[]`, `config_path=""`로 부른다. 서버·REST 자체는 서버 API 스펙의 몫이다. | 코드 확인 (호출 줄을 읽음) |
| R-33 | CLI가 부름(`cli.py:274-285`; 분기 `if`는 :274, 생성 :275-280, `run()` :282, `gpt_researcher` 읽기 :285) | `args.report_type == "detailed_report"`이면 `DetailedReport(query=args.query, query_domains=query_domains, report_type="research_report", report_source="web_search")`를 만들고 `report = await detailed_report.run()`을 한 뒤 `researcher = detailed_report.gpt_researcher`를 비용·출처 수 계산에 쓴다. `source_urls`·`tone`·`config_path`·`mcp_*`는 주지 않는다. `"web_search"`는 `ResearchConductor.conduct_research`가 비교하는 `ReportSource` 값(`web`, `local`, `hybrid`, `azure`, `langchain_documents`, `langchain_vectorstore`)에 없고 `source_urls`도 비어 있어서 어느 분기에도 맞지 않는다. 그래서 주 연구기의 초기 컨텍스트가 `[]`이고(research-pipeline R-08, 검색·스크랩 없음) 같은 값을 받은 서브토픽 연구기들도 모두 컨텍스트가 `[]`이다. 결과 흐름: 하위 주제 목록은 LLM이 `data="[]"`로 만든다(R-07), 서론은 빈 컨텍스트로 LLM이 쓴다(R-11), 서브토픽 조각은 전부 고정 문장이다(R-28), 목차는 제목 줄뿐이고, 결론은 고정 문장들을 본문으로 쓰고, 참고문헌은 `visited_urls`가 비어 제목만 붙는다. `--report_source` 인자는 이 분기에서 쓰이지 않는다. | 코드 확인 (분기 없음은 소스 문자열 검사와 source-modes 스펙의 실행 확인, 고정 문장은 report-writing 실행 확인, 전체 연쇄는 이어서 실행하지 않았다) |
| R-34 | `DetailedReport`가 소스 모드 인자를 다루는 방식 | 주 연구기는 `report_source`, `source_urls`, `document_urls`, `complement_source_urls`를 받지만 `documents`, `vector_store`는 받지 않는다. 서브토픽 연구기는 `report_source`, `source_urls`, `complement_source_urls`만 받고 `document_urls`는 받지 않는다. 그래서 상세 보고서에서: `langchain_documents`는 주 연구기가 `documents=None`으로 로더를 부르다 `TypeError`로 `run()`이 실패한다(source-modes R-31). `hybrid`는 주 연구기가 `document_urls`의 온라인 문서를 쓰지만 서브토픽 연구기는 `document_urls`가 없어 `DOC_PATH` 폴더의 문서를 읽는다(`researcher.py:175-181`). `local`은 둘 다 `DOC_PATH`다. `langchain_vectorstore`·`vector_store` 경로는 사용자 제외다. | 코드 확인 (`documents` 인자 부재는 실행 확인: 시그니처 검사), source-modes R-31 |

- 불변식:
  - 서브토픽 처리는 목록 순서이고 서브토픽 연구기는 한 시점에 하나만 살아 있다. 따라서 `existing_headers`·`global_written_sections`는 서브토픽 k를 쓰는 동안 1~k-1의 결과만 담는다. 전제: `DetailedReport` 인스턴스 하나에서 `run()`을 한 번만 부른다(`run()`을 다시 부르면 전역 상태가 이어지는지는 정해져 있지 않다).
  - `report`는 `str`이다(서론·결론이 `""`여도).
  - 모든 연구기가 쓰는 `visited_urls`는 한 객체이므로 스크랩 대상 URL은 한 번만 고른다(research-pipeline 불변식, 단 prefetched 제외).
- 미결정: 없음
- 확인 한계:
  - 실제 `GPTResearcher`로 끝까지 실행하지 않았다(`agent.py`는 의존 패키지가 없어 가져올 수 없다). 서브토픽 연구기의 연구 내용, LLM 응답, 실제 검색·스크랩 결과, 이벤트가 websocket에 실제로 어떤 순서로 도착하는지는 확인하지 못했다. R-15·R-33의 "컨텍스트가 비어 모두 고정 문장" 연쇄도 각 고리를 코드로 따라갔을 뿐 이어서 실행하지 않았다.
  - `RecursiveCharacterTextSplitter`는 빈 줄 단위로 나누는 대체물이다. 실제 분할(1000자, 겹침 100자)의 경계는 확인하지 않았다. 데모의 짧은 텍스트에서는 문단 하나가 조각 하나라는 가정이다. 실제 `EmbeddingsFilter`(임베딩 유사도 비교, 상위 개수 기본값 포함)와 `get_embeddings()`가 만드는 실제 임베딩, `written_contents`가 빈 첫 서브토픽에서 임베딩 경로가 `[]`를 돌려주는지 예외를 내는지는 라이브러리 몫이라 확인하지 못했다(키워드 경로는 빈 입력에서 `[]`를 실행으로 확인).
  - `PydanticOutputParser`의 형식 안내 문구와 JSON 추출은 langchain의 몫이라 대체물을 썼다. LLM이 실제로 `Subtopics` 형식 JSON을 내는지, 상한(`MAX_SUBTOPICS`)을 지키는지는 확인하지 못했다.
  - `list(set)[:10]`의 선택 결과는 프로세스마다 달라질 수 있다(문자열 해시 무작위화). 이는 Python 표준 동작에 따른 추론이고 서로 다른 해시 시드로 실행해 보지는 않았다.
  - 마크다운 함수는 Python-Markdown 3.10.3, 검증은 pydantic 2.13.5로 실행했다. 다른 버전에서 헤더 인식 범위가 달라질 수 있다.

### 1.5 필수 코드 참조

라이선스: overview 1절을 따른다. `LICENSE`는 Apache License 2.0이고 `pyproject.toml`은 MIT로 적어 표기가 어긋난다. 이 스펙은 코드를 복사하지 않았고 줄 범위만 가리킨다. 아래 범위의 함수와 프롬프트 문구는 재구현 때 원본을 그대로 재사용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `backend/report_type/detailed_report/detailed_report.py:10-91` `DetailedReport.__init__`, `_generate_research_id`, `run` | 인자·기본값, 주 연구기 인자 구성(`report_type` 하드코딩, MCP 조건부 키, `max_search_results` 덮어쓰기), 전역 상태 초기값, `run()`의 순서 | R-01~R-04, R-13 |
| C-02 | `detailed_report.py:93-120` `_initial_research`, `_get_all_subtopics`, `_generate_subtopic_reports` | 초기 연구의 상태 인계, 서브토픽 항목 변환과 빈 목록 처리, 순차 `for`와 본문 이어 붙이기(`"\n\n\n"`, truthy 조건) | R-05, R-06, R-09, R-24 |
| C-03 | `detailed_report.py:122-136` `_hashable_context` | 리스트 원소를 `str`로(dict는 `"Title: {title or 'No title'}\nContent: {body or content or ''}"`) 바꾸는 규칙. `str` 입력은 글자 단위 | R-14, R-22 |
| C-04 | `detailed_report.py:138-195` `_get_subtopic_report` | 서브토픽 연구기 인자, `max_search_results` 덮어쓰기, 컨텍스트 선설정, 초안 제목의 `str` 변환과 헤더 text 추출, 유사 섹션 검색 호출, `write_report` 인자, 전역 상태 갱신 4개와 `existing_headers` 항목 형식, 반환 `{"topic", "report"}` | R-12~R-16, R-20~R-22 |
| C-05 | `detailed_report.py:197-205` `_construct_detailed_report` | 목차·결론·참고문헌 계산과 `f"{서론}\n\n{목차}\n\n{본문}\n\n{결론+참고문헌}"` | R-25 |
| C-06 | `gpt_researcher/utils/llm.py:165-227` `construct_subtopics` | 프롬프트 템플릿 변수 4개, `PydanticOutputParser(Subtopics)` 체인(프롬프트, 모델, 파서를 `|`로 이은 langchain 체인), 제공자 인자 구성(추론 모델 분기·`llm_kwargs`·`max_tokens`), `config.max_subtopics` 전달, 모든 예외를 잡아 입력 `subtopics` 반환 | R-07~R-09 |
| C-07 | `gpt_researcher/utils/validators.py:1-26` `Subtopic`, `Subtopics` | 하위 주제 JSON의 모양과 검증(`task` 1자 이상, `subtopics` 기본 `[]`) | R-08, R-09 |
| C-08 | `gpt_researcher/prompts.py:572-593` `PromptFamily.generate_subtopics_prompt` | 하위 주제 생성 프롬프트 전문(변수 `{task}`, `{data}`, `{subtopics}`, `{max_subtopics}`, `{format_instructions}`) | R-08 |
| C-09 | `gpt_researcher/skills/writer.py:206-265` `ReportGenerator.get_subtopics`, `get_draft_section_titles` | 이벤트 이름, `construct_subtopics`·초안 제목 호출 인자(초안 제목의 `query`는 연구기의 query) | R-07, R-16 |
| C-10 | `gpt_researcher/skills/context_manager.py:89-163` `get_similar_written_contents_by_draft_section_titles`, `__get_similar_written_contents_by_query` | 질의 목록, 질의별 `gather`, 집합 합집합과 `[:max_results]`, 임베딩 시도와 키워드 대체, 압축기 호출 인자(임계값 0.5, `max_results`, `cost_callback`), 이벤트 | R-17, R-18 |
| C-11 | `gpt_researcher/context/compression.py:191-265` `WrittenContentCompressor`, `gpt_researcher/context/retriever.py:40-71` `SectionRetriever` | 섹션→문서 변환(메타데이터는 `section_title`만), 분할기 1000/100, `EmbeddingsFilter` 임계값, 출력 형식 `"Title: ...\nContent: ...\n"`, 비용 콜백이 먼저 호출됨 | R-18 |
| C-12 | `gpt_researcher/context/lexical.py:19-66`, `:110-133` `_TOKEN`, `_STOPWORDS`, `_stem`, `tokenize`, `bm25_scores`, `rank_written_sections` | 토큰화(소문자, `\w+`, 길이 2 이상, 불용어 제거, 가벼운 복수형 제거), BM25 점수(`k1=1.5`, `b=0.75`), 최고점 기준 0.5 비율 필터, 출력 형식 | R-19 |
| C-13 | `gpt_researcher/agent.py:620-662`, `:700-743` | `get_subtopics`, `get_draft_section_titles`, `get_similar_written_contents_by_draft_section_titles`(기본 `max_results=10`)와 `extract_headers`·`extract_sections`·`table_of_contents`·`add_references`가 순수 함수·스킬로 위임만 한다는 것 | R-07, R-16, R-17, R-22, R-25 |
| C-14 | `backend/server/websocket_manager.py:144-159`, `cli.py:274-285` | 서버·CLI의 `DetailedReport` 생성 인자와 `run()` 호출 | R-32, R-33 |
| C-15 | 선행 스펙 C-ID 재사용: report-writing C-07(`prompts.py:595-670`, 서브토픽 프롬프트), C-12(`report_generation.py:160-206`, 초안 제목), C-13(`writer.py:31-134`, 고정 문장), C-14, C-17(`markdown_processing.py:5-127`); research-pipeline C-16(`agent.py:343-413`) | 서브토픽 본문의 프롬프트 문구, 초안 제목 호출, 빈 컨텍스트 고정 문장, 헤더·섹션·목차·참고문헌 함수, 연구기 쪽 `conduct_research` | R-14, R-16, R-20, R-23, R-25, R-28 |

### 1.6 수락 사례

출처: 모두 구현에서 도출했고 같은 입력을 오프라인 데모(`artifacts/gpt-researcher/detailed-report-demos/demo_detailed_report.py`)로 실행해 기대값을 확인했다. 사례 중 "실행 안 함"이라고 적은 것은 도출만 했다. 데모의 연구기·LLM·임베딩·분할기는 대체물이므로 실제 연구 내용과 LLM 품질, 실제 임베딩 유사도, 실제 분할 경계는 검증하지 않는다. 표의 문자열은 데모 출력과 같다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-05 | 하위 주제 `["T1","T2"]`, 서브토픽 연구기 호출을 로그로 기록 | 순서 `주.연구 → 주.하위주제 → 주.서론 → T1.연구 → T1.초안제목 → T1.유사섹션 → T1.작성 → T2.(같은 순서) → 주.결론`. T2의 연구는 T1의 작성이 끝난 뒤 시작한다 |
| T-02 | R-25 | 서론 `"# Intro\n\nintro text"`, T1 조각 `"## T1 Heading\n\n### A1\n\ntext a1 ([c](https://x))\n\n### B1\n\ntext b1"`, T2 조각 `"## T2 Heading\n\n### A2\n\ntext a2"`, 결론 `"## Conclusion\n\nconcl"`, 방문 URL `m1, m2, t1a, t2a` | 반환 `"# Intro\n\nintro text\n\n## Table of Contents\n\n- T1 Heading\n    - A1\n    - B1\n- T2 Heading\n    - A2\n\n\n\n\n\n## T1 Heading\n\n### A1\n\ntext a1 ([c](https://x))\n\n### B1\n\ntext b1\n\n\n## T2 Heading\n\n### A2\n\ntext a2\n\n## Conclusion\n\nconcl\n\n\n## References\n\n- [https://m1](https://m1)\n- [https://m2](https://m2)\n- [https://t1a](https://t1a)\n- [https://t2a](https://t2a)\n"`. 서론·본문 뒤에는 참고문헌이 없고 결론 뒤에만 있다 |
| T-03 | R-01, R-02, R-13 | `DetailedReport(query="Q", report_type="detailed_report", report_source="web")` | 주 연구기 인자 키는 정확히 11개(R-02). `report_type`은 `"research_report"`. `documents`·`subtopics`·`visited_urls` 없음. `max_search_results="7"`이면 주 연구기 `cfg`가 7, `None`이면 5, `"abc"`면 `ValueError` |
| T-04 | R-12, R-13 | `source_urls`, `complement_source_urls=True`, `query_domains`, `tone`, `headers`, `websocket`, `document_urls`, `config_path`, `report_source="hybrid"`, `mcp_configs`, `mcp_strategy="deep"`, `max_search_results=9`를 모두 줌 | 서브토픽 연구기 인자 키는 정확히 16개(R-12). `source_urls`·`complement_source_urls`·`query_domains`·`tone`·`headers`·`websocket`(같은 객체)·`report_source`는 같은 값, `document_urls`와 `config_path`는 없음(주 연구기에는 있음), `mcp_*`는 주 연구기의 속성값, 서브토픽 `cfg`도 9 |
| T-05 | R-12, R-21 | 위 T-01 실행 | `주.visited_urls is d.global_urls`이고 모든 서브토픽 연구기의 `visited_urls` 인자가 그 객체다. 실행 뒤 집합은 `{m1, m2, t1a, t2a}`(T2가 `m1`을 다시 냈어도 하나) |
| T-06 | R-20, R-22, R-23 | T-01 실행 | T1의 `write_report`는 `existing_headers=[]`, T2의 것은 `[{"subtopic task":"T1","headers":[{"level":2,"text":"T1 Heading","children":[{"level":3,"text":"A1"},{"level":3,"text":"B1"}]}]}]`. T2의 유사 섹션 검색 입력의 기존 섹션은 `[{"section_title":"A1","written_content":"text a1 (c)"},{"section_title":"B1","written_content":"text b1"}]`(바로 아래에 하위 헤더만 있는 `T1 Heading`은 빠짐). `global_written_sections` 제목은 `A1, B1, A2` |
| T-07 | R-16 | 초안 제목이 `["### A1", "### B1"]` | `str(...)`는 `"['### A1', '### B1']"`이고 `extract_headers`는 `[]`, 유사 섹션 검색은 `(task, [], 기존 섹션)`으로 호출된다. 줄 처음에 `###`가 있는 일반 문자열 `"### A1\n### B1"`이면 `["A1","B1"]`이 나온다(이 경로에서는 오지 않음). `str([])` = `"[]"`도 `[]` |
| T-08 | R-14 | `_hashable_context(["a", 3, {"title":"T","body":"B"}, {"content":"C"}, {}])` / `"abca"` | `["a","3","Title: T\nContent: B","Title: No title\nContent: C","Title: No title\nContent: "]` / `["a","b","c","a"]`(글자 단위). 한 번의 실행 뒤 `global_context`는 마지막 서브토픽 컨텍스트 `"T2 CTX"`의 글자 집합(`' ','2','C','T','X'`을 포함하는 5개, 순서 없음) |
| T-09 | R-22, R-24 | T1 조각이 `""`(LLM 실패), T2는 정상 | 본문에 T1이 없고 T2만 있다. 그러나 `existing_headers[0] == {"subtopic task":"T1","headers":[]}`이고 `global_written_sections`는 T1 몫이 없다 |
| T-10 | R-28 | T2 조각이 고정 문장 `I could not gather any source material for "T2". ...` | 그 문장이 본문에 그대로 이어 붙는다. 목차는 `"## Table of Contents\n\n"`뿐이고 `global_written_sections`는 비어 있다 |
| T-11 | R-09, R-25, R-26 | 하위 주제 생성이 `[]`를 반환하고 서론·결론도 `""`, 초기 URL `m1, m2` | `Unexpected subtopics data format: []`를 출력한 뒤 서브토픽 연구기는 만들어지지 않고, 결론은 `""` 본문으로 호출된다. 반환은 `"\n\n## Table of Contents\n\n\n\n\n\n\n\n\n## References\n\n- [https://m1](https://m1)\n- [https://m2](https://m2)\n"`. `.subtopics`가 `[]`인 객체도 같은 경로 |
| T-12 | R-08, R-09 | `construct_subtopics` 체인이 ① `{"subtopics":[{"task":"S1"},{"task":"S2"}]}` ② 5개 항목(상한 3) ③ LLM 예외 ④ `"not json"` ⑤ `{"subtopics":[{"task":""}]}` ⑥ `{"topics":[]}`를 돌려줄 때(입력 `subtopics=["PRE"]`) | ①②는 `Subtopics`(②는 5개 그대로, 절단 없음) ③④⑤는 `["PRE"]`(입력 리스트, `subtopics`가 없는 기본이면 `[]`) ⑥은 항목이 없는 `Subtopics`(예외 아님). 렌더된 프롬프트에 `Limit the number of subtopics to a maximum of 3`가 있고 체인 입력은 `{"task","data","subtopics","max_subtopics":3}`. 추론 모델이면 `reasoning_effort="high"`, 아니면 `temperature=0.4`, `max_tokens=12000` |
| T-13 | R-08 | 파싱된 서브토픽이 5개 | 서브토픽 연구기가 5개 만들어진다(상한·중복 처리 없음) |
| T-14 | R-27 | T2 연구기의 `conduct_research`가 `RuntimeError("boom in T2")` | `run()`이 그 예외로 끝난다. 서론과 T1 작성은 이미 일어났고 `existing_headers`에는 T1만 있고 결론은 호출되지 않는다. 초기 연구가 예외면 `get_subtopics`도 호출되지 않는다. T1의 `write_report`가 예외면 `existing_headers`와 `global_written_sections`는 갱신되지 않는다 |
| T-15 | R-18, R-19 | 임베딩 모델 생성이 예외, 섹션 3개(배터리 화학, 태양광, 계통 저장), 서브토픽 task `"battery storage"` | 키워드 경로가 쓰이고 `["Title: Grid storage\nContent: Grid storage uses batteries to shift evening demand.\n"]`처럼 `"Title: ...\nContent: ...\n"` 문자열 리스트가 나온다. `written_contents`가 `[]`이면 `[]`, 겹치는 단어가 없으면 `[]`, 제목만 맞는 섹션도 찾아진다. 압축기 클래스는 만들어지지 않는다 |
| T-16 | R-17, R-18 | 임베딩 모델이 있고, 질의 3개(task와 제목 2개)에 압축기가 `["S1","S2"]`, `["S2","S3"]`, `[]`를 돌려줌 | 압축기를 질의마다 `similarity_threshold=0.5`, `max_results=10`, 비용 콜백과 함께 3번 부른다. 결과는 합집합 `{S1,S2,S3}`. 서로 다른 24개 문자열이면 10개로 잘린다(어느 10개인지 순서 없음). 압축기가 예외를 내면 `run()` 쪽으로 전파되고 키워드로 내려가지 않는다 |
| T-17 | R-18 | 실제 `WrittenContentCompressor`, 문서 `[{"section_title":"Keep me","written_content":"KEEP this paragraph.\n\nnot this one"},{"section_title":"Drop me","written_content":"nothing relevant"}]`, 필터는 "KEEP"이 든 조각만 남기는 대체물 | `["Title: Keep me\nContent: KEEP this paragraph.\n"]`. 비용 콜백은 검색 전에 한 번 불리고 인자는 `(임베딩 모델 상수, 문서 수 2)`. 분할기는 `(1000, 100)`, 필터는 임계값 `0.5` |
| T-18 | R-23 | `generate_subtopic_report_prompt("T2", existing_headers, ["Title: A1\nContent: text a1 (c)\n"], "Q", ...)` | 프롬프트에 `{'subtopic task': 'T1', 'headers': [{'level': 2, 'text': 'T1 Heading', 'children': [{'level': 3, 'text': 'A1'}]}]}`와 `['Title: A1\nContent: text a1 (c)\n']`(줄바꿈은 두 글자 `\n`)가 그대로 들어간다 |
| T-19 | R-33 | `report_source="web_search"`를 `ResearchConductor.conduct_research`의 분기와 비교 | 비교 대상 6개 값에 없다. 주·서브토픽 연구기의 컨텍스트가 `[]`가 되어 서브토픽 조각이 전부 고정 문장이라는 연쇄는 코드로만 확인했다(실행 안 함) |
| T-20 | R-15 | `source_urls=["https://s"]`, `complement_source_urls=False`로 상세 보고서 | 주 연구기가 `https://s`를 방문 처리한 뒤 서브토픽 연구기의 URL 경로는 새 URL이 없어 컨텍스트가 `""`가 되고 모든 서브토픽이 고정 문장이 된다(실행 안 함, 코드 연쇄로 도출) |
| T-21 | R-32 | 서버 호출 인자 | 호출 인자는 소스 문자열 검사(`websocket=logs_handler`, `document_urls=document_urls` 등)로만 확인했다. 서버를 실행하지 않았다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

문서와 구현의 차이(구현을 사실로 썼다):
- `backend/report_type/detailed_report/README.md`는 순서를 "초기 보고서 → 서브토픽 생성 → 서브토픽마다 헤더 누적과 보고서 작성 → 서론과 목차 → 최종 = 서론 + 목차 + 서브토픽 보고서들"로 쓰지만, 실제 `run()`은 서론을 서브토픽 보고서보다 먼저 쓰고, 결론과 참고문헌도 조립에 들어간다(`detailed_report.py:84-91`, `:197-205`). README의 "헤더가 누적되어 다시 생성되지 않게 한다"는 설명은 맞지만 README에 없는 비슷한 섹션 검색이 있고, 그 초안 제목 입력은 실제로 비어서 동작하지 않는다(R-16).
- overview 기능 지도의 이 행은 "전역 컨텍스트 공유"로 적었으나 `global_context`는 어떤 연구·작성 입력으로도 읽히지 않는다. 서브토픽 사이에 실제로 공유되는 것은 `visited_urls`, `existing_headers`, `global_written_sections`다(R-14).
- `GPTResearcher.__init__`의 docstring은 `max_subtopics (int): Maximum number of subtopics to generate`이고 기본값 5지만 어디서도 읽히지 않는다. 실제 상한 지시는 `config.max_subtopics`(`MAX_SUBTOPICS`, 기본 3)가 프롬프트에 들어가는 것뿐이다(`agent.py:77`, `:145`, `llm.py:218`, Grep으로 `max_subtopics` 사용처 전수 확인).
- `construct_subtopics`의 docstring은 `list`를 반환한다고 하지만 성공하면 `Subtopics` 객체, 실패하면 입력 `subtopics` 리스트다(`llm.py:165-227`).
- `get_draft_section_titles`는 `list[str]`을 돌려주는데(`agent.py:628` 주석과 `report_generation.py:160-206`) `DetailedReport`는 `str`을 기대하는 것처럼 `isinstance(..., str)` 검사 후 `str(리스트)`로 바꾼다(`detailed_report.py:169-170`). 그 결과 초안 제목이 쓰이지 않는다(R-16).
- `detailed_report.py:180`과 `:204`의 주석은 이미지가 주 연구 단계에서 미리 생성된다고 하지만, `GPTResearcher.conduct_research`는 `deep`이 아니면 매번 이미지 생성(활성일 때)을 하므로(`agent.py:398-411`) 서브토픽 연구기도 각자 이미지를 만들고 `write_report`가 `self.available_images`를 쓴다. 이미지 생성은 범위 밖이라 경계만 적는다.
- `DetailedReport`의 `global_written_sections: List[str]` 타입 표기는 실제 원소(`Section` dict)와 다르고, `_hashable_context`의 인자 표기 `List[str] | List[dict]`는 실제로 `str`도 받는다(R-14).
- `DetailedReport.__init__`의 `report_type` 인자는 읽히지 않고 주 연구기는 항상 `research_report`다(R-01, R-02). `cli.py`는 `"research_report"`를, 서버는 `"detailed_report"`를 주지만 결과는 같다.
- `docs/docs/examples/detailed_report.md`는 열어 보지 않았다. `README.md`(루트)는 이 스펙에서 대조하지 않았다.

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | `detailed_report.py:11-44`(C-01), 데모 A1 | 실제 클래스를 가짜 연구기로 실행. `research_id`가 안 읽히는 것은 `rg research_id backend/report_type`에서 정의 줄뿐임을 확인 |
| R-02 | `detailed_report.py:47-67`, `agent.py:146`, 데모 A1 | 키 집합은 실행으로, `Tone` 변환은 코드만 읽음. 주 연구기의 `verbose`·`log_handler` 기본값은 `agent.py:74`, `:78`, `:162`, `:168` |
| R-03 | `detailed_report.py:72-76`, `:93-96`, 데모 A1 | 실행 확인 |
| R-04 | `detailed_report.py:84-91`, 데모 A2 | 호출 순서 기록으로 확인 |
| R-05 | `detailed_report.py:110-120`, 데모 A2 | 같음. `asyncio.sleep`으로 양보하는 연구기에서도 순서 유지 |
| R-06 | `detailed_report.py:93-96`, 데모 A3, A7 | 실행 확인 |
| R-07 | `writer.py:206-233`(C-09), `agent.py:620-626`, `llm.py:165-227`(C-06), `agent.py:160`, 데모 A1, A3, A12 | 이벤트·인자는 코드, 체인은 스텁으로 실행. 비용 콜백 부재는 `construct_subtopics` 시그니처와 호출부에 `cost_callback`이 없음 |
| R-08 | C-06, C-07, C-08, `config/variables/default.py:31`, `config/variables/base.py:31`, `agent.py:77`, `:145`, 데모 A12 | 렌더링·인자·무절단은 실행, `max_subtopics` 미사용은 Grep. 실제 langchain 파서는 대체물 |
| R-09 | C-06(`:223-227`), C-02(`:98-108`), C-07, 데모 A6, A12 | 실행 확인(스텁 체인, 실제 pydantic 모델). `AttributeError` 경로는 도달 불가라 실행하지 않음 |
| R-10 | `detailed_report.py:148`, `agent.py:160`, `writer.py:220`, 데모 A3 | 코드 확인. `subtopics`를 읽는 곳이 `writer.py:220`뿐임을 Grep으로 확인 |
| R-11 | `detailed_report.py:87`, `writer.py:175-204`, 데모 A2 | 실행(호출 순서·입력). 서론 내용은 report-writing R-24 |
| R-12 | `detailed_report.py:138-158`, `agent.py:141`, `config.py:155`, 데모 A3 | 키 집합·동일 객체는 실행, `Config` 효과는 코드 확인 |
| R-13 | `detailed_report.py:69-71`, `:160-162`, 데모 A1, A3 | 실행 확인 |
| R-14 | `detailed_report.py:122-136`, `:164-165`, `:187`, `agent.py:392`, `researcher.py:212`, 데모 A3, A4 | 규칙·글자 분해는 실행, 덮어쓰기는 코드 확인(데모의 가짜 연구기가 같은 동작을 흉내 냄) |
| R-15 | `researcher.py:145-162`, `:813-834`, `context/select.py:53-101`, `prompts.py:555-562`, research-pipeline R-20, report-writing R-03 | 코드를 읽어 연쇄를 따라감. 이어서 실행하지 않음 |
| R-16 | `detailed_report.py:167-174`, `report_generation.py:160-206`, `writer.py:235-265`, 데모 A8, report-writing 데모 D-06 | `extract_headers`는 실제 함수로 실행, 반환 타입은 report-writing 데모 T-26과 코드 |
| R-17 | `detailed_report.py:176-178`, `context_manager.py:89-119`(C-10), `agent.py:639-662`, 데모 A10 | 실제 `ContextManager`를 가짜 연구기와 압축기로 실행 |
| R-18 | `context_manager.py:121-163`, `compression.py:191-265`(C-11), `context/retriever.py:40-71`, 데모 A10, A11 | 실제 클래스 실행(분할기·필터는 대체물). 라이브러리 내부는 코드 읽기 불가(미설치) |
| R-19 | `lexical.py:19-66`, `:110-133`(C-12), 데모 A10 | 실제 함수 실행(분할기는 대체물, 짧은 입력) |
| R-20 | `detailed_report.py:180-184`, `writer.py:49-134`, 데모 A4 | 실행(인자 스냅샷) |
| R-21 | `detailed_report.py:75-76`, `:89`, `:96`, `:188`, 데모 A3, A4 | 객체 동일성 실행 확인 |
| R-22 | `detailed_report.py:186-193`, 데모 A4, A6, A7 | 실행 확인 |
| R-23 | `prompts.py:595-670`(report-writing C-07), `detailed_report.py:176-193`, 데모 A4, A9 | 실제 프롬프트 함수로 렌더링. LLM의 준수는 미확인 |
| R-24 | `detailed_report.py:110-120`, 데모 A5, A6 | 실행 확인 |
| R-25 | `detailed_report.py:197-205`(C-05), `markdown_processing.py:72-127`, 데모 A5, A6 | 실제 `DetailedReport`·실제 마크다운 함수로 정확한 문자열 확인 |
| R-26 | 데모 A6 | 실행 확인 |
| R-27 | `detailed_report.py` 전체에 `try`·`except`가 없음(Grep), 데모 A7, `context_manager.py:147-163` | 실행(가짜 연구기가 던진 예외) |
| R-31 | `detailed_report.py:116-118`, `:167-174`, `:197-205`, 데모 A6, A8, report-writing R-24~R-26과 불변식 | 서브토픽·서론·결론이 `""`인 경우는 가짜 연구기가 `""`를 돌려주게 해 실행했다. 실제 LLM 실패가 `""`가 되는 것은 report-writing 쪽 실행 확인에 기댄다 |
| R-28 | `writer.py:79-88`, `detailed_report.py:116-118`, 데모 A6 | 고정 문장은 가짜 연구기가 같은 문장을 반환하게 했으므로 본문에 섞이는 부분만 `DetailedReport` 실행으로 확인, 문장 생성은 report-writing R-03 |
| R-29 | `detailed_report.py` 전체에 `cost` 접근 없음(Grep), `app.py:357`, `cli.py:226`, `agent.py:161-168`, `:785-806` | 코드 확인. 실제 비용 값은 계산하지 않음 |
| R-30 | `writer.py:175-265`, `context_manager.py:139-145`, `actions/utils.py:7-32`, `researcher.py:114-126`, `:231-237`, `websocket_manager.py:154` | 코드 확인. 실제 이벤트 수신은 하지 않음 |
| R-32 | C-14 (`websocket_manager.py:144-159`), `websocket_manager.py:161-166`, `app.py:333-360`, `server_utils.py:41-80`(`CustomLogsHandler`) | 코드를 읽음. 데모 A13은 소스 문자열 검사일 뿐 서버 실행이 아님 |
| R-33 | `cli.py:274-285`, `researcher.py:112`, `:144-209`, `utils/enum.py:30-51`, 데모 A14, source-modes R-08과 T-21, report-writing T-03 | 분기 목록은 소스 문자열·열거형으로 확인. 전체 연쇄는 이어서 실행하지 않음 |
| R-34 | `detailed_report.py:47-59`, `:140-158`, `researcher.py:166-188`, source-modes R-31, 데모 A1(시그니처에 `documents` 없음), A3 | `documents` 부재와 서브토픽에 `document_urls`가 없음은 실행, `hybrid`·`local` 분기는 코드 읽기, `TypeError`는 source-modes의 스텁 실행에 기댐 |
| T-01~T-21 | 해당 R-ID의 근거와 같다. 데모 검사 대응: T-01=A2, T-02=A5, T-03=A1, T-04=A3, T-05=A3·A4, T-06=A4, T-07=A8, T-08=A4, T-09=A6, T-10=A6, T-11=A6, T-12=A12, T-13=A6·A12, T-14=A7, T-15=A10, T-16=A10, T-17=A11, T-18=A9, T-19=A14(코드 연쇄는 도출), T-20=도출만, T-21=A13 | 출력은 `artifacts/gpt-researcher/detailed-report-demos/demo_detailed_report.out`(104 PASS). 데모는 실제 소스를 불러 쓰되 `GPTResearcher`, LLM, 임베딩, langchain 클래스, `Config`는 대체했다. Python-Markdown·pydantic은 로컬 uv 캐시에 풀려 있던 사본을 `sys.path`에 추가해 썼다(새로 설치하지 않음). 원본 테스트는 열람하지 않았다 |

### 2.2 코드 읽는 순서

1. `backend/report_type/detailed_report/detailed_report.py` 전체(205줄): `run`(:84) → `_get_subtopic_report`(:138) → `_construct_detailed_report`(:197).
2. `gpt_researcher/skills/writer.py:206` `get_subtopics` → `utils/llm.py:165` `construct_subtopics` → `prompts.py:572` 프롬프트와 `utils/validators.py`.
3. `skills/writer.py:235` 초안 제목 → `detailed_report.py:167-174`의 `str` 변환(R-16).
4. `skills/context_manager.py:89` → `context/compression.py:191`(임베딩 경로)과 `context/lexical.py:110`(키워드 경로).
5. 서브토픽 프롬프트(`prompts.py:595`)는 report-writing 스펙의 C-07, 연구기 쪽은 research-pipeline 스펙.
6. 호출자: `backend/server/websocket_manager.py:144`, `cli.py:274`.

원본의 구현 전략은 "상세 보고서는 일반 연구기를 서브토픽마다 새로 만들어 쓰는 얇은 조립기이고, 서브토픽 사이의 중복 방지는 코드로 걸러 내지 않고 앞선 헤더 트리와 비슷한 섹션 본문을 프롬프트에 보여 주어 LLM이 피하게 한다"이다. 서브토픽 사이에 이어지는 연구 입력은 `visited_urls`뿐이다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| 없음 | 이 문서에서는 적용 메모를 정하지 않았다 | 원본 동작을 기록하는 것이 목적이다. 초안 제목이 쓰이지 않는 점(R-16), `global_context`가 쓰이지 않는 점(R-14), 서브토픽 비용이 집계되지 않는 점(R-29), CLI의 `report_source="web_search"`(R-33)는 우리가 고칠지 따로 정할 항목이다 | — |
