# daily_stock_analysis — 질문·답변 검증 기록

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 2
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | 한국 종목 `fundamental_context`에 `capital_flow` 키가 실제로 들어가 buy 강등 조건이 성립하는가 | Q1 / Q4-5 | 해소 | R1 |
| R1-Q2 | 백테스트 요약 도구가 단일 에이전트에 실제로 바인딩되는가 | Q1 | 해소 | R1 |
| R1-Q3 | Agent 경로 자동 활성 조건(`AGENT_SKILLS` 기본값, `analysis_skills` 출처) | Q2 / Q4-2 | 해소 | R1 |
| R1-Q4 | `_augment_historical_with_realtime`가 실시간 시세를 일봉에 붙이는 조건 | Q2 | 해소 | R1 |
| R1-Q5 | GitHub Actions에서 DB 영속화 수단이 정말 없는가(전체 워크플로) | Q3 | 없음 확정 | R1 |
| R1-Q6 | Web/API 수동 분석이 같은 파이프라인·가드레일을 거치는가 | Q3 | 해소 | R1 |
| R1-Q7 | Actions cron(UTC 10:00) 시점에 미국 종목의 시장 단계 판정값 | Q3 / Q4-5 | 해소 | R1 |
| R1-Q8 | 점수↔액션 정렬 단계가 가드레일의 buy 강등을 되돌릴 수 있는가 | Q4-5 | 재질문 → R2-Q1 → 정적 확인 불가 | R2 |
| R1-Q9 | `_finalize_dashboard_payload`가 점수·액션을 추가로 바꾸는 규칙 | Q4-5 | 해소 | R1 |
| R1-Q10 | LLM/멀티라운드 중재자를 켜는 설정이 존재하는가 | Q4-2 | 없음 확정 | R1 |
| R1-Q11 | 코드 점수(`系统评分`)와 LLM 점수의 관계를 정하는 프롬프트 지시·코드 | Q4-3 / Q4-5 | 없음 확정 | R1 |
| R1-Q12 | 뉴스 검색 결과의 중복 제거 장치 유무 | Q5 | 없음 확정 | R1 |
| R2-Q1 | (8) 대시장 가드레일 뒤 (9) 되돌림 성립 조건(LLM `guardrail_reason` 경로 포함) | Q4-5 | 정적 확인 불가 | R2 |
| R2-Q2 | LLM 대시보드 `action`이 리스크 오버라이드 후에도 최종 `result.action`으로 남는가 | Q4-5 | 해소 | R2 |
| R2-Q3 | API 응답·리포트 `action`이 파이프라인 `result.action`과 달라지는 조건 | Q4-5 | 해소 | R2 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. 한국 종목에서 `capital_flow` 키가 `fundamental_context`에 실제로 들어가는가
- GUIDE 항목: Q1 / Q4-5
- 왜 묻는가: `00-overview.md` 핵심 발견 4, `03-decision.md` 4-5 덮어쓰기 장치 (1), `05-boundary-and-fit.md` 7-1 "주의"는 "한국 `.KS`는 자금흐름이 항상 `not_supported`라 매수가 항상 hold로 강등된다"고 쓴다. 그런데 `src/analyzer.py:1094-1095`의 강등 분기는 `flow_bias == "unavailable"`에 더해 `isinstance(fundamental_context, dict) and "capital_flow" in fundamental_context`가 참이어야 실행된다. 보고서는 `base.py:4057-4075`에서 `not_supported` 블록이 만들어진다는 것만 보였고, 그 블록이 한국 종목 경로에서 `stabilize_decision_with_structure`에 넘어가는 `fundamental_context`의 `capital_flow` 키로 실제 들어가는지는 추적하지 않았다. `next.md` 2절도 이 결론을 "정적 추적만"이라고 적었다.
- 질문: `005930.KS` 같은 한국 종목이 레거시 경로를 탈 때, `stabilize_decision_with_structure`에 전달되는 `fundamental_context`는 어디서 만들어지며, 그 dict에 `capital_flow` 키가 (값이 `not_supported` 상태로라도) 반드시 존재하는가?
- 답변 완료 조건: `fundamental_context`가 생성되는 함수(`get_fundamental_bundle` 등)에서 한국 종목일 때 `capital_flow` 키를 넣는 코드의 `파일:라인`과 원문, 그 dict가 `stabilize_decision_with_structure` 호출 인자로 넘어가는 호출처 `파일:라인`. 한국 분기(`base.py:4281-4286` 해외 분기 포함)에서 키가 빠지는 경로가 있다면 그 조건 원문.

#### R1-Q2. 백테스트 요약 도구가 단일 에이전트(`AgentExecutor`)에 실제로 바인딩되는가
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` 1-2 표의 `get_skill_backtest_summary` 행은 "도구 레지스트리에는 등록되어 단일 에이전트가 볼 수 있으나 … 지시는 없음"이라고 쓰고 검증 수준을 `추론`으로 남겼다. 레지스트리 등록과 실제로 LLM에 노출되는 도구 목록은 다를 수 있다.
- 질문: `AGENT_ARCH=single`일 때 `AgentExecutor`가 LLM에 넘기는 도구 목록에 `backtest_tools.py`의 도구(`get_skill_backtest_summary` 등)가 포함되는가?
- 답변 완료 조건: 단일 에이전트의 도구 목록을 구성하는 코드(`factory.py` 등)의 `파일:라인`과 필터 조건 원문, 백테스트 도구가 포함/제외되는 근거. 프롬프트(`executor.py`의 `AGENT_SYSTEM_PROMPT`)에 해당 도구 이름이나 백테스트 사용 지시가 있는지 grep 결과.

#### R1-Q3. Agent 경로가 자동으로 켜지는 조건과 기본값
- GUIDE 항목: Q2 / Q4-2
- 왜 묻는가: `00-overview.md` 핵심 발견 1은 "기본 경로는 단일 LLM 호출"이라 하고, `01-data.md` 범례는 "`AGENT_SKILLS`가 `all`이 아닌 값이면 Agent 경로"라고 쓴다. `src/core/pipeline.py:561-571`을 보면 `self.analysis_skills`가 비어 있지 않을 때도 Agent가 자동 활성화된다. `AGENT_SKILLS`의 기본값과 `analysis_skills`가 어디서 채워지는지가 보고서에 없어서, 기본 실행(Actions cron, 로컬 스케줄러)이 정말 레거시 경로를 타는지 확정되지 않았다.
- 질문: `config.agent_skills`의 기본값은 무엇이며(환경변수 미설정 시), `StockAnalysisPipeline.analysis_skills`는 어떤 입력(CLI 인자, API 요청, 스케줄 설정)에서 채워지는가? 기본 Actions 실행과 `--schedule` 실행에서 두 값은 각각 무엇이 되는가?
- 답변 완료 조건: `agent_skills` 기본값을 정하는 `config.py` `파일:라인`과 원문, `analysis_skills`를 설정하는 생성자·호출처 `파일:라인`, `.github/workflows/00-daily-analysis.yml`에서 `AGENT_SKILLS` 관련 키 grep 결과.

#### R1-Q4. `_augment_historical_with_realtime`가 실시간 시세를 일봉에 붙이는 조건
- GUIDE 항목: Q2
- 왜 묻는가: `01-data.md` 2-3 마지막 행은 "시세에 장중 반영 후 MA 재계산"이라고 하면서 검증을 "함수 호출 확인, 내부는 미열람"으로 남겼다. 장후(18:00) 실행에서 실시간 시세가 이미 저장된 당일 일봉과 중복되거나, 장전 실행에서 전일 종가가 '오늘 봉'으로 붙으면 MA·乖离 계산이 달라지므로 판단 입력의 정확성에 직결된다.
- 질문: `_augment_historical_with_realtime`(`pipeline.py:2733-2811`)는 어떤 조건(시장 단계, 날짜 비교, 마지막 일봉 날짜와 시세 시각의 관계)에서 실시간 시세를 새 행으로 추가하거나 마지막 행을 덮어쓰거나 아무것도 하지 않는가?
- 답변 완료 조건: 함수 내부의 분기 조건 원문과 `파일:라인`, 각 분기의 동작(추가/덮어쓰기/생략). 그 결과 DataFrame이 `StockTrendAnalyzer`에 들어가는 호출처 `파일:라인`.

#### R1-Q5. GitHub Actions에서 SQLite DB를 보존하는 단계가 정말 없는가
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3-3은 "워크플로에 DB 캐시/복원 단계가 없다 → 매 실행이 빈 DB"라고 하고, `next.md` 4절 질문 2는 이 때문에 자동 백테스트가 무의미하다고 추정한다. 근거는 `00-daily-analysis.yml` 한 파일뿐이고, 다른 워크플로나 저장소 커밋 방식(DB를 브랜치에 커밋 등)으로 보존할 가능성은 조사 범위에 없다.
- 질문: `.github/workflows/` 아래 모든 워크플로와 `00-daily-analysis.yml`이 호출하는 스크립트에 `data/stock_analysis.db`(또는 `DATABASE_PATH`)를 캐시·복원·커밋·아티팩트 다운로드하는 단계가 있는가?
- 답변 완료 조건: `.github/workflows/*` 파일 목록, `actions/cache|download-artifact|upload-artifact|git commit|git push|stock_analysis.db|DATABASE_PATH` grep 결과와 조사 범위. 있으면 해당 `파일:라인` 원문.

#### R1-Q6. Web/API 수동 분석 요청이 같은 파이프라인과 가드레일을 거치는가
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3-1 "Web/API 수동" 행이 `미확인`이다. 웹 UI에서 분석을 돌리는 경로가 `StockAnalysisPipeline.analyze_stock`→가드레일 3종을 그대로 거치는지, 별도 경로인지가 보고서 전체 결론("두 경로 모두 같은 가드레일 통과")의 적용 범위를 정한다.
- 질문: `api/v1/endpoints/analysis.py`의 분석 요청 엔드포인트는 어떤 함수 체인을 거쳐 분석을 실행하며, 그 체인에 `stabilize_decision_with_structure`, `apply_phase_decision_guardrails`, `apply_daily_market_context_guardrail`이 모두 포함되는가?
- 답변 완료 조건: 엔드포인트 함수에서 파이프라인 진입까지의 호출 순서(`파일:라인` 연쇄)와, 가드레일 호출이 포함된 지점의 `파일:라인`. 빠지는 가드레일이 있으면 그 이유가 되는 분기 원문.

#### R1-Q7. Actions cron(UTC 10:00) 시점에 미국 종목의 시장 단계 판정값
- GUIDE 항목: Q3 / Q4-5
- 왜 묻는가: `02-schedule.md` 3-6 마지막 문단은 "미국 장은 그 시각 아직 열려 있지 않으므로 별도 cron이 필요하다"를 `추론`(시간대 계산 기반)으로 남겼다. 시장 단계 값에 따라 `phase_decision_guardrail`이 `immediate_action`과 신뢰도를 바꾸므로(`03-decision.md` 4-5 (7)), 미국 종목이 어떤 단계로 판정되는지는 정적으로 계산 가능한 사실이다.
- 질문: 평일 UTC 10:00(미국 동부 06:00 전후)에 미국 종목을 분석하면 `trading_calendar.py`의 단계 판정 함수는 `premarket`/`non_trading`/`postmarket` 중 무엇을 반환하며, "마지막 완전 일봉 날짜"는 어느 날짜가 되는가?
- 답변 완료 조건: 미국 시장의 세션 시각·시간대 정의(`trading_calendar.py` `파일:라인` 원문)와 단계 판정 분기 원문, 그 단계가 `phase_decision_guardrail.py`에서 걸리는 분기 `파일:라인`.

#### R1-Q8. 점수↔액션 정렬 단계가 가드레일 강등을 되돌릴 수 있는가
- GUIDE 항목: Q4-5
- 왜 묻는가: `03-decision.md` 4-5 (9)는 "`action`이 hold/watch인데 점수가 buy 구간이고 `guardrail_reason`이 없으면 점수 구간의 액션으로 되돌린다"고 하고, 같은 표의 "방향성" 행은 "상향 규칙은 없음, (9)만 예외"라고 한다. 가드레일 (1)~(4)·(8)이 강등할 때 점수를 45~59 또는 ≤52로 클램프하는지, `guardrail_reason`을 설정하는지에 따라 (9)가 강등을 무효화할 수 있다. `analyzer.py:1414-1436`에서 `guardrail_reason`이 calibration에 들어가는 흔적은 보이나, 결과 객체의 `guardrail_reason` 필드에 쓰이는지와 (9)가 그 값을 읽는지는 보고서에 없다.
- 질문: `_refresh_decision_action_for_final_result`(`pipeline.py:2320`)가 `build_action_fields`를 호출할 때 넘기는 `sentiment_score`와 `guardrail_reason`은 각각 어느 필드에서 오며, 가드레일 (1)~(4), (7), (8)이 강등한 결과에 대해 (9)의 `score_action_conflicts_without_guardrail`이 참이 되는 경우가 존재하는가?
- 답변 완료 조건: `_refresh_decision_action_for_final_result` 본문의 인자 출처 원문(`파일:라인`), 각 가드레일이 `result.guardrail_reason` 또는 점수를 바꾸는 코드 `파일:라인`, `score_action_conflicts_without_guardrail` 조건 원문(`decision_scale.py:158-171`). 되돌림이 가능한 경우가 있으면 그 조건을, 없으면 왜 없는지 코드로 보인다.

#### R1-Q9. Agent multi 경로의 `_finalize_dashboard_payload`가 점수·액션을 추가로 바꾸는가
- GUIDE 항목: Q4-5
- 왜 묻는가: `next.md` 2절·3절 2번은 `orchestrator.py:1370-1660` `_finalize_dashboard_payload` 전체 규칙을 미확인으로 남겼다. `03-decision.md` 4-5 (10b)는 이 범위 일부(`:1385-1412`, `:1442`, `:1466-1480`)만 인용했다. 코드가 최종 결정을 바꾸는 장치 목록이 완전한지 확정해야 한다.
- 질문: `_finalize_dashboard_payload`(와 그 안에서 호출하는 보조 함수)가 `sentiment_score`, `decision_type`, `action`, `operation_advice`, `confidence_level`을 변경하는 분기는 (10b)에 적힌 것 외에 무엇이 있는가?
- 답변 완료 조건: 위 다섯 필드에 대입하는 모든 줄의 `파일:라인`과 각 분기 조건 원문. 추가 분기가 없으면 함수 범위와 grep 패턴(`sentiment_score|decision_type|action|operation_advice|confidence_level` 대입)으로 조사 범위를 제시.

#### R1-Q10. LLM 중재자(`LLMDeliberationMediator`, `MultiRoundDeliberationMediator`)를 켜는 설정이 존재하는가
- GUIDE 항목: Q4-2
- 왜 묻는가: `03-decision.md` 4-2 "토론 라운드" 행은 "LLM 중재자는 정의만 있고 기본 경로에 연결되지 않는다"고 하지만, `next.md` 2절은 "활성화 설정은 못 찾음", 3절 1번은 "켜는 설정이 있는지" 확인하라고 남겼다. "LLM 토론 없음"을 확정하려면 비활성 기본값이 아니라 연결 자체가 없는지 알아야 한다.
- 질문: 저장소 어디에서든 `LLMDeliberationMediator` 또는 `MultiRoundDeliberationMediator`를 인스턴스화하거나 선택하는 코드·설정 키가 있는가? 있다면 어떤 조건에서 선택되는가?
- 답변 완료 조건: 두 클래스 이름과 관련 설정 키(`deliberation|mediator`)의 `src/`, `api/`, `main.py`, `.env.example`, `docs/` 전체 grep 결과와 조사 범위. 인스턴스화 지점이 있으면 `파일:라인`과 분기 조건 원문.

#### R1-Q11. 코드 점수(`系统评分`)와 LLM 점수의 관계를 정하는 지시나 코드가 있는가
- GUIDE 항목: Q4-3 / Q4-5
- 왜 묻는가: `00-overview.md` 핵심 발견 2는 코드 점수가 "LLM 입력 참고값일 뿐"이라고 하고, `next.md` 4절 질문 4는 "코드 점수를 따르라는 직접 지시는 찾지 못했다"고 적었다. 조사 범위(어떤 문자열로 어디를 찾았는지)가 없어 "없음"으로 확정할 수 없다.
- 질문: 레거시 시스템 프롬프트(`analyzer.py:1949-2134`)·유저 프롬프트(`_format_prompt`)·`CORE_TRADING_SKILL_POLICY`에 `系统评分`/`系统信号`(또는 코드 점수)을 LLM의 `sentiment_score`와 어떻게 관계 지을지 지시하는 문장이 있는가? 또 후처리 코드가 두 점수를 비교하거나 한쪽으로 보정하는 곳이 있는가?
- 답변 완료 조건: 지시 문장이 있으면 원문 인용과 `파일:라인`. 없으면 `系统评分|系统信号|signal_score|trend_score` 등 grep 패턴과 대상 파일 목록. 후처리 비교 코드가 있으면 `파일:라인`.

#### R1-Q12. 뉴스 검색 결과의 중복 제거 장치
- GUIDE 항목: Q5
- 왜 묻는가: `04-research.md` 5-4 "중복 제거" 행이 `미확인`(`:3777-3840` 범위에서 확인 못함)이다. 레거시 경로는 5차원 검색 결과를 이어 붙이므로, 차원 간 같은 기사가 반복되면 LLM 입력이 특정 뉴스에 치우친다.
- 질문: `search_comprehensive_intel`(`search_service.py:4384-4636`)과 그 하위 필터·랭킹 단계에서 URL 또는 제목 기준으로 중복 결과를 제거하는 코드가 있는가? 있다면 차원 안에서만인가, 차원 간에도 적용되는가?
- 답변 완료 조건: 중복 제거 코드의 `파일:라인`과 키(URL/제목/정규화 규칙) 원문, 적용 범위. 없으면 `dedup|seen|unique|set\(|url` 등 grep 패턴과 조사한 함수 범위.

### 답변 (답변자)

#### R1-Q1 답변
- 결론: **확정**. 한국 종목(`005930.KS`, 시장 태그 `kr`)이 레거시 경로를 타면 `stabilize_decision_with_structure`에 넘어가는 `fundamental_context`에는 **항상 `capital_flow` 키가 존재**하고(값은 `status="not_supported"`, `data={}`), 따라서 `analyzer.py:1094-1095`의 두 조건이 모두 참이 된다. 키가 빠지는 경로는 없다. 1차 보고서의 결론("한국은 매수가 항상 hold로 강등")은 맞고, 이번 답변으로 정적 추적이 완결됐다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/pipeline.py:595-606` | `analyze_stock()` Step 2.5 | `fundamental_context = self.fetcher_manager.get_fundamental_context(code, budget_seconds=...)` / 예외 시 `fundamental_context = self.fetcher_manager.build_failed_fundamental_context(code, str(e))` | 코드 확인 |
  | `src/core/pipeline.py:613-617`, `:1229`, `:1256-1258` | `_attach_belong_boards_to_fundamental_context()` | `enriched_context = dict(fundamental_context)` (얕은 복사), `if market != "cn": enriched_context["belong_boards"] = existing_board_list or []; return enriched_context` — `capital_flow` 키를 지우지 않는다 | 코드 확인 |
  | `src/core/pipeline.py:906`, `:1718` | `stabilize_decision_with_structure(result, trend_result, fundamental_context)` | 레거시 경로(906)와 Agent 경로(1718) 두 호출처 모두 위 변수를 그대로 넘긴다 | 코드 확인 |
  | `data_provider/base.py:4281-4286` | `get_fundamental_context()` | `if market in {"us", "hk", "jp", "kr", "tw"}: return self._build_offshore_fundamental_context(stock_code, market=market, budget_seconds=budget_seconds)` | 코드 확인 |
  | `data_provider/base.py:3963` | `_build_offshore_fundamental_context()` | `result_ctx` 초기값에 `"capital_flow": {},` 가 들어 있다 | 코드 확인 |
  | `data_provider/base.py:4057-4075` | 같은 함수 | `futu_capital_flow = (bundle_payload.get("capital_flow") if isinstance(...) and bundle_payload.get("capital_flow") else {})` → 비어 있으면 `result_ctx["capital_flow"] = self._build_fundamental_block("not_supported", {}, [...], ["not supported for this source"])` | 코드 확인 |
  | `data_provider/base.py:3865-3866` | `_fetch_offshore_fundamental_bundle()` | `if market != "hk" or not FutuFetcher.has_configured_endpoint(): return _use_yfinance()` → 한국은 Futu 분기에 들어가지 않고 yfinance로 간다 | 코드 확인 |
  | `data_provider/yfinance_fundamental_adapter.py:158-168` | `get_fundamental_bundle()` | 반환 dict 키는 `status, growth, earnings, institution, boards, belong_boards, source_chain, errors`뿐이고 `capital_flow` 키가 없다 (파일 내 `capital_flow` grep 0건) | 코드 확인 |
  | `data_provider/base.py:4225-4253` | `build_failed_fundamental_context()` | `block_names = ("valuation", ..., "capital_flow", "dragon_tiger", "boards")` 각각 `"failed"` 블록 생성 → 예외 경로에서도 `capital_flow` 키 존재 | 코드 확인 |
  | `data_provider/base.py:3678-3733` (`:3704`) | `_build_market_not_supported()` | 기본 파이프라인 꺼짐(`enable_fundamental_pipeline` false, `base.py:4272-4276`)·지수 대상(`pipeline.py:586-592`)도 `"capital_flow": self._build_fundamental_block("not_supported", ...)` 포함 | 코드 확인 |
  | `src/analyzer.py:1322-1337` | `_capital_flow_bias_with_status()` | `block = fundamental_context.get("capital_flow")` / `status`가 `_CAPITAL_FLOW_UNAVAILABLE_STATUS`(`:586-598`, `"not_supported"` 등) 또는 `"not supported"`면 `return "unavailable", status or "not_supported"`; `stock_flow`가 비면 `"empty_stock_flow"` | 코드 확인 |
  | `src/analyzer.py:1093-1105` | `stabilize_decision_with_structure()` | `if flow_bias == "unavailable": if isinstance(fundamental_context, dict) and "capital_flow" in fundamental_context: if decision_type == "buy" or advice_decision_type == "buy": _downgrade_buy_without_capital_flow(...)` | 코드 확인 |

- 동작 설명: ① `analyze_stock`이 `get_fundamental_context("005930.KS")`를 호출 → `_market_tag`(`base.py:243-256`)가 `get_suffix_market`로 `kr`을 반환 → 4281행 분기로 `_build_offshore_fundamental_context`. ② 한국은 Futu(HK 전용) 분기를 타지 않고 yfinance 번들을 받는데 이 번들에는 `capital_flow`가 없으므로 4062행 `if futu_capital_flow:`가 거짓 → 4070-4075행에서 `status="not_supported"` 블록이 `result_ctx["capital_flow"]`에 들어간다. ③ 이 `result_ctx`(또는 캐시된 같은 구조)가 반환돼 `_attach_belong_boards...`에서 얕은 복사만 거치고 `fundamental_context`로 `stabilize_decision_with_structure`에 전달된다. ④ `_capital_flow_bias_with_status`가 `"unavailable"`을 반환하고 `"capital_flow" in fundamental_context`가 참이므로, LLM 판단이 buy(또는 advice가 buy)이면 `_downgrade_buy_without_capital_flow`가 실행된다. 비-buy면 `_set_decision_stability_unavailable`만 실행된다(`analyzer.py:1106-1116`). 예외 경로(`build_failed_...`)도 `status="failed"` + `data={}`라 `empty_stock_flow`로 같은 `"unavailable"`이 된다.
- 보고서 정정 필요 여부: 결론은 정정 불필요. 다만 `03-decision.md` 4-5 (1)의 위치 `data_provider/base.py:4057-4075`는 실제로는 `:4057-4075`(Futu 분기와 `not_supported` else)로 맞고, 한국이 Futu 분기가 아니라 yfinance 번들을 쓴다는 근거(`base.py:3865`, `yfinance_fundamental_adapter.py:158-168`)를 추가하면 완전해진다.
- 조사 범위: `data_provider/base.py`(3541-4330 전 구간), `data_provider/yfinance_fundamental_adapter.py`, `src/core/pipeline.py`(555-620, 880-940, 1217-1275, 1700-1725), `src/analyzer.py`(586-600, 1043-1340, 1373-1540); grep `capital_flow`(src/ api/ main.py data_provider/), `stabilize_decision_with_structure`, `_market_tag|_is_kr_market|get_suffix_market`.

#### R1-Q2 답변
- 결론: **확정**. `AGENT_ARCH=single`에서도 `AgentExecutor`가 LLM에 노출하는 도구 목록에는 `backtest_tools.py`의 세 도구(`get_skill_backtest_summary`, `get_strategy_backtest_summary`, `get_stock_backtest_summary`)가 **모두 포함된다**. 도구 필터가 없고, 프롬프트(`AGENT_SYSTEM_PROMPT`, `LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT`)에는 이 도구 이름이나 백테스트 사용 지시가 **없다**. 1차 보고서의 "레지스트리 등록됨, 지시는 없음"은 `추론`이 아니라 `코드 확인`으로 올릴 수 있다. (참고: 보고서가 `get_skill_backtest_summary`만 언급했으나 `get_stock_backtest_summary`도 같은 방식으로 노출된다.)
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/factory.py:363`, `:366-376` | `_build_tool_registry()` | `from src.agent.tools.backtest_tools import ALL_BACKTEST_TOOLS` / `for tool_fn in (ALL_DATA_TOOLS + ALL_ANALYSIS_TOOLS + ALL_SEARCH_TOOLS + ALL_MARKET_TOOLS + ALL_BACKTEST_TOOLS + ALL_FXMACRODATA_TOOLS): registry.register(tool_fn)` | 코드 확인 |
  | `src/agent/tools/backtest_tools.py:278-282` | `ALL_BACKTEST_TOOLS` | `[get_skill_backtest_summary_tool, get_strategy_backtest_summary_tool, get_stock_backtest_summary_tool]` (`name=`은 `:131`, `:159`, `:242`) | 코드 확인 |
  | `src/agent/factory.py:582`, `:609-625` | `build_agent_executor()` | `registry = get_tool_registry(config)` → `arch != "multi"`이면 `return AgentExecutor(tool_registry=registry, ...)` — 레지스트리를 걸러내지 않고 그대로 전달 | 코드 확인 |
  | `src/agent/tools/registry.py:243-245` | `ToolRegistry.to_openai_tools()` | `return [t.to_openai_tool() for t in self._tools.values()]` (필터 인자 없음) | 코드 확인 |
  | `src/agent/executor.py:713`, `:762`; `src/agent/runner.py:367` | `AgentExecutor.run/chat`, `run_agent_loop` | `tool_decls = self.tool_registry.to_openai_tools()` / `tool_decls = tool_registry.to_openai_tools()` — 루프가 쓰는 도구 선언은 전체 레지스트리 | 코드 확인 |
  | `src/agent/executor.py:71-229`, `:230-385` | `LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT`, `AGENT_SYSTEM_PROMPT` | grep `backtest`(대소문자 무시) 0건 | 코드 확인 |
  | `src/agent/executor.py:460-467` | `CODEX_CHAT_SYSTEM_PROMPT` | `- \`get_skill_backtest_summary\`：读取指定交易技能的已保存回测汇总。`(지정한 거래 스킬의 저장된 백테스트 요약을 읽는다) — 이 프롬프트는 채팅 전용(`executor.py:569`, Codex 백엔드)이며 분석용이 아니다 | 코드 확인 |
  | `src/agent/tools/registry.py` 전체 | 권한 | `permissions`는 `ToolPolicy` 필드(`:43`, `:59`, `:67`, `:78`)로만 존재하고, 실행·노출 단계에서 검사하는 코드는 `execution.py`/`runner.py`/`registry.py`에 없다 (grep `permissions`) | 코드 확인 |

- 동작 설명: 모듈 캐시 레지스트리(`get_tool_registry`)가 데이터·분석·검색·시장·백테스트·FX 도구를 모두 등록 → `build_agent_executor`가 single일 때 이 레지스트리를 `AgentExecutor`에 그대로 넘김 → `run_agent_loop`가 매 호출 `to_openai_tools()`로 전체 도구를 LLM에 선언 → LLM이 이름과 `description`("Inspect backtest data for a specific skill when skill-scoped stats exist …")을 보고 호출할 수 있다. 분석 프롬프트가 사용을 지시하지는 않으므로 호출은 LLM 재량이다. multi 아키텍처는 에이전트별 `tool_names`로 제한하며(`base_agent.py:54`, `:255-266`; `decision_agent.py:29`는 `[]`), 이번 질문 범위 밖이다.
- 조사 범위: `src/agent/factory.py`, `src/agent/executor.py`, `src/agent/runner.py`, `src/agent/tools/registry.py`, `src/agent/tools/backtest_tools.py`, `src/agent/agents/*.py`(`tool_names`); grep `backtest`(src/agent 전체), `to_openai_tools`, `permissions`, `ALL_BACKTEST_TOOLS`.

#### R1-Q3 답변
- 결론: **확정** (기본값 기준). `config.agent_skills`의 기본값은 **빈 리스트 `[]`**, `agent_mode` 기본값은 `False`, `StockAnalysisPipeline.analysis_skills`의 기본값은 **`None`**이다. 기본 GitHub Actions 실행은 이 값들을 바꾸는 환경변수를 워크플로가 전달하지 않으므로 **레거시(단일 LLM 호출) 경로**를 탄다. `--schedule`(로컬)도 코드상 기본은 같다. 다만 로컬 `--schedule`은 사용자의 `.env`/환경변수의 `AGENT_MODE`·`AGENT_SKILLS`가 런타임에 이를 바꿀 수 있고, 그 값은 정적으로 알 수 없다(갈림 지점: `config.py:1984`, `:1992`). 1차 보고서의 `01-data.md` 범례("`AGENT_SKILLS`가 `all`이 아닌 값이면 Agent 경로")는 **불완전**해서 보정이 필요하다(아래).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/config.py:1055`, `:1984` | `agent_mode` | `agent_mode: bool = False` / `agent_mode=os.getenv('AGENT_MODE', 'false').lower() == 'true'` | 코드 확인 |
  | `src/config.py:1058`, `:1992` | `agent_skills` | `agent_skills: List[str] = field(default_factory=list)` / `agent_skills=[s.strip() for s in os.getenv('AGENT_SKILLS', '').split(',') if s.strip()]` → 미설정·빈 값이면 `[]` | 코드 확인 |
  | `.env.example:505` | 예시 설정 | `AGENT_SKILLS=` (빈 값, 주석 처리되지 않은 기본 줄). 주석(`:494-496`): `留空时，系统会使用 metadata 里声明的主默认策略 skill（内置默认是 bull_trend）`(비우면 metadata에 선언된 주 기본 전략 skill을 쓴다, 내장 기본은 bull_trend) — 이는 Agent 경로 안에서의 스킬 선택이지 Agent 경로 진입 조건이 아니다 | 코드 확인 |
  | `src/core/pipeline.py:246`, `:269` | `StockAnalysisPipeline.__init__` | `analysis_skills: Optional[List[str]] = None` / `self.analysis_skills = list(analysis_skills) if analysis_skills is not None else None` | 코드 확인 |
  | `src/core/pipeline.py:561-571` | `analyze_stock()` | `use_agent = getattr(self.config, 'agent_mode', False)` → `if self.analysis_skills: use_agent = True` → `configured_skills = getattr(self.config, 'agent_skills', []); if configured_skills and configured_skills != ['all']: use_agent = True` | 코드 확인 |
  | `src/services/analysis_service.py:140-149` | `AnalysisService.analyze_stock()` | `StockAnalysisPipeline(config=config, ..., analysis_skills=skills, ...)` — `skills`는 API 요청의 `skills`(`api/v1/endpoints/analysis.py:608`) 또는 작업 큐(`task_queue.py:826`)에서 온다. **`analysis_skills`를 채우는 호출처는 이곳뿐이다** | 코드 확인 |
  | `main.py:962-970`, `src/services/task_service.py:201-208`, `bot/commands/batch.py:108-113` | 그 밖의 생성처 | `analysis_skills` 인자를 넘기지 않음 → `None` | 코드 확인 |
  | `.github/workflows/00-daily-analysis.yml:74`, `:81` | `env:` | AGENT 관련 키는 `AGENT_GENERATION_BACKEND`, `AGENT_LITELLM_MODEL` 두 개뿐. `AGENT_MODE`, `AGENT_SKILLS`, `AGENT_ARCH` grep 결과 0건. `.env` 생성·로드 단계도 없음(grep `\.env|dotenv` 0건, 저장소에 `.env` 파일 없음, `.gitignore`) | 코드 확인 |
  | `main.py:1837-1850` | `--schedule` | `scheduled_task` → `run_full_analysis(runtime_config, args, ...)` → `main.py:962`의 `StockAnalysisPipeline(...)`(skills 인자 없음). `runtime_config`는 `_reload_runtime_config()`로 환경/`.env`를 다시 읽는다 | 코드 확인 |

- 동작 설명: 기본 Actions(`python main.py`) → `main.py:962`에서 `analysis_skills=None`인 파이프라인 생성 → `analyze_stock`에서 `agent_mode=False`, `analysis_skills=None`(falsy), `agent_skills=[]`(falsy)이므로 `use_agent=False` → 레거시 단일 LLM 경로. Agent 경로가 켜지는 입력은 세 가지다. (a) `AGENT_MODE=true`, (b) API 요청 본문의 `skills`(→ `analysis_skills`), (c) `AGENT_SKILLS`가 비어 있지 않고 `["all"]`이 아닌 값. `AGENT_SKILLS=all`은 `['all']`이라 자동 활성화에서 제외된다. **보고서 정정 필요**: `01-data.md` 범례에 "(b) API 요청의 `skills`로도 Agent가 자동 활성화되고 `AGENT_MODE=true`도 있다"를 추가해야 하며, 기본 Actions·로컬 스케줄 실행은 레거시 경로라는 확정 사실을 적을 수 있다.
- 조사 범위: `src/config.py`(1050-1060, 1980-1995, 3105-3145), `src/core/pipeline.py`(240-290, 555-575), `main.py`(955-975, 1835-1860), `src/services/analysis_service.py`, `src/services/task_service.py`, `src/services/task_queue.py`, `bot/commands/batch.py`, `.env.example`, `.github/workflows/00-daily-analysis.yml`; grep `analysis_skills`, `AGENT_SKILLS|AGENT_MODE|AGENT_ARCH`(.github, .env.example, docker), `skills=`(src/ api/ bot/ main.py), `StockAnalysisPipeline(`(저장소 전체, tests 제외).

#### R1-Q4 답변
- 결론: **확정**. `_augment_historical_with_realtime`는 **시장 단계(장중/장후)나 시각을 보지 않는다.** 보는 것은 (1) 데이터·시세 유효성, (2) `ENABLE_REALTIME_TECHNICAL_INDICATORS`, (3) 시장 현지 날짜가 **거래일인가**, (4) 마지막 일봉 날짜 대 시장 현지 오늘 날짜의 비교뿐이다. 그 결과 거래일이면 **장전(예: 개장 전 아침)이든 장후이든 항상 "오늘 날짜의 봉"이 생기거나 덮어써진다**. 이는 질문이 우려한 동작이 코드상 실제로 가능하다는 뜻이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/pipeline.py:2745-2750` | 선행 가드 | `if df is None or df.empty or 'close' not in df.columns: return df` / `if realtime_quote is None: return df` / `if price is None or not (isinstance(price, (int, float)) and price > 0): return df` → 생략 | 코드 확인 |
  | `src/core/pipeline.py:2753-2757` | 설정 가드 | `enable_realtime_tech = getattr(self.config, 'enable_realtime_technical_indicators', True)` / `if not enable_realtime_tech: return df` → 생략 (기본 `True`, `config.py:1276`) | 코드 확인 |
  | `src/core/pipeline.py:2758-2762` | 거래일 가드 | `market_today = get_market_now(market).date()` / `if market and not is_market_open(market, market_today): return df` → 비거래일이면 생략. `is_market_open`은 날짜의 `cal.is_session()`만 본다(`trading_calendar.py:151-175`), 시각은 안 본다 | 코드 확인 |
  | `src/core/pipeline.py:2779-2795` | 덮어쓰기 | `if last_date >= market_today:` → `df.loc[idx, 'close'] = price`, `open/high/low/volume/amount/pct_chg`도 시세 값으로 교체(`vol`·`amt`·`pct`는 값이 있을 때만) — 마지막 행이 이미 오늘 날짜면 그 행을 실시간 값으로 덮어쓴다 | 코드 확인 |
  | `src/core/pipeline.py:2796-2810` | 추가 | `else: # 追加一行虚拟的当日实时 K 线。` (가상 당일 실시간 K선을 한 행 추가) → `new_row = {... 'date': market_today, 'open': open_p, ..., 'close': price, 'volume': vol, ...}` / `df = pd.concat([df, new_df], ignore_index=True)` | 코드 확인 |
  | `src/core/pipeline.py:651-655` | 호출처 | `if self.config.enable_realtime_quote and realtime_quote: df = self._augment_historical_with_realtime(df, realtime_quote, code, market=market)` / `trend_result = self.trend_analyzer.analyze(df, code)` — 결과 DataFrame이 `StockTrendAnalyzer.analyze`에 들어간다. 호출처는 이 한 곳뿐이다(grep) | 코드 확인 |
  | `src/core/pipeline.py:638-646` | 입력 일봉 | `end_date = frozen if frozen else get_market_now(_mkt).date()` / `start_date = end_date - timedelta(days=89)` / `historical_bars = self.db.get_data_range(code, start_date, end_date)` | 코드 확인 |

- 동작 설명: 분기표는 다음과 같다.

  | 조건 | 동작 |
  |---|---|
  | 시세가 없거나 `price<=0`, 일봉이 비었거나, 기능 꺼짐(`ENABLE_REALTIME_TECHNICAL_INDICATORS=false`), 또는 `ENABLE_REALTIME_QUOTE=false`/시세 조회 실패(호출처 조건) | 생략(원본 DataFrame 그대로) |
  | 시장 현지 오늘이 비거래일(휴일·주말) | 생략 |
  | 거래일이고 `마지막 일봉 날짜 >= 시장 현지 오늘` | 마지막 행을 시세 값으로 덮어쓰기 |
  | 거래일이고 `마지막 일봉 날짜 < 시장 현지 오늘` | 오늘 날짜의 가상 행 추가 |

  장후 18:00 Actions 실행(CN)에서 오늘 일봉이 DB에 이미 있으면 덮어쓰기, 없으면 추가이고 시세가 종가 근처라 MA 차이는 작다. 장전 시각 실행이면 전일 종가가 `price`인 시세가 "오늘 봉"으로 추가된다(예: 미국 UTC 10:00 = 뉴욕 05:00~06:00, 거래일이므로 추가됨; R1-Q7 참조). `frozen`(`get_frozen_target_date`)이 과거 날짜여도 `market_today`는 실제 오늘이라, 과거 고정 실행에서도 오늘 날짜 행이 붙는 분기가 존재한다(`pipeline.py:2760`, `:2779`). 이 함수는 호출처 조건과 달리 `realtime_quote`의 시각(`as_of`)은 확인하지 않는다.
- 조사 범위: `src/core/pipeline.py:630-665`, `:2733-2811`; `src/core/trading_calendar.py:151-176`, `:214-236`; `src/config.py:1274-1276`, `:2307-2310`; grep `_augment_historical_with_realtime`(src/ api/ main.py).

#### R1-Q5 답변
- 결론: **없음 확정**. `.github/workflows/` 아래 전체 워크플로와 `00-daily-analysis.yml`이 호출하는 스크립트에는 `data/stock_analysis.db`(또는 `DATABASE_PATH`)를 캐시·복원·커밋·아티팩트 다운로드하는 단계가 **없다**. 일일 분석 워크플로가 업로드하는 아티팩트는 `reports/`와 `logs/`뿐이고 `data/`(DB 위치)는 포함되지 않는다. 따라서 Actions의 DB는 실행마다 비어서 시작한다(1차 보고서 `02-schedule.md` 3-3 결론 확정). 호출 스크립트 쪽도 `main.py` 하나뿐이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `.github/workflows/00-daily-analysis.yml:44-61` | 스텝 구성 | `actions/checkout@v5` → `actions/setup-python@v6` → `pip install` → `mkdir -p data logs reports`(빈 디렉터리 생성) | 코드 확인 |
  | `.github/workflows/00-daily-analysis.yml:543-550` | 실행 | `python main.py --market-review $FORCE_RUN_ARG` / `python main.py --no-market-review ...` / `python main.py $FORCE_RUN_ARG` — 호출 대상은 `main.py` 하나 | 코드 확인 |
  | `.github/workflows/00-daily-analysis.yml:552-560` | 아티팩트 | `uses: actions/upload-artifact@v6` ... `path: \| reports/ \| logs/` `retention-days: 30` — `data/` 미포함, 업로드만 있고 `download-artifact`는 없음 | 코드 확인 |
  | `.github/workflows/*.yml` 전체 | grep | `actions/cache`는 `desktop-release.yml:185`(데스크톱 빌드)에만, `download-artifact`는 `desktop-release.yml:232`, `pr-review.yml:221`에만 있고 DB와 무관. `stock_analysis.db`, `DATABASE_PATH`, `\.db\b`, `git commit`, `git push`, `git add` 매치 0건 | 코드 확인 |
  | `src/config.py:1222`, `:2196` | DB 경로 기본값 | `database_path: str = "./data/stock_analysis.db"` — 워크플로 `env:`에 `DATABASE_PATH` 없음 | 코드 확인 |
  | `.gitignore:57`, `:62` | 저장소 보관 | `/data/`, `*.db` 무시, `git ls-files`에 `.db`·`data/` 파일 0건 → 저장소에서 복원되는 DB도 없음 | 코드 확인 |

- 동작 설명: Actions 실행 시 runner는 새 VM이다. 체크아웃된 저장소에는 DB가 없고(.gitignore), `mkdir -p data`로 빈 폴더만 만든 뒤 `main.py`가 새 SQLite를 만든다. 실행이 끝나면 `reports/`, `logs/`만 아티팩트로 올라가고 DB는 VM과 함께 사라진다. 그러므로 Actions 안에서 자동 백테스트·과거 분석 이력 기반 기능은 직전 실행의 데이터를 쓰지 못한다(같은 실행 내 저장분은 사용 가능).
- 조사 범위: `.github/workflows/` 10개 파일(`00-daily-analysis.yml`, `auto-tag.yml`, `ci.yml`, `create-release.yml`, `desktop-release.yml`, `docker-publish.yml`, `ghcr-dockerhub.yml`, `network-smoke.yml`, `pr-review.yml`, `stale.yml`), `.github/scripts/`(`ai_review.py`, `build_release_notes.py` — 일일 분석 워크플로가 호출하지 않음), grep `actions/cache|download-artifact|upload-artifact|git commit|git push|git add|stock_analysis\.db|DATABASE_PATH|\.db\b|data/|sqlite|curl|gh |tar|cp |mv `(워크플로 전체), `.gitignore`, `git ls-files`.

#### R1-Q6 답변
- 결론: **확정**. Web/API 수동 분석(동기·비동기 모두)은 `AnalysisService.analyze_stock` → `StockAnalysisPipeline.process_single_stock` → `analyze_stock`을 거치며, 그 안에서 `stabilize_decision_with_structure`, `apply_phase_decision_guardrails`, `apply_daily_market_context_guardrail` **세 가드레일이 모두** 실행된다. 레거시 경로(`pipeline.py:906-927`)와 Agent 경로(`:1718`, `:1738`, `:1766`) 양쪽에 있다. 빠지는 가드레일은 없다. 단, **분석이 아닌 에이전트 채팅 엔드포인트**(`api/v1/endpoints/agent.py`)는 파이프라인을 거치지 않는다(아래).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `api/v1/endpoints/analysis.py:329-348` | `trigger_analysis()` | `@router.post("/analyze", ...)` `def trigger_analysis(request: AnalyzeRequest, ...)` | 코드 확인 |
  | `api/v1/endpoints/analysis.py:441-450` | 모드 분기 | `if not request.async_mode: ... return _handle_sync_analysis(stock_codes[0], request, ...)` / `return _handle_async_analysis_batch(stock_codes, request, ...)` | 코드 확인 |
  | `api/v1/endpoints/analysis.py:599-611` | `_handle_sync_analysis()` | `service = AnalysisService()` / `result = service.analyze_stock(stock_code=..., skills=getattr(request, "skills", None), analysis_phase=request.analysis_phase, ...)` | 코드 확인 |
  | `api/v1/endpoints/analysis.py:471`, `:509` | `_handle_async_analysis_batch()` | `task_queue = get_task_queue()` / `task_queue.submit_tasks_batch(**submit_kwargs)` | 코드 확인 |
  | `src/services/task_queue.py:437`, `:526-535`, `:758-826` | `submit_tasks_batch` → `_execute_task` | `self.executor.submit(self._execute_task, ...)` → `service = AnalysisService()` (`:803`) → `result = service.analyze_stock(... skills=skills, ...)` (`:818-826`) | 코드 확인 |
  | `src/services/analysis_service.py:140-163` | `AnalysisService.analyze_stock()` | `pipeline = StockAnalysisPipeline(config=config, ..., analysis_skills=skills, ...)` / `result = pipeline.process_single_stock(code=stock_code, skip_analysis=False, single_stock_notify=send_notification, report_type=rt, analysis_target=analysis_target)` | 코드 확인 |
  | `src/core/pipeline.py:3295`, `:3368` | `process_single_stock()` | `result = self.analyze_stock(code, report_type, **analyze_kwargs)` | 코드 확인 |
  | `src/core/pipeline.py:561-571`, `:664` | `analyze_stock()` | `use_agent`가 참이면 `return self._analyze_with_agent(...)`, 아니면 레거시 계속 | 코드 확인 |
  | `src/core/pipeline.py:906-927` | 레거시 가드레일 | `stabilize_decision_with_structure(result, trend_result, fundamental_context)` → `adjustments = apply_phase_decision_guardrails(...)` → `market_context_adjustments = apply_daily_market_context_guardrail(...)` | 코드 확인 |
  | `src/core/pipeline.py:1718`, `:1738`, `:1766` | `_analyze_with_agent()` | 같은 세 함수 호출 | 코드 확인 |
  | `src/**`, `api/**`, `bot/**`, `main.py` | 호출처 전수 | 세 함수의 비테스트 호출처는 `pipeline.py:906/907/916`, `:1718/1738/1766`뿐 | 코드 확인 |

- 동작 설명: CLI(`main.py` → `pipeline.run()` → 종목별 `process_single_stock`)와 Web/API 수동 분석, 포트폴리오 엔드포인트(`portfolio.py:463`의 `queue.submit_tasks_batch`), 봇 배치(`bot/commands/batch.py`)가 모두 `analyze_stock`으로 수렴한다. API 쪽 차이는 `skills`(요청)·`analysis_phase`·`report_language`·`portfolio_context` 인자가 파이프라인 생성자로 전달된다는 것뿐이다. `skills`가 비어 있지 않으면 R1-Q3처럼 Agent 경로가 자동 선택되지만 그 경로에도 가드레일 3종이 있다. **예외**: 채팅용 `api/v1/endpoints/agent.py`(`build_agent_chat_executor`, `bot/commands/ask.py`의 `build_agent_executor`)는 `AgentExecutor`/`AgentChatExecutor`만 쓰고 `StockAnalysisPipeline`을 거치지 않으므로 이 가드레일들이 적용되지 않는다(자유 대화 응답이며 최종 결정 객체를 만들지 않는다).
- 조사 범위: `api/v1/endpoints/analysis.py`(329-460, 585-655, 보조), `src/services/task_queue.py`, `src/services/analysis_service.py`, `src/core/pipeline.py`(555-670, 900-945, 1700-1790, 3295-3370), `api/v1/endpoints/portfolio.py`, `api/v1/endpoints/agent.py`; grep `apply_phase_decision_guardrails|apply_daily_market_context_guardrail|stabilize_decision_with_structure`(저장소 전체), `submit_tasks_batch|submit_task\b|\.analyze_stock\(`.

#### R1-Q7 답변
- 결론: **확정**. 평일 UTC 10:00에 미국 종목을 분석하면 뉴욕 현지 시각은 **06:00(EDT, 3월 둘째 일요일~11월 첫째 일요일) 또는 05:00(EST)** 이고, 미국 정규장 개장(09:30 ET, 시각은 `exchange_calendars`의 XNYS 캘린더 값이라 레포에는 없다)보다 항상 이르다. 그 날이 미국 거래일이면 `infer_market_phase`는 **`premarket`**을, 미국 휴장일이면 `non_trading`을 반환한다. "마지막 완전 일봉 날짜"는 **직전 거래 세션**(화~금이면 전 거래일, 월요일이면 직전 금요일, 휴장일이면 그 이전 마지막 세션)이다. `premarket`이면 `phase_decision_guardrail`이 즉시 매매 신호를 "대기"로 바꾼다. 단, 휴장일 종목은 기본 설정에서 아예 분석 대상에서 빠진다(`main.py:493-516`), 그래서 Actions 기본 실행에서 실제로 보이는 값은 `premarket`이다. 1차 보고서 `02-schedule.md` 3-6의 "별도 cron 필요" 서술은 `추론`에서 `코드 확인`으로 올릴 수 있다. 전제: `exchange-calendars` 설치(`requirements.txt:10`), 미설치면 `unknown`(아래).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/trading_calendar.py:41`, `:44-51` | 시장 정의 | `MARKET_EXCHANGE = {..., "us": "XNYS", ...}` / `"us": "America/New_York"` | 코드 확인 |
  | `src/core/trading_calendar.py:214-236` | `get_market_now()` | `if tz_name: return datetime.now(ZoneInfo(tz_name))` — 현지 시각 | 코드 확인 |
  | `src/core/trading_calendar.py:393-414` | `infer_market_phase()` | `if not cal.is_session(local_date): return MarketPhase.NON_TRADING` / `session_open = _as_market_datetime(cal.session_open(session), tz_name)` / `if market_now < session_open: return MarketPhase.PREMARKET` / `if market_now >= session_close: return MarketPhase.POSTMARKET` | 코드 확인 |
  | `src/core/trading_calendar.py:393-396`, `:30-33` | 캘린더 미설치 | `if not _XCALS_AVAILABLE: return MarketPhase.UNKNOWN` (설치되면 `_XCALS_AVAILABLE=True`) | 코드 확인 |
  | `src/core/trading_calendar.py:239-282` | `get_effective_trading_date()` | 비거래일: `return cal.date_to_session(local_date, direction="previous").date()`(`:266-267`) / 거래일: `if market_now >= close_local: return session.date()`(`:278-279`) / `return cal.previous_session(session).date()`(`:281`) — 개장 전 거래일이면 전 세션 | 코드 확인 |
  | `src/core/pipeline.py:476-484` | 단계 구성 | `market_phase_context = build_market_phase_context(market=market, current_time=current_time, trigger_source=self.query_source, analysis_phase=getattr(self, "analysis_phase", "auto"))` — Actions/CLI는 `analysis_phase="auto"`(`:247`, `:270`)라 달력 추론 사용 | 코드 확인 |
  | `src/core/trading_calendar.py:551-590` | `build_market_phase_context()` | `analysis_phase="auto"`면 `phase = infer_market_phase(...)`, `effective_daily_bar_date = get_effective_trading_date(...)` | 코드 확인 |
  | `main.py:493-516`, `src/core/trading_calendar.py:618-635` | 종목 필터 | `open_markets = get_open_markets_today()`(각 시장 **현지 날짜**의 `is_market_open`) / `if mkt in open_markets or mkt is None: filtered_codes.append(code)` — `trading_day_check_enabled` 기본 `True`(`config.py:1270`), 워크플로도 기본 `'true'`(`00-daily-analysis.yml:429`), `--force-run`이면 필터 생략(`main.py:493`) | 코드 확인 |
  | `src/phase_decision_guardrail.py:18`, `:170-197` | `CONSERVATIVE_ACTION_PHASES` | `{"premarket", "non_trading", "unknown"}` / `has_non_intraday_action = (phase in CONSERVATIVE_ACTION_PHASES and _has_immediate_buy_sell_signal(...))` → `phase_decision["immediate_action"] = _safe_wait_action(language)`(`"等待盘中确认，禁止追高。"` = 장중 확인을 기다리고 추격 매수 금지), 처음 신뢰도가 高면 低로(`:183-185`) | 코드 확인 |

- 동작 설명: Actions cron `0 10 * * 1-5`(`00-daily-analysis.yml:6`)가 UTC 월~금 10:00에 돈다. UTC 평일이면 뉴욕 현지 날짜도 같은 평일이므로 `get_open_markets_today`가 미국 거래일에만 `us`를 포함한다. 포함된 종목은 `build_market_phase_context` → `infer_market_phase`에서 `market_now(06:00/05:00 ET) < session_open`이라 `premarket`, `effective_daily_bar_date`는 전 세션 날짜이다. 이후 `apply_phase_decision_guardrails`가 `decision_type`이 buy/sell이거나 `operation_advice`에 즉시 매매 문구가 있으면 `immediate_action`만 교체하고 신뢰도 高→低로 내린다. 그 함수는 `decision_type`, `action`, `sentiment_score`를 바꾸지 않는다. 같은 시점에 R1-Q4의 증강 함수는 거래일이라 오늘 날짜 가상 행을 추가한다. 달력 미설치(`ImportError`)면 `unknown`이지만 `unknown`도 `CONSERVATIVE_ACTION_PHASES`에 포함돼 같은 가드레일이 걸린다. UTC 10:00은 한국(19:00 KST)·일본(19:00 JST)·홍콩(18:00)·중국(18:00)에서는 모두 장 마감 후라 `postmarket`이다(`session_close` 이후, `:414-415`).
- 조사 범위: `src/core/trading_calendar.py` 전체 함수 목록(`:375-447`, `:551-617`, `:618-635`), `src/phase_decision_guardrail.py:1-210`, `main.py:480-520`, `src/core/pipeline.py:470-490`, `.github/workflows/00-daily-analysis.yml:1-10`, `:429`; grep `premarket|PREMARKET`(src/), `_XCALS_AVAILABLE`.

#### R1-Q8 답변
- 결론: **확정**. (1) `_refresh_decision_action_for_final_result`가 넘기는 `sentiment_score`는 `dashboard.decision_score_calibration.adjusted_score`가 있으면 그 값, 없으면 `result.sentiment_score`이고, `guardrail_reason`은 `calibration.guardrail_reason` → `dashboard.decision_stability.reason` → `result.guardrail_reason`(파이프라인에서는 항상 미설정) 순서로 찾은 뒤 중립 키워드 휴리스틱으로 보충한 값이다. (2) 가드레일 (1)~(4)(및 (5))가 강등한 결과에 대해서는 (9)가 **참이 될 수 없다**(점수가 45~59 "watch" 구간으로 고정되고 사유도 설정됨). (7)은 행동 필드를 바꾸지 않아 해당 없다. (3) **(8)만 예외로 되돌림이 가능하다**: 대시장 가드가 점수를 `min(52, 점수)`로만 낮추고 `guardrail_reason`을 설정하지 않으므로, 원래 LLM 점수가 40 미만(buy 판단과 모순되는 점수)이면 (9)가 `watch`를 `reduce`/`sell`로 바꾼다. 1차 보고서 `03-decision.md`의 "방향성" 행("(9)만 점수가 높으면 buy로 되돌릴 수 있음")은 **보정이 필요**하다. (8) 뒤에는 점수가 52 이하로 고정되므로 buy 방향 되돌림은 불가능하고, 가능한 되돌림은 reduce/sell 방향이다. 또 보고서가 `_refresh...`가 `build_action_fields`를 직접 호출한다고 본 것은 사실과 달리 `resolve_decision_signal_action_fields`를 거친다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/pipeline.py:2320-2339` | `_refresh_decision_action_for_final_result()` | `if previous_advice != current_advice: result.action = None; result.action_label = None` / `fields = resolve_decision_signal_action_fields(result, report_type=str(report_type or ""))` / `result.action = fields["action"]` | 코드 확인 |
  | `src/services/decision_signal_extractor.py:177-204` | `resolve_decision_signal_action_fields()` | `score = _effective_signal_score(_score_from_result(getattr(result, "sentiment_score", None)), score_calibration)` / `guardrail_reason = _extract_guardrail_reason(result, dashboard, score=score, raw_action=raw_action)` / `return build_action_fields(..., sentiment_score=score, guardrail_reason=guardrail_reason, align_with_score=True)` | 코드 확인 |
  | `src/services/decision_signal_extractor.py:269-274` | `_effective_signal_score()` | `adjusted = _calibrated_or_raw_score(calibration, prefer="adjusted")` / `return adjusted if adjusted is not None else score` | 코드 확인 |
  | `src/services/decision_signal_extractor.py:327-360` | `_extract_guardrail_reason()` | `reason = _first_text(score_calibration.get("guardrail_reason"), _as_mapping(dashboard.get("decision_stability")).get("reason"), getattr(result, "guardrail_reason", None))` → 없고 `score_action_conflicts_without_guardrail(...)`가 참이면 `operation_advice`(buy 구간이면 `analysis_summary`, `buy_reason`, 관찰 조건도)에 `_NEUTRAL_GUARDRAIL_HINTS`(`:300-325`: `"等待","待","需要确认","回踩","支撑","压力","风险","资金","突破","不追","不宜","缺少","缺少确认","未确认","wait","waiting","pending confirmation","lack confirmation","pullback","support","resistance","risk","flow"`) 중 하나가 들어 있으면 그 문장을 사유로 반환 | 코드 확인 |
  | `src/schemas/decision_scale.py:158-171` | `score_action_conflicts_without_guardrail()` | `if str(guardrail_reason or "").strip(): return False` / `if normalized_action not in {"hold", "watch"}: return False` / `score_action = action_for_score(score)` / `return score_action in {"buy", "reduce", "sell"}` | 코드 확인 |
  | `src/schemas/decision_action.py:389-396` | `build_action_fields()` | `if align_with_score and score_action_conflicts_without_guardrail(...): score_action = action_for_score(sentiment_score); if score_action in _ACTION_VALUES: action = score_action` | 코드 확인 |
  | `src/schemas/decision_scale.py:20-26` | 점수 구간 | `(80,100) buy`, `(60,79) buy`, `(40,59) watch`, `(20,39) reduce`, `(0,19) sell` | 코드 확인 |
  | `src/analyzer.py:1419-1437` | `_bound_hold_watch_sentiment_score()` | `adjusted_score = min(59, max(45, score))` / `result.sentiment_score = adjusted_score` / `_record_decision_score_calibration(..., adjusted_score=..., guardrail_reason=reason)` (`:1396-1416`에서 `calibration["guardrail_reason"] = guardrail_reason`) | 코드 확인 |
  | `src/analyzer.py:1520`, `:1621-1623`, `:1538-1560` | 호출처 | 자금흐름 강등(1): `_bound_hold_watch_sentiment_score(result, reason=reason, final_action="hold")`. 구조 강등 (2)(3)(4)(5): `_downgrade_to_structural_hold(...)` → `_set_structural_hold_wording(..., calibrate_score=True)` → `_bound_hold_watch_sentiment_score(result, reason=reason, ...)` (`reason`은 비어 있지 않은 템플릿 문장) | 코드 확인 |
  | `src/analyzer.py:1440-1493` | `_apply_hold_watch_dashboard()` | `stability = {"applied": True, "reason": reason, ...}` / `dashboard["decision_stability"] = stability` | 코드 확인 |
  | `src/daily_market_context_guardrail.py:79-91`, `:280-285` | `apply_daily_market_context_guardrail()` (8) | `result.decision_type = "hold"` / `result.operation_advice = softened_advice`(`"观望"`) / `result.sentiment_score = _cap_conservative_sentiment_score(...)` = `min(52, max(0, score))` — `calibration`, `decision_stability`, `guardrail_reason`을 **쓰지 않는다** | 코드 확인 |
  | `src/phase_decision_guardrail.py:170-205` | (7) | `result.confidence_level`, `dashboard.phase_decision`만 변경. 장중 복기 문구 교체(`:341-371`)에서만 `result.operation_advice`가 바뀌는데 교체 문구(`"等待盘中确认，禁止追高。"`, `"Wait for intraday confirmation; do not chase."`)에 힌트 `"等待"`/`"wait"`가 있다 | 코드 확인 |
  | `src/core/pipeline.py:934-938`(레거시), `:1702`, `:1719`, `:1747`, `:1778`(Agent) | `_refresh...` 호출 위치 | 레거시는 가드레일 3종이 모두 끝난 뒤 1회, Agent는 가드레일마다 1회 | 코드 확인 |

- 동작 설명: 
  - **(1)~(5) 강등 후**: `decision_type="hold"`, `operation_advice`가 `"持有观察"`/`"震荡观望"`/`"洗盘观察"`로 바뀌고 점수는 45~59로 클램프된다(`min(59, max(45, score))`). 갱신 단계는 `calibration.adjusted_score`를 읽으므로 `action_for_score`는 `watch`다. `score_action_conflicts_without_guardrail`은 `watch`가 `{"buy","reduce","sell"}`에 없어 거짓이다. 사유도 `calibration.guardrail_reason`에 있어서 이중으로 막힌다. 되돌림 불가.
  - **(6) 문구만 정리**(`calibrate_score=False`)와 **자금흐름 불가 + 비-buy**(`_set_decision_stability_unavailable`, `analyzer.py:1373-1393`): 점수는 안 바뀌지만 `decision_stability.reason`이 비어 있지 않아(`"资金流不可用，未使用资金流校准"` 포함) `_extract_guardrail_reason`가 사유로 채택, (9)는 거짓이다. 이때 `applied=False`여도 이 함수는 `applied`를 확인하지 않는다(반면 `decision_scale.py`의 `extract_decision_guardrail_reason`은 `applied`가 False면 stability 사유를 제외한다, `include_stability_reason`). 
  - **(7)**: 행동 필드를 바꾸지 않아 (9) 입력이 달라지지 않는다.
  - **(8)**: 발동 조건이 `decision_type == "buy"`이거나 advice에 공격적 매수 문구가 있을 때(`daily_market_context_guardrail.py:218-231` `_has_aggressive_buy_signal`)이며, 이후 `action`은 `"观望"`에서 `watch`로 재계산된다(advice가 바뀌었으므로 `result.action=None`). 점수는 `min(52, 원점수)`이다. 원점수가 40~100이면 결과가 40~52라 `watch` 구간이므로 충돌이 없다. 원점수가 0~39면 그대로 남아 `reduce`(20~39)/`sell`(0~19)가 된다. 사유는 `"观望"`에 힌트 키워드가 없어 None이다. 그러면 (9)가 `watch`→`reduce`/`sell`로 바꾼다. 이 경우는 LLM이 buy를 말하면서 점수를 40 미만으로 준 모순 출력일 때만 생긴다. 코드상 그 경우가 배제되지는 않는다.
  - **보충 발견**: `AnalysisService._build_analysis_response`(`analysis_service.py:206-216`)와 `populate_decision_action_fields`(`analyzer.py:1900-1925`)는 `guardrail_reason=getattr(result, "guardrail_reason", None)`를 쓰는데, `AnalysisResult`(`analyzer.py:1718`)에는 그 필드가 없고 파이프라인 어디에서도 설정하지 않는다(`history_service.py:1106`만 이력 로드 시 `setattr`). 그래서 API 동기 응답의 `summary.action`은 `decision_stability.reason`에 의존한 위 (6)/불가 케이스에서 점수 구간에 다시 정렬될 수 있어 파이프라인 최종 `result.action`과 다를 수 있다.
- 조사 범위: `src/core/pipeline.py:2320-2340`, `:900-940`, `:1700-1790`; `src/services/decision_signal_extractor.py`(전 함수), `src/schemas/decision_action.py`, `src/schemas/decision_scale.py`(전체), `src/analyzer.py`(1043-1640, 1900-1925), `src/daily_market_context_guardrail.py`(전체), `src/phase_decision_guardrail.py`(전체), `src/services/analysis_service.py:195-225`; grep `guardrail_reason`(src/ api/), `populate_decision_action_fields`, `score_action_conflicts_without_guardrail`.

#### R1-Q9 답변
- 결론: **확정**. `_finalize_dashboard_payload`(`orchestrator.py:1370-1662`)와 그 보조 함수가 다섯 필드에 쓰는 곳은 **끝에서 무조건 쓰는 한 묶음(`:1646-1650`)** 이고, 그 값을 만드는 분기는 아래 표가 전부다. 이전 보고서(10b)가 적은 것 외에 **`confidence_level`이 항상 덮어써진다**는 점이 빠져 있다(**보고서 정정 필요**). `action` 필드는 이 함수 어디에서도 쓰지 않는다. 같은 호출 체인에서 `decision_type`은 `_prepare_dashboard_payload`(`:1364`)와 `_apply_risk_override`(`:1927`)에서도 쓰인다.
- 근거: 다섯 필드에 대입하는 모든 줄.

  | 필드 | 위치 | 분기 조건 / 원문 | 검증 |
  |---|---|---|---|
  | `decision_type` | `orchestrator.py:1393-1400` | `decision_type = (application.post_risk_signal.value if risk_applied else normalize_decision_signal(payload.get("decision_type") or (base_opinion.signal if base_opinion else "hold")))` → `:1649` `payload["decision_type"] = decision_type` | 코드 확인 |
  | `decision_type` (전 단계) | `:1364-1367`, `:1927` | `_prepare_dashboard_payload`: `prepared["decision_type"] = normalize_decision_signal(prepared.get("decision_type") or (base_opinion.signal ...))` / `_apply_risk_override`: `dashboard["decision_type"] = new_signal` (리스크 규칙 적용 시) | 코드 확인 |
  | `sentiment_score` | `:1402-1408` | `sentiment_score = payload.get("sentiment_score")` → `int(...)` 실패 시 `_estimate_sentiment_score(decision_type, confidence)`(`:2150-2158`, buy 65~79, hold 45~59, sell 20~39 선형) / `if risk_applied: sentiment_score = _adjust_sentiment_score(sentiment_score, decision_type)`(`:2051-2059`, buy 60~79, hold 40~59, sell 0~39 클램프) → `:1646` | 코드 확인 |
  | `operation_advice` | `:1467-1481` | `operation_advice_raw = payload.get("operation_advice")` / `if risk_applied:` → `_adjust_operation_advice(pre_risk_advice, decision_type)`(`:2062-2073`: `"买入"/"观望"/"减仓/卖出"`, 다르면 `f"{...}（原建议已被风控下调）"`) / `else:` → `_normalize_operation_advice_value(operation_advice_raw, decision_type)`(`:2136-2139`: 문자열이면 그대로, 아니면 `_signal_to_operation`) → `:1648` | 코드 확인 |
  | `confidence_level` | `:1401`, `:1650` | `confidence = float(base_opinion.confidence if base_opinion is not None else 0.5)` … `payload["confidence_level"] = _confidence_label(confidence)` — **`risk_applied`와 무관하게 항상 실행**. `_confidence_label`(`:2142-2147`): `>= 0.75` → `"高"`, `>= 0.45` → `"中"`, 그 외 `"低"` | 코드 확인 |
  | `confidence`의 출처 | `src/agent/agents/decision_agent.py:271-282` | `AgentOpinion(... confidence=min(1.0, _score / 100.0), ...)` — decision 에이전트의 `confidence`는 LLM이 쓴 `sentiment_score/100`이다. `base_opinion`은 `decision` 우선(`orchestrator.py:1855-1870`) | 코드 확인 |
  | `action` | `orchestrator.py` 전체 | `\["action"\]`/`"action"` 대입 grep 0건. LLM 페이로드의 `action`이 그대로 통과 | 코드 확인 |
  | 보조 함수 | `:1664-1850`, `:1947-2010` | `_collect_*`, `_build_data_perspective`, `_merge_risk_warning`, `_mark_partial_dashboard` 등에는 다섯 필드 대입이 없다 (`:1664-2050` 범위 grep으로 `decision_type` 대입 `:1927` 한 줄만 확인) | 코드 확인 |

- 동작 설명: `_resolve_dashboard_payload`(`:1309-1339`)가 `_prepare_dashboard_payload` → `_apply_risk_override`(위험 규칙이 적용되면 `decision_type`만 변경) → `_finalize_dashboard_payload` 순으로 호출한다. 파생값은 다음과 같다. 점수는 LLM 값이 있으면 유지하고 없을 때만 추정하며, 리스크가 적용된 때만 구간으로 클램프한다. `operation_advice`는 LLM 문구를 유지하다가 리스크 적용 시에만 재작성한다. **`confidence_level`은 LLM이 쓴 `confidence_level` 문자열을 버리고 LLM 점수(`sentiment_score/100`)로 다시 계산한 高/中/低로 항상 대체된다**(점수 ≥75 高, ≥45 中, 그 미만 低). 따라서 데이터 품질 상한 프롬프트("quote/daily_bars/technical이 stale이면 `confidence_level`은 高 금지")의 효과는 이 단계에서 점수가 75 이상이면 무효가 될 수 있다. (이후 파이프라인의 `phase_decision_guardrail`이 `core_degraded`일 때 高→中으로 다시 낮춘다.) `_finalize...`의 호출처는 `_resolve_dashboard_payload`(`:1335`)와 `_resolve_final_output`의 `parse_dashboard=False` 분기에서 `final_dashboard`가 dict일 때(`:1302`) 두 곳이다. 이 함수 이후 `pipeline.py:2272-2275`가 `confidence_level`을 받아 `result.confidence_level`에 넣는다.
- 조사 범위: `src/agent/orchestrator.py:1250-1662`, `:1664-2200`(대입 grep `sentiment_score|decision_type|operation_advice|confidence_level|\["action"\]`), `src/agent/agents/decision_agent.py:260-300`, `src/agent/dashboard_payload.py`, `src/agent/protocols.py:104-110`, `src/core/pipeline.py:2265-2280`.

#### R1-Q10 답변
- 결론: **없음 확정**. 저장소에는 `LLMDeliberationMediator`, `StrategySelfReviewMediator`, `MultiRoundDeliberationMediator`를 **인스턴스화하거나 설정으로 선택하는 코드가 없다**. 정의와 지연 export(`skills/__init__.py`), 테스트(`tests/test_strategy_deliberation.py`)와 문서(`docs/multi-strategy-contract.md`)에서만 나온다. 설정 키(`deliberation|mediator`)도 없다. 실제 런타임에서는 두 곳 모두 인자 없이 `StrategySynthesizer()`를 만들어 **결정론적 `DeliberationMediator`(`mediator_v0`)** 만 쓴다. 1차 보고서의 "LLM 중재자는 정의만 있고 기본 경로에 연결되지 않는다"는 **맞고**, `next.md`의 "켜는 설정이 있는지" 미확인은 "없다"로 닫을 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/skills/synthesis.py:203-210` | `StrategySynthesizer.__init__` | `deliberation_mediator: Optional[Any] = None` / `self.deliberation_mediator = deliberation_mediator or DeliberationMediator()` | 코드 확인 |
  | `src/agent/skills/engine.py:191` | `StrategyEngine` | `synthesis = StrategySynthesizer().synthesize(` (인자 없음) | 코드 확인 |
  | `src/agent/skills/aggregator.py:75` | `SkillAggregator` | `synthesis = StrategySynthesizer().synthesize(` (인자 없음) | 코드 확인 |
  | `src/agent/skills/__init__.py:35-37`, `:70-81` | 지연 export | `"LLMDeliberationMediator"`, `"StrategySelfReviewMediator"`, `"MultiRoundDeliberationMediator"`를 `__getattr__`로 import해 돌려줄 뿐 인스턴스화하지 않음 | 코드 확인 |
  | `src/agent/skills/deliberation.py:284`, `:563`, `:696` | 클래스 정의 | 세 클래스는 생성자에 호출 가능한 객체(`completion` 등)를 받는 형태 — 이를 주입하는 비테스트 코드가 없다 | 코드 확인 |
  | `docs/multi-strategy-contract.md:245`, `:262`, `:299` | 문서 | `llm_mediator_v1 是 StrategyDeliberation 的可注入增强模式，不是默认运行时行为`(주입 가능한 강화 모드이며 기본 런타임 동작이 아니다), `self_review_v2 ... 不是默认运行时行为`, `multi_round_v4 ... 不是默认运行时行为`; `:258` `也不新增配置项`(설정 항목도 추가하지 않는다) | 코드 확인 |

- 동작 설명: 두 호출처(`StrategyEngine`은 `orchestrator.py:181`에서 생성, `SkillAggregator`는 `orchestrator.py:1048-1049`의 specialist 합의 단계)가 인자 없는 `StrategySynthesizer()`를 쓰므로 `deliberation_mediator`는 항상 `DeliberationMediator()`(`mode="mediator_v0"`, 규칙 기반 1라운드, `deliberation.py:89-147`)다. 선택 분기·설정·환경변수 경로가 없어서 사용자가 LLM/자가 검토/다중 라운드 중재자를 켤 방법은 코드 수정(생성자에 객체 주입)뿐이다. 보고서 `03-decision.md` 4-2의 서술과 일치한다.
- 조사 범위: grep `LLMDeliberationMediator|MultiRoundDeliberationMediator|StrategySelfReviewMediator|deliberation_mediator|StrategySynthesizer\(|DeliberationMediator\(`(`src/`, `api/`, `bot/`, `main.py`, `tests/`), 설정 grep `deliberat|mediator`(대소문자 무시; `src/`, `api/`, `bot/`, `main.py`, `server.py`, `webui.py`, `.env.example`, `docs/`, `docker/`, `apps/*/src`, `scripts/`, `evals/`, `strategies/`, `templates/`, `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`) — 그 밖의 `deliberately` 단어 매치는 무관, `src/config.py`에 해당 키 없음.

#### R1-Q11 답변
- 결론: **없음 확정**(레거시 경로의 프롬프트·후처리 범위). 레거시 시스템 프롬프트(`analyzer.py:1949-2134`), 유저 프롬프트(`_format_prompt`, `:4313-5093`), `CORE_TRADING_SKILL_POLICY_ZH`에는 `系统评分`/`系统信号`을 LLM의 `sentiment_score`와 **어떻게 관계 지을지 정하는 지시 문장이 없다**. 레거시 후처리 코드에는 두 점수를 비교하거나 한쪽으로 보정하는 곳도 없다. 코드 점수는 유저 프롬프트 표에 `系统评分 | {score}/100`로 **값만 제공**된다. **단, Agent 경로에서는 코드 점수가 직접 대체값이 된다**: LLM 점수가 없으면 `sentiment_score = signal_score`이고, 대시보드가 없으면 `signal_score`·`buy_signal`로 점수·advice·`decision_type`을 채운다. 따라서 "참고값일 뿐"(`00-overview.md` 핵심 발견 2)은 레거시에 한정되며, **Agent 경로 서술에는 보정이 필요하다**.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/analyzer.py:4780-4791` | `_format_prompt()` 레거시 기본 템플릿 | `### 趋势分析预判（基于交易理念）` / `\| 系统信号 \| {trend.get('buy_signal', unknown_text)} \| \|` / `\| 系统评分 \| {trend.get('signal_score', 0)}/100 \| \|` / `#### 系统分析理由` (추세 분석 예비 판단(거래 이념 기반) / 시스템 신호·시스템 점수 / 시스템 분석 이유) — 판정란이 비어 있고 사용 지시 없음 | 코드 확인 |
  | `src/analyzer.py:4812-4823` | 스킬 템플릿 | `### 技术与结构分析（供激活技能判断参考）`(기술·구조 분석, 활성 스킬 판단 참고용) / `\| 系统评分 \| {trend.get('signal_score', 0)}/100 \| \|` | 코드 확인 |
  | `src/analyzer.py:4747`, `:4762` | 영어 템플릿 | `Technical and Structure Analysis (reference for the active skills)` / `\| System Score \| {trend.get('signal_score', 0)}/100 \| \|` | 코드 확인 |
  | `src/analyzer.py:2087-2127` | 시스템 프롬프트 | `## 评分标准`은 **LLM 자신의** 점수 기준(`强烈买入（80-100分）`: 다중 배열·乖离率<2% 등)이고, `不得仅因为单日涨跌或评分跨线就在“买入/卖出”之间剧烈切换。`(하루 등락이나 점수 경계 통과만으로 매수/매도 사이를 급변하지 말 것)의 "评分"도 LLM 점수를 가리킨다. 코드 점수에 대한 언급 없음 | 코드 확인 |
  | `src/agent/skills/defaults.py:26-67` | `CORE_TRADING_SKILL_POLICY_ZH` | 7개 항목(乖离率·多头排列·筹码·回踩·风险·估值·강한 추세)에 `评分|分数|score|系统|signal` 매치 0건 | 코드 확인 |
  | `src/analyzer.py:811-878` | `_sanitize_trend_analysis_for_prompt()` | `prompt_consistency_notes`는 추세 방향과 상충하는 이유 문구 제거와 안내만 하며 점수와 무관 | 코드 확인 |
  | `src/core/pipeline.py:1085-1098` | `_enhance_context()` | `'signal_score': trend_result.signal_score`를 컨텍스트에 담음 (프롬프트 입력) | 코드 확인 |
  | `src/core/pipeline.py:2169-2180` | Agent 결과 변환 | `if self._is_agent_field_missing(raw_score, scalar=True): fallback_score = self._trend_score_fallback(trend_result); if fallback_score is not None: result.sentiment_score = fallback_score` | 코드 확인 |
  | `src/core/pipeline.py:2300`, `:2615-2672` | `_apply_trend_fallback()` | 대시보드 없음 → `result.sentiment_score = numeric_score if numeric_score > 0 else 50`(`:2630`), `operation_advice`=신호 라벨, `decision_type`=`buy_signal` 매핑(`signal_to_decision`) | 코드 확인 |
  | `src/core/pipeline.py:657` | 로그 | `f"买入信号={trend_result.buy_signal.value}, 评分={trend_result.signal_score}"` — 비교 없음 | 코드 확인 |
  | `src/agent/tools/analysis_tools.py:84` | Agent 도구 | `"signal_score": result.signal_score` 반환 (참고용 데이터) | 코드 확인 |

- 동작 설명: 코드 점수(`stock_analyzer.py:730`의 `result.signal_score`)는 (a) 프롬프트 표 값, (b) 로그, (c) Agent 도구 반환값, (d) Agent 폴백 대체값으로만 쓰인다. 후처리 가드레일(`analyzer.py:1043`~)은 `trend_result`에서 가격 수준(`current_price`, `support_levels`, `resistance_levels`)만 읽고 `signal_score`는 읽지 않는다. LLM 점수와 코드 점수를 비교하는 `if`는 어디에도 없다.
- 조사 범위: grep `系统评分|系统信号|signal_score|trend_score|系统打分|量化评分|代码评分`(`src/`, `api/`, `bot/`, `main.py`, `data_provider/`, `strategies/`, `templates/`), `src/analyzer.py`(시스템 프롬프트: 레거시 `:1949-2134`, 스킬 기본 `:2275-2313` 이하 동일 구조; grep `系统评分|系统信号`는 `:4789-4790`, `:4821-4822`와 영어판 `:4762`만 매치; `_format_prompt` `:4313-5093`에서 `系统|评分|score|信号` 검색), `src/agent/skills/defaults.py` 전체, `src/core/pipeline.py`(1085-1098, 2165-2215, 2426-2440, 2615-2675).

#### R1-Q12 답변
- 결론: **없음 확정**. `search_comprehensive_intel`과 그 하위 필터·랭킹 단계(`_filter_news_response`, `_normalize_and_limit_response`, `_rank_news_response`, `_filter_ranked_news_for_context`, `_limit_search_response`)에는 **URL이나 제목으로 중복 결과를 제거하는 코드가 없다**. 차원 안에서도 차원 간에도 적용되지 않는다. 각 차원은 서로 다른 검색 질의로 한 엔진을 호출해 결과를 `results[dim['name']]`에 따로 담을 뿐이다. 중복 제거는 두 곳에만 있고 둘 다 이 경로와 무관하다. (a) DB 저장 시 `url` 기준 upsert(`storage.py:2399-2425`, LLM 입력이 아님), (b) 로컬 인텔 풀 로딩 내부의 `seen_urls`(`pipeline.py:3033-3047`, 검색 결과와의 교차 중복은 제거하지 않음). `04-research.md` 5-4의 `미확인`은 "없음"으로 확정할 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/search_service.py:4546-4620` | `search_comprehensive_intel()` 루프 | 차원마다 `provider.search(...)` → `_filter_news_response` 또는 `_normalize_and_limit_response` → `_rank_news_response` → `_filter_ranked_news_for_context` → `_limit_search_response` → `results[dim['name']] = filtered_response` | 코드 확인 |
  | `src/search_service.py:3687-3775` | `_filter_news_response()` | 게시일 기준 최신성 필터(`published < earliest`, `published > latest`) + 최대 개수 절단. URL/제목 비교 없음 | 코드 확인 |
  | `src/search_service.py:3777-3814` | `_normalize_and_limit_response()` | `for item in response.results[:max_results]:` 날짜 정규화만 | 코드 확인 |
  | `src/search_service.py:3364-3426` | `_rank_news_response()` | 관련도 점수화 후 `sorted(..., key=sort_key)`, `ranked_results[:max_results]` — 정렬과 절단만 | 코드 확인 |
  | `src/search_service.py:3428-3485` | `_filter_ranked_news_for_context()` | 저품질·성인 스팸·무관련(점수 0) 제거만 (`dropped_low_quality`, `dropped_adult_spam`, `dropped_zero_relevance`) | 코드 확인 |
  | `src/search_service.py:3816-3836` | `_limit_search_response()` | `limited_results = response.results[:max_results]` (차원당 `target_per_dimension = 3`, `:4526`) | 코드 확인 |
  | `src/search_service.py:4638-4690` | `format_intel_report()` | 차원별 `resp.results[:4]`를 순서대로 출력, 차원 간 비교 없음 | 코드 확인 |
  | `src/core/pipeline.py:701-728` | 호출처 | `intel_results = self.search_service.search_comprehensive_intel(...)` → `news_context = self.search_service.format_intel_report(...)`, 이어서 `news_context + "\n\n" + persisted_intelligence_context`(`:750-755`) 연결, 중복 제거 없음 | 코드 확인 |
  | `src/storage.py:2399-2425` | `save_news_intel()` | `existing = session.execute(select(NewsIntel).where(NewsIntel.url == url_key))...` 기존이면 갱신 — DB 저장용 | 코드 확인 |
  | `src/search_service.py:4766-4789` | `search_stock_price_fallback()`의 `seen_urls` | 주가 폴백 검색 전용, 뉴스 경로와 무관 | 코드 확인 |

- 동작 설명: 차원 질의(`latest_news`, `market_analysis`, `risk_check`, `announcements`, `earnings`, `industry` 중 `max_searches=5`개)가 서로 다르고, 엔진은 사용 가능한 목록에서 돌려 쓴다(`provider_index % len(available_providers)`). 같은 기사가 두 차원에 잡히면 두 번 다 그대로 `news_context`에 들어가고 LLM 입력에서 반복된다. 차원 내부 중복도 제거되지 않지만, 개수는 차원당 최대 3건(`:4526`)으로 제한된다.
- 조사 범위: `src/search_service.py` 전체 grep `dedup|seen|unique|set\(\)|duplicate|_url_key|normalize_url|canonical|drop_duplicates`(매치는 `:832-853` rich snippet 확장 문구, `:2821-2913` 검색어 변형 `_append_unique`, `:3282-3287` 식별어 점수 중복 방지, `:4766-4789` 가격 폴백뿐), 함수별 정독(`:3364-3500`, `:3687-3836`, `:4384-4720`), `src/core/pipeline.py:675-780`, `:3019-3070`, `src/storage.py:2380-2430`, `src/` 전체 grep `dedup|seen_urls|seen_titles|unique_news|drop_duplicates`(알림 노이즈 `notification_noise.py`는 무관).

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `analyzer.py:1093-1096`(강등 분기 두 조건), `:1322-1337`(`not_supported`→`"unavailable"`), `base.py:4281-4286`(kr→offshore), `:3865-3866`(hk 외 yfinance), `:3963`(`"capital_flow": {}` 초기값), `:4062`·`:4070-4075`(`not_supported` 블록)을 직접 열어 인용·라인 일치 확인. `yfinance_fundamental_adapter.py`의 `capital_flow` grep 0건도 재현. 생성 함수, 키 삽입 위치, 호출처(`pipeline.py:906`), 키가 빠지는 경로 없음(실패·비활성 경로 포함)까지 완료 조건 모두 충족 |
| R1-Q2 | 해소 | `factory.py:363`, `:366-376`(필터 없이 `ALL_BACKTEST_TOOLS` 등록), `registry.py:243-245`(`to_openai_tools` 필터 없음) 확인. `executor.py:71-385`에서 `backtest`(대소문자 무시) 0건 재현. 도구 목록 구성 코드·필터 조건·프롬프트 grep 결과 모두 제시됨 |
| R1-Q3 | 해소 | `config.py:1984`, `:1992`(기본 `false`/`[]`), `pipeline.py:561-571`(세 활성 조건) 원문 일치 확인. `00-daily-analysis.yml`의 `AGENT` grep 결과가 `:74`, `:81` 두 줄뿐인 것도 재현. 로컬 `--schedule`이 사용자 `.env`에 따라 달라지는 부분은 사용자 설정 의존이며 갈림 지점(`config.py:1984`, `:1992`)이 명시돼 있어 정적 부분은 완결됨. 보고서 정정 필요(`01-data.md` 범례) |
| R1-Q4 | 해소 | `pipeline.py:2753-2762`(설정·거래일 가드, 시각 미확인), `:2779-2781`(덮어쓰기), `:2796-2797`(가상 행 추가), `:651-655`(호출처→`trend_analyzer.analyze`) 확인. 분기 조건·동작·호출처 모두 충족. 시세 값 자체(장전 시세가 전일 종가인지)는 외부 API 응답이지만 분기 구조는 코드로 확정됨 |
| R1-Q5 | 없음 확정 | `00-daily-analysis.yml:552-560` 업로드 경로가 `reports/`, `logs/`뿐임을 확인. 워크플로 전체 grep `stock_analysis\.db|DATABASE_PATH|git commit|git push|actions/cache` 재실행 결과 `desktop-release.yml:185`(데스크톱 빌드 캐시) 1건뿐. 파일 목록·패턴·`.gitignore`·호출 스크립트까지 조사 범위 충분 |
| R1-Q6 | 해소 | `analysis.py:599-611`(동기 → `AnalysisService.analyze_stock`, `skills` 전달), `analysis_service.py:140-163`(`analysis_skills=skills`, `process_single_stock`) 확인. 세 가드레일의 비테스트 호출처 grep을 재실행해 `pipeline.py:906/907/916`, `:1718/1738/1766` 6곳뿐임을 재현. 엔드포인트→파이프라인 호출 연쇄와 가드레일 지점 충족 |
| R1-Q7 | 해소 | `trading_calendar.py:393-416`(`is_session`→`NON_TRADING`, `market_now < session_open`→`PREMARKET`), `phase_decision_guardrail.py:18`, `:170-186`(보수 단계에서 `immediate_action` 교체·신뢰도 高→低), `00-daily-analysis.yml:6`(cron) 확인. 세션 개장 시각은 `exchange_calendars` 라이브러리 값이지만 XNYS 정규장 09:30 ET는 고정 사실이고 UTC 10:00 = ET 05:00/06:00이므로 결론이 갈리지 않음 |
| R1-Q8 | 재질문 | (1)~(5) 강등 후 (9)가 성립하지 않는다는 부분은 `pipeline.py:2320-2339`, `decision_scale.py:158-171`, `decision_signal_extractor.py:327-345`, `daily_market_context_guardrail.py:79-91`, `:280-285`를 열어 확인함. 그러나 (8) 예외의 성립 조건이 불완전함: `analyzer.py:5451-5458`에서 LLM JSON의 최상위 `guardrail_reason`/`downgrade_reason`이 `dashboard.decision_score_calibration.guardrail_reason`에 `setdefault`로 들어간다(시스템 프롬프트 `:1969`가 "점수 구간과 최종 action이 다르면 채우라"고 지시). 답변은 (8) 이후 사유가 "None"이라고 했으나 LLM이 이 필드를 채우면 (9)가 막힌다. 또 (8)이 (1)~(5) 뒤에 실행되므로 (8)만 단독 발동하는 전제(자금흐름 사용 가능 등)도 정리되지 않음 → R2-Q1 |
| R1-Q9 | 해소 | `orchestrator.py:1401`, `:1646-1650`(무조건 대입, `confidence_level` 재계산), `:2142-2147`(`_confidence_label`), `decision_agent.py:271-282`(`confidence = score/100`) 확인. `orchestrator.py`의 `["action"]` 대입 grep 0건 재현. 다섯 필드 대입 위치·조건·조사 범위 충족. 보고서 정정 필요(`confidence_level` 항상 덮어씀). 단, 이 함수가 건드리지 않는 LLM `action`이 이후 어디로 흐르는지는 새 의문 → R2-Q2 |
| R1-Q10 | 없음 확정 | 인스턴스화 grep을 재실행해 `StrategySynthesizer(`가 `aggregator.py:75`, `engine.py:191` 두 곳(둘 다 인자 없음)뿐이고 세 LLM 중재자 클래스의 생성 호출은 `src/api/bot/main.py`에 0건임을 확인. `synthesis.py:203-210` 기본값 `DeliberationMediator()` 일치. 설정 키 grep 범위(`.env.example`, `docs/`, `config.py` 포함) 충분 |
| R1-Q11 | 없음 확정 | `analyzer.py:4789-4790`(값만 제공, 지시 없음), `pipeline.py:2169-2180`·`:2630`(Agent 폴백 대체) 확인. grep 패턴(`系统评分|系统信号|signal_score|trend_score` 등)과 대상 파일 목록이 제시돼 레거시 범위의 "지시·비교 코드 없음"은 확정. Agent 경로의 폴백 대체는 보고서 정정 필요 |
| R1-Q12 | 없음 확정 | `search_service.py` `dedup|seen|duplicate` grep 재실행: `:832-853`(스니펫 확장), `:3271-3287`(식별어), `:4742`(`search_stock_price_fallback` `:4726` 내부)뿐이며 뉴스 경로와 무관함을 확인. `_limit_search_response`(`:3816-3836`)가 절단만 하고 `target_per_dimension = 3`(`:4526`) 일치. 함수 범위·패턴 충분 |

---

## Round 2

### 질문 (질문자)

#### R2-Q1. 대시장 가드레일 (8) 뒤에 (9)가 `watch`를 `reduce`/`sell`로 바꾸는 조건의 완결 (R1-Q8 재질문)
- GUIDE 항목: Q4-5
- 왜 묻는가: R1-Q8 답변은 "(8)은 `guardrail_reason`을 설정하지 않으므로 원점수가 40 미만이면 (9)가 `watch`→`reduce`/`sell`로 바꾼다"고 결론냈다. 그런데 `src/analyzer.py:5451-5458`은 LLM 응답 JSON의 최상위 `guardrail_reason`(또는 `downgrade_reason`)을 `dashboard["decision_score_calibration"]["guardrail_reason"]`에 `setdefault`로 넣고, 레거시 시스템 프롬프트(`analyzer.py:1969`)는 "分数区间与最终 action 不一致时填写降级/升级原因"(점수 구간과 최종 action이 다르면 사유를 채우라)고 지시한다. 즉 답변이 말한 "LLM이 buy인데 점수 <40" 상황은 바로 LLM이 이 필드를 채우도록 요구받는 상황이며, 채워지면 `_extract_guardrail_reason`(`decision_signal_extractor.py:335-339`)이 사유를 찾아 (9)가 막힌다. 답변은 이 경로를 다루지 않았다. 또 (8)은 (1)~(5) 뒤에 실행되므로, (1)~(5)가 먼저 발동하면(예: 한국 종목은 R1-Q1에 따라 buy가 항상 (1)로 강등) (8)의 단독 발동 자체가 일어나지 않는다. 결국 "(8) 뒤 되돌림"이 실제로 성립하는 입력 조건이 확정되지 않았다.
- 질문: 레거시 경로와 Agent 경로 각각에서, (8) `apply_daily_market_context_guardrail`이 buy를 `hold`/`"观望"`으로 바꾼 뒤 `_refresh_decision_action_for_final_result`의 (9)가 `reduce`/`sell`로 바꾸려면 어떤 조건이 **모두** 성립해야 하는가? 특히 (a) LLM 응답의 `guardrail_reason`/`downgrade_reason`이 `decision_score_calibration.guardrail_reason`에 들어가는 경로가 Agent 경로(대시보드 파싱, `orchestrator.py`·`pipeline.py`의 Agent 결과 변환)에도 있는가, (b) (1)~(5)가 먼저 buy를 강등하지 않아야 한다는 전제를 만족하는 조건(자금흐름 상태, 구조 조건)은 무엇인가?
- 답변 완료 조건: ① `analyzer.py:5451-5458` 경로가 레거시 결과에 적용되는 호출 체인(`파일:라인`). ② Agent 경로에서 같은 필드가 calibration으로 들어가는 코드가 있으면 `파일:라인`과 원문, 없으면 grep 패턴(`guardrail_reason|downgrade_reason|decision_score_calibration`)과 조사 범위. ③ (8)이 발동하는 시점에 `decision_type == "buy"`가 남아 있으려면 (1)~(5) 각각이 발동하지 않는 조건 원문(`analyzer.py` `파일:라인`). ④ 위를 종합한 "되돌림 성립 조건" 목록. 하나라도 정적으로 정해지지 않으면(LLM 출력 의존) 그 갈림 지점을 `파일:라인`으로 명시.

#### R2-Q2. LLM 대시보드의 `action` 필드가 최종 `result.action`까지 그대로 남는 경우
- GUIDE 항목: Q4-5
- 왜 묻는가: R1-Q9 답변은 `_finalize_dashboard_payload`가 `action`을 쓰지 않아 "LLM 페이로드의 `action`이 그대로 통과"한다고만 했다. 그런데 `pipeline.py:2314-2317`은 대시보드의 `action`을 `explicit_action`으로 `populate_decision_action_fields`에 넘기고, `build_action_fields`(`decision_action.py:383-387`)는 `explicit_action`이 있으면 `operation_advice`보다 우선한다. `_refresh_decision_action_for_final_result`(`pipeline.py:2331-2333`)는 가드레일 전후 `operation_advice` 문자열이 다를 때만 `result.action`을 지운다. 따라서 Agent multi 경로에서 `_apply_risk_override`가 `decision_type`을 바꾸고 `_finalize_dashboard_payload`가 `operation_advice`를 재작성한 경우(이 변경은 파이프라인 가드레일 "이전"에 일어나므로 `previous_operation_advice`와 비교 대상이 아님), LLM이 쓴 `action`(예: `buy`)이 `decision_type`(예: `sell`/`hold`)과 어긋난 채 최종 `result.action`이 될 수 있는지가 확정되지 않았다. `03-decision.md` 4-5의 "최종 결정 필드" 서술 범위에 직결된다.
- 질문: Agent 경로(single·multi)에서 `result.action`의 최초 값은 어디서 정해지며, 리스크 오버라이드(`orchestrator.py:1927`)나 `_finalize_dashboard_payload`의 advice 재작성(`:1467-1481`)으로 `decision_type`/`operation_advice`가 바뀌었을 때 LLM이 쓴 `action`이 최종 `result.action`으로 남는 경로가 있는가? 레거시 경로에서도 LLM JSON의 `action`이 같은 방식으로 우선되는가?
- 답변 완료 조건: ① Agent 결과 변환에서 `result.action`을 처음 설정하는 `파일:라인`(`pipeline.py:2314-2317` 및 `populate_decision_action_fields` `analyzer.py:1900-1925` 본문). ② `explicit_action` 우선 규칙 원문(`decision_action.py`). ③ 가드레일 단계에서 `result.action`이 초기화되는 조건(`pipeline.py:2331-2333`)과, 리스크 오버라이드 후 advice가 가드레일에서 다시 바뀌지 않는 경우의 최종값. ④ 레거시 파싱(`analyzer.py:5522`)에서 `explicit_action` 출처. 어긋남이 가능하면 그 조건, 불가능하면 막는 코드(예: `decision_type`과 `action`의 정합 검사) `파일:라인`. 실제로 LLM이 어떤 `action`을 쓰는지는 LLM 출력 의존이므로, 그 부분만 정적 확인 불가로 남길 수 있다.

#### R2-Q3. API 응답·리포트의 `action`이 파이프라인 최종 `result.action`과 달라지는 조건
- GUIDE 항목: Q4-5
- 왜 묻는가: R1-Q8 답변의 "보충 발견"은 `AnalysisService._build_analysis_response`(`analysis_service.py:206-216`)가 `guardrail_reason=getattr(result, "guardrail_reason", None)`(항상 None)과 `align_with_score=True`로 `build_action_fields`를 다시 호출해, API 동기 응답의 `summary.action`이 파이프라인 `result.action`과 다를 수 있다고 했으나 구체 조건을 추적하지 않았다. 확인한 바로는 `explicit_action=result.action`이 먼저 쓰이므로, 파이프라인이 `hold`/`watch`로 남긴 결과(예: 한국 종목에서 LLM이 hold+점수 65, `decision_stability.reason`으로만 (9)가 막힌 경우)가 API에서는 점수 구간 `buy`로 바뀔 수 있다. 이 경우 사용자가 보는 최종 판단이 출력 경로마다 달라진다.
- 질문: `_build_analysis_response`의 `summary.action`이 파이프라인의 `result.action`과 달라지는 입력 조건은 정확히 무엇이며, 같은 재계산(`guardrail_reason` 없이 `align_with_score=True`)을 하는 출력 경로(비동기 작업 결과, 이력 조회 `history_service.py`, 알림/리포트 렌더러)는 어디인가?
- 답변 완료 조건: ① `analysis_service.py:206-216` 호출 인자 원문과, 이 응답이 쓰이는 엔드포인트(동기·비동기) `파일:라인`. ② `build_action_fields(..., align_with_score=True)`를 `guardrail_reason` 없이(또는 `result.guardrail_reason`으로) 호출하는 저장소 내 모든 비테스트 호출처 grep 결과(`build_action_fields\(|populate_decision_action_fields\(`)와 각 호출의 `guardrail_reason`·`align_with_score` 인자. ③ 파이프라인 `result.action`이 `hold`/`watch`이면서 점수가 buy/reduce/sell 구간에 남는 구체 조건(R1-Q8 답변의 (6)/자금흐름 불가 비-buy 케이스 포함)을 `파일:라인`으로. ④ `history_service.py:1106`의 `setattr(... "guardrail_reason" ...)`이 이력 조회 응답에서 이 차이를 없애는지 여부.

### 답변 (답변자)

#### R2-Q1 답변
- 결론: **정적 확인 불가** (조건 목록은 코드로 확정, 최종 성립 여부는 LLM 출력 한 곳에서 갈림). (8) 뒤 (9)가 `watch`를 `reduce`/`sell`로 바꾸려면 아래 D1~D6이 **모두** 성립해야 한다. 갈림 지점은 레거시에서 LLM이 최상위 `guardrail_reason`/`downgrade_reason`을 채우는지(`src/analyzer.py:5452-5458`)이다. 채우면 (9)가 막혀 `watch`가 유지되고, 비우면 `reduce`/`sell`로 뒤집힌다. Agent 경로는 이 필드를 요구하는 프롬프트도, 읽는 코드도 없어서 사실상 "비어 있음" 쪽이다. **R1-Q8 답변 정정**: "(8) 이후 사유는 None"이라고 한 것은 레거시에서 LLM 출력에 따라 틀릴 수 있었다. 또 (8) 단독 발동은 자금흐름이 사용 가능한 종목(사실상 A주)에서만 가능하다는 전제와, 한국어 리포트에서는 `action`이 `None`이 되어 뒤집힘이 없다는 점이 R1-Q8 답변에 빠져 있었다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/pipeline.py:843`, `src/analyzer.py:3989`, `:4234`, `:5427`, `:5452-5458` | 레거시 호출 체인 | `result = self.analyzer.analyze(` → `def analyze(` → `result = self._parse_response(response_text, code, name)` → `guardrail_reason = data.get("guardrail_reason") or data.get("downgrade_reason")` / `if guardrail_reason and isinstance(dashboard, dict):` / `score_calibration.setdefault("guardrail_reason", str(guardrail_reason).strip())`. `dashboard`가 dict가 아니면 기록하지 않는다 | 코드 확인 |
  | `src/analyzer.py:1949`, `:1969`, `:2136`, `:2157`, `:2337` | 레거시 시스템 프롬프트 3종(`LEGACY_DEFAULT_SYSTEM_PROMPT`, `SYSTEM_PROMPT`, EN 템플릿) | `"guardrail_reason": "当分数区间与最终 action 不一致时填写降级/升级原因，否则留空"` (분수 구간과 최종 action이 다르면 강등/상향 사유를 채우고, 아니면 비워 둠). EN: `"Reason for the downgrade/upgrade when the score band and the final action differ; otherwise leave empty"` | 코드 확인 |
  | `src/schemas/decision_scale.py:43` | `CANONICAL_DECISION_SCALE_PROMPT_ZH` | `若 score >= 60 但最终 action 是 hold/watch，或 score < 40 但最终 action 是 hold/watch，必须在 guardrail_reason 或 dashboard.decision_stability.reason 中说明降级原因` (hold/watch인데 점수가 극단이면 사유를 반드시 쓰라) | 코드 확인 |
  | `src/analyzer.py:1396-1416`, `:1419-1437` | `_record_decision_score_calibration()` | `dashboard["decision_score_calibration"] = calibration` — LLM이 넣은 calibration 딕셔너리를 **통째로 교체**한다. (1)~(5)가 발동한 경우에만 호출 | 코드 확인 |
  | `src/agent/` 전체, `src/core/pipeline.py:2133-2317` | Agent 경로 | `guardrail_reason\|downgrade_reason\|decision_score_calibration\|decision_stability` grep 0건(`src/agent`, `src/core`). `decision_agent.py:101-111`의 필수 키는 `stock_name, sentiment_score, trend_prediction, operation_advice, decision_type, confidence_level, dashboard, analysis_summary, key_points, risk_warning`이고, `executor.py:107-117` 스키마에도 `guardrail_reason`·`action` 키가 없다. `CANONICAL_DECISION_SCALE_PROMPT_*`는 `analyzer.py`에서만 import된다(grep) | 코드 확인 |
  | `src/core/pipeline.py:2309-2317` | Agent 변환 끝 | `result.dashboard = nested_dashboard or dash` 이후 `populate_decision_action_fields(result, explicit_action=explicit_action)`. 최상위 `dash["guardrail_reason"]`를 읽는 코드가 없다 | 코드 확인 |
  | `src/analyzer.py:1094-1105` | (1) 자금흐름 불가 강등 | `if flow_bias == "unavailable": if isinstance(fundamental_context, dict) and "capital_flow" in fundamental_context: if decision_type == "buy" or advice_decision_type == "buy": _downgrade_buy_without_capital_flow(...)` | 코드 확인 |
  | `src/analyzer.py:1135-1168` | (2)(3)(4) 매수 구조 강등 | `if decision_type == "buy": if near_resistance and flow_bias != "inflow":` → `elif flow_bias == "outflow" and not breakout:` → `elif mid_range and flow_bias == "neutral":` 각각 `_downgrade_to_structural_hold(...)`. 앞에 `if current_price is None: return`(`:1116-1117`) | 코드 확인 |
  | `src/analyzer.py:1169-1191`, `:1192-1213` | (5) 매도 구조 강등, (6) hold 문구 | `elif decision_type == "sell":` … / `elif decision_type == "hold":` `change_pct < 0 and near_support and flow_bias != "outflow"` 또는 `mid_range and flow_bias == "neutral"` → `_set_structural_hold_wording(...)`(`calibrate_score=False`, 점수 클램프 없음, 사유는 `stability.reason`에 기록) | 코드 확인 |
  | `src/analyzer.py:1322-1357`, `:586-598` | `_capital_flow_bias_with_status()` | `unavailable` 조건: `fundamental_context`가 dict 아님, `capital_flow` 블록 없음/dict 아님, `status`가 `_CAPITAL_FLOW_UNAVAILABLE_STATUS`(`not_supported`, `unavailable`, `missing` 등) 또는 `"not supported"`, `stock_flow`가 비었음, `main_net_inflow`/`inflow_5d`/`inflow_10d`가 전부 None | 코드 확인 |
  | `src/core/pipeline.py:579-617`, `:1217-1236` | `fundamental_context`는 항상 dict | 지수는 `build_not_supported_fundamental_context`, 예외는 `build_failed_fundamental_context`, `_attach_belong_boards_to_fundamental_context`는 dict가 아니면 `build_failed_...`를 만든다 → `capital_flow` 키는 항상 존재(R1-Q1). `"capital_flow" in fundamental_context` 거짓 경로가 없으므로 (1)은 `unavailable`이면 반드시 발동 | 코드 확인 |
  | `data_provider/base.py:4481-4507`, `:3962-4075`, `:4281-4286` | `capital_flow` 값의 출처 | ETF는 `"not_supported"`(`:4481`). A주 비-ETF는 `get_capital_flow_context`(`:4503`)로 실제 조회. us/hk/jp/kr/tw는 `_build_offshore_fundamental_context`이고 `capital_flow`는 Futu가 채울 때(`:4057-4066`, HK + 엔드포인트 설정)만 데이터, 아니면 `"not_supported"`(`:4070-4075`) | 코드 확인 |
  | `src/daily_market_context_guardrail.py:62-91` | (8) | `if result is None or not _is_conservative_context(daily_market_context): return []` / `if not _has_aggressive_buy_signal(result, language=language): return []` / `if ... decision_type ... == "buy": result.decision_type = "hold"` / `result.operation_advice = softened_advice` / `result.sentiment_score = _cap_conservative_sentiment_score(...)`. `calibration`·`decision_stability`·`guardrail_reason`은 쓰지 않는다 | 코드 확인 |
  | `src/daily_market_context_guardrail.py:201-215`, `:218-231`, `:278-285` | 발동 조건·점수 상한 | `_is_conservative_context`: `risk_tags`가 `{"high_risk","market_cooling","conservative","low_position_cap"}`와 겹침, `position_cap` 비어 있지 않음, 또는 `summary`에 `("退潮","观望","高风险","谨慎","保守","仓位上限","仓位不超过","轻仓")`/영·한 대응어. `_has_aggressive_buy_signal`: `decision_type == "buy"`면 마커가 부정 없이 있거나 마커가 아예 없으면 True(부정된 마커만 있으면 False), 그 외 타입이면 advice에 부정되지 않은 마커(`"立即买入","建议买入","分批买入","追高","加仓"` 등)가 있어야 True. 점수 `min(52, max(0, score))`, 변환 실패 시 52 | 코드 확인 |
  | `src/report_language.py:72`, `src/schemas/decision_action.py:38`, `:90-95`, `:303-361` | `softened_advice`와 action 변환 | `"watch": {"zh": "观望", "en": "Watch", "ko": "관망"}`. `normalize_decision_action("观望")`와 `("Watch")`는 `watch`. 한국어 `"관망"`은 `_ACTION_PHRASES["watch"]`(`"观望","等待","wait","watch"`)에 없어 `None` | 코드 확인 |
  | `src/core/pipeline.py:905-938`(레거시), `:1701-1790`(Agent), `:2320-2339` | `_refresh_decision_action_for_final_result()` | 레거시는 가드레일 3종 뒤 1회, Agent는 구조/단계/대시장 뒤 각 1회. `if previous_advice != current_advice: result.action = None; result.action_label = None` 이후 `resolve_decision_signal_action_fields(...)`. previous는 각 가드레일 **직전**의 `operation_advice` | 코드 확인 |
  | `src/services/decision_signal_extractor.py:300-360` | `_extract_guardrail_reason()` | 사유 후보 순서: `calibration.guardrail_reason` → `dashboard.decision_stability.reason`(`applied` 무시) → `result.guardrail_reason` → (충돌일 때) advice의 힌트 문장. 힌트 `_NEUTRAL_GUARDRAIL_HINTS`는 `"等待","待","需要确认","回踩","支撑","压力","风险","资金","突破","不追","不宜","缺少","缺少确认","未确认","wait","waiting","pending confirmation","lack confirmation","pullback","support","resistance","risk","flow"`. 소문자화한 `"观望"`, `"watch"`, `"관망"`에는 해당 없음 | 코드 확인 |
  | `src/analyzer.py:1718-1790` | `AnalysisResult` | 필드 목록에 `guardrail_reason`/`downgrade_reason` 없음. `guardrail_reason` grep은 `getattr(result, "guardrail_reason", None)`(`:1920`)뿐 | 코드 확인 |
  | `src/schemas/decision_scale.py:20-26`, `:158-171` | 구간·충돌 판정 | `(40,59) watch`, `(20,39) reduce`, `(0,19) sell`. `if str(guardrail_reason or "").strip(): return False` / `if normalized_action not in {"hold", "watch"}: return False` / `return score_action in {"buy", "reduce", "sell"}` | 코드 확인 |

- 동작 설명 (되돌림 성립 조건, 레거시와 Agent 공통 전제):
  1. **D1. (8)이 발동**: 대시장 문맥이 보수적(`:201-215`)이고, `_has_aggressive_buy_signal`이 참이다. 보통은 LLM `decision_type == "buy"`이다. 변형으로 `decision_type`이 buy가 아니어도 advice에 부정 없는 마커(예: `"回踩加仓"`)가 있으면 발동한다(이때 `result.decision_type`은 그대로, advice만 `"观望"`).
  2. **D2. (1)~(5)가 발동하지 않음**(a: 질문 (b)에 대한 답). 안 그러면 advice가 `"持有观察"`/`"震荡观望"`/`"洗盘观察"`(영·한 대응 문구)로 바뀌고 `decision_type="hold"`가 되어 (8)의 `_has_aggressive_buy_signal`이 거짓이 된다(그 문구들에 마커가 없다). 또 `calibration.guardrail_reason`과 점수 45~59 클램프가 생겨 (9)도 막힌다. `decision_type == "buy"`일 때 (1)~(5)가 모두 안 걸리는 조건은 다음과 같다.
     - 자금흐름이 **사용 가능**해야 한다. 즉 `capital_flow.status`가 불가 목록에 없고 `stock_flow`에 `main_net_inflow`/`inflow_5d`/`inflow_10d` 중 숫자가 하나 이상 있어야 한다(`:1322-1357`). `capital_flow` 키는 항상 있으므로(위 표) `unavailable`이면 (1)이 반드시 발동한다. 데이터가 실제로 채워지는 경로는 A주 비-ETF 비-지수와 Futu 엔드포인트가 설정된 HK뿐이다(`base.py:4057-4066`, `:4503`). 그래서 us/jp/kr/tw, 일반 HK, ETF, 지수에서는 (8) 단독 발동이 불가능하다.
     - `current_price`가 None이면 (2)~(5)가 모두 건너뛰어진다(`return`). 있으면 `flow_bias`별로 다음이어야 한다. `inflow`: (2)(3)(4) 모두 거짓이라 항상 통과. `outflow`: (2)는 `near_resistance`면 발동, (3)은 `not breakout`이면 발동하므로 `breakout`(`current_price > resistance*1.01`)이면서 `near_resistance`가 아니어야 통과. `neutral`: `near_resistance`가 아니고 `mid_range`(`support*1.03 < price < resistance*0.97`)도 아니어야 통과.
     - `stabilize_decision_with_structure`가 예외를 내면(`:1217-1218` `except Exception as exc:` → `logger.warning("[decision_stability] skipped: %s", exc)`) 강등이 건너뛰어진다.
     - 변형(`decision_type`이 hold + advice에 마커)은 hold 분기가 `_set_structural_hold_wording`(advice 교체)이나 `_set_decision_stability_unavailable`(`stability.reason` 기록, `:1384`)을 실행하지 않아야 한다. 후자가 실행되면 `stability.reason`이 사유로 잡혀 (9)가 막힌다.
  3. **D3. 원점수 s0가 0~39**. (8)이 점수를 `min(52, max(0, s0))`로만 낮추므로 s0가 40 이상이면 결과가 40~52이고 `watch` 구간이라 충돌이 없다. `sentiment_score`가 숫자가 아니면 52가 되어 충돌 없음. 이 상황은 LLM이 buy 결론에 40 미만 점수를 준 모순 출력이다. 코드에는 이를 막는 검사가 없다(레거시 파싱 `sentiment_score=int(data.get('sentiment_score', 50))` `:5482`, Agent는 `pipeline.py:2181`의 `self._safe_int(raw_score, 50)`로 그대로 사용).
  4. **D4. (8) 이후 `result.action`이 `hold`/`watch`**. 바뀐 advice(`"观望"`/`"Watch"`)가 직전 advice와 다르면 `action`이 `None`으로 지워지고 advice에서 `watch`로 재계산된다. **한국어 리포트에서는 `"관망"`이 `None`으로 변환**되어 충돌 판정에서 `action`이 `hold`/`watch`가 아니므로 뒤집힘이 없다(최종 `result.action = None`). LLM이 원래 advice를 정확히 `"观望"`으로 썼다면 `previous_advice == current_advice`라 `action`이 지워지지 않고 이전 값(LLM 명시 `action` 또는 advice에서 유도된 값)이 남는다. 이 경우 LLM이 `action`을 `buy`로 명시했다면 `buy`가 유지된다(R2-Q2 참고).
  5. **D5. 사유가 비어 있음** (여기가 갈림 지점이다).
     - **레거시, 경우 A(LLM이 최상위 `guardrail_reason` 또는 `downgrade_reason`을 채우고 `dashboard`가 dict)**: `:5458`이 `decision_score_calibration.guardrail_reason`에 넣고, (8)은 calibration을 건드리지 않으므로 `_extract_guardrail_reason`이 이를 읽어 (9)가 거짓이 된다. 최종은 `watch`이고 점수는 52 이하로 남는다. 프롬프트(`:1969`)가 "분수 구간과 최종 action이 다르면 채우라"고 하므로 buy+저점수 출력에서 LLM이 채울 가능성이 있으나, 채울지는 런타임 LLM 출력이다.
     - **레거시, 경우 B(LLM이 비우거나 생략하거나 `dashboard`가 dict가 아님)**: 후보 3개가 모두 비고, 힌트도 없어(`"观望"`/`"Watch"`에 힌트 없음) 사유는 `None`이다. (9)가 참이 되어 `watch`가 `reduce`(s0 20~39) 또는 `sell`(s0 0~19)로 바뀐다.
     - **Agent**: 위 표대로 프롬프트도 코드도 없으므로 정상적으로는 경우 B다. 예외는 LLM이 요청받지 않은 `dashboard.decision_score_calibration.guardrail_reason` 또는 `dashboard.decision_stability.reason`을 자발적으로 넣는 경우뿐이며, 이것도 LLM 출력 의존이다. Agent 최상위 `guardrail_reason`은 어디서도 읽지 않는다.
  6. **D6. `result.guardrail_reason`이 없음**: `AnalysisResult`에 필드가 없고 파이프라인 어디서도 설정하지 않는다(`history_service.py:1106`만 이력 재구성 때 설정).
  - 최종 판정: D1~D6이 모두 성립하면(= 자금흐름 사용 가능한 종목 + 저점수 buy 모순 출력 + 사유 미기재 + 비한국어) `watch` → `reduce`/`sell` 되돌림이 일어난다. (1)~(5) 중 하나라도 먼저 발동하면, 또는 사유가 있으면, 또는 한국어면 일어나지 않는다. buy 방향 되돌림은 (8) 뒤에는 불가능하다(점수 ≤52).
  - 실행 순서 차이: 레거시는 모든 가드레일이 끝난 뒤 (9)를 1회 평가하고(`pipeline.py:934-938`), Agent는 (8)(`:1766`) 직후 `_refresh`로 평가한다. 최종 결과는 같다.
- 조사 범위: `src/analyzer.py`(1043-1500, 1949-1975, 2136-2160, 2322-2340, 3989, 4225-4240, 5427-5530), `src/daily_market_context_guardrail.py`(전체), `src/core/pipeline.py`(576-622, 843, 900-940, 1217-1236, 1640-1800, 2133-2340), `src/services/decision_signal_extractor.py`(160-360), `src/schemas/decision_action.py`(30-237, 300-400), `src/schemas/decision_scale.py`(전체), `src/report_language.py:60-75`, `data_provider/base.py`(3962-4075, 4262-4290, 4470-4510); grep `guardrail_reason|downgrade_reason|decision_score_calibration|decision_stability`(저장소 전체, `tests/` 제외, `--include='*.py'`와 비-py 파일), `CANONICAL_DECISION_SCALE`, `apply_daily_market_context_guardrail`. 비-py 파일에서는 `docs/`와 `.github/ci-test-durations.json`에서만 매치되고 코드가 아님.

#### R2-Q2 답변
- 결론: **확정**. Agent 경로에서 `result.action`의 최초 값은 `pipeline.py:2314-2317`(`_agent_result_to_analysis_result`)에서 정해진다. 이때 `explicit_action`이 `operation_advice`보다 우선하며(`decision_action.py:383-387`), 이후 `decision_type`과 `action`의 정합을 검사하는 코드는 저장소에 없다. 따라서 LLM이 쓴 `action`이 리스크 오버라이드나 advice 재작성 뒤에도 최종 `result.action`으로 남는 경로가 **존재한다**. 단 Agent 프롬프트는 `action` 키를 요구하지 않으므로, 이 경로는 LLM이 요청받지 않은 `action`을 자발적으로 쓸 때만 활성화된다(발생 빈도는 LLM 출력 의존). 레거시는 `action`을 프롬프트로 요구하므로(`analyzer.py:1968`) 같은 우선 규칙이 정상 경로로 적용된다. 보고서에 "LLM 페이로드의 `action`이 그대로 통과"(R1-Q9)라고만 쓴 부분은 이 기준으로 보강이 필요하다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/core/pipeline.py:2314-2317` | `_agent_result_to_analysis_result()` 끝 | `explicit_action = dash.get("action") if isinstance(dash, dict) else None` / `if explicit_action is None and isinstance(getattr(result, "dashboard", None), dict): explicit_action = result.dashboard.get("action")` / `return populate_decision_action_fields(result, explicit_action=explicit_action)` | 코드 확인 |
  | `src/analyzer.py:1900-1925` | `populate_decision_action_fields()` | `action_source = explicit_action` / `if action_source is None and use_existing_action: action_source = getattr(result, "action", None)` / `build_action_fields(operation_advice=getattr(result, "operation_advice", None), explicit_action=action_source, ..., sentiment_score=getattr(result, "sentiment_score", None), guardrail_reason=getattr(result, "guardrail_reason", None), align_with_score=align_with_score)` (`align_with_score` 기본 True) / `result.action = fields["action"]` | 코드 확인 |
  | `src/schemas/decision_action.py:383-396` | `build_action_fields()` | `action = normalize_decision_action(explicit_action)` / `if action is None: ... action = normalize_decision_action(advice_text)` / `if align_with_score and score_action_conflicts_without_guardrail(...): ... action = score_action` | 코드 확인 |
  | `src/agent/agents/decision_agent.py:101-111`, `src/agent/executor.py:107-117`(및 `:263-` 이후 동일 스키마) | Agent 프롬프트의 JSON 스키마 | 필수 키 `stock_name, sentiment_score, trend_prediction, operation_advice, decision_type, confidence_level, dashboard, analysis_summary, key_points, risk_warning`. `"action"` 키 없음(`src/agent`에서 `"action"` 문자열은 `action_checklist`·`action_window`·`immediate_action`과 무관한 `factory.py:321`·`web_intent_resolver.py`뿐) | 코드 확인 |
  | `src/agent/orchestrator.py:1309-1339`, `:1330`, `:1335`, `:1901-1927`, `:1467-1481`, `:2051-2073` | multi 경로 후처리 | `_prepare_dashboard_payload` → `self._apply_risk_override(ctx)` → `self._finalize_dashboard_payload(post_risk, ctx)`. `dashboard["decision_type"] = new_signal`, `_adjust_operation_advice`: `{"buy":"买入","hold":"观望","sell":"减仓/卖出"}`, 다르면 `f"{mapping[signal]}（原建议已被风控下调）"`. `["action"]` 대입 없음 | 코드 확인 |
  | `src/core/pipeline.py:1699-1712` | Agent 첫 `_refresh` | `initial_action_advice = getattr(result, "operation_advice", None)` 직후 `previous_operation_advice=initial_action_advice`로 호출. 리스크 오버라이드·advice 재작성은 `result` 변환 **전**(오케스트레이터 안)에 끝나므로 두 값이 같고 `action`이 지워지지 않는다 | 코드 확인 |
  | `src/core/pipeline.py:2320-2339` | `_refresh_decision_action_for_final_result()` | `if previous_advice != current_advice: result.action = None; result.action_label = None` → 이후 `resolve_decision_signal_action_fields`가 `explicit_action=getattr(result, "action", None)`(`decision_signal_extractor.py:196-204`)로 같은 `build_action_fields`를 호출 | 코드 확인 |
  | `src/analyzer.py:5474-5476`, `:5522-5525` | 레거시 파싱 | `explicit_action = data.get("action")` / `if explicit_action is None and isinstance(dashboard, dict): explicit_action = dashboard.get("action")` / `populate_decision_action_fields(result, explicit_action=explicit_action, align_with_score=False)`. 프롬프트가 `"action": "buy/add/hold/reduce/sell/watch/avoid/alert"`를 요구(`:1968`) | 코드 확인 |
  | `src/schemas/decision_action.py`, `src/schemas/decision_scale.py` | 정합 검사 유무 | `decision_type` 언급은 문서(`:6`)와 `display_decision_type_for_result`(`:488-512`, **action에서 decision_type을 유도**: `buy/add→buy`, `reduce/sell→sell`, 그 외 `hold`)뿐. `action`과 `decision_type`을 비교해 고치는 코드 없음(grep `decision_type` in `src/schemas/`, `src/services/decision_signal_extractor.py`) | 코드 확인 |

- 동작 설명:
  - **최초 값(Agent)**: single(`AgentExecutor`)과 multi(Orchestrator) 모두 `agent_result.dashboard`를 `_agent_result_to_analysis_result`가 받는다. `result.action`은 `pipeline.py:2317`에서 `build_action_fields`가 정한다. 우선순위는 (1) `dash["action"]`(없으면 `result.dashboard["action"]`)을 `normalize_decision_action`으로 정규화한 값, (2) 정규화가 `None`이면 `operation_advice` 문구에서 유도, (3) 그 결과가 `hold`/`watch`이고 점수가 buy/reduce/sell 구간이며 사유가 없으면 점수 구간의 action이다(`result.guardrail_reason`은 항상 `None`이고, 이 시점에는 calibration/stability도 없다).
  - **multi + 리스크 오버라이드**: `decision_type`이 바뀌고(`:1927`) `operation_advice`가 `"观望（原建议已被风控下调）"` 또는 `"减仓/卖出（…）"` 형태로 재작성된다(`:1467-1481`). 점수는 구간으로 클램프된다(`:1408`). 변환 시점의 `operation_advice`는 이미 이 값이므로 **LLM이 `action`을 쓰지 않은 경우** `action`은 이 advice에서 유도돼 `decision_type`과 맞는다. 단 `"减仓/卖出（…）"`는 `减仓`(reduce)와 `卖出`(sell)이 동시에 매칭돼 모호하므로 `normalize_decision_action`이 `None`을 반환한다(`decision_action.py:303-361`의 `len(matches) == 1`/`matches <= {"hold","watch"}`가 모두 거짓). 그래서 리스크가 sell로 내린 multi 결과(및 LLM advice가 없어 `_signal_to_operation("sell")`로 채워진 경우)는 `result.action = None`이 된다. 이때 `pipeline_start_action`이 None이라 `action_chain_valid = False`로 처리돼 `agent_disagreement_explanation`이 생성되지 않는다(`pipeline.py:1710`, `:1803`, `:1812`).
  - **LLM이 `action`을 명시한 경우(Agent 자발 출력, 또는 레거시)**: `explicit_action`이 advice보다 우선한다. 예를 들어 multi에서 LLM이 `action: "buy"`를 쓰고 리스크가 `decision_type`을 hold/sell로 내렸어도, `result.operation_advice`가 `"观望（…）"`일 뿐 `result.action`은 `buy`로 설정된다. 이후 구조/단계/대시장 가드레일이 advice 문자열을 바꾸지 않으면 `action`이 지워지지 않으므로(`:2331`) `buy`가 최종값이다. `buy`는 (9)의 `{"hold","watch"}` 조건에도 걸리지 않는다. 가드레일 중 하나라도 advice를 바꾸면 `action`이 `None`으로 지워지고 새 advice에서 유도되므로 LLM `action`이 사라진다.
  - **레거시**: 파싱 시 `align_with_score=False`로 LLM `action`(없으면 advice 유도)을 그대로 저장한다(`:5522-5525`). 파이프라인 끝의 `_refresh`(`pipeline.py:934-938`)에서 `stabilize`/(7)/(8)이 advice를 안 바꿨으면 LLM `action`이 유지되고, 바꿨으면 advice에서 재유도된다. 가드레일이 `decision_type`만 바꾸고 advice를 같은 문자열로 남기는 경우가 있다. 예로 (8)은 LLM advice가 정확히 `"观望"`이고 `decision_type == "buy"`일 때 `decision_type`을 `hold`로 바꾸지만 advice는 같다. 이때 LLM `action`이 `buy`면 `decision_type=hold`와 `action=buy`가 어긋난 채 남는다.
  - **어긋남을 막는 코드**: 없다. `decision_type`과 `action`의 정합 검사는 저장소에 없고(위 표), 소비 측은 `display_decision_type_for_result`가 `action`을 우선해 `decision_type`을 다시 유도하므로 표시/집계는 `action` 기준이다(`notification.py:1219`).
  - **정적으로 정해지지 않는 부분**: LLM이 어떤 `action` 값을 쓰는지(Agent에서는 쓰는지 자체)는 런타임 LLM 출력이다. 갈림 지점은 `pipeline.py:2314`(Agent)와 `analyzer.py:5474`(레거시)다.
- 조사 범위: `src/core/pipeline.py`(1640-1830, 2133-2340), `src/analyzer.py`(1895-1925, 5427-5530, 5659), `src/schemas/decision_action.py`(전체), `src/schemas/decision_scale.py`, `src/services/decision_signal_extractor.py`(177-204), `src/agent/orchestrator.py`(1250-1340, 1393-1481, 1901-1927, 2040-2082), `src/agent/agents/decision_agent.py`(60-300), `src/agent/executor.py`(98-150), `src/agent/final_explanation.py`(39-130); grep `"action"`/`'action'`(`src/agent/*.py`, `src/agent/agents/*.py`), `decision_type`(`src/schemas/`), `build_action_fields\(|populate_decision_action_fields\(`(저장소 전체, `tests/` 제외).

#### R2-Q3 답변
- 결론: **확정**. API의 `summary.action`은 파이프라인의 `result.action`을 그대로 전달하지 않고, `explicit_action=result.action`으로 시작해 `align_with_score=True`로 **사유 없이 다시 계산**한다. 사유(`guardrail_reason`)를 읽는 방식이 출력 경로마다 달라서 다음 조건에서 결과가 갈린다. 파이프라인 최종 `result.action ∈ {hold, watch}`이고, 점수가 `action_for_score` 기준 buy/reduce/sell 구간(≥60 또는 ≤39)이며, 파이프라인에서는 사유가 있어 뒤집힘이 막혔는데 출력 경로는 그 사유를 읽지 못하는 경우다. 그러면 파이프라인/DecisionSignal은 `hold`/`watch`, 출력 경로는 점수 구간의 `buy`/`reduce`/`sell`이 된다. **R1-Q8 보충 발견 정정**: 동기 응답의 최종 `summary.action`은 `analysis_service.py:209`가 아니라 엔드포인트의 `_build_analysis_report`(`analysis.py:1560-1575`, 응답 반영 `:1581`)가 다시 계산해 덮어쓴 값이다(두 곳 모두 사유 없음이라 결과는 같다). `history_service.py:1106`의 `setattr`은 이 차이를 없애지 못한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/services/analysis_service.py:206-216` | `_build_analysis_response()` | `action_fields = build_action_fields(operation_advice=getattr(result, "operation_advice", None), explicit_action=getattr(result, "action", None), report_type=report_type, report_language=report_language, sentiment_score=getattr(result, "sentiment_score", None), guardrail_reason=getattr(result, "guardrail_reason", None), align_with_score=True)` → `"action": action_fields["action"]`(`:257`) | 코드 확인 |
  | `src/analyzer.py:1718-1850`, `:1801-1845` | `AnalysisResult`, `to_dict()` | `guardrail_reason` 필드 없음. `to_dict()` 키는 `'action': self.action`, `'action_label'`, `'dashboard': self.dashboard` 등이고 `guardrail_reason`/`downgrade_reason`/`metadata` 없음. `storage.py:3617-3626` `_build_raw_result`는 `to_dict()`에 `data_sources`, `raw_response`만 추가 | 코드 확인 |
  | `api/v1/endpoints/analysis.py:585-640` | 동기 `POST /analyze`(`:329`) → `_handle_sync_analysis` | `result = service.analyze_stock(...)`(`:602`) → `report = _build_analysis_report(report_data, query_id, stock_code, ...)`(`:624`) | 코드 확인 |
  | `src/services/task_queue.py:818` → `api/v1/endpoints/analysis.py:1170`, `:1067-1156`, `:1121`, `:1151`, `:1345` | 비동기 | `service.analyze_stock(...)` 결과가 `task.result`에 저장되고, `GET /status/{task_id}`(`get_analysis_status` `:1170`)가 `_build_task_analysis_result`(`:1067`)로 `_build_analysis_report`(`:1121`) 또는 `_ensure_report_action_fields`(`:1040`, 호출 `:1151`)로 재계산한다. DB 폴백(`:1345`, 응답 반영 `:1374`)도 `build_action_fields`를 호출 | 코드 확인 |
  | `api/v1/endpoints/analysis.py:1560-1575`, `:220-238` | `_build_analysis_report()`, 로컬 `_extract_guardrail_reason()` | `explicit_action=raw_result_data.get("action") or ...` / `guardrail_reason=_extract_guardrail_reason(raw_result_data)` / `align_with_score=True`. 로컬 추출기는 `raw_result`의 `guardrail_reason`, `downgrade_reason`, `decision_score_guardrail_reason`, `metadata.guardrail_reason/downgrade_reason`만 보고 **`dashboard`(calibration, stability)는 읽지 않는다**. `to_dict()`에 이 키들이 없으므로 항상 `None`. 그 결과가 `ReportSummary(action=action_fields["action"])`(`:1581`)로 응답에 들어간다 | 코드 확인 |
  | `api/v1/endpoints/analysis.py:1040-1064` | `_ensure_report_action_fields()` | `guardrail_reason=_extract_guardrail_reason(raw_result)`, `align_with_score=True` → 같은 로컬 추출기 | 코드 확인 |
  | `api/v1/endpoints/history.py:200-218`, `:469-477` | `get_stock_bar` | 같은 형태의 로컬 `_extract_guardrail_reason(raw_result)`(dashboard 미참조) + `align_with_score=True` | 코드 확인 |
  | `src/services/history_service.py:806-816`, 호출 `:438`, `:776` | `_decision_action_fields_for_record()` (이력 목록·상세) | `display_action_fields(..., sentiment_score=getattr(record, "sentiment_score", None), guardrail_reason=extract_decision_guardrail_reason(raw))` → `decision_scale.py:114-155`: 후보 `data.guardrail_reason`, `downgrade_reason`, `decision_score_guardrail_reason`, `metadata.*`, `calibration.guardrail_reason/downgrade_reason`, 그리고 `stability_applied not in (False, 0, "0", "false", "False")`일 때만 `stability.guardrail_reason/downgrade_reason/reason` | 코드 확인 |
  | `src/services/history_comparison_service.py:41-48` | 이력 비교 | `display_action_fields(..., guardrail_reason=extract_decision_guardrail_reason(raw_result))` — 위와 동일 후보 | 코드 확인 |
  | `src/schemas/decision_action.py:404-411`, `:415-440`, `:458-512`; `src/notification.py:1207`, `:1219`, `:1230`, `:2996`, `:3010`; `src/services/report_renderer.py:145`, `:149`, `:176`; `src/services/history_service.py:1513`, `:1521` | `display_*_for_result()` (알림·리포트 렌더·이력 마크다운) | `_result_guardrail_reason(result)` = `extract_decision_guardrail_reason({"guardrail_reason": getattr(result, "guardrail_reason", None), "downgrade_reason": ..., "dashboard": result.dashboard, "metadata": ...})` → `align_with_score=True`. calibration과 `applied`가 거짓이 아닌 stability 사유까지 읽음 | 코드 확인 |
  | `src/services/decision_signal_extractor.py:74-75`, `:177-204`, `:327-360` | DecisionSignal 생성 / 파이프라인 `_refresh` | `resolve_decision_signal_action_fields` = 파이프라인과 **같은 함수**. 사유 후보는 calibration → stability.reason(`applied` 무시) → `result.guardrail_reason` → advice 힌트 | 코드 확인 |
  | `src/services/decision_signal_service.py:556-575`, `:574-610`; `src/services/decision_signal_reassess_service.py:223-234`, `:347-380` | 이력 기반 신호 재유도 | `calibration.guardrail_reason`, `stability.reason`, `raw.guardrail_reason` + 힌트(`_history_guardrail_reason`). 파이프라인과 동일 후보 | 코드 확인 |
  | `src/services/backtest_service.py:944-955` | 백테스트 행 | `guardrail_reason=raw.get("guardrail_reason") or raw.get("downgrade_reason")` — dashboard 미참조 | 코드 확인 |
  | `src/analyzer.py:1192-1213`, `:1384-1393`, `:1440-1493` | 사유는 있으나 점수는 안 바뀌는 강등/표시 | (6) hold 문구: `_set_structural_hold_wording(calibrate_score=False)` → `_apply_hold_watch_dashboard`가 `stability = {"applied": True, "reason": reason, ...}`. 자금흐름 불가+비-buy: `_set_decision_stability_unavailable`가 `{"applied": False, "reason": "资金流不可用，未使用资金流校准", ...}` | 코드 확인 |
  | `src/services/history_service.py:1035-1106`, `:1010` | `_rebuild_analysis_result()` | `guardrail_reason = extract_decision_guardrail_reason(raw_result)` / `if guardrail_reason: setattr(result, "guardrail_reason", guardrail_reason)`. 호출처는 `get_markdown_report`(`:969`, 호출 `:1010`) 하나뿐(grep) | 코드 확인 |

- 동작 설명:
  - **차이가 생기는 정확한 입력 조건**: 파이프라인 최종값 `A_p = result.action`이 `hold` 또는 `watch`이고, 그 시점의 유효 점수가 buy(≥60)/reduce(20~39)/sell(0~19) 구간이어야 한다. 그러면서 파이프라인의 `_extract_guardrail_reason`이 비어 있지 않은 사유를 찾았어야 한다(그래서 `A_p`가 점수 구간으로 뒤집히지 않고 남았다). 출력 경로는 `explicit_action=A_p`로 시작해 사유가 없으면 점수 구간 action으로 바꾼다. 점수는 두 쪽이 같다. (1)~(5)가 `result.sentiment_score`를 `adjusted_score`로 덮어쓰므로(`_bound_hold_watch_sentiment_score`, `analyzer.py:1430`) `calibration.adjusted_score`와 `result.sentiment_score`가 일치한다.
  - **그런 `A_p`가 만들어지는 구체 사례**(점수가 클램프되지 않는 강등/사유 기록):
    1. **자금흐름 불가 + 비-buy**(`analyzer.py:1094-1116` → `_set_decision_stability_unavailable` `:1384`): `decision_type`과 advice가 모두 buy가 아니고(예: LLM `hold`, 점수 62), `capital_flow`가 불가인 us/jp/kr/tw·일반 HK·ETF·지수·A주 조회 실패. 점수는 안 바뀌고 `stability.reason`(`applied=False`)만 기록. 파이프라인은 `applied`를 무시하고 사유로 인정해 `hold` 유지. 출력 경로 중 로컬 추출기(`analysis.py`, `history.py`)와 `extract_decision_guardrail_reason` 기반(`history_service`, `display_*_for_result` 알림·렌더, `history_comparison`)은 모두 사유를 못 읽어 → 점수 구간 `buy`(62)로 뒤집는다. `stability.applied=False`는 `decision_scale.py:140-148`이 제외하기 때문이다.
    2. **(6) hold 문구**(`:1192-1213`): LLM `decision_type=hold`, 자금흐름 사용 가능, `change_pct<0 & near_support & flow != outflow` 또는 `mid_range & flow == neutral`, 점수 ≥60 또는 <40. `stability.applied=True`, `reason` 있음. 파이프라인은 `hold` 유지. API 로컬 추출기 경로(`analysis.py`·`history.py`)는 dashboard를 못 읽어 뒤집지만, `extract_decision_guardrail_reason` 기반 경로(`history_service` 목록·상세, 알림·렌더)는 `applied=True`라 읽어 `hold` 유지.
    3. **LLM 사유**(레거시, `analyzer.py:5452-5458`): LLM이 `hold`/`watch`에 극단 점수와 `guardrail_reason`을 채운 경우. `calibration.guardrail_reason`에 기록. 파이프라인·DecisionSignal·`extract_decision_guardrail_reason` 기반 경로는 읽지만 `analysis_service`와 API 로컬 추출기 경로는 못 읽어 뒤집는다. 채우는지는 LLM 출력 의존.
    4. **advice 힌트 사유**(`decision_signal_extractor.py:343-360`): advice 등에 `"等待"`, `"风险"`, `"support"` 같은 힌트가 있으면 사유로 간주. 파이프라인과 `decision_signal_service`/`reassess`만 인정. 모든 API·알림 경로는 힌트를 쓰지 않는다.
  - **경로별 사유 해석 요약**: 파이프라인 `result.action` 및 DecisionSignal = (calibration, stability 전부, 힌트) / `analysis_service`·`analysis.py`(동기·비동기·DB 폴백)·`history.py` stock bar·`backtest_service` = 사실상 사유 없음 / `history_service` 목록·상세·`history_comparison`·알림·`report_renderer`·이력 마크다운 = (calibration, `applied≠False`인 stability) / `decision_signal_service`·`reassess` = 파이프라인과 같은 후보. 그래서 같은 분석 건이 DecisionSignal에서는 `hold`, `POST /analyze`·`/status`·`/history/stock-bar`에서는 `buy`로 보일 수 있다. 반대 방향(파이프라인이 뒤집었는데 출력이 `hold`로 되돌리는 경우)은 없다. 출력 경로가 `explicit_action`으로 이미 뒤집힌 `A_p`를 받기 때문이다.
  - **`history_service.py:1106`의 효과**: `_rebuild_analysis_result`는 이력 마크다운 생성(`get_markdown_report`)에서만 쓰이고, 거기서 설정되는 값은 `_result_guardrail_reason`이 이미 `dashboard`에서 읽는 것과 같은 후보(`extract_decision_guardrail_reason`)라 결과가 달라지지 않는다. 동기·비동기 응답의 `analysis_service` 입력은 새로 만든 파이프라인 결과 객체이므로 이 `setattr`이 적용되지 않는다. 따라서 API 응답의 차이를 없애지 못한다.
- 조사 범위: `src/services/analysis_service.py`(140-290), `api/v1/endpoints/analysis.py`(26-60, 200-240, 329-340, 585-650, 1040-1215, 1290-1365, 1465-1600), `api/v1/endpoints/history.py`(195-220, 415-495), `src/services/history_service.py`(425-445, 770-830, 969-1110, 1500-1535), `src/services/history_comparison_service.py`, `src/services/decision_signal_service.py`(540-620), `src/services/decision_signal_reassess_service.py`(210-380), `src/services/backtest_service.py`(935-962), `src/services/task_queue.py`(805-845), `src/notification.py`(1198-1235, 2990-3015), `src/services/report_renderer.py`(140-180), `src/schemas/decision_action.py`, `src/schemas/decision_scale.py`, `src/storage.py`(2794-2830, 3617-3626), `src/analyzer.py`(1384-1500, 1801-1850, 1900-1925). grep `build_action_fields\(|populate_decision_action_fields\(|display_action_fields\(|display_action_fields_for_result\(|resolve_decision_signal_action_fields\(|display_operation_advice_for_result\(|display_decision_type_for_result\(|score_action_conflicts_without_guardrail\(`(저장소 전체, `tests/` 제외)와 `guardrail_reason|downgrade_reason`(전체 `.py`, `tests/` 제외). 비테스트 호출처는 모두 위 표에 포함했다.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R2-Q1 | 정적 확인 불가 | 직접 열어 확인한 근거: `analyzer.py:5451-5458`(최상위 `guardrail_reason`/`downgrade_reason`을 `dashboard`가 dict일 때만 calibration에 `setdefault`), `:1966-1969`(프롬프트가 `action`과 `guardrail_reason`을 요구), `:1094-1117`(자금흐름 `unavailable`이면 (1) 또는 `_set_decision_stability_unavailable` 뒤 `return`, `current_price is None`이면 `return`), `:1119-1131`(`breakout`·`near_resistance`·`mid_range` 정의), `:1135-1168`((2)(3)(4) 분기), `:1217-1218`(예외 시 건너뜀), `:1322-1360`(`unavailable` 조건), `daily_market_context_guardrail.py:47`(상한 52), `:62-91`, `:201-231`, `:280-285`((8)이 calibration·stability를 쓰지 않음), `decision_signal_extractor.py:177-204`, `:269-274`, `:300-360`(사유 후보 순서, `"观望"`에 힌트 없음), `decision_scale.py:158-171`, `pipeline.py:900-938`(레거시는 가드레일 3종 뒤 1회 `_refresh`), `:1760-1782`(Agent는 (8) 직후 `_refresh`), `:2305-2317`, `:2320-2339`, `decision_action.py:30-109`, `:303-361`, `:375-396`(한국어 `"관망"`은 `_ACTION_PHRASES`에 없어 `None` → (9) 불성립). `src/agent`·`src/core`에서 `guardrail_reason|downgrade_reason|decision_score_calibration|decision_stability` grep 0건 재현. D1~D6이 코드 위치로 고정됐고, 갈림 지점(`analyzer.py:5452`)과 경우 A(사유 기재 → `watch` 유지)·경우 B(미기재 → `reduce`/`sell`)·Agent(정상적으로 B)가 모두 열거돼 정적 확인 불가 조건을 충족한다. 다만 질문자 확인으로 **보충할 점 2개**가 있다. ① 레거시 프롬프트에 포함된 `CANONICAL_DECISION_SCALE_PROMPT_ZH/EN`(`decision_scale.py:43`, `:55`; `analyzer.py:1955`, `:2143`, `:2464`, `:2527`에서 결합)은 사유를 "`guardrail_reason` **또는 `dashboard.decision_stability.reason`**"에 쓰라고 지시한다. 따라서 레거시 경우 A에는 LLM이 `dashboard.decision_stability.reason`(또는 `dashboard.decision_score_calibration.guardrail_reason`)을 직접 채우는 경우도 포함된다. 답변은 이 경로를 Agent의 "자발적 기재"로만 다뤘다. ② (9)의 점수는 `calibration.adjusted_score`가 있으면 그 값을 쓴다(`decision_signal_extractor.py:185-188`, `:269-274`). (1)~(5)가 발동하지 않은 경우 calibration은 LLM이 쓴 그대로 남으므로, LLM이 요청받지 않은 `adjusted_score`를 넣으면 (8)의 52 상한이 아니라 그 값으로 D3가 판정된다. 둘 다 LLM 출력에 따른 추가 갈림이며 결론(정적 확인 불가)을 바꾸지 않는다. 다음 라운드 질문으로 열 실익이 없어 보고서 반영 목록에 함께 적는다 |
| R2-Q2 | 해소 | `pipeline.py:2314-2317`(대시보드 `action`을 `explicit_action`으로 전달), `analyzer.py:5474-5476`, `:5522-5525`(레거시 `explicit_action`, `align_with_score=False`), `decision_action.py:375-396`(`explicit_action`이 advice보다 우선), `pipeline.py:1699-1712`(Agent 첫 `_refresh`의 previous = 변환 직후 advice라 `action`이 지워지지 않음), `:2329-2333`(advice 문자열이 다를 때만 `action` 초기화), `orchestrator.py:2062-2073`(`"减仓/卖出（原建议已被风控下调）"`), `decision_action.py:85-108`(`减仓`→reduce, `卖出`→sell 동시 매칭 → `:349-353`에서 `None`), `decision_agent.py:101-111`(필수 키에 `action` 없음)을 확인. 완료 조건 ①~④를 모두 채웠고, `decision_type`과 `action` 정합 검사가 없다는 결론과 어긋남이 생기는 조건(LLM `action` 명시 + 이후 가드레일이 advice 문자열을 바꾸지 않음)이 코드로 제시됨. LLM이 `action`을 쓰는지만 LLM 출력 의존으로 남겼고 갈림 지점(`pipeline.py:2314`, `analyzer.py:5474`)이 명시됨 |
| R2-Q3 | 해소 | `analysis_service.py:206-216`(`guardrail_reason=getattr(result, "guardrail_reason", None)`, `align_with_score=True`), `api/v1/endpoints/analysis.py:218-238`(로컬 추출기는 `raw_result`의 최상위·`metadata` 키만 보고 `dashboard`를 읽지 않음), `:618-630`(동기 응답이 `_build_analysis_report` 경유), `:1040-1064`, `:1560-1581`(같은 추출기로 `summary.action` 재계산), `history.py:200-218`, `:466-478`, `history_service.py:806-816`, `:1095-1106`, `decision_scale.py:114-155`(`stability.applied`가 거짓이면 stability 사유 제외), `decision_action.py:402-445`(`_result_guardrail_reason`, `display_action_fields`), `analyzer.py:1380-1394`(`applied: False` + 사유 기록)을 확인. `build_action_fields(|populate_decision_action_fields(|display_action_fields(` 비테스트 호출처 grep을 재실행해 17곳이 답변 표와 일치함을 확인. 차이가 생기는 입력 조건, 경로별 사유 해석 범위, 구체 사례 4종, `history_service.py:1106`이 차이를 없애지 못하는 이유까지 완료 조건 ①~④ 충족. `_build_analysis_report` 위치 정정(R1-Q8 보충 발견)도 직접 확인함 |

---

## 최종 정리 (질문자)

- 총 라운드: 2 / 총 질문: 15 / 해소 9 · 없음 확정 4 · 정적 확인 불가 2 (R1-Q8은 R2-Q1로 이어져 정적 확인 불가로 종결)
- 이 레포를 이해하는 데 핵심인 확정 사실
  1. **기본 실행은 레거시 단일 LLM 경로다.** `AGENT_MODE` 기본 `false`, `AGENT_SKILLS` 기본 `[]`, `analysis_skills` 기본 `None`이고 Actions 워크플로는 이 값들을 바꾸지 않는다. Agent 경로는 `AGENT_MODE=true`, API 요청의 `skills`, `all`이 아닌 `AGENT_SKILLS` 중 하나로 켜진다(`src/config.py:1984`, `:1992`; `src/core/pipeline.py:561-571`; `src/services/analysis_service.py:140-149`) — R1-Q3
  2. **한국·미국·일본·대만 등 해외 종목(Futu 미설정 HK, ETF, 지수 포함)은 LLM의 buy가 항상 hold로 강등된다.** `capital_flow` 키는 모든 경로에서 존재하고 값은 `not_supported`이므로 자금흐름 불가 강등이 반드시 발동한다(`data_provider/base.py:3963`, `:4070-4075`, `:3865-3866`; `src/analyzer.py:1094-1105`, `:1322-1337`) — R1-Q1, R2-Q1
  3. **Web/API·CLI·봇 배치 분석은 모두 `StockAnalysisPipeline.analyze_stock`으로 모여 가드레일 3종을 거친다.** 비테스트 호출처는 `pipeline.py:906/907/916`(레거시), `:1718/1738/1766`(Agent)뿐이다. 채팅 엔드포인트(`api/v1/endpoints/agent.py`)만 예외다 — R1-Q6
  4. **Actions cron(UTC 10:00) 시점의 미국 종목은 `premarket`이다.** 그래서 `phase_decision_guardrail`이 즉시 매매 문구를 "대기"로 바꾸고 신뢰도 高를 低로 낮춘다(`src/core/trading_calendar.py:393-416`; `src/phase_decision_guardrail.py:18`, `:170-186`). 같은 시점에 `_augment_historical_with_realtime`는 시각을 보지 않고 거래일이면 오늘 날짜 가상 봉을 붙인다(`src/core/pipeline.py:2758-2810`) — R1-Q4, R1-Q7
  5. **Actions 실행은 매번 빈 DB로 시작한다.** DB를 캐시·복원·커밋하는 단계가 없고 아티팩트는 `reports/`, `logs/`뿐이다(`.github/workflows/00-daily-analysis.yml:552-560`; `.gitignore:57`, `:62`) — R1-Q5
  6. **LLM/다중 라운드 중재자는 켤 방법이 없다.** 런타임은 인자 없는 `StrategySynthesizer()`로 규칙 기반 `DeliberationMediator`만 쓴다(`src/agent/skills/engine.py:191`, `aggregator.py:75`, `synthesis.py:203-210`) — R1-Q10
  7. **최종 `action`은 `explicit_action` → advice → 점수 구간 정렬 순으로 정해지고, `decision_type`과의 정합 검사는 없다.** LLM이 쓴 `action`은 이후 가드레일이 advice 문자열을 바꾸지 않으면 그대로 남는다(`src/schemas/decision_action.py:375-396`; `src/core/pipeline.py:2314-2317`, `:2320-2339`) — R2-Q2
  8. **점수 구간 정렬 (9)는 사유가 있으면 막힌다.** 가드레일 (1)~(5)는 점수를 45~59로 고정하고 사유를 calibration에 남겨 되돌림을 막는다. (8) 대시장 가드레일은 사유를 남기지 않아, 저점수 buy 모순 출력에서 사유가 없으면 `watch`가 `reduce`/`sell`로 바뀔 수 있다. buy 방향 되돌림은 없다(`src/schemas/decision_scale.py:158-171`; `src/analyzer.py:1419-1437`; `src/daily_market_context_guardrail.py:79-91`, `:280-285`) — R1-Q8, R2-Q1
  9. **같은 분석 건의 `action`이 출력 경로마다 다를 수 있다.** 파이프라인·DecisionSignal은 `dashboard`의 calibration·stability 사유를 읽지만, API 동기·비동기 응답과 `/history` stock bar는 `dashboard`를 읽지 않는 로컬 추출기로 다시 계산한다. 그래서 자금흐름 불가 + LLM hold + 점수 ≥60 같은 결과가 파이프라인에서는 `hold`, API에서는 `buy`로 보인다(`api/v1/endpoints/analysis.py:218-238`, `:1560-1581`; `src/analyzer.py:1380-1394`; `src/schemas/decision_scale.py:130-148`) — R2-Q3
  10. **코드 점수(`系统评分`)는 레거시에서는 프롬프트 표의 값일 뿐이고, Agent 경로에서는 LLM 점수나 대시보드가 없을 때 대체값이 된다.** 두 점수를 비교하는 코드는 없다(`src/analyzer.py:4789-4790`; `src/core/pipeline.py:2169-2180`, `:2615-2672`). 뉴스 검색 결과에는 URL·제목 중복 제거가 없다(`src/search_service.py:4546-4620`) — R1-Q11, R1-Q12

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `00-overview.md` 핵심 발견 2 | 코드 점수는 "LLM 입력 참고값일 뿐" | 레거시 경로에 한정한다. Agent 경로에서는 LLM 점수가 없으면 `signal_score`가 `sentiment_score`가 되고(`pipeline.py:2169-2180`), 대시보드가 없으면 `signal_score`·`buy_signal`로 점수·advice·`decision_type`을 채운다(`:2615-2672`)고 추가 | R1-Q11 |
| `00-overview.md` 핵심 발견 4, `03-decision.md` 4-5 (1), `05-boundary-and-fit.md` 7-1 "주의" | 한국 `.KS`는 자금흐름이 항상 `not_supported`라 매수가 항상 hold로 강등(정적 추적만) | 결론 유지, 검증 수준을 `코드 확인`으로 올리고 근거 추가: 한국은 Futu(HK 전용)가 아니라 yfinance 번들을 쓰며(`base.py:3865-3866`) 그 번들에 `capital_flow`가 없어(`yfinance_fundamental_adapter.py:158-168`) `:4070-4075`의 `not_supported` 블록이 들어감. 적용 범위를 us/jp/kr/tw, Futu 미설정 HK, ETF, 지수, A주 조회 실패까지로 넓혀 적는다 | R1-Q1, R2-Q1 |
| `01-data.md` 범례 | Agent 경로는 `AGENT_MODE=true` 또는 `AGENT_SKILLS`가 `all`이 아닌 값일 때 | API 요청 본문의 `skills`(→ `analysis_skills`, `analysis_service.py:140-149`)로도 자동 활성화됨을 추가. 기본 Actions·로컬 스케줄은 기본값 기준 레거시 경로임을 명시(`config.py:1984`, `:1992`) | R1-Q3 |
| `01-data.md` 1-2 백테스트 요약 도구 행 | `get_skill_backtest_summary` 등, 검증 `추론` | 검증을 `코드 확인`으로 올림. single 에이전트는 필터 없이 백테스트 도구 3개(`get_skill_/get_strategy_/get_stock_backtest_summary`)를 모두 LLM에 노출하고(`factory.py:363-376`, `registry.py:243-245`), 분석 프롬프트에 사용 지시는 없음(`executor.py:71-385` grep 0건) | R1-Q2 |
| `01-data.md` 2-3 마지막 행 | "시세에 장중 반영 후 MA 재계산", 내부 미열람 | 시장 단계·시각을 보지 않고, 거래일이면 마지막 봉이 오늘 이상일 때 덮어쓰기, 아니면 오늘 날짜 가상 봉 추가(`pipeline.py:2758-2810`). 장전 실행에서도 오늘 봉이 생김 | R1-Q4 |
| `02-schedule.md` 3-1 "Web/API 수동" 행 | `미확인` | 동기·비동기 모두 `AnalysisService.analyze_stock` → `process_single_stock` → `analyze_stock`으로 가드레일 3종을 거침(`analysis.py:599-611`, `task_queue.py:803-826`). 채팅 엔드포인트(`agent.py`)는 파이프라인을 거치지 않음 | R1-Q6 |
| `02-schedule.md` 3-3, `next.md` 4절 질문 2 | DB 캐시/복원 단계 없음(1개 워크플로 근거), 백테스트 무의미 추정 | 워크플로 10개 전체와 `.gitignore`를 조사한 `없음 확정`으로 올림. 아티팩트는 `reports/`, `logs/`뿐(`00-daily-analysis.yml:552-560`) | R1-Q5 |
| `02-schedule.md` 3-6 마지막 문단 | 미국 장은 그 시각 열려 있지 않음, `추론` | `코드 확인`으로 올림. UTC 10:00 = ET 05:00/06:00이라 미국 거래일이면 `premarket`, 마지막 완전 일봉은 직전 세션(`trading_calendar.py:239-282`, `:393-416`). 휴장일 종목은 기본 필터로 분석에서 빠짐(`main.py:493-516`) | R1-Q7 |
| `03-decision.md` 4-5 "방향성" 행 | "(9)만 점수가 높으면 buy로 되돌릴 수 있음" | (1)~(5) 뒤에는 점수 45~59 고정과 calibration 사유 때문에 (9)가 성립하지 않음. (8) 뒤에는 점수 ≤52라 buy 방향 되돌림은 불가하고, 원점수 0~39 + 사유 없음 + 비한국어 + 자금흐름 사용 가능 종목일 때만 `watch`→`reduce`/`sell`이 가능. 사유 기재 여부는 LLM 출력에 달려 정적으로 정해지지 않음(`analyzer.py:5452-5458`). hold+점수 ≥60에서 사유가 없으면 (9)가 `buy`로 올리는 경우는 여전히 있음 | R1-Q8, R2-Q1 |
| `03-decision.md` 4-5 (9) 설명 | `_refresh_decision_action_for_final_result`가 `build_action_fields`를 직접 호출 | `resolve_decision_signal_action_fields`(`decision_signal_extractor.py:177-204`)를 거침. 점수는 `calibration.adjusted_score` 우선, 사유는 calibration → `decision_stability.reason`(`applied` 무시) → `result.guardrail_reason` → advice 힌트 순 | R1-Q8 |
| `qa.md` R1-Q8 답변 (3)·동작 설명 (8) | "(8) 이후 사유는 None", 저점수면 (9)가 `reduce`/`sell`로 바꿈 | 레거시는 LLM이 최상위 `guardrail_reason`/`downgrade_reason`(`analyzer.py:5452-5458`) 또는 `dashboard.decision_stability.reason`/`decision_score_calibration.guardrail_reason`(프롬프트 `decision_scale.py:43`, `:55`)을 채우면 사유가 생겨 막힘. (8) 단독 발동은 자금흐름 사용 가능 종목에서만 가능하고, 한국어 리포트는 `"관망"`이 `None`으로 변환돼 뒤집힘이 없음(`decision_action.py:30-109`). LLM이 calibration에 `adjusted_score`를 넣으면 (9)의 점수가 그 값으로 바뀜(`decision_signal_extractor.py:269-274`) | R2-Q1 |
| `qa.md` R1-Q8 답변 "보충 발견" | API 동기 응답의 `summary.action`은 `analysis_service.py:206-216`에서 정해짐 | 최종 응답값은 엔드포인트 `_build_analysis_report`(`api/v1/endpoints/analysis.py:1560-1581`)가 `dashboard`를 읽지 않는 로컬 추출기(`:218-238`)로 다시 계산한 값. 차이 조건은 R2-Q3 결론대로 | R2-Q3 |
| `03-decision.md` 4-5 (10b), `next.md` 2절·3절 2번 | `_finalize_dashboard_payload` 일부 범위만 인용, 전체 규칙 미확인 | `confidence_level`이 `risk_applied`와 무관하게 LLM 점수/100으로 다시 계산돼 항상 덮어써짐(`orchestrator.py:1401`, `:1650`, `:2142-2147`)을 추가하고 미확인 항목을 닫음. LLM `action`은 이 함수가 건드리지 않고 그대로 통과 | R1-Q9 |
| `03-decision.md` 4-5 최종 결정 필드 서술 | `action`과 `decision_type`이 함께 최종 결정을 이룬다는 전제 | 최종 `action`은 `explicit_action` 우선이며 `decision_type`과의 정합 검사가 없음(`decision_action.py:375-396`). 레거시에서 LLM advice가 정확히 `"观望"`이고 `action=buy`면 (8) 뒤 `decision_type=hold`, `action=buy`로 어긋날 수 있음. multi 리스크 sell 결과의 advice `"减仓/卖出（…）"`는 모호해서 `action=None`이 됨. 표시·집계는 `display_decision_type_for_result`가 `action`에서 다시 유도(`decision_action.py:488-512`) | R2-Q2 |
| `03-decision.md` 4-5 (신규 행), `05-boundary-and-fit.md` 7-1 | 출력 경로별 `action` 차이 서술 없음 | 사유 해석 범위가 경로마다 다름: 파이프라인·DecisionSignal(calibration, stability 전부, 힌트) / `analysis_service`·API 동기·비동기·DB 폴백·`/history` stock bar·백테스트(사실상 사유 없음) / 이력 목록·상세·비교·알림·리포트 렌더(calibration, `applied≠False` stability). 그래서 자금흐름 불가 + LLM hold + 점수 ≥60이면 DecisionSignal은 `hold`, API 응답은 `buy`가 됨(`analysis.py:218-238`, `:1560-1581`; `analyzer.py:1380-1394`; `decision_scale.py:130-148`). `history_service.py:1106`은 이 차이를 없애지 못함 | R2-Q3 |
| `03-decision.md` 4-2 "토론 라운드" 행, `next.md` 2절·3절 1번 | LLM 중재자 활성화 설정 미확인 | `없음 확정`: 인스턴스화·설정 키가 없고 런타임은 인자 없는 `StrategySynthesizer()`만 씀(`engine.py:191`, `aggregator.py:75`, `synthesis.py:203-210`) | R1-Q10 |
| `next.md` 4절 질문 4 | 코드 점수를 따르라는 직접 지시는 못 찾음(범위 없음) | 레거시 프롬프트·`CORE_TRADING_SKILL_POLICY_ZH`에 지시 없음, 비교 코드 없음을 grep 범위와 함께 `없음 확정`으로 적음(R1-Q11 조사 범위) | R1-Q11 |
| `04-research.md` 5-4 "중복 제거" 행 | `미확인` | `없음 확정`: 차원 안·차원 간 모두 URL·제목 중복 제거 없음. 차원당 최대 3건 절단만 있음(`search_service.py:4526`, `:3816-3836`). DB upsert(`storage.py:2399-2425`)는 LLM 입력과 무관 | R1-Q12 |
