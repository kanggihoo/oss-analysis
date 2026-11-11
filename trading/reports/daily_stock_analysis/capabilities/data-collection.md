---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/data/stock_index_loader.py
  - src/services/market_symbol_utils.py
  - src/services/stock_code_utils.py
  - src/services/stock_index_remote_service.py
  - src/core/pipeline.py
  - data_provider/base.py
  - data_provider/realtime_types.py
  - data_provider/yfinance_fetcher.py
  - data_provider/fundamental_adapter.py
  - data_provider/yfinance_fundamental_adapter.py
  - src/storage.py
  - src/config.py
  - data_provider/akshare_fetcher.py
  - data_provider/efinance_fetcher.py
  - data_provider/tencent_fetcher.py
  - data_provider/baostock_fetcher.py
  - data_provider/pytdx_fetcher.py
  - data_provider/tushare_fetcher.py
  - data_provider/tickflow_fetcher.py
  - data_provider/longbridge_fetcher.py
  - data_provider/futu_fetcher.py
  - data_provider/futu_fundamental_adapter.py
  - data_provider/tw_institutional_fetcher.py
  - data_provider/miaoxiang_fetcher.py
  - data_provider/finnhub_fetcher.py
  - data_provider/alphavantage_fetcher.py
  - src/services/stock_list_parser.py
status: ready
depends: []
---

# 데이터 수집·정규화

> 종목·지수 식별자와 설정을 받아 일봉을 정규화·저장하고, 실시간 시세·보유 원가 분포(chip)·펀더멘털을 후속 분석에 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 원래 입력의 지수 정체성을 판별한 뒤 종목 코드를 정규화하고 시장별 provider 후보를 고른다.
2. 호출자가 정한 유효 거래일의 DB 일봉이 있고 `force_refresh=false`이면 일봉 네트워크 요청을 건너뛴다.
3. 그렇지 않으면 provider를 순차 시도해 처음 얻은 비어 있지 않은 일봉을 정규화하고 `(code,date)`로 저장한다.
4. 분석 단계에서 가벼운 종목명 조회, 선택적 실시간 시세, chip 순서로 수집한다. 시세·chip 부재는 분석 중단 조건이 아니다.
5. 펀더멘털을 예산 안에서 집계한다. 블록마다 상태·출처·오류를 유지하고 수집 실패를 부분 입력으로 전달한다.
6. 후속 [컨텍스트 조립](analysis-context.md)은 저장 일봉·시세·chip·펀더멘털로 추세 및 판단 입력을 만든다. 기본 경로와 Agent 경로 모두 분기 전에 이 수집을 거친다.

### 1.2 범위·통합 지점

- 제공: provider 패밀리의 공통 일봉·시세·chip 계약, 시장별 라우팅, 펀더멘털 집계와 예산·캐시, 일봉 저장 및 실패 전달.
- 제외: 추세 점수·봉 overlay·DB `today/yesterday` 조립은 행 2, 검색은 행 3, 실행 스케줄은 행 7. 브로커 주문 API는 포함하지 않는다. 시세 provider로 쓰는 Longbridge/Futu는 주문 계층과 구별한다.
- 외부 의존: provider SDK/HTTP는 코드가 요청하는 열·타입 또는 예외를 반환하는 경계다. 서비스의 실제 가용성·필드 보장·요금은 미확인이다. 저장소는 일봉 유일키 조회와 transaction을 제공하고, 시계는 로컬 날짜·UTC·monotonic 용도로 나뉜다.
- 소유 상태: manager별 provider 목록·이름 캐시·펀더멘털 캐시·provider lock 및 timeout worker slot. 일봉 circuit breaker와 timeout quarantine은 manager 간 공유한다. DB 일봉과 write-only fundamental snapshot은 영속 상태다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `get_daily_data` | code:string, start/end:optional date string, days:int=30 → `(table,source_name)` | 표준 열 `date,open,high,low,close,volume,amount,pct_chg`와 `ma5,ma10,ma20,volume_ratio`. 날짜 오름차순. 특정 provider는 이를 override한다. 호출 날짜를 강제 필터하는 공통 사후 단계는 없다. |
| `fetch_and_save_stock_data` | code,force_refresh=false,current_time?,analysis_target? → `(bool,error?)` | 캐시 적중도 성공. 저장 새 행 0개도 성공. 예외는 오류 문자열과 false로 바꾼다. |
| 실시간 quote | `UnifiedRealtimeQuote?` | `price>0`이어야 usable. 원가격 통화는 `currency`, 시장은 `market`. `change_pct/turnover_rate/amplitude`는 % 수치, ratio는 배수, volume은 주식 수. `amount/total_mv/circ_mv`의 통화는 provider·시장에 따른다. 공통 타입 주석의 ‘元’을 모든 시장의 CNY로 해석하지 않는다. |
| quote 품질 | fetched_at/provider_timestamp:string?, is_stale:bool?,stale_seconds:int?,fallback_from:string? | 시스템 조회 시각과 provider 실제 시각을 구분. 미제공 provider 시각을 현재 시각으로 꾸미지 않는다. |
| `quote.to_dict()` | map | code/name/source는 항상 포함. optional은 None만 제거하므로 0,false,빈 list는 유지한다. 객체는 보충 과정에서 제자리 변경된다. |
| chip | `ChipDistribution?` | profit_ratio는 0~1 의미, avg_cost는 가격, concentration은 비율. manager의 usable 검사는 모든 값의 엄격한 범위 검증이 아니다. `to_dict`는 cost_70_low/high를 제외한다. |
| 펀더멘털 | map | `market,status,coverage,source_chain,errors`, 블록 `valuation,growth,earnings,institution,capital_flow,dragon_tiger,boards`; 해외에는 provider/as_of/data_quality/missing_fields/belong_boards도 있다. 블록은 `{status,coverage:{status},source_chain,errors,data}`. 비지원·실패는 숫자 0과 다르다. |
| 펀더멘털 주요 입력 | nullable 숫자·문자열·list/map | valuation: PE/PB/total_mv/circ_mv. growth: revenue_yoy/net_profit_yoy/roe/gross_margin(%). earnings: financial_report·forecast/quick summary·dividend(events,TTM cash/share,TTM yield %). institution: 지분 변화 또는 TW foreign/trust/dealer/total net. capital_flow: stock_flow와 sector_rankings, HK Futu는 latest/rows 형식도 가능. 세부 매핑은 C-ID가 기준이다. |

설정은 `ENABLE_REALTIME_QUOTE=true`, `ENABLE_CHIP_DISTRIBUTION=true`, `ENABLE_FUNDAMENTAL_PIPELINE=true`, `REALTIME_CACHE_TTL=600`초, `FUNDAMENTAL_STAGE_TIMEOUT_SECONDS=8`, `FUNDAMENTAL_FETCH_TIMEOUT_SECONDS=8`, `FUNDAMENTAL_RETRY_MAX=1`, `FUNDAMENTAL_CACHE_TTL_SECONDS=120`, `FUNDAMENTAL_CACHE_MAX_ENTRIES=256`이 기본이다. bool은 lower 결과가 `true`일 때만 true다. 숫자 설정 파싱은 C-14를 따른다. `FUNDAMENTAL_RETRY_MAX=0`도 실행에서는 최소 1회다(R-10).

### 1.3.1 Provider adapter 경계

각 행의 세부 요청·응답 열, 변환, 제한 및 예외는 표시된 C-ID에서 가져온다(R-17~R-20). 외부 서비스의 실제 보장은 미확인이다.

| Provider | 일봉·실시간·보조 데이터의 경계 | 코드 |
|---|---|---|
| Akshare | CN 개별 일봉은 Eastmoney→Sina→Tencent 내부 폴백, ETF·HK·등록 지수는 별도 endpoint. 기본 우선순위 1, 2~5초 간격. chip은 CN 개별 종목만. 재시도 decorator는 ConnectionError/TimeoutError에만 적용되며 내부 catch·변환 여부를 따라야 한다. | C-18 |
| Efinance | CN 주식·ETF 일봉, 둘 다 전방 조정, 60초 호출 제한. 미국·HK 일봉 거부. 기본 우선순위 0, 일봉 decorator 최대 1회. realtime 전체 시장 캐시 기본 600초. | C-19 |
| Tencent | CN 일봉. 기본 우선순위 5. STAR 688/689 이외 거래량 lot×100; count 제한으로 누락 의심 시 빈 표를 반환해 다음 provider로 넘긴다. | C-20 |
| Baostock·Pytdx | CN 일봉. Baostock 기본 우선순위 3, 전방 조정과 로그인·로그아웃; Pytdx 기본 2, host 순회·연결 cooldown, 비조정 원시 봉. 제한된 예외에 3회 재시도 decorator가 있으나 포장된 DataFetchError는 그 대상이 아니다. | C-21 |
| Tushare | token 설정 시 일봉·시세·chip. 기본 분당 80회 limiter, 코드에 따라 `daily`·`fund_daily`·`hk_daily` endpoint를 선택하며 여기서는 조정 인자를 넘기지 않는다. 실패는 예외 또는 None으로 상위 fallback. | C-22 |
| TickFlow | 설정된 key의 CN 주식·ETF 일봉/시세. 일봉 기본 adjust `none`, batch 기본 활성·100개, 요청 timeout 기본 30초. volume lot→주식 수, 비율→percent. TTL·잘림 검사는 R-20. | C-27 |
| Finnhub·AlphaVantage | key가 있는 US 개별 종목 일봉·시세. 일봉 volume×close를 amount로 추정; HTTP timeout과 오류는 일봉 예외, 시세 None. | C-28 |
| Longbridge·Futu | 설정/연결 시 해외 일봉과 HK/US 시세. Longbridge 일봉 ForwardAdjust, static 정보 캐시 기본 24시간. Futu HK 일봉은 미조정·1000개 요청, 오류·빈 결과는 빈 표 또는 None. | C-29 |
| Akshare fundamental·Yfinance fundamental | CN 재무/예고/배당/기관 및 해외 성장·분기 재무·배당·sector/industry mapping. 동일 분기 1년 전 비교를 요구하며 통화는 재무와 배당을 구분한다. | C-23, C-24 |
| Futu fundamental·Miaoxiang·TW 기관 | Futu OpenD HK 재무/배당/수급, Miaoxiang CN chip/수급, TWSE/TPEx 기관 순매수. 각각 별도 실패 및 캐시 경계 사용. | C-25, C-26 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 코드 입력 | 정규화 C-01 적용. `005930.KS/000660.KQ`의 suffix를 보존한다. 지수는 정규화 전에 파싱하여 명시 지수와 동명 6자리 주식을 섞지 않는다. | 코드 확인 |
| R-02 | 일봉 provider 선택 | 등록 provider는 priority 안정 정렬, 미설정 선택 provider는 생성하지 않는다. 알려진 시장 비지원 및 availability probe 실패 provider를 제외한다. 미국 개별 종목은 Finnhub→AlphaVantage→Yfinance→Longbridge 기본 후보를 현재 priority로 재정렬하며, Longbridge 사용 가능 시 이를 고정 선두로 둔다. 미국 지수는 Yfinance 고정 선두→Finnhub. JP/KR/TW 내장 일봉 후보는 Yfinance다. | 코드 확인 |
| R-03 | 일봉 성공·실패 | 첫 비어 있지 않은 표와 provider명을 반환. 예외는 다음 provider로 진행하고 일봉 breaker 실패를 기록한다. empty 표는 성공 health를 기록하되 다음 provider로 진행한다. 일반 종목 전부 실패는 DataFetchError; 등록 중국 지수는 고정 체인 실패 후 표준 빈 표와 빈 source를 반환한다. | 코드 확인 |
| R-04 | 공통 BaseFetcher 일봉 | end 미지정이면 시스템 오늘, start 미지정이면 end에서 days×2 달력일을 뺀다. close/volume 결측 행 제거·날짜 정렬·MA 및 전일 5일평균 거래량 대비 배수 계산은 C-03. | 코드 확인 |
| R-05 | 수집·저장 | 유효 거래일은 외부 달력 경계가 결정한다. 해당 일자 DB 존재+force false이면 skip. 아니면 days=30으로 조회하고 upsert. 수집/저장 실패가 나도 상위 단일종목 처리는 기존 DB로 분석을 시도한다. `skip_analysis=true`도 수집·저장 뒤에 적용한다. | 코드 확인 |
| R-06 | 실시간 일반 A주 | 설정 순서 기본 `tencent,akshare_sina,efinance,akshare_em`. 첫 usable quote를 primary로 보존하고 이후 usable source 중 최대 하나의 필드만 합친다. 보충 필드는 C-05의 7개이며 price/source를 교체하지 않는다. 전부 실패는 None. | 코드 확인 |
| R-07 | 해외 실시간 | JP/KR/TW는 Yfinance만. US는 Longbridge 사용 가능 시 우선, 아니면 Yfinance 우선; 개별 종목에는 secondary 뒤 Finnhub/AlphaVantage로 보충 가능. US 지수는 Yfinance only. HK는 `futu,longbridge,akshare,yfinance` 설정 순서이며 미설정 Futu는 fallback 실패로 기록하지 않는다. | 코드 확인 |
| R-08 | 실시간 품질 | UTC fetched_at 부착. provider_timestamp가 없거나 파싱 불가면 timestamp/stale_seconds/is_stale 모두 None. 있으면 UTC 정규화 후 음수 age를 0으로 제한하고 age>TTL일 때만 stale. stale은 이 manager에서 quote 거부 조건이 아니다. | 코드 확인 |
| R-09 | chip 수집 | 설정 off면 None. priority 순으로 get_chip_distribution 구현 provider를 시도. avg_cost>0 및 concentration_90 또는70>=0가 있어야 usable. 0·None placeholder는 후속 provider로 진행. 예외는 breaker failure, 빈/무의미 응답은 inconclusive 처리. | 코드 확인 |
| R-10 | 펀더멘털 예산·재시도 | CN은 valuation→bundle→capital_flow→dragon_tiger→boards 순으로 남은 stage 예산을 소비. attempt 수는 max(1,retry_max), 고정 sleep 없음. timeout은 호출자의 대기만 끝내며 daemon 작업을 취소하지 않는다. manager slot 8개, 명시 quarantine key는 timeout 후 실제 작업 종료까지 새 호출을 막고 manager 간 공유한다. | 코드 확인 |
| R-11 | 펀더멘털 시장 경로 | CN bundle은 Akshare. 해외는 Yfinance bundle, HK OpenD 설정 시 Futu 우선·필드 공백은 Yfinance로 보충. JP/KR capital_flow/dragon_tiger/institution 기본 not_supported. TW institution은 4개 core net이 모두 None 아니면 ok이며 진짜 0은 보존한다. ETF는 capital_flow/dragon_tiger/boards를 비지원으로 둔다. 지수는 pipeline이 전체 fundamental 모듈을 비지원 구조로 건너뛴다. | 코드 확인 |
| R-12 | 블록 및 전체 status | 값이 있으면 블록 ok, 없으면 fallback status. CN은 전부 not_supported면 not_supported, failed/partial 포함이면 partial, 그 외 ok(일부 not_supported와 ok 혼합도 ok). ETF는 일부라도 지원되면 partial. 해외는 평가용 active_statuses를 따르며 TW institution ok도 전체 판정에 포함. | 코드 확인 |
| R-13 | 펀더멘털 캐시 | manager 메모리 캐시 key는 정규화 code+100ms budget bucket. TTL>0일 때만 조회/저장하고 반환은 deep copy가 아닌 저장 context 참조다. top status failed는 저장 안 함; ok 또는 의미 있는 블록 data가 있는 일부 성공만 저장. 만료 초과·가장 오래된 항목부터 제거. | 코드 확인 |
| R-14 | 영속 쓰기 | 일봉 중복 날짜는 배치 마지막 행이 이김. NaN은 SQL NULL, 새 행 count만 반환. 기존 canonical_id를 새 NULL로 덮지 않음. fundamental snapshot 쓰기 실패는 로그만 남기고 분석 계속. 분석 전에 snapshot을 읽어 재사용하지 않는다. | 코드 확인 |
| R-15 | 일봉·chip breaker | 일봉 key는 시장+provider, 실패 3회/300초. chip key는 provider_chip, 실패2회/600초. cooldown 뒤 half-open probe1회, 성공 reset/실패 reopen/불확실 응답 재냉각. | 코드 확인 |
| R-16 | Yfinance 일봉·한국 시세 | 일봉 요청은 auto_adjust=true; pct_chg는 close 변화×100, amount는 volume×close 추정. 한국 explicit suffix 그대로 요청. 시세는 fast_info 예외 시 history(2d) fallback, amount/volume_ratio/turnover_rate는 None이고 valuation은 info에서 보충한다. 네트워크 실제 성공은 미확인. | 코드 확인 |
| R-17 | provider별 일봉 | 아래 adapter 표의 시장·조정 방식·실패 정책과 C-ID의 실제 필드 mapping을 적용한다. 조정 기준·거래량 단위는 provider마다 다르며 manager는 첫 비어 있지 않은 결과를 선택한다. | 코드 확인 |
| R-18 | Akshare·Yfinance·Futu fundamental | Akshare는 각 endpoint 후보의 첫 유효 표를 쓰고 시장 전체 표는 요청 코드가 존재해야 한다. Yfinance는 분기 재무와 info를 best-effort 결합하고 같은 분기 전년 대비가 없으면 info 성장률을 쓴다. Futu는 profile→financials→배당/분할→수급→소속판을 순서대로 시도하고 반환된 데이터로 부분 결과를 만든다. 세부 필드·예외·배당 창은 C-23~C-25. | 코드 확인 |
| R-19 | 선택 수급 provider | Miaoxiang은 300초 기본 캐시와 단일 비차단 요청 lock을 사용한다. 금액 필드만 자금 유입으로 채택하며 최신 항목이 비어 있으면 과거로 대체하지 않고 5/10일 합계는 해당 창 전체가 존재해야 한다. Taiwan 기관 수급은 시장·날짜별 900초 기본 캐시와 동일 key 단일 요청, 시장별 실패 3회·300초 breaker를 쓴다. 빈 응답은 캐시하지 않고 네트워크 실패는 None이다(C-26). | 코드 확인 |
| R-20 | TickFlow 기간 일봉 | Asia/Shanghai 시각의 시작·종료와 count를 함께 전송하고 count가 꽉 찬 응답의 첫 날짜가 첫 예상 거래일보다 늦으면 잘림으로 거부하여 다음 provider로 넘긴다. 일봉 캐시는 symbol·시작·종료·adjust key로 인스턴스 수명 중 유지하며 복사본을 반환한다. | 코드 확인 |

- 미결정: 없음.
- 확인 한계: 원본 설치·실행·외부 API 호출 없음. 날짜 동결은 DB 조회/분석 구간의 장치이며 모든 네트워크 자료의 point-in-time 보장으로 확대할 수 없다. 일봉 네트워크 호출에 frozen target을 end_date로 전달하지 않고 펀더멘털도 현재 상태를 가져온다(R-04/05/10/16).

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `data_provider/base.py:71-270` normalize_stock_code·시장/chip 판정 | 코드·시장·ETF 분류와 chip usable 조건 | R-01,09,11 |
| C-02 | `data_provider/base.py:634-710` manager 상태·체인, `data_provider/base.py:727-878` 조회/probe/lock, `data_provider/base.py:1791-1903` 초기화, `data_provider/base.py:1917-2183` get_daily_data, `data_provider/base.py:2805-2831` 미국 정렬 | provider 등록·일봉 라우팅 | R-02,03 |
| C-03 | `data_provider/base.py:467-604` BaseFetcher.get_daily_data/_clean_data/_calculate_indicators | 공통 날짜·정규화 호출·지표 계산 | R-04 |
| C-04 | `src/core/pipeline.py:376-432` fetch_and_save_stock_data, `src/core/pipeline.py:3212-3227` 유효일 경계, `src/core/pipeline.py:3330-3368` 단일종목 호출 | 일봉 cache→fetch→save, 실패 후 분석 | R-05 |
| C-05 | `data_provider/base.py:2352-2803` timestamp·실시간 라우팅·merge, `data_provider/base.py:2833-2910` provider 시도/보충 | 실시간 main 보존과 품질 metadata | R-06~08 |
| C-06 | `data_provider/realtime_types.py:94-282` enum·UnifiedRealtimeQuote·ChipDistribution | 전체 필드·직렬화·chip 문구 임계값 | R-08,09 |
| C-07 | `data_provider/base.py:2916-3028` get_chip_distribution, `data_provider/realtime_types.py:285-464` CircuitBreaker와 인스턴스 | chip fallback·breaker 전이 | R-09,15 |
| C-08 | `data_provider/base.py:3381-3487` timeout/retry, `data_provider/base.py:4261-4564` get_fundamental_context | CN 수집 순서·예산·배당수익률·전체 상태 | R-10~12 |
| C-09 | `data_provider/base.py:3494-3676` 블록/값/캐시 판정, `data_provider/base.py:1618-1679` scalar 결측 판정, `data_provider/base.py:3678-3732` 비지원, `data_provider/base.py:4225-4260` 실패 builder | 0과 누락 구분, source_chain·status 공통 | R-11~13 |
| C-10 | `data_provider/base.py:3734-4223` 해외 bundle·집계 | HK 필드 보충·TW 기관 수급·해외 전체 상태 | R-11,12 |
| C-11 | `data_provider/base.py:1578-1615` key/prune | 예산 bucket·TTL·LRU가 아닌 작성시각순 제거 | R-13 |
| C-12 | `data_provider/base.py:4566-4870` capital/dragon/boards | 개별 수급 fallback·남은 예산·sector 순위 | R-10~12 |
| C-13 | `src/storage.py:2263-2274` 날짜·SQL 값 정규화, `src/storage.py:2310-2339` has_today_data, `src/storage.py:3294-3481` save_daily_data, `src/storage.py:2202-2243` write transaction | upsert·중복·신규수·rollback·SQLite lock retry | R-05,14 |
| C-14 | `src/config.py:185-185` stage 기본값, `src/config.py:2307-2347` 환경설정 로드 | on/off·수집 예산·cache 설정 | R-06,10,13 |
| C-15 | `src/core/pipeline.py:500-637` 실시간/chip/fundamental 수집·snapshot | 전처리 실패 허용·지수 capability skip | R-09~11,14 |
| C-16 | `data_provider/yfinance_fetcher.py:97-307` 코드/일봉/정규화, `data_provider/yfinance_fetcher.py:794-945` 시세 | 한국 시장 포함 Yahoo 요청·응답 매핑 | R-16 |
| C-17 | `data_provider/fundamental_adapter.py:341-625` Akshare bundle/capital/dragon, `data_provider/yfinance_fundamental_adapter.py:53-158` 공통 변환 | 펀더멘털 입력 mapping 진입점 | R-10~12 |

| C-18 | `data_provider/akshare_fetcher.py:64-105, 111-159, 162-224, 252-275, 321-403, 404-1022, 1073-1521, 1522-1820, 1821-1898` | 일봉·실시간·chip 요청, 내부 fallback, 공통 변환 및 timeout helper. | R-06,07,09,17 |
| C-19 | `data_provider/efinance_fetcher.py:126-146, 153-217, 262-623, 624-748, 830-923` | 일봉/ETF·시세 mapping, 캐시, timeout·오류 처리. | R-06,17 |
| C-20 | `data_provider/tencent_fetcher.py:26-105, 137-279` | 일봉 count·잘림 검사·lot 변환과 필드 mapping. | R-17 |
| C-21 | `data_provider/baostock_fetcher.py:45-54, 57-288`; `data_provider/pytdx_fetcher.py:48-83, 86-95, 98-282, 304-410` | 종목 코드·세션·일봉 조회와 normalization, retry·cooldown. | R-17 |
| C-22 | `data_provider/tushare_fetcher.py:51-125, 135-297, 301-469, 470-596, 701-808, 1151-1298` | 인증·rate limit·일봉·quote·chip 및 계산. | R-09,17 |
| C-23 | `data_provider/fundamental_adapter.py:24-46, 48-335, 338-625` | Akshare fundamental 후보·검색·기간·배당·수급 mapping과 결측·오류 규칙. | R-10~12,18 |
| C-24 | `data_provider/yfinance_fundamental_adapter.py:39-147, 150-386` | 해외 bundle, ratio 변환·전년 같은 분기 45일 허용·분기/TTM fallback·배당 및 통화. | R-11,12,18 |
| C-25 | `data_provider/futu_fundamental_adapter.py:11-276`; `data_provider/futu_fetcher.py:28-59, 66-131, 144-264` | HK profile·financials·corporate actions·capital flow·board API와 응답 mapping. | R-11,12,18 |
| C-26 | `data_provider/miaoxiang_fetcher.py:38-87, 89-259, 259-395`; `data_provider/tw_institutional_fetcher.py:20-100, 102-398` | Miaoxiang 표 추출·수급 및 Taiwan 기관 자료 매핑, TTL, throttle, breaker. | R-09,11,19 |
| C-27 | `data_provider/tickflow_fetcher.py:40-82, 84-131, 153-234, 237-299, 334-556, 574-721, 722-877` | TickFlow 변환·count·batch·기간 캐시·잘림 검증·시세. | R-17,20 |
| C-28 | `data_provider/finnhub_fetcher.py:20-149`; `data_provider/alphavantage_fetcher.py:20-161` | US 일봉/시세 요청, 응답·오류 mapping. | R-07,17 |
| C-29 | `data_provider/longbridge_fetcher.py:38-80, 325-411, 414-497, 497-665, 680-941`; `data_provider/futu_fetcher.py:28-131, 271-348` | Longbridge 인증/연결·cache·일봉/시세, Futu HK 일봉·시세. Longbridge 설정 구성 helper는 같은 파일 `82-324` 참조. | R-07,17 |
| C-30 | `src/services/stock_list_parser.py:52-87, 127-157, 176-188, 191-253, 257-287, 290-407, 465-520, 526-626, 632-815, 855-1005, 1037-1136`; `src/data/stock_index_loader.py:23-53, 56-67, 106-114, 203-230, 404-651` | 명시 index canonical/alias를 먼저 찾아 대상 확정; bare numeric은 stock. active registry 후보·검증·캐시. | R-01 |
| C-31 | `src/services/stock_code_utils.py:21-35, 39-81, 121-195, 226-247`; `src/services/market_symbol_utils.py:15-64, 88-97`; `data_provider/base.py:273-291`; `src/services/stock_index_remote_service.py:20-29, 68-70, 91-135` | C-30의 코드 정규화·suffix·BSE 판정·registry payload helper. | R-01 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. provider·DB·시계를 대체하여 반환/저장 정책을 검증하는 사례이며 외부 서비스 품질을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01,02,16 | `005930.ks`, 내장 fetcher 목록 | `005930.KS` 유지, 한국 일봉 Yfinance 경로 사용 |
| T-02 | R-04 | close=[10,20], volume=[100,200] | ma5=[10,15], volume_ratio=[1,2]; 날짜 오름차순 |
| T-03 | R-03,15 | 첫 일봉 provider 예외, 다음 정상 표 | 다음 source명과 표 반환, 첫 provider health 실패 증가 |
| T-04 | R-05 | 유효 거래일 DB 있음, force false | provider 일봉 미호출, `(true,None)` |
| T-05 | R-05,14 | 같은 날짜 행 두 개 포함, 기존 날짜 갱신 | 배치 마지막 값 저장, 신규수에는 갱신 미포함 |
| T-06 | R-06 | primary.price=100,volume_ratio=None; 다음 usable source.price=101,volume_ratio=2 | primary 가격100 유지, volume_ratio2만 보충 |
| T-07 | R-08 | provider_timestamp 없음 | fetched_at만 생성, stale 관련 세 필드는 None |
| T-08 | R-08 | provider age=600초, TTL600 | is_stale=false; 601초일 때 true |
| T-09 | R-09 | avg_cost=0인 chip, 다음 정상 chip | 첫 응답 미채택, 다음 응답 반환; 빈 응답은 예외 failure로 세지 않음 |
| T-10 | R-10 | timeout 작업이 계속 실행, 동일 quarantine key 재호출 | 첫 대기는 종료, 작업은 계속; 후속은 previous request still running 오류 |
| T-11 | R-11,12 | 한국 valuation/growth ok, capital/institution 비지원 | 해외 전체 status는 active 집계에 따라 ok 가능; 비지원 항목은 coverage에 유지 |
| T-12 | R-13 | ttl120, age120초인 cached context, 같은 bucket | 저장 객체 참조 반환; age>120이면 새 집계 |
| T-13 | R-05 | 일봉 전체 실패, skip_analysis false | fetch false 후에도 analyze 시도 |
| T-14 | R-11 | TW 네 net figure 모두0 | 기관 block ok, ‘없음’으로 치환하지 않음 |
| T-15 | R-17 | Tencent `688001`과 `600000`의 raw volume 각각 2 | 표준 volume은 각각 2, 200. |
| T-16 | R-18 | Yfinance 분기 값은 있으나 1년 전 같은 분기 자료 없음 | QoQ로 오인하지 않고 `info` 성장률을 사용하거나 None. |
| T-17 | R-19 | Miaoxiang 최근 5개 중 한 값 누락 | 5일 합계 None; 이전 날짜로 빈칸을 채우지 않음. |
| T-18 | R-20 | TickFlow 반환 수가 count에 도달하고 첫 봉이 예상 첫 거래일보다 늦음 | 잘림 오류, 이 표는 저장하지 않고 manager가 다음 provider를 시도. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

기준은 frontmatter의 SHA다. `코드 확인`은 클라이언트의 호출·변환·실패 정책을 읽었다는 뜻이다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01/T-01 | C-01,02,16 | suffix 보존·정규화 이전 지수 분기 확인 |
| R-02,03/T-03 | C-02,07 | 주석의 단순 Yfinance 우선 설명과 실제 미국 Finnhub/AlphaVantage 체인이 다름. 구현 기준으로 정리 |
| R-04/T-02 | C-03 | rolling min_periods=1 및 shift(1), 소수2자리 확인 |
| R-05/T-04,05,13 | C-04,13 | has_today_data의 자연일 주석과 달리 pipeline은 유효 거래일을 명시 전달 |
| R-06,07/T-06 | C-05,14 | 설정 목록 및 해외 별도 분기 직접 확인 |
| R-08/T-07,08 | C-05,06 | timestamp 없는 quote를 stale=false로 보장하지 않음 |
| R-09,15/T-09 | C-01,07 | 실패와 inconclusive·half-open 상태 구분 |
| R-10/T-10 | C-08,12 | daemon timeout이 취소가 아님을 구현에서 확인 |
| R-11,12/T-11,14 | C-09,10,12,15,17 | 시장별 비지원과 0 값 보존 확인 |
| R-13/T-12 | C-09,11 | 캐시 참조 반환 및 budget key·TTL 경계 확인 |
| R-14/T-05 | C-13,15 | write-only snapshot과 일봉 upsert 경계 확인 |
| R-17/T-15 | C-18~22, C-27~29 | 각 provider 호출 및 변환 구현 확인. |
| R-18/T-16 | C-23~25 | statement·dividend·부분 실패 코드 확인. |
| R-19/T-17 | C-26 | 수급 API와 캐시·락·breaker 코드 확인. |
| R-20/T-18 | C-27 | count 제한 검증과 인스턴스 cache 직접 확인. |
| R-01 | C-30,31 | 등록 index parser와 registry helper를 로컬 C-ID로 명시하여 선행 순환을 방지. |
| R-16/T-01 | C-16 | retry decorator는 ConnectionError/TimeoutError지만 본문이 대부분 DataFetchError로 감싸므로 네트워크 오류마다 3회 보장은 없음 |

핵심 고정 근거: [일봉 routing](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/data_provider/base.py#L1917-L2183), [펀더멘털 집계](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/data_provider/base.py#L4261-L4564).

### 2.2 코드 읽는 순서

pipeline의 일봉 사전 저장 → manager 시장 routing → BaseFetcher 정규화 → 분석 직전 realtime/chip/fundamental 순으로 읽는다. 이후 행2에서 DB 최신 두 봉과 trend 계산을 확인한다. 외부 provider가 종목에 따라 다른 통화·권한·결측을 반환할 수 있다는 사실과, 클라이언트가 그 응답을 어떤 입력으로 취급하는지는 구분한다.
