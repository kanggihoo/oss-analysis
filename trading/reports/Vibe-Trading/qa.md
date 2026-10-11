# Vibe-Trading — 질문·답변 검증 기록

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 3
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | 펀딩비(`funding_rate`)가 LLM·전략 입력까지 전달되는 경로 | Q1 | 해소 | R1 |
| R1-Q2 | OI·온체인 데이터 제공 도구·loader 존재 여부 | Q1 | 없음 확정 | R1 |
| R1-Q3 | `.KS` 종목으로 investment_committee 실행 시 정상 데이터를 주는 도구 | Q1 | 해소 | R1 |
| R1-Q4 | pykrx 미설치로 강등될 때 `get_market_data` 결과에 실제 서빙 소스가 표시되는가 | Q2 | 해소 | R1 |
| R1-Q5 | `fundamentals_loader.py`의 PIT(공시 가능일) 구현 | Q2 | 해소 | R1 |
| R1-Q6 | KIS 일봉 조회의 연속 조회(페이지네이션) 처리 | Q2 | 없음 확정 | R1 |
| R1-Q7 | 데이터 나이(stale) 검사 코드의 부재 확정 | Q3 | 없음 확정 | R1 |
| R1-Q8 | swarm 상류 `report.md`가 하류 프롬프트에 들어갈 때 길이 제한 | Q4-1 | 해소 | R1 |
| R1-Q9 | `run_swarm` 결과가 메인 grounding 장부에 증거로 들어가는가 | Q4-5 | 해소 | R1 |
| R1-Q10 | grounding `figures` 대조의 허용 오차 값 | Q4-5 | 해소 | R1 |
| R1-Q11 | 라이브 러너 턴의 system prompt가 원칙 4를 포함하는가 | Q4-5 / Q6 | 해소 | R1 |
| R1-Q12 | 영속 메모리 recall 상위 3건의 선택 산식 | Q4-7 | 해소 | R1 |
| R2-Q1 | 선언 없는 숫자(swarm 보고서 수치 옮겨 적기)를 게이트가 어떻게 처리하는가 | Q4-5 | 해소 | R2 |
| R2-Q2 | swarm 상류 작업이 `token_limit` 등으로 실패하면 하류 작업은 어떻게 되는가 | Q4-1 / Q4-5 | 해소 | R2 |
| R3-Q1 | 기본 제공 swarm 프리셋에 `depends_on` 게이트를 우회하는 `input_from` 연결이 있는가 | Q4-1 / Q4-5 | 없음 확정 | R3 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. 펀딩비가 판단 입력까지 전달되는가
- GUIDE 항목: Q1 (코인 전용)
- 왜 묻는가: `01-data.md` 1-1절 "코인 전용 / 펀딩비" 행이 `추론`이고 제공자·소비 주체가 `미확인`이다. `next.md` 미확인 체크리스트 1번과 같다. `agent/backtest/loaders/ccxt_loader.py`에 `funding_rate` 컬럼을 채우는 코드가 있는 것으로 보이나, 그 컬럼이 LLM이나 전략에 실제로 닿는지는 보고서에 없다.
- 질문: `funding_rate` 컬럼을 채우는 loader는 어느 것이며, 그 컬럼이 (a) `get_market_data` 도구 출력으로 LLM에 전달되는지, (b) 백테스트 `SignalEngine`의 입력 데이터프레임에 포함되는지 각각 어떻게 되는가?
- 답변 완료 조건: 컬럼을 채우는 함수의 `파일:라인`과 원문, 그리고 (a)·(b) 각각에 대해 컬럼을 통과시키거나 걸러내는 코드의 `파일:라인`(필드 선택·`fields` 인자 처리 등). 전달되지 않으면 걸러지는 지점을 제시.

#### R1-Q2. OI·온체인 데이터 제공 경로가 있는가
- GUIDE 항목: Q1 (코인 전용)
- 왜 묻는가: `01-data.md` 1-1절 "온체인, OI" 행이 `미확인`이고 "`skills/defi-yield`, `crypto-derivatives` 문서는 안 읽음"이라고만 되어 있다. 없음이라면 조사 범위가 필요하다.
- 질문: 미결제약정(open interest)이나 온체인 지표(거래소 유출입, 활성 주소, TVL 등)를 가져오는 도구 또는 loader가 코드에 존재하는가? 스킬 문서가 이런 데이터를 언급한다면 실제로 어떤 도구 호출로 이어지는가?
- 답변 완료 조건: 있으면 도구·loader의 `파일:라인`과 데이터 제공자. 없으면 grep 패턴 목록(`open_interest`, `openInterest`, `fetch_open_interest`, `onchain`, `on-chain`, `tvl`, `defillama`, `glassnode` 등)과 확인한 디렉터리, 두 스킬 문서가 지시하는 도구 이름.

#### R1-Q3. 한국 종목으로 investment_committee를 돌릴 때 정상 데이터를 주는 도구
- GUIDE 항목: Q1 (시장별 데이터 차이)
- 왜 묻는가: `01-data.md` 1-4절 마지막 행이 `추론`이고, 문장도 "OHLCV + `get_financial_statements`(한국 미지원) 없이 가격 중심 분석"으로 읽기 어렵다. `investment_committee.yaml:47-49`의 도구 목록 중 한국 종목에서 실제로 데이터를 주는 도구가 무엇인지 확정이 필요하다.
- 질문: `investment_committee` 프리셋의 각 에이전트 도구 화이트리스트에 있는 도구 중, 심볼 `005930.KS`에 대해 에러 봉투 없이 데이터를 반환하는 코드 경로를 가진 도구는 어느 것인가?
- 답변 완료 조건: 프리셋의 도구 목록 원문(`파일:라인`)과, 도구마다 `.KS` 심볼이 지나는 시장 분기 코드의 `파일:라인` 및 결과(지원 / `unsupported` 에러 / 다른 시장으로 오분류). 표 한 개로 정리.

#### R1-Q4. pykrx 강등 시 `get_market_data` 결과가 실제 소스를 알려 주는가
- GUIDE 항목: Q2 (폴백·실패 처리)
- 왜 묻는가: `01-data.md` 2-4절은 pykrx 미설치 시 "조용히 yahoo/yfinance로 내려간다"고 하고, 2-3절 "실제 서빙 소스 기록"은 `agent/backtest/runner.py:1803-1812`의 run card 보정만 근거로 든다. 메인 에이전트의 `get_market_data` 도구 경로에서도 LLM이 실제 소스를 알 수 있는지는 적혀 있지 않다.
- 질문: `kr_equity` 시장에서 pykrx가 사용 불가일 때 `get_market_data` 도구가 LLM에 돌려주는 결과에 실제 응답한 소스 이름(예: `yahoo`)이 필드로 포함되는가?
- 답변 완료 조건: `get_market_data` 반환 봉투를 만드는 코드의 `파일:라인`과 소스 관련 필드 원문, 그 값이 요청 소스인지 실제 서빙 소스인지 결정하는 코드 위치.

#### R1-Q5. 재무 loader의 PIT 구현
- GUIDE 항목: Q2 (look-ahead 방지)
- 왜 묻는가: `01-data.md` 2-3절 "미래 데이터 차단(재무)" 행이 "불변식 선언까지. 구현 본문은 안 읽음"이다. `next.md` 미확인 체크리스트 2번.
- 질문: `agent/backtest/loaders/fundamentals_loader.py`는 기준일 이후 공시된 값을 어떤 필드(예: `filed` 날짜)와 어떤 비교 연산으로 걸러내는가?
- 답변 완료 조건: 필터링 코드의 `파일:라인`과 원문(사용하는 날짜 필드명, 비교 조건). 기준일이 어디서 들어오는지(함수 인자) 포함.

#### R1-Q6. KIS 일봉 조회의 연속 조회 처리
- GUIDE 항목: Q2 (수집 방식)
- 왜 묻는가: `next.md` 미확인 체크리스트 6번. `kis/sdk.py:445-465`가 시작일 `19900101`로 1회 호출 후 `limit`으로 자른다고 되어 있다. 응답 행 수 상한 자체는 외부 API 사양이지만, 코드에 연속 조회 처리가 있는지는 정적으로 확인 가능하다.
- 질문: KIS 일봉 조회 함수에 연속 조회(응답 헤더 `tr_cont`, 다음 키, 반복 호출 등) 처리가 있는가?
- 답변 완료 조건: 있으면 반복 로직의 `파일:라인`. 없으면 해당 함수 전문 범위와 `_get` 헬퍼의 `파일:라인`, grep 패턴(`tr_cont`, `CTX_AREA`, `ctx_area`, `next`, `while`)과 결과.

#### R1-Q7. stale 데이터 검사 코드의 부재 확정
- GUIDE 항목: Q3 (데이터 신선도)
- 왜 묻는가: `02-schedule.md` "신선도 관리" 표의 "코드 수준" 행이 `추론`이며 "전수 grep이 아니라 함수 읽기 기반"이라고 스스로 밝혔다.
- 질문: 도구 결과나 grounding 게이트, swarm 사전 조회 어디에서든 데이터의 시각(봉 날짜, as-of)을 현재 시각과 비교해 경고·거절·확신도 하향을 하는 코드가 있는가?
- 답변 완료 조건: 있으면 비교 코드의 `파일:라인`과 임계값. 없으면 `agent/src` 전체 grep 패턴(`stale`, `freshness`, `as_of`, `asof`, `max_age`, `timedelta`, `age_days` 등)과 각 결과를 어떻게 배제했는지.

#### R1-Q8. swarm 상류 요약의 길이 제한
- GUIDE 항목: Q4-1 (길이 제한과 자르기)
- 왜 묻는가: `03-decision.md` 4-1절 "swarm 상류 요약" 행이 "자르기 규칙은 못 찾음 … (해당 구간 기준)"으로 범위가 좁다. `report.md` 전문이 그대로 하류에 들어가면 PM 입력 크기가 무제한이 된다.
- 질문: 상류 작업의 `report.md`(또는 최종 텍스트)가 하류 워커 프롬프트의 `{upstream_context}`로 들어가기까지 어느 단계에서든 길이 제한·자르기·요약이 적용되는가?
- 답변 완료 조건: 상류 결과를 읽는 지점부터 프롬프트 치환까지의 호출 경로(`파일:라인` 순서)와, 자르기가 있으면 상수값 원문, 없으면 그 경로상 함수 목록과 grep 패턴(`truncat`, `[:`, `max_chars`, `MAX_`)과 결과.

#### R1-Q9. `run_swarm` 결과가 grounding 장부의 증거가 되는가
- GUIDE 항목: Q4-5 (코드의 덮어쓰기·제한 장치)
- 왜 묻는가: `00-overview.md` 핵심 발견 3은 "swarm 워커에는 적용되지 않는다"고만 하고, 메인 에이전트가 swarm 결과의 숫자를 최종 답변에 옮길 때의 처리는 `next.md` 미확인 체크리스트 3번으로 남아 있다.
- 질문: 메인 루프에서 `run_swarm` 도구 결과가 `ingest_tool_result`(`agent/src/agent/grounding/ledger.py:274`)를 거쳐 증거로 등록되는가, 등록된다면 swarm 보고서 안의 숫자가 `observed` 수치의 근거로 인정되는가?
- 답변 완료 조건: 도구 결과가 장부에 들어가는 호출처의 `파일:라인`, `run_swarm`을 포함·제외하는 분기 원문(도구 이름 목록, 결과 형식 조건 등).

#### R1-Q10. figures 대조의 허용 오차
- GUIDE 항목: Q4-5 (숫자 임계값)
- 왜 묻는가: `03-decision.md` 4-5절은 "허용 오차·산식 평가는 `ast` 기반"이라고만 하고 값이 없다. `next.md` 미확인 체크리스트 마지막 항목이며, 이 레포의 핵심 장치(grounding)의 결정 기준이 숫자로 비어 있다.
- 질문: `observed` 역할 수치를 도구 결과와 대조할 때 일치로 판정하는 허용 오차(상대·절대)는 얼마이며, 어느 함수에 정의되어 있는가?
- 답변 완료 조건: 허용 오차 상수 또는 `_close` 계열 함수의 `파일:라인`과 원문, 그 함수가 `_validate_figures`/`_check_observed`에서 호출되는 `파일:라인`.

#### R1-Q11. 라이브 러너 턴의 system prompt
- GUIDE 항목: Q4-5 / Q6 (판단 → 주문 경계)
- 왜 묻는가: `03-decision.md` 4-5절 마지막 항목이 `추론`이다. 원칙 4("조언 금지", `context.py:56-59`)와 러너의 "Trade freely INSIDE the limits"(`runner.py:241-245`)가 충돌한다고 했는데, 러너 턴이 실제로 같은 system prompt를 쓰는지가 정적으로 확인되지 않았다. 실제 LLM 반응은 질문하지 않는다.
- 질문: `LiveRunner`의 자율 턴이 에이전트를 실행할 때 쓰는 system prompt는 `ContextBuilder`의 `_SYSTEM_PROMPT`(원칙 4 포함)와 같은가, 아니면 러너 전용 system prompt나 원칙 제거·치환 경로가 있는가?
- 답변 완료 조건: 러너가 에이전트(`AgentLoop` 또는 세션)를 생성·호출하는 `파일:라인`부터 system prompt가 조립되는 `파일:라인`까지의 경로와, 분기가 있으면 분기 조건 원문.

#### R1-Q12. 영속 메모리 recall 선택 산식
- GUIDE 항목: Q4-7 (메모리)
- 왜 묻는가: `03-decision.md` 4-1·4-7절과 `01-data.md` 1-1절은 "상위 3건 자동 recall(각 500자)"이라고만 한다. 어떤 기준으로 3건을 고르는지는 `next.md` 미확인 체크리스트 8번으로 남아 있다.
- 질문: `PersistentMemory.find_relevant`는 사용자 메시지와 저장된 메모리의 관련도를 어떤 방식(키워드 겹침, 임베딩, 최신순 등)으로 계산해 상위 3건을 고르는가?
- 답변 완료 조건: 점수 계산 코드의 `파일:라인`과 원문, 동점·최소 점수 기준이 있으면 그 값, `context.py:390-400`에서 호출하는 인자.

### 답변 (답변자)

경로 표기: 별도 표기가 없으면 `repos/Vibe-Trading/agent/` 기준이다 (예: `src/market_data.py` = `repos/Vibe-Trading/agent/src/market_data.py`).

#### R1-Q1 답변
- 결론: **확정**. `funding_rate` 컬럼을 채우는 loader는 `backtest/loaders/ccxt_loader.py`의 `_fetch_perpetual` 하나뿐이다(코드는 `BASE-USDT-PERP`, Binance USD-M 한정). (a) `get_market_data`는 컬럼을 걸러내지 않으므로 컬럼이 LLM에 전달된다. 단, 모델이 `source="ccxt"`와 `-PERP` 코드를 직접 지정해야 하며 `source="auto"`로는 이 loader에 도달하지 못한다. (b) 백테스트에서는 컬럼이 `SignalEngine.generate(data_map)` 입력 프레임에 그대로 포함되고, 엔진도 이 컬럼으로 펀딩비를 정산한다. 1차 보고서 `01-data.md` 1-1절의 "제공자·소비 주체 미확인"은 이 답으로 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `backtest/loaders/ccxt_loader.py:63-70` | `_parse_ccxt_symbol` | `if normalized.endswith("-PERP"):` ... `return f"{match.group(1)}/USDT:USDT", "swap"` / 그 외 `return normalized.replace("-", "/"), "spot"` | 코드 확인 |
  | `backtest/loaders/ccxt_loader.py:209-214` | `_get_exchange` | `"BASE-USDT-PERP currently requires CCXT_EXCHANGE=binance"` → `exchange_id = "binanceusdm"` | 코드 확인 |
  | `backtest/loaders/ccxt_loader.py:343-364` | `_fetch_perpetual` | `funding = cls._fetch_funding_history(exchange, symbol, since_ms, end_ms)` ... `result["funding_rate"] = 0.0` / `result["funding_settlement_time"] = pd.NaT` / `result.loc[aligned, "funding_rate"] = funding.loc[aligned, "funding_rate"]` | 코드 확인 |
  | `backtest/loaders/ccxt_loader.py:375-420` | `_fetch_funding_history` | `exchange.fetch_funding_rate_history(symbol, since=cursor, limit=limit)`, `"funding_rate": pd.to_numeric([row["fundingRate"] for row in rows], ...)` | 코드 확인 |
  | `backtest/loaders/ccxt_loader.py:244` | `fetch` docstring | `fields: Ignored.` (loader가 필드 선택을 하지 않음) | 코드 확인 |
  | `src/tools/market_data_tool.py:96-153` | `parameters` | properties는 `codes, start_date, end_date, source, interval, max_rows`뿐이다. 필드 선택 인자가 없다 | 코드 확인 |
  | `src/market_data.py:417-421` | `_emit` | `records = [] if as_frames else df.reset_index().to_dict(orient="records")` → `results[symbol] = df if as_frames else cap_rows(records, max_rows)` (모든 컬럼이 레코드에 들어감, 행만 샘플링) | 코드 확인 |
  | `src/market_data.py:67-77` | `detect_source` | `-PERP` 심볼은 `_SOURCE_PATTERNS`에 없고 `_detect_market`이 `"a_share"`를 돌려줘 `return "tushare"  # Keep the documented fallback for unknown symbols.` | 코드 확인 |
  | `src/tools/market_data_tool.py:104-105` | description | 예시는 `["BTC-USDT"]`까지만이며 `-PERP`는 언급이 없다 | 코드 확인 |
  | `backtest/runner.py:1815`, `backtest/runner.py:1958` | `fetch_data_map`, `_sanitize_data_map` | `data_map = loader.fetch(...)` → `return {code: validate_ohlc(frame) ...}` (행만 제거, 컬럼 유지) | 코드 확인 |
  | `backtest/engines/base.py:907-921` | `run_backtest` | `data_map = loader.fetch(codes, ..., fields=extra_fields, interval=interval)` → `signal_map = signal_engine.generate(data_map)` | 코드 확인 |
  | `backtest/runner.py:1568-1570` | `_create_market_engine` | `if source in ("okx", "ccxt"):` → `return CryptoEngine(config)` | 코드 확인 |
  | `backtest/engines/_market_hooks.py:456-462` | `calc_crypto_funding_fee` | `hist = bar.get("funding_rate")` / `if hist is not None and pd.notna(hist): funding_rate = float(hist)` / `return notional * funding_rate * pos.direction * settlements` | 코드 확인 |
  | `backtest/engines/crypto.py:60-66,174,363,607` | `CryptoEngine` | `self.funding_mode = str(config.get("funding_mode", "fixed"))`, strict 경로 `rate = bar["funding_rate"]`, `self._apply_data_funding()`, 비엄격 경로 `fee = calc_crypto_funding_fee(...)` | 코드 확인 |
  | `backtest/loaders/base.py:328` | `resample_bars` | `elif column == "funding_rate": columns[column] = values.mean()` (주봉·월봉 변환에서도 컬럼 유지) | 코드 확인 |

- 동작 설명:
  1. (a) LLM 경로: 모델이 `get_market_data(codes=["BTC-USDT-PERP"], source="ccxt", ...)`를 호출한다. 도구는 입력 검증 후(`market_data_tool.py:158-245`) `fetch_market_data_json`으로 넘긴다. 심볼은 `normalize_crypto_symbol`(`market_data.py:83-87`)의 정규식 `([A-Z]{2,})[-/]?USDT`에 맞지 않아 그대로 `ccxt` loader의 `fetch`(`market_data.py:352`)에 들어간다. loader가 swap 경로(`ccxt_loader.py:284-288`)로 `_fetch_perpetual`을 호출해 OHLCV + `execution_open`, `mark_*`, `funding_rate`, `funding_settlement_time`(+ 브래킷 artifact가 있으면 `maintenance_*`) 컬럼을 만든다. 도구 출력은 `df.reset_index().to_dict(orient="records")`라서 이 컬럼이 모두 JSON에 실린다(`market_data.py:417`).
  2. `source="auto"`이면 `detect_source("BTC-USDT-PERP")`가 `"tushare"`를 돌려준다(`market_data.py:77`). A주 체인에서 풀리지 않아 `_unresolved`가 된다. 도구 설명에도 `-PERP` 예시가 없어, 모델이 이 경로를 스스로 알 확률은 낮다. 이것은 코드가 보장하는 사실이 아니라 설명문 기준의 서술이다.
  3. (b) 백테스트: `config.json`에 `source: "ccxt"`와 `BTC-USDT-PERP` 코드를 지정해야 한다. `fetch_data_map`이 `ccxt` loader를 쓰고(`runner.py:1802-1815`), `_create_market_engine`이 `CryptoEngine`을 고른다(`runner.py:1568-1570`; `_detect_market("BTC-USDT-PERP")`는 `"a_share"`지만 a_share 분기는 source 분기 뒤의 `else`에만 있다, `runner.py:1600-1608`). 프레임은 `generate(data_map)`에 필터 없이 전달되어(`base.py:921`) 전략 코드가 `funding_rate`를 읽을 수 있다. 엔진은 같은 컬럼으로 펀딩비를 정산한다. 기본 `funding_mode="fixed"`에서도 컬럼이 있고 NaN이 아니면 고정값 대신 이 값을 쓴다(`_market_hooks.py:459-461`). `perpetual_strict=True`이면 `funding_mode="data"`가 강제되고(`crypto.py:65-66`) 컬럼·결제 시각이 없으면 `ValueError`다(`crypto.py:174-181`).
  4. 다른 loader(`okx`, `binance_loader`, `yahoo` 등)에는 `funding` 문자열이 없다(grep 결과, 아래 조사 범위).
- 보고서 정정 필요: `01-data.md` 1-1절의 "펀딩비 추론/미확인"을 위 사실로 대체해야 한다. 추가로 "도구 출력에 포함된다"는 조건(`source="ccxt"` + `-PERP` 명시)을 적어야 한다.
- 조사 범위: `grep -rnI "funding" agent --include='*.py' --exclude-dir=tests` 전수. `funding_rate` 컬럼을 쓰는 loader는 `ccxt_loader.py`뿐이고, 소비 쪽은 `engines/_market_hooks.py`, `engines/crypto.py`, `engines/composite.py`, `perpetual_risk.py`, `loaders/base.py:276-328`뿐이다. `src/` 아래에서는 `funding`이 `okx-market/scripts/market_data_example.py`(스킬 예제 스크립트), `live/*`의 `account_funding_usd`(계좌 자금, 펀딩비와 무관), `research_papers_tool.py:194`(정규식 라벨)에만 나온다. `PERP`는 `grep -rn "PERP" backtest src --include='*.py'` 결과 `ccxt_loader.py`, `binance_*` 보정 모듈, `trading/connectors/binance/usdm.py:312`, 테스트뿐이다. 따라간 경로: `get_market_data` → `fetch_market_data_json` → `fetch_market_data` → `loader.fetch`; `runner.main` → `fetch_data_map` → `_create_market_engine` → `BaseEngine.run_backtest` → `signal_engine.generate`.

#### R1-Q2 답변
- 결론: **없음 확정**. 미결제약정(OI)과 온체인 지표를 가져오는 **전용 도구나 loader는 코드에 없다**. 스킬·프리셋 문서는 두 갈래로 데이터를 지시한다. OI·펀딩비는 `okx-market` 스킬의 REST 예제를 `bash`로 직접 호출하라는 방식이고, 온체인·스테이블코인·TVL 지표는 `read_url`로 외부 웹(DeFi Llama, Glassnode, Dune 등)을 읽으라는 방식이다. 둘 다 코드가 보증하는 정형 데이터 경로가 아니다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/tools/options_chain_tool.py:31` | `get_options_chain` | `("openInterest", "open_interest"),` (Yahoo **옵션** 체인의 행사가별 OI, 코인 OI 아님) | 코드 확인 |
  | `src/skills/okx-market/SKILL.md:69` | 스킬 표 10행 | `/public/open-interest ... Retrieve open-interest data for derivatives` | 문서 확인 |
  | `src/skills/okx-market/references/合约行情/持仓量.md:34` | 참조 문서 | `resp = requests.get(f"{BASE_URL}/public/open-interest", params={"instType": "SWAP"})` (모델이 `bash`로 실행할 예제 코드) | 문서 확인 |
  | `src/skills/okx-market/scripts/market_data_example.py:80` | 예제 스크립트 | `requests.get(f"{BASE_URL}/public/funding-rate", params={"instId": sym})` | 코드 확인 |
  | `src/swarm/presets/crypto_trading_desk.yaml:36,41` | `funding_basis_analyst` | `- Open interest level and 24h change` / `tools: [bash, read_file, write_file, load_skill, get_market_data]` | 코드 확인 |
  | `src/swarm/presets/crypto_trading_desk.yaml:82,118` | `liquidation_analyst`, `flow_analyst` | `tools: [bash, read_file, write_file, load_skill, read_url]` | 코드 확인 |
  | `src/skills/stablecoin-flow/SKILL.md:181-193` | 데이터 소스 표 | `DeFi Llama (Stablecoins page)`, `Glassnode`, `CryptoQuant`, `Dune Analytics`, `Nansen` ... `Use `read_url` tool to access web-based data sources.` | 문서 확인 |
  | `src/skills/defi-yield/SKILL.md:207-213` | 데이터 소스 표 | `DeFi Llama Yields`, `Aave/Compound dashboards`, `Dune Analytics` (도구 지시 없음) | 문서 확인 |
  | `src/skills/onchain-analysis/SKILL.md:252` | 마지막 항목 | `on-chain data requires extra APIs (Glassnode / Nansen)` | 문서 확인 |
  | `src/skills/crypto-derivatives/SKILL.md:280` | 마지막 항목 | `OKX data is available through the OKX data source, while Deribit requires an additional interface` | 문서 확인 |
  | `src/skills/perp-funding-basis/SKILL.md:202` | 마지막 줄 | `Use `load_skill("okx-market")` for OKX data retrieval patterns.` | 문서 확인 |
  | `src/tools/web_reader_tool.py:137` | `read_url` | `name = "read_url"` (임의 URL 읽기. 코인 지표 전용 파서는 없음) | 코드 확인 |
  | `src/tools/sentiment_tool.py:5-7` | `sentiment` | `fear_greed_index — fetch the current crypto Fear & Greed Index` (유일하게 코드에 있는 코인 시장 지표, OI·온체인은 아님) | 코드 확인 |
  | `src/tools/orderbook_depth_tool.py:17` | 호가 도구 | `Perpetuals (-PERP) are out of scope here — this tool is spot-book depth only.` | 코드 확인 |

- 동작 설명: 코인 데스크 프리셋의 `funding_basis_analyst`는 도구가 `get_market_data`(OHLCV)와 `bash`뿐이라 OI를 얻으려면 `okx-market` 스킬(`load_skill`)을 읽고 `bash`로 OKX 공개 REST를 직접 호출해야 한다. `flow_analyst`·`liquidation_analyst`는 `read_url`로 웹 페이지를 읽는다. 어느 경우에도 코드가 값을 정규화·검증하지 않는다. 호출이 실제로 성공하는지는 외부 네트워크와 모델의 실행에 달려 있다(실행 결과 영역, 질문 범위 밖).
- 조사 범위: `rg -n -i "open[_ ]?interest|openInterest|fetch_open_interest|onchain|on-chain|\btvl\b|defillama|glassnode|exchange_?flow|active_address|whale|coinglass|nansen|dune|etherscan|coingecko|stablecoin"`를 저장소 전체(README*, CHANGELOG, `frontend/`, 테스트 제외)에서 실행했다. `.py` 코드 히트는 `options_chain_tool.py`(옵션 OI), `research_papers_tool.py:188,194`(논문 분류용 정규식 라벨), `yahoo_client.py`(`optionChain`)뿐이고, 나머지는 `agent/src/swarm/presets/*.yaml`과 `agent/src/skills/*/SKILL.md` 문서다. `backtest/loaders/` 전체(`okx.py`, `ccxt_loader.py`, `binance_loader.py` 포함)와 `src/trading/connectors/`, `src/openbb_bridge/`에는 OI·온체인 관련 함수가 없다. 도구 디렉터리는 `ls src/tools` 전체 목록(코인 관련은 `market_data_tool`, `orderbook_depth_tool`, `sentiment_tool`)을 확인했다.

#### R1-Q3 답변
- 결론: **확정**. `investment_committee`의 4개 에이전트 도구 목록 중 `005930.KS`에 대해 에러 봉투 없이 시장 데이터를 반환하는 코드 경로를 가진 것은 `get_market_data`(pykrx 또는 Yahoo)와 `backtest`뿐이다. `get_financial_statements`, `get_stock_news`, `get_research_reports`는 지원 안 함 에러를 낸다. `get_fund_flow`는 최상위 `ok: true`로 감싸고 심볼 항목 안에만 오류를 넣는다. `get_margin_trading`은 `.KS`를 거부하지 않고 숫자 `005930`을 **A주 코드로 오분류**한다. `get_options_chain`은 Yahoo에 `005930.KS`를 그대로 보내며 결과는 외부 응답에 달려 있다(정적 확인 불가, 분기는 아래 표). 1차 보고서의 "`get_margin_trading`이 에러 봉투를 반환한다"는 부분은 **보고서 정정 필요**하다.
- 근거 (프리셋 도구 목록 원문): `src/swarm/presets/investment_committee.yaml:47-49`(bull) `tools: [bash, read_file, write_file, load_skill, get_market_data, factor_analysis, get_financial_statements, get_fund_flow, get_margin_trading, get_research_reports, get_stock_news]`, `:118-120`(bear)는 위 목록에 `get_options_chain`을 추가, `:190-192`(risk)는 `get_market_data, get_options_chain, options_pricing, options_payoff, get_financial_statements, get_fund_flow, get_margin_trading, get_research_reports, get_stock_news`, `:239`(PM) `tools: [bash, read_file, write_file, load_skill, backtest]`.

  | 도구 | `.KS` 분기 위치 | 원문 / 동작 | 결과 |
  |---|---|---|---|
  | `get_market_data` | `src/market_data.py:48`, `backtest/loaders/registry.py:220` | `(re.compile(r"^\d{6}\.(KS\|KQ)$", re.I), "pykrx")`, `"kr_equity": ["pykrx", "yahoo", "yfinance", "local"]` | **지원** (pykrx, 미설치면 yahoo) |
  | `backtest` | `backtest/runner.py:1541-1543` | `if "kr_equity" in markets: ... return KoreaEquityEngine(config)` | **지원** |
  | `factor_analysis`, `options_pricing`, `options_payoff` | `factor_analysis_tool.py:20`, `options_pricing_tool.py:92`, `options_payoff_tool.py:119` | 입력이 CSV 경로 또는 숫자 인자(`spot`, `strike` 등)이며 심볼을 받지 않음 | 시장과 무관(심볼 분기 없음) |
  | `get_financial_statements` | `financial_statements_tool.py:665-684,772-776` | `_classify_market`은 `SH/SZ/BJ/SS`, `US`, `HK`, `L`만 인식하고 `None` → `"code must carry a supported suffix: .SH/.SZ/.BJ, .US, .HK, or .L"` | **에러 봉투** |
  | `get_stock_news` | `stock_news_tool.py:43,45,353-358` | `_EM_SUFFIXES = ("SH", "SZ", "BJ")`, `_YAHOO_SUFFIXES = ("US", "HK")` → `unsupported market for code {code!r}; expected suffix in ...` | **에러 봉투** |
  | `get_research_reports` | `research_reports_tool.py:51,132-134` | `if suffix not in _A_SHARE_SUFFIXES:` → `"research reports are China A-share only (.SH/.SZ/.BJ); got '{code}'"` | **에러 봉투** |
  | `get_fund_flow` | `fund_flow_tool.py:100-113,238-248`, `eastmoney_client.py:261-267`, `tushare_fallbacks.py:93-101` | `resolve_secid`가 `.KS`에 `None` → tushare 폴백 `_ts_code`가 `TushareFallbackUnavailable(f"unsupported Tushare symbol: {code}")` → 심볼 항목 `{"symbol":..., "error": "unresolvable symbol", "fallback_error": ...}`. 그런데 최상위는 `"ok": True` | **데이터 없음, 최상위는 성공 봉투** |
  | `get_margin_trading` | `margin_trading_tool.py:49-72,175,190` | `_extract_code("005930.KS")`: `parts = ["005930","KS"]`, 첫 토큰이 `len(part) == 6 and part.isdigit()`이라 `"005930"` 반환(`:70`) → Eastmoney `filter: (SCODE="005930")`로 요청. 이후 분기: (i) Eastmoney 행 있음 → `ok:true`, (ii) 행 없음/거절 → `tushare_fallbacks.fetch_margin_trading("005930")`가 `_ts_code`에서 `"005930.SZ"`로 변환(`tushare_fallbacks.py:102-106`)해 `TUSHARE_TOKEN` 필요(`:22-27`) | **정적 확인 불가**: 분기점 `margin_trading_tool.py:190`(Eastmoney 응답), `tushare_fallbacks.py:22-27`(토큰). 가능한 결과는 A주 `005930`의 데이터가 있으면 엉뚱한 종목 데이터, 없으면 `ok:false`. 어느 쪽이든 "한국 미지원" 에러는 아니다 |
  | `get_options_chain` | `options_chain_tool.py:95`, `backtest/loaders/yahoo_client.py:72-95,381` | `yahoo_client.get_options(ticker)` → `map_symbol`은 `.KS`를 `return cleaned`로 그대로 통과 | **정적 확인 불가**: Yahoo의 `005930.KS` 옵션 응답에 달려 있음(`options_chain_tool.py:95`의 `except`는 `ok:false`로 포장). 코드는 한국 거부 분기가 없음 |
  | `bash`, `read_file`, `write_file`, `load_skill` | — | 시장 데이터 도구가 아님 (`bash`로 yfinance 스크립트를 짜면 가능하나 정형 경로 아님) | 해당 없음 |

- 동작 설명: 한국 종목 `005930.KS`로 위원회를 돌리면 bull/bear/risk는 `get_market_data`로 OHLCV를 얻는다. 재무·뉴스·리서치 3종은 에러 봉투, 수급은 "성공 봉투 + 심볼별 오류", 신용잔고는 A주 코드로 오분류된 호출, 옵션 체인은 Yahoo가 응답하는지에 달린다. PM은 `backtest`로 `005930.KS`를 돌릴 수 있다. "OHLCV + `get_financial_statements`" 문장은 `get_financial_statements`가 한국을 지원하지 않으므로 잘못된 서술이고, 실제로 확정된 데이터는 가격(OHLCV)과 백테스트뿐이다.
- 조사 범위: `investment_committee.yaml` 도구 목록 4곳 전체, 위 표의 도구별 `execute`와 시장 분기 함수(`_classify_market`, `_suffix_of`, `_extract_code`, `resolve_secid`, `_ts_code`, `map_symbol`), `ls src/tools` 전체에서 도구 이름 `name = "..."`을 확인해 프리셋의 11개 이름을 모두 대응시켰다(`get_options_chain` 등 누락 없음).

#### R1-Q4 답변
- 결론: **확정**. 알려 준다. 메인 에이전트의 `get_market_data` 결과는 심볼별 `_provenance`에 실제로 응답한 로더의 이름을 `source`로 담는다. pykrx 미설치로 Yahoo가 대신 응답하면 `source: "yahoo"`, `detected_source: "pykrx"`, `fallback_used: true`가 된다. 값은 "요청 소스"가 아니라 "실제 서빙 소스"다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/tools/market_data_tool.py:233-245` | `execute` | `"include_provenance": True,` ... `return fetch_market_data_json(**fetch_kwargs)` | 코드 확인 |
  | `src/market_data.py:90-94` | `get_loader` | `return get_loader_cls_with_fallback(source)` (기본 `loader_resolver`) | 코드 확인 |
  | `backtest/loaders/pykrx_loader.py:80,85-90` | `DataLoader` | `name = "pykrx"`, `is_available`: `import pykrx` 실패 시 `return False` | 코드 확인 |
  | `backtest/loaders/registry.py:612-673` | `get_loader_cls_with_fallback` | `if instance is not None and instance.is_available(): return loader_cls` → 아니면 `for market in loader_cls.markets:` `fallback = resolve_loader(market)` → `return type(fallback)` | 코드 확인 |
  | `backtest/loaders/registry.py:220` | `FALLBACK_CHAINS` | `"kr_equity": ["pykrx", "yahoo", "yfinance", "local"]` | 코드 확인 |
  | `backtest/loaders/yahoo_loader.py:191` | `DataLoader` | `name = "yahoo"` | 코드 확인 |
  | `src/market_data.py:335,344,383-388` | `_fetch_via_chain` | `loader_cls = loader_resolver(attempt_src)` → `serving_source = getattr(loader_cls, "name", None) or attempt_src` → `if used_source is None: used_source = serving_source` → `symbol_sources[symbol] = (serving_source, loader_cls)` | 코드 확인 |
  | `src/market_data.py:430-433` | `_emit` | `"source": used_source or src,` `"requested_source": source,` `"detected_source": src,` `"fallback_used": bool(used_source and used_source != src),` | 코드 확인 |
  | `src/market_data.py:535` | `fetch_market_data` | `results["_provenance"] = provenance` | 코드 확인 |
  | `backtest/runner.py:1803-1812` | `fetch_data_map` | `served_by = str(getattr(loader, "name", source) or source)` (백테스트 쪽 동일 보정, 1차 보고서가 인용한 곳) | 코드 확인 |

- 동작 설명: 기본 `source="auto"`에서 `detect_source("005930.KS")`는 `"pykrx"`다(`market_data.py:48`). `_chain_for`가 `kr_equity` 체인을 고르고 시도 순서는 `[pykrx, yahoo, yfinance, local]`이다(`market_data.py:312`의 `[src, *chain]`). 첫 시도에서 resolver가 `get_loader_cls_with_fallback("pykrx")`를 부르는데 pykrx가 없으면 `resolve_loader("kr_equity")`가 체인을 따라 처음 사용 가능한 `yahoo` 로더를 돌려준다(`registry.py:662-671`). `serving_source`는 pykrx가 아니라 `getattr(loader_cls, "name")` = `"yahoo"`다. 다음 시도 `yahoo`는 `serving_source in attempted_providers`로 건너뛴다(`market_data.py:345-346`). 결과 provenance는 위 표대로 `source: "yahoo"`, `requested_source: "auto"`(또는 사용자가 준 값), `detected_source: "pykrx"`, `fallback_used: true`다. 모델이 `source="pykrx"`를 명시해도 `requested_source: "pykrx"`, `source: "yahoo"`로 구분된다. 호출 결과가 비면 `_diagnostics`에 `source_unavailable`/`no_data` 등 시도 기록이 실린다(`market_data.py:327-330`의 `record(...)`, `:537`의 `results["_diagnostics"]`).
- 조사 범위: `src/tools/market_data_tool.py`, `src/market_data.py` 전문, `backtest/loaders/registry.py`의 `resolve_loader`·`get_loader_cls_with_fallback`·`FALLBACK_CHAINS`, `pykrx_loader.py`, `yahoo_loader.py`의 `name`. MCP 경로(`loader_resolver` 주입)는 별도 resolver라 이 답은 로컬 에이전트 도구 기준이다(`market_data_tool.py:240-243`).

#### R1-Q5 답변
- 결론: **확정**. `fundamentals_loader.py`는 SEC companyfacts의 `filed`(공시일) 필드로 PIT를 구현한다. 값은 `filed` 날짜 당일 이후의 날짜에서만 보이고, `period_end`로는 보이지 않는다. 기준일은 `load_fundamental_panel`의 `index` 인자(가격 프레임의 날짜 인덱스)다. 이 loader는 미국(SEC XBRL) 전용이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `backtest/loaders/fundamentals_loader.py:1-6` | 모듈 docstring | `values become visible on their SEC ``filed`` date, never on ``period_end``` | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:92,105` | `_extract_concept_series` | `"filed": item.get("filed"),` → `df["filed"] = pd.to_datetime(df["filed"], errors="coerce").dt.normalize()` (날짜 단위, 시각 없음) | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:111,118,127` | 같은 함수 | `keep = "first" if pit else "last"` → `drop_duplicates(subset=["period_end"], keep=keep)` (PIT 모드는 같은 기간의 **최초 공시본**만 유지, 정정·재공시본 배제) | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:160,315` | `_quarterly_flow_frames`, `_to_ttm_flow_series` | `"filed": max(annual["filed"], inside["filed"].max())`, `pd.NaT if pos < 3 else max(filed_values[pos - 3 : pos + 1])` (합성 Q4와 TTM은 구성 공시 중 **가장 늦은** `filed`에 앵커) | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:170-194` | `_ffill_pit` | `values = sparse.set_index("filed")["value"].sort_index()` → `aligned_index = values.index.union(target_index)` → `return values.reindex(aligned_index).ffill().reindex(target_index)` | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:197-205,233` | `load_fundamental_panel` | `index: pd.DatetimeIndex \| None = None` → `target_index = _target_index(start, end, index)` | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:520` | `_fetch_symbol_raw_frame` | `frame[field] = _ffill_pit(sparse, index)` | 코드 확인 |
  | `backtest/runner.py:1104,1117-1120` | `_inject_fundamental_panel` | `price_index = index` (없으면 `close.index`) → `load_fundamental_panel(..., pit=pit, source=source, index=price_index)` | 코드 확인 |
  | `src/tools/alpha_bench_tool.py:727` | 알파 벤치 | `load_fundamental_panel(symbols=list(close.columns), fields=fields, start=start, end=end, pit=True, index=close.index)` | 코드 확인 |
  | `backtest/loaders/fundamentals_loader.py:433,442` | `_resolve_ciks` | `cik = sec_edgar_client.cik_for(symbol)`, 전부 실패 시 `"fundamentals loader is US-only (SEC XBRL)..."` | 코드 확인 |

- 동작 설명: 호출자(runner의 팩터 패널 주입, `get_fundamentals` 도구, alpha_bench)가 가격 날짜 인덱스를 `index`로 넘긴다. loader는 SEC companyfacts에서 `period_end`/`filed`/`value`를 뽑고(`:92-105`), PIT 모드에서 기간별 최초 공시본만 남긴 뒤(`:111-127`), 값을 `filed` 날짜에 붙여 날짜 인덱스에 **앞으로 채우기(ffill)** 한다(`:191-194`). 날짜 D에서 보이는 값은 `filed <= D`인 가장 최근 공시다. 비교가 `<=`에 해당하므로 **공시일 당일 봉부터** 보인다. `filed`에 시각이 없어(`.dt.normalize()`) 장 마감 후 공시도 같은 날 봉에 반영된다. 이 한계(최대 1봉)는 코드에서 확인된 사실이고 방어 코드는 없다. `pit=False`는 최신 정정본을 쓰는 리서치 모드다(`:111`).
- 조사 범위: `fundamentals_loader.py` 전문(`_extract_concept_series`, `_quarterly_flow_frames`, `_ffill_pit`, `load_fundamental_panel`, `_to_ttm_flow_series`, `_load_symbol_raw_frame`, `_fetch_symbol_raw_frame`)과 호출처 `rg -n "load_fundamental_panel" agent --glob '*.py'`(`runner.py:1112`, `alpha_bench_tool.py:727`, `get_fundamentals_tool.py:180-188`). A주 재무 보강은 별도 경로(`engines/base.py:415-449`의 `_maybe_enrich_fundamentals` → `TushareFundamentalProvider`, `as_of=config.get("end_date")`)이며 이 질문 범위 밖이다.

#### R1-Q6 답변
- 결론: **없음 확정**. KIS 일봉 조회 함수 `get_historical_bars`에는 연속 조회 처리가 없다. `_get`으로 1회만 호출하고 응답 `output2`를 뒤집어 `limit`으로 자른다. 같은 파일의 `tr_cont` 연속 조회 헬퍼 `_get_paginated`는 잔고·체결 조회에만 쓰이고 일봉에는 쓰이지 않는다. 1차 보고서(`next.md` 6번)의 "연속 조회 미확인"은 "없음"으로 확정한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/trading/connectors/kis/sdk.py:421-465` | `get_historical_bars` | `payload = _get(cfg, "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", tr_id=_TR_CHART, params={... "FID_INPUT_DATE_1": "19900101", "FID_INPUT_DATE_2": end, ...})` → `bars = [_bar_to_dict(item) for item in reversed(_as_list(payload.get("output2")))]` → `capped = max(int(limit), 0)` → `"bars": bars[-capped:] if capped else []` | 코드 확인 |
  | `src/trading/connectors/kis/sdk.py:752-754` | `_get` | `body, _headers_out = _request(cfg, "GET", path, tr_id=tr_id, params=params)` / `return body` (응답 헤더 `tr_cont`를 버림) | 코드 확인 |
  | `src/trading/connectors/kis/sdk.py:762-809` | `_get_paginated` | `tr_cont`가 `F`/`M`이면 `CTX_AREA_FK100`/`CTX_AREA_NK100`을 다음 요청에 넣고 `tr_cont = "N"`, 최대 `_MAX_CONTINUATION_PAGES = 20`(`:99-101`) | 코드 확인 |
  | `src/trading/connectors/kis/sdk.py:334,659` | 호출처 | `_get_paginated`의 호출처는 `inquire-daily-ccld`(체결, `:334`)와 `inquire-balance`(잔고, `_balance`, `:659`) 둘뿐 | 코드 확인 |
  | `src/trading/connectors/kis/sdk.py:396,447` | `_get` 호출처 | `get_quote`(`:396`)와 `get_historical_bars`(`:447`)만 단발 `_get` 사용 | 코드 확인 |

- 동작 설명: 일봉 조회는 시작일 `19900101`~오늘(KST)로 한 번 요청한다(`:445-461`). 헤더의 `tr_cont`는 `_get`에서 버려지고(`:753`) `CTX_AREA_*` 값도 읽지 않으므로 응답이 한 페이지 상한(KIS 사양상 행 수 제한은 외부 API 문서에 달려 있고 코드는 값을 모른다)에서 끊겨도 뒤 구간을 요청하지 않는다. `limit`은 응답 이후에 `bars[-capped:]`로 적용되어(`:464-465`) 요청 크기를 줄이지 못한다. 상한 행 수 자체는 외부 사양이라 정적으로 확인할 수 없고(질문 범위 밖), 코드가 반복 조회를 하지 않는다는 점만 확정이다. 호출자 쪽 소비: `service.py:452` 근방의 `module.get_historical_bars(...)` 동적 호출과 `kis/classification.py:19`의 `READ` 분류가 전부이며 재호출 로직은 없다.
- 조사 범위: `sdk.py` 전체에서 `grep -n "tr_cont\|CTX_AREA\|ctx_area\|while\|next\|_get_paginated\|_get("` 실행. `get_historical_bars` 호출처는 `rg -n "get_historical_bars" agent --glob '*.py'`로 확인(`trading/service.py:432-464`의 커넥터 공통 디스패처, `kis/classification.py:19`). 질문이 가리킨 `kis/sdk.py:445-465`와 위 라인은 1~2줄 차이만 있다(호출 시작 `:447`).

#### R1-Q7 답변
- 결론: **없음 확정**. 도구 결과, grounding 게이트, swarm 사전 조회 어디에도 데이터 시각(봉 날짜, as-of)을 **현재 시각과 비교해** 경고·거절·확신도 하향을 하는 코드는 없다. 신선도는 시스템 프롬프트 문장(원칙 2)과 현재 날짜 주입에 맡겨져 있다. 1차 보고서의 `추론`은 "없음 확정"으로 올릴 수 있다.
- 근거 (현재 시각을 쓰는 코드와 왜 stale 검사가 아닌지):

  | 위치 | 식별자 | 내용 (원문 인용) | 판정 |
  |---|---|---|---|
  | `src/agent/context.py:45-47,268,319,346` | 시스템 프롬프트 | `2. **Every data point carries its as-of.** Financial data is always lagged.`, `Today is {current_datetime}.`, `current_datetime=now.strftime("%A, %B %d, %Y %H:%M UTC")` | 프롬프트 문장일 뿐, 코드 비교 없음 |
  | `src/swarm/worker.py:372-376` | `build_worker_prompt` | `Today is {now.strftime('%A, %B %d, %Y %H:%M UTC')}` | 날짜 주입만 |
  | `src/agent/grounding/__init__.py:12-14` | 모듈 docstring | `The rest of that contract — "state the as-of", "analysis, not advice", "refuse out loud" — stays in the system prompt on purpose.` | as-of 표기를 코드로 검사하지 않는다고 명시 |
  | `src/agent/grounding/evidence.py:28,382-410` | `_TIMESTAMP_FIELDS`, `_timestamp_matches_claim_date` | 주장 날짜와 증거 `timestamp`가 같은 날인지만 비교 | 나이 계산 아님 |
  | `src/goal/store.py:639` | `add_evidence` | `freshness_status = "fresh" if evidence.data_as_of else "unknown"` | `data_as_of` **존재 여부**만 보고 현재 시각과 비교하지 않음. 값이 1년 전이어도 `"fresh"` |
  | `src/goal/context.py:127` | 목표 컨텍스트 | `as_of={item.get('data_as_of') or 'unknown'}` | 표시만 |
  | `backtest/loaders/base.py:552-564` | `loader_cache_range_is_final` | `return end < dt.date.today()` | 캐시 저장 가능 여부(미완성 봉 고정 방지). 사용자에게 가는 경고 아님 |
  | `src/swarm/grounding.py:45-47,187-188` | swarm 사전 조회 | `It does not refresh data mid-run. ... long-running swarms will see stale data after many minutes`, `end = today or date.today()`, `start = end - timedelta(days=window_days)` | stale 가능성을 주석으로 인정하고 검사 없음 |
  | `src/tools/institutional_holdings_tool.py:385` | `_latest_reportable_quarter` | `cutoff = (today or date.today()) - timedelta(days=_FILING_LAG_DAYS)` | 기본 분기 선택용 계산, 결과 데이터 검사 아님 |
  | `src/tools/etf_holdings_tool.py:786-796` | `_lag_days` | `(filing_date - as_of).days` | 보고 기간 말~공시일 차이, 현재 시각과 무관 |

- 동작 설명: 도구가 돌려준 봉의 마지막 날짜가 며칠 전인지 계산해 경고하는 함수가 없다. 모델이 프롬프트 원칙 2에 따라 as-of를 적도록 유도할 뿐이다. 게이트는 가격 주장이 증거와 모순되는지, 심볼이 도구를 거쳤는지를 본다(`grounding/__init__.py:5-14`). `technical_indicator_tool.py:291-293`은 `datetime.now()`로 조회 구간 끝을 정하는 기본값 계산이다.
- 조사 범위: `rg -n -i "stale|fresh|as_of|asof|max_age|age_days|data_age|last_bar|latest_bar|outdated|lag_days|freshness|needs_refresh" agent/src agent/backtest --glob '*.py'`(테스트·`skills/` 제외 약 830줄 히트 중 채널 모듈의 토큰 갱신·세션 정리, goal 상태 enum, swarm 런 reaper 등은 데이터 시각과 무관해 배제). 추가로 `rg -n "datetime.now|date.today|utcnow|time\.time\(\)|now\(" src/agent src/tools src/swarm src/goal src/hypotheses src/session`로 현재 시각을 읽는 파일을 전수 확인했다: `src/agent/grounding/{ledger,evidence,release,identity}.py`는 기록 타임스탬프(`checked_at`, `recorded_at`)만, `block_trades/southbound/lockup/institutional_holdings/portfolio_risk`는 조회 구간 기본값이다. `agent/mcp_server.py:640-712`의 `data_as_of`는 goal 증거 필드를 전달할 뿐이다.

#### R1-Q8 답변
- 결론: **확정**. 상류 작업의 `report.md`(없으면 최종 텍스트)는 **자르기·요약·길이 상한 없이** 하류 워커 시스템 프롬프트의 `{upstream_context}`에 통째로 들어간다. 길이 제한은 간접적인 것 하나뿐이다. 워커 메시지 전체의 토큰 추정치가 `_MAX_TOKEN_ESTIMATE = 60_000`을 넘으면 그 워커가 `token_limit`으로 끝나 하류 작업이 `failed`가 된다. 1차 보고서의 "자르기 규칙은 못 찾음"은 "자르기 없음 + 60,000 토큰 추정 상한으로 실패"로 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/swarm/worker.py:1312-1322` | `_resolve_summary` | `content = report_path.read_text(encoding="utf-8").strip()` → `if content: return content` (전문 반환) | 코드 확인 |
  | `src/swarm/worker.py:940-942` | `run_worker` 종료 | `summary = response.content or last_assistant_content or "(no summary)"` → `summary = _resolve_summary(artifact_dir, summary)` | 코드 확인 |
  | `src/swarm/runtime.py:531` | `_run_layers` | `task_summaries[tid] = result.summary` | 코드 확인 |
  | `src/swarm/runtime.py:980-990` | `_execute_layer` | `for context_key, source_task_id in task.input_from.items(): if source_task_id in task_summaries: upstream[context_key] = task_summaries[source_task_id]` → `upstream_summaries=upstream` | 코드 확인 |
  | `src/swarm/worker.py:303-312` | `build_worker_prompt` | `sections.append(f"### {key}\n{summary}")` → `prompt_parts.append(agent_spec.system_prompt.replace("{upstream_context}", upstream_block))` | 코드 확인 |
  | `src/swarm/worker.py:118,703-715` | `_MAX_TOKEN_ESTIMATE` | `_MAX_TOKEN_ESTIMATE = 60_000` / `token_estimate = len(json.dumps(messages, ensure_ascii=False)) // 4` / `if token_estimate > _MAX_TOKEN_ESTIMATE:` → `status="token_limit"` | 코드 확인 |
  | `src/swarm/runtime.py:586-596` | 결과 처리 else 분기 | `completed`/`cancelled`가 아니면 `TaskStatus.failed`, `error=... or f"worker did not complete (status={result.status})"` | 코드 확인 |
  | `src/swarm/runtime.py:1157` | `_run_worker_with_retries` | `# Success (or timeout/token_limit/completed) — no more retries` (`token_limit`은 재시도 안 함) | 코드 확인 |

- 동작 설명: 상류 워커 종료 시 `_resolve_summary`가 `report.md` 전문 또는 마지막 어시스턴트 텍스트를 `WorkerResult.summary`로 만든다(`worker.py:940-942`). 러너가 이를 `task_summaries`에 쌓고(`runtime.py:531`) `input_from` 매핑대로 `upstream_summaries`를 구성해(`runtime.py:980-990`) 하류 워커에 넘긴다. `build_worker_prompt`가 `## Upstream Context` 블록을 만들어 `{upstream_context}` 자리에 치환한다(`worker.py:303-312`). 이 경로의 어디에도 문자 수 제한이 없다. 하류 워커의 ReAct 루프는 매 반복 시작 시 `messages`(시스템 프롬프트 포함) JSON 길이를 4로 나눈 값이 60,000을 넘는지 검사하고(`worker.py:703-704`), 넘으면 `token_limit`으로 종료한다. 이때 요약은 `last_assistant_content`(첫 반복이면 빈 값)나 `report.md`로 채워지며, 러너는 이를 `failed`로 기록한다(`runtime.py:586-596`). 즉 상류 보고서가 크면 하류가 잘린 입력을 받는 것이 아니라 **실패**한다. 모델이 읽는 도구 결과의 길이 제한 `truncate_tool_result`(`worker.py:1047`)는 상류 요약에는 적용되지 않는다.
- 조사 범위: `src/swarm/{worker,runtime,store,models,serialization}.py`에서 `rg -n -i "truncat|\[:\s*[0-9A-Za-z_]+\]|max_chars|MAX_|_LIMIT|token_estimate"` 실행. 히트는 `worker.py`의 이벤트 미리보기 `_truncate_preview`(200자, `:1192-1198`), `[:160]`·`[:40]`·`[:300]` 판별용 슬라이스(`:1264,1296`), 도구 결과 `truncate_tool_result`(`:1047`), 위의 `_MAX_TOKEN_ESTIMATE`뿐이고 모두 상류 요약 치환 경로 밖이다. `store.py`의 `[:limit]`은 목록 조회용이다(`:245`).

#### R1-Q9 답변
- 결론: **확정**. `run_swarm` 결과는 메인 루프에서 `ingest_tool_result`로 **들어간다**(도구 이름 제외 분기 없음). 그러나 swarm 보고서 안의 숫자는 `observed` 근거로 **등록되지 않는다**. 등록되는 수치는 결과 JSON의 숫자 리프(토큰 사용량, 태스크 `iterations`)뿐이고, 숫자가 들어 있는 `final_report`/`summary`는 문자열이라 숫자 증거가 되지 않는다. 단, 결과 문자열에 나온 티커는 세션 심볼로 등록된다(신원 허용용). 따라서 swarm 보고서의 가격을 최종 답변에 `observed`로 선언하면 게이트가 `no_evidence`로 거절하고, `cited`로 선언하면(출처를 같은 줄에 적는 조건) 값 검사 없이 통과한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/loop.py:3347-3354` | 도구 결과 후처리 | `if self._grounding is not None: self._grounding.ingest_tool_result(tool_name=tc.name, arguments=..., result=result, call_id=tc.id, success=success)` (모든 도구 호출 공통, 이름 필터 없음) | 코드 확인 |
  | `src/agent/loop.py:1149` | `run` | `self._grounding = GroundingLedger(run_dir=run_dir, user_message=user_message, history=history, ...)` (실행마다 생성) | 코드 확인 |
  | `src/agent/grounding/ledger.py:40-42,305-318` | `ingest_tool_result` | `_ANALYSIS_TOOLS = frozenset({"backtest", "factor_analysis", "run_shadow_backtest", "quantlib_call"})`, `self._track_session_symbols(arguments, result)` … `elif payload is not None: self._ingest_generic_numeric(tool_name, arguments, payload, call_id)` (`run_swarm`은 마지막 분기로 감) | 코드 확인 |
  | `src/agent/grounding/evidence.py:1109-1169` | `_ingest_generic_numeric` | `if _is_number(value): self._evidence.append(EvidenceRecord(... status="observed" ...))`, 문자열은 `visit`에서 처리되지 않음, 상한 `_MAX_GENERIC_EVIDENCE = 2_000`(`:30`) | 코드 확인 |
  | `src/agent/grounding/evidence.py:350-356` | `_is_number` | `isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))` | 코드 확인 |
  | `src/tools/swarm_tool.py:696-710` | `_format_result` | `"final_report": run.final_report or ""`, `"tasks": task_summaries`, `"token_usage": {"total_input_tokens": ..., "total_output_tokens": ...}` | 코드 확인 |
  | `src/swarm/serialization.py:20-38` | `serialize_task` | 숫자 필드는 `"iterations"`뿐, `"summary": task.summary`는 문자열 | 코드 확인 |
  | `src/agent/grounding/identity.py:1044` | `_track_session_symbols` | `found = _scan_symbols(rendered_arguments) \| _scan_symbols(result)` (결과 전문에서 티커 추출 → 세션 심볼 등록) | 코드 확인 |
  | `src/agent/grounding/policies.py:1725-1727` | `_check_observed` | `"no_evidence"`, `"is declared observed but this session holds no matching tool evidence to check it against"` | 코드 확인 |
  | `src/agent/grounding/policies.py:1983-2034` | `_check_cited` | 출처 노트가 있고 같은 줄에 보이면 통과, 값은 미검사 | 코드 확인 |

- 동작 설명: 메인 루프가 `run_swarm`을 실행하면 `loop.py:3348`이 결과 전문을 장부에 넘긴다. `run_swarm`은 `_ANALYSIS_TOOLS`에 없고 `get_market_data`/`read_file`도 아니므로 `payload`가 JSON 객체이면 `_ingest_generic_numeric`으로 간다. 이 함수는 JSON 숫자 리프만 `observed` 증거로 만드는데, `run_swarm` 결과의 숫자 리프는 `token_usage.*`와 `tasks[].iterations`뿐이다(`symbol=None`, 인자에 심볼 키가 없음). 보고서 본문(`final_report`, `tasks[].summary`)은 문자열이라 숫자가 증거로 파싱되지 않는다. 그래서 최종 답변에 swarm 수치를 가격처럼 쓰면 증거 없는 숫자로 취급된다(관련 정책의 세부는 R1-Q10). 한편 `_track_session_symbols`가 결과 문자열에서 티커를 긁어 세션 심볼에 추가하므로(`identity.py:1044`), swarm 보고서에 나온 종목은 "도구가 다룬 심볼"로 허용될 수 있다. 이는 숫자 증거가 아니라 신원 게이트용이다. swarm 워커 쪽은 `src/swarm/grounding.py`의 사전 조회 블록을 프롬프트에 넣는 방식이며 이 장부(`GroundingLedger`)와 별개다(1차 보고서의 "swarm 워커에는 적용되지 않는다"와 일치. 이 문장은 `loop.py:1149`의 장부가 메인 `AgentLoop.run`에서만 생성된다는 코드 사실에 근거한다).
- 조사 범위: `rg -n "ingest_tool_result" agent/src`(호출처 `loop.py:3348` 하나), `ledger.py:274-320` 분기 전체, `evidence.py` `_ingest_generic_numeric`·`_is_number`, `swarm_tool.py:456-710`, `swarm/serialization.py`, `identity.py:997-1049`. `run_swarm`이라는 문자열이 `src/agent/grounding/*.py`와 `loop.py`의 grounding 관련 코드에 없음을 `rg -n "run_swarm" src/agent/grounding src/agent/loop.py`로 확인했다(`loop.py`의 다른 용도는 grounding과 무관).

#### R1-Q10 답변
- 결론: **확정**. 허용 오차는 **상대 0.5%**(`_TOLERANCE = 0.005`)이고 절대 하한은 `1e-9`다. 소수점이 있는 숫자로 쓴 값은 추가로 "쓴 마지막 자릿수의 절반 단위" 이내여야 하며 상대 0.5% 상한(`ROUNDED_BAND = 0.005`)은 동일하다. 정의 위치는 `src/agent/grounding/policies.py:100`(`_TOLERANCE`), `:129-131`(`_close`), `:1523-1547`(`_within_written_precision`), `src/agent/grounding/figures.py:29`(`ROUNDED_BAND`)다. 질문에서 쓴 함수 이름 `_close` 계열과 `_validate_figures`/`_check_observed`가 모두 `policies.py`에 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/grounding/policies.py:99-100` | `_TOLERANCE` | `#: Relative band a value must fall in to count as matching evidence.` / `_TOLERANCE = 0.005` | 코드 확인 |
  | `src/agent/grounding/policies.py:129-136` | `_close`, `_close_any` | `return abs(value - target) <= max(abs(target) * _TOLERANCE, 1e-9)` / `return any(_close(value, target) for target in targets)` | 코드 확인 |
  | `src/agent/grounding/figures.py:25-29` | `ROUNDED_BAND` | `#: Maximum relative rounding gap; written precision can only narrow this.` / `ROUNDED_BAND = 0.005` | 코드 확인 |
  | `src/agent/grounding/policies.py:1523-1547` | `_within_written_precision` | `band = abs(target) * (ROUNDED_BAND if "." in written else _TOLERANCE)` / `if "." in written: band = min(band, _written_half_unit(written) * unit * (1 + 1e-9))` / `return abs(candidate - target) <= max(band, 1e-9)` | 코드 확인 |
  | `src/agent/grounding/policies.py:1479-1521` | `_matches_evidence` | `legacy_direct=True`이면 `_close_any(figure.value, direct)`(평평한 0.5%), 아니면 `_within_written_precision`. `scaled`(퍼센트↔분수, 낙폭 부호)도 같은 함수 | 코드 확인 |
  | `src/agent/grounding/figures.py:162-185` | `Declaration` 매칭 | 정확 일치 `abs(declaration.value - value) <= max(abs(value) * 1e-9, 1e-9)`, 소수 표기는 `half_unit` 이내이면서 `abs(item.value - value) <= abs(item.value) * ROUNDED_BAND` | 코드 확인 |
  | `src/agent/grounding/policies.py:1841-1857` | `_result_matches` (산식 결과) | `abs(value - abs(target)) <= max(abs(target) * _TOLERANCE, half_unit, 1e-9)` | 코드 확인 |
  | `src/agent/grounding/policies.py:571,660` | `_validate_figures` 호출처 | 선언 없는 숫자: `found = self._check_observed(figure, None, symbol, records)`, 선언된 observed: `issues.extend(self._check_observed(figure, declaration, symbol, records))` | 코드 확인 |
  | `src/agent/grounding/policies.py:1625,1733` | `_check_observed` 내부 | 선언에 ref가 있으면 `self._matches_evidence(figure, values, [] if money else values)`(`:1625`), 없으면 `self._matches_evidence(figure, direct, scaled, legacy_direct=True)`(`:1733`) | 코드 확인 |
  | `src/agent/grounding/ledger.py:371` | `_validate` | `issues.extend(self._validate_figures(content, block, figures))` | 코드 확인 |

- 동작 설명: 최종 답변의 숫자는 `_validate_figures`(`policies.py:463`)가 하나씩 `observed/derived/proposed/cited/count` 역할로 확인한다. `observed`는 `_check_observed`(`:1549`)에서 증거 값과 비교한다. 선언 ref가 있으면 ref가 가리킨 호출의 값들과 `_within_written_precision`으로, ref가 없는 가격 주장은 `legacy_direct=True`로 가격 증거 전체와 `_close_any`(상대 0.5%)로 비교한다. 예: 증거 100.00에 대해 `100.4`는 0.4%라 통과, `100.6`은 거절이다. 소수 둘째 자리까지 쓴 `0.82`는 0.82467을 0.5%(0.0041)와 반단위(0.005) 중 작은 쪽 `0.0041`로 판정하므로 거절되고(`figures.py:25-28`의 주석과 일치), `0.825`는 통과한다. 정수로 쓴 값(`6,700`)은 소수점이 없어 상대 0.5%만 적용된다(`policies.py:1528-1534`의 docstring).
- 조사 범위: `rg -n -i "tolerance|rel_tol|abs_tol|isclose|_close|1e-|_TOLERANCE|ROUNDED_BAND" agent/src/agent/grounding/*.py`. 다른 허용 오차 상수는 `grounding` 디렉터리에 없다(`math.isclose`는 쓰이지 않음). 보고서의 "`ast` 기반"은 산식 평가(`_formula_in_note` 등)를 가리키며 비교 허용 오차와 별개다.

#### R1-Q11 답변
- 결론: **확정**. 라이브 러너 턴의 system prompt는 일반 에이전트와 **같다**. 러너는 system prompt를 만들지 않고, 만든 텍스트(`_pin_mandate_prompt`)를 `SessionService.send_message`로 **사용자 메시지**로 보낸다. 이후 `AgentLoop.run` → `ContextBuilder.build_messages`가 원칙 4가 든 `_SYSTEM_PROMPT`를 system 메시지로 조립한다. 러너 전용 system prompt, 원칙 제거·치환 경로는 없다. 즉 system prompt(원칙 4 "Do not tell the user what to buy, sell, or hold")와 user 프롬프트("Trade freely INSIDE the limits below")는 **둘 다 같은 대화에 존재**하며 코드는 이 충돌을 조정하지 않는다. 모델이 실제로 어떻게 반응하는지는 정적으로 알 수 없다(질문 범위 밖).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/live/runtime/runner.py:242-245` | `_pin_mandate_prompt` | `"You are running an AUTONOMOUS live-trading tick under a bounded mandate. Trade freely INSIDE the limits below; you must NEVER place an order that would breach any limit — defer instead. ..."` | 코드 확인 |
  | `src/live/runtime/runner.py:511-525` | `_invoke_and_audit` | `prompt = _pin_mandate_prompt(self.broker, mandate, now)` → `result = await self._agent_caller(self._session_id, prompt)` | 코드 확인 |
  | `src/api/live_routes.py:754-755` | `_agent_caller` | `async def _agent_caller(sid: str, prompt: str): return await _run_live_session_attempt(svc, sid, prompt)` | 코드 확인 |
  | `src/api/live_routes.py:603` | `_run_live_session_attempt` | `receipt = await svc.send_message(session_id, prompt)` | 코드 확인 |
  | `src/session/service.py:244-300` | `send_message` | `message = Message(session_id=session_id, role=role, content=content)` (`role="user"` 기본) → `attempt = Attempt(... prompt=content)` → `self._run_attempt(...)` | 코드 확인 |
  | `src/session/service.py:543-561` | `_run_with_agent` | `agent = AgentLoop(registry=registry, llm=llm, event_callback=event_callback, max_iterations=50, persistent_memory=pm)` → `agent.run(user_message=attempt.prompt, history=history, session_id=session_id)` (system prompt 인자 없음) | 코드 확인 |
  | `src/agent/loop.py:918-926` | `AgentLoop.__init__` | 매개변수는 `registry, llm, memory, event_callback, max_iterations, persistent_memory`뿐 (system prompt 오버라이드 없음) | 코드 확인 |
  | `src/agent/loop.py:1158,1169` | `run` | `context = ContextBuilder(self.registry, self.memory, persistent_memory=self._persistent_memory)` → `messages = context.build_messages(llm_user_message, history)` | 코드 확인 |
  | `src/agent/context.py:385` | `build_messages` | `{"role": "system", "content": self.build_system_prompt(user_message)},` | 코드 확인 |
  | `src/agent/context.py:338-348` | `build_system_prompt` | `return _SYSTEM_PROMPT.format(...)` | 코드 확인 |
  | `src/agent/context.py:56-59` | 원칙 4 | `4. **Analysis, not advice.** Deliver evidence, mechanisms, scenarios, and risks. Do not tell the user what to buy, sell, or hold, and do not prescribe position sizes.` | 코드 확인 |

- 동작 설명: 러너 틱 → `LiveRunner._invoke_and_audit`(`runner.py:511`) → 주입된 `agent_caller`(`live_routes.py:754`) → `SessionService.send_message`(`live_routes.py:603`)로 `role="user"` 메시지 저장 → `_run_attempt` → `_run_with_agent`(`service.py:470`) → `AgentLoop.run` → `ContextBuilder.build_messages`가 system(`_SYSTEM_PROMPT`)+history+user(러너 프롬프트)를 조립한다. `build_system_prompt`는 `context.py`에서 호출되는 곳이 `build_messages` 하나뿐이고(`rg "build_system_prompt"` 결과) 모드별 분기가 없다. 러너 모듈 docstring도 `agent loop internals`를 건드리지 않는다고 명시한다(`runner.py:22`, `:335-337`). 실제 주문은 별도의 강제 게이트(`enforcement`)가 막는 구조이며, 프롬프트 충돌 자체는 코드로 해소되지 않는다.
- 조사 범위: `rg -n "LiveRunner\(|agent_caller" agent/src`(생성 지점 `live_routes.py:772` 하나), `rg -n "build_system_prompt|_SYSTEM_PROMPT|\"role\": \"system\"" agent/src/agent agent/src/session agent/src/api agent/src/live`(system 메시지 추가는 `loop.py:1317,1660,1688`의 지시 메시지뿐이고 `_SYSTEM_PROMPT` 대체가 아님). `session_config`로 system prompt를 바꾸는 경로가 없음은 `service.py:470-561`의 `_run_with_agent` 전문으로 확인했다.

#### R1-Q12 답변
- 결론: **확정**. 기본 설정(`VT_MEMORY=off`)에서 `find_relevant`는 **토큰 겹침 점수**(제목·설명·키워드 가중 2.0, 본문 1.0)로 계산해 점수 내림차순·동점 시 최신 수정순으로 상위 3건을 고른다. `VT_MEMORY_FTS_INDEX`가 켜져 있으면 SQLite FTS5 `rank` 순서로 먼저 시도하고 결과가 비면 같은 토큰 스캔으로 내려간다. 임베딩은 쓰지 않는다. 최소 점수 기준은 `token_score > 0`뿐이다. **추가 사실(보고서 반영 필요)**: 토큰화 정규식이 한글(Hangul) 범위를 포함하지 않아 한국어만 있는 질의는 토큰이 0개가 되어 **항상 빈 결과**다(숫자·영문 2자 이상 토큰만 있으면 동작).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/context.py:392-396` | `build_messages` | `if self._persistent_memory:` → `recalls = self._persistent_memory.find_relevant(user_message, max_results=3)` → `lines = [f"- **{r.title}** ({r.memory_type}): {r.body[:500]}" for r in recalls]` | 코드 확인 |
  | `src/memory/persistent.py:24-25` | 상수 | `MAX_RESULTS = 5` / `METADATA_WEIGHT = 2.0` | 코드 확인 |
  | `src/memory/persistent.py:149-151` | `_tokenize` | `return set(_TOKEN_RE.findall(text.lower()))` | 코드 확인 |
  | `src/memory/persistent.py:122` | `_TOKEN_RE` | `re.compile(rf"[a-zA-Z0-9]{{2,}}\|[{_NON_LATIN_SCRIPT_RANGES}]")` | 코드 확인 |
  | `src/memory/persistent.py:109-115` | `_NON_LATIN_SCRIPT_RANGES` | 코드포인트 `U+4E00-9FFF`(CJK), `U+3400-4DBF`(CJK 확장 A), `U+0E00-0E7F`(태국), `U+0620-064A`(아랍), `U+05D0-05EA`(히브리), `U+0400-04FF`(키릴). 한글(`U+AC00-D7A3`)은 없음 | 코드 확인 (파일에서 코드포인트를 직접 읽음) |
  | `src/memory/persistent.py:412-433` | `find_relevant` 토큰 스캔 | `query_tokens = _tokenize(query)` / `if not query_tokens: return []` / `token_score = len(query_tokens & meta_tokens) * METADATA_WEIGHT + len(query_tokens & kw_tokens) * METADATA_WEIGHT + len(query_tokens & body_tokens)` / `if token_score > 0:` / `scored.sort(key=lambda x: (-x[0], -x[1].modified_at))` / `results = [entry for _, entry in scored[:max_results]]` | 코드 확인 |
  | `src/memory/persistent.py:428-429` | 감쇠 | `if _is_decay_enabled(): final_score *= 0.5 + 0.5 * entry.importance` | 코드 확인 |
  | `src/memory/persistent.py:369-408` | FTS 경로 | `if cfg.fts_index_enabled:` → `matches = index.search(query, max_results=max_results)` → 감쇠 켜짐이면 `key=lambda pair: -pair[0].rank * (0.5 + 0.5 * pair[1].importance)`로 재정렬 → `return fts_results[:max_results]` | 코드 확인 |
  | `src/memory/search_index.py:363-377,554` | `search`, `_sanitize_fts_query` | `ORDER BY rank LIMIT ?`, 토큰 `r"[a-zA-Z0-9_]{2,}\|[一-鿿㐀-䶿]"` (한글 없음) | 코드 확인 |
  | `src/memory/persistent.py:435-466` | 링크 확장 | `if cfg.links_enabled and results:` 결과가 `max_results` 미만일 때만 연관 엔트리를 덧붙임 | 코드 확인 |
  | `src/config/env_schema.py:600,613,632` | 기본값 | `preset ... default="off"`, `decay_enabled` 기본 `False`, `fts_index_enabled` 기본 `False` (`VT_MEMORY=on`은 decay만, `full`은 FTS·링크까지 켬: `:558-582`) | 코드 확인 |

- 동작 설명: 기본 설정에서는 `cfg.fts_index_enabled`가 거짓이라 `persistent.py:412`의 토큰 스캔으로 간다. 질의를 영문·숫자 2자 이상 단어와 CJK 등 문자 단위로 쪼개 `set`을 만들고, 엔트리의 제목+설명, 키워드, 본문 토큰 집합과의 교집합 크기를 센다. 제목·설명 겹침 하나당 2점, 키워드 겹침 하나당 2점, 본문 겹침 하나당 1점이다(같은 단어가 제목과 키워드에 모두 있으면 4점+본문 1점까지 가산됨). 점수가 0보다 큰 엔트리만 후보가 되고 점수 내림차순, 동점이면 `modified_at` 큰 쪽(최신)이 앞선다. 상위 `max_results`=3건(`context.py:394`)을 `title`, `memory_type`, 본문 앞 500자로 주입한다(`context.py:396`). 한글만 있는 사용자 메시지는 `_tokenize`가 빈 집합을 돌려 `return []`이고(`:413-414`), FTS 켜짐일 때도 `_sanitize_fts_query`가 빈 쿼리를 돌려 `search`가 `[]`를 반환한 뒤 같은 토큰 스캔으로 내려가므로 마찬가지다. 한국어 사용자 메시지에 종목 코드(`005930`)나 영문 단어가 섞여 있으면 그 토큰으로만 매칭된다. 라이브 러너 틱 프롬프트는 영어라 영향이 없다.
- 보고서 정정/추가 필요: `03-decision.md` 4-1·4-7절과 `01-data.md` 1-1절의 "상위 3건 자동 recall"에 선택 산식(토큰 겹침 가중 2:1, 동점 시 최신순)과 한글 미토큰화 한계를 추가해야 한다.
- 조사 범위: `src/memory/persistent.py` `find_relevant` 전문(362-466), `_tokenize`·`_TOKEN_RE`·`_NON_LATIN_SCRIPT_RANGES`, `src/memory/search_index.py`의 `search`·`_sanitize_fts_query`·`_is_cjk_char`(`_CJK_RANGE_MAIN = (0x4E00, 0x9FFF)`, `_CJK_RANGE_EXT_A = (0x3400, 0x4DBF)`, `:29-30`), `src/config/env_schema.py:545-640`의 메모리 프리셋·플래그. 임베딩 사용 여부는 `rg -n -i "embedding" agent/src/memory`로 확인했다.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `ccxt_loader.py:343-364`(`result["funding_rate"] = 0.0` → `aligned` 대입), `market_data.py:415-421`(`df.reset_index().to_dict(orient="records")`, 컬럼 필터 없음), `market_data.py:67-77`(`-PERP` → `"tushare"`), `_market_hooks.py:456-462`(`hist = bar.get("funding_rate")`)를 열어 일치 확인. (a)·(b) 각각 통과 지점과 도달 조건(`source="ccxt"` + `-PERP`)이 제시되어 완료 조건 충족 |
| R1-Q2 | 없음 확정 | `options_chain_tool.py:31`(옵션 OI), `crypto_trading_desk.yaml:36,41,82,118`(도구 목록에 OI 전용 도구 없음) 확인. grep 패턴이 질문에 적은 목록(`open_interest`, `openInterest`, `onchain`, `tvl`, `defillama`, `glassnode` 등)과 동의어를 모두 포함하고, 스킬 문서가 지시하는 도구(`bash`+OKX REST, `read_url`)까지 제시함 |
| R1-Q3 | 해소 | `investment_committee.yaml:47-49,118-120,190-192,239` 도구 목록 원문, `margin_trading_tool.py:49-72`(`len(part) == 6 and part.isdigit()` → `"005930"` 반환), `fund_flow_tool.py:100-113,238-248`(`"ok": True` 최상위 봉투), `tushare_fallbacks.py`의 `startswith(("0","2","3"))` → `SZ` 분기를 열어 확인. 정적으로 정해지는 부분(어느 도구가 어떤 분기로 가는지)은 표로 모두 확정되었고, `get_margin_trading`·`get_options_chain`의 최종 응답만 Eastmoney/Yahoo 외부 응답에 의존하므로 혼합 결론을 허용함 |
| R1-Q4 | 해소 | `market_data.py:335-346,383-388`(`serving_source = getattr(loader_cls, "name", None) or attempt_src`), `:428-434`(`"source": used_source or src`, `"fallback_used"`), `registry.py:660-673`(같은 시장 폴백 `return type(fallback)`) 확인. 값이 실제 서빙 소스임을 정하는 코드 위치 제시됨 |
| R1-Q5 | 해소 | `fundamentals_loader.py:170-194`(`_ffill_pit`: `set_index("filed")` → `reindex(...).ffill()`), `:111,127`(`keep = "first" if pit else "last"`) 확인. 날짜 필드(`filed`), 비교 의미(`filed <= D`, 당일 포함), 기준일 인자(`index`) 모두 제시됨 |
| R1-Q6 | 없음 확정 | `kis/sdk.py:445-465`(`"FID_INPUT_DATE_1": "19900101"` 단발 `_get`, `bars[-capped:]`), `:750-756`(`_get`이 `_headers_out` 버림), `grep tr_cont` 결과 `_get_paginated` 호출처가 `:334`, `:659`뿐임을 직접 확인. grep 패턴이 완료 조건 목록을 충족 |
| R1-Q7 | 없음 확정 | `goal/store.py:639`(`"fresh" if evidence.data_as_of else "unknown"` — 존재 여부만), `swarm/grounding.py:45-47`(stale 가능성 주석), `grounding/__init__.py:12-14`(as-of는 프롬프트에 맡김) 확인. grep 패턴(`stale`, `fresh`, `as_of`, `asof`, `max_age`, `age_days` 등)과 `datetime.now`/`date.today` 전수 확인 및 각 히트의 배제 이유가 적혀 있어 범위 충분 |
| R1-Q8 | 해소 | `worker.py:1312-1322`(`_resolve_summary` 전문 반환), `:303-312`(`replace("{upstream_context}", upstream_block)`), `:118,703-715`(`_MAX_TOKEN_ESTIMATE = 60_000`, `status="token_limit"`), `runtime.py:980-990`(`upstream[context_key] = task_summaries[...]`) 확인. 경로 순서·상수·grep 결과 모두 제시. 단, 상류 실패 시 하류 처리가 새 의문으로 생겨 R2-Q2로 분리 |
| R1-Q9 | 해소 | `loop.py:3347-3354`(이름 필터 없는 `ingest_tool_result`), `ledger.py:274-320`(분기 전체, `run_swarm`은 `elif payload is not None: self._ingest_generic_numeric`), `evidence.py:1109-1135`(`_is_number` 리프만 증거화) 확인. `swarm_tool.py:522-666`이 완료까지 대기 후 `_format_result`를 돌려주는 동기 호출임도 확인. 다만 선언 없이 옮겨 적은 숫자의 처리(`policies.py:571` 이후)는 "R1-Q10 참조"로만 넘겨 추적되지 않았으므로 R2-Q1로 분리 |
| R1-Q10 | 해소 | `policies.py:99-100`(`_TOLERANCE = 0.005`), `:129-136`(`_close`: `max(abs(target) * _TOLERANCE, 1e-9)`), `:1523-1547`(`_within_written_precision`), `figures.py:25-29`(`ROUNDED_BAND = 0.005`) 확인. 호출처 `:571,660,1625,1733` 제시되어 완료 조건 충족 |
| R1-Q11 | 해소 | `runner.py:511-525`(`_pin_mandate_prompt` → `self._agent_caller`), `live_routes.py:603,754-755`(`svc.send_message`), `service.py:543-561`(`AgentLoop(...)`에 system prompt 인자 없음, `user_message=attempt.prompt`), `context.py:385`(`{"role": "system", "content": self.build_system_prompt(...)}`) 확인. 러너 전용 system prompt·치환 경로 없음이 호출 경로 전체로 확정됨 |
| R1-Q12 | 해소 | `persistent.py:109-122`(`_NON_LATIN_SCRIPT_RANGES`에 한글 범위 없음, `_TOKEN_RE`), `:412-433`(가중 2:2:1 토큰 겹침, `token_score > 0`, `(-score, -modified_at)` 정렬), `context.py:392-396`(`max_results=3`, `r.body[:500]`) 확인. 산식·동점·최소 점수·호출 인자 모두 제시. 한글 미토큰화는 보고서 반영 항목으로 기록 |

---

## Round 2

### 질문 (질문자)

#### R2-Q1. 선언 없이 최종 답변에 쓴 숫자를 게이트가 어떻게 처리하는가
- GUIDE 항목: Q4-5 (코드의 덮어쓰기·제한 장치)
- 왜 묻는가: R1-Q9 답변은 "swarm 보고서의 숫자는 증거가 되지 않는다", "`observed`로 선언하면 `no_evidence`, `cited`로 선언하면 통과"까지만 확정했다. 그런데 모델이 숫자를 **아무 역할 선언 없이** 본문에 옮겨 적는 경우는 "증거 없는 숫자로 취급된다(세부는 R1-Q10)"로 넘겼고, R1-Q10 답변도 이 경로를 다루지 않았다. `policies.py:570-571`의 `if declaration is None: found = self._check_observed(figure, None, symbol, records)` 이후 무엇이 일어나는지(거절, 경고, 통과)가 비어 있어, swarm 수치가 검증 없이 최종 답변에 실릴 수 있는지가 정해지지 않았다.
- 질문: 최종 답변 본문의 숫자가 grounding 선언 블록에 없을 때(`declaration is None`), 증거와 일치하지 않거나 증거가 없으면 `_validate_figures`는 그 숫자를 거절(issue 생성)하는가, 통과시키는가? 숫자의 종류(가격·퍼센트·정수·연도 등)나 선언 블록 존재 여부(`block.present`)에 따라 갈린다면 각 분기는?
- 답변 완료 조건: `policies.py:571` 이후 `found` 결과를 처리하는 분기의 `파일:라인`과 원문(issue 코드명 포함), 검사 대상에서 제외되는 숫자 유형을 정하는 코드의 `파일:라인`, 그리고 issue가 생겼을 때 최종 답변이 막히는지(재작성 요구·차단) 아니면 경고만 붙는지를 결정하는 `ledger.py`/`loop.py` 쪽 `파일:라인`.

#### R2-Q2. swarm 상류 작업이 실패하면 하류 작업은 어떻게 되는가
- GUIDE 항목: Q4-1 (입력 조립) / Q4-5 (실패 처리)
- 왜 묻는가: R1-Q8 답변은 하류 워커가 60,000 토큰 추정 상한을 넘으면 `token_limit` → `failed`가 된다고 확정했다. 그런데 `runtime.py:530-531`은 `if result.status == "completed": task_summaries[tid] = result.summary`로 **완료된 작업만** 요약을 저장하고, `runtime.py:980-990`은 `if source_task_id in task_summaries`일 때만 상류 맥락을 넣는다. 따라서 상류가 실패하면 하류(예: PM)가 (a) 건너뛰어지는지, (b) 그 상류 맥락 없이 그대로 실행되는지, (c) 런 전체가 실패하는지가 답변에 없다. (b)라면 PM이 일부 분석가 보고서 없이 결론을 내는 경로가 생긴다.
- 질문: 어떤 작업이 `failed`(또는 `token_limit`/`timeout`)로 끝났을 때, 그 작업을 `input_from`/`depends_on`으로 참조하는 하류 작업과 swarm 런 전체의 상태는 각각 어떻게 결정되는가? 하류 워커 프롬프트에 상류 실패 사실이 표시되는가?
- 답변 완료 조건: 실패 작업 처리 분기(`runtime.py:586-596` 근방)부터 다음 레이어 실행 여부를 정하는 코드까지의 `파일:라인`과 원문(건너뛰기·취소·계속 실행 조건), 런 최종 상태를 정하는 코드의 `파일:라인`, 하류 프롬프트에 실패 표시를 넣는 코드가 있으면 그 위치, 없으면 `build_worker_prompt`와 `_execute_layer`에서 확인한 범위와 grep 패턴(`failed`, `skipped`, `cancel`, `depends_on`, `upstream`).

### 답변 (답변자)

#### R2-Q1 답변
- 결론: **확정**. 선언 없는 숫자(`declaration is None`)는 **"측정값 모양"일 때만 검사**되고, 검사하면 **증거와 일치할 때만 통과**하며 증거가 없거나 어긋나면 **issue를 만들어 거절**한다(통과시키는 분기는 "증거 일치" 하나뿐). 선언 블록이 있으면(`block.present`) 이 issue의 코드는 `figure_undeclared`, 없으면 `_check_observed`가 만든 `numeric_claim_unavailable`(증거 없음) 또는 `numeric_claim_conflict`(값 불일치)다. issue가 하나라도 있으면 `valid=False`라 답변은 **차단**(재작성 요구)되며, 경고만 붙는 경로는 없다. 재작성 한도(`MAX_GROUNDING_REVISIONS = 2`)를 넘기면 숫자를 `(omitted※)`로 잘라낸 채 릴리스한다. 따라서 swarm 보고서에서 가격·퍼센트·소수 같은 **표식이 붙은 숫자**를 옮겨 적으면, 그 값이 이 세션의 숫자 증거(가격 봉·지표 등)와 0.5% 안에서 일치하지 않는 한 통과하지 못한다(swarm 숫자는 R1-Q9에서 확정했듯 증거가 아니다). 예외는 **표식 없는 평범한 정수**(`bare`)로, 종목 가격대에 해당하지 않으면 검사 자체를 건너뛴다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/grounding/figures.py:1074` | `scan_figures` | `marked = percent or currency or "." in token.digits or token.grouped` | 코드 확인 |
  | `src/agent/grounding/figures.py:1082-1090` | `scan_figures` 형태 분류 | `shape = "exempt"`(날짜·시각·코드 숫자·줄머리 번호·코드 펜스·표 행번호 열), `elif marked or (row is not None and not worded): shape = "measured"`, `else: shape = "bare"` | 코드 확인 |
  | `src/agent/grounding/figures.py:1011-1020` | docstring | `` * ``exempt`` — a date, time, security-code digits, line-leading ordinal ``…`` * ``measured`` — a decimal point, percent / pp / bp, touching currency mark …`` / `` * ``bare`` — a plain integer (counts, horizons, window lengths) …: unchecked.`` | 코드 확인 |
  | `src/agent/grounding/policies.py:537-538` | `_validate_figures` | `if figure.shape not in ("measured", "bare"):` → `continue` (exempt는 제외) | 코드 확인 |
  | `src/agent/grounding/policies.py:548-551` | `_validate_figures` | `if figure.shape == "bare" and not self._poses_as_price(figure, self._price_band(symbol, records)): continue` | 코드 확인 |
  | `src/agent/grounding/policies.py:1440-1460` | `_poses_as_price` | `if band is None or figure.percent: return False` / 소수는 `low * 0.9 <= value <= high * 1.1` / 정수는 `low >= _INTEGER_PRICE_FLOOR and low * 0.5 <= value <= high * 2.0` | 코드 확인 |
  | `src/agent/grounding/policies.py:570-571` | `_validate_figures` | `if declaration is None:` / `found = self._check_observed(figure, None, symbol, records)` | 코드 확인 |
  | `src/agent/grounding/policies.py:572-598` | 블록 있음 분기 | `if block.present and found:` → `self._figure_issue("figure_undeclared", figure, None, symbol, "undeclared", "is not declared in the figures block and is not an observed value; declare it as observed / derived / proposed / cited / count, or remove it", ...)` → `continue` | 코드 확인 |
  | `src/agent/grounding/policies.py:599-601` | 블록 없음 분기 | `checked_price = True` / `issues.extend(found)` / `continue` (`found`가 빈 리스트면 issue 없음 = 통과) | 코드 확인 |
  | `src/agent/grounding/policies.py:1719-1731` | `_check_observed` 증거 없음 | `if not direct and not scaled and not tail_risk: return [self._figure_issue("numeric_claim_unavailable", figure, "observed", symbol, "no_evidence", "is declared observed but this session holds no matching tool evidence to check it against", ...)]` | 코드 확인 |
  | `src/agent/grounding/policies.py:1733-1734` | `_check_observed` 일치 | `if self._matches_evidence(figure, direct, scaled, legacy_direct=True): return []` (통과 분기) | 코드 확인 |
  | `src/agent/grounding/policies.py:1755-1775` | `_check_observed` 불일치 | `"numeric_claim_conflict", figure, "observed", symbol, "value_mismatch", "is declared observed but conflicts with the … evidence …"` | 코드 확인 |
  | `src/agent/grounding/ledger.py:365-377` | `_validate` | `issues.extend(self._validate_figures(content, block, figures))` / `issues = self._dedupe_issues(issues)` / `result = ValidationResult(valid=not issues, issues=issues, ...)` | 코드 확인 |
  | `src/agent/loop.py:1722-1724` | 최종 답변 검증 | `self._grounding.validate_final_answer(final_content)` → `if not validation.valid:` | 코드 확인 |
  | `src/agent/loop.py:1753,1814-1818` | 거절 후 재작성 | `if not validation.valid:` … `messages.append({"role": "user", "content": f"<system>{self._grounding.correction_prompt(validation)}</system>"})` | 코드 확인 |
  | `src/agent/loop.py:1832-1846` | 재작성 한도 | `and grounding_revisions < MAX_GROUNDING_REVISIONS` 이면 `grounding_correction_text_only = True` 후 `continue` | 코드 확인 |
  | `src/agent/grounding/release.py:32` | 상수 | `MAX_GROUNDING_REVISIONS = 2` | 코드 확인 |
  | `src/agent/loop.py:1855-1858,1885` | 한도 초과 | `released = self._grounding.redacted_release(rejected_draft, validation)`; `None`이면 `final_content = self._grounding.safe_fallback()` | 코드 확인 |
  | `src/agent/grounding/release.py:35-42,563-564` | `_REDACTABLE_CODES`, `redacted_release` | `{"numeric_claim_conflict","numeric_claim_unavailable","unsourced_symbol_figures","figure_undeclared"}`(전부 잘라낼 수 있음), 시장 답변인데 가격 증거가 없으면 `return None` → 고정 폴백 | 코드 확인 |

- 동작 설명: `GroundingLedger._validate`(`ledger.py:365`)가 본문의 숫자를 `scan_figures`로 분류한다. (1) **exempt**(날짜·시각·종목코드 숫자·줄머리 번호·펜스 안·표의 행번호 열)는 `policies.py:537`에서 제외된다. (2) 소수점·퍼센트·통화표식·천 단위 구분(`1,234`)이 붙은 숫자는 `measured`로 검사 대상이다. (3) 표식 없는 정수는 `bare`이고, 종목의 관측 가격대에 해당할 때만(`_poses_as_price`: 정수는 가격이 `_INTEGER_PRICE_FLOOR` 이상인 종목에서 관측 범위의 0.5~2배, 소수는 ±10%) 검사하며 그 외는 `continue`로 통과한다. 증거가 없는 세션에서는 `band is None`이라 `bare`는 전부 통과한다. (4) 검사 대상이고 `block.match`가 선언을 못 찾으면(`declaration is None`) `_check_observed(figure, None, ...)`로 세션 전체의 가격·지표 증거와 대조한다(`ref` 없는 경로, `legacy_direct=True`, 허용 오차는 R1-Q10). 일치하면 `[]`이라 **통과**한다(선언 없이도 증거와 맞으면 허용). 증거가 하나도 없으면 `numeric_claim_unavailable`, 있으나 안 맞으면 `numeric_claim_conflict`가 반환된다. (5) 이때 선언 블록이 있으면(`block.present`) 코드는 `figure_undeclared`로 바뀌어 "declare it as observed / derived / proposed / cited / count, or remove it" 메시지를 받고, 블록이 없으면 `_check_observed`의 issue가 그대로 들어간다. 또한 `declared_in_other_unit`이 있으면(분수↔퍼센트 단위 차이) 메시지에 `declared_as`를 덧붙인다. (6) issue가 하나라도 있으면 `valid=False`이고 `loop.py:1753`의 거절 분기로 가서 `answer_rejected`를 기록하고, 먼저 `recovery_action`(식별 불명이면 `search_symbol`, 신원이 잠겼는데 `numeric_claim_unavailable`/`unsourced_symbol_figures`가 있으면 `get_market_data` 재조회, `release.py:309-330`)을 시도하며, 아니면 `correction_prompt`를 사용자 메시지로 넣어 다시 쓰게 한다(최대 `MAX_GROUNDING_REVISIONS=2`회). 한도를 넘기면 `redacted_release`가 거절된 숫자를 `(omitted※)`로 바꿔 릴리스하고 각주를 붙이며, 시장 답변인데 관측된 가격이 없거나(`release.py:563`) 신원 issue 등 못 자르는 issue가 있으면 `safe_fallback()` 고정 문구가 나간다. 경고만 붙이고 원문을 그대로 내보내는 경로는 없다. 결론적으로 swarm 보고서의 수치를 선언 없이 옮겨 적어도 (a) 표식 있는 숫자는 증거와 안 맞으면 거절, (b) 표식 없는 정수는 가격대 밖이면 **검증 없이 통과**한다. 라이브 러너·swarm 워커는 이 장부가 없다(R1-Q9 확정 사실).
- 보고서 정정/추가 필요: "증거 없는 숫자는 거절되지만 표식 없는 평범한 정수(개수·기간 등)는 검사 대상이 아니다"를 `03-decision.md`의 grounding 설명에 추가한다. 또한 R1-Q9 답변의 "`policies.py:1725-1727`"은 현재 파일에서 `:1719-1731`이다(`"no_evidence"` 문자열은 `:1726`).
- 조사 범위: `policies.py:455-680`(`_validate_figures` 전문), `:1440-1460`, `:1549-1790`(`_check_observed` 전문), `figures.py:1005-1110`(`scan_figures`), `ledger.py:300-400`, `release.py:28-61,175,309-340,536-600`, `loop.py:1700-1900`. `rg -n "figure_undeclared|numeric_claim_unavailable|numeric_claim_conflict" agent/src/agent/grounding agent/src/agent/loop.py`로 issue 코드의 생성·소비 지점을 확인했다. 경고 전용(비차단) 분기를 찾기 위해 `loop.py`에서 `validation.valid`·`validation.issues` 사용처를 전수 확인했고(`:1722-1869`) 차단 외 분기는 없었다.

#### R2-Q2 답변
- 결론: **확정**. 상류 작업이 `failed`·`timeout`·`token_limit`(또는 `cancelled`) 등 **`completed`가 아닌 상태로 끝나면**, 그 작업을 `depends_on`에 둔 하류 작업은 **(a) 건너뛰어진다**. 하류는 실행되지 않고 `TaskStatus.blocked`로 저장되며 `task_blocked` 이벤트가 나간다. (b)처럼 상류 맥락 없이 실행되는 경로는 `depends_on`으로 연결된 경우 없다. 런 전체는 **(c)처럼 즉시 중단되지는 않고** 같은 레이어의 독립 작업과 이후 레이어의 무관한 작업은 계속 실행되지만, `all_succeeded=False`가 되어 최종 `RunStatus.failed`가 된다(취소 신호가 켜졌으면 `cancelled`). 하류 워커 프롬프트에 "상류 실패"를 적는 코드는 없다(실패한 하류는 아예 프롬프트가 만들어지지 않는다). **보고서 보강 필요**: 런타임 주석이 말하듯 `input_from`만 있고 `depends_on`에는 없는 연결은 게이트되지 않아 상류 맥락이 조용히 빠진다(실제 프리셋 사용 여부는 아래 참고).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/swarm/runtime.py:530-531` | `_execute_run` 결과 처리 | `if result.status == "completed":` / `task_summaries[tid] = result.summary` | 코드 확인 |
  | `src/swarm/runtime.py:555-564` | 취소 | `elif result.status == "cancelled":` … `all_succeeded = False` / `TaskStatus.cancelled` | 코드 확인 |
  | `src/swarm/runtime.py:586-595` | 그 외 모든 상태 | `else:` `all_succeeded = False` / `task_store.update_status(tid, TaskStatus.failed, error=redact_internal_paths(result.error) or f"worker did not complete (status={result.status})", ...)` (`timeout`·`token_limit`·`failed`가 여기로 모여 `failed`로 저장, 요약은 `task_summaries`에 넣지 않음) | 코드 확인 |
  | `src/swarm/runtime.py:929-937` | `_execute_layer` 게이트 | `for dep_id in task.depends_on:` … `except FileNotFoundError: blocked_upstreams.append((dep_id, "missing"))` / `if dep_task.status != TaskStatus.completed: blocked_upstreams.append((dep_id, dep_task.status.value))` | 코드 확인 |
  | `src/swarm/runtime.py:939-958` | 건너뛰기 | `if blocked_upstreams:` → `task_store.update_status(tid, TaskStatus.blocked, error=f"Blocked: upstream not completed ({reason})", blocked_by=blocked_by_ids, ...)` → `"task_blocked"` 이벤트 → `continue` (워커 제출 없음) | 코드 확인 |
  | `src/swarm/runtime.py:920-928` | 설계 주석 | `"a failed risk_officer would let PM produce a \"decision\" with no risk input — which is safety-critical. Mark blocked and skip dispatch; same-layer peers with no shared upstream are unaffected."` | 코드 확인 |
  | `src/swarm/runtime.py:609-621` | 레이어 후처리 | `for tid in layer_task_ids: if tid in layer_results: continue` / `if task_store.load_task(tid).status == TaskStatus.completed: continue` / `all_succeeded = False` (차단된 작업을 런 실패로 계상) | 코드 확인 |
  | `src/swarm/runtime.py:637-638` | 최종 런 상태 | `RunStatus.cancelled if cancel_event.is_set() else RunStatus.completed if all_succeeded else RunStatus.failed` | 코드 확인 |
  | `src/swarm/runtime.py:646-651` | 최종 보고서 | `last_layer = layers[-1] if layers else []` / `if tid in task_summaries: run.final_report = task_summaries[tid]` (마지막 레이어 작업이 `blocked`/`failed`이면 `final_report`는 설정되지 않음) | 코드 확인 |
  | `src/swarm/runtime.py:980-984` | 상류 맥락 조립 | `for context_key, source_task_id in task.input_from.items(): if source_task_id in task_summaries: upstream[context_key] = task_summaries[source_task_id]` (게이트를 통과한 작업에만 도달) | 코드 확인 |
  | `src/swarm/runtime.py:1154-1157` | 재시도 | `if result.status != "failed":` → `# Success (or timeout/token_limit/completed) — no more retries` (`timeout`·`token_limit`은 재시도 없이 반환) | 코드 확인 |
  | `src/swarm/runtime.py:1033-1038` | 레이어 데드라인 | `results[tid] = WorkerResult(status="timeout", summary="", error=f"Worker exceeded layer deadline of {layer_deadline}s")` | 코드 확인 |
  | `src/swarm/worker.py:703-712` | `token_limit` | `if token_estimate > _MAX_TOKEN_ESTIMATE:` … `return WorkerResult(status="token_limit", summary=summary, ...)` (부분 요약이 있어도 `completed`가 아니라 위 `else`로 감) | 코드 확인 |
  | `src/swarm/worker.py:305-312` | `build_worker_prompt` | `if upstream_summaries:` … `"## Upstream Context (from previous agents)\n\n"` — 실패 표시 문자열 없음. 상류가 비어 있으면 `upstream_block = ""`로 치환 | 코드 확인 |
  | `src/swarm/presets.py:227-234` | 검증 경고 | `input_from` 참조가 DAG상 상류가 아니면 `warnings.append(f"Task '{task.id}' input_from '{key}' references '{upstream_task_id}', which is not upstream in the DAG")`(경고뿐, 로드 실패 아님) | 코드 확인 |
  | `src/tools/swarm_tool.py:626-629,697-704` | `run_swarm` 반환 | `"status": run.status.value`, `"final_report": run.final_report or ""`, `"error": run_level_error(run)`, `"tasks": task_summaries` (메인 에이전트가 `failed` 런 상태와 작업별 상태를 받음) | 코드 확인 |

- 동작 설명: `_execute_run`는 `topological_layers`(`runtime.py:479`)로 만든 레이어를 순서대로 실행한다. 각 레이어에서 `_execute_layer`가 작업마다 `depends_on`의 상태를 `task_store`에서 읽어(`:929-937`) 하나라도 `completed`가 아니면 `blocked`로 저장하고 `continue`한다. 같은 레이어의 다른 작업은 영향받지 않는다. 워커가 돌아와도 `status`가 `completed`가 아니면(`failed`, `timeout`, `token_limit`) `:586-595`에서 `failed`로 저장하고 요약은 `task_summaries`에 넣지 않는다. 다음 레이어에서 이 작업을 `depends_on`으로 가진 작업(예: PM)은 `:936`의 게이트에서 `blocked`가 된다. `blocked` 작업은 `layer_results`에 없으므로 `:616-621`이 `all_succeeded=False`로 만든다. 그 결과 레이어 순회가 중단되지는 않고(취소 신호만 `:497-501`에서 중단) 끝까지 돌아 `RunStatus.failed`로 확정되며(`:637-638`), 마지막 레이어 작업이 `task_summaries`에 없으면 `final_report`가 빈 문자열이다. 메인 에이전트는 `run_swarm`의 `status:"failed"`와 `tasks[].status`(`blocked`/`failed`)를 받는다. 하류 프롬프트에 실패 표시를 넣는 코드는 필요가 없고 존재하지도 않는다: 막힌 작업은 프롬프트가 만들어지지 않고, 실행되는 작업에서는 `:980-984`가 `completed`된 상류의 요약만 `upstream`에 담는다. 유일한 틈은 `input_from`만 쓰고 `depends_on`에는 쓰지 않은 연결이다. 이 경우 `:929`의 게이트가 보지 않으므로 상류가 실패해도 하류가 상류 맥락 없이 실행되고, 로더는 경고만 낸다(`presets.py:229-234`는 "DAG상 상류가 아닐 때"의 경고이며, `input_from`⊆`depends_on`을 강제하는 코드는 찾지 못했다). 프리셋별로 이 불일치가 실제로 있는지는 이 질문의 범위(코드의 처리 규칙) 밖이다. 다만 "상류가 실패하면 PM이 일부 보고서 없이 결론을 낸다"는 경로는 `depends_on`이 `input_from`을 포함하는 프리셋에서는 막혀 있다.
- 보고서 정정/추가 필요: 1차 보고서에 swarm 상류 실패 시 하류 `blocked` 처리와 런 `failed` 확정(`runtime.py:929-958`, `:616-621`, `:637-638`)이 없다면 추가해야 한다. 또한 R1-Q8 답변의 "하류 워커가 `token_limit`이면 `failed`"는 맞지만, 그 부분 요약(`summary`)은 `task_summaries`에 들어가지 않으므로(`:530`의 `completed` 한정) 더 하류로 전달되지 않는다는 점을 보강한다.
- 조사 범위: `src/swarm/runtime.py:430-670`(`_execute_run` 전문), `:866-1045`(`_execute_layer` 전문), `:1140-1200`(재시도·`_cancel_remaining_tasks`), `src/swarm/worker.py:223-320`(`build_worker_prompt`), `:660-715`, `src/swarm/task_store.py:207-252`(`topological_layers`), `src/swarm/presets.py:190-240`, `src/swarm/models.py:120-135,200-250`, `src/tools/swarm_tool.py:595-710`. grep 패턴: `rg -n "blocked|failed|skipped|cancel|depends_on|upstream|input_from" agent/src/swarm/runtime.py agent/src/swarm/worker.py agent/src/swarm/presets.py`(`skipped`는 swarm 런타임에 상태로 쓰이지 않음, 건너뛰기는 `blocked`만 사용). 정적 확인 불가 항목은 없다.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R2-Q1 | 해소 | `policies.py:537-551`(`shape not in ("measured","bare")` → `continue`, `bare`는 `_poses_as_price` 아니면 `continue`), `:570-601`(`declaration is None` → `_check_observed(figure, None, ...)`, `block.present and found`면 `figure_undeclared`, 아니면 `issues.extend(found)`), `:1719-1734`(`numeric_claim_unavailable` / `_matches_evidence(..., legacy_direct=True)`면 `return []`), `ledger.py:374`(`valid=not issues`), `loop.py:1724`(`if not validation.valid:`), `:1855-1858`(`redacted_release`), `release.py:30-42`(`MAX_GROUNDING_REVISIONS = 2`, `_REDACTABLE_CODES`)를 열어 일치 확인. 완료 조건 3가지(`found` 처리 분기와 issue 코드, 제외 유형을 정하는 코드, 차단 여부를 정하는 `ledger`/`loop` 위치)를 모두 충족. 경고 전용 분기가 없다는 점도 `validation.valid` 사용처 전수 확인으로 뒷받침됨 |
| R2-Q2 | 해소 | `runtime.py:530-531`(`completed`만 `task_summaries`), `:586-595`(그 외 상태 → `TaskStatus.failed`), `:918-958`(`depends_on` 중 하나라도 `!= TaskStatus.completed`면 `TaskStatus.blocked` + `task_blocked` + `continue`), `:609-621`(차단 작업 → `all_succeeded = False`), `:636-651`(`RunStatus.failed`, `final_report`는 마지막 레이어 요약이 있을 때만), `presets.py:228-234`(DAG상 상류가 아닌 `input_from`은 경고만)를 열어 확인. 하류 처리·런 상태·실패 표시 부재가 모두 `파일:라인`으로 제시됨. 추가로 `presets.py:214-224`의 `is_upstream`이 의존 간선을 따라가는 **전이적** 검사임을 확인함(조상 작업을 `input_from`으로 참조하는 경우는 중간 작업이 `blocked`되어 연쇄 차단되므로 틈이 아님). 남은 틈은 "DAG상 상류가 아닌 작업을 `input_from`으로 참조"하는 경우뿐이며, 기본 제공 프리셋에 그런 연결이 있는지는 답변이 범위 밖으로 남겼으므로 R3-Q1로 분리 |

---

## Round 3

### 질문 (질문자)

#### R3-Q1. 기본 제공 swarm 프리셋에 `depends_on` 게이트를 우회하는 `input_from` 연결이 있는가
- GUIDE 항목: Q4-1 (입력 조립) / Q4-5 (실패 처리)
- 왜 묻는가: R2-Q2 답변은 상류 실패 시 하류가 `blocked`된다고 확정했지만, 게이트(`runtime.py:929-937`)는 `depends_on`만 본다. `input_from`이 DAG상 상류가 아닌 작업(전이적으로도 `depends_on`으로 닿지 않는 작업)을 가리키면 그 상류가 실패해도 하류는 그 맥락 없이 실행되고, 로더는 경고만 낸다(`presets.py:228-234`). 답변은 "프리셋별로 이 불일치가 실제로 있는지는 범위 밖"이라고 남겼다. 기본 제공 프리셋(`src/swarm/presets/*.yaml`, 30개)에 이런 연결이 하나라도 있으면 "PM이 일부 보고서 없이 결론을 내는 경로"가 실제 프리셋에 존재하는 것이므로 확정이 필요하다. 또 이 경고가 `run_swarm` 실행을 막는지(에러로 승격되는지)도 같은 사실의 일부다.
- 질문: `src/swarm/presets/*.yaml`의 모든 작업 중 `input_from`의 값이 그 작업의 `depends_on`에서 (전이적으로) 도달할 수 없는 작업을 가리키는 경우가 있는가? 그리고 `presets.py`의 `warnings`는 `run_swarm`/프리셋 로드 경로에서 실행을 중단시키는가, 아니면 무시·표시만 되는가?
- 답변 완료 조건: (1) 30개 프리셋 각각에 대해 `input_from` 값 ⊆ (전이적) `depends_on` 여부를 확인한 방법(스크립트 없이 읽은 경우 프리셋별 표, 또는 grep 결과)과, 위반이 있으면 프리셋 파일명·작업 ID·`파일:라인` 원문. 없으면 확인한 프리셋 목록. (2) `warnings` 리스트가 반환된 뒤 소비되는 지점(`swarm_tool.py`·`runtime.py` 등)의 `파일:라인`과 원문(중단 / 로그 / 무시).

### 답변 (답변자)

#### R3-Q1 답변
- 결론: **없음 확정**. 위반(상류가 아닌 `input_from`)은 번들 프리셋에 없고, 경고를 실행 경로에서 소비하는 코드도 없다. 세부는 다음과 같다.
  1. 기본 제공 프리셋 30개의 `input_from` 104개 전부가 같은 작업의 `depends_on`에서 (전이적으로) 도달 가능한 작업을 가리킨다. `presets.py`의 `is_upstream` 기준 경고 대상(DAG상 상류가 아닌 `input_from`)은 **0건**이고, 존재하지 않는 작업을 가리키는 `input_from`도 0건이다. 따라서 "게이트를 우회해 PM이 일부 보고서 없이 결론을 내는 경로"는 기본 제공 프리셋에는 **없다**(사용자 프리셋 `~/.vibe-trading/swarm/presets/`는 정적으로 알 수 없음).
  2. `presets.py`의 `warnings`는 `inspect_preset()`의 반환 딕셔너리에만 들어간다. `inspect_preset`의 호출처는 CLI `cmd_swarm_inspect`와 테스트뿐이고, `run_swarm`/`SwarmRuntime.start_run`의 실행 경로(`build_run_from_preset` + `validate_dag`)는 `inspect_preset`을 호출하지 않는다. 즉 경고는 **실행을 중단시키지도, 실행 경로에서 읽히지도 않는다.** `swarm inspect` 화면에서는 노란색 `WARN` 행으로 표시만 되고 종료 코드는 `errors` 기준(`valid`)이며 경고는 종료 코드에 영향이 없다.
- 보충 사실(질문 범위 밖이지만 R2-Q2와 직결): 104개 중 **12쌍**(7개 프리셋)는 `depends_on`에 **직접** 적혀 있지 않고 **간접(조상)** 으로만 연결된다. 이 경우 게이트(`runtime.py:929-937`)는 직접 의존만 보지만, 중간 작업이 `completed`가 아니면 그 작업이 `blocked`가 되어(`!= TaskStatus.completed`) 하류도 연쇄로 `blocked`되므로 우회 경로가 아니다. 즉 조상이 실패하면 중간 작업은 `blocked`(= `completed` 아님)가 되므로 중간 작업만 성공하는 경우는 없다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/swarm/presets.py:210-212` | `dependents` 구성 | `for task in run.tasks:` / `for dep in task.depends_on:` / `dependents[dep].append(task.id)` | 코드 확인 |
  | `src/swarm/presets.py:214-226` | `is_upstream` | `"""Return whether candidate can reach task_id through dependency edges."""` — `stack.extend(dependents.get(current, []))`로 의존 간선을 따라가는 전이적 검사 | 코드 확인 |
  | `src/swarm/presets.py:229-234` | 경고 생성 | `if upstream_task_id in task_id_set and not is_upstream(upstream_task_id, task.id):` → `warnings.append(f"Task '{task.id}' input_from '{key}' references '{upstream_task_id}', " "which is not upstream in the DAG")` | 코드 확인 |
  | `src/swarm/presets.py:196-200` | 존재하지 않는 작업 | `errors.append(f"Task '{task.id}' input_from references unknown task '{upstream_task_id}'")` (이 경우는 경고가 아니라 에러) | 코드 확인 |
  | `src/swarm/presets.py:261-263` | 반환값 | `"valid": not errors,` / `"errors": errors,` / `"warnings": warnings,` (`valid`는 경고와 무관) | 코드 확인 |
  | `src/swarm/runtime.py:327-328` | `start_run` 로드 경로 | `run = build_run_from_preset(preset_name, user_vars)` / `validate_dag(run.tasks)` — `inspect_preset`·`warnings` 사용 없음 | 코드 확인 |
  | `agent/cli/_legacy.py:2703-2706` | 유일한 비테스트 호출처 | `from src.swarm.presets import inspect_preset` / `report = inspect_preset(preset)` (`cmd_swarm_inspect`, 실행 명령이 아니라 점검 명령) | 코드 확인 |
  | `agent/cli/_legacy.py:2763-2766` | 경고 표시 | `if report["warnings"]:` / `validation_table.add_row("[yellow]WARN[/yellow]", warning)` | 코드 확인 |
  | `agent/cli/_legacy.py:2770` | 종료 코드 | `return EXIT_SUCCESS if report["valid"] else EXIT_RUN_FAILED` (경고만 있으면 성공) | 코드 확인 |
  | `agent/tests/test_swarm_preset_inspect.py:8-14` | 테스트 | `assert report["valid"], ...` — 번들 프리셋 전부 `errors` 없음을 검사, `warnings`는 검사하지 않음 | 코드 확인 |
  | `src/swarm/runtime.py:929-937` | 게이트(R2-Q2) | `for dep_id in task.depends_on:` … `if dep_task.status != TaskStatus.completed: blocked_upstreams.append(...)` | 코드 확인 |

- 프리셋별 확인 결과(`src/swarm/presets/*.yaml` 30개 전부; 모든 작업의 `input_from` 값이 같은 작업의 `depends_on` 조상 집합에 속하는지 YAML을 파싱해 검사. 열은 작업 수 / `input_from` 항목 수 / 위반 수):

  | 프리셋 | 작업 | input_from | 위반 | | 프리셋 | 작업 | input_from | 위반 |
  |---|---|---|---|---|---|---|---|---|
  | commodity_research_team | 3 | 2 | 0 | | investment_committee | 4 | 3 | 0 |
  | convertible_bond_team | 4 | 3 | 0 | | macro_rates_fx_desk | 4 | 3 | 0 |
  | credit_research_team | 4 | 3 | 0 | | macro_strategy_forum | 4 | 3 | 0 |
  | crypto_research_lab | 4 | 3 | 0 | | ml_quant_lab | 3 | 2 | 0 |
  | crypto_trading_desk | 4 | 3 | 0 | | pairs_research_lab | 4 | 5 | 0 |
  | derivatives_strategy_desk | 3 | 3 | 0 | | portfolio_review_board | 4 | 3 | 0 |
  | earnings_research_desk | 4 | 3 | 0 | | quant_strategy_desk | 5 | 7 | 0 |
  | equity_research_team | 4 | 6 | 0 | | risk_committee | 4 | 3 | 0 |
  | etf_allocation_desk | 4 | 3 | 0 | | sector_rotation_team | 4 | 3 | 0 |
  | event_driven_task_force | 3 | 3 | 0 | | sentiment_intelligence_team | 4 | 3 | 0 |
  | factor_research_committee | 4 | 5 | 0 | | social_alpha_team | 4 | 3 | 0 |
  | fund_selection_panel | 3 | 3 | 0 | | statistical_arbitrage_desk | 4 | 5 | 0 |
  | fundamental_research_team | 4 | 3 | 0 | | technical_analysis_panel | 6 | 5 | 0 |
  | geopolitical_war_room | 4 | 3 | 0 | | value_investing_committee | 5 | 4 | 0 |
  | global_allocation_committee | 4 | 3 | 0 | | global_equities_desk | 4 | 3 | 0 |

  합계 30개 프리셋, `input_from` 104개, 위반 0, 존재하지 않는 작업 참조 0. 직접 `depends_on`에 없고 조상으로만 닿는 항목(12쌍)은 다음 7개 프리셋에 있다: `derivatives_strategy_desk`(`task-greeks`←`task-vol`), `equity_research_team`(`task-stock`←`task-macro`, `task-aggregate`←`task-macro`/`task-sector`), `event_driven_task_force`(`task-strategy-build`←`task-event-scan`), `factor_research_committee`(`task-review`←`task-mine`/`task-validate`), `fund_selection_panel`(`task-fof-optimize`←`task-fund-screen`), `pairs_research_lab`(`task-microstructure-review`←`task-correlation-scan`/`task-cointegration-test`), `statistical_arbitrage_desk`(`task-risk-review`←`task-pair-scan`/`task-microstructure`). 이 12쌍은 모두 전이적으로 `depends_on`에서 도달 가능하므로 `is_upstream`이 참이다.
- 동작 설명: `inspect_preset`(`presets.py:171`)은 `depends_on` 간선으로 `dependents` 역방향 그래프를 만들고(`:210-212`), 각 `input_from` 대상이 이 그래프로 해당 작업에 도달하는지(`is_upstream`, `:214-226`) 확인해 도달하지 못하면 `warnings`에 문자열을 넣는다(`:229-234`). 30개 번들 프리셋 전부 이 조건을 만족해 이 경고는 번들 프리셋에서 발생하지 않는다. 실행 경로는 `SwarmRuntime.start_run`이 `build_run_from_preset` → `validate_dag`(`runtime.py:327-328`)만 호출하며 `inspect_preset`을 거치지 않는다. 따라서 경고가 있어도 없어도 실행 결과는 같고, 사용자가 `swarm inspect`를 실행했을 때만 `WARN` 행으로 보인다. 이는 R2-Q2의 "상류 실패 시 하류 blocked" 결론을 번들 프리셋 전체에 그대로 적용할 수 있다는 뜻이다.
- 보고서 정정/추가 필요: 1차 보고서에 "번들 프리셋 30개의 `input_from`은 모두 `depends_on` 조상이며, 상류 실패 시 PM/aggregator 등 하류는 `blocked`된다. 단 `presets.py`의 `input_from` 경고는 `swarm inspect`에서만 표시되고 실행을 막지 않는다(사용자 프리셋은 같은 보호가 없다)"를 추가한다.
- 조사 범위: `agent/src/swarm/presets/*.yaml` 30개 전부(`ls` 결과 30개, 비 YAML 파일 0개)를 Ruby `YAML.safe_load`로 파싱해 각 작업의 `input_from` 값이 `depends_on` 조상(전이적) 집합에 속하는지, 그리고 직접 `depends_on`에 속하는지를 검사했다(스크립트는 저장소 밖 scratchpad에서만 실행, 저장소 코드는 실행하지 않음). 검사 결과 전이적 위반 0건, 알 수 없는 작업 참조 0건. `grep -n "input_from" presets/*.yaml`은 41줄이며 이는 `input_from:` 키를 가진 작업 수 등을 센 것이고, 항목(키-값) 수 104는 파싱 결과다. 경고 소비처는 `grep -rn "inspect_preset" .`(저장소 전체)로 `src/swarm/presets.py:171`(정의), `src/swarm/__init__.py:14,30`(재노출), `agent/cli/_legacy.py:2703,2706`(CLI), `agent/tests/test_swarm_preset_inspect.py`, `agent/tests/test_swarm_presets_packaging.py:101,115`(테스트)만 존재함을 확인했고, `src/tools/swarm_tool.py`·`api_server.py`·`runtime.py`에는 `inspect_preset`/`warnings` 사용이 없다. 사용자 프리셋 디렉터리(`presets.py:34`, `~/.vibe-trading/swarm/presets`)의 내용은 정적 분석 범위 밖이다.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R3-Q1 | 없음 확정 | (1) 직접 검증: 저장소 밖에서 Ruby `YAML.safe_load`로 `agent/src/swarm/presets/*.yaml` 30개 전부를 다시 파싱해 각 `input_from` 값이 같은 작업의 `depends_on` 전이 조상 집합에 속하는지 검사함 → `input_from` 104개, 위반 0, 직접 `depends_on`에 없고 조상으로만 닿는 항목 12개로 답변 수치와 일치. 추가로 `equity_research_team.yaml:114-141`(`task-aggregate`: `depends_on: [task-stock]`, `input_from`에 `task-macro`·`task-sector` → 조상 경유), `quant_strategy_desk.yaml:148-181`(작업 5 / `input_from` 7, `task-report`가 4개 모두 직접 `depends_on`), `pairs_research_lab.yaml:286-311`(`task-microstructure-review`가 `task-correlation-scan`·`task-cointegration-test`를 조상으로만 참조), `investment_committee.yaml:246-269`(`task-decision`: `depends_on: [task-risk]`, `input_from: full_debate: task-risk`)를 눈으로 대조함. (2) `presets.py:196-200`(미존재 작업은 `errors`), `:210-234`(`is_upstream` 전이 검사 → `warnings.append`), `:261-263`(`"valid": not errors`), `runtime.py:327-328`(`build_run_from_preset` → `validate_dag`, `inspect_preset` 미호출), `_legacy.py:2703-2706,2763-2770`(`WARN` 행 표시, `return EXIT_SUCCESS if report["valid"] else EXIT_RUN_FAILED`) 확인. `grep -rn inspect_preset` 결과 테스트 외 호출처가 `presets.py:171`(정의), `swarm/__init__.py:14,30`(재노출), `_legacy.py:2703,2706`뿐임을 직접 확인. 완료 조건 (1) 프리셋 전체 목록·방법·결과, (2) `warnings` 소비 지점(실행 경로 없음, CLI 표시만) 모두 충족. 사용자 프리셋 디렉터리 내용은 런타임 파일이라 범위 밖으로 남는 것이 타당함 |

새 질문 없음. R2-Q2에서 남긴 "게이트 우회 `input_from`" 틈은 번들 프리셋에는 없고 사용자 프리셋에만 해당한다는 것으로 닫혔으며, 그 밖에 범위 안에서 반쯤 추적된 의문은 남지 않았다.

---

## 최종 정리 (질문자)

- 총 라운드: 3 / 총 질문: 15 / 해소 11 · 없음 확정 4 · 정적 확인 불가 0 (남음 0)
- 핵심 확정 사실:
  1. **펀딩비는 코인 무기한 loader 한 곳에서만 채워진다.** `ccxt_loader.py:343-364`(`_fetch_perpetual`, Binance USD-M `-PERP`)가 `funding_rate` 컬럼을 넣고, `get_market_data`는 컬럼을 거르지 않으며(`market_data.py:415-421`), 백테스트 엔진도 이 컬럼으로 정산한다(`_market_hooks.py:456-462`). 단 `source="ccxt"`와 `-PERP` 코드를 직접 지정해야 하며 `auto`로는 닿지 않는다(R1-Q1).
  2. **OI·온체인 전용 도구나 loader는 없다.** 스킬 문서가 `bash`+OKX REST나 `read_url`(DeFi Llama, Glassnode 등)로 우회하도록 지시할 뿐이다(R1-Q2).
  3. **`get_market_data`는 실제 서빙 소스를 알려 준다.** `market_data.py:383-388,428-434`의 `serving_source`/`"source": used_source or src`/`fallback_used`로 pykrx가 없으면 `source: "yahoo"`, `fallback_used: true`가 된다(R1-Q4). 한국 종목에 정상 데이터를 주는 committee 도구는 `get_market_data`와 `backtest`뿐이고, `get_margin_trading`은 `005930`을 A주 코드로 오분류한다(`margin_trading_tool.py:49-72`, R1-Q3).
  4. **재무 PIT는 SEC `filed` 날짜 기준 전방 채움이다.** `fundamentals_loader.py:170-194`(`set_index("filed")` → `reindex(...).ffill()`), 미국 전용(R1-Q5).
  5. **데이터 나이(stale) 검사 코드는 없다.** `goal/store.py:639`는 `data_as_of` 존재 여부만 보고, 신선도는 시스템 프롬프트에 맡긴다(`grounding/__init__.py:12-14`, R1-Q7). KIS 일봉도 연속 조회 없이 1회 호출 후 자른다(`kis/sdk.py:445-465`, R1-Q6).
  6. **grounding 게이트의 숫자 허용 오차는 상대 0.5%다.** `policies.py:99-100,129-136`(`_TOLERANCE = 0.005`), `figures.py:25-29`(`ROUNDED_BAND`)(R1-Q10). 선언 없는 숫자도 표식이 있으면(`measured`) 증거와 맞을 때만 통과하고, 아니면 `figure_undeclared`/`numeric_claim_*`로 차단되며 2회 재작성 후 `(omitted※)`로 잘린다. 표식 없는 정수(`bare`)는 가격대에 해당하지 않으면 검사하지 않는다(`policies.py:537-601`, `release.py:30-42`, R2-Q1).
  7. **swarm 결과의 숫자는 증거가 아니다.** `run_swarm` 결과도 `ingest_tool_result`에 들어가지만 숫자 리프(토큰 수 등)만 증거가 되고 보고서 문자열 안의 숫자는 아니다(`loop.py:3347-3354`, `evidence.py:1109-1135`, R1-Q9).
  8. **swarm 상류 요약은 자르지 않고 통째로 들어가며, 상한은 60,000 토큰 추정치뿐이다.** `worker.py:1312-1322,303-312`, `:118`(`_MAX_TOKEN_ESTIMATE`)(R1-Q8). 상류가 `completed`가 아니면 `depends_on` 하류는 `blocked`되고 런은 `failed`가 된다(`runtime.py:929-958,609-621,637-638`, R2-Q2). 번들 프리셋 30개의 `input_from` 104개는 모두 `depends_on` 조상이라 이 게이트를 우회하는 연결이 없고, `presets.py:229-234` 경고는 `swarm inspect`에서만 보인다(R3-Q1).
  9. **라이브 러너는 일반 에이전트와 같은 system prompt를 쓴다.** 러너 지시문은 사용자 메시지로 들어가고(`runner.py:511-525`, `service.py:543-561`), system 메시지는 원칙 4가 든 `_SYSTEM_PROMPT`다(`context.py:385`). 두 지시의 충돌을 코드가 조정하지 않는다(R1-Q11).
  10. **메모리 recall은 토큰 겹침 점수(2:2:1)로 상위 3건을 고르고, 한글은 토큰화되지 않는다.** `persistent.py:109-122,412-433`, `context.py:392-396`(R1-Q12).

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` 1-1절 "코인 전용 / 펀딩비", `next.md` 미확인 1번 | 제공자·소비 주체 `미확인`, `추론` | `ccxt_loader.py`의 `_fetch_perpetual`(Binance USD-M `-PERP`)이 유일한 제공자. `get_market_data` 출력과 백테스트 `SignalEngine` 입력에 모두 포함됨. 단 `source="ccxt"` + `-PERP` 명시가 조건 | R1-Q1 |
| `01-data.md` 1-1절 "온체인, OI" | `미확인`, 스킬 문서 안 읽음 | 전용 도구·loader 없음(없음 확정). 스킬은 `bash`+OKX REST, `read_url`(DeFi Llama, Glassnode, Dune)로 우회 지시 | R1-Q2 |
| `01-data.md` 1-4절 마지막 행 | `추론`, "`get_margin_trading`이 에러 봉투를 반환" 등 | `.KS`에 정상 데이터를 주는 도구는 `get_market_data`·`backtest`뿐. `get_margin_trading`은 에러가 아니라 `005930`을 A주 코드로 오분류, `get_fund_flow`는 최상위 `ok: true` 안에 오류, `get_options_chain`은 외부 응답 의존 | R1-Q3 |
| `01-data.md` 2-3·2-4절 "실제 서빙 소스 기록" | run card 보정만 근거 | 메인 에이전트 `get_market_data`의 `_provenance`에도 실제 서빙 소스(`source`), `detected_source`, `fallback_used`가 들어감(`market_data.py:383-388,428-434`) | R1-Q4 |
| `01-data.md` 2-3절 "미래 데이터 차단(재무)", `next.md` 미확인 2번 | 구현 본문 안 읽음 | `filed` 날짜 기준 `reindex(...).ffill()`로 공시 당일부터 보임(`fundamentals_loader.py:170-194`), 미국 SEC 전용 | R1-Q5 |
| `next.md` 미확인 6번 (KIS 연속 조회) | 미확인 | 일봉 조회에 연속 조회 없음(없음 확정). `_get_paginated`는 잔고·체결에만 사용 | R1-Q6 |
| `02-schedule.md` "신선도 관리" 코드 수준 행 | `추론` | 없음 확정. 데이터 시각을 현재 시각과 비교하는 코드 없음, 프롬프트 원칙 2와 날짜 주입에만 의존 | R1-Q7 |
| `03-decision.md` 4-1절 "swarm 상류 요약" | 자르기 규칙 못 찾음 | 자르기·요약 없음. 워커 메시지 토큰 추정 60,000 초과 시 `token_limit` → `failed`. 그 부분 요약은 하류로 전달되지 않음(`runtime.py:530` `completed` 한정) | R1-Q8, R2-Q2 |
| `00-overview.md` 핵심 발견 3, `next.md` 미확인 3번 | swarm 워커에 grounding 미적용만 기술, 메인 전달 시 처리 미확인 | `run_swarm` 결과는 장부에 들어가지만 보고서 안 숫자는 증거가 아님. `observed`로 선언하면 `no_evidence` 거절, `cited`면 값 검사 없이 통과 | R1-Q9 |
| `03-decision.md` 4-5절 grounding 설명, `next.md` 마지막 항목 | 허용 오차 값 없음 | 상대 0.5%(`_TOLERANCE`, `ROUNDED_BAND`), 절대 하한 `1e-9`, 소수는 쓴 자릿수 절반 이내 추가 조건 | R1-Q10 |
| `03-decision.md` 4-5절 grounding 설명 | 선언 없는 숫자 처리 없음 | 표식 있는 숫자는 증거 일치 시에만 통과, 아니면 차단(`figure_undeclared`/`numeric_claim_*`) 후 최대 2회 재작성, 초과 시 `(omitted※)` 잘라 릴리스 또는 고정 폴백. 표식 없는 정수(`bare`)는 가격대 밖이면 검사 안 함. 경고만 붙는 경로 없음 | R2-Q1 |
| `03-decision.md` 4-5절 마지막 항목 (원칙 4 vs 러너) | `추론` | 러너는 같은 `_SYSTEM_PROMPT`(원칙 4 포함)를 쓰고 "Trade freely" 지시는 사용자 메시지로 들어감. 코드상 조정 없음(확정) | R1-Q11 |
| `03-decision.md` 4-1·4-7절, `01-data.md` 1-1절, `next.md` 미확인 8번 | "상위 3건 자동 recall(각 500자)"만 기술 | 토큰 겹침 가중(제목·설명 2, 키워드 2, 본문 1), `score > 0`, 동점 시 최신순, 임베딩 없음. 한글은 토큰화되지 않아 한국어만 있는 질의는 recall 0건 | R1-Q12 |
| `03-decision.md` 4-1·4-5절 swarm 실패 처리 | 없음 | 상류가 `completed`가 아니면 `depends_on` 하류는 `blocked`(실행 안 함), 런은 끝까지 돈 뒤 `RunStatus.failed`, 마지막 레이어 요약이 없으면 `final_report` 빈 문자열(`runtime.py:929-958,609-621,637-651`) | R2-Q2 |
| `03-decision.md` 4-1·4-5절 swarm 실패 처리 (위 항목 보충) | 없음 | 번들 프리셋 30개의 `input_from` 104개는 모두 `depends_on` 조상이라 게이트 우회 없음. `presets.py`의 "not upstream" 경고는 `swarm inspect`에만 표시되고 실행을 막지 않으므로 사용자 프리셋은 같은 보호가 없음 | R3-Q1 |
| (qa.md 내부) R1-Q9 답변의 `policies.py:1725-1727` | 라인 표기 | 현재 파일 기준 `:1719-1731`(`"no_evidence"`는 `:1726`) | R2-Q1 |
