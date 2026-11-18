---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/rule.rb
  - app/models/rule/runner.rb
  - app/models/rule/condition.rb
  - app/models/rule/condition_filter.rb
  - app/models/rule/condition_filter/transaction_name.rb
  - app/models/rule/condition_filter/transaction_amount.rb
  - app/models/rule/condition_filter/transaction_type.rb
  - app/models/rule/condition_filter/transaction_tag.rb
  - app/models/rule/condition_filter/transaction_category.rb
  - app/models/rule/condition_filter/transaction_merchant.rb
  - app/models/rule/condition_filter/transaction_account.rb
  - app/models/rule/condition_filter/transaction_notes.rb
  - app/models/rule/condition_filter/transaction_details.rb
  - app/models/rule/condition_filter/transaction_additional_detail.rb
  - app/models/rule/condition_filter/unsupported.rb
  - app/models/rule/safe_regex.rb
  - app/models/rule/registry.rb
  - app/models/rule/registry/transaction_resource.rb
  - app/models/rule/action.rb
  - app/models/rule/action_executor.rb
  - app/models/rule/action_executor/set_transaction_category.rb
  - app/models/rule/action_executor/set_transaction_tags.rb
  - app/models/rule/action_executor/set_transaction_merchant.rb
  - app/models/rule/action_executor/set_transaction_name.rb
  - app/models/rule/action_executor/set_investment_activity_label.rb
  - app/models/rule/action_executor/exclude_transaction.rb
  - app/models/rule/action_executor/set_as_transfer_or_payment.rb
  - app/models/rule/action_executor/send_email_notification.rb
  - app/models/rule/action_executor/split_transaction.rb
  - app/models/rule/action_executor/fill_similar_merchants.rb
  - app/models/rule/action_executor/bayes_categorize.rb
  - app/models/rule/action_executor/auto_categorize.rb
  - app/models/rule/action_executor/auto_detect_merchants.rb
  - app/models/rule/layout.rb
  - app/models/rule_run.rb
  - app/models/rule_group.rb
  - app/models/family.rb
  - app/models/family/bayes_categorizer.rb
  - app/models/family/bayes_settings.rb
  - app/models/family/similar_matcher.rb
  - app/models/family/similar_merchant_filler.rb
  - app/models/family/auto_categorizer.rb
  - app/models/family/auto_merchant_detector.rb
  - app/models/family/ai_settings.rb
  - app/models/family/syncer.rb
  - app/models/concerns/enrichable.rb
  - app/models/entryable.rb
  - app/models/data_enrichment.rb
  - app/models/transaction.rb
  - app/models/entry.rb
  - app/models/category.rb
  - app/models/category/merger.rb
  - app/models/tag.rb
  - app/models/merchant.rb
  - app/models/family_merchant.rb
  - app/models/provider_merchant.rb
  - app/models/merchant/merger.rb
  - app/models/provider/llm_concept.rb
  - app/models/provider/classification_concept.rb
  - app/models/provider/openai.rb
  - app/models/provider/openai/auto_categorizer.rb
  - app/models/provider/openai/auto_merchant_detector.rb
  - app/models/plaid_entry/processor.rb
  - app/validators/database_text_validator.rb
  - app/jobs/apply_rules_job.rb
  - app/jobs/apply_all_rules_job.rb
  - app/jobs/rule_job.rb
  - app/jobs/bayes_categorize_job.rb
  - app/jobs/auto_categorize_job.rb
  - app/jobs/auto_detect_merchants_job.rb
  - app/jobs/clear_ai_cache_job.rb
  - lib/tasks/rules.rake
  - app/models/transaction/splittable.rb
  - app/models/plaid_account/transactions/processor.rb
  - app/models/simplefin_account/transactions/processor.rb
  - app/controllers/rules_controller.rb
  - app/controllers/settings/classifiers_controller.rb
  - app/controllers/transactions/categorizes_controller.rb
  - app/controllers/categories_controller.rb
  - app/controllers/tags_controller.rb
  - app/helpers/languages_helper.rb
  - db/schema.rb
depends:
  - ./transactions.md
  - ./provider-import-adapter.md
  - ./sync-pipeline.md
  - ./money-currency-rules.md
status: draft
---

# 거래 분류 자동화 (규칙·Bayes·LLM·가맹점 감지)와 분류 데이터

> 거래 한 건의 이름·메모·금액·종류·카테고리·가맹점·태그를 조건으로 삼는 규칙(조건 → 동작 13종)을 순서대로 실행하고, 규칙 밖에서는 Bayes 분류기, 유사 거래 가맹점 채우기, LLM 카테고리 분류, LLM 가맹점 감지가 비어 있는 카테고리·가맹점을 채우며, 이 모두가 쓰는 카테고리·태그·가맹점 데이터의 제약을 정의한다.

이 문서에서 쓰는 이름은 다음과 같다. 같은 대상은 끝까지 같은 이름으로 부른다.

- 규칙(`Rule`): 조건(`Rule::Condition`) 0개 이상과 동작(`Rule::Action`) 1개 이상을 가진 가족 단위 레코드.
- 동작(action): 규칙이 거래에 하는 일. `action_type` 13종(1.3 표).
- 속성 잠금(lock): `locked_attributes`(속성명 → 시각 map)에 이름이 있으면 그 속성은 자동 갱신 대상에서 빠진다. 정의는 [transactions](./transactions.md) R-13과 같다. 잠금은 `Entry`(이름·excluded)와 `Transaction`(카테고리·가맹점·태그·`investment_activity_label`)이 따로 가진다.
- enrichment: 자동 출처가 속성 값을 바꾸고 `data_enrichments`에 `(대상, source, 속성명)` 한 행을 남기는 갱신. 규칙은 `source: "rule"`, LLM 분류·감지는 `"ai"`, Bayes는 `"bayes"`, 유사 가맹점 채우기는 `"similar"`. 갱신 메커니즘은 [provider-import-adapter](./provider-import-adapter.md) R-34, 출처 저장 위치는 R-69와 같다.
- 매칭 범위: 규칙이 볼 수 있는 거래 집합(R-07).
- claim: 한 번의 실행 안에서 윗규칙이 어떤 속성을 이미 맡았다는 표시(R-33).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

가맹점명이 한글인 은행 거래가 들어와 카테고리가 붙기까지의 대표 흐름이다. 정확한 기준은 1.4다.

1. 사용자(또는 import)가 거래를 만든다. 거래는 카테고리·가맹점이 비어 있고, 계정이 `draft`/`active`이면 규칙의 매칭 범위에 들어간다(R-07).
2. 동기화가 끝나면 post-sync가 `ApplyRulesJob`을 큐에 넣는다(R-37, sync-pipeline R-15). 규칙 생성·수정 자체는 실행을 부르지 않는다(R-36).
3. `Rule::Runner`가 가족 단위 advisory lock을 잡고 활성 규칙을 위에서 아래로 한 규칙씩 실행한다(R-28~R-31). 새 가족에는 맨 위에 "Merchant matcher"(유사 가맹점 채우기), 그 아래 "Category classifier"(Bayes) 규칙이 이미 있다(R-38).
4. 각 규칙은 조건으로 거래를 고르고(R-08~R-19), 윗규칙이 이미 맡은 속성과 `stop_processing`으로 빠진 거래를 뺀 뒤(R-33, R-34), 동작을 같은 대상 집합에 차례로 적용한다(R-20~R-27). 잠긴 속성은 건드리지 않는다(R-21).
5. 가맹점 채우기와 Bayes 동작은 비어 있는 가맹점·카테고리만 채운다. 한글 이름을 토큰으로 쓰려면 Bayes의 `word_split` 설정을 바꿔야 한다(R-45, R-46).
6. LLM 동작은 같은 대상을 `LLM_MAX_ITEMS_PER_CALL`(기본 25)건씩 나눠 비동기 job으로 보내고, 응답의 카테고리 이름이 사용자 카테고리와 정확히 같을 때만 적용하고 잠근다(R-52~R-55). 끝나면 job이 `RuleRun`에 결과를 보고한다(R-31).
7. 규칙 하나가 실패하면 그 `RuleRun`만 `failed`로 남기고 아래 규칙은 계속 실행한다(R-32).

### 1.2 범위·통합 지점

- 제공:
  - 규칙 모델(조건 10종·연산자·`compound`, 동작 13종, 순서·그룹·`stop_processing`·`effective_date`), 규칙 실행기와 실행 이력(`RuleRun`), 실행 트리거.
  - Bayes 분류기와 설정, 유사 거래 기반 가맹점 채우기, LLM 카테고리 분류, LLM 가맹점 감지의 입력·출력·적용 규칙.
  - 카테고리·태그·가맹점(`FamilyMerchant`, `ProviderMerchant`)의 모델 제약, 삭제·병합 결과, 기본 카테고리 생성.
- 제외:
  - 분류 wizard(`Transactions::CategorizesController`)의 묶음 계산(`Transaction::Grouper::ByMerchantOrName`)과 화면. 이 스펙은 wizard가 부르는 `Rule.create_from_grouping`(R-39)까지만 쓰고, `bulk_update!`로 카테고리를 확정하는 쪽은 [transactions](./transactions.md) R-37·R-32가 갖는다. `Grouper`는 읽지 않았다(확인 한계).
  - `split_once!`와 분할 자식 검증·잠금. `split_transaction` 동작이 이를 부르는 지점(R-26)만 쓰고, 분할 자체는 transactions의 분할 규칙(`entry.rb`의 `split_once!`, 해당 문서 C-02)이다.
  - LLM provider 구현(OpenAI·Anthropic 등의 HTTP 호출, 프롬프트 문구, 토큰 계량). 입력·출력 계약만 R-52~R-57에 쓴다. `Provider::Jev`(분류 provider)의 내부와 `Ai::Router`의 provider 선택은 읽지 않았다(U-02).
  - Bayes 성능 평가(`Family::BayesEvaluation`)와 설정 자동 튜닝(Settings → Classifier의 Evaluate·Find best·Apply best). 분류 결과를 바꾸지 않는 진단 기능이다.
  - 규칙 import/export(`RuleImport`, `Family::DataExporter`), 규칙 이메일 알림의 메일 본문과 `NotificationDelivery` 내부, 규칙 목록 화면(`Rule::ListFilter`).
  - 이체(`Transfer`) 생성 내부와 `Transfer#confirm!`의 효과(행 3). `set_as_transfer_or_payment`가 부르는 지점만 R-25에 쓴다.
  - 금액·환율 일반 규칙([money-currency-rules](./money-currency-rules.md)). 이 스펙은 분할 금액의 자릿수(R-26)에서 `default_precision` 표를 참조한다.
  - provider가 거래를 넣을 때의 `name`/merchant 생성과 보호 skip([provider-import-adapter](./provider-import-adapter.md)).
- 외부 의존·선행 계약: PostgreSQL(`ILIKE`, `~*`, jsonb, advisory lock, `statement_timeout`)을 전제한다. 호출자가 제공하는 것은 가족·계정·거래 저장소, 백그라운드 job 큐(우선순위 `medium_priority`, `ai_low_priority`), LLM provider(입력·출력은 R-52~R-57), `Current.user`(규칙 저장 시 가맹점 선택 검증에만 쓰임). 호출 경계: post-sync가 `ApplyRulesJob`을 큐에 넣는 시점은 sync-pipeline R-11·R-15, 거래의 `bulk_update!`·`split_once!`는 transactions, enrichment 갱신은 provider-import-adapter R-34다.
- 소유 상태·부작용: `rules`·`rule_conditions`·`rule_actions`·`rule_groups`·`rule_runs`, 거래의 `category_id`·`merchant_id`·태그·`investment_activity_label`·`entries.name`·`entries.excluded`에 대한 규칙·자동 분류의 쓰기, 그 속성의 잠금과 `data_enrichments`(`rule`·`ai`·`bayes`·`similar`), `families.bayes_settings`, `categories`·`tags`·`merchants`·`taggings`, `categorization_comparisons`(shadow 비교 기록). 부작용으로 `DebugLogEntry`를 남기고 계정 sync를 예약한다(분할·이체 동작).

### 1.3 인터페이스와 데이터 의미

타입은 중립 표현이다. `uuid`는 문자열 UUID다.

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Rule` | `id: uuid`, `family_id`, `name: string?`, `resource_type: "transaction"`, `active: bool(기본 false)`, `stop_processing: bool(기본 false)`, `effective_date: date?`, `position: int`, `rule_group_id: uuid?`, `conditions: list`, `actions: list` | 검증은 R-01. `position`은 가족의 규칙과 규칙 그룹이 공유하는 한 줄의 순서다(R-03). |
| `Rule::Condition` | `condition_type: string`, `operator: string`, `value: string?`, `parent_id: uuid?`, `sub_conditions: list` | `condition_type`은 10종 + `compound`. 최상위 조건은 모두 AND, `compound`의 `operator`는 `and`/`or`(R-09). 한 단계만 중첩된다. |
| 조건 10종 | 아래 "조건 필터" 표 | 필터 이름은 클래스 이름의 snake_case다. `name`은 옛 이름이라 저장 전에 `transaction_name`으로 바꾼다(R-05). |
| `Rule::Action` | `action_type: string`, `value: string?` | 13종. 다중 값은 쉼표로 이은 문자열 하나로 저장한다(R-20). |
| 동작 13종 | 아래 "동작" 표 | `value` 형식과 효과는 R-22~R-27. |
| `RuleRun` | `rule_id`, `rule_name`, `execution_type: "manual"\|"scheduled"`, `status: "pending"\|"success"\|"failed"`, `transactions_queued/processed/modified/pending_jobs_count: int`, `error_message`, `executed_at` | 규칙 하나를 한 번 실행할 때마다 한 행(R-31). |
| `Family::BayesSettings` | `families.bayes_settings: json`(기본값과 다른 키만 저장) | 키·기본값·허용 범위는 C-20. 핵심 기본값은 R-43~R-47에 적는다. |
| 카테고리 입력(LLM) | `{id: uuid, name: string, is_subcategory: bool, parent_id: uuid?}` 목록 | 가족의 모든 카테고리. 비면 오류(R-52). |
| 거래 입력(LLM) | `{id: uuid, amount: decimal(절댓값), classification: "income"\|"expense", description: string, merchant: string?}` 목록 | `description`은 `name`과 `notes`의 비어 있지 않은 것을 공백 하나로 이은 문자열. `classification`은 `amount < 0`이면 `income`(R-58). |
| LLM 카테고리 출력 | `{transaction_id: uuid, category_name: string?}` 목록 (`AutoCategorization`) | `category_name`이 null이면 "모름". 사용자 카테고리 이름과 정확히 같아야 적용(R-53). |
| LLM 가맹점 출력 | `{transaction_id, business_name: string?, business_url: string?}` 목록 | 둘 다 있어야 적용(R-56). |

조건 필터 10종(`Rule::Registry::TransactionResource` 순서). 연산자 문자열은 저장되는 값이다.

| `condition_type` | 대상 필드 | 허용 연산자 | `value` 의미 |
|---|---|---|---|
| `transaction_name` | `entries.name` | `like`, `not_like`, `starts_with`, `ends_with`, `matches_regex`, `=`, `!=`, `is_null`, `is_not_null` | 텍스트 |
| `transaction_amount` | `ABS(entries.amount)` | `>`, `>=`, `<`, `<=`, `=`, `!=` | 숫자(`to_d`) |
| `transaction_type` | `entries.amount`부호와 `kind` | `=` | `income`/`expense`/`transfer` |
| `transaction_merchant` | `merchants.id` | `=`, `!=`, `is_null`, `is_not_null` | 가맹점 uuid |
| `transaction_category` | `categories.id` | 위와 같음 | 카테고리 uuid |
| `transaction_tag` | `taggings` 존재 여부 | 위와 같음 | 태그 uuid |
| `transaction_details` | `transactions.extra`(JSON) 안의 문자열·숫자 값 | `like`, `=`, `is_null` | 텍스트 |
| `transaction_additional_detail` | `transactions.extra` 안의 키 | `=`, `like` | `키` 또는 `키=값` |
| `transaction_notes` | `entries.notes` | `transaction_name`과 같은 9종 | 텍스트 |
| `transaction_account` | `entries.account_id` | `=`, `!=`, `is_null`, `is_not_null` | 계정 uuid |

동작 13종(`action_type`).

| `action_type` | `value` | 한 줄 효과 |
|---|---|---|
| `set_transaction_category` | 카테고리 uuid | 카테고리를 값으로 바꾼다(R-22) |
| `set_transaction_tags` | 태그 uuid 쉼표 목록 | 기존 태그에 합친다(R-23) |
| `set_transaction_merchant` | 가맹점 uuid | 가맹점을 값으로 바꾼다(R-24) |
| `set_transaction_name` | 새 이름 | `entries.name`을 바꾼다(R-24) |
| `set_investment_activity_label` | 라벨 13종 중 하나 | `investment_activity_label`을 바꾼다(R-24) |
| `exclude_transaction` | 없음 | `entries.excluded`를 켠다(R-24) |
| `set_as_transfer_or_payment` | 상대 계정 uuid | 상대 계정에 반대 거래를 만들어 이체로 확정한다(R-25) |
| `split_transaction` | JSON `{splits: [...]}` | 거래를 분할한다(R-26) |
| `send_email_notification` | 없음 | 새로 매칭된 거래를 이메일로 알린다(R-27) |
| `fill_similar_merchants` | 없음 | 유사 거래의 가맹점을 복사한다(R-48) |
| `bayes_categorize` | 없음 | Bayes로 카테고리를 채운다(R-44) |
| `auto_categorize` | 없음 | LLM으로 카테고리를 채운다(R-52) |
| `auto_detect_merchants` | 없음 | LLM으로 가맹점을 감지한다(R-56) |

### 1.4 행동 규칙과 남은 질문

#### 규칙 모델과 검증

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Rule` 저장 | 다음을 모두 만족해야 저장된다. `resource_type`은 있어야 하고 값은 `transaction`뿐이다. `name`은 nil이거나 1자 이상이다(공백만 있는 문자열은 저장 전에 nil이 된다). `name`·`resource_type`에 NUL이나 깨진 UTF-8이 없다. 동작이 1개 이상이다(삭제 표시된 것은 세지 않고, 새 규칙이 동작을 하나라도 만들고 있으면 통과). 같은 `action_type`이 두 번 나오지 않는다. `split_transaction`이 있으면 동작은 그것 하나뿐이다. `compound` 조건 안에 `compound`가 없다. 규칙에 같은 조건·이름이 이미 있는지는 검사하지 않는다. 조건 0개 규칙도 저장된다(R-07에서 전체 매칭). | 코드 확인 |
| R-02 | 규칙의 기본값 | `active` 기본 false, `stop_processing` 기본 false, `effective_date` 기본 nil(제한 없음), `position` 기본 0. `position`이 양수가 아니면 규칙을 처음 저장(생성)할 때만(`before_create`, 수정 때는 부여하지 않음) 가족의 `max(규칙 position, 규칙 그룹 position) + 1`로 채우고, 이때 가족 단위 advisory lock(namespace 4013)을 잡아 동시 생성이 같은 값을 받지 않게 한다. | 코드 확인 |
| R-03 | 규칙 순서 | 실행·표시 순서는 `position` 오름차순, 같으면 `created_at`, 같으면 `id`다. 규칙과 규칙 그룹은 한 순서(position)를 공유하고 그룹은 자기 상태가 없는 폴더다. 규칙이 그룹에 들어가면 그 그룹의 마지막 규칙 바로 뒤로, 그룹에서 나오면 그 그룹 바로 아래로 옮겨지고 뒤 항목의 `position`이 1씩 밀린다. 같은 `position`이면 그룹이 규칙보다 앞선다. `RuleGroup.name`은 가족 안에서 유일하고 최대 100자다. | 코드 확인 |
| R-04 | `Rule::Condition` 저장 | `condition_type`은 10종 또는 `compound`여야 하고, `operator`는 있어야 한다. `value`는 `compound`이거나 연산자가 `is_null`/`is_not_null`일 때만 비어도 된다. NUL·깨진 UTF-8은 거부한다. 연산자가 그 `condition_type`이 지원하는 것인지는 저장할 때 검사하지 않는다(R-17에서 실행 때 실패). | 코드 확인 |
| R-05 | 옛 `condition_type` | 저장 전 검증에서 `name`은 `transaction_name`으로 바뀐다. | 코드 확인 |
| R-06 | 저장된 `condition_type`이 지금 등록부에 없다 | 실행하면 그 조건은 0건을 매칭하고(warning 로그) 규칙의 나머지는 정상 실행된다. AND 규칙이면 결과적으로 0건이다. | 코드 확인 |

#### 매칭 범위와 조건 의미

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 규칙의 매칭 범위 | 가족 거래 중, 계정 status가 `draft`/`active`이고, 분할 원본(자식 entry가 있는 entry)이 아니고, `effective_date`가 있으면 `entry.date >= effective_date`인 거래다. `excluded`, 보류, 이체 `kind` 거래도 포함된다. 조건이 없으면 이 범위 전체가 매칭이다. | 코드 확인 |
| R-08 | 규칙 조건 평가 | 최상위 조건은 모두 AND다. 조건 하나를 평가하기 전에 필요한 JOIN(`entries`, `categories`, `merchants`)이 먼저 붙는다. 규칙에 `matches_regex` 조건이 하나라도 있으면 매칭 id 목록을 `statement_timeout` 5000ms 아래서 먼저 뽑고 그 id 집합으로 범위를 좁힌다. | 코드 확인 |
| R-09 | `compound` 조건 | `operator`가 `or`이면 하위 조건 결과를 OR로 묶고(하위가 0개면 범위 그대로), 그 밖의 값(`and` 포함)이면 모두 AND로 묶는다. | 코드 확인 |
| R-10 | 텍스트 필드(`transaction_name`, `transaction_notes`)의 값 정규화 | `matches_regex`를 뺀 연산자는 값에서 연속 공백 `\s+`를 공백 하나로 바꾸고 앞뒤를 자른 값과, 필드에서 `BTRIM(REGEXP_REPLACE(field, '[[:space:]]+', ' ', 'g'))`로 같은 처리를 한 값을 비교한다. `%`와 `_`는 문자 그대로 비교되게 이스케이프한다. `matches_regex`는 값도 필드도 정규화하지 않는다. | 코드 확인 |
| R-11 | 텍스트 연산자 의미 | `like` 포함·`starts_with` 앞부분·`ends_with` 뒷부분은 `ILIKE`(영문 대소문자 무시)다. `not_like`는 `NOT ILIKE`이고 필드가 NULL인 행도 매칭한다(필드는 정규화 전 값으로 검사). `=`는 대소문자를 구분하는 같음, `!=`는 `IS DISTINCT FROM`(NULL인 행도 매칭)이다. `matches_regex`는 `~*`(대소문자 무시 정규식)다. `is_null`/`is_not_null`은 필드를 정규화 없이 `IS NULL`/`IS NOT NULL`로 검사하므로 빈 문자열 메모는 `is_null`에 걸리지 않는다. | 코드 확인 |
| R-12 | 한글·공백·대소문자·정규화 처리 | 한글에는 대소문자가 없어 한글 값의 비교 결과는 대소문자로 갈리지 않는다(`like`는 값을 포함하는지, `=`는 정규화한 전체가 같은지로 갈린다). 영문이 섞인 이름에서는 `like`·`starts_with`·`ends_with`·`matches_regex`만 대소문자를 무시하고 `=`·`!=`는 구분한다. 값 쪽 공백 정규화는 Ruby `\s`(ASCII 공백)로 하고 필드 쪽은 PostgreSQL `[[:space:]]`로 하므로, 전각 공백(U+3000)·NBSP가 값에 있으면 값에서는 접히지 않고, 필드에서는 DB 로케일에 따라 접힐 수도 있다(U-01). 원본에는 유니코드 정규화(NFC/NFD)가 없어서 조합형(NFD) 한글 이름은 완성형(NFC) 값과 `like`로 맞지 않는다. | 코드 확인(정규화 없음), 추론(`\s`와 로케일 동작) |
| R-13 | Plaid 이름 호환 | `transaction_name`의 `=`/`!=`만, 이름이 값과 같거나, 거래가 `entries.source = 'plaid'`이고 정규화한 이름이 `값 + " - " + transactions.extra.plaid.original_description`(정규화)와 같으면 매칭으로 본다(`!=`는 그 부정, NULL은 FALSE로 취급해 수동 입력 행이 `!=`에서 빠지지 않는다). 다른 source에는 적용하지 않는다. | 코드 확인 |
| R-14 | `transaction_amount` | 값을 `to_d`로 바꿔(숫자가 아니면 0) `ABS(entries.amount)`와 비교한다. 부호와 통화는 보지 않는다. 환율 환산이 없으므로 `> 10000`은 KRW 15,000원과 USD 12,000달러에 똑같이 참이다. | 코드 확인 |
| R-15 | `transaction_type` | `income`은 `amount < 0`이고 `kind`가 이체 종류(`funds_movement`, `cc_payment`, `loan_payment`, `investment_contribution`)가 아닌 것, `expense`는 `amount >= 0`이고 이체 종류가 아닌 것(0원 포함), `transfer`는 이체 종류인 것이다. 그 밖의 값은 조건 없음과 같이 모두 통과한다. `operator`는 보지 않는다. | 코드 확인 |
| R-16 | 선택형 조건(`transaction_merchant`, `transaction_category`, `transaction_account`) | `=`는 id 같음, `!=`는 `IS DISTINCT FROM`이라 가맹점·카테고리가 비어 있는 거래도 매칭한다. `is_null`/`is_not_null`은 미설정/설정이다. 지워진 가맹점·카테고리 id에 대한 `=`는 0건, `!=`는 전체를 매칭한다. uuid 형식이 아닌 값은 DB 오류로 이어져 그 규칙 실행이 `failed`가 될 것으로 본다. | 코드 확인, 추론(잘못된 uuid) |
| R-17 | 필터가 지원하지 않는 연산자로 실행 | `UnsupportedOperatorError`가 나고 그 규칙은 `failed`로 기록된다(R-32). 저장 때는 막지 않는다(R-04). `transaction_tag`는 `=`/`!=`/`is_null`/`is_not_null`만 처리하고 나머지는 같은 오류다. | 코드 확인 |
| R-18 | `transaction_tag` | 태그가 있는 거래는 correlated EXISTS로 판정한다. `=`는 그 태그가 붙은 것, `!=`는 그 태그가 붙지 않은 것(태그 없는 거래 포함), `is_null`은 태그가 하나도 없는 것, `is_not_null`은 하나라도 있는 것이다. 태그 조건 두 개를 AND하면 두 태그를 모두 가진 거래만 남는다. | 코드 확인 |
| R-19 | `transaction_details`·`transaction_additional_detail` | `transactions.extra`(JSON)를 본다. `transaction_details`는 어느 깊이든 문자열·숫자 값(키·true/false/null 제외)에 `like`는 포함(`ILIKE`), `=`도 포함(`LIKE`, 대소문자 구분)이고, `is_null`은 `extra`가 NULL이거나 `{}`인 것이다. 값은 공백 정규화를 하지 않는다. `transaction_additional_detail`은 `value`를 첫 `=`에서 `키`와 `값`으로 나눠(둘 다 strip) 어느 깊이의 객체에서든 그 키를 찾는다. `=`는 값이 같음(대소문자 구분), `like`는 포함(`ILIKE`)이고, `=`가 없으면 키만 있으면 되며 JSON null 값도 있는 것으로 센다. 키가 비면 0건이다. | 코드 확인 |

#### matches_regex 안전장치

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20a | `matches_regex` 조건을 새로 만들거나 값·연산자를 바꾸는 저장 | 패턴이 공백뿐이면 `blank`, 200자를 넘으면 `too_long`, 이스케이프 쌍을 읽어 `\1`~`\9` 역참조가 있으면 `backreference`(`\\1`은 역슬래시 + 1이라 통과), DB가 컴파일하지 못하면(`SELECT '' ~* 패턴`을 1000ms 안에 시도) `invalid`, 1000ms를 넘기면 `too_complex`로 거부된다. 값·연산자가 안 바뀌면 다시 검사하지 않는다. | 코드 확인 |
| R-20b | 저장된 패턴 규칙 실행 | 매칭 id를 뽑는 쿼리가 5000ms를 넘기면 `Rule::SafeRegex::TimeoutError`가 나고 그 규칙은 `failed`다. 규칙 매칭 건수를 화면에 세는 경우는 0으로 보이고, "이 거래가 규칙에 맞는가" 판정은 false다. `RuleJob`은 이 오류를 재시도하지 않고 버린다. | 코드 확인 |

#### 동작 적용

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 동작 `value` 저장·해석 | 배열로 들어온 `value`는 비어 있지 않은 항목만 쉼표로 이어 한 문자열로 저장한다. 다중 선택 동작(`set_transaction_tags`)만 실행 때 쉼표로 다시 나눈다. 쉼표가 들어 있는 이름을 portable 값으로 인코딩할 때는 CSV 인용을 쓴다. 실행 시점에 `action_type`이 등록부에 없을 때만 `UnsupportedActionError`로 그 규칙이 `failed`다(AI 동작이 AI 없이 실패하는 경로는 R-21a). | 코드 확인 |
| R-21a | `auto_categorize`/`auto_detect_merchants`의 노출과 AI가 없을 때 | 노출 조건은 편집 화면의 선택지에만 영향을 준다. 규칙이 이미 그 동작을 가졌거나 해당 기능의 AI가 가용(`Ai.available?(:categorize / :detect_merchants)`)일 때 보인다. 저장 검증은 13종 전체를 허용한다. 저장된 AI 동작은 자기 자신이 `rule.actions`에 있어 실행 때 노출 조건(`existing_action?`)을 항상 통과하므로 AI가 없어도 `UnsupportedActionError`가 나지 않는다. 동작은 job을 큐에 넣고, job 안에서 `AutoCategorizer`가 `Error`(provider 없음)를 던지면 `RuleRun`이 `fail_job!`로 `failed`가 된다(`auto_detect_merchants`는 R-56). `UnsupportedActionError`는 `action_type`이 등록부에 없을 때뿐이다. 가용 판정 내용은 읽지 않았다(U-02). | 코드 확인, 미확인(가용 판정) |
| R-21 | 속성 잠금과 덮어쓰기(공통) | 값을 바꾸는 동작은 `ignore_attribute_locks`가 false일 때 그 속성이 잠긴 거래를 대상에서 뺀다. 잠금 키는 카테고리 `category_id`, 가맹점 `merchant_id`, 태그 `tag_ids`, `investment_activity_label`(모두 `transactions.locked_attributes`)이고, `name`·`excluded`는 `entries.locked_attributes`다. `ignore_attribute_locks`가 true(사용자 Apply, Apply all)이면 `set_transaction_category`·`set_transaction_tags`·`set_transaction_merchant`·`set_transaction_name`·`set_investment_activity_label`·`exclude_transaction`·`split_transaction`이 잠금을 무시하고 덮어쓴다. `bayes_categorize`·`fill_similar_merchants`·`auto_categorize`·`auto_detect_merchants`는 플래그와 상관없이 항상 잠금을 존중한다(항상 `enrichable` 범위만 본다). 갱신은 `enrich_attribute(속성, 값, source: "rule")`이고, 값이 같으면 바뀐 것으로 세지 않는다. 규칙 동작은 속성을 잠그지 않는다(분할 동작의 자식 잠금만 예외, R-26). | 코드 확인 |
| R-22 | `set_transaction_category` | `value`가 가족의 카테고리 id가 아니면 0건 처리한다. 맞으면 대상 거래의 `category_id`를 그 값으로 바꾸고 `rule` enrichment를 남긴다. 카테고리가 지워져 값이 가족 카테고리가 아니면 이 동작은 claim도 하지 않는다(R-33). | 코드 확인 |
| R-23 | `set_transaction_tags` | `value`의 태그 중 가족 소유만 쓰고 하나도 없으면 0건이다. 거래별로 행 잠금(`with_lock`) 안에서 `기존 태그 ∪ 선택 태그`로 갱신한다. 기존 태그를 지우지 않는다. 같은 규칙 실행에서 태그는 claim하지 않아 여러 규칙의 태그가 누적된다. | 코드 확인 |
| R-24 | 단일 값 동작 4종 | `set_transaction_merchant`: `value`가 uuid이고 가족의 `FamilyMerchant`이거나 가족 거래에 쓰이는 `ProviderMerchant`일 때만 적용하고, 아니면 0건이며 claim도 하지 않는다. 사용자가 규칙을 저장할 때는 그 사용자가 쓸 수 있는 가맹점(`assignable_merchants_for`)만 허용한다. `set_transaction_name`: `value`가 비어 있으면 0건, 아니면 `entries.name`을 바꾼다(`entries.locked_attributes`의 `name` 검사). `set_investment_activity_label`: `Transaction::ACTIVITY_LABELS` 13종(`Buy`, `Sell`, `Sweep In`, `Sweep Out`, `Dividend`, `Reinvestment`, `Interest`, `Fee`, `Transfer`, `Contribution`, `Withdrawal`, `Exchange`, `Other`) 밖이면 0건. `exclude_transaction`: `value`를 쓰지 않고 `entries.excluded`를 true로만 바꾼다(끄는 동작은 없다. `entries.locked_attributes`의 `excluded` 검사). | 코드 확인 |
| R-25 | `set_as_transfer_or_payment` | `value`가 가족 계정이 아니면 0건이다. 이 동작은 `ignore_attribute_locks`를 쓰지 않고 잠금 검사도 하지 않는다. 대상 거래가 이미 이체(`transfer?`)면 건너뛴다. 아니면 상대 계정에 부호 반대·같은 통화·같은 날짜의 거래를 새로 만들고(이름은 상대가 부채 계정이면 `Payment`, 아니면 `Transfer`로 시작해 방향에 따라 `to <상대 계정명>` 또는 `from <이 계정명>`을 붙임, `user_modified: true`) `Transfer`를 `confirmed`로 저장·확정하고 계정 sync를 예약한다. 변경 건수 집계(블록이 true/false를 돌려주지 않아 `previous_changes`로 대체)가 어떻게 되는지는 확인하지 못했다(U-03). | 코드 확인, 추론(건수 집계) |
| R-26 | `split_transaction` | 설정은 `{splits: [...]}` JSON이다. 저장 검증(2~20행, 이름 필수·255자 이하, `type`은 `fixed`/`percentage`, `share > 0`이고 `fixed`는 소수 4자리 이하, `percentage` 합이 100(허용 오차 0.01), 카테고리·가맹점·태그 id는 가족 것, 순수 `fixed`면 AND 조건으로 `transaction_amount = X`가 있고 `fixed` 합이 X)는 C-16·C-18이다. 실행은 분할 원본이 아니고 자식이 아니고 `excluded`가 아닌 거래 중 `splittable?`(이체 아님, 분할 자식·원본 아님, 보류 아님, `excluded` 아님)인 것만 대상으로 하고, `entries.locked_attributes`에 `excluded`가 있으면 건너뛴다(잠금 무시 모드는 예외). 이체·보류 거래는 로그 없이 조용히 건너뛴다. 각 거래에서 `fixed` 행을 먼저 빼고 남은 금액을 `percentage` 행에 비율대로 나눠(마지막 percentage 행이 반올림 잔액을 가진다) 금액 부호는 원 거래를 따르며 자릿수는 `min(통화 default_precision, 4)`(알 수 없는 통화는 2)다. 합이 맞지 않거나 `percentage` 금액이 0 이하이면 그 거래만 건너뛰고(`unresolvable_split_amounts`), 저장 오류도 그 거래만 건너뛴다(`record_invalid`). 건너뛴 것은 규칙 실행당 한 번의 `DebugLogEntry`(warning, 최대 20건)로 남긴다. `entry.split_once!(splits, lock_attributes: true)`는 잠금 안에서 분할 원본·`excluded`·이체·보류를 다시 확인해 하나라도 걸리면 false를 돌려주고(건너뜀, 로그 없음), 분할이 일어나면 계정 sync를 예약한다. 이 동작은 아무 속성도 claim하지 않는다. | 코드 확인 |
| R-27 | `send_email_notification` | 규칙이 활성일 때만 실행한다(비활성이면 0). 매칭된 거래 id 중 이 규칙으로 아직 알린 적 없는 것만 `NotificationDelivery`에 기록하고(동시 실행이 겹쳐도 한 쪽만 새 id를 받는다), 그 id로 메일 job을 큐에 넣고 새 건수를 돌려준다. 규칙 생성·활성화·동작 추가·조건 변경 때는 그 시점의 매칭을 "이미 알림"으로 미리 기록해서(baseline) 이후 새로 생기는 거래만 알린다. baseline 쿼리가 시간 초과면 규칙을 끄고 이유를 기록한다. 메일 본문은 범위 밖이다. | 코드 확인 |

#### 실행기

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | 실행 대상 규칙 선택 | 가족 규칙을 순서(R-03)대로 훑는다. 요청된 규칙은 실행하고, 요청되지 않은 규칙은 활성일 때만 `ignore_attribute_locks: false`로 실행한다(윗규칙 효과를 먼저 반영하기 위해서). 마지막 요청 규칙을 지나면 멈추므로 그 아래 규칙은 실행하지 않는다. `ignore_attribute_locks`는 요청된 규칙에만 적용된다. | 코드 확인 |
| R-29 | 가족당 동시 실행 | `pg_try_advisory_lock`(키: `"rule_runner:<family_id>"`의 MD5를 2^62로 나눈 나머지)로 가족 하나에 한 번만 실행한다. 잠금을 못 얻으면 `LockBusy`가 나고, 세 job(`ApplyRulesJob`, `ApplyAllRulesJob`, `RuleJob`)은 30초 간격으로 총 20회까지 시도한다(재시도 19회). 요청 규칙이 없으면 아무것도 하지 않는다. | 코드 확인 |
| R-30 | 한 규칙의 실행 | 매칭 id(R-08)에서 윗규칙의 `stop_processing`이 거른 거래를 뺀 집합을 먼저 확정하고 `RuleRun`(`pending`, `transactions_queued`=그 수)을 만든다. 모든 동작은 조건을 다시 평가하지 않고 이 확정된 id 집합에 차례로 적용된다. 그래서 앞 동작이 이름을 바꿔 조건이 더는 안 맞아도 뒤 동작은 그 거래에 적용된다. | 코드 확인 |
| R-31 | `RuleRun` 기록 | 동기 동작만 있으면 `success`, `transactions_processed`=queued, `transactions_modified`=동작별 변경 건수의 합이다. 비동기 동작(`auto_categorize`, `auto_detect_merchants`)이 실제로 job을 큐에 넣었으면 `pending`, `pending_jobs_count`=큐에 넣은 job 수, `transactions_processed`=비동기 대상 수(`enrichable` 거래 수)에 같은 규칙의 동기 동작 변경 건수를 더한 값으로 두고(대상이 없어 job을 안 넣으면 정수 0을 돌려주므로 비동기가 아니고 `success`), 각 job이 끝날 때 `complete_job!`이 변경 건수를 더하고 job 수를 줄여 0이 되면 `success`(이미 `failed`면 유지)로 바꾼다. job이 실패하면 `fail_job!`이 `failed`와 오류 메시지를 줄 단위로 누적한다. `execution_type`은 `manual`/`scheduled`뿐이다. | 코드 확인 |
| R-32 | 규칙 하나가 예외로 실패 | 그 규칙의 `RuleRun`은 `failed`(`error_message`는 `<오류 클래스>: <메시지>`)가 되고 `DebugLogEntry`(category `rule_run`)가 남으며 아래 규칙은 계속 실행된다. 실패 시점에 따라 claim·`stop_processing`이 다르다(R-33, R-34). 매칭 단계 실패(정규식 timeout, 지원하지 않는 연산자 R-17, 잘못된 uuid R-16)는 `matched_ids`가 빈 집합이라 `RuleRun`이 `transactions_queued = 0`으로 `failed`가 되고 아무 거래도 claim·제외하지 않는다. 동작 단계 실패는 이미 확정한 매칭 집합의 claim·`stop_processing`이 반영된다. job 정책: `ApplyRulesJob`과 `ApplyAllRulesJob`은 실패한 규칙이 있어도 오류를 던지지 않고 끝난다(`ApplyRulesJob`은 재시도하면 전체가 다시 돌기 때문). `RuleJob`은 마지막(요청한) 규칙이 `failed`이면 그 오류를 다시 던져 job을 실패로 만들고, 정규식 timeout은 재시도 없이 버린다. | 코드 확인 |
| R-33 | top rule wins(claim) | 규칙이 매칭한 모든 거래(값이 이미 같거나 잠겨 안 바뀐 것도 포함, 동작 단계에서 실패한 규칙도 포함)에 대해 그 규칙 동작의 claim 속성을 실행 내내 기억한다. 매칭 단계에서 실패한 규칙은 매칭 집합이 비어 아무것도 claim하지 않는다. 속성은 `category_id`, `merchant_id`, `name`, `excluded`, `transfer`, `investment_activity_label`이다. 아래 규칙의 동작은 자기 claim 속성을 윗규칙이 claim한 거래를 대상에서 뺀다. 같은 규칙의 동작끼리는 서로 막지 않는다. 태그·`split_transaction`·`send_email_notification`은 claim하지 않는다. 값이 가리키는 레코드가 사라져 실행해도 아무것도 못 바꾸는 동작(`actionable?` false)과, AI·Bayes·유사 가맹점 동작(R-44, R-48, R-52, R-56)은 claim을 남기지 않아 아래 규칙을 막지 않는다. 다만 이 동작들도 윗규칙의 claim은 존중한다. | 코드 확인 |
| R-34 | `stop_processing` | 규칙이 켜져 있으면 그 규칙이 매칭한 거래는 실행 내내 아래 규칙 대상에서 빠진다(매칭 직후, 동작 단계에서 실패해도). 매칭 단계에서 실패하면 빈 집합이라 아무 거래도 제외하지 않는다. | 코드 확인 |

#### 실행 트리거

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-35 | 규칙이 보는 대상의 시점 | 규칙 조건은 실행하는 순간의 데이터로 평가한다. 거래·규칙 생성이나 거래 수정이 규칙을 따로 호출하지 않는다. | 코드 확인 |
| R-36 | 규칙을 만들거나 수정 | 저장만 하고 실행하지 않는다. 생성 뒤에는 확인(confirm) 화면으로 보내고(매칭 건수·AI 비용 추정 표시), 수정 뒤에는 목록으로 돌려보낸다. | 코드 확인 |
| R-37 | 실행이 일어나는 경로 | (a) 동기화 뒤 `ApplyRulesJob`: 가족의 활성 규칙만, 잠금 존중, `execution_type: "scheduled"`. (b) 사용자 "Apply": 그 규칙을 `active: true`로 바꾼 뒤 `RuleJob`을 큐에 넣는다. 잠금 무시, 위의 활성 규칙을 먼저 돌림(R-28). 이메일 baseline이 시간 초과로 규칙이 꺼진 채면 실행하지 않는다. (c) 사용자 "Apply all": `ApplyAllRulesJob`이 가족의 모든 규칙(비활성 포함)을 잠금 무시로 돌린다. (d) Settings → Classifier의 Run: `BayesCategorizeJob`이 규칙 순서 밖에서 유사 가맹점 채우기(그 규칙이 활성일 때만) 뒤 Bayes를 돌린다. (e) assistant의 `apply_rule` 도구와 FinanceKit 하위 처리도 같은 job을 부른다. (f) 운영 작업 `rules:apply_all[family_id]`(rake)는 job 없이 `Rule::Runner`를 직접 불러 가족의 모든 규칙을 잠금 무시·`manual`로 한 번 돌린다. `LockBusy`면 재시도 없이 실패 메시지를 출력하고 종료 코드 1로 끝나며, 실패한 규칙이 있어도 종료 코드 1이다. 동기화 뒤 호출 시점은 [sync-pipeline](./sync-pipeline.md) R-11·R-15(post-sync)를 따른다. | 코드 확인 |
| R-38 | 새 가족 생성 | 가족이 커밋되면 조건 없는 활성 규칙 두 개가 만들어진다. position 1은 "Merchant matcher"(`fill_similar_merchants`), position 2는 "Category classifier"(`bayes_categorize`)다(기존 규칙·그룹이 있으면 position이 1씩 밀린다). 규칙 이름은 로케일 문자열이다. Settings → Classifier의 스위치는 그 `action_type`을 가진 규칙의 `active`를 켜고 끄며, 규칙이 지워졌으면 켤 때 다시 만들지 묻는다. | 코드 확인 |
| R-39 | 분류 wizard가 규칙을 만든다 | `Rule.create_from_grouping(가족, grouping_key, 카테고리, transaction_type:)`: 이름이 `grouping_key`이고 활성인 규칙을 만든다. 조건은 `transaction_name like grouping_key`(+ `transaction_type`이 있으면 `transaction_type = 그 값`)이고 동작은 `set_transaction_category`(카테고리 id)다. 저장이 검증 오류면 nil을 돌려주고 호출자가 경고를 띄운다. 같은 규칙의 중복은 막지 않는다. 만든 규칙은 즉시 실행되지 않는다(R-36). wizard 자체와 카테고리 확정은 transactions R-37. | 코드 확인 |

#### Bayes 분류기

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | 학습 데이터 | 가족 거래 중 카테고리가 있는 것에서, 제외 카테고리(부모를 제외하면 자식도)와 `exclude_transfers`(기본 off)일 때 이체 종류, `skip_self_labels`(기본 on)일 때 "Bayes가 `self_label_grace_days`(기본 90)일 안에 붙인 뒤 사용자가 바꾸거나 잠그지 않은 것"(Bayes 자신이 건 잠금은 확인으로 치지 않음)을 뺀다. 생성 시각 내림차순(`created_at DESC, id DESC`)으로 최대 `max_training_transactions`(기본 5000, 범위 100~20000)건을 쓴다. | 코드 확인 |
| R-41 | 학습 가드 | 학습 거래가 20건 이상이고 서로 다른 카테고리가 2개 이상일 때만 분류한다. 아니면 `probabilities`는 빈 값이고 아무것도 채우지 않는다. | 코드 확인 |
| R-42 | 거래의 텍스트 토큰 | `name`, `include_notes`(기본 true)이면 `notes`, `merchant_name_words`(기본 true)이면 가맹점 이름을 공백으로 이어 소문자로 바꾼다(Ruby `downcase`). `word_split` 기본 `ascii`는 `[a-z0-9]+` 토큰만, `unicode`는 `[\p{L}\p{N}]+`, `symbols`는 글자·숫자 덩어리가 기호 하나로 이어진 것(`mcdonald's`)까지 한 토큰으로 자른다. 그러므로 기본 설정에서 한글만 있는 이름은 토큰이 0개다. 그 뒤 옵션: `drop_numbers`(기본 off), `keep_single_chars`(기본 on, off면 1글자 제거), `drop_codes`(기본 off, 글자와 숫자 2개 이상이 섞인 코드 제거), `bigrams`(기본 off). `merchant_field`(기본 off)이면 `merchant:<가맹점 id>`, `account_field`(기본 off)이면 `account:<계정 id>` 토큰을 더한다. `binary`(기본 off)이면 거래당 토큰을 중복 제거한다. | 코드 확인 |
| R-43 | 점수 계산(기본 설정) | 카테고리 c의 점수는 `log(1/K) + Σ log((count_t(c)+1)/(total(c)+V))`이다(K=학습된 카테고리 수, V=어휘 크기, 평활 `smoothing` 1.0). 어휘에 없는 토큰은 건너뛰고, 계정 토큰이 아닌 알려진 토큰이 하나도 없으면 결과가 비어 분류하지 않는다. 점수를 softmax(안정화)한 값이 confidence다. `complement`·`prior`·`separate_fields`·`spread_filter`·`amount_field`는 기본 off이고 켜면 식이 달라진다(C-19). | 코드 확인 |
| R-44 | 분류와 적용 | 최고 confidence가 `threshold`(기본 0.7, 범위 0.05~0.99) 이상이면 그 카테고리를, 아니면 nil(모르는 것)을 돌려준다. 적용은 `category_id`가 nil이고 `category_id`가 잠기지 않은 거래만 대상이며, `enrich_attribute(:category_id, source: "bayes", metadata: {confidence(소수 3자리), model: "bayes-2", settings: <설정 digest>})`로 갱신한다. `lock_results`(기본 off)가 켜져 있으면 metadata에 `locked_by_bayes: true`를 넣고 `category_id`를 잠근다. `bayes_categorize` 동작과 `Family#bayes_categorize_uncategorized`는 대상을 규칙 매칭 범위 ∩ `category_id`가 nil ∩ `kind`가 `funds_movement`·`cc_payment`가 아님 ∩ 잠기지 않음으로 좁히고 변경 건수를 돌려주며 `DebugLogEntry`(info)를 남긴다. 이 동작은 claim을 남기지 않는다(R-33). | 코드 확인 |
| R-45 | 기본 설정에서 한글 거래 | `word_split: "ascii"`이므로 한글만 있는 이름·메모·가맹점명은 토큰이 0개고, 학습 쪽 한글 텍스트도 어휘에 들어가지 않는다. `merchant_field`를 켜지 않으면 한글 거래는 알려진 토큰이 없어 분류되지 않는다. `unicode`나 `symbols`로 바꾸면 한글 덩어리(공백·기호로 끊긴 단위)가 토큰이다. 형태소 분석은 없어서 "스타벅스강남점"처럼 붙여 쓴 이름은 한 토큰이다. | 코드 확인 |
| R-46 | 설정 저장 | `bayes_settings`에는 기본값과 다른 키만 저장되고, 모르는 키는 버려지며 값은 키 종류(boolean, 정수·실수는 허용 범위로 clamp, 문자열은 선택지 안에서, 목록은 문자열 정렬·중복 제거)에 맞게 변환된다. 설정 digest는 저장 값의 정렬 JSON의 SHA256 앞 12자다. "초기화"는 `{}`로 저장한다. | 코드 확인 |
| R-47 | 규칙이 건 잠금 풀기 | `clear_bayes_locks!`는 `lock_results`로 Bayes가 건 `category_id` 잠금과 `lock_similar_merchants`로 유사 가맹점 동작이 건 `merchant_id` 잠금 중 값이 그대로인 것만 풀고 값은 둔다. 사용자가 건 잠금은 풀지 않는다. | 코드 확인 |

#### 유사 거래로 가맹점 채우기

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-48 | `fill_similar_merchants` 대상 | 규칙 매칭 범위 중 `merchant_id`가 nil, 이체 종류가 아님, `merchant_id`가 잠기지 않은 거래만 채운다. 풀(복사 원본)은 가맹점이 있고 이체 종류가 아닌 거래 중 `similar_skip_self`(기본 on)일 때 "유사 채우기가 `similar_self_grace_days`(기본 90)일 안에 붙인 뒤 사용자가 확인하지 않은 것"을 뺀 최신순 최대 `max_training_transactions`(Bayes와 같은 설정, 기본 5000, 범위 100~20000)건이다. 풀 크기가 `similar_min_neighbours`(기본 2) 미만이면 아무것도 안 한다. `ignore_attribute_locks`를 무시하고 항상 잠금을 존중한다. claim은 남기지 않는다. | 코드 확인 |
| R-49 | 유사도 계산 | 거래 이름에서 특징을 뽑는다. 단어: 소문자로 바꾼 뒤 `[\p{L}\p{N}]+` 덩어리 중 글자를 포함하고 "글자와 숫자 2개 이상이 섞인 코드"가 아닌 것(그래서 `8812`, `2k4l19`는 버려지고 `7eleven`은 남는다). 문자 3-gram: 단어를 공백 하나로 이어 앞뒤에 공백을 붙인 문자열(Ruby 문자 단위)의 3글자 조각. 풀 안 문서 빈도 df로 `idf = ln((풀 크기+1)/(df+1)) + 1`, df가 `max(floor(풀 크기 × similar_common_share(기본 0.2)), 50)`을 넘는 특징은 무시한다. 가중치는 `(1+ln(count)) × idf`를 단어·3-gram 각각 L2 정규화하고, 유사도는 두 코사인의 평균(`(단어 코사인 + 3-gram 코사인)/2`)이다. `similar_threshold`(기본 0.9, 범위 0.5~0.99) 이상이고 자기 자신이 아닌 풀 거래가 이웃이다. | 코드 확인 |
| R-50 | 이웃 합의 | 이웃 중 가맹점이 있는 것들의 값이 `similar_min_neighbours`(기본 2, 범위 1~3)개 이상이고 모두 같을 때만 그 가맹점을 쓴다. 가맹점이 없는 이웃은 세지 않는다. 한 곳이라도 다르면 채우지 않는다. | 코드 확인 |
| R-51 | 적용 | 합의한 가맹점으로 `enrich_attribute(:merchant_id, source: "similar", metadata: {locked_by_similar: true}(`lock_similar_merchants`가 켜졌을 때만, 기본 off))`를 부르고, 실제로 바뀌었고 `lock_similar_merchants`이면 `merchant_id`를 잠근다. 돌려주는 값은 채운 거래 수다. | 코드 확인 |

#### LLM 카테고리 분류와 가맹점 감지

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-52 | `auto_categorize` 동작 | 매칭 범위 중 `category_id`가 잠기지 않은 거래를 `LLM_MAX_ITEMS_PER_CALL` 환경변수 > 설정 `llm_max_items_per_call` > 25(0 이하는 건너뜀)건씩 나눠 `AutoCategorizeJob`(큐 `ai_low_priority`)에 넣는다. 반환은 비동기 결과이고 대상 수에는 이미 카테고리가 있는 거래도 포함된다(job 안에서 다시 거른다). 대상이 없으면 0이다. 이 동작은 claim을 남기지 않는다. | 코드 확인 |
| R-53 | `AutoCategorizer` 실행(job 안) | 대상은 전달된 id ∩ 가족 ∩ `category_id`가 nil ∩ 잠기지 않은 거래다(대상이 없으면 0). provider가 없으면 `Error`, 카테고리가 하나도 없으면 DebugLog(error) 후 `Error`, provider 응답이 실패면 `Error`를 던져 job이 실패하고 `RuleRun`에 반영된다. 응답을 `transaction_id`로 대응시키고 `category_name`이 사용자 카테고리 이름과 정확히 같은 것만 적용한다(없거나 다르면 그 거래는 건너뜀). 적용은 `enrich_attribute(:category_id, source: "ai")` 뒤 변경 여부와 상관없이 `category_id`를 잠근다. 이미 잠긴 거래 중 `ai` 출처가 현재 값이면 "캐시 사용", 아니면 "보호로 차단"이라고 로그만 남긴다. 변경된 건수를 돌려준다. | 코드 확인 |
| R-54 | confidence 임계값과 shadow 비교 | 분류 provider(`CategoryDecision`을 돌려주는 Jev 등)의 응답만 임계값을 적용한다. 임계값은 환경변수 `CATEGORIZATION_CONFIDENCE_THRESHOLD` > 가족 설정(DB 기본 0.7, 범위 0~1)이고, 0이면 모두 적용한다. 임계값이 양수이고 `confidence`(없으면 0) < 임계값이면 그 응답은 적용·잠금하지 않고 로그에만 남겨 다음 실행에서 다시 시도되게 한다. LLM provider 응답은 신뢰도가 없어 임계값을 적용하지 않는다. `categorization_shadow_rate`(기본 0)의 확률로 사용하지 않는 쪽 provider에도 같은 입력을 보내 결과를 `categorization_comparisons`에 기록하되 적용하지 않고, 실패는 무시한다. 기본 provider는 `ENV["CATEGORIZATION_PROVIDER"]` > 가족 설정(`llm` 또는 `jev`)이고, Jev를 못 만들면 LLM provider로 대체한다. | 코드 확인 |
| R-55 | LLM 호출 입력 배치 | provider는 한 번에 받은 거래 목록을 모델 context 길이에 맞게 추가로 나눠 호출하고(`BatchSlicer`, 사용자 카테고리 목록은 매 호출의 고정 비용), 결과를 이어 붙인다. OpenAI provider에서 사용자 카테고리가 없으면 `Error`다. | 코드 확인 |
| R-56 | `auto_detect_merchants` 동작과 `AutoMerchantDetector` | 동작은 매칭 범위 중 `merchant_id`가 잠기지 않은 거래(가맹점이 이미 있어도 포함)를 R-52와 같은 크기로 `AutoDetectMerchantsJob`에 넣고 claim을 남기지 않는다. 실행은 provider가 없으면 `RuntimeError`, provider 응답이 실패면 오류를 던지지 않고 0을 돌려준다(R-53과 다름). `business_name`과 `business_url`이 둘 다 있는 응답만 쓴다. (1) 거래에 가맹점이 없으면: 이름이 가족 `FamilyMerchant` 이름과 정확히 같은 것을 쓰고, 없으면 `website_url`이 같은 비 AI `ProviderMerchant`(또는 이 가족이 거래에 쓰는 AI `ProviderMerchant`)를, 없으면 이 가족이 쓰는 AI `ProviderMerchant` 중 이름이 같은 것을, 그래도 없으면 가족 `FamilyMerchant`를 만든다(`website_url` 포함, 이름이 거부되면 건너뜀). 거래에 `enrich_attribute(:merchant_id, source: "ai")` 뒤 `merchant_id`를 잠근다. (2) 거래의 가맹점이 비 AI `ProviderMerchant`이면 `website_url`이 비어 있을 때만 응답의 URL을 채우고 거래를 잠근다. (3) 그 밖(AI 가맹점, `FamilyMerchant`)은 건드리지 않는다. | 코드 확인 |
| R-57 | LLM 결과 정규화(OpenAI provider) | `category_name`을 strip해서 빈 문자열이거나 `null`(대소문자 무시)이면 nil로 본다. 사용자 카테고리 이름과 정확히 같으면 그것, 아니면 대소문자 무시로 같은 것, 아니면 "느슨한 일치"(양쪽에서 `[^a-z0-9]`를 지우고 한쪽이 다른 쪽을 포함, 또는 영어 유의어 표)로 찾은 첫 카테고리 이름을 돌려준다. 어느 것도 없으면 정규화한 문자열을 그대로 돌려준다(이후 R-53에서 이름이 안 맞아 건너뜀). 한글은 `[^a-z0-9]` 제거 뒤 빈 문자열이 되고 빈 문자열은 모든 문자열에 포함되므로 두 방향으로 오매핑된다. 응답 이름이 한글이면 카테고리 언어와 상관없이 목록의 첫 카테고리(영문 포함)가 매핑되고, 카테고리 이름이 한글이면 정확·대소문자 일치가 없는 영문 응답까지 흡수한다. "첫 번째"는 `family.categories.map` 순서이며 `order`가 없어 DB가 돌려주는 순서다. 스키마 강제(`strict`)를 쓰는 OpenAI 본가 경로는 응답 이름이 카테고리 목록 enum으로 제한되어 이 경로에 덜 도달한다. 범용(custom) provider에서는 응답 중 절반을 넘게 null이거나 빠지면 strict를 버리고 자유 형식으로 한 번 재시도한다(`AUTO_MODE_NULL_THRESHOLD` 0.5). | 코드 확인 |
| R-58 | LLM 입력 구성 | 거래 입력은 1.3 표의 5개 필드다. `amount`는 절댓값, `classification`은 부호로 정한 `income`/`expense`, `description`은 `name`과 `notes`를 비어 있지 않은 것만 공백으로 이은 값, `merchant`는 가맹점 이름이다. 가맹점 감지 호출에는 가족 `FamilyMerchant`의 `{id, name}` 목록이 같이 간다. 프롬프트는 OpenAI 본가용 `detailed_instructions`와 custom provider용 `simple_instructions` 두 벌이고 가족이 덮어쓸 수 있다. 카테고리 분류의 본가 지침(`detailed_instructions`)은 거래당 결과 하나, `transaction_id`로 대응, 가장 구체적인 하위 카테고리 우선, 모르면 `"null"`(약 60% 이상 확신할 때만 분류, 오탐보다 null 선호)이다. 본가의 응답 형태는 `json_schema`(strict)로 강제한다. custom provider용 `simple_instructions`에는 카테고리 이름을 목록과 정확히 같게 쓰고 모르면 `"null"`, 응답은 `{"categorizations": [{"transaction_id", "category_name"}]}` JSON이라는 문구가 들어 있다. 가맹점 감지의 본가 지침은 거래당 결과 하나, 서브도메인 없는 URL, 일반명사 이름은 null, 약간 비관적으로 판단이고, `simple_instructions`에는 불확실하면 `"null"`(80% 이상 확신할 때만), 응답은 `{"merchants": [{"transaction_id", "business_name", "business_url"}]}`라는 문구가 있다. | 코드 확인 |
| R-59 | AI 캐시 초기화(규칙 화면의 "AI 캐시 지우기") | 요청하면 `ClearAiCacheJob`(큐 `low_priority`)이 가족의 `Transaction`과 `Entry` 레코드마다 `clear_ai_cache`를 부른다. 레코드 하나는 행 잠금 아래에서, `ai` enrichment 중 "현재 값이 enrichment 값과 같고 `superseded`가 아닌" 속성의 잠금만 풀고(사용자가 바꾼 값은 잠금 유지), 그 레코드의 `ai` enrichment 행을 모두 지우고, 지운 게 있으면 `touch`한다. 값 자체는 되돌리지 않는다. 풀린 거래는 `category_id`/`merchant_id`가 잠기지 않아 R-52·R-56이 다시 분류·감지할 수 있다(R-53이 건 AI 잠금을 푸는 경로). 레코드 단위 오류는 모아서 보고하고 계속한다. 요청과 완료는 `DebugLogEntry`(category `ai_cache_reset`)로 남는다. | 코드 확인 |

#### 카테고리·태그·가맹점 데이터

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | `Category` 저장 | `name`, `color`, `lucide_icon`, 가족이 있어야 한다. `color`는 `#` 뒤 16진수 6자리(대소문자 무관)여야 한다. `name`은 가족 안에서 유일하다(앱 검증과 DB unique index, 둘 다 대소문자를 구분하므로 `Food`와 `food`는 서로 다른 이름, 앞뒤 공백도 다듬지 않는다). 예약값 `__uncategorized__`는 이름으로 못 쓴다. 부모는 같은 가족이어야 하고 깊이는 최대 2단계다(부모가 이미 하위 카테고리거나, 자식이 있는 카테고리가 하위 카테고리가 되려 하면 거부). 하위 카테고리는 저장 시 부모의 색을 상속하고 부모 색이 바뀌면 자식에게 전파된다. 카테고리의 수입/지출 `classification`은 폐기되어 컬럼 이름이 `classification_unused`다. | 코드 확인 |
| R-61 | `Category` 삭제·병합 | 삭제하면 그 카테고리의 거래는 `category_id`가 nil이 되고(해당 거래의 Bayes·AI enrichment는 superseded로 표시), 자식 카테고리의 `parent_id`는 nil이 된다. 병합은 원본 거래를 대상으로 옮기고 예산 항목을 합산·이관하고 원본의 자식을 대상 밑으로 옮긴 뒤 원본을 지운다. 부모를 자신의 자손에 병합하거나 자식이 있는 카테고리를 하위 카테고리로 병합하는 것, 다른 가족의 카테고리는 거부된다. 가족의 `categories_locked`가 켜져 있으면 카테고리 생성과 기본 카테고리 만들기만 막히고 수정·삭제는 된다. | 코드 확인 |
| R-62 | 기본 카테고리 만들기(`bootstrap!`) | 22개를 가족에 만든다(수입, 식음료, 식료품, 쇼핑, 교통, 여행, 엔터테인먼트, 의료, 개인 관리, 주택 개선, 모기지/월세, 공과금, 구독, 보험, 스포츠·피트니스, 선물·기부, 세금, 대출 상환, 서비스, 수수료, 저축·투자, 투자 기여금에 해당하는 이름과 색·아이콘). 이름은 현재 로케일의 번역이다. 이미 같은 이름이 있으면 새로 만들지 않는다. 화면의 "기본 카테고리 만들기" 외에, Plaid·SimpleFIN 거래 processor가 가족에 카테고리가 하나도 없을 때 자동으로 호출한다(`categories_locked`는 이 자동 호출을 막지 않는다). 한국어(`ko`)는 앱의 지원 로케일 목록과 카테고리 번역 파일에 없으므로 한국어 기본 카테고리는 없다. | 코드 확인 |
| R-63 | `Tag` 저장·삭제 | `name`은 필수이고 가족 안에서 유일하며(대소문자 구분, DB unique index도 같음) 예약값 `__untagged__`는 못 쓴다. `color`는 있으면 `#` + 16진수 6자리여야 한다(DB 기본 `#e99537`, null 불가). 삭제하면 그 태그의 `taggings`가 모두 지워진다. 다른 태그로 교체하며 삭제하면 `taggings`의 태그가 교체 태그로 바뀐다. | 코드 확인 |
| R-64 | `FamilyMerchant` 저장 | `name` 필수, 가족 안에서 유일(DB unique index는 `FamilyMerchant`에만), 예약값 `__no_merchant__` 불가. `color`는 `#` + 16진수 6자리이고 형식이 틀리거나 비면 기본 팔레트 10색 중 하나가 무작위로 들어간다. 로고는 jpeg·png·webp, 5MB 이하만 허용한다. 같은 이름이 이미 있으면 새로 만들지 않고 기존 것을 재사용하는 `find_or_create_with_name`(동시 생성 경쟁에도 안전)이 쓰인다. | 코드 확인 |
| R-65 | `ProviderMerchant` | `source`가 필수(`ai`, `plaid`, `simplefin` 등 닫힌 목록)이고 `name`은 같은 `source` 안에서 유일하다. `provider_merchant_id`와 `source`가 있으면 그 조합도 유일하다. 색을 지원하지 않는다(읽기는 항상 nil, 쓰기는 버림). `website_url`이 있고 로고가 없을 때만 Brandfetch로 로고 URL을 만든다. 여러 가족이 공유하므로 가족에서 떼는 것은 그 가족 거래의 `merchant_id`를 nil로 만들고 "최근 해제" 기록을 남기는 것이고 레코드는 지우지 않는다. | 코드 확인 |
| R-66 | 가맹점 변환·병합 | `ProviderMerchant`를 가족 `FamilyMerchant`로 바꾸면(같은 이름이 있으면 재사용) 그 가족의 거래만 새 가맹점으로 옮기고(옮기기 전에 거래 entry에 `user_modified`를 표시해 sync가 되돌리지 않게 함) 규칙의 가맹점 조건·동작 값 중 옛 id를 새 id로 바꾼다. 가맹점 병합도 같은 방식으로 거래를 옮기고 원본 `FamilyMerchant`는 지우고(`ProviderMerchant`는 남김) 규칙 참조를 바꾼다. 이때 가맹점 조건이 바뀐 이메일 규칙은 baseline을 다시 잡는다. | 코드 확인 |
| R-67 | 카테고리 변경이 자동 분류의 claim을 끝낸다 | 거래의 `category_id`가 바뀌면(저장 콜백, 또는 일괄 재배정) 그 거래의 `ai`·`bayes` 카테고리 enrichment에 `superseded: true`가 표시되어, 나중에 사용자가 같은 값으로 되돌려도 자동 분류가 맡은 것으로 다시 세지 않는다. 이 표시는 Bayes의 자기 라벨 제외(R-40)와 가맹점·카테고리 "자동 출처" 판정에 쓰인다. 사용자 편집은 `locked_attributes`로 잠기고(transactions R-13), Bayes·유사 가맹점·AI 결과는 위 규칙에 따라 잠기거나 잠기지 않는다. | 코드 확인 |

- 불변식:
  - 규칙 동작은 `ignore_attribute_locks`가 false인 한 잠긴 속성을 바꾸지 못한다. 예외는 `set_as_transfer_or_payment`(R-25)뿐이다.
  - 규칙 실행 하나에서 같은 거래의 같은 속성은 첫 claim 규칙의 값이 남는다(R-33). 단 `ignore_attribute_locks`가 true여도 claim은 그대로이고, 한 번의 실행 사이에서만 성립한다. 다음 실행에서는 아래 규칙이 값을 다시 덮어쓸 수 있다.
  - 이름·가맹점·카테고리는 한 가족의 것만 쓴다. 다른 가족의 id는 값이 되지 못한다(R-22, R-24).
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-10, R-12 | 전각 공백(U+3000)과 NBSP가 들어간 한글 가맹점명이 필드 쪽 `[[:space:]]`에서 접히는가, 값 쪽 Ruby `\s`가 ASCII 공백만 잡는다는 것이 맞는가 | 한국 은행 CSV의 전각·NBSP 공백이 규칙 `like`/`=` 결과를 바꾼다. 구현자가 공백 정규화 범위(ASCII만 / 유니코드 공백 전체)를 골라야 한다 | 대상 PostgreSQL에서 `SELECT E'　' ~ '[[:space:]]'`와 DB 로케일(`lc_ctype`)을 확인하고 Ruby에서 `"　" =~ /\s/`를 실행 |
| U-02 | R-21a, R-54 | AI 기능 가용 판정(`Ai::Router`)과 provider 선택 규칙, Jev provider의 `decide` 응답 형식 | AI 동작을 규칙 편집 화면에 노출하는 조건과 임계값이 적용되는 provider 범위. 외부 연동은 사용자가 따로 만든다고 했으므로 영향은 노출 조건에 한정된다 | `app/models/ai/router.rb`·`ai/routes`·`provider/jev.rb`를 읽는다 |
| U-03 | R-25 | `set_as_transfer_or_payment`의 변경 건수 집계(블록 반환값이 true/false가 아니어서 `previous_changes`로 대체됨)와 이미 다른 이체가 걸린 거래의 처리 | `RuleRun.transactions_modified` 숫자와 이중 이체 방지. 거래 분류 결과 자체에는 영향 없음 | `Transfer` 모델(행 3)과 `count_modified_resources`를 실제 실행 또는 테스트로 확인 |

- 확인 한계: Ruby·PostgreSQL을 이 작업 환경에서 실행하지 못했다. 정규식·공백·로케일 동작(R-12), 유사도 값(T-18), Bayes 수치(T-16)는 코드를 읽고 계산한 값이다. 유사도는 같은 식을 Python으로 옮겨 계산했다(Ruby 미실행). `Transaction::Grouper::ByMerchantOrName`(wizard 묶음)과 `Provider::Anthropic` 등 OpenAI 외 provider의 결과 정규화는 읽지 않았다. 원본 테스트는 열지 않았다.

### 1.5 필수 코드 참조

원본 라이선스의 인용 허용 여부는 [overview](./../overview.md) 1절을 따른다. 아래는 글보다 코드가 짧고 정확한 규칙이다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/rule.rb:25-42` `ordered`, 검증 선언 / `app/models/rule.rb:447-480` `min_actions`, `no_duplicate_actions`, `split_is_only_action`, `no_nested_compound_conditions` | 규칙 순서 정렬, 저장 검증, 동작·중첩 조건 제약 | R-01, R-03 |
| C-02 | `app/models/rule.rb:375-396` `matching_scope` / `app/models/rule.rb:560-566` `normalize_name` / `app/models/rule.rb:401-405` `assign_next_position` / `app/models/rule.rb:183-186` `next_position_for` | 조건 평가 순서, 정규식 있을 때 id 먼저 뽑기, 이름 정규화, position 자동 부여 | R-02, R-08 |
| C-03 | `app/models/rule.rb:291-318` `apply` | 동작별로 claim된 거래를 뺀 범위에 적용하고 비동기 결과를 합치는 방식 | R-30, R-31, R-33 |
| C-04 | `app/models/rule/runner.rb:50-88` `run_rules`, `record_claims`, `reserved_attributes` | 규칙 선택·break, claim·`stop_processing` 기록 | R-28, R-33, R-34 |
| C-05 | `app/models/rule/runner.rb:90-211` `execute`, `run_counts`, `record_failure`, `with_family_lock` | 실행 흐름, `RuleRun` 계수, 실패 처리, advisory lock | R-29~R-32 |
| C-06 | `app/models/rule/registry/transaction_resource.rb:1-100` | 조건 10종·동작 13종 등록 순서, 매칭 범위, AI 동작 노출 | R-07, R-20, R-21a |
| C-07 | `app/models/rule/condition.rb:15-23` 검증 / `app/models/rule/condition.rb:54-75` `regex?`, `apply` / `app/models/rule/condition.rb:133-143` `build_compound_scope` | 조건 검증, `compound` and/or | R-04, R-09 |
| C-08 | `app/models/rule/condition_filter.rb:6-40` 연산자 목록 / `app/models/rule/condition_filter.rb:107-181` `build_sanitized_where_condition`, `sanitize_operator`, `normalize_value`, `normalize_field` | 연산자 문자열→SQL, 값·필드 정규화, NULL 처리 | R-10, R-11, R-17 |
| C-09 | `app/models/rule/condition_filter/transaction_name.rb:22-88` | Plaid 이름 호환 `=`/`!=` | R-13 |
| C-10 | `app/models/rule/condition_filter/transaction_amount.rb:1-14` / `transaction_type.rb:1-37` / `transaction_tag.rb:1-47` / `transaction_details.rb:1-54` / `transaction_additional_detail.rb:1-99` / `transaction_category.rb:1-18` / `transaction_merchant.rb:1-18` / `transaction_account.rb:1-14` / `transaction_notes.rb:1-14` / `unsupported.rb:1-22` (모두 `app/models/rule/condition_filter/` 아래) | 필터별 SQL | R-06, R-14~R-19 |
| C-11 | `app/models/rule/safe_regex.rb:20-104` | 정규식 길이·역참조·컴파일 프로브·실행 timeout | R-20a, R-20b |
| C-12 | `app/models/rule/action.rb:69-101` `value=`, 쉼표 값, `apply` / `app/models/rule/action.rb:114-121` claim / `app/models/rule/action.rb:150-152` `execution_value` | 다중 값 저장·해석 | R-20, R-33 |
| C-13 | `app/models/rule/action_executor.rb:36-56` `claimed_attributes`, `reserves_claimed_attributes?`, `actionable?` / `app/models/rule/action_executor.rb:82-105` `count_modified_resources` | claim 계약, 변경 건수 집계 | R-31, R-33 |
| C-14 | `app/models/rule/action_executor/set_transaction_category.rb:1-38` / `set_transaction_tags.rb:1-40` / `set_transaction_merchant.rb:1-66` / `set_transaction_name.rb:1-40` / `set_investment_activity_label.rb:1-40` / `exclude_transaction.rb:1-31` | 단일 속성 동작의 잠금 검사·값 검증 | R-21~R-24 |
| C-15 | `app/models/rule/action_executor/set_as_transfer_or_payment.rb:1-56` / `send_email_notification.rb:1-35` | 이체 동작, 이메일 동작 | R-25, R-27 |
| C-16 | `app/models/rule/action_executor/split_transaction.rb:5-11` 상수 / `:44-93` `execute` / `:100-161` `config_errors` / `:196-203` `amount_precision` / `:230-298` `build_splits` / `:334-341` `parse_decimal` | 분할 설정 검증, 금액 계산 알고리즘, 건너뛰기 | R-26 |
| C-17 | `app/models/rule/action_executor/fill_similar_merchants.rb:1-20` / `bayes_categorize.rb:1-20` / `auto_categorize.rb:30-73` / `auto_detect_merchants.rb:10-46` | AI·Bayes·유사 가맹점 동작의 claim 설정과 배치 큐잉 | R-33, R-44, R-48, R-52, R-56 |
| C-18 | `app/models/rule/action.rb:154-222` `build_split_value`, `split_config_valid`, `exact_amount_condition_value` | 순수 fixed 분할의 `amount =` 조건 요건 | R-26 |
| C-19 | `app/models/family/bayes_categorizer.rb:14-41` 상수·`Result` / `:54-111` `enough_training_data?`, `classify`, `classify_and_apply` / `:113-204` 토큰·학습 데이터 / `:206-369` 점수식 | 학습 가드, 토큰화, 점수·softmax, 적용 | R-40~R-45 |
| C-20 | `app/models/family/bayes_settings.rb:9-87` `DEFAULTS`, `CHOICES`, `STEPS`, `RANGES` / `:91-125` 생성·`to_stored`·`digest`·`coerce` | Bayes·유사 가맹점 설정 키·기본값·범위 | R-40~R-48 |
| C-21 | `app/models/family/similar_matcher.rb:10-109` | 유사도 알고리즘 전체 | R-49, R-50 |
| C-22 | `app/models/family/similar_merchant_filler.rb:14-70` | 채움 대상·풀·적용 | R-48, R-51 |
| C-23 | `app/models/family/auto_categorizer.rb:9-113` `auto_categorize` / `:156-171` `withhold?` / `:246-267` 입력 구성 / `:309-313` `scope` | LLM 카테고리 적용 규칙 | R-53, R-54, R-58 |
| C-24 | `app/models/family/auto_merchant_detector.rb:9-59` `auto_detect` / `:93-164` 입력·매칭·생성 | LLM 가맹점 감지 규칙 | R-56, R-58 |
| C-25 | `app/models/family.rb:418-426` 설정 접근 / `:442-475` `bayes_categorize_uncategorized`, `fill_similar_merchants` / `:480-509` 분류 규칙 관리 / `:515-524` `clear_bayes_locks!` / `:893-901` `add_classifier_rules`, `categorizable_transactions` | Family 단위 진입점, 기본 규칙 두 개 | R-38, R-44, R-47, R-48 |
| C-26 | `app/jobs/apply_rules_job.rb:1-16` / `apply_all_rules_job.rb:1-14` / `rule_job.rb:1-27` / `bayes_categorize_job.rb:1-11` / `auto_categorize_job.rb:1-14` / `auto_detect_merchants_job.rb:1-14` | 트리거 job과 재시도·실패 정책 | R-29, R-32, R-37 |
| C-27 | `app/models/concerns/enrichable.rb:20-25` `enrichable` scope / `:63-147` `enrich_attributes` / `:149-169` 잠금 | 잠금 필터·갱신·출처 기록 | R-21 |
| C-28 | `app/models/transaction.rb:82-121` 상수(`TRANSFER_KINDS`, `UNCATEGORIZED_EXCLUDED_KINDS`, `ACTIVITY_LABELS`) / `:229-262` `category_from`, `enriched_from_sql`, `supersede_automatic_category_claims!` / `:276-306` `reassign_category!` | 이체 종류·라벨 목록, 자동 출처 판정, superseded | R-15, R-24, R-44, R-67 |
| C-29 | `app/models/category.rb:22-38` 검증·콜백 / `:53-59` 색상 상수 / `:322-347` `default_categories` / `:350-352` `inherit_color_from_parent` / `:438-456` 깊이 검증 | 카테고리 제약 | R-60, R-62 |
| C-30 | `app/models/tag.rb:12-23` / `app/models/merchant.rb:1-43` / `app/models/family_merchant.rb:14-36` / `app/models/provider_merchant.rb:3-10` / `:78-114` `convert_to_family_merchant_for` / `:133-145` `unlink_from_family` | 태그·가맹점 제약과 변환 | R-63~R-66 |
| C-31 | `app/models/provider/openai/auto_categorizer.rb:239-298` `build_response`, `normalize_category_name`, `find_fuzzy_category_match` / `:451-480` `json_schema` | LLM 결과 정규화·스키마 | R-57 |
| C-32 | `app/models/provider/llm_concept.rb:1-19` 계약과 `max_items_per_call` / `app/models/provider/classification_concept.rb:1-45` `CategoryDecision` | provider 입출력 계약 | R-52, R-54 |
| C-33 | `app/models/family/ai_settings.rb:14-17` / `:28-31` / `:44-59` / `:61-86` | provider 선택·임계값·shadow 설정 | R-54 |
| C-34 | `app/controllers/rules_controller.rb:47-68` `create`, `apply` / `:136-139` `apply_all` / `:243-260` `rule_params` | 트리거와 허용 파라미터 | R-36, R-37 |
| C-35 | `app/controllers/settings/classifiers_controller.rb:23-65` | Classifier 설정·스위치·Run | R-37, R-38, R-46 |
| C-36 | `app/models/category/merger.rb:21-91` / `app/models/merchant/merger.rb:21-62` | 병합 | R-61, R-66 |
| C-37 | `app/models/rule.rb:258-269` `create_from_grouping` / `app/controllers/transactions/categorizes_controller.rb:24-42` | wizard가 규칙을 만드는 호출 경계 | R-39 |
| C-38 | `db/schema.rb:2336-2350` `rules` / `db/schema.rb:2287-2294` `rule_actions` / `db/schema.rb:2296-2306` `rule_conditions` / `db/schema.rb:2318-2334` `rule_runs` / `db/schema.rb:406-419` `categories` / `db/schema.rb:2774-2782` `tags` / `db/schema.rb:1691-1707` `merchants` / `db/schema.rb:597-607` `data_enrichments` | 컬럼 기본값·유일 index | R-02, R-60~R-65 |
| C-39 | `app/models/family/syncer.rb:22-28` `perform_post_sync` | post-sync가 `ApplyRulesJob`을 큐에 넣는 지점 | R-37 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않음). 수치는 코드를 읽고 계산한 값이며, 유사도 값은 Python으로 옮겨 계산했다(Ruby 미실행).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10, R-11 | 거래 `name`이 `"스타벅스  강남점"`(공백 2칸). 조건 `transaction_name like "  스타벅스 강남점 "`. | 값은 `"스타벅스 강남점"`으로, 필드는 공백 1칸으로 접혀 매칭된다. |
| T-02 | R-11, R-12 | `name = "Starbucks Gangnam"`. 조건 `like "starbucks"`와 `= "starbucks gangnam"`을 각각 평가. | `like`는 매칭, `=`는 대소문자가 달라 매칭되지 않는다. |
| T-03 | R-12 | 거래 `name`이 NFD로 저장된 `"스타벅스"`(자모 분리), 조건 `like "스타벅스"`(NFC). | 정규화가 없어 매칭되지 않을 것으로 본다(추론). |
| T-04 | R-11 | `notes`가 빈 문자열인 거래, 조건 `transaction_notes is_null`. | 매칭되지 않는다(`""`는 NULL이 아님). |
| T-05 | R-14 | 규칙 `transaction_amount > 10000`. 거래 A: KRW `-15000`, B: USD `12000`, C: KRW `9999`. | A, B 매칭, C 제외(통화 환산 없음, 부호 무시). |
| T-06 | R-15 | 조건 `transaction_type = expense`. 거래 `amount = 0`, `kind = standard`. | 매칭된다(0원은 expense). |
| T-07 | R-18 | 거래 X에 태그 a, b, 거래 Y에 태그 a만. 조건 `tag = a` AND `tag = b`. | X만 매칭. 조건 `tag != b`는 Y와 태그 없는 거래가 매칭. |
| T-08 | R-19 | `extra = {"redbark": {"merchant_category_code": "5411"}}`. 조건 `additional_detail = "merchant_category_code=5411"` / `"merchant_category_code"` / `"merchant_category_code=5812"`. | 첫째·둘째 매칭, 셋째 불일치. `"merchant_category_code": null`이어도 둘째는 매칭. |
| T-09 | R-20a | 패턴 `(a)\1` / 201자 패턴 / `(` / `\\1` 저장. | 순서대로 `backreference`, `too_long`, `invalid`로 거부, 마지막(`\\1`)은 역슬래시와 `1`이라 통과. |
| T-10 | R-30, R-33 | 규칙1(position 1) `name like "스타벅스"` → 카테고리 `식비`, 규칙2(position 2) 같은 조건 → 카테고리 `카페` + 태그 `a`. 거래 `"스타벅스 강남점"`, 잠금 없음, 활성 두 규칙 모두 ApplyRulesJob 실행. | 카테고리는 `식비`(규칙2는 category를 claim당한 거래라 건너뜀), 태그 `a`는 붙는다(태그는 claim 대상 아님). |
| T-11 | R-34 | 규칙1 `stop_processing` 켜짐, 조건 `name like "스타벅스"`, 동작 태그 `a`. 규칙2는 같은 조건에 카테고리 `카페`. | `"스타벅스 …"` 거래는 규칙2 대상에서 빠져 카테고리가 비어 있다. |
| T-12 | R-21 | 거래의 `category_id`가 잠겨 있고 값은 `식비`. 규칙이 `카페`로 바꿈. 동기화 뒤 ApplyRulesJob / 사용자 "Apply". | ApplyRulesJob은 바꾸지 않고, "Apply"는 `카페`로 덮어쓴다. 어느 쪽도 규칙이 새로 잠그지는 않는다. |
| T-13 | R-26 | `split_transaction` 설정 `fixed 6000 "식비"`, `fixed 4000 "간식"`. 조건에 `amount = 10000`이 없다. 같은 설정에 AND 조건 `amount = 10000`을 넣는다. | 앞은 `fixed_requires_exact_amount_condition`로 거부, 뒤는 저장. KRW `10000` 거래는 6000·4000, 수입 거래 `-10000`은 `-6000`, `-4000`(부호 유지). |
| T-14 | R-26 | 설정 `percentage 30`, `percentage 70`, KRW `10001`(자릿수 0). | 첫 행 `(10001×30/100).round(0) = 3000`, 마지막 행은 잔액 `7001`. 합 10001. |
| T-15 | R-26 | 설정 `fixed 2000`, `percentage 100`, 거래 KRW `1500`. | `fixed`가 총액을 넘어 `remaining ≤ 0`이므로 그 거래는 건너뛰고 `unresolvable_split_amounts`를 로그에 남긴다. |
| T-16 | R-42~R-44, R-45 | 학습 20건: `"스타벅스 강남점"` 10건 카테고리 A, `"GS25 역삼점"` 10건 카테고리 B. 기본 설정(`word_split: ascii`)과 `unicode` 설정에서 `"스타벅스 서초점"`을 분류. | `ascii`: 토큰 없음이라 `nil`(채워지지 않음). `unicode`: 알려진 토큰은 `스타벅스`뿐이고 A의 확률 `(10+1)/(20+4) = 11/24`, B는 `1/24`, softmax 후 A `0.9167`로 임계값 0.7 이상이라 A로 채우고 enrichment metadata의 confidence는 `0.917`. |
| T-17 | R-41 | 학습 거래 19건, 카테고리 2개. | `classify`가 nil. 학습 20건에 카테고리 1개여도 nil. |
| T-18 | R-49, R-50 | 풀(가맹점 M1) `"스타벅스 강남점"`, `"스타벅스 서초점"`, 풀(M2) `"GS25 역삼점"`. 대상 `"스타벅스 강남역점 7782"`를 기본 설정으로 채운다. | 유사도는 약 0.72, 0.52, 0이라 임계값 0.9 미만이고 이웃이 없어 가맹점을 채우지 않는다. 임계값 0.7, `min_neighbours` 1이어도 이웃은 첫 거래 하나뿐이라 M1을 쓴다(이 조합에서만 채워짐). |
| T-19 | R-53 | LLM이 카테고리 `"식비"` 응답, 가족 카테고리 `식비` 존재. 다른 거래는 `"음식"` 응답(가족 카테고리에 없음, 응답 처리 단계에서 정규화되지 못한 상태), 다른 거래는 `null`. | 첫 거래: `category_id` 적용 + 잠금. 두 번째 거래: 이름 불일치로 건너뜀. 세 번째: 건너뜀. |
| T-20 | R-57 | 사용자 카테고리 `["식비", "교통"]`, 범용 provider가 `"음식"` 응답. | 정확·대소문자 일치가 없고, 한글은 `[^a-z0-9]` 제거로 빈 문자열이 되어 포함 검사가 참이라 첫 카테고리 `"식비"`로 매핑된다. 사용자 카테고리가 `["Food", "식비"]`(`family.categories` 반환 순서)이고 응답이 한글 `"음식"`이면 `"Food"`로 매핑된다. |
| T-21 | R-54 | `confidence_threshold = 0.7`, 분류 provider가 `confidence 0.62`로 `교통`을 응답. | 적용·잠금하지 않고 "withheld"로 로그에만 남으며 거래는 다음 실행 대상으로 남는다. LLM provider 응답은 신뢰도가 없어 같은 임계값이어도 적용된다. |
| T-22 | R-56 | 거래에 비 AI `ProviderMerchant`가 이미 있고 `website_url`이 비어 있다. LLM이 `business_name = "스타벅스"`, `business_url = "starbucks.co.kr"` 응답. | 가맹점의 `website_url`만 채워지고 거래의 `merchant_id`는 그대로이며 `merchant_id`가 잠긴다. 거래에 가맹점이 없었다면 가족 `FamilyMerchant "스타벅스"`를 찾거나 만들어 `source: ai` enrichment로 붙이고 잠근다. |
| T-23 | R-01 | 규칙에 `split_transaction`과 `set_transaction_category`를 같이 넣거나, 같은 `action_type`을 두 번 넣거나, 동작 0개로 저장. | 세 경우 모두 저장 거부. 조건 0개 규칙은 저장되고 범위 전체가 매칭된다. |
| T-24 | R-60 | 카테고리 `식비` 두 번 생성 / 부모→자식→손자 생성 / 색 `#fff` / 이름 `__uncategorized__`. | 모두 거부. `food`와 `Food`는 둘 다 생성된다. |
| T-25 | R-32, R-33, R-34 | (a) 규칙 5개 중 3번째가 매칭 단계에서 실패(`matches_regex`가 5초 초과, 지원하지 않는 연산자, 잘못된 uuid). (b) 3번째가 매칭은 성공하고 동작 단계에서 예외. | (a) 3번째 `RuleRun`은 `failed`, `transactions_queued = 0`이고 claim·`stop_processing`이 비어 있어 4·5번째는 3번째가 맞췄을 거래에도 제한 없이 적용된다. (b) 3번째 `RuleRun`은 `failed`이지만 매칭 집합의 claim·`stop_processing`은 유지되어 4·5번째는 그 거래의 claim된 속성을 건드리지 못한다. 두 경우 모두 4·5번째는 정상 실행된다. |
| T-26 | R-29 | 한 가족의 규칙 실행 중 같은 가족의 `ApplyRulesJob`이 또 시작. | 뒤 job은 `LockBusy`로 30초 뒤 다시 시도하고 총 20회까지 시도한다(재시도 19회). |
| T-27 | R-38 | 새 가족을 만든다. | position 1 `fill_similar_merchants`, position 2 `bayes_categorize`, 둘 다 조건 없음·활성. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

기준은 모두 `repos/sure@1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a`다. "없다·전부" 주장은 확인 방법 칸에 검색 명령과 범위를 적는다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, `app/validators/database_text_validator.rb:1-20` | 코드 확인. "같은 규칙의 중복은 막지 않는다"는 부재 주장이다. `app/models/rule.rb`의 검증 선언 전체(`validates`, `validate`)를 읽었고 uniqueness가 없고 `db/schema.rb:2336-2350`에 unique index가 없다. 범위는 `app/models/rule.rb`·`db/schema.rb`이고 DB 트리거나 마이그레이션은 보지 않았다. |
| R-02 | C-02, C-38 | 코드 확인. |
| R-03 | C-01, `app/models/rule/layout.rb:1-143`, `app/models/rule_group.rb:1-46` | 코드 확인. |
| R-04, R-05 | C-07, `app/models/rule/condition.rb:125-131` | 코드 확인. "연산자 유효성을 저장 때 검사하지 않는다"는 부재 주장이다. `app/models/rule/condition.rb`의 `validates`·`validate`와 `app/controllers/rules_controller.rb`의 `rule_params`를 읽었다. 가져오기(`RuleImport`)는 읽지 않았다. |
| R-06 | C-10(`unsupported.rb`), `app/models/rule/condition.rb:105-109` | 코드 확인. |
| R-07 | C-06 | 코드 확인. `Entry.visible`(`app/models/entry.rb:89-91`), `Entry.excluding_split_parents`(`:144-150`), `Entryable.visible`(`app/models/entryable.rb:17`)을 같이 읽었다. `excluded` 거래를 거르지 않는다는 것은 `resource_scope`에 `excluded` 조건이 없음을 읽은 것이다. |
| R-08 | C-02 | 코드 확인. |
| R-09 | C-07 | 코드 확인. |
| R-10, R-11 | C-08 | 코드 확인. |
| R-12 | C-08, `app/models/rule/condition_filter.rb:170-179`. "유니코드 정규화가 없다"는 부재 주장이다. | `grep -rn "unicode_normalize\|I18n.transliterate\|NFC\|NFKC" app lib --include=*.rb`(범위: `app/`, `lib/`의 `.rb`)에서 규칙·분류 코드에 없고, 결과는 `app/controllers/oauth_registration_controller.rb`의 앱 이름 검사뿐이다. 동적 호출·DB 쪽 정규화는 보지 않았다. 값 쪽 `\s`가 ASCII 공백만 잡고 필드 쪽 `[[:space:]]`가 로케일 의존이라는 것은 언어·DB 문서 지식이라 `추론`이다(U-01). |
| R-13 | C-09, `app/models/plaid_entry/processor.rb:6-7` | 코드 확인(`NAME_SEPARATOR = " - "`, `SOURCE = "plaid"`). |
| R-14 | C-10(`transaction_amount.rb`), C-08 | 코드 확인. 환율 환산이 없다는 것은 `transaction_amount.rb`에 통화 관련 코드가 없음을 읽은 것이다. |
| R-15 | C-10(`transaction_type.rb`), C-28 | 코드 확인. |
| R-16 | C-10(`transaction_category.rb`, `transaction_merchant.rb`, `transaction_account.rb`), C-08 | 코드 확인. 잘못된 uuid가 DB 오류가 된다는 것은 `categories.id`가 uuid 컬럼이라는 `db/schema.rb:406`에서 추론했고 실행하지 않았다. |
| R-17 | C-08(`sanitize_operator`), C-10(`transaction_tag.rb`) | 코드 확인. |
| R-18 | C-10(`transaction_tag.rb`) | 코드 확인. |
| R-19 | C-10(`transaction_details.rb`, `transaction_additional_detail.rb`) | 코드 확인. |
| R-20a, R-20b | C-11, C-07(`regex_value_is_safe`, `regex_value_changed?`), C-26(`rule_job.rb`) | 코드 확인. `affected_resource_count`·`matches_transaction?`의 timeout 처리는 `app/models/rule.rb:136-140`, `:246-250`. |
| R-20 | C-12, `app/models/rule/action.rb:84-97` | 코드 확인. |
| R-21a | C-06, `app/models/rule/action.rb:135-137` | 코드 확인. `offered?`는 `existing_action?(...) || 가용 판정`(`transaction_resource.rb:76-88`)이고 저장된 AI 동작은 `rule.actions`에 있어 항상 노출 조건을 통과한다. `Ai.available?`는 `app/models/ai.rb:11-17`에서 `Ai::Router`로 위임한다는 것만 읽었다(U-02). |
| R-21 | C-27, C-14, C-13 | 코드 확인. "규칙 동작은 속성을 잠그지 않는다"는 부재 주장이다. `grep -rn "lock_attr!\|lock_saved_attributes!" app lib --include=*.rb`(범위: `app/`, `lib/`의 `.rb`)에서 `app/models/rule/` 아래에는 호출이 없다. 분할 동작은 `split_once!(…, lock_attributes: true)`를 통해 잠근다. 호출자 목록은 컨트롤러·`entry.rb`·`family/auto_*`·`bayes_categorizer.rb`·`similar_merchant_filler.rb` 등이다. 매크로·동적 호출은 보지 않았다. |
| R-22~R-24 | C-14 | 코드 확인. |
| R-25 | C-15 | 코드 확인. 건수 집계는 `count_modified_resources`(C-13)의 대체 경로를 읽은 것에서의 추론이라 U-03이다. |
| R-26 | C-16, C-18, C-15 | 코드 확인. `split_once!`의 동작은 transactions 스펙 C-02에 있고 호출 인자만 확인했다. | `splittable?`은 `app/models/transaction/splittable.rb:4-6`, `split_once!`의 재확인은 `app/models/entry.rb:573-580`.
| R-27 | C-15, `app/models/rule.rb:44-72`, `:535-554` | 코드 확인. |
| R-28~R-34 | C-03, C-04, C-05, C-26 | 코드 확인. |
| R-35, R-36 | C-34 | 코드 확인. "규칙 생성·수정이 실행을 부르지 않는다"는 부재 주장이다. `grep -rn "apply_later\|RuleJob\|ApplyRulesJob\|ApplyAllRulesJob\|BayesCategorizeJob\|Rule::Runner" app lib config --include=*.rb --include=*.yml --include=*.erb --include=*.rake`(범위: `app/`, `lib/`, `config/`)의 job 호출처는 `rules_controller.rb:66`, `:137`, `classifiers_controller.rb:58`, `assistant/function/apply_rule.rb:107`, `rule.rb:321`, `family/syncer.rb:27`, `financekit/downstream.rb:54`이고, `Rule::Runner`를 job 없이 직접 부르는 곳은 `lib/tasks/rules.rake:3-41`(`rules:apply_all`, R-37 (f))이다. `config/*.yml` 스케줄러에는 규칙 호출이 없다. `bin/`과 외부 cron은 보지 않았다. |
| R-37 | C-26, C-34, C-35, C-39, sync-pipeline R-11·R-15 | 코드 확인. |
| R-38 | C-25, `app/models/family.rb:178` `after_create_commit :add_classifier_rules` | 코드 확인. |
| R-39 | C-37 | 코드 확인. `Transaction::Grouper`는 읽지 않았다. |
| R-40~R-44 | C-19, C-20, C-25 | 코드 확인. 점수 식은 코드를 그대로 옮겼고 T-16의 수치는 직접 계산했다. |
| R-45 | C-19(`word_tokens`), C-20(`word_split: "ascii"`) | 코드 확인. 한글이 `[a-z0-9]+`에 걸리지 않는다는 것은 정규식 의미에서 직접 도출했다. |
| R-46 | C-20, C-35 | 코드 확인. |
| R-47 | C-25(`clear_bayes_locks!`), `app/models/family.rb:906-912` | 코드 확인. |
| R-48 | C-22, C-25, C-17(`fill_similar_merchants.rb`) | 코드 확인. |
| R-49, R-50 | C-21 | 코드 확인. T-18의 값은 같은 식을 Python으로 옮겨 계산한 근사값이다. |
| R-51 | C-22 | 코드 확인. |
| R-52 | C-17(`auto_categorize.rb`), C-32 | 코드 확인. 배치 크기는 `llm_concept.rb:5-7`. |
| R-53 | C-23, C-26(`auto_categorize_job.rb`) | 코드 확인. |
| R-54 | C-23, C-33, `db/schema.rb:857-862`, `:888-890` | 코드 확인. `family/ai_settings.rb:61-67` 주석은 "Zero … is the default"라고 하지만 DB 기본은 0.7이다. 구현(DB 기본)을 사실로 썼다. |
| R-55 | `app/models/provider/openai.rb:221-258`, `:519-525` | 코드 확인. `BatchSlicer` 내부는 읽지 않았다. |
| R-56 | C-24, C-17(`auto_detect_merchants.rb`), C-26 | 코드 확인. |
| R-57 | C-31 | 코드 확인. 한글 이름의 느슨한 일치 동작은 코드의 정규식 의미에서 도출했고 실행하지 않았다. OpenAI 본가 경로가 enum으로 제한한다는 것은 `json_schema`(C-31)에서 읽었다. |
| R-58 | C-23, C-24, `app/models/provider/openai/auto_categorizer.rb:43-90`, `app/models/provider/openai/auto_merchant_detector.rb:42-100`, `app/models/entry.rb:359-361` | 코드 확인. 프롬프트 문구 전체는 범위 밖이라 필수 요소만 옮겼다. |
| R-59 | `app/controllers/rules_controller.rb:141-144`, `app/jobs/clear_ai_cache_job.rb:12-40`, `app/models/concerns/enrichable.rb:172-215` | 코드 확인. `Transaction`·`Entry` 둘 다 `CLEARABLE_MODELS`에 있고 `Enrichable`을 포함한다. 레코드 단위 로직은 `enrichable.rb`에서 읽었고 job의 요약·오류 수집은 앞부분만 읽었다. |
| R-60 | C-29, C-38 | 코드 확인. 대소문자 구분은 앱 검증이 기본값(대소문자 구분)이고 DB index가 일반 컬럼 index라는 것에서 도출했다. |
| R-61 | C-29, C-36, `app/controllers/categories_controller.rb:91-141`, `:148-157` | 코드 확인. |
| R-62 | C-29, `app/helpers/languages_helper.rb:158-180`, `config/locales/models/category/` | `ls config/locales/models/category/`에 `ko.yml`이 없고 `SUPPORTED_LOCALES`에 `ko`가 없다. 범위는 이 두 위치이고 다른 번역 경로는 보지 않았다. |
| R-63 | C-30 | 코드 확인. |
| R-64, R-65 | C-30, C-38 | 코드 확인. |
| R-66 | C-30, C-36, `app/models/rule.rb:192-213` | 코드 확인. |
| R-67 | C-28, `app/models/transaction.rb:30-31` | 코드 확인. |
| T-01~T-27 | 관련 R-ID의 근거 | 구현에서 도출. T-03(NFD), T-18의 수치, T-20, T-21은 실행하지 않은 계산·추론이다. |

### 2.2 코드 읽는 순서

1. `app/models/rule/registry/transaction_resource.rb`: 조건·동작 등록과 매칭 범위.
2. `app/models/rule/runner.rb`와 `app/models/rule.rb#apply`: 실행 순서, claim, `stop_processing`.
3. `app/models/rule/condition_filter.rb`와 `condition_filter/*`: 연산자와 한글 문자열 비교.
4. `app/models/rule/action_executor/*`: 동작별 효과.
5. `app/models/family.rb`(Bayes·유사 가맹점 진입점)에서 `family/bayes_categorizer.rb`, `family/similar_matcher.rb`로.
6. LLM은 `auto_categorize.rb` 동작에서 `family/auto_categorizer.rb`, `provider/openai/auto_categorizer.rb` 순서.

원본의 구현 전략: 규칙 매칭은 거래 필터를 SQL `WHERE`로 구성해 DB가 매칭하고, Bayes와 유사도는 메모리에 학습 집합을 올려 Ruby에서 계산하며, LLM 동작은 비동기 job으로 배치 처리한다.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-03이 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: R-ID 약 70개 중 약 55개가 일치했고 C-01~C-39 전체를 대조했다. Bayes(T-16)·유사도(T-18)·AI 임계값 0.7을 재계산했다. 중요 오류 5건(R-32~R-34 실패 시 claim, R-20, R-26, R-35·R-37 호출처, R-57), 사소 8건, 누락 3건이 나왔다. 작성자가 전부 반영해 R-59를 새로 넣었다.
- **메인 표본 점검**: R-33·R-34(`rule/runner.rb:90-97,124-129`, 매칭 단계 오류에서 `matched_ids`가 비어 claim이 비어 있음), R-26(`transaction/splittable.rb:4-6`), R-37(`lib/tasks/rules.rake:3-39`)을 원본에서 직접 확인했다. R-20은 작성자가 `offered?`를 다시 읽어 확정했다.
- **대조하지 못한 것**: 전각·NBSP 공백(Ruby `\s`, PostgreSQL `[[:space:]]`, U-01), `Ai.available?`와 Jev provider(U-02), `previous_changes` 건수 집계(U-03), `bin/`과 외부 cron의 규칙 실행 경로, 규칙 import(`RuleImport`).
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-12 | 규칙 비교 전에 이름·값을 NFC로 정규화하고 공백 정규화 범위에 U+3000·NBSP를 넣을지 결정한다 | 한국 은행·카드 CSV는 전각·NBSP 공백이나 조합형 한글이 섞일 수 있고, 원본은 이를 처리하지 않는다 | T-03이 매칭으로 바뀐다. U-01을 닫은 뒤 결정 |
| R-42, R-45 | Bayes 한글 기본값으로 `word_split`을 `unicode`(또는 `symbols`)로 두고, 필요하면 한글 음절 2~3-gram을 토큰으로 쓴다 | 원본 기본값 `ascii`는 한글 이름을 토큰 0개로 만들어 한글 거래를 분류하지 못하고, 공백 없는 한글 이름은 형태소 분석 없이 한 덩어리가 된다 | T-16의 `ascii` 결과가 바뀐다 |
| R-57 | 응답이나 카테고리 이름이 한글이어도 느슨한 일치가 첫 카테고리로 오매핑되지 않게 한다(빈 문자열 포함 검사 제거 또는 비-ASCII 정규화) | 원본은 `[^a-z0-9]` 제거 뒤 빈 문자열이 "포함"이 되어 한글 카테고리 이름에서 오분류한다 | T-20이 "적용하지 않음"으로 바뀐다 |
| R-14 | 금액 조건에 통화 조건을 두거나 기준 통화로 환산한다 | 원본은 통화를 보지 않아 KRW와 외화에 같은 임계값이 적용된다 | T-05의 B가 제외될 수 있다 |
| R-13, R-27 | Plaid 이름 호환과 이메일 알림 baseline은 구현하지 않아도 된다 | KB국민 CSV 등 외부 연동을 사용자가 따로 만들고 provider `plaid`·메일은 쓰지 않는다 | R-13의 `source = 'plaid'` 분기와 R-27 삭제 |
| R-62 | 한국어 기본 카테고리 세트를 정의한다 | 원본에는 `ko` 번역이 없다 | 기본 카테고리 목록(이름·색·아이콘)을 새로 정해야 한다 | 자동 호출: `app/models/plaid_account/transactions/processor.rb:30-36`, `app/models/simplefin_account/transactions/processor.rb:63-69`(둘 다 `categories.none?`일 때 `bootstrap!`).
