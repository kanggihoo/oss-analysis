---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/analyzer.py
  - src/agent/skills/defaults.py
  - src/core/pipeline.py
  - src/schemas/report_schema.py
  - src/schemas/decision_action.py
  - src/schemas/decision_scale.py
  - src/utils/data_processing.py
  - src/llm/backend_registry.py
  - src/services/analysis_context_builder.py
  - src/schemas/analysis_context_pack.py
  - src/analysis_context_pack_prompt.py
  - src/analysis_context_pack_overview.py
  - src/agent/factory.py
  - src/config.py
  - src/report_language.py
  - src/llm/backend_factory.py
  - src/llm/litellm_backend.py
  - src/market_phase_prompt.py
  - src/market_structure_prompt.py
  - src/services/daily_market_context.py
depends:
  - analysis-context.md
  - research.md
status: ready
---

# 기본 LLM 판단

> 강화된 종목 context와 선택적 뉴스 텍스트를 프롬프트로 바꾸고 LLM 응답을 `AnalysisResult`로 파싱한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. context·뉴스 등 수집 artifacts로 품질 pack을 만들고 prompt 요약과 공개 overview를 렌더링한다. 실패하면 빈 요약·null overview로 계속한다.
2. 언어·skill·system prompt를 정하고 설정된 지연을 적용한 뒤 이름과 backend 가용성을 확인한다.
3. 데이터 텍스트를 만들고 생성 요청한다.
4. 응답 JSON을 검증·파싱하고 결과에 원문, 검색 여부, 시장 스냅샷과 모델을 붙인 뒤 chip 가용성을 한 차례 정규화한다.
5. 선택적 무결성 검사에 실패하면 설정 횟수까지 보완 재요청하고, 소진 시 placeholder를 채운다.
6. 결과를 반환하여 호출자가 후처리한다. 설정·생성·파싱 실패는 실패 상태 결과로 표현한다.

### 1.2 범위·통합 지점

- 제공: 단일 기본 분석 요청과 판단기 생성 `AnalysisResult` 계약.
- 제외: 뉴스 수집, context 구성, Agent 경로, 결과 보정·저장·주문 경계는 별도 스펙이다. 생성 backend의 프로세스 실행 및 벤더 transport 내부는 외부 어댑터 경계로 취급한다. analyzer 내부 chip 보정과 그 뒤 후처리는 [decision-output](decision-output.md)에 설명하며 순환을 피하려고 depends에 넣지 않는다.
- 선행 계약: [analysis-context](analysis-context.md)의 map, [research](research.md)의 optional news 텍스트. 생성 backend는 prompt·system prompt와 설정을 받아 텍스트·model·usage를 반환하거나 오류를 낸다.
- 부작용: 요청 전 설정 지연, 외부 생성 호출, 로그와 조건부 usage 기록. callback 예외는 무시한다.

### 1.3 인터페이스와 데이터 의미

| 항목 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `analyze` | context map, news_context optional string, progress callback, stream callback, optional summary → `AnalysisResult` | 검색 여부는 `bool(news_context)`이며 검색 실행 여부와 같다고 보장하지 않는다. |
| `AnalysisResult` | 객체 | 필수 `code`, `name`, `sentiment_score` int, `trend_prediction`, `operation_advice`; `decision_type` 기본 hold, confidence 기본 중, action·label optional, dashboard optional map. 전체 필드·초기값은 C-01. 모델 응답의 주석상 0–100은 parser가 clamp하지 않는다. |
| 상세 결과 | 문자열 | 추세·단기/중기 전망·기술/MA/거래량/패턴·기본면/업종/회사·뉴스/감성/화제·요약/요점/위험/매매 이유. 기본 빈 문자열. |
| 메타데이터 | optional map/string/bool | 시장 snapshot·raw_response·model_used·current_price·change_pct·query_id 등. `success`, `error_message`는 실패를 구분한다. |
| 생성 설정 | 환경변수 | `GENERATION_BACKEND` 기본 `litellm`, `GENERATION_FALLBACK_BACKEND` 미설정 시 `litellm`(primary와 같으면 비활성), `GEMINI_REQUEST_DELAY=2.0`초, `REPORT_INTEGRITY_ENABLED=true`, `REPORT_INTEGRITY_RETRY=1`(0 이상). `LLM_TEMPERATURE` 우선, 미설정·파싱 실패 시 provider별 legacy 값 및 최종 기본값 0.7을 사용한다. `LITELLM_FALLBACK_MODELS`는 쉼표 목록이며 비어 있으면 채널 목록 또는 legacy Gemini fallback을 구성할 수 있다(C-15). |
| context pack 출력 | summary string, overview optional map | summary는 값 자체를 생략한 저민감 품질 정보로 prompt에 삽입하고, overview는 결과 후처리에 전달한다. |
| dashboard | optional map | 원본 JSON을 유지하고 attribution 및 action 등 일부를 정규화한다. 선언 schema의 주요 블록은 `core_conclusion`, `data_perspective`, `intelligence`, `battle_plan`, `phase_decision`, `signal_attribution`, `agent_disagreement_explanation`; 실제 parser는 전체 schema 준수를 강제하지 않는다(C-02, C-03). |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-00 | 판단 전 context pack 조립 | quote·daily_bars·technical·chip·fundamentals·news와 선택적 portfolio 블록을 만들고 품질 가중 점수·상태를 계산한다. pack 생성이나 외부 렌더 호출에서 예외가 전파되면 빈 summary·null overview로 진행한다. overview 렌더러가 내부에서 처리한 오류는 summary를 유지하고 overview만 null이다. | 코드 확인 |
| R-01 | backend 설정 오류로 fallback 불가 또는 모델 불가 | 점수 50, 횡보·보유·낮은 confidence, `success=false`와 오류를 반환한다. | 코드 확인 |
| R-02 | 생성 가능 | 프롬프트와 system prompt를 만들고 temperature 설정, 최대 출력 토큰 8192, stream 및 JSON validator를 사용한다. 모델 호출·fallback은 C-04. | 코드 확인 |
| R-02a | 생성 실패 또는 validator 실패 | LiteLLM은 기본 모델 다음 설정된 fallback 모델 순서로 시도한다. stream 예외면 같은 모델을 non-stream으로 재시도한다. backend 수준 fallback은 fallbackable 오류와 설정된 대체 backend가 있을 때 실행한다. | 코드 확인 |
| R-02b | 프롬프트 구성 | 한국어는 영어 구조에 한국어 출력 지시를 추가한다. 일봉·실시간·기본면·추세·뉴스를 있는 대로 넣고 결측 경고와 index/ETF 제약을 조건부 추가한다. 뉴스 윈도는 context의 양의 정수 우선, 아니면 설정에서 해석한다. | 코드 확인 |
| R-03 | 유일한 JSON object | fenced 또는 비 fenced object를 선택·보정한다. schema 검증 예외는 경고만; 최소 5개 키 중 하나가 있어야 하고 sentiment_score는 int 변환 가능해야 한다. 파싱 시 부족한 필드는 C-03 기본값을 쓴다. | 코드 확인 |
| R-04 | 모든 모델의 응답이 유효하지 않지만 마지막 텍스트가 있음 | 해당 텍스트를 파싱 시도한다. 텍스트 폴백은 키워드별 존재 수 차이가 2 이상이면 65/buy 또는 35/sell, 아니면 50/hold; 앞 500자를 요약하고 `success=false`다. | 코드 확인 |
| R-05 | 무결성 검사 활성·누락 | 점수·advice·요약·한 줄 결론·risk_alerts 목록을 검사하고 buy/hold면 stop_loss도 검사한다. phase context가 map이면 phase 필드도 검사한다. 설정 횟수만큼 이전 응답과 누락 필드를 포함해 재요청하고 소진하면 placeholder를 채워 계속 반환한다(C-09). | 코드 확인 |
| R-06 | 생성·파싱 중 예외 | 안전화된 오류와 50·횡보·보유·낮은 confidence를 가진 실패 결과를 반환한다. | 코드 확인 |
| R-03b | 모델 응답 파싱 직후 | context의 chip으로 chip 가용성을 정규화한다. 호출자는 이후 원본 chip으로 같은 helper를 다시 호출하며 세부 보정 계약은 [decision-output](decision-output.md) R-01에 있다. | 코드 확인 |
| R-03a | action 및 attribution | 명시 action을 먼저 해석하고 불명확하면 operation_advice로 유도한다. 판단기 파싱 시 점수 정렬은 꺼져 있다. attribution 4개 값을 정규화한다(C-10). | 코드 확인 |
| R-07 | 암묵적으로 builtin bull_trend가 기본 선택됨 | legacy prompt에 기본 skill 기준을 넣는다. 유효한 명시 skill 선택이면 그 baseline을 자동 주입하지 않는다. 기준에는 MA5 이격률, MA 정렬, chip·리스크 규칙이 포함된다. 이는 프롬프트 지시이며 결정적 코드 강제가 아니다. | 코드 확인 |

프롬프트의 canonical score 척도는 80–100 strong buy, 60–79 buy, 40–59 watch, 20–39 reduce, 0–19 sell이다(C-11). 이는 지시이며 parser가 score를 이 구간으로 강제하지 않는다.

프롬프트 핵심 원문과 번역(C-05):

- “when the price deviates more than 5% above MA5, do not buy” — 가격이 MA5보다 5% 넘게 높으면 매수하지 않는다.
- “Required bullish alignment: MA5 > MA10 > MA20” — 필수 상승 정렬은 MA5 > MA10 > MA20이다.
- “Ignore all news whose publication date is unknown” — 게시일을 알 수 없는 뉴스는 무시한다(C-07).
- “Strong trend stocks may relax the bias requirement” — 강한 추세 종목은 이격률 조건을 완화할 수 있다. 같은 정책에 엄격한 금지와 완화가 함께 있으므로 코드가 우선순위를 해소한다고 가정하지 않는다.

- 미결정: 없음. 선행 analysis-context·research의 입력 계약과 상태를 대조했다.
- 호출 비용 경계: 정상·완전 응답이면 생성 요청 1회다. 기본 integrity 설정에서는 누락 시 전체 보고서를 최대 1회 추가 요청해 정상 모델 기준 최대 2회다. 각 요청에 대해 모델 fallback, stream 실패 후 같은 모델의 non-stream 재요청, Router 내부 재시도와 backend fallback이 추가될 수 있으므로 외부 호출 총수의 고정 상한을 이 스펙에서 단정하지 않는다(R-02, R-02a, R-05).
- 확인 한계: LLM과 외부 backend는 실행하지 않았다. 프롬프트 준수는 보장되지 않는다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-00 | `src/core/pipeline.py:799-823,3072-3108,3160-3186`; `src/schemas/analysis_context_pack.py:19-117`; `src/services/analysis_context_builder.py:21-116,119-565,568-783`; `src/analysis_context_pack_prompt.py:1-521`; `src/analysis_context_pack_overview.py:1-94,125-326` | pack 상태·점수, 생성과 prompt/공개 overview 렌더링 | R-00 |
| C-01 | `src/analyzer.py:1718-1800` `AnalysisResult` | 결과 필드와 기본값 | R-01, R-03, R-04, R-06 |
| C-02 | `src/schemas/report_schema.py:18-218,219-347,351-388` | 선언된 dashboard 및 보고서 스키마. schema 모델은 검증용이며 결과를 다시 직렬화하지 않음 | R-03 |
| C-03 | `src/analyzer.py:5296-5401,5427-5590,5592-5659` | JSON 선택·최소 검증·파싱·텍스트 폴백 | R-03, R-04 |
| C-04 | `src/analyzer.py:3989-4311` `analyze` | backend 확인·호출·무결성 재시도·실패 결과 | R-01, R-02, R-05, R-06 |
| C-06 | `src/analyzer.py:2631-2733,3489-3602,3604-3879` | skill·system 구성, backend 수준 폴백과 LiteLLM 모델별 호출 | R-02, R-02a, R-07 |
| C-07 | `src/analyzer.py:4313-5093,5095-5196` | 입력 프롬프트·조건부 섹션·포맷 및 시장 snapshot | R-02b |
| C-08 | `src/llm/backend_registry.py:10-31,43-117`; `src/llm/backend_factory.py:14-45`; `src/llm/litellm_backend.py:26-71` | backend 선택과 LiteLLM adapter 경계 | R-02a |
| C-09 | `src/analyzer.py:123-147,327-520,5198-5294` | 필수 필드 검사·언어별 placeholder 및 retry prompt | R-05 |
| C-10 | `src/analyzer.py:1900-1925`; `src/schemas/decision_action.py:1-401`; `src/utils/data_processing.py:353-448` | action 및 attribution 정규화 | R-03a |
| C-12 | `src/agent/factory.py:158-217,496-550`; `src/agent/skills/defaults.py:108-117,127-246` | skill 선택과 기본 정책 주입 조건 | R-07 |
| C-13 | `src/analyzer.py:148-237,709-882`; `src/market_phase_prompt.py:1-217`; `src/market_structure_prompt.py:1-186`; `src/services/daily_market_context.py:635-713`; `src/config.py:329-340` | 프롬프트의 phase·market·trend helper 및 뉴스 창 | R-02b |
| C-14 | `src/report_language.py:11-135,301-317,770-821,838-848,858-928,947-999,1234-1263` | 언어별 기본값·advice, trend, confidence 및 decision_type 추론 | R-01, R-03, R-04, R-05 |
| C-15 | `src/config.py:753-795,951-963,1002-1002,1185-1186,1567-1585,1623-1667,1680-1688,1912-1912,2169-2170`; `src/llm/backend_registry.py:88-117` | 환경 기본값, 모델 및 backend fallback | R-02, R-02a, R-05 |
| C-11 | `src/schemas/decision_scale.py:19-48`; `src/analyzer.py:1949-2135,2136-2320,2458-2580` | system prompt, score/action 척도와 출력 요구 | R-07 |
| C-05 | `src/agent/skills/defaults.py:26-94` `CORE_TRADING_SKILL_POLICY_ZH`, `CORE_TRADING_SKILL_POLICY_EN` | 기본 정책과 수치 | R-07 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. backend와 callback은 대체물이며 실제 모델·네트워크 동작을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-00 | R-00 | pack 생성에서 예외 발생 | summary 빈 문자열, overview null; 판단 호출은 계속 |
| T-01 | R-01 | 사용 가능한 모델 없음 | `success=false`, 점수 50 및 낮은 confidence |
| T-02 | R-03 | 유일한 JSON `{"sentiment_score":70}` | int 점수 70, 누락 필드는 parser 기본값, 성공 결과 |
| T-02a | R-02a | 첫 모델이 validator 실패, 두 번째가 유효 JSON 반환 | 두 번째 모델 결과를 반환 |
| T-03 | R-04 | JSON이 아닌 텍스트에 `bullish buy`만 포함 | 점수 65, buy, `success=false`, 원문 앞 500자 요약 |
| T-04 | R-05 | 무결성 실패, 재시도 한도 0 | placeholder를 채우고 반환 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-00 / T-00 | C-00 | pack 생성·예외 분기와 렌더러 확인 |
| R-01 / T-01 | C-04 | 설정·가용성 실패 분기 |
| R-02 / R-02a / T-02a | C-04, C-06, C-08, C-15 | 호출 인자·라우팅·폴백 확인 |
| R-02b | C-07, C-13 | 조건부 입력 섹션과 언어·뉴스 윈도 확인 |
| R-03 / T-02 | C-01, C-03, C-14 | validator와 parser 기본값 확인 |
| R-04 / T-03 | C-03, C-04, C-14 | fallback과 키워드 비교 확인 |
| R-03b | C-04; [decision-output](decision-output.md) C-01 | 호출 순서 확인 |
| R-03a | C-10 | action 우선순위와 attribution 정규화 확인 |
| R-05 / T-04 | C-04, C-09, C-14, C-15 | 재시도·소진 분기 확인 |
| R-06 | C-04 | 예외 분기 확인 |
| R-07 | C-05, C-06, C-11, C-12 | skill 정책 선택 경로와 원문 확인 |
