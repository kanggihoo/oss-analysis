---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/__init__.py
  - tradingagents/dataflows/router.py
  - tradingagents/dataflows/errors.py
  - tradingagents/dataflows/net.py
  - tradingagents/dataflows/files.py
  - tradingagents/default_config.py
  - tradingagents/agents/tools.py
  - tradingagents/dataflows/vendors/yahoo/common.py
  - tradingagents/dataflows/vendors/yahoo/market.py
  - tradingagents/dataflows/vendors/yahoo/ohlcv.py
  - tradingagents/dataflows/vendors/yahoo/snapshot.py
  - tradingagents/dataflows/vendors/yahoo/fundamentals.py
  - tradingagents/dataflows/vendors/yahoo/news.py
  - tradingagents/dataflows/vendors/alpha_vantage/common.py
  - tradingagents/dataflows/vendors/alpha_vantage/stock.py
  - tradingagents/dataflows/vendors/alpha_vantage/indicator.py
  - tradingagents/dataflows/vendors/alpha_vantage/fundamentals.py
  - tradingagents/dataflows/vendors/alpha_vantage/news.py
  - tradingagents/dataflows/vendors/sec_edgar.py
  - tradingagents/dataflows/vendors/fred.py
  - tradingagents/dataflows/vendors/polymarket.py
depends:
  - configuration.md
  - point-in-time.md
  - run-input.md
status: ready
---

# 데이터 벤더 라우팅과 수집 패밀리

> 분석 도구의 메서드·인자와 실행 설정을 받아, 선택한 데이터 공급자에서 가격·지표·기업 재무·뉴스·거시·예측시장 자료를 가져오고 실패를 구분해 반환한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 도구가 분석 종목·제한된 기준일·도구별 인자를 요청한다.
2. 메서드가 속한 카테고리를 찾고 `tool_vendors[method]`, 그다음 `data_vendors[category]` 순서로 벤더 목록을 고른다.
3. 메서드가 실제 제공하는 벤더만 남겨 순서대로 호출한다. 첫 정상 반환값을 그대로 반환한다.
4. 예외가 나면 종류를 기억하고 다음 벤더를 시도한다. 실패의 최종 우선순위에 따라 '공급자 장애'·'자료 없음' 안내문 또는 예외를 반환한다.
5. 개별 벤더는 HTTP·SDK 응답을 CSV·Markdown·원본 JSON 문자열로 가공한다. Yahoo 지표 가격과 SEC facts는 자체 파일 캐시를 사용한다.
6. 검증 스냅샷은 이 라우터를 우회해 Yahoo를 직접 호출한다. 소셜의 StockTwits·Reddit 수집도 이 패밀리 등록부 밖이며 [감성 분석](sentiment-analysis.md)이 소유한다.

### 1.2 범위·통합 지점

- 제공: 11개 메서드의 등록·벤더 선택·폴백·예외 의미와 Yahoo, Alpha Vantage, SEC EDGAR, FRED, Polymarket의 실제 수집/가공 규칙.
- 선행: [설정](configuration.md)의 실행 스코프 설정, [기준일 제한](point-in-time.md)의 날짜·보류·커버리지 유틸, [실행 입력](run-input.md)의 종목 정규화·경로 검증.
- 제외: LLM이 어떤 도구를 호출하는지와 해석하는 기준은 각 분석가 스펙, 소셜 수집·Jev 필터는 감성 스펙, 성과 정산용 종가 소비는 메모리 스펙이 소유한다. 이 문서에서는 그 경로가 쓰는 Yahoo `get_closes`의 호출 의미까지만 정한다.
- 외부 의존: yfinance·stockstats·pandas·requests. SDK는 요청 매개변수에 대한 응답/예외를 주는 경계이며 실제 최신 데이터 보장·계산 라이브러리 내부 상수는 실행 검증하지 않았다. stockstats는 원본 이름으로 계산을 요청하며 원본에서 덮어쓰지 않은 기본값을 임의로 확정하지 않는다.
- 소유 상태·부작용: 데이터 요청, 로그, Yahoo 가격 CSV·SEC JSON 캐시와 고유 임시파일. 정기 데이터 동기화 작업은 만들지 않고 호출 시 읽고 수집한다. yfinance 전역 `config.debug.hide_exceptions=False`도 설정한다.

### 1.3 인터페이스와 데이터 의미

#### 요청·반환 계약

`route_to_vendor(method,*args,**kwargs)`는 메서드명을 소비해 등록 함수를 찾고 나머지 인자를 변경 없이 `impl_func(*args,**kwargs)`로 전달한다. list로 등록된 경우 첫 함수를 쓴다. 타입·길이·빈 본문 검증이나 통합 응답 스키마는 없다. 도구의 원래 인자·기본값과 실제 인자 순서는 기준일 제한 스펙 C-04~C-06을 따른다.

| 메서드 / 위치 인자 | 카테고리 | 등록 벤더 순서(`default`일 때) | 반환 데이터 의미 |
|---|---|---|---|
| `get_stock_data(symbol,start,end)` | `core_stock_apis` | alpha_vantage → yfinance | 기간 포함 OHLCV CSV. AV는 adjusted close·배당/분할 이벤트도 원본 CSV에 포함 |
| `get_indicators(symbol,indicator,date,lookback)` | `technical_indicators` | alpha_vantage → yfinance | 지표 날짜별 값과 설명. 벤더별 형식·정렬·지원 차이 있음 |
| `get_fundamentals(ticker,date)` | `fundamental_data` | alpha_vantage → yfinance | 기업 개요. Yahoo는 필드별 텍스트, AV는 원본 응답 문자열 |
| `get_balance_sheet`, `get_cashflow`, `get_income_statement(ticker,freq,date)` | `fundamental_data` | alpha_vantage → sec_edgar → yfinance | 재무제표. SEC는 공시일 기준 기간별 CSV. Yahoo는 SDK 표 CSV. AV는 원본 JSON/응답 문자열이고 freq를 별도로 필터하지 않음 |
| `get_news(ticker,start,end)` | `news_data` | alpha_vantage → yfinance | 뉴스·요약·출처·링크 또는 AV NEWS_SENTIMENT 원본 응답 |
| `get_global_news(date,lookback?,limit?)` | `news_data` | yfinance → alpha_vantage | 글로벌 뉴스. Yahoo 설정 쿼리 순회, AV는 고정 토픽 |
| `get_insider_transactions(ticker,date?)` | `news_data` | alpha_vantage → yfinance | 내부자 거래 또는 보류/자료 없음 안내 |
| `get_macro_indicators(indicator,date,lookback?)` | `macro_data` | fred | 단위·주기·최근치·기간 변화·최대 40개 관측 표 |
| `get_prediction_markets(topic,limit?,date?)` | `prediction_markets` | polymarket | 열려 있고 종료일이 미래인 시장의 첫 outcome 확률·거래량·종료일·1주 변화(pp) |

실행 기본 설정은 위의 `default` 등록 순서와 다르다. 기본은 가격·기술·뉴스 `yfinance`, 재무 `sec_edgar,yfinance`, 거시 `fred`, 예측시장 `polymarket`, 도구별 덮어쓰기는 빈 map이다. 개요·내부자 도구에는 SEC 구현이 없어 필터 후 Yahoo만 남는다. 내부자 도구의 카테고리는 이름과 달리 `fundamental_data`가 아닌 `news_data`다.

#### 벤더별 수집·가공·저장 경계

| 벤더 | 요청·데이터 / 키 | 가공·시간·캐시 |
|---|---|---|
| Yahoo | `Ticker.history`, `Ticker.info`, 재무 속성, `insider_transactions`, `get_news`, `Search`; 코드에서 API 키를 전달하지 않음 | 가격은 종목 정규화·10일 stale 검사. 지표/스냅샷은 오늘 기준 5년의 일봉을 별도 CSV 캐시에 저장 후 분석일 이하만 사용. 직접 가격 도구와 `get_closes`는 이 캐시를 안 거침 |
| Alpha Vantage | query endpoint, `ALPHA_VANTAGE_API_KEY` 필수, timeout 30초 | 공통 요청은 function·apikey·source를 붙여 응답 문자열을 유지. 자체 디스크 캐시·재시도 루프 없음. 가격 CSV와 지표는 로컬 기간 필터, 뉴스는 API 기간 인자. 과거 재무·개요·내부자는 공통 guard |
| SEC EDGAR | company_tickers와 companyfacts; 키 대신 `SEC_EDGAR_USER_AGENT` 또는 버전+placeholder 연락처를 전달, timeout 30초 | US ticker map→10자리 CIK, us-gaap facts. data_cache_dir/sec_edgar 아래 ticker map·CIK JSON을 24시간 캐시. 실제 SEC 수용 조건은 외부 미확인 |
| FRED | series와 series/observations, `FRED_API_KEY` 필수, timeout 30초 | 별칭 또는 raw ID, 기본 365일 창. 메타/관측 요청 모두 `realtime_start=end=min(분석일, Chicago 오늘)`. '.'/null/빈 값 제외. 자체 디스크 캐시·재시도 루프 없음 |
| Polymarket | Gamma public-search q=topic, limit_per_type=20; 키를 전달하지 않음, timeout 30초 | 과거 분석은 요청 전 보류. open/future/outcome 존재 필터→volumeNum 내림차순→기본 6개. 자체 디스크 캐시·재시도 루프 없음 |

Yahoo 개요의 필드/통화·비율 매핑은 C-12, SEC 표 항목·태그/기간 규칙은 C-20~C-22, 지표명·API 매핑은 C-09·C-17, 거시 별칭은 C-24를 원본으로 삼는다. 이 짧은 선언·매핑 목록을 글로 중복 전사하지 않는다. 가격은 quote 통화, Yahoo 기업소득은 financialCurrency, 시총/EPS는 주요 통화 단위로 표시하여 서로 같다고 가정하지 않는다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 메서드 요청 | C-01 등록 카테고리와 벤더 함수 선택. 미등록 메서드는 category 탐색에서 ValueError | 코드 확인 |
| R-02 | 벤더 설정 | 도구 설정이 카테고리보다 우선. 쉼표 split·strip, 빈/default를 뺀 명시 목록이 있으면 지원 벤더만 유지. 전부 미지원이면 ValueError. 명시 목록이 없을 때만 등록 전체 순서 사용 | 코드 확인 |
| R-03 | 벤더가 정상 반환 | 빈 문자열·보류 안내·오류 안내·null을 포함해 반환값 그대로 즉시 종료. '내용 없음' 문자열을 근거로 다음 벤더를 시도하지 않음 | 코드 확인 |
| R-04 | 호출 중 예외 | C-02 분기대로 장애·설정 누락·자료 없음·비정형 예외를 기록하고 다음 벤더 호출. 성공 전까지 첫 오류를 보존 | 코드 확인 |
| R-05 | 전부 실패 | unavailable 존재→DATA_UNAVAILABLE; 비정형 실패+no-data→DATA_UNAVAILABLE; no-data→NO_DATA_AVAILABLE; 그 외 첫 오류는 optional 2카테고리면 안내문, 핵심이면 raise. 아무 상태도 없으면 RuntimeError | 코드 확인 |
| R-06 | Yahoo 요청 실패·빈 응답 | rate limit만 최대 3회 재시도(2,4,8초). 기타 실패는 unavailable, 명시적 404/무가격 예외는 빈 응답으로 판정. 가격·개요 등의 빈 결과는 HEAD probe의 접속 가능 여부로 unavailable/no-data를 구분 | 코드 확인 |
| R-07 | Yahoo 직접 가격 또는 정산 종가 | 직접 가격은 요청 종료일+1일을 SDK end로 전달하고 CSV 반환 전 최신 봉이 요청일보다 10일 넘게 오래되면 no-data. 정산 `get_closes`는 end 제외 일봉 Close 시리즈 또는 빈 시리즈 반환(C-08) | 코드 확인 |
| R-08 | Yahoo 지표·스냅샷용 캐시 | C-07 기준으로 종목별 CSV, 동일 호스트 일자에 기록된 캐시만 사용. 현재/미래 요청은 900초 이내일 때만 재사용. 과거 요청도 오늘 다운로드한 5년 범위만 제공 가능하며 그 이후 행은 필터 | 코드 확인 |
| R-09 | 가격 정리·지표 계산 | 원시 날짜의 지역 달력일을 유지해 naive midnight 정규화. 지표는 Close 없는 행을 버리고 나머지 가격 결측 ffill/bfill; 스냅샷은 fill_gaps=False. 기준일 이후 행을 제거한 다음 계산·stale 검사. 지표명/출력/단일일 fallback은 C-09 | 코드 확인 |
| R-10 | 검증 스냅샷 | Yahoo 직접 경로, 기본 11개 지표·최근 1~30거래행. 값 없는 셀 N/A, 지표 하나 오류는 해당 셀 N/A(예외명), 전체 loader 오류는 도구가 typed 2종을 센티널로 바꿈. data_vendors/tool_vendors로 바뀌지 않음 | 코드 확인 |
| R-11 | Yahoo 개요·재무·내부자 | 공통 날짜 guard 후 요청. 개요는 사용 가능한 필드만, 하나도 없으면 no-data. 재무 표는 quarterly 문자열인 경우 분기 속성·그 외 연간 속성. 내부자 빈 결과는 host reachable이면 정상 부재 안내문. 종목 identity용 `get_company_profile`은 별도 raw info dict(빈 응답이면 빈 map)이며 날짜 guard를 거치지 않음 | 코드 확인 |
| R-12 | Yahoo 뉴스 | 종목 feed가 비면 Search로 같은 ticker 태그 기사만 사용. 응답·태그 부재는 unavailable. 기간 안 결과가 없으면 coverage 안내/부재 구분. 글로벌 쿼리는 날짜 필터→제목 중복제거→limit 순서이며 검색 한계를 감춘 부재 선언을 피함 | 코드 확인 |
| R-13 | Alpha Vantage 요청 | 키 없음/invalid key→not-configured, rate/premium 문구→unavailable, Error Message→unavailable. secret은 요청 예외와 API 문구에서 치환. CSV/비JSON/JSON 정상 원문은 문자열 반환. 자체 재시도 없음 | 코드 확인 |
| R-14 | Alpha Vantage 데이터 | 가격은 inclusive 기간 trim 실패를 삼키지 않음. 지표 미지원·일반 처리 실패는 no-data지만 일부 CSV 헤더/열 문제는 Error 문자열로 정상 반환. 뉴스 end는 23:59, 글로벌 토픽은 고정 3개. 재무 freq는 응답 필터에 쓰이지 않음 | 코드 확인 |
| R-15 | SEC 재무 | C-20~C-22. 공시일 이하 최신 수정본, 태그 순서 우선(합산하지 않음), 기간 폭·annual form 선별. 분기는 해당 분기 우선, 없으면 명시한 6/9개월 YTD, 임의 차감 Q4 생성 없음. USD million와 EPS 단위 구분, 기간별 행 | 코드 확인 |
| R-16 | FRED 거시 | C-24~C-25. 빈티지 pin 두 요청 공통 적용. 잘못된 별칭 문구 반환, metadata 없으면 문구. 빈 관측도 안내문. 표는 최근 40개여도 변화는 전체 창 최초→최후 | 코드 확인 |
| R-17 | Polymarket | C-26. 과거 보류·HTTP RequestException은 문구 반환. open/future 결과를 거래량순 선택하고 첫 outcome 확률을 표시. JSON 구조·기타 오류는 자체 포괄 catch가 없어서 router의 optional 처리로 이동 | 코드 확인 |
| R-18 | 캐시 기록 | 고유 임시파일→os.replace. PermissionError이면 임시파일 제거·기존 캐시 보존 후 계속. 다른 쓰기 오류는 제거 후 raise. Yahoo는 캐시 CSV read 오류를 포괄 catch하지 않음; SEC는 JSON ValueError만 cache miss | 코드 확인 |

- 불변식: 명시적으로 선택하지 않은 벤더는 자동 추가되지 않는다. 반환값의 데이터 부재 의미는 폴백 조건이 아니며 예외만 폴백한다.
- 미결정: 없음. 설정·기준일 제한·실행 입력 선행 스펙은 ready다.
- 확인 한계: 모든 규칙은 클라이언트 코드 확인. 외부 API 실제 응답·가용 범위·stockstats 계산 내부 기본값은 미확인. Yahoo 오늘 기준 조정 가격을 과거일로 잘라도 당시 조정 전 빈티지를 복원하지는 않는다. 상한 필터와 과거 데이터 실제 완전성은 다르다.

### 1.5 필수 코드 참조

원본 SHA는 frontmatter와 같다. 외부 라이브러리 경계는 1.2, 종목·설정·날짜 helper는 선행 스펙으로 닫는다. 아래 C-ID는 해당 벤더의 실제 가공·포맷·오류를 빠뜨리지 않도록 함수 단위로 제공한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/dataflows/router.py:44-173` 등록 상수, `get_category_for_method`, `get_vendor` | 카테고리·메서드·벤더 매핑과 설정 우선순위 | R-01, R-02 |
| C-02 | `tradingagents/dataflows/router.py:176-297` 센티널 함수, `route_to_vendor` | 전달·폴백·최종 실패·정확한 안내문 | R-02~R-05 |
| C-03 | `tradingagents/dataflows/errors.py:21-58` 오류 계층 | 세 행동 분기·symbol/canonical/detail 필드 | R-04, R-05 |
| C-04 | `tradingagents/dataflows/net.py:6-37` HTTP helper | raise_for_status, secret 치환, HEAD probe(상태코드보다 접속 성공 판정) | R-06, R-13 |
| C-05 | `tradingagents/dataflows/files.py:14-33` `replace_file` | 고유 temp·replace·실패 정리 | R-18 |
| C-06 | `tradingagents/dataflows/vendors/yahoo/common.py:16-91` 상수·가격포맷·빈응답·재시도 | 가격 precision·예외 분류·retry와 YAHOO_HOST | R-06, R-07, R-11 |
| C-07 | `tradingagents/dataflows/vendors/yahoo/ohlcv.py:15-257` 캐시 상수·정리 helper·`load_ohlcv` | 10일·900초·5년 캐시와 날짜/결측 처리 전체 | R-07~R-09, R-18 |
| C-08 | `tradingagents/dataflows/vendors/yahoo/market.py:18-63,266-270` 가격·종가 요청 | inclusive 도구와 exclusive 정산 호출 차이, CSV | R-07 |
| C-09 | `tradingagents/dataflows/vendors/yahoo/market.py:66-263,273-294` 지표 window·bulk·일별 helper | 13개 허용명·설명·캘린더 역순 출력·fallback·stockstats 요청 | R-09 |
| C-10 | `tradingagents/dataflows/vendors/yahoo/snapshot.py:23-128` 지표상수·row·format·snapshot | 11개 기본 지표·원시 셀·최근 행·포맷 | R-10 |
| C-11 | `tradingagents/agents/tools.py:73-94` `get_verified_market_snapshot` | 라우터 우회와 typed 오류 변환 | R-10 |
| C-12 | `tradingagents/dataflows/vendors/yahoo/fundamentals.py:19-118` `_MAIN_UNIT`, 개요·공통 재무 | 필드명·가격/보고/주요통화·비율 단위·누락·재무 guard | R-11 |
| C-13 | `tradingagents/dataflows/vendors/yahoo/fundamentals.py:121-171` 제표별 wrapper·내부자 | SDK 속성·빈 내부자 응답·raw 회사 profile | R-11 |
| C-14 | `tradingagents/dataflows/vendors/yahoo/news.py:16-201` extract/search/format·뉴스 2종 | 두 입력 포맷·일시 파싱·태그·검색·dedup·출력·coverage | R-12 |
| C-15 | `tradingagents/dataflows/vendors/alpha_vantage/common.py:11-134` API 상수·키·시간·공통요청 | 키·timeout·notice 분류·scrub·endpoint·source | R-13, R-14 |
| C-16 | `tradingagents/dataflows/vendors/alpha_vantage/common.py:137-166`; `tradingagents/dataflows/vendors/alpha_vantage/stock.py:9-42` | inclusive CSV 필터·compact/full(시작일이 현시점 100일 이내인지) | R-14 |
| C-17 | `tradingagents/dataflows/vendors/alpha_vantage/indicator.py:9-219` `get_indicator` | 지표 API·파라미터·CSV column·범위·오류 분기 | R-14 |
| C-18 | `tradingagents/dataflows/vendors/alpha_vantage/fundamentals.py:5-53` 개요·재무 wrapper | guard와 OVERVIEW/BALANCE_SHEET/CASH_FLOW/INCOME_STATEMENT | R-14 |
| C-19 | `tradingagents/dataflows/vendors/alpha_vantage/news.py:10-89` 종목/글로벌·내부자 | NEWS_SENTIMENT 토픽·limit·시간, INSIDER_TRANSACTIONS | R-14 |
| C-20 | `tradingagents/dataflows/vendors/sec_edgar.py:37-143` 상수·태그·UA·fetch/cache·CIK | URL·항목·기간/form 상수·24h cache·typed 실패 | R-15, R-18 |
| C-21 | `tradingagents/dataflows/vendors/sec_edgar.py:146-188` `_span_index`, `_as_of` | 기간 폭·공시 cutoff·수정본·태그·단위 선별 | R-15 |
| C-22 | `tradingagents/dataflows/vendors/sec_edgar.py:191-270` statement·million·공개 wrappers | YTD·열/행·단위·소액 precision·제표 호출 | R-15 |
| C-23 | `tradingagents/default_config.py:138-171` 뉴스·벤더 기본값 | 기사 개수·검색 목록·기본 체인·도구 덮어쓰기 | R-02, R-12, R-14 |
| C-24 | `tradingagents/dataflows/vendors/fred.py:22-164` 상수·별칭·키·resolve·today·request | ID mapping·오류·30초·Chicago·HTTP400 body | R-16 |
| C-25 | `tradingagents/dataflows/vendors/fred.py:167-286` `get_macro_data` | 365일·빈티지·metadata/observation·결측·요약·40행 | R-16 |
| C-26 | `tradingagents/dataflows/vendors/polymarket.py:23-165` 상수·request·parse·필터·확률포맷·공개함수 | 6개·20개 검색·open/future·거래량·확률 precision·예외 | R-17 |

| C-27 | `tradingagents/__init__.py:3-3` `__version__` | SEC 기본 User-Agent에 넣는 패키지 버전 | R-15 |

C-08·C-09는 표시한 두 범위를 모두 필수로 읽는다. stockstats 허용명에는 Yahoo `mfi`가 있지만 AV에는 없고, AV `vwma`는 목록에 있어도 실제 endpoint 분기가 없어 no-data가 된다. 기본 스냅샷에는 vwma/mfi가 없다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. 벤더 응답·시계·파일시스템을 제어하는 사례이며 실제 API/SDK 실행 결과를 주장하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | category=yfinance, tool=alpha_vantage | AV만 호출. 실패해도 Yahoo 자동 추가 안 됨 |
| T-02 | R-02 | `get_fundamentals`, chain=`sec_edgar,yfinance` | 지원하지 않는 SEC 제거 후 Yahoo 호출 |
| T-03 | R-02 | chain=`unknown,default` | 명시 unknown만 남아 지원 목록 공집합 → ValueError |
| T-04 | R-03 | 첫 vendor가 보류 문구 또는 빈 문자열 | 그 값 반환, 다음 vendor 호출 0회 |
| T-05 | R-04, R-05 | 첫 vendor unavailable, 둘째 no-data | DATA_UNAVAILABLE. 종목 자체 무자료로 단정하지 않음 |
| T-06 | R-05 | 키 누락 + no-data | NO_DATA_AVAILABLE. 비정형 일반 오류 + no-data이면 DATA_UNAVAILABLE |
| T-07 | R-05 | 일반 예외만 발생, category news_data vs macro_data | news_data는 최초 오류 raise, macro_data는 optional DATA_UNAVAILABLE |
| T-08 | R-06 | Yahoo rate limit 4번 연속 | 2·4·8초 후 4번째 시도까지 수행하고 unavailable |
| T-09 | R-07 | requested 최신행 차이=10일 vs 11일 | 10일 허용, 11일 NoMarketDataError |
| T-10 | R-08 | 오늘 쓴 cache, 과거 요청 vs 현일 요청, age=901초 | 과거 요청 재사용, 현일 요청 refetch |
| T-11 | R-09 | 최신행 Close=null이고 이전행 Close 존재 | 최신 무종가행 제거. 지표는 나머지 결측 보충, snapshot은 원시 결측 유지 |
| T-12 | R-10 | snapshot indicator 하나 계산 오류 | 해당 값 N/A(예외명), 다른 값·OHLCV 출력 계속 |
| T-13 | R-11 | 과거일, 재무 체인=`yfinance,sec_edgar` | Yahoo 보류 문구 반환 후 종료. SEC로 넘어가지 않음 |
| T-14 | R-12 | 글로벌 검색에 기간 밖 기사와 제목 중복 | 기간 밖 결과는 limit 소모하지 않고 중복 제목 한 번만 포함 |
| T-15 | R-13, R-14 | AV response Error Message 또는 indicator CSV time 열 없음 | 전자는 unavailable→폴백 가능, 후자는 Error 문자열→폴백 종료 |
| T-16 | R-15 | 사실 A 공시일 7/1, 수정 A 8/1, as_of=7/15 | 7/1 값 선택. 회사가 SEC map에 없으면 no-data→설정된 다음 벤더 |
| T-17 | R-16 | 지역 분석일이 Chicago 오늘보다 하루 앞, 관측>40 | 빈티지는 Chicago 오늘, 표 최근40·변화는 전체 창 |
| T-18 | R-17 | 과거일 또는 HTTP RequestException | 과거는 요청 0회 보류, HTTP 오류는 사용불가 문구 정상 반환 |
| T-19 | R-18 | 임시파일 쓰기 후 os.replace PermissionError | temp 제거·기존 파일 보존·경고. 일반 OSError면 temp 제거 후 오류 전파 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01~R-05 / T-01~T-07 | C-01~C-03, C-23 | 등록 순서·if 분기·정상 즉시 return·최종 예외 우선순위 직접 읽음 |
| R-06 / T-08 | C-04, C-06 | retry 횟수·지연 공식·예외 분류·probe 구현 직접 읽음. 외부 SDK 의미는 클라이언트 가정 |
| R-07~R-10 / T-09~T-12 | C-07~C-11 | cache age·가격/지표·snapshot 경로 직접 읽음. stockstats 내부 기본 파라미터 수치는 확정하지 않음 |
| R-11 / T-13 | C-12, C-13, point-in-time C-03 | guard가 API 호출 전 문자열을 돌려주는 것과 router 정상 return 결합 확인 |
| R-12 / T-14 | C-14, C-23 | 추출·태그·기간·dedup·limit와 coverage 분기 확인 |
| R-13~R-14 / T-15 | C-15~C-19 | 응답 notice·HTTP error scrub·CSV 파싱 경계·문자열 오류 반환 확인 |
| R-15 / T-16 | C-20~C-22 | 공시일·수정본·태그/기간·가공 직접 확인. 실제 SEC facts coverage와 기본 UA 수용 여부 미확인 |
| R-16 / T-17 | C-24, C-25 | realtime pin·요청 인자·관측/표 규칙 직접 확인. 실제 ALFRED 값 보증 미확인 |
| R-17 / T-18 | C-26 | public-search 요청·본문·catch 범위 직접 읽음. 서버 API 의미는 클라이언트 가정 |
| R-18 / T-19 | C-05, C-07, C-20 | cache read 예외 범위·고유 temp·PermissionError 분기 직접 읽음 |

### 2.2 코드 읽는 순서

라우터 등록·실행 분기 → 현재 설정 → 오류 계층 → 실제 선택 벤더 공개 함수 → 그 함수가 사용하는 helper·상수 순서로 읽는다. 도구 전체를 Yahoo 대체 어댑터 하나로 이해하지 않는다. 검증 스냅샷과 정산 종가·소셜은 각각 별도 진입 경계다.

## 적용 메모

분석자 의견: 원본 미국주식 경로는 유지한다. 한국 소스를 추가하려면 다음은 서로 다른 교체 지점이다.

| 관련 R-ID | 교체 검토 지점 | 이유·영향 |
|---|---|---|
| R-01~R-05 | 새 vendor 함수와 등록·카테고리/도구 설정 | 기존 호출 인자·문자열 반환·세 예외 행동을 유지하면 기존 판단 입력에 연결할 수 있음. 키움/DART의 실제 API 계약은 이번 조사에서 확정하지 않음 |
| R-10 | Yahoo 고정 snapshot 경로 | router 등록만 바꾸면 snapshot은 Yahoo를 계속 사용하므로 별도 provider 경계가 필요 |
| R-15 | SEC의 CIK·US-GAAP·USD/공시일·기간 태그 | 국내 재무는 데이터 공급자만 바꾸어도 동일한 표 의미가 자동 보장되지 않음 |
| R-12, R-16, R-17 | 글로벌 뉴스 쿼리·FRED 별칭·예측시장 커버리지 | 대상 시장별 적합성은 설정/데이터 선택 문제. 미국 소스를 제거할 이유는 없음 |
| R-07~R-09 | Yahoo 종목 식별·조정가격·거래일·통화 | .KS/.KQ 사용 가능성과 실제 국내 데이터 품질·범위는 다르므로 어댑터별 사례가 필요 |

원본 코드 재사용의 라이선스 기준은 overview 1절 Apache-2.0이다. 위 표는 설계 의견이며 원본 스펙의 동작을 변경하지 않는다.
