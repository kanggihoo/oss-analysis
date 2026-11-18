---
sha: "1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a"
created: 2026-11-17
updated: 2026-11-17
sources:
  - repos/sure/README.md
  - repos/sure/docs/clients.md
  - repos/sure/docs/llm-guides/architecture.md
  - repos/sure/docs/hosting/mcp.md
  - repos/sure/config/routes.rb
  - repos/sure/app/models/import.rb
  - repos/sure/app/models/provider/registry.rb
  - repos/sure/Gemfile
---

# Sure Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/we-promise/sure`
- **기준 SHA**: `1cd94e66182e276d9cd5ceab9c4ad8e6646cac1a` (2026-11-16)
- **작업트리 상태**: Clean
- **분석 목적**: 재구현. 2026-11-17 결정: Ruby가 아닌 다른 언어로 구현할 예정이라, 스펙은 Rails 관례가 아니라 동작과 규칙으로 쓴다. 은행·증권·암호화폐 연동은 사용자가 따로 만들고, Sure의 기존 연동 구조와 연동 밖 기능을 가져온다(2절 "가져올 범위").
- **라이선스**: AGPL-3.0 (`LICENSE`, 저장소 루트). `mobile/assets/icons/lucide/LICENSE`는 ISC(아이콘 한정). README는 Maybe Finance(archived)의 community fork이고, "Maybe" 이름·로고는 사용 금지라고 쓴다.
- **분석 대상 제품**: 루트 Rails 앱(web·API·MCP·background job), `desktop/`(Tauri 2 macOS shell), `mobile/`(Flutter 앱), `charts/sure`(Helm chart)
- **스펙 범위**: 2026-11-17 승인(권장 + 선택 + 공유 계약 3): 행 1, 2, 3, 4, 8, 10, 11, 12, 13, 14, 15와 공유 계약 금액·통화 규칙·Sync 파이프라인·Provider 어댑터 계약 · 제외: 행 5~7(개별 provider, 이유: 사용자가 직접 구현), 9, 16~20(이유: 프레임워크 배관·클라이언트·운영), 공유 계약 Family 테넌시(승인 범위 밖)

---

## 2. 프로젝트 개요

Sure는 개인 재무·자산 관리 앱이다. 은행·카드·투자·암호화폐·부동산·차량·대출 계정을 한곳에 모아 순자산, 현금흐름, 지출, 예산, 목표를 보여 준다. Docker로 self-host하는 것이 기본이고(`docs/hosting/docker.md`), 웹 외에 macOS 앱, Flutter 모바일 앱, HTTP API, MCP endpoint로도 같은 서버 데이터에 접근한다(`docs/clients.md`).

기술 스택은 Rails 8.1 + PostgreSQL + Redis + Sidekiq + Hotwire(Turbo·Stimulus)다(`Gemfile`). `config.app_mode`가 `managed`와 `self_hosted`로 갈리고(`config/application.rb:40`), 같은 코드가 호스팅 서비스와 self-host를 같이 지원한다.

데이터 모델의 중심은 `Family`(테넌트)가 `Account`를 소유하고, `Account`가 `accountable`(Depository·Investment·Crypto·Property·Vehicle·OtherAsset·CreditCard·Loan·OtherLiability)로 종류를 위임하며, `Entry`가 `Valuation`·`Transaction`·`Trade` 중 하나를 가리키는 구조다(`docs/llm-guides/architecture.md`, 코드 확인은 미열람이라 문서 기준).

### Feature map

한 행은 사용자가 보는 동작 묶음 하나다. 이번 세션은 `config/routes.rb`, 모델·컨트롤러·job 디렉터리 이름, `Provider::Registry`, `Import::TYPES`, `docs/`를 대조했고 **각 기능의 본문 흐름은 열지 않았다**. 그래서 검증 수준은 "진입점·등록부 존재"까지만 `코드 확인`이고, 동작 설명은 `추론`이다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1 | 계정·잔액·순자산 | 계정 9종을 수동 등록하고, 일별 잔액과 순자산을 계산한다. 계정마다 통화가 다르다 | `app/models/account.rb`, `concerns/accountable.rb`, `balance/materializer.rb`, `balance_sheet.rb` | 핵심 | `capabilities/account-balances.md` · draft | 코드 확인(파일 존재) / 추론(동작) |
| 2 | 거래 관리 | 거래 CRUD, 분할(split), 일괄 수정·삭제, 첨부, 검색, 보류 거래 중복 병합 | `transactions_controller.rb`, `entry.rb`, `transaction.rb`, `entry_search.rb` | 핵심 | `capabilities/transactions.md` · draft | 코드 확인(routes) / 추론 |
| 3 | 이체 매칭 | 두 계정의 입출금을 이체로 묶고, 자동 후보 제안, 거절 기록 | `transfer.rb`, `family/auto_transfer_matchable.rb`, `rejected_transfer.rb`, `auto_matches_controller.rb`, `transfer/creator.rb`, `transfer/matcher.rb`, `transfer_matches_controller.rb`, `transaction/transferable.rb` | 핵심 | `capabilities/transfer-matching.md` · draft | 코드 확인(파일) / 추론 |
| 4 | 투자·시세 | 보유종목·매매 기록, 종목 시세·환율·부동산 가치를 외부 provider에서 가져와 평가액 계산 | `holding.rb`, `trade.rb`, `security.rb`, `exchange_rate.rb`, `provider/registry.rb` (CONCEPTS: exchange_rates, securities, llm, property_valuations, classification) | 핵심 | `capabilities/investments-securities.md` · draft | 코드 확인(registry) / 추론 |
| 5 | 은행·카드 연동 패밀리 | 외부 aggregator로 계정·거래를 가져온다. Plaid(US/EU), SimpleFIN, Lunchflow, Enable Banking, Akahu, Up, Monobank, Fio, Sophtron, Mercury, Brex, Wise, TrueLayer, Redbark, FinanceKit | `app/controllers/*_items_controller.rb`(27개), `family/*_connectable.rb`, `provider/*_adapter.rb`, `account/provider_import_adapter.rb` | 핵심 | 미작성(패밀리 한 행) | 코드 확인(routes·파일명) / 미확인(provider별 차이) |
| 6 | 증권 연동 패밀리 | 증권사 계좌·체결을 가져온다. IBKR, Questrade, Trading212, Trade Republic, SnapTrade, Sharesight, Indexa Capital | 위와 같음, `trade_republic_websocket.rb`(WebSocket 방식은 고유 흐름) | 핵심 | 미작성(패밀리) | 코드 확인(파일명) / 미확인 |
| 7 | 암호화폐 연동 패밀리 | 거래소(Binance, Coinbase, Coinspot, Coinstats, Kraken)와 온체인 지갑(Bitcoin, EVM, Solana, Cosmos, Polkadot)을 가져온다 | `onchain/*_adapter.rb`, `onchain_wallet_items_controller.rb`, `provider/{etherscan,solana_rpc,mempool_space,...}.rb` | 핵심 | 미작성(패밀리) | 코드 확인(파일명) / 미확인 |
| 8 | 가져오기(Import) | 파일로 거래·보유·계정·분류·규칙·가맹점을 넣는다. 13종: Transaction, Trade, Account, Mint, Actual, YNAB, Monarch, Category, Rule, Merchant, PDF, QIF, Sure. 계정 명세서 보관(statement vault)도 포함 | `app/models/import.rb:42`(`TYPES`), `imports_controller.rb`, `pdf_import.rb`, `account_statement.rb` | 핵심 | `capabilities/imports.md` · draft | 코드 확인(`TYPES` 상수) / 추론 |
| 9 | 내보내기·백업 | 가족 데이터 전체 export, 월별 리포트 CSV, 청구 일정 iCal feed | `family_exports_controller.rb`, `family/data_exporter.rb`, `bills_feeds_controller.rb` | 부속 | 미작성 | 코드 확인(routes) / 추론 |
| 10 | 거래 분류 자동화 | 규칙(조건·동작), Bayes 분류, LLM 자동 분류, 가맹점 자동 감지, 비슷한 가맹점 채우기 | `rule/*`, `rule/action_executor/*`(13개), `family/auto_categorizer.rb`, `family/bayes_categorizer.rb`, `settings/classifiers_controller` | 핵심 | `capabilities/transaction-classification.md` · draft | 코드 확인(파일) / 추론 |
| 11 | 예산 | 월별 예산, 카테고리별 배정·이월(rollover), 예산 공유 | `budget.rb`, `budget_category.rb`, `budget/rollover_calculator.rb`, `budgets_controller.rb`, `budget_share.rb`, `budget_ownership.rb` | 핵심 | `capabilities/budgets.md` · draft | 코드 확인(파일) / 추론 |
| 12 | 목표(Goal)와 Plan | 저축 목표와 연결 계정, pledge(적립 약속)와 거래 자동 대조, 예산+목표를 묶는 Plan 화면(preview 기능) | `goal.rb`, `goal_pledge/`, `docs/llm-guides/goals.md`, `plans_controller.rb` | 핵심 | `capabilities/goals.md` · draft | 코드 확인(문서·컨트롤러) / 추론 |
| 13 | 정기 거래·청구서 | 반복 지출·수입 식별, 청구서 일정, 가격 변동 감지, 급여 계획(paycheck planner) | `recurring_transaction/*`(pipeline·identifier·matcher·paycheck_planner), `bills_controller.rb`, `recurring_occurrences_controller.rb`, `recurring_allocations_controller.rb`, `identify_recurring_transactions_job.rb` | 핵심 | `capabilities/recurring-transactions.md` · draft | 코드 확인(파일) / 추론 |
| 14 | 대시보드·리포트·인사이트 | 순자산 차트, 현금흐름 Sankey, 지출 추이, 투자 요약, 위젯 배치 커스터마이즈. 인사이트 생성기 8종(예산, 현금흐름 경고, 유휴 현금, 목표 소진, 순자산 마일스톤, 저축률 변화, 지출 이상, 구독 점검) | `pages_controller.rb#dashboard`, `income_statement/*`, `reports_controller.rb`, `insight/generators/*` | 핵심 | `capabilities/reports-insights.md` · draft | 코드 확인(파일) / 추론 |
| 15 | AI 어시스턴트 | 채팅으로 계정·거래·예산을 묻고 일부는 쓰기까지 한다. 내장 assistant(function tool 약 50개)와 외부 assistant 둘 다 지원. OpenAI·Anthropic·OpenAI 호환 endpoint, 토큰 예산, 벡터 검색(pgvector·Qdrant·OpenAI)으로 가족 문서 검색 | `assistant/builtin.rb`, `assistant/function/*`, `assistant/external.rb`, `ai/router.rb`, `vector_store/*`, `chats_controller.rb` | 핵심 | `capabilities/ai-assistant-tools.md` · draft | 코드 확인(파일) / 추론 |
| 16 | MCP 서버 | 외부 AI 클라이언트(Claude Desktop 등)가 JSON-RPC로 Sure 도구를 호출. OAuth 2.0 동적 등록 또는 정적 bearer token | `mcp_controller.rb`, `oauth_registration_controller.rb`, `oauth_metadata_controller.rb`, `docs/hosting/mcp.md` | 핵심 | 미작성 | 코드 확인(routes·문서) / 추론 |
| 17 | 공개 API v1 | API key로 계정·거래·거래 분할·예산·카테고리·규칙·import(청크 업로드)·채팅·인사이트 등을 조작. OpenAPI 문서 | `config/routes.rb` `api/v1`, `app/controllers/api/v1/*`, `docs/api/openapi.yaml` | 핵심 | 미작성 | 코드 확인(routes) |
| 18 | 인증·접근 제어 | 비밀번호, MFA(TOTP), passkey(WebAuthn), OIDC·SAML·Google·GitHub SSO, 초대, 역할(guest·member·admin·super admin), 계정 단위 공유, 관리자 impersonation | `sessions_controller.rb`, `mfa_controller.rb`, `sso_provider.rb`, `account_sharings_controller.rb`, `admin/*` | 핵심 | 미작성 | 코드 확인(파일) / 추론 |
| 19 | 클라이언트 | macOS 앱(Tauri, 웹을 감싸는 shell), Flutter 모바일(로그인과 계정 잔액 중심), PWA, 푸시 알림 | `desktop/`, `mobile/`, `pwa_controller.rb`, `push_subscription/` | 부속 | 미작성 | 코드 확인(디렉터리·`docs/clients.md`) |
| 20 | 운영·배포 | Docker compose, Helm chart, Stripe 구독(managed 모드), Sentry·Langfuse·OpenTelemetry, 시스템 상태 화면, 평가(eval) 도구 | `compose.example.yml`, `charts/sure`, `stripe/`, `app/models/eval/*`, `admin/system_health` | 부속 | 미작성 | 코드 확인(파일) / 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 것. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| Sync 파이프라인 (`Sync`가 item·account·family를 순회하고 job이 실행) | 5, 6, 7, 4 | `sync.rb`, `sync_job.rb`, `sync_schedule.rb`, `provider/syncable.rb`, `family/syncer.rb` | `capabilities/sync-pipeline.md` · draft | 코드 확인(파일명) / 추론 |
| 금액·통화 규칙 (`Money`는 자동 환산 안 함, 입력 부호: 음수가 유입) | 1, 2, 4, 14 | `lib/money.rb`, `exchange_rate.rb`, `docs/llm-guides/architecture.md` | `capabilities/money-currency-rules.md` · draft | 문서 기준(코드 미열람) |
| Family 테넌시와 접근 범위 (`Current.family`, `accessible_accounts`) | 전부 | `current.rb`, `family.rb`, `account_share.rb` | 미작성 | 문서 기준(코드 미열람) |
| Provider 어댑터 계약 (`import_transaction` 등으로 외부 데이터를 내부 Entry로) | 5, 6, 7 | `account/provider_import_adapter.rb`, `docs/llm-guides/providers.md` | `capabilities/provider-import-adapter.md` · draft | 코드 확인(파일명) / 추론 |

**대조한 범위와 미탐색 영역**
- 대조: README, `docs/clients.md`, `docs/roadmap.md`, `docs/llm-guides/architecture.md`·`goals.md`, `docs/hosting/mcp.md`, `config/routes.rb`(web·api/v1·admin·webhooks), `app/models` 디렉터리 이름, `Provider::Registry` 앞부분, `Import::TYPES`, `Gemfile`
- 문서와 구현의 차이: 확인하지 않음
- 미탐색: 모든 기능의 본문 흐름, `db/schema.rb`, `app/components`·`app/javascript`(UI), `test/`·`spec/`(기본 제외), `docs/llm-guides/{wealth-agent-harness,wealth-blueprint,harness-adapters}.md`(AI 에이전트 설계 문서로 보이며, 읽으면 15번의 방향이 달라질 수 있음), provider별 차이(5~7번 패밀리 내부), Plaid·Stripe 외 webhook
- 숫자 출처: 연동 컨트롤러 27개는 `ls app/controllers | grep _items_controller`, function tool 약 50개는 `app/models/assistant/function/` 파일 수를 센 근사값이다.

### 가져올 범위 (2026-11-17 사용자 결정)

결정: KB국민·키움·업비트 연동과 한국 종목 시세는 사용자가 따로 만든다. Sure에서는 기존 연동 구조와 연동 밖 기능을 가져온다. 소스에 없는 것(업비트·키움·KB·한국 시세)은 feature map 행으로 넣지 않는다.

확인한 사실: `app/`·`lib/`·`config/`에 업비트·키움·KB 코드가 없다. `config/locales`와 `config/locales/views/*`에 `ko.yml`이 없어 UI 번역은 영어 기준이다.

위 20행을 이 결정에 맞춰 나눈 표다. "원 #"은 위 표의 행 번호다.

| 구분 | 원 # | 가져올 것 | 검증 수준 |
|---|---|---|---|
| 가져올 기능 | 1~4, 10~18 | 계정·잔액·순자산, 거래, 이체 매칭, 투자 모델(Holding·Trade·Security와 시세 provider 구조), 분류 규칙, 예산, 목표, 정기 거래, 대시보드·인사이트, AI 어시스턴트, MCP, API v1, 인증. 계정이 여러 곳이라 이체 매칭(원 3)이 중요하다 | 코드 확인(파일 존재) / 추론(동작) |
| 가져올 구조 | 5~7의 개별 provider가 아니라 공통 구조 | 연동 한 건이 `Item`(자격증명·sync 단위) → `Account` → `Importer`(외부 데이터 수집) → `Processor`(내부 `Entry`로 변환) → `Syncer`로 이어지는 틀, `Account::ProviderImportAdapter`, 공유 계약의 Sync 파이프라인. 구조를 읽을 예시: `kraken_item/*`·`kraken_account/*`(거래소), `provider/trading212*.rb`(API 키 증권), `lib/generators/provider/`(뼈대 생성기), `docs/api/rails_provider_generator.md` | 코드 확인(파일명) / 추론(역할, 본문 미열람) |
| 가져올 기능 (CSV) | 8 | `TransactionImport`·`TradeImport` 등 파일 import, 열 매핑, 중복 제거. KB 파일 적용 시 확인할 곳은 아래 | 코드 확인(상수) / 미확인(KB 파일 실물) |
| 가져오지 않음 | 5~7의 개별 provider 구현, 9, 19, 20 | 해외 provider 구현 내용, 내보내기, 데스크톱·모바일·PWA, 운영·배포 | 사용자 결정 |

**코드 양 (2026-11-17, 파일 이름 규칙으로 센 줄 수, 기준 SHA `1cd94e6`)**

| 묶음 | 파일 | 줄 |
|---|---|---|
| 앱 코드 전체(`app/`·`lib/`·`config/`·`bin/`) | — | 약 358,500 |
| 제외: 개별 연동 provider(원 5~7) | 712 | 100,556 |
| 제외: `desktop/`·`mobile/`(원 19) | 313 | 56,152 |
| 제외: 운영·과금·eval·`charts/`(원 20) | 99 | 10,633 |
| 제외: 내보내기, PWA·푸시(원 9, 19) | 23 | 2,240 |
| **남는 앱 코드** | 1,850 | **188,769** (Ruby 125,269 · ERB 37,330 · JS 18,174 · CSS 1,648) |
| 처음부터 세지 않은 것 | | 테스트 307,114 · locale 217,598 · docs 32,688 · db 20,617 |

남는 188,769줄에는 행에 속하지 않는 것(mailer, 관리자 화면, `DS::*` 컴포넌트, 공통 JS)도 들어 있다. 행에 속하는 모델·컨트롤러·job만 따로 센 값(views·components·JS 제외, 하한)은 아래다.

| 행 | 줄 | 행 | 줄 |
|---|---|---|---|
| 1 계정·잔액 | 14,541 | 13 정기 거래 | 6,525 |
| 15 AI 어시스턴트 | 13,180 | 18 인증·접근 | 6,287 |
| 8 Import | 10,054 | 14 대시보드·인사이트 | 5,309 |
| 10 분류 자동화 | 8,436 | 2 거래 | 4,879 |
| 4 투자·시세 구조 | 7,114 | 공통 Sync·어댑터 | 3,489 |
| 17 API v1 | 5,671 | 12 목표, 3 이체, 11 예산, 16 MCP | 2,707 · 2,053 · 1,664 · 950 |

합계 약 92,900줄. 행 분류는 경로 이름 규칙이라 겹치거나 빠진 파일이 있을 수 있다(추론).

**CSV import에서 확인할 곳** (`app/models/import.rb`)
1. 인코딩: `rchardet`으로 감지하고(신뢰도 0.75 초과), 실패하면 `COMMON_ENCODINGS`(`:775`)를 시도한다. 이 목록에 `CP949`·`EUC-KR`이 없다(추론: CP949 파일은 감지에 의존).
2. 금액 컬럼: `AMOUNT_TYPE_STRATEGIES`(`:79`)는 `signed_amount`(부호 있는 한 컬럼)와 `custom_column`(금액 한 컬럼과 유입 여부 컬럼) 둘뿐이다. 입금액·출금액이 따로 있는 파일은 합치는 전처리가 필요하다(KB 파일 컬럼은 미확인).
3. 날짜 `YYYY.MM.DD`·`YYYYMMDD`는 `Family::DATE_FORMATS`에 있다(코드 확인).

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

미작성. 목적이 정해진 뒤 필요하면 그린다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: 사용자가 feature map을 보고 목적을 정한다. 위치는 그에 따라 확정한다.
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸
