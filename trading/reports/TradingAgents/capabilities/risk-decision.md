---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/risk_mgmt/aggressive_debator.py
  - tradingagents/agents/risk_mgmt/conservative_debator.py
  - tradingagents/agents/risk_mgmt/neutral_debator.py
  - tradingagents/agents/managers/portfolio_manager.py
  - tradingagents/graph/conditional_logic.py
  - tradingagents/graph/setup.py
depends:
  - run-state.md
  - configuration.md
  - run-input.md
  - decision-contract.md
  - investment-decision.md
status: ready
---

# 리스크 토론·최종 판단

> 트레이더 제안과 분석 근거를 세 리스크 역할이 논쟁하고 PM이 최종 등급과 근거를 만든다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. Trader 이후 Aggressive가 먼저 발언한다.
2. Aggressive→Conservative→Neutral 순서로 각자 논거와 이전 두 역할 발언을 읽는다.
3. 각 발언 뒤 count·latest_speaker로 반복 또는 PM 종료를 결정한다.
4. PM은 리스크 이력·연구계획·트레이더 제안·보유 문맥·있을 때 과거 교훈을 종합한다.
5. typed 판단 성공 시 rating을 그대로 쓰고, 자유텍스트 fallback만 등급을 파싱해 최종 상태를 반환한다.

### 1.2 범위·통합 지점

- 제공: 리스크 토론 및 최종 판단.
- 제외: 주문 실행·승인 절차·결정적 수량 산정·하드 한도. 메모리 조회는 외부 단계가 만든 past_context만 받는다.
- 선행: S1·S2·설정, 투자 판단의 보고서/상대 공백 helper.
- 상태: risk_debate_state, final_trade_decision, final_rating.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 리스크 노드 | 4개 report + trader_investment_plan + portfolio_context + risk_debate_state → 부분 상태 | quick 모델, 각 역할 history·current response·count |
| Portfolio Manager | 투자계획·트레이더 제안·리스크 이력·past_context → 최종 상태 | deep 모델, 원본 분석가 보고서 각각을 직접 삽입하지 않는다 |
| final_rating | string | Buy/Overweight/Hold/Underweight/Sell 또는 REVIEW |
| max_risk_discuss_rounds | 정수 설정 | 기본1. 누적 발언 count를 3×라운드와 비교 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 리스크 역할별 발언 | 공격적은 고위험·고수익, 보수적은 자산 보전·변동성 최소화, 중립은 양쪽의 균형·분산을 논한다. 4개 보고서·트레이더 제안·보유 현황·종목 문맥·이력·다른 두 역할의 최신 발언을 프롬프트로 넣는다. 보고서·상대 공백은 투자 판단 계약의 표식 사용. | 코드 확인 |
| R-02 | 리스크 상태 갱신 | 역할 접두사 붙인 response를 전체 history와 자신의 history에 추가하고 자신의 current response, latest_speaker를 설정, count+1. 다른 역할의 history·응답은 보존한다. | 코드 확인 |
| R-03 | 리스크 분기 | count≥3×설정 라운드이면 PM. 아니면 latest_speaker가 Aggressive면 Conservative, Conservative면 Neutral, 나머지는 Aggressive. 첫 Aggressive 이후 검사하므로 0라도 첫 발언은 실행한다. | 코드 확인 |
| R-04 | PM 프롬프트 | 연구계획·트레이더 제안·리스크 이력·종목·보유 문맥을 넣고 past_context가 truthy일 때만 교훈 섹션을 넣는다. 강한 쪽을 근거로 결정하되 근거가 균형이거나 부족할 때 Hold를 지시한다. 외부 도구·웹검색을 하지 말라는 S2 지시 포함. | 코드 확인 |
| R-05 | PM 생성 성공·실패 | typed 성공이면 렌더링 문자열과 decision.rating.value를 쓴다. typed 미지원·실패는 자유텍스트 호출 후 parse_rating한다. 등급이 모호하거나 없으면 REVIEW. 자유텍스트 invoke 자체 실패는 전파한다. | 코드 확인 |
| R-06 | 최종 반환 | risk_debate_state의 다른 필드·count는 보존, latest_speaker=Judge, final_trade_decision과 final_rating 반환. PM은 과거 등급·Trader 방향과의 일치를 강제하거나 가격·비중을 수치 한도로 덮어쓰지 않는다. | 코드 확인 |
| R-07 | 리스크 노드 모델 오류 | 토론자 invoke 예외는 노드 자체에서 포착하지 않아 전파한다. 세 의견을 수치 가중평균·다수결로 합산하지 않고 PM LLM이 정한다. | 코드 확인 |

- 미결정: 없음. 선행 스펙을 대조했고 선언한 범위의 원본 경계는 정해져 있다.
- 확인 한계: 설치·실행 및 실제 모델·외부 API 응답 검증은 하지 않았다. 프롬프트 지시가 모델 응답에 항상 지켜진다는 보장은 없다.

### 1.5 필수 코드 참조

기준은 frontmatter SHA이며 경로는 원본 레포 상대 경로다. 호출한 공통 helper는 위 선행 계약에서 정의한다.
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/risk_mgmt/aggressive_debator.py:10-68 create_aggressive_debator` | 공격 역할 프롬프트·상태 | R-01, R-02, R-07 |
| C-02 | `tradingagents/agents/risk_mgmt/conservative_debator.py:10-70 create_conservative_debator` | 보수 역할 프롬프트·상태 | R-01, R-02, R-07 |
| C-03 | `tradingagents/agents/risk_mgmt/neutral_debator.py:10-68 create_neutral_debator` | 중립 역할 프롬프트·상태 | R-01, R-02, R-07 |
| C-04 | `tradingagents/graph/conditional_logic.py:23-33 should_continue_risk_analysis; tradingagents/graph/setup.py:175-185 setup_graph` | 리스크 진입·종료 조건·PM→END | R-03 |
| C-05 | `tradingagents/agents/managers/portfolio_manager.py:23-106 create_portfolio_manager` | PM 프롬프트·교훈 삽입·typed rating·상태 반환 | R-04, R-05, R-06 |
| C-07 | `tradingagents/graph/setup.py:132-140 setup_graph` | 토론자·Trader quick, RM·PM deep 모델 조립 | R-02, R-04 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 모델·네트워크를 대체 응답으로 바꿔 분기를 검증하는 사례이며 모델 품질이나 실제 제공자 가용성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | 기본 라운드1·count0 | Aggressive→Conservative→Neutral→PM, count3 |
| T-02 | R-04 | past_context 빈 문자열 | 교훈 섹션 없음 |
| T-03 | R-05 | typed rating=Sell, 본문에 Buy 인용 포함 | final_rating=Sell; 본문을 재파싱하지 않는다 |
| T-04 | R-05 | fallback 텍스트에 등급 라벨 없음 | final_rating=REVIEW |
| T-05 | R-06 | PM 완료 | latest_speaker=Judge, count·토론 이력 보존 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-02, R-07 | C-01 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01, R-02, R-07 | C-02 | 원본 코드 직접 열람, 실행하지 않음 |
| R-01, R-02, R-07 | C-03 | 원본 코드 직접 열람, 실행하지 않음 |
| R-03 | C-04 | 원본 코드 직접 열람, 실행하지 않음 |
| R-04, R-05, R-06 | C-05 | 원본 코드 직접 열람, 실행하지 않음 |

모델 계층은 C-07에서 확인했다.

T-ID의 기대 결과는 해당 R-ID 및 C-ID의 분기에서 도출했다. 테스트는 이름 검색까지만 참고했으며 수락 사례의 출처로 삼지 않았다.

판단 기준 원문(R-04): “Ground every conclusion in specific evidence from the analysts.”

번역: “모든 결론은 분석가가 제시한 구체적 근거에 기반하라.” 프롬프트 지시이며 인용 유효성의 코드 검증은 아니다.

[핵심 원본](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/agents/risk_mgmt/aggressive_debator.py#L10-L68).

## 적용 메모

분석자 의견: 국장·미장 모두 최종 등급을 주문으로 연결할 때 자연어 비중과 별개로 주문 계층의 수치 한도·가격 유효성을 검증해야 한다. 이 변경은 원본 스펙에 포함하지 않는다.
