---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-18
updated: 2026-11-18
sources:
  - app/models/import.rb
  - app/models/import/row.rb
  - app/models/import/mapping.rb
  - app/models/import/category_mapping.rb
  - app/models/import/account_mapping.rb
  - app/models/import/tag_mapping.rb
  - app/models/import/account_type_mapping.rb
  - app/models/import/preflight.rb
  - app/models/import_session.rb
  - app/models/import_source_mapping.rb
  - app/models/transaction_import.rb
  - app/models/trade_import.rb
  - app/models/account_import.rb
  - app/models/mint_import.rb
  - app/models/actual_import.rb
  - app/models/ynab_import.rb
  - app/models/category_import.rb
  - app/models/merchant_import.rb
  - app/models/rule_import.rb
  - app/models/qif_import.rb
  - app/models/monarch_import.rb
  - app/models/sure_import.rb
  - app/models/pdf_import.rb
  - app/models/account_statement.rb
  - app/models/account_statement/account_matcher.rb
  - app/models/account_statement/metadata_detector.rb
  - app/models/account/provider_import_adapter.rb
  - app/models/family/data_exporter.rb
  - app/controllers/imports_controller.rb
  - app/controllers/import/uploads_controller.rb
  - app/controllers/import/configurations_controller.rb
  - app/controllers/import/cleans_controller.rb
  - app/controllers/import/confirms_controller.rb
  - app/controllers/import/mappings_controller.rb
  - app/controllers/import/rows_controller.rb
  - app/controllers/import/qif_category_selections_controller.rb
  - app/controllers/account_statements_controller.rb
  - app/controllers/api/v1/imports_controller.rb
  - app/controllers/api/v1/import_sessions_controller.rb
  - app/controllers/concerns/import_guest_guardable.rb
  - app/jobs/import_job.rb
  - app/jobs/import_session_job.rb
  - app/jobs/revert_import_job.rb
  - app/jobs/process_pdf_job.rb
  - app/jobs/sync_cleaner_job.rb
  - app/models/family_export.rb
  - app/models/family.rb
  - app/models/entry.rb
  - config/routes.rb
  - db/schema.rb
depends:
  - ./transactions.md
  - ./investments-securities.md
  - ./money-currency-rules.md
  - ./provider-import-adapter.md
status: draft
---

# 가져오기 (Import)와 계정 명세서 보관 (statement vault)

> 사용자가 올린 CSV·NDJSON·QIF·PDF 파일을 행으로 풀어 열 매핑·정리·확인을 거친 뒤 거래·매매·계정·분류·태그·가맹점·규칙으로 한 번에 게시(publish)하고, 게시를 되돌리고(revert), 멈춘 작업을 정리하며, 계정 명세서 파일을 계정에 자동으로 짝지어 보관하는 규칙을 정의한다.

이 문서에서 쓰는 이름은 다음과 같다. `Import`는 파일 하나의 가져오기 작업 한 건이고 `type`(서브클래스)이 파일 형식을 정한다. `row`는 파일의 한 줄을 문자열 필드로 풀어 저장한 `Import::Row`다. `mapping`은 파일 안의 값(계정 이름, 카테고리 이름, 태그 이름)을 내부 레코드에 짝짓는 `Import::Mapping`이다. 게시(publish)는 `Import`의 행을 실제 `Entry`·`Account` 등으로 만드는 단계다. 부호는 [money-currency-rules](./money-currency-rules.md) R-36(음수 = 유입)을 따른다.

KB국민은행·카드 CSV는 이 문서의 CSV 경로(`TransactionImport`)로 들어간다. 따라서 CSV 공통 파이프라인(R-03~R-28)과 한국 사용 관점 값(1.4 "한국 CSV" 구역, T-01~T-10)이 핵심이다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

KB국민은행 거래내역 CSV를 `TransactionImport`로 가져오는 대표 흐름이다. 정확한 기준은 1.4다.

1. 사용자가 파일을 올린다. 서버가 크기(10MB)와 MIME type을 확인하고 `raw_file_str`에 저장하며 인코딩을 UTF-8로 바꾼다(R-03, R-04, R-06).
2. 사용자가 구분자, 열 이름, 날짜 형식, 숫자 형식, 부호 전략, 건너뛸 줄 수를 정한다. 서버는 기존 행을 지우고 CSV 줄마다 `row`를 만든 뒤 매핑 후보를 만든다(R-07~R-12, R-18).
3. 정리 단계에서 사용자가 오류 행을 고친다. 행을 고칠 때마다 매핑이 다시 계산된다(R-16, R-22).
4. 확인 단계에서 카테고리·태그·계정 매핑을 고른다. 이름이 같은 기존 레코드가 있으면 자동으로 짝지어지고, 없으면 "새로 만들기"가 기본이다(R-18~R-21).
5. 게시를 누르면 서버가 `status`를 `importing`으로 바꾸고 job을 예약한다. job은 한 DB transaction 안에서 매핑된 새 레코드를 만들고, 행마다 같은 날짜·금액·통화·이름의 기존 수동 거래를 찾아 있으면 갱신하고 없으면 새 거래를 만든다(R-23, R-24, R-40).
6. 성공하면 가족 단위 sync를 예약하고 `complete`가 된다. 실패하면 transaction이 되돌려지고 `failed`와 오류 메시지가 남는다. 사용자는 `complete`나 `revert_failed`인 import를 되돌려 `pending`으로 보낼 수 있다(R-24, R-26).
7. 작업자가 죽어 `importing`에서 멈추면 1시간 뒤 사용자가 취소할 수 있고, 6시간 뒤에는 정리 job이 상태를 정한다(R-28).

### 1.2 범위·통합 지점

- 제공: `Import` 13종(R-01)의 업로드·설정·매핑·정리·게시·되돌리기, API v1의 import 생성·preflight·행 조회, 청크 업로드(`ImportSession`), 중복(멱등) 처리, 실패·멈춤 정리, `AccountStatement`(명세서 파일 보관, 계정 자동 짝짓기, 대조 상태).
- 제외:
  - `Entry`·`Transaction`의 저장 검증과 `convert_to_trade`. 검증은 [transactions](./transactions.md) R-02, 변환은 R-64가 갖는다. 이 문서는 import가 만드는 값만 쓴다.
  - 종목 해석(`Security::Resolver`). `TradeImport`와 `QifImport`가 호출하는 경계만 쓰고, 해석 규칙은 [investments-securities](./investments-securities.md) R-09~R-12다.
  - 중복 후보 판정 `find_duplicate_transaction`의 조건. [provider-import-adapter](./provider-import-adapter.md) R-15가 갖고, 이 문서는 호출 인자(R-40, R-51)만 쓴다. `import_locked` 의미는 같은 문서 R-09·R-12다.
  - Sure NDJSON을 풀어 넣는 `Family::DataImporter`(1,823줄)와 `SureImport::Preflight`(430줄), Monarch 변환기 `MonarchImport::Converter`(339줄)의 내부. 열지 않았다. 호출 경계와 상태 규칙만 R-53, R-54에 쓴다. feature map에 별도 행("가족 데이터 export·import")이 필요하다는 제안은 보고에 있다.
  - PDF 내용 추출의 LLM 호출 내부(`PdfImport::AiProcessor`, 토큰·프롬프트). 호출 경계는 R-51이다.
  - 외부 은행 연동 provider([provider-import-adapter](./provider-import-adapter.md) 소관)와 KB국민 CSV 전용 어댑터(사용자가 따로 만든다).
- 외부 의존·선행 계약: DB transaction과 jsonb, 파일 저장소(Active Storage: NDJSON, PDF, 명세서 원본, Monarch 잔액 파일), background job 큐(`high_priority`, `medium_priority`, `ai_low_priority`), 현재 사용자·가족과 계정 권한(`accessible_accounts`, `writable_by`, [transactions](./transactions.md) R-68), `Family#sync_later`와 `EntryScheduledSyncJob`(호출만), 통화 표([money-currency-rules](./money-currency-rules.md) R-09), CSV 파서(RFC 4180 호환, 느슨한 따옴표 허용), 문자 인코딩 감지기(원본은 `rchardet`).
- 소유 상태·부작용: `imports`, `import_rows`, `import_mappings`, `import_sessions`, `import_source_mappings`, `account_statements`와 그 원본 파일. 게시가 `entries`(`import_id`로 표시)·`accounts`(`import_id`)·`categories`·`tags`·`merchants`·`rules`·`trades`를 만든다. 가족 sync를 예약한다.

### 1.3 인터페이스와 데이터 의미

**데이터**

| 데이터 | 타입 | 의미·제약 |
|---|---|---|
| `Import` | 행 | `type`(13종 중 하나, R-01), `status`(기본 `pending`, R-02), `family_id`, `account_id`(선택, 이 import가 넣을 계정), `account_statement_id`, `import_session_id`, `raw_file_str`(CSV 본문 text, UTF-8로 정규화된 값), `col_sep`(기본 `,`), `rows_to_skip`(기본 0), 열 이름 `date_col_label`·`amount_col_label`·`name_col_label`·`category_col_label`·`tags_col_label`·`account_col_label`·`qty_col_label`·`ticker_col_label`·`exchange_operating_mic_col_label`·`price_col_label`·`entity_type_col_label`·`notes_col_label`·`currency_col_label`, `date_format`(strptime 형식, DB 기본 `%m/%d/%Y`), `number_format`(없으면 `1,234.56`), `signage_convention`(기본 `inflows_positive`), `amount_type_strategy`(기본 `signed_amount`), `amount_type_identifier_value`·`amount_type_inflow_value`, `rows_count`(행 수 counter), `error`(실패 메시지), `summary`·`error_details`·`expected_record_counts`·`readback_verification`(jsonb 객체, 기본 `{}`), 청크용 `sequence`·`client_chunk_id`·`checksum`(64자 SHA256). |
| `Import::Row` | 행 | 모두 문자열. `source_row_number`(1부터, import 안에서 유일), `account`, `date`, `qty`, `ticker`, `exchange_operating_mic`, `price`, `amount`, `currency`, `name`, `category`, `tags`, `entity_type`, `notes`, 규칙·분류·가맹점용 필드(`category_color`, `category_parent`, `category_icon`, `merchant_color`, `merchant_website`, `resource_type`, `active`, `effective_date`, `conditions`, `actions`, `rule_group`). |
| `Import::Mapping` | 행 | `type`(Category·Tag·Account·AccountType·MonarchAccount 매핑), `key`(파일 안의 원래 값, `(import, type, key)` 유일), `mappable`(짝지은 내부 레코드, 선택), `create_when_empty`(기본 true, 짝이 없을 때 새로 만들지), `value`(AccountType은 선택한 accountable 이름, Monarch는 선택 JSON). |
| `ImportSession` | 행 | `import_type`(`SureImport`만), `status`(`pending`·`importing`·`complete`·`failed`), `client_session_id`(가족 안에서 유일), `expected_chunks`(양의 정수), `summary`, `error_details`. 청크는 `sequence` 순서의 `SureImport`들이다. |
| `ImportSourceMapping` | 행 | 한 세션에서 원본 ID를 만든 레코드에 짝짓는다. `source_type`·`target_type`은 10종(Account, Category, Tag, Merchant, RecurringTransaction, RecurringOccurrence, Transaction, Budget, Security, Rule) 중 하나다. `(import_session, source_type, source_id)` 유일. |
| `AccountStatement` | 행 | `filename`, `content_type`(PDF·CSV·XLSX만), `byte_size`(1~25MB), `checksum`(MD5, 옛 행용), `content_sha256`(가족 안에서 유일), `account_id`(선택), `suggested_account_id`·`match_confidence`(0~1), `review_status`(`unmatched`·`linked`·`rejected`), `period_start_on`·`period_end_on`, `opening_balance`·`closing_balance`, `currency`, `institution_name_hint`·`account_name_hint`·`account_last4_hint`, `parser_confidence`, 원본 파일. |

**연산**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| 웹 import 생성 `POST /imports` | `import[type]`, `import[account_id]`, `import[import_file]` → 새 `Import`, 다음 단계로 redirect | R-03 |
| 업로드 `PATCH /imports/:id/upload` | `import[import_file]` 또는 `raw_file_str`, `col_sep`, `account_id` | R-04 |
| 설정 `PATCH /imports/:id/configuration` | 열 이름·형식 필드(R-07), `refresh_only` | R-07 |
| 정리 `GET /imports/:id/clean`, 행 `PATCH .../rows/:id` | `view=errors`, `per_page`(기본 10), 행 필드 | R-16, R-22 |
| 확인 `GET /imports/:id/confirm`, 매핑 `PATCH .../mappings/:id` | `mappable_id`(또는 `internal_new_resource`), `value` | R-19~R-21 |
| 게시 `POST /imports/:id/publish` | → `importing` 후 job | R-23, R-24 |
| 되돌리기 `PUT /imports/:id/revert`, 취소 `POST .../cancel`, 삭제 `DELETE /imports/:id`, 템플릿 `PUT .../apply_template` | | R-26~R-31 |
| API `POST /api/v1/imports`, `POST .../preflight`, `GET .../imports`, `GET .../imports/:id`, `GET .../imports/:id/rows` | `type`, `file` 또는 `raw_file_content`(둘 다 CSV는 10MB 상한), 설정 필드, `publish=true` | R-55, R-56 |
| API 청크 `POST /api/v1/import_sessions`, `POST .../:id/chunks`, `POST .../:id/publish`, `GET .../:id` | `client_session_id`, `expected_chunks`, `sequence`, `client_chunk_id`, 파일 | R-57~R-59 |
| 명세서 `POST /account_statements`, `PATCH .../:id`, `PATCH .../:id/link`, `.../unlink`, `.../reject`, `DELETE` | `files[]`, `account_id`, 힌트·기간·잔액 필드 | R-60~R-64 |

### 1.4 행동 규칙과 남은 질문

**공통 파이프라인: 유형·상태·생성·업로드**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `Import.type` | 13종만 저장된다: TransactionImport, TradeImport, AccountImport, MintImport, ActualImport, YnabImport, MonarchImport, CategoryImport, RuleImport, MerchantImport, PdfImport, QifImport, SureImport. 그 밖의 값은 검증 오류다. 가족 설정(분류·가맹점·규칙·Sure·Monarch)을 쓰는 5종(`FAMILY_CONFIG_TYPES`)은 guest 역할이 만들거나 바꿀 수 없다(R-29). 웹 `create`에서 알 수 없는 `type`은 오류 없이 `TransactionImport`로 바뀐다(예외: `DocumentImport`, R-03). | 코드 확인 |
| R-02 | `Import.status` | 6종: `pending`(기본), `importing`, `complete`, `failed`, `reverting`, `revert_failed`. 전이는 (a) `pending`·`failed` → `importing`(R-23), (b) `importing` → `complete` 또는 `failed`(R-24), (c) `complete`·`revert_failed` → `reverting`(R-26), (d) `reverting` → `pending` 또는 `revert_failed`(R-26), (e) 멈춤 정리·강제 취소(R-28). `failed`는 재게시 가능하다(트랜잭션이 되돌려졌기 때문). `complete`·`reverting`·`revert_failed`에서 job이 다시 오면 게시하지 않고 건너뛴다(R-24). `publish_later`가 `status`를 검사하지 않으므로 (a)는 `complete`·`reverting` 등 어느 상태에서든 직접 요청으로 일어날 수 있다(R-25). | 코드 확인 |
| R-03 | 웹 `create`(`POST /imports`) | 분기 우선순위: (1) 파일이 있고 `type=DocumentImport`이면 문서 업로드, (2) 파일이 있고 `type=SureImport`이면 R-54, (3) `DocumentImport`·`SureImport`인데 파일이 없으면 오류 알림 후 `new`로, (4) 파일 MIME이 `application/pdf`이면 `%PDF-`로 시작하는지 확인(아니면 알림)한 뒤 PDF import(R-51), (5) 그 밖에는 CSV 계열. CSV 계열은 먼저 `Import`를 `date_format = 가족의 date_format`으로 만들고(`account`는 `accessible_accounts`에서 못 찾으면 오류 없이 nil), 파일이 있으면 크기가 10MB(`MAX_CSV_SIZE`)를 넘거나 MIME이 `text/csv`·`text/plain`·`application/vnd.ms-excel`·`application/csv`가 아니면 방금 만든 import를 지우고 알림으로 되돌린다. 통과하면 본문을 `raw_file_str`에 넣고 `preset_for_uploaded_csv`(R-42)를 거쳐 저장하고 설정 단계로 보낸다. 파일이 없으면 업로드 단계로 보낸다. 크기·MIME 검사는 확장자를 보지 않는다. | 코드 확인 |
| R-04 | `PATCH /imports/:id/upload`(CSV 계열) | 본문(`import_file` 또는 `raw_file_str`)을 `col_sep`(`,` 또는 `;`)로 파싱해 헤더가 있고 데이터가 1행 이상이며 CSV 문법 오류가 없을 때만 받는다. 아니면 422와 알림이다. 받으면 계정(없으면 nil, 있는데 접근 못 하면 404)을 정하고 `raw_file_str`·`col_sep`을 저장한 뒤(검증 없이) `preset_for_uploaded_csv`를 거쳐 설정 단계로 간다. 이 경로는 크기·MIME을 다시 검사하지 않는다. QIF·Sure·Monarch는 각자 업로드 규칙을 쓴다(R-52~R-54). 업로드는 `save!(validate: false)`로 저장하므로 `col_sep`·`rows_to_skip` 검증은 이 시점이 아니라 이후 설정 저장(R-07)에서 실행된다. | 코드 확인 |
| R-05 | CSV 파싱(`Import.parse_csv_str`) | 본문 앞뒤 공백·개행을 지우고 첫 줄을 헤더로 읽는다. 따옴표 규칙을 느슨하게 적용하고(`liberal_parsing`), 모든 셀의 앞뒤 공백을 지운다. 구분자는 `col_sep`(`,` 또는 `;`)뿐이다. 탭·`|` 구분자는 검증으로 거부된다. `rows_to_skip`이 양수이면 파싱 전에 앞 N줄(개행 기준 `lines`)을 버리고 그 다음 줄을 헤더로 쓴다. 따옴표 안의 개행도 줄로 세므로 그런 줄 위에서는 건너뛰기가 어긋난다. `RuleImport`는 `parsed_csv`를 따로 정의해 `rows_to_skip`을 무시한다(`rule_import.rb:93-95`). | 코드 확인 / 추론(따옴표 안 개행) |
| R-06 | `raw_file_str`이 바뀐 채 저장될 때 인코딩 정규화 | 비어 있으면 그대로. 이미 유효한 UTF-8이면 그대로. 아니면 감지기로 인코딩을 추정하고 신뢰도가 0.75를 넘으면 그 인코딩으로 읽어 UTF-8로 변환한다(깨진 바이트는 대체 문자로). 신뢰도가 낮거나 감지에 실패하면 `Windows-1250`, `Windows-1252`, `ISO-8859-1`, `ISO-8859-2` 순으로 유효하게 읽히는 첫 인코딩을 쓰고, 모두 실패하면 UTF-8로 보고 잘못된 바이트를 `?`로 바꾼다. 후보 목록에 `CP949`·`EUC-KR`·`UTF-16`은 없고, 폴백 `try_common_encodings`는 UTF-8 유효성을 먼저 확인하지 않는다. 단일 바이트 인코딩(`Windows-1250`이 첫 후보)은 거의 모든 바이트열을 유효로 보므로, 신뢰도가 0.75 이하인 CP949·UTF-8 한글 파일은 오류 없이 깨진 글자(mojibake)로 저장될 수 있다(추론, U-01). 웹 파일 업로드는 바이트열을 읽으므로 UTF-8 파일도 이 감지를 거친다. BOM을 제거하는 코드는 없다(R-09). | 코드 확인 / 추론(업로드가 바이트열로 읽힘, U-01·U-02) |
| R-07 | 설정 저장(`PATCH .../configuration`) | `refresh_only`이면 `rows_to_skip`만 저장하고 설정 화면으로 돌아간다. 아니면 허용 필드(열 이름 13개, `date_format`, `number_format`, `signage_convention`, `amount_type_strategy`, `amount_type_identifier_value`, `amount_type_inflow_value`, `rows_to_skip`)를 저장(검증 포함)하고 R-10의 행 생성과 R-18의 매핑 동기화를 실행한 뒤 정리 단계로 간다. 검증 실패는 첫 메시지와 함께 설정 화면으로 돌아간다. 행 생성은 transaction이 아니다. 헤더 중복(R-09)으로 행 생성이 실패하면 기존 행은 이미 지워진 상태다. PDF·QIF는 이 단계를 건너뛴다. `date_format` 값은 목록 검증이 없어 어떤 `strptime` 형식 문자열이든 저장된다. 화면은 `Family::DATE_FORMATS` 11종에 `DD/MM/YY`(`%d/%m/%y`)를 더해 보여준다(C-02). | 코드 확인 |
| R-08 | `Import` 저장 검증 | `type`(R-01), `amount_type_strategy`(`signed_amount`·`custom_column`), `col_sep`(`,`·`;`), `signage_convention`(`inflows_positive`·`inflows_negative`·nil), `number_format`(4종, R-11), `rows_to_skip`(0 이상 정수이며 파일 줄 수보다 작아야 함), `sequence`(양의 정수), `checksum`(64자), 계정과 세션이 같은 가족인지, `custom_column`이면 `amount_type_inflow_value` 필수, `summary`·`error_details`가 객체인지, 세션 청크는 `sequence`·`checksum` 필수. | 코드 확인 |
| R-09 | 열 이름 해석(`csv_value`) | 헤더와 열 이름 모두 `strip → downcase → *제거 → 공백·하이픈 연속을 _로` 바꿔 비교한다. 열 이름이 비어 있으면 그 필드는 nil이다(별칭도 안 본다). 열 이름이 있는데 헤더에 없거나 셀이 비어 있으면 별칭을 순서대로 본다: 계정 `account`·`account_name`, 날짜 `date`, 수량 `qty`·`quantity`, 종목 `ticker`, 시장 `exchange_operating_mic`, 가격 `price`, 금액 `amount`·`balance`, 통화 `currency`, 이름 `name`, 분류 `category`, 태그 `tags`, 유형 `entity_type`·`account_type`·`type`, 메모 `notes`. 정규화 뒤 같아지는 서로 다른 헤더가 둘 이상이면 `duplicate_headers` 오류로 `RecordInvalid`가 된다. BOM(`﻿`)은 정규화가 지우지 않는다. | 코드 확인 |
| R-10 | 행 생성(`generate_rows_from_csv`, 기본 구현) | 기존 행을 모두 지우고, CSV 데이터 줄마다 `source_row_number`를 1부터 매겨 `row`를 만든다. 금액·수량·가격은 `sanitize_number`(R-11) 결과를 문자열로 저장한다. `currency`는 셀이 있으면 그 값, 없으면 계정의 통화(없으면 가족 통화)다. `name`은 셀이 없으면 `Imported item`이다. 그 밖의 필드는 셀 문자열이다. 행 수 counter를 다시 센다. `MintImport`·`ActualImport`·`YnabImport`·`CategoryImport`·`MerchantImport`·`RuleImport`·`QifImport`·`PdfImport`는 각자의 구현을 쓴다(R-45~R-52). | 코드 확인 |
| R-11 | 숫자 정규화(`sanitize_number`) | `number_format` 4종: `1,234.56`(소수점 `.`, 천 단위 `,`), `1.234,56`, `1 234,56`(천 단위 공백), `1,234`(소수점 없음, 천 단위 `,`). 빈 값·nil·미지원 형식이면 `""`. 공백 천 단위 형식은 모든 종류의 공백을 지우고 양끝의 숫자·소수점·`-`가 아닌 문자(통화 기호)를 지운다. 나머지 형식은 숫자·천 단위·소수점·`-` 이외의 문자(통화 기호, 괄호, `+`, 한글 단위 포함)를 전부 지우고 천 단위 문자를 지운 뒤 소수점을 `.`로 바꾼다. 결과가 `^-?\d+\.?\d*$`가 아니면 `""`이다. 그래서 `(1,234)`는 `1234`(양수로 바뀜), `1,234-`·`.5`·`1.234.567,89`는 `""`다. `""`이면 R-16의 "필수" 오류가 난다. `1,234`(소수점 없음) 형식에서는 소수점 문자 `.`도 허용 문자가 아니어서 지워지므로 `1,234.50`이 `123450`(100배)이 되고 오류도 없다. `MintImport`는 금액을 이 함수 없이 숫자로 읽는다(R-45). | 코드 확인 |
| R-12 | 날짜 | 행의 `date`는 `date_format`으로 엄격하게 파싱해야 한다(형식 불일치면 "must exactly match the format" 오류). 파싱된 날짜는 `Entry.min_supported_date`(오늘 − 30년)보다 작지 않아야 하고(같은 날 허용) 오늘(`Date.current`)보다 크면 안 된다. 즉 행 검증은 미래 날짜를 거부한다(`Entry` 자체는 미래 날짜를 받는다, [transactions](./transactions.md) R-02). 날짜 형식 추정(`detect_date_format`)은 후보 형식 중 샘플 최대 50개를 가장 많이 파싱하는 것(동점이면 1970..오늘+5년 범위 안 개수)을 고르고, QIF와 명세서 CSV 메타데이터 감지에서만 쓴다. CSV import의 `date_format` 기본값은 가족의 `date_format`(DB 기본 `%m-%d-%Y`)이고, API로 만들면 `Import`의 DB 기본 `%m/%d/%Y`다. 행 검증은 하한 날짜 당일을 허용하지만 `Entry` 저장 검증은 `date > 오늘 − 30년`이라 당일을 거부한다. 그 행은 정리 단계를 통과해도 게시에서 R-40의 롤백으로 실패할 수 있다. | 코드 확인 / 추론(후행 문자열은 Ruby 표준 동작, U-03) |
| R-13 | 부호 전략 `signed_amount`(기본) | `row.signed_amount`는 금액에 `signage_convention`을 적용한다: `inflows_positive`(CSV에서 입금이 양수)이면 −1을 곱하고, `inflows_negative`이면 그대로 둔다. 결과가 Sure 내부 부호(지출 양수, 수입 음수, money-currency-rules R-36)다. 같은 금액 칸에서 입금·출금을 구분하는 열이 없으면 이 전략만 쓸 수 있다. | 코드 확인 |
| R-14 | 부호 전략 `custom_column` | 구분 열(`entity_type_col_label`)의 값이 `amount_type_identifier_value`(없으면 `amount_type_inflow_value`)와 같으면 입금 행, 아니면 출금 행이다. 입금 행은 금액에 (`inflows_positive`이면 −1, 아니면 +1)을 곱하고, 출금 행은 (`inflows_positive`이면 +1, 아니면 −1)을 곱한다. 이 "treat as" 값은 `amount_type_inflow_value`가 `inflows_positive`·`inflows_negative`이면 그 값, 아니면 `signage_convention`, 그것도 아니면 `inflows_positive`다. 금액에 `abs`를 취하지 않는다. 구분 열 값이 입금·출금 어느 쪽이 아니어도(빈 값 포함) 출금으로 취급한다. | 코드 확인 |
| R-15 | `TradeImport` 행의 `signed_amount` | `price × (±qty)`다. `inflows_positive`이면 `+qty`, 아니면 `−qty`를 쓴다. 매수(수량 +)가 지출 양수가 되는 기본 설정이다. | 코드 확인 |
| R-16 | `Import::Row` 검증과 `cleaned?` | 행 검증: `amount`는 숫자(빈 값 허용), `currency` 필수이고 통화 표에 있어야 한다("is not a valid currency code"), 날짜는 R-12, 유형별 필수 열은 값이 비면 오류(Transaction·Mint·Actual·YNAB·PDF `date`·`amount`, Trade `date`·`ticker`·`qty`·`price`, Account `name`·`amount`, Category·Merchant `name`, Rule `resource_type`·`conditions`·`actions`). `cleaned?`는 파일이 올라와 있고 행이 1개 이상이며 모든 행이 유효한 것이다. 정리 화면은 `view=errors`일 때 무효 행만 보여주고 10건(기본)씩 나눈다. | 코드 확인 |
| R-17 | 태그 문자열 분해(`tags_list`) | 비어 있으면 `[""]`(태그 하나가 빈 문자열). 아니면 이스케이프되지 않은 `,`가 있으면 `,`로, 없고 `|`가 있으면 `|`로, 둘 다 없으면 `,`로 자른다(`,`가 우선). 각 조각의 앞뒤 공백을 지운다. 역슬래시가 다음 `,`·`|`·`\`를 이스케이프한다. 이스케이프할 필요 없는 문자 앞의 역슬래시는 그대로 남는다. | 코드 확인 |

**공통 파이프라인: 매핑·정리·확인**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | 매핑 동기화(`sync_mappings`) | `mapping_steps`(유형별, R-40~R-52)의 매핑 종류마다, 행에서 모은 고유 값(카테고리는 `category`, 태그는 `tags_list` 전체, 계정은 `account`, 계정 유형은 `entity_type`)을 `key`로 만들고 이름이 정확히 같은 가족의 기존 레코드(대소문자 구분)를 `mappable`로 짝짓는다. 못 찾고 `key`가 비어 있지 않으면 `create_when_empty = true`다. 이미 있는 매핑은 `mappable`·`create_when_empty`를 다시 계산해 덮어쓴다(사용자 선택은 보존되지 않는다). 마지막으로 해당 매핑 클래스에서 방금 만든 목록에 없는 매핑을 지우는데, 이 삭제 범위에 import 조건이 없어 다른 import와 가족의 같은 종류 매핑까지 지워진다(U-04). | 코드 확인 |
| R-19 | 매핑 선택(`PATCH .../mappings/:id`) | `mappable_id`가 `internal_new_resource`이면 `create_when_empty = true`, 매핑 레코드는 비운다. 그 밖이면 같은 가족의 해당 클래스 레코드를 찾아(없으면 nil) `mappable`로 둔다. `value`도 저장한다. 변경 권한은 R-29이고, 저장 뒤 확인 화면으로 돌아간다. 선택지에 계정은 수동 계정만, 카테고리·태그는 가족 것 전부가 나오며 `key`가 비어 있지 않을 때만 "새로 만들기"가 있다. | 코드 확인 |
| R-20 | 매핑 종류별 규칙 | Category: 키 `Parent:Child`는 `:`를 한 번만 나눠 앞뒤를 strip하고, 기존 카테고리를 찾을 때는 자식 이름(`Child`)으로 찾는다. 새로 만들 때 `Parent`가 최상위로 있으면 쓰고, 이미 하위 카테고리면 그 부모를 쓰고, 없으면 최상위로 만든다(동시 생성 충돌은 기존 것을 읽어 해소). 자식은 부모 색을 따른다. `:`가 없는 키는 색을 무작위로 정해 만들고 아이콘은 이름으로 추천한다. 선택은 필수가 아니다. Tag: 이름으로 `find_or_create`한다. Account: 새로 만들 때 이름 = 키, 잔액 0, 통화 = 가족 통화, 종류 `Depository`이고 이 import에 묶는다. `mappable`은 `(key.blank? || !create_when_empty) && import.account.nil?`일 때만 필수다. 그래서 키가 비어 있거나 "새로 만들기"가 아닌데 짝이 없으면 무효이고, 키가 있고 `create_when_empty`이면 짝 없이도 유효하다. AccountType: `value`(accountable 종류)가 필수다. | 코드 확인 |
| R-21 | 정리 → 확인 → 게시 화면 이동 | `show`(import 상세)는 CSV import가 업로드 전이면 업로드로, `publishable?`이 아니면 `mapping_steps`가 비었을 때는 정리로, 있으면 확인으로 보낸다. 정리는 `configured?`가 아니면 설정으로(PDF는 상세로) 보낸다. 확인은 `mapping_steps`가 비었으면 상세로, 아니면 `cleaned?`가 아닐 때 정리로 보낸다. `publishable?` = `cleaned?`이고 모든 매핑이 유효한 것이다. | 코드 확인 |
| R-22 | 행 수정(`PATCH .../rows/:id`) | 허용 필드(`account`, `date`, `qty`, `ticker`, `price`, `amount`, `currency`, `name`, `category`, `tags`, `entity_type`, `notes`, 분류 필드 4개)를 검증 없이 저장하고 R-18을 다시 실행한다. 사용자가 입력한 문자열이 그대로 `row`에 들어가므로 `number_format`을 거치지 않는다(`amount`에 `1234.5` 형태를 넣어야 한다). | 코드 확인 / 추론(입력 형태) |

**공통 파이프라인: 게시·되돌리기·정리**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-23 | 게시 예약(`publish_later`, 웹 `publish`) | 행 수가 `max_row_count`(기본 10,000, `AccountImport` 50, `SureImport` 100,000)를 넘으면 `MaxRowCountExceededError`다(웹은 알림). `publishable?`이 아니면 일반 `RuntimeError`("Import is not publishable")를 던지고 웹은 이를 잡지 않는다. 통과하면 `status = importing`으로 저장하고 `ImportJob`(high_priority)을 예약한다. 저장 뒤 예약이 실패해도 상태를 되돌리지 않는다(`SureImport`는 되돌린다, R-54). `failed`이고 더 이상 `publishable?`이 아니면 게시 대신 import 상세로 보낸다. | 코드 확인 |
| R-24 | 게시 실행(`Import#publish`, job) | `complete`·`reverting`·`revert_failed`이면 경고 로그만 남기고 아무것도 하지 않는다(job 도착 시점의 검사이며 예약 단계(R-23)에는 같은 검사가 없다). 행 수 한도를 다시 확인하고 `import!`(유형별, R-40~R-54)를 부른 뒤 가족 sync(`family.sync_later`)와 새 entry의 예약 sync를 걸고 `complete`로 저장한다. 어디서든 예외가 나면 `failed`와 `error = 메시지`로 저장한다. `import!`는 한 DB transaction이라 그 안의 실패는 모두 되돌려지지만, 그 뒤의 sync 예약 실패도 같은 `rescue`로 `failed`가 된다(데이터는 이미 커밋된 상태). | 코드 확인 |
| R-25 | 게시 범위의 원자성과 멱등 | 유형별 `import!`는 한 DB transaction이다. 새 레코드는 한꺼번에 저장되고 중간 실패면 하나도 남지 않는다. 같은 import를 `failed` 뒤 다시 게시하면 `TransactionImport`는 R-40의 중복 판정으로 이전 부분 결과 없이 처음부터 돌고, `TradeImport`·`MintImport`·`ActualImport`·`YnabImport`는 중복 판정이 없어 `complete` 뒤 재실행되면 이중 입력된다. `publish_later`와 웹 `publish`는 `status`를 검사하지 않아 `complete` import에 `POST /imports/:id/publish`를 직접 보내면 `importing`으로 바뀌고 `import!`가 다시 돈다. R-24의 건너뛰기는 job이 도착했을 때 이미 `complete`인 경우뿐이다(UI는 `_ready.html.erb`에서 버튼만 숨긴다). 직접 재요청하면 `TradeImport`·Mint·Actual·YNAB는 모든 행이 이중 입력되고 `TransactionImport`는 R-40 중복 판정으로 기존 entry를 갱신한다. | 코드 확인 / 추론(중복 판정 없음은 호출 코드에 없음, 2.1) |
| R-26 | 되돌리기(`revert_later`/`revert`) | `complete`·`revert_failed`에서만 가능하다(아니면 `RuntimeError`). `status = reverting`으로 두고 `RevertImportJob`(medium)을 예약한다. job은 한 transaction에서 이 import의 `accounts`와 `entries`를 삭제하고 유형별 후처리(`revert_derived_state!`)를 한 뒤 가족 sync를 예약하고 `pending`(PDF는 R-51)으로 되돌린다. 행·매핑은 남아 다시 게시할 수 있다. 실패하면 `revert_failed`와 오류가 남는다. `import_id`가 없는 기존 entry(R-40의 중복 갱신분)는 삭제되지 않는다. 분류·가맹점·규칙 import(태그 전용 import는 없다)는 entry·계정이 없어서 되돌려도 만든 레코드가 지워지지 않는다. | 코드 확인 / 추론(분류·가맹점·규칙은 `revert` 재정의 없음, 2.1) |
| R-27 | `data_committed?` | 이 import가 데이터를 커밋했는지 판단한다: `entries`나 `accounts`가 있으면 참이다. Category·Merchant·Rule import는 행의 이름이 모두 가족 레코드에 이미 있으면 참이다(이름이 모두 빈 파일은 거짓). `MonarchImport`는 기존 계정을 바꾼 기록이 있어도 참이다. | 코드 확인 |
| R-28 | 멈춘 import 정리 | 사용자가 `importing`·`reverting`에서 마지막 변경 후 1시간(`PRESUMED_LOST_AFTER`)이 지난 import를 취소하면 `failed`(`reverting`이면 `revert_failed`)와 "job이 사라진 것으로 보임" 메시지로 바뀐다. 1시간 전이면 `false`이고 바뀌지 않는다. 정리 job(`SyncCleanerJob`)은 `importing`·`reverting`에서 6시간(`STUCK_AFTER`) 지난 import 중 `PdfImport`와 세션 청크를 뺀 것을 행 잠금 아래에서 다시 확인하고 정한다: `reverting`이면 `revert_failed`, `data_committed?`이면 `complete`(그리고 가족 sync), 아니면 `failed`. 한 건의 실패가 나머지 정리를 막지 않는다. `PdfImport`는 `importing`을 처리 중 표시로도 써서 따로 정리한다(R-51). `ImportSession`과 `FamilyExport`(`pending`·`processing` 6시간 → `failed`)도 같은 job이 정리한다(R-59). | 코드 확인 |
| R-29 | 권한 | 모든 import 화면은 가족 범위다. guest는 가족 설정 5종을 만들거나 바꿀 수 없고, 그 밖의 import는 `pending`·`failed`일 때만 편집할 수 있다. guest가 게시할 때 새 카테고리·태그를 만드는 매핑이 있으면 거부한다. 게시·되돌리기·삭제는 이 import가 쓰는 기존 계정(자기 계정, 계정 매핑, 이미 쓴 entry의 계정, 이름으로 찾는 계정) 전부에 쓰기 권한이 있어야 한다. 명세서가 붙은 import는 명세서를 관리할 수 있어야 바꾼다(R-62). 설정이 잠긴 import(`configuration_locked?`, Monarch가 커밋된 뒤)는 업로드·설정을 못 바꾼다. | 코드 확인 |
| R-30 | 삭제(`DELETE /imports/:id`) | `Import`와 의존 행·매핑·계정·entry를 삭제한다(`destroy`, 의존 관계 cascade). 삭제 전에 `revert`를 거치지 않으므로 계정·entry가 같이 지워진다. 가족 sync 예약은 Monarch만 한다. | 코드 확인 / 추론(sync 미예약은 호출 코드에 없음) |
| R-31 | 템플릿(`apply_template`) | 같은 가족·계정·유형으로 `complete`된 가장 최근 import의 열 이름 13개, `date_format`, `signage_convention`, `number_format`, `rows_to_skip`을 복사한다. 없으면 알림이다. 복사 필드에 `amount_type_strategy`·`amount_type_identifier_value`·`amount_type_inflow_value`가 없어 `custom_column` 설정은 복사되지 않는다. `TransactionImport`는 올린 파일이 Sure 내보내기 CSV이면 템플릿 대신 R-42의 설정을 쓴다. | 코드 확인 |
| R-32 | `dry_run`(확인 화면의 건수) | 기본은 행 수, 새로 만들 카테고리·태그 수, 계정이 없으면 새로 만들 계정 수다. `TradeImport`는 행 수와 새 계정 수, `AccountImport`는 행 수, Category·Merchant·Rule은 행 수, `SureImport`는 NDJSON 줄 유형별 개수, Monarch는 변환 결과 통계다. | 코드 확인 |

**유형별: 13종 차이**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-40 | `TransactionImport#import!` | 한 transaction에서: 먼저 매핑의 새 레코드를 만든다. 행마다 (1) 계정 = `import.account` 또는 계정 매핑의 `mappable`. 둘 다 없으면 "Row N: Account 'X' is not mapped…" 메시지의 `MappingError`를 던져 전체가 실패한다. (2) 카테고리 = 매핑의 `mappable`(없으면 nil), 태그 = 태그마다 `mappable`(없는 것은 버림). (3) 통화 = `currency_col_label`이 있으면 행의 통화, 없으면 계정 통화(없으면 가족 통화). (4) 같은 계정에서 날짜·`signed_amount`·통화·이름이 같고 provider 연동이 아닌(`external_id` 없음) `Transaction` entry를 중복 후보로 찾는다([provider-import-adapter](./provider-import-adapter.md) R-15). 이번 import에서 이미 짝지은 entry는 제외하므로 같은 줄이 두 번 있으면 기존 entry가 하나일 때 하나만 짝지어지고 나머지는 새로 만들어진다. (5) 중복이 있으면 새로 만들지 않고 기존 entry를 갱신한다: 카테고리는 값이 있을 때만, 태그는 하나라도 있을 때만 바꾸고, 메모는 비어 있지 않을 때만 바꾸며 `import_locked = true`로 켠다. 기존 entry의 `import_id`는 바꾸지 않는다. (6) 없으면 새 entry(`import_locked = true`, `import` 연결)를 만든다. 갱신분을 먼저 저장하고 새 거래는 한꺼번에 저장한다. 이름은 row 생성 때 `Imported item`으로 채워지므로 이름 비교는 항상 걸린다. 별도 "신규/중복" 건수 요약은 만들지 않는다. 개별 `Entry`·`Transaction` 저장 검증이 실패하면(`save!`나 `import!`) 예외로 transaction 전체가 롤백되어 `failed`가 된다. 일부만 저장되지는 않는다. | 코드 확인 |
| R-41 | `TransactionImport` 열·단계 | 열: 계정 열은 `import.account`가 없을 때만, `date`·`amount`(필수), `name`·`currency`·`category`·`tags`·`notes`. 매핑 단계: Category, Tag, (계정이 없으면) Account. 샘플 CSV: `date*,amount*,name,currency,category,tags,account,notes`(`account`는 `import.account`가 있으면 열에서 뺀다). | 코드 확인 |
| R-42 | Sure 내보내기 CSV 재가져오기 | 올린 `TransactionImport` 헤더가 내보내기 헤더 8개(`date, account_name, amount, name, category, tags, notes, currency`, 소문자·BOM 제거 후 비교)를 모두 포함하면 `signed_amount`·`inflows_negative`·`%Y-%m-%d`·`1,234.56`·`rows_to_skip=0`으로 설정하고(템플릿 적용 때는 열 이름도 헤더에 맞춘다), 이전 파일이 내보내기였는데 새 파일이 아니면 `signed_amount`·`inflows_positive`·가족 `date_format`으로 되돌린다. | 코드 확인 |
| R-43 | `TradeImport#import!` | 열: `date`·`ticker`·`qty`·`price`(필수), 선택 `exchange_operating_mic`·`currency`·`name`·계정. 매핑: 계정만. 행마다 종목을 `Security::Resolver`([investments-securities](./investments-securities.md) R-09~R-12)로 해석하되 같은 `ticker:MIC`는 import 안에서 캐시한다(티커가 비면 종목 없음). `Trade`(수량 = 행의 `qty` 그대로, 가격, 활동 라벨 = 수량이 0·빈 값이면 없음, 양수 `Buy`, 음수 `Sell`)와 `Entry`(금액 = R-15, 통화 = 행 통화나 계정 통화, `import_locked`)를 한꺼번에 저장한다. 중복 판정이 없다. | 코드 확인 |
| R-44 | `AccountImport#import!` | 행마다 구분 열(`entity_type`)을 `AccountType` 매핑(`value` = accountable 이름)으로 바꿔 계정을 만들고(이름, 잔액 = 금액, 통화, 이 import에 묶음) 저장한 뒤 오프닝 잔액을 설정한다. 날짜가 있으면 `date_format`으로 읽고(실패하면 `OpeningBalanceError`), 없으면 계정의 가장 이른 entry 하루 전과 2년 전 중 이른 날(entry가 없으면 2년 전)이다. 오프닝 설정이 오류를 돌려주면 전체가 실패한다. 최대 50행, 같은 이름 중복 검사 없음. | 코드 확인 / 추론(중복 검사 없음) |
| R-45 | `MintImport` | 생성 직후 기본 열 이름을 채운다(`Date`, `Description`, `Amount`, `Currency`, `Account Name`, `Category`, `Labels`, `Notes`, `Transaction Type`, 날짜 `%m/%d/%Y`, `inflows_positive`). 행 생성은 열 이름으로 셀을 읽고 금액은 `Transaction Type`이 `credit`이면 `+금액`, 그 밖이면 `−금액`으로 숫자 변환한다(`sanitize_number`를 쓰지 않는다). 게시는 매핑(Category, Tag, Account) 후 행마다 entry를 만든다(중복 판정 없음, `import_locked` 없음). | 코드 확인 |
| R-46 | `ActualImport` | 기본 열: `Date`(`%Y-%m-%d`), `Payee`(이름, 비면 `Notes`, 그것도 비면 `Imported item`), `Amount`(그대로 `to_d`), `Account`, `Category`, `Notes`, `inflows_positive`. 카테고리 키는 `Category_Group` 열이 있으면 `"그룹: 카테고리"`(한쪽이 비면 있는 쪽)다. 통화는 `default_currency`, 게시 때는 계정 통화(없으면 가족 통화). 매핑은 Category·Account. 중복 판정 없음. | 코드 확인 |
| R-47 | `YnabImport` | 기본 열: `Date`(`%m/%d/%Y`), `Payee`, `Account`, `Category`, `Memo`, `inflows_positive`. 금액은 `Amount`(있으면 우선, `sanitize_number`)이거나 `Inflow − |Outflow|`(둘 다 `sanitize_number`)이고, 금액 근원 열이 하나도 없으면 비워서 필수 검증이 막게 한다. 카테고리는 `Category Group/Category` 열 → `Category Group`+`Category` → `Master Category`+`Sub Category` → `Category` 순서로 한 문자열을 만든다(`"그룹: 카테고리"`). 이름은 `Payee` → `Memo` → `Imported item`. 매핑 Category·Account. | 코드 확인 |
| R-48 | `CategoryImport` | 두 번 돈다. 1차: 행의 `name`으로 가족 카테고리를 `find_or_initialize`해 색(행 → 기존 → 기본 uncategorized 색)과 아이콘(행 → 기존 → `shapes`)을 정하고 부모를 비운 채 저장하며, 부모 이름이 있으면 placeholder 카테고리를 만든다. 2차: 부모를 연결한다. 자기 자신이 부모면 `own_parent` 오류로 전체 실패한다. 열: `name*`, `color`, `parent_category`, `lucide_icon`(별칭 허용). 필수 헤더(`name`)가 없으면 `RecordInvalid`다. 헤더 중복 오류는 없고 같은 정규화 이름이 여럿이면 마지막 열이 이긴다(중복 오류는 `MerchantImport`만 낸다). | 코드 확인 |
| R-49 | `MerchantImport` | 행의 `name`(strip)이 비면 건너뛴다. 가족에 같은 이름이 있으면 건너뛴다(갱신하지 않음). 없으면 색(행 값 또는 무작위)과 `website_url`로 `FamilyMerchant`를 만든다. 열: `name*`, `color`, `website_url`. | 코드 확인 |
| R-50 | `RuleImport` | 행마다 `resource_type`이 `transaction`이 아니면 실패한다. `conditions`·`actions`는 JSON(느슨하게 정리해 재시도하는 복구 경로 포함)이고 액션이 0개면 실패한다. 이름이 있으면 같은 이름·유형의 규칙을 찾아 조건·액션을 통째로 교체하고, 이름이 없으면 새 규칙이다. 조건·액션 값의 카테고리·가맹점·태그 이름은 가족의 레코드로 해석하고 없으면 만든다(가맹점은 가족 가맹점이 우선, 이름이 유일한 provider 가맹점 다음). `active` 문자열 `true·1·yes·y`만 참이다. `rule_group` 열이 있을 때만 그룹을 바꾼다. 필수 열: `resource_type`, `conditions`, `actions`. | 코드 확인 |
| R-51 | `PdfImport`(LLM 호출 경계만) | PDF는 `AccountStatement`(R-60)로 저장된 뒤 같은 파일의 이전 PDF import(`failed` 제외)가 있고 계정·날짜 형식이 같으면 재사용하고 아니면 새로 만든다. 업로드 직후 `process_with_ai_later`가 `status = importing`(처리 표시)으로 바꾸고 `ProcessPdfJob`(ai_low_priority)을 예약한다. job은 LLM으로 문서 유형(`bank_statement`·`credit_card_statement`·`investment_statement`·`financial_document`·`contract`·`other`)과 요약을 추정하고, 은행·카드 명세서면 거래를 추출해 행으로 만든다. 행 생성 때 같은 계정의 기존 entry와 날짜 ±3일, 금액·통화 일치(이름 무시, provider 연동 entry 포함)이면 행을 만들지 않고 그 entry에 "명세서가 증거"라고 표시(`reconciled_at`, `reconciled_by_statement_id`)한다. 계정이 정해지기 전에는 모두 새 행이다. 거래가 있으면 `pending`(사용자 검토), 없거나 다른 문서면 `complete`로 끝낸다. 실패하면 오류 메시지를 정리해 `failed`로 둔다. 게시는 계정이 필수이고 게시 직전에 다시 중복을 확인하며 새 entry는 생성부터 명세서 증거가 붙는다. 되돌리면 이 명세서의 증거 표시를 풀고 행을 다시 만든다(다 일치하면 `complete`). `importing`을 6시간 넘게 잡고 있으면 정리 job이 `reverting`은 `revert_failed`, 데이터가 있으면 `complete`, 없으면 `pending`으로 되돌린다. | 코드 확인 |
| R-52 | `QifImport` | QIF 파일은 업로드 때 형식·인코딩을 정규화하고 파일 안 계정이 없으면 대상 계정이 필수다. 날짜 형식은 D 필드 샘플로 추정하고(실패하면 `%m/%d/%Y`) 사용자가 바꿀 수 있다. 행 생성은 파서 결과로 거래 행과 투자 행을 만들고, 게시는 일반 거래를 일괄 저장하고 분할 거래는 하나씩 만들어 분할 줄 합계가 원 금액과 같을 때만 분할한다. 투자 행은 매매(`Buy`·`ReinvDiv`·`Cover` = 매수, `Sell`·`ShtSell` = 매도)와 그 밖의 현금 거래로 나눠 만든다. 파일 안 계정 이름은 기존 계정과 이름으로 맞추고 없으면 만든다. 오프닝 잔액은 파일 값을 쓰거나, 없으면 가장 이른 거래보다 하루 앞으로 기존 오프닝 앵커를 당긴다. | 코드 확인(`QifParser` 세부는 범위 밖). 단계는 업로드 → 카테고리·태그 선택(`qif_category_selections_controller.rb`: 날짜 형식 선택·변경 시 행 재생성, 선택에서 뺀 카테고리는 행의 `category`를 빈 값으로 갱신, 저장 뒤 `sync_mappings`) → 확인 → 게시다. 설정 화면은 QIF를 이 선택 화면으로 보낸다 |
| R-53 | `MonarchImport` | 잔액 내역 CSV(필수)와 거래 CSV(선택) 두 파일을 받는다. 계정마다 포함 여부·유형·종료 여부·기존 계정 연결·현재 잔액을 사용자가 정한다. 게시는 `MonarchImport::Converter`로 NDJSON 레코드를 만들어 `Family::DataImporter`에 넘긴다. 기존 계정의 오프닝 잔액을 옮기고 상태를 바꾸며 그 기록을 `summary`에 남겨 되돌릴 때 복원하되, 게시 뒤 사용자가 다시 바꾼 값은 복원하지 않는다. 데이터가 커밋된 뒤에는 설정이 잠긴다. API는 이 유형 생성을 거부한다(R-56). | 코드 확인(변환기 내부는 열지 않음) |
| R-54 | `SureImport`(Sure NDJSON) | 업로드는 확장자 `.ndjson`·`.json`(또는 허용 MIME), 크기 10MB(`SURE_IMPORT_MAX_NDJSON_SIZE_MB`), 첫 줄이 `type`·`data` 키를 가진 JSON 객체여야 한다. 줄의 유형 15종(Account, Balance, Category, Tag, Merchant, RecurringTransaction, Transaction, Transfer, RejectedTransfer, Trade, Holding, Valuation, Budget, BudgetCategory, Rule)별로 `rows_count`와 `expected_record_counts`를 센다. 게시 예약은 preflight(`SureImport::Preflight`)를 통과하고 가져올 레코드가 1개 이상일 때만 허용하며, 예약이 실패하면 상태를 되돌린다. 실제 입력은 `Family::DataImporter`가 하고, 끝난 뒤 가족 레코드 수의 증가분을 파일의 예상 건수와 비교해 `readback_verification`(`matched`·`mismatch`·`failed`·`reverted`)을 남긴다. 되돌리면 `reverted`로 둔다. 최대 100,000줄. | 코드 확인(내부 importer와 preflight는 열지 않음) |

**API·청크 세션**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-55 | API v1 preflight(`POST /api/v1/imports/preflight`) | 아무것도 저장하지 않는다. `type`은 PDF·QIF·Monarch를 뺀 10종이고 없으면 `TransactionImport`, 아니면 422 `invalid_import_type`. 파일 또는 `raw_file_content`가 없으면 422 `missing_content`. 파일은 10MB·MIME 규칙(R-03)을 지킨다. 메모리상 `Import`를 만들어 검증하고 오류를 `validation_failed` 목록으로, 파싱된 데이터 행 수, 헤더 목록, 필수 헤더, 누락된 필수 헤더(`missing_required_headers`), `no_data_rows`, 행 수가 유형별 한도를 넘는 경고를 200으로 돌려준다. 유형에 기본 열 이름(Mint·Actual·YNAB)이 있으면 비어 있는 설정에 채워 넣는다. `rows_to_skip`은 반영한다. | 코드 확인 |
| R-56 | API v1 import 생성(`POST /api/v1/imports`) | 쓰기 scope 필요(guest는 가족 설정 5종 거부). `type`이 `SureImport`이면 NDJSON 경로(R-54), `MonarchImport`이면 422 `unsupported_type`. 그 밖에는 설정 필드를 받아 `Import`를 만들고 파일(10MB·MIME) 또는 `raw_file_content`(10MB)를 `raw_file_str`로 넣어 저장한 뒤, 본문이 있으면 행 생성(R-10)만 실행하고(실패는 로그만 남김) `sync_mappings`는 실행하지 않는다. `publish=true`이고 `configured?`이면 게시를 예약한다. 매핑이 만들어지지 않으므로 카테고리·태그는 모두 비어 있고 계정은 `account_id`가 없으면 R-40의 `MappingError`로 실패한다. guest는 새 카테고리·태그가 필요할 때만 거부된다. `PdfImport`·`QifImport` 등 다른 `type`은 `Import::TYPES`에 있으면 만들어진다. 응답은 201이고 `index`·`show`·`rows`는 읽기 scope다(`status`·`type` 필터, 페이지 크기 1~100, 기본 25). API 생성과 preflight는 `amount_type_identifier_value`를 허용 필드에 넣지 않아 API로는 `custom_column`의 입금 값을 지정할 수 없다. `publish=true`인데 행이 무효이면 `publish_later`의 `RuntimeError`가 바깥 `rescue`에 잡혀 import는 저장된 채 500이 돌아간다. | 코드 확인 |
| R-57 | 청크 세션 생성·청크 올리기 | `type`은 `SureImport`뿐(없으면 기본값). `client_session_id`가 이미 있으면 같은 세션을 돌려주되 `expected_chunks`가 다르면 `ConflictError`(409)다. 청크는 `sequence`(양의 정수, `expected_chunks` 이하)와 선택 `client_chunk_id`로 올리고, 내용의 SHA256을 `checksum`으로 저장한다. 같은 `sequence`·같은 내용은 재시도로 보고 기존 청크를 돌려주며(첨부가 빠졌으면 다시 붙이고 행 수를 센다), 같은 `sequence`에 다른 내용, 같은 `client_chunk_id`에 다른 `sequence`·다른 내용, `sequence`와 `client_chunk_id`가 서로 다른 청크를 가리키는 경우는 모두 409다. 게시가 시작된 뒤(`importing`·`complete`)에는 청크를 못 올린다(`pending`·`failed`만). guest는 쓰기가 모두 거부된다. | 코드 확인 |
| R-58 | 세션 게시(`publish_later` → `publish`) | 예약: 모든 청크의 행 수를 다시 세고(첨부 누락이면 409), 이미 `complete`·`importing`이면 아무것도 하지 않는다. 청크가 없거나 행 합계가 100,000을 넘거나 `expected_chunks`가 있는데 `sequence`가 1..N과 다르면(누락·초과 목록을 메시지에 담음) 거부한다. 통과하면 `importing`으로 저장하고 `ImportSessionJob`을 예약하며, 예약이 실패하면 이전 상태로 되돌리고 `EnqueueError`(503)다. 실행: 청크를 `sequence` 순서로 하나씩 처리한다. 이미 `complete`인 청크는 건너뛰고, 아니면 `importing`으로 두고 `import!(import_session:)`를 실행해 `complete`와 청크 요약을 남긴다. 한 청크가 실패하면 그 청크를 `failed`와 오류·요약으로 저장하고 세션도 `failed`와 `error_details`로 저장한다. 재게시하면 `complete`가 아닌 첫 청크부터 이어서 한다. 전체가 끝나면 청크 요약을 합산해 `complete`로 저장하고 가족 sync와 entry 예약 sync를 건다(가족 sync 예약 실패(`enqueue_family_sync`)만 자체 `rescue`로 `error_details`에 남기고 `complete`를 유지한다. 그 뒤 `EntryScheduledSyncJob` 예약 실패는 바깥 `rescue`로 가서 세션이 `failed`가 된다). | 코드 확인 |
| R-59 | `SyncCleanerJob`(cron) | 여섯 단계를 순서대로 돌리되 하나가 실패해도 나머지는 돈다(`Sync`, `Import`, `ImportSession`, `FamilyExport`, `PdfImport`, provider 활동 플래그). `ImportSession`: `importing`에서 6시간 지난 세션은 행 잠금 아래에서 다시 확인하고, `importing` 청크 중 데이터가 커밋된 것은 `complete`로 고친 뒤(재게시가 이중 입력하지 않도록) 세션을 `failed`와 `import_interrupted`로 저장한다. | 코드 확인 |

**계정 명세서 보관 (statement vault)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-60 | 명세서 업로드 | 파일마다 `prepare_upload!`: 크기가 0이거나 25MB를 넘으면, 확장자가 `.pdf`·`.csv`·`.xlsx`가 아니거나 내용에서 감지한 MIME이 확장자에 허용된 값이 아니면(PDF는 `%PDF-` 시작 확인 포함) 거부한다. SHA256으로 같은 가족의 기존 명세서를 찾고(옛 행은 MD5), 있으면 새로 만들지 않고 `DuplicateUploadError`로 기존 명세서를 알려준다(동시 업로드의 unique 위반도 같게 처리). 새로 만들 때 계정이 있으면 `linked`, 없으면 `unmatched`이고 통화는 계정 통화(없으면 가족 통화)다. 저장 직전에 메타데이터를 감지하고(R-61) 계정이 없으면 자동 짝짓기(R-62)를 한다. 저장 실패 시 올린 원본을 지운다. 업로드·보관 관리는 admin·member 역할만 한다. | 코드 확인 |
| R-61 | 메타데이터 감지 | 순서: PDF는 앞 2쪽 텍스트에서 기간·잔액·IBAN 끝 4자리(내용이 파일명보다 우선), 그다음 파일명에서 끝 4자리(`xx`·`ending`·`last 4`·`acct`·`account`·`card` 뒤 숫자 4자리), 날짜 패턴(`YYYY-M-D`, `D-M-YYYY`, `YYYYMMDD`, 구분자 `-_.`; 날짜가 2개 이상이면 첫·끝 날짜가 기간, 1개면 그 달 전체, 없으면 `YYYY-M`·`월이름 YYYY`로 그 달 전체), 기관·계정 힌트(파일명에서 날짜·숫자를 지운 문자열 `hint`를 만들고, 판정에만 영문 소문자·숫자로 정규화한 사본에서 `bank`·`statement` 같은 일반어를 뺀 뒤 남는 것이 있는지 본다. 판정을 통과하면 저장값은 정규화 전 `hint`이므로 한글이 섞인 `KB국민_2024-05.csv`는 한글 포함 힌트가 저장된다. 힌트가 없는 경우는 영문·숫자가 하나도 없는 파일명, 예를 들어 순수 한글·특수문자 이름뿐이다). CSV는 헤더 중 이름이 `date`·`posted`·`transaction`을 포함하는 열의 샘플 최대 250개로 날짜 형식을 추정해 기간을 정한다(열 100개 초과면 건너뜀). XLSX는 파일명만 본다. 이미 값이 있는 필드는 덮어쓰지 않는다. 날짜는 1970..오늘+5년 안만 받는다. `parser_confidence`는 PDF 텍스트 0.85, CSV 날짜 0.65, 파일명만 0.45, 아무것도 못 찾으면 0.1이다. | 코드 확인 / 추론(순수 한글 파일명·한글 헤더는 영문 패턴에 걸리지 않음, 2.1) |
| R-62 | 계정 자동 짝짓기와 연결 | 후보는 가족의 보이는 계정이다. 점수: 기관 힌트가 계정 이름·기관명·도메인에 포함되면 +0.45, 계정 이름 힌트가 계정 이름에 포함되면 +0.25, 끝 4자리가 계정 이름·기관명에 포함되면 +0.25, 통화 일치 +0.05(최대 1). 힌트는 소문자·공백 정리 후 부분 일치다. 세 힌트가 모두 비면 짝짓지 않는다. 0.35 미만은 버리고, 1·2위 점수가 같으면 추측하지 않고 짝짓지 않는다. 짝은 `suggested_account`·`match_confidence`로만 저장되고 사용자가 `link`해야 `account`가 된다(`link`는 계정 인자가 없으면 제안 계정을 쓴다). `unlink`는 계정을 비우고 다시 짝짓기를 한다. `reject`는 제안을 지우고 `rejected`로 둔다(받은 편지함에 남음). 연결·해제·삭제는 대상 계정에 대한 권한(owner·full_control)이 필요하다. | 코드 확인 |
| R-63 | 대조 상태(`reconciliation_status`) | 계정이 있고 기간이 있을 때 세 가지를 검사한다: 기간 시작일의 `Balance.start_balance`와 `opening_balance`, 종료일의 `end_balance`와 `closing_balance`, 두 잔액이 모두 있으면 기간 변화량. 통화는 명세서 통화(`currency` → 계정 통화 → 가족 통화)로 찾는다. 차이의 절댓값이 0.01 이하이면 `matched`, 아니면 `mismatched`이다. 검사할 수 있는 항목이 없으면 `unavailable`, 하나라도 `mismatched`면 전체가 `mismatched`다. | 코드 확인 |
| R-64 | 명세서와 import의 연결 | PDF 명세서는 `PdfImport`와 연결된다(R-51). 계정을 연결·변경하면(`assign_account!`) 이미 데이터가 커밋됐거나 `importing`·`reverting`인 import는 거부하고, 아니면 이전 계정에 대한 증거 표시를 풀고 행을 다시 판정한다. 명세서가 있는 import 접근은 그 명세서를 볼 수 있어야 하고(계정 없으면 admin·member, 있으면 그 계정 공유 대상), 변경은 명세서를 관리할 수 있어야 한다. 명세서가 import에 의존하는 동안 삭제는 막힌다(`restrict_with_error`). | 코드 확인 |

- R-ID 번호: R-33~R-39는 비어 있다. 공통 파이프라인(R-01~R-32)과 유형별(R-40~)을 나누려고 번호를 띄웠고, 빠진 규칙이 아니다.

- 불변식: 게시된(`complete`) import가 만든 `entries`와 `accounts`는 `import_id`로 그 import에 묶여 되돌리기와 삭제 대상이 된다. 중복으로 갱신된 기존 entry는 묶이지 않는다. 한 import 안에서 `(import, source_row_number)`는 유일하다. `ImportSession` 안에서 `sequence`와 `client_chunk_id`는 각각 유일하다.
- 불변식의 예외: R-18의 매핑 정리는 import 범위를 지키지 않는다(U-04).

**한국 CSV (KB국민은행·카드)** 값 정리. 코드가 정한 값이고, KB 파일 실물과의 일치는 확인하지 않았다(미확인, 아래 확인 한계).

| 항목 | 값 | 근거 R-ID |
|---|---|---|
| 인코딩 | 기본 경로는 감지기(신뢰도 > 0.75)에 의존한다. 후보 목록에 `CP949`·`EUC-KR`이 없다. 감지가 `EUC-KR`을 돌려주면 CP949 전용 글자가 대체 문자로 바뀔 수 있다. 재구현은 업로드 때 UTF-8 BOM, UTF-8, CP949 순으로 명시적으로 판정하는 것이 안전하다(적용 메모). | R-06, U-01 |
| 구분자 | `,` 또는 `;`만. KB 파일이 탭이면 입력 전에 바꿔야 한다. | R-05, R-08 |
| 날짜 | `Family::DATE_FORMATS`에 `%Y.%m.%d`(`YYYY.MM.DD`), `%Y-%m-%d`, `%Y/%m/%d`, `%Y%m%d`가 있다. 시각이 붙은 값(`2024.05.15 14:30:21`)은 엄격 파싱에서 실패할 가능성이 크다. | R-12, U-03 |
| 숫자 | `1,234.56` 형식이면 `1,234,567`·`1,234,567원`·`-1,234`가 읽힌다. 괄호 음수는 양수로 읽히고, 후행 `-`는 빈 값이다. 통화 기호·`원`은 지워진다. KRW는 소수가 없어 `1,234`(소수 없음) 형식도 있다. | R-11 |
| 부호 | KB가 입금·출금을 별도 열로 주면 금액 열이 하나뿐이라 그대로 쓸 수 없다. 방법 하나는 입금·출금을 한 열로 합쳐(출금은 양수, 입금은 음수 또는 `inflows_positive`에 맞춰) 올리는 전처리, 다른 하나는 구분 열 + `custom_column`이다. 구분 값에 입금 외의 모든 것(빈 값 포함)이 출금으로 취급되고 금액 부호는 보존된다. | R-13, R-14 |
| 통화 | 통화 열이 없으면 계정 통화, 계정이 없으면 가족 통화. 한 파일에 계정이 하나라면 `import.account`를 정해 계정 열 매핑을 피한다. | R-10, R-40 |
| 천 단위 | `,`(기본) 지원, `.`이나 공백은 형식을 바꿔야 한다. | R-11 |
| 건너뛸 줄 | KB 파일 앞의 안내 줄은 `rows_to_skip`으로 건너뛴다. 파일 줄 수보다 작아야 한다. | R-05, R-08 |
| 중복 | 같은 계정·날짜·금액·통화·이름의 수동 거래는 갱신으로 처리되므로 이미 넣은 파일을 다시 올려도 이중 입력되지 않는다. 같은 날 같은 이름·금액 거래가 2건이면 기존이 2건일 때만 둘 다 갱신으로 처리된다. | R-40 |
| 최대 행 | 한 import 10,000행. | R-23 |

- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-06 | 업로드된 CP949(KB) 파일이 감지기에서 어떤 인코딩과 신뢰도로 나오고, 그 결과 한글이 깨지는가. | 재구현이 감지기를 쓰면 한글이 대체 문자로 바뀌어도 오류 없이 저장된다. 구현자는 감지 로직을 따라 할지 명시적 인코딩 판정을 쓸지 정해야 한다. | Ruby 환경에서 KB 샘플 CSV를 `rchardet`와 R-06 경로로 변환해 본다(이 작업에는 Ruby가 없었다). |
| U-02 | R-06, R-09 | 업로드된 UTF-8 BOM 파일의 첫 헤더에 `﻿`가 남는가. 남으면 첫 열의 별칭 조회(`date` 등)가 실패한다. | 첫 열이 `날짜`가 아닌 별칭 의존이면 매핑이 비는지 결정해야 한다. 열 이름을 직접 고르는 설정 화면은 헤더 원문을 써서 영향이 작다. | 같은 샘플에 BOM을 붙여 `csv_headers`를 본다. 코드 근거: `transaction_import.rb:162-164` 주석("keep a BOM"). |
| U-03 | R-12 | `Date.strptime("2024.05.15 14:30:21", "%Y.%m.%d")`가 오류를 내는가(후행 문자열 거부). | KB 거래일시 열을 그대로 쓸 수 있는지 정해진다. 오류가 나면 시각을 자르는 전처리가 필요하다. | `ruby -e 'require "date"; Date.strptime("2024.05.15 14:30:21","%Y.%m.%d")'`. |
| U-04 | R-18 | `sync_mappings` 마지막의 매핑 삭제(`mapping_class.where.not(id: …).destroy_all`)가 의도된 전역 삭제인가, import 범위 누락인가. | 원본 동작대로 하면 한 import를 설정하는 순간 다른 import·가족의 같은 종류 매핑이 사라져 `publishable?` 판정이 바뀐다. 구현자는 원본 재현과 import 범위 제한 중 하나를 골라야 한다(적용 메모는 범위 제한). | 호출 코드에는 범위 조건이 없다. 의도는 `git log -S"where.not(id: updated_mappings"`와 관련 PR로 확인. |

- 확인 한계: 외부 파일 형식(KB국민은행·카드 CSV의 실제 헤더·인코딩·날짜·부호)은 웹 검색과 실물 파일로 확인하지 않았다. Ruby를 실행할 수 없어 인코딩 변환(U-01), BOM(U-02), `strptime` 후행 문자열(U-03)은 실행 확인을 못 했다. `Family::DataImporter`, `SureImport::Preflight`, `MonarchImport::Converter`, `QifParser` 세부, LLM 추출(`PdfImport::AiProcessor`)은 열지 않았다. 테스트는 열지 않았다.

### 1.5 필수 코드 참조

라이선스가 인용을 허용하는지는 overview 1절을 따른다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `app/models/import.rb:34-47` 상수, `:79` | 업로드 한도, 허용 MIME, `TYPES`, `FAMILY_CONFIG_TYPES`, 부호 규약·전략 이름, 구분자 | R-01, R-03, R-08 |
| C-02 | `app/models/import.rb:56-73` `NUMBER_FORMATS`, `CSV_ONLY_DATE_FORMATS`, `reasonable_date_range`; `app/models/family.rb:22-35` `DATE_FORMATS` | 숫자 형식 4종 표, 날짜 형식 목록 | R-07, R-11, R-12 |
| C-03 | `app/models/import.rb:190-198` `parse_csv_str`, `:696-705` `parsed_csv` | CSV 파싱 옵션과 `rows_to_skip` | R-05 |
| C-04 | `app/models/import.rb:714-759` `sanitize_number` | 숫자 정규화 알고리즘 | R-11 |
| C-05 | `app/models/import.rb:773-833` `ensure_utf8_encoding`, `try_common_encodings` | 인코딩 정규화 알고리즘과 후보 목록 | R-06 |
| C-06 | `app/models/import.rb:647-694` `csv_value`, `normalize_header` | 열 이름 해석, 별칭, 중복 헤더 | R-09 |
| C-07 | `app/models/import.rb:392-434` `generate_rows_from_csv`, `sync_mappings` | 행 생성 필드 변환표와 매핑 동기화 | R-10, R-18 |
| C-08 | `app/models/import/row.rb:4-38`, `:129-161` | 행 검증, 필수 열, 날짜·통화 검증, `signed_amount` | R-12, R-16 |
| C-09 | `app/models/import/row.rb:40-127` | 태그 분해, 부호 전략 계산 | R-13~R-15, R-17 |
| C-10 | `app/models/import.rb:246-348` | `publish_later`, `publish`, `force_fail!`, `revert` | R-23~R-28 |
| C-11 | `app/models/import.rb:124-188` `clean`, `reap_stuck!`; `:266`, `:272` | 정리 규칙, `data_committed?` | R-27, R-28 |
| C-12 | `app/models/import.rb:440-522`, `:543-565` | `cleaned?`, `publishable?`, 권한, 템플릿 | R-21, R-29, R-31 |
| C-13 | `app/models/import/category_mapping.rb:1-102`, `app/models/import/account_mapping.rb:1-53`, `app/models/import/tag_mapping.rb:1-44`, `app/models/import/account_type_mapping.rb:1-25`, `app/models/import/mapping.rb:1-45` | 매핑 종류별 키 계산·선택지·생성 | R-18~R-20 |
| C-14 | `app/models/transaction_import.rb:16-114` | 거래 import 본문, 열, 매핑 단계 | R-40, R-41 |
| C-15 | `app/models/transaction_import.rb:2-14`, `:138-188` | Sure 내보내기 CSV 판정과 preset | R-42 |
| C-16 | `app/models/account/provider_import_adapter.rb:797-841` | 중복 후보 조건(CSV는 `name`·`exclude_entry_ids` 인자) | R-40, R-51 |
| C-17 | `app/models/trade_import.rb:1-109` | 매매 import | R-43 |
| C-18 | `app/models/account_import.rb:1-75`, `app/models/account/opening_balance_manager.rb:30-75` | 계정 import, 오프닝 잔액 기본 날짜 | R-44 |
| C-19 | `app/models/mint_import.rb:1-107`, `app/models/actual_import.rb:1-114`, `app/models/ynab_import.rb:1-162` | 세 서비스별 기본 열, 금액·카테고리 조합 | R-45~R-47 |
| C-20 | `app/models/category_import.rb:1-122`, `app/models/merchant_import.rb:1-116`, `app/models/rule_import.rb:1-501` | 분류·가맹점·규칙 import | R-48~R-50 |
| C-21 | `app/models/pdf_import.rb:1-153`, `:242-293`, `:414-537`; `app/jobs/process_pdf_job.rb:1-89` | PDF 처리 표시, 행 생성, 증거 표시, 되돌리기 | R-51 |
| C-22 | `app/models/qif_import.rb:1-140`, `:285-373`, `:444-537` | QIF 게시 | R-52 |
| C-23 | `app/models/monarch_import.rb:1-367` | Monarch 게시, 기존 계정 변경 복원 | R-53 |
| C-24 | `app/models/sure_import.rb:5-31`, `:131-209`, `:266-343` | Sure NDJSON 유형, 게시, readback | R-54 |
| C-25 | `app/models/import/preflight.rb:16-47`, `:96-168`, `:266-312` | API preflight | R-55 |
| C-26 | `app/controllers/api/v1/imports_controller.rb:65-151`, `:213-236` | API 생성 흐름과 허용 필드 | R-56 |
| C-27 | `app/models/import_session.rb:103-211`, `:230-282`, `:313-335`, `:386-433` | 청크 세션 | R-57, R-58 |
| C-28 | `app/models/import_session.rb:40-101`, `app/jobs/sync_cleaner_job.rb:14-21`, `app/models/family_export.rb:42-72` | 세션 정리, 정리 job 목록 | R-28, R-59 |
| C-29 | `app/models/account_statement.rb:22-30`, `:76-126`, `:137-231` | 명세서 업로드 검증, 중복 판정 | R-60 |
| C-30 | `app/models/account_statement/metadata_detector.rb:7-132`, `:169-203` | 메타데이터 감지 정규식과 신뢰도 | R-61 |
| C-31 | `app/models/account_statement/account_matcher.rb:6-114` | 자동 짝짓기 점수 | R-62 |
| C-32 | `app/models/account_statement.rb:234-284`, `:305-381` | 권한, 연결·해제, 대조 상태 | R-62~R-64 |
| C-33 | `app/controllers/imports_controller.rb:84-148`, `:150-186`, `:233-261` | 웹 생성·상세·게시·되돌리기 흐름 | R-03, R-21, R-23, R-26, R-29 |
| C-34 | `app/controllers/import/uploads_controller.rb:19-38`, `:125-138`; `app/controllers/import/configurations_controller.rb:21-38` | 업로드 검증, 설정 저장 순서 | R-04, R-07 |
| C-35 | `app/models/concerns/qif_parser.rb:37-39`, `:80-120` | QIF 매매 동작 분류와 형식 확인 | R-52 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(테스트는 열지 않았다). 아래 값은 코드를 따라 계산한 기대값이고 실행 확인은 하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-12 | `date_format = %Y.%m.%d`, 행 `date = "2024.05.15"`. | 파싱된 날짜는 2024-05-15이고 날짜 오류 없음. |
| T-02 | R-12, U-03 | 같은 설정에 `date = "2024.05.15 14:30:21"`. | 기대: 형식 불일치 오류("must exactly match…"). 실행 미확인. |
| T-03 | R-12 | 오늘이 2026-11-18, `date = "2026.11.19"` 또는 `1996.11.17`(30년 전보다 이전). | 두 경우 모두 행 오류("must be between…"). `1996.11.18`은 행 검증은 통과하지만 `Entry`의 `date > min_supported_date`(`entry.rb:64`, 엄격 부등호) 검증에서 거부되어 게시가 `failed`가 될 수 있다(코드 읽기 기준). |
| T-04 | R-11 | `number_format = 1,234.56`, 금액 셀 `"1,234,567원"`, `"-45.99"`, `"(1,234)"`, `"1,234-"`, `".5"`, `"1.234.567,89"`. | 순서대로 `"1234567"`, `"-45.99"`, `"1234"`, `""`, `""`, `""`. `""`인 행은 "amount is required" 오류. |
| T-05 | R-11 | `number_format = 1 234,56`, 셀 `"€1 234,56"`, `"1,234.56"`. | `"1234.56"`, `""`(소수점 규칙 위반으로 거부). |
| T-06 | R-13 | `signed_amount`, `inflows_positive`, 금액 `"45.99"`. 같은 설정에서 `"-1500.00"`. | 첫째 `-45.99`(CSV의 양수를 수입으로 읽어 음수), 둘째 `+1500.00`(CSV의 음수가 지출로 바뀌어 양수). `inflows_negative`이면 부호를 바꾸지 않아 `45.99`가 지출, `-1500.00`이 수입이다. |
| T-07 | R-14 | `custom_column`, 구분 열 `구분`, `amount_type_identifier_value = "입금"`, `amount_type_inflow_value = "inflows_positive"`. 행 A: 구분 `입금`, 금액 `1000`. 행 B: 구분 `출금`, 금액 `1000`. 행 C: 구분 `출금`, 금액 `-1000`. 행 D: 구분 빈 값, 금액 `1000`. | A `-1000`(수입), B `+1000`(지출), C `-1000`(수입으로 읽힘, `abs` 없음), D `+1000`(지출). |
| T-08 | R-15 | `TradeImport`, `inflows_positive`: `qty=10, price=150` / `qty=-5, price=2500`. `inflows_negative`: `qty=10, price=150`. | `1500` / `-12500` / `-1500`. 활동 라벨은 `Buy` / `Sell` / `Buy`. |
| T-09 | R-10, R-40 | 계정 `KRW` 통화, 통화 열 설정 안 함. 또 통화 열을 설정했지만 셀이 빈 행. | 두 경우 모두 entry 통화는 `KRW`(둘째는 `row.currency`가 `default_currency`로 채워짐). |
| T-10 | R-17 | 태그 셀 `"a|b"`, `"a,b|c"`, `"a\\,b"`, `""`. | `["a","b"]`, `["a","b|c"]`, `["a,b"]`, `[""]`(빈 문자열 하나, 태그 매핑 키가 빈 값). |
| T-11 | R-40 | 계정 `A`에 수동 거래(2024-05-15, 지출 4500, `KRW`, 이름 "스타벅스", `external_id` 없음) 1건. CSV에 같은 값의 행 2줄. | 첫 줄은 기존 거래를 갱신(`import_locked = true`, 카테고리가 있으면 바꿈), 둘째 줄은 새 거래. 새 거래 1건만 `import_id`를 가진다. |
| T-12 | R-40 | 같은 값의 기존 거래가 `external_id`를 가진 provider 거래. | 중복 후보가 아니므로 새 거래가 만들어진다(이중 입력). |
| T-13 | R-40 | `import.account` 없음, 행 3의 계정 열 값이 "KB급여"이고 매핑이 비어 있다. | `MappingError` "Row 3: Account 'KB급여' is not mapped…", 모든 저장이 롤백, `status = failed`, `error`에 메시지. |
| T-14 | R-23 | 행 10,001개의 `TransactionImport` 게시. `AccountImport` 51행. | 둘 다 `MaxRowCountExceededError`, `status`는 `pending` 그대로. |
| T-15 | R-03 | 10MB + 1바이트 CSV. MIME `application/octet-stream`인 작은 CSV. | 둘 다 방금 만든 import를 지우고 알림. 후자는 확장자가 `.csv`여도 거부. |
| T-16 | R-18, R-20 | 가족에 카테고리 `식비`가 있고 CSV 카테고리 값이 `식비`, `교통:택시`(가족에 `교통` 없음), 빈 값. | `식비`는 기존 레코드에 짝지어짐, `교통:택시`는 `create_when_empty = true`(게시 때 최상위 `교통`과 자식 `택시`를 만들고 자식은 부모 색), 빈 값은 `create_when_empty = false`로 카테고리 없음. |
| T-17 | R-20 | `import.account` 없음, 계정 열 값이 빈 행이 있다. | 키 `""`의 계정 매핑이 무효라 `publishable?`이 거짓이고 게시되지 않는다. |
| T-18 | R-24 | `complete`인 import에 `ImportJob`이 다시 도착. | 경고 로그만 남기고 `import!`를 실행하지 않는다. |
| T-19 | R-28 | `importing`이고 `updated_at`이 7시간 전. (a) entry가 있음 (b) 없음. `reverting`이고 7시간 전. | (a) `complete`와 가족 sync 예약 (b) `failed` + "interrupted" 메시지. `reverting`은 `revert_failed`. |
| T-20 | R-28 | `importing`이고 마지막 변경이 61분 전 / 59분 전에 사용자가 취소. | 61분: `failed`와 메시지, 59분: 취소 불가 알림, 상태 그대로. |
| T-21 | R-58 | 세션 `expected_chunks = 3`에 청크 `sequence` 1, 3만 있다. | 게시 예약이 `ConflictError`("…missing sequences: 2")로 거부되고(409) `status`는 그대로. |
| T-22 | R-57 | 같은 `sequence`·같은 내용을 두 번 올림. 같은 `sequence`에 내용이 다름. | 첫째는 기존 청크 반환(중복 생성 없음), 둘째는 409 "chunk already exists with different content". |
| T-23 | R-60 | 같은 PDF를 두 번 업로드. 25MB + 1바이트 CSV. 확장자 `.csv`인데 내용이 PDF. | 둘째 업로드는 `DuplicateUploadError`로 기존 명세서를 알려줌. 25MB 초과는 `InvalidUploadError`. 내용 MIME이 확장자와 맞지 않으면 거부. |
| T-24 | R-62 | 명세서 힌트가 기관 "kb국민", 통화 `KRW`. 계정 A는 기관명 "KB국민은행"·통화 `KRW`, 계정 B는 이름만 "국민". | A는 0.45(기관 포함: "kb국민은행"에 "kb국민" 포함) + 0.05 = 0.50, B는 기관 힌트 점수 없음. A가 제안으로 저장됨. A와 같은 점수의 계정이 둘이면 제안 없음. |
| T-25 | R-61 | 파일명 `국민은행_거래내역.csv`, 헤더 `거래일자,출금,입금,잔액`. | 파일명은 영문·숫자 패턴이 없어 힌트·기간 없음, CSV 헤더는 `date|posted|transaction`을 포함하지 않아 기간 없음, `parser_confidence = 0.1`. |
| T-26 | R-63 | 계정 연결 명세서(기간 2024-05-01~31, 기초 1,000,000, 기말 1,200,000, `KRW`). 장부 `Balance`의 시작이 1,000,000.005, 끝이 1,200,000. | 기초 차이 0.005(≤ 0.01) `matched`, 기말 `matched`, 기간 변화량 차이 0.005 `matched`이므로 전체 `matched`. 장부 시작이 999,000이면 `mismatched`. |
| T-27 | R-51 | PDF 거래 행(2024-05-15, 4500)과 계정의 기존 entry(2024-05-17, 4500, 같은 통화, `external_id` 있음, 이름 다름). | 날짜 차이 2일(≤ 3)이라 일치로 보고 행을 만들지 않으며 그 entry에 명세서 증거 표시(`reconciled_by_statement_id`)가 붙는다. |
| T-28 | R-45, R-47 | Mint: `Transaction Type = debit`, `Amount = 8.55` / `credit`, `2000`. YNAB: `Outflow = $4.25`, `Inflow = $0.00`. | Mint 행 금액 `-8.55`·`+2000`, 게시 후 entry `+8.55`(지출)·`-2000`(수입). YNAB `-4.25`, 게시 후 `+4.25`(지출). |
| T-29 | R-46 | Actual: `Payee` 빈 값, `Notes = "Reconciliation balance adjustment"`, `Category_Group = Income`, `Category = Paycheck`. 둘 다 빈 행. | 이름 "Reconciliation balance adjustment", 카테고리 키 `Income: Paycheck`(R-20으로 최상위 `Income` 아래 `Paycheck`). 둘 다 빈 행은 이름 `Imported item`. |
| T-30 | R-48, R-49 | `CategoryImport`에 `A`의 부모가 `A`. `MerchantImport`에 이미 있는 이름 `스타벅스`. | 전자는 `own_parent` 오류로 전체가 롤백되고 `failed`. 후자는 기존 가맹점을 갱신하지 않고 건너뜀. |
| T-31 | R-44 | `AccountImport` 행: 유형 `Checking`→매핑 `Depository`, 이름 "급여통장", 금액 `1000000`, 날짜 빈 값, 대상 계정에 entry 없음. | 잔액 1,000,000인 `Depository` 계정이 만들어지고 오프닝 잔액 날짜는 2년 전. 51행 이상이면 R-23으로 게시 거부. |
| T-32 | R-26 | `complete`인 `TransactionImport`(새 entry 3, 기존 entry 갱신 1)를 되돌린다. | 새 entry 3건 삭제, 갱신된 기존 entry는 남음(다만 `import_locked`와 바뀐 카테고리는 되돌려지지 않음). 상태 `pending`, 행·매핑 유지. |
| T-33 | R-56 | API로 `TransactionImport` CSV를 `publish=true`로 올리고 `account_id` 없음, 카테고리 열 있음. | `sync_mappings`가 없어서 카테고리·태그 매핑이 없고, 계정 매핑이 없으므로 게시 job이 `MappingError`로 `failed`. `account_id`가 있으면 카테고리·태그는 비어 있는 채 입력된다. |
| T-34 | R-11 | `number_format = 1,234`(소수 없음) 형식, 금액 셀 `"1,234.50"`. 같은 셀을 `1,234.56` 형식으로 읽으면. | 앞은 `.`이 지워져 `"123450"`(100배, 오류 없음). 뒤는 `"1234.50"`. KRW 파일이라도 소수점이 있는 값에는 `1,234` 형식을 쓰면 안 된다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `import.rb:42-45`, `:103`, `:94-101`; `imports_controller.rb:113-114`, `:198-201`; `api/v1/imports_controller.rb:69-70`, `:179-183` | 직접 읽음. |
| R-02 | `import.rb:94-101`, C-10, C-11, `imports_controller.rb:39-66` | 전이는 각 메서드를 읽어 정리했다. |
| R-03 | C-33 `imports_controller.rb:84-148`, C-01 | 직접 읽음. 웹 `create`의 UI 폼 필드는 열지 않았다. |
| R-04 | C-34 `uploads_controller.rb:19-38`, `:125-138`, `:155-161`; `import.rb:861-870` | `save!(validate: false)`는 `before_validation`을 건너뛰고 `before_save :ensure_utf8_encoding`은 실행된다(콜백 정의 `import.rb:87-88`). 이 순서는 Rails 콜백 의미로 읽은 추론이다. |
| R-05 | C-03; `import.rb:47`, `:105`, `:861-870` | 따옴표 안 개행이 줄로 세어지는 것은 `String#lines`를 쓴 코드(`import.rb:700-702`)에서 읽은 추론. |
| R-06 | C-05 `import.rb:773-833`; `uploads_controller.rb:125-126` | "CP949·EUC-KR이 없다": `grep -rn "EUC-KR\|CP949" app lib --include=*.rb`가 결과 없음(2026-11-18, 기준 SHA). 놓쳤을 가능성: gem 내부(`rchardet`)는 보지 않았다. 업로드가 바이트열을 읽어 UTF-8 판정을 건너뛴다는 점은 `UploadedFile#read`의 반환 인코딩에 대한 일반 지식이라 추론이다(U-01). |
| R-07 | C-34 `configurations_controller.rb:21-38`, `:60-83`; `import.rb:861-870`; `views/import/configurations/_transaction_import.html.erb:25`; C-02 | "`date_format` 목록 검증이 없다": `grep -n "date_format" app/models/import.rb`에서 검증 줄이 없음(`validates` 목록 `:103-117`에 없음). 행 생성이 transaction이 아닌 것은 `configurations_controller.rb:29-31`에 transaction이 없는 것을 읽음. |
| R-08 | `import.rb:103-117`, `:765-771`, `:835-870` | 직접 읽음. |
| R-09 | C-06 `import.rb:647-694` | 직접 읽음. BOM: `grep -n "FEFF\|BOM" app/models/import.rb`가 결과 없음. 같은 문제를 `transaction_import.rb:162-164`, `:185-187`이 알고 있다(주석 "keep a BOM"). |
| R-10 | C-07 `import.rb:392-416`, `:639-645` | 직접 읽음. |
| R-11 | C-04 `import.rb:707-759`, `:56-61` | 직접 읽음. 예시 값은 정규식을 손으로 따라가 계산했다. |
| R-12 | `row.rb:21-23`, `:135-151`; `entry.rb:64`, `:684-686`; `import.rb:67-73`, `:210-243`; `schema.rb:867`, `:1406`; `family.rb:22-35` | `Date.strptime` 후행 문자열 거부는 Ruby 표준 동작에 대한 지식(U-03). 호출처: `detect_date_format`은 `qif_import.rb:543`, `metadata_detector.rb:189`에서만 호출(`grep -rn "detect_date_format" app`). |
| R-13 | C-09 `row.rb:25-31`, `:98-100` | 직접 읽음. UI 라벨: `_transaction_import.html.erb:60-64`("incomes are positive"). |
| R-14 | C-09 `row.rb:101-123`; `_transaction_import.html.erb:85-100`; `import.rb:765-771` | 직접 읽음. UI가 두 값을 따로 채우는 구조는 `_transaction_import.html.erb:85`, `:96`. |
| R-15 | `row.rb:25-27`, `:93-95` | 직접 읽음. |
| R-16 | C-08 `row.rb:4-9`, `:129-161`; `import.rb:456-458`; 유형별 `required_column_keys`(`transaction_import.rb:100-102`, `trade_import.rb:47-49`, `account_import.rb:47-49`, `category_import.rb:41-43`, `merchant_import.rb:28-30`, `rule_import.rb:22-24`); `cleans_controller.rb:6-19` | 직접 읽음. Mint·Actual·YNAB·PDF는 `date amount`(각 파일 `required_column_keys`). |
| R-17 | C-09 `row.rb:13-19`, `:40-90` | 직접 읽음. |
| R-18 | C-07 `import.rb:418-434`; C-13; `mapping.rb:7-14` | "삭제 범위에 import 조건이 없다": `import.rb:431`의 `mapping_class.where.not(id: …)`에 `for_import`가 없음을 읽음. 기본 scope 여부: `mapping.rb` 전체(45줄)에 `default_scope` 없음. 다른 import에 실제로 영향을 주는지는 실행하지 않았다(U-04). |
| R-19 | `mappings_controller.rb:7-46`; C-13 `mapping.rb:34-44`, `category_mapping.rb:31-39`, `account_mapping.rb:13-21` | 직접 읽음. `internal_new_resource`는 `mapping.rb:2`. |
| R-20 | C-13 | 직접 읽음. `Category::COLORS`, `suggested_icon` 값은 열지 않았다. |
| R-21 | `imports_controller.rb:150-166`; `cleans_controller.rb:6-19`; `confirms_controller.rb:6-12`; `import.rb:444-470` | 직접 읽음. |
| R-22 | `rows_controller.rb:7-24`; `row.rb:33-37` | 직접 읽음. `number_format` 미적용은 `update_and_sync`가 `sanitize_number`를 안 부르는 것을 읽은 추론. |
| R-23 | C-10 `import.rb:246-253`, `:599`, `:631-633`; `imports_controller.rb:39-50`; `account_import.rb:72-74`; `sure_import.rb:162-177`, `:219-221`; `jobs/import_job.rb:1-7` | 직접 읽음. 웹이 `RuntimeError`를 잡지 않는 것은 `imports_controller.rb:48-50`의 rescue가 한 종류뿐인 것을 읽음. |
| R-24 | C-10 `import.rb:276-303` | 직접 읽음. |
| R-25 | `import.rb:635-637`, 유형별 `import!`(C-14, C-17~C-19) | "중복 판정이 없다": `trade_import.rb`, `mint_import.rb`, `actual_import.rb`, `ynab_import.rb`의 `import!`에서 `find_duplicate_transaction` 호출이 없음(`grep -n "find_duplicate" app/models/*_import.rb`가 `transaction_import.rb:51`, `pdf_import.rb:449`만 반환). |
| R-26 | C-10 `import.rb:305-348`, `:481-483`, `:608-615`; `jobs/revert_import_job.rb`; `monarch_import.rb:326-329`; `pdf_import.rb:522-539` | "분류·가맹점·규칙은 `revert` 재정의 없음": `grep -n "def revert\|revert_derived_state" app/models/*_import.rb`가 `sure_import.rb:259`, `monarch_import.rb:326`, `pdf_import.rb:522·537`만 반환. 되돌리기 화면이 그 유형에 버튼을 보여주는지는 열지 않았다. |
| R-27 | C-11 `import.rb:266-268`, `:626-629`; `category_import.rb:33-35`; `monarch_import.rb:148-150` | 직접 읽음. |
| R-28 | C-11 `import.rb:5-14`, `:136-188`, `:313-334`; `imports_controller.rb:60-66`; C-28; `pdf_import.rb:18-61` | 직접 읽음. |
| R-29 | `imports_controller.rb:1-9`, `:198-248`; `import_guest_guardable.rb:1-14`; `import.rb:487-522` | 직접 읽음. `require_non_guest!`, `accounts_writable_by` 하위 쿼리(`writable_by`)의 정의는 열지 않았다([transactions](./transactions.md) R-68 참조). |
| R-30 | `imports_controller.rb:182-186`; `import.rb:119-122`; `monarch_import.rb:15-16` | "sync 미예약": `grep -n "after_destroy\|before_destroy" app/models/*import*.rb app/models/import/*.rb`가 `monarch_import.rb:15-16`만 반환. |
| R-31 | `import.rb:543-565`; `transaction_import.rb:146-152`; `imports_controller.rb:173-180` | 직접 읽음. |
| R-32 | `import.rb:362-374`; `trade_import.rb:57-67`; `account_import.rb:55-59`; `monarch_import.rb:205-217`; `sure_import.rb:125-129`; 분류·가맹점·규칙 `dry_run` | 직접 읽음. |
| R-40 | C-14 `transaction_import.rb:16-98`; C-16; `import.rb:643-645` | 직접 읽음. "같은 줄이 두 번이면…"은 `claimed_entry_ids`와 후보 쿼리(C-16 `:830`)를 따라간 결과. 이름이 항상 있다는 판단은 `import.rb:406`·`:639-641`. |
| R-41 | `transaction_import.rb:100-133` | 직접 읽음. |
| R-42 | C-15 `transaction_import.rb:2-14`, `:138-188`; `family/data_exporter.rb:6` | 직접 읽음. |
| R-43 | C-17 `trade_import.rb:1-109`; [investments-securities](./investments-securities.md) R-09~R-12 | 직접 읽음. |
| R-44 | C-18 `account_import.rb:4-41`; `opening_balance_manager.rb:30-75` | "같은 이름 중복 검사 없음": `account_import.rb:4-41`에 이름 조회가 없음을 읽음. |
| R-45 | C-19 `mint_import.rb:2-16`, `:22-41`, `:43-67`, `:91-100` | 직접 읽음. |
| R-46 | C-19 `actual_import.rb:4-39`, `:41-61`, `:85-113` | 직접 읽음. |
| R-47 | C-19 `ynab_import.rb:4-47`, `:49-69`, `:98-111`, `:141-153` | 직접 읽음. |
| R-48 | C-20 `category_import.rb:2-29`, `:64-84`, `:113-121` | 직접 읽음. |
| R-49 | C-20 `merchant_import.rb:2-16`, `:51-69` | 직접 읽음. |
| R-50 | C-20 `rule_import.rb:2-9`, `:72-122`, `:166-225`, `:406-417` | 조건·액션 해석 내부(`:227-404`)는 읽었으나 규칙 모델 정의는 열지 않았다. |
| R-51 | C-21 `pdf_import.rb:1-153`, `:195-293`, `:414-537`; `process_pdf_job.rb:1-89`; `imports_controller.rb:250-261` | `PdfImport::AiProcessor`와 LLM 호출 내부는 열지 않았다. 문서 유형 6종은 `import.rb:40`. |
| R-52 | C-22 `qif_import.rb`; C-35 `qif_parser.rb:37-39`; `uploads_controller.rb:101-123` | `QifParser` 본문(607줄)은 상수와 진입 메서드 이름만 봤다. |
| R-53 | C-23 `monarch_import.rb`; `uploads_controller.rb:71-95`; `configurations_controller.rb:9-19` | `Converter`·`Exports` 본문은 앞부분(`exports.rb:1-60`)만 봤다. |
| R-54 | C-24 `sure_import.rb`; `imports_controller.rb:332-360`; `uploads_controller.rb:42-69` | `Family::DataImporter`, `SureImport::Preflight` 본문은 열지 않았다. |
| R-55 | C-25 `import/preflight.rb:16-168`, `:266-312` | 직접 읽음. 라우트는 `routes.rb:862-865`. |
| R-56 | C-26 `api/v1/imports_controller.rb:65-151` | 직접 읽음. "`sync_mappings`를 부르지 않는다": 컨트롤러 전체(414줄)에서 `sync_mappings` 호출이 없음을 읽음. |
| R-57 | C-27 `import_session.rb:103-211`, `:313-335`; `api/v1/import_sessions_controller.rb:10-57`, `:84-96` | 직접 읽음. |
| R-58 | C-27 `import_session.rb:230-282`, `:291-311`, `:386-433`; `jobs/import_session_job.rb` | 직접 읽음. |
| R-59 | C-28 `import_session.rb:40-101`; `sync_cleaner_job.rb:14-21`; `family_export.rb:42-72` | 직접 읽음. |
| R-60 | C-29 `account_statement.rb:22-30`, `:76-126`, `:137-231`; `account_statements_controller.rb:41-69`, `:146-150` | 직접 읽음. 내용 MIME 감지(`Marcel`)는 gem 동작이라 열지 않았다. |
| R-61 | C-30 `metadata_detector.rb:7-132`, `:134-203`, `:212-223` | "한글 파일명·헤더는 걸리지 않는다"는 정규식을 따라간 추론(`meaningful_filename_hint`의 `[^a-z0-9]` 제거, 날짜 헤더 정규식 `date|posted|transaction`). `TextMetadataParser`(PDF 텍스트 정규식)는 상수 이름만 봤다. |
| R-62 | C-31 `account_matcher.rb:6-114`; C-32 `account_statement.rb:234-284`; `account_statements_controller.rb:71-133` | 직접 읽음. |
| R-63 | C-32 `account_statement.rb:305-381` | 직접 읽음. |
| R-64 | `pdf_import.rb:159-193`; `account_statement.rb:36`, `:234-246`; `imports_controller.rb:189-192`, `:233-238` | 직접 읽음. |
| T-01~T-33 | 해당 R-ID의 근거 | 모두 코드를 손으로 따라 계산했다. 실행으로 확인한 것은 없다. T-02는 U-03에 의존한다. |

### 2.2 코드 읽는 순서

`imports_controller.rb`(진입, 분기) → `import.rb`(상태·공통 알고리즘) → `import/row.rb`(검증·부호) → `import/*_mapping.rb` → `transaction_import.rb`(대표 유형) → 나머지 유형은 R-43~R-54 표의 C-ID. 원본의 구현 전략은 행을 문자열로 먼저 저장하고(`import_rows`) 검증과 변환을 게시 시점까지 미루는 것이다. 사용자가 중간에 설정을 바꾸면 행을 처음부터 다시 만든다.

### 2.3 비교·재사용 출처

원본 코드를 복사하지 않았다. 중복 판정 규칙은 [provider-import-adapter](./provider-import-adapter.md) R-15와, 거래 부호는 [money-currency-rules](./money-currency-rules.md) R-36과, 거래 변환(`convert_to_trade`)은 [transactions](./transactions.md) R-64와 맞닿는다.

### 2.4 검토 기록

`draft`다(미결정 U-01~U-04가 남았고 선행 스펙도 `draft`). 2026-11-18에 한 점검의 범위는 다음과 같다.

- **독립 검토(검토자 서브에이전트 1명)**: 공통 파이프라인과 KB CSV 경로(R-03~R-17, R-40~R-42)를 중심으로 R-ID 약 50개, 부재 주장 R-12·R-18·R-25·R-56 반증 시도, 계산값 재계산. 중요 불일치 2건(R-25 재게시, R-61 힌트), 사소 8건, 보완할 누락 6건이 나왔다. 작성자가 전부 반영했고 T-34를 추가했다. R-33~R-39는 번호만 빈 것으로 확인했다.
- **메인 표본 점검**: R-25(`publish_later`와 `ImportsController#publish`에 `complete` 검사 없음, `import.rb:246-253`, `imports_controller.rb:39-50`), R-11(구분자 `,` 형식이 `.`을 지움, `import.rb:738-748`), R-06(`try_common_encodings`가 UTF-8 확인 없이 목록 순서대로 시도, `import.rb:818-833`)을 원본에서 직접 확인했다.
- **대조하지 못한 것**: Ruby 실행 결과(`strptime` 후행 문자열, rchardet 감지, U-01~U-03), `Family::DataImporter`·`QifParser`·`MonarchImport::Converter`·`PdfImport::AiProcessor` 본문(호출 경계만), R-32·R-50~R-54 해석 내부, KB 실제 파일 형식.
- 재구현: 미수행.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-06 | 업로드 때 BOM 확인, UTF-8 엄격 검증, 실패하면 CP949로 변환, 그래도 실패하면 오류로 거부한다. 감지기 신뢰도에 기대지 않는다. | KB 파일은 CP949일 수 있고(미확인) 원본은 후보에 없다. 조용히 깨지는 것보다 오류가 낫다(추론). | 인코딩 판정 함수 추가. T 사례: CP949 샘플이 한글 그대로 저장된다. |
| R-09 | 헤더 정규화에서 BOM을 제거한다. | 원본은 첫 열 별칭이 실패할 수 있다(U-02). | T-25 계열에서 첫 열이 BOM이어도 같은 결과. |
| R-12 | 날짜 파서에 "시각 부분 무시" 옵션을 둔다(KB 거래일시). 행 검증이 미래 날짜를 거부하는 규칙은 사용자 설정으로 둔다. | 거래일시 열을 전처리 없이 쓰기 위해(추론). | `date_format`에 시각 접미사 허용 플래그. |
| R-14 | 입금·출금이 따로 있는 열(KB 형식)을 `deposit_col`·`withdrawal_col` 두 열로 받는 전략을 추가한다. | 원본은 금액 열이 하나뿐이라 KB 형식은 전처리가 필요하다. | 전략 `two_columns` 추가, 금액 = 입금 − 출금(내부 부호는 지출 양수이므로 출금 − 입금). |
| R-18 | 매핑 삭제를 해당 import의 매핑으로 한정한다. | U-04, 다른 import의 매핑 유실 방지. | 삭제 쿼리에 `import` 조건. |
| R-11 | 천 단위 `,` 형식에서 `.`이 있으면 거부하거나 소수로 처리한다. | 원본은 `1,234.50`을 `123450`으로 읽어 오류 없이 100배가 된다(T-34). | `1,234` 형식 숫자 파서의 검증 추가. |
| R-24 | `import!`의 커밋 뒤 sync 예약 실패가 `failed`로 기록되지 않게 `rescue` 범위를 나눈다. | 원본은 데이터가 커밋됐는데 `failed`가 되어 재시도 시 이중 입력 위험이 있다(R-25, `TransactionImport` 외). | 상태 `complete` 후 sync 실패는 경고만. |
| R-23, R-25 | 예약 단계에서 `complete` import의 게시를 거부한다. | 원본은 직접 요청이 `complete`를 `importing`으로 되돌려 재실행한다(R-25). | `publish_later`에 `status` 검사. |
| R-25 | 모든 유형에 중복 판정을 넣거나 `Import` 단위 멱등 키(파일 `checksum`)를 둔다. | `TradeImport`·Mint·Actual·YNAB는 재실행이 이중 입력이다. | 파일 `checksum` 유일 검사. |
| R-26 | 분류·가맹점·규칙 import를 되돌릴 때 만든 레코드를 지우거나, 되돌리기를 아예 막는다. | 원본은 상태만 `pending`으로 돌아가고 레코드가 남는다. | 되돌리기 가능 유형 목록. |
| R-56 | API 생성에서도 매핑 동기화를 실행한다. | 원본 API는 카테고리·태그 매핑이 없어 조용히 비워진다(T-33). | `generate_rows` 뒤 `sync_mappings`. |
| R-61 | 파일명 힌트의 "의미 있는지" 판정을 정규화본이 아니라 저장값 기준으로 하고 한글을 허용한다. | 원본은 판정이 영문 정규화본이라 순수 한글 파일명(`국민은행_거래내역.csv`)에서 힌트가 없다(T-25). | 힌트 판정에 한글 허용. |
