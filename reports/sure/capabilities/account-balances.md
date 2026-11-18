---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/account.rb
  - app/models/concerns/accountable.rb
  - app/models/concerns/syncable.rb
  - app/models/account/anchorable.rb
  - app/models/account/current_balance_manager.rb
  - app/models/account/opening_balance_manager.rb
  - app/models/account/reconcileable.rb
  - app/models/account/reconciliation_manager.rb
  - app/models/account/syncer.rb
  - app/models/account/linkable.rb
  - app/models/account/chartable.rb
  - app/models/account_share.rb
  - app/models/balance.rb
  - app/models/balance/materializer.rb
  - app/models/balance/base_calculator.rb
  - app/models/balance/forward_calculator.rb
  - app/models/balance/reverse_calculator.rb
  - app/models/balance/sync_cache.rb
  - app/models/balance/balance_data.rb
  - app/models/balance/chart_series_builder.rb
  - app/models/balance/linked_investment_series_normalizer.rb
  - app/models/balance_sheet.rb
  - app/models/balance_sheet/account_totals.rb
  - app/models/balance_sheet/account_group.rb
  - app/models/balance_sheet/classification_group.rb
  - app/models/balance_sheet/historical_account_scope.rb
  - app/models/balance_sheet/net_worth_series_builder.rb
  - app/models/balance_sheet/sync_status_monitor.rb
  - app/models/valuation.rb
  - app/models/valuation/name.rb
  - app/models/depository.rb
  - app/models/investment.rb
  - app/models/crypto.rb
  - app/models/property.rb
  - app/models/vehicle.rb
  - app/models/other_asset.rb
  - app/models/other_liability.rb
  - app/models/credit_card.rb
  - app/models/loan.rb
  - app/models/loan/principal_payments.rb
  - app/models/entry.rb
  - app/models/period.rb
  - app/models/family/syncer.rb
  - app/models/kraken_account/processor.rb
  - app/models/plaid_account/processor.rb
  - app/models/wise_account/processor.rb
  - app/models/enable_banking_account/processor.rb
  - app/models/trading212_account/processor.rb
  - app/models/ibkr_account/processor.rb
  - app/models/simplefin_item/importer.rb
  - app/controllers/accounts_controller.rb
  - app/controllers/concerns/accountable_resource.rb
  - app/controllers/concerns/entryable_resource.rb
  - app/controllers/concerns/account_authorizable.rb
  - app/controllers/properties_controller.rb
  - app/controllers/valuations_controller.rb
  - app/controllers/credit_cards_controller.rb
  - app/controllers/loans_controller.rb
  - app/controllers/vehicles_controller.rb
  - app/controllers/investments_controller.rb
  - app/controllers/cryptos_controller.rb
  - app/controllers/holdings_controller.rb
  - app/jobs/destroy_job.rb
  - config/routes.rb
  - db/schema.rb
  - docs/llm-guides/architecture.md
depends:
  - ./money-currency-rules.md
  - ./sync-pipeline.md
  - ./provider-import-adapter.md
status: draft
---

# 계정·잔액·순자산

> 사용자가 계정 9종을 수동으로 등록·수정·삭제하고 Valuation(opening anchor, current anchor, reconciliation)과 거래·매매 entry를 입력하면, 계정별 일별 잔액(`balances`)을 forward 또는 reverse 방식으로 재구성하고, 계정 캐시 잔액을 family 통화로 합산해 자산·부채·순자산과 순자산 시계열을 제공한다.

이 문서에서 쓰는 이름을 먼저 정한다. **캐시 잔액**은 `accounts.balance`와 `accounts.cash_balance` 열이다. **balances 행**은 `balances` 테이블의 하루치 행이다. **anchor**는 계정의 잔액을 그 날짜의 절대값으로 못 박는 Valuation이다(opening anchor, current anchor). **forward**는 opening anchor에서 시작해 날짜순으로 계산하는 방식, **reverse**는 current anchor에서 시작해 날짜 역순으로 계산하는 방식이다. **수동 계정**은 연동(`account_providers` 등)이 없는 계정이고, **연동 계정**은 있는 계정이다([provider-import-adapter R-61](./provider-import-adapter.md)).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

수동 계정 하나가 만들어져 순자산에 들어가기까지의 대표 경로다.

1. 사용자가 종류 하나(Depository 등 9종), 이름, 통화, 현재 잔액을 입력한다. `Account.create_and_sync`가 계정 행과 종류 행을 저장하고, 입력한 잔액을 값으로 갖는 opening anchor Valuation entry를 만든다. 대출·차량처럼 "처음 잔액"이 따로 입력되면 현재 잔액은 오늘 날짜 reconciliation Valuation으로 따로 못 박는다(R-05).
2. 계정 `Sync`가 시작되면 `Account::Syncer`가 전략을 고른다. 수동 계정은 forward, 연동 계정은 reverse다(R-24). `window_start_date`는 forward만 읽는다(R-25).
3. 계산에 쓰는 entry는 보류 거래·분할 원본·미래 날짜를 뺀 것이고, 각 금액은 계정 통화로 환산한다. 환산에 실패한 entry는 뺀다(R-28, R-37).
4. 계산기가 날짜마다 `balances` 행(시작 잔액, 현금·비현금 흐름, 조정, 시장 변동)을 만든다. Valuation이 있는 날은 그 날의 총 잔액이 Valuation 금액으로 고정되고 차이는 "조정" 열에 남는다(R-30~R-35).
5. `Balance::Materializer`가 행을 upsert하고 계산 범위 밖의 오래된 행을 지운다. forward면 마지막 행의 값을 캐시 잔액에 쓴다(R-26, R-36, R-38).
6. 사용자가 현재 잔액을 고치면 `set_current_balance`가, 과거 시점 값을 맞추면 reconciliation이 Valuation을 쓰고 다시 sync를 요청한다(R-16~R-21). 연동 계정의 정본 입력은 current anchor Valuation이다(R-22).
7. `BalanceSheet`가 캐시 잔액을 family 통화로 환산해 자산·부채·순자산을 합산하고(R-41~R-43), 순자산 시계열은 balances 행에서 만든다(R-46).

### 1.2 범위·통합 지점 [필수]

- 제공: 계정 9종의 등록·수정·상태 전환·삭제, 종류별 부가 속성의 저장, Valuation 3종 kind와 anchor 관리(opening, current, reconciliation), 일별 잔액 재구성(forward, reverse, window 기반 증분), 캐시 잔액 갱신 규칙, 계정 그룹별 합계·순자산·순자산 시계열·계정 단위 잔액 차트의 계산 규칙.
- 제외:
  - 부호 규칙 일반, 환율 조회·fallback, 통화 코드 검증, 금액 표시: [money-currency-rules.md](./money-currency-rules.md). 이 스펙은 R-21, R-25~R-27, R-36~R-41을 가져다 쓴다.
  - `Sync` 상태 기계와 `sync_later`의 창 합치기, Account sync의 호출 순서: [sync-pipeline.md](./sync-pipeline.md) R-05, R-06, R-17. 이 스펙은 `Balance::Materializer`가 받는 `window_start_date`의 의미만 정한다(R-25).
  - 외부 데이터를 entry로 넣는 계약, `update_balance`의 정의, `linked?` 정의, 연결 해제: [provider-import-adapter.md](./provider-import-adapter.md) R-58, R-61, R-65. 이 스펙은 그 값이 잔액 재구성에서 어떤 입력이 되는지(R-22, R-23)만 쓴다.
  - 보유종목 평가·`Holding` 계산·종목 시세·증권 가격 통화 환산·부동산 AVM 시세·`Holding::Materializer`: 행 4(investments-securities, 미작성). 이 스펙은 `Balance`가 `Holding` 행을 입력으로 받는 경계(R-29)만 쓴다. `Balance::LinkedInvestmentSeriesNormalizer`(연동 투자 계정 차트에서 신뢰할 수 없는 과거 구간 제거)와 `gains` 차트도 행 4다.
  - 거래·매매 entry의 생성·수정·삭제와 pending 판정: 행 2(미작성). 이체(`Transfer`) 매칭과 계정 삭제 때 `Transfer`가 지워진 뒤의 상대편 처리: 행 3(미작성).
  - 대출 상환 일정, 이자 계산, 원금 replay(`Loan::PrincipalPayments`와 `Loan::*`): 별도 엔진이다. 이 스펙은 계산기가 그 결과를 받는 경계(R-40)만 쓴다. 이유는 R-40에 있다.
  - 가족 테넌시·계정 공유 권한(`AccountShare`, `accessible_by`의 의미)·로그인 사용자 모델: 공유 계약 "Family 테넌시"(미작성, 승인 범위 밖). 이 스펙은 `BalanceSheet`가 쓰는 조건(R-41)만 쓴다.
  - 순자산 breakdown 시계열, 순자산 속도·모멘텀, 인사이트, 대시보드 위젯: 행 14. 공개 API v1과 AI 어시스턴트 도구(`set_opening_balance`, `get_balance_sheet` 등): 행 15, 17.
  - 거래·명세서 대조 상태(`Account::ReconciliationIndicator`, `entries.reconciled_status`): 이름에 reconciliation이 들어 있지만 이 스펙의 reconciliation Valuation과 별개다. 행 2, 8.
  - 로고, 계정 이름 표시, 번역, 화면 레이아웃.
- 외부 의존·선행 계약:
  - 관계형 DB: transaction, 행 잠금(`SELECT ... FOR UPDATE`), 저장된 generated column(R-27), `(account_id, date, currency)` unique 위 upsert, 날짜 생성·lateral 하위 질의가 필요한 순자산 시계열 SQL(C-15).
  - 키-값 cache(R-47), job 시스템(sync, 계정 삭제 job), 시계와 시간대(`Date.current`, [money-currency-rules](./money-currency-rules.md)의 "오늘" 전제와 같다), 진단 로그 수집기(`DebugLogEntry.capture` 한 건과 로그 한 줄).
  - 환율: money-currency-rules의 `exchange_to`(R-21), `rates_for`(R-27), 환율 SQL 규칙(R-26).
- 소유 상태·부작용: `accounts` 행과 9개 종류 테이블 행, Valuation(`valuations` 행과 그것을 가리키는 `entries` 행. `entries` 테이블 자체는 행 2와 공유), `balances` 행, 캐시 잔액. 계정 삭제는 entries·holdings·balances·공유·목표 연결 등 계정에 달린 행을 모두 지우고, 연결된 `Transfer`를 지우고, 계정에 붙은 명세서를 받은 편지함으로 돌린다(R-10).

### 1.3 인터페이스와 데이터 의미 [필수]

타입은 중립 표현이다. `decimal`은 임의 정밀도 10진수다. "오늘"은 `Date.current`다.

**accounts 행** (C-01)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `id` | uuid | DB 생성 |
| `family_id` | uuid, not null | 소유 family |
| `owner_id` | uuid, null 가능 | 소유 사용자. 저장 전에 비어 있으면 R-03의 기본 소유자 규칙으로 채운다 |
| `accountable_type`, `accountable_id` | string, uuid | 9종 중 하나와 그 종류 테이블 행(R-01). 둘 다 DB는 null 허용 |
| `name` | string | 모델이 필수로 검사한다 |
| `balance` | decimal(19,4), DB null 허용 | 캐시 잔액. 부채 계정은 갚을 크기를 양수로 둔다. 모델이 필수로 검사한다(R-03) |
| `cash_balance` | decimal(19,4), 기본 0, null 허용 | 현금 부분의 캐시. 투자·암호화폐 계정에서만 의미가 다르다(R-29) |
| `currency` | string, DB null 허용 | 계정 통화. 모델이 필수로 검사하고 코드 검증은 money R-18을 따른다 |
| `status` | string, 기본 `active` | `active`, `draft`, `disabled`, `pending_deletion`(R-09) |
| `disabled_at` | datetime, null 가능 | 비활성화 시각. 순자산 시계열의 종료 기준이다(R-46) |
| `classification` | string, 저장된 generated | `accountable_type`이 `Loan`, `CreditCard`, `OtherLiability`면 `liability`, 아니면 `asset`. 직접 쓸 수 없다(R-01) |
| `exclude_from_reports` | bool, 기본 false, not null | R-11 |
| `subtype`(accounts 열) | string | 읽는 쪽은 종류 행의 `subtype`이다(R-04). 이 열은 `Account#subtype`이 읽지 않는다 |
| `notes`, `institution_name`, `institution_domain`, `logo_selection`, `enable_category_matcher`, `locked_attributes`, `import_id` | | 이 스펙 밖 |
| `plaid_account_id`, `simplefin_account_id`, `account_providers_count` | | 연동 판정용 옛 FK와 카운터(provider-import-adapter R-61) |

**종류별 부가 속성** (수동 폼이 받는 것. 화이트리스트는 C-22)

| 종류 | 저장 속성 |
|---|---|
| Depository, OtherAsset, OtherLiability | `subtype`(OtherAsset·OtherLiability는 SUBTYPES 없음) |
| Investment | `subtype` |
| Crypto | `subtype`(`wallet`, `exchange`), `tax_treatment`(`taxable` 기본, `tax_deferred`, `tax_exempt`, not null) |
| Property | `subtype`, `year_built`(int), `area_value`(int), `area_unit`(기본 `sqft`), 주소(`address`), AVM 연동 열(`avm_provider`, `avm_external_id`, `avm_last_synced_on`, 행 4). 수정 폼이 받는 종류 속성은 `subtype`, `year_built`, `area_unit`, `area_value`뿐이다(R-08) |
| Vehicle | `make`, `model`, `year`, `mileage_value`, `mileage_unit`(속성 기본 `mi`), 저장되지 않는 폼 속성 `initial_balance`, `initial_balance_shown`, `purchase_date`(R-07) |
| CreditCard | `subtype`, `available_credit`, `minimum_payment`, `apr`, `annual_fee`(모두 decimal(10,2)), `expiration_date`, `statement_close_day`, `due_day`(정수 1~31 또는 null. DB CHECK도 같다) |
| Loan | `subtype`, `rate_type`, `interest_rate`(decimal(10,3)), `term_months`, `initial_balance`(decimal(19,4)), `start_date`(오늘 이전), `down_payment`(0 이상), `insurance_rate`(0 이상), `insurance_rate_type`(`level_term`, `decreasing_life` 또는 null), `day_count_convention`(`thirty_360` 기본, `actual_365`, `actual_actual`), `principal_only_transfers`(bool 기본 false), `variable_rate_schedule`(jsonb 날짜→이율) |

종류 테이블은 모두 `locked_attributes`(jsonb)를 갖는다(enrichment 잠금, 이 스펙 밖).

**Valuation** (C-17, C-18)

| 필드 | 의미·제약 |
|---|---|
| `valuations.kind` | `reconciliation`(기본), `opening_anchor`, `current_anchor`. 그 밖의 값은 검증 오류. not null |
| Valuation을 가리키는 `entries` 행 | `amount`는 그 날 끝의 계정 총 잔액이다(money R-39, 부호 규칙 적용 안 함). `currency`는 manager가 만들 때 항상 계정 통화다. `name`은 아래 표의 고정 영어 문구다 |
| 날짜 제약 | 같은 계정의 Valuation entry는 날짜가 유일하다(kind 무관, 모델 검증. DB 제약은 없다). 모든 entry의 날짜는 오늘로부터 30년 전 날짜보다 엄격히 늦어야 한다 |

기본 이름(저장되는 문구):

| kind | Property, Vehicle | Loan | Investment, Crypto, OtherAsset | 그 밖 |
|---|---|---|---|---|
| opening_anchor | Original purchase price | Original principal | Opening account value | Opening balance |
| current_anchor | Current market value | Current loan balance | Current account value | Current balance |
| reconciliation | Manual value update(Investment, Crypto, OtherAsset 포함) | Manual principal update | Manual value update | Manual balance update |

**balances 행** (C-14, R-27): 계정·날짜·통화당 하나. 열은 `start_cash_balance`, `start_non_cash_balance`, `cash_inflows`, `cash_outflows`, `non_cash_inflows`, `non_cash_outflows`, `net_market_flows`, `cash_adjustments`, `non_cash_adjustments`, `flows_factor`(`1` 자산, `-1` 부채), 계산기가 쓰는 `balance`, `cash_balance`, 그리고 저장된 generated column `start_balance`, `end_cash_balance`, `end_non_cash_balance`, `end_balance`. 금액 열은 모두 decimal(19,4)이다.

**연산**

| 연산 | 입력 → 출력 | 의미 |
|---|---|---|
| `Account.create_and_sync(attributes, skip_initial_sync=false, opening_balance_date=nil)` | → Account | R-05. 실패하면 예외, 전체 rollback |
| `account.set_current_balance(balance, date=nil, schedule_sync=true)` | → Result(`success?`, `changes_made?`, `error`, `historical?`) | R-19~R-21. 예외를 던지지 않고 Result로 전달 |
| `account.set_opening_anchor_balance(balance, date=nil)` | → Result(`success?`, `changes_made?`, `error`) | R-13. 성공하면 전체 sync 요청 |
| `account.create_reconciliation(balance, date, dry_run=false)`, `update_reconciliation(entry, balance, date, dry_run=false)` | → ReconciliationResult | R-16, R-17 |
| `Balance::Materializer(account, strategy, security_ids=nil, window_start_date=nil).materialize_balances` | → 반환값 없음(소비자 없음) | R-26. strategy는 `forward`, `reverse` |
| `BalanceSheet(family, user=nil)` | `assets`, `liabilities`, `net_worth`, `account_groups`, `net_worth_series(period)`, `syncing?` | R-41~R-46. user가 없으면 로그인 사용자, 그것도 없으면 family 전체 |
| `account.balance_series(period, view, interval)` | → Series | R-48. view는 `balance`, `cash_balance`, `holdings_balance`, `gains` |

**웹 진입점** (경로·메서드는 원본 그대로. 이 중 sync와 연결 해제는 선행 스펙 소관)

| 경로 | 동작 |
|---|---|
| `POST /depositories`, `/investments`, `/properties`, `/vehicles`, `/credit_cards`, `/loans`, `/cryptos`, `/other_assets`, `/other_liabilities` | 계정 생성(R-05, 속성 `account[...]`는 C-22). `GET .../new`, `GET .../:id/edit`가 폼 |
| `PATCH /<종류>/:id` | 계정 수정(R-08). Property는 별도 `update`를 쓰고 `balance`를 받지 않는다 |
| `DELETE /accounts/:id` | 삭제 예약(R-10) |
| `PATCH /accounts/:id/toggle_active` | active ↔ disabled(R-09) |
| `PATCH /accounts/:id/set_default`, `/remove_default` | 사용자의 기본 계정 지정·해제(R-51) |
| `PATCH /accounts/:id/toggle_exclude_from_reports` | R-11 |
| `PATCH /accounts/reorder` | 사용자별 수동 정렬 저장, 실패하면 422(R-44) |
| `POST /valuations`, `PATCH /valuations/:id`, `DELETE /valuations/:id`, `POST /valuations/confirm_create`, `POST /valuations/:id/confirm_update` | reconciliation 생성·수정·삭제와 dry-run 확인(R-16, R-17) |
| `PATCH /properties/:id/update_balances` | Property의 통화와 현재 잔액(R-06) |
| `POST /properties` (`avm_provider` 있음 또는 없음) | Property 생성의 AVM 분기와 수동 분기(R-06) |

수정·삭제·상태 전환·valuation 변경은 계정의 소유자 또는 `full_control` 공유자만 할 수 있다(`require_account_permission!`, 권한 모델은 Family 테넌시 계약).

### 1.4 행동 규칙과 남은 질문 [필수]

"today"는 `Date.current`다. "계산 결과 행"은 balances 행이다. 금액의 부호는 [money-currency-rules R-36~R-40](./money-currency-rules.md)을 따르고, 여기서는 balances 행의 열이 그것을 어떻게 쓰는지만 쓴다.

**A. 계정과 종류**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 계정 종류와 자산·부채 구분 | 종류는 `Depository`, `Investment`, `Crypto`, `Property`, `Vehicle`, `OtherAsset`, `CreditCard`, `Loan`, `OtherLiability` 아홉 개뿐이다. 계정 하나는 종류 테이블의 행 하나와 `accountable_type`·`accountable_id`로 이어진다. 계정을 만들면 종류 행도 같이 만들고(`accountable_attributes`가 없으면 빈 속성으로), 계정을 지우면 종류 행도 지운다. `Loan`, `CreditCard`, `OtherLiability`는 부채(`liability`), 나머지 여섯은 자산(`asset`)이다. 이 구분은 DB가 `accountable_type`에서 계산해 저장하는 열(`accounts.classification`)이고 각 종류 클래스의 분류값과 같다. 9종 밖의 이름은 종류로 인정하지 않는다(조회 함수가 없음을 돌려준다). | 코드 확인 |
| R-02 | 계정의 `balance_type` | `Depository`, `CreditCard`는 `cash`. `Property`, `Vehicle`, `OtherAsset`, `Loan`, `OtherLiability`는 `non_cash`. `Investment`, `Crypto`는 `investment`. 그 밖은 오류다. 이 값이 잔액을 현금과 비현금으로 나누는 방식을 정한다(R-29, R-30, R-35). 대출·기타 부채가 `non_cash`인 것은 부채 전체가 "현금이 아닌 부분"이라는 뜻이다. | 코드 확인 |
| R-03 | 계정 저장 | `name`, `balance`, `currency`가 비어 있으면 검증 오류다. `family`가 있어야 하고, `owner`가 정해져 있으면 그 사용자가 같은 family 소속이어야 한다(아니면 오류). 소유자가 비어 있으면 검증 직전에 채운다. 현재 사용자가 있고 그 사용자의 family가 같으면 그 사용자, 아니면 family의 admin 중 가장 먼저 만들어진 사용자(`created_at`, 같으면 `id`), 없으면 super_admin 중 같은 순서, 없으면 아무 사용자 중 같은 순서다. `status` 기본값은 `active`다. 통화 코드가 표에 있는지는 검사하지 않는다(money R-18). 새 계정 폼의 통화 기본값은 family 대표 통화다. | 코드 확인 |
| R-04 | 종류별 속성과 subtype | `subtype`은 종류 행에 저장하고 `Account#subtype`은 그 값을 읽는다. 검증은 `Loan`만 한다(허용 목록 7개 `mortgage`, `student`, `auto`, `home_equity`, `line_of_credit`, `business`, `other`, 빈 값 허용). 다른 종류는 어떤 문자열도 저장한다. 종류별 허용 목록은 화면 선택지일 뿐이다(C-02). `CreditCard`의 `statement_close_day`, `due_day`는 1~31 정수 또는 null, `Loan`의 `start_date`는 오늘 이전, `down_payment`와 `insurance_rate`는 0 이상, `insurance_rate_type`은 두 값 또는 null, `day_count_convention`은 세 값 중 하나가 아니면 검증 오류다. `Loan`의 이율 변경 이력은 폼 입력 `rate_changes`(행마다 `effective_date`, `rate`)로 받아 `variable_rate_schedule`(날짜 → 이율 문자열)을 조립한다. 날짜와 이율이 둘 다 빈 행은 건너뛴다. 하나만 비었거나, 이율이 유한한 0~100 범위 밖이거나(`MAX_INTEREST_RATE` 100), 날짜가 ISO 8601(`YYYY-MM-DD`)이 아니면 그 행을 불완전·무효 행으로 모아 두었다가 저장을 거부하고(검증 `rate_changes_must_be_parseable`) 폼에 입력한 그대로 되돌려 준다. 같은 날짜의 행은 나중 행이 덮어쓴다(하나의 날짜에 이율 둘을 둘 수 없다). `rate_changes` 키가 아예 없으면 이력은 바뀌지 않고, 빈 배열이면 이력을 비운다. 가변 금리 대출은 대출 시작일(`start_date`, 없으면 첫 Valuation 날짜, 없으면 opening anchor 날짜)보다 이른 이율 변경이 있으면 저장을 거부한다(`rate_changes_must_not_precede_origination`). 변경 이력이 같아 보이는 저장에서도 무효 행이 있으면 검증이 돌도록 계정 저장 때마다 이 종류 행을 검사한다(`changed_for_autosave?`). `Crypto`는 `subtype`이 `exchange`일 때만 사용자가 매매를 직접 입력할 수 있다. `Investment`의 세액 구분(`tax_treatment`)은 subtype 표에서 읽고 없으면 `taxable`이다(C-02). | 코드 확인 (subtype 검증이 Loan뿐이라는 것은 2.1) |
| R-05 | 수동 계정 생성 (`Account.create_and_sync`) | (1) `accountable_attributes`가 없으면 빈 맵으로 둔다. `cash_balance` 키가 없으면 `cash_balance = balance`로 둔다. (2) `accountable_attributes.initial_balance`가 비어 있지 않을 때만 decimal로 읽는다(빈 문자열은 값 없음). (3) 한 DB transaction 안에서 계정을 저장하고(`save!`), opening anchor를 만든다. 금액은 `initial_balance`가 있으면 그것, 없으면 `account.balance`다. 날짜는 호출자가 준 `opening_balance_date`이고 없으면 R-13의 기본 날짜다(웹 폼 경로는 날짜가 비거나 잘못되면 오늘로부터 2년 전을 넘긴다). 단 `initial_balance`가 있는 `Loan`이고 `start_date`가 있고 그것이 30년 전 날짜보다 늦으면 `start_date`가 폼 날짜를 이긴다. (4) `initial_balance`가 있고 `account.balance`와 다르며 opening anchor 날짜가 오늘보다 이르면, 오늘 날짜 reconciliation(금액 `account.balance`)을 따로 만든다. opening anchor가 오늘이면 만들지 않는다(같은 날 reconciliation이 anchor를 덮어쓰기 때문). (5) family 설정이 "기본 공유"이면 계정을 다른 구성원에게 공유한다(Family 테넌시). (6) 위 단계의 오류는 예외로 전체를 되돌린다. (7) 함수 끝에서 `skip_initial_sync`가 아니면 창 없는 `sync_later`를 요청한다. 이 시점은 호출자의 transaction에 달려 있다. 이 함수 안의 transaction은 끝났지만, 웹 생성 경로(`AccountableResource#create`)는 이 함수를 `Account.transaction`으로 한 번 더 감싸고 소유자(`owner: 현재 사용자`)를 넘기며 같은 바깥 transaction 안에서 `lock_saved_attributes!`까지 한다. 그래서 웹 경로에서 `Sync` 행은 바깥 transaction 안에서 만들어지고, `SyncJob` 큐 등록은 바깥 transaction이 commit된 뒤로 미뤄진다(`ApplicationJob`의 commit 후 enqueue 설정). 바깥 transaction이 되돌려지면 `Sync` 행도 job도 남지 않는다. 연동 계정을 만드는 경로(`create_from_*_account`)는 `skip_initial_sync`를 켜고 같은 함수를 부른다. 입력한 현재 잔액이 곧 opening anchor가 되므로 이후 거래는 그 날짜 이후부터 잔액을 움직인다. | 코드 확인 |
| R-06 | Property 생성(마법사) | 웹 Property 생성은 두 갈래다. AVM provider를 고른 경우(`params[:avm_provider]`)는 `create_via_avm_provider`가 따로 처리한다(미리보기 토큰 확인 뒤 `status: draft`로 계정을 만든다, 행 4). 수동 경로는 `create_and_sync`를 쓰지 않는다. 계정을 `balance: 0`, `status: draft`, 소유자 = 현재 사용자, 통화 = 입력 또는 family 통화로 만들고(`create!`) 종류 속성을 사용자 입력으로 잠그고, family 설정이 "기본 공유"면 `auto_share_with_family!`를 부른다. sync는 요청하지 않고 opening anchor도 만들지 않는다. 다음 단계 `update_balances`가 통화(주어졌을 때)와 현재 잔액을 `set_current_balance`로 쓴다(transaction 안, 실패하면 둘 다 되돌린다). 수동·비현금 계정이므로 R-21에 따라 오늘 날짜 reconciliation 하나가 생긴다. 마지막 단계 `update_address`가 주소를 저장하고 `draft`면 `activate`한다. 그래서 이 경로의 Property는 opening anchor가 없는 계정이고 R-13의 fallback 날짜를 쓴다. | 코드 확인 |
| R-07 | Vehicle 구매 가격·날짜 편집 | 폼이 `initial_balance`(구매 가격), `initial_balance_shown`(화면에 보여 준 가격), `purchase_date`를 항상 미리 채워 보낸다. 반올림한(통화 소수 자릿수) `initial_balance`가 `initial_balance_shown`(없으면 저장된 구매 가격)과 다르면 가격이 편집된 것이고, `purchase_date`가 현재 opening anchor 날짜와 다르면 날짜가 편집된 것이다. 하나라도 편집되면 종류 행 갱신 직후(`after_update`) `set_opening_anchor_balance`로 opening anchor를 갱신한다(실패하면 그 오류로 저장을 되돌린다. 날짜는 R-13의 date 오류 규칙을 먼저 검증한다). 쓸 금액은 가격이 편집됐으면 `initial_balance`, 아니면 `unedited_anchor_balance`다. 날짜만 편집했고 현재 opening anchor 날짜가 오늘이면 `initial_balance_shown`(있을 때)을 쓰고(그 날의 anchor는 오늘의 현재 값이기도 해서 같은 폼의 계정 갱신이 이미 덮어썼을 수 있기 때문), 그 밖에는 현재 구매 가격(`purchase_price`)이다. 이 `after_update`는 웹 수정 경로에서 계정의 `balance` 변경(R-08의 `set_current_balance`)이 끝난 뒤에 돈다. 그래서 `after_update` 시점에 읽는 `account.balance`는 폼에서 현재 잔액도 바꿨다면 이미 새 값이다. anchor 금액이 이 `account.balance`와 다르고 anchor 날짜가 오늘보다 이르고 anchor 다음 날부터 오늘까지 Valuation이 하나도 없으면, 현재 값이 anchor를 따라 바뀌지 않게 오늘 날짜 reconciliation(금액 = 그 시점의 `account.balance`)을 만든다. `purchase_price`는 opening anchor가 있으면 그 금액, 없으면 첫 Valuation(없으면 현재 잔액)이다. | 코드 확인 |
| R-08 | 계정 수정(종류별 `update`) | 기본 경로(`AccountableResource#update`, Property 외 8종)는 폼 속성이 C-22의 화이트리스트다. 입력 `balance`가 있고 캐시 잔액과 다르면 먼저 `set_current_balance`(날짜 없이)를 부르고, 실패하면 이유를 오류 메시지로 하고 전체를 되돌린다. 비교는 입력을 decimal로 읽은 전체 정밀도 그대로 저장된 캐시 값(소수 4자리)과 `!=` 하며 통화 자릿수로 반올림하지 않는다(소수 5자리 이상을 입력하면 같은 값으로 보이는데도 `set_current_balance`가 불린다, 추론). 이어 `balance`와 `opening_balance_date`를 뺀 나머지 속성(이름, 통화, subtype, 종류별 속성, 노트, `exclude_from_reports` 등)을 `update`하고 실패하면 잔액 변경까지 되돌린다. 통화는 이 경로로 바꿀 수 있다. **Property는 `update`를 덮어쓴다.** 허용 키는 `name`, `currency`, `accountable_type`, `institution_name`, `institution_domain`, `notes`, `accountable_attributes`(`id`, `subtype`, `year_built`, `area_unit`, `area_value`)뿐이고 `balance`, `exclude_from_reports`는 받지 않으므로 이 경로는 `set_current_balance`를 부르지 않는다(잔액은 `update_balances`, R-06). 저장하면 종류 속성을 잠그고, 계정이 `active`면 수정 화면을 다시 보여 주고 아니면 잔액 단계로 보낸다. sync 요청: 종류 행에 sync를 요청하는 callback은 두 개다. `Loan`은 상환 입력(`interest_rate`, `term_months`, `rate_type`, `start_date`, `variable_rate_schedule`, `day_count_convention`, 보험료 두 속성, `initial_balance`, `principal_only_transfers`)이 바뀐 저장이 commit될 때(R-40), `Vehicle`은 구매 가격·날짜 편집 때(R-07, `set_opening_anchor_balance`)다. 이름, 통화, subtype 등 다른 속성만 바꾸는 수정은 sync를 요청하지 않는다. 그러면 통화만 바꾼 경우 balances 행은 다음 sync까지 이전 통화로 남는다(R-36). | 코드 확인 (통화 변경 뒤 결과와 5자리 입력 효과는 추론) |
| R-09 | 상태 기계 | 상태는 `active`(초기), `draft`, `disabled`, `pending_deletion`이다. 이벤트: `activate`는 `draft`, `disabled` → `active`(`disabled_at`을 비운다). `disable`은 `draft`, `active` → `disabled`. `enable`은 `disabled` → `active`(`disabled_at`을 비운다). `mark_for_deletion`은 `draft`, `active` → `pending_deletion`(`disabled_at`을 비운다), `disabled` → `pending_deletion`(`disabled_at` 유지). `restore_after_failed_deletion`은 `pending_deletion` → `disabled`(이전 `disabled_at`이 있으면 유지). 허용되지 않은 전이는 오류다. `disabled`로 들어갈 때 `disabled_at`이 찍히는 것은 상태 기계 라이브러리의 timestamps 옵션이 한다(레포 밖 의미). 조회 범위: `visible` = `draft` + `active`, `historical` = `visible` + `disabled`. `pending_deletion`은 둘 다에 들어가지 않는다. `toggle_active`는 `active`면 `disable`, `disabled`면 `enable`을 하고 그 밖의 상태에서는 아무것도 하지 않는다. `disabled_at`은 순자산 시계열이 그 계정의 마지막 날을 정하는 기준이다(R-46). | 코드 확인 (`disabled_at` 기록은 추론) |
| R-10 | 계정 삭제 | 연동 계정은 삭제할 수 없다(경고와 함께 거부. 연결을 먼저 해제해야 한다, provider-import-adapter R-65). 수동 계정은 `destroy_later`: 계정 행을 잠근 transaction 안에서 현재 상태를 읽고 `mark_for_deletion`을 한다. 두 번째 요청은 이미 `pending_deletion`이라 상태 전이 오류가 나고 "삭제 실패"로 보인다. transaction이 commit된 뒤에 삭제 job을 큐에 넣고, 넣기에 실패하면 상태를 이전 값으로 되돌린다. job은 `account.destroy`를 한다. 실패하면 상태를 `disabled`로 돌린다(이전 `disabled_at`이 있으면 유지, 없으면 지금. 그 사이 다른 쓰기가 상태를 바꿨으면 덮어쓰지 않는다). 교착(deadlock)은 job이 최대 5번 늘어나는 간격으로 재시도한다. 삭제가 실행되면 먼저 이 계정 거래 entry에 연결된 `Transfer`(inflow 또는 outflow가 이 계정)를 모두 지우고, 계정에 달린 공유, import 매핑, entries, holdings, balances, 정기 거래, 목표 연결·pledge, 종류 행을 지운다. 이 계정으로 들어오는 정기 이체 규칙도 지운다. commit 뒤에 이 계정에 붙었던 명세서(`account_statements`)는 지우지 않고 `account_id`를 비우고 `review_status`를 `unmatched`로 바꿔 받은 편지함으로 돌린다. DB는 계정을 가리키는 일부 외래 키를 삭제 때 null로 만든다: `users.default_account_id`(기본 계정 해제, R-51), `account_statements.account_id`와 `suggested_account_id`, `debug_log_entries.account_id`, `financekit_account_lineages.account_id`, `sharesight_accounts`의 배당·자금·정산 계정 id 세 개, `accounts.owner_id`(사용자 쪽 삭제 때). `entries`는 계정 삭제 때 DB가 같이 지운다(cascade). | 코드 확인 |
| R-11 | `exclude_from_reports` | 계정의 관리 권한자가 토글하는 bool이다. 켜면 현재 합계(R-41의 counted 조건)와 순자산 시계열(R-46의 대상 조건)에서 빠지지만, 계정 목록·그룹 안의 계정 행에는 남는다. 다른 보고서·내보내기가 이 값을 쓰는 방식은 행 14다. | 코드 확인 |

**B. anchor와 Valuation**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | Valuation entry의 제약과 의미 | kind는 1.3 표의 세 값이다. 이 계정의 Valuation entry는 날짜가 유일하다(모델 검증). opening anchor, current anchor가 계정당 하나라는 DB 제약이나 모델 검증은 없고, anchor를 읽는 곳은 kind로 걸러 `first`(정렬 없음)를 쓴다. 하나뿐이라는 가정은 anchor를 쓰는 manager의 잠금과 호출 규칙이 지킨다. anchor가 둘 이상 생기면 원본은 Valuation 행의 기본 키(uuid) 순으로 첫 번째를 쓰므로(프레임워크의 `first` 의미, 추론) 날짜와 무관하게 임의의 하나가 이긴다. 이 경우의 결정적 규칙은 원본에 없다. 따라서 재구현은 계정당 kind별 하나를 유지해야 하고, 둘 이상이 들어온 입력은 정의되지 않은 동작이다(적용 메모). entry는 `date`, `name`, `amount`, `currency`가 필수이고 `date`는 `오늘 - 30년`(같은 날짜 불가)보다 늦어야 한다. Valuation의 금액이 음수가 아니어야 한다는 검증은 없다(money R-39). 기본 이름은 1.3의 표다. reconciliation이 같은 날 이름을 덮어쓰는 규칙은 R-16이다. | 코드 확인 |
| R-13 | opening anchor | `has_opening_anchor?`는 kind가 `opening_anchor`인 Valuation의 존재다. `opening_date`: anchor가 있으면 그 entry 날짜, 없으면 (Valuation entry 중 가장 이른 날짜)와 (Valuation이 아닌 entry 중 가장 이른 날짜의 하루 전) 중 이른 쪽, 둘 다 없으면 오늘. `opening_balance`: anchor 금액, 없으면 0. `set_opening_balance(balance, date=nil)`: 계정 행을 잠근 transaction 안에서(조회 cache 없이) 다음을 한다. 날짜가 주어졌고, anchor 자신을 뺀 entry가 있고, `date >=` 그 가장 이른 entry 날짜이면 실패 결과(`Opening balance date must be before the oldest entry date`)를 돌려주고 아무것도 쓰지 않는다. anchor가 없으면 새로 만든다(kind `opening_anchor`, 이름은 종류별 문구, 금액 `balance`, 통화 = 계정 통화, 날짜 = 주어진 날짜 또는 기본 날짜). 있으면 금액이나 날짜(주어졌을 때만)가 다를 때 갱신하고 `changes_made?`로 알린다. 기본 날짜: anchor를 뺀 entry가 있으면 (가장 이른 entry 날짜 - 1일)과 (오늘 - 2년) 중 이른 쪽, 없으면 오늘 - 2년. `Account#set_opening_anchor_balance`는 성공하면 창 없는 `sync_later`를 요청한다. opening anchor가 삭제되면(R-52) 위의 fallback이 적용되고 forward 시작 잔액은 0이 된다(R-31). | 코드 확인 |
| R-14 | 이른 entry 앞으로 anchor 이동 (`ensure_opening_anchor_precedes_entries`) | 연동이 과거 거래를 넣은 뒤 provider 흐름이 부른다. opening anchor가 있고 금액이 0일 때만 동작한다(금액이 있는 anchor는 사람이 입력한 값이라 옮기지 않는다). anchor를 뺀 entry 중 가장 이른 날짜가 anchor 날짜 이하이면 anchor 날짜를 그 날짜의 하루 전으로 옮기고 금액 0을 유지한다. 실패하면 예외다. sync는 요청하지 않는다. | 코드 확인 |
| R-15 | `history_start_date`, `Account#start_date` | `history_start_date`: 연동된 투자·암호화폐 계정이면 `LinkedInvestmentSeriesNormalizer`가 정한다(행 4). 그 외에는 (opening anchor가 있으면 그 날짜, 보류가 아닌 entry 중 가장 이른 날짜, balances 행 중 가장 이른 날짜)의 최솟값이다. `Account#start_date` = (모든 entry 중 가장 이른 날짜, 없으면 오늘) - 1일. 이 값은 money R-35의 환율 필요 시작일이 쓴다. | 코드 확인 |
| R-16 | reconciliation (`reconcile_balance(balance, date=오늘, dry_run=false, existing_valuation_entry=nil)`) | (1) 변경 전 값: `existing_valuation_entry`가 있으면 그 날짜, 없으면 `date`의 balances 행(통화 = 계정 통화)에서 `end_balance`, `end_cash_balance`를 읽는다(행이 없으면 둘 다 없음). (2) 쓸 Valuation entry: 인자로 받은 entry, 없으면 이 계정의 `date`에 있는 Valuation entry(kind 무관), 없으면 새 reconciliation entry(이름은 종류별 문구)다. 날짜 = `date`, 금액 = `balance`, 통화 = 계정 통화로 쓴다. kind가 `reconciliation`인 Valuation이면 이름을 기본 이름으로 되돌린다(provider가 붙인 라벨은 덮어써진다). 같은 날 anchor Valuation이 있으면 금액만 바뀌고 kind는 그대로다. (3) `dry_run`이 아니면 저장하고 R-17의 pledge 대조를 실행한다. `dry_run`이면 저장도 pledge도 없다. (4) 결과: `success? = true`, `old_balance`, `old_cash_balance`, `new_balance = balance`, `new_cash_balance`. `new_cash_balance`는 `date`의 balances 행에 `balance`와 `cash_balance`가 모두 있을 때만 `balance - (행의 end_balance - 행의 end_cash_balance)`이고(총액에서 기존 비현금을 뺀 현금), 아니면 없음이다. (5) 어떤 예외든(검증 실패 포함) `success? = false`와 메시지로 돌려주고 던지지 않는다. | 코드 확인 |
| R-17 | reconciliation의 부수 효과와 호출 | `Account#create_reconciliation`, `update_reconciliation`은 R-16을 부르고 `success?`이고 `dry_run`이 아니면 창 없는 `sync_later`를 요청한다(전체 재계산). `dry_run`은 확인 대화상자(`confirm_create`, `confirm_update`)가 쓴다. 저장 뒤 `GoalPledge::Reconciler`를 `valuation_delta`와 함께 부른다(행 12). delta = 저장한 금액 - (기존 Valuation을 수정한 경우 그 저장 전 금액, 아니면 balances 행의 `end_balance`, 그것도 없으면 0)이다. 웹의 금액 공백 검사는 확인 단계(`confirm_create`, `confirm_update`)에만 있고 "금액 필요" 오류로 되돌려 보낸다. `create`는 공백 검사 없이 `create_reconciliation`을 부르므로 금액이 비면 저장 검증 오류의 메시지로 실패한다. `update`는 날짜나 금액이 하나라도 비어 있으면 reconcile을 건너뛰고(노트만 저장) 성공으로 처리한다. Valuation entry를 삭제하면(`DELETE /valuations/:id`, 권한은 1.3 끝의 규칙, kind 제한 없음, R-52) entry를 지운 뒤 창 없는 계정 sync를 요청한다(삭제된 entry는 시작 날짜를 남기지 않는다). | 코드 확인 |
| R-18 | current anchor 읽기 (`CurrentBalanceManager`) | `has_current_anchor?`는 kind가 `current_anchor`인 Valuation의 존재다. `current_balance`: anchor가 있으면 그 entry 금액, 없으면 경고 로그(`No current balance anchor found for account <id>. Using cached balance instead, which may be out of date.`)를 남기고 캐시 잔액을 돌려준다. `current_date`: anchor가 있으면 그 entry 날짜, 없으면 오늘. 원본 주석은 anchor가 항상 있어야 하고 fallback은 하위 호환용이라고 적는다. anchor가 없을 때는 호출마다 다시 조회하고 경고를 남긴다. | 코드 확인 |
| R-19 | `set_current_balance(balance, date=nil, schedule_sync=true)` | 연동 계정이면 R-20(날짜 = 주어진 값 또는 오늘), 수동 계정이면 R-21(날짜는 무시되고 오늘로 처리)을 따른다. 수동 경로에서는 전략 결과가 실패여도 이어서 `account.update!(balance: balance)`로 캐시 잔액을 쓴다(성공 여부와 무관하게 캐시가 바뀐다). 중간의 모든 예외는 `success? = false`와 메시지로 돌려준다. `Account#set_current_balance`는 `success?`이고 `schedule_sync`가 참이면 창 없는 `sync_later`를 요청한다. 캐시 잔액은 `balance`만 쓰고 `cash_balance`는 건드리지 않는다. | 코드 확인 |
| R-20 | 연동 계정의 current anchor 쓰기 | 계정 행을 잠근 안에서 anchor를 다시 읽은 뒤: (a) anchor가 있고 그 날짜가 `date`보다 늦으면 "과거 명세서"다. 그 `date`의 reconciliation을 R-16으로 쓰고(그 날짜의 Valuation이 있으면 갱신), anchor와 캐시 잔액은 그대로 두고, `historical? = true`로 돌려준다. (b) 아니면 anchor가 있고 anchor 날짜가 `date`와 다르면 기존 anchor를 reconciliation으로 바꾼다(kind 변경, 이름은 reconciliation 기본 이름). 날짜가 같으면 그대로 둔다. 그 뒤 anchor가 남아 있으면(같은 날짜) 금액·날짜가 다를 때 갱신하고, 없으면 새 anchor entry(날짜 `date`, 금액 `balance`, 통화 = 계정 통화, 이름은 종류별 문구)를 만든다. 마지막으로 `account.update!(balance: balance)`를 한다. `changes_made?`는 anchor를 만들었거나 금액·날짜가 바뀌었을 때 참이다. 같은 날짜에 이미 reconciliation이 있으면 새 anchor 저장이 날짜 유일성 검증에 걸려 실패하고 잠금 transaction이 되돌려지며 결과는 실패다. 결국 sync마다 anchor가 하루 전 값의 reconciliation 하나씩을 남기는 "waypoint 사슬"이 만들어지고, reverse 계산이 그 waypoint에서 잔액을 다시 맞춘다(R-34). | 코드 확인 (잠금 transaction 되돌림은 프레임워크 의미를 읽은 추론) |
| R-21 | 수동 계정의 `set_current_balance` | 두 전략 중 하나다. (a) 거래 조정: `balance_type`이 `cash`(Depository, CreditCard)이고 이 계정에 kind `reconciliation`인 Valuation이 하나도 없으면, opening anchor 금액을 `새 balance - 캐시 잔액` 만큼 바꾼다(`set_opening_balance(balance: 현재 opening_balance + delta)`, 날짜는 그대로, anchor가 없으면 R-13의 기본 날짜로 새로 만든다). Valuation을 새로 쓰지 않으므로 "그 날부터 값을 리셋"하지 않는다. (b) 값 추적: 그 밖의 모든 경우(`non_cash`, `investment`이거나 cash인데 reconciliation이 이미 있음)에는 오늘 날짜의 Valuation(kind 무관)이 있으면 그것을 갱신하고 없으면 새 reconciliation을 만든다(R-16). 결과의 `changes_made?`는 항상 참이다. 어느 쪽이든 sync는 R-19의 `sync_later`가 맡는다. | 코드 확인 (두 전략의 의도는 원본 주석) |
| R-22 | **balance 재구성의 입력과 새 연동의 현재 잔액 경로 (provider-import-adapter U-01의 결론)** | 재구성이 읽는 "현재 잔액"은 전략에 따라 다르다. **reverse(연동 계정)**: 출발점은 current anchor Valuation의 금액과 날짜다(R-18). anchor가 없을 때만 캐시 잔액(날짜 = 오늘)을 쓴다. 그래서 reverse에서 `accounts.balance`는 anchor가 없을 때의 fallback 입력이고, anchor가 있으면 입력이 아니다. **forward(수동 계정)**: 출발점은 opening anchor와 모든 Valuation(kind 무관)이고 캐시 잔액은 입력이 아니라 출력이다(R-26, R-38). 캐시 잔액이 입력으로 읽히는 곳은 수동 계정의 `set_current_balance` 거래 조정의 delta 계산(R-21), 수정 폼의 변경 판정(R-08), 합계(R-42)다. 원본에서 두 경로가 공존한다. `*_account/processor.rb` 27개 중 **anchor 경로(`set_current_balance` 호출)는 12개**(CoinStats, Enable Banking, IBKR, Indexa Capital, Plaid, Questrade, Redbark, Sharesight, SnapTrade, Sophtron, Trade Republic, Trading212)이고, **캐시 직접 쓰기(anchor 없음)는 15개**(`account.update!(balance:, cash_balance:)`: Akahu, Binance, Brex, Coinbase, Coinspot, Fio, Kraken, Lunchflow, Mercury, Monobank, OnchainWallet, SimpleFIN, TrueLayer, Up, Wise)이며 그 밖에 FinanceKit이 `update_balance`를 쓴다(SimpleFIN은 item importer도 `update_balance`). 따라서 "대다수 provider가 `set_current_balance`"는 사실이 아니다. 새 연동이 `set_current_balance`를 **반드시 써야 하는지**의 답: 원본은 강제하지 않는다. provider 계약(`Provider::Base`, 어댑터 등록)에 잔액 연산의 요구가 없고, 직접 쓰기 provider 15개 이상도 sync가 성공한다. 직접 쓰기를 하면 anchor가 없으므로 reverse가 캐시 잔액을 오늘 날짜 출발 잔액으로 쓰고, 읽을 때마다 R-18의 경고가 남고, 이전 current anchor를 reconciliation waypoint로 굳히는 사슬(R-20)이 없다. 원본 provider 생성기 템플릿(`lib/generators/provider/family/templates/account_processor.rb.tt`)은 `set_current_balance`를 부르고 주석에 "reverse sync가 제대로 동작하려면 필수"라고 적는다(개발자 의도, 추론). anchor 경로의 순서는 provider마다 다르다. Trading212는 `balance`, `cash_balance`, 통화를 계정에 먼저 저장한 뒤 `set_current_balance(총액)`을 부른다. Plaid는 계정 행을 잠근 안에서 (a) anchor가 명세서 날짜보다 최신이 아니고 계정 통화가 provider 통화와 다르면 통화를 provider 통화로 바꾸고(anchor가 더 최신이면 통화를 바꾸지 않는다), (b) manager의 `set_current_balance(balance, date: 명세서 날짜)`를 부르고(실패하면 오류), (c) 결과가 `historical?`이 아닐 때만 `cash_balance`를 쓰고, 끝나고 sync를 요청한다(과거 명세서면 캐시 `balance`와 `cash_balance` 모두 그대로). IBKR도 같은 틀이다. 이 스펙은 provider에 대한 강제 규칙을 만들지 않고 두 경로의 결과를 R-23에 적는다. | 코드 확인 (provider 분류는 위 27개 파일의 `grep`, 2.1) |
| R-23 | `update_balance`와 캐시 직접 쓰기의 효과 | `update_balance(balance, cash_balance=nil)`는 계정의 `balance`를 쓰고 `cash_balance`를 `cash_balance` 또는 `balance`로 쓴다(provider-import-adapter R-58). Valuation도 sync도 만들지 않는다. 계정 직접 쓰기도 같은 효과이고 통화·`cash_balance`를 함께 쓰는 경우가 많다. 효과는 계정 상태에 따라 갈린다. (a) anchor가 없는 연동 계정: 다음 reverse 재계산이 그 값을 출발 잔액(날짜 오늘)으로 쓰고 읽을 때마다 R-18의 경고를 남긴다. 해당 provider는 R-22의 직접 쓰기 목록(Akahu, Binance, Brex, Coinbase, Coinspot, Fio, Kraken, Lunchflow, Mercury, Monobank, OnchainWallet, SimpleFIN, TrueLayer, Up, Wise, FinanceKit)이다. 단 Wise는 다른 provider가 만든 anchor가 이미 있으면 그 anchor의 금액·날짜를 새 잔액으로 제자리에서 바꾼다. 값이 바뀌었는데 재계산이 안 돌면 balances 행은 이전 값 그대로다. (b) current anchor가 있는 연동 계정: 새 값은 캐시 잔액에만 반영되고 balances 행은 anchor 기준으로 계산되므로 둘이 어긋난다. reverse는 캐시 잔액을 쓰지 않으므로 다음 `set_current_balance`가 덮어쓸 때까지 어긋난다. (c) 수동(forward) 계정: 다음 materialize가 캐시 잔액을 계산 결과로 덮어쓴다. Wise processor는 매 sync마다 anchor가 reconciliation으로 굳어 과거가 밀리는 것을 피하려고 일부러 anchor를 만들지 않는다. | 코드 확인 |

**C. 일별 잔액 재구성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | 계정 sync의 잔액 단계 | `Account::Syncer#perform_sync(sync)`는 (1) 시장 데이터 가져오기(예외 삼킴, sync-pipeline R-17), (2) `Balance::Materializer`를 만들어 `materialize_balances`를 부른다. 전략은 `linked?`가 참이면 reverse, 아니면 forward이고 `window_start_date`에 `sync.window_start_date`를 넘긴다(`window_end_date`는 쓰지 않는다). 이 호출의 예외는 삼키지 않는다. (3) 이후 IBKR 덮어쓰기와 anchor-holdings 날짜 진단(예외 삼킴)이 따른다. Materializer를 부르는 곳은 이 외에 보유종목 편집(`security_ids`와 함께, 창 없음)과 SnapTrade 분할 보정이다. 전략은 호출 시점의 `linked?`로 정해진다. | 코드 확인 |
| R-25 | `window_start_date`의 의미 | "이 날짜 이후만 다시 계산해도 된다"는 힌트다. **forward만 읽는다.** reverse와 보유종목 계산은 창을 무시하고 항상 전체를 계산한다. 창이 없으면(null) 전체 계산이다. 창의 시작 날짜는 entry가 바뀔 때 `Entry#sync_account_later`가 정한다. entry를 저장하면 (이 entry가 로드된 뒤 가졌던 가장 이른 날짜, 저장 전 날짜, 현재 날짜) 중 가장 이른 값이고, 삭제하면 시작 날짜 없이(전체) 요청한다. 진행 중이지 않은 `Sync`가 있으면 창은 합쳐진다(sync-pipeline R-05, R-06). **증분 계산은 아래가 모두 참일 때만 한다.** (1) 창이 있다. (2) 계정이 다통화가 아니다(보류가 아닌 entry 중 계정 통화와 다른 통화가 없고 계정 통화 = family 대표 통화). (3) `창 - 1일`의 balances 행(계정 통화)이 있다. (4) 그 행의 `end_non_cash_balance`가 0이다. 하나라도 거짓이면 전체 계산으로 돌아간다(투자·암호화폐 계정은 보유 평가액이 0이 아니면 항상 전체 계산이다). 증분이면: 그 행의 `end_cash_balance`, `end_non_cash_balance`를 시작 잔액으로 쓰고, 계산 범위는 `창 시작`부터 R-31의 끝 날짜까지이며, entry는 창 시작 이후 것만 읽는다. 창 시작이 계산 끝 날짜보다 늦으면 행을 만들지 않고 R-36의 꼬리 정리만 한다. 이 의미는 sync-pipeline이 넘긴 질문 "Account::Syncer가 부르는 Materializer의 window_start_date"에 대한 답이다. | 코드 확인 |
| R-26 | `materialize_balances` 흐름 | 한 DB transaction 안에서 순서대로: (1) 보유종목 materialize(경계, 행 4). 전략은 그대로 넘긴다. (2) 계산기로 balances 행 목록을 만든다(forward 또는 reverse). (3) 2,000행씩 `(account_id, date, currency)` 기준으로 upsert하고 `updated_at`을 현재 시각으로 쓴다. (4) 계산 범위 밖 행을 지운다(R-36). (5) forward일 때만 캐시 잔액을 갱신한다(R-38). 예외가 나면 전체가 되돌려지고 호출자(`Account::Syncer`)로 전파된다(Account `Sync`가 `failed`, sync-pipeline R-17). reverse는 캐시 잔액을 쓰지 않는다. | 코드 확인 |
| R-27 | balances 행의 구조 | 행은 `(account_id, date, currency)`가 유일하다(DB unique). 계산기가 `balance`, `cash_balance`, `start_cash_balance`, `start_non_cash_balance`, 네 흐름 열, 두 조정 열, `net_market_flows`, `flows_factor`를 쓴다. 나머지 열은 DB가 저장 시 계산한다. `end_cash_balance = start_cash_balance + (cash_inflows - cash_outflows) * flows_factor + cash_adjustments`. `end_non_cash_balance = start_non_cash_balance + (non_cash_inflows - non_cash_outflows) * flows_factor + net_market_flows + non_cash_adjustments`. `end_balance`는 둘의 합, `start_balance`는 두 시작 잔액의 합이다. `flows_factor`는 1 또는 -1이어야 한다(모델 검증). 계산기가 쓰는 `balance`, `cash_balance`는 "계산기 변수의 end 값"이고 DB가 계산한 `end_*`와 **항상 같지는 않다.** 같은 경우: forward의 모든 날(Valuation이 있는 날은 조정 열이 차이를 흡수), reverse의 일반 날과 reconciliation waypoint 날, reverse의 opening anchor 다음 날(경계 보정이 조정 열로 흡수). **갈라지는 경우: reverse의 opening anchor 날짜(R-34 (1))**. 같은 날 거래·매매가 있으면 계산기는 `start = end = anchor 금액`, 조정 0으로 두면서 흐름 열에는 그 날 값을 그대로 쓰므로 DB가 계산한 `end_balance`가 anchor 금액에서 흐름만큼 어긋나 `balance` 열과 달라진다. 차트와 R-16의 old_balance는 `end_*` 열을 읽으므로 그 날은 `end_*` 값이 보인다. 이 갈라짐은 실제로 생길 수 있다. opening anchor 날짜를 entry보다 앞서게 하는 검사는 `set_opening_balance`의 날짜 검사(R-13)와 R-14의 금액 0 anchor 이동뿐이고, 금액이 있는 anchor와 같은 날짜(또는 이후에 추가한 과거 날짜)의 entry가 사후에 생기는 것을 막는 검사는 없다. | 코드 확인 |
| R-28 | 계산이 쓰는 entry 집합 | 계정의 entry 중 (a) 보류 거래가 아닌 것(보류 판정은 행 2·provider-import-adapter R-30. 매매와 Valuation은 항상 포함), (b) 분할 원본이 아닌 것(자식 entry를 가진 entry), (c) 날짜가 오늘 이하인 것, 날짜순. `excluded` 플래그(사용자 제외)는 거르지 않는다. 증분이면 창 시작 이후 날짜만. 각 entry 금액은 `entry.date`의 환율(거래·매매의 `extra.exchange_rate`가 있으면 그 값, money R-22)로 계정 통화로 환산하고 통화도 계정 통화로 바꾼다. 환산이 실패한 entry는 제외한다(R-37). 날짜별로 묶어 쓴다. 그 날의 Valuation은 (`get_valuation`) 첫 번째 Valuation entry이고, 흐름 계산은 그 날의 거래·매매 entry만 쓴다. | 코드 확인 |
| R-29 | 현금·비현금 분리와 보유종목 입력 | 총 잔액 하나를 현금과 비현금으로 나눌 때: `investment`는 `현금 = 총액 - 그 날의 보유종목 평가액`, `cash`는 `현금 = 총액`, `non_cash`는 `현금 = 0`이다(비현금 = 총액 - 현금). 현금이 음수가 되어도 자르지 않는다. 그 날의 보유종목 평가액은 계정의 `holdings` 행 중 `date`가 그 날짜인 것의 금액 합이다(각 행은 그 행 날짜의 환율로 계정 통화로 환산, 실패하면 1:1, R-37). 그 날짜에 행이 없으면 0이다(이월하지 않는다). 그래서 보유종목 행이 매일 있어야 투자 계정의 현금·비현금이 맞는다. 이 입력을 만드는 계산은 행 4다. | 코드 확인 |
| R-30 | 하루 흐름 4열 | 그 날의 거래·매매(환산 뒤)로부터: `txn_in` = 금액이 음수인 거래 금액 합(음수), `txn_out` = 금액이 0 이상인 거래 금액 합. 수량이 0이 아닌 매매에서 `trade_in` = 음수 금액 합(매도), `trade_out` = 0 이상 금액 합(매수). 수량이 0인 매매(배당·이자)에서 `income_in`, `income_out`도 같은 방식. `cash` 또는 `investment`: `cash_inflows = abs(txn_in) + abs(trade_in) + abs(income_in)`, `cash_outflows = txn_out + trade_out + income_out`, `non_cash_inflows = trade_out`(매수는 보유 증가), `non_cash_outflows = abs(trade_in)`(매도는 보유 감소). `Loan`: 원금 replay 변화(R-40)가 있으면 `non_cash_inflows = principal_paid`, `non_cash_outflows = principal_added`, 없으면 `non_cash_inflows = abs(txn_in)`, `non_cash_outflows = txn_out`(매매는 무시, 현금 흐름 열은 0). 그 밖의 `non_cash`(Property, Vehicle, OtherAsset, OtherLiability): 네 열 모두 0이다. 투자 계정의 `net_market_flows` = (그 날 보유종목 평가액 - 전날 평가액) - (`non_cash_inflows - non_cash_outflows`), 다른 종류는 0이다. 부호 의미는 money R-36~R-38과 같다. | 코드 확인 |
| R-31 | forward의 범위와 시작 잔액 | 계산 시작일 = (opening anchor 날짜, 보류가 아닌 entry 중 가장 이른 날짜, 오늘) 중 가장 이른 날짜다(anchor가 없으면 R-13의 fallback 날짜). 끝 날짜 = (보류가 아닌 entry 중 날짜가 오늘 이하인 것의 가장 늦은 날짜, 계정의 보유종목 행 중 가장 늦은 날짜) 중 늦은 쪽이고, 둘 다 없으면 오늘이다. 즉 끝은 오늘이 아니라 마지막 활동일이다. 시작일이 끝보다 늦으면 행이 없다. 시작 잔액: 시작일이 opening anchor 날짜보다 이르면(anchor보다 앞선 entry가 있음) 현금 0, 비현금 0이다. 아니면 opening anchor 금액을 R-29로 나눈 값(anchor가 없으면 금액 0)이다. 증분이면 R-25의 행 값이 시작 잔액이다. | 코드 확인 |
| R-32 | forward의 하루 계산 | 시작일부터 끝 날짜까지 달력 날짜마다 하나의 행을 만든다(gap 없음). 그 날 Valuation(kind 무관)이 있으면: `end_cash = R-29로 나눈 현금(Valuation 금액)`, `end_non_cash = Valuation 금액 - end_cash`. 즉 그 날의 거래 흐름은 기록만 하고 잔액에는 적용하지 않고 Valuation 금액이 이긴다. 없으면: `end_cash = start_cash + 부호 있는 흐름`(`non_cash` 종류는 0). `end_non_cash`는 `Loan`이면 `start_non_cash + 부호 있는 흐름`, `investment`면 그 날 보유종목 평가액, 그 밖의 비현금이면 `start_non_cash` 그대로. 부호 있는 흐름 = 그 날 거래·매매 금액 합 `S`에 대해 자산은 `-S`, 부채는 `+S`다(수량이 0이 아닌 매매도 포함). `Loan`에 원금 replay 변화가 있으면 `principal_added - principal_paid`다. 조정: `cash_adjustments = end_cash - start_cash - (cash_inflows - cash_outflows) * flows_factor`(`non_cash` 종류는 0), `non_cash_adjustments = end_non_cash - start_non_cash - (non_cash_inflows - non_cash_outflows) * flows_factor`(`non_cash` 종류만, 그 밖은 0). 행: `balance = end_cash + end_non_cash`, `cash_balance = end_cash`, `start_*` = 전날 end(첫 날은 시작 잔액), `flows_factor` = 자산 1, 부채 -1, 통화 = 계정 통화. | 코드 확인 |
| R-33 | forward의 증분에서 쓰는 purge 하한 | 증분 계산은 계산한 행 범위 앞쪽 행을 유효하다고 보고 남긴다(R-36). 전체 계산으로 돌아갔는지 여부는 계산기가 알려 주고(`incremental?`) Materializer가 그에 맞는 하한을 쓴다. 증분 여부를 계산 전에 묻는 것은 오류다. | 코드 확인 |
| R-34 | reverse의 계산 | 출발: `end` = current anchor 금액(R-18)을 anchor 날짜로 R-29에 따라 나눈 현금·비현금이다. anchor 날짜부터 계산 시작일(R-31과 같은 정의, anchor가 없으면 fallback)까지 하루씩 거꾸로 간다. anchor 날짜가 계산 시작일보다 이르면(예: opening anchor가 current anchor보다 늦은 날짜) 반복이 비어 balances 행이 0개이고, 계산된 행이 없으므로 reverse는 purge도 하지 않는다(R-36, R-50). 매일 R-30의 흐름과 그 날 Valuation을 읽고 다음 중 하나를 적용한다. (1) 계정에 opening anchor가 있고 그 날이 opening anchor 날짜면: `end`를 opening anchor 금액을 나눈 값으로 바꾸고 `start = end`, 조정 0, 시장 변동 0으로 둔다. 이 날 흐름 열(`cash_inflows` 등)에는 그 날 거래·매매의 값을 그대로 쓴다. 즉 "흐름은 잔액에 적용하지 않는다"는 계산기 변수(`start`, `end`)에만 해당하고, DB가 계산하는 `end_*` 열에는 흐름이 적용되므로 같은 날 거래가 있으면 `end_balance`가 anchor 금액과 달라진다(R-27, T-26). (2) 그 날 Valuation이 kind `reconciliation`이면: `end`를 그 금액을 나눈 값으로 재설정하고(waypoint), `start`는 아래 (3)과 같이 그 날 흐름으로 거꾸로 계산한다. (3) 그 밖에는 `start`를 `end`에서 거꾸로 계산한다. 거꾸로 계산: `cash start = end_cash + S'`, `S'`는 자산이면 `S`(그 날 거래·매매 금액 합), 부채면 `-S`(forward의 역). 비현금 `start`는 `Loan`이면 `end_non_cash + S'`, `investment`이면 전날(`date - 1`) 보유종목 평가액, 그 밖은 `end_non_cash` 그대로. 그 날이 opening anchor 날짜의 다음 날이면 경계 보정을 한다. `start`를 opening anchor를 나눈 값(현금, 비현금)으로 덮어쓰고 `cash_adjustments = (비현금 종류면 0, 아니면 end_cash - opening_cash - (cash_inflows - cash_outflows) * flows_factor)`, `non_cash_adjustments = end_non_cash - opening_non_cash - (non_cash_inflows - non_cash_outflows) * flows_factor - net_market_flows`(종류 가드 없음)이다. 즉 opening anchor와 거래 합이 맞지 않는 차이는 그 하루의 조정 열에 모인다. 행의 나머지는 R-32와 같고 다음 반복의 `end`는 이 행의 `start`다. 범위는 anchor 날짜 이하이고, anchor 날짜 뒤(오늘까지)의 entry는 어느 행에도 쓰이지 않는다. current anchor 자신의 Valuation은 (2)가 아니라 (3)으로 처리된다(출발 잔액이 이미 anchor 금액이므로). | 코드 확인 |
| R-35 | 비현금 계정과 부채의 흐름 | `Property`, `Vehicle`, `OtherAsset`, `OtherLiability`는 거래·매매가 잔액을 움직이지 않는다. 흐름 열이 0이고 forward에서 잔액은 Valuation 사이에서 이전 값이 이어진다. `Loan`은 `non_cash`이지만 거래가 부채를 움직인다(양수 금액이 부채 증가, 음수가 감소). `CreditCard`는 `cash`로 처리되고 `flows_factor`가 -1이라 같은 거래 부호가 부채를 늘리고 줄인다. 이 모든 종류의 balances 행 값은 부채가 양수다. | 코드 확인 |
| R-36 | 계산 범위 밖 행 정리(purge) | 계산 직후 `account.balances`에서 다음 행을 통화에 관계없이 지운다. 계산된 행이 있으면: 하한 = (forward이고 증분이면 계산 시작일, 아니면 계산된 행 중 가장 이른 날짜), 상한 = 계산된 행 중 가장 늦은 날짜. `날짜 < 하한` 또는 `날짜 > 상한`인 행을 지운다. 계산된 행이 없으면: forward이고 증분이고 계산 시작일 <= `창 시작 - 1일`일 때만 `날짜 < 계산 시작일` 또는 `날짜 > 창 시작 - 1일`인 행을 지운다(미래 날짜 행 정리). 그 밖에는 아무것도 지우지 않는다. 지우는 조건에 통화가 없으므로 범위 안에 남은 이전 통화의 행은 그대로이고(다음 upsert가 새 통화 행을 따로 만든다), 차트·캐시 갱신은 계정 통화 행만 읽는다(R-38, R-46). reverse는 anchor 날짜보다 늦은 행도 지운다. | 코드 확인 (이전 통화 행이 남는 결과는 추론) |
| R-37 | 환산 실패 정책 (이 스펙에서 만나는 경우) | 실패(`ConversionError`, 환율을 못 찾음)를 호출처가 다르게 처리한다. 정책은 하나로 통일돼 있지 않다. (a) **entry 환산(잔액 계산)**: 그 entry를 계산에서 뺀다(1:1로 쓰면 환율 간격만큼 잔액이 틀리기 때문). 제외한 건수와 통화 쌍 목록을 `DebugLogEntry`(category `sync`, level `warn`, source `Balance::SyncCache`, 메시지 `Excluded N entry from balance calculation: no exchange rate available`, metadata `missing_rate_pairs` = `FROM->TO` 목록과 `unconvertible_entry_count`, 계정·family 연결)로 남긴다. 계산은 계속한다. (b) **보유종목 평가액 환산**: 1:1(원래 금액)로 쓴다(빼면 `총액 - 평가액`으로 구하는 현금이 가짜로 늘기 때문). 같은 형식으로 건수와 쌍을 기록한다(`unconvertible_holding_count`, 메시지 `Valued N holding at a 1:1 rate: no exchange rate available`). (c) **예정 entry 투영**(R-39): 그 entry를 뺀다. 기록은 없다. (d) **연동 거래소 계정 생성 시 제공자 잔액 환산**(`convert_provider_balance`): 없음(nil)을 받아 0으로 쓴다. 곧 이어지는 첫 sync가 환산한 값을 쓴다. (e) **BalanceSheet의 계정 잔액**(R-42): 0으로 만들어 합계에서 빠지게 한다(행에는 자기 통화 잔액이 보인다). (f) **순자산 시계열**(R-46): 그 날 그 계정의 환율이 NULL이라 합에서 뺀다(1로 계산하지 않는다). (g) **Property의 family 통화 추세**(표시용): 저장된 환율이 없으면 값을 만들지 않는다(nil). 환율 조회·fallback 규칙 자체는 money R-25~R-27이다. | 코드 확인 |
| R-38 | 캐시 잔액의 소유자 | 쓰는 곳(대표): forward Materializer(R-26 마지막 단계, 아래), `set_current_balance`(`balance`만, R-19~R-21), `update_balance`(`balance`와 `cash_balance`, R-23), 연동 provider processor가 직접(`cash_balance`, 통화 포함), 계정 생성(R-05의 입력). forward Materializer는 `balances`에서 계정 통화 행 중 날짜가 오늘 이하인 가장 최근 행을 읽어 `balance = end_balance`, `cash_balance = end_cash_balance`로 쓴다. 그런 행이 없으면 둘 다 0이다. 읽는 곳(대표): BalanceSheet(R-42), 수동 `set_current_balance`의 delta(R-21), 수정 폼의 변경 판정(R-08), `projected_balance_money`(R-39), 목표의 `free_to_earmark`(`balance - 고정 배정액`), Property·Vehicle 추세(현재 값). reverse 연동 계정의 캐시 잔액은 sync가 갱신하지 않는다. 그 값은 연동이 마지막으로 쓴 것이다. | 코드 확인 (읽고 쓰는 곳의 목록은 대표, 2.1) |
| R-39 | 예정(미래 날짜) entry | 날짜가 오늘보다 늦은 entry는 `scheduled`다. 잔액 계산에서 완전히 빠지고(R-28), forward 끝 날짜는 오늘 이하 활동일까지이며(R-31), 캐시 갱신도 오늘 이하 행만 읽는다. 표시용 투영: `Account#scheduled_entries_total_money(through_date=nil)` = 보류도 분할 원본도 아닌, 날짜가 오늘보다 엄격히 늦은(`date > 오늘`, 오늘 날짜는 포함하지 않는다. `through_date`가 있으면 그 날짜 이하인) 거래와 수량 0인 매매의 계정 통화 환산 금액에 대해 자산이면 `-금액`, 부채이면 `+금액`을 합한 Money다. 수량이 0이 아닌 매매는 뺀다(보유와 현금 사이 이동이라 총액이 안 바뀐다). `non_cash`이면서 `Loan`이 아닌 계정은 0이다. 환산 실패 entry는 뺀다(R-37 c). `projected_balance_money = 캐시 잔액 + 이 합계`. 인스턴스당 한 번 계산해 재사용한다. 그 날짜가 오면 다음 sync가 잔액에 넣는다(그 날짜에 sync를 예약하는 job은 행 2·sync). | 코드 확인 |
| R-40 | Loan 원금 replay 경계 (이 스펙은 인터페이스만) | 계산기는 `Loan::PrincipalPayments#change_for(date)`가 돌려주는 `Change(principal_paid, principal_added, interest_paid)`가 있으면 R-30, R-32의 흐름을 그 값으로 대신한다(`net = principal_added - principal_paid`). 이 값이 만들어지는 조건: 계정이 대출이고 상환 일정을 만들 수 있고(`amortizable?`) 수동 계정이고 opening anchor가 있어 금액이 양수이고 `loan.initial_balance`가 양수이고 anchor 날짜가 대출 시작일(`origination_date`)과 같고 anchor 금액이 `original_balance`와 통화 소수 자릿수 기준으로 같으며, 또한 family의 구성원 중 하나라도 preview 기능을 켠 경우다. 그렇지 않으면 replay 변화가 없고 R-30의 일반 규칙이 쓰인다. 일정·이자 계산·유예 기간·보험료를 푸는 알고리즘은 이 스펙의 범위 밖이다(이유는 1.2의 제외 항목: 별도 엔진이고 preview 사용자에게만 켜진다). 대출의 balance 입력 속성(`SCHEDULE_INPUTS`, 보험료, `initial_balance`, `principal_only_transfers`)이 바뀌어 저장되면 commit 뒤 계정 sync를 요청하고, 실행 중인 sync가 있으면 그 sync에 `full_resync_requested`를 표시한다(sync-pipeline R-12). | 코드 확인 (알고리즘은 열람만, 범위 밖) |

**D. BalanceSheet(현재 합계)와 시계열**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-41 | 현재 합계 대상 계정 | `BalanceSheet(family, user)`의 계정 목록은 family 계정 중 상태가 `draft` 또는 `active`(`visible`)인 것이다. `user`가 있으면(없으면 로그인 사용자, 그것도 없으면 제한 없음) 그 사용자가 접근할 수 있는(소유했거나 공유받은, 권한 종류 무관) 계정만이다. 계정마다 `included_in_finances`(user가 없으면 참, 있으면 소유했거나 `include_in_finances`가 참인 공유를 받은 계정)와 `exclude_from_reports`를 함께 가진다. 합계에 들어가는 계정(counted)은 `included_in_finances`가 참이고 `exclude_from_reports`가 거짓인 계정이다. 자산 목록과 부채 목록은 `accounts.classification` 기준이다. 계정 id 목록은 cache에 두고 family 데이터가 바뀌면 무효화한다(구현 상세는 Family 계약). | 코드 확인 |
| R-42 | 계정별 환산 잔액 | 캐시 잔액을 쓴다(`balances` 행이 아니다). 계정 통화 = family 통화이면 그대로, 아니면 목록의 외화 통화 전체에 대해 `rates_for(외화들, to: family 통화, date: 오늘)`(money R-27) 한 번으로 환율을 구해 `balance * 환율`이다. 환율이 없으면 0이다(R-37 e). | 코드 확인 |
| R-43 | 자산·부채·순자산·그룹 | 자산 합계 = 자산 계정 중 counted인 것의 환산 잔액 합, 부채 합계 = 부채 계정 중 counted인 것의 환산 잔액 합(부채는 양수). `net_worth = 자산 합계 - 부채 합계`. 모두 family 통화다. 계정 그룹은 분류(자산, 부채) 안에서 `accountable_type`별로 묶는다. 그룹의 순서는 `Accountable::TYPES` 순서(Depository, Investment, Crypto, Property, Vehicle, OtherAsset, CreditCard, Loan, OtherLiability)다. 그룹의 `total`도 counted 계정 합이다. 그룹의 `weight` = 그룹 합계 / 그 분류의 합계 * 100이고 분류 합계가 0이면 0이다. 그룹과 목록에는 counted가 아닌 계정도 행으로 들어 있다. 환산 규칙은 money R-41(1)을 따른다. | 코드 확인 |
| R-44 | 계정 정렬 | 각 분류의 계정 목록은 사용자의 `account_order` 키로 정렬한다(없으면 `name_asc`): `name_asc`(이름 소문자, 같으면 id), `name_desc`(그 역순), `balance_asc`(환산 잔액, 같으면 id), `balance_desc`(그 역순), `manual`(사용자가 끌어다 둔 그룹별 위치가 있는 계정이 먼저, 위치 순서대로, 나머지는 이름 소문자 순), 그 밖의 키는 정렬하지 않는다. `PATCH /accounts/reorder`가 사용자별 그룹별 순서를 저장한다. 그룹 키가 9종 종류 이름(snake_case)이 아니거나 계정 id 목록이 배열이 아니면 저장하지 않고 422를 돌려준다. 요청 id 중 사용자가 접근할 수 있고 그 종류인 것만, 중복을 빼고, 상한(`MANUAL_ACCOUNT_ORDER_LIMIT`)까지 요청 순서대로 저장하며 성공하면 200이다. | 코드 확인 |
| R-45 | 동기화 중 표시 | `syncing?` = family의 `visible` 계정 중 보이는(visible) `Sync`(sync-pipeline R-04)가 있는 계정이 하나라도 있음이고, 계정별 `syncing?`도 같은 집합이다. 집합은 family의 `latest_sync_activity_at`을 키에 넣어 cache한다. | 코드 확인 |
| R-46 | 순자산 시계열 (`BalanceSheet#net_worth_series(period=최근 30일)`) | 대상 계정은 `historical`(`draft`, `active`, `disabled`)이고 `exclude_from_reports`가 거짓인 family 계정이다(user가 있으면 소유했거나 `include_in_finances`가 참인 공유를 받은 계정으로 한정). 비활성(`disabled`) 계정은 `(disabled_at, 없으면 updated_at)`의 날짜 - 1일까지만 합에 들어간다(`pending_deletion`은 대상이 아니다). 날짜: 기간의 `start_date`부터 `end_date`까지 `interval` 간격 날짜에 `end_date`를 반드시 더한다. 기간 간격(`interval`)은 기간이 5년 넘으면 `1 month`, 1년 넘으면 `1 week`, 아니면 `1 day`다. 각 날짜 `d`와 계정마다: 날짜가 `d` 이하인 가장 최근 balances 행(통화 = 계정 통화)이 없으면 그 날 합에서 빠진다. 환율은 계정 통화 = family 통화면 1, 아니면 `d` 이하의 가장 최근 양수 환율, 없으면 `d` 이후의 가장 이른 양수 환율, 그래도 없으면 없음이라 계정이 그 날 합에서 빠진다. 값 = `Σ end_balance * flows_factor * 환율`(부채는 `flows_factor`가 -1이라 뺀다). 추세(`trend`)의 이전 값은 같은 행의 `start_balance * flows_factor * 환율` 합이다. 결과는 `Series`(날짜, 포맷된 날짜, family 통화 Money, 추세 목록)다. 합에 들어가는 계정이 하나도 없는 날의 값은 0이다. SQL은 C-15다. 이 시계열의 마지막 점과 `BalanceSheet#net_worth`는 같지 않을 수 있다(시계열은 `balances` 행과 비활성 계정을 쓰고, 현재 합계는 캐시 잔액과 `draft`, `active`만 쓴다). | 코드 확인 |
| R-47 | 시계열 cache | 시계열 결과는 cache에 두고, 키에 다음을 넣는다. family cache 키(family 데이터 변경 시 무효화, 세부는 Family 계약), `CONVERSION_CACHE_VERSION`(`fx2`, money R-28), `exchange_rates`의 가장 최근 `updated_at`(늦게 들어온 환율이 빠졌던 계정을 되살리기 때문), 사용자 id, 사용자의 공유 행 중 가장 최근 `updated_at`, 계정 부분집합이면 그 id 목록의 해시, 기간의 시작·끝 날짜. | 코드 확인 |
| R-48 | 계정 하나의 잔액 차트 (`balance_series(period, view, interval)`) | R-46과 같은 SQL을 계정 하나(`account_ids = [id]`)에 대해 계정 통화로 실행한다(환율 1). `favorable_direction`은 자산 `up`, 부채 `down`이고 `down`이면 값에 -1을 곱한다. 부채는 `flows_factor`(-1)와 -1이 겹쳐 양수(갚을 크기)로 나온다. `view`는 `balance`(`end_balance`/`start_balance`), `cash_balance`(`end_cash_balance`), `holdings_balance`(자산의 `end_non_cash_balance`), `gains`(행 4, 이 스펙 밖) 중 하나이고 그 밖은 오류다. 기간 기본값은 최근 30일(`[오늘 - 30일, 오늘]`)이다. 연동된 투자 계정의 결과는 정규화기를 거친다(행 4). | 코드 확인 |
| R-49 | `Accountable.balance_money(family)` (사용되지 않음) | 클래스 메서드로 존재한다: 한 종류의 `active` 계정(`draft`, 사용자 접근, `exclude_from_reports`는 보지 않는다)의 캐시 잔액을 family 통화로 환산해 합한다(환율 없으면 0, money R-41(1)과 같은 방식). 호출처를 `app`, `lib`에서 찾지 못했다. R-43이 쓰는 경로와 필터가 다르다. 재구현에 필요하지 않다. | 코드 확인 (호출처 없음, 검색 범위 2.1) |
| R-50 | reverse의 빈 계산 범위 | R-34의 빈 반복과 R-36의 "계산된 행이 없음" 분기가 만나는 경우다. 계산된 행이 없으면 forward 증분의 꼬리 정리만 있고 reverse는 어떤 행도 지우지 않는다. 이전 계산의 balances 행이 그대로 남는다. | 코드 확인 |
| R-51 | 기본 계정 지정 | `PATCH /accounts/:id/set_default`는 `eligible_for_transaction_default?`가 참(`Depository` 또는 `CreditCard`이고, `active`이고, 연동되지 않음)일 때만 현재 사용자의 `default_account`로 저장한다. 아니면 지정하지 않고 경고와 함께 계정 목록으로 돌려보낸다. `PATCH /accounts/:id/remove_default`는 현재 사용자의 `default_account`를 비운다. 두 요청은 사용자가 접근할 수 있는 계정이면 되고 소유자·`full_control` 같은 관리 권한 검사는 없다(근거는 2.1 R-51). 지정된 계정이 삭제되면 DB가 `users.default_account_id`를 null로 만든다(R-10). 지정값을 쓰는 곳(거래 입력 기본 계정)은 행 2다. | 코드 확인 |
| R-52 | Valuation 삭제 | `DELETE /valuations/:id`(`EntryableResource#destroy`)는 entry를 지우고 창 없는 계정 sync를 요청한다. kind 검사가 없어 opening anchor와 current anchor도 삭제된다. opening anchor가 삭제되면 R-13의 fallback 날짜와 금액 0이, current anchor가 삭제되면 R-18의 fallback(캐시 잔액, 오늘)이 적용된다. 삭제 권한은 계정의 소유자 또는 `full_control` 공유자다. | 코드 확인 |

- 불변식:
  - 모든 balances 행에서 `end_*` 열은 `start_*`, 흐름, 조정, 시장 변동으로 정해지는 값이다(DB가 계산). 계산기는 변수의 end 값을 `balance`, `cash_balance`로 따로 쓴다. 둘이 같다는 보장은 reverse의 opening anchor 날짜에 같은 날 거래가 있으면 성립하지 않는다(R-27).
  - 같은 계정·통화에서 balances 행이 있는 날짜는 계산 범위 안에서 빈 날 없이 연속이다(forward는 시작일부터 끝 날짜까지, reverse는 anchor 날짜부터 시작일까지).
  - forward에서 Valuation이 있는 날의 `end_balance`는 Valuation 금액이다(그 날 환산 실패로 Valuation이 제외된 경우는 예외, R-28). reverse에서는 current anchor 날짜(출발 잔액)와 reconciliation 날짜의 `end_balance`가 해당 금액이다. opening anchor 날짜는 같은 날 거래·매매가 없을 때만 `end_balance`가 anchor 금액이다(계산기의 `balance` 열은 항상 anchor 금액).
  - 부채 계정의 `balance`와 balances 행의 end 값은 갚을 크기를 양수로 둔다.
  - 한 계정의 Valuation entry는 날짜당 하나다.
- 미결정: 없음. provider-import-adapter U-01은 R-22, R-23으로 닫았다. 이 스펙은 선행 스펙 세 개가 모두 `draft`이므로 `draft`다.
- 확인 한계:
  - 실행하지 않았다(금지). 계산 예시는 코드를 손으로 따라가 도출했다(T-ID는 모두 구현에서 도출, 원본 테스트 미열람).
  - 상태 기계 라이브러리(AASM)의 `timestamps` 옵션, 프레임워크의 transaction 되돌림·`first` 정렬·callback 실행 순서는 레포 밖 의미다(R-09, R-12, R-20).
  - `Family#build_cache_key`, 사용자의 `account_order`·`manual_account_order` 저장 형식, `AccountShare` 권한 검증의 세부는 Family 테넌시 계약(미작성)이라 열지 않았다.
  - `Date.current`가 어떤 시간대인지(웹 요청은 family 시간대로 전환, sync job의 시간대는 sync-pipeline이 다룬다)는 호출 문맥에 달려 있다. 이 스펙은 money-currency-rules의 "오늘" 전제를 따른다.

### 1.5 필수 코드 참조 [필수]

라이선스는 AGPL-3.0(overview 1절)이다. 아래 C-ID는 줄 범위 안내이고 코드를 복사하지 않았다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/concerns/accountable.rb:1-12` `Accountable::TYPES`, `from_type`; `db/schema.rb:99-139` `accounts`(`:105` generated `classification`) | 종류 9종 목록과 accounts 열·제약, 부채 판정식 | R-01, R-03 |
| C-02 | `app/models/depository.rb:6-13`, `app/models/investment.rb:9-97`, `app/models/loan.rb:4-12`, `app/models/property.rb:4-15`, `app/models/crypto.rb:7-10`, `app/models/credit_card.rb:6-8` `SUBTYPES` | 종류별 subtype 키 목록(Investment는 약 80개와 subtype별 `tax_treatment`). 데이터 표라 코드가 글보다 짧다 | R-04 |
| C-03 | `app/models/account.rb:81-102`, `:115-119`, `:166-174`, `:226-269` | 분류 enum, `VISIBLE_STATUSES`, `HISTORICAL_STATUSES`, 조회 범위, `accessible_by`(소유 또는 공유), `included_in_finances_for`(소유 또는 `include_in_finances` 공유), 상태 기계 이벤트와 전이 | R-09, R-41, R-46 |
| C-04 | `app/models/account.rb:286-348` `Account.create_and_sync` | 생성 단계 순서와 분기 | R-05 |
| C-05 | `app/models/account/current_balance_manager.rb:13-217` | current anchor 읽기·쓰기, 수동 전략 두 가지, 연동 경로의 잠금·회전·과거 명세서 분기 | R-18~R-21 |
| C-06 | `app/models/account/opening_balance_manager.rb:8-124` | opening anchor 조회·생성·갱신, 날짜 오류, 기본 날짜 | R-13 |
| C-07 | `app/models/account/reconciliation_manager.rb:9-134` | reconciliation 쓰기, dry-run, 결과 필드, 현금 도출, delta | R-16, R-17 |
| C-08 | `app/models/account/anchorable.rb:12-89`, `app/models/account/reconcileable.rb:4-14` | 공개 연산과 sync 요청 지점, 이른 entry 앞 anchor 이동, `history_start_date` | R-13~R-15, R-17, R-19 |
| C-09 | `app/models/balance/materializer.rb:16-123` | 실행 순서, upsert 배치, purge 조건, 캐시 갱신 | R-26, R-36, R-38 |
| C-10 | `app/models/balance/base_calculator.rb:41-43`, `:50-68`, `:70-210` | 계산 시작일, 대출 원금 변화 경계(`loan_principal_payments` 조건), 현금 분리, 조정 열 공식, 하루 흐름 4열, 부호 있는 흐름의 공통 틀 | R-29, R-30, R-35, R-40 |
| C-11 | `app/models/balance/forward_calculator.rb:8-160` | forward 범위, 시작 잔액, 일별 계산, 증분 조건 | R-25, R-31, R-32 |
| C-12 | `app/models/balance/reverse_calculator.rb:3-167` | reverse 출발, 세 분기, 경계 보정 | R-34 |
| C-13 | `app/models/balance/sync_cache.rb:26-161` | entry 집합 조건, 환산, 제외·1:1 정책, 보유종목 평가액 합, 환산 실패 보고(`report_missing_rates`) | R-28, R-29, R-37 |
| C-14 | `db/schema.rb:257-282` `balances` | 열, generated column 식, unique 인덱스 | R-27 |
| C-15 | `app/models/balance/chart_series_builder.rb:148-246` | 순자산·계정 차트 SQL(날짜 생성, 계정 활성 구간, 최근 행 lateral, 환율 lateral) | R-46, R-48 |
| C-16 | `app/models/balance_sheet.rb:13-43`, `:66-105`; `app/models/balance_sheet/account_totals.rb:31-111`; `classification_group.rb:25-59`; `account_group.rb:36-46`; `historical_account_scope.rb:11-14`; `net_worth_series_builder.rb:11-71` | 대상 계정 조건, counted, 합계·그룹·정렬, 시계열 대상·비활성 종료일·cache 키 | R-41~R-47 |
| C-17 | `app/models/valuation.rb:4-25`, `app/models/valuation/name.rb:1-102` | kind enum, 고정 이름 문구 | R-12 |
| C-18 | `app/models/entry.rb:62-65`, `:131-155`, `:378-384`, `:430-432`, `:684-686`, `:787`, `:811-815` | entry 검증, `excluding_pending`, `excluding_split_parents`, 미래 날짜 조건, 창 시작 날짜 규칙(`sync_account_later`, 일괄 수정 경로의 창 계산 `:787`, `track_earliest_saved_date`), `min_supported_date` | R-12, R-25, R-28, R-39 |
| C-19 | `app/models/account.rb:41-79`, `:970-1005` | 예정 entry 투영과 projected balance | R-39 |
| C-20 | `app/models/account/syncer.rb:8-24` | 전략 선택과 호출 순서 | R-24 |
| C-21 | `app/models/loan/principal_payments.rb:24-60`, `:70` | `Change` 구조, 생성 조건, `change_for` 인터페이스만 | R-40 |
| C-22 | `app/controllers/concerns/accountable_resource.rb:198-206`; `credit_cards_controller.rb:4-13`; `loans_controller.rb:4-10`; `vehicles_controller.rb:4-8`; `investments_controller.rb:4`; `cryptos_controller.rb:4`; `properties_controller.rb:33-46`(Property의 `update`), `:287-298`(Property 허용 키) | 폼이 받는 계정·종류별 속성 화이트리스트와 Property의 별도 수정 경로 | R-04, R-05, R-08 |
| C-23 | `app/models/account/chartable.rb:5-27` | `favorable_direction`(자산 `up`, 부채 `down`), `balance_series`의 `view` 검증(네 값 밖은 오류)과 builder 구성 | R-48 |
| C-24 | `app/models/account.rb:883-889`; `app/controllers/accounts_controller.rb:284-297` | `supports_default?`, `eligible_for_transaction_default?`, 기본 계정 지정·해제 | R-51 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드를 손으로 따라 계산, 실행하지 않았다). 아래 모든 사례의 오늘은 2026-11-18, family 통화 USD, 계정 통화 USD, 환율·보유종목 행은 따로 적지 않으면 없다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05, R-13, R-31 | Depository를 `balance 1000`, `opening_balance_date 2026-11-10`으로 생성하고 sync | opening anchor entry(kind `opening_anchor`, 이름 `Opening balance`, 금액 1000, 날짜 11-10, 통화 USD) 하나, `cash_balance 1000`, reconciliation 없음. balances 행은 11-10 하나(시작일 = 끝 날짜 = 11-10), `end_balance 1000`. 캐시 잔액 1000 |
| T-02 | R-30, R-32, R-38 | T-01 뒤에 거래 +30(11-12), -200(11-15)를 넣고 전체 sync | 행은 11-10~11-15 여섯 개. end: 11-10 1000, 11-11 1000, 11-12 970(`cash_outflows 30`), 11-13 970, 11-14 970, 11-15 1170(`cash_inflows 200`). 캐시 잔액 1170. 11-15 이후 행 없음 |
| T-03 | R-32 | T-02에 11-11 reconciliation 900 추가 후 sync | 11-11: `end 900`, `cash_adjustments = 900 - 1000 - 0 = -100`. 11-12 870, 11-15 1070. 캐시 잔액 1070 |
| T-04 | R-32, R-35 | CreditCard를 `balance 500`(opening anchor 11-10)으로 생성, 거래 +100(11-12, 카드 사용), -300(11-14, 납부)을 넣고 sync | `flows_factor -1`. 11-10 500, 11-12 600(`cash_outflows 100`: `500 + (0 - 100) * -1`), 11-13 600, 11-14 300(`cash_inflows 300`). 캐시 잔액 300(부채가 양수) |
| T-05 | R-29, R-30, R-32 | Investment에 opening anchor 1000(11-10). 보유종목 행(다른 스펙이 만든 것으로 가정): 11-11 값 300, 11-12 값 330. 매수 매매 금액 +300, 수량 2(11-11)가 있다. forward | 11-10: 현금 1000, 비현금 0. 11-11: 현금 700(`1000 - 300`), 비현금 300(보유종목 값), `balance 1000`, `non_cash_inflows 300`, `net_market_flows = (300 - 0) - (300 - 0) = 0`. 11-12: 현금 700, 비현금 330, `balance 1030`, `net_market_flows = (330 - 300) - 0 = 30`. 끝 날짜 = 보유종목 마지막 날짜 11-12. 캐시 잔액 1030, `cash_balance 700` |
| T-06 | R-35, R-32 | Property(opening anchor 300,000, 2020-01-01), reconciliation 350,000(2024-06-01), 거래 +5,000(2023-03-01) | 2020-01-01~2024-05-31 행의 `end_balance` 300,000. 거래일 행의 흐름 열은 모두 0. 2024-06-01 행 350,000(`non_cash_adjustments 50,000`). 끝 날짜 = 2024-06-01(마지막 entry). 캐시 잔액 350,000 |
| T-07 | R-34 | 연동 Depository: opening anchor 700(11-01), current anchor 1000(11-18), 거래 -200(11-17), +50(11-15). reverse | 11-18 end 1000. 11-17 end 1000, start 800(`1000 + (-200)`). 11-16 800. 11-15 start 850(`800 + 50`). 11-14~11-03 850. 11-02: start를 opening 700으로 덮고 `cash_adjustments = 850 - 700 - 0 = 150`. 11-01: end = start = 700. 행은 11-01~11-18. 캐시 잔액은 바뀌지 않는다 |
| T-08 | R-18, R-22, R-23 | T-07의 계정에서 current anchor가 없고 캐시 잔액 1000이다. 이어서 anchor가 있는 상태에서 `update_balance(1500)` | anchor가 없을 때: T-07과 같은 행(출발 잔액 1000, 날짜 오늘), 읽을 때마다 `No current balance anchor found ...` 경고. anchor가 있을 때: 캐시 잔액만 1500이고 balances 행은 그대로(11-18 end 1000), 어긋난 상태 |
| T-09 | R-20 | 연동 계정의 current anchor(11-17, 900). `set_current_balance(1000)`(날짜 없음)을 부르고, 이어서 같은 날 `set_current_balance(1100)` | 첫 호출: 기존 anchor entry가 kind `reconciliation`, 이름 `Manual balance update`로 바뀌고, 새 anchor entry(11-18, 금액 1000, 이름 `Current balance`)가 생기고, 캐시 잔액 1000, `success?` 참, `historical?` 거짓, sync 요청. 둘째 호출: anchor가 같은 날짜라 새 entry 없이 금액만 1100으로 갱신, 캐시 잔액 1100 |
| T-10 | R-20 | anchor(11-18, 1000)가 있는 연동 계정에 `set_current_balance(950, date: 2026-11-10)` | 11-10 reconciliation 950 생성(그 날 Valuation이 있으면 갱신). anchor와 캐시 잔액(1000) 그대로. `historical?` 참 |
| T-11 | R-21 | 전제: 두 계정 모두 sync가 끝나 캐시 잔액이 계산 결과와 같은 상태다. 수동 Depository(opening anchor 1000, 11-01, reconciliation 없음, 캐시 잔액 1000) `set_current_balance(1200)`. 같은 계정에 reconciliation(900, 11-03)이 이미 있는 경우도(그때 캐시 잔액은 sync 결과 900) | 앞의 경우: delta = 1200 - 1000 = 200이라 opening anchor 금액이 1200으로 바뀌고 새 Valuation 없음, 캐시 잔액 1200, sync 요청. 뒤의 경우: 오늘(11-18) reconciliation 1200이 생기고 opening anchor는 그대로 |
| T-12 | R-13 | 계정에 opening anchor(2026-02-01)와 anchor가 아닌 entry 중 가장 이른 날짜 2026-03-01이 있다. `set_opening_balance(balance: 100, date: 2026-03-01)`, 이어 `date: 2026-02-28` | 첫 호출: 실패, 메시지 `Opening balance date must be before the oldest entry date`, 아무것도 안 바뀐다. 둘째 호출: 성공, anchor가 금액 100, 날짜 02-28로 갱신, `changes_made?` 참 |
| T-13 | R-05, R-32 | Loan을 `balance 8000`, `initial_balance 10000`, `start_date 2024-11-18`로 생성(폼 opening 날짜는 다른 값) | opening anchor(10000, 날짜 2024-11-18, 이름 `Original principal`), 오늘 날짜 reconciliation(8000, 이름 `Manual principal update`). sync 뒤 2024-11-18~2026-11-17 행의 `end_balance` 10000, 2026-11-18 행 8000(`non_cash_adjustments -2000`) |
| T-14 | R-25 | USD 계정(family도 USD), 기존 balances 행이 있고 `end_non_cash_balance`가 0이다. 거래를 11-15로 저장하고 sync. 이어서 그 거래 날짜를 11-10에서 11-15로 옮긴 경우, 그리고 계정이 EUR인 경우 | 첫째: 창 시작 11-15, 11-14 행에서 시작 잔액을 읽고 11-15 이후만 재계산, 그 이전 행은 그대로. 둘째: 창 시작 11-10. 셋째: 다통화이므로 창을 무시하고 전체 재계산 |
| T-15 | R-41~R-43 | family USD. Checking USD 1,000(자산), Savings EUR 500(자산, 오늘 EUR→USD 1.1), Home USD 200,000(Property), Card USD 300(CreditCard), Old USD 777(`disabled`), Hidden USD 999(`exclude_from_reports`), `pending_deletion` 계정 하나. 사용자 지정 없이 | 목록에 Old와 `pending_deletion` 계정은 없다. Hidden은 목록에 있고 합계에 안 들어간다. 자산 합계 `1000 + 550 + 200000 = 201,550`, 부채 합계 300, `net_worth 201,250`. EUR 환율이 없으면 Savings는 0으로 합산: 자산 201,000, `net_worth 200,700`(Savings 행은 `500 EUR`로 보인다) |
| T-16 | R-46 | 기간 11-01~11-18(`1 day`), 계정 A(USD, active, 11-01부터 행이 있고 end_balance 1000), 카드 B(USD, `flows_factor -1`, end_balance 300), 계정 C(USD, disabled, `disabled_at` 2026-11-10, end_balance 500) | 11-09까지의 날짜는 `1000 - 300 + 500 = 1200`, 11-10부터는 `1000 - 300 = 700`. 마지막 점(11-18) 700. 현재 `net_worth`는 C를 포함하지 않으므로 700이고 캐시 잔액이 다르면 둘이 다를 수 있다 |
| T-17 | R-28, R-37 | USD 계정에 EUR 거래 +100(11-12)이 있고 EUR→USD 환율이 저장돼 있지 않으며 provider도 없다 | 그 거래는 계산에서 빠지고 11-12 행의 흐름 열은 0. `DebugLogEntry`(category `sync`, level `warn`, source `Balance::SyncCache`, 메시지 `Excluded 1 entry from balance calculation: no exchange rate available`, `missing_rate_pairs ["EUR->USD"]`, `unconvertible_entry_count 1`). 같은 상황의 보유종목은 1:1로 합산하고 `Valued 1 holding at a 1:1 rate ...` 기록 |
| T-18 | R-09 | active 계정을 `toggle_active`, 다시 `toggle_active`, 이어 disabled 상태에서 `mark_for_deletion`, 삭제가 실패 | 첫 호출 `disabled`(`disabled_at` 기록), 둘째 `active`(`disabled_at` 비움). `mark_for_deletion`은 `pending_deletion`(이전 `disabled_at` 유지). 실패하면 `disabled`로 돌아가고 `disabled_at`은 원래 값. 목록(visible)에서는 `pending_deletion`이 빠진다 |
| T-19 | R-10 | 연동 계정에 `DELETE /accounts/:id` | 거부, 경고. 수동 계정이면 `pending_deletion`으로 바뀌고 삭제 job이 큐에 들어간다. job 뒤 계정, entries, balances, holdings, 공유가 없고, 이 계정 거래에 연결된 `Transfer`도 없고, 계정에 붙었던 명세서는 `account_id`가 비고 `review_status`가 `unmatched` |
| T-20 | R-16 | 11-12 balances 행의 `end_balance`가 970, `end_cash_balance`가 970. `reconcile_balance(balance: 900, date: 11-12, dry_run: true)` | 저장 없음. `old_balance 970`, `old_cash_balance 970`, `new_balance 900`, `new_cash_balance = 900 - (970 - 970) = 900`. 행이 없는 날짜로 호출하면 old·new_cash가 없다 |
| T-21 | R-12, R-16 | 계정에 11-03 reconciliation이 이미 있다. `reconcile_balance(800, 11-03)` | 두 번째 entry를 만들지 않고 기존 entry의 금액을 800으로 갱신한다. 같은 날짜의 Valuation entry를 직접 하나 더 저장하면 날짜 유일성 검증이 실패한다 |
| T-22 | R-12 | 오늘 2026-11-18에 Valuation entry를 날짜 1996-11-18, 1996-11-19로 저장 | 1996-11-18은 검증 실패(오늘 - 30년과 같으면 안 된다), 1996-11-19는 성공 |
| T-23 | R-08 | 폼 `balance`가 캐시 잔액과 같은 계정 수정, 다른 값으로 수정, 다른 값이지만 속성 검증이 실패하는 수정 | 같으면 `set_current_balance`를 부르지 않는다. 다르면 R-19~R-21. 속성 검증이 실패하면 잔액 변경까지 되돌아가고 422 |
| T-24 | R-39 | Depository 캐시 잔액 1000, 거래 +40(2026-11-25, 보류 아님) | balances 행·캐시 잔액에 영향이 없다. `scheduled_entries_total_money = -40`, `projected_balance_money = 960`. `through_date`가 2026-11-24면 합계 0 |
| T-25 | R-22, R-24 | 새 연동이 Investment 계정에 총액 5,000, 현금 1,200을 넣는다(정본 순서) | 계정에 통화와 `cash_balance 1200`을 저장하고 `set_current_balance(5000)`이 current anchor(금액 5000)와 캐시 `balance 5000`을 쓰고, sync를 요청한다. reverse 재계산이 anchor 날짜에 `end_balance 5000`을 만든다. `cash_balance`는 sync가 갱신하지 않는다 |
| T-26 | R-27, R-34 | 연동 Depository: opening anchor 700(11-01), current anchor 1000(11-18), 거래 +50(11-01, anchor와 같은 날). reverse | 11-01 행: 계산기 변수 `start = end = 700`, 조정 0이고 `cash_outflows 50`이 행에 기록된다. DB가 계산한 `end_cash_balance = 700 + (0 - 50) * 1 + 0 = 650`이고 계산기가 쓴 `balance` 열은 700이다. 차트는 11-01을 650으로 보인다. 11-02 행: `start`는 opening 700으로 덮이고 `cash_adjustments = 1000 - 700 - 0 = 300`, `end_balance 1000` |
| T-27 | R-52, R-13, R-31 | 수동 Depository: opening anchor 1000(11-10), 거래 +30(11-12). opening anchor entry를 `DELETE /valuations/:id`로 삭제하고 sync | 삭제가 허용된다(kind 검사 없음). `opening_date`는 `11-12 - 1일 = 11-11`, `opening_balance`는 0. 행 11-11 `end_balance 0`, 11-12 `end_balance -30`(음수 잔액이 그대로 나온다). 캐시 잔액 -30 |
| T-28 | R-08 | Property 수정 요청 `PATCH /properties/:id`에 `account[name]`, `account[accountable_attributes][year_built]`, `account[balance] = 999`를 보낸다 | 이름과 `year_built`만 저장된다. `balance`는 허용 키가 아니라 저장되지 않고 `set_current_balance`도 불리지 않는다. 계정이 `active`면 수정 화면을 다시 보인다 |
| T-29 | R-17 | 웹에서 reconciliation 생성(`POST /valuations`)을 금액 없이, 수정(`PATCH /valuations/:id`)을 금액 없이 보낸다. 확인 단계(`confirm_create`)도 금액 없이 | 생성: 공백 검사 없이 `create_reconciliation`이 불리고 저장 검증 오류 메시지로 실패(422). 수정: reconcile을 건너뛰고(노트만 저장) 성공. `confirm_create`: "금액 필요" 오류로 422 |
| T-30 | R-07 | Vehicle: opening anchor(20,000, 날짜 오늘 2026-11-18), 캐시 잔액 20,000. 폼은 `initial_balance`·`initial_balance_shown` 20,000, `purchase_date`만 2026-11-10으로 바꿔 보낸다(다른 entry 없음) | 가격은 편집되지 않았고 날짜만 편집됐다. anchor 날짜가 오늘이라 쓸 금액은 `initial_balance_shown` 20,000이다. opening anchor가 11-10, 금액 20,000으로 바뀐다. anchor 금액이 `account.balance`(20,000)와 같으므로 오늘 reconciliation은 만들지 않는다 |
| T-31 | R-22, R-23, R-18 | 새 연동 계정(Depository, reverse)에 총액 2,000을 (a) `set_current_balance(2000)`으로, (b) 계정 직접 쓰기 `balance: 2000, cash_balance: 2000`으로 넣는다 | (a) current anchor(금액 2000, 오늘)와 캐시 `balance 2000`이 생긴다. 다음 sync가 11-18 `end_balance 2000`을 만들고 하루 뒤 같은 호출은 이전 anchor를 reconciliation으로 굳힌다. (b) anchor가 없다. 다음 reverse 재계산은 캐시 잔액 2000을 오늘 날짜 출발 잔액으로 쓰고 읽을 때마다 `No current balance anchor found ...` 경고가 남는다. 둘 다 sync는 성공한다(원본은 (a)를 강제하지 않는다) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 `repos/sure/` 기준, 기준 SHA는 문서 frontmatter와 같다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01; `app/models/depository.rb:42-44`, `app/models/credit_card.rb:30-32`, `app/models/loan.rb:584-586` 등 각 종류의 `classification`; `app/models/account.rb:81`, `:182`, `:224` | 종류 클래스 9개의 `classification`이 schema의 generated 식과 같은 값임을 하나씩 대조했다. `Accountable.from_type(type)`은 목록 밖이면 nil(`accountable.rb:9-12`). |
| R-02 | `app/models/account.rb:912-923` | 코드 확인. `Accountable` 9종과 일치하는 분기 9개. |
| R-03 | `app/models/account.rb:4`, `:11-12`, `:1034-1057`; `db/schema.rb:99-139`; `app/controllers/concerns/accountable_resource.rb:19-24` | 코드 확인. |
| R-04 | C-02; `app/models/account.rb:183`; `app/models/loan.rb:29-48`, `:295`; `app/models/credit_card.rb:17-19`; `app/models/crypto.rb:14-24`; `db/schema.rb` 각 종류 테이블; 검색: `grep -rn "validates :subtype\|validate.*subtype" app/models/*.rb` | 전칭 주장은 "subtype 검증은 Loan뿐"이다. 검색 범위는 `app/models/*.rb`(하위 디렉터리 제외)였고 `loan.rb:29`만 나왔다. concern·하위 디렉터리·컨트롤러의 검증은 검색하지 않았다. |
| R-05 | C-04; `app/controllers/concerns/accountable_resource.rb:37-81`; `app/jobs/application_job.rb:1-15`(commit 후 enqueue); `app/models/account.rb:350-697`(`create_from_*`) | 코드 확인. 웹 경로의 바깥 `Account.transaction`은 `accountable_resource.rb:43-49`다. `Sync` 행이 바깥 transaction 안에서 만들어지고 job 등록이 commit 뒤인 것은 `syncable.rb:65-78`의 `Sync` 생성과 `application_job.rb`의 설정을 읽은 결론이다. 생성 헬퍼 일부(simplefin, enable_banking, wise, coinbase, crypto 거래소)만 읽었다. |
| R-06 | `app/controllers/properties_controller.rb:12-31`, `:55-77`, `:115-143`, `:145-220`(`create_via_avm_provider`는 분기 존재만 확인) | 코드 확인. `Property::AvmImport`(`status: "draft"`로 생성하는 다른 경로, `app/models/property/avm_import.rb:51`)는 열지 않았다(행 4). |
| R-07 | `app/models/vehicle.rb:8-14`(`initial_balance_shown` 주석 `:10-12`), `:28-31`, `:56-118`; `app/controllers/concerns/accountable_resource.rb:97-125`(잔액 변경이 속성 갱신보다 먼저) | 코드 확인. `after_update` 시점의 `account.balance`가 새 값이라는 점은 컨트롤러의 호출 순서(`set_current_balance` → `@account.update`)와 `vehicle.rb:79`의 읽기 시점을 조합한 결론이다. |
| R-08 | `app/controllers/concerns/accountable_resource.rb:83-135`; `app/controllers/properties_controller.rb:33-46`, `:287-298`; `app/models/loan.rb:293-352`; `app/models/vehicle.rb:14`; 검색: `grep -rn "after_update\|after_save\|after_commit\|before_save\|after_create" app/models/account.rb app/models/account/*.rb app/models/concerns/accountable.rb app/models/valuation.rb app/models/balance.rb app/models/<9종>.rb app/models/entry.rb app/models/concerns/syncable.rb` | "통화나 이름만 바꾸는 수정은 sync를 요청하지 않는다"는 위 검색 범위의 부재 확인이다. sync를 요청하는 종류 행 callback은 `loan.rb:323-324`(상환 입력 변경 시)와 `vehicle.rb:14`(구매 가격·날짜 편집 시) 두 곳이고, 결과의 `entry.rb:87`, `account/logoable.rb`는 sync 요청이 아니다. 다른 디렉터리의 callback과 컨트롤러가 부르는 sync(`CreditCardsController`, `InvestmentsController`는 읽음, 호출 없음)는 놓칠 수 있다. 이전 통화 행이 남는 결과는 R-36에서 도출한 추론이다. 5자리 입력의 효과는 비교식(`accountable_resource.rb:99`)에서 도출한 추론. |
| R-09 | C-03; `app/controllers/accounts_controller.rb:267-274`; `app/models/account.rb:250-269` 주석 | 코드 확인. `disabled_at` 기록은 `timestamps: true`(레포 밖 gem)를 코드 주석(`:233-235`)이 설명하는 것을 읽은 추론. |
| R-10 | `app/controllers/accounts_controller.rb:299-313`; `app/models/account.rb:6-9`, `:18-39`, `:777-824`, `:1069-1093`; `app/jobs/destroy_job.rb:1-70`; `db/schema.rb:3179`(`entries` FK cascade) | 코드 확인. `Transfer#destroy!`가 상대 거래를 어떻게 처리하는지는 행 3이다. 계정 삭제 시 `account_statements`는 `dependent` 없이 별도 이동(`:179-180`, `:1069-1084`). |
| R-11 | `app/controllers/accounts_controller.rb:279-282`; `balance_sheet/classification_group.rb:25-28`; `balance_sheet/historical_account_scope.rb:11-14`; `account.rb:90` | 코드 확인. 다른 사용처는 `grep -rn "exclude_from_reports\|included_in_reports" app --include=*.rb`로 많이 나오지만 읽지 않았다. |
| R-12 | C-17, C-18; `db/schema.rb:709-751`, `:3066-3071`; `app/models/account/current_balance_manager.rb:162-164`; `app/models/account/opening_balance_manager.rb:87-89`; 검색: `grep -n "valuations\|opening_anchor\|current_anchor" db/schema.rb`(`valuations` 테이블 정의 한 건), `grep -rn "validates.*kind\|uniqueness" app/models/valuation.rb app/models/entry.rb` | 부재 주장("anchor 유일 제약 없음")은 위 두 검색의 범위에서 못 찾았다는 뜻이다. `first` 정렬 없음은 코드에 `order`가 없다는 읽기이고, 실제 순서는 DB·프레임워크 의미(추론). 임포트 경로(`family/data_importer.rb`, `qif_import.rb`, `monarch_import/converter.rb`)가 anchor를 직접 만드는 곳은 행 8에서 다룬다. |
| R-13 | C-06, C-08 `anchorable.rb:12-27` | 코드 확인. |
| R-14 | C-08 `anchorable.rb:41-55`; 호출처 검색 `grep -rn "ensure_opening_anchor_precedes_entries" app` | 호출처는 읽지 않았다(provider 흐름). |
| R-15 | C-08 `anchorable.rb:57-67`; `app/models/account.rb:855-858` | 코드 확인. 투자 연동 분기는 행 4. |
| R-16 | C-07 | 코드 확인. |
| R-17 | C-07, C-08 `reconcileable.rb:4-14`; `app/controllers/valuations_controller.rb:1-117`; `app/controllers/concerns/entryable_resource.rb:33-39`; `app/models/entry.rb:378-382` | 코드 확인. `GoalPledge::Reconciler`는 열지 않았다(행 12). |
| R-18 | C-05 `current_balance_manager.rb:13-34`, `:162-164`; `app/models/balance/reverse_calculator.rb:6-9` | 코드 확인. |
| R-19 | C-05 `:40-53`, C-08 `anchorable.rb:73-77` | 코드 확인. 수동 경로가 전략 실패와 무관하게 캐시를 쓰는 것은 `:44-49`에 `result` 확인이 없는 것으로 확인했다. |
| R-20 | C-05 `:106-217` | 코드 확인. 예외로 인한 되돌림은 `with_lock`이 transaction을 연다는 프레임워크 의미(추론). Plaid·IBKR processor가 `with_lock` 바깥 transaction에 합류한다고 주석이 적는다(`plaid_account/processor.rb:111-146`, `ibkr_account/processor.rb:40-75`). |
| R-21 | C-05 `:76-97` | 코드 확인. |
| R-22 | C-05, `app/models/balance/reverse_calculator.rb:6-9`, `:18`; `app/models/balance/forward_calculator.rb:110-124`; `app/models/balance/materializer.rb:37-65`; `app/models/account/provider_import_adapter.rb:420-425`; `lib/generators/provider/family/templates/account_processor.rb.tt:95-109`; `app/models/trading212_account/processor.rb:24-36`; `app/models/plaid_account/processor.rb:111-146`; 검색: `for f in app/models/*_account/processor.rb; do grep -c "set_current_balance" $f; grep -cE "account\.update!\(|update_balance" $f; done`(27개 파일), `grep -rn "set_current_balance\|\.update_balance\|set_opening_anchor_balance" app lib --include=*.rb` | 분류 결과: `set_current_balance`를 호출하는 processor 12개(coinstats `:61`, enable_banking `:90`, ibkr `:55`, indexa_capital `:69`, plaid `:132`, questrade `:55`, redbark `:86`, sharesight `:46`, snaptrade `:67`, sophtron `:77`, trade_republic `:41`, trading212 `:34`). 직접 쓰는 processor 15개를 줄까지 확인했다(akahu `:36`, binance `:67`, brex `:50`, coinbase `:129`, coinspot `:79`, fio `:42`, kraken `:31`, lunchflow `:81`, mercury `:57`, monobank `:39`, onchain_wallet `:227`, simplefin(processor 일부 `:62`, importer `simplefin_item/importer.rb:233`의 `update_balance`), truelayer `:34`, up `:40`, wise `wise_account/processor.rb:40-46`). FinanceKit은 `financekit/processor.rb:135`의 `update_balance`다. Brex, Binance, Coinspot, Fio, Mercury, Monobank, TrueLayer, Up은 위 줄을 열어 `account.update!(balance:, cash_balance:)`이고 `set_current_balance` 호출이 없음을 직접 확인했다. 검색은 `app`, `lib`의 `.rb`만 봤다. 동적 호출과 processor 밖의 쓰기, 호출 인자가 같은 파일의 다른 메서드를 거치는 경우는 놓칠 수 있다. "reverse는 캐시를 쓰지 않는다"는 `grep -rn "update!\|update_all\|update_column\|\.update(" app/models/balance app/models/balance.rb`가 `materializer.rb:61`(forward 분기)뿐이었다는 범위 한정 결과다. "원본은 강제하지 않는다"는 `app/models/provider/base.rb`와 어댑터 등록(`Provider::Factory`)에 잔액 연산 요구가 없음(`grep -n "balance" app/models/provider/base.rb`가 결과 없음)과 직접 쓰기 provider가 존재하는 사실의 조합이다. 이 행은 provider-import-adapter U-01의 결론이고 원본 주석(`current_balance_manager.rb:17-19`)과 일치한다. |
| R-23 | `app/models/account/provider_import_adapter.rb:420-425`; `app/models/wise_account/processor.rb:40-70`; `app/models/kraken_account/processor.rb:31-40`; `app/models/balance/reverse_calculator.rb:6-9`; C-05 `:17-26` | 코드 확인. 경고가 남는 provider 목록은 R-22의 분류(직접 쓰기 + FinanceKit)와 같다. 캐시와 balances 행이 어긋난다는 결론은 두 코드의 읽기·쓰기 관계에서 도출했고 실행하지 않았다. |
| R-24 | C-20; `app/controllers/holdings_controller.rb:90-100`, `:130-137`; `app/models/snaptrade_account/split_security_repair.rb:85`; 검색: `grep -rn "Balance::Materializer" app lib --include=*.rb` | 호출처는 위 검색(범위 `app`, `lib`)의 결과다. |
| R-25 | C-11 `forward_calculator.rb:8-15`, `:74-135`; C-18 `entry.rb:378-382`, `:811-815`; `app/models/concerns/syncable.rb:60-80`; `app/models/balance/materializer.rb:81-115`; sync-pipeline R-05, R-06, R-17 | 코드 확인. "reverse는 창을 무시"는 `grep -rn "window_start_date" app/models/balance app/models/holding`이 `forward_calculator.rb`뿐인 결과(범위 한정). `Entry#sync_account_later` 호출처는 컨트롤러 `entryable_resource.rb:37` 등 일부만 읽었다(행 2). |
| R-26 | C-09 | 코드 확인. |
| R-27 | C-14; `app/models/balance.rb:1-31`; `app/models/balance/balance_data.rb:1-9`; `balance/materializer.rb:71-79`; `balance/reverse_calculator.rb:24-34`, `:69-82`; `db/schema.rb:267-269` | generated 식은 schema에서 읽은 것이다. reverse의 opening anchor 날짜 행에서 `start = end`, 조정 0이고 흐름 열은 `flows`를 그대로 쓰는 것(`reverse_calculator.rb:24-34`, `:69-82`)과 generated 식을 조합해 `end_balance`가 anchor 금액과 갈라지는 것을 도출했다(T-26, 실행하지 않음). 다른 경우(forward, reverse의 일반 날, waypoint 날, 경계 다음 날)가 같아지는 것은 두 계산기의 조정 공식을 대수로 풀어 확인한 추론(보유종목 행이 매일 있고 전날 평가액이 시작 비현금과 같다는 전제). |
| R-28 | C-13 `sync_cache.rb:26-48`, `:94-146`; C-18 `entry.rb:131-155` | 코드 확인. "`excluded`를 거르지 않는다"는 `entries_scope`(`sync_cache.rb:143-146`)와 `excluding_*` 정의에 `excluded` 조건이 없음을 읽은 것이다. |
| R-29 | C-10 `base_calculator.rb:70-82`; C-13 `sync_cache.rb:36-38`, `:63-92` | 코드 확인. `holdings_value_by_date[date] || 0`. |
| R-30 | C-10 `base_calculator.rb:101-162` | 코드 확인. |
| R-31 | C-10 `base_calculator.rb:41-43`; C-11 `forward_calculator.rb:110-124`, `:137-147`; C-08 `anchorable.rb:18-24`; C-06 `opening_balance_manager.rb:12-24` | 코드 확인. |
| R-32 | C-11 `forward_calculator.rb:17-63`, `:149-171`; C-10 `base_calculator.rb:84-99`, `:164-186` | 코드 확인. |
| R-33 | C-11 `forward_calculator.rb:8-15` | 코드 확인. |
| R-34 | C-12; C-10 `base_calculator.rb:164-186`; `app/models/balance/materializer.rb:82-95`(빈 계산 시 purge) | 코드 확인. T-07을 손으로 따라가 맞췄다. 빈 반복은 Ruby `downto`가 시작 > 끝이면 빈 목록이라는 언어 의미(추론)다. |
| R-35 | C-10 `base_calculator.rb:116-186`; C-11 `forward_calculator.rb:149-160`; C-12 `reverse_calculator.rb:94-101` | 코드 확인. |
| R-36 | C-09 `materializer.rb:81-115` | 코드 확인. 통화 조건이 없다는 것은 SQL 문자열 두 곳(`:87-91`, `:113`)에서 확인했다. |
| R-37 | C-13 `sync_cache.rb:63-141`; `app/models/account.rb:670-676`, `:994-1005`; `app/models/balance_sheet/account_totals.rb:106-111`; C-15 `chart_series_builder.rb:152-158`; `app/models/property.rb:61-93`, `:183-190` | 코드 확인. money R-42의 목록과 겹치는 호출처만 정리했다. `Account#current_holdings_total`(`account.rb:826-829`)은 `unconvertible: 0`(보유 환산 실패를 0)이라 R-37(b)와 다른 정책이지만 행 4가 쓴다. |
| R-38 | C-09 `materializer.rb:37-65`; C-05; `app/models/account.rb:77-79`, `:752-754`; 검색은 R-22와 같음 | 쓰고 읽는 곳 목록은 대표이고 전수가 아니다. |
| R-39 | C-19; C-18 `entry.rb:430-432`; C-13 `sync_cache.rb:94-146`; C-09 `materializer.rb:37-65` | 코드 확인. |
| R-40 | C-21; `app/models/balance/base_calculator.rb:50-68`; `app/models/loan.rb:296-360`; `app/models/family.rb:150-152` | 계산기가 replay 변화를 받는 지점과 생성 조건만 읽었다. replay 알고리즘(`loan/principal_payments.rb:70-421`)은 읽었지만 이 스펙에서 검증하지 않았다. |
| R-41 | C-16 `account_totals.rb:31-65`; C-03; `app/models/account.rb:115-119`, `:166-174`; `app/models/balance_sheet.rb:6-11` | 코드 확인. `user`가 nil일 때 `Current.user`로 대체(`balance_sheet.rb:10`). |
| R-42 | C-16 `account_totals.rb:94-111`; money R-27, R-41 | 코드 확인. |
| R-43 | C-16 `balance_sheet.rb:13-39`; `classification_group.rb:25-59`; `account_group.rb:36-46` | 코드 확인. |
| R-44 | C-16 `balance_sheet.rb:66-105`; 정렬 키 저장 형식은 `app/models/user.rb`(미열람) | 정렬 규칙은 코드 확인. `account_order` 등의 저장 형식은 열지 않았다. |
| R-45 | `app/models/balance_sheet/sync_status_monitor.rb:1-35` | 코드 확인. |
| R-46 | C-15; C-16 `net_worth_series_builder.rb:11-71`, `historical_account_scope.rb:11-14`; `app/models/period.rb:180-188` | SQL을 따라가 도출했다. `Series` 클래스(`app/models/series.rb`)의 `Value` 구조는 읽었고 `Trend`는 열지 않았다. 마지막 점과 `net_worth`의 차이는 코드 비교로 도출했다(실행하지 않음). |
| R-47 | C-16 `net_worth_series_builder.rb:53-79` | 코드 확인. `Family#build_cache_key`는 미열람. |
| R-48 | `app/models/account/chartable.rb:5-27`; C-15 `chart_series_builder.rb:15-34`, `:144-158` | 코드 확인. |
| R-49 | `app/models/concerns/accountable.rb:90-107`; 검색: `grep -rn "balance_money(" app lib --include=*.rb --include=*.erb --include=*.jbuilder` | 결과는 정의와 `credit_card.rb`의 `last_statement_balance_money`(다른 메서드)뿐이다. `public_send` 같은 동적 호출은 `grep -rnE "\.public_send\|\.send\(" app --include=*.rb`에서 `balance_money`를 포함한 줄을 찾지 못했다. 그 밖의 확장자와 `test/`는 검색하지 않았다. |
| R-50 | `app/models/balance/materializer.rb:82-95`; `app/models/balance/reverse_calculator.rb:18` | 코드 확인. 빈 범위가 되는 조건(anchor 날짜 < 계산 시작일)은 두 정의를 비교해 도출했고 재현하지 않았다. |
| R-51 | C-24; `app/controllers/accounts_controller.rb:6`(`set_default`는 `set_account`, 관리 권한 필터는 `set_manageable_account` 대상에 `set_default`가 없다), `:284-297`; `db/schema.rb:3330` | 코드 확인. `set_default`, `remove_default`는 `before_action :set_account`(접근 가능한 계정이면 됨)만 받고 관리 권한 검사(`set_manageable_account`)는 걸려 있지 않다(`accounts_controller.rb:5-6`). |
| R-52 | `app/controllers/concerns/entryable_resource.rb:33-39`; `app/controllers/valuations_controller.rb:1-4`; `app/models/entry.rb:378-384` | 코드 확인. `destroy`에 kind 검사가 없는 것은 `entryable_resource.rb:33-39`에 조건이 없음을 읽은 것이다. `ValuationsController`는 `destroy`를 덮어쓰지 않는다(`grep -n "def destroy" app/controllers/valuations_controller.rb` 결과 없음). |
| T-01~T-04, T-06 | 구현에서 도출 | R-31, R-32의 손 계산. |
| T-26~T-31 | 구현에서 도출 | 독립 검토 반영으로 추가. T-26은 `reverse_calculator.rb:24-34`와 generated 식, T-27은 `opening_balance_manager.rb:12-24`와 R-31, T-28은 `properties_controller.rb:33-46`, T-29는 `valuations_controller.rb:7-13`, `:26-31`, `:51-72`, T-30은 `vehicle.rb:78-108`, T-31은 R-22 분류를 따라 도출. 실행하지 않았다. |
| T-05 | 구현에서 도출 | 보유종목 행은 가정한 입력이다. 보유종목 계산은 행 4. |
| T-07, T-08 | 구현에서 도출 | R-34, R-18의 손 계산. |
| T-09~T-12, T-18, T-21, T-22 | 구현에서 도출 | 각 manager 코드를 따라갔다. 이름 문구는 `valuation/name.rb`. |
| T-13 | 구현에서 도출 | `Loan`의 `initial_balance`는 종류 행 속성(R-05)이다. |
| T-14~T-17, T-19, T-20, T-23~T-25 | 구현에서 도출 | 실행하지 않았다. |

### 2.2 코드 읽는 순서 [선택]

1. `app/models/account.rb`의 `create_and_sync`, 상태 기계, `balance_type`(계정의 모양). 2. `app/models/account/anchorable.rb`와 `current_balance_manager.rb`, `opening_balance_manager.rb`, `reconciliation_manager.rb`(anchor와 Valuation을 쓰는 모든 경로). 3. `app/models/account/syncer.rb`와 `balance/materializer.rb`(전략 선택, 쓰기, purge). 4. `balance/base_calculator.rb`의 `flows_for_date`와 현금 분리, `forward_calculator.rb`, `reverse_calculator.rb`, `sync_cache.rb`. 5. `balance_sheet.rb`와 `balance_sheet/*`, `balance/chart_series_builder.rb`의 SQL. 6. 종류별 모델(`vehicle.rb`의 구매 anchor 처리, `loan.rb`의 balance 입력 callback).

원본의 구현 전략은 다섯 가지다. 하나, balances를 "하루 단위 materialized view"처럼 앱이 직접 만든다(조회·차트는 SQL로 이 테이블만 읽는다). 둘, 계정에 두 방향이 있다. 수동 계정은 opening anchor에서 앞으로, 연동 계정은 외부가 알려 준 현재 잔액(current anchor)에서 뒤로 가며 거래를 되돌린다. 셋, 외부 잔액이 매일 바뀌어도 이력이 흔들리지 않게 이전 current anchor를 reconciliation으로 굳혀 waypoint 사슬을 만든다. 넷, balances의 end 열을 DB generated column으로 두어 start·흐름·조정으로 항상 일관되게 한다. 다섯, 순자산 현재 값은 캐시 잔액, 시계열은 balances 행이라 두 계산 경로가 다르다.

### 2.3 비교·재사용 출처 [선택]

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다. 원본은 AGPL-3.0이다(overview 1절).

### 2.4 검토 기록 [필수, ready 스펙]

`draft`다. 선행 스펙 세 개가 모두 `draft`이고, 이 스펙은 작성자 점검만 했다(메인 원본 대조 점검과 독립 검토 전).

- 방식: 작성자 점검만 했다. 코드를 읽으며 R-ID와 T-ID를 도출했고, `python scripts/check.py sure`로 인용 줄 범위 형식을 점검했다. 인용한 줄이 주장을 뒷받침하는지 다시 맞춰 보는 별도 대조는 하지 않았다.
- 독립 검토 반영(2026-11-18): 검토자 주장을 코드로 다시 확인해 반영했다. R-27·불변식(reverse opening anchor 날짜, 일치), R-08·1.3(Property 별도 `update`, 일치), R-22·R-23(provider 분류, 일치하고 15개 직접 쓰기로 확장), R-17(공백 검사 위치), R-39(`>` 엄격), R-07(호출 순서, 날짜만 편집 분기), R-04(Loan 검증), R-05(웹 경로의 transaction), R-06, R-10(FK), R-34(빈 범위), R-44(422), C-ID 정정. 검토자가 지적한 "R-14 때문에 실제로 생긴다"는 R-14가 금액 0인 anchor만 옮긴다는 점은 맞지만, 같은 날 entry를 막는 검사가 없다는 것이 근거라서 R-27에 그렇게 적었다.
- 대조한 R-ID: 없음(메인 원본 대조 점검 대기).
- 대조하지 않은 R-ID: 전부. 고위험 후보는 R-19(수동 경로가 실패해도 캐시를 쓴다), R-20, R-22(provider 분류와 강제 여부), R-23, R-25, R-27(`balance` 열과 `end_*`가 갈라짐), R-28(`excluded`를 거르지 않음), R-34, R-36(통화 조건 없음), R-37, R-46, R-52(anchor 삭제 허용)이다.
- 재구현: 미수행.

- **메인 점검(2026-11-18)**: 독립 검토자 1명이 R-01~R-49와 C-ID 전부, T-ID 16개를 다시 계산했고(U-01 결론 R-22·R-23과 R-25의 네 조건은 코드와 일치, 반례 5건과 누락 9건), 작성자가 전부 반영했다. 메인은 `entries_scope`가 `excluded`를 거르지 않는 점(`balance/sync_cache.rb:143`)과 `DELETE /valuations/:id`가 kind를 가리지 않고 권한만 확인하는 점(`entryable_resource.rb` `destroy`)을 직접 확인했다.
- **대조하지 못한 것**: R-04의 `Investment` subtype 목록과 `tax_treatment` 표 내용, R-37(d)(g)의 `convert_provider_balance` 호출자, `Family#build_cache_key`, `account_order` 저장 형식, `GoalPledge::Reconciler`, R-09·R-20의 AASM·잠금 transaction 되돌림(프레임워크 동작). `Loan` 상환·이자 엔진은 범위 결정 대기라 R-40에 인터페이스만 있다.

## 적용 메모

원본 동작과 구분해 읽는다. 아래는 다른 언어로 다시 구현할 때 주의할 점과 우리가 다르게 하고 싶은 후보다. 원본의 미결정을 여기서 해소한 것으로 치지 않는다(이 스펙에는 남은 미결정이 없다).

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-22, R-23 | 자체 연동(KB국민, 키움, 업비트 어댑터)은 항상 `set_current_balance` 경로(current anchor + 캐시 잔액)로 현재 잔액을 넣고, 캐시만 쓰는 `update_balance`·직접 쓰기 경로는 만들지 않는다. 투자·암호화폐는 `cash_balance`를 따로 저장하고, 과거 명세서는 `date:`를 넘긴다. 이 경로를 인터페이스로 강제한다(잔액을 쓰는 연산 하나만 provider에 열어 둔다). | 원본은 강제하지 않고 15개 provider가 직접 쓰기를 한다(R-22). 직접 쓰기는 anchor 없는 reverse가 되어 매 읽기마다 경고가 나고 waypoint 사슬이 없으며, anchor가 있는 계정에서는 balances 행과 캐시가 어긋난다(R-23 b). | `update_balance`에 해당하는 연산을 만들지 않거나, 내부에서 anchor 갱신을 하게 바꾼다. T-08 둘째 사례가 사라진다. |
| R-19 | 수동 `set_current_balance`는 전략이 성공했을 때만 캐시 잔액을 쓴다. | 원본은 전략이 실패 결과를 돌려줘도 캐시를 써서 Valuation과 캐시가 어긋날 수 있다(R-19). | R-19의 "성공 여부와 무관"이 "성공했을 때만"으로 바뀐다. |
| R-12 | anchor가 둘 이상일 때의 규칙을 정한다(예: opening은 가장 이른 날짜, current는 가장 늦은 날짜). 원본은 uuid 순 `first`라 임의다. 구현은 위 DB 제약으로 둘 이상을 막는 쪽을 권한다. | 원본에서 둘 이상이 생기면 어느 쪽이 이기는지 정해져 있지 않다. | R-12의 "둘 이상" 문장이 규칙으로 바뀐다. |
| R-27, R-34 | reverse의 opening anchor 날짜에 같은 날 거래가 있을 때 선택지 둘: (a) 원본처럼 `end_*`를 generated column 식으로 계산해 anchor 날짜 `end_balance`가 흐름만큼 어긋나는 것을 그대로 둔다(차트가 650, 계산기 `balance` 열은 700, T-26). (b) 계산기가 그 날 조정 열에 `anchor 금액 - start - 흐름`을 써서 `end_balance`가 항상 anchor 금액이 되게 한다(forward의 Valuation 날과 같은 처리). generated column을 쓰지 않는 구현은 `end_*`를 저장하는 쪽과 `balance`를 저장하는 쪽 중 하나만 정본으로 정해야 한다. 권장은 (b)이고 `end_balance`만 정본으로 둔다. | 원본은 어느 열을 읽느냐에 따라 값이 다르다(차트와 R-16의 old_balance는 `end_*`). 한 값만 정본이어야 한다. | T-26의 기대값이 (b)에서는 11-01 `end_balance 700`, `cash_adjustments 50`이 된다. |
| R-05 | `Sync` 행 생성과 job 등록을 같은 시점으로 맞추는 transaction 경계를 정한다. 원본의 웹 경로는 바깥 transaction 안에서 `Sync`를 만들고 job은 commit 뒤에 등록하므로, 구현도 "commit 뒤 enqueue"를 보장하는 outbox 같은 장치를 둔다. | 그렇지 않으면 worker가 commit 전의 계정을 읽는다(원본 주석이 같은 문제를 적는다). | R-05 (7)의 "바깥 transaction" 설명이 이 보장으로 바뀐다. |
| R-08 | 잔액 비교는 통화 소수 자릿수(또는 저장 정밀도)로 반올림한 뒤 한다. | 원본은 전체 정밀도로 비교해 같은 값으로 보이는 입력에도 `set_current_balance`가 불린다. | R-08의 5자리 입력 사례가 사라진다. |
| R-12, R-13, R-20 | 계정당 opening anchor 하나, current anchor 하나를 DB 제약(부분 unique 인덱스, 또는 entries에 kind 열을 두고)으로 강제한다. Valuation의 이름을 저장하지 말고 kind에서 표시 이름을 만든다(한국어 UI에서는 번역). | 원본은 manager 잠금에만 기대고 `first` 정렬이 없다. 저장된 영어 이름은 로케일을 바꿔도 남는다(원본은 표시할 때 같은 이름이면 번역해 보여 준다, `valuation.rb:28-40`). | R-12, R-17의 이름 규칙이 바뀐다. 이름 문구를 비교하는 표시 로직이 사라진다. |
| R-31, R-39 | 계산 끝 날짜를 마지막 활동일이 아니라 오늘로 하는 것을 검토한다(날짜 계산 범위가 오늘까지 매일 행을 갖게). 선택하지 않으면 원본처럼 "마지막 행 이후 값은 이월"을 모든 소비자(차트, 캐시 갱신)가 알아야 한다. | 원본은 마지막 행 뒤의 값을 차트 SQL의 "가장 최근 행" 조회가 이월한다(R-46). 다른 소비자가 날짜 `d`의 행을 직접 찾으면 없을 수 있다. | 선택은 새 결정이다. 선택하면 T-02의 행 개수가 늘어난다. |
| R-37, R-42, R-46 | 환산 실패를 한 정책(없음으로 전파, 1:1 대체 없음)으로 통일하고, 합계에서 빠진 계정과 건수를 화면·API 응답에 함께 낸다(money 스펙 적용 메모와 같다). 보유종목 환산의 1:1도 뺀다면 현금 도출 방식(총액 - 평가액)을 함께 바꿔야 한다. | 원본은 항목 제외, 1:1, 0, NULL, nil이 섞여 있고 합계에서 빠진 사실이 조용히 보이지 않는다. | R-29, R-37(b)의 보유 1:1이 바뀌면 T-05 류 사례의 현금 값이 바뀐다. |
| R-42, R-46 | 현재 순자산을 시계열의 마지막 점과 같은 근거(balances 최신 행)로 계산하거나, 둘의 차이를 문서화한 정책으로 둔다(비활성 계정 포함 여부, 캐시와 행의 차이). | 원본은 현재 값이 캐시 잔액, 시계열이 balances 행이라 reverse 연동 계정의 캐시가 어긋나면(R-23) 두 값이 다르다. | T-16의 마지막 점 비교가 바뀐다. |
| R-36, R-08 | 통화가 바뀌면(R-08) 그 계정의 이전 통화 balances 행을 지우고 전체 재계산을 요청한다. | 원본은 통화 변경만으로 sync를 요청하지 않고 purge가 통화를 보지 않아 이전 통화 행이 범위 안에 남는다(R-36). | R-08의 "sync를 요청하지 않는다"가 바뀐다. |
| R-31, R-13, R-05 | "오늘"과 날짜는 한국 시간대(KST)로 정하고 `Date.current`에 해당하는 값을 한 곳에서 주입한다. opening anchor의 기본 날짜(오늘 - 2년)는 한국 사용자에게 맞게 조정할 수 있다. | money 스펙 적용 메모의 시간대 결정과 같다. | T-01의 날짜 입력 기본값이 바뀔 수 있다. |
| R-40 | 대출 원금 replay(`Loan::PrincipalPayments`)와 일정 엔진은 이 스펙에서 만들지 않는다. 대출은 R-30의 일반 규칙(거래 금액 합)만 쓴다. | preview 기능이고 별도 엔진이다. 필요하면 별도 스펙으로 분리한다(보고의 feature map 보정 제안). | R-30의 "replay 변화가 있으면" 분기가 사라진다. |
| R-10, R-43 | 한국 사용자는 은행·증권·코인 연동을 직접 만든다. 연동 계정은 R-10대로 삭제가 막히므로 직접 연동에도 "연결 해제 후 삭제" 흐름을 둔다(provider-import-adapter R-65). | 연동 계정 삭제 거부는 원본 규칙이다. | 해당 없음. |
