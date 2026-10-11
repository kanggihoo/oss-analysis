# TradingAgents — 질문·답변 검증 기록

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 1
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | `get_verified_market_snapshot`이 벤더 라우터를 거치는가 | Q1, Q2 | 해소 | R1 |
| R1-Q2 | 기술지표 파라미터(RSI·볼린저·ATR·MACD)를 레포가 지정하는가 | Q1 | 없음 확정 | R1 |
| R1-Q3 | 새 벤더 함수가 지켜야 할 호출 계약(인자·반환·예외) | Q2 | 해소 | R1 |
| R1-Q4 | Alpha Vantage 벤더의 look-ahead 차단과 캐시 | Q2 | 해소 | R1 |
| R1-Q5 | 도구 함수 예외가 ToolNode에서 런을 끝내는가 | Q2, Q4-6 | 정적 확인 불가 | R1 |
| R1-Q6 | Sentiment 사전 수집에서 `get_news` 예외가 새어 나가는 경로 | Q2, Q4-6 | 해소 | R1 |
| R1-Q7 | OHLCV 10일 규칙 외 stale 감지가 있는가 | Q3 | 해소 | R1 |
| R1-Q8 | 정산 진입가가 분석일 종가인가, 그 다음 종가인가 | Q4-7 | 해소 | R1 |
| R1-Q9 | 분석가가 도구를 한 번도 안 부르고 끝날 수 있는가(최소 호출 수) | Q4-2, Q4-8 | 해소 | R1 |
| R1-Q10 | 자유 텍스트 등급 파싱이 `REVIEW`를 반환하는 정확한 분기 | Q4-6 | 해소 | R1 |
| R1-Q11 | 과거 날짜 런의 Memory Log 정산이 `trade_date` 이후 가격을 쓰는가 | Q4-7, Q2 | 해소 | R1 |
| R1-Q12 | 외부 텍스트 프롬프트 인젝션 방어 장치 부재 확정 | Q4-1, Q5 | 없음 확정 | R1 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. `get_verified_market_snapshot`은 벤더 라우터를 거치는가
- GUIDE 항목: Q1, Q2
- 왜 묻는가: `01-data.md` Q1-0은 "도구 12개는 … 모두 `route_to_vendor()`를 거친다"고 쓰지만, `router.py:97-149`의 `VENDOR_METHODS`에는 11개 메서드만 있고 `get_verified_market_snapshot`이 없다. 또 `tools.py:15`는 `vendors.yahoo.snapshot.build_verified_market_snapshot`을 직접 import한다. 이 도구가 Yahoo에 고정돼 있다면 `05-boundary-and-fit.md` 의견 3의 "키움 벤더를 라우터에 추가하면 된다"는 설명도 불완전하다.
- 질문: `get_verified_market_snapshot` 도구는 어떤 경로로 데이터를 가져오며, `data_vendors`/`tool_vendors` 설정으로 벤더를 바꿀 수 있는가?
- 답변 완료 조건: `tools.py`의 해당 도구 본문 `파일:라인`과 원문, 그 함수가 부르는 OHLCV 로더(`load_ohlcv` 등)의 위치, 그리고 설정으로 벤더 교체가 가능한지 여부(불가능하면 Yahoo에 고정된 지점의 `파일:라인`). 보고서 정정 필요 여부 명시.

#### R1-Q2. 기술지표 파라미터를 레포가 지정하는가
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` Q1-1 "지표 파라미터(RSI 14, 볼린저 20일 2σ, ATR 14, MACD 12/26/9)" 행이 `추론`이고, `next.md` 미확인 체크리스트에도 있다. 레포가 파라미터를 넘기지 않는다는 근거가 `market.py:223` 한 줄뿐이다.
- 질문: 레포 코드 어디에서든 stockstats의 윈도·파라미터(예: `StockDataFrame` 클래스 속성, `rsi_14` 같은 접미사 이름, 설정 값)를 지정하거나 덮어쓰는 곳이 있는가? 없다면 stockstats 버전은 어디에 어떻게 고정돼 있는가?
- 답변 완료 조건: (a) 지정하는 곳이 있으면 `파일:라인`과 원문, (b) 없으면 `stockstats|StockDataFrame|_14|window` 등 grep 패턴과 조사 디렉터리를 적은 "없음 확정" + `pyproject.toml`의 stockstats 버전 제약 원문. 라이브러리 기본값 자체는 설치 금지로 열람 불가이면 "정적 확인 불가"로 그 이유를 적는다.

#### R1-Q3. 새 벤더 함수가 지켜야 할 호출 계약
- GUIDE 항목: Q2 (GUIDE 5절: 벤더 라우터에 한국 벤더를 끼울 위치)
- 왜 묻는가: `01-data.md` Q2-1의 "한국 벤더 삽입 위치" 행이 `추론`이다. 위치만 있고, 벤더 함수가 받는 인자 순서·반환 형식·실패 시 던져야 할 예외(무데이터 vs 장애)가 정리되지 않았다.
- 질문: `route_to_vendor`가 벤더 함수를 호출할 때 인자를 어떻게 전달하고, 반환값을 어떻게 처리하며, 벤더가 어떤 예외를 던져야 폴백/센티널 분기가 의도대로 동작하는가?
- 답변 완료 조건: `router.py`의 호출부 `파일:라인`과 원문(인자 전달, 반환값 사용), 예외 타입별 분기 원문, 그리고 기존 벤더 1개(예: `get_YFin_data_online`)의 시그니처와 반환형을 근거로 든 계약 정리.

#### R1-Q4. Alpha Vantage 벤더의 look-ahead 차단과 캐시
- GUIDE 항목: Q2
- 왜 묻는가: `01-data.md` Q2-4 "Alpha Vantage 캐시 여부: 미확인", `next.md` 미확인 체크리스트 첫 항목("look-ahead 필터 구현, CHANGELOG는 있다고 함"). 옵트인 벤더라도 선택 시 point-in-time 보장이 Yahoo 경로와 같은지 알아야 한다.
- 질문: `dataflows/vendors/alpha_vantage/*.py`의 각 함수는 `trade_date`(또는 `as_of`) 이후 데이터를 잘라내는가, 그리고 캐시를 쓰는가?
- 답변 완료 조건: 파일별(OHLCV·지표·펀더멘털·뉴스·내부자) 날짜 필터 코드의 `파일:라인`과 원문, 필터가 없는 함수는 그 함수와 조사한 grep 패턴, 캐시 코드 유무(있으면 위치·키·만료).

#### R1-Q5. 도구 함수 예외가 ToolNode에서 런을 끝내는가
- GUIDE 항목: Q2, Q4-6
- 왜 묻는가: `01-data.md` Q2-6 "도구 예외" 행이 `미확인`이다(레포 전제 `tools.py:88` 주석만 근거). `graph/setup.py:85`는 `ToolNode(list(spec.tools))`로 인자 없이 만든다.
- 질문: 도구 함수 안에서 예외가 나면 분석가 서브그래프와 전체 런은 어떻게 되는가?
- 답변 완료 조건: `ToolNode` 생성부 원문과 `handle_tool_errors` 등 관련 인자 사용 여부(레포 전체 grep), 도구 쪽에서 예외를 잡아 문자열로 바꾸는 곳(`tools.py` 내 try/except) 목록. LangGraph 기본 동작이 라이브러리 버전에 달려 정적으로 정할 수 없으면 `pyproject.toml`의 langgraph 버전 제약 원문과 함께 "정적 확인 불가"로 경우의 수를 적는다.

#### R1-Q6. Sentiment 사전 수집에서 `get_news` 예외가 새어 나가는 경로
- GUIDE 항목: Q2, Q4-6
- 왜 묻는가: `01-data.md` Q2-6 마지막 행과 `00-overview.md` 6절이 "기본 설정에서 실제 발생 가능성은 낮다(추론)"로 끝난다. `yf_retry`가 모든 예외를 `VendorUnavailableError`로 바꾼다는 근거(`common.py:73-76`)가 `get_news` 경로의 모든 호출(`Ticker.get_news`와 폴백 `yf.Search`, 그 뒤 가공 코드)을 덮는지는 확인되지 않았다.
- 질문: 기본 설정(`news_data=yfinance`)에서 Sentiment Analyst의 `get_news.func(...)` 호출이 예외를 밖으로 던질 수 있는 코드 경로가 존재하는가?
- 답변 완료 조건: `yahoo/news.py`의 `get_news_yfinance` 안에서 `yf_retry` 바깥에 있는 코드(가공·날짜 필터 등) 목록과 `파일:라인`, 각 구간이 던질 수 있는 예외, 그 예외가 `router.py`에서 `raise`되는지 센티널로 바뀌는지의 분기 원문. "가능성 낮다"가 아니라 경로 존재 여부로 결론.

#### R1-Q7. OHLCV 10일 규칙 외 stale 감지가 있는가
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` Q3-4와 `00-overview.md` 5절이 "stale은 OHLCV 10일 규칙만"이라고 하지만, SEC·FRED·뉴스·Polymarket·스냅샷 경로를 어떤 패턴으로 찾아봤는지 조사 범위가 없다.
- 질문: OHLCV `ohlcv.py:18,109-143`의 10일 규칙 외에, 데이터가 오래됐음을 감지해 예외·경고·문구로 처리하는 코드가 다른 데이터 경로에 있는가?
- 답변 완료 조건: 있으면 각 `파일:라인`과 원문, 임계값. 없으면 `stale|STALE|max_age|too old|days old|freshness|latest.*before` 등 grep 패턴과 `dataflows/` 전체 조사 범위를 적은 "없음 확정".

#### R1-Q8. 정산 진입가는 분석일 종가인가, 그 다음 종가인가
- GUIDE 항목: Q4-7
- 왜 묻는가: 보고서끼리 모순된다. `02-schedule.md` Q3-2는 "정산 시 진입가는 분석일 종가"라 쓰고, `03-decision.md` 4-7 "기간" 행은 "진입 = 분석일 이후 첫 종가, 청산 = 5번째 이후 종가"라 쓴다. `settlement.py:73,83`은 `get_closes(ticker, trade_date, end_str)`의 첫 행을 진입으로 쓰므로, `get_closes`가 시작일을 포함하는지에 따라 결론이 갈린다.
- 질문: 정산의 진입 종가는 `trade_date` 당일 종가(당일이 거래일일 때)인가, `trade_date` 다음 거래일 종가인가? 청산은 진입 후 몇 번째 세션 종가인가?
- 답변 완료 조건: `yahoo/market.py`의 `get_closes` 본문 `파일:라인`과 시작일 포함/제외를 정하는 원문(비교 연산자 또는 yfinance 호출 인자), `settlement.py`의 `stock.index[0]`/`stock.index[holding_days]` 원문. 두 보고서 중 어느 쪽을 정정해야 하는지 명시.

#### R1-Q9. 분석가가 도구 없이 끝날 수 있는가 (최소 LLM 호출 수)
- GUIDE 항목: Q4-2, Q4-8
- 왜 묻는가: `03-decision.md` 4-8 표는 Market/News/Fundamentals의 호출 수를 "최소 2"로 쓰고 합계 "최소 약 15회"를 낸다. 그런데 `setup.py`의 서브그래프는 `_tools_or_done`이 도구 호출이 없으면 바로 `END`로 가는 구조로 보인다. 프롬프트가 스냅샷 호출을 "지시"하는 것(`market_analyst.py:48`)과 코드가 강제하는 것은 다르다.
- 질문: 도구 분석가의 첫 LLM 응답에 도구 호출이 없으면 그 분석가는 1회 호출로 끝나는가? 도구 호출을 최소 1회 강제하는 코드(`tool_choice` 등)가 있는가?
- 답변 완료 조건: `_tools_or_done` 원문과 `파일:라인`, 분석가 LLM에 도구를 바인딩하는 코드(`bind_tools` 호출과 인자) 원문, `tool_choice|required|force` grep 결과. 이를 근거로 분석가별 최소 호출 수와 4-8 합계의 정정 필요 여부.

#### R1-Q10. 자유 텍스트 등급 파싱이 `REVIEW`를 반환하는 정확한 분기
- GUIDE 항목: Q4-6 (GUIDE 5절: `REVIEW` 반환 조건)
- 왜 묻는가: `03-decision.md` 4-6의 "`REVIEW`가 되는 조건" 행은 네 조건을 나열하지만 마지막 문장 "라벨 첫 줄(헤딩 제외)이 `- ` 없는 본인 등급줄이면 그것을 채택"은 처음 읽는 사람이 이해하기 어렵고, 조건들의 평가 순서가 없다.
- 질문: `rating.py`에서 PM 자유 텍스트를 등급으로 바꾸는 함수는 어떤 순서로 무엇을 검사하고, 각 단계에서 어떤 값(등급 또는 `REVIEW`)을 반환하는가?
- 답변 완료 조건: 해당 함수의 `파일:라인`, 사용하는 정규식 원문, 분기를 위에서부터 순서대로 "조건 → 반환값"으로 정리한 표, 그리고 각 분기를 예시 입력 문자열 1개로 설명(테스트 `tests/test_rating_integrity.py`에 예시가 있으면 그 `파일:라인`).

#### R1-Q11. 과거 날짜 런의 Memory Log 정산이 `trade_date` 이후 가격을 쓰는가
- GUIDE 항목: Q4-7, Q2 (look-ahead)
- 왜 묻는가: `01-data.md` Q2-5와 `03-decision.md` 4-7은 "과거 날짜 런은 `resolved <= trade_date`인 교훈만 주입"을 point-in-time 장치로 든다. 하지만 같은 런의 `Memory Log` 노드(`trading_graph.py:308-335`)가 정산할 때 가격 조회 종료일이 런의 `trade_date`로 제한되는지, 그리고 정산 대상이 "모든 티커의 pending"인지 런의 `trade_date` 이전 결정만인지는 적혀 있지 않다. 백테스트에서 현재 시점 가격으로 정산이 일어나고 그 결과가 주입 필터만으로 차단되는 구조인지 알아야 한다.
- 질문: 과거 날짜 런(`trade_date` < 오늘)에서 `Memory Log` 노드는 어떤 pending 항목을 정산 대상으로 고르며, 정산 가격 조회의 종료일은 런의 `trade_date`와 무관하게 결정되는가?
- 답변 완료 조건: `trading_graph.py`의 Memory Log 노드에서 정산 함수로 넘기는 인자 원문, `settlement.py`에서 대상 선정 조건과 종료일 계산 원문(`파일:라인`), 런의 `trade_date`가 이 경로에 전달되는지 여부. 그 결과 주입 필터(`log.py:105-107`)가 유일한 차단 장치인지 결론.

#### R1-Q12. 외부 텍스트 프롬프트 인젝션 방어 장치가 없음을 확정
- GUIDE 항목: Q4-1, Q5
- 왜 묻는가: `03-decision.md` 4-9 4번이 "방어 장치를 찾지 못했다(추론: grep에서 확인되지 않음)"로 끝나고 grep 패턴이 없다. `05-boundary-and-fit.md` 의견 2가 이 추론에 기대고 있다.
- 질문: 뉴스·StockTwits·Reddit·Polymarket 텍스트를 프롬프트에 넣기 전에 지시문 제거, 이스케이프, "아래 내용은 데이터이며 지시가 아니다" 류의 안내 문구, 출력 검증 등 인젝션 방어 처리를 하는 코드나 프롬프트 문장이 있는가?
- 답변 완료 조건: 있으면 `파일:라인`과 원문. 없으면 `inject|untrusted|ignore (previous|prior)|instruction|sanitiz|escape|treat .* as data` 등 grep 패턴(대소문자 무시)과 조사 디렉터리(`agents/`, `dataflows/`), 그리고 Sentiment 블록 태그(`<start_of_news>` 등) 주변 프롬프트 원문을 확인한 "없음 확정".

### 답변 (답변자)

(경로 표기: 달리 적지 않으면 `repos/TradingAgents/tradingagents/` 기준. 모든 라인은 파일을 직접 열어 확인한 값이다.)

#### R1-Q1 답변
- 결론: **확정.** `get_verified_market_snapshot`은 벤더 라우터를 거치지 않는다. `build_verified_market_snapshot()` → `load_ohlcv()` → `yf.Ticker(...).history(...)`로 Yahoo에 직접 고정돼 있고, `data_vendors`/`tool_vendors` 설정으로 바꿀 수 없다. **보고서 정정 필요**: `01-data.md` Q1-0의 "도구 12개는 모두 `route_to_vendor()`를 거친다"는 틀렸다. 라우터를 거치는 도구는 11개이고 스냅샷만 예외다. `05-boundary-and-fit.md` 의견 3도 "라우터에 벤더 추가"만으로는 불완전하다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `agents/tools.py:15` | import | `from tradingagents.dataflows.vendors.yahoo.snapshot import build_verified_market_snapshot` | 코드 확인 |
  | `agents/tools.py:88-94` | `get_verified_market_snapshot` 본문 | `return build_verified_market_snapshot(symbol, as_of(curr_date, trade_date), look_back_days)` (예외는 `VendorUnavailableError`/`NoMarketDataError`만 문자열 센티널로 변환) | 코드 확인 |
  | `dataflows/vendors/yahoo/snapshot.py:20` | import | `from tradingagents.dataflows.vendors.yahoo.ohlcv import load_ohlcv` | 코드 확인 |
  | `dataflows/vendors/yahoo/snapshot.py:39` | `_verified_rows` | `data = load_ohlcv(symbol, as_of_date, fill_gaps=False)` | 코드 확인 |
  | `dataflows/vendors/yahoo/ohlcv.py:212-217` | `load_ohlcv` | `downloaded = yf_retry(lambda: yf.Ticker(canonical).history(start=start_str, end=end_str, auto_adjust=True, actions=False,))` | 코드 확인 |
  | `dataflows/vendors/yahoo/ohlcv.py:178,190-194` | `load_ohlcv` | `config = get_config()` 는 캐시 경로 `config["data_cache_dir"]`에만 쓰이고 `get_vendor`/`data_vendors`는 읽지 않는다 | 코드 확인 |
  | `dataflows/router.py:45-87` | `TOOLS_CATEGORIES` | 카테고리 6개의 `tools` 목록에 `get_verified_market_snapshot` 없음 | 코드 확인 |
  | `dataflows/router.py:97-149` | `VENDOR_METHODS` | 키 11개: `get_stock_data, get_indicators, get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_news, get_global_news, get_insider_transactions, get_macro_indicators, get_prediction_markets` | 코드 확인 |
  | `agents/tools.py` (`@tool` 선언 18,41,72,97,114,133,152,171,194,218,232,267) | 도구 12개 | 12개 중 `get_verified_market_snapshot`(72)만 `route_to_vendor`를 부르지 않는다 | 코드 확인 |

- 동작 설명: Market Analyst가 스냅샷 도구를 부르면 `tools.py:90`이 `as_of(curr_date, trade_date)`로 날짜를 런의 `trade_date` 이하로 자른 뒤 `build_verified_market_snapshot`을 직접 호출한다. 이 함수는 `load_ohlcv`로 5년치 일봉을 받고(`ohlcv.py:183-217`, 심볼별 CSV 캐시) `stockstats.wrap`으로 지표를 계산한다. 설정의 벤더 값은 이 경로 어디에서도 읽지 않는다. 같은 `load_ohlcv`를 `get_indicators`의 yfinance 구현(`market.py:219,284`)도 쓰지만 그쪽은 라우터 경유다. 결과적으로 `technical_indicators`를 `alpha_vantage`로 바꿔도 `get_indicators`만 바뀌고 스냅샷은 계속 Yahoo OHLCV에서 계산한다. 정산(`memory/settlement.py:9,73`)도 라우터를 거치지 않고 `yahoo.market.get_closes`를 직접 부른다. 한국 데이터 소스를 붙이려면 라우터 등록 외에 스냅샷의 `load_ohlcv`와 정산의 `get_closes` 두 곳도 바꿔야 한다.
- 조사 범위: `agents/tools.py` 전체, `dataflows/router.py` 전체, `dataflows/vendors/yahoo/{snapshot,ohlcv,market}.py`, `memory/settlement.py`. grep `get_verified_market_snapshot|build_verified_market_snapshot|load_ohlcv|get_closes`로 호출처 확인.

#### R1-Q2 답변
- 결론: **없음 확정.** 레포 코드에는 stockstats의 윈도·파라미터를 지정하거나 덮어쓰는 곳이 없다. Yahoo 경로는 `rsi`, `boll`, `atr`, `macd` 같은 접미사 없는 이름을 `df[indicator]`로 넘길 뿐이라 실제 윈도 숫자는 stockstats 라이브러리 기본값이 정한다. 그 숫자(RSI 14, 볼린저 20일 2σ, ATR 14, MACD 12/26/9) 자체는 설치 금지로 라이브러리 소스를 볼 수 없어 **정적 확인 불가**(분기점: `dataflows/vendors/yahoo/market.py:223`, `snapshot.py:83`). 반면 Alpha Vantage 경로는 레포가 숫자를 직접 지정한다(아래 표). **보고서 보강 필요**: `01-data.md` Q1-1의 "RSI 14, 볼린저 20일 2σ, ATR 14, MACD 12/26/9"는 Yahoo 경로에서는 코드 확인이 아니라 라이브러리 기본값 전제이고, 코드로 확인되는 것은 Alpha Vantage 경로의 값이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `dataflows/vendors/yahoo/market.py:217-223` | `_get_stock_stats_bulk` | `df = wrap(data)` … `df[indicator]  # This triggers stockstats to calculate the indicator` (파라미터 인자 없음) | 코드 확인 |
  | `dataflows/vendors/yahoo/market.py:285-289` | `get_stock_stats` | `df = wrap(data)` … `df[indicator]  # trigger stockstats to calculate the indicator` | 코드 확인 |
  | `dataflows/vendors/yahoo/snapshot.py:23-27,77,83` | `DEFAULT_SNAPSHOT_INDICATORS` | `"close_10_ema", "close_50_sma", "close_200_sma", "rsi", "boll", "boll_ub", "boll_lb", "macd", "macds", "macdh", "atr"` / `stock_df = wrap(df.copy())` / `stock_df[name]  # triggers stockstats calculation` | 코드 확인 |
  | `dataflows/vendors/yahoo/market.py:77-148` | `best_ind_params` | 지표 이름과 설명 문자열만 있다(예: `"boll": "Bollinger Middle: A 20 SMA serving as the basis ..."`). 계산 파라미터가 아니라 LLM에 보여줄 텍스트다 | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/indicator.py:15,121,137` | `get_indicator` | `time_period: int = 14` → RSI `"time_period": str(time_period)`, ATR `"time_period": str(time_period)` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/indicator.py:90,98,106,129` | `get_indicator` | SMA `"time_period": "50"`/`"200"`, EMA `"time_period": "10"`, BBANDS `"time_period": "20"`. MACD 호출(110-115행)에는 기간 인자가 없다 | 코드 확인 |
  | `pyproject.toml:26` | 의존성 | `"stockstats>=0.6.5",` (하한만 있고 상한·락 파일 없음. `uv.lock` 없음, `requirements.txt`는 `.`만 있음) | 코드 확인 |

- 동작 설명: 지표 요청이 오면 yfinance 벤더(`get_stock_stats_indicators_window`)가 `_get_stock_stats_bulk`에서 OHLCV를 `wrap`으로 감싼 뒤 `df["rsi"]`처럼 이름만 접근한다. stockstats는 접근한 컬럼이 없으면 이름을 해석해 계산하는데, 접미사 없는 이름의 기본 윈도는 라이브러리 내부 값이다. 레포는 `StockDataFrame` 클래스 속성이나 `rsi_14` 같은 접미사 이름을 한 번도 쓰지 않는다(`close_10_ema`, `close_50_sma`, `close_200_sma`는 이름에 윈도가 들어 있어 레포가 지정한 것이다). 설치되는 stockstats 버전은 `>=0.6.5` 중 설치 시점의 최신이 되므로 기본값이 바뀌어도 레포는 감지하지 못한다.
- 조사 범위: `tradingagents/`, `cli/` 전체 grep `stockstats|StockDataFrame|_window|\.set\(|BOLL|rsi_|_14\b|\bwrap\(`. 결과는 `yahoo/market.py:8,186,191,217,220,223,238,285,289`, `yahoo/snapshot.py:16,74,77,83`, `yahoo/ohlcv.py:69`(독스트링)뿐이고 모두 `wrap()` + 이름 접근이다. 의존성 선언은 `pyproject.toml`, `requirements.txt`, `CHANGELOG.md`(stockstats 언급은 116행 모듈 이름 변경 설명뿐)에서 확인했다.

#### R1-Q3 답변
- 결론: **확정.** 호출 계약은 다음과 같다. (1) `route_to_vendor(method, *args, **kwargs)`는 도구가 넘긴 인자를 그대로(`*args, **kwargs`) 벤더 함수에 위치 인자로 전달한다. (2) 반환값은 검사·변환 없이 그대로 돌려준다(성공 판정은 "예외 없이 반환"뿐). (3) 실패는 반드시 예외 타입으로 알려야 하며 타입마다 분기가 다르다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `dataflows/router.py:200-209` | `route_to_vendor` | `def route_to_vendor(method: str, *args, **kwargs):` / `if method not in VENDOR_METHODS: raise ValueError(...)` | 코드 확인 |
  | `dataflows/router.py:216-225` | 벤더 체인 | `explicit = [v for v in primary_vendors if v and v != "default"]` → 설정된 이름 중 `VENDOR_METHODS[method]`에 있는 것만 체인. 하나도 없으면 `ValueError`, `default`면 등록된 모든 벤더 | 코드 확인 |
  | `dataflows/router.py:232-236` | 호출부 | `impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl` / `return impl_func(*args, **kwargs)` | 코드 확인 |
  | `dataflows/router.py:237-242` | `VendorUnavailableError` | `last_unavailable = e` 저장 후 `continue`(다음 벤더) | 코드 확인 |
  | `dataflows/router.py:243-247` | `VendorNotConfiguredError` | `first_error`에 보관 후 `continue` | 코드 확인 |
  | `dataflows/router.py:248-250` | `NoMarketDataError` | `last_no_data = e` 후 `continue` | 코드 확인 |
  | `dataflows/router.py:251-259` | 그 밖의 `Exception` | 경고 로그, `first_error`/`failed`에 보관 후 `continue` | 코드 확인 |
  | `dataflows/router.py:265-295` | 체인 소진 후 | `last_unavailable` 있으면 `vendor_unavailable(...)` 문자열 반환(266). `failed`와 `last_no_data`가 같이 있으면 `vendor_unavailable`(267-268). `last_no_data`만 있으면 `no_data_available`(274-282). `first_error`만 있으면 선택 카테고리(`macro_data`, `prediction_markets`, 94행)는 `DATA_UNAVAILABLE` 문자열, 그 외는 `raise first_error`(288-295) | 코드 확인 |
  | `dataflows/errors.py:21-58` | 예외 계층 | `VendorError` 아래 `NoMarketDataError(symbol, canonical=None, detail="")`, `VendorUnavailableError`, `VendorNotConfiguredError(VendorError, ValueError)` | 코드 확인 |
  | `agents/tools.py:38,66,111,130,149,168,191,215,229,264,291` | 인자 전달 | 아래 "동작 설명"의 시그니처 표 근거 | 코드 확인 |
  | `dataflows/vendors/yahoo/market.py:18-22,39-40,65` | `get_YFin_data_online` | `(symbol, start_date, end_date)` → 빈 결과면 `raise_for_empty(...)`, 정상이면 `header + csv_string`(문자열) 반환 | 코드 확인 |

- 동작 설명: 새 벤더 함수는 `VENDOR_METHODS[method][벤더이름]`에 등록되고(또 `data_vendors`/`tool_vendors` 설정에 그 이름이 들어가야 체인에 든다), 도구가 넘기는 인자 순서 그대로 받아야 한다.

  | 메서드 | 벤더 함수가 받는 위치 인자 (호출부) |
  |---|---|
  | `get_stock_data` | `(symbol, start_date, end_date)` (`tools.py:38`, 날짜는 이미 `as_of_window`로 `trade_date` 이하) |
  | `get_indicators` | `(symbol, indicator, curr_date, look_back_days)` (`tools.py:66`, 지표 이름 하나씩) |
  | `get_fundamentals` | `(ticker, as_of_date)` (`tools.py:111`) |
  | `get_balance_sheet`, `get_cashflow`, `get_income_statement` | `(ticker, freq, as_of_date)` (`tools.py:130,149,168`) |
  | `get_news` | `(ticker, start_date, end_date)` (`tools.py:191`) |
  | `get_global_news` | `(as_of_date, look_back_days, limit)` (`tools.py:215`) |
  | `get_insider_transactions` | `(ticker, trade_date or None)` (`tools.py:229`) |
  | `get_macro_indicators` | `(indicator, as_of_date, look_back_days)` (`tools.py:264`) |
  | `get_prediction_markets` | `(topic, limit, trade_date or None)` (`tools.py:291`) |

  반환형은 모두 `str`(도구 시그니처 `-> str`)이어야 LLM에 그대로 전달된다(라우터는 타입 검사를 하지 않는다. Alpha Vantage 일부 함수의 주석은 `dict | str`이지만 실제로는 `_make_api_request`가 `response_text` 문자열을 돌려준다, `alpha_vantage/common.py:106,134`). 예외 계약은 다음과 같다.
  - 데이터가 정말 없음(미지원 심볼, 빈 결과, stale)은 `NoMarketDataError(symbol, canonical, detail)`을 던진다. 다음 벤더로 넘어가고, 전원이 이러면 `NO_DATA_AVAILABLE` 센티널이 된다.
  - 장애, 한도 초과, 네트워크 실패는 `VendorUnavailableError`를 던진다. 다음 벤더로 넘어가고, 전원이 이러면 `DATA_UNAVAILABLE` 센티널이다(런은 계속).
  - 키 누락은 `VendorNotConfiguredError`를 던진다. 다음 벤더로 넘어가지만 다른 벤더가 모두 실패하면 이 예외가 그대로 다시 던져진다(288-295).
  - 이 세 타입이 아닌 예외(예: `requests` 예외, `AttributeError`)는 "깨진 벤더"로 취급돼 다음 벤더로 넘어가지만, 마지막까지 성공하지 못하면(`last_no_data` 없이) `first_error`가 다시 던져져 도구까지 올라온다(295행). 선택 카테고리(`macro_data`, `prediction_markets`)만 센티널로 흡수된다.
  - `get_indicators` 도구만 `ValueError`를 잡아 문자열로 바꾼다(`tools.py:67-68`). 지원하지 않는 지표 이름은 yfinance 벤더가 `ValueError`를 던지고(`market.py:150-153`) 이것이 `first_error`로 다시 던져져 이 `except`에서 잡힌다.
  - 벤더 함수 안에서 `yf_retry`처럼 모든 예외를 `VendorUnavailableError`로 바꾸는 패턴(`yahoo/common.py:73-76`)을 따르면 센티널 경로가 의도대로 동작한다.
- 조사 범위: `dataflows/router.py` 전체, `dataflows/errors.py` 전체, `agents/tools.py` 전체(호출부 11곳), `yahoo/market.py`, `yahoo/common.py`, `alpha_vantage/common.py`.

#### R1-Q4 답변
- 결론: **확정.** Alpha Vantage 벤더 함수 9개 중 날짜를 클라이언트에서 직접 자르는 것은 OHLCV(`get_stock`)와 지표(`get_indicator`) 2개다. 뉴스 2개는 API의 `time_from`/`time_to` 파라미터에만 맡기고 응답을 다시 거르지 않는다. 펀더멘털 4개와 내부자 거래는 날짜로 자르지 않고, 과거 날짜 런이면 데이터를 반환하지 않고 "withheld" 안내문을 돌려준다. 캐시는 없다. **보고서 보강 필요**: `next.md`의 "look-ahead 필터 구현" 미확인 항목과 `01-data.md` Q2-4의 "캐시 여부 미확인"은 위와 같이 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `dataflows/vendors/alpha_vantage/stock.py:40-42` | `get_stock` | `response = _make_api_request("TIME_SERIES_DAILY_ADJUSTED", params)` / `return _filter_csv_by_date_range(response, start_date, end_date)` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/common.py:152-164` | `_filter_csv_by_date_range` | `# ... this trim is the only thing keeping bars after end_date out of a historical run.` / `filtered_df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/indicator.py:75-76,187-189` | `get_indicator` | `before = as_of_dt - relativedelta(days=look_back_days)` / `if before <= date_dt <= as_of_dt:` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/news.py:27-31` | `get_news` | `"time_from": format_datetime_for_api(start_date), "time_to": format_datetime_for_api(end_date, end_of_day=True),` 후 `return _make_api_request("NEWS_SENTIMENT", params)` (응답 필터 없음) | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/news.py:63-70` | `get_global_news` | 같은 방식으로 `time_to`를 `as_of_date` 하루 끝(`T2359`)으로 지정, 응답 필터 없음 | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/common.py:38-52` | `format_datetime_for_api` | `return dt.strftime("%Y%m%dT2359" if end_of_day else "%Y%m%dT0000")` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/fundamentals.py:21-23,34-36,42-44,50-52` | 펀더멘털 4종 | `withheld = withhold_live_profile(as_of_date, ticker)` / `withhold_undated_statements(...)` → `if withheld: return withheld` | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/news.py:86-88` | `get_insider_transactions` | `withheld = withhold_undisclosed_trades(as_of_date, symbol)` → `if withheld: return withheld` | 코드 확인 |
  | `dataflows/date_window.py:39-41,108-131,134-176` | `is_historical`, `withhold_*` | `return bool(run_date) and str(run_date) < get_current_date()`. 과거 날짜면 안내문, 오늘이거나 날짜가 없으면 `None`(= 현재 값을 그대로 서빙) | 코드 확인 |
  | `dataflows/vendors/alpha_vantage/stock.py:31-32` | `get_stock` | `outputsize = "compact" if days_from_today_to_start < 100 else "full"` (compact는 최근 100개 포인트) | 코드 확인 |

- 동작 설명: 도구가 `as_of_window`/`as_of`로 날짜를 `trade_date` 이하로 자른 뒤(`tools.py:35,61,111` 등) 벤더에 넘기므로 벤더 함수의 필터는 "그 끝 날짜 이후 제거"로 동작한다. 벤더 함수 자체는 `trade_date`를 모르고 받은 끝 날짜만 신뢰한다. 직접 호출하면 미래 날짜를 줄 수 있다. 뉴스는 API 서버가 `time_to`를 지킨다는 전제이고 서버 응답 준수 여부는 외부 사항이라 코드로 확인할 수 없다. 펀더멘털은 `is_historical(as_of_date)`일 때만 withheld이고, 오늘 날짜 런(또는 `as_of_date`가 `None`)이면 라이브 값이 그대로 나간다. 캐시는 없다. `get_scrubbed`(`net.py:6-24`)는 `requests.get` 한 번이고 저장 코드가 없다.
- 조사 범위: `dataflows/vendors/alpha_vantage/` 전체(`__init__.py`, `common.py`, `fundamentals.py`, `indicator.py`, `news.py`, `stock.py`)를 열어 읽었다. 캐시 grep `cache|lru|memoiz|pickle|to_csv|os\.path|Path\(` (대소문자 무시)은 `common.py:166`의 `filtered_df.to_csv(index=False)`(문자열 반환, 파일 저장 아님) 한 건뿐이다. `dataflows/net.py` 전체와 `date_window.py` `withhold_*` 함수도 확인했다.

#### R1-Q5 답변
- 결론: **정적 확인 불가.** 갈리는 지점은 `graph/setup.py:85`의 `graph.add_node("tools", ToolNode(list(spec.tools)))`이다. 레포는 `handle_tool_errors` 인자를 어디에서도 넘기지 않아 도구 예외 처리는 `langgraph.prebuilt.ToolNode` 라이브러리 기본값(설치 금지로 열람 불가)이 정한다. 다만 레포 쪽에서 "도구 예외가 ToolNode까지 올라올 수 있는 경로"는 코드로 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `graph/setup.py:85` | `_analyst_graph` | `graph.add_node("tools", ToolNode(list(spec.tools)))` (인자 없음) | 코드 확인 |
  | `graph/setup.py:87-88` | 엣지 | `graph.add_conditional_edges("agent", _tools_or_done, ["tools", END])` / `graph.add_conditional_edges("tools", more_or_wrap_up, ["agent", "wrap_up"])` (tools 노드 실패 시 대체 경로 없음) | 코드 확인 |
  | `agents/tools.py:34-37,65-68,88-94,187-190` | try/except 전부 | `get_stock_data`/`get_news`: `except ValueError as e: return str(e)`, `get_indicators`: `except ValueError`, `get_verified_market_snapshot`: `except VendorUnavailableError`/`except NoMarketDataError`. 나머지 도구(`get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_global_news`, `get_insider_transactions`, `get_macro_indicators`, `get_prediction_markets`)는 `route_to_vendor` 호출을 보호하지 않는다 | 코드 확인 |
  | `agents/tools.py:88` | 주석 | `# An exception out of a tool would end the run.` (레포 저자의 전제) | 코드 확인 |
  | `dataflows/router.py:288-295` | `route_to_vendor` | `if category in OPTIONAL_CATEGORIES: ... return ("DATA_UNAVAILABLE: ...")` / `raise first_error` | 코드 확인 |
  | `graph/trading_graph.py:397` | `_run_graph` | `final_state = self.graph.invoke(graph_input, **args)` (try/except 없음) | 코드 확인 |
  | `pyproject.toml:15` | 버전 | `"langgraph>=1.2.12",` (하한만, 락 파일 없음) | 코드 확인 |
  | 레포 전체 | grep | `handle_tool_errors\|ToolException\|handle_tool_error` 일치 0건 (`ToolNode`는 `graph/setup.py:7,85`와 테스트 `tests/test_dataflows_config.py:167,182`, `tests/test_tool_date_enforcement.py:16,101`에만 등장) | 코드 확인 |

- 동작 설명: 도구 예외가 `ToolNode`에 도달하면 두 경우로 갈린다. (A) 라이브러리 기본값이 모든 도구 예외를 `ToolMessage` 오류 문자열로 바꾸는 경우: 분석가는 오류 문자열을 받고 다음 라운드로 진행하며 런은 계속된다. (B) 기본값이 인자 검증 오류 등 일부만 문자열로 바꾸고 나머지는 다시 던지는 경우: `tools` 노드 예외 → 분석가 서브그래프 → 부모 그래프 → `self.graph.invoke`(397행) 또는 `stream_run`(`trading_graph.py:422` 이하 루프)으로 전파돼 런이 중단된다. 레포의 방어 코드(`tools.py:88` 주석, `router.py`의 센티널 설계, `OPTIONAL_CATEGORIES` 주석 92-94행 "so a bad LLM-supplied indicator ... should not crash an analysis")는 모두 (B)를 전제로 작성돼 있고 (A)에 의존하는 코드는 없다. 레포 쪽에서 예외가 도구 밖으로 나오는 경로는 확정이다. 필수 카테고리(`core_stock_apis`, `technical_indicators`, `fundamental_data`, `news_data`)에서 벤더가 `VendorNotConfiguredError`나 타입 없는 예외만 던지고 다른 벤더가 성공하지 못하면 `raise first_error`(`router.py:295`)가 일어나고, `ValueError`를 잡는 도구(`get_stock_data`, `get_news`, `get_indicators`)를 제외한 도구에서는 그대로 올라온다.
- 조사 범위: `graph/setup.py` 전체, `agents/tools.py` 전체, `dataflows/router.py` 전체, `graph/trading_graph.py`의 `invoke`/`stream` 호출부(`try:` 위치 242,319,328,423), `tradingagents/`·`cli/`·`tests/` grep `handle_tool_errors|ToolException|handle_tool_error|ToolNode`. 라이브러리 소스(`langgraph/prebuilt/tool_node.py`)는 설치 금지라 읽지 않았다.

#### R1-Q6 답변
- 결론: **확정.** 기본 설정(`news_data=yfinance`)에서 Sentiment Analyst의 `get_news.func(...)`가 예외를 밖으로 던질 수 있는 코드 경로는 존재한다. `get_news_yfinance`에는 `yf_retry` 바깥에서 실행되는 가공 코드가 있고, 거기서 난 예외는 라우터에서 센티널로 바뀌지 않고 `raise first_error`로 다시 던져지며, Sentiment 노드에는 이를 잡는 코드가 없다. 따라서 `00-overview.md` 6절과 `01-data.md` Q2-6의 "실제 발생 가능성은 낮다(추론)"는 "경로는 존재하며, 발생 여부는 Yahoo 응답 형태에 달려 있다(정적 확인 불가)"로 **정정 필요**. `sentiment_analyst.py:63-65` 주석("no exceptions surface from here")도 `get_news` 호출에는 맞지 않는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `agents/analysts/sentiment_analyst.py:63-66` | `sentiment_analyst_node` | `# ... returns a string (no exceptions surface from here)` / `news_block = get_news.func(ticker, start_date, end_date)` (이 노드의 47-125행에 try/except 없음) | 코드 확인 |
  | `agents/tools.py:187-191` | `get_news` 본문 | `try: start_date, end_date = as_of_window(...)` `except ValueError as e: return str(e)` / `return route_to_vendor("get_news", ticker, start_date, end_date)` (라우터 호출은 보호 없음) | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:107` | `get_news_yfinance` | `feed = yf_retry(lambda: yf.Ticker(canonical).get_news(count=article_limit)) or []` (이 호출만 `yf_retry` 안) | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:108,117` | 가공(`yf_retry` 밖) | `articles = [_extract_article_data(a) for a in feed]` / `articles = [_extract_article_data(a) for a in found]` | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:22-25,34-35` | `_extract_article_data` | `content = article.get("content")`, `url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}`, `"publisher": (content.get("provider") or {}).get("displayName") or "Unknown"`, `"link": url_obj.get("url") or ""`. `provider`나 `url_obj`가 dict가 아니면 `AttributeError`, 원소가 dict가 아니면 `article.get`에서 `AttributeError`. 보호되는 것은 `fromisoformat`의 `ValueError, AttributeError`(28행)뿐 | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:64-72` | `_search_news` | `search = yf_retry(lambda: yf.Search(canonical, news_count=limit))` 뒤 `canonical in (t.upper() for t in a.get("relatedTickers") or [])`, `q.get("symbol")`는 `yf_retry` 밖(원소가 문자열이 아니거나 dict가 아니면 `AttributeError`) | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:119-134` | 날짜 처리 | `datetime.strptime(...)`, `in_window(...)`(`date_window.py:23-31`), `coverage_gap(...)`(`date_window.py:44-68`)도 `yf_retry` 밖. 입력 날짜는 `_seven_days_back`이 만든 정상 형식이라 이 구간의 발생 가능성은 낮다 | 코드 확인 |
  | `dataflows/vendors/yahoo/common.py:61-76` | `yf_retry` | `except Exception as exc: ... raise VendorUnavailableError(f"Yahoo Finance request failed: {type(exc).__name__}") from exc` (`yf_retry` 안의 호출만 덮는다) | 코드 확인 |
  | `dataflows/router.py:251-259` | 라우터 | `except Exception as e: logger.warning(...); first_error = e; failed = e; continue` (`VendorError` 계열이 아니라 센티널로 바뀌는 분기를 타지 않는다) | 코드 확인 |
  | `dataflows/router.py:265-268,274,288-295` | 체인 소진 후 | `last_unavailable`과 `last_no_data`가 모두 `None`이므로 266·268·274행 분기를 건너뛰고, `if first_error is not None:` → `news_data`는 `OPTIONAL_CATEGORIES`(94행)에 없으므로 `raise first_error` | 코드 확인 |

- 동작 설명: 기본 설정에서 `news_data`는 `yfinance` 단일 벤더 체인이다. `get_news_yfinance`가 `yf_retry` 밖의 `_extract_article_data`/`_search_news` 가공에서 `AttributeError` 같은 untyped 예외를 내면, 라우터가 이를 `failed`/`first_error`에 담고 체인이 끝나 `raise first_error`(295행)로 다시 던진다. `get_news.func`는 `@tool` 래퍼를 건너뛰고 원본 함수를 직접 호출하므로 `tools.py`의 `ValueError` 처리 외에는 보호가 없고, 예외는 `sentiment_analyst_node`를 빠져나가 분석가 서브그래프와 런을 중단시킨다(R1-Q5의 (B) 경우와 달리 `ToolNode`를 거치지 않으므로 라이브러리 기본값과 무관하게 확정이다). `VendorUnavailableError`(`news.py:112,116`의 두 곳 포함)는 266행에서 `DATA_UNAVAILABLE` 문자열이 되고 `NoMarketDataError`는 센티널이 되므로 새지 않는다. 그 가공 코드가 실제로 예외를 내는지는 Yahoo가 돌려주는 JSON의 모양에 달려 있어 코드만으로는 단정할 수 없다(정적 확인 불가). 비기본 설정에서는 `news_data=alpha_vantage`이면서 키가 없을 때 `VendorNotConfiguredError`가(`router.py:243-247,295`), `requests` 예외가 `alpha_vantage/common.py:95`에서 나갈 때도 같은 경로로 새 나간다.
- 조사 범위: `agents/analysts/sentiment_analyst.py` 전체, `agents/tools.py:171-191`, `dataflows/vendors/yahoo/{news,common}.py` 전체, `dataflows/router.py` 전체, `dataflows/date_window.py`, `dataflows/symbols.py`(`normalize_symbol`은 순수 문자열 처리), `dataflows/vendors/alpha_vantage/{news,common}.py`.

#### R1-Q7 답변
- 결론: **확정.** "최신 행 날짜와 기준일의 차이가 임계값을 넘으면 거부"하는 규칙은 OHLCV의 `MAX_OHLCV_STALE_DAYS = 10`뿐이고, 다른 데이터 경로에는 이런 임계값 규칙이 없다. 다만 "오래됨/못 본 구간"을 문구로 알리는 다른 장치가 4가지 있으므로 `02-schedule.md` Q3-4와 `00-overview.md` 5절의 "stale은 OHLCV 10일 규칙만"은 **보고서 정정 필요**(임계값 규칙은 맞지만 유사 장치 생략).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `dataflows/vendors/yahoo/ohlcv.py:18,109-143,255` | `_assert_ohlcv_not_stale` | `MAX_OHLCV_STALE_DAYS = 10` / `if stale_days > max_stale_days: raise NoMarketDataError(...)` / `load_ohlcv`가 255행에서 호출 | 코드 확인 |
  | `dataflows/vendors/yahoo/market.py:49` | `get_YFin_data_online` | `_assert_ohlcv_not_stale(data, end_date, symbol, canonical)` (라우터 경유 OHLCV 경로에서 같은 규칙) | 코드 확인 |
  | `dataflows/date_window.py:44-68` | `coverage_gap` | `reason = "the window extends past today"` / `reason = "it only serves recent items"` → `"<{source} unavailable for {start_date}..{end_date}: {reason}, so this is not an absence of {subject}>"`. 일수 임계값이 아니라 "응답이 창의 첫날까지 닿는가"를 본다. 호출처: `yahoo/news.py:130,198`, `stocktwits.py:112`, `reddit.py:287` | 코드 확인 |
  | `dataflows/vendors/polymarket.py:49-66` | `_is_forward_looking` | `if market.get("closed"): return False` / `endDate`가 `now`보다 과거면 제외 | 코드 확인 |
  | `dataflows/vendors/yahoo/ohlcv.py:24,146-158` | `_cache_is_fresh` | `OHLCV_CACHE_TTL_SECONDS = 900` (데이터 stale 판정이 아니라 캐시 재사용 판정) | 코드 확인 |
  | `dataflows/vendors/sec_edgar.py:41,124` | `_cached_json` | `_CACHE_TTL_SECONDS = 24 * 60 * 60` (캐시 만료이며 데이터 stale 판정 아님) | 코드 확인 |
  | `dataflows/vendors/fred.py:260-272` | `get_macro_data` | 최신 관측일을 `**Latest:** {last_val} ({last_date})`로 표시만 하고 기준일과 비교하는 임계값은 없다 | 코드 확인 |

- 동작 설명: OHLCV는 최신 행이 요청일보다 10일 넘게 앞이면 `NoMarketDataError`(상세에 "stale")를 던지고 라우터가 `NO_DATA_AVAILABLE` 센티널로 바꾼다(`router.py:185-197`). 뉴스·StockTwits·Reddit은 응답이 요청 창을 덮지 못하면 `coverage_gap`이 "unavailable ... not an absence" 문구를 돌려준다. FRED는 최신 관측 날짜를 보여주기만 하고 판정은 LLM 몫이다. SEC EDGAR는 `filed <= as_of_date`로 공시일 기준 필터만 한다(`sec_edgar.py:176`). 스냅샷은 `load_ohlcv`를 통하므로 같은 10일 규칙을 따르고(`snapshot.py:39`), 스냅샷의 "Latest trading row used" 날짜는 항상 출력된다(`snapshot.py:97`).
- 조사 범위: `tradingagents/dataflows/` 전체와 `tradingagents/agents/`에 대해 grep `stale|max_age|too old|days old|freshness|older than|outdated|expired|ttl|last_updated|latest.*before|days_since|age_days`(대소문자 무시)와 `coverage_gap|_CACHE_TTL|mtime|timedelta\(days`. 일치한 모든 파일(`errors.py`, `router.py`, `ohlcv.py`, `market.py`, `polymarket.py`, `sec_edgar.py`, `fred.py`, `stocktwits.py`, `reddit.py`, `yahoo/news.py`, `date_window.py`)을 열어 확인했다.

#### R1-Q8 답변
- 결론: **확정.** 진입 종가는 `trade_date` 이후(당일 포함) 첫 거래일의 종가이고, `trade_date`가 거래일이면 그날 종가다. 청산은 진입 이후 `holding_period_days`(기본 5)번째 세션 종가(`stock.index[5]`, 진입 바를 0번째로 센다)다. 두 보고서 모두 부정확하다. `02-schedule.md` Q3-2 "분석일 종가"는 `trade_date`가 거래일일 때만 맞고(주말·휴일이면 다음 거래일), `03-decision.md` 4-7 "분석일 이후 첫 종가"는 `trade_date` 당일을 제외하는 것처럼 읽혀 **정정 필요**. 시작일 포함은 yfinance `history(start=...)`의 라이브러리 동작(설치 금지로 소스 미열람)에 의존하며, 레포는 `get_closes` 독스트링으로 그렇게 전제한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `dataflows/vendors/yahoo/market.py:268-272` | `get_closes` | `"""Daily closes from ``start_date`` up to, not including, ``end_date``."""` / `history = yf_retry(lambda: yf.Ticker(canonical).history(start=start_date, end=end_date))` / `return history["Close"] if ...` | 코드 확인 |
  | `memory/settlement.py:66-70` | `fetch_returns` | `start = datetime.strptime(trade_date, "%Y-%m-%d")` / `end = start + timedelta(days=round(holding_days * 7 / 5) + 7)` (= trade_date + 14일) | 코드 확인 |
  | `memory/settlement.py:73` | `fetch_returns` | `stock = _by_day(get_closes(ticker, trade_date, end_str))` (시작 = `trade_date` 그대로) | 코드 확인 |
  | `memory/settlement.py:81-83` | `fetch_returns` | `if len(stock) <= holding_days: return None, None, None, None` / `entry, exit_ = stock.index[0], stock.index[holding_days]` | 코드 확인 |
  | `memory/settlement.py:91` | `fetch_returns` | `raw = float((stock.iloc[holding_days] - stock.iloc[0]) / stock.iloc[0])` | 코드 확인 |
  | `default_config.py:180` | 기본값 | `"holding_period_days": 5,` | 코드 확인 |
  | `dataflows/vendors/yahoo/ohlcv.py:229-230` | `load_ohlcv` | `data = data[data["Date"] <= as_of_dt]` (분석 시점 데이터는 `trade_date` 당일 바를 포함한다) | 코드 확인 |

- 동작 설명: `get_closes(ticker, trade_date, trade_date+14일)`는 `trade_date`부터(포함) 14일 전(미포함)까지의 종가를 돌려준다. 첫 행이 진입(`index[0]`)이다. `trade_date`가 거래일이면 그날 종가이고, 아니면 다음 거래일 종가다. 청산은 `index[5]`이므로 진입 후 5세션째다. 바가 6개(`index[0]`~`index[5]`) 미만이면(`len(stock) <= 5`) `None`을 돌려 이후 런에서 다시 시도한다. `_by_day`(38-49행)는 종가가 0 이하인 행을 버린다. 벤치마크는 진입일 이전 7일치부터 가져와(`bench_start`, 75행) 진입일과 청산일에 `asof`로 값을 매긴다(92행). 따라서 결정에 쓰인 분석 데이터(당일 종가 포함)와 정산 진입가가 같은 종가가 되는 구조다. 이는 코드가 그렇게 정의한 사실이며, 같은 종가로 체결할 수 있는지는 이 레포의 범위 밖이다. 테스트는 `yfinance.Ticker`를 mock해 가격 리스트를 주므로(`tests/test_memory_log.py:514-528`) 시작일 포함 여부를 검증하지 않는다.
- 조사 범위: `memory/settlement.py` 전체, `dataflows/vendors/yahoo/market.py:268-272`, `default_config.py`의 `holding_period_days`, `tests/test_memory_log.py:512-545`, `tests/test_symbol_normalization_paths.py`의 `fetch_returns` 사용부.

#### R1-Q9 답변
- 결론: **확정.** 도구 분석가(Market, News, Fundamentals)의 첫 LLM 응답에 도구 호출이 없으면 그 분석가는 LLM 1회 호출로 끝난다. 도구 호출을 강제하는 코드(`tool_choice` 등)는 없다. 따라서 `03-decision.md` 4-8 표의 "최소 2"는 **정정 필요**: 코드상 하한은 분석가당 1회이고, 합계 하한은 "약 15회"가 아니라 12회다(분석가 3 + Sentiment 1 + Bull/Bear 2 + Research Manager 1 + Trader 1 + 리스크 3 + Portfolio Manager 1, 정산 성찰 제외). 상한 21회/분석가는 그대로다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `graph/setup.py:48-50` | `_tools_or_done` | `return "tools" if state["messages"][-1].tool_calls else END` | 코드 확인 |
  | `graph/setup.py:64-65,87-88` | `_analyst_graph` | `graph.add_edge(START, "agent")` / `graph.add_conditional_edges("agent", _tools_or_done, ["tools", END])` | 코드 확인 |
  | `agents/analysts/turn.py:26-27` | `take_turn` | `result = (prompt | llm.bind_tools(tools)).invoke(messages)` / `return result, "" if result.tool_calls else result.content` (`bind_tools(tools)`에 인자 하나, `tool_choice` 없음) | 코드 확인 |
  | `agents/analysts/market_analyst.py:77`, `news_analyst.py:56`, `fundamentals_analyst.py:57` | 호출처 | `result, report = take_turn(prompt, llm, TOOLS, state["messages"])` | 코드 확인 |
  | `agents/analysts/market_analyst.py:46,48` | 프롬프트 | `Please make sure to call get_stock_data first ...` / `Before writing the final report, call get_verified_market_snapshot ...` (지시이며 코드 강제가 아님) | 코드 확인 |
  | `agents/analysts/sentiment_analyst.py:109-120` | Sentiment | `No bind_tools — the data is already in the prompt.` / `invoke_structured_or_freetext(...)` 단일 호출 | 코드 확인 |
  | `graph/setup.py:76-77` | `more_or_wrap_up` | `return "wrap_up" if rounds(state["messages"]) >= max_tool_rounds else "agent"` (상한 쪽만 강제) | 코드 확인 |

- 동작 설명: 분석가 서브그래프는 `START → agent`로 시작하고 `agent`가 `take_turn`을 한 번 부른다. 응답의 마지막 메시지에 `tool_calls`가 비어 있으면 `_tools_or_done`이 `END`를 반환하고 그 응답 본문이 보고서가 된다(`turn.py:27`). 이때 LLM 호출은 1회다. 도구 라운드가 `max_tool_rounds`(20, `default_config.py:137`)에 도달하면 `wrap_up`이 1회 더 불러 최대 21회가 된다. 최소 쪽을 막는 장치는 프롬프트 문장뿐이다. 모델이 도구를 부르지 않고 보고서를 쓰면 코드는 이를 그대로 받아들이므로, 근거 없는 수치를 쓸 위험이 있다(스냅샷 도구의 "source of truth" 지시가 지켜지지 않을 수 있다).
- 조사 범위: `graph/setup.py` 전체, `agents/analysts/{turn,market_analyst,sentiment_analyst}.py`, `news_analyst.py`·`fundamentals_analyst.py`의 `take_turn` 호출부, `graph/analyst_execution.py`(`tools=...TOOLS` 연결 25,38,44행). `tradingagents/agents`, `tradingagents/graph`, `tradingagents/llm_clients`에서 grep `bind_tools|tool_choice|force|required`: `bind_tools`는 `turn.py:26` 한 곳뿐이고, `tool_choice`는 `llm_clients/`(`capabilities.py`, `openai_client.py`)에서 구조화 출력 시 `tool_choice`를 끄는 설정(`supports_tool_choice`)으로만 나온다. 분석가 도구 호출을 강제하는 `tool_choice` 설정은 없다.

#### R1-Q10 답변
- 결론: **확정.** 등급 파싱은 `agents/rating.py`의 `extract_rating`(55-93행)이 5등급 중 하나 또는 `None`을 돌려주고, `parse_rating`(96-103행)이 `None`을 `REVIEW`("REVIEW" 상수는 30행)로 바꾼다. 평가 순서는 아래 표와 같다. 호출처는 PM 자유 텍스트 폴백(`managers/portfolio_manager.py:86`), 메모리 로그 태그(`memory/log.py:56`), `run_rating`(`rating.py:106-112`, `trading_graph.py:369,404,463`, `reporting.py:26`, `report_html.py:251`)이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `agents/rating.py:37-38` | `_RATING_LABEL_RE` | `(?<![a-z])rating\b[^:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*(\w+)` (IGNORECASE) — 줄 어디에든 있는 "rating … : 값" 라벨 | 코드 확인 |
  | `agents/rating.py:45-50` | `_RATING_LINE_RE` | `\s*(?P<item>(?:[-+*\u2022]|\d+[.)])\s+)?[\s*_#]*` + `(?:(?:final\|our\|overall\|my\|recommended\|updated\|revised\|new\|current)\s+)*` + `rating[^\w:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*(?P<value>\w+)` — 줄 시작에서 "본인 등급줄"만 매칭. `item` 그룹은 목록 표시(`- `, `* `, `1. ` 등) | 코드 확인 |
  | `agents/rating.py:53` | `_RATING_SCALE_RE` | `rating\s*(scale\|options\|legend)` — 등급 척도 설명 줄 | 코드 확인 |
  | `agents/rating.py:63-65` | 전처리 | `if not text: return None` / `norm = unicodedata.normalize("NFKC", text)` (전각 `：`을 ASCII로) | 코드 확인 |
  | `agents/rating.py:74-76` | `lines`, `first` | `lines = [line for line in norm.splitlines() if line.strip() and not _RATING_SCALE_RE.search(line)]` / `first = next((line for line in lines if not line.lstrip().startswith("#") or _RATING_LINE_RE.match(line)), "")` | 코드 확인 |
  | `agents/rating.py:77-80` | 즉시 채택 | `opening = m if m and m.group("value").lower() in _RATING_SET else None` / `if opening and not opening.group("item"): return opening.group("value").capitalize()` | 코드 확인 |
  | `agents/rating.py:82-93` | 합의 판정 | `own = [opening...]` 후 모든 줄을 훑어 목록 표시 없는 본인 등급줄은 `own`, 줄 안의 라벨은 `labels`에 모음 / `found = own or labels` / `return found[0] if found and len(set(found)) == 1 else None` | 코드 확인 |
  | `agents/rating.py:96-103` | `parse_rating` | `rating = extract_rating(text)` / `return rating if rating is not None else default` (`default=RATING_REVIEW`) | 코드 확인 |

- 동작 설명: 위에서부터 순서대로 평가한다.

  | 순서 | 조건 | 반환 | 예시 입력 (출처) |
  |---|---|---|---|
  | 1 | 텍스트가 비었음(`rating.py:63`) | `None` → `REVIEW` | `""` |
  | 2 | 공백 줄과 척도 줄(`Rating Scale/Options/Legend`)을 제외하고(74행), `#`로 시작하는 헤딩 줄은 건너뛰되 헤딩이 등급줄 모양(`## Our rating - Buy`)이면 그 줄을 첫 줄로 삼는다(75-76행). 첫 줄이 `[final/our/overall/my/…] rating <구분자> <5등급 단어>` 형태이고 목록 표시(`- `, `1. `)가 없다 | 그 등급을 즉시 반환(뒤 줄 무시) | `"**Rating**: Buy\n\nAccumulate."` → `Buy` (`tests/test_rating_integrity.py:89`). 등급줄이 맨 앞이 아니어도 `Buy arguments were raised and rejected.` 다음 `Rating: Underweight`는 아래 4번에서 `Underweight` (같은 파일 26-27행) |
  | 3 | 첫 줄이 등급줄인데 목록 표시가 있다(`- **Rating**: Buy`). 인용·목록 머리일 수 있으므로 즉시 채택하지 않고 `own`에 넣어 다음 단계에서 다른 줄과 합의를 본다(82행) | 4번으로 | `"- **Rating**: Buy\nConsensus rating: Sell"` → `Buy` (두 번째 줄은 `Consensus`가 접두어 목록에 없어 `_RATING_LINE_RE`에 안 걸리므로 `own`이 `labels`보다 우선, 구성한 예시) |
  | 4 | 모든 줄을 훑어 목록 표시 없는 본인 등급줄을 `own`, 줄 안의 `rating … : 값` 라벨을 `labels`에 모은다(84-88행). 단 값이 5등급 집합(`_RATING_SET`) 안에 있는 것만 센다. `found = own or labels` | 5번으로 | `INVERTED`(`Final rating — Underweight.`) → `Underweight` (`tests/test_rating_integrity.py:17-19,31-32`) |
  | 5a | `found`가 비어 있다(라벨 없음. 산문 속 등급 단어만 있거나, 값이 `Strong`처럼 집합 밖이거나, 척도 줄만 있거나, 환불·거부 문장) | `None` → `REVIEW` | `"We would not Sell here; the dip is a chance to add."` (같은 파일 44-52행), `"I'm sorry, I can't provide a rating for this security."` (20,56-58행) |
  | 5b | `found`에 서로 다른 등급이 둘 이상이고 어느 것이 결정인지 표시가 없다 | `None` → `REVIEW` | `"The bull wants Buy, the bear wants Sell, and the committee was split."` (36-40행). 라벨 두 개가 충돌하는 예: `"Analyst note. Rating: Buy\nTrader's rating: Sell"` → `Buy`·`Sell` 충돌로 `REVIEW`(구성한 예시, 테스트에는 없음) |
  | 5c | `found`가 모두 같은 등급 하나 | 그 등급(첫 값, `capitalize`) | `Rating: Buy` 줄이 두 번 → `Buy` |

  `03-decision.md` 4-6 "`REVIEW`가 되는 조건" 행의 네 조건(라벨 없음, 라벨 충돌, 산문에만 등급 단어, 척도 줄만 있음)은 5a·5b와 일치한다. 마지막 문장 "라벨 첫 줄(헤딩 제외)이 `- ` 없는 본인 등급줄이면 그것을 채택"은 2번(즉시 채택, 이후 줄에 다른 등급이 있어도 무시)을 뜻하므로 "조건들 중 가장 먼저 평가되며 다른 줄과 충돌해도 이 줄이 이긴다"고 순서를 명시하도록 고치는 것이 좋다(**보고서 보강 필요**). 구조화 출력이 성공하면 이 파서는 쓰이지 않는다(`portfolio_manager.py:82-83`, `final_rating = decision.rating.value`).
- 조사 범위: `agents/rating.py` 전체, `tests/test_rating_integrity.py` 1-110행, grep `extract_rating|parse_rating|run_rating|RATING_REVIEW|is_review`로 `tradingagents/`와 `cli/` 전 호출처 확인. 정규식 동작은 코드 읽기로 추적했고 실행은 하지 않았다.

#### R1-Q11 답변
- 결론: **확정.** 정산 대상 선정과 가격 조회 종료일은 런의 `trade_date`와 무관하다. `Memory Log` 노드는 "모든 티커의 pending 결정"을 대상으로 하고, 각 결정의 날짜(`entry["date"]`)에서 약 14일 뒤까지 Yahoo에서 실제 가격을 받아 정산한다. 런의 `trade_date`는 이 경로로 전달되지 않는다. 따라서 과거 날짜 런에서도 그 런의 `trade_date` 이후 가격이 정산에 쓰이며, 주입 시점 필터(`log.py:105-107`)가 그 결과가 프롬프트에 들어가는 것을 막는 유일한 장치다. 단, 이 필터는 읽을 때만 막고 메모리 로그 파일의 기록 자체는 막지 않는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `graph/trading_graph.py:308-321` | `_memory_step` | `done = self.settle_all_pending(wait=False)` (인자에 `state["trade_date"]` 없음) | 코드 확인 |
  | `graph/trading_graph.py:348-356` | `settle_all_pending` | `return settlement.settle_all_pending(self.memory_log, self.reflector, self.config, wait=wait)` | 코드 확인 |
  | `memory/settlement.py:158-169` | `settle_all_pending` | `for ticker in dict.fromkeys(e["ticker"] for e in memory_log.get_pending_entries()):` → `settle_pending(ticker, ...)` (날짜 필터 없음) | 코드 확인 |
  | `memory/log.py:89-91` | `get_pending_entries` | `return [e for e in self.load_entries() if e.get("pending")]` | 코드 확인 |
  | `memory/settlement.py:123,129-131` | `settle_pending` | `pending = [e for e in memory_log.get_pending_entries() if e["ticker"] == ticker]` / `fetch_returns(ticker, entry["date"], config.get("holding_period_days", 5), benchmark=benchmark,)` | 코드 확인 |
  | `memory/settlement.py:66-73` | `fetch_returns` | `end = start + timedelta(days=round(holding_days * 7 / 5) + 7)`, 시작과 끝은 모두 결정 날짜 기준, 실제 현재 시각은 `yf` 응답이 결정 | 코드 확인 |
  | `memory/settlement.py:81-82,136-137` | 보유 기간 미경과 | `if len(stock) <= holding_days: return None, None, None, None` → `if raw is None: continue` (현재까지 거래된 바가 부족할 때만 건너뜀) | 코드 확인 |
  | `graph/trading_graph.py:328-330` | 주입 | `past_context = self.memory_log.get_past_context(state["company_of_interest"], as_of=self._memory_as_of(state["trade_date"]))` | 코드 확인 |
  | `graph/trading_graph.py:130-138` | `_memory_as_of` | `return str(trade_date) if is_historical(trade_date) else None` | 코드 확인 |
  | `memory/log.py:105-107` | `get_past_context` | `entries = [e for e in self.load_entries() if not e.get("pending")]` / `if as_of is not None: entries = [e for e in entries if e.get("resolved") and e["resolved"] <= as_of]` | 코드 확인 |
  | `memory/settlement.py:97` | `resolution_date` | `resolution_date = exit_.strftime("%Y-%m-%d")` (청산 종가일을 `resolved`로 저장) | 코드 확인 |
  | `graph/setup.py:157-159`, `agents/managers/portfolio_manager.py:35-38` | 소비처 | `only the Portfolio Manager reads its lessons` / `past_context = state.get("past_context", "")` | 코드 확인 |

- 동작 설명: 과거 날짜 `T` 런이 시작하면 `Memory Log` 노드가 분석가와 병렬로 실행된다. 이 노드는 `T`와 무관하게 로그의 pending 항목 전부(다른 티커 포함, 날짜가 `T`보다 뒤인 것도 포함)를 대상으로 `fetch_returns(ticker, 그 결정의 날짜, 5)`를 호출한다. 결정 날짜 + 5거래일이 이미 지나 있으면(현재 시각 기준) 실제 가격으로 정산해 `resolved`(청산일)와 반성문을 로그에 기록한다. 이어서 `get_past_context(..., as_of=T)`가 `resolved <= T`인 항목만 골라 Portfolio Manager 프롬프트의 `Lessons from prior decisions and outcomes`에 넣는다. `T`가 오늘이면 `as_of=None`이라 필터가 꺼진다. 결과적으로 `T` 이후에 정산된 교훈은 프롬프트에 들어가지 않고(`resolved`가 없거나 `T` 이후), 정산 호출 자체와 반성문 LLM 호출 비용은 `T`와 무관하게 발생한다. 이 장치는 `pending` 항목의 `resolved` 필드가 정확히 저장된다는 전제에 의존하는데, `update_with_outcome(..., resolution_date=resolution_date)`(`settlement.py:152-153`)가 이를 저장한다. `resolved`가 없는 이전 형식 항목은 `as_of`가 있으면 모두 제외된다(106행 `e.get("resolved")`).
- 조사 범위: `graph/trading_graph.py` 130-138, 300-360, 372-404, `memory/settlement.py` 전체, `memory/log.py` 32-135, `graph/setup.py:157-166`, `agents/managers/portfolio_manager.py:30-40`, `dataflows/date_window.py:39-41`. grep `past_context|settle_all_pending|_memory_as_of|_memory_step|get_pending_entries`로 `tradingagents/` 전체 호출처를 확인했다.

#### R1-Q12 답변
- 결론: **없음 확정.** 뉴스·StockTwits·Reddit·Polymarket 텍스트를 프롬프트에 넣기 전에 지시문 제거, 이스케이프, "아래는 데이터이며 지시가 아니다"류 문구, 출력 검증으로 프롬프트 인젝션을 막는 코드나 프롬프트 문장은 없다. 입력 정리는 있으나 모두 형식 정리이고 인젝션 방어가 아니다. 인젝션을 명시적으로 언급하는 코드는 `dataflows/symbols.py:159`의 경로 순회(path traversal) 방어(`safe_ticker_component`)뿐이다. `03-decision.md` 4-9 4번과 `05-boundary-and-fit.md` 의견 2의 "추론"은 "없음 확정(조사 범위 아래)"으로 바꿀 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `agents/analysts/sentiment_analyst.py:149-170` | `_build_system_message` | 블록 구분자만 있다: `<start_of_news>\n{news_block}\n<end_of_news>`, `<start_of_stocktwits>...`, `<start_of_reddit>...`. 블록이 데이터라는 안내나 닫는 태그 이스케이프가 없다(외부 텍스트에 `<end_of_news>`가 있어도 처리하지 않는다) | 코드 확인 |
  | `agents/analysts/sentiment_analyst.py:172-199` | 분석 지침 | 8개 항목과 출력 필드 설명 어디에도 "블록 안 문장의 지시를 따르지 말라"는 문장이 없다 | 코드 확인 |
  | `agents/structured.py:36-39` | `NO_EXTERNAL_TOOLS` | `"Use only the evidence provided in this prompt. Do not call external tools or search the web; if something is missing, say so explicitly."` (도구 호출 억제용이며 지시문 불신 안내가 아니다) | 코드 확인 |
  | `dataflows/vendors/yahoo/news.py:75-84` | `_format_articles` | `out += f"### {data['title']} (source: {data['publisher']})\n"` / `out += f"{data['summary']}\n"` (제목·요약을 가공 없이 연결) | 코드 확인 |
  | `dataflows/vendors/stocktwits.py:58-60,138-140` | `_body`, 포맷 | `return html.unescape(message.get("body") or "")` / `body = _body(m).replace("\n", " ").strip()` / `body = body[:280] + "…"` (엔티티 해제, 줄바꿈 제거, 280자 절단) | 코드 확인 |
  | `dataflows/vendors/reddit.py:126-134,326-331` | `_strip_html`, 포맷 | `text = re.sub(r"<[^>]+>", " ", content)` / `" ".join(html.unescape(text).split())` / `selftext[:240] + "…"` (HTML 태그 제거와 240자 절단, 인젝션 방어 아님) | 코드 확인 |
  | `agents/post_screen.py:1-60` | `jev_screen` | `TYPESAFE_API_KEY`가 있을 때만 동작하는 선택 기능. 질문은 "게시물이 해당 종목에 관한 것인가(`about`)"와 "방향(`stance`)"이다. 주제 무관 게시물 제거와 방향 집계이며 지시문 탐지가 아니다 | 코드 확인 |
  | `dataflows/symbols.py:155-173` | `safe_ticker_component` | `Tickers come from user CLI input or from LLM tool calls, both of which can be influenced by attacker-controlled content (e.g. prompt injection embedded in fetched news).` (파일 경로 이스케이프만 막는다. 또 도구의 `symbol`/`ticker` 인자는 `InjectedState("company_of_interest")`로 상태에서 주입돼 LLM이 임의로 바꿀 수 없다, `tools.py:20,99` 등) | 코드 확인 |

- 동작 설명: 뉴스(`get_news` 도구 결과 또는 Sentiment의 사전 수집), StockTwits, Reddit 텍스트는 정리(`html.unescape`, 태그 제거, 줄바꿈 제거, 길이 절단) 후 프롬프트에 그대로 삽입된다. 이후 Bull/Bear 등 하위 에이전트는 분석가 보고서(LLM 요약)를 입력으로 받으므로 인젝션이 있다면 1차 LLM이 요약하며 전파될 수 있다(구조상 사실이며 실제 성공 여부는 실행 실험이 필요한 사항이라 범위 밖). 최종 결정 단계는 구조화 출력의 enum 검증과 `REVIEW` 표식만 있고 내용 기반 이상 탐지는 없다(`03-decision.md` 4-6).
- 조사 범위: `tradingagents/`(특히 `agents/`, `dataflows/`, `graph/`, `memory/`)와 `cli/`에 대해 grep(대소문자 무시) `inject|untrusted|prompt.?injection|adversar|malicious|not (an )?instruction|do not follow|disregard|ignore (any|all|previous|prior|above)|treat .{0,40} as data|sanitiz|escape|as data|jailbreak|prompt.?guard|html\.unescape|bleach|only the evidence|quoted|verbatim`. `InjectedState`와 `injection` 일치는 모두 LangGraph 상태 주입 또는 메모리 로그 "프롬프트 주입(주입 = 삽입)" 의미이고, 방어 문맥은 `symbols.py:159`뿐이다. 추가로 `tests/`, `README.md`, `CHANGELOG.md`에서 `injection|untrusted`를 grep해 방어 기능 기록이 없음을 확인했다(`tests/test_structured_agents.py`, `tests/test_memory_log.py`의 "injection"은 메모리 로그 삽입 의미). 에이전트 프롬프트 파일(`agents/analysts/*.py`, `researchers/*.py`, `risk_mgmt/*.py`, `managers/*.py`, `trader/*.py`)도 같은 grep 대상에 포함했고, 시스템 메시지를 직접 읽은 것은 `market_analyst.py`, `news_analyst.py`의 프롬프트, `sentiment_analyst.py` 전체, `portfolio_manager.py` 56-66행이다(모두 데이터 불신 안내 문장 없음).

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `agents/tools.py:15,88-94`(직접 import, `build_verified_market_snapshot` 호출)와 `ohlcv.py:212-217`(`yf.Ticker(...).history`)를 열어 확인함. `router.py:97-149`의 `VENDOR_METHODS` 키가 11개이고 스냅샷이 없음을 확인함. 완료 조건(도구 본문, 로더 위치, 고정 지점)을 충족함 |
| R1-Q2 | 없음 확정 | `yahoo/market.py:223` `df[indicator]` 원문과 `pyproject.toml:26` `"stockstats>=0.6.5"`을 확인함. `uv.lock`이 없음을 확인함. `StockDataFrame\|rsi_[0-9]\|_14\b`를 직접 grep해 0건임을 재확인함. 기본 윈도 숫자는 레포에 없는 서드파티 라이브러리 내부값이라 정적 확인 불가 하위 판단을 인정함(레포 쪽 "지정 없음"은 완전히 확정됨) |
| R1-Q3 | 해소 | `router.py:232-236`(`impl_func(*args, **kwargs)` 그대로 반환)와 `288-295`(`OPTIONAL_CATEGORIES` 센티널 / `raise first_error`)를 확인함. 인자 순서표, 반환형, 예외 타입별 분기가 모두 있음 |
| R1-Q4 | 해소 | `alpha_vantage/common.py:152-164`(`end_dt` 필터와 "only thing keeping bars after end_date" 주석)와 `news.py:27-31`(`time_from`/`time_to`만 사용)을 확인함. `cache\|lru`를 grep해 0건임을 재확인함. 함수별 필터 유무와 캐시 부재가 정리됨. 뉴스 서버가 `time_to`를 지키는지는 외부 API 사항으로 적절히 분리함 |
| R1-Q5 | 정적 확인 불가 | `graph/setup.py:85` `ToolNode(list(spec.tools))`(인자 없음)를 확인함. `handle_tool_error`를 grep해 0건이고 `pyproject.toml:16` `"langgraph>=1.2.12"`도 확인함. 결과는 레포에 없는 LangGraph 기본값에 달려 있음. 레포 쪽 예외 유출 경로(`router.py:295`, 보호 없는 도구 목록)는 확정됐고 (A)/(B) 경우의 수도 적혀 있어 종료 상태로 인정함 |
| R1-Q6 | 해소 | `yahoo/news.py:107-108,117`(`yf_retry`는 `get_news` 호출만 감싸고 `_extract_article_data`는 밖에 있음), `22-35`(`(content.get("provider") or {}).get`, `url_obj.get`), `yahoo/common.py:61-76`, `router.py:251-259`, `sentiment_analyst.py:63-66`(try 없음, "no exceptions surface" 주석)을 확인함. 경로 존재가 정적으로 확정됨. 실제 발생은 Yahoo JSON 형태에 달려 있어 남은 부분은 정당한 외부 의존임 |
| R1-Q7 | 해소 | `ohlcv.py:18` `MAX_OHLCV_STALE_DAYS = 10`과 `date_window.py:44-68` `coverage_gap` 원문을 확인함. grep 패턴과 조사 범위가 적혀 있음. "임계값 규칙은 OHLCV뿐, 유사 문구 장치 4종"이라는 결론이 명확함 |
| R1-Q8 | 해소 | `yahoo/market.py:268-272`(독스트링 "from start_date up to, not including, end_date", `history(start=trade_date, ...)`)와 `settlement.py:66-83`(`stock.index[0]`, `stock.index[holding_days]`)을 확인함. 시작일 포함은 yfinance 내부 동작이지만 레포 계약(독스트링)으로 명시돼 있어 결론을 인정함. 두 보고서의 정정 방향도 적혀 있음 |
| R1-Q9 | 해소 | `graph/setup.py:48-50` `_tools_or_done`과 `turn.py:26-27` `llm.bind_tools(tools)`(`tool_choice` 없음)를 확인함. 합계 12회는 기본값 `max_debate_rounds=1`, `max_risk_discuss_rounds=1`(`default_config.py:133-134`, `conditional_logic.py:16,26`)을 전제로 한 하한이며 이를 직접 확인함 |
| R1-Q10 | 해소 | `agents/rating.py:74-93`을 열어 첫 줄 선택 → 목록 표시 없는 등급줄 즉시 채택 → `own or labels` 합의 → 단일 값이 아니면 `None` 흐름을 확인함. 정규식 원문, 순서표, 예시 입력이 모두 있음 |
| R1-Q11 | 해소 | `trading_graph.py:308-321`(`settle_all_pending(wait=False)`, `trade_date` 미전달), `settlement.py:158-169`(전체 pending 티커), `log.py:105-107`(`resolved <= as_of` 필터)을 확인함. 주입 필터가 유일한 차단 장치라는 결론이 근거와 맞음 |
| R1-Q12 | 없음 확정 | `dataflows/symbols.py:155-160`의 경로 순회 방어 주석을 확인함. `untrusted\|do not follow\|treat .{0,40} as data\|disregard`를 직접 grep해 0건임을 재확인함. 조사 패턴(동의어 포함)과 디렉터리 범위가 충분함 |

---

## 최종 정리 (질문자)

- 총 라운드: 1 / 총 질문: 12 / 해소 9 · 없음 확정 2 · 정적 확인 불가 1
- 핵심 확정 사실:
  1. 도구 12개 중 11개만 `route_to_vendor`를 거친다. `get_verified_market_snapshot`은 `build_verified_market_snapshot` → `load_ohlcv` → `yf.Ticker().history`로 Yahoo에 고정돼 있고, 정산의 `get_closes`도 라우터를 거치지 않는다(`agents/tools.py:15,88-94`, `yahoo/ohlcv.py:212-217`, `memory/settlement.py:73`).
  2. 벤더 계약: 인자는 도구가 넘긴 그대로 위치 인자로 전달되고 반환값(`str`)은 검사 없이 통과한다. 실패는 `NoMarketDataError`(무데이터), `VendorUnavailableError`(장애), `VendorNotConfiguredError`(키 없음)로 알려야 하며, 그 밖의 예외는 필수 카테고리에서 `raise first_error`로 다시 던져진다(`router.py:232-236,288-295`).
  3. Yahoo 경로의 지표 윈도는 레포가 지정하지 않고 stockstats 기본값(`>=0.6.5`, 락 없음)을 따른다. Alpha Vantage 경로는 레포가 값을 직접 지정한다(`yahoo/market.py:223`, `alpha_vantage/indicator.py:15,90-137`).
  4. Alpha Vantage는 OHLCV와 지표만 클라이언트에서 날짜를 자르고, 뉴스는 API 파라미터에 맡기며, 펀더멘털과 내부자 거래는 과거 날짜 런이면 반환을 보류한다. 캐시는 없다(`alpha_vantage/common.py:152-164`, `news.py:27-31`, `date_window.py:108-176`).
  5. Sentiment 사전 수집의 `get_news.func`는 `yf_retry` 밖의 가공 코드에서 난 예외를 그대로 내보낼 수 있는 경로가 있다. ToolNode를 거치지 않으므로 이 경로가 있다는 사실은 라이브러리와 무관하게 확정이다(`yahoo/news.py:107-117`, `router.py:251-259,295`, `sentiment_analyst.py:63-66`).
  6. 일수 임계값으로 stale을 거부하는 규칙은 OHLCV의 10일 규칙뿐이다. 뉴스·StockTwits·Reddit에는 `coverage_gap` 문구가 있고, Polymarket에는 종료 시장 제외가, FRED에는 최신일 표시가 있다(`ohlcv.py:18,109-143`, `date_window.py:44-68`).
  7. 정산 진입가는 `trade_date` 당일(거래일이면)이나 그 이후 첫 거래일의 종가이고, 청산가는 진입 바를 0으로 셀 때 5번째 세션의 종가다(`settlement.py:66-83`, `yahoo/market.py:268-272`).
  8. 분석가에게 도구 호출을 강제하는 코드는 없다. 분석가 1명당 최소 LLM 호출은 1회이고, 기본 토론 라운드 설정에서 런 전체 하한은 12회다(`graph/setup.py:48-50`, `turn.py:26-27`).
  9. PM 자유 텍스트 등급은 `extract_rating`이 첫 등급줄 즉시 채택 → `own or labels` 합의 순서로 판정하고, 합의가 안 되면 `REVIEW`가 된다(`agents/rating.py:55-103`).
  10. Memory Log 정산은 런의 `trade_date`와 무관하게 모든 pending을 현재 가격으로 정산한다. 과거 날짜 런에서 look-ahead를 막는 장치는 읽을 때 적용하는 `resolved <= as_of` 필터 하나다(`trading_graph.py:308-321`, `settlement.py:158-169`, `log.py:105-107`).
  11. 외부 텍스트에 대한 프롬프트 인젝션 방어 장치는 없다. 유일한 관련 방어는 티커 경로 순회 방지다(`symbols.py:155-173`).

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` Q1-0 | 도구 12개는 모두 `route_to_vendor()`를 거친다 | 11개만 라우터를 거친다. `get_verified_market_snapshot`은 Yahoo `load_ohlcv`에 직접 고정돼 있다(`tools.py:15,90`, `snapshot.py:39`) | R1-Q1 |
| `05-boundary-and-fit.md` 의견 3 | 키움 벤더를 라우터에 추가하면 된다 | 라우터 등록 외에 스냅샷의 `load_ohlcv`와 정산의 `get_closes`(`settlement.py:73`)도 교체해야 한다 | R1-Q1 |
| `01-data.md` Q1-1 지표 파라미터 행 | RSI 14, 볼린저 20일 2σ, ATR 14, MACD 12/26/9 (추론) | Yahoo 경로는 레포가 파라미터를 지정하지 않고 stockstats(`>=0.6.5`, 락 없음) 기본값을 따른다(숫자는 정적 확인 불가). Alpha Vantage 경로는 RSI·ATR 14, BBANDS 20, SMA 50/200, EMA 10을 코드로 지정하고 MACD 기간 인자는 넘기지 않는다 | R1-Q2 |
| `01-data.md` Q2-1 한국 벤더 삽입 위치 행 | 위치만 있음 (추론) | R1-Q3 답변의 인자 순서표, `str` 반환, 예외 3종 계약을 반영하고 "확정"으로 바꾼다 | R1-Q3 |
| `01-data.md` Q2-4, `next.md` 미확인 체크리스트 | Alpha Vantage 캐시 여부·look-ahead 필터 미확인 | 캐시 없음. OHLCV와 지표는 클라이언트에서 날짜를 자르고, 뉴스는 API `time_to`에 맡기며, 펀더멘털과 내부자 거래는 과거 날짜 런이면 반환을 보류한다 | R1-Q4 |
| `01-data.md` Q2-6 도구 예외 행 | 미확인 | 정적 확인 불가(LangGraph `ToolNode` 기본값에 의존, `handle_tool_errors` 미지정). 레포 쪽 유출 경로(`router.py:295`, 보호 없는 도구 8개)는 확정 | R1-Q5 |
| `01-data.md` Q2-6 마지막 행, `00-overview.md` 6절 | 기본 설정에서 실제 발생 가능성은 낮다 (추론) | 예외 유출 경로는 존재한다(`yahoo/news.py:108,117`의 `yf_retry` 밖 가공 → `router.py:295` → `sentiment_analyst.py:66` 무보호). 실제 발생 여부는 Yahoo 응답 형태에 달려 있다 | R1-Q6 |
| `02-schedule.md` Q3-4, `00-overview.md` 5절 | stale은 OHLCV 10일 규칙만 | 일수 임계값 규칙은 OHLCV 10일 규칙뿐이다. 다만 `coverage_gap` 문구(뉴스·StockTwits·Reddit), Polymarket 종료 시장 제외, FRED 최신일 표시 같은 유사 장치가 있다 | R1-Q7 |
| `02-schedule.md` Q3-2 | 정산 진입가는 분석일 종가 | `trade_date` 당일(거래일이면)이나 그 이후 첫 거래일의 종가 | R1-Q8 |
| `03-decision.md` 4-7 기간 행 | 진입 = 분석일 이후 첫 종가, 청산 = 5번째 이후 종가 | 진입 = `trade_date` 당일을 포함한 첫 거래일 종가(`index[0]`), 청산 = 진입 후 5번째 세션 종가(`index[5]`) | R1-Q8 |
| `03-decision.md` 4-8 호출 수 표 | 도구 분석가 최소 2, 합계 최소 약 15회 | 도구 분석가 최소 1(도구 강제 없음), 합계 하한 12회(기본 토론 라운드 1, 정산 성찰 제외) | R1-Q9 |
| `03-decision.md` 4-6 `REVIEW` 조건 행 | 조건 나열, 평가 순서 없음 | 평가 순서를 적는다: 첫 줄(헤딩 제외)이 목록 표시 없는 본인 등급줄이면 가장 먼저 즉시 채택한다(뒤 줄과 충돌해도 이긴다). 그 밖에는 `own or labels`가 단일 값일 때만 채택하고 아니면 `REVIEW` | R1-Q10 |
| `01-data.md` Q2-5, `03-decision.md` 4-7 | 과거 날짜 런은 `resolved <= trade_date` 교훈만 주입 (point-in-time 장치) | 정산 자체는 `trade_date`와 무관하게 모든 pending을 현재 가격으로 수행하고 로그에 기록한다. 읽을 때 적용하는 `log.py:105-107` 필터가 유일한 차단 장치라는 점을 덧붙인다 | R1-Q11 |
| `03-decision.md` 4-9 4번, `05-boundary-and-fit.md` 의견 2 | 방어 장치를 찾지 못했다 (추론) | 없음 확정(R1-Q12 grep 패턴과 범위). 입력 정리는 형식 정리일 뿐이고, 관련 방어는 `symbols.py:155-173`의 경로 순회 방지뿐이다 | R1-Q12 |
