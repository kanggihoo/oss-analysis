---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/recurring_transaction.rb
  - app/models/recurring_transaction/schedule.rb
  - app/models/recurring_transaction/identifier.rb
  - app/models/recurring_transaction/matcher.rb
  - app/models/recurring_transaction/allocator.rb
  - app/models/recurring_transaction/pipeline.rb
  - app/models/recurring_transaction/cleaner.rb
  - app/models/recurring_transaction/price_change_detector.rb
  - app/models/recurring_transaction/occurrence_generator.rb
  - app/models/recurring_transaction/history_backfiller.rb
  - app/models/recurring_transaction/paycheck_planner.rb
  - app/models/recurring_transaction/classifier.rb
  - app/models/recurring_transaction/frequency_preset.rb
  - app/models/recurring_transaction/declared_bill.rb
  - app/models/recurring_transaction/ai_setup_suggester.rb
  - app/models/recurring_occurrence.rb
  - app/models/recurrence_rule.rb
  - app/models/recurring_allocation.rb
  - app/models/recurring_price_change.rb
  - app/models/recurring_match_rejection.rb
  - app/models/family/sync_complete_event.rb
  - app/models/family.rb
  - app/models/transfer.rb
  - app/models/sync.rb
  - app/jobs/identify_recurring_transactions_job.rb
  - app/jobs/generate_recurring_occurrences_job.rb
  - app/jobs/backfill_recurring_history_job.rb
  - app/controllers/bills_controller.rb
  - app/controllers/bills_feeds_controller.rb
  - app/controllers/recurring_transactions_controller.rb
  - app/controllers/recurring_occurrences_controller.rb
  - app/controllers/recurring_allocations_controller.rb
  - app/controllers/transactions_controller.rb
  - app/controllers/transfers_controller.rb
  - app/controllers/concerns/recurring_feature_guardable.rb
  - app/controllers/concerns/preview_gateable.rb
  - app/controllers/concerns/localize.rb
  - app/models/transaction.rb
  - app/models/account.rb
  - app/models/family/data_importer.rb
  - app/models/assistant/function/update_bill.rb
  - app/controllers/api/v1/recurring_transactions_controller.rb
  - lib/tasks/recurring_bills.rake
  - config/schedule.yml
  - config/routes.rb
  - config/application.rb
  - db/schema.rb
depends:
  - ./transactions.md
  - ./money-currency-rules.md
  - ./sync-pipeline.md
status: draft
---

# 정기 거래·청구서 (RecurringTransaction)

> 가족의 거래 내역에서 반복 지출·수입을 찾아내거나 사용자가 직접 선언한 청구서·구독·급여를 받아, 회차(occurrence)별 일정을 만들고, 들어온 거래를 회차에 연결해 납부 상태를 관리하며, 가격 변동 감지와 급여일 기준 지출 계획(paycheck planner)을 제공하는 기능을 정의한다.

이 문서에서 쓰는 이름은 아래와 같다. 반복 규칙 한 묶음을 `series`(`recurring_transactions` 행 하나), 그 규칙이 낳는 날짜별 항목을 `occurrence`(`recurring_occurrences` 행), 거래와 occurrence의 연결을 `allocation`(`recurring_allocations` 행)이라고 부른다. `Entry`와 `Transaction`의 뜻은 [transactions](./transactions.md) 1부 첫 문단과 같다. 금액 부호는 [money-currency-rules](./money-currency-rules.md) R-36을 따른다(`Entry.amount` 음수는 수입, 0 이상은 지출).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

대표 흐름은 "넷플릭스 17,000원이 3개월 연속 결제되고, 사용자가 확인해서 청구서가 되고, 다음 결제가 자동으로 납부 처리된다"이다. 정확한 기준은 1.4다.

1. 은행·카드 sync가 끝나면 Family 완료 이벤트가 정기 거래 식별을 예약한다. 30초 debounce 뒤 job이 가족별 advisory lock을 잡고 파이프라인을 돈다(R-22, R-23).
2. 식별기(Identifier)가 최근 3개월 거래를 (가맹점 또는 이름, 통화, 계정)으로 묶고, 금액을 평균의 ±7.5% 안에서 군집화한다. 군집이 3건 이상이고 마지막 거래가 45일 안이고 모든 거래일이 기대일에서 2일 이내이면 `suggested` series를 만든다. 이미 있는 series와 금액이 7.5% 안이면 새로 만들지 않고 그 series의 이력 필드만 갱신한다(R-13~R-17).
3. 사용자가 제안을 확인하면 `active`가 되고, 지난 6개월 occurrence 이력을 만들어 실제 거래와 맞춰 본다. 사용자가 직접 선언하거나 거래에서 "정기 거래로 표시"해도 `active` series가 바로 생긴다(R-01, R-27, R-35, R-61).
4. `active` series마다 일정 엔진(Schedule)이 오늘 이후 90일(분기·연 단위면 다음 회차까지) occurrence를 `scheduled`로 만든다(R-06, R-33).
5. 매칭기(Matcher)가 열린 occurrence와 거래를 점수로 비교한다. 0.85 이상이고 모호하지 않으면 `confirmed` allocation으로 자동 연결하고, 0.60 이상이면 사용자 검토용 `suggested` allocation을 남긴다. 연결된 금액이 기대 금액에 차면 occurrence가 `paid`로 닫힌다(R-37~R-43).
6. 두 번 연속 단일 거래로 같은 새 금액이 확정되면 가격 변동으로 기록하고, 자동 감지 series는 금액을 바꾼다(R-46).
7. 사용자는 청구서 화면에서 연체·이번 달·이후·납부 완료를 보고, 달력과 iCal로 받고, 직접 선언한 급여일을 기준으로 기간별 지출 계획을 본다(R-50~R-60, R-65).

### 1.2 범위·통합 지점

- 제공:
  - series 모델과 상태(`suggested`/`active`/`paused`/`inactive`/`ended`), 규칙 기반 일정 엔진, 주기 선택 UI의 규칙 변환(FrequencyPreset).
  - 자동 식별(Identifier, Classifier, 후보 목록), 선언 청구서(DeclaredBill), 거래·이체에서 만드는 정기 거래, 중복 판정(`covering`, `identity_taken_by`).
  - occurrence 생성·재생성·이력 재구성, 매칭(Matcher)과 정산(Allocator), 가격 변동 감지, stale 판정(Cleaner).
  - 청구서 화면(overview, all, calendar, paycheck, 상세)의 산정 규칙, 급여 계획(PaycheckPlanner), iCal feed 계약.
  - 파이프라인 job 3개와 sync 완료 후 호출 경계.
- 제외:
  - iCal 문서 렌더링 외의 feed 토큰 관리 세부와 "내보내기" 묶음(feature map 행 9). 이 문서는 feed의 입력·출력 계약만 쓴다(R-65).
  - AI 보조: `ai_setup_suggester.rb`(LLM으로 청구서 설정 제안), `bills/smart_configurations_controller`, `bills/ai_reviews_controller`, `recurring_transactions/smart_fills_controller`, 어시스턴트 도구 9개(`assistant/function/*bill*`). 외부 LLM 호출이 본체이고 결과는 사용자가 검토한 뒤 이 문서의 편집 경로(R-61, R-62)로 들어온다. `ai_setup_suggester.rb`는 읽었고(frontmatter), 제안 값을 프리셋 범위로 clamp한다는 것까지만 확인했다.
  - API v1 `recurring_transactions`(행 17). 쓰기 상태는 `active`/`inactive`만 받는다는 것(R-01)만 쓴다.
  - 예산의 청구서 예약(`budget_category.rb#bills_reservation`), 인사이트 생성기(구독 점검, 현금흐름 경고), `transactions` 목록의 예정 거래 표시 렌더링. 이 문서는 소비 쪽이 읽는 데이터 규칙(R-56)만 쓴다.
  - 뷰(ERB)·Stimulus. UI 문구와 레이아웃은 규칙이 아니라서 R-ID에 넣지 않았다.
  - 가맹점·카테고리 자동 부여(행 10), 이체 매칭 본문(행 3). 이 문서는 `Transaction.kind`의 이체 판정과 `Transfer` 쌍을 읽기만 한다.
- 외부 의존·선행 계약:
  - [transactions](./transactions.md): `Entry`·`Transaction` 필드(`amount`, `date`, `name`, `currency`, `excluded`, `account_id`, `merchant_id`, `category_id`, `kind`, `pending?`)와 `mark_as_recurring` 호출을 받는 쪽의 권한 확인(`require_account_permission!`). `kind`가 이체인지는 `Transaction::TRANSFER_KINDS = funds_movement, cc_payment, loan_payment, investment_contribution`(`transaction.rb:82`)이다.
  - [money-currency-rules](./money-currency-rules.md): `Money` 산술, `exchange_to`(환율 없으면 `ConversionError`, R-23), 통화 소수 자릿수.
  - [sync-pipeline](./sync-pipeline.md): Family `Sync`가 끝나면 완료 이벤트가 실행된다(R-11, R-18). 이 문서는 그 이벤트가 부르는 `identify_patterns_for`(R-23)만 소유한다. `Sync.any_incomplete_for?(family)`는 그 Family·Account·연동 item의 `Sync` 중 `pending` 또는 `syncing`이 하나라도 있으면 true다(`sync.rb:19`, `:131-133`, sync-pipeline R-32·C-07).
  - 호출자가 제공하는 것: PostgreSQL(advisory lock, partial unique index, `ILIKE`, `jsonb`), 가족별 job 큐와 지연 실행, cache(debounce 시각 저장, TTL 지원), 일 1회 cron, 계정 접근 판정(`accessible_by(user)`: 소유자이거나 `account_shares`에 있는 계정, `writable_by(user)`: 쓰기 권한 있는 계정), `Family.currency`·`Family.timezone`, 활성 계정 상태(`draft`·`active`가 화면에 보이는 상태, `account.rb:83`), 세제 혜택 계좌 id 목록(`family.tax_advantaged_account_ids`, R-59).
- 소유 상태·부작용: `recurring_transactions`, `recurrence_rules`, `recurring_occurrences`, `recurring_allocations`, `recurring_match_rejections`, `recurring_price_changes`(컬럼은 1.3, DDL은 C-01), `families.recurring_transactions_disabled`·`bills_feed_token`(값은 이 문서가 읽고 쓰는 것만 R-26·R-65), Rails cache 키 `recurring_transaction_identify:<family_id>`와 `bills:materialized:<family_id>`, Postgres advisory lock 두 종류(가족별 R-22, 거래별 R-44).

### 1.3 인터페이스와 데이터 의미

**series (`recurring_transactions`)**

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `family_id` | uuid | 필수. 모든 조회는 가족 안에서만. |
| `account_id` | uuid? | 비면 "어느 계정이든". 이체 series는 출금(source) 계정. |
| `destination_account_id` | uuid? | 있으면 이체 series. 값이 있으면 `account_id`도 필수이고 서로 달라야 하며 같은 가족이어야 한다. |
| `merchant_id`, `name` | uuid?, string? | 식별 키. 둘 중 하나는 있어야 한다(R-03). 감지는 가맹점이 있으면 `name`을 비우고, 없으면 거래 `name`을 쓴다. |
| `amount` | decimal(19,4) | 필수. 지출 양수, 수입 음수(R-02). 이체는 출금 금액(양수). |
| `currency` | string | 필수. |
| `expected_amount_min/max/avg` | decimal? | 관측된 변동 띠. 감지는 군집 전체의 부호 있는 값으로 채운다. |
| `amount_strategy` | enum | `fixed`(기본) / `average` / `last`. occurrence의 기대 금액 해석(R-32). |
| `amount_tolerance_pct` | decimal(5,2) | 기본 7.5. 매칭·닫힘·claim 허용 오차(R-39, R-43). |
| `expected_day_of_month` | int 1~31 | 필수. 월 단위 주기의 기준일. 규칙 없는 series의 유일한 일정 정보. |
| `anchor_date` | date? | N 주기마다 반복(interval>1)과 `after_count` 종료의 기준 회차. |
| `last_occurrence_date`, `next_expected_date` | date | 필수. 관측 이력과 캐시된 다음 날짜. 일정의 권위는 occurrence이고 이 둘은 힌트다(R-33, R-51). |
| `occurrence_count` | int ≥0 | 관측된 횟수(감지·수동 갱신이 쓰는 값). |
| `status` | enum | `suggested` / `active`(기본) / `paused` / `inactive` / `ended`. R-01. |
| `bill_type` | enum | `bill`(기본) / `subscription` / `installment` / `income` / `transfer` / `other`. |
| `manual` | bool | 사용자가 만들었으면 true(선언·거래에서 표시·이체에서 표시). 감지는 false. 급여일 판정(R-60)과 stale 기준(R-48)이 쓴다. |
| `autopay` | bool | true면 청구서 목록에 있지만 "해야 할 일(needs action)" 수에는 안 센다(R-51). |
| `weekend_adjust` | enum | `none`(기본) / `skip` / `before` / `after`. R-07. |
| `end_mode`, `end_on`, `end_after_count` | enum, date?, int? | `never`(기본) / `on_date` / `after_count`. 횟수는 1~600. |
| `match_days_early`, `match_days_late` | int | 기본 2, 7. 매칭 창(R-38). |
| `notify_days_before`, `overdue_grace_days` | int? | 비면 앱 기본 3, 3(R-31). |
| `dedup_scope` | string | 기본 `""`. 같은 정체성의 여러 금액 단계를 구분하는 키(R-04). |
| `matcher_hints` | jsonb map | `detected_name`, `name_aliases`(list), `learned_tolerance_pct`, `schedule_pinned_at`를 쓴다. |
| `category_id`, `payment_url`, `notes`, `trial_ends_on`, `renews_on`, `cancelled_on` | | 표시·알림용. `payment_url`은 http(s)만 허용(R-03). |
| `holiday_calendar`, `upcoming_window_days`, `replaced_by_id` | | 읽는 계산 코드를 찾지 못한 필드(R-49). import·export만 다룬다. |

**occurrence (`recurring_occurrences`)**: `recurring_transaction_id`, `family_id`, `original_due_on`(규칙이 낸 원래 날짜, 정체성), `due_on`(주말 보정 후 날짜), `snoozed_until`, `expected_amount`(null이면 series에서 해석), `currency`, `status`(`scheduled`/`paid`/`skipped`/`missed`), `closed_at`·`closed_source`(`auto`/`user`), `notes`. `(series, original_due_on)`이 unique다. `status = scheduled`일 때만 `closed_at`이 null이다.

**allocation (`recurring_allocations`)**: `recurring_occurrence_id`, `entry_id`(null 가능, 거래가 지워지면 null), `allocated_amount`(> 0, occurrence 통화), `source_amount`·`source_currency`(거래 통화 기준 금액), `state`(`suggested`/`confirmed`), `source`(`auto_matched`/`user_confirmed`/`user_created`), `match_confidence`(0~1, 4자리), `match_signals`(jsonb), `paid_on`(비면 거래 날짜, 없으면 오늘). `(occurrence, entry)`는 `entry_id`가 있을 때 unique다. DB에는 `(occurrence_id, currency)` 복합 FK가 있어 allocation 통화는 occurrence 통화와 같아야 한다. 계정이 지워지면 그 계정을 `account`나 `destination_account`로 가진 series도 DB cascade로 지워진다(`db/schema.rb:3269`, `:3278`).

**rule (`recurrence_rules`)**: `frequency`(`weekly`/`monthly`/`yearly`), `interval`(≥1), `day_of_month`(1~31 또는 -1=말일), `weekday`(0=일~6=토), `weekday_ordinal`(1~5 또는 -1=마지막), `month_of_year`(1~12), `position`. 규칙이 0개인 series는 "매월 `expected_day_of_month`일" 한 규칙과 같다.

**기타**: `recurring_match_rejections(series, entry)` unique 쌍, `recurring_price_changes(effective_on, previous_amount, new_amount, currency, source detected/user, entry_id)`에서 `(series, effective_on)`이 unique다.

**연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `POST /recurring_transactions/identify` | → flash, 목록으로 redirect | 파이프라인을 lock 아래 실행(`backfill: true`). lock 중이면 "이미 실행 중" 알림(R-25). |
| `POST /bills/detect` | → flash, `/bills`로 redirect | 위와 같다. 알림은 이번 실행으로 새로 생긴 `suggested` series(수입 제외, 사용자가 볼 수 있는 것) 수. |
| `POST /recurring_transactions/cleanup` | → flash(정리 개수) | stale `active` series를 `inactive`로(R-48). |
| `POST /recurring_transactions/:id/confirm`, `/dismiss`, `/toggle_status`, `DELETE /recurring_transactions/:id` | → redirect | R-01, R-63. |
| `GET/POST /recurring_transactions/new`, `create`, `GET edit`, `PATCH update` | 폼 값 → series | R-61, R-62. |
| `PATCH /recurring_transactions/update_settings` | `recurring_transactions_disabled` → 가족 설정 | `"true"` 문자열일 때만 true. 그 외는 false(R-26). |
| `POST /transactions/:id/mark_as_recurring` | → flash | R-27. |
| `POST /transfers/:id/mark_as_recurring` | → flash | R-28. |
| `GET /bills`(`view` = overview, all, calendar, paycheck), `GET /bills/:id`(`display` = drawer, history) | → 화면 데이터 | R-50~R-55, R-57~R-60. `view=subscriptions`는 `view=all&q[bill_type]=subscription`으로 redirect. |
| `POST /recurring_occurrences/:id/{mark_paid, skip, reopen}`, `PATCH .../{snooze, override_amount}` | → redirect `/bills` | R-42. |
| `POST /recurring_occurrences/:id/allocations`, `DELETE /recurring_allocations/:id`, `POST .../confirm`, `.../reject` | `entry_id`, `amount`, `paid_on` → allocation | R-42, R-44. |
| `GET /bills_feed/:token` | 서명 토큰 → `text/calendar` | R-65. |
| `POST /bills/reset_feed_token` | → feed 토큰 교체 | 이전 URL이 모두 무효가 된다(R-65). |
| 내부: `RecurringTransaction.identify_patterns_for(family)` | → 0 | sync 완료 후 호출 경계(R-23). |

### 1.4 행동 규칙과 남은 질문

**데이터·상태**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `status` 값과 전이 | 값은 5개. 쓰는 경로별로 전이는 다음과 같다. 감지가 새로 만든 series는 `suggested`(R-16). `confirm`(POST)은 현재 status를 확인하지 않고 `active`로 바꾼다. `dismiss`는 `ended`로 바꾼다. `toggle_status`는 `active`면 `inactive`로, 그 외 모든 값이면 `active`로 바꾼다. `cleanup`은 stale `active`를 `inactive`로 바꾼다(R-48). API는 `active`/`inactive`만 쓸 수 있고, 어시스턴트의 "paused"는 `inactive`로 저장된다. 웹·API·어시스턴트에서 `paused`를 쓰는 곳을 찾지 못했다(import는 쓴다). **종료 조건(`end_on`, `end_after_count`)에 도달해도 status는 자동으로 `ended`가 되지 않는다.** 일정 엔진만 더는 회차를 내지 않는다. 의미: `suggested`는 청구서가 아니라 검토 대기(회차를 만들지 않고 화면 목록에서도 빠진다), `inactive`는 일시 중지 또는 stale(회차를 새로 만들지 않는다), `ended`는 기각·삭제 표식으로 감지가 다시 만들지 않는다. 회차 생성은 `active`만 한다(R-33). `inactive`·`ended` series의 열린 회차는 남고 매칭에 계속 쓰인다(R-37). | 코드 확인(없다 주장은 2.1) |
| R-02 | 금액 부호·유형 | 지출 series는 `amount > 0`, 수입은 `amount < 0`이다(선언 폼·편집도 크기를 받아 수입이면 음수로 저장한다, R-61·R-62). 감지는 마지막 군집 거래의 부호를 따른다. `destination_account_id`가 있으면 `bill_type`은 저장 전에 `transfer`로 정해지고, `bill_type = transfer`인데 목적지 계정이 없으면 검증 오류다. 감지의 `bill_type`은 수입이면 `income`, 아니면 Classifier 결과(R-18)다. 거래·이체에서 표시한 series는 지출이면 `bill`, 수입이면 `income`, 이체면 `transfer`다. `occurrence`의 기대 금액·`allocation` 금액은 항상 양수(크기)다. | 코드 확인 |
| R-03 | series 저장 검증 | `amount`와 `currency` 필수. `expected_day_of_month`는 1~31. `occurrence_count`는 0 이상의 정수. `end_after_count`는 비어 있거나 1~600의 정수. `merchant_id`와 `name`이 모두 비면 오류. `category_id`·`account_id`·`destination_account_id`는 같은 가족 것이어야 한다. `expected_amount_min`이 `max`보다 크면 오류. 이체는 출금 계정 필수·두 계정 서로 달라야 함·같은 가족. `payment_url`은 비어 있거나 `http`/`https` URI이고 host가 있어야 한다. 저장 전 `payment_url`은 trim하고, 비면 null, 스킴이 없으면(`example.com:8080`처럼 포트 숫자가 `:` 뒤에 오는 경우 포함) `https://`를 붙인다. 스킴이 있으면 그대로 둬서 `javascript:`·`data:`가 검증에서 거부되게 한다. 일부 규칙이라도 `interval > 1`이면 `anchor_date` 필수. `end_mode`가 `on_date`면 `end_on`, `after_count`면 `end_after_count` 필수. | 코드 확인 |
| R-04 | 같은 정체성 중복 방지 | 일반 series의 DB unique는 `(family, account, merchant 또는 name, amount, currency, dedup_scope)`이고, 이체는 `(family, account, destination, merchant 또는 name, amount, currency, dedup_scope)`다. 가맹점이 있으면 name을 키에서 빼고(merchant 인덱스), 없으면 name 인덱스를 쓴다. 인덱스는 status와 무관하다. 그래서 `ended` series도 키를 점유한다. 한 정체성의 두 번째 금액 단계는 `dedup_scope`로 구분한다: 거래·선언에서 만들 때는 `금액.to_s("F")`(예 `"17000.0"`), 감지가 같은 정체성의 기존 series가 있을 때는 군집 평균을 소수 2자리로 반올림한 문자열, 없으면 `""`. **`account_id`가 null이면 인덱스가 중복을 막지 못한다**(NULL은 서로 다르다). 선언 청구서만 앱 코드로 막는다(R-61). | 코드 확인 |
| R-05 | 규칙 한 줄의 검증 | `frequency`는 3개 중 하나, `interval` ≥ 1, `day_of_month`는 -1~31이고 0 불가, `weekday` 0~6, `weekday_ordinal` -1~5이고 0 불가, `month_of_year` 1~12, `position` ≥ 0이고 series 안에서 unique. `weekly`는 `weekday` 필수이고 `weekday_ordinal`·`day_of_month`·`month_of_year`는 금지. `monthly`는 `month_of_year` 금지. `yearly`는 `month_of_year` 필수. `monthly`·`yearly`는 `day_of_month`와 `weekday` 중 정확히 하나가 있어야 하고, `weekday`가 있으면 `weekday_ordinal`도 필요하다(없으면 금지). | 코드 확인 |

**일정 엔진** (구체 계산은 C-04~C-06)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 규칙에서 날짜를 낸다 | 규칙이 0개면 "매월 `expected_day_of_month`일" 한 규칙으로 본다. `weekly`는 앵커(저장된 series는 `anchor_date`, 없으면 `last_occurrence_date`이고 이 컬럼은 NOT NULL이라 항상 있다. 구간 시작일로 대신하는 것은 `Schedule`을 직접 만들 때만) 기준 `weekday`를 첫 날로 잡고 `7 × interval`일 간격이며 앵커 이전·이후 모두 낸다. 규칙에 `weekday`가 없으면 앵커의 요일을 쓴다(둘 다 없으면 오류). `monthly`는 기준 월(앵커의 달)에서 `interval`개월마다 낸다. 날짜는 `day_of_month`를 그 달 길이로 줄인 값이고(31일 규칙은 2월 28/29일, 4월 30일), -1은 말일이다. `weekday + ordinal`이면 그 달의 n번째 요일이고, 5번째 요일이 없는 달은 건너뛴다(-1은 마지막 요일). `yearly`는 `interval`년마다 `month_of_year`월의 같은 규칙으로 낸다(2월 29일은 평년에 2월 28일). 규칙이 여럿이면 날짜를 합쳐 중복을 없애고 정렬한다. | 코드 확인 |
| R-07 | `weekend_adjust` | 규칙이 낸 날짜(`original_due_on`)가 토·일이면 `before`는 직전 금요일(토 -1, 일 -2), `after`는 다음 월요일(토 +2, 일 +1)로 `due_on`을 옮기고, `skip`은 그 회차를 없앤다. `none`은 그대로다. 공휴일은 보지 않는다. occurrence의 정체성은 보정 전 `original_due_on`이다. 보정된 `due_on`이 구간 밖으로 나가는 것을 막으려고 구간을 3일씩 넓혀 생성한다. | 코드 확인(공휴일 없다는 2.1) |
| R-08 | 종료 조건 | `on_date`: `due_on > end_on`인 회차는 없다(`end_on` 당일은 있다). `after_count`: 앵커(R-06의 앵커)부터 센 첫 `end_after_count`개 회차만 있다(보정 전 날짜가 앵커 이상인 것만 센다). 앵커가 없으면 오류다. 종료된 series는 `first_occurrence_after`가 nil을 돌려준다. series의 status는 바뀌지 않는다(R-01). | 코드 확인 |
| R-09 | 옛 단일 월 규칙(규칙 0개 또는 "월 1회, 날짜 지정(-1 아님), 보정·종료 없음")의 `next_occurrence_after(date)`와 `next_occurrence_from_today` | `next_occurrence_after(date)`는 `date`의 다음 달에서 `expected_day_of_month`일을 만들고, 그 달에 없으면 말일이다. `date`의 일자는 보지 않는다(1월 31일 다음 2월 28일/29일, 2월 29일 다음 3월 31일). `next_occurrence_from_today`는 이번 달의 기대일이 오늘보다 뒤면 그 날짜, 아니면 다음 달 기대일(없으면 말일)이다. **단 이번 달에 기대일이 없는 달(31일 기대일의 4월 등)은 말일로 줄이지 않고 건너뛰어 다음 달로 간다**(4월 10일 오늘, 기대일 31이면 5월 31일). 이 경로가 `next_expected_date` 캐시를 채운다. 그 밖의 모양은 규칙 엔진(R-10)으로 넘어간다. 엔진은 같은 31일 규칙에서 4월 30일을 낸다. 두 경로가 갈리므로 UI의 다음 청구일은 occurrence 기준(R-51)이다. | 코드 확인 |
| R-10 | 탐색 도우미 | `first_occurrence_after(date)`: `date` 다음 날부터 "가장 긴 주기 + 40일" 창으로 훑어 첫 회차를 돌려주고, 종료됐으면 nil, 최대 3,660일에서 포기하면 nil. `longest_period_days` = 규칙별(주 `7×interval`, 월 `31×interval`, 년 `366×interval`)의 최댓값 + 40. `cycle_for(date)`: `date` 이하의 마지막 회차(없으면 그 앞 창의 첫 회차)부터 다음 회차 직전까지의 반열린 구간. `occurrences_per_year`: 규칙별 합(주 `365.25/(7×interval)`, 월 `12/interval`, 년 `1/interval`). 이 값에서 "회차 간 일수 `365.25/연간횟수`"가 나온다. | 코드 확인 |
| R-11 | 주기 선택(FrequencyPreset) ↔ 규칙 | 프리셋은 `monthly, weekly, biweekly, semimonthly, quarterly, semiannual, annual`과 "N 주/월/년마다"(`interval`, N은 1~99, 단위는 `weekly/monthly/yearly`)다. 변환: monthly = 월 1규칙, weekly = 주 1규칙, biweekly = 주 `interval 2` + `anchor_date` 보충, semimonthly = 월 규칙 2개(position 0, 1)(두 날짜를 정렬하되 -1은 32로 취급하고 같으면 monthly), quarterly = 월 `interval 3`, semiannual = 월 `interval 6`, annual = 연 1규칙. 앵커가 없는 `interval>1` 계열은 `anchor_date ||= anchor ?? last_occurrence_date ?? 오늘`. 규칙에서 읽어올 때(`detect`)는 같은 모양이면 같은 프리셋이다(월 interval 3 = quarterly). 월·년의 n번째 요일 규칙과 규칙 3개 이상은 `custom`이고 건드리지 않는다. `apply`는 바꿨을 때만 true를 돌려주고, 같은 값이면 규칙을 다시 쓰지 않는다. 쓸 때 `expected_day_of_month`는 날짜 고정 계열이면 그 날(-1이면 31), 아니면 기준일의 일자다. 잘못된 interval·단위는 오류를 기록하고 아무것도 바꾸지 않는다. | 코드 확인 |
| R-12 | 거래 날짜가 회차에 속하는지(`matches_day?`) | 월·년 규칙은 규칙이 낸 날짜(원래 날짜 또는 보정된 날짜)와 거래일이 2일 이내(`DAY_MATCH_TOLERANCE`)이면 맞다. 주 규칙은 오차 0(그 요일 날짜 그대로)이다. 종료 조건 밖이거나 `skip`된 회차는 매칭되지 않는다. 일자 비교(SQL 쪽)는 31일 원형 달력이다: 거리 = `min(|d1-d2|, 31-|d1-d2|)`(30일과 1일은 2), 기대일은 그 달 말일로 줄여서 비교한다(31일 기대일은 2월 28일 거래에 맞는다). | 코드 확인 |

**자동 식별** (C-01~C-03)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | 식별 입력 거래 선택 | 가족의 `Transaction` entry 중 오늘 기준 3개월 전(`3.months.ago.to_date`) 이후, 계정 종류가 `Investment`·`Crypto`가 **아닌**(종류가 null이면 포함) 계정, `transactions.kind`가 이체 4종이 아닌 것. `excluded`, 보류(pending), 분할 원본 필터는 **없다**(분할 원본과 자식이 둘 다 들어간다). 그룹 키는 `(가맹점 id가 있으면 [:merchant, id] 아니면 [:name, entry.name 원문], currency, account_id)`이고 금액은 키가 아니다. 이름은 정규화하지 않은 원문 그대로 비교한다(R-19). | 코드 확인(없다 주장은 2.1) |
| R-14 | 그룹 안 금액 군집화 | 금액 오름차순(부호 있는 값)으로 훑으며, 항목이 현재 군집 **평균**에서 `|금액 − 평균| ≤ |평균| × 7.5%`이면 군집에 넣고 아니면 새 군집을 연다. 이웃이 아니라 평균과 비교한다. 수입(음수)도 같은 식이다. | 코드 확인 |
| R-15 | 군집을 패턴으로 채택 | 군집 크기 ≥ `min_occurrences`(자동 파이프라인 3, 후보 목록 2), 군집의 마지막 거래일 ≥ 오늘 − 45일, 군집 거래일의 "일(day)"이 모두 기대일에서 원형 거리 2 이내. 기대일은 일 목록이 1개면 그 값이고, 아니면 31일 원형에서 폭(span)이 최소가 되도록 회전한 뒤 중앙값(짝수면 두 중앙의 평균을 half-up 반올림)을 되돌린 값이다(C-03). 패턴 필드: `amount` = 마지막 거래 금액(부호 있음), `expected_amount_min/max/avg` = 군집 값(avg = 합/개수), `last_occurrence_date`, `occurrence_count` = 군집 크기. 일자(월 중 일) 기준이라 월 1회 패턴만 잡힌다(주·격주·반월·분기·연 단위는 군집이 일 일관성이나 3건 조건을 못 채운다). | 코드 확인 / 추론(월 단위만 잡힌다는 귀결) |
| R-16 | 패턴을 series에 연결 | 기존 series를 정체성 키 `([:merchant,id] 또는 [:name, matcher_name], currency, account_id, destination 없음)`로 모으고(모든 status·수동·`ended` 포함), 패턴과 같은 키의 후보 중 `|series.amount − 패턴 avg| ≤ |패턴 avg| × 7.5%`를 만족하는 것에서 차이가 가장 작은 것을 claim한다. claim된 series가 `manual`이거나 `ended`면 아무것도 하지 않는다(사용자가 선언·기각한 것을 감지가 되살리거나 덮어쓰지 않는다). 그 외는 R-17로 갱신한다. claim할 series가 없으면 `suggested` series를 만든다: `amount` = 패턴 amount, 변동 띠·기대일·last/next·count 채움, `status = suggested`, `manual = false`, `bill_type` = 수입이면 `income` 아니면 Classifier, 수입이면 카테고리 null·`autopay` false, 가맹점 키면 `name = null`, 이름 키면 `matcher_hints.detected_name = 이름`, `next_expected_date` = R-09의 `next_occurrence_after(last_occurrence_date)`(옛 단일 월 규칙), `dedup_scope`는 R-04. unique 충돌(경합)이면 다시 읽어 claim 처리한다. | 코드 확인 |
| R-17 | claim된 series 갱신 | `last_occurrence_date`, `occurrence_count`, `expected_amount_min/max/avg`, `next_expected_date`(= `schedule.next_occurrence_after(마지막 거래일)`)를 갱신한다. `schedule_pinned_at`이 없으면 `expected_day_of_month`를 패턴 기대일로 바꾸고, series가 "월 1규칙(interval 1, 날짜 고정, -1 아님)"뿐이면 그 규칙의 `day_of_month`도 같이 바꾼다(R-34로 미래 회차가 다시 만들어진다). **`amount`와 `status`는 건드리지 않는다**(가격은 R-46, 상태는 사용자). 카테고리가 비어 있고 수입이 아니면 Classifier가 군집에서 고른 카테고리를 채운다. 채울 때는 DB에서 `category_id IS NULL` 조건을 다시 걸어 사용자 저장을 덮지 않고, 카테고리가 가족 것인지도 확인한다. | 코드 확인 |
| R-18 | Classifier (감지 시 최초 1회) | 이름을 소문자로 바꿔 영문 키워드를 단어 경계로 찾는다(`utilit*`처럼 `*`는 접미 허용). 순서: 할부 키워드(`klarna affirm afterpay sezzle zip pay uplift`)면 `installment`. 청구 키워드나 ACH 표식이 있으면 `bill`. 구독 키워드가 있으면 `subscription`. 어느 이름 신호도 없으면, 군집 금액이 센트까지 모두 같고, 첫 금액 절댓값이 **150 이하**이고, 계정이 `CreditCard`일 때만 `subscription`. 그 밖은 `bill`. `autopay`는 `bill`이 아니면 true, `bill`이면 이름에 `autopay autopmt autodraft auto draft auto-draft autodebit auto debit auto-debit`가 있을 때만 true. 카테고리는 군집 거래 중 최빈 카테고리(동률은 먼저 센 것)다. 키워드 목록은 C-07. **150이라는 문턱은 통화를 보지 않는다.** 키워드는 모두 영문이다. 생성 뒤 다시 분류하지 않는다(rake `recurring:classify_existing`가 기본값 series를 일괄 재분류하는 운영 도구로 있다). 영문 키워드 매칭의 한글 경계 동작은 U-03이다. | 코드 확인 / 미확인(U-03) |
| R-19 | 이름 비교 | `normalize_name` = 소문자화, 연속 공백을 한 칸으로, 앞뒤 공백 제거. 유니코드 정규화(NFC·NFKC), 괄호·접미어 제거는 없다. series가 "아는 이름" = `name`, `matcher_name`(`matcher_hints.detected_name` 또는 `name`), `matcher_hints.name_aliases`(모두 정규화). 이름 키 series가 이름을 바꿔도 `detected_name`이 처음 이름을 보존한다(첫 변경 때 저장). 매칭은 이 정규화한 이름의 집합 포함으로, 식별 그룹 키는 정규화 없는 원문 일치로 비교한다. | 코드 확인 |
| R-20 | 후보 목록(선언 폼 선택용, 읽기 전용) | `candidate_patterns`: R-13~R-15와 같되 최소 2건. 지출/수입 부호를 맞추고 평균 절댓값이 1 미만이면 뺀다. 이미 같은 정체성(가맹점 또는 `[:name]`, currency, account, 이체 아님)의 series가 금액 7.5% 안에 있으면 뺀다. `income_source_candidates`: 수입은 금액 군집이 아니라 출처별로, 최근 90일, `amount < 0`, 이체 아님, `Investment`·`Crypto` 제외, 같은 `(가맹점 또는 이름, currency, account)`에 2건 이상이고 평균 절댓값 ≥ 1, 선언된(`bill_type = income`) series가 그 출처를 금액 무관하게 이미 갖고 있으면 뺀다. 총 입금액 큰 순. 폼은 접근 가능한 계정의 것만 8개까지 보여 준다. | 코드 확인 |
| R-21 | 수동(`manual`) series 변동 갱신 | 파이프라인의 식별 단계에서, `manual` · `active` · 이체 아님 series마다 최근 6개월 거래 중 통화가 같고, series에 계정이 있으면 그 계정이고, 거래 금액이 series `amount`의 `[amount/2, amount×2]`(부호 있는 값의 min/max 구간) 안이고, `schedule.matches_day?`(R-12)이고, 가맹점이 같거나(가맹점 키) `entry.name == matcher_name`(이름 키, 원문 일치)인 것을 모은다. 하나라도 있으면 `expected_amount_min/max/avg`(전체 평균), `occurrence_count`(개수), `last_occurrence_date`(최근 거래일), `next_expected_date`(`schedule.next_occurrence_after`)를 덮어쓰고 빈 카테고리를 최빈 값으로 채운다. 하나도 없으면 아무것도 안 한다. `kind`·`excluded` 필터는 없다. | 코드 확인 |

**실행 경계·시간대**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 파이프라인 `run!(backfill:)`와 lock | 순서: (1) 식별(R-13~R-17, R-21) (2) `active` series 전부의 occurrence 생성(R-33) (3) 매칭기의 orphan 복구(R-41) (4) 매칭 실행(R-37~R-40) (5) 가격 변동 감지(R-46) (6) `backfill`이면 6개월 이력 재구성(R-35). 반환은 (1)의 패턴 수(claim 갱신 포함)다. stale 정리(R-48)는 이 파이프라인에 없다. 가족별 Postgres advisory lock(`pg_try_advisory_lock`, 키 = MD5("recurring_transaction_identify:<family_id>")의 정수값 mod 2^31)을 잡지 못하면 블록은 실행되지 않고 false(사용자 실행은 nil)를 돌려주며, 잡았으면 끝날 때 반드시 같은 연결에서 푼다. | 코드 확인 |
| R-23 | sync 완료 후 호출 경계 | Family 완료 이벤트(sync-pipeline R-18)가 `identify_patterns_for(family)`를 부르고, 예외는 로그만 남기고 삼킨다. 가족의 정기 거래가 꺼져 있으면(R-26) 예약하지 않는다. 예약: cache `recurring_transaction_identify:<family_id>`에 현재 시각(초, 소수)을 40초(30+10) 동안 저장하고, job을 30초 뒤에 `(family_id, 그 시각)`으로 큐에 넣는다. 호출 자체는 즉시 0을 돌려준다. job 실행 시 (a) 가족이 없거나 꺼져 있으면 끝, (b) cache 값이 있고 자기 시각보다 크면 끝(더 새 예약이 있다), (c) 그 가족에 incomplete `Sync`가 있으면 끝(마지막 `Sync`의 완료 이벤트가 다시 예약한다), (d) lock을 잡고 `run!`을 backfill 없이 실행한다. lock을 못 잡으면 조용히 끝난다. cache가 만료돼 값이 없으면 (b)를 통과한다. job 실행 시 `Date.current`의 시간대는 U-01이다. 완료 이벤트는 Account·item `Sync`마다 실행되므로(sync-pipeline R-18), 한 번의 sync에서 예약이 여러 번 생기고 마지막 것만 실행되는 것이 정상이다. | 코드 확인 |
| R-24 | 야간 occurrence 생성 | cron `30 5 * * *`(UTC)에서 가족마다(정기 거래가 켜진 곳만) job을 따로 큐에 넣고, 각 job이 R-22와 같은 lock 아래 `active` series의 occurrence만 생성한다(식별·매칭·가격은 안 한다). sync가 없는 수동 가족의 창을 유지하려는 것이다. `sidekiq_options lock: :until_executed, on_conflict: :log`가 선언돼 있어 같은 job의 중복을 막으려는 의도로 읽히지만 실제 동작은 확정하지 못했다(U-02). | 코드 확인 |
| R-25 | 사용자 실행 | `identify`·`bills#detect`: `run_with_lock!(backfill: true)`. lock 중이면 nil → "이미 실행 중" 알림. `bills#detect`는 실행 전후의 접근 가능한 `suggested`(수입 제외) id를 비교해 새로 생긴 개수로 알린다(0이면 "없음"). `cleanup`은 R-48. `BillsController`는 `ensure_recurring_enabled`를 액션 제한 없이 걸므로(`detect`, `reset_feed_token` 포함) 기능이 꺼져 있거나 미리보기 설정이 꺼져 있으면 쓸 수 없다. `RecurringOccurrencesController`·`RecurringAllocationsController`도 같다. `RecurringTransactionsController`는 `new`·`create`·`edit`·`update`·`confirm`·`dismiss`에만 걸고, `identify`·`cleanup`·`index`·`toggle_status`·`destroy`·`update_settings`는 가족이 기능을 꺼도 호출할 수 있다. | 코드 확인 |
| R-26 | 기능 꺼짐·미리보기 게이트 | `families.recurring_transactions_disabled`(기본 false)가 true면: 예약·job 실행·야간 생성이 건너뛰어지고, `reconstruct_history!`는 true만 돌려주고 아무것도 안 하며, 청구서 계열 화면과 액션(`BillsController` 전체, 회차·정산 컨트롤러, 선언·편집·확인·기각)은 홈으로 redirect하고(가드는 `require_preview_features!`를 먼저 부르므로 미리보기 설정이 꺼져 있어도 같다), iCal feed는 404, 이체의 "정기 거래로 표시"는 거부, 규칙은 유지(데이터 삭제 없음). 청구서 화면은 추가로 사용자의 미리보기 기능 설정이 켜져 있어야 한다(꺼져 있으면 홈으로 redirect + 안내). `PATCH update_settings`는 `recurring_transactions_disabled == "true"`일 때만 true로 저장한다. | 코드 확인 |
| R-27 | 거래에서 "정기 거래로 표시"(`mark_as_recurring`) | 계정 권한 확인(`require_account_permission!`) 뒤, DB transaction 안에서 거래별 advisory lock(R-44)을 잡고 `covering`(R-29)이 있으면 "이미 포함됨", 없고 `identity_taken_by`가 있으면 "이미 존재" 알림으로 끝낸다. 아니면 `create_from_transaction`을 만든다. `RecordInvalid` → 생성 실패, `RecordNotUnique` → 이미 존재, 그 밖 예외 → 예기치 못한 오류 알림(모두 목록으로 redirect). 생성 내용: `expected_day = 거래일의 일`, `amount = 거래 금액`(부호 유지), `name = 가맹점이 있으면 null 아니면 entry.name`, `manual = true`, `status = active`, `bill_type = 수입이면 income 아니면 bill`, 카테고리는 지출일 때만 거래 것, `last_occurrence_date = 거래일`, `next_expected_date`는 R-09의 `next_occurrence_from_today`, `dedup_scope = 금액.to_s("F")`, `matcher_hints.detected_name = 가맹점이 없으면 entry.name`. 변동 띠와 `occurrence_count`는 과거 6개월의 같은 계정·통화·(가맹점 또는 이름 원문)·기대일 ±2(원형)·금액 `[a/2, a×2]` 거래들의 min/max/avg/개수이고, 1건이면 셋이 같고 0건이면 null이다. 저장 직후 occurrence가 생성된다(R-33). `anchor_date`를 채우지 않으므로 `manual`이어도 R-33의 앵커 하한이 적용되지 않아 이전 주기 시작부터 occurrence가 생길 수 있다(`occurrence_generator.rb:24,29`를 읽은 귀결이고 실행하지 않았다: 추론). | 코드 확인 |
| R-28 | 이체에서 "정기 거래로 표시"(`create_from_transfer`) | 기능이 꺼져 있으면 거부, 출금·입금 계정이 없으면 오류 알림, 두 계정 모두 쓰기 권한 필요. 같은 `(source, destination, 출금 금액, 통화)` series가 이미 있으면 거부. 만들 때: 출금 entry·입금 entry 둘 다 필요(없으면 `ArgumentError`), `name = Transfer 이름`(목적지가 부채 계정이면 "Payment to <계정>", 아니면 "Transfer to <계정>"), `amount = 출금 금액`(양수), 통화·기대일 = 출금 entry의 것, `last_occurrence_date = 출금일`, `next_expected_date`는 R-09의 from_today, `status = active`, `bill_type = transfer`, `occurrence_count = 1`, `manual = true`. `dedup_scope`는 채우지 않는다(`""`). 이체 series는 가맹점·변동 띠가 없다. | 코드 확인 |
| R-29 | 이미 정기 거래인가(`covering`, `identity_taken_by`) | `covering(entry)`는 호출자가 `accessible_by(Current.user)`로 좁힌 series에서만 찾으므로 사용자가 접근할 수 없는 series는 중복 판정에서 빠진다(`transactions_controller.rb:590-592`, `recurring_transactions_controller.rb:293-297`). 대상은 `ended`가 아닌 같은 가족 series이고: (1) 이 entry에 `confirmed` allocation이 있는 series가 있으면 그것. (2) entry가 이체 다리면 없음. (3) 통화가 같고, 계정이 entry 계정이거나 null이고, 이체 series가 아니고, 이 entry에 대해 사용자가 거부한 series가 아니고(R-42), `amount_within_variance_band?(entry.amount, series.amount)`이고(부호 있는 `[a/2, a×2]`, 기준이 0이면 정확히 같을 때), 가맹점 series면 entry의 가맹점이 같고 아니면 `known_names`와 `[entry.name, 가맹점 이름]`(정규화)이 교집합인 것 중 `created_at`이 가장 이른 것. `identity_taken_by(transaction)`은 status와 무관하게 정확한 unique 키 `(family, account, destination null, amount, currency, dedup_scope = 금액 문자열, 가맹점 또는 name)`가 같은 행을 찾는다. | 코드 확인 |
| R-30 | "오늘"의 기준 시간대 | 웹 요청은 Family의 `timezone`(없거나 모르는 값이면 앱 기본)으로 `Date.current`를 쓴다. `Sync#perform` 전체는 `Time.use_zone(family 시간대)` 안에서 실행된다(`sync.rb:183-185`, sync-pipeline R-09). 야간 cron job(R-24)과 rake는 앱 기본 시간대를 쓴다. `config.time_zone`은 설정하지 않아 UTC이고 job 코드에 `use_zone`이 없다. sync 후 식별 job(R-23)은 `Sync#perform`의 같은 블록에서 큐에 들어가지만, 그 job이 worker에서 어느 시간대로 도는지는 확정하지 못했다(U-01). 야간 job이 UTC라면 한국(UTC+9) 가족은 한국 시각 00:00~09:00에 하루 전 날짜를 "오늘"로 본다. | 코드 확인(야간 job, 웹) / 미확인(sync 후 job, U-01) |

**occurrence와 이력**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | occurrence의 상태와 파생 상태 | 저장 status는 `scheduled`, `paid`, `skipped`, `missed`뿐이다. `effective_due_on = max(due_on, snoozed_until)`. 열린(`scheduled`) occurrence의 파생 상태는 `오늘 > effective_due_on + 유예일`이면 `overdue`, `오늘 ≥ effective_due_on − 알림일`이면 `due`, 아니면 `upcoming`이다(유예일 = `overdue_grace_days` 또는 3, 알림일 = `notify_days_before` 또는 3). 닫힌 것은 저장 status 그대로다. 화면용 `overdue?`·`due?`는 series가 `active`일 때만 참이다(`derived_state`는 series 상태와 무관해서 매칭이 쓴다). `missed`는 `miss!`(사용자 동작 의도)로만 만들 수 있으나 호출하는 곳을 찾지 못했다(2.1). 따라서 `missed` occurrence는 정상 경로로 생기지 않는다. | 코드 확인(없다 주장은 2.1) |
| R-32 | 예상 금액 해석·remaining | `resolved_expected_amount`: occurrence에 `expected_amount`가 있으면 그 값. 없으면 `amount_strategy`로 series에서 해석하고 절댓값을 쓴다: `fixed` = series `amount`, `average` = `expected_amount_avg`(없으면 `amount`), `last` = 직전 `paid` occurrence(`due_on`이 더 이른 것 중 최신)의 `confirmed` 합(양수일 때, 아니면 `amount`). 닫으면(`close!`) 그 시점에 해석한 금액을 `expected_amount`로 고정한다. 다시 열어도 고정값이 남는다. 확정 금액이 처음 연결될 때도 고정한다(R-43). `remaining_amount = max(해석 금액 − confirmed 합, 0)`. `partially_paid? = 열림 ∧ confirmed 합 > 0 ∧ 합 < 해석 금액`(오차 허용 없음). `overpaid? = confirmed 합 > 해석 금액 + 0.01`. | 코드 확인 |
| R-33 | occurrence 생성(`generate!`) | `active`가 아니면 0건. 시작 = `schedule.cycle_for(오늘)`의 시작(없으면 오늘), `manual` series는 `max(시작, anchor_date)`(앵커 전 달에 가짜 연체를 만들지 않는다). 끝 = `max(오늘 + 90일, 오늘 이후 첫 회차)`이고, 횟수 종료(`after_count`)면 `max(위, anchor_or_오늘 + ceil(365.25/연간횟수) × (횟수+1))`로 전체 계획을 한 번에 만든다. 구간의 (원래 날짜, 보정 날짜) 쌍을 `(series, original_due_on)` unique로 insert하고 충돌은 무시한다(재실행이 안전하고 기존 행을 건드리지 않는다). 단, 이미 있는 행이 현재 일정이 더 이상 내지 않는 날짜(규칙 수정 전 것)이고 현재 일정의 가장 가까운 회차(반 주기 이내)를 "대신 서 있으면" 그 회차는 새로 만들지 않는다. 반 주기 = `max((floor(365.25/연간횟수) − 1) / 2 (정수 나눗셈), 1)`. `after_commit on create`와 일정 변경 때 실행된다. 반환은 새로 만든 행 수. | 코드 확인 |
| R-34 | 일정 변경 시 재생성 | `expected_day_of_month`, `anchor_date`, `end_mode`, `end_on`, `end_after_count`, `weekend_adjust`, `status`, `currency` 중 하나가 바뀌거나 FrequencyPreset이 규칙을 다시 썼으면(금액·이름은 아님), 저장 후에 `due_on ≥ 오늘`이고 열려 있고 **allocation이 하나도 없는**(suggested 포함) occurrence를 지우고 `generate!`를 다시 한다. 닫힌 행과 지난 행, allocation이 있는 행은 남는다. 그래서 `inactive`·`ended`로 바꾸면 미래 열린 회차는 지워지고(`generate!`가 0건), `active`로 되돌리면 다시 생긴다. | 코드 확인 |
| R-35 | 이력 재구성 | `suggested → active` 전환 직후(웹 confirm, API, 어시스턴트 어느 경로든) `reconstruct_history!`: 기능이 켜져 있어야 하고, R-22의 lock 안에서 (1) 그 series의 occurrence 생성 (2) HistoryBackfiller(6개월): `active` series마다 6개월 전부터 오늘까지의 occurrence를 만들고(`backfill!`), **가족 전체**에 대해 매칭기를 백필 모드로 돌리고(확정 가능한 `exact` 등급만 쓰고 제안은 쓰지 않는다, R-40), 현재 주기 시작 전의 열린·allocation 없는 occurrence를 삭제한다(과거 빚을 만들지 않는다). lock 중이면 false → `BackfillRecurringHistoryJob`이 series가 `active`인 동안 재시도한다(점점 늘어나는 간격, 최대 10회). 전환 후 실패 예외는 보고하고 같은 job으로 넘기며 사용자의 저장은 실패시키지 않는다. 사용자 실행(R-25)도 6개월 백필을 한다. rake `recurring:backfill_history[months]`가 같은 일을 수동으로 한다. | 코드 확인 |
| R-36 | series 금액 변경 | 금액이 바뀌면(저장 후) `expected_amount`가 없고 `due_on ≤ 오늘`인 열린 occurrence에 변경 전 금액을 고정한다(미래 회차는 새 금액을 따라간다). 이미 allocation이 있는 행은 정산이 고정했다. | 코드 확인 |

**매칭·정산**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-37 | 매칭 후보 수집 | 열린 occurrence 전체(가족 내, **series status와 무관**)와 entry를 비교한다. entry는 `Transaction`, `excluded = false`, 모든 occurrence 창을 합친 날짜 범위(열린 매칭은 상한 오늘, 백필은 상한 없음), 이체 종류가 아니거나(`kind`가 4종) 이체 series의 출금 다리인 것, `confirmed` allocation이 이미 있는 entry 제외. 쌍이 후보가 되려면: 사용자가 거부한 `(series, entry)`가 아니고, **정체성 일치**(통화 같음, series 계정이 있으면 같음, 부호 같음 = 지출 series는 `entry.amount > 0`이어야 하므로 금액 0은 안 맞음, 이체 series면 entry가 그 출금 다리이며 입금이 `destination_account`로 가는 것, 이체가 아니면 이체 다리가 아니어야 하고 가맹점이 같거나 정규화 이름이 `known_names`에 있음), 창 안, 점수 ≥ 0.60. 한 entry는 한 series 안에서 `|entry.date − effective_due_on|`이 가장 작은 occurrence 하나로만 후보가 된다. | 코드 확인 |
| R-38 | 매칭 창 | `주기일수 = floor(365.25/연간횟수)`, `반주기 = max((주기일수−1)/2, 1)`(정수 나눗셈)일 때 창 = `[effective_due_on − min(match_days_early, 반주기), effective_due_on + min(match_days_late, 반주기)]`. 기본은 2일 전, 7일 후이고 월 단위면 반주기 14라서 그대로다. 파생 상태가 `overdue`인 occurrence는 창 끝을 오늘까지로 늘린다(늦은 납부 허용). | 코드 확인 |
| R-39 | 점수(0~1, 소수 4자리 반올림) | 합 = 정체성 신호 + 금액 + 날짜 + 계정. 정체성: 이체 series 0.40, 가맹점 series 0.40, 이름 series 0.35. 금액(`기대 = resolved_expected_amount`, `실제 = |entry.amount|`): 차이 < 0.01이면 0.30. 아니면 `허용 = max(series.amount_tolerance_pct, matcher_hints.learned_tolerance_pct)`, `띠 = 기대 × 허용/100`, 차이가 띠보다 크거나 띠가 0이면 후보 탈락(점수 0), 아니면 `0.25 − (차이/띠) × 0.10`(0.25~0.15). 날짜: `span = max(창 길이 일수, 1)`, `0.20 − (min(|entry.date − effective_due_on|, span)/span) × 0.15`(0.20~0.05). 계정: entry 계정이 series 계정과 같거나 series 계정이 null이면 0.10. 신호는 allocation의 `match_signals`에 저장한다. | 코드 확인 |
| R-40 | 등급·모호성·적용 | 후보를 (신뢰도 내림차순, occurrence id, entry id)로 정렬해 하나씩 처리하고, entry와 occurrence는 한 실행에서 한 번만 배정한다. 등급: 신뢰도 ≥ 0.85이고 entry가 보류(pending)가 아니고 모호하지 않으면 `exact` → `confirmed`로 쓴다. 모호함 = 같은 entry에 대한 **다른** occurrence 후보(다른 series) 중 신뢰도 차이가 0.15 미만인 것이 있음. 그 밖에 ≥ 0.60이면 `high` → `suggested`로 쓴다(**수입 series는 high 없음**: 수입은 exact가 아니면 아무것도 쓰지 않는다). 백필 모드는 `high`를 쓰지 않는다. 쓰기 중 unique 충돌이나 entry 초과 배정은 그 후보만 건너뛰지만, 건너뛴 후보의 entry와 occurrence도 이미 이번 실행에서 배정된 것으로 기록돼 차순위 후보가 같은 실행에서 그 entry·occurrence를 쓰지 못한다(`matcher.rb:131-133`). | 코드 확인 |
| R-41 | orphan allocation 복구(`repair_orphans!`) | `entry_id`가 null이고 `source`가 `auto_matched`·`user_confirmed`인 allocation마다(provider가 보류 거래를 새 행으로 바꿔 FK가 null이 된 경우), 같은 통화·`paid_on`·금액(`source_amount`·`allocated_amount` 각각의 ±부호)이 같고, 다른 allocation을 하나라도(`suggested` 포함) 가진 entry를 뺀 entry 중 series 계정(있으면)과 맞고, 느슨한 정체성(이체 series는 도착 계정, 가맹점이 양쪽에 있으면 가맹점 일치, 아니면 정규화 이름이 아는 이름과 같거나 한쪽이 다른 쪽의 접두어)인 것을 찾아 연결한다. | 코드 확인 |
| R-42 | 사용자 정산 연산 | 모두 series가 쓰기 가능(계정이 null이거나 `writable_by`)해야 한다(아니면 404). `allocate`(수동 연결·금액 입력): `confirmed`, `source`는 거래가 있으면 `user_confirmed`, 없으면 `user_created`, 금액은 R-44. `unallocate`: 삭제 후 닫힘 재계산(R-43). `confirm`: `suggested → confirmed`, `source = user_confirmed`, 기대 금액 고정, 닫힘 재계산. `reject`: `(series, entry)` 거부 행을 만들고(영구, 매칭기와 `covering`이 이후 무시) allocation 삭제(닫힘 상태는 안 바꾼다). `mark_paid`: 남은 금액만큼 거래 없는 `confirmed` allocation(`user_created`)을 만들고 occurrence를 `paid`(`closed_source = user`)로 닫는다. `skip`(→ `skipped`), `reopen`(어느 상태에서든 → `scheduled`, 고정 금액은 남음), `snooze(until)`(`snoozed_until` 설정, 날짜 파싱 실패는 오류 알림), `override_amount`(`expected_amount` 설정, 빈 값이면 해제, 음수는 모델 검증 실패인데 컨트롤러가 rescue하지 않아 처리되지 않은 `RecordInvalid`가 된다) 모두 상태 제한이 없다. | 코드 확인 |
| R-43 | 회차 닫힘 규칙 | 닫힘 재계산(`refresh_close_state`)은 `confirmed` allocation으로만 판단한다. `닫힘 자격 = 기대 금액 > 0 ∧ confirmed가 1건 이상 ∧ (confirmed가 정확히 1건이고 |그 금액 − 기대| ≤ 기대 × series.amount_tolerance_pct/100, 또는 합 ≥ 기대 − 0.01)`. 열린 occurrence가 자격이 있으면 `paid`(`closed_source = auto`)로 닫는다. `paid`이고 `closed_source = auto`인데 자격이 없어졌으면 다시 연다. 사용자가 닫은 것(`user`)은 자동으로 다시 열리지 않는다. `suggested` allocation은 닫힘에 영향이 없다. 확정 연결 시 기대 금액이 없으면 그 시점 해석 금액으로 고정한다. | 코드 확인 |
| R-44 | allocation 금액·거래 용량 | 한 거래가 여러 occurrence에 나뉘어 연결될 수 있되 합이 거래 금액을 넘지 못한다. 용량 = `|entry.amount| − Σ COALESCE(source_amount, allocated_amount)`(`ended` series의 allocation은 세지 않고, `suggested`도 센다), 하한 0. 같은 통화: 금액이 없으면 `occurrence.remaining`이 양수일 때 `min(용량, remaining)`, 아니면 용량. 금액을 주면 그 값. 다른 통화: 그 거래일의 환율(`find_or_fetch_rate`)로 환산하고, 금액 없이 환율도 없으면 `MissingRateError`. 환율 없이 금액을 주면 `source_amount`가 null이고 그 거래는 allocation을 하나만 받을 수 있다. 거부 규칙: 용량이 0이면 같은 occurrence가 이미 갖고 있을 때 "이미 연결됨", 아니면 "소진됨"이고, `source_amount > 용량 + 0.01`이면 초과 배정 오류다. 모든 쓰기는 occurrence 행 잠금 → 거래별 advisory lock(`pg_advisory_xact_lock(8311, MD5(entry.id) mod 2^31)`) 순서다. 오류는 `OverAllocationError`(하위: 소진, 이미 연결), `MissingRateError`다. 어시스턴트용 `cap_at_remaining`은 잔액 초과를 거부한다(웹 경로는 쓰지 않아 초과 금액이 가격 상승을 기록하는 방법이다). | 코드 확인 |
| R-45 | 수동 연결이 가르치는 것 | `allocate`가 거래를 연결할 때만(자동 매칭은 안 함) series의 `matcher_hints`를 고친다. 이름 키 series인데 그 거래 이름(정규화)이 아는 이름에 없으면 `name_aliases`에 원문을 추가한다. 연결이 occurrence를 단독으로 닫는 확정 1건이고 `|거래 − 기대|/기대 × 100`(편차)이 series 허용치와 기존 `learned_tolerance_pct`를 모두 넘고 25 이하면 `learned_tolerance_pct`를 편차(소수 1자리)로 올린다. 부분 납부는 학습하지 않는다. | 코드 확인 |

**가격 변동·상태 정리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-46 | 가격 변동 감지(`detect!`) | `active`이고 `amount > 0`인 series마다: `paid` occurrence를 `due_on` 내림차순 2건 읽고(2건 미만이면 종료), 각각 `confirmed` allocation이 **정확히 1건**이어야 한다(아니면 종료). 두 `allocated_amount`의 차이가 0.01 이하이고, 그 값(`new_amount`)이 `|series.amount|`와 0.01을 넘게 다르고, 같은 `effective_on`(= 최신 paid 회차의 `due_on`)의 변동이 없고, 마지막 기록 변동의 `new_amount`와 같지 않을 때 `RecurringPriceChange`(source `detected`, `previous_amount = |series.amount|`, entry = 최신 settlement의 entry)를 만든다. `manual`이 아닌 series는 `amount`를 `new_amount`로 바꾼다(`manual`은 기록만, 금액은 사용자가 바꾼다). unique 충돌은 무시한다. 자동·기본 금액으로 연결하면 `allocated_amount`가 회차 잔액으로 잘려서(R-44) 더 비싼 요금도 기대 금액으로 기록된다. 그래서 가격 **인상**은 사용자가 거래 없이 금액을 직접 기록했을 때(수동 결제 `user_created`, 이때 변경 기록의 `entry`는 null)나 `override_amount`로 기대 금액을 올렸을 때, 또는 거래+금액을 함께 보내는 직접 POST로만 감지된다. 웹 화면에는 거래 연결과 금액 입력을 동시에 하는 경로가 없다(후보 연결은 `entry_id`만, 수동 결제 폼은 `amount`와 `paid_on`만 보낸다). `override_amount` 액션을 부르는 뷰는 찾지 못했다(2.1). **인하**는 폭이 `amount_tolerance_pct` 안일 때만 감지된다. 폭이 허용치를 넘으면 매칭이 후보에서 빼고(R-39), 수동 기본 연결의 단일 금액도 허용 밖이고 합도 기대 금액에 못 미쳐 `paid`가 되지 않으며(R-43), 감지기는 `paid` 2건만 본다. 실패 처리: 변경 기록 생성과 `series.update!(amount:)`는 하나의 transaction이 아니다. `update!`가 `RecordNotUnique`면 기록은 남고 금액은 그대로이며 같은 `effective_on`은 재시도되지 않는다. `RecordInvalid`는 rescue되지 않아 `detect!`와 파이프라인 전체(R-22, 단계마다 rescue 없음)가 중단된다. 매칭은 허용 오차 밖 금액을 후보에서 뺀다(R-39). | 코드 확인 / 추론(잘림의 귀결, 뷰 경로는 읽어서 확정) |
| R-47 | 중요한 변동 | 변동의 `shift = (new − previous)/previous`(previous가 0 이하면 0), `material? = |shift| ≥ 0.10`. 청구서 화면의 알림은 `material?`이면 긴급으로 분류한다(R-54). `source = user` 값은 enum에 있으나 만드는 곳을 찾지 못했다(2.1). | 코드 확인 |
| R-48 | stale 판정과 정리 | `staleness_threshold_date = min(달력 하한, 오늘 − ceil(2 × 365.25/연간횟수)일)`이고, 달력 하한은 자동 series 2개월 전·`manual` 6개월 전이다(둘 중 더 이른 날짜). `should_be_inactive?` = `last_occurrence_date < threshold`. `cleanup`(웹 버튼 `POST /recurring_transactions/cleanup`)은 `active` series마다 이 판정이 true이고, `matching_transactions`(R-10의 일정으로 거른 일치 거래) 중 `date ≥ threshold`가 없으면 `inactive`로 바꾸고 개수를 알린다. 이체 series는 출금·입금 쌍이 일치하는 출금 entry로 판단한다. **자동으로 이 정리를 실행하는 코드는 찾지 못했다**(파이프라인·cron에 없다). 재활성 자동화도 없어서 `inactive`는 사용자가 되돌릴 때까지 간다. | 코드 확인(없다 주장은 2.1) |
| R-49 | 호출처를 찾지 못한 것 | (a) `remove_old_inactive_transactions`(감지된 `inactive` 6개월 초과 삭제), `record_occurrence!`·`update_amount_variance`(수동 series 갱신), 모델 scope `bills`·`payable`·`expected_soon`·`needs_action`, `projected_entry`, `miss!`는 app·lib에서 호출처가 없다(`record_occurrence!`은 테스트에서만 호출). (b) `holiday_calendar`, `upcoming_window_days`, `replaced_by_id`는 import·export 말고 읽는 곳이 없다. (c) `weekend_adjust`, `amount_strategy`, `amount_tolerance_pct`, `match_days_early/late`, `notify_days_before`, `overdue_grace_days`를 **쓰는** 웹·API·어시스턴트 경로가 없다(import·export·모델·어시스턴트의 읽기 도구뿐). 따라서 실제 값은 기본값(`none`, `fixed`, 7.5, 2, 7, 3, 3)이거나 import 값이다. 엔진은 값이 있으면 R-06~R-12·R-31·R-38~R-43대로 동작한다. | 코드 확인(검색 범위 한정, 2.1) |

**청구서 화면·급여 계획**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-50 | "내야 할 청구서" 대상 | 화면의 대상 series = 가족 안, status `active` 또는 `inactive`, `amount > 0`(수입 제외), (이체가 아니거나 목적지가 `CreditCard`·`Loan` 계정인 이체), 사용자가 접근 가능(R-64). 즉 신용카드·대출 상환 이체는 청구서이고 일반 이체·수입은 아니다. `suggested`와 `ended`는 목록에서 빠진다. `inactive` series의 남은 열린 회차는 "휴면(dormant)"으로 표시되고 연체로 세지 않는다. 금액 하한은 없다. | 코드 확인 |
| R-51 | overview 산정 | occurrence 범위: 대상 series의 occurrence 중 `due_on ≤ 오늘+90`이고 (`effective_due_on ≥ 이번 달 1일` 또는 열림). 열림/닫힘으로 나누고 열림은 `active`와 휴면으로 나눈다. `active` 열림은 파생 상태가 `overdue`인 것(연체), `effective_due_on ≤ 이번 달 말`인 것(이번 달), 그 이후(다음 이후)로 나눈다. 이후는 series당 `effective_due_on`이 가장 이른 1건만 보인다. 이번 달 목록은 이번 달에 닫힌 `paid`(`effective_due_on`이 이번 달)도 날짜순으로 섞어 보인다. "다음 예정"은 이번 달·이후 중 `effective_due_on ≥ 오늘`을 날짜순 4건이다. KPI: 이번 달 남은 금액 = 연체+이번 달의 `remaining_amount` 합, 이번 달 납부 합 = `paid` 건의 confirmed 합, 7일 내 = 오늘~오늘+6의 열린 건 remaining 합(연체 제외), 연체 합, 건수, 해야 할 일 수 = 연체+이번 달 중 `autopay = false`. 모든 합은 Family 통화로 환산하고 환산 실패 건은 합에서 빼고 개수만 센다(money R-42). 가족에 occurrence가 하나도 없고 cache `bills:materialized:<family_id>`가 없으면 활성 series 전부를 한 번 생성하고 cache를 12시간 둔다. | 코드 확인 |
| R-52 | all 목록·구독 롤업 | 접근 가능한 series 전체(status 무관, 단 기본은 `ended` 제외). 검색은 `name` 또는 가맹점 이름 `ILIKE`. 상태 필터: 결제 상태(`overdue`, `due`, `partial`, `paid`: series의 "현재 occurrence"의 파생 상태로 거른다)와 수명주기(`paused` = `inactive`+`paused`, `ended`). 현재 occurrence = 열린 것 중 `due_on`이 가장 이른 것, 없으면 가장 최근 닫힌 것. `bill_type` 필터. 정렬: 이름, 금액 내림차순, 기본(status, `next_expected_date`). 구독 롤업(`bill_type = subscription`일 때): `active` 구독의 `monthly_equivalent_amount`(R-55)를 Family 통화로 합해 월·연(×12)·개수, 환산 불가 개수, 최근 1년 내 가격 변동 10건. | 코드 확인 |
| R-53 | calendar | 월 파라미터(`YYYY-MM`, 잘못되면 이번 달), 오늘 + 13개월의 달 초로 제한. 격자는 그 달 1일이 속한 주의 일요일부터 말일이 속한 주의 토요일까지. 격자 끝이 오늘+89일을 넘으면 그 범위까지 occurrence를 먼저 생성한다. 대상 = R-50의 series의 occurrence 중 `due_on`(snooze 아님)이 격자 안인 것을 `due_on`별로 묶는다. 월 합계: 그 달 건수, 기대 금액 합, 납부 합(환산 실패 제외·카운트). | 코드 확인 |
| R-54 | 알림·검토 필요 건수 | 알림은 R-50의 `active` series만: `trial_ends_on`이 오늘~+14일(체험 종료), `renews_on`이 오늘~+14일(갱신), 최근 30일 안 `effective_on`의 가격 변동. 정렬: 긴급(체험은 종료일 ≤ 오늘+3, 가격은 `material?`) 먼저, 그다음 오늘과 날짜의 거리. `detected_awaiting_review`(감지만 있고 사용자가 아직 청구서를 만진 적 없음 안내) = 접근 가능한 `manual` series가 있거나, `ended`가 있거나, `auto_matched`가 아닌 allocation이 있으면 0, 아니면 R-50 대상 중 `manual = false`·`active` 개수. 감지 제안 검토 줄은 수입이 아닌 `suggested`다(수입 제안은 설정 화면에서 검토). | 코드 확인 |
| R-55 | 파생 지표 | `monthly_equivalent_amount = amount × occurrences_per_year/12`(예: 매주 10,000 → 43,482.14, 매년 120,000 → 10,000). `cycles_overdue`: 연체가 아니면 0, 아니면 `floor((오늘 − next_due_date)일 / (365.25/연간횟수))`(하루 늦음은 0). `next_due_date`: 열린 occurrence 중 가장 이른 것의 `effective_due_on`, 없으면 `next_expected_date`가 오늘 이전이면 그 값, 아니면 `next_expected_date`와 `next_occurrence_from_today` 중 이른 값. `installment_progress`: `bill_type = installment`이고 `end_after_count`가 있으면 `(paid 회차 수, end_after_count)`. `duplicate_key = (표시 이름 소문자·공백 정리, amount, expected_day_of_month)`. 상세 `display=history`는 닫힌 occurrence 최근 12건(`due_on` 내림차순), 앞으로 400일 안의 예정 3건, 분석(`paid` 회차별 confirmed 합의 평균·최소·최대, 연환산 = `monthly_equivalent × 12`, 올해 납부합 = `paid_on ≥ 올해 1월 1일`인 confirmed 합), 최근 12개월 월별 납부 합, 연도별 합계·평균(최근 4년)을 준다. | 코드 확인 |
| R-56 | 거래 목록의 예정 거래 소비 | 거래 목록은 접근 가능한 `active` series 중 `next_expected_date`가 `[오늘, 오늘+10일]`인 것을 "예정"으로 보여 준다. 저장 cache에는 id만 1일 두고(키: 가족·사용자·오늘·정기 거래 버전 등) 읽을 때 다시 조회한다. 이 판정은 occurrence가 아니라 캐시된 `next_expected_date`다(R-09의 단일 월 규칙 경로가 채운 값). | 코드 확인 |
| R-57 | 급여 계획: 입력과 기간 | 급여 occurrence = 가족의 열린 occurrence 중 series가 `active`·`bill_type = income`·`manual = true`·접근 가능이고 `due_on ≥ 오늘`(snooze는 안 본다), `due_on` 순. 없으면 계획 없음(nil, 화면은 선언을 유도). `periods_limit`(기본 3, overview의 달 구분은 6)이면 급여 날짜(중복 제거) 앞 `limit+1`개를 모으고 경계 = `[오늘] + 날짜`(중복 제거, 최대 `limit+2`개). 기간은 경계의 연속 두 개마다 `[시작, 다음 시작 − 1일]`이고, 마지막 경계는 마지막 기간의 끝을 닫을 뿐 그 급여는 어느 기간의 수입도 아니다. 경계가 하나뿐(급여가 모두 오늘)이면 기간이 없어 빈 계획(빈 목록)이다. 수입 = 기간 시작일 `due_on`인 급여들의 `resolved_expected_amount`를 Family 통화로 환산해 합한 값(환산 실패는 0과 개수 +1). 첫 기간은 `leading`(오늘~첫 급여 전날, 오늘이 급여일이면 그 급여를 포함하므로 수입 > 0), 마지막은 `final`. | 코드 확인 |
| R-58 | 급여 계획: 청구서 배분(`apportion_bills`) | 배분 대상 = 열린 occurrence 중 series가 `active`, `amount > 0`, (이체가 아니거나 목적지가 가족의 `CreditCard`·`Loan`), 접근 가능, `effective_due_on ≤ 마지막 기간 끝`. `(effective_due_on, id)` 순으로 하나씩: `remaining = Family 통화로 환산한 remaining_amount`(양수만, 환산 실패는 0이라 건너뜀·개수 +1). `due = max(effective_due_on, 첫 기간 시작)`(연체는 첫 기간으로). 그 날짜가 속한 기간이 home. `available[i]`는 기간 i의 수입에서 이미 배분한 몫을 뺀 잔액으로 처음엔 수입이다. `funded = min(remaining, max(available[home], 0))`, `uncovered = remaining − funded`. 부족분은 home 앞쪽의 **수입이 있는** 기간(가까운 쪽부터)이 맡는다: 각 기간에서 `take = (맨 앞에 있는 마지막 후보면 uncovered 전부, 아니면 min(uncovered, max(available, 0)))`을 `due_in_period = false`(예약) 몫으로 넣고 `available`에서 뺀다. 가장 이른 수입 기간은 잔액이 모자라도 나머지를 전부 가져가 마이너스가 되게 한다(부족을 오늘 보여 준다). 앞 기간에 수입이 없어 맡길 곳이 없으면 부족분도 home의 몫(`funded`)에 합친다. home에는 `funded`를 `due_in_period = true` 몫으로 넣는다. 각 항목은 `(occurrence, share, remaining_total, due_in_period)`다. | 코드 확인 |
| R-59 | 급여 계획: 기간 지표와 현금 | 기간별: `due_total = Σ(due_in_period 몫)`, `reserved_total = Σ(예약 몫)`, `obligation_total = 둘의 합`, `remaining = income − obligation_total`, 항목은 몫 큰 순. 다리(bridge) 기간 = `leading`이고 수입이 양수가 아닌 기간(오늘~다음 급여 사이에 들어오는 돈이 없는 구간). `short?`: 다리 기간이면 `cash_on_hand`가 있고 `obligation_total > cash_on_hand`, 아니면 `remaining < 0`. `shortfall`: 다리면 `obligation_total − cash_on_hand`, 아니면 `−remaining`(부족 아니면 0). `cash_after_obligations`: 다리이고 현금이 있을 때 `cash_on_hand − obligation_total`. `cash_on_hand`는 `leading` 기간에만 붙고: 가족의 보이는(draft·active) `Depository` 계정 중 접근 가능하고 세제 혜택 계좌가 아닌 것의 잔액을 Family 통화로 환산해 합한다. 대상 계정이 없으면 nil, 하나라도 환산에 실패하면 nil(부분 합을 쓰지 않는다)이고 실패 계좌 수를 센다. nil이면 "알 수 없음"이라 부족으로 판정하지 않는다. | 코드 확인 |
| R-60 | 급여일을 정하는 것 | **직접 선언한(`manual`) 활성 수입 series만** 급여일을 정한다. 감지된 수입은 확인(`active`)해도 `manual = false`라서 계획에 안 들어간다. 부호만으로 수입을 판정하지 않는다(1원 이체는 수입이어도 급여일이 아니다). 급여 화면은 수입 series(`suggested`·`ended` 제외) 중 `active`가 아니거나 `manual`이 아닌 것이 있으면 "주의 필요"로 표시한다. series별 다음 급여 = `due_on`이 오늘 이후인 가장 이른 열린 급여 occurrence(`next_expected_date`는 안 쓴다). 같은 날 여러 급여는 합쳐 한 이벤트로 보인다(합계는 Family 통화로 환산, 환산 실패는 개수만 센다). | 코드 확인 |

**선언·편집·접근·feed**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-61 | 선언 청구서 생성(`DeclaredBill`) | 입력: `name`, `amount`, `currency`, `account_id`, `first_due_on`, `frequency_preset`(+`frequency_interval`·`unit`), `category_id`, `payment_url`, `autopay`, `notes`, `is_income`. 기본 시각 규칙: 계정이 있으면 쓰기 가능한 계정이어야 하고(아니면 오류), 날짜를 파싱하지 못하면 오류, 금액은 절댓값이며 파싱 실패·비유한(`Infinity`, `NaN`)·0이면 오류, 수입이면 음수로 저장한다. 금액은 통화 표의 최대 소수 자릿수(주석상 8)로 반올림한 값이 4자리로 반올림한 값과 같아야 한다(부동소수 잡음은 허용, 그보다 세밀하면 "너무 정밀"). 카테고리는 수입이면 무시하고, 아니면 가족 것이어야 한다(아니면 오류). 통화 = 폼 값(표에 있는 코드) → 계정 통화 → Family 통화. 저장: `status = active`, `manual = true`, `occurrence_count = 0`, `bill_type = 수입 ? income : bill`, `expected_day_of_month = 기한의 일`, `anchor_date = last_occurrence_date = next_expected_date = first_due_on`, 주기는 R-11로 규칙 변환, `dedup_scope`는 비면 금액 문자열. **계정이 없는 선언은 같은 (가맹점 또는 name, currency, dedup_scope, 이체 여부)가 이미 있으면 앱 코드로 거부**하고(R-04), 저장은 savepoint 안에서 하며 unique 충돌은 "이미 존재" 오류로 돌려준다. 폼에서 거래를 출발점으로 열면(`entry_id`) 저장 전에 거래별 lock 아래 `covering`을 확인해 있으면 막고, `allow_duplicate=1`일 때만 별도 청구서로 만든다. 기본값(폼): 수입은 `biweekly`, 지출은 `monthly`, 첫 기한 오늘. 저장 성공이면 `/bills`로 이동. | 코드 확인 |
| R-62 | series 편집(`update`) | 이름, 금액(크기 입력, 수입이면 음수 부호 유지, 정밀도 검사), 계정(비면 "아무 계정", 값이 있는데 쓰기 가능한 계정이 아니면 오류로 거부), 주기 프리셋(바꿨을 때만 `schedule_pinned_at`을 찍는다, R-17), 그리고 허용 필드 `payment_url`, `autopay`, `notes`, `bill_type`, `category_id`, `renews_on`, `trial_ends_on`, `cancelled_on`, `end_after_count`만 받는다. `currency`와 `first_due_on`은 편집하지 않는다. `bill_type = installment`이고 `end_after_count`가 있으면 `end_mode = after_count`로 하고 `anchor_date ||= last_occurrence_date`. 저장 성공 뒤 `apply_to_siblings=1`이고 `payment_url`이 비지 않았으면, 같은 가맹점(가맹점 없으면 정확히 같은 name)이고 쓰기 가능한 계정(또는 계정 없음)에 속한 다른 series의 `payment_url`을 `update_all`로 같은 값으로 바꾼다(가맹점·이름이 둘 다 없으면 대상 없음). | 코드 확인 |
| R-63 | 삭제·기각 | `dismiss` = `ended`. `destroy`: `manual`이면 행을 삭제(occurrence·allocation·규칙·변동·거부 기록이 같이 지워진다), 아니면 `ended`로 남긴다(감지가 되살리지 못하게 하는 표식). 알림 뒤 `/bills/:id`에서 왔으면 `/bills`로, 아니면 이전 화면으로 간다. | 코드 확인 |
| R-64 | series 접근·쓰기 범위 | 읽기: series의 `account_id`와 `destination_account_id` 중 값이 있는 것이 **모두** 사용자의 접근 가능 계정이어야 한다(둘 다 null이면 가족 모든 구성원이 본다). 쓰기(편집·상태 변경·삭제·확인·기각·정산 연산): 계정이 null이거나 쓰기 가능한 계정일 때만이고, 아니면 404다. 이체 series의 쓰기 판정은 출금 계정만 본다. | 코드 확인 |
| R-65 | iCal feed(계약만) | `GET /bills_feed/:token`(형식 `.ics`): 토큰은 서버 비밀로 서명된 `[user_id, 가족 feed 토큰의 SHA256 앞 16자]`이고, 서명·사용자·가족의 현재 스탬프가 모두 맞아야 한다. 사용자의 미리보기 설정이 꺼졌거나 가족이 기능을 껐으면 404. 토큰을 교체(`reset_feed_token`)하면 이전 URL이 전부 무효다. 이벤트 = 접근 가능한 `active` series(`amount > 0`)의 열린 occurrence 중 `due_on`이 오늘~오늘+90일인 것, `due_on` 순. 각 이벤트: UID `<occurrence id>@sure-bills`, `DTSTART;VALUE=DATE` = `effective_due_on`(yyyymmdd), `SUMMARY` = `표시 이름 (통화 서식 금액)`(쉼표·세미콜론·역슬래시 이스케이프, 개행은 공백). 캘린더 이름·PRODID `-//Sure//Bills//EN`. 인증은 세션이 아니라 토큰이다. | 코드 확인 |

- 불변식:
  - occurrence는 `(series, original_due_on)`당 하나다(R-33).
  - `confirmed` allocation의 거래 용량 합은 거래 금액을 넘지 않는다(R-44, 단 환율 없는 allocation 하나는 예외).
  - `status = scheduled` ⇔ `closed_at` null(DB check). `paid`가 되려면 보통 `confirmed` 합이 기대 금액에 찬다(R-43). 단 `mark_paid`는 남은 금액만큼 거래 없는 allocation을 먼저 만든다.
  - 감지는 `manual` series와 `ended` series를 갱신·재생성하지 않는다(R-16).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-30, R-23 | `Sync#perform` 블록 안에서 큐에 넣은 `IdentifyRecurringTransactionsJob`이 worker에서 큐에 넣을 때의 `Time.zone`을 복원해 Family 시간대로 도는지, 앱 기본(UTC)으로 도는지 | 식별 단계의 "3개월 전", "45일", `next_expected_date`의 기준 날짜가 한국에서 하루 어긋날 수 있다 | Rails 8.1.4.1 ActiveJob의 직렬화 동작(gem 소스)이나 실제 job 실행 로그로 확인 |
| U-02 | R-24 | `lock: :until_executed, on_conflict: :log` 선언이 같은 job의 중복 큐잉을 실제로 막는지 | 야간 job이 겹쳐 실행될 수 있는지(R-22의 advisory lock이 직렬화는 하므로 결과 영향은 작음) | 사용하는 sidekiq lock gem의 문서·소스 확인 |
| U-03 | R-18 | Ruby 정규식 `\b`가 한글과 공백·영문 경계에서 어떻게 동작하는지(한글 키워드를 추가할 때) | 적용 메모의 한글 키워드 추가 방식(`\b` 대신 별도 경계)을 정해야 한다 | 실행해 확인(`"넷플릭스 구독".match?(/\b넷플릭스\b/)` 등) |

- 확인 한계:
  - U-01~U-03은 gem·런타임 동작이라 읽거나 실행하지 못했다.
  - 이 환경에서 코드를 실행하지 않았다(레포 지침). T-ID의 날짜·점수 값은 코드를 읽고 Python(IEEE 부동소수와 `Decimal`)으로 같은 식을 재계산한 값이다. Rails 날짜 산술(`3.months.ago`, `Date#next_month`가 말일로 줄이는 것)은 프레임워크 동작을 읽은 해석이다.
  - 뷰·Stimulus, AI 보조 파일(`ai_setup_suggester.rb` 외 컨트롤러·어시스턴트 도구), API v1, 예산·인사이트 소비 쪽은 열지 않았다. UI가 감추는 선택지와 문구는 R-ID가 아니다.
  - 점수식은 Float와 BigDecimal을 섞어 합한 뒤 소수 4자리로 반올림한다. 반올림 후의 값으로 문턱(0.85, 0.60)을 비교하므로 경계값은 위 값으로 판정한다고 읽었다(추론, Ruby 수치 형 변환 규칙).
  - `family.tax_advantaged_account_ids` 본문, `Account.accessible_by`·`writable_by`, `Transaction#pending?`, `Transfer` 생성 규칙은 호출자 계약으로 두고 읽은 만큼만 적었다(위 1.2).

### 1.5 필수 코드 참조

라이선스는 AGPL-3.0(overview 1절)이다. 아래 C-ID는 규칙을 옮기기 위한 위치이고 복사 여부는 별도 결정이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `db/schema.rb:2085-2231` `recurrence_rules`, `recurring_allocations`, `recurring_match_rejections`, `recurring_occurrences`, `recurring_price_changes`, `recurring_transactions` | 컬럼·기본값·unique·check 제약(partial unique 인덱스 4개) | R-04, R-05, 1.3 |
| C-02 | `app/models/recurring_transaction/identifier.rb:17-36`, `:210-282` `DEFAULT_TOLERANCE_PCT`, `MINIMUM_CANDIDATE_AMOUNT`, `NON_BILLABLE_ACCOUNTABLE_TYPES`, `collect_patterns` | 식별 입력 선택, 그룹 키, 채택 조건, 패턴 필드 | R-13, R-15 |
| C-03 | `identifier.rb:289-311`, `:331-335`, `:552-605` `cluster_by_amount`, `within_tolerance?`, `nearest_within_tolerance`, `days_cluster_together?`, `calculate_expected_day` | 군집·claim 허용 오차식, 원형 중앙값 기대일 | R-14, R-15, R-16 |
| C-04 | `app/models/recurring_transaction/schedule.rb:15-25`, `:69-96`, `:195-230` | 상수, 원형 거리, SQL 일자 창, `matches_day?` 판정 | R-12 |
| C-05 | `schedule.rb:255-413` `adjusted_pairs`, `lifetime_pairs`, `adjust_for_weekend`, `raw_occurrences`, `weekly/monthly/yearly_occurrences`, `date_in_month`, `nth_weekday_in_month`, `longest_period_days` | 세 빈도의 날짜 생성, 말일 줄임, n번째 요일, 주말 보정, 횟수 종료 | R-06, R-07, R-08 |
| C-06 | `schedule.rb:107-192` `occurrence_pairs_between`, `first_occurrence_after`, `cycle_for`, `occurrences_per_year`, `next_occurrence_after`, `next_occurrence_from_today`, `legacy_monthly?`(`:242-253`), `occurrence_in_month`(`:409-413`) | 탐색 도우미와 옛 단일 월 규칙 경로(말일 줄임 차이) | R-09, R-10 |
| C-07 | `app/models/recurring_transaction/classifier.rb:12-128` | 키워드 목록 4종, 분류 순서, 단어 경계 정규식, 150 문턱, 최빈 카테고리 | R-18 |
| C-08 | `app/models/recurring_transaction/matcher.rb:12-21`, `:313-329`, `:359-374`, `:394-439` `EXACT_TIER`, `HIGH_TIER`, `AMBIGUITY_MARGIN`, `MAX_LEARNED_TOLERANCE_PCT`, `window_for`, `identity_matches?`, `score`, `amount_score`, `date_score` | 문턱, 창, 정체성 필터, 점수식 | R-37~R-40 |
| C-09 | `matcher.rb:111-165`, `:187-226`, `:256-273` `apply`, `tier_for`, `unambiguous?`, `collect_candidates`, `prune_to_nearest_per_series`, `entries_for` | 정렬·배정 순서, 등급 판정, 후보 가지치기, entry 쿼리 조건 | R-37, R-40 |
| C-10 | `app/models/recurring_transaction/allocator.rb:233-248`, `:250-301`, `:322-327`, `:340-367`, `:385-415` `close_worthy?`, `resolve_amounts`, `entry_capacity`, `learn_from_manual_attach!`, `guard_entry_capacity!` | 닫힘 자격, 금액 기본값·환산, 거래 용량, 학습, 초과 배정 거부 | R-43~R-45 |
| C-11 | `app/models/recurring_transaction/price_change_detector.rb:20-73`, `app/models/recurring_price_change.rb:19-28` | 가격 변동 조건 전체와 중요 변동 문턱 | R-46, R-47 |
| C-12 | `app/models/recurring_transaction.rb:798-813` `staleness_threshold_date`, `should_be_inactive?`, `app/models/recurring_transaction/cleaner.rb:20-39` | stale 문턱식과 정리 판정 | R-48 |
| C-13 | `app/models/recurring_transaction/paycheck_planner.rb:82-163` `plan`, `period_boundaries`, `build_periods`, `upcoming_income_occurrences`(`:128-139`) | 기간 경계·수입 집계·급여 occurrence 조건 | R-57, R-60 |
| C-14 | `paycheck_planner.rb:176-232` `apportion_bills`, `:234-256` `open_payable_occurrences` | 배분 알고리즘 | R-58 |
| C-15 | `paycheck_planner.rb:11-71`, `:266-310` `Period`(`bridge?`, `short?`, `shortfall`, `cash_after_obligations`), `cash_on_hand`, `to_family_currency` | 기간 지표, 현금, 환산 실패 처리 | R-59 |
| C-16 | `app/models/recurring_transaction/frequency_preset.rb:7-15`, `:23-41`, `:123-137`, `:149-236` `PRESETS`, `detect`, `every`, `target_detection`, `write`, `canonical_semimonthly_days`, `authoritative_day` | 프리셋↔규칙 변환 표 | R-11 |
| C-17 | `app/models/recurring_occurrence.rb:41-127` | 예상 금액 해석, remaining, 파생 상태 | R-31, R-32 |
| C-18 | `app/models/recurring_transaction/occurrence_generator.rb:20-131` | 생성 구간, 지평, 유한 계획, stood-in, 반 주기 | R-33, R-34 |
| C-19 | `app/models/recurring_transaction.rb:585-633`, `:637-702` `covering`, `identity_taken_by`, `create_from_transaction` | 중복 판정, 거래에서 만드는 정기 거래 | R-27, R-29 |
| C-20 | `app/models/recurring_transaction/pipeline.rb:20-77`, `app/jobs/identify_recurring_transactions_job.rb:8-55` | 파이프라인 순서, lock 키, debounce | R-22, R-23 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 날짜·점수는 위 규칙대로 직접 계산한 값이다. 한국에서 의미 있는 입력은 `[KR]`로 표시한다(원본 동작을 한국 값으로 쓴 사례이고, 한국에 맞춰 바꾸는 것은 적용 메모다). 통화는 KRW 가정이며 소수점은 없다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-15 | 기대일 계산: 거래일(일) `[1, 2, 29, 30, 31]`, `[5, 6]`, `[5, 10, 15]`, `[1, 31]`. | 기대일 31 (거리 `[1,2,2,1,0]`, 모두 ≤ 2라 채택), 6(짝수 중앙 4.5를 half-up, 거리 `[1,0]`), 10(거리 5라 채택 안 됨), 1. 월말에서 다음 달 초로 넘어가는 군집도 한 군집이다. |
| T-02 | R-14 | `[KR]` 같은 가맹점의 금액 `[9000, 9500, 9900, 10500, 12000]` 군집화. | 군집 `[9000, 9500, 9900]`, `[10500]`, `[12000]`. 9900은 평균 9250에서 650 ≤ 693.75라 들어가고, 10500은 평균 9466.67에서 1033 > 710이라 새 군집. 또 `[17000, 17000, 18000]`은 한 군집(1000 ≤ 1275), `[17000, 17000, 19000]`은 둘(2000 > 1275). 수입 `[-3000000, -3000000, -3300000]`은 `[-3300000]`과 `[-3000000, -3000000]`로 나뉘어 둘 다 3건 미만이다(상여금 달이 급여 군집을 깬다). |
| T-03 | R-13~R-16, R-18 | 오늘 2025-06-20, 가맹점 있는 거래 17,000원이 2025-04-10, 05-10, 06-10(계정 A, 신용카드, 이름 `NETFLIX`)에 있고 기존 series 없음. 식별 실행. | `suggested` series 1건: `amount 17000`, min/max/avg 모두 17000, `expected_day_of_month 10`, `last_occurrence_date 2025-06-10`, `next_expected_date 2025-07-10`, `occurrence_count 3`, `dedup_scope ""`, `manual false`, 가맹점 키라 `name null`. 이름이 `netflix` 키워드라 `bill_type subscription`, `autopay true`. 2건뿐이면 만들지 않고, 마지막 거래가 2025-05-05 이전이면(45일 초과) 만들지 않는다. |
| T-04 | R-18 | `[KR]` 같은 거래를 이름만 바꿔 분류: `NETFLIX`, `넷플릭스`(둘 다 17,000원 고정, 신용카드), `인터넷 요금 internet`, `KT 인터넷`. | `NETFLIX` → subscription, autopay true. `넷플릭스` → **bill**, autopay false(영문 키워드에 없고, 150원 이하 조건이 17,000에서 깨짐). `인터넷 요금 internet` → bill(`internet`이 단어 경계로 잡힘). `KT 인터넷` → bill, 이름 신호가 없어 기본값. 한글 키워드는 없으므로 한국어 가맹점 이름만으로는 subscription이 되지 않는다. |
| T-05 | R-19, R-13 | `[KR]` 이름 키 series `쿠팡 결제`. 거래 이름 `"  쿠팡   결제 "`, `"쿠팡(주) 결제"`, 식별에서 원문 `"쿠팡 결제 "`와 `"쿠팡 결제"`. | 정규화 `"쿠팡 결제"`로 첫 거래는 매칭 후보(이름 집합에 포함), 둘째는 아님. 식별은 원문으로 묶으므로 뒤쪽 두 거래는 서로 다른 그룹이다(공백 한 칸 차이로 군집이 갈린다). 가맹점 id가 있으면 이름 차이는 무관하다. |
| T-06 | R-09 | 옛 단일 월 규칙, 기대일 31. `next_occurrence_after`: 마지막 날짜 2024-01-31, 2024-02-29, 2023-01-31, 기대일 30에서 2025-01-30. | 2024-02-29, 2024-03-31(이전 날짜의 일자가 아니라 달만 본다), 2023-02-28, 2025-02-28. |
| T-07 | R-09, R-06 | `[KR]` 말일 급여. 거래일 2025-05-31로 "정기 거래로 표시"한 날 오늘이 2025-06-20(기대일 31, 규칙 없음). | `next_expected_date = 2025-07-31`(6월 31일이 없어 6월을 건너뜀). 반면 occurrence 생성(엔진)은 2025-06-30을 낸다. UI의 다음 청구일은 occurrence 기준이라 6월 30일이고, 거래 목록의 "예정"(R-56, `next_expected_date` 기준)은 6월 30일에 보이지 않는다. 오늘이 2025-04-10이고 기대일 31이면 `next_occurrence_from_today = 2025-05-31`, 오늘이 2025-01-15면 2025-01-31, 2025-01-31이면 2025-02-28. |
| T-08 | R-06 | 엔진: 월 규칙 `day_of_month 31`(그리고 -1)로 `occurrences_between(2025-01-01, 2025-04-30)`. | `[2025-01-31, 2025-02-28, 2025-03-31, 2025-04-30]`. 격주 금요일(규칙 `weekly`, `weekday 5`, `interval 2`, `anchor 2025-01-03`)의 `occurrences_between(2025-01-20, 2025-02-10)` = `[2025-01-31]`(01-03, 01-17, 01-31, 02-14 중). 분기(월, 15일, `interval 3`, 앵커 2025-01-15)의 2025년 = `[01-15, 04-15, 07-15, 10-15]`. 연 규칙 2월 29일의 `occurrences_between(2025-01-01, 2026-12-31)` = `[2025-02-28, 2026-02-28]`, 2028년은 02-29. |
| T-09 | R-07 | `[KR]` 급여일 25일 월 규칙에 `weekend_adjust`를 바꿔서 2025-10-25(토), 2025-05-25(일), 2025-04-25(금). | `before`: 2025-10-24, 2025-05-23, 2025-04-25. `after`: 2025-10-27, 2025-05-26, 2025-04-25. `skip`: 토·일 회차는 없고 금요일만 있다. `none`: 그대로. 어느 경우도 `original_due_on`은 25일이다. 공휴일(예: 2025-10-03 개천절 금요일)은 보정되지 않는다. |
| T-10 | R-08 | 월 규칙 10일, `after_count`, `end_after_count 3`, `anchor_date 2025-01-10`로 2025-12-31까지 생성. `on_date`, `end_on 2025-02-10`(같은 월 10일 규칙, 앵커 2025-01-10). | 횟수: `[2025-01-10, 2025-02-10, 2025-03-10]`. 날짜: `[2025-01-10, 2025-02-10]`(당일 포함)이고 03-10은 없다. 어느 쪽도 series status는 `active`로 남는다. |
| T-11 | R-12 | 월 규칙 31일에서 2025-03-02 거래, 월 규칙 30일에서 2025-02-28 거래, 매주 금요일 규칙에서 토요일 거래. | 셋의 결과: 2025-03-02는 맞음(2월 말일 28과 2일 차), 02-28은 맞음(30을 28로 줄인 거리 0), 토요일은 맞지 않음(주 규칙 오차 0). |
| T-12 | R-39, R-40 | 오늘 2025-06-17. 가맹점 series 기대 17,000, 계정 A, occurrence due 2025-06-10(오늘이 `06-13`을 넘어 `overdue`지만 창 끝이 `max(06-17, 오늘)`이라 창은 `[06-08, 06-17]`, span 9). entry 17,000(06-13, 계정 A): 가맹점 0.40, 금액 0.30, 날짜 `0.20−(3/9)×0.15=0.15`, 계정 0.10. 17,500(06-10): 금액 `0.25−(500/1275)×0.10=0.2108`(자동 매칭된 allocation의 `allocated_amount`는 `min(17500, 잔액 17000) = 17000`). 18,500(06-10). 17,000(06-18, 오늘 2025-06-18이면 `overdue`라 창이 `[06-08, 06-18]`(span 10)으로 늘어나 후보가 되고 날짜 `0.20−(8/10)×0.15=0.08`, 합 `0.40+0.30+0.08+0.10=0.88`로 exact). 이름 series, 정확 금액, 7일 늦음. | 0.95 → exact → `confirmed`. 17,500은 `0.40+0.2108+0.20+0.10=0.9108` → exact. 18,500은 8.8% > 7.5%라 후보 탈락. 06-18은 오늘이 06-17이면 창 밖이라 후보 아님(위 조건에서는 후보). 이름 series 7일 늦음은 날짜 `0.20−(7/9)×0.15=0.0833` → `0.35+0.30+0.0833+0.10=0.8333` < 0.85 → `suggested`. 17,001원은 차이 1(≥ 0.01)이라 금액 `0.25−(1/1275)×0.10=0.2499`, 정확 일치로 치지 않는다. |
| T-13 | R-40 | 같은 가맹점의 두 series(A 10,000, B 10,500)와 둘 다 due 2025-06-10인 occurrence, entry 10,000(06-10, 같은 계정). | A는 1.00, B는 `0.40+0.1865+0.20+0.10=0.8865`(차이 500 ≤ 787.5, 금액 `0.25−(500/787.5)×0.10=0.1865`). 차이 0.1135 < 0.15라 모호. 정렬상 A가 먼저 배정되고 등급은 `high`로 낮아져 A에 `suggested` allocation 1건이 생기고 B에는 아무것도 없다(entry는 한 번만 배정). |
| T-14 | R-40 | T-12의 17,000 entry가 보류(pending) 거래, 같은 상황에서 series가 수입일 때. | 지출 series: 신뢰도 1.0이어도 exact 불가 → `high` → `suggested`. 수입 series: 보류이거나 모호하면 아무것도 쓰지 않는다. |
| T-15 | R-43, R-45 | 기대 17,000, 허용 7.5%(1,275). 거래를 기본 금액으로 연결: 17,500 / 10,000 / 10,000 다음 7,000 / 19,000 / 22,000. | 17,500은 할당이 `min(17500, 17000) = 17000`이라 `|0| ≤ 1275`로 `paid`(`auto`). 10,000은 열림, `partially_paid`, remaining 7,000. 10,000+7,000은 합 17,000 ≥ 17,000−0.01로 `paid`. 19,000도 할당 17,000이 허용 안이라 `paid`이고, 학습은 거래 금액 기준 편차 `(19000−17000)/17000 = 11.76%`(> 7.5, ≤ 25)라 `learned_tolerance_pct = 11.8`(`allocator.rb:356`). 22,000은 할당 17,000으로 `paid`이나 편차 29.4% > 25라 학습 없음. 사용자가 닫은 `paid`(`user`)는 연결을 지워도 열리지 않고, 자동으로 닫힌 것은 자격이 없어지면 열린다. |
| T-16 | R-44 | 거래 30,000을 occurrence A(기대 20,000)에 기본 금액으로 연결하고, 이어서 occurrence B(기대 17,000)에 기본 금액으로, 이어서 명시 15,000으로, 다시 한 번 기본으로 연결. | A는 `min(30000, 20000) = 20000`. B 기본은 용량 10,000이라 `min(10000, 17000) = 10000`. 명시 15,000은 `15000 > 0 + 0.01`(남은 용량 0)이라 소진 오류. 같은 occurrence에 같은 거래를 다시 연결하면 "이미 연결됨". 용량이 10,000인 상태에서 명시 15,000은 `15000 > 10000.01`이라 초과 배정 오류. |
| T-17 | R-46 | series(자동 감지, 기대 17,000)의 `paid` occurrence 2025-04-10, 05-10이 각각 확정 allocation 1건 19,000(웹에서는 거래 없는 수동 결제 `amount=19000`, 또는 직접 POST로 거래+금액). 감지 실행. 이어서 (a) 같은 데이터에서 series가 `manual`, (b) 05-10 occurrence에 allocation이 둘, (c) 19,000 거래를 기본 금액으로 연결, (d) 인하: 거래 16,000을 두 회차에 기본 연결, (e) 인하 15,000을 두 회차에 기본 연결. | 변동 1건 `effective_on 2025-05-10`, `17000 → 19000`, `shift 0.1176 → material`, series `amount = 19000`(수동 결제면 변경 기록 `entry null`). (a) 변동은 기록, `amount`는 17,000 그대로, 다음 실행은 마지막 변동이 같은 `new_amount`라 만들지 않는다. (b) 감지 없음. (c) 기본 연결은 `min(19000, 잔액 17000) = 17000`으로 기록돼 감지되지 않는다. (d) 16,000은 허용 안(5.9%)이라 매칭되고 할당 16,000이 단일 허용 오차 안이라 `paid`, 두 회차 모두면 `17000 → 16000`으로 감지된다. (e) 15,000은 매칭 탈락이고 수동 기본 연결의 할당 15,000은 단일 허용 밖(2,000 > 1,275)이며 합도 모자라 `paid`가 안 되므로 감지되지 않는다. |
| T-18 | R-48 | `[KR]` 자동 감지 월 단위 series, 오늘 2025-03-31. `last_occurrence_date`가 2025-01-30, 2025-01-28. 같은 series가 `manual`. 연 단위(`occurrences_per_year = 1`) 자동 series, 오늘 2025-06-10. | 월 단위 문턱 = `min(2025-01-31, 오늘−61일 = 2025-01-29) = 2025-01-29`: 01-30은 stale 아님, 01-28은 stale → 매칭 거래가 `2025-01-29` 이후에 없으면 `inactive`. `manual`은 달력 하한 2024-09-30(6개월)과 2025-01-29 중 이른 2024-09-30. 연 단위는 `min(2025-04-10, 오늘−731일 = 2023-06-10) = 2023-06-10`. 주 단위는 `ceil(2×365.25/52.18) = 14`일이라 달력 하한(2개월)이 문턱이다. 정리 버튼을 누르지 않으면 어느 경우도 `inactive`가 되지 않는다. |
| T-19 | R-13, R-16 | `[KR]` 신용카드 대금 결제 `kind = cc_payment`(그 계정에서 같은 금액·같은 날)가 3개월 연속. 식별 실행. 또 같은 거래를 이체(`Transfer`)로 인식시킨 뒤 "이체에서 정기 거래로 표시". | 식별은 `kind`가 이체 4종인 거래를 읽지 않아 패턴이 없다. 이체 표시를 하면 `bill_type transfer`, `destination`이 `CreditCard` 계정이면 `payable`에 들어가 청구서로 보이고, 이름은 `Payment to <카드 계정 이름>`이다. 카드 결제일 일정은 이 선언으로만 생긴다. |
| T-20 | R-27 | `[KR]` 급여 입금 거래(이름 `급여`, `-3000000`, 가맹점 없음, 2025-06-25)를 "정기 거래로 표시". 오늘 2025-06-20. 같은 이름으로 `-3200000` 입금이 이미 `active` series 이름 `급여`(금액 -3,000,000)로 있는 경우. | 새 series: `name 급여`, `amount -3000000`, `bill_type income`, `manual true`, `category null`, `expected_day 25`, `next_expected_date 2025-06-25`, `dedup_scope "-3000000.0"`, 급여일 계획의 급여가 된다(R-60). 같은 이름 `급여`, 금액 -3,000,000인 `active` series가 이미 있는 상태에서 `-3200000` 입금을 표시하려 하면, `covering`이 구간 `[-6000000, -1500000]`(부호 있는 값의 min/max) 안의 금액과 정규화 이름 일치로 찾아 "이미 포함됨"으로 막는다. |
| T-21 | R-23 | 한 sync에서 Account `Sync` 완료 이벤트가 t0, t0+5초, t0+9초에 발생. 마지막 하나는 incomplete `Sync`가 남은 상태에서 job이 실행. | 예약 3회, cache는 t0+9의 시각. 앞의 두 job은 cache 값이 자기 시각보다 커서 끝나고, 셋째 job은 incomplete `Sync`가 있으면 끝나 마지막 `Sync`의 완료 이벤트가 다시 예약한다. incomplete가 없으면 lock을 잡고 `run!`(backfill 없음)을 실행한다. |
| T-22 | R-30 | `[KR]` Family 시간대 `Asia/Seoul`. 한국 시각 2025-06-21 07:00(UTC 2025-06-20 22:00)에 (a) 사용자가 청구서 화면을 연다, (b) 같은 시각에 야간 occurrence 생성 job(R-24)이 돈다. | (a) `Date.current = 2025-06-21`. (b) 야간 job은 `Date.current = 2025-06-20`(UTC)이라 occurrence 생성 구간이 하루 다른 날짜를 쓴다. sync 후 식별 job(R-23)이 같은 시각에 돌면 어느 날짜를 쓰는지는 U-01이 닫힌 뒤 정해진다. |
| T-23 | R-57~R-59 | `[KR]` 오늘 2025-06-20(금), KRW. 직접 선언한 수입 급여 3,000,000원 매월 25일(`first_due_on 2025-06-25`). 직접 선언한 월 청구서: 통신 60,000원(`first_due_on 2025-06-22`), 월세 900,000원(`first_due_on 2025-07-01`), 연 청구서 보험 4,000,000원(`first_due_on 2025-07-28`). 생성 지평은 오늘+90일 = 2025-09-18까지다. 예금 계좌 잔액 합 100,000원. `periods_limit 3`으로 계획. | 열린 회차: 급여 06-25, 07-25, 08-25, 통신 06-22, 07-22, 08-22, 월세 07-01, 08-01, 09-01, 보험 07-28. 경계 `[06-20, 06-25, 07-25, 08-25]`, 기간 P1 `[06-20, 06-24]`(leading, 수입 0), P2 `[06-25, 07-24]`(수입 3,000,000), P3 `[07-25, 08-24]`(final, 수입 3,000,000). 배분 대상은 마지막 기간 끝 08-24 이하의 모든 열린 청구 회차이고 날짜순(06-22 통신, 07-01 월세, 07-22 통신, 07-28 보험, 08-01 월세, 08-22 통신)으로 처리한다. 통신 06-22: home P1, 앞 기간 없음 → P1에 60,000(due), `available[P1] = −60,000`. 월세 07-01: P2에 900,000(due). 통신 07-22: P2에 60,000(due). 이때 `available[P2] = 2,040,000`. 보험 07-28(P3): `funded = min(4,000,000, 3,000,000) = 3,000,000`, 부족 1,000,000은 앞 수입 기간 P2가 예약(`due_in_period false`)해 `available[P2] = 1,040,000`, `available[P3] = 0`. 월세 08-01(P3): `funded 0`, 부족 900,000을 P2가 예약 → `available[P2] = 140,000`, P3에는 몫 0인 due 항목이 들어간다. 통신 08-22(P3): 같은 방식으로 60,000을 P2가 예약 → `available[P2] = 80,000`. 결과: P1 due 60,000, obligation 60,000, remaining −60,000, 다리 기간이라 `short?`는 `60,000 > 100,000`이 아니어서 false, `cash_after_obligations 40,000`. P2 due 960,000 + reserved 1,960,000 = obligation 2,920,000, remaining 80,000. P3 due 3,000,000, remaining 0(부족 아님). 현금을 30,000으로 바꾸면 P1은 short, shortfall 30,000. 현금이 있는 계좌가 없으면 `cash_on_hand nil`이라 부족으로 판정하지 않는다. 월세가 `first_due_on 2025-06-01`로 선언돼 06-01 회차가 아직 열려 있다면(연체) `max(effective_due_on, 06-20)`으로 P1에 900,000이 통째로 들어가 P1 obligation은 960,000이고 현금 100,000 대비 shortfall 860,000이다. |
| T-24 | R-60 | 감지된 수입 series(`bill_type income`, `manual false`)를 확인해 `active`로 만든 상태. | 급여 occurrence 없음 → 계획 nil, 급여 화면은 "주의 필요". 같은 거래로 "정기 거래로 표시"(`manual true`)하거나 선언하면 계획이 생긴다. |
| T-25 | R-61 | `[KR]` 선언 폼: `name 월세`, `amount "900000"`, `currency KRW`, `first_due_on 2025-07-01`, `frequency_preset monthly`, 계정 없음. 같은 값으로 다시 제출. 금액 `"0"`, `"Infinity"`, `"16.990000000000002"`. | 첫 제출: `status active`, `manual true`, `expected_day_of_month 1`, `anchor/last/next 2025-07-01`, `dedup_scope "900000.0"`, 월 규칙(`day_of_month 1`) 1개. 계정이 없어 DB unique가 막지 못하므로 둘째 제출은 앱 코드가 "이미 존재" 오류로 거부한다. `"0"`·`"Infinity"`는 금액 오류. 소수 잡음 값은 16.99로 저장된다. |
| T-26 | R-29, R-27 | 이름 키 series `넷플릭스`(17,000, 계정 A, 가맹점 없음). entry 이름 `넷플릭스`, 18,000(계정 A) / 40,000 / `-17000`. | 18,000은 구간 `[8500, 34000]` 안이고 이름이 아는 이름에 있어 "이미 포함됨"으로 막힌다. 40,000은 구간 밖이라 별도 series로 만들 수 있다(둘째 금액 단계). `-17000`은 부호가 반대라 구간 밖이다. |
| T-27 | R-65 | 접근 가능한 `active` series 월세(900,000원, 2025-07-01, `amount > 0`)와 수입 series, 오늘 2025-06-20. 올바른 토큰으로 feed 요청. 토큰 교체 후 옛 URL. 가족이 기능을 끔. | 이벤트 1건(수입은 `amount > 0`이 아니어서 없다): `UID <id>@sure-bills`, `DTSTART;VALUE=DATE:20250701`, `SUMMARY:월세 (<통화 서식 금액>)`. 교체 후와 꺼진 뒤에는 404(스탬프 불일치, 기능 꺼짐). |
| T-28 | R-35 | `suggested` series를 확인(`active`)할 때 그 가족 파이프라인이 lock을 잡고 있음. | 상태 변경은 성공하고, 즉시 이력 재구성은 건너뛰고 `BackfillRecurringHistoryJob`이 큐에 들어가 series가 `active`인 동안 재시도한다. 그 사이 사용자가 `inactive`로 바꾸면 job은 아무것도 안 한다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@1cd94e6 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `app/models/recurring_transaction.rb:29-36`, `app/controllers/recurring_transactions_controller.rb:40-57`, `:223-263`, `app/models/recurring_transaction/identifier.rb:452-479`, `app/models/recurring_transaction/cleaner.rb:20-39`, `app/controllers/api/v1/recurring_transactions_controller.rb:5-9`, `:232-238`, `app/models/assistant/function/update_bill.rb:216-230`, `app/models/assistant/function/bills_support.rb:8-17`, `app/models/recurring_transaction/occurrence_generator.rb:20-21` | 전이는 호출 코드를 읽은 것. "`ended`를 쓰는 곳은 dismiss·destroy뿐, `paused`를 쓰는 웹·API·어시스턴트 경로 없음, 종료 조건이 status를 바꾸지 않음": `grep -rn "\"ended\"\|:ended\|\.ended\b\|ended!" app lib --include=*.rb`와 `grep -rn "\"paused\"\|status: \"paused\"" app --include=*.rb`로 확인(app·lib의 .rb만, 마이그레이션·`db/seeds`·`test`는 안 봄). import는 `app/models/family/data_importer.rb:643-690`이 status를 넣는 것까지 확인. 놓칠 수 있는 것: 문자열을 조립하는 동적 호출. |
| R-02 | `recurring_transaction.rb:35-41`, `:284-294`, `:514-547`, `:637-702`, `recurring_transaction/declared_bill.rb:25-38`, `identifier.rb:459-474` | 코드 확인. |
| R-03, R-04 | `recurring_transaction.rb:43-62`, `:92-118`, `:168-201`, `:296-346`, `db/schema.rb:2175-2231` (C-01), `identifier.rb:483-491`, `declared_bill.rb:117-156` | partial unique 인덱스 4개와 `dedup_scope` 의미는 schema와 `create_from_transaction`(`:672-699`), `identity_conditions`를 읽은 것. NULL 계정이 인덱스를 피한다는 설명은 `declared_bill.rb:120-125`의 주석과 일치한다. |
| R-05 | `app/models/recurrence_rule.rb:11-50`, `db/schema.rb:2085-2105` | 코드 확인. |
| R-06 | C-05 `schedule.rb:255-413`, `:51-67`, `:232-237` | 알고리즘을 읽고 T-08을 손으로 계산. 5번째 요일이 없는 달 건너뜀은 `nth_weekday_in_month`(`:384-393`). |
| R-07 | `schedule.rb:255-265`, `:293-302`, `:17-19` | 코드 확인. "공휴일을 보지 않는다": `grep -rn "holiday_calendar\|holiday" app lib --include=*.rb`에서 `holiday_calendar`는 `app/models/family/data_exporter.rb:672`, `app/models/family/data_importer.rb:655`만 나온다(app·lib .rb 범위, `holidays` gem 사용 여부는 `Gemfile`을 열지 않음). |
| R-08 | `schedule.rb:107-124`, `:267-291`, `:51-67` | 코드 확인. |
| R-09 | C-06 `schedule.rb:172-192`, `:239-253`, `:407-413` | 코드 확인. "31일 규칙에서 엔진과 단축 경로가 다르다"는 `:183-189`의 주석("Preserved quirk")과 두 경로를 읽은 것. T-06~T-07 손계산. |
| R-10 | C-06 `schedule.rb:128-168`, `:395-405` | 코드 확인. |
| R-11 | C-16 `frequency_preset.rb:7-15`, `:23-75`, `:123-236` | 코드 확인. |
| R-12 | C-04 `schedule.rb:69-96`, `:195-230` | 코드 확인. T-11 손계산. |
| R-13 | C-02 `identifier.rb:210-237` | "`excluded`·보류·분할 원본 필터가 없다": `identifier.rb:206-282`를 전부 읽었고 `excluded`·`pending`·`parent_entry_id`·`split`이라는 단어가 이 구간에 없다(`grep -n "excluded\|pending\|split" app/models/recurring_transaction/identifier.rb` → 0건). 분할 원본이 `excluded = true`라는 사실은 [transactions](./transactions.md) R-16이다. `family.entries`가 계정 join을 하는지는 `accounts.accountable_type` 조건이 SQL에 쓰인 것으로 추론. |
| R-14 | C-03 `identifier.rb:289-311` | 코드 확인. T-02 Python 재계산. |
| R-15 | C-02, C-03 `identifier.rb:210-282`, `:552-605` | 코드 확인. "월 단위만 잡힌다"는 R-15 구조(3개월 창, 3건, 일 일관성)에서 추론. T-01 Python 재계산(`calculate_expected_day` 재현). |
| R-16 | `identifier.rb:106-152`, `:198-204`, `:331-335`, `:358-361`, `:452-491` | 코드 확인. |
| R-17 | `identifier.rb:367-390`, `:407-422`, `:436-450`, `recurring_transaction.rb:819-826` | 코드 확인. |
| R-18 | C-07 `classifier.rb:12-128`, `lib/tasks/recurring_bills.rake:20-49` | 코드 확인. "한글 키워드가 없다": 목록 전체를 읽었다. 단어 경계 정규식 `\b`가 한글 경계에서 어떻게 동작하는지는 실행하지 않았다(T-04의 `인터넷 요금 internet`은 영문 단어 `internet`이 공백으로 구분돼 있어 영향이 없다고 읽었다, 추론). |
| R-19 | `matcher.rb:27-29`, `recurring_transaction.rb:144-166`, `identifier.rb:233-236` | "유니코드 정규화가 없다": `grep -rn "unicode_normalize\|\.normalize" app/models/recurring_transaction* ` → `matcher.rb:27`의 `normalize_name`과 `allocator.rb:347,349`의 호출만(0건). 범위: 이 디렉터리와 `recurring_transaction.rb`. DB 쪽 collation은 안 봄. |
| R-20 | `identifier.rb:42-103`, `recurring_transactions_controller.rb:304-332` | 코드 확인. |
| R-21 | `identifier.rb:161-195`, `:493-540`, `recurring_transaction.rb:555-562` | 코드 확인. |
| R-22 | C-20 `pipeline.rb:20-77` | 코드 확인. Cleaner가 파이프라인에 없다는 것은 R-48의 검색. |
| R-23 | `app/models/family/sync_complete_event.rb:38-45`, `recurring_transaction.rb:496-499`, `app/jobs/identify_recurring_transactions_job.rb:8-55`, `sync.rb:127-133`, sync-pipeline R-11·R-18 | 코드 확인. 타이밍(30초, 40초)은 상수에서 읽은 값. |
| R-24 | `app/jobs/generate_recurring_occurrences_job.rb:5-39`, `config/schedule.yml:85-90` | 코드 확인. `lock: :until_executed`의 정확한 의미는 sidekiq-unique-jobs류 gem 동작이라 읽지 않음(추론). |
| R-25 | `recurring_transactions_controller.rb:18-20`, `:70-97`, `app/controllers/bills_controller.rb:118-133`, `recurring_feature_guardable.rb:15-18` | 코드 확인. |
| R-26 | `recurring_feature_guardable.rb:15-19`, `recurring_transactions_controller.rb:545-547`, `bills_feeds_controller.rb:27`, `transfers_controller.rb:150-155`, `recurring_transaction.rb:214-216`, `db/schema.rb:882`, `app/controllers/concerns/preview_gateable.rb:8-19` | 코드 확인. 미리보기 설정의 저장 위치(User 컬럼 `preview_features_enabled?`)는 호출자 계약. |
| R-27 | `transactions_controller.rb:484-540`, `:594-600`, C-19 `recurring_transaction.rb:637-702` | 코드 확인. `require_account_permission!`의 규칙은 transactions R-68. |
| R-28 | `transfers_controller.rb:150-207`, `recurring_transaction.rb:514-547`, `app/models/transfer.rb:78-85` | 코드 확인. |
| R-29 | C-19 `recurring_transaction.rb:585-633`, `:555-562` | 코드 확인. T-20, T-26 손계산. |
| R-30 | `app/models/sync.rb:183-185`, `Gemfile.lock:53`(activejob 8.1.4.1), `config/application.rb:28`(주석 처리), `app/models/family.rb:310-320`, `:822-840`, `app/controllers/concerns/localize.rb:115-126`(sync-pipeline R-24 참조), `app/jobs/*recurring*` | `grep -rn "use_zone\|resolved_time_zone" app lib --include=*.rb`에서 job 쪽은 `entry_scheduled_sync_job.rb`와 `monarch_import/converter.rb`뿐이고 정기 거래 job에는 없다. 범위는 app·lib의 .rb. Sidekiq 프로세스의 `TZ` 환경변수는 `Time.zone`에 영향이 없다는 것은 Rails 동작에 대한 추론이다. |
| R-31 | C-17 `recurring_occurrence.rb:13-35`, `:103-127`, `:133-160`, `:163-169` | 코드 확인. "`miss!` 호출처 없음": `grep -rn "miss!\|\.miss\b" app lib --include=*.rb` → `recurring_occurrence.rb:146` 정의 한 줄뿐. 범위 app·lib의 .rb, 놓칠 수 있는 것은 `send(:miss!)` 같은 동적 호출과 `.erb`(grep 안 함). 라우트에도 `miss` 액션이 없다(`config/routes.rb:652-659`). |
| R-32 | C-17 `recurring_occurrence.rb:41-99`, `:171-189`, `allocator.rb:227-231` | 코드 확인. |
| R-33 | C-18 `occurrence_generator.rb:20-34`, `:57-131` | 코드 확인. |
| R-34 | `recurring_transaction.rb:66-84`, `:256-265`, `occurrence_generator.rb:38-46` | 코드 확인. |
| R-35 | `recurring_transaction.rb:76-84`, `:203-254`, `history_backfiller.rb:16-55`, `app/jobs/backfill_recurring_history_job.rb:5-21`, `lib/tasks/recurring_bills.rake:1-18` | 코드 확인. |
| R-36 | `recurring_transaction.rb:267-282` | 코드 확인. |
| R-37 | C-09 `matcher.rb:187-273`, `:359-374` | 코드 확인. "series status를 보지 않는다": `matcher.rb:228-233`(`open_occurrences`)와 `identity_matches?`에 status 조건이 없다는 것을 읽음. `bills_controller.rb:648-651`의 주석이 같은 내용을 말한다. |
| R-38 | C-08 `matcher.rb:313-333` | 코드 확인. |
| R-39 | C-08 `matcher.rb:394-439` | 코드 확인. T-12·T-13은 Python `Decimal`로 재계산(0.2108, 0.1865, 0.0833 등). |
| R-40 | C-09 `matcher.rb:111-182`, `:222-226` | 코드 확인. |
| R-41 | `matcher.rb:50-85`, `:338-351` | 코드 확인. |
| R-42 | `recurring_occurrences_controller.rb:6-8`, `:30-77`, `recurring_allocations_controller.rb:6-77`, `allocator.rb:73-208`, `recurring_occurrence.rb:133-160`, `recurring_match_rejection.rb` | 코드 확인. `override_amount`의 음수 거부는 모델 검증 `expected_amount >= 0`(`recurring_occurrence.rb:31`). |
| R-43 | C-10 `allocator.rb:199-210`, `:233-248` | 코드 확인. |
| R-44 | C-10 `allocator.rb:37-63`, `:250-327`, `:385-415`, `recurring_allocation.rb:22-40` | 코드 확인. `cap_at_remaining`은 `allocate!`의 인자(`:73`, `:86-90`)이고 호출하는 쪽은 어시스턴트 도구라 읽지 않았다. 웹 컨트롤러는 쓰지 않는다(`recurring_allocations_controller.rb:11-17`). |
| R-45 | C-10 `allocator.rb:340-367`, `matcher.rb:21` | 코드 확인. |
| R-46 | `app/views/recurring_occurrences/_candidate.html.erb:50-65`(연결은 `entry_id`만), `app/views/recurring_occurrences/show.html.erb:248-266`(수동 결제는 `amount`·`paid_on`만), `grep -rn "override_amount" app/views` 0건(뷰 .erb 범위), `price_change_detector.rb:55-68`(transaction 없음), `pipeline.rb:20-39`(rescue 없음), C-11 `price_change_detector.rb:20-73`, `allocator.rb:250-301`, `recurring_transaction.rb:271-282` | 코드 확인. "인상은 감지되지 않는다"는 `resolve_amounts`의 `[capacity, remaining].min`(`allocator.rb:268-270`)과 감지기가 `allocated_amount`를 쓰는 것(`price_change_detector.rb:48`)의 조합에서 낸 귀결(추론, 실행 안 함). 설계 의도는 `allocator.rb:80-85` 주석("a single settlement above the expected amount is exactly how a price rise gets recorded")과 어긋난다. |
| R-47 | C-11 `recurring_price_change.rb:17-28`, `bills_controller.rb:563-581` | `source: "user"` 변동을 만드는 곳 없음: `grep -rn "RecurringPriceChange.create\|recurring_price_changes.*create" app --include=*.rb` → `price_change_detector.rb:58`만. `grep -rn "price_change\|PriceChange" app/models/assistant app/controllers --include=*.rb`에서 어시스턴트는 읽기 도구(`get_bill_audit.rb`, `get_bill_details.rb`)뿐. 범위 app .rb(`.erb`·`lib`는 안 봄). |
| R-48 | C-12 `recurring_transaction.rb:798-813`, `cleaner.rb:20-51`, `recurring_transactions_controller.rb:88-97`, `recurring_transaction.rb:765-788`, `:925-965` | "자동 실행 경로가 없다": `grep -rn "Cleaner\|cleanup_stale\|remove_old_inactive\|mark_inactive\|should_be_inactive" app lib config --include=*.rb --include=*.yml --include=*.erb`와 `grep -rn "remove_old_inactive\|cleanup_stale\|RecurringTransaction::Cleaner\|record_occurrence" lib config db/seeds* bin` 결과: 호출처는 `recurring_transactions_controller.rb:89`(cleanup)와 `:225`(toggle의 `mark_inactive!`)뿐이고 나머지는 번역 문자열이다. 놓칠 수 있는 것: 외부 스케줄러(레포 밖 cron), `send`로 조립한 호출. 모델 주석(`:32`)은 "auto-retired by the Cleaner"라고 쓰지만 호출은 수동뿐이다(문서와 구현이 다름, 구현을 사실로 썼다). |
| R-49 | `recurring_transaction.rb:352-379`, `:839-873`, `:887-914`, `cleaner.rb:43-51` | 위 R-48 검색 + `grep -rn "\.payable\b\|RecurringTransaction\.bills\|\.expected_soon\|projected_entry\|\.needs_action\|payable\b" app lib --include=*.rb --include=*.erb`에서 `bills_controller.rb`의 `payable_series_ids`·`payable_occurrences` 같은 이름만 나오고 model scope 호출은 없다. `record_occurrence!`은 테스트(`test/models/recurring_transaction_test.rb:214-228`, `:988-994`)에서만 호출된다(파일명·줄 검색만, 본문은 열지 않음). knob 쓰기 경로는 `grep -rn "amount_tolerance_pct\|match_days_early\|match_days_late\|notify_days_before\|overdue_grace_days\|amount_strategy\|weekend_adjust" app --include=*.rb --include=*.erb` 결과가 import·export·읽기 도구·모델뿐이다. 놓칠 수 있는 것: 열지 않은 어시스턴트 도구(`create_bill.rb`, `update_bill.rb`는 `weekend|notify|tolerance|strategy`를 grep해서 0건). |
| R-50 | `bills_controller.rb:477-502`, `recurring_transaction.rb:352-379` | 코드 확인. 컨트롤러의 `debt_accounts`는 가족 필터가 없지만(`:478`) series의 목적지가 같은 가족이어야 한다는 모델 검증(`:187-195`)으로 같은 결과다. 모델 scope `payable`과 컨트롤러의 정의는 `active` 대 `active+inactive`가 다르다(컨트롤러가 화면의 기준). |
| R-51 | `bills_controller.rb:21-112`, `:491-502`, `:536-556`, `:671-687` | 코드 확인. |
| R-52 | `bills_controller.rb:7-12`, `:300-400`, `:360-373`, `recurring_transaction.rb:404-407`, `:440-442` | 코드 확인. |
| R-53 | `bills_controller.rb:423-463` | 코드 확인. |
| R-54 | `bills_controller.rb:561-628`, `:632-637` | 코드 확인. |
| R-55 | `recurring_transaction.rb:385-389`, `:423-442`, `:457-471` | 코드 확인. T-ID 값은 Python 재계산(43,482.14). |
| R-56 | `transactions_controller.rb:84-101`, `:584-588` | 코드 확인. 렌더링은 열지 않았다. |
| R-57 | C-13 `paycheck_planner.rb:82-163`, `bills_controller.rb:21-35`, `:523-534` | 코드 확인. T-23 손계산. |
| R-58 | C-14 `paycheck_planner.rb:176-256` | 코드 확인. T-23 손계산. |
| R-59 | C-15 `paycheck_planner.rb:11-71`, `:94-113`, `:258-310`, `app/models/family.rb:601-619` | `tax_advantaged_account_ids`는 `tax_advantaged_depository_account_ids`를 호출자 계약으로 두고 읽지 않았다. |
| R-60 | `paycheck_planner.rb:126-139`, `bills_controller.rb:205-236`, `:241-260` | 코드 확인. |
| R-61 | `declared_bill.rb:17-168`, `recurring_transactions_controller.rb:102-177`, `recurring_transaction.rb:126-135` | 코드 확인. 통화 표의 최대 자릿수는 `Money::Currency.all`의 `default_precision` 최댓값이고 주석의 "crypto's eight"는 통화 표 파일을 열지 않았다. |
| R-62 | `recurring_transactions_controller.rb:191-221`, `:394-409`, `:454-543` | 코드 확인. |
| R-63 | `recurring_transactions_controller.rb:52-57`, `:240-263`, `recurring_transaction.rb:19-22` | 코드 확인. |
| R-64 | `recurring_transaction.rb:472-492`, `recurring_transactions_controller.rb:372-388`, `recurring_occurrences_controller.rb:71-77` | 코드 확인. |
| R-65 | `bills_feeds_controller.rb:11-75`, `app/models/family.rb:784-820`, `bills_controller.rb:135-140` | 코드 확인. 금액 서식은 money R-11. |
| T-01 | R-15 | `calculate_expected_day`를 Python으로 재현해 `[29,30,31,1,2]`(정렬 `[1,2,29,30,31]`) 등을 계산. |
| T-02~T-03 | R-14, R-16, R-18 | Python `Decimal`로 군집 재현, 손계산. |
| T-12~T-15 | R-39~R-45 | Python으로 점수식 재현. 반올림은 소수 4자리 half-up. |

### 2.2 코드 읽는 순서

1. 데이터 모델: `recurring_transaction.rb`(검증·상태·생성 경로), `recurring_occurrence.rb`, `recurrence_rule.rb`.
2. 일정: `schedule.rb`(엔진과 옛 단일 월 경로 차이), `frequency_preset.rb`, `occurrence_generator.rb`.
3. 식별: `identifier.rb`, `classifier.rb`, `pipeline.rb`와 두 job.
4. 매칭·정산: `matcher.rb`, `allocator.rb`, `price_change_detector.rb`.
5. 화면·계획: `bills_controller.rb`, `paycheck_planner.rb`, `recurring_transactions_controller.rb`.

원본 구현 전략: 파이프라인은 가족별 advisory lock으로 직렬화하고, 생성·백필은 `insert_all` unique 충돌 무시로 멱등성을 만든다. 점수 상수와 허용 오차는 코드 상수이고 series 컬럼은 대부분 기본값으로 고정돼 있다(R-49).

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 아직 없다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-03이 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-65 전부와 C-ID 표본, 점수식·날짜 계산(T-01, T-06~T-09, T-12~T-13, T-18) 재계산, 부재 주장 R-01·R-13·R-31·R-48·R-49 반증 시도. 중요 오류 5건(R-25·R-26 가드 범위, R-46·T-17, R-30·T-22, T-23, R-46 실패 처리), 사소 7건이 나왔다. 미결정 0개는 부당하다는 지적에 따라 U-01~U-03을 추가했다. 작성자가 전부 반영했다.
- **메인 표본 점검**: R-25(`bills_controller.rb:17`), R-30(`sync.rb:183-185`의 `Time.use_zone`), R-40·R-41(`matcher.rb:78,129-134`)을 원본에서 직접 확인했다. R-46의 뷰 경로는 작성자가 뷰를 다시 읽어 확정했다.
- **대조하지 못한 것**: ActiveJob이 enqueue 시점의 `Time.zone`을 복원하는지(U-01), `lock: :until_executed`(U-02), 한글 `` 경계(U-03), `MAX_END_AFTER_COUNT`, iCal feed 요청의 시간대, 캐시 키 세부.
- 재구현: 미수행.

## 적용 메모

원본 동작은 위 1부이고, 한국 사용을 위해 바꿀 점은 여기에만 둔다. 원본의 미결정을 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-07, R-49 | 월급일·카드 결제일에 `weekend_adjust`와 한국 공휴일(대체공휴일 포함) 달력을 쓸 수 있게 하고, 입력 경로(화면 또는 API)를 연다. 급여는 `before`(직전 영업일)를 기본으로 제안한다. | 원본은 토·일만 보정하고 공휴일은 모르며, 보정 값을 설정하는 경로가 없다(T-09). 한국 급여는 보통 직전 영업일 지급이다. | 일정 입력에 보정 선택과 휴일 목록 의존이 생긴다. T-09의 개천절 사례가 바뀐다. |
| R-18, R-19 | 한글 구독·청구 키워드(넷플릭스, 한국전력, 통신사 이름 등)와 가맹점 이름 정규화(유니코드 NFC, 전각/반각, `(주)`·승인번호 접미 제거)를 추가한다. | 원본은 영문 키워드와 공백·대소문자 정규화뿐이라 한국어 가맹점은 `bill`로 떨어지고, 결제마다 이름이 달라지면 식별 그룹이 갈라진다(T-04, T-05). | `normalize_name`과 식별 그룹 키가 같은 정규화를 쓰게 한다(원본은 그룹 키가 원문). T-05가 바뀐다. |
| R-18 | 150이라는 "소액 구독" 문턱을 통화별로 정한다. | 원본은 통화를 보지 않아 KRW에서는 사실상 항상 거짓이다(T-04). | 문턱 입력이 통화별 표가 된다. |
| R-39, R-43 | 금액 일치 판정의 0.01 오차를 통화 최소 단위(KRW는 1원)로 바꾸는 것을 검토한다. | KRW는 소수가 없어 0.01이 "정확히 같음"과 같다. | 점수·닫힘 경계 사례(T-12의 17,001원)가 바뀐다. |
| R-30 | 야간 cron job(R-24)과 rake도 Family 시간대로 "오늘"을 계산하고, sync 후 job(R-23)은 시간대를 명시적으로 설정한다(U-01을 닫기 전까지는 그렇게 가정하지 않는다). | 한국 가족은 UTC 날짜와 하루 어긋나는 시간대가 매일 9시간 있다(T-22). | job 진입에서 시간대 설정. T-22 (b)가 바뀐다. |
| R-09, R-56 | 말일 기대일(31)의 `next_expected_date`를 엔진과 같이 말일로 줄인다. | 원본의 두 경로가 다르다. 말일 급여가 6월을 건너뛴다(T-07). | 거래 목록 "예정"의 날짜가 바뀐다. |
| R-15, R-48 | 월 외 주기(분기·연·반월)와 카드 결제일 같은 이체 패턴의 자동 식별, 주기적인 stale 정리 job 추가를 검토한다. | 원본은 월 1회 패턴만 식별하고(R-15), `kind` 이체 4종을 읽지 않으며(T-19), stale 정리가 수동뿐이다(R-48). | 식별 입력과 스케줄러가 늘어난다. |
| R-46 | 기본 연결 금액이 잔액으로 잘려 가격 인상을 놓치는 점(T-17 (c))을 고친다. | 원본의 주석 의도와 동작이 다르다. | `allocate_matched!`의 금액 결정과 감지기의 입력이 바뀐다. T-17 (c)가 바뀐다. |
