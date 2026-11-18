---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/goal.rb
  - app/models/goal_account.rb
  - app/models/goal_pledge.rb
  - app/models/goal_pledge/reconciler.rb
  - app/models/goal/currency_converter.rb
  - app/models/goal/withdrawal_detector.rb
  - app/controllers/goals_controller.rb
  - app/controllers/goal_pledges_controller.rb
  - app/controllers/plans_controller.rb
  - app/controllers/concerns/preview_gateable.rb
  - app/controllers/concerns/localize.rb
  - app/jobs/sweep_expired_goal_pledges_job.rb
  - app/jobs/refresh_maintained_goal_targets_job.rb
  - app/jobs/generate_insights_job.rb
  - app/models/assistant.rb
  - app/controllers/mcp_controller.rb
  - app/models/assistant/function/create_goal.rb
  - app/models/insight/generators/maintained_goal_depleted_generator.rb
  - app/models/insight/generator.rb
  - app/models/account.rb
  - app/models/account/provider_import_adapter.rb
  - app/models/account/reconciliation_manager.rb
  - app/models/family.rb
  - app/models/budget.rb
  - app/models/user.rb
  - app/models/income_statement.rb
  - app/models/income_statement/family_stats.rb
  - app/helpers/application_helper.rb
  - app/helpers/goals_helper.rb
  - app/components/goals/lifecycle_panel_component.rb
  - app/components/goals/funding_accounts_breakdown_component.rb
  - app/views/goals/_form.html.erb
  - app/views/goals/show.html.erb
  - app/views/goals/consume.html.erb
  - app/views/goal_pledges/new.html.erb
  - app/views/plans/show.html.erb
  - app/views/plans/_goals_card.html.erb
  - app/views/plans/_budget_card.html.erb
  - app/views/budgets/show.html.erb
  - app/views/budgets/_available_cash.html.erb
  - app/javascript/controllers/goal_form_controller.js
  - app/javascript/controllers/goal_pledge_preview_controller.js
  - config/routes.rb
  - config/schedule.yml
  - config/currencies.yml
  - config/application.rb
  - db/schema.rb
  - db/migrate/20260511100000_create_goals.rb
  - docs/llm-guides/goals.md
  - docs/llm-guides/gating-a-preview-feature.md
depends:
  - ./budgets.md
  - ./account-balances.md
  - ./transactions.md
  - ./money-currency-rules.md
  - ./provider-import-adapter.md
  - ./recurring-transactions.md
status: draft
---

# 목표(Goal)와 Plan 화면

> 가족(family)이 저축 목표(금액, 선택적 기한, 연결 계정, 계정별 earmark)를 만들면, 연결 계정의 잔액에서 목표가 차지하는 몫으로 진행률·필요 월 저축액·상태(on track, behind 등)를 계산하고, 사용자가 적립 약속(pledge)을 기록하면 이후 들어온 거래나 잔액 갱신을 규칙(날짜 ±5일, 금액 ±0.50 또는 1%)으로 자동 대조하며, 예산과 목표를 한 화면(Plan)에 묶고, 목표가 현금 계정에서 차지한 금액을 예산의 free cash 계산에 내주는 규칙을 정의한다.

이 문서에서 쓰는 이름은 다음과 같다. 목표는 `Goal` 행 하나다. 연결(link)은 목표와 계정을 잇는 `GoalAccount` 행이다. earmark는 연결의 `allocated_amount`다. 이 값이 null인 연결을 "whole-account 연결"(계정 잔액 전체를 요구하는 연결)이라 부르고, 값이 있는 연결을 "고정 earmark"라 부른다. backing은 목표가 계정 하나에서 가져가는 몫이다(R-10). pool은 한 가족의 released 상태가 아닌 목표들이 한 계정에 건 고정 earmark 모음이다. released 상태는 `archived`와 `completed`다(코드의 `RELEASED_STATES`). pledge는 "곧 이 계정에 이 금액을 넣겠다"는 약속 행(`GoalPledge`)이고, 대조(reconcile)는 들어온 거래나 잔액 갱신을 열린 pledge와 맞춰 보는 일이다. 목표 종류(`kind`)는 `one_off`(한 번 달성하고 닫는 목표)와 `maintained`(유지할 하한선, 코드 주석의 reserve, 이 문서는 "유지형 목표"라 쓴다)다. Plan 화면은 `/plan`이고, 예산 카드와 목표 카드를 나란히 놓는 요약 화면이다. 목표와 Plan은 모두 사용자별 preview 플래그 뒤에 있다(R-01).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

preview 플래그를 켠 한국 가족(`currency = KRW`)이 "결혼 자금" 목표를 쓰는 대표 흐름이다. 오늘은 2026-11-18이다. 기준은 1.4다.

1. 사용자가 목표를 만든다. 이름, 목표 금액 10,000,000, 기한 2027-03-18, 연결할 계정(예금 계정 A, 잔액 3,500,000)과 선택적 earmark를 낸다. 서버는 통화를 가족 통화(KRW)로 정하고 연결 계정이 하나 이상인지, 가족 계정인지, 예금·투자·암호화폐 계정인지 검사한다(R-04~R-07).
2. 목표 화면을 열 때마다 서버가 계산한다. 계정에서 목표의 몫(backing)을 구하고(R-10), 환산해 합산한 `current_balance`(R-11)로 남은 금액·진행률(R-13)과 필요 월 저축액(R-14)을 구한다. 최근 90일 순유입을 3으로 나눈 pace(R-15)와 비교해 `on_track`/`behind` 같은 status를 정한다(R-16). 위 값으로는 backing 3,500,000, 남은 6,500,000, 진행률 35, 필요 월액 1,625,000, pace 1,500,000이므로 `behind`다(T-06~T-09).
3. 사용자가 pledge를 기록한다(금액 500,000, 계정 A). 서버는 pledge를 `open`으로 저장하고 7일 뒤 만료 시각을 둔다(R-24~R-26).
4. 계정 A가 연동 계정이고 그 provider가 `import_transaction`을 거치면(어댑터를 우회하는 provider는 대조되지 않는다, 예 Kraken, R-27), 다음 동기화에서 입금 거래가 들어올 때 대조기가 열린 pledge를 날짜·금액 허용 오차로 맞춰 보고, 맞으면 pledge를 `matched`로 바꾸고 거래에 `extra.goal.pledge_id`를 찍는다(R-27~R-30). 수동 계정이면 사용자가 잔액을 갱신(reconciliation)할 때 잔액 증가분으로 대조한다. 대조는 목표의 금액·진행률을 바꾸지 않는다(R-31).
5. 15분마다 도는 job이 만료 시각이 지난 열린 pledge를 `expired`로 바꾼다(R-26).
6. 사용자가 일부를 실제로 써 버렸다고 기록하면(consume) 그만큼 earmark가 줄고 `consumed_amount`가 늘어 진행률이 유지된다(R-22). 목표를 완료하면 그 시점의 backing이 `completed_amount`로 얼고 earmark가 풀린다(R-20, R-21).
7. Plan 화면은 이번 기간 예산 카드와 활성 목표 카드를 함께 보여 주고(R-32, R-33), 예산 화면의 사용 가능 현금 패널은 목표가 현금 계정에서 차지한 금액을 뺀 free cash를 보여 준다(R-35).

### 1.2 범위·통합 지점

- 제공: 목표 CRUD와 연결 계정·earmark 관리, 공유 계정의 backing 계산(pool, pro-rata), 환산 규칙, 진행률·필요 월액·pace·status 계산, 상태 전이(active, paused, completed, archived)와 완료 시 동결, 사용(consume) 기록과 미귀속 출금 후보, 유지형 목표와 "N개월치 지출" 목표 금액 갱신, pledge 생성·연장·취소·만료·자동 대조, Plan 화면과 목표 목록 KPI, 예산 free cash에 내주는 `Goal#backing_within` 계약, AI 어시스턴트 `create_goal`, 유지형 목표 고갈 인사이트.
- 제외:
  - 권한(Family 테넌시, `AccountShare`, `accessible_accounts`)의 판정. 사용 지점만 R-03, R-06, R-22, R-24에 쓴다(U-01).
  - 예산 계산 자체(남은 금액, 기간, 이월). Plan 화면의 예산 카드는 [budgets](./budgets.md) R-01~R-06, R-18~R-20, R-33이 정한 값을 그대로 쓴다. 이 문서는 사용 지점만 R-32에 쓴다.
  - 지출·소득 집계(`IncomeStatement`)의 내부. 유지형 목표의 월 지출 중앙값은 `median_expense(interval: "month")`를 쓰고, 그 규칙은 [budgets](./budgets.md) R-21이다(R-19).
  - 잔액 시계열 빌더(`Balance::ChartSeriesBuilder`)와 차트 렌더링(D3), 색상 팔레트, i18n 문구, 도넛·진행 링 모양, 목록 필터 칩(`goals_filter_controller.js`), 아바타. 차트에 넘기는 값의 정의는 R-17에 쓴다.
  - 온보딩의 `users.goals`(사용자가 고른 사용 목적 문자열 배열, `users_controller.rb`, `onboardings/goals.html.erb`)는 이 기능과 이름만 같다.
  - 구독 요금제(`subscriptions/_plan_choice`), 시세 제공자 요금제(`security/plan_restriction_tracker.rb`), AI 라우팅(`ai/plan.rb`)은 이름만 같고 이 기능이 아니다(2.1에서 확인한 범위).
  - 정기 거래의 청구서·급여 계획(`bills`, `paycheck_planner`)은 Plan 화면에 연결되어 있지 않다. 목표 코드는 `month_start_day`(월급일 기준 예산 기간)를 읽지 않는다(2.1).
- 외부 의존·선행 계약: PostgreSQL(`pg_advisory_xact_lock`, jsonb 키 조회, partial unique index). 환율은 `ExchangeRate.find_or_fetch_rate`([money-currency-rules](./money-currency-rules.md) R-23, R-25). 거래의 `excluded`·보류·분할 원본 판정은 [transactions](./transactions.md) R-16, R-22~R-30, 보류 판정은 [provider-import-adapter](./provider-import-adapter.md) R-30. 계정 `balance`, `balance_type`, `visible`, `balances.net_market_flows`는 [account-balances](./account-balances.md) R-02, R-09, R-27이고 Entry 금액 부호(유입 음수)는 [money-currency-rules](./money-currency-rules.md) R-36이다. 요청·동기화가 쓰는 시간대는 [recurring-transactions](./recurring-transactions.md) R-30과 R-39다. 호출자가 제공하는 것은 현재 사용자·가족, 접근 가능한 계정 판정, 환율 저장소·제공자, 비동기 job 실행기(15분 주기와 월 1회 cron)다.
- 소유 상태·부작용: `goals`, `goal_accounts`, `goal_pledges` 세 테이블과 `transactions.extra["goal"]`의 두 키(`pledge_id`, `consumed_goal_id`). 대조기가 거래의 `extra`를 쓴다(R-30). 유지형 목표의 job이 `goals.target_amount`를 다시 쓴다(R-19). 목표 화면을 열어도 목표 세 테이블에는 쓰지 않는다. 다만 환율이 없으면 `DebugLogEntry`를 쓰고(`goal.rb:563-570`), 환율 조회가 제공자에서 새로 받으면 `exchange_rates` 행을 저장한다(`exchange_rate/provided.rb:44-50`, R-12). Plan 화면은 예산 행을 만들고 갱신할 수 있다(R-32).

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Goal` | 행 | `family_id`(필수, 가족 삭제 시 cascade), `name`(필수, 255자 이하), `target_amount`(decimal(19,4), 필수, 0 초과), `currency`(필수, 생성 때 가족 통화로 정해지고 연결이 생긴 뒤 변경 불가), `target_date`(date, 선택, 유지형은 항상 null), `color`(`#RRGGBB` 형식, 선택), `icon`(허용 목록 안, 선택), `notes`(text), `state`(`active`·`paused`·`completed`·`archived`, 기본 `active`), `kind`(`one_off`·`maintained`, 기본 `one_off`), `target_mode`(`fixed`·`months_of_expenses`, 기본 `fixed`), `target_months`(정수 1 이상, 선택), `progress_basis`(`balance`·`contributions`, 기본 `balance`), `consumed_amount`(decimal(19,4), 0 이상, 기본 0), `completed_amount`(decimal(19,4), null 가능, 완료 때 얼린 값), `completed_at`. DB check 제약이 `target_amount > 0`, `consumed_amount >= 0`, enum 4개, 이름 길이를 한 번 더 막는다(C-23). |
| `GoalAccount` (연결) | 행 | `goal_id`(필수, cascade), `account_id`(필수, 계정 삭제는 DB가 restrict), `allocated_amount`(decimal(19,4), null이면 whole-account 연결, 값이 있으면 0 이상, 계정 통화 단위). `(goal_id, account_id)` 유일. |
| `GoalPledge` | 행 | `goal_id`, `account_id`(필수), `amount`(decimal(19,4), 0 초과, 목표 통화 단위), `currency`(필수, 목표 통화와 같아야 함), `kind`(`transfer`·`manual_save`), `status`(`open`·`matched`·`cancelled`·`expired`, 기본 `open`), `expires_at`(필수), `matched_transaction_id`(거래 삭제 시 DB가 null로 바꿈). `matched_transaction_id`가 null이 아닌 행끼리는 유일(partial unique index). |
| `transactions.extra["goal"]` | jsonb 중첩 | `pledge_id`(이 거래를 차지한 pledge id), `consumed_goal_id`(이 출금을 사용으로 기록한 목표 id). `pledge_id`는 값이 있는 거래끼리 유일(partial unique index, C-23). `consumed_goal_id`에는 DB 제약이 없다. |
| 가족 필드 | 필드 | `currency`(목표 통화의 기본값, `primary_currency_code`는 정규화한 값이거나 없으면 `USD`), `timezone`(R-39). |
| preview 플래그 | 필드 | `users.preferences["preview_features_enabled"]`가 `true`일 때만 켜짐. 기본 꺼짐. |

**연산(웹, 전부 preview 게이트)**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| Plan 화면 | `GET /plan`(선택 `owner`) | R-32 |
| 목표 목록 | `GET /goals` | 활성·완료·보관 구분, KPI(R-34) |
| 목표 만들기 | `POST /goals`, `goal[name, target_amount, target_date, color, icon, notes, kind, target_mode, target_months]`, `goal[account_ids][]`, `goal[allocations][<account_id>]` | R-04~R-07. `currency`는 받지 않는다. 폼은 모든 후보 계정마다 `allocations` 칸을 보내고 빈 칸은 whole-account 연결이다. |
| 목표 수정 | `PATCH /goals/:id`, 같은 파라미터 | `account_ids` 키가 요청에 아예 없으면 연결을 건드리지 않는다(R-06). 폼은 `kind`·`target_mode`·`target_months`를 수정 때도 보낸다. |
| 목표 삭제 | `DELETE /goals/:id` | 어느 상태에서도 가능(R-09) |
| 상태 전이 | `PATCH /goals/:id/{pause,resume,complete,archive,unarchive,reopen}` | R-20, R-21 |
| 사용 기록 | `GET/POST /goals/:id/consume`, `amount`, `account_id`(선택), `transaction_id`(선택) | R-22. 계정이 하나뿐이면 `account_id`를 보내지 않는다. 미귀속 출금 버튼은 `transaction_id`만 보낸다. |
| pledge 만들기 | `GET /goals/:goal_id/pledges/new`(선택 `amount`, `account_id`), `POST /goals/:goal_id/pledges`, `goal_pledge[amount]`, `goal_pledge[account_id]` | R-24. Turbo frame이 아닌 GET은 목표 화면으로 redirect한다. |
| pledge 연장·취소 | `PATCH .../pledges/:id/renew`, `DELETE .../pledges/:id` | R-26. DELETE는 행을 지우지 않고 취소한다. |
| 어시스턴트 | `create_goal`(`name`, `target_amount`, `target_date`, `linked_account_names`, `earmarks`, `notes`) | R-37 |
| 내부 계약 | 목표 인스턴스 메서드 `goal.backing_within(account_ids, currency:)` → decimal | 예산 free cash 계산이 부른다(R-35) |
| job | `SweepExpiredGoalPledgesJob`(15분마다), `RefreshMaintainedGoalTargetsJob`(매월 1일 03:00) | R-26, R-19 |

### 1.4 행동 규칙과 남은 질문

**게이트·범위**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 목표·pledge·Plan 요청 | `GoalsController`와 `GoalPledgesController`는 모든 action 앞에서 현재 사용자의 `preferences["preview_features_enabled"] == true`를 검사하고, 아니면 루트 경로로 redirect하며 alert(`preview.not_enabled`)를 남긴다. `PlansController`는 같은 검사에 실패하면 예산 경로(`/budgets`)로 redirect하고 flash는 없다. 플래그는 사용자 단위다. 같은 가족의 다른 구성원이 켜도 이 사용자에게는 꺼져 있다. 사이드바 항목은 플래그가 있으면 Plan(`/plan`, 목록·상세 화면에서도 켜진 상태), 없으면 예산 항목이다. 라우트는 항상 열려 있고 요청마다 판정한다. 예산 화면의 사용 가능 현금 패널도 본인 플래그로 판정한다([budgets](./budgets.md) R-31). | 코드 확인 |
| R-02 | 게이트가 없는 경로 | (a) pledge 대조 hook(R-27)과 만료 job은 사용자 플래그와 무관하게 돈다. (b) 유지형 목표 금액 갱신 job(R-19)도 같다. (c) AI 어시스턴트의 `create_goal`은 기본 함수 목록에 들어 있고 preview 전용 목록에 없으므로(`Assistant.function_classes`) 플래그가 꺼진 사용자의 어시스턴트도 목표를 만들 수 있다. 가족 설정 변경 도구 목록(`FAMILY_CONFIG_FUNCTION_CLASSES`, guest에게서 빼는 목록)에도 없어 guest도 부를 수 있다(`assistant.rb:40-47`, `:78`, `:106`). 만들어진 목표는 플래그가 켜져야 UI에서 보인다. MCP 엔드포인트도 같은 함수 목록을 `tools/list`와 호출에 쓰므로(`mcp_controller.rb:99`, `:118`) `create_goal`이 외부 에이전트에도 열린다. (d) 인사이트 생성은 가족에 플래그를 켠 구성원이 있을 때만 돈다(R-38). REST API(`api/v1`)에는 목표 엔드포인트가 없다(2.1의 검색 범위). | 코드 확인(부재는 검색 범위 안) |
| R-03 | 목표·pledge 조회 | 목표는 `Current.family.goals`에서만 찾는다. 다른 가족의 id이거나 없는 id면 목표 목록으로 redirect하며 alert(`goals.errors.not_found`)를 남긴다(pledge 컨트롤러도 같다). 목표 화면·집계는 연결 계정이 현재 사용자에게 접근 가능한지 따지지 않고 가족 전체 계정 기준으로 계산한다. 접근 판정은 연결 계정 후보(R-06), 사용 기록의 계정(R-22)과 미귀속 출금(R-23)에서만 쓴다(U-01). | 코드 확인 |

**목표 생성·수정·삭제**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-04 | 목표 저장(`Goal` 검증) | 허용 파라미터는 `name`, `target_amount`, `target_date`, `color`, `icon`, `notes`, `kind`, `target_mode`, `target_months`뿐이다(`currency`, `state`, `progress_basis`, `consumed_amount`는 요청으로 받지 않는다). 새 목표의 통화는 요청이 아니라 가족의 `primary_currency_code`다. 검증: 이름 필수·255자 이하, `target_amount` 필수·0 초과, `currency` 필수, `color`는 `#`과 16진수 6자리, `icon`은 `Category.icon_codes` 안, `kind`는 2값, `target_mode`는 2값, `target_months`는 1 이상 정수 또는 null, `target_mode = months_of_expenses`는 `kind = maintained`와 `target_months` 값이 함께 있어야 하고(아니면 오류), `fixed`에는 `target_months`가 없어야 한다. 유지형이면 저장 전에 `target_date`를 null로 지운다(오류 없이 정규화). 오류가 있으면 새 화면·수정 화면을 422로 다시 그린다. | 코드 확인 |
| R-05 | 연결(`GoalAccount`)의 검증 | 목표는 연결이 하나 이상이어야 한다(삭제 표시된 연결은 세지 않는다). 연결 계정의 `accountable_type`은 `Depository`·`Investment`·`Crypto`만 허용한다(`FUNDABLE_ACCOUNT_TYPES`). 계정은 목표와 같은 가족이어야 한다. 한 목표에 같은 계정을 두 번 연결할 수 없다. `allocated_amount`는 null 또는 0 이상이다(0은 whole-account가 아니라 몫 0의 고정 earmark다). 목표 통화는 연결이 하나라도 저장된 뒤에는 바꿀 수 없다. 계정의 상태(`active`, `disabled` 등)와 `exclude_from_reports`는 연결 검증에도, 이후의 금액 계산에도 쓰지 않는다. | 코드 확인 |
| R-06 | 만들기·수정 요청의 계정 처리(`GoalsController`) | 연결 후보는 `Current.user.accessible_accounts` 중 `Depository`·`Investment`·`Crypto`이고 `visible`(draft·active)인 계정이다. 요청의 `account_ids` 중 이 후보에 없는 id는 오류 없이 버려진다. 만들기에서 걸러진 뒤 계정이 하나도 없으면 연결 필수 검증이 실패해 422다. 만들기와 수정은 `Goal.transaction` 안에서 한다. 수정에서 `account_ids` 키가 요청에 있으면: 걸러진 결과가 비었을 때 연결 필수 오류로 422(저장 시도 없음)이고, 아니면 (1) 현재 연결 중 현재 사용자가 접근할 수 있는 계정이 새 선택에 없으면 삭제하고(접근할 수 없는 계정의 연결은 선택 칸에 보이지 않으므로 지우지 않는다. 다만 이 판정은 `accessible_accounts` 기준이고 선택 칸은 `visible`(draft·active)만 보여 주므로, 접근은 되지만 `disabled` 같은 visible이 아닌 연결 계정은 체크박스에 나오지 않는다. `account_ids`가 포함된 수정에서는 그 연결이 선택에서 빠진 것으로 보여 조용히 삭제된다, `goals_controller.rb:230-238`), (2) 새 계정은 연결을 만들고, (3) 이미 있는 연결의 `allocated_amount`는 요청에 그 계정의 `allocations` 키가 있을 때만 바꾼다(빈 값은 null, 곧 whole-account로 바뀐다), (4) 목표를 한 번 저장해 모든 검증을 건다. `account_ids` 키가 아예 없는 수정은 속성만 저장한다. 폼의 계정 체크박스는 hidden 필드가 없는 `check_box_tag`라서(`_form.html.erb:154`) 편집 화면에서 체크를 모두 해제하고 저장하면 `account_ids` 키가 오지 않고, 이 경우 연결은 그대로이며 오류도 없다(체크박스가 해제되면 키를 보내지 않는 것은 브라우저·프레임워크 동작이라 추론). `allocations` 값은 공백을 지우고 빈 문자열이면 null이다. | 코드 확인 / 추론(체크박스 제출) |
| R-07 | whole-account 연결의 배타성 | whole-account 연결은 그 계정 잔액 전체를 요구하므로 같은 가족의 released 상태가 아닌 다른 목표가 같은 계정에 whole-account 연결을 가질 수 없다(오류 `account_already_fully_earmarked`, 충돌 목표 이름 포함). 새 행이거나 `allocated_amount`·`account_id`·`goal_id`가 바뀌는 행에만 검사한다. 이전부터 겹쳐 있던 행은 목표 이름 변경 같은 저장을 막지 않는다. 검사 전에 계정별 transaction 범위 advisory lock을 계정 id 오름차순으로 잡는다(두 요청이 동시에 통과하는 것을 막고 교착을 피한다). released 상태(`archived`, `completed`)의 목표를 `unarchive`나 `reopen`으로 비released 상태(`active`)로 되돌릴 때도 같은 검사를 그 목표의 whole-account 계정 전부에 건다(검증 오류 `whole_account_conflict_on_restore`, 충돌 목표·계정 이름 포함). 이 검사는 고정 earmark에는 없다. 고정 earmark 합이 계정 잔액을 넘는 것은 허용되고 R-10의 pro-rata로 처리한다. | 코드 확인 |
| R-08 | 계정 삭제와 연결이 사라진 목표 | `Account`는 삭제될 때 자기 연결과 pledge를 지운다(`dependent: :destroy`, DB는 연결·pledge의 계정 FK를 restrict로 둔다). 연결이 모두 사라진 목표는 지워지지 않고 남는다. 이 목표는 backing 0, pace 0이다. 연결 필수 검증이 모든 저장에 걸리므로 이 목표의 상태 전이 저장은 실패하고(R-20), 수정 화면에서 계정을 다시 고르면 복구된다. | 코드 확인 |
| R-09 | 목표 삭제 | 어느 상태에서도 삭제할 수 있다. 목표의 연결과 pledge가 함께 지워지고, 이미 `matched`인 pledge가 지워질 때 그 거래의 `extra["goal"]["pledge_id"]`가 자기 id일 때만 지운다(`goal` 키가 비면 그것도 지운다). 계정·잔액·거래는 지워지지 않는다. `extra["goal"]["consumed_goal_id"]`는 목표가 지워져도, 목표를 `reopen`해도 지워지지 않는다. 그 출금은 이후 어느 목표에서도 사용 기록에 쓸 수 없고(R-22 `transaction_already_claimed`) 미귀속 출금 후보에서도 계속 빠진다(R-23). | 코드 확인(`consumed_goal_id`를 지우는 코드는 2.1의 검색 범위에서 없음) |

**계산: backing, 환산, 진행률**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | 목표의 한 계정 backing(`backing_share_for`) | 계정 통화 단위로 먼저 계산한다. 기준액 `base`는 `progress_basis = balance`면 `account.balance`, `contributions`면 `max(account.balance − Σ balances.net_market_flows, 0)`이다(투자·암호화폐 계정이 연결된 목표는 처음 저장할 때 `balance`에서 `contributions`로 바뀌고, 이후 요청으로 바꾸는 경로는 없다). `base <= 0`이면 backing 0이다. `others_fixed`는 같은 가족의 released 상태가 아닌 다른 목표들이 이 계정에 건 고정 earmark의 합이다(whole-account 연결은 0으로 센다). 이 목표의 연결이 고정 earmark `mine`이면(0도 해당) `total = others_fixed + mine`이고 `total > base`이면 `round(mine × base / total, 4)`, 아니면 `mine`이다. whole-account 연결이면 `max(base − others_fixed, 0)`이다. 이 목표 자신의 earmark는 자기 연결에서 읽으므로 이 목표가 released 상태여도 값이 나온다(pool에서는 빠진다). 결과: 한 계정에서 고정 earmark들의 backing 합은 `base`를 넘지 않는다. | 코드 확인 |
| R-11 | 목표의 금액 합계(`current_balance`, `market_value_money`, `backing_within`) | `completed_amount`가 있으면 그 값을 그대로 돌려준다(상태가 `completed`가 아니어도 값이 있으면 쓴다). 없으면 연결 계정 전부(계정 상태와 무관)의 backing(R-10)을 R-12로 목표 통화로 환산해 더한다. `market_value_money`는 같은 계산을 `progress_basis`와 무관하게 `balance` 기준으로 한 값이다. `backing_within(account_ids, currency:)`는 연결 계정 중 `account_ids`에 속한 것만 R-10의 backing(진행 기준·pool 반영)을 구해 `currency`(기본은 목표 통화)로 환산해 더한 decimal이다. `completed_amount`는 쓰지 않는다. 환율이 없는 계정은 0으로 센다. | 코드 확인 |
| R-12 | 환산(`Goal::CurrencyConverter`, `convert_money`, `convert_money!`) | 같은 통화는 환율 1이고 금액 0은 환율 조회 없이 0이다. 환율은 `find_or_fetch_rate(from, to, date)`이고 없거나 0 이하이면 `ConversionError`다(1:1로 대신하지 않는다). 같은 변환기는 `(from, to, date)`별로 결과(없음 포함)를 기억해 한 화면 안에서 제공자를 반복 호출하지 않는다. 읽기 경로(`convert_money`)는 오류를 0으로 바꾸고 그 통화 코드를 목표의 `missing_exchange_rate_currencies`에 모은다(가족·통화쌍별로 하루 한 번 `DebugLogEntry` 경고를 남긴다). 쓰기 경로(`convert_money!`: 완료 동결, pledge 대조, 사용 기록)는 오류를 그대로 던진다. 날짜: 잔액·pace·유입은 오늘 환율, pledge 대조와 사용 기록은 거래 날짜의 환율이다. 화면은 알려진 부분 합계에 "환율 없음" 경고를 붙인다(`currency_conversion_incomplete?`가 backing, pace, market value를 먼저 계산한 뒤 모은 통화가 있는지 본다). | 코드 확인 |
| R-13 | 진행률(`remaining_amount`, `progress_amount`, `progress_percent`) | `remaining_amount = max(target_amount − current_balance − consumed_amount, 0)`. `progress_amount = current_balance + consumed_amount`. `progress_percent`: 상태가 `completed`이면 100, `target_amount`가 0이면 0, `remaining_amount`가 0이면 100, 아니면 `floor((current_balance + consumed_amount) / target_amount × 100)`을 0~99로 자른다. 따라서 목표를 채우기 전에는 99를 넘지 않는다. 사용 기록(R-22)이 진행에 포함되므로 쓴 돈이 진행률을 깎지 않는다. | 코드 확인 |
| R-14 | 필요 월 저축액(`months_remaining`, `monthly_target_amount`) | `target_date`가 없으면 `months_remaining`과 월 저축액은 nil이다. 있으면 `months_remaining = max((target_date − 오늘) 일수 / 30.0, 0.0)`(일 단위, 달력월이 아니다). `monthly_target_amount`는 `months_remaining`이 0이면 `remaining_amount` 그대로, 아니면 `ceil(remaining_amount / months_remaining, 소수 2자리)`다. 기한이 지난 목표도 nil이 아니라 남은 금액 전부다. 목표 생성 폼의 "월 N 저축" 안내 문구는 브라우저에서 `ceil(금액 / ((기한 − 지금) / 30.44일))`로 따로 계산하고 정수로 올리므로(30.44 사용, 서버는 30.0) 서버 값과 다를 수 있다. | 코드 확인 |

**계산: pace와 status**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | pace(`Goal.pace_for`, `Goal.balance_pace_for`, `pace`, `pace_measurable?`) | 연결 계정마다 아래 네 경로 중 앞에서 맞는 하나로 정한다(가족의 모든 목표 연결 계정을 한 번에 읽어 목표마다 쿼리하지 않는다). 거래 합은 계정 전체에 대한 것이고 earmark로 나누지 않는다. **1 거래**: 최근 90일(`오늘 − 90일`~오늘, 양끝 포함)에 `excluded = false`이고 보류가 아닌 거래가 하나라도 있으면, 그 거래들의 `Entry.amount`를 통화별로 합해(거래 `kind` 제한 없음이라 이체도 센다. Valuation은 조인 모양 때문에 빠지고, 분할 원본은 `excluded = true`로 저장되므로 `excluded = false` 조건으로 빠진다, [transactions](./transactions.md) R-16, R-23) 오늘 환율로 목표 통화로 환산한 값을 쓴다. **2 잔액**: 1이 아니고 최근 365일에 `reconciliation` 또는 `current_anchor` Valuation이 있고 1년 전 날짜 이전의 가장 늦은 balances 행(계정 통화)이 있으면, `(오늘 balance − 그 행의 end_balance + 제외 거래 합) / 12`다. 제외 거래 합은 같은 구간에서 `excluded = true`·보류 아님·분할 원본 아님인 거래를 entry 날짜 환율(거래의 `exchange_rate` 우선)로 계정 통화로 바꿔 더한 값이다(환율이 없는 항목은 건너뛴다). `contributions` 기준이면 구간의 `net_market_flows` 합을 더 뺀다. 1년 전 행이 없으면 이 경로가 아니다(0으로 읽지 않는다). **3 휴면**: 1·2가 아니고 Valuation(위 종류)이 최근 365일에 없으며, 제외도 보류도 아닌 거래가 날짜 제한 없이 하나라도 있으면 측정된 0이다. **4 미측정**: 그 밖(개설 잔액만 있음, 최근 Valuation은 있는데 1년 전 행이 없음, Valuation이 모두 1년보다 오래됨 등). `pace`는 경로 1에서 `−(환산한 Entry.amount 합) / 3`(유입이 음수이므로 부호를 뒤집는다), 경로 2의 값을 더하고, 경로 3·4는 0을 더해 소수 2자리로 반올림한 값이다. `pace_measurable?`은 모든 연결 계정이 1·2·3 중 하나일 때만 true다(연결이 없으면 true, pace 0). | 코드 확인 |
| R-16 | status(`status`, `display_status`, `behind_pace?`, `needs_attention?`) | 유지형이면 `remaining_amount`가 0일 때 `funded`, 아니면 `depleted`다. 그 밖에는 위에서부터: 상태가 `completed`이거나 `remaining_amount`가 0이면 `reached`, `target_date`가 없으면 `no_target_date`, `pace_measurable?`이 false면 `pace_unknown`, `monthly_target_amount <= pace`이면 `on_track`, 아니면 `behind`다. `display_status`는 상태가 `archived`·`paused`·`completed`이면 그 상태(우선순위 이 순서)이고 아니면 `status`다. 보관·일시정지 목표도 `status` 값 자체는 계산된다. `behind_pace?`는 `paused`가 아니고 유지형이 아니고 `status = behind`일 때만 true다(일시정지는 pace를 멈춘 것으로 본다). `needs_attention?`은 `status`가 `behind` 또는 `depleted`다. | 코드 확인 |
| R-17 | 파생 표시값(`months_of_runway`, `catch_up_delta_money`, `projection_end_amount`, `projection_payload`, `to_donut_segments_json`, 예상 도달 월) | `months_of_runway`는 `target_date`가 없고 `pace_measurable?`이고 `pace > 0`일 때만 `round(current_balance / pace, 1)`, 아니면 nil이다. `catch_up_delta = max(monthly_target_amount − pace − Σ(열린 pledge amount), 0)`이고 월 저축액이 nil이면 0이다(`Σ`는 DB에서 `status = open`이고 `expires_at >= 지금`인 pledge의 합, 목표 통화). `projection_end_amount`는 `target_date`가 없거나 pace 미측정이면 `current_balance`, 아니면 `max(current_balance, current_balance + pace × max((target_date − 오늘) / 30.44, 0))`이다(`consumed_amount`를 더하지 않는다). 예상 도달 월은 `ceil(remaining_amount / pace)`개월을 오늘에 더한 달이고 pace가 양수일 때만 나온다. `projection_payload`(차트가 받는 값)는 최근 90일 목표 통화 잔액 시계열을 `min(current_balance / Σ(연결 계정 balance 환산 합), 1)`로 스케일한 저장선(합이 양수가 아니면 비율 0), 목표 금액·기한, `current_amount = current_balance`, `avg_monthly = pace`(pace 미측정이면 nil), `required_monthly`, `status`, `projection_end_value`, 부족액 라벨(미측정이면 없음, `target_amount > projection_end`일 때 `target_amount − projection_end`)을 담는다. 시리즈 계산이 환율 오류를 만나면 빈 시계열로 대신하고 모은 통화에 더한다. 다른 오류는 로그와 오류 추적에 남기고 빈 시계열로 대신한다. 라벨의 K/M 약어(`short_money`)는 절댓값이 1,000,000 이상이면 `M`, 1,000 이상이면 `K`로 소수 1자리(정수면 소수 생략), 그 미만은 천 단위 쉼표 정수다. 한국어 단위(만, 억)는 쓰지 않는다. 링 도넛은 채운 부분 `current_balance`(양수일 때, 목표 색이 없으면 첫 팔레트 색)와 남은 부분 `remaining_amount`(양수일 때)의 두 조각이고 둘 다 0이면 회색 단일 조각이다. | 코드 확인 |
| R-18 | 목표 종류(`kind`) 규칙 | `maintained`: `complete` 이벤트를 막고(R-20), `consume!`을 막고(R-22), `target_date`를 지우고(R-04), 목록 KPI의 on-track 분모에서 빼고(R-34), `behind_pace?`에서 뺀다(R-16). 미귀속 출금 후보도 내지 않는다(R-23). `kind`는 released 상태(DB에 저장된 상태 기준)인 목표에서 바꿀 수 없고(오류 `locked_while_released`), `consumed_amount`가 양수인 목표를 `maintained`로 바꿀 수 없다(오류 `locked_once_consumed`). 반대 방향(`maintained`에서 `one_off`)은 제한이 없다. 목표 금액이 `consumed_amount`보다 작아지는 수정은 오류(`below_consumed`)다. | 코드 확인 |
| R-19 | "N개월치 지출" 목표 금액(`months_of_expenses`) | 대상: `kind = maintained`이고 `target_mode = months_of_expenses`이고 `target_months > 0`. 계산: 가족의 월 지출 중앙값(`IncomeStatement(family, accounts: family.accounts.visible.included_in_reports).median_expense(interval: "month")`, 사용자와 무관한 가족 전체 계정 범위, 가족 통화)을 `m`이라 하면 `target_amount = convert(round(m × target_months, 2), 가족 통화 → 목표 통화).round(2)`다(통화가 같으면 환산 없음, 환산은 오늘 환율). `m <= 0`이거나 환율이 없거나 결과가 양수가 아니면 계산 불가(nil)다. 중앙값의 집계 규칙(달력월 기준, 이력 전체, 거래 포함 조건)은 [budgets](./budgets.md) R-21이다. 실행 시점: (a) 이 모드의 목표를 만들 때, 그리고 `target_months`·`target_mode`·`target_amount`가 바뀔 때 검증 앞에서(사용자가 입력한 `target_amount`를 덮어쓴다. 폼은 이 모드에서 금액 칸을 비활성화해 보내지 않는다), (b) 월 1회 job이 released 상태가 아닌 이 모드의 모든 목표에 `refresh_target_from_expenses!`를 건다(계산 불가이거나 값이 같으면 쓰지 않는다. 쓰다가 검증 오류가 나면 `DebugLogEntry`로 남기고 이전 값을 유지한다). 계산 불가이면 새 목표는 입력값이 없어 금액 필수 검증에서 실패하고, 기존 목표는 이전 `target_amount`가 그대로 남는다. 폼은 계산 가능 여부(`median > 0`이고 환산 결과가 양수)를 미리 알아 계산할 수 없으면 금액 칸을 열어 둔다. 실행 주기는 매월 1일 03:00(cron 식 `0 3 1 * *`)이고 시간대는 `schedule.yml`에 적혀 있지 않다(같은 파일의 다른 항목은 UTC라고 주석, 이 항목은 추론으로 UTC, 한국 시각 정오). | 코드 확인 / 추론(cron 시간대) |

**상태 전이와 사용 기록**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 상태 전이 | `pause`: active → paused. `resume`: paused → active. `complete`: active 또는 paused → completed(`one_off`일 때만. 유지형은 허용 전이가 없다). `archive`: active, paused, completed → archived. `unarchive`: archived → active. `reopen`: completed → active. 그 밖의 전이는 컨트롤러가 먼저 막고 alert(`invalid_transition`)와 함께 목표 화면으로 redirect한다. 전이는 저장하면서 모든 검증을 다시 건다. 검증이 실패하면(연결이 없는 목표, 복구 충돌 R-07, 완료 때 환율 없음 R-21) 전이는 일어나지 않고 오류 문장을 alert로 보여 준다(AASM의 bang 이벤트는 저장 실패를 예외가 아닌 `false`로 돌려준다는 가정, 컨트롤러가 반환값을 검사하는 것은 코드 확인, gem 동작은 추론). 성공은 목표 화면으로 redirect하고 notice를 남긴다. `paused`는 pool에 남는다(예약을 풀지 않는다). | 코드 확인 / 추론(AASM 반환값) |
| R-21 | 전이의 부수 효과 | `completed`로 저장될 때: 검증 앞에서 모든 연결 계정의 환산을 엄격하게 시도해 환율이 없으면 오류(`missing_exchange_rate`)로 전이를 거부한다. 저장 뒤 같은 transaction 안에서 `completed_amount = Σ 연결 계정 backing의 엄격 환산`(R-10, 목표가 이미 released이므로 pool에서 빠진 상태의 계산)과 `completed_at = 지금`을 쓴다. 이후 `current_balance`는 이 값(R-11)이고 `progress_percent`는 100이다. 진행률과 무관하게 완료할 수 있다(가드는 `one_off`뿐). released 상태에서 비released 상태로 갈 때(`reopen`, `unarchive`): `completed_amount`와 `completed_at`을 지우고, 지우기 전에 `completed_amount`가 있었으면 `consumed_amount`를 0으로 되돌린다. 완료한 적 없이 보관했다가 되돌린 목표는 `consumed_amount`를 지키고 백킹을 실시간 계산으로 돌린다. 완료 후 보관(`completed` → `archived`)은 `completed_amount`를 그대로 둔다. released 상태로 가는 순간 pool에서 빠져 같은 계정에서 다른 목표의 몫이 커진다(R-10). | 코드 확인 |
| R-22 | 사용 기록(`consume!`) | 사용 기록은 "이 금액을 이 목표가 겨냥한 일에 썼다"는 선언이다. 사전 검사 순서와 이유 코드: 금액 0 이하 `non_positive`; 유지형 `maintained`; 연결이 없음 `no_linked_account`; 계정을 안 줬는데 연결이 둘 이상 `account_required`; 준 계정이 연결이 아님 `account_not_linked`; 환율이 없음 `missing_exchange_rate`(엄격 환산 오류를 변환). 환율 `rate`는 "계정 통화 1단위의 목표 통화 값"(거래에 기대면 그 거래의 날짜, 아니면 오늘)이고 `native = amount / rate`다. 이어서 목표 행을 잠그고 최신 값으로 확인한다: 상태가 active가 아님 `not_active`; `consumed_amount + amount > target_amount` `exceeds_target`; 거래를 줬으면 그 거래의 `extra["goal"]["consumed_goal_id"]`가 이미 있으면(자기 id여도) `transaction_already_claimed`, 없으면 자기 id를 찍는다. 연결이 고정 earmark면 `native > allocated_amount`일 때 `exceeds_earmark`(깎지 않고 거부), 아니면 `allocated_amount −= native`. whole-account 연결이면 `backed`(R-10의 계정 통화 backing)보다 `native`가 클 때 `exceeds_earmark`, 아니면 연결을 고정 earmark로 바꾼다: `allocated_amount = min(backed, (target_amount − consumed_amount − amount) / rate)`. 마지막으로 `consumed_amount += amount`를 저장한다(이 저장의 검증 실패는 전체를 되돌린다). 컨트롤러: 거래 id를 받으면 그 거래의 금액을 목표 통화로(거래 날짜 환율) 바꿔 amount로 삼고 거래의 계정을 쓴다. 거래 id가 없으면 폼의 `amount`와(여러 계정일 때만 보내는) `account_id`를 쓴다. 후보 계정은 현재 사용자가 접근할 수 있는 연결 계정으로 좁히고(그 밖이면 `account_not_linked`), 하나뿐이면 자동으로 고른다. 거래 id가 후보 출금(R-23)에 없으면 `transaction_not_found`다. 거부와 검증 오류는 목표 화면으로 alert와 함께 redirect한다. 사용 기록 UI는 `one_off`이고 active이고 현재 사용자가 접근 가능한 연결의 backing이 양수일 때만 나온다. | 코드 확인 |
| R-23 | 미귀속 출금 후보(`Goal::WithdrawalDetector`) | 목표가 `one_off`이고 active이고 후보 계정이 있을 때만 낸다. 후보 계정은 호출자가 넘긴 `accounts:` 배열이다. 컨트롤러는 현재 사용자가 접근할 수 있는 연결 계정 배열을 항상 넘기고, 그 배열이 비어 있어도 연결 전체로 되돌아가지 않고 후보가 없다(`accounts.empty?`이면 빈 결과). 연결 전체를 쓰는 경우는 `accounts:`를 넘기지 않는 호출(job, test)뿐이다. 후보 거래는 그 계정들의 거래 중 `excluded = false`, 최근 90일(오늘 포함), 보류가 아님, `Entry.amount >= 100`(출금은 양수), `extra["goal"]["consumed_goal_id"]`가 없는 것이고 날짜·id 내림차순이다. 화면은 3건, 사용 기록 조회는 50건까지 본다. 100은 entry 통화로 환산하지 않은 비교다. 원화 거래 100원은 사실상 모든 출금이 후보이고, 외화 거래도 그 통화의 100 이상이면 후보다. | 코드 확인 |

**pledge**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | pledge 만들기 | 입력은 `goal_pledge[amount]`와 `goal_pledge[account_id]`뿐이다. 서버가 `kind`는 계정의 `default_pledge_kind`(R-25), `currency`는 목표 통화, `status`는 `open`, `expires_at`은 지금 + 7일로 정한다. 계정은 그 목표의 연결 계정 중에서만 찾는다(현재 사용자의 접근 권한은 보지 않는다). 연결이 아닌 계정 id이거나 비어 있으면 계정이 없는 상태로 검증이 실패해 422로 폼을 다시 그린다. 검증: `amount` 필수·0 초과, `currency` 필수·목표 통화와 같음, `expires_at` 필수, 계정이 목표에 연결돼 있음, 같은 목표·같은 계정·같은 금액의 `open`이고 `expires_at >= 지금`인 pledge가 이미 있으면 오류(중복 클릭 방지, 만들 때만 검사). 목표의 `state`(paused, completed, archived)나 `kind`는 보지 않는다. UI는 active이고 `reached`·`funded`가 아닌 목표에만 버튼을 보이지만(목표 화면의 pledge 버튼 조건) 서버는 막지 않는다. 성공은 목표 화면으로 redirect한다. 계정이 없을 때의 "must exist" 검증은 `belongs_to`의 프레임워크 기본(`load_defaults 8.1`)에 기댄다. | 코드 확인 / 추론(belongs_to 필수) |
| R-25 | pledge 종류(`default_pledge_kind`) | 계정이 수동 계정(`account_providers`가 없고 `plaid_account_id`·`simplefin_account_id`도 없음)이고 `balance_type`이 `investment`가 아니면 `manual_save`, 그 밖은 `transfer`다. 투자·암호화폐 계정은 수동이어도 `transfer`다(잔액 증가가 시세 변동일 수 있으므로). 한 목표에 수동 계정과 연동 계정이 섞여 있으면 선택한 계정별로 종류가 정해진다. 종류는 계정 연결 방식이고 거래의 `kind`(예: 이체 종류)와 무관하다. | 코드 확인 |
| R-26 | pledge 생애주기 | `open` 상태에서만 바뀐다. 연장(`extend!`)은 기존 `expires_at`에 7일을 더한다(지금이 아니라 기존 만료 시각 기준, 만료 시각이 지났어도 아직 `open`이면 가능). 취소(`DELETE`)는 `status = cancelled`로 바꾸고 행을 지우지 않는다. 열린 상태가 아니면 둘 다 `NotOpenError`이고 컨트롤러가 alert(`not_open`)로 목표 화면에 redirect한다. 만료 job은 15분마다 `status = open`이고 `expires_at < 지금`인 행을 하나씩 `expired`로 바꾼다(한 행의 실패는 로그와 오류 추적에 남기고 계속한다. 쿼리 단계 실패는 남기고 다시 던진다). `matched`·`cancelled`·`expired`는 끝 상태이고 되돌리는 전이가 없다. 목표 화면과 카드가 보여 주는 "열린 pledge"는 `open`이고 `expires_at >= 지금`인 것이다. 남은 일수 `days_left`는 `open`일 때 `ceil((expires_at − 지금) / 1일)`을 0 이상으로 자른 값이다. | 코드 확인 |
| R-27 | 대조 실행 지점 | 대조기를 부르는 코드는 두 곳뿐이다. (a) `Account::ProviderImportAdapter#import_transaction`이 거래 entry를 저장한 뒤, 들어온 거래가 보류가 아니고 그 계정이 어떤 목표에든 연결돼 있을 때(어댑터 인스턴스마다 한 번 조회해 기억). 이미 있던 entry가 보호 상태(제외, 사용자 수정, import 잠금)면 어댑터가 일찍 돌아오므로 대조하지 않는다. 새 거래가 보호 상태인 기존 수동·CSV 거래를 중복으로 판정해 연결만 하고 돌아오는 경로(`provider_import_adapter.rb:128-132`의 `return duplicate`)도 같다. 사용자가 직접 입력한 거래·CSV import 거래는 어댑터를 거치지 않아 대조하지 않는다. 어댑터를 우회하는 provider 경로도 있다. `kraken_account/ledger_processor.rb:180-192`와 `:457`은 `account.entries.create!`로 entry를 직접 만들어 Kraken 거래(입금 포함)는 pledge와 대조되지 않는다(`coinstats_entry/processor.rb`는 `import_transaction`을 쓴다). 그 밖에 우회하는 provider가 있는지는 전수 확인하지 못했다(U-03). (b) `Account::ReconciliationManager#reconcile_balance`가 Valuation을 저장한 뒤(`dry_run`이 아닐 때), 잔액 증가분 `valuation_delta = 새 금액 − 이전 금액`과 함께. 이전 금액은 이 Valuation이 저장돼 있던 금액이 있으면 그것, 없으면 해당 날짜 balances 행의 잔액, 그것도 없으면 0이다. 대조기가 어떤 예외로 실패해도 삼키고 로그와 오류 추적에만 남겨 가져오기·잔액 갱신을 막지 않는다. pledge를 만들기 전에 이미 가져온 거래는 만들 때 소급해서 대조하지 않는다. 같은 거래가 이후 동기화에서 어댑터로 다시 들어오고 보호 상태가 아니어야 대조된다(U-02, U-03). | 코드 확인(우회 경로 전수는 U-03) |
| R-28 | 대조 후보와 순서(`GoalPledge::Reconciler#run`) | entry가 계정이 없거나 `excluded`이거나 Transaction·Valuation이 아니면 아무것도 하지 않는다. Transaction이 이미 `extra["goal"]["pledge_id"]`를 가졌으면 건너뛴다. 후보 pledge는 `account_id`가 같고 `status = open`이고 `kind`가 같고(Valuation은 `manual_save`, Transaction은 `transfer`) `expires_at >= 지금`인 것을 `created_at`, `id` 오름차순으로 훑는다. `matches?`(R-29)가 참인 첫 pledge를 해결하고 거기서 멈춘다(오래된 pledge가 먼저 이긴다). 해결 중 이미 닫혔거나 거래가 다른 pledge에 차지됐거나 검증·유일성 위반이 나면 다음 후보로 넘어간다. | 코드 확인 |
| R-29 | 일치 판정(`GoalPledge#matches?`) | 아래를 모두 만족해야 참이다. (1) pledge가 `open`. (2) entry의 계정이 pledge의 계정. (3) 종류별 방향: Transaction이고 pledge가 `transfer`면 `entry.amount < 0`(유입)이어야 한다(0과 양수는 거부). Valuation이면 계정이 투자 종류가 아니고 `valuation_delta > 0`이어야 한다. (4) 날짜: `earliest = pledge.created_at의 날짜 − 5일`, `latest = max(created_at의 날짜 + 5일, expires_at의 날짜)`이고 `earliest <= entry.date <= latest`(양끝 포함). 연장하면 `latest`가 따라 늘어난다. 날짜는 현재 시간대 기준이다(R-39). (5) 금액: 비교 금액은 Transaction이면 `|entry.amount|`, Valuation이면 `|valuation_delta|`이고 entry 통화(없으면 계정 통화)에서 목표 통화로 entry 날짜 환율로 환산한 값(엄격, 환율이 없으면 거짓)이다. `diff = |환산 금액 − pledge.amount|`일 때 `diff <= 0.50`이거나 `diff / pledge.amount <= 0.01`이면 참이다(둘 중 하나, 목표 통화 단위. 0.50은 통화와 무관한 고정값이다). 거래 `kind`, 이름, 카테고리는 보지 않는다. | 코드 확인 |
| R-30 | pledge 해결(`resolve_with!`, `resolve_with_valuation!`) | Transaction 일치: pledge 행을 잠그고 `open`인지 확인한 뒤 거래 행을 잠그고, 거래의 `extra["goal"]["pledge_id"]`가 다른 pledge의 것이면 `AlreadyClaimedError`, 아니면 `extra["goal"]["pledge_id"] = pledge.id`를 쓰고 pledge를 `matched`로, `matched_transaction_id`를 그 거래로 저장한다. 이중 차지는 DB 유일 인덱스(`goal_pledges.matched_transaction_id`, `transactions.extra.goal.pledge_id`)도 막는다. Valuation 일치: 거래가 없으므로 `status = matched`만 바꾼다(`matched_transaction_id`는 null). 거래가 나중에 삭제되면 DB가 `matched_transaction_id`를 null로 바꾸고 pledge는 `matched`로 남는다. `last_matched_pledge_at`은 `matched` pledge의 거래 entry의 날짜 중 가장 늦은 것이고(Valuation 일치와 거래 삭제 뒤의 pledge는 세지 않는다) pledge의 `updated_at`을 쓰지 않는다. | 코드 확인 |
| R-31 | pledge가 바꾸지 않는 것 | pledge는 목표의 `current_balance`, `progress_percent`, `pace`, `status`, earmark를 바꾸지 않는다. 목표 진행은 계정 잔액에서만 나온다. pledge 금액이 쓰이는 곳은 `catch_up_delta`에서 빼는 값(R-17), 카드·Plan의 "대기 중 pledge" 개수(R-33), 목표 화면의 배너·안내, 생성 모달의 미리보기 문구(브라우저에서 `현재 잔액 + 입력 금액`을 목표와 비교), 마지막 대조 일수 표시다. `matched`로 바뀐 pledge가 있어도 잔액이 실제로 오르기 전에는 진행률이 그대로다. 목표가 completed·archived가 되어도 그 목표의 열린 pledge는 닫히지 않고 시간이 지나 만료될 때까지 대조될 수 있다. | 코드 확인(부재는 검색 범위 안) |

**Plan 화면·집계·연동**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | `GET /plan` | 플래그 검사(R-01) 뒤 (1) 예산: `resolve_budget(Date.current)`로 이번 기간 예산을 구한다. 보는 대상이 본인 또는 household면 `Budget.find_or_bootstrap`을 부르므로 예산 행과 배정 행을 만들고 이월 체인을 다시 계산하는 쓰기가 일어난다([budgets](./budgets.md) R-06, R-07, R-29). 다른 구성원의 공유 예산을 보면 기존 예산만 찾는다(budgets R-33, `owner` 파라미터 포함). 화면은 `editable_by?`, 전환 선택지, 초기화된 예산이면 상위 지출 카테고리 4개(`top_spending_categories`, budgets R-20)를 쓴다. 예산 카드는 총 실적/총 예산, 남은 일수, 사용률을 보여 주고 상태 pill을 `available_to_spend < 0`이면 over, 사용률 90 이상이면 warning, 그 밖이면 good으로 정한다. 이 pill은 Budget 단위 `available_to_spend`·`percent_of_budget_spent`(budgets R-18)를 쓰고, 90은 이 화면에 하드코딩된 값이다(카테고리 단위 `near_limit?`의 90, budgets R-20과 같은 숫자지만 별개의 코드다). (2) 목표: 완료·보관이 아닌 가족의 모든 목표를 R-33의 정렬로 구해 요약(`summary_for`, 가족 통화)과 함께 낸다. 카드에는 처음 5개만 나열하고 합계는 전부다. 환산이 불완전한 목표가 있으면 경고를 하나 붙인다. (3) 연결 가능한 계정 수 = 현재 사용자가 접근 가능한 `Depository`·`Investment`·`Crypto` 중 `visible`인 계정 수이고, 0이면 목표 만들기 대신 계정 추가를 안내한다. (4) "모든 목표" 링크는 가족에 목표가 하나라도 있으면(완료·보관 포함) 나온다. Plan 화면은 목표 쪽으로는 저장하지 않지만 위 (1)의 예산 쓰기를 한다("읽기 전용"이 아니다). | 코드 확인 |
| R-33 | 활성 목표 정렬과 요약(`active_display_sort`, `active_prepared_for`, `summary_for`) | 정렬 키는 `[순위, 이름 소문자]`이고 순위는 일시정지 5, 그 밖은 `status`별 `behind 0, depleted 0, on_track 1, no_target_date 2, pace_unknown 2, funded 3`, 표에 없는 `status`(예: `reached`)는 4다. `summary_for(goals, currency)`: `saved_money = Σ current_balance`(통화가 `currency`와 같은 목표만, `consumed_amount`는 더하지 않는다), `target_money = Σ target_amount`(같은 통화 목표만), `behind_count = behind_pace?`인 목표 수와 `pending_count = Σ 열린 pledge 수`는 통화와 무관하게 전체 목표에서 센다. Plan 카드의 진행 막대는 `saved_money / target_money × 100`을 0~100으로 자른 값이다. | 코드 확인 |
| R-34 | 목표 목록의 KPI(`GoalsController#kpi_payload`, `Family#savings_inflow_windows`) | 활성 목록(완료·보관 제외, R-33 정렬)에 대해: `behind` = `behind_pace?` 수, `needs_this_month = Σ monthly_target_amount`(behind인 목표의, 통화 환산 없이 숫자 그대로 합해 가족 통화로 표기), `on_track` = 일시정지가 아니고 `status = on_track`인 수, `reached`, `no_date`, `paused`, `pace_unknown`(일시정지 아님) 수. `tracked_total`(on-track 분모) = 일시정지·유지형이 아니고 `status`가 `reached`·`no_target_date`·`pace_unknown`이 아닌 목표 수다. 30일 저축 유입: 가족의 모든 목표(상태 불문)에 연결된 계정 중 계정 통화가 가족 통화인 것(계정 종류 제한 없음)의 `excluded = false`·보류 아님 거래의 `Entry.amount` 합에 −1을 곱한 값이다(entry 통화는 보지 않고 환산하지 않는다). 현재 창은 `[오늘 − 30일, 오늘]`, 직전 창은 `[오늘 − 60일, 오늘 − 31일]`(양끝 포함이라 현재 창이 31일, 직전 창이 30일이다). `delta = 현재 − 직전`, `delta_percent = 직전이 0이면 nil, 아니면 round(delta / |직전| × 100, 1)`, 방향은 delta의 부호(up, down, flat)이고 머리 숫자의 부호(순유출이면 "−")와 따로 낸다. | 코드 확인 |
| R-35 | 예산 free cash에 내주는 계약(인스턴스 메서드 `goal.backing_within`, `Budget#earmarked_for_goals`) | 이 규칙이 [budgets](./budgets.md) U-02를 닫는다. 예산의 현금 계정 집합 `ids`(budgets R-31: `Depository`, `visible`, `exclude_from_reports = false`, personal은 소유자 계정, household는 요청 사용자가 접근하는 계정)가 비면 `earmarked_for_goals = 0`이다. 아니면 가족의 released 상태가 아닌 모든 목표(일시정지·유지형 포함)를 R-10의 pool과 함께 준비해, `earmarked_for_goals = Σ goal.backing_within(ids, currency: 예산 통화)`(R-11)이다. 목표는 예산 통화로 직접 환산하므로 목표 통화를 거치지 않는다. 투자·암호화폐 계정에 건 earmark는 `ids`에 없어 빠진다. `free_cash = max(available_cash − earmarked_for_goals, 0)`이다(`available_cash`는 budgets R-31). 환율이 없는 계정의 backing은 0이 되고 그 통화는 예산의 `missing_cash_currencies`에 들어가지 않는다(예산 쪽 환산에서 빠진 통화만 거기 모인다). 현재 사용자가 보지 못하는 계정의 earmark도 `ids`에 속하면 센다. | 코드 확인 |
| R-36 | 계정 earmark 도우미(`Account#goal_earmarked_total`, `free_to_earmark`) | `goal_earmarked_total` = 그 계정에 건 고정 earmark(`allocated_amount`가 null이 아닌 연결)의 합(released 상태 목표 제외, 계정 통화), `free_to_earmark = balance − goal_earmarked_total`이고 음수면 과예약이다. whole-account 연결은 0으로 센다. 쓰이는 곳은 어시스턴트 `create_goal`의 계정 목록(R-37)이다. 폼의 earmark 안내는 같은 값을 현재 편집 중인 목표를 뺀 pool에서 따로 계산한다(`earmarked_by_other_goals`). | 코드 확인 |
| R-37 | AI 어시스턴트 `create_goal` | 필수 `name`, `target_amount`, `linked_account_names`, 선택 `target_date`(ISO 8601), `earmarks`(계정 이름 → 계정 통화 금액), `notes`. 순서대로 검사해 첫 실패를 `{success: false, error, message, ...}`로 돌려준다: `name_required`, `target_amount_invalid`(0 초과가 아님), `no_linked_accounts`, `unknown_accounts`(가족의 `Depository` `visible` 계정 이름과 안 맞음), `ambiguous_accounts`(같은 이름이 둘 이상), `account_claimed_in_full`(다른 목표가 whole-account로 잡은 계정을 earmark 없이 연결). 실패 응답에는 계정 목록(이름, 통화, `free_to_earmark`, whole-account로 잡혔는지)이 붙는다. 성공이면 가족 통화의 `one_off` 목표를 만들고(통화는 가족 통화, 색은 무작위, `earmarks`의 0 이하·숫자 아님은 버리고 그 계정은 whole-account) `{success: true, goal_id, url, ...}`를 돌려준다. 검증 오류는 `validation_failed`다. `target_date`가 ISO 8601이 아니면 `Date::Error`를 삼켜 nil이 되고 목표는 날짜 없이 오류 없이 만들어진다(`create_goal.rb:185-190`). guest도 호출할 수 있다(R-02). 이 함수는 UI와 달리 `Depository`만, 현재 사용자의 접근이 아니라 가족의 모든 `visible` 계정을 대상으로 하고(U-01) 유지형·월 지출 모드를 만들 수 없다. | 코드 확인 |
| R-38 | 유지형 목표 고갈 인사이트 | 인사이트 생성(가족에 preview 구성원이 있을 때만, R-02)은 `kind = maintained`이고 `state = active`인 목표 중 `status = depleted`이고 환산이 불완전하지 않은 것을 부족액(`remaining_amount`) 내림차순으로 최대 2개 뽑는다. 항목은 유형 `maintained_goal_depleted`, 우선순위 `high`, 사실 값(목표 이름, 부족액·저축액·목표 금액의 통화 표기 문자열), 메타(`goal_id`, 부족액·목표 금액을 소수 0자리 float로 반올림한 값), dedup 키 `maintained_goal_depleted:<goal_id>:<YYYY-MM>`(월마다 바뀌어 매달 한 번 다시 나올 수 있다)를 가진다. 일시정지된 목표는 대상이 아니다. | 코드 확인 |
| R-39 | 날짜·시간대 | 웹 요청은 가족의 `timezone`(없거나 모르는 값이면 앱 기본)으로 `Date.current`와 시각 속성의 날짜를 읽고, 동기화 실행도 같은 규칙이다([recurring-transactions](./recurring-transactions.md) R-30). 앱 기본 시간대는 설정이 주석이라 Rails 기본값(UTC)일 것이다(추론). 목표 코드는 `Date.current`(pace 창, 기한까지 일수, 열린 pledge 판정은 `Time.current`), pledge의 `created_at.to_date`와 `expires_at.to_date`(R-29)를 쓰고 `Family#local_date`는 쓰지 않는다. 같은 pledge도 읽는 시점의 시간대에 따라 날짜가 하루 달라질 수 있다(T-17). 만료 job과 월 job은 요청 밖에서 도는 앱 기본 시간대 컨텍스트다. | 코드 확인 / 추론(앱 기본값) |
| R-40 | 목표 화면의 계정별 유입(`FundingAccountsBreakdownComponent`) | 연결 계정마다 최근 90일 `[오늘 − 90일, 오늘]`(`excluded = false`, 보류 아님) 거래의 각 `max(−Entry.amount, 0)`(입금만, 출금은 0)을 entry 통화(없으면 계정 통화)에서 목표 통화로 오늘 환율로 읽기 경로 환산해 더한 값이 90일 유입이고, 그중 날짜가 `오늘 − 30일` 이후인 것이 30일 유입이다. 이것은 총유입이고 R-15 pace의 순유입(입금과 출금의 합)과 다른 정의다. 계정 행은 backing 내림차순이고 비율은 `round(그 계정 backing / 모든 계정 backing 합 × 100)`(합이 0이면 0)이다. 계산 중 어떤 예외든 로그와 오류 추적에 남기고 빈 맵으로 대신한다(유입 0). | 코드 확인 |

- 불변식: (1) 한 계정에서 고정 earmark를 가진 목표들의 backing 합은 그 계정의 `base`를 넘지 않는다(R-10). 단 whole-account 연결이 이미 둘 이상 겹쳐 저장된 옛 데이터는 예외다(R-07의 검증은 새로 쓰는 행에만 건다). (2) pool, whole-account 배타 검사, 복구 검사, `Account#goal_earmarked_total`, 예산 earmark(R-35)는 모두 같은 released 상태 정의(`archived`, `completed`)를 쓴다. 그래서 완료·보관은 이 다섯 곳에서 함께 예약을 푼다. (3) 환율이 없는 금액은 1:1로 대신하지 않는다. 읽기는 0으로 세고 경고를 붙이며 쓰기는 거부한다(R-12). (4) pledge 대조와 목표 진행은 독립이다(R-31). (5) 요청마다 계산이다. 진행률·pace·status는 저장하지 않고 화면을 열 때 구하며, 저장하는 파생값은 `completed_amount`와 유지형의 `target_amount`뿐이다(R-21, R-19).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-03, R-06, R-22, R-24, R-37 | 권한(Family 테넌시, `AccountShare`)의 목표 쪽 판정은 승인 범위 밖이다. 코드로 확인한 것은 사용 지점뿐이다. 후보·사용 기록·미귀속 출금은 `accessible_accounts`로 좁히지만, backing·pace·KPI·Plan 합계·`free_cash`는 보는 사람과 무관하게 가족 전체 계정 기준이고, pledge 만들기와 `create_goal`은 접근 권한을 보지 않는다. | 재구현이 사용자별 노출을 어떻게 할지(공유받지 못한 계정이 연결된 목표의 금액을 누구에게 보일지)는 이 스펙으로 정할 수 없다. 단일 사용자 가족이면 영향이 없다. 가정: 가족 전체 계정 기준으로 계산하고 접근 판정은 호출자가 준다. | 계정 공유·권한 스펙(승인 범위 밖)이나 `Account.accessible_accounts`, `AccountShare` 정의. `app/models/account.rb`, `app/models/user.rb:230-232`. |
| U-02 | R-27 | pledge를 만들기 전에 이미 가져온 입금 거래(생성 시점 5일 전까지 허용)는 소급 대조 코드가 없고, 같은 거래가 이후 동기화에서 `import_transaction`으로 다시 들어올 때만 대조된다. provider별로 기존 거래를 다시 전달하는지, 전달한다면 어느 기간까지인지는 읽지 않았다. | 자동 대조가 되는 시나리오와 안 되는 시나리오의 경계(사용자 체감). 재구현이 생성 시 소급 대조를 넣을지. | 연동 provider별 processor가 동기화마다 어떤 기간의 거래를 `import_transaction`으로 넘기는지. 사용자 요청으로 연동은 따로 만들므로 재구현 쪽 provider 계약으로 정한다. |
| U-03 | R-27 | `import_transaction`을 거치지 않고 Transaction entry를 만드는 경로(provider processor가 `Entry`를 직접 만드는 경우)가 있는지 전수 확인하지 않았다. 호출처 32개 파일(2.1)의 목록을 만들었고, 우회하는 경로 하나(`kraken_account/ledger_processor.rb:180-192`, `:457`, 직접 `account.entries.create!`)는 확인했다. 부분 해소이고 나머지 provider의 직접 생성은 전수 확인하지 못했다. | 우회 경로의 거래는 pledge 대조 대상이 아니다(Kraken은 확인됨). | `grep -rn "Entry.create\|entries.create\|entries.build\|Entry.new" app/models/*_entry app/models/*_account`로 어댑터를 우회하는 경로를 찾는다. |
| U-04 | R-29, R-39 | 대조기가 도는 모든 컨텍스트(동기화 job, 웹 요청, webhook 등)에서 `Time.zone`이 가족 시간대인지 확인하지 않았다. 동기화는 `Sync#perform`이 가족 시간대로 감싸고 웹 요청은 around_action이 감싸는 것만 코드로 확인했다. | pledge 날짜 창(`created_at`의 날짜)이 하루 달라질 수 있다(T-17). 한국 가족(KST)은 09:00 이전 생성에서 영향이 있다. | provider processor가 `Sync#perform` 밖에서 `import_transaction`을 부르는 경로(webhook, 별도 job)가 있는지. |

- 확인 한계: 원본 테스트는 열지 않았고(파일 이름만 확인) 수락 사례의 값은 코드를 따라 손으로 계산했다. 실행하지 않았다. 환율 제공자·실제 잔액 시계열·AASM·Active Record 같은 프레임워크의 동작은 코드 주석과 호출 방식에서 읽었고 `추론`으로 표시한 곳 외에는 구현부(원본 코드)를 직접 읽은 것에 한정한다. 차트 시계열 빌더(`Balance::ChartSeriesBuilder`)와 화면 모양은 읽지 않았다.

### 1.5 필수 코드 참조

라이선스: overview 1절을 따른다(다른 스펙과 같은 레포 SHA).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/goal.rb:18`, `:105`, `:137`, `:146`, `:165`, `:429`, `:296-297` | `RELEASED_STATES`, `FUNDABLE_ACCOUNT_TYPES`, `KINDS`, `TARGET_MODES`, 정렬 순위 표, `PAUSED_DISPLAY_RANK`, `BALANCE_PACE_DAYS`, 잔액 pace에 쓰는 Valuation 종류 | R-05, R-10, R-15, R-18, R-33 |
| C-02 | `app/models/goal.rb:1266-1316` `account_amount_for`, `net_contributed_for`, `backing_share_for`, `own_allocation_for` | 진행 기준별 base, 고정 earmark pro-rata, whole-account 잔여 계산 | R-10 |
| C-03 | `app/models/goal.rb:499-546`, `:684-689` `current_balance`, `backing_within`, `account_backing`, `market_value_money` | 목표 금액 합계와 예산에 내주는 `backing_within` | R-11, R-35 |
| C-04 | `app/models/goal/currency_converter.rb:1-29`; `app/models/goal.rb:552-585` | 환산 규칙, 읽기·쓰기 경로 차이, 환율 없음 경고 | R-12 |
| C-05 | `app/models/goal.rb:695-697`, `:806-861` | 남은 금액, 진행률, 월 저축액 | R-13, R-14 |
| C-06 | `app/models/goal.rb:279-292`, `:324-388`, `:882-918`, `:1343-1352` | pace의 네 경로 | R-15 |
| C-07 | `app/models/goal.rb:1015-1065`, `:1213-1215`, `:1254-1260`, `:926-932` | status, 표시 status, behind, 필요 delta, runway | R-16, R-17 |
| C-08 | `app/models/goal.rb:957-1013`, `:934-949`, `:1490-1503` | 차트 payload, 도넛 조각, K/M 라벨 | R-17 |
| C-09 | `app/models/goal.rb:460-494`, `:1360-1378`, `:1416-1427`, `:1354-1358` | 상태 기계, 완료 동결, 되돌림, 완료 전 환산 검사 | R-20, R-21 |
| C-10 | `app/models/goal.rb:715-792`, `:1383-1408` | 사용 기록 알고리즘 | R-22 |
| C-11 | `app/models/goal.rb:177-249`, `:1623-1654`; `app/models/goal_account.rb:38-61` | pool, whole-account 충돌 조회·lock, 복구 검사 | R-07, R-10 |
| C-12 | `app/models/goal_pledge.rb:4-10`, `:57-87` | 허용 오차 상수와 일치 판정 | R-29 |
| C-13 | `app/models/goal_pledge.rb:89-194` | 해결, 연장, 취소, 만료, 검증, 삭제 시 거래 정리 | R-24, R-26, R-30 |
| C-14 | `app/models/goal_pledge/reconciler.rb:13-70` | 대조 후보·순서·실패 처리 | R-27, R-28 |
| C-15 | `app/models/goal.rb:396-458` | prepared_for, 정렬, 요약 | R-33 |
| C-16 | `app/controllers/goals_controller.rb:269-347`; `app/models/family.rb:81-106`, `:117-123` | KPI와 30일 저축 유입 | R-34 |
| C-17 | `app/models/goal.rb:609-677`, `:1438-1463`; `app/jobs/refresh_maintained_goal_targets_job.rb:11-47` | "N개월치 지출" 목표 금액 | R-19 |
| C-18 | `app/models/goal/withdrawal_detector.rb:19-23`, `:38-48`, `:57-75` | 미귀속 출금 후보 | R-23 |
| C-19 | `app/models/budget.rb:200-251`; `app/models/account.rb:739-754` | 예산 earmark·free cash, 계정 earmark 도우미 | R-35, R-36 |
| C-20 | `app/models/account.rb:722-732` | pledge 종류 결정 | R-25 |
| C-21 | `app/models/account/provider_import_adapter.rb:59-107`, `:296-307`, `:1086-1091`, `:1155-1160`; `app/models/account/reconciliation_manager.rb:9-22`, `:78-81` | 대조 hook과 보호 entry 경계, 잔액 증가분 | R-27 |
| C-22 | `config/routes.rb:505-506`, `:522-543`; `config/schedule.yml:98-110` | 경로와 job 주기 | 1.3, R-26, R-19 |
| C-23 | `db/schema.rb:21-22`, `:1132-1191`, `:2905`, `:3211-3216` | 테이블, enum, check, unique index, FK | 1.3, R-05, R-30 |
| C-24 | `app/models/assistant/function/create_goal.rb:73-162`, `:196-227`; `app/models/assistant.rb:78`, `:105` | 어시스턴트 함수와 게이트 | R-02, R-37 |
| C-25 | `app/models/insight/generators/maintained_goal_depleted_generator.rb:11-61`; `app/jobs/generate_insights_job.rb:19-41` | 고갈 인사이트 | R-38 |
| C-26 | `app/controllers/goal_pledges_controller.rb:7-66`; `app/controllers/plans_controller.rb:2-33` | pledge 컨트롤러, Plan 컨트롤러 | R-24, R-26, R-32 |
| C-27 | `app/controllers/concerns/preview_gateable.rb:8-19`; `app/helpers/application_helper.rb:128-153` | preview 게이트와 Plan 사이드바 항목 | R-01 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(손계산, 실행하지 않음). 통화는 KRW, 오늘은 2026-11-18이다. 이후 표의 금액은 원 단위이고 `Money` 표기는 `₩1,500,000`(소수 0자리, `config/currencies.yml`의 KRW)이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10, R-11 | 예금 계정 A 잔액 5,000,000, 목표 G가 A에 whole-account 연결, 다른 목표 없음, 목표 금액 10,000,000, 사용 기록 없음 | backing 5,000,000, `current_balance` 5,000,000, `remaining_amount` 5,000,000, `progress_percent` 50 |
| T-02 | R-10 | A 잔액 10,000,000. G1 고정 earmark 3,000,000, G3 고정 earmark 2,000,000, G2 whole-account | G1 3,000,000, G3 2,000,000, G2 `max(10,000,000 − 5,000,000, 0)` = 5,000,000(합 10,000,000) |
| T-03 | R-10 | A 잔액 1,000,000. G1 고정 earmark 800,000, G3 고정 earmark 400,000(합 1,200,000이 잔액 초과) | pro-rata: G1 `round(800,000 × 1,000,000 / 1,200,000, 4)` ≈ 666,666.6667, G3 ≈ 333,333.3333(합 1,000,000, 소수 4자리 반올림, 나눗셈 자릿수는 추론). G1이 completed가 되면 pool에서 빠져 G3은 400,000을 그대로 받는다 |
| T-04 | R-10 | A 잔액 −200,000(당좌 초과 인출), G whole-account. 고정 earmark 100,000도 같은 조건 | 둘 다 backing 0(`base <= 0`) |
| T-05 | R-10, R-11 | 투자 계정(KRW) 잔액 12,000,000, 누적 `net_market_flows` 합 2,000,000, 목표 G whole-account(투자 계정이 연결돼 첫 저장에서 `progress_basis = contributions`로 바뀜) | backing `12,000,000 − 2,000,000` = 10,000,000, `market_value_money` 12,000,000. 누적 시장 손익 합이 13,000,000이면 base `max(12,000,000 − 13,000,000, 0)` = 0 |
| T-06 | R-13 | 목표 금액 10,000,000, backing 3,500,000, `consumed_amount` 0. 다음에 backing 9,999,999, 마지막으로 10,000,000 | 진행률 35. 9,999,999에서는 `floor(99.99999)` = 99(`remaining_amount` 1이므로 99로 자름). 10,000,000에서는 `remaining_amount` 0이라 100 |
| T-07 | R-14 | 위 목표에 `target_date` 2027-03-18(120일 뒤), `remaining_amount` 6,500,000 | `months_remaining` = 4.0, `monthly_target_amount` = `ceil(6,500,000 / 4.0, 2)` = 1,625,000.00. 기한이 오늘이면 `months_remaining` 0.0이라 월 저축액은 `remaining_amount` 6,500,000. 기한이 어제여도 같다 |
| T-08 | R-15, R-16 | 연결 계정 A의 최근 90일 거래: 입금(`amount` −2,000,000)이 3건, 출금(`amount` +1,500,000)이 1건, 보류 거래 1건(−5,000,000, 제외), 제외 처리한 거래 1건(−900,000, 제외) | 합 `−6,000,000 + 1,500,000` = −4,500,000, `pace = 4,500,000 / 3` = 1,500,000.00. T-07의 필요 월액 1,625,000보다 작아 `status = behind` |
| T-09 | R-17 | T-08 상태. 열린 pledge가 없을 때, 100,000일 때, 200,000일 때 | `catch_up_delta` = `max(1,625,000 − 1,500,000 − 0, 0)` = 125,000, 100,000이면 25,000, 200,000이면 0. `projection_end_amount` = `max(3,500,000, 3,500,000 + 1,500,000 × 120 / 30.44)` ≈ 9,413,272(약 `₩9,413,272`), 부족액 라벨은 `10,000,000 − 9,413,272` ≈ 586,728 |
| T-10 | R-15 | 계정 A에 최근 90일 거래 없음, 최근 365일 안에 `reconciliation` Valuation 있음, 1년 전 이전 balances 행의 `end_balance` 2,000,000, 지금 balance 5,400,000, 제외 거래 합 0, `balance` 기준 | 경로 2: `(5,400,000 − 2,000,000) / 12` = 283,333.33 → `pace` 283,333.33. 같은 조건에서 구간의 `net_market_flows` 합이 400,000이고 `contributions` 기준이면 `(5,400,000 − 2,000,000 − 400,000) / 12` = 250,000 |
| T-11 | R-15, R-16 | 계정 A: 2026-09-01 개설 잔액만 있고 거래·Valuation이 없음, 기한 있는 목표 | 경로 4(미측정): `pace_measurable?` false, pace에는 0, `status = pace_unknown`. 같은 계정에 2025년 거래만 있고 최근 Valuation이 없으면 경로 3(휴면)으로 측정된 0이라 `behind` |
| T-12 | R-29 | 연동 예금 계정 A에 `transfer` pledge 500,000(목표 통화 KRW)을 2026-11-18 10:00(가족 시간대)에 만듦. 만료 2026-11-25 10:00. 입금 거래를 다음 날짜·금액으로 가져옴 | 날짜 창 2026-11-13~2026-11-25(기본 7일이 +5일보다 길어 `latest` = 11-25). 11-20 입금 −498,000: `diff` 2,000 <= 5,000(1%) 일치. −495,000: `diff` 5,000, 비율 0.01 이하 일치(경계 포함). −494,999: `diff` 5,001, 비율 0.010002 불일치. +500,000(출금): 거부. 11-12 입금 −500,000: `earliest`보다 이르러 거부. 11-13은 일치. `renew` 뒤 만료 2026-12-02 10:00이면 `latest` = 12-02 |
| T-13 | R-29 | pledge 100(원), 입금 −101, −102 | 허용 오차 `max(0.50, 1% = 1)`: −101은 `diff` 1이라 일치, −102는 `diff` 2라 불일치. 고정 0.50은 원화에서 의미가 없고 1%가 결정한다. 1,000,000원 pledge는 ±10,000이 허용된다 |
| T-14 | R-28, R-30, R-24 | 계정 A에 열린 `transfer` pledge P1 500,000(2026-11-18 생성), P2 502,000(11-19 생성). 입금 −501,000 거래를 가져옴 | 둘 다 일치 조건이지만 `created_at` 오름차순이라 P1이 해결: P1 `matched`, 거래 `extra.goal.pledge_id = P1`. P2는 `open` 그대로. 거래를 다시 동기화로 받아도 `pledge_id`가 있어 건너뜀. 중복 검사는 `open`이고 만료 전인 행만 본다. (매칭 전 순서) P1이 `open`일 때 같은 계정에 500,000 pledge를 만들면 중복 오류. (매칭 후 순서) P1이 `matched`가 된 뒤에는 500,000 pledge를 다시 만들 수 있고, 아직 `open`인 P2와 같은 502,000을 만들면 중복 오류 |
| T-15 | R-25, R-27, R-29 | 수동 예금 계정 B 잔액 3,000,000, `manual_save` pledge 500,000. 사용자가 잔액을 3,500,000으로 갱신 / 2,800,000으로 갱신 | 3,500,000 갱신: `valuation_delta` +500,000, 일치, pledge `matched`(`matched_transaction_id` null). 2,800,000 갱신: delta −200,000 불일치. 수동 투자 계정은 pledge가 `transfer`라 Valuation으로는 절대 일치하지 않는다 |
| T-16 | R-27 | 보류(pending) 입금 거래가 먼저 들어옴, 이후 확정 거래가 들어옴 | 보류 단계에서는 대조하지 않고, 확정 거래를 `import_transaction`으로 저장한 뒤 대조한다. 사용자가 이미 편집한(`user_modified`) entry와 제외 entry는 대조하지 않는다 |
| T-17 | R-29, R-39 | 같은 pledge가 KST 2026-11-19 07:30에 만들어짐(UTC로는 11-18 22:30) | `Time.zone`이 Asia/Seoul인 컨텍스트에서는 `created_at.to_date` = 11-19이고 날짜 창 11-14~11-26. UTC 컨텍스트에서 읽으면 11-18이고 창 11-13~11-25(U-04) |
| T-18 | R-22 | 목표 금액 5,000,000인 `one_off` active 목표 G, 연결 하나(계정 A whole-account, 잔액 6,000,000), `consumed_amount` 0, 사용 기록 2,000,000(통화 같음) | `rate` 1, `native` 2,000,000, `backed` 6,000,000, `still_needed = 5,000,000 − 0 − 2,000,000` = 3,000,000, 연결이 고정 earmark `min(6,000,000, 3,000,000)` = 3,000,000으로 바뀜. `consumed_amount` 2,000,000. 이후 `current_balance` 3,000,000, `progress_amount` 5,000,000, `remaining_amount` 0, 진행률 100. A의 `free_to_earmark` = `6,000,000 − 3,000,000` = 3,000,000 |
| T-19 | R-22 | (a) 고정 earmark 1,000,000인 연결에 1,500,000 사용 기록 (b) `consumed_amount` 4,000,000인 목표(목표 금액 5,000,000)에 1,500,000 사용 기록 (c) 유지형 목표에 사용 기록 (d) 연결이 둘인 목표에 계정을 안 주고 사용 기록 (e) 같은 출금 거래로 두 번째 사용 기록 | (a) `exceeds_earmark`, 변화 없음. (b) `4,000,000 + 1,500,000 > 5,000,000`이라 `exceeds_target`. (c) `maintained`. (d) `account_required`. (e) 두 번째는 `transaction_already_claimed` |
| T-20 | R-20, R-21 | 목표 G(backing 8,000,000, 목표 10,000,000)를 `complete`. 이후 계정에서 7,000,000을 써 잔액이 1,000,000이 됨. 다음에 `reopen` | `completed_amount` 8,000,000, 진행률 100, 잔액이 줄어도 `current_balance` 8,000,000 그대로. `reopen` 뒤 `completed_amount`가 지워지고 backing은 실시간 1,000,000이며 `consumed_amount`는 0으로 초기화. 환율이 없는 외화 계정이 연결돼 있으면 `complete`는 거부된다 |
| T-21 | R-07 | G1이 A에 whole-account. G2도 A에 whole-account 연결을 만들려 함 / G1을 `complete`한 뒤 G2를 만들려 함 / G2를 만든 뒤 G1을 `reopen` | 첫째는 오류 `account_already_fully_earmarked`. 둘째는 G1이 released라 허용. 셋째는 G1 복구가 `whole_account_conflict_on_restore`로 거부되어 G1은 `completed`로 남는다. 고정 earmark 3,000,000 둘을 같은 A에 거는 것은 허용 |
| T-22 | R-35 | 예산 통화 KRW, 현금 계정 A(예금) 10,000,000, B(예금) 2,000,000. G1(KRW) A에 고정 3,000,000, G2(KRW) B에 whole-account. 완료된 G3(KRW)가 A에 고정 4,000,000, 투자 계정 C(5,000,000)에 건 whole-account 목표 G4 | `available_cash` 12,000,000, `earmarked_for_goals` = 3,000,000 + 2,000,000 = 5,000,000(G3은 released, G4는 C가 현금 계정이 아니라 제외), `free_cash` 7,000,000 |
| T-23 | R-35 | 현금 계정 A −200,000, B 1,000,000, 목표 G가 둘 다 whole-account | `available_cash` 800,000, G의 backing A 0 + B 1,000,000 = 1,000,000, `free_cash = max(800,000 − 1,000,000, 0)` = 0 |
| T-24 | R-35, R-12 | 예산 통화 KRW, 달러 예금 D 1,000 USD, 1 USD = 1,400 KRW. 목표 G(통화 USD)가 D에 고정 earmark 600 USD. 환율이 있을 때와 없을 때 | 환율 있음: `available_cash` 1,400,000, G의 backing 600 USD를 KRW로 840,000, `free_cash` 560,000. 환율 없음: 예산 쪽 D가 0으로 빠지고(`missing_cash_currencies` = {USD}) G의 backing도 0이라 `free_cash` 0 |
| T-25 | R-33 | Plan 요약(`currency` KRW). G1(KRW) 3,500,000/10,000,000 behind, G2(KRW) 1,000,000/2,000,000 on_track, G3(USD) 2,000/5,000 behind, 열린 pledge 수 1·0·2 | `saved_money` 4,500,000(KRW만), `target_money` 12,000,000, `behind_count` 2(USD 목표 포함), `pending_count` 3 |
| T-26 | R-34 | 오늘 2026-11-18. 목표 연결 KRW 계정의 순유입이 10-19~11-18에 3,000,000, 09-19~10-18에 2,000,000 | 현재 3,000,000(31일 창), 직전 2,000,000(30일 창), `delta` 1,000,000, `delta_percent` 50.0, 방향 up. 순유출이면 머리 숫자는 "−"와 절댓값 |
| T-27 | R-19 | 유지형 목표(`months_of_expenses`, `target_months` 6), 가족 통화 KRW, 월 지출 합 2,000,000·2,400,000·2,200,000·3,000,000. 목표 통화가 KRW / USD(1 KRW = 0.00072 USD로 가정) | 중앙값 2,300,000, `target_amount` 13,800,000. USD이면 `round(13,800,000 × 0.00072, 2)` = 9,936.00. 지출 이력이 없으면 중앙값 0이라 새 목표는 금액 필수 오류, 기존 목표는 이전 금액 유지 |
| T-28 | R-23 | `one_off` active 목표, 연결 KRW 계정에 최근 90일 출금 5,000원(카드 결제), 99원, 입금 −300,000, 보류 출금 500,000, 이미 사용 기록한 출금 200,000 | 후보는 5,000원 한 건이다(99원은 100 미만, 입금은 양수가 아님, 보류와 이미 귀속된 것은 제외). 원화에서는 100 하한이 의미가 없어 소액 출금도 후보다 |
| T-29 | R-17 | `short_money`에 1,234,567 / 25,000 / 999 / 10,000,000 (KRW) | `₩1.2M`, `₩25K`, `₩999`, `₩10M` |
| T-30 | R-01, R-02 | preview 꺼진 사용자가 `GET /goals`, `GET /plan`, `POST /goals/:id/pledges` / 같은 사용자의 어시스턴트가 `create_goal` 호출 | `/goals`와 pledge 요청은 루트로 redirect하며 alert, `/plan`은 `/budgets`로 redirect. 어시스턴트(와 MCP 도구 목록)는 목표를 만들 수 있고 목표는 플래그를 켜야 UI에서 보인다 |
| T-31 | R-37 | `create_goal`: 이름이 같은 예금 계정 둘, 다른 목표가 whole-account로 잡은 계정을 earmark 없이 | 각각 `ambiguous_accounts`, `account_claimed_in_full`. 후자 응답의 계정 목록에 `claimed_in_full: true`. `earmarks: {"비상금통장": 2000000}`를 주면 그 계정에 고정 earmark 2,000,000으로 연결 |
| T-32 | R-09 | 거래 X가 pledge P(`matched`)에 찍혀 있고(`pledge_id = P`), 사용 기록 `consumed_goal_id = G`도 찍힌 거래 Y. 목표 G를 삭제 | P가 지워지며 X의 `pledge_id`와 비면 `goal` 키가 지워진다. Y의 `consumed_goal_id`는 남아 이후 다른 목표의 사용 기록에서 `transaction_already_claimed`가 된다 |
| T-33 | R-40, R-15 | 연결 KRW 계정의 최근 90일 거래: 입금 −2,000,000 3건(20일 전, 40일 전, 70일 전), 출금 +1,500,000 1건(10일 전) | 90일 유입 6,000,000(출금은 0으로 센다), 30일 유입 2,000,000(20일 전 입금만). pace는 순유입 4,500,000 / 3 = 1,500,000이라 6,000,000과 다른 정의다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

기준은 repo@`1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a`다. 아래 줄 번호는 이 SHA의 파일이다.

**검색 범위와 놓쳤을 가능성(부재·전칭 주장 공통).** 목표 관련 코드 전체를 `grep -rn -i -E "goal|earmark|backing_within|savings_inflow|pledge" app lib config db/schema.rb db/seeds.rb --include=*.rb --include=*.rake --include=*.yml --include=*.erb --include=*.js`로 훑어 파일 목록을 만들었다(번역 yml 제외 후 약 60개 파일). `.rake`는 `lib/tasks`에 있는 것까지 포함했고 목표 이름은 `app/models/demo/generator.rb`(데모 데이터)에서만 나왔다. 매크로·`send`·문자열로 만든 이름·`app/mailers`·`db/seeds`의 동적 호출은 이 방법으로 잡히지 않는다. 읽은 범위는 위 소스 목록이다. 읽지 않은 것: 원본 테스트, 번역 yml, `Goals::AvatarComponent`·`ProgressRingComponent`·`AccountStackComponent`, `goals_filter_controller.js`, `goal_projection_chart_controller.js`, `goal_earmark_controller.js`.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-27 `preview_gateable.rb:8-19`; `goals_controller.rb:2`; `goal_pledges_controller.rb:2`; `plans_controller.rb:8`, `:31-33`; `application_helper.rb:128-153`; `docs/llm-guides/gating-a-preview-feature.md:7-16`, `:141` | 코드 확인. 문서와 구현이 일치한다. `PlansController`의 redirect 대상은 `budgets_path`이고 flash가 없다는 것은 `plans_controller.rb:32-33`. `Current.user.preview_features_enabled?`는 `user.rb:909-911`. |
| R-02 | C-24 `assistant.rb:78`, `:105`; `sweep_expired_goal_pledges_job.rb:10-21`; `refresh_maintained_goal_targets_job.rb:11-18`; `generate_insights_job.rb:19-27`, `:41`; `family.rb:135`, `:150-152` | 코드 확인. guest 호출 가능은 `assistant.rb:40-47`(제외 목록에 `CreateGoal` 없음), `:105-106`. 부재 주장(REST 목표 API 없음)은 `grep -rn -i goal app/controllers/api config/routes.rb`와 위 전체 검색에서 `api` 아래 목표가 나오지 않았고 `routes.rb`의 목표 관련 줄은 `:415`(온보딩), `:505-506`, `:522-543`뿐이라는 근거다. `Assistant.function_classes`의 호출처는 `mcp_controller.rb:99`, `:118`, `assistant/configurable.rb:106`, `eval/runners/chat_runner.rb:251`이다(`grep -rn function_classes app lib config`). 이 목록 밖에 `Goal`을 쓰는 도구는 위 검색에서 없었다. MCP 엔드포인트의 인증·사용자 범위는 읽지 않았다. |
| R-03 | `goals_controller.rb:6`, `:197-205`; `goal_pledges_controller.rb:5`, `:59-66`, `:86-88`(`record_not_found`) | 코드 확인. 접근 판정 사용 지점은 `goals_controller.rb:215-224`, `:370-376`, `plans_controller.rb:17-21` 부근. 비접근 계산: `goal.rb:177-186`, `:256-258`이 `family`만으로 조회한다. |
| R-04 | `goal.rb:20-21`, `:34-36`, `:77`, `:148-151`, `:1452-1463`, `:1601-1603`; `goals_controller.rb:207-213`; `goals_controller.rb:59-62`; `_form.html.erb:28-40`, `:57-71`, `:76-107` | 코드 확인. 뷰가 보내는 필드를 `_form.html.erb`에서 확인했다(`kind` 라디오, `target_mode` 선택, `target_months`, `target_amount`, `target_date`, `notes`, `color`/`icon`은 `_color_picker`, 파일은 읽지 않았고 허용 필드는 컨트롤러가 정한다). `currency`는 폼에 없고 컨트롤러가 허용하지 않는다(`goals_controller.rb:62`). 유지형에서 `target_date` 칸을 숨기고 months 모드에서 금액 칸을 비활성화하는 동작은 `goal_kind_controller.js:44-54`를 보고 쓴 것이고 서버 쪽 정규화(`goal.rb:1601-1603`, `:1438-1447`)가 기준이다. |
| R-05 | `goal.rb:105`, `:1525-1538`, `:1551-1560`, `:1605-1610`; `goal_account.rb:5-8` | 코드 확인. 계정 상태·`exclude_from_reports`를 연결·금액 계산에서 쓰지 않는다는 주장은 `goal.rb:499-508`(`linked_accounts` 전체를 더함), `goal.rb:27-28`(조건 없는 관계)에서 읽었다. 읽기 범위: `goal.rb`와 `goal_account.rb` 전체. |
| R-06 | `goals_controller.rb:58-87`, `:95-137`, `:215-224`, `:226-267`(연결 삭제 `:230-238`); `_form.html.erb:154-182` | 코드 확인. 뷰가 `goal[account_ids][]`와 계정마다 `goal[allocations][<id>]`를 보내는 것은 `_form.html.erb:154-163`, `:171-183`이다(`af.money_field account.id` → `goal[allocations][id]`). 빈 칸이 `nil`인 이유는 `goals_controller.rb:259-267`. |
| R-07 | C-11 `goal.rb:200-249`; `goal_account.rb:10`, `:38-61`; `goal.rb:1623-1639` | 코드 확인. advisory lock 키는 `goal.rb:219-221`. "고정 earmark에는 배타 검사가 없다"는 `goal_account.rb:39`(`return unless whole_account?`)에서 읽었다. |
| R-08 | `account.rb:29-31`; `db/schema.rb:3211-3214`; `goal.rb:885-886`, `:1525-1529`; `goals_controller.rb:95-107`(수정 경로 주석 `:109-115`) | 코드 확인. 전이 저장 실패는 `goals_controller.rb:402-417`. |
| R-09 | `goals_controller.rb:139-148`; `goal.rb:27-29`; `goal_pledge.rb:37`, `:183-194`; `db/schema.rb:3215`; 부재: `consumed_goal_id`는 `goal.rb:1385`, `:1392`와 `withdrawal_detector.rb:67`에서만 나온다 | 코드 확인. 부재 검색: `grep -rn "consumed_goal_id" app lib config db --include=*.rb --include=*.rake --include=*.erb`(위 세 줄만). `reopen`의 `thaw`(`goal.rb:1416-1427`)는 `completed_amount`·`completed_at`·`consumed_amount`만 건드리고 거래를 지우지 않는다. 놓칠 수 있는 것: 콘솔·raw SQL 정리. |
| R-10 | C-02 `goal.rb:1266-1316`; `pooled_allocations_for` `goal.rb:177-186` | 코드 확인. `net_market_flows`가 depository에서 0이라는 말은 주석(`goal.rb:1271-1274`)이고, 계산은 모든 연결 계정에 같은 식이다. 한국 사례(T-03)의 나눗셈 자릿수는 BigDecimal 기본 정밀도 가정이다(추론). 투자 계정이 연결되면 첫 저장에서 `contributions`로 바뀌는 것은 `goal.rb:39`, `:1544-1549`. `progress_basis`를 쓰는 다른 코드: `grep -rn progress_basis app lib config --include=*.rb --include=*.erb --include=*.rake`가 `goal.rb`밖에서 나오지 않았다(폼·컨트롤러·어시스턴트 모두 쓰지 않음). |
| R-11 | C-03 `goal.rb:499-546`, `:684-689`, `:524-529` | 코드 확인. `completed_amount.present?`가 `completed?`와 다르다는 점은 `goal.rb:500-505` 주석. `backing_within`이 `account_amount_for`를 쓰고 `account_backing`이 아니라는 점은 `goal.rb:524-529`와 `:540-546`를 대조해 확인. |
| R-12 | C-04 `currency_converter.rb:1-29`; `goal.rb:552-585`; `money-currency-rules.md` R-21~R-23, R-25 | 코드 확인. "하루 한 번 로그"는 `Rails.cache.write(..., unless_exist: true, expires_in: 1.day)` 조건(`goal.rb:563-565`). 환율 조회 내부는 money-currency-rules. |
| R-13 | C-05 `goal.rb:695-697`, `:806-808`, `:825-837` | 코드 확인. |
| R-14 | C-05 `goal.rb:844-861`; `goal_form_controller.js:164-183`, `:232-234` | 코드 확인. 폼의 안내 문구는 브라우저 계산이라 원본 의도(미리 보기)는 추론이다. |
| R-15 | C-06 `goal.rb:279-292`, `:296-388`, `:882-918`, `:1343-1352`; `docs/llm-guides/goals.md:169-219` | 코드 확인. 문서의 "90일 순유입 / 3, 네 경로, 순서"와 구현이 같다. 경로 2의 제외 거래 합만 `excluding_split_parents`를 따로 건다(`goal.rb:357-361`, `excluded = true`인 항목 중 분할 원본을 빼야 하므로). 경로 1의 `pace_for`는 `excluded = false` 조건 하나로 분할 원본도 빠진다(분할 원본이 `excluded = true`인 것은 transactions R-16, R-23). `Transaction.excluding_pending` 정의는 `transaction.rb:184-186`, `:211`. 거래 `kind`로 거르지 않으므로 이체 거래도 센다(`goal.rb:279-292`에 `kind` 조건 없음). `Balance::SyncCache`와의 일치 주장은 `goal.rb:352-354` 주석이고 해당 파일은 읽지 않았다. `month_start_day`를 이 경로에서 읽지 않는다: `grep -n month_start_day app/models/goal*.rb app/models/goal/*.rb app/controllers/goal*.rb app/controllers/plans_controller.rb app/components/goals/*.rb app/helpers/goals_helper.rb`에 일치가 없다. |
| R-16 | C-07 `goal.rb:1015-1065`, `:1213-1215` | 코드 확인. 문서(`docs/llm-guides/goals.md:141-153`)는 `reached`를 "`progress_percent >= 100`"이라 쓰지만 구현은 `completed? || remaining_amount.zero?`이고 유지형 `funded`·`depleted`가 문서에 없다. 구현을 사실로 썼다. |
| R-17 | C-07 `goal.rb:926-932`, `:1008-1013`, `:1254-1260`; C-08 `goal.rb:934-949`, `:957-1003`, `:1217-1246`, `:1505-1523`, `:1490-1503` | 코드 확인. `short_money`의 1,000 미만 분기는 소수를 버리지 않고 `round`한 정수다(`goal.rb:1500-1502`). KRW 기호 `₩`는 `config/currencies.yml:1981`. 차트 시리즈 자체(`Balance::ChartSeriesBuilder`)는 읽지 않았다. |
| R-18 | `goal.rb:479-481`, `:722`, `:1039`, `:1063-1065`, `:1570-1599`, `:1601-1603`; `withdrawal_detector.rb:68`; `goals_controller.rb:326-328` | 코드 확인. |
| R-19 | C-17 `goal.rb:609-677`, `:1438-1463`; `refresh_maintained_goal_targets_job.rb:11-47`; `schedule.yml:105-110`; `goal_kind_controller.js:44-54`; `income_statement.rb:176-182`, `:329-335`; `family_stats.rb:36-63` | 코드 확인. cron의 시간대는 `schedule.yml:91-93` 주석("6:00 AM UTC")만 근거라 이 항목이 UTC라는 것은 추론이다(U로 올리지 않은 이유: 영향이 실행 시각뿐이다). 중앙값 SQL(`PERCENTILE_CONT(0.5)`)의 조건(`kind` 제외, `excluded`, `exclude_from_reports`, 보류, 세금 우대, 예정 거래)은 budgets R-21과 같은 파일(`family_stats.rb:46-53`). |
| R-20 | C-09 `goal.rb:460-494`; `goals_controller.rb:402-425`; `docs/llm-guides/goals.md:154-158` | 코드 확인. AASM bang의 반환값은 gem 동작이라 추론이다(`whiny_persistence` 설정이 `app lib config`에 없음을 `grep -rn whiny`로 확인). 컨트롤러 주석(`goals_controller.rb:408-412`)이 같은 가정을 적고 있다. `paused`가 pool에 남는 것은 `goal.rb:107-113`의 주석과 `RELEASED_STATES` 정의(`goal.rb:18`). |
| R-21 | C-09 `goal.rb:82`, `:1354-1378`, `:1416-1427`; `goal.rb:91-100` | 코드 확인. "완료한 적 없는 보관 목표의 되돌림은 `consumed_amount`를 지키는" 분기는 `goal.rb:1419-1424`. |
| R-22 | C-10 `goal.rb:715-792`, `:1383-1408`; `goals_controller.rb:170-188`, `:349-400`; `consume.html.erb:8-47`; `goal.rb:535-537` | 코드 확인. 뷰가 보내는 파라미터: 폼은 `amount`(money_field, 스코프 없음)와 계정이 둘 이상일 때만 `account_id`(DS::Select)를 보내고(`consume.html.erb:13-44`), 미귀속 출금 버튼은 `transaction_id`를 보낸다(`_unattributed_outflows.html.erb`, 줄 `~36-40`). 컨트롤러가 읽는 키와 같다(`goals_controller.rb:176-177`, `:357`, `:388`). `money_field`가 금액 문자열을 어떻게 정규화해 보내는지(쉼표·천 단위)는 읽지 않았고 컨트롤러는 `to_d`를 쓴다. |
| R-23 | C-18 `withdrawal_detector.rb:19-23`, `:38-48`, `:57-75`; `goals_controller.rb:37`, `:359`, `:370-380`(항상 배열을 넘김); `withdrawal_detector.rb:30-55`(`@accounts ||=`는 빈 배열도 truthy라 fallback 없음, 추론: Ruby 의미) | 코드 확인. "원화에서 100이 사실상 하한이 없다"는 계산 결과(통화 환산 없음, `withdrawal_detector.rb:66`의 `amount >= 100` 조건)이고 원본 주석이 "달러·유로 규모에 맞춘 고정값"이라고 직접 적는다(`withdrawal_detector.rb:14-19`, 주석). |
| R-24 | C-26 `goal_pledges_controller.rb:7-66`, `:76-82`; `goal_pledge.rb:20-25`, `:149-181`; `goal_pledges/new.html.erb:41-62`; `goals/show.html.erb:156-170` | 코드 확인. 뷰가 보내는 파라미터: 폼 모델이 `GoalPledge`라 필드 이름은 `goal_pledge[amount]`(money_field)와 `goal_pledge[account_id]`(select)이고(`new.html.erb:41-62`) 컨트롤러가 `amount`만 `permit`하고 계정은 따로 읽는다(`goal_pledges_controller.rb:72-73`, `:25-27`). 상태 검사 부재: `grep -n -i "paused\|archived\|completed\|active?\|state" app/models/goal_pledge.rb app/controllers/goal_pledges_controller.rb app/models/goal_pledge/reconciler.rb` 결과 없음. 접근 권한 부재: `lookup_account`가 `@goal.linked_accounts`만 쓴다(`:76-79`). |
| R-25 | C-20 `account.rb:722-732`, `:912-923`; `goal_pledges_controller.rb:25-29`, `:81-83`; `goals/show.html.erb`; `docs/llm-guides/goals.md:253-264` | 코드 확인. 문서가 말하는 `GoalPledgesController#kind_for_account`는 구현에 없고(`grep`으로 없음 확인) 실제는 `Account#default_pledge_kind`다. 문서와 구현이 다르다. |
| R-26 | C-13 `goal_pledge.rb:32-34`, `:123-146`; `goal_pledges_controller.rb:44-56`; `sweep_expired_goal_pledges_job.rb:10-21`; `schedule.yml:98-103`; `goal.rb:30-32` | 코드 확인. 연장이 지금이 아니라 기존 만료 기준이라는 점은 `goal_pledge.rb:126`(`expires_at + days.days`). 만료 후 sweep 전의 `open` 행도 `extend!` 가능: `set_pledge`가 `@goal.goal_pledges.find`(상태 조건 없음)이고(`goal_pledges_controller.rb:69-71`) `extend!`는 `status_open?`만 본다. UI에는 열린 pledge만 나온다(`goals_controller.rb:36`). |
| R-27 | C-21 `provider_import_adapter.rb:59-107`, `:128-132`, `:296-307`; `kraken_account/ledger_processor.rb:180-192`, `:457`; `:1086-1091`, `:1155-1160`; `reconciliation_manager.rb:9-22`, `:78-81`; 부재: `GoalPledge::Reconciler` 호출처 | 코드 확인. 호출처 검색: `grep -rn "GoalPledge::Reconciler\|Reconciler.new" app lib config --include=*.rb --include=*.rake`에서 `provider_import_adapter.rb:306`과 `reconciliation_manager.rb:19` 둘뿐이다(`goal_pledge/reconciler.rb` 자신 제외). 잔액 갱신을 부르는 곳은 `current_balance_manager.rb:83`, `:153`, `reconcileable.rb:5`, `:11`, `account.rb:334`, `vehicle.rb:116`이고 모두 `reconcile_balance`로 모인다. 어댑터 호출처 파일 32개는 `grep -rln "import_transaction(" app lib`로 목록만 만들었다(U-03). 소급 대조 없음은 위 호출처 검색이 근거다. |
| R-28 | C-14 `reconciler.rb:13-70` | 코드 확인. |
| R-29 | C-12 `goal_pledge.rb:57-87`; `reconciler.rb:68-70`; 사용처: `grep -rn "\.matches?(" app lib`로 대조기(`reconciler.rb:25`)에서만 호출됨 | 코드 확인. `matches?`가 Transaction이고 pledge가 `manual_save`인 조합에서 방향 검사를 건너뛰는 분기는 `goal_pledge.rb:63-69`에 있으나 대조기가 종류를 먼저 걸러 이 조합에 도달하지 않는다(위 검색 근거). `docs/llm-guides/goals.md:221-233`의 "$0.50 또는 1%, ±5일"이 구현과 같다. |
| R-30 | C-13 `goal_pledge.rb:89-115`, `:183-194`; `reconciler.rb:27-43`; `db/schema.rb:1158`, `:2905`, `:3215` | 코드 확인. `Goal#last_matched_pledge_at`은 `goal.rb:1071-1079`. |
| R-31 | `goal.rb:29-32`, `:456`, `:1071-1086`, `:1257`; `goals/show.html.erb:96-98`, `:159-165`; `goal_pledge_preview_controller.js:55-70` | 코드 확인. 부재 검색: `grep -n "goal_pledges\|open_pledges\|pledge" app/models/goal.rb`가 위 줄(관계 선언, `summary_for`의 `pending_count`, `last_matched_pledge_at`, `pledge_action_label_key`, `catch_up_delta_money`)뿐이다. `current_balance`·`status`·`pace`는 pledge를 읽지 않는다. 완료·보관된 목표의 pledge를 닫는 코드가 없다는 것은 `grep -rn "goal_pledges\|open_pledges" app --include=*.rb`에서 상태 전이 코드(`goal.rb:460-494`, `:1360-1378`)가 pledge를 건드리지 않는 것으로 확인. |
| R-32 | C-26 `plans_controller.rb:10-14`(`resolve_budget` 호출), `:10-28`; `budget_ownership.rb:34-60`; `plans/show.html.erb`; `_budget_card.html.erb:14-17`, `:62`; `_goals_card.html.erb:84`, `:119-125`; `budget_ownership.rb:34-60` | 코드 확인. 예산 부분은 budgets.md R-06, R-18~R-20, R-33에 맡겼고 이 문서가 다시 정하지 않는다. `resolve_budget`이 nil을 돌려줄 수 있는 경로(budgets R-33의 "household를 껐을 때")에서 `@budget.editable_by?`가 터지는지는 읽지 않았다. |
| R-33 | C-15 `goal.rb:396-458`; `_goals_card.html.erb:75-78` | 코드 확인. `summary_for`가 `consumed_amount`를 `saved_money`에 더하지 않는다는 것은 `goal.rb:453`(`current_balance`만 합). 같은 카드의 목록 막대는 `progress_percent`(consumed 포함)를 쓴다(`_goals_card.html.erb`의 `goal.progress_percent`)라서 합계 막대와 개별 막대의 기준이 다르다. |
| R-34 | C-16 `goals_controller.rb:269-347`; `family.rb:81-106`, `:117-123` | 코드 확인. `family.rb:67-80`의 주석은 "depository 계정"이라 적지만 `goal_linked_account_ids`는 계정 종류를 거르지 않는다(`:117-123`). 구현을 사실로 썼다. 통화 합산의 혼합: `needs`는 목표 통화를 보지 않고 합한다(`goals_controller.rb:295-297`). |
| R-35 | C-19 `budget.rb:200-251`, `:543-551`; `_available_cash.html.erb:19-38`; `budgets/show.html.erb:49-54`; `budgets.md` R-31 | 코드 확인. 예산 쪽 계산(`cash_accounts`, `available_cash`)은 budgets R-31에 맡겼다. 이 항목이 budgets U-02를 닫는다. `missing_cash_currencies`가 목표 쪽 누락 통화를 모으지 않는다는 것은 `budget.rb:244-247`, `:543-551`(예산 자신의 `@missing_cash_currencies`에만 더함)과 `goal.rb:574-576`(목표 인스턴스의 별도 Set)의 대조다. |
| R-36 | C-19 `account.rb:739-754`; `create_goal.rb:196-207`; `goals_helper.rb`(`earmarked_by_other_goals`); `_form.html.erb:150-151` | 코드 확인. |
| R-37 | C-24 `create_goal.rb:73-162`, `:196-227`; `assistant.rb:67-103` | 코드 확인. 설명 문구는 "Depository 계정에 연결"(`create_goal.rb:19-20`)이고 구현은 `accountable_type: "Depository"`로 조회한다(`:93`, `:199`). `kind`·`target_mode` 파라미터가 스키마에 없음은 `params_schema`(`:39-70`)에서 확인. |
| R-38 | C-25 `maintained_goal_depleted_generator.rb:11-61`; `generator.rb:107-113`; `generate_insights_job.rb:19-41` | 코드 확인. `month_token`은 `date.strftime("%Y-%m")`(`generator.rb:111-113`). 인사이트의 `title`·템플릿 문구는 읽지 않았다. |
| R-39 | `localize.rb:5-7`, `:114-128`; `family.rb:832-840`; `sync.rb:185`; `config/application.rb:28`; `recurring-transactions.md` R-30 | 코드 확인 / 추론(앱 기본 UTC는 `config.time_zone` 주석 상태에서 Rails 기본값을 가정). 비교 대상 `Family#local_date`(`family.rb:317-320`)를 목표 코드가 쓰지 않는다는 것은 위 전체 검색에서 `local_date` 호출이 목표 파일에 없다는 것으로 확인. |
| R-40 | `funding_accounts_breakdown_component.rb:3-4`, `:11-40`, `:68-102` | 코드 확인. R-15와 정의가 다른 것은 `:92`의 `clamp(0..)`. 뷰 `goals/show.html.erb:178-182`가 이 컴포넌트를 렌더한다. |
| T-01~T-33 | 위 규칙의 C-ID 범위 | 손계산. 실행하지 않았다. 환율 값(T-24, T-27)은 가정이다. T-03의 소수 4자리와 T-09의 근사값은 BigDecimal 정밀도·Float 계산에 따른 추론이다. |

### 2.2 코드 읽는 순서

1. `app/models/goal.rb`를 계산 순서로 읽는다: 상수와 검증(1-165) → pool·pace 준비(177-458) → 상태 기계(460-494) → backing·환산(499-585) → 진행률·월 저축액·pace(695-918) → status(1015-1065) → 사용 기록(715-792) → private 계산(1266-1352).
2. pledge는 `goal_pledge.rb`(`matches?` → `resolve_with!`) → `goal_pledge/reconciler.rb` → 호출 지점(`provider_import_adapter.rb:296-307`, `reconciliation_manager.rb:9-22`) 순서다.
3. 예산 연결은 `budget.rb:200-251`에서 `Goal.prepared_for`와 `backing_within`으로 들어간다.
4. 구현 전략: 목표 목록은 가족 전체의 pool·시장 손익·pace를 한 번에 읽어 각 목표에 주입한다(`inject_backing_math!`). 재구현은 목표마다 쿼리하지 않도록 같은 모양으로 준비하면 된다. 결과는 목표별로 따로 계산한 것과 같다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. `docs/llm-guides/goals.md`는 문서와 구현이 다른 곳이 있다. 실제 `docs/llm-guides/goals.md:46-89`가 적은 `_form_stepper.html.erb`, `goal_stepper_controller.js`, `db/migrate/20260514120000_create_goal_pledges.rb`, `20260514120001_drop_goal_contributions.rb`는 이 SHA의 추적 파일에 없다(실제 폼은 `_form.html.erb`, pledge 테이블은 `20260511100000_create_goals.rb`가 만든다). `20260514120002_add_pledge_id_index_to_transactions.rb`는 존재한다. 이 문서의 모든 규칙은 구현을 기준으로 썼다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-04가 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: `goal.rb` 전체와 pledge·대조기·환산·출금 감지·두 controller·job·`create_goal`·인사이트 생성기를 직접 읽고 R-ID 39개 중 약 34개가 일치했다. T-01~T-32 중 T-14를 뺀 31개를 재계산했고 부재 주장 R-09·R-27·R-31 및 REST API·MCP 경로를 grep으로 반증 시도했다. 중요 오류 3건(T-14, R-32 Plan 읽기 전용, R-27 우회 경로), 사소 5건, 누락 3건이 나왔다. 작성자가 전부 반영해 R-40과 T-33을 추가했다. `docs/llm-guides/goals.md`가 구현과 다르다는 작성자 주장도 확인됐다.
- **메인 표본 점검**: R-32(`plans_controller.rb:10-14`), R-27(`kraken_account/ledger_processor.rb:180-192`), R-35(`goal.rb:524` 인스턴스 메서드), 마이그레이션 존재 여부를 원본에서 직접 확인했다. 이 스펙이 `budgets` U-02를 닫았다.
- **대조하지 못한 것**: `Balance::ChartSeriesBuilder`와 차트 JS, 실제 환율 provider 응답, provider별 processor 32개의 `Time.zone`(U-04)과 거래 재전달 범위(U-02), `resolve_budget`이 nil일 때의 경로.
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-23, R-14 | (후보) 원화 기준에서 미귀속 출금 하한 100과 pledge 허용 오차의 고정 0.50은 통화별 소수 자릿수·크기에 맞춰 조정할 수 있다 | 한국 사용에서 100원, 0.50원은 의미가 없다(T-13, T-28). 원본의 미결정이 아니라 원본 동작이므로 본문은 그대로 두고 여기에만 둔다 | 하한을 통화별 상수로 바꾸면 R-23의 후보 집합과 T-28이 바뀐다 |
| R-34 | (후보) 목록 KPI의 `needs_this_month`는 목표 통화가 가족 통화와 다르면 합에서 빼거나 환산 | 원본은 통화를 무시하고 합한다(R-34) | KPI 값과 T-26 |
