---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-17
updated: 2026-11-18
---

# Next Session Plan: sure

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 스펙 범위 승인(행 1·2·3·4·8·10·11·12·13·14·15 + 공유 계약 3, 14개)
- [x] wave 0: 공유 계약 3개 작성, 독립 검토, 작성자 반영, 2.4 검토 기록. 셋 다 `draft`(미결정이 남아 `ready` 조건 미충족)
  - [money-currency-rules](./capabilities/money-currency-rules.md) 미결정 U-01~U-03
  - [sync-pipeline](./capabilities/sync-pipeline.md) 미결정 U-01~U-06
  - [provider-import-adapter](./capabilities/provider-import-adapter.md) 미결정 U-01

---

- [x] wave 1: `account-balances`(R-01~R-52), `transactions`(R-01~R-75), `investments-securities`(R-01~R-69) 작성, 독립 검토, 작성자 반영, 2.4 기록. 셋 다 `draft`
  - wave 0의 열린 질문 해소: 현재 잔액의 정본 경로(`set_current_balance`, account-balances R-22·R-23), `window_start_date` 의미(R-25)

- [x] wave 2: `transfer-matching`, `imports`, `transaction-classification`, `budgets`, `recurring-transactions` 작성, 독립 검토, 작성자 반영, 2.4 기록. 다섯 모두 `draft`
  - 미결정: transfer-matching U-01~U-05, imports U-01~U-04, transaction-classification U-01~U-03, budgets U-01~U-05, recurring-transactions U-01~U-03

- [x] wave 3: `goals`, `reports-insights`, `ai-assistant-tools` 작성, 독립 검토, 작성자 반영, 2.4 기록. 셋 다 `draft`. `budgets` U-01·U-02 해소
  - 미결정: goals U-01~U-04, reports-insights U-01~U-03, ai-assistant-tools U-01~U-06

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 사용자 결정 4건(스펙 적용 메모의 선택지): item Syncer의 `stale` 덮어쓰기(원본대로 / 종료 상태 보호), 3단 트리 취소 정체(원본대로 / 중간 노드 `finalize`), `end_date` 상한(뉴욕 오늘 / 로컬 오늘), `source` 닫힌 목록(원본대로 / 자유 문자열)
- [x] `Loan` 상환·이자 엔진(`Loan::PrincipalPayments` 421줄 등): 2026-11-18 사용자 결정으로 별도 스펙 없이 참고용으로만 둔다(현재 대출 없음). account-balances R-40의 인터페이스 수준만 유지
- [ ] 사용자 결정: 새 연동에 `set_current_balance`를 강제할지(account-balances 적용 메모, 권장: 강제), reverse opening anchor 날짜의 `end_balance` 처리((b) 조정 열로 anchor 금액에 맞춤 권장)
- [ ] 남은 미결정: transactions U-01, investments-securities U-01~U-05(분할 조정 여부, MIC 없는 조회, 날짜 기준 포함)
- [x] 가족 데이터 export·import(Sure NDJSON): 2026-11-18 사용자 결정으로 제외(imports는 호출 경계만 유지)
- [ ] wave 2의 원본-재구현 차이 결정(적용 메모 선택지): imports의 CP949·BOM·`1,234.50` 처리와 `complete` 재게시 거부, transaction-classification의 Bayes `word_split`·한글 정규화·LLM 정규화, recurring-transactions의 공휴일·시간대, budgets의 household 실적 범위
- [ ] 미결정을 `ready` 조건에서 어떻게 볼지: gem·프레임워크 동작이라 확인 한계로 옮길지(money U-01~U-03, sync U-01~U-05), 닫을지

---

## 3. 기능 스펙 후보

없음(승인 범위 안에서 진행 중).

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음 작업: 통합 검토(워크플로 4장 "통합 검토" 4항목). 승인 범위 14개 스펙은 모두 `draft`로 작성됨.

### wave 3 지시문에 반영할 경계 (wave 2에서 정해짐)

| 대상 | 규칙 |
|---|---|
| 행 14 `IncomeStatement` | budgets R-17·U-01이 입력·출력·제외 규칙 계약을 가정했다. 행 14가 이 계약을 실제로 쓰고 budgets U-01을 닫는다 |
| 행 12 `Goal.backing_within`(`earmarked_for_goals`, `free_cash`) | budgets U-02. 행 12가 해소처 |
| 행 15 AI 도구 | `match_transfer`·`review_transfer`·`unmatch_transfer`는 transfer-matching R-23·R-18, `update_budget`은 budgets R-38, bill 도구 9개는 recurring-transactions를 링크하고 중복하지 않는다 |
| 행 14 인사이트 | `subscription_audit`·`cash_flow_warning`은 recurring-transactions, 예산 인사이트는 budgets를 링크 |
| 행 17 API v1(승인 범위 밖) | 거래 `update`·`destroy` 권한 누락(transactions R-69), API 생성 import가 `sync_mappings`를 안 부름(imports R-56), `budget_categories` 조회의 이월 재계산은 각 스펙에 기록됨 |
| 가족 데이터 export·import(Sure NDJSON, `Family::DataImporter` 1,823줄) | imports는 호출 경계만 썼다. 행 9(내보내기)와 묶어 별도 행으로 둘지 사용자 결정 |

### wave 2 지시문에 반영한 경계 (wave 1에서 정해짐, 참고)

| 대상 | 규칙 |
|---|---|
| `Security::Resolver`를 부르는 행 8 | investments-securities R-09~R-12를 선행으로 두고 중복하지 않는다 |
| `convert_to_trade` | transactions R-64 소관. 행 8은 링크 |
| 분류 wizard(`transactions/categorizes_controller.rb`), `Rule::ActionExecutor::SplitTransaction`이 부르는 `split_once!` | 행 10은 transactions를 선행으로 두고 `bulk_update!`·분할 호출 경계만 쓴다 |
| `mark_as_recurring` | 행 13 소관(transactions는 넘김) |
| `Transfer` 삭제 시 상대 다리 해제(`transfer.rb:22,236-262`), `categorizable?`(transactions R-10이 사용) | 행 3 소관 |
| `AccountShare`·권한 4단계·`accessible_by`(transactions R-68, account-balances R-41·R-46이 쓴다) | 승인 범위 밖 Family 테넌시 공유 계약이 비어 있음. 통합 검토에서 스펙으로 만들지 정한다 |
| 환산 실패 정책 | account-balances R-37, investments-securities R-61, transactions R-72에 각각 정리됨. 통합 검토에서 공유 정의로 통일 |

### wave 0에서 정해진 경계 (wave 1 이후 지시문에 반영)

| 대상 | 규칙 |
|---|---|
| 환율(`ExchangeRate` 조회·fallback·적재) | money-currency-rules가 가졌다. 행 4는 링크하고 `Security::Price`와 증권 provider만 다룬다 |
| 부호 규칙 R-36~R-40(잔액 반영 포함) | money-currency-rules가 가졌다. 행 1은 선행으로 두고 balance 계산 세부만 쓴다 |
| 연결 해제(`AccountsController#unlink`) | provider-import-adapter R-65. 행 1은 중복해서 쓰지 않고 링크한다 |
| 보류 거래 수동 병합(`Transaction#merge_with_duplicate!`)과 중복 제안 처리 | 행 2(`transactions`) 소관. 어댑터 스펙은 기록 형식만 다룬다 |
| `Account::Syncer`가 부르는 `Balance::Materializer`의 `window_start_date` 의미 | 행 1에서 맞춘다 |
| `SyncCleanerJob`이 정리하는 `Import`·`ImportSession`·`FamilyExport`·`PdfImport` | 행 8 |
| `SyncPropertyValuationsJob`(`Sync`를 쓰지 않는 월간 부동산 시세 갱신) | 행 4 |
| 환산 실패 정책(항목 제외, 0, NULL, 1:1이 호출처마다 다름) | 행 1·2·4·14가 같은 문제를 만난다. 통합 검토에서 공유 정의로 확인 |
| `post-sync`가 부르는 transfer 자동 매칭·규칙 적용(`ApplyRulesJob`)·가맹점 로고 | 호출 경계만 sync-pipeline에 있고 본문은 행 3, 10 |

### 막힌 경로

| 시도 | 결과 | 재개 조건 |
|---|---|---|
| AASM, Sidekiq, sidekiq-cron, sidekiq-unique-jobs, `after_commit_everywhere` gem 소스 열람 | 이번에 열지 않음(sync U-01~U-05) | 사용자가 gem 소스 열람을 허용하거나, 확인 한계로 옮기기로 결정하면 |
| Rails 실행으로 동작 재현(`stale` 덮어쓰기, 삭제된 syncable 분기, 조기 확정 race) | 실행하지 않음(레포 AGENTS.md도 서버·마이그레이션 실행 금지) | 사용자가 실행을 허용하면 |

---

## 5. 참고 사항 및 후속 제안

- 한국 사용 관련: `provider-import-adapter`의 이름 비교 키가 `a-z0-9`만 남겨 한글 이름은 비어 있고, 투자 활동 라벨 추정도 영어 정규식뿐이다(R-26·R-27·R-38). 직접 연동은 `investment_activity_label`을 직접 넘겨야 한다. 생성기 템플릿의 `normalize_cash_amount`는 어댑터와 부호가 반대다. UI는 `ko.yml`이 없다.
- 작성자 서브에이전트는 `draft`로만 두고, `ready`는 메인의 원본 대조 점검 뒤에 정한다.
