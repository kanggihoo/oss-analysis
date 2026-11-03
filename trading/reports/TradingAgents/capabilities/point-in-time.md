---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/dataflows/date_window.py
  - tradingagents/agents/tools.py
depends:
  - run-state.md
status: ready
---

# 분석 기준일 제한

> 그래프가 제공한 분석일과 도구가 요청한 날짜·기간을 받아, 벤더에 전달할 시점을 제한하고 과거 값을 증명할 수 없는 자료를 보류한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 실행 상태의 `company_of_interest`와 `trade_date`를 도구 호출에 주입한다. 모델이 이 두 값을 직접 정하지 않는다.
2. 단일 날짜는 `as_of`, 기간은 `as_of_window`로 제한한다.
3. 기간이 잘못되면 가격·종목 뉴스 도구는 오류 문구를 데이터 반환값으로 돌려주고 벤더를 호출하지 않는다.
4. 날짜가 붙은 자료는 UTC 기준 창으로 선별한다. 관측하지 못한 과거 기간은 자료 부재와 구별한다.
5. 공개 당시 값을 제공하지 못하는 회사 개요·재무제표·내부자 거래는 과거 분석에서 안내문으로 대체한다.
6. SEC 공시일 선별, FRED 빈티지 요청, Polymarket 과거 보류 같은 벤더별 추가 처리는 [벤더 라우팅](vendor-routing.md)의 경계다.

### 1.2 범위·통합 지점

- 제공: 공통 날짜 변환·기간 필터와 도구의 기준일 전달 규약.
- 제외: 벤더의 실제 과거 보관 범위·SDK 시간 의미·모든 데이터의 과거 정합성 보증. 공시·거시·가격 조정 이력의 실제 값은 벤더 구현과 외부 응답에 달린다.
- 선행: [실행 상태](run-state.md). 그래프 경로의 `trade_date`는 정규 `YYYY-MM-DD`이고 미래가 아니어야 한다. 직접 함수를 호출할 때의 빈 `trade_date`는 별도 규약이다.
- 소유 상태·부작용: 날짜 유틸은 파일·네트워크를 변경하지 않는다. `today`는 호스트 지역일, 기사 필터·커버리지는 UTC 현재시각을 읽으므로 결과는 시계에 따라 달라질 수 있다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `as_of(requested, trade_date)` | optional string, string → optional string | 요청일이 유효하고 기준일 이하이면 정규 날짜. 나머지는 기준일. 기준일이 비면 파싱 가능한 요청일만 정규화하고 잘못된 값·null은 그대로 반환 |
| `as_of_window(start_date, end_date, trade_date)` | string 3개 → (string, optional string) | 양끝을 포함하는 날짜 창. 시작일 파싱 실패·시작일>원래 종료일은 ValueError. 종료일 제한 뒤 창 전체가 미래이면 원래 길이를 유지해 뒤로 이동 |
| `to_utc(dt)` | datetime → UTC-aware datetime | naive 시각은 UTC로 간주. aware 시각은 UTC로 변환 |
| `in_window(pub_dt, start_dt, end_dt)` | optional datetime, datetime 2개 → bool | `[start, end+1일)`의 반개구간. `pub_dt=null`은 종료시각이 UTC 현재시각−1일 이상이면 보존 |
| `coverage_gap(dates,start_date,end_date,source,subject)` | iterable optional datetime 등 → optional string | 종료일이 UTC 오늘 이후이거나 관측 최저일이 시작일보다 늦으면 unavailable 안내문. 아니면 null. 빈 dates의 관측 최저일은 UTC 현재시각 |
| `is_historical(run_date)` | optional 값 → bool | 값이 있고 문자열이 호스트 지역 오늘보다 작으면 true. 내부에서 날짜 형식 검증하지 않음 |
| `withhold_live_profile`, `withhold_undisclosed_trades`, `withhold_undated_statements` | optional 기준일·레이블 등 → optional string | 과거면 각 보류 안내문, 아니면 null. 벤더 호출부는 안내문이 있으면 네트워크 호출 전에 반환 |
| 날짜를 쓰는 도구 | 상태 주입 + 모델 인자 → string | 도구 인자·기본값·실제 전달 순서는 C-04~C-06. 단일 기준일/기간을 받지 않는 내부자·예측시장 도구도 상태 기준일을 전달 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 그래프에서 분석 도구 호출 | 종목 관련 도구의 종목과 모든 도구의 분석 기준일을 상태에서 주입한다. 모델이 요청하는 날짜와 주입 기준일을 구분한다 | 코드 확인 |
| R-02 | 단일 날짜 요청 | `as_of`의 정규화·상한 분기(C-01)를 적용. 빈 기준일 직접 호출은 상한 보증 대상이 아니다 | 코드 확인 |
| R-03 | 기간 요청 | `as_of_window`의 파싱·역전 거부·상한·기간 이동(C-01)을 적용. 가격·종목 뉴스 도구는 ValueError 문구를 반환하고 벤더 호출을 건너뛴다 | 코드 확인 |
| R-04 | 지표·스냅샷·개요·재무·글로벌 뉴스·거시 도구 호출 | 단일 날짜를 제한한 뒤 벤더에 전달한다. 지표는 쉼표 분리 후 각 지표의 ValueError를 문구로 흡수하며 나머지를 계속 처리한다 | 코드 확인 |
| R-05 | 내부자·예측시장 도구 호출 | 주입 `trade_date` 또는 null을 전달한다. 모델이 별도 날짜를 지정하지 않는다 | 코드 확인 |
| R-06 | 시각이 있는 기사·게시물 | C-02의 UTC 변환과 반개구간 판정. 종료일 다음 자정의 자료는 제외한다. 시각 없는 자료는 종료일이 현재에 가까운 경우만 남는다 | 코드 확인 |
| R-07 | 뉴스·소셜 feed가 요청 기간을 관측하지 못함 | `coverage_gap`은 관측 부족을 unavailable 안내로 표현한다. 과거 빈 결과가 곧 '그때 뉴스 없음'이라는 결론은 아니다 | 코드 확인 |
| R-08 | 과거일의 현시점 개요·공시일 없는 재무·내부자 데이터 | C-03의 보류 안내문. 과거 여부는 지역 오늘과 문자열로 비교하므로 상위에서 정규 날짜를 제공해야 한다 | 코드 확인 |
| R-09 | 날짜 guard의 반환이 정상 문자열 | 이것은 데이터 유효성이나 빈티지의 실제 보증이 아니다. 도구·벤더 호출 여부·필터 규약만 보장한다 | 코드 확인 |

- 불변식: 정규·유효한 `trade_date`가 있는 `as_of` 결과는 그 날짜보다 늦지 않다. 기간 제한은 기준일 검증 및 유효한 시작일을 전제로 한다.
- 미결정: 없음. 선행 실행 상태 스펙은 ready다.
- 확인 한계: 실제 API 응답·라이브러리 실행 미검증. naive→UTC는 원본의 가정이며 실제 원천 시각대가 UTC라는 외부 보증은 아니다. 날짜 제한은 현재 다운로드한 조정 가격의 과거 개정까지 되돌리지는 않는다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/dataflows/date_window.py:72-111` `_parse`, `as_of`, `as_of_window` | 날짜 파싱·정규화·기간 이동·오류 문구 전체 | R-02, R-03 |
| C-02 | `tradingagents/dataflows/date_window.py:19-69` `to_utc`, `in_window`, `get_current_date`, `is_historical`, `coverage_gap` | 두 시계 기준·반개구간·coverage 안내 | R-06, R-07, R-08 |
| C-03 | `tradingagents/dataflows/date_window.py:114-176` `withhold_*` | 세 종류 과거 보류 문구와 조건(C-02 사용) | R-08 |
| C-04 | `tradingagents/agents/tools.py:18-94` `get_stock_data`, `get_indicators`, `get_verified_market_snapshot` | InjectedState·날짜·지표 split·ValueError·typed 예외 변환 | R-01~R-04 |
| C-05 | `tradingagents/agents/tools.py:97-229` 재무·종목/글로벌 뉴스·내부자 도구 | 실제 공개 인자·기본값·벤더 인자 순서·기간 오류 문구 | R-01, R-03~R-05 |
| C-06 | `tradingagents/agents/tools.py:232-291` `get_macro_indicators`, `get_prediction_markets` | 거시·예측시장 시점 전달 | R-01, R-04, R-05 |

C-04~C-06의 데이터 요청은 표준 경계다. 라우터는 `route_to_vendor(method,*args,**kwargs)`로 성공 문자열 또는 예외를 주고, 스냅샷 로더는 문자열 또는 두 typed 오류(NoMarketDataError/VendorUnavailableError)를 준다. 여기서는 그 요청의 내부 처리를 재구현하지 않는다. 공통 guard만 먼저 구현 가능하도록 `depends`에 벤더 스펙을 넣지 않는다. 반환 문자열/예외의 추가 분기는 소비 기능이 소유한다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. 시계·벤더·도구 decorator는 대체 경계로 두며 실제 네트워크 및 LangGraph 실행을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `as_of('2026-7-3','2026-07-23')` | `2026-07-03` |
| T-02 | R-02 | 요청일 null/잘못된 날짜/기준일보다 늦은 날짜, 기준일 `2026-07-23` | 기준일 반환 |
| T-03 | R-02 | `trade_date=''`, requested='bad' | `bad` 그대로; 전역 상한 보장 없음 |
| T-04 | R-03 | `as_of_window('2026-08-01','2026-08-11','2026-07-23')` | `('2026-07-13','2026-07-23')` |
| T-05 | R-03 | 시작일>종료일 또는 시작일 파싱 불가로 가격/뉴스 도구 호출 | 오류 문구 반환, 벤더 호출 0회 |
| T-06 | R-04 | 지표 `'rsi, bad, macd'`, bad의 vendor가 ValueError | 각 지표 처리 순서 유지, bad 문구와 나머지 결과를 줄바꿈 join |
| T-07 | R-06 | start=2026-07-01 00:00 UTC, end=2026-07-03 00:00 UTC, pub=2026-07-04 00:00 UTC | 제외 |
| T-08 | R-06 | pub=null, 고정 UTC now=2026-07-04 12:00, end=2026-07-03 00:00 | 제외(정확한 24시간 비교이며 단순 전일 날짜 비교가 아님) |
| T-09 | R-07 | 과거 기간·dates 빈 목록 | 현재시각을 최저일로 사용해 'recent items' unavailable 안내 |
| T-10 | R-08 | 지역 오늘 2026-07-24, as_of=2026-07-23 | 세 withhold 함수가 각각 보류 문구 반환 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-04, R-05 / T-06 | C-04~C-06 | InjectedState 선언·본문의 전달값 정적 확인. 런타임 decorator 동작은 실행 미검증 |
| R-02, R-03 / T-01~T-05 | C-01, C-04, C-05 | 파싱·분기·날짜 계산과 호출자 예외 처리를 직접 읽음 |
| R-06, R-07 / T-07~T-09 | C-02 | datetime.now(UTC), min 날짜와 부등호 직접 읽음 |
| R-08 / T-10 | C-02, C-03 | 지역일·문자열 비교·반환문 확인 |
| R-09 | C-01~C-06 | 함수가 수행하는 것은 입력 제한·필터·안내 반환. 원천 이력을 복원하는 연산은 이 범위에 없음 |

## 적용 메모

분석자 의견: 미국/한국 소스를 병행하더라도 '관측일'과 '공개일'을 별도 취급하는 경계를 보존한다. 날짜만 보존한 국내 데이터로 과거 분석이 안전하다고 가정하지 않는다. 원본 guard 동작은 여기서 바꾸지 않는다.
