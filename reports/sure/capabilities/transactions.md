---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/entry.rb
  - app/models/entryable.rb
  - app/models/transaction.rb
  - app/models/transaction/splittable.rb
  - app/models/transaction/search.rb
  - app/models/transaction/transferable.rb
  - app/models/entry_search.rb
  - app/models/entry/split_references.rb
  - app/models/concerns/enrichable.rb
  - app/models/account.rb
  - app/models/account_share.rb
  - app/models/current.rb
  - app/models/family.rb
  - app/models/transfer.rb
  - app/models/balance/sync_cache.rb
  - app/jobs/entry_scheduled_sync_job.rb
  - app/controllers/transactions_controller.rb
  - app/controllers/concerns/entryable_resource.rb
  - app/controllers/concerns/account_authorizable.rb
  - app/controllers/transactions/bulk_updates_controller.rb
  - app/controllers/transactions/bulk_deletions_controller.rb
  - app/controllers/transactions/categorizes_controller.rb
  - app/controllers/splits_controller.rb
  - app/controllers/transaction_attachments_controller.rb
  - app/controllers/pending_duplicate_merges_controller.rb
  - app/controllers/api/v1/transactions_controller.rb
  - app/controllers/api/v1/splits_controller.rb
  - app/controllers/concerns/api/v1/transaction_lookup.rb
  - app/controllers/concerns/safe_pagination.rb
  - app/controllers/transaction_categories_controller.rb
  - app/views/transactions/_form.html.erb
  - app/views/transactions/show.html.erb
  - config/routes.rb
  - app/views/splits/new.html.erb
  - db/schema.rb
depends:
  - ./money-currency-rules.md
  - ./provider-import-adapter.md
status: draft
---

# 거래 관리 (Entry·Transaction)

> 사용자가 화면(또는 API)으로 입력한 거래 한 건의 날짜·금액·통화·이름·분류를 만들고 고치고 지우며, 분할·일괄 수정·일괄 삭제·첨부·검색·보류 거래 수동 병합을 하고, 이 편집을 provider sync가 덮어쓰지 못하게 잠그는 규칙을 정의한다.

이 문서에서 쓰는 이름은 `Entry`(계정에 속한 원장 한 줄), `Transaction`(`Entry`의 세부, 입출금 한 건), 보호(protected)와 잠금(locked attribute)이다. 앞의 둘과 보호·잠금의 정의는 [provider-import-adapter](./provider-import-adapter.md) 1.3 용어 표와 같다. 이 문서는 사용자가 거래를 만지는 쪽의 규칙이고, provider가 거래를 넣을 때의 보호 skip·claim·`extra` 병합은 그 문서(R-06~R-37)가 갖는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

사용자가 수동 계정에 지출 거래를 입력하고, 나중에 분할하고 일괄 분류하는 대표 흐름이다. 정확한 기준은 1.4다.

1. 사용자가 계정·날짜·이름·금액·통화를 입력해 거래를 만든다. 서버는 `Entry`와 `Transaction`을 한 번에 저장하고, 저장한 속성을 모두 잠그고 `user_modified`를 켠 뒤, 그 계정의 잔액 재계산(sync)을 예약한다(R-04, R-05, R-13, R-70).
2. 사용자가 이름·카테고리를 고친다. 바뀐 속성만 잠기고, 바뀐 속성이 이름·메모·카테고리·가맹점뿐이면 잔액 재계산은 예약하지 않는다(R-11, R-12).
3. 사용자가 이 거래를 금액 합이 같은 여러 줄로 분할한다. 원본(parent)은 `excluded`가 되고 자식(child) 거래들이 잔액과 목록에 대신 들어간다(R-22~R-28).
4. 사용자가 목록에서 여러 건을 선택해 카테고리·태그를 한 번에 바꾼다. 분할 원본은 선택에서 빠지고, 권한이 주석(annotate)까지인 계정은 일부 필드만 바뀐다(R-31~R-36).
5. 은행 연동 계정에서는 보류(pending) 거래가 확정 거래와 짝이 안 맞아 둘 다 남을 수 있다. 사용자가 후보를 골라 병합하면 확정 거래가 남고 보류 거래는 지워진다(R-56~R-62).
6. 검색은 필터를 모두 AND로 묶어 분할 원본을 뺀 거래 목록과 합계를 만든다(R-42~R-54).

### 1.2 범위·통합 지점

- 제공: `Entry`·`Transaction`의 생성·수정·삭제, 분할·재분할·해제, 일괄 수정, 일괄 삭제, 첨부 파일, 검색·필터와 합계(`Transaction::Search`, `EntrySearch`), 사용자 수정 보호(`locked_attributes`, `user_modified`, `excluded`), 거래 `kind`, 보류 거래 수동 병합과 중복 제안의 거절·삭제, 수동 입력 중복 방지(idempotency key), 수동 대조 상태(`reconciled_status`), 거래를 매매(Trade)로 바꾸는 변환, 이 편집들이 잔액 재계산을 부르는 지점(R-70).
- 제외:
  - 분류 규칙·카테고리·태그·가맹점이 자동으로 값을 넣는 본문, 규칙 만들기 제안, 분류 마법사(wizard)의 묶음 계산(행 10 소관). 이 문서는 마법사가 `bulk_update!`를 부르는 지점만 쓴다(R-37).
  - 이체 매칭(행 3). 이 문서는 거래를 삭제할 때 `Transfer`가 같이 지워지고 상대 다리가 풀리는 결과만 쓴다(R-20).
  - 잔액 계산(행 1). 이 문서는 `account.sync_later`를 부르는 시점과 `window_start_date` 값까지만 정한다. 재계산의 내용과 `sync_later`의 합치기 규칙은 [sync-pipeline](./sync-pipeline.md) R-05·R-06이다.
  - 금액 부호·환산 일반([money-currency-rules](./money-currency-rules.md)). 이 문서는 입력 부호를 받는 곳(R-04, R-24)과 환산 실패를 만나는 곳(R-72)만 쓴다.
  - provider import 경로(보류·claim·`extra` 병합, 보류 거래 자동 제외 `Entry.auto_exclude_stale_pending`, `reconcile_pending_duplicates`)는 provider-import-adapter 소유다. 제안 기록의 형식은 그 문서 R-28·R-29, 이 문서는 사용자가 제안을 받아들이거나 거절하는 쪽이다.
  - 계정 접근 권한 모델(`AccountShare`)과 `Family` 테넌시. 별도 스펙이 없어서 이 문서가 쓰는 권한 판정(R-68)만 정의한다.
  - 반복 거래 등록(`mark_as_recurring`, 행 13), 거래의 `Trade`·`Valuation` 쪽 CRUD(행 4·1), API v1 전체(행 17). 거래에 관한 API 차이는 R-69에 요약한다.
- 외부 의존·선행 계약: DB는 PostgreSQL 기능(jsonb, partial unique index, `ILIKE`)을 전제한다. 파일 저장소(첨부), 현재 사용자와 가족(`Current.user`, `Current.family`)의 접근 범위, `Category`·`Merchant`·`Tag`의 존재와 가족 소유 판정, 환율 저장소(`ExchangeRate`)는 호출자가 제공한다. 보류 판정과 제안 기록 형식은 provider-import-adapter R-08·R-28·R-30을 쓴다.
- 소유 상태·부작용: `entries`(+`transactions`), `taggings`, 첨부(`active_storage_attachments`), 분할 자식 `entries`, `entries.locked_attributes`/`transactions.locked_attributes`, `user_modified`·`excluded`·`reconciled_status`, `transactions.extra` 중 `potential_posted_match`·`manual_merge`·`exchange_rate`를 쓴다. 계정의 sync를 예약한다. 캐시는 `Entry` 저장이 `Family`의 `entries_cache_version`을 바꾸는 방식으로 무효화된다(`entry.rb:7-12`).

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Entry` | 행 | `account_id`(필수), `date`, `name`(not null), `amount`(decimal(19,4) not null), `currency`, `notes`, `excluded`(기본 false), `user_modified`·`import_locked`(기본 false, not null), `locked_attributes`(map 속성명→잠근 시각, 기본 `{}`), `external_id`·`source`(provider용), `idempotency_key`(수동 입력 중복 방지), `parent_entry_id`(분할 자식이면 값), `reconciled_status`(`unreconciled`/`cleared`/`reconciled`, 기본 `unreconciled`), `reconciled_at`·`reconciled_by_statement_id`(명세서 대조), `entryable_type`+`entryable_id`(세부). 계정이 지워지면 `Entry`도 지워지고(DB cascade), 부모 `Entry`가 지워지면 자식도 지워진다. |
| `Transaction` | 행 | `category_id`(null 가능, 카테고리가 지워지면 null), `merchant_id`, `kind`(기본 `standard`), `investment_activity_label`, `extra`(jsonb, not null, 기본 `{}`), `locked_attributes`, `transfer_id`(`Transfer` 참조, null 가능. 이체 매칭이 채우고 이 문서는 읽지 않는다), `external_id`(이 문서는 쓰지 않음). 값 규칙은 C-01. |
| `Tagging` | 행 | `tag_id`(not null), `taggable_type`+`taggable_id`. `Transaction`의 태그는 이 연결 행이다. `Transaction.tag_ids`는 컬럼이 아니라 이 연결의 가상 속성이다(R-14). |
| 첨부 | 파일 | `Transaction`에 여러 개 붙는 파일. 제한은 R-38. |
| 분할 자식 | `Entry` | `parent_entry_id`가 있는 `Entry`. 부모와 같은 계정·날짜·통화다(R-23, R-25). |
| 보류 중복 제안 | `extra["potential_posted_match"]` | 형식은 provider-import-adapter R-28·R-29. 이 문서는 `dismissed`(true면 거절됨)와 `entry_id`를 읽는다(R-56). |

**연산(웹 화면 경로 기준, 문서의 R-ID가 규칙)**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| 거래 만들기 | 계정, `entry`(name, date, amount, currency, notes, excluded, nature, entryable 속성: category_id, merchant_id, kind, investment_activity_label, exchange_rate, tag_ids), 선택 idempotency_key(UUID) → 새 `Entry` 또는 검증 오류 | R-04~R-08 |
| 거래 수정 | 거래 id, 위와 같은 필드 → 수정된 `Entry` 또는 검증 오류 | R-09~R-14 |
| 태그 수정 | 거래 id, `toggle_tag_id`(하나 토글) 또는 `tag_ids`(전체 교체) → 태그 목록 | R-15 |
| 거래 삭제 / 일괄 삭제 | 거래 id / `entry_ids` → 삭제 건수 | R-20, R-21 |
| 분할 만들기·고치기·해제 | 거래 id, `splits`(name, amount, category_id, merchant_id, excluded, tag_ids 목록) | R-22~R-30 |
| 일괄 수정 | `entry_ids`, date, notes, name, category_id, merchant_id, reconciled_status, tag_ids → 바뀐 건수 | R-31~R-36 |
| 첨부 올리기·보기·삭제 | 거래 id, 파일 | R-38~R-41 |
| 검색·목록 | `q`(필터 맵), page, per_page → 거래 목록, 합계 | R-42~R-55 |
| 보류 병합 후보·병합·제안 거절 | 보류 거래 id, 확정 `Entry` id | R-56~R-62 |
| 잠금 풀기 | 거래 id | R-13 |
| 수동 대조 상태 넘기기 | 거래 id | R-17 |
| 환율 조회 | 계정 id, 통화, 날짜 → `{rate}` | R-08 |
| 이름 제안 | 입력 문자열 → 이름과 가장 많이 쓴 카테고리 | R-67 |
| 매매로 변환 | 거래 id, 종목, qty·price → 새 `Trade` `Entry` | R-64 |

**엔드포인트별 id 종류**: 같은 URL 모양이라도 그 id가 `Entry` id인지 `Transaction` id인지가 엔드포인트마다 다르다. 구현자는 이 표대로 맞춰야 한다.

| id 종류 | 엔드포인트 |
|---|---|
| `Entry` id | 웹 거래 show·update·destroy, `update_tags`(`PATCH /transactions/:id/tags`), 분할(`/transactions/:transaction_id/split`), 수동 병합(`.../pending_duplicate_merges`), 카테고리 선택(`PATCH /transactions/:transaction_id/category`), 이체 매칭(`transfer_match`) |
| `Transaction` id | 웹 `unlock`, `reconcile`, `merge_duplicate`, `dismiss_duplicate`, `convert_to_trade`, `create_trade_from_transaction`, `mark_as_recurring`, 첨부(`.../attachments`), API v1 거래·분할 전체(`/api/v1/transactions/:id`, `:transaction_id/split`) |

### 1.4 행동 규칙과 남은 질문

**생성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Entry`의 세부(entryable) | `entryable_type`은 `Valuation`·`Transaction`·`Trade` 셋 중 하나이고, `Entry` 하나가 세부 하나를 가리킨다. `Entry`를 지우면 세부도 지워지고, 세부를 지우면 그 `Entry`도 지워진다. 이 문서는 `Transaction`을 다룬다. | 코드 확인 |
| R-02 | `Entry` 저장 검증 | `date`·`name`·`amount`·`currency`가 비어 있으면 저장이 실패한다. `date`는 오늘 − 30년(`min_supported_date`)보다 엄격하게 커야 한다. 날짜 상한은 없어서 미래 날짜도 저장된다(R-71). `external_id`와 `source`가 둘 다 있으면 같은 계정 안에서 `(source, external_id)`가 유일해야 한다. `amount`는 소수 4자리까지 저장된다. | 코드 확인 |
| R-03 | 새 `Transaction` `Entry`이고 `import_id`가 없고 `name`이 blank이고 `external_id`·`source`가 둘 다 없고, 가족 설정 `auto_generate_transaction_names`가 true다(기본 false) | 이름을 `"<카테고리 표시 이름> - <가맹점 이름>"`으로 채운다(없는 쪽은 빼고 `" - "`로 잇는다). 둘 다 없으면 이름은 blank로 남고 R-02 때문에 저장이 실패한다("Unknown" 같은 대체 이름은 넣지 않는다). 저장이 실패해 폼을 다시 보여줄 때는, 사용자가 이름을 비워 보냈으면 이 생성된 이름을 폼에서 다시 비운다. 안 비우면 사용자가 카테고리를 바꿔 다시 제출할 때 낡은 생성 이름이 그대로 저장된다. | 코드 확인 |
| R-04 | 사용자가 거래를 만든다(웹 `create`) | 계정은 `accessible_accounts`에서 찾고(없으면 계정 없는 `Entry`로 검증해 422로 폼을 다시 보여준다), 있으면 그 계정에 대한 쓰기 권한(R-68의 write)이 있어야 한다. `amount`·`date`가 비어 있으면 파라미터에서 빼므로 R-02의 presence 오류가 난다. `nature`가 `inflow`이면 입력 amount의 부호를 뒤집어 저장하고, `nature`가 있어도 `inflow`가 아니면 입력값을 그대로 저장한다(`outflow`에 음수를 넣으면 음수 그대로다). `nature`가 없으면 입력값 그대로다. 부호 규약은 money-currency-rules R-36(음수 = 유입)이다. `currency`는 `entry[currency]`로 받고, 비어 있으면 R-02로 실패한다(계정 통화로 대신 채우지 않는다. 폼의 기본값이 계정 통화다). 허용 필드는 C-12. `entry[entryable_type]`은 폼이 `"Transaction"`을 숨은 필드로 보내고(`_form.html.erb:13`) 이 값이 없으면 세부 `Transaction`이 만들어지지 않으므로 사실상 필수다(추론: 세부가 없는 `Entry`가 저장되지 않는다는 판단). | 코드 확인 / 추론(필수성) |
| R-05 | 생성 저장이 성공한다 | 순서대로: (1) `sync_account_later`(R-70), (2) `lock_saved_attributes!`(R-13), (3) `mark_user_modified!`, (4) 태그가 있으면 `tag_ids` 잠금(R-14). 결과로 이 거래는 `user_modified = true`이고 `locked_attributes`에 생성 때 저장된 속성(`account_id`, `date`, `name`, `amount`, `currency`, `entryable_type`, `entryable_id`, `idempotency_key` 등)이 모두 들어간다. 그래서 수동 입력 거래는 만들자마자 provider sync 보호 대상이다(provider-import-adapter R-09). 저장 실패면 위 단계는 하나도 실행되지 않는다. | 코드 확인 |
| R-06 | 생성 요청에 idempotency key가 있다 | 키가 UUID 형식(8-4-4-4-12 16진, 대소문자 무시)일 때만 쓴다. 그 밖의 값(없음, 변조, 문자열 아님)은 오류가 아니라 중복 방지만 꺼진 채로 만든다. `(account, idempotency_key)`가 같은 `Entry`가 이미 있으면 새로 만들지 않고 첫 요청의 성공 응답을 그대로 돌려준다. 거의 동시에 온 두 요청은 DB의 부분 unique index `(account_id, idempotency_key)`(key not null일 때)가 하나만 통과시키고, 진 쪽은 위반 오류를 받아 이긴 쪽의 `Entry`로 성공 응답한다. 키는 `external_id`·`source`와 별개 컬럼에 저장한다(그 둘을 쓰면 수동 거래가 provider 연동 거래로 보여 필드가 잠기고 중복 후보에서 빠지기 때문이다). 폼이 열릴 때마다 새 UUID를 만들고, 검증 실패로 폼을 다시 그릴 때는 제출된 UUID를 유지한다. | 코드 확인 |
| R-07 | 거래의 통화 | `Entry.currency`는 거래 자신의 통화로 계정 통화와 달라도 된다. 거래 한 건의 환율은 `Transaction.extra.exchange_rate`(숫자 > 0)에 선택적으로 저장한다. 비우면 nil, 숫자가 아니거나 유한하지 않으면 "must be a number", 0 이하면 "must be greater than 0"으로 저장이 실패한다. `exchange_rate=`는 값이 비어 있어도 `extra`에 `{"exchange_rate" => nil, "exchange_rate_invalid" => false}`를 병합한다. 그래서 요청의 `entryable_attributes`에 `exchange_rate` 키가 있으면(새 거래 폼은 항상 보내고 거래 상세의 수정 폼에는 이 필드가 없다) 값이 비어 있어도 `extra`가 바뀐 것이 되어 R-12가 true(sync 예약)가 되고 `extra`가 잠긴다. 이 값을 환산에 쓰는 쪽은 money-currency-rules R-22다. | 코드 확인 |
| R-08 | 환율 조회(`exchange_rate` 화면 보조 엔드포인트) | 계정 통화와 요청 통화가 같으면 `{same_currency: true, rate: 1.0}`. 다르면 `find_or_fetch_rate(from: 요청 통화, to: 계정 통화, date)`(date 기본 오늘)를 부르고 결과가 nil이면 `{error}` 404를 돌려주고, 아니면 `{rate, account_currency}`를 돌려준다. 환율이 없다고 1.0으로 대신하지 않는다. 계정은 가족의 계정이면 되고 접근 권한은 보지 않는다. | 코드 확인 |

**수정과 사용자 수정 보호**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | 사용자가 거래를 수정한다(웹 `update`) | 거래는 접근 가능한 계정의 것이어야 찾힌다(없으면 404). 허용 파라미터는 계정 권한으로 정해진다. owner·full_control: R-04의 필드 전부. read_write: `notes`와 entryable의 `category_id`·`merchant_id`·`tag_ids`뿐. read_only: 빈 파라미터. 수정 컨트롤러에는 권한 확인 호출이 따로 없어서, read_only 사용자의 수정 요청도 빈 파라미터로 성공하고 이어서 R-11이 실행되어 `user_modified`가 켜진다. `date`·`amount`가 비어 있으면 파라미터에서 빠져 기존 값이 유지된다. 검증이 실패하면 422로 상세 화면을 다시 보여주고 R-11의 후속 단계는 실행되지 않는다. | 코드 확인 |
| R-10 | 수정 파라미터에 `category_id`가 있고 이 거래가 이체의 입금 다리(`transfer_as_inflow`가 있고 그 `Transfer`가 categorizable. `Transfer.status`는 보지 않아 pending도 포함)다 | `category_id`를 파라미터에서 빼고 나머지만 저장한다. 입금 다리에는 출금 다리의 카테고리가 읽기 전용으로 보인다. 이 판정은 거래의 `kind`가 아니라 `Transfer` 레코드로 한다(`kind`를 `standard`로 바꿔도 우회되지 않는다). `Transfer#categorizable?`는 이체 매칭 스펙 소관이다. 일괄 수정(R-36)과 분류 wizard에는 이 검사가 없다. | 코드 확인 (검색 범위는 2.1) |
| R-11 | 수정 저장이 성공한다 | 순서대로: (1) 저장 직후에 `saved_changes_affect_balances?`를 계산한다(R-12, 이후 쓰기가 변경 기록을 지우므로 먼저 한다). (2) 카테고리가 바뀌었으면 그 카테고리의 `last_used_at`을 갱신한다(수동 선택일 때만, 규칙·import는 갱신 안 함). (3) 카테고리 규칙 만들기 안내 표시 여부를 판정한다(행 10). (4) `lock_saved_attributes!`, (5) `mark_user_modified!`, (6) 태그가 하나라도 있으면 `tag_ids` 잠금. (7) (1)이 true였으면 `sync_account_later`. 이 모든 단계는 변경이 없는 수정에도 실행되어 `user_modified`를 켠다. 카테고리 선택 전용 엔드포인트는 순서와 내용이 다르다(R-73). | 코드 확인 |
| R-12 | 수정이 잔액에 영향을 주는가(`saved_changes_affect_balances?`) | 이번 저장에서 바뀐 `Entry` 속성 중 `name`, `notes`, `updated_at` 밖의 것이 하나라도 있거나, 바뀐 `Transaction` 속성 중 `category_id`, `merchant_id`, `updated_at` 밖의 것이 하나라도 있으면 true다. 그러므로 `date`, `amount`, `currency`, `excluded`, `kind`, `investment_activity_label`, `extra`(환율 포함)의 변경은 true이고, 이름·메모·카테고리·가맹점만 바꾸면 false라서 sync를 부르지 않는다. 태그 변경은 `Entry`·`Transaction` 속성을 바꾸지 않으므로 이 판정에 안 걸린다. `Transaction`이 아닌 entryable이면 `updated_at`만 제외한다. 요청이 `exchange_rate` 키를 보내면 값이 비어 있어도 `extra`가 바뀌므로 true다(R-07). | 코드 확인 / 추론(태그 변경이 속성을 안 바꾼다는 점은 가상 속성 동작을 읽은 판단) |
| R-13 | 잠금 메커니즘 | `locked_attributes`는 `속성명 → 잠근 시각` map이고, 값이 있으면 그 속성은 잠긴 것이다. `Entry`와 `Transaction` 둘 다 따로 갖는다. `lock_saved_attributes!`는 직전 저장에서 바뀐 속성 이름 중 `id`·`created_at`·`updated_at`을 뺀 것을 모두 잠그고(`Entry`를 먼저, 이어서 세부), 이미 잠긴 속성은 시각만 새로 쓴다. 잠금은 사용자의 편집을 막지 않고 provider sync와 규칙·AI의 자동 갱신만 막는다(provider-import-adapter R-31~R-34, `enrich_attributes`는 잠긴 속성을 건너뛴다). `unlock`(웹, write 권한 필요)은 한 DB transaction에서 `Entry`의 `user_modified`·`import_locked`를 false로, `locked_attributes`를 `{}`로 되돌리고 세부의 `locked_attributes`도 `{}`로 되돌린다. 보호 플래그 3개의 의미와 skip 순서(excluded > user_modified > import_locked)는 provider-import-adapter R-09다. | 코드 확인 |
| R-14 | 태그 잠금 | `tag_ids`는 컬럼이 아니라 `taggings`를 통한 가상 속성이다. 생성·수정·일괄 수정은 태그가 하나라도 남은 경우에만 `tag_ids`를 잠그고, 태그를 모두 지운 경우에는 잠그지 않는다. 태그 수정 엔드포인트(R-15)는 항상 잠근다. | 코드 확인 |
| R-15 | 태그 수정(`update_tags`) | annotate 권한(owner·full_control·read_write)이 필요하다. `toggle_tag_id`가 있으면 가족의 그 태그 하나를 행 잠금(row lock) 안에서 있으면 지우고 없으면 만든다(두 번 빠르게 눌러도 서로 덮지 않는다). 없으면 `tag_ids` 중 가족 소유인 것만 골라 전체를 교체한다(남의 가족 태그는 조용히 버린다). 이어서 `lock_saved_attributes!`, `mark_user_modified!`, `tag_ids` 잠금을 실행한다. `sync_account_later`는 부르지 않는다. | 코드 확인 |
| R-16 | `excluded` 플래그 | 사용자가 `excluded`를 직접 켜고 끌 수 있다(허용 필드, C-12). 켜진 거래는 (a) provider sync에서 보호된다(provider-import-adapter R-09), (b) 소득·지출 통계, 목표, 반복 거래 매칭, "Uncategorized" 카운트, 이체 매칭 후보에서 빠진다. (c) 계정 잔액 계산에서는 빠지지 않는다(잔액 계산은 보류·분할 원본·미래 날짜만 뺀다). 분할 원본은 시스템이 `excluded = true`로 만들고, 자식이 있는 동안 `excluded`를 false로 되돌리는 저장은 검증 오류다. | 코드 확인 ((b)의 대상 목록은 검색 범위 한정, 2.1) |
| R-17 | 수동 대조 상태 넘기기(`reconcile`) | 가족 설정 `manual_reconciliation`이 true일 때만(아니면 404) 쓸 수 있고, write 권한과 수동(연동 안 된) 계정이어야 한다. `unreconciled → cleared → reconciled → unreconciled` 순환으로 한 칸 넘긴다. 이 변경은 잠금·`user_modified`를 건드리지 않고 sync도 부르지 않는다. 일괄 수정(R-35)에서도 같은 값을 쓸 수 있다. 명세서 대조(`reconciled_at`, `reconciled_by_statement_id`)는 별개 개념이고 이 문서 범위 밖이다. | 코드 확인 |
| R-18 | 거래 `kind` | 값은 6개(C-01): `standard`(기본, 예산 분석에 포함), `funds_movement`, `cc_payment`, `one_time`(예산 분석에서 제외), `loan_payment`, `investment_contribution`(실제 지출로 예산에 포함). `transfer?`는 `kind`가 `funds_movement`·`cc_payment`·`loan_payment`·`investment_contribution` 넷 중 하나일 때다. 사용자는 거래 폼의 `kind`로 직접 바꿀 수 있고, 바꾼 값은 R-13 때문에 잠긴다. 6개 밖의 값은 enum 오류를 일으킨다(추론: 프레임워크 동작). 이체 매칭이 `kind`를 정하고 푸는 규칙은 행 3, provider가 `kind`를 정하는 규칙은 provider-import-adapter R-39다. | 코드 확인 / 추론(6개 밖 값의 오류) |
| R-19 | `investment_activity_label` | 거래 폼에서 받는다. `Transaction`에는 값 목록 검증이 없다. 허용 목록(UI 드롭다운) 13개는 C-01의 `ACTIVITY_LABELS`다. | 코드 확인 |

**삭제**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 거래 한 건 삭제(웹 `destroy`) | write 권한이 필요하다. `Entry`를 삭제하면 (1) 세부 `Transaction`이 지워지고, (2) 그 `Transaction`이 속한 `Transfer`(입금 다리 또는 출금 다리)와 수수료 거래(`fee_transactions`)가 지워지고, 반대쪽 다리는 지워지지 않고 `kind`가 `standard`로 돌아가며(보류 상태의 자동 매칭이 아닐 때) 그 `kind` 잠금이 풀린다, (2-1) 남은 다리의 `idempotency_key`는 nil로 지워지고(같은 키로 재시도한 생성 요청이 낡은 키에 걸려 실패하지 않게 하려는 목적) 그 거래에 걸린 거절 이체 기록(`RejectedTransfer`) 행도 같이 지워진다, (3) 태그 연결이 지워진다, (4) 분할 원본이면 자식도 같이 지워진다, (5) 첨부는 정리된다(추론: 프레임워크 기본 동작). 삭제 후 `sync_account_later`를 부르는데, 삭제된 `Entry`는 날짜 창을 계산하지 않으므로 `window_start_date`가 nil(제한 없는 전체 재계산)이다(R-70). 분할 자식은 개별 삭제가 중단된다(R-25). 삭제 결과 메시지는 계정 화면으로 돌아간다. | 코드 확인 / 추론((5)) |
| R-21 | 일괄 삭제(`bulk_deletions#create`) | 가족의 계정 중 사용자가 쓰기 가능한(owner 또는 full_control) 계정의 `Entry`만, 그중 `parent_entry_id`가 없는 것만 `entry_ids`로 골라 삭제한다. 쓰기 불가 계정과 분할 자식은 조용히 제외되고 오류가 없다. 삭제는 거래마다 콜백을 실행하는 개별 삭제이고 컨트롤러가 전체를 하나의 DB transaction으로 묶지 않으므로, 중간에 실패하면 그 앞의 삭제는 남는다(추론: 전체 transaction 코드가 없음을 읽은 판단). 삭제 뒤 영향받은 계정마다 창 없는 `sync_later`를 한 번 부른다. 응답은 삭제된 건수 문구다. | 코드 확인 / 추론(부분 삭제) |

**분할 (split)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 거래를 분할할 수 있는가(`splittable?`) | 이체 `kind`가 아니고, 분할 자식이 아니고, 이미 분할 원본이 아니고, 보류가 아니고(provider-import-adapter R-30), `excluded`가 아니어야 한다. 웹 `create`는 이 판정 뒤에 락을 잡고(R-28) 같은 조건(분할 원본·`excluded`·이체·보류)을 다시 확인하며, 안 맞으면 "not splittable" 알림으로 돌아간다. | 코드 확인 |
| R-23 | 분할 실행(`split!`, C-02) | `splits` 각 줄의 `amount` 합(십진수)이 원본 `amount`와 정확히 같아야 한다. 다르면 오류("Split amounts must sum to parent amount (expected …, got …)")이고 아무것도 저장하지 않는다. 줄 수의 최솟값 검증은 없다. 한 DB transaction에서: 줄마다 자식 `Entry`(+`Transaction`)를 만든다. 자식은 원본의 계정·날짜·통화·`import`·`import_locked`를 그대로 물려받고, 줄의 `name`·`amount`·`notes`를 쓰며, `excluded`는 줄 값이 참 값(`true`, `"true"`, `"1"`, `1`)일 때만 true다. 자식의 `Transaction`은 줄의 `category_id`, 줄의 `merchant_id`(없으면 원본의 가맹점), 줄의 태그(없으면 태그 없음), 원본의 `kind`를 갖는다. 자식은 `user_modified`가 아니고 잠금도 없다(규칙이 `lock_attributes: true`로 부른 경우만 줄이 정한 카테고리·가맹점을 잠근다). 마지막으로 원본을 `excluded = true`로 바꾸고 `user_modified`를 켠다. 줄별 금액의 부호·0 검증은 없다(합만 맞으면 음수·0인 줄도 허용). `splits`가 빈 목록이어도 원본 `amount`가 0이면 합(0)이 같아 통과해서, 자식 없이 원본만 `excluded = true`·`user_modified`가 된다. 웹 분할 만들기·고치기에서 `RecordInvalid`가 나면 오류 메시지를 알림으로 보여주고 돌아간다. | 코드 확인 |
| R-24 | 분할 입력의 부호(웹) | 웹 분할 화면은 원본 금액을 `−amount`로 보여주고(지출 거래는 음수 표기), 입력 합계와 비교한다. 서버는 제출된 각 줄 `amount`에 −1을 곱해서 `split!`에 넘긴다. 그러므로 화면 입력은 "화면에 보이는 부호"이고 저장은 `Entry` 부호 규약(R-04)이다. API v1의 분할은 원본과 같은 부호의 값을 그대로 받는다(R-69). | 코드 확인 |
| R-25 | 분할 자식의 제약 | (a) 자식의 `date`는 부모의 `date`와 같아야 한다(바꾸는 저장이 검증 오류). (b) 자식은 개별 삭제가 중단된다(부모 삭제나 분할 해제 때만 삭제). 웹 단건 삭제 요청이 직접 이를 만나면 삭제 중단이 예외(`RecordNotDestroyed`)가 되고 이를 처리하는 코드가 없다(화면은 자식에 삭제 버튼을 그리지 않는다, R-74. 직접 요청의 응답 종류는 확인 한계). 일괄 삭제는 조용히 건너뛴다(R-21). (c) 일괄 수정은 자식의 `date`를 바꾸지 않는다(R-32). (d) 분할 원본은 일괄 수정과 분류 wizard의 대상에서 빠진다(R-31, R-37). | 코드 확인 |
| R-26 | 분할 고치기(`resplit!`) | 락 안에서 이미 분할 원본인지 확인하고(아니면 "not split" 알림), 맞으면 기존 자식을 모두 지운 뒤 새 줄로 `split!`을 다시 한다. 자식에 나중에 붙인 카테고리·`excluded`·태그는 이월되지 않는다. 이 경로는 보류·이체 여부를 다시 확인하지 않는다. 성공하면 `sync_account_later`를 부른다. | 코드 확인 |
| R-27 | 분할 해제(`unsplit!`) | 락 안에서 분할 원본인지 확인하고 자식을 모두 삭제한 뒤 원본의 `excluded`를 false로 되돌린다. 원본의 `user_modified`는 true로 남는다. 성공하면 `sync_account_later`. | 코드 확인 |
| R-28 | 분할 동시성 | 분할·고치기·해제는 먼저 `Transaction` 행, 이어서 `Entry` 행의 순서로 락을 잡고 그 안에서 조건을 다시 확인한다(순서를 고정해 교착을 막는다). 두 요청이 동시에 분할하면 하나만 자식을 만들고 진 쪽은 "not splittable"이 된다(합계가 두 번 잡히는 것을 막는 목적이다). | 코드 확인 |
| R-29 | 분할 쓰기 권한과 입력 정리 | 만들기·고치기·해제는 write 권한이 필요하다. 줄의 `category_id`·`merchant_id`·`tag_ids`는 가족이 쓸 수 있는 것만 남기고 나머지는 조용히 버린다(가맹점은 사용자가 볼 수 있는 가맹점, 규칙 분할은 가족 가맹점만. "볼 수 있는 가맹점"의 정의는 R-75). 고치기·해제·편집 화면은 자식에서 열어도 부모로 올라가서 처리한다. | 코드 확인 |
| R-30 | 분할 후 집계 | 거래 목록·검색·잔액 재계산은 분할 원본을 제외하고 자식을 포함한다(`excluding_split_parents`). 분할·고치기·해제가 성공하면 R-70대로 sync를 예약한다. 첨부는 원본에 남는다(R-41). | 코드 확인 |

**일괄 수정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | 일괄 수정 대상 선택 | 사용자가 주석(annotate) 가능한 계정의 `Entry` 중 분할 원본이 아닌 것을 `entry_ids`로 고른다. 그중 쓰기 가능(owner·full_control) 계정의 것은 모든 필드를, 주석만 가능한 계정(read_write)의 것은 `notes`·`category_id`·`merchant_id`·`tag_ids`만 바꾼다. 읽기 전용이거나 접근 불가 계정의 `Entry`는 조용히 제외된다. | 코드 확인 |
| R-32 | `bulk_update!`의 필드 처리(C-05) | 바꿀 수 있는 필드는 `date`, `notes`, `name`, `reconciled_status`, `category_id`, `merchant_id`, 태그. 빈 값(nil, 빈 문자열)은 "바꾸지 않음"이라서 일괄 수정으로 카테고리·가맹점·메모를 비울 수는 없다. 태그는 `update_tags: true`(요청에 `tag_ids` 키가 있을 때)일 때만 바꾸고, 빈 목록이면 태그를 모두 지운다. 거래마다: 분할 자식은 `date`를 빼고, `Transaction`이 아니면 카테고리·가맹점을 빼고, 연동된 계정이면 `reconciled_status`를 뺀다. 그다음 `update!`, 카테고리 사용 기록(R-11 (2)), 그리고 `reconciled_status`만 바뀐 게 아니면 `lock_saved_attributes!`+`mark_user_modified!`(대조만 바꾼 건 검증 행위이므로 잠그지 않는다). 태그를 바꿨으면 태그가 남았을 때 `tag_ids`를 잠그고 `lock_saved_attributes!`+`mark_user_modified!`. 전체가 한 DB transaction이라서 한 건이라도 검증 실패하면 전부 되돌려진다. 반환값은 바뀐 `Entry` 수다. 필드가 하나도 없으면 0을 반환한다. | 코드 확인 |
| R-33 | 일괄 수정 입력의 가족 범위 정리 | `category_id`는 가족의 카테고리가 아니면 nil이 되어 "바꾸지 않음"으로 처리된다(오류 없음). `merchant_id`는 사용자가 쓸 수 있는 가맹점이 아니면 같다. 태그는 가족 태그만 남기고, 태그를 요청했는데 하나도 유효하지 않으면 태그는 건드리지 않는다(지우지 않는다). 명시적 빈 목록만 태그를 지운다. 응답 문구는 항상 "<n> transactions updated"다. | 코드 확인 |
| R-34 | 일괄 수정과 sync | `date`가 바뀐 `Entry`가 있으면 계정마다 (이전 날짜, 새 날짜) 중 가장 이른 날짜를 모아 그 날짜를 `window_start_date`로 계정당 한 번 `sync_later`를 부른다. 미래 날짜가 된 `Entry`에는 예약 job을 건다(R-71). 날짜 말고 다른 필드만 바꾸면 sync를 부르지 않는다. | 코드 확인 |
| R-35 | 일괄 수정의 `reconciled_status` | 값이 있으면 `manual_reconciliation`이 켜져 있어야 하고(아니면 알림 후 중단), 값은 3개 중 하나여야 한다(아니면 알림 후 중단). 이 검사는 `bulk_update!` 호출 전에 한다. 검증 오류(`RecordInvalid`)는 전체 롤백 후 "failure" 알림이다. | 코드 확인 |
| R-36 | 일괄 수정에는 R-10(이체 입금 다리의 카테고리 차단)이 없다 | 일괄 수정과 분류 wizard의 카테고리 변경은 이체 입금 다리에도 그대로 적용된다. | 코드 확인 (`grep -rn "category_set_on_transfer_outflow\|category_editable" app --include=*.rb` 결과가 단건 수정·카테고리 선택 컨트롤러·뷰 helper뿐이었음) |
| R-37 | 분류 wizard(`Transactions::CategorizesController`)의 카테고리 확정 | 한 묶음(또는 한 건)을 카테고리로 확정하는 `create`·`assign_entry`는 `annotatable_entries`에서 분할 원본을 뺀 대상에 `bulk_update!({category_id: ...})`를 부른다. 따라서 R-32의 잠금·`user_modified`가 같이 적용된다. 묶음 계산, 규칙 만들기(`Rule.create_from_grouping`)는 행 10이다. wizard와 미분류 배지가 쓰는 `Entry.uncategorized_transactions`는 카테고리 없음, `kind`가 `funds_movement`·`cc_payment`가 아님, `excluded`가 false, 계정 상태 draft·active를 모두 건다. 검색 필터 R-48의 "Uncategorized"는 앞의 두 조건(카테고리 없음, `kind`)만 같고 `excluded`를 거르지 않으며, 계정 상태는 `active_accounts_only`(기본 true)일 때만 같은 조건이다. 그래서 `excluded` 거래는 검색의 Uncategorized에는 나오고 배지·wizard 대상에는 없다. | 코드 확인 |

**첨부**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-38 | 첨부 제한 | 거래당 최대 10개, 파일당 10MB 이하, 콘텐츠 타입은 `image/jpeg`·`image/jpg`·`image/png`·`image/gif`·`image/webp`·`application/pdf`만 허용한다. 위반하면 `Transaction` 저장 검증이 실패한다(개수 초과, 파일별 크기, 파일별 형식 오류). 확장자는 검사하지 않고 `content_type`만 본다. | 코드 확인 |
| R-39 | 첨부 올리기 | owner·full_control·read_write 권한이 필요하다(아니면 "not authorized"). 거래 행에 락을 잡고 (기존 개수 + 새 파일 수)가 10을 넘으면 파일 전체를 거부한다(일부만 붙이지 않는다). 아니면 붙이고 검증하여, 실패하면 오류 알림을 보여주고 이번에 올린 파일은 거래에 남지 않는다(코드는 새로 붙은 첨부를 `purge`로 지운다. 붙이는 순간 저장소에 올라가는지와 purge의 저장소 효과는 프레임워크 동작이라 추론). 파일이 없으면 "파일 미선택" 알림. 어떤 예외든 잡아서 일반 실패 알림만 낸다. 첨부는 잠금·`user_modified`·sync에 영향이 없다. | 코드 확인(결과) / 추론(purge) |
| R-40 | 첨부 보기·삭제 | 보기는 접근 가능한 계정의 거래이면 되고 `disposition` 파라미터가 `attachment`이면 내려받기, 아니면 인라인으로 저장소의 blob URL로 리다이렉트한다. 삭제는 owner·full_control만 가능하고 파일을 purge한다. | 코드 확인 |
| R-41 | 분할·병합과 첨부 | 분할해도 첨부는 숨겨진 원본에 남고, 첨부 필터는 자식이 "원본에 첨부가 있으면 첨부 있음"으로 센다(R-51). 보류 병합은 보류 거래의 첨부 연결을 확정 거래로 옮긴다(R-58). | 코드 확인 |

**검색·필터**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-42 | 목록·검색 요청의 필터 파라미터(`q`) | 허용 키: `start_date`, `end_date`, `search`, `amount`, `amount_operator`, `active_accounts_only`, `accounts`, `account_ids`, `categories`, `merchants`, `types`, `tags`, `status`, `ai_status`, `attachment_status`, `reconcile_status`. 빈 값은 모두 버린다. `amount`가 없으면 `amount_operator`도 버린다. `ai_status`와 `attachment_status`는 허용 값(`current`·`history`, `with`·`without`)만 남기고, 남는 게 없으면 키를 지운다. 필터는 모두 AND로 합쳐진다. | 코드 확인 |
| R-43 | 검색 대상 집합(`transactions_scope`) | 가족의 `Transaction`이고 분할 원본은 제외한다. 사용자가 접근 가능한 계정으로 한정한다(접근 가능 계정이 하나도 없으면 결과가 비어 있다). `active_accounts_only`(기본 true)이면 상태가 draft·active인 계정만 포함한다. 정렬은 이 집합이 아니라 목록 컨트롤러(`index`)가 `reverse_chronological`로 붙인다: 날짜 내림차순, 같은 날이면 평가(`Valuation`)를 뒤로, 이어서 `created_at` 내림차순, `id` 내림차순. 한 페이지 크기는 R-55다. | 코드 확인 |
| R-44 | `search` 문자열 | `entries.name` 또는 `entries.notes`에 그 문자열이 부분 포함되면 일치한다(대소문자 무시 `ILIKE`, 문자열 안의 `%`·`_`는 이스케이프한다). 공백·유니코드 정규화는 하지 않는다. | 코드 확인 |
| R-45 | 날짜·금액·계정 필터 | `start_date`·`end_date`는 각각 있을 때만 `date >= `, `date <= `(양끝 포함)로 건다. `amount`+`amount_operator`는 `|amount|` 기준이다: `equal`은 `||entry.amount| − 입력|`이 0.01 이하, `less`는 미만, `greater`는 초과다. 연산자가 이 셋이 아니면 필터를 걸지 않는다. 금액은 환산 없이 거래의 원래 통화 금액끼리 비교한다. `accounts`는 계정 이름, `account_ids`는 계정 id로 거른다(둘 다 있으면 모두 만족). | 코드 확인 |
| R-46 | `status` 필터 | `pending`만이면 보류 거래, `confirmed`만이면 보류가 아닌 거래. 둘 다 고르면 필터 없음. 보류 판정은 provider-import-adapter R-30(`PENDING_PROVIDERS` 10개 네임스페이스의 `pending` 값)이다. | 코드 확인 |
| R-47 | `types` 필터 | `expense`는 `amount >= 0`이고 `kind`가 이체 4종이 아닌 것, `income`은 `amount < 0`이고 이체 4종이 아닌 것, `transfer`는 `kind`가 이체 4종인 것이다(금액 부호와 무관). 조합은 합집합이다. 셋을 모두 고르면 필터 없음. 금액 0은 지출이다. | 코드 확인 |
| R-48 | `categories` 필터 | 이름으로 고르고, 이름이 같은 가족 카테고리의 자식(parent_id가 그 카테고리)도 함께 일치한다. 가상 값 "Uncategorized"(`Category::UNCATEGORIZED_FILTER_VALUE`)는 카테고리가 없고 `kind`가 `funds_movement`·`cc_payment`가 아닌 거래다(이체의 두 다리는 분류할 것이 없어서 뺀다. `loan_payment`·`investment_contribution`은 포함). 이 필터는 가족이 반드시 주어져야 하고 없으면 `ArgumentError`다. | 코드 확인 |
| R-49 | `merchants`·`tags` 필터 | 가맹점은 이름, 태그는 이름으로 고르고 하나라도 일치하면 포함한다(any-of). 가상 값 "No merchant"(`Merchant::NO_MERCHANT_FILTER_VALUE`)·"Untagged"(`Tag::UNTAGGED_FILTER_VALUE`)는 가맹점·태그가 없는 `Transaction`이다. 태그 필터는 거래가 여러 태그와 일치해도 한 줄로 나오고 합계에서 중복 계산되지 않도록 서브쿼리로 한다. | 코드 확인 |
| R-50 | `ai_status` 필터 | `current`는 자동 분류(AI 또는 Bayes)가 정한 카테고리가 지금도 그 값인 거래, `history`는 자동 분류 기록이 있지만 지금은 그 값이 아닌(사용자가 바꿔 기록이 superseded) 거래, 둘 다 고르면 자동 분류 기록이 있는 모든 거래다. 자동 분류와 superseded 의미는 행 10 소관이고 이 문서는 필터 조건만 쓴다. | 코드 확인 |
| R-51 | `attachment_status`·`reconcile_status` 필터 | `attachment_status`는 `with`·`without` 중 하나만 고르면 적용하고(둘이면 필터 없음), 거래 자신 또는 분할 부모에 첨부가 있으면 "있음"이다. `reconcile_status`는 허용 3값만 남기고, 수동(연동 안 된) 계정의 거래 중 그 값을 가진 것으로 한정한다(연동 계정의 거래는 기본값 `unreconciled`이어도 일치하지 않는다). | 코드 확인 |
| R-52 | `EntrySearch`(계정 화면 등 `Entry` 기준 검색) | `Transaction::Search`와 같은 필터 일부를 `Entry`에 건다. 텍스트·날짜·금액·계정·상태 필터는 R-44~R-46과 같고, `categories`·`types`·`merchants`·`tags` 중 하나라도 있으면 `Transaction` 항목만 남기고 R-47~R-49와 같은 필터를 건다. `Valuation`·`Trade`는 그런 필터가 켜지면 결과에서 빠진다. 호출처는 계정 상세 목록 두 곳이다. `accounts_controller.rb:111`은 분할 원본을 빼고(`excluding_split_parents`) 가족을 넘긴다. `accountable_resource.rb:29`는 분할 원본을 빼지 않고 가족도 넘기지 않는다. 후자는 `categories` 필터가 들어오지 않는 경로라서 R-48의 `ArgumentError`에는 도달하지 않는 것으로 본다(추론). | 코드 확인 |
| R-53 | 검색 합계(`totals`) | 검색 결과 집합에서 `count`, 지출 합, 수입 합, 이체 유입 합, 이체 유출 합을 `family.currency`로 계산한다. 지출은 `amount >= 0`이고 이체 `kind`가 아닌 것의 `|amount × 환율|`, 수입은 `amount < 0`이고 이체가 아닌 것, 이체 유입·유출은 이체 `kind`를 부호로 나눈 것이다. 종료일(`end_date`)이 있거나 시작일이 엄격히 오늘보다 뒤(`start_date > 오늘`)인 "미래 조회"가 아니면(시작일을 날짜로 읽지 못하면 미래 조회가 아니다) 날짜가 오늘 이후인 거래를 합계에서 빼고 그 건수를 따로 센다(목록에는 보인다). 세금 우대 계정(`tax_advantaged_account_ids`)은 합계에서 뺀다. 환율은 `rate_sql(거래 통화 → 가족 통화, 거래 날짜)`이고 환율이 없으면 NULL이라 그 거래의 금액은 합에서 빠지지만 `count`에는 들어간다(R-72). 이 집합은 `excluded`와 보류 거래를 걸러내지 않는다. 결과는 필터·가족 `entries_cache_version`·환율 최신 갱신 시각·세금 우대 계정 id·접근 계정 id·오늘 날짜로 만든 키로 캐시한다. | 코드 확인 |
| R-54 | 검색 세션 상태 | 목록 요청의 필터·page·per_page를 세션에 저장하고, 쿼리 없이 목록을 다시 열면 저장된 필터로 리다이렉트한다. "clear filter"는 필터만 비운다. 이 상태는 서버 세션에 있다. | 코드 확인 |
| R-55 | 페이지 크기(`safe_per_page`) | 허용 값은 10, 20, 30, 50, 100이다. 기본값은 호출자가 넘기는 값(목록은 세션에 저장된 `per_page`)이고, 그 값이 없거나 허용 목록에 없으면 10이다. 요청의 `per_page`가 없거나 0 이하이면 기본값, 허용 목록 밖이면 가장 가까운 허용 값이다. 총 건수·페이지 계산은 pagy 라이브러리를 쓴다. | 코드 확인 |

**보류 거래 수동 병합과 중복 제안**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-56 | 중복 제안의 상태 | 제안은 보류 거래의 `extra["potential_posted_match"]`다(형식과 생성은 provider-import-adapter R-28·R-29). "제안 있음"(`has_potential_duplicate?`)은 그 값이 있고 `dismissed`가 true가 아닐 때다(키가 없으면 false로 읽는다). `confidence`가 없으면 `"medium"`으로 읽고 `"low"`이면 낮은 확신 제안이다. 거절(`dismiss`)은 write 권한이 필요하고 `dismissed`를 true로 쓴다(제안이 없으면 false를 반환). 삭제(`clear`)는 키를 지운다(웹 경로는 이 문서에서 못 찾았다, 2.1). 거절된 제안은 R-60의 수동 병합이 덮어쓸 수 있다. | 코드 확인 |
| R-57 | 병합 실행의 전제(`merge_with_duplicate!`, C-03) | 다음 중 하나라도 어긋나면 아무것도 바꾸지 않고 `false`를 돌려준다: (a) 이 거래가 보류가 아니다, (b) 제안이 없거나 거절됐다, (c) 제안의 `entry_id`로 확정 `Entry`를 못 찾는다, (d) 두 `Entry`의 계정이 다르다(계정 간 병합 금지). 확정 쪽이 보류인지·통화·금액은 여기서 검사하지 않는다. | 코드 확인 |
| R-58 | 병합의 결과(C-03) | 한 DB transaction에서 두 `Entry`와 확정 쪽 `Transaction`에 행 잠금을 잡고(순서: 보류 `Entry` → 확정 `Entry` → 확정 `Transaction`), 확정 거래(posted)를 남기고 보류 거래(pending)를 삭제한다. 확정 쪽에 반영되는 것: (1) 보류 거래에 `external_id`가 있으면 확정 `Transaction.extra["manual_merge"]` 배열에 `{merged_from_entry_id, merged_from_external_id, merged_at(ISO8601), source}`를 추가한다(옛 단일 map 형식이면 한 원소 배열로 바꿔 이어 붙인다). 이 기록은 sync가 같은 보류 거래를 다시 가져오지 않게 하는 용도다. (2) 확정 `Entry`가 보호 상태(`excluded`·`user_modified`·`import_locked`)가 아닐 때만: 보류 거래의 카테고리(있으면)를 확정 거래에, 보류 거래의 날짜를 확정 `Entry`에 쓴다. 이름·가맹점·금액은 확정 값을 그대로 둔다. (3) 보호 여부와 무관하게: 보류 거래의 메모를 확정 메모에 합친다(보류 메모가 비었으면 그대로, 확정 메모가 비었으면 보류 메모, 확정 메모의 문단들이 보류 메모의 문단 순서열을 이미 포함하면 그대로, 아니면 `"확정\n\n보류"`로 잇는다. 문단 경계는 빈 줄 둘 이상(`\n{2,}`)이고 각 문단은 앞뒤 공백을 지운 뒤 비교한다. 보류 문단열이 확정 문단열의 연속 부분열일 때만 "이미 포함"이라서 "Order 123"은 "Order 1234"에 포함된 것으로 보지 않는다. C-04). 보류 거래의 첨부 연결을 옮기고(확정 거래에 이미 있는 blob은 중복을 지움) 태그 중 없는 것을 더한다. 병합 후 첨부가 10개를 넘으면 병합을 전체 롤백하고 false다. (4) 확정 `Entry`에 `mark_user_modified!`. 보류 `Entry`는 `destroy!`. 확정 쪽 세부가 `Transaction`이 아니면(예: `Trade`) `extra`·카테고리·첨부·태그 처리는 건너뛰고 날짜(보호 아닐 때)·메모·`user_modified`만 처리한다. 동시 실행: 보류 `Entry`가 이미 사라졌으면 성공(true)으로 보고 끝낸다. 확정 `Entry`가 사라졌으면 롤백하고 false. | 코드 확인 |
| R-59 | 병합 후보 목록(`pending_duplicate_candidates`) | 이 거래가 보류일 때만 후보가 있다. 같은 계정, 같은 통화, 보류가 아닌 `Transaction` `Entry` 중 자신을 뺀 것을 날짜 내림차순·`created_at` 내림차순으로 `limit`·`offset`만큼 돌려준다. 금액 일치는 요구하지 않는다. 화면은 한 번에 10개를 보이고 11개를 가져와 다음 페이지 여부를 정하며, `offset`은 0 미만이면 0으로 고친다. 접근 가능한 계정의 `Entry`가 아니면 찾지 못해 404(`RecordNotFound`)이고, 찾았지만 `Transaction`이 아니거나 보류가 아니면 "pending only" 알림으로 목록으로 돌아간다. | 코드 확인 |
| R-60 | 사용자가 후보 하나를 골라 병합(`pending_duplicate_merges#create`) | annotate 권한이 필요하다. `posted_entry_id`가 없으면 알림. 선택한 `Entry`는 같은 계정, 같은 통화, 자신이 아니고, 보류가 아니어야 한다(아니면 "invalid" 알림). 통과하면 보류 거래의 `extra["potential_posted_match"]`를 `{entry_id, reason: "manual_match", posted_amount(문자열), confidence: "high", detected_at(오늘)}`로 덮어쓰고(기존 제안·거절 표시는 사라진다) 곧바로 R-57~R-58을 실행한다. 병합이 false를 돌려주거나 중간에 실패해도 먼저 덮어쓴 제안(`manual_match`)은 되돌려지지 않고 남는다(제안 쓰기는 병합 transaction 밖의 별도 `update!`다). 성공이면 성공 알림, false면 실패 알림, 병합 중 `RecordInvalid`·삭제 실패·교착·락 대기 초과는 실패 알림으로 처리한다. | 코드 확인 |
| R-61 | 제안 받아들이기·거절의 권한 | 목록 화면의 `merge_duplicate`(제안대로 병합)와 `dismiss_duplicate`는 write 권한(owner·full_control)이 필요하다. 후보를 골라 수동 병합하는 `pending_duplicate_merges#create`는 annotate 권한(read_write 포함)이면 된다. 같은 병합 결과를 두 권한 수준에서 얻을 수 있다. `merge_duplicate`는 레코드 없음·검증 실패·삭제 실패·교착·락 대기 초과를 실패 알림으로 처리하고 목록으로 돌아간다. | 코드 확인 |
| R-62 | 병합과 sync | 병합 경로(모델 `merge_with_duplicate!`, 두 컨트롤러)는 `sync_account_later`를 부르지 않는다. 보류 거래는 잔액 계산에서 빠지므로(sync-pipeline·account-balances) 보류 거래 삭제는 잔액에 영향이 없지만, 확정 거래의 날짜가 보류 날짜로 바뀌면 그 날짜 이후의 일별 잔액이 다음 sync까지 갱신되지 않을 수 있다(추론: 호출이 없다는 사실과 날짜가 잔액 일자에 영향을 준다는 점의 조합). | 코드 확인 (검색 범위는 2.1) / 추론(영향) |

**기타 거래 동작**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-63 | 병합·제안과 provider 경로의 경계 | 오래된 보류 거래의 자동 제외, 확정 도착 시 보류 거래 claim, 제안 생성은 provider-import-adapter R-18~R-29가 갖는다. 이 문서의 수동 병합과 달리 그쪽은 자동 `excluded`·claim이다. | 코드 확인 |
| R-64 | 거래를 매매로 변환(`convert_to_trade`) | 계정이 매매를 지원해야 하고(`supports_trades?`: 투자 계정이거나, 암호화폐 계정이면서 그 accountable의 `supports_trades?`가 참일 때) write 권한이 필요하다. 원본이 이미 `excluded`면 거부한다. 종목은 요청에서 정한다(기존 보유 종목 id, 또는 `__custom__`+티커, 또는 `SYMBOL|거래소|provider` 형식의 combobox 값). 종목 해석은 DB 락을 잡기 전에 하고, 락 안에서 `Entry`를 다시 읽어 `excluded`를 재확인한다. `qty`·`price` 중 하나만 있으면 다른 하나를 `|amount|`로 계산한다(qty = `|amount| / price`를 소수 6자리, price = `|amount| / qty`를 소수 4자리로 반올림). `qty`는 절댓값으로 쓰고 `price`는 0 이하(음수 포함)이면 거부한다. 둘 다 없으면 거부한다. 요청의 `trade_name`이 빈 문자열이어도 이름으로 그대로 쓰여(`nil`일 때만 생성 이름) 이름 검증이 실패한다. 매도 여부: `investment_activity_label`이 `Sell`이거나(라벨이 없고 `amount < 0`)이다. 새 `Trade` `Entry`: 같은 계정·날짜·통화, `qty`는 매수 양수·매도 음수, `amount = ±(qty × price)`(매도는 음수), 이름은 요청값 또는 생성 이름, 메모에 원본 이름·날짜를 적고, `user_modified`+속성 잠금을 건다. 원본 거래는 삭제하지 않고 `excluded = true`로 바꾼다(소프트 삭제). 이 경로는 `sync_account_later`를 부르지 않는다(R-70). 실패는 알림으로 돌아간다. | 코드 확인 |
| R-65 | 거래 복제(`new`의 `duplicate_entry_id`) | 접근 가능한 계정의 `Transaction`일 때만 원본에서 이름, `|amount|`, 통화, 메모, 카테고리, 가맹점, 태그를 새 거래 폼에 채우고, `nature`는 원본 부호로(음수면 `inflow`) 정한다. 계정은 원본의 것이 기본이다. 폼 채우기일 뿐 저장은 R-04를 탄다. | 코드 확인 |
| R-66 | `Entry#classification`과 예정(scheduled) 거래 | `classification`은 `amount < 0`이면 `income`, 아니면(0 포함) `expense`다. `date`가 오늘보다 뒤인 `Entry`는 예정 거래(`scheduled?`)다. 예정 거래는 잔액 계산에서 제외되고 날짜가 오면 일반 거래가 된다(R-71). | 코드 확인 |
| R-67 | 이름 제안(`name_suggestions`) | 입력이 3자 이상이면 접근 가능한 계정의 거래 이름 중 입력을 부분 포함(ILIKE)하는 것을 사용 횟수 내림차순으로 최대 8개 돌려주고, 이름마다 그 이름에서 가장 많이 쓴 카테고리를 붙인다. "Unknown" 계열 대체 이름(지원 로캘마다의 번역)은 제외한다. 입력이 3자 미만이면 가족 설정 `auto_generate_transaction_names`가 켜진 경우에만 최근 200건에서 뽑은 최근 이름 최대 20개 중 입력을 포함하는 것을 돌려준다(꺼져 있으면 빈 목록). | 코드 확인 |
| R-68 | 권한 4단계 | 계정에 대한 권한은 `owner`(계정 소유자), `full_control`·`read_write`·`read_only`(공유 `AccountShare`의 값) 중 하나이거나 없음이다. write = owner·full_control. annotate = owner·full_control·read_write. 거래를 찾는 모든 경로는 사용자가 접근 가능한(소유 또는 공유받은) 계정의 것만 찾는다(read_only 포함, 없으면 404). 필요한 권한이 없으면 "not authorized" 알림(HTML·turbo는 리다이렉트, JSON은 403)이다. 권한별로 쓰는 연산은 R-09, R-13, R-15, R-17, R-20, R-21, R-29, R-31, R-39~R-40, R-60~R-61, R-64에 있다. 새 계정을 만들 때 `auto_share_with_family!`가 소유자를 뺀 가족 구성원마다 공유를 만든다(역할이 `guest`면 `read_only`, 그 밖은 `read_write`). 계정 공유 모델은 별도 스펙이 없다. | 코드 확인 |
| R-69 | API v1 거래 경로의 차이(행 17에서 다룰 내용의 요약, 거래 `create`·`update`·`destroy`와 분할만) | (a) `user_modified`는 요청이 `user_modified`를 true로 보낼 때만 켠다(웹은 항상 켠다). `lock_saved_attributes!`는 항상 한다. (b) 권한 확인이 엔드포인트마다 다르다. `create`는 `writable_by`(owner·full_control) 계정만 찾는다. `update`·`destroy`는 `Account.accessible_by`로 거래를 찾을 뿐(`load_accessible_transaction`) 쓰기·주석 권한 호출이 없어서 read_only나 read_write 공유 사용자도 API로 거래를 수정·삭제할 수 있다(`ensure_write_scope`는 API 키의 쓰기 범위 확인이고 계정 권한이 아니다). 분할 API의 create·update·destroy는 `ensure_account_write_permission`으로 owner·full_control을 요구한다(403). (c) `nature`: `income`·`inflow`는 `−|amount|`, `expense`·`outflow`는 `+|amount|`, 그 밖에는 입력값이다(웹은 `inflow`만 부호를 바꾸고 `|amount|`를 쓰지 않는다). (d) 통화는 생략하면 가족 통화다. (e) 알 수 없는 category·merchant·tag id는 조용히 버리지 않고 422로 거부한다. (f) 분할 자식은 수정·삭제를 거부하고, 분할 원본의 금액·날짜·`nature` 변경도 거부한다. (g) `external_id`+`source`를 idempotency 용도로 쓴다. `source`만 보내면 거부하고, `external_id`만 보내면 `source`가 `"api"`로 채워져 그 `Entry`는 `linked?`(provider 연동 거래처럼 보임)가 된다. 같은 `(external_id, source)`가 있으면 새로 만들지 않고 기존 `Entry`를 200으로, 새로 만들면 201로 돌려준다(기존 `Entry`의 세부가 `Transaction`이 아니면 422). 금액은 `to_f`로 읽는다. 생성 후 호출 순서는 `lock_saved_attributes!` → (요청 시) `mark_user_modified!` → `sync_account_later`이고 웹은 `sync_account_later`가 먼저다. 수정은 필요할 때 `sync_account_later`가 `lock_saved_attributes!`보다 먼저다. (h) 분할 입력은 원본과 같은 부호의 금액이다(R-24와 반대). (i) 분할 API 입력: `splits`는 비어 있지 않은 배열이어야 하고(웹은 R-23의 경우 비어도 통과할 수 있다), 줄의 `name`이 비면 원본 이름을 쓰고, 알 수 없는 category·merchant·tag id는 조용히 버리지 않고 422이며, 금액은 소수 4자리로 반올림한 뒤 절댓값이 1e15 미만이어야 하고, 이미 분할돼 있으면 `create`는 422, 분할이 없는 거래의 `update`·`destroy`는 404 "not split"이다. 자식 id로 접근하면 부모로 올라가 처리한다. | 코드 확인 (api/v1 거래·분할 컨트롤러 일부만 읽음, 2.1) |

**sync 호출 경계와 예정 거래, 환산 실패**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-70 | `Entry#sync_account_later`와 호출 지점(C-10) | 이 메서드는 계정의 `sync_later(window_start_date: D)`를 부른다. `D`는 `Entry`가 로드된 뒤 거친 가장 이른 날짜(`@earliest_saved_date`, 날짜가 바뀐 모든 저장에서의 변경 전 날짜의 최솟값), 마지막 저장의 변경 전 날짜(`date_previously_was`), 현재 날짜 중 가장 이른 값이다(옛 날짜 위치에서 다시 계산하려는 목적이다). 삭제된 `Entry`는 `D`가 nil이라 창이 없는 전체 재계산이다. 날짜가 미래이고 삭제되지 않았으면 그 날짜 00:05(가족 시간대)에 sync를 거는 지연 job(`EntryScheduledSyncJob`)도 예약한다. `sync_later`가 새 Sync를 만들지 합칠지는 sync-pipeline R-05다. 호출하는 곳: 생성(항상), 수정(R-12가 true일 때), 단건 삭제, 분할·고치기·해제, 일괄 삭제(영향 계정마다 창 없이), 일괄 수정(날짜가 바뀐 계정마다 가장 이른 날짜로). 호출하지 않는 곳: 태그 수정, 메모·카테고리·가맹점·이름만 바꾼 수정, 대조 상태 변경, 첨부, 병합(R-62), 매매 변환(R-64), 분류 wizard의 카테고리 확정(날짜가 안 바뀌므로 R-34 규칙대로 없음). | 코드 확인 (호출 목록은 `grep -rn "sync_account_later" app --include=*.rb`, 2.1) |
| R-71 | 미래 날짜(예정) 거래 | `date > 오늘`인 `Entry`는 예정이다. 잔액 계산(`entries_scope`)은 날짜가 오늘 이하인 것만 쓰므로 예정 거래는 날짜가 올 때까지 잔액에 들어가지 않는다. 날짜가 오는 날 지연 job이 계정을 sync해서 반영한다. 거래 목록에는 보이고 검색 합계에서는 R-53대로 빠진다. 예정 거래를 통계에 쓰지 않는 용도의 범위 `excluding_scheduled`(`date <= 오늘`)가 있다. | 코드 확인 |
| R-72 | 이 스펙의 경로가 환산 실패를 만났을 때 | (a) 검색 합계: 환율이 없는 거래는 금액이 합에서 빠지고(NULL) 건수에는 포함된다(항목 제외, 1:1이나 0이 아니다). (b) 환율 조회 엔드포인트: 환율이 없으면 404 오류이고 1.0으로 대신하지 않는다(통화가 같을 때만 1.0). (c) 거래별 `exchange_rate`: 숫자가 아니거나 0 이하면 저장을 거부한다(R-07). (d) 금액 필터·병합 후보·분할 합계는 환산을 하지 않고 원래 통화 금액을 쓴다(통화가 다른 거래끼리는 병합 후보가 되지 못한다, R-59). (e) 잔액 계산에서의 환산 실패(항목 제외, 보유 1:1)는 money-currency-rules R-40·R-42다. 이 문서의 경로는 NULL로 두는 방식 하나(검색 합계)와 오류로 알리는 방식(환율 조회, 검증)만 쓴다. | 코드 확인 |

**추가 규칙**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-73 | 카테고리 선택 전용 엔드포인트(`PATCH /transactions/:transaction_id/category`, `Entry` id) | annotate 권한이 필요하다. 이체 입금 다리(R-10)면 본문 없이 422다. 아니면 `entry_params`(`entryable_type`, entryable의 `id`·`category_id`)로 `update!`하고, 카테고리 사용 기록(R-11 (2))과 규칙 안내 판정을 한 뒤 `Transaction`과 `Entry`의 `lock_saved_attributes!`를 실행한다. R-11과 달리 `mark_user_modified!`와 `sync_account_later`를 부르지 않는다(카테고리는 R-12의 비영향 속성이라 sync가 필요 없다는 이유로 보이지만 이는 추론이다. `user_modified`가 켜지지 않아도 바뀐 `category_id`는 잠긴다). 응답은 목록 행·메뉴를 다시 그린다. | 코드 확인 |
| R-74 | 화면(UI)에서만 걸리고 서버는 막지 않는 제약 | 거래 상세 화면은 (a) 분할 자식은 이름 입력을, (b) `linked?`(`external_id`가 있음) `Entry`이거나 분할 원본·자식이면 날짜·금액·통화·`nature` 입력을, (c) 권한이 없으면 해당 입력을 `disabled`로 그리고, 분할 자식에는 삭제 버튼을 그리지 않으며, 이체 거래에는 금액·`nature` 입력을 그리지 않는다. 서버의 웹 `update`·`destroy`에는 이 제약에 해당하는 검사가 없다(분할 자식의 개별 삭제는 R-25 (b)의 모델 콜백이 막고, 분할 원본의 금액·날짜 수정과 `linked?` 거래의 금액 수정은 막히지 않는다). 그래서 직접 요청하면 분할 원본의 금액을 바꿔 자식 합과 어긋나게 만들 수 있다(API는 R-69 (f)로 막는다). 이 규칙의 화면 쪽은 `show.html.erb`에서 읽었고 모든 partial을 읽지는 않았다. | 코드 확인 (화면 범위는 2.1) |
| R-75 | "사용자가 볼 수 있는 가맹점"(`available_merchants_for`) | 가족이 만든 가맹점, 사용자가 접근 가능한 계정의 거래에 붙은 가맹점, 최근에 "연결 해제(unlink)"된 가맹점(`FamilyMerchantAssociation`의 `recently_unlinked`)의 합집합이다. 거래 폼·분할·일괄 수정의 `merchant_id`가 이 집합에 있어야 반영된다(R-29, R-33). | 코드 확인 (`recently_unlinked`의 기간 정의는 열지 않았다) |

- 불변식:
  - 분할 원본은 자식이 있는 동안 `excluded = true`이고, 자식 `amount` 합은 분할 시점에 원본 `amount`와 같다(R-23, R-16). 분할 뒤 자식이나 원본의 금액이 따로 바뀌면 이 합이 깨질 수 있다(R-74).
  - 자식의 `date`는 부모와 같다(R-25 (a), 날짜를 바꾸는 저장 시점 검증).
  - 생성한 거래는 만든 직후부터 `user_modified = true`다(R-05). provider 경로로 들어온 거래는 이 문서의 규칙으로 보호가 켜지지 않는다.
  - 병합 뒤 같은 `external_id`의 보류 `Entry`는 존재하지 않는다(R-58).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-14, R-32 | 일괄 수정에서 카테고리와 태그를 같이 바꾸면, 태그 저장(`entry.transaction.save!`)이 변경 기록을 비워서 뒤의 `lock_saved_attributes!`가 `category_id`를 잠그지 못하는지 알 수 없다(`entry.rb:750-777`). 변경 기록은 프레임워크 동작이다. | 재구현이 같이 바꾼 카테고리를 잠글지 추측해야 한다. 안 잠기면 다음 provider sync가 카테고리를 덮을 수 있다. | 실행 가능한 환경에서 카테고리+태그 일괄 수정 후 `transactions.locked_attributes`를 본다. 이 SHA에서는 실행하지 않았다. |

- 확인 한계:
  - 프레임워크 기본 동작을 읽은 추론이다: 거래 삭제 때 첨부가 정리된다(R-20 (5), `has_many_attached`의 기본 삭제 방식), `kind` enum이 6개 밖 값에서 `ArgumentError`인지 `RecordInvalid`인지(R-18), 첨부 `content_type`을 누가 정하는지(업로드 헤더인지 내용 판별인지, R-38), 잠금 저장(R-13)이 같은 인스턴스의 변경 기록에 의존하는 점, 행 잠금(`lock!`)의 대기·교착 동작. 이 SHA에서 라이브러리 소스는 열지 않았다.
  - 뷰·Stimulus(`app/views`, `app/javascript`)는 열지 않았다. UI가 감추는 버튼과 입력 제약은 서버 규칙이 아니라서 R-ID에 넣지 않았고, 필요한 곳은 U-ID로 올렸다. 분할 화면의 부호 규칙(R-24)과 거래 상세의 비활성 입력(R-74)은 `app/views/splits/new.html.erb:17,29,67`과 컨트롤러 곱하기에서 읽었다.
  - 분할 자식을 직접 요청으로 삭제할 때의 HTTP 응답(R-25, R-74): 앱에 `RecordNotDestroyed` 처리가 없다는 것까지만 읽었고 최종 응답은 프레임워크 동작이다.
  - 이 환경에서 코드를 실행하지 않았다(레포 지침). 락 경합·동시 요청의 결과는 코드 읽기로만 확인했다.

### 1.5 필수 코드 참조

라이선스는 AGPL-3.0(overview 1절)이다. 아래 C-ID는 규칙을 옮기기 위한 위치이고 복사 여부는 별도 결정이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/transaction.rb:71-117`, `:124-128` `kind` enum, `TRANSFER_KINDS`, `BUDGET_EXCLUDED_KINDS`, `UNCATEGORIZED_EXCLUDED_KINDS`, `ACTIVITY_LABELS`, `INTERNAL_MOVEMENT_LABELS`, `PENDING_PROVIDERS` | `kind` 6값과 이체·예산 제외·미분류 제외 목록, 활동 라벨 13개, 보류 네임스페이스 10개 | R-18, R-19, R-47, R-48 |
| C-02 | `app/models/entry.rb:4`, `:561-673`, `:795-808`, `:818-836` `TRUTHY_VALUES`, `split!`, `split_once!`, `resplit!`, `unsplit_once!`, `unsplit!`, `with_split_lock`, 분할 검증 | 분할 합계 검증, 자식 필드 복사, 원본 `excluded`·`user_modified`, 해제 | R-22, R-23, R-26, R-27, R-28 |
| C-03 | `app/models/transaction.rb:500-663` `merge_with_duplicate!`, `dismiss_duplicate_suggestion!`, `clear_duplicate_suggestion!`, `pending_duplicate_candidates` | 병합 전제·상속·롤백 조건, 제안 거절·삭제, 후보 쿼리 | R-56~R-59 |
| C-04 | `app/models/transaction.rb:665-696` `carry_over_user_additions`, `attachment_count_after_merge`, `merged_notes` | 첨부·태그 이월과 메모 문단 병합 알고리즘 | R-58 |
| C-05 | `app/models/entry.rb:688-791` `bulk_update!` | 일괄 수정의 필드 처리·잠금 조건·sync 창 | R-32, R-34 |
| C-06 | `app/models/transaction/search.rb:18-144` `apply_category_filter`, `apply_type_filter`, `apply_merchant_filter`, `apply_tag_filter` | 카테고리·유형·가맹점·태그 필터 | R-47~R-49 |
| C-07 | `app/models/transaction/search.rb:147-151`, `:180-204`, `:297-404` `transactions_scope`, `look_ahead?`, 상태·ai·첨부·대조 필터 | 검색 집합 조합과 나머지 필터 | R-43, R-46, R-50, R-51, R-53 |
| C-08 | `app/models/transaction/search.rb:207-278` `totals` | 합계 SQL | R-53 |
| C-09 | `app/models/entry_search.rb:29-133` | 텍스트·날짜·금액·계정·상태 필터와 `Entry` 기준 조합 | R-44, R-45, R-52 |
| C-10 | `app/models/entry.rb:7-12`, `:378-393` `sync_account_later`, `saved_changes_affect_balances?`, `app/jobs/entry_scheduled_sync_job.rb:16-35`, `entry.rb:814-816` `track_earliest_saved_date` | sync 창 계산, 영향 판정, 예정 거래 지연 job | R-12, R-70, R-71 |
| C-11 | `db/schema.rb:709-751` `entries`, `:2893-2913` `transactions`, `:2764-2772` `taggings` | 컬럼·기본값·unique·check 제약 | 1.3 데이터, R-02, R-06 |
| C-12 | `app/controllers/transactions_controller.rb:668-685`, `:802-824` `entry_params`, `permitted_entry_params` | 허용 필드, `nature` 부호 처리, 권한별 허용 필드 | R-04, R-16 |
| C-13 | `app/models/concerns/enrichable.rb:149-169`, `:246-248`, `app/models/entry.rb:363-366`, `:480-559` | 잠금 확인·잠그기·풀기, 보호 판정, `unlock_for_sync!` | R-13 |
| C-14 | `app/models/transaction.rb:33-67` `exchange_rate`, `exchange_rate=`, 검증 | 거래별 환율 저장과 검증 | R-07 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않았다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-05 | 수동 계정(KRW)에 `name: "점심"`, `amount: 12000`, `currency: KRW`, `nature: outflow`, `date: 오늘`을 만든다. | `Entry.amount = 12000`, `user_modified = true`, `locked_attributes`에 `name`·`amount`·`date`·`currency` 등이 있고 `sync_later(window_start_date: 오늘)`가 한 번 호출된다. |
| T-02 | R-04 | 같은 요청에서 `nature: inflow`, `amount: 12000`. | `Entry.amount = -12000`. `nature: outflow`이고 `amount: -500`이면 `-500` 그대로다. |
| T-03 | R-06 | 같은 UUID `idempotency_key`로 같은 계정에 두 번 만든다. | `Entry`는 하나뿐이고 두 번째 응답도 성공이다. 키가 UUID 형식이 아니면 두 번 만들면 `Entry`가 둘이다. |
| T-04 | R-12, R-07 | 거래 상세 폼으로(요청에 `exchange_rate` 키 없이) 거래의 이름만 바꾼다. 이어서 금액만 바꾼다. 같은 이름 수정을 `entryable_attributes[exchange_rate]=""`를 포함해 보낸다. | 첫 수정은 sync를 부르지 않고 두 번째는 부른다. 둘 다 `user_modified = true`이고 바뀐 속성이 잠긴다. 세 번째는 `extra`가 바뀌어 sync가 불리고 `extra`가 잠긴다. |
| T-05 | R-23, R-24 | 지출 거래 `amount = 10000`을 웹 분할 화면에서 6000, 4000(화면 입력은 `−6000`, `−4000`)으로 나눈다. 합이 맞지 않는 `−6000`, `−3000`이면. | 첫 경우 자식 두 개(6000, 4000)와 원본 `excluded = true`, `user_modified = true`. 둘째 경우 합 오류로 아무것도 저장되지 않는다. |
| T-06 | R-22 | 보류 거래나 `kind = funds_movement`인 거래를 분할한다. | "not splittable"로 거부된다. |
| T-07 | R-27 | 분할된 원본을 해제한다. | 자식이 모두 삭제되고 원본 `excluded = false`, `user_modified = true`로 남는다. |
| T-08 | R-32, R-33 | `category_id`만 채우고 `notes`는 빈 문자열로 선택한 5건에 일괄 수정을 한다. 그중 하나는 분할 원본이다. | 분할 원본을 뺀 4건의 카테고리가 바뀌고 메모는 그대로이며 4건이 `user_modified`가 된다. 가족 밖 `category_id`면 아무것도 바뀌지 않지만 응답 문구는 "0 transactions updated"다. |
| T-09 | R-34 | 두 거래의 `date`를 일괄로 3월 5일 → 3월 1일, 3월 10일 → 3월 1일로 바꾼다(같은 계정). | `sync_later`가 계정에 한 번, `window_start_date = 3월 1일`로 호출된다. 카테고리만 바꾸면 호출되지 않는다. |
| T-10 | R-20, R-70 | 거래 하나를 삭제한다. | 삭제 후 `sync_later(window_start_date: nil)`이 호출된다. 이체의 한쪽 다리를 삭제하면 반대쪽 다리의 `kind`가 `standard`로 돌아간다. |
| T-11 | R-21 | 선택한 `entry_ids`에 분할 자식과 읽기 전용 계정의 거래가 섞여 있다. | 두 종류는 조용히 남고 나머지만 삭제되며 알림은 삭제 건수다. |
| T-12 | R-38, R-39 | 거래에 이미 9개가 있는데 3개를 올린다. 또는 11MB 파일, `text/plain` 파일을 올린다. | 첫 경우 3개 모두 거부된다. 나머지는 오류 알림이 나오고 거래에 첨부가 늘지 않는다(저장소에서의 파일 정리는 추론). |
| T-13 | R-46, R-47 | 검색 `types = ["transfer"]`와 `types = ["expense"]`. `amount = 0`이고 `kind = standard`인 거래. | 앞은 `kind`가 이체 4종인 것만, 뒤는 `amount >= 0`이고 이체가 아닌 것이다. 금액 0 거래는 지출이다. |
| T-14 | R-48 | `categories = ["Uncategorized"]`. 카테고리 없는 `standard`, `funds_movement`, `loan_payment` 거래. | `standard`와 `loan_payment` 거래만 나오고 `funds_movement`는 빠진다. |
| T-15 | R-53, R-72 | 가족 통화 KRW에 USD 거래 2건(하나는 USD→KRW 환율 행 있음, 하나는 없음)이 오늘 이전 날짜로 있다. | `count = 2`, 지출 합은 환율 있는 거래만 환산해 더한다. 미래 날짜 거래는 `end_date`가 없으면 합에서 빠진다. |
| T-16 | R-57, R-58 | 같은 계정에 보류 `P`(날짜 3/1, 카테고리 식비, `external_id = X`)와 확정 `Q`(날짜 3/3, 카테고리 없음, 보호 아님), `P`에 `Q`를 가리키는 제안이 있다. `P.merge_with_duplicate!`. | `P`는 삭제되고 `Q`가 남는다. `Q`의 날짜는 3/1, 카테고리는 식비, 이름·금액은 그대로이고 `extra.manual_merge`에 `merged_from_external_id = X` 항목이 생기며 `Q.user_modified = true`다. |
| T-17 | R-58 | 위에서 `Q`가 `user_modified`였다. | `Q`의 날짜와 카테고리는 바뀌지 않는다. `manual_merge` 기록, 메모 합치기, 첨부·태그 이월은 그대로 일어난다. |
| T-18 | R-57 | 보류가 아닌 거래에서, 또는 제안이 `dismissed: true`인 거래에서, 또는 계정이 다른 `Entry`를 가리키는 제안으로 병합을 호출한다. | 모두 `false`이고 아무것도 바뀌지 않는다. |
| T-19 | R-60 | 보류 거래에서 후보 하나를 골라 수동 병합한다(기존 제안이 `dismissed`였다). | 제안이 `manual_match`·`high`로 덮이고 곧바로 병합된다. 선택한 `Entry`가 다른 통화이거나 보류이면 "invalid" 알림으로 아무것도 바뀌지 않는다. |
| T-20 | R-64 | 투자 계정에서 거래(`amount = 100000`)를 `qty = 10`, `price` 없음으로 매매 변환한다. | `price = 10000`, 새 `Trade` `Entry`(`amount = 100000`, 매수), 원본은 `excluded = true`. sync는 호출되지 않는다. |
| T-21 | R-69 | read_only 공유 사용자가 API로 다른 사람 계정의 거래를 `PATCH`·`DELETE`한다. 같은 사용자가 `POST`로 그 계정에 만든다. 분할 API `POST`를 보낸다. | `PATCH`·`DELETE`는 성공한다(원본 동작). `POST` 생성은 계정을 못 찾아 404이고 분할은 403이다. |
| T-22 | R-73 | read_write 공유 사용자가 카테고리 선택 엔드포인트로 카테고리를 바꾼다. | 카테고리가 바뀌고 `locked_attributes`에 `category_id`가 들어가지만 `user_modified`는 변하지 않고 sync는 불리지 않는다. 확정 이체의 입금 다리면 422다. |
| T-23 | R-60 | 수동 병합에서 선택한 확정 `Entry`로 병합이 false가 된다(예: 첨부가 합쳐서 10개를 넘음). | 보류 거래의 `potential_posted_match`가 `manual_match`·`high`로 바뀐 채 남고 두 `Entry`는 그대로다. |
| T-24 | R-23 | 원본 `amount = 0`인 거래를 `splits = []`로 분할한다. 합이 맞는 `[6000, -2000, 0]`을 `amount = 4000`인 거래에 보낸다. | 첫 경우 자식 없이 원본만 `excluded = true`가 된다. 둘째는 줄의 부호·0과 무관하게 합이 4000이므로 허용된다. API는 빈 배열을 422로 거부한다. |
| T-25 | R-55 | `per_page`를 0, 15, 70, 500으로 보낸다(저장된 값 없음). | 각각 10, 10(15는 10·20과 거리가 같아 목록에서 앞선 10), 50, 100이다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

모든 근거는 `repos/sure@1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a`다. 줄 범위는 문서 작성 때 열어 읽은 곳이다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | `app/models/entryable.rb:1-31`, `entry.rb:33-34` | `delegated_type`과 `has_one :entry, dependent: :destroy`(entryable.rb:13) 양방향 삭제를 읽었다. |
| R-02 | `entry.rb:62-68`, `:684-686`, `db/schema.rb:709-751` (C-11) | `comparison greater_than`이 엄격 부등호라는 점은 코드 읽기. |
| R-03 | `entry.rb:70-84`, `:843-854`; `transactions_controller.rb:745-747`; `db/schema.rb:854` | `Category#display_name`과 가맹점 이름 결합 형식은 `set_default_name`에서 읽었다. 번역 이름 목록은 열지 않았다. |
| R-04 | `transactions_controller.rb:121-133`, `:668-685`(C-12); `concerns/entryable_resource.rb:15-24`; `account_authorizable.rb:10-29` | 계정 `nil`이면 `Current.family.entries.new(entry_params)`로 검증만 하고 422. |
| R-05 | `transactions_controller.rb:147-155` | 순서는 코드 줄 순서. |
| R-06 | `transactions_controller.rb:135-145`, `:718-720`, `app/views/transactions/_form.html.erb:13-20`, `:161-172`, `:687-720`; `db/schema.rb:709-751`(`index_entries_on_account_and_idempotency_key`) | 형식 정규식은 `:710`. `Transfer` 해제 때 키를 비우는 부분은 `transfer.rb:236-262`(범위 밖). |
| R-07 | C-14 `transaction.rb:33-67`; money-currency-rules R-22; `app/views/transactions/_form.html.erb:73`(필드 있음), `show.html.erb`에 `exchange_rate` 필드 없음(`grep -rn exchange_rate app/views/transactions/*.erb`) | `exchange_rate=`의 빈 값 병합은 `transaction.rb:38-40`. 새 폼이 키를 항상 보낸다는 것은 필드가 항상 렌더되는지 폼 조건을 모두 확인하지는 않았다. |
| R-08 | `transactions_controller.rb:541-563` | `find_or_fetch_rate`의 내부(제공자 호출)는 money-currency-rules 범위. |
| R-09 | `transactions_controller.rb:174-191`, `:802-824`; `entryable_resource.rb:47-52`; `account_share.rb:8-13` | "컨트롤러에 권한 확인이 없다"는 `update` 본문과 `before_action`(`entryable_resource.rb:5`, `transactions_controller.rb:5-7`)에 `require_account_permission!` 호출이 없음을 읽은 것이다. `transactions_controller.rb` 전체를 읽었고 `require_account_permission!`는 `create`·`update_tags`·`merge_duplicate`·`dismiss_duplicate`·`convert_to_trade`·`create_trade_from_transaction`·`unlock`·`reconcile`·`mark_as_recurring`에만 있고 `update`에는 없다(검색 명령이 아니라 읽기, 범위는 이 파일 한 개). 라우트 단의 제한은 `config/routes.rb`를 열지 않았다. |
| R-10 | `transactions_controller.rb:817-821`; `transaction.rb:386-400` | 전칭 부분 검색은 R-36 줄 참조. |
| R-11 | `transactions_controller.rb:174-198`, `:655-666` | 규칙 안내(`needs_rule_notification?`)는 행 10. |
| R-12 | C-10 `entry.rb:7-12`, `:386-393`; `transactions_controller.rb:176` | 태그 변경이 속성을 안 바꾼다는 판단은 `Transaction.tag_ids=`가 `taggings`를 쓰는 가상 속성임을 읽은 추론. |
| R-13 | C-13; `entry.rb:363-366`, `:554-559`; `transactions_controller.rb:433-440` | `lock_saved_attributes!`가 `lock_attr!`(내부 `update!`)를 반복해도 이미 계산된 이름 목록으로 돌기 때문에 안전하다는 점은 읽은 해석. 세부의 `saved_changes`가 `Entry`의 `update!`로 지워지지 않는다는 점은 추론이다. |
| R-14 | `transactions_controller.rb:153`, `:190`, `:257`; `entry.rb:770` | |
| R-15 | `transactions_controller.rb:243-262`; `transaction.rb:425-434` | |
| R-16 | `entry.rb:818-822`, `:647`, `:671`; `balance/sync_cache.rb:143-146`; 통계 `income_statement/family_stats.rb:48`, `category_stats.rb:54`, `daily_expense_totals.rb:63`, `totals.rb:74,99`, `spending_comparison.rb:50`, `goal.rb:285`, `recurring_transaction/matcher.rb:267`, `account/reconciliation_indicator.rb:16-21` | 전칭 부분 "잔액 계산에서는 빠지지 않는다": `grep -rn "excluded" app/models/balance app/models/balance_sheet app/models/account`의 결과에서 `Balance` 계열에 `excluded` 필터가 없었고 `entries_scope`(`sync_cache.rb:144`)는 `excluding_pending.excluding_split_parents.where(date: ..오늘)`뿐이다. 다른 잔액 경로(예: `ReverseCalculator` 자체의 쿼리)는 열지 않았다. "(b) 목록" 은 `grep -rn "excluded: false\|excluded = false" app/models`의 결과를 모은 것이라 전수가 아니다. |
| R-17 | `transactions_controller.rb:446-482`; `entry.rb:49-60`, `:658-662`; `db/schema.rb:709-751`(check 제약); `bulk_updates_controller.rb:5-20`; `entry.rb:746-748` | 명세서 대조(`reconciled_at`)는 `entry.rb:24-26`, `:457-474`에서 이름만 확인. |
| R-18 | C-01 `transaction.rb:71-117` | 6개 밖 값의 오류는 enum 동작 추론. provider 쪽 `kind` 규칙은 provider-import-adapter R-39. |
| R-19 | `transaction.rb:106-110`; `transactions_controller.rb:671` | |
| R-20 | `entryable_resource.rb:33-39`; `transfer.rb:241-267`; `transaction/transferable.rb:12-17`; `entry.rb:33`, `:378-384`; `transaction.rb:8`, `app/models/transaction/transferable.rb:3-14`; `transfer.rb:5`, `:22`, `:236-262`; `db/schema.rb:3180` | 첨부 정리는 `transaction.rb:14`의 `has_many_attached` 기본 동작 추론. 반대 다리 `kind` 되돌림은 `transfer.rb`의 `release_transactions`(행 3 범위)를 읽은 것. |
| R-21 | `transactions/bulk_deletions_controller.rb:1-22` | 전체 transaction 코드가 없다는 부재 주장: 이 파일 22줄 전체를 읽었다. `destroy_by`의 레코드별 처리는 프레임워크 동작 추론. |
| R-22 | `transaction/splittable.rb:1-7`; `entry.rb:571-578`; `splits_controller.rb:9-24` | |
| R-23 | C-02 `entry.rb:607-652`, `:14`, `:4` | "줄 수 최솟값 검증이 없다"는 `split!`와 `Entry` 검증에 그런 코드가 없다는 읽기(`entry.rb` 전체를 읽음). |
| R-24 | `splits_controller.rb:107-121`; `app/views/splits/new.html.erb:17,29,67`; `edit.html.erb:17,30,42`; `api/v1/splits_controller.rb:160`(부호 주석), `:192-223` | API가 "same sign as parent"라고 주석한 곳(`api/v1/splits_controller.rb:160`)과 곱하기 없음(`:204-215`)을 확인. |
| R-25 | `entry.rb:818-836`, `:86`, `:744`; `bulk_deletions_controller.rb:6-8`; `entryable_resource.rb:33-39` | 웹 단건 삭제 응답은 확인 한계 참조. |
| R-26 | `entry.rb:580-591`; `splits_controller.rb:40-58` | |
| R-27 | `entry.rb:593-601`, `:664-673`; `splits_controller.rb:63-77` | |
| R-28 | `entry.rb:795-808` | |
| R-29 | `splits_controller.rb:5-7`, `:82-95`, `:107-121`; `entry/split_references.rb:1-40` | `new`·`edit`는 `require_split_write_permission!`의 대상이 아님(`before_action ... only: %i[create update destroy]`). |
| R-30 | `entry.rb:144-150`, `balance/sync_cache.rb:144`; `transaction/search.rb:183` | |
| R-31 | `transactions/bulk_updates_controller.rb:22-37`; `current.rb:36-41`; `account.rb:141-163` | |
| R-32 | C-05 `entry.rb:688-791` | 코드 읽기. |
| R-33 | `bulk_updates_controller.rb:75-101`, `:45` | |
| R-34 | `entry.rb:758-762`, `:785-788`; `jobs/entry_scheduled_sync_job.rb:30-35` | |
| R-35 | `bulk_updates_controller.rb:5-20`, `:38-60` | |
| R-36 | `grep -rn "category_set_on_transfer_outflow\|category_editable" app --include=*.rb`(범위: `app/`의 `.rb`) → `transactions_controller.rb:819`, `transaction_categories_controller.rb:9`, `accounts_controller.rb:153`, `helpers/categories_helper.rb:23,27`, `transaction.rb` 정의뿐. 뷰(`.erb`)에서의 사용은 이 검색에 포함하지 않았다. | `bulk_update!`(`entry.rb:688-791`)에 그 호출이 없음을 읽었다. |
| R-37 | `transactions/categorizes_controller.rb:24-40`, `:94-103`; `entry.rb:183-190`; `transaction/search.rb:18-63`, `:306-312` | wizard 묶음·규칙 생성은 행 10. 검색 쪽이 `excluded`를 거르지 않는다는 것은 `apply_category_filter`와 `transactions_scope`를 읽은 결과. |
| R-38 | `transaction.rb:11-26`, `:698-716` | |
| R-39 | `transaction_attachments_controller.rb:11-66`, `:101-106` | purge가 저장소에 미치는 효과는 Active Storage 동작이라 추론. |
| R-40 | `transaction_attachments_controller.rb:6-9`, `:68-88`, `:90-105` | |
| R-41 | `transaction/search.rb:345-364`; `transaction.rb:665-683` | |
| R-42 | `transactions_controller.rb:828-853`; `transaction/search.rb:146-151` | |
| R-43 | C-07 `search.rb:180-204`; `entry.rb:102-109`; `transactions_controller.rb:23-53`(정렬 `reverse_chronological`은 `:28-30`) | 정렬이 `transactions_scope`가 아니라 `index`에서 붙는다는 것은 두 곳을 읽은 결과. |
| R-44, R-45 | C-09 `entry_search.rb:29-63` | |
| R-46 | `transaction/search.rb:367-382`, `entry_search.rb:74-106` | 보류 판정은 provider-import-adapter R-30. |
| R-47~R-49 | C-06 `search.rb:18-144` | |
| R-50 | `search.rb:318-341` | |
| R-51 | `search.rb:345-364`, `:394-404` | |
| R-52 | `entry_search.rb:109-139`; 호출처 `grep -rn "EntrySearch\|Entry.search\|\.search(" app --include=*.rb`(범위 `app/`의 `.rb`) → `accounts_controller.rb:111`, `concerns/accountable_resource.rb:29`, `entry.rb:679-681`. `.search(`의 다른 의미(벡터 검색 등)는 걸러서 읽었다. | 다른 확장자·동적 호출은 놓칠 수 있다. |
| R-53 | C-08 `search.rb:207-278`, `:281-292`, `:297-303`(`look_ahead?`); `exchange_rate.rb`는 money-currency-rules R-26 | `excluded`·보류를 거르지 않는다는 부재 주장은 `transactions_scope`(`search.rb:180-204`)와 `totals`의 `where`를 읽은 것(`.excluding_pending`·`excluded` 조건 없음). |
| R-54 | `transactions_controller.rb:106-119`, `:855-881` | |
| R-55 | `app/controllers/concerns/safe_pagination.rb:7-17`; `transactions_controller.rb:53`, `:855-873` | 코드 확인. 동률 처리는 `min_by`가 첫 최소를 돌려준다는 언어 동작(추론). |
| R-56 | C-03 `transaction.rb:468-498`, `:623-643`; `transactions_controller.rb:307-323` | `clear_duplicate_suggestion!`의 호출처는 검색하지 않았다. 읽은 컨트롤러(`transactions_controller`, `pending_duplicate_merges_controller`)에는 호출이 없다는 뜻이다. |
| R-57 | `transaction.rb:503-516` | |
| R-58 | C-03 `transaction.rb:518-621`; C-04 `:665-696` | |
| R-59 | `transaction.rb:645-663`; `pending_duplicate_merges_controller.rb:4-17`, `:62-69` | 접근 불가가 404인 것은 `Current.accessible_entries.find`(`:63`)가 `RecordNotFound`를 낸다는 읽기와 앱의 `rescue_from RecordNotFound`(`store_location.rb:14`). |
| R-60 | `pending_duplicate_merges_controller.rb:19-60`, `:71-81` | |
| R-61 | `transactions_controller.rb:287-323`; `pending_duplicate_merges_controller.rb:20` | |
| R-62 | `grep -rn "sync_account_later" app --include=*.rb`의 출력(R-70 줄)에 `transaction.rb`·`pending_duplicate_merges_controller.rb`가 없고 `transactions_controller.rb`는 `:150`(생성)·`:191`(수정)뿐이다. 두 파일은 읽어서도 `sync_later` 호출이 없음을 확인했다 | 범위: 위 3개 파일. 다른 곳에서 콜백으로 sync가 걸릴 가능성(Entry 저장 콜백 `entry.rb:87` 등)은 `after_save :track_earliest_saved_date`뿐이고 sync를 부르지 않는다. 날짜 변경이 sync 없이 남는 영향은 추론. |
| R-63 | provider-import-adapter R-18~R-29 | 링크. |
| R-64 | `transactions_controller.rb:326-431`(`:399` 이름), `:883-977`(`:957-974` qty·price); `account.rb:893-897` `supports_trades?` | accountable의 `supports_trades?` 정의는 열지 않았다(암호화폐 "exchange" 하위 종류는 `account.rb` 주석). |
| R-65 | `transactions_controller.rb:16-21`, `:621-648` | |
| R-66 | `entry.rb:359-361`, `:430-432` | |
| R-67 | `transactions_controller.rb:565-576`, `:768-797`; `transaction.rb:309-365` | |
| R-68 | `account.rb:115-163`, `:944-947`, `:957-967`; `account_authorizable.rb:10-29`; `account_share.rb:8-13`; `current.rb:31-41` | `AccountShare`의 생성·변경 규칙은 범위 밖. |
| R-69 | `api/v1/transactions_controller.rb:74-215`, `:326-382`, `:449-509`; `concerns/api/v1/transaction_lookup.rb:10-22`; `api/v1/splits_controller.rb:12-23`, `:40-100`, `:115-123`, `:160-232` | 이 두 컨트롤러의 일부(생성·수정·삭제, 분할)만 읽었다. 목록·필터·인증 범위는 읽지 않았다. (b)의 "권한 확인이 없다"는 `update`(`:141-193`)·`destroy`(`:195-212`) 본문과 `set_transaction`→`load_accessible_transaction`을 읽은 것이고, 권한 관련 검색 `grep -n "writable\|permission" api/v1/transactions_controller.rb api/v1/base_controller.rb`는 `:96`(create)만 나왔다(범위: 이 두 파일, `Api::V1::BaseController`의 `before_action`도 읽었다). |
| R-73 | `transaction_categories_controller.rb:4-24`, `:49-62`; `config/routes.rb:613-635`(`resource :category`) | 코드 확인. `Current.accessible_entries.transactions`로 `Entry` id를 받는다. |
| R-74 | `app/views/transactions/show.html.erb:50-82`, `:446-462`; `entryable_resource.rb:33-39`; `entry.rb:832-836` | 화면 범위: `show.html.erb`의 개요 폼·삭제 영역만 읽었다. 서버 검사가 없다는 부재 주장은 `TransactionsController#update`·`EntryableResource#destroy`를 읽은 범위 한정. |
| R-75 | `app/models/family.rb:404-416` `available_merchants_for` | `recently_unlinked` 정의는 열지 않았다. |
| R-70 | C-10; `grep -rn "sync_account_later" app --include=*.rb`(범위: `app/`의 `.rb`) → 거래 관련 호출처는 `transactions_controller.rb:150,191`, `concerns/entryable_resource.rb:37`, `splits_controller.rb:21,56,75`, `api/v1/transactions_controller.rb:113,169,202`, `api/v1/splits_controller.rb:48,76,91`, `assistant/function/{create,update,delete}_transaction.rb`, `rule/action_executor/split_transaction.rb:82`, `transfer*.rb` 등. 일괄 삭제(`bulk_deletions_controller.rb:10`)와 일괄 수정(`entry.rb:785-788`)은 `sync_later`를 직접 부른다. | 제외한 호출처(provider, 규칙, AI 도구, 이체)는 이 스펙 범위 밖이다. 동적 호출·다른 확장자는 놓칠 수 있다. |
| R-71 | `entry.rb:155`, `:430-432`; `balance/sync_cache.rb:94-146`; `search.rb:219-233`; `jobs/entry_scheduled_sync_job.rb:16-25` | |
| R-72 | `search.rb:239-266`, `transactions_controller.rb:541-563`, `transaction.rb:33-67`; money-currency-rules R-21~R-27, R-40~R-42 | 이 문서 경로의 환산 호출을 읽은 범위 내에서의 서술이다. |
| T-01~T-20 | 모두 위 R-ID의 근거에서 손으로 따라가 도출했다. 실행하지 않았다. | |

### 2.2 코드 읽는 순서

1. `app/controllers/transactions_controller.rb`의 `create`·`update`(R-04~R-12), `entry.rb`의 `lock_saved_attributes!`·`mark_user_modified!`·`sync_account_later`.
2. `app/models/entry.rb:561-673`(분할)와 `:688-791`(일괄 수정).
3. `app/models/transaction.rb:500-696`(병합), `pending_duplicate_merges_controller.rb`.
4. `transaction/search.rb`와 `entry_search.rb`(검색).
5. 첨부(`transaction.rb:698-716`, `transaction_attachments_controller.rb`).

### 2.4 검토 기록

`draft`다(미결정 U-01이 남아 `ready` 조건 미충족, 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-01~R-72 전부, C-ID 전부, T-01~T-20 중 12개를 다시 따라갔다. 일치 약 62개, 불일치 10건, 누락 16건이 나왔다. 작성자가 코드로 다시 확인해 전부 반영했고 R-73~R-75, T-21~T-25를 추가했다.
- **메인 표본 점검**: R-16(`excluded`는 잔액 계산 범위에 영향 없음, `balance/sync_cache.rb:143`), R-69(b)(API `update`·`destroy`는 `accessible_by`로 찾기만 하고 쓰기 권한을 보지 않음, `api/v1/transactions_controller.rb:96`과 `transaction_lookup.rb:10-22`), R-55(`safe_per_page` 허용 [10, 20, 30, 50, 100], `safe_pagination.rb:7-17`)를 원본에서 직접 확인했다.
- **대조하지 못한 것**: R-32·R-14(일괄 수정에서 카테고리와 태그를 함께 바꿀 때 잠금, U-01), R-13, R-18, R-38, R-20(5)의 프레임워크 동작, R-46·R-56의 보류 판정(`provider-import-adapter` 소관), R-69의 `index`·필터·인증 범위, 뷰·Stimulus의 입력 제약(`show.html.erb`의 disabled와 삭제 버튼만 읽음).

## 적용 메모

아래는 원본과 다르게 할 후보이며 사용자 결정 전이다. 원본의 미결정(U-01)을 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-09 | read_only 권한 사용자의 수정 요청을 거부한다(`update`에 write·annotate 권한 확인을 둔다). | 원본은 빈 파라미터로 성공하고 `user_modified`를 켠다. 재구현에서는 의미 없는 상태 변경이다. | R-09·R-11 결과와 T-04 사전 조건이 바뀐다. |
| R-62, R-64 | 병합으로 날짜가 바뀌었거나 매매 변환을 했으면 `sync_account_later`를 부른다. | 원본은 부르지 않아 다음 sync까지 일별 잔액이 어긋날 수 있다(추론). | R-70의 호출하지 않는 곳 목록이 줄고 T-16·T-20에 sync 기대가 추가된다. |
| R-04 | 금액 부호를 `nature` 하나로 일관되게 정한다(`outflow`는 `+|amount|`, `inflow`는 `−|amount|`). 웹과 API의 부호 규칙을 통일한다. | 원본은 웹은 `inflow`만 뒤집고 API는 둘 다 절댓값을 써서 같은 입력의 결과가 다르다(R-69 (c)). | R-04, R-69, T-02. |
| R-24 | 분할 입력의 부호를 `Entry` 부호 규약과 같게 한다(화면 변환은 UI에서). | 웹은 곱하기 −1, API는 그대로라서 클라이언트마다 다르다. | R-24, T-05. |
| R-03, R-67 | 한글 이름·적요: `ILIKE` 검색과 이름 제안은 유니코드 부분 일치로 동작하지만 정규화(NFC/NFD)는 하지 않으므로, 입력 시 한 형식으로 정규화해서 저장한다. 이름이 비어 있으면 대체 이름("Unknown")을 쓸지는 정책 결정이 필요하다(원본은 자동 생성 설정이 꺼져 있으면 저장을 거부한다). | 한글은 조합형·분해형이 섞이면 같은 글자가 다르게 비교된다(추론). | R-44, R-67. |
| R-02, R-45 | KRW는 소수가 없으므로 `amount`를 정수로 다루고 금액 `equal` 필터의 허용 오차 0.01을 0으로 둔다. 저장 스케일 4자리는 그대로 두거나 통화별 자릿수로 줄인다. | `entries.amount`는 4자리까지 저장하고 `equal` 필터는 0.01 오차를 쓴다. KRW에는 의미가 없다. money-currency-rules R-10 참조. | R-45. |
| R-53 | 검색 합계에서 보류·`excluded` 거래를 어떻게 셀지 정한다(원본은 거르지 않는다). | 목록의 합계와 통계 화면의 합계가 달라질 수 있다. | R-53, T-15. |
| R-70 | 삭제 후 `window_start_date`를 삭제된 거래의 날짜로 줄인다(원본은 nil이라 전체 재계산). | 거래가 많으면 매번 전체를 다시 계산한다(추론: 성능). | R-20, R-70, T-10. |
