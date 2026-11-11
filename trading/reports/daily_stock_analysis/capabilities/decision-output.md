---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/core/pipeline.py
  - src/analyzer.py
  - src/phase_decision_guardrail.py
  - src/daily_market_context_guardrail.py
  - src/analysis_context_pack_prompt.py
  - src/market_phase_summary.py
  - src/report_language.py
  - src/schemas/decision_action.py
  - src/schemas/decision_scale.py
  - src/schemas/decision_profile.py
  - src/services/decision_signal_extractor.py
  - src/services/decision_signal_service.py
  - src/services/decision_signal_summary.py
  - src/repositories/decision_signal_repo.py
  - src/storage.py
  - src/utils/sniper_points.py
  - src/utils/sanitize.py
  - src/config.py
status: ready
depends:
  - llm-decision.md
  - agent-decision.md
---

# 결과 보정·저장·신호 경계

> 판단기가 만든 AnalysisResult를 코드 규칙으로 보정하고, 성공 보고서 이력을 저장한 뒤 별도 DecisionSignal을 추출·저장한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. [기본 LLM 판단](llm-decision.md) 또는 [Agent 판단](agent-decision.md)에서 생성한 AnalysisResult와 시세·추세·펀더멘털·시장 단계·품질 overview를 받는다.
2. 누락된 chip/price_position 표시 필드를 실제 데이터로 채우고 구조·수급에 맞춰 매수·매도 판단을 보정한다.
3. 시장 단계 가드레일 → 일일 시장 환경 가드레일을 적용한다. 일부는 신뢰도·문구만 바꾸고 일부는 decision_type·점수도 바꾼다.
4. 이전 advice와 달라졌으면 낡은 action/action_label을 버리고, 보고서와 신호가 공통으로 쓰는 resolver로 최종 action을 계산한다.
5. result.success가 참일 때 context snapshot과 원본 응답을 보고서 이력에 저장한다. 저장 실패가 판단 결과를 제거하지 않는다.
6. 저장 ID가 bool 아닌 양의 int일 때만 DecisionSignal payload를 만들고 별도 transaction으로 저장한다. 신호 실패는 이미 저장한 이력을 rollback하지 않는다.
7. 저장 신호의 제한된 요약만 result에 붙여 호출자에게 반환한다. 이 경계 안에서는 주문 제출이나 사람 승인 대기가 없다(R-15).

### 1.2 범위·통합 지점

- 제공: 공통 후처리 함수의 원본 규칙, 두 판단 경로의 적용 순서 차이, 이력·snapshot·신호 추출 및 생성 시 필요한 정규화·중복·만료·반대 신호 무효화.
- 제외: 판단기 입력·LLM/Agent 루프는 선행 spec. 신호 조회 API·수동 수정·과거 보고서 backfill·사후 수익률 평가는 행 9/10 영역이다. 알림 전달은 행11로 제외한다.
- 소유 상태: AnalysisResult와 그 dashboard를 제자리 변경한다. report history와 decision signal은 별도 영속 레코드다. 이력 ID로 신호를 연결하며 하나의 원자적 transaction으로 묶지 않는다.
- 통합 입력: result는 기본 타입 계약을 따른다. `trend_result`는 dict·to_dict 지원 객체·일반 속성 객체, quote는 객체 또는 dict가 일부 helper에 허용된다. `fundamental_context`는 수급 블록을 가진 map 또는 None. 날짜·시간은 저장소 로컬 created_at과 신호 UTC naive 시계를 구별한다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 공유 AnalysisResult | 선행 spec의 객체 → 같은 객체 | 생성 필드 원본은 행4. 이 spec은 보정한 score/advice/decision_type/action, dashboard·snapshot·signal summary의 의미를 소유한다. 성공/실패를 모든 helper가 새로 판정하지 않는다. |
| 3상태와 8상태 | decision_type=`buy/hold/sell`, action=`buy/add/hold/reduce/sell/watch/avoid/alert` 또는 None | 서로 다른 계약. score만으로 모든 action을 강제 일치시키는 로직이 아니다(R-07). action_label은 report language에 따른 표시 문자열. |
| decision_stability | dashboard map | applied,reason,current_price,support,resistance,capital_flow_bias 및 선택적 capital_flow_status/raw_score/adjusted_score/final_action. ‘수급 없어 미적용’도 이유를 남긴다. |
| decision_score_calibration | dashboard map | raw/adjusted score,final_action,guardrail_reason와 점수 band metadata. 후속 추출은 유효한 adjusted_score를 현재 result.score보다 우선한다. |
| phase_decision | dashboard map | phase_context,action_window,immediate_action,watch_conditions,next_check_time,confidence_reason,data_limitations. 초기 누락값은 None/빈 list로 보강한다. |
| context snapshot | map | enhanced_context,news_content,quote/chip raw 및 선택적 retrieval count/pack overview/시장 summary/diagnostics/skills. runtime prompt 자료 일부를 제거한 shallow copy. save_context_snapshot=false도 런타임 snapshot 생성·신호 추출은 한다. |
| save_analysis_history | result,query_id,report_type,news_content,snapshot,save_snapshot → int | 성공 새 history ID 또는0. raw_result는 result.to_dict에 data_sources/raw_response를 추가한 JSON. sniper_points 4개는 숫자 컬럼에도 저장한다. |
| 신호 payload | map | stock_code/name/market/source_type/source_report_id/trace_id/decision_profile/market_phase/trigger_source/action/action_label/confidence/score/entry_low/high/stop_loss/target_price/reason/risk_summary/catalyst_summary/watch_conditions/evidence/data_quality_summary/metadata/report_language. None·빈 문자열·빈 list/map은 builder가 제거한다. |
| 신호 생성 반환 | `{item,created}` 또는 None | created=false도 기존/refresh 신호 item 반환 가능. DB 정규화 후 evidence/metadata는 JSON이었다가 직렬화 시 구조로 복구한다. |
| 보유 상태 | metadata.holding_state | quantity가 유한 숫자이면 abs>0 holding,0 empty,없음·비숫자·비유한 unknown. 포트폴리오의 전체 보유 자산을 조회해 이 값을 추정하지 않는다. |

신호 기본값은 source_type=`analysis`(Agent 경로도 동일), profile=`balanced`, profile_source=`auto_default`다. 기본 horizon은 alert 또는 premarket/intraday/lunch_break/closing_auction이면 intraday, 아니면3d. intraday 만료는 close까지 분, 없으면 open까지 분+시장 세션 대체 시간, 그것도 없으면 CN4h/HK5.5h/US6.5h/기타4h다. 3d는 거래일이 아닌72시간이다. 저장시 이미 만료면 status=expired다(R-12).

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | chip 데이터 | usable 데이터가 있으면 placeholder인 네 chip 필드만 채우고 모델의 의미 있는 필드는 보존한다. 없으면 기존 data_perspective의 chip_structure를 빈 map으로 접고 unavailable 사유를 붙인다. 기본 pipeline은 항상 호출하지만 Agent pipeline은 chip_data가 None 아닐 때만 호출한다. | 코드 확인 |
| R-02 | price_position 누락 | MA/bias/current_price·첫 support/resistance를 trend에서 채우고 trend 가격이 placeholder면 quote.price 사용. LLM의 의미 있는 필드는 덮지 않는다. bias_status는 채울 computed 값이 없어 자동 계산되지 않는다. helper 오류는 경고 후 통과한다. | 코드 확인 |
| R-03 | 수급 블록이 존재하지만 usable 수급 없음 | buy 또는 advice가 buy이면 hold로 낮추고 confidence Low,score45~59로 제한·calibration/사유/대응 문구를 기록한다. 비buy는 calibration 미적용 사유만 남긴다. fundamental 자체가 없거나 capital_flow 키가 없으면 해당 강등 없이 반환한다. | 코드 확인 |
| R-04 | usable 수급과 현재가 존재 | 수급 방향은 main/5d/10d의 nonzero 부호가 모두 같으면 inflow/outflow,0만 있거나 충돌이면 neutral. support×0.985 미만은 이탈, support×1.03 이하(이탈 제외)는 지지 근처, resistance×1.01 초과는 돌파, resistance×0.97 이상(돌파 제외)은 저항 근처. buy는 저항 근처+유입 미확인 / 유출+미돌파 / 중간구간+neutral 순으로 hold 강등. sell은 지지 근처+유출 아님 또는 유입+미이탈에서 중대위험 없으면 hold 강등. 원래 hold는 상황 문구만 바꾸고 점수를 강제 보정하지 않는다. | 코드 확인 |
| R-05 | 시장 단계·품질 | quote/daily_bars/technical 중 degraded block이 있고 최초 confidence high이면 medium으로 제한. premarket/non_trading/unknown의 buy/sell 또는 즉시 매매 문구는 immediate_action을 대기로 바꾸며 최초 high였다면 low. 이 분기는 decision_type·score 자체를 바꾸지 않는다. 장중 recap 문구는 해당 필드만 단계에 맞게 대체한다. phase 단계의 limitation은 중복 제거해 앞의 최대 5개만 유지하며 이후 daily 단계는 제한을 재적용하지 않아 여섯 번째 항목을 추가할 수 있다. | 코드 확인 |
| R-06 | 일일 시장 환경이 보수적이고 aggressive buy | risk tag·비어 있지 않은 position_cap·보수적 summary 패턴 중 하나면 보수적. buy decision_type은 hold,advice는 관망,high confidence는 medium,score는0~52로 제한. dashboard·position advice/strategy·phase 제한도 갱신한다. 기존 `decision_score_calibration.adjusted_score`는 고치지 않아 추후 action·신호 score가 52가 아닌 기존 유효 adjusted_score를 우선할 수 있다. 부정된 buy 문구는 단순 substring과 구별한다. | 코드 확인 |
| R-07 | 최종 advice/action 계산 | advice 문자열이 바뀌면 기존 action/label clear. 유효 adjusted score 우선, 명시 action→advice 해석 순으로 public action 선택. action이 hold/watch인데 점수 band가 buy/reduce/sell이고 guardrail reason이 없을 때만 score action으로 바꾼다. reason은 calibration·stability·result 필드뿐 아니라 충돌 시 advice 및 buy band면 summary·buy_reason·watch 조건의 지정된 단어에서도 유추한다. 다른 action 충돌·None을 전부 score로 채우지는 않는다. 비종목 report type은 action None. | 코드 확인 |
| R-08 | 경로별 순서 | 기본은 가격→chip→price position→structure→phase→daily context→필드 부착→action refresh. Agent는 weak 무결성/자체 dashboard 보정 후 chip(조건부)→초기 action refresh→price position→가격→structure/refresh→phase/refresh→daily/refresh→최종 설명. Agent의 보정 이력·설명 생성 계약은 행5가 소유한다. | 코드 확인 |
| R-09 | 성공 보고서 저장 | result.success 참일 때만 history 쓰기. snapshot에서 runtime phase/portfolio/pack/prompt summary를 제외하고 별도 public overview/phase summary는 보존. save_snapshot false면 DB snapshot은 NULL, raw_result와 뉴스는 계속 저장한다. 기본은 news_content를 history에 전달, Agent는 history.news_content=None이며 런타임 context의 뉴스는 snapshot에 남을 수 있다. | 코드 확인 |
| R-10 | history 저장 결과 | 양의 int이고 bool이 아닌 ID일 때만 신호 추출. 0/None/True이면 추출 안 함. 쓰기 실패는 로그 후 결과 반환, 기존 history를 신호 실패로 rollback하지 않는다. snapshot 직렬화 전 helper 오류와 DB 오류가 잡히는 위치는 C-07/08의 경계대로다. | 코드 확인 |
| R-11 | 신호 추출 | 실패 result·액션 미해석·시장 미인식/미지원이면 None. confidence map은 高/high=.8,中/medium/mid=.6,低/low=.4이고 한국어 수준 문자열은 map에 없어 누락된다. entry 두 가격이 있으면 정렬하되 하나뿐이면 그 슬롯만 유지. reason은 summary→buy_reason→key_points. risk/catalyst 최대5개, watch는 phase list 우선 뒤 checklist. | 코드 확인 |
| R-12 | 신호 정규화·저장 | 6시장·8action enum 검사, confidence0~1/score0~100 검사, 가격은 유한 양수. 입력 범위 뒤집힘은 ValueError. list/map 설명은 sanitized JSON 문자열 저장. horizon·만료·plan_quality 기본 산출은 C-10. plan 슬롯(entry1개,stop,target,invalidation,watch)4개 이상 complete,2개 이상 partial,그 외 minimal. | 코드 확인 |
| R-13 | 신호 중복·반대 액션 | report ID 우선(없으면 trace)·source·시장·종목·profile·action·horizon·phase가 같으면 기존 신호. 만료→미래 active 재생성은 동일 ID의 가변 필드 refresh. null horizon/phase만 채우는 relaxed merge도 있다. 새 active bullish(buy/add)는 이전 defensive(reduce/sell/avoid)를, 반대도 동일하게 invalidated. hold/watch/alert는 반대 무효화 없음. 각 write가 별 transaction이므로 동시 생성 exactly-once 보장은 하지 않는다. | 코드 확인 |
| R-14 | 신호 실패·요약 | builder/서비스/저장/직렬화 예외는 추출 함수가 잡아 None. 신호가 저장된 뒤 반대 무효화나 직렬화 실패가 나면 일부 상태가 이미 영속화될 수 있다. 성공 item에서 허용 필드만 sanitize해 result.decision_signal_summary에 부착. | 코드 확인 |
| R-15 | 판단→주문 경계 | 이 분석 경로는 보고서·신호를 저장하며 주문 제출·사람 승인 호출이 없다. position_cap과 추천 비중 문자열은 이 경계에서 주문 수량의 hard limit으로 집행되지 않는다. 다른 브로커 기능 전체의 존재 여부에 관한 주장은 아니다. | 코드 확인 |

- 미결정: 없음. 두 선행 판단 spec이 ready이며 결과 계약·보정 순서를 대조했다.
- 확인 한계: 정적 코드 분석. 외부 SDK·LLM·DB 동시성 및 실제 매매 결과를 실행 확인하지 않았다. R-13 중복 조회를 DB unique constraint 기반 exactly-once로 과장하지 않는다.

### 1.5 필수 코드 참조

작은 변환·문구·패턴 목록은 아래 코드가 원본 계약이다. 1.4는 적용 조건·소유권·실패 전달을 정의한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/analyzer.py:883-1040` chip/price fill, `src/analyzer.py:525-530` chip key/placeholder, `src/analyzer.py:609-635` float/chip 변환 | chip 백분율·가격 누락 채우기 | R-01,02 |
| C-02 | `src/analyzer.py:1043-1654` stabilize와 내부 helper, `src/analyzer.py:533-606` risk/status 상수·text 판정 | 수급 부호·가격 임계값·점수 제한·기록·상황 문구 | R-03,04 |
| C-03 | `src/phase_decision_guardrail.py:17-450` 상수·apply 및 내부 helper, `src/analysis_context_pack_prompt.py:64-72` CORE_DEGRADED_STATUSES | 단계별 조정·최대5개 제한·부정문 패턴 | R-05 |
| C-04 | `src/daily_market_context_guardrail.py:16-288` 전체 guardrail 계약 | 보수적 환경·매수 부정 인식·52점 cap·대응 문구 | R-06 |
| C-05 | `src/core/pipeline.py:2320-2340` refresh, `src/services/decision_signal_extractor.py:177-204` resolver, `src/services/decision_signal_extractor.py:249-365` 점수/action/reason helper, `src/schemas/decision_action.py:13-401` action enum/패턴/해석/label, `src/schemas/decision_scale.py:11-29` band·`src/schemas/decision_scale.py:58-172` 숫자와 충돌 판정 | public action과 점수 보정 범위 | R-07,11 |
| C-06 | `src/core/pipeline.py:890-1000` 기본 후처리·저장, `src/core/pipeline.py:1685-1832` Agent 공통 보정·설명 연결, `src/core/pipeline.py:1863-1940` Agent 저장 | 순서·최상위 실패 전파 | R-08~10 |
| C-07 | `src/core/pipeline.py:2813-2848` snapshot, `src/core/pipeline.py:2886-2941` 신호 연결, `src/core/pipeline.py:3189-3207` runtime 제외, `src/core/pipeline.py:3230-3246` safe_to_dict, `src/core/pipeline.py:2474-2513` 지수 일봉 출처 | snapshot·valid ID·요약 부착 | R-09,10,14 |
| C-08 | `src/storage.py:2794-2847` save history, `src/storage.py:3607-3635` raw/json/sniper wrapper, `src/storage.py:2202-2255` write transaction/lock 판정, `src/storage.py:338-441` history model | 저장 열·직렬화·transaction 경계 | R-09,10 |
| C-09 | `src/services/decision_signal_extractor.py:28-174` payload/상수, `src/services/decision_signal_extractor.py:207-246` best-effort 추출, `src/services/decision_signal_extractor.py:368-506` entry/quality/market/holding/evidence, `src/utils/sniper_points.py:11-123` 가격 파싱/중첩 탐색 | 보고서→신호 정확한 매핑 | R-11,14 |
| C-10 | `src/services/decision_signal_service.py:48-68` enum/TTL, `src/services/decision_signal_service.py:121-135` 생성, `src/services/decision_signal_service.py:171-189` store/write, `src/services/decision_signal_service.py:786-1075` 정규화·수명·반대 무효화·plan, `src/services/decision_signal_service.py:1104-1363` scalar/JSON/직렬화 | 신호 생성 경계와 검증·기본값 | R-12~14 |
| C-11 | `src/repositories/decision_signal_repo.py:42-150` create, `src/repositories/decision_signal_repo.py:246-471` 반대 active 조회·expire·중복 helper, `src/repositories/decision_signal_repo.py:533-536` profile 조건, `src/storage.py:1031-1122` 신호 model | key·refresh·부분 transaction | R-13,14 |
| C-12 | `src/services/decision_signal_summary.py:11-41` public summary, `src/utils/sanitize.py:11-232` key/text/URL sanitize | 요약 allowlist·비밀 패턴·JSON 정제 | R-12,14 |
| C-13 | `src/report_language.py:815-821` normalize, `src/report_language.py:853-903` chip unavailable·lookup 공통, `src/report_language.py:992-999` confidence, `src/report_language.py:1042-1067` chip health/placeholder, `src/report_language.py:1234-1263` advice 추론 | 표시 변환; 같은 파일의 상수·helper closure는 행4 C-ID 참조 | R-01~07 |
| C-14 | `src/market_phase_summary.py:14-38` summary 키, `src/market_phase_summary.py:87-105` render, `src/market_phase_summary.py:266-321` scalar/list helper | phase public projection; 시장 단계 enum은 행2 선행 계약 | R-05,09 |

| C-15 | `src/storage.py:76-85` UTC 시각, `src/config.py:2204-2216` SQLite retry·snapshot 기본값, `src/schemas/decision_profile.py:20-65` profile 정규화 | naive UTC·retry 3회/0.1초 exponential·snapshot true·profile enum | R-09,10,12,13 |

`DecisionSignalService`의 code parser/시장 코드 계약은 수집과 컨텍스트 선행 계약을 그대로 쓴다. `VALID_MARKETS={cn,hk,us,jp,kr,tw}`다. 신호 profile은 이 자동 추출 경로에서 balanced로 고정되며 legacy profile 역산 분기는 호출되지 않는다. DB Session은 commit/rollback/close 가능한 SQLAlchemy 경계이고 timestamp model default·UTC 변환은 C-15를 따른다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. 실제 LLM·provider·DB를 실행한 결과가 아니다. 객체와 저장소 대체물로 단계별 계약을 확인하는 사례다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | usable chip가 있고 모델 profit_ratio='N/A', avg_cost 의미 있음 | profit ratio만 데이터에서 보충, 모델 avg_cost 보존 |
| T-02 | R-01,08 | chip=None, 기존 chip 표시 존재 | 기본 경로는 빈 chip map+사유, Agent 조건부 호출은 이 단계 자체를 건너뜀 |
| T-03 | R-03 | buy,score90, capital_flow.status=not_supported | hold,Low,score59; 원점수90과 강등 사유 기록 |
| T-04 | R-03 | buy지만 fundamental_context=None | 수급 결측 강등은 실행하지 않음 |
| T-05 | R-04 | buy,저항100,현재가100,수급neutral | 저항 근처→hold,score45~59로 제한 |
| T-06 | R-04 | sell,지지100,현재가100,수급inflow,중대위험 없음 | hold 강등; 동일 조건에 중대위험 있으면 해당 sell 강등 미실행 |
| T-07 | R-05 | premarket,decision_type=buy,high confidence | immediate_action=대기,confidence low; 이 함수만으로 decision_type/score는 안 바뀜 |
| T-08 | R-06 | high_risk 시장 context, buy score90 high | hold·관망·score52·medium,시장 제한 사유 기록 |
| T-08a | R-06,07 | 기존 adjusted_score=59와 guardrail reason이 있고 daily guardrail이 현재 score를 52로 제한 | report score 52, 후속 action resolver·신호 score는 기존 adjusted_score 59를 사용한다 |
| T-08b | R-05,06 | phase limitation 다섯 개가 이미 있고 daily guardrail이 새 문구 추가 | daily 적용 후 여섯 개가 될 수 있다 |
| T-09 | R-07 | advice 변경으로 stale action clear,score75,advice watch,guardrail 사유 없음 | public action buy; 사유 있으면 watch 유지 |
| T-10 | R-10 | history writer가0 또는True 반환 | 신호 writer 미호출; result는 그대로 반환 |
| T-11 | R-09 | success=true,save_snapshot=false | history snapshot NULL,raw_result 보존,런타임 snapshot으로 신호 추출 가능 |
| T-12 | R-11 | confidence='높음',entry ideal110/secondary100 | confidence payload 누락,entry_low100/high110 |
| T-13 | R-12 | 한국 intraday,분 정보 없음 | 기본 TTL4h; report 저장 성공 여부와 별도 신호 상태 |
| T-14 | R-13 | 동일 report·action·phase·horizon으로 재추출 | active 기존이면 created=false; 만료 신호+미래 active 입력이면 refresh 가능 |
| T-15 | R-13 | 같은 종목/profile의 오래된 buy active,새 sell active | 오래된 buy invalidated,새 sell active |
| T-16 | R-14 | history 저장 후 signal writer 예외 | history 유지,result 반환,signal summary 없음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01,02/T-01,02 | C-01,06,13 | pipeline 조건 차이 및 helper 내부 예외 처리를 확인 |
| R-03,04/T-03~06 | C-02 | flow key 부재와 ‘존재하지만 unusable’의 분기가 다름. 한국 수급 미지원은 이 코드에서 buy 강등으로 연결될 수 있음 |
| R-05/T-07,T-08b | C-03,14 | confidence 초기값을 먼저 잡아 두므로 core cap 후에도 non-intraday cap 가능 |
| R-06/T-08,T-08a,T-08b | C-04 | 시장 가드레일은 score52 상한과 dashboard를 바꾸지만 기존 calibration을 지우지는 않음 |
| R-07/T-08a,T-09 | C-05 | ‘score와 action의 모든 충돌 해소’가 아니라 neutral 충돌만 처리 |
| R-08/T-02 | C-06 | Agent 자체 판단/최종 설명 helper는 행5 참조. pipeline 공통 함수의 내용은 이 문서 소유 |
| R-09,10/T-10,11 | C-06~08 | snapshot flag와 신호 추출 여부는 별개. DB 실패 후 result 반환 |
| R-11/T-12 | C-09 | confidence 원본 map에 한국어 키가 없어 자동 누락. entry 숫자 파서의 ‘마지막 숫자’ 방식은 C-ID 그대로 |
| R-12/T-13 | C-10,12 | TTL은 시장 달력 경과가 아닌 시간 덧셈; 사용자 가격 검증과 추출 가격 정렬 구별 |
| R-13/T-14,15 | C-10,11 | 중복 조회 후 commit이며 transaction 간 race 보장 없음 |
| R-14/T-16 | C-07,09,12 | 신호 일부 영속화 이후 예외도 None이 될 수 있음 |
| R-15 | C-06~11 | 분석→보정→이력→신호 생성 호출 경로를 끝까지 읽음. 주문 계층 전체 부재 주장이 아님 |

핵심 근거: [기본 후처리와 이력 연결](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/core/pipeline.py#L890-L1000), [신호 payload 및 best-effort 추출](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/services/decision_signal_extractor.py#L43-L246).

### 2.2 코드 읽는 순서

각 판단기에서 나온 객체 → pipeline의 경로별 후처리 순서 → analyzer 공통 structure helper → phase/daily guardrail → public action resolver → history → extractor → signal service/repository 순으로 읽는다. `AnalysisResult.raw_response`는 모델 응답이고 최종 보정값을 보장하지 않으므로 저장된 raw_result의 최종 필드와 구분한다.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-03,15 | 의견: 키움 수급 부재·휴장·권한 오류를 구분하고 주문 계층에서 별도 승인/위험 한도를 정한다 | 원본 수급 부재 강등 및 비중 문구만으로 우리 주문 정책을 정할 수 없음 | 원본 spec은 그대로이며 별도 설계 결정 필요 |
