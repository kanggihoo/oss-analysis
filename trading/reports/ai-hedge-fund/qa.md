# ai-hedge-fund — 질문·답변 검증 기록

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 1
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | 재무지표 행의 최신순 정렬을 코드가 보장하는가 | Q1 / Q2 | 없음 확정 | R1 |
| R1-Q2 | 프롬프트의 `mktcap`·`P/E` 값의 출처와 기준 시점 | Q1 | 해소 | R1 |
| R1-Q3 | NaN/Inf를 클라이언트에서 거르는 코드가 있는가 | Q2 | 없음 확정 | R1 |
| R1-Q4 | 날짜 없는 캐시 키 항목(`company_facts`, `earnings_history`)의 재사용 범위 | Q2 | 해소 | R1 |
| R1-Q5 | PEAD 실적 이력(최신 N건)이 과거 기준일을 덮지 못할 때의 동작 | Q2 / Q1 | 해소 | R1 |
| R1-Q6 | 체결 전 refresh 평가의 기준일과 발생 조건 | Q3 / Q4-2 | 해소 | R1 |
| R1-Q7 | CLI 백테스트의 기본 기간이 정해지는 위치 | Q3 / Q4-8 | 해소 | R1 |
| R1-Q8 | PEAD가 이벤트 없음일 때 블렌딩에서 어떻게 처리되는가 | Q4-3 / Q4-5 | 해소 | R1 |
| R1-Q9 | 주간 리밸런스에서 PEAD가 보는 이벤트 범위 | Q4-3 | 해소 | R1 |
| R1-Q10 | 여러 전략에 같은 페르소나가 있을 때 호출 중복 여부 | Q4-2 / Q4-8 | 해소 | R1 |
| R1-Q11 | 기권 누적에 대한 경보·중단 장치 부재 확정 | Q4-6 | 없음 확정 | R1 |
| R1-Q12 | paper/live에서 blind 프롬프트를 켤 수 있는 경로 | Q4-1 | 해소 | R1 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. 재무지표 행의 최신순 정렬을 코드가 보장하는가
- GUIDE 항목: Q1, Q2(원시 데이터 가공)
- 왜 묻는가: `01-data.md` Q1-1 표와 `03-decision.md` 4-1절은 스냅샷이 "기간별 행(최대 20행, 최신순)"이고 `debt_to_equity_latest`, `market_cap_latest`, `eps_growth_yoy`(t-0 대비 t-4), `gross_margin_trend`(최신-최오래), blind의 `t-0` 표기가 모두 첫 행을 최신으로 가정한다고 적었다. 그런데 `build_snapshot()`은 `metrics[0]`을 그대로 최신으로 쓰고, `data/client.py`·`data/cached.py`·`features/snapshot.py`에서 정렬 코드를 찾지 못했다. 순서가 FD 응답에만 의존한다면 이 집계 전부의 전제가 외부 응답이다.
- 질문: `get_financial_metrics()` 결과가 `build_snapshot()`에 들어가기 전에 `report_period` 또는 `filing_date` 기준으로 정렬되는 코드가 있는가, 아니면 FD 응답 순서를 그대로 쓰는가?
- 답변 완료 조건: 정렬 코드가 있으면 그 `파일:라인`과 원문. 없으면 `hedge_fund/` 전체의 `sort`, `sorted`, `reverse`, `order` grep 결과와 함께 "없음 확정". 테스트 픽스처나 docstring이 응답 순서를 가정하는 문장이 있으면 그 위치와 원문도 붙인다.

#### R1-Q2. 프롬프트의 `mktcap`·`P/E` 값의 출처와 기준 시점
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` Q1-1 "핵심 시사점"은 "프롬프트의 시총·P/E는 가장 최근에 공시된 ttm 행의 값"이고 "밸류에이션이 최대 한 분기쯤 낡을 수 있다"를 `추론`으로 적었다. `next.md` 미확인 체크리스트에도 "`market_cap`이 공시일 기준 시총인지"가 남아 있다. 처음 읽는 사람은 LLM이 보는 P/E가 어느 날짜 가격으로 계산된 값인지 알 수 없다.
- 질문: 스냅샷 행의 `market_cap`과 `price_to_earnings_ratio`는 코드가 가격으로 다시 계산하는가, FD `/financial-metrics/` 응답 필드를 그대로 쓰는가? 그대로 쓴다면 그 값의 기준 시점을 코드(모델 필드 주석, docstring, 테스트)가 어떻게 기술하는가?
- 답변 완료 조건: 값이 만들어지거나 복사되는 `파일:라인`과 원문. 기준 시점에 대한 코드 내 서술이 있으면 그 원문, 없으면 "코드에 서술 없음"과 함께 정적 확인 불가 사유(외부 API 정의에 의존).

#### R1-Q3. NaN/Inf를 클라이언트에서 거르는 코드가 있는가
- GUIDE 항목: Q2(원시 데이터 가공: 결측치)
- 왜 묻는가: `01-data.md` Q2 "원시 데이터 가공" 표의 NaN/Inf 행은 "서버 측에서 null로 정리한다고 docstring에 명시. 코드로 직접 검증 불가"로 `추론` 표기했다(`data/models.py:36-43`). 클라이언트 쪽에 pydantic validator나 `isfinite` 검사가 있는지는 코드로 답할 수 있다.
- 질문: `FinancialMetrics`를 포함한 FD 응답 모델이 생성되거나 스냅샷 집계(`_avg`, `_trend`, `_cagr`, `_eps_growth_yoy`, `_fmt`)에 들어갈 때 NaN/Inf를 검사하거나 None으로 바꾸는 코드가 있는가?
- 답변 완료 조건: 있으면 `파일:라인`과 원문. 없으면 `data/models.py`, `data/client.py`, `features/snapshot.py`에 대한 `validator`, `field_validator`, `isfinite`, `isnan`, `nan`, `inf` grep 결과를 조사 범위로 적고 "없음 확정". 그 경우 NaN이 들어오면 집계와 렌더가 어떤 값을 내는지 코드 흐름으로 설명.

#### R1-Q4. 날짜 없는 캐시 키 항목(`company_facts`, `earnings_history`)의 재사용 범위
- GUIDE 항목: Q2(캐시)
- 왜 묻는가: `01-data.md` Q2 "캐시" 표의 "운영 시 주의" 행은 "`get_company_facts`/`get_earnings_history`는 TTL이 없어 오래된 값을 반환할 수 있다"를 `추론`으로 두었고 `next.md` 체크리스트에도 미확인으로 남았다. `data/cached.py:87-97` 부근을 보면 두 메서드의 캐시 params에 날짜가 없다(`{"ticker", "limit"}`, `{"ticker"}`). 이것이 사실이면 추론이 아니라 코드로 확정할 수 있는 사실이다.
- 질문: `get_company_facts`와 `get_earnings_history`의 캐시 키 구성 요소는 무엇이며, 한 번 캐시된 뒤 `refresh=True` 외에 다시 FD를 호출하게 만드는 조건이 코드에 있는가?
- 답변 완료 조건: 두 메서드의 params 원문(`파일:라인`), `_cached_item`/`_cached_list`의 재사용 판단 분기 원문, `refresh`가 어디서 `True`로 설정되는지(호출처 `파일:라인` 또는 없음 확정). 결론은 "최초 캐시 값을 무기한 재사용한다" 또는 그 반대로 확정.

#### R1-Q5. PEAD 실적 이력(최신 N건)이 과거 기준일을 덮지 못할 때의 동작
- GUIDE 항목: Q2(미래 데이터 차단), Q1
- 왜 묻는가: `01-data.md` Q2 "미래 데이터 차단" 표는 PEAD가 `filing_date <= 기준일`만 고려한다고 적었지만, `data/client.py:186-201`의 `get_earnings_history`는 날짜 파라미터 없이 `ticker`, `limit`만 보낸다. 보고서는 PEAD 이력을 `limit=8`로 적었다(`01-data.md` Q1-1, `03-decision.md` 4-1). 그렇다면 FD가 최신 N건만 돌려줄 경우 오래된 백테스트 기준일에는 해당 시점의 이벤트가 응답에 없을 수 있는데, 보고서는 이 점을 다루지 않았다.
- 질문: PEAD가 실제로 요청하는 `limit` 값은 어디서 정해지며(기본값과 mandate/YAML에서 바꾸는 경로), 기준일 이전 이벤트가 응답 범위 밖에 있으면 `PEADModel.predict()`는 어떤 값을 반환하는가?
- 답변 완료 조건: `limit` 기본값과 전달 경로의 `파일:라인` 원문, `predict()`에서 `past`가 비었을 때의 분기 원문. FD가 최신순으로 N건을 주는지는 외부 동작이므로, 코드나 docstring에 서술이 없으면 그 부분만 "정적 확인 불가"로 분리해 적는다.

#### R1-Q6. 체결 전 refresh 평가의 기준일과 발생 조건
- GUIDE 항목: Q3(주기와 시점), Q4-2
- 왜 묻는가: `02-schedule.md` "세션 1회의 순서" 2단계와 `03-decision.md` 4-2 "T일 결정 → T+1일 체결 상세" 4행은 "직전 달력일이 결정일과 다르면 뷰를 다시 평가해서 체결"한다고 적었고, 같은 표의 "의미" 행에서 refresh가 캐시 적중한다는 해석을 `추론`으로 두었다. `previous_day()`가 달력일인지 세션인지, refresh의 `as_of`가 정확히 무엇인지가 보고서에 원문으로 없어서 "T 결정 → T+1 체결"이 언제 깨지는지 독자가 판단할 수 없다.
- 질문: `execute_decision()`에서 refresh 여부를 가르는 `cutoff`(`previous_day(session)`)는 어떻게 계산되며, refresh가 일어날 때 새 평가의 `as_of`와 주문에 쓰이는 비중은 원래 결정과 refresh 결정 중 어느 쪽인가?
- 답변 완료 조건: `data/sessions.py`의 `previous_day()` 원문, `pipeline/stages.py`의 `cutoff`/`effective` 분기 원문과 `파일:라인`, 주문 생성에 `effective.final_weights`가 쓰이는 줄. 금요일 결정 → 월요일 체결 같은 구체 예 1개로 흐름을 설명. 캐시 적중 여부는 refresh 평가의 프롬프트가 원래 평가와 같아지는 조건을 코드로 설명하거나, 실행 의존이면 정적 확인 불가 사유.

#### R1-Q7. CLI 백테스트의 기본 기간이 정해지는 위치
- GUIDE 항목: Q3(트리거), Q4-8(비용)
- 왜 묻는가: `03-decision.md` 4-8 표의 "백테스트(78주 기본 창, 주간)" 행은 근거로 `tui/shared.py:74`를 들고 `추론`으로 표기했다. 그런데 `02-schedule.md` 트리거 표는 `aihf backtest <mandate> --universe ...` CLI를 별도 트리거로 들었다. 78주가 TUI 기본값인지 CLI에도 적용되는지 보고서에서 구분되지 않는다.
- 질문: `aihf backtest` CLI 경로에서 시작일과 종료일의 기본값은 어디서 어떤 값으로 정해지는가? TUI의 78주 기본 창과 같은 값인가?
- 답변 완료 조건: `run.py`의 백테스트 인자 정의와 기본값 원문(`파일:라인`), `backtesting/fund.py`에서 기간을 해석하는 줄, `tui/shared.py:74` 원문. 두 경로의 값이 같은지 다른지 확정.

#### R1-Q8. PEAD가 이벤트 없음일 때 블렌딩에서 어떻게 처리되는가
- GUIDE 항목: Q4-3, Q4-5
- 왜 묻는가: `03-decision.md` 4-3 "기권/중립" 행은 "기권은 제외, 중립(0.0)은 투표에 포함"이라고만 적었다. `signals/pead.py`의 `_neutral()`은 `metadata` 없이 `value=0.0`을 반환하는 것으로 보이는데, 그렇다면 PEAD 단독 전략(`earnings-drift`)은 이벤트가 없는 대부분의 세션에 `flat_reason`이 되고, 예시 mandate(`deep-value 0.6 + earnings-drift 0.4`)에서 그 슬라이스 비중이 어떻게 되는지 보고서에 없다. 판단 결과 해석에 직접 영향을 주는 핵심 흐름이다.
- 질문: PEAD의 "이벤트 없음/기간 초과" 신호는 `blend_signals()`에서 기권으로 빠지는가, 0.0 투표로 들어가는가? 그리고 `earnings-drift` 슬라이스가 flat일 때 `assess_fund()`의 전략 네팅에서 그 슬라이스 몫(예시 mandate의 0.4)은 다른 전략에 재분배되는가, 현금으로 남는가?
- 답변 완료 조건: `_neutral()` 원문과 `blend_signals()`의 `abstained` 분기 원문(`파일:라인`), `stages.py`의 슬라이스 계산·네팅 줄 원문. 예시 mandate 기준으로 "PEAD 이벤트 없음" 세션의 최종 비중 합이 어떻게 되는지 공식으로 설명.

#### R1-Q9. 주간 리밸런스에서 PEAD가 보는 이벤트 범위
- GUIDE 항목: Q4-3
- 왜 묻는가: `03-decision.md` 4-3 숫자 규칙 표는 PEAD가 "이벤트가 기준일로부터 `signal_window_days=4`일 이내일 때만" 발화한다고 적었고, 같은 표의 리밸런스 행은 `weekly`가 ISO 주의 첫 세션에서만 결정한다고 적었다. 두 규칙을 합치면 주간 mandate에서 PEAD는 리밸런스 세션 직전 4일 안의 공시만 반영하는 것으로 읽히지만 보고서는 이를 연결하지 않았다.
- 질문: `PEADModel.predict()`가 호출되는 날짜는 리밸런스 세션의 `as_of`와 refresh의 `cutoff`뿐인가? 비리밸런스 세션에 PEAD가 호출되는 경로가 있는가?
- 답변 완료 조건: `pipeline/session.py`에서 `assess_fund`를 부르는 조건 원문, `stages.py`에서 모델 `predict`를 부르는 줄 원문(`파일:라인`). 다른 호출 경로가 없다면 `predict(` grep 범위를 적고 "없음 확정".

#### R1-Q10. 여러 전략에 같은 페르소나가 있을 때 호출 중복 여부
- GUIDE 항목: Q4-2, Q4-8
- 왜 묻는가: `03-decision.md` 4-8 표 첫 행은 "같은 페르소나가 두 전략에 있어도 프롬프트가 같으면 두 번째는 캐시 적중"이라고 적었다(`stages.py:52-54`). 이것이 디스크 `PromptCache` 적중을 뜻하는지, `assess_fund()`가 (종목, 모델) 단위로 신호를 한 번만 만들어 전략끼리 공유하는지 불분명하다. 호출 수 공식의 M("서로 다른 LLM 페르소나 수")이 맞는지가 여기에 달려 있다.
- 질문: `assess_fund()`는 같은 모델 이름이 여러 전략에 있을 때 `predict()`를 전략마다 호출하는가, 한 번 호출한 결과를 공유하는가? 전략별 YAML `params`가 다르면(예: 가중치 외 파라미터) 별도 인스턴스가 되는가?
- 답변 완료 조건: `stages.py`의 staff 구성과 호출 루프 원문, `fund/spec.py`의 모델 인스턴스 생성 줄 원문(`파일:라인`). 공유 방식(메모리 dict, 디스크 캐시, 없음) 중 하나로 확정.

#### R1-Q11. 기권 누적에 대한 경보·중단 장치 부재 확정
- GUIDE 항목: Q4-6
- 왜 묻는가: `03-decision.md` 4-6 표 아래 "주의" 문단은 "기권 비율에 대한 경보/중단 임계값은 없다(grep 결과 해당 없음)"고 하면서 검증 수준을 `추론`으로 표기했고 조사 범위(grep 패턴, 디렉터리)를 적지 않았다. `next.md` "분석 중 생긴 질문" 3번도 같은 문제다. GUIDE 4절은 "없음"에 조사 범위를 요구한다.
- 질문: `hedge_fund/` 어디에든 기권(`abstained`) 신호의 개수나 비율을 집계해 경보, 로그 이벤트, halt, flat 처리로 이어지는 코드가 있는가?
- 답변 완료 조건: `abstain`, `abstained`, `abstain_reason`의 모든 참조 위치 목록(`파일:라인`, 테스트 제외 여부 명시)과 각 참조가 판단·표시·저장 중 무엇인지 분류. 집계 로직이 없으면 "없음 확정"과 조사 범위. TUI에 기권을 표시하는 부분이 있으면 그 위치도 적는다.

#### R1-Q12. paper/live에서 blind 프롬프트를 켤 수 있는 경로
- GUIDE 항목: Q4-1
- 왜 묻는가: `00-overview.md` 6절 4번과 `03-decision.md` 4-2 "백테스트와 라이브의 동일성" 표는 "백테스트는 blind, paper는 unblind라 기록이 같을 수 없다"를 적으면서 "일치 조건" 해석을 `추론`으로 두었다. `fund/spec.py:199`는 `{**m.params, "blind": True}`로 params에 blind를 덮어쓰는데, 반대로 mandate YAML의 모델 `params`에 `blind: true`를 직접 넣으면 paper에서도 blind가 되는지는 보고서에 없다.
- 질문: paper `tick` 경로(`Fund(deployed.spec)`)에서 blind 렌더를 켤 수 있는 설정 경로(YAML `params`, CLI 플래그, 환경 변수)가 존재하는가?
- 답변 완료 조건: `LLMAgent.__init__`의 `blind` 인자 원문, `fund/spec.py`에서 YAML `params`를 모델 생성자에 넘기는 줄과 params 검증 규칙(`extra="forbid"` 등) 원문(`파일:라인`). 경로가 있으면 그 방법, 없으면 조사 범위와 함께 "없음 확정".

### 답변 (답변자)

#### R1-Q1 답변
- 결론: **없음 확정** (정렬 코드 없음). `get_financial_metrics()` 결과는 정렬 없이 FD 응답 순서 그대로 `build_snapshot()`에 들어가며, 코드는 "첫 행 = 최신"을 전제로만 쓴다. FD가 실제로 최신순을 주는지는 **정적 확인 불가**(외부 응답)이므로 아래에 호출 지점과 경우의 수를 분리해 적는다. 보고서 서술(최신순)은 코드의 전제와 일치하지만 "코드가 보장한다"는 뜻은 아니다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/data/client.py:114-120` | `FDClient.get_financial_metrics` | `data = self._get("/financial-metrics/", {"ticker": ticker, "filing_date_lte": end_date, "period": period, "limit": limit}, ...)` / `return [FinancialMetrics(**row) for row in data] if data else []` — `order`/`sort` 파라미터 없음, 반환 후 정렬 없음 | 코드 확인 |
  | `hedge_fund/data/client.py:244-249` | `_get` 페이지 루프 | `rows.extend(body.get(response_key) or [])` — 다음 페이지를 뒤에 이어 붙일 뿐 재정렬 없음 | 코드 확인 |
  | `hedge_fund/data/cached.py:66-71, 148-149` | `CachedDataClient.get_financial_metrics` / `_cached_list` | `return [model_cls(**row) for row in hit["data"]]` — 저장된 순서 그대로 복원 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:195-197` | `build_snapshot` | `metrics = data_client.get_financial_metrics(ticker, as_of, period="ttm", limit=periods,)` 직후 `len(metrics) < MIN_PERIODS` 검사만 있고 정렬 없음 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:209-212, 225, 230-231` | 행 변환과 최신값 | `rows = [PeriodFundamentals(...) for m in metrics]`, `periods=rows`, `debt_to_equity_latest=metrics[0].debt_to_equity`, `market_cap_latest=metrics[0].market_cap` | 코드 확인 |
  | `hedge_fund/features/snapshot.py:259-267, 285-288` | 순서 전제를 쓰는 집계 | `latest = periods[0].earnings_per_share` / `prior = periods[4].earnings_per_share`; `_trend` docstring `"""Latest minus oldest (values arrive newest first)."""` → `xs[0] - xs[-1]` | 코드 확인 |
  | `hedge_fund/features/snapshot.py:54`, `features/test_snapshot.py:51` | 순서 가정 서술 | `"""What an analyst may know about *ticker* as of *as_of*. Newest first."""` / 테스트 픽스처 docstring `"""n periods, newest first, quarter-spaced."""` | 코드 확인 |
  | `hedge_fund/data/test_client.py:43` | 실 API 테스트(출력만, assert 없음) | `print(f"  {ticker} metrics: {len(metrics)} periods  [{periods[-1]} → {periods[0]}]")` — 오래된 → 최신 순으로 `periods[0]`을 최신으로 읽는 출력 | 코드 확인 |
  | `hedge_fund/data/protocol.py:14-25` | `DataClient` 계약 | docstring은 "point-in-time: return only data that was publicly filed by *end_date*"만 요구하고 정렬 순서는 명시하지 않음 | 코드 확인 |

- 동작 설명: `LLMAgent.predict()` → `build_snapshot()`(`snapshot.py:195`) → `CachedDataClient.get_financial_metrics()` → (캐시 미스 시) `FDClient.get_financial_metrics()` → `_get()`이 FD 응답 리스트를 그대로 반환 → `build_snapshot()`이 리스트 인덱스로 `metrics[0]`(최신), `periods[4]`(t-4), `xs[0]/xs[-1]`(최신/최오래)을 사용 → `render()`가 같은 순서로 행을 출력하고 blind는 `t-{i}`를 인덱스로 붙인다(`snapshot.py:164-165`). 경우의 수: (a) FD가 `filing_date` 내림차순으로 주면 모든 집계가 의도대로 동작한다. (b) 오름차순이거나 무순서면 `debt_to_equity_latest`, `market_cap_latest`, `gross_margin_trend`, `eps_growth_yoy`, `t-0` 라벨, blind의 `oldest = self.periods[-1]`(`snapshot.py:141`)이 전부 뒤집히며, 코드 어디에서도 이를 감지하거나 예외를 내지 않는다. 어느 쪽인지는 FD `/financial-metrics/` 응답에 달려 있고 이 저장소에는 서버 구현이 없다.
- 조사 범위: `hedge_fund/` 전체 `*.py`에 `grep -rnE "sort|reverse|newest|most recent|descending|order_by|\border\b"` — 정렬은 `run.py:275,279`, `paper/ledger.py:51`, `paper/deployed.py:69,97`, `pipeline/stages.py:108`, `pipeline/execution.py:38`, `pipeline/session.py:143,145`, `brokers/*`, `event_study/__main__.py:115`, `backtesting/engine.py:23`, `data/sessions.py:30`(가격 종가 dict)에만 있고 재무지표에는 없음. `data/`, `features/`에서 `grep -rniE "newest|latest first|most-recent|first row|\[0\]"` 확인. 직접 열어 읽은 파일: `data/client.py`, `data/cached.py`, `data/protocol.py`, `data/models.py`, `features/snapshot.py`, `features/test_snapshot.py`, `data/test_client.py`.

#### R1-Q2 답변
- 결론: **확정** — 코드는 가격으로 다시 계산하지 않고 FD `/financial-metrics/` 행의 `market_cap`, `price_to_earnings_ratio`를 필드 이름 그대로 복사한다. 코드에는 이 값의 기준 시점(공시일 종가인지, 보고기간 말인지 등)에 대한 서술이 없고, 기준 시점 자체는 **정적 확인 불가**(FD API 정의에 의존, 호출 지점 `data/client.py:114`). 따라서 보고서 `01-data.md`의 "밸류에이션이 최대 한 분기쯤 낡을 수 있다"는 `추론` 표기가 맞고, 코드가 보장하는 사실은 "가장 최근 공시 행의 값을 쓴다"까지다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/data/models.py:56,58` | `FinancialMetrics` | `market_cap: float \| None = None` / `price_to_earnings_ratio: float \| None = None` — 그냥 응답 필드. 필드 주석에 기준 시점 서술 없음(docstring은 36-41행 "Financial ratios and per-share metrics from /financial-metrics") | 코드 확인 |
  | `hedge_fund/data/client.py:114-120` | `get_financial_metrics` | `FinancialMetrics(**row)`로 응답 행 그대로 생성 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:209-212` | `rows` 생성 | `PeriodFundamentals(**m.model_dump(include=set(PeriodFundamentals.model_fields)))` — `market_cap`, `price_to_earnings_ratio`를 복사 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:231` | `market_cap_latest` | `market_cap_latest=metrics[0].market_cap` (프롬프트 요약 줄 117행 `Market cap (latest filed): ...`) | 코드 확인 |
  | `hedge_fund/features/snapshot.py:204-206` | 주석 | `# Market cap comes from the most recent FILED metrics row. Deliberately NOT data_client.get_market_cap(): that prefers company_facts.market_cap, which is latest-only — lookahead in a backtest.` | 코드 확인 |
  | `hedge_fund/features/snapshot.py:129-130, 166` | 행 렌더 | `{_fmt(p.market_cap)} \| {_fmt(p.price_to_earnings_ratio)}` (blind는 P/E만, 시총 제외) | 코드 확인 |

- 동작 설명: `build_snapshot()`은 `get_financial_metrics(..., period="ttm", limit=20)`로 받은 각 행의 두 필드를 가공 없이 `PeriodFundamentals`에 넣고(`snapshot.py:209-212`), 첫 행의 시총을 `market_cap_latest`로 요약에 쓴다. 프롬프트에는 "Market cap (latest filed)"라는 라벨만 붙는다(`snapshot.py:117`). P/E는 각 행 값 그대로다. 값이 어떤 날의 가격으로 계산됐는지를 정하는 코드는 이 저장소에 없다. 추가 발견(보고서에 없던 사실): `FDClient.get_market_cap()`(`data/client.py:207-215`)은 `facts.market_cap`을 읽지만 `CompanyFacts` 모델(`data/models.py:154-171`)에는 `market_cap` 필드가 없고 `extra="ignore"`(157행)이다. 이 메서드의 호출처는 `get_market_cap` 정의·캐시 래퍼 외에 `hedge_fund/` 안에 없으므로 현재 실행 경로에서는 쓰이지 않는다.
- 조사 범위: `grep -rn "market_cap\|price_to_earnings" --include='*.py' hedge_fund` (테스트 제외) — `data/models.py`, `data/client.py:207-214`, `data/cached.py:106-110`, `data/protocol.py:88`, `features/snapshot.py`, `features/breakpoints.py:77-92`(시총 입력, `size_percentile`)만 해당. 값을 가격 × 주식 수로 재계산하는 코드는 없음.

#### R1-Q3 답변
- 결론: **없음 확정** — 클라이언트 쪽에서 NaN/Inf를 검사하거나 None으로 바꾸는 코드는 없다. 서버가 실제로 NaN을 `null`로 정리하는지는 **정적 확인 불가**(외부 응답, 호출 지점 `data/client.py:114-120`; 코드에는 docstring 한 줄뿐). 아래 흐름은 "NaN이 들어왔다고 가정한 경우"의 코드 동작이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/data/models.py:36-41` | `FinancialMetrics` docstring | `All ratio/metric fields are nullable (NaN/Inf sanitised to null).` — 서술일 뿐, validator 없음. 필드는 모두 `float \| None = None` (56-106행), `model_config = _IGNORE`(43행)는 `extra="ignore"`만 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:270-277` | `_fmt` | `if v is None: return "-"` / `if abs(v) >= 1e9: ...` / `return f"{v:.2f}"` — NaN이면 비교가 모두 False라 `f"{nan:.2f}"` = `"nan"` 문자열이 프롬프트에 들어감 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:280-282` | `_avg` | `xs = [v for v in values if v is not None]` / `round(sum(xs) / len(xs), 4)` — None만 거르므로 NaN 하나가 평균을 NaN으로 만듦 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:285-299` | `_trend`, `_cagr` | None만 거름. `_cagr`의 `xs[-1] <= 0 or xs[0] <= 0`는 NaN에서 False라 통과해 NaN 결과 | 코드 확인 |
  | `hedge_fund/features/snapshot.py:259-267` | `_eps_growth_yoy` | `prior <= 0`이 NaN에서 False → `round(latest / prior - 1, 4)` NaN | 코드 확인 |
  | `hedge_fund/features/snapshot.py:247-256` | `_per_share_index` | `base <= 0`이 NaN에서 False → `"nan"` 문자열 | 코드 확인 |

- 동작 설명: `FDClient._get()`은 `resp.json()`을 그대로 `FinancialMetrics(**row)`로 만든다(`client.py:241-242, 120`). pydantic 모델에는 `field_validator`가 없어 float 필드는 들어온 값을 받는다. 이후 집계 함수는 `None`만 걸러내므로 NaN/Inf가 있으면 집계가 NaN/Inf가 되고, `_fmt`가 `"nan"`/`"inf"`(1e9 이상이면 `inf` 비교가 True라 `"infB"`)를 문자열로 렌더한다. 이를 예외로 올리는 검사는 `build_snapshot`에 없다. 경우의 수: (a) FD가 docstring대로 서버에서 null로 정리하면 위 코드 경로는 발생하지 않는다. (b) 정리하지 않으면 위처럼 프롬프트에 `nan`이 들어간다. 어느 쪽인지는 FD 응답이 결정한다.
- 조사 범위: `grep -rniE "validator|isfinite|isnan|\bnan\b|\binf\b" hedge_fund --include='*.py'` — `isfinite`는 `brokers/sim.py:39`, `data/sessions.py:28`, `llm/client.py:120,220`, `llm/contract.py:115`, `pipeline/stages.py:114,140,150,188`, `portfolio/construction.py:52,55,67,76`, `risk/limits.py:67-75`, `tui/app.py:2587`에만 있고 모두 가격/비중/LLM 값 검사다. `data/models.py`, `data/client.py`, `features/snapshot.py`에는 없음. 추가로 `grep -rniE "allow_inf_nan|inf_nan|BeforeValidator|model_validator"` 결과 없음. `QuantModel._safe_float`(`signals/base.py:57-66`)은 NaN/Inf를 0.0으로 바꾸는 헬퍼이지만 `grep -rn "_safe_float" hedge_fund --include='*.py'` 결과 정의(`base.py:58`)와 테스트(`signals/test_signals.py:42-43`)뿐이고 재무지표 경로에서는 호출되지 않는다.

#### R1-Q4 답변
- 결론: **확정** — 두 메서드의 캐시 키에는 날짜가 없고, 한 번 파일로 저장되면 `refresh=True`가 아닌 한 **무기한 재사용**한다. 그리고 `hedge_fund/` 어디에서도 `refresh=True`로 `CachedDataClient`를 만들지 않으므로, 이 저장소의 실행 경로(CLI, TUI, paper tick)에서는 디스크 캐시 파일을 지우지 않는 한 다시 FD를 부르지 않는다. 보고서 `01-data.md` Q2 "운영 시 주의"의 `추론`은 코드로 확정된다(FD가 이후 다른 값을 돌려주는지는 외부 사항).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/data/cached.py:87-92` | `get_earnings_history` | `{"ticker": ticker, "limit": limit}` — 날짜 없음 | 코드 확인 |
  | `hedge_fund/data/cached.py:94-98` | `get_company_facts` | `self._cached_item("get_company_facts", CompanyFacts, {"ticker": ticker}, ...)` — 날짜 없음 | 코드 확인 |
  | `hedge_fund/data/cached.py:116-118` | `_key` | `canonical = json.dumps(params, sort_keys=True)` / `sha256(f"{method}\|{canonical}")[:24]` | 코드 확인 |
  | `hedge_fund/data/cached.py:120-129` | `_read` | `if self._refresh: return None` / `path.exists()`가 아니면 None / 파일이 있으면 `json.loads` — 만료 검사 없음 | 코드 확인 |
  | `hedge_fund/data/cached.py:158-165` | `_cached_item` | `hit = self._read(key)` / `if hit is not None: return model_cls(**hit["data"]) if hit["data"] is not None else None` — 가격 전용 TTL 분기 없음 | 코드 확인 |
  | `hedge_fund/data/cached.py:135-149` | `_cached_list` | 가격 일봉(`method == "get_prices" and params.get("interval") == "day"`)만 `complete` 검사로 `hit = None` 처리. `get_earnings_history`는 `if hit is not None: return [model_cls(**row) ...]`로 바로 반환 | 코드 확인 |
  | `hedge_fund/data/cached.py:43-51` | `__init__` | `refresh: bool = False` 기본값 | 코드 확인 |
  | `hedge_fund/run.py:197, 258`; `hedge_fund/tui/app.py:1679, 2211, 2249, 2930, 2978, 3013` | 인스턴스 생성 지점 | 전부 `CachedDataClient(raw)` — `refresh` 인자 없음 | 코드 확인 |

- 동작 설명: 첫 호출에서 `_read`가 None → `fetch()` → `_write(key, ...)`로 `~/.hedge-fund/cache/data/<해시>.json` 저장(`cached.py:37, 131-133, 163-165`). 이후 같은 `(ticker, limit)` 또는 `ticker`로 부르면 키가 같아 `_read`가 그 파일을 읽고 FD를 부르지 않는다. 키에 시점이 없으므로 `get_company_facts`는 `sector`/`industry`가 최초 조회값으로, `get_earnings_history`는 최초 조회 시점의 "최신 N건"으로 고정된다. 파생 효과(코드로 확정): paper tick은 매번 새 `Fund`와 새 `CachedDataClient`를 만들지만(`paper/tick.py:132`, `run.py:258`) 디스크 파일은 남으므로, PEAD(`signals/pead.py:120`)는 최초 조회 이후 새로 올라온 8-K를 보지 못한다. (`PEADModel._cache` 인메모리 캐시 `pead.py:54, 117-121`도 있지만 프로세스 안에서만 유효.) 반대로 `get_financial_metrics`는 키에 `end_date`가 있어 날짜가 바뀌면 새 호출이므로 이 문제가 없다(`cached.py:66-71`).
- 조사 범위: `grep -rn "CachedDataClient(\|refresh=" hedge_fund --include='*.py'`(테스트 제외) — 위 8곳 생성 지점 전부 `refresh` 미지정, `refresh=`는 `cached.py:13,47,51,121`에만. 캐시 파일 삭제/만료 코드: `grep -rnE "unlink|rmtree|CACHE_DIR|cache_dir|st_mtime|ttl|TTL|max_age"` — `features/breakpoints.py:111-121`(ME breakpoints CSV만), `tui/app.py:527-539`(mandate/paper 삭제)뿐이고 `~/.hedge-fund/cache/data/` 삭제 코드는 없음. `data/cached.py` 전체를 직접 읽음.

#### R1-Q5 답변
- 결론: **확정** (limit 전달 경로와 `past`가 비었을 때의 값) + 분리된 하위 항목 **정적 확인 불가**(FD `/earnings/`가 최신순 N건을 주는지). `PEADModel`은 `earnings_limit`(기본 8)을 FD에 보내고, 기준일 이전 이벤트가 응답 안에 하나도 없으면 `_neutral()`(`value=0.0`, `metadata` 없음)을 반환한다. 보고서가 이 점을 다루지 않은 것은 맞다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/signals/pead.py:42-50` | `PEADModel.__init__` | `earnings_limit: int = 8, signal_window_days: int = 4, announcement_only: bool = True` / `self._earnings_limit = earnings_limit` | 코드 확인 |
  | `hedge_fund/signals/pead.py:117-121` | `_qualifying_events` | `records = data_client.get_earnings_history(ticker, limit=self._earnings_limit)` / `self._cache[ticker] = records` — 호출은 날짜 인자 없음 | 코드 확인 |
  | `hedge_fund/data/client.py:197-200` | `FDClient.get_earnings_history` | `self._get("/earnings/", {"ticker": ticker, "limit": limit}, response_key="earnings")` — 날짜 필터 파라미터 없음 | 코드 확인 |
  | `hedge_fund/signals/pead.py:63-67` | `predict` | `past = [e for e in events if _parse_date(e["filing_date"]) <= as_of]` / `if not past: return self._neutral(ticker, date)` | 코드 확인 |
  | `hedge_fund/signals/pead.py:100-101` | `_neutral` | `return Signal(model_name=self.name, ticker=ticker, date=date, value=0.0)` | 코드 확인 |
  | `hedge_fund/signals/pead.py:124-131` | 사전 필터 | `if not r.filing_date or not r.quarterly: continue` / `surprise not in ("BEAT", "MISS")` / `self._announcement_only and r.source_type != "8-K"` → 응답 8건 중 8-K이면서 BEAT/MISS인 것만 남음 | 코드 확인 |
  | `hedge_fund/fund/spec.py:25, 199-200` | `ModelSpec.params`, `Fund.__init__` | `params: dict[str, Any] = Field(default_factory=dict, description="constructor kwargs for the model")` / `staff.append(cls(**params))` — YAML에서 `params: {earnings_limit: N}`로 변경 가능 | 코드 확인 |
  | `hedge_fund/strategies/earnings-drift.yaml`, `hedge_fund/fund/example.yaml:24-27` | PEAD 설정 | `models:\n  - name: pead` — `params` 없음 → 기본 8 | 코드 확인 |
  | `hedge_fund/data/cached.py:87-92` | 캐시 키 | `{"ticker": ticker, "limit": limit}` — Q4와 같이 날짜 없음 | 코드 확인 |

- 동작 설명: `limit`의 기본값 8은 `PEADModel.__init__`(`pead.py:45`)에서 정해지고, YAML `models[].params.earnings_limit`로 바꾸면 `Fund.__init__`이 `PEADModel(earnings_limit=N)`을 만든다(`spec.py:199-200`; PEAD 생성자는 keyword-only라 알 수 없는 키는 TypeError). `predict()`는 ticker별로 한 번만 `get_earnings_history`를 부르고(`pead.py:117-121`) 모든 기준일에서 같은 `records`를 재사용한다. 따라서 (a) FD가 "최신 N건"을 주는 경우: 8건은 같은 분기에 8-K/10-Q가 겹쳐 있어 대략 몇 개 분기분이므로, 이 범위보다 오래된 기준일(과거 백테스트 구간 앞쪽)에서는 `past`가 비어 `_neutral`(0.0)이 되고, 이는 "이벤트 없음"과 구분되지 않는다. (b) FD가 오래된 순 N건 등 다른 순서를 주면 반대로 최근 구간이 비게 된다. FD가 어떤 순서·범위로 N건을 자르는지는 `data/client.py:197`의 외부 응답이며 이 저장소에 서술이 없다(`EarningsRecord` docstring `data/models.py:234-240`은 "flat history mode"만 설명). 페이지네이션: `_get`(`client.py:244-249`)은 `next_page_url`이 있으면 끝까지 이어 붙이지만 요청에 `limit`이 들어 있어 서버가 limit까지만 준다는 것은 `get_earnings` docstring(`client.py:177-179`, "without a limit the pagination loop in _get would walk the ticker's entire feed")이 간접 서술할 뿐이다. 반환값은 `Signal(value=0.0)`이고 `metadata`가 비어 있으므로 `abstained`가 아니다(Q8 참조).
- 조사 범위: `grep -rn "get_earnings_history\|earnings_limit" hedge_fund --include='*.py'` — 호출처는 `signals/pead.py:120`, `event_study/engine.py:154`(별도 event study), `data/protocol.py:82`, `data/client.py:186`, `data/cached.py:87`. `earnings_limit`을 설정하는 YAML(`strategies/*.yaml`, `fund/example.yaml`)에는 없음.

#### R1-Q6 답변
- 결론: **확정** — `cutoff`는 `session`의 **달력상 전날**이고, 원래 결정일과 다르면 `assess_fund(fund, cutoff, ...)`로 새로 평가한 `effective`로 주문을 만든다. 체결 비중은 **refresh 결정의 `final_weights`**다. 같은 프롬프트가 되어 LLM 캐시가 적중하는지는 그 날짜 사이에 새 공시가 있었는지에 달려 **정적 확인 불가**(FD 응답 의존)이고, PEAD는 코드상 결과가 달라질 수 있다(아래).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/data/sessions.py:17-18` | `previous_day` | `return (date.fromisoformat(day) - timedelta(days=1)).isoformat()` — 달력일 -1, 거래일 아님 | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:125-126` | `execute_decision` 검사 | `if session <= original.as_of or session > completed_through(): raise ValueError(...)` | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:129-132` | cutoff/effective | `cutoff = previous_day(session)` / `effective = original if cutoff == original.as_of else assess_fund(fund, cutoff, data_client, original.universe,)` | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:134-136` | 목표 | `validate_targets(spec, effective.strategies, effective.final_weights)` / `targets = {t: w for t, w in effective.final_weights.items() if w != 0}` | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:142` | 주문 생성 | `orders = build_orders(targets, held, marks, equity_before)` — `marks`는 체결일 종가(`exact_marks`, 137행) | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:157-165` | 기록 | `fields = effective.model_dump(exclude={"as_of", "marks"})` / `as_of=original.as_of` / `original_assessment=original...`, `refreshed_assessment=effective...` | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:43-45, 173-189` | `assess_fund`/`_mark_prices` | `if as_of > completed_through(): raise ...`; `start = (_date.fromisoformat(as_of) - timedelta(days=_MARK_LOOKBACK_DAYS))` (7일 룩백, 일요일이어도 금요일 종가를 찾음) | 코드 확인 |
  | `hedge_fund/pipeline/session.py:137-139, 148-149` | `advance` | `if state.pending is not None: executed = execute_decision(fund, state.pending, session, broker, data_client)` / `decision = assess_fund(fund, session, data_client, universe) if rebalance else None` | 코드 확인 |
  | `hedge_fund/features/snapshot.py:87-94, 195-197` | 렌더와 데이터 호출 | 렌더에 `as_of` 없음 → 데이터가 같으면 프롬프트 동일. 단 `get_financial_metrics`는 `as_of`가 키에 들어가(`cached.py:66-71`) 날짜가 다르면 FD 호출은 다시 발생(데이터 캐시 미스, LLM 캐시와 별개) | 코드 확인 |
  | `hedge_fund/signals/llm_agent.py:74-80` | LLM 캐시 | `key = (cache_key(...) if callable(cache_key) else prompt_key(self.name, self._llm.model, system, user))` / `cached = self._cache.get(key)` / `if cached is not None and "parsed" in cached: return self._to_signal(...)` | 코드 확인 |
  | `hedge_fund/signals/pead.py:73-75` | PEAD 창 | `if (as_of - filed).days > self._signal_window_days: return self._neutral(ticker, date)` | 코드 확인 |

- 동작 설명: 발생 조건 = 결정 세션 `T`와 다음 체결 세션 `S`에 대해 `S`의 전날(달력)이 `T`가 아닐 때. 즉 주말·휴장을 사이에 둔 경우다. 예: 일간 mandate에서 금요일 2026-10-02에 결정(`advance`가 `session.py:149`로 `assess_fund(..., "2026-10-02")`) → 다음 세션은 월요일 2026-10-05 → `cutoff = previous_day("2026-10-05") = "2026-10-04"`(일요일) ≠ `"2026-10-02"` → `assess_fund(fund, "2026-10-04", ...)`을 다시 실행해 `effective`를 만들고, 그 `final_weights`로 월요일 종가에 주문한다. 월요일 결정 → 화요일 체결이면 `cutoff == original.as_of`라 재평가가 없다. 주간 mandate(첫 거래일=월요일)는 보통 재평가가 없고, 월요일이 휴장이라 화요일에 결정한 뒤 수요일 체결도 전날=결정일이라 없다. 금요일이 주의 첫 세션이거나 월간 mandate의 첫 세션이 금요일인 경우처럼 간격이 2일 이상일 때만 refresh한다. paper TUI도 같은 조건을 미리 계산해 `previous_day(due) != state.pending.as_of`일 때 그 날짜를 warm 대상에 넣는다(`tui/app.py:2225-2227`). "캐시 적중"은 `T`와 `cutoff` 사이에 새 `filing_date`가 없어 `metrics` 행이 같은 LLM 페르소나에 한해 성립한다. PEAD는 프롬프트가 없고 `as_of`가 이벤트 창(4일)에 직접 들어가므로 금요일엔 발화하던 이벤트가 일요일엔 창 밖이 되어 결과가 달라질 수 있다(예: 화요일 공시 → 금요일 diff 3일 발화, 일요일 diff 5일 중립). 그러므로 `03-decision.md`의 "캐시 적중 가능성 높음"은 LLM 페르소나에만 해당하며 PEAD는 해당하지 않는다(보고서 보완 필요).
- 조사 범위: `grep -rn "assess_fund\|execute_decision" hedge_fund --include='*.py'` — 호출처는 `session.py:139,149`, `stages.py:130`뿐(나머지는 export/주석/테스트). `previous_day` 사용처는 `stages.py:129`, `backtesting/fund.py:46`(워밍 스케줄), `tui/app.py`.

#### R1-Q7 답변
- 결론: **확정** — CLI `aihf backtest`와 TUI는 같은 상수 `_BACKTEST_WEEKS = 78`을 쓴다. CLI는 `tui/shared.py`에서 import해서 쓰므로 기본 창은 두 경로가 같다. 기본 종료일은 "마지막 완료 세션"이다. 보고서 `03-decision.md` 4-8의 `추론` 표기는 78주 값 자체에 관한 한 코드로 확정되고, "고유 프롬프트 수 ≈ 6~7회"만 가정이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/tui/shared.py:74` | `_BACKTEST_WEEKS` | `_BACKTEST_WEEKS = 78  # ~18 months of history for the default backtest window` | 코드 확인 |
  | `hedge_fund/run.py:68` | import | `from hedge_fund.tui.shared import _BACKTEST_WEEKS` | 코드 확인 |
  | `hedge_fund/run.py:126-127` | 인자 | `backtest.add_argument("--start", help=f"first session YYYY-MM-DD (default: {_BACKTEST_WEEKS} weeks before --end)")` / `backtest.add_argument("--end", help="last session YYYY-MM-DD (default: the latest completed session)")` | 코드 확인 |
  | `hedge_fund/run.py:189-190` | `_backtest` | `end = args.end or completed_through()` / `start = args.start or (_date.fromisoformat(end) - timedelta(weeks=_BACKTEST_WEEKS)).isoformat()` | 코드 확인 |
  | `hedge_fund/tui/app.py:2866` | TUI 기본값 | `start.value = (today - timedelta(weeks=_BACKTEST_WEEKS)).isoformat()` | 코드 확인 |
  | `hedge_fund/data/sessions.py:12-14` | `completed_through` | `return (datetime.now(NEW_YORK).date() - timedelta(days=1)).isoformat()` — 뉴욕 기준 어제 | 코드 확인 |
  | `hedge_fund/backtesting/fund.py:51-59, 117-123` | 기간 해석 | `closes = session_closes(data, benchmark, start, end)` → 벤치마크 일봉이 있는 날만 세션. `session_closes`는 `end = min(end, completed_through())`(`sessions.py:22`) | 코드 확인 |

- 동작 설명: `_backtest()`가 `start`, `end`를 정하고(`run.py:189-190`) `backtest_fund(fund, start, end, ...)`(`run.py:204`)로 넘긴다. 이후 `session_closes`가 벤치마크(기본 SPY, `spec.py:90`) 일봉으로 거래일 격자를 만들고 `rebalance_grid`가 cadence(기본 weekly, `spec.py:86`)에 따라 리밸런스일을 고른다. 78주 / 주간이면 리밸런스 ≈ 78회이며, 벤치마크 데이터가 없는 날은 격자에서 빠진다.
- 조사 범위: `grep -rn "_BACKTEST_WEEKS" hedge_fund` — `tui/shared.py:74`, `run.py:68,126,190`, `tui/app.py:93,2866`. `backtest` 서브커맨드 인자는 `run.py:118-128`, 본문 `run.py:183-210`을 직접 읽음.

#### R1-Q8 답변
- 결론: **확정** — PEAD의 "이벤트 없음/창 초과"는 기권이 아니라 **0.0 투표**로 블렌딩에 들어간다. `earnings-drift`처럼 PEAD 단독 전략에서 모든 종목이 0.0이면 그 전략은 `flat_reason="no_eligible_positions"`이 되고, 그 슬라이스 몫은 **다른 전략으로 재분배되지 않고 현금**으로 남는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/signals/pead.py:100-101` | `_neutral` | `return Signal(model_name=self.name, ticker=ticker, date=date, value=0.0)` — `metadata` 기본값 `{}` | 코드 확인 |
  | `hedge_fund/models.py:27` | `Signal.metadata` | `metadata: dict[str, Any] = Field(default_factory=dict)` | 코드 확인 |
  | `hedge_fund/portfolio/construction.py:69-70` | 기권 분기 | `if signal.metadata.get("abstained") is True: continue` — `{}`는 `get`이 None이라 통과하지 않음 | 코드 확인 |
  | `hedge_fund/portfolio/construction.py:71-75` | 투표 합산 | `weighted_sum[ticker] += weight * value` / `weight_total[ticker] += weight` — 0.0도 분모에 들어감 | 코드 확인 |
  | `hedge_fund/portfolio/construction.py:80-82` | 확신도/점수 | `convictions = {t: weighted_sum[t] / weight_total[t] if weight_total.get(t) else 0.0 ...}` / `scores = {t: max(convictions[t], 0.0) + (min(short_assessments[t], 0.0) ...` | 코드 확인 |
  | `hedge_fund/portfolio/construction.py:96-99` | 총합 0 처리 | `gross = sum(abs(score) ...)` / `if gross < WEIGHT_TOLERANCE: flat_reason = "no_eligible_positions"` → `weights = dict.fromkeys(tickers, 0.0)`(83행) | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:55, 68-70` | 슬라이스와 네팅 | `total_slice = sum(s.weight for s, _ in fund.strategies)` / `slice_ = strategy.weight / total_slice` / `netted[ticker] += slice_ * weight` — 분모는 전략 가중치 합으로 고정, flat 전략이 있어도 불변 | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:76-78` | 기록 | `flat_reason=blend.flat_reason` | 코드 확인 |
  | `hedge_fund/risk/limits.py:8-9`, `limits.py:94-100` | 재분배 없음 | `Exposure removed by a clamp is NOT redistributed to other names; it stays in cash.` — 리스크 단계는 축소만 하고 확대하지 않음 | 코드 확인 |
  | `hedge_fund/tui/app.py:1252` | 표시 | `"...: zero exposure — {_FLAT_REASONS[strategy.flat_reason]}. Allocated capital remains unused."` | 코드 확인 |
  | `hedge_fund/fund/example.yaml:14-27` | 예시 mandate | `deep-value` weight 0.6 (graham 2.0 + buffett + munger, long_only), `earnings-drift` weight 0.4 (pead, long_short), gross_target 기본 1.0(`spec.py:40`) | 코드 확인 |

- 동작 설명: PEAD 이벤트가 없거나 창(4일)을 넘으면 `_neutral`(0.0, abstained 없음)이다. `blend_signals`에서 이 신호는 `weight_total`에 가중치만큼 들어가 `conviction = 0 / w = 0.0`이 된다. 단독 모델 전략이면 모든 종목 score가 0이라 `gross < 1e-9` → `flat_reason="no_eligible_positions"`, 비중 전부 0. 예시 mandate에서 `slice_`는 deep-value 0.6/1.0 = 0.6, earnings-drift 0.4/1.0 = 0.4. 최종 네팅 비중은 `netted[t] = 0.6 × w_dv[t] + 0.4 × w_pead[t]`이고, PEAD flat이면 `w_pead = 0`이므로 `Σ|netted| = 0.6 × Σ|w_dv| = 0.6 × 1.0 = 0.6` (deep-value에 점수가 있을 때). 나머지 0.4는 `apply_limits`가 채우지 않으므로 현금이다. 이후 종목 상한 0.25와 총노출 1.0이 `limits.py:82-100`에서 적용된다. 다만 한 전략에 PEAD와 다른 모델이 함께 있으면 PEAD의 0.0은 기권이 아니라 투표이므로 평균을 희석한다(기권이어야 제외되는 것은 `construction.py:69-70`이 증명). 이벤트가 있으면 ±1.0이고 PEAD 모델 `investment_approach = "long_short"`(`pead.py:40`)라 short도 허용된다.
- 조사 범위: `grep -n "abstain" -r hedge_fund --include='*.py'` — 기권 분기는 `construction.py:69`와 LLM `_abstain`(`llm_agent.py:196-204`)뿐. PEAD에는 `abstained`를 세팅하는 코드 없음(`pead.py` 전체 읽음). `grep -n "flat_reason" -r`로 사용처 확인.

#### R1-Q9 답변
- 결론: **확정** — 운영 경로에서 `PEADModel.predict()`는 `assess_fund()` 한 곳(`pipeline/stages.py:62`)에서만 불리고, `assess_fund()`는 (1) 리밸런스 세션의 `advance`(`session.py:149`)와 (2) 체결 전 refresh(`stages.py:130`)에서만 불린다. 즉 주간 mandate에서는 리밸런스 세션 `as_of`와 refresh `cutoff` 두 날짜뿐이다. 이 밖에 TUI warm과 레거시 `BacktestEngine`, `event_study`가 별도 경로로 PEAD를 부르지만 펀드의 결정에는 쓰이지 않는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/pipeline/session.py:148-149` | `advance` | `rebalance = is_rebalance_session(session, state.last_session, spec.rebalance)` / `decision = assess_fund(fund, session, data_client, universe) if rebalance else None` | 코드 확인 |
  | `hedge_fund/pipeline/session.py:201-209` | `is_rebalance_session` | `if cadence == "daily" or last_session is None: return True` / `return _period(session, cadence) != _period(last_session, cadence)` — weekly는 ISO 주 | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:58-62` | 모델 호출 | `for strategy, staff in fund.strategies:` / `for ticker in tradeable:` / `for model in staff:` / `signals.append(model.predict(ticker, as_of, data_client))` | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:129-132` | refresh | `assess_fund(fund, cutoff, data_client, original.universe,)` | 코드 확인 |
  | `hedge_fund/signals/pead.py:73-75` | 창 판정 | `if (as_of - filed).days > self._signal_window_days: return self._neutral(...)` | 코드 확인 |
  | `hedge_fund/tui/app.py:2254, 3021` | TUI warm | `desk.settle(model.predict(ticker, as_of, fd))` / `model.predict(ticker, as_of, fd)` — 캐시 채우기용(`except Exception: pass`), 결정과 무관 | 코드 확인 |
  | `hedge_fund/backtesting/engine.py:132` | 레거시 단일 모델 엔진 | `signal = model.predict(ticker, d, data_client)` — 거래일마다 호출 | 코드 확인 |
  | `hedge_fund/event_study/engine.py:154` | 이벤트 스터디 | `data_client.get_earnings_history(...)` 직접 호출 (predict 아님) | 코드 확인 |

- 동작 설명: 주간 mandate에서 비리밸런스 세션은 `decision=None`이라 `assess_fund`가 불리지 않는다(`session.py:149`). 따라서 PEAD는 "리밸런스 세션 `as_of` 기준 직전 4일 이내 8-K 공시"와 "refresh `cutoff` 기준 직전 4일 이내"만 반영한다. 예: 월요일 리밸런스(`as_of`=월요일)는 `filing_date`가 직전 목요일 이후(월요일 − 4일 이내)인 8-K만 반영한다. 지난 화~수요일에 낸 8-K는 월요일 기준 5~6일이라 반영되지 않고, 다음 리밸런스(7일 뒤)에서도 마찬가지로 창 밖이다. 즉 주간 mandate의 PEAD는 8-K 이후 4일 안에 리밸런스 세션이 오는 경우에만 발화한다. 이것이 보고서의 두 규칙을 합친 결과이며 `pead.py:73-75`와 `session.py:148-149`로 확정된다. 일간 mandate는 매 세션 호출되므로 4일 창이 모두 관측된다. 레거시 `BacktestEngine`(`backtesting/__init__.py:3`에서 export, `backtesting/__main__.py:14`)은 `run.py`/`Fund` 경로가 아니라 별도 CLI이다.
- 조사 범위: `grep -n "predict(" -r hedge_fund --include='*.py'` (정의/테스트/주석 제외) — `pipeline/stages.py:62`, `backtesting/engine.py:132`, `tui/app.py:2254,3021`. `grep -rn "assess_fund\|execute_decision"` — Q6과 동일 호출처.

#### R1-Q10 답변
- 결론: **확정** — `assess_fund()`는 전략마다, 종목마다, 모델마다 `predict()`를 **그대로 다시 호출**하며 메모리 공유는 없다. 같은 페르소나가 두 전략에 있으면 `Fund`가 **전략별로 별도 인스턴스**를 만들고, 공유는 **디스크 `PromptCache`**(프롬프트 해시 키)로만 일어난다. 따라서 보고서의 "두 번째는 캐시 적중"은 디스크 캐시 적중이라는 뜻으로 맞지만, 파싱 실패/호출 오류로 `parsed`가 없는 항목은 적중으로 치지 않아 두 번째 전략에서 LLM을 다시 부른다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/pipeline/stages.py:58-62` | 호출 루프 | `for strategy, staff in fund.strategies:` / `signals = []` / `for ticker in tradeable: for model in staff: signals.append(model.predict(ticker, as_of, data_client))` — dict/메모 없음 | 코드 확인 |
  | `hedge_fund/fund/spec.py:189-201` | staff 구성 | `for strategy in spec.strategies:` ... `for m in strategy.models:` ... `cls = ALPHA_MODEL_REGISTRY[m.name]` / `staff.append(cls(**params))` — 전략·모델 항목마다 새 인스턴스 | 코드 확인 |
  | `hedge_fund/signals/llm_agent.py:50-51` | `LLMAgent.__init__` | `self._llm = llm if llm is not None else make_llm()` / `self._cache = cache if cache is not None else PromptCache()` — 인스턴스마다 `PromptCache()`지만 같은 디렉터리 | 코드 확인 |
  | `hedge_fund/llm/cache.py:22, 25-28, 31-42` | 디스크 캐시 | `DEFAULT_CACHE_DIR = CACHE_DIR / "llm"` / `payload = f"{agent}\|{model}\|{system}\|{user}"` → `sha256(...)[:24]` / `get`은 `<key>.json` 읽기 | 코드 확인 |
  | `hedge_fund/signals/llm_agent.py:74-80` | 적중 조건 | `cached = self._cache.get(key)` / `if cached is not None and "parsed" in cached:` → `_to_signal(..., cached=True)` | 코드 확인 |
  | `hedge_fund/signals/llm_agent.py:96, 110` | 실패 기록 | `self._cache.put(key, {**record, "call_error": ...})` / `{**record, "parse_error": ...}` — `parsed` 키 없음 → 다음 호출은 미적중 | 코드 확인 |
  | `hedge_fund/pipeline/stages.py:66, 70` | 모델 가중 | `model_weights=strategy.model_weights` (`spec.py:66-69`: `{m.name: m.weight ...}`) | 코드 확인 |
  | `hedge_fund/signals/pead.py:52-54, 117-121` | PEAD 인스턴스 캐시 | 인스턴스별 `self._cache: dict[str, list[EarningsRecord]]` — 인스턴스마다 따로(단 `CachedDataClient` 디스크 캐시는 공유) | 코드 확인 |

- 동작 설명: 두 전략에 `buffett`가 있으면 `Fund.strategies`에 서로 다른 `BuffettAgent` 인스턴스 2개가 생기고, `assess_fund`는 각각에 대해 종목 수만큼 `predict`를 호출한다. 두 호출은 각자 `build_snapshot`을 만들고(데이터 호출은 `CachedDataClient`가 디스크로 흡수), 같은 (agent 이름, 모델, system, user)이면 키가 같아 두 번째가 `PromptCache.get`에서 `parsed`를 찾아 즉시 `Signal`을 만든다. YAML `params`가 다른 경우: `LLMAgent`의 생성자 인자는 `llm, cache, blind, breakpoints`뿐(`llm_agent.py:43-49`)이며 YAML로 줄 수 있는 것은 사실상 `blind` 같은 단순 값이고, 이것이 다르면 user 프롬프트(`render(blind=...)`)가 달라져 키가 달라진다(별개 호출). 호출 수 공식의 M(서로 다른 페르소나 수)은 "성공한 호출이 이미 캐시된 경우"에만 맞고, 실패한 첫 호출이 있으면 두 번째 전략에서 재호출한다. 사전 `warm`은 페르소나당 1인스턴스(`tui/app.py:3011`)로 디스크 캐시를 채우므로 이후 `Fund` 호출은 대부분 적중한다.
- 조사 범위: `hedge_fund/pipeline/stages.py`, `fund/spec.py`, `signals/llm_agent.py`, `llm/cache.py`, `signals/pead.py` 전체를 직접 읽음. 같은 모델의 결과를 메모리 dict로 공유하는 코드는 `grep -rnE "_cache\b|lru_cache|functools" hedge_fund --include='*.py'`(테스트·tui 제외)로 찾았을 때 `signals/llm_agent.py:51,78,96,110,114`(PromptCache), `signals/pead.py:54,117-118`(인스턴스별), `pipeline/session.py:224`(`code_version`용 `lru_cache`)뿐이며 모델 결과를 공유하는 메모리 캐시는 없다.

#### R1-Q11 답변
- 결론: **없음 확정** — 기권 개수/비율을 집계해 경보, 로그 이벤트, halt, flat 처리로 잇는 코드는 `hedge_fund/`에 없다. 기권은 (1) 생성, (2) 블렌딩에서의 제외, (3) TUI 표시, (4) 신호 기록 저장에만 쓰인다. 경보/중단 임계값이 없다는 보고서 서술이 맞고, 조사 범위가 이제 명시된다.
- 근거 (비테스트 코드의 `abstain` 계열 전체 참조):

  | 위치 | 식별자 | 내용 (원문 인용) | 분류 |
  |---|---|---|---|
  | `hedge_fund/signals/llm_agent.py:18` | 모듈 docstring | `LLM call/parse failures ABSTAIN: Signal(value=0.0, metadata.abstained=True).` | 서술 |
  | `hedge_fund/signals/llm_agent.py:69` | `predict` | `return self._abstain(ticker, date, f"insufficient data: {exc}")` | 생성 |
  | `hedge_fund/signals/llm_agent.py:98, 101` | LLM 호출 실패 | `signal = self._abstain(ticker, date, f"LLM call failed: {exc}")`; 이어서 `logger.warning("%s LLM call failed for %s@%s: %s", ...)`(102행) — 종목별 경고 로그 1줄, 집계 없음 | 생성 + 로그 |
  | `hedge_fund/signals/llm_agent.py:112` | 파싱 실패 | `return self._abstain(ticker, date, f"parse failed: {exc}")` (경고 로그 111행) | 생성 + 로그 |
  | `hedge_fund/signals/llm_agent.py:190, 196-204` | `_to_signal`, `_abstain` | `"abstained": False,` / `metadata={"abstained": True, "abstain_reason": reason, "cached": False}` | 생성 |
  | `hedge_fund/portfolio/construction.py:69-70` | `blend_signals` | `if signal.metadata.get("abstained") is True: continue` | 판단(제외) |
  | `hedge_fund/signals/base.py:40` | `AlphaModel.predict` docstring | `Set metadata["abstained"] to True when the model cannot form a view.` | 서술 |
  | `hedge_fund/tui/app.py:870, 877-878` | `_VERDICT_STYLE`, `_verdict` | `"abstain": ("·", MUTED),` / `if signal.metadata.get("abstained") is True: word = "abstain"` | 표시 |
  | `hedge_fund/pipeline/models.py:35`, `pipeline/stages.py:75` | `StrategyRecord.signals` | `signals: list[Signal]  # this strategy's analysts x tradeable tickers` / `signals=signals` — `abstain` 문자열 참조는 없고 `Signal.metadata`가 그대로 직렬화됨 | 저장 |
  | `hedge_fund/portfolio/validation.py:59-60` | `validate_targets` | `abstain` 참조 없음, `flat_reason`이면 비중 0을 요구하는 검사만 | 해당 없음 |

  (테스트 참조: `pipeline/test_stages.py:50-66, 207-215`, `portfolio/test_construction.py:14-135`, `llm/test_client.py`, `signals/test_llm_agents.py`, `tui/test_app.py:209` — 모두 동작 검증이며 경보 코드가 아님.)
- 동작 설명: 기권 → `blend_signals`가 분모와 분자에서 제외 → 한 종목의 모든 모델이 기권이면 그 종목의 `weight_total`이 없어 `convictions=0.0` → 총점이 0이면 `flat_reason="no_eligible_positions"`(전략 단위). 이 `flat_reason`은 종목/전략 수준 결과이며 "기권 때문"이라는 이유 코드는 아니다(`FlatReason` 타입, `construction.py:16`). 기권이 많아도 paper `tick`은 정상 종료한다. 자동 halt는 예외가 날 때만(`paper/tick.py:138-142`: `except Exception as exc: ... ledger.halt(reason)`) 걸리고, 기권은 예외가 아니다(`_abstain`이 예외 대신 `Signal`을 반환).
- 조사 범위: `grep -n "abstain" -r hedge_fund --include='*.py'`(위 표가 비테스트 전수), `grep -rn "halt" --include='*.py'`(`run.py:32,149-151,284-306`, `paper/ledger.py`, `paper/tick.py:76,110,136-142`, `pipeline/session.py:56,125-126` — 조건은 `state.halted`, 수동 `aihf paper halt`, 틱 예외뿐), `grep -rn "flat_reason"`(`construction.py`, `stages.py:78`, `pipeline/models.py:39`, `validation.py:59-60`, `tui/app.py:1234,1252,1446`). 개수/비율 계산(`sum(`/`count(`/`len(` 와 `abstained` 결합)은 해당 파일들에서 없음을 직접 읽어 확인.

#### R1-Q12 답변
- 결론: **확정** — 있다. mandate YAML의 모델 `params`에 `blind: true`를 쓰면 paper `tick`에서도 LLM 에이전트가 blind 프롬프트로 만들어진다. CLI 플래그나 환경 변수 경로는 없다. 반대로 blind를 끄는 경로도 `blind=True` 덮어쓰기(`spec.py:199`)로 백테스트에서는 막혀 있다. 보고서 `00-overview.md` 6절 4번/`03-decision.md` 4-2의 "paper는 unblind"는 **기본 동작으로는 맞지만 설정으로 바꿀 수 있다**(보고서 보완 필요).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `hedge_fund/signals/llm_agent.py:43-49, 58` | `LLMAgent.__init__` | `blind: bool = False,` / `self._blind = blind` | 코드 확인 |
  | `hedge_fund/signals/llm_agent.py:132-141` | 사용 | `if self._blind: ... breakpoints = self._breakpoints` / `return snapshot.render(blind=self._blind)` | 코드 확인 |
  | `hedge_fund/fund/spec.py:18-25` | `ModelSpec` | `model_config = ConfigDict(extra="forbid")` — `name`, `weight`, `params`만 허용하고 `params: dict[str, Any] = Field(default_factory=dict, description="constructor kwargs for the model")` — 내용 검증 없음 | 코드 확인 |
  | `hedge_fund/fund/spec.py:199-200` | `Fund.__init__` | `params = {**m.params, "blind": True} if blind and issubclass(cls, LLMAgent) else m.params` / `staff.append(cls(**params))` — `blind=False`(기본)면 YAML params가 그대로 생성자에 전달 | 코드 확인 |
  | `hedge_fund/paper/tick.py:132` | paper 경로 | `fund = (build_fund or Fund)(deployed.spec)` — `blind` 인자 없음 | 코드 확인 |
  | `hedge_fund/run.py:194` | 백테스트 | `fund = Fund(spec, blind=True)` | 코드 확인 |
  | `hedge_fund/signals/pead.py:42-48` | PEAD 생성자 | keyword-only `earnings_limit, signal_window_days, announcement_only`만 — `params: {blind: true}`를 PEAD에 쓰면 `TypeError`(LLM이 아닌 모델에는 해당 없음) | 코드 확인 |
  | `hedge_fund/signals/{buffett,graham,munger,lynch,druckenmiller}.py` | 페르소나 | 모두 `class XAgent(LLMAgent)`로 `__init__` 재정의 없음 → `blind` 인자 상속 | 코드 확인 |

- 동작 설명: paper `tick`은 `Fund(deployed.spec)`을 `blind=False`로 만들므로 `spec.py:199`의 삼항식은 `m.params`를 그대로 쓴다. YAML에 `params: {blind: true}`가 있으면 `cls(blind=True)`가 되어 `LLMAgent._blind=True` → 스냅샷이 `size_percentile`을 위해 `shared_breakpoints()`(`llm_agent.py:135`)를 로드하고 `render(blind=True)`가 호출된다. 반대 경로(YAML `blind: false`)는 백테스트에서 `{**m.params, "blind": True}`가 뒤에 와서 덮어쓰므로 무효다. mandate는 `load_spec`(`spec.py:125-133`)을 거치지만 `params` 내부 키 검증은 없다. 환경 변수/CLI로 blind를 켜는 코드는 없다.
- 조사 범위: `grep -rn "blind" hedge_fund --include='*.py'`(비테스트) — `signals/llm_agent.py`, `features/snapshot.py`, `fund/spec.py:177-199`, `run.py:191-194`, `tui/app.py:2938,3002-3011`, `features/breakpoints.py`. `grep -rniE "BLIND"`로 `environ`/`getenv`와 결합한 사용 없음, `run.py`의 `add_argument` 목록(`--blind` 계열) 없음. paper 쪽 `paper/deployed.py`는 `spec`을 그대로 저장/로드(`yaml.safe_dump(deployed.model_dump())`, `deployed.py:69`)하므로 YAML `params`가 보존된다.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 없음 확정 | `data/client.py:114-120`(정렬/order 파라미터 없음), `features/snapshot.py:195-212, 225-231`(`metrics[0]`을 그대로 최신으로 사용), `snapshot.py:285-288`(`_trend` docstring "values arrive newest first")을 직접 열어 확인함. `hedge_fund/` 전체에 sort/reverse/order grep 범위가 적혀 있음. FD 응답 순서는 외부 사항으로 분리했고 경우의 수(a/b)까지 적혀 있어 정적 부분은 모두 확정됨 |
| R1-Q2 | 해소 | `snapshot.py:204-212`(FD 행 필드 복사, 주석 원문), `snapshot.py:231`, `data/models.py:36-43`을 확인함. 재계산 없음이 확정됐고, 기준 시점은 완료 조건대로 "코드에 서술 없음 + 외부 API 정의 의존"으로 분리함. 추가 발견(`client.py:207-215` `get_market_cap`이 `facts.market_cap`을 읽지만 `CompanyFacts`(`models.py:154-171`)에 그 필드가 없음, 호출처 없음)도 확인함 |
| R1-Q3 | 없음 확정 | `models.py:36-43`(docstring뿐, `_IGNORE`), `snapshot.py:270-282`(`_fmt`/`_avg`는 None만 거름)을 확인함. validator/isfinite/isnan/allow_inf_nan grep 범위가 충분하고, NaN 유입 시 `"nan"`/`"infB"` 렌더 흐름도 코드로 설명됨. 서버 정리 여부만 외부 사항 |
| R1-Q4 | 해소 | `data/cached.py:87-98`(params에 날짜 없음), `cached.py:120-129`(`_read` 만료 검사 없음), `cached.py:135-165`(TTL 분기는 일봉 가격만)를 확인함. `CachedDataClient(` grep 결과 비테스트 생성 지점 8곳 모두 `refresh` 미지정임을 직접 재확인함. "무기한 재사용"으로 확정 |
| R1-Q5 | 해소 | `signals/pead.py:42-50`(`earnings_limit=8`), `pead.py:63-67`(`past` 비면 `_neutral`), `pead.py:100-101`, `pead.py:117-121`(날짜 인자 없는 호출, 인스턴스 캐시)을 확인함. limit 경로와 반환값은 정적으로 확정됐고, FD가 어느 N건을 주는지만 외부 응답이라 분리함(완료 조건이 허용한 분리) |
| R1-Q6 | 해소 | `data/sessions.py:17-18`(달력일 -1), `pipeline/stages.py:129-136`(`cutoff`/`effective`, 주문은 `effective.final_weights`), `stages.py:157-165`(원래·refresh 평가 모두 기록), `snapshot.py:87-94`(렌더에 as_of 없음)를 확인함. 금요일→월요일 예시가 코드와 일치함. LLM 캐시 적중 여부만 새 공시 유무(외부)에 의존하고, PEAD는 창 판정 때문에 결과가 달라질 수 있다는 점이 코드로 확정됨 |
| R1-Q7 | 해소 | `tui/shared.py:74`, `run.py:189-190`을 확인함. CLI와 TUI가 같은 상수 78주를 쓰고, 종료일 기본값은 `completed_through()`임이 확정됨 |
| R1-Q8 | 해소 | `pead.py:100-101`(metadata 없음), `portfolio/construction.py:69-75, 80-100`(abstained만 제외, 0.0은 분모 포함, gross<tol이면 `no_eligible_positions`), `stages.py:55, 68-70`(분모는 전략 가중치 합 고정)을 확인함. 예시 mandate에서 PEAD flat이면 총노출 0.6, 나머지 0.4는 현금이라는 공식이 코드와 맞음 |
| R1-Q9 | 해소 | `pipeline/session.py:148-149`(리밸런스일만 `assess_fund`), `session.py:201-209`(ISO 주), `stages.py:58-62`(유일한 운영 `predict` 호출), `pead.py:73-75`(4일 창)를 확인함. 결정에 쓰이지 않는 TUI warm/레거시 엔진 경로까지 구분됨 |
| R1-Q10 | 해소 | `fund/spec.py:189-201`(전략·모델 항목마다 새 인스턴스), `stages.py:52-62`(메모 없음, 주석 "second ask is a prompt-cache hit"), `signals/llm_agent.py:78-80`(`"parsed"`가 있을 때만 적중), `llm_agent.py:96, 110`(실패 기록에는 `parsed` 없음)을 확인함. 공유 방식은 "디스크 PromptCache"로 확정 |
| R1-Q11 | 없음 확정 | `abstain` 비테스트 grep을 직접 다시 돌려 답변 표와 대조함. `llm/client.py:62`, `llm/contract.py:14` 두 docstring 언급이 표에서 빠졌지만 둘 다 서술 주석이라 결론에 영향 없음. `llm_agent.py:196-204`, `construction.py:69`, `tui/app.py:877-878`, `paper/tick.py:138-142`(halt는 예외 때만)를 확인함. 집계·경보 코드 없음 |
| R1-Q12 | 해소 | `fund/spec.py:18-25`(`params: dict[str, Any]`, 내부 검증 없음), `spec.py:199-200`(blind=False면 YAML params 그대로 전달), `paper/tick.py:132`(`Fund(deployed.spec)`), `llm_agent.py:43-58`(`blind` 생성자 인자)를 확인함. YAML `params: {blind: true}`로 paper에서도 blind가 켜진다는 결론이 확정됨 |

새로운 범위 내 질문은 없다. 답변에서 나온 추가 사실(PEAD 실적 이력 캐시 고정, refresh 시 PEAD 결과 변동, 동일 전략 내 PEAD 0.0 희석, `get_market_cap` 미사용 결함)은 모두 코드로 확정돼 있어 아래 보고서 반영 목록에 넣는다.

---

## 최종 정리 (질문자)

- 총 라운드: 1 / 총 질문: 12 / 해소 9 · 없음 확정 3 · 정적 확인 불가 0
- 핵심 확정 사실
  1. 재무지표 행 순서는 코드가 정렬하지 않는다. `build_snapshot()`은 FD `/financial-metrics/` 응답 순서를 그대로 쓰고 `metrics[0]`을 최신으로 가정한다(`features/snapshot.py:195-231`, `data/client.py:114-120`). 순서가 틀려도 감지하는 코드가 없다.
  2. 프롬프트의 시총과 P/E는 FD 행 필드를 그대로 복사한 값이다. 가격으로 다시 계산하지 않고, 기준 시점은 코드에 서술이 없다(`snapshot.py:204-212, 231`).
  3. NaN/Inf를 거르는 클라이언트 코드는 없다. NaN이 들어오면 집계가 NaN이 되고 프롬프트에 `"nan"`이 찍힌다(`snapshot.py:270-299`, `data/models.py:36-43`).
  4. `get_company_facts`와 `get_earnings_history`는 캐시 키에 날짜가 없어서 디스크 캐시를 무기한 재사용한다. 저장소 어디에서도 `refresh=True`를 쓰지 않는다(`data/cached.py:87-98, 120-165`). 그래서 paper 운영 중 PEAD는 처음 조회한 뒤에 나온 8-K를 보지 못한다.
  5. PEAD는 날짜 인자 없이 `earnings_limit=8`건을 한 번만 받는다. 기준일 이전 이벤트가 그 안에 없거나 4일 창 밖이면 기권이 아니라 `value=0.0` 투표가 된다(`signals/pead.py:42-75, 100-121`).
  6. 체결 전 refresh는 체결일의 달력상 전날이 결정일과 다를 때(주말·휴장 사이) 일어난다. 주문은 refresh 평가의 `final_weights`로 만든다(`data/sessions.py:17-18`, `pipeline/stages.py:129-142`).
  7. 전략 슬라이스는 `strategy.weight / Σweight`로 고정된다. flat인 전략의 몫은 다른 전략으로 재분배되지 않고 현금으로 남는다(`stages.py:55, 68-70`, `portfolio/construction.py:96-99`).
  8. 운영 경로에서 모델 `predict()`는 `assess_fund()`에서만 불린다. `assess_fund()`는 리밸런스 세션과 refresh에서만 호출된다(`pipeline/session.py:148-149`, `stages.py:58-62, 130`). 그래서 주간 mandate의 PEAD는 공시 후 4일 안에 리밸런스 세션이 와야만 발화한다.
  9. 같은 페르소나가 여러 전략에 있으면 인스턴스가 따로 생긴다. 공유는 디스크 `PromptCache`로만 이뤄지고, 실패 기록은 적중으로 치지 않는다(`fund/spec.py:189-201`, `signals/llm_agent.py:74-112`).
  10. 기권 집계, 경보, halt 장치는 없다. halt는 틱에서 예외가 나거나 수동으로 걸 때만 걸린다(`paper/tick.py:138-142`). blind는 백테스트에서 강제로 켜지고, paper에서도 YAML `params.blind`로 켤 수 있다(`fund/spec.py:199`, `run.py:194`).

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` Q1-1 표, `03-decision.md` 4-1 | 스냅샷 행은 "최신순" | "최신순은 FD 응답 순서에 의존한다. 코드에는 정렬이 없고 `metrics[0]`을 최신으로 가정한다(`snapshot.py:195-231`). 역순이면 `*_latest`, `_trend`, `eps_growth_yoy`, `t-0` 라벨이 모두 뒤집히고 이를 감지하는 코드가 없다"를 추가 | R1-Q1 |
| `01-data.md` Q1-1 핵심 시사점, `next.md` 미확인 체크리스트 | 시총·P/E 출처 `추론`, "`market_cap`이 공시일 기준 시총인지" 미확인 | 출처는 `확정`으로 바꾼다: FD 행 필드를 복사하고 재계산하지 않는다(`snapshot.py:204-212`). 기준 시점은 "코드에 서술 없음(외부 API 정의)"으로 적는다. `FDClient.get_market_cap()`은 `CompanyFacts`에 없는 `market_cap` 필드를 읽지만 호출처가 없어 미사용이라는 점도 덧붙인다(`client.py:207-215`, `models.py:154-171`) | R1-Q2 |
| `01-data.md` Q2 원시 데이터 가공 NaN/Inf 행 | 서버가 정리한다고 docstring에 있음, `추론` | 클라이언트 검사는 "없음 확정"(조사 범위 기재). NaN이 유입되면 `_avg`/`_trend`/`_cagr`가 NaN이 되고 `_fmt`가 `"nan"`을 렌더한다(`snapshot.py:270-299`). `QuantModel._safe_float`은 이 경로에서 호출되지 않는다 | R1-Q3 |
| `01-data.md` Q2 캐시 "운영 시 주의", `next.md` 체크리스트 | `company_facts`/`earnings_history` TTL 없음, `추론` | `확정`으로 바꾼다: 캐시 키가 `{"ticker"}`, `{"ticker","limit"}`라 무기한 재사용하고, `refresh=True` 호출 지점이 없다(`cached.py:87-98, 120-165`). paper 운영 중 PEAD는 최초 조회 뒤에 나온 8-K를 보지 못한다는 운영 영향도 추가 | R1-Q4 |
| `01-data.md` Q2 미래 데이터 차단, `03-decision.md` 4-1 | PEAD는 `filing_date <= 기준일`만 고려 | 덧붙인다: PEAD는 날짜 필터 없이 최신 `earnings_limit=8`건을 티커당 한 번 받는다(`pead.py:117-121`, `client.py:197-200`). 그 범위보다 이른 기준일에서는 `past`가 비어 0.0(중립)이 되고, 이는 이벤트 없음과 구분되지 않는다. FD가 자르는 순서는 정적 확인 불가 | R1-Q5 |
| `02-schedule.md` 세션 순서 2단계, `03-decision.md` 4-2 T→T+1 표 | "직전 달력일이 결정일과 다르면 재평가", 캐시 적중 `추론` | `previous_day`는 달력일 -1이다(`sessions.py:17-18`). 주문은 refresh 평가의 `final_weights`로 만든다(`stages.py:129-136`). 금요일 결정→월요일 체결 예시를 추가한다. 캐시 적중 가능성은 LLM 페르소나에만 해당하고, PEAD는 4일 창 때문에 refresh에서 결과가 바뀔 수 있다(`pead.py:73-75`) | R1-Q6 |
| `03-decision.md` 4-8 백테스트 행 | 78주 기본 창, `추론`(`tui/shared.py:74`) | `확정`으로 바꾼다: CLI `aihf backtest`도 같은 상수를 import한다(`run.py:68, 189-190`). 종료일 기본값은 `completed_through()`(뉴욕 기준 어제)다 | R1-Q7 |
| `03-decision.md` 4-3 기권/중립 행 | "기권은 제외, 중립(0.0)은 투표에 포함" | 추가: PEAD 이벤트 없음/창 초과는 0.0 투표다(`pead.py:100-101`). PEAD 단독 전략은 `no_eligible_positions`로 flat이 되고, 그 슬라이스(예시 mandate 0.4)는 현금으로 남는다(`stages.py:55, 68-70`). PEAD가 다른 모델과 한 전략에 있으면 0.0이 평균을 희석한다 | R1-Q8 |
| `03-decision.md` 4-3 숫자 규칙 표(PEAD 창 + 리밸런스) | 두 규칙이 따로 적힘 | 연결 문장을 추가: 주간 mandate에서 PEAD는 리밸런스 세션 `as_of`와 refresh `cutoff` 두 날짜에만 평가된다. 공시 후 4일 안에 리밸런스 세션이 와야 발화한다(`session.py:148-149`, `stages.py:58-62`) | R1-Q9 |
| `03-decision.md` 4-8 첫 행 | "같은 페르소나가 두 전략에 있어도 프롬프트가 같으면 두 번째는 캐시 적중" | 구체화한다: 전략마다 별도 인스턴스가 생기고, 공유는 디스크 `PromptCache`로만 이뤄진다(`spec.py:189-201`, `llm_agent.py:78-80`). 호출 실패/파싱 실패 기록은 적중이 아니라서 두 번째 전략이 다시 호출한다. 그래서 M 공식은 성공 캐시를 전제로 한다 | R1-Q10 |
| `03-decision.md` 4-6 "주의" 문단, `next.md` 질문 3번 | 기권 경보/중단 임계값 없음, `추론`, 조사 범위 없음 | "없음 확정"으로 바꾸고 조사 범위(`abstain`/`halt`/`flat_reason` grep)를 적는다. 자동 halt는 틱 예외 때만 걸린다는 점도 추가(`paper/tick.py:138-142`) | R1-Q11 |
| `00-overview.md` 6절 4번, `03-decision.md` 4-2 동일성 표 | "백테스트는 blind, paper는 unblind" | "paper는 기본이 unblind다. mandate YAML 모델 `params: {blind: true}`로 paper에서도 blind를 켤 수 있다(`spec.py:18-25, 199-200`, `paper/tick.py:132`). 백테스트의 blind는 덮어쓰기로 강제된다(`run.py:194`)"로 고친다 | R1-Q12 |
