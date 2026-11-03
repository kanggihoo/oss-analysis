---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/graph/trading_graph.py
  - tradingagents/agents/context.py
  - tradingagents/portfolio.py
  - tradingagents/dataflows/symbols.py
  - tradingagents/dataflows/date_window.py
  - tradingagents/dataflows/vendors/yahoo/fundamentals.py
depends:
  - configuration.md
  - run-state.md
status: ready
---

# 종목·보유 현황 입력

> 기준일을 검증하고 종목 식별 정보와 선택적 보유 현황을 공통 실행 상태에 조립한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자가 company_name·trade_date·asset_type과 optional PortfolioContext를 전달한다.
2. 기준일이 오늘 이하의 정규 YYYY-MM-DD인지 검증한다.
3. Yahoo profile에서 현재 종목 식별 정보를 얻고 실패하면 빈 identity로 계속한다.
4. 정확한 원본 종목 문자열과 자산 유형·식별 정보를 prompt 문맥으로 만든다.
5. 포트폴리오가 제공되면 해당 종목의 모든 일치 포지션·현금·다른 포지션을 렌더링한다.
6. S1 초기 상태를 만들고 이후 단계에서 문맥 helper를 통해 읽는다.

### 1.2 범위·통합 지점

- 제공: 날짜 검증·종목 정규화·파일명 안전성·식별 문맥·보유 JSON/렌더/fingerprint·초기화 연결.
- 제외: 데이터 수집 도구의 기준일 보정·수집 결과는 별도 기능. 브로커 계좌 조회·환전·주문·포지션 합산은 제공하지 않는다.
- 외부 의존: profile(ticker)는 longName/shortName/sector/industry/exchange/quoteType map 또는 예외를 제공한다. 원본은 Yahoo normalize_symbol→yf_retry→Ticker.info 경로를 호출한다. yf_retry 내부는 데이터 수집 스펙 소유이며 이 기능은 모든 조회 예외를 빈 identity로 처리한다.
- 소유 상태: identity의 프로세스 LRU256(성공 반환값 캐시), caller 소유 PortfolioContext, 생성된 문맥 문자열·초기 상태. 계좌 잔고 변경 없음.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| propagate/create_run_state | company_name:string, trade_date:any, asset_type:string="stock", portfolio:optional PortfolioContext | API는 asset_type 문자열을 별도 enum 검증하지 않음. crypto와 정확히 같을 때 암호자산 문맥 |
| 날짜 | str(trade_date) → YYYY-MM-DD | 오늘은 호스트 로컬 날짜. 정규 문자열과 정확 비교; 미래일·비정규/불가 날짜는 ValueError |
| 종목 | 원본 company_name / normalize_symbol(raw) | state company_of_interest는 원문. 데이터·보유 매칭에서 Yahoo 정규화. 정규화가 실재 종목 존재를 확인하지는 않음 |
| 보유 JSON | cash:optional number, currency:optional string, positions:list(default[]) | Position: ticker:string, quantity:number(음수 숏), average_price:optional number. 모델이 NaN/Inf 거부. 빈 book과 미제공은 다름 |
| render/fingerprint | ticker→string / ()→string | 일치 포지션은 각각 표시, 합산하지 않음; fingerprint는 model_dump_json의 SHA256 앞12자리. 원본 필드·순서 차이로 fingerprint 달라질 수 있음 |
| get_instrument_context_from_state | state→string | 비어 있지 않은 string 문맥 우선. 없으면 ticker-only 설명을 만들고 네트워크를 재호출하지 않음 |
| get_portfolio_context_from_state | state→string | 비어 있지 않은 string 문맥 우선, 없으면 보유/현금 미제공 안내문. 현금0으로 추정하지 말라는 지시 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 기준일 입력 | C-01대로 정규 문자열 여부와 로컬 오늘 초과 여부를 검증한다. S1 생성자 자체는 이 검증을 하지 않으므로 공개 graph 입력 경계에서 수행한다. | 코드 확인 |
| R-02 | 종목 정규화·파일명 | C-02의 상수·별칭·crypto/forex/HK/Shanghai 순서로 정규화한다. safe_ticker_component는 별도이며 정규화를 하지 않고 비어있음·길이32 초과·금지 문자·점만 있는 값을 ValueError로 거부한다. | 코드 확인 |
| R-03 | 종목 identity | profile 정상값을 C-03대로 정제·선택해 LRU256 캐시. 조회 예외는 resolve 함수가 잡아 빈 map을 반환하며 실패 예외는 캐시에 저장되지 않는다. 정상 빈 profile/빈 identity는 캐시될 수 있다. | 코드 확인 |
| R-04 | 과거/현재 문맥 | 과거일은 현재 회사명만 식별 목적으로 넣고 당시 이름이 다를 수 있음을 명시한다. 현재 sector/industry/exchange는 과거 문맥에서 제외한다. 현재일 문맥은 제공된 분류·거래소를 넣는다. crypto는 기업 재무를 가정하지 않도록 지시한다. | 코드 확인 |
| R-05 | 보유 파일·값 | load_portfolio가 I/O·JSON 파싱·schema ValidationError를 path 포함 ValueError로 변환한다. 필수 quantity·ticker와 숫자 유효성은 C-04 모델을 따른다. cash/quantity의 음수나 average_price의 양수 제약을 새로 추가하지 않는다. | 코드 확인 |
| R-06 | 보유 렌더링·동일 종목 | normalize_symbol 기준으로 일치 포지션 전부 표시하고 다른 포지션은 제외하여 별도 나열한다. 원본 ticker 저장값을 바꾸거나 일치 목록을 하나로 합산하지 않는다. position_in은 첫 일치만 반환한다. | 코드 확인 |
| R-07 | 없음/빈 book·helper | portfolio=None이면 상태 문맥은 빈 문자열. 빈 객체면 해당 종목 미보유 문맥이 생긴다. 상태 helper는 빈 문맥이면 미제공 안내문으로 대체하되 종목 fallback에서 네트워크를 추가 호출하지 않는다. | 코드 확인 |
| R-08 | 초기 상태·fingerprint | C-06은 검증한 날짜와 조립한 문맥을 S1으로 전달한다. fingerprint는 포트폴리오 모델 JSON 직렬화 그대로 해시하며 동등한 경제 노출을 정규화한 해시가 아니다. | 코드 확인 |

- 미결정: 없음(선언한 범위의 원본 경계).
- 확인 한계: 외부 API·모델·LangGraph를 실행하지 않았다. 아래 사례는 구현에서 도출했으며 테스트 실행 결과가 아니다.

### 1.5 필수 코드 참조

기준은 frontmatter의 SHA이며 원본 레포 루트 상대 경로다. C-ID가 지시하는 표·포맷·분기·알고리즘은 해당 범위를 함께 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/graph/trading_graph.py:30-41` · _validate_trade_date; `tradingagents/dataflows/date_window.py:35-42` · get_current_date·is_historical | 정규 YYYY-MM-DD와 로컬 오늘 | R-01, R-04 |
| C-02 | `tradingagents/dataflows/symbols.py:31-180` · 모든 별칭/상수·crypto_base·normalize_symbol·safe_ticker_component | 정규화 helper·정규식 포함 완결 범위 | R-02, R-06 |
| C-03 | `tradingagents/agents/context.py:51-169` · 정제·resolve·_identity·build_instrument_context; `tradingagents/dataflows/vendors/yahoo/fundamentals.py:169-171` · get_company_profile | profile 조회는 정의한 외부 경계. 정규화 C-02, 시계 C-01 | R-03, R-04 |
| C-04 | `tradingagents/portfolio.py:25-81` · Position·PortfolioContext·load_portfolio | 보유 모델·모든 메서드·loader. normalize_symbol C-02 | R-05, R-06, R-08 |
| C-05 | `tradingagents/agents/context.py:172-187,204-218` · 문맥 읽기 helper | build_instrument_context C-03. 포트폴리오 미제공 지시 | R-07 |
| C-06 | `tradingagents/graph/trading_graph.py:117-128,292-306` · resolve_instrument_context·create_run_state | 초기 상태 주입. _validate C-01·context C-03·portfolio C-04·S1 생성자 | R-07, R-08 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 모델·SDK·네트워크는 정상/오류를 반환하는 대체물로 가정하며 실제 서비스 호환성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 2026-7-3 또는 로컬 오늘 이후 날짜 | ValueError, 종목 조회 이전에 거부 |
| T-02 | R-02 | BTCUSDT, 700.HK, 600519.SH 정규화 | BTC-USD, 0700.HK, 600519.SS |
| T-03 | R-02 | safe_ticker_component("../AAPL") / ".." | 모두 ValueError |
| T-04 | R-03 | profile이 예외 후 다음번 정상 반환 | 첫 요청 ticker-only로 진행, 다음 요청 재조회 가능 |
| T-05 | R-04 | 과거일·현재명/sector/exchange 제공 | 현재명 주의문만 사용; 현재 분류·거래소 생략 |
| T-06 | R-05 | 파일 JSON 오류 또는 quantity=NaN | path 포함 ValueError |
| T-07 | R-06 | 포지션 BTCUSDT와 BTC-USD 2개 | 둘 다 동일 분석 종목 아래 별도 표시, 합산 안 함 |
| T-08 | R-07 | portfolio=None / PortfolioContext(positions=[]) | 전자는 미제공, 후자는 미보유 문맥 |
| T-09 | R-08 | 같은 경제 노출이지만 positions 순서만 다름 | 원본 JSON 순서가 달라 fingerprint도 달라질 수 있음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-04 | C-01 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-02, R-06 | C-02 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-03, R-04 | C-03 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-05, R-06, R-08 | C-04 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-07 | C-05 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-07, R-08 | C-06 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |

## 적용 메모

의견: 국내 종목 코드를 Yahoo 표기로 바꾸는 계층과 키움 표기로 바꾸는 계층을 분리할 후보가 있다. 원본 .KS/.KQ 입력 지원과 국내 공시·수급 데이터의 충분성은 별개이며 이 문서는 후자를 보장하지 않는다.
