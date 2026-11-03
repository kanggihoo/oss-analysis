---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/analysts/news_analyst.py
  - tradingagents/agents/analysts/turn.py
  - tradingagents/agents/context.py
  - tradingagents/graph/setup.py
depends:
  - run-state.md
  - configuration.md
  - run-input.md
  - vendor-routing.md
  - point-in-time.md
  - analysis-orchestration.md
status: ready
---

# 뉴스·거시·이벤트 분석

> 실행 상태와 모델 도구 응답을 받아 최근 일주일 뉴스·거시·사건 확률을 해석한 보고서를 작성한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자가 실행 상태와 quick 모델로 노드를 준비한다.
2. 기준일·종목·언어를 분석 지시와 합친다.
3. 현재 메시지 이력을 넣어 도구 사용 가능 모델의 한 턴을 실행한다.
4. 도구 요청 중이면 보고서를 비우고, 도구 요청이 끝났으면 content를 news_report로 반환한다.

### 1.2 범위·통합 지점

- 제공: 분석 역할별 보고서와 해당 턴 AI 메시지.
- 제외: 벤더 응답·캐시·재시도 세부는 데이터 계약, 루프 상한·도구 실행은 실행 구조 계약.
- 선행: 실행 상태·설정·벤더·시점 제한·도구 루프.
- 소유 상태: 해당 보고서 한 키의 부분 갱신. 이 노드 자체는 디스크에 쓰지 않는다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| create_*_analyst(llm) | 모델 → state를 받는 노드 | 노드 생성 시 네트워크 조회 없음 |
| state | map | trade_date, company_of_interest, instrument_context, asset_type, messages는 공유 상태 계약 |
| 반환 | map: messages=list, news_report=string | 도구 호출 중에는 보고서가 빈 문자열. content를 문자열로 변환하는 검사는 없다. 반환은 전체 상태가 아닌 부분 갱신 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 일반 도구 사용 턴 | quick 모델을 사용하며 도구는 `get_news, get_global_news, get_macro_indicators, get_prediction_markets`만 바인딩한다. 기준일·종목 문맥·출력 언어·이전 messages를 프롬프트에 넣는다. | 코드 확인 |
| R-02 | 모델 응답에 tool_calls 존재 | 그 AI 메시지를 반환하고 `news_report`는 빈 문자열. 도구 실행·다음 턴·상한 종료는 병렬 분석·도구 루프 계약이 담당한다. | 코드 확인 |
| R-03 | 모델 응답에 tool_calls 없음 | 모델 content를 정규화 없이 `news_report`로 반환하며 전체 messages 중 이번 응답 하나만 반환한다. 별도 매수·매도 등급을 추출하지 않는다. | 코드 확인 |
| R-04 | 프롬프트 또는 모델 invoke 실패 | 노드 내부에서 예외를 잡거나 Hold로 바꾸지 않고 호출자에게 전파한다. 빈 content·누락 데이터에 대한 코드 기반 최소 품질 검사는 없다. | 코드 확인 |
| R-05 | 보고서 생성 지시 | 최근 일주일 뉴스·거시·사건 확률을 해석한 보고서를 작성하고 끝에 Markdown 요약표를 붙이라는 지시다. 항목 완전성·길이·요약표 유무는 코드로 검사하지 않는다. | 코드 확인 |
| R-06 | 뉴스 조사 | LLM이 뉴스 날짜·FRED 별칭 또는 시리즈 ID·Polymarket topic 등을 작성해 정해진 도구에 넘긴다. 임의 웹 검색·웹페이지 읽기 도구를 바인딩하지 않는다. crypto는 company 대신 asset 문구를 쓴다. | 코드 확인 |

- 미결정: 없음. 선행 스펙을 대조했고 선언한 범위의 원본 경계는 정해져 있다.
- 확인 한계: 설치·실행 및 실제 모델·외부 API 응답 검증은 하지 않았다. 프롬프트 지시가 모델 응답에 항상 지켜진다는 보장은 없다.

### 1.5 필수 코드 참조

기준은 frontmatter SHA이며 경로는 원본 레포 상대 경로다. 호출한 공통 helper는 위 선행 계약에서 정의한다.
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/analysts/news_analyst.py:13-18 TOOLS` | 허용 도구 목록 | R-01, R-05 |
| C-02 | `tradingagents/agents/analysts/news_analyst.py:23-32 create_news_analyst` | 분석 기준 프롬프트 | R-01, R-05, R-06 |
| C-03 | `tradingagents/agents/analysts/news_analyst.py:34-63 create_news_analyst` | 문맥 삽입·턴 실행·부분 상태 반환 | R-01, R-05 |
| C-04 | `tradingagents/agents/analysts/news_analyst.py:34-63 node` | 직접 invoke 경로에 예외 catch 없음 | R-02, R-03, R-04 |
| C-06 | `tradingagents/graph/setup.py:125-140 setup_graph` | 분석가 quick 모델 조립 | R-01 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 모델·네트워크를 대체 응답으로 바꿔 분기를 검증하는 사례이며 모델 품질이나 실제 제공자 가용성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 모델이 1개 이상 tool_calls와 content를 반환 | 보고서는 빈 문자열, messages에는 해당 응답 하나 |
| T-02 | R-03 | 모델이 tool_calls 없이 보고서 반환 | 같은 content가 보고서 키에 저장 |
| T-03 | R-04 | 모델 invoke가 예외 발생 | 이 노드에서 Hold·빈 보고서로 삼키지 않고 전파 |
| T-04 | R-05 | 모델이 요약표 없는 content를 반환 | 코드가 보정·재시도하지 않고 그대로 보고서로 반환 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-05 | C-01 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01, R-05, R-06 | C-02 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01, R-05 | C-03 | 원본 코드 직접 열람, 실행하지 않음 |
| R-02, R-03, R-04 | C-04 | 원본 코드 직접 열람, 실행하지 않음 |

R-01의 모델 계층은 C-06에서 확인했다.

T-ID의 기대 결과는 해당 R-ID 및 C-ID의 분기에서 도출했다. 테스트는 이름 검색까지만 참고했으며 수락 사례의 출처로 삼지 않았다.

프롬프트 핵심 원문: “Report what your tools support; another agent decides the trade.”

번역: “도구가 뒷받침하는 내용을 보고하라. 거래 판단은 다른 에이전트가 한다.” 코드 확인(R-05·R-06).

[핵심 원본](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/agents/analysts/news_analyst.py#L13-L18).

## 적용 메모

분석자 의견: 현재 미장용 수집·프롬프트를 보존한다. 국장 적용 시 도구명·보고서 출력 계약을 유지하면서 수집 소스와 자료 해석의 시장 가정을 별도로 검토한다.
