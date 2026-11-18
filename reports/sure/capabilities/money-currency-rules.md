---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-17
updated: 2026-11-17
sources:
  - lib/money.rb
  - lib/money/arithmetic.rb
  - lib/money/currency.rb
  - lib/money/formatting.rb
  - config/currencies.yml
  - config/initializers/money.rb
  - app/models/exchange_rate.rb
  - app/models/exchange_rate/provided.rb
  - app/models/exchange_rate/importer.rb
  - app/models/exchange_rate_pair.rb
  - app/models/provider/exchange_rate_concept.rb
  - app/models/provider.rb
  - app/models/provider/registry.rb
  - app/models/setting.rb
  - app/models/concerns/monetizable.rb
  - app/models/concerns/iso_numeric_currency.rb
  - app/models/concerns/currency_normalizable.rb
  - app/models/family.rb
  - app/models/account.rb
  - app/models/entry.rb
  - app/models/transaction.rb
  - app/models/trade.rb
  - app/models/holding.rb
  - app/models/holding/portfolio_cache.rb
  - app/models/holding/trade_calculator_helpers.rb
  - app/models/balance/base_calculator.rb
  - app/models/balance/forward_calculator.rb
  - app/models/balance/reverse_calculator.rb
  - app/models/balance/sync_cache.rb
  - app/models/balance/chart_series_builder.rb
  - app/models/balance_sheet/account_totals.rb
  - app/models/concerns/accountable.rb
  - app/models/income_statement/scoped_transactions_query.rb
  - app/models/account/market_data_importer.rb
  - app/models/market_data_importer.rb
  - app/helpers/application_helper.rb
  - app/jobs/data_cache_clear_job.rb
  - app/models/property.rb
  - app/controllers/reports_controller.rb
  - app/models/transaction/search.rb
  - app/models/account_statement.rb
  - app/models/import/row.rb
  - app/models/security/price/import_windows.rb
  - app/models/security/manual_price_import.rb
  - app/controllers/currencies_controller.rb
  - app/controllers/api/v1/balance_sheet_controller.rb
  - app/jobs/market_data_reset_job.rb
  - app/components/UI/account_page.rb
  - db/schema.rb
  - docs/llm-guides/architecture.md
  - test/lib/money_test.rb
  - test/lib/money/currency_test.rb
  - test/integration/mixed_currency_test.rb
  - test/models/exchange_rate/importer_test.rb
depends: []
status: draft
---

# 금액·통화 규칙 (공유 계약)

> 금액(Decimal)과 통화 코드를 묶은 `Money` 값 객체, 통화 표(`config/currencies.yml`), 날짜별 환율 행(`exchange_rates`)을 입력으로 받아, 산술·비교·표시 규칙, 통화 환산과 환율 조회·적재 규칙, 거래 금액의 부호 규칙, family 대표 통화로 합치는 규칙을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

외화 거래 하나가 family 대표 통화 합계에 들어가기까지의 대표 경로다.

1. 거래·잔액·보유 항목은 금액(Decimal)과 자기 통화 코드를 각각 한 열씩 저장한다. 거래 금액은 음수가 유입, 양수가 유출이다(R-36).
2. 코드는 `<필드>_money`로 이 둘을 `Money(amount, currency)`로 묶어 쓴다(R-17). `Money`끼리 더하거나 비교할 때는 통화가 같아야 한다(R-07).
3. 통화가 다른 금액을 합치려면 먼저 `exchange_to(대상 통화, date:)`로 환산한다(R-21). `Money`는 혼자 환산하지 않는다.
4. 환산은 `exchange_rates` 행을 날짜로 찾는다. 같은 날 행이 없으면 최근 5일 안의 행, 그다음 외부 provider 순으로 찾는다(R-25). 합계용 경로(`rates_for`, `rate_sql`)는 더 오래된 행도 쓴다(R-26, R-27).
5. 환율을 끝내 못 찾으면 `ConversionError`를 던지거나 그 금액을 합계에서 뺀다. 환율 1로 대신하지 않는다(R-23, R-41, R-42).
6. `exchange_rates` 행은 동기화 때 `ExchangeRate::Importer`가 통화 쌍(from, to)별 구간으로 provider에서 받아 채운다. provider가 비워 둔 날은 직전 값으로 채우고, 같은 날짜의 역수 행도 같이 저장한다(R-30~R-33).
7. 화면·API에 보여 줄 때는 `format`이 통화의 소수 자릿수와 로케일 규칙으로 문자열을 만든다(R-11~R-14).

### 1.2 범위·통합 지점 [필수]

- 제공: `Money`의 산술·비교·반올림·표시, 통화 표와 통화별 소수 자릿수, 통화 코드 검증·정규화, 환산(`exchange_to`), 환율 행의 제약·조회 순서·fallback·gap 채우기·역수 행, 환율 provider가 만족해야 하는 인터페이스, 거래·평가 금액의 부호 규칙, 외화 금액을 family 대표 통화로 합칠 때 환율이 없는 경우의 처리.
- 제외:
  - 환율 provider 구현(Frankfurter, Twelve Data, Yahoo Finance, MOEX 등)의 HTTP·인증·throttle. 이 스펙은 `ExchangeRate`가 provider에 요구하는 인터페이스(R-29)까지만 다룬다.
  - `exchange_rates` 적재를 언제 호출하는지(스케줄, job, sync 순서). [sync-pipeline.md](./sync-pipeline.md)가 다룬다. 이 스펙은 "어떤 통화 쌍이 필요한지"(R-35)와 "호출되면 무엇을 하는지"만 쓴다.
  - 외부 provider 데이터의 부호·통화를 Sure 내부 `Entry`로 바꾸는 규칙. [provider-import-adapter.md](./provider-import-adapter.md)가 다룬다.
  - 일별 잔액 계산 전체, 이체 매칭의 교차 통화 허용오차, 수입·지출 보고서의 `kind` 분류. feature map의 행 1, 3, 14(스펙 미작성)가 다룬다. 이 스펙은 그쪽이 의존하는 부호·환산 규칙만 쓴다.
  - 화면 문구 번역, 로케일 파일(`config/locales`)의 내용.
- 외부 의존·선행 계약: 선행 스펙은 없다. 호출자가 제공해야 하는 것은 아래다.
  - 저장소: `exchange_rates`, `exchange_rate_pairs` 테이블(1.3). 같은 (from, to, date)에 대한 동시 쓰기를 DB unique 제약으로 막는 관계형 DB.
  - 키-값 캐시: 적재 중복 방지용 lock에 쓴다(R-30). TTL과 "없을 때만 쓰기"를 지원해야 한다.
  - provider 객체: 1.3의 "환율 provider 인터페이스"를 만족해야 한다. 설정이 없으면 provider 없음(nil)으로 취급한다(R-29).
  - "오늘"을 정하는 시계와 시간대. 원본은 요청·동기화 문맥의 시간대로 `Date.current`를 쓴다(1.4 확인 한계).
  - 오류 보고 수단(handled warning 한 건과 로그 한 줄을 남길 수 있는 것).
- 소유 상태·부작용:
  - `exchange_rates`, `exchange_rate_pairs` 행. `exchange_to`를 부르는 것만으로도 provider 호출과 행 저장이 일어날 수 있다(R-25).
  - 프로세스 안 전역 상태 두 가지. strict 플래그(R-07)와 "이미 보고한 통화 불일치" 집합(최대 500개, R-07).
  - `Money` 값 자체는 불변이다(R-02).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. `decimal`은 임의 정밀도 10진수(부동소수점이 아님)를 뜻한다. "행"은 DB 테이블의 한 줄이다.

**Money와 통화 표**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Money(amount, currency, store)` | amount: Money 또는 숫자(정수, 부동소수점, decimal). currency: 통화 코드 문자열 또는 Currency. 기본 `USD`. store: 환율 저장소, 기본 `ExchangeRate`. 출력: Money | amount와 currency를 보관하는 값 객체. 생성 뒤 바뀌지 않는다(R-01, R-02). |
| `Money.default_currency` | Currency | 프로세스 전역 기본값 `USD`. 코드에서 바꾸는 곳이 없다(R-01). |
| `+ - * /`, 단항 `-`, `abs`, `zero?`, `negative?`, `positive?`, `to_f` | Money와 숫자 | R-03~R-05. 코드는 C-06. |
| `==`, `<=>`와 파생 비교(`< > <= >=`) | Money 또는 정수 0 | R-06, R-07. |
| `exchange_to(currency, date, custom_rate)` | date 기본 "오늘", custom_rate는 선택. 출력: Money | 환산. 환율을 못 찾으면 `ConversionError`(R-21~R-23). |
| `for_display()` | Money | 통화 소수 자릿수로 반올림한 새 Money(R-08). |
| `format(options)`, `to_s` | options 맵. 출력: string | 옵션은 `locale`, `indian_grouping`(먼저 떼어 낸다)과 `unit`, `precision`, `delimiter`, `separator`, `format` 덮어쓰기다. 다른 키는 R-16 경로로 간다. R-11~R-14. 앱 코드가 넘기는 옵션은 `precision`을 확인했다(R-15). |
| `format_options(locale, indian_grouping)` | 출력: 옵션 맵 | `format`이 쓰는 기본 옵션 맵을 돌려주는 공개 메서드(R-11). |
| `as_json()` | `{amount, currency, formatted}` | currency는 대문자 코드, formatted는 `format()` 결과다. amount는 decimal의 직렬화이고 정확한 형태는 U-03이다(R-08). API v1 `balance_sheet`가 이 값을 응답에 그대로 쓴다. |
| Currency 레코드 | `name`, `priority`, `iso_code`, `iso_numeric`, `html_code`, `symbol`, `minor_unit`, `minor_unit_conversion`, `smallest_denomination`, `separator`, `delimiter`, `default_format`, `default_precision` | 통화 표(C-01)의 한 항목. 조회 규칙은 R-09, 소수 자릿수는 R-10, 그 밖의 공개 API는 R-43. |
| `Monetizable.monetize(필드...)` | 모델에 `<필드>_money` 접근자를 추가 | R-17. |

**환율 데이터와 조회**

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `exchange_rates` 행 | `id` uuid(기본 `gen_random_uuid()`), `from_currency` string not null, `to_currency` string not null, `date` date not null, `rate` decimal not null(정밀도·자릿수 제한 없음), `created_at`, `updated_at` not null | 한 방향 한 날짜의 환율. 1 `from` 단위가 몇 `to` 단위인지를 뜻한다(`amount * rate`로 환산, R-21). unique `(from_currency, to_currency, date)`. CHECK `rate > 0` 이고 NaN·무한대가 아님(제약 이름 `chk_exchange_rates_rate_positive`). 인덱스: `from_currency`, `(to_currency, updated_at)`, `updated_at`. 통화 코드의 길이·형식·존재 여부는 검사하지 않는다(R-24). |
| `exchange_rate_pairs` 행 | `from_currency` string not null, `to_currency` string not null, `first_provider_rate_on` date null, `provider_name` string null, `created_at`, `updated_at` | 통화 쌍마다 한 행(unique `(from_currency, to_currency)`). provider가 이 쌍에 대해 처음으로 준 유효 환율 날짜를 기억한다(R-34). |
| `ExchangeRate.valid_rate?(value)` | 숫자 또는 숫자 문자열 → bool | 유한하고 양수면 true. 변환 불가(숫자 아님, nil)는 false(R-24). |
| `find_or_fetch_rate(from, to, date, cache=true)` | 출력: 행 또는 provider가 준 Rate 또는 nil | 한 날짜의 환율 하나. `Money#store`가 요구하는 유일한 메서드다. `exchange_to`는 반환값의 `rate`(decimal)만 읽고, `rates_for`(R-27 단계 3)는 `date`도 읽는다(R-25). |
| `find_stored_rate(from, to, date)` | 출력: 행 또는 nil | provider를 부르지 않는다(R-26). |
| `rates_for(currencies, to, date)` | list of 통화 코드 → map `{통화: decimal}` | 여러 통화의 환율을 한꺼번에. 환율이 없는 통화는 맵에서 빠진다(R-27). |
| `rate_sql(from, to, on)` | SQL 식 문자열을 반환 | 인자는 값이 아니라 SQL 식(열 이름, 바인드 이름). 같은 통화면 1, 아니면 저장된 환율, 없으면 NULL(R-26). |
| `currencies_without_rate(currencies, to)` | list → list | 어느 날짜에도 `to`로 가는 환율 행이 없는 통화(R-28). |
| `stale_rate_dates(currencies, to, as_of)` | list → map `{통화: date}` | 가장 최근 환율이 `as_of`보다 5일을 넘게 오래된 통화(R-28). |
| `import_provider_rates(from, to, start_date, end_date, clear_cache=false)` | 출력: 호출자가 쓰지 않는 값 | 한 통화 쌍의 구간을 적재한다(R-30~R-33). |
| `CONVERSION_CACHE_VERSION` | string `"fx2"` | family 대표 통화로 환산한 값을 캐시하는 모든 키에 넣는다. 환산 규칙을 바꾸면 이 값을 올려야 한다(R-28). |

**환율 provider 인터페이스** (`ExchangeRate`가 provider에 요구하는 것)

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `fetch_exchange_rate(from, to, date)` | → Response(`success?`, `data: Rate`, `error`) | 한 날짜의 환율. 성공이어도 `data.date`가 요청 날짜와 다를 수 있다(R-25). |
| `fetch_exchange_rates(from, to, start_date, end_date)` | → Response(`success?`, `data: list of Rate`, `error`) | 구간의 일별 환율. 휴일·주말 행이 빠져 있어도 된다(R-32). 순서는 가정하지 않는다. |
| `max_history_days()` | → int 또는 nil | 선택 메서드. 값이 있으면 과거 몇 일까지만 줄 수 있는지다. nil이거나 메서드가 없으면 제한 없음(R-31). |
| Rate | `date`, `from`, `to`, `rate` | 한 날짜의 환율 값. |
| Response | `success?` bool, `data`, `error`(메시지를 가진 오류) | 실패는 예외가 아니라 `success? = false`로 전달한다. |
| 유효성 래퍼 | 모든 provider에 자동으로 붙는다 | 단건 응답의 rate가 `valid_rate?`가 아니면 실패 Response로 바꾼다. 구간 응답에서는 유효하지 않은 행만 버리고 성공으로 돌려준다. 버릴 때 경고 로그와 디버그 기록(category `exchange_rates`)을 남긴다(R-29). |

**환경 설정**

| 이름 | 값·기본값 | 의미 |
|---|---|---|
| `EXCHANGE_RATE_PROVIDER` (환경변수) | 비어 있으면 DB 설정 `exchange_rate_provider`, 그 기본값은 같은 환경변수 또는 `twelve_data` | 사용할 provider 이름. 등록된 이름은 `twelve_data`, `yahoo_finance`, `moex_public`, `frankfurter` 넷이다. 환경변수가 빈 문자열이면 없는 것으로 본다(R-29). |
| strict 플래그 | development·test는 켜짐, 그 외(production)는 꺼짐 | 통화가 다른 `Money`끼리 연산할 때 오류를 던질지 정한다(R-07). |

**금액·통화를 담는 열** (`db/schema.rb`)

| 열 | 제약 |
|---|---|
| `entries.amount` | numeric(19, 4), not null. 소수 5자리 이상 입력은 4자리로 맞춰 저장된다. 맞추는 곳은 ActiveRecord decimal 타입의 scale 적용(저장 전)일 가능성이 높고 DB도 같은 half up이다(추론: 둘 다 레포 밖 의미, R-02). |
| `entries.currency` | string, DB는 null 허용. 모델이 presence를 검사한다(R-18). |
| `accounts.currency`, `accounts.balance` | currency string null 허용(모델 presence 검사), balance numeric(19, 4). |
| `families.currency` | string, 기본 `"USD"`, null 허용(R-20). |
| 그 밖의 금액 열 | 대부분 numeric(19, 4)다. 예외: 신용카드의 `annual_fee`, `apr`, `available_credit`, `minimum_payment`는 numeric(10, 2)(`db/schema.rb:574-581`). 그 밖에 numeric(10, 6), (19, 10), (25, 10), (32, 18), (34, 18) 열이 있다(열별 용도는 읽지 않았다). |
| `balances.currency`, `security_prices.currency` | string, 기본 `"USD"`, not null(`balances`는 일별 잔액 테이블, `db/schema.rb:257-265`). |

### 1.4 행동 규칙과 남은 질문 [필수]

"strict 모드"는 R-07의 strict 플래그가 켜진 상태다. "환율 행"은 `exchange_rates`의 행이다.

**A. Money 값 객체**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Money(amount, currency)`를 만든다 | amount가 Money면 그 amount와 currency를 복사하고 currency 인자는 무시한다. 숫자(정수, 부동소수점, decimal)면 값을 문자열로 바꿔 decimal로 읽는다. 부동소수점 `1000.899`는 정확히 decimal `1000.899`가 된다. 문자열·nil·그 밖의 타입은 오류다(문자열 `"12.5"`는 decimal로 읽히지만 타입 검증에서 거부된다). currency를 생략하면 `USD`다. currency는 문자열·심볼·Currency만 받고 대소문자를 구분하지 않는다. 통화 표에 없는 코드는 `UnknownCurrencyError`, 다른 타입은 `ArgumentError`다. `Money`를 넘겨 만들 때 원본의 `store`는 복사하지 않고 새 `store`는 인자(기본 `ExchangeRate`)다. NaN·무한대 amount도 생성은 통과한다(검사 코드 없음). | 코드 확인 |
| R-02 | `Money`로 산술·환산·생성을 한다 | 모든 연산은 새 `Money`를 돌려주고 원본을 바꾸지 않는다. 연산·환산 중에는 반올림하지 않고 decimal의 전체 정밀도를 유지한다. 반올림은 `for_display`와 `format`에서만 하고, 둘 다 half up이다(경계값 0.5는 절댓값이 커지는 쪽: `0.125`를 2자리로 `0.13`, `-0.125`는 `-0.13`). 근거: `for_display`는 모드 없이 `round`를 부르고(decimal 기본 모드), `format`은 `round_mode`를 로케일 설정에서 읽는데 로케일 파일의 값이 전부 `default`다(`config/locales`에서 45건, 다른 값 없음). `default`와 decimal 기본 모드가 half up이라는 것은 레포 밖 라이브러리 의미에 기댄 추론이다. 소수 자릿수 제한은 저장할 때 열(`entries.amount` 등 소수 4자리)이 적용한다. | 코드 확인 (반올림 모드와 저장 시 맞춤 방식은 추론) |
| R-03 | `Money`에 `+` 또는 `-` | 상대가 `Money`면 통화를 확인(R-07)한 뒤 amount끼리 계산하고 결과 통화는 왼쪽 값의 통화다. 상대가 숫자면 통화 확인 없이 amount에 더하거나 빼고 통화는 유지한다. 숫자가 왼쪽이면(`n + money`, `n - money`) 언어의 coerce 규약으로 `money + n`, `money - n`이 계산된다. 따라서 `5 - Money(8, USD)`는 `Money(-3)`이 아니라 `Money(3, USD)`다. 배열 합계(`sum`)가 정수 0으로 시작해도 동작하는 이유가 이 규칙이다. | 코드 확인 (뒤집힘은 coerce 규약을 읽은 추론, 테스트는 같은 값끼리만 비교) |
| R-04 | `Money`에 `*` 또는 `/` | `Money * Money`는 `TypeError`다. `Money * 숫자`는 Money이고 `숫자 * Money`도 같은 결과다. `Money / Money`는 통화를 확인(R-07)한 뒤 amount의 비(단위 없는 decimal)를 돌려준다. `Money / 숫자`는 Money다. `숫자 / Money`는 `TypeError`다. `Money / 0`, `Money / Money(0)`을 위한 별도 처리는 코드에 없다. 결과(오류 종류, NaN·무한대)는 decimal 라이브러리 의미(레포 밖)에 달려 있고, 최선 추정은 `ZeroDivisionError`이지만 확인하지 못했다(U-02). | 코드 확인 (0 나눗셈 결과는 추론) |
| R-05 | 단항 `-`, `abs`, `zero?`, `negative?`, `positive?`, `to_f` | 부호를 뒤집은 Money, 절댓값 Money, amount의 영·음수·양수 판정, amount를 부동소수점으로 바꾼 값을 돌려준다. 통화는 유지한다. | 코드 확인 |
| R-06 | `==`와 `<=>` | 상대가 통화가 다른 `Money`면 `==`는 오류 없이 false다. 같은 통화면 amount가 같을 때 true다. `Money`가 아닌 상대는 `other.eql?(0)`이 참인 값만 비교할 수 있고 그때는 amount와 0을 비교한다(`Money(0) == 0`은 true). 정수 0뿐 아니라 decimal 0도 통과할 것으로 본다(추론: decimal의 `eql?`이 `==`와 같다는 레포 밖 의미). 부동소수점 `0.0`을 포함한 그 밖의 숫자(`Money(1) == 1`)는 `TypeError`다. `<=>`는 통화를 확인(R-07)한 뒤 amount를 비교하고, amount가 같으면 두 통화 코드 문자열의 비교 결과를 돌려준다. 같은 통화면 0이고, 통화가 다르면 amount가 같아도 0이 아니다(production에서 `Money(100, USD) <=> Money(100, EUR)`는 `USD`가 `EUR`보다 뒤라 1). `< > <= >=`는 이 `<=>`로 정해진다. `Money`는 해시 키로 쓸 값 동등성(`eql?`, `hash`)을 정의하지 않는다. | 코드 확인 (decimal 0 통과는 추론) |
| R-07 | 서로 통화가 다른 두 `Money`에 `+ - / <=>`(파생 비교 포함)를 쓴다 | strict 모드(development·test)면 `CurrencyMismatchError`(왼쪽 통화, 오른쪽 통화, 연산 이름 보관, 메시지 `Can't apply <연산> to <왼쪽> and <오른쪽> amounts; convert one with exchange_to first`)를 던진다. 연산 이름은 `+`, `-`, `/`, `<=>` 넷이고, `< > <= >=`는 이름이 따로 없이 모두 `<=>`로 기록된다. strict 모드가 아니면(production) 오류 없이 기존 결과를 돌려준다. `+`·`-`는 왼쪽 통화 Money(amount는 그대로 계산), `/`는 amount의 비, `<=>`는 amount를 비교하고 같으면 통화 코드를 비교한 결과다(R-06). 이때 (연산 이름, 왼쪽 통화, 오른쪽 통화, 호출 위치) 조합마다 프로세스당 한 번만 handled warning(source `money`)과 로그를 남긴다. 기억한 조합이 500개가 되면 집합을 비우고 다시 쌓는다(새 호출 위치는 계속 보고되고, 알려진 위치가 한 번 더 보고될 수 있다). `==`, `*`, 숫자와의 연산은 이 검사 대상이 아니다. 호출 위치는 연산자를 부른 소스 위치의 `파일:줄:메서드` 문자열이다(`caller_locations(2, 1)`, C-07). `<` 같은 파생 비교는 언어가 내부에서 `<=>`를 부르므로 그 연산을 쓴 줄이 위치가 되는 것으로 본다(추론). | 코드 확인 (파생 비교의 호출 위치는 추론) |
| R-08 | `for_display`, `as_json` | `for_display`는 amount를 통화의 `default_precision`자리로 반올림(0.5는 올림, half up)한 새 Money다. `Money(1000.6, JPY).for_display`는 `Money(1001, JPY)`다. `as_json`은 `{amount, currency(대문자 코드), formatted(format 결과)}`다. amount는 decimal을 직렬화한 값(문자열일 가능성이 높다, 추론)이고 `1000`이 `"1000.0"`인지 `"1000"`인지 같은 정확한 형태는 U-03이다. API v1의 `balance_sheet`(`net_worth`, `assets`, `liabilities`)가 이 값을 응답으로 쓴다. | 코드 확인 (amount 형태는 추론) |

**B. 통화 표와 소수 자릿수**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | `Currency(코드)` 조회 | 입력은 문자열·심볼·Currency만 받고(그 밖은 `ArgumentError`) 소문자로 바꿔 통화 표(C-01, 키는 소문자 코드)에서 찾는다. 없으면 `UnknownCurrencyError`(`ArgumentError`의 하위 클래스)다. 같은 코드는 같은 인스턴스를 재사용한다. 통화 표는 182개 항목이고 모든 키가 소문자 `iso_code`와 같다. 옵션 목록(`as_options`)은 `[priority, name]` 오름차순이다. `popular`는 `priority` 오름차순 상위 12개다. `step`은 `10^-default_precision`이다. 두 Currency는 `iso_code`로 비교한다. | 코드 확인 |
| R-10 | 통화별 소수 자릿수 | `default_precision`이 표시와 `for_display`의 자릿수다. 182개 중 0자리 29개(`KRW`, `JPY`, `CLP`, `HUF`, `ISK`, `VND`, `UGX`, `XOF` 등), 3자리 7개(`BHD`, `KWD`, `OMR`, `TND`, `LYD`, `IQD`, `JOD`), 4자리 1개(`CLF`), 8자리 3개(`BTC`, `DOGE`, `ETH`), 1자리 2개(`MGA`, `MRU`), 나머지 140개는 2자리다. `minor_unit_conversion`은 최소 단위의 개수(`USD` 100, `KRW` 1, `BTC` 10^8, `ETH` 10^18)이고 `default_precision`과 항상 일치하지는 않는다(`ETH`는 10^18인데 표시는 8자리, `MGA`·`MRU`는 5인데 표시는 1자리). 이 자릿수는 표시용이다. 저장·연산 정밀도는 R-02의 decimal이 정한다(`KRW` 금액도 소수 4자리까지 저장된다). | 코드 확인 |

**C. 표시(format)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | `format()` 기본 | 기본 옵션은 `{unit: 기호, precision: default_precision, delimiter, separator, format: default_format}`이고 통화 표 값에 R-12의 로케일 변경을 덮어쓴다. 호출자의 옵션이 마지막에 이긴다. 만드는 법(C-03, C-04): amount의 절댓값을 `precision`자리로 반올림(half up)하고, 정수부를 3자리마다 `delimiter`로 끊고, `precision`이 0이 아니면 `separator` 뒤에 소수부를 0으로 채워 붙인 뒤, `format`의 `%n`에 숫자, `%u`에 기호를 넣는다. `precision`이 0이면 소수부와 `separator`를 붙이지 않는다. 통화 표의 `default_format`은 `%u%n`(88개), `%n %u`(93개), `%u %n`(1개)이다. 예: `Money(1000.899, USD).format`은 `$1,000.90`, `Money(1234567, KRW).format`은 `₩1,234,567`. 옵션 처리(C-03): `locale`, `indian_grouping`은 먼저 떼어 낸다. 남은 옵션 키가 `unit precision delimiter separator format` 다섯 개를 벗어나거나 amount가 NaN·무한대면 이 단순 알고리즘 대신 프레임워크 `number_to_currency` 경로로 간다(R-16). 반올림은 항상 half up이다(R-02). | 코드 확인 |
| R-12 | 활성 로케일(없으면 `en`)별 변형 | 로케일 이름이 아래 중 하나면 표시 규칙을 덮어쓴다. 해당 없는 로케일(예: `ko`, `ja`, `zh-CN`)은 통화 표의 규칙을 그대로 쓴다. 그래서 통화 표에 유럽식 구분자(`.` 묶음, `,` 소수점)가 적힌 `EUR`은 `ko`에서도 그 구분자로 표시되고, `en`·`en-IE`에서만 예외로 `,` 묶음·`.` 소수점이 된다. 규칙 표는 C-02에 있다. 요약: `fr`은 NBSP 묶음·`,` 소수점·기호 뒤(NBSP). `de es it tr ca ro pt-PT`는 `.` 묶음·`,` 소수점·기호 뒤. `pl nb hu`는 공백 묶음·`,` 소수점·기호 뒤. `nl pt-BR`은 `.` 묶음·`,` 소수점·기호 앞(공백 포함). `MXN`과 `es`는 `%n %u`만 바꾼다. `EUR`과 `pt`는 `.`·`,`·`%u %n`. | 코드 확인 |
| R-13 | 인도식 묶음 | 통화가 `INR`이거나 로케일이 `en-IN en-IND hi hi-IN mr-IN ta te bn gu kn ml pa` 중 하나면 정수부를 `12,34,567`처럼 끝 3자리 뒤로 2자리씩 끊는다(패턴은 C-02). 이때 구분자는 항상 `,`, 소수점은 `.`로 고정해 다른 통화·로케일의 구분자와 섞이지 않게 한다. `indian_grouping: true`는 강제로 켜고 `false`는 묶음만 끈다(인도 로케일이면 구분자 고정은 유지). | 코드 확인 |
| R-14 | 기호와 음수 | 통화 `symbol`이 `$`이고 `iso_code`가 `USD`가 아니면 코드 앞 2글자를 붙여 `AU$`, `CA$`, `MX$`, `TW$`처럼 쓴다. 통화 표에서 이 규칙이 걸리는 통화는 USD 외 29개다(`AUD CAD SBD SGD SRD MXN NAD NZD XCD TTD TWD BZD CLP COP CUC CUP CVE DOP FJD ARS BBD BMD BND BSD KYD LRD GYD HKD JMD`, `symbol`이 `$`인 항목을 센 값). 음수는 `format` 앞에 `-`를 붙인다(`-$1,000.00`, `-1.000,00 €`). 반올림한 값이 0이 되는 음수는 부호를 붙이지 않는다(판정: `abs(amount) * 10^precision >= 0.5`일 때만 `-`). | 코드 확인 |
| R-15 | `format_money(값, 옵션)` 도우미 | 값이 nil이면 nil. `Money`면 그 통화로, 숫자면 `USD`로 `format`을 부른다. 앱 코드가 넘기는 옵션은 `precision`(주로 0)을 확인했고, `locale`·`indian_grouping`은 테스트에서만 쓴다. | 코드 확인 (검색 범위는 2.1) |
| R-16 | 로케일의 숫자 설정이 `significant` 또는 `strip_insignificant_zeros`를 켠 경우(예: `hu`, `pl`), 인도식 묶음, `format(locale: <활성이 아닌 로케일>)` | 원본은 단순 문자열 조립 대신 프레임워크의 `number_to_currency`를 거친다. 호출자가 다섯 옵션 키 밖의 키(`significant`, `negative_format` 등)를 넘기는 경우와 amount가 NaN·무한대인 경우도 같은 경로다(`lib/money/formatting.rb:18`, `:76`). 결과가 R-11의 단순 규칙과 달라질 수 있다(원본 테스트의 explicit locale 사례: `1000.00 USD`를 `hu`로 표시하면 `1 000 $`, `1000.50 USD`를 `pl`로 표시하면 `1 000,5 $`). 활성 로케일이 `en`·`ko`처럼 이 설정이 꺼져 있으면 R-11 규칙과 같다. 인도식 묶음의 결과는 R-13과 C-02의 패턴, R-11의 반올림·부호 규칙으로 재현할 수 있다. 그 밖의 경우의 정확한 규칙은 U-01. | 추론 |

**D. 통화 입력과 family 대표 통화**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-17 | 모델의 `<필드>_money` | 필드 값이 비어 있거나(nil·빈 문자열) 모델의 통화가 nil이면 nil이다. 아니면 `Money(필드 값, 모델의 통화)`다. 모델의 통화는 기본적으로 그 모델의 `currency` 값이고, 모델이 따로 정한 경우(예: family 대표 통화를 쓰는 집계 객체)가 있다. 따라서 `Entry`의 `amount_money`는 계정이 아니라 거래 자신의 `currency`를 쓴다. `<필드>_money`는 키워드 인자를 받아 그대로 필드 메서드에 넘긴다(`monetizable.rb:7-8`). `monetize` 호출에 붙은 `allow_nil:`, `as:` 옵션은 아무 동작도 하지 않는다. | 코드 확인 (옵션이 무동작이라는 판단은 언어 의미를 읽은 추론) |
| R-18 | 통화 코드가 저장·입력되는 경로 | 통화 코드 검증은 경로마다 다르다. (1) 모델 검증으로 통화 표에 있는지 확인하는 곳: `Family.currency`(통화가 바뀔 때만, R-20), `Import::Row`(`UnknownCurrencyError`를 검증 오류 `is not a valid currency code`로 바꾼다. 빈 값은 이 검증을 통과하고 `presence` 검증이 따로 막는다), `AccountStatement`. (2) 비어 있는지만 확인하는 곳: `Account`, `Entry`, `Holding`, `Goal`, `ExchangeRate`, `ExchangeRatePair`. (3) 모델 밖에서 직접 확인하는 곳: 보안 가격 수동 import(`Security::ManualPriceImport`는 대문자로 바꾼 코드를 통화 표 키에서 소문자로 찾고 없으면 `currency must be an ISO 4217 code`), 어시스턴트의 거래 생성 도구(`valid_currency?`는 `UnknownCurrencyError`·`ArgumentError`를 거짓으로 바꾼다), 선언된 청구서(`DeclaredBill`은 알 수 없는 코드를 저장하지 않고 무시해 계정 통화를 쓴다), 거래 분할 규칙(알 수 없는 코드면 소수 2자리로 대체한다) 등. (4) 표에 없는 코드가 (2)의 모델에 저장되면 나중에 그 값으로 `Money`를 만들 때 `UnknownCurrencyError`가 난다. 외부 provider 값은 `parse_currency`를 거친다. 값이 비어 있으면 로그 없이 nil이다. 앞뒤 공백을 지우고 대문자로 바꾼 뒤 `[A-Z]{3}`이 아니거나 통화 표에 없으면 경고 로그를 남기고 nil이다(예: `"XXX"`, `"invalid"`). | 코드 확인 ("이 목록 밖에는 검증이 없다"는 검색 범위 한정, 2.1) |
| R-19 | ISO 숫자 코드를 주는 provider(예: 980, 840) | `alpha_currency_code(코드)`는 숫자 코드를 문자열로 바꿔 앞뒤 공백을 지우고 3자리로 0 채움(`36`은 `036`)한 뒤 통화 표의 `iso_numeric`으로 알파벳 코드를 찾는다. 없거나 비어 있으면 nil. 숫자 코드가 빈 항목(암호화폐, `GBX`, `CNH` 등 11개)은 조회 대상이 아니다. `minor_unit_divisor(알파벳 코드)`는 통화의 `minor_unit_conversion`을 쓰고, 코드가 비었거나 통화 표에 없거나 값이 비어 있으면 100이다(`KRW`·`JPY`는 1). 이 provider들은 금액을 최소 단위(정수)로 주므로 이 나눗수로 나눠 decimal 금액으로 바꾼다. | 코드 확인 |
| R-20 | family 대표 통화 | `families.currency`는 기본 `USD`다. 저장 전에 대문자 코드로 바꾸고(`krw`는 `KRW`), 통화 표에 없는 값이면 검증 오류다(검증은 `currency`가 바뀔 때만 돈다. 이미 저장된 값이 표에 없어도 다른 속성을 고칠 때는 다시 검사하지 않는다). 값이 비어 있으면 `primary_currency_code`는 `USD`를 돌려준다. 통화 표에 없거나 타입이 틀린 값은 nil(오류 없음)로 정규화된다. 사용자가 고르는 통화 목록(`enabled_currencies`)을 따로 두면 대표 통화가 항상 포함되고, 통화 표 전체와 같아지면 nil(전체 허용)로 저장한다. | 코드 확인 |

**E. 환산과 환율 조회**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-21 | `exchange_to(대상, date, custom_rate)` | 대상의 통화 코드를 확인(통화 표에 없으면 `UnknownCurrencyError`)하고, 원래 통화와 같으면 자기 자신을 그대로 돌려준다(환율 조회 없음). 다르면 환율을 정해 `Money(amount * 환율, 대상)`를 돌려준다(C-08). 환율은 `custom_rate`가 있으면 그것, 없으면 `store.find_or_fetch_rate(from, to, date)`의 `rate`다. `date` 기본값은 "오늘"이다. 결과는 반올림하지 않는다. | 코드 확인 |
| R-22 | `custom_rate` 처리 | `custom_rate`가 비어 있지 않으면(nil·빈 문자열이 아니면) 그 값을 decimal로 바꿔 쓰고 `date`를 무시하며 저장소를 부르지 않는다. 값이 0이나 음수여도 저장소로 넘어가지 않고 `ConversionError`다. 거래·매매 한 건의 환율은 그 거래의 `extra.exchange_rate`(부동소수점)에 저장하고, 비우면 nil, 숫자가 아니거나 유한하지 않으면 저장 시 "must be a number", 0 이하면 "must be greater than 0" 검증 오류다. 잔액 계산은 이 값을 `custom_rate`로 넘긴다(R-40). | 코드 확인 |
| R-23 | 환율이 없거나 0 이하 | `ConversionError(from, to, date)`를 던진다. 메시지는 `Couldn't find exchange rate from <from> to <to> on <date>`다. 환율 1로 대신하지 않는다. 오류를 어떻게 처리할지는 호출자마다 다르다(R-42). | 코드 확인 |
| R-24 | `exchange_rates` 행을 쓴다 | 쓰기 전 모델 검증: `from_currency`, `to_currency`, `date`, `rate`가 있어야 하고, (from, to, date)가 유일해야 하며, `rate`는 유한한 양수여야 한다(`valid_rate?`: 숫자로 읽히지 않으면 false). 검증을 건너뛰는 일괄 upsert도 DB의 unique 제약과 CHECK 제약이 같은 규칙을 강제한다. 방향별로 행이 따로 있다(`USD→EUR`와 `EUR→USD`는 다른 행이고, 역수 행은 R-33이 따로 만든다). 쓰는 경로는 R-25의 단건 저장(`find_or_create_by!`와 불량 행 교체), R-32의 정방향 upsert, R-33의 역방향 upsert와 백필이다. 지우는 경로는 `DataCacheClearJob`(모든 행. `exchange_rate_pairs`는 지우지 않는다), 시장 데이터 초기화 job(쌍별 `[시작일, 끝일]` 구간을 지운 뒤 `clear_cache: true`로 다시 적재한다), 데모 데이터 정리다. | 코드 확인 (쓰고 지우는 곳이 더 없다는 것은 검색 범위 한정, 2.1) |
| R-25 | `find_or_fetch_rate(from, to, date, cache=true)` (R-21이 쓴다) | 아래 순서로 첫 번째 결과를 돌려준다. 환율이 0 이하인 행은 어느 단계에서도 무시한다. (1) `date`와 같은 날짜의 행. (2) `date`를 포함해 `date - 5일`까지 구간(양 끝 포함)에서 가장 최근 날짜의 행. (3) provider가 없으면 nil. (4) `provider.fetch_exchange_rate(from, to, date)`. 실패 응답이면 nil. 성공이고 `cache`가 거짓이면 그 Rate를 저장 없이 반환한다. 성공이면 `(rate.from, rate.to, rate.date)`로 행을 저장하고(없을 때만 만든다) 그 행이 아니라 provider가 준 Rate를 반환한다. 반환값의 날짜는 요청 날짜와 다를 수 있다(공급자가 가장 가까운 거래일을 줄 수 있고, 저장도 그 날짜로 한다). 동시 쓰기로 저장이 실패하면 상대가 저장한 행을 다시 읽어 쓰되, 그 행의 환율이 양수가 아니면 provider 응답을 쓴다. 이미 있는 행의 환율이 0 이하이고 provider 값이 양수면 행을 provider 값으로 고친다. 이 고침이 실패해도 provider 값이 답이다. 이 경로는 `date`보다 늦은 날짜의 행과 5일보다 오래된 행을 보지 않는다. 반환 객체의 `rate`는 `exchange_to`가, `date`는 `rates_for`(R-27)가 읽는다. | 코드 확인 |
| R-26 | 저장된 환율만 쓰는 조회(`find_stored_rate`, `rate_sql`) | 둘은 같은 규칙이다. `from`과 `to`가 같으면 1(`rate_sql`만 해당. `find_stored_rate`는 같은 통화를 특별 취급하지 않는다). 아니면 (1) `date`보다 같거나 이른 날짜 중 가장 최근 행(나이 제한 없음), (2) 없으면 `date`보다 늦은 날짜 중 가장 이른 행, (3) 둘 다 없으면 없음(`rate_sql`은 NULL, `find_stored_rate`는 nil). 환율 0 이하인 행은 건너뛴다. provider를 부르지 않는다. NULL과 곱한 값은 NULL이고 합계에서 빠진다. 환율이 없는 금액을 1로 계산하지 않기 위한 의도다. 코드는 C-09. | 코드 확인 |
| R-27 | `rates_for(통화 목록, to, date)` | 반환은 `{통화: decimal 환율}` 맵이다. 목록에 `to`가 있으면 `to`는 1이다. `to`가 목록에 없으면 맵에도 없다. `to`를 뺀 통화마다 아래 순서로 첫 결과를 쓴다. (1) `date`의 행. (2) `date - 5일 ~ date`의 가장 최근 행. (3) provider(R-25의 단건 조회를 부르고, 그 결과가 양수이면서 그 날짜의 행이 저장돼 있어야 인정). (4) 저장된 환율 중 `date` 이전 가장 최근(나이 제한 없음), 없으면 `date` 이후 가장 이른 것(R-26과 같음). 이 순서를 다 거쳐도 없는 통화는 맵에서 빠지고 경고 로그를 남긴다. 1로 채우지 않는다. 날짜가 요청과 다른 환율을 쓰면 디버그 로그에 간격(일)을 남긴다. 환율이 없을 때 그 금액을 어떻게 처리할지는 호출자가 정한다(R-41). | 코드 확인 |
| R-28 | 환율 상태 진단과 캐시 키 | `currencies_without_rate(통화들, to)`는 `to`와 nil을 뺀 통화 중 `to`로 가는 양수 환율 행이 어느 날짜에도 없는 것의 목록이다. `stale_rate_dates(통화들, to, as_of)`는 `as_of` 이하 날짜 중 가장 최근 양수 환율의 날짜가 `as_of - 5일`보다 이른 통화를 `{통화: 그 날짜}`로 돌려준다(`as_of` 이후 날짜 행은 무시, 환율이 아예 없는 통화는 제외). `Family`가 이 둘로 "환율 없음", "오래된 환율" 안내를 만든다(통화 대상은 계정·거래·보유가 쓰는 통화, 오래된 환율은 현재 잔액·보유의 통화만). 대표 통화로 환산한 값을 캐시하는 키(대시보드 계열)에는 `CONVERSION_CACHE_VERSION`(`"fx2"`)을 넣는다. | 코드 확인 |
| R-29 | provider 선택과 응답 검증 | provider 이름은 환경변수 `EXCHANGE_RATE_PROVIDER`가 있으면 그것, 없으면 설정값(기본 `twelve_data`)이다. 환경변수가 빈 문자열이면 없는 것으로 보고 설정값을 쓴다. 설정값의 기본값도 부팅 시 같은 환경변수에서 정해지므로, 환경변수가 빈 문자열이면 기본값도 빈 문자열이 되어 아래 오류가 나는 것으로 보인다(추론: 설정 객체가 빈 값을 기본값으로 바꾸는지는 열지 않았다). 등록된 이름이 아니면 오류를 던진다. `twelve_data`는 API 키(환경변수 또는 설정)가 없으면 provider 없음(nil)이다. nil이면 단건 조회는 nil을, 적재는 경고 로그 후 0을 반환한다. 모든 provider 응답에는 R-24의 `valid_rate?` 검증이 붙는다(1.3의 "유효성 래퍼"). 구간 응답에서 버려진 날짜는 이후 gap이므로 R-32가 직전 값으로 채운다. | 코드 확인 (빈 문자열 환경변수의 결과는 추론) |

**F. 환율 적재(`import_provider_rates`와 Importer)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-30 | `import_provider_rates(from, to, start_date, end_date)` 호출 | provider가 없으면 경고 로그 후 0을 반환하고 아무것도 하지 않는다. 있으면 `(from, to, start_date)`마다 키-값 캐시에 lock을 쓴다(키 `exchange_rate_import:<from>:<to>:<start_date>`, 값은 호출마다 새로 만든 uuid, TTL 5분, 키가 없을 때만 쓰기). lock을 못 얻으면(이미 진행 중) 로그 후 0을 반환한다. 얻으면 Importer를 실행하고, 끝나면(오류여도) lock 값이 자기 uuid일 때만 지운다. lock 범위에 `start_date`가 들어가므로 더 넓은 구간 요청은 좁은 구간 요청에 막히지 않는다. | 코드 확인 |
| R-31 | Importer가 구간을 정한다 | `end_date`는 오늘을 넘지 못한다(`min(요청 end_date, 오늘)`). 원본 의도(코드 주석): 오늘은 뉴욕 시간대의 오늘이다(`Date.current.in_time_zone("America/New_York").to_date`, `importer.rb:284-289`). 실제 동작(추론): `Date#in_time_zone(zone)`은 그 날짜의 해당 zone 자정 시각을 만들 뿐이어서 `.to_date`가 같은 날짜로 돌아오므로 시간대 변환이 일어나지 않고, 상한은 활성 시간대의 오늘(`Date.current`)이다. 이 판단은 프레임워크(ActiveSupport) 의미에 기댄 추론이다. `clamped_start`는 쌍의 `first_provider_rate_on`이 있고 `start_date`보다 늦으면 그 날짜, 아니면 `start_date`다. `clear_cache`가 참이면 `effective_start`는 `start_date`, 아니면 `[clamped_start, end_date]`에서 환율 행이 없는 첫 날짜(모두 있으면 `end_date`)다. provider 요청 시작일은 `effective_start - 5일`이고, provider의 `max_history_days`가 있어 `end_date`와의 간격이 그보다 크면 `end_date - max_history_days`로 줄인다. 채우기 시작일 `fill_start`는 `max(요청 시작일, effective_start)`다. `clear_cache`가 거짓이고 `[clamped_start, end_date]`의 모든 날짜에 행이 이미 있으면 provider를 부르지 않고 R-33의 역수 백필만 하고 끝낸다. `first_provider_rate_on`은 `DataCacheClearJob`이 행을 지운 뒤에도 남으므로, 지운 뒤 다시 적재하면 `clamped_start`가 `start_date`보다 늦어져 그 앞 구간은 다시 받지 않는다(provider가 그 이전 데이터를 갖지 않는다고 기억하기 때문이다, R-24, R-34). | 코드 확인 (끝 날짜 상한의 실제 동작은 추론) |
| R-32 | Importer가 gap을 채운다 | `provider.fetch_exchange_rates(from, to, 요청 시작일, end_date)`로 받은 행을 날짜로 찾을 수 있게 둔다. 실패면 경고 로그와 오류 추적 보고 후 빈 응답으로 취급한다. 응답이 비면 경고 로그 후 아무것도 쓰지 않고 끝낸다. 시작 환율을 정한다. `fill_start == start_date`면 provider 행 중 `start_date` 이하의 가장 최근 양수 환율, 없으면 그 날의 저장 행(양수일 때), 없으면 없음이다. 그렇지 않으면 provider 행 중 `fill_start` 이전의 가장 최근 양수 환율, 없으면 `fill_start` 이전 저장 행 중 가장 최근 양수 환율(나이 제한 없음)이다. 시작 환율이 없고 provider에 양수 환율이 하나라도 있으면 가장 이른 양수 환율 날짜로 채우기 시작일을 옮기고 그 값을 시작 환율로 쓴다(쌍이 provider 역사보다 오래된 경우). 그래도 없으면 `MissingStartRateError`를 로그·오류 추적에 남기고 아무것도 쓰지 않는다. 실제 provider는 유효성 래퍼(R-29)가 0 이하·nil 행을 먼저 버리므로 모두 무효인 응답은 위의 "응답이 비면" 경로로 끝나고, 이 오류 경로는 래퍼를 거치지 않는 provider 객체에서만 나온다(추론). 채우기 시작일부터 `end_date`까지 모든 달력 날짜에 대해 (C-10) 그 날의 provider 양수 환율, 없으면 그 날의 저장 행 양수 환율, 없으면 직전 날짜에 쓴 값(마지막 관측값 이월, 주말·휴일 gap)을 쓴 행을 만들어 (from, to, date) 기준으로 200건씩 upsert한다. provider 값이 같은 날 저장 행보다 우선하므로 오래된 행이 새 provider 값으로 덮어써진다. | 코드 확인 |
| R-33 | 역수 행 | R-32로 만든 각 행(환율 0 이하 제외)마다 `to→from` 행을 같은 날짜로 upsert한다. 환율은 `1 / rate`를 소수 12자리로 반올림(half up)한 값이다. 반올림 결과가 유효하지 않으면(0이 되면) 그 날짜는 건너뛴다(C-11). 정방향 환율이 2×10^12이면 역수 `5×10^-13`이 half up으로 `10^-12`가 되어 행이 만들어지고, 3×10^12이면 0이라 건너뛴다. 마지막에 백필을 한다. `[clamped_start, end_date]`의 역방향 행 수가 날짜 수 이상이면 하지 않는다. 아니면 이 호출 전에 있던 정방향 저장 행(`[start_date, end_date]`) 가운데 그 날짜의 역방향 행이 `[clamped_start, end_date]`에 없는 것의 역수 행을 만든다. `first_provider_rate_on`이 `start_date`보다 늦은 쌍은 `[start_date, clamped_start)` 구간의 역방향 행이 이미 있어도 이 조회가 보지 않으므로 그 구간의 역수 행을 다시 만들어 덮어쓴다. | 코드 확인 (반올림 모드는 추론) |
| R-34 | 쌍 메타데이터 | 쌍 행은 처음 필요할 때 만들고, 동시에 만들어 unique 충돌이 나면 기존 행을 읽는다. 행에 기록된 `provider_name`이 현재 provider와 다르고 `first_provider_rate_on`이 있으면 `first_provider_rate_on`을 비우고 `provider_name`을 현재 값으로 바꾼다(provider가 바뀌면 처음 환율 날짜를 다시 알아낸다). R-32가 provider에서 가장 이른 양수 환율 날짜를 찾았으면 `first_provider_rate_on`이 비었거나 그 날짜보다 늦을 때만 그 날짜로 바꾼다(앞으로 늦추지 않는 조건부 갱신). 화면(`UI::AccountPage#fx_coverage_start_date`)도 외화 계정을 렌더링할 때 `for_pair`로 이 행을 읽고, 그 호출만으로 쌍 행이 만들어진다. 이 값이 계정의 가장 이른 거래일보다 늦으면 화면이 그 날짜를 안내한다. | 코드 확인 |
| R-35 | 필요한 환율 쌍 (적재 대상을 정하는 규칙, 호출 시점은 [sync-pipeline.md](./sync-pipeline.md)) | 모든 쌍의 끝 날짜는 오늘이고, 쌍의 환율은 `(from → to)` 방향 하나다. **계정 하나 기준**(`Account::MarketDataImporter`. provider가 있고 외화 항목·외화 계정·외화 가격 증권 중 하나가 있어야 하며, 없으면 아무것도 하지 않는다. `clear_cache`는 넘기지 않는다): (1) 계정의 항목 전체(거래·매매·평가 항목 포함) 중 통화가 계정 통화와 다른 것을 통화별로 묶어 최초 날짜 d를 구한다. 각 통화에서 `{계정 통화, family 대표 통화}`(같으면 한 번, 자기 자신과 같은 대상은 제외)로 가는 쌍이 d부터 필요하다. 이체가 family 대표 통화를 거쳐 환산하기 때문이다. (2) 계정 통화가 family 대표 통화와 다르면 `(계정 통화 → family 대표 통화)`가 `계정.start_date`부터 필요하다. `계정.start_date`는 항목 최초 날짜(항목이 없으면 오늘)의 하루 전이다. (3) 증권: 계정의 증권마다 필요 시작일 W를 구한다. W는 첫 매매일, 수량이 양수인 첫 보유일, 그 증권을 provider 보유로 받았으면 `계정.start_date` 중 가장 이른 날이고, 그런 날이 없으면 `계정.start_date`다. 그 증권의 이미 저장된 가격 중 통화가 계정 통화와 다른 것만 대상이다. (증권, 통화)별 가장 최근 가격 날짜 L이 W보다 이르면 건너뛴다. 아니면 `(가격 통화 → 계정 통화)`가 필요하고 시작일은 통화별로 W 중 가장 이른 값이다. 저장된 가격이 없으면 쌍이 만들어지지 않는다. 같은 쌍이 여러 규칙에서 나오면 가장 이른 시작일을 쓴다. **전체 기준**(`MarketDataImporter`. provider가 없으면 경고 후 끝낸다. `clear_cache`를 그대로 `import_provider_rates`에 넘긴다): (1) 모든 항목 중 `항목 통화 ≠ 계정 통화`인 것을 (항목 통화, 계정 통화, family 통화)로 묶은 최초 날짜부터 `{계정 통화, 정규화한 family 통화(없으면 USD)}`로 가는 쌍. (2) `family 통화 ≠ 계정 통화`인 계정마다 `(계정 통화 → family 대표 통화)`가 `min(그 계정의 최초 항목 날짜, 31일 전)`부터 필요하다(항목이 없는 계정은 31일 전). 계정 기준과 달리 하루를 빼지 않는다. (3) 증권 가격 통화 쌍은 이 경로에 없다. 모드가 `snapshot`이면 모든 쌍의 시작일이 31일 전이다. 끝 날짜는 이 경로에서도 R-31의 "뉴욕 오늘"(실제로는 활성 시간대의 오늘, 추론)이다. | 코드 확인 (끝 날짜 상한은 R-31의 추론) |

**G. 거래 금액의 부호와 대표 통화 환산**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-36 | 거래(`Transaction`)·매매(`Trade`) 항목의 `Entry.amount` | 음수는 유입(수입), 0 이상은 유출(지출)이다. `Entry`의 `classification`은 `amount < 0`이면 `income`, 아니면(0 포함) `expense`다. 이 부호는 계정의 자산·부채 구분과 무관하게 같다. 음수인 체크 계좌 거래는 현금을 늘리고, 음수인 신용카드 거래(카드 대금 납부)는 부채를 줄인다. | 코드 확인 |
| R-37 | 하루의 거래가 계정 잔액에 반영된다 | 계정 분류는 `Loan`, `CreditCard`, `OtherLiability`가 부채(`liability`), 나머지가 자산(`asset`)이다. 부채 계정의 `balance`는 갚아야 할 크기를 양수로 저장한다. 자산 계정은 하루 거래 금액의 합을 빼서(`잔액 - Σamount`), 부채 계정은 더해서(`잔액 + Σamount`) 다음 잔액을 만든다. 거꾸로 계산(역방향)하면 반대다. 하루 흐름 집계에서 `amount < 0`인 거래는 현금 유입, `amount >= 0`은 현금 유출이다. 대출 계정은 원금 변화(`loan_principal_change`)가 없을 때 같은 부호를 비현금(원금) 유입·유출로 쓰고, 있으면 그 값(`principal_paid`는 유입, `principal_added`는 유출)이 대신한다. 이 계산에 들어가는 항목은 R-40이 정한다. | 코드 확인 |
| R-38 | 매매(`Trade`) 금액 | 매수(`amount >= 0`)는 현금 유출이고 보유(비현금) 유입이다. 매도(`amount < 0`)는 현금 유입이고 보유 유출이다. 수량이 0인 매매(배당·이자)는 현금 흐름만 만들고 비현금 흐름은 만들지 않는다. | 코드 확인 |
| R-39 | 평가(`Valuation`) 항목의 `Entry.amount` | 유입·유출이 아니라 그 날의 계정 총 잔액을 뜻하는 절댓값이다. 잔액 계산이 부호를 바꾸지 않고 그대로 총 잔액으로 쓰며, 부채 계정의 평가도 양수(갚을 금액)다. 같은 계정·같은 날짜의 평가 항목은 하나만 허용한다. 평가 금액이 음수가 아니어야 한다는 검증은 찾지 못했다. 이동 방향 부호(R-36)를 평가 금액에 적용하면 안 된다. | 코드 확인 ("검증 없음"은 검색 범위 한정, 2.1) |
| R-40 | 잔액 계산 중 다른 통화의 항목을 계정 통화로 바꾼다 | 잔액 계산이 읽는 항목은 계정의 항목 중 보류(pending) 중인 것과 분할된 원본(split parent)을 뺀 것, 날짜가 오늘(`Date.current`) 이하인 것이다(미래 항목 제외). 하루의 흐름(R-37, R-38)에 쓰는 것은 그중 거래·매매뿐이고 평가 항목은 따로 그 날의 총 잔액으로 쓴다(R-39). 환산이 성공한 항목은 금액과 통화가 계정 통화 값으로 덮어써진다. 각 거래·평가·매매는 `entry.date`의 환율로 계정 통화로 환산한다(R-21). 환율은 거래의 `extra.exchange_rate`가 있으면 그것(R-22), 없으면 R-25다. 환산이 `ConversionError`면 그 항목을 계산에서 빼고(이유: 1:1로 쓰면 환율 간격만큼 잔액이 틀린다) 건수와 통화 쌍을 오류 보고에 남긴다. 보유(holding)의 환산 실패는 반대로 1:1(원래 금액)로 계산한다. 보유를 빼면 `총 잔액 - 보유 평가액`으로 구한 현금이 가짜로 늘어나기 때문이고, 같은 방식으로 건수와 통화 쌍을 보고한다. | 코드 확인 |
| R-41 | 여러 통화의 계정·거래를 family 대표 통화로 합친다 | 합계는 경로에 따라 환율 규칙이 다르다. 모든 경로에서 환율이 없는 금액은 1로 계산하지 않고 합계에서 뺀다. (1) 계정 잔액 합계(순자산, 계정 종류별 합계): `rates_for(외화 목록, family 통화, 오늘)`(R-27)로 현재 환율을 쓴다. 환율이 없는 계정은 0으로 계산해 합계에서 빠지고 그 계정의 행에는 자기 통화 잔액이 그대로 보인다. (2) 기간별 거래 합계(수입·지출, 검색 합계, 투자 합계): 항목마다 `rate_sql(거래 통화, family 통화, 거래 날짜)`(R-26)로 곱한다. 환율이 없으면 NULL이라 합계에서 빠지고, 합계 식은 전부 빠졌을 때 0을 읽도록 `COALESCE`로 감싼다. 중앙값·평균 같은 통계는 일부러 NULL로 두어 환산할 수 없는 기간을 건너뛴다(지출 0인 기간으로 세지 않는다). (3) 일별 잔액 차트: 날짜마다 그 날짜 이전 가장 최근 환율(없으면 이후 가장 이른 환율)로 계정별 잔액을 곱한다. 환율이 없으면 그 계정은 그 날의 합에서 빠진다. 호출자가 엄격 모드를 켜면(목표 진행도) 대신 `ConversionError`를 던진다. 환산 결과를 캐시하는 키에는 `CONVERSION_CACHE_VERSION`을 넣는다(R-28). | 코드 확인 |
| R-42 | 환산 호출자가 `ConversionError`를 받는다 | 처리는 호출자마다 다르고 통일된 규칙이 없다. 확인한 것: 잔액 계산은 항목을 빼고 보유는 1:1(R-40). 예정 거래 미리보기 환산은 항목을 뺀다. 외부 계정의 잔액 환산(`convert_provider_balance`)은 nil을 돌려주고 호출자가 0으로 대신한다. 매도 실현손익은 거래일·방향이 같은 환율 행만 쓰고(5일 조회·반대 방향 없음) 없으면 값을 만들지 않는다(nil). 보유 평단 환산에서 환율이 없으면 평단을 모름(nil)으로 둔다. 증권 가격 일별 캐시는 원래 가격을 그대로 쓴다(1:1). 보유 금액 환산(`amount_in_account_currency`)은 호출자가 정한 대체값을 쓴다. 이 목록 밖의 호출처(`ConversionError`를 받는 곳이 전부 약 30곳)는 읽지 않았다. 읽은 곳 중 환산 실패 시 1:1을 쓰는 곳은 보유 환산(R-40)과 증권 가격 캐시다. | 코드 확인 (호출처 전수는 아님, 2.1) |
| R-43 | `Currency`의 공개 API | `Money::Currency.all`은 통화 표 원본(소문자 코드 → 항목 맵)을 그대로 돌려주고 다른 코드가 직접 쓴다(통화 존재 확인, 항목의 `default_precision` 최댓값 계산). `Currency#as_json`은 인스턴스의 모든 속성을 맵으로 직렬화한 것으로 보이고(추론), 통화 조회 화면 엔드포인트는 `iso_code`가 `params[:id]`와 같은 통화를 찾아 이 맵에 `step`을 더해 JSON으로 렌더한다. `step`은 `1.0 / 10^default_precision`의 부동소수점이다(`KRW`는 `1.0`, `USD`는 `0.01`). 일치하는 통화가 없으면 오류가 난다(nil에 `merge`를 호출하게 된다). | 코드 확인 (as_json 직렬화 형태는 추론) |

- 불변식:
  - 환율 행의 `rate`는 항상 유한한 양수다(DB CHECK, 모델 검증, provider 래퍼 세 겹).
  - 금액이 있는 모든 행은 자기 통화를 함께 가진다. 통화가 다른 두 금액을 `exchange_to` 없이 더하는 코드는 strict 모드에서 오류가 된다.
  - 적재 뒤에는 (from, to)의 `fill_start`부터 `end_date`까지 달력 날짜마다 행이 하나씩 있다(provider가 준 날, 저장돼 있던 날, 직전 값으로 채운 날). 전제: 시작 환율을 정할 수 있어야 하고(R-32), provider 응답이 비어 있지 않아야 한다.
  - "환율 없음"과 "환율 1"을 구별한다. 환율 조회는 없음을 맵에서 빼거나 NULL, nil, 오류로 표현하고 1로 대체하지 않는다. 예외 두 곳(보유 환산, 증권 가격 캐시)은 R-40, R-42에 적었다.
  - `Money` 연산은 입력을 바꾸지 않는다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-16 | 활성 로케일의 숫자 설정에 `significant: true` 또는 `strip_insignificant_zeros: true`가 있는 로케일(`config/locales/defaults/<로케일>.yml`의 `number.format` 또는 `number.currency.format`, 예: `hu`, `pl`)에서 `format`이 프레임워크의 `number_to_currency`를 거친 정확한 출력 규칙. 활성 로케일이 아닌 로케일을 `locale:`로 넘기는 호출은 앱 코드에 없고 테스트에만 있다. | 이런 로케일을 지원하는 구현이 `hu`에서 `1 000 $`처럼 유효숫자·0 제거가 섞인 결과를 재현하려면 규칙을 정해야 한다. `en`·`ko`만 지원하는 구현은 영향이 없다(두 로케일 모두 해당 설정이 꺼져 있다). | 프레임워크의 `ActiveSupport::NumberHelper::NumberToCurrencyConverter` 소스(레포 밖)와 로케일 파일의 `number` 절을 열어 대조한다. |
| U-02 | R-04 | `Money / 0`, `Money / Money(0)`의 결과. 코드에 별도 처리가 없어 decimal 라이브러리(레포 밖)의 0 나눗셈 의미에 달려 있다. 오류(`ZeroDivisionError`)인지 NaN·무한대 값인지 확인하지 못했다. | 0 나눗셈에서 오류를 던질지 특수 값을 돌려줄지 구현자가 정해야 한다. 원본 호출처가 0 나눗셈을 미리 피하는지는 읽지 않았다. | Ruby `bigdecimal`의 0 나눗셈 동작(레포 밖)을 확인하고, `app`의 `Money` 나눗셈 호출처를 검색한다. |
| U-03 | R-08 | `Money#as_json`의 amount가 API 응답에서 어떤 문자열인가(`1000`이 `"1000.0"`인지 `"1000"`인지, 소수 끝 0 유지 여부, 큰 값의 지수 표기). API v1 `balance_sheet`가 이 값을 그대로 응답한다. | API 클라이언트가 받는 금액 문자열 형식이 달라진다. 호환이 목적이면 형식을 정해야 한다. | 프레임워크의 decimal `as_json`(레포 밖)을 확인하거나 `docs/api/openapi.yaml`, `test/controllers/api/v1/balance_sheet_controller_test.rb`의 예시 값을 연다(열지 않았다). |

- 확인 한계:
  - 어떤 코드도 실행하지 않았다(rails·ruby 미실행). 출력 문자열 사례(1.6)는 코드를 손으로 따라가 도출했고, 원본 테스트 `test/lib/money_test.rb`에 같은 값이 있는 사례는 출처에 적었다.
  - "오늘"(`Date.current`)은 활성 시간대의 날짜다. 웹 요청은 사용자·family·브라우저 순으로 정한 시간대(`Localize`)를, 동기화는 family 시간대를 쓰고, 그 밖에는 프레임워크 기본(설정 파일에서 주석 처리돼 UTC)이다. 시간대를 정하는 규칙 자체는 이 스펙의 범위 밖이다. 적재의 `end_date` 상한은 코드 주석상 뉴욕 시간대의 오늘이지만, 실제로는 활성 시간대의 오늘일 것으로 추론했다(R-31, 프레임워크 의미에 기댄 추론).
  - 외부 provider가 실제로 어떤 날짜를 돌려주는지는 확인하지 못했다. R-25의 "가장 가까운 거래일을 줄 수 있다"는 코드 주석의 주장이고 외부 서비스 동작은 `미확인`이다.
  - 호출처 전수(`exchange_to` 호출 42곳, `ConversionError` 처리 약 30곳)를 모두 읽지 않았다. R-42는 읽은 곳만 표로 적었다.

### 1.5 필수 코드 참조 [필수]

라이선스는 AGPL-3.0이다(overview 1절). 이 스펙은 줄 범위만 가리키고 코드를 복사하지 않았다. 코드를 가져다 쓰면 AGPL 의무가 따른다(2.3).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `config/currencies.yml:1-2548` 통화 표 182개 | 통화별 `name`, `priority`, `iso_code`, `iso_numeric`, `html_code`, `symbol`, `minor_unit`, `minor_unit_conversion`, `smallest_denomination`, `separator`, `delimiter`, `default_format`, `default_precision` 값. 데이터 파일이다. `KRW`(`:1975-1988`)는 기호 `₩`, `separator "."`, `delimiter ","`, 형식 `%u%n`, 소수 0자리, `minor_unit_conversion 1`이다. `USD`(`:1-14`)는 `$`, 형식 `%u%n`, 2자리, 100이다. 암호화폐 `BTC`, `DOGE`, `ETH`와 비ISO 코드(`GBX`, `CNH`, `USDC`, `USDT` 등)도 들어 있다. | R-09, R-10, R-11, R-19 |
| C-02 | `lib/money/formatting.rb:6-16`, `:121-155` `EUROPEAN_SYMBOL_AFTER`, `SPACE_DELIMITER_SYMBOL_AFTER`, `EUROPEAN_SYMBOL_BEFORE`, `INDIAN_*`, `locale_options` | 로케일 이름 집합과 로케일별 `delimiter`·`separator`·`format` 덮어쓰기 표, 인도식 묶음 정규식. `locale_options`는 `MXN`+`es` → `fr` → 유럽식 기호 뒤 → 공백 묶음 → 유럽식 기호 앞 → `EUR`+`pt`, `EUR`+`en` 순으로 첫 일치를 쓴다. | R-12, R-13 |
| C-03 | `lib/money/formatting.rb:21-67` `format`, `format_options` | 옵션 병합 순서(통화 표 값 → 로케일 덮어쓰기 → 호출자 옵션), 인도식 묶음일 때 구분자 고정. | R-11, R-13 |
| C-04 | `lib/money/formatting.rb:18-19`, `:73-99` `FAST_FORMAT_KEYS`, `DELIMITER_REGEX`, `fast_format` (78-84줄의 프레임워크 로케일 조회 제외) | 단순 경로의 반올림·묶음·부호·`%n`·`%u` 치환 알고리즘, 단순 경로를 쓸 수 있는 옵션 키 집합(18줄), 3자리 묶음 정규식(19줄). 78~84줄은 로케일의 숫자 설정을 확인해 단순 경로를 쓸지 정하는 부분이고 R-16, U-01이 다룬다. 85줄의 `round_mode`는 93줄 반올림에서 쓰이며, 로케일 파일 어디에도 `default` 외의 값이 없어 half up이다(R-02). | R-11, R-14 |
| C-05 | `lib/money/formatting.rb:101-119` `indian_grouping?`, `indian_locale?`, `get_symbol` | 인도식 묶음 켜짐 판정 우선순위(명시 옵션 > 통화 `INR` > 로케일)와 `$` 기호 앞 2글자 규칙. | R-13, R-14 |
| C-06 | `lib/money/arithmetic.rb:1-69` | 연산자 정의 전체(R-03~R-05의 동작). 숫자가 왼쪽일 때의 `coerce` 규약(66-68줄)은 이 언어 고유 장치이고 R-03이 동작으로 풀어 썼다. | R-03, R-04, R-05 |
| C-07 | `lib/money.rb:5-31`, `:33-66`, `:120-159` `ConversionError`, `CurrencyMismatchError`, `REPORTED_MISMATCHES_LIMIT`, `strict_currency?`, `first_mismatch_report?`, `==`, `<=>`, `ensure_same_currency!` | 오류 클래스의 필드와 메시지, 보고 기억의 상한(500)과 비우기, 비교 규칙, 통화 불일치 검사·보고. `caller_locations(2, 1)`은 연산자를 부른 코드 위치(호출 위치)다. | R-06, R-07, R-23 |
| C-08 | `lib/money.rb:91-109` `exchange_to` | 환산 우선순위와 오류 조건. | R-21, R-22, R-23 |
| C-09 | `app/models/exchange_rate/provided.rb:160-171` `rate_sql` | 저장 환율 조회 SQL(같은 통화 1, 이전 최근, 이후 최초, NULL). `exchange_rates` 열 이름만 쓰는 자기완결 SQL이다. | R-26 |
| C-10 | `app/models/exchange_rate/importer.rb:55-77` | gap 채우기 반복(provider 양수 → 저장 양수 → 직전 값). 입력 `loop_start_date`, `prev_rate_value`, 두 날짜별 맵은 R-32가 정의한다. | R-32 |
| C-11 | `app/models/exchange_rate/importer.rb:255-261` `inverse_rate` | 역수를 12자리로 반올림하고 유효하지 않으면 건너뛴다. | R-33 |
| C-12 | `app/models/concerns/iso_numeric_currency.rb:11-49` `class << self`의 `alpha_by_numeric`(모듈 수준 메서드), `alpha_currency_code`, `minor_unit_divisor`, `normalize_numeric_code` | 숫자 코드 → 알파벳 코드 맵(통화 표에서 만들고 처음 나온 항목 우선), 0 채움, `minor_unit_divisor` 기본 100. | R-19 |
| C-13 | `app/models/balance/base_calculator.rb:116-162` `flows_for_date` | 거래·매매·배당의 금액 부호가 현금·비현금 유입·유출로 나뉘는 규칙과 대출 계정 예외. | R-37, R-38 |
| C-14 | `app/models/balance/forward_calculator.rb:153-160`, `app/models/balance/reverse_calculator.rb:98-101` `signed_entry_flows` | 자산은 `-Σamount`, 부채는 `+Σamount`(역방향은 반대). 대출 원금 변화가 있으면 그 값이 우선한다(forward 154-156줄). 대출 원금 계산은 이 스펙 범위 밖이다. | R-37 |

### 1.6 수락 사례 [필수]

출처: 별도 표기가 없으면 구현에서 도출(코드를 따라가 계산). 표기한 것은 원본 테스트(`test/lib/money_test.rb` 등)에 같은 값이 있다. 환율 DB를 쓰는 사례는 provider가 없는 환경(`provider = nil`)을 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-02, R-11 | `Money(1000.899)`(통화 생략) 후 `format`, `for_display` (원본 테스트) | amount `1000.899`, 통화 `USD`. `format`은 `$1,000.90`. `for_display`는 amount `1000.9`. 원래 Money는 그대로 `1000.899`. |
| T-02 | R-10, R-11, R-08 | `Money(1000.6, KRW)`, `Money(1234567, KRW)` | `for_display`는 `Money(1001, KRW)`(JPY는 원본 테스트). `format`은 `₩1,001`, `₩1,234,567`. 활성 로케일이 `ko`여도 같다(로케일 변형 없음). |
| T-03 | R-01 | `Money("12.5")`, `Money(nil)`, `Money(1, "ZZZ")`, `Money(1, 5)` | 앞 둘은 오류(타입 검증 실패, decimal 읽기 실패). 셋째는 `UnknownCurrencyError`. 넷째는 `ArgumentError`. |
| T-04 | R-07 | `Money(200, USD) - Money(180, EUR)`, strict 모드 (원본 테스트) | `CurrencyMismatchError`(left `USD`, right `EUR`). 메시지 `Can't apply - to USD and EUR amounts; convert one with exchange_to first`. `+`, `/`, `<=>`도 strict 모드에서 같은 오류다. `> < >= <=`는 연산 이름이 모두 `<=>`인 오류다. |
| T-05 | R-07 | 같은 식을 strict 모드가 아닐 때 세 번, 같은 호출 위치에서 (원본 테스트) | 세 번 모두 `Money(20, USD)`. 불일치 보고는 한 건. |
| T-06 | R-06 | `Money(100, USD) == Money(100, EUR)`, `Money(0) == 0`, `Money(1) == 1` (원본 테스트) | false(오류 없음), true, `TypeError`. |
| T-07 | R-03 | `5 - Money(8, USD)`, `5 + Money(8, USD)` | `Money(3, USD)`, `Money(13, USD)`. 뺄셈의 피연산자 순서가 뒤집힌다(coerce 규약을 읽고 도출, 같은 값 비교만 원본 테스트에 있다). |
| T-08 | R-04 | `Money(1000) / Money(500)`, `1000 / Money(2)`, `Money(1000) * Money(2)` (원본 테스트) | decimal `2`, `TypeError`, `TypeError`. |
| T-09 | R-22, R-23 | `Money(1000, USD).exchange_to(JPY, custom_rate: 1.25)`; `custom_rate: 0`, `-1` (원본 테스트) | `Money(1250, JPY)`, 저장소 조회 없음. 0과 -1은 `ConversionError`. |
| T-10 | R-23 | 환율 행이 없고 provider가 없을 때 `Money(1000, USD).exchange_to(JPY, date: 2026-09-10)` (원본 테스트) | `ConversionError`, 메시지 `Couldn't find exchange rate from USD to JPY on 2026-09-10`. |
| T-11 | R-25 | 행 `USD→EUR`, 2025-03-10, rate 0.9 한 건뿐. `exchange_to(EUR, date: 2025-03-15)`와 `date: 2025-03-16`, provider 없음 | 03-15는 `03-10`이 구간 `[03-10, 03-15]`에 있으므로 amount × 0.9. 03-16은 구간 `[03-11, 03-16]`에 없고 provider도 없어 `ConversionError`. |
| T-12 | R-26 | 행 `EUR→USD` 2025-03-01 = 1.1, 2025-03-20 = 1.2. `rate_sql` 기준: 03-10, 02-01, 03-25, GBP→USD(행 없음), USD→USD | 03-10은 1.1(이전 최근, 나이 제한 없음). 02-01은 1.1(이전이 없어 이후 최초). 03-25는 1.2. GBP는 NULL. USD→USD는 1. |
| T-13 | R-27, R-28 | 목표 USD, 대상 `[EUR, JPY, KRW, USD]`. EUR은 오늘 행, JPY는 20일 전 행뿐, KRW는 행 전혀 없음, provider 없음 | 맵은 `{EUR: 오늘 환율, JPY: 20일 전 환율, USD: 1}`. KRW는 빠지고 경고 로그. `currencies_without_rate([EUR, JPY, KRW], USD)`는 `[KRW]`, `stale_rate_dates`는 `{JPY: 20일 전 날짜}`. |
| T-14 | R-41 | family 대표 통화 USD. 같은 종류(예: 입출금)의 자산 계정 두 개: USD 잔액 1000, EUR 잔액 500. 오늘 `EUR→USD` 행 1.1. 합계를 구한다 | `1000 + 500 × 1.1 = 1550`. 행이 모든 날짜에 없으면 EUR 계정은 0으로 계산해 합계 `1000`이고 그 계정 행에는 EUR 500이 보인다. |
| T-15 | R-32, R-33 | 저장: `USD→EUR` D-3 = 1.2, D-2 = 1.25. 호출: `start_date = D-3`, `end_date = 오늘`. provider는 D-1 = 1.3만 반환, 오늘은 활성 시간대의 오늘(`Date.current`)이라고 가정(R-31) (원본 테스트: 정방향 값) | provider 요청 시작일 D-6. 정방향 행 D-3 1.2, D-2 1.25, D-1 1.3, 오늘 1.3(이월). 역방향 `EUR→USD` 행: D-1, 오늘 = 0.769230769231, D-3 = 0.833333333333, D-2 = 0.8(백필). `exchange_rate_pairs.first_provider_rate_on`은 D-1. |
| T-16 | R-32 | provider 객체가 유효성 래퍼를 거치지 않고 0 이하이거나 nil인 행만 담은 성공 응답을 줌 (원본 테스트는 provider를 mock으로 대체해 래퍼를 거치지 않는다) | 시작 환율이 없어 `MissingStartRateError`를 기록하고 저장 행이 없다. 실제 provider(R-29의 래퍼가 무효 행을 먼저 버림)에서는 응답이 빈 것과 같아 "응답이 비어 있음" 경고로 끝나고 저장 행이 없다. |
| T-17 | R-33 | 정방향 환율 `3000000000000`(3×10^12)이 있는 날짜 | 역수가 약 `3.3e-13`이라 12자리로 반올림하면 0이므로 그 날짜의 역방향 행은 만들지 않는다. (`2e12`면 역수 `5e-13`이 half up으로 `1e-12`가 되어 행이 만들어진다. half-even이면 `5e-13`이 `0`이 되어 달라지므로 R-02의 모드 규칙을 따라야 한다.) |
| T-18 | R-31, R-32 | `clear_cache: false`, 구간 전체에 이미 정방향 행이 있다 (원본 테스트) | provider를 부르지 않고 역수 백필만 한다. |
| T-19 | R-14, R-11 | `Money(-0.004, USD).format`, `Money(-0.005, USD).format` | `$0.00`(부호 없음), `-$0.01`. |
| T-20 | R-12, R-14 | `Money(1000.12, EUR).format(locale: fr)`, `(locale: de)`, `(locale: nl)`; `Money(100.12, MXN).format(locale: es)` (원본 테스트) | `1 000,12 €`(`1`과 `000` 사이, `12`와 `€` 앞은 NBSP), `1.000,12 €`, `€ 1.000,12`, `100.12 MX$`. |
| T-21 | R-13 | `Money(1234567.89, INR).format`, 음수, `precision: 0`로 `Money(100000, INR)`, `Money(100000, USD).format(indian_grouping: true)` (원본 테스트) | `₹12,34,567.89`, `-₹12,34,567.89`, `₹1,00,000`, `$1,00,000.00`. |
| T-22 | R-18, R-19 | `parse_currency(" gbp ")`, `"XXX"`, `"invalid"`, nil. `alpha_currency_code(980)`, `(36)`, `(999)`; `minor_unit_divisor("KRW")`, `("BTC")`, `(nil)` | `GBP`, nil, nil, nil. `UAH`, `AUD`(`"036"`), nil. 1, 100000000, 100. |
| T-23 | R-20 | family 저장: `currency = "krw"`, `"ABC"`, 값 없음의 `primary_currency_code` | `KRW`로 저장. 검증 오류. `USD`. |
| T-24 | R-36, R-37 | 체크 계좌(자산) 잔액 1000, 하루에 거래 `-200`(유입)과 `+50`(유출). 카드 계좌(부채) 잔액 500(갚을 금액), 하루에 `-100`(납부)과 `+30`(결제) | 체크: `1000 - (-200 + 50) = 1150`. 카드: `500 + (-100 + 30) = 430`. |
| T-25 | R-39 | 부채 계좌에 평가 항목 `amount = 500`을 날짜 D에 둔다 | D의 총 잔액은 500(음수로 바뀌지 않음). 그 날 거래 부호 규칙은 적용되지 않는다. |
| T-26 | R-40 | USD 계좌에 EUR 거래(금액 -100, 날짜 D). D의 `EUR→USD`가 없고 provider도 없음 | 그 거래는 잔액 계산에서 빠지고(1:1 금지) 건수 1건과 쌍 `(EUR, USD)`가 보고된다. |
| T-27 | R-31, R-35 | 활성 시간대 KST, 현재 시각이 11월 25일 02:00 KST(뉴욕은 11월 24일 12:00). `import_provider_rates(from: KRW, to: USD, start_date: 11월 1일, end_date: 11월 25일)` | 원본 의도(뉴욕 오늘)면 `end_date`가 11월 24일로 줄어든다. 추론한 실제 동작은 상한이 `Date.current`인 11월 25일이라 줄지 않고 25일 행까지 만든다(provider에 그 날 값이 없으면 직전 값 이월). 두 결과가 달라 구현이 하나를 골라야 한다(적용 메모). |
| T-28 | R-06, R-07 | strict 모드가 아닐 때 `Money(100, USD) <=> Money(100, EUR)`를 같은 호출 위치에서 두 번, 그리고 `==` | 둘 다 1(amount가 같아 통화 코드 `USD`와 `EUR`를 비교한 결과, 0이 아님). 불일치 보고는 한 건. `==`는 false. |
| T-29 | R-18, R-20 | `Import::Row`의 currency가 `"ZZZ"`. `Account`의 currency를 `"ZZZ"`로 저장한 뒤 그 계정으로 `balance_money`. 이미 `"ZZZ"`가 저장된 family의 다른 속성만 고쳐 저장 | 앞은 검증 오류 `is not a valid currency code`. 둘째는 저장되고(비어 있는지만 검사) `balance_money`에서 `UnknownCurrencyError`. 셋째는 통과한다(`currency`가 바뀔 때만 검증). |
| T-30 | R-35 | USD 계정. 증권 S는 가격 통화 KRW, 저장된 KRW 가격의 최신일 2026-11-10, S의 첫 매매일 2026-01-05, provider 보유 아님 | `(KRW → USD)` 쌍이 2026-01-05부터 오늘까지 필요하다. S의 KRW 가격 최신일이 2026-01-02였다면(필요 시작일보다 이름) 쌍이 만들어지지 않는다. 저장된 가격이 없어도 만들어지지 않는다. |
| T-31 | R-02, R-08, R-11 | `Money(0.125, USD).for_display`, `Money(-0.125, USD).for_display`, `Money(2.5, JPY).format` | amount `0.13`, `-0.13`, 문자열 `¥3`(half up). half-even이면 `0.12`, `-0.12`, `¥2`라 원본과 다르다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

기준은 `repos/sure@1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a`다. 줄 범위는 이 SHA에서 직접 읽은 것이다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `lib/money.rb:37`, `:40-46`, `:73-80`, `:161-165`; `lib/money/currency.rb:13-23`, `:53-70` | 생성자와 검증을 읽었다. 문자열이 decimal로 읽힌 뒤 타입 검증에서 거부되는 순서, `nil`의 decimal 읽기 실패는 코드 순서로 도출했고 오류 클래스 이름은 프레임워크 의미를 읽은 추론이다. `Money.default_currency=`(`lib/money.rb:44`)를 부르는 곳은 `grep -rn "default_currency =" app lib config --include=*.rb`가 결과 없음이었고, `grep -rn "Money.default_currency" app lib config --include=*.rb`는 `lib/money.rb`의 기본 인자(`:73`)뿐이었다(`Import`의 `default_currency` 메서드들은 다른 이름이다). 테스트(`test/`)와 `.erb`는 이 검색에 넣지 않았다. |
| R-02 | `lib/money.rb:73-80`, `:112-114`; `lib/money/arithmetic.rb:4-31`; `db/schema.rb:711` | 연산자가 `Money.new`로 새 객체를 만들고 `round`를 부르지 않는 것을 확인했다. 소수 5자리 입력을 맞추는 곳(ActiveRecord decimal 타입의 scale 적용이 먼저일 가능성이 높고 DB도 half up)은 레포 밖 의미라 추론이다. 반올림 모드: `lib/money/formatting.rb:85`, `:93`이 `round_mode`를 읽어 `round`에 넘기고, `grep -rhn "round_mode" config/locales`는 45건 모두 `default`였다. `default`와 decimal 기본 모드가 half up이라는 것은 레포 밖 의미(추론)다. |
| R-03 | C-06 `lib/money/arithmetic.rb:4-22`, `:64-68`; 원본 테스트 `test/lib/money_test.rb:43-48`, `:112-116` | `5 - money`가 `money - 5`가 되는 것은 `coerce`가 `[self, CoercedNumeric(5)]`를 돌려주고 언어가 `a - b`를 계산한다는 규약을 읽은 추론이다. 원본 테스트 "operator order does not matter"는 `Money(1000) - 1000`과 `1000 - Money(1000)`이 같다고만 확인하므로 두 식이 같은 값(0)이어서 뒤집힘을 가리지 못한다. |
| R-04 | `lib/money/arithmetic.rb:28-42`; `test/lib/money_test.rb:50-59` | 코드 확인, 테스트가 TypeError 두 경우를 확인한다. `Money / 0`의 결과는 코드에 처리가 없어 U-02로 올렸다. |
| R-05 | `lib/money/arithmetic.rb:24-26`, `:44-62` | 코드 확인. |
| R-06 | `lib/money.rb:120-143`; `test/lib/money_test.rb:21-30`, `:74-77` | `Money(1) == 1`이 `TypeError`인 것은 원본 테스트가 확인한다. `eql?`·`hash` 미정의는 `grep -n "def eql?\|def hash" lib/money.rb lib/money/*.rb`가 결과 없음(범위: `lib/money.rb`, `lib/money/*.rb`). `Comparable`은 `Money`에 포함돼 있고 `eql?`을 정의하지 않는다. amount가 같고 통화가 다를 때 `<=>`가 통화 코드 비교 결과를 돌려주는 것은 `lib/money.rb:134-141`이고, 정수 0 판정 `other.eql?(0)`은 `:129`다. decimal의 `eql?`이 `==`와 같다는 것은 레포 밖 의미(추론)다. |
| R-07 | C-07 `lib/money.rb:21-31`, `:33-71`, `:146-159`; `config/initializers/money.rb:4-6`; `test/lib/money_test.rb:61-110`; `test/integration/mixed_currency_test.rb:111-115` | strict 플래그를 쓰는 곳은 `grep -rn "strict_currency" app lib config --include=*.rb`로 `lib/money.rb`와 이니셜라이저뿐이다(`balance/chart_series_builder.rb`, `goal.rb`의 `strict_currency_conversion`은 다른 개념, R-41). `Rails.env.local?`은 development와 test에서 참이라는 프레임워크 의미다. 연산 이름이 파생 비교에서도 `<=>`인 것은 `lib/money.rb:134`(`ensure_same_currency!(other, :<=>)`)이고 호출 위치는 `:154`다. 파생 비교의 호출 위치가 쓴 줄이 되는 것은 언어의 호출 스택 의미를 읽은 추론이다. |
| R-08 | `lib/money.rb:112-118`; `test/lib/money_test.rb:144-147` | `as_json`의 amount 직렬화 형태는 프레임워크 의미를 읽은 추론이라 U-03으로 올렸다. 호출처: `grep -rnE "_money\b.*(as_json|to_json)|money\.as_json" app lib --include=*.rb --include=*.jbuilder --include=*.erb`에서 `app/controllers/api/v1/balance_sheet_controller.rb:16-18` 세 곳을 찾았다(범위 한정). |
| R-09 | C-01, `lib/money/currency.rb:1-80`; `test/lib/money/currency_test.rb:17-33` | 항목 수 182와 키=소문자 코드는 `config/currencies.yml`을 파싱해 센 값이다(`python`으로 정규식 추출). `popular`·`as_options`는 코드로 확인했고 호출처는 읽지 않았다. |
| R-10 | C-01; `test/lib/money/currency_test.rb:35-55` | 자릿수별 개수는 파일에서 `default_precision` 값을 센 값이다. `minor_unit_conversion`과 자릿수가 다른 항목(`ETH`, `MGA`, `MRU`)은 같은 파일 비교로 찾았다. "KRW도 소수 4자리까지 저장"은 `entries.amount`가 numeric(19, 4)이고 반올림이 표시 경로에만 있다는 두 사실의 조합(추론). |
| R-11 | C-03, C-04 `lib/money/formatting.rb:21-99`; `test/lib/money_test.rb:138-142`; 통화 표의 `default_format` 개수는 C-01을 센 값 | `fast_format`을 손으로 따라가 `₩1,234,567`을 도출했다(실행하지 않음). `%u%n` 88개, `%n %u` 93개, `%u %n` 1개는 파일에서 센 값이다. |
| R-12 | C-02 `lib/money/formatting.rb:6-16`, `:121-155`; `test/lib/money_test.rb:149-217`, `:285-292` | 로케일 이름은 활성 로케일의 정확한 심볼 일치만 본다(`de-DE` 같은 지역 변형은 목록에 없으면 적용되지 않는다). `EUR`의 통화 표 값이 `separator ","`, `delimiter "."`인 점(`config/currencies.yml:15-28`)과 로케일 예외(`en`, `en-IE`) 조합으로 "`en`에서만 EUR이 `,`·`.`"를 도출했다. |
| R-13 | C-02, C-03, C-05 `lib/money/formatting.rb:46-67`, `:101-119`; `test/lib/money_test.rb:219-283` | 코드와 테스트 확인. 인도식 묶음은 `delimiter_pattern`을 넘기므로 R-16의 프레임워크 경로를 탄다. 패턴 결과는 원본 테스트의 기대값으로 맞춰 봤다. |
| R-14 | C-04, C-05 `lib/money/formatting.rb:87-91`, `:113-119`; `test/lib/money_test.rb:208-217` | 음수 부호 판정식은 `fast_format` 87~91줄. `$` 기호 통화 29개는 `config/currencies.yml`에서 `symbol: "$"`인 항목을 센 값(USD 포함 30개)이다. 프레임워크 `number_to_currency`가 같은 판정을 쓰는지는 코드의 주석("parity")에 기대고 레포 밖 소스는 열지 않았다. |
| R-15 | `app/helpers/application_helper.rb:203-207`; 검색: `grep -rn "\.format(.*locale\|indian_grouping" app lib --include=*.rb --include=*.erb`가 `lib/money/formatting.rb` 밖에서 결과 없음 | 전칭 주장은 "앱 코드가 `locale:`, `indian_grouping:` 옵션을 넘기지 않는다" 하나다. 위 검색을 `app`, `lib`의 `.rb`, `.erb`에서 돌렸고 `lib/money/formatting.rb` 밖에서 결과가 없었다. 옵션 변수를 거친 호출(`format(options)`)과 다른 확장자의 템플릿은 놓칠 수 있다. `precision`을 쓰는 호출은 `grep -rnE "(money|_money)\.format\(" app`의 출력 일부(`format(precision: 0)`)로 표본 확인했다. |
| R-16 | `lib/money/formatting.rb:73-99`, `:21-43`; `config/locales/defaults/hu.yml:139-151`, `pl.yml:203-214`, `en.yml:177-187`, `ko.yml:125-140` | `fast_format`이 `significant`·`strip_insignificant_zeros`·`delimiter_pattern`을 보고 물러서는 것을 확인했다. `hu`의 `1 000 $` 예는 원본 테스트(`test/lib/money_test.rb:253-260`)의 explicit locale 사례에서 가져온 것이고 활성 로케일 `hu`의 실제 출력은 도출하지 못해 U-01로 뒀다. `ko`·`en`의 설정이 꺼져 있는 것은 yml에서 읽었다. |
| R-17 | `app/models/concerns/monetizable.rb:1-22`; `app/models/entry.rb:16`; `app/models/account.rb:41`; `grep -rn "monetize\|monetizable_currency" app --include=*.rb` | `allow_nil:`·`as:`가 무동작이라는 판단: `monetize(*fields)`가 키워드 인자를 받지 않으므로 해시가 마지막 `field`로 들어가 의미 없는 메서드 이름이 만들어진다(언어 의미를 읽은 추론). `blank?`가 decimal 0에 거짓인 것도 같은 종류의 추론이다. |
| R-18 | `app/models/family.rb:174`, `:946-948`; `app/models/import/row.rb:5-9`, `:153-161`; `app/models/account_statement.rb:60`, `:439-445`; `app/models/entry.rb:62`; `app/models/account.rb:11`; `app/models/concerns/currency_normalizable.rb:30-66`; `app/models/security/manual_price_import.rb:78`; `app/models/assistant/function/create_transaction.rb:312-319`; `app/models/recurring_transaction/declared_bill.rb:160-168`; `app/models/rule/action_executor/split_transaction.rb:196-203`; 검색: `grep -rn "UnknownCurrencyError" app lib --include=*.rb`(18건), `grep -rn "validates.*:currency" app/models`, `grep -rnE "validate.*currenc" app/models` | 위 검색 결과 중 `Import::Row`, `AccountStatement`, `Family`, 어시스턴트 도구, `DeclaredBill`, `SplitTransaction`, `ManualPriceImport`를 열어 위 문장을 썼다. 나머지 `UnknownCurrencyError` rescue(`brex_account`, `financekit/*`, `wise_item/balance_replay`, `account_statement/text_metadata_parser`, `currency_normalizable`, `iso_numeric_currency`)는 provider·명세서 쪽이라 열지 않았다. "이 목록 밖에는 검증이 없다"는 `app`, `lib`의 `.rb` 검색에 한정하고 `.erb`·JS(`app/javascript`)·컨트롤러의 파라미터 검증은 보지 않았다. 앞서 쓴 "Family만 검증"은 틀렸다(검토에서 `Import::Row` 등이 확인됨). |
| R-19 | C-12 `app/models/concerns/iso_numeric_currency.rb:14-49`; `config/currencies.yml`(`iso_numeric` 중복·빈 값은 파일에서 확인: 숫자 코드가 빈 항목 11개, 중복 없음); 사용처 `app/models/monobank_account.rb:84`, `app/models/monobank_entry/processor.rb:244` | 사용처는 `grep -rn "alpha_currency_code\|IsoNumericCurrency" app`로 확인했고 둘 다 Monobank이다(provider 구현은 이 스펙 밖). |
| R-20 | `app/models/family.rb:174`(`if: :currency_changed?`), `:176-182`, `:197-202`, `:224-232`, `:934-951`; `db/schema.rb:865` | 코드 확인. 기본값 `USD`는 schema의 `families.currency`. |
| R-21 | C-08 `lib/money.rb:91-109`; `test/lib/money_test.rb:309-352` | 코드 확인. |
| R-22 | C-08 `lib/money.rb:91-109`; `app/models/transaction.rb:33-66`; `app/models/trade.rb:37-60`; `test/lib/money_test.rb:342-357` | `Trade`의 검증은 `Transaction`과 같은 모양임을 `trade.rb:37-56`에서 확인했으나 검증 메시지 세부는 `Transaction`만 읽었다. |
| R-23 | `lib/money.rb:5-15`, `:105`; `test/lib/money_test.rb:315-340` | 코드·원본 테스트 확인. |
| R-24 | `app/models/exchange_rate.rb:10-31`; `db/schema.rb:837-849`; 검색: `grep -rn "ExchangeRate\.\(create\|upsert\|insert\|find_or_create\|new\)\|ExchangeRate.delete\|ExchangeRate.destroy" app lib db/seeds.rb`, 추가로 `grep -rn "ExchangeRate\.where.*delete_all" app lib`, `grep -rn "ExchangeRatePair" app lib --include=*.rb` | 쓰는 곳은 `provided.rb:51`(`find_or_create_by!`), `provided.rb:77`(`update!`), `importer.rb:126`(`upsert_all`, 호출은 `:79`, `:97`, `:252`)다. 지우는 곳은 `app/jobs/data_cache_clear_job.rb:6`(`ExchangeRate.delete_all`, 쌍 테이블은 지우지 않는다), `app/jobs/market_data_reset_job.rb:126`(구간 삭제), `app/models/demo/data_cleaner.rb:42`다. 마이그레이션·rake 작업은 검색 범위 밖이다. |
| R-25 | `app/models/exchange_rate/provided.rb:12`, `:26-83`, `:242-244`; `app/models/provider/exchange_rate_concept.rb:6-31` | 코드 확인. `date`를 지정하지 않으면 "오늘"이다. "공급자가 가장 가까운 거래일을 줄 수 있다"는 `provided.rb:30-34`의 주석(Yahoo Finance 예)이라 외부 동작은 `미확인`이다(1.4 확인 한계). 이 경로가 반환하는 값이 저장한 행이 아니라 provider의 Rate라는 점은 `provided.rb:82` `rate`. |
| R-26 | C-09 `provided.rb:19-21`, `:160-171`, `:248-259`; 사용처 `app/models/property.rb:186`, `app/controllers/reports_controller.rb:386-395` | `find_stored_rate`는 `any_stored_rates([from], to:, date:)`의 한 통화 결과다. 같은 통화를 특별히 처리하지 않는 것은 코드에서 그런 분기가 없음을 읽은 것이다(호출자 `property.rb:187`이 먼저 같은 통화를 걸러 낸다). |
| R-27 | `provided.rb:96-150`; `test/models/exchange_rate_test.rb` 사례명(88-120, 201-222) | 단계 (3)에서 "그 날짜의 행이 저장돼 있어야 인정"은 `provided.rb:128-134`. 사례명은 열어 확인하지 않았고 이 규칙 문장과 이름이 맞는지만 봤다. |
| R-28 | `provided.rb:176-197`; `app/models/exchange_rate.rb:8`; `app/models/family.rb:638-675`; `grep -rn "CONVERSION_CACHE_VERSION" app lib --include=*.rb`로 캐시 키 사용처 확인(`account/chartable.rb:3`, `balance_sheet/net_worth*_builder.rb`, `income_statement.rb`, `investment_statement.rb`, `transaction/search.rb`) | "모든 캐시 키"는 위 검색의 출력에 한정한 서술이다. 같은 값을 쓰지 않는 환산 캐시가 있을 수 있다. |
| R-29 | `provided.rb:5-9`; `app/models/provider/registry.rb:52-58`, `:222-228`, `:233-236`; `app/models/setting.rb:101`; `app/models/provider/exchange_rate_concept.rb:6-62`; `app/models/provider.rb:2` | `Provider::Response = Data.define(:success?, :data, :error)`. `get_provider`가 등록되지 않은 이름에서 오류를 던지는 것은 `registry.rb:222-228`. provider 클래스 본문(`frankfurter.rb`의 `fetch_exchange_rates`, `max_history_days`)은 인터페이스 형태 확인용으로 일부만 봤다. |
| R-30 | `provided.rb:200-237` | 코드 확인. 반환 타입 주석(`@return [Integer]`)과 달리 실제 반환은 Importer의 마지막 식 값이고, 호출처(`account/market_data_importer.rb:53`, `market_data_importer.rb:57`)는 반환값을 쓰지 않는다. |
| R-31 | `importer.rb:5-14`, `:16-22`, `:173-210`, `:263-275`, `:284-289`; `app/models/market_data_importer.rb:162-165` | 코드 확인. 끝 날짜 상한: 두 파일이 `Date.current.in_time_zone("America/New_York").to_date`를 쓴다. `Date#in_time_zone(zone)`이 그 날짜의 zone 자정 시각을 만들고 `.to_date`가 같은 날짜로 돌아온다는 것은 ActiveSupport 의미(레포 밖)에 기댄 추론이며 실행으로 확인하지 못했다. 코드 주석과 이름(`today_est`)은 뉴욕 오늘을 의도한다. 삭제 뒤 `first_provider_rate_on`이 남는 것은 `data_cache_clear_job.rb:6-10`이 쌍을 지우지 않는 것과 `importer.rb:173-178`을 합쳐 도출했다. 원본 테스트 `importer_test.rb`의 `"clamps end_date..."`, `"skips provider call when all rates exist..."`, `"clamps provider fetch to max_history_days..."` 사례명으로 규칙 문장과의 대응만 봤다. |
| R-32 | C-10 `importer.rb:23-77`, `:138-171`, `:212-231`; 테스트 `importer_test.rb:11-67`, `:172-204`, `:233-255`, `:300-332` | 테스트 네 개를 열어 손으로 따라간 결과(T-15의 정방향)와 맞는지 확인했다. "저장 행이 provider 값에 덮인다"는 `importer_test.rb:172-204`. |
| R-33 | C-11 `importer.rb:79-101`, `:233-261`; 테스트 사례명 `importer_test.rb:144`, `:205`, `:256` | T-15의 역수 행 값(0.769230769231 등)과 백필 동작은 코드를 따라가 도출했고 테스트 본문은 열지 않았다. 백필 범위 불일치는 `importer.rb:234`(`existing_inverse_dates`는 `clamped_start..end_date`)와 `:237`(`db_rates`는 `start_date..end_date`, `:277-282`)를 비교해 도출했다. `BigDecimal#round(12)`가 half up이라는 것은 레포 밖 의미(추론)다. |
| R-34 | `app/models/exchange_rate_pair.rb:1-41`; `importer.rb:103-108`, `:173-182`; `app/components/UI/account_page.rb:80-92` | 코드 확인. 테스트 사례명 `exchange_rate_pair_test.rb`는 열지 않았다. |
| R-35 | `app/models/account/market_data_importer.rb:11-70`, `:74-121`; `app/models/security/price/import_windows.rb:1-100`; `app/models/market_data_importer.rb:40-65`, `:97-150`, `:162-165`; `app/models/account.rb:855-858` | 두 importer의 쌍 수집과 증권 가격 통화의 시작일 규칙(`import_windows.rb`의 `start_date` 계산 `:79-86`)을 읽었다. 증권 종료일 규칙(`end_date`)과 `current_holdings` 정의는 열지 않았다. 필요 시작일 W의 "provider 보유" 조건은 `import_windows.rb:85`. 두 경로의 `clear_cache` 전달 차이는 `market_data_importer.rb:57-63`과 `account/market_data_importer.rb:53-58`의 호출 인자를 비교했다. 끝 날짜의 시간대는 R-31의 추론에 의존한다. |
| R-36 | `app/models/entry.rb:200-204`, `:359-361`; `docs/llm-guides/architecture.md:66-80`; C-13 | 문서와 구현이 일치한다. 가져오기(import) 단계에서 외부 부호를 이 부호로 바꾸는 규칙은 범위 밖이다. |
| R-37 | C-13, C-14; `db/schema.rb:105`(`accounts.classification` 가상 열), `app/models/account.rb:81`, `app/models/concerns/accountable.rb:21-22` | 부채 계정 목록은 schema의 가상 열 정의(`Loan`, `CreditCard`, `OtherLiability`)다. 대출 원금 분기는 `base_calculator.rb:137-143`과 `forward_calculator.rb:154-156`의 조건만 읽었고 `loan_principal_change`의 계산은 열지 않았다. |
| R-38 | C-13 `base_calculator.rb:125-153`; `docs/llm-guides/architecture.md:74-79` | 코드 확인. `Trade`의 `amount` 생성 규칙(수량·가격·수수료로 어떻게 만드는지)은 열지 않았다. |
| R-39 | `docs/llm-guides/architecture.md:57-63`, `:75-79`; `balance/forward_calculator.rb:22-32`; `balance/reverse_calculator.rb:41-44`; `entry.rb:62-63` | "평가 금액 부호 검증 없음"은 `app/models/valuation.rb` 전체(검증 선언 없음, `grep -n "valid\|amount" app/models/valuation.rb`에서 `enum ... validate: true`뿐)와 `entry.rb:62`의 `validates :date, :name, :amount, :currency, presence: true`(존재만 검사)를 읽은 결과다. DB CHECK도 `entries`에서 보이지 않는다(`db/schema.rb:709-751`). 컨트롤러·폼 객체의 입력 검증은 검색하지 않았다. |
| R-40 | `app/models/balance/sync_cache.rb:40-42`(`get_entries`), `:60-125`, `:143-146`(`entries_scope`) | 코드 확인. 주석(#1143)이 정책 이유를 직접 적는다. 이유 문장은 코드 주석이라 개발자 의도로는 `추론`이다. |
| R-41 | `app/models/balance_sheet/account_totals.rb:94-112`; `app/models/concerns/accountable.rb:92-107`; `app/models/income_statement/scoped_transactions_query.rb:18-35`; `app/models/transaction/search.rb:236-250`; `app/models/balance/chart_series_builder.rb:66-84`, `:150-160`, `:205-235`; `app/models/goal.rb:1512` | 세 경로를 대표로 읽었다. `investment_statement.rb`, `reports_controller.rb`의 환산은 같은 `rate_sql`, `rates_for`를 쓰는 것을 줄 번호로만 확인했고 본문은 읽지 않았다. 이 때문에 "모든 경로에서 1로 계산하지 않는다"는 읽은 경로 한정이다. |
| R-42 | `balance/sync_cache.rb:63-125`; `app/models/account.rb:668-678`, `:983-1003`; `app/models/trade.rb:244-285`; `app/models/holding.rb:150-175`, `:396-402`; `app/models/holding/portfolio_cache.rb:38-55`; `app/models/holding/trade_calculator_helpers.rb:52-63`; `grep -rn "Money::ConversionError" app lib --include=*.rb`(약 30곳) | 위 일부만 읽었다. "1:1을 쓰는 곳은 보유 환산과 증권 가격 캐시"는 읽은 호출처 안에서의 서술이다. 나머지 호출처는 열지 않았다. |
| R-43 | `lib/money/currency.rb:25-47`, `:72-74`; `app/controllers/currencies_controller.rb:1-6`; 사용처 `app/models/concerns/iso_numeric_currency.rb:15`, `app/models/recurring_transaction.rb:127`, `app/models/security/manual_price_import.rb:78` | `grep -rn "Money::Currency.all\b" app lib --include=*.rb`(`all_instances` 제외)의 세 곳이다. `as_json`이 모든 속성을 맵으로 만든다는 것은 `lib/money/currency.rb`에 `as_json` 정의가 없다는 코드 사실과 프레임워크 기본 직렬화 의미(추론)에 기댄다. |
| T-01~T-10 | 원본 테스트 `test/lib/money_test.rb:5-110`, `:138-147`, `:309-360` 또는 구현에서 도출 | T-03, T-07은 코드만으로 도출. T-11은 `provided.rb:26-45`를 따라가 도출. |
| T-12~T-13 | `provided.rb:19-21`, `:96-150`, `:160-197` | 구현에서 도출. 원본 테스트 사례명(`exchange_rate_test.rb:104-146`)과 같은 규칙을 다룬다. |
| T-14, T-24~T-26 | `balance_sheet/account_totals.rb:94-112`, `balance/forward_calculator.rb:153-160`, `balance/sync_cache.rb:94-125` | 구현에서 도출. 실행하지 않았다. |
| T-15~T-18 | `importer.rb`; 원본 테스트 `importer_test.rb:11-67`, `:172-204`, `:300-332` 열람 | T-15의 정방향 값은 테스트의 `[1.2, 1.25, 1.3, 1.3]`과 같은 구성을 따랐고 역방향 값은 계산으로 도출했다. T-16~T-18은 사례명 열람. |
| T-27~T-31 | 구현에서 도출 | T-27은 R-31의 추론에, T-31·T-17은 half up 가정에 의존한다. 실행하지 않았다. |
| T-19~T-23 | `formatting.rb`, `currency_normalizable.rb`, `iso_numeric_currency.rb`, `family.rb`를 손으로 따라 도출. T-20, T-21은 원본 테스트 `money_test.rb:149-217`, `:219-250` | T-19는 코드 도출뿐이고 원본 테스트에 없다. |

### 2.2 코드 읽는 순서 [선택]

1. `lib/money.rb`와 `lib/money/arithmetic.rb`(값 객체와 통화 불일치 검사). 2. `lib/money/currency.rb`와 `config/currencies.yml`의 `usd`, `krw`, `jpy` 항목(통화 표). 3. `lib/money/formatting.rb`(표시). 4. `app/models/exchange_rate.rb`와 `exchange_rate/provided.rb`(제약과 세 가지 조회 규칙). 5. `exchange_rate/importer.rb`와 `exchange_rate_pair.rb`(적재). 6. `balance/base_calculator.rb`의 `flows_for_date`와 `sync_cache.rb`(부호와 환산이 만나는 곳). 7. `balance_sheet/account_totals.rb`, `income_statement/scoped_transactions_query.rb`(대표 통화 합계).

원본의 구현 전략은 세 가지다. 하나, 환율 조회 규칙이 세 개다. 단건(`find_or_fetch_rate`: 5일 + provider), 배치(`rates_for`: 5일 + provider + 나이 제한 없는 저장 환율), SQL(`rate_sql`: 나이 제한 없는 저장 환율만). 둘, 적재(Importer)가 모든 달력 날짜에 행을 채워 두므로 SQL 경로는 보통 같은 날짜의 행을 찾는다. 셋, 합계 캐시 키에 `CONVERSION_CACHE_VERSION`을 넣어 규칙 변경 때 한 번에 무효화한다.

### 2.3 비교·재사용 출처 [선택]

다른 레포의 같은 기능 스펙은 없다. 원본은 AGPL-3.0이다(overview 1절). 이 스펙은 코드를 복사하지 않았다. `config/currencies.yml`은 데이터 파일이라 재사용을 고려할 때 라이선스를 따로 확인한다(통화 코드·소수 자릿수 같은 ISO 4217 사실 자체와 파일 표현은 구분해서 판단해야 한다).

### 2.4 검토 기록 [필수, ready 스펙]

`draft`다(미결정 U-01~U-03이 남아 있어 `ready` 조건을 충족하지 못한다). 2026-11-17에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-42 전부를 코드와 한 번씩 대조했다. 문제 없이 일치 24개, 경미한 보정이 필요한 14개, 불일치 3개(R-18, R-31, R-35)가 나왔다. C-ID 전부(C-01~C-14)의 줄 범위와, T-ID 중 T-01, T-02, T-04~T-17, T-19~T-26을 손으로 다시 계산했다. 작성자가 지적 전부를 코드로 다시 확인해 반영했다(틀린 지적은 `format_money` 줄 범위 1건과 R-14 판정식 줄 범위 1건).
- **메인 표본 점검**: R-03(`5 - Money`가 `Money - 5`로 계산됨, `lib/money/arithmetic.rb`의 `coerce`), R-18(`Import::Row`의 통화 검증, `import/row.rb:9, 153-161`), R-31(`Date.current.in_time_zone("America/New_York").to_date`가 같은 날짜를 돌려줌), R-07(`<=>`가 amount가 같고 통화가 다르면 통화 코드 비교, `lib/money.rb:126-141`)을 원본 줄과 직접 맞췄다.
- **대조하지 못한 것**: R-16(`number_to_currency` 출력 규칙, 프레임워크 코드), R-02·R-06·R-08·R-31의 일부(ActiveRecord 반올림, `BigDecimal#eql?`, `as_json` 형식, `Date#in_time_zone`은 레포 밖 의미라 `추론`), R-41의 `investment_statement.rb`·`reports_controller.rb` 환산 본문, R-42의 `ConversionError` 호출처 약 30곳 중 약 20곳, 외부 provider의 실제 응답 날짜. 테스트 중 `money_test.rb`, `currency_test.rb`, `importer_test.rb` 일부, `mixed_currency_test.rb` 일부만 열었다.

## 적용 메모

원본 동작과 구분해 읽는다. 아래는 다른 언어로 다시 구현할 때 주의할 점과 우리가 다르게 하고 싶은 후보다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-02, R-04, R-21, R-33 | 금액·환율을 부동소수점으로 두지 않는다. 임의 정밀도 decimal 타입(예: Python `decimal`, Java `BigDecimal`)을 쓴다. 정밀도 상한이 있는 타입(예: 28자리)은 환산 결과와 역수 계산에 맞는지 먼저 확인한다. 환율은 provider 응답을 부동소수점이 아니라 문자열로 받아 decimal로 읽는다. | 원본 `Money`는 임의 정밀도 decimal이고 환산 결과를 반올림하지 않는다(R-02). 역수는 소수 12자리로 반올림한다(R-33). 부동소수점이면 `0.1 + 0.2` 같은 오차가 잔액에 쌓인다. 원본이 부동소수점 `1000.899`를 문자열 표현으로 읽는 것(R-01)은 입력 쪽의 우연한 정확성이고, 구현에서는 입력을 처음부터 decimal 문자열로 받는 편이 안전하다(추론). | 생성자 입력 타입이 숫자 대신 decimal 또는 문자열이 된다. T-01의 입력도 문자열 `"1000.899"`로 쓴다. |
| R-02, R-10 | "통화별 최소 단위 정수"(원, 센트)로 저장하는 방식은 원본 동작이 아니다. 원본은 decimal 주 단위(소수 4자리)로 저장한다. 정수 최소 단위로 바꾸려면 환산 결과를 정수로 만드는 반올림 지점이 새로 생긴다. `ETH`의 `minor_unit_conversion`(10^18)은 64비트 정수를 넘는다. 원본 호환이 목적이면 `numeric(19, 4)`를 그대로 쓴다. | KRW·JPY의 표시 자릿수는 0이지만 저장·연산은 소수 4자리까지 허용된다(R-10). 환산(예: `1000 USD × 1380.4567 = 1,380,456.7 KRW`)을 정수로 줄이면 오차가 합계에 쌓인다. | 저장 형식을 바꾸면 R-02, R-40 합계, T-14가 달라지므로 별도 결정이 필요하다. |
| R-03 | `숫자 - Money`가 `Money - 숫자`로 뒤집히는 동작(T-07)은 재현하지 않는다. 좌항이 `Money`인 연산만 지원하고, 숫자가 좌항이면 오류로 한다. 합계는 `Money`의 `zero` 값에서 시작한다. | 원본의 `coerce` 구현은 덧셈과 곱셈에는 무해하지만 뺄셈 순서를 뒤집는다(코드 주석은 "순서가 상관없게" 하려는 의도). | T-07의 기대값을 오류로 바꾼다. |
| R-07 | 모든 환경에서 통화 불일치를 오류로 한다. 원본의 production 동작(오류 대신 "기존 결과"를 돌려주고 호출 위치당 한 번 보고)은 기존 화면이 깨지지 않게 하려고 둔 점진 도입 장치다. 새 구현에는 이전 결과가 없으므로 이 장치가 필요 없다. 점진 이관이 필요하면 report-only 플래그로 한정한다. | production에서 불일치를 숨기면 틀린 합계가 화면에 남는다(원본 주석이 같은 이유로 strict를 켠다). | R-07의 production 열이 사라지고 T-05는 쓰지 않는다. |
| R-21, R-25 | `exchange_to`를 순수 함수(`환율을 받아 곱하기`)와 환율 해석기(DB 조회, 5일 조회, provider 호출, 저장)로 나눈다. | 원본은 금액 객체의 메서드가 DB 조회와 외부 HTTP 호출, 행 저장까지 일으킨다(R-25). 렌더링 중 호출될 수 있어 테스트와 성능이 어렵다. | `Money.exchange_to(rate)`와 `RateResolver.resolve(from, to, date)`로 분리하면 R-21의 "store" 인자가 사라진다. |
| R-25~R-27 | 조회 규칙 셋(단건, 배치, SQL)을 하나의 해석기로 통일할 수 있는지 먼저 정한다. 원본은 같은 날짜라도 경로에 따라 5일 제한이 있거나 없어 환율이 달라질 수 있다. | 원본은 provider를 부르는 경로(5일 제한)와 부르지 않는 경로(나이 제한 없음)를 의도적으로 분리했다(R-26, R-27). 통일하면 오래된 환율을 오늘 값처럼 쓰는 위험(R-28의 "오래된 환율" 안내)을 어디서 보여 줄지도 정해야 한다. | 선택은 새 결정이고 원본의 미결정이 아니다. |
| R-40~R-42 | 환산 실패 처리를 한 정책으로 통일한다(권장: 실패는 항상 "없음"으로 전파하고 1:1 대체를 두지 않는다). 원본은 잔액 계산이 항목을 버리고(R-40), 보유 환산과 증권 가격 캐시는 1:1을 쓰고(R-40, R-42), 합계는 0 또는 NULL로 뺀다(R-41). | 원본 주석이 "없음과 패리티는 다른 사실"이라고 직접 적는다(`provided.rb:88-92`). 1:1 대체는 환율 간격만큼 틀린 값을 정상 값처럼 보이게 한다. | R-40의 보유 1:1 규칙, R-42의 증권 가격 캐시 규칙이 바뀐다. |
| R-41 | 환율이 없는 금액을 "합계에서 뺀다"면 화면에 뺐다는 사실을 함께 보여 주는 구조를 둔다(원본은 `currencies_without_exchange_rate`와 `stale_exchange_rate_dates`로 안내한다, R-28). | 조용히 빠지면 합계가 작아 보이는 것과 구별되지 않는다. | R-28의 진단 두 함수를 합계와 함께 반환하게 할 수 있다. |
| R-11, R-12, R-13 | 로케일 표는 실제로 지원할 로케일(예: `ko`, `en`)만 구현한다. `ko`는 별도 규칙이 없어 통화 표 값만 쓴다(`₩1,000`). 한국어 화면에서 `1,000원` 형태를 원하면 새 결정이다(원본 `config/locales/defaults/ko.yml`의 `number.currency.format`은 `%n%u`, 단위 `원`이지만 `Money#format`이 `unit`, `format`을 항상 넘겨 이 값을 덮어쓴다). | 원본 `format`은 통화의 기호·형식을 로케일보다 우선한다(R-11). 로케일 파일의 값이 쓰인다고 기대하면 결과가 다르다. | T-02의 `₩1,001` 기대값이 바뀐다. 인도식 묶음(R-13)은 INR을 지원할 때만 필요하다. |
| R-07, R-30 | 프로세스 전역 상태(통화 불일치 보고 집합, 적재 lock)는 다중 프로세스·다중 스레드에서 안전한 구조로 만든다. lock은 값에 소유자 토큰을 넣고 자기 토큰일 때만 지우는 방식(R-30)을 유지한다. | 원본은 프로세스마다 보고 집합이 따로라 여러 프로세스가 같은 불일치를 각각 한 번씩 보고한다(추론). lock이 5분 TTL이라 그보다 오래 걸리는 적재는 중복 실행될 수 있다. | 해당 없음. |
| R-31, R-35 | "오늘"과 적재 `end_date` 상한을 하나로 정한다. 선택지는 둘이다. (a) 원본 의도대로 뉴욕 오늘을 상한으로 한다. (b) 원본의 실제 동작(추론)대로 활성 시간대(예: KST)의 오늘을 상한으로 한다. 환율 행의 `date`는 시간대 없는 달력 날짜로 둔다. | 원본 코드 주석은 (a)를 의도하지만 동작은 (b)로 추론된다(R-31). 한국 사용자는 KST라 (a)에서는 한국 날짜 오전에 뉴욕 날짜가 어제여서 하루 어긋날 수 있고(T-27), (b)에서는 미국 기준 provider가 오늘 값을 아직 주지 않아 직전 값 이월로 채워질 수 있다(추론). | R-31의 상한 규칙과 T-27 기대값이 선택에 따라 달라진다. 결정은 사용자 몫이다. |
| R-02, R-08, R-11, R-33 | 반올림 모드를 half up으로 명시한다. 일부 언어의 decimal 기본은 half-even이다(예: Python `decimal`의 기본 컨텍스트). 표시 반올림, `for_display`, 역수 12자리 반올림 모두 해당한다. | 원본의 `round`는 half up(추론)이라 `0.125`를 `0.13`으로, 환율 역수 경계값 `5e-13`을 `1e-12`로 만든다(T-31, T-17). half-even이면 값이 달라지고 R-33의 건너뛰기 판정도 달라진다. | T-17, T-31이 모드에 의존한다. |
| R-16, U-01 | 이 사용자는 `ko`와 `en`만 쓰므로 U-01(`hu`, `pl` 등 숫자 설정이 켜진 로케일의 `format`)은 영향이 없다. 구현은 R-11의 단순 경로만 만들고 프레임워크 `number_to_currency` 경로(R-16)는 만들지 않는다. | `ko`와 `en`의 로케일 숫자 설정은 `significant`, `strip_insignificant_zeros`가 꺼져 있다(`config/locales/defaults/ko.yml`, `en.yml`). 다른 로케일을 지원하게 되면 U-01을 먼저 닫아야 한다. | 인도식 묶음(R-13)과 `locale:` 옵션(앱 코드에 호출 없음)도 만들지 않아도 된다. |
| R-18 | 통화 코드 검증을 통화 표 조회 한 곳으로 통일한다. 원본은 모델마다, 입력 경로마다 검증이 달라(R-18) 표에 없는 코드가 `Account`·`Entry`에 저장될 수 있다. | 저장된 뒤 `Money` 생성에서 터지는 것보다 입력에서 거르는 편이 안전하다(추론). | R-18의 (2)번 모델 목록이 (1)번으로 옮겨 간다. |
| 통화 표 (C-01) | 통화 표(182개)는 구현 언어의 자료 파일로 옮기되, 코드 계약은 키 조회(대소문자 무시)와 R-09~R-10의 규칙뿐이다. 필요한 통화만 두는 것도 선택지다. 목록을 줄이면 R-18의 "표에 없는 코드는 거부"가 더 많이 걸린다. | 파일 복사는 AGPL(2.3)과 얽힌다. | 해당 없음. |
