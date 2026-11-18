---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-17
updated: 2026-11-17
sources:
  - app/models/account/provider_import_adapter.rb
  - app/models/account/linkable.rb
  - app/models/account_provider.rb
  - app/models/entry.rb
  - app/models/entryable.rb
  - app/models/transaction.rb
  - app/models/trade.rb
  - app/models/holding.rb
  - app/models/holding/cost_basis_reconciler.rb
  - app/models/concerns/enrichable.rb
  - app/models/concerns/provider_disconnectable.rb
  - app/models/data_enrichment.rb
  - app/models/provider_merchant.rb
  - app/models/provider/base.rb
  - app/models/provider/factory.rb
  - app/models/provider/kraken_adapter.rb
  - app/models/transfer.rb
  - app/models/family.rb
  - app/models/goal_pledge/reconciler.rb
  - app/models/provenance/citation.rb
  - app/models/simplefin_entry/processor.rb
  - app/models/simplefin_account/transactions/processor.rb
  - app/models/plaid_entry/processor.rb
  - app/models/plaid_account/transactions/processor.rb
  - app/models/kraken_account.rb
  - app/models/kraken_account/processor.rb
  - app/models/kraken_account/holdings_processor.rb
  - app/models/enable_banking_account/transactions/processor.rb
  - app/models/lunchflow_entry/processor.rb
  - app/models/transaction_import.rb
  - app/models/trade_import.rb
  - app/models/concerns/sync_stats/collector.rb
  - app/controllers/accounts_controller.rb
  - app/controllers/transactions_controller.rb
  - app/controllers/kraken_items_controller.rb
  - db/schema.rb
  - docs/llm-guides/providers.md
  - docs/llm-guides/architecture.md
depends: []
status: draft
---

# Provider 어댑터 계약

> 외부 provider가 준 거래·보유종목·매매·잔액을 내부 `Entry`(Transaction·Trade)와 `Holding`으로 넣는 공통 경로(`Account::ProviderImportAdapter`)의 입력·중복 판정·보류 대조·사용자 수정 보호·연결(`AccountProvider`) 규칙을 정의한다.

이 문서에서 두 가지 "adapter"를 구분한다. **import adapter**는 `Account::ProviderImportAdapter`로, 계정 하나에 묶여 데이터를 내부 모델로 쓰는 객체다. **provider adapter**는 `Provider::Base`의 하위 클래스(예: `Provider::KrakenAdapter`)로, provider 계정 레코드에 이름·지원 계정 종류·UI 연결 정보를 붙이는 등록 항목이다. 둘은 서로 호출하지 않는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

거래 한 건을 넣는 `import_transaction`의 대표 흐름이다. 순서와 분기의 정확한 기준은 1.4와 C-01이다.

1. provider별 processor(예: SimpleFIN의 `SimplefinEntry::Processor`)가 외부 응답 한 건을 내부 필드(`external_id`, `source`, `amount`, `currency`, `date`, `name`, 선택 필드)로 변환한다. 이 변환은 이 스펙의 범위 밖이다. processor는 계정마다 import adapter를 하나 만들어 한 sync 동안 재사용한다(R-01).
2. `import_transaction`이 `(account, source, external_id)`로 기존 `Entry`를 찾는다. 있고 그 entry가 보호 상태(제외, 사용자 수정, import 잠금)면 거의 아무것도 바꾸지 않고 돌려준다(R-09~R-12).
3. 찾지 못하면 새 키다. 이 때 먼저 사용자가 미리 입력한 예정 거래나 external_id 없는 수동·CSV 거래를 같은 거래로 보고 claim(소유권 이전)한다(R-13~R-17).
4. 들어온 거래가 확정(booked) 거래이면, 같은 provider가 앞서 보낸 보류(pending) 거래를 찾아 claim한다. 1순위는 provider가 준 `pending_transaction_id`, 2순위는 금액 정확 일치다(R-18~R-23).
5. 금액·통화·날짜를 덮어쓰고(잠금 존중), 이름·카테고리·가맹점·메모는 잠금이 없을 때만 바꾸고, `extra`는 provider 네임스페이스 단위로 병합한다(R-31~R-37). 투자 계정이면 활동 라벨과 `kind`를 정한다(R-38~R-40).
6. 저장한 뒤 열린 목표 pledge와 대조하고(R-41), 새로 생긴 확정 거래이면 비슷한 보류 거래에 "중복 의심" 제안을 남긴다(R-25~R-28).
7. 저장된 `Entry`를 돌려준다. 보호 때문에 건너뛴 거래는 import adapter의 `skipped_entries`에 쌓이고, 호출자가 sync 통계로 올린다(R-05).

보유종목(`import_holding`), 매매(`import_trade`), 잔액(`update_balance`)은 각자 별도 메서드이고 규칙이 다르다(R-43~R-59). 계정과 provider 계정의 연결은 import 이전에 만들어 두며 `AccountProvider`가 맡는다(R-60~R-68).

### 1.2 범위·통합 지점

- 제공: import adapter의 공개 메서드 전부(1.3), 중복·보류 판정 규칙, `Transaction#extra` 병합 규칙, 사용자 수정 보호, `AccountProvider`와 `Account::Linkable`의 연결·해제 규칙, 출처 기록 방식, 데이터가 들어가는 테이블의 제약.
- 제외:
  - provider별 API 호출과 응답 변환(`*_item/importer`, `*_account/processor`). SimpleFIN·Plaid·Kraken processor는 호출 규약을 보려고만 읽었고 스펙화하지 않았다.
  - 잔액 계산과 balance 재구성(account-balances 스펙 소관). 이 스펙은 `update_balance`가 계정의 두 필드를 직접 쓴다는 것까지만 다룬다. Plaid처럼 `Valuation`(current anchor)으로 잔액을 넣는 경로는 어댑터 밖이다(U-01).
  - 금액 부호·통화 환산 규칙 일반([money-currency-rules](./money-currency-rules.md)). 여기서는 어댑터 입력의 부호 규약만 쓴다.
  - sync 상태 기계와 job 실행([sync-pipeline](./sync-pipeline.md)). 어댑터는 sync를 예약하지 않는다(R-03).
  - 이체 매칭(`Transfer`), 목표 pledge(`GoalPledge`), 분류 규칙, 거래 분할·수동 병합 UI. 어댑터가 이들을 부르는 지점과 입력·결과만 쓴다.
  - `Security` 해석(티커→종목 레코드). `import_holding`·`import_trade`는 이미 해석된 `Security`를 받는다. 어댑터가 읽는 속성은 `id`와 `ticker` 둘뿐이다.
  - CSV·QIF·PDF 파일 import(`Import`). 이 경로는 어댑터의 `find_duplicate_transaction`만 빌려 쓰고, 만든 entry에 `import_locked`를 붙인다(R-12, T-07).
  - provider 연결의 인증·credential(`*_item`), 소유자·권한(`ProviderItemOwnable`).
- 외부 의존·선행 계약: 호출자가 `Account`(대상 계정)와 해석된 `Security`·`Merchant` 레코드를 준비한다. DB는 PostgreSQL 기능(jsonb, partial unique index)을 전제로 한다. 선행 스펙은 없다. 금액 부호는 money-currency-rules, 호출 시점은 sync-pipeline과 경계만 공유한다.
- 소유 상태·부작용: 어댑터는 `entries`(+ `transactions`/`trades`), `holdings`, `data_enrichments`, `merchants`(provider 가맹점), `accounts.balance`/`cash_balance`와 accountable의 일부 속성을 쓴다. 직접 쓰는 것 말고 저장 callback과 호출한 메서드가 만드는 부작용이 더 있다(R-40, R-42, R-57).
  - `Entry`·`Transaction` 저장 callback: 카테고리가 바뀌면 AI·Bayes 분류 기록을 "대체됨"으로 표시한다(정의는 transaction-classification 스펙 소관).
  - `Transaction.merchant_id`가 바뀌고 새 가맹점이 provider 가맹점이면 `FamilyMerchantAssociation`의 `(family, merchant)` 행을 지운다(R-42).
  - provider 가맹점을 저장할 때 웹사이트는 있고 로고가 없으면 로고 URL을 생성한다(R-57).
  - 투자 계정에서 라벨이 `Contribution`이면 가족의 "Investment Contributions" 카테고리를 찾거나 만들고, 이름이 다른 중복 카테고리를 합치고 지운다(R-40).

### 1.3 인터페이스와 데이터 의미

**용어(코드를 모르는 구현자용)**

| 용어 | 의미 |
|---|---|
| `Entry` | 계정에 속한 한 줄의 원장 기록. 공통 필드(`account_id`, `date`, `name`, `amount`, `currency`, `notes`, `external_id`, `source`, 보호 플래그)를 갖고, 종류별 세부는 `entryable`이 가리키는 `Transaction`·`Trade`·`Valuation` 중 하나가 갖는다. `entryable_type`과 `entryable_id`가 그 연결이다. |
| `Transaction` | 입출금 한 건의 세부. `category_id`, `merchant_id`, `kind`, `investment_activity_label`, `extra`(jsonb), `locked_attributes`. |
| `Trade` | 종목 매매 한 건의 세부. `security_id`, `qty`(부호 있음), `price`, `fee`, `currency`, `investment_activity_label`, `extra`. |
| `Holding` | 특정 날짜의 보유 수량과 평가액 스냅샷(계정·종목·날짜·통화마다 한 행). `Entry`가 아니다. |
| `source` | 이 entry를 만든 provider를 가리키는 문자열(예: `"simplefin"`). `entries.source`는 자유 문자열이다(R-69). |
| `external_id` | provider가 그 거래에 붙인 식별자. `(account, source, external_id)`가 같으면 같은 거래다(R-06). |
| 보호(protected) | 사용자가 건드렸거나 import가 만들었거나 제외된 entry는 provider sync가 덮어쓰지 않는다(R-09). |
| 잠금(locked attribute) | 사용자가 바꾼 필드 이름을 `locked_attributes`(필드명 → 잠근 시각 map)에 기록해 두면, 그 필드만 sync가 바꾸지 않는다(R-31, R-33). |
| `extra` namespace | `Transaction#extra`의 최상위 키 하나가 provider 하나의 영역이다(예: `extra["simplefin"]`). |
| 확정(booked)/보류(pending) | 보류는 provider가 "아직 확정 전"이라고 표시한 거래다. 표시는 `extra[<provider>]["pending"]` 값이다(R-30). |

**import adapter 연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `new(account)` | 계정 1개 → 어댑터 | 모든 쓰기가 이 계정에 간다. `account`(읽기 전용 접근자)와 `skipped_entries`(빈 목록)를 들고 있다. |
| `account` | → `Account` | 어댑터가 묶인 계정. |
| `skipped_entries` / `reset_skipped_entries!` | → 목록 / 비움 | 보호로 건너뛴 거래 기록이 인스턴스 수명 동안 쌓인다. `reset_skipped_entries!`는 이 SHA에서 외부 호출처가 없다(2.1). |
| `import_transaction(...)` | 1.3 아래 표 → `Entry` | 거래 upsert. 규칙 R-06~R-42. |
| `import_holding(...)` | 아래 표 → `Holding` | 보유종목 upsert. R-43~R-50. |
| `import_trade(...)` | 아래 표 → `Entry`(Trade) | 매매 upsert. R-51~R-55. |
| `find_or_create_merchant(provider_merchant_id:, name:, source:, website_url: nil, logo_url: nil)` | → provider 가맹점 레코드 또는 nil | R-56~R-57. |
| `update_balance(balance:, cash_balance: nil, source: nil)` | → 계정 갱신 | R-58. |
| `update_accountable_attributes(attributes:, source:)` | map → true/false | R-59. |
| `find_duplicate_transaction(date:, amount:, currency:, name: nil, exclude_entry_ids: nil, date_window: 0, include_provider_entries: false)` | → `Entry` 또는 nil | 수동·CSV 거래 중복 후보. R-15. 외부 호출자도 있다(CSV import, 명세서 import(`pdf_import.rb`), Monarch import(`monarch_import/converter.rb:158`), Enable Banking). |
| `find_scheduled_transaction(date:, amount:, currency:, date_window: 7)` | → `Entry` 또는 nil | R-14. 외부 호출자는 Enable Banking(`enable_banking_entry/processor.rb:393`). |
| `find_pending_transaction(date:, amount:, currency:, source:, date_window: 8)` | → `Entry` 또는 nil | R-20. 외부 호출자는 Enable Banking(같은 파일 `:395`). |
| `find_pending_transaction_fuzzy(date:, amount:, currency:, source:, merchant_id: nil, name: nil, date_window: 3, amount_tolerance: 0.30)` | → `Entry` 또는 nil | R-26. 외부 호출처 없음. |
| `find_pending_transaction_low_confidence(date:, amount:, currency:, source:, merchant_id: nil, name: nil, date_window: 3)` | → `Entry` 또는 nil | R-27. 외부 호출처 없음. |
| `store_duplicate_suggestion(pending_entry:, posted_entry:, reason:, posted_amount:, confidence: "medium")` | → 없음 | R-28. 외부 호출처 없음. |
| `detect_activity_label(name, amount)` | → 라벨 문자열 또는 nil | R-38. Enable Banking이 외부에서 호출한다. |
| `determine_skip_reason(entry)` / `record_skip(entry, reason)` | → 문자열 또는 nil / 기록 | R-09, R-05. CoinStats processor가 외부에서 호출한다. |

**`import_transaction` 인자**

| 인자 | 타입 | 필수·기본 | 의미·제약 |
|---|---|---|---|
| `external_id` | string | 필수(blank면 `ArgumentError`) | `(account, source)` 안에서 유일. 접두어 규칙은 없다. SimpleFIN은 `"simplefin_<id>"`, Plaid는 원본 `transaction_id`를 쓴다. |
| `source` | string | 필수(blank면 `ArgumentError`) | provider 이름. 같은 계정에 provider 둘이 같은 `external_id`를 써도 `source`가 다르면 별개 entry다. |
| `amount` | decimal | 필수 | `Entry.amount`에 그대로 저장(소수 4자리까지, R-31). 부호는 양수가 지출, 음수가 수입이다. SimpleFIN processor는 provider 값의 부호를 반전해서 넘긴다. |
| `currency` | string | 필수 | entry의 통화. 계정 통화와 달라도 저장된다. |
| `date` | date | 필수 | 오늘 기준 30년보다 오래된 날짜는 저장 검증에서 실패한다. |
| `name` | string | 필수 | blank면 저장이 실패한다(R-32). |
| `category_id` | id | nil | 있으면 잠금이 없을 때만 반영(R-33). |
| `kind` | string | nil | `standard`, `funds_movement`, `cc_payment`, `loan_payment`, `one_time`, `investment_contribution`. 이 6개 밖의 값은 `ArgumentError`(Rails enum 동작, 추론). 라벨·`Loan` 규칙이 먼저 적용되고(R-39), 주어진 값은 `kind` 잠금과 무관하게 덮어쓴다. |
| `merchant` | 가맹점 레코드 | nil | `merchant.id`가 `Transaction.merchant_id`로 반영(R-33). |
| `notes` | string | nil | 비어 있지 않을 때만 반영(R-33). |
| `pending_transaction_id` | string | nil | 이 확정 거래가 대체하는 보류 거래의 `external_id`(R-19). |
| `extra` | map | nil | provider 네임스페이스 map. 최상위 키가 네임스페이스다. 병합 규칙은 R-35~R-37. |
| `investment_activity_label` | string | nil | `Transaction`에는 값 목록 검증이 없다. 값은 `Transaction::ACTIVITY_LABELS`(C-17). |
| `allow_heuristic_matching` | bool | true | false면 R-13의 claim과 R-20의 금액 일치 claim, R-25의 제안을 모두 끈다. FinanceKit, Sharesight(`cash_router`, `funding_mirror`), Trade Republic는 false를 고정으로 넘기고, Enable Banking은 상황에 따라 계산한 값을 넘긴다(`grep -rn allow_heuristic_matching app lib`). |
| `replace_extra_namespaces` | string 목록 | `[]` | provider가 통째로 소유하는 네임스페이스(R-36). |
| `name_extra_keys` | map(네임스페이스 → 키 목록) | `{}` | `name`을 만드는 데 쓴 `extra` 키(R-11). |

**입력 타입 계약**: 어댑터는 숫자 인자의 타입을 검사하지 않는다. `find_*` 메서드는 `date`를 `Date.parse(date.to_s)`로 바꾸고 fuzzy 계열은 `BigDecimal(amount.to_s)`를 쓰므로 날짜 문자열과 금액 문자열·정수·소수를 받는다. 그러나 `import_trade`는 `quantity.negative?`와 `quantity > 0`, `qty.to_d`를 값에 그대로 호출하므로 `quantity`는 숫자 타입(정수·Float·BigDecimal)이어야 하고 문자열이면 예외가 난다. `import_transaction`의 `amount`는 DB 컬럼 타입(decimal)으로 변환되어 저장되므로 숫자 문자열도 저장은 되는 것으로 보이나(추론), `entry.amount.negative?` 판정은 변환된 값으로 한다. 안전한 입력은 모든 금액·수량에 십진수 타입(BigDecimal)이다. Float는 이진 오차가 있으므로 피한다.

**`import_holding` 인자**: `security`(필수), `quantity`, `amount`(계정 통화 기준 총 평가액), `currency`, `date`, `price`(시그니처상 선택이지만 `Holding`이 필수로 검증하므로 nil이면 저장 실패, R-47), `cost_basis`(nil 가능), `external_id`(nil 가능), `source`(필수, 검증에만 쓰고 저장하지 않는다, R-50), `account_provider_id`(nil 가능), `delete_future_holdings`(기본 false).

**`import_trade` 인자**: `security`(필수), `quantity`(매수 양수, 매도 음수), `price`, `amount`(수수료를 포함한 현금 영향 총액), `currency`, `date`, `name`(nil이면 생성), `external_id`(nil 가능), `source`(필수), `activity_label`, `exchange_rate`(`Trade`의 `extra["exchange_rate"]`에 저장되고 컬럼이 아니다, R-52), `fee`(`amount`에 이미 포함된 수수료).

**저장 제약 (db/schema.rb, C-24)**

| 대상 | 제약 | 동작으로 풀면 |
|---|---|---|
| `entries` | `amount` decimal(19,4) not null, `name` not null, `account_id` not null, `excluded` 기본 false, `import_locked`·`user_modified` 기본 false not null, `locked_attributes` jsonb 기본 `{}` | 금액은 소수 4자리로 반올림 저장. 모델 검증은 `date`·`name`·`amount`·`currency` 필수, `date`는 오늘 기준 30년 이내(`Entry.min_supported_date`). |
| `entries` | unique `(account_id, source, external_id)`, 단 두 값이 모두 not null일 때만 | external_id가 없거나 source가 없는 entry는 중복 제한이 없다. 모델 검증도 같은 조건이다. |
| `transactions` | `extra` jsonb not null 기본 `{}`, `kind` 기본 `"standard"` not null, `locked_attributes` 기본 `{}`, GIN index on `extra` | `extra`가 nil이 되면 안 된다. `transactions.external_id` 컬럼도 있지만 어댑터는 쓰지 않는다(2.1). |
| `transactions` | unique index on `extra->'goal'->>'pledge_id'` (값이 있을 때) | 같은 pledge로 두 거래를 확정하지 못한다. `goal`은 Sure가 쓰는 네임스페이스다(R-37). |
| `trades` | `security_id` not null, `fee` decimal(19,4) 기본 0 not null, `price` decimal(19,10), `qty` decimal(34,18), `extra` jsonb 기본 `{}` not null | 매매 가격은 소수 10자리, 수량은 18자리까지 저장. |
| `holdings` | `qty` decimal(34,18) not null, `price` decimal(19,**4**) not null, `amount` decimal(19,4) not null, `currency`·`date`·`security_id`·`account_id` not null, `security_locked`·`cost_basis_locked` 기본 false not null | 보유 가격은 소수 4자리로 반올림된다(매매 가격과 정밀도가 다르다). 모델 검증은 `qty`·`price`·`amount`가 0 이상이다. 공매도 같은 음수 보유는 저장되지 않는다. |
| `holdings` | unique `(account_id, security_id, date, currency)`, unique `(account_id, external_id)`(external_id가 있을 때) | 한 계정·종목·날짜·통화에 행이 하나. external_id는 계정 안에서 유일(provider와 무관). |
| `account_providers` | `account_id`, `provider_id`(uuid), `provider_type` 모두 not null, unique `(account_id, provider_type)`, unique `(provider_type, provider_id)` | 계정 하나는 provider 종류(클래스) 하나당 연결이 최대 하나. provider 계정 하나는 Sure 계정 하나에만 연결된다. |
| `data_enrichments` | unique `(enrichable_id, enrichable_type, source, attribute_name)`, `value`·`metadata` jsonb | 같은 대상·출처·속성은 한 행이고 갱신된다. |
| `merchants` | provider 가맹점: unique `(source, name)`, unique `(provider_merchant_id, source)`(id가 있을 때), `name` not null | R-56. |

**`Transaction#extra` 규약**

최상위 키는 두 부류다. provider 네임스페이스(`simplefin`, `plaid`, `kraken` 등)는 provider가 쓴다. Sure 소유 키는 R-37에 나열한다. provider는 Sure 소유 키 이름을 쓰면 안 된다. 보류 표시 네임스페이스는 고정 목록(`PENDING_PROVIDERS`, R-30)에 있어야 인식된다.

**provider adapter 최소 계약 (`Provider::Base`)**

| 연산 | 의미 |
|---|---|
| `Provider::Factory.register("<ProviderAccount 클래스명>", 어댑터 클래스)` | 클래스 본문에서 등록. 등록이 없으면 `create_adapter`가 `nil`이 아니라 `AdapterNotFoundError`를 던진다(R-62). |
| `new(provider_account, account: nil)` | provider 계정 레코드와 대상 계정을 받는다. `account`를 안 주면 `provider_account.account`를 쓴다. 접근자 `provider_account`, `account`. |
| `provider_name` | 필수 구현(없으면 `NotImplementedError`). 예: `"kraken"`. |
| `provider_type` | provider 계정 클래스 이름(예: `"KrakenAccount"`). |
| `raw_payload`, `metadata` | `provider_account.raw_payload`, `{provider_name:, provider_type:}`(institution 메타데이터 모듈이 있으면 `institution:` 추가). |
| `self.supported_account_types` | 기본 `[]`. 지원 accountable 종류 목록(예: `["Crypto"]`). |
| `can_delete_holdings?` | 기본 false. R-49·R-63. |
| `self.connection_configs(family:)` | 기본 `[]`. UI 연결 정보. 이 스펙 범위 밖. |
| `self.connection_item_class`, `self.member_connectable?` | 기본 nil, 기본 false(item 클래스가 `credential_scope :per_connection`을 선언해야 true). 일반 멤버의 연결 허용 여부. 이 스펙 범위 밖. |

### 1.4 행동 규칙과 남은 질문

**호출 규약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | import adapter를 만든다 | 어댑터는 계정 1개에 묶이고 이후 모든 조회·쓰기는 그 계정의 entries·holdings로 한정된다(`account.entries`·`account.holdings`에서 시작). 어댑터를 얼마나 오래 들고 있을지는 호출자가 정한다. 거래 entry processor 대부분(예: Plaid, Akahu, Brex, Lunchflow, Mercury, Monobank, Fio)은 거래 한 행마다 processor를 새로 만들고 그 안에서 `@import_adapter ||= 어댑터.new(account)`로 어댑터를 만든다(어댑터 주석도 "most processors build an adapter per row"). 이 경우 `skipped_entries`는 어댑터마다 따로 쌓이고 호출자가 모으지 않으면 버려진다. SimpleFIN processor와 Enable Banking account processor는 sync 한 번 동안 어댑터 하나를 만들어 모든 거래에 공유해 `skipped_entries`를 모은다. holding·activity processor는 계정 단위로 하나를 쓴다. | 코드 확인(Plaid, SimpleFIN, Enable Banking, Kraken processor를 열어 읽음) / 추론(나머지 processor는 `@import_adapter ||=` 줄만 확인) |
| R-02 | `import_transaction`·`import_holding`·`import_trade` 호출에서 필수 인자가 비었거나 저장 검증이 실패하거나 DB unique 충돌이 난다 | `external_id`(import_transaction)·`source`·`security`(holding·trade)가 비면 `ArgumentError`. 그 밖의 저장 실패(`name` blank, 날짜 범위 밖, `price` nil인 holding 등)는 예외로 호출자에게 그대로 전파된다. 어댑터에 행 단위 rescue는 없고, `import_transaction`은 호출 하나가 DB transaction 하나라서 예외가 나면 그 호출의 쓰기가 모두 되돌려진다. 호출자 processor가 행마다 rescue하고 다음 행으로 넘어간다(SimpleFIN은 오류 수를 세고 계속). | 코드 확인 |
| R-03 | 어댑터 메서드가 entry·holding·계정을 저장한다 | 어댑터는 account sync를 예약하지 않고 balance를 재계산하지도 않는다. sync 예약은 호출자(syncer)의 일이다. | 코드 확인 (검색 범위는 2.1) |
| R-04 | provider가 어댑터를 거치지 않고 entry를 직접 만든다 | 허용되는 구현이다. Kraken processor는 매매를 `import_trade`가 아니라 `account.entries.create!`로 직접 만든다(`source: "kraken"`, `external_id: "kraken_trade_<txid>"`). 직접 만들어도 R-06의 unique 제약과 `Entry` 검증은 똑같이 적용되지만, 이 스펙의 보호·claim 규칙은 적용되지 않는다. 직접 만든 쪽은 보호 확인을 스스로 한다(Kraken은 갱신 때 `protected_from_sync?`를 확인). | 코드 확인 |
| R-05 | 보호 때문에 거래를 건너뛴다(R-09, R-16) | `skipped_entries`에 `{id, name, reason, external_id, account_name}` 한 건이 추가된다. `reason`은 `"excluded"`, `"user_modified"`, `"import_locked"`, 보호된 중복 claim일 때는 `determine_skip_reason`의 값 또는 `"protected"`. 호출자가 sync가 끝나면 `tx_skipped`(건수), reason별 건수, 앞 20건 상세로 sync 통계에 올린다. 목록은 어댑터 수명 동안 늘기만 하고 지우는 호출자는 없다. | 코드 확인 |

**기존 entry 식별과 보호 (`import_transaction`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `(account, source, external_id)`가 같은 entry가 있다 | 그 entry를 갱신 대상으로 쓴다. 없으면 `Transaction`을 entryable로 하는 새 entry를 준비한다(아직 저장 전). 같은 `external_id`라도 `source`가 다르면 서로 다른 entry다. DB와 모델 검증이 `(account, source, external_id)` 유일을 강제한다. | 코드 확인 |
| R-07 | 같은 키의 기존 entry가 `Transaction`이 아니다(예: `Trade`) | `ArgumentError`("already exists with different entryable type"). 보호 검사보다 먼저 일어난다. | 코드 확인 |
| R-08 | 들어온 `extra`에 보류 표시가 있다 | "들어온 거래는 보류"는, `extra`가 map이고 `PENDING_PROVIDERS` 네임스페이스 중 하나라도 값이 map이면서 그 `"pending"`이 참이면 성립한다. 거짓으로 읽는 값은 정해져 있고 그 밖은 모두 참이다. 거짓: `false`, 정수 `0`, 문자열 `"0"`, `"f"`, `"F"`, `"false"`, `"FALSE"`, `"off"`, `"OFF"`(Rails가 거짓으로 캐스트하는 값), 빈 문자열, null. `"False"`, `"Off"`, `"no"`처럼 이 목록에 없는 표기는 참(보류)이다. 레포 주석(`transaction.rb:145-150`)이 PostgreSQL은 `"no"`·`"False"`·`"Off"`를 거짓으로 읽지만 이 판정은 참으로 읽는다고 명시한다. JSON 숫자 `0.0`도 보류로 읽힌다(`:155`). 값이 map이 아닌 네임스페이스는 무시하고, `extra`가 없으면 "확정"으로 취급한다. 이 판정이 R-10, R-13 이후의 모든 분기를 가른다. | 코드 확인(구조와 "no/False/Off는 참"이라는 주석) / 추론(거짓 문자열의 정확한 집합은 프레임워크 상수, 1.4 확인 한계) |
| R-09 | 기존 entry가 있고 `excluded`, `user_modified`, `import_locked` 중 하나가 참이다 | 보호 상태다. 이유는 `excluded` > `user_modified` > `import_locked` 순으로 첫 참을 쓴다. 보호 상태이면 `amount`·`currency`·`date`·`name`·`category`·`merchant`·`notes`·`kind`·라벨을 건드리지 않고, 아래 R-10·R-11의 예외 갱신만 한 뒤 기존 entry를 반환하며 R-05의 기록을 남긴다. 이후 단계(heuristic, 확정 대조, goal 대조, 제안)는 실행되지 않는다. | 코드 확인 |
| R-10 | R-09의 이유가 `user_modified`이고 들어온 거래가 보류가 아니며 저장된 거래가 보류 상태다 | 저장된 `extra`에서 보류 표시를 지운다. `PENDING_PROVIDERS` 네임스페이스마다 `"pending"` 키를 제거하고 그 결과 네임스페이스가 비면 네임스페이스도 제거한다. 사용자가 보류 거래를 분류해 `user_modified`가 된 뒤 같은 `external_id`로 확정본이 오는 경우에 보류 배지가 영구히 남는 것을 막는다. entry가 `user_modified`와 `import_locked`를 둘 다 가지면 이유는 `user_modified`이므로 이 예외만 실행되고 R-11은 실행되지 않는다. `excluded`·`import_locked`만인 entry에는 적용되지 않는다. | 코드 확인 |
| R-11 | R-09의 이유가 `user_modified`이고 `import_locked`가 아니다 | `replace_extra_namespaces`에 적은 네임스페이스만 들어온 `extra`에서 잘라, 저장된 `extra`의 같은 네임스페이스 가지를 통째로 교체한다(R-36). 다만 `name_extra_keys`로 선언된 키는 저장된 값이 있으면 그 값을 유지한다(사용자가 이름을 지켰으므로 이름의 재료도 지킨다). 저장된 값이 없는 키는 들어온 값을 쓴다. `replace_extra_namespaces`가 `[]`이면(기본값) 아무것도 바뀌지 않는다. 최상위 `extra` 전체를 병합하지 않는 이유는 `extra["exchange_rate"]`처럼 사용자가 편집하는 값이 같은 map에 있기 때문이다. | 코드 확인 |
| R-12 | R-09의 이유가 `excluded` 또는 `import_locked`다(이유가 `user_modified`가 아니다. `excluded`와 `user_modified`를 함께 가진 entry의 이유는 `excluded`이므로 R-10·R-11도 실행되지 않는다) | 어떤 필드도 바뀌지 않는다. `import_locked`는 파일 import 경로가 켠다. CSV import는 새 entry에 true를 쓰고 중복으로 찾은 기존 entry도 true로 바꾼다(`transaction_import.rb:66`). QIF·PDF·Monarch import도 true를 쓴다. family data import는 원본 데이터의 `import_locked`가 참일 때만 true로 켜고, import 세션이 있으면 `external_id`와 `source`를 세션 값으로 채운다(`family/data_importer.rb:997-1003`). 그래서 `import_locked` entry의 `external_id`는 대개 비어 있지만 항상 비어 있지는 않다. 수동 입력 entry는 `user_modified`가 참이다. | 코드 확인 |

**새 키일 때: 수동·예정 거래 claim**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | 새 키(R-06에서 못 찾음)이고 `allow_heuristic_matching`이 참이다 | 먼저 `find_scheduled_transaction`을 부르고, 결과가 없을 때만 `find_duplicate_transaction(date, amount, currency)`를 부른다(이름은 넘기지 않는다. provider마다 이름 형식이 달라서다). 들어온 거래가 보류여도 이 단계는 실행된다. | 코드 확인 |
| R-14 | `find_scheduled_transaction` | 같은 계정의 `Transaction` entry 중 `external_id`가 없고, `amount`·`currency`가 정확히 같고, 날짜가 들어온 날짜의 ±7일 안이고, `created_at`이 entry의 `date`보다 이른 것(미리 입력한 예정 거래)을 찾는다. 날짜 차이가 가장 작은 것, 같으면 `created_at`이 이른 것을 고른다. 찾으면 그 entry를 claim한다: `external_id`, `source`를 쓰고 `date`를 provider 날짜로 바꾼다. 사용자 수정으로 보호된 entry도 claim한다. 이후 `name`·카테고리·메모는 개별 잠금을 존중해 갱신된다. | 코드 확인 |
| R-15 | `find_duplicate_transaction` | 같은 계정의 `Transaction` entry 중 `amount`·`currency` 정확 일치, `parent_entry_id` 없음(분할 자식 제외), 날짜가 같음(`date_window`가 0이면 같은 날, 아니면 ±window일), 기본으로 `external_id`가 없음(`include_provider_entries`가 참이면 provider가 만든 것도 포함)을 찾는다. `name`을 주면 이름이 같아야 하고, `exclude_entry_ids`는 후보에서 뺀다. 정확한 날짜 검색은 `created_at`이 가장 이른 것, 창 검색은 날짜가 가장 가까운 것(같으면 `created_at`이 이른 것)을 반환한다. 소비처가 다르다. provider sync는 기본값, CSV import는 `name`과 `exclude_entry_ids`, 명세서 import는 `date_window`와 `include_provider_entries`를 쓴다. | 코드 확인 |
| R-16 | R-15로 찾은 중복이 보호 상태(`excluded`·`user_modified`·`import_locked` 중 하나)다 | 그 entry에 `external_id`와 `source`만 기록(`update!`)하고 R-05의 기록(이유는 보호 이유, 없으면 `"protected"`)을 남긴 뒤 그 entry를 반환한다. 다른 값은 바뀌지 않고, 이후 단계는 실행되지 않는다. 다음 sync에서는 `(source, external_id)`로 바로 찾히므로 R-09가 적용된다. | 코드 확인 |
| R-17 | R-15로 찾은 중복이 보호 상태가 아니다 | 그 entry에 `external_id`·`source`를 쓰고 새 entry 대신 갱신 대상으로 삼는다. 이후는 기존 entry와 같은 일반 갱신 경로(R-31 이후)를 탄다. 한 번 claim되면 `external_id`가 생기므로 같은 entry가 다시 중복 후보가 되지 않는다. | 코드 확인 |

**보류 → 확정 대조**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | 아직 새 entry(R-13~R-17에서 claim하지 못함)이고 들어온 거래가 보류가 아니다 | 같은 provider의 보류 entry를 찾는다(R-19, R-20). 찾으면 새 entry를 만들지 않고 그 보류 entry를 확정 거래로 바꾼다(R-21). | 코드 확인 |
| R-19 | `pending_transaction_id`가 있다 | 1순위. `(account, source, external_id = pending_transaction_id)`인 entry를 찾는다. `allow_heuristic_matching`과 무관하게 실행되고, 그 entry가 보류 상태인지는 확인하지 않는다. | 코드 확인 |
| R-20 | 1순위로 못 찾았고 `allow_heuristic_matching`이 참이다 | 2순위 `find_pending_transaction`. 같은 계정·같은 `source`·같은 `currency`·`amount` 정확 일치이고, 보류 상태(R-30)이고, 날짜가 `[들어온 날짜 − 8일, 들어온 날짜]` 안인 `Transaction`을 찾아 가장 최근 날짜를 반환한다. 보류 날짜가 확정 날짜보다 늦은 것은 후보가 아니다. | 코드 확인 |
| R-21 | 보류 entry를 찾았다 | 그 entry를 갱신 대상으로 삼고 `external_id`를 새 값으로 바꾼다(`source`는 같다). `extra`에서 보류 표시를 지우고(R-10과 같은 방식), 옛 `external_id`를 `extra["auto_claimed_pending_ids"]`(문자열 배열, 중복 제거)에 추가한다. 이 값은 sync 쪽이 보관된 원본 payload의 옛 보류 행을 다시 새 거래로 import하지 않게 하는 용도다. 소비처는 Enable Banking과 Lunchflow processor 둘뿐이다(2.1). 날짜는 보류 entry가 가진 날짜를 유지한다(R-24). | 코드 확인 |
| R-22 | R-21의 claim | claim 대상 보류 entry에는 R-09의 보호 검사를 하지 않는다. `user_modified`인 보류 entry도 claim되고, 이름·카테고리 등은 개별 잠금이 있으면 유지되고 없으면 확정 값으로 바뀐다(사용자가 이름을 바꾼 보류 entry는 그 이름을 지킨다). 금액·통화는 R-31의 잠금 규칙을 따른다. | 코드 확인 (보호 검사가 없다는 주장의 범위는 2.1) |
| R-23 | 이미 있는 entry를 갱신 대상으로 삼았다(같은 키로 찾았거나, R-14·R-17·R-21의 claim)이고 들어온 거래가 보류가 아니고 저장된 거래가 보류 상태이며 R-09의 보호 skip으로 일찍 끝나지 않았다 | 저장된 `extra`에서 보류 표시를 지운다. 새 entry가 아닌 모든 경로에 적용되므로 예정 거래·수동 거래 claim(R-14·R-17)도 포함한다(R-21의 claim은 이미 지웠으므로 효과가 없다). 같은 `transaction_id`를 보류와 확정에 재사용하는 provider(예: Enable Banking의 일부 은행)가 같은 키 경로로 이 규칙을 탄다. `extra`가 nil이어서 R-35가 실행되지 않아도 지워진다. | 코드 확인 |
| R-24 | 날짜 결정(`effective_date`) | 보류 claim이 일어났으면 그 보류 entry의 날짜를 쓴다. 보류 claim이 아니더라도 기존 entry의 `extra`에 `"auto_claimed_pending_ids"` 키가 있으면(과거에 claim된 적 있음) 저장된 날짜를 유지한다. 그 밖에는 들어온 날짜를 쓴다. 따라서 claim된 거래의 날짜는 확정일이 아니라 보류 시작일로 고정된다. | 코드 확인 |
| R-25 | 이번 호출로 완전히 새로 생긴 확정 거래(claim 없음)이고 `allow_heuristic_matching`이 참이다 | 저장 직후 같은 `source`의 보류 entry 중 비슷한 것에 "중복 의심" 제안을 남긴다. 먼저 R-26, 없으면 R-27 순서로 찾는다. 자동 병합은 하지 않는다. | 코드 확인 |
| R-26 | `find_pending_transaction_fuzzy` | 같은 계정·`source`·`currency`, 날짜 `[날짜 − 3일, 날짜]`, 보류 상태이고, `|보류 금액|`이 `[|확정 금액| / 1.3, |확정 금액|]` 안인 후보. 그다음 (1) `merchant_id`가 주어지고 가맹점이 같은 후보가 정확히 1개면 그것, (2) 아니면 이름 비교 키가 같은 후보가 정확히 1개면 그것, 그 밖에는 nil이다. 후보가 2개 이상이면 모호하다고 보고 포기한다. 이름 비교 키는 이름을 소문자로 바꾸고 `a-z`, `0-9`, 공백이 아닌 문자를 모두 지운 뒤 처음 세 단어를 공백으로 이은 것이다. 한글처럼 ASCII 영숫자가 아닌 글자는 지워지므로 한글 이름은 키가 빈 문자열이 되어 이름 비교가 꺼지고 가맹점 일치만 남는다. | 코드 확인 |
| R-27 | `find_pending_transaction_low_confidence` | R-26에서 못 찾았을 때만. 같은 계정·`source`·`currency`, 날짜 `[날짜 − 3일, 날짜]`, 보류 상태, `|보류 금액|`이 `[|확정 금액| / 2, |확정 금액| × 0.77]` 안. 가맹점과 이름 비교 키가 모두 같은 후보가 정확히 1개일 때만 반환한다(`merchant_id`나 `name`이 없거나 키가 비면 nil). | 코드 확인 |
| R-28 | `store_duplicate_suggestion`(R-26·R-27 결과가 있을 때) | 보류 entry가 `Transaction`이 아니거나, 이미 `extra["potential_posted_match"]`가 있거나(기존 제안이 dismiss 됐어도 덮어쓰지 않음), 확정 쪽 entry가 보류 상태이면 아무것도 하지 않는다. 아니면 보류 거래의 `extra["potential_posted_match"]`에 `{entry_id: 확정 entry id, reason: "fuzzy_amount_match" 또는 "low_confidence_match", posted_amount: 금액 문자열, confidence: "medium" 또는 "low", detected_at: 오늘 날짜 문자열}`을 기록한다. 이 기록이 `RecordInvalid`로 실패해도 import는 계속된다(경고 로그만). 사용자가 제안을 받아들이는 수동 병합은 transactions 스펙 소관이다. 병합 결과로 확정 거래의 `extra["manual_merge"]`에 `{merged_from_entry_id, merged_from_external_id, merged_at, source}` 항목이 쌓이고, 확정 entry는 `user_modified`가 된다. | 코드 확인 |
| R-29 | 정리 보조 함수 `Entry.auto_exclude_stale_pending`, `Entry.reconcile_pending_duplicates` | 어댑터가 부르지 않는다. 호출처는 SimpleFIN importer뿐이다. 전자는 보류 상태이고 날짜가 8일보다 오래된 entry를 `excluded = true`로 일괄 갱신한다. 후자는 보류 entry마다 두 단계로 찾는다. (1) 같은 통화·같은 금액·날짜 `[보류일, 보류일+8일]`의 확정 거래를 최대 2개까지 찾아 정확히 1개면 보류 entry를 `excluded`로 만든다. 0개 또는 2개 이상이면 (2)로 간다. (2) 날짜 `[보류일, 보류일+3일]`, `|확정 금액|`이 `[|보류 금액|, |보류 금액|×1.25]`, 같은 통화, 이름 비교 키(R-26)가 같은 확정 후보가 정확히 1개일 때만 제안을 남긴다(자동 제외 없음, 기존 제안이 있으면 덮지 않음). 이 경로가 저장하는 제안은 `{entry_id, reason: "fuzzy_amount_match", posted_amount, confidence: "medium", dismissed: false, detected_at}`로 `dismissed` 키를 포함한다. R-28의 `store_duplicate_suggestion`이 저장하는 제안에는 `dismissed` 키가 없다. 읽는 쪽은 키가 없으면 거절 안 함(false)으로 읽어야 한다. `dismissed`는 사용자가 제안을 거절할 때 true가 된다(`dismiss_duplicate_suggestion!`). 새 연동이 같은 문제를 겪으면 직접 호출해야 한다. | 코드 확인 |
| R-30 | 보류 상태 판정 | `Transaction#pending?`(Ruby), `Transaction.pending_sql`(SQL), `Entry.pending`·`excluding_pending` 스코프가 모두 같은 규칙을 쓴다. `PENDING_PROVIDERS` = `akahu`, `enable_banking`, `financekit`, `lunchflow`, `mercury`, `monobank`, `plaid`, `redbark`, `simplefin`, `up` 10개 네임스페이스 중 하나라도 `extra[<ns>]["pending"]`이 참이면 보류다(값이 map이 아닌 네임스페이스는 무시). SQL에서는 값이 없거나 JSON null이면 거짓, 문자열로 읽은 값이 거짓 값 목록(R-08)에 없으면 참이다. 이 목록에 없는 이름의 네임스페이스는 `pending: true`를 써도 보류로 인식되지 않는다. 보류 거래는 소득·지출 집계 SQL에서 제외된다(`not_pending_sql`, `pending_providers_sql`). UI는 보류 배지를 띄운다. | 코드 확인 |

**갱신 규칙 (기존 entry 또는 claim된 entry)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | 금액·통화·날짜 | `amount`, `currency`, `date`(R-24의 `effective_date`)를 들어온 값으로 덮어쓴다. 단 이미 저장된 entry에서 `date`가 잠겨 있으면(사용자나 API가 바꿔 `locked_attributes`에 있음) 날짜는 빼고, `amount` 또는 `currency` 중 하나라도 잠겨 있으면 금액과 통화 둘 다 뺀다(둘은 한 쌍이다). 잠금은 `user_modified` 플래그가 없어도 적용된다(API PATCH 등). 단 R-14의 예정 거래 claim은 날짜를 잠금과 무관하게 먼저 덮어쓴다. | 코드 확인 |
| R-32 | `name` | `enrich_attribute(:name)`: 이름이 잠겨 있지 않고 저장된 값과 다르면 바꾼다. 새 entry라면 이때 첫 저장이 일어난다. `name`이 blank이면 저장이 실패하고 이어지는 최종 저장에서 예외가 난다. 자동 이름 생성(`auto_generate_transaction_names?`)은 `external_id`나 `source`가 있는 entry에는 적용되지 않으므로 provider 거래는 빈 이름을 받지 못한다. SimpleFIN processor는 이름이 없으면 번역된 "unknown" 문구로 채운다. | 코드 확인 |
| R-33 | `category_id`, `merchant`, `notes` | 값이 있을 때만 각각 `Transaction.category_id`, `Transaction.merchant_id`(= `merchant.id`), `Entry.notes`를 R-34의 방식으로 갱신한다(잠금이 있으면 유지). `notes`는 blank이면 아예 건드리지 않아 기존 메모를 지우지 않는다. `category_id`·`merchant`가 nil이면 기존 값은 그대로 남는다. | 코드 확인 |
| R-34 | 속성 단위 갱신과 출처 기록 (`enrich_attributes`) | 갱신 대상 속성 중 잠금이 없고 저장된 값과 다른 것만 새 값으로 바꾸고 저장한다. 저장이 거절되면 savepoint로 되돌리고 `false`를 돌려준다(호출 전체 transaction은 유지). 대상이 이미 저장된 record(새 record의 첫 저장이 아님)였으면 속성마다 `data_enrichments`에 `(enrichable, source, attribute_name)` 한 행을 만들거나 갱신해 `value`(바꾼 값)와 `metadata`를 기록한다. 이것이 속성 단위 출처 기록이다. `DataEnrichment.source`는 닫힌 목록(25개)이라 목록에 없는 `source`로 기존 record의 이름·카테고리 등이 바뀌면 이 기록 단계에서 오류가 날 수 있다(목록에 coinspot·snaptrade·trading212·financekit 등 import에 쓰이는 이름이 빠져 있다). `ProviderMerchant.source`도 별도의 닫힌 목록이고(18개: ai, akahu, brex, coinstats, enable_banking, fio, indexa_capital, lunchflow, mercury, monobank, plaid, questrade, redbark, simplefin, sophtron, synth, truelayer, up) `DataEnrichment`의 25개와 목록이 다르다. `find_or_create_merchant`의 `source`가 목록 밖이면 가맹점 생성에서 같은 종류의 오류가 날 가능성이 크다. 확인한 호출부의 `source`(akahu, brex, coinstats, enable_banking, fio, lunchflow, mercury, monobank, plaid, redbark, simplefin, sophtron, truelayer, up)는 모두 이 목록 안이다. provider 스캐폴드 생성기가 새 provider를 만들 때 두 enum 파일에 이름을 추가하므로(`lib/generators/provider/family/family_generator.rb:481-486`) 목록 갱신은 의도된 등록 절차다. | 코드 확인(알고리즘, 목록) / 추론(닫힌 enum이 오류를 낸다는 점은 Rails enum 동작 가정) |
| R-35 | `extra` 적용 (`apply_provider_extra`) | `extra`가 비어 있거나(nil·빈 map) entryable이 `Transaction`이 아니면 아무것도 하지 않는다(저장된 `extra`는 그대로). 아니면 `새 extra = (저장된 extra에서 교체 대상 네임스페이스를 뺀 것).deep_merge(들어온 extra)`로 즉시 저장한다. 들어온 키는 문자열로 정규화된다. deep merge는 map끼리는 재귀로 합치고, 배열·스칼라는 들어온 값이 덮어쓰며, 들어온 `nil`도 값으로서 저장된 값을 덮는다. 키가 `extra`에서 사라지길 원하면 들어온 쪽에서 안 보내는 것으로는 부족하고 R-36을 쓰거나 값을 명시해야 한다. | 코드 확인 |
| R-36 | `replace_extra_namespaces` | 목록에 있고 들어온 `extra`에도 있는 최상위 키의 저장된 가지는 병합 전에 버려지고 들어온 가지로 대체된다. 들어온 `extra`에 없는 네임스페이스는 대상이 아니므로 저장된 값이 남는다. 매번 현재 스냅샷을 통째로 보내는 provider(Plaid의 `"plaid"`)가 쓴다. 중첩 키(예: `payment_meta.payee`)를 provider가 보내지 않게 되면 이 옵션이 없을 때는 영구히 남고 있을 때는 사라진다. | 코드 확인 |
| R-37 | Sure가 `extra` 최상위에서 직접 읽고 쓰는 키 | `goal`(목표 pledge 확정 기록, `goal.pledge_id`는 unique index 대상), `potential_posted_match`(R-28), `manual_merge`(수동 병합 기록), `auto_claimed_pending_ids`(R-21), `exchange_rate`와 `exchange_rate_invalid`(사용자가 편집하는 환율, 0보다 커야 함), `security_id`/`security.id`(투자 활동의 종목 참조), `superseded_external_ids`(Enable Banking processor가 쓰고 읽는 배열), `demo_financekit_activity_version`(데모 데이터 생성기 전용). provider 네임스페이스는 이 이름을 쓰면 안 된다. 나머지 최상위 키(`simplefin`, `plaid`, `redbark`, `kraken`, `binance`, `coinspot`, `monobank`, `lunchflow`, `financekit` 등)는 provider 네임스페이스다. | 코드 확인 (검색 범위는 2.1) |

**투자 활동 라벨과 `kind`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-38 | 계정이 `Investment` 종류이고 호출자가 `investment_activity_label`을 주지 않았다 | 이름으로 라벨을 추정한다(C-08). 소문자로 바꾸고 앞뒤 공백을 지운 이름이 정규식과 맞으면: `Dividend`(`^dividend`, `dividend payment`, `qualified dividend`, `ordinary dividend`), `Interest`(`^interest`, `interest income`, `interest payment`), `Fee`(`^fee`, `management fee`, `advisory fee`, `transaction fee`), `Contribution`(`employer match`, `employer contribution`, `401k`/`401(`, `ira contribution`, `roth contribution`). 맞는 것이 없으면 nil이다. 이름이 비어 있어도 nil. 정규식이 영어뿐이므로 한글 입출금명(예: 배당금, 이자, 수수료)은 항상 nil이다. 한글 데이터는 호출자가 `investment_activity_label`을 직접 넘겨야 한다. 사용자가 나중에 바꿀 수 있어서 의도적으로 보수적이다. Crypto 등 다른 계정 종류는 추정하지 않는다. | 코드 확인 |
| R-39 | 라벨(호출자 값 또는 R-38의 추정값)과 계정 종류로 `kind`를 정한다 | 우선순위: (1) 라벨이 `Transfer`, `Sweep In`, `Sweep Out`, `Exchange` 중 하나면 `funds_movement`. (2) 라벨이 `Contribution`이면 `investment_contribution`(그리고 R-40의 카테고리). (3) 계정이 `Loan`이고 `entry.amount`가 음수(상환 입금)면 `loan_payment`. (4) 위가 아니면 호출자의 `kind` 인자. 어느 것도 없으면 `kind`는 건드리지 않는다(저장된 값 유지, `standard`로 되돌리지 않음). 계정 종류 분기는 (3) 하나뿐이다. `CreditCard`용 분기는 없다(코드 주석은 신용카드를 말하지만 코드에는 없다, 2.1). `Loan` 계정이라도 `amount`가 양수이면 provider가 넘긴 `kind: "funds_movement"`가 그대로 쓰인다. 정해진 `kind`는 `kind` 잠금(`locked_attributes`)을 확인하지 않고 바로 쓴다. 그래서 provider가 `kind: "standard"`를 매 sync 넘기면 잠기지 않은 `kind`는 물론 잠긴 `kind`도 매번 덮인다(보호 entry는 R-09에서 이미 빠진다). `kind`가 6개 값 밖이면 `ArgumentError`다(추론). | 코드 확인 / 추론(enum 오류) |
| R-40 | 결정된 `kind`와 라벨, 카테고리를 쓴다 | (a) 추정·지정 라벨은 저장된 라벨이 비어 있을 때만 쓴다(한번 정해진 라벨은 덮지 않는다). (b) `kind`가 정해졌으면: 이 거래가 `Transfer`의 두 다리 중 하나이고 그 transfer가 확정(confirmed) 상태이면 `kind`는 transfer가 정한다(입금 다리는 `funds_movement`, 출금 다리는 도착 계정 종류에 따라 `loan_payment`·`cc_payment`·`investment_contribution`·`funds_movement`, 사용자가 선택했으면 그 값). 미확인(pending) transfer나 transfer가 없으면 (R-39) 값을 쓴다. 이렇게 하는 이유는 같은 이체를 두 다리가 모두 지출로 세는 이중 집계를 막기 위함이다. (c) 라벨이 `Contribution`(R-39의 (1)이 아닐 때)이면 거래에 카테고리를 넣든 말든 `account.family.investment_contributions_category`가 항상 실행된다. 이 메서드는 모든 지원 locale의 "Investment Contributions" 이름을 가진 가족의 카테고리를 모두 찾는다. 있으면 첫 번째(keeper)만 남기고 중복본의 거래·하위 카테고리·예산 카테고리(`BudgetCategory`)를 keeper로 옮긴 뒤 중복본을 `delete_all`로 삭제하고, keeper의 이름을 가족 locale의 이름으로 바꾼다. 없으면 가족 locale 이름으로 새로 만든다(색 `#0d9488`, 아이콘 `trending-up`). 카테고리 이름은 번역 문자열(I18n 키 `models.category.investment_contributions`)이라 영어로 고정되지 않는다. 이 부작용 뒤에 거래의 저장된 `category_id`가 비어 있을 때만 그 카테고리가 거래에 붙는다. | 코드 확인 |
| R-41 | 저장 후, 들어온 거래가 보류가 아니고 계정이 목표(goal)에 연결되어 있다 | `GoalPledge::Reconciler`가 그 entry에 맞는 열린 pledge를 찾아 확정한다(목표 스펙 소관). 이 reconciler는 모든 오류를 자체적으로 잡아 로그만 남기므로 import를 실패시키지 않는다. 목표 연결 여부는 어댑터 인스턴스당 한 번만 조회하고 기억한다. | 코드 확인 |
| R-42 | 새 `Transaction`이 저장될 때 | `Entry`·`Transaction`의 저장 callback이 같이 실행된다: entry 저장 후 가장 이른 날짜를 기억해 이후 sync 범위에 쓰고, `category_id`가 바뀌면 AI·Bayes 분류 기록을 "대체됨"으로 표시한다. `Transaction`이 저장될 때 `merchant_id`가 바뀌고 새 가맹점이 provider 가맹점이면 `FamilyMerchantAssociation`의 `(family, merchant)` 행을 `delete_all`한다(가족이 그 가맹점을 "연결 해제"한 기록을 지운다). 어댑터는 이 callback을 직접 부르지 않는다. 새 구현은 같은 효과(분류 기록 대체)가 필요하면 자기 쪽에서 해야 한다. | 코드 확인 |

**보유종목 (`import_holding`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-43 | 기존 행 찾기, `external_id`가 있다 | 차례로 시도: (1) 이 계정에서 `external_id`가 같은 행(provider 무관). (2) `provider_security`가 들어온 종목이고 날짜·통화가 같은 행(`account_provider_id`가 주어졌으면 그 값으로 한정). (3) `provider_security`의 티커가 들어온 종목 티커와 같고 날짜·통화가 같은 행(티커가 비면 건너뜀, provider로 한정). (4) 종목·날짜·통화가 같은 행(provider로 한정). 모두 없으면 `(종목, 날짜, 통화, account_provider_id)`로 새 행을 준비한다. | 코드 확인 |
| R-44 | 기존 행 찾기, `external_id`가 없다 | 먼저 `provider_security`가 들어온 종목이고 날짜·통화가 같은 행(사용자가 종목을 다른 것으로 바꾼 행을 찾기 위함, provider로 한정). 없으면 `(종목, 날짜, 통화)`로 찾거나 새로 준비한다. | 코드 확인 |
| R-45 | `external_id`가 있고, 같은 `(종목, 날짜, 통화)` 행이 이미 있으며, 그 행의 `account_provider_id`와 들어온 `account_provider_id`가 둘 다 있고 서로 다르다 | 다른 provider의 행이므로 건드리지 않고 그 행을 그대로 반환한다(경고 로그). 같은 계정에 provider 둘이 같은 종목·날짜를 보고해도 서로 덮지 않는다. | 코드 확인 |
| R-46 | 새 행을 만든다 | 같은 종목(또는 그 종목을 `provider_security`로 기록한 행, 또는 사용자가 잠가서 그 종목으로 바꾼 행)의 직전 날짜 행 중 가장 최근 것(`previous_holding_for`: 날짜 내림차순, 같은 날이면 rank 순서 0 = `provider_security`가 이 종목인 행, 1 = `provider_security`가 비어 있고 행의 종목이 이 종목인 행(종목을 바꾸지 않은 행), 2 = 사용자가 잠가서 이 종목으로 바꾼 행, 마지막으로 id. 연쇄 보정 A→B, B→C에서 들어온 종목이 B일 때 두 행이 같은 날에 걸려도 결과가 정해지게 한 순서다)을 찾아 그 행의 사용자 보정(종목 잠금, 평단가 잠금)을 새 행에 이어 쓴다. 가장 최근 행만 보므로 사용자가 이미 되돌린 보정은 옛날 행에서 되살아나지 않는다. | 코드 확인 |
| R-47 | 저장할 속성 | `date`, `currency`, `qty`(=`quantity`), `price`, `amount`, `account_provider_id`, `external_id`를 들어온 값으로 항상 덮어쓴다. 들어온 값이 nil이면 nil로 덮어쓰므로(예: `external_id`나 `account_provider_id`를 안 주면 기존 값이 지워진다) 같은 호출 방식을 유지해야 한다. `price`가 nil이거나 `qty`·`price`·`amount`가 음수이면 검증 실패로 예외가 난다. | 코드 확인 |
| R-48 | 종목과 평단가 결정 | 종목: 이어 받은 행이 종목 잠금이면 그 행의 종목과 잠금 상태를 쓴다. 새 행이거나 종목이 잠겨 있지 않으면 들어온 종목을 쓴다(`provider_security`가 비어 있을 때만 들어온 종목 id로 채워서 provider 원본을 기억한다). 잠긴 행은 종목을 바꾸지 않는다. 평단가: 이어 받은 행이 평단가 잠금이면 그 값. 아니면 `CostBasisReconciler`가 정한다. 우선순위는 `manual`(3) > `calculated`(2) > `provider`(1) > 없음(0)이다. provider가 보낸 평단가가 nil 또는 0이면 모르는 값으로 본다. 새 행이면 들어온 값을 쓴다. 평단가가 잠겨 있으면 절대 덮지 않는다. `manual`인 행은 `calculated`만 덮을 수 있다. 그 밖에는 들어온 출처 우선순위가 기존 이상일 때만 값이 있으면 덮는다(같은 출처·같은 값이면 쓰기 생략). | 코드 확인 |
| R-49 | `delete_future_holdings`가 참이다 | 저장 후, 계정이 `can_delete_holdings?`일 때만(연결이 없으면 참, 연결된 모든 provider의 `can_delete_holdings?`가 참일 때만 참) 같은 종목의 `date`가 들어온 날짜보다 뒤인 행을 삭제한다. `account_provider_id`가 주어졌으면 그 provider의 행만 지운다. 허용되지 않으면 삭제하지 않고 경고만 남기며 저장한 행을 반환한다. `Provider::Base`의 기본값은 false라서 provider가 명시적으로 true를 반환해야 한다(Plaid가 쓰는 동작). 삭제 대상은 들어온 종목 기준이므로 사용자가 다른 종목으로 바꾼 행은 지워지지 않을 수 있다. | 코드 확인 |
| R-50 | 저장 충돌 복구와 `source` | 저장이 `(계정, 종목, 날짜, 통화)` unique 충돌로 실패하면(동시 import 또는 다른 provider의 행) savepoint 안에서 격리하고 그 키의 기존 행을 다시 찾는다. 기존 행이 다른 provider 소유(R-45와 같은 조건)면 건드리지 않고 반환한다. 같은 provider이거나 소유자가 없으면 `qty`·`price`·`amount`를 최신 값으로(검증 없이) 갱신하고, 평단가는 R-48의 규칙대로, 소유자가 없었으면 `account_provider_id`를, `external_id`가 비어 있었으면 `external_id`를 채운다. 이 복구 중의 오류는 삼킨다. 기존 행을 못 찾으면 원래 오류를 다시 던진다. `source` 인자는 필수 검증에만 쓰이고 `holdings`에는 출처 컬럼이 없어 저장되지 않는다. | 코드 확인 |

**매매 (`import_trade`)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-51 | 이름과 키 | `external_id`가 있으면 `(account, source, external_id)`로 찾거나 새로 준비한다. 없으면 호출 때마다 새 entry를 만든다(중복 제거 없음). 같은 키의 기존 entry가 `Trade`가 아니면 `ArgumentError`. `name`이 없으면 `"<Buy 또는 Sell> <수량 절댓값> shares of <ticker>"`(수량이 음수면 Sell)로 만든다. | 코드 확인 / 추론(수량 문자열 표기는 10, 10.0 중 어느 쪽인지 미확인) |
| R-52 | `Trade` 속성 | `security`, `qty`(=`quantity`), `price`, `currency`, `investment_activity_label`(= `activity_label` 또는 `qty > 0`이면 `"Buy"`, 아니면 `"Sell"`)를 항상 쓴다. `fee`는 nil이 아닐 때만 쓴다(nil이면 기존 값 유지). `exchange_rate`도 nil이 아닐 때만 `Trade#exchange_rate=`로 쓰는데, 이 값은 컬럼이 아니라 `trades.extra["exchange_rate"]`(숫자)와 `extra["exchange_rate_invalid"]`에 저장되고 `extra`의 다른 키는 유지된다. 빈 문자열 `""`처럼 blank를 넘기면 `exchange_rate`를 nil(과 invalid false)로 덮는다. 숫자로 바꿀 수 없거나 유한하지 않으면 invalid로 표시되어 검증이 실패하고, 0 이하여도 검증이 실패한다(`trade.rb:36-52`, `:185-195`). 라벨은 13개 값(`Transaction::ACTIVITY_LABELS` 사본: Buy, Sell, Sweep In, Sweep Out, Dividend, Reinvestment, Interest, Fee, Transfer, Contribution, Withdrawal, Exchange, Other) 중 하나여야 하고 아니면 저장 검증이 실패한다. | 코드 확인 |
| R-53 | `Entry` 속성 | `date`, `amount`, `currency`, `name`을 항상 덮어쓴다. `amount`는 수수료를 포함한 현금 영향 총액이다(Kraken: 매수는 +비용, 매도는 −비용이고 수수료가 얹힌다). | 코드 확인 |
| R-54 | 기존 `Trade` entry를 다시 import한다 | 보호 검사(R-09)와 속성 잠금이 없다. 사용자가 고친 값도 덮어쓴다. `excluded`·`user_modified`·`import_locked`를 보지 않고, 중복 claim도 보류 대조도 없다. | 코드 확인 (범위는 2.1) |
| R-55 | `Trade`의 부호 규약 | 수량은 매수 양수, 매도 음수. `Trade#buy?`는 `qty` 양수. 같은 `activity_label`이 `Transfer`·`Sweep In`·`Sweep Out`이면 `internal_movement?`로 판정되어 매도가 아니라 계정 간 이동으로 취급된다(비용 기준 계산 때). | 코드 확인 |

**가맹점·잔액·accountable**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-56 | `find_or_create_merchant` | `provider_merchant_id`와 `name`이 둘 다 있어야 하고 아니면 nil. `(provider_merchant_id, source)`로 먼저 찾고, 없으면 `(source, name)`으로 찾는다. 찾았고 `logo_url`을 받았는데 저장된 값과 다르면 로고를 바꾼다(실패해도 import는 계속, 경고). 못 찾으면 새 provider 가맹점을 만들고, 동시 생성 충돌(unique)이면 다시 찾아 쓴다. `website_url`은 새로 만들 때만 쓴다. 가맹점 식별자는 정규화한 이름에서 파생한 안정 값이어야 한다(SimpleFIN은 `"simplefin_" + md5(소문자 이름)`). | 코드 확인 |
| R-57 | provider 가맹점 저장 제약 | `source`는 필수이고 닫힌 목록(18개)이다. `(source, name)`이 unique이다. `color`는 항상 nil(지원 안 함). 웹사이트 URL은 있고 로고 URL이 비어 있으면 저장 전에 웹사이트로 로고 URL을 생성한다(Brandfetch 설정이 있을 때, `before_save`). 사용자 가맹점(`FamilyMerchant`)과는 별개의 종류다. | 코드 확인 |
| R-58 | `update_balance(balance:, cash_balance: nil, source: nil)` | 계정의 `balance`를 `balance`로, `cash_balance`를 `cash_balance` 또는(nil이면) `balance`로 저장한다. `Valuation` entry를 만들지 않고 통화도 바꾸지 않는다. `source`는 쓰이지 않는다. 투자·암호화폐 계정이 보유 평가액과 현금을 나눠 알면 `cash_balance`를 따로 줘야 한다(Kraken은 직접 `account.update!(balance:, cash_balance: 0, currency:)`를 쓴다). | 코드 확인 |
| R-59 | `update_accountable_attributes` | accountable(예: CreditCard, Loan)이 없거나 `attributes`가 비어 있으면 false. nil 값은 제외하고, accountable이 쓰기 가능한 속성 이름만 골라 한 번에 갱신하고 true를 반환한다. 쓸 수 있는 키가 하나도 없으면 false. 어떤 오류든 로그만 남기고 false를 반환한다(예외를 던지지 않는다). | 코드 확인 |
| R-74 | 외부에서 거래가 취소·삭제되거나 보유종목이 사라진다 | 어댑터에는 entry나 holding을 지우는 메서드가 없다. 지우는 일은 각 processor가 어댑터 밖에서 직접 한다(Plaid는 `(source, external_id)` 또는 옛 `plaid_id`로 entry를 찾아 `destroy_all`). 어댑터 안에서 지우는 것은 `import_holding`의 `delete_future_holdings`뿐이며(R-49), 이는 같은 종목의 더 늦은 날짜 행만 지우고 `can_delete_holdings?`가 기본 false라 provider가 켜야 한다. 그러므로 보고에서 사라진 종목의 과거 행과 취소된 거래는 어댑터만으로는 정리되지 않는다. 보호된 entry를 지울지도 processor가 정한다(예: Monobank 보류 정리는 `protected_from_sync?`면 지우지 않고 보류 표시만 뺀다). | 코드 확인 (검색 범위는 2.1) |

**계정과 provider 계정의 연결**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | `AccountProvider` 저장 | `provider`는 provider 쪽 계정 레코드(polymorphic: 클래스명과 id를 `provider_type`·`provider_id`에 저장). `(account_id, provider_type)`와 `(provider_type, provider_id)`가 각각 유일해야 한다(모델 검증과 DB unique index). 한 provider 계정은 Sure 계정 하나에만, Sure 계정 하나는 같은 provider 종류에 하나만 연결된다. 서로 다른 종류(예: Plaid와 Kraken)는 한 계정에 함께 연결될 수 있다. 연결을 삭제하면 그 연결을 가리키던 `Holding`의 `account_provider_id`는 null이 된다(`has_many :holdings, dependent: :nullify`, holding 행은 남는다). | 코드 확인 |
| R-61 | `Account#linked?` | `account_providers`가 하나라도 있거나, 옛 FK 컬럼 `plaid_account_id`·`simplefin_account_id`가 있으면 참. `unlinked?`/`manual?`는 그 부정. `linked` 스코프는 같은 조건의 SQL 판정이다. `provider`(대표 adapter)는 연결이 여러 개일 때 `account_providers.first`이므로 어느 것인지 정해져 있지 않다(정렬 없음). `provider_for(type)`와 `provider_account_for(type)`는 종류로 찾는다. | 코드 확인 / 추론(`first`가 정렬 없이 기본 키 순서인 점은 Rails 동작 가정) |
| R-62 | 연결에서 provider adapter를 얻는다 | `AccountProvider#adapter`는 `Provider::Factory.create_adapter(provider, account:)`를 호출한다. `provider`(provider 계정 레코드)가 nil이면 nil을 돌려주고, 아니면 클래스 이름으로 레지스트리를 찾고, 없으면 `app/models/provider/*_adapter.rb`를 모두 불러온 뒤 다시 찾아 그래도 없으면 nil이 아니라 `AdapterNotFoundError`를 던진다. 등록(`Provider::Factory.register`)을 빠뜨린 provider는 이 호출을 하는 모든 경로가 예외로 끝난다(R-63). `AccountProvider#provider_name`은 adapter 값을 쓰며, `provider_type`을 snake_case로 바꾼 값은 adapter가 nil일 때(`provider` 레코드가 없을 때)만 쓰인다. | 코드 확인 |
| R-63 | `Account#can_delete_holdings?` | 연결이 없으면 참. 있으면 연결된 모든 provider adapter가 `can_delete_holdings?`가 참일 때만 참(하나라도 거짓이면 거짓). R-49가 쓴다. adapter를 얻는 `Account#providers`(= 모든 연결의 `adapter` 목록, nil 제외), `Account#provider`(첫 연결의 adapter), `Account#provider_name`, `Account#provider_for(type)`은 R-62의 등록이 없으면 예외를 던진다. 따라서 `Provider::Factory.register`를 빠뜨리면 연결된 계정에서 `delete_future_holdings: true`인 `import_holding`이 `can_delete_holdings?`에서 예외로 끝난다. | 코드 확인 |
| R-64 | FinanceKit 전용 배타 규칙 | `AccountProvider` 저장 때 계정 행을 잠그고 검사한다: 계정에 `FinancekitAccountLineage` 연결이 있으면 다른 연결을 추가할 수 없고, `FinancekitAccountLineage`를 추가하려면 다른 연결이 없어야 하며 그 provider의 `family_id`가 계정의 `family_id`와 같아야 한다. 일반 provider에는 없는 규칙이다. | 코드 확인 |
| R-65 | 연결 해제 (`AccountsController#unlink`, 연결된 계정만) | 한 DB transaction 안에서: (1) FinanceKit 연결이 있으면 `disconnect!`. (2) 이 계정의 연결에 속한 `Holding`의 `account_provider_id`를 null로 만든다(holding은 유지). (3) 모든 `AccountProvider`를 삭제한다. SnapTrade provider 계정은 남겨 재연결에 쓴다. (4) 옛 FK 두 개를 null로. (5) 옛 SimpleFIN 연결이었으면 `SimplefinAccount`를 삭제한다. entries·잔액·holdings는 지우지 않고, 계정은 수동 계정이 된다. entry의 `external_id`·`source`·보호 플래그도 그대로다. 오류가 나면 전체를 되돌린다. 연결이 하나도 없으면 시작 전에 거부된다. | 코드 확인 |
| R-66 | 해제 뒤 다른 provider로 다시 연결해 import한다 | 옛 provider가 만든 entry는 `external_id`가 있어 `find_duplicate_transaction` 기본값(`external_id` 없음만 후보)의 후보가 아니다. 새 provider의 `(source, external_id)`와도 다르다. 그래서 같은 거래가 중복 entry로 생길 수 있다. 같은 provider로 다시 연결하면 `(source, external_id)`가 같아 기존 entry가 갱신된다. | 추론 (R-06·R-15의 조건에서 도출) |
| R-67 | 연결 삭제 시 provider별 후처리 | 일반 규칙이 아니다. `CoinstatsAccount` 연결을 지우면 그 provider 계정도 삭제한다. `OnchainWalletAccount` 연결을 지우면 provider 계정도 삭제한다(단 provider 계정 쪽의 연쇄 삭제로 시작된 경우는 제외). Sharesight·FinanceKit은 `retain`(기본, 데이터 유지)·`discard`(import한 데이터 삭제, 구현한 provider만 선언) 두 해제 방식을 쓴다(`ProviderDisconnectable`). | 코드 확인 |
| R-68 | 연결 만들기 | 모델 일반 규칙은 R-60과 R-64뿐이다. "수동 계정만 연결", "이미 연결된 provider 계정 거부", 대상 계정 종류 확인은 provider별 컨트롤러가 건다(Kraken: 수동 암호화폐 거래소 계정만, 이미 연결된 provider 계정은 거부, 연결 후 sync 예약). provider 계정 모델은 `has_one :account_provider`와 이를 통한 `account`(`current_account`)를 제공하고, import 때 `current_account`가 없으면 processor는 보통 아무것도 하지 않고 돌아간다. | 코드 확인 |
| R-72 | `Account::Linkable`의 나머지 연산 | `providers`는 모든 연결의 adapter 목록(nil 제외, 인스턴스에 기억), `provider_for(type)`는 `provider_type`이 같은 연결의 adapter, `provider_account_for(type)`은 그 연결의 provider 계정 레코드(예: `EnableBankingAccount`)다. `provider_name`은 대표 adapter의 이름이고, adapter가 없으면 옛 연결을 보아 `plaid_account`가 있으면 `"plaid"`, `simplefin_account`가 있으면 `"simplefin"`, 그 밖에는 nil이다. `linked_to?(type)`는 그 종류 연결이 있는지다. `supports_category_matcher?`는 `plaid_account`가 있으면 참, 아니면 연결 중에 `PlaidAccount`, `UpAccount`, `MonobankAccount`, `RedbarkAccount`(`CATEGORY_MATCHER_PROVIDER_TYPES`)가 있으면 참이다. 이 목록은 provider가 거래에 category matcher를 적용하고 계정의 `enable_category_matcher` 설정을 존중한다고 선언하는 opt-in이다. 코드 주석은 설정을 실제로 확인하는 provider만 목록에 넣으라고 한다(아니면 사용자가 아무 일도 하지 않는 스위치를 본다). 새 provider가 category matcher를 쓰려면 이 목록에 등록하고 processor가 `account.enable_category_matcher?`를 확인해야 한다. | 코드 확인 |
| R-73 | provider 계정 쪽의 연결 보조 `ensure_account_provider!` | 규약이 아니라 Kraken의 관례다. `KrakenAccount#ensure_account_provider!(target_account = nil)`는 대상 계정(없으면 `current_account`)이 있을 때 `AccountProvider.find_or_initialize_by(provider_type: "KrakenAccount", provider_id: id)`로 찾거나 만들어 계정을 지정하고 저장한다. 계정이 없으면 nil을 돌려준다. 저장 중 어떤 오류든(유일 제약, FinanceKit 검증 포함) 경고 로그만 남기고 nil을 돌려주므로 호출자는 연결 실패를 예외로 받지 못한다. | 코드 확인(Kraken) |

**출처 기록**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-69 | 출처가 저장되는 곳 | (a) `entries.source`와 `entries.external_id`: entry 단위. `source`는 자유 문자열(enum 아님)이다. (b) `data_enrichments`: 어댑터가 `name`·`category_id`·`merchant_id`·`notes`를 바꿀 때 `(대상, source, 속성명)` 단위로 값과 `metadata`. 분류 규칙(`rule`), AI, Bayes도 같은 표에 자기 `source`로 기록한다. (c) `transactions.extra`의 provider 네임스페이스: provider 원본 필드와 보류 표시. (d) `merchants.source`(provider 가맹점). (e) `holdings.account_provider_id`(어느 연결이 보고한 행인지)와 `holdings.external_id`. holdings에는 `source` 컬럼이 없다. | 코드 확인 |
| R-70 | `Entry#statement_cleared?` | `external_id`나 `source`가 있으면 참이다. "은행이 인지한 거래"라는 파생 값이며 사용자가 설정할 수 없고 저장되지 않는다. 수동 entry가 R-17·R-16으로 claim되면 참이 된다. | 코드 확인 |
| R-71 | `Provenance::Citation` | provider import 경로와 무관하다. AI 어시스턴트가 평가액을 기록할 때(`record_valuation` 도구) 출처 문자열의 문법(`["estimated: "] 출처 [" (grade: A|B|C)"]`)을 검증하는 값 객체다. 어댑터의 출처 기록(R-69)과 연결되어 있지 않다. | 코드 확인 (범위는 2.1) |

- 불변식:
  - 한 계정에서 `(source, external_id)`가 모두 있는 entry는 하나뿐이다(R-06).
  - 어댑터는 `Transaction`의 `kind`를 R-39 조건에서만 바꾸고, `locked_attributes`·`user_modified`·`import_locked`·`excluded` 플래그는 어떤 경로에서도 바꾸지 않는다(R-16의 `external_id`/`source` 기록은 플래그 변경이 아니다). 사용자 보호 플래그를 켜고 끄는 쪽은 컨트롤러와 import이다.
  - 보호 상태 entry의 `amount`·`name`·카테고리 등은 `import_transaction`으로 바뀌지 않는다(R-09, R-16). 단 보류 claim(R-22)과 예정 거래 claim(R-14)은 보호 상태 검사를 거치지 않는 경로라 예외이고, `import_trade`·`import_holding`에는 이 보호가 없다(R-54).
  - 같은 입력을 같은 상태에 두 번 넣어도 결과는 같다(멱등). 단 R-21의 `auto_claimed_pending_ids`는 한 번 늘면 줄지 않고, R-25의 제안은 처음 하나만 남는다.
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| — | — | (해소) 이전 U-01(새 연동의 "현재 잔액" 정본 경로)은 [account-balances](./account-balances.md) R-22·R-23·R-27에서 닫혔다(2026-11-18). 정본은 `Account#set_current_balance`이고 `update_balance`는 캐시만 쓰는 옛 경로다. 원본은 새 연동에 강제하지 않는다. | — | — |

- 확인 한계:
  - `ActiveModel::Type::Boolean`의 거짓 값 목록(R-08)은 Rails 프레임워크 상수라서 `repos/sure`에 없다. 목록 자체는 일반 지식 기준이고, 레포 주석이 확인해 주는 것은 `"no"`·`"False"`·`"Off"`가 참으로 읽힌다는 점뿐이다. 이 SHA의 Rails 버전에서 목록이 정확히 같은지 gem 소스로 확인하지 못했다. 새 구현은 JSON `true`/`false`만 쓰는 것이 안전하다.
  - R-14의 예정 거래 판정 `entries.created_at < entries.date`는 timestamp와 date를 비교한다. PostgreSQL이 date를 자정 timestamp로 바꿔 비교한다고 보고 썼고(추론) 시간대 경계 사례는 실행해 보지 않았다.
  - `Account.transaction do ... return entry ... end`처럼 transaction 블록 안에서 `return`으로 빠져나가는 경로(R-09의 보호 skip, R-16)가 쓰기를 commit하는지는 Rails 버전의 동작에 달려 있다. 원본은 R-10·R-11·R-16의 쓰기가 남는다는 의도로 쓰여 있고(주석), 그 전제로 이 스펙을 썼다. 실행해서 확인하지 않았다.
  - 어떤 provider processor도 이 스펙 범위에서 끝까지 읽지 않았다. 아래 R-ID는 어댑터 자체와 호출 규약 예시(SimpleFIN·Plaid·Kraken)만 근거로 한다.
  - 테스트는 열지 않았다. 닫힌 enum이 실제로 오류를 내는지(R-34)는 테스트로 보지 못했다.

- 구현자가 자주 막히는 질문과 답이 있는 곳:

| 질문 | 답 |
|---|---|
| 새 연동의 보류(승인 대기) 거래를 보류로 인식시키려면? | 원본은 고정 목록(`PENDING_PROVIDERS`)에 네임스페이스를 넣어야 한다. 목록 밖 이름의 `pending: true`는 인식되지 않는다(R-30). 값은 JSON boolean으로 쓴다(R-08). |
| `external_id`는 어떻게 만드나? 은행 CSV에는 거래 ID가 없다. | 어댑터는 값의 규칙을 정하지 않고 `(account, source)` 안에서 유일하고 같은 거래에 같은 값이면 된다(R-06). 원본에 ID 생성 장치는 어댑터에 없다. 결정적 값을 직접 만들어야 한다(적용 메모 B). |
| 금액 부호는? | 양수가 지출, 음수가 수입이다(1.3 `amount`). 생성기의 활동 템플릿은 반대로 쓰여 있어 주의해야 한다(적용 메모 B). |
| `amount`·`quantity`에 문자열이나 Float를 넘겨도 되나? | 날짜 문자열과 `find_*`의 금액은 받지만 `import_trade`의 수량은 숫자 타입이어야 한다. 안전한 입력은 십진수 타입이다(1.3 입력 타입 계약). |
| 한글 거래명은 중복·보류 제안과 투자 라벨 추정에서 어떻게 되나? | 이름 비교 키가 비어 가맹점 일치만 남고(R-26, R-27), 라벨 추정은 항상 nil이다(R-38). 라벨은 호출자가 직접 넘긴다. |
| 취소된 거래나 보고에서 사라진 보유종목은 어떻게 지우나? | 어댑터에는 지우는 API가 없다. processor가 직접 지우고, `delete_future_holdings`는 같은 종목의 더 늦은 날짜 행만 지운다(R-49, R-74). |
| 새 `source` 이름을 쓰면 무엇을 갱신해야 하나? | 원본에서는 `DataEnrichment`(25개)와 `ProviderMerchant`(18개)의 닫힌 목록과 보류 네임스페이스 목록이다(R-34, R-57, R-30). 목록 밖이면 이름이 바뀌는 시점에 오류가 날 수 있다. |
| 계정의 현재 잔액은 어떻게 넣나? | `update_balance`는 캐시 필드만 쓴다. balance 재구성의 정본 입력은 이 스펙이 정하지 못했다(U-01). |

### 1.5 필수 코드 참조

라이선스는 AGPL-3.0이다(overview 1절). 아래 코드를 그대로 가져오면 AGPL 고지·소스 공개 의무가 따른다. 동작을 다른 언어로 새로 쓰는 경우에는 규칙만 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/account/provider_import_adapter.rb:39-364` `import_transaction` | 분기 순서의 기준. 글(R-06~R-42)이 요약이고, 둘이 다르면 이 코드가 기준이다. 순서: 키 조회 → 유형 충돌 → 보호 skip → heuristic claim → 보류 대조 → 같은 id 확정 → 날짜 → 금액 잠금 → enrich → extra → kind → 저장 → goal → 제안. | R-06~R-42 |
| C-02 | `app/models/account/provider_import_adapter.rb:797-841` `find_duplicate_transaction` | 중복 후보 조건과 정렬. | R-15 |
| C-03 | `app/models/account/provider_import_adapter.rb:851-860` `find_scheduled_transaction` | 예정 거래 후보 조건(`created_at < date`). | R-14 |
| C-04 | `app/models/account/provider_import_adapter.rb:871-893` `find_pending_transaction` | 정확 금액 보류 후보. | R-20 |
| C-05 | `app/models/account/provider_import_adapter.rb:910-963` `find_pending_transaction_fuzzy` | 금액 허용 범위 계산, 가맹점·이름 키 비교, 후보 1개 규칙. | R-26 |
| C-06 | `app/models/account/provider_import_adapter.rb:977-1014` `find_pending_transaction_low_confidence` | 낮은 확신 범위와 이중 일치 조건. | R-27 |
| C-07 | `app/models/account/provider_import_adapter.rb:1024-1049` `store_duplicate_suggestion` | 제안 기록 형식과 생략 조건. | R-28 |
| C-08 | `app/models/account/provider_import_adapter.rb:1058-1079` `detect_activity_label` | 이름 → 투자 활동 라벨 정규식 표. | R-38 |
| C-09 | `app/models/account/provider_import_adapter.rb:1175-1184` `apply_provider_extra` | `extra` 병합과 교체. | R-35, R-36 |
| C-10 | `app/models/account/provider_import_adapter.rb:1200-1214` `keep_name_sources` | 보호된 entry에서 이름 재료 키 유지. | R-11 |
| C-11 | `app/models/account/provider_import_adapter.rb:1222-1232` `clear_pending_flags_from_extra` | 보류 표시 제거와 빈 네임스페이스 제거. | R-10, R-21, R-23 |
| C-12 | `app/models/account/provider_import_adapter.rb:441-681` `import_holding` | holding 조회 순서, 충돌 복구, 삭제 조건. 글(R-43~R-50)이 요약. | R-43~R-50 |
| C-13 | `app/models/account/provider_import_adapter.rb:1121-1138` `previous_holding_for` | 직전 날짜 행 선택 순서. | R-46 |
| C-14 | `app/models/holding/cost_basis_reconciler.rb:16-66` `reconcile` 와 `app/models/holding.rb:7-14`, `app/models/holding.rb:225-245` | 평단가 우선순위와 교체 가능 조건(마지막 "기존 값 유지" fallback 포함, 우선순위 비교 `new_priority >= cost_basis_source_priority` 포함). | R-48 |
| C-15 | `app/models/account/provider_import_adapter.rb:698-753` `import_trade` | 매매 upsert 전체(짧아서 코드가 정본). | R-51~R-54 |
| C-16 | `app/models/account/provider_import_adapter.rb:374-413` `find_or_create_merchant` | 가맹점 조회·생성·충돌 처리. | R-56 |
| C-17 | `app/models/transaction.rb:71-78`, `app/models/transaction.rb:107-117` | `kind` 6개 값, 활동 라벨 13개, 내부 이동 라벨 4개, `PENDING_PROVIDERS` 10개. | R-30, R-38, R-39 |
| C-18 | `app/models/transaction.rb:133-169`, `app/models/transaction.rb:196-205` | 보류 판정(Ruby·SQL)과 거짓 값 처리. | R-08, R-30 |
| C-19 | `app/models/concerns/enrichable.rb:54-169`, `app/models/concerns/enrichable.rb:234-244` `log_enrichment` | 속성 단위 갱신, 잠금, 출처 기록의 알고리즘과 `data_enrichments` 쓰기(`(대상, source, 속성)` 한 행의 `value`·`metadata` 갱신). | R-31~R-34 |
| C-20 | `app/models/entry.rb:480-482`, `app/models/entry.rb:512-526`, `app/models/entry.rb:554-559` | 보호 정의, 사용자 수정 표시, 보호 해제. | R-09 |
| C-21 | `app/models/account/linkable.rb:25-34`, `app/models/account/linkable.rb:89-96` | `linked?` 정의와 `can_delete_holdings?`. | R-61, R-63 |
| C-22 | `app/models/account_provider.rb:5-75` | 연결 유일 검증, FinanceKit 규칙, `holdings` nullify, CoinStats·onchain 연결 삭제 후처리(`destroy_coinstats_provider_account`, `destroyed_by_association` 가드). | R-60, R-64, R-67 |
| C-23 | `app/controllers/accounts_controller.rb:319-357` `unlink` | 연결 해제 절차. | R-65 |
| C-24 | `db/schema.rb:24-32`, `db/schema.rb:597-608`, `db/schema.rb:709-751`, `db/schema.rb:1213-1236`, `db/schema.rb:1691-1707`, `db/schema.rb:2840-2854`, `db/schema.rb:2893-2913` | 1.3 저장 제약 표의 원본(account_providers, data_enrichments, entries, holdings, merchants, trades, transactions). | R-06, R-47, R-60 |
| C-25 | `app/models/transfer.rb:31-47`, `app/models/transfer.rb:112-117` | R-40(b)에서 transfer가 `kind`를 정하는 규칙. 이체 매칭 스펙 소관이라 이 부분만 가져온다. | R-40 |
| C-26 | `app/models/data_enrichment.rb:5-31`, `app/models/provider_merchant.rb:3-10` | `source` 닫힌 목록과 provider 가맹점 검증. | R-34, R-57 |
| C-27 | `app/models/trade.rb:11`, `app/models/trade.rb:33-35`, `app/models/trade.rb:73-77` | Trade 라벨 검증, 필수 필드, 기본 이름. | R-51, R-52 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 금액은 지출이 양수다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06, R-31~R-33 | 계정에 entry 없음. `import_transaction(external_id: "tx1", source: "simplefin", amount: 12.5, currency: "KRW", date: 2026-11-10, name: "카페")`. | 새 entry가 생긴다: `(source "simplefin", external_id "tx1")`, `kind "standard"`, `extra {}`. `data_enrichments` 행은 생기지 않는다(새 record의 첫 저장). |
| T-02 | R-06, R-31, R-34 | T-01 후 같은 키로 `amount: 13.0`, `name: "카페 B"`. | 같은 entry가 갱신된다(새 entry 없음). `amount` 13.0, `name` "카페 B". `data_enrichments`에 `(entry, "simplefin", "name")` 행이 만들어진다(`simplefin`은 `DataEnrichment.source` 목록 안). |
| T-02b | R-34 | T-02에서 `source`를 목록 밖 값(`"bankx"`)으로 바꿔, 이미 저장된 entry의 `name`을 바꾸는 import. | 이름이 바뀌는 순간 `data_enrichments` 기록에서 오류가 날 가능성이 크다(Rails enum 동작 가정, 추론). 새 entry의 첫 저장이나 이름이 바뀌지 않는 재import는 영향이 없다. 이 사례는 확정이 아니다. |
| T-03 | R-06 | `(bankx, tx1)` entry가 있다. 다른 provider `(cardx, tx1)`로 같은 날짜·금액을 import. | 두 번째 호출이 새 entry를 만든다. 계정에 entry가 둘이다. |
| T-04 | R-07 | `(bankx, t9)`이 `Trade` entry로 존재. `import_transaction(external_id: "t9", source: "bankx", ...)`. | `ArgumentError`. 어떤 쓰기도 남지 않는다. |
| T-05 | R-09, R-05 | `(bankx, tx1)` entry의 `user_modified`가 true, `name`이 "내가 바꾼 이름". 같은 키로 `name: "카페"`, `amount: 99`. | entry는 변하지 않는다(`name`·`amount` 그대로). `skipped_entries`에 `reason: "user_modified"` 한 건. |
| T-06 | R-10 | `(simplefin, tx1)`: `user_modified` true, 저장된 `extra {"simplefin": {"pending": true}}`. 같은 키로 `extra: {"simplefin": {"pending": false}}`, `replace_extra_namespaces` 기본값. | 저장된 `extra`에서 `simplefin`의 `pending`이 제거되고 네임스페이스가 비어 사라진다(`{}`). 이름·금액은 그대로. R-11은 교체 대상이 없어 아무 효과가 없다. |
| T-07 | R-12, R-16 | CSV import가 만든 entry: `external_id` 없음, `import_locked` true, 금액 12.5, 날짜 2026-11-10, `created_at`은 날짜 이후(과거 거래를 가져온 보통의 경우. `created_at < date`이면 R-14가 먼저 claim해 날짜까지 덮이므로 결과가 달라진다). 어댑터로 같은 금액·날짜·통화의 새 거래 `(bankx, tx2)`를 import. | CSV entry에 `external_id "tx2"`, `source "bankx"`만 기록된다. 다른 필드는 그대로. `skipped_entries`에 `reason "import_locked"`. 새 entry는 생기지 않는다. 다음 sync에서 `(bankx, tx2)`가 R-09로 바로 걸린다. |
| T-08 | R-14 | 사용자가 11-05에 만든 예정 거래(날짜 11-10, 금액 100, `external_id` 없음, `created_at` 11-05, `user_modified`). provider가 `(simplefin, b1)` 금액 100, 날짜 11-12를 보낸다. | 그 entry가 claim된다: `external_id "b1"`, 날짜 11-12(차이 2일 ≤ 7). 사용자가 잠근 이름·카테고리는 유지. |
| T-09 | R-15, R-17 | `external_id` 없는 일반 entry(`user_modified` false, 금액 30, 날짜 11-10, `created_at`은 11-10 이후라서 예정 거래가 아님). provider가 `(simplefin, c1)` 금액 30, 날짜 11-10. | 그 entry가 claim되어(`external_id "c1"`) 일반 갱신 경로로 갱신된다. 새 entry 없음. `created_at`이 11-10보다 이르면 R-14가 먼저 claim하고 날짜는 provider 날짜가 된다. |
| T-10 | R-20~R-24 | 보류 entry `(simplefin, p1)`: 금액 30, 날짜 11-10, `extra {"simplefin": {"pending": true}}`. 이제 `import_transaction`으로 `(simplefin, b1)`, 금액 30, 날짜 11-12, `extra {"simplefin": {"pending": false}}`를 넣는다. | 새 entry 없이 `p1` entry가 `external_id "b1"`로 바뀐다. 날짜는 11-10 유지(R-24). `extra`는 `{"simplefin": {"pending": false}, "auto_claimed_pending_ids": ["p1"]}`. |
| T-11 | R-19 | `(plaid, p1)` 금액 20(보류). `(plaid, b1)` 금액 25, `pending_transaction_id: "p1"`, 확정. | 금액 일치 여부와 무관하게 `p1` entry가 claim되고 금액은 25로 바뀐다(R-31). `auto_claimed_pending_ids ["p1"]`. |
| T-12 | R-25, R-26, R-28 | `(simplefin, p2)` 보류, 금액 20, 날짜 11-10, 가맹점 M. 새 확정 `(simplefin, b2)`, 금액 25, 날짜 11-11, 가맹점 M. | 금액 20은 `[25/1.3 ≈ 19.2, 25]` 안이고 후보가 1개라 claim이 아니라 제안: `b2`는 새 entry로 생기고 `p2`의 `extra["potential_posted_match"]`가 `{entry_id: b2의 id, reason: "fuzzy_amount_match", confidence: "medium", ...}`. 자동 병합 없음. |
| T-12b | R-26 | T-12와 같은데 가맹점 없이 이름이 "스타벅스 강남". | 한글 이름은 비교 키가 빈 문자열이라 이름 비교가 꺼진다. 가맹점도 없으므로 제안이 생기지 않는다. |
| T-13 | R-36 | 저장된 `extra {"plaid": {"payment_meta": {"payee": "A"}, "pending": true}}`. 같은 키(`user_modified` 아님)로 `extra {"plaid": {"pending": false}}`. `replace_extra_namespaces: ["plaid"]`와 `[]` 두 경우. | `["plaid"]`이면 `{"plaid": {"pending": false}}`(`payee` 사라짐). `[]`이면 deep merge라 `{"plaid": {"payment_meta": {"payee": "A"}, "pending": false}}`. |
| T-14 | R-31 | 저장된 entry의 `locked_attributes`에 `amount`만 있다(`user_modified` false). 같은 키로 금액·통화를 바꿔 import. | 금액·통화 둘 다 바뀌지 않는다. 날짜는 바뀐다. |
| T-15 | R-38~R-40 | `Investment` 계정. `name "Employer Match 2026"`, 라벨 미지정. | 라벨 `Contribution`, `kind investment_contribution`, 카테고리가 비어 있으면 가족의 "Investment Contributions" 카테고리. |
| T-16 | R-39 | `Loan` 계정, 금액 −500(상환 입금), `kind` 미지정. | `kind loan_payment`. |
| T-17 | R-43, R-47 | 계정에 `external_id "h1"` 행이 있다. 같은 `external_id`로 수량·평가액을 바꿔 `import_holding`. | 행이 하나인 채로 수량·평가액·가격이 바뀐다. |
| T-18 | R-45 | 연결 A가 `(종목 S, 날짜 D, 통화 C)` 행을 만들었다. 연결 B가 `external_id`를 줘서 같은 `(S, D, C)`를 import. | 새 행도, 갱신도 없다. A의 행이 그대로 반환된다. |
| T-19 | R-46, R-48 | 사용자가 어제 행의 종목을 T로 바꾸고 잠갔다(`provider_security` S). 오늘 provider가 종목 S로 import. | 오늘 새 행의 종목이 T, `provider_security`가 S, 종목 잠금 true. |
| T-20 | R-49 | `delete_future_holdings: true`, 연결된 provider 둘 중 하나의 `can_delete_holdings?`가 false. | 삭제가 일어나지 않고 저장된 행이 반환된다. |
| T-21 | R-51, R-54 | `external_id` 없이 같은 매매를 두 번 `import_trade`. | entry 두 개. `external_id "x1"`로 두 번 호출하면 한 개이고, 두 번째 호출이 사용자가 바꾼 이름·금액을 덮어쓴다. |
| T-22 | R-65 | 계정에 Kraken 연결과 holdings가 있다. `unlink`. | `AccountProvider` 삭제, holdings는 남고 `account_provider_id`가 null. 계정은 `linked?` 거짓이고 entries는 그대로. |
| T-23 | R-39 | `Loan` 계정에 `kind: "funds_movement"`를 준 거래 두 건: 금액 +500과 −500. | +500은 `funds_movement`(`Loan` 분기는 음수만), −500은 `loan_payment`(provider 힌트보다 `Loan` 분기가 이긴다). |
| T-24 | R-39 | 이미 저장된 거래(`user_modified` 아님, `kind`가 API로 바뀌어 잠김)를 `kind: "standard"`로 다시 import. | `kind`가 `standard`로 덮인다(잠금을 확인하지 않는다). |
| T-25 | R-38 | `Investment` 계정에 이름 "배당금", 라벨 미지정. 같은 이름으로 `investment_activity_label: "Dividend"`를 준 경우. | 라벨 미지정이면 라벨 nil, `kind` 불변(한글 이름은 추정되지 않음). 라벨을 주면 `Dividend`가 저장된다. |
| T-26 | R-40 | `Investment` 계정에 이름 "Employer Match"를 import. 가족에 서로 다른 locale 이름의 "Investment Contributions" 카테고리 두 개가 있고 각각 거래가 달려 있다. | 카테고리가 하나로 합쳐진다(첫 번째가 남고 거래·하위 카테고리·예산 카테고리가 옮겨지고 나머지는 삭제, 이름은 가족 locale 이름). 새 거래의 `category_id`가 비어 있었으므로 그 카테고리가 붙는다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

경로는 `repos/sure` 기준, SHA는 frontmatter와 같다(`1cd94e6`). 줄 번호는 C-ID와 같은 범위를 쓴다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `:39-47`, `simplefin_account/transactions/processor.rb:26-47`, `enable_banking_account/transactions/processor.rb:23`, `plaid_entry/processor.rb:44-47`, 어댑터 주석 `provider_import_adapter.rb:1141-1144`, `kraken_account/holdings_processor.rb:104` | 위 파일들을 읽었다. 거래 entry processor가 행마다 어댑터를 만드는지는 Plaid(생성자가 거래 한 건을 받음)에서 확인했고, 나머지(Akahu, Brex, Lunchflow, Mercury, Monobank, Fio)는 `grep -rn "@import_adapter ||=" app/models`로 같은 메모이즈 줄만 확인했다(추론). |
| R-02 | C-01 `:40-41`, `:53-55`, `:43`, `:332-333`, `simplefin_account/transactions/processor.rb:38-47` | `import_transaction` 전체를 읽어 rescue가 `store_duplicate_suggestion` 호출부(`RecordInvalid`)뿐임을 확인했다. 부재 주장은 아래 "부재·전칭 주장"의 6번. |
| R-03 | `provider_import_adapter.rb` 전체 | 아래 6번 |
| R-04 | `kraken_account/processor.rb:110-122`, `kraken_account/processor.rb:146`(`reconcile_with_ledger`의 `protected_from_sync?`) | Kraken processor를 읽었다. 직접 만든 trade가 `import_trade` 호출 없이 `entries.create!`로 가는 것을 코드로 확인. `import_trade` 호출 파일 11개에 Kraken이 없다(아래 7번). |
| R-05 | C-01 `:1086-1105`, `concerns/sync_stats/collector.rb:214-233`, `simplefin_account/transactions/processor.rb:48` | 통계 필드와 20건 상한을 읽었다. `reset_skipped_entries!` 외부 호출처 없음은 아래 4번. |
| R-06 | C-01 `:46-48`, C-24 `entries`(`:738`), `entry.rb:65` | 코드와 schema 확인. |
| R-07 | C-01 `:53-55` | 코드 확인. |
| R-08 | C-18, C-01 `:59`, `transaction.rb:130-134`, `transaction.rb:145-155` | 판정 구조는 코드로 확인. `"no"`·`"False"`·`"Off"`가 참으로 읽힌다는 것과 JSON `0.0`이 보류라는 것은 `transaction.rb:145-155`의 주석을 읽었다. 거짓 문자열의 정확한 집합(`FALSE_VALUES`)은 Rails 상수로 repo 밖이라 일반 지식 기준(확인 한계). `:133`은 그 집합의 문자열 원소에 빈 문자열을 더해 SQL용 목록을 만든다. |
| R-09 | C-01 `:61-108`, C-20 `entry.rb:480-482`, `:1086-1091` | 코드 확인. |
| R-10 | C-01 `:75-83`, C-11 | 코드 확인. 주석이 `user_modified`+`import_locked` 조합 사례를 설명한다(`:75-78`). |
| R-11 | C-01 `:84-103`, C-09, C-10, `docs/llm-guides/providers.md:155-165` | 코드 확인. 이름 재료 보존 이유는 문서와 코드 주석이 일치한다. |
| R-12 | C-01 `:95-107`, `transaction_import.rb:66-85`, `trade_import.rb:32`, `family/data_importer.rb:997-1003`, `monarch_import/converter.rb:129`(검색 결과), `qif_import.rb:315`(검색 결과), `pdf_import.rb:140`(검색 결과) | `grep -rn import_locked app lib --include=*.rb`로 설정 위치를 찾았다. `transaction_import.rb`, `trade_import.rb`, `family/data_importer.rb`는 해당 줄을 열어 읽었고 나머지는 검색 결과의 줄만 봤다. "수동 입력은 `user_modified`"는 `transactions_controller.rb:150-153`에서 확인. `excluded`와 `user_modified`가 함께 있으면 이유가 `excluded`가 되는 것은 `determine_skip_reason`(`:1086-1091`)의 순서에서 확인. |
| R-13 | C-01 `:110-140` | 코드 확인. |
| R-14 | C-03, C-01 `:118-126` | 코드 확인. 비교 `entries.created_at < entries.date`의 시간대는 PostgreSQL이 date를 자정 timestamp로 변환하는 동작에 의존(확인 한계). |
| R-15 | C-02, `transaction_import.rb:47-58`, `pdf_import.rb:449`(검색 결과) | 코드 확인. 소비처별 인자는 호출부에서 읽었다(CSV는 `name`·`exclude_entry_ids`). 명세서 import(`pdf_import.rb`)는 호출 줄만 확인. |
| R-16 | C-01 `:127-133` | 코드 확인. |
| R-17 | C-01 `:135-139` | 코드 확인. |
| R-18 | C-01 `:142-182` | 코드 확인. |
| R-19 | C-01 `:147-152`, `plaid_entry/processor.rb:28`, `docs/llm-guides/providers.md:167-172` | 코드 확인. |
| R-20 | C-04 | 코드 확인. `find_pending_transaction` 외부 호출은 Enable Banking 한 곳(`enable_banking_entry/processor.rb:395`). |
| R-21 | C-01 `:163-181`, `enable_banking_account/transactions/processor.rb:64-77`, `lunchflow_entry/processor.rb:261` | 코드 확인. 소비처는 아래 8번. |
| R-22 | C-01 `:61-182`(보호 검사는 `:64-108`에서만 일어나고 claim은 그 뒤) | 코드 확인. 부재 주장("claim 경로에 보호 검사 없음")의 범위는 아래 9번. |
| R-23 | C-01 `:184-194` | 코드 확인. 이 블록은 `entry.new_record?`와 무관하게 새 entry가 아닌 모든 경로(같은 키 조회, R-14·R-17·R-21의 claim)가 지나가며 `if !incoming_pending && entry.entryable.is_a?(Transaction)` 조건만 본다. R-09의 보호 skip은 이 블록 앞에서 `return`한다. |
| R-24 | C-01 `:196-212` | 코드 확인. |
| R-25 | C-01 `:309-360` | 코드 확인. |
| R-26 | C-05 | 코드 확인. ASCII 정규식은 `:946`, `:949`에서 확인. 한글이 지워진다는 결과는 정규식에서 도출(실행 안 함). |
| R-27 | C-06 | 코드 확인. |
| R-28 | C-07, `transaction.rb:500-600`(수동 병합), `entry.rb:329-346` | `store_duplicate_suggestion`은 코드 확인. 수동 병합의 `manual_merge` 기록 형식은 `transaction.rb:566-579`에서 읽었으나 UI 흐름은 이 스펙 범위 밖. |
| R-29 | `entry.rb:158-160`(`stale_pending`), `entry.rb:215-226`(`auto_exclude_stale_pending`), `entry.rb:235-357`(`reconcile_pending_duplicates`: 정확 일치 `:248-284`, 흐릿한 단계 `:286-350`), `simplefin_item/importer.rb:1450`, `:1501` | `grep -rn "auto_exclude_stale_pending\|reconcile_pending_duplicates" app lib`의 호출처가 SimpleFIN importer 두 줄뿐이었다. 동적 호출·rake 작업은 `--include=*.rake`로도 검색했으나 없었다. 두 제안 형식의 차이는 `entry.rb:331-345`(`dismissed => false` 포함)와 `provider_import_adapter.rb:1038-1048`(`dismissed` 없음)를 나란히 읽어 확인했다. |
| R-30 | C-17, C-18, `entry.rb:122-139`, `transaction.rb:213-225`, `docs/llm-guides/providers.md:38-50`, `:218` | 코드 확인. "목록에 없으면 인식 안 됨"은 `pending_sql`이 목록과의 교집합만 쓰는 코드(`:160`)에서 확인. 소득·지출 집계 제외는 `pending_providers_sql` 주석(`:213-225`)에서 읽었고 그 SQL 호출처를 열지는 않았다. |
| R-31 | C-01 `:214-223`, `entry.rb:62-65`, `:684-686` | 코드 확인. |
| R-32 | C-01 `:226`, `entry.rb:62`, `:81-84`, `simplefin_entry/processor.rb:120-135` | 코드 확인. 저장 실패 → 예외는 검증과 `save!`(`:293`)에서 도출. |
| R-33 | C-01 `:229-239` | 코드 확인. |
| R-34 | C-19, C-26, `db/schema.rb:597-608`, `docs/llm-guides/providers.md:38-50`, `lib/generators/provider/family/family_generator.rb:481-486` | 알고리즘과 목록은 코드 확인. 닫힌 enum이 오류를 낸다는 점은 Rails 동작 가정(추론). 실제 import에 쓰이는 `source` 중 `DataEnrichment` 목록에 없는 것은 `grep -rn "import_transaction(" -A14 app/models`로 모은 `source:` 값(coinspot, snaptrade, trading212, financekit)과 `data_enrichment.rb:5-31` 목록을 대조해 찾았다. 이름이 바뀌지 않으면 기록 단계가 실행되지 않으므로 평소에는 드러나지 않는다. `ProviderMerchant`는 `provider_merchant.rb:3`의 18개 목록과, `grep -rn "find_or_create_merchant(" -A6 app/models | grep source:`로 모은 호출부 `source:` 값을 대조했다(검색 결과에 `source: source`처럼 값을 알 수 없는 줄이 있어 그 호출부는 확인하지 못했다). 생성기가 두 enum에 새 provider 이름을 넣는다는 것은 `update_source_enums`가 두 파일에 대해 `update_source_enum`을 부르는 줄(`family_generator.rb:481-486`)에서 확인했고, 실제 파일을 고치는 `update_source_enum` 본문은 읽지 않았다. |
| R-35 | C-09 | 코드 확인. Ruby의 `deep_merge`·`deep_stringify_keys` 의미(배열 대체, `nil` 덮어씀)는 ActiveSupport 동작에서 도출. |
| R-36 | C-09, `plaid_entry/processor.rb:30-36`, `docs/llm-guides/providers.md:40-46` | 코드 확인. |
| R-37 | 검색 `grep -rhn` + 정규식(`extra["키"]`, `extra->'키'`, `extra -> '키'`, `extra&.dig("키"`, `extra ? '키'` 형태)을 `app lib --include=*.rb --include=*.rake -o`로 두 번 실행(두 번째는 `lib`·`.rake` 포함), `transaction.rb:33-52`, `transaction.rb:446-460`, `enable_banking_entry/processor.rb:48`, `enable_banking_account/transactions/processor.rb:87-91`, `demo/financekit_generator.rb:139-153`, `db/schema.rb:2905` | 키 목록은 검색 결과에서 provider 네임스페이스가 아닌 최상위 키를 모았다(`goal`, `potential_posted_match`, `exchange_rate`, `exchange_rate_invalid`, `manual_merge`, `auto_claimed_pending_ids`, `superseded_external_ids`, `security_id`/`security`, `demo_financekit_activity_version`). 첫 검색은 패턴이 좁아 `superseded_external_ids`를 놓쳤고 패턴을 넓힌 재검색으로 찾았다. 변수에 담은 키(예: Enable Banking의 `SUPERSEDED_IDS_KEY`)와 `extra.merge("..." => ...)`처럼 쓰기만 하는 접근은 패턴에 잡히지 않을 수 있다. 목록은 그 범위의 목록이다. |
| R-38 | C-08, C-01 `:244-248` | 코드 확인. |
| R-39 | C-01 `:250-267`, `provider_import_adapter.rb:282-286`, C-17 | 코드 확인. 코드와 주석이 다르다. `:248-256`의 주석은 provider가 `funds_movement`를 넘겨도 `Loan`/`CreditCard`에 연결된 상환은 `loan_payment`/`cc_payment`로 남는다고 쓰지만, 계정 종류 분기는 `:264`의 `account.accountable_type == "Loan" && entry.amount.negative?` 하나뿐이고 `CreditCard` 분기는 없다. 이 스펙은 구현(코드)을 사실로 쓴다. `kind` 대입(`:282-286`)이 `locked?(:kind)`를 보지 않는 것은 그 줄 범위를 읽어 확인했다(해당 줄에 `locked?` 호출 없음). 6개 enum 밖 값의 `ArgumentError`는 Rails enum 동작 가정(추론). |
| R-40 | C-01 `:259-291`, C-25, `family.rb:559-595`, `category.rb:113`, `category.rb:278-288`, `transfer.rb:109-117` | 코드 확인. `account.family.investment_contributions_category`는 `:261-263`의 `elsif detected_label == "Contribution"` 분기에서 카테고리 저장 조건(`:288`)과 무관하게 호출되는 것을 읽었다. 이름이 `I18n.t` 값인 것은 `category.rb:113`(키)와 `:278-288`(`investment_contributions_name`, `all_investment_contributions_names`)에서 확인. `Transfer#kind_for_leg`·`kind_for_account`를 읽었고 transfer 확정 절차 자체는 읽지 않았다(이체 매칭 스펙 범위). |
| R-41 | C-01 `:296-307`, `:1154-1160`, `goal_pledge/reconciler.rb:1-60` | 코드 확인. reconciler의 오류 흡수는 `:45-52`의 `rescue StandardError`에서 읽었다. |
| R-42 | `transaction.rb:30-31`, `entry.rb:87`, `:812-816` | callback 선언을 읽었다. 분류 기록 대체의 세부는 읽지 않았다. |
| R-43~R-44 | C-12 `:451-518` | 코드 확인. |
| R-45 | C-12 `:520-538` | 코드 확인. |
| R-46 | C-12 `:540-542`, C-13 `:1132-1137`(rank 3단계) | 코드 확인. |
| R-47 | C-12 `:551-559`, `:584`, `holding.rb:21-24`, `db/schema.rb:1213-1236` | 코드 확인. nil 덮어쓰기는 `assign_attributes`가 값 nil도 쓰는 것에서 도출. |
| R-48 | C-12 `:562-582`, C-14 | 코드 확인. |
| R-49 | C-12 `:654-677`, C-21, `provider/base.rb:78-83`, `provider/kraken_adapter.rb:45-47` | 코드 확인. "Plaid가 쓴다"는 `can_delete_holdings?`를 true로 구현한 provider가 있다는 주석(`:654`)에서 읽었고 Plaid adapter 파일은 열지 않았다. |
| R-50 | C-12 `:586-652`, `:441-443`, `db/schema.rb:1213-1236` | 코드 확인. `source` 미저장은 holdings 컬럼 목록과 `:441-681`에서 `source`가 검증 줄(`:443`)에만 나오는 것에서 확인. |
| R-51 | C-15 `:698-727`, C-27 | 코드 확인. 수량 문자열 표기(10 vs 10.0)는 ActiveSupport의 `BigDecimal#to_s`가 "F" 형식이라는 일반 지식에 의존해 판단을 보류했다. |
| R-52 | C-15 `:730-741`, C-27, `trade.rb:36-52`, `trade.rb:185-195`, `transaction.rb:107-110` | 코드 확인. `Trade#exchange_rate=`의 blank 처리, `Float()` 변환 실패 시 invalid 표시, 검증 메시지를 읽었다. |
| R-53 | C-15 `:743-748`, `kraken_account/processor.rb:100-115` | 코드 확인. |
| R-54 | C-15 | 부재 주장. 아래 5번. |
| R-55 | `trade.rb:11-27`, `:39-60` | 코드 확인. |
| R-56 | C-16, `simplefin_entry/processor.rb:158-190`, `db/schema.rb:1691-1707` | 코드 확인. |
| R-57 | C-26, `provider_merchant.rb:3-60`, `provider_merchant.rb:149` | 코드 확인. 로고 생성 callback은 `:7`의 `before_save`와 `should_generate_logo?`(`:149`)에서 읽었다. 조건 함수 본문은 일부만 읽었다. |
| R-58 | C-01 `:420-425`, `kraken_account/processor.rb:31-40`, `account/current_balance_manager.rb:95-140` | 코드 확인. `update_balance` 호출처(`simplefin_item/importer.rb:233`, `financekit/processor.rb:135`)를 확인했다. |
| R-59 | C-01 `:760-776` | 코드 확인. 호출처 파일은 2개(`grep -rln update_accountable_attributes app lib`). 호출부는 읽지 않았다. |
| R-74 | C-01 전체(`grep -n "destroy\|delete" app/models/account/provider_import_adapter.rb`에서 주석이 아닌 일치가 `:220`(해시 키 삭제), `:441`(인자 이름), `:656-676`(`delete_future_holdings`), `:1228-1229`(`extra` 키 삭제)뿐), `plaid_account/transactions/processor.rb:43-55`, `docs/llm-guides/providers.md:57` | 어댑터 파일 안의 부재 주장은 위 검색 범위에서 확인. processor 쪽 삭제는 Plaid와 문서의 Monobank 설명만 읽었고 다른 provider의 삭제 방식은 보지 않았다. |
| R-60 | C-22, `db/schema.rb:24-32` | 코드 확인. `dependent: :nullify`는 `account_provider.rb:5`. |
| R-61 | C-21, `account/linkable.rb:36-70` | 코드 확인. `first`의 정렬은 Rails 동작 가정(추론). |
| R-62 | `provider/factory.rb:19-29`, `:118-128`, `account_provider.rb:25-34` | 코드 확인. `create_adapter`의 `return nil if provider_account.nil?`(`:21`)와 `raise AdapterNotFoundError`(`:26`)를 확인했다. |
| R-63 | C-21, `account/linkable.rb:38-70`, `provider/factory.rb:21-26` | 코드 확인. `providers`·`provider`·`provider_name`이 모두 `AccountProvider#adapter`를 거치는 것을 읽었다. |
| R-64 | C-22 `:10`, `:38-51` | 코드 확인. |
| R-65 | C-23 | 코드 확인. `disconnect!`의 세부와 SnapTrade 보존 근거는 컨트롤러 주석(`:333-337`). |
| R-66 | C-02 `:805`, C-01 `:46-48` | 추론. 조건 도출만 했고 실제 재연결 시나리오는 실행하지 않았다. |
| R-67 | C-22 `:15-24`, `:53-75`, `concerns/provider_disconnectable.rb:1-70` | 코드 확인. `ProviderDisconnectable`을 쓰는 곳은 `grep -rln ProviderDisconnectable app lib` 결과 `financekit_item.rb`, `sharesight_item.rb`, `sharesight_item/unlinking.rb`와 API 컨트롤러·제너레이터 템플릿이다. 다른 provider에 같은 이름의 동작이 없다는 주장은 하지 않는다. |
| R-68 | `kraken_items_controller.rb:80-112`, `kraken_account.rb:1-35`, `akahu_items_controller.rb:116` 등 `AccountProvider.create!` 호출 | 코드 확인. `grep -rn "AccountProvider\.\(find_or_create_by\|create\|find_or_initialize\)" app lib` 결과의 앞 30줄을 봤다. 모든 provider가 같은 검사를 하는지는 확인하지 않았다. |
| R-72 | `account/linkable.rb:44-75`, `account/linkable.rb:77-87` | 코드 확인. `CATEGORY_MATCHER_PROVIDER_TYPES`의 주석(`:77-80`)이 opt-in의 이유를 설명한다. 이 목록의 provider가 `enable_category_matcher`를 실제로 확인하는지는 processor를 열어 확인하지 않았다. |
| R-73 | `kraken_account.rb:21-33` | 코드 확인. 다른 provider의 `ensure_account_provider!`가 같은 방식인지는 확인하지 않았다. |
| R-69 | C-24, `data_enrichment.rb:1-31`, `enrichable.rb:234-244`, `entry.rb:62-65` | 코드 확인. |
| R-70 | `entry.rb:445-455` | 코드 확인. |
| R-71 | `provenance/citation.rb:1-109`, `assistant/function/record_valuation.rb:84` | `grep -rn "Provenance" app lib config --include=*.rb` 결과 어댑터 경로 호출이 없었다(아래 10번). |
| T-01~T-26(T-02b 포함) | 해당 R-ID의 근거와 같다. 코드를 실행하지 않고 규칙을 입력에 적용해 도출했다. | T-10·T-12는 `source "simplefin"`(`PENDING_PROVIDERS`에 있는 네임스페이스)을 가정한다. T-10의 `extra` 결과는 R-21·R-35를 손으로 적용한 값이다. |

**부재·전칭 주장과 검색 범위 (기준 SHA `1cd94e6`, `repos/sure` clean)**

1. 어댑터의 공개 메서드가 전부다: `grep -n "^  def " app/models/account/provider_import_adapter.rb`로 `private` 앞 공개 메서드를 모았다(`initialize`, `reset_skipped_entries!`, `import_transaction`, `find_or_create_merchant`, `update_balance`, `import_holding`, `import_trade`, `update_accountable_attributes`, `find_duplicate_transaction`, `find_scheduled_transaction`, `find_pending_transaction`, `find_pending_transaction_fuzzy`, `find_pending_transaction_low_confidence`, `store_duplicate_suggestion`, `detect_activity_label`, `determine_skip_reason`, `record_skip`). `Valuation`을 만드는 메서드는 없다. 이 파일 안의 `Valuation` 언급은 주석 두 곳뿐이다. 다른 파일이 `Account::ProviderImportAdapter`를 열어 메서드를 추가하는 monkey patch는 검색하지 않았다.
2. 어댑터가 sync를 예약하지 않는다(R-03): 같은 파일에서 `sync` 문자열을 검색해 주석 외 호출이 없었다(`grep -n "sync\b\|sync_later\|sync_account" provider_import_adapter.rb`). `sync_account_later`는 `app` 아래 컨트롤러에서만 호출된다(`grep -rn sync_account_later app lib --include=*.rb`).
3. 호출처 수(참고): `import_transaction` 29개 파일, `import_holding` 16개, `import_trade` 11개, `update_balance` 5개(`grep -rln "\bimport_transaction\b" app lib --include=*.rb`, 어댑터 파일 제외). 동적 호출(`send`)은 `determine_skip_reason`·`record_skip`에서 CoinStats가 쓰는 것을 확인했고 다른 메서드는 `send` 검색을 하지 않았다.
4. `reset_skipped_entries!`, `store_duplicate_suggestion`, `find_pending_transaction_fuzzy`, `find_pending_transaction_low_confidence`의 외부 호출처 없음: `grep -rn "<이름>" app lib --include=*.rb --include=*.rake`에서 어댑터 파일 밖 일치가 0건이었다. 테스트·docs는 검색하지 않았다. 문서(`docs/`)에는 이름이 나올 수 있다.
5. `import_trade`에 보호 검사·잠금 존중이 없다(R-54): `provider_import_adapter.rb:698-753`을 줄 단위로 읽어 `determine_skip_reason`, `protected_from_sync?`, `locked?`, `enrich_attribute` 호출이 없음을 확인했다. 어댑터 밖에서 trade entry를 보호하는 callback이 있는지는 `entry.rb`와 `trade.rb`를 훑었으나 찾지 못했을 뿐이다(찾지 못함이 없음의 증거는 아니다).
6. R-02의 "어댑터에 행 단위 rescue 없음": 같은 줄 범위(`:39-364`)에서 `rescue` 키워드를 읽어 `store_duplicate_suggestion` 둘레(`:332`, `:355`)뿐임을 확인했다. `import_holding`에는 충돌 복구용 rescue(`:590`, `:642`)가 있다.
7. Kraken이 `import_trade`를 쓰지 않는다(R-04): `grep -rn "import_trade\|import_holding\|import_transaction" app/models/kraken_account app/models/kraken_item`에서 `import_holding` 한 곳(`holdings_processor.rb:86`)만 나왔다. 이 검색은 해당 두 디렉터리 한정이고 Kraken 관련 다른 위치(`lib`, 컨트롤러)는 보지 않았다. `import_trade` 호출 11개 파일 목록은 `grep -rln import_trade app lib --include=*.rb`이다.
8. `auto_claimed_pending_ids` 소비처는 Enable Banking과 Lunchflow processor뿐(R-21): `grep -rn "auto_claimed_pending_ids\|manual_merge\|merged_from_external_id" app lib --include=*.rb`에서 어댑터·`transaction.rb` 밖 일치가 `enable_banking_account/transactions/processor.rb`, `enable_banking_entry/processor.rb`, `lunchflow_entry/processor.rb`뿐이었다. 다른 provider(SimpleFIN 등)가 소비하지 않는다는 뜻은 아니다(저장된 원본 payload 재처리 방식이 달라 필요 없을 수 있음. 추론). `.rake`·`lib`도 같은 명령에 포함했다.
9. R-22의 "claim 경로에 보호 검사 없음": `import_transaction`에서 보호 검사는 `determine_skip_reason`을 부르는 `:65` 한 곳이고 이는 `(source, external_id)`로 찾은 기존 entry에만 적용된다. 보류 claim(`:142-182`)은 이 뒤에서 새 키 entry가 있을 때만 실행되며 `find_pending_transaction`·`pending_transaction_id` 조회에는 보호 조건이 없다(`:148`, C-04). 호출 순서를 줄 단위로 읽어 확인했다.
10. `Provenance::Citation`은 import 경로와 무관(R-71): `grep -rn "Provenance" app lib config --include=*.rb`에서 `provenance/` 디렉터리 밖 사용처가 `assistant/function/record_valuation.rb` 한 곳이었다(`enrichable.rb`의 "Provenance" 일치는 주석 속 일반 단어). `app/models/provenance/`에는 `citation.rb`뿐이다.
11. `transactions.external_id`를 어댑터가 쓰지 않는다: `grep -rn "transaction.external_id\|transactions.external_id" app lib --include=*.rb`에서 일치가 없었다. `Transaction#external_id` 같은 접근자 호출은 따로 검색하지 않았다. 컬럼 인덱스는 `db/schema.rb:2907`에 있다.
12. R-37의 최상위 키 목록은 R-37 항목의 검색 범위(`app`·`lib` 아래 `.rb`·`.rake`의 위 패턴)에 한한다. 첫 검색이 `superseded_external_ids`를 놓치고 재검색에서 찾았다는 점이 보여 주듯, 패턴 밖 접근은 놓칠 수 있다.
13. 어댑터에 삭제 API가 없다(R-74): R-74 행의 검색 범위. 다른 파일이 어댑터에 메서드를 덧붙이거나 `send`로 private 메서드를 부르는 경우는 보지 않았다.
14. 생성기 템플릿 24개 중 `activities_processor.rb.tt`와 `transactions_processor.rb.tt`만 열어 읽었고 나머지는 `ls`로 이름만 확인했다. 적용 메모 B의 부호 경고 근거는 `lib/generators/provider/family/templates/activities_processor.rb.tt:196-205`와 `transactions_processor.rb.tt:122-133`이다.

### 2.2 코드 읽는 순서

1. `account/provider_import_adapter.rb:39-364`(`import_transaction`)를 위에서 아래로. 주석이 각 분기의 이유(Revolut Italy 사례, 사용자가 분류한 보류 거래, 이체 다리 kind)를 설명한다.
2. 호출자 한 곳: `simplefin_entry/processor.rb:29-45`(인자 조립)와 `simplefin_account/transactions/processor.rb:26-47`(어댑터 공유, 행 단위 rescue, `skipped_entries` 수집). 인자를 더 많이 쓰는 예로 `plaid_entry/processor.rb:19-37`(`pending_transaction_id`, `replace_extra_namespaces`, `name_extra_keys`).
3. 보유종목·매매: `account/provider_import_adapter.rb:441-753`, 호출 예로 `kraken_account/holdings_processor.rb:61-97`.
4. 연결: `account_provider.rb`, `account/linkable.rb`, `provider/factory.rb`, 해제는 `accounts_controller.rb:319-357`, 연결 생성 예로 `kraken_items_controller.rb:80-112`.
5. 사용자 수정 보호의 출처(누가 플래그와 잠금을 켜는지): `entry.rb:480-526`, `transactions_controller.rb:135-195`, `concerns/enrichable.rb:149-169`.

### 2.3 비교·재사용 출처

다른 레포에 같은 기능의 스펙은 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록

`draft`다(미결정 U-01이 남아 있어 `ready` 조건을 충족하지 못한다). 2026-11-17에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-71 전부, 공개 메서드 시그니처(표 1.3) 전부, C-ID 전부, T-01~T-22와 T-12b를 따라갔다. 일치 약 58개, 부분 일치 5개, 불일치·누락 약 15건이 나왔다. 작성자가 지적 전부를 코드로 다시 확인해 반영했고 R-72~R-74, T-02b, T-23~T-26을 추가했다.
- **메인 표본 점검**: R-26·R-27(이름 비교 키가 `a-z0-9`만 남겨 한글 이름은 빈 키가 됨, `provider_import_adapter.rb:946, 949, 1000, 1005`), R-39(`Loan` 분기만 있고 `CreditCard` 분기가 없음, `:257-267`), R-40(c)(`investment_contributions_category`가 라벨이 `Contribution`이면 항상 호출됨, `:261-263`), R-37(`superseded_external_ids`가 Enable Banking 쪽 `extra` 최상위 키), T-02(`DataEnrichment.source`가 닫힌 enum), R-72(`CATEGORY_MATCHER_PROVIDER_TYPES`, `linkable.rb:81`), R-62(등록 없으면 `AdapterNotFoundError`, `factory.rb:21-26`)를 원본에서 직접 확인했다.
- **대조하지 못한 것**: R-12의 Monarch·QIF·PDF import의 `import_locked` 설정 본문, R-28의 수동 병합 UI 흐름, R-30의 집계 SQL 호출처, R-40(b)의 Transfer 확정 절차, R-41의 `GoalPledge` 내부, R-42의 분류 기록 대체 SQL, R-56의 SimpleFIN `external_id` 규칙 줄, R-67·R-68·R-49의 일부 provider 본문. R-14의 `created_at < date` 비교(PostgreSQL date→timestamp 캐스트), Rails 거짓 값 집합, enum 오류 동작은 실행하지 못한 `추론`이다.

## 적용 메모

아래 A는 원본과 다르게 할 점의 후보이고 원본 동작이 아니다. B는 자체 연동(은행 CSV 변환기, 업비트·키움 클라이언트)이 이 계약에 맞추려고 만들어 넘겨야 하는 필드와 주의점이며, 각 행에서 원본 사실과 우리 지침을 구분해 적는다. 원본의 미결정(U-01)을 여기서 해소한 것으로 치지 않는다.

**A. 원본과 다르게 할 점 (우리가 새로 정하는 설계)**

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-34, R-57 | `DataEnrichment.source`와 `ProviderMerchant.source`를 닫힌 목록이 아니라 자유 문자열로 둔다. 원본 방식(닫힌 목록)을 따르려면 새 연동의 `source`마다 두 목록(25개, 18개)에 이름을 추가하는 작업이 선행되어야 한다(원본 생성기가 하는 일). | 새 연동마다 목록을 고치지 않아도 되고 R-34의 잠재 오류가 없다. | `source` 검증을 비어 있지 않은 문자열로 완화. T-02b가 오류 없이 동작한다. 선택은 우리 결정 사항이다. |
| R-30 | 보류 표시 네임스페이스를 고정 상수 대신 등록하는 레지스트리로 바꾼다. 원본은 코드 상수 `PENDING_PROVIDERS`(`transaction.rb:117`)에 이름을 넣는 방식이다. | 새 provider의 보류 거래를 인식시키려고 코드 상수를 고쳐야 하는 것을 피한다. | 연동이 보류 네임스페이스를 등록하는 호출이 새로 생기고, `pending_sql`·`pending_extra?`가 같은 레지스트리를 읽는다. |
| R-26, R-27, R-38 | 이름 비교 키를 유니코드 글자·숫자(한글 포함)로 만들고, 투자 활동 라벨 추정에 한국어 패턴(배당금, 이자, 수수료 등)을 추가할지 정한다. 원본은 `a-z0-9`만 남기고 영어 정규식만 쓴다. | 한국 증권사·거래소 이름이 비교 키와 라벨 추정에서 모두 무시된다(T-12b, T-25). | 이름 키 함수와 `detect_activity_label` 교체. 교체하지 않으면 호출자가 `investment_activity_label`을 직접 넘겨야 한다. |
| R-54 | `import_trade`에도 보호 검사(R-09 수준)를 적용할지 정한다. 원본은 사용자가 고친 매매를 덮어쓴다. | 키움·업비트처럼 체결을 반복해 가져오는 연동에서 사용자 수정이 사라질 수 있다. | 적용하면 T-21이 바뀐다. |
| R-39 | `kind`를 덮어쓰기 전에 `kind` 잠금을 확인할지 정한다. 원본은 확인하지 않는다. | provider가 `kind`를 매번 넘기면 사용자가 바꾼 값이 되돌려진다(T-24). | 적용하면 T-24가 바뀐다. |
| R-47 | `holdings.price`의 정밀도(소수 4자리)와 음수 보유 거부를 거래소 자산에 맞게 바꿀지 정한다. | 소액 암호화폐 가격이 반올림되거나 공매도 계열 보유가 저장되지 않는다. | 컬럼 정밀도와 검증 변경. |
| R-08 | 보류 여부를 문자열 거짓 값 목록으로 읽지 않고 JSON boolean만 인식한다. | 원본은 `"no"` 같은 문자열을 참으로 읽는다. 프레임워크 상수 의존도 없앤다. | R-08, R-30에서 `true`/`false` 외 값은 오류나 거짓. |
| R-74 | 취소된 거래와 사라진 보유종목을 정리하는 어댑터 메서드를 새로 둘지 정한다. 원본에는 없다(processor가 직접 지운다). | 한국 연동에서 같은 정리 코드를 provider마다 반복하지 않게 한다. | 새 공개 메서드와 "보호된 entry를 지울지" 규칙이 필요하다. |

**B. 자체 연동이 이 계약에 맞추려고 만들어 넘길 필드와 주의점**

| 데이터 | 만들어 넘길 것(우리 지침) | 근거가 되는 원본 규칙 |
|---|---|---|
| 공통 | 연동마다 `source` 이름 하나를 고정하고(`"kb"`, `"upbit"`, `"kiwoom"` 등) 모든 호출에 같은 값을 넘긴다. 위 A의 첫 행을 원본 방식으로 가면 `source`를 두 닫힌 목록과 보류 네임스페이스 목록에 먼저 등록한다. 계정마다 어댑터를 만들고 한 sync 동안 재사용하면 `skipped_entries`를 모을 수 있다. 행 단위로 오류를 잡고 계속 진행한다. | R-01, R-02, R-05, R-06, R-34 |
| 입력 타입 | `date`는 date 타입, 금액·수량·가격은 십진수 타입(BigDecimal)으로 넘긴다. `import_trade`의 `quantity`에 문자열을 넘기면 예외가 난다. | 1.3 입력 타입 계약 |
| 은행 거래(KB CSV 등) | `external_id`: 은행이 거래 ID를 주지 않으면 거래일시·금액·적요·거래 후 잔액·같은 값 중복 순번 같은 결정적 값으로 직접 만든다(같은 파일을 다시 넣어도 같은 값이어야 멱등). 어댑터에는 이를 대신 만들어 주는 장치가 없다. `amount`: 출금은 양수, 입금은 음수(입금·출금 컬럼이 따로면 합쳐서 부호를 준다). `currency`: `"KRW"`. `date`: 거래일. `name`: 비어 있지 않은 적요(없으면 대체 문구, 비면 저장이 실패한다). `notes`: 선택(비우면 기존 메모를 지우지 않는다). | R-06, R-31~R-33 |
| 은행 보류(카드 승인) | 승인만 된 거래를 가져온다면 `extra[<ns>]["pending"] = true`를 JSON boolean으로 쓰고, 확정 때 `false`로 바꾼다. 원본에서 `<ns>`가 보류로 인식되려면 `PENDING_PROVIDERS` 상수에 이름이 있어야 한다. A의 레지스트리는 우리 설계이고 원본에는 없다. 승인 거래의 `external_id`를 확정 거래의 `pending_transaction_id`로 넘기면 금액이 달라도 대응된다. 은행 CSV처럼 확정만 있으면 보류 필드는 필요 없다. | R-08, R-19, R-30 |
| 거래 부가 | 원본 응답은 `extra[<ns>]`에 스냅샷으로 넣고 `replace_extra_namespaces: ["<ns>"]`를 같이 넘긴다. 가맹점이 있으면 `find_or_create_merchant`로 레코드를 만들어 `merchant`로 넘긴다(식별자는 정규화한 이름에서 만든 안정 값). Sure 소유 `extra` 키 이름(R-37)은 피한다. | R-35~R-37, R-56 |
| Investment 계정의 현금 활동(배당·입금·출금) | `import_transaction`으로 넣는다(거래 `Entry`). `amount`: 계좌로 들어온 돈(배당, 이자, 입금)은 음수, 나간 돈(출금, 수수료)은 양수. `investment_activity_label`: 한글 이름("배당금", "이자")은 어댑터가 추정하지 못하므로 13개 값(Buy, Sell, Sweep In, Sweep Out, Dividend, Reinvestment, Interest, Fee, Transfer, Contribution, Withdrawal, Exchange, Other) 중 하나를 직접 넘긴다. `Transfer`·`Sweep In`·`Sweep Out`·`Exchange`는 `kind`를 `funds_movement`로, `Contribution`은 `investment_contribution`과 카테고리 부작용을 만든다(R-39, R-40). 어떤 활동에 어떤 라벨을 줄지는 우리 결정이다. | R-38~R-40 |
| `kind` 인자 | 정말 필요할 때만 넘긴다. 넘기지 않으면 `kind`는 건드려지지 않고, 넘기면 매 sync마다 덮이며(잠금 무시) 6개 값 밖이면 오류다. `Loan` 계정의 음수 금액만 자동으로 `loan_payment`가 된다. | R-39 |
| 보유종목(키움·업비트) | 해석된 `security`(id, ticker). `quantity`(0 이상), `amount`(계정 통화 총 평가액), `price`(필수, 0 이상, 소수 4자리로 저장), `currency`, `date`(스냅샷 날짜), `external_id`(`"<source>_<종목>_<날짜>"`처럼 결정적 값, 권장), `account_provider_id`(연결 레코드 id, 권장), 평단가가 있으면 `cost_basis`(0은 모름으로 취급됨). `delete_future_holdings`는 `Provider::Base#can_delete_holdings?`가 기본 false라서 우리 provider adapter가 true를 반환하지 않으면 켜도 삭제되지 않는다. 종목 해석은 선행 작업이다(investments-securities 스펙). | R-43~R-50 |
| 매매(키움·업비트) | `security`, `quantity`(매수 양수·매도 음수, 숫자 타입), `price`, `amount`(수수료를 포함한 현금 영향, 지출 방향이 양수), `currency`, `date`, `external_id`(체결 ID. 없으면 호출마다 새 entry가 생기므로 사실상 필수), `fee`(`amount`에 이미 포함), `activity_label`(13개 중 하나), 해외 체결이면 `exchange_rate`(0보다 큰 숫자). | R-51~R-55 |
| 잔액 | `update_balance(balance:, cash_balance:)`로 계정 캐시를 쓴다. balance 재구성이 요구하는 anchor는 별도이고 아직 정해지지 않았다. | R-58, U-01 |
| 연결 | provider 계정 모델(`<Source>Account`: `current_account`, `has_one account_provider`), `AccountProvider(account, provider)` 한 건, `Provider::Factory.register`로 등록한 provider adapter(`provider_name`, `supported_account_types`, `can_delete_holdings?`). 등록을 빠뜨리면 연결된 계정의 `provider_name`, `providers`, `can_delete_holdings?`가 예외로 끝난다. category matcher를 쓰려면 `CATEGORY_MATCHER_PROVIDER_TYPES`에 등록한다. 해제 뒤 다른 provider로 재연결하면 중복 가능성이 있다(R-66). | R-60~R-68, R-72 |

**B에 대한 한계와 경고**

- 삭제 한계: 어댑터에는 취소된 거래나 사라진 보유종목을 지우는 메서드가 없다. `delete_future_holdings`는 같은 종목의 더 늦은 날짜 행만 지우고 `can_delete_holdings?`가 기본 false이므로 provider가 켜야 한다(R-49, R-74). 우리 연동이 취소·정정을 받으면 자기 쪽에서 지우는 코드를 따로 만들어야 한다.
- 생성기 템플릿 부호 경고: 원본에는 새 provider 뼈대를 만드는 생성기(`lib/generators/provider/family/`, 템플릿 24개와 `update_source_enums`)가 있다. 그러나 `activities_processor.rb.tt:196-205`의 `normalize_cash_amount`는 `WITHDRAWAL`·`TRANSFER_OUT`·`FEE`·`TAX`를 음수로, `CONTRIBUTION`·`TRANSFER_IN`·`DIVIDEND`·`DIV`·`INTEREST`를 양수로 만들어 `import_transaction`의 `amount`로 그대로 넘긴다. 어댑터의 규약은 양수가 지출, 음수가 수입이므로(`Entry#classification`) 반대 방향이다. 템플릿을 그대로 쓰면 부호가 뒤집힌다. 반면 `transactions_processor.rb.tt:122-133`은 은행 API의 차변을 양수로 보고 부호를 그대로 두며 반대 규약이면 직접 뒤집으라고 안내한다. 템플릿이 만든 값이 어댑터 호출 앞에서 다시 뒤집히지는 않는다.
