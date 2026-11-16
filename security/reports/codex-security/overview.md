---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
---

# codex-security Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/openai/codex-security`
- **기준 SHA**: `173483d7c658be7a512c93d9559bf01a05d5b196` (main, 2026-11-13T18:38:24-08:00, "fix(plugin): preserve Windows helper exit codes (#2651)"). 전체 이력 clone이다. 기록은 [repo-metadata.txt](../../artifacts/codex-security/repo-metadata.txt).
- **작업트리 상태**: Clean
- **분석 목적**: 보안 검증을 하는 skill과 그 skill이 호출하는 코드(MCP 도구·helper·Python)의 소스를 이해한다(2026-11-16 사용자 정정). 취약점을 찾고 가르고 판정하는 지침이 skill 문서에 있고 코드가 어디까지 강제하는지를 본다. SDK(`cs` CLI)는 시작·마무리 담당이라 부속이다. 스펙을 어디에 쓸지(재구현·설계 참고 등)는 미정이다. 주제 폴더 목적은 [GUIDE.md](../../GUIDE.md).
- **라이선스**: Apache-2.0. `LICENSE`(루트)와 `sdk/typescript/LICENSE`를 열어 첫머리가 Apache License Version 2.0임을 확인했다(코드 확인). 추가 LICENSE 파일은 `git ls-files`에서 이 둘뿐이다. `plugins/codex-security/native/licenses/`(파일 1개, 네이티브 모듈 서드파티 고지 후보)는 열지 않았다.
- **분석 대상 제품**: 한 레포 안의 배포 단위 4개(README와 매니페스트 기준, 역할은 feature map 작성 때 코드로 확인한다).
  - `sdk/typescript/`: npm 패키지 `@openai/codex-security` 0.10.0. CLI 바이너리 `cs`·`codex-security`와 TypeScript SDK(`sdk/typescript/package.json`의 `bin`, `exports`)
  - `plugins/codex-security/`: Codex 플러그인 `codex-security` 0.1.95. skill 20개, Python 스크립트, MCP 앱, Rust 네이티브 모듈(`plugins/codex-security/.codex-plugin/plugin.json`)
  - `github-action/`: GitHub Action(`action.yml`, `github-action/README.md`)
  - `docker/`: 컨테이너 이미지와 workflow runner(`Dockerfile`, `compose*.yaml`, `docker/README.md`)
- **스펙 범위**: 승인(2026-11-16, 사용자): 행 1~11과 공유 계약 S1~S3(S1은 행 4, S2는 행 9, S3는 행 1이 소유). 진행 순서: 1단계 행 1 → 2·4·5·6·8, 2단계 행 3·11, 3단계 행 7·9·10(필요한 만큼만 좁혀서). · 제외: 행 12·13·14(이유: 사용자 제외, 선택 행이었고 선택하지 않음), 부속 15~17(이유: 사용자 제외). 2026-11-16에 선행 순환(행 2↔9)을 풀기 위해 행 2·9의 선행에서 S2를 빼고, 행 7의 선행에서 S1·S2를 뺐다. 경계는 각 스펙 안에서 정의한다

---

## 2. 프로젝트 개요

README는 이 도구를 "코드의 취약점을 찾고, 조사하고, 고치도록 돕는 것"으로 소개한다(미확인: README의 주장). 같은 워크플로를 Codex 안(플러그인 skill), 터미널(`cs` CLI), 자동화(TypeScript SDK·GitHub Action·컨테이너)에서 쓸 수 있다고 한다.

README가 나열한 기능(코드로는 아직 확인하지 않은 후보):

- 저장소·경로·Git 변경분 스캔. Deep 스캔은 Standard 스캔을 반복해 중복을 제거한 결과를 낸다.
- 후보 취약점 검증, 패치 생성, 기존 수정 검증
- `SECURITY.md` 초안 작성, threat model 저장·내보내기
- 저장된 스캔·finding 조회, 중복 판별, 사용자 rubric 기준 severity 평가, 소스·Git 이력 기반 owner 제안
- 외부 스캐너 결과 가져오기(`docs/scanner-imports/`)와 Codex Security Cloud 게시
- Linear·Jira·GitHub 추적, SARIF·JSON·CSV 내보내기, ServiceNow 내보내기
- 여러 저장소·컴포넌트 대상 자동화(CI, 컨테이너 bulk scan)
- 모델 제공자: OpenAI, Amazon Bedrock, OpenRouter, Fireworks AI, Cheaper Inference

### Feature map

> 2026-11-16 재구성. 처음 21행은 SDK(`cs` CLI) 기능 기준이었다. 사용자가 "보안 검증을 하는 skill과 그 skill이 호출하는 코드의 소스를 보고 싶다"고 정해, skill → 호출 대상(MCP 도구, helper, Python) 기준 17행으로 다시 나눴다. SDK 쪽은 부속 2행(15·16)으로 내렸다.

경로 표기: `SDK` = `sdk/typescript/src/`, `플러그인` = `plugins/codex-security/`, `MCP` = `플러그인/mcp-app/`. 검증 수준은 이번 세션에 연 범위만 `코드 확인`이고, 파일 이름·크기만 본 것은 `추론`이다. 행 번호와 분할은 제안이며, 스펙을 쓰면서 병합·분리하면 이 표를 고친다.

**읽는 법**

1. **검증 판단은 skill 문서에 있다.** 이 레포에는 AST·규칙 엔진 같은 정적 분석 코드가 없다(`grep`: `scripts`, `mcp-app/src`, `sdk/typescript/src`). 취약점을 찾고, 실제인지 가르고, 공격 경로를 따지는 기준은 `SKILL.md`·`references/*.md`이고, 모델이 따른다(코드 확인). 코드는 그 결과를 받아 형식을 검사하고 저장한다.
2. **스캔 종류마다 파이프라인이 다르다.** Standard와 Deep worker는 `references/core-scan.md` 하나로 발견·검증·판정을 한 번에 한다. 별도 phase skill(`finding-discovery`·`validation`·`attack-path-analysis`)은 호출하지 않는다고 각 SKILL.md가 적었다. phase skill은 diff 스캔(compact workbench diff), 구형 phase 스캔, 단독 요청에서 쓴다(코드 확인: 세 SKILL.md의 "Scan integration", `플러그인/references/scan-artifacts.md`의 Phase 1~4 절).
3. **skill이 부르는 것은 네 종류다.** (가) MCP 도구(`MCP/server.ts`, `MCP/src/server/compact-artifact-tools.ts`에 등록), (나) 셸 helper(`launch_codex_security_mcp --helper <이름>` → `MCP/helpers-main.ts` → `MCP/src/helpers/`), (다) Python(`플러그인/scripts/`, MCP 도구가 내부에서 `workbench_db.py`를 실행), (라) CLI(`codex-security import|publish|export`, `publish-findings` skill과 `sarif-adapter.md`만).
4. **SDK는 호출 대상이 아니라 시작·마무리 담당이다.** SDK가 Codex를 띄워 프롬프트로 skill을 따르게 하고, 모델이 끝난 뒤 확정·보고서·봉인을 한다. 의존은 SDK → 플러그인 한 방향이고 플러그인의 비테스트 코드는 SDK를 import하지 않는다(코드 확인).
5. **완료 책임이 호출자마다 다르다.** `cs scan`(SDK-owned)은 모델이 봉인 전 파일을 쓰고 끝내며 SDK가 확정한다. Codex 데스크톱(workbench-owned)은 모델이 `complete_codex_security_scan`까지 부른다. Deep은 coordinator가 확정한다(코드 확인: `플러그인/references/final-report.md` 6~12행 표).

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 (skill → 호출 코드) | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 호출자 모드·스캔 시작 | 같은 skill이 `cs scan`, Codex 데스크톱, Deep 중 누가 시작했느냐에 따라 스캔 등록·저장·완료 책임이 달라진다. 스캔 로직 자체는 포함하지 않는다 | `플러그인/references/final-report.md` 표, `references/scan-prologue.md`, `skills/security-scan/SKILL.md` 16~17행, `skills/security-scan/references/{sdk-files,scan-results,managed-scan,desktop-scan}.md` → `MCP/server.ts` `start_codex_security_standard_scan`·`start_codex_security_prompt_only_scan`·`get_codex_security_scan_context`·`update_codex_security_scan_progress`, `SDK/api.ts` `skillNameFor` | 없음 | 핵심 | [`capabilities/caller-modes.md`](./capabilities/caller-modes.md) · draft | 코드 확인(문서 표·도구 이름·`skillNameFor`) / 도구 동작은 추론 |
| 2 | Standard 감사 | 저장소·경로 전체를 한 번에 감사한다. baseline 감사자와 집중 조사자가 후보를 내고 같은 흐름에서 검증하며, 초안을 저장한다. phase skill은 부르지 않는다 | `skills/security-scan/SKILL.md`, `references/core-scan.md`·`baseline-auditor.md`·`focused-investigator.md`·`security-guidance.md`·`default-severity-rubric.md`(`static-finding-assessment.md`는 Standard 경로가 읽지 않아 행 5·11로 옮김) → MCP `record_codex_security_scan_draft`(`MCP/src/server/compact-artifact-tools.ts` 169행), helper `resolve-security-md`·`bind-repo-scopes`·`make-repo-scope-input`(`플러그인/scripts/dispatch_inventory_tool`은 skill이 부르지 않는 PATH 정리용 dispatcher라 행 10으로 옮김) | 1 | 핵심 | [`capabilities/standard-audit.md`](./capabilities/standard-audit.md) · draft | 코드 확인(`SKILL.md`·`core-scan.md` 전문) / worker 위임은 코드가 강제하지 않는다(부재 검색 확인). SDK가 `features.multi_agent_v2`(최대 9 스레드)를 켤 뿐이다 |
| 3 | Diff 감사 | PR·commit·branch·working tree 변경에서 생긴 취약점을 찾는다. 변경 파일 전체(삭제 포함)를 검토 단위로 삼고, 발견→검증→공격 경로를 단계별로 기록한다 | `skills/security-diff-scan/SKILL.md` → `prepare_codex_security_review_items`·`list_codex_security_review_items`(MCP), helper `generate-in-scope-files`(`MCP/src/helpers/generate-inventory.ts` `inventoryCommand`. `make-diff-rank-input`도 같은 함수가 구현하지만 이 skill은 부르지 않고 구형 `scan-artifacts-and-ledger.md` 경로만 부름), diff 대상 해석 `플러그인/scripts/workbench_setup.py` `require_diff_target`·`플러그인/scripts/workbench_db.py` `register-cli-scan` diff 분기, `SDK/targets.ts` `DiffTarget` | 1, 4, 5, 6 | 핵심 | [`capabilities/diff-audit.md`](./capabilities/diff-audit.md) · draft | 코드 확인(skill 앞부분, helper 이름·파일 존재) / 본문 나머지는 추론 |
| 4 | 후보 발견·정규화 | 범위 안 소스에서 공격자 입력→통제→sink를 추적해 후보를 만들고 ID·위치·증거·반증을 후보 ledger에 쌓는다. 최종 severity는 정하지 않는다 | `skills/finding-discovery/SKILL.md`(전문) → MCP `record_codex_security_discovery_candidates`(`compact-artifact-tools.ts` 110행)·`list_codex_security_candidates`·`list_codex_security_review_items`, `MCP/src/artifact-discovery.ts` `recordCodexSecurityDiscoveryCandidates`(실제 진입점. 정규화기 `normalizeCandidateBatch`를 worker thread로 실행), `MCP/src/helpers/normalize-candidates.ts`(562줄. 같은 정규화기의 CLI는 이 SHA에서 skill·reference·SDK가 부르지 않는 잔존 경로), `MCP/src/artifact-candidate-ledger.ts`·`deep-scan/artifact-contracts.ts` `candidateSchemaV1` | 1, S1 | 핵심 | [`capabilities/candidate-discovery.md`](./capabilities/candidate-discovery.md) · draft | 코드 확인(skill 전문, 도구 등록, ledger 앞부분) / `normalize-candidates` 본문은 추론 |
| 5 | 후보 검증 | 후보마다 소스 추적이나 허가된 재현으로 증거를 모으고 처분(reportable 등)·신뢰도·반증·증명 공백을 기록한다. 오탐 피드백(`false_positive_feedback.json`)을 증거로 읽는다 | `skills/validation/SKILL.md`(전문), `skills/validation/references/validation-guidance.md`, `플러그인/references/standalone-validation.md` → MCP `record_codex_security_candidate_validations`(`compact-artifact-tools.ts` 139행) → `MCP/src/artifact-candidate-ledger.ts` `recordCodexSecurityCandidateValidations`, `플러그인/schemas/tools/candidate-validations.schema.json`, `SDK/api.ts` `validate`(단독 실행) | 4, S1 | 핵심 | [`capabilities/candidate-validation.md`](./capabilities/candidate-validation.md) · draft | 코드 확인(skill 전문, ledger 쓰기 규칙: 기존 후보 전부를 정확히 한 번, 미지·중복 후보는 오류) / 재현 실행 규칙의 실제 강제는 미확인 |
| 6 | 공격 경로·severity 판정 | 검증을 통과한 후보의 공격자→영향 경로, 통제·전제, 영향·가능성, 최종 severity와 보고 여부(`reportable`/`deferred`/`ignore`)를 정한다 | `skills/attack-path-analysis/SKILL.md`(전문), `skills/attack-path-analysis/references/{severity-policy,attack-path-facts}.md`, `플러그인/references/default-severity-rubric.md` → MCP `record_candidate_attack_paths` → `artifact-candidate-ledger.ts` `recordCodexSecurityCandidateAttackPaths`, `플러그인/schemas/tools/candidate-attack-paths.schema.json` | 4, 5, S1 | 핵심 | [`capabilities/attack-path-severity.md`](./capabilities/attack-path-severity.md) · draft | 코드 확인(skill 전문, 도구 등록, ledger 함수 앞부분) / 정책 본문은 미독 |
| 7 | Deep 스캔 | Standard 감사를 반복하고 중복을 제거해 합치며, worker 사이 단서를 교환한다. 연속 감사에서 새 발견이 없거나 한도에 닿으면 멈춘다 | `skills/deep-security-scan/SKILL.md` → MCP `start_codex_security_deep_scan`(`server.ts` 892행), `MCP/src/deep-scan/`(`coordinator.ts`·`engine.ts`·`iteration.ts`·`worker-runner.ts`·`peer-notes.ts`·`same-fix.ts`), helper `copy-deep-review-input`, `플러그인/scripts/deep_scan_*.py`, `SDK/deep-scan.ts` `runDeepScan` | 1, 2, 4 | 핵심 | `capabilities/deep-scan.md` · 미작성 | 코드 확인(SKILL.md 앞부분, `runDeepScan`이 `mcp/server.mjs --deep-scan-engine` 실행, 디렉터리 목록) / 반복·종료 구현은 추론 |
| 8 | Threat model | 스캔 초반에 아키텍처·공격자·보호 자산을 모델로 만들어 초안에 담고, 이후 발견·검증의 입력으로 쓴다. 저장된 모델을 `threatmodel.md` 문서로 투영한다(그림 `threat-model-visualize`는 행 13) | `skills/threat-model/SKILL.md`, `플러그인/references/threat-model.md` → MCP `record_codex_security_scan_draft`의 `threatModel`, `MCP/src/threat-model-{schema,render,document,format}.ts`, `플러그인/scripts/threat_model_projection.py`(렌더만), 문서를 쓰는 호출자 `플러그인/scripts/finalize_scan_contract.py` `write_threat_model_projection_if_possible`·`플러그인/scripts/workbench_saved_results.py` `write_scan_draft` | 1 | 핵심 | [`capabilities/threat-model.md`](./capabilities/threat-model.md) · draft | 코드 확인(`core-scan.md`의 checkpoint 규칙) / 렌더·투영은 추론 |
| 9 | 스캔 초안·확정·봉인 | 모델이 낸 `threatModel`·`findings`·`reviewState`를 검증해 초안으로 저장하고, 완료 시 digest로 봉인해 보고서를 만든다. 누가 확정하는지는 행 1을 따른다 | MCP `record_codex_security_scan_draft` → `MCP/src/artifact-scan-draft.ts`(3,524줄)·`finding-normalization.ts`·`sealed-contract.ts`, MCP `complete_codex_security_scan`(`server.ts` 1567행), `플러그인/scripts/finalize_scan_contract.py`(3,471줄)·`validate_scan_contract.py`·`report_projection.py`, `플러그인/schemas/*.schema.json`, `references/final-report.md`·`finding-detail-fields.md` | 1 | 핵심 | `capabilities/scan-finalize.md` · 미작성 | 코드 확인(`validate_contract`가 finalizer 검증을 호출, 도구 등록) / 규칙 본문은 추론 |
| 10 | 입력 준비 helper | skill이 소스를 읽기 전에 쓰는 셸 helper: 범위 안 파일 인벤토리, `SECURITY.md` 상속 해석, 범위 바인딩, diff 파일 순위, 소스 미리보기 | `플러그인/scripts/launch_codex_security_mcp` → `MCP/helpers-main.ts` → `MCP/src/helpers/`(`resolve-security-md.ts`·`generate-inventory.ts`·`inventory-git.ts`(1,271줄)·`inventory-paths.ts`·`hosted-scope-inventory.ts`·`bind-repo-scopes.ts`·`rank-worklists.ts`·`source-preview.ts`) | 없음 | 핵심 | `capabilities/input-helpers.md` · 미작성 | 코드 확인(런처·helper 이름·파일·줄 수) / 본문은 추론 |
| 11 | 수정·수정 검증 | 검증된 finding을 패치하고(`fix-finding`), 기존 수정이 막는지 검증한다(`verify-fix`) | `skills/fix-finding/SKILL.md`, `skills/verify-fix/SKILL.md` → MCP `set_codex_security_finding_remediation`, `SDK/remediation.ts`, `SDK/api.ts` `patch`, `플러그인/scripts/workbench_remediation.py` | 1 | 핵심 | [`capabilities/fix-and-verify.md`](./capabilities/fix-and-verify.md) · draft | 코드 확인(skill 경로 지시) / 상태 처리는 추론 |
| 12 | finding 상태 관리 workbench | 스캔·finding·triage·remediation 상태를 SQLite에 저장하고 MCP 도구로 조회·변경한다 | MCP `set_codex_security_finding_triage`·`list_codex_security_findings`·`export_codex_security_findings`·`list_codex_security_scans` 등, `플러그인/scripts/workbench_db.py`(3,543줄)·`workbench_schema.py`·`workbench_finding_*.py`·`workbench_scan_*.py`, `MCP/src/workbench/` | S4 | 핵심 | `capabilities/workbench-store.md` · 미작성 | 코드 확인(도구 이름, MCP가 `workbench_db.py`를 자식 프로세스로 실행) / 스키마는 추론 |
| 13 | skill 전용 보조 워크플로 (패밀리) | 코드 연동이 약한 skill: finding triage, 패치 위험 평가, 의존성 alert 추적, 설계 hardening, 취약점 보고서, 설치 전 skill 점검, threat model 시각화 | `skills/{triage-finding,assess-patch-risk,resolve-dependency-alert,propose-security-hardening,vulnerability-writeup,check-skills,threat-model-visualize}/`, helper `validate-patch-risk-assessment`, `플러그인/schemas/patch-risk-assessment.schema.json`, `skills/threat-model-visualize/scripts/build_explorer.py` | 없음 | 핵심 | `capabilities/auxiliary-skills.md`(패밀리 1행) · 미작성 | 코드 확인(skill 이름·README 설명, 파일 존재) / 본문은 추론 |
| 14 | 가져오기·게시·티켓 skill ↔ CLI | 모델이 CLI를 셸로 실행하는 유일한 skill들: 외부 스캐너 findings를 `codex-security import`·`publish findings`로 저장하고, 티켓을 만들고, SARIF로 내보낸다 | `skills/publish-findings/SKILL.md`·`references/*`, `skills/track-findings/SKILL.md`(helper `validate-tracking-source`), `skills/cloud-findings/`, `플러그인/references/sarif-adapter.md`, `skills/publish-findings/scripts/collect_checkmarx.py` → `SDK/cli.ts` `imports`·`publication`·`export`, `SDK/import-scan.ts`, `SDK/publish.ts`, `SDK/*-findings.ts` | S4 | 핵심 | `capabilities/import-publish.md` · 미작성 | 코드 확인(skill의 CLI 호출 문장, 명령 등록) / 어댑터 공통 규칙은 추론 |
| 15 | SDK 런처: 스캔 시작·프롬프트·마무리 | `cs scan`이 등록 scan ID로 Codex thread를 열고 skill을 따르게 하는 프롬프트를 넘기고, 끝난 뒤 확정·보고서를 만든다. 비용·시간 한도와 취소 포함 | `SDK/api.ts` `CodexSecurity.run`·`#run`·`scanPrompt`·`skillNameFor`, `SDK/runtime.ts` `runWorkbench`·`pluginRuntimeProjection`, `SDK/cost.ts`, `SDK/scan-time-budget.ts`, `SDK/cli.ts` `createScanCommands` | 1, 9 | 부속 | `capabilities/sdk-launcher.md` · 미작성 | 코드 확인(`run`→`#run`→`scanPrompt`, `.mcp.json` 투영) / 비용·재시도는 추론 |
| 16 | SDK 주변 기능 (패밀리) | 설정 파일, 스캔 이력·재개·재실행·비교, severity 재분류·dedupe·owner 제안, `SECURITY.md` 생성, 다중 대상(components·bulk), 인증·제공자, Hosted 실행기, CLI 표면·MCP 설치 | `SDK/project-config.ts`, `saved-scan.ts`·`scan-comparison.ts`, `classify-severity.ts`·`deduplication/`·`suggest-owners.ts`, `security-policy.ts`·`플러그인/skills/define-security-policy/`, `component-scan.ts`·`multiscan.ts`, `auth.ts`·`provider-profile.ts`, `scan-executor.ts`·`hosted-scan.ts`, `cli-integrations.ts`·`cli-mcp.ts` | 15 | 부속 | `capabilities/sdk-features.md` 또는 필요한 항목만 분리 · 미작성 | 코드 확인(명령 등록·export 이름) / 나머지 추론 |
| 17 | 배포 단위: GitHub Action·컨테이너 | Action은 저장소·PR 스캔과 severity 임계값 검사·SARIF 출력, 컨테이너는 CLI의 Debian·Wolfi 이미지와 Compose bulk 스캔 | `action.yml`, `github-action/src/main.ts`, `Dockerfile`, `compose*.yaml`, `docker/` | 15 | 부속 | `capabilities/distribution-units.md` · 미작성 | 코드 확인(`action.yml`의 `runs`, 파일 목록) / 나머지 추론 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 행 수에 넣지 않았다)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1 후보 ledger (후보 JSONL 행에 discovery → validation → attack path 필드를 단계별로 덧붙이는 계약, 각 단계는 전체 행을 교체) | 3, 4, 5, 6, 7 | `MCP/src/artifact-candidate-ledger.ts`, `MCP/src/artifact-contracts.ts`, `플러그인/schemas/tools/`, `플러그인/references/scan-artifacts.md` Phase 2~4 | 행 4 스펙에 포함(제안) · 미작성 | 코드 확인(검증·공격 경로 기록 함수의 검사 규칙) / 스키마 본문은 추론 |
| S2 스캔 산출물 계약 (`scan-manifest.json`·`findings.json`·coverage, 초안→완료→봉인) | 2, 3, 7, 9, 11, 14 | `플러그인/schemas/{scan-manifest,findings,coverage}.schema.json`, `references/scan-contract.md`·`scan-artifacts.md`·`final-report.md`, `scripts/finalize_scan_contract.py` | 행 9 스펙에 포함(제안) · 미작성 | 코드 확인(`validate_contract`) / 스키마 본문은 추론 |
| S3 호출자·실행 환경 계약 (`CODEX_SECURITY_*` 환경 변수, 호출자별 완료 책임, `CODEX_SECURITY_SCAN_PROGRESS` 줄, `.mcp.json`) | 1, 2, 3, 7, 15 | `SDK/api.ts` `scanPrompt`, `플러그인/.mcp.json`, `references/scan-runtime.md`·`final-report.md` | 행 1 스펙에 포함(제안) · 미작성 | 코드 확인(`scanPrompt` 환경 변수·progress 줄, 문서 표) |
| S4 workbench 저장소 (SQLite 스키마, scan·finding·triage·remediation 상태) | 11, 12, 14 | `플러그인/scripts/workbench_schema.py`·`workbench_db.py`, `MCP/src/workbench/database.ts`·`migrations.ts` | 행 12 스펙에 포함(제안) · 미작성 | 추론(파일 이름·크기) |

**대조한 범위와 미탐색 영역**
- 대조: `플러그인/skills/README.md`의 skill 20개를 전부 행에 배정했다(2·3·4·5·6·7·8·11·13·14, `define-security-policy`는 16). MCP 도구는 `MCP/server.ts`의 `registerTool`(32건)과 `compact-artifact-tools.ts`의 `registerCompactTool` 이름을 뽑아 행 1·2·4~7·9·11·12에 배정했다. skill 문서가 부르는 helper 7종(`resolve-security-md`·`make-diff-rank-input`·`validate-patch-risk-assessment`·`make-repo-scope-input`·`copy-deep-review-input`·`bind-repo-scopes`·`validate-tracking-source`)은 `MCP/src/helpers/`와 대조했다. 스캔 파이프라인은 `references/scan-artifacts.md`의 Phase 1~4·Final Report·Fix Finding 절과 맞췄다.
- 문서와 구현의 차이 후보: README는 "로컬 `serve` 명령과 dashboard는 제거했다"고 하는데 `package.json`은 `./server` export(`SDK/server/api.ts`)를 노출하고 `SDK/scan-dashboard.ts`가 남아 있다. 어느 쪽이 살아 있는지는 미확인(행 16).
- 둘 이상으로 구현된 것 후보: workbench·중복 판별이 Python(`플러그인/scripts/workbench_*.py`)과 TypeScript(`MCP/src/workbench/*.ts`, `SDK/deduplication/`)에 있다. `SDK/workbench-arguments.ts`는 첫 줄이 "Generated from plugin workbench-arguments.ts"라 플러그인에서 생성한 복사본이다(코드 확인). 나머지가 같은 방식인지는 미확인.
- 2026-11-16 작성 중 발견(행 4·5·6 작성자 보고, 행 4·5·6 미검증 후보): Deep 비용 한도 소진 마무리(`플러그인/scripts/workbench_db.py` `complete_budget_exhausted_scan`, `workbench_saved_results.py` `budget_exhausted_draft`)가 Python으로 ledger를 따로 읽고 `validation.disposition`·`attack_path.decision`을 coverage `disposition`으로 옮긴다. 행 7 또는 행 9에서 다룰 후보다. SDK custom validation(`SDK/custom-validation.ts`)은 `options.validationPrompt`가 있으면 `record_codex_security_candidate_validations`·`record_candidate_attack_paths` 도구를 끄고 SDK가 별도 턴에서 검증한다(행 16 후보). Deep reducer worker도 같은 `candidate_ledger.jsonl`을 게시한다(`deep_scan_workbench.py`, 행 7)
- 2026-11-16 작성 중 발견(행 3·11 작성자 보고): Python에 diff 변경 목록 규칙이 한 번 더 구현돼 있고(`workbench_target.py:462-585`의 `git_changed_paths`·`diff_scan_file_count`·`candidate_source_lines`) 인벤토리 TS 구현과 결과 동일성은 미확인이다(행 10 후보). diff scan의 target 식별 `snapshotDigest` 계산이 `artifact-scan-draft.ts:3085-3128`과 `workbench_target.py:44-70` 두 곳에 있다(행 9에서 다룰 것). 행 11의 입력은 ledger가 아니라 완료된 scan의 sealed finding(S2)이어서 선행을 행 1 하나로 줄였다. `cs patch --create-pr`(`SDK/cli.ts`, `patch-publication.ts`)는 행 14·16 후보다. 행 3 스펙의 SDK diff prompt(`api.ts:6559`)와 skill의 "SDK가 완료를 소유하면 제외" 문장이 겹쳐 모델이 어느 쪽을 따르는지는 미확인이다
- 행 수: 17행(핵심 14 / 부속 3)이다. 행 13·14·16은 패밀리로 묶었다.
- 미탐색: 모든 skill 본문 중 `security-scan`·`finding-discovery`·`validation`·`attack-path-analysis`·`security-diff-scan`(앞부분)·`deep-security-scan`(앞부분) 외, `compact-artifact-tools.ts` 110~215행과 `artifact-candidate-ledger.ts` 앞 120줄 외의 MCP 본문, `artifact-scan-draft.ts`·`finalize_scan_contract.py`·`workbench_*.py` 본문, `MCP/src/helpers/` 본문, `MCP/src/deep-scan/` 본문, `references/` 중 `core-scan.md` 외, SDK 대부분(`cli.ts` 13,714줄·`api.ts` 7,847줄·`cost.ts` 4,159줄), `native/`(Rust), `evals/`, `sdk/mutation/`, `examples/`, `.github/`, 테스트. 실행(`cs`, SDK, MCP, Docker)은 하지 않았다.
- 열지 않은 것(워크플로 2장 3번 기본 제외): 루트 `AGENTS.md`·`sdk/typescript/AGENTS.md`(그 레포 개발자용 지침이라 따르지 않음), `CONTRIBUTING.md`, `RELEASING.md`, `SECURITY.md`, `CHANGELOG.md`, `.github/` CI 설정.

### 권장 범위 (승인됨: 행 1~11, S1~S3)

목적(사용자 정정): 보안 검증을 하는 skill과 그 skill이 호출하는 코드의 소스를 이해한다. 아래를 기본안으로 제안한다. 부속(15~17)은 기본 제외다.

| 행 | 포함 | 이유 |
|---|---|---|
| 1 | 포함 | 같은 skill이 호출자별로 다르게 끝나므로 2~9를 읽기 전에 알아야 하는 경계다 |
| 2 | 포함 | Standard 감사는 기본 스캔이고 `core-scan.md` 하나로 발견·검증이 끝나는 경로다 |
| 3 | 포함 | phase skill(4~6)이 실제로 쓰이는 파이프라인이다 |
| 4, 5, 6 | 포함 | "찾는다 → 가른다 → 경로·severity를 정한다"의 skill 3개와 호출 도구(`record_*`)·ledger 코드가 한 쌍으로 이어진다. 처음 요청하신 내용에 가장 가깝다 |
| 7 | 포함 | 반복·종료를 코드(`MCP/src/deep-scan/`)가 소유해 skill과 코드의 경계가 가장 크게 보인다 |
| 8 | 포함 | 발견·검증의 입력이다 |
| 9 | 포함 | 모델 출력을 코드가 어디까지 강제하는지(스키마·digest·증거)가 드러난다 |
| 10 | 포함 | skill이 소스를 읽기 전에 부르는 helper라 "skill이 호출하는 코드"에 직접 해당한다 |
| S1, S2, S3 | 포함 | 2~10이 같이 쓰는 계약이라 먼저 쓴다 |
| 11, 12 | 선택 | 11은 발견 다음 단계(수정), 12는 MCP 도구가 내부에서 쓰는 저장소다. 수정이나 저장 쪽으로 넓히고 싶을 때 S4와 함께 추가한다 |
| 13, 14 | 제외 제안 | 13은 코드 연동이 약하고, 14는 가져오기·게시 연동이라 검증 판단과 거리가 있다. 14는 "skill이 CLI를 부르는" 유일한 경로라 호기심이 있으면 추가할 만하다 |
| 15~17 | 제외 | SDK 런처·주변 기능·배포 단위(부속) |

**사용자 결정(2026-11-16)**: 행 1~11 승인(11 포함). 순서: 1·2·4·5·6·8 → 3·11 → 7·9·10(7은 반복·종료·worker 조율, 9는 모델 출력이 거절되는 검사 함수, 10은 skill이 부르는 helper 7종 위주로 좁힘). 12·14와 구조도(2장 5번)는 이번에 하지 않는다.

---

## 3. 핵심 아키텍처 (archify Diagrams)

미작성. 사용자 요청이 feature map까지라 2장 5번(구조도)은 하지 않았다. 범위 승인 후 또는 요청 시 그린다.

---

## 4. 질문 (Questions)

아직 없다.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: feature map 작성 후 2절의 "스펙·상태" 칸
