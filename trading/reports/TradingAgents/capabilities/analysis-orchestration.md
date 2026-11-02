---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/graph/analyst_execution.py
  - tradingagents/graph/setup.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/agents/analysts/turn.py
  - tradingagents/graph/propagation.py
depends:
  - configuration.md
  - run-state.md
  - decision-contract.md
  - run-input.md
status: ready
---

# 병렬 분석·도구 루프

> 선택한 분석가의 독립 도구 루프와 메모리 정산을 병렬로 실행하고 모두 완료되면 투자 토론을 시작한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 분석가 선택 키를 등록부에서 순서대로 조회한다.
2. 선택 분석가마다 공통 입력 상태를 읽고 자기 보고서만 반환하는 하위 그래프를 만든다.
3. 부모 START에서 분석가들과 Memory Log를 병렬 시작한다.
4. 도구가 있는 분석가는 model→tools를 반복하고 상한에 도달하면 도구 없는 마지막 응답을 받는다.
5. 선택 분석가와 Memory Log가 모두 완료되면 Bull Researcher로 합류한다.
6. 이후 투자·리스크 단계 연결은 각 기능 계약에 따라 진행한다.
7. 일반 실행은 final_state·signal, 스트림은 메시지·부분 상태를 제공한다.

### 1.2 범위·통합 지점

- 제공: 분석가 등록/선택·독립 하위 그래프·합류·도구 상한·실행/스트림 연결.
- 제외: 각 분석가 도구/프롬프트, 토론 판단, 메모리 처리·체크포인트·기록은 각 기능 소유.
- 외부 경계: LangGraph StateGraph/ToolNode compile·invoke·stream·MessagesState를 사용한다. 각 agent(state)는 messages와 보고서 필드를 반환한다. 각 도구 결과/예외는 ToolNode로 전달된다. 원본은 ToolNode의 예외 처리 옵션을 명시하지 않아 SDK 기본값 이상의 예외 분류를 확정하지 않는다.
- 소유 상태: 분석가별 private message history, parent report 필드, 실행 종료 상태. 도구가 만드는 외부 부작용은 도구 기능 책임.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| selected_analysts | iterable<string>, 기본 market/social/news/fundamentals | CLI sentiment 표기와 별개로 graph 내부 키 social. unknown 또는 빈 선택은 ValueError. 중복 제거는 plan이 하지 않음 |
| AnalystNodeSpec | key, agent_node, report_key, tools:tuple | 정확한 키/노드/보고서 매핑 C-01. social tools=()이고 사전 수집 agent |
| max_tool_rounds / max_recur_limit | 기본20 / 100 | 2*max_tool_rounds+2 >= max_recur_limit이면 graph 생성 ValueError. 별도의 양수 검증은 없음 |
| rounds | 도구 호출을 가진 AI 메시지 수 | 한 메시지의 tool_calls 개수가 아님. 3개 tool_calls 한 메시지는 1라운드 |
| 하위 그래프 출력 | 해당 spec.report_key:string | private messages는 parent 출력 schema에서 제외된다 |
| stream_run | graph_input + args → iterable(messages, optional state) | 부모 values의 전체 messages/상태, 하위 tasks.result에서 messages·truthy 보고서 추출. 병합·표시 중복제거는 별도 소비자 책임 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 분석가 선택 | C-01대로 등록 순서 입력을 보존하여 spec을 만든다. social은 도구 미바인딩. 중복 키 허용 검증을 새로 넣지 않으며 실제 중복 노드 조립 실패는 graph 라이브러리 경계다. | 코드 확인 |
| R-02 | 하위 상태 격리 | C-02의 output_schema는 해당 보고서 키 하나만 노출한다. tools가 없으면 agent 후 종료. 있는 경우 마지막 메시지 tool_calls가 truthy면 ToolNode, 아니면 종료한다. | 코드 확인 |
| R-03 | 상한·최후 응답 | 도구 실행 후 누적 tool-call 메시지 수가 상한 이상이면 wrap_up. WRAP_UP HumanMessage를 넣어 agent를 한 번 더 호출하고 그 응답이 무엇이든 종료한다. 이 마지막 호출은 take_turn이 tool binding을 제거한다. | 코드 확인 |
| R-04 | 최후 응답 텍스트 이력 | C-03대로 AI 도구 호출은 name(args JSON) 텍스트, ToolMessage는 human 결과 텍스트로 변환한다. 다른 메시지는 유지한다. 마지막 보고서는 model content 그대로이며 숫자 증거를 코드가 추가 검증하지 않는다. | 코드 확인 |
| R-05 | 병렬 합류 | C-04는 각 selected analyst와 선택적 memory_node를 START에 연결하고 first_steps 전체에서 Bull로 join한다. memory_node 없는 GraphSetup 직접 사용도 가능. 실제 TradingAgentsGraph는 memory_node를 제공한다. 메모리가 끝나기 전 토론 시작을 허용하지 않는다. | 코드 확인 |
| R-06 | 예외·재귀 한도 | C-05의 생성자 한도식을 적용한다. agent/도구 예외를 감싸 Hold로 바꾸는 이 계층 코드는 없다. ToolNode의 명시되지 않은 예외 정책·LangGraph task scheduling은 외부 의존이다. Memory Log 자체의 예외 흡수는 메모리 기능 소유다. | 코드 확인 |
| R-07 | 실행/스트림 | C-06대로 invoke 또는 debug stream을 실행하고 최종 상태를 기록·체크포인트 정리한 뒤 state와 run_rating을 반환한다. stream_run은 run_config_context에서 iterator 생성/next/close를 실행해 외부 소비자 컨텍스트를 유지한다. 하위 tasks 결과가 report를 줄 때 parent join을 기다리지 않고 관찰할 수 있다. | 코드 확인 |

- 미결정: 없음(선언한 범위의 원본 경계).
- 확인 한계: 원본 clone 및 의존 라이브러리 실행 없이 확인했다. ToolNode의 기본 예외 분류·LangGraph reducer/일정은 명시된 외부 의존의 동작이며 이 스펙은 자체 재구현하지 않는다. task result 이벤트와 namespace shape는 원본 소비 코드가 기대하는 형태다. SDK의 정확한 버전별 실제 동작은 미확인.

### 1.5 필수 코드 참조

기준은 frontmatter의 SHA이며 원본 레포 루트 상대 경로다. C-ID가 지시하는 표·포맷·분기·알고리즘은 해당 범위를 함께 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/graph/analyst_execution.py:7-62` · spec·등록부·build_analyst_execution_plan | 등록부가 참조하는 TOOLS는 각 분석가 기능의 외부 도구 계약으로 제공. node/report key는 이 범위 완결 | R-01 |
| C-02 | `tradingagents/graph/setup.py:48-90` · _tools_or_done·_analyst_graph | 하위 그래프·상한·완료 분기. WRAP_UP C-03, AgentState S1 | R-02, R-03 |
| C-03 | `tradingagents/agents/analysts/turn.py:7-42` · WRAP_UP·take_turn·_as_text | 상한 도달시 이력 변환과 무도구 마지막 턴 | R-03, R-04 |
| C-04 | `tradingagents/graph/setup.py:109-166` · setup_graph | 선택 분석가·Memory Log fan-out/join. factory/state를 입력 계약으로 제공 | R-05 |
| C-05 | `tradingagents/graph/trading_graph.py:84-113` · __init__; `tradingagents/graph/propagation.py:67-80` · get_graph_args | 한도 검증·모든 graph 실행에 전달할 recursion_limit | R-06 |
| C-06 | `tradingagents/graph/trading_graph.py:373-436` · _run_graph·stream_run | 하위 호출의 create_run_state/record_decision/checkpoint_*는 각 입력·메모리·재개 계약으로 제공, run_rating은 S2 경계. 설정은 configuration | R-07 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 모델·SDK·네트워크는 정상/오류를 반환하는 대체물로 가정하며 실제 서비스 호환성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | selected_analysts=[] 또는 [unknown] | ValueError |
| T-02 | R-02, R-05 | market/news 선택, market가 먼저 보고서 완료 | market 보고서 관찰 가능하나 news와 Memory Log 완료 전 Bull 실행 안 함 |
| T-03 | R-03 | max_tool_rounds=2, 각 메시지 tool_calls3개씩 2턴 | 6개 도구 호출 뒤 wrap_up 1회; rounds는2 |
| T-04 | R-04 | 이력에 ToolMessage 있음, WRAP_UP 턴 | 도구 결과를 HumanMessage 텍스트로 전달하고 bind_tools 없는 model 호출 |
| T-05 | R-06 | max_tool_rounds=49, max_recur_limit=100 | 2*49+2=100이므로 ValueError; 48이면 이 검증은 통과 |
| T-06 | R-07 | stream 소비 사이 process 설정 다른 값 사용 | 각 graph next는 자기 config로 수행; 종료 시 stream.close를 해당 컨텍스트에서 호출 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-02, R-03 | C-02 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-03, R-04 | C-03 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-05 | C-04 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-06 | C-05 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-07 | C-06 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
