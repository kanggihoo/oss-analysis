---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/budget.rb
  - app/models/budget_category.rb
  - app/models/budget/rollover_calculator.rb
  - app/models/budget_share.rb
  - app/models/family.rb
  - app/models/user.rb
  - app/models/account.rb
  - app/models/category.rb
  - app/models/category/merger.rb
  - app/models/assistant/function/update_budget.rb
  - app/controllers/concerns/preview_gateable.rb
  - app/models/transaction.rb
  - app/models/entry.rb
  - app/models/entryable.rb
  - app/models/income_statement.rb
  - app/models/income_statement/scoped_transactions_query.rb
  - app/models/income_statement/totals.rb
  - app/models/income_statement/family_stats.rb
  - app/models/income_statement/category_stats.rb
  - app/models/exchange_rate/provided.rb
  - app/controllers/budgets_controller.rb
  - app/controllers/budget_categories_controller.rb
  - app/controllers/concerns/budget_ownership.rb
  - app/controllers/settings/budget_shares_controller.rb
  - app/controllers/api/v1/budget_categories_controller.rb
  - app/helpers/budgets_helper.rb
  - app/views/budgets/show.html.erb
  - app/views/budgets/edit.html.erb
  - app/views/budgets/_budgeted_summary.html.erb
  - app/views/budget_categories/_budget_category_form.html.erb
  - app/views/budget_categories/_allocation_progress.erb
  - app/views/settings/preferences/show.html.erb
  - config/routes.rb
  - db/schema.rb
depends:
  - ./transactions.md
  - ./money-currency-rules.md
  - ./account-balances.md
status: draft
---

# 예산 (월별 예산, 카테고리 배정, 이월, 예산 공유)

> 가족(family)이 월 단위 기간(기본 1일 시작, 선택적으로 매월 N일 시작)마다 총 지출 한도·예상 소득·카테고리별 배정액을 정하면, 그 기간의 실제 지출·소득을 배정과 견주어 남은 금액·초과 여부를 계산하고, 카테고리별 잉여를 다음 달로 이월(rollover)하며, 개인 예산을 다른 가족 구성원에게 읽기 또는 읽기·쓰기로 공유하는 규칙을 정의한다.

이 문서에서 쓰는 이름은 다음과 같다. 예산(`Budget`)은 한 기간의 행 하나이고, 배정 행(`BudgetCategory`)은 예산 안에서 카테고리 하나에 붙는 행이다. 총 예산은 `Budget.budgeted_spending`, 배정액은 `BudgetCategory.budgeted_spending`, 이월액은 `BudgetCategory.rolled_over_amount`다. 예산 소유자는 `Budget.user_id`다. 이 값이 없으면 household 예산(가족 공용)이고, 있으면 그 사용자의 personal 예산이다. 체인(chain)은 같은 가족·같은 소유자의 예산을 시작일 순으로 이은 열이다. 하위 카테고리 중 배정액이 0인 것을 "공유 하위"(부모 예산을 같이 쓰는 하위 카테고리), 배정액이 0보다 큰 것을 "개별 한도 하위"라고 부른다. 코드는 앞의 것을 `inherits_parent_budget?`, 뒤의 것을 `reject(&:inherits_parent_budget?)`로 구분하고, 이 문서는 뒤의 것을 "ring-fenced 하위"라고도 쓴다(원본 주석 용어).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

월급일이 25일인 가족(`month_start_day = 25`, 통화 KRW)이 11월 예산을 처음 쓰는 대표 흐름이다. 기준은 1.4다.

1. 사용자가 예산 화면을 열면 `month_year` 파라미터(`nov-2026`)가 기간으로 바뀐다. 2026-11-25~2026-12-24다. 이 기간이 유효 범위 안이면 예산 행을 찾거나 만들고, 카테고리마다 배정 행을 맞추고(가족 카테고리 전체에 대해 배정 0인 행), 이월 체인을 다시 계산한다(R-01~R-07, R-27~R-29).
2. 예산이 아직 초기화되지 않았고(`budgeted_spending`이 비어 있음) 이전에 초기화된 예산이 있으면 "이전 달 복사" 제안이 나온다. 복사하면 총 예산·예상 소득·배정액·이월 toggle이 옮겨진다(R-09, R-10).
3. 사용자가 총 예산과 예상 소득을 입력하면(R-08) 예산이 초기화된다. 이어서 카테고리별 배정액을 입력한다. 하위 카테고리 배정은 부모의 배정액에 합산된다(R-11~R-13).
4. 화면은 그 기간의 지출·소득을 집계(IncomeStatement, 행 14 소관)에서 받아 총 남은 금액·배정 안 한 금액·카테고리별 남은 금액·"초과/주의/정상" 상태를 계산해 보여 준다(R-14~R-21).
5. 사용자가 카테고리 하나의 rollover를 켜면 그 카테고리가 이월을 시작한다. 다음 달로 `max(배정 + 들어온 이월 − 실제 지출, 0)`이 넘어간다(R-24~R-28).
6. 사용자는 한 카테고리의 배정액을 다른 카테고리로 옮길 수 있다(R-15).
7. personal 예산을 켠 가족은 구성원이 자기 예산을 다른 구성원에게 공유하고, 공유받은 사람은 읽기만 하거나 수정까지 한다(R-30~R-33).

### 1.2 범위·통합 지점

- 제공: 예산 기간 계산과 접근 가능 범위, 예산 행·배정 행의 자동 생성, 이전 달 복사, 총 예산·예상 소득 입력, 카테고리 배정과 부모-하위 합산, 배정 이동(move), 남은 금액·미배정 금액·초과 판정 계산, 예상 소득·지출 추정치 사용, 일일 권장 지출, rollover 이월 계산과 체인 재계산, 예산이 쓰는 통화 환산, household/personal 예산 선택, 예산 공유(`BudgetShare`)와 그 권한 판정.
- 제외:
  - 기간별 지출·소득 집계(`IncomeStatement`). 행 14 소관이다. 이 문서는 예산이 쓰는 입력·출력·제외 규칙(R-17)만 쓰고 SQL 구조·캐시 키·일별 시계열·`DailyExpenseTotals`·`invested_total`은 쓰지 않는다. 계약은 [reports-insights](./reports-insights.md) R-01~R-15에서 확정됐고 U-01은 닫혔다(카테고리 통계 창은 R-10·R-11, 보류 판정 `PENDING_PROVIDERS`는 R-01).
  - 목표(Goal)의 예약액(`earmarked_for_goals`)과 `free_cash`의 목표 차감(`Goal.backing_within`). 행 12 소관이고 preview 기능이다. 계약은 [goals](./goals.md) R-35에서 확정됐고(`goal.backing_within(ids, currency:)`는 인스턴스 메서드다) U-02는 닫혔다. 사용 지점만 R-23에 쓴다.
  - 정기 거래의 청구서 예약(`bills_reserved`, `RecurringOccurrence`). 행 13 소관이다. 사용 지점만 R-34에 쓴다(U-03).
  - `Family` 테넌시와 계정 접근(`AccountShare`, `accessible_by`, `included_in_finances_for`). 이 문서가 쓰는 판정은 "보는 사람이 접근할 수 있는 계정 집합"을 입력으로 받는다는 것뿐이다(U-04, 가정).
  - 예산을 읽는 다른 소비자: 인사이트 생성기(`budget_insight_generator`), AI 어시스턴트(`get_budget`·`update_budget`), API v1 `budgets`·`budget_categories`(routes `index`·`show`만, `config/routes.rb:840-841`), Plan 화면(`plans_controller`), 리포트. 이들이 이 문서의 계산 메서드를 부른다는 사실만 확인했고 본문은 읽지 않았다.
  - 화면 배치·도넛 차트 구간 색·i18n 문구·Stimulus. 상태 데이터의 의미는 1.3·1.4에 썼다(도넛은 R-21).
- 외부 의존·선행 계약: PostgreSQL(`pg_advisory_xact_lock`, `PERCENTILE_CONT`)과 `Rails.cache`(없어도 동작은 같고 재계산이 매번 실행될 뿐, R-29). 현재 사용자(`Current.user`)·가족(`Current.family`)과 접근 계정 판정은 호출자가 제공한다. 거래 `kind`·`excluded`·보류·예정 규칙은 [transactions](./transactions.md) R-16·R-18·R-71, 환산·소수 자릿수·부호는 [money-currency-rules](./money-currency-rules.md) R-10·R-26·R-36·R-41, 계정 `exclude_from_reports`·상태·잔액은 [account-balances](./account-balances.md) R-09·R-11·R-38이다.
- 소유 상태·부작용: `budgets`, `budget_categories`, `budget_shares` 행. 예산 화면을 여는 것만으로 `budgets` 행과 `budget_categories` 행이 생기고 `rolled_over_amount`가 갱신될 수 있다(읽기가 쓰기를 한다, R-06, R-29). `Family`의 `month_start_day`·`personal_budgets`·`household_budget_enabled`·`investment_contributions_as_spending`·`currency`를 읽는다. 쓰는 것은 이 문서가 소유한 세 테이블뿐이다.

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Budget` | 행 | `family_id`(필수), `user_id`(null이면 household), `start_date`·`end_date`(date, 필수), `currency`(필수, 생성 때 가족 통화로 고정), `budgeted_spending`(decimal(19,4), null이면 미초기화), `expected_income`(decimal(19,4), null 가능). 유일성: household는 `(family, start_date, end_date)`, personal은 `(family, start_date, end_date, user)`가 DB partial unique index로 유일하다. 모델 검증은 `start_date`·`end_date`를 각각 `(family_id, user_id)` 범위에서 유일하게 한다. 숫자 범위 검증은 없다(R-08). |
| `BudgetCategory` | 행 | `budget_id`·`category_id`·`currency`(필수), `budgeted_spending`(decimal(19,4) not null, 기본값 없음), `rollover_enabled`(기본 false), `rolled_over_amount`(decimal(19,4) not null, 기본 0, DB check `>= 0`). `(budget_id, category_id)` 유일. 가족의 카테고리마다 한 행이다(R-05). |
| 합성 "미분류" 배정 행 | 메모리 객체 | `category`가 없는 `BudgetCategory`. 저장되지 않고 읽을 때 만든다. id는 `uuid_v5(URL_NAMESPACE, "uncategorized")`로 고정이다. 배정액은 `max(available_to_allocate, 0)`이다(R-13). |
| `BudgetShare` | 행 | `owner_id`·`viewer_id`(둘 다 사용자, 필수), `permission`(`read_write`·`read_only`, 기본 `read_only`). `(owner, viewer)` 유일, 자기 자신에게 공유 불가, 둘이 같은 가족이어야 한다(R-31). |
| 가족 설정 | 필드 | `month_start_day`(int 1~28, 기본 1, DB check와 모델 검증 둘 다), `personal_budgets`(bool, 기본 false), `household_budget_enabled`(bool, 기본 true), `investment_contributions_as_spending`(bool, 기본 true), `currency`. |
| 카테고리 | 행 | 2단계까지만 허용(부모-하위). 합성 카테고리 둘(미분류, 기타 투자)은 행이 없고 집계 때만 나온다. 카테고리 스펙은 행 10 소관이다. |

**연산(웹 경로 기준)**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| 예산 열기 | `GET /budgets/:month_year`, `owner`(선택: `household` 또는 사용자 id) → 예산 | R-01~R-07, R-30 |
| 현재 월로 이동 | `GET /budgets` → 오늘(`Date.current`)이 속한 예산으로 redirect | R-02 |
| 총 예산·예상 소득 수정 | `PATCH /budgets/:month_year`, `budget[budgeted_spending]`, `budget[expected_income]` → 배정 화면으로 redirect | R-08 |
| 이전 달 복사 | `POST /budgets/:month_year/copy_previous` | R-09, R-10 |
| 배정·rollover 수정 | `PATCH /budgets/:month_year/budget_categories/:id`, `budget_category[budgeted_spending]`, `budget_category[rollover_enabled]` | R-11~R-13, R-24 |
| 배정 이동 | `POST /budgets/:month_year/budget_categories/move`, `from_id`, `to_id`, `budget_category_move[amount]` | R-15 |
| 카테고리 상세 | `GET /budgets/:month_year/budget_categories/:id` → 그 카테고리의 최근 거래 3건 | R-35 |
| 배정 목록 | `GET .../budget_categories` | 편집 가능 사용자만(R-32) |
| 월 선택기 | `GET /budgets/picker?year=` | 월별 유효 여부 표시(R-03) |
| 예산 공유 설정 | `PATCH /settings/budget_shares`, `budget_shares[members][]{viewer_id, permission}` | R-31 |

**월 파라미터**: 형식은 `%b-%Y`를 소문자로 쓴 것이다(`nov-2026`). 월 이름은 영어 3글자 약어다. 만드는 쪽(`to_param`)과 읽는 쪽(`param_to_date`)이 같은 형식이다.

### 1.4 행동 규칙과 남은 질문

**기간과 접근**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 날짜 `d`가 속한 예산 기간을 구한다(`period_for`). 가족의 `month_start_day`가 `S`다 | `S = 1`이면 `[d의 달 1일, d의 달 말일]`. `S ≠ 1`이면 시작일은 `d.day >= S`일 때 `d`의 달의 `S`일, 아니면 `d`의 직전 달(`d − 1개월`)의 `S`일이다. 종료일은 시작일 + 1개월 − 1일이다. 종료일이 속한 날까지 포함한다(`start..end`). 기간 이름과 파라미터는 시작일의 달을 따른다. `S`는 1~28이라 모든 달에 있다. | 코드 확인 |
| R-02 | 월 파라미터 `p`를 날짜로 바꾼다(`param_to_date`) 그리고 "현재 월" 진입(`index`) | `p`를 `%b-%Y`로 읽어 `S = 1`이면 그 달 1일, 아니면 그 달의 `S`일 날짜를 만든다(그 날짜가 속한 기간의 시작일이다). 형식이 틀린 `p`는 `Date::Error`가 나고 컨트롤러는 이 오류를 처리하지 않는다(응답은 프레임워크 기본으로 500일 것이다, 추론). `index`는 `Date.current`(서버 시간대)가 속한 예산으로 redirect한다. 가족의 `timezone`을 쓰는 `local_date`는 쓰지 않는다. | 코드 확인 / 추론(500) |
| R-03 | 예산 접근 유효 범위(`budget_date_valid?`). 입력 날짜 `d`의 기간 시작일을 `b`라 한다 | `b >= 하한`이고 `b <= 상한`일 때만 유효하다. 하한 = `min(오늘 기준 2년 전 달의 1일, 가족의 가장 이른 entry 날짜의 달 1일)`. entry가 하나도 없으면 가장 이른 날짜는 오늘이다(`oldest_entry_date`는 거래·매매·평가 등 모든 종류의 entry를 센다). 상한 = `S = 1`이면 `오늘의 달 1일 + 2년`, `S ≠ 1`이면 `오늘이 속한 기간의 시작일 + 2년`이다. 하한·상한과 `b`의 비교는 날짜 단위이고 포함이다. 유효하지 않은 날짜는 예산을 만들지 않고 `find_or_bootstrap`이 nil을 돌려주며 컨트롤러는 404(RecordNotFound)로 간다. 하한은 달의 1일 기준이라, `S ≠ 1`이면 `S`일에 시작하는 기간은 같은 달 1일보다 늦어 하한을 넘긴다(T-03). | 코드 확인 |
| R-04 | 이전·다음 달 파라미터(`previous_budget_param`, `next_budget_param`) | `start_date ∓ 1개월`을 R-03으로 검사해 유효하면 그 날짜의 파라미터를, 아니면 nil을 돌려준다(nil이면 이동 링크가 없다). | 코드 확인 |
| R-05 | 현재 기간 판정과 남은 일수(`current?`, `days_remaining`) | `current?`는 `start_date`·`end_date`가 오늘(`Date.current`)이 속한 기간(R-01)과 둘 다 같을 때 true다. `days_remaining = max(end_date − 오늘 + 1, 0)`이라 종료일 당일은 1이고 기간이 끝나면 0이다. 지난 기간·미래 기간도 값은 계산되지만 일일 권장액(R-20)은 현재 기간에서만 쓴다. | 코드 확인 |

**생성·초기화·복사**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 예산 찾기·만들기(`find_or_bootstrap(family, start_date, user, household)`) | 한 DB 트랜잭션 안에서 순서대로 한다. (1) R-03이 유효하지 않으면 nil. (2) `household`가 true이고 가족의 `personal_budgets`가 true이고 `household_budget_enabled`가 false면 nil(공용 예산을 껐다). (3) 소유자는 `household`가 true이거나 `personal_budgets`가 false면 없음(household), 아니면 `user`다. (4) `(family, 기간 시작·종료, 소유자)`로 찾고 없으면 `currency = family.currency`로 만든다(`budgeted_spending`은 비어 있다). (5) 그 예산의 `current_user`를 요청 사용자로 두고 `sync_budget_categories`(R-07)를 한다. (6) `RolloverCalculator`로 그 소유자 체인을 재계산한다(R-27). 결과로 예산 화면을 열기만 해도 행이 생긴다. | 코드 확인 |
| R-07 | 배정 행 동기화(`sync_budget_categories`) | 가족의 모든 카테고리(부모·하위 구분 없이) 중 배정 행이 없는 것마다 `budgeted_spending = 0`, `currency = 가족 통화`로 행을 만들고, 가족 카테고리에 없는(삭제된) 카테고리의 배정 행은 지운다. 새 행의 `rollover_enabled`는 같은 소유자의 "가장 최근에 초기화된 이전 예산"(`start_date`가 이 예산보다 앞이고 `budgeted_spending`이 null이 아닌 것 중 가장 늦은 것)에서 그 카테고리가 `rollover_enabled = true`였을 때만 true로 물려받고, 아니면 false다. 이미 있는 행의 toggle은 바꾸지 않는다. 이 동기화는 `find_or_bootstrap` 때만 일어난다(카테고리 생성 시점에는 일어나지 않는다). 카테고리를 지우거나 병합하는 쓰기 경로는 R-38이다. | 코드 확인 |
| R-08 | 총 예산·예상 소득 수정(`budgets#update`) | `budget[budgeted_spending]`·`budget[expected_income]`만 허용한다. 권한이 없으면 404(R-32). 값은 검증 없이 저장한다. 음수·0도 저장되고(0이면 초기화로 친다, `0.present?`는 true), 빈 문자열은 null이 되어 예산이 미초기화로 남는다. 숫자가 아닌 문자열은 0으로 저장된다(프레임워크의 decimal 캐스트, 추론). 저장 뒤 배정 화면으로 redirect한다. 이 경로는 체인 재계산을 하지 않는다. 다음 화면 로드의 `find_or_bootstrap`이 한다(R-29). 초기화 판정(`initialized?`)은 `budgeted_spending`이 null이 아닌 것이다. | 코드 확인 / 추론(캐스트) |
| R-09 | 이전 달 복사 요청(`copy_previous`) | 권한이 없으면 404. 이미 초기화된 예산이면 alert만 남기고 복사하지 않는다. 아니면 `most_recent_initialized_budget`(같은 소유자, 이전, 초기화됨 중 가장 늦은 것)을 원본으로 삼고, 없으면 alert("원본 없음")이다. 있으면 R-10을 하고 배정 화면으로 간다. | 코드 확인 |
| R-10 | `copy_from!(source)` | 원본이 같은 가족·같은 소유자이고 `start_date`가 앞서야 한다(아니면 `ArgumentError`, 컨트롤러 경로에서는 원본 선택 규칙 때문에 발생하지 않는다). 한 트랜잭션에서: 이 예산의 `budgeted_spending`·`expected_income`을 원본 값으로 바꾸고, 이 예산에 있는 카테고리마다 원본의 `budgeted_spending`·`rollover_enabled`를 복사한다(원본에만 있는 카테고리는 건너뛴다). `rolled_over_amount`는 복사하지 않는다(체인 계산만 쓴다). 마지막에 체인을 재계산한다. 복사로 하위 카테고리의 배정이 복사되므로 부모-하위 합 제약(R-12)은 원본 값에 맡긴다(복사 중 재계산 없음). | 코드 확인 |

**배정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | 배정 수정 요청(`budget_categories#update`) | 권한이 없으면 404, 배정 행은 이 예산의 것만 찾는다(합성 미분류 id는 404). 순서대로: (1) `rollover_enabled`가 요청에 있으면 불리언으로 캐스트해 저장하고 앞으로 전파한다(R-24). (2) `budgeted_spending`을 `update_budgeted_spending!`로 저장한다. 값이 요청에 없거나 빈 문자열이면 0으로 저장한다(toggle만 보낸 요청도 배정을 0으로 만든다. 화면의 폼은 두 필드를 항상 함께 보낸다). (3) 체인을 재계산한다(R-27). (4) 응답: turbo_stream 또는 html redirect. 저장 검증 오류(`RecordInvalid`)는 422로 배정 목록을 다시 보여 준다. 음수 금액을 서버는 막지 않는다(입력 요소의 `min=0`은 UI 제약이다). 숫자 단위는 통화 자릿수로 반올림하지 않고 decimal(19,4)로 저장한다. | 코드 확인 |
| R-12 | 부모-자식 배정 합 규칙(`update_budgeted_spending!`) | 한 행을 잠그고(`lock!`) 값을 바꾼다. 바뀐 행이 하위 카테고리면 부모 배정 행을 잠그고 다시 계산한다. 이전 값 `p`, 새 값 `n`, 같은 부모의 다른 하위 배정 합 `s`, 부모 현재 배정 `P`에 대해 `reserve = max(P − s − p, 0)`, 새 부모 배정 = `s + n + reserve`. 즉 부모의 배정은 "하위들의 합 + 부모 몫(reserve)"이고 reserve는 보존되며 음수 reserve는 0으로 올라간다. 부모를 직접 수정하면 하위와의 합을 맞추지 않고 값을 그대로 저장한다(부모를 하위 합보다 작게 두는 것을 서버가 막지 않는다). 그 상태에서 하위 하나를 수정하면 reserve가 0이 되어 부모는 하위 합으로 다시 올라간다(T-07). 이 재계산은 부모가 이 예산에 있을 때만 한다(없으면 건너뛴다). 부모는 2단계 제한 때문에 하위의 하위를 갖지 않는다. | 코드 확인 |
| R-13 | 총 예산 대비 배정 계산 | `allocated_spending` = 하위가 아닌(부모) 배정 행의 `budgeted_spending` 합(하위의 배정은 이미 부모에 들어 있어 따로 더하지 않는다). `available_to_allocate = (총 예산 ?? 0) − allocated_spending`(미배정 금액, 음수면 초과 배정). `allocated_percent = allocated_spending / 총 예산 × 100`이고 총 예산이 없거나 0 이하면 0이다. `allocations_valid? = 초기화됨 && available_to_allocate >= 0 && allocated_spending > 0`(도넛이 회색 단색이 되는 조건의 반대). 합성 미분류 행의 배정액은 `max(available_to_allocate, 0)`이다(미배정 금액이 미분류의 예산이다). 배정 행의 통화는 가족 통화로 둔다. 화면: 초기화됐고 `available_to_allocate`가 음수면 도넛 대신 과배정 경고를, 양수일 때만 "예산/실적" 탭을 보여 준다(`budgets/show.html.erb:15-46`). | 코드 확인 |
| R-14 | 공유 하위 판정과 표시 배정(`inherits_parent_budget?`, `display_budgeted_spending`) | 하위 카테고리이고 배정액이 null 또는 0이면 공유 하위다(부모 예산을 같이 쓴다). 공유 하위의 표시 배정은 부모의 배정액이고(부모가 이 예산에 없으면 0), 그 밖은 자기 배정액이다. `BudgetCategory#subcategory?`는 `category.parent_id.present?`만 본다(부모 행이 실제로 있는지는 보지 않는다). 부모 행이 없는 orphan 하위(`parent_id`는 있는데 부모 카테고리가 없음)는 배정 쪽에서는 하위로 취급되지만(부모 배정 행을 못 찾아 `parent_budget_category`가 nil이면 공유 하위의 남은 금액·사용률이 0), IncomeStatement가 쓰는 `Category#subcategory?`(`parent_id.present? && parent.present?`)에서는 최상위로 집계된다. 두 판정이 갈리는 경우의 합계는 확인하지 않았다. | 코드 확인 |
| R-15 | 배정 이동(`move_allocation!(from, to, amount)`) | `amount = amount.to_d`(빈 값·숫자 아님은 0). 아래 검증을 순서대로 하고 첫 실패의 이유 코드를 돌려준다(`InvalidMove`, 컨트롤러는 422로 alert): `non_positive_amount`(amount <= 0), `uncategorized`(어느 쪽이든 카테고리가 없거나 저장 안 된 행), `different_budgets`, `same_category`, `parent_child`(한 쪽이 다른 쪽의 직계 부모-자식), `insufficient_funds`(amount가 이동 가능액보다 큼). 이동 가능액: 하위는 자기 배정 전부, 부모는 `max(자기 배정 − ring-fenced 하위들의 배정 합, 0)`이다. 통과하면 한 트랜잭션에서 관련 행(from, to, 각자의 부모)을 id 오름차순으로 잠그고, 잠금 안에서 다시 읽어 이동 가능액을 한 번 더 검사하고, `from`에서 amount를 빼고 `to`에 더한다(각각 R-12의 부모 재계산을 탄다). 이동 기록은 남기지 않는다. `move_allocation!`의 이유 코드는 모델을 직접 부를 때만 모두 나온다. 컨트롤러는 먼저 `@budget.budget_categories.find`로 두 행을 찾아 합성 미분류 id와 다른 예산의 행은 404(RecordNotFound)로 끝나서 `uncategorized`·`different_budgets` 이유 코드에 도달하지 않는다. 컨트롤러는 이동이 커밋된 뒤 체인을 한 번 재계산한다(재계산을 트랜잭션 안에서 하지 않는다. 락 순서 역전으로 인한 교착을 피한다는 것이 코드 주석이다). 권한이 없으면 404. 같은 부모의 두 하위 사이 이동은 부모 합이 변하지 않는다(T-17). | 코드 확인 |

**실적·상태 계산**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | 예산이 쓰는 계정 범위 | 실적은 예산 종류에 따라 다른 계정 집합으로 집계한다. personal 예산: 소유자가 `owner`인 계정 중 `exclude_from_reports = false`인 것만(보는 사람과 무관하다. 공유받은 사람은 소유자의 숫자를 본다). household 예산: 요청 사용자가 접근할 수 있는 금융 대상 계정(`user.finance_accounts` = 자기 소유 또는 `include_in_finances`로 공유받은 계정, U-04). 즉 household 예산의 실적과 지출 합은 보는 사람마다 다를 수 있다. 다른 사람의 기존 personal 예산을 볼 때는 `current_user`가 없고 소유자 계정으로 계산한다. 단, 이월 체인의 household 계산은 사용자와 무관하게 `가족의 모든 exclude_from_reports=false 계정`을 쓴다(R-26). | 코드 확인 |
| R-17 | 예산이 IncomeStatement에서 받는 계약(기간 `start..end` 포함, 계정 집합, 가족 통화 기준) | 입력은 예산 기간(포함 구간)과 R-16의 계정 집합이다. 출력은 가족 통화 금액이고, 거래별로 `entry.date` 날짜의 환율(저장된 환율 중 그 날 이하 가장 최근, 없으면 이후 가장 이른 것, money-currency-rules R-26)로 곱하고, 환율이 전혀 없는 외화 금액은 합에서 빠진다(1로 대신하지 않는다). 포함 거래: 계정 상태가 draft·active, `exclude_from_reports = false`, 세금 우대 계정(tax-advantaged)이 아님, 보류(pending)가 아님, 날짜가 오늘 이하(예정 거래 제외, transactions R-71), `entry.excluded = false`(분할 원본 포함 제외, transactions R-16·R-23), 거래 `kind`가 `funds_movement`·`one_time`·`cc_payment`가 아님, 투자 활동 라벨이 Transfer·Sweep In·Sweep Out·Exchange가 아님. 매매(Trade)는 전부 제외한다. 분류: `kind`가 `loan_payment`면 지출(절댓값), `kind`가 `investment_contribution`이면 가족의 `investment_contributions_as_spending`가 true일 때 지출(절댓값), false면 별도 "투자"로 빠져 지출·소득 어디에도 안 들어간다. 그 밖은 `amount < 0`이면 소득, 아니면 지출이다. 출력 모양: 지출 합·소득 합·카테고리별 합(부모의 합은 하위의 합을 포함, 합성 "미분류" 포함. 합성 "기타 투자"는 구조상 항목일 뿐 `is_uncategorized_investment`가 상수 `false`라 합이 항상 0이다, reports-insights R-05)과, 카테고리별로 `지출 − 소득`이 양수면 순지출·음수면 순소득으로 나눈 순집계(R-18). 카테고리 그룹 키는 거래의 `category_id`다. 이 규칙의 내부 구현(쿼리, 캐시)은 행 14 소관이다(해소: [reports-insights](./reports-insights.md) R-01·R-10·R-11). | 코드 확인 |
| R-18 | 실적 지출 계산 | 총 실적 `actual_spending` = 순집계의 총 순지출 = 부모(하위가 아닌) 카테고리별 `지출 − 소득`이 양수인 것들의 합이다. 소득이 지출보다 큰 카테고리는 총 실적을 줄이지 않는다(0으로 센다). 카테고리 하나의 실적(`budget_category_actual_spending`) = `max(그 카테고리의 지출 합 − 소득 합, 0)`이고 부모의 값은 하위를 포함한다. 합성 미분류(`category_id` 없음)와 기타 투자는 고정 키로 찾는다. 환불·반품이 같은 카테고리에서 지출을 상쇄하는 것이 이 계산의 의미다. `available_to_spend = (총 예산 ?? 0) − actual_spending`(음수면 초과). `percent_of_budget_spent = actual_spending / 총 예산 × 100`이고 총 예산이 0 이하면 0이다(100을 넘을 수 있고 자르지 않는다. 미초기화 예산에서 부르면 nil 비교 오류이므로 호출자는 `initialized?`일 때만 부른다). `overage_percent = |available_to_spend| / actual_spending × 100`이고 초과가 아니면 0이다(예: 한도 1,000,000에 1,250,000 지출 → 20). "기타 투자"는 합이 항상 0이라(reports-insights R-05) 총 실적에 0이 더해지고, 배정 행이 없어 카테고리 목록에도 나타나지 않는다. | 코드 확인 |
| R-19 | 카테고리별 남은 금액(`available_to_spend`)과 사용률(`percent_of_budget_spent`) | 세 경우로 나뉜다. (a) 공유 하위: `shared_budget = 부모 배정 + 부모 이월 − ring-fenced 하위들의 배정 합`, `shared_spending = 부모 실적 − ring-fenced 하위들의 실적 합`, 남은 금액 = `max(shared_budget − shared_spending, 0)`(음수가 되지 않는다). 사용률 = `자기 실적 / max(shared_budget, 0) × 100`이고 분모와 실적이 모두 0이면 0, 분모 0에 실적 양수면 100이다. 부모가 없으면 남은 금액·사용률 0. (b) 개별 한도 하위: `배정 + 자기 이월 − 자기 실적`. (c) 부모: `배정 + 자기 이월 + ring-fenced 하위들의 이월 합 − 부모 실적(하위 포함)`이다(하위 배정은 이미 부모 배정에 들어 있어 이월만 더한다). (b)(c)의 사용률 분모는 `배정 + 이월(+ 부모면 하위 이월)`이고, 분모 0·실적 0이면 0, 분모 양수·실적 0이면 0, 분모 0·실적 양수면 100, 둘 다 양수면 `실적 / 분모 × 100`이다. 분모가 음수인 경우 사용률은 nil이다(서버가 음수 배정을 막지 않아 가능하다, 이 경로는 확인하지 않았다). | 코드 확인 |
| R-20 | 카테고리 상태와 임계값 | `over_budget? = available_to_spend < 0`(정확히 0은 초과가 아니다). `budgeted? = (표시 배정 + 표시 이월) > 0`(이월만으로 돈이 있는 카테고리도 예산이 있는 것으로 센다). 표시 이월: 공유 하위는 부모의 이월, 개별 한도 하위는 자기 이월, 부모는 자기 이월 + ring-fenced 하위들의 이월 합이다. `unbudgeted_with_spending? = !budgeted? && 실적 > 0`, `over_budget_with_budget? = budgeted? && over_budget?`, `on_track? = budgeted? && !over_budget?`, `any_over_budget? = unbudgeted_with_spending? || over_budget_with_budget?`. `near_limit? = !over_budget? && 사용률 >= 90`(90 포함). 진행 막대 폭 = `min(사용률, 100)`이고 색은 초과 → 위험, 주의(near_limit) → 경고, 그 밖 → 정상이다. 목록에서 "정상"으로 보이는 조건(`visible_on_track?`)은 `on_track?`이고, 공유 하위는 실적이 0보다 클 때만 보인다. 일일 권장액(`suggested_daily_spending`): 남은 금액이 양수이고, 예산이 현재 기간이고, `days_remaining > 0`일 때만 `{amount: 남은 금액 / days_remaining(반올림 없음, 가족 통화), days_remaining}`을 돌려주고 아니면 nil이다. 상위 카테고리 요약(`top_spending_categories(limit = 4)`): 부모 배정 행 중 실적 0이고 배정 0인 행을 빼고 `(실적 내림차순, 배정 내림차순)`으로 상위 4개다. | 코드 확인 |
| R-21 | 소득 계산 | `actual_income` = 예산 기간의 소득 합(IncomeStatement 소득 총계, R-17, 환불 거래도 소득 분류면 포함되어 R-18의 환불 상쇄와 별개로 센다). `remaining_expected_income = (expected_income ?? 0) − actual_income`(음수면 예상보다 번 것). `actual_income_percent = actual_income / expected_income × 100`이고 `expected_income`이 없거나 0 이하면 0이다. `surplus_percent`는 `remaining_expected_income`이 음수가 아니면 0, 음수이고 `expected_income`이 없거나 0 이하면 100, 아니면 `|remaining| / expected_income × 100`이다. 예상 지출·소득 추정(`estimated_spending`, `estimated_income`)은 총 예산·예상 소득 입력 화면의 자동 채움 값이다(제안 조건은 `estimated_income && estimated_spending`인데 두 값이 모두 통계가 없으면 `|| 0`의 0이라 사실상 항상 제안이 나오고 제안 값이 0일 수 있다). 값은 지출/소득 각각의 "달별 합계의 중앙값"이다. 달은 항상 달력 달(`date_trunc('month')`)이라 `month_start_day`를 따르지 않고, 기간은 예산 기간이 아니라 이력 전체(오늘까지, 아직 끝나지 않은 이번 달 포함)다. 합계가 없는 달은 중앙값에서 빠지고, 통계가 하나도 없으면 0이다. 집계 대상 계정은 R-16의 `income_statement` 설정을 따르고, 이 통계는 R-17과 조건이 다르다. 계정 `status` 조건이 없고, 투자 활동 라벨(Transfer·Sweep·Exchange) 제외가 없고, 보류 판정은 `Transaction.pending_providers_sql`(`PENDING_PROVIDERS` 목록 기반)이고, 예정 거래 제외는 `ae.date <= 오늘`이다(`family_stats.rb:46-53`). 카테고리별 `median_monthly_expense`·`avg_monthly_expense`는 배정 화면에 참고로 보이는 값이고, 카테고리의 달별 합계에 대한 중앙값·평균이다(계산 창의 세부는 U-01). | 코드 확인 |

**이월(rollover)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 이월 toggle의 의미 | `rollover_enabled`는 카테고리(봉투) 단위의 지속 선택이다. 켜면 그 카테고리의 잉여가 다음 달로 간다. 끄면 이번 달에 들어오는 이월(incoming)도 0이 되고 이번 달에서 나가는 이월(outgoing)도 0이 된다(끈 달이 앞 달의 잉여를 다음 켠 달로 넘기지 않는다). 사용자가 꺼도 앞 달에서 이미 저장된 `rolled_over_amount`는 다음 재계산에서 0으로 지워진다(R-27). | 코드 확인 |
| R-23 | 이월액의 읽기(`rolled_over_amount`, `rolled_over?`, `total_rolled_over`) | `rolled_over_amount`(읽기)는 toggle이 꺼졌거나 공유 하위면 저장값과 무관하게 0이고, 아니면 저장값(없으면 0)이다. 저장값은 체인 계산이 쓴 값이며 읽을 때 다시 계산하지 않는다. `rolled_over?`는 표시 이월이 0보다 큰 것이다. 예산의 `total_rolled_over`는 공유 하위가 아닌 모든 배정 행의 읽기 이월 합이다(부모의 이월은 하위분을 빼고 센 값이라 한 금액이 두 번 세어지지 않는다). 이 값은 배정·남은 금액 계산(R-13)에 들어가지 않는 참고 합계이고 `allocated_spending`·`available_to_allocate`는 이월을 더하지 않는다. 남은 금액·사용률에는 이월이 들어간다(R-19). | 코드 확인 |
| R-24 | 이월 선택 전파(`propagate_rollover_choice_forward!`) | rollover toggle을 저장한 뒤, 같은 가족·같은 소유자·같은 카테고리의 이후 예산(`start_date`가 더 늦은 것) 배정 행 중 값이 다른 것을 모두 새 값으로 바꾼다(`update_all`, 검증 없음). 이전 달은 바꾸지 않는다. 이유: 이전 달에 먼저 만든 뒤 선택을 바꾼 경우에도 체인이 끊기지 않게 한다는 것이 코드 주석이다. 다음 달이 새로 만들어질 때는 R-07의 상속이 쓰인다. | 코드 확인 |
| R-25 | 이월 계산에 참여하는 예산(`initialized_budgets`) | 같은 가족·같은 소유자(household는 `user_id` null) 예산 중 `budgeted_spending`이 null이 아닌 것만이다. 초기화하지 않은 달은 "0으로 예산을 짠 달"이 아니라 체인의 빈 칸이어서, 이월액은 그 달을 건드리지 않고 건너뛴다(T-13). | 코드 확인 |
| R-26 | 체인 계산이 쓰는 실적 범위 | 체인 안의 각 예산은 R-17의 같은 실적 계산을 쓰되, household 체인은 가족의 모든 `exclude_from_reports = false` 계정(`household_account_scope`)으로 고정하고(저장되는 이월 행이 가족 공용 한 행이라 누가 화면을 열었는지에 따라 값이 달라지면 안 되기 때문이라는 것이 코드 주석), personal 체인은 소유자의 계정(R-16)이다. 따라서 household 예산 화면의 실적(보는 사람의 접근 계정)과 그 달의 이월 계산에 쓰인 실적(가족 전체 계정)은 다를 수 있다. | 코드 확인 |
| R-27 | 체인 재계산(`RolloverCalculator#recompute!`) | (1) 시작 달 `from` = 이 체인에서 `rollover_enabled`가 true이거나 `rolled_over_amount ≠ 0`인 배정 행을 가진 초기화 예산 중 가장 이른 `start_date`. 없으면 아무것도 하지 않는다(rollover를 쓰지 않는 가족은 쿼리 한 번이다). (2) 계산 범위는 `from`보다 앞선 가장 늦은 초기화 예산(seed, 있으면)부터 마지막 초기화 예산까지를 시작일 순으로 한다. (3) 달을 순서대로 지나며 `carry`(카테고리 id → [금액, 통화])를 이어 간다. 달마다 공유 하위가 아닌 각 배정 행에 대해 `incoming = rollover_enabled ? carry[카테고리]의 금액 : 0`(carry에 없거나, carry의 통화가 이 배정 행의 통화와 다르면 0), 저장된 `rolled_over_amount ≠ incoming`이면 `incoming`으로 쓰도록 모은다. `outgoing = rollover_enabled ? leftover(R-28) : 0`을 다음 달 carry에 넣는다. 공유 하위는 건너뛴다(carry에서 빠지고 저장된 이월액은 그대로 둔다. 읽을 때 0이다, R-23). 이 달에 없는 카테고리(삭제됨)는 carry에서 자연히 사라진다. 이번 달 carry는 다음 초기화된 달에만 적용되고, 달 사이에 건너뛴 미초기화 달은 영향이 없다. (4) 모은 변경은 `(id)` 기준 upsert로 쓰되 `rolled_over_amount`와 `updated_at` 두 컬럼만 덮어쓴다(동시 요청이 바꾼 배정액을 되돌리지 않기 위해서다). 이월은 기간이 끝났는지 보지 않는다. 이번 달이 진행 중이어도 그 시점까지의 실적으로 남은 금액을 계산해 다음 초기화 예산에 넘긴다(T-16). | 코드 확인 |
| R-28 | 잉여 계산(`leftover_for`) | `leftover = max(배정 + incoming − 실적, 0)`. 부모 행은 ring-fenced 하위마다 배정을 `budgeted`에서, 하위의 실적을 `actual`에서 뺀 뒤 계산한다(하위가 자기 잉여를 따로 넘기므로 같은 돈을 두 번 넘기지 않기 위해서다). 하위의 `incoming`은 부모 계산에서 빼지 않는다(부모의 `incoming`은 부모 자신의 이월만이다). 적자(음수)는 이월하지 않고 그 달에서 끝난다. 실적은 R-18의 카테고리 실적이다. | 코드 확인 |
| R-29 | 체인 재계산의 호출 시점·동시성·캐시 | 호출처는 R-06(예산 화면을 열 때마다), R-10(복사), R-11(배정·toggle 수정), R-15(이동 커밋 뒤), 그리고 API v1 `budget_categories` 읽기 경로다(행 17 소관, 호출 구조만 확인). 거래가 바뀔 때와 R-38의 쓰기 경로에서는 호출하지 않는다. 그 대신 다음 예산 화면 로드가 재계산한다. 따라서 저장된 이월액은 마지막 재계산 시점 기준이다. 체인(`family, user`)별로 `pg_advisory_xact_lock`을 잡아 두 재계산이 겹치지 않게 하고, 락을 잡은 뒤 입력을 다시 읽는다. 최적화: 입력 지문(예산·배정 행 다이제스트, 계정 상태·소유·`exclude_from_reports`, `AccountShare` 필드, 세금 우대 계정 id, 가족 entry 캐시 버전, 환율 최신 갱신 시각, 가족 `updated_at`)이 캐시에 저장된 값과 같으면 재계산을 건너뛰고, 쓴 것이 없었던 패스에서만 지문을 저장한다. 캐시는 정확성이 아니라 속도를 위한 것이다(재구현은 매번 계산해도 같은 결과다, 추론). | 코드 확인 / 추론(캐시 생략) |
| R-30 | 통화가 다른 달 사이의 이월 | 예산의 `currency`는 만들 때 가족 통화로 고정된다. 체인에서 carry를 넘길 때 앞 달 배정 행의 통화와 이번 달 배정 행의 통화가 다르면 이월을 0으로 시작한다(숫자를 다른 단위로 읽는 것을 막는다). 가족이 통화를 바꾸면 이전 예산은 옛 통화로 남는다. 실적(R-17)은 항상 현재 가족 통화로 계산되고 예산 금액 필드는 저장된 숫자 그대로라서, 통화를 바꾼 뒤 옛 예산을 열면 두 숫자의 단위가 다르다. 서버는 이를 변환하지 않는다(코드에서 변환 지점을 찾지 못했다, 2.1). | 코드 확인 |

**통화·현금**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | 사용 가능 현금(`available_cash`, `free_cash`, `missing_cash_currencies`) | 예산 옆의 참고 지표이고 배정·남은 금액 계산에 들어가지 않는다(원본 주석). 이 패널은 보는 사람 본인이 preview 기능을 켰을 때만 보인다(`PreviewGateable#preview_features_enabled?` = `Current.user&.preview_features_enabled? == true`, `app/controllers/concerns/preview_gateable.rb:8-10`, `app/views/budgets/show.html.erb:52`). 가족 단위 `Family#preview_features_enabled?`는 이 화면에서 쓰지 않는다. 현금 계정 = 가족의 `visible`(draft·active) 계정 중 `exclude_from_reports = false`이고 종류가 `Depository`인 것(투자 계정의 현금은 제외). personal 예산은 소유자의 계정만, household는 요청 사용자가 접근하는 계정만이다. `available_cash = Σ 계정 balance를 예산 통화로 환산한 값`이다. 환산: 계정 통화가 같거나 금액이 0이면 그대로, 아니면 오늘 날짜의 `find_or_fetch_rate(계정 통화 → 예산 통화)`(provider 호출 포함, money-currency-rules R-25)를 곱한다. 환율이 없거나 0 이하면 그 계정은 0으로 세고 그 통화 코드를 `missing_cash_currencies`에 모은다(1:1로 대신하지 않는다). `free_cash = max(available_cash − earmarked_for_goals, 0)`이다. `earmarked_for_goals`는 목표가 현금 계정에서 차지한 금액의 환산 합이고 목표 스펙 소관이다(해소: [goals](./goals.md) R-35). | 코드 확인 |

**공유·권한**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | 예산 조회·수정 권한(`viewable_by?`, `editable_by?`) | household 예산(`user_id` 없음)은 모든 가족 구성원이 보고 수정한다. personal 예산은 소유자가 보고 수정한다. 소유자가 아닌 사용자는 `(owner, viewer)` `BudgetShare`가 있으면 볼 수 있고, `permission = read_write`일 때만 수정할 수 있다. 수정 동작(배정 목록, `edit`, `update`, `copy_previous`, 배정 수정, 이동)은 `editable_by?`가 false면 404다. `show`·`picker`·카테고리 상세는 수정 권한을 검사하지 않고, 어떤 예산을 볼지는 R-33의 resolve가 정한다(`viewable_by?`는 컨트롤러에서 호출되지 않는다, 2.1). 화면은 `show`에서 `@editable`로 편집 버튼 표시를 정한다. | 코드 확인 |
| R-33 | 요청의 대상 예산 결정(`BudgetOwnership#resolve_budget`) | 대상 사용자는 `owner`가 없거나 `household`면 현재 사용자, 아니면 `owner` id의 가족 구성원이 현재 사용자가 아니고 그에게서 현재 사용자에게 온 `BudgetShare`가 있을 때만 그 사용자이고, 그 밖(없는 id, 공유 없음, 다른 가족)은 조용히 현재 사용자로 되돌린다(오류 없음). 대상이 현재 사용자가 아니면: 그 기간의 그 사용자 기존 예산을 찾아 그대로 돌려준다(없을 때 생성하지 않고, 배정 동기화·체인 재계산도 하지 않는다). 없으면 현재 사용자의 본인 예산을 만들어 돌려준다(막다른 길을 피함). 대상이 현재 사용자(또는 household)면 `find_or_bootstrap`(R-06)을 부른다. household를 명시했는데 가족이 공용 예산을 껐으면(R-06 (2)) 현재 사용자의 본인 예산으로 대신한다. 최종 결과가 nil이면 404다. 예산 전환 버튼(switcher)은 `personal_budgets`가 true일 때만 나오고 household(공용 예산을 켰을 때)·본인·나에게 공유한 구성원 순이다. | 코드 확인 |
| R-34 | 예산 화면이 읽는 다른 기능의 값(사용 지점만) | 카테고리 배정 행의 `bills_reserved`(기간 안의 미결제 청구서 예약액, 환산 불가 건수 포함)는 정기 거래(행 13)의 `RecurringOccurrence`에서 읽는 값이고 예산 계산(R-13~R-21)에는 들어가지 않는다("예산은 확정된 entry에서만 파생된다"는 원본 주석). `available_cash`의 목표 차감은 R-31. | 코드 확인(경계) |
| R-35 | 카테고리 상세의 거래 목록(`budget_categories#show`) | 예산의 `transactions`(가족 거래 중 계정이 draft·active, 기간 안, personal은 소유자의 `exclude_from_reports = false` 계정, household는 요청 사용자가 접근하는 `included_in_reports` 계정, 요청 사용자도 소유자도 없으면 계정 필터 없음) 중 `kind`가 `analytics_excluded_kinds`(`funds_movement`, `one_time`, `cc_payment`, 그리고 가족이 투자 적립을 지출로 안 치면 `investment_contribution`)가 아닌 것을 쓴다. 합성 미분류 id면 `category_id`가 없는 거래, 아니면 그 카테고리 또는 그 하위 카테고리 거래다. 정렬은 날짜 내림차순, 같으면 `|amount|` 내림차순이고 앞 3건만 돌려준다. 이 목록은 R-17의 보류·예정·`excluded`·세금 우대 계정 조건을 적용하지 않고 계정 접근 범위도 합계와 다르다(household는 `accessible_by`이고 `exclude_from_reports = false`가 붙는다. 합계는 `finance_accounts`). 목록도 `exclude_from_reports` 계정은 뺀다. 따라서 합계와 목록이 맞지 않을 수 있다. | 코드 확인 |
| R-36 | 예산 공유 설정(`settings/budget_shares#update`) | 입력은 `members` 목록(`viewer_id`, `permission`)이다. 공유 대상 후보는 현재 사용자의 가족에서 현재 사용자가 아니고 `active`인 구성원이고, 후보가 아닌 `viewer_id`는 무시한다. 한 DB 트랜잭션에서 목록의 구성원마다: `permission`이 `read_write`·`read_only`면 기존 공유가 있으면 그 값으로 바꾸고 없으면 만든다. 그 밖의 값(빈 값 포함)이면 기존 공유를 지우고 없으면 아무것도 하지 않는다. 목록에 없는 구성원의 공유는 건드리지 않는다. 끝나면 설정 화면으로 redirect한다. 현재 사용자는 자기가 준 공유만 바꿀 수 있고(`budget_shares_given`), 관리자 권한은 필요 없다. `BudgetShare` 검증은 R-32의 데이터 제약을 따른다. 공유는 사용자가 삭제되면 같이 지워지고, `personal_budgets`를 끄거나 켜도 공유 행은 그대로다(이 경로에서 정리하는 코드를 찾지 못했다, 2.1). | 코드 확인 |
| R-37 | 월 시작일 변경과 기존 예산 | `month_start_day`는 가족 설정에서 1~28로 바꾼다(`UsersController`, 행 소관 밖). 바꾼 뒤에는 새 값으로 기간을 계산하고(R-01), 이전 값으로 만든 예산 행의 기간은 그대로 남는다. 새 기간으로 예산을 열면 새 행이 생기고 옛 행과 기간이 겹칠 수 있다(모델 검증은 `start_date`와 `end_date`를 각각 `(family_id, user_id)` 범위에서 유일하게 하므로 시작일이나 종료일 중 하나만 같아도 검증에서 거절된다. DB index는 `(family, start_date, end_date, user)` 조합이 같을 때만 막는다). 기존 행을 새 기간으로 옮기거나 합치는 코드는 찾지 못했다(2.1). 설정 화면은 사용자 지정 시작일일 때 "예산과 MTD 계산이 이 시작일을 쓴다"는 경고를 보인다. | 코드 확인(없다 주장은 2.1) |

**배정 행의 다른 쓰기 경로**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-38 | 카테고리 삭제·병합과 AI `update_budget` | 이 경로들은 R-12의 부모 합 재계산도, 이월 체인 재계산(R-27)도 타지 않는다. (a) 카테고리 삭제: `Category`가 `has_many :budget_categories, dependent: :destroy`라 모든 예산의 그 카테고리 배정 행이 지워진다. 이월 carry에서 그 카테고리가 빠지는 것은 다음 재계산 때다(R-27). (b) 카테고리 병합(`Category::Merger#merge_budget_categories`): 원본 카테고리의 배정 행마다 같은 예산에 대상 카테고리 행이 있으면 대상의 `budgeted_spending`에 원본 값을 더하고(`to_d`, null은 0) 원본 행을 지우고, 없으면 원본 행의 `category_id`를 대상으로 바꾼다. 이월 toggle·`rolled_over_amount`는 합치지 않는다(대상 행의 값이 남는다). (c) 중복 카테고리 정리(`Family#merge_duplicate_categories`): 중복 카테고리의 모든 배정 행을 `update_all`로 keeper 카테고리 id로 바꾸므로 한 예산에 같은 카테고리 행이 둘이 되어 `(budget_id, category_id)` 유일 index에 걸릴 수 있다(충돌 처리 코드는 읽은 범위에 없다, 추론). (d) AI `update_budget` 함수는 `find_or_bootstrap` 뒤 `budget.update!`와 `update_budgeted_spending!`로 쓰고 체인 재계산을 부르지 않는다(`find_or_bootstrap` 안의 재계산은 쓰기 전에 실행된다). 행 15 소관이라 호출 사실만 적는다. | 코드 확인 / 추론((c)의 충돌) |

- 불변식:
  - 한 가족·소유자·기간에는 예산이 하나다(DB partial unique index, R-06). 한 예산에서 한 카테고리는 배정 행이 하나다.
  - 개별 한도 하위가 하나라도 있고 그 하위만 수정해 온 부모는 `부모 배정 >= 개별 한도 하위 배정 합`이다(R-12가 유지). 부모를 직접 수정한 직후에는 깨질 수 있다.
  - `rolled_over_amount >= 0`(DB check). 이월은 잉여만이라 음수가 없다(R-28).
  - 배정 행의 `rolled_over_amount` 저장값은 마지막 체인 재계산 시점의 입력으로 만든 값이다. 거래·환율이 바뀐 뒤 재계산 전까지는 낡을 수 있다(R-29).
  - `available_to_allocate = 총 예산 − 부모 배정 합`이고 이월은 포함하지 않는다(R-13, R-23).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-03 | R-34 | `bills_reserved`의 `RecurringOccurrence.open_status`·`remaining_amount_money`·`RecurringAllocation.confirmed` 계약은 읽지 않았다. | 청구서 예약액 표시. 예산 계산에는 영향 없다. | 행 13(정기 거래) 스펙. `budget.rb:427-450`, `budget_category.rb:420-437` 호출 지점. |
| U-04 | R-16, R-32, R-33, R-35 | "요청 사용자가 접근할 수 있는 계정"(`accessible_by`)과 "금융 대상 계정"(`finance_accounts`, `included_in_finances_for`)의 정의는 `Family`/`AccountShare` 스펙(승인 범위 밖) 소관이다. 이 문서는 두 집합이 다르다는 것(목록은 접근 계정, 합계는 금융 대상 계정)까지만 쓴다. | household 예산의 실적 범위. 구현자는 두 함수를 입력으로 받아야 한다. | `account.rb:115-119`, `:166-174`의 SQL과 AccountShare 스펙. 가정: 구현이 가족 구성원마다 다른 합계를 허용하거나, 하나의 가족 전체 집합으로 통일한다는 결정은 새 결정이다(원본은 구성원마다 다르다). |
| U-05 | R-30 | 가족 통화를 바꾼 뒤 옛 통화 예산의 실적·배정 숫자 단위가 다르다. 원본이 의도적으로 그렇게 두었는지, 단지 처리하지 않은 것인지 알 수 없다. | 통화 변경 사용 시 예산 표시. | `family.rb`의 통화 변경 흐름(money-currency-rules R-20)에서 예산을 건드리는 코드가 있는지 확인한다(이 문서는 `grep`으로 못 찾았다). |

- 확인 한계:
  - 이 환경에서 코드를 실행하지 않았다(레포 지침). 락·동시성(R-12, R-15, R-29)은 코드 읽기로만 확인했다.
  - 뷰·Stimulus는 상태 데이터의 의미를 정하는 부분(`budgets/show`, `_budgeted_summary`, `_allocation_progress`, `_budget_category_form`)만 읽었다. 도넛 구간 계산(`to_donut_segments_json`, `donut_budget_categories`)은 R-13·R-18 값을 쓰는 표시 로직이라 R-ID에 넣지 않았다.
  - `Date::Error`·decimal 캐스트·`RecordNotFound` 응답 코드는 프레임워크 기본 동작을 읽은 추론이다(R-02, R-08).
  - Budget 소비자인 인사이트·AI 함수·API v1·리포트는 열지 않았다. API v1 `budget_categories`가 조회 때 재계산을 호출한다는 것은 메서드 주석과 `recompute!` 호출 줄로만 확인했다.

### 1.5 필수 코드 참조

라이선스는 AGPL-3.0(overview 1절)이다. 아래 C-ID는 규칙을 옮기기 위한 위치이고 복사 여부는 별도 결정이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/budget.rb:29-54`, `:93-105` `date_to_param`, `param_to_date`, `budget_date_valid?`, `period_for`, `oldest_valid_budget_date`, `latest_valid_budget_start_date` | 파라미터 형식, 기간 계산, 유효 범위 | R-01~R-03 |
| C-02 | `app/models/family.rb:156`, `:322-345` `month_start_day` 검증, `uses_custom_month_start?`, `custom_month_start_for`, `custom_month_end_for`, `current_custom_month_period`, `:698-700` `oldest_entry_date` | 월 시작일 처리 | R-01, R-03, R-05 |
| C-03 | `app/models/budget.rb:65-90` `find_or_bootstrap` | 예산 찾기·만들기 순서 | R-06 |
| C-04 | `app/models/budget.rb:116-155` `sync_budget_categories`, `inherited_rollover_flags` | 배정 행 동기화와 toggle 상속 | R-07 |
| C-05 | `app/models/budget.rb:287-327` `most_recent_initialized_budget`, `copy_from!` | 복사 | R-09, R-10 |
| C-06 | `app/models/budget_category.rb:186-195`, `:439-460` `update_budgeted_spending!`, `sync_parent_budgeted_spending!` | 부모-자식 합 규칙 | R-12 |
| C-07 | `app/models/budget_category.rb:49-55`, `:69-147` `uncategorized`, `move_allocation!`, `validate_move!`, `movable_from`, `direct_lineage?`, `lock_ids_for_move` | 배정 이동 | R-15 |
| C-08 | `app/models/budget.rb:410-423`, `:460-504` `estimated_spending`, `actual_spending`, `budget_category_actual_spending`, `available_to_spend`, `percent_of_budget_spent`, `overage_percent`, `allocated_spending`, `allocated_percent`, `available_to_allocate`, `total_rolled_over`, `allocations_valid?` | 실적·배정 계산식 | R-13, R-18, R-23 |
| C-09 | `app/models/budget.rb:509-538` `estimated_income`, `actual_income`, `remaining_expected_income`, `actual_income_percent`, `surplus_percent` | 소득 계산식 | R-21 |
| C-10 | `app/models/budget_category.rb:221-343` `rolled_over_amount`, `inherits_parent_budget?`, `display_budgeted_spending`, `parent_budget_category`, `available_to_spend`, `percent_of_budget_spent`, `bar_width_percent`, `over_budget?`, `budgeted?`, `display_rolled_over_amount` | 카테고리별 남은 금액·사용률·표시 이월 | R-14, R-19, R-20, R-23 |
| C-11 | `app/models/budget_category.rb:345-386`, `:405-414` `unbudgeted_with_spending?`, `over_budget_with_budget?`, `on_track?`, `any_over_budget?`, `visible_on_track?`, `near_limit?`, `suggested_daily_spending`, `siblings`, `subcategories` | 상태 판정과 임계값 90, 일일 권장액 | R-20 |
| C-12 | `app/models/budget.rb:337-363` `current?`, `days_remaining`, `top_spending_categories` 와 `:365-377` `previous_budget_param`, `next_budget_param` | 현재 기간·남은 일수·요약·이동 | R-04, R-05, R-20 |
| C-13 | `app/models/budget/rollover_calculator.rb:30-123`, `:151-225` `recompute!`, `lock_chain!`, `recompute_chain!`, `first_relevant_budget_date`, `chain`, `initialized_budgets`, `incoming_carry`, `household_account_scope`, `ring_fenced_children_by_parent`, `leftover_for` | 체인 재계산과 잉여식 | R-22, R-25~R-28, R-30 |
| C-14 | `app/models/budget/rollover_calculator.rb:125-149` `inputs_fingerprint` | 선택적 캐시 지문(재구현 생략 가능) | R-29 |
| C-15 | `app/models/budget_category.rb:175-184` `propagate_rollover_choice_forward!` | 이후 달 전파 | R-24 |
| C-16 | `app/models/budget.rb:157-179`, `:200-251`, `:540-593` `uncategorized_budget_category`, `transactions`, `cash_accounts`, `available_cash`, `earmarked_for_goals`, `free_cash`, `convert_to_budget_currency`, `income_statement`, `income_statement_accounts`, `net_totals`, `expense_totals_by_category`, `income_totals_by_category`, `stable_synthetic_key` | 계정 범위, 환산, 카테고리 집계 키 | R-13, R-16, R-18, R-31, R-35 |
| C-17 | `app/models/budget.rb:269-285` `viewable_by?`, `editable_by?` | 권한 판정 | R-32 |
| C-18 | `app/controllers/concerns/budget_ownership.rb:24-68` `budget_target_user`, `resolve_budget`, `ensure_budget_editable!` | 대상 예산 결정과 편집 가드 | R-32, R-33 |
| C-19 | `app/controllers/budgets_controller.rb:1-70`, `app/controllers/budget_categories_controller.rb:1-118` | 컨트롤러 흐름(권한 가드, 파라미터, 재계산 시점, 오류 응답) | R-02, R-08, R-09, R-11, R-15, R-35 |
| C-20 | `app/controllers/settings/budget_shares_controller.rb:4-39`, `app/models/budget_share.rb:1-29`, `app/models/user.rb:240-242` | 공유 설정과 검증 | R-36 |
| C-21 | `app/models/income_statement.rb:62-123`, `:211-263` `net_category_totals`, `build_period_total`, `totals_for_period` | 순집계와 카테고리 합 | R-17, R-18 |
| C-22 | `app/models/income_statement/scoped_transactions_query.rb:13-33`, `:54-79`, `app/models/income_statement/totals.rb:73-83`, `:97-107` | 분류식, 환산식, 제외 조건 | R-17 |
| C-23 | `app/models/transaction.rb:87`, `app/models/family.rb:553-557` `BUDGET_EXCLUDED_KINDS`, `analytics_excluded_kinds` | 제외 `kind` 목록 | R-17, R-35 |
| C-24 | `app/models/income_statement/family_stats.rb:36-63` | 달별 합계의 중앙값(추정치) | R-21 |
| C-25 | `app/models/exchange_rate/provided.rb:160-171` `rate_sql` | 거래 날짜 환율 조회(money-currency-rules C-09와 같은 코드) | R-17 |
| C-27 | `app/models/category.rb:7`, `app/models/category/merger.rb:73-89`, `app/models/family.rb:566-573` | 카테고리 삭제·병합·중복 정리가 배정 행에 하는 일 | R-38 |
| C-26 | `db/schema.rb:364-404`, `:871-892` `budget_categories`, `budget_shares`, `budgets`, 가족 설정 컬럼 | 컬럼·기본값·unique·check | 1.3 데이터, R-06, R-12 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 날짜는 오늘이 2026-11-18, 가족 통화는 KRW(소수 자릿수 0), 별도 언급이 없으면 `month_start_day = 1`이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-02 | `S = 1`. 날짜 2026-11-18의 기간. 파라미터 `nov-2026`을 읽는다 | 기간 2026-11-01 ~ 2026-11-30. 파라미터 `nov-2026` → 2026-11-01. 예산 `to_param`은 `nov-2026`이다. |
| T-02 | R-01, R-02 | 월급일 `S = 25`. 날짜 2026-11-18, 2026-11-25, 2026-01-10, 2026-03-01의 기간. 파라미터 `oct-2026`을 읽는다 | 2026-11-18 → 2026-10-25 ~ 2026-11-24. 2026-11-25 → 2026-11-25 ~ 2026-12-24. 2026-01-10 → 2025-12-25 ~ 2026-01-24(파라미터 `dec-2025`). 2026-03-01 → 2026-02-25 ~ 2026-03-24. `oct-2026` → 2026-10-25(파라미터는 시작일의 달이다). 11월 24일 거래는 `oct-2026` 예산에, 25일 거래는 `nov-2026` 예산에 들어간다. |
| T-03 | R-03, R-04 | 오늘 2026-11-18, 가장 이른 entry 2025-03-14, `S = 1`. 이어서 `S = 25`로 바꾼 가족 | `S = 1`: 하한 = `min(2024-11-01, 2025-03-01)` = 2024-11-01, 상한 = 2028-11-01. `oct-2024` 무효, `nov-2024` 유효, `nov-2028` 유효, `dec-2028` 무효. 이전/다음 링크는 경계 달에서 nil. `S = 25`: 상한 = 오늘이 속한 기간 시작일 2026-10-25 + 2년 = 2028-10-25라 `oct-2028`(시작 2028-10-25) 유효, `nov-2028`(시작 2028-11-25) 무효. 하한은 2024-11-01이라 `oct-2024`(시작 2024-10-25) 무효, `nov-2024`(시작 2024-11-25) 유효. 가장 이른 entry가 2023-06-20이면 하한은 2023-06-01로 내려간다. entry가 없는 가족의 하한은 `min(2년 전 달 1일, 오늘의 달 1일)` = 2024-11-01이다. |
| T-04 | R-06, R-07 | 가족 KRW, `personal_budgets = false`, 카테고리 식비(부모)·외식(식비의 하위)·교통. 사용자 Alice가 `nov-2026`을 처음 연다 | household 예산 행 1개(`user_id` 없음, `currency = KRW`, `budgeted_spending = null`)가 생기고 배정 행 3개(식비·외식·교통, `budgeted_spending = 0`, `rollover_enabled = false`)가 생긴다. `initialized?`는 false. 같은 요청을 다시 해도 행이 늘지 않는다. 기간이 2029-01이면 아무것도 만들지 않고 404. |
| T-05 | R-07 | `oct-2026` 예산이 초기화됐고 식비 `rollover_enabled = true`, 교통 false. 이어서 `nov-2026`을 처음 연다. 이후 카테고리 "여가"를 새로 만들고 `nov-2026`을 다시 연다 | `nov-2026`의 식비는 `rollover_enabled = true`로 시작하고 교통은 false. 이미 있는 행의 toggle은 안 바뀐다. "여가" 행은 `oct-2026`에 없어 false로 생긴다. `oct-2026`이 초기화되지 않았으면 모두 false다. |
| T-06 | R-09, R-10 | `oct-2026`: 총 예산 3,000,000, 예상 소득 3,500,000, 식비 800,000(rollover true), 교통 150,000. `nov-2026`은 미초기화. 복사 요청 | `nov-2026`의 총 예산 3,000,000, 예상 소득 3,500,000, 식비 800,000(rollover true), 교통 150,000이 된다. `rolled_over_amount`는 복사가 아니라 체인 재계산 결과다. 다시 복사를 요청하면 alert만 나오고 변하지 않는다. 이전 초기화 예산이 없으면 alert("원본 없음"). |
| T-07 | R-12, R-13 | 총 예산 3,000,000. 식비 800,000, 교통 150,000, 외식(식비 하위) 0. 이어서 외식을 200,000, 다시 0으로. 따로: 식비를 100,000으로 낮추고 외식 200,000이 있는 상태에서 외식을 250,000으로 | 처음: `allocated_spending` = 950,000(식비+교통, 하위는 안 더함), `available_to_allocate` = 2,050,000, 미분류 배정 = 2,050,000. 외식 200,000으로: 이전 0, 형제 합 0, `reserve = max(800,000 − 0 − 0, 0)` = 800,000 → 식비 = 0 + 200,000 + 800,000 = 1,000,000, `allocated_spending` = 1,150,000. 외식 0으로: 이전 200,000, `reserve = max(1,000,000 − 0 − 200,000, 0)` = 800,000 → 식비 800,000. 따로: 식비 100,000(서버가 막지 않음), 외식 250,000으로 수정하면 `reserve = max(100,000 − 0 − 200,000, 0)` = 0 → 식비 = 250,000. |
| T-08 | R-13 | 총 예산 1,000,000. 부모 배정 700,000과 400,000 | `available_to_allocate` = −100,000, `allocated_percent` = 110, `allocations_valid?` false. 예산 화면은 도넛 대신 과배정 경고를 보이고 "예산/실적" 탭은 나오지 않는다. 총 예산 0이면 `allocated_percent` = 0. |
| T-09 | R-18 | 총 예산 3,000,000. 식비(부모) 기간 지출 650,000·같은 카테고리 환불(소득 분류) 50,000, 교통 지출 130,000. 별도로 여가: 지출 10,000, 환불 30,000 | 식비 카테고리 실적 600,000, 교통 130,000, 여가 실적 `max(10,000 − 30,000, 0)` = 0. 총 실적 = 600,000 + 130,000 = 730,000(여가는 순소득이라 총 실적을 줄이지 않는다). `available_to_spend` = 2,270,000, `percent_of_budget_spent` ≈ 24.33. 한도 1,000,000에 지출 1,250,000이면 `available_to_spend` = −250,000, 사용률 125, `overage_percent` = 20. |
| T-10 | R-19, R-20 | 식비 배정 300,000, 이월 0. 실적을 270,000 / 269,999 / 300,000 / 300,001로 바꿔 본다. 별도로 "여가" 배정 0, 이월 0, 실적 5,000 / 배정 0, 이월 80,000, 실적 0 | 270,000: 사용률 90.0 → `near_limit?` true. 269,999: 89.9997 → false. 300,000: 남은 0이라 `over_budget?` false, 사용률 100, `near_limit?` true. 300,001: 남은 −1 → `over_budget?` true(근접 아님). 여가 실적 5,000: `budgeted?` false → `unbudgeted_with_spending?` true → `any_over_budget?` true. 이월 80,000만 있는 여가: `budgeted?` true, 실적 0이면 `on_track?` true. |
| T-11 | R-19 | 식비(부모) 배정 800,000(이월 0), 하위 배달 150,000(개별 한도), 외식 0(공유). 식비 자체 지출 200,000, 외식 400,000, 배달 100,000 → 부모 실적 700,000 | 외식: `shared_budget` = 800,000 − 150,000 = 650,000, `shared_spending` = 700,000 − 100,000 = 600,000, 남은 금액 = 50,000, 사용률 = 외식 실적 400,000 / 650,000 × 100 ≈ 61.54. 배달: 150,000 − 100,000 = 50,000. 부모: 800,000 + 0 + 0 − 700,000 = 100,000. 공유 하위의 남은 금액은 0 아래로 내려가지 않고, 부모의 남은 금액은 따로 계산된다. 배달이 한도보다 덜 쓰면 공유 몫이 넘쳐도 부모는 양수일 수 있다. 예: 식비 자체 200,000, 외식 500,000, 배달 0이면 부모 실적 700,000, `shared_spending` = 700,000 > `shared_budget` 650,000이라 외식 남은 금액은 `max(−50,000, 0)` = 0이지만 부모 남은 금액은 800,000 − 700,000 = 100,000이다. |
| T-12 | R-22, R-27, R-28 | 식비 rollover 켬. 1월 배정 300,000·실적 220,000, 2월 300,000·실적 400,000, 3월 300,000·실적 100,000(모두 초기화됨) | 1월 incoming 0, outgoing `max(300,000 − 220,000, 0)` = 80,000. 2월 incoming 80,000(저장 `rolled_over_amount` = 80,000), 남은 금액 300,000 + 80,000 − 400,000 = −20,000(초과), outgoing 0(적자는 안 넘어감). 3월 incoming 0, 남은 금액 300,000 + 0 − 100,000 = 200,000. |
| T-13 | R-25, R-27 | T-12에서 2월이 초기화되지 않음(`budgeted_spending` null). 3월 rollover 켬 | 3월 incoming = 1월 outgoing 80,000(2월은 체인의 빈 칸이라 건너뜀). 2월 행은 갱신되지 않는다. |
| T-14 | R-22, R-27 | T-12에서 2월에 식비 rollover를 끄고, 3월에 다시 켠다(2·3월 모두 초기화) | 2월 incoming 0(꺼짐), outgoing 0 → 3월 incoming 0. 앞서 저장돼 있던 2월 `rolled_over_amount` 80,000은 다음 재계산에서 0으로 쓰인다. 읽기 이월(R-23)은 저장값과 상관없이 꺼진 달에 0이다. |
| T-15 | R-23, R-28 | 식비(부모) 배정 800,000(하위 배달 150,000 포함), incoming 0, 부모 실적 700,000(배달 100,000 포함), 둘 다 rollover 켬 | 부모 leftover: `budgeted` = 800,000 − 150,000 = 650,000, `actual` = 700,000 − 100,000 = 600,000 → 50,000. 배달 leftover: 150,000 + 0 − 100,000 = 50,000. 다음 달 `total_rolled_over` = 50,000 + 50,000 = 100,000. 다음 달 식비 남은 금액 = 800,000 + 50,000 + 배달 이월 50,000 − 부모 실적. |
| T-16 | R-27 | 오늘 2026-11-18. 11월 식비 배정 300,000·지금까지 실적 100,000, 12월(초기화됨)·rollover 켬 | 12월 식비 incoming = 300,000 − 100,000 = 200,000(11월이 끝나지 않았어도). 11월에 더 지출하면 다음 화면 로드의 재계산이 12월 incoming을 줄인다. 12월 배정 300,000이면 12월 남은 금액 = 500,000. |
| T-17 | R-15 | 식비 500,000, 교통 100,000. 식비 → 교통 150,000 이동 | 식비 350,000, 교통 250,000. 이어서 실패 사례: amount 0 → `non_positive_amount`, 식비 → 식비 → `same_category`, 식비 → 외식(하위) → `parent_child`, `uncategorized`·`different_budgets`는 모델 직접 호출에서만 나오고(컨트롤러 경로는 `find`에서 404), 컨트롤러 경로의 나머지 실패는 422다. 식비 배정 800,000에 개별 한도 하위 배달 150,000이 있을 때 이동 가능액은 650,000이라 700,000 이동은 `insufficient_funds`. 같은 부모의 하위끼리 이동은 부모 배정이 바뀌지 않는다. 권한 없으면 404. |
| T-18 | R-31 | 예산 통화 KRW. 현금 계정 입출금(KRW) 잔액 2,000,000, USD 계정 잔액 1,000 USD, 오늘 환율 USD→KRW 1,350. 이어서 USD 환율이 없는 경우 | `available_cash` = 2,000,000 + 1,350,000 = 3,350,000. 환율이 없으면 USD 계정은 0이라 `available_cash` = 2,000,000, `missing_cash_currencies` = {USD}. `earmarked_for_goals` 500,000이면 `free_cash` = 2,850,000(환율 있음). 차감 결과가 음수면 0. 투자 계정의 현금과 `exclude_from_reports` 계정은 합에 들지 않는다. |
| T-19 | R-20 | 현재 기간(2026-11-01~2026-11-30), 오늘 2026-11-18, 식비 남은 금액 210,000. 오늘이 11-30이면, 오늘이 12-01이면, 지난 달 예산이면 | `days_remaining` = 13 → `{amount: 210,000 / 13 = 16153.846..., days_remaining: 13}`(반올림 없음, 화면 표시는 ₩16,154). 11-30이면 1일. 12-01이면 `days_remaining` 0이라 nil. 지난·미래 기간이면 nil. 남은 금액이 0 이하여도 nil. |
| T-20 | R-32, R-33 | `personal_budgets = true`. Alice 소유 personal 예산. Bob에게 `read_only` 공유. Bob이 `?owner=<Alice>`로 `nov-2026`을 열 때(Alice의 11월 예산이 있는 경우와 없는 경우), Bob이 배정을 수정할 때. 이어서 `read_write`로 바꾼 뒤 | Alice의 11월 예산이 있으면 그것을 보여 준다(새로 만들지 않음, 재계산 안 함). 없으면 Bob 본인 예산을 만들어 보여 준다. 수정은 404. `read_write`로 바꾸면 수정 가능하고 실적은 Alice의 소유 계정 기준이다. 공유 없는 Carol이 같은 `owner`로 열면 조용히 Carol 본인 예산이 열린다. household 예산(`?owner=household`, `household_budget_enabled`가 true)은 모든 구성원이 수정 가능하고, 가족이 껐으면 본인 예산이 열린다. |
| T-21 | R-36 | Alice가 `members: [{viewer_id: Bob, permission: "read_only"}]`를 보낸다. 이어서 Bob을 `read_write`로, 빈 값으로, `viewer_id`에 비활성 사용자·다른 가족 사용자·자기 자신을 넣어서 | 처음: 공유 행 생성(`read_only`). 두 번째: 같은 행의 permission이 `read_write`. 빈 값: 행 삭제. 후보가 아닌 `viewer_id`는 무시되어 행이 생기지 않는다. Bob이 Alice에게 준 공유는 영향받지 않는다. 설정 화면으로 redirect. |
| T-22 | R-21 | 예상 소득 3,500,000, 실제 소득 3,900,000. 이어서 예상 소득 미입력(null)·실제 소득 100,000 | `remaining_expected_income` = −400,000, `actual_income_percent` ≈ 111.43, `surplus_percent` = 400,000 / 3,500,000 × 100 ≈ 11.43. 예상 소득이 없으면 `remaining` = −100,000, `actual_income_percent` = 0, `surplus_percent` = 100. |
| T-23 | R-17, R-18 | 가족 KRW. 식비 카테고리 거래: 지출 amount +30,000, 환불 amount −5,000(소득 분류), 같은 카테고리 외화 거래 USD +10(거래일 환율 1,380, KRW 환산 13,800), 환율이 없는 JPY +1,000. 그 밖 거래: kind `funds_movement` 50,000, `excluded = true` 20,000, 보류 15,000, 날짜가 내일인 18,000 | 이 기간 식비 지출 합 = 30,000 + 13,800 = 43,800, 환불 5,000. 이체(`funds_movement`)·`excluded`·보류·미래 거래·환율 없는 JPY는 합에 안 들어간다. 식비 실적 = 43,800 − 5,000 = 38,800. |
| T-24 | R-02, R-03 | 임의 문자열 `foo`로 `GET /budgets/foo`, 유효 범위 밖 `/budgets/jan-2031` | `foo`는 `Date::Error`(처리 안 됨, 500 추정). `jan-2031`은 R-03에서 유효하지 않아 404. |
| T-25 | R-08, R-11 | 총 예산 입력 `3000000.5`(KRW), 배정 요청에 `budgeted_spending` 키 없이 `rollover_enabled=true`만 보냄, 배정에 `-5000` | 총 예산 3,000,000.5가 그대로 저장된다(KRW도 반올림하지 않는다). 화면 표시만 통화 자릿수(KRW 0자리)로 반올림해 ₩3,000,001로 보인다(money-currency-rules R-08, R-10). 키 없는 요청은 toggle을 켜고 배정을 0으로 저장한다. −5,000은 서버가 저장한다(UI `min=0`만 막는다). |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `app/models/budget.rb:48-54`; C-02 `app/models/family.rb:322-345` | 코드 확인. 종료일 계산 `next_month_start - 1.day`는 `family.rb:337-339`. |
| R-02 | C-01 `app/models/budget.rb:29-40`; `app/controllers/budgets_controller.rb:7-9`, `:60-69`; `app/controllers/budget_categories_controller.rb:113-117`; `app/controllers/concerns/store_location.rb:14` | 코드 확인. `Date::Error` 처리 여부: 예산 컨트롤러는 rescue가 없고 `store_location.rb:14`가 처리하는 것은 `RecordNotFound`뿐이라 500은 프레임워크 기본을 읽은 추론이다. `grep -rn "Date::Error" app/controllers` 결과 `accountable_resource.rb:40`만 있다. 확인 범위 `app/controllers`. |
| R-03 | C-01 `app/models/budget.rb:42-46`, `:93-105`; `app/models/family.rb:698-700` | 코드 확인. 하한의 `2.years.ago.beginning_of_month`가 시간 값이고 `oldest_entry_date`는 날짜라 `min`이 섞여 비교하는 것은 읽었다. 두 값의 비교를 날짜 단위로 쓴 것은 추론(시간대 경계에서 하루 차이가 날 수 있다). 404 경로는 `budgets_controller.rb:60-64`. |
| R-04 | C-12 `app/models/budget.rb:365-377` | 코드 확인. |
| R-05 | C-12 `app/models/budget.rb:337-351`; `app/models/budget_category.rb:375-386` | 코드 확인. |
| R-06 | C-03 `app/models/budget.rb:65-90`; `db/schema.rb:400-401` | 코드 확인. 유일성 index는 C-26. |
| R-07 | C-04 `app/models/budget.rb:116-155`; `db/schema.rb:364-377` | 코드 확인. "카테고리 생성·삭제 시점에는 동기화하지 않는다"는 부재 주장: `grep -rn "sync_budget_categories" app lib --include=*.rb` 범위에서 `budget.rb:84`(`find_or_bootstrap`)와 정의뿐이다. 놓칠 수 있는 곳: 콜백·동적 호출·`app` 밖. |
| R-08 | `app/controllers/budgets_controller.rb:22-25`, `:56-58`; `app/models/budget.rb:19-20`; `db/schema.rb:390-404` | 코드 확인. 숫자 검증이 없다는 부재 주장: `grep -n "validates" app/models/budget.rb app/models/budget_category.rb`는 `budget.rb:19-20`(presence·uniqueness)과 `budget_category.rb:24`(uniqueness)뿐이고 `db/schema.rb`의 `budgets`에는 check constraint가 없다. 비숫자 문자열이 0이 되는 것은 `ActiveModel::Type::Decimal` 기본 동작을 읽은 추론. 이 경로가 체인 재계산을 안 부르는 것은 `grep -rn "recompute!" app lib --include=*.rb` 결과(`budget.rb:86`, `:325`, `budget_categories_controller.rb:51`, `:73`, `api/v1/budget_categories_controller.rb:57`)로 확인. |
| R-09 | `app/controllers/budgets_controller.rb:27-41`; C-05 `app/models/budget.rb:287-295` | 코드 확인. |
| R-10 | C-05 `app/models/budget.rb:297-327` | 코드 확인. "복사 중 재계산 없음"은 `copy_from!`이 `update!`로만 부모-하위 합을 건드리지 않는 것을 읽은 것이다(`BudgetCategory#update!`를 직접 부르고 `update_budgeted_spending!`를 부르지 않는다). |
| R-11 | `app/controllers/budget_categories_controller.rb:37-60`, `:99-111`; C-06 | 코드 확인. 폼이 두 필드를 함께 보내는 것은 `app/views/budget_categories/_budget_category_form.html.erb:33-60`. 음수 허용은 R-08의 검증 부재 확인과 같다. |
| R-12 | C-06 `app/models/budget_category.rb:186-195`, `:439-460` | 코드 확인. T-07의 수치는 식을 손으로 풀어 맞춘 것이다(실행하지 않았다). |
| R-13 | C-08 `app/models/budget.rb:157-162`, `:479-504`; `app/views/budgets/show.html.erb:13-46`; `app/views/budget_categories/_allocation_progress.erb:5-43` | 코드 확인. |
| R-14 | C-10 `app/models/budget_category.rb:217-219`, `:237-257`; `app/models/category.rb:369-371` | 코드 확인. orphan에서 합계가 어긋나는지는 실행하지 않았다. |
| R-15 | C-07 `app/models/budget_category.rb:69-147`, `:200-207`; `app/controllers/budget_categories_controller.rb:62-90` | 코드 확인. 검증 순서는 `validate_move!` 줄 순서다. |
| R-16 | C-16 `app/models/budget.rb:164-179`, `:552-565`; `app/models/income_statement.rb:8-18`, `:329-335`; `app/models/account.rb:166-174` | 코드 확인. `find_or_bootstrap`이 `current_user`를 요청 사용자로 두는 것은 `budget.rb:83`, 다른 사람의 기존 예산을 반환하는 경로에서 `current_user`가 없는 것은 `budget_ownership.rb:44-46`을 읽은 것이다. 계정 집합 SQL은 U-04. |
| R-17 | C-21, C-22, C-23, C-25; `app/models/income_statement.rb:20-23`, `:153-155`; `app/models/income_statement/totals.rb:84-107`; 투자 활동 라벨 제외 `scoped_transactions_query.rb:45-52` | 코드 확인. 예산이 쓰는 경로(`totals_for_period`, `expense_totals`, `income_totals`)만 읽었다. 환율 규칙은 money-currency-rules R-26, R-41. 일별 시계열·`invested_total`은 읽지 않았다. 보류 판정 SQL(`not_pending_sql`)의 내용은 읽지 않았다(해소: [reports-insights](./reports-insights.md) R-01·R-10·R-11). |
| R-18 | C-08 `app/models/budget.rb:414-423`, `:460-474`; C-21 `app/models/income_statement.rb:62-123`; C-16 `:579-593` | 코드 확인. 총 실적이 부모 카테고리의 양의 순지출 합이라는 것은 `income_statement.rb:81-101`의 `reject { subcategory? }`와 `net > 0` 분기를 읽은 것이다. "기타 투자가 목록에 안 보인다"는 `budget.rb:396-405`(`donut_budget_categories`)와 배정 행이 가족 카테고리 기준으로만 생기는 `sync_budget_categories`를 읽은 추론이다. |
| R-19 | C-10 `app/models/budget_category.rb:259-315` | 코드 확인. 분모가 음수일 때 nil은 `:313`의 후행 `if`가 거짓이 되는 것을 읽은 것이고 실행해 보지 않았다. |
| R-20 | C-10 `app/models/budget_category.rb:317-343`; C-11 `:345-386`; C-12 `app/models/budget.rb:353-363`; 사용 `app/views/budget_categories/_budget_category.html.erb:28-45`, `app/helpers/budgets_helper.rb:13-17` | 코드 확인. 임계값 90은 `near_limit?`(`budget_category.rb:370-372`)의 상수다. 문서/주석은 없다. |
| R-21 | C-09 `app/models/budget.rb:509-538`; C-24 `app/models/income_statement/family_stats.rb:36-63`; `app/models/income_statement.rb:176-194`; `app/views/budgets/edit.html.erb:22-41`; `app/models/income_statement/category_stats.rb:40-61` | 코드 확인. `actual_income`이 `income_totals.total`(순집계가 아님)이라는 것은 `budget.rb:513-515`와 R-18의 `net_totals`를 대조한 것이다. 달 기준이 달력 달인 것은 `date_trunc(:interval, ae.date)`(`family_stats.rb:40`)다. `estimated_*`가 `|| 0`인 것은 `budget.rb:410-411`, `:509-510`, 제안 조건은 `budgets/edit.html.erb:22`. 부재 주장 "`a.status`·투자 활동 라벨 제외가 없다": `family_stats.rb`의 WHERE 절(`:46-53`)에 해당 조건이 없다. 확인 범위 이 파일(공용 SQL 조각 `scoped_transactions_query.rb`의 `investment_activity_label_sql`을 이 쿼리가 부르지 않는 것까지). |
| R-22 | C-13 `app/models/budget/rollover_calculator.rb:96-107`, `:185-192` | 코드 확인. |
| R-23 | C-10 `app/models/budget_category.rb:225-234`, `:338-343`; C-08 `app/models/budget.rb:498-500` | 코드 확인. |
| R-24 | C-15 `app/models/budget_category.rb:175-184`; `app/controllers/budget_categories_controller.rb:39-44` | 코드 확인. |
| R-25 | C-13 `app/models/budget/rollover_calculator.rb:176-183` | 코드 확인. |
| R-26 | C-13 `app/models/budget/rollover_calculator.rb:77`, `:194-201`; `app/models/budget.rb:12`, `:552-565` | 코드 확인. 이유는 코드 주석(`rollover_calculator.rb:194-198`)의 서술이다(개발자 의도이므로 `추론`에 준하나 주석 원문이라 코드 확인으로 표기). |
| R-27 | C-13 `app/models/budget/rollover_calculator.rb:30-123`, `:151-174`, `:185-192` | 코드 확인. T-12~T-16의 수치는 식을 풀어 맞춘 것이다. |
| R-28 | C-13 `app/models/budget/rollover_calculator.rb:209-225` | 코드 확인. |
| R-29 | C-13 `rollover_calculator.rb:20-58`; C-14 `:125-149`; `app/controllers/api/v1/budget_categories_controller.rb:36-59`; 호출처 검색 `grep -rn "RolloverCalculator" app lib --include=*.rb` | 코드 확인. 부재 주장 "거래가 바뀔 때 호출하지 않는다": 위 검색 범위는 `app/`, `lib/`뿐이고 결과는 `budget.rb`, `budget_category.rb`(주석), `budget_categories_controller.rb`, `api/v1/budget_categories_controller.rb`, 계산기 자신이다. `config/`·`db/`·rake 작업은 검색하지 않았고, 호출이 콜백·`send`로 숨어 있을 가능성은 검색으로 배제하지 못한다. API v1의 `refresh_rollover_chains` 호출 지점은 열지 않았다. 캐시 생략이 같은 결과라는 것은 코드 구조를 읽은 추론이다(캐시는 "쓴 것이 없는 패스"만 저장). |
| R-30 | C-13 `app/models/budget/rollover_calculator.rb:64-73`, `:185-192`; `app/models/budget.rb:80`, `:213-214`, `:553`; `app/models/income_statement.rb:365-367` | 코드 확인. 부재 주장 "옛 예산의 통화를 변환하는 코드가 없다": `grep -rn "currency" app/models/budget.rb app/models/budget_category.rb`와 `family.rb`의 통화 변경 분기(money-currency-rules R-20이 읽은 `family.rb:174`, `:176-182`)를 대조했고 예산을 건드리는 줄이 없었다. 확인 범위 이 세 파일. 다른 디렉터리의 콜백은 배제하지 못했다(U-05). |
| R-31 | C-16 `app/models/budget.rb:200-251`, `:540-551`; `app/models/account.rb:83-86`; `app/views/budgets/show.html.erb:49-55`; `app/controllers/concerns/preview_gateable.rb:8-10` | 코드 확인. 환율 조회는 money-currency-rules R-25. 패널 노출 조건은 `app/controllers/concerns/preview_gateable.rb:8-10`의 `Current.user` 기준이다(`family.rb:150-152`의 `Family#preview_features_enabled?`는 이 화면이 쓰지 않는다). 이 concern이 `BudgetsController`에 포함돼 뷰의 helper로 쓰이는 연결은 `budgets/show.html.erb:52` 호출만 확인했다. |
| R-32 | C-17 `app/models/budget.rb:269-285`; C-18 `app/controllers/concerns/budget_ownership.rb:66-68`; `app/controllers/budgets_controller.rb:4-5`, `:13`; `app/controllers/budget_categories_controller.rb:4-5` | 코드 확인. 부재 주장 "`viewable_by?`는 컨트롤러에서 호출되지 않는다": `grep -rn "viewable_by?\|editable_by?" app lib --include=*.rb --include=*.erb` 결과 예산에 관한 호출은 `budgets_controller.rb:13`, `budget_ownership.rb:67`, `plans_controller.rb:12`(모두 `editable_by?`)뿐이고 `Budget#viewable_by?`의 호출처는 없었다(나머지 `viewable_by?`는 `AccountStatement` 것이다). 놓칠 수 있는 곳: 정의 이름이 같은 다른 클래스·동적 호출. |
| R-33 | C-18 `app/controllers/concerns/budget_ownership.rb:17-64`, `:75-106`; `app/models/user.rb:240-242` | 코드 확인. |
| R-34 | `app/models/budget.rb:425-450`; `app/models/budget_category.rb:1-17`, `:420-437` | 코드 확인(호출 경계만). 호출되는 `RecurringOccurrence` 쪽은 읽지 않았다(U-03). |
| R-35 | `app/controllers/budget_categories_controller.rb:12-35`; C-16 `app/models/budget.rb:169-179`; C-23 `app/models/family.rb:553-557` | 코드 확인. 합계와 목록이 맞지 않을 수 있다는 서술은 R-17의 조건과 이 목록의 `where`를 대조한 것이다. 원본 주석(`budget_categories_controller.rb:13-21`)은 `kind` 필터를 맞추려는 목적만 말한다. |
| R-36 | C-20 `app/controllers/settings/budget_shares_controller.rb:4-39`; `app/models/budget_share.rb:1-29`; `config/routes.rb:423`; `db/schema.rb:379-388` | 코드 확인. 부재 주장 "`personal_budgets` 변경 때 공유를 정리하는 코드가 없다": `grep -rn "budget_shares\|BudgetShare" app lib --include=*.rb`에서 `users_controller.rb`의 `personal_budgets_changed`(`:144-149`)가 무엇을 하는지 줄만 확인했고 본문 동작은 열지 않았다. 따라서 이 주장은 확인이 불완전하다. 사용자 삭제 때 공유가 지워지는 것은 `user.rb:41-42`의 `dependent: :destroy`. |
| R-37 | `app/controllers/users_controller.rb:117`; `app/views/settings/preferences/show.html.erb:64-76`; C-02 `app/models/family.rb:156`; 검색 `grep -rn "month_start_day" app lib config --include=*.rb --include=*.erb` | 코드 확인. 부재 주장 "기존 예산 행을 새 시작일로 옮기는 코드가 없다": 위 검색 결과의 사용처는 `users_controller.rb:117`, 설정 뷰, `family.rb`, `assistant/function/month_resolvable.rb:11`, `budget.rb:36`뿐이다. 확인 범위 `app/`, `lib/`, `config/`의 `.rb`·`.erb`. `db/`의 마이그레이션과 문자열·동적 참조(`send`, 문자열 조합)는 검색하지 않았다. |
| R-38 | C-27; `app/models/assistant/function/update_budget.rb:105-130` | 코드 확인. 부재 주장 "세 경로가 `update_budgeted_spending!`·`RolloverCalculator`를 부르지 않는다": 위 줄 범위를 읽은 것이고 `grep -rn "RolloverCalculator" app lib`의 호출처 목록(R-29)에 `category.rb`·`merger.rb`·`family.rb`가 없다. 확인 범위 `app/`, `lib/`. (c)의 유일 index 충돌은 `update_all`이 index를 우회하지 않는다는 DB 동작에서 온 추론이다. |
| T-01~T-25 | 각 R-ID의 근거 | 식을 코드와 대조해 손으로 계산했다. 실행은 하지 않았다. T-03의 하한·상한 값은 오늘 2026-11-18 가정에서 R-03 식에 대입한 것이다. |

### 2.2 코드 읽는 순서 [선택]

1. `app/controllers/concerns/budget_ownership.rb`(어떤 예산을 여는가), `budgets_controller.rb`, `budget_categories_controller.rb`(입구와 재계산 시점).
2. `app/models/budget.rb`의 `find_or_bootstrap`과 기간 메서드, 다음 실적·배정 계산(`:410-538`).
3. `app/models/budget_category.rb`의 `update_budgeted_spending!`·`move_allocation!`, 그다음 카테고리별 계산(`:221-386`).
4. `app/models/budget/rollover_calculator.rb`(`recompute_chain!`과 `leftover_for`가 핵심, 나머지는 락과 캐시).
5. 집계는 `income_statement.rb`와 `income_statement/scoped_transactions_query.rb`(R-17의 제외 규칙이 여기 있다).

원본의 구현 전략: 이월액은 읽을 때 계산하지 않고 체인을 앞에서 뒤로 한 번에 계산해 저장한다. 월 N의 이월이 월 N−1에 의존해 읽기마다 전체 체인을 걷지 않기 위해서다(코드 주석).

### 2.4 검토 기록

- **wave 3 후속(2026-11-18)**: U-01(`IncomeStatement` 계약)은 reports-insights 독립 검토가, U-02(`Goal.backing_within`)는 goals 독립 검토가 닫았다. R-17·R-18의 "기타 투자 포함" 문장은 합이 항상 0이라는 사실에 맞게 고쳤다.

`draft`다(미결정 U-03~U-05가 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-37 전부와 C-01~C-26 표본, T-01~T-23 중 대부분 재계산, 부재 주장 R-07·R-08·R-29·R-30·R-32·R-36·R-37 반증 시도. 원본 내부 불일치로 적은 R-21·R-26·R-35는 실제로 확인됐다. 중요 오류 1건(R-31 패널 노출 조건), 사소 5건, 누락 3건이 나왔다. 작성자가 전부 반영해 R-38을 추가했다.
- **메인 표본 점검**: R-31(`budgets/show.html.erb:52`, `preview_gateable.rb:8-9`), R-38(`category.rb:7`, `category/merger.rb:73-89`), R-14(`budget_category.rb:217-219`), R-37(`budget.rb:20`)을 원본에서 직접 확인했다.
- **대조하지 못한 것**: 화면 partial 세부, `Date.strptime` 오류 응답과 decimal 캐스트(추론).
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-08, R-11 | 금액이 음수·비숫자면 서버에서 검증 오류로 거절한다. 배정 요청에 `budgeted_spending` 키가 없으면 0으로 쓰지 않고 그 필드를 그대로 둔다. | 원본은 화면(`min=0`)에만 맡겨 서버가 음수를 저장하고 percent 계산이 nil을 낼 수 있다(R-19). | 입력 검증 실패 응답 추가. T-25의 두 번째·세 번째 결과가 달라진다. 원본의 미결정이 아니라 새 결정이다. |
| R-16, R-17, R-35 | household 예산의 실적 범위를 구성원과 무관한 가족 전체 계정으로 통일할지 결정한다. 카테고리 상세 목록에도 합계와 같은 제외 조건을 적용한다. | 원본은 보는 사람마다 합계가 다르고 목록과 합계가 어긋난다. 월급일 기준 한 가족이 함께 쓰는 예산이면 구성원마다 숫자가 다른 것이 혼란스럽다. | `current_user`를 계정 집합 입력으로 받는 인터페이스가 가족 집합으로 바뀐다. R-26의 household 체인 계산과도 일치한다. |
| R-03 | 하한을 달력 달 1일이 아니라 "기간 시작일" 기준으로 비교한다. | 월급일 25일 사용자는 하한 달의 1~24일 구간이 속한 기간(전월 25일 시작)이 무효가 되는 경계 효과가 있다(T-03). | 유효 범위 판정 식 변경. |
| R-30 | 가족 통화를 바꿀 때 예산 금액을 환산하거나 옛 통화 예산을 읽기 전용으로 표시한다. | 원본은 실적과 배정의 단위가 어긋난다(U-05). | 통화 변경 흐름에 예산 처리 추가. U-05의 해소가 아니라 새 결정이다. |
| R-31 | `free_cash`의 목표 차감은 목표를 구현하기 전에는 생략한다. | 목표 기능을 구현하지 않는 동안만. 계약은 goals R-35. | `earmarked_for_goals = 0`. |
