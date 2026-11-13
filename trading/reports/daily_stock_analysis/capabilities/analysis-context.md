---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/core/pipeline.py
  - src/storage.py
  - src/stock_analyzer.py
  - src/schemas/decision_scale.py
  - data_provider/realtime_types.py
  - src/services/daily_market_context.py
  - src/config.py
  - src/core/trading_calendar.py
  - src/search_service.py
  - src/report_language.py
depends:
  - data-collection.md
status: ready
---

# 분석 컨텍스트 조립

> 수집된 일봉·실시간·추세·기본면과 시장 정보를 합쳐 판단기의 입력 map을 만든다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. DB에서 종목의 최신 두 일봉으로 분석 context를 만들고, 별도로 최대 89일 범위 이력으로 trend를 계산한다.
2. 비어 있고 JP/KR/TW면 일봉 60개 요청을 시도하고 저장·재조회 또는 메모리에서 마지막 두 행을 변환한다.
3. 결과가 `None`이면 해당 시장 현재 날짜와 빈 일봉을 가진 결측 context를 만든다.
4. 실시간 quote·chip·trend·fundamental과 이름 등을 얕은 복사본에 붙인다.
5. 조건이 맞으면 실시간 가격과 추세 MA로 `today`를 대체하고 파생 비율을 갱신한다.
6. phase, 일일 시장 요약, portfolio 및 시장 구조를 추가해 판단기에 전달한다.

### 1.2 범위·통합 지점

- 제공: 판단 경로가 공유하는 입력 map과 일봉 부재 시 시장별 보완.
- 제외: 데이터 제공자 수집 자체는 선행 스펙, 뉴스는 research, 판단과 후처리는 각 별도 스펙이다. Agent 경로의 조립 호출 위치는 별도 경로다.
- 외부 의존·선행 계약: [data-collection](data-collection.md)의 DB 일봉, quote, chip, fundamental 및 시장 식별·시계. trend 계산은 이 기능이 소유한다. DB 조회는 context 또는 `None`, 일봉 fetch는 dataframe·source를 반환한다.
- 상태·부작용: 폴백 일봉을 DB에 저장할 수 있다. 원본 context는 얕게 복사하므로 미교체 중첩 객체는 공유된다. portfolio는 별도 얕은 복사다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 기본 context | map 또는 null | `code`, `date`, `today`, 선택적 `yesterday`, 비율·`ma_status`; 폴백 단일 행이면 yesterday가 없다. |
| 결측 | map | `data_missing=true`, `today={}`, `yesterday={}`; date는 종목 시장의 현재 날짜 ISO 문자열. 빈 map은 `None`과 다르다. |
| enhanced | map | `report_language`, `stock_name`, `news_window_days`(검색 서비스 속성 기본 3), `is_index_etf`, `fundamental_context`; quote/chip/trend가 참일 때 각각 `realtime`, `chip`, `trend_analysis`. 정확한 필드와 null 제거는 C-01. |
| 추가 map | optional map | `market_phase_context`는 호출자가 항상 대입. daily market은 안전 map과 문자열 요약을 함께 붙이고, portfolio는 얕은 복사, market structure는 map일 때 원본 참조를 붙인다. |
| `today` | map | 실시간 대체 시 `is_estimated=true`, `estimated_fields`와 출처·선택적 부분봉·시각 메타데이터를 포함한다. 가격 변화율은 %, 거래량 변화율은 배수다. |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-00 | 일봉 이력 존재 | 최신 두 행을 사용하고 target_date를 조회 필터로 쓰지 않는다. 전일 데이터가 있으면 비율과 MA 상태를 계산한다. trend는 20행 미만이면 위험 표시만 반환하고, 충분하면 MA·MACD·RSI 및 신호를 계산한다. 예외는 trend 없이 계속한다. | 코드 확인 |
| R-00a | 이력과 유효한 quote가 있고 실시간 기술지표 설정·거래일 조건 충족 | 마지막 일봉 날짜가 시장 오늘 이상이면 마지막 행 복사·수정, 이전이면 오늘 가상 봉 추가. 가격은 필수 양수, open은 quote open → pre_close → 마지막 close, high/low는 quote 값 → 가격. 거래량 0은 기존 봉을 덮지 않는다. | 코드 확인 |
| R-01 | DB context가 비어 있고 JP/KR/TW | 일봉 60일 요청; 실패·빈 결과는 원래 context 반환. 저장·재조회 실패 또는 재조회 빈 결과면 메모리 변환. 다른 시장은 원래 값 반환. | 코드 확인 |
| R-02 | context가 정확히 `None` | 시장 현재일·결측 표시와 빈 일봉으로 계속한다. | 코드 확인 |
| R-03 | 입력 결합 | 얕은 복사에 선택적 데이터 및 정규화 언어를 합친다. quote의 `None` 값은 제거하고 chip의 가격 없으면 0으로 상태를 계산한다. | 코드 확인 |
| R-04 | quote와 trend 존재, MA5 > 0, quote 가격 > 0 | C-01의 우선순위로 today를 만들고 기존 비실시간 소유 필드를 보존; 유효한 전일 종가·거래량이 있으면 변화율을 계산한다. | 코드 확인 |
| R-05 | 일일 시장 context 있음 | safe map의 prompt section이 비지 않을 때만 map과 요약을 부착한다. | 코드 확인 |

- 미결정: 없음. 선행 data-collection의 반환 계약과 대조했다.
- 확인 한계: 정적 분석만 수행했다. 실제 외부 응답과 시장 시계는 실행하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-00 | `src/storage.py:3483-3568` `get_analysis_context`, `_analyze_ma_status`; `src/core/pipeline.py:639-659` | 최신 두 일봉과 trend 호출 경계 | R-00 |
| C-05 | `src/stock_analyzer.py:33-200,206-754` `StockTrendAnalyzer`; `src/schemas/decision_scale.py:12-26,58-84` | trend 결과 기본값·상수·각 지표와 신호. `bias_threshold` 기본 5.0은 `src/config.py:1049` | R-00 |
| C-06 | `src/core/pipeline.py:2733-2811` `_augment_historical_with_realtime` | 거래일 조건과 봉 교체·추가 | R-00a |
| C-07 | `src/storage.py:159-177,2341-2366` `StockDaily.to_dict`, `get_latest_data` | DB 행 필드와 날짜 내림차순 | R-00 |
| C-08 | `data_provider/realtime_types.py:234-282` `get_chip_status` | chip 상태 설명 | R-03 |
| C-09 | `src/services/daily_market_context.py:635-713` `format_daily_market_context_prompt_section` | 빈 요약 배제, sentinel escape 및 비신뢰 배경 구획 | R-05 |
| C-10 | `src/core/trading_calendar.py:125-175,214-236`; `src/search_service.py:2279-2279,2526-2548,2668-2691`; `src/report_language.py:11-31,815-821`; `src/services/daily_market_context.py:62-86,959-964` | 시장·시계·ETF 분기, 언어 정규화 및 safe map | R-00a, R-03, R-05 |
| C-01 | `src/core/pipeline.py:1002-1215` `_enhance_context` | 모든 추가 필드·실시간 우선순위와 비율 | R-03, R-04 |
| C-02 | `src/core/pipeline.py:1965-2045` `_get_analysis_context_with_market_fallback`, `_build_analysis_context_from_daily_df` | 시장 분기와 dataframe 변환 | R-01 |
| C-03 | `src/core/pipeline.py:2693-2732` `_describe_volume_ratio`, `_compute_ma_status` | C-01이 호출하는 설명·MA 분류 | R-03, R-04 |
| C-04 | `src/core/pipeline.py:2113-2131` `_attach_daily_market_context` | 안전 요약 부착 | R-05 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. DB·fetcher·시계는 대체물로 제공하며 실제 제공자와 DB 엔진은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-00 | R-00 | DB에 종목 일봉 1행만 있고 target_date가 과거 | 최신 행을 today로 반환하고 yesterday·비율·ma_status는 없음; target_date는 조회를 제한하지 않음 |
| T-00a | R-00a | 거래일, 마지막 봉이 오늘 이전, 양수 quote 가격 | 오늘 가상 봉을 추가해 반환 |
| T-01 | R-01 | KR DB에 context 없음, fetch 결과 2행, 저장 실패 | 날짜순 마지막 두 행으로 context 반환; 전일 종가·거래량이 참이면 비율 계산 |
| T-02 | R-02 | 비 KR/JP/TW DB 반환 `None` | 빈 today/yesterday와 `data_missing=true` |
| T-03 | R-04 | quote price=110, trend MA5>0, yesterday close=100·volume=50, quote volume=100 | today close 110, estimated true, 가격 변화율 10.0%, 거래량 변화율 2.0 |
| T-04 | R-05 | daily market safe map의 포맷 결과가 빈 문자열 | 두 daily market 키 모두 추가하지 않음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-00 / T-00 | C-00, C-05, C-07 | DB 조회, 계산 및 최소 행 수 확인 |
| R-00a / T-00a | C-06, C-10 | 실시간 봉 보강 조건과 변경 확인 |
| R-01 / T-01 | C-02 | 분기·예외 직접 확인 |
| R-02 / T-02 | `src/core/pipeline.py:758-775` | `None` 비교 확인 |
| R-03 / R-04 / T-03 | C-01, C-03, C-08, C-10 | 입력 필드와 대체 확인 |
| R-05 / T-04 | C-04, C-09, C-10; `src/core/pipeline.py:788-797` | 부착 조건 확인 |
