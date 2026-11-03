---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/bin/archify.mjs
  - archify/bin/delivery-update.mjs
  - archify/bin/recover-output.mjs
  - archify/renderers/shared/output-path.mjs
  - archify/renderers/shared/portable-path.mjs
  - archify/renderers/shared/sidecar-path.mjs
  - archify/renderers/shared/path-semantics.mjs
  - archify/renderers/shared/atomic-output.mjs
  - archify/references/delivery-contract.md
depends: [rendering.md]
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# 전달 (deliver)

> 타입 이름·입력 JSON 경로·(선택) 출력 경로를 받아, 같은 디렉터리의 staging 폴더에서 렌더러와 정적 검사를 통과시킨 뒤, HTML과 그 해시를 담은 provenance 사이드 파일(`<stem>.delivery.json`)을 한 쌍으로 교체해 두고, 실패하면 기존 HTML을 그대로 둔 채 provenance를 "실패" 표지로 바꾸는 CLI 명령 `archify deliver`.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. `archify deliver <type> <input.json> [output.html] [--json] [--open] [--quality …] [--repo-root …]`. 인자를 해석하고 `<type>`에 맞는 렌더러 경로(`renderers/<type>/render-<type>.mjs`)를 정한다.
2. 입력 파일을 **한 번** 읽고 JSON으로 파싱한다. 출력 경로를 정한다(CLI 인자 > `meta.output` > `<type>.html`). 입력과 같은 파일이면 거부한다. 출력 폴더를 만들고(`mkdir -p`), HTML과 provenance 대상의 현재 상태(없음 / 일반 파일 1개 링크)를 스냅샷한다.
3. 출력 폴더 안에 `.archify-delivery-XXXXXX/` staging 폴더를 만든다. 출력 폴더 전체 잠금(`.archify-delivery-lock.json`)을 잡고, 진행 중 표시 journal(`<stem>.delivery-pending.json`)을 쓴다.
4. 입력 바이트를 staging의 `specification.snapshot.json`에 고정하고, **그 스냅샷**을 렌더러(자식 프로세스)에 넘겨 staging에 HTML 후보를 얻는다(렌더러가 하는 일: [rendering.md](rendering.md)).
5. 후보 HTML에 정적 검사(`scripts/check-render-output.mjs`, 자식 프로세스)를 돌린다(검사 항목: [verification-gates.md](verification-gates.md)). 통과하면 입력·후보의 SHA-256과 크기로 provenance JSON을 만들어 staging에 쓴다.
6. 쌍 교체는 **단계별**이다. 두 대상을 검증하고, 기존 HTML과 provenance를 차례로 staging 백업(하드링크 후 공개 이름 제거)으로 옮긴 뒤, HTML 후보와 provenance 후보를 차례로 공개 이름으로 하드링크한다. 성공하면 staging 후보와 journal을 지운다(R-16).
7. 잠금을 풀고, `--open`이면 연다. stdout에 요약 또는 JSON 영수증을 쓰고 종료 코드 0. staging 폴더는 항상 지운다(복구 필요 때만 남김).
8. 어느 단계에서든 실패하면: HTML은 건드리지 않고(기존 파일 바이트 유지), 기존 HTML이 있으면 provenance를 `status: "failed"` 표지로 교체하고, journal은 남기고, 잠금·staging은 정리한다. 종료 코드 1(인자 오류는 2).

### 1.2 범위·통합 지점
- 제공: 한 입력을 검증된 HTML로 전달하는 명령, 출력 경로 해석 규칙, HTML과 provenance의 쌍 교체와 실패 시 상태, provenance 파일의 형식·이름 규칙·검증 규칙, 출력 폴더 잠금과 journal.
- 제외:
  - 렌더링 내용(스키마 검증·SVG·템플릿)은 [rendering.md](rendering.md). 여기서는 "staging의 스냅샷으로 렌더러를 자식 프로세스로 실행해 staging 파일에 HTML을 얻는다"만 쓴다. 렌더러 종료 코드 0 / 비0과 stderr의 구조화 진단만 소비한다.
  - 정적 검사 항목은 [verification-gates.md](verification-gates.md). 여기서는 "`check-render-output.mjs <candidate>`가 종료 코드 0이면 통과, stdout이 JSON 영수증"만 쓴다.
  - 단계 오케스트레이션(`finalize`)·`browser-check`는 finalize 스펙과 verification-gates. provenance를 읽고 검증하는 쪽(check)이 이 스펙의 1.4 R-10을 링크한다.
  - `explainer` 타입(Markdown 초안 준비·리소스 번들)은 별도 행(explainer). 이 스펙의 전달 뼈대는 같지만 explainer 전용 분기(`prepareExplainerInput`, `--writing`, provenance의 `explainer` 필드)는 이름만 언급한다. `meta.output`이 explainer에서는 선택이다(R-03).
  - `--open`의 OS별 실행 방식(`bin/open-artifact.mjs`)과 업데이트 확인의 내용(`bin/delivery-update.mjs`)은 영수증 필드 이름만 쓴다.
- 외부 의존·선행 계약: 렌더러 CLI 계약 `node <renderer> <input> <output>` (rendering.md). 정적 검사 CLI 계약 `node check-render-output.mjs <html>` → 종료 코드와 stdout JSON(`ok`, `checks[]`, `composition{profile,status,summary{errors,warnings},issues[]}`). Node.js 18+, 출력 폴더가 로컬 파일시스템이고 `link`·`rename`·`mkdtemp`가 되는 것.
- 소유 상태·부작용:
  - 출력 폴더(없으면 만든다): HTML, `<stem>.delivery.json`, `<stem>.delivery-pending.json`, `.archify-delivery-lock.json`(+ 레거시 `<stem>.delivery-lock.json` 울타리), `.archify-delivery-XXXXXX/`(staging).
  - 스킬 폴더나 입력 파일은 바꾸지 않는다.
  - 외부: 업데이트 확인 자식 프로세스 1개(1초 제한, `ARCHIFY_UPDATE_CHECK_DISABLED=1`이면 생략), `--open`의 OS opener.

### 1.3 인터페이스와 데이터 의미

**명령행**

| 항목 | 의미·제약 |
|---|---|
| `<type>` | 필수. `architecture workflow sequence dataflow lifecycle erd tree class timeline waterfall explainer` 중 하나. 아니면 종료 2, 코드 `cli/unknown-diagram-type`(렌더러 경로 해석에서 거부, 입력은 읽지 않음). |
| `<input.json>` | 필수. 상대 경로는 cwd 기준. |
| `[output.html]` | 선택. 위치 인자 3번째. 4개 이상이면 usage 오류. |
| `--json` | stdout에 JSON 영수증(성공·실패 모두)을 쓴다. 없으면 사람용 텍스트. |
| `--open` | 전달 성공·잠금 해제 뒤 OS opener로 연다. 실패해도 전달은 성공이고 stderr에 안내만 쓴다. 영수증에 `open{requested,status,target,method[,failure]}`. |
| `--quality standard\|showcase` | 렌더러·검사에 `ARCHIFY_QUALITY_PROFILE`로 전달. 값 누락 `cli/missing-option-value`, 잘못된 값 `cli/invalid-option-value`(`--quality=값` 형태도 허용). deliver 자체의 기본값은 없음(렌더러가 `meta.quality_profile` 등으로 결정, rendering.md). |
| `--repo-root <path>` | 렌더러에 `ARCHIFY_REPO_ROOT`(절대화)로 전달. 값 누락 `cli/missing-option-value`. `--repo-root=값` 허용. |
| `--writing warn\|strict\|off` | explainer 전용. 다른 타입에서 쓰면 `cli/unsupported-option`. |
| 그 밖의 `--x` | `cli/unknown-option` (`Unknown deliver option "--x".`). `-x` 한 줄 대시 인자는 옵션이 아니라 위치 인자로 센다. |

**종료 코드**: 0 성공. 2 인자 오류(위치 인자 0~1개, 4개 이상, 알 수 없는 타입·옵션, 옵션 값 오류). 1 그 밖의 실패. 렌더러·검사가 실패하면 그 자식의 종료 코드(`status ?? 1`)를 그대로 쓴다(실측 1).

**stdout / stderr**

| 상황 | `--json` 없음 | `--json` |
|---|---|---|
| 성공 | stdout 2줄: `delivered <type> <절대 출력 경로>` / `<통과>/<전체> artifact checks; composition <profile>: <status>[; engineering <p>: pass]; sha256 <해시 앞 12자리>`. 업데이트 안내가 필요하면 한 줄 더, `--open` 성공이면 `opened <경로>`. 렌더러 stderr와 로케일 경고(`archify: <message>`)는 stderr. | stdout에 영수증 JSON(아래) 1개. |
| 실패 | stderr에 `<error 문장>` 다음 줄마다 `[<code>] <message> Fix: <supportedFixes를 "; "로 연결>.` | stdout에 실패 영수증 JSON 1개. 인자 오류(`stage: "arguments"`)도 `--json`이면 JSON(종료 2). 인자 오류 `--json` 없음: stderr에 메시지만(usage 오류는 사용법 표 전체), 종료 2. |

**성공 영수증** (stdout JSON. 필드 순서대로)

| 필드 | 값 |
|---|---|
| `schemaVersion` | `1` |
| `receiptId` | 이번 시도의 UUID v4 |
| `ok` | `true` |
| `command` | `"deliver"` |
| `type`, `input`, `output` | 타입, 입력 절대 경로, **정규화된 출력 절대 경로**(R-23) |
| `explainer` | explainer일 때만 `{preparedSha256, dependencies[]}` |
| `specification` | `{sha256, bytes}` — 읽은 입력 바이트 |
| `artifact` | `{sha256, bytes}` — 검사를 통과한 후보 HTML 바이트 |
| `validation` | `{checksPassed, checkCount, compositionProfile, compositionStatus, [engineeringProfile], errors, warnings, [compositionIssues(경고만)]}` (검사 영수증의 `checks[]`·`composition`에서 가져옴) |
| `evidence` | 렌더된 HTML에 `archify-source-evidence-data` 스크립트가 있을 때만 `{verified:true, repository, revision, references, [linkMode]}` |
| `diagnostics` | 로케일 경고가 있을 때만 |
| `open` | `--open`일 때만 |
| `update` | 업데이트 확인 결과. 필드 이름: `status, installedVersion, availableVersion, releaseNotes, severity, summary, checkedAt, source, noticeRequired, noticeText, eventKey, reason, suppressedUntil` (`unavailable`이면 앞쪽 일부와 `reason`만; 내용은 이 스펙 범위 밖) |

**실패 영수증** (stdout JSON): `schemaVersion:1, ok:false, command:"deliver", [receiptId], stage, type, input, [output], error, diagnostics[], [provenance], [checker], [update]`. `stage` ∈ `arguments`(인자) / `input` / `prepare` / `render` / `check` / `receipt` / `commit` / `release`. `provenance` ∈ `failed`(실패 표지 기록됨) / `absent`(기존 HTML 없음, 기록할 것 없음) / `unrecorded`(기록 못함) / `not-applicable`. `diagnostics[]` 항목은 `{code, severity:"error", message, subject{}, evidence{}, supportedFixes[]}`. `checker`는 `check` 단계 실패일 때 검사 영수증 전체(`file`은 최종 출력 경로로 바꿈).

**provenance·journal·잠금 파일** (이 스펙이 소유하는 외부 계약)

*이름 규칙* — 아래에서 `A`는 최종 HTML의 **물리 경로**(심볼릭 링크는 realpath로 풀고, 아직 없으면 존재하는 가장 가까운 조상 폴더 + 나머지 이름).

| 파일 | 경로 | 비고 |
|---|---|---|
| provenance | `dirname(A)/<stem>.delivery.json` | 가장 최근에 **완료된** 시도 기록 |
| journal | `dirname(A)/<stem>.delivery-pending.json` | 진행 중·미복구 표지 |
| 폴더 잠금 | `dirname(A)/.archify-delivery-lock.json` | 폴더당 1개 |
| 레거시 잠금(전달 중에만 추가로 만듦) | `<A에서 .html/.htm 제거>.delivery-lock.json` (요청한 철자와 물리 철자 각각, 이름이 255바이트 이하일 때) | 구버전 바이너리 차단용. 이미 있으면 `rejectExistingDeliveryLock` 규칙 |
| staging | `dirname(A)/.archify-delivery-` + `mkdtemp` 6자 | 안에: `specification.snapshot.json`, `<basename(A)>`(후보), `delivery-provenance.json`(후보), `.previous-output`, `.previous-provenance`(백업) |

`<stem>`은 C-01로 정한다: `basename(A)`를 (1) 문자(grapheme) 단위로 NFC 정규화, (2) 대소문자 접기(`toLocaleUpperCase('en-US').toLocaleLowerCase('en-US')`)를 **그 폴더의 파일시스템이 두 철자를 같은 항목으로 취급할 때만** 적용(임시 파일 탐침으로 확인), (3) 다시 NFC. 결과가 리터럴 `.html`로 끝나면 stem은 그 앞부분. 아니면 전체 이름을 stem으로 쓰면서 해시 표지를 붙인다(`.~archify-<sha256 hex 64>` ← 입력 `"full-component\0"+이름`). 어떤 접미사(`.delivery.json`/`.delivery-pending.json`/`.delivery-lock.json`)를 붙여도 255바이트(UTF-8)·255 UTF-16 단위를 넘으면 stem 끝을 코드포인트 단위로 잘라내고 `.~archify-<sha256(stem)>`을 붙인다. 즉 대소문자를 구분하지 않는 파일시스템(macOS 기본)에서 `CamelCase.html` → `camelcase.delivery.json`, `Mixed.HTML` → `mixed.delivery.json`(실측), 구분하는 파일시스템에서 `Mixed.HTML`은 `Mixed.HTML.~archify-<해시>.delivery.json`(코드 확인, 미실행). 읽을 때(`check`)는 같은 파생 외에 폴백으로 "HEAD 시대" 원본 철자(`<stem>.delivery.json`, 해시 표지 없는 stem일 때만)와 "구 확장자" 철자(`.HTML` 등 대문자 확장자에서 `.html`만 떼고 접미사를 붙인 이름)를 찾는다.

*provenance 내용* (`status: "current"`, UTF-8 JSON, 2칸 들여쓰기, 끝에 개행 1개)

| 필드 | 타입 | 의미 |
|---|---|---|
| `schemaVersion` | int | `1` |
| `receiptId` | string | UUID v4, 영수증 `receiptId`와 같음. 시도마다 새로 생성 |
| `status` | string | `"current"` |
| `command` | string | `"deliver"` |
| `type` | string | 다이어그램 타입 |
| `input` | string | 입력 절대 경로(전달 시점 철자) |
| `output` | string | 정규화된 HTML 절대 경로. 검사 시 점검 대상과 **같은 디렉터리 항목**이어야 함 |
| `specification` | `{sha256, bytes}` | 읽은 입력 바이트의 SHA-256(소문자 hex 64자)과 바이트 수 |
| `artifact` | `{sha256, bytes}` | 최종 HTML 바이트의 SHA-256과 바이트 수 |
| `explainer` | `{preparedSha256, dependencies[]}` | explainer일 때만 |

*실패 표지* (`status: "failed"`): `schemaVersion:1, receiptId, status:"failed", command:"deliver", stage, input, output, [artifact{sha256,bytes}], error`. `artifact`는 그때 존재한 기존 HTML을 읽을 수 있었을 때만. 특정 `type`·`specification`은 없음.

*journal 내용*: `{schemaVersion:1, command:"deliver", status:"pending", receiptId, input, output}`.

*잠금 내용*: `{"schemaVersion":1,"receiptId":<uuid>,"pid":<int>}` + 개행.

**출력 경로 규칙(해석 순서)**

| 단계 | 규칙 |
|---|---|
| 우선순위 | CLI 위치 인자 → `meta.output` → `<type>.html`(cwd). CLI 인자가 있어도 `meta.output`은 먼저 검증된다(R-03). |
| 기준 | 상대 경로는 모두 cwd(`process.cwd()`) 기준. |
| 최종화 | 경로를 정한 뒤 `canonicalFuturePath`로 물리 경로를 얻는다(존재하면 realpath, 아니면 가장 가까운 존재하는 조상의 realpath + 나머지). 심볼릭 링크 순환은 `output/symlink-cycle`. |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 인자 해석: 위 표. `<type>`·`<input>` 없음 또는 위치 인자 4개 이상 | 종료 2. `--json` 없이는 stderr에 사용법 표. 알 수 없는 `--옵션`은 `cli/unknown-option`(`--json`이면 JSON `stage:"arguments"`, 종료 2). 어떤 파일도 만들지 않는다 | 실행 확인 |
| R-02 | `--json` 유무에 따른 stdout/stderr 모양, 성공·실패 영수증 필드 | 1.3 표대로. 성공 사람용 출력은 2줄(+옵션). 실패는 stderr `error` + `[code] message Fix: …` | 실행 확인(필드), 코드 확인(`update`·`open` 필드 이름) |
| R-03 | 출력 우선순위. 비-explainer는 `meta.output`이 **없거나 형식이 틀려도** CLI 출력 인자와 무관하게 `validateAuthoredOutputPath`에서 먼저 실패. explainer는 `meta.output`이 있을 때만 검증 | CLI 인자 > `meta.output` > `<type>.html`. `meta.output` 누락 시 `output/meta-path-syntax`(reason `type`). 실패는 `stage:"prepare"`, 어떤 파일·폴더도 만들지 않고 provenance·journal도 쓰지 않는다. 입력 JSON을 읽지 못한 `input` 단계 실패는 이 단계 이전이라 `meta.output`을 못 보고 출력 철자를 `CLI 인자 \|\| <type>.html`로 보고한다 | 실행 확인(CLI가 `meta.output`을 덮어씀·누락 거부), 코드 확인(explainer 예외) |
| R-04 | `meta.output` 규칙: POSIX 상대, `/` 구분, 비어 있지 않은 `.html` basename(대소문자 무시), 절대(`/`·`\`·`C:\` 시작)·드라이브 상대(`C:x`)·URI 스킴·역슬래시·빈 세그먼트·`.`/`..` 세그먼트·제어 문자·짝 없는 서로게이트·`:`·`<>"\|?*`·끝의 `.`/공백·Windows 장치 이름(`con prn aux nul conin$ conout$ com1-9 lpt1-9`와 윗첨자 숫자, 뒤에 `.확장자` 허용)·8.3 모양(`~숫자`)·세그먼트가 UTF-8 255바이트 또는 UTF-16 255단위 초과 거부. cwd 기준으로 풀었을 때 심볼릭 링크를 따라간 뒤에도 `.html`이고 cwd 안이어야 함 | 위반 시 코드: 절대 `output/meta-absolute`, 그 밖의 형식 `output/meta-path-syntax`(`evidence.reason`에 세부 사유), 확장자 `output/meta-extension`, 링크 해소 후 확장자 `output/meta-resolved-extension`, cwd 밖 `output/meta-outside-cwd`, 판정 불가 `output/containment-indeterminate`. 실측: `/tmp/x.html`·`../x.html`·`a\b.html`·`CON.html`·`a/../x.html`·누락 거부, `x.txt`는 `meta-extension` | 실행 확인(7종), 코드 확인(나머지 reason) |
| R-05 | CLI 출력 인자 규칙(호스트 네이티브 문법). 절대·상대·cwd 밖(`../x.html`)·`..` 중간 세그먼트(`up/../rel/x.html`) 허용. 빈 문자열·NUL·짝 없는 서로게이트·끝 구분자(`dir/`)·구성요소가 255바이트(UTF-8, POSIX) 초과는 거부. Windows 호스트: 드라이브 상대, `\file`(현재 드라이브 루트), 장치 네임스페이스, `\\?\` 확장 경로 중 허용 형식 외, ADS(`:`), 장치 이름, 끝의 `.`/공백, 255 UTF-16 단위 초과 거부. POSIX에서는 Windows 이름 규칙을 적용하지 않는다(`con.html` 허용). 확장자는 `.html`(대소문자 무시)이어야 하고 심볼릭 링크를 따라간 끝도 `.html`이어야 함 | 위반 시 `output/native-path-syntax`(`evidence.reason` 예: `trailing-separator`, `component-too-long`, `windows-reserved-name`…), 확장자 `output/cli-extension`(`.txt`·`.htm` 포함), 링크 끝 `output/cli-resolved-extension`(Windows 호스트의 `.htm`→`.html` 기존 별칭만 예외). 모두 `stage:"prepare"`이고 출력 폴더도 만들지 않는다. 실측: `out.txt`·`out.htm` → `cli-extension`, `dir/` → `native-path-syntax`, `.txt`를 가리키는 댕글링 `lnk.html` → `cli-resolved-extension`, `up/../rel/x.html`·절대·`../up-out.html`·`Mixed.HTML`·`con.html` 성공 | 실행 확인(POSIX), 코드 확인(Windows·`\\?\`) |
| R-06 | 출력(정규화 전·후)이 입력 경로와 같은 항목이거나 provenance 경로가 입력 또는 HTML 경로와 같은 항목(심볼릭 링크·미래 경로 별칭 포함) | `output/input-alias`("Output must not replace an input" / provenance 쪽은 "the delivery input"), HTML과 provenance가 서로 같으면 `output/target-alias`. 입력 파일은 바뀌지 않는다. 실측: `same.html same.html`, 입력을 가리키는 심볼릭 링크 출력, `./in/../in/ok.json`, 입력 `x.delivery.json`을 출력 `x.html`로 (provenance 경로 충돌) 거부. 입력이 자기 `meta.output`과 같은 이름이어도 거부 | 실행 확인 |
| R-07 | 출력 폴더와 대상 상태: 폴더가 없으면 `mkdir -p`(렌더 이전이라 이후 실패해도 폴더는 남는다). 대상 HTML·provenance가 없거나 **링크 1개인 일반 파일**이어야 함. HTML 대상이 파일 심볼릭 링크면 링크는 보존하고 가리키는 실제 파일을 교체 | 폴더 생성 실패 `delivery/prepare-directory`. 하드링크 2개 이상 `output/target-hardlinked`(provenance 쪽은 `delivery/provenance-hardlink-unsupported`), 디렉터리·FIFO 등 `output/target-not-regular-file`, 스냅샷과 달라짐 `output/target-changed`, 판정 불가 `output/target-indeterminate`. 이들은 `stage:"prepare"`(또는 commit)이며 HTML·provenance·journal을 쓰지 않는다. 실측: 하드링크 대상, 디렉터리 `dirtarget.html`, 심볼릭 링크 `alias.html` 경유 재전달(링크 유지, `real.html` 교체, 사이드 파일은 `real.delivery.json`만) | 실행 확인 |
| R-08 | 사이드 파일 이름 | 1.3 "이름 규칙" 표대로. 실행 폴더가 대소문자 무시 파일시스템이면 stem이 소문자로 접힘(실측) | 실행 확인(APFS 대소문자 무시), 코드 확인(구분 FS·긴 이름·NFC) |
| R-09 | 성공 시 provenance 내용 | 1.3 "provenance 내용" 표대로. `specification.sha256`은 렌더에 쓴 스냅샷과 같은 바이트의 해시, `artifact.sha256`은 **검사 통과 뒤 후보 파일을 다시 읽은** 바이트의 해시. 같은 입력을 같은 경로에 다시 전달하면 `artifact`·`specification`은 같고 `receiptId`만 새로 바뀐다 | 실행 확인(재전달 시 해시 동일·receiptId 변경) |
| R-10 | provenance 검증(`check`/`browser-check`가 호출. `--require-provenance` 유무 포함) 입력 HTML 경로 `P`, 바이트 | **순서대로** 판정, 첫 해당에서 결과 결정. (1) `P`의 journal(이름 규칙의 정규·HEAD·구확장자 3철자 중 하나라도 존재) → `failed`, `delivery/provenance-failed`("unfinished or failed"). (2) 폴더 잠금 또는 레거시 잠금 존재 → `locked`, `delivery/provenance-locked`. 존재 판정 중 오류는 `invalid`. (3) provenance 파일 찾기(정규→HEAD→구확장자 순). 없으면: 플래그 없음 `unknown`·통과, `--require-provenance`이면 `unknown`·실패 `delivery/provenance-required`. (4) 파일이 링크 1개 일반 파일이 아니면(하드링크는 `unsupported`, `delivery/provenance-hardlink-unsupported`) 또는 JSON이 아니거나 스키마 불일치(`schemaVersion===1`, `command==="deliver"`, `receiptId`가 UUID v4, `output`·`input`이 절대 경로, `status`∈{current,failed}, current면 `type`이 유효 타입이고 `specification`·`artifact`가 `{sha256:/^[0-9a-f]{64}$/, bytes:음이 아닌 안전 정수}`, failed면 `stage`가 문자열) → `invalid`, `delivery/provenance-invalid`. (5) `receipt.output`이 점검 중인 `P`와 같은 디렉터리 항목이 아니면 `invalid`(판정 불가면 `delivery/provenance-output-indeterminate`). (6) `status:"failed"` → `failed`, `delivery/provenance-failed`("stale because the latest delivery attempt failed"). (7) 실제 바이트의 SHA-256·길이가 `artifact`와 다르면 `mismatch`, `delivery/provenance-mismatch`(evidence에 기대·실제 해시와 크기). (8) 일치하면 `current`(`receiptId`, `artifact`, `type` 반환). `unknown`만 플래그 없이 통과하고 나머지(`failed` `locked` `invalid` `unsupported` `mismatch`)는 항상 실패 | 실행 확인((1)(3)(6)(7)·current), 코드 확인(나머지) |
| R-11 | 단계 순서 | 입력 읽기 → 출력 경로 해석(R-03~06) → `mkdir -p` → provenance 경로 해석(R-06) → 대상 스냅샷(R-07) → 업데이트 확인 시작 → staging 생성 → 잠금(R-18) → 대상 재스냅샷 → journal(R-19) → 입력 스냅샷 고정 → **렌더** → 렌더 stderr·로케일 경고를 stderr로 → **검사** → 영수증·provenance 후보 작성 → 경로 재해석 → **쌍 교체**(R-16) → 잠금 해제 → `--open` → 출력. 각 단계가 실패하면 뒤 단계는 실행되지 않는다 | 코드 확인 |
| R-12 | 렌더·검사 호출 규약 | 렌더: `node <renderer> <staging>/specification.snapshot.json <staging>/<basename(A)>`, `stdio: pipe`, 환경에 `ARCHIFY_DIAGNOSTIC_FORMAT=json`(+ `ARCHIFY_QUALITY_PROFILE`·`ARCHIFY_REPO_ROOT`; explainer는 준비 번들 변수). 입력 파일은 이후 다시 읽지 않으므로 전달 도중 입력이 바뀌어도 결과·해시는 처음 읽은 바이트 기준. 렌더 성공 뒤 후보 파일에 기존 대상의 권한 비트를 적용(대상이 있을 때). 검사: `node scripts/check-render-output.mjs <staging 후보>`, stdout 버퍼 상한 64 MiB(환경변수 `ARCHIFY_CHECK_MAX_BUFFER`로 조정), 상한 초과로 종료되면 판정이 아니라 실패(`stage:"check"`, 메시지 "output buffer … previous artifact was preserved") | 코드 확인 |
| R-13 | 렌더 또는 검사 실패, 영수증 파싱·후보 읽기 실패, 쌍 교체 도중 롤백 가능한 실패(R-17), 검사 통과 후 경로 재해석 실패 — 이때 **기존 HTML이 있었음** | (a) 기존 HTML 바이트 불변. (b) `<stem>.delivery.json`이 R-10의 실패 표지로 교체됨(`artifact`에 기존 HTML의 해시, `stage`에 실패 단계 `input\|prepare\|render\|check\|receipt\|commit`, `error`에 메시지). 이전의 `current` provenance는 사라지므로 이후 `check`는 `failed`로 막힌다. (c) journal(`<stem>.delivery-pending.json`)이 남는다. (d) 폴더 잠금·staging 폴더는 정리된다. (e) 영수증 `provenance:"failed"`, 종료 1(렌더·검사는 자식 종료 코드). 실측(스키마 오류 입력, `stage:"render"`): HTML 해시 전후 동일, provenance가 `failed`, `*.delivery-pending.json` 존재, `check`는 `delivery/provenance-failed`로 종료 1. 기존 HTML이 provenance 없이 있던 경우도 실패 표지가 새로 생기고 `artifact`에 기존 해시가 들어감. 연속 실패는 표지의 `receiptId`만 갱신 | 실행 확인(render 단계), 코드 확인(check·receipt·commit 단계 — 모두 같은 `reportDeliveryFailure` 경로) |
| R-14 | 같은 실패인데 **기존 HTML이 없음**(첫 전달 실패, 또는 입력 읽기 실패) | HTML·provenance는 만들지 않는다(영수증 `provenance:"absent"`, 단 렌더 실패 등에서는 필드가 생략될 수 있음). 이미 만든 출력 폴더와 **journal은 남는다**(`<stem>.delivery-pending.json`). 같은 경로에 이후 성공 전달을 하면 journal이 덮어써졌다가 지워지고 provenance가 생긴다. 다른 출력 경로의 전달은 이 journal에 막히지 않지만 그 경로의 `check`는 R-10 (1)로 막힌다. 실측: `fresh/dir/never.delivery-pending.json`만 남음 → 같은 경로 성공 전달 후 `never.html`·`never.delivery.json`만 남음 | 실행 확인 |
| R-15 | 같은 경로에 이미 정상 산출물(HTML+`current` provenance)이 있고 새 전달이 성공 | 두 파일이 새 쌍으로 교체되고 journal·잠금·staging이 남지 않는다. HTML이 같으면 provenance 안의 `receiptId`만 다르다. 입력이 다르면 `specification`·`artifact`·`bytes`가 바뀐다. `check --require-provenance`가 `current`와 `deliveryReceiptId`(=새 `receiptId`)를 돌려준다. 실패 표지·잔여 journal 위에 성공 전달해도 같은 결과로 복구된다 | 실행 확인 |
| R-16 | 쌍 교체(성공 경로). 입력: staging 후보 두 개, 두 대상의 스냅샷, 잠금·journal 소유권 | 대상별 순차가 아니라 **단계별**이다(각 단계는 HTML → provenance 순으로 두 대상을 돌고, 매 변경 직전 잠금·journal 소유권을 확인). ① 두 대상 모두: 스냅샷 재확인(경로 슬롯·종류·장치/inode·권한·링크 수 1), 후보를 대상 권한으로 chmod하고 해시·크기·링크 1 확인, 기존 대상이 파일이면 그 바인딩 확보. ② 백업: HTML을 staging `.previous-output`으로 **하드링크**(링크 2개 확인)하고 공개 이름을 격리 폴더로 `rename`한 뒤 `unlink`(중간에 다른 파일이 끼어든 것이 확인되면 복원하고 실패), 이어 provenance를 `.previous-provenance`로 같은 방식으로 백업. ③ HTML 후보를 공개 이름으로 `link`, 이어 provenance 후보를 `link`(이미 있으면 `EEXIST` → 남이 선점, 실패). 각 `link` 직후 링크 2개 확인. ④ 두 공개 이름 링크 2개 재확인 → 두 staging 후보 이름을 격리 제거 → 두 공개 이름 링크 1개 확인 → 마지막으로 **journal을 지운다**. 따라서 ②와 ③ 사이에는 HTML·provenance 공개 이름이 **둘 다 없는** 구간이 있고, ③의 두 `link` 사이에는 HTML만 새 파일이다. `rename`으로 덮어쓰지 않는 이유: 늦게 나타난 다른 쓰기자를 덮지 않기 위함. 같은 기본 연산(백업·격리 제거)을 단일 파일 경로(`render`의 `writeDiagram`)도 쓰지만 그쪽은 잠금·journal이 없고 복구 기록 파일을 남기는 점이 다르다([rendering-contracts.md](rendering-contracts.md) R-13, R-14, 1.3 D) | 코드 확인([rendering-contracts.md](rendering-contracts.md) R-14와 같은 코드. 순서는 `commitDeliveryPair`의 `for` 단계 6개로 확인) |
| R-17 | 쌍 교체 도중 실패(②③④ 중) | 되돌리기는 **두 루프**다(R-16의 단계 구조와 대응). (1) 새로 링크된 공개 이름을 역순으로 소유 확인 후 격리 제거(링크 수 기대는 후보가 아직 있으면 2, 없으면 1). (2) 백업된 항목을 역순으로 복원: 공개 이름에 남은 것이 있으면 바인딩을 확인해 제거 → 백업을 공개 이름으로 `link`(이미 있으면 선점으로 중단) → 두 이름 링크 2개 확인 → 백업 이름 격리 제거 → 링크 1개 확인. 모두 복원되면 `delivery/commit`("previous files were restored") 실패, 이때 R-13 (b)~(e)와 동일(실패 표지·journal 유지). **복원이 하나라도 불완전**하거나 소유권을 잃었으면 `delivery/commit-recovery-required`(+`delivery/ownership-lost`): 실패 표지를 쓰지 않고 잠금·journal을 풀지 않고 staging 폴더를 남기며 영수증 `evidence`에 `recoveryDirectory`·`recoverableBackups[]{label,path,…}`·`rollbackErrors[]`를 싣고 stderr에 `Recovery required: delivery backups were retained at "<staging>"`. 소유권 상실이면 되돌리지 않고 즉시 중단한다. 대상 상태 불일치(`output/target-*`)로 실패하면 잠금만 풀고 표지는 쓰지 않는다 | 코드 확인(실행·주입 실패 시험 안 함. [rendering-contracts.md](rendering-contracts.md) R-15와 같은 코드) |
| R-18 | 폴더 잠금. 시작 시 `.archify-delivery-lock.json`(+ 레거시 울타리)을 `open(path,'wx',0o600)`로 만들어 `{schemaVersion,receiptId,pid}`를 쓴다 | `wx` 성공만 소유권. 이미 있는 잠금: 유효한 v1이고 `pid`가 살아 있거나 판별 불가 → `delivery/concurrent-attempt`; `pid`가 죽음 → `delivery/lock-stale`(evidence에 `pid`·`receiptId`); 읽을 수 없음·형식 오류·심볼릭 링크·디렉터리·일반 파일 아님 → `delivery/lock-invalid`; 잠금 경로가 입력과 같은 항목 → `delivery/lock-path-conflict`; 구(pre-namespace) journal 존재 → `delivery/legacy-pending`; 해제 실패 → `delivery/lock-release`; 소유 확인 실패 → `delivery/ownership-lost`. 거부된 시도는 journal·실패 표지·HTML을 **쓰지 않는다**(`stage:"prepare"`). **자동 복구 없음**: 정지한 잠금은 사람이 확인해 보고된 그 잠금 파일만 지우고 다시 실행(문서·supportedFixes). 잠금은 폴더 전체 단위이므로 같은 폴더의 다른 파일명 전달도 직렬화된다. 잠금과 journal의 생성·해제는 `atomic-output.mjs`가 아니라 `bin/archify.mjs`에 구현돼 있고(C-08, C-09), **해제도 소유 확인 뒤 격리 제거**(`quarantineRemoveOwnedDeliveryEntry`)를 쓴다 | 실행 확인(미리 만든 잠금에 대한 거부 12건: 사전 산출물 유무 × 유효 v1 죽은 pid / 산 pid / JSON 아님 / 빈 파일 / 디렉터리 / 레거시. 모두 종료 1·`stage:"prepare"`·잠금 파일 보존·HTML·provenance 바이트 불변. [rendering-contracts.md](rendering-contracts.md) T-10~T-12) / 코드 확인(`wx` 경쟁·해제 실패·그 밖 코드) |
| R-19 | journal | 잠금 소유 후 렌더 이전에 `{schemaVersion:1,command:"deliver",status:"pending",receiptId,input,output}`을 기록한다(기존 journal이 있으면 덮어씀). 성공한 쌍 교체의 마지막에만 지워진다. 실패 처리는 지우지 않는다(R-13·R-14). 존재 자체가 `check`를 막는 안전 장벽(R-10 (1)). journal을 만들지 못하면 `delivery/journal-write`(`stage:"prepare"`), 롤백 불가면 `delivery/journal-recovery-required` | 실행 확인(잔존·덮어씀·삭제), 코드 확인(오류 코드) |
| R-20 | 프로세스가 도중에 죽음(`kill` 등) | 자동 정리는 없다. 가능한 잔재: `.archify-delivery-lock.json`(+레거시 잠금), `<stem>.delivery-pending.json`, `.archify-delivery-XXXXXX/`. 렌더·검사 단계에서 죽으면 공개 HTML·provenance는 이전 그대로(기존 `current` provenance도 그대로이지만 journal 때문에 `check`는 막힘). 쌍 교체에서 ②(백업)가 끝나고 ③(`link`) 전에 죽으면 **HTML과 provenance의 공개 이름이 둘 다 없을 수 있고**, 이전 파일은 staging의 `.previous-output`·`.previous-provenance`에 각각 하드링크로 남는다(HTML 백업 도중이면 HTML만 없다. ③의 두 `link` 사이면 HTML만 새 파일이고 provenance 공개 이름은 없다). 복구는 사람이 한다: 활성 전달이 없음을 확인 → 잠금 제거 → staging 백업을 공개 이름으로 `link`(덮어쓰지 않음) → 성공 `deliver`를 다시 실행하면 journal이 대체·삭제됨. `bin/recover-output.mjs <.archify-remove-id> [--json]`은 **단일 파일 발행**(`render` 등이 쓰는 `publishRegularFileBinding`)이 남긴 `publication-recovery-v1.json`용이며 deliver의 쌍 교체 백업에는 적용되지 않는다 | 코드 확인·문서(실행 안 함). 도구 적용 범위는 코드 확인(호출처 검색) |
| R-21 | 입력 읽기·파싱 실패(없음·JSON 오류) | `stage:"input"`, 코드 `input/read` 또는 `input/json-parse`. 출력은 `CLI 인자 \|\| <type>.html`의 절대 경로. 출력 경로가 `.html`이면 R-13·R-14 규칙으로 실패 표지·journal 처리(기존 HTML이 있으면 표지, 없으면 `absent`+journal). 실측: 존재하지 않는 입력 → `provenance:"absent"`, `x10.delivery-pending.json` 남음 | 실행 확인 |
| R-22 | 성공 후 | 잠금 해제 성공이 먼저. `--open`은 그 뒤. 업데이트 확인 결과를 `receipt.update`에 넣고 출력. staging 폴더는 소유 항목만 지우고 남은 항목이 있으면 경고만. 잠금 해제 실패 시 HTML·provenance는 이미 교체됐으나 `stage:"release"`로 종료 1 | 코드 확인(해제 실패는 실행 안 함), 실행 확인(정상 종료 후 잠금·staging 없음) |
| R-23 | 정규화: 출력이 심볼릭 링크·대소문자·유니코드 정규화·8.3 별칭이면 | 가리키는 물리 파일의 철자로 교체하고 영수증·provenance `output`·사이드 파일 이름에 **물리 경로**를 쓴다(링크 항목은 보존). 실측: `alias.html -> real.html`에 전달하면 `real.html`·`real.delivery.json`만 갱신되고 영수증 `output`은 `real.html` | 실행 확인(심볼릭 링크), 코드 확인(나머지) |

- 불변식:
  - `current` provenance가 있으면 그 `artifact`는 그 시점의 공개 HTML과 바이트가 같다(교체 순서와 롤백 때문; 단, 두 파일은 두 개의 개별 `link`라 잠금·journal이 있는 동안만 쌍 일관성이 보장된다).
  - 공개 HTML은 렌더·검사 실패로는 바뀌지 않는다. 기존 정상 산출물의 정당성은 provenance 쪽이 `failed`로 바뀌어 표시된다.
  - 같은 물리 폴더에서는 동시에 한 전달만 진행된다(잠금).
  - 같은 입력 바이트·같은 렌더러 버전이면 `specification.sha256`은 같다. `receiptId`는 매번 다르다.
- 미결정: 없음(1부 규칙 안에서 구현자가 추측해야 할 항목은 확인 한계 외에 없음. 단, 선행 [rendering.md](rendering.md)가 초안이라 이 스펙도 `draft`).
- 확인 한계: 잠금 경쟁(동시 `wx` 시도)·정지 잠금의 사람 복구·프로세스 중단·쌍 교체 도중 실패·롤백·Windows 호스트·대소문자 구분 파일시스템·`check` 단계 실패 사례(검사가 실패하는 입력)·`--open`·explainer 전달은 **실행하지 않았다**(요청에 따라 코드로만 확인하거나 범위 밖). 미리 만든 잠금 파일이 deliver를 거부하는 경로는 T-17로 실행했다. 실행은 macOS(APFS, 대소문자 무시) · Node v26.10.0 · 설치본(`~/.claude/skills/archify`)에서 했다. 설치본과 레포 `archify/`가 바이트 동일하다는 것은 overview의 `diff -rq`(2026-11-01) 결과를 따랐고 이번에 다시 대조하지 않았다.

### 1.5 필수 코드 참조

Apache-2.0(레포 `LICENSE`, 인용 가능; overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/bin/archify.mjs:13-17,35-74` `DELIVERY_SIDECAR_SUFFIXES`·`deliverySidecarNamespace`·`deliverySidecarPath`·`deliveryProvenancePath`·`deliveryPendingPath`; `renderers/shared/sidecar-path.mjs:1-38` `boundedSidecarStem`·`sidecarStemFromComponent`; `renderers/shared/path-semantics.mjs:685-790` `sidecarNamespaceComponentKey` | 사이드 파일 이름(NFC·파일시스템 탐침 대소문자 접기·`.html` 분리·해시 표지·255 제한) | R-08 |
| C-02 | `archify/bin/archify.mjs:1889-1902` `deliverySuccessProvenance`; `:981-983` `artifactIdentity`; `:5009-5052` 영수증 조립과 `provenanceBytes` | provenance 필드와 해시 대상, 직렬화(2칸 들여쓰기+개행) | R-09 |
| C-03 | `archify/bin/archify.mjs:1904-2179` `inspectDeliveryProvenance` | provenance 검증 순서·스키마 검사·상태·코드 | R-10 |
| C-04 | `archify/bin/archify.mjs:1739-1775` (실패 표지 본문·`writeCapturedDeliveryProvenance`) 와 `:1607-1738` `recordDeliveryFailure` 앞부분 | 실패 표지 필드, 기존 HTML 없음이면 표지를 쓰지 않음(`absent`) | R-13, R-14 |
| C-05 | `archify/renderers/shared/output-path.mjs:256-311,323-357,373-440` `validateNativeOutputPath`·`validateAuthoredOutputPath`·`resolveOutputPath` | 출력 경로 우선순위·검증·코드 | R-03~R-06 |
| C-06 | `archify/renderers/shared/portable-path.mjs:1-8,72-213` `validatePortablePath` | `meta.output` 포터블 경로 규칙(정규식·거부 순서) | R-04 |
| C-07 | `archify/bin/archify.mjs:3236-3469` `commitDeliveryPair` (성공 경로), `:3470-3604` (롤백) | 쌍 교체 알고리즘·롤백 | R-16, R-17 |
| C-08 | `archify/bin/archify.mjs:136-216,520-757` `deliveryLockPath`·`rejectExistingDeliveryLock`·`acquireDeliveryLock` | 폴더 잠금과 레거시 울타리 생성·거부 | R-18 |
| C-09 | `archify/bin/archify.mjs:985-1008` `beginDeliveryAttempt` | journal 본문 | R-19 |
| C-10 | `archify/renderers/shared/atomic-output.mjs:911-993` `backupPublicRegularFileBinding` | 백업(하드링크→공개 이름 제거). `atomic-output.mjs`는 바인딩·격리 제거·백업·publish 기본 연산만 제공하고 잠금·journal·쌍 교체는 `bin/archify.mjs`(C-07~C-09)에 있다. 같은 연산을 단일 파일 경로(`publishRegularFileBinding`)도 쓴다([rendering-contracts.md](rendering-contracts.md) R-13) | R-16 |
| C-11 | `archify/bin/archify.mjs:4400-5300` `commandDeliver` | 단계 순서·실패 분기·정리 | R-11~R-15, R-21~R-23 |
| C-12 | `archify/bin/recover-output.mjs:1-41` | 복구 도구의 범위와 종료 코드(0 recovered/absent, 2 preserved, 1 그 외, 64 인자 오류) | R-20 |

범위 안에서 쓰는 프로젝트 내부 helper: `canonicalFuturePath`/`pathsAlias`(output-path.mjs:11-61)는 R-23·R-06의 "물리 경로 동일성"으로 풀었고, `captureAtomicOutput`/`verifyAtomicOutput`(atomic-output.mjs:1522-1560)는 R-07·R-16의 "대상 스냅샷: 요청 항목·쓰기 슬롯·종류·장치/inode·권한 일치 확인"으로, `captureRegularFileBinding`/`verifyRegularFileBinding`/`quarantineRemoveRegularFileBinding`는 "inode·권한·해시·링크 수가 기대와 같은지 확인하고 격리 폴더 경유로 제거"로 푼다.

### 1.6 수락 사례

출처: 모두 **원본 실행 관찰** — [run-demo.sh](../../../artifacts/archify/spec-demos/delivery/run-demo.sh) → [run-demo.out.txt](../../../artifacts/archify/spec-demos/delivery/run-demo.out.txt), [run-demo2.sh](../../../artifacts/archify/spec-demos/delivery/run-demo2.sh) → [run-demo2.out.txt](../../../artifacts/archify/spec-demos/delivery/run-demo2.out.txt) (설치본, scratch 폴더 `work/`·`work2/`, 입력 [in/](../../../artifacts/archify/spec-demos/delivery/in/)). 아래 `ok.json`은 `examples/agent-run.lifecycle.json`에 `meta.output:"meta-default.html"`을 넣은 것(타입 lifecycle), `bad-schema.json`은 거기서 최상위 `states`를 뺀 것.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-09, R-11 | 빈 폴더. `deliver lifecycle in/ok.json` | 종료 0. `meta-default.html`·`meta-default.delivery.json` 생성, 숨김 항목(`.archify-delivery-*`, 잠금) 없음. stdout 2줄(`delivered lifecycle <abs>/meta-default.html` / `9/9 artifact checks; composition showcase: pass; sha256 ed4d735dc926`). provenance: `schemaVersion 1, status current, command deliver, type lifecycle`, `input`·`output` 절대 경로, `specification{sha256 7df533…, bytes 4003}`, `artifact{sha256 ed4d73…, bytes 847663}` |
| T-02 | R-15 | T-01 직후 같은 명령 | 종료 0. HTML 해시 불변, provenance의 `receiptId`만 다름, 파일 목록 불변 |
| T-03 | R-03 | `deliver lifecycle in/ok.json cli/out.html --json` | 종료 0, stdout JSON `ok:true`, `output`=`<abs>/cli/out.html`, `validation{checksPassed:9,checkCount:9,compositionProfile:"showcase",compositionStatus:"pass",errors:0,warnings:0}`, `update.reason:"disabled"`(`ARCHIFY_UPDATE_CHECK_DISABLED=1`). `cli/out.html`·`cli/out.delivery.json` 생성, `meta.output` 경로는 새로 바뀌지 않음 |
| T-04 | R-13 | T-01 상태에서 `deliver lifecycle in/bad-schema.json --json` (같은 `meta.output`) | 종료 1, stdout `ok:false, stage:"render"`, 진단 `schema/required`, `provenance:"failed"`. `meta-default.html` 해시 불변. `meta-default.delivery.json`은 `status:"failed", stage:"render"`, `artifact`=기존 HTML 해시, `error`에 스키마 메시지. `meta-default.delivery-pending.json` 존재. 이어서 `check meta-default.html --require-provenance --json` → 종료 1, `provenance:"failed"`, 진단 `delivery/provenance-failed`(`evidence.pendingJournal` 경로). 플래그 없는 `check`도 종료 1 |
| T-05 | R-15 | T-04 직후 `deliver lifecycle in/ok-v2.json` (제목만 다른 입력) → `check meta-default.html --require-provenance` | 둘 다 종료 0. journal 없음, provenance `current`에 새 `specification.sha256 d92152…`·`artifact.sha256 f41b81…`·bytes 847672. check 영수증 `provenance:"current"`, `deliveryReceiptId`=새 `receiptId` |
| T-06 | R-14 | 없는 폴더 `fresh/dir/never.html`에 `bad-schema.json` 전달 | 종료 1(stderr `[schema/required] …`). `fresh/dir/never.delivery-pending.json`만 존재, HTML·provenance 없음. 이어 `ok.json`을 같은 경로에 전달(`n/never.html` 사례) → 종료 0, 폴더에 `never.html`·`never.delivery.json`만 |
| T-07 | R-13 | `legacy.html`(provenance 없는 정상 HTML, `check`는 `provenance:"unknown"` 통과)에 `bad-schema.json` 전달, 두 번 | 각 종료 1. `legacy.html` 불변. `legacy.delivery.json`이 `failed` 표지(`artifact`=기존 해시), 두 번째 실패 후 `receiptId`만 갱신, journal 남음 |
| T-08 | R-10 | `deliver ok.json t.html` 성공 후 `echo "<!-- tamper -->" >> t.html`, `check t.html --require-provenance --json` | 종료 1, `provenance:"mismatch"`, `deliveryReceiptId`=전달 영수증 ID, 진단 `delivery/provenance-mismatch`. 플래그 없는 `check t.html`도 종료 1 |
| T-09 | R-06 | `same.html`(=ok.json 복사)에 대해 `deliver lifecycle same.html same.html --json` | 종료 1, `stage:"prepare"`, 코드 `output/input-alias`, 아무 파일도 쓰지 않음. 입력을 가리키는 심볼릭 링크 `in/link.html`을 출력으로 줘도, `./in/../in/ok.json`을 줘도 같은 코드. 입력 `prov.delivery.json`+출력 `prov.html`은 `output/input-alias`("the delivery input") |
| T-10 | R-05 | `out.txt` / `out.htm` / `dir/` / 댕글링 `lnk.html→target.txt` 출력 | 각각 종료 1, 코드 `output/cli-extension` / `output/cli-extension` / `output/native-path-syntax` / `output/cli-resolved-extension`. 출력 폴더·파일 생성 없음 |
| T-11 | R-05 | 출력 `up/../rel/x.html`, 절대 `<abs>/abs/y.html`, 다른 cwd에서 `../up-out.html`, `Mixed.HTML`, `con.html` | 모두 종료 0. `rel/x.html`(`up`은 안 생김), `abs/y.html`, cwd 밖 `up-out.html`, `Mixed.HTML`, `con.html`. 이때 사이드 파일: `up-out.delivery.json`, `mixed.delivery.json`(대소문자 무시 FS), `con.delivery.json` |
| T-12 | R-04 | `meta.output`이 `/tmp/x.html`, `../x.html`, `a\b.html`, `CON.html`, `a/../x.html`, 누락 (각각 CLI 출력 `cli9/<이름>.html`을 줌, `--json`) | 모두 종료 1, `stage:"prepare"`, 코드 `output/meta-absolute`(절대) / 나머지는 `output/meta-path-syntax`. `cli9/` 폴더는 생기지 않는다. `meta.output:"x.txt"`는 `output/meta-extension` |
| T-13 | R-07, R-23 | `real.html` 정상 전달 후 `alias.html -> real.html` 만들고 `deliver ok-v2.json alias.html` | 종료 0, 영수증 `output`=`<abs>/real.html`, `alias.html`은 링크 유지, `real.delivery.json`의 `input`이 `ok-v2.json`, `alias.delivery.json` 없음 |
| T-14 | R-07 | `ln real.html hard.html` 후 `deliver ok.json real.html --json`; 디렉터리 `dirtarget.html`에 전달 | 전자 종료 1, 메시지 "target is hard-linked …", 후자 `output/target-not-regular-file`. 두 경우 모두 기존 파일·journal 변화 없음 |
| T-15 | R-01 | `deliver` / `deliver lifecycle` / `deliver nosuchtype in/ok.json` / 위치 인자 4개 / `--bogus` / `--bogus --json` | 모두 종료 2. 앞 둘과 4개는 stderr에 사용법 표, 알 수 없는 타입은 `Unknown diagram type "nosuchtype". Expected one of: …`, `--bogus`는 `Unknown deliver option "--bogus".`, `--json`이면 stdout JSON `stage:"arguments"`, 코드 `cli/unknown-option` |
| T-16 | R-21 | 존재하지 않는 입력 `in/nope.json`, 출력 `x10.html`, `--json` | 종료 1, `stage:"input"`, `provenance:"absent"`, `output`=`<abs>/x10.html`, `x10.delivery-pending.json`만 남음. 깨진 JSON 입력은 `input/json-parse`, 종료 1 |
| T-17 | R-18 | 출력 폴더에 `{"schemaVersion":1,"receiptId":<uuid4>,"pid":<죽은 PID>}` 잠금 파일이 있음(사전 산출물 없음 / 정상 HTML+provenance 있음 두 경우). 출처: 원본 실행 관찰([rendering-contracts.md](rendering-contracts.md) T-10~T-12, [03-lock.txt](../../../artifacts/archify/spec-demos/rendering/contracts/out/03-lock.txt)) | 종료 1, `stage:"prepare"`, `delivery/lock-stale`(evidence에 `pid`, `receiptId`), 잠금·HTML·provenance 모두 불변(해시 일치), journal·실패 표지·staging을 만들지 않는다. 같은 조건에서 PID가 살아 있으면 `delivery/concurrent-attempt`, JSON 아님·빈 파일·디렉터리는 `delivery/lock-invalid`, 레거시 `a.delivery-lock.json`(죽은 pid)은 `delivery/lock-stale` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (archify@a406594 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `archify/bin/archify.mjs:4400-4421` `commandDeliver` 인자 해석, `:2227-2241` `fail`·`rejectCliArgument`, `:2243-2255` `rendererPath`, `:2310-2395` `extractQualityArgs`·`extractRepoRootArgs`, `:2397-2414` `extractExplainerWritingArgs`, `:7283-7288` 최상위 오류 처리, `:2212-2225` `usage` | 코드를 읽고 T-15를 실행. `--quality`·`--repo-root` 값 오류 경로는 코드만 |
| R-02 | `bin/archify.mjs:5009-5052,5252-5278` 성공 영수증·출력, `:4289-4312` `reportArtifactFailure`, `:2787-2795` `formatDiagnostics`, `bin/delivery-update.mjs:9-47` `unavailable`·`normalize` | 성공·실패 JSON을 T-03·T-04·T-15에서 읽음. `evidence`·`open` 필드는 해당 경로 코드만 |
| R-03 | `bin/archify.mjs:4504-4551` 경로 해석, `output-path.mjs:373-391` (C-05), `:323-357` | T-03(CLI 우선), T-12(누락 거부). explainer 예외는 `:4506` 조건식만 읽음 |
| R-04 | `portable-path.mjs:72-213` (C-06), `output-path.mjs:76-96,323-357` | T-12에서 6종 + 확장자 실행. 나머지(URI·제어 문자·255 초과 등)는 코드 |
| R-05 | `output-path.mjs:256-311,412-434` (C-05) | T-10·T-11 실행. Windows 분기는 코드만 |
| R-06 | `output-path.mjs:393-410`, `bin/archify.mjs:4582-4617,5084-5120` | T-09 실행 |
| R-07 | `bin/archify.mjs:4548-4573,4619-4660,2543-2582`, `atomic-output.mjs:1522-1560` | T-13·T-14 실행. `output/target-changed`·`target-indeterminate`는 코드만 |
| R-08 | C-01 | T-11·T-01 실행(소문자 접힘 포함). 구분 FS·긴 이름·NFC는 코드만 |
| R-09 | C-02 | T-01·T-02·T-05 실행(JSON 전문 확인) |
| R-10 | C-03 | T-04·T-05·T-07·T-08 실행. `locked`·`invalid`·`unsupported` 분기는 코드만 |
| R-11 | C-11 `bin/archify.mjs:4400-5300` (정확한 위치: 읽기 4487, 경로 4504-4617, 스냅샷 4619-4660, staging 4665, 잠금 4703, journal 4782, 스냅샷 고정 4833, 렌더 4870, 검사 4904, provenance 후보 5050, 경로 재해석 5085, 교체 5124, 해제 5214, 열기 5235, 출력 5252) | 코드 읽음. 정상 종료 후 목록으로 결과만 간접 확인 |
| R-12 | `bin/archify.mjs:4870-4875,4895-4903,2259-2295` `runNode`·`artifactCheckMaxBuffer`, `:4904-4925` | 코드. 입력 변경 중 동작은 시험하지 않음 |
| R-13 | `bin/archify.mjs:4313-4363` `writeDeliveryFailureReceipt`, `:1607-1876` (C-04), `:4880-4889` 렌더 실패 호출 | T-04·T-07 실행(render 단계). 다른 단계는 모두 같은 `reportDeliveryFailure`를 호출함을 코드로 확인 |
| R-14 | `bin/archify.mjs:1750-1763`(artifact 부재 시 `status:'absent'`), `:497-518` `releaseDeliveryOwnership`(journal 비삭제) | T-06·T-16 실행 |
| R-15 | `bin/archify.mjs:3236-3469`, `:985-1008` | T-02·T-05 실행 |
| R-16 | C-07, C-10, `bin/archify.mjs:3295-3452`(단계별 `for` 6개: 검증·바인딩 → 백업 → `link` → 링크 2 확인 → 후보 격리 제거 → 링크 1 확인) | 코드만(성공 결과는 T-01~T-05). 직접 코드를 다시 읽어 [rendering-contracts.md](rendering-contracts.md) D-10 보정과 일치 확인 |
| R-17 | `bin/archify.mjs:3453-3614`(두 롤백 루프), `:2521-2542` `deliveryCommitRecoveryDiagnostic`, `:5133-5185` | 코드만 |
| R-18 | C-08, `bin/archify.mjs:497-518` `releaseDeliveryOwnership`(격리 제거 사용), `references/delivery-contract.md:15-100`(잠금 표) | 코드와 문서 대조(일치). 미리 만든 잠금 거부는 T-17로 실행 확인. 잠금 경쟁(`wx` 동시 시도)·해제 실패는 실행 안 함 |
| R-19 | C-09, `bin/archify.mjs:3452-3462` (`quarantineRemoveOwnedDeliveryEntry` journal 삭제) | T-04·T-06 실행(잔존·삭제) |
| R-20 | `references/delivery-contract.md:100-145`, C-12, [rendering-contracts.md](rendering-contracts.md) 1.3 F(중단 지점별 사후 상태), `atomic-output.mjs:586-700,1120-1330`(기록 생성은 `publishRegularFileBinding`만; `grep`으로 호출처 확인: `cli.mjs:276`, `finalize.mjs:74`, `preview.mjs:687`, `render-explainer.mjs:37`) | 코드·문서만. deliver 쌍 교체가 기록을 남기지 않는다는 것은 `backupPublicRegularFileBinding`(:911-993)에 기록 쓰기가 없음으로 확인 |
| R-21 | `bin/archify.mjs:4486-4512,2646-2662` `inputDiagnostic` | T-16 실행 |
| R-22 | `bin/archify.mjs:5214-5300` | 정상 경로 실행. 해제 실패는 코드만 |
| R-23 | `bin/archify.mjs:4527-4533,108-116` `canonicalExistingDeliveryOutput`, `output-path.mjs:11-37` | T-13 실행 |
| T-01~T-16 | 실행 기록 링크는 1.6 | 실제 출력과 대조 |
| 문서와 구현 차이 | (1) overview feature map·q2는 "실패하면 직전 정상 파일 유지"로 적었으나 구현은 **HTML 바이트만** 유지하고 provenance를 `failed`로 바꾸며 journal을 남겨 이후 `check`를 막는다(T-04). `delivery-contract.md`의 "writes a new status: failed sidecar and leaves the journal"과는 일치. (2) overview는 "원자 교체"로 표현했으나 구현은 rename 교체가 아니라 백업 하드링크→공개 이름 제거→`link` 순서이며 그 사이에 공개 이름(HTML·provenance 둘 다)이 잠시 없다. 단일 파일 경로(`render`)가 같은 기본 연산을 쓰는 것은 [rendering-contracts.md](rendering-contracts.md) 1.3 D 참조. 문서도 "not crash-atomic replacement"라고 명시. (3) overview 2행 진입점은 `scripts/recover-output.mjs` 류라 했으나 실제 위치는 `bin/recover-output.mjs`이고 deliver 쌍 교체의 백업에는 적용되지 않는다. (4) q3는 "`meta.output`은 필수"라 썼으나 explainer 타입은 선택(`archify.mjs:4506`). (5) `delivery-contract.md`의 "Windows reserved name 금지"는 `meta.output`에만 적용되고 POSIX CLI 경로 `con.html`은 허용된다(T-11, 문서도 "POSIX CLI paths retain POSIX filename rules"). (6) 입력 파일을 읽지 못한 경우에도 구현은 출력 경로를 `CLI 인자 || <type>.html`로 보고 잠금·journal·실패 표지 기록을 시도한다(R-21). 문서는 이 경우를 따로 설명하지 않는다. | 위 각각 코드 줄과 실행으로 확인 |

### 2.2 코드 읽는 순서
`commandDeliver`(4400)를 위에서 아래로 읽는다: 4400-4520(인자·입력), 4504-4660(경로·스냅샷), 4665-4830(staging·잠금·journal), 4830-5100(렌더·검사·영수증·provenance 후보), 5100-5300(교체·해제·출력). 그다음 `acquireDeliveryLock`(520) → `commitDeliveryPair`(3236) → `backupPublicRegularFileBinding`(atomic-output 911). provenance 파일은 쓰기 `deliverySuccessProvenance`(1889), 실패 표지 `recordDeliveryFailure`(1607), 읽기 `inspectDeliveryProvenance`(1904). 경로 쪽은 `output-path.mjs` → `portable-path.mjs` → `path-semantics.mjs`. 구현 전략: 모든 공유 상태 변경(잠금·journal·교체·롤백) 직전에 소유권(잠금 inode·내용, journal inode·내용)을 다시 확인하고, 파일 교체는 항상 inode·해시·링크 수를 바인딩해 검증한다.

## 적용 메모
없음.
