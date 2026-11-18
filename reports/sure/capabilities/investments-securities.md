---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/holding.rb
  - app/models/holding/materializer.rb
  - app/models/holding/forward_calculator.rb
  - app/models/holding/reverse_calculator.rb
  - app/models/holding/portfolio_cache.rb
  - app/models/holding/portfolio_snapshot.rb
  - app/models/holding/trade_calculator_helpers.rb
  - app/models/holding/lot_book.rb
  - app/models/holding/cost_basis_reconciler.rb
  - app/models/holding/gapfillable.rb
  - app/models/holding/holding_data.rb
  - app/models/holding/current_for_investment_accounts.rb
  - app/models/holding_lot.rb
  - app/models/trade.rb
  - app/models/trade/create_form.rb
  - app/models/security.rb
  - app/models/security/resolver.rb
  - app/models/security/provided.rb
  - app/models/security/split.rb
  - app/models/security/price.rb
  - app/models/security/price/importer.rb
  - app/models/security/price/import_windows.rb
  - app/models/security/manual_price_import.rb
  - app/models/security/health_checker.rb
  - app/models/security/combobox_option.rb
  - app/models/security/plan_restriction_tracker.rb
  - app/models/security/warsaw_price_currency_backfill.rb
  - app/models/holding/cost_basis_tracker.rb
  - app/models/onchain/security_resolver.rb
  - app/models/property.rb
  - app/controllers/api/v1/trades_controller.rb
  - app/controllers/api/v1/securities_controller.rb
  - app/controllers/concerns/api/v1/security_resource_filtering.rb
  - app/models/provider.rb
  - app/models/provider/security_concept.rb
  - app/models/provider/registry.rb
  - app/models/provider/yahoo_finance.rb
  - app/models/provider/eodhd.rb
  - app/models/provider/property_valuation_concept.rb
  - app/models/setting.rb
  - app/models/account.rb
  - app/models/account/market_data_importer.rb
  - app/models/market_data_importer.rb
  - app/models/balance/materializer.rb
  - app/models/balance/sync_cache.rb
  - app/models/investment.rb
  - app/models/investment_statement.rb
  - app/models/investment_statement/totals.rb
  - app/models/investment_flow_statement.rb
  - app/models/portfolio/section_registry.rb
  - app/models/portfolio/flow_classifier.rb
  - app/models/portfolio/xirr.rb
  - app/controllers/holdings_controller.rb
  - app/controllers/trades_controller.rb
  - app/controllers/securities_controller.rb
  - app/controllers/portfolios_controller.rb
  - app/controllers/investments_controller.rb
  - app/controllers/settings/hostings_controller.rb
  - app/controllers/api/v1/security_prices_controller.rb
  - app/jobs/sync_property_valuations_job.rb
  - config/exchanges.yml
  - config/schedule.yml
  - docs/llm-guides/adding-a-securities-provider.md
  - db/schema.rb
depends:
  - ./money-currency-rules.md
  - ./provider-import-adapter.md
status: draft
---

# 투자·시세 구조 (Holding·Trade·Security, 시세 provider 인터페이스, 투자 요약)

> 매매(Trade) 기록과 외부에서 받은 보유(Holding) 스냅샷, securities provider가 주는 종목 검색 결과와 일별 종가를 입력으로 받아, 종목(Security) 해석, 일별 시세 적재, 보유종목 일별 재구성, 보유 단가(cost basis)와 lot 계산, 투자 요약(평가액·수익·배분), 부동산 시세 갱신을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

수동 증권 계정(연동 없음)에서 한국 종목 매수 한 건이 보유 평가액이 되기까지의 대표 경로다. 연동 계정은 3번의 입력이 provider 스냅샷으로 바뀐다(R-28, R-33).

1. 사용자가 종목 검색창에 입력하면 켜져 있는 모든 securities provider가 병렬로 검색하고, 결과가 `티커|MIC|provider` 형식 id의 선택지로 나온다(R-07, R-08).
2. 사용자가 선택지를 골라 매수를 저장하면 `Security::Resolver`가 DB의 `Security`를 찾거나 만들고(R-09~R-12), `Trade`를 가진 `Entry`가 저장되고 계정 sync가 예약된다(R-15). 선택한 `price_provider`가 종목에 저장된다.
3. sync 때 시장 데이터 단계가 계정의 종목별 필요 구간(첫 매매일부터 보유 중이면 오늘까지)을 정하고(R-17, R-18), provider에서 일별 종가를 받아 빠진 날을 직전 값으로 채워 `security_prices`에 저장한다(R-19~R-24).
4. `Holding::Materializer`가 계정의 첫 항목 전날부터 오늘까지 하루씩 걸으며 매매와 액면분할을 적용해 종목별 수량을 만들고, 그날 가격(DB 시세, 없으면 매매가)을 계정 통화로 환산해 `holdings` 행을 만든다(R-28~R-35).
5. 같은 계산이 보유 단가를 lot 장부로 구해 `holdings.cost_basis`에 쓰고, 사용자·provider가 정한 값과 우선순위로 조정한다(R-36, R-40~R-45).
6. 잔액 계산(Balance)이 방금 저장된 holdings를 읽어 계정 총액과 현금을 구한다(R-28, 경계만).
7. 화면은 `current_holdings`와 `InvestmentStatement`로 포트폴리오 평가액, 평가손익, 일변동, 종목 배분을 family 대표 통화로 합쳐 보여 준다(R-39, R-51~R-59).

### 1.2 범위·통합 지점 [필수]

- 제공: `Security` 식별·해석·검색, 시세 provider 인터페이스(`securities` concept)와 그 인터페이스를 쓰는 시세 적재(구간 계산, gap 채우기), 수동 시세, 종목 건강 점검, `Holding` 일별 재구성(forward·reverse), 보유 단가·lot 계산과 출처 우선순위, 보유 종목 교체(remap)·삭제, 실현·미실현 손익, 투자 요약·배분·기간 합계, 포트폴리오 화면의 데이터, 부동산 시세 갱신 job과 `property_valuations` provider 인터페이스.
- 제외:
  - 환율 조회·fallback·적재와 통화 쌍 시작일 규칙. [money-currency-rules.md](./money-currency-rules.md)가 가졌다(환율 R-25~R-27, 쌍 규칙 R-35). 이 스펙은 `exchange_to`와 `rates_for`를 부르는 곳과 실패 때의 처리만 쓴다(R-61).
  - 잔액(Balance) 계산. 행 1(`account-balances`, 미작성)이 가진다. 이 스펙은 holdings가 Balance로 들어가는 경계(R-28)만 쓴다.
  - 연동이 holding·trade를 넣는 계약. [provider-import-adapter.md](./provider-import-adapter.md)의 `import_holding`(R-43~R-50), `import_trade`(R-51~R-55). 이 스펙은 그 결과로 생긴 provider 행을 materializer가 어떻게 대하는지(R-36, R-37)만 쓴다.
  - sync 오케스트레이션(언제 `Account::MarketDataImporter`가 불리는지). [sync-pipeline.md](./sync-pipeline.md) R-17. 이 스펙은 불린 뒤 하는 일을 쓴다.
  - 개별 securities provider 구현 내부(HTTP, 인증, throttle). Yahoo Finance와 EODHD는 인터페이스를 설명하는 대표 예로만 읽었다(R-66, R-67).
  - 기여·인출 라벨로 잡는 현금 흐름 `InvestmentFlowStatement`(리포트 화면이 부른다, 행 14). `Portfolio::FlowClassifier`·`Portfolio::Xirr`(기준 SHA에서 호출처 없음, R-60).
  - 거래 일반(`Transaction`) CRUD, 이체 매칭, 가져오기(`TradeImport`)와 QIF import가 `Security::Resolver`를 부르는 방식(행 2, 3, 8). 부르는 인터페이스는 R-09에 있다.
  - Sharesight 계정 설정 저장(`InvestmentsController#update`의 Sharesight 부분). 개별 provider 소관이다.
- 외부 의존·선행 계약:
  - 금액·환산: money-currency-rules의 `Money`, `exchange_to`, `rates_for`, `rate_sql`, 통화 표.
  - provider 어댑터: `account_provider_id`가 있는 holding 행(provider 스냅샷)과 `CostBasisReconciler`를 어댑터와 같이 쓴다([provider-import-adapter.md](./provider-import-adapter.md) R-48).
  - 저장소: PostgreSQL 전제 기능(partial·expression unique index, CHECK, `DISTINCT ON`, `jsonb`, `FILTER`). 키-값 캐시(검색 결과 5분, 실패 로그 throttle).
  - 시계: `Date.current`(요청·sync 문맥의 시간대). 시세 구간의 끝은 뉴욕 오늘이라는 코드 의도가 있다(R-20).
  - 설정: `SECURITIES_PROVIDERS`(쉼표 목록), `SECURITIES_PROVIDER`(단일 fallback), provider별 API 키(R-14).
  - 오류 보고(Sentry, `DebugLogEntry` 수준의 handled warning 기록).
- 소유 상태·부작용: `securities`, `security_prices`, `security_splits`, `holdings`, `holding_lots`, `trades`(entryable) 행. `properties.avm_*` 열(job이 쓴다). 다른 기능에 보이는 부작용: 매매·보유 변경 뒤 계정 sync 예약(`account.sync_later`), 시세 적재가 `exchange_rates`를 부를 필요를 만든다(R-18), `Setting` 변경 때 종목의 `offline` 일괄 변경(R-14).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. `decimal`은 임의 정밀도 10진수다. 제약은 DB가 강제하는 것과 모델 검증이 강제하는 것을 구분해 적는다. 괄호의 `(p,s)`는 전체 자릿수와 소수 자릿수다.

**저장 데이터**

| 데이터 | 열과 제약 | 의미·제약 |
|---|---|---|
| `securities` | `id` uuid, `ticker` string not null, `exchange_operating_mic` string null, `name`, `country_code`, `price_provider` string null, `offline` bool 기본 false not null, `offline_reason` string null, `failed_fetch_count` int 기본 0 not null, `failed_fetch_at`, `first_provider_price_on` date null, `last_health_check_at`, `kind` string 기본 `standard` not null, `logo_url`, `website_url`, `exchange_mic`, `exchange_acronym`, 분류 열(`asset_class`, `asset_sub_class`, `classification_source`, `classification_locked`, `sector`, `industry`, `region`) | unique 식별은 `(대문자 ticker, 대문자 MIC 또는 빈 문자열)`(DB 식 index). DB CHECK로 닫힌 목록인 열은 `kind`(`standard`·`cash`), `asset_class`, `asset_sub_class`, `classification_source` 넷뿐이고 `sector`·`industry`·`region`은 제약이 없다(provider마다 어휘가 달라서, 모델도 검증하지 않는다). 모델의 ticker 유일 검증은 MIC의 nil과 빈 문자열을 다르게 보고, DB 식 index는 같은 칸으로 본다. `price_provider`는 모델 검증으로 registry의 securities 키 중 하나만 허용(nil 허용). 분류 열을 쓰는 코드는 기준 SHA에 없고(R-02 근거) 투자 배분의 읽기에만 쓰인다. |
| `security_prices` | `security_id`(DB는 null 허용, 모델은 `belongs_to :security`), `date` not null, `price` decimal(19,4) not null, `currency` string 기본 `USD` not null, `provisional` bool 기본 false not null | unique `(security_id, date, currency)`. 같은 날 통화가 다른 두 행이 공존할 수 있다(U-01). `provisional`은 gap 채우기로 만든 최근 값을 뜻한다(R-23). |
| `security_splits` | `security_id`, `ex_date`, `numerator` int, `denominator` int, `source` string not null | unique `(security_id, ex_date)`. DB CHECK `numerator > 0 AND denominator > 0`, `numerator <> denominator`. 새 주식 수 / 옛 주식 수 비율이다(2-for-1은 2/1, 1-for-10 병합은 1/10). 이 스펙 범위에서 split을 쓰는 곳은 읽기뿐이다(R-34). |
| `trades`(Entry의 entryable) | `security_id` not null, `qty` decimal(34,18), `price` decimal(19,10), `fee` decimal(19,4) 기본 0 not null, `currency` string, `investment_activity_label`, `extra` jsonb 기본 `{}`, `locked_attributes` jsonb | `qty` 부호가 방향이다(양수 매수, 음수 매도). 금액은 부모 `Entry.amount`(부호 규칙은 money-currency-rules R-36, R-38)에 따로 저장된다. `extra.exchange_rate`에 거래 자신의 환율을 둘 수 있다(R-05). |
| `holdings` | `account_id`, `security_id`, `date`, `currency` not null, `qty` decimal(34,18) not null, `price` decimal(19,4) not null, `amount` decimal(19,4) not null, `cost_basis` decimal(19,4) null, `cost_basis_source` string null(`manual`·`calculated`·`provider`), `cost_basis_locked` bool 기본 false, `security_locked` bool 기본 false, `provider_security_id` null, `account_provider_id` null, `external_id` null | unique `(account_id, security_id, date, currency)`, unique `(account_id, external_id)`(external_id가 있을 때). 모델 검증으로 `qty`·`price`·`amount`는 0 이상이다. 계산해서 만든 행은 이 검증을 거치지 않고 일괄 upsert로 들어가므로(R-36) 음수 수량이 저장될 수 있다. 행의 `account_provider_id`가 있으면 provider 스냅샷, 없으면 계산된 행이다. |
| `holding_lots` | `account_id`, `security_id`, `source_entry_id` null, `origin_security_id` null, `acquired_on`, `qty` decimal(34,18) not null, `unit_cost` decimal(25,10) null, `currency` not null, `clamped` bool | unique `(account_id, source_entry_id)`, `source_entry_id`가 없는 행(opening lot)은 `(account_id, security_id)`당 하나. DB CHECK `qty >= 0`. |
| `properties` | `avm_provider` null(CHECK: `rentcast`·`realie`·`chimnie`), `avm_external_id`, `avm_last_synced_on` | R-62~R-65가 쓴다. |

**securities provider 인터페이스** (`Provider::SecurityConcept`, 새 provider가 맞출 것)

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `search_securities(symbol, country_code:, exchange_operating_mic:)` | → Response, `data`: list of `Security(symbol, name, logo_url, exchange_operating_mic, country_code, currency?, isin?)` | `currency`·`isin`은 선택(없으면 nil). MIC는 ISO 10383 코드로 매핑해서 돌려줘야 한다. 호출자는 `symbol`, `name`, `logo_url`, `exchange_operating_mic`, `country_code`와 있으면 `currency`, `isin`만 읽는다(R-08, R-66). |
| `fetch_security_info(symbol:, exchange_operating_mic:)` | → Response, `data`: `SecurityInfo(symbol, name, links, logo_url, description, kind, exchange_operating_mic)` | 호출자는 `name`, `logo_url`, `links`(→ `website_url`)만 읽고 비어 있지 않은 것만 덮어쓴다(R-18). |
| `fetch_security_price(symbol:, exchange_operating_mic:, date:)` | → Response, `data`: `Price(symbol, date, price, currency, exchange_operating_mic)` | 한 날짜의 가격. 반환 `date`가 요청 날짜와 다를 수 있다(R-16). 종목 건강 점검(R-26)과 단건 조회(R-16)가 쓴다. |
| `fetch_security_prices(symbol:, exchange_operating_mic:, start_date:, end_date:)` | → Response, `data`: list of `Price` | 구간의 일별 종가. 거래일이 아닌 날이 빠져 있어도 된다. 날짜로 색인하므로 행 순서는 날짜별 가격 선택에 영향이 없다. 그러나 통화가 비었을 때 쓰는 초기 통화는 응답 첫 행의 통화라서 모든 행에 `currency`를 채우고 한 통화로 통일한다(R-21). `price`가 nil이거나 0 이하인 행은 호출자가 무효로 취급한다(R-21). |
| `max_history_days()` | → int 또는 nil | 선택. 값이 있으면 `end_date` 기준 그만큼 이전으로 요청 시작일을 줄인다(R-20). 없거나 nil이면 제한 없음. |
| Response | `Provider::Response(success?, data, error)` | 실패는 예외가 아니라 `success? = false`와 `error`로 전달한다. 모든 연산을 감싸는 래퍼(`with_provider_response`)가 블록의 예외를 잡아 provider 자신의 `Error`로 바꾼다(R-66). |

**등록과 설정**

| 이름 | 값·기본값 | 의미 |
|---|---|---|
| securities provider 키 | `twelve_data yahoo_finance tiingo eodhd alpha_vantage mfapi binance_public moex_public tinkoff_invest mansa` | 등록된 키 목록. `Security.price_provider`는 이 중 하나만 저장할 수 있다(R-02). |
| provider 생성 | API 키가 필요한 provider는 환경변수, 없으면 DB 설정의 키로 만들고 키가 없으면 provider 없음(nil)이다 | 키가 필요 없는 provider(`yahoo_finance`, `mfapi`, `binance_public`, `moex_public`)는 항상 만들어진다. |
| `SECURITIES_PROVIDERS`(환경변수) / DB 설정 `securities_providers` | 쉼표 목록, 기본 빈 문자열 | 켜진 provider와 그 순서. 환경변수가 우선(R-14). |
| `SECURITIES_PROVIDER` / DB 설정 `securities_provider` | 기본 `twelve_data` | 위 목록이 비었을 때만 쓰는 단일 fallback. |
| 종목 선택지 id | `"<ticker>\|<MIC>\|<price_provider>"` | 검색 결과 선택지의 id이자 매매·보유 교체 폼이 보내는 값이다(R-07). |

**주요 연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `Security::Resolver(symbol, exchange_operating_mic:, country_code:, price_provider:).resolve` | → Security(저장된 행) 또는 nil | symbol이 blank면 생성자가 오류, `resolve`는 항상 행을 돌려준다(없으면 offline 행을 만든다). R-09~R-12. |
| `Security.search_provider(symbol, country_code:, exchange_operating_mic:, technical_failure:)` | → list of 저장되지 않은 `Security`(검색 결과) | R-08. |
| `Security#find_or_fetch_price(date, cache)` | → 가격 행/Price 또는 nil | R-16. |
| `Security#import_provider_prices(start_date:, end_date:, clear_cache:)` | → `[저장 건수, provider 오류 문자열]` 또는 provider가 없으면 정수 0 | R-19. |
| `Security::Price::ImportWindows(account).to_h` | → map `{security_id: (start_date, end_date)}` | R-17. |
| `Holding::Materializer(account, strategy:, security_ids:).materialize_holdings` | `strategy`는 `forward`·`reverse`. → 계산한 holding 목록 | R-28. |
| `Holding#avg_cost` | → Money(보유 통화) 또는 nil(모름) | R-46. |
| `InvestmentStatement(family, user:)` | 읽기 전용 집계 | R-51~R-58. |
| `SyncPropertyValuationsJob.perform(property_id:, force:)` | 부수효과만 | R-62~R-65. |

### 1.4 행동 규칙과 남은 질문 [필수]

"계정 통화"는 `accounts.currency`, "family 통화"는 `families.currency`다. "시세"는 `security_prices` 행이다.

**A. 데이터 제약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Holding`을 모델로 저장한다 | `qty`, `currency`, `date`, `price`, `amount`가 있어야 하고 `qty`·`price`·`amount`는 0 이상이어야 한다. `external_id`는 계정 안에서 유일해야 한다(비어 있으면 검사 안 함). `cost_basis_source`는 nil 또는 `manual`·`calculated`·`provider`. 이 검증은 materializer의 일괄 upsert(R-36)에는 적용되지 않는다. DB의 unique `(account, security, date, currency)`는 모든 경로가 지킨다. | 코드 확인 |
| R-02 | `Security`를 저장한다 | 저장 전에 `ticker`를 대문자로 바꾼다. MIC는 값이 바뀔 때만 대문자로 바꾸고 별칭표(C-13)로 정식 MIC로 바꾼다. `ticker`가 필수이고 `(대소문자 무시 ticker, MIC)`가 유일해야 한다(이 유일성은 DB 식 index가 보장하고 거기서는 MIC의 nil과 빈 문자열이 같은 칸이다. 모델 검증은 `ticker`를 `exchange_operating_mic` 값 단위로 비교해 nil과 빈 문자열을 다르게 본다). `kind`는 `standard`·`cash`. `price_provider`는 nil이거나 registry 키 중 하나. `asset_class`·`asset_sub_class`·`classification_source`는 닫힌 목록이고 `sector`·`industry`·`region`은 검증이 없다. 분류 열(`asset_class` 등)을 쓰는 곳은 투자 배분의 읽기뿐이고(R-55) 쓰는 코드는 찾지 못했다(검색 범위 2.1). `price_provider`가 바뀌면 `first_provider_price_on`을 비운다(같은 저장에서 둘 다 지정하면 그 값). | 코드 확인 |
| R-03 | `Security.find_by_ticker_and_exchange(ticker, mic, country_code, match_blank_mic)` | ticker는 대소문자 무시로 찾는다. MIC가 있으면 정식 MIC와 그 별칭 모두를 같은 장소로 보고 찾으며, 정식 MIC 행을 먼저 고른다. MIC가 비었을 때 `match_blank_mic`가 참이면 MIC가 비어 있는 행만, 거짓이면 MIC를 거르지 않고 첫 행을 쓴다. `country_code`가 있으면 그것으로도 거른다. 찾은 행이 별칭 MIC를 가졌으면 같은 ticker의 정식 MIC 행이 이미 있을 때 그 행을 돌려주고, 없으면 그 행의 MIC를 정식 값으로 고쳐 저장한다. `find_or_initialize_by_ticker_and_exchange`는 못 찾으면 정식 MIC를 넣은 저장 전 새 행을 만든다. | 코드 확인 |
| R-04 | `Security.cash_for(account, currency:)`, `Security#cash?` | 합성 현금 종목을 `(ticker, kind=cash)`로 찾거나 만든다. 통화가 계정 통화와 같거나 비면 ticker `CASH-<account id>`, 다르면 `CASH-<account id>-<통화>`(대문자)이고 이름은 `Cash` 또는 `Cash (<통화>)`, `offline = true`다. 현금 종목은 시세를 가져오지 않는다. 투자 배분은 `cash?`로 현금 칸을 정한다(R-55). 이자·수수료 매매가 종목을 안 골랐을 때 쓴다(R-15). | 코드 확인 |
| R-05 | `Trade`를 저장한다 | `qty`, `price`, `currency`가 있어야 한다. `investment_activity_label`은 nil이거나 13개 값(`Buy`, `Sell`, `Sweep In`, `Sweep Out`, `Dividend`, `Reinvestment`, `Interest`, `Fee`, `Transfer`, `Contribution`, `Withdrawal`, `Exchange`, `Other`) 중 하나다. `exchange_rate=`는 비면 `extra.exchange_rate`를 nil로, 숫자(유한)면 실수로 저장하고 아니면 원래 값과 `exchange_rate_invalid: true`를 저장한다. 검증은 invalid면 "must be a number", 값이 있고 0 이하면 "must be greater than 0"이다. `buy?`는 `qty > 0`, `sell?`은 `qty < 0`. "내부 이동"은 라벨이 `Transfer`·`Sweep In`·`Sweep Out`인 매매이고, `Exchange`는 포함하지 않는다(종목끼리 교환은 이익 실현일 수 있어서). 매매는 예산에서 항상 제외된다. | 코드 확인 |
| R-06 | `Security::Price`·`Security::Split`을 모델로 저장한다 | 시세는 `date`, `price`, `currency`가 있어야 하고 `(security, currency)` 안에서 날짜가 유일해야 한다. 가격이 0 이하라는 검증은 모델에 없다(importer·수동 시세가 따로 거른다). split은 `ex_date`, `source`가 있어야 하고 분자·분모가 양의 정수여야 하고 둘이 같으면 안 되며 `(security, ex_date)`가 유일해야 한다. 주식 수 변환은 `scale(qty, ratio) = round18(qty × 분자 ÷ 분모)`, `unscale`은 분자와 분모를 바꾼 같은 식이다(소수 18자리 반올림, C-02). | 코드 확인 |

**B. 종목 해석과 검색**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 선택지 id `"A\|B\|C"`를 해석한다 | `|`로 최대 3조각으로 나누고 각 조각이 비면 nil로 본다(`ticker`, `exchange_operating_mic`, `price_provider`). 선택지의 id는 `symbol`, `exchange_operating_mic`, `price_provider`를 `|`로 이은 문자열이다(값이 nil이면 빈 칸). 표시 문구는 번역 키 `securities.combobox.display`에 `symbol`, `name`, 거래소 이름을 넣어 만든다. 거래소 이름은 `config/exchanges.yml`에서 MIC로 찾고 없으면 대문자 MIC 자신이다. | 코드 확인 |
| R-08 | `Security.search_provider(symbol, ...)` (`GET /securities`가 부른다) | symbol이 비거나 켜진 provider가 없으면 빈 목록. 켜진 모든 provider를 병렬로 호출하고, 하나당 8초 기한을 공유한다(느린 provider 때문에 빠른 provider의 결과를 잃지 않는다). 각 provider 결과는 provider 키 + 대문자 symbol + `country_code`·`exchange_operating_mic` 해시로 만든 키로 5분 캐시한다(nil 결과는 캐시하지 않는다). provider가 오류 응답, 예외, 시간 초과를 내면 그 provider의 결과는 없는 것으로 보고, `technical_failure` 콜백이 있으면 그 provider로 한 번 호출한다(결과가 비어 있는 정상 응답과 구분). 합친 결과는 `symbol\|MIC\|provider`(대문자)로 중복을 지운다. 같은 종목이 서로 다른 provider에서 나오면 각각 남는다(사용자가 시세원을 고르게 하려는 것). 정렬: (1) 질의가 형식과 체크 숫자가 맞는 ISIN이고 결과 ISIN이 같으면 -1, ticker가 질의와 같으면 0, ticker가 질의로 시작하면 1, 이름에 질의가 들어 있으면 2, 나머지 3. (2) 사용자 국가와 같으면 0, 아니면 1. (3) ticker. 앞 30건만 돌려준다. 질의는 대문자로 비교한다. 결과 각각은 provider 키를 `price_provider`로, provider가 준 `currency`·`isin`을 검색용 임시 속성으로 가진다(저장되지 않음). | 코드 확인 |
| R-09 | `Security::Resolver#resolve` | 생성자: symbol이 blank면 오류, 아니면 앞뒤 공백을 지우고 대문자. MIC는 정식 MIC로 바꾼다. `price_provider`는 registry에 있고 현재 켜져 있을 때만 받고 아니면 nil로 버린다(오류 없음). 해석 순서: (1) DB에서 정확히 일치, (2) provider 검색에서 정확히 일치(MIC가 있을 때만), (3) provider 검색에서 가까운 일치, (4) offline 종목 생성. 앞 단계가 결과를 내면 뒤 단계는 부르지 않는다. 항상 저장된 행을 돌려준다. | 코드 확인 |
| R-10 | Resolver 1단계(DB) | `find_by_ticker_and_exchange(ticker, MIC, country_code)`(R-03)로 찾는다. 행이 offline이고 `offline_reason`이 `resolution_pending`이면 이 단계를 건너뛴다(provider 검색을 다시 시도). 호출자가 `price_provider`를 줬고 행의 값과 다르면 호출자 값으로 바꾼다(연동 sync는 nil을 줘서 기존 선택을 덮지 않는다). 행이 offline이면 다음 조건에서 online으로 되돌린다: 호출자가 `price_provider`를 줬거나 `offline_reason`이 `provider_disabled`·`resolution_pending`이고, 그 종목의 `price_data_provider`가 존재할 때. 되돌릴 때 `offline=false`, `offline_reason=nil`, `failed_fetch_count=0`, `failed_fetch_at=nil`. `health_check_failed` 같은 다른 사유는 사람이 provider를 골라야 풀린다. | 코드 확인 |
| R-11 | Resolver 2·3단계(provider 검색) | 검색은 `(MIC, country_code)`를 그대로 provider에 넘기고 R-08의 결과를 쓴다. 정확 일치: MIC가 있을 때만 시도하고, ticker(대문자)가 같고 MIC가 정식 MIC 기준으로 같고, 국가 코드를 줬으면 결과의 국가가 같거나 비어 있어야 한다. 가까운 일치: 국가 코드가 있으면 같은 국가(결과 국가가 비어 있으면 통과)만 남기고, 정렬 키 (ticker가 같음 0/1, MIC가 같음 0/1, 국가 선호 순위, MIC 선호 순위)의 첫 항목을 쓴다. 국가 선호 순위는 사용자 국가 + 고정 목록 `US CN JP IN GB CA FR DE CH SA TW AU NL SE KR IE ES AE IT HK BR DK SG MX RU IL ID BE TH NO`, MIC 선호 순위는 미국 거래소 위주 고정 목록(C-12)이고 목록에 없으면 가장 뒤다. 일치 결과로 종목을 `find_or_initialize`해서 `country_code`를 쓰고, 이름이 비어 있을 때만 검색 결과 이름을 채우고(덮어쓰지 않음), `price_provider`는 호출자 값이 있으면 그것, 없으면 검색 결과의 provider 키(새 행이거나 아직 provider가 없을 때를 포함해 결과 키가 있으면 쓴다)로 쓴다. 저장 뒤 R-10의 online 복귀 규칙을 적용한다. 정렬 동점의 결과는 정해지지 않는다(U-02). 정확 일치 단계의 국가 조건은 `country_code && MIC`가 참인지로 정하는데 빈 문자열도 참으로 취급해 "줬다"로 본다. | 코드 확인 (동점은 추론) |
| R-12 | 어느 단계도 못 찾았다 | offline 종목을 `find_or_initialize`해서 `country_code`를 쓰고 `offline = true`로 저장한다(시세를 다시 가져오지 않는다는 표시). provider 검색이 오류·시간 초과였으면 `offline_reason = resolution_pending`(이미 더 구체적인 사유가 있으면 덮지 않는다)이고 경고 로그를 남긴다. 검색이 정상으로 끝났는데 일치가 없으면 사유를 비우고, 이전의 `resolution_pending`이면 사유를 지운다(이후 resolve가 DB 경로로 간다). `price_provider`는 건드리지 않는다. | 코드 확인 |
| R-13 | `Security#price_data_provider`, `provider_status` | 종목에 `price_provider`가 있으면 그 provider가 켜져 있고 만들어질 때만 쓰고, 아니면 nil을 돌려준다(다른 provider로 대신하지 않는다. 호환되지 않는 코드를 보내지 않으려는 의도). `price_provider`가 없으면 켜진 provider의 첫 번째다. `provider_status`는 지정한 provider를 쓸 수 없으면 `provider_unavailable`, offline이면 `offline`, provider가 없으면 `no_provider`, `failed_fetch_count > 0`이면 `stale`, 나머지 `ok`다. | 코드 확인 |
| R-14 | securities provider를 켜고 끈다 | 켜진 목록은 환경변수 `SECURITIES_PROVIDERS`가 있으면 그것, 없으면 DB 설정 `securities_providers`, 둘 다 비면 단일 `SECURITIES_PROVIDER`나 DB `securities_provider`(기본 `twelve_data`) 하나다. 쉼표로 나누고 공백을 지운다. `Security.providers`는 목록의 순서대로 provider를 만들고 만들지 못하거나(키 없음) registry에 없으면 건너뛴다. 설정을 바꿔 provider가 목록에서 빠지면 그 `price_provider`를 가진 online 종목을 모두 `offline = true`, `offline_reason = provider_disabled`로 바꾼다. provider가 다시 목록에 들어오면 `offline_reason = provider_disabled`인 offline 종목만 online으로 되돌린다(`failed_fetch_*` 초기화). 설정 화면에서 목록을 모두 비우면 단일 설정 `securities_provider`도 빈 문자열로 지워져 켜진 목록이 빈 목록이 된다. 목록에 넣을 수 있는 값은 registry 키뿐이다(나머지는 버린다). 암호화폐 지갑 연동(`Onchain::SecurityResolver.enable_price_provider!`)도 같은 설정 필드에 `binance_public`을 덧붙이지만 `provider_disabled` 종목을 되살리지는 않는다(되살리기는 설정 화면 경로뿐). | 코드 확인 |
| R-15 | 사용자가 매매를 저장한다(`TradesController#create` → `Trade::CreateForm`) | 계정 쓰기 권한이 필요하다. 이체형이면 상대 계정 권한도 필요하다. 종목: `ticker` 값이 있으면 R-07로 해석해 Resolver(R-09)에 넘기고, 없으면 `manual_ticker`를 MIC·provider 없이 Resolver에 넘긴다(수동 티커도 provider 검색을 거쳐 실제 종목이 될 수 있다). `buy`/`sell`/`sweep_in`/`sweep_out`/`reinvestment`: 종목이 없으면 저장하지 않고 오류. 수량은 `sell`·`sweep_out`이면 음수, 나머지는 양수(절댓값 기준)이고 `Entry.amount = 부호 있는 수량 × price + fee`(매도의 amount는 음수, 수수료는 부호와 관계없이 더한다). 이름은 `Buy`/`Sell` 때 `"<Buy\|Sell> <수량> shares of <ticker>"`, 나머지는 `"<라벨> <수량> shares of <ticker>"`. `dividend`·`interest`·`fee`: `qty = 0`, `price = 0`, `fee = 0`인 `Trade`로 만들고 라벨을 붙인다. `Entry.amount`는 dividend·interest가 `-|amount|`(유입), fee가 `+|amount|`다. dividend는 종목이 필수(해석 실패는 오류), interest·fee는 종목이 없으면 `Security.cash_for(account, currency)`다. 저장에 성공하면 속성 잠금과 사용자 수정 표시를 하고 계정 sync를 예약한다. 매매 수정(`update`)은 `Dividend`·`Interest`의 금액을 다시 음수로 만들고, 수량·가격이 있으면 `nature = inflow`를 매도로 보고 같은 부호 규칙으로 `amount`를 다시 계산하며 라벨이 비었거나 `Buy`·`Sell`이면 방향에 맞게 라벨과 이름을 바꾼다(`fee`는 수정 입력에 없으면 기존 값을 더한다). HTML 생성은 Resolver에 `country_code`를 넘기지 않는다. `interest`·`fee`에서 `ticker` 문자열이 있는데 파싱한 ticker가 비면(`|XKRX|` 같은 값) `security`가 nil이라 `sec.cash?`에서 NoMethodError가 난다(dividend는 rescue해서 오류 항목으로 바꾼다). HTML 폼은 `price` 0을 막지 않는다(존재 검사뿐, API는 R-68). | 코드 확인 (수동 티커가 offline 전용이라는 주석과 구현이 다르다, 2.1) |

**C. 시세 적재**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | `Security#find_or_fetch_price(date: 오늘, cache: true)`(키워드 인자) | 그 날짜의 시세 행이 있으면(통화 구분 없이 첫 행) 그것을 돌려준다. 없고 종목이 offline이면 nil. provider를 정할 수 없으면 nil. 있으면 `fetch_security_price`를 부르고 실패하면 실패 로그(종목당 하루 한 건으로 throttle)를 남기고 nil. 성공이고 `cache`가 참이면 `(security, 반환된 price.date, price.currency)` 행을 없을 때만 만들어 저장하고 provider가 준 Price(저장 행이 아님)를 돌려준다. 반환 날짜가 요청 날짜와 다르면(직전 거래일) 저장도 그 날짜로 하므로 요청 날짜 행은 계속 없고 매 호출이 provider를 다시 부른다. `Trade#unrealized_gain_loss`(R-50)가 오늘 가격으로 이것을 쓴다. | 코드 확인 (반복 호출은 추론) |
| R-17 | `Security::Price::ImportWindows(account, today:).to_h` | 계정의 종목마다 시세가 필요한 구간을 돌려준다. 대상 종목: `account.current_holdings`의 종목, 수동으로 다시 열릴 수 있는 종목(아래), provider 보유가 마지막 매수보다 오래된 종목, 매매가 한 건이라도 있는 종목, 수량 > 0인 보유가 한 번이라도 있던 종목의 합집합. 시작일 = min(첫 매매일(수량 0인 배당·이자 매매도 포함), 수량 > 0인 첫 보유일, provider 보유가 있는 종목이면 `account.start_date`)이고 하나도 없으면 `account.start_date`. 끝날짜: 현재 보유 중(R-39의 current), 수동으로 다시 열릴 수 있는 종목, provider에서 다시 매수된 종목은 `today`, 그 밖에는 max(수량이 0이 아닌 마지막 매매일, 수량 > 0인 마지막 보유일)다. 수동으로 다시 열릴 수 있는 종목: 매매 수량 합이 0이 아니고 provider 보유가 없으며 (보유 행이 없거나 마지막 매매일이 마지막 보유일보다 늦거나 매매·항목 수정 시각이 마지막 보유 갱신보다 늦은 것). 끝날짜를 정할 수 없으면 그 종목은 빠진다. | 코드 확인 |
| R-18 | 시세 적재를 부른다(두 경로) | **계정 기준**(`Account::MarketDataImporter#import_security_prices`): 켜진 provider가 하나도 없으면 아무것도 안 한다. R-17의 구간을 구하고 그중 online 종목마다 `import_provider_prices(start, end)`(R-19) 다음 `import_provider_details`를 부른다. 시세를 환율보다 먼저 가져온다(받은 시세의 통화로 필요한 환율 쌍을 정하기 위해, money-currency-rules R-35). **전체 기준**(`MarketDataImporter`, 모드 `full`·`snapshot`): provider가 없으면 경고 후 끝낸다. 시세가 필요한 모든 계정(보유 행이 있거나 매매 항목이 있는 계정, 계정 상태 무관)의 구간을 종목별로 합쳐(시작은 이른 쪽, 끝은 늦은 쪽) 종목당 한 번 적재한다. `snapshot` 모드는 시작을 최소 31일 전으로 올리고 끝이 31일 전보다 이른 종목은 건너뛴다. `clear_cache`는 그대로 넘긴다. 끝으로 모든 online 종목에 `import_provider_details`를 부른다. `import_provider_details`: provider가 없으면 경고만. 이름이 있고 (로고 또는 웹사이트)가 있고 `clear_cache`가 아니면 provider 호출을 건너뛴다. 아니면 `fetch_security_info`를 부르고 성공이면 비어 있지 않은 `name`, `logo_url`, `links`(→`website_url`)만 덮어쓴다. 이어 로고가 비었으면 T-Invest 로고 provider(토큰이 있을 때만)에서 로고를 채운다(암호화폐 종목은 건너뛴다). 실패는 경고와 진단 로그다. | 코드 확인 |
| R-19 | `Security#import_provider_prices(start_date:, end_date:, clear_cache:)` | provider를 정할 수 없으면 경고 후 정수 `0`을 돌려준다. 있으면 Importer(R-20~R-24)를 실행하고 `[upsert 건수, provider 오류 문자열 또는 nil]`을 돌려준다(반환 형태가 두 가지다). | 코드 확인 |
| R-20 | Importer가 구간을 정한다 | `end_date = min(요청 end_date, 뉴욕 오늘)`. 원본 의도는 뉴욕 시간대의 오늘이지만 같은 식이 `Date#in_time_zone(...).to_date`라 시간대 변환이 일어나지 않고 활성 시간대의 오늘일 가능성이 높다(money-currency-rules R-31과 같은 코드 형태, 추론). `clamped_start = 종목의 first_provider_price_on이 있고 start_date보다 늦으면 그 날짜, 아니면 start_date`. `clear_cache`가 참이면 `effective_start = start_date`, 아니면 `[clamped_start, end_date]` 중 DB 시세가 없거나 다시 받을 provisional 시세(R-23)가 있는 첫 날짜(모두 있으면 `end_date`). provider 요청 시작일 = `effective_start - 7일`, provider의 `max_history_days`가 있고 `end_date`와의 간격이 그보다 크면 `end_date - max_history_days`로 줄인다. gap 채우기 시작일 `fill_start = max(요청 시작일, effective_start)`. `clear_cache`가 거짓이고 (다시 받을 provisional이 없고) `[clamped_start, end_date]`의 DB 시세 행 수가 날짜 수와 같으면 provider를 부르지 않고 0을 돌려준다(통화가 다른 같은 날 행이 있으면 행 수가 더 커져 이 단축이 일어나지 않을 수 있다, 추론, U-01). | 코드 확인 (뉴욕 오늘과 행 수 단축은 추론) |
| R-21 | Importer가 날짜마다 가격과 통화를 고른다 | `fill_start`부터 `end_date`까지 모든 달력 날짜를 한 행씩 만든다. provider 응답은 날짜로 색인한다. 가격이 유효하다는 것은 값이 있고 0보다 큰 것이다. 선택: `clear_cache`이거나 그 날의 DB 행이 provisional이면 provider 값(유효하지 않아도 그대로 후보)과 provider 통화. 그렇지 않고 유효한 DB 값이 있으면 DB 값과 DB 통화(사용자가 고친 값을 보존). 아니면 provider 값과 통화. 고른 가격이 nil이거나 0 이하이면 직전에 쓴 가격과 통화로 채운다(마지막 관측값 이월). 통화가 비면 직전 통화, 그래도 없으면 `USD`다. 가격과 통화는 항상 같은 출처에서 함께 고른다. 어느 날의 통화도 정해지지 않을 때 쓰는 초기 통화는 provider 응답 `values.first`의 통화(응답 순서의 첫 행), 없으면 DB 시세 `values.first`의 통화, 없으면 `USD`다. 그러므로 한 응답 안에서 통화가 섞이거나 일부 행의 통화가 비면 결과가 응답 순서에 달려 있고, 모든 행의 통화가 비면 가격이 KRW 숫자여도 `USD`로 저장된다. | 코드 확인 |
| R-22 | Importer가 시작 앵커를 정한다 | 시작 가격: `fill_start == start_date`면 provider 시세 중 `start_date` 이하에서 날짜가 가장 늦은 행 하나를 먼저 고르고 그 가격이 유효(양수)할 때만 쓴다. 그 행이 무효이면 더 이전의 유효 행으로 거슬러 가지 않고 그 날의 DB 값(유효할 때)으로, 그것도 없으면 없음으로 간다(앵커가 없으면 아래 상장 전 처리로 간다). 아니면 provider 시세 중 `fill_start` 이전 가장 늦은 값, 없으면 DB 시세 중 `fill_start` 이전 가장 늦은 양수·비provisional 값(통화가 정해져 있으면 그 통화). 앵커가 없고 provider 시세 중 유효 값이 있으면(상장 전 요청) 가장 이른 유효 날짜로 `fill_start`를 옮기고 그 값을 앵커로 쓴다. 그 앞 날짜는 DB에 쓰지 않는다(상장 전을 미래 가격으로 메우지 않는다). 옮겼으면 종목의 `first_provider_price_on`을 그 날짜로 쓰되 비어 있거나 더 이른 날짜일 때만이다(앞으로 늦추지 않는다). 앵커가 끝내 없으면 오류 로그와 Sentry 보고를 하고 0을 돌려준다. provider 응답이 비면 경고만 남기고 0이다. | 코드 확인 |
| R-23 | Importer가 `provisional`을 정한다 | provider 값이 유효한 날은 `false`. 이월로 채운 날은 그 날짜가 7일 전 날짜 이상(오늘까지, 양끝 포함해 8개 날짜)이면 `true`, 아니면 `false`. 그 밖에는 기존 값을 유지(없으면 false). provisional이고 날짜가 `7일 전 날짜..오늘`(양끝 포함, 8개 날짜)인 행은 다음 실행에서 다시 받는다(`refetchable`). "7일"은 달력으로 7일 전 날짜부터 세므로 8일이다. provider가 오늘 날짜에 장중 값을 종가로 주면 유효한 provider 값이라 `provisional = false`로 저장되고, 이후 실행은 비provisional DB 행을 그대로 두므로(R-21) `clear_cache` 전까지 그 값에 고정된다. 그래서 provider는 장 마감 전의 오늘 행을 주지 않아야 한다. 주말·휴일의 이월 값이 다음 거래일의 실제 값으로 교체되게 하는 장치다. | 코드 확인 |
| R-24 | Importer가 저장한다·실패한다 | 행을 200건씩 `(security, date, currency)` 기준 upsert하고 전체 건수를 돌려준다. provider 호출이 실패하면(`success? = false`) 응답을 빈 것으로 취급하고 provider 오류 메시지를 `provider_error`에 남기고(호출자가 받는다, R-19), 경고·진단 로그를 남기고, 오류 메시지가 요금제 제한이면 종목별 제한 기록을 남기고(7일 보관), 성공하면 그 기록을 지운다(요금제 제한을 판별하는 provider 클래스 표는 TwelveData 하나뿐이다). 이 경우 `provider_prices`가 비어 있어 0을 돌려준다. 시세가 비어 있어도 R-22의 앵커가 DB 값으로 만들어질 수 있으나 먼저 `provider_prices.empty?`가 걸려 항상 0으로 끝난다. | 코드 확인 |
| R-25 | 사용자 시세 입력(`Security::ManualPriceImport`, API v1 `POST security_prices`) | 대상은 provider가 없는 종목뿐이다(offline이고 `offline_reason`이 비고 `price_provider`가 비어 있을 것. R-26의 건강 점검이 이런 종목도 점검해 실패를 쌓으면 `health_check_failed` 사유가 붙어 이 조건에서 탈락한다). 현금 종목은 불가. 행은 1~1000개, 각 행은 `date`(`YYYY-MM-DD` 형식, 미래 날짜만 거부하므로 오늘은 허용), `price`(양수, 소수 4자리 이하, 10^15 미만), `currency`(통화 표에 있는 코드). 한 요청의 날짜는 서로 달라야 하고 통화는 모두 같아야 한다. 통화는 종목의 기존 시세 통화로 고정되고, 시세가 없으면 호출자 계정의 매매 통화, 그것도 없으면 보유 통화로 정하며 둘 이상이면 오류다. 모든 행을 검증한 뒤 한 번에 upsert하고(오류가 하나라도 있으면 아무것도 쓰지 않는다) `provisional = false`로 쓴다. 종목 행을 잠근 채로 검사와 쓰기를 한다. 생성된 시세는 모든 family가 같은 종목으로 공유하므로 API는 self-hosted 모드에서만 허용한다. 대상 계정은 그 종목을 거래했거나 연동 계정이 그 종목을 보유한 쓰기 가능 계정이고, 저장 뒤 그 계정들의 sync를 예약한다. | 코드 확인 |
| R-26 | 종목 건강 점검(`Security::HealthChecker`, 평일 02:00 job) | 점검 대상은 `kind = standard`인 종목 중 한 번도 점검하지 않은 것(제한 없음)과 마지막 점검이 7일 이상 지난 것(오래된 순, 하루 1000개)이고, `offline` 여부와 `price_provider` 유무는 거르지 않는다. 종목의 provider를 정할 수 없으면(지정 provider가 꺼짐 포함) 실패로 세지 않고 점검 시각만 갱신한다. `price_provider`가 비어 있으면 켜진 첫 provider로 점검한다(R-13). 점검은 `fetch_security_price(오늘)`가 성공하면 성공이다(`AlphaVantage`는 쿼터 때문에 항상 성공으로 본다). 성공이면 `offline = false`, 실패 카운트 0(`offline_reason`은 지우지 않는다). 실패면 `failed_fetch_count`를 1 올리고 기록한다. 카운트가 5를 넘기면(6번째 연속 실패) 종목을 `offline = true`, `offline_reason = health_check_failed`로 바꾸고, 시세 이력이 없을 때만 시세 행을 `delete_all`하는데 이력이 없으니 지울 행이 존재할 수 없다(코드는 있으나 효과가 없다). 이력이 있으면 지우지 않는다. `health_check_failed` 사유가 붙으면 R-25의 "추적되지 않는 종목" 조건에서 빠져 수동 시세 입력이 거부된다. 점검 중 예외는 Sentry로 보내고 삼키며 어떤 경우에도 `last_health_check_at`을 갱신한다. | 코드 확인 |
| R-27 | 사용자가 보유 상세에서 시세 동기화를 누른다(`HoldingsController#sync_prices`) | 종목이 offline이면 안내와 함께 거부. 아니면 `import_provider_prices(31일 전, 오늘, clear_cache: true)`와 `import_provider_details`를 부른다. 저장 건수가 0이면 provider 오류(없으면 일반 문구)와 함께 끝내고 재계산하지 않는다. 아니면 그 종목만 `security_ids`로 한정한 `Balance::Materializer`를 실행한다(계정이 연동이면 reverse, 아니면 forward). | 코드 확인 |

**D. 보유종목 일별 재구성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | 계정의 잔액을 다시 계산한다(`Balance::Materializer`) | Balance 트랜잭션 안에서 가장 먼저 `Holding::Materializer.materialize_holdings`를 실행하고 그 뒤에 잔액을 계산·저장한다(holdings가 Balance의 입력이다). 전략은 연동 계정이면 `reverse`, 수동 계정이면 `forward`다(호출 규칙은 sync-pipeline R-17, 매핑은 `HoldingsController`가 같은 식을 쓴다). `Holding::Materializer`는 (1) 계산(R-32, R-33), (2) 행 저장(R-36), (3) lot 저장(R-44), (4) `forward`이고 `security_ids`가 없을 때 오래된 행 정리(R-37), (5) provider 스냅샷이 가린 계산 행 삭제(R-37), (6) 계정의 holdings 연관 캐시 비우기를 이 순서로 한다. 계산된 holdings의 통화는 항상 계정 통화이고 provider 스냅샷 행은 provider가 준 통화를 그대로 유지한다(R-30). 잔액 쪽이 holdings를 환산하는 방식과 실패 처리(1:1, 건수 보고)는 행 1이 쓴다. | 코드 확인 |
| R-29 | `PortfolioCache`가 종목별 날짜 가격을 만든다 | 대상 종목은 계정 매매의 종목이고 reverse(`use_holdings`)면 계정 holdings의 종목도 더한다. `security_ids`가 있으면 그것과의 교집합. 날짜별 후보 가격 세 종류: 우선순위 1 DB 시세(`account.start_date..오늘`, 모든 통화), 2 매매 가격(수량이 0인 매매는 제외, 배당·이자가 시세를 0으로 덮는 것을 막기 위함이며 가격이 아니라 수량으로 판정), 3 보유 가격(reverse일 때만). 한 날짜에 후보가 여럿이면 우선순위 숫자가 작은 것 하나를 쓴다. 같은 우선순위의 동점(같은 날 같은 종류의 두 통화 시세)은 정해지지 않는다(U-01). 출처를 지정해 조회하면(`source: holding`) 그 출처의 후보만 본다. 종목 캐시에 없는 종목을 조회하면 오류(`SecurityNotFound`)다. | 코드 확인 (동점은 추론) |
| R-30 | `get_price(security, date)`가 가격을 계정 통화로 바꾼다 | 가격이 없으면 nil(그 날 그 종목 행은 만들지 않는다). 있으면 `Money(price, 통화).exchange_to(계정 통화, date)`로 환산한다(money-currency-rules R-21, R-25의 5일 조회와 provider 호출 포함). 환산이 `ConversionError`이면 환산하지 않은 원래 가격 숫자를 그대로 두고 통화 표시만 계정 통화로 바꾼다(1:1, 보고도 없다). 통화 코드가 통화 표에 없으면 `UnknownCurrencyError`(ConversionError가 아님)로 계산 전체가 실패한다(R-67, 추론: 잡는 곳을 찾지 못했다). | 코드 확인 |
| R-31 | 매매를 날짜 순으로 재생한다 | 계정의 매매 항목을 `(date, created_at, 수량 음수 여부, 원래 순번)`으로 정렬한다. 같은 날 같은 `created_at`(일괄 import)이면 매수가 매도보다 먼저다(팔기 전에 사는 것이 가능하도록). `created_at`이 다르면 그 순서를 유지한다. 시세용 매매 가격 후보(R-29)는 이 순서에 의존하지 않도록 따로 `chronological` 순서의 그룹을 쓴다. | 코드 확인 |
| R-32 | forward 계산(`ForwardCalculator`) | 시작 포트폴리오는 계정 매매에 나오는 모든 종목이 수량 0이다. `account.start_date`(첫 항목 전날, 항목이 없으면 어제)부터 오늘까지 하루씩: (1) 그 날 ex-date인 split을 전날 말 수량과 lot 장부에 적용(R-34), (2) 그 날의 매매를 재생 순서(R-31)로 적용(R-40~R-42), (3) 종목마다 그 날 가격(R-29, R-30)이 있으면 `Holding` 데이터 `(수량, 가격, 통화=계정 통화, 금액 = 수량 × 환산 가격, 보유 단가, 단가 모름 표시)`를 만든다. 가격이 없는 날·종목은 만들지 않는다. 수량 0인 행도 만든다. 마지막에 gap을 채운다(R-35). 미래 날짜의 항목(`date > 오늘`)은 재생에 들어가지 않는다는 점은 날짜 루프가 오늘에서 끝나기 때문이다. | 코드 확인 |
| R-33 | reverse 계산(`ReverseCalculator`, 연동 계정) | 시작 포트폴리오는 `PortfolioSnapshot`: 계정에 provider 보유 행이 있으면 가장 최근 provider 날짜의 행들, 없으면 종목별 가장 최근 행. 그 수량을 "오늘의 수량"으로 보고 매매의 종목은 수량 0으로 시작한다. 스냅샷이 오늘보다 오래됐으면 스냅샷 날짜 이후 오늘까지 ex-date인 split의 비율로 수량을 앞으로 보낸다(스냅샷 이후의 매매는 이미 반영된 것으로 가정한다). 오늘부터 `start_date`까지 하루씩 거꾸로: 그 날 말 수량으로 행을 만들고(오늘은 보유 행의 가격만, 과거는 시세 규칙 R-29), 그 날의 매매를 되돌리고 그 날 ex-date인 split을 되돌려(`unscale`) 전날 말 수량을 구한다. 결과는 gapfill(R-35)한다. 보유 단가는 R-43이다. | 코드 확인 |
| R-34 | split을 적용한다 | split은 ex-date의 시가(그 날 매매보다 먼저)에 적용된다. 그 날 매매는 이미 분할 후 주식 수로 기록된 것으로 본다. 계정 `start_date`~오늘 사이의 split만 일별 재구성에 쓰고, 미래 ex-date는 도래하기 전까지 적용하지 않는다. 스냅샷을 앞으로 보낼 때(R-33)만 계정 시작보다 이른 split도 읽는다. 수량·단가 변환은 R-06의 `scale`/`unscale`이고 18자리 반올림이다. 하나의 포지션을 팔고 나서 반올림 때문에 아주 작은 잔량(`1e-12` 이하)이 남는 경우는 lot 장부가 보정한다(R-40). 이 스펙의 범위에서 split 행을 만드는 코드는 찾지 못했다(검색 범위 2.1). | 코드 확인 (split 쓰기 부재는 검색 범위 한정) |
| R-35 | gap을 채운다(`Holding.gapfill`) | 종목별로 가장 이른 행의 날짜부터 오늘까지 모든 날짜를 만든다. 행이 없는 날은 전날 행의 수량·가격·통화·금액·단가를 그대로 이월한다. 그 날이 split ex-date이면 이월하기 전에 전날 행을 분할 후로 바꾼다: 수량은 `scale`, 가격과 단가는 `unscale`, 금액은 `scale된 수량 × unscale된 가격`으로 다시 계산한다. 가격이 더 이상 오지 않는 종목은 마지막 가격으로 오늘까지 이월된다. | 코드 확인 |
| R-36 | 계산한 holdings를 저장한다 | 계정의 기존 행 중 locked·cost_basis 출처가 있는·provider 행·cost_basis가 있는 행만 미리 읽어 둔다. 계산 행마다 키 `(계정, 종목, 날짜, 통화)`로 기존 행을 찾아: (a) 기존 행이 provider 행(`account_provider_id` 있음)이면 건너뛴다(provider 값이 권위). (b) 기본 열(날짜, 통화, 수량, 가격, 금액, 종목, 계정, 갱신 시각)은 항상 upsert한다. 단가 열은 아래 순서로 정한다. ① 기존 행이 `cost_basis_locked`면 단가 열을 건드리지 않는다. ② 계산이 "단가 모름"(이전 이동 입고, R-42)이고 기존 단가가 있으면서 출처가 비었거나 `calculated`이면 단가와 출처를 nil로 지운다(`manual`·`provider`는 남긴다). ③ 조정(R-45)이 갱신이라고 하고 새 단가가 있으면 새 단가와 `calculated`를 쓴다. ④ 아니면 기존 단가가 있고 출처가 `calculated`·`manual`이면 단가 열을 건드리지 않고, 아니면 해당 종목의 가장 최근 provider 단가(그 날짜 이전, 분할 보정, 통화가 다르면 그 날짜 환율로 환산, 환산 실패면 이월하지 않음)를 `provider` 출처로 이월한다. 이월할 값이 없거나 이미 같으면 건드리지 않는다. 일괄 upsert이므로 R-01의 모델 검증은 적용되지 않는다. 2000건씩 나눠 쓴다. | 코드 확인 |
| R-37 | 오래된 행과 가려진 행을 정리한다 | (1) provider 스냅샷이 있는 `(종목, 날짜)`(통화 무관)에 있는 `account_provider_id`가 없는 계산 행을 지운다(같은 포지션이 두 번 세어지지 않도록, provider는 자기 통화로 보고하고 계산 행은 계정 통화이기 때문). (2) 계정의 가장 최근 provider 스냅샷 날짜에, 그 스냅샷에 나온 종목의 provider가 아닌 행을 모두 지운다. (3) `forward`이고 `security_ids`가 없을 때만: 계정에 매매가 없으면 provider가 아닌 모든 행을 지운다. 매매가 있으면 provider가 아닌 행 중 날짜가 `account.start_date`보다 이르거나 종목이 매매에 나오지 않는 행을 지운다. provider 행은 어느 경우에도 지우지 않는다. 그래서 매매로 뒷받침되지 않는 수동 보유 행은 다음 forward 계산에서 사라진다. | 코드 확인 |
| R-38 | `security_ids`로 한정해서 재계산한다(보유 종목 교체, 시세 동기화) | 계산과 lot 저장이 그 종목들에 한정되고(reverse의 스냅샷 재구성은 그 종목의 매매·split만 재생), R-37의 (3) 정리는 하지 않는다. 한정하지 않은 전체 재계산과 같은 행 저장 규칙(R-36)을 쓴다. | 코드 확인 |
| R-39 | "현재 보유"를 정한다(`Account#current_holdings`, `Holding::CurrentForInvestmentAccounts`) | 계정에 provider 행이 있으면 가장 최근 provider 날짜의 provider 행 중 수량이 0이 아닌 것. 없으면 계정 통화인 행 중 종목별 가장 최근 날짜의 행으로서 수량이 0이 아닌 것. 금액 내림차순. 여러 계정을 한 번에 묻는 형태(`CurrentForInvestmentAccounts`)는 provider 날짜를 `updated_at`의 날짜로 정하는 점이 다르다(provider 행이 있는 계정은 그 계정의 provider 행 중 갱신일이 가장 늦은 날짜의 행, 없으면 계정 통화의 종목별 최신 행). `Account#current_holdings_total`은 계정 통화로 환산한 합계이고 환산할 수 없는 행은 0으로 센다(R-61). | 코드 확인 |

**E. 보유 단가와 lot**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | lot 장부(`LotBook`)가 종목 하나의 매매를 받는다 | 알고리즘은 C-01(가격은 계정 통화 기준으로 받는다). 요약: 매수는 가중평균 단가 풀(총비용, 총수량)에 더하고 lot 하나(원천 항목, 취득일, 수량, 단가)를 만든다. 매도는 열린 lot 전체에서 비례로 수량을 줄이고, 풀에서는 현재 평균 단가로 수량을 줄여 평균 단가는 그대로 둔다. 풀의 수량이 0이 되면 풀을 초기화하므로 전량 매도 뒤 재매수는 새 단가로 시작한다. 가진 것보다 많이 팔면 모자란 만큼을 "부족분"으로 기억하고 다음 매수가 그만큼을 먼저 채운다(그 매수는 lot을 덜 연다). 가격이 모르는(nil) 매수가 있으면 평균 단가를 포지션이 전량 청산될 때까지 모름으로 만든다. 이동 입고 수량은 단가를 모르는 lot으로 열리고 풀에는 넣지 않는다. split은 총수량·부족분·lot 수량을 `scale`로, lot 단가를 비율의 역수로 바꾸고 총비용은 그대로 둔다. lot 수량은 소수 18자리로 맞추고 반올림 오차는 마지막 lot에 몰아 합이 포지션과 같게 한다. `average_cost`는 풀 수량이 0이거나 모름이면 nil이다. 보고하는 평균 단가는 lot이 아니라 풀에서 나온다. | 코드 확인 |
| R-41 | 매매의 취득 단가를 구한다(`effective_trade_price`) | 거래일의 환율로 가격을 계정 통화로 바꾼다. 매매 자신의 `extra.exchange_rate`가 있으면 그것을 `custom_rate`로 쓴다(money-currency-rules R-22). 환산할 환율이 없으면 단가는 nil(모름)이고 원래 숫자로 대신하지 않는다. 수량이 양수(취득)인 매매는 수수료도 환산해 `가격 + 수수료 ÷ 수량`을 취득 단가로 한다(수수료가 비용에 들어간다). 수수료 환산이 불가능해도 nil이다. 처분(수량 ≤ 0)의 가격은 단가에 쓰지 않으므로 수수료를 반영하지 않는다. | 코드 확인 |
| R-42 | 내부 이동 매매(라벨 `Transfer`·`Sweep In`·`Sweep Out`, R-05)를 재생한다 | 입고(수량 > 0)는 단가를 모르는 lot을 연다. 그 종목은 포지션 수량이 0 이하로 내려갈 때(이전 수량이 양수였다가 0 이하가 되는 하향 통과)까지 "단가 모름"이다. 이 기간의 행은 `cost_basis_unknown` 표시를 가지고 단가는 nil이다. 출고(수량 ≤ 0)는 매도처럼 현재 평균 단가로 수량만 줄인다. 이동이 아닌 매수와 매도는 평범하게 적용된다. 이미 수량이 0 이하였던 포지션은 하향 통과로 세지 않는다. 같은 날 전량 매도 후 재매수가 있어도 중간 시점에 통과를 감지한다(매매 단위로 수량을 추적하므로). | 코드 확인 |
| R-43 | reverse에서 단가·opening lot을 만든다 | 매매 전체와 split을 날짜순(같은 날 split이 먼저)으로 재생해 (날짜, 평균 단가) 스냅샷을 쌓고(전량 청산 뒤는 nil도 기록해서 청산 구간이 이전 단가를 이월하지 않게 한다) 이동 입고가 열고 닫는 "단가 모름" 구간을 기록한다. 날짜의 단가는 그 날짜 이전의 마지막 스냅샷(이분 탐색), 모름 구간 안이면 nil이다. 스냅샷 수량에서 모든 매매와 split을 거꾸로 되돌려 첫 매매 직전의 수량을 구하고, 그것이 provider가 보고하는데 매매로는 설명되지 않는 몫이므로 단가를 모르는 opening lot으로 연다. 매매 수량의 합이 provider 수량을 넘어(음수 baseline이 `-1e-12` 이하) 열 것이 없으면 그 종목은 "clamped" 표시만 한다. 반올림 오차 범위(`1e-12`) 안의 부족은 clamped로 보지 않는다. 마지막에 열린 lot 합이 provider 수량과 같도록 opening lot(없으면 마지막 lot)에 `1e-12` 이하의 오차를 몰아 넣는다. 미래 날짜의 매매는 오늘의 수량을 설명하지 못하므로 제외한다. | 코드 확인 |
| R-44 | lot을 저장한다(`HoldingLot.store!`) | 계산이 만든 lot을 저장한다. 파생 lot(원천 항목 있음)은 계정 통화 단가로 저장한다. opening lot의 단가는, 원천이 있는 lot이 하나라도 있는 종목이면 계정 통화로 모름(nil)이고, 매매로 전혀 설명되지 않는 포지션이면 provider의 가장 최근 단가(분할 보정)와 그 통화를 쓴다. 파생 lot은 `(계정, 원천 항목)`, opening lot은 `(계정, 종목)`을 키로 upsert하고 키에 없는 기존 행은 지운다. reverse만 opening lot을 저장하고 삭제한다(forward는 열지 못한다). clamped 종목은 수량 0, `clamped = true`인 opening lot이다. 기준 SHA에서 lot을 화면·계산이 읽는 곳은 찾지 못했다(쓰기와 종목 교체 때 이동뿐). | 코드 확인 (읽는 곳 부재는 검색 범위 한정) |
| R-45 | 단가의 출처를 조정한다(`CostBasisReconciler`, 어댑터와 공용) | 우선순위 `manual`(3) > `calculated`(2) > `provider`(1) > 없음(0). provider가 준 단가가 nil이거나 0이면 모름으로 본다. 기존 행이 없으면 들어온 값을 그대로 쓴다. 기존 행이 잠겨 있으면 절대 바꾸지 않는다. 기존 출처가 `manual`이고 잠기지 않았으면 `calculated`만 덮을 수 있다(사용자가 잠금을 푼 것은 다시 계산하겠다는 뜻). 그 밖에는 들어온 출처의 우선순위가 기존 이상이고 들어온 값이 있을 때만 덮는다. 같은 출처·같은 값이면 쓰지 않는다. 결과는 `(단가, 출처, 갱신 여부)`다. | 코드 확인 |
| R-46 | `Holding#avg_cost`를 구한다 | 저장된 `cost_basis`가 "알려진 값"이면 그것(보유 통화 Money)을 쓴다. 알려진 값 = 비어 있지 않고(잠겼으면 0도 유효, 에어드롭용) 잠기지 않았으면 양수. 아니면 매매에서 계산한다: 그 포지션 날짜 이전(포함)의 수량 > 0 매매를 모두 모아 `Σ((가격 × 수량 + 수수료) × 환율) ÷ Σ수량`. 환율은 거래 자신의 `extra.exchange_rate`(숫자 또는 십진 숫자 문자열), 없으면 거래일 같은 날짜의 `exchange_rates` 행(거래 통화 → 계정 통화, 5일 조회나 provider 호출 없음)이다. 거래 통화가 계정 통화와 같으면 1이다. 외화 매수에 쓸 환율이 없거나 0 이하이면 평균 단가는 nil이다. 라벨이 내부 이동인 매수가 하나라도 있으면 nil이다. 매수가 없으면 nil("단가를 모름", 시장 가격으로 대신하지 않는다). 이 계산은 매도와 split을 반영하지 않는다(lot 장부 경로 R-40과 다르다). 환율은 계정 통화 기준으로 결합하고 결과를 `Money(값, 보유 통화)`로 감싸므로 provider 보유 행의 통화가 계정 통화와 다르면 숫자는 계정 통화인데 통화 표시는 보유 통화가 된다. 목록 화면은 한 쿼리로 여러 보유의 값을 미리 계산해 넘기는 경로를 쓰고 결과가 같다. 이 경로의 SQL이 정본이다(C-17). | 코드 확인 |
| R-47 | 사용자가 보유의 단가를 직접 고친다·되돌린다 | 입력은 주당 단가 또는 총액(총액이면 수량으로 나눈다). 주당 단가가 0 이상이고 수량이 양수일 때만 받는다(0은 허용, 빈 값은 불허해 모르는 값이 0으로 잠기는 것을 막는다). 받으면 `cost_basis`, `cost_basis_source = manual`, `cost_basis_locked = true`로 쓴다. 잠금 해제는 `cost_basis_locked = false`만 바꾸므로 다음 계산에서 `calculated` 출처만 덮을 수 있다(R-45). 쓰기 권한이 필요하다. | 코드 확인 |
| R-48 | 보유의 종목을 다른 종목으로 교체한다·되돌린다(`remap_security!`, `reset_security_to_provider!`) | 교체: 선택지 id의 ticker가 비면 거부. `(ticker, MIC)`로 종목을 찾거나 만들고(`Resolver`를 다시 부르지 않고 사용자 선택을 그대로 신뢰), 지정 provider가 있으면 쓰고 `offline = false`, 실패 카운트 0으로 저장한다. 트랜잭션 안에서 계정의 옛 종목 holdings를 모두 처리한다. 새 종목에 같은 `(날짜, 통화)` 행이 이미 있으면 수량·금액을 합치고 가격은 합친 금액 ÷ 합친 수량(수량 0이면 0), 단가는 둘 다 있으면 수량 가중평균(아니면 기존 단가), 합쳐진 행의 `external_id`·`provider_security_id`·`account_provider_id`는 비어 있을 때만 옛 행 것으로 채우고 `security_locked = true`로 잠그고 옛 행을 지운다. 충돌이 없는 행은 `provider_security_id`가 비었으면 옛 종목으로 채우고 종목을 바꿔 `security_locked = true`다. 이어 그 계정의 옛 종목 매매 전부를 새 종목으로 옮기고 lot을 함께 옮긴다(파생 lot은 항상, opening lot은 새 종목에 이미 있으면 버림). 끝나면 새 종목만 `security_ids`로 한정해 재계산한다(R-38). 되돌리기: `provider_security`가 있을 때만. 현재 종목의 매매 전부를 원래 종목으로 되돌린다(주의: 사용자가 원래 그 종목으로 한 매매도 같이 옮겨진다는 한계를 코드 주석이 인정한다). 되돌리는 행은 `security_locked = false`, `provider_security_id = nil`. provider 갱신이 종목을 덮지 못하게 하는 것은 `security_locked`이고(어댑터 R-48), `provider_security_id`는 원래 provider 종목을 기억할 뿐이다. 교체 대상은 `Security.find_or_initialize_by(ticker:, exchange_operating_mic:)`로 정확히 같은 값만 찾는다(대소문자·MIC 별칭 정규화는 저장할 때만 일어난다). `price_provider`는 registry 키인지만 검증하고 켜져 있는지는 확인하지 않는다. 되돌릴 때 opening lot은 `origin_security`가 원래 종목인 것만 옮긴다. | 코드 확인 |
| R-49 | 보유를 삭제한다(`HoldingsController#destroy`) | 계정이 `can_delete_holdings?`(연동이 없거나 모든 provider adapter가 허용)일 때만 허용한다. 허용되면 트랜잭션 안에서 그 계정의 그 종목 매매 항목을 모두 지우고 그 보유 행을 지운 뒤 계정 sync를 예약한다(다른 날짜의 같은 종목 보유 행은 다음 재계산이 정리한다). 아니면 거부 메시지. 쓰기 권한 필요. | 코드 확인 |
| R-50 | 실현·미실현 손익 | **미실현**(`Trade#unrealized_gain_loss`): 매수만, 오늘 시세(R-16)가 있어야 한다. `현재 평가 = 오늘 가격 × |수량|`, `비용 = 가격 × |수량| + 수수료`(통화 환산 없음). **실현**(`Trade#realized_gain_loss`): 매도만이고 내부 이동은 nil. 기준 보유 = 그 종목의 매도 날짜 이전(포함) 가장 최근 holding 행. 그 행의 `avg_cost`(R-46)가 없으면 nil. `비용 = avg_cost × |수량|`, `수익 = 가격 × |수량| - 수수료`를 비용의 통화로 환산한다. 환산은 거래일·같은 방향(매도 통화 → 기준 통화)의 환율 행만 쓰고(5일 조회·역방향·provider 없음), 환율이 없거나 0 이하이면 nil이고 "환산 불가" 표시가 선다(합계 계산자가 빠진 것으로 센다). 같은 통화면 변환 없이 쓴다. | 코드 확인 |

**F. 투자 요약과 포트폴리오 화면**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-51 | `InvestmentStatement`가 계정 집합을 정한다 | `investment_accounts` = family의 계정 중 화면에 보이고(visible) 보고서에 포함된(included_in_reports) `Investment`·`Crypto` 계정. `user`가 있으면 그 사용자가 재무에 포함할 수 있는 계정(`included_in_finances_for`)만. `portfolio_value`는 계정 `balance`를 family 통화로 환산한 합이다(환율이 없는 계정은 0, R-53). `cash_balance`는 계정 `cash_balance`의 환산 합이고 `holdings_value = portfolio_value - cash_balance`다. `cash_balance`·`holdings_value`를 부르는 곳은 이 클래스 안에서 보이지 않았다(검색 범위 2.1). 환율은 오늘 날짜의 `rates_for`로 한 번에 구해 메모한다(계정 통화와 보유 통화 중 family 통화가 아닌 것). | 코드 확인 |
| R-52 | 현재 보유와 일변동 | `current_holdings` = R-39의 다중 계정 형태. 한 번 읽어 메모한다. `holdings_with_avg_costs`는 단가가 저장돼 있지 않은 보유들의 평균 단가를 한 번에 계산해 각 보유에 넘긴다(R-46). 일변동은 같은 계정·종목·통화에서 현재 행보다 날짜가 이른 가장 최근 행과 현재 행의 평가액 비교다. 이전 행이 없으면 일변동 없음. 포트폴리오 일변동은 이전 행이 있는 보유만 family 통화로 환산해 합한다. | 코드 확인 |
| R-53 | family 통화로 환산한다(`convert_to_family_currency`) | 같은 통화면 그대로. 아니면 오늘 환율 맵에서 곱하고 환율이 없으면 0이다(그 금액은 모든 합계에서 빠진다. 1로 세지 않는다). 한 보유의 평가액과 비용은 같은 환율로 같이 환산되므로 환율이 없으면 둘이 함께 빠진다. 같은 클래스의 배분 설명 주석은 "환율이 없는 통화는 1:1"이라고 쓰지만 구현은 0이다(구현이 사실, 2.1). | 코드 확인 |
| R-54 | 종목별로 묶는다(`top_holdings`, `allocation`, `holdings_table_rows`의 공통 기반) | 보유를 종목 id로 묶고, 행 단위로 family 통화 환산 금액이 양수인 보유만 남긴다(음수 행이 다른 계정의 정상 행과 상쇄되지 않게. materializer가 일괄 upsert로 검증 없이 쓰기 때문에 음수 행이 있을 수 있다). 묶음의 값은 남긴 행의 환산 합이고 값 내림차순이다. 비중의 분모는 `max(portfolio_value, 보유 합계)`다(현금이 음수여도 100%를 넘지 않게, `portfolio_value`가 오래돼 0이어도 보유가 보이게). `top_holdings(limit=5)`: 보유 합이 0이면 빈 목록, 아니면 값 순 상위 N개에 `weight = 값 ÷ 분모 × 100`(소수 2자리 반올림)과 묶음의 평가손익 `trend`를 붙인다. `allocation`은 전체 목록(같은 분모)이고 합이 100이 아니라 투자된 몫이다(현금이 나머지). 평가손익 `trend`는 `avg_cost`를 아는 보유만 합산한다(현재가 vs 수량 × 평균 단가를 각각 family 통화로 환산해 합산, 모르는 보유는 양쪽에서 모두 뺀다). | 코드 확인 |
| R-55 | 분류별 배분(`allocation_by`) | 허용 묶음: `asset_class`, `asset_sub_class`, `sector`, `region`, `account`, `currency`, `kind`. 목록 밖의 이름이면 빈 목록(오류 없음). 모든 묶음은 같은 포트폴리오를 잰다: 양수 환산 금액의 보유들 + 각 계정의 "현금" = (계정 `balance`를 family 통화로 환산) - (그 계정 보유 환산 합)이 양수인 것(계정별로 양수만, 한 계정의 마진이 다른 계정의 현금과 상쇄되지 않게). 현금은 `asset_class`에서 `liquidity`, `asset_sub_class`에서 `cash`, `sector`·`region`에서 `unclassified`, `currency`에서 계정 통화, `kind`에서 `cash`, `account`에서 그 계정에 속한다. 보유의 칸은 분류 열 값(비면 `unclassified`)이고 현금 종목(`cash?`)은 열 값과 무관하게 현금 칸이다. `kind`는 현금, 암호화폐(`exchange_operating_mic`이 Binance MIC), 일반으로 나눈다. 금액이 0 이하인 칸은 버리고 칸이 모두 비면 빈 목록, 큰 순으로 정렬하고 비중은 합 대비 소수 2자리 반올림이다. `allocation_children`은 `asset_class` → 하위 분류 → 종목 순으로 한 단계씩 내려가고(다른 묶음은 빈 목록), 하위 분류 이름이 `unclassified`처럼 여러 asset class에서 반복되므로 `parent`로 asset class도 맞춘다. 종목 단계의 현금은 한 행("cash")으로 합쳐 같이 나온다. | 코드 확인 |
| R-56 | 보유 표(`holdings_table_rows(sort, dir)`) | 종목 하나가 한 행이고(계정을 가로질러 묶음) 수량 합, 알려진 단가 보유만의 평균 단가·평가손익, 모르는 보유가 하나라도 있으면 `missing_cost_basis`, 비중(R-54와 같은 분모), 일변동을 가진다. 정렬 키는 `value`·`weight`·`return`·`day_change`·`name`, 방향은 `asc`·`desc`이고 잘못된 값은 각각 `value`, `desc`로 대체한다. 정렬 값이 없는 행(수익·일변동이 없는 행)은 방향과 관계없이 맨 뒤이고, 동점은 이름(소문자), 종목 id 순이다. | 코드 확인 |
| R-57 | 기간 합계(`totals(period)`) | 계정 집합(R-51)의 항목 중 기간의 날짜이고 `excluded = false`인 것을 family 통화로 환산해(항목 날짜의 환율, `rate_sql`, 환율이 없는 항목은 NULL이라 합에서 빠진다) 집계한다. 대상은 `Trade` 전부와, 라벨이 `Dividend`·`Interest`인 보류가 아닌 `Transaction`이다. `contributions` = 수량 > 0이고 배당·이자 라벨이 아닌 매매의 `|amount × 환율|` 합, `withdrawals` = 수량 < 0이고 배당·이자 라벨이 아닌 매매의 같은 합, `dividends`·`interest` = 해당 라벨의 `amount × 환율` 합의 음수(부호 있는 합이므로 유입 취소 등은 줄어든다), `trades_count` = 매매 수. 계정 집합이 비면 모두 0. 결과는 (family 통화, 계정 집합 해시, 기간, 항목 변경 버전, 환율 최신 갱신 시각, 사용자)를 키로 캐시한다. 누적 기여·배당·이자는 전체 기간 합이다. | 코드 확인 |
| R-58 | 기간 수익률(`period_return_trend`) | 계정 집합이 비면 nil. 기간 중 계정(상태 draft·active)의 일별 `net_market_flows`를 `rate_sql`로 환산해 합한 값이 절대 수익이다. 기준 시작 값은 계정별로 기간 시작 이전 가장 최근 `balances` 행의 `end_balance`를 환산한 합이다. 시작 값이 0이면 nil. `Trend(현재 = 시작 값 + 절대 수익, 이전 = 시작 값)`이다. 환율이 없는 행은 0으로 합산한다. `net_market_flows`를 만드는 것은 잔액 계산(행 1)이다. | 코드 확인 |
| R-59 | 포트폴리오 화면(`GET portfolio`) | 미리보기 기능을 켠 사용자만 접근한다(아니면 대시보드로 보내고 안내). 요청마다 `as_of = 오늘`을 한 번 정해 모든 섹션에 넘긴다. 섹션은 레지스트리가 정하고 내장은 `accounts` 하나(계정별 잔액 카드, 투자 계정이 있을 때만 보임). 투자 계정이 하나도 없으면 빈 화면. 사용자의 섹션 순서 설정을 따르되 설정에 없는 섹션은 선언 순서로 뒤에 붙인다. 순서·접힘 설정 저장은 `portfolio` 키 아래 허용된 섹션 키만 받고 형식이 틀리면 거부한다. 화면이 보이는 수치는 `InvestmentStatement`(R-51~R-58)와 계정 잔액 카드다. | 코드 확인 |
| R-60 | `Portfolio::Xirr`, `Portfolio::FlowClassifier`의 사용처 | 기준 SHA에서 `app`·`lib`·`config`·`db` 안에서 `Xirr`는 정의 파일 밖에서 쓰이지 않고, `FlowClassifier`는 `InvestmentStatement::Totals`의 주석에만 이름이 나온다. 투자 요약의 합계(R-57)는 분류기를 거치지 않고 자체 SQL로 집계한다. 두 클래스는 이 스펙의 동작에 영향을 주지 않는 미연결 코드다. | 코드 확인 (검색 범위 2.1) |

**G. 환산 실패 정책**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-61 | 이 스펙의 계산이 환율 없음(`ConversionError` 또는 환율 NULL)을 만난다 | 호출처마다 다르다. 아래가 이 스펙 범위의 전부다(money-currency-rules R-42의 호출처 목록 중 이 기능 몫). 1:1(환산하지 않은 숫자를 계정 통화로 표기): 일별 재구성의 시세 환산(R-30)과 `Holding#amount_in_account_currency`의 기본값, `Holding#weight`. 0(합계에서 제외): `Account#current_holdings_total`(`unconvertible: 0`을 넘김), `InvestmentStatement`의 모든 환산(R-53), 기간 합계·수익률의 SQL(R-57, R-58은 `rate_sql`의 NULL이 합에서 빠짐). 모름(nil): 보유 평균 단가의 SQL 경로(R-46), lot 장부 경로의 매수 단가(R-41, 평균 단가가 청산 전까지 모름), 실현 손익(R-50, 환산 불가 표시), provider 단가 이월(R-36). 한 식 안에서 정책이 섞이는 곳이 있다: `Holding#weight`는 분자(`amount_in_account_currency`, 1:1)와 분모의 `current_holdings_total`(0)이 서로 다른 정책이다. 분모는 `max(account.balance, current_holdings_total, 분자)`이고 양수가 아니면 100이 아니라 1을 돌려준다(`holding.rb:41-50`). 잔액 계산이 보유를 1:1로 환산하고 건수를 보고하는 것은 행 1(`Balance::SyncCache`)이 쓴다. 호출처마다 하나의 통일 규칙은 코드에 없다. | 코드 확인 (이 스펙 범위의 호출처만) |

**H. 부동산 시세 갱신**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-62 | `SyncPropertyValuationsJob.perform(property_id: nil, force: false)` | `Sync`를 쓰지 않는 독립 job이다. 대상은 `avm_provider`가 있는 부동산(`property_id`가 있으면 그 하나), 마지막 갱신이 가장 오래된 순(갱신한 적 없는 것이 먼저)이다. 부동산마다 아래를 차례로 검사하고 걸리면 요청을 쓰지 않고 다음으로 간다: 계정이 active가 아님(조용히 건너뜀), 이번 실행에서 그 provider가 rate limit에 걸림, provider 키가 registry에 없음, `force`가 아닌데 `avm_last_synced_on`이 오늘 - 갱신 간격보다 늦음, 주소·식별자가 미비하거나 provider 국가 밖(`lookup_ready?`, 경고 기록), provider를 만들 수 없음(API 키가 사라짐, 경고 기록), provider의 월 요청 예산이 소진됨, 계정 통화가 provider의 평가 통화와 다름(경고 기록, 잘못된 통화로 잔액이 오염되지 않게). provider 인스턴스는 키마다 한 번만 만든다(요청 간격 throttle이 인스턴스에 있어서). 부동산마다 예외가 나면 기록하고 다음 부동산으로 계속한다. | 코드 확인 |
| R-63 | 평가 요청이 끝난다 | 주소 필드(줄1, locality, region, 우편번호)와 provider가 요구하면 `external_id`, 사용자가 면적을 직접 입력했고 provider가 지원하면 `square_footage`를 넘긴다. 성공이면 트랜잭션 안에서 `account.set_current_balance(평가액)`(행 1)을 실행하고 실패하면 롤백, 이어 평가 항목 이름을 정하고 `avm_last_synced_on = 오늘`을 쓴다. 잔액 갱신이 실패하면 그 내용을 기록한다. provider 실패면 응답 오류가 그 provider의 rate limit 오류 클래스일 때 그 provider를 이번 실행에서 멈추고(다음 실행까지 더 부르지 않음), 어느 경우든 기록한다. | 코드 확인 |
| R-64 | `property_valuations` provider 인터페이스(`Provider::PropertyValuationConcept`) | registry의 `property_valuations` 키는 `rentcast`, `realie`, `chimnie`이고 API 키가 있어야 만들어진다. 구현체는 `MAX_REQUESTS_PER_MONTH`, `RateLimitError`, `fetch_property_valuation(line1:, locality:, region:, postal_code:, external_id:, square_footage:)`(→ Response, `data`: `PropertyValuation(valuation, currency, property_type, year_built, area_value, area_unit, external_id?, valuation_low?, valuation_high?, confidence?)`)를 가져야 한다. 클래스 수준 능력 메서드(키 없이 확인할 수 있게): `valuation_currency`(기본 `USD`), `supported_country`(기본 `US`), `requires_external_id?`(기본 false), `accepts_square_footage?`(기본 false), `required_address_fields`(기본 줄1·locality·region·우편번호), `refresh_interval`(기본 1일). `lookup_ready?(address, external_id)`: 주소가 없거나 필수 필드가 비었거나 외부 식별자가 필요한데 없으면 false, 국가가 비어 있으면 통과, 아니면 지원 국가의 별칭 목록(US: US/USA/UNITED STATES/UNITED STATES OF AMERICA, GB: GB/UK/GBR/UNITED KINGDOM/GREAT BRITAIN, 마침표 제거 후 대문자 비교)에 있어야 true. 월 예산은 DB 카운터로 세어(캐시가 아님) 한도를 넘으면 증가분을 되돌리고 rate limit 오류를 낸다. 한도는 환경변수 `<PROVIDER>_MAX_REQUESTS_PER_MONTH`로 올릴 수 있다. | 코드 확인 |
| R-65 | 갱신 일정과 연결 | cron이 매월 1일 01:30에 job을 실행한다. 사용자가 부동산에 provider를 연결하면(`link_avm_provider!`) 원자적으로 `avm_provider`를 채우고 `avm_last_synced_on`을 비운다. 연결 가능 조건은 부동산에 provider가 아직 없고, 주소에 국가가 있고, provider가 외부 식별자를 요구하지 않고(Chimnie 같은 식별자 기반 provider는 연결 불가), 계정 통화가 provider의 평가 통화와 같고, `lookup_ready?`인 것이다. 연결하면 `force: true`로 job을 동기 실행(`perform_now`)해 첫 평가를 받고, 그 뒤에도 `avm_last_synced_on`이 비어 있으면 `avm_provider`를 다시 비워 연결을 되돌린다. 갱신 간격은 provider가 정하며(기본 1일, Chimnie는 한 달) 월 1회 cron에서는 `force: true`인 사용자 즉시 갱신에서만 의미가 있다. job 중복 실행은 큐의 unique lock이 막는다(gem 규칙은 미열람). | 코드 확인 (lock은 추론) |

**I. securities provider 인터페이스 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-66 | 새 provider를 securities concept에 붙인다 | provider는 `Provider`를 상속하고 `SecurityConcept`의 네 연산을 구현해야 한다(구현하지 않으면 `NotImplementedError`). 모든 공개 연산은 `with_provider_response`로 감싸 블록 반환값이 `data`가 되게 하고, 예외는 `Response(success? = false, error)`로 바뀌어 호출자에게 간다(Faraday 오류는 응답 본문을 `details`로 보존). registry의 securities 키 목록에 등록하고, 생성 메서드(API 키가 있으면 만들고 없으면 nil)와 설정 필드(키는 암호화 필드)를 추가해야 `Security.price_provider`가 받아들이고 설정 화면에서 켤 수 있다. 호출자는 `search_securities`의 결과에서 `currency`·`isin`을 `respond_to?`로 확인해서 읽으므로 이 두 필드가 없는 값 객체도 동작한다. 선택 연산: `max_history_days`(R-20), `healthy?`와 `usage`(관리 화면용, 이 스펙은 읽지 않았다). provider 키는 클래스 이름의 마지막 조각을 snake_case로 바꾼 값(`Provider::YourProvider` → `your_provider`)이고 이것이 검색 결과의 `price_provider`와 중복 제거 키가 되므로 클래스 이름이 registry 키와 같아야 한다. 등록에는 설정 화면의 허용 파라미터, provider 선택 화면, 번역 키도 필요하다(문서 Step 4~5, 해당 파일은 열지 않음). | 코드 확인 |
| R-67 | provider가 돌려주는 값에 대한 호출자의 가정 | (a) 가격은 양수이고 거래일이 아닌 날은 행 자체가 없거나 가격이 비어 있어야 한다(0 이하와 nil은 무효로 이월 처리, R-21). (b) `currency`는 통화 표에 있는 3자 코드여야 한다. 모델은 존재만 검사하고(R-06) 표에 없는 코드는 나중에 `Money`를 만들 때 오류가 난다(R-30). 소문자 코드는 `Money`가 받지만 holdings 키와 비교 일부가 문자열 일치라서 대문자 코드가 안전하다(추론). (c) `exchange_operating_mic`는 ISO 10383 코드로 매핑해서 돌려줘야 한다. 목록에 없는 거래소 이름은 raw 문자열이 MIC로 저장된다(Yahoo의 매핑 기본 분기가 대문자 raw 값을 돌려준다). (d) 반환 날짜가 요청 날짜와 다를 수 있다(R-16). 단건 조회에서 쉬는 날에 직전 거래일을 돌려주는 구현(Yahoo, 10일 구간 조회)과 오류로 끝내는 구현(EODHD, 구간이 하루)이 둘 다 있고, 건강 점검(R-26)은 오늘 날짜로 단건 조회를 해서 성공해야 하므로 후자는 쉬는 날 점검이 실패한다. (e) 구간 응답은 날짜로 색인되므로 행 순서는 날짜별 가격 선택에 영향이 없다. 단 초기 통화는 응답 첫 행의 통화라서 모든 행에 통화를 채운다(R-21). (f) 가격 소수 자릿수는 4자리로 저장된다(R-06의 열). 다른 통화 단위(영국 펜스 등)의 소수 단위 통화는 provider가 큰 단위로 바꿔서 줘야 한다(Yahoo는 `GBp`, `ZAc`를 변환한다). (g) provider 객체 안에서 `Security`라는 이름은 값 객체(`SecurityConcept::Security`)를 가리키고 모델은 `::Security`다. (h) 오늘 날짜의 행은 장 마감 뒤의 확정 종가여야 한다(R-23, 장중 값은 고정된다). (i) 검색이 돌려준 `symbol`은 그대로 `ticker`로 저장되고 이후 모든 조회에 같은 값이 `symbol:`로 넘어온다. 접미사가 붙은 심볼(`005930.KS`)을 검색이 주면 조회가 그 형태를 받아야 하고(Yahoo는 접미사가 이미 있으면 그대로 통과), `(ticker, MIC)`가 유일 키라서 같은 회사를 접미사 있는 형태와 없는 형태로 저장하면 종목이 둘이 된다(R-02, R-03). (j) `Price.date`는 시각 없는 날짜, `price`는 decimal로 바꿀 수 있는 숫자, `SecurityInfo.links`는 문자열(그대로 `website_url`), `SecurityInfo.kind`는 `import_provider_details`가 읽지 않는다(검색 범위 2.1). 현지 거래일 대 UTC 날짜 규칙은 코드에 없다(U-05). (k) 가격의 분할 조정 여부는 코드가 정하지 않는다(U-03). (l) 통화가 틀리거나 비면(`USD`로 저장) 필요한 환율 쌍이 그 통화로 정해진다. 환율 쌍은 저장된 시세의 통화에서 정해지고(R-18, money-currency-rules R-35) 적재하는 쪽은 `Account::MarketDataImporter`이지 provider가 아니다. | 코드 확인 (b의 소문자·d의 반복 호출은 추론) |
| R-68 | API v1 `trades`·`securities`·`security_prices` | **trades**: 읽기 필터 `account_id`, `account_ids`, `start_date`, `end_date`. 생성은 계정이 매매를 지원해야 하고(투자 또는 암호화폐 거래소 계정) `type`이 `Trade::CreateForm` 지원 목록이어야 한다. 종목은 `security_id`(저장된 종목을 `<ticker>\|<MIC>`로 바꿔 Resolver를 거침, provider 선택은 없음), `ticker`(선택지 id 형식), `manual_ticker` 중 하나가 필수다(입출금형 제외, interest·fee는 없으면 현금 종목). 매수·매도형은 `qty > 0`과 `price > 0`을 강제하고(HTML 폼은 `price` 0 허용), 금액형은 양수 금액이어야 하며, 라벨을 주면 `type`의 라벨과 같아야 한다. 수정은 `qty`·`price`가 있으면 `amount = 부호 수량 × price`로 다시 계산해 수수료를 더하지 않는다(HTML 수정 R-15는 수수료를 더한다). 방향은 `type`/`nature`가 `sell`·`sweep_out`·`inflow`면 매도다. 삭제는 항목을 지우고 계정 sync를 예약한다. **securities**: 읽기 전용이고 접근 가능한 계정의 보유·매매에 나오는 종목만 보이며, 필터는 `ticker`(대소문자 무시), `exchange_operating_mic`(대문자), `kind`, `offline`이다. **security_prices**: 읽기 필터 `security_id`(uuid), `currency`, `start_date`, `end_date`, `provisional`, 쓰기는 R-25. | 코드 확인 |
| R-69 | 사용처가 없거나 일회성인 코드 | `Holding::CostBasisTracker`는 `LotBook`의 빈 하위 클래스이고 `app`·`lib`·`config` 안에서 정의 파일 밖의 사용처를 찾지 못했다. `Security::WarsawPriceCurrencyBackfill`은 rake task(`lib/tasks/securities.rake`)가 쓰는 일회성 보정으로, 통화 없이 `USD`로 저장된 폴란드(PLN) 시세의 통화를 PLN으로 고치고 같은 날 PLN 행이 이미 있으면 USD 행을 지운다(원인: EODHD 검색 캐시가 만료되어 통화를 못 찾은 시세가 `USD`로 저장됨, R-21). 새 구현에는 필요 없고 통화 누락 방지 근거로만 읽는다. | 코드 확인 (사용처 부재는 검색 범위 한정, 2.1) |

- 불변식: `holdings`의 `(account, security, date, currency)`와 `security_prices`의 `(security, date, currency)`는 DB가 유일을 보장한다. 계산된 holdings의 `currency`는 항상 계정 통화다(R-30, provider 스냅샷 행 제외). 보유 단가는 `manual` > `calculated` > `provider` 순으로만 덮이고 잠긴 값은 어떤 경로도 덮지 못한다(R-36, R-45). 미래 날짜의 시세·보유 행을 일별 재구성이 만들지 않는다(날짜 루프 상한이 오늘).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-20, R-29 | 한 종목의 같은 날짜에 통화가 다른 시세 행이 둘 있을 때 어느 행이 쓰이는가 | 일별 재구성이 `Security::Price.where(...)`를 정렬 없이 읽고 같은 우선순위 동점에서 `min_by`가 첫 항목을 고른다. 정렬이 없어 어느 통화가 이기는지 DB의 반환 순서에 달려 있다. importer의 `db_prices`도 날짜로만 색인해 한 행이 다른 행을 덮는다. 같은 종목의 provider를 바꿔 통화가 달라진 경우에 생길 수 있다 | 같은 종목의 두 통화 시세를 가진 DB에서 `PortfolioCache`를 돌려 보거나 원본 테스트에서 그 사례를 찾는다(이번에는 실행·테스트 열람을 하지 않음) |
| U-02 | R-08, R-11 | 정렬 키가 모두 같은 검색 결과(같은 ticker와 MIC를 서로 다른 provider가 줄 때)의 순서와, 그에 따른 `price_provider` 선택 | 정확 일치 단계는 결과의 첫 항목을 쓰고 가까운 일치는 정렬 후 첫 항목을 쓴다. 언어 기본 정렬이 안정적이라는 보장이 없어(Ruby의 `sort_by`) 동점의 승자가 정해지지 않는다. 호출자가 `price_provider`를 안 준 자동 해석(수동 티커, 가져오기)에서 어느 provider가 저장되는지에 영향 | 동점 사례를 만들어 실행해 보거나 Ruby `sort_by`의 안정성 문서를 확인한다(이번에는 실행하지 않음) |
| U-03 | R-67 | provider가 주는 과거 종가가 분할 조정된 값이어야 하는가, 분할 전 실제 가격이어야 하는가 | 일별 재구성은 수량을 `security_splits` 행으로 조정하고 가격은 provider 값을 그대로 쓴다(R-34). split 행을 쓰는 코드가 기준 SHA에 없어서(R-34) split 표는 비어 있을 수 있고, 그때 조정 종가를 쓰면 과거 수량은 그대로인데 가격만 조정돼 과거 평가액이 틀어진다. 반대로 실제 가격을 쓰면서 split 행이 없으면 분할일에 평가액이 불연속이 된다. 어느 쪽을 가정했는지 코드와 주석에 없다 | 원본 테스트·이슈에서 split 행의 출처와 provider 가격 가정을 찾는다(이번에는 열지 않음) |
| U-04 | R-03, R-09 | MIC 없이 ticker만으로 DB를 조회할 때(수동 티커, 연동 해석) 같은 ticker의 서로 다른 MIC 행이 여럿이면 어느 행이 선택되는가 | `match_blank_mic`가 거짓이면 MIC를 거르지 않고 정렬 없는 `first`로 고른다(`security.rb:216-227`). Rails의 `first`는 정렬이 없으면 기본 키(uuid) 순이라 같은 DB에서는 반복되지만 의미 있는 기준이 아니다(추론). 한국 종목처럼 같은 코드가 여러 거래소 행(`XKRX`, Yahoo raw MIC, 접미사 형태)으로 있을 때 어느 행의 시세가 쓰일지에 영향 | 같은 ticker의 두 MIC 행을 둔 DB에서 해석을 실행하거나 Rails `first`의 정렬 규칙을 확인한다(이번에는 실행하지 않음) |
| U-05 | R-21, R-67 | provider의 `Price.date`가 거래소 현지 거래일인가 UTC 날짜인가 | 인터페이스는 시각 없는 날짜만 받고 기준 시간대를 정하지 않는다. Yahoo는 타임스탬프를 UTC 날짜로 바꾼다(`yahoo_finance.rb:372`). 현지 거래일과 UTC 날짜가 다른 시장에서는 하루 어긋날 수 있다(KRX 개장 09:00 KST는 같은 날짜 00:00 UTC라 어긋나지 않는다, 추론) | 시장별로 provider가 주는 날짜 기준을 확인한다(외부 자료, 미확인) |

- 확인 한계: (1) 데이터베이스가 `numeric(19,4)` 열에 소수 5자리 이상 값을 넣을 때의 반올림 방식(Float 입력 포함)은 레포 밖 의미라 열람하지 않았다(money-currency-rules R-02의 같은 한계). 가격은 4자리로 저장된다는 것까지만 코드로 확인했다. (2) `Concurrent::Promises`의 시간 초과 동작(`future.value(0)`이 nil), `Rails.cache.fetch`의 `skip_nil`, 큐 unique lock은 gem 의미에 기댄 것이라 소스를 열지 않았다. (3) 외부 provider(Yahoo, EODHD 등)의 실제 응답은 확인하지 않았고 코드가 그렇게 가정한다는 것만 확인했다. 한국 시장 관련 외부 사실(Yahoo의 `.KS`·`.KQ` 접미사, EODHD의 KOSDAQ 코드)은 `미확인`으로 적용 메모에 표시했다. (4) `Date.current`가 사용자 시간대인지는 요청·sync 문맥의 시간대 설정에 달려 있고 열지 않았다(money-currency-rules 1.4와 같은 한계). (5) 원본 테스트는 열지 않았다.

### 1.5 필수 코드 참조 [필수]

AGPL-3.0 레포이므로 코드를 복사하지 않고 위치만 가리킨다(overview 1절). 아래는 글보다 코드가 짧고 정확한 규칙이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/holding/lot_book.rb:28-181` `Holding::LotBook` | lot 장부 전체: 매수·매도·이동 입고·split, 부족분, 풀 초기화, 반올림 보정, `average_cost`, `settle_opening`. 알고리즘이 자기완결적이라 코드가 정본이다. | R-40, R-42, R-43 |
| C-02 | `app/models/security/split.rb:17-47` `Security::Split` | 비율(`Rational(분자, 분모)`)과 `scale`·`unscale`(수량 × 분자 ÷ 분모, 소수 18자리 반올림), `QTY_SCALE = 18`. | R-06, R-34, R-35, R-40 |
| C-03 | `app/models/holding/trade_calculator_helpers.rb:38-62` `effective_trade_price`, `convert_to_account_currency` | 취득 단가에 수수료 포함, 거래일 환율과 `custom_rate` 우선, 환산 실패 시 nil. | R-41 |
| C-04 | `app/models/holding/cost_basis_reconciler.rb:16-66` `reconcile`와 `app/models/holding.rb:230-245` `cost_basis_replaceable_by?` | 출처 우선순위 조정(상수는 `holding.rb:7-12`). | R-45 |
| C-05 | `app/models/holding/gapfillable.rb:5-82` `gapfill`, `carry_through_split` | gap 채우기와 split 통과 이월. | R-35 |
| C-06 | `app/models/holding/portfolio_cache.rb:119-122` `trades` | 매매 재생 정렬 키(날짜, 생성 시각, 처분 여부, 순번). 가격 후보 우선순위는 R-29의 글이 설명한다(`:157-236`). | R-29, R-31 |
| C-07 | `app/models/security/price/import_windows.rb:9-96` `ImportWindows#to_h` | 종목별 시세 필요 구간(대상 종목과 시작·끝 날짜의 집합식과 SQL 집계). | R-17 |
| C-08 | `app/models/security/price/importer.rb:19-149`, `:154-376` `Security::Price::Importer` | 구간 계산, 일별 선택·이월, 앵커, provisional, upsert 전체. R-20~R-24는 요약이고 코드가 정본이다. | R-20~R-24 |
| C-09 | `app/models/holding/forward_calculator.rb:28-137` `calculate`, `apply_splits`, `apply_trades`, `build_holdings` | forward 일별 걷기. | R-32, R-34, R-42 |
| C-10 | `app/models/holding/reverse_calculator.rb:36-131`, `:133-289` | reverse 걷기, 스냅샷 전진, 단가 스냅샷·모름 구간·opening lot, 단가 조회. | R-33, R-43 |
| C-11 | `app/models/holding/materializer.rb:15-44`, `:54-100`, `:102-241`, `:243-275`, `:281-363`, `:365-380` | 저장 순서, 단가 분기, 정리·purge. | R-28, R-36, R-37, R-38 |
| C-12 | `app/models/security/resolver.rb:14-21`, `:47-88`, `:90-206`, `:208-266`, `:270-307` | 해석 순서, DB 단계, provider 단계, online 복귀, 국가·MIC 선호 목록. | R-09~R-12 |
| C-13 | `app/models/security.rb:14-20`, `:201-252` | MIC 별칭표와 `find_by_ticker_and_exchange`. | R-02, R-03 |
| C-14 | `app/models/security/provided.rb:31-38`(캐시 5분, 최대 30건, 기한 8초 상수), `:48-115`, `:124-142`, `:144-158`(ISIN 판정), `:168-191` | 병렬 검색, 캐시 키, 중복 제거, 정렬. | R-08 |
| C-15 | `app/models/provider/security_concept.rb:1-40`와 `app/models/provider.rb:1-75` | provider 값 객체 세 가지, 인터페이스 메서드 이름, `Response`와 오류 변환. | R-66, R-67 |
| C-16 | `app/models/provider/eodhd.rb:26-97`, `:314-340`와 `app/models/provider/yahoo_finance.rb:582-633`, `:1133-1201`, `:1203-1257` | 대표 provider 두 개의 MIC·통화 매핑표와 심볼 조립 방식(예시). 한국 거래소가 어디에 있고 어디에 없는지가 이 줄들에 있다. | R-66, R-67, 적용 메모 |
| C-17 | `app/models/holding.rb:88-174`, `:418-446` | 평균 단가 SQL(환율 결합, 합계, 모름 판정)과 내부 이동 제외. | R-46 |
| C-18 | `app/models/investment_statement.rb:421-427`, `:575-588`, `:755-781` | 환산(없으면 0), 계정별 양수 현금, 분모와 종목 묶음. | R-53~R-55 |
| C-19 | `app/models/investment_statement/totals.rb:73-110` | 기간 합계 SQL(환율 곱, 라벨 판정, 보류 제외). | R-57 |
| C-20 | `app/jobs/sync_property_valuations_job.rb:15-113` | 부동산 시세 갱신의 건너뛰기 순서와 쓰기. 짧고 자기완결적이라 코드가 정본이다. | R-62, R-63 |
| C-21 | `app/models/provider/property_valuation_concept.rb:14-148` | 평가 provider의 능력 메서드와 `lookup_ready?`, 월 예산. | R-64 |
| C-22 | `app/models/security/health_checker.rb:12-17`, `:27-45`, `:61-67`, `:87-90`, `:108-177` | 점검 대상 선정 상수, 성공·실패, offline 전환. | R-26 |
| C-23 | `db/schema.rb:1193-1236`, `:2352-2388`, `:2405-2429`, `:2840-2854` | `holding_lots`, `holdings`, `securities`, `security_prices`, `security_splits`, `trades`의 열과 제약(1.3의 표와 일치해야 하는 정본). | R-01, R-02, R-06 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(원본 테스트는 열람하지 않음). 금액은 예시 값이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-29, R-32 | KRW 계정, 첫 항목이 2026-11-02 매수 `005930`/`XKRX` 10주 가격 70,000(계정 `start_date`는 11-01). DB 시세: 11-02 71,000 KRW, 11-03 72,000 KRW. 11-01 시세는 없음. | 11-01 행은 없다(가격 없음). 11-02 수량 10, 가격 71,000(DB 시세가 매매가보다 우선), 금액 710,000. 11-03 가격 72,000. DB 시세가 11-02에 없었다면 11-02 가격은 매매가 70,000이다. |
| T-02 | R-30, R-61 | USD 계정, 보유 종목의 시세가 KRW이고 KRW→USD 환율이 5일 안에도 provider에도 없다. | 계산은 오류 없이 끝나고 행의 통화는 USD, 가격은 환산하지 않은 KRW 숫자(예 70,000), 금액 700,000이다(1:1). 보고는 이 단계에서 없다. |
| T-03 | R-40 | 계정 통화 기준: 매수 10주 @100, 매수 10주 @200 → 매도 5주 → 매도 15주 → 매수 1주 @300. | 두 번째 매수 뒤 평균 단가 150, 수량 20. 매도 5주 뒤 평균 150, 수량 15. 15주 매도로 수량 0이 되어 평균 nil(풀 초기화). 마지막 매수 뒤 평균 300, 수량 1. |
| T-04 | R-42 | 매수 1주 @30,000 → `Transfer` 라벨로 1주 입고 → 1주 매도 → 1주 매도(수량 0). | 입고 뒤 수량 2, 단가 nil이고 "단가 모름" 표시가 선다. 첫 매도 뒤 수량 1, 여전히 모름. 마지막 매도로 수량이 0이 되면 모름 표시가 풀린다. 이후 재매수의 단가는 새 값으로 시작한다. |
| T-05 | R-41 | 계정 통화 매수 10주 @100, 수수료 20. 또 다른 외화 매수는 환율 행이 거래일에도 5일 전에도 없다. | 첫 매수의 취득 단가 102(= 100 + 20 ÷ 10). 둘째는 단가 nil이라 포지션이 전량 청산될 때까지 평균 단가가 모름이다. 이때 첫 매수 때 저장된 `calculated` `cost_basis`는 지워지지 않고 이전 값이 남는다(R-36 ④: "단가 모름" 표시는 이동 입고에만 서므로 가격을 모르는 매수의 nil은 기존 calculated 값을 덮지 않는다). |
| T-06 | R-34, R-35 | 수량 10, 2-for-1 split의 ex-date가 D, D에 가격이 없는 종목. | D의 gap 행은 수량 20, 가격과 단가는 절반, 금액은 20 × 절반 가격(즉 전날 금액과 같음)이다. D 이후 이월 행도 20주다. |
| T-07 | R-33 | 연동 계정, 오늘 provider 보유 수량 10, 3일 전(D) 매수 4주 기록, 시세 있음. | 오늘부터 D까지 수량 10(오늘의 가격은 보유 행의 가격, D까지는 시세 규칙), D 전날부터 수량 6. D의 매매는 되돌려진다. |
| T-08 | R-09~R-12 | (a) DB에 `005930`/`XKRX`가 있다. (b) 없고 provider 검색에 같은 ticker·MIC가 있다. (c) 어디에도 없다. (d) 검색이 시간 초과다. | (a) provider를 부르지 않고 그 행. (b) 행을 만들고 이름·국가를 채우고 `price_provider`를 provider 키로 쓴다. (c) `offline = true`, 사유 없음. (d) `offline = true`, 사유 `resolution_pending`, 다음 resolve는 DB 단계를 건너뛰어 검색을 다시 한다. |
| T-09 | R-20, R-21, R-23 | provider가 월 100, 화 101, 목 103만 준다(수요일 빠짐), 요청 구간 월~금, 금요일 빠짐, 오늘은 그 주 안. | 월 100, 화 101, 수 101(이월, provisional), 목 103, 금 103(이월, provisional). 다음 실행에서 provisional 날짜가 다시 받아진다. |
| T-10 | R-22 | `start_date` 2018-01-01, provider 시세가 2020-01-03부터 있다. | 2020-01-03부터 행이 만들어지고 그 이전은 비어 있다. `first_provider_price_on = 2020-01-03`. 이후 실행은 그 날짜로 구간을 줄여 건너뛰기가 가능하다. |
| T-11 | R-21 | 날짜 D의 DB 행이 사용자가 고친 값 500(비provisional)이고 provider는 480을 준다. (a) 일반 실행 (b) `clear_cache` 실행. | (a) 500 유지. 구간 전체에 비provisional DB 행이 있으면 importer가 provider를 아예 부르지 않고, 다른 날 때문에 부르더라도 D는 DB 값을 보존한다. (b) 480으로 덮어쓴다. |
| T-12 | R-24, R-19 | provider가 오류 응답을 낸다. | upsert 0건, `[0, 오류 메시지]`가 돌아가고 경고·진단 로그가 남는다. 요금제 제한 메시지면 종목별 제한 기록이 남는다. |
| T-13 | R-08 | 두 provider가 같은 `AAPL`/`XNAS`를 준다. 한 provider가 같은 키를 두 번 준다. | 결과에 provider별로 하나씩 둘이 남고, 한 provider의 중복은 하나로 합쳐진다. 결과는 최대 30건. |
| T-14 | R-25 | 가격 0.12345 한 행, 또는 1001행, 또는 두 통화, 또는 provider가 추적하는 종목. | 모두 거부되고 아무 행도 쓰이지 않는다. |
| T-15 | R-45, R-36 | 기존 행이 출처 `manual`이고 잠기지 않았다. 들어오는 값이 (a) `calculated` (b) `provider`. | (a) 덮는다. (b) 덮지 않는다. 잠긴 행이면 (a)(b) 모두 덮지 않는다. |
| T-16 | R-48 | 보유 종목 A를 B로 교체. A의 날짜 d1 행과 B의 d1 행(같은 통화)이 모두 있고 A의 d2 행은 B에 없다. | d1은 수량·금액이 합쳐지고 `security_locked = true`로 한 행이 남고, d2는 종목이 B로 바뀌고 잠긴다. A의 매매 전부가 B로 옮겨진다. B만 한정해 재계산된다. |
| T-17 | R-53, R-61 | family USD, 투자 계정이 KRW이고 KRW→USD 환율이 없다. | `InvestmentStatement`의 환산 합계에서 그 계정의 보유·잔액이 빠지고(0) `unrealized_gains_trend`에도 그 보유가 양쪽에서 빠진다. 같은 계정의 잔액 계산은 보유를 1:1로 센다(행 1). |
| T-18 | R-57 | 매수(수량 +10, amount +1,000 USD), 배당(수량 0, 라벨 `Dividend`, amount -50 USD), family 통화 USD. | `contributions` 1,000, `dividends` 50, `trades_count` 2. 배당은 `contributions`와 `withdrawals`에 들어가지 않는다. |
| T-19 | R-62 | 계정 통화가 KRW인 부동산이 USD 평가 provider에 연결돼 있다. | provider 요청 없이 경고만 남기고 건너뛴다. `avm_last_synced_on`은 바뀌지 않는다. |
| T-20 | R-37 | forward 전체 재계산. 계정에 매매가 없는 종목의 비 provider 보유 행이 있고, 같은 계정에 provider 행도 있다. | 비 provider 행은 지워지고 provider 행은 남는다. `security_ids`로 한정한 재계산에서는 지워지지 않는다. |
| T-21 | R-17 | 종목 A는 전량 매도되어 마지막 매매일이 2026-03-01, 종목 B는 현재 보유 중이다. | A의 구간 끝은 2026-03-01, B의 끝은 오늘이다. |
| T-22 | R-13 | 종목에 `price_provider = tiingo`인데 tiingo가 설정에서 꺼져 있다. | `price_data_provider`는 nil, `provider_status`는 `provider_unavailable`이다. 첫 번째 켜진 provider로 대신하지 않는다. |
| T-23 | R-02, R-03, R-67 | Yahoo 검색 결과 `005930.KS`를 골라 저장한다. 별도로 사용자가 `005930`/`XKRX`를 직접 입력해 저장한다. | `ticker`가 다르고 MIC도 다르므로 종목이 둘 생기고 시세·보유가 따로 쌓인다. 앞의 종목은 `fetch_security_prices(symbol: "005930.KS")` 왕복이 성립하고, 뒤의 종목은 provider가 접미사 없는 심볼을 어떻게 다루는지에 달려 있다(Yahoo는 한국 MIC에 접미사를 붙이지 않아 요청이 실패할 수 있다, 서버 응답은 미확인). |
| T-24 | R-21 | EODHD로 `XKOS` 종목의 시세를 받는데 `currency_for`가 nil을 돌려주고 응답에 가격이 있다. | 모든 행이 통화 `USD`로 저장된다(숫자는 KRW 값). 이후 환산이 그 숫자를 USD로 환산해 보유 평가액이 틀어진다. |
| T-25 | R-23 | provider가 오늘 날짜에 장중 값 70,500을 돌려주고 장 마감 후 종가는 71,000이다. | 장중 값이 `provisional = false`로 저장되고 이후 일반 실행에서 갱신되지 않아 `clear_cache` 전까지 70,500에 고정된다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `app/models/holding.rb:21-24`, `db/schema.rb:1213-1236` | 검증과 인덱스를 직접 읽음. 일괄 upsert는 R-36 근거(`materializer.rb:117`, `:141-150`)에서 검증이 없음을 확인 |
| R-02 | `app/models/security.rb:89-103`, `:310-318`, `:344-348`, `db/schema.rb:2352-2388` | 분류 열의 쓰기 부재: `grep -rn "asset_class\|asset_sub_class\|classification_source" app lib --include=*.rb`에서 `security.rb`(정의)와 `investment_statement.rb`(읽기) 밖의 결과가 없다. 놓칠 수 있는 곳: `sector`·`region`·`industry` 열(이 패턴에 없음), `update_columns`·SQL 문자열·`db/` 마이그레이션·JS·동적 `send`. 가져오기 `Family::DataImporter`는 `exchange_mic` 등을 쓰므로(`data_importer.rb:1240`) 분류 열 외 열은 쓰는 코드가 더 있을 수 있다 |
| R-03 | `app/models/security.rb:201-252` | 직접 읽음 |
| R-04 | `app/models/security.rb:120-131`, `app/models/trade/create_form.rb:116-130` | 직접 읽음 |
| R-05 | `app/models/trade.rb:26-71`, `:186-195`, `:178-182` | 직접 읽음 |
| R-06 | `app/models/security/price.rb:1-14`, `app/models/security/split.rb:8-47`, `db/schema.rb:2405-2429` | 직접 읽음. 가격 양수 검증이 모델에 없다는 것은 파일 전체를 읽어 확인 |
| R-07 | `app/models/security.rb:108-112`, `app/models/security/combobox_option.rb:1-21`, `config/exchanges.yml` 1-30 | 직접 읽음. 번역 문구 내용은 열지 않음 |
| R-08 | C-14, `app/controllers/securities_controller.rb:1-7` | 직접 읽음. `Concurrent::Promises` 시간 초과·`skip_nil` 의미는 gem 규칙(확인 한계 2) |
| R-09 | C-12 `resolver.rb:2-21`, `:26-38` | 직접 읽음. 호출처: `grep -rln "Security::Resolver" app lib --include=*.rb`가 22개 파일(어댑터 래퍼·`trade_import.rb`·`qif_import.rb`·`transactions_controller.rb`·`trade/create_form.rb` 포함)을 반환 |
| R-10 | C-12 `resolver.rb:90-116`, `:208-226` | 직접 읽음 |
| R-11 | C-12 `resolver.rb:118-206`, `:228-307` | 직접 읽음. 동점 처리는 코드에 규칙이 없고 `sort_by`의 의미에 기댄 추론(U-02) |
| R-12 | C-12 `resolver.rb:47-88` | 직접 읽음 |
| R-13 | `app/models/security/provided.rb:200-221` | 직접 읽음 |
| R-14 | `app/models/setting.rb:100-105`, `:221-229`, `app/models/security/provided.rb:8-28`, `app/controllers/settings/hostings_controller.rb:130-147`, `app/models/provider/registry.rb:233-252` | 직접 읽음. 설정 화면 갱신 처리 중 이 줄 이외는 읽지 않음 |
| R-15 | `app/models/trade/create_form.rb:1-156`(`:60-76`, `:78-110`, `:112-155`), `app/controllers/trades_controller.rb:16-47`, `:49-81`, `:101-155` | 직접 읽음. 수동 티커: `create_form.rb:61-62`의 주석은 "offline ticker (that we won't fetch prices for)"이고 구현은 `Security::Resolver.new(parsed[:ticker], ...)`(`:65-69`)이다. 구현이 사실 |
| R-16 | `app/models/security/provided.rb:223-269` | 직접 읽음. 반복 호출은 코드 구조에서의 추론 |
| R-17 | C-07 | 직접 읽음 |
| R-18 | `app/models/account/market_data_importer.rb:10-13`, `:62-76`, `app/models/market_data_importer.rb:13-45`, `:70-95`, `app/models/security/provided.rb:272-343` | 직접 읽음. `snapshot` 모드 조건은 `:31-34`. 스케줄링은 sync-pipeline이 가짐 |
| R-19 | `app/models/security/provided.rb:354-368` | 직접 읽음. 반환 형태 두 가지는 `holdings_controller.rb:117-121`이 구조 분해로 받는 것으로 확인 |
| R-20 | C-08 `importer.rb:154-173`, `:227-261`, `:271-290`, `:372-376` | 직접 읽음. 뉴욕 오늘: money-currency-rules R-31과 같은 식(`Date.current.in_time_zone("America/New_York").to_date`)이고 의미는 ActiveSupport에 기댄 추론. 행 수 단축은 `:227-239`에서 읽은 추론 |
| R-21 | C-08 `importer.rb:78-127` | 직접 읽음 |
| R-22 | C-08 `importer.rb:30-76`, `:142-146`, `:292-327` | 직접 읽음 |
| R-23 | C-08 `importer.rb:329-343`, `app/models/security/price.rb:11-14` | 직접 읽음 |
| R-24 | C-08 `importer.rb:25-28`, `:175-218`, `:345-362`, `app/models/security/plan_restriction_tracker.rb` 1-25 | 직접 읽음. 마지막 문장: `:25-28`의 `provider_prices.empty?`가 앵커 계산 전에 걸리는 것을 읽음. 요금제 제한 기록 내부는 앞 25줄만 읽음 |
| R-25 | `app/models/security/manual_price_import.rb:1-189`, `app/controllers/api/v1/security_prices_controller.rb:21-80` | 직접 읽음. API 컨트롤러의 나머지(`writable_accounts_referencing` 이후)는 앞 80줄만 읽음 |
| R-26 | C-22 | 직접 읽음. 건강 점검 job 스케줄: `config/schedule.yml:20-24`(평일만, `0 2 * * 1-5`). 성공 때 `offline_reason`을 지우지 않는 것은 `health_checker.rb:108-114`, `delete_all` 조건은 `:146`, `:159`, 점검 대상은 `:27-45`(offline 필터 없음), provider 대체는 `provided.rb:200-207`. 점검 주기·배치는 `health_checker.rb:12-14`, `:27-45` |
| R-27 | `app/controllers/holdings_controller.rb:108-144` | 직접 읽음 |
| R-28 | `app/models/balance/materializer.rb:16-35`, C-11 `materializer.rb:15-44`, `app/controllers/holdings_controller.rb:96-98`, `:135-136` | 직접 읽음. 전략 매핑: `app/models/account/syncer.rb:22`(`account.linked? ? :reverse : :forward`)를 grep으로 확인(sync-pipeline R-17의 근거와 같음) |
| R-29 | C-06 `portfolio_cache.rb:10-23`, `:25-54`, `:124-151`, `:153-236` | 직접 읽음. 동점은 `:225-228`의 `min_by`가 첫 항목을 고르고 입력 순서가 DB 반환 순서(`:166-168` 정렬 없음)라는 읽기에서의 추론(U-01) |
| R-30 | `app/models/holding/portfolio_cache.rb:25-54` | 직접 읽음. `UnknownCurrencyError` 미포착: 이 파일과 `forward_calculator.rb`·`reverse_calculator.rb`·`materializer.rb`에서 `UnknownCurrencyError`·`ArgumentError` rescue를 찾지 못함(검색 범위가 이 네 파일, 호출자의 rescue는 보지 않음) |
| R-31 | `app/models/holding/portfolio_cache.rb:115-122` | 직접 읽음 |
| R-32 | C-09 `forward_calculator.rb:6-82`, `app/models/account.rb:855-858` | 직접 읽음 |
| R-33 | C-10 `reverse_calculator.rb:20-83`, `app/models/holding/portfolio_snapshot.rb:12-57`, `app/models/holding/materializer.rb:382-389` | 직접 읽음 |
| R-34 | `app/models/holding/portfolio_cache.rb:60-113`, C-09 `:87-95`, C-10 `:99-107`, C-02 | 직접 읽음. split 쓰기 부재: `grep -rn "Security::Split\|security_splits\|splits\.create\|Split\.create\|Split\.new\|splits\.build" app lib --include=*.rb`와 `grep -rn "\.splits\b\|splits\.\(create\|find_or\|upsert\|insert\)\|Split\.\(upsert\|insert\|find_or\)" app lib --include=*.rb`에서 `holding/*`(읽기), `security/split.rb`(모델), `snaptrade_account/split_security_repair.rb`(읽기)만 나오고 쓰는 호출이 없다(`splits_controller.rb`는 거래 분할로 무관). 놓칠 수 있는 곳: 마이그레이션·`db/seeds`·`rake` task(`lib/tasks`는 `lib` 검색에 포함)·SQL 문자열·동적 호출 |
| R-35 | C-05 | 직접 읽음 |
| R-36 | C-11 `materializer.rb:102-232`, `:281-363` | 직접 읽음 |
| R-37 | C-11 `materializer.rb:15-44`, `:234-275`, `:365-380`, `app/models/account.rb:851-853` | 직접 읽음 |
| R-38 | C-11 `materializer.rb:9-13`, `:22-24`, C-10 `:151-176` | 직접 읽음 |
| R-39 | `app/models/account.rb:826-853`, `app/models/holding/current_for_investment_accounts.rb:1-51` | 직접 읽음. 두 형태의 provider 날짜 정의 차이(`maximum(:date)` vs `updated_at::date`)는 코드에서 읽음 |
| R-40 | C-01 | 직접 읽음 |
| R-41 | C-03 | 직접 읽음 |
| R-42 | C-09 `forward_calculator.rb:105-137`, C-10 `reverse_calculator.rb:190-226`, `app/models/trade.rb:26`, `:69-71` | 직접 읽음 |
| R-43 | C-10 `reverse_calculator.rb:133-289` | 직접 읽음 |
| R-44 | `app/models/holding/materializer.rb:54-100`, `app/models/holding_lot.rb:5-58`, `db/schema.rb:1193-1211` | 직접 읽음. 읽는 곳 부재: `grep -rn "holding_lots\|HoldingLot" app lib --include=*.rb --include=*.erb`로 `account.rb`(연관), `holding.rb`(이동), `materializer.rb`, 모델 자신만 나옴. JS·API·locale·동적 호출은 보지 않음 |
| R-45 | C-04 | 직접 읽음 |
| R-46 | C-17, `app/models/holding.rb:52-78`, `:99-128` | 직접 읽음. 환율 결합이 정확히 같은 날짜·방향의 행만 쓴다는 것은 `:134-144`의 SQL에서 읽음. lot 장부 경로와 다름은 코드 비교 |
| R-47 | `app/controllers/holdings_controller.rb:17-45`, `app/models/holding.rb:247-259` | 직접 읽음 |
| R-48 | `app/models/holding.rb:261-375`, `app/controllers/holdings_controller.rb:61-106`, `:146-154`, `app/models/holding_lot.rb:44-57` | 직접 읽음. 어댑터의 잠금 규칙은 provider-import-adapter R-46, R-48 |
| R-49 | `app/models/holding.rb:215-222`, `app/controllers/holdings_controller.rb:47-59` | 직접 읽음. `can_delete_holdings?`는 provider-import-adapter R-63 |
| R-50 | `app/models/trade.rb:80-89`, `:160-243`, `:271-281` | 직접 읽음 |
| R-51 | `app/models/investment_statement.rb:37-62`, `:388-410` | 직접 읽음. `cash_balance`·`holdings_value` 호출처: `grep -rn "\.cash_balance\b\|holdings_value\b\|cash_balance_money" app --include=*.rb --include=*.erb | grep -i statement`에서 이 클래스 내부만 나옴(검색 범위가 `app`의 rb·erb, 뷰 헬퍼의 동적 호출은 보지 않음) |
| R-52 | `app/models/investment_statement.rb:64-86`, `:322-386` | 직접 읽음 |
| R-53 | C-18 `:421-427`, `:145` 주석 | 직접 읽음. 주석(`:144-145` "a currency with no rate counts 1:1 (`convert_to_family_currency`)")과 구현(`:426` `rate ? numeric * rate : 0`)이 다르다. `:418-420`과 `totals.rb:65-67`의 주석은 0과 일치. 구현이 사실 |
| R-54 | C-18 `:755-781`, `:87-134`, `:240-259`, `:783-801` | 직접 읽음 |
| R-55 | `app/models/investment_statement.rb:136-186`, `:451-641` | 직접 읽음 |
| R-56 | `app/models/investment_statement.rb:188-215`, `:643-741` | 직접 읽음 |
| R-57 | C-19, `app/models/investment_statement.rb:15-29`, `:225-238`, `:807-820` | 직접 읽음. 보류 판정 SQL(`Transaction.pending_providers_sql`)은 열지 않음 |
| R-58 | `app/models/investment_statement.rb:261-320` | 직접 읽음. `net_market_flows` 정의는 행 1 소관이라 열지 않음 |
| R-59 | `app/controllers/portfolios_controller.rb:1-60`, `app/models/portfolio/section_registry.rb:1-91`, `app/controllers/concerns/preview_gateable.rb:1-20`, `app/views/portfolios/_accounts.html.erb:1-8` | 직접 읽음. 카드(`accounts/balance_card`)는 열지 않음(행 1) |
| R-60 | `app/models/portfolio/xirr.rb:1-60`, `app/models/portfolio/flow_classifier.rb:1-60` | 명령 `grep -rn "Portfolio::Xirr\|Xirr\b" app lib --include=*.rb --include=*.erb`와 `grep -rn "Xirr\|FlowClassifier" app lib config db`, `grep -rn "FlowClassifier" app --include=*.rb --include=*.erb -l`. 결과는 `totals.rb`(주석), `flow_classifier.rb`, `xirr.rb` 자신뿐. 놓칠 수 있는 곳: JS, 동적 `constantize`, `docs/`. `xirr.rb` 머리 주석은 "The caller that renders this is a later PR"라고 쓴다. `InvestmentFlowStatement`는 `reports_controller.rb:143`이 부른다(행 14) |
| R-61 | R-30, R-36, R-41, R-46, R-50, R-53, R-57, R-58의 근거와 `app/models/holding.rb:41-50`, `:396-403`, `app/models/account.rb:826-829`, `app/models/balance/sync_cache.rb:63-92`(경계) | 직접 읽음. 목록은 이 스펙이 읽은 호출처 한정이고 `ConversionError`·`rate_sql` 호출처 전수는 아니다(money-currency-rules R-42와 같은 한계). `reports_controller.rb:561-640`의 `gains_by_tax_treatment`는 환율이 없으면 nil로 두고 합계에서 빼서 센다(행 14, 대표값만 확인) |
| R-62 | C-20 | 직접 읽음. 예산 소진 판정 `requests_remaining?`는 C-21 `:103-105` |
| R-63 | C-20 `:77-113` | 직접 읽음. `set_current_balance`는 행 1이라 열지 않음 |
| R-64 | C-21, `app/models/provider/registry.rb:246-248`, `:183-204`, `db/schema.rb:1999-2008` | 직접 읽음. 개별 provider 구현(`rentcast`, `realie`, `chimnie`)은 `chimnie`의 클래스 메서드 위치만 grep(`:84-104`) |
| R-65 | `config/schedule.yml:42-47`, `app/models/property.rb:107-165`(`avm_linkable?`, `link_avm_provider!`), C-20 `:1-14` | `property.rb:122-130`, `:152-165`를 읽음. 연결 해제는 첫 평가 뒤 `avm_last_synced_on`이 비어 있을 때의 `update_all`. 큐 lock은 gem 규칙(미열람, 추론) |
| R-66 | C-15, `docs/llm-guides/adding-a-securities-provider.md:29-270`, `:271-330`, `:471-493`, `app/models/provider/registry.rb:233-252` | 문서와 구현을 대조. 문서의 `SecurityConcept::Security` 필드 목록(`currency`만)과 구현의 `currency`, `isin`(선택)이 다르다. 구현이 사실. `healthy?`·`usage`는 문서에만 있고 호출처는 열지 않음 |
| R-67 | C-16, `app/models/security/price/importer.rb:78-127`, `app/models/security/health_checker.rb:92-105`, `app/models/provider/eodhd.rb:234-243`, `app/models/provider/yahoo_finance.rb:296-331` | 직접 읽음. 소문자 통화 코드의 영향은 `holding.rb:397`(`currency == account.currency` 문자열 비교)에서 읽은 추론. 마지막 문장 g는 `security_concept.rb:4-6` 주석 |
| R-68 | `app/controllers/api/v1/trades_controller.rb:1-400`, `app/controllers/api/v1/securities_controller.rb:1-60`, `app/controllers/concerns/api/v1/security_resource_filtering.rb:1-53`, `app/controllers/api/v1/security_prices_controller.rb:1-129` | 직접 읽음. trades 컨트롤러의 `:400` 이후는 읽지 않음. `ticker_from_security`는 `:439-443` |
| R-69 | `app/models/holding/cost_basis_tracker.rb:1-5`, `app/models/security/warsaw_price_currency_backfill.rb:1-20`, `lib/tasks/securities.rake` | 사용처: `grep -rn "WarsawPriceCurrencyBackfill\|CostBasisTracker" app lib config -l`이 정의 파일과 rake만 반환(`rake` 본문 일부만 읽음). 놓칠 수 있는 곳: 동적 호출, `db/` |
| R-02·R-11·R-14·R-15~R-18·R-21~R-25·R-46·R-48·R-61·R-66·R-67 보강 | 독립 검토 반영: `security.rb:98`, `db/schema.rb:2352-2415`, `resolver.rb:130`, `hostings_controller.rb:129`, `onchain/security_resolver.rb:46-48`, `create_form.rb:48-52`, `:118-128`, `provided.rb:118-120`, `:223`, `:324`, `import_windows.rb:18`, `importer.rb:31`, `:124`, `:295-300`, `:337`, `:364-370`, `price.rb:11-14`, `manual_price_import.rb:61-63`, `:103`, `plan_restriction_tracker.rb:13-25`, `holding.rb:41-50`, `:173-174`, `:421`, `:443-445`, `holdings_controller.rb:74-80`, `holding.rb:361` | 직접 읽고 대조함("소수 5자리" 등 이전 표현과 달라진 곳은 본문이 최신) |
| T-01~T-25 | 해당 R-ID의 근거를 따라 값을 대입해 도출한 사례 | 실행하지 않음(Rails 실행 금지). 시나리오의 날짜와 금액은 예시 |

### 2.2 코드 읽는 순서 [선택]

1. 입구: `trade/create_form.rb`(매매 저장) → `security/resolver.rb`(종목 해석) → `account/market_data_importer.rb`(`import_security_prices`) → `security/price/import_windows.rb` → `security/price/importer.rb`.
2. 재구성: `balance/materializer.rb:16`(holdings를 먼저 부른다) → `holding/materializer.rb` → `holding/forward_calculator.rb`·`reverse_calculator.rb` → `holding/portfolio_cache.rb`(가격·split) → `holding/lot_book.rb`(단가) → `holding/gapfillable.rb`.
3. 읽기: `account.rb:826`(`current_holdings`) → `holding.rb`(`avg_cost`) → `investment_statement.rb`.
4. 시세 provider 인터페이스: `provider/security_concept.rb` → `provider/eodhd.rb:26-97`(매핑표와 `eodhd_symbol`) → `provider/yahoo_finance.rb:582-633`, `:1203-1257`.
5. 원본의 구현 전략: 재구성은 매번 계정 전체를 처음부터 다시 계산하고(항목이 바뀔 때마다 sync), 결과를 행 단위 upsert로 덮는다(증분 갱신 없음). 시세는 구간을 정하고 gap을 이월로 채워 저장한다. 요약 쿼리(`InvestmentStatement`)는 평균 단가와 이전 스냅샷을 한 번의 쿼리로 미리 계산해 N+1을 피한다.

### 2.3 비교·재사용 출처 [선택]

다른 레포의 같은 기능 스펙은 아직 없다. 이 스펙은 코드를 복사하지 않았다(AGPL-3.0, overview 1절). 선행 스펙과 겹치는 부분: 환율(R-25~R-27, R-35)은 [money-currency-rules.md](./money-currency-rules.md), `import_holding`·`import_trade`·`CostBasisReconciler` 호출 계약은 [provider-import-adapter.md](./provider-import-adapter.md)가 가진다. 어댑터 스펙의 적용 메모가 "종목 해석은 이 스펙"이라고 가리키지만 어댑터 스펙의 `depends`에는 이 스펙이 없으므로 순환은 없다.

### 2.4 검토 기록 [필수, ready 스펙]

`draft`라서 원본 대조 점검(워크플로 4장 5번)은 아직 하지 않았다. 작성자가 확인한 것: R-ID마다 근거 줄을 직접 읽었고, `python scripts/check.py sure`로 형식·줄 존재를 점검한다. 재구현은 미수행.

- **독립 검토(검토자 서브에이전트 1명, 2026-11-18)**: R-01~R-67 전부, C-ID 전부, T-ID 16개를 다시 따라갔다. 일치 약 53개, 세부 차이 14개, 불일치와 누락 약 25건이 나왔다. 작성자가 코드로 다시 확인해 반영했다(검토자가 틀린 두 곳은 고쳐 반영). R-68·R-69, T-23~T-25와 미결정 U-03~U-05가 추가됐다.
- **메인 표본 점검**: Yahoo 검색 결과 `symbol`에 접미사가 이미 붙어 저장되고 `normalize_symbol`이 그대로 통과시킴(`yahoo_finance.rb:218-222, 629-633`), EODHD `currency_for`가 매핑이 없으면 nil이고 시세 importer가 nil이면 USD로 저장(`eodhd.rb:326-340`, `security/price/importer.rb:31, 124`), 자동 건강 점검 cron이 평일만 실행(`config/schedule.yml:20-24`)을 원본에서 직접 확인했다.
- **대조하지 못한 것**: Yahoo의 실제 `exchange`·`exchDisp` 값과 `.KS`·`.KQ` 접미사, EODHD 코스닥 코드(외부 서버 동작, 미확인), R-08의 `Concurrent::Promises`·`Rails.cache` 의미, R-20의 `Date#in_time_zone`, R-55·R-56·R-59의 뷰와 하위 보조 메서드, 개별 부동산 provider(Rentcast, Realie).

## 적용 메모 [선택]

한국 종목(KRX, KRW, MIC `XKRX`)과 우리가 따로 만드는 시세 provider를 기준으로 쓴다. 원본의 미결정(U-01, U-02)을 여기서 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-20, R-18 | 시세 구간의 끝 날짜를 종목 거래소 현지 오늘로 정한다(계정·family 시간대로 정하는 방안도 있다) | 원본의 의도는 뉴욕 오늘이지만 코드는 시간대 변환 없이 `Date.current`를 쓰는 것으로 읽힌다(`importer.rb:372-376`, 추론, money-currency-rules R-31과 같은 코드 형태). 의도대로 변환이 일어난다면 14:00 KST 이전(뉴욕은 전날)에는 상한이 한국 날짜보다 하루 이르고(KRX 마감 15:30 KST는 06:30 UTC로 뉴욕에서는 같은 날짜 새벽이다), 변환이 없다면 사용자 시간대의 오늘이 상한이다. 어느 쪽인지 코드만으로 확정되지 않고 어느 쪽이든 거래소 현지 날짜와 같다는 보장은 없다 | `end_date` 상한 규칙이 바뀐다. T-09의 오늘 판정이 현지 날짜가 된다 |
| R-61 | 환산 실패 정책을 "모름 표시 + 건수 보고" 하나로 통일할지 정한다(원본은 1:1·0·nil이 섞임, 특히 `Holding#weight`가 한 식에서 두 정책) | 사용자 결정 대기. 통일하지 않으면 같은 보유가 화면마다 다른 금액으로 보인다(T-17) | 일별 재구성의 시세 환산(R-30)과 요약(R-53)의 실패 경로가 바뀐다. T-02, T-17의 기대가 바뀐다 |
| R-15 | 수동으로 입력한 티커는 provider 검색을 거치지 않고 항상 offline 종목으로 만들지 정한다 | 원본은 주석상 offline 전용이지만 구현은 검색을 거쳐 실제 종목이 될 수 있다. 한국 종목을 코드만 쳐서 입력하면 어느 provider의 어느 거래소로 해석될지 사용자가 통제하지 못한다 | R-09~R-12의 입력이 `manual_ticker`일 때의 경로 |
| R-26, R-67 | 단건 조회(`fetch_security_price`)가 쉬는 날에 직전 거래일을 돌려주도록 인터페이스를 명시한다 | 원본은 구현마다 다르고(Yahoo는 10일 구간, EODHD는 하루 구간 후 오류) 건강 점검이 오늘 날짜로 호출한다. KRX 공휴일(설·추석 등)과 주말에 점검이 실패로 세어진다 | `fetch_security_price`의 계약, R-16의 반환 날짜 규칙, T-12 |
| R-17, R-29 | 시세 행의 가격 소수 자릿수(4자리)와 계정 통화 환산 뒤 `holdings.price`의 4자리가 KRW에서 충분한지 확인한다 | KRW 가격은 정수라 문제없으나 KRW 종목을 USD 계정이 가지면 환산 가격이 소수 4자리에서 잘린다(예: 500 KRW ≈ 0.36 USD 근처에서 0.0001 USD 단위). 환산 가격의 정밀도가 필요하면 `holdings.price` 열을 넓힌다 | `holdings.price` 열 정의 |

**새 securities provider를 만드는 사람을 위한 체크리스트 (한국 종목 기준)**

- 티커 형식과 Yahoo 접미사: 원본은 `Security.ticker`를 문자열로 저장하고 대문자로 바꾸며(R-02) 숫자 코드의 앞자리 0도 보존한다. Yahoo는 검색 결과의 `symbol`을 `quote["symbol"]` 그대로 돌려주므로(`yahoo_finance.rb:218-222`) 접미사가 이미 붙은 심볼(예 `005930.KS`)이 검색 결과이고, 그것을 골라 저장한 종목은 `ticker`에 접미사가 들어간다. `normalize_symbol`은 이미 접미사가 있으면 그대로 통과시키고(`:629-633`) `EXCHANGE_CONFIG`(`:582-606`)에 한국이 없어 접미사를 새로 붙이지 않으므로 `fetch_security_prices(symbol: "005930.KS", ...)` 왕복은 성립한다. 접미사 없이 `005930`을 보내 404가 나는 경로는 사용자가 `005930`과 `XKRX`를 직접 짝지은 경우(수동 티커, 가져오기, 연동)뿐이다. 영향: (1) 유일 키가 `(ticker, MIC)`라서(R-02, R-03) 같은 회사가 `005930.KS`+Yahoo MIC 행과 `005930`+`XKRX` 행으로 따로 생기고 시세·보유가 갈라진다(보유 종목 교체 R-48로 합칠 수 있다, T-23). (2) Resolver 정확 일치(R-11)는 입력 ticker와 검색 결과 ticker의 문자열 일치를 보므로 `005930`을 입력해도 `005930.KS`는 정확 일치가 아니고 가까운 일치로 가며 다른 후보가 있으면 뒤로 밀린다. (3) Yahoo의 `search_securities`는 `exchange_operating_mic` 인자를 캐시 키와 이중 상장 중복 제거에만 쓴다. Yahoo의 실제 `exchange`·`exchDisp` 값과 `.KS`·`.KQ` 접미사의 서버 동작은 `미확인`이다. `map_country_code`는 거래소 표시명이 `KOREA|KRX`에 맞으면 `KR`을 돌려주고(`:1184-1185`) `Security::EXCHANGES.dig(MIC, "country")`가 nil일 때만 쓰인다(`:222`).
- MIC 매핑: `config/exchanges.yml`에 `XKRX`와 `XKOS`가 모두 있고(`:250-255`) 표시명과 국가에만 쓰인다(R-07). Yahoo는 `map_exchange_mic`(`:1203-1257`)에도 한국 코드가 없어 검색 결과 MIC가 Yahoo raw 거래소 코드의 대문자 문자열이 된다(값은 `미확인`). 그래서 이 경로의 종목 MIC는 `XKRX`가 아니다. EODHD는 `XKRX → KS`, `KS → XKRX`, `KS → KRW`가 있고 `XKOS`는 어느 표에도 없다(`eodhd.rb:48`, `:71`, `:91`). `XKOS` 종목은 `<symbol>.XKOS`로 조립된다(`:314-324`). EODHD가 코스닥을 받는 코드는 `미확인`이다. 새 provider는 검색 결과를 `XKRX`/`XKOS`로 매핑하고, 요청에서 받은 MIC를 자기 거래소 코드로 되돌리는 양방향 표를 가져야 한다.
- 경고, 조용한 통화 오염: EODHD의 `currency_for`(`:326-340`)는 검색에서 24시간 캐시한 통화, 거래소 기본 통화 표 순으로 통화를 찾고 둘 다 없으면 nil을 돌려준다. `XKOS`처럼 표에 없는 MIC이거나 검색 캐시가 만료된 raw 코드 종목은 nil이 되고, 시세 importer는 통화가 없는 행을 `USD`로 저장한다(`importer.rb:31`, `:124`, R-21). 숫자는 KRW인데 통화는 USD인 시세가 생기고 환산(R-30)이 그 숫자를 USD로 환산해 보유 평가액이 틀어진다(T-24). 같은 원인의 선례가 폴란드 PLN 시세 보정이다(R-69). 새 provider는 모든 `Price`에 통화를 채우고, 통화를 모르면 오류로 끝내는 편이 안전하다.
- 통화: provider의 `Price.currency`는 `KRW`(대문자 3자)여야 한다(R-67). 통화 표에서 KRW는 소수 자릿수 0이고(money-currency-rules R-10) 이것은 표시용이다. 저장은 소수 4자리까지다. 가격이 비어 있는 응답에서 provider가 기본 통화를 추정해야 한다면 거래소별 기본 통화 표를 가져야 한다(Yahoo의 `default_currency`, EODHD의 `EXCHANGE_CURRENCY`처럼).
- 가격 정밀도: `security_prices.price`는 소수 4자리, `trades.price`는 10자리, `holdings.price`는 4자리다(R-06, 1.3). KRW 종목은 정수 가격이라 손실이 없다. 소수 4자리를 넘는 가격을 주는 provider는 반올림이 일어난다.
- 응답 타입: `SecurityConcept::Security`, `SecurityInfo`, `Price` 값 객체와 `Provider::Response`로 돌려주고 모든 연산을 `with_provider_response`로 감싼다(R-66). 가격이 없는 날은 행을 생략하거나 nil을 주고 0 이하 가격을 만들지 않는다(R-21).
- 단건 조회: 쉬는 날(주말, 한국 공휴일)에 오류가 아니라 직전 거래일 가격을 돌려준다(R-26, R-67 d). 건강 점검이 오늘 날짜로 호출한다.
- 이력 제한: 제한이 있으면 `max_history_days`를 정의한다(R-20). 상장 전 구간 요청에는 빈 응답이나 상장일 이후 행만 주면 importer가 앵커를 옮긴다(R-22).
- 등록: registry의 securities 키 목록, 생성 메서드(API 키가 없으면 nil), 설정 필드를 추가한다(R-14, R-66). 켜진 provider 목록의 순서가 종목에 `price_provider`가 없을 때의 기본 provider를 정한다(R-13).
- 액면분할: 시세는 분할 조정 전 값이어야 한다. 원본은 split 행을 별도 테이블에서 읽어 수량을 조정하고 가격은 그대로 쓴다(R-34). split을 채우는 코드가 기준 SHA에 없어서(R-34 근거) 분할 데이터는 새 provider가 아니라 별도 적재가 필요하다. 조정 종가를 주는 provider를 쓰면 이중으로 조정되는지 확인해야 한다(추론).
- 소수 수량: 코스피·코스닥은 소수 주식이 없지만 증권사 소수점 거래 연동이 있으면 수량은 소수 18자리까지 저장된다(1.3).
- 구현자가 막히는 질문과 답: (a) `Price.date`는 시각 없는 날짜, `price`는 decimal로 바꿀 수 있는 숫자이고 현지 거래일 대 UTC 기준은 코드에 없다(U-05, Yahoo는 UTC 날짜). (b) 오늘 날짜에 장중 값을 종가로 주면 `provisional = false`로 고정되니 장 마감 전에는 오늘 행을 주지 않는다(R-23, T-25). (c) 검색이 준 `symbol`이 그대로 저장되어 조회에 돌아오니 접미사 형식은 검색과 조회가 일치해야 한다(R-67 i). (d) `SecurityInfo.links`는 문자열, `kind`는 호출자가 읽지 않는다(R-67 j). (e) 통화가 비면 `USD`로 저장되고 환율 쌍은 저장된 시세 통화에서 정해지며 적재는 `Account::MarketDataImporter`가 한다(R-21, R-18). (f) 분할 조정 여부는 미결정이다(U-03). (g) provisional 재조회 구간 "7일"은 8개 날짜다(R-23). (h) MIC 없는 DB 조회는 정렬 없는 `first`라 같은 ticker의 여러 MIC 행 중 선택이 의미 없는 기준이다(U-04).
- 부동산(`property_valuations`): 기준 SHA의 평가 provider는 미국(RentCast, Realie)과 영국(Chimnie)용이고(R-64 `supported_country`), 한국 provider를 만들려면 `supported_country`, `valuation_currency`(KRW), `lookup_ready?`의 주소 필드, 월 예산 카운터를 능력 메서드로 정의해야 한다. 한국 주소는 `locality`·`region` 필수 필드와 맞는지 확인한다(미확인). 연동하지 않으면 job은 대상이 없어 아무것도 하지 않는다.
