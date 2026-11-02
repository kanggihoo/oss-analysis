---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/SKILL.md
  - archify/references/delivery-contract.md
  - archify/references/architecture-layout-repair.md
  - archify/references/authoring-contract.md
  - archify/bin/finalize.mjs
  - archify/bin/archify.mjs
  - archify/bin/visual-check.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/renderers/shared/validator.mjs
depends: [finalize-orchestration.md, verification-gates.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# 실패 진단·수리 루프

> `finalize`·`deliver`·`check`·`browser-check`가 비정상 종료하면 코드는 진단 JSON·`supportedFixes`·`nextAction`을 내고(`[코드]`), 지시문(SKILL.md·references)은 에이전트가 그것을 읽고 초안을 고쳐 같은 `finalize`를 다시 돌리는 절차와 횟수 한도를 정한다(`[지시문]`). 통과 뒤의 권고 필드(`visualReviewRecommendation`·`layoutReviewRecommendation`)와 선택 시각 검토도 이 루프의 일부다.

<!--
원본에서 확인한 범위: SKILL.md 49-55·87-103, delivery-contract.md의 "Failed finalize and candidate repair"(3-13), "Sequence width review"(491-498), "A new candidate at an existing output path"(563-574), "Perceptual review"·"Handoff receipt"(602-665), architecture-layout-repair.md 전체, authoring-contract.md의 "Repair evidence"·"Repair order"·"Workflow viewport repair"(244-318), finalize.mjs의 compactFinalizeReceipt(563-720)·최종 인계(1030-1045), archify.mjs의 COMPOSITION_FIXES·compositionFixes(2697-2785)와 validate 통과 영수증(7140-7165), visual-check.mjs의 viewport-overflow 진단(2150-2252). supportedFixes 문장은 렌더러·게이트 약 45개 파일에 흩어져 있어(grep) 전부 읽지 않았다. 대신 일부러 만든 실패 204건에서 나온 문장을 수집했다(1.3 "supportedFixes").
읽지 않은 것: geometry.mjs·route-quality.mjs의 hint 생성식 전체, workflow-compiler(supportedFixes 69곳), explainer/*의 fix 문장(explainer.md 소관), 테스트.
스크립트·출력: ../../../artifacts/archify/spec-demos/repair-loop/ (이하 DEMO). 설치본(`~/.claude/skills/archify`)으로 실행했고 `diff -rq`로 레포 `archify/`와 차이 없음을 확인했다(DEMO/out/installed-vs-repo.diff.txt).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. 에이전트가 `finalize <type> <candidate> <output.html> --quality showcase [--repo-root …] --json`을 돌린다. 비정상 종료(종료 코드 ≠ 0)는 성공이 아니다(R-12).
2. **코드가 내는 것**: 종료 코드, 요약 영수증(`status`, `failedStage`, `gates`, 최대 8개 `diagnostics[]`, `diagnosticSummary`)과 `evidence.summaryReceipt` 경로. `failedStage:"validate"`일 때만 `nextAction`이 붙는다(R-01~R-05).
3. 에이전트는 진단을 `code`·`subject`·`evidence`·`supportedFixes`로 읽는다. 단계별로 갈린다(1.3 단계 표): 초안 JSON 문제(`validate`)는 초안을 제자리에서 고치고, 환경·증거 문제(Chrome 없음, 동시 전달, 증거 경로 소유권)는 초안을 고치지 않고 경로·환경을 바꿔 같은 바이트로 다시 돌린다(R-13, R-18~R-21).
4. 고칠 때는 요청 의미·라벨·근거·합의된 토폴로지를 보존하고 연결된 이웃만 편집한다(R-14). 순서는 스키마 → 겹침 → 경로 → 교차 → 라벨(R-13).
5. **완전한 `finalize`를 같은 인자로 다시** 돌린다. 이전 `--candidate-sha256`은 뺀다. 출력 경로가 이미 browser-check를 거쳤으면 새 `--out-dir`을 준다(R-17).
6. 같은 문제(같은 code·subject·stage·evidence)가 두 번의 집중 수리 뒤에도 남으면 측정값·계약을 다시 보고, 증거에 근거한 재시도 한 번 뒤에는 구체적인 격차를 보고하고 멈춘다(R-15). **이 횟수를 세는 코드는 없다**(R-07).
7. 통과했어도 `visualReviewRecommendation`·`layoutReviewRecommendation`이 있으면 지시문이 정한 한 번짜리 위치 수리를 할 수 있다(R-20, R-21). 사람 눈 검토는 요청·의심이 있을 때만 하고 보정 라운드는 2회까지다(R-22).

### 1.2 범위·통합 지점 [필수]
- 제공: 수리 루프가 소비하는 신호(진단 객체·`supportedFixes`·`nextAction`·통과 후 권고)의 의미와 한계, `supportedFixes` 문장의 종류, 수리 한도 5종과 그 출처, 출력 경로 재사용·`--out-dir` 규칙, 실패 단계별 수리 표, 레이아웃 수리의 "한 번" 규칙과 복원 규칙, 실제로 일부러 만든 실패에서 관찰한 흔한 진단 code.
- 제외:
  - 진단 객체의 공통 모양·`schema/*`·`repository-evidence/*` 코드 목록·`supportedFixes` 정규화는 [input-validation.md](input-validation.md)(1.3 "진단 객체"). 여기서는 다시 정의하지 않는다.
  - 영수증 필드(`failedStage`, `gates`, `diagnostics`, `nextAction`, `visualReviewRecommendation`, `layoutReviewRecommendation`), 종료 코드, 8개 한도, 합성 진단(`finalize/*`)의 생성은 [finalize-orchestration.md](finalize-orchestration.md) R-05·R-14~R-19·R-26~R-29. 여기서는 소비 규칙만 쓴다.
  - 각 게이트가 어떤 조건에서 어떤 code를 내는지(`delivery/*`, `viewer/*`, `artifact/*`, `composition/*`)는 [verification-gates.md](verification-gates.md), 전달 실패 영수증과 잠금·복구는 [delivery.md](delivery.md), 렌더 중 레이아웃 진단은 [rendering.md](rendering.md). 설명용 링크이며 `depends`에는 넣지 않았다.
  - explainer의 `explainer/*` 진단과 `patch`는 [explainer.md](explainer.md). 여기서는 prepare 실패가 시작 전 실패 객체로 나오는 것만 다룬다(1.3 단계 표).
  - LLM이 이 지시문을 실제로 따르는지, 따랐을 때 결과 품질: **미확인**(1.4 확인 한계 1). 이 스펙의 수리 사례는 실험자가 지시문을 흉내 내어 고친 것이다.
- 외부 의존: 에이전트(LLM)가 초안 JSON을 고치는 행위. 코드는 LLM을 부르지 않는다(overview 2절).
- 소유 상태·부작용: 이 기능이 새로 만드는 파일·상태는 없다. 수리 루프가 일으키는 부작용은 finalize·deliver가 소유한 것과 같다(HTML·provenance 교체, 영수증 덮어쓰기, `--out-dir` 폴더 생성). 에이전트가 고치는 초안 파일은 에이전트 소유다.

### 1.3 인터페이스와 데이터 의미 [필수]

**수리 루프가 읽는 신호**

| 신호 | 어디서 | 모양·조건 | 소비 규칙 |
|---|---|---|---|
| 요약 영수증 | stdout(`--json`) 또는 `<stem>.finalize-summary.json`(`evidence.summaryReceipt`) | 필드·8개 한도는 finalize R-26·R-27. 텍스트 모드 stdout에는 **진단이 없다** | 수리에는 `--json`이거나 요약 파일을 읽는다. 요약에 증거가 모자랄 때만 전체 영수증·단계 영수증을 연다(R-11) |
| `diagnostics[]` | 요약 | `{code, severity, message, [subject], [evidence], [supportedFixes]}`([input-validation.md](input-validation.md) 1.3). `severity:"warning"`(예: `viewer/chrome-unavailable`)도 실패 영수증에 실릴 수 있다 | `code`로 분기하고 `subject`가 가리키는 연결된 이웃을 고친다 |
| `supportedFixes` | 진단 안 | 문장 목록(아래 "supportedFixes 값"). 닫힌 집합이 아니고, 빈 배열일 수 있다 | R-02 |
| `nextAction`(finalize) | 요약 | `{action:"edit-in-place", candidate:<초안 절대경로>, constraint:<문장>, then:"finalize-once"}`. `status:"fail"`이고 `failedStage:"validate"`일 때만 | R-04 |
| `nextAction`(validate) | `validate <type> <input> --json`이 **통과**했을 때의 영수증 | `{command:"finalize", arguments:[<type>, <후보 절대경로>, "<output.html>", "--quality", <q>, [--repo-root, <root>]?, "--candidate-sha256", <sha256>, "--json"]}`. 같은 영수증에 `candidate:{path,sha256,bytes}`, `candidateFrozen:true` | R-05 |
| `visualReviewRecommendation` / `layoutReviewRecommendation` | 통과한 요약 | finalize R-28 | R-20, R-21 |
| 종료 코드 | 프로세스 | 0 통과 / 1 실패 / 2 skipped·인자 오류(finalize R-05) | 2(skipped)는 환경 문제 신호(R-18) |

`repairable` 같은 필드는 **없다**. 수리 가능성은 신호로만 읽는다: `nextAction` 있음 = 초안을 제자리 편집하라는 코드의 신호, `status:"skipped"` 또는 `severity:"warning"` = 환경 문제, 나머지 실패(`failedStage`가 `deliver`·`check`·`browser-check`·`finalize`)는 `nextAction` 없이 진단·`supportedFixes`만 준다(R-06).

**`nextAction.arguments`와 `<output.html>`**: 문자열 배열이고 첫 요소가 하위 명령(`finalize`)이 아니라 `<type>`이다(`command`가 따로 있다). 실행할 때 `<output.html>` 한 칸만 실제 출력 경로로 바꾼다. `--repo-root` 쌍은 validate 때 `--repo-root`를 줬을 때만 들어간다. 같은 영수증의 `candidateFrozen:true`는 "이 해시의 바이트로 더 진행하라"는 뜻이고 코드는 이 값을 이후 어디서도 강제하지 않는다. 강제하는 것은 `--candidate-sha256`뿐이다(finalize R-20).

**supportedFixes 값**: 문장 하나가 한 수리 방향이다. **중앙 enum이 없다.** 정적 표는 세 곳뿐이고(`COMPOSITION_FIXES` 7개 code, `CHECK_FIXES` 4개 검사, 스키마 keyword 표) 나머지는 각 렌더러·게이트가 진단을 만들 때 문장을 직접 쓴다(약 45개 파일). 종류는 아래와 같다. 관찰 열은 DEMO 실행에서 실제로 본 것이다.

| 종류 | 예(code → 문장 형태) | 의미·주의 |
|---|---|---|
| A 고정 문구 | `schema/required` → `add required property "<이름>"`, `schema/additionalProperties` → `remove unsupported property "<이름>"`, `schema/type` → `use "<type>" at <경로>`, `schema/enum` → `choose one of the allowed values`, `schema/maxLength` → `provide at most <n> character(s)` | keyword별 문구 표는 input-validation R-05. 값(허용 목록·원래 이름)은 문장에 없고 `evidence.expected`에 있다 |
| B 계산된 구체 지시 | `architecture/unknown-endpoint`·`workflow/unknown-edge-endpoint`·`sequence/…`·`dataflow/…` → `set /<컬렉션>/<i>/to to verified node id "<id>"`(후보 최대 3개, lifecycle은 `state id`), `layout/component-overlap` → `move component "<id>" pos to [x, y] (right of "<다른 id>")` / `or move … (below)` / `or shrink …`, `layout/component-out-of-bounds` → `set meta.viewBox to at least [W, H]` 또는 `move component "<id>" right by Npx`, `composition/label-gap` → `increase the clear gap … to at least Npx`, `dataflow/node-below-area` → `lower yOffset on node "<id>"`, `architecture/component-label-overflow` → `widen component "<id>" to at least Npx` | 좌표·수치가 렌더러의 측정으로 채워진다. 적용하면 같은 진단은 사라지지만 다른 진단이 드러날 수 있다(T-02: 겹침 해소 → 연결 길이 8px → 라벨이 컴포넌트와 겹침) |
| C 조건부 문장 | `if the authored via/route/channelX/channelY controls exist and are not required by the user, remove them to let the renderer re-plan; otherwise preserve that intent and adjust …` | `COMPOSITION_FIXES`의 7개 code(`composition/proper-crossing`, `ambiguous-corridor`, `container-border-run`, `label-route-clearance`, `label-canvas-containment`, `micro-segment`, `short-interior-segment`)와 geometry.mjs의 `clean-flow/*`. 사용자가 고정한 경로면 보존하고 생성된 경로면 지우라는 두 갈래가 한 문장에 들어 있다 |
| D 측정 서술(긴 문장) | `composition/viewport-height` → "…ratio 0.89 …is below the 1.55 wide ratio … compact vertical spacing so meta.viewBox height is at most 529 …, or spread content sideways so the width is at least 1426 …", `composition/desktop-readability` → "…complete viewBox width is at most 1085px (current 1440px …)", `viewer/viewport-overflow` → 페이지 높이 분해("12px body padding + 52px header + … = 1967px against 900px") + 점검 지시 | 수치가 계산돼 들어간다(`compositionFixes`, `verticalBudgetFixes`). 서로 모순될 수 있다(T-06) |
| E 환경·재시도 | `set ARCHIFY_CHROME to a Chrome/Chromium executable … and rerun browser-check`, `restore the delivered artifact or rerun deliver to create a matching artifact and provenance pair`, `move the conflicting file aside, or choose a separate --out-dir, then rerun browser-check`, `finish other delivery attempts for this output, then rerun finalize from the frozen candidate` | 초안은 고치지 않는다 |
| F 비어 있음 | `layout/constraint`(기본 code), `relationship/duplicate-id`, `schema/oneOf`, `workflow/explicit-pin-conflict` | 수리 지시가 `message` 안에만 있을 수 있다. 예: `Label "approved build" overlaps component "container" — … Suggested fix: set labelAt [562, 252]`. 그래서 `nextAction.constraint`가 "apply each diagnostic's supportedFixes, **or the fix its message names**"라고 쓴다 |
| G explainer | `Use a valid form, for example: [Evidence](source:known-source)` | explainer.md 소관 |
| H finalize 합성 | `restore the frozen candidate, or finalize the edited candidate as a new attempt`, `use the compact finalize summary to repair the named subject in place, then rerun finalize once` | finalize C-05·C-06 |

**finalize가 `viewer/viewport-overflow`를 합칠 때 문장을 잃는다**: 뷰포트 여러 개가 넘치면 finalize는 하나로 합치고 `supportedFixes`를 "`contain the rendered layout within 1440x900 (smallest reported viewport), then rerun browser-check`" 한 문장으로 바꾼다(finalize R-18). 페이지 높이 분해·워크플로 레인 점검 지시는 `<stem>.browser-check.json`의 진단에만 남는다(T-07).

**수리 한도 5종**(어디에 적혀 있나; 모두 지시문이고 영수증에 카운터 필드는 없다)

| 한도 | 내용 | 출처 | 코드가 세나 |
|---|---|---|---|
| L1 집중 수리 | 지속되는 문제 하나(= `code`·`subject`·`stage`·`evidence`가 같은 것)당 **집중 수리 2회**, 그래도 남으면 측정 기하·관련 계약을 확인하고 **증거에 근거한 재시도 1회**, 그다음 구체적 격차 보고. 새로 드러난 문제는 자기 시퀀스를 새로 시작 | delivery-contract.md:11 | 아니오 |
| L2 시각 검토 보정 | `correction_rounds`는 0·1·2, "never exceed two focused correction rounds". 요청 없으면 0 | delivery-contract.md:633-635, 654 | 아니오. `finalize`는 `visualReview`에 항상 `"not-requested"`만 쓴다 |
| L3 위치 수리(resolvedCrossovers) | 위치·크기만 바꾸는 **한 번의 편집** + 새 `--out-dir`로 재실행 1회. 실패·교차 증가·굴곡 증가면 사본을 복원해 또 다른 새 `--out-dir`로 1회. **두 번째 배치 라운드 금지** | SKILL.md:93 | 아니오 |
| L4 시퀀스 폭 | `meta.column_fit:"spread"` 변경은 허가될 때만, 완전한 `finalize` **1회**(`--out-dir <folder>/width-review`), 실패하면 저장한 후보를 복원해 `<folder>/width-restore`로 finalize, 더 반복하지 않고 제안을 보고 | delivery-contract.md:495, finalize.mjs:706 | 아니오 |
| L5 아키텍처 레이아웃 | 사람 눈 검토에서 얽힘이 발견된 뒤 한 번의 연결된 장면 수리 + `visual-check`. "A bounded second repair may address a remaining specific defect", 그래도 실패면 후보 유지·격차 보고, 맹목적 좌표 수정 금지. `--layout-json`은 한 번 | architecture-layout-repair.md:13, 18 | 아니오 |

L1 총 시도 수는 지시문 문장의 산술로 "최대 3회"(2 + 1)이지만 문장이 합계를 말하지는 않는다(추론). SKILL.md:49는 "including its repair limit"라고만 쓰고 숫자는 delivery-contract.md에만 있다.

**출력 경로 재사용·`--out-dir` 규칙**(코드가 만드는 충돌 + 지시문이 정한 회피)

| 상황 | 코드가 하는 일 | 지시문 규칙 |
|---|---|---|
| 같은 HTML 경로에 browser-check까지 간 적이 있고 초안을 바꿔 다시 finalize | deliver·check는 통과(HTML 교체), 옛 `<stem>.browser-check.json`이 옛 HTML 해시에 묶여 있어 browser-check가 `viewer/evidence-path-conflict`(`evidence.reason.code:"ownership-artifact-mismatch"`)로 실패. 옛 영수증은 그대로(finalize R-23, verification-gates R-35) | 이미 증거가 있는 경로면 **고친 후보마다 새 `--out-dir`**(`<folder>/review-<n>` 또는 `<stem>.review-<revision>`)을 `finalize`와 `visual-check` 모두에 준다. 같은 바이트 재시도는 같은 폴더를 유지. HTML 경로는 안정적으로 유지 |
| `--out-dir`이 옮기는 것 | browser-check 영수증, 기본 finalize 영수증·요약만. HTML과 `<stem>.delivery.json`은 요청한 출력 경로에 그대로 | 증거 폴더는 HTML의 보관소가 아니다. HTML만 복사해도 영수증이 다시 묶이지 않는다. 이력이 필요하면 후보·산출물을 따로 보관 |
| 이전 검증이 HTML·증거를 만들지 못한 실패 | 해당 없음 | 새 폴더 불필요. 알 수 없는 증거를 지워서 재시도를 통과시키지 않는다 |
| 옛 증거 | 새 HTML 바이트에 묶이지 않은 채 남는다 | 변경된 HTML의 증거로 쓰지 않는다 |

**실패 단계별 권장 수리 행동**(`failedStage` 또는 시작 전 실패 기준)

| 단계 | 대표 진단 code | 코드가 주는 신호 | 초안을 고치나 | 권장 행동(근거) | 관찰 |
|---|---|---|---|---|---|
| 시작 전(인자·explainer prepare·`--candidate-sha256` 불일치) | `cli/*`, `output/*`, `explainer/*`, `finalize/candidate-changed` | 영수증 없음, `gates` 전부 `not-run`, `failedStage` 없음(finalize R-06) | explainer면 마크다운을 고친다. 해시 불일치면 해시를 뺀다 | explainer: 진단의 `line`·`supportedFixes` 예시대로 고쳐 재실행. 해시: "Omit an earlier `--candidate-sha256` after editing"(delivery-contract.md:11) | T-08, T-11 |
| validate (입력·렌더·deliver 안의 check) | `schema/*`, `layout/*`, `architecture/unknown-endpoint`, `repository-evidence/*`, `composition/*`, `clean-flow/*` | `nextAction` 있음. `supportedFixes` 종류 A~C·F | **예**, 제자리 편집 | 수리 순서(R-13)로 연결된 이웃만. 근거 오류는 `evidence.lineCount` 등으로 줄·경로를 고치거나 `--repo-root`를 맞춘다 | T-01~T-03, T-12 |
| deliver (showcase 경고, 비입력 실패) | `composition/viewport-height`(경고→오류), `delivery/concurrent-attempt`, `delivery/lock-stale` 등 | `nextAction` 없음. 경고 실패는 이미 HTML이 교체됨(finalize R-16, R-22) | 경고는 예(종류 D 문장), 잠금·커밋류는 아니오 | 경고: 진단 문장의 계산값(최대 viewBox 높이·최소 폭)으로 구성 변경. 잠금류: "finish other delivery attempts … rerun finalize from the frozen candidate"(종류 E) | T-06 |
| check | `delivery/provenance-mismatch`, `delivery/provenance-failed`, `artifact/*` | `nextAction` 없음. HTML·provenance는 deliver가 만든 그대로 | 아니오(HTML을 손으로 고치지 않는다) | "restore the delivered artifact or rerun deliver to create a matching artifact and provenance pair" | T-10 |
| browser-check: skipped | `viewer/chrome-unavailable`(warning) | 종료 2, `status:"skipped"`, `nextAction` 없음 | 아니오 | `ARCHIFY_CHROME` 설정 후 재실행. 초안·산출물은 정상 | T-09 |
| browser-check: 소유권 충돌 | `viewer/evidence-path-conflict` | `failedStage:"browser-check"`, `ran:false` | 아니오 | 새 `--out-dir`로 같은 후보를 다시 finalize | T-04 |
| browser-check: 넘침·가독성 | `viewer/viewport-overflow`, `viewer/projected-text-readability`, `viewer/chrome-*-clearance`, `viewer/diagram-clipped` | `nextAction` 없음. 합쳐진 한 문장 fix(위 "합칠 때 문장을 잃는다") | 예, 단 `validate`가 아니라 `nextAction`이 없다 | `<stem>.browser-check.json`의 전체 fix와 `evidence`(`workflowLanes`, `pageComposition`)를 읽고 워크플로 viewport 수리(R-23)·구성 변경 후 **새 HTML**로 재측정 | T-07 |
| finalize(최종 인계) | `finalize/candidate-changed`, `finalize/final-artifact-mismatch` | `failedStage:"finalize"`, 네 gate는 `pass` | 초안이 바뀌었으면 복원하거나 새 시도로 | "restore the frozen candidate, or finalize the edited candidate as a new attempt" | 코드 확인 |

**흔한 진단 code**(실험: 아래 "관찰" 설명)

| 순위 | code | 관찰 횟수(변이 204건, 진단 308개) | 수리 방법 |
|---|---|---|---|
| 1 | `layout/constraint` | 78 (전부 `supportedFixes` 비어 있음) | 특정 code의 짝 진단이거나(예: `unknown-endpoint`마다 하나) 단독(라벨이 노드보다 넓음, 연결 길이 최소 24px 미만, 라벨이 컴포넌트와 겹침). `message`에 수리 문장이 있다 |
| 2 | `schema/additionalProperties` | 36 | `remove unsupported property "<이름>"` |
| 3 | `schema/type` | 32 | `use "<type>" at <경로>` |
| 4 | `composition/label-canvas-containment` | 28 (sequence 9, dataflow 14, architecture 4, workflow 1) | 라벨 `labelAt/labelDx/labelDy` 조정, 문구 단축, `meta.viewBox` 확대. 생성된 경로면 지우고 재계획 |
| 5 | `relationship/duplicate-id` | 21 (fix 없음) | 중복 관계 `id`를 고유하게 |
| 6 | `schema/required` | 19 | `add required property "<이름>"` |
| 7 | `dataflow/node-below-area` | 12 | `lower yOffset on node "<id>"` |
| 8 | `layout/component-out-of-bounds` | 11 | `set meta.viewBox to at least [W,H]` 또는 `move … right by Npx` |
| 9 | `composition/label-route-clearance` | 9 | 종류 C 문장 |
| 10 | `layout/component-overlap` | 7 | `move component "<id>" pos to [x, y]` |
| 공동 11 | `architecture/unknown-endpoint`, `layout/route-out-of-bounds` | 각 6 | 후보 id 중 하나를 `set …/to`; 경로를 캔버스 안으로 |

이 표의 횟수는 **내가 만든 변이 8종**(키 삭제·모르는 키 추가·타입 변경·위치 흔들기·viewBox 축소·끝점 오타·긴 라벨·중복 id)의 결과이고 실사용 빈도가 아니다(1.4 확인 한계 5, 실사용 빈도는 미확인). 변이 없는 기존 예제 23개를 showcase `finalize`에 돌리면 **3개**(`async-job-roundtrip.sequence`, `release-delivery.workflow`, `event-stream.dataflow`)가 `composition/viewport-height`(deliver 단계)로 실패했고 2개(`web-app.architecture`, `product-analytics.dataflow`)는 통과하며 `visualReviewRecommendation`이 붙었다(DEMO/out/scan-summary.txt). 변이로는 나오지 않고 다른 경로에서만 본 code: `composition/viewport-height`, `viewer/viewport-overflow`(standard로 통과한 workflow), `viewer/evidence-path-conflict`, `viewer/chrome-unavailable`, `delivery/provenance-mismatch`, `repository-evidence/line-out-of-range`·`root-required`, `explainer/unresolved-reference`, `finalize/candidate-changed`, `composition/proper-crossing`, `composition/desktop-readability`.

### 1.4 행동 규칙과 남은 질문 [필수]

표기: `[코드]`는 코드가 만드는 신호·동작, `[지시문]`은 SKILL.md·references가 에이전트에게 요구하는 행동이다. `[지시문]` 규칙의 검증 수준은 지시문 원문을 읽은 `코드 확인(지시문)`이고, 에이전트가 실제로 따르는지는 모두 `미확인`이다(아래 확인 한계 1). 코드 신호를 실행으로 확인한 경우 그 신호의 수준을 적는다.

**코드가 내는 신호**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 `[코드]` | 어느 단계든 비정상 종료 | finalize는 첫 비통과 단계에서 멈추고 요약에 `status`·`failedStage`·`gates`·`diagnostics`를 쓴다(finalize R-17~R-18). 수리 루프의 입력은 요약(stdout `--json` 또는 `evidence.summaryReceipt`). 텍스트 모드 stdout은 4줄뿐이고 진단을 싣지 않는다 | 실행 확인(T-01~T-09) |
| R-02 `[코드]` | `supportedFixes` 해석 | 문장 목록이며 닫힌 값 집합이 없다(1.3 종류 A~H). 정규화는 trim·빈 문자열 제거·중복 제거(input-validation 1.3). **비어 있을 수 있다**: 변이 204건에서 나온 진단 308개 중 101개가 비어 있었고 전부 `layout/constraint`(78)·`relationship/duplicate-id`(21)·`schema/oneOf`·`workflow/explicit-pin-conflict`이다. 이때 수리 방향은 `message`(예: `Suggested fix: set labelAt [x, y]`)나 `evidence`(예: `lineCount`)에 있다. `nextAction.constraint`는 이를 "or the fix its message names"로 허용한다 | 실행 확인(T-02, T-13), `constraint` 문장은 코드 확인 |
| R-03 `[코드]` | `supportedFixes`의 값 | 문장의 종류·예·주의는 1.3 표. 값을 정하는 곳: 정적 표 `COMPOSITION_FIXES`(7 code)·`CHECK_FIXES`(4 검사)·스키마 keyword 표, 나머지는 각 렌더러·게이트가 진단 생성 때 쓴다. 측정 수치가 계산돼 들어가는 문장(B·D)은 입력마다 달라진다 | 코드 확인(C-02, C-04), 실행 확인(T-13의 문장 수집) |
| R-04 `[코드]` | finalize 요약의 `nextAction` | `ok:false`·`status:"fail"`·`failedStage:"validate"`일 때만 `{action:"edit-in-place", candidate, constraint, then:"finalize-once"}`. `constraint`는 type이 architecture이고 진단 code 중 하나가 `ROUTE_DIAGNOSTIC`(`^(clean-flow/\|composition/(proper-crossing\|ambiguous-corridor\|border-run\|container-border-run\|excessive-route-detour\|route-rhythm\|arrowhead-collision))`)이면 레이아웃 수리 문장("…Use references/architecture-layout-repair.md to choose a local repair or connected-scene reflow; edit the existing candidate."), 아니면 "Preserve unaffected semantics and geometry; apply each diagnostic's supportedFixes, or the fix its message names, and do not replace the whole candidate." `deliver` 이후 실패·skipped에는 없다 | 실행 확인(둘째 문장: T-01·T-02, 첫째: T-12, 부재: T-04·T-06·T-07·T-09) |
| R-05 `[코드]` | `validate <type> <input> --json`이 통과 | 영수증에 `candidate:{path,sha256,bytes}`, `candidateFrozen:true`, `nextAction:{command:"finalize", arguments:[type, 후보 절대경로, "<output.html>", "--quality", <q>, (--repo-root, root)?, "--candidate-sha256", sha, "--json"]}`가 들어간다. `<q>`는 `--quality` 인자, 없으면 결과 `composition.profile`, 그것도 없으면 `standard`. 이 인자를 `<output.html>`만 바꿔 실행하면 통과한다. 실패한 validate에는 `nextAction`이 없다 | 실행 확인(T-11), 실패 시 부재는 코드 확인 |
| R-06 `[코드]` | 수리 가능성·`repairable` 필드 | 그런 필드는 어디에도 없다(`repairable`·`retryable` grep 0건, 영수증 필드 목록에 없음). 코드가 주는 간접 신호는 `nextAction` 유무(= `failedStage:"validate"`)와 `status:"skipped"`·`severity:"warning"`뿐이다 | 코드 확인(grep) |
| R-07 `[코드]` | 수리 횟수·한도 | **코드는 수리 횟수를 세지 않는다.** `repairLimit`·`repairCount`·`correction_rounds` 등은 마크다운에만 있고(`correction_rounds`는 delivery-contract.md:633-654), `finalize.mjs`·`archify.mjs`에 카운터·상한·시도 번호가 없다. 같은 후보를 몇 번 돌려도 영수증 모양은 같다 | 코드 확인(grep: `bin/`, `renderers/`, `scripts/`에서 repair 관련 카운터 없음) |
| R-08 `[코드]` | 출력 경로에 이전 browser-check 영수증이 있고 HTML이 바뀜 | browser-check가 `viewer/evidence-path-conflict`로 실패한다. `failedStage:"browser-check"`, deliver·check는 `pass`, HTML은 새 것으로 이미 교체, 옛 영수증은 그대로, `browserCheck:{requested:true, ran:false}`. 진단 `message`는 "will not replace the existing **unowned** evidence path"라고 하지만 `evidence.reason.code`는 `ownership-artifact-mismatch`다. `nextAction`은 없다 | 실행 확인(T-04) |
| R-09 `[코드]` | `--candidate-sha256` | 초안 해시가 다르면 단계 실행·영수증 없이 시작 전 실패(`finalize/candidate-changed`, 종료 1, `gates` 전부 `not-run`). 수정한 후보에 옛 해시를 주면 항상 이렇게 된다. 해시를 빼면 통과 | 실행 확인(T-11) |
| R-10 `[코드]` | 통과한 실행 | 요약에 `visualReviewRecommendation`(finalize R-28: `resolvedCrossovers`·`routesOverSuggestedBends`·`routesOverSuggestedStretch` 중 양수가 있을 때)이나 `layoutReviewRecommendation`(`inspect-leading-space`: `emptyTopRatio`가 큰 경우, `inspect-sequence-width`)이 붙을 수 있고, 종료 코드·gate는 통과 그대로다. architecture가 아니면 `hints`가 없고 `repair`는 "Advisory only: this mode places or routes these relationships itself. Report them; do not remove relationships or meaning to reduce crossings."이다 | 실행 확인(T-04 `resolvedCrossovers:1`+hints, T-05 `inspect-leading-space`, 비-architecture advisory는 `product-analytics.dataflow` scan). `inspect-sequence-width`는 만들지 못해 코드 확인 |
| R-11 `[코드]` | 요약에 진단이 8개 초과 | `diagnosticSummary.truncated:true`, `omittedByCode`에 생략 개수(finalize R-27). 전체는 `evidence.receipt`(전체 영수증)에 있다. 합쳐진 `viewer/viewport-overflow`의 구체 fix는 요약이 아니라 `<stem>.browser-check.json`에만 있다 | 실행 확인(T-07) |

**지시문이 요구하는 행동**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태(요구되는 행동) | 검증 수준 |
|---|---|---|---|
| R-12 `[지시문]` | 비정상 종료 | "A non-zero exit is never success." 압축 stdout 또는 `evidence.summaryReceipt`를 읽고 delivery-contract의 수리 절을 따른다. 전체 사이드카는 요약에 증거가 모자랄 때만 읽는다. 별도 `validate`·`check` 같은 단독 명령은 별도 요청이나 집중 진단에서만 쓴다. 업데이트 안내(`update.noticeRequired`)는 게이트가 실패해도 최종 응답에 한 번 유지한다(SKILL.md:49-53) | 코드 확인(지시문) |
| R-13 `[지시문]` | 수리 순서 | ① `meta.quality_profile`·스키마 오류 → ② 노드 겹침·범위 밖 → ③ edge-through-node·끝점 방향 → ④ 교차·모호한 복도·테두리 따라가기·과한 우회·경로 리듬 → ⑤ 라벨-노드, 라벨-라벨, 라벨-경로 간격 → ⑥ 캔버스 밖 라벨(`labelAt`/`labelDx`/`labelDy`/`labelSegment` 이동 또는 `meta.viewBox` 확대. 제안된 `labelDx/labelDy`는 기존 값에 더하지 않고 **대체**). 진단은 `code`·정확한 `subject`·측정 `evidence`·`supportedFixes`로 소비하고, 진단이 `labelAt`을 주면 다른 오프셋을 추정하지 않는다(authoring-contract.md:269-277) | 코드 확인(지시문) |
| R-14 `[지시문]` | 수리 시 보존 | 요청된 의미, 의미 있는 라벨, 소스 근거(`sources`), 고정·합의된 토폴로지를 보존한다. 진단이 가리킨 **연결된 이웃**만 편집하고 이미 잘 읽히는 기하는 건드리지 않는다. 막힌 주 경로는 무관한 라벨을 밀지 말고 다시 흘려 놓는다. 전체 후보를 새로 쓰지 않는다(`nextAction.constraint`). 위치 수리(R-22)는 노드 위치·크기만 바꾸고 모든 노드·관계(`from`·`to` 포함)·라벨·소스는 그대로. 사용자가 고정한 기하는 보존하고 에이전트가 만든 위치·경로 제어는 바꿀 수 있다. 노드를 옮긴 뒤에는 낡은 생성 경로 override를 지워 자동 라우팅이 새 배치를 쓰게 한다. 외부 행위자는 경계 사각형(패딩 포함) 밖에 둔다. 의미를 지우거나 관계를 빼서 교차를 줄이지 않는다. 넘침은 숨기거나 클리핑하거나 글자를 줄여서 통과시키지 않고 진짜 중복인 내용만 제거·간격 압축한다 | 코드 확인(지시문: delivery-contract.md:7·9·616, architecture-layout-repair.md:7·15) |
| R-15 `[지시문]` | 수리 한도 L1 | 지속되는 문제(code·subject·stage·evidence 동일)마다 집중 수리 2회, 남으면 측정 기하·관련 계약 확인 후 증거 기반 재시도 1회, 그다음 구체적 격차 보고. 새로 드러난 문제는 새 시퀀스. 진단은 code·subject·stage·evidence로 비교하며 **오류 개수가 줄었다는 것만으로** 진전이라 보지 않는다. 최상위 안전장치: 집중 수리 뒤에도 진단이 실행 불가면 그때 Archify 구현을 본다(SKILL.md:55) | 코드 확인(지시문), 준수 미확인 |
| R-16 `[지시문]` | 재실행 인자 | 수리 후 **완전한** `finalize` 명령을 `--quality showcase`(+ 저장소 기반이면 `--repo-root`)로 다시 돌린다. 단 SKILL.md:44는 `meta.quality_profile`과 같은 `--quality`를 주라고 하고 밀집 ERD 첫 패스는 `standard`를 허용한다(2.1). 이전 `--candidate-sha256`은 뺀다(R-09). `validate`·`check`·`browser-check`를 따로 돌려 통과를 대신하지 않는다 | 코드 확인(지시문: delivery-contract.md:11, SKILL.md:44, 49) |
| R-17 `[지시문]` | 출력 경로 재사용 | R-08의 충돌을 피하려고, 이미 다른 후보의 browser 증거가 있는 출력 경로에는 **후보가 바뀔 때마다 새 `--out-dir`**(`<folder>/review-<n>` 또는 `<output-stem>.review-<revision>`)을 `finalize`와 `visual-check` 모두에 준다. 같은 바이트의 재시도는 같은 폴더. HTML 경로는 고정. 기존 증거는 지우지 않는다 | 코드 확인(지시문: SKILL.md:49, delivery-contract.md:563-574) |
| R-18 `[지시문]` | 환경·증거 실패(skipped, 잠금, 복구) | 초안을 고치지 않는다. 냉동 후보(`validate`가 통과시킨 바이트)로 같은 명령을 다시 돌려 "later environmental or evidence failures against those frozen bytes" 재시도. 고칠 측정 근거가 생기면 새 후보이며 옛 해시 없이 완전한 `finalize`를 다시 한다 | 코드 확인(지시문: delivery-contract.md:13) |
| R-19 `[지시문]` | 연결된 레이아웃 수리(여러 경로가 얽힘) | 사람 눈 검토에서 여러 경로가 얽혔을 때만: 기존 후보를 대상으로 ① 영향받는 관계·끝점을 JSON에서 추적하고 독자의 주 경로를 기존 간선의 순서 목록으로 쓴다(주 경로의 이웃 쌍은 실제 설명하는 관계여야 하고 나머지는 실제 소유자 옆 가지에 둔다) ② 연결된 주 경로 이웃을 읽는 순서로 배치하고 공유 상태는 읽고 쓰는 쪽 사이(필요하면 인접 행)에, 피드백 순환은 열린 사각형 둘레에 간선 순서대로 ③ 새 배치에서 자동 끝점을 유지하고 측면은 꼭 필요한 가지·복귀에만 제한, 상세 `via`·라벨 좌표는 남은 측정 결함에만 ④ `composition/label-gap`이 최소 간격을 보고하면 그 간격을 키우거나 연결 그룹을 다른 줄로 옮긴다. 하나의 일관된 수리 후 완전한 `finalize` **1회**, 이어 성공한 산출물에 `visual-check`(L5). `--layout-json`은 compact 영수증·스크린샷으로 모자랄 때만 **한 번** | 코드 확인(지시문: architecture-layout-repair.md 1-18), 실행 확인은 R-22의 일부만 |
| R-20 `[지시문]` | `resolvedCrossovers` 위치 수리의 "한 번" 규칙 | 통과한 Architecture 영수증이 `visualReviewRecommendation.signals.resolvedCrossovers`를 보고하면: 후보를 **사본으로 따로 저장**하고 hints를 **한 번의 편집**으로 적용(노드 위치·크기만). `finalize`를 새 `--out-dir <folder>/review-2`로 **한 번** 다시. 그 실행이 실패하거나 교차가 더 많거나 같은 교차인데 `signals.routesOverSuggestedBends`가 늘면 **사본을 복원해** `--out-dir <folder>/review-3`로 finalize. **두 번째 배치 라운드를 시작하지 않는다.** 굴곡 hint만 있는 경우는 선택(SKILL.md:93). `visualReviewRecommendation`은 자문이고 시각 품질을 주장하려면 캡처를 직접 본다 | 코드 확인(지시문), 위치 수리 한 라운드는 실행 확인(T-04), 복원 분기는 실행하지 않음(복원은 단순한 finalize 재실행) |
| R-21 `[지시문]` | `layoutReviewRecommendation` | `inspect-leading-space`: 위쪽 여백이 의도인지 확인, 아니면 연결된 장면을 캔버스 원점 쪽으로 옮기고 경계·라벨·복귀 경로 공간은 남긴 채 `finalize` 재실행, 스크린샷 불필요(finalize.mjs:693-697). `inspect-sequence-width`: 고정 기하가 의도인지 확인하고 변경이 허가될 때만 `meta.column_fit`만 `"spread"`로 바꿔 L4(delivery-contract.md:495). 어느 것도 게이트 실패·자동 변경이 아니다 | 코드 확인(지시문), `inspect-leading-space`는 실행 확인(T-05) |
| R-22 `[지시문]` | 선택 시각 검토 | 일반 생성에서는 하지 않는다("Perceptual review is optional"). 이유가 있을 때만(사용자 요청, 검토 권고, 렌더러·템플릿 변경, 새 레이아웃·브라우저 진단 의문, 샘플 감사): `visual-check`로 현재 산출물의 캡처를 만들어 이미지 읽기 도구나 사람이 확인(두 테마·READ 뷰·교차·라벨 마스크·노드/카드 맞춤·포커스/검색/패스포트 닫힘·내보내기 청결). 상태는 `visual_review: not_requested|passed|skipped (image reader unavailable)|failed` 중 하나. 이 검토는 `browser_evidence`를 바꾸지 않는다. 산출물을 보지 않고 `passed`라 하지 않는다. 검토로 후보를 바꾸면 `finalize`를 다시 돌린다. 보정은 최대 2라운드(L2). `finalize`가 자동 요약하는 `visualReview`는 항상 `"not-requested"`다(finalize R-26) | 코드 확인(지시문: delivery-contract.md:602-640) |
| R-23 `[지시문]` | 뷰포트 수리 | 데스크톱 기본 폭(1440×900, 1600×1000, 1920×1080, 2048×1320)에서 `scrollWidth ≤ innerWidth`. `viewer/viewport-overflow`에 `workflowLanes`가 있으면 소스를 바꾸기 전에 가장 높은 프레임·노드 span을 확인하고 `validate workflow <source> --layout-json`으로 프레임을 소스 레인·`col`·`yOffset`에 대응시킨다. 같은 마지막 논리 열에 단계가 몰려 `yOffset`이 큰지 본다. 소유권·명시 기하가 허락하면 단계를 논리 열·의미 있는 레인에 재분배하되 주 경로 단조성은 유지. 소유권·절대 pin이 막으면 레인을 합치거나 pin을 자동으로 옮기지 말고 제약을 보고한다. 변경된 JSON을 validate·deliver한 새 HTML로 브라우저 검사를 다시 하고 첫 화면을 확인한다. 뷰포트 수리가 새 경로 충돌을 일으키면 측정된 레이아웃을 복원하고 남은 캔버스·텍스트 제약을 따로 해결한다. `meta.viewBox`를 생략할 수 있는 건 architecture와 readable-v2 workflow(`composition/viewport-height`의 fix 문장) | 코드 확인(지시문: authoring-contract.md:297-318, delivery-contract.md:9·616) |
| R-24 `[지시문]` | 보고 | 한도에 걸리면 후보를 유지하고 구체적 격차를 보고한다(수리 성공으로 세지 않는다). 확인 주장은 자동화 수준을 한정한다(artifact checks / browser evidence / captures / perceptual review 구분). 사용자에게 주는 최종 응답에는 수리 라운드·해시·품질 프로파일·검사 목록을 되풀이하지 않고(SKILL.md:131) "자동 검사 통과, 시각 검토 안 함" 같은 한 줄로 답한다. 핸드오프 영수증 요약에는 `diagram_type`, `output`, `specification_sha256`, `artifact_sha256`, `validation`, `browser_evidence`, `visual_review`, `correction_rounds`를 쓴다(요청된 진단 핸드오프에서만) | 코드 확인(지시문) |

- 불변식:
  - 코드는 수리를 하지 않고 입력(진단·fix·`nextAction`)만 낸다. 초안을 고치는 주체는 에이전트다. `finalize`는 초안·HTML·provenance를 되돌리지 않는다(finalize R-22).
  - 같은 후보 바이트·같은 출력 경로·같은 폴더에서 `finalize`를 되풀이해도 영수증에 시도 번호는 없다(R-07).
  - `nextAction`은 `validate` 단계 실패에서만 나온다. 다른 단계 실패는 진단의 `supportedFixes`와 이 스펙의 단계 표가 전부다.
- 미결정: 없음.
- 확인 한계: (1) LLM이 위 `[지시문]`을 실제로 따르는지, 따랐을 때 결과 품질은 **미확인**이다. DEMO의 수리는 실험자가 `supportedFixes`·`message`를 읽고 적용한 것이고(일부는 스크립트가 문장을 파싱해 적용) "에이전트 수리 사례"가 아니라 "코드 신호만으로 한 번에 닫히는 수리 사례"다. (2) 사람 눈 검토(`visual-check` 캡처 읽기)와 `visual_review` 상태는 실행하지 않았다. (3) `inspect-sequence-width`, `finalize/final-artifact-mismatch`·`delivery-type-mismatch`·`artifact-binding-mismatch` 등 일부 합성·바인딩 진단은 만들지 못해 코드로만 확인했다(finalize 스펙과 같음). (4) `supportedFixes` 문장은 약 45개 파일에 흩어져 있고 이 스펙은 실행에서 수집한 것과 정적 표만 다룬다. 모든 렌더러·타입의 문장을 열거하지 않았다. (5) 변이 204건의 code 빈도는 변이 선택에 종속적이다. (6) 실행은 macOS·Node v26.10.0·설치본·`ARCHIFY_UPDATE_CHECK_DISABLED=1`.

### 1.5 필수 코드 참조 [필수]

Apache-2.0(레포 `LICENSE`, 인용 가능; overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/bin/finalize.mjs:563-584` `placementHints`·`ROUTE_DIAGNOSTIC` | 위치 hint 문장 생성(교차·우회·붐비는 변)과 레이아웃 수리를 가리키는 code 정규식 | R-04, R-10 |
| C-02 | `archify/bin/finalize.mjs:660-718` `compactFinalizeReceipt` 후반 | `visualReviewRecommendation`·`layoutReviewRecommendation`·`nextAction`의 조건·문장 원문(finalize C-09의 부분집합, 문장 원문은 이 범위를 그대로) | R-04, R-10, R-20, R-21 |
| C-03 | `archify/bin/archify.mjs:2697-2785` `COMPOSITION_CHECKS`·`CHECK_FIXES`·`COMPOSITION_FIXES`·`compositionFixes` | 검사 단계 진단의 정적 fix 표 7+4개와 `composition/viewport-height`·`composition/desktop-readability`의 계산된 fix 문장 | R-03 |
| C-04 | `archify/bin/archify.mjs:7140-7165` | validate 통과 영수증의 `candidate`·`candidateFrozen`·`nextAction.arguments` 구성 | R-05 |
| C-05 | `archify/renderers/architecture/render-architecture.mjs:800-824` | 끝점 오타에 대해 후보 id(최대 3) `set /connections/<i>/<field> to verified node id "<id>"` 생성과 짝 `layout/constraint` | R-02, R-03 |
| C-06 | `archify/bin/visual-check.mjs:2150-2252` `verticalBudgetFixes`·`observationDiagnostics` | `viewer/viewport-overflow` 진단의 증거 필드와 fix 문장(페이지 높이 분해, 워크플로 레인 점검 지시) | R-03, R-23 |
| C-07 | `archify/bin/finalize.mjs:405-425` `consolidateDiagnostics`(overflow 합치기) | 여러 뷰포트 overflow를 한 진단·한 문장으로 합침(finalize C-06의 일부) | R-11 |
| C-08 | `archify/bin/finalize.mjs:1030-1045` | 최종 인계의 `finalize/candidate-changed`와 그 fix 문장 | R-09 |

범위 안 프로젝트 내부 helper: `identity`(finalize C-03), `artifactIdentity`는 "`{path, sha256, bytes}`" 신원으로 풀었다. 지시문 규칙은 코드가 아니므로 C-ID가 아니라 R-ID와 2.1의 원문 위치로 둔다.

### 1.6 수락 사례 [필수]

출처: 모두 **원본 실행 관찰**(설치본, 2026-11-02). 스크립트 [run-cases.sh](../../../artifacts/archify/spec-demos/repair-loop/run-cases.sh) → 출력 [out/](../../../artifacts/archify/spec-demos/repair-loop/out/)(`<사례>.<단계>.{stdout,stderr,exit}`, 영수증 사본, 요약 [cases-digest.txt](../../../artifacts/archify/spec-demos/repair-loop/out/cases-digest.txt)), 입력 [in/](../../../artifacts/archify/spec-demos/repair-loop/in/), scratch는 `work/`(실행마다 재생성). 실패 입력 생성: 변이 [sweep.py](../../../artifacts/archify/spec-demos/repair-loop/sweep.py) → [out/sweep-summary.txt](../../../artifacts/archify/spec-demos/repair-loop/out/sweep-summary.txt)·[sweep-codes.json](../../../artifacts/archify/spec-demos/repair-loop/out/sweep-codes.json), 기존 예제 전수 [scan.sh](../../../artifacts/archify/spec-demos/repair-loop/scan.sh) → [out/scan-summary.txt](../../../artifacts/archify/spec-demos/repair-loop/out/scan-summary.txt), 교차 신호가 켜지는 입력 탐색 [crossover-search.py](../../../artifacts/archify/spec-demos/repair-loop/crossover-search.py). 저장소 근거는 [input-validation/setup-repo.sh](../../../artifacts/archify/spec-demos/input-validation/setup-repo.sh)가 만든 임시 git 레포(`repo/`, 커밋 `0147eb22…`, `src/a.txt` 3줄)를 읽기만 했다. "아키텍처 샘플" = finalize 스펙의 `brand-aware-delivery.architecture.json`. 모든 실행에서 `ARCHIFY_UPDATE_CHECK_DISABLED=1`. **수리 단계(`fixed`)는 실험자가 지시문·`supportedFixes`를 흉내 내어 만든 것**이다(1.4 확인 한계 1).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-02, R-04, R-13, R-16 | **스키마 오류.** 아키텍처 샘플에서 `components[0].label` 삭제, `components[1].colour:"red"` 추가, `components[2].size[0]:"wide"`(`in/c1-schema.bad…`). 같은 폴더·같은 출력 경로로 `finalize architecture … d.html --json`. 그 뒤 fix대로 라벨 복원·`colour` 삭제·숫자 복원한 `c1-schema.fixed…`로 같은 명령 | 1차: 종료 1, `failedStage:"validate"`, `gates{validate:"fail", 나머지 "not-run"}`, 진단 3개: `schema/required`(`add required property "label"`), `schema/additionalProperties`(`remove unsupported property "colour"`), `schema/type`(`use "number" at /components/2/size/0`), `diagnosticSummary{total:3, shown:3, truncated:false}`, `nextAction.action:"edit-in-place"`, `constraint` 둘째 문장, `candidate`는 입력 절대경로. 2차: 종료 0, 4 gate `pass`, 진단 0, `nextAction` 없음 |
| T-02 | R-02, R-03, R-13, R-15 | **노드 겹침.** 아키텍처 샘플에서 `github.pos`를 `[240,270]`(claude `[220,260]`와 겹침). 3회 수리: ① 진단의 첫 fix `move component "github" pos to [366, 270] (right of "claude")` 적용(`apply_c2.py`) ② `github`를 `[402,270]`으로(최소 24px 연결 길이, 실험자가 고름) ③ 진단 `message`의 `Suggested fix: set labelAt [562, 252]`를 연결 `github-to-container`에 적용(`apply_c2_label.py`). 매번 같은 `finalize … --json` | 1차 실패: `composition/label-route-clearance`(fix 종류 C)와 `layout/component-overlap`(`move component "github" pos to [366, 270] (right of "claude")` / `or move … to [240, 336] (below)` / `or shrink "claude" or "github" …`). ①후: 새 진단 `layout/constraint` `Connection "change set" is too short (8px; minimum 24px)`, `supportedFixes:[]`. ②후: `layout/constraint` `Label "approved build" overlaps component "container" … Suggested fix: set labelAt [562, 252]`, `supportedFixes:[]`. ③후: 종료 0, 4 gate `pass`, `visualReviewRecommendation.signals{routesOverSuggestedBends:1, routesOverSuggestedStretch:1}`. 네 번의 실행에서 매번 다른 code가 드러나 L1의 "새로 드러난 문제는 새 시퀀스"에 해당한다 |
| T-03 | R-02, R-13, R-14 | **근거 줄 오류.** 임시 레포에서 `components[0].sources[0].line:5`(파일은 3줄), `--repo-root <repo>`(`in/c3-evidence.bad…`). 이어 `--repo-root` 없이, 이어 `line:3`으로 고쳐 `--repo-root`와 함께 | 1차: 종료 1, `failedStage:"validate"`, `repository-evidence/line-out-of-range`(`message` "/components/0/sources/0 requests line 5, but src/a.txt has 3 lines at revision 0147eb22…", `evidence{sourcePath:"src/a.txt", requestedLine:5, lineCount:3, revision}`, `supportedFixes:["use a line range that exists at the pinned revision"]`, `subject.nodeId:"web"`). 줄 수는 fix가 아니라 `evidence.lineCount`에 있다. `--repo-root` 없음: `repository-evidence/root-required`(`pass --repo-root with the matching local Git checkout`). 3줄: 종료 0, 4 gate `pass` |
| T-04 | R-08, R-10, R-14, R-17, R-20 | **통과 후 위치 수리 + 소유권 충돌.** 아키텍처 입력(`web-app` 변형 `c4-crossover…`, `crossover-search.py`가 찾은 것)을 showcase finalize → 통과 후 `visualReviewRecommendation`. hint대로 `cache`를 `[710,200]`(api 바로 위)으로만 옮긴 `…fixed`를 ① 같은 폴더·`--out-dir` 없이 ② `--out-dir review-2`로 | 첫 실행: 종료 0, `signals{resolvedCrossovers:1}`, `affectedRoutes.crossings[0]`(`jwt-verification` auth→api × `cache-read-through` api→cache, `sharedNode:"api"`), `hints:["auth → api and api → cache cross next to api: move node auth or cache so the two reach api from different sides …"]`, `repair`는 레이아웃 수리 문장. ①: 종료 1, deliver·check `pass`, `failedStage:"browser-check"`, `viewer/evidence-path-conflict`(`evidence.reason.code:"ownership-artifact-mismatch"`, fix `move the conflicting file aside, or choose a separate --out-dir, then rerun browser-check`), HTML은 이미 새 것. ②: 종료 0, 4 gate `pass`, 권고 필드 없음, `review-2/`에 browser-check·finalize 영수증 3개, 폴더 밖 `d.browser-check.json`은 옛 것으로 남음(`out/c4.ls`). 복원 분기(R-20 둘째 `review-3`)는 실행하지 않음 |
| T-05 | R-10, R-21 | 아키텍처 입력(`web-app` 변형, 모든 `pos.y`에 +260, `meta.viewBox` 없음, `in/c11-leading-space…`)을 finalize. 이어 `pos.y`를 −260 되돌린 입력을 `--out-dir review-2`로 | 1차: 종료 0, `layoutReviewRecommendation.action:"inspect-leading-space"`, `evidence{emptyTopPx:370, emptyTopRatio:0.436, canvasHeight:848, reviewSuggested:true}`. 2차: 종료 0, 권고 필드 없음 |
| T-06 | R-03, R-15, R-23 | **deliver 단계 showcase 경고 + 한도.** 시퀀스 예제 `async-job-roundtrip`(viewBox 820×920) showcase finalize. 이어 진단의 "spread content sideways so the width is at least 1426" 쪽을 시도해 `meta.viewBox`를 `[1440,920]`으로 | 1차: 종료 1, `failedStage:"deliver"`, `gates{validate:"not-run", deliver:"fail", …}`, `composition/viewport-height`(`message` "Showcase delivery reported composition/viewport-height; zero warnings are required.", `evidence{ratio:0.89, wideRatio:1.55, pageHeightPx:1636, overflowPx:736}`, fix 종류 D), `nextAction` 없음, `s.html`이 이미 교체돼 존재(`out/c5.1.ls`). 2차: 종료 1, `failedStage:"validate"`, `composition/desktop-readability`(fix "…complete viewBox width is at most 1085px (current 1440px …)", `nextAction` 있음). 두 fix가 **동시에 만족될 수 없다**(폭 ≥1426 vs 폭 ≤1085): 지시문대로 구체적 격차를 보고해야 하는 경우. 이 사례는 통과하는 수리를 찾지 못했다 |
| T-07 | R-11, R-23 | `standard` 품질로 workflow 샘플(`release-delivery.workflow.json`, 6레인)을 finalize | 종료 1, `gates{pass, pass, pass, browser-check:"fail"}`, `failedStage:"browser-check"`, 요약의 `viewer/viewport-overflow` 1개: `message` "The rendered artifact overflows 6 viewport/theme combinations.", `supportedFixes` 한 문장 "contain the rendered layout within 1440x900 (smallest reported viewport), then rerun browser-check", `evidence.overflows` 6개(`browser-measurement`, 라이트 4+다크 2, `workflowLanes` 6개 포함). 전체 `w.browser-check.json`에는 같은 code 진단 6개와 4문장 fix(페이지 높이 분해·`validate workflow … --layout-json`·레인 재분배·`authoring-contract.md#workflow-viewport-repair`)가 있다. `nextAction` 없음 |
| T-08 | R-01, R-18(시작 전) | explainer 초안 `Claim.[](source:nope)`(출처 선언 없음) finalize. 이어 `@source s1 title=… path=archify/SKILL.md lines=1:10`을 추가하고 `[](source:s1)`로 고쳐 `--repo-root`와 함께 | 1차: 종료 1, **영수증 파일 없음**, stdout JSON `gates` 전부 `not-run`, `failedStage` 없음, `explainer/unresolved-reference`(`subject.line:7`, `evidence.example:"[Evidence](source:known-source)"`, fix `Use a valid form, for example: [Evidence](source:known-source)`). 2차: 종료 0, `gates` 3개 `pass` + `browser-check:"not-run"` |
| T-09 | R-01, R-06 | `ARCHIFY_CHROME=/nonexistent`로 아키텍처 샘플 finalize | 종료 2, `status:"skipped"`, `failedStage:"browser-check"`, 진단 `viewer/chrome-unavailable`(`severity:"warning"`, fix `set ARCHIFY_CHROME to a Chrome/Chromium executable (or Microsoft Edge) and rerun browser-check`), `browserCheck{requested:true, ran:false}`, `nextAction` 없음 |
| T-10 | R-03 | finalize 통과 후 `d.html` 끝에 주석 한 줄을 붙이고 `check d.html --require-provenance` | 종료 1, `provenance:"mismatch"`, `delivery/provenance-mismatch`(fix `restore the delivered artifact or rerun deliver to create a matching artifact and provenance pair`) |
| T-11 | R-05, R-09 | `validate architecture <후보> --quality showcase --json`(통과) → `nextAction.arguments`의 `<output.html>`만 `d.html`로 바꿔 `finalize` 실행. 이어 후보 라벨을 바꾸고 옛 `--candidate-sha256`로, 마지막으로 해시 없이 `--out-dir review-2` | validate: 종료 0, `candidateFrozen:true`, `candidate.sha256:"703cb55b…"`, `nextAction.arguments[0]:"architecture"`, `…["--quality","showcase","--candidate-sha256","703cb55b…","--json"]`. 그대로 실행: 종료 0. 옛 해시: 종료 1, 시작 전 실패 `finalize/candidate-changed`(`expected sha256 703cb55b…, found 92876075…`), `gates` 전부 `not-run`. 해시 없이: 종료 0 |
| T-12 | R-04 | 아키텍처 샘플에 `request→customer` 직접 연결을 추가해 finalize | 종료 1, `failedStage:"validate"`, `composition/proper-crossing`(`subject.id:"container-to-billing"`, fix 종류 C), `nextAction.constraint:"Preserve all semantics and user-fixed geometry. Use references/architecture-layout-repair.md to choose a local repair or connected-scene reflow; edit the existing candidate."`. 수리는 하지 않음(관찰만) |
| T-13 | R-02, R-03 | `sweep.py`: 10개 타입 예제 + 2개 입력 × 변이 8종 × 최대 3회 = 204회 `validate --quality showcase --json`, 시드 고정 | 통과 24, 실패 180, 진단 308개, 이 중 `supportedFixes` 비어 있는 것 101. code 상위: `layout/constraint` 78, `schema/additionalProperties` 36, `schema/type` 32, `composition/label-canvas-containment` 28, `relationship/duplicate-id` 21, `schema/required` 19, `dataflow/node-below-area` 12, `layout/component-out-of-bounds` 11, `composition/label-route-clearance` 9, `layout/component-overlap` 7(1.3 표) |
| T-14 | R-06, R-10 | `scan.sh`: 변이 없는 기존 예제 23개를 showcase `finalize` | 통과 20(그중 `web-app.architecture`·`product-analytics.dataflow`에 `visualReviewRecommendation`), 실패 3(`composition/viewport-height`). dataflow의 권고에는 `hints`가 없고 `repair`는 "Advisory only: …" |
| T-15 | R-19 | `validate architecture <후보> --layout-json`(T-02 ②의 거부된 후보, ③의 통과 후보) | 거부: 종료 1, JSON 키 `ok:false, contract:"archify-architecture-layout-v1", diagnostics, components, boundaries, connections, labels, viewBox…`. 통과: 종료 0, `ok:true`와 같은 레이아웃 키(진단·`contract` 없음). HTML은 쓰지 않음. 워크플로도 지원, 다른 타입은 `--layout-json is currently supported for architecture and workflow diagrams only.`(코드 확인) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

문서와 구현이 다르거나 문서끼리 다른 곳은 이 표에 `차이`로 남긴다.

| R-ID / T-ID | 근거 (archify@a406594 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | finalize 스펙 R-04·R-17·R-18, `bin/finalize.mjs:563-720` | 요약 필드는 finalize 스펙을 링크. 텍스트 모드 4줄 출력은 이 실험에서 다시 하지 않았고 finalize 스펙 T-02·T-05의 관찰을 쓴다(DEMO 출력은 모두 `--json`) |
| R-02, R-03 | C-03(`archify.mjs:2697-2785`), C-05(`render-architecture.mjs:812-822`), C-06(`visual-check.mjs:2150-2252`), `renderers/shared/validator.mjs:56-75`, `renderers/shared/i18n.mjs:252-288`, `renderers/shared/repository-evidence.mjs`, `renderers/shared/geometry.mjs`(hint 8곳) | 실행으로 수집(T-13, `out/sweep-codes.json`의 첫 예시 문장). 정적 표는 코드 확인. **차이**: README:363은 "only supported repair controls"라고 하지만 `supportedFixes`는 닫힌 집합이 아니고 41% 가까이 비어 있다(101/308, 변이 입력 기준) |
| R-04 | C-01, C-02(`finalize.mjs:584,709-718`) | 코드 확인 + 실행(T-01·T-12). finalize 스펙 R-29와 같은 규칙 |
| R-05 | C-04(`archify.mjs:7140-7165`), delivery-contract.md:13 | 실행(T-11). 실패 validate에 nextAction이 없음은 같은 함수 `else` 분기 읽기 |
| R-06 | grep `repairable\|retryable\|recoverable`: 의미 있는 일치 없음(`owned-temp-directory.mjs`의 파일시스템 재시도만) | 코드 확인. 존재하지 않음을 grep으로 확인한 것이라 다른 이름의 개념이 있을 수 있으나 영수증 필드는 finalize 스펙 1.3과 대조해 없음 |
| R-07 | `grep -n 'repairLimit\|repair.?limit\|correction_rounds\|focused repair'`: `SKILL.md:49,55`, `delivery-contract.md:11,633-654`뿐(마크다운). `bin/finalize.mjs`의 `attempt` 일치는 delivery 시도·재시도 문구(234, 380, 1040) | 코드 확인(grep). 문서에 "repair limit"라고 적힌 곳(SKILL.md:49)은 숫자가 없고 숫자는 delivery-contract.md:11에 있다 |
| R-08 | finalize 스펙 R-23, verification-gates 스펙 R-35, `bin/visual-check.mjs:253` | 실행(T-04 ①). **차이**: 진단 `message`가 "unowned evidence path"로 읽히지만 `reason.code`는 `ownership-artifact-mismatch`(소유권은 있으나 HTML 해시가 다름) |
| R-09 | C-08(`finalize.mjs:1030-1045`), finalize 스펙 R-20 | 실행(T-11) |
| R-10 | C-02(`finalize.mjs:660-708`), finalize 스펙 R-28 | 실행(T-04, T-05, T-14). **보정**: finalize 스펙은 두 권고 필드를 "미관찰"로 적었다. 이 실험에서 `resolvedCrossovers`(자동 라우팅 기본 입력을 흔들어 찾음, 150회 중 1회), `inspect-leading-space`, `routesOverSuggestedBends`·`Stretch`를 관찰했다 |
| R-11 | C-07(`finalize.mjs:405-425`), finalize 스펙 R-18·R-27 | 실행(T-07): 요약의 한 문장 vs `w.browser-check.json`의 4문장 대조 |
| R-12 | `SKILL.md:49,51-53`, `delivery-contract.md:5` | 지시문 원문. 준수 미확인 |
| R-13 | `authoring-contract.md:269-277`(`Repair order`) | 지시문 원문. T-01~T-03은 이 순서와 무관하게 한 번에 닫혔다. T-02는 겹침(②)이 경로·라벨(④⑤)보다 먼저 고쳐지며 새 진단이 단계별로 드러난 사례 |
| R-14 | `delivery-contract.md:7,9`, `architecture-layout-repair.md:3,7,9,15`, `authoring-contract.md:1-13`(Composition repair·Label repair), `delivery-contract.md:616`, `SKILL.md:93` | 지시문 원문 |
| R-15 | `delivery-contract.md:11` | 지시문 원문. **차이**: 한도가 L1~L5로 대상별로 따로 있고 서로 다른 단위(지속 문제 / 상관 라운드 / 위치 라운드 / 폭 시도 / 레이아웃 수리)를 센다. 한 곳에 합쳐 적힌 한도는 없다 |
| R-16 | `delivery-contract.md:11`, `SKILL.md:44,49` | **차이**: delivery-contract는 재실행에 `--quality showcase`를 쓰라고 하고 SKILL.md:44는 `meta.quality_profile`과 같은 `--quality`(밀집 ERD 첫 패스는 `standard`)를 쓰라고 한다. 두 문장이 충돌하는 경우(초안이 `standard`)의 우선순위는 문서에 없다 |
| R-17 | `SKILL.md:49,93`, `delivery-contract.md:11,563-574` | 지시문 원문. **차이(이름)**: 폴더 이름이 `<output-stem>.review-<revision>`(delivery-contract.md:11)와 `<folder>/review-<n>`(SKILL.md:49,93)로 다르다. 코드는 임의 폴더를 받으므로 이름 규칙은 관례다 |
| R-18 | `delivery-contract.md:13`, finalize 스펙 R-12·R-05 | 지시문 원문 + 코드(T-09 skipped 종료 2) |
| R-19 | `architecture-layout-repair.md:1-18`, `authoring-contract.md:244-262`, `archify.mjs:6973-6994`(`--layout-json` 옵션 처리) | 지시문 원문, `--layout-json` 동작은 실행(T-15). **차이**: authoring-contract·architecture-layout-repair는 `validate architecture … --layout-json`을 쓰라고 하고 [rendering.md](rendering.md) R-05는 직접 실행 렌더러가 7개 타입을 지원한다고 하는데, 공개 `validate`는 architecture·workflow만 받는다(`archify.mjs:6991`) |
| R-20 | `SKILL.md:93`, C-02 | 지시문 원문, 위치 수리 한 라운드는 T-04. **차이**: architecture-layout-repair.md:18은 사람 눈 검토 뒤의 수리에 "bounded second repair"를 허용하지만, SKILL.md:93은 `resolvedCrossovers` 위치 수리에 "second placement round"를 금지한다. 트리거가 달라 모순은 아니나 한 에이전트가 두 트리거를 같이 만나면 어느 쪽이 우선인지 문서에 없다 |
| R-21 | `finalize.mjs:693-708`, `delivery-contract.md:491-498` | 코드 확인 + T-05. `inspect-sequence-width`는 만들지 못함 |
| R-22 | `delivery-contract.md:602-665`, `SKILL.md:97` | 지시문 원문. 실행하지 않음 |
| R-23 | `authoring-contract.md:297-318`, `delivery-contract.md:9,616`, C-06 | 지시문 원문 + 코드(T-06·T-07의 진단). 통과하는 수리 사례는 만들지 못했다 |
| R-24 | `delivery-contract.md:625-665`(상태 값·핸드오프 영수증), `SKILL.md:103,131` | 지시문 원문 |
| T-01~T-12 | DEMO `run-cases.sh`, `out/cases-digest.txt`, `out/<사례>.*` | 실행. 수리는 실험자가 적용 |
| T-13 | DEMO `sweep.py`, `out/sweep-*` | 시드 고정(20261102). 변이에 종속 |
| T-14 | DEMO `scan.sh`, `out/scan-summary.txt` | 실행 |
| T-15 | DEMO `out/c2.layout-json.*.json` | 실행 |

### 2.2 코드 읽는 순서 [선택]
1. `SKILL.md:49`(루프 한 줄) → `references/delivery-contract.md:3-13`(수리 절 전체) → 필요 시 `563-574`(경로 재사용).
2. 코드 신호: `bin/finalize.mjs:563-720`(`nextAction`·권고), `bin/archify.mjs:2697-2785`(검사 단계 fix 표), `7140-7165`(validate의 `nextAction`).
3. 레이아웃 수리: `references/architecture-layout-repair.md`(18줄) → `authoring-contract.md:244-278`.
4. 단계별 fix 문장의 실물은 DEMO `out/sweep-codes.json`과 `out/cases-digest.txt`가 빠르다.

## 적용 메모 [선택]
(재구현 계획 없음 — 원본 동작만 기록. overview 1절)
