---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - sdk/typescript/src/api.ts
  - sdk/typescript/src/cli.ts
  - sdk/typescript/src/codex-prompt.ts
  - sdk/typescript/src/deep-scan.ts
  - sdk/typescript/src/runtime.ts
  - sdk/typescript/src/scan-executor.ts
  - sdk/typescript/src/scan-modes.ts
  - sdk/typescript/src/scan-settings.ts
  - sdk/typescript/src/targets.ts
  - sdk/typescript/src/worker-progress.ts
  - plugins/codex-security/.mcp.json
  - plugins/codex-security/.codex-plugin/plugin.json
  - plugins/codex-security/scripts/launch_codex_security_mcp
  - plugins/codex-security/mcp-app/server.ts
  - plugins/codex-security/mcp-app/deep-scan-main.ts
  - plugins/codex-security/mcp-app/src/artifact-context.ts
  - plugins/codex-security/mcp-app/src/workbench-client.ts
  - plugins/codex-security/mcp-app/src/python_command.ts
  - plugins/codex-security/mcp-app/artifact-writer-main.ts
  - plugins/codex-security/mcp-app/src/helpers/inventory-git.ts
  - plugins/codex-security/mcp-app/src/server/handoff-tools.ts
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts
  - plugins/codex-security/mcp-app/src/deep-scan/executor.ts
  - plugins/codex-security/scripts/workbench_cli.py
  - plugins/codex-security/scripts/workbench_db.py
  - plugins/codex-security/scripts/workbench_scan_start.py
  - plugins/codex-security/scripts/workbench_source_scopes.py
  - plugins/codex-security/scripts/workbench_progress.py
  - plugins/codex-security/scripts/workbench/handoff.py
  - plugins/codex-security/scripts/workbench/storage.py
  - plugins/codex-security/scripts/deep_scan_workbench.py
  - plugins/codex-security/scripts/deep_scan_config.py
  - plugins/codex-security/scripts/workbench_target.py
  - plugins/codex-security/scripts/finalize_scan_contract.py
  - plugins/codex-security/references/final-report.md
  - plugins/codex-security/references/scan-prologue.md
  - plugins/codex-security/references/scan-runtime.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/references/access-advisory.md
  - plugins/codex-security/skills/security-scan/SKILL.md
  - plugins/codex-security/skills/security-scan/references/sdk-files.md
  - plugins/codex-security/skills/security-scan/references/scan-results.md
  - plugins/codex-security/skills/security-scan/references/managed-scan.md
  - plugins/codex-security/skills/security-scan/references/desktop-scan.md
  - plugins/codex-security/skills/security-scan/references/scoped-paths.md
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/skills/deep-security-scan/SKILL.md
depends: []
status: draft
---

# 호출자 모드와 스캔 시작

> 같은 보안 skill이 `cs scan`(SDK-owned), Codex 데스크톱 등 workbench가 소유한 시작(workbench-owned), Deep(coordinator) 중 누가 시작했느냐에 따라 누가 scan을 등록하고, 모델이 무슨 prompt와 환경 변수를 받고, 누가 완료·봉인하는지가 어떻게 갈리는지 정의한다. 이 스펙이 공유 계약 S3(호출자·실행 환경 계약)를 소유한다.

<!--
이 레포에서 "구현"의 일부는 skill·reference 문서(모델에게 주는 지침)다. R-ID 앞의 [강제]는 코드가 검사하거나 만든다는 뜻, [지침]은 문서가 모델에게 요구할 뿐 코드가 같은 것을 검사하는 곳을 찾지 못했다는 뜻이다.
검증 수준 `코드 확인`은 그 코드·문장을 직접 읽었다는 뜻이다. [지침] 규칙의 `코드 확인`은 지침 문장을 읽었다는 뜻이고, 모델이 따르는지는 R-45가 `미확인`으로 따로 묶는다.
용어: "SDK-owned"는 SDK가 모델을 부르기 전에 scan을 등록하는 경로(`scans.recipe_json`이 채워진다), "workbench-owned"는 workbench(MCP 서버와 Python)가 scan을 만드는 경로, "Deep"은 coordinator가 반복 감사를 돌리는 경로다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 `cs scan <repository>`로 시작한 Standard 스캔(SDK-owned)이다. 순서는 실제로 이 순서다.

1. SDK가 target을 정규화하고, mode(`standard`/`deep`)가 target과 맞는지 검증하고, skill 이름을 고른다(R-01~R-04).
2. SDK가 workbench에 `register-cli-scan`을 호출해 scan을 등록한다. 이 시점에 scan은 이미 `running`이고, `scanId`·`scanDir`·target 식별자가 workbench에서 돌아온다(R-05~R-07).
3. SDK가 입력 파일(target paths 파일, `false_positive_feedback.json`)을 쓰고, `CODEX_SECURITY_*` 환경 변수를 만들고, prompt를 조립하고, `.mcp.json`을 투영한 plugin 사본으로 Codex 프로세스를 띄운다(R-08~R-16).
4. SDK가 Codex thread를 열어 prompt를 보낸다. `thread.started` 이벤트가 오면 그 thread ID를 scan에 묶는다(R-17).
5. 모델은 `security-scan` skill을 따라 검토한다. `CODEX_SECURITY_SCAN_PROGRESS` 줄을 출력하고(SDK가 이벤트에서 읽는다, R-18~R-19), 초안을 MCP 도구나 `CODEX_SECURITY_SCAN_DIR`의 `scan-manifest.json`·`findings.json`으로 남기고, 시작·완료 도구를 부르지 않은 채 끝난다(R-13, R-41).
6. 턴이 `completed`로 끝나면 SDK가 `prepare-scan-completion`, 파일 검증, 결과 수집을 거쳐 `complete-scan`으로 봉인하고 보고서를 만든다. 중간 어디서든 실패하면 SDK가 등록한 scan을 `fail-scan`/`cancel-scan`으로 닫는다(R-20, R-21).
7. SDK가 임시 입력(target paths 파일, staged plugin 사본 등)을 지운다(R-21).

workbench-owned(R-22~R-32)와 Deep(R-33~R-36)은 2단계가 다르다. scan을 SDK 대신 workbench가 만들고, 모델이 시작 도구로 받은 `scanId`와 소유 증명(claim token 또는 owner thread)으로 이후 도구를 부르고, 완료는 모델(Standard/diff)이나 coordinator(Deep)가 한다.

### 1.2 범위·통합 지점 [필수]
- 제공: 호출자 모드별 scan 등록·소유·완료 경계, 모델이 받는 환경 계약(prompt 구성, `CODEX_SECURITY_*` 환경 변수, `.mcp.json`, `CODEX_SECURITY_SCAN_PROGRESS` 줄), 소유 증명(claim token, owner thread), 시작·context·progress·complete 도구의 입력과 동작.
- 제외:
  - 발견·검증·판정 로직(행 2~6)과 산출물 검증 규칙 및 `complete-scan` 내부 검증(행 9, S2). 이 스펙은 "누가 어떤 파일을 쓰고 누가 봉인하는가"까지만 다룬다.
  - workbench SQLite 스키마(S4)와 Deep coordinator의 반복·종료(행 7). 시작·완료 소유 경계만 다룬다.
  - SDK의 비용·시간 한도, 재개(resume), 다중 대상, knowledge base 준비, Hosted 실행기, 인증·제공자 설정(행 15·16, 사용자가 부속으로 제외). prompt와 환경 변수 조립에 필요한 부분만 다룬다.
  - Codex 데스크톱 앱 코드. 앱은 이 레포에 없고, 앱이 부르는 app-only 도구의 서버 쪽 동작만 다룬다(U-01).
- 외부 의존·선행 계약: 선행 스펙 없음. Codex 프로세스는 SDK가 준 환경을 MCP 서버(`.mcp.json`의 `env_vars`)와 모델 shell에 전달하고, 모델 thread ID를 MCP 요청 metadata에 싣는다고 가정한다(확인 한계). workbench는 Python 스크립트 + SQLite다.
- 소유 상태·부작용: workbench DB의 `scans`·`scan_progress`·`workspaces` 행, scan 디렉터리, target paths 파일(mode `0400`), `false_positive_feedback.json`, Windows의 staged plugin 사본, MCP 서버 프로세스 메모리의 claim token 캐시.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 호출자 모드 요약

| 모드 | 누가 scan을 등록하나 | 모델이 받는 것 | 모델의 MCP 호출을 어떻게 인가하나 | 초안 저장 | 누가 완료·봉인하나 |
|---|---|---|---|---|---|
| SDK-owned (`cs scan`, SDK `run`) | SDK. 모델 호출 전에 `register-cli-scan` | prompt(R-12~R-15), `CODEX_SECURITY_*` 환경 변수(1.3.3), 이미 등록된 `scanId`·`scanDir` | claim token 없음. SDK가 `thread.started`에서 저장한 `continuation_thread_id`와 호출 thread의 일치(R-17, R-29) | Standard는 prompt가 MCP 도구 `record_codex_security_scan_draft`로 checkpoint하라고 지시한다. 도구를 못 쓰면 모델이 `SCAN_DIR`에 `scan-manifest.json`·`findings.json`을 직접 쓴다(R-41) | SDK. `prepare-scan-completion` 후 `complete-scan`(R-20). 모델의 완료 도구 호출을 서버는 막지 않는다(R-32) |
| workbench-owned, app-start (Codex 데스크톱 UI) | 앱이 app-only 도구 `start_codex_security_scan`으로 scan을 만들고 handoff를 claim·전달한다 | 앱이 보내는 continuation 지시(레포 밖, U-01). skill이 전제하는 것은 `scanId`와 `handoffClaimToken` | claim token(UUID 또는 `recovery_` 접두) | 모델이 `record_codex_security_scan_draft` | 모델이 `complete_codex_security_scan`(Standard/diff) |
| workbench-owned, prompt-only | 모델이 `start_codex_security_prompt_only_scan` 호출. 확인된 데스크톱 host의 Standard, 그리고 diff | 도구 결과(scan context) | claim token 없음. owner = 호출 thread(workspace thread) | 모델 | 모델이 `complete_codex_security_scan` |
| workbench-owned, headless Standard | 모델이 `start_codex_security_standard_scan` 호출. 데스크톱이 아닌 host | 도구 결과 + `handoffClaimToken` | claim token + `continuation_thread_id` | 모델 | 모델이 `complete_codex_security_scan` |
| Deep | 모델이 `start_codex_security_deep_scan`(`targetPath`로 새로, 또는 이미 있는 `scanId`로). SDK가 등록한 Deep scan도 같다 | coordinator가 돌려주는 aggregate와 지시문 | claim token(있으면), owner thread | worker는 coordinator가 묶어 준 도구만 쓴다(행 7) | coordinator. 서버 코드가 coordinator 종료 후 `complete-scan`을 부른다. SDK-owned Deep이면 SDK가 한다(R-34) |

#### 1.3.2 MCP 도구

외부 계약이므로 이름·필드는 원문 그대로다. "model"은 모델에게 보이는 도구, "app"은 데스크톱 앱 전용이다.

| 도구 | 노출 | 입력 | 결과·효과 |
|---|---|---|---|
| `start_codex_security_standard_scan` | model | `targetPath`(필수), `scope?`(기본 `"."`), `targetSummary?`(최대 2400자), `userContext?` | `{ startDisposition: "created"\|"joined", scanId, scanDir, handoffClaimToken, scan }`. `scan`에는 token이 없다(R-25) |
| `start_codex_security_prompt_only_scan` | model | `mode`(`"diff"`\|`"standard"`), `targetPath`, `scope`(필수), `targetSummary?`, `userContext?`, `diffTarget?`(`kind`: `working_tree`\|`commit`\|`range`, `baseRevision?`, `headRevision?`, `contentDigest?`) | scan context(`startDisposition` 포함)와 안내문(R-24) |
| `get_codex_security_scan_context` | model | `scanId`, `handoffClaimToken?`, `occurrenceId?`, `requestId?`·`actionToken?`(remediation 전용) | 목표·mode·`userContext`·`scanDir`·progress를 돌려준다. token을 주면 handoff 전달을 기록한다(R-27) |
| `update_codex_security_scan_context` | model | `scanId`, `userContext`(전체 교체, 빈 문자열이면 지움), `handoffClaimToken?` | 실행 중 scan의 `userContext`를 교체한다(R-30) |
| `update_codex_security_scan_progress` | model | `scanId`, `phase?`(`preflight`\|`threat_model`\|`discovery`\|`validation`\|`attack_path`\|`reporting`), `phaseItemsTotal?`, `phaseItemsCompleted?`, `phaseProgressUnit?`(`checks`\|`threat_surfaces`\|`review_receipts`\|`candidate_findings`\|`validated_findings`\|`report_artifacts`), `reviewItemsTotal?`, `reviewItemsCompleted?`, `reportableFindingsCount?`, `deepReviewPass?`, `handoffClaimToken?` | `{ scan }`(갱신된 context, `scan.userContext` 포함)(R-31) |
| `complete_codex_security_scan` | model | `scanId`, `handoffClaimToken?` | 봉인된 scan context. 실패하면 "멈추고 이 오류를 그대로 보고하라"는 문구를 단 오류(R-32) |
| `cancel_codex_security_scan` / `fail_codex_security_scan` | model | `{ scanId }` / `{ scanId, message, handoffClaimToken? }` | 취소는 소유 thread에서만. 실패는 되돌릴 수 없다(R-43) |
| `start_codex_security_deep_scan` | model | `scanId?` 또는 `targetPath?`(둘 중 정확히 하나), `scope?`, `userContext?`, `handoffClaimToken?`, `projectConfigPath?` | coordinator 결과(`scanId`, `scanDir`, `manifestPath`, `terminalReason`, `instructions`, 서버가 완료했으면 `completion`)(R-33, R-34) |
| `open_codex_security_workspace`, `submit_codex_security_setup`, `start_codex_security_scan` | app | workspace 생성·저장, scan 시작 | `start_codex_security_scan`은 `handoff_status: pending` scan을 만든다(R-22) |
| `claim_codex_security_scan_handoff_delivery`, `release_…`, `attach_codex_security_scan_continuation_thread`, `mark_codex_security_scan_handoff_delivered` | app | `scanId`, `claimToken`, (`threadId`, `takeOverStale?`) | handoff 소유 전이(R-23) |

#### 1.3.3 `CODEX_SECURITY_*` 환경 변수

SDK가 `scan` 명령에서 Codex 프로세스에 넣는 값이다(`validate`·`patch`·`policy` 명령은 일부만 넣는다. 줄 범위는 C-04). "읽는 곳"은 이 SHA에서 소비자를 찾은 곳이고, 못 찾은 변수는 그렇게 적는다(R-11).

| 변수 | 값 | 설정 조건 | 읽는 곳 |
|---|---|---|---|
| `CODEX_SECURITY_STARTED_AT` | ISO 시각. resume이고 등록 결과에 문자열 `startedAt`이 있으면 그 값, 아니면 `new Date().toISOString()` | 항상 | `finalize_scan_contract.py`가 completion binding 없이 `scan.startedAt`을 채울 때 |
| `CODEX_SECURITY_REPOSITORY` | 정규화된 저장소 경로 | 항상 | prompt, 입력 준비 helper(`--repo`), Deep parent sandbox |
| `CODEX_SECURITY_SCAN_DIR` | scan 디렉터리(모델이 쓰는 출력의 유일한 위치) | 항상 | prompt, helper의 receipt 기록, Deep worker 설정 경로 해석 |
| `CODEX_SECURITY_PLUGIN_ROOT` | plugin 루트. Windows에서 staged 사본을 만들었으면 그 경로, 아니면 `runtime.plugin.pluginRoot` | 항상 | prompt의 skill·helper 경로, MCP `workbench-client`, 투영된 launcher |
| `CODEX_SECURITY_STATE_DIR` | workbench 상태 디렉터리 | 항상 | Python `state_dir()`, Deep engine 진입점 |
| `CODEX_SECURITY_SURFACE` | `"plugin"`\|`"cli"`\|`"sdk"` (SDK 인스턴스의 surface, 기본 `"sdk"`) | 항상 | 소비자를 찾지 못함 |
| `CODEX_SECURITY_SCAN_ID` | 등록된 `scanId` | 항상 | helper `generate-inventory`가 scoped inventory receipt를 쓸 때, Deep worker writer |
| `CODEX_SECURITY_TARGET_ID` | 등록 결과 `targetId` | 항상 | prompt·skill 문서가 `scan.target.targetId`에 그대로 쓰라고 지시 |
| `CODEX_SECURITY_TARGET_DISPLAY_NAME` | `basename(repo)` | 항상 | 같음 (`scan.target.displayName`) |
| `CODEX_SECURITY_TARGET_KIND` | `git_revision`\|`git_worktree`\|`git_diff`\|`directory_snapshot` 중 하나(R-07) | 항상 | 같음 (`scan.target.kind`) |
| `CODEX_SECURITY_TARGET_REVISION` | 등록된 revision | 등록된 값이 `"unversioned"`가 아닐 때 | 같음 (`scan.target.revision`) |
| `CODEX_SECURITY_TARGET_SNAPSHOT_DIGEST` | `git_diff`면 diff target의 `contentDigest`, 아니면 contract의 `requiredSnapshotDigest` | 값이 문자열일 때 | 같음 (`scan.target.snapshotDigest`, `git_revision`이면 생략) |
| `CODEX_SECURITY_KNOWLEDGE_BASE` | 준비된 knowledge base 경로 | knowledge base가 있을 때 | prompt·`core-scan` 지침 |
| `CODEX_SECURITY_CONFIG_PATH` | `runtime.configPath` | 정의돼 있을 때 | Deep worker 설정 읽기 |
| `CODEX_SECURITY_DEEP_SCAN_CONFIG_PATH` | `runtime.deepScanConfigPath` | mode가 `deep`이고 정의돼 있을 때 | `deep_scan_config.py`, Deep worker 설정 |
| `CODEX_SECURITY_TARGET_PATHS_FILE` | target paths 파일 경로(R-08) | target이 `paths`일 때 | 입력 준비 helper의 `--scopes-file`, `bind-repo-scopes` |

같은 `runtimePaths`에 비 `CODEX_SECURITY_*` 변수도 들어간다. `PYTHON`(plugin Python 해석기), `CODEX_SQLITE_HOME`(workbench `sqlite_home` 설정이 있을 때)이다. Codex 프로세스 환경에는 여기에 `PYTHONUTF8=1`, `CODEX_SECURITY_PYTHON_COMMAND`, `CODEX_CLI_PATH`, `CODEX_SECURITY_GIT`(신뢰 확인된 git 실행 파일), `PATH`(git 확인 결과), `CODEX_HOME`, 제공자 키(해당 시), `CODEX_SAFETY_IDENTIFIER`(해당 시), 그리고 비 Windows에서 `_CODEX_SECURITY_SDK_NODE_SEARCH_PATH`가 더해진다(R-09).

`validate` 명령은 `CODEX_SECURITY_REPOSITORY`·`CODEX_SECURITY_PLUGIN_ROOT`·`CODEX_SECURITY_SURFACE`(+knowledge base가 있으면 `CODEX_SECURITY_KNOWLEDGE_BASE`)를, `patch` 명령은 앞의 세 개를, `policy` 명령은 `CODEX_SECURITY_STATE_DIR`까지 더해 넣는다. `CODEX_SECURITY_SCAN_ID` 등 scan 식별 변수는 `scan` 명령에만 있다.

#### 1.3.4 `.mcp.json`과 MCP 서버 프로세스

- plugin의 `.mcp.json`은 서버 하나(`codex-security`)를 선언한다. `command`는 `./scripts/launch_codex_security_mcp`, `args`는 `["--stdio"]`, `cwd`는 `"."`, `startup_timeout_sec`는 120, `tool_timeout_sec`는 349200이다. `env_vars`는 Codex가 MCP 프로세스에 넘길 환경 변수 이름 목록이다. 목록 전체는 C-08이다.
- 목록에 든 `CODEX_SECURITY_*`는 `GIT`, `PYTHON_COMMAND`, `KNOWLEDGE_BASE`, `CONFIG_PATH`, `DEEP_SCAN_CONFIG_PATH`, `SCAN_DIR`, `PLUGIN_ROOT`, `REPOSITORY`, `SCAN_ROOT`, `STATE_DIR`, `SURFACE` 11개다. `SCAN_ID`, `TARGET_*`, `STARTED_AT`, `TARGET_PATHS_FILE`은 목록에 없다(R-10). 그래서 MCP 도구는 `scanId`를 입력 인자로 받는다.
- `CODEX_SECURITY_SCAN_ROOT`는 SDK가 만들지 않는다. 사용자가 정하면 MCP 서버가 scan 출력 루트로 쓴다(없으면 `<state_dir>/scans`).
- SDK는 이 파일을 그대로 쓰지 않고 투영한다(R-10).

#### 1.3.5 prompt 구성

`scanPrompt`가 만든다. 어떤 줄이 어떤 조건에서 들어가는지는 R-12~R-15가 정하고, 줄의 원문은 C-02·C-03이다. 환경 변수는 값이 아니라 shell 참조로 prompt에 들어간다(R-16).

#### 1.3.6 `CODEX_SECURITY_SCAN_PROGRESS` 줄

모델이 한 줄로 단독 출력하는 `CODEX_SECURITY_SCAN_PROGRESS {"phase":"discovery","filesCompleted":3,"filesTotal":8}`다. 형식과 수락 조건은 R-18, 원문은 C-09·C-10이다.

### 1.4 행동 규칙과 남은 질문 [필수]

#### SDK-owned 시작과 환경

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] `cs scan <repository>`(dry-run 아님) 또는 SDK `CodexSecurity.run(repository, options)` | 둘 다 `run`으로 들어가 `#run`을 실행한다. `options.workflowId`가 있으면 `#runWorkflow`로 간다. `options.mock`이면 모델 없이 mock scan을 만든다(이 스펙 밖) | 코드 확인 |
| R-02 | [강제] skill 이름 선택 | target 종류가 `refs`·`working_tree`면 mode와 상관없이 `security-diff-scan`. 그 외 mode가 `deep`이면 `deep-security-scan`. 그 외는 `security-scan`. SDK의 mode는 `standard`·`deep` 둘뿐이고(기본 `standard`), diff는 mode가 아니라 target 종류로 정해진다 | 코드 확인 |
| R-03 | [강제] mode가 `deep`이고 target이 `refs`·`working_tree` | `InvalidTargetError("Deep mode supports repository and path targets only.")`. scan은 등록되지 않는다. workbench는 `refs`·`working_tree` target의 scan mode를 `diff`로 기록한다 | 코드 확인 |
| R-04 | [강제] 선택한 skill의 `skills/<skill>/SKILL.md`가 plugin 루트(Windows는 staged 사본)에 일반 파일로 없다 | `IncompleteScanError("Installed plugin is missing scan skill: <skill>")`. 이 확인은 scan 등록 전에 한다 | 코드 확인 |
| R-05 | [강제] SDK가 모델 호출 전에 scan을 등록한다 | workbench `register-cli-scan`(recipe JSON을 stdin으로)이 `scanId`, `scanDir`, `targetId`, `contract`, `targetRevision`을 돌려준다. SDK는 `scanId`·`targetId`가 문자열, `scanDir`이 SDK가 정한 값과 같음, `targetKind`가 4종 중 하나, `targetRevision`이 문자열, `git_worktree`·`directory_snapshot`이면 digest가 문자열임을 확인하고, 어긋나면 `CodexSecurityError("The Codex Security workbench returned an invalid scan registration.")`를 던진다. resume이면 `get-cli-scan-resume`을 쓰고, 저장된 recipe의 repository·target이 다르거나 thread ID가 없으면 "mismatched scan resume context" 오류다 | 코드 확인 |
| R-06 | [강제] `register-cli-scan`이 만드는 scan 행 | `recipe_json`이 채워진다(이것이 SDK-owned 표지다). `handoff_status`는 `delivered`, `handoff_claim_token`은 NULL, `user_context`는 `options.scanPrompt`, `scan_dir`은 SDK가 정한 경로다. 이 경로가 저장소와 같거나 저장소 안이거나 저장소를 포함하면 거부되고, `archiveExisting`이 아니면 비어 있어야 한다. `launch_surface`는 등록 입력의 `surface`가 `cli`·`sdk`일 때만 저장된다. 처음 `phase`는 hosted가 아닌 Standard scan이면 `threat_model`, 그 외(diff, Deep)는 `preflight`다 | 코드 확인 |
| R-07 | [강제] target kind와 digest 도출 | workbench가 `allowedKinds`를 정한다: diff mode면 `["git_diff"]`, revision이 `"unversioned"`면 `["directory_snapshot"]`, digest가 없으면 `["git_worktree","git_revision"]`, digest가 clean worktree digest와 같으면 `["git_revision"]`, 아니면 `["git_worktree"]`. SDK는 `allowedKinds`가 정확히 1개일 때만 `targetKind`로 쓰고 아니면 위 R-05의 오류를 낸다. non-diff scan의 digest는 항상 있으므로(unversioned는 디렉터리 digest, 그 외는 worktree digest) 실제로는 1개가 된다. `git_diff`의 snapshot digest는 `diffTarget.contentDigest`다 | 코드 확인 |
| R-08 | [강제] 입력 파일 | (a) scan 디렉터리는 `--output`이 없으면 상태 디렉터리 아래 `scans/<repo 이름>`에서 정하고, 저장소 밖이고 모델이 쓰기 안전해야 한다. (b) `paths` target이면 `codex-security-target-paths-<uuid>.json`을 Codex home의 상위 디렉터리에 `wx`·mode `0400`으로 쓴다. 내용은 요청 경로의 JSON 배열 + 개행이다. (c) workbench에서 받은 false-positive feedback이 비어 있지 않고 새 scan(resume 아님)이면 `<scanDir>/artifacts/01_context/false_positive_feedback.json`을 `wx`·mode `0600`으로 쓴다. feedback 응답의 `scanId`·`targetId`가 이 scan과 다르거나, 목록이 배열이 아니거나, `reason`이 빈 문자열인 항목이 있으면 `CodexSecurityError`를 던진다(이 확인은 resume에서도 한다). 같은 파일을 workbench-owned app-start scan에서는 workbench가 직접 쓴다(R-22) | 코드 확인 |
| R-09 | [강제] 환경 변수 설정 규칙 | 1.3.3 표의 변수를 `runtimePaths`로 만든다. 값이 없는 선택 변수(`TARGET_REVISION`, `TARGET_SNAPSHOT_DIGEST`, `KNOWLEDGE_BASE`, `CONFIG_PATH`, `DEEP_SCAN_CONFIG_PATH`, `TARGET_PATHS_FILE`)는 키를 넣지 않는다. 이 묶음이 Codex 프로세스의 환경(`env`)으로 전달된다(`CODEX_HOME`, git·python 환경과 합쳐진다). Codex가 이 중 무엇을 모델 shell과 MCP 프로세스에 넘기는지는 Codex 동작이라 확인하지 못했다(확인 한계) | 코드 확인 |
| R-10 | [강제] `.mcp.json` 투영 | `.mcp.json`의 `codex-security` 서버 `command`가 정확히 `./scripts/launch_codex_security_mcp` 또는 `…/launch_codex_security_mcp.cmd`일 때만 투영한다(아니면 투영 없음, plugin은 그대로 쓴다). 투영은 `command`를 `./scripts/launch_codex_security_mcp_sdk`(Windows는 `.cmd`)로 바꾸고, `env_vars`에 `CODEX_SECURITY_PLUGIN_ROOT`·`CODEX_SECURITY_REPOSITORY`가 없으면 추가하고, 그 launcher 파일 2개를 plugin 사본에 쓴다. 새 launcher는 `CODEX_SECURITY_PLUGIN_ROOT`가 설정돼 있으면 그 아래 원래 launcher를 `exec`하고 아니면 자기 옆 launcher를 쓴다. 이 SHA의 `.mcp.json`에는 두 이름이 이미 있어 추가는 일어나지 않는다. 투영은 SDK가 만든 marketplace 사본(`<codexHome>/sdk-marketplace/plugins/codex-security`)에만 쓰고 원본 plugin 파일은 바꾸지 않는다 | 코드 확인 |
| R-11 | [강제] MCP·Python이 `CODEX_SECURITY_*`를 읽는 곳과 읽지 않는 곳 | MCP 프로세스는 `SCAN_ROOT`(출력 루트), `PLUGIN_ROOT`, `PYTHON_COMMAND`, `STATE_DIR`(Deep engine 진입점), `GIT`을 읽는다. Python은 `STATE_DIR`, `GIT`, `DEEP_SCAN_CONFIG_PATH`, `STARTED_AT`을 읽는다. `SCAN_ID`는 helper와 Deep worker writer만, `TARGET_ID`·`TARGET_DISPLAY_NAME`·`TARGET_KIND`·`TARGET_REVISION`·`TARGET_SNAPSHOT_DIGEST`는 SDK prompt와 skill 문서만 쓴다. `SURFACE`·`KNOWLEDGE_BASE`는 `.mcp.json` 목록과 SDK 설정 말고는 읽는 코드를 못 찾았다(`KNOWLEDGE_BASE`는 모델 지침이 읽는다) | 코드 확인 (찾지 못함은 2.1의 범위 안) |
| R-12 | [강제] prompt 형태 선택 | `standard` 플래그 = skill이 `security-scan`이고 plugin `.codex-plugin/plugin.json`의 `codexSecurity.standardScanHandoff`가 `1`이다(plugin.json이 없거나 키가 없으면 false). `standard`면 R-13의 단일 prompt, 아니면 R-14의 prompt를 만든다. 이 SHA의 번들 plugin은 `standardScanHandoff: 1`이다 | 코드 확인 |
| R-13 | [강제] `standard` prompt | 순서: 한 줄 임무 → `Repository root: "$CODEX_SECURITY_REPOSITORY"` → target 설명 → (owner 제안, severity rubric, 추가 지시, knowledge base 문단이 있으면 그 순서로) → skill 지시(`discoveryPrompt`가 있으면 그것, 없으면 `"$CODEX_SECURITY_PLUGIN_ROOT/skills/security-scan/SKILL.md"`를 따르라) → "SDK가 이미 이 scan을 등록했다. `<scanId>`와 `$CODEX_SECURITY_SCAN_DIR`를 쓰고, scan-start·completion 도구를 부르지 말고, unsealed 결과를 SDK에 돌려주라" → worker 허용 문장 → `SECURITY.md` 해석 지시 → 첫 threat model에서 `record_codex_security_scan_draft`로 checkpoint하고 `scan-results` 문서를 따르라 → progress 줄 지시. 원문은 C-02 | 코드 확인 |
| R-14 | [강제] `standard`가 아닌 prompt | 공통: `[$codex-security](mcp://codex-security)` 도구 사용 문장, skill 지시, "비대화형", Python 해석기 지정, `Repository root`·`scan 디렉터리`·`scanId`·`scan.target.*`·`scan.producer.name`을 환경 변수 그대로 쓰라는 문장, progress 줄 지시, 환경 변수 참조 규칙, target 설명. 조건 문장 셋: (1) mode가 `deep`이면 "`start_codex_security_deep_scan`을 `{ scanId }`로 부르고 `targetPath`를 넘기지 말라"와 "aggregate가 오면 `scanId`·`manifestPath`로 턴을 끝내라, 확정은 SDK가 한다". (2) skill이 `security-scan`이거나 custom validation이면 "SDK가 이미 등록했다, 시작·완료 도구를 부르지 말라". diff skill에는 이 문장이 들어가지 않는다. (3) 완료 문장: Deep은 위 (1), `security-scan`·비용 한도(`maxCostUsd`)·custom validation이면 "`scan-manifest.json`·`findings.json`을 쓰고 확정·봉인하지 말라", 그 외(diff skill)는 "skill이 지시하는 대로 `record_codex_security_scan_draft`와 `complete_codex_security_scan`을 쓰라" | 코드 확인 |
| R-15 | [강제] prompt 끝에 붙는 문단 | 아래를 이 순서로 붙인다. (1) scope 파일 수 추정이 있으면 "progress에 이 추정을 쓰라"는 문장. (2) `standard` 플래그가 켜져 있고 제공자가 Bedrock이 아니고 인증이 stored credentials이고 ChatGPT 로그인으로 보일 때(`nativeChatGptLogin ?? (파일 store가 아니거나 credential이 api_key가 아님)`) Daybreak 접근 확인 문장. (3) mode가 `standard`이고 hosted가 아닌 Windows scan이면 `resolve-security-md`를 부르는 PowerShell 블록. (4) resume이면 Deep은 coordinator로 이어가라, Standard는 저장된 파일과 checkpoint에서 이어가라는 문장. (5) false-positive feedback을 파일로 썼으면(R-08) 검증 중 읽으라는 문장. (6) mode가 `standard`이고 `maxTimeMinutes`가 있으면 time budget 문장. 문장 원문은 코드다 | 코드 확인 |
| R-16 | [강제] 환경 변수 참조 | prompt는 환경 변수를 값이 아니라 `"$NAME"`(POSIX) 또는 `"$env:NAME"`(Windows) 형태로 참조한다. prompt는 "값을 복사하거나 다시 파싱하지 말라"고 지시한다. Python 해석기는 `$PYTHON`(Windows `& $env:PYTHON`)이다 | 코드 확인 |
| R-17 | [강제] thread 열기 | SDK는 `workingDirectory = scanDir`, `skipGitRepoCheck = true`, 승인 정책, thread source `scan`으로 thread를 연다. 저장된 thread ID가 있으면(resume) `resumeThread`, 없으면 `startThread`다. `runStreamed(prompt)`로 prompt를 보낸다. `thread.started` 이벤트가 오면 SDK가 `set-scan-thread`로 `scans.continuation_thread_id`를 저장한다. resume인데 thread ID가 다르면 "Codex did not resume the original scan session." 오류이고, 저장이 실패하면 warning만 남기고 계속한다 | 코드 확인 |
| R-18 | [강제] `CODEX_SECURITY_SCAN_PROGRESS` 줄 | SDK는 `item.completed` 이벤트의 `agent_message.text`와 `command_execution.aggregated_output`만 읽고, 코드 펜스 밖의 줄 중 `CODEX_SECURITY_SCAN_PROGRESS `로 시작하는 줄의 JSON을 파싱한다. 스키마는 `phase`(6개 중 하나), `filesCompleted`·`filesTotal`(0 이상 정수, `filesCompleted <= filesTotal`)이다. 어긋난 줄은 오류 없이 무시한다. 같은 방식의 `CODEX_SECURITY_WORKER_STATUS` 줄(worker dispatch 수)도 있다 | 코드 확인 |
| R-19 | [강제] SDK가 progress를 받아들이는 규칙 | (a) discovery phase의 첫 `filesCompleted: 0` 줄(또는 inventory 신호가 붙은 줄)은 inventory로 보고 그 `filesTotal`을 총수로 정한다. inventory가 아닌 줄은 총수를 모르거나, `filesTotal`이 정해진 총수보다 크거나, `filesCompleted`가 이미 받은 값보다 작으면 버린다. (b) 모델 이벤트에서 온 값과 Deep은 phase를 그대로 반영하고, 이벤트 출처가 없는 값(workbench 폴링 등)은 phase가 앞으로 갈 때만 반영한다. custom validation 턴이 돌고 있으면 phase는 `validation`으로 보고한다. (c) 직전과 같은 값은 다시 알리지 않는다. (d) 따로 SDK는 workbench에서 persisted progress를 주기적으로 읽는다. scoped(`paths`) Standard이고 plugin이 `scopedInventoryReceipt: 1`이면 `scoped-source-input.receipt.json`이 바뀔 때마다 `update-progress --refresh-scope-file-count`를 부른다. 이 receipt는 helper `make-repo-scope-input`이 `SCAN_ID`·`SCAN_DIR`·`REPOSITORY`·`TARGET_PATHS_FILE`이 모두 있고 인자와 같은 파일일 때만 쓴다(하나라도 다르면 쓰지 않는다) | 코드 확인 |
| R-20 | [강제] SDK 마무리 순서와 실패 | 모델 턴이 끝나면: (1) 턴 상태가 `completed`가 아니면 `IncompleteScanError`(연결 오류면 `CodexConnectionError`), thread ID가 없으면 `IncompleteScanError`. (2) `onFinalize`: 비용 추적을 멈추고(custom validation이 있으면 그 턴을 먼저 돌리고) workbench `prepare-scan-completion`을 부른다. 이것이 실패했는데 scan 상태가 `failed`이고 `failureMessage`가 있으면 그 메시지의 `IncompleteScanError`로 바꾼다. (3) `scan-manifest.json`·`findings.json`이 있어야 하고 JSON으로 읽혀야 하며, helper `parseCanonicalScanDraft`로 초안을 해석했을 때 `complete === false`면 `IncompleteScanError("Codex Security produced only an unfinished audit checkpoint.")`다. (4) 결과 수집: `report.md`도 있어야 하고, 계약(`loadContract`)을 기대값(저장소, revision, target, mode, plugin 버전)으로 검증하고, `manifest.scan.status`가 `completed`가 아니면 `IncompleteScanError`다. (5) workbench `complete-scan --scan-id <id> [--cost-json …]`으로 scan을 `complete`로 바꾼다. (6) 그 뒤에 owner 제안, finding 매칭 같은 후처리가 오고, 후처리 실패는 warning이다 | 코드 확인 (`loadContract`·`prepare-scan-completion` 내부 검증은 행 9) |
| R-21 | [강제] SDK 실패·종료 처리 | scan 등록 후 어디서든 오류가 나면: 이미 `complete`면 usage만 마무리한다. 비용 한도 초과 + 측정 가능하면 `complete-budget-exhausted-scan`으로 닫아 결과를 돌려준다. 연결 오류(`CodexConnectionError`)이고 로컬 Standard이고 저장된 scan이 재개 가능하면 scan을 `running`으로 두고 "Resume when connected: codex-security scans resume <id>" 메시지의 `ScanInterruptedError`를 던진다. 그 외에는 `stopRegisteredScan`: 호출자가 명시적으로 취소했으면(`signal`이 aborted이고 reason이 비용 초과·TimeoutError가 아님) `cancel-scan`, 아니면 오류 메시지로 `fail-scan`. resume한 Deep은 자기 terminal 상태를 스스로 저장하므로 건드리지 않는다. 끝나면 `finally`에서 head drift 감시, 진행 추적, knowledge base 사본, target paths 파일, staged plugin 디렉터리, 저장된 provider profile을 지운다. 정리 실패는 warning이다 | 코드 확인 |

#### workbench-owned 시작·소유·완료

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | [강제] app-only `start_codex_security_scan`(`start-scan`) | workspace가 저장돼(`submitted`, `target_path`) 있어야 한다. 아니면 "Save the Codex Security setup before starting the scan." 이 workspace에 이미 `running`이고 취소되지 않은 scan이 있으면 새로 만들지 않고 그 scan을 돌려준다. 새 scan은 `handoff_status = 'pending'`, `phase = 'preflight'`, `recipe_json = NULL`이고, `scan_dir`은 workbench가 scan 루트(`CODEX_SECURITY_SCAN_ROOT` 또는 `<state_dir>/scans`) 아래에 만든 비공개 임시 디렉터리다. false-positive feedback이 있으면 workbench가 직접 `artifacts/01_context/false_positive_feedback.json`을 쓴다. Deep workspace는 같은 thread에 같은 target·scope의 활성 Deep scan이 있으면 거부한다 | 코드 확인 |
| R-23 | [강제] handoff app-only 도구 4개 | `claim`: `pending` handoff만 대상이고, 첫 claim이 이긴다. 같은 token의 재시도나 경쟁에서 진 호출은 상태를 바꾸지 않고 workspace 상태를 돌려준다. `takeOverStale`이고 기존 claim이 만료됐으면 claim을 교체하면서 continuation·Deep owner thread를 비운다. `release`: `pending`이고 token이 일치하면 claim·continuation·Deep owner를 비운다. `attach`: token이 일치해야 하고, `continuation_thread_id`가 비어 있으면 호출 thread를 저장(Deep이면 Deep owner도), 같은 thread 재호출은 그대로, 다른 thread면 오류. `mark delivered`: `pending`→`delivered`, token이 일치해야 하고, 요청 thread가 owning thread와 같아야 한다(`recovery_` 접두 token은 예외). 처음 delivered가 되는 non-deep scan은 preflight 카운터를 0으로 되돌린다. token은 `recovery_` 접두를 지닐 수 있는 UUID다 | 코드 확인 |
| R-24 | [강제] `start_codex_security_prompt_only_scan` | 호출 thread ID가 없으면 오류. `mode: "diff"`는 `diffTarget`이 필요하고 scope가 전체 target(`.` 또는 targetPath 자신)이어야 한다. `mode: "standard"`는 `diffTarget`을 받지 않는다. 서버는 `start-prompt-only-scan`을 부르고 결과가 `startedScanSchema`(`startDisposition`, `scan.scanId`, 비어 있지 않은 `scan.scanDir`, `scan.handoffStatus === "delivered"`, `workspace.results.scanId === scan.scanId`)를 통과해야 한다. 통과 못 하면 "returned malformed context; no prompt-driven scan was started." 오류를 낸다. 새 scan은 `handoff_status = 'delivered'`, claim token 없음이고, owner는 workspace의 thread다. `phase`는 Standard면 `threat_model`, diff면 `preflight`다 | 코드 확인 |
| R-25 | [강제] `start_codex_security_standard_scan` | 호출 thread ID가 없으면 오류. `start-headless-standard-scan`(mode는 `standard`, `scope` 기본 `"."`)을 부른다. 새 scan이면 workbench가 새 UUID claim token과 `continuation_thread_id = 호출 thread`를 기록하고(기록 못 하면 "ownership could not be recorded"), 서버는 결과가 `scan.mode === "standard"`, `continuationThreadId === 호출 thread`, `progress.status === "running"`, `handoffClaimToken`이 UUID 문자열이고, 새로 만든 scan이면 `phase === "threat_model"`임을 확인한다(`joined`도 token이 있어야 통과한다). 아니면 "returned malformed Standard scan ownership." 서버는 token을 프로세스 메모리 캐시(R-28)에 넣고, 응답의 `scan`에서는 token을 지우고 최상위 `handoffClaimToken`으로만 준다. 새 scan에는 access advisory 안내문이 붙는다 | 코드 확인 |
| R-26 | [강제] 시작 도구의 재사용(`joined`) | 같은 thread가 같은 target·scope·mode·`userContext`·`targetSummary`·diff identity로 다시 시작하면 새 scan 대신 기존 `running`·`delivered` scan을 `startDisposition: "joined"`로 돌려준다. 조건에는 target 파일시스템 identity(revision, digest, device, inode) 일치와 `submitted` workspace가 들어 있고, 어느 쪽이든 `recipe_json`이 NULL(SDK-owned가 아님)이어야 한다. prompt-only는 기존 scan의 claim token이 NULL일 때만, headless Standard는 claim token이 있고 `continuation_thread_id`가 workspace thread와 같을 때만 재사용한다. 그래서 두 시작 도구는 서로의 scan을 재사용하지 않는다(이 판정은 이 SQL 조건에서 읽은 것이다) | 코드 확인 |
| R-27 | [강제] `get_codex_security_scan_context` | (a) remediation 인자(`requestId`·`actionToken`)가 있으면 셋(`occurrenceId`, `requestId`, `actionToken`)이 모두 있어야 하고 그 finding 문맥만 돌려준다. (b) `handoffClaimToken`이 있으면 `mark-handoff-delivered --return-context`를 부른다(R-23). 이때 scan이 `running` Standard, `phase === 'preflight'`, `canceled_at` 없음, 호출 thread 있음, `occurrenceId` 없음이면 `phase`를 `threat_model`로 올리고 `beganStandardReview: true`를 돌려주며 서버가 access advisory 안내문을 붙인다. (c) token이 없으면 `get-scan`을 모델 thread ID와 캐시된 claim(호출 thread가 캐시의 thread와 같을 때만)으로 부른다. (d) 호출이 token을 줬고 scan이 `delivered`이고 token이 일치하고 (`continuation_thread_id`가 호출 thread이거나 token이 `recovery_` 형식)이면 서버가 그 token을 캐시한다. 결과는 `handoffClaimToken`을 지운 채 모델에게 간다 | 코드 확인 |
| R-28 | [강제] claim token 캐시와 claim 요구 | 서버는 `scanId → { claimToken, threadId }` Map을 프로세스 메모리에만 둔다(R-25·R-27이 채운다). 이후 artifact 도구는 `입력의 handoffClaimToken ?? (캐시의 thread가 호출 thread와 같을 때) 캐시 token`을 쓴다. 해당 scan에 claim token이 저장돼 있으면 artifact 도구는 일치하는 token을 요구한다(token이 없으면 "requires its current continuation claim", 저장된 것과 다른 token이면 "is owned by a different continuation"). 저장된 claim token이 없는 scan(SDK-owned, prompt-only)은 token 없이 통한다. 서버를 다시 띄우면 캐시가 사라지므로 모델이 token을 직접 넘겨야 한다. 단 `record_codex_security_scan_draft`와 완료 scan 읽기는 `requireBoundScan`→`requireMatchingScan`(`artifact-scan-draft.ts:3022-3056`, 호출 234·2827행)이 컨텍스트 token이 있을 때 입력의 `handoffClaimToken`이 컨텍스트 token과 같을 것을 따로 요구하므로, 캐시 token이 있어도 모델이 입력에서 token을 생략하면 "scan draft: pass the current authoritative handoffClaimToken."으로 거부된다(코드 읽기, 실행하지 않음. standard-audit 작성자가 지적, 2026-11-16 메인이 해당 줄을 열어 확인) | 코드 확인 |
| R-29 | [강제] owner thread 검사(tokenless) | workbench는 모델 호출(`model_thread_id`가 있음)에 대해, scan에 claim token이 없으면: `handoff_status`가 `pending`이면 거부, owner = `continuation_thread_id`, 없으면 Deep owner thread, 없으면 workspace thread이고, owner가 호출 thread와 다르면 "This scan requires its owning Codex thread.", owner를 알 수 없으면(import 완료 scan 제외) "This scan is awaiting its owning Codex thread."로 거부한다. `model_thread_id`를 주지 않는 호출자(신뢰된 로컬 호출자)는 검사를 건너뛴다. SDK가 workbench를 직접 부를 때는 `model_thread_id`를 주지 않는다. 이 검사는 `complete-scan`, `update-progress`, scan context 조회에서 확인했다 | 코드 확인 (나머지 호출 지점은 열지 않음) |
| R-30 | [강제] `update_codex_security_scan_context` | 호출 thread ID가 없으면 오류. `update-scan-context`를 `userContext` 전체와 함께 부른다. 빈 문자열이면 지운다. 모델에게 가는 결과는 `modelScanContext`를 거친다. app 전용 변형은 scan이 속한 workspace가 있어야 한다. "다음 phase부터 새 값을 쓰고 지금 phase의 worker는 원래 값을 유지한다"는 것은 도구 설명이고 workbench 쪽 구현은 열지 않았다 | 코드 확인(연결) / 추론(다음 phase 의미) |
| R-31 | [강제] `update_codex_security_scan_progress` | `update-progress`를 `modelUpdate: true`와 모델 thread ID로 부른다. workbench는 (순서대로) owner 검사, scan이 `running`이어야 함("Only a running scan can update progress."), Deep이면 coordinator generation 검사, claim 검사를 한 뒤 값을 검사한다: phase는 앞으로만("Scan progress cannot move to an earlier phase."), `phaseItemsCompleted <= phaseItemsTotal`, 총계가 0보다 크면 `phaseProgressUnit` 필요, 같은 phase 안에서 total·completed는 줄지 않고 unit은 바뀌지 않는다. phase가 바뀌면 phase 카운터가 0으로 시작한다. `deepReviewPass`는 Deep만 쓸 수 있다. 결과 `scan`에는 최신 `userContext`가 들어 있다 보충(행 4·5·6 작성자 제안, 메인 미검증): compact 도구는 호출 thread ID를 얻지 못하면 `modelThreadId: ""`를 넘기고(`compact-artifact-tools.ts:362`), 이 빈 문자열이 `--model-thread-id`로 그대로 전달되면 `None`이 아니라서 owner 검사가 적용될 수 있다. 인자 전달 경로는 열지 않아 `미확인` | 코드 확인 |
| R-32 | [강제] `complete_codex_security_scan`(모델이 부를 때) | `complete-scan`을 `claimToken`, 호출 thread, `turnId`(thread source가 `security_scan`인 요청 metadata에서만)와 함께 부른다. workbench는 owner·claim을 검사하고(R-28·R-29), scan이 `running`·`complete`가 아니면 "Only a running scan can be completed."를 낸다. 이미 `complete`면 저장된 결과를 새로 고쳐 돌려준다(재호출은 무해). `recipe_json`이 있는 scan(SDK-owned)이면 `scan-manifest.json`·`findings.json`이 scan 디렉터리에 있어야 하고 없으면 "Scan agent did not create required draft artifacts: …"로 거부한다. 최신 초안이 `complete: false`면 "The latest saved scan draft is incomplete…"로 거부한다. 서버는 어떤 오류든 "Codex Security scan completion failed. … Stop the current response… Do not retry completion…" 문구로 감싼다. 서버와 workbench 어디에도 SDK-owned scan에 대한 모델의 `complete_codex_security_scan` 호출을 거부하는 검사가 없다(그래서 SDK-owned에서 모델이 호출하지 않는 것은 R-13·R-14·R-41의 지침이다) | 코드 확인 ("없다" 주장은 2.1) |

#### Deep

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-33 | [강제] `start_codex_security_deep_scan` 입력 | `scanId`와 `targetPath` 중 정확히 하나. `scanId`가 있으면 `scope`·`userContext`·`projectConfigPath`를 주면 오류(저장된 scan이 기준). `targetPath`는 scope가 전체 target이어야 하고 `handoffClaimToken`과 같이 쓸 수 없다. 호출 thread ID와 parent sandbox를 못 정하면 오류. 통과하면 `deepScanStore.begin`(workbench `begin-deep-scan`)이 scan을 만들거나 받아 오고, coordinator engine을 시작하거나 이미 있으면 합류한다. claim token을 받았으면 캐시에 넣는다 | 코드 확인 (`begin-deep-scan` 내부와 engine은 행 7) |
| R-34 | [강제] Deep의 완료 소유 | coordinator가 종료(`settled`)하면 서버 코드 `completeDeepScan`이 실행된다. 결과 상태가 `succeeded`가 아니면 terminal 오류·취소 결과를 그대로 돌려준다. `succeeded`이고 `sdkOwnsCompletion`(= scan의 `recipe_json`이 NULL이 아님)이면 `complete-scan`을 부르지 않고 "…End this turn with the returned scanId and manifestPath. The SDK owns finalization and report generation after the turn ends." 지시문을 돌려준다. `succeeded`이고 SDK-owned가 아니면 서버가 `complete-scan`을 부르고 결과의 `completion`(progress status, reportAvailable, usage, cost)과 `reportPath`를 돌려주고 "Do not call complete_codex_security_scan again…" 지시문을 붙인다. `terminalReason === "capped"`이고 완료된 감사가 0이면 "deadline expired before any Standard scan completed" 문구가 들어간다 | 코드 확인 |
| R-35 | [강제] SDK가 Deep을 모델 없이 직접 돌리는 조건 | `directDeepScan` = mode가 `deep`, resume 아님, `CODEX_MCP_NODE_PATH`가 설정되지 않음, (제공자가 Bedrock이거나 API 키 인증), 그리고 직접 실행이 가능한 런타임(Bun이 아님, 주입으로 바꿀 수 있음)이다. 맞으면 SDK는 모델 parent turn 없이 native control session을 만들고(prompt는 "host가 coordinator를 직접 돌리고 finalization을 소유한다. 새 scan을 시작하지 말라"는 문장을 덧붙인다) `node <plugin>/mcp/server.mjs --deep-scan-engine`을 띄워 `{ scanId, … }` JSON 한 줄을 stdin으로 준다. 돌아온 `scanId`·`manifestPath`가 이 scan과 다르면 "Deep Scan engine returned results for a different scan." 오류다. 이후 SDK가 `complete-scan`을 부르고 `report.md`를 결과로 읽는다. 맞지 않으면 모델 parent가 `start_codex_security_deep_scan({ scanId })`를 부른다(R-14) | 코드 확인 |
| R-36 | [강제] Deep worker의 환경(경계) | worker는 별도 MCP 서버 `cs_artifacts`(`mcp/server.mjs --artifact-writer --stdio`)를 쓰고, 그 환경은 `CODEX_SECURITY_ARTIFACT_ROOT`, `CODEX_SECURITY_REPO_ROOT`, `CODEX_SECURITY_ARTIFACT_LAYOUT`, `CODEX_SECURITY_SCAN_ID`, `CODEX_SECURITY_PLUGIN_ROOT`, (있으면) `CODEX_SECURITY_DISCOVERY_BOARD_ROOT`·`CODEX_SECURITY_DISCOVERY_WORKER`·`CODEX_SECURITY_SCOPE`·`CODEX_SECURITY_INCLUDE_PATHS_FILE`·`CODEX_SECURITY_PYTHON_COMMAND`다. worker 프로세스는 `CODEX_SECURITY_CONFIG_PATH`·`CODEX_SECURITY_DEEP_SCAN_CONFIG_PATH`(coordinator가 작성)를 읽는다. 이 변수들의 의미와 worker 조율은 행 7이 다룬다 | 코드 확인 |

#### 지침 문서 (모델에게 주는 계약)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-37 | [지침] 호출자별 제출·완료 소유 표 | 지침은 4행이다. Workbench Standard/diff는 `record_codex_security_scan_draft({ scanId, handoffClaimToken?, scope?, threatModel?, findings, reviewState, complete? })`로 내고 부모가 `complete_codex_security_scan`을 부른다. bound Deep Standard worker는 자기 bound semantic draft tool로 내고 Deep coordinator가 마친다. workbench Deep parent는 coordinator의 aggregate를 쓰고 coordinator가 확정하며 `completion`을 sealed manifest와 함께 돌려준다. SDK-owned는 SDK가 준 identity·metadata로 unsealed canonical 파일을 내고(bound draft tool이 주어지면 그것으로), 완료·finalizer를 부르지 않으며 SDK가 마친다. 다른 scan은 권위 있는 managed context가 필요하고 shell로 쓴 canonical 파일로 대신하지 않는다. `complete: false`는 checkpoint이고 `complete: true`(또는 생략)가 제출을 끝낸다. 완료는 있는 artifact를 검증할 뿐 빠진 phase를 하지도, 없는 초안을 만들지도 않는다 | 코드 확인 (지침 문장) |
| R-38 | [지침] `security-scan` skill의 시작 분기 | `CODEX_SECURITY_SCAN_ID`와 `CODEX_SECURITY_SCAN_DIR`가 SDK에서 오면 그 등록 scan을 쓴다(SDK 지시, 없으면 SDK handoff 문서). SDK handoff가 없으면 managed scan 도구를 쓴다: scan ID가 주어지면 `get_codex_security_scan_context`(token이 있으면 같이), scan ID가 없고 "확인된 Codex desktop host"면 `start_codex_security_prompt_only_scan`(`mode: "standard"`), 그 외 host는 `start_codex_security_standard_scan`. 목표·범위·exact user context를 넘기고 `running` Standard scan을 요구하며 target·scope·phase·token을 유지한다. 시간 제한은 사용자가 이 대화에서 요청했고 제공된 것이 없을 때만 한 번 렌더링한다. SDK가 소유한 scan의 완료는 SDK 몫이다 | 코드 확인 (지침 문장) |
| R-39 | [지침] `security-diff-scan`·`deep-security-scan` skill의 시작 분기 | diff skill: 기존 `scanId`는 `get_codex_security_scan_context`로 이어가고, 없으면 `start_codex_security_prompt_only_scan`을 `mode: "diff"`, `scope: "."`, `diffTarget`으로 한 번 부르고, MCP가 없거나 baseline이 지원되지 않으면 blocker를 보고하되 대체 scan이나 shell로 쓴 canonical 파일을 만들지 않는다. 완료는 `complete_codex_security_scan` 한 번 후 `get_codex_security_completed_scan`이고 "SDK가 완료를 소유하는 경우는 제외"한다. Deep skill: 새 target은 `inspect_codex_security_setup` → `start_codex_security_deep_scan({ targetPath, scope: ".", … })`, 기존 scan은 `{ scanId, handoffClaimToken? }`다. 새로 시작된 native scan이면 `get_codex_security_scan_context` 결과의 `otherRunningDeepScans`를 한 번 보고, 다른 Deep scan이 활성이면 사용자에게 Cancel/Continue를 묻고 명시적 선택을 기다린다(닫힌 대화상자는 취소가 아니다). SDK-owned는 scan ID와 manifest 경로를 돌려 SDK가 확정하게 한다 | 코드 확인 (지침 문장) |
| R-40 | [지침] 상위 prologue의 소유·context 규칙 | Deep 최상위 scan은 한 번만 적용하고, 독립 worker는 top-level setup·scan ownership·끝난 phase를 반복하지 않는다. headless host(Codex CLI, 평가 harness, automation)는 데스크톱 workspace를 열거나 기다리지 않는다. native continuation이 `scanId`를 주면 `get_codex_security_scan_context`를 한 번(`handoffClaimToken`이 있으면 함께) 불러 identity·directory·target·scope·mode·exact `userContext`·token을 유지한다. 필요한 context가 없거나 형식이 틀리거나 다른 mode면 identifier를 만들거나 새 scan을 만들거나 target을 넓히지 않고 활성 entrypoint의 기존 오류·라우팅을 따른다. SDK-owned scan은 SDK가 준 identity·directory를 쓰고 다른 scan을 만들거나 확정하지 않는다. 사용자 context는 한 글자도 바꾸지 않고 보존하되 분석 데이터로만 취급하며 workflow 지시를 바꾸거나 읽기·네트워크·테스트·공개를 허가하지 못한다. 실행 중 host-backed scan에서 context 추가·수정·삭제를 요청받으면 즉시 `update_codex_security_scan_context`로 완전한 교체본과 현재 token을 넘기고, 각 정방향 phase 전환에서는 `update_codex_security_scan_progress`가 돌려준 `structuredContent.scan.userContext`를 그 phase와 worker의 불변 context로 쓴다. prompt-only scan은 원래 context를 유지한다 | 코드 확인 (지침 문장) |
| R-41 | [지침] SDK handoff 문서 | draft tool 없이 SDK가 소유한 scan이면 모델이 `CODEX_SECURITY_SCAN_DIR`에 unsealed `scan-manifest.json`·`findings.json`을 쓴다. review bookkeeping은 `scan.reviewState`에 두고 threat model은 findings가 비어 있어도 초기 draft에 저장하고, 이후 checkpoint와 마지막 handoff에서 갱신한다. `scan.target`은 환경 변수 값 그대로(`TARGET_ID`, `TARGET_DISPLAY_NAME`, `TARGET_KIND`, `TARGET_REVISION`, `TARGET_SNAPSHOT_DIGEST`; digest는 `git_revision`이면 생략)이고, producer name은 `codex-security-plugin`, `scan.sealedAt`·`scan.artifacts`는 쓰지 않는다. 각 finding에는 안정적인 `identity.anchor`가 필요하다. 범위 지정(target paths) scan은 `scan.mode`를 `scoped_path`로 쓰고 manifest를 쓴 뒤 `bind-repo-scopes` helper를 부르고(명령은 C-17), 전체 저장소면 `scan.mode`를 `repository`로 쓴다. 두 파일이 있는지 확인한 뒤 제어를 SDK에 돌려준다(SDK가 보고서·threat model을 만들고 봉인한다). `scan-results` 문서도 두 파일을 확인한 뒤 SDK-owned scan이면 바로 돌아가라("return now")고 지시한다 | 코드 확인 (지침 문장) |
| R-42 | [지침] phase 보고 | 관리되는 Standard scan은 실제 정방향 전환에서만 `update_codex_security_scan_progress`를 부른다: `discovery`는 dispatch 전, `validation`은 후보를 확인하기 전, `attack_path`는 도달성 평가 전, `reporting`은 최종 조립 전. 작업이 겹치면 현재 phase를 유지한다. investigator 총수는 새 배정을 dispatch하기 전에 올리고, 끝난 조사는 coverage surface로 기록한 뒤 `review_receipts` 카운트를 올린다. 오래된 handoff가 preflight에 있으면 `threat_model`로 한 번 올린다. SDK-owned scan은 대신 `CODEX_SECURITY_SCAN_PROGRESS` 줄을 낸다: discovery 시작, 의미 있는 검토 batch, 이후 phase 전환마다, 실제 phase·고유하게 완료한 경로 수·범위 총수나 host 추정치로. host-backed diff scan은 architecture mapping 전에 `threat_model`로 올린다 | 코드 확인 (지침 문장) |
| R-43 | [지침 + 강제 일부] 취소·실패 | 지침: `cancel_codex_security_scan`은 사용자의 명시적 취소에만, `fail_codex_security_scan`은 문서화된 복구를 다 한 뒤 확정된 복구 불가 blocker에만 쓰고 active worker·부분 산출물·미완 작업·일시적 preflight 문제·턴 종료에는 쓰지 않는다. 재개 가능한 durable scan은 `running`으로 남긴다. 완료가 막혔다고 scan을 취소·실패시키지 말고 진단을 보존해 보고한다. 강제: `cancel`은 호출 thread ID가 있어야 하고 Deep coordinator를 취소한다. `fail`은 `message`가 필요하고 정상 처리되면 coordinator 실패를 기록한다. 지침이 "하지 말라"는 쓰임을 서버가 막는지는 확인하지 못했다(SDK는 R-21처럼 오류 때 스스로 `fail-scan`을 부른다) | 코드 확인 (지침 문장과 도구 등록) |
| R-44 | [지침] 데스크톱·worker 환경 | 확인된 Codex desktop scan에서만 desktop 결과 문서를 읽고, 완료 전에 handoff가 요구하는 finding별 write-up을 지키고, 완료 뒤 보고서·canonical artifact를 링크한다. 데스크톱은 finding마다 `::code-comment{title="[P<n>] …" body=… file=<절대 경로> start=… end=… priority=<0~3> confidence=<0~1>}` 한 줄을 가장 좁은 root control 위치로 낸다(critical/high/medium/low = P0/P1/P2/P3). 위임 도구를 쓸 수 없거나 worker가 시작되지 않으면 parent가 배정된 검토를 이어 간다(모든 권한 있는 파일과 보안 질문을 다루고 실제 coverage gap을 보고). 영속 Codex 설정을 읽거나 고쳐 worker·goal 도구를 켜지 않는다 | 코드 확인 (지침 문장) |
| R-45 | 모델이 [지침] 규칙(R-13·R-14·R-37~R-44)을 따르는가: 시작·완료 도구를 부르지 않기, progress 줄 형식, token 전달, 취소·실패 사용 | 실행하지 않았다. 서버는 R-22~R-32가 정한 검사만 한다(소유 thread, claim, phase 순서, 필요한 파일의 존재)이고 그 밖의 준수는 모델에 달렸다 | 미확인 |

- 불변식:
  - 모든 모델 MCP 호출은 `scanId`와 소유 증명(claim token이 저장된 scan은 token, 아니면 owner thread 일치)으로 인가되고, 증명이 맞지 않으면 workbench가 거부한다(R-28, R-29). 단 `model_thread_id`를 주지 않는 SDK의 직접 workbench 호출은 인가 검사를 건너뛴다.
  - scan은 `running`일 때만 progress·초안·완료를 받는다. `complete`로 닫힌 scan에 `complete-scan`이 다시 오면 상태를 바꾸지 않고 저장된 결과를 새로 고쳐 돌려준다.
  - SDK-owned scan의 scan 행은 `recipe_json`이 있고 claim token이 없다. workbench-owned scan 행은 `recipe_json`이 없다. Deep 완료 소유자는 이 표지로 정해진다.
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-22, R-23, R-27, R-38 | 데스크톱 앱이 claim·attach·deliver 뒤에 모델 thread에 보내는 continuation 지시의 본문은 무엇인가. 레포에는 앱 코드가 없고 skill 문서는 "native continuation이 `scanId`를 주고 `handoffClaimToken`이 있으면 함께"라고만 한다 | workbench-owned app-start 경로를 처음부터 구현하는 사람이 모델에게 줄 prompt를 정해야 한다. 최소한 `scanId`와 `handoffClaimToken`을 준다는 것만 알고 있다 | Codex 데스크톱 앱 소스, 또는 실제 continuation 지시가 담긴 세션 기록. 이 레포에서는 알 수 없다 |
| U-02 | R-38 | skill이 말하는 "확인된 Codex desktop host"를 모델이 무엇으로 확인하는가(`start_codex_security_prompt_only_scan`과 `start_codex_security_standard_scan` 중 고르는 기준). `scan-prologue`는 headless host(Codex CLI, harness, automation)를 데스크톱이 아닌 쪽으로만 열거한다 | 구현자가 두 시작 도구 중 무엇을 부를지 정하는 기준을 정해야 한다 | 데스크톱이 모델에 주는 system·developer 지침(레포 밖), 또는 `SKILL.md` 17행 문장을 만든 호스트 계약 문서 |

- 확인 한계:
  - 실행하지 않았다(`cs`, SDK, MCP, Python, Codex 프로세스). R-09의 "Codex가 모델 shell과 MCP 프로세스에 환경 변수를 넘긴다", MCP 요청 metadata에 thread ID(`openai/threadId` 등)와 turn metadata(`x-codex-turn-metadata`)가 실린다는 것은 Codex 쪽 동작이고, 코드는 "SDK·서버가 그렇게 가정했다"는 증거다.
  - SDK diff 스캔 prompt에는 R-14 (2)처럼 "이미 등록됐으니 scan-start 도구를 부르지 말라"는 문장이 없다. diff skill은 기존 `scanId`가 없으면 `start_codex_security_prompt_only_scan`을 부르라고 하므로, 모델이 prompt의 `scanId` 줄(manifest에 쓰라는 지시)만 보고 새 scan을 시작하는지는 실행 없이 알 수 없다. 새 scan을 시작하면 SDK가 등록한 scan은 초안이 없어 R-32의 "required draft artifacts" 오류나 R-20의 파일 확인에서 막힐 것으로 추론한다(`추론`).
  - `CODEX_SECURITY_SURFACE`의 소비자는 못 찾았다(R-11). 값 집합은 SDK가 정한다(`plugin`·`cli`·`sdk`).
  - `complete-scan`·`prepare-scan-completion`이 하는 검증의 상세, `loadContract`의 기대값 비교는 행 9·S2 범위라 열지 않았다.
  - `get-scan`의 owner 검사 호출 지점 6곳(`workbench_db.py`·`workbench_saved_results.py`·`deep_scan_workbench.py`) 중 R-29에 쓴 3곳만 함수 문맥까지 열었다.

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `sdk/typescript/src/api.ts:6566-6570` `skillNameFor`, `sdk/typescript/src/targets.ts:759-771` `validateMode` | skill 선택과 deep + diff target 거부 | R-02, R-03 |
| C-02 | `sdk/typescript/src/api.ts:6477-6495` `scanPrompt`의 `standard` 분기 | `standard` prompt의 줄 순서와 문구 | R-13 |
| C-03 | `sdk/typescript/src/api.ts:6496-6563` `scanPrompt`의 비`standard` 분기 | 공통 줄과 조건 문장 셋의 문구 | R-14 |
| C-04 | `sdk/typescript/src/api.ts:3516-3553` `runtimePaths` | `scan` 명령의 `CODEX_SECURITY_*` 값과 설정 조건. `validate`(`api.ts:1386-1390`), `patch`(`api.ts:1586-1590`), `policy`(`api.ts:2040-2047`)의 변수 묶음 | R-09 |
| C-05 | `sdk/typescript/src/runtime.ts:4252-4279` `pluginExecutionEnvironment`·`environmentWithGit` | `PYTHON`, `CODEX_SECURITY_PYTHON_COMMAND`, `CODEX_CLI_PATH`, `CODEX_SECURITY_GIT`, `PATH` 설정 | R-09 |
| C-06 | `sdk/typescript/src/codex-prompt.ts:9-15` `shellEnvironmentReference`·`pluginPythonCommand` | 환경 변수 shell 참조 형식 | R-16 |
| C-07 | `sdk/typescript/src/runtime.ts:3458-3516` `pluginRuntimeProjection` | `.mcp.json` 투영 조건·변경·생성 파일 | R-10 |
| C-08 | `plugins/codex-security/.mcp.json:1-69` | 서버 선언과 `env_vars` 전체 목록 | R-10, R-11 |
| C-09 | `sdk/typescript/src/worker-progress.ts:16-29` | progress 줄 JSON 스키마(phase enum, 정수·부등식 조건) | R-18 |
| C-10 | `sdk/typescript/src/worker-progress.ts:83-138` | 읽는 이벤트 종류, 코드 펜스 제외, 접두 파싱 | R-18 |
| C-11 | `plugins/codex-security/scripts/workbench/handoff.py:22-64` | owner thread 검사와 claim token 일치 검사 | R-28, R-29 |
| C-12 | `plugins/codex-security/scripts/workbench_db.py:908-943` | `joined` 재사용 SQL 조건 | R-26 |
| C-13 | `plugins/codex-security/scripts/workbench_progress.py:218-300` `update_progress` | progress 검사 순서와 오류 문구 | R-31 |
| C-14 | `plugins/codex-security/scripts/workbench_source_scopes.py:28-38` `expected_target_kinds` | `allowedKinds` 결정 규칙 | R-07 |
| C-15 | `plugins/codex-security/mcp-app/server.ts:955-998` `completeDeepScan`, `plugins/codex-security/mcp-app/server.ts:2205-2231` `deepScanTerminalResult` | Deep 완료 소유 분기와 지시문 | R-34 |
| C-16 | `plugins/codex-security/references/final-report.md:7-14` | 호출자별 제출·완료 소유 표(문서 원문) | R-37 |
| C-17 | `plugins/codex-security/skills/security-scan/references/sdk-files.md:5-24` | SDK 파일 handoff 절차(명령 포함) | R-41 |
| C-18 | `plugins/codex-security/mcp-app/src/artifact-context.ts:52-71` | claim 일치·요구 규칙 | R-28 |
| C-19 | `plugins/codex-security/scripts/workbench_scan_start.py:411-418, 428-432, 463-468, 492-500` `insert_running_scan` | handoff 기본값(`pending`), scan 디렉터리 생성, 처음 phase 결정, feedback 파일 쓰기 | R-06, R-22 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01~R-09, R-12, R-13, R-17, R-20 | 변경 없는 git 저장소 `/r`에서 `cs scan /r`(mode `standard`, target `repository`)을 돌리고, 모델이 `scan-manifest.json`·`findings.json`을 `SCAN_DIR`에 쓰고 시작·완료 도구 없이 턴을 `completed`로 끝낸다 | scan이 모델 호출 전에 `running`으로 등록되고, 환경에 `CODEX_SECURITY_SCAN_ID`·`SCAN_DIR`이 있고 `TARGET_KIND`는 `git_revision`(작업트리에 변경이 있으면 `git_worktree`)이며 `TARGET_PATHS_FILE`은 없다. prompt는 `standard` 분기이고 "Do not call scan-start or completion tools"를 포함한다. 마무리 뒤 scan 상태는 `complete`이고 `report.md`가 있다 |
| T-02 | R-02, R-03 | (target, mode) = (`refs`, `standard`), (`repository`, `deep`), (`paths`, `standard`), (`working_tree`, `deep`) | skill은 각각 `security-diff-scan`, `deep-security-scan`, `security-scan`이고, 마지막 입력은 "Deep mode supports repository and path targets only."로 거부되며 scan이 등록되지 않는다 |
| T-03 | R-08, R-09 | target이 `paths`(`["src","lib/a.ts"]`), knowledge base 없음 | `codex-security-target-paths-<uuid>.json`이 mode `0400`, 내용 `["src","lib/a.ts"]\n`으로 생기고 환경에 `CODEX_SECURITY_TARGET_PATHS_FILE`이 있다. `CODEX_SECURITY_KNOWLEDGE_BASE`는 없다. 스캔이 성공하든 실패하든 `finally`에서 `removeTargetPathsFile`이 호출된다(삭제 본문은 열지 않음) |
| T-04 | R-05, R-07 | workbench 등록 응답의 `contract.target.allowedKinds`가 `["git_worktree","git_revision"]`(원소 2개)로 온다(모의 응답) | SDK가 `CodexSecurityError("The Codex Security workbench returned an invalid scan registration.")`를 던지고 모델은 시작되지 않는다. 실제 workbench는 non-diff에 digest를 항상 만들어 이 응답을 내지 않는다 |
| T-05 | R-10 | `.mcp.json`의 `command`가 `./scripts/launch_codex_security_mcp`인 plugin, 그리고 `command`가 다른 문자열인 plugin | 첫 번째는 marketplace 사본에서 `command`가 `./scripts/launch_codex_security_mcp_sdk`로 바뀌고 launcher 2개가 추가되며 원본 plugin 파일은 그대로다. 두 번째는 투영이 없다 |
| T-06 | R-18 | 모델 출력에 (a) `CODEX_SECURITY_SCAN_PROGRESS {"phase":"discovery","filesCompleted":3,"filesTotal":8}` 한 줄, (b) 같은 줄을 ```` ``` ```` 코드 펜스 안에, (c) `{"phase":"discovery","filesCompleted":9,"filesTotal":8}` | (a)만 progress로 읽히고, (b)는 펜스 안이라 무시되고, (c)는 `filesCompleted > filesTotal`이라 오류 없이 무시된다 |
| T-07 | R-20 | 모델이 `record_codex_security_scan_draft`를 `complete: false`로만 부르고 턴을 `completed`로 끝낸다 | `prepare-scan-completion` 뒤 파일 해석에서 `IncompleteScanError("Codex Security produced only an unfinished audit checkpoint.")`가 나고, SDK가 scan을 `fail-scan`으로 닫는다(호출자 취소가 아니므로) |
| T-08 | R-32 | SDK 등록 scan에 `scan-manifest.json`·`findings.json`이 없는 상태에서 모델이 `complete_codex_security_scan({ scanId })`를 부른다 | 호출 thread가 `continuation_thread_id`와 같다면 owner 검사는 통과하고 "Scan agent did not create required draft artifacts: scan-manifest.json, findings.json. …"로 거부되며, 서버가 "Stop the current response… Do not retry completion…"를 덧붙인 오류를 낸다 |
| T-09 | R-29 | SDK 등록 scan(`continuation_thread_id` = A)에 thread B가 `update_codex_security_scan_progress`를 부른다 | "This scan requires its owning Codex thread."로 거부된다 |
| T-10 | R-31 | scan 현재 `phase`가 `validation`인데 `phase: "discovery"`로 progress를 올린다 | "Scan progress cannot move to an earlier phase."로 거부된다. `phaseItemsTotal: 5`, `phaseItemsCompleted: 6`이면 "Completed phase items cannot exceed total phase items."다 |
| T-11 | R-25, R-26 | 같은 thread가 `start_codex_security_standard_scan({ targetPath: "/r" })`를 두 번 부른다(그 사이 target이 바뀌지 않음) | 첫 응답은 `startDisposition: "created"`, `phase`가 `threat_model`이고 `handoffClaimToken`이 UUID다. 두 번째는 `"joined"`로 같은 `scanId`를 돌려준다. 응답의 `scan` 안에는 token이 없다 |
| T-12 | R-27 | headless로 시작한 `running` Standard scan이 `preflight` phase인데 `get_codex_security_scan_context({ scanId, handoffClaimToken })`가 owning thread에서 온다 | `phase`가 `threat_model`로 올라가고 결과가 `beganStandardReview`를 포함해 access advisory 안내문이 붙는다. 같은 호출을 다시 하면 phase는 그대로다 |
| T-13 | R-24 | `start_codex_security_prompt_only_scan({ mode: "diff", targetPath, scope: "." })`(`diffTarget` 없음) | "Review changes prompt-only scans require diffTarget."로 거부되고 scan은 만들어지지 않는다. `mode: "standard"`에 `diffTarget`을 주면 "Standard prompt-only scans must omit diffTarget."이다 |
| T-14 | R-34 | SDK가 등록한 Deep scan(`recipe_json` 있음)을 coordinator가 `succeeded`로 마친다 | 서버는 `complete-scan`을 부르지 않고 "The SDK owns finalization…" 지시문과 `scanId`·`manifestPath`를 돌려준다. SDK-owned가 아닌 Deep이면 서버가 `complete-scan`을 부르고 `completion`과 `reportPath`를 돌려준다 |
| T-15 | R-33 | `start_codex_security_deep_scan({ scanId, scope: "." })` | scan이 저장돼 있으니 `scope`를 빼라는 오류로 거부된다. `{ targetPath, handoffClaimToken }`도 거부된다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다. "없다" 주장의 검색 명령은 이 표 아래 "부재 주장의 검색 범위"에 모았다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `sdk/typescript/src/cli.ts:12245-12248`(`security.run(repository, options)`), `sdk/typescript/src/api.ts:849-876` `run`, `sdk/typescript/src/api.ts:2224-2231` `#run` | `cs scan` 명령 등록부는 열지 않고 호출 지점만 봤다 |
| R-02 | C-01, `sdk/typescript/src/api.ts:2599`, `sdk/typescript/src/scan-modes.ts:1-2`, `sdk/typescript/src/scan-settings.ts:12` | `DEFAULT_SCAN_MODE`는 `"standard"` |
| R-03 | C-01, `sdk/typescript/src/api.ts:5786-5791`(`normalizeTarget`·`validateMode`), `plugins/codex-security/scripts/workbench_db.py:1632-1645` | `validateMode`는 `#prepareLocalInputs`에서 호출(등록 전). `#prepareLocalInputs` 나머지는 열지 않았다 |
| R-04 | `sdk/typescript/src/api.ts:2631-2636` | |
| R-05 | `sdk/typescript/src/api.ts:2905-2933`, `2974-3029`(resume), `3030-3072`(검증) | 등록 응답 구성은 R-06·R-07의 Python |
| R-06 | `plugins/codex-security/scripts/workbench_db.py:1577-1801` `register_cli_scan`(특히 1595-1599, 1645, 1739-1768, 1786-1801), C-19 | 처음 phase 조건은 `workbench_scan_start.py:463-468`. 디렉터리 규칙은 `plugins/codex-security/scripts/workbench_db.py:1560-1576` `require_cli_scan_directory`(저장소와 같거나 포함·피포함 관계면 거부, `archiveExisting`이 아니면 비어 있어야 함) |
| R-07 | C-14, `sdk/typescript/src/api.ts:3030-3072`, `plugins/codex-security/scripts/workbench_scan_start.py:63-90`, `plugins/codex-security/scripts/workbench_db.py:360-390` `scan_contract` | "non-diff digest는 항상 있다"는 `scan_target_identity`의 코드 구조에서 읽음 |
| R-08 | `sdk/typescript/src/api.ts:2445-2475`(scan 디렉터리), `3262-3279`(target paths 파일), `3424-3447`·`3493-3514`(feedback), `4385-4404`(정리) | `removeTargetPathsFile` 본문은 열지 않았다. 삭제한다는 것은 `finally`의 호출 이름에서 읽음 |
| R-09 | C-04, C-05, `sdk/typescript/src/api.ts:4806-4812`, `4932-4952`, `5000-5043` | `PYTHON`·`CODEX_SQLITE_HOME`은 `runtimePaths` 안에 있다. `selectedScanEnvironment`·`definedEnvironment` 같은 필터 함수 본문은 열지 않았다(제공자 키 처리는 행 15·16) |
| R-10 | C-07, C-08, `sdk/typescript/src/runtime.ts:3368-3393`(`createMarketplace`), `3575-3600`(`bootstrapPlugin`이 투영을 읽음), `plugins/codex-security/scripts/launch_codex_security_mcp:5-9` | 투영된 launcher 내용은 `runtime.ts:3492-3511`. 설치된 사본과의 비교(`pluginContentsMatch`)는 열지 않았다 |
| R-11 | 아래 "부재 주장의 검색 범위" 1번, 소비자: `plugins/codex-security/mcp-app/src/workbench-client.ts:13`·`20-21`, `plugins/codex-security/mcp-app/deep-scan-main.ts:58`, `plugins/codex-security/mcp-app/src/python_command.ts:33`, `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:244-247`, `plugins/codex-security/mcp-app/src/deep-scan/executor.ts:969-1011`·`1106-1127`, `plugins/codex-security/scripts/workbench/storage.py:16-31`, `plugins/codex-security/scripts/finalize_scan_contract.py:1570-1588`, `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:516-520`, `plugins/codex-security/scripts/workbench_target.py:251`, `plugins/codex-security/scripts/deep_scan_config.py:45`, `plugins/codex-security/mcp-app/artifact-writer-main.ts:29-30` | 아래 검색의 한계 참고. `STARTED_AT`은 `completion_binding`이 없을 때만 쓰이는데 그 호출 경로(누가 binding 없이 부르는가)는 열지 않았다 |
| R-12 | `sdk/typescript/src/api.ts:2613-2617`, `7625-7636`, `plugins/codex-security/.codex-plugin/plugin.json:21-27` | |
| R-13 | C-02 | 문구 원문은 C-02. 표는 순서만 적었다 |
| R-14 | C-03(특히 `sdk/typescript/src/api.ts:6508-6516`, `6517-6526`, `6538-6546`, `6550-6560`) | 아래 "부재 주장" 3번(diff prompt에 등록 문장이 없다) |
| R-15 | `sdk/typescript/src/api.ts:3449-3452`, `3453-3468`, `3469-3486`, `3487-3492`, `3493-3514`, `3663-3676` | `readScanTimeBudgetPolicy`·`renderScanTimeBudgetPolicy` 본문은 열지 않았다 |
| R-16 | C-06, `sdk/typescript/src/api.ts:6548` | |
| R-17 | `sdk/typescript/src/api.ts:3562-3580`, `3645`, `3693`, `3726-3757`, `plugins/codex-security/scripts/workbench_db.py:1804-1814` `set_scan_thread` | thread ID 저장이 `continuation_thread_id`라는 것이 R-29 owner 검사의 전제다(`handoff.py:35`) |
| R-18 | C-09, C-10, `sdk/typescript/src/worker-progress.ts:140-153` | `scan-activity.ts:326`이 같은 접두 줄을 활동 기록에서 거른다는 것은 보았으나 이 스펙 밖 |
| R-19 | `sdk/typescript/src/api.ts:2660-2665`, `2673-2727`, `3326-3394`, `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:236-265` | `ScanProgressTracker`·`ScanCostTracker` 본문은 열지 않았다(행 15) |
| R-20 | `sdk/typescript/src/api.ts:3697-3921`, `6105-6293` `runScanEvents`, `6799-6850` `collectResult`, `plugins/codex-security/scripts/workbench_db.py:1287-1351`, `1385-1440` | `requireScanArtifacts`·`loadContract`·`parseCanonicalScanDraft` 본문은 열지 않았다(행 9). `prepare_only`가 파일을 쓴다는 것은 `complete_scan_locked`에서 `_write_prepared_scan_finalization`(1415)이 `prepare_only` 분기(1439)보다 앞에 있는 구조에서 읽음 |
| R-21 | `sdk/typescript/src/api.ts:4138-4161`, `4183-4261`, `4262-4357`, `4385-4404`, `7052-7093` `stopRegisteredScan`, `sdk/typescript/src/scan-executor.ts:125-134` `explicitlyCanceled` | `complete-budget-exhausted-scan`의 조건은 `workbench_db.py:1147-1199`를 훑었다(상세는 행 15). 후처리(owner 제안·finding 매칭) 실패가 warning이라는 것은 `api.ts:4067-4137` |
| R-22 | `plugins/codex-security/mcp-app/server.ts:870-889`, `plugins/codex-security/scripts/workbench_db.py:719-840` `start_scan`, C-19 | 앱이 `submit_codex_security_setup` 후 이 도구를 부르는 순서는 도구 설명과 스키마(`server.ts:826-889`)에서 읽음. 앱 자체는 레포에 없다 |
| R-23 | `plugins/codex-security/mcp-app/src/server/handoff-tools.ts:22-101`, `plugins/codex-security/scripts/workbench/handoff.py:81-290`, `plugins/codex-security/scripts/workbench_cli.py:380-390` | 앱이 이 도구들을 어떤 순서로 부르는지는 레포 밖(U-01). 서버 쪽 전이 규칙만 읽었다 |
| R-24 | `plugins/codex-security/mcp-app/server.ts:162-182`, `637-679`, `1897-1919`, `2048-2080`, `plugins/codex-security/scripts/workbench_db.py:843-1023` | 처음 phase는 C-19 |
| R-25 | `plugins/codex-security/mcp-app/server.ts:183-197`, `570-635`, `1921-1944`, `plugins/codex-security/scripts/workbench_db.py:999-1012`, `plugins/codex-security/scripts/workbench_cli.py:102-117` | token 형식은 `handoffClaimTokenSchema`(UUID 또는 `recovery_` + UUID, `handoff-tools.ts:22-30`). 새로 만든 token은 `uuid.uuid4()` |
| R-26 | C-12, `plugins/codex-security/scripts/workbench_db.py:944-950` | 같은 thread에서 두 scan이 동시에 `running`일 수 있는지(다른 target)는 확인하지 않았다 |
| R-27 | `plugins/codex-security/mcp-app/server.ts:1348-1419`, `plugins/codex-security/scripts/workbench/handoff.py:204-290`, `plugins/codex-security/scripts/workbench_db.py:2753-2770` | token 없이 부르는 `get-scan` 경로의 나머지(2770행 이후)는 열지 않았다 |
| R-28 | `plugins/codex-security/mcp-app/server.ts:524-530`, `1379`, `1408-1412`, `1847-1852`, C-18, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:353-368` | |
| R-29 | C-11, `plugins/codex-security/scripts/workbench_db.py:1299`·`2690`·`2757`, `plugins/codex-security/scripts/workbench_progress.py:236`, `sdk/typescript/src/api.ts:3904-3911`(SDK가 `complete-scan`에 모델 thread를 주지 않음) | `model_thread_id` 생략 시 건너뛴다는 것은 `handoff.py:28`과 docstring(27행). SDK가 모든 workbench 호출에서 생략하는지는 `complete-scan`·`get-scan`·`register-cli-scan` 호출 지점만 확인했다 |
| R-30 | `plugins/codex-security/mcp-app/server.ts:1437-1513` | `update-scan-context` Python 구현은 열지 않았다 |
| R-31 | C-13, `plugins/codex-security/mcp-app/server.ts:1515-1564` | `deep_preflight` 분기(239-246)는 Deep 전용이라 생략했다 |
| R-32 | `plugins/codex-security/mcp-app/server.ts:1566-1595`, `2419-2426`, `plugins/codex-security/scripts/workbench_db.py:1287-1311`, `1334-1351`, `1377-1384`, `1494-1507` | 아래 "부재 주장" 2번 |
| R-33 | `plugins/codex-security/mcp-app/server.ts:891-1139` | `WorkbenchDeepScanStore.begin`·`startDeepScanEngine` 본문은 열지 않았다(행 7) |
| R-34 | C-15, `plugins/codex-security/scripts/deep_scan_workbench.py:339-343` | `sdkOwnsCompletion`이 `recipe_json is not None`이라는 것은 이 한 줄에서 읽음 |
| R-35 | `sdk/typescript/src/api.ts:2602-2612`, `3678-3693`, `3922-3932`, `sdk/typescript/src/deep-scan.ts:372-442` | `runEngine`(444-513)과 `deepScanLaunch`는 훑지 않았다. direct engine의 coordinator 동작은 행 7 |
| R-36 | `plugins/codex-security/mcp-app/src/deep-scan/executor.ts:594-627`, `969-1011` | worker 프로세스 환경 조립(215-264)은 일부만 읽었다 |
| R-37 | C-16 | 문서 문장. 줄 14·16도 읽음 |
| R-38 | `plugins/codex-security/skills/security-scan/SKILL.md:14-21`, `plugins/codex-security/references/artifact-storage.md:3-9` | `artifact-storage.md`는 "Standard는 `start_codex_security_standard_scan`"이라고 일반화해 적고 `SKILL.md`가 데스크톱만 prompt-only로 가른다. 충돌이 아니라 구체화로 읽었다(추론) |
| R-39 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:12-20`, `32-33`, `plugins/codex-security/skills/deep-security-scan/SKILL.md:10-14` | |
| R-40 | `plugins/codex-security/references/scan-prologue.md:3-17`, `29-37` | |
| R-41 | C-17, `plugins/codex-security/skills/security-scan/references/scan-results.md:3-13`, `plugins/codex-security/references/scan-artifacts.md:7-14` | `scoped-paths.md`(1-23)의 inventory 명령은 행 10 |
| R-42 | `plugins/codex-security/skills/security-scan/references/managed-scan.md:1-11`, `plugins/codex-security/skills/security-scan/references/scan-results.md:3`, `plugins/codex-security/references/scan-runtime.md:7` | |
| R-43 | `plugins/codex-security/references/scan-prologue.md:35-37`, `plugins/codex-security/references/final-report.md:57-61`, `plugins/codex-security/mcp-app/server.ts:1199-1220`, `1624-1651` | `cancelSecurityScan`(1141-1198) 본문은 앞부분만 읽었다 |
| R-44 | `plugins/codex-security/skills/security-scan/references/desktop-scan.md:1-5`, `plugins/codex-security/references/final-report.md:81-87`, `plugins/codex-security/references/scan-runtime.md:1-9` | |
| R-45 | 실행하지 않음 | |
| T-01~T-15 | 해당 R-ID의 근거 | 모두 코드 읽기로 기대값을 도출했다. 실행·원본 테스트 열람 없음 |

**부재 주장의 검색 범위**
1. R-11 (환경 변수 소비자). 기준 SHA에서 `git grep -n -E "CODEX_SECURITY_(SURFACE|KNOWLEDGE_BASE|SCAN_ID|TARGET_ID|TARGET_KIND|TARGET_REVISION|TARGET_DISPLAY_NAME|TARGET_SNAPSHOT_DIGEST|STARTED_AT)" -- plugins sdk github-action docker ':!*.md' ':!*test*' ':!*/tests/*'`. `SURFACE`는 `.mcp.json`과 SDK의 설정 코드만, `KNOWLEDGE_BASE`는 `.mcp.json`과 SDK의 설정·prompt 코드만 나온다. `SCAN_ID`는 `artifact-writer-main.ts:29`, `generate-inventory.ts:245`, Deep worker 환경(`executor.ts:607`), `sdk/typescript/src/scan-comparison.ts:1290`(인증 환경 선택, 이 스펙과 무관)에서 나온다. 놓칠 수 있는 것: 이름을 문자열 상수나 배열에서 조합해 읽는 코드(`environmentValue(env, name)`의 `name`이 변수인 호출), 빌드된 `mcp/*.mjs`(레포에 추적되지 않는 생성물), 테스트가 만든 fixture(`sdk/typescript/scripts/fixtures/`는 Codex를 흉내 낸 테스트 코드라 소비자로 세지 않았다). Python 쪽은 `git grep -n "CODEX_SECURITY_" plugins/codex-security/scripts`(`*.py`)로 `GIT`·`STATE_DIR`·`DEEP_SCAN_CONFIG_PATH`·`STARTED_AT`만 나왔다.
2. R-32 (모델의 완료 호출을 막는 검사가 없다). `git grep -n "recipe_json" plugins/codex-security/scripts/workbench_db.py`로 17곳을 확인했고 `complete_scan_locked`(1287-1576) 안은 1334행뿐이다(초안 파일 존재 확인). `plugins/codex-security/mcp-app/server.ts:1566-1595`의 도구 본문에도 SDK 소유 확인이 없다. 놓칠 수 있는 것: `workbench_saved_results.py`·`workbench/*.py`가 `complete-scan`을 가로채는 다른 진입점(`partial(...)`로 등록된 핸들러 중), 그리고 Codex 쪽이 SDK 소유 scan의 MCP 호출을 막는 설정(이 레포에서 SDK가 그런 설정을 주지 않는 것은 확인하지 못했다).
3. R-14 (diff skill의 SDK prompt에 등록 문장이 없다). `sdk/typescript/src/api.ts:6508-6516`의 삼항식은 `mode === "deep"`, `skillName === "security-scan" || customValidation`, 그 외 `[]` 세 갈래이고, 그 외 갈래에 diff skill이 들어간다. 놓칠 수 있는 것: 이 prompt를 만든 뒤 호출자가 덧붙이는 문장(`options.scanPrompt`, 시간 제한, Windows 블록 등은 R-15에 적었고 diff 전용 추가 문장은 찾지 못했다).

### 2.2 코드 읽는 순서 [선택]
SDK 경로부터 읽는다. `sdk/typescript/src/api.ts`의 `run`(849) → `#run`(2224)에서 `skillNameFor`(2599) → 등록(2905) → `runtimePaths`(3516) → `scanPrompt`(3404, 6435) → thread(3562-3693) → `runScanEvents`(3697, 6105) → `complete-scan`(3904)을 따라간다. 환경이 모델과 MCP로 가는 길은 `#createSessionCodex`(4771)와 `runtime.ts`의 `pluginRuntimeProjection`(3458)이다. 등록과 소유 규칙은 `plugins/codex-security/scripts/workbench_db.py`의 `register_cli_scan`(1577)·`_start_prompt_driven_scan`(843)·`start_scan`(719)·`complete_scan_locked`(1287)와 `scripts/workbench/handoff.py`다. MCP 쪽은 `mcp-app/server.ts`의 도구 등록(570, 637, 891, 1348, 1515, 1566)을 보고, 지침은 `references/final-report.md`(7-12행 표) → `scan-prologue.md` → `skills/security-scan/SKILL.md`(14-21행) → `references/{sdk-files,scan-results,managed-scan,desktop-scan}.md` 순이다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용한 파일:줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본 4개를 인용 줄에서 열어 주장과 대조했다. 이 스펙은 행 2·3·4·7·9가 `depends`로 의존하므로 워크플로 4장 5번에 따라 독립 검토(검토자 서브에이전트)가 남아 있고, 그 전까지 `draft`로 둔다.
- 대조한 R-ID: R-03(`targets.ts:768`의 오류 메시지, `validateMode`가 등록 전 호출), R-11(`CODEX_SECURITY_SURFACE`는 비테스트 코드에서 `api.ts`가 설정하는 4곳뿐이고 읽는 곳 없음), R-29(`workbench/handoff.py`의 `model_thread_id is None`이면 검사 생략), R-32(`workbench_db.py`의 "Only a running scan can be completed."와 "Scan agent did not create required draft artifacts" 위치). 모두 일치.
- 대조하지 않은 R-ID: 위 4개를 제외한 전부. 특히 R-05~R-07, R-20~R-27, R-30, R-31, R-34는 고위험 후보로 독립 검토에서 볼 대상이다.
- 재구현: 미수행
