---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/agent.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/actions/report_generation.py
  - gpt_researcher/actions/markdown_processing.py
  - gpt_researcher/actions/utils.py
  - gpt_researcher/prompts.py
  - gpt_researcher/utils/enum.py
  - gpt_researcher/utils/llm.py
  - gpt_researcher/llm_provider/generic/base.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/skills/browser.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/image_generator.py
  - gpt_researcher/skills/researcher.py
  - backend/report_type/basic_report/basic_report.py
  - backend/report_type/detailed_report/detailed_report.py
depends:
  - ../capabilities/research-pipeline.md
status: ready
reimplementation: 미실행
---

# 보고서 작성

> 조사가 끝난 컨텍스트(문자열)와 보고서 타입·톤·언어·분량·인용 형식 설정을 받아 LLM으로 마크다운 보고서(본문·서론·결론)를 쓰고, 목차·참고문헌·헤더 추출 같은 마크다운 후처리 함수를 제공한다.

<!--
용어. 컨텍스트 = 연구 파이프라인이 돌려준 문자열(선행 스펙 R-25, 못 모으면 빈 리스트 `[]`). 에이전트 역할 문장(role) = 질문 분야에 맞춰 선택된 "You are ..." 지시문으로, 보고서 호출의 system 메시지가 된다. 프롬프트 생성 함수 = 보고서 종류별로 LLM에 보낼 user 메시지를 만드는 `PromptFamily`의 정적 메서드. 서브토픽 보고서 = 상세 보고서가 하위 주제마다 따로 쓰는 보고서 조각.
검증 방법. 이 스펙의 순수 함수·프롬프트 선택·생성 흐름은 오프라인 데모 `artifacts/gpt-researcher/report-writing-demos/demo_report_writing.py`(출력 `demo_report_writing.out`, 140개 검사 통과)로 실행했다. LLM과 Config는 대체물이고 대체 범위는 2.1 "확인 방법"과 1.4 확인 한계에 적었다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

단일 보고서(`research_report`)를 쓰는 경우다. 호출자는 `GPTResearcher(query, report_type="research_report", tone=Tone.Objective)`를 만들고 `conduct_research()`를 끝낸 뒤 `write_report()`를 부른다.

1. `write_report`가 `_current_step`을 `"report_writing"`으로 바꾸고, `log_handler`가 있으면 `writing_report` 이벤트를 보낸 뒤 `ReportGenerator.write_report`에 맡긴다. 컨텍스트는 `ext_context`가 비어 있지 않으면 그것, 아니면 `self.context`다.
2. 생성기가 스크랩으로 모은 이미지 URL이 있으면 websocket으로 `selected_images` 이벤트를 먼저 보낸다.
3. 컨텍스트가 비어 있으면(공백뿐인 문자열, 빈 리스트 포함) LLM을 부르지 않고 "자료를 모으지 못했다"는 고정 문장을 보고서 대신 돌려준다.
4. 프롬프트를 만든다. `custom_prompt`가 있으면 `"{custom_prompt}\n\nContext: {context}"`이고, 없으면 `report_type`에 대응하는 생성 함수에 컨텍스트·톤·분량(`TOTAL_WORDS`)·인용 형식(`REPORT_FORMAT`)·언어(`LANGUAGE`)를 넣는다. 미리 만들어진 이미지가 있으면 끝에 `AVAILABLE IMAGES:` 블록을 덧붙인다.
5. role을 system, 프롬프트를 user 메시지로 LLM을 스트리밍 호출한다. 예외가 나면 role과 프롬프트를 한 개의 user 메시지로 합쳐 한 번 더 부른다. 두 번 다 실패하면 빈 문자열이다.
6. 결과 문자열을 그대로 반환하고 `report_completed` 이벤트를 보낸다. 비용은 호출이 성공할 때마다 `add_costs`로 쌓인다.
7. 상세 보고서 같은 호출자는 서론(`write_introduction`), 결론(`write_report_conclusion`), 목차(`table_of_contents`), 참고문헌(`add_references`), 헤더 추출 함수를 별도로 불러 조립한다. 조립 순서는 [상세 보고서 스펙(detailed-report.md)](detailed-report.md)의 몫이다.

### 1.2 범위·통합 지점

- 제공: 보고서 본문 작성(타입 6종 + 폴백), `custom_prompt` 지정, 톤·언어·분량·인용 형식 반영, 이미 만들어진 이미지의 삽입 지시, 서론·결론·서브토픽 초안 제목 작성, 마크다운 순수 함수 4개(`extract_headers`, `extract_sections`, `table_of_contents`, `add_references`), 진행 이벤트·비용 기록, 실패 시 반환 규칙.
- 제외:
  - 상세 보고서의 전체 조립(서론+목차+본문+결론+참고문헌 순서, 서브토픽 목록 생성 `get_subtopics`, 서브토픽 간 유사 내용 검색)은 다른 스펙(detailed-report.md)이 맡는다. 여기서는 서브토픽 프롬프트가 `existing_headers`·`relevant_written_contents`를 어떻게 쓰는지까지만 쓴다.
  - 이미지 생성과 계획은 범위 밖이다(사용자 제외). 이미 만들어진 `available_images` 목록을 입력으로 받는 경계만 정한다.
  - LLM 제공자·`Config` 로딩·임베딩·비용 계산 방식(`calculate_llm_cost`)은 범위 밖이다(사용자 제외). 설정 키는 원문 이름만 쓴다.
  - 서버·CLI가 톤 이름을 `Tone` 열거형으로 바꾸는 일, 보고서 파일(md/pdf/docx) 저장은 서버 API·CLI 스펙의 몫이다.
  - `multi_agents`의 자체 작가 에이전트는 다른 경로다.
- 외부 의존과 경계(이 스펙이 정의하는 입력·정상 결과·실패):

  | 대상 | 이 스펙이 주는 입력 | 정상 결과 | 실패 시 이 스펙이 보는 것 |
  |---|---|---|---|
  | LLM 호출 `create_chat_completion` | `messages`(system+user 또는 user 하나), `model`=`SMART_LLM` 모델, `temperature`(본문 0.35, 서론·결론·초안 제목 0.25), `max_tokens`=`SMART_TOKEN_LIMIT`, `llm_provider`, `stream=True`, `websocket`(초안 제목만 `None`), `llm_kwargs`, `cost_callback`, 그리고 `GPTResearcher(**kwargs)`로 받은 여분 인자 | `str` | 예외. `websocket`이 있고 `stream`이면 한 번만 시도하고, 아니면 최대 10번(대기 1, 2, 4, 8, 8...초) 시도한 뒤 `RuntimeError`를 던진다. 빈 응답도 실패로 센다. 성공했을 때만 `cost_callback`을 한 번 부른다. |
  | websocket(선택) | `await send_json(dict)`를 가진 객체 | 이벤트 전송 | 전송 오류는 이 코드에서 잡지 않는다. |
  | `log_handler`(선택) | `await on_research_step(step: str, details: dict)`를 가진 객체 | 이벤트 기록 | `_log_event`가 예외를 잡아 로그만 남긴다. |
  | `cost_callback`=`add_costs` | `float`·`int` | 비용 누적 | 숫자가 아니면 `ValueError`. 이 값은 LLM 호출 함수 안에서 나므로 `generate_report`의 `except`가 잡는다(R-17). |
  | Python-Markdown(`markdown.markdown(text)`, 확장 없음) | 마크다운 문자열 | HTML 문자열 | 이 스펙이 직접 잡지 않는다(R-27~R-29는 입력이 `str`이 아닐 때만 막는다). |
  | 선행 스펙(research-pipeline) | — | 컨텍스트가 `str`(비어 있지 않음) 또는 `[]`, 에이전트 `role` 채워짐 | 컨텍스트가 `[]`이면 R-03의 고정 문장 |

- 소유 상태·부작용:
  - `GPTResearcher._current_step`: `write_report`가 `"report_writing"`으로 바꾸고 되돌리지 않는다. 서론·결론·초안 제목은 바꾸지 않는다(R-22).
  - `research_costs`, `step_costs`: LLM 호출이 성공할 때마다 늘어난다.
  - 이 기능은 `context`, `visited_urls`, `research_sources`, `research_images`, `available_images`를 읽기만 하고 바꾸지 않는다.
  - 외부 자원: LLM API, websocket 메시지, `log_handler` 호출, 콘솔 출력(실패 메시지).

### 1.3 인터페이스와 데이터 의미

호출은 모두 비동기(`await`)이고, 순수 함수 4개만 동기다. 중간 결과를 돌려주거나 취소하는 기능은 없다.

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GPTResearcher.write_report(existing_headers=[], relevant_written_contents=[], ext_context=None, custom_prompt="")` | → `string` | 보고서 본문. 생성에 실패하면 `""`이고 예외는 없다(R-17). 컨텍스트가 비면 보고서가 아니라 고정 문장이 온다(R-03). 호출자는 두 경우를 문자열 내용으로만 구별한다. |
| `write_introduction()` | → `string` | `self.context`로 서론(H1 제목 포함)을 쓴다. 입력 인자가 없다. 실패하면 `""`(R-24). |
| `write_report_conclusion(report_body)` | `report_body: string` → `string` | 인자로 받은 보고서 본문을 읽고 결론을 쓴다. 실패하면 `""`(R-25). |
| `get_draft_section_titles(current_subtopic)` | `string` → `list[string]` | 서브토픽 보고서의 초안 헤더 줄 목록. 실패하면 `[]`(R-26). 상세 보고서가 `relevant_written_contents`를 고르는 질의로 쓰려고 부르지만, 돌려받은 목록이 헤더 추출을 거치며 항상 빈 목록이 되어 실제로는 쓰이지 않는다([detailed-report.md](detailed-report.md) R-16). |
| `extract_headers(markdown_text)` | `string` → `list[HeaderNode]` | 헤더 트리(R-27). 문자열이 아니거나 비면 `[]`. |
| `HeaderNode` | `{level: int(1~), text: string, children?: list[HeaderNode]}` | `text`는 plain text가 아니라 Python-Markdown이 만든 안쪽 HTML이다(링크는 `<a href=...>`). `children`은 자식이 있을 때만 생긴다. |
| `extract_sections(markdown_text)` | `string` → `list[Section]` | 헤더마다 본문을 뽑은 평평한 목록(R-28). |
| `Section` | `{section_title: string, written_content: string}` | 제목은 HTML 그대로, 본문은 태그를 지운 텍스트(엔티티는 `&amp;` 등 그대로). |
| `table_of_contents(markdown_text)` | `string` → `string` | `"## Table of Contents\n\n"` 다음에 들여쓴 `- 제목` 줄들(R-29). |
| `add_references(report_markdown, visited_urls)` | `string`, `set[string]`(또는 반복 가능한 것) → `string` | 본문 뒤에 참고문헌 절을 붙인다(R-30). 새 문자열을 돌려주고 입력은 바꾸지 않는다. |
| `existing_headers` | `list`, 원소 형식은 제한 없음 | 서브토픽 보고서에서만 프롬프트에 파이썬 리스트 표기로 들어간다(R-12). 상세 보고서가 주는 형식은 `{"subtopic task": string, "headers": list[HeaderNode]}`의 목록이다. |
| `relevant_written_contents` | `list`, 원소 형식은 제한 없음 | 위와 같이 서브토픽 보고서에서만 쓰인다. 상세 보고서는 유사 내용 문자열의 목록을 준다. |
| `available_images` 원소 | `{url: string, title?: string, alt_text?: string, section_hint?: string}` | 이미 만들어진 이미지. `url`이 비었거나 dict가 아닌 원소는 무시한다(R-15). |
| `ext_context` | `string` 또는 `list[string]` 또는 `None` | 비어 있지 않을 때만 내부 컨텍스트 대신 쓴다(R-02). |
| `custom_prompt` | `string` | 비어 있지 않으면 타입별 프롬프트 대신 쓴다(R-10). |

보고서 관련 생성자 인자와 설정 키:

| 이름 | 기본값 | 쓰임 |
|---|---|---|
| `report_type` | `"research_report"` | 문자열. 프롬프트 생성 함수를 고른다(R-05). 열거형 멤버 자체가 아니라 값(`ReportType.X.value`)이어야 매핑이 맞는다. |
| `tone` | `Tone.Objective` | `Tone`이 아니면 `Tone.Objective`로 바뀐다(R-08). |
| `report_source` | `"web"` | 프롬프트의 참고문헌 지시를 가른다(R-09). 빈 값이면 `cfg.report_source`. |
| `parent_query` | `""` | 서브토픽 보고서의 상위 주제(`main_topic`)(R-12). |
| `report_format` (생성자 인자) | `"markdown"` | 저장만 하고 어디서도 읽지 않는다(R-07). |
| `verbose`, `websocket`, `log_handler`, `prompt_family`, `**kwargs` | `True`, `None`, `None`, `None`, — | 이벤트(R-20), 스트리밍(R-19), 로그(R-23), R-06, LLM 호출에 그대로 전달(R-16). `kwargs`에서 `encoding`은 빠진다. |
| `TOTAL_WORDS` | `1200` | 본문 프롬프트의 최소 단어 수. 환경변수가 같은 이름의 설정값을 덮어쓴다(`config.py:63-67`). |
| `REPORT_FORMAT` | `"APA"` | 본문·서브토픽·deep 프롬프트의 인용 형식 이름. 서론·결론에는 전달되지 않는다(R-24). |
| `LANGUAGE` | `"english"` | 본문·서브토픽·deep·서론·결론의 출력 언어. outline에는 쓰이지 않는다. |
| `AGENT_ROLE` | `None` | 있으면 선택된 role보다 우선하는 system 메시지(R-13). |
| `SMART_LLM` / `SMART_TOKEN_LIMIT` | `"openai:gpt-5.4"` / `12000` | 모든 보고서 호출의 모델과 `max_tokens`. |
| `PROMPT_FAMILY` | `"default"` | R-06. |

프롬프트가 각 입력을 쓰는지(실행 확인, 서로 다른 표식 값을 넣어 문구에 들어갔는지 본 결과):

| report_type | 컨텍스트·질문 | `TOTAL_WORDS` | `LANGUAGE` | `REPORT_FORMAT` | 톤 | `report_source`로 참고문헌 지시가 달라짐 | 그 밖에 받는 것 |
|---|---|---|---|---|---|---|---|
| `research_report` | 예 | 예 | 예 | 예 | 예 | 예 | 오늘 날짜 |
| `resource_report` | 예 | 예 | 예 | 아니오 | 아니오 | 예 | — |
| `outline_report` | 예 | 예 | 아니오 | 아니오 | 아니오 | 아니오 | — |
| `custom_report` | 예(질문이 지시문) | 아니오 | 아니오 | 아니오 | 아니오 | 아니오 | — |
| `deep` | 예 | 예 | 예 | 예 | 예 | 예 | 오늘 날짜 |
| `subtopic_report` | 예 | 예 | 예 | 예(대문자로) | 예(`tone`이 없으면 오류) | 받지 않음 | `existing_headers`, `relevant_written_contents`, `main_topic`, 오늘 날짜 |

진행 이벤트 형식: websocket이 있으면 `stream_output(type, content, output, websocket, output_log=True, metadata=None)`가 `{"type": type, "content": content, "output": output, "metadata": metadata}`를 `send_json`한다. `type != "images"`이면 같은 `output`을 로거에도 남긴다. 보고서 글 조각 자체는 이 형식이 아니라 R-19의 `{"type": "report", "output": 조각}`으로 간다.

### 1.4 행동 규칙과 남은 질문

호출 흐름과 컨텍스트

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `GPTResearcher.write_report` 호출 | `_current_step="report_writing"`으로 바꾼다. `log_handler`가 있으면 `writing_report`(details: `existing_headers`, `context_source` = `"external"`/`"internal"`, `available_images_count`) → 생성기 호출 → `report_completed`(details: `report_length`, `images_embedded`) 순으로 기록한다. 생성기에는 `existing_headers`, `relevant_written_contents`, `ext_context or self.context`, `custom_prompt`, `available_images=self.available_images`를 그대로 넘기고 그 문자열을 그대로 반환한다. `log_handler`가 없으면 기록만 없다. `images_embedded`는 실제로 삽입된 수가 아니라 `len(available_images)`다(이미지가 없으면 0). | 실행 확인 (C-15; ast로 발췌해 가짜 `self`에서 실행) |
| R-02 | 컨텍스트 선택 | 에이전트와 생성기가 각각 `ext_context or 기존 컨텍스트`를 적용한다. truthy한 `ext_context`만 우선한다. `""`, `[]`, `None`이면 `self.context`를 쓰고 `context_source`도 `"internal"`로 기록한다. 내부 컨텍스트가 비어 있어도 `ext_context`가 있으면 가드(R-03)를 통과한다. | 실행 확인 (C-13, C-15) |
| R-03 | 선택된 컨텍스트가 비어 있음 | 컨텍스트가 `list`면 `"\n".join(list)`, 아니면 `str(context or "")`를 만들어 `strip()`했을 때 비면 보고서를 쓰지 않는다. 대신 C-13의 고정 문장(`I could not gather any source material for "<query>". No sources were retrieved ... so I am not able to produce a reliable, sourced report.`)을 반환한다. LLM 호출, 비용, `logs` 이벤트(`writing_report` 등)는 없고, R-21의 `selected_images` 이벤트는 이 가드보다 먼저 나간다. 반환값은 일반 문자열이라 호출자가 보고서와 구별하려면 문장을 비교해야 한다. 상세 보고서는 이를 구별하지 않고 본문에 이어 붙인다(`if result["report"]`만 검사). | 실행 확인 (생성기까지), 코드 확인 (상세 보고서의 처리) |
| R-04 | 컨텍스트가 리스트에 비문자열 원소를 포함 | R-03의 `"\n".join`이 `TypeError`를 던지고 `write_report`가 이를 잡지 않아 호출자까지 나간다. LLM은 호출되지 않는다. | 실행 확인 |
| R-05 | 컨텍스트 삽입 모양 | 프롬프트에는 `f"{context}"` 그대로 들어간다. `str`은 그대로이고, `list`·`dict`는 파이썬 표기(따옴표 포함, 줄바꿈은 두 글자 `\n`)가 된다. 연구 파이프라인이 주는 컨텍스트는 `str` 또는 `[]`이므로 리스트 표기는 호출자가 `ext_context`로 리스트를 준 경우에만 생긴다. | 실행 확인 |

프롬프트 선택과 변수

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `report_type` → 프롬프트 생성 함수 | C-01의 매핑표를 따른다. `research_report`, `resource_report`, `outline_report`, `custom_report`, `subtopic_report`, `deep`만 키이고 경고 없이 선택된다. 키에 없는 값(`detailed_report`, 알 수 없는 문자열, `""`, 열거형 멤버 자체)은 예외 없이 `research_report` 프롬프트를 쓰고 `UserWarning`("Invalid report type: ...")만 낸다. 정상 경로의 상세 보고서는 주 연구기를 `research_report`로 만들고(`detailed_report.py:50`) 서브토픽은 `subtopic_report`로 쓰므로 `detailed_report` 값은 보통 여기에 도달하지 않는다. 본문 프롬프트는 `researcher.prompt_family`가 아니라 클래스 `PromptFamily`의 정적 메서드를 직접 쓴다. 서론·결론·초안 제목만 `researcher.prompt_family`를 쓰고, 이 SHA의 granite 계열은 보고서 프롬프트를 덮어쓰지 않으므로 어느 값이든 결과가 같다. | 실행 확인 (선택·폴백), 코드 확인 (`prompt_family` 영향 없음) |
| R-07 | 변수 전달 | 본문 호출(`generate_report`)은 `report_format=cfg.report_format`, `tone`(인자), `total_words=cfg.total_words`, `language=cfg.language`를 항상 넘긴다. 어느 입력을 어느 타입이 쓰는지는 1.3의 표를 따른다. `GPTResearcher(report_format=...)` 생성자 인자는 `self.report_format`에 저장될 뿐 어디서도 읽히지 않으므로 인용 형식은 오직 `REPORT_FORMAT` 설정이 정한다. 프롬프트 생성 함수의 기본값(`"apa"`, 1000단어, `"english"`)은 이 경로에서는 항상 덮어써진다. `headers` 인자는 `generate_report`가 받지만 쓰지 않는다. | 실행 확인 (표), 코드 확인 (`report_format` 미사용) |
| R-08 | 톤 | `GPTResearcher` 생성자는 `Tone`이 아닌 값을 `Tone.Objective`로 바꾼다. 프롬프트는 `tone.value`(예: `"Formal (adheres to academic standards ...)"`)를 문장에 넣는다(research는 "Write the report in a {tone.value} tone."). `tone`이 falsy이면 research·resource·deep은 톤 문장을 빼지만 `subtopic_report`는 `tone.value`를 무조건 읽어 `AttributeError`가 난다. 생성기를 거치지 않고 `generate_report`에 문자열 톤을 직접 주면 `AttributeError`가 나며, 프롬프트 생성은 LLM 호출의 `try` 바깥이라 예외가 호출자까지 나간다. 톤 값 17개는 C-18. | 실행 확인 (프롬프트·`generate_report`), 코드 확인 (생성자의 강제 변환) |
| R-09 | 참고문헌 지시(`report_source`) | `research_report`·`resource_report`·`deep`은 `report_source == "web"`일 때만 "사용한 출처 URL을 하이퍼링크로 쓰라"는 문단을 넣고, 그 밖의 값(`local`, `hybrid`, `static` 등)이면 "사용한 문서 이름을 쓰라"는 문단을 넣는다. `outline_report`와 `custom_report`는 `report_source`를 쓰지 않는다. 참고문헌은 LLM이 쓰는 것이므로 결과 형식은 LLM 출력에 달렸다. | 실행 확인 (프롬프트 분기), 미확인 (LLM이 따르는지) |
| R-10 | `custom_prompt`가 비어 있지 않고 `report_type != "subtopic_report"` | 타입별 프롬프트 생성 함수 대신 `"{custom_prompt}\n\nContext: {context}"`가 user 메시지가 된다(톤·언어·분량 지시는 들어가지 않는다). `subtopic_report`이면 `custom_prompt`는 무시되고 서브토픽 프롬프트를 쓴다. 이미지 블록(R-15)은 어느 경우에나 뒤에 붙는다. | 실행 확인 |
| R-11 | `report_type="custom_report"`이고 `custom_prompt`가 없음 | 질문(`query`) 문자열이 곧 지시문이다. user 메시지는 `'"{context}"\n\n{query}'`이다. | 실행 확인 |
| R-12 | `report_type == "subtopic_report"`(서브토픽 보고서) | 생성기는 `query`를 `current_subtopic`으로, `parent_query`를 `main_topic`으로 넘기고 `existing_headers`, `relevant_written_contents`도 프롬프트 생성 함수에 준다. 프롬프트는 두 목록을 파이썬 표기로 그대로 삽입하고 "기존 헤더를 새 소제목으로 쓰지 말 것", "이미 쓴 내용을 반복하지 말 것", 비슷한 소제목이 필요하면 기존 내용과의 차이를 밝힐 것을 지시한다. 소제목 수는 최대 5개(`max_subsections` 기본값, 호출부가 바꾸지 않는다)이고 분량은 `cfg.total_words`(기본 1200, 프롬프트 기본 800은 덮어써진다)다. 서브토픽이 아닌 타입에서는 이 세 인자가 프롬프트에 들어가지 않는다. 호출자가 넘기는 목록의 원소 형식은 코드가 검사하지 않는다. | 실행 확인 |
| R-13 | system 메시지(role) 결정 | `cfg.agent_role or researcher.role`이다. 이 값은 생성기 생성 시 한 번 계산되지만 비어 있으면 `write_report` 호출 시점에 다시 계산하므로, 생성 뒤(`conduct_research` 중)에 정해진 role도 쓰인다. `AGENT_ROLE` 설정이 있으면 선택된 role보다 우선한다. 둘 다 없으면 system 메시지는 문자열 `"None"`이다. 서론·결론·초안 제목은 항상 호출 시점에 계산한다. | 실행 확인 |
| R-14 | 생성 후 값 변경 | `ReportGenerator`는 생성 시점에 `query`, `report_type`, `report_source`, `tone`, `websocket`, `cfg`, `headers`를 `research_params`에 복사한다. 이후 `researcher.report_type`을 바꿔도 프롬프트 선택에는 반영되지 않는다(서브토픽용 인자를 넣을지 정하는 분기만 현재 값을 본다). | 실행 확인 (`report_type`), 코드 확인 (나머지) |
| R-15 | `available_images`가 있음(이미 만들어진 이미지) | `dict`이고 `url`이 비어 있지 않은 원소만 골라 `- Image {n}: ![{alt}]({url}) - {hint}` 줄을 만들고(n은 유효한 원소 기준 1부터), `alt`는 `title` → `alt_text` → `"Illustration"`, `hint`는 `section_hint` → `"General"` 순서다. 유효한 줄이 하나라도 있으면 프롬프트 끝에 `AVAILABLE IMAGES:` 설명과 줄 목록(문구는 C-10)을 붙이고, 없으면 아무것도 붙이지 않는다. `None`은 빈 목록과 같다. 이미지를 실제로 보고서에 넣는 것은 LLM이다. | 실행 확인 (삽입 문구), 미확인 (LLM이 넣는지) |

LLM 호출·실패·스트리밍

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | 본문 LLM 호출 사양 | system=role, user=프롬프트, `temperature=0.35`, `stream=True`, 모델·제공자·`max_tokens`는 `SMART_LLM`·`SMART_TOKEN_LIMIT`, `llm_kwargs=cfg.llm_kwargs`, `websocket`, `cost_callback=add_costs`, 그리고 `GPTResearcher(**kwargs)`로 받은 여분 인자를 그대로 붙인다. `agent.py`는 `encoding` 키를 이 인자에서 뺀다. | 실행 확인 (인자 기록; 실제 제공자 호출은 아님) |
| R-17 | 본문 호출이 예외 | 한 번 더 호출한다. 이때 설정은 같고(0.35, 스트리밍, 같은 `cost_callback`) 메시지만 `[{"role":"user","content":"{role}\n\n{프롬프트}"}]` 하나다. 두 번째가 성공하면 그 문자열을, 두 번째도 실패하면 `Error in generate_report: <두 번째 오류>`를 stdout에 `print`하고 `""`를 반환한다(예외 없음). 첫 번째 오류는 이 함수가 기록하지 않는다. 호출자(`ReportGenerator`)는 `""`여도 `report_written` 이벤트를 보내고 그대로 돌려준다. | 실행 확인 (가짜 LLM) |
| R-18 | 프롬프트 생성 중 예외 | 프롬프트 생성과 이미지 블록 생성은 `try` 바깥이다. R-08의 `AttributeError`처럼 거기서 난 예외는 폴백 없이 `write_report`까지 나가고 LLM은 호출되지 않는다. | 실행 확인 |
| R-19 | 스트리밍(제공자가 하는 일) | `websocket`이 있으면 제공자가 글 조각을 모아 줄바꿈이 포함될 때마다 `{"type": "report", "output": 조각}`을 보내고 끝에 남은 조각도 보낸다. 반환값은 전체 문자열이다. 본문, 서론, 결론이 이 경로를 쓰고 초안 제목은 `websocket=None`이라 보내지 않는다. `websocket`이 없으면 전송은 없다(콘솔 출력은 제공자의 `verbose` 설정). `websocket`과 `stream`이 함께면 한 번만 시도하므로 이 기능의 재시도는 R-17의 한 번이 전부이고, `websocket`이 없으면 호출마다 최대 10번이라 R-17과 합쳐 최대 20번 시도한다. 스트리밍 중에 실패하면 이미 보낸 조각이 있는 채로 재호출하므로 같은 글의 앞부분이 중복 전송될 수 있다. | 코드 확인 (스트리밍·재시도), 추론 (중복 전송) |
| R-20 | 진행 이벤트(`ReportGenerator.write_report`) | 순서는 ① `selected_images`(R-21) ② `verbose`이고 `available_images`가 있으면 `logs/images_available` ③ (R-03 가드 통과 뒤) `verbose`면 `logs/writing_report`(`✍️ Writing report for '{query}'...`) ④ LLM 호출 ⑤ `verbose`면 `logs/report_written`(`📝 Report written for '{query}'`)이다. 가드에 걸리면 ②~⑤는 없다. 서론은 `writing_introduction`/`introduction_written`, 결론은 `writing_conclusion`/`conclusion_written`, 초안 제목은 `generating_draft_sections`/`draft_sections_generated`를 `verbose`일 때만 보낸다. `websocket`이 없으면 전송은 없고 로거에만 남는다(`images` 타입 제외). | 실행 확인 |
| R-21 | `selected_images` 이벤트 | `researcher.get_research_images()`(스크랩한 이미지 URL의 앞 10개)가 비어 있지 않으면 `verbose`와 상관없이 컨텍스트 가드보다 먼저 `{"type":"images","content":"selected_images","output": json.dumps(URL 목록), "metadata": URL 목록}`를 보낸다. 이것은 스크랩으로 고른 이미지이고 R-15의 `available_images`(생성된 이미지)와 다르다. 보고서 프롬프트에는 들어가지 않는다. | 실행 확인 |
| R-22 | 비용 기록 | 본문, 서론, 결론, 초안 제목 호출 모두 `cost_callback=add_costs`다. 호출이 성공한 뒤에만 한 번 불리고 값은 숫자여야 한다(아니면 `ValueError`). `add_costs`는 `research_costs`와 `step_costs[_current_step]`에 더한다. `_current_step`은 `write_report`만 `"report_writing"`으로 바꾸고 되돌리지 않으므로, 서론·결론·초안 제목의 비용은 그때의 단계(예: 상세 보고서의 주 연구기는 `"research"`)로 귀속된다. `log_handler`가 있으면 `add_costs`는 `self._log_event("research", step="cost_update", ...)`를 `await` 없이 호출하므로 그 이벤트는 실행되지 않는다(코루틴만 만들어지고 `RuntimeWarning`). | 실행 확인 (가짜 `self`), 코드 확인 (LLM 성공 후 호출) |
| R-23 | 로그 기록 | 이 기능이 쓰는 기록은 R-01의 `log_handler` 이벤트(`writing_introduction`/`introduction_completed`, `writing_conclusion`/`conclusion_completed` 포함)와 `_log_event`가 같이 남기는 `research` 로거 줄뿐이다. `ResearchConductor`가 쓰는 `json_handler`(`costs`, `context`)는 보고서 작성 경로의 어디에서도 호출되지 않는다. | 코드 확인 |

서론·결론·초안 제목

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | `write_introduction()` | `self.context`(인자 없음)와 role로 서론을 쓴다. 컨텍스트가 비어 있어도 가드 없이 LLM을 부른다. 프롬프트는 `LANGUAGE`만 반영하고 톤·`TOTAL_WORDS`는 반영하지 않으며, `REPORT_FORMAT`을 전달하지 않아 인용 형식은 항상 `APA`다. `temperature=0.25`, 스트리밍, `websocket` 전달, `researcher.prompt_family`의 `generate_report_introduction`을 쓴다. LLM 예외는 이 함수가 잡아 로그를 남기고 `""`를 반환한다(재시도 없음, 한 번 호출). 프롬프트의 구조 규칙은 R-32. | 실행 확인 |
| R-25 | `write_report_conclusion(report_body)` | 인자로 받은 본문을 `report_content`로 쓴다(`self.context`는 무시). 호출 사양과 실패 처리는 R-24와 같고 인용 형식은 항상 `APA`다. 프롬프트는 2~3문단 결론, 맨 끝에 `## Conclusion` 제목이 없으면 결론 맨 위에 붙일 것을 지시한다. | 실행 확인 |
| R-26 | `get_draft_section_titles(current_subtopic)` | 서브토픽·주제(`query`)·컨텍스트로 H3 헤더 초안 목록을 LLM에 쓰게 하고(`temperature=0.25`, `websocket=None`) 응답을 `"\n"`으로 나눈 `list[string]`을 반환한다. 예외면 `[]`이다. 응답이 비어 있어도 `[""]`가 될 뿐 검사하지 않는다. | 실행 확인 (분할·실패), 코드 확인 (프롬프트) |

마크다운 순수 함수(전부 Python-Markdown의 기본 변환을 거친 HTML 줄 단위로 동작한다. 정확한 코드는 C-17)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `extract_headers(markdown_text)` | 문자열이 아니거나 비면 `[]`. 아니면 `markdown.markdown`이 만든 HTML에서 `<h숫자`로 시작하는 줄만 헤더로 본다. 텍스트는 첫 `>` 뒤부터 마지막 `<` 앞까지(안쪽 HTML)다. 스택으로 트리를 만든다. 새 헤더 이상의 수준을 가진 항목을 스택에서 빼고, 남은 맨 위 항목의 `children`에 붙이고 없으면 최상위에 둔다. 따라서 H1 아래 바로 H4가 와도 H4는 H1의 자식이고 H-번호의 빈틈은 의미가 없다. 같은 제목은 합치지 않는다. Python-Markdown이 헤더로 만드는 것은 모두 잡힌다: `#` 형식, 밑줄(`===`) 형식, 끝의 `#`은 제거, 목록·인용 안의 헤더, 그리고 코드 펜스(백틱 세 개) 블록 안의 `# 줄`(펜스를 인식하지 않으므로). 빈 헤더(`#`)는 `text ""`다. | 실행 확인 |
| R-28 | `extract_sections(markdown_text)` | 문자열이 아니거나 비면 `[]`. HTML 전체에서 정규식으로 `<h숫자>제목</h숫자>` 다음 내용(다음 `<h숫자>` 앞 또는 문자열 끝까지)을 잡고, 내용에서 `<...>` 태그를 지운 뒤 앞뒤 공백을 자른다. 내용이 비면(예: 바로 아래에 하위 헤더만 오는 헤더) 그 항목은 건너뛴다. 첫 헤더 앞의 글은 버린다. 결과는 문서 순서의 평평한 목록이고 제목은 HTML 그대로, 본문 엔티티는 이스케이프된 채(`&amp;`, `&lt;`)다. 속성이 붙은 원시 `<h2 id=...>`는 `extract_headers`는 잡지만 이 함수는 못 잡는다. | 실행 확인 |
| R-29 | `table_of_contents(markdown_text)` | 문자열이 아니면 `""`. 문자열이면 `"## Table of Contents\n\n"` 뒤에 `extract_headers` 트리를 깊이 우선으로 펼쳐 줄마다 `" " * (깊이*4) + "- " + text + "\n"`를 붙인다. 깊이는 트리 깊이이고 H-번호가 아니다. 헤더가 없거나 빈 문자열이면 제목 줄만 있다. 텍스트는 HTML 그대로다. 내부 예외는 잡아 `print`하고 입력 `markdown_text`를 그대로 반환한다. | 실행 확인 (정상·경계), 코드 확인 (예외 경로) |
| R-30 | `add_references(report_markdown, visited_urls)` | `report_markdown`이 `None`이면 `""`, 문자열이 아니면 `str()`로 바꾼다. `visited_urls`가 `None`이면 본문을 그대로 돌려준다. 아니면 본문 뒤에 `"\n\n\n## References\n\n"`과 `sorted(visited_urls)` 순서의 `"- [{url}]({url})\n"`을 이어 붙인다(같은 집합이면 항상 같은 결과). URL은 검증·이스케이프하지 않고 그대로 쓴다. 빈 집합이면 `## References` 제목만 붙는다. 집합이 아닌 리스트는 받지만 중복을 제거하지 않고, 정렬할 수 없는 원소(문자열과 숫자 혼합)를 만나면 예외를 잡아 메시지를 `print`하고 본문만 돌려준다. 문자열을 주면 글자마다 한 줄이 된다. | 실행 확인 |
| R-31 | 후처리 함수의 사용처 | `add_references`, `table_of_contents`, `write_introduction`, `write_report_conclusion`을 부르는 것은 상세 보고서의 조립(`_construct_detailed_report`)뿐이다. 단일 보고서 경로(`BasicReport`, CLI, 서버, 그 밖의 호출자)는 `write_report`만 부르고 `add_references`를 부르지 않는다. 그 경로의 참고문헌과 인용은 프롬프트가 LLM에게 쓰게 한 것이다(R-32). | 코드 확인 (호출처 검색) |
| R-32 | 프롬프트가 요구하는 보고서 구조(문구는 C-ID, 핵심만 인용) | ① `research_report`: 마크다운 문법과 `{report_format}` 형식, "`#` for the main title, `##` for major sections, and `###` for subsections", "You MUST NOT include a table of contents", "at least {total_words} words", 표(table) 권장, 본문 속 인용은 문장·문단 끝의 `([in-text citation](url))`, 모든 주장에 인용, 끝에 참고문헌 목록(출처 URL 중복 없이 한 번씩), `{tone}` 톤, `{language}`로 작성, 현재 날짜 가정. ② `subtopic_report`: "Use H2 for the main subtopic header (##) and H3 for subsections (###)", H1 금지, 서론·결론·요약·참고문헌 절 금지, 인용은 같은 `([in-text citation](url))`, 최소 `{total_words}` 단어. ③ 서론: 보고서 전체를 아우르는 H1 제목으로 시작, 다른 절 금지, 인용 형식 `APA`. ④ 결론: 2~3문단, `## Conclusion` 제목. ⑤ `resource_report`: 출처마다 분석하는 참고자료 추천 보고서, 모든 관련 출처 URL을 하이퍼링크로, 최소 `{total_words}` 단어. ⑥ `outline_report`: 소제목·핵심 점을 담은 개요(outline). 프롬프트 문구는 원본 재사용. | 코드 확인 (문구 존재는 실행으로 확인), 미확인 (LLM이 실제로 지키는지) |

- 불변식:
  - `write_report`, `write_introduction`, `write_report_conclusion`, `get_draft_section_titles`는 LLM 호출이 실패해도 예외를 호출자에게 던지지 않는다(`""` 또는 `[]`). 예외가 나가는 경우는 프롬프트 생성·컨텍스트 가드의 `TypeError`/`AttributeError`(R-04, R-08, R-18)뿐이다.
  - 순수 함수 4개는 입력 객체를 바꾸지 않는다. `extract_headers`, `extract_sections`, `table_of_contents`는 같은 입력이면 같은 결과이고(단 Python-Markdown 버전에 따라 HTML이 같다는 전제), `add_references`는 같은 집합이면 같은 결과다.
- 미결정: 없음
- 확인 한계:
  - LLM 호출은 가짜로 대체했다. 실제 제공자의 스트리밍 조각, 10번 재시도와 대기, 빈 응답 재시도, 비용 계산(`calculate_llm_cost`)은 실행하지 않았고 소스를 읽어 정리했다(R-19, 1.2 표). 그래서 `Config`가 환경변수·JSON을 읽어 `TOTAL_WORDS` 같은 값을 만드는 과정도 실행하지 않았고 기본값만 `default.py`에서 읽었다.
  - `agent.py`는 import할 수 없어(의존 패키지 미설치) 해당 메서드만 소스에서 잘라 가짜 `self`로 실행했다. 생성자(톤 변환, `ReportGenerator` 생성 시점)와 `agent.py`의 나머지는 코드로만 확인했다.
  - 마크다운 순수 함수는 Python-Markdown 3.10.3으로 실행했다(레포 요구는 `pyproject.toml`의 `markdown>=3.8`, `requirements.txt`는 `>=3.5.1`). 다른 버전이나 다른 마크다운 파서로 옮기면 헤더로 인식되는 범위(코드 펜스 안의 `#`, 원시 HTML 헤더 등)가 달라질 수 있다.
  - LLM이 프롬프트의 구조 규칙(헤더 수준, 인용 형식, 분량, 참고문헌, 이미지 삽입)을 실제로 지키는지, `TOTAL_WORDS`만큼 쓰는지는 확인하지 못했다.

### 1.5 필수 코드 참조

라이선스: overview 1절을 따른다. `LICENSE`는 Apache License 2.0이고 `pyproject.toml`은 MIT로 적어 표기가 어긋난다. 이 스펙은 코드를 복사하지 않았고, 프롬프트 문구는 R-32에서 짧은 구절만 인용했다. 아래 범위의 프롬프트 문구와 함수 본문은 재구현 때 원본을 그대로 재사용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/prompts.py:852-876` `report_type_mapping`, `get_prompt_by_report_type` | 타입 값 → 생성 함수 이름 매핑표 6개(`research_report`→`generate_report_prompt`, `resource_report`→`generate_resource_report_prompt`, `outline_report`→`generate_outline_report_prompt`, `custom_report`→`generate_custom_report_prompt`, `subtopic_report`→`generate_subtopic_report_prompt`, `deep`→`generate_deep_research_prompt`)와 키에 없을 때의 경고·`research_report` 폴백 | R-05, R-06 |
| C-02 | `gpt_researcher/prompts.py:261-316` `PromptFamily.generate_report_prompt` | research_report 프롬프트 전문: 참고문헌 문단의 web/그 외 분기, 톤 문장, 헤더·인용·분량·목차 금지·언어·날짜 지시 | R-07, R-08, R-09, R-32 |
| C-03 | `gpt_researcher/prompts.py:352-390` `generate_resource_report_prompt` | resource_report 프롬프트 전문(`report_format`, `tone`을 받지만 쓰지 않음) | R-07, R-09, R-32 |
| C-04 | `gpt_researcher/prompts.py:392-396` `generate_custom_report_prompt` | `'"{context}"\n\n{query_prompt}'` | R-11 |
| C-05 | `gpt_researcher/prompts.py:398-415` `generate_outline_report_prompt` | outline_report 프롬프트 전문 | R-07, R-32 |
| C-06 | `gpt_researcher/prompts.py:417-487` `generate_deep_research_prompt` | deep 프롬프트 전문(`ReportSource.Web.value` 분기 포함) | R-06, R-07, R-09 |
| C-07 | `gpt_researcher/prompts.py:595-670` `generate_subtopic_report_prompt` | 서브토픽 프롬프트 전문: `existing_headers`·`relevant_written_contents`·`main_topic` 삽입 위치, 중복 방지·헤더·인용·분량 지시, `max_subsections=5` 기본값 | R-12, R-32 |
| C-08 | `gpt_researcher/prompts.py:672-704` `generate_draft_titles_prompt` | 초안 제목 프롬프트 전문 | R-26 |
| C-09 | `gpt_researcher/prompts.py:706-753` `generate_report_introduction`, `generate_report_conclusion` | 서론·결론 프롬프트 전문(`report_format` 기본값 `"apa"`) | R-24, R-25, R-32 |
| C-10 | `gpt_researcher/actions/report_generation.py:209-326` `generate_report` | 프롬프트 선택(서브토픽 / `custom_prompt` / 타입별), 이미지 블록 생성 규칙과 문구, 본문 LLM 호출 인자, 실패 시 두 번째 시도(단일 user 메시지)와 `""` 반환, 프롬프트 생성이 `try` 바깥인 구조 | R-07, R-08, R-10, R-11, R-12, R-15, R-16, R-17, R-18 |
| C-11 | `gpt_researcher/actions/report_generation.py:12-112` `write_report_introduction`, `write_conclusion` | 서론·결론의 LLM 호출 인자(0.25, 스트리밍, `report_format` 미전달)와 실패 시 `""` | R-24, R-25 |
| C-12 | `gpt_researcher/actions/report_generation.py:160-206` `generate_draft_section_titles` | 초안 제목 호출(`websocket=None`), `"\n"` 분할, 실패 시 `[]` | R-26 |
| C-13 | `gpt_researcher/skills/writer.py:31-134` `ReportGenerator.__init__`, `write_report` | `research_params` 복사 시점, `selected_images` 이벤트, 빈 컨텍스트 가드와 고정 문장, 이벤트 순서, role 재계산, 서브토픽일 때만 `main_topic`·`existing_headers`·`relevant_written_contents` 전달 | R-02, R-03, R-04, R-12, R-13, R-14, R-20, R-21, R-22 |
| C-14 | `gpt_researcher/skills/writer.py:136-265` `write_report_conclusion`, `write_introduction`, `get_draft_section_titles` | 서론·결론·초안 제목 호출 래퍼(컨텍스트·role 출처, `prompt_family`와 `kwargs` 전달, 이벤트 이름) | R-20, R-24, R-25, R-26 |
| C-15 | `gpt_researcher/agent.py:463-529` `write_report`, `write_report_conclusion`, `write_introduction` | `_current_step` 변경, `ext_context or self.context`, `log_handler` 이벤트와 details, `available_images` 전달 | R-01, R-02 |
| C-16 | `gpt_researcher/agent.py:785-806` `add_costs`, `:323-341` `_log_event` | 비용 누적과 단계 귀속, `ValueError`, `await` 없는 `_log_event` 호출 | R-22, R-23 |
| C-17 | `gpt_researcher/actions/markdown_processing.py:5-127` `extract_headers`, `extract_sections`, `table_of_contents`, `add_references` | 순수 함수 4개 전체(약 120줄, 자기완결적이고 `re`, `markdown`만 쓴다). 줄 단위 헤더 판정, 스택 트리, 섹션 정규식(`<h\d>(.*?)</h\d>(.*?)`와 다음 `<h\d>` 또는 문자열 끝까지의 lookahead, DOTALL), 목차 들여쓰기 4칸, 참고문헌 형식과 정렬, 각 예외 경로 | R-27, R-28, R-29, R-30 |
| C-18 | `gpt_researcher/utils/enum.py:6-27`, `:54-91` `ReportType`, `Tone` | 보고서 타입 값 7개(`research_report`, `resource_report`, `outline_report`, `custom_report`, `detailed_report`, `subtopic_report`, `deep`)와 톤 17개(`Objective`~`Casual`)의 이름과 설명 문구 | R-06, R-08 |
| C-19 | `gpt_researcher/actions/utils.py:7-32` `stream_output` | 이벤트 JSON 형식, `images` 타입은 로거에 남기지 않는 규칙, websocket이 없으면 전송하지 않는 규칙 | R-20, R-21 |

### 1.6 수락 사례

출처: 모두 구현에서 도출했고, 같은 입력을 오프라인 데모(`artifacts/gpt-researcher/report-writing-demos/demo_report_writing.py`)로 실행해 기대값을 확인했다. 데모의 LLM·`Config`는 대체물이므로 실제 LLM 응답 품질, 실제 스트리밍·재시도·비용 계산은 검증하지 않는다. 표의 기대값은 데모 출력과 같다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-16, R-07 | `research_report`, 컨텍스트 `"CTX"`, 설정 기본값, 톤 `Objective`, role `"ROLE"`, LLM이 `"THE REPORT"` 반환 | `"THE REPORT"`. LLM은 한 번 호출: messages `[system "ROLE", user 프롬프트]`, `temperature 0.35`, `stream True`, `max_tokens 12000`. user 메시지에 `"CTX"`, 질문, `at least 1200 words`, `markdown syntax and APA format`, `Write the report in a Objective (impartial ...) tone.`, `language: english`, 날짜 문장이 있다 |
| T-02 | R-02 | `self.context="INTERNAL"`; `ext_context="EXTERNAL"` / `""` / `[]` / `None`로 각각 호출 | `"EXTERNAL"`이면 프롬프트에 `EXTERNAL`만 있고 `context_source="external"`. 나머지 셋은 `INTERNAL`이고 `"internal"`. 내부 컨텍스트가 `[]`이고 `ext_context="X"`면 가드를 통과해 LLM이 호출된다 |
| T-03 | R-03 | 컨텍스트가 `""`, `[]`, `None`, `"  \n "`, `["", "  "]`, `0`; `query="Q?"` | 모두 `I could not gather any source material for "Q?". No sources were retrieved (searches may have returned nothing or been blocked), so I am not able to produce a reliable, sourced report.`를 반환, LLM 호출 0회, 비용 0 |
| T-04 | R-04 | 컨텍스트 `[{"title": "x"}]` | `TypeError`가 `write_report` 밖으로 나가고 LLM 호출 0회 |
| T-05 | R-05 | `ext_context=["alpha\nbeta", "gamma"]` | 프롬프트에 `"['alpha\nbeta', 'gamma']"`(따옴표와 두 글자 `\n`)가 들어간다. 컨텍스트가 dict `{"a": 1}`이면 `{'a': 1}`이 들어간다 |
| T-06 | R-06 | `get_prompt_by_report_type`에 `research_report`, `resource_report`, `outline_report`, `custom_report`, `subtopic_report`, `deep` | 각각 C-01의 함수를 돌려주고 경고 없음 |
| T-07 | R-06 | 값 `"detailed_report"`, `"bogus"`, `""`, `ReportType.ResearchReport`(열거형 멤버) | 모두 `generate_report_prompt`, `UserWarning` 한 건("Invalid report type: ..."), 예외 없음. `generate_report(report_type="detailed_report")`는 research_report 프롬프트로 LLM을 호출한다 |
| T-08 | R-07, R-08 | 표식 값 `TOTAL_WORDS=1234`, `LANGUAGE="Klingon"`, `REPORT_FORMAT="MLA9"`, 톤 `Formal`로 각 타입 프롬프트 생성 | 1.3의 사용 표와 같다. research·deep·subtopic은 네 값이 모두 들어가고, resource는 `1234`와 `Klingon`만, outline은 `1234`만, custom은 어느 것도 없다. subtopic은 `MLA9`를 대문자로 쓴다. `generate_report`에 `cfg`로 같은 값을 주면 `at least 1234 words`, `markdown syntax and MLA9 format`, `language: Klingon`이 들어가고 모델과 `max_tokens`는 `cfg` 값이다 |
| T-09 | R-08 | `generate_report(tone="Formal")`; `subtopic_report`에 `tone=None`; `research_report`에 `tone=None` | 앞의 둘은 `AttributeError`(LLM 호출 0회). 마지막은 톤 문장 없이 정상 |
| T-10 | R-09 | `report_source`를 `"web"`, `"hybrid"`, `"static"`으로 research_report 프롬프트 생성 | `web`은 `source urls`, 나머지는 `source document names` 문단. outline·custom은 `web`과 `local`의 프롬프트가 같다 |
| T-11 | R-10 | `custom_prompt="CUSTOM PROMPT"`, 타입이 research·resource·outline·custom·deep 각각 | user 메시지가 정확히 `"CUSTOM PROMPT\n\nContext: CTX"`. `subtopic_report`는 `custom_prompt`가 무시되고 서브토픽 프롬프트(`under the main topic: MAIN`)가 쓰인다 |
| T-12 | R-11 | `report_type="custom_report"`, `query="MY OWN INSTRUCTION"`, `custom_prompt` 없음 | user 메시지가 `"CTX"\n\nMY OWN INSTRUCTION`(따옴표 포함) |
| T-13 | R-12 | 연구기 `report_type="subtopic_report"`, `query="SUBTOPIC"`, `parent_query="MAIN TOPIC"`, `existing_headers=[{"subtopic task": "t", "headers": []}]`, `relevant_written_contents=["W"]` | 프롬프트에 `on the subtopic: SUBTOPIC under the main topic: MAIN TOPIC`, `{'subtopic task': 't', 'headers': []}`, `['W']`, `minimum length of 1200 words`. 타입이 `research_report`이면 같은 두 목록을 줘도 프롬프트에 들어가지 않는다 |
| T-14 | R-13 | `ReportGenerator`를 role `None`으로 만든 뒤 `role="ROLE CHOSEN LATER"`로 바꾸고 호출 / `cfg.agent_role="CONFIG ROLE"`과 `role="CHOSEN"` / role이 어디에도 없음 | system 메시지가 각각 `"ROLE CHOSEN LATER"` / `"CONFIG ROLE"` / `"None"` |
| T-15 | R-14 | 생성기 생성 뒤 `researcher.report_type`을 `"outline_report"`로 바꾸고 호출 | outline 프롬프트가 아니라 생성 시점의 research_report 프롬프트가 쓰인다 |
| T-16 | R-15 | `available_images=[{"url":"http://i/1.png","title":"T1","section_hint":"Intro"}, None, "notadict", {"title":"no url"}, {"url":""}, {"url":"http://i/2.png","alt_text":"ALT2"}, {"url":"http://i/3.png"}]` | 프롬프트 끝에 `AVAILABLE IMAGES:` 설명과 `- Image 1: ![T1](http://i/1.png) - Intro`, `- Image 2: ![ALT2](http://i/2.png) - General`, `- Image 3: ![Illustration](http://i/3.png) - General`. 유효한 항목이 없거나 `None`이면 블록 없음. `custom_prompt`와 함께면 `"CP\n\nContext: CTX\n\nAVAILABLE IMAGES:..."` |
| T-17 | R-17 | LLM 첫 호출이 예외, 두 번째가 `"SECOND TRY"` | `"SECOND TRY"`. 두 번째 호출의 messages는 user 하나이고 내용은 `"ROLE\n\n" + 첫 호출의 user 프롬프트`, `temperature 0.35`, `stream True`. `cost_callback`은 두 호출에 모두 전달된다 |
| T-18 | R-17 | 두 호출 모두 예외(`boom1`, `boom2`) | `""`, 예외 없음, stdout에 `Error in generate_report: boom2`(`boom1`은 없음). `ReportGenerator`를 거쳐도 `""`이고 `verbose`면 `report_written` 이벤트가 나간다 |
| T-19 | R-20, R-21 | `verbose=True`, websocket, 스크랩 이미지 2개, `available_images` 1개, 정상 컨텍스트 | 이벤트 순서 `images/selected_images`, `logs/images_available`, `logs/writing_report`, `logs/report_written`. `selected_images`의 `output`은 `json.dumps(["http://s/1.jpg","http://s/2.jpg"])`이고 `metadata`는 그 리스트 |
| T-20 | R-20, R-21, R-03 | 같은 조건에서 `verbose=False` / 스크랩 이미지 없음 / 컨텍스트가 비어 있음 | 순서대로: `selected_images`만 / `writing_report`, `report_written`만 / `selected_images`만 나가고 고정 문장 반환, LLM 호출 0회 |
| T-21 | R-22 | 정상 호출, `add_costs`를 `cost_callback`으로 | LLM 성공 후 한 번 불린다(가짜 LLM이 0.5를 줌). 첫 호출이 실패하고 두 번째가 성공해도 한 번이다 |
| T-22 | R-22, R-01 | 가짜 `self`에서 `add_costs(0.25)`, `_current_step="report_writing"`으로 바꾸고 `add_costs(1)` / `add_costs("1")`, `None`, `[1]` / `log_handler`가 있을 때 `add_costs(0.1)` | `research_costs 1.25`, `step_costs {"research": 0.25, "report_writing": 1}` / 모두 `ValueError` / 코루틴 `_log_event`가 await되지 않았다는 `RuntimeWarning`, `cost_update` 이벤트는 기록되지 않는다 |
| T-23 | R-01 | 가짜 `self`(`context=["INTERNAL"]`, `log_handler`, `available_images=[]`)에서 `write_report()` | 반환 `"REPORT-X"`(생성기 반환값), `_current_step=="report_writing"`, 생성기에 `existing_headers=[]`, `relevant_written_contents=[]`, `custom_prompt=""`, `ext_context=["INTERNAL"]`, `available_images=[]`. 이벤트 `writing_report {existing_headers: [], context_source: "internal", available_images_count: 0}`, `report_completed {report_length: 8, images_embedded: 0}`. 서론·결론 호출은 `_current_step`을 바꾸지 않는다 |
| T-24 | R-24 | `cfg`에 `REPORT_FORMAT="MLA9"`, `LANGUAGE="Klingon"`, `TOTAL_WORDS=1234`, 서론 호출 / 같은 설정으로 결론 호출(`context="REPORT BODY"`) | 서론 프롬프트: 컨텍스트가 맨 앞, `topic -- Q?`, `preceded by an H1 heading`, `output must be in Klingon language`, `APA format`, `MLA9`·`1234`·톤 없음, `temperature 0.25`, `stream True`, websocket 전달. 결론: `Research Report: REPORT BODY`, `2-3 paragraphs`, `"## Conclusion" section title`, `written in Klingon language`, `APA format` |
| T-25 | R-24, R-25 | 서론·결론 LLM이 예외 / 연구기 `context=""`로 `write_introduction` | 둘 다 `""`(LLM 호출 1회). 컨텍스트가 비어도 서론은 LLM을 부른다. 결론은 `self.context`를 무시하고 인자 본문을 쓴다 |
| T-26 | R-26 | LLM이 `"### A\n### B"`를 반환 / 예외 | `["### A", "### B"]`, 호출에 `websocket=None` / `[]` |
| T-27 | R-27 | 예시 문서(H1 `Title` 아래 `Section A`→`Sub A1`, `Section B ([cite](http://x.y))`, 밑줄 형식 H1 `Setext H1`, 그 아래 H4 `Deep`과 H2 `Section A`) | `[{level 1,"Title",children:[{2,"Section A",children:[{3,"Sub A1"}]},{2,'Section B (<a href="http://x.y">cite</a>)'}]},{level 1,"Setext H1",children:[{4,"Deep"},{2,"Section A"}]}]`. `Sub A1`에는 `children` 키가 없다 |
| T-28 | R-27 | `""`, `None`, `5`, `b"x"` / `"plain text only"` / `"#"` / `"## Title ##\ntext"` / 코드 펜스(백틱 세 개) 블록 안에 `# a comment` 줄이 있고 앞에 `# T`, 뒤에 `## S`가 있는 문서 / `"- ## item"`, `"> ## quoted"` | `[]` / `[]` / `[{"level":1,"text":""}]` / `[{"level":2,"text":"Title"}]` / 헤더 `T`와 `a comment`(그 자식 `S`) / `item`, `quoted` 헤더가 잡힌다 |
| T-29 | R-28 | 예시 문서 / `"intro before any header\n\n## A\n### B\nb text\n## C\nc text & <b>x</b> a < b"` / `"<h2 id='x'>raw</h2>\n\ntext"` | 제목 순서 `Title, Section A, Sub A1, Section B (<a ...>cite</a>), Setext H1, Deep, Section A`이고 `Sub A1`의 본문은 `"text a1 bold"` / `B`(`b text`)와 `C`(`c text &amp; x a &lt; b`)뿐이고 첫 헤더 앞 글과 본문이 빈 `A`는 없다 / `[]` |
| T-30 | R-29 | 예시 문서 / `""`, `"plain"` / `None`, `5` / `"#"` | `"## Table of Contents\n\n- Title\n    - Section A\n        - Sub A1\n    - Section B (<a href=\"http://x.y\">cite</a>)\n- Setext H1\n    - Deep\n    - Section A\n"` / `"## Table of Contents\n\n"` / `""` / `"## Table of Contents\n\n- \n"` |
| T-31 | R-30 | `add_references("# R", {"https://b.example/x", "https://a.example/y"})` | `"# R\n\n\n## References\n\n- [https://a.example/y](https://a.example/y)\n- [https://b.example/x](https://b.example/x)\n"`. 같은 집합을 다시 넣어도 같다 |
| T-32 | R-30 | `add_references("# R", set())` / `("# R", None)` / `(None, {"u"})` / `(5, {"u"})` / `("# R", ["https://b","https://a","https://b"])` / `("# R", {"a", 1})` / `("# R", "abc")` | `"# R\n\n\n## References\n\n"` / `"# R"` / `"\n\n\n## References\n\n- [u](u)\n"` / `"5\n\n\n## References\n\n- [u](u)\n"` / `https://b` 줄이 두 번 있는 정렬된 목록 / `"# R"`(`print`로 `Encountered exception in adding source urls`) / `a`, `b`, `c` 줄 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

문서와 구현의 차이(구현을 사실로 썼다):
- `GPTResearcher.__init__`는 `report_format="markdown"`을 받고 docstring도 "(markdown, pdf, etc)"라고 적지만, 이 값은 `self.report_format`에 저장될 뿐 어디서도 읽히지 않는다(`agent.py:57`, `:91`, `:144`, `gpt_researcher/` 전체 Grep). 프롬프트의 인용 형식은 `cfg.report_format`(`REPORT_FORMAT`, 기본 `"APA"`)이다(R-07).
- 프롬프트 생성 함수의 기본값(`report_format="apa"`, `total_words=1000`, `deep`은 2000, 서브토픽은 800)은 `generate_report`가 항상 `cfg` 값을 넘겨 덮어쓴다(`report_generation.py:254`, `:258`). 서론·결론 함수는 `report_format` 인자가 있지만 호출부가 넘기지 않아(`report_generation.py:42-46`, `:95-98`) 항상 `APA`다. 서론·결론은 톤과 `TOTAL_WORDS`도 쓰지 않는다.
- `ReportType.DetailedReport`가 열거형에 있지만 프롬프트 매핑에는 없다(`prompts.py:852-859`). `DetailedReport` 클래스는 주 연구기를 `research_report`로 만들어(`detailed_report.py:50`) 이 폴백을 피한다(R-06).
- `ReportGenerator.write_report`는 `prompt_family`를 `generate_report`에 넘기지 않아 본문 프롬프트는 항상 클래스 `PromptFamily`의 정적 메서드다(`writer.py:107-124`, `report_generation.py:224`). 서론·결론·초안 제목만 `researcher.prompt_family`를 쓴다. 이 SHA의 granite 계열은 `pretty_print_docs`, `join_local_web_documents`만 덮어써서(`prompts.py:756-834`) 실제 차이는 없다(R-06 근거).
- `agent.py:785-806` `add_costs`는 `async`인 `_log_event`를 `await` 없이 호출한다(R-22). `_log_event`의 `cost_update` 이벤트는 실제로 기록되지 않는다.
- `write_report`의 docstring은 "The generated report as a string"이라고만 하지만 반환값은 보고서이거나 고정 사과 문장이거나 `""`다(R-03, R-17).
- `agent.py:497` 주석은 이미지를 "Pass pre-generated images"라 하고 로그는 `images_embedded`라고 쓰지만 값은 입력 개수(`len(self.available_images)`)이고 LLM이 실제로 넣었는지는 확인하지 않는다(R-01).
- overview 지도의 이 행은 "프롬프트 내용·참고문헌 처리는 미확인"이었으나 이 스펙에서 코드와 실행으로 확인했다. README는 대조하지 않았다.
- 원본 테스트는 열람하지 않았다. 검색 결과에 보인 `tests/test_markdown_none_inputs.py:28-30`, `tests/test_add_references_order.py`의 단언 줄은 데모의 T-31, T-32 결과와 모순되지 않는다. 테스트는 실행하지 않았다.

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-15 (`agent.py:463-504`), 데모 F-01, F-02, F-05, F-06 | `ast`로 메서드를 잘라 가짜 `self`에서 실행. `images_embedded`의 값은 `agent.py:502`와 데모 F-05 |
| R-02 | `agent.py:495`, `writer.py:77`(C-13), 데모 F-03, F-04, E-05~E-07 | 실행 확인 |
| R-03 | `writer.py:79-88`(C-13), `detailed_report.py:116-118`, 데모 E-02(고정 문장 출력은 `.out`의 `apology text:`), E-20 | 생성기는 실제 코드 실행. 상세 보고서 처리는 코드만 읽음 |
| R-04 | `writer.py:82`, 데모 E-03 | 실행 확인 |
| R-05 | `report_generation.py:254-258`(f-string), 데모 C-11, C-12, E-04 | 실행 확인 |
| R-06 | C-01 (`prompts.py:852-876`), `agent.py:169`, `detailed_report.py:50`, `:143`, 데모 B-01~B-05, C-10 | 실행 확인. `prompt_family` 영향 없음은 `prompts.py:756-834`를 읽어 확인(코드 확인) |
| R-07 | `report_generation.py:249-258`(C-10), `prompts.py:261-316` 등, `config/variables/default.py:24-25`, `:32`, `agent.py:57`, `:144`, 데모 B-06~B-11, B-15, B-16, C-24 | 프롬프트·`generate_report`는 실행. `report_format` 미사용은 Grep(`report_format`) 결과로 확인. `Config`가 환경변수를 읽어 이 값들을 만드는 과정(`config.py:63-67`)은 실행하지 않음 |
| R-08 | `agent.py:146`, `prompts.py:291`, `:453`, `:667`, `utils/enum.py:54-91`, 데모 B-14, C-22, C-23 | 프롬프트는 실행. `agent.py:146` 강제 변환은 코드만 읽음 |
| R-09 | `prompts.py:277-289`, `:366-375`, `:439-451`, 데모 B-12, B-13 | 실행 확인(문구 분기). LLM 결과는 미확인 |
| R-10 | `report_generation.py:253-258`(C-10), 데모 C-05, C-06, C-17, E-15 | 실행 확인 |
| R-11 | `prompts.py:392-396`(C-04), 데모 B-09, C-04 | 실행 확인 |
| R-12 | `writer.py:114-120`, `prompts.py:595-670`(C-07), `report_generation.py:254`, 데모 B-11, C-06~C-09, E-08, E-09 | 실행 확인. 상세 보고서가 주는 목록 형식은 `detailed_report.py:176-193`, `skills/context_manager.py:89-119`를 읽어 확인(코드 확인) |
| R-13 | `writer.py:40`, `:107-109`, `:158`, `:188`, `:249`, 데모 E-10~E-12 | 실행 확인 |
| R-14 | `writer.py:38-47`, `:107`, `:114`, 데모 E-13 | `report_type`만 실행으로 확인했고 나머지 복사 필드는 코드를 읽음 |
| R-15 | `report_generation.py:260-290`(C-10), `skills/image_generator.py:148-152`(키 이름 `title`, `section_hint`), 데모 C-13~C-17 | 실행 확인. 이미지 생성은 범위 밖 |
| R-16 | `report_generation.py:291-306`, `writer.py:124`, `agent.py:183`, 데모 C-02, C-21, E-14 | 인자는 가짜 LLM에서 실행으로 확인. 실제 제공자 호출은 하지 않음 |
| R-17 | `report_generation.py:291-326`(C-10), 데모 C-18~C-20, E-21 | 가짜 LLM으로 실행 확인 |
| R-18 | `report_generation.py:249-290` vs `:291`(`try`), 데모 C-22, C-23 | 실행 확인 |
| R-19 | `utils/llm.py:120-162`, `llm_provider/generic/base.py:361-404` | 코드만 읽음. 가짜 LLM은 `websocket`·재시도를 흉내 내지 않았다. 중복 전송은 추론 |
| R-20 | `writer.py:65-132`(C-13), `:136-265`(C-14), `actions/utils.py:7-32`(C-19), 데모 E-16~E-22, E-26 | 가짜 websocket으로 이벤트를 받아 확인 |
| R-21 | `writer.py:65-75`, `skills/browser.py:59-60`, `:86-115`, `agent.py:665-674`, `actions/utils.py:20`, 데모 E-16~E-20 | 실행 확인. 스크랩이 `research_images`를 채우는 쪽은 브라우저 스펙 영역(여기서는 가짜 목록) |
| R-22 | `utils/llm.py:147-159`, `agent.py:484`, `:785-806`(C-16), `writer.py:119`, `:122`, `:159`, `:191`, `:252`, 데모 E-01, E-23, F-07~F-10 | 가짜 LLM이 성공 후 `cost_callback(0.5)`를 호출하게 했다. 실제 비용 값은 계산하지 않음. 비용 귀속과 `await` 누락은 실행 확인 |
| R-23 | `agent.py:323-341`, `skills/researcher.py:238-240`, `backend/server/logging_config.py:7`, `gpt_researcher/utils/logging_config.py:7-83`, `writer.py`·`report_generation.py`·`agent.py:463-529`에서 `json_handler` 검색 결과 없음 | Grep으로 호출처 확인(코드 확인). 실행 안 함 |
| R-24 | `report_generation.py:12-60`(C-11), `prompts.py:706-716`(C-09), `writer.py:175-204`(C-14), 데모 D-01~D-03, D-05, E-23, E-25, E-26 | 가짜 LLM으로 실행 확인 |
| R-25 | `report_generation.py:63-112`(C-11), `prompts.py:719-753`(C-09), `writer.py:136-173`, 데모 D-04, D-05, E-24 | 같음 |
| R-26 | `report_generation.py:160-206`(C-12), `prompts.py:672-704`(C-08), `writer.py:235-265`, 데모 D-06, D-07 | 분할·실패 경로는 실행, 프롬프트는 코드를 읽음 |
| R-27 | `markdown_processing.py:5-41`(C-17), 데모 A-01~A-10 | 실제 코드를 Python-Markdown 3.10.3으로 실행 |
| R-28 | `markdown_processing.py:43-70`(C-17), 데모 A-11~A-17 | 같음 |
| R-29 | `markdown_processing.py:72-99`(C-17), 데모 A-18~A-22 | 같음. `except` 경로(`:97-99`)는 코드만 읽음(`extract_headers` 쪽 예외를 일으키는 입력을 만들지 못했다) |
| R-30 | `markdown_processing.py:101-127`(C-17), 데모 A-23~A-31 | 실행 확인 |
| R-31 | `Grep add_references\(`, `\.table_of_contents\(`, `write_introduction\(`, `write_report_conclusion\(` 결과: `detailed_report.py:87`, `:198-200`뿐(`agent.py`의 위임 메서드와 `tests/` 제외), `basic_report.py:73-75`, `cli.py:317`, `backend/server/server_utils.py:107` | 코드 확인(호출처 검색, `*.py` 범위). 비 Python 호출자는 확인하지 않음 |
| R-32 | `prompts.py:261-316`(C-02), `:352-415`, `:595-670`, `:706-753`, 데모 B-06~B-11, C-03, D-02, D-04 | 문구가 프롬프트에 들어가는지는 실행 확인. 인용은 짧은 구절만. LLM이 지키는지는 미확인 |
| T-01~T-32 | 위 R-ID의 근거와 같다. 데모 검사 ID 대응: T-01=C-01~C-03, T-02=F-03·F-04·E-05~E-07, T-03=E-02, T-04=E-03, T-05=C-11·E-04, T-06=B-01, T-07=B-02~B-04·C-10, T-08=B-06~B-11·C-24, T-09=C-22·C-23·B-14, T-10=B-12·B-13, T-11=C-05·C-06, T-12=C-04, T-13=C-07·C-09·E-08·E-09, T-14=E-10~E-12, T-15=E-13, T-16=C-13~C-17, T-17=C-18·C-20, T-18=C-19·E-21, T-19=E-16·E-17, T-20=E-18~E-20, T-21=E-01·C-20, T-22=F-08~F-10, T-23=F-01·F-02·F-07, T-24=D-01~D-04, T-25=D-05·E-25·D-04, T-26=D-06·D-07, T-27=A-01~A-04, T-28=A-05~A-10, T-29=A-11~A-16, T-30=A-18~A-22, T-31=A-23·A-24, T-32=A-25~A-31 | 데모 출력은 `artifacts/gpt-researcher/report-writing-demos/demo_report_writing.out`(140 PASS). 데모는 실제 소스를 불러 쓰되 LLM, `Config`, `langchain_core.Document`, 패키지 `__init__`은 대체했고 `agent.py`는 메서드만 발췌했다. Python-Markdown은 로컬 uv 캐시에 풀려 있던 3.10.3 사본을 `sys.path`에 추가해 썼다(새로 설치하지 않음) |

### 2.2 코드 읽는 순서

1. `agent.py:463` `write_report` → `skills/writer.py:49` `ReportGenerator.write_report`: 컨텍스트 선택, 가드, 이벤트, 인자 조립.
2. `actions/report_generation.py:209` `generate_report`: 프롬프트 선택, 이미지 블록, LLM 호출과 폴백.
3. `prompts.py:852` 매핑 → 타입별 프롬프트(`:261`, `:352`, `:392`, `:398`, `:417`, `:595`).
4. `agent.py:506`·`:520` → `writer.py:136`·`:175` → `report_generation.py:12`·`:63`: 서론·결론.
5. `actions/markdown_processing.py` 전체와 `agent.py:700-743`의 위임 메서드.
6. 호출자 경계: `backend/report_type/basic_report/basic_report.py:72`, `detailed_report/detailed_report.py:84`(조립과 서브토픽 입력).

원본의 구현 전략은 "보고서 본문은 프롬프트 한 번에 쓰게 하고, 인용·참고문헌·구조는 프롬프트 문구로 LLM에게 맡긴다"이다. 코드가 직접 하는 후처리는 서브토픽을 합치는 상세 보고서 경로의 `table_of_contents`와 `add_references`뿐이다(R-31).
