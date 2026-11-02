---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/schemas.py
  - tradingagents/agents/structured.py
  - tradingagents/agents/rating.py
depends: []
status: ready
---

# S2 구조화 판단·등급

> 의견·행동·최종 등급의 스키마와 텍스트 렌더링·구조화 실패 폴백·등급 파싱 계약을 정의한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 역할별 스키마를 LLM의 with_structured_output에 바인딩한다.
2. 구조화 호출이 유효한 결과를 주면 타입 필드를 사용하고 Markdown으로 렌더링한다.
3. 바인딩이 지원되지 않거나 구조화 호출이 실패하면 caller가 동일 prompt로 일반 LLM을 호출한다.
4. 자유 텍스트 최종 등급은 라벨 문법으로 읽고 판별 불가면 REVIEW를 반환한다.
5. 완료 상태의 final_rating이 truthy면 재파싱하지 않고 우선 사용한다.

### 1.2 범위·통합 지점

- 제공: 스키마·직렬화·파서·공용 폴백 helper.
- 제외: 각 역할 prompt의 입력 조립·최종 상태 기록은 투자/리스크/감성 기능 소유. 가격 필드는 주문 실행 계약이 아니다.
- 외부 경계: 구조화 runnable은 스키마 인스턴스 또는 None/예외를 반환한다. SDK 검증·모델 서비스는 외부 의존.
- 소유 상태·부작용: 문자열/객체 변환과 경고 로깅; 원장·파일을 변경하지 않는다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| PortfolioRating / TraderAction | 각각 5등급 / 3행동 enum | Buy·Overweight·Hold·Underweight·Sell / Buy·Hold·Sell. 자동 변환표 없음 |
| ResearchPlan | recommendation:5등급, rationale/strategic_actions:string | 모두 필수. 렌더 포맷 C-02 |
| TraderProposal | action:3행동, reasoning:string, entry_price/stop_loss:optional number, position_sizing:optional string | 선택 필드 기본 null; 가격은 호가통화 절대값이라는 prompt 지시. 양수/비중 상한은 schema가 강제하지 않음 |
| PortfolioDecision | rating:5등급, executive_summary/investment_thesis:string, price_target:optional number, time_horizon:optional string | 선택 필드 기본 null; 가격·보유기간·크기에 실행 코드 한도 없음 |
| SentimentReport | overall_band:6단계 enum, overall_score:number[0,10], confidence:low/medium/high, narrative:string | band별 점수 구간과 표본 부족 confidence 기준은 지시문이며 코드 일치 검사 없음 |
| bind_structured / invoke_structured | model+schema / runnable+prompt → runnable? / typed? | 없으면 null. invoke_structured_or_freetext는 render 함수와 plain model을 받아 최종 문자열 반환 |
| extract_rating / parse_rating / run_rating | string→optional rating / string→rating-or-default / state→string | parse_rating default="REVIEW"; run_rating은 truthy final_rating 우선. REVIEW는 거래 가능한 등급이 아님 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 스키마 입력·선택 숫자 | C-01의 coercion과 각 스키마를 사용한다. 문자열의 %, 범위·N/A 등은 null로 만들고 통화기호·쉼표를 제거한 단일 숫자는 변환한다. 일반 string 필드는 길이·서술 품질을 검증하지 않는다. | 코드 확인 |
| R-02 | 정상 구조화 결과 | C-02·C-03·C-04·C-05의 고정 라벨·순서를 보존한다. 미제공 optional 출력 표시는 각 renderer의 not provided 규칙을 따른다. | 코드 확인 |
| R-03 | 스키마 바인딩 실패 | NotImplementedError 또는 AttributeError만 경고 후 null. 다른 바인딩 예외는 전달한다. | 코드 확인 |
| R-04 | 구조화 invoke 실패/None | 모든 Exception 또는 None을 경고 후 null로 바꾼다. 공용 or_freetext는 이후 일반 호출 1회 수행하며 그 예외는 잡지 않는다. 일반 호출 실패를 Hold/REVIEW로 강제 대체하지 않는다. | 코드 확인 |
| R-05 | 텍스트 등급 추출 | NFKC 정규화·라벨/자기 등급 우선순위·충돌 처리는 C-07 문법 그대로. 등급 단어만 있는 문장은 등급으로 간주하지 않는다. | 코드 확인 |
| R-06 | 완료 상태 등급·REVIEW | run_rating은 final_rating truthy면 그대로 사용한다(재검증 없음). 아니면 final_trade_decision을 parse_rating. parse_rating 판별 불가는 default, is_review는 REVIEW와 정확 비교. | 코드 확인 |

- 미결정: 없음(선언한 범위의 원본 경계).
- 확인 한계: 외부 API·모델·LangGraph를 실행하지 않았다. 아래 사례는 구현에서 도출했으며 테스트 실행 결과가 아니다.

### 1.5 필수 코드 참조

기준은 frontmatter의 SHA이며 원본 레포 루트 상대 경로다. C-ID가 지시하는 표·포맷·분기·알고리즘은 해당 범위를 함께 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/schemas.py:30-87` · `_NULLISH_FLOAT`, `_coerce_optional_float`, enums | 선택 수치 변환·정확한 enum값 | R-01 |
| C-02 | `tradingagents/agents/schemas.py:95-138` · `ResearchPlan`, `render_research_plan` | 스키마 설명이 모델 지시에도 쓰임. enum C-01 | R-01, R-02 |
| C-03 | `tradingagents/agents/schemas.py:146-213` · `TraderProposal`, `render_trader_proposal` | 가격 validator C-01·ACTION 라벨 및 후미 FINAL TRANSACTION PROPOSAL | R-01, R-02 |
| C-04 | `tradingagents/agents/schemas.py:221-288` · `PortfolioDecision`, `render_pm_decision` | PM 필드·renderer. 가격 validator C-01 | R-01, R-02 |
| C-05 | `tradingagents/agents/schemas.py:296-379` · `SentimentBand`, `SentimentReport`, `render_sentiment_report` | 감성 enum·제약·포맷 | R-01, R-02 |
| C-06 | `tradingagents/agents/structured.py:36-95` · `NO_EXTERNAL_TOOLS`, bind/invoke helpers | 바인딩·호출 폴백과 외부 도구 금지 문구 | R-03, R-04 |
| C-07 | `tradingagents/agents/rating.py:22-117` · 상수·정규식·extract/parse/run_rating/is_review | 파서에 쓰이는 내부 상수 포함 전체 문법 | R-05, R-06 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 모델·SDK·네트워크는 정상/오류를 반환하는 대체물로 가정하며 실제 서비스 호환성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | entry_price="$1,234.50", stop_loss="15%" | 1234.5와 null로 전처리 |
| T-02 | R-02 | PM optional price_target/time_horizon 생략 | 두 라벨 모두 not provided로 렌더링 |
| T-03 | R-03, R-04 | 바인딩 NotImplementedError / invoke 일시 오류, 이후 plain 성공 | 전자 null, 후자 null 후 일반 호출하여 문자열 반환 |
| T-04 | R-04 | plain invoke도 예외 | 호출자까지 예외 전달, Hold로 덮어쓰지 않음 |
| T-05 | R-05 | 텍스트 Rating: Buy 줄로 시작하고 뒤에 인용 Rating: Sell | 처음 자기 등급 Buy |
| T-06 | R-05 | - Rating: Buy 및 - Rating: Sell만 있음 / 본문 not a Sell만 있음 | 각각 판별 불가, parse_rating 기본 REVIEW |
| T-07 | R-06 | state.final_rating="Hold", 본문 Rating: Sell | Hold 반환 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-01, R-02 | C-02 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-01, R-02 | C-03 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-01, R-02 | C-04 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-01, R-02 | C-05 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-03, R-04 | C-06 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-05, R-06 | C-07 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
