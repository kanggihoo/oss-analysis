---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/core/pipeline.py
  - src/agent/factory.py
  - src/agent/executor.py
  - src/agent/runner.py
  - src/agent/orchestrator.py
  - src/agent/risk_override.py
  - src/agent/tools/execution.py
  - src/agent/skills/router.py
  - src/agent/skills/aggregator.py
  - src/agent/protocols.py
  - src/agent/llm_adapter.py
  - src/agent/tools/registry.py
  - src/agent/agents/base_agent.py
  - src/agent/memory.py
  - src/agent/skills/engine.py
  - src/agent/skills/synthesis.py
  - src/agent/skills/deliberation.py
  - src/agent/skills/base.py
  - src/agent/skills/defaults.py
  - src/agent/agents/technical_agent.py
  - src/agent/agents/intel_agent.py
  - src/agent/agents/risk_agent.py
  - src/agent/agents/decision_agent.py
  - src/agent/skills/skill_agent.py
  - strategies/bull_trend.yaml
  - strategies/ma_golden_cross.yaml
  - strategies/volume_breakout.yaml
  - strategies/shrink_pullback.yaml
  - strategies/bottom_volume.yaml
  - strategies/box_oscillation.yaml
  - strategies/chan_theory.yaml
  - strategies/wave_theory.yaml
  - strategies/one_yang_three_yin.yaml
  - strategies/dragon_head.yaml
  - strategies/emotion_cycle.yaml
  - strategies/hot_theme.yaml
  - strategies/event_driven.yaml
  - strategies/expectation_repricing.yaml
  - strategies/growth_quality.yaml
  - src/agent/tools/search_tools.py
  - src/agent/news_evidence.py
  - src/agent/tools/data_tools.py
  - src/agent/tools/analysis_tools.py
  - src/agent/tools/market_tools.py
  - src/agent/tools/backtest_tools.py
  - src/agent/tools/fxmacrodata_tools.py
  - src/agent/final_explanation.py
  - src/agent/dashboard_payload.py
  - src/agent/skills/scheduler.py
  - src/config.py
depends:
  - data-collection.md
  - research.md
  - llm-decision.md
status: ready
---

# Agent 판단 패밀리

> 명시된 Agent 설정 또는 skill 선택으로 단일 tool loop나 multi-agent 판단을 실행하고 AnalysisResult로 변환한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 사전 수집과 추세 분석 후 Agent 활성 조건이면 기본 뉴스 prefetch 전에 분기한다.
2. skill과 tool registry, LLM adapter를 구성하고 single 또는 multi executor를 만든다.
3. 기존 시세·추세·펀더멘털, 시장 및 보유 컨텍스트와 social·로컬 인텔을 준비한다.
4. single은 tool loop로 dashboard를 만들고, multi는 모드별 specialist 체인을 수행한다.
5. multi는 선택적 risk override를 거친 dashboard를 정규화하고 결과를 AnalysisResult로 바꾼다.
6. 약한 무결성 보완 및 공통 결과 보정 후 설명을 만들고 이력 저장과 별도 신호 추출을 시도한다.

### 1.2 범위·통합 지점
- 제공: Agent 활성화·실행·skill 선택·tool loop·multi 조합·risk override·결과 변환.
- 외부 의존: 수집 컨텍스트와 설정·LLM·tool provider·DB. [결과 후처리](decision-output.md)는 보정·저장·신호 추출을 소유한다. [뉴스·리서치](research.md)의 기본 prefetch는 실행하지 않으며 로컬 인텔 helper와 social을 공유한다.
- 소유 상태: 한 실행의 대화·도구 호출 로그·news evidence와 multi stage 결과. 성공 시 히스토리 저장 및 별도 단건 뉴스 저장을 시도한다.

### 1.3 인터페이스와 데이터 의미
| 항목 | 타입 | 의미 |
|---|---|---|
| 활성 조건 | bool / list | `agent_mode` 참, 요청 skills가 비어 있지 않음, 또는 설정 `agent_skills`가 비어 있지 않고 `['all']`이 아니면 활성화. API 키만으로 활성화하지 않는다. |
| `agent_arch` | string | 정확히 `multi`이면 orchestrator, 그 외 single. |
| 초기 context | map | stock_code/name, report_type/language, fundamental, 선택적 quote/chip/trend, phase/market/portfolio, social·로컬 인텔 등. 지수는 일부 도구를 제거한다. |
| AgentResult → AnalysisResult | object | success/error·provider/model을 보존하고 dashboard 값을 변환. 실패도 실패 AnalysisResult가 될 수 있고 외부 예외는 None이다. |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Agent 활성 | 기본 검색 단계보다 먼저 분기하고 executor를 호출한다. 초기 context에 기존 데이터와 social·로컬 인텔을 넣고 이력 확보를 시도한다. | 코드 확인 |
| R-02 | skill 선택 | 요청이 설정을 우선하고 유효 ID를 순서 보존·중복 제거한다. 유효 선택이 없으면 기본 skill; 암묵적 내장 bull_trend만 legacy prompt를 쓴다. | 코드 확인 |
| R-03 | single | prompt는 시세·일봉 → 기술·칩 → 뉴스 → dashboard의 단계와 도구에서 숫자를 얻고 실패 도구를 반복하지 말 것을 지시한다. 이는 prompt 규칙이며 강제 실행 보장은 아니다. | 코드 확인 |
| R-04 | tool loop | 등록된 도구 선언을 LLM에 전달하고 응답의 tool call을 실행해 결과를 대화에 붙인다. 단계·시간 예산 또는 LLM 오류와 JSON 파싱 실패는 실패 결과로 전달한다. | 코드 확인 |
| R-05 | multi | quick=technical→decision, standard=technical→intel→decision, full=technical→intel→risk→decision, specialist=full에 decision 직전 최대 4개 skill specialist를 병렬 삽입한다. intel·risk·skill 실패는 degraded로 계속하나 critical 단계 실패는 종료한다. | 코드 확인 |
| R-10 | specialist routing | 요청 skill 우선, manual 설정 다음, technical opinion의 상승(bullish·점수 ≥70)·하락(bearish·≤30)·횡보(neutral 또는 35~65)·변동(heavy·30~70) 순으로 regime을 판정하고 해당 skill을 고른다. 최대 4개다. | 코드 확인 |
| R-11 | specialist 합산 | 유효한 skill 의견의 신호점수와 confidence를 가중 평균한다. 유효 의견이 없거나 가중치 합이 0 이하면 score 3, confidence 0, hold; 조정값은 별도 합계다. 가중치는 confidence × 유효한 성과 factor이며 조회 실패는 factor 1이다. score 기준 ≥4.5 strong_buy, ≥3.5 buy, ≥2.5 hold, ≥1.5 sell, 나머지 strong_sell. 합산은 decision 입력이며 최종 signal 자체를 확정하지 않는다. | 코드 확인 |
| R-12 | 모델·도구 실패 | LLM adapter는 설정한 모델을 순서대로 시도하고 전체 실패를 provider=`error`로 돌려준다. 같은 provider의 rate-limit 다음 모델 전에만 짧게 backoff한다. 한 응답의 여러 도구는 최대 5개 worker로 병렬 실행하되 결과 메시지는 호출 순서를 따른다. 동일 도구·인자의 `retriable=false` 오류와 timeout은 실행 내 재사용한다. timeout worker 자체가 즉시 종료되는 것은 아니다. | 코드 확인 |
| R-13 | strategy 합의 | 잘못된 skill signal은 진단으로 분리한다. 유효 의견이 없는 경우는 C-14의 no-consensus 또는 no-skills 분기다. conflict가 있으면 deterministic mediator가 최대 3개 안건을 1회 다루고, 제안된 완화는 preview이며 합의 signal을 덮어쓰지 않는다. high/medium conflict는 confidence에 각각 0.85/0.93을 곱하고 실제 mediator가 있으면 high는 0.06~0.08, medium은 0.04~0.05를 추가로 뺀다. | 코드 확인 |
| R-14 | specialist 공통 실행 | 각 단계는 정해진 도구 subset과 자체 max_steps를 사용하고 이전 데이터 필드를 각각 8,000자까지 주입한다. memory가 활성화된 경우 최근 분석 최대 3개와 signal review를 읽고, calibration이 유효하면 confidence에 factor를 곱해 0~1로 제한한다. | 코드 확인 |
| R-15 | skill 파일 | 내장 `strategies/` YAML과 사용자 `AGENT_SKILL_DIR` 또는 `AGENT_STRATEGY_DIR`의 YAML·`SKILL.md` bundle을 로드한다. 같은 이름은 custom이 우선한다. 15개 내장 전략의 정확한 prompt·도구·regime은 C-18~C-22를 따른다. | 코드 확인 |
| R-16 | 공통 후처리 및 설명 | weak 무결성 뒤 chip(있는 경우) → action refresh → price position 채움 → 현재가 부착 → structure/refresh → phase/refresh → daily market/refresh 순서. 실제 action 변경만 수집한다. runtime facts와 유효한 시작·종료 action 및 온전한 action chain이 있을 때에만 기존 explanation을 지우고 새 `agent_disagreement_explanation`을 만든다. | 코드 확인 |
| R-06 | multi risk | `agent_risk_override`가 활성이고 risk `veto_buy`, `signal_adjustment=veto`, 또는 high severity flag가 있으면 buy→hold. downgrade는 buy→hold→sell 순으로 이동한다. `risk_level=high` 단독은 발동 조건이 아니다. quick·standard에는 risk 단계가 없다. | 코드 확인 |
| R-07 | dashboard | multi는 후보를 sanitize해 signal을 정하고 risk 적용 후 점수·advice 등 dashboard를 완성한다. 점수 누락 시 confidence를 0~1로 제한해 buy 65~79, hold 45~59, sell 20~39 선형 보간; override 적용 시 buy 60~79, hold 40~59, sell 0~39로 제한한다. 유효 후보가 없어도 의견이나 유의미한 context가 있으면 기본 signal hold를 쓸 수 있다. single은 파싱 실패를 실패로 반환한다. | 코드 확인 |
| R-08 | 실행 결과 | 변환 초기값은 score 50, 관망, medium이고 성공 dashboard를 읽으며 누락 점수는 trend fallback을 시도한다. 선택적 integrity 검사는 placeholder만 보충하고 LLM 재시도는 하지 않는다. 공통 보정·저장은 결과 후처리 경계다. | 코드 확인 |
| R-09 | 뉴스 evidence·실패 | Agent 실행 중 실제 도구 결과로 count를 정한다. 실행 중 성공한 검색 도구 결과도 최선 노력으로 저장한다. 종료 후 별도 단건 검색은 저장 전용이며 count에 반영하지 않는다. 검색 채널이 가용하나 도구를 호출하지 않은 경우 count는 0, 채널이 불가하면 None이다. 실행 예외는 기록 후 바깥에서 None으로 바뀌고, 성공 결과만 히스토리 저장한다. | 코드 확인 |

- 미결정: 없음.
- 확인 한계: 실행 및 외부 LLM·검색 응답은 확인하지 않았다.


### 프롬프트와 호출 수

- single prompt 원문: “绝不编造数字，所有数据必须来自工具返回结果。” 번역: 숫자를 만들어 내지 말고 모든 데이터는 도구 결과에서 가져온다. 실패 도구 재호출 금지도 프롬프트 지시다(C-03). 실제 loop가 재실행을 막는 것은 timeout 또는 `retriable=false` 등 R-12의 경우다.
- 내장 기본 정책은 “当股价偏离 MA5 超过 5% 时，坚决不买入”라고 지시한다. 번역: 주가가 MA5에서 5% 넘게 벗어나면 매수하지 않는다. 같은 정책에는 강한 추세주에 대한 완화 문구도 있어 prompt 내부의 두 지시를 함께 읽어야 한다(C-15).
- 한 loop는 LLM을 최소 1회 호출하고 도구가 나오면 다음 round가 필요하다. 기본 single의 `AGENT_MAX_STEPS=10`은 최대 10 round다. multi의 단계별 상한은 technical 6, intel 4, risk 4, decision 3, 각 skill 4다. 따라서 모든 단계가 상한까지 진행한다는 산술 상한은 quick 9, standard 13, full 17, specialist 17 + 최대 4개 skill×4 = 33 round다. 각 단계의 실패·예산 종료가 실제 횟수를 줄이고, 각 round에서 모델 fallback 또는 provider 재시도가 발생하면 실제 provider 요청은 이보다 늘 수 있다(C-05, C-06, C-12, C-16, C-17). 이는 호출 상한 계산이지 비용이나 실제 실행 측정이 아니다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/pipeline.py:556-571, 639-679, 1460-1668` | 활성 분기·초기 context·호출·evidence·호출 기록 | R-01, R-09 |
| C-02 | `src/agent/factory.py:112-217, 496-625, 689-713` | skill 선택과 executor 구성 | R-02 |
| C-03 | `src/agent/executor.py:85-342` | single legacy·일반 prompt와 dashboard 계약 | R-03 |
| C-04 | `src/agent/executor.py:651-721, 809-915` | prompt 조립·loop 결과 변환 | R-03, R-04, R-07 |
| C-05 | `src/agent/runner.py:117-253, 256-601, 608-889`; `src/agent/tools/execution.py:230-425` | 파싱, loop·tool 실행·deadline·동일 비재시도 결과 | R-04 |
| C-06 | `src/agent/orchestrator.py:531-914` | 단계·병렬 specialist·실패 | R-05 |
| C-07 | `src/agent/risk_override.py:13-56, 241-305, 308-339` 및 `src/agent/orchestrator.py:1901-1944` | risk 적용 | R-06 |
| C-08 | `src/agent/orchestrator.py:1270-1900, 1946-2207` | dashboard 구성 및 결과 helper | R-07 |
| C-09 | `src/core/pipeline.py:1669-1929, 2133-2319` | 변환·보정·저장 경계 | R-08, R-09 |
| C-10 | `src/agent/skills/router.py:25-159` | 요청·manual·regime 기반 선택 | R-10 |
| C-11 | `src/agent/skills/aggregator.py:31-41, 59-171, 205-266`; `src/agent/protocols.py:23-111, 216-295` | skill 의견 평균·정규화 | R-11 |
| C-12 | `src/agent/llm_adapter.py:336-529, 547-669, 678-949`; `src/agent/tools/registry.py:85-145, 169-245, 302-345` | LLM fallback·메시지/도구 변환·실행 | R-04, R-12 |
| C-13 | `src/agent/agents/base_agent.py:38-335`; `src/agent/memory.py:38-380` | 공통 단계·context·memory·calibration | R-14 |
| C-14 | `src/agent/skills/engine.py:26-271`; `src/agent/skills/synthesis.py:21-557`; `src/agent/skills/deliberation.py:23-283, 895-1028` | 유효 의견 분리·conflict·deterministic deliberation | R-13 |
| C-15 | `src/agent/skills/base.py:27-481`; `src/agent/skills/defaults.py:19-351`; `src/agent/factory.py:350-495` | skill 로딩·선택·prompt·registry | R-02, R-15 |
| C-16 | `src/agent/agents/technical_agent.py:23-103`; `src/agent/agents/intel_agent.py:25-119`; `src/agent/agents/risk_agent.py:30-138` | specialist prompt·도구·결과 | R-05, R-14 |
| C-17 | `src/agent/agents/decision_agent.py:24-289`; `src/agent/skills/skill_agent.py:25-132`; `src/agent/orchestrator.py:914-1133` | decision·skill prompt·병렬 합의 | R-05, R-11, R-13, R-14 |
| C-18 | `strategies/bull_trend.yaml:1-49`; `strategies/ma_golden_cross.yaml:1-46`; `strategies/volume_breakout.yaml:1-47` | 추세 전략 | R-15 |
| C-19 | `strategies/shrink_pullback.yaml:1-46`; `strategies/bottom_volume.yaml:1-49`; `strategies/box_oscillation.yaml:1-69` | 조정·반전·횡보 전략 | R-15 |
| C-20 | `strategies/chan_theory.yaml:1-58`; `strategies/wave_theory.yaml:1-64`; `strategies/one_yang_three_yin.yaml:1-37` | 구조·패턴 전략 | R-15 |
| C-21 | `strategies/dragon_head.yaml:1-44`; `strategies/emotion_cycle.yaml:1-79`; `strategies/hot_theme.yaml:1-54` | 섹터·심리 전략 | R-15 |
| C-22 | `strategies/event_driven.yaml:1-54`; `strategies/expectation_repricing.yaml:1-54`; `strategies/growth_quality.yaml:1-54` | 이벤트·기대·성장 전략 | R-15 |
| C-23 | `src/agent/tools/search_tools.py:1-256`; `src/agent/news_evidence.py:1-99` | Agent 도구 검색·즉시 저장·근거 집계 | R-09 |
| C-24 | `src/agent/tools/data_tools.py:53-737`; `src/agent/tools/analysis_tools.py:24-531`; `src/agent/tools/market_tools.py:23-116` | 시세·컨텍스트·기술·시장 도구의 선언과 반환 | R-04 |
| C-25 | `src/agent/tools/backtest_tools.py:40-282`; `src/agent/tools/fxmacrodata_tools.py:13-118` | 평가·거시 tool 선언 및 경계 | R-04 |
| C-26 | `src/agent/final_explanation.py:16-233`; `src/core/pipeline.py:1685-1832` | 실제 action 변경과 최종 설명 생성 조건·내용 | R-16 |
| C-27 | `src/agent/dashboard_payload.py:1-29`; `src/agent/orchestrator.py:153-220, 914-983`; `src/agent/skills/scheduler.py:1-176` | dashboard 예약 필드 제거·병렬 scheduler | R-05, R-07 |
| C-28 | `src/config.py:184-184, 1051-1075, 1368-1405, 1981-2002, 2050-2063` | Agent 선택·기본 단계/시간·risk·memory 설정 | R-01, R-04, R-05, R-06, R-14 |

### 1.6 수락 사례
출처: 모두 구현에서 도출. LLM·도구·DB를 대체한다.

| T-ID | 관련 R-ID | 입력 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | API 키만 설정, agent_mode false, skill 미지정 | Agent로 자동 전환하지 않는다. |
| T-02 | R-02 | 잘못된 skill만 지정 | 유효 선택이 없어 기본 skill 사용. |
| T-03 | R-05 | multi standard, intel 실패 | degraded로 기록하고 decision을 계속한다. |
| T-04 | R-06 | full, buy, high severity risk flag | override 활성 시 hold로 낮춘다. |
| T-05 | R-06 | risk_level high만 있고 flag·조정 없음 | 그것만으로 signal을 변경하지 않는다. |
| T-06 | R-09 | Agent 도구 검색 0건, 종료 후 저장용 검색 3건 | 실행 중 근거 count는 0이고 추가 검색은 변경하지 않는다. |
| T-07 | R-12 | 같은 인자로 retriable=false 도구 응답을 재요청 | 실행 내 저장한 오류를 돌려주고 도구를 재실행하지 않는다. |
| T-08 | R-13 | high conflict를 가진 두 유효 skill 의견 | confidence 보정과 1회 mediator가 실행되며 revision projection은 원 합의 signal을 변경하지 않는다. |
| T-09 | R-16 | 각 guardrail 전후 action이 같음 | 해당 단계의 조정 이력은 추가하지 않는다. |

## 2부. 근거

### 2.1 요구사항별 근거

핵심 진입점: [Agent 분기](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/core/pipeline.py#L556-L679), [risk 계획](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/agent/risk_override.py#L241-L305).
| R-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-09 | C-01, C-09 | pipeline 분기 및 예외·저장 경로 직접 확인 |
| R-02 | C-02 | 선택·default·prompt 분기 확인 |
| R-03 | C-03, C-04 | prompt 지시와 강제 실행 구별 |
| R-04 | C-04, C-05 | loop·도구 실행과 timeout helper 확인 |
| R-05 | C-06 | stage 구성·실패 분기 확인 |
| R-06 | C-07 | plan 및 적용 확인 |
| R-07 | C-04, C-08 | dashboard 구성·risk 후 점수와 helper 확인 |
| R-08 | C-09 | 변환 기본값·약한 integrity 경계 확인 |
| R-10, R-11 | C-10, C-11, C-17 | router 및 aggregation 구현 직접 확인 |
| R-12 | C-05, C-12 | fallback·timeout·재사용 경계 확인 |
| R-13 | C-14 | 실제 기본 mediator 경로 확인 |
| R-14 | C-13, C-16, C-17 | 단계·memory 확인 |
| R-15 | C-15, C-18~C-22 | 로더와 전략 파일 확인 |
| R-16 | C-09, C-26 | 공통 보정 호출 순서 및 실제 변경 기록 조건 확인 |
| T-01~T-09 | T별 R-ID의 위 근거 | 모두 구현에서 도출. 외부 의존은 대체물 |
