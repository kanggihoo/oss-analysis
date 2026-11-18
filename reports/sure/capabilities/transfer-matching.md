---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/transfer.rb
  - app/models/rejected_transfer.rb
  - app/models/family/auto_transfer_matchable.rb
  - app/models/transfer/creator.rb
  - app/models/transfer/matcher.rb
  - app/models/transfer/pending_match.rb
  - app/models/transfer/investment_kind_reconciler.rb
  - app/models/transaction.rb
  - app/models/transaction/transferable.rb
  - app/models/account.rb
  - app/models/account/syncer.rb
  - app/models/family/syncer.rb
  - app/models/financekit/downstream.rb
  - app/models/wise_item/interbalance_linker.rb
  - app/models/rule/action_executor/set_as_transfer_or_payment.rb
  - app/models/family.rb
  - app/models/category.rb
  - app/models/loan.rb
  - app/controllers/transfers_controller.rb
  - app/controllers/transfer_matches_controller.rb
  - app/controllers/auto_matches_controller.rb
  - app/controllers/concerns/account_authorizable.rb
  - app/controllers/application_controller.rb
  - app/jobs/auto_match_transfers_job.rb
  - app/views/transactions/_transaction.html.erb
  - app/views/transfers/show.html.erb
  - config/routes.rb
  - config/application.rb
  - config/locales/models/transfer/en.yml
  - db/schema.rb
  - .env.example
depends:
  - ./transactions.md
  - ./money-currency-rules.md
  - ./account-balances.md
  - ./sync-pipeline.md
status: draft
---

# 이체 매칭 (Transfer)

> 같은 가족의 두 계정에서 금액이 맞는 출금 거래와 입금 거래를 이체(`Transfer`) 하나로 묶고, 자동 후보 제안(pending)과 사용자의 확정·거절·해제, 수동 이체 생성, 거절 기록(`RejectedTransfer`)을 정의한다.

이 문서의 이름은 다음과 같다. `Transfer`는 입금 다리(inflow leg)와 출금 다리(outflow leg)를 묶는 행이다. 다리는 `Transaction` 하나(그 `Entry`의 `amount`가 음수면 입금, 양수면 출금)다. "후보(candidate)"는 아직 `Transfer`가 없는 (입금 다리, 출금 다리) 쌍이다. `Entry`·`Transaction`·`kind`·`user_modified`·잠금(locked attribute)은 [transactions](./transactions.md) 1.3·R-13·R-18과 같다. 금액 부호(음수 = 유입)는 [money-currency-rules](./money-currency-rules.md) R-36이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 원화 입출금 계좌에서 카드 대금을 낸 두 거래가 이체 후보로 잡히고 사용자가 확정하는 것이다. 정확한 기준은 1.4다.

1. 은행 거래가 들어온 뒤 계정 sync가 끝나면 post-sync가 `auto_match_transfers!(account:)`를 부른다. 가족 설정 `auto_match_transfers_disabled`가 true면 아무것도 하지 않는다(R-13, R-15).
2. 한 번의 SQL이 후보 쌍을 찾는다. 같은 가족의 서로 다른 활성 계정, 입금 `amount < 0`·출금 `amount > 0`, 둘 다 `excluded = false`, 날짜 차이 ±4일 이내, 같은 통화면 금액이 정확히 반대(`500000`과 `-500000`)다. 다른 통화면 환율 오차 안의 쌍이다(R-07~R-10). 이미 `Transfer`가 있는 다리와 거절 기록이 있는 쌍은 뺀다(R-07, R-19).
3. 후보를 (같은 통화 먼저, 날짜 차이 작은 순)으로 훑으면서 이미 쓴 거래가 없는 쌍마다 `Transfer`를 `pending`으로 만든다. 두 거래의 `kind`는 그대로다(R-12, R-13).
4. 사용자는 거래 목록의 pending 표시나 자동 매칭 화면에서 확정하거나 거절한다(R-32). 확정(`confirm!`)은 출금 다리 `kind`를 도착 계정 종류로 정한다. 카드 계정이면 `cc_payment`, 입금 다리는 `funds_movement`다(R-26, R-03).
5. 거절(`reject!`)은 (입금 거래 id, 출금 거래 id) 쌍을 `RejectedTransfer`에 남기고 `Transfer`를 지운다. 자동 경로와 거래 목록 hint는 그 쌍을 다시 제안하지 않는다(R-18, R-19).
6. 자동으로 못 찾은 쌍은 사용자가 거래의 수동 매칭 창(±30일, 오차 10% 이상)에서 고르거나, 새 이체를 직접 만든다(R-21~R-25).
7. 거래 한 건을 지우면 그 거래가 속한 `Transfer`가 지워지고 반대쪽 다리는 그 `Transfer`가 확정(`confirmed`)이었고 다리 `kind`가 이체 종류일 때만 `standard`로 돌아간다. pending 매칭이었다면 `kind`는 그대로다(R-31).

### 1.2 범위·통합 지점

- 제공: `Transfer`·`RejectedTransfer` 데이터와 검증, 후보 탐색(자동·거래 목록 hint·수동 창), 자동 매칭 실행과 pending 수명, 확정·거절·삭제·bulk 처리, 수동 매칭(기존 거래 짝짓기와 새 반대 거래 생성), 새 이체 생성(`Transfer::Creator`, 수수료 포함), 이체 때문에 정해지는 `kind`와 `categorizable?`, 투자 계좌 대상 이체의 `investment_contribution` 전환, 자동 매칭 설정 토글, 이체 삭제 때 반대 다리 해제.
- 제외:
  - 거래 CRUD·분할·잠금 일반([transactions](./transactions.md)). 이 문서는 거래를 지울 때 `Transfer`가 지워지는 결과(R-31)와 이체의 입금 다리 카테고리 차단 판정에 쓰는 `categorizable?`(R-05)만 갖는다. 차단을 거는 쪽은 transactions R-10이다.
  - 환율 조회·저장·환산과 부호 규칙. [money-currency-rules](./money-currency-rules.md) R-21~R-27, R-36. 이 문서는 후보 SQL이 환율 행을 읽는 방식(R-09)과 `Transfer::Creator`가 `exchange_to`를 부르는 지점(R-24)만 쓴다.
  - sync 예약·합치기·post-sync 실행·예외 삼킴([sync-pipeline](./sync-pipeline.md) R-05, R-06, R-11, R-15). 이 문서는 post-sync가 부르는 `auto_match_transfers!` 본문과 그 호출처(R-15)를 갖는다. 잔액 재계산은 [account-balances](./account-balances.md)다.
  - Family 테넌시와 `AccountShare` 권한 모델. 승인 범위 밖이다. 사용 지점(쓰기 가능 판정)만 R-ID에 쓰고 정의는 U-02로 둔다.
  - 규칙 액션 `SetAsTransferOrPayment`(행 10), 반복 거래 등록 `mark_as_recurring`(행 13), AI assistant 함수 `match_transfer`(`Transfer::Matcher` 호출, `match_transfer.rb:110-111`)·`review_transfer`·`unmatch_transfer`·`get_transfer_match_candidates`(`Matcher#candidates`, `:62`), API v1 `transfers`·`rejected_transfers`(읽기 전용 index·show, 행 17), `Family::DataImporter`의 이체 가져오기. 이들이 이 문서의 `Transfer`·`kind_for_account`·`reject!`를 쓰는 지점만 R-03·R-18·R-23에 적는다.
  - Wise 연동 고유 로직(`WiseItem::InterbalanceLinker`)은 provider 구현이다. 이 문서는 자동 매칭이 같은 Wise 연결의 두 계정 쌍을 건너뛰는 조건(R-10)과 삭제 시 거절로 바뀌는 분기(R-30)의 존재만 쓴다. 쌍이 "재링크되는 쌍"인지 판정하는 규칙은 적지 않는다(U-05).
  - 이체 때문에 바뀌는 예산·통계 집계. 이 문서는 `kind` 값까지만 정한다.
- 외부 의존·선행 계약: PostgreSQL(SQL 전체가 PG 문법이다). 현재 사용자(`Current.user`)와 그 가족의 접근 가능·쓰기 가능 계정 집합(U-02), `exchange_rates` 저장소(R-09), `Money#exchange_to`(R-24), 계정 종류 판정(`loan?`·`credit_card?`·`investment?`·`crypto?`·`liability?`, money-currency-rules R-37), `Entry#sync_account_later`(sync-pipeline), `Family#investment_contributions_category`와 수수료 카테고리("Fees") 조회·생성(카테고리 소관, 행 10), `Loan#amortizable?`·`principal_only_transfers?`.
- 소유 상태·부작용: `transfers`(`status`, `amount`, `notes`), `rejected_transfers`, 수수료 거래(`transactions.transfer_id`로 `Transfer`에 연결된 `Transaction`)와 그 `Entry`, 다리 `Transaction`의 `kind`·`category_id`·`locked_attributes["kind"]`, 다리 `Entry`의 `idempotency_key`(지워짐), 새 이체로 만든 다리 `Entry`와 가족 설정 `families.auto_match_transfers_disabled`. 계정 sync를 예약한다(R-22, R-24, R-13).

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Transfer` | 행 | `inflow_transaction_id`·`outflow_transaction_id`(둘 다 not null, `Transaction` 참조, 거래가 지워지면 DB가 `Transfer`를 지움), `status`(`pending`/`confirmed`, 기본 `pending`), `amount`(decimal(19,4), 0 이상, 기본 0), `notes`(text, null 가능). (입금 id, 출금 id) 쌍에 unique index가 있다. 규칙은 R-01, R-02. |
| 다리 | `Transaction` | 한 `Transaction`은 입금 다리로 한 번, 출금 다리로 한 번 중 하나로만 쓰인다(검증, R-01). `Transaction#transfer`는 `transfer_as_inflow`가 있으면 그것, 없으면 `transfer_as_outflow`다. |
| 수수료 거래 | `Transaction` | `transactions.transfer_id`가 이 `Transfer`를 가리키는 거래. `Transfer`가 지워지면 같이 지워진다(R-24, R-28, R-31). |
| `RejectedTransfer` | 행 | (`inflow_transaction_id`, `outflow_transaction_id`) 쌍(둘 다 not null, unique). 둘 중 한 거래가 지워지면 DB가 행도 지운다(R-20). |
| 후보 행 | 읽기 전용 | `inflow_transaction_id`, `outflow_transaction_id`, `date_diff`(일, 정수), `match_rank`(0 = 같은 통화 정확 일치, 1 = 환율 오차 일치), `rejected_transfer_id`(거절 기록이 있으면 id). |
| 가족 설정 | boolean | `auto_match_transfers_disabled`, 기본 false. |
| 환경변수 | 문자열 | `TRANSFER_MATCH_EXCHANGE_RATE_TOLERANCE`(예: `0.03`). R-11. |

**후보 탐색 매개변수 (`transfer_match_candidates`, C-09)**

| 매개변수 | 기본 | 의미 |
|---|---|---|
| `date_window` | 4 | 정수 일수. 정수로 못 바꾸면 `ArgumentError`. |
| `exchange_rate_tolerance` | 환경변수 값(R-11) | 실수. 숫자가 아니거나 유한하지 않거나 음수면 `ArgumentError`. |
| `inflow_transaction_id`, `outflow_transaction_id`, `account_id`, `transaction_ids` | nil | 해당 거래·계정으로 한정. `transaction_ids`가 빈 목록(nil이 아님)이면 결과는 비어 있다. |
| `include_rejected` | true | false면 거절 기록이 있는 쌍을 뺀다. |
| `restrict_cross_currency_to_linked_accounts`, `require_common_writer`, `exclude_same_wise_item` | false | R-10. 자동 경로만 셋 다 true로 부른다. |

**연산(웹 경로 기준)**

| 연산 | 입력 → 출력 | 규칙 |
|---|---|---|
| 자동 매칭 실행 | `auto_match_transfers!(account?, exchange_rate_tolerance?)` → 만든 `Transfer`(pending) | R-13~R-15 |
| 새 이체 생성 `POST /transfers` | `transfer[from_account_id, to_account_id, amount, date, exchange_rate, source_fee_amount, destination_fee_amount, tag_ids, idempotency_key]` → confirmed `Transfer` | R-24, R-25 |
| 수동 매칭 창 `GET /transactions/:transaction_id/transfer_match/new` | 거래(`Entry`) id → 후보 목록, 새 반대 거래를 만들 대상 계정 목록 | R-21 |
| 수동 매칭 `POST /transactions/:transaction_id/transfer_match` | `transfer_match[method]`(`new`이면 `target_account_id`, 아니면 `matched_entry_id`) → confirmed `Transfer` | R-22 |
| hint 무시 `DELETE /transactions/:transaction_id/transfer_match` | 거래(`Entry`) id → `RejectedTransfer` 생성 | R-17 |
| 이체 확정·거절·수정 `PATCH /transfers/:id` | `transfer[status]`(`confirmed`/`rejected`), `notes`, `category_id`, `amount`, `source_fee_amount`, `destination_fee_amount`, `investment_contribution` | R-26~R-29 |
| 이체 삭제 `DELETE /transfers/:id` | id → `Transfer` 삭제(또는 거절) | R-30, R-31 |
| 이체 태그 `PATCH /transfers/:id/tags` | `tag_ids` → 두 다리의 태그 교체 | R-33 |
| 자동 매칭 목록·일괄 처리·설정 `GET /auto_matches`, `PATCH /auto_matches/bulk_update`, `PATCH /auto_matches/update_settings` | `status`+`transfer_ids` / `auto_match_transfers_disabled` | R-32, R-34 |

**id 종류**: `transfer_match`의 `:transaction_id`와 `matched_entry_id`는 `Entry` id다([transactions](./transactions.md) 1.3). 후보 행·`Transfer`·`RejectedTransfer`의 `*_transaction_id`는 `Transaction` id다.

### 1.4 행동 규칙과 남은 질문

**데이터와 검증**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Transfer` 저장 | `inflow_transaction_id`가 다른 `Transfer`의 입금 id와 같거나 `outflow_transaction_id`가 다른 `Transfer`의 출금 id와 같으면 검증 오류(`taken`)다. 그래서 거래 하나는 입금 다리 하나·출금 다리 하나까지만 가진다. (입금, 출금) 쌍 unique index가 이를 백업한다. `status`는 `pending`·`confirmed` 둘뿐이고 DB 기본은 `pending`, `amount`는 0 이상이며 기본 0이다. 다리 `Transaction`이 지워지면 DB FK가 그 `Transfer`를 지운다. | 코드 확인 |
| R-02 | `Transfer` 검증 4종 (두 다리의 `Entry`가 모두 있을 때만 검사) | (a) 두 다리의 계정이 달라야 한다(`different_accounts`). (b) 두 계정의 family가 같아야 한다(`same_family`). (c) 입금 `amount`는 음수, 출금 `amount`는 양수여야 하고(`opposite_amounts`), 두 통화가 같으면 합이 정확히 0이어야 한다. 통화가 다르면 부호만 보고 환율 오차는 검증하지 않는다. (d) 두 날짜 차이의 절댓값이 `status`가 `confirmed`이면 30일, 그 밖(pending)이면 4일을 넘으면 `within_days` 오류다(경계 포함: 4일·30일 차이는 통과). 검사는 저장할 때마다 `status` 값 기준으로 돈다. | 코드 확인 |
| R-03 | 도착 계정 종류별 출금 다리 `kind` (`Transfer.kind_for_account(to, from_account:)`, C-02) | 도착이 `Loan`이면 `loan_payment`, `CreditCard`면 `cc_payment`, `Investment`·`Crypto`이면 출발 계정이 `Investment`·`Crypto`가 아닐 때(출발 미지정 포함) `investment_contribution`, 출발도 둘 중 하나면 `funds_movement`, 그 밖의 부채(`OtherLiability`)면 `cc_payment`, 나머지(`Depository`·`Property`·`Vehicle`·`OtherAsset`)는 `funds_movement`다. 위에서부터 첫 일치로 정한다. 입금 다리는 항상 `funds_movement`다. `Transfer::Creator`·자동 확정·수동 매칭·규칙·`Family::DataImporter`가 모두 이 함수를 부른다. | 코드 확인 |
| R-04 | 다리의 `kind` 계산 (`kind_for_leg`, C-03) | 입금 다리는 `funds_movement`. 출금 다리는 (a) 그 `kind`가 잠겨 있고(`locked_attributes["kind"]`) 값이 `investment_contribution`·`funds_movement` 중 하나이고 R-03의 기본값이 `investment_contribution`인 경우에만(도착이 투자·암호화폐이고 출발은 아닐 때) 현재 `kind`를 그대로 쓰고(사용자의 선택), (b) 아니면 R-03 값이다. `investment_contribution_choice`는 (a)일 때 현재가 `investment_contribution`인지 여부, 아니면 nil이다. | 코드 확인 |
| R-05 | `categorizable?` (C-05) | 도착 계정이 없으면 false. 있으면 `kind_for_leg(출금 다리)`가 `funds_movement`·`cc_payment`가 아니면 true다. 그러므로 카드·기타 부채 도착과 일반 계좌 간 이체는 false(분류할 것이 없음), 대출 상환과 투자 기여는 true다. 사용자가 투자 기여를 일반 이체로 바꾸면(R-29) false가 된다. `status` 조건이 없어 pending `Transfer`도 같은 값을 낸다. 그래서 `category_set_on_transfer_outflow?`(`transaction.rb:398-400`, 입금 다리 카테고리 편집 차단)도 pending 이체의 입금 다리에 적용된다(`kind`는 아직 바뀌지 않았어도 차단됨, transactions R-10). 이 값은 다리의 저장된 `kind`가 아니라 도착 계정으로 계산한다(provider sync가 낡은 `kind`를 남겨도 맞게 하려는 목적, 코드 주석). | 코드 확인 / 추론(목적은 주석 근거) |
| R-06 | 이름·종류 표시 | `payment?`는 도착 계정이 부채(`liability?`: `Loan`·`CreditCard`·`OtherLiability`)일 때 true다. 표시 이름은 `payment?`이면 `"Payment to <도착 계정 이름>"`, 아니면 `"Transfer to <도착 계정 이름>"`이고 도착 계정이 없으면 각각 `"Payment"`·`"Transfer"`다. `transfer_type`은 출금 다리 `kind`가 `loan_payment`면 `"loan_payment"`, `cc_payment`면 `"liability_payment"`, 아니면 `"transfer"`다. `amount_abs`는 입금 다리 금액의 절댓값이고 입금 다리가 없으면 `Money(0, 출발 계정 통화 || "USD")`다(`transfer.rb:75`). | 코드 확인 |
| R-35 | 거래 쪽 이체 판정 | `Transaction::TRANSFER_KINDS`는 `funds_movement`·`cc_payment`·`loan_payment`·`investment_contribution`이고 `Transaction#transfer?`는 `kind`가 이 중 하나일 때 true다(`transfer`(레코드)가 있는지와 무관). 분류 제외 목록(`UNCATEGORIZED_EXCLUDED_KINDS`)은 `funds_movement`·`cc_payment`뿐이다. `category_editable?`은 이체 `kind`이면서 `Transfer`가 있을 때 `categorizable?`이고 출금 다리일 때만 true, `Transfer`가 없으면 true다. 입금 다리 카테고리 차단(`category_set_on_transfer_outflow?`)은 `kind`가 아니라 `Transfer` 레코드와 `categorizable?`로 정한다. 이 판정을 호출하는 쪽은 transactions R-10이다. | 코드 확인 |

**후보 탐색**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 후보 쌍의 공통 조건 (SQL, C-14) | 입금 다리는 `Transaction` entryable이고 `excluded = false`이고 `amount < 0`. 출금 다리는 `Transaction`이고 `excluded = false`이고 `amount > 0`이고 입금 다리와 계정이 다르며 날짜가 입금 날짜 ± `date_window`일(양끝 포함) 안이다. 두 계정 모두 `family_id`가 같고 상태가 `draft`·`active`다. 입금 거래가 이미 어떤 `Transfer`의 입금 다리이거나 출금 거래가 이미 어떤 `Transfer`의 출금 다리이면 제외한다(pending·confirmed 모두). `account_id`가 있으면 입금·출금 계정 중 하나가 그것이어야 하고, `inflow_transaction_id`·`outflow_transaction_id`·`transaction_ids`가 있으면 그 거래가 해당 다리여야 한다(`transaction_ids`는 입금 또는 출금 쪽 하나만 맞아도 된다). `include_rejected = false`이면 같은 (입금, 출금) 쌍의 `RejectedTransfer`가 있는 쌍을 뺀다. 이 조건에는 거래 `kind`, 보류(pending) 여부, 분할 자식 여부, 카테고리, 이름 조건이 없다. | 코드 확인 (없다 주장 검색 범위는 2.1) |
| R-08 | 같은 통화 분기 (`match_rank = 0`) | 출금 통화 = 입금 통화이고 `출금.amount = -입금.amount`(decimal 정확 일치, 오차 없음)인 쌍이다. 예: 은행 `+500000`(KRW)와 카드 `-500000`(KRW)는 후보이고, `+500000`과 `-499999`는 아니다. | 코드 확인 |
| R-09 | 다른 통화 분기 (`match_rank = 1`) | 통화가 다른 쌍 중 `ABS(입금.amount / (출금.amount × 환율))`가 `[1 − 오차, 1 + 오차]` 안인 쌍이다(양끝 포함). 환율은 출금 거래의 날짜(`출금.date`) 기준으로 저장된 `exchange_rates`만 읽는다(공급자 호출·±5일 보정 없음). 직접 환율 `출금 통화 → 입금 통화` 행이 있고 0이 아니면 그것, 아니면 `(출금 통화 → 가족 통화) / (입금 통화 → 가족 통화)`로 파생한다(통화가 가족 통화이면 그 항은 1). 환율이 없거나 분모가 0이면 식이 NULL이 되어 그 쌍은 빠진다. 예: 가족 통화 KRW, `USD→KRW` 행 `1350`, 출금 KRW `+1350000`이면 파생 환율은 1/1350이고 입금 USD `-1098`은 비율 `1.098`로 오차 0.1 안, `-1101`은 `1.101`로 밖이다. | 코드 확인 |
| R-10 | 자동 경로의 추가 제약 (`auto_match_transfers!`가 켜는 3개 옵션, C-10·C-13·C-14) | (a) `restrict_cross_currency_to_linked_accounts`: R-09 분기에서만 적용한다. 두 계정이 모두 연동 계정(`plaid_account_id`·`simplefin_account_id`가 있거나 `account_providers` 행이 있음, C-15)이거나, 같은 가족에서 같은 방향(같은 출금 계정 → 같은 입금 계정)으로 이미 `confirmed`인 `Transfer`가 하나라도 있어야 한다. 수동 계정끼리의 환율 매칭은 첫 확정 전까지 자동으로 제안되지 않는다. 같은 통화 분기(R-08)는 계정 종류와 무관하다. (b) `require_common_writer`: 같은 가족의 구성원 한 명(writer)이 있어서 다음을 모두 만족해야 한다. 입금 계정은 소유자가 없거나 writer가 쓸 수 있고, 출금 계정도 소유자가 없거나 writer가 쓸 수 있으며, writer가 입금 계정이나 출금 계정 중 적어도 하나를 쓸 수 있다(쓰기 = 소유자이거나 `full_control` 공유, U-02). 소유자 없는 계정끼리면 세 번째 조건이 실패해 쌍이 제외된다. (c) `exclude_same_wise_item`: 두 계정이 같은 Wise 연결(`wise_item`)의 `WiseAccount`에 각각 연결돼 있으면 두 분기 모두에서 제외한다. 거래 목록 hint와 수동 창은 이 셋을 켜지 않는다. | 코드 확인 |
| R-11 | 환율 오차(tolerance) 값 | 자동 경로 기본값은 `0.1`(10%)이다. `TRANSFER_MATCH_EXCHANGE_RATE_TOLERANCE`가 비어 있거나 숫자로 못 읽거나 무한이거나 음수이면 `0.1`로 되돌리고, 읽히면 최대 `0.5`로 자른다(`0.9` → `0.5`, `0.03` → `0.03`, `abc` → `0.1`, `-1` → `0.1`). 매 호출마다 읽는다. 수동 창은 `max(0.1, 자동 값)`을 쓴다. 거래 목록 hint는 고정 `0.03`이다. 후보 함수에 직접 넘기는 값은 C-09의 검증(숫자·유한·음수 아님)을 통과해야 한다. | 코드 확인 |
| R-12 | 후보 정렬과 중복 후보 | SQL은 `match_rank` 오름차순, `date_diff` 오름차순으로 정렬한다. 그 뒤 순서(rank·`date_diff`가 모두 같은 후보들)는 지정하지 않는다(U-01). 한 거래가 여러 후보에 들어갈 수 있으므로 소비자는 이 순서로 하나씩 고른다(R-13). 같은 통화 후보가 다른 통화 후보보다 날짜가 하루 더 멀어도 먼저다. | 코드 확인 |

**자동 매칭 실행**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | `auto_match_transfers!(account?, tolerance?)` (C-10) | 가족 설정 `auto_match_transfers_disabled`가 true면 즉시 끝나고 아무것도 만들지 않는다(반환 nil). 아니면 `date_window = 4`로 R-07~R-12의 후보를 `include_rejected: false`와 R-10의 세 옵션으로 구한다. 한 DB transaction 안에서 후보를 순서대로 훑으며 입금 id나 출금 id가 이번 실행에서 이미 쓰인 후보는 건너뛰고(탐욕 방식), 아니면 R-14로 `Transfer`를 찾거나 만든다. 만든 `Transfer`는 `status = pending`, `amount = 0`(설정하지 않음)이고, 두 다리의 `kind`·카테고리·`user_modified`는 바꾸지 않는다(확정 전에는 예산·리포트에 영향이 없다). 이미 같은 쌍이 존재해 찾기만 했으면 이번 실행에서 쓴 것으로 표시는 하되 신규 목록에는 넣지 않는다. 마지막에 이번에 새로 만든 `Transfer` 중 어느 한 계정이 `Loan`이고 `amortizable?`이고 `principal_only_transfers?`이면 그 `Transfer`의 두 다리와 수수료 거래 계정에 `sync_account_later`를 건다(대출 원금 replay가 이체를 쓰기 때문). 다른 경우 sync는 부르지 않는다. | 코드 확인 |
| R-14 | 후보 한 쌍의 `Transfer` 생성 경쟁 (`find_or_create_transfer!`, C-12) | savepoint(`requires_new`) 안에서 `find_or_create_by!(inflow, outflow)`를 한다. 동시 sync가 같은 쌍을 먼저 commit해 unique index 오류(`RecordNotUnique`)가 나면 그 쌍의 기존 행을 돌려준다(없으면 nil이라 후보를 건너뛴다). 거래별 unique 검증 오류(`taken`)가 나면 정확히 같은 쌍의 행이 있을 때만 그 행을 쓰고, 다른 쌍이 거래를 가져간 경우이면 nil(건너뜀)이다. `taken`이 아닌 검증 오류(예: 날짜·부호 검증)는 다시 던져 바깥 transaction 전체(이번 실행에서 만든 모든 `Transfer`)가 롤백된다. 후보 SQL이 이 검증을 이미 만족시키므로 실제로는 `taken`만 난다(추론). | 코드 확인 / 추론(그 밖의 검증 오류는 안 난다는 판단) |
| R-15 | 자동 매칭을 부르는 곳 | (a) 계정 sync의 post-sync가 `auto_match_transfers!(account: 그 계정)`을 부른다. (b) 가족 sync의 post-sync가 계정 인자 없이 부른다. (c) FinanceKit 연동 downstream이 부른다. (d) `AutoMatchTransfersJob`(큐 `medium_priority`)이 계정 인자 없이 부른다. 이 job은 설정 토글이 꺼짐에서 켜짐으로 바뀔 때 enqueue된다(R-34). 수동 이체·확정·삭제는 이 함수를 부르지 않는다. post-sync의 예외 처리와 중복 실행(정확히 한 번이 아님)은 sync-pipeline R-11이 갖는다. 같은 쌍을 두 번 만나도 R-07·R-14 때문에 두 번째는 아무것도 만들지 않으므로 반복은 안전하다. | 코드 확인 (호출처 검색 범위는 2.1) |
| R-16 | 거래 목록의 "Transfer?" hint 후보 (`transfer_hint_candidates`, C-11) | 대상 거래 중 `kind`가 이체 종류(R-35)이거나 `Transfer`가 이미 있는 거래는 뺀다. 남은 거래마다 `date_window = 2`, `tolerance = 0.03`, `include_rejected: false`로 후보를 구하고(R-10의 세 옵션은 끄고 `transaction_ids`로 한정), 후보 중 두 다리의 `category_id`가 같고(둘 다 nil 포함) 현재 사용자가 두 다리 계정 모두에 쓰기 권한이 있는 쌍만 남긴다. `transaction_ids_with_transfer_candidates`는 이 쌍에 든 거래 중 대상 목록에 있는 id의 집합이고, hint는 그 거래 행에 표시된다(해당 거래에 이미 `Transfer`가 있으면 hint 대신 pending·확정 표시). hint 후보에는 split 원본만 `excluded`로 빠지고 분할 자식은 포함된다(R-07). | 코드 확인 |
| R-17 | hint "Not a transfer" (`dismiss_transfer_hint!`, `DELETE .../transfer_match`) | 이 거래의 계정에 쓰기 권한이 필요하다(아니면 권한 오류로 돌아간다). 한 DB transaction 안에서 R-16이 이 거래에 대해 내놓는 모든 쌍마다 `RejectedTransfer`를 find_or_create한다. 그 결과 자동 경로와 hint는 이 쌍들을 다시 제안하지 않고 수동 창에는 계속 나온다(R-19, R-21). hint 후보가 하나도 없으면 아무 행도 만들지 않는다. 응답은 hint 표시를 지운다. | 코드 확인 |

**거절 기록**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | `Transfer#reject!` (C-05) | 한 DB transaction에서 `RejectedTransfer`를 (입금 id, 출금 id)로 find_or_create한 뒤 `Transfer`를 지운다. 지울 때 R-31이 돈다. 즉 `pending`이면 두 다리의 `kind`는 그대로이고, `confirmed`이면 두 다리가 `standard`로 돌아간다. 수수료 거래는 함께 지워진다. 웹의 거절(`transfer[status] = rejected`)·삭제 중 Wise 재링크 분기(R-30)·자동 매칭 화면의 일괄 거절이 이 함수를 쓴다. | 코드 확인 |
| R-19 | `RejectedTransfer`의 키와 효과 | 키는 (입금 `Transaction` id, 출금 `Transaction` id)의 순서 있는 쌍이다. 금액·날짜·계정으로 만든 키가 아니므로 거래의 금액이나 날짜를 나중에 고쳐도 거절은 유지된다. 한 거래가 다른 거래와 짝이 되는 것은 막지 않는다(그 쌍은 거절되지 않음). 효과: 자동 매칭(R-13)과 hint(R-16)는 `include_rejected = false`로 후보에서 뺀다. 수동 창과 `Transfer::Matcher`·`Transaction#transfer_match_candidates`는 `include_rejected`가 true라 거절된 쌍도 후보로 내고, 수동 창은 거절된 상대를 맨 뒤로 정렬한다(R-21). 수동 매칭 생성은 거절 기록을 지우지 않는다. 거절은 `Transfer`가 아닌 거래 쌍 기록이라 만료 기간이 없다. | 코드 확인 |
| R-20 | 거절 기록의 삭제 | 두 거래 중 하나가 지워지면 DB FK(`on_delete: :cascade`)가 그 거래의 모든 `RejectedTransfer` 행을 지운다. 거래 모델의 `has_one ..., dependent: :destroy`는 각 방향에서 한 행만 지우지만 DB cascade가 나머지를 지운다. 또 가족 금융 데이터 초기화(`Family::FinancialDataReset`)는 그 가족 거래에 걸린 `RejectedTransfer`를 `destroy_all`로 일괄 삭제한다(`family/financial_data_reset.rb:20,112,254-255`). 이 외에 거절 기록을 지우는 경로는 찾지 못했다(검색 범위는 2.1). 설정 토글을 끌 때는 거절 기록을 만들지 않는다(R-34). | 코드 확인 |

**수동 이체**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-21 | 수동 매칭 창의 후보 (`Transaction#transfer_match_candidates`, C-20, `GET .../transfer_match/new`) | 이 거래 `amount`가 음수면 입금 다리로, 아니면 출금 다리로 보고 `date_window = 30`, `tolerance = max(0.1, 자동 tolerance)`, `include_rejected = true`로 가족 전체 후보를 구한다(R-10의 세 옵션은 끔). 정렬: 거절된 상대가 맨 뒤, 그 앞에서는 이 거래와 같은 `category_id`인 상대가 먼저, 나머지는 SQL 순서(R-12, 동률은 위치 유지)다. 창은 현재 사용자가 쓰기 가능하고(`writable_by`) `visible`한 계정의 상대 거래만 목록에 보이며, 대상 계정 선택 목록은 쓰기 가능한 계정 중 이 거래 계정을 뺀 것이다. 이 창의 후보는 분할 자식 상대도 포함한다(R-23의 `Matcher`는 뺀다). | 코드 확인 |
| R-22 | 수동 매칭 생성 (`TransferMatchesController#create`, C-21) | 이 거래 계정에 쓰기 권한이 필요하고, 상대 계정에도 필요하다(없으면 `accounts.not_authorized` 알림으로 돌아간다). `method = new`이면 `target_account_id`로 고른 접근 가능 계정에 이 거래와 반대 부호·같은 날짜·같은 금액·**이 거래의 통화**인 새 거래(`user_modified = true`, 이름 `"Transfer to <입금 쪽이 아닌 계정 이름>"` 규칙: 이 거래가 입금이면 이 거래 계정 이름, 출금이면 대상 계정 이름)를 만든다. 그 외에는 `matched_entry_id`의 거래와 짝짓는다. 이 거래 `amount`가 음수이면 이 거래가 입금 다리, 양수이면 출금 다리다. 같은 (입금, 출금) 쌍의 `Transfer`가 이미 있으면(자동 pending) 그것을 `confirmed`로 쓰고 없으면 새로 만든다. 저장(검증 R-02 적용, 날짜 30일)과 `confirm!`(R-26)은 한 DB transaction이고 이어 두 다리·수수료 거래 계정의 sync를 예약한다. 이 컨트롤러는 R-21 후보 목록에 속하는지, `excluded`·분할 여부, 이미 다른 `Transfer`가 있는지를 따로 확인하지 않는다. 그래서 통화가 다르면 부호만 반대이면 어떤 쌍도 만들어지고, 검증 실패(`RecordInvalid`)는 컨트롤러에 rescue가 없다. | 코드 확인 (rescue 없음은 파일 전체 읽음) |
| R-23 | `Transfer::Matcher` (C-19, assistant 함수 `match_transfer`·`get_transfer_match_candidates`가 쓰는 연산) | `candidates`는 거래가 `excluded`이거나 분할 자식이면 빈 목록, 아니면 `date_window = 30`·R-21과 같은 tolerance·`include_rejected = true`로 구하고 상대가 분할 자식인 행을 뺀다. `TransferMatchesController`와 달리 `Transfer.amount`를 `outflow.entry.amount.abs`로 채운다(`matcher.rb:146-153`, `confirmed`로 저장). `match_with!(상대)`는 락 아래(`Transaction`·`Entry` 행을 id 순으로 잠그고 reload)에서 양쪽이 분할 원본·자식이 아니고(`split_transaction`), `excluded`가 아니고(`excluded_transaction`), `Transfer`가 없고(`already_linked`)를 확인하고, 상대가 `candidates`에 있어야 한다(`not_a_candidate`). `match_to_account!(계정)`은 같은 계정이면 `same_account`, 다른 가족이면 `account_not_found`이고, 이 거래와 반대 금액·같은 통화·같은 날짜의 새 거래(`user_modified = true`, 이름 `"Transfer to ..."`)를 같이 만든다. 성공하면 `confirmed`로 저장하고 `confirm!`한 뒤 sync를 예약한다. `RecordInvalid`·`RecordNotUnique`는 `invalid_transfer` 오류로 바뀐다. `dry_run`이면 저장 없이 검증만 한다. 권한 확인은 호출자 몫이다. | 코드 확인 |
| R-24 | 새 이체 생성 (`Transfer::Creator#create`, C-16·C-18, `POST /transfers`) | 컨트롤러가 두 계정을 접근 가능 계정에서 찾고 두 계정 모두 쓰기 권한을 확인한다(권한 판정은 U-02). 수수료가 음수이거나 환율이 0 이하이면 `ArgumentError`다(날짜 파싱 실패도 `ArgumentError`로 폼 오류 "date invalid"가 된다). 한 DB transaction(savepoint)에서 `confirmed` `Transfer`(`amount` = 입력)와 두 다리를 만든다. 출금 다리는 출발 계정·출발 통화·`amount`(양수)·입력 날짜·`user_modified = true`·`kind` = R-03이고 `investment_contribution`이면 카테고리를 `Family#investment_contributions_category`로 정한다. 이름은 `"<Payment 또는 Transfer> to <도착 이름>"`(도착이 부채면 `Payment`)이다. 입금 다리는 도착 계정·도착 통화·`-(amount를 도착 통화로 환산한 값)`·같은 날짜·`user_modified = true`·`kind = funds_movement`·이름 `"... from <출발 이름>"`이다. 환산은 `Money(amount.abs, 출발 통화).exchange_to(도착 통화, date, custom_rate: 입력 환율)`이다(money-currency-rules R-21, R-22: 통화가 같으면 환율 입력은 무시). 환율을 못 찾으면 `Money::ConversionError`이고 폼에 "exchange rate unavailable" 오류로 돌아간다. 수수료(출발·도착 각각 0보다 클 때)는 해당 계정에 `kind = standard`, 이름 `"Transfer fee — <Payment 또는 Transfer> to/from ..."`, 카테고리 "Fees"(가족 카테고리에서 찾거나 만듦), `amount` = 수수료(양수)인 별도 거래로 만들어 `Transfer`에 연결한다. 태그는 가족 태그만 두 다리에 붙인다. 저장 뒤 두 다리와 수수료 계정의 sync를 예약한다. `amount`가 0 이하이거나 숫자가 아닌 문자열(0으로 읽힘)이거나, 출발 계정과 도착 계정이 같으면 R-02 때문에 `RecordInvalid`가 나고 컨트롤러는 이 예외를 처리하지 않는다. 거래 이름은 영어 리터럴이고, 한국어 로캘은 카테고리 이름 번역 파일이 없어서 "Fees"·"Investment Contributions"가 영어 기본값(i18n fallback)으로 만들어진다(추론). | 코드 확인 / 추론(한국어 로캘 이름) |
| R-25 | `idempotency_key`가 있는 이체 생성 | 키는 UUID 형식(8-4-4-4-12 16진, 대소문자 무시)일 때만 받는다. 아니면 키가 없는 요청과 같다. 이미 출발 계정에 같은 키의 `Entry`가 있고 그 거래의 `Transfer`가 이번 요청과 같으면(출발·도착 계정, 날짜, 출금 금액, 입금 금액 = 이번 요청 환율로 환산한 값, 출발·도착 수수료 합계가 모두 같음) 새로 만들지 않고 그 `Transfer`를 돌려준다. 키는 있으나 내용이 다르면 새로 만들기를 시도하다가 unique index 오류가 나서 `StaleIdempotencyKeyError`이고 폼은 "stale form" 오류로 돌아간다. 키는 출금 다리 `Entry`에는 그대로, 입금 다리에는 `-inflow`, 출발 수수료 거래에는 `-source_fee`, 도착 수수료 거래에는 `-destination_fee`를 붙여 저장한다. 두 요청이 거의 동시에 오면 DB의 `(account_id, idempotency_key)` unique index가 하나만 통과시키고 진 쪽은 이긴 쪽 `Transfer`를 받는다. 환율을 다시 못 구하면 같은 요청이 아닌 것으로 본다. | 코드 확인 |

**확정·수정·삭제**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | `Transfer#confirm!` (C-05) | 한 DB transaction에서 `status`를 `confirmed`로 저장하고(검증 R-02: 30일 한도) 출금 다리 `kind`를 R-03 값으로, 입금 다리를 `funds_movement`로 저장한다. 출금 `kind`가 `investment_contribution`이고 출금 다리 `category_id`가 비어 있으면 카테고리를 `Family#investment_contributions_category`로 정한다(이미 카테고리가 있으면 유지). `kind`는 잠그지 않는다. pending이 아닌 `Transfer`에 불러도 거부하지 않고 같은 값을 다시 쓰므로, 이미 확정된 투자 `Transfer`의 사용자 선택(R-29로 잠근 `kind`)을 기본값으로 덮어쓴다. | 코드 확인 |
| R-27 | `PATCH /transfers/:id` (`update`, C-22) | 찾기: 이 사용자가 두 다리 모두에 접근 가능한 `Transfer`여야 한다(아니면 404, R-30). `status = rejected`이면 R-18의 거절 경로로 가고 권한은 R-30이다. 그 밖에는 출금·입금 두 계정에 쓰기 권한이 필요하다(없으면 목록으로 돌려보내며 알림). 통과하면 한 DB transaction 안에서 순서대로 (1) `status = confirmed`이면 `confirm!`, (2) 금액·수수료 변경(R-28), (3) `category_id`가 요청에 있으면 출금 다리 카테고리 저장, `notes`가 있으면 `Transfer.notes` 저장, (4) `investment_contribution` 키가 있으면 R-29. 키가 없는 항목은 건드리지 않는다. 이 경로는 `sync_account_later`를 부르지 않는다(U-04). | 코드 확인 (sync 없음은 2.1) |
| R-28 | 금액·수수료 수정 (`update_transfer_fees_and_amount`, C-23) | 요청의 `amount`가 있고 `Transfer.amount`(DB 값)와 다르면 금액 변경이다. 이때 출금 다리 `Entry.amount`를 새 값으로, 입금 다리 `Entry.amount`를 `-(새 값을 출발 통화 → 도착 통화로 `Transfer` 날짜(입금 다리 날짜) 환율 환산한 값)`으로 저장하고 `Transfer.amount`를 새 값으로 저장한다(환율을 못 찾으면 `Money::ConversionError`, 컨트롤러가 처리하지 않음). 수수료는 요청 값이 있고 현재 유도 값(수수료 거래 합)과 다르면 변경이다. 기존·새 모두 양수이면 수수료 `Entry.amount`를 바꾸고, 기존이 양수이고 새 값이 0이면 수수료 거래를 지우고, 기존이 0이고 새 값이 양수이면 "Fees" 카테고리의 `standard` 수수료 거래를 `Transfer` 날짜로 만들어 연결한다. `Transfer.amount`의 값은 생성 경로마다 다르다. `Creator`(R-24)는 입력 `amount`, `Matcher`(R-23)는 출금 금액 절댓값을 저장하고, 자동 매칭(R-13), `TransferMatchesController`(R-22), 규칙 액션 `SetAsTransferOrPayment`(`set_as_transfer_or_payment.rb:49-53`)는 설정하지 않아 DB 기본 0이다. 그래서 0인 `Transfer`에 0이 아닌 `amount` 요청이 오면 실제 금액이 같아도 항상 금액 변경으로 처리된다. 변경이 없으면 아무것도 하지 않는다. 화면(`transfers/show`)에는 금액·수수료 입력 칸이 없고 표시만 있어 이 경로는 파라미터로만 도달한다(추론: 뷰에서 입력 필드를 찾지 못함). | 코드 확인 / 추론(UI 도달 여부) |
| R-29 | 투자 기여 전환 (`update_investment_contribution!(enabled)`, C-04) | `confirmed`이고 R-03 기본값이 `investment_contribution`(도착이 투자·암호화폐이고 출발은 아님)인 `Transfer`만 전환할 수 있다. 아니면 false를 돌려주고 아무것도 하지 않는다(컨트롤러는 반환값을 쓰지 않으므로 오류 없이 지나간다). 전환할 수 있으면 한 DB transaction 안에서 출금 거래를 잠그고 `kind`를 `investment_contribution`(enabled)·`funds_movement`로 저장하고 `kind`를 잠근다. enabled이고 카테고리가 없으면 "Investment Contributions" 카테고리를 넣고, disabled이고 현재 카테고리 이름이 지원 로캘 전체의 투자 기여 이름 중 하나이면 카테고리를 비운다(다른 카테고리는 유지). `show` 화면은 두 계정 모두 쓰기 가능하고 `investment_contribution_switchable?`일 때만 토글을 그린다. | 코드 확인 |
| R-30 | `DELETE /transfers/:id`와 거절의 접근·권한 (`destroy`·`reject_transfer`·`set_transfer`, C-24) | 찾기: 삭제·거절은 두 다리 중 하나에만 접근 가능하면 찾고, `update`(확정 등)는 둘 다, 그 밖 동작(show 등)은 입금 다리 접근만으로 찾는다(접근 불가면 404). 권한: 삭제·거절은 한쪽 끝점의 쓰기 권한이 있으면 되고, `Transfer`에 수수료 거래가 있으면 수수료가 걸린 모든 계정에도 쓰기 권한이 있어야 한다(없으면 그 계정 기준으로 권한 오류). 동작: 삭제는 두 다리가 모두 Wise 출처이고 같은 Wise 연결의 시스템 링크이면(`WiseItem::InterbalanceLinker.relinks?`, U-05) `reject!`(R-18), 아니면 `destroy!`(거절 기록 없음)다. 웹 거절은 `Transfer`를 행 잠금 아래에서 처리한다. | 코드 확인 |
| R-31 | `Transfer` 삭제 때 다리 해제 (`release_transactions`, `before_destroy`, C-06) | 삭제 경로가 무엇이든(직접 삭제, 거절, 다리 거래·`Entry` 삭제의 연쇄, 자동 매칭 설정 끔) 삭제 직전에 살아남는 각 다리에 대해: 연쇄 삭제로 지워지는 다리(`destroyed_by_association`의 외래 키가 가리키는 쪽)와 이미 존재하지 않는 다리는 건너뛴다. 나머지 다리는 (a) `kind`가 이체 종류(R-35)이고 이 `Transfer`가 `pending`이 아니면 `kind`를 `standard`로 되돌리고 그 `kind` 잠금이 있으면 푼다(pending 매칭은 처음부터 `kind`를 바꾸지 않았으므로 그대로 둔다), (b) `Entry.idempotency_key`가 있으면 nil로 지운다(같은 키로 재시도한 생성 요청이 낡은 키에 걸리지 않게 하려는 목적, 코드 주석). 수수료 거래는 `Transfer`와 함께 삭제된다. 해제 중 `RecordNotFound`는 무시하고 `NoMethodError`는 그 다리를 건너뛴다. 카테고리는 되돌리지 않는다(확정 때 넣은 "Investment Contributions"가 남는다). | 코드 확인 |
| R-33 | `PATCH /transfers/:id/tags` | 두 다리 계정 모두에 annotate 권한(owner·full_control·read_write)이 필요하다. 가족 태그 중 요청에 있는 것만 골라 두 다리의 `tag_ids`를 한 DB transaction에서 같은 값으로 교체하고 `tag_ids` 잠금을 건다. 응답은 `{tag_ids}`(출금 다리 기준). | 코드 확인 |

**자동 매칭 화면과 설정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | 자동 매칭 화면과 일괄 처리 (`AutoMatchesController`, C-25) | 목록은 `pending` `Transfer` 중 두 다리 모두 현재 사용자가 접근 가능한 것을 `created_at` 내림차순으로 페이지에 나눠 보여준다(확정 버튼은 두 계정 모두 쓰기 가능할 때만 의미 있다). `bulk_update`는 `status`가 `confirmed`·`rejected`가 아니거나 `transfer_ids`가 비어 있으면 "invalid selection" 알림이다. 아니면 `pending`이고 두 다리 접근 가능한 선택 건 중 두 계정 모두 쓰기 가능한 것만 하나씩 `with_lock`으로 다시 읽어 아직 `pending`이면 `confirm!`(R-26) 또는 `reject!`(R-18)하고 처리 건수를 센다. 권한이 없거나 그 사이 다른 요청이 이미 처리한 건은 조용히 건너뛰고(이미 거절로 사라진 건은 `RecordNotFound`로 건너뜀), 건너뛴 건에 대한 오류는 없다. 한 건의 검증 오류(`RecordInvalid`)는 처리하지 않는다. 응답 문구는 처리 건수를 담는다. | 코드 확인 |
| R-34 | 자동 매칭 설정 (`update_settings`) | 가족 관리자(admin)만 바꿀 수 있다(아니면 `accounts_path`로 알림 리다이렉트). 한 Family DB transaction에서 `auto_match_transfers_disabled`를 저장한다. 꺼짐으로 바뀌면(이전에 켜짐) 가족의 pending `Transfer` 중 두 다리 `kind`가 모두 `standard`인 것(진짜 자동 제안)을 `destroy!`한다(`reject!`가 아니므로 거절 기록이 없어 다시 켜면 같은 쌍이 다시 제안된다). 다리에 이미 이체 `kind`가 있는 pending `Transfer`(데이터 가져오기·데모)는 남긴다. 꺼짐에서 켜짐으로 바뀌면 transaction 밖에서 가족 전체 매칭 job(R-15 (d))을 enqueue한다. 이미 같은 값이면 정리·job 모두 없다. | 코드 확인 |
| R-36 | `Transfer::InvestmentKindReconciler` (C-29, 일괄 정리 도구) | 도착 계정이 `Investment`·`Crypto`인 `Transfer`의 두 다리 중 `kind`가 이체 종류이고 `excluded`가 아니고 `kind`가 잠기지 않은 다리를 R-04의 값과 비교해 다르면 `kind`를 DB `update_columns`로 고치고 `Entry.updated_at`도 같이 갱신한다(캐시 키 무효화 목적). `dry_run`이면 바뀔 건수만 센다. 두 번 돌리면 두 번째는 바꿀 것이 없다. 결과는 확인한 `Transfer` 수와 `"<이전>-><이후>"`별 변경 수다. 호출처는 rake task `reconcile_investment_transfer_kinds`(환경변수 `DRY_RUN`, `FAMILY_ID`로 가족 한정, `lib/tasks/data_migration.rake:260-270`)뿐이고 웹 경로에서 부르는 곳은 찾지 못했다(2.1). | 코드 확인 |

- 불변식: (1) `Transfer`가 있는 두 다리는 서로 다른 계정, 같은 가족이고 입금 `amount < 0`, 출금 `amount > 0`이며 같은 통화면 합이 0이다(저장 시점. 이후 `Entry` 금액 편집은 이 검증을 거치지 않는다, R-28은 둘을 같이 고친다). (2) 한 거래는 입금 다리로 최대 한 `Transfer`, 출금 다리로 최대 한 `Transfer`에 속한다. (3) `pending` `Transfer`는 다리의 `kind`·카테고리 값을 바꾸지 않는다. 확정(R-26)이 처음 바꾼다. 다만 `categorizable?`에는 `status` 조건이 없어 pending 이체의 입금 다리도 카테고리 편집이 막힌다(R-05).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-12, R-13 | rank와 `date_diff`가 같은 후보들의 순서(예: 한 출금에 입금 후보 둘이 같은 날짜) | 어느 쌍이 `Transfer`가 되는지 결정이 DB 실행 순서에 달려 있다. 재구현은 임의 규칙(예: id 순)을 골라야 한다 | 원본 테스트 중 동률 사례가 있는지 열람(미열람) 또는 사용자 결정 |
| U-02 | R-10, R-16, R-22, R-27, R-30, R-32, R-33 | `Family` 테넌시와 `AccountShare` 권한 모델(쓰기 = 소유자 또는 `full_control` 공유, annotate = 소유자·`full_control`·`read_write`, 접근 = 소유·공유·가족 정책)의 정의. 이 스펙은 `Account.writable_by`(C-30)의 정의를 가정으로 쓰고, 소유자 없는 계정(`owner_id` nil)의 처리는 R-10 SQL만 확인했다 | 단일 사용자 재구현이면 권한 검사를 항상 통과로 둘 수 있으나 다중 사용자 시 동작이 이 가정에 달렸다 | 승인 범위 밖. 별도 스펙이 생기면 그쪽 R-ID로 교체 |
| U-03 | R-13, R-22, R-28 | 자동 매칭(R-13), `TransferMatchesController`(R-22), 규칙 액션이 만든 `Transfer.amount`가 0으로 남는 것(`Creator`와 `Matcher`는 금액을 채움)이 의도인지, 그리고 그 값이 `update`의 "금액 변경" 판정(`new_amount != Transfer.amount`)에 쓰이는 결과(요청 `amount`가 0이 아니면 항상 변경으로 처리)가 의도인지 | 재구현이 모든 경로에서 `amount`를 채우면 R-28의 변경 판정이 달라진다 | 개발자 의도는 코드로 확인 불가. 사용자 결정 또는 `Transfer.amount`의 다른 읽는 곳 전수 확인(이번엔 `app` 안 `.amount` 일부만 확인) |
| U-04 | R-27, R-28 | `PATCH /transfers/:id`가 금액·수수료를 바꾸고도 `sync_account_later`를 부르지 않는 것이 의도인지(다음 sync 전까지 두 계정 잔액이 낡을 수 있음) | 재구현이 잔액 일관성을 위해 sync를 부를지 정해야 한다 | 코드로는 호출이 없다는 것까지만 확인 가능. 사용자 결정 |
| U-05 | R-10, R-30 | Wise 연동 고유의 "재링크되는 쌍" 판정(`relinks?`)과 같은 연결 계정 제외(`exclude_same_wise_item`)의 상세. 연동은 사용자가 따로 만든다는 범위 규칙에 따라 이 스펙은 호출 지점만 정의한다 | 재구현에 Wise 같은 연동이 없으면 두 분기는 항상 false(삭제 = `destroy!`, 제외 없음)로 둔다 | 연동 구현 시 provider 스펙에서 정의 |

- 확인 한계: 테스트는 파일명 검색까지만 했고(`test/models/family/auto_transfer_matchable_test.rb`가 tolerance 환경변수를 다루는 것을 확인) 실행하지 않았다. 후보 SQL은 PostgreSQL에서 실행해 보지 않고 읽기만 했다(날짜 뺄셈이 정수 일수라는 점은 PG 의미를 읽은 판단). 거래 목록 UI의 pending 표시·확정 버튼 배치는 뷰 일부(`_transaction.html.erb`)만 읽었다.

### 1.5 필수 코드 참조

라이선스는 AGPL-3.0이다([overview](../overview.md) 1절). 아래 코드는 규칙 설명을 대신하는 용도로 지정했고, 복사하려면 AGPL-3.0 조건을 따라야 한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/transfer.rb:9-17`, `:269-301` `status` enum, `validates`, `transfer_has_*`, `transfer_within_date_range` | 상태 값과 검증 4종, 날짜 한도 30/4 | R-01, R-02 |
| C-02 | `app/models/transfer.rb:31-47` `Transfer.kind_for_account` | 도착 계정 종류 → 출금 `kind` 표 | R-03 |
| C-03 | `app/models/transfer.rb:112-136`, `:226-236` `kind_for_leg`, `investment_contribution_chosen?` | 다리 `kind` 계산과 사용자 선택 보존 | R-04, R-05 |
| C-04 | `app/models/transfer.rb:123-167` `investment_contribution_switchable?`, `update_investment_contribution!` | 투자 기여 전환 | R-29 |
| C-05 | `app/models/transfer.rb:173-206` `categorizable?`, `reject!`, `confirm!` | 분류 가능 판정, 거절, 확정 | R-05, R-18, R-26 |
| C-06 | `app/models/transfer.rb:19-22`, `:238-267` `release_transactions` | 삭제 때 다리 해제 | R-31 |
| C-07 | `app/models/transfer.rb:78-107` `name`, `payment?`, `transfer_type` | 이름·종류 표시 | R-06 |
| C-08 | `app/models/family/auto_transfer_matchable.rb:2-37` 상수, `exchange_rate_tolerance`, `manual_match_exchange_rate_tolerance` | tolerance 규칙 | R-11 |
| C-09 | `app/models/family/auto_transfer_matchable.rb:39-74` `transfer_match_candidates`, `:254-271` 인자 검증 | 후보 탐색 인터페이스 | R-07, R-11 |
| C-10 | `app/models/family/auto_transfer_matchable.rb:114-181` `auto_match_transfers!`, `sync_principal_only_loan_accounts` | 자동 실행 전체 | R-13 |
| C-11 | `app/models/family/auto_transfer_matchable.rb:76-112`, `:183-213` hint 함수, `dismiss_transfer_hint!` | hint 후보와 무시 | R-16, R-17 |
| C-12 | `app/models/family/auto_transfer_matchable.rb:215-252` `find_or_create_transfer!`, `existing_transfer` | 생성 경쟁 처리 | R-14 |
| C-13 | `app/models/family/auto_transfer_matchable.rb:273-327` `common_writer_condition_sql`, `same_wise_item_condition_sql`, `writer_can_write_sql` | 자동 경로 세 옵션 중 (b)(c) | R-10 |
| C-14 | `app/models/family/auto_transfer_matchable.rb:329-507` `transfer_match_candidates_sql` | 후보 SQL 전체(조건·환율식·정렬) | R-07~R-10, R-12 |
| C-15 | `app/models/family/auto_transfer_matchable.rb:509-521` `linked_account_sql` | 연동 계정 판정 | R-10 |
| C-16 | `app/models/transfer/creator.rb:8-88` `initialize`, `create` | 새 이체 생성 절차와 오류 | R-24, R-25 |
| C-17 | `app/models/transfer/creator.rb:93-151` `find_existing_transfer`, `matches_request?`, `entry_idempotency_attrs` | 멱등 키 처리 | R-25 |
| C-18 | `app/models/transfer/creator.rb:153-255` 다리·수수료 생성, `inflow_converted_amount`, `name_prefix` | 다리 속성·이름·환산 | R-24 |
| C-19 | `app/models/transfer/matcher.rb:20-153` `Transfer::Matcher` | 수동 매칭의 데이터 규칙과 락 | R-23 |
| C-20 | `app/models/transaction/transferable.rb:12-17`, `:20-65` `transfer`, `transfer_match_candidates`, `likeliest_first` | 다리 연결과 수동 창 후보 정렬 | R-20, R-21 |
| C-21 | `app/controllers/transfer_matches_controller.rb:1-104` | 수동 매칭 창·생성·hint 무시 | R-17, R-21, R-22 |
| C-22 | `app/controllers/transfers_controller.rb:93-120`, `:372-399` `update`, `update_transfer_status`, `update_investment_contribution`, `update_transfer_details` | 확정·수정 흐름 | R-27 |
| C-23 | `app/controllers/transfers_controller.rb:401-473` `update_transfer_fees_and_amount`, `update_fee_transaction` | 금액·수수료 수정 | R-28 |
| C-24 | `app/controllers/transfers_controller.rb:141-148`, `:210-264`, `:324-339` `destroy`, `set_transfer`, `reject_transfer`, `unlink_permission_account` | 접근·권한·삭제·거절 | R-30 |
| C-25 | `app/controllers/auto_matches_controller.rb:1-125` | 자동 매칭 화면·일괄 처리·설정 | R-32, R-34 |
| C-26 | `app/models/transaction.rb:80-104`, `:367-412` `TRANSFER_KINDS`, `UNCATEGORIZED_EXCLUDED_KINDS`, `transfer?`, `category_editable?`, `payment?` | 거래 쪽 이체 판정 | R-35 |
| C-27 | `app/models/account/syncer.rb:16-18`, `app/models/family/syncer.rb:22-24`, `app/jobs/auto_match_transfers_job.rb:1-5` | 자동 매칭 호출처 | R-15 |
| C-28 | `db/schema.rb:2277-2285`, `:2915-2927`, `:3285-3286`, `:3323-3325` `rejected_transfers`, `transfers`, FK | 컬럼·unique·cascade·CHECK | R-01, R-20 |
| C-29 | `app/models/transfer/investment_kind_reconciler.rb:20-74` | 투자 계좌 대상 `kind` 정리 | R-36 |
| C-30 | `app/models/account.rb:142-148` `WRITABLE_BY_CONDITION`, `writable_by` | 쓰기 가능 정의(U-02의 가정) | R-10, R-16, R-30 |
| C-31 | `app/views/transactions/_transaction.html.erb:223-245` | hint 표시와 무시 버튼 | R-16, R-17 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열람하지 않음).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-07, R-08, R-13 | 가족 통화 KRW. 은행 입출금(`Depository`, KRW) 거래 `+500000` 2026-03-25, 신한카드(`CreditCard`, KRW) 거래 `-500000` 2026-03-27(둘 다 `standard`, `excluded` false). `auto_match_transfers!` 실행 | `Transfer` 1건: 입금 = 카드 거래, 출금 = 은행 거래, `status = pending`, `amount = 0`. 두 거래 `kind`는 `standard` 그대로 |
| T-02 | R-26, R-03, R-05 | T-01의 `Transfer`를 `confirm!` | `status = confirmed`. 은행 거래 `kind = cc_payment`, 카드 거래 `kind = funds_movement`. `categorizable?` = false. 은행 거래 카테고리는 바뀌지 않음 |
| T-03 | R-07, R-02 | 은행 `+500000` 2026-03-25 대 카드 `-500000` 2026-03-29(차이 4일)와 2026-03-30(차이 5일) | 자동·hint·수동: 4일은 자동에서 후보, 5일은 자동에서 후보 아님(수동 창은 ±30일이라 5일도 후보). 4일 쌍의 pending `Transfer`는 저장 가능, 31일 차이 쌍은 확정 저장도 `within_days` 오류 |
| T-04 | R-08, R-02 | 은행 `+500000`(KRW)와 카드 `-499999`(KRW), 같은 날짜 | 어느 경로에서도 후보 아님(같은 통화는 정확 일치만, 환율 분기는 통화가 다를 때만). 수동 매칭을 강제로 요청하면 합이 0이 아니어서 `RecordInvalid` |
| T-05 | R-09 | 가족 통화 KRW, `USD→KRW` 환율 행 1350(출금 날짜). KRW 은행(연동 계정) `+1350000`, USD 증권(연동 계정) `-1098` 같은 날, 자동 tolerance 0.1 | 비율 1.098 → 자동 후보(rank 1). 입금이 `-1101`(비율 1.101)이면 후보 아님 |
| T-06 | R-10 | T-05와 같지만 두 계정이 모두 수동 계정이고 둘 사이에 confirmed 이체가 없음 | 자동 후보 아님. 거래 `+1350000`의 수동 창(±30일, tolerance 0.1)에서는 후보로 보임. 사용자가 한 번 확정한 뒤에는 같은 방향의 새 쌍이 자동 후보가 됨 |
| T-07 | R-12, R-13 | 은행 출금 `+100000` 2026-04-10, 카드B `-100000` 2026-04-10, 카드C `-100000` 2026-04-11(모두 KRW) | `Transfer` 1건만: (카드B, 은행). 카드C는 은행 출금이 이미 쓰여 건너뜀 |
| T-08 | R-12 | 같은 출금에 대해 같은 통화 후보(하루 뒤)와 환율 후보(같은 날, 오차 안) | 같은 통화 후보(rank 0)가 먼저 선택됨 |
| T-09 | R-18, R-19 | T-01의 pending `Transfer`를 거절(`transfer[status] = rejected`) | `Transfer` 삭제, `RejectedTransfer(입금=카드 거래, 출금=은행 거래)` 1행, 두 거래 `kind`는 `standard` 그대로. 이후 `auto_match_transfers!`는 이 쌍을 다시 만들지 않는다. 은행 거래의 수동 창에는 카드 거래가 맨 뒤 후보로 나온다 |
| T-10 | R-31 | confirmed 이체(은행 → 카드, 출금 `cc_payment`/입금 `funds_movement`) 후 카드 쪽 `Entry` 삭제 | `Transfer` 삭제, 은행 거래 `kind = standard`(잠겨 있었다면 잠금 해제), 은행 `Entry.idempotency_key = nil`. pending 이체였다면 은행 거래 `kind`는 원래 값 그대로 |
| T-11 | R-24, R-03 | 은행(`Depository`, KRW) → 증권(`Investment`, KRW) `amount = 1000000`, 날짜 2026-05-02, 수수료 없음 | confirmed `Transfer`. 출금 거래: 은행, `+1000000`, `kind = investment_contribution`, 카테고리 "Investment Contributions", 이름 `Transfer to <증권 계좌명>`. 입금 거래: 증권, `-1000000`, `kind = funds_movement`, 이름 `Transfer from <은행 이름>`. 두 `Entry` 모두 `user_modified = true` |
| T-12 | R-24, R-03 | 증권(`Investment`) → 증권(`Investment`) 같은 요청, 은행 → 카드(`CreditCard`) `amount = 300000` | 증권 → 증권: 출금 `kind = funds_movement`, 카테고리 없음. 은행 → 카드: 출금 `kind = cc_payment`, 이름 `Payment to <카드 이름>` |
| T-13 | R-24 | `amount = 0`, 또는 출발 = 도착 계정 | `RecordInvalid`(R-02)가 나고 컨트롤러가 처리하지 않는다. `amount = 1000`, `exchange_rate = 0` → `ArgumentError`, 폼 "date invalid" 오류 메시지가 붙는다(원본의 ArgumentError rescue가 날짜 메시지를 쓴다) |
| T-14 | R-25 | 같은 UUID 키로 같은 요청을 두 번 | 두 번째는 첫 번째와 같은 `Transfer`를 돌려주고 새 행이 없다. 같은 키로 `amount`를 바꾼 요청은 `StaleIdempotencyKeyError` |
| T-15 | R-11 | 환경변수 `0.03` / `abc` / `0.9` / `-1` / 미설정 | 자동 tolerance가 각각 `0.03` / `0.1` / `0.5` / `0.1` / `0.1`. 수동 창은 `max(0.1, 값)` = `0.1` / `0.1` / `0.5` / `0.1` / `0.1` |
| T-16 | R-16, R-17 | 거래 `+200000`(카테고리 없음)과 다른 계정 `-200000`(카테고리 식비), 같은 날짜 | hint 후보 아님(카테고리가 다름). 둘 다 카테고리 없음이면 후보. 후보인 상태에서 hint를 무시하면 그 쌍의 `RejectedTransfer`가 생기고 hint는 사라진다 |
| T-17 | R-34 | 설정을 끔: pending `Transfer` 둘(하나는 두 거래 모두 `standard`, 하나는 출금 `funds_movement`) | 앞의 것만 삭제, `RejectedTransfer` 없음, 뒤의 것은 남음. 다시 켜면 job이 enqueue되고 삭제된 쌍이 다시 제안될 수 있음 |
| T-18 | R-32 | `bulk_update`로 `confirmed`, 선택 3건 중 1건은 한쪽 계정이 읽기 전용 공유, 1건은 그 사이 이미 confirmed | 나머지 1건만 `confirm!` 처리, 알림 건수 1, 오류 없음 |
| T-19 | R-29 | confirmed 은행 → 증권 이체에서 `investment_contribution = false` / pending 이체에서 같은 요청 | confirmed: 출금 `kind = funds_movement`, 잠금, 카테고리가 "Investment Contributions"이면 비움. pending: 아무 변화 없이 지나감 |
| T-20 | R-22 | 거래 A `-80`(USD 계정), 거래 B `+105000`(KRW 계정), 같은 날짜, 사용자가 둘 모두 쓰기 가능, 수동 매칭 요청 | 통화가 달라 환율 검증 없이 `confirmed` `Transfer`가 만들어진다(부호만 반대이면 됨). 둘 다 양수이면 `RecordInvalid`로 처리되지 않은 오류 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@1cd94e6 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-28 `transfer.rb:11-12`, `schema.rb:2915-2927`, `:3324-3325` | `taken`은 `validates uniqueness`로 읽었다. `transfers.status` 기본값은 schema 줄 2921, `amount` 기본 0과 CHECK는 2916·2927. |
| R-02 | C-01 `transfer.rb:269-301`, `config/locales/models/transfer/en.yml:20-23` | `count: max_days` 오류 키로 한도를 확인. 경계는 `date_diff > max_days`(초과만 오류)라서 4일·30일은 통과. |
| R-03 | C-02, 호출처 `app/models/transfer/creator.rb:246`, `app/models/family/data_importer.rb:1128`, `app/models/demo/financekit_generator.rb:163` | 호출처 검색: `grep -rn "Transfer.kind_for_account" app lib config`. assistant 쪽 호출은 `app/models/assistant/function/match_transfer.rb:150`(dry run 응답의 `outflow_kind`, 도착 계정만 넘겨 출발 계정이 투자여도 `investment_contribution`이 나올 수 있다). 규칙·자동 확정·수동은 `confirm!`(transfer.rb:195)이 같은 함수를 부른다. |
| R-04 | C-03 | 코드 확인. |
| R-05 | C-05 `transfer.rb:173-177`, C-26 `transaction.rb:104` | 코드 확인. "stale 방지" 목적은 코드 주석(transfer.rb:169-172) 근거라 추론. |
| R-06 | C-07, `money-currency-rules` R-37의 부채 정의 | 코드 확인. 부채 판정(`liability?`)은 `classification` enum(`account.rb:81`)이고 종류별 값은 money-currency-rules가 확인. |
| R-35 | C-26 | 코드 확인. |
| R-07 | C-14 `auto_transfer_matchable.rb:378-413`, `:421-503` | "kind·보류·분할 자식·카테고리 조건이 없다"는 SQL 두 분기의 WHERE·JOIN 조건을 읽어 확인한 것이다. 놓쳤을 가능성: 후보 이후 Ruby에서 거르는 단계(`Matcher.candidates`는 분할 자식을 거르고, hint는 카테고리를 거른다. 자동 경로에는 없음). 분할 자식 `excluded`는 거래 소유로 transactions R-23(자식은 `excluded`가 줄 값)이다. |
| R-08 | C-14 `:380-388` | 코드 확인. 인덱스 `index_entries_on_transfer_match_lookup`(schema.rb:740)이 (`currency`, `amount`, `date`, `account_id`) 조회용인 것을 확인. |
| R-09 | C-14 `:421-503` | 환율 3개 LEFT JOIN은 모두 `outflow_candidates.date`와 정확히 같은 날짜 행(`:432-446`). 환율 저장소의 날짜 보정(money-currency-rules R-25의 5일)은 이 SQL에 없다. 파생 환율 식은 `:487-491`. 수치 예(`1350`, 1.098)는 이 식을 손으로 계산한 값이다(실행하지 않음). |
| R-10 | C-10 `:124-138`, C-13, C-14 `:444-468`·`:496-503`, C-15 | `confirmed_routes`는 `restrict...` 가 true일 때만 행이 생기는 서브쿼리(`:462`). `(b)`의 SQL은 `common_writer_condition_sql`(`:280-291`). 실행하지 않음. |
| R-11 | C-08 `:28-37`, `.env.example:141`, `test/models/family/auto_transfer_matchable_test.rb:345-404`(파일명·사례명 검색으로 존재만 확인) | `Float(x, exception: false)`의 `nil`·무한·음수 처리를 읽고 `abc → 0.1` 등을 도출. 테스트 본문은 열지 않음. |
| R-12 | C-14 `:505` | "동률 순서를 지정하지 않는다"는 ORDER BY에 두 키만 있는 것을 읽은 부재 주장이다(검색 범위: 이 SQL 한 곳). `Transaction#likeliest_first`는 수동 창에서만 재정렬(R-21). U-01. |
| R-13 | C-10 | `Transfer`의 `amount`가 설정되지 않는다는 점: `find_or_create_by!(inflow, outflow)`만 호출(`:226-229`)하고 DB 기본 0(R-01 근거). 검색: `grep -n "amount" app/models/family/auto_transfer_matchable.rb`에서 `amount`는 SQL 안에만 있음. |
| R-14 | C-12 | 코드 확인. "그 밖의 검증 오류는 안 난다"는 후보 SQL이 검증을 만족시킨다는 읽은 판단이라 추론(날짜·부호는 SQL 조건과 같다). |
| R-15 | C-27, `app/models/financekit/downstream.rb:53`, `app/controllers/auto_matches_controller.rb:37`, `app/models/up_entry/processor.rb:129`(주석만) | 검색: `grep -rn "auto_match_transfers" app lib config --include=*.rb --include=*.erb`. 놓칠 수 있는 곳: 동적 호출·rake task·`lib/`(검색 대상에 포함, 결과 없음)·`script/`·`db/`(검색 안 함). post-sync 예외 삼킴은 sync-pipeline R-11. |
| R-16 | C-11 `:183-213`, `app/controllers/transactions_controller.rb:56`, `:206`, `app/controllers/accounts_controller.rb:179` | 호출처 검색: `grep -rn "transaction_ids_with_transfer_candidates\|transfer_hint_pair_ids" app`. 분할 자식 포함은 SQL에 조건이 없다는 부재 주장(R-07과 같은 범위). |
| R-17 | C-11 `:99-112`, C-21 `:29-38`, C-31 | 코드 확인. |
| R-18 | C-05 `:179-184`, 호출처 `transfers_controller.rb:146`, `:250`, `:378`, `auto_matches_controller.rb:75`, `app/models/assistant/function/review_transfer.rb:68`, `app/models/assistant/function/unmatch_transfer.rb:93` | 호출처 검색: `grep -rn "reject!" app` 결과 중 `Transfer` 것만 골랐다. `transfers_controller.rb:378`의 분기는 `update`가 `rejecting?`이면 먼저 `return reject_transfer`(`:94`)하므로 실제로는 도달하지 않는다(코드 읽음). |
| R-19 | C-28 `schema.rb:2277-2285`, C-14 `:394-397`, `:473-476`, C-20 `:52-53` | 키와 효과는 코드 확인. "만료 없음"은 부재 주장: 거절 기록을 지우는 코드는 R-20의 cascade와 `Entry` 삭제뿐이다. 검색: `grep -rn "RejectedTransfer" app lib db/seeds.rb`. 삭제 경로는 `Family::FinancialDataReset`(`financial_data_reset.rb:20,112,254-255`, 가족 초기화 시 일괄 `destroy_all`)이 하나 더 있다. 그 외 `Family::DataImporter`(`:1137-1148`)·`DataExporter`·`SureImport::Preflight`·Sharesight 연동(`cash_router.rb:169-170`, `transfer_linking.rb:22`)은 읽기·생성 쪽이었다. |
| R-20 | C-28 `:3285-3286`, C-20 `:15-17` | `has_one ... dependent: :destroy`가 한 행만 다룬다는 점은 Rails 의미를 읽은 추론이지만 결과는 DB cascade가 보증한다. 일괄 삭제 경로: `app/models/family/financial_data_reset.rb:20,112,254-255`. 위 검색은 `app lib db/seeds.rb`이고 `db/migrate`·`script`는 검색하지 않았다. |
| R-21 | C-20 `:24-65`, C-21 `:4-9`, `:45-59` | 코드 확인. `likeliest_first`의 정렬 키는 `[거절 여부, 카테고리 일치 여부, 원래 위치]`. `visible`은 계정 scope로 정의는 account-balances 소관. |
| R-22 | C-21 `:11-26`, `:61-103` | 코드 확인. "rescue가 없다"는 파일을 끝까지 읽은 부재 주장이다(상위 `ApplicationController`의 rescue_from은 열지 않음, 놓쳤을 가능성). |
| R-23 | C-19, 호출처 `app/models/assistant/function/match_transfer.rb`(파일명 검색으로 존재 확인, 본문 일부 열람) | 코드 확인. 호출처는 `grep -rn "Transfer::Matcher\|match_with!\|match_to_account!" app`로 찾았고 `match_transfer.rb:110-111`(`match_with!`·`match_to_account!`)과 `get_transfer_match_candidates.rb:62`(`candidates`)뿐이다. `Transfer.amount` 값: `matcher.rb:146-153`은 `amount: outflow.entry.amount.abs`, 반면 `transfer_matches_controller.rb:73-103`과 `set_as_transfer_or_payment.rb:49-53`은 `find_or_initialize_by`에 amount가 없다(R-28). |
| R-24 | C-16, C-18, C-26 없음. `app/controllers/transfers_controller.rb:35-91`, `config/application.rb:35`, `config/locales/models/category/` 목록 | 한국어 로캘: `ls config/locales/models/category`에 `ko.yml`이 없고 `config/application.rb:35`에 `i18n.fallbacks = true`. 기본 로캘이 `en`인지 열지 않아 추론. 수수료 카테고리 키 `models.category.defaults.fees`는 `en.yml:28`이 "Fees". |
| R-25 | C-16 `:69-88`, C-17 | `matches_request?`의 비교 항목은 `:121-134`. UUID 정규식은 `transfers_controller.rb:350`. |
| R-26 | C-05 `:190-206` | 코드 확인. "pending이 아닌 Transfer에도 불러도 거부하지 않는다"는 `confirm!` 본문에 가드가 없는 것을 읽은 부재 주장이다. 컨트롤러 `update`는 상태 확인이 없다(`transfers_controller.rb:93-120`). 호출처는 `grep -rn "confirm!" app`. |
| R-27 | C-22, C-24 | sync 호출 없음: `grep -n "sync" app/controllers/transfers_controller.rb`가 주석 한 줄(144)만 나옴. `Entry`의 `after_save`는 `track_earliest_saved_date`뿐(`entry.rb:87`)이라 저장이 sync를 부르지 않는 것을 확인. `Transaction`·`Transfer` 모델의 콜백에서는 sync 호출을 찾지 못했다(검색: `grep -n "sync" app/models/transfer.rb app/models/transaction.rb`는 `Transfer#sync_account_later`만 해당). |
| R-28 | C-23 | 코드 확인. UI 입력 없음: `grep -n "amount\|source_fee\|destination_fee" app/views/transfers/show.html.erb`가 표시 코드만 반환. `_form.html.erb`는 새 이체용이다. |
| R-29 | C-04, C-22 | 코드 확인. |
| R-30 | C-24 | 코드 확인. Wise 분기의 `relinks?` 정의는 `wise_item/interbalance_linker.rb:49-57`만 읽었고 `system_link?` 본문은 부분만 읽었다(U-05). |
| R-31 | C-06, C-20 `:12-13`, `app/models/entry.rb:33` | 연쇄 삭제 경로: `Entry` → `delegated_type :entryable, dependent: :destroy`(`entry.rb:33`) → `Transaction` `has_one :transfer_as_*, dependent: :destroy` → `Transfer#before_destroy`. 카테고리가 되돌려지지 않는다는 점은 `release_transactions` 본문에 카테고리 처리가 없는 것을 읽은 부재 주장. |
| R-32 | C-25 `:8-21`, `:47-87` | 코드 확인. |
| R-33 | `app/controllers/transfers_controller.rb:122-139` | 코드 확인. |
| R-34 | C-25 `:23-45`, `:101-120`, `app/controllers/application_controller.rb:24-30` | 코드 확인. 데이터 가져오기·데모가 `kind`를 미리 정한 pending을 만든다는 근거는 코드 주석(`:110-113`)이다(추론). |
| R-36 | C-29 | 호출처 검색: `grep -rn "InvestmentKindReconciler" app lib config`가 정의 파일 외에 `lib/tasks/data_migration.rake:260-270`(`reconcile_investment_transfer_kinds`)을 찾았다. 이 task는 `DRY_RUN`·`FAMILY_ID`를 받는다. 웹·job 호출은 이 검색 범위에서 없었고 `db/migrate`·`script`는 검색하지 않았다. |
| T-01~T-20 | 각각 관련 R-ID의 C-ID. T-03·T-05·T-15의 수치는 SQL·`Float()` 의미를 읽어 손으로 도출했다(실행하지 않음). | 구현에서 도출. T-13의 두 번째 사례는 `ArgumentError` rescue가 날짜 오류 메시지를 붙이는 것(`transfers_controller.rb:75-82`)을 읽은 결과이고 그 동작이 사용자 의도인지는 판단하지 않았다. |

### 2.2 코드 읽는 순서

1. `family/auto_transfer_matchable.rb`의 `auto_match_transfers!`(`:114`)와 후보 SQL(`:368`)로 후보 선택을 읽는다. 환율 식은 `:487-491`이다.
2. `transfer.rb`의 `confirm!`·`reject!`·`release_transactions`와 `kind_for_account`로 상태 변화를 읽는다.
3. 수동 경로는 `transfer_matches_controller.rb`, `transfer/matcher.rb`, `transfer/creator.rb` 순서다. 세 경로 모두 최종적으로 `Transfer` 저장 + `confirm!`을 한다(`Creator`는 `confirmed`로 만들며 `confirm!`을 부르지 않고 `kind`를 직접 정한다).
4. 후보 SQL의 구현 전략은 단일 쿼리 안에서 같은 통화(rank 0)와 환율(rank 1) 두 분기를 `UNION ALL`로 합치고 Ruby에서 탐욕으로 소비하는 것이다. 구현할 때 같은 통화 매칭에는 `(currency, amount, date, account_id)` 인덱스(schema.rb:740)가 쓰인다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-05가 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-36 전부와 C-01~C-31 표본, T-05·T-07·T-15 재계산, 부재 주장 R-07·R-15·R-22·R-27 반증 시도. 일치 약 34개, 불일치 4건(중요 3, 사소 1), 누락 3건이 나왔다. 작성자가 코드로 다시 확인해 전부 반영했다. 누락 중 `pending` `Transfer`의 입금 다리 카테고리 차단은 `transactions` R-10 정정으로 이어졌다.
- **메인 표본 점검**: R-23·R-28(`Matcher#build_transfer`의 `amount`, `matcher.rb:146-153`), R-36(rake 호출처, `lib/tasks/data_migration.rake:260-270`), R-19·R-20(`family/financial_data_reset.rb:20,112,254`), R-05(`transaction.rb:398-400`, `transfer.rb:173-177`)를 원본에서 직접 확인했다.
- **대조하지 못한 것**: 후보 SQL의 PostgreSQL 실행 결과, 뷰의 `pending` 표시, `WiseItem` 판정(U-05), 기본 로캘이 `en`인지(R-24 추론).
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-08, R-09 | 한국 사용(원화↔원화 카드 대금·증권 이체)은 같은 통화 분기만 쓰고, 달러 증권 계좌 등 외화 이체는 수동 매칭 창으로만 두는 선택지가 있다. 원본은 환율 분기도 지원한다 | 자동 환율 매칭은 연동 계정에만 켜지고 환율 행이 있어야 동작한다. 사용자가 별도로 만들 연동의 범위가 정해지면 다시 정한다 | 결정 시 R-09·R-10을 제거하거나 유지 |
| R-24, R-06 | 한국어 UI에서 이름(`Transfer to`·`Payment to`)과 기본 카테고리("Fees", "Investment Contributions")를 한국어로 만들지 정한다 | 원본의 거래 이름(`Transfer to`·`Payment to`·`Transfer fee —`)은 I18n이 아닌 영어 문자열 리터럴이고(`creator.rb:163`, `:185`, `:211`), 카테고리 이름은 한국어 번역 파일이 없어 영어로 저장된다(추론) | 카테고리 매칭이 이름 문자열(R-29의 `all_investment_contributions_names`)을 쓰므로 한국어 이름을 쓰려면 그 목록도 확장해야 한다 |
| R-19 | 거절 키를 거래 id 쌍으로 두는 원본 방식을 유지할지, 연동 거래가 재import돼 id가 바뀌는 경우(원본의 provider가 거래를 교체하는 경로는 이 스펙에서 다루지 않음)에 대비해 외부 id 기준으로 둘지 | 외부 거래 id가 바뀌지 않는 연동을 가정하면 원본 방식으로 충분하다 | 키 변경 시 R-19·R-20 수정 |
