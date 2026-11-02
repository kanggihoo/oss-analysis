---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/bin/archify.mjs
  - archify/bin/finalize.mjs
  - archify/bin/visual-check.mjs
  - archify/bin/delivery-update.mjs
  - archify/references/delivery-contract.md
depends: [delivery.md, verification-gates.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# finalize 오케스트레이션 (`archify finalize`)

> 타입·초안 경로·출력 경로를 받아 `deliver` → `check` → `browser-check`를 차례로 실행하고(explainer는 prepare를 먼저 하고 browser-check를 기본 생략), 각 단계 영수증이 같은 산출물 바이트를 가리키는지 묶어 확인한 뒤, 첫 실패에서 멈추고 전체 영수증(`<stem>.finalize.json`)과 요약 영수증(`<stem>.finalize-summary.json`)을 남기는 CLI 명령.

<!--
원본에서 확인한 범위: bin/finalize.mjs 전체, bin/archify.mjs의 commandFinalize와 인자 추출 함수, delivery-contract.md의 finalize 절, visual-check.mjs의 browserCheckSidecarPaths 호출부, delivery-update.mjs의 반환 모양.
읽지 않은 것: 영수증 파일을 원자적으로 쓰는 atomic-output.mjs 내부(captureAtomicOutput·publishRegularFileBinding), 각 gate 안의 로직(delivery.md·verification-gates.md 소관), 테스트.
스크립트·출력: ../../../artifacts/archify/spec-demos/finalize/ (이하 DEMO)
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. `archify finalize <type> <input> <output.html> [옵션]`. 인자를 해석하고 `<type>`을 확인한다(R-01~R-03). explainer이면 이 프로세스에서 초안을 한 번 prepare해 임시 폴더에 번들로 동결한다(R-24).
2. `runFinalize` 진입: `--candidate-sha256`이 있으면 초안의 지금 해시와 대조한다(R-20). 출력 경로를 풀고 출력 폴더를 만들고, 영수증·요약 파일 경로를 정해 겹침을 검사하고, 두 파일 자리를 선점해 `status:"running"` 영수증을 먼저 쓴다(R-07~R-09). 업데이트 확인을 병렬로 시작한다(R-25).
3. **deliver**: 자식 프로세스 `archify deliver <type> <입력 절대경로> <출력 절대경로> --quality <q> [--repo-root …] --json`. 통과하면 이 결과로 `validate` 단계를 "deliver에 내장"으로 채운다(R-11, R-15). deliver가 `showcase`에서 경고를 하나라도 보고하면 종료 코드 0이어도 실패다(R-16).
4. **check**: 자식 프로세스 `archify check <출력> --require-provenance`. deliver가 만든 provenance(영수증 ID·산출물 해시)와 같은 산출물인지 묶어 확인한다(R-13, R-14).
5. **browser-check**(native는 기본, explainer는 `--browser-check`일 때만): 같은 프로세스 안에서 Chrome을 띄워 `executeBrowserEvidence`를 호출한다(자식 프로세스가 아님, R-12).
6. 단계마다 통과하면 두 영수증 파일을 다시 쓴다(R-09). 처음 비통과(fail/skipped) 단계에서 반복을 멈추고 종료 코드와 진단을 정한다(R-17, R-18).
7. 모두 통과하면 최종 인계 검사: provenance가 아직 현재이고 산출물 바이트가 deliver 때와 같은지, 초안이 시작 때와 같은지 다시 본다(R-19). 업데이트 확인 결과를 기다려 `update`에 넣고 영수증·요약을 마지막으로 쓴다. stdout에 요약(JSON 한 줄 또는 텍스트 4줄)을 내고 종료 코드를 정한다(R-04, R-05).

### 1.2 범위·통합 지점 [필수]
- 제공: 인자 해석, 단계 실행 순서와 호출 인자·환경, 단계 간 바인딩 확인, 첫 실패 중단과 종료 코드, finalize 영수증·요약 영수증의 이름·경로·필드·축소 규칙(이 스펙이 소유하는 공유 계약, 1.3), 후보 해시 고정과 변조 감지, explainer 분기(품질 기본값·prepare 선행·browser-check 생략).
- 제외:
  - deliver 안의 로직(렌더 호출, 출력 경로 해석 우선순위·검증, provenance 쓰기·교체·잠금·journal·실패 표지)은 [delivery.md](delivery.md). 여기서는 호출 인자·환경·영수증 매핑만 쓴다.
  - check·browser-check 안의 로직(정적 검사 9종, provenance 대조 순서와 `delivery/*` 코드, Chrome 측정, 뷰포트, browser-check 영수증 필드, `viewer/evidence-path-conflict` 소유권)은 [verification-gates.md](verification-gates.md). 여기서는 호출과 "통과로 인정하는 영수증 조건"만 쓴다.
  - 입력 로드·스키마 검증·진단 객체 공통 모양은 [input-validation.md](input-validation.md), 렌더러는 [rendering.md](rendering.md)이다(둘 다 `depends`에는 넣지 않은 설명용 링크). 이 스펙은 deliver 자식이 내놓은 진단을 그대로 소비한다.
  - explainer 문법·번들·렌더·`check`·`patch`는 [explainer.md](explainer.md). 여기서는 finalize가 부르는 지점(prepare 선행, 환경변수, 품질 기본값, browser-check 생략)만 쓴다.
  - 실패 후 수리 지침(LLM이 진단을 읽고 고치는 절차)은 행 9(repair-loop). 여기서는 영수증이 싣는 `nextAction`·`supportedFixes` 필드까지만 쓴다.
  - 업데이트 확인의 내용·`--open`은 필드 이름만 쓴다.
- 외부 의존·선행 계약:
  - 자식 프로세스 계약: `node <archify.mjs> <deliver|check> …`가 stdout에 JSON 영수증 하나를 쓴다(deliver 영수증은 delivery.md 1.3, check 영수증은 verification-gates.md 1.3). stdout이 비었거나 JSON이 아니면 "영수증 없음"으로 취급한다(R-13).
  - 브라우저 게이트 함수 `executeBrowserEvidence({command:'browser-check', capture:false, requireProvenance:true, artifactPath, outDir, chromePath, resolveChrome, browserFactory})` → `{exitCode, receipt}`. 종료 코드 0/1/2의 의미는 verification-gates.md R-33.
  - Node.js 18+, 출력·영수증 폴더가 로컬 파일시스템.
- 소유 상태·부작용:
  - 출력 HTML 옆에(또는 `--out-dir`/`--receipt`가 정한 곳에) `<stem>.finalize.json`·`<stem>.finalize-summary.json`. 이 둘은 실행 **시작 직후부터** 존재하고(`running`), 매 통과 단계마다 갱신된다.
  - deliver·check·browser-check의 부작용(HTML, `<stem>.delivery.json`, journal, `<stem>.browser-check.json`)은 각 스펙 소유다. finalize가 실패해도 이미 deliver가 교체한 HTML은 되돌리지 않는다(R-22).
  - explainer: 임시 폴더 `archify-explainer-finalize-*`(번들 `explainer.prepared.json`)를 만들고 종료 때 지운다.
  - Chrome 프로세스 1개(browser-check 단계에서만, 종료 때 닫힘).

### 1.3 인터페이스와 데이터 의미 [필수]

**명령행**: `archify finalize <type> <input> <output.html> [--json] [--browser-check] [--receipt <path.json>] [--out-dir <dir>] [--quality standard|showcase] [--repo-root <path>] [--candidate-sha256 <hex>] [--writing warn|strict|off]` (`--writing`은 usage 한 줄에는 없지만 explainer에서 동작).

| 인자 | 기본값 | 의미·잘못된 입력 |
|---|---|---|
| `<type>` | 필수 | 10개 native 타입 + `explainer`. 아니면 종료 2, `cli/unknown-diagram-type`(입력을 읽지 않음) |
| `<input>` | 필수 | 상대 경로는 cwd 기준. 이후 단계에는 절대 경로로 전달 |
| `<output.html>` | 필수(위치 인자 정확히 3개) | deliver의 CLI 출력 인자 규칙(delivery.md R-05)이 그대로 적용된다. finalize에서는 `meta.output`이 아니라 이 인자가 항상 위치를 정한다. 위치 인자가 3개가 아니면 `cli/usage`, 종료 2 |
| `--json` | 꺼짐 | stdout에 요약 JSON 한 줄(R-04). 인자 오류도 `--json`이면 JSON으로 낸다 |
| `--browser-check` | 꺼짐 | explainer에서만 의미가 있다. native는 항상 browser-check를 한다(켜도 같음) |
| `--quality standard\|showcase` | **`showcase`** | `--quality=값` 허용. 값 누락 `cli/missing-option-value`, 잘못된 값 `cli/invalid-option-value`. 모든 단계에 `--quality`로 전달된다. 초안의 `meta.quality_profile`은 finalize 인자가 있든 없든 이 값에 밀린다 |
| `--repo-root <path>` | 없음 | 절대 경로로 바꿔 deliver에 `--repo-root`로 전달. 값 누락 `cli/missing-option-value` |
| `--out-dir <dir>` | 출력 HTML 폴더 | browser-check 영수증과 기본 finalize 영수증·요약을 둘 폴더(없으면 만듦). HTML과 provenance는 요청한 출력 경로에 그대로 둔다. 값 누락은 `fail`로 stderr에 `--out-dir requires a directory path.`와 종료 2(`--json`이어도 JSON이 아님) |
| `--receipt <path.json>` | `<stem>.finalize.json`(위) | 전체 영수증 경로 지정. 요약은 `<파일명에서 .json 제거>-summary.json`(같은 폴더). `.json`이 아니면 `output/cli-extension`. 값 누락 `cli/missing-option-value` |
| `--candidate-sha256 <hex>` | 없음 | 64자리 소문자 hex가 아니면 `cli/invalid-option-value`(종료 2). 초안 바이트의 SHA-256과 다르면 시작 전 실패(R-20) |
| `--writing warn\|strict\|off` | explainer에서 deliver의 기본(`warn`) | explainer가 아닌 타입에 쓰면 `cli/unsupported-option`, 두 번 쓰거나 값이 틀리면 `cli/invalid-arguments` |
| 그 밖의 `--x` | | `cli/unknown-option`(`Unknown finalize option "--x".`), 종료 2 |

**영수증 파일 경로 규칙**

| 파일 | 경로 |
|---|---|
| 전체 영수증 | `--receipt` 값, 없으면 `<browser-check 영수증 폴더>/<stem>.finalize.json`. `<browser-check 영수증 폴더>`는 `--out-dir` 또는 HTML 폴더, `<stem>`은 browser-check 영수증 stem(HTML 파일명에서 `.html` 제거, 길이·대소문자 처리는 deliver와 공유하는 `boundedSidecarStem`, delivery.md C-01). `<stem>.finalize.json`·`.finalize-summary.json` 접미사를 붙여 255바이트를 넘으면 stem을 해시로 줄인다 |
| 요약 영수증 | 기본 이름이면 `<stem>.finalize-summary.json`, `--receipt`가 `x.finalize.json`이면 `x.finalize-summary.json`, 그 밖의 이름 `y.json`이면 `y-summary.json` |
| 겹침 금지 | 두 파일은 입력 초안, 출력 HTML, deliver의 사이드 파일(`<stem>.delivery.json`, `-pending`, 잠금 2종), browser-check 영수증 경로와 같은 항목이면 안 된다(별칭 포함). 요약은 전체 영수증과도 달라야 한다. 위반하면 `finalize/runtime`(R-06) |

**stdout**

| 상황 | `--json` | 없음(텍스트) |
|---|---|---|
| 단계까지 간 실행(통과·실패·skipped) | 요약 영수증(아래)을 `JSON.stringify` **한 줄**로 | 4줄: `finalize <status>: <산출물 절대경로>` / `gates validate:<s> deliver:<s> check:<s> browser-check:<s>` / `receipt <전체 영수증 경로>` / `perceptual visual review <visualReview>`. 진단 중 `severity:"warning"`은 stderr에 `warning [<code>] <message>`. `update.noticeRequired`가 true면 `update.noticeText` 한 줄 더. **실패 진단 내용은 텍스트 모드에 나오지 않는다**(요약 파일에서 읽는다) |
| 시작 전 실패(R-06) | 실패 객체 JSON 한 줄(아래) | stderr에 `finalize could not start` 뒤 줄마다 `[code] message`(`formatDiagnostics`). 종료 1 |
| 인자 오류 | pretty JSON `{schemaVersion:1, ok:false, command:"finalize", stage:"arguments", error, diagnostics[]}`(종료 2). `usage` 오류는 `error`에 사용법 전체 | stderr에 메시지만(종료 2) |

**시작 전 실패 객체** (stdout JSON, 영수증 파일은 없음): `schemaVersion:1, ok:false, command:"finalize", status:"fail", type, quality, specification:{path}, artifact:{path}, gates:{네 단계 모두 "not-run"}, browserCheck:{requested, ran:false}, diagnostics[], visualReview:"not-requested"`. 해시·`diagnosticSummary`·`durationMs`·`evidence`는 없다. `diagnostics`는 던져진 오류의 진단 배열, 없으면 `[{code: error.finalizeCode || "finalize/runtime", severity:"error", message, [evidence]}]`.

**전체 영수증 `<stem>.finalize.json`** (UTF-8, 2칸 들여쓰기, 끝 개행 1개. 필드는 아래 순서이며 `failedStage`는 실패 시 `evidence`·`visualReview` 근처에 붙고 `finishedAt`, `durationMs`, `update`는 맨 끝)

| 필드 | 타입·값 | 의미 |
|---|---|---|
| `schemaVersion` | `1` | |
| `ok` | bool | 모든 단계 통과 + 최종 인계 검사 통과일 때만 true |
| `command` | `"finalize"` | |
| `status` | `"running"` \| `"pass"` \| `"fail"` \| `"skipped"` | `running`은 진행 중에 쓴 사본에만(프로세스가 죽으면 그대로 남음). `skipped`는 어느 단계가 skipped(종료 코드 2 또는 영수증 `status:"skipped"`)일 때 |
| `type`, `quality` | string | `quality`는 `standard`\|`showcase`(인자 또는 기본 `showcase`) |
| `startedAt`, `finishedAt` | ISO 8601 UTC | `finishedAt`은 마지막 쓰기에만 있음 |
| `specification` | `{path, sha256, bytes}` 또는 `{path}` | 실행 시작 시 읽은 초안 바이트. 읽을 수 없으면 `path`만 |
| `artifact` | `{path, sha256, bytes}` 또는 `{path}` | 진행 중에는 `{path}`. deliver 통과 후 deliver 영수증의 `artifact`를 덧붙임. 최종: 성공이면 deliver 영수증의 것, 실패이면 **그 시점 디스크의 출력 HTML**의 현재 해시(없거나 못 읽으면 `{path}`만) |
| `stages` | map | 아래 "단계 항목". 키는 `validate`, `deliver`, `check`, `browser-check` 중 기록된 것 |
| `browserCheck` | `{requested:bool, ran:bool}` | `requested`=browser-check 단계가 계획에 있는지(native 또는 `--browser-check`). `ran`=browser-check 영수증에 `containment.viewports`가 있는지(Chrome이 실제 측정까지 감) |
| `diagnostics` | list | 진행 중·성공: deliver가 보고한 `severity:"warning"` 진단만(예: 로케일 대체). 실패: 실패 단계의 진단(R-18) |
| `failedStage` | `"validate"`\|`"deliver"`\|`"check"`\|`"browser-check"`\|`"finalize"` | 실패·skipped일 때만. deliver 자식이 입력·렌더·검사 단계에서 실패해 `validate` 단계가 fail이면 `validate` |
| `evidence` | `{receipt, summaryReceipt, [browserCheckReceipt]}` | 전체·요약 영수증 절대 경로. `browserCheckReceipt`는 browser-check 단계에 도달한 뒤에만 |
| `visualReview` | `"not-requested"` | 이 명령은 다른 값을 쓰지 않는다 |
| `durationMs` | int | 전체 소요 |
| `update` | 객체 | 업데이트 확인 결과(R-25). 항상 있다(최종 쓰기에서) |

*단계 항목* (`stages[<이름>]`)

| 모양 | 의미 |
|---|---|
| `{status, exitCode, durationMs, command[], [execution:"in-process"], [receipt], [stdout], [stderr], [signal]}` | 실제로 실행한 `deliver`·`check`·`browser-check`. `command`는 `[node 경로, archify.mjs 경로, ...인자]`(browser-check는 자식이 아니라도 같은 모양으로 기록). `receipt`는 stdout JSON, JSON이 아니면 `stdout`에 최대 원문 그대로. `stderr`는 trim한 자식 stderr |
| `validate` 통과 | `{status:"pass", exitCode:0, durationMs:null, execution:"embedded-in-deliver", command(=deliver의 것), receipt:{schemaVersion:1, ok:true, command:"validate", specification, validation}}`. deliver 영수증에서 가져온 것이고 별도 프로세스는 없다 |
| 자리표시자 | `{status:"not-run", execution:"embedded-in-deliver"}`(deliver 실패인데 입력 단계 문제는 아님), `{status:"not-run", execution:"blocked-by-validate"}`(deliver 슬롯, validate가 실패한 경우), `{status:"not-run", execution:"not-requested"}`(explainer의 browser-check 기본) |

단계 `status` 값 집합: `pass`, `fail`, `skipped`, `not-run`. 요약의 `gates`는 이 `status`를 네 키(`validate`, `deliver`, `check`, `browser-check`)에 복사하고 기록이 없으면 `not-run`이다.

**요약 영수증 `<stem>.finalize-summary.json`과 stdout JSON** = `compactFinalizeReceipt(전체 영수증)` (필드 순서대로. 요약 파일은 pretty, stdout은 한 줄)

| 필드 | 값 | 비고 |
|---|---|---|
| `schemaVersion`, `ok`, `command`, `status`, `type`, `quality`, `specification`, `artifact` | 전체 영수증의 값 그대로 | |
| `gates` | `{validate, deliver, check, browser-check}` 각 `pass`\|`fail`\|`skipped`\|`not-run` | |
| `failedStage` | 전체와 같음 | 있을 때만 |
| `diagnostics` | 최대 8개의 진단 `{code, severity("error" 기본), message, [subject], [evidence(비어 있지 않을 때)], [supportedFixes(비어 있지 않을 때, 복사)]}` | 선택 규칙 R-27 |
| `diagnosticSummary` | `{total, shown, truncated, [omittedByCode: {code: 개수}]}` | `omittedByCode`는 `truncated`일 때만, 0인 코드는 뺌 |
| `evidence` | 전체와 같음 | |
| `update` | 전체의 `update` | `update.status`가 `unavailable`이면 **생략** |
| `visualReview` | `"not-requested"` | |
| `durationMs` | | |
| `browserCheck` | 전체와 같음 | 있을 때만 |
| `visualReviewRecommendation` | `{action:"inspect-route-readability", signals, reason, [affectedRoutes], [hints], [repair]}` | 통과했고 check 영수증 `composition.metrics`의 `resolvedCrossovers`·`routesOverSuggestedBends`·`routesOverSuggestedStretch` 중 하나 이상이 0보다 클 때만(R-28) |
| `layoutReviewRecommendation` | `{action:"inspect-leading-space"\|"inspect-sequence-width", evidence, reason, repair}` | 통과했을 때만(R-28) |
| `nextAction` | `{action:"edit-in-place", candidate, constraint, then:"finalize-once"}` | `status:"fail"`이고 `failedStage:"validate"`일 때만(R-29) |

### 1.4 행동 규칙과 남은 질문 [필수]

**인자·출력·종료 코드**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 인자 해석 순서: `--quality` → `--repo-root` → `--out-dir` → `--receipt` → `--candidate-sha256` → `--writing`을 차례로 뽑고, 남은 인자 중 `--`로 시작하고 `--json`·`--browser-check`가 아닌 것은 `cli/unknown-option`. 위치 인자(남은 것에서 `--json`·`--browser-check` 제외)가 정확히 3개가 아니면 `cli/usage` | 종료 2. 어떤 파일도 만들지 않는다. `--json`이 있으면 stdout JSON `stage:"arguments"`, 없으면 stderr 메시지. 위치 인자 4개·0개·`--bogus`·`--quality gold`·`--candidate-sha256 ABC`·explainer 아닌 타입의 `--writing`, 모두 종료 2. `--out-dir` 값 누락만 예외로 항상 stderr 텍스트(종료 2) | 실행 확인(T-12) |
| R-02 | `<type>` 검증(`rendererPath`)은 위 인자 추출이 끝난 뒤, `runFinalize`를 부르기 전에 한다 | 알 수 없는 타입이면 종료 2, `cli/unknown-diagram-type`. 입력 파일은 읽지 않는다 | 실행 확인(T-12d) |
| R-03 | `--quality`가 없을 때 | `quality = "showcase"`(finalize 고유 기본값. deliver·validate는 렌더러 기본을 쓴다). 단계 자식에는 항상 `--quality <값>`이 붙는다. explainer도 같다(초안의 `quality_profile`보다 우선, explainer.md R-17) | 실행 확인(T-01의 `command` 배열) |
| R-04 | stdout 형식 | 1.3 표대로. `--json`: 요약을 한 줄로. 텍스트: 4줄(+stderr 경고, +update 안내). 텍스트 모드는 실패 진단을 출력하지 않는다 | 실행 확인(T-01, T-02, T-05) |
| R-05 | 종료 코드 | 통과 0. 인자 오류 2. 첫 비통과 단계가 `skipped`(자식 종료 코드 2이거나 영수증 `status:"skipped"`)이면 2(예: Chrome 없음, T-10). 그 밖의 실패는 그 단계의 종료 코드, 0이면 1(예: deliver가 종료 0으로 끝났지만 showcase 경고로 실패 → 1). 최종 인계 검사 실패 1. 시작 전 실패 1(출력 확장자 오류, 후보 불일치, explainer prepare 실패, 영수증 경로 충돌 포함 — 이들은 `cli/*` 인자 오류와 달리 종료 **1**) | 실행 확인(0·1·2 모두) |
| R-06 | `runFinalize`가 영수증 파일을 쓰기 전에 던지는 오류, 또는 prepare 실패 | `commandFinalize`가 잡아 "시작 전 실패 객체"(1.3)를 낸다. 영수증·요약 파일은 만들지 않는다. 해당 오류: 출력 경로·`--receipt` 경로 검증(`output/cli-extension` 등), `finalize/candidate-changed`(R-20), 영수증이 입력·출력·사이드 파일과 겹침(`finalize/runtime`, 메시지 `The finalize receipt must be distinct from …`), explainer prepare 진단, 영수증 자리 선점 실패(`finalize/receipt-publication`). 출력 폴더는 이미 만들어졌을 수 있다(R-07) | 실행 확인(T-05, T-08b, T-09c, T-12g, T-12k). `receipt-publication`은 코드 확인 |

**준비·경로·영수증 파일**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | `runFinalize` 시작 순서 | ① 입력·출력 경로를 절대화하고 출력 경로를 CLI 규칙으로 검증(`output/cli-extension` 등), `--out-dir` 검증 ② 초안 바이트를 읽어 `specification` 신원(`path, sha256, bytes`, 못 읽으면 `path`만) ③ `--candidate-sha256` 대조(R-20) ④ `--receipt` 경로 원문 검증(`.json` 필수) ⑤ **출력 폴더 `mkdir -p`** ⑥ 영수증·요약 경로 결정과 겹침 검사(R-06) ⑦ 두 파일 자리를 먼저 모두 선점(`regular-or-absent`: 없거나 일반 파일이어야 함. 하나라도 실패하면 어느 쪽도 쓰지 않음) ⑧ `running` 영수증·요약을 쓴다 ⑨ 업데이트 확인 시작(R-25) ⑩ 단계 반복. ①~④에서 실패하면 출력 폴더도 영수증도 없고, ⑤ 이후(⑥⑦)에서 실패하면 출력 폴더만 남을 수 있다 | 실행 확인(T-08b·T-12g·T-12k에서 폴더·파일 없음, T-05에서 폴더만 존재), 코드 확인(순서) |
| R-08 | 영수증·요약 위치 | 1.3 "경로 규칙" 표대로. `--out-dir`을 주면 `<dir>/<stem>.finalize.json`·`<stem>.finalize-summary.json`·`<stem>.browser-check.json`이 그 폴더에 생기고 HTML·`<stem>.delivery.json`은 출력 경로 옆에 남는다. `--receipt r/my.json`이면 `r/my.json`·`r/my-summary.json`이고 browser-check 영수증은 HTML 옆(또는 `--out-dir`). 영수증 폴더가 없으면 만든다 | 실행 확인(T-03, T-04) |
| R-09 | 쓰는 시점과 방식 | 전체·요약 두 파일을 **같은 시점에 함께** 쓴다: 시작 직후(`running`) → 통과한 단계마다 → 마지막(성공·실패 모두. 최종 쓰기에 `finishedAt`·`durationMs`·`update`가 붙음). 실패한 단계는 반복을 `break`한 뒤 마지막 쓰기에 반영된다(그 전의 중간 쓰기는 없음). 각 쓰기는 임시 파일을 거쳐 게시하며, 쓰기 직전 두 자리가 선점 때와 같은 일반 파일인지 다시 확인한다. 달라졌으면 `finalize/receipt-publication` 오류로 실행이 중단된다(시작 전 실패 객체, 종료 1) | 코드 확인. 최종 상태는 실행 확인(T-01), 중간 `running` 사본은 관찰하지 않음 |

**단계 실행**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | 단계 목록 | `needsBrowser = type !== 'explainer' \|\| --browser-check`. 반복하는 단계는 `needsBrowser`이면 `deliver → check → browser-check`, 아니면 `deliver → check`. `validate`는 반복에 없고 deliver 통과 때 내장 항목으로 채워진다(R-15). explainer에서 browser-check를 생략하면 시작부터 `stages["browser-check"] = {status:"not-run", execution:"not-requested"}`, `browserCheck:{requested:false, ran:false}`이고 최종 요약 `gates["browser-check"]="not-run"`. 생략해도 `ok:true`가 될 수 있다 | 실행 확인(T-09a: explainer 4단계 `pass/pass/pass/not-run`, T-09b: `--browser-check` 시 `pass`·`ran:true`) |
| R-11 | 단계 자식 프로세스 호출 | `execFile(node, [archify.mjs 절대경로, ...인자], {cwd: finalize의 cwd, env, encoding:utf8, maxBuffer})`. 인자: **deliver** `deliver <type> <입력 절대> <출력 절대> --quality <q> [--repo-root <절대>] [--writing <m>(explainer만)] --json`; **check** `check <출력 절대> --require-provenance`(`--json` 없음, check는 항상 JSON 출력). 환경: `env`(기본 `process.env`; explainer는 거기에 `ARCHIFY_EXPLAINER_PREPARED=<번들 파일>` 추가) 그대로 두 자식에 전달하되 **deliver 자식에만** `ARCHIFY_UPDATE_CHECK_DISABLED=1`을 덧붙인다(업데이트 확인을 finalize가 한 번만 하기 위해). `maxBuffer = max(ARCHIFY_CHECK_MAX_BUFFER 또는 64MiB, 4MiB) + 64KiB`; 초과·실행 실패는 종료 코드 정수면 그 값, 아니면 1로 취급 | 코드 확인 + 실행 확인(`stages.*.command` 배열: T-01, T-09a). 환경변수는 코드 확인(실행 시 관찰하지 않음) |
| R-12 | browser-check 단계 | 자식 프로세스가 아니라 **같은 프로세스에서** `executeBrowserEvidence`를 호출한다(`execution:"in-process"`, `command` 배열은 기록용으로 `browser-check <출력> --json --require-provenance [--out-dir <절대>]`). 이 단계에 들어갈 때 비로소 Chrome을 찾아(`findChrome({env})`, `ARCHIFY_CHROME` 포함) 브라우저를 띄우므로 deliver·check가 실패하면 Chrome은 뜨지 않는다. Chrome을 찾는 중 예외가 나면 `viewer/browser-check-runtime`(`browser-check could not discover Chrome.`) 실패 영수증을 `<stem>.browser-check.json`으로 써서 그 단계를 fail(종료 1)로 둔다. Chrome이 없을 뿐이면 browser-check가 `status:"skipped"`(종료 2, `viewer/chrome-unavailable`)를 낸다. 브라우저는 단계 종료·실패 때 닫는다 | 실행 확인(T-01 `execution:"in-process"`, T-10 skipped·종료 2), 탐색 예외 분기는 코드 확인 |
| R-13 | 단계 통과 판정(`stageStatus`) | 자식 종료 코드가 2이거나 영수증 `status:"skipped"`이면 `skipped`. 종료 코드 0이고 아래 "통과 영수증 조건"을 만족하면 `pass`, 아니면 `fail`. 영수증이 없거나 JSON이 아니면 `fail`(stdout 전체는 `stdout`에 보존). 통과 영수증 조건: **deliver** `ok:true`, `command:"deliver"`, `schemaVersion:1`, `receiptId`가 UUID v4, `specification`·`artifact`가 `{sha256 64hex, bytes≥0}`, `validation{checkCount>0, checksPassed==checkCount, compositionStatus:"pass", errors:0, compositionProfile==요청 quality, (showcase면) warnings:0}`. **check** `ok:true`, `artifact` 유효, `checks[]` 비어 있지 않고 전부 `ok`, `provenance:"current"`, `deliveryReceiptId`가 UUID v4, `composition{schemaVersion:1, profile==quality, status:"pass", summary.errors:0, (showcase면) summary.warnings:0}`. **browser-check(native)** `status:"pass"`, `evidenceKind:"automated-browser"`, `provenance:"current"`, `deliveryReceiptId` UUID v4, `containment/themeStates/readability/viewerChrome.status:"pass"`, 그리고 viewport 목록이 정확히 verification-gates.md의 라이트 4개(1440×900, 1600×1000, 1920×1080, 2048×1320)·테마 6개(라이트 4 + 다크 1440×900, 2048×1320)를 한 번씩 덮고 각 항목이 `ok`. **browser-check(explainer)** `family:"explainer"`, `viewportPolicy:"explainer-desktop-v1"`, 1280·1440 폭 × 높이 900 × light·dark 4개 viewport를 `containment/readability/viewerChrome/themeStates`가 덮고, `commonQa/interactions/references/noJavaScript/print` 각각 `pass`에 관찰이 1개 이상이고 모두 `ok` | 코드 확인. 통과·실패·skipped 사례는 실행 확인 |
| R-14 | 단계 간 바인딩(통과로 판정된 단계 직후) | deliver 영수증이 기준이다: `type`, `specification{sha256,bytes}`, `output`, `artifact{sha256,bytes}`, `receiptId`, `validation.checkCount`. **deliver 직후**: `receipt.type`≠요청 타입이면 `finalize/delivery-type-mismatch`; `receipt.specification`≠finalize가 시작 때 읽은 초안 신원이면 `finalize/candidate-changed-during-delivery`(이때 `validate`가 fail·`deliver`는 `blocked-by-validate`로 기록, `failedStage:"validate"`); `receipt.output`이 출력과 다른 항목이거나 `receipt.artifact`≠지금 디스크 HTML의 해시·바이트이면 `finalize/artifact-binding-mismatch`. **check 직후**: `checks.length`≠deliver의 `checkCount`이면 `finalize/delivery-validation-mismatch`. **check·browser-check 공통**: 영수증의 대상 경로(check는 `file`, browser-check는 `artifact.path`)가 출력과 다른 항목이거나 `artifact`가 deliver의 `artifact`와 다르거나 `deliveryReceiptId`≠deliver의 `receiptId`이면 `finalize/artifact-binding-mismatch`. browser-check는 `(type==='explainer') !== (family==='explainer')`이면 `finalize/browser-family-mismatch`. 어느 경우든 그 단계는 `fail`이 되고 이 진단 1개가 실패 진단이 된다 | 코드 확인. `candidate-changed-during-delivery`는 실행 확인(T-11 지연 0.12초), 나머지 코드만 |
| R-15 | `validate` 단계 | 별도 프로세스가 아니다. deliver 통과 시 `validate`를 `embedded-in-deliver` 항목으로 채운다(1.3). deliver가 실패하면 영수증의 `stage`가 `input`·`render`·`check`이거나 R-14의 `candidate-changed-during-delivery`일 때 `validate`가 fail(+`deliver`는 `blocked-by-validate`), 그 밖의 deliver 실패(`prepare`·`receipt`·`commit`·`release`·`arguments`와 showcase 경고)는 `validate: not-run`, `deliver: fail`. 이 분류가 `gates`와 `failedStage`에 그대로 나온다(R-17) | 실행 확인(T-06: `validate:fail`+`failedStage:"validate"`, T-07a: `validate:not-run`+`deliver:fail`) |
| R-16 | showcase 경고 규칙 | `quality==="showcase"`이고 deliver가 종료 0이며 영수증이 통과 조건 중 `warnings:0`만 어기고(경고 수 `validation.warnings>0`) 나머지는 만족하면: 바인딩 진단이 있으면 그것이, 없으면 경고마다 **오류 진단 하나씩**(`code`=원래 경고의 `composition/*` 코드, `severity:"error"`, `message:"Showcase delivery reported <code>; zero warnings are required."`, `subject:{stage:"deliver", check:"composition", [nodeId]}`, `evidence:{reportedSeverity, …원래 증거}`, `supportedFixes:[원래 detail에서 앞의 "[...] " 제거한 문장]`)가 실패 진단이 된다. `validation.compositionIssues`가 경고 수와 개수가 다르거나 항목이 `severity:"warning"`·`composition/` 접두 코드·비어 있지 않은 `detail`을 갖추지 못했으면 `finalize/showcase-warnings` 하나. 이 실패는 **deliver는 이미 HTML을 교체한 뒤**이므로 출력 HTML과 provenance는 새 정상 쌍으로 남는다(R-22). `standard`에서는 경고가 있어도 통과 | 실행 확인(T-07a: `composition/viewport-height`) |

**실패·후속 상태**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-17 | 단계 결과가 `pass`가 아님 | 반복을 즉시 멈춘다(뒤 단계는 실행·기록 없음, 예: deliver 실패 시 check·browser-check는 `not-run`). `status` = `skipped`면 `skipped`, 아니면 `fail`. 종료 코드 R-05. `failedStage` = 그 단계 이름(R-15의 validate 예외). 진단은 R-18. 마지막 영수증·요약 쓰기와 stdout 출력은 정상 수행된다 | 실행 확인(T-06, T-07, T-10, T-11) |
| R-18 | 실패 진단 선택(`failureDiagnostics` → `consolidateDiagnostics`) | ① 바인딩·showcase 진단이 있으면 그것. ② 없으면 단계 영수증의 `diagnostics`가 비어 있지 않으면 그대로. ③ 없으면 합성 진단 1개: 종료 0인데 통과 조건 미충족이면 `finalize/invalid-stage-receipt`(`The <stage> stage exited successfully without a valid passing receipt.`, `supportedFixes:["restore the <stage> JSON receipt contract before retrying finalize"]`), 그 밖에는 `finalize/stage-failure`(`The <stage> stage did not complete successfully.`, `supportedFixes:["use the compact finalize summary to repair the named subject in place, then rerun finalize once"]`). 합성 진단의 `subject:{stage}`, `evidence:{exitCode, [signal], [reason], [stdout 앞 2000자], [stderr 앞 2000자]}`. ④ `consolidateDiagnostics`: `code+message+subject`가 같은 진단은 하나로. `viewer/viewport-overflow`는 여러 개를 하나로 합쳐 `message:"The rendered artifact overflows N viewport/theme combinations."`, `subject:{diagramType}`, `evidence.overflows[]`(각 `{detection:"browser-measurement"\|"validate-prediction", subject, evidence}`, `innerWidth/innerHeight/readerLayout/readerOverflow/readerFit` 제거), `supportedFixes`는 가장 작은 뷰포트로 한 문장(없으면 원래 것의 합집합). 1개뿐이면 `subject`에서 `artifact`와 증거에서 위 5개 키를 제거. 성공 시에는 deliver의 `severity:"warning"` 진단만 남는다 | 실행 확인(T-06 `schema/required`, T-07a, T-07b 합친 overflow 6건, T-09c·T-12h 단계 영수증 진단). 합성 진단 두 종류는 코드 확인 |
| R-19 | 모든 단계 통과 직후 최종 인계 검사 | ① `inspectDelivery`(= `check`와 같은 provenance 대조, `--require-provenance` 켬)가 실패하거나 `receiptId`가 deliver의 것과 다르면 그 진단(첫 번째)을, 비어 있으면 `finalize/artifact-binding-mismatch`를 실패 진단으로. ② 아니면 지금 HTML 바이트가 deliver의 `artifact`와 같고 provenance 파일이 `status:"current"`, `receiptId`·`type`·`output`·`artifact`가 deliver와 같은지 직접 읽어 보고, 다르면 `finalize/final-artifact-mismatch`(`The artifact or delivery receipt changed after the final gate completed.`, 증거에 기대·현재 값). ③ 아니면 초안을 다시 읽어 시작 때 해시·바이트와 다르면 `finalize/candidate-changed`(`The frozen candidate changed before the final handoff.`, `evidence:{expected, actual}`). 어느 하나에 걸리면 `ok:false`, `status:"fail"`, `failedStage:"finalize"`, 진단은 그 하나, 종료 1. 이때도 4개 gate는 모두 `pass`로 남고(`gates`는 단계 상태), 출력 HTML은 deliver가 만든 그대로다 | 실행 확인(`finalize/candidate-changed`: T-11 지연 0.2·0.3·0.9초). ①②는 코드 확인 |
| R-20 | 후보 해시 고정과 변조 감지 | (a) `--candidate-sha256`가 있고 시작 때 읽은 초안의 SHA-256과 다르면(읽을 수 없으면 `actualSha256` 없음) `finalize/candidate-changed`(`The candidate changed after validation: expected sha256 <기대>, found <실제>.`, `evidence:{candidate, expectedSha256, [actualSha256]}`)로 시작 전 실패(R-06): 단계 실행·영수증·출력 폴더 모두 없음, 종료 1. 같으면 통과해 정상 실행(해시는 검사에만 쓰이고 이후 흐름에 흔적이 없다). 해시 값은 `validate --json`의 `candidate.sha256`·`nextAction.arguments`가 주는 값([input-validation.md](input-validation.md))을 쓰도록 되어 있다. (b) deliver는 초안을 **자기 손으로 다시 읽고** 읽은 바이트의 해시를 영수증 `specification`에 쓰므로, finalize가 시작 때 잡은 신원과 다르면 R-14의 `candidate-changed-during-delivery`. (c) deliver가 끝난 뒤에는 초안을 어떤 단계도 다시 쓰지 않으므로, 변조는 최종 인계 검사(R-19 ③)에서만 걸린다. 두 경우 모두 해시는 **초안 바이트** 기준이며 출력 HTML 변조는 R-14·R-19 ①②가 잡는다 | 실행 확인((a) T-08a·T-08b, (b) T-11 0.12초, (c) T-11 0.2~0.9초) |
| R-21 | `artifact` 필드 | 성공: `{path, sha256, bytes}` = deliver 영수증 `artifact` + 절대 경로. 실패: `{path}`에 **디스크 현재 HTML**의 해시·바이트를 넣는다(첫 실행 실패로 HTML이 없으면 `{path}`만). 요약의 `artifact`도 같다. 따라서 deliver를 넘어 실패하면 이 해시는 새로 전달된 HTML이고, deliver가 렌더 단계에서 실패했으면 이전 HTML의 해시다 | 실행 확인(T-06a `artifact`=이전 HTML 해시, T-06b `{path}`만, T-07a 새 HTML 해시) |
| R-22 | 실패 뒤 디스크 상태 | 영수증·요약 파일은 항상 남는다(시작 전 실패 제외). HTML·provenance는 단계에 따라: **deliver가 입력·렌더·검사 단계에서 실패**: 기존 HTML 바이트 불변, provenance는 실패 표지로 교체, journal 잔존(기존 HTML이 없으면 HTML·provenance 없음, journal만. delivery.md R-13·R-14). **deliver 통과 후 showcase 경고 실패, check 실패, browser-check 실패·skipped, 최종 인계 실패**: deliver가 만든 새 HTML과 `current` provenance가 그대로 남는다(finalize가 되돌리지 않음). browser-check가 실패하면 `<stem>.browser-check.json`(실패·skipped 영수증도)이 쓰이고, deliver 이전 단계에서 실패하면 이번 실행의 browser-check 영수증은 없으며 **이전 실행의 `<stem>.browser-check.json`이 그대로 남을 수 있다**(요약 `evidence`에는 안 실림) | 실행 확인(T-06a/b, T-07a/b, T-10) |
| R-23 | 같은 출력 경로 반복 실행·소유권 충돌 | (a) 같은 초안·같은 경로: HTML 바이트 불변, deliver 영수증 `receiptId`·provenance만 새로 바뀌고, `<stem>.finalize.json`·`-summary.json`은 소유권 검사 없이 덮어쓴다(`startedAt`·`durationMs`·`receiptId` 변경). 이전 영수증이 일반 파일이 아니거나 자리가 바뀌면 `finalize/receipt-publication`. (b) **초안을 바꿔 같은 경로·같은 폴더에 다시 finalize**: deliver·check는 통과하지만(HTML 교체) 이전 `<stem>.browser-check.json`이 옛 HTML 해시에 묶여 있어 browser-check가 `viewer/evidence-path-conflict`(`reason.code:"ownership-artifact-mismatch"`)로 실패한다(verification-gates.md R-35). 결과: `gates` validate·deliver·check는 `pass`, browser-check는 `fail`, `failedStage:"browser-check"`, `browserCheck:{requested:true, ran:false}`, 새 HTML은 이미 교체돼 있고 옛 browser-check 영수증은 그대로. 해결은 `--out-dir`을 새 폴더로 주는 것(T-11c: 통과). 이때 finalize 영수증도 새 폴더로 간다 | 실행 확인(T-02, T-14) |
| R-24 | explainer 분기 | `type==='explainer'`이면 `runFinalize` 전에 이 프로세스에서: 초안 바이트를 읽어 `prepareExplainerInput(바이트, 경로, {repoRoot, quality: 인자 \|\| "showcase", writingMode})`로 prepare → 소유 임시 폴더(`archify-explainer-finalize-*`)에 번들 파일을 쓰고 그 경로를 `ARCHIFY_EXPLAINER_PREPARED`로 단계 자식 환경에 넣는다(deliver 자식은 이 번들을 다시 prepare하지 않고 읽는다). prepare가 실패하면 시작 전 실패(R-06): 영수증 파일 없음, 진단은 `explainer/*`, 종료 1, `gates` 전부 `not-run`. `runFinalize`는 deliver 시작 전과 **각 단계 종료 후(종료 코드 0일 때)** `assertPreparedDependencies`로 초안이 참조한 원본 자원(레포 발췌·이미지 등)이 prepare 때와 같은지 확인하고, 달라졌으면 그 단계를 `{ok:false, stage:"prepare", diagnostics}` 실패로 바꾼다(다음 단계는 실행하지 않음). 영수증을 쓸 때마다 explainer 진단은 `subject`에 `input`·`line`(번들 `sourceMap`, 없으면 1)·`component:"document"`를, `evidence`에 `reason`(=code)·`example`(첫 supportedFix 또는 기본 문장)을 채운다. 완료 후 임시 폴더를 지운다(실패 포함). browser-check 생략과 품질 기본값은 R-03·R-10 | 실행 확인(T-09a~c: prepare 실패와 통과), `ARCHIFY_EXPLAINER_PREPARED`·`assertPreparedDependencies`·진단 주석은 코드 확인 |
| R-25 | 업데이트 확인 필드 | 첫 영수증 쓰기 직후 `startDeliveryUpdateCheck({env, deadlineMs})`를 시작한다(`needsBrowser`이면 4000ms, 아니면 200ms). 단계가 끝난 뒤 최종 쓰기 직전에 기다려 `receipt.update`에 넣는다. `ARCHIFY_UPDATE_CHECK_DISABLED=1`이면 즉시 `unavailable`/`reason:"disabled"`. 필드 이름: `status`(`current`\|`update_available`\|`unavailable`), `installedVersion`, `availableVersion`, `releaseNotes`, `severity`, `summary`, `checkedAt`, `source`, `noticeRequired`, `noticeText`, `eventKey`, `reason`, `suppressedUntil`(일부는 상태에 따라 없음). 요약 영수증은 `unavailable`이면 `update`를 생략한다. 텍스트 모드는 `noticeRequired`일 때 `noticeText`를 출력한다. 내용 의미는 이 스펙 밖 | 실행 확인(`disabled` 경우만: T-01 전체 영수증 `update.reason:"disabled"`, 요약엔 없음). 네트워크 경로(`current`·`update_available`)는 코드 확인 |

**요약 축소 규칙** (`compactFinalizeReceipt`)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | 요약 필드 구성 | 1.3 요약 표대로. `stages`·`startedAt`·`finishedAt`·전체 `diagnostics`·`failedStage` 외 상세는 요약에 없다. `gates`는 단계 `status` 복사, `visualReview`는 항상 `not-requested`. `update`는 `unavailable`이면 제외. `browserCheck`는 전체에 있을 때만 | 실행 확인(T-01, T-06, T-10) |
| R-27 | 진단 상한 8개와 선택 순서 | 전체 `diagnostics`에서 (1) 처음 등장한 `code`마다 1개씩, (2) 이어서 `subject` 키(우선순위 `id, edge, connection, relationship, component, node, path, stage` 중 처음 있는 키의 `이름:JSON값`, 없으면 subject JSON 전체)가 처음인 것마다 1개씩, (3) 남은 것을 원래 순서로, 합쳐서 8개가 찰 때까지 채운다(같은 항목은 한 번만). 요약의 순서는 선택된 순서다. `diagnosticSummary.total`=전체 개수, `shown`=선택 개수, `truncated`=`total>shown`, 잘렸을 때 `omittedByCode`로 생략된 개수를 코드별로 센다. 진단 항목은 `{code, severity(없으면 "error"), message, [subject], [evidence], [supportedFixes]}`만 옮긴다 | 실행 확인(T-13: 10개 `schema/required` → `shown:8, truncated:true, omittedByCode:{"schema/required":2}`, 전체 영수증은 10개) |
| R-28 | 통과 시 권고 필드 | `ok`일 때만. **`visualReviewRecommendation`**: check 단계 영수증 `composition.metrics`의 `resolvedCrossovers`, `routesOverSuggestedBends`, `routesOverSuggestedStretch` 중 유한 양수만 `signals`에 모아 하나라도 있으면 생성. `reason`은 고정 문장, `routeReview`가 있으면 `affectedRoutes{crossings(최대 8), detours(최대 8), truncated}`, `advisoryOnly = (type !== 'architecture')`가 아니고 hints가 있으면 `hints`(최대 8개 노드 이동 제안, `placementHints`), `repair`는 architecture는 레이아웃 수리 지침 문장, 그 밖의 타입은 "Advisory only …" 문장. 종료 코드·gate에는 영향 없음. **`layoutReviewRecommendation`**: check 영수증 `composition.leadingSpace.reviewSuggested===true`이면 `{action:"inspect-leading-space", evidence:leadingSpace, reason, repair}`, 그리고 타입이 sequence이고 `composition.sequenceColumnSpace.reviewSuggested===true`이면 `{action:"inspect-sequence-width", …}`로 **덮어쓴다**(둘 다 해당하면 sequence 쪽만 남음) | 코드 확인. 예제 4종 통과 실행(production-deployment·checkout-platform architecture, cache-miss sequence)에서는 두 필드 모두 나오지 않았다(미관찰) |
| R-29 | `nextAction` | `ok:false`이고 `status:"fail"`이고 `failedStage:"validate"`일 때만(skipped·deliver 이후 실패에는 없음): `{action:"edit-in-place", candidate:<초안 경로>, constraint, then:"finalize-once"}`. `constraint`는 architecture이고 진단 코드 중 하나가 정규식 `^(clean-flow\/\|composition\/(proper-crossing\|ambiguous-corridor\|border-run\|container-border-run\|excessive-route-detour\|route-rhythm\|arrowhead-collision))`에 맞으면 레이아웃 수리 지침 문장, 아니면 "Preserve unaffected semantics and geometry; apply each diagnostic's supportedFixes, …" 문장 | 실행 확인(T-06a, T-12h: 둘째 문장), 첫째 문장은 코드 확인 |

- 불변식:
  - 시작 전 실패(R-06)를 뺀 모든 실행은 전체·요약 영수증 두 파일을 남기고, 둘은 항상 같은 영수증의 같은 시점 사본이다(요약 = 축소 함수의 결과).
  - `ok:true`이면 `gates` 중 `not-run`은 explainer의 `browser-check`뿐이고, 나머지 셋은 `pass`이며, 세 영수증(deliver·check·browser-check)의 `artifact`와 `deliveryReceiptId`·`receiptId`가 모두 같고, 그 해시가 종료 시점의 HTML·`current` provenance와 같다.
  - 어떤 단계도 첫 비통과 단계 뒤에는 실행되지 않는다.
  - finalize는 HTML·provenance를 직접 쓰지 않는다(쓰는 것은 deliver뿐).
- 미결정: 없음.
- 확인 한계: `finalize`는 `--open`을 받지 않는다(알 수 없는 옵션으로 종료 2, 코드 확인). 네트워크 업데이트 확인(`current`·`update_available`), Windows·대소문자 구분 파일시스템, 영수증 자리 경쟁·`finalize/receipt-publication`, 프로세스가 도중에 죽었을 때의 `running` 영수증, `visualReviewRecommendation`·`layoutReviewRecommendation`·`finalize/final-artifact-mismatch`·`finalize/delivery-type-mismatch`·`delivery-validation-mismatch`·`artifact-binding-mismatch`·`browser-family-mismatch`·`invalid-stage-receipt`·`stage-failure`·`showcase-warnings`와 explainer의 `assertPreparedDependencies` 실패는 **실행으로 만들지 못했고** 코드로만 확인했다. 환경변수 `ARCHIFY_EXPLAINER_PREPARED`는 코드로만 확인(자식 환경을 직접 관찰하지 않음). 실행은 macOS(APFS, 대소문자 무시) · Node v26.10.0 · 설치본(`~/.claude/skills/archify`, 실행 때 `diff -rq`로 레포 `archify/`와 차이 없음 확인) · `ARCHIFY_UPDATE_CHECK_DISABLED=1`에서 했다. 타이밍 의존 사례(T-11)는 지연 값에 따라 결과가 갈릴 수 있어 4회 관찰했다.

### 1.5 필수 코드 참조 [필수]

Apache-2.0(레포 `LICENSE`, 인용 가능; overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/bin/archify.mjs:5888-5997` `commandFinalize` | 인자 추출 순서, 위치 인자 3개, explainer prepare·번들·환경변수, `runFinalize` 인자 매핑, 시작 전 실패 객체, stdout 출력 | R-01, R-02, R-03, R-04, R-05, R-06, R-24 |
| C-02 | `archify/bin/archify.mjs:2310-2411` `extractQualityArgs`·`extractRepoRootArgs`·`extractOutDirArgs`·`extractExplainerWritingArgs`; `:5822-5886` `extractFinalizeReceiptArgs`·`extractCandidateSha256Args` | 각 옵션의 `--x v`·`--x=v` 형태, 값 누락·잘못된 값 코드, 64hex 검사 | R-01 |
| C-03 | `archify/bin/finalize.mjs:25-87` `identity`·`captureReceipt`·`writeJsonAtomic` | 신원 `{path,sha256,bytes}`, 영수증 JSON 직렬화(2칸+개행), 자리 선점·게시 | R-07, R-09 |
| C-04 | `archify/bin/finalize.mjs:89-220` `validIdentity`·`validReceiptId`·`validStageReceipt` 및 그 helper | 단계별 통과 영수증 조건(R-13의 목록 그대로) | R-13 |
| C-05 | `archify/bin/finalize.mjs:222-382` `identityMismatchDiagnostic`·`showcaseWarningDiagnostics`·`stageBindingDiagnostic`·`finalArtifactDiagnostic` | 바인딩·showcase·최종 인계 진단의 코드·메시지·증거·`supportedFixes` 문장 | R-14, R-16, R-19 |
| C-06 | `archify/bin/finalize.mjs:384-466` `stageStatus`·`consolidateDiagnostics`·`failureDiagnostics` | 단계 상태 판정, 진단 병합·overflow 합치기, 합성 진단 | R-13, R-18 |
| C-07 | `archify/bin/finalize.mjs:493-524` `stageCaptureMaxBuffer`·`defaultRunner`·`stageArguments` | 자식 호출 모양과 단계별 인자 | R-11 |
| C-08 | `archify/bin/finalize.mjs:526-561` `defaultFinalizeReceiptPath`·`defaultFinalizeSummaryPath`·`reservedFinalizePaths` | 영수증·요약 이름과 겹침 금지 목록 | R-08, R-06 |
| C-09 | `archify/bin/finalize.mjs:563-720` `placementHints`·`ROUTE_DIAGNOSTIC`·`compactFinalizeReceipt` | 요약 필드 순서, 진단 선택(8개), 권고·`nextAction` 생성 규칙. 정규식·문장 원문은 이 줄 범위를 그대로 가져온다 | R-26, R-27, R-28, R-29 |
| C-10 | `archify/bin/finalize.mjs:722-833` `runFinalize` 앞부분 | 시작 순서, `needsBrowser`, 영수증 초기값, `persistReceipts`(explainer 진단 주석 포함), 업데이트 확인 시작 | R-07, R-09, R-10, R-24, R-25 |
| C-11 | `archify/bin/finalize.mjs:835-1008` 단계 반복 | 자식 실행·browser-check in-process·`assertPreparedDependencies`·단계 항목 기록·validate 내장·실패 중단·`failedStage` | R-11, R-12, R-13, R-15, R-17 |
| C-12 | `archify/bin/finalize.mjs:1010-1055` 최종 인계 | 성공 판정, 최종 인계 검사, `artifact` 확정, 마지막 쓰기, 반환값 | R-19, R-20, R-21, R-25 |
| C-13 | `archify/bin/delivery-update.mjs:9-92` `unavailable`·`normalize`·`startDeliveryUpdateCheck` | `update` 필드 모양과 `disabled` 단락 | R-25 |

범위 안 프로젝트 내부 helper: `pathsAlias`(output-path.mjs)는 "물리 경로가 같은 항목", `browserCheckSidecarPaths`·`boundedSidecarStem`은 "browser-check 영수증 이름 규칙(verification-gates.md 1.3 영수증 파일 이름 · delivery.md C-01)"으로 풀었다. `captureAtomicOutput`·`publishRegularFileBinding`은 R-07·R-09의 "자리 선점 후 임시 파일을 거쳐 게시, 쓰기 직전 자리 재확인"으로 푼다.

### 1.6 수락 사례 [필수]

출처: 모두 **원본 실행 관찰**(설치본, 2026-11-02). 스크립트 [run.sh](../../../artifacts/archify/spec-demos/finalize/run.sh) → 출력 [out/](../../../artifacts/archify/spec-demos/finalize/out/)(`<이름>.stdout/.stderr/.exit/.ls`와 영수증 사본), 타이밍 사례 [run-race.sh](../../../artifacts/archify/spec-demos/finalize/run-race.sh) → [out/race-summary.txt](../../../artifacts/archify/spec-demos/finalize/out/race-summary.txt), 입력 [in/](../../../artifacts/archify/spec-demos/finalize/in/). scratch 작업 폴더는 `work/`. 표의 "아키텍처 샘플" = `in/brand-aware-delivery.architecture.json`(sha256 `211c126e…`, 2789바이트), "lifecycle 정상" = `in/ok.json`(`7df53378…`, 4003바이트), `bad-schema.json`은 거기서 최상위 `states`를 뺀 것(`24678f52…`), `ok-v2.json`은 제목만 다른 정상 입력(`d921527e…`), "workflow 경고 샘플" = `in/release-delivery.workflow.json`. 모든 실행에서 `ARCHIFY_UPDATE_CHECK_DISABLED=1`.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-04, R-08~R-12, R-13, R-14, R-21, R-25, R-26 | 빈 폴더 `work/a`. `finalize architecture <아키텍처 샘플> out.html --json` | 종료 0. stdout JSON 한 줄: `ok:true, status:"pass", type:"architecture", quality:"showcase", gates:{validate,deliver,check,browser-check:"pass"}, diagnostics:[], diagnosticSummary:{total:0, shown:0, truncated:false}, visualReview:"not-requested", browserCheck:{requested:true, ran:true}`, `artifact{sha256 88ceda09…, bytes 857101}`, `evidence{receipt, summaryReceipt, browserCheckReceipt}`, 요약에 `update` 없음. 폴더에 `out.html, out.delivery.json, out.browser-check.json, out.finalize.json, out.finalize-summary.json`만. 전체 영수증 `stages`: `validate{execution:"embedded-in-deliver", durationMs:null}`, `deliver.command`=`[node, archify.mjs, "deliver","architecture",<입력 절대>,<출력 절대>,"--quality","showcase","--json"]`, `check.command`=`[…, "check",<출력>,"--require-provenance"]`, `browser-check{execution:"in-process"}`, 전체 `update.reason:"disabled"` |
| T-02 | R-04, R-23 | T-01 직후 같은 명령을 `--json` 없이 | 종료 0. stdout 4줄(`finalize pass: <abs>/out.html` / `gates validate:pass deliver:pass check:pass browser-check:pass` / `receipt <abs>/out.finalize.json` / `perceptual visual review not-requested`), stderr 빈. HTML 해시 불변, deliver `receiptId`만 새 값, 파일 목록 불변 |
| T-03 | R-08 | `finalize architecture … out.html --out-dir rcpt --json` (`work/b`) | 종료 0. `out.html`·`out.delivery.json`은 `work/b/`, `rcpt/`에 `out.finalize.json, out.finalize-summary.json, out.browser-check.json`. `evidence.receipt`=`…/rcpt/out.finalize.json` |
| T-04 | R-08 | `… out.html --receipt r/my.json --json` (`work/c`) | 종료 0. `r/my.json`, `r/my-summary.json`, HTML 옆에 `out.browser-check.json`·`out.delivery.json`. `evidence.summaryReceipt`=`…/r/my-summary.json` |
| T-05 | R-06, R-07 | `… out.html --receipt out.delivery.json --json` (`work/d`) | 종료 1. stdout `ok:false, status:"fail"`, `specification{path}`(해시 없음), `gates` 전부 `not-run`, 진단 `finalize/runtime`(`The finalize receipt must be distinct from … out.delivery.json`). 폴더에 파일 없음(폴더는 존재) |
| T-06 | R-05, R-15, R-17, R-18, R-21, R-22, R-26, R-29 | (a) `work/e`에 lifecycle 정상을 finalize(통과) 후 같은 경로 `e.html`에 `bad-schema.json`을 `--json` (b) 새 폴더 `work/f`에 `bad-schema.json` (c) (b)를 텍스트 모드로 | (a) 종료 1. `gates{validate:"fail", deliver:"not-run", check:"not-run", browser-check:"not-run"}`, `failedStage:"validate"`, `diagnostics:[schema/required(subject{diagramType,path:"/"}, evidence{missingProperty:"states"}, supportedFixes:['add required property "states"'])]`, `diagnosticSummary{1,1,false}`, `evidence`에 `browserCheckReceipt` 없음, `browserCheck{requested:true, ran:false}`, `nextAction{action:"edit-in-place", candidate:<bad-schema 경로>, then:"finalize-once"}`. 전체 영수증 `stages.validate{status:"fail", exitCode:1, execution:"embedded-in-deliver"}`, `stages.deliver{status:"not-run", execution:"blocked-by-validate"}`, `artifact`=기존 HTML 해시 `ed4d735d…`(HTML 해시 전후 동일). `e.delivery.json`은 `status:"failed", stage:"render"`, `e.delivery-pending.json` 존재, 이전 실행의 `e.browser-check.json` 잔존. (b) 종료 1, `artifact{path}`만, 폴더에 `f.delivery-pending.json`·`f.finalize.json`·`f.finalize-summary.json`뿐(HTML 없음). (c) 종료 1, stdout 4줄(`finalize fail: …` / `gates validate:fail deliver:not-run check:not-run browser-check:not-run` / `receipt …` / `perceptual …`), stderr 빈 — 진단은 출력되지 않음 |
| T-07 | R-05, R-16, R-17, R-18, R-21, R-22 | (a) workflow 경고 샘플을 기본(`showcase`)으로 `--json` (`work/g`) (b) 같은 입력에 `--quality standard` (`work/h`) | (a) 종료 1. `gates{validate:"not-run", deliver:"fail", check:"not-run", browser-check:"not-run"}`, `failedStage:"deliver"`, 진단 1개 `composition/viewport-height`(`severity:"error"`, `message:"Showcase delivery reported composition/viewport-height; zero warnings are required."`, `subject{stage:"deliver", check:"composition"}`, `evidence{reportedSeverity:"warning", overflowPx:909, …}`). `stages.deliver{status:"fail", exitCode:0}`. 폴더에 `w.html`·`w.delivery.json`(정상 쌍)·finalize 영수증 2개, browser-check 영수증 없음, `artifact`=새 HTML(`c5d05dbb…`, 846840). (b) 종료 1. `gates{pass, pass, pass, "fail"}`, `failedStage:"browser-check"`, 진단 1개 `viewer/viewport-overflow`(6개 뷰포트를 합친 메시지 `The rendered artifact overflows 6 viewport/theme combinations.`, `subject:{}`, `evidence.overflows` 6개 각 `detection:"browser-measurement"`), `browserCheck{requested:true, ran:true}`, `evidence.browserCheckReceipt` 있음 |
| T-08 | R-01, R-06, R-20 | `SHA`=`ok.json`의 sha256. (a) `finalize lifecycle ok.json i.html --candidate-sha256 SHA --json` (b) `ok-v2.json`(다른 초안)에 같은 `SHA` (c) `--candidate-sha256 ABC` `--json` / 텍스트 | (a) 종료 0 통과(`i.*` 파일 5개). (b) 종료 1, stdout 한 줄 JSON `gates` 전부 `not-run`, 진단 `finalize/candidate-changed`(`expected sha256 7df53378… found d921527e…`, `evidence{candidate, expectedSha256, actualSha256}`), 출력 폴더·영수증 파일 생성 없음(`i2.*` 없음). (c) 종료 2, `--json`이면 pretty JSON `stage:"arguments"`, `cli/invalid-option-value`, 텍스트면 stderr `--candidate-sha256 must be 64 lowercase hexadecimal characters.` |
| T-09 | R-03, R-10, R-24 | (a) `finalize explainer in/ok.archify.md x.html --repo-root <archify 체크아웃> --json` (b) 같은 명령에 `--browser-check` (c) `in/b07-unresolved-source.archify.md`(참조 오류)를 (a)와 같이 (`work/y`) | (a) 종료 0. `gates{validate:"pass", deliver:"pass", check:"pass", browser-check:"not-run"}`, `quality:"showcase"`, `browserCheck{requested:false, ran:false}`, `evidence`에 `browserCheckReceipt` 없음, 전체 영수증 `stages["browser-check"]={status:"not-run", execution:"not-requested"}`, `deliver.command`에 `--quality showcase --repo-root <abs> --json`(`--writing` 없음), deliver 영수증에 `explainer{preparedSha256, dependencies[]}`. 폴더에 `x.html, x.delivery.json, x.finalize*.json`(browser-check 영수증 없음). (b) 종료 0, `browser-check:"pass"`, `browserCheck{requested:true, ran:true}`. (c) 종료 1, 시작 전 실패 객체: `gates` 전부 `not-run`, 진단 `explainer/unresolved-reference`(`subject{line:7, column:1, component:"prose", path, panelId, input}`), `browserCheck{requested:false, ran:false}`, 폴더·영수증 파일 없음 |
| T-10 | R-05, R-12, R-17 | 환경 `ARCHIFY_CHROME=/nonexistent`로 아키텍처 샘플 `--json` (`work/j`) | 종료 **2**. `status:"skipped"`, `ok:false`, `gates{pass, pass, pass, "skipped"}`, `failedStage:"browser-check"`, 진단 `viewer/chrome-unavailable`(`severity:"warning"`), `browserCheck{requested:true, ran:false}`, `evidence.browserCheckReceipt` 있고 `j.browser-check.json` 생성, HTML·provenance는 정상 |
| T-11 | R-14, R-19, R-20 | `run-race.sh`: lifecycle 정상 사본을 `finalize`에 주고 실행 시작 후 `d`초 뒤 그 초안 끝에 개행 1바이트 추가. d=0.12, 0.2, 0.3, 0.9 | 모두 종료 1. d=0.12: `gates{validate:"fail", deliver:"not-run", …}`, `failedStage:"validate"`, 진단 `finalize/candidate-changed-during-delivery`. d=0.2·0.3·0.9: `gates` 네 단계 모두 `pass`, `status:"fail"`, `failedStage:"finalize"`, 진단 `finalize/candidate-changed`. (0.12초는 deliver 자식이 초안을 읽기 전, 0.2초 이후는 읽은 뒤 — 경쟁이므로 환경에 따라 달라질 수 있음) 이 실패에서도 출력 HTML은 deliver가 만든 대로 남는다 |
| T-12 | R-01, R-02, R-05, R-06, R-18, R-29 | 인자 오류 열 개: (a) 인자 없음 (b) `--bogus --json` (c) `--bogus` (d) 타입 `nosuch --json` (e) `--out-dir` 값 없음 (f) 위치 인자 4개 `--json` (g) 출력 `z.txt --json` (h) 존재하지 않는 입력 `--json` (i) `--quality gold --json` (j) `--writing strict`(lifecycle) `--json` (k) `--receipt r.txt --json` | (a)(f) 종료 2, `--json` pretty JSON `stage:"arguments"`, `error`에 사용법 전체. (b) 종료 2, `cli/unknown-option`. (c) 종료 2, stderr `Unknown finalize option "--bogus".`. (d) 종료 2, `cli/unknown-diagram-type`. (e) 종료 2, stderr `--out-dir requires a directory path.`(JSON 아님). (g) 종료 **1**, 한 줄 JSON 시작 전 실패 객체, 진단 `output/cli-extension`(`message:"CLI output must target a .html file."`), 영수증 없음. (h) 종료 1, `gates{validate:"fail", …}`, `failedStage:"validate"`, 진단 `input/read`(`systemCode:"ENOENT"`), `nextAction` 있음, `z.finalize*.json`과 `z.delivery-pending.json` 생성. (i) 종료 2, `cli/invalid-option-value`(`supportedValues`). (j) 종료 2, `cli/unsupported-option`. (k) 종료 1, `output/cli-extension`, 영수증 없음 |
| T-13 | R-18, R-26, R-27 | 모든 state에서 `id`를 뺀 `in/many-errors.json`(10개 state)을 `--json` | 종료 1, `failedStage:"validate"`. 요약 `diagnostics` 8개(전부 `schema/required`, subject `path:"/states/0"`~`/states/7"`가 `identity:"Queued"` 등과 함께), `diagnosticSummary{total:10, shown:8, truncated:true, omittedByCode:{"schema/required":2}}`. 전체 영수증 `diagnostics`는 10개 |
| T-14 | R-23 | `work/k`: (a) lifecycle 정상 finalize(통과) (b) 같은 `k.html`에 `ok-v2.json`을 finalize (c) 같은 입력 `ok-v2.json`을 `--out-dir k.review-2`로 | (a) 종료 0. (b) 종료 1, `gates{pass, pass, pass, "fail"}`, `failedStage:"browser-check"`, 진단 `viewer/evidence-path-conflict`(`evidence.reason.code:"ownership-artifact-mismatch"`), `browserCheck{requested:true, ran:false}`. HTML은 `ok-v2`의 새 HTML로 교체돼 있고(해시 `out/11b.html.sha`), `k.browser-check.json`은 옛 것. (c) 종료 0, `k.review-2/`에 browser-check·finalize 영수증 3개 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (archify@a406594 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `archify.mjs:5888-5912`, C-02, `:2227-2241` `fail`·`rejectCliArgument`, `:7283-7288`(아규먼트 오류 처리), `:4366-4380` `reportArtifactArgumentFailure` | 코드 읽음 + T-12 실행. `--receipt`의 경로 값 오류는 T-12(k)만 |
| R-02 | `archify.mjs:5910`(`rendererPath(type)`), `:2243-2255` | 코드 + T-12(d) |
| R-03 | `archify.mjs:5925,5938`(`qualityArgs.quality \|\| 'showcase'`), `finalize.mjs:514-524` `stageArguments` | T-01·T-09a의 `command` 배열 |
| R-04 | `archify.mjs:5982-5996` | T-01, T-02, T-06c 실행 |
| R-05 | `archify.mjs:5996`(`process.exitCode = result.exitCode`), `finalize.mjs:998`(`status==='skipped' ? 2 : (code \|\| 1)`), `:384-387` `stageStatus` | T-01(0), T-07a(deliver 종료 0 → 1), T-10(2) |
| R-06 | `archify.mjs:5956-5979`(catch), `finalize.mjs:743-800` | T-05, T-08b, T-09c, T-12g·k |
| R-07 | `finalize.mjs:743-821` | 순서는 코드. T-08b(폴더 미생성), T-05(폴더 생성·파일 없음)로 ③·④ 경계 확인 |
| R-08 | `finalize.mjs:526-561` C-08, `:766-788` | T-03, T-04 실행. 긴 이름 해시 축소는 코드만 |
| R-09 | `finalize.mjs:25-87,801-817,1007,1049` | 코드. `running` 사본은 관찰 못 함 |
| R-10 | `finalize.mjs:746,795-796,835` | T-09a·b |
| R-11 | `finalize.mjs:493-524,885-897`(자식 실행과 deliver 전용 env), `archify.mjs:5930-5933`(env에 번들 변수) | `command` 배열은 실행 확인, env는 코드 |
| R-12 | `finalize.mjs:847-884`, `archify.mjs:5952-5954` `runBrowserCheck`, `visual-check.mjs` `persistBrowserCheckFailure` | T-01 `execution:"in-process"`, T-10. 탐색 예외 분기는 코드 |
| R-13 | `finalize.mjs:188-220,384-387` | 통과·실패·skipped는 T-01·T-06·T-10, 조건 목록은 코드 |
| R-14 | `finalize.mjs:267-340` | T-11(0.12초)만 실행. 나머지 코드 |
| R-15 | `finalize.mjs:940-985` | T-06·T-07 |
| R-16 | `finalize.mjs:238-265,926-935` | T-07a |
| R-17 | `finalize.mjs:988-1008` | T-06, T-07, T-10 |
| R-18 | `finalize.mjs:389-466,998-1002` | T-06, T-07b, T-13. 합성 진단은 코드 |
| R-19 | `finalize.mjs:342-382,1010-1042` | T-11(candidate-changed)만 실행 |
| R-20 | `archify.mjs:5851-5886`, `finalize.mjs:752-762,281-290,1030-1042` | T-08, T-11 |
| R-21 | `finalize.mjs:29-36,939-941,1043-1047` | T-06a·b, T-07a |
| R-22 | 코드 + delivery.md R-13·R-14, verification-gates.md R-34·R-35 | T-06, T-07, T-10, T-14 |
| R-23 | `finalize.mjs:49-54,801-817`, verification-gates.md R-35 | T-02, T-14 |
| R-24 | `archify.mjs:5919-5934,5980-5982`, `archify.mjs:2420-2425`(자식 deliver가 번들을 읽음), `finalize.mjs:848-855,899-905,801-808` | T-09. 번들 의미는 explainer.md R-19·R-20 |
| R-25 | `finalize.mjs:818,1048`, `delivery-update.mjs:9-60` | T-01(`disabled`) |
| R-26~R-29 | C-09 `finalize.mjs:586-720` | T-01, T-06, T-13 실행. R-28은 코드, 예제 3종 통과 시 필드 없음 확인 |
| T-01~T-14 | 실행 기록 링크는 1.6 | 실제 출력과 대조 |
| 문서와 구현 차이 | (1) feature map·q1은 finalize가 "단계를 자식 프로세스로 실행"한다고 했고 delivery-contract.md도 `deliver`·`check`·`browser-check`를 호출한다고 읽히지만, **browser-check는 자식이 아니라 같은 프로세스에서 `executeBrowserEvidence`로 실행**된다(`finalize.mjs:847,880-884`, 영수증 `execution:"in-process"`). `check`·`deliver`만 자식. (2) delivery-contract.md는 "Its stdout is one compact JSON object"라 하나 그것은 `--json`일 때만이고 기본은 텍스트 4줄이며 진단은 나오지 않는다(`archify.mjs:5982-5996`). (3) overview 2절은 문서의 4단계(validate·deliver·check·browser-check) vs 코드를 "모순은 아니다"라 적었다: 실제로 `validate`는 deliver 내장 항목이고 별도 단계가 아니다(R-15, 이 스펙이 확정). (4) q3는 영수증 파일 이름 규칙을 `미확인`으로 뒀다 — 이 스펙 1.3이 확정한다(기본은 browser-check 영수증 폴더·stem 공유, `--out-dir`·`--receipt` 효과). (5) q2는 "마지막에도 후보 파일이 도중에 바뀌지 않았는지 해시로 한 번 더 확인"이라 했고 이는 R-19로 구체화된다: 확인 대상은 **초안(후보 JSON)과 HTML·provenance** 둘이다. (6) 인자 오류 종료 코드가 둘로 갈린다: `cli/*` 인자 오류는 2, 같은 "시작 전" 실패 객체 경로를 타는 출력 확장자·후보 해시 불일치는 1(R-05). (7) delivery-contract.md는 "Chrome은 delivery와 strict checking이 통과한 뒤에만 시작"이라 하며 코드와 일치한다(R-12). (8) `--writing`은 finalize usage 한 줄에 없지만 처리된다. (9) 초안의 `meta.quality_profile`이 있어도 finalize의 `--quality` 기본 `showcase`가 이긴다 — q2·explainer.md R-17과 일치하며 deliver 단독 실행과 다르다 |

### 2.2 코드 읽는 순서 [선택]
`commandFinalize`(`archify.mjs:5888`)로 진입해 인자와 explainer prepare를 보고, `runFinalize`(`finalize.mjs:722`)를 위에서 아래로 읽는다: 시작 순서(743-833) → 단계 반복(835-1008, 자식 실행·바인딩·기록·중단) → 최종 인계(1010-1055). 그다음 통과 조건(`validStageReceipt`, 188)과 바인딩 진단(`stageBindingDiagnostic`, 267) → 요약(`compactFinalizeReceipt`, 586). 구현 전략: 각 단계의 stdout 영수증을 "자기 단계의 진술"로만 받고, deliver 영수증의 `artifact`·`receiptId`를 기준값으로 두어 뒤 단계 영수증이 같은 값을 말하는지 대조한다. 영수증은 단계마다 먼저 쓰고(진행 중 상태가 디스크에 남음), 마지막에 한 번 더 쓴다.

### 2.3 비교·재사용 출처 [선택]
다른 레포 구현 없음. 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]
없음.
