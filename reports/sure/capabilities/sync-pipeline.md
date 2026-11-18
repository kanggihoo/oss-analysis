---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-17
updated: 2026-11-17
sources:
  - app/models/sync.rb
  - app/models/concerns/syncable.rb
  - app/models/sync_schedule.rb
  - app/models/family/syncer.rb
  - app/models/account/syncer.rb
  - app/models/family/sync_complete_event.rb
  - app/models/account/sync_complete_event.rb
  - app/models/kraken_item.rb
  - app/models/kraken_item/syncer.rb
  - app/models/kraken_item/sync_complete_event.rb
  - app/models/binance_item/syncer.rb
  - app/models/coinbase_item/syncer.rb
  - app/models/coinspot_item/syncer.rb
  - app/models/onchain_wallet_item/syncer.rb
  - app/models/simplefin_item/syncer.rb
  - app/models/financekit/processor.rb
  - app/models/demo/generator.rb
  - app/models/demo/financekit_generator.rb
  - app/models/family/financial_data_reset.rb
  - app/models/background_job_console.rb
  - app/models/family.rb
  - app/models/account.rb
  - app/models/entry.rb
  - app/models/loan.rb
  - app/models/setting.rb
  - app/models/current.rb
  - app/models/balance_sheet/sync_status_monitor.rb
  - app/models/concerns/provider_item_ownable.rb
  - app/models/concerns/sync_stats/collector.rb
  - app/models/financekit_item.rb
  - app/jobs/application_job.rb
  - app/jobs/sync_job.rb
  - app/jobs/sync_all_job.rb
  - app/jobs/sync_all_providers_job.rb
  - app/jobs/sync_hourly_job.rb
  - app/jobs/sync_scheduled_items_job.rb
  - app/jobs/sync_cleaner_job.rb
  - app/jobs/entry_scheduled_sync_job.rb
  - app/jobs/identify_recurring_transactions_job.rb
  - app/services/auto_sync_scheduler.rb
  - app/services/cron_scheduler.rb
  - app/controllers/application_controller.rb
  - app/controllers/concerns/auto_sync.rb
  - app/controllers/syncs_controller.rb
  - app/controllers/sync_schedules_controller.rb
  - app/controllers/accounts_controller.rb
  - app/controllers/settings/providers_controller.rb
  - app/controllers/settings/hostings_controller.rb
  - app/controllers/kraken_items_controller.rb
  - app/controllers/sophtron_items_controller.rb
  - app/controllers/simplefin_items_controller.rb
  - app/controllers/settings/background_jobs_controller.rb
  - app/controllers/concerns/localize.rb
  - app/controllers/api/v1/base_controller.rb
  - app/controllers/api/v1/sync_controller.rb
  - app/controllers/api/v1/syncs_controller.rb
  - app/views/api/v1/syncs/_sync.json.jbuilder
  - app/views/api/v1/syncs/index.json.jbuilder
  - app/views/api/v1/syncs/show.json.jbuilder
  - app/views/api/v1/sync/create.json.jbuilder
  - app/views/accounts/_sync_controls.html.erb
  - app/views/shared/notifications/_sync_toast.html.erb
  - config/schedule.yml
  - config/sidekiq.yml
  - config/initializers/sidekiq.rb
  - config/routes.rb
  - db/schema.rb
  - Gemfile.lock
  - docs/llm-guides/architecture.md
  - test/models/sync_test.rb
  - test/models/provider_item_sync_complete_events_test.rb
depends: []
status: draft
---

# Sync 파이프라인 (공유 계약)

> `Syncable`을 구현한 객체(Family, Account, 외부 연동 item)가 `sync_later`로 `Sync` 레코드를 만들고, job이 그것을 부모-자식 트리로 실행해 `pending → syncing → completed | failed | stale`로 마무리한 뒤 후속 처리와 완료 이벤트를 호출하는 계약이다. 새 연동을 직접 만들 때 맞춰야 하는 규칙을 뽑았다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 Family 전체 sync(매일 새벽 예약 또는 사용자의 "Sync all")다. 연동 item 하나와 그 아래 Account까지 이어진다.

1. 트리거(R-19, R-24, R-25)가 `family.sync_later`를 부른다. 같은 Family에 5분 안의 진행 중 `Sync`가 없으면 `Sync`(status `pending`)를 만들고 `SyncJob`을 큐에 넣는다. 있으면 그것을 돌려준다(R-05, R-04).
2. `SyncJob`이 `Sync#perform`을 호출한다. `pending`이 아니면 아무것도 하지 않고, 아니면 `syncing`으로 바꾼 뒤 syncable의 Syncer를 실행한다(R-08, R-09).
3. Family Syncer는 Family의 모든 연동 item과 수동 Account에 대해 자식 `Sync`를 `sync_later(parent_sync: 이 sync)`로 만든다(R-15). 자식 하나하나가 같은 방식으로 큐에 들어가 병렬로 돈다.
4. 연동 item의 Syncer는 외부 데이터를 가져와 처리한 뒤(이 스펙 밖, `./provider-import-adapter.md`), 그 item에 연결된 Account마다 자식 `Sync`를 만든다. Account Syncer는 시장 데이터와 잔액 재계산을 "호출"한다(R-16, R-17).
5. 자기 Syncer가 끝난 `Sync`는 `finalize`를 호출한다. 자식이 모두 끝났을 때만 `completed`(자식 중 `failed`가 있으면 `failed`, 취소 요청이 있었으면 `stale`)로 확정하고, `stale`이 아니면 post-sync와 완료 이벤트를 실행한다. Family의 post-sync는 transfer 자동 매칭, 가맹점 로고 보충, 규칙 적용 job enqueue를 호출한다(R-15). post-sync와 완료 이벤트는 `Sync` 행을 잠근 transaction 안에서 실행된다(R-11). 이어 부모의 `finalize`를 부른다(R-10, R-11).
6. 큐에서 사라진 job 때문에 24시간 넘게 끝나지 않은 `Sync`는 매시 정각의 `SyncCleanerJob`이 `stale`로 바꾼다(R-14).

다른 트리거(수동 item sync, 예약 `SyncSchedule`, 시간별, 로그인, 거래 저장 등)도 대부분 같은 `sync_later`로 들어오며 시작하는 syncable의 종류만 다르다. 예외로 `sync_later`를 거치지 않고 `Sync`를 직접 만들거나 상태를 직접 바꾸는 경로가 있고(R-34, R-16), 이 경로에서는 아래 흐름의 보장 일부가 성립하지 않는다.

### 1.2 범위·통합 지점 [필수]

- 제공: `Sync` 레코드의 생명주기, `sync_later`의 합치기와 부모-자식 연결, 트리거와 예약 job 구성, 취소와 stale 정리, post-sync와 완료 이벤트의 호출 경계, 중복 실행 방지, 사용자·API에 보이는 상태, 새 연동이 구현해야 할 Syncer 계약.
- 제외: 개별 provider의 import·process 로직(각 `*_item/importer`, `*_account/processor`)은 `./provider-import-adapter.md`의 몫이다. 잔액 계산(`Balance::Materializer`), transfer 매칭, 규칙 적용, 반복 거래 식별은 각각 호출까지만 쓰고 계산은 다른 스펙의 몫이다(`./account-balances.md`는 feature map 행 1 스펙이며 아직 없다). Plaid의 transactions refresh 요청·후속 sync job 체인과 Plaid 외 provider 전용 후속 job(`*_follow_up_sync_job`, `*_activities_fetch_job`)은 연동별 흐름이라 뺐다. `SyncPropertyValuationsJob`은 이름에 sync가 들어 있지만 `Sync`를 쓰지 않는 월간 부동산 시세 갱신이므로 뺐다.
- 외부 의존: (a) 지연·예약 실행과 큐 우선순위를 지원하는 job 시스템, (b) 행 단위 잠금(`SELECT ... FOR UPDATE`)과 transaction을 지원하는 DB, (c) cron 표현식(IANA 시간대 포함)으로 반복 job을 등록·제거하는 scheduler, (d) 사용자 화면으로 보내는 실시간 push(Turbo Streams의 `broadcast_replace_to`, `broadcast_refresh`), (e) 오류 수집기(Sentry), (f) 진단 로그(`DebugLogEntry.capture`), (g) 앱 전역 설정(`Setting`), (h) Family별 시간대(`family.resolved_time_zone`).
- 소유 상태·부작용: `syncs`, `sync_schedules` 행, Family의 `latest_sync_activity_at`·`latest_sync_completed_at`·`last_sync_all_attempted_at`, 위 설정의 cron 등록. post-sync와 완료 이벤트는 다른 기능의 상태(transfer, 규칙 실행, 반복 거래, 화면)를 간접으로 바꾸지만 그 상태의 소유자는 이 스펙이 아니다.

### 1.3 인터페이스와 데이터 의미 [필수]

**`syncs` 레코드** (C-16)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `id` | uuid | 기본값은 DB가 만드는 무작위 uuid |
| `syncable_type`, `syncable_id` | string, uuid | 둘 다 not null. 대상 객체의 종류(`Family`, `Account`, `KrakenItem` 등)와 id. 다형 참조이고 DB 외래 키는 없다. 종류 이름은 상속 최상위 클래스 이름이다 |
| `parent_id` | uuid, null 가능 | 같은 테이블 `syncs.id`를 가리키는 외래 키. 없으면 루트. 부모를 지우면 자식도 지운다(애플리케이션 규칙, R-33) |
| `status` | string | 기본 `"pending"`, DB는 null을 허용한다. 값은 `pending`, `syncing`, `completed`, `failed`, `stale` |
| `error` | string, null 가능 | 실패 시 예외 메시지 또는 아래 R-08의 고정 문구. 상태 전이와 별개의 쓰기로 저장한다 |
| `window_start_date`, `window_end_date` | date, null 가능 | 잔액 재계산 범위. 둘 다 null이면 제한 없는 전체 sync. 시작이 끝보다 늦으면 저장이 거부된다(R-03) |
| `pending_at`, `syncing_at`, `completed_at`, `failed_at` | datetime, null 가능 | 해당 상태로 전이한 시각(R-02). `stale`용 시각 컬럼은 없다 |
| `cancel_requested_at` | datetime, null 가능 | 취소 요청 시각. 루트 `Sync`에만 찍힌다(R-13) |
| `full_resync_requested` | boolean | 기본 false, not null. 실행 중 입력이 바뀌어 끝난 뒤 전체 sync가 필요하다는 표시(R-12) |
| `sync_stats` | text(JSON 문자열) | provider Syncer가 요약 통계를 담는 자유 형식 map. 파이프라인은 읽지 않는다(화면 표시용). 검색 범위는 2.1 R-33 |
| `data` | jsonb | 읽거나 쓰는 코드를 찾지 못했다(2.1 R-33) |
| `created_at`, `updated_at` | datetime | not null |

인덱스: `parent_id`, `status`, `(syncable_type, syncable_id)`, `(syncable_type, syncable_id, created_at 내림차순, id 내림차순)`. 최신순 정렬(`ordered`)은 `created_at` 내림차순, 같으면 `id` 내림차순이다.

**`sync_schedules` 레코드** (C-16): 연동 item 하나의 개별 주기.

| 필드 | 의미·제약 |
|---|---|
| `syncable_type`, `syncable_id` | not null. `(type, id)` 조합에 unique 인덱스가 있어 연결당 최대 1개다. 허용 종류는 R-21 |
| `interval_minutes` | int, not null. 허용값 15, 30, 60, 120, 240, 360, 720 |
| `next_run_at` | datetime, not null. `next_run_at`에 일반 인덱스가 있다 |

**Family 컬럼** (C-16): `auto_sync_on_login` boolean 기본 true not null. `last_sync_all_attempted_at` datetime null 가능. `latest_sync_activity_at`, `latest_sync_completed_at` datetime 기본값은 행 생성 시각.

**앱 전역 설정** (`Setting`, C-12): `auto_sync_enabled`(환경변수 `AUTO_SYNC_ENABLED`, 기본 켜짐), `auto_sync_time`(`AUTO_SYNC_TIME`, 기본 `"02:22"`), `auto_sync_timezone`(`AUTO_SYNC_TIMEZONE`, 기본 `"UTC"`). 시간 형식은 정규식 `\A([01]?\d|2[0-3]):([0-5]\d)\z`다.

**Syncable 객체가 제공하는 연산** (R-05, R-30)

| 연산 | 입력 → 출력 | 의미 |
|---|---|---|
| `sync_later(parent_sync?, window_start_date?, window_end_date?)` | → `Sync` | 새 `Sync`를 만들거나 진행 중인 것을 합쳐 돌려준다(R-05) |
| `syncing?` | → bool | 보이는(visible) 진행 중 `Sync`가 있는가(R-04) |
| `last_synced_at` | → datetime 또는 null | 가장 최근 `completed` `Sync`의 `completed_at` |
| `last_sync_created_at` | → datetime 또는 null | 가장 최근 `Sync`(상태 무관)의 `created_at` |
| `latest_sync_record`, `latest_completed_sync_record` | → `Sync` 또는 null | 최신(`created_at`, 같으면 `id` 내림차순) `Sync`, 그중 `completed`인 최신 `Sync`. 화면이 요청 단위로 미리 조회해 둔 값이 있으면 그것을 먼저 쓴다(R-30) |
| `sync_error` | → string 또는 null | 최신 `Sync`의 `error`, 없으면 그 자식들의 `error` 중 첫 non-null |
| `perform_sync(sync)`, `perform_post_sync`, `broadcast_sync_complete` | | 각각 Syncer와 SyncCompleteEvent로 위임한다 |

**새 연동 item이 맞춰야 할 계약.** 아래를 모두 만족하면 Family 전체 sync, 예약 주기, `Sync` 조회 범위, 반복 거래 식별 gate에 별도 등록 없이 참여한다(R-32). 화면의 연동 목록(계정 화면의 최신 `Sync` 조회가 item 27종을 직접 나열), 설정 화면의 provider별 sync(`PANEL_SYNCABLE_TYPES`), 시간별 sync 대상, API의 provider 연결 목록은 별도로 등록해야 한다(R-32).

| 요구 | 내용 |
|---|---|
| Family 연결 | Family가 `<이름>_items`로 끝나는 has-many 연결을 가진다. 연결이 가리키는 모델이 Syncable이어야 한다 |
| `syncable` 범위(scope) | 지금 sync해도 되는 item만 고르는 조회. 원본 대부분은 "삭제 예약(`scheduled_for_deletion`)이 아닌 것"이다. 빈 결과를 돌려주면 그 모델은 Family sync에서 빠진다(FinanceKit이 그렇다) |
| Syncer | `Syncer(item)` 생성 후 `perform_sync(sync)`와 `perform_post_sync`를 가진다. 원본 연동 item 28개 중 27개가 Syncer를 가지며(FinanceKit만 없음) 대부분의 `perform_post_sync`는 비어 있다 |
| 완료 이벤트 | `SyncCompleteEvent(item).broadcast`. 원본 item 구현은 모두 Family의 완료 이벤트(`family.broadcast_sync_complete`)를 호출하는 것으로 확인했고 item 카드를 직접 push하지 않는다(R-18) |
| 선택 훅 | `scheduled_for_deletion?`(있으면 R-08이 실행 중에도 검사), `sync_later_with_provider_refresh`(있으면 R-22와 R-25가 이쪽을 부른다), `manageable_by?(user)`(R-23의 편집 권한) |
| Account 연결 | `perform_sync` 안에서 연결된 Account마다 `account.sync_later(parent_sync: sync, window_start_date:, window_end_date:)`를 부른다(R-16) |

**진입점**: 사용자·API가 sync를 시작하는 경로는 R-25, R-24, R-26에 있다. 취소는 `POST /syncs/:id/cancel`(R-27), 주기 편집은 `GET/PATCH /sync_schedule?syncable_type=&syncable_id=`(R-23), API는 `POST /api/v1/sync`, `GET /api/v1/syncs`, `GET /api/v1/syncs/latest`, `GET /api/v1/syncs/:id`(R-31)다.

**job 구성** (C-12, C-13, R-29)

| job | queue | 시작 | 중복 방지 | 하는 일 |
|---|---|---|---|---|
| `SyncJob(sync, balances_only: false)` | high_priority | `sync_later`가 `Sync`당 하나 | 없음(R-08 상태 guard가 대신함) | `sync.perform` |
| `SyncAllJob` | scheduled | 동적 cron `sync_all_accounts`(R-19) | 실행 완료 전까지 같은 job 중복 금지, 충돌 시 로그만 | 모든 Family에 `sync_later` |
| `SyncAllProvidersJob(family_id)` | high_priority | 설정 화면 "Sync all"(R-25) | `family_id` 단위로 위와 같음 | 한 Family에 `sync_later` |
| `SyncHourlyJob` | scheduled | cron `0 * * * *` | 위와 같음 | 시간별 대상 item `sync_later`(R-20) |
| `SyncScheduledItemsJob` | scheduled | cron `*/15 * * * *` | 위와 같음 | 만기 `SyncSchedule` 처리(R-22) |
| `SyncCleanerJob` | scheduled | cron `0 * * * *` | 없음 | `Sync.clean`과 비 sync 정리(R-14) |
| `EntryScheduledSyncJob(entry_id)` | low_priority | 미래 날짜 거래 저장 시 그 날짜 00:05(Family 시간대)에 지연 실행 | 없음 | `account.sync_later`(R-26) |

`SyncJob`의 `balances_only:` 인자는 실행 중에만 `sync`에 붙는 임시 플래그(`balances_only?`)이고 DB에 저장하지 않는다. 원본에서 `true`로 넘기는 곳은 SimpleFIN 컨트롤러 하나이며, 이 플래그를 읽는 쪽도 SimpleFIN 전용이라 이 스펙은 인자 존재만 기록한다.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Sync` 상태와 전이 | 초기값 `pending`. 허용 전이는 `start`(`pending → syncing`), `complete`(`syncing → completed`), `fail`(`syncing → failed`), `mark_stale`(`pending` 또는 `syncing → stale`)뿐이다. `completed`, `failed`, `stale`은 종료 상태이고 나가는 전이가 없다. 허용되지 않은 전이를 호출하면 예외를 던지는 것이 AASM 기본 동작이다. 호출하는 쪽은 `may_start?`, `may_fail?`로 먼저 확인한다. 이 전이표는 `Sync` 객체가 메모리에서 아는 상태를 기준으로 하므로, 호출하는 쪽이 오래된 메모리 객체로 가드하면 DB에서 이미 종료 상태가 된 `Sync`를 덮을 수 있다. 일부 provider Syncer는 전이표를 우회해 `status`를 직접 쓰기도 한다(R-16) | 코드 확인(전이표) / 추론(예외 동작) |
| R-02 | 전이와 저장 | 전이할 때 해당 상태의 시각 필드(`syncing_at`, `completed_at`, `failed_at`)를 찍는다. `stale`은 시각 컬럼이 없어 `updated_at`만 남는다. `Sync`가 만들어지거나 갱신될 때마다(commit 후) 그 Family의 `latest_sync_activity_at`을 현재로 바꾼다. syncable이 없거나 Family가 저장돼 있지 않으면 이 갱신은 건너뛴다. `complete` 전이의 commit 후 처리는 `latest_sync_completed_at`을 현재로 바꾼다. `finalize` 안에서 `complete`가 일어나면 이 처리는 `finalize`의 transaction이 commit될 때 실행되므로 post-sync와 완료 이벤트(R-11)가 끝난 뒤다(추론: after_commit_everywhere는 바깥 transaction의 commit까지 미룬다). `start` 전이의 commit 후 처리는 이 syncable이 오늘(Family 시간대 하루) 만든 `Sync`가 10개를 넘으면 오류 수집기에 경고를 보낸다. `start`와 `complete`의 commit 후 처리에는 syncable·Family가 없을 때의 guard가 없어 `nil` 호출 예외가 난다(R-08 (2)) | 코드 확인 / 추론(timestamps 세부, commit 후 실행 순서) |
| R-03 | `window_start_date`와 `window_end_date`가 모두 있고 시작이 끝보다 늦음 | 저장이 거부된다(`window_end_date`에 오류). 한쪽이라도 null이면 검사하지 않는다 | 코드 확인 |
| R-04 | "보이는(visible)" 진행 중 `Sync`의 정의 | status가 `pending` 또는 `syncing`이고, 생성 후 5분이 지나지 않았고, `cancel_requested_at`이 null인 `Sync`. 5분이 넘은 진행 중 `Sync`는 DB에서 아직 진행 중이어도 visible이 아니다. `syncing?`과 UI 스피너는 visible만 본다. 취소가 요청된 `Sync`는 즉시 visible에서 빠진다 | 코드 확인 |
| R-05 | `sync_later(parent_sync, window_start_date, window_end_date)` | syncable 행을 잠그고 transaction 안에서 처리한다. visible `Sync`가 이미 있으면 새로 만들지 않고 그 `Sync`를 돌려준다. 이때 (a) 창 확장을 시도하고(R-06), (b) 부모가 주어졌고 그 `Sync`에 부모가 없으면 부모를 붙인다(이미 부모가 있으면 바꾸지 않는다). visible `Sync`가 없으면 `pending` `Sync`를 만들고(부모·창 저장) `SyncJob`을 큐에 넣은 뒤 돌려준다. `Sync`를 만드는 경로가 이것 하나는 아니다(R-34) | 코드 확인 |
| R-06 | 진행 중 `Sync`에 더 넓은 창으로 `sync_later`가 들어옴 | `pending`인 `Sync`만 확장한다. 시작은 두 값 중 이른 쪽, 끝은 늦은 쪽이다. 어느 한쪽이라도 null(제한 없음)이면 그쪽 결과도 null이다. 이미 시작·끝이 모두 null이면 변경하지 않는다. `syncing`인 `Sync`는 창을 넓히지 않으므로 그 요청은 현재 실행에 반영되지 않는다 | 코드 확인 |
| R-07 | job을 큐에 넣는 시점 | 감싸는 DB transaction이 commit된 뒤에 큐에 넣는다. rollback되면 넣지 않는다. 이렇게 하지 않으면 worker가 commit 전에 job을 꺼내 `Sync`를 못 찾고(직렬화 인자 복원 실패) job이 조용히 버려져 `Sync`가 `pending`에 머문다. job 인자를 복원하지 못하면 그 job은 재시도 없이 버린다 | 코드 확인 |
| R-08 | `Sync#perform` 시작 가드 | (1) status가 `pending`이 아니면(서버 재시작·중복 enqueue·취소로 `stale`이 된 경우) 경고 로그만 남기고 아무것도 하지 않는다. 이 분기는 부모 `finalize`를 부르지 않는다. (2) syncable이 없으면 `start` 후 `fail`하고 `error`를 `"Syncable record was deleted"`로 저장하려 한다. 그런데 `start` 전이의 commit 후 처리(R-02, 경고 확인)가 `syncable.syncs`를 부르고 이 분기에는 rescue가 없어 `nil` 호출 예외가 난다. 그 예외가 `perform` 밖으로 전파되는지는 AASM 5.5.1과 after_commit_everywhere 1.6.0의 동작이라 추론이다. 전파되면 `fail`과 `error` 저장이 실행되지 않아 `Sync`는 `syncing`에 남고 24시간 sweep(R-14)이 `stale`로 바꾼다. 따라서 `failed` + 고정 `error`가 실제로 기록된다는 보장은 코드만으로 없다. 이 분기는 syncable만 callback 없이 지워진 경우에 닿는다(syncable을 정상 삭제하면 그 `Sync`도 함께 지워진다, R-33. 추론). (3) syncable이 `scheduled_for_deletion?`에 true를 답하면 `start`, `fail` 후 `error`를 `"Syncable record is scheduled for deletion"`으로 저장한다(이 분기는 syncable이 있어 (2)의 문제가 없다). (2), (3)은 Syncer를 실행하지 않고 부모 `finalize`도 부르지 않는다. 그래서 이 `Sync`가 부모의 마지막 미종료 자식이었다면 부모는 다른 `finalize` 호출이 없는 한 24시간 sweep(R-14)까지 `syncing`에 남는다 | 코드 확인 / 추론((2)의 예외 전파, 부모 잔류) |
| R-09 | `Sync#perform` 실행 | Family 시간대(없으면 앱 기본)에서 실행한다. `start` 후 syncable의 Syncer `perform_sync(sync)`를 부른다. Syncer가 `StandardError`를 던지면 `Sync` 행을 잠그고 다시 읽은 뒤 `fail`이 가능할 때(`syncing`일 때)만 `failed`로 바꾸고, 그 뒤 `error`를 예외 메시지로 저장하고, 오류 수집기에 보낸다. 이 Syncer 예외는 `perform` 밖으로 던지지 않는다. 다만 `start` 전이, 위 rescue 절 안의 쓰기, `ensure`의 `finalize`에는 rescue가 없어 이들의 예외(DB 오류 등)는 `perform` 밖으로 나가 job 시스템의 처리로 넘어간다. 성공이든 Syncer 실패든 마지막에 항상 `finalize`(R-10)를 부른다. 따라서 `perform` 자체가 `completed`로 바꾸는 일은 없고, `perform` 경로의 `completed`는 `finalize`에서만 생긴다(다른 경로는 R-16, R-34) | 코드 확인 |
| R-10 | `finalize`(자기 자신과 부모) | 행을 잠그는 transaction을 열고 자식을 읽는다. 자식 중 `pending` 또는 `syncing`이 하나라도 있으면 아무것도 바꾸지 않고 돌아온다(부모 전파도 없음). 모두 끝났고 자기가 `syncing`이면 (a) `cancel_requested_at`이 있으면 `stale`, (b) 아니면 자식 중 `failed`가 하나라도 있으면 `failed`, (c) 아니면 `completed`로 바꾼다. `stale` 자식은 부모를 실패시키지 않는다. 자기가 `syncing`이 아니어도(이미 `failed`, `completed`이거나 `pending`) 이 지점에 도달하면 `stale`이 아닐 때 post-sync를 실행한다(`pending`인 `Sync`에 `finalize`가 닿아도 전이 없이 post-sync가 실행된다). post-sync와 완료 이벤트(R-11)는 이 transaction 안에서 실행되고, transaction이 끝난 뒤 부모가 있으면 부모의 `finalize`를 부른다. 자식이 `failed`이면 부모도 `failed`가 되어 실패가 루트까지 올라간다(R-16의 SimpleFIN 경로는 예외). 조기 확정 경합: 부모 Syncer가 자식을 하나씩 만드는 동안 먼저 만든 자식이 끝나면 그 자식이 부르는 부모 `finalize`는 그 시점에 존재하는 자식만 보고 부모를 `completed`로 확정하고 post-sync를 실행할 수 있다. 부모 Syncer가 이후 만든 자식이 끝나면 부모 `finalize`가 다시 닿아 post-sync가 한 번 더 실행된다(추론: Syncer가 부모 행을 잠그지 않는 구조에서 읽은 것이며 재현하지 않았다) | 코드 확인 / 추론(조기 확정 경합) |
| R-11 | post-sync와 완료 이벤트 | `finalize`가 `stale`이 아닌 상태로 끝에 도달하면 syncable의 `perform_post_sync`를 부르고, 이어 `broadcast_sync_complete`를 부른다. 이 둘은 `finalize`가 연 transaction 안에서, 그 `Sync` 행의 잠금을 쥔 채 실행된다. 따라서 `completed` 상태와 `latest_sync_completed_at`은 post-sync와 broadcast가 끝난 뒤에 commit되고, post-sync가 오래 걸리면 그만큼 행 잠금이 유지된다(이 순서가 의도인지는 U-06). 둘 중 하나가 예외를 던지면 로그와 오류 수집기에 보내고 삼키며 `Sync`의 상태는 바뀌지 않는다. `perform_post_sync`가 던지면 broadcast는 실행되지 않는다. 마지막에는 어느 경우든 full resync 확인(R-12)을 한다. 실패한 `Sync`도 post-sync를 실행한다. 실행 여부를 기록하는 필드가 없어, 같은 `Sync`에 대해 `finalize`가 모든 자식 종료 뒤에 여러 번 호출되면(자식 두 개가 거의 동시에 끝나 각각 부모를 finalize하는 경우, 또는 R-10의 조기 확정) post-sync도 그 횟수만큼 실행될 수 있다. 정확히 한 번을 보장하지 않으므로 post-sync 대상 연산은 반복해도 안전해야 한다 | 코드 확인 / 추론(동시 실행 시 중복, commit 시점) |
| R-12 | full resync 요청 | 다른 기능(원본은 Loan의 잔액 입력값 변경)이 실행 중인 `Sync`에 `full_resync_requested = true`를 찍는다. 그 `Sync`가 `stale`이 아닌 상태로 post-sync 단계를 마치거나(R-11의 마지막 단계), `stale`로 전이되면(commit 후) DB에서 새로 읽어 확인한다. 값이 true이면, 같은 syncable의 visible이고 `syncing`인 다른 `Sync`가 있으면 거기에 `full_resync_requested = true`를 옮기고, 없으면 `sync_later`(창 없음 = 전체)를 부른다. 그 뒤 이 `Sync`의 플래그를 false로 내린다. 이 처리의 예외는 삼키고 기록한다. 취소로 `stale`이 된 `Sync`도 같은 처리를 한다 | 코드 확인 |
| R-13 | 취소 요청 `request_cancel!`(루트 `Sync`) | 행 잠금 아래에서 (a) `pending`이면 `cancel_requested_at`을 찍고 즉시 `stale`로 바꾼다(큐에 남은 job은 R-08(1)로 무시된다), (b) `syncing`이면 `cancel_requested_at`만 찍는다, (c) 종료 상태이면 `false`를 돌려주고 끝낸다. (a), (b) 뒤에는 `pending`인 자손을 재귀로 `stale`로 바꾼다(`syncing`인 자손은 상태를 건드리지 않고 그 아래로만 내려간다). 이어 루트에만 `finalize`를 부른다. 중간 노드에는 `finalize`를 부르지 않는다. 이미 실행 중인 자손의 job은 중단되지 않고 끝까지 돌며 끝난 결과(`completed`, `failed`)는 유지된다. 그 job이 끝날 때 자기 `finalize`가 자기 자식을 확인하고 부모로 전파한다. 따라서 루트가 `stale`로 끝나는 것(R-10 (a), post-sync 없음)은 루트의 자식이 모두 `pending` 또는 실행 중인 job을 가진 `syncing`인 깊이 2에서만 성립한다. 루트 → 자식(`syncing`, job은 이미 끝나 자기 자식만 기다림) → 손자(`pending`)처럼 3단 이상이면 손자만 `stale`이 되고 자식과 루트는 `syncing`에 남는다(`cancel_requested_at` 때문에 visible에서는 빠진다). 이 노드들은 24시간 sweep(R-14)이 `stale`로 바꿀 때까지 남는다. 취소 플래그는 루트에만 있고 자손에는 퍼지지 않는다. 원본에서 이 플래그를 읽는 코드는 Family Syncer의 자식 생성 반복과 SimpleFIN Syncer뿐이다(검색 범위는 2.1) | 코드 확인 |
| R-14 | stale 정리 | `SyncCleanerJob`이 매시 정각에 `Sync.clean`을 호출한다. `pending` 또는 `syncing`이고 `created_at`이 24시간보다 오래된 `Sync`를 하나씩 `mark_stale`한다(`error`는 건드리지 않는다. 행 잠금·다시 읽기 없이 조회 시점의 메모리 객체로 전이한다). 부모·자식으로 전파하지 않고 post-sync를 실행하지 않는다. `stale` 전이 commit 후 R-12의 확인이 실행된다. 하나씩 도는 반복에는 개별 rescue가 없어 한 건에서 예외가 나면 그 run의 남은 정리는 멈추고(job은 이 정리 항목의 예외를 로그와 오류 수집기에 보내고 다음 정리 항목으로 간다) 남은 `Sync`는 다음 정시 run이 다시 처리한다. 이 job의 다른 정리 항목(Import, ImportSession, FamilyExport, PdfImport, 일부 provider 계정의 `activities_fetch_pending` 6시간 초과 플래그)도 각자 독립해서 실패해도 다음 항목을 계속한다. `stale`이 되는 경로는 이것 외에 취소(R-13)와 관리자 background jobs 콘솔의 취소 동작(진행 중 `Sync`에 `mark_stale`, 전파 없음)이 있다. 외부에서 `stale`이 된 `Sync`의 job이 Account·Family Syncer 경로로 끝나면: 이후 그 job의 `fail`은 R-01에 따라 일어나지 않지만 `error`는 저장되고, `finalize`는 상태를 바꾸지 않고 post-sync도 실행하지 않은 채 부모 `finalize`만 이어간다. item Syncer 경로에서는 R-16의 덮어쓰기 때문에 이 문장이 성립하지 않는다 | 코드 확인 / 추론(동시 완료와의 경합) |
| R-15 | Family `perform_sync(sync)`와 post-sync | 먼저 구독 시험 기간 상태를 갱신하는 연산을 한 번 부른다(`trialing`이고 기간이 끝났으면 구독 상태를 `paused`로 저장). 이 연산이 예외를 던지면 Syncer가 실패한다. 그 다음 자식 syncable 목록 `(Family의 모든 syncable 연동 item의 syncable 범위) + (연동에 연결되지 않은 수동 Account)`를 차례로 돌며 각각 `sync_later(parent_sync: sync, window_start_date: sync.window_start_date, window_end_date: sync.window_end_date)`를 부른다. 자식마다의 rescue가 없어 한 자식의 `sync_later`가 예외를 던지면 반복이 중단되고 Family `Sync`가 `failed`가 된다(이미 만든 자식은 그대로 실행되고 R-10에 따라 마지막에 post-sync). 반복 도중 매번 `cancel_requested_at`을 DB에서 새로 읽어, 설정돼 있으면 남은 자식 생성을 중단한다. 연동에 연결된 Account는 이 목록에 없고 그 item의 Syncer가 맡는다. "수동 Account"는 `account_providers` 행이 없고 `plaid_account_id`, `simplefin_account_id`가 모두 null인 Account이며, 상태(`active`, `draft`, `disabled`, `pending_deletion`) 필터는 없다. Family `perform_post_sync`(R-11이 호출): (1) Family 전체 transfer 자동 매칭, (2) Family 거래의 provider 가맹점 로고 보충(내부에서 예외를 삼키고 로그), (3) 활성 규칙 적용 job(`ApplyRulesJob`) enqueue | 코드 확인 |
| R-16 | 연동 item `perform_sync`의 의무와 `Sync` 상태 직접 변경(Kraken 예) | Kraken 순서: 자격 증명 확인, 외부 데이터 가져오기(import), item 상태가 `requires_update`였다면 `good`으로 복구, 설정 상태 통계 저장, 연결되지 않은 provider 계정이 있으면 item의 `pending_account_setup`을 true로 없으면 false로 갱신, 연결된(visible 상태) 계정이 있을 때만 처리(process) 후 그 Account들에 `sync_later(parent_sync: sync, 같은 창)`. 자격 증명이 없으면 item 상태를 `requires_update`로 바꾸고 `sync`를 직접 `failed`+`error`로 만든 뒤 예외 없이 반환한다. 인증·권한·OTP 오류는 item 상태를 `requires_update`로 바꾸고 `sync`를 직접 `failed`+`error`로 만든 뒤 예외를 다시 던진다. 그 밖의 예외도 직접 `failed`+`error`로 만든 뒤 다시 던진다(R-09가 그 예외를 `error`로 다시 저장). Account sync 예약이 한 계정에서 실패해도 그 오류를 모아 반환할 뿐 item sync를 실패시키지 않는다. 자식 예약 뒤 item `Sync`는 `syncing`으로 남고 자식이 끝날 때 R-10이 완료시킨다. 직접 변경의 규칙(원본 동작): Kraken, Binance, Coinbase, Coinspot, OnchainWallet의 `mark_failed`는 `may_start?`이면 `start!`, `may_fail?`이면 `fail!`을 부르고 아니면 `status`를 `failed`로 직접 쓴다(Binance, Coinbase는 시작 전에 메모리 상태가 `completed`이면 건너뛴다). 판단에 쓰는 `sync`는 `Sync#perform`이 들고 있는 메모리 객체이고 DB를 다시 읽지 않는다. 그래서 job이 도는 동안 DB에서 `stale`이 된 `Sync`(취소, 24시간 정리, 관리자 콘솔)도 `failed`로 덮인다(추론: AASM이 메모리의 전이 결과를 쓴다). 이어 R-09의 rescue가 행을 다시 읽지만 이미 `failed`이고, R-10은 `stale`이 아니므로 post-sync를 실행한다. SimpleFIN의 `mark_completed`는 행 잠금 아래에서 `cancel_requested_at`이나 종료 상태를 확인해 건너뛰므로 이 덮어쓰기가 없지만, SimpleFIN `mark_failed`는 위 패턴을 쓴다. SimpleFIN `mark_completed`는 `finalize`를 거치지 않고 `complete!`를 직접 부르며 자식 Account `Sync` 예약 직후에 호출하므로 자식이 `pending`이어도 item `Sync`가 `completed`가 되고, 이후 자식이 `failed`여도 item `Sync`는 `failed`가 되지 않는다 | 코드 확인(Kraken, Binance, Coinbase, Coinspot, OnchainWallet, SimpleFIN) / 추론(DB 덮어쓰기) |
| R-17 | Account `perform_sync`와 post-sync | `perform_sync`: (1) 시장 데이터(환율·종목 시세) 보충 가져오기, 예외는 삼키고 오류 수집기에 보낸다. (2) 잔액 재계산 호출: 연동된 Account는 reverse, 수동 Account는 forward 전략이며 `window_start_date`를 넘긴다(`window_end_date`는 넘기지 않는다). 이 호출의 예외는 삼키지 않으므로 Account `Sync`가 `failed`가 된다. (3) IBKR 연동 계정이면 과거 잔액 덮어쓰기(예외는 삼킴). (4) 잔액 기준일과 가장 최근 보유 종목 날짜의 차이 진단 기록(예외는 삼킴). `perform_post_sync`: 그 Family에 대해 해당 Account만 대상으로 transfer 자동 매칭을 호출한다 | 코드 확인 |
| R-18 | 완료 이벤트 `broadcast` | Family 이벤트: Family 스트림에 `#sync-toast`와 `#accounts-sync-controls`를 교체하는 push를 두 번 보내고, 이어 반복 거래 패턴 식별을 예약한다(30초 debounce 후 실행, 이 스펙 밖. 예약 실패 예외만 삼키고 앞의 push의 예외는 호출자(R-11)에서 삼킨다). Account 이벤트: Family 이벤트를 호출하고 이어 그 Account 화면 새로고침 push를 보낸다. 연동 item 이벤트(Kraken 예): Family 이벤트를 호출하고, 실패는 경고 로그로 삼킨다. 따라서 Account나 item `Sync` 하나가 끝날 때마다 Family 이벤트가 실행된다. 어느 이벤트도 사용자별 데이터를 담은 화면 조각을 push하지 않는다(모든 구성원이 같은 스트림을 구독하므로 toast가 각 브라우저에서 자기 인증으로 페이지를 다시 불러오게 한다) | 코드 확인 |
| R-19 | 매일 Family sync | `SyncAllJob`이 모든 Family를 순회하며 (Plaid transactions refresh 요청 후) `family.sync_later`를 부른다. Family 한 곳의 예외는 로그로 삼키고 다음 Family로 간다. 이 job의 cron 항목 `sync_all_accounts`는 앱이 `Setting`에서 만들어 등록하며 시각 표현은 `"<분> <시> * * * <IANA 시간대>"`다. `auto_sync_enabled`가 true일 때만 등록하고 false면 제거한다. 환경변수 `AUTO_SYNC_ENABLED`는 값이 정확히 `"1"`일 때만 켜진다(기본 `"1"`). 등록 시점은 worker 프로세스 시작 시, 그리고 설정 화면에서 `auto_sync_enabled` 또는 `auto_sync_time`을 바꿀 때다. 이 설정 화면은 self-hosted 모드에서만 열리고, 변경에는 관리자이면서 인스턴스 설정 관리 권한(super admin이거나, self-hosted 관리자 중 구독이 synthetic이 아니고 Family가 하나뿐인 경우 등)이 필요하다. 시간을 바꿀 때 `auto_sync_timezone`은 바꾼 사용자의 Family `timezone`(비었으면 `"UTC"`)으로 저장한다. 시간 형식이 틀리면 기본값 `02:22`로 대체하고 로그를 남긴다. 알 수 없는 시간대 이름은 로그 없이 UTC로 대체한다. 등록 실패는 오류로 기록하되 worker 시작은 막지 않는다. 시간대는 IANA 이름이라 DST를 따라간다 | 코드 확인 |
| R-20 | 시간별 sync | `SyncHourlyJob`이 정각마다, 시간별 대상 클래스 목록에 있는 모델의 `active` item(삭제 예약이 아닌 것)에 `sync_later`를 부른다. 원본 목록에는 CoinStats item 하나뿐이다. item 하나의 예외는 로그로 삼키고 다음으로 간다 | 코드 확인 |
| R-21 | `SyncSchedule`의 모양 | `interval_minutes`는 15, 30, 60, 120, 240, 360, 720 중 하나만 허용한다(모두 24시간의 약수). 허용 syncable 종류는 "Family의 `*_items` 연결 중 Syncable인 것"의 모델 이름 집합이다(R-32). 연결 하나당 스케줄 하나다. `next_run_at`은 저장 전에 "현재 시각 이후의 첫 간격 경계"로 정렬한다. 경계는 Unix epoch(UTC 자정)부터 간격 초의 배수다(예: 6시간이면 UTC 00, 06, 12, 18시). 정렬은 간격이 바뀌거나 `next_run_at`이 비었을 때 일어난다. `advance!`는 행을 잠그고 다시 읽은 뒤, `next_run_at`이 아직 미래이면 `false`, 아니면 `next_run_at`을 "지금 이후의 첫 경계"로 옮기고 `true`를 돌려준다. 그 사이 행이 지워졌으면 `false`다 | 코드 확인 |
| R-22 | 15분 틱 `SyncScheduledItemsJob` | `next_run_at`이 현재 이하인 스케줄마다: 허용 종류에서 빠진 종류면 스케줄을 지우고 넘어간다. `advance!`가 `false`면 넘어간다(먼저 advance하므로 sync가 계속 실패해도 그 연결의 주기대로만 재시도한다). 대상 item이 없으면 스케줄을 지운다. item이 자기 모델의 `syncable` 범위에 있으면 `sync_later_with_provider_refresh`가 있는 모델은 그것을, 없는 모델은 `sync_later`를 부른다. 범위에 없으면(삭제 예약 등) 아무것도 하지 않고 스케줄은 남긴다. 스케줄 하나의 예외는 로그와 진단 로그에 남기고 다음으로 간다. 놓친 틱은 따라잡지 않는다(다음 경계로만 이동) | 코드 확인 |
| R-23 | 스케줄 편집 `PATCH /sync_schedule` | 대상은 `syncable_type`, `syncable_id`로 지정하며, 현재 Family의 해당 연결에서만 찾는다. 허용 종류가 아니거나 다른 Family의 id이거나 삭제 예약 중이면 404. 편집 권한은 `manageable_by?`가 있는 item은 그 결과, 없으면 관리자(원본 규칙: 관리자는 모든 연결, 구성원은 본인 소유이고 소유 가능 provider의 연결만). `manageable_by?`는 관리자이면 true이고, 아니면 소유자이면서 소유 가능 provider이고 사용자가 지금도 `member` 역할일 때만 true다(소유했어도 `guest`로 바뀐 사용자는 편집할 수 없다). 권한이 없으면 HTML은 경고와 함께 리다이렉트, 그 외 형식은 403. `sync_schedule[interval_minutes]` 키가 없으면 422(삭제하지 않음). 값이 빈 문자열이면 스케줄을 삭제한다. 값이 있으면 생성 또는 변경하고, 허용되지 않은 값이면 편집 화면을 422로 다시 그린다. 같은 연결에 두 요청이 동시에 스케줄을 만들면 unique 인덱스에 막힌 쪽이 먼저 만들어진 행에 자기 간격을 적용한다 | 코드 확인 |
| R-24 | 로그인 시 자동 sync | 모든 인증된 요청의 앞단에서: Family에 `active` 상태의 계정이 하나라도 있고, Family 자신의 `Sync` 중 가장 최근 `created_at`의 날짜가 오늘 이전(또는 `Sync`가 없음)이고, `auto_sync_on_login`이 true이면 Plaid refresh 요청 후 `family.sync_later`를 부른다. 이미 오늘 만든 `Sync`가 있으면(상태 무관) 부르지 않는다. 앞단 실행 순서는 인증 뒤, 요청별 시간대 전환(`Localize`의 `switch_timezone`) 앞으로 읽었다(`ApplicationController`가 한 줄에서 여러 모듈을 include하며 Ruby는 뒤쪽 인수부터 처리한다는 해석, 추론). 이 해석이 맞으면 "오늘"(`Date.current`)과 최근 `Sync`의 날짜 변환은 Family 시간대가 아니라 앱 기본 시간대(원본은 `config.time_zone`을 지정하지 않아 UTC)로 계산된다 | 코드 확인 / 추론(실행 순서, 시간대) |
| R-25 | 사용자가 직접 sync | (a) `POST /accounts/sync_all`: 요청한 Family에 refresh 요청 후 `family.sync_later`. (b) `POST /accounts/:id/sync`(접근 가능한 계정만): 그 Account가 `syncing?`이면 아무것도 안 한다. 연동 계정이면 연결된 item마다 그 item이 `syncing?`이 아닐 때 `sync_later`(Plaid item은 `sync_later_with_provider_refresh`). 수동 계정이면 `account.sync_later`. (c) `POST /settings/providers/sync_all`(관리자): Family 행의 `last_sync_all_attempted_at`이 null이거나 30초 이전일 때만 그 값을 지금으로 바꾸는 조건부 단일 갱신(갱신된 행이 0이면 거절)을 통과해야 `SyncAllProvidersJob(family_id)`를 enqueue한다. (d) `POST /settings/providers/:provider_key/sync`(관리자): 그 provider 종류의 `syncable` item 중 `syncing?`이 아닌 것에 `sync_later`. (e) `POST /<provider>_items/:id/sync`(원본 Kraken: 관리자): item이 `syncing?`이 아니면 `sync_later`. (f) `POST /api/v1/sync`(쓰기 권한): `family.sync_later`, 응답 202 | 코드 확인 |
| R-26 | 데이터 변경이 거는 sync(호출 경계) | 거래를 바꾸는 흐름은 `entry.sync_account_later`를 호출하고, 이것이 `account.sync_later(window_start_date: 영향 받는 가장 이른 날짜)`를 부른다(잔액 재계산 범위가 그 날짜부터가 된다. 삭제된 거래는 창 없이 전체). 모든 저장이 부르는 것은 아니고 호출 여부는 흐름마다 다르다(`docs/llm-guides/architecture.md:112-115`). 저장한 거래가 미래 날짜면 그 날짜 00:05(Family 시간대)에 `EntryScheduledSyncJob`을 지연 실행해 `account.sync_later`를 부른다. Account를 새로 만들 때는 `skip_initial_sync`가 아니면 `account.sync_later`를 부른다(연동 계정은 건너뛴다. provider sync가 잔액을 만든다). Loan 입력 변경은 R-12의 플래그나 `account.sync_later`를 쓴다. Loan은 실행 중 `Sync`에 플래그를 찍은 뒤 그 `Sync`가 이미 `syncing`이 아니면 호출자가 직접 `account.sync_later`를 부른다. 이때 종료된 `Sync`의 `full_resync_requested`는 true로 남는다(이후 그 `Sync`에 `finalize`가 다시 닿으면 R-12가 한 번 더 sync를 만들 수 있다, 추론) | 코드 확인 |
| R-27 | 취소 `POST /syncs/:id/cancel` | `Sync.for_family(현재 Family, resource_owner: 현재 사용자)`로만 찾는다. 이 범위는 (a) Family 자신, (b) 사용자가 접근할 수 있는 Account(Family의 Account 전체 또는 `accessible_accounts`), (c) Family의 모든 syncable 연동 item의 `Sync`다. 범위 밖이면 404. 연동 item의 `Sync`는 관리자만 취소할 수 있고 그 외 구성원은 404. 취소 성공이면 알림과 함께, 이미 종료된 `Sync`면(`request_cancel!`이 false) 경고와 함께 이전 페이지(`redirect_back_or_to`, 없으면 계정 화면)로 리다이렉트 | 코드 확인 |
| R-28 | 동시 실행 방지 | 층이 여럿이고 완전하지 않다. (1) `sync_later`가 syncable 행을 잠그고 visible `Sync`를 확인하므로 5분 안에서는 syncable당 진행 중 `Sync`가 하나로 합쳐진다. (2) `Sync#perform`의 `pending` 가드가 같은 `Sync`의 중복 실행·재실행을 무시한다. (3) 전이와 `finalize`, 취소, 실패 처리는 `Sync` 행 잠금 아래에서 상태를 다시 읽고 한다. (4) 반복 job(`SyncAllJob`, `SyncAllProvidersJob`, `SyncHourlyJob`, `SyncScheduledItemsJob`)은 job 시스템의 unique lock(완료 전까지, 충돌 시 로그만)으로 중복을 막는다. 빈틈: 5분이 지난 `syncing` `Sync`는 visible이 아니므로 같은 syncable에 새 `Sync`가 만들어져 두 `Sync`가 동시에 실행될 수 있다. `SyncJob`과 `SyncCleanerJob`에는 unique lock이 없다 | 코드 확인 / 추론(동시 실행 결과) |
| R-29 | 큐·재시도 설정 | queue별 가중치: `scheduled` 10, `high_priority` 4, `medium_priority` 2, `low_priority` 1, `default` 1. AI job은 별도 큐 그룹으로 분리해 sync가 굶지 않게 한다. 한 worker의 동시 실행 수 = 총 스레드(기본 3) - AI 스레드(기본 1). 모든 job의 기본 큐는 `low_priority`. 공통 규칙: DB 교착(deadlock)이면 재시도, 인자 복원 실패면 폐기. 반복 job 틱 지각 허용: 기본 600초(환경변수로 조정) | 코드 확인 |
| R-30 | 사용자에게 보이는 상태 | `syncing?` = visible `Sync` 존재(R-04). `last_synced_at` = 가장 최근 `completed` `Sync`의 `completed_at`(`failed`, `stale`은 무시). 계정 목록 화면은 모든 item·Account의 최신 `Sync`, 최신 완료 `Sync`, syncing 여부를 한 번에 조회해 요청 단위 캐시(`Current`)에 넣고 개별 질의를 피한다. 화면 요소: Family가 `syncing?`이면 새로고침 아이콘이 회전·비활성화되고, Family의 visible `Sync`가 있으면 "Cancel sync" 버튼이 보인다. 완료 시 R-18의 toast가 뜨고, 사용자가 유휴면 잠시 뒤 자동 새로고침, 입력 중이면 toast의 새로고침 버튼 대기, 모달이 열려 있으면 닫힌 뒤 표시된다. 계정별 syncing 표시는 Family의 visible 상태(`draft`, `active`) 계정 중 visible한 Account `Sync`가 있는 계정 id의 집합이며 `latest_sync_activity_at`이 키인 캐시(R-02가 그 값을 갱신)에 담는다 | 코드 확인 |
| R-31 | API 응답 | `GET /api/v1/syncs`(읽기 권한, 최신순 페이지 단위), `/latest`(없으면 `{data: null}`), `/:id`는 R-27의 범위(`for_family`, 요청자가 접근 가능한 Account로 한정)에서만 찾고, `:id`가 uuid 형식이 아니거나 범위 밖이면 404다. 목록 응답은 `{data: [항목...], meta: {page, per_page, total_count, total_pages}}`이고 `page`는 1 미만이면 1, `per_page`는 1~100은 그대로, 100 초과는 100, 그 밖(0 이하, 숫자 아님)은 25다. 항목: `id`, `status`, `in_progress`(`pending` 또는 `syncing`), `terminal`(`completed`, `failed`, `stale`), `syncable{type, id, name}`, `parent_id`, `children_count`, `window_start_date`, `window_end_date`, `pending_at`, `syncing_at`, `completed_at`, `failed_at`, `error`, `created_at`, `updated_at`. `error`는 원문을 노출하지 않는다: `failed`이면 `{message: "Sync failed"}`, `stale`이고 `error`가 있으면 `{message: "Sync became stale before completion"}`, 그 외 null. `POST /api/v1/sync`(쓰기 권한)는 202와 `id`, `status`, `syncable_type`, `syncable_id`, `syncing_at`, `completed_at`, 창, 고정 문구 `message`를 담고, 처리 중 예외가 나면 500과 `{error: "internal_server_error", message: "An unexpected error occurred"}`를 준다 | 코드 확인 |
| R-32 | Syncable item의 자동 등록 | "Family의 has-many 연결 이름이 `_items`로 끝나고 그 모델이 Syncable인 것"을 실행 시점에 열거한다. 이 목록이 (a) Family sync의 자식 item(R-15), (b) `SyncSchedule`의 허용 종류(R-21), (c) `Sync.for_family`의 item 범위(R-27, R-31), (d) 반복 거래 식별 job이 끝나지 않은 sync가 있는지 보는 게이트(`any_incomplete_for?`)를 동시에 정한다. 새 연동이 이 이름 규칙과 Syncable을 따르면 별도 등록 없이 네 곳에 들어간다. 이 목록은 원본에서 Family 재무 데이터 초기화(destructive reset)의 삭제 대상도 정한다. 원본에서 Syncable을 포함한 모델은 Family, Account, 연동 item 28개다. FinanceKit item은 `syncable`이 항상 빈 결과라 Family sync에 참여하지 않는다. 자동이 아닌 곳(수동 등록): 계정 화면의 최신 `Sync` 조회(item 27종 직접 나열), 설정 화면 provider별 sync(`PANEL_SYNCABLE_TYPES`), 시간별 sync 대상 목록, API `provider_connections`의 provider 목록 | 코드 확인 |
| R-33 | `Sync` 보존과 삭제 | 시간이 지나도 `Sync` 행을 지우는 정리 코드를 찾지 못했다(오래된 행은 그대로 남는다). 삭제는 syncable이 지워질 때(syncable의 `syncs`, `sync_schedule` 연결의 `dependent: destroy`)와 부모가 지워질 때(자식 `dependent: destroy`), Family 재무 데이터 초기화뿐이다. DB 제약: `syncs.parent_id`는 `syncs`를 가리키는 외래 키이고 삭제 시 동작 지정이 없어(기본 거부) 자식이 있는 부모 행만 SQL로 지우면 거절된다. FinanceKit 수신 batch의 `sync_id`는 `syncs`를 가리키고 `Sync`가 지워지면 null이 된다 | 코드 확인(검색 범위 한정) |
| R-34 | `sync_later`를 거치지 않는 `Sync` 생성과 직접 전이 | `Sync`를 만드는 경로는 `sync_later`만이 아니다. (a) Sophtron 수동 sync 컨트롤러는 `item.syncs.create!`로 `Sync`를 만들고 `start`한 뒤, 여러 요청에 걸쳐 직접 `fail`하고 `error`를 쓰거나 `finalize`(R-10)를 호출한다. 이 `Sync`는 `SyncJob`이 실행하지 않는다. (b) SimpleFIN의 balances 액션은 `syncs.create!(status: :pending)`으로 만든 `Sync`에 `SyncJob(balances_only: true)`를 넣는다. 5분 안의 진행 중 `Sync`와 합치지 않으므로(R-05 우회) 같은 item에 진행 중 `Sync`가 둘 생길 수 있다. (c) FinanceKit 처리기와 FinanceKit 데모 생성기는 `status: "completed"`와 `completed_at`을 채운 `Sync`를 job 없이 직접 만든다(전이표, `finalize`, post-sync, 완료 이벤트가 없고 R-02의 생성 시 commit 후 갱신만 일어난다). (d) 데모 생성기는 `Sync.create!(syncable: account).perform`으로 job 없이 동기 실행한다. 따라서 "모든 `Sync`는 `sync_later`로 만들어지고 `SyncJob`이 실행하며 `completed`는 `finalize`에서만 생긴다"는 원본 전체에서 성립하지 않는다(R-16의 SimpleFIN `complete!`도 같다). 새 연동이 `sync_later`와 `Sync#perform` 경로만 쓰면 R-05, R-08, R-10의 보장을 모두 받는다 | 코드 확인 |

- 불변식(Account·Family·`sync_later`와 `Sync#perform` 경로 기준. item Syncer와 직접 생성 경로의 예외는 각 항목에 적었다): (1) `perform` 경로의 `completed`는 `finalize`를 거쳐서만 생기고 그 시점에 모든 자식은 `pending`, `syncing`이 아니다(R-09, R-10). 예외는 SimpleFIN `mark_completed`(자식이 `pending`이어도 `complete!`), FinanceKit 직접 생성(R-34), Sophtron 컨트롤러의 직접 전이(R-34)다. (2) `stale` 루트는 post-sync를 실행하지 않는다(R-10, R-13, R-14). 단 item Syncer 경로에서는 R-16의 덮어쓰기로 `stale`이 `failed`가 되어 post-sync가 실행될 수 있다. (3) 종료 상태 `Sync`의 status는 `Sync` 안의 전이(R-01), `finalize`, `request_cancel!`, `Sync.clean` 경로에서 바뀌지 않는다. Account·Family Syncer 경로는 이 보장을 지킨다. item Syncer 경로(Kraken, Binance, Coinbase, Coinspot, OnchainWallet, SimpleFIN의 `mark_failed`)에서는 성립하지 않는다(R-16). 구현자가 따를 쪽은 적용 메모의 보정 선택지에 구분해 적었다. (4) `finalize`는 자식을 포함한 트리 전체가 끝나기 전에는 부모에게 결과를 전하지 못한다. 어떤 자식이 `pending`, `syncing`에 머물면 부모도 24시간 sweep 전까지 `syncing`에 머문다. 이 상태는 R-08의 부모 잔류, R-13의 3단 취소에서도 생긴다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-02 | 새로 만든 `Sync`의 `pending_at`이 채워지는가. 코드에는 초기 상태에서 시각을 찍는 곳이 없고, 상태 전이 시 시각을 찍는 AASM `timestamps` 옵션이 초기 상태에도 적용되는지는 gem 동작이다 | API가 `pending_at`을 노출하므로 null로 낼지 `created_at`과 같게 낼지 구현자가 정해야 한다 | AASM 5.5.1(`Gemfile.lock`)의 timestamps 구현 확인 또는 `Sync.create!` 후 컬럼 조회(실행 금지라 미수행) |
| U-02 | R-29, R-28 | `SyncJob`이 job 시스템 수준에서 몇 번, 어떤 간격으로 재시도되는가(원본은 `ApplicationJob`의 교착 재시도만 명시하고 나머지는 Sidekiq 기본값에 위임) | 재시도 횟수는 R-08 가드 덕에 `Sync` 상태에는 영향이 없다. 구현 job 시스템의 재시도 기본값을 정해야 한다 | Sidekiq 8.0.5 기본 재시도와 ActiveJob adapter 동작 확인 |
| U-03 | R-19, R-22 | 여러 worker 프로세스가 같은 cron 틱을 동시에 받을 때 반복 job이 한 번만 enqueue되는 보장이 scheduler(sidekiq-cron) 쪽인가 unique lock 쪽인가 | 구현 scheduler가 다중 인스턴스에서 틱당 한 번만 enqueue하는 보장을 직접 제공해야 하는지 | sidekiq-cron 2.4.0, sidekiq-unique-jobs 8.0.11 소스 확인 |
| U-04 | R-18, R-32 | Brex, Questrade, Sharesight item은 `SyncCompleteEvent`를 정의하지 않은 것으로 보이는데 어떻게 완료 이벤트가 동작하는가. 상수가 없으면 이름 오류가 나고 R-11이 삼킨다고 추론했을 뿐이다 | 새 연동이 완료 이벤트를 안 만들면 toast가 안 뜨고 오류가 매번 기록되는지, 구현자가 완료 이벤트를 필수로 할지 | 위 세 모델의 constant 해석(Zeitwerk 규칙)을 확인 |
| U-05 | R-08 | `Sync`의 syncable이 없는 분기에서 `start` 전이의 commit 후 처리가 `nil`에서 예외를 내면 그 예외가 `perform` 밖으로 나가는가, 나가면 `fail`과 `error` 저장은 실행되지 않는가 | 이 분기의 결과(`failed` + 고정 `error` 기록 또는 `syncing`에 잔류)를 구현자가 정해야 한다 | AASM 5.5.1과 after_commit_everywhere 1.6.0의 commit 후 콜백 예외 처리 확인 |
| U-06 | R-02, R-10, R-11 | post-sync와 완료 이벤트를 `Sync` 행 잠금과 transaction 안에서 실행해 `completed` 상태와 `latest_sync_completed_at`이 그 뒤에 commit되는 것이 의도인가. 화면 새로고침 push가 `completed` commit보다 먼저 나갈 수 있다 | 구현자가 post-sync·push를 commit 전과 후 중 어디에 둘지 정해야 한다. 원본 순서를 따르면 push를 받은 클라이언트가 이전 상태를 읽을 수 있다 | 원본 이슈·커밋 기록 확인(코드에는 의도가 없음). 현재는 `추론` |

- 확인 한계: Rails·실행 환경을 쓰지 않아 AASM, Sidekiq, sidekiq-cron, sidekiq-unique-jobs, ActiveJob의 gem 동작은 코드 사용 방식에서 읽은 것이다(R-01의 예외 동작, R-02와 R-08의 commit 후 콜백, R-07, R-19, R-28(4), R-29, U-01~U-03, U-05). 외부 시스템(Plaid 등)과의 상호작용은 범위 밖이다.

### 1.5 필수 코드 참조 [필수]

원본은 AGPL-3.0이다(overview 1절). 아래는 위치 지정이며 이 문서는 원본 코드를 복사하지 않았다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/sync.rb:1-56` 상수, 범위, 상태 기계 | `STALE_AFTER` 24시간, `VISIBLE_FOR` 5분, 상태 5종과 이벤트 4종의 전이, `visible`·`incomplete` 조건 | R-01, R-04 |
| C-02 | `app/models/sync.rb:179-228` `perform` | 가드 순서, 시간대 감싸기, 예외 처리와 `finalize` 호출 위치 | R-08, R-09 |
| C-03 | `app/models/sync.rb:270-303` `finalize_if_all_children_finalized` | 자식 집계, 상태 결정 순서, post-sync 실행 조건, 부모 전파 | R-10, R-11 |
| C-04 | `app/models/sync.rb:236-261`, `329-334` `request_cancel!`, `cancel_pending_descendants!` | 취소 분기와 자손 정리 | R-13 |
| C-05 | `app/models/sync.rb:306-326` `expand_window_if_needed` | 창 확장 규칙 | R-06 |
| C-06 | `app/models/sync.rb:349-380` `perform_post_sync`, `queue_full_resync` | post-sync 오류 처리와 full resync 이관 | R-11, R-12 |
| C-07 | `app/models/sync.rb:58-74`, `127-154` `clean`, `for_family`, `any_incomplete_for?`, `account_syncable_ids`, `family_syncable_associations` | stale 정리 조건, Family 범위 조회(Family 자신, 접근 가능한 Account, `_items` Syncable 연결) | R-14, R-27, R-32 |
| C-08 | `app/models/concerns/syncable.rb:54-80` `sync_later` | 잠금, 합치기, 부모·창 처리, enqueue | R-05, R-06 |
| C-09 | `app/models/family/syncer.rb:8-54` | 자식 목록 구성, 취소 확인, post-sync 호출 목록, `_items` 열거 | R-15, R-32 |
| C-10 | `app/models/sync_schedule.rb:9-100` | 허용 간격(10-25), `schedulable_associations`(28-35), `assign`(37-52), `editable_by?`(54-65), `advance!`(72-86), 정렬과 경계 계산(88-100) | R-21, R-23 |
| C-11 | `app/jobs/sync_scheduled_items_job.rb:8-62` | 틱 처리 순서 | R-22 |
| C-12 | `app/services/auto_sync_scheduler.rb:1-31`, `app/services/cron_scheduler.rb:7-43`, `config/initializers/sidekiq.rb:76-82`, `app/models/setting.rb:239-241,251-256` | 매일 sync cron 등록(`sync!` 7-14, `upsert_job` 16-39, 제거 41-43), 설정 기본값, 시간 형식 정규식 | R-19 |
| C-13 | `config/schedule.yml:7-12,28-40`, `config/sidekiq.yml:1-15` | 정적 cron과 큐 가중치 | R-14, R-20, R-22, R-29 |
| C-14 | `app/models/kraken_item/syncer.rb:12-62`, `app/models/kraken_item.rb:24-26,59-73` | item Syncer 예시(구조 예시이며 Kraken 자체는 이 스펙의 대상이 아님) | R-16 |
| C-15 | `app/models/account/syncer.rb:8-18` | Account sync의 호출 순서 | R-17 |
| C-16 | `db/schema.rb:2729-2762`, `db/schema.rb:856,873-875` | `sync_schedules`, `syncs`, Family sync 컬럼의 제약·기본값 | 1.3 |
| C-17 | `app/models/kraken_item/syncer.rb:69-80`, `app/models/binance_item/syncer.rb:76-91`, `app/models/simplefin_item/syncer.rb:122-148,242-256` | item Syncer가 `Sync` 상태를 직접 바꾸는 방식(메모리 객체 기준 `may_fail?`와 `fail!`, 직접 `status` 쓰기, 행 잠금 아래 재확인 후 `complete!`) | R-01, R-16 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 시간에 따라 변하는 값은 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05 | Account A에 `Sync`가 없다. `A.sync_later`를 두 번 연속 부른다 | `Sync`는 한 개(`pending`), job은 한 번 enqueue, 두 호출이 같은 `Sync`를 돌려준다 |
| T-02 | R-05, R-06 | `pending` `Sync`(창 2026-11-10 ~ 2026-11-12)가 있다. `sync_later(창 2026-11-05 ~ 2026-11-11)` | 새 `Sync` 없음. 창이 2026-11-05 ~ 2026-11-12. `syncing`이면 창은 변하지 않는다 |
| T-03 | R-06 | `pending` `Sync`의 창이 2026-11-10 ~ 2026-11-12다. `sync_later(창 없음)` | 시작·끝이 모두 null이 된다(전체) |
| T-04 | R-04, R-05 | A의 `Sync`가 `syncing`이고 생성 후 6분이 지났다. `A.sync_later` | 새 `pending` `Sync`가 생긴다(기존 것은 visible이 아님). 두 `Sync`가 공존한다 |
| T-05 | R-08 | status가 `stale`인 `Sync`에 대해 `SyncJob`이 실행된다 | 상태·`error` 변화 없음, Syncer 호출 없음 |
| T-06 | R-08 | `Sync.syncable`의 객체가 callback 없이 삭제됐다. `perform` | 코드가 의도한 결과는 `failed`, `error` = `"Syncable record was deleted"`, 부모 finalize 호출 없음이다. `start` 전이의 commit 후 처리가 `nil` 호출 예외를 내므로 그 예외가 `perform` 밖으로 전파되면 `fail`과 `error` 저장이 실행되지 않고 `Sync`는 `syncing`에 남는다(U-05, 추론). 어느 쪽이든 부모의 마지막 미종료 자식이면 부모는 `syncing`에 남는다 |
| T-07 | R-09, R-10 | 자식 없는 Account `Sync`. Syncer가 정상 종료 | `pending → syncing → completed`, post-sync와 완료 이벤트 호출, Family의 `latest_sync_completed_at` 갱신 |
| T-08 | R-09, R-10, R-11 | Account `Sync`의 Syncer가 예외 `"boom"`을 던진다 | 상태 `failed`, `error` = `"boom"`, 오류 수집기에 보고, post-sync 실행, `SyncJob`은 예외 없이 끝난다 |
| T-09 | R-10 | 루트 Family `Sync`에 자식 item `Sync` 둘. 하나가 `failed`, 다른 하나가 `completed`로 끝났고 루트 Syncer는 정상이다 | 루트가 마지막 자식 종료 시점에 `failed`(자식 중 `failed` 존재)가 된다. `stale` 자식만 있으면 `completed` |
| T-10 | R-10 | 루트 `Sync`가 `syncing`이고 자식 하나가 아직 `syncing`이다. 루트 Syncer가 끝나 `finalize` 호출 | 루트는 `syncing`을 유지하고 post-sync는 실행되지 않는다. 자식이 끝나면 부모 finalize가 이어져 확정된다 |
| T-11 | R-13 | `pending` 루트와 `pending` 자식 둘. `request_cancel!` | 루트·자식 모두 `stale`, 루트 `cancel_requested_at` 설정, 반환 true. 이후 큐의 job은 R-08(1)로 무시된다 |
| T-12 | R-13, R-10 | 루트 `syncing`, 자식 A `syncing`(job 실행 중), 자식 B `pending`(깊이 2). `request_cancel!` 후 A가 정상 종료 | B는 `stale`, A는 `completed` 유지, 루트는 A가 끝나는 시점에 `stale`이고 post-sync 없음. 이 결과는 깊이 2에서만 성립한다(깊이 3은 T-28) |
| T-13 | R-13 | `completed`인 `Sync`에 `request_cancel!` | 반환 false, 변화 없음, 취소 화면은 "취소할 수 없음" 경고 |
| T-14 | R-14 | `syncing`이고 `created_at`이 25시간 전인 `Sync`, 1시간 전인 `Sync`. `Sync.clean` | 앞의 것만 `stale`. 뒤의 것은 그대로. 부모·자식 상태 변화 없음 |
| T-15 | R-14, R-16 | 외부에서 `stale`이 된 `Sync`의 job이 끝난다. (a) Account Syncer 경로에서 Syncer가 예외를 던진다 | status는 `stale` 유지, `error`는 예외 메시지, post-sync와 완료 이벤트는 실행되지 않는다. (b) item Syncer 경로(Kraken 등)에서 Syncer가 예외를 던진다(원본 동작, T-29) | `mark_failed`가 메모리 객체로 `fail!`을 불러 `stale`이 `failed`로 덮이고 post-sync가 실행된다 |
| T-16 | R-12 | 실행 중 `Sync` S에 `full_resync_requested = true`가 찍힌 뒤 S가 `completed`로 끝난다 | 같은 syncable에 새 `Sync`(창 없음)가 만들어지고 S의 플래그는 false. 다른 visible `syncing` `Sync`가 있으면 새 `Sync` 대신 그쪽 플래그가 true가 된다 |
| T-17 | R-15 | Family에 연동 item 2개(하나는 `scheduled_for_deletion`), 수동 Account 1개, 연동 Account 1개 | 자식 `Sync`는 삭제 예약이 아닌 item 1개와 수동 Account 1개 둘만 생긴다. 연동 Account는 item이 만든다. 취소 요청이 이미 있으면 자식이 하나도 안 생긴다 |
| T-18 | R-21 | `interval_minutes` 60, 현재 UTC 10:20에 스케줄을 저장 | `next_run_at` = 같은 날 11:00 UTC. 정확히 10:00:00에 저장하면 11:00이다 |
| T-19 | R-21 | `interval_minutes`에 45를 저장 | 저장 거부(허용값 아님) |
| T-20 | R-22 | `next_run_at`이 10분 전인 스케줄, 간격 60. 틱 실행 | 스케줄이 다음 경계로 이동하고 item에 `sync_later`가 한 번 호출된다. 두 번째 틱이 같은 시각에 오면 `advance!`가 false여서 호출이 없다 |
| T-21 | R-22 | 스케줄의 item이 삭제됐다 | 스케줄이 삭제되고 sync는 없다 |
| T-22 | R-23 | `sync_schedule` 파라미터에 `interval_minutes` 키가 없다 | 422, 기존 스케줄 유지. 값이 `""`이면 스케줄 삭제 |
| T-23 | R-25 | 같은 Family가 20초 간격으로 "Sync all"을 두 번 누른다 | 첫 번째만 `SyncAllProvidersJob`을 enqueue. 두 번째는 "최근에 이미 요청됨" 알림 |
| T-24 | R-24 | (a) Family에 오늘 만든 `Sync`가 있고 `auto_sync_on_login`이 true | 로그인 요청에서 sync를 시작하지 않는다. 어제 마지막이고 계정이 active면 시작한다. (b) Family 시간대가 UTC+9이고 앱 기본이 UTC이며 지금이 Family 기준 2026-11-18 08:00(UTC 2026-11-17 23:00)이고 마지막 `Sync`가 Family 기준 2026-11-17 23:00(UTC 2026-11-17 14:00)에 만들어졌다 | Family 시간대로 판정하면 마지막 `Sync`가 어제이므로 시작한다. 원본 해석(R-24 추론)대로 앱 기본 시간대(UTC)로 판정하면 오늘(2026-11-17)에 만든 `Sync`가 있다고 보고 시작하지 않는다 |
| T-25 | R-27 | 구성원(관리자 아님)이 연동 item의 `Sync`를 취소 요청 | 404. 같은 구성원이 Family 또는 접근 가능한 Account의 `Sync`를 요청하면 취소된다 |
| T-26 | R-31 | `failed` `Sync`의 `error` = `"secret detail"` | API의 `error` = `{message: "Sync failed"}`. `stale`이고 `error`가 비어 있으면 null |
| T-27 | R-11, R-15 | Family의 post-sync 세 호출(transfer 자동 매칭, 가맹점 로고 보충, 규칙 적용 job enqueue) 중 transfer 자동 매칭이 예외를 던진다 | `Sync` 상태는 유지(예: `completed`), 로고 보충과 규칙 job enqueue는 실행되지 않고(첫 호출에서 중단) 완료 이벤트도 실행되지 않으며, full resync 확인은 실행된다 |
| T-28 | R-13 | 루트 Family `Sync` `syncing`(Syncer 종료), 자식 item `Sync` `syncing`(job은 이미 끝나 자기 자식 Account `Sync`만 기다림), 손자 Account `Sync` `pending`. 루트에 `request_cancel!` | 손자만 `stale`이 된다. item `Sync`와 루트는 `syncing`에 남고(`cancel_requested_at`은 루트에 있어 루트는 visible에서 빠진다), 24시간 뒤 `Sync.clean`이 각각 `stale`로 바꾼다 |
| T-29 | R-16, R-14 | Kraken item `Sync`가 `syncing`이다. 관리자 콘솔 또는 취소로 DB에서 `stale`이 된 뒤, job이 도는 Kraken Syncer가 인증 오류를 던진다 | `mark_failed`가 메모리 객체(`syncing`)로 `fail!`을 불러 DB의 `stale`이 `failed`로 덮인다. 오류가 다시 던져져 R-09가 `error`를 저장하고, `finalize`는 `stale`이 아니므로 post-sync를 실행한다 |
| T-30 | R-34, R-05 | SimpleFIN item에 5분 안의 `pending` `Sync`가 있다. 사용자가 balances 액션을 부른다 | 기존 `Sync`와 합치지 않고 새 `pending` `Sync`가 만들어져 `SyncJob(balances_only: true)`가 enqueue된다(같은 item에 진행 중 `Sync` 둘). Sophtron 수동 sync 컨트롤러는 `Sync`를 직접 만들어 `start`하고 job 없이 컨트롤러가 `fail`·`finalize`를 호출한다 |
| T-31 | R-16, R-10 | SimpleFIN item Syncer가 자식 Account `sync_later`를 만든 직후 `mark_completed`를 부른다. 자식 하나는 아직 `pending`이다 | item `Sync`는 `completed`가 된다(`finalize` 없이 `complete!`). 이후 자식이 `failed`가 되어도 item `Sync`는 `completed`로 남고 자식 종료 때 부모 `finalize`가 post-sync를 실행한다 |
| T-32 | R-10, R-11 | 부모 Syncer가 자식 둘을 차례로 만든다. 첫 자식이 둘째 자식 생성 전에 끝난다(추론한 경합) | 첫 자식의 부모 `finalize`가 존재하는 자식만 보고 부모를 `completed`로 확정하고 post-sync를 실행할 수 있다. 둘째 자식이 끝날 때 부모 `finalize`가 다시 닿아 post-sync가 한 번 더 실행된다 |
| T-33 | R-31 | 사용자가 `GET /api/v1/syncs?per_page=500&page=0`을 부른다. 다른 요청은 `GET /api/v1/syncs/abc` | 응답은 `{data: [...], meta: {page: 1, per_page: 100, total_count, total_pages}}`이고 최신순이다. `per_page=0`이면 25다. `abc`는 uuid 형식이 아니므로 404다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@1cd94e6 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `sync.rb:30-56`. 호출 쪽 확인 `may_start?` `sync.rb:188`, `may_fail?` `sync.rb:220,196`. 메모리 객체 기준 가드 C-17 | 전이표는 코드 확인. 예외 동작(`whiny_transitions`)은 gem 기본값이라 추론(gem 소스 미열람, `Gemfile.lock:5` aasm 5.5.1). `sync.rb:290`의 테스트 사례 이름("a late provider complete! cannot resurrect")이 SimpleFIN 경로의 종료 상태 보호를 뒷받침. 다른 item Syncer의 덮어쓰기는 C-17을 직접 읽어 확인(`grep -rln "sync.fail!" app`: sophtron 컨트롤러와 binance, coinbase, coinspot, kraken, onchain_wallet, simplefin Syncer) |
| R-02 | `sync.rb:24`, `399-427` 콜백(경고 확인 `388-397`, 완료 touch `407-409`, 활동 touch `422-427`). `db/schema.rb:2740-2762`에 `stale_at` 없음. `sync.rb:271-299`의 transaction | `stale_at`이 없다는 주장은 `grep -n "stale" db/schema.rb`(syncs 블록)로 확인. 시각 필드를 AASM이 채우는 규칙은 추론(U-01). `complete`의 commit 후 처리가 바깥 transaction commit 뒤로 미뤄진다는 것은 `Gemfile`의 `after_commit_everywhere`(`Gemfile.lock:87`, 1.6.0)와 이벤트의 `after_commit:` 옵션에서 읽은 추론(U-06) |
| R-03 | `sync.rb:28`, `416-420` | |
| R-04 | `sync.rb:4-7`, `22`, `157-164` | |
| R-05 | C-08 `syncable.rb:54-80` | |
| R-06 | C-05 `sync.rb:306-326` | `syncing` 상태는 `return unless pending?`로 확장하지 않음 |
| R-07 | `app/jobs/application_job.rb:1-18`(주석이 이유를 설명), `syncable.rb:74` | 추론: 설정이 gem 버전에서 실제 작동하는지는 주석("Rails 8.2 default, 8.1에서 클래스 속성으로 설정")을 믿음 |
| R-08 | C-02 `sync.rb:179-209`, `app/jobs/sync_job.rb:1-15`. `sync.rb:193-200`(syncable 없음 분기), `388-409`(commit 후 처리) | (2), (3) 분기가 `next`로 나가 `begin/ensure`의 `finalize`에 닿지 않는 것은 코드 확인, 그 결과 부모가 남는 것은 추론. (2)에서 `report_warnings`가 `syncable.syncs`를 부르고 `family`가 `nil`을 돌려주는 것은 코드 확인, 예외 전파는 AASM·after_commit_everywhere 동작이라 추론(U-05). 테스트 사례 이름 `sync_test.rb:6` "does not run if not in a valid state" |
| R-09 | C-02 `sync.rb:185-227`, `211-225` | `start!`는 `begin` 밖(`:211`)이고 `rescue => e`는 `StandardError`만 잡으며 `ensure`의 `finalize`에는 rescue가 없다는 것은 코드 확인. `sync_test.rb:77` "handles sync errors" 이름 확인 |
| R-10 | C-03 `sync.rb:270-303`, `341-347` | `syncing?`이 false인 상태에서 post-sync가 실행되는 것은 `sync.rb:281,298`(전이는 `syncing`일 때만, post-sync는 `stale?`만 본다)에서 읽음. `pending`에 `finalize`가 닿는 실제 호출 경로는 찾지 않았다(분기 존재만 코드 확인). 조기 확정 경합은 Family `perform_sync`의 순차 `sync_later`(`family/syncer.rb:13-19`)와 부모 행을 잠그지 않는 구조에서 읽은 추론. `sync_test.rb:92,136,182` 이름("nested syncs", "failures propagate up the chain", "parent failure should not change status if child succeeds") |
| R-11 | C-03·C-06 `sync.rb:271-299`(transaction 범위), `294-303`, `349-359`. `db/schema.rb:2740-2762`에 post-sync 실행 기록 컬럼 없음 | post-sync와 broadcast가 `Sync.transaction` 안에서 실행되는 것은 `sync.rb:271-299`에서 코드 확인. 중복 실행은 코드 구조에서 읽은 추론(두 자식이 동시에 `parent.finalize`를 부르는 경우, 또는 R-10의 조기 확정). 재현하지 않음 |
| R-12 | C-06 `sync.rb:361-380`, `sync.rb:411-414`. `app/models/loan.rb:337-352` 설정하는 쪽 | `grep -rn "full_resync_requested" app`로 설정하는 곳은 `loan.rb:345`뿐(`sync.rb` 제외). 다른 기능이 쓰면 놓쳤을 수 있음(검색 범위: `app`, 별칭·`update_column` 형태 포함해 패턴 `full_resync_requested`) |
| R-13 | C-04 `sync.rb:236-261`, `329-334`, `271-293`. `sync_test.rb:261-366`의 이름들 | `cancel_pending_descendants!`가 `pending`에만 `mark_stale!`을 부르고 중간 노드에 `finalize`를 부르지 않는 것은 `sync.rb:329-334`와 `236-261`에서 코드 확인(3단 결과는 그 코드의 귀결, 실행하지 않음). 전칭 부분: "취소 플래그를 읽는 코드는 Family Syncer의 반복과 SimpleFIN Syncer뿐". 명령 `grep -rn "cancel_requested" app lib --include=*.rb`, 결과는 `sync.rb`, `family/syncer.rb:16`, `simplefin_item/syncer.rb:129,142,146`. 다른 디렉터리·동적 호출은 보지 않음 |
| R-14 | C-07 `sync.rb:58-61`. `sync_cleaner_job.rb:14-31`, `config/schedule.yml:7-12`. job 중 stale: `sync.rb:216-224`, `294-298`. `sync_test.rb:228-259`. 관리자 콘솔 `settings/background_jobs_controller.rb:73-79`(`cancellable_status?`는 `:67-71`) | `sync_cleaner_job.rb:34-58`의 provider 플래그 정리는 이 스펙 밖(이름만 확인). `Sync.clean`의 `find_each(&:mark_stale!)`에 가드·rescue가 없고 `sweep`이 `rescue`로 감싸는 것은 코드 확인. 한 건의 예외로 run이 멈추는 것의 구체 조건(DB 오류 등)은 추론. 동시 완료 `Sync`를 덮을 수 있다는 점은 행 잠금이 없는 코드에서 읽은 추론. 관리자 콘솔은 `grep -rn "mark_stale!" app`에서 `background_jobs_controller.rb:80`과 `sync.rb` 안만 나옴 |
| R-15 | C-09 `family/syncer.rb:8-28,47-53`. 수동 Account `app/models/account.rb:94-98`. 구독 상태 갱신 `app/models/family/subscribeable.rb:103-107` | `Family.accounts.manual`에는 status 조건이 없다는 점은 코드 확인. 자식 반복에 per-child rescue가 없는 것은 `family/syncer.rb:13-19`에서 코드 확인, `failed`가 되는 결과는 R-09의 귀결. `sync_test.rb:359` 이름 확인 |
| R-16 | C-14 `kraken_item/syncer.rb:12-79`, `kraken_item.rb:59-73`. 직접 변경 C-17: `kraken_item/syncer.rb:69-80`, `binance_item/syncer.rb:76-91`, `coinbase_item/syncer.rb:75-90`, `coinspot_item/syncer.rb:128-137`, `onchain_wallet_item/syncer.rb:83-92`, `simplefin_item/syncer.rb:122-148,242-256` | 전칭 확인: `grep -rln "sync.fail!" app`에서 `sync.fail!`을 직접 부르는 코드는 위 6개 Syncer와 `sophtron_items_controller.rb:832`뿐이다(다른 item Syncer는 예외를 던져 R-09에 맡김, 동적 호출은 보지 않음). 메모리 객체가 DB를 다시 읽지 않는 것은 코드 확인. 덮어쓰기 결과는 AASM이 메모리의 전이 결과를 저장한다는 gem 동작에 기대므로 추론. 연동 item 28개 중 Syncer 파일은 27개다(`ls app/models/*/syncer.rb`는 29개이고 Family·Account가 포함, FinanceKit만 없음). `perform_post_sync`가 대부분 비어 있음은 `grep -n "perform_post_sync" -A3`로 확인(내용이 있는 것은 OnchainWallet, TrueLayer 등 일부). 본문 흐름은 Kraken과 SimpleFIN만 열었다 |
| R-17 | C-15 `account/syncer.rb:8-18,21-24,33-38,101-110` | `window_end_date` 미전달: `account/syncer.rb:10` 호출 인자 |
| R-18 | `family/sync_complete_event.rb:8-45`, `account/sync_complete_event.rb:10-21`, `kraken_item/sync_complete_event.rb:10-17`(Family 이벤트 호출은 `:14`). 화면 조각 `app/views/shared/notifications/_sync_toast.html.erb:1-33`, `app/views/accounts/_sync_controls.html.erb:1-31` | 이벤트 파일이 없는 모델: `for d in ... ; [ -f $d/sync_complete_event.rb ]`로 세어 brex, financekit, questrade, sharesight 4개(financekit는 syncable 없음). `grep -rn "SyncCompleteEvent" app lib`로 다른 정의가 없음을 확인했으나 동적 정의는 확인 못 함(U-04). 개별 provider 15개에 대한 "toast만 보낸다"는 `test/models/provider_item_sync_complete_events_test.rb:1-30` 이름·주석으로 확인 |
| R-19 | C-12 `auto_sync_scheduler.rb:1-31`, `cron_scheduler.rb:7-43`, `config/initializers/sidekiq.rb:76-82`, `hostings_controller.rb:14-24`(권한), `165-184`, `540-545`, `569-571`(시간대 값), `setting.rb:239-256`. `models/user.rb:220-225`(`manages_instance_settings?`). `sync_all_job.rb:1-15` | "SyncAllJob을 enqueue하는 곳은 AutoSyncScheduler뿐"이라는 주장은 `grep -rn "SyncAllJob" app config lib docs`로 확인(주석 제외 `auto_sync_scheduler.rb:18`만). 수동 호출 가능성(console 등)은 범위 밖. `manages_instance_settings?`는 앞 5줄만 읽었고 그 뒤 조건은 보지 않음. self-hosted 한정은 `hostings_controller.rb:17`의 `guard_feature unless: -> { self_hosted? }` |
| R-20 | `sync_hourly_job.rb:1-27`, `config/schedule.yml:28-33` | `HOURLY_SYNCABLES`는 `CoinstatsItem` 하나(`sync_hourly_job.rb:6-8`) |
| R-21 | C-10 `sync_schedule.rb:10-25,28-35,72-100` | `sync_schedule_test.rb:8-148`의 사례 이름이 같은 항목을 가리킴(본문 미열람) |
| R-22 | C-11 `sync_scheduled_items_job.rb:8-62`, `config/schedule.yml:35-40` | |
| R-23 | `sync_schedules_controller.rb:7-53`, `sync_schedule.rb:37-65`, `provider_item_ownable.rb:59-71` | `manageable_by?`의 `member?` 재확인은 `provider_item_ownable.rb:62-71`에서 코드 확인. `member_connectable?`(provider별 소유 가능 여부)의 정의는 열지 않음 |
| R-24 | `auto_sync.rb:1-22`, `application_controller.rb:2-3`(`Localize`, `AutoSync`, `Authentication`을 한 줄에서 include), `concerns/localize.rb:4-7,114-116`(`switch_timezone`은 around_action), `db/schema.rb:856`, `config/application.rb:28`(`time_zone` 지정 주석 처리). `test/controllers/concerns/auto_sync_test.rb:12-45` 이름만 | 다중 include의 callback 등록 순서(뒤쪽 인수부터 처리)는 Ruby·ActiveSupport 규칙에서 읽은 추론. 이 순서면 인증 → `AutoSync` → `Localize` 순이다. 테스트 이름은 인증된 요청에서 동작함을 시사하지만 시간대 경계는 검증하지 않는다. 앱 기본 시간대가 UTC라는 것은 `config.time_zone`이 주석 처리된 것(`config/application.rb:28`)에서 읽은 추론이다 |
| R-25 | `accounts_controller.rb:87-91`, `201-223`, `settings/providers_controller.rb:82-108`(관리자 제한은 `:4`), `kraken_items_controller.rb:34-42`(관리자 제한은 `:5`), `api/v1/sync_controller.rb:7-23`, `config/routes.rb:359-366,460-461,754,879-880` | (e)는 Kraken 컨트롤러만 열었다. 다른 item 컨트롤러가 같은 방식이라는 것은 `routes.rb`의 `post :sync` 18개 이상 줄에서 추론 |
| R-26 | `entry.rb:378-384`, `entry_scheduled_sync_job.rb:1-36`, `docs/llm-guides/architecture.md:112-115`, `account.rb:344-346`, `loan.rb:337-352` | 호출처 대표값이며 전수가 아니다. 목록은 `grep -rn "\.sync_later" app --include=*.rb`로 약 60곳을 보았고 provider별 호출은 뺐다. Loan 경합 뒤의 플래그 잔류와 재 sync는 `loan.rb:341-349`와 `sync.rb:361-380`에서 읽은 추론 |
| R-27 | `syncs_controller.rb:2-22`(리다이렉트는 `:18-20`), C-07 `sync.rb:63-74`, `141-154` | |
| R-28 | R-05, R-08, R-10, R-13 근거. `sync_all_job.rb:3`, `sync_all_providers_job.rb:3`, `sync_hourly_job.rb:3`, `sync_scheduled_items_job.rb:3`의 `sidekiq_options lock: :until_executed, on_conflict: :log` | unique lock의 동작은 gem 규칙(미열람). `SyncJob`·`SyncCleanerJob`에 lock이 없음은 파일 전체 확인 |
| R-29 | C-13 `config/sidekiq.yml:1-15`, `application_job.rb:16-18`, `config/initializers/sidekiq.rb:102-105` | 가중치의 의미(엄격한 우선순위가 아니라 가중 선택)는 Sidekiq 규칙이며 미열람 |
| R-30 | `syncable.rb:9-46,94-104`, `app/models/current.rb:5`, `accounts_controller.rb:520-563`(조회 묶음), `balance_sheet/sync_status_monitor.rb:1-35`(`:19-24`가 `syncable_id`를 담음), `_sync_controls.html.erb`, `_sync_toast.html.erb` | toast의 유휴·입력 중·모달 3분기는 `family/sync_complete_event.rb:9-14` 주석 설명이며 Stimulus controller(`sync-toast`)는 열지 않음(추론) |
| R-31 | `api/v1/syncs_controller.rb:1-46`(`:34` uuid 검사), `api/v1/base_controller.rb:42,238-255`(404 처리, page·per_page 규칙), `api/v1/sync_controller.rb:7-33`, `views/api/v1/syncs/_sync.json.jbuilder:1-24`, `index.json.jbuilder`, `show.json.jbuilder`, `views/api/v1/sync/create.json.jbuilder`, `sync.rb:170-177` | `pending_at` 값은 U-01. `RecordNotFound`가 404로 매핑되는 것은 `rescue_from ... with: :handle_not_found`(`base_controller.rb:42`)에서 읽음(응답 본문 형식은 열지 않음) |
| R-32 | C-09 `family/syncer.rb:35-44`, `sync.rb:147-154`, `sync_schedule.rb:28-35`. 포함 목록 `grep -rn "include Syncable\|include AASM, Syncable" app/models`, `scope :syncable` 28건. 수동 등록 지점: `accounts_controller.rb:520-563`, `settings/providers_controller.rb:241-`, `sync_hourly_job.rb:6-8` | 연동 item 28개, Family·Account 포함 모델 30개. `app/models/financekit_item.rb:22`에 `scope :syncable, -> { none }`. reset 사용은 `family/syncer.rb:30-34` 주석. `ProviderConnectionStatus::PROVIDERS`(API provider 목록)는 별도 하드코딩 목록이라 이 자동 등록과 무관(`provider_connection_status.rb:6-34`). 계정 화면 preload 목록의 item 27종은 `accounts_controller.rb:521-548`을 세어 확인(FinanceKit 제외) |
| R-33 | `syncable.rb:5-6`, `sync.rb:13-16`, `db/schema.rb:3197`(batch `sync_id` 외래 키 `on_delete: :nullify`), `db/schema.rb:3312`(`syncs.parent_id` 외래 키, 삭제 동작 지정 없음) | 부재 주장: 명령 `grep -rnE "Sync\.(where|delete|destroy)\|syncs\.(destroy_all\|delete_all)" app lib --include=*.rb`에서 시간 기준 삭제가 없고 `family/financial_data_reset.rb:173,273`만 나옴. `app/jobs/data_cleaner_job.rb`에는 `sync`가 없음(`grep -n "Sync\|sync"`). `sync_stats`를 읽는 곳은 화면 컴포넌트와 provider 코드(`grep -rn "sync_stats" app -l`)이고 `sync.rb`는 `serialize`만. `data` 컬럼: `grep -rnE "sync(\.\|\[:)data\b" app lib`에서 결과 없음. `status_text`: `Sync`에 없고(`db/schema.rb`, `sync.rb`에 없음) item Syncer가 `respond_to?(:status_text)`로 가드해서(Kraken 7곳) 실행되지 않는다 |
| R-34 | `sophtron_items_controller.rb:654-655`(생성·`start`), `692`, `789`(`finalize`), `831-833`(`fail`), `simplefin_items_controller.rb:142-143`, `financekit/processor.rb:38-39`, `demo/financekit_generator.rb:77`, `demo/generator.rb:1099-1100`, `simplefin_item/syncer.rb:122-148` | 전칭 확인: `grep -rnE "Sync\.create\|syncs\.create\|syncs\.build\|Sync\.new" app lib --include=*.rb`의 결과로 `Syncable#sync_later`(`syncable.rb:68`) 외 `Sync`를 만드는 곳은 위 5곳 6줄뿐이다. `Sync.create!(...)`를 간접 호출하는 메타 코드나 console은 보지 않음 |
| T-01~T-33 | 사례별 대응 R-ID의 근거 | 모두 구현에서 도출. 실제 실행·테스트는 하지 않음(`test/models/sync_test.rb`의 이름만 참고). T-24(b), T-28, T-29, T-32는 추론이 섞인 결과다 |

### 2.2 코드 읽는 순서 [선택]

1. `app/models/concerns/syncable.rb`의 `sync_later`로 `Sync`가 어떻게 만들어지는지 본다.
2. `app/models/sync.rb`의 `perform`, `finalize_if_all_children_finalized`, `request_cancel!` 순서로 상태가 어디서 바뀌는지 본다.
3. `app/models/family/syncer.rb`와 `app/models/kraken_item/syncer.rb`, `app/models/account/syncer.rb`로 트리가 Family, item, Account로 내려가는 모양을 본다.
4. 트리거는 `app/jobs/sync_*.rb`, `config/schedule.yml`, `app/services/auto_sync_scheduler.rb`, `app/controllers/concerns/auto_sync.rb` 순서다.

### 2.3 비교·재사용 출처 [선택]

없음. 같은 기능을 다른 레포에서 스펙화하지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]

`draft`다(미결정 U-01~U-06이 남아 있어 `ready` 조건을 충족하지 못한다). 2026-11-17에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-33 전부와 상태 전이표(AASM 정의), C-ID 전부, T-01~T-27 전부를 다시 따라갔다. 일치 21개, 불일치 13건이 나왔다. 구현을 막는 반례 4개(item Syncer의 `stale` 덮어쓰기, 삭제된 syncable 분기, 3단 이상 취소, `Sync` 직접 생성 경로)와 세부 오류(R-19, R-24, R-27, R-30, Syncer 개수, C-ID 4곳)였다. 작성자가 코드로 다시 확인해 전부 반영했고 R-34, T-28, T-30~T-33, U-05, U-06을 추가했다.
- **메인 표본 점검**: R-10(`finalize` 판정 순서와 post-sync 조건), R-13(취소 흐름과 `cancel_pending_descendants!`의 중간 노드 미처리), R-19(`SyncAllJob` 등록 위치 한 곳, cron 이름·기본 시각), 검토자의 1·2·3번 지적과 R-34의 `Sync` 생성 위치 4곳(데모 제외)을 원본에서 직접 확인했다.
- **대조하지 못한 것**: AASM, Sidekiq, sidekiq-cron, sidekiq-unique-jobs의 gem 동작(R-02·R-07·R-08(2)·R-19·R-28·R-29, U-01~U-03·U-05), R-16의 "다른 item Syncer도 같은 틀"(Kraken과 Binance만 열었음), R-26의 호출처 약 60곳 전수, R-30의 화면 3분기(Stimulus controller), R-34의 "5곳뿐"에서 데모 2곳을 1곳으로 센 방식. R-10의 조기 확정 race와 R-11의 중복 post-sync는 재현하지 않은 `추론`이다.

## 적용 메모 [선택]

Sidekiq 없이 다른 job 시스템으로 구현할 때 필요한 보장이다. "원본 수단" 열은 원본이 쓴 방법이고 나머지는 구현이 제공해야 하는 요구다. 원본과 달라지는 부분만 "다르게 할 점"에 적었다.

| 보장 | 원본 수단(원본 동작) | 없을 때 깨지는 규칙 | 다르게 할 점·메모 |
|---|---|---|---|
| 중복 실행 허용 + 멱등 | `SyncJob`은 lock 없이 상태 가드(R-08)로 중복을 무시한다 | R-08, R-28 | job 시스템은 최소 한 번 실행(at-least-once)이어도 된다. `SyncJob`의 가드는 그대로 구현해야 한다 |
| DB commit 뒤 enqueue | `enqueue_after_transaction_commit`(R-07) | R-05, R-07 | 같은 DB에 job 테이블을 두면 `Sync` 생성과 같은 transaction에서 enqueue하는 방식으로 이 보장을 대신할 수 있다(outbox). 원본과 구현 방식이 달라진다 |
| 재시도 | 교착만 `ApplicationJob`이 재시도(R-29). `Sync#perform`이 Syncer 예외를 삼켜 provider 오류로는 job이 재시도되지 않는다. 그 외 재시도는 Sidekiq 기본값에 의존(U-02) | R-09 | Syncer 오류를 `failed`로 기록하고 job은 성공으로 끝내는 구조를 유지한다. 인프라 오류(DB 연결 끊김, 교착)만 job 재시도 대상으로 둔다. 재시도 횟수는 U-02를 정한 뒤 결정 |
| 반복 job 중복 방지 | `lock: :until_executed`: 대기·실행 중이면 같은 job 추가 enqueue를 무시하고 로그(R-28(4)). `SyncAllProvidersJob`은 `family_id`가 키 | R-19, R-20, R-22, R-25(c) | 키 단위 "이미 대기·실행 중이면 무시"를 job 시스템이 제공해야 한다. 없으면 `SyncAllJob` 등은 DB의 advisory lock이나 실행 기록 행으로 대신한다 |
| 지연 실행 | `wait_until` 지연 enqueue(R-26의 `EntryScheduledSyncJob`), 30초 debounce(반복 거래 식별, 이 스펙 밖) | R-26 | 지연 job이 유실돼도 24시간 안에 다음 daily sync가 보완한다(원본 암묵 동작) |
| cron 스케줄 | 정적 cron(`schedule.yml`)과 Settings에서 만드는 동적 cron(R-19). 시간대를 cron 문자열에 포함. 틱 지각 허용 기본 600초 | R-14, R-19, R-20, R-22 | 다중 인스턴스에서 틱당 한 번만 실행되는 보장은 U-03. 설정 변경 시 재등록 경로가 필요하다. 놓친 틱을 따라잡는 정책(원본: grace 안에서만)은 직접 정해야 한다 |
| 큐 분리 | 우선순위 5개 큐와 AI 전용 큐 그룹(R-29) | 사용자 체감(R-25의 즉시 반응) | `SyncJob`과 "Sync all"은 높은 우선순위, 예약 job은 낮은 비용 큐로 나누고 AI 작업이 sync를 굶기지 않게 한다 |
| 유실된 job 복구 | `SyncCleanerJob`이 24시간 뒤 `stale` 처리(R-14), visible 창 5분(R-04) | R-04, R-14 | durable 큐와 visibility timeout이 있으면 두 임계값(5분, 24시간)을 다시 정할 수 있다. 정하기 전에는 원본 값을 쓴다 |
| post-sync 반복 안전 | 원본은 실행 여부를 기록하지 않아 중복 가능(R-11) | R-11 | 구현에서 post-sync 대상 연산(transfer 매칭, 규칙 적용, 로고 보충)이 반복해도 안전한지 해당 스펙에서 확인한다. 이 스펙은 원본과 동일하게 at-least-once로 둔다 |


원본과 다르게 할 수 있는 선택지다. 확정한 결정이 아니고, 아래 어느 것도 원본 동작은 아니다. 원본 동작은 1부(R-ID)에 있다.

| 관련 R-ID | 원본과 다르게 할 점(선택지) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-14, R-16 | 종료 상태 보호를 `Sync` 쪽에서 강제한다. 전이(`fail`, `complete`)를 호출하기 직전에 행을 잠그고 DB 값을 다시 읽어 종료 상태이면 건드리지 않는다. 직접 `status`를 쓰는 fallback은 두지 않는다. 원본 동작을 그대로 재현하려면 item Syncer가 메모리 객체로 `fail!`을 부르는 방식을 따른다(불변식 (3)이 item Syncer 경로에서 성립하지 않는다) | 원본은 Account·Family 경로만 보호하고 item Syncer 경로는 종료 상태를 덮는다(T-15, T-29). 구현자가 새 연동 Syncer를 쓸 때 어느 쪽을 따를지 정해야 한다 | 전이 연산이 내부에서 잠금과 재조회를 하는 인터페이스. T-29의 기대가 `stale` 유지와 post-sync 미실행으로 바뀐다 |
| R-13 | 중간 노드(`syncing`이고 job이 끝난 노드)에도 취소 뒤 `finalize`를 호출해 자기 자식이 모두 끝나면 `stale`로 확정하고 부모로 전파한다 | 원본은 루트에만 `finalize`를 부르고 3단 이상에서 중간 노드와 루트가 24시간 sweep까지 `syncing`에 남는다(T-28) | 취소 흐름이 트리 전체를 아래에서 위로 finalize한다. T-28의 기대가 루트와 중간 노드 모두 `stale`로 바뀐다. 이때 중간 노드가 취소 플래그 없이 `stale`이 되는 것을 허용할지 정해야 한다 |
| R-08, R-34 | `Sync` 생성과 시작 전이를 `sync_later`와 `perform` 한 경로로 일원화하고 Sophtron·SimpleFIN 같은 직접 생성 경로를 같은 경로로 합친다 | 원본은 직접 생성 경로에서 합치기(R-05)와 finalize 보장을 우회한다. syncable 없음 분기(R-08 (2))의 불확실한 결과(U-05)도 이 일원화로 정할 수 있다 | `Sync` 생성 API가 하나가 된다. T-30의 기대가 "기존 진행 중 `Sync`와 합친다"로 바뀐다 |
| R-10, R-11 | post-sync 실행 여부를 `Sync`에 기록해 한 번만 실행한다. post-sync와 완료 이벤트는 `completed`가 commit된 뒤 실행한다(U-06) | 원본은 post-sync를 반복 실행할 수 있고 transaction 안에서 실행해 상태 commit보다 push가 앞선다 | `syncs`에 실행 기록 필드 추가. T-32의 기대가 "post-sync 1회"로 바뀐다 |

