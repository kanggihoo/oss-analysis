---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/validator.mjs
  - archify/renderers/shared/diagnostics.mjs
  - archify/renderers/shared/repository-evidence.mjs
  - archify/renderers/shared/repository-location.mjs
  - archify/renderers/shared/output-path.mjs
  - archify/renderers/shared/portable-path.mjs
  - archify/renderers/shared/i18n.mjs
  - archify/renderers/shared/engineering-profiles.mjs
  - archify/renderers/shared/generated-validators.mjs
  - archify/scripts/generate-validators.mjs
  - archify/schemas/common.schema.json
  - archify/schemas/README.md
  - archify/schemas/architecture.schema.json
  - archify/bin/archify.mjs
  - archify/locales/manifest.json
  - archify/renderers/architecture/render-architecture.mjs
  - archify/renderers/workflow/workflow-compiler.mjs
  - archify/renderers/sequence/render-sequence.mjs
  - archify/renderers/dataflow/dataflow-compiler.mjs
  - archify/renderers/lifecycle/render-lifecycle.mjs
  - archify/renderers/erd/render-erd.mjs
  - archify/renderers/tree/render-tree.mjs
  - archify/renderers/class/render-class.mjs
  - archify/renderers/timeline/render-timeline.mjs
  - archify/renderers/waterfall/render-waterfall.mjs
depends: []
status: ready
---

# 입력 로드·검증

> 렌더러 프로세스가 받은 JSON 파일 경로(와 선택적 `--repo-root`)를 읽어 파싱 → 출력 경로 형식 → 스키마 → 로케일 → 관계 ID 중복 → 엔지니어링 프로파일 → 저장소 근거 순으로 검증하고, 통과하면 `{diagram, template, outPath, sourceEvidence}`를 돌려주며, 실패하면 진단 객체를 담은 오류로 프로세스를 끝낸다. 이 스펙은 진단 객체와 공통 `meta` 스키마 계약도 소유한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
렌더러(`render-<type>.mjs`)가 시작하면 `loadDiagram`이 아래를 **이 순서로** 실행한다. 각 단계는 실패하면 거기서 던지고 다음 단계로 가지 않는다(단계 안에서는 같은 종류의 문제를 모아서 한 번에 던진다).

1. 진단 경계 설치(`installRendererDiagnosticBoundary`) → 입력 파일을 UTF-8로 읽는다. 실패: `input/read`.
2. `JSON.parse`. 실패: `input/json-parse`.
3. `meta.output`이 있으면(`undefined`가 아니면) 형식을 검사한다. 실패: `output/meta-*`.
4. 스키마 검증(타입별 ajv 생성 검증기). 실패: `schema/<ajv keyword>` 여러 개.
5. 로케일 적용(`meta.locale`이 있을 때만). 실패하지 않는다. 경고만 남긴다.
6. 관계 ID 중복 검사. 실패: `relationship/duplicate-id`.
7. 엔지니어링 프로파일(`architecture` + `meta.engineering_profile == "deployment-ownership"`일 때만). 실패: `engineering/*`.
8. 저장소 근거 검증(`sources` 또는 `meta.repository`가 있을 때만; `--repo-root`가 필요). 실패: `repository-evidence/*`. 결과는 `sourceEvidence`(없으면 `null`).
9. (이 스펙의 범위 밖) 템플릿 읽기와 출력 경로 해석 후 반환. 해석 실패는 `output/*`(1.2).

통과한 뒤 타입별 렌더러가 레이아웃·참조 검증을 이어서 한다(행 6).

### 1.2 범위·통합 지점 [필수]
- 제공: 위 1~8단계, 진단 객체 계약(1.3 B), 공통·타입별 스키마의 `meta` 계약(1.3 C), 저장소 근거 검증(1.3 D).
- 제외:
  - 타입별 배치·참조 검증(노드 ID 중복, 끝점 존재, 겹침 등)은 `loadDiagram` 이후 각 렌더러 안에서 한다(위치는 1.3 C 표). 행 6.
  - 단계 9: 템플릿 읽기(`assets/template.html`)와 `resolveOutputPath`. 출력이 입력과 같은 파일이면 `output/input-alias` 같은 `output/*`가 여기서 나고, 파일시스템 오류는 `output/write`다. 행 7이 소유한다. 이 스펙은 `meta.output`의 *형식*(3단계)만 소유한다.
  - 영수증·`--json` 영수증 모양, 품질 게이트에서 경고를 실패로 바꾸는 규칙(행 4·7).
  - explainer 문서 검증(행 10). 단 `verifyRepositoryEvidence`는 explainer가 재사용한다(`explainer/sources.mjs:220,272`).
  - `validate`·`deliver` 명령 자체: 공개 CLI는 렌더러를 자식 프로세스로 띄운다. `validate`는 입력 검증 뒤 임시 폴더에 전체 렌더와 정적 검사까지 한다(`bin/archify.mjs:6963`).
- 외부 의존·선행 계약: 선행 스펙 없음. 호출자가 제공하는 것: 입력 파일 경로(`argv[2]`), 환경변수 `ARCHIFY_REPO_ROOT`(공개 CLI가 `--repo-root`를 절대경로로 바꿔 넣는다), `ARCHIFY_DIAGNOSTIC_FORMAT=json`(공개 CLI가 자식에게 설정), 로컬 `git` 실행 파일(저장소 근거를 쓸 때만), 패키지의 `locales/`.
- 소유 상태·부작용: 파일 쓰기 없음. 프로세스 전역 상태 3개: 로케일 카탈로그 맵(`registerLocale`), 기록된 진단 목록(JSON 모드), `uncaughtException` 핸들러 1개. `git`은 읽기 명령만 실행하고 네트워크를 쓰지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### A. loadDiagram

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `loadDiagram({rendererDir, diagramType, defaultExample, argv})` | `argv[2]`: 입력 JSON 경로(없으면 `<skillRoot>/examples/<defaultExample>`), `argv[3]`: 출력 경로 → `{diagram, template, outPath, sourceEvidence}` | 동기 함수. `diagramType`은 10종(`architecture workflow sequence dataflow lifecycle erd tree class timeline waterfall`). `diagram`은 파싱된 객체 그대로(변형 없음). `sourceEvidence`는 1.3 D 모양 또는 `null`. |
| `ARCHIFY_REPO_ROOT` | 환경변수, 절대경로 | 공개 CLI의 `--repo-root <p>` 또는 `--repo-root=<p>`가 `path.resolve`된 값. 값이 없거나 빈 문자열이거나 `--`로 시작하면 CLI가 종료 코드 2(stderr 한 줄 `--repo-root requires a repository path.`). 렌더러를 직접 실행할 때는 환경변수만 있다. |
| 로케일 카탈로그 | `meta.locale`(string), `meta.translations`(map) | 1.4 R-07. |

#### B. 진단 객체 (공유 계약 a)

다른 행(finalize, deliver, 검증 게이트, 수리 루프)은 이 절을 링크해 쓴다.

**모양.** 모든 진단은 `normalizedDiagnostic`을 거쳐 아래 필드만 가진다(C-04).

| 필드 | 타입 | 규칙 |
|---|---|---|
| `code` | string | `<표면>/<kebab-reason>`. 비었거나 없으면 `internal/unclassified`. 수리 루프가 분기하는 안정 키. |
| `severity` | `"error"` \| `"warning"` | 정확히 `"warning"`이 아니면 `"error"`. |
| `message` | string | trim. 비면 `Archify could not classify this failure.` |
| `subject` | map | 무엇에 대한 진단인지. `undefined` 값 항목은 제거, 객체가 아니면 `{}`. 관례 키: `path`(JSON 포인터), `diagramType`, `collection`, `nodeId`, `identity`, `input`, `output`, `repoRoot`, `surface`. |
| `evidence` | map | 판단 근거 값. 같은 정리 규칙. |
| `supportedFixes` | list of string | 각 항목 trim, 빈 문자열 제거, 중복 제거(첫 등장 순). 배열이 아니면 `[]`. |
| `suppresses` | list of string, 선택 | 배열이면 trim·빈 값 제거·중복 제거해서 포함. 없으면 키 자체가 없다. |

**정렬 규칙.** 진단 목록은 정렬하지 않는다. 발생 순서가 곧 순서다: 스키마는 ajv가 낸 순서, 엔지니어링 프로파일은 코드의 발생 순서(경계 종류 → 컴포넌트 → security-group 경계 → 연결), 저장소 근거는 노드 순서 → `sources` 순서. JSON 모드에서는 이전에 *기록된* 진단(경고 포함)이 앞에 오고, 같은 `code + message + JSON(subject)`는 한 번만 남는다(R-21).

**code 접두사.**

| 접두사 | 발생 위치 | 이 스펙 범위 |
|---|---|---|
| `input/` (`read`, `json-parse`) | `loadDiagram` | 소유 |
| `output/` | `meta-absolute`, `meta-path-syntax`, `meta-extension`, `meta-resolved-extension`, `meta-outside-cwd`(3단계) / `native-path-syntax`, `cli-extension`, `cli-resolved-extension`, `input-alias`, `target-alias`, `write`, `target-*`(9단계 이후) | 앞 5개만 소유 |
| `schema/<ajv keyword>` | `validateSchema` (`required`, `additionalProperties`, `type`, `enum`, `const`, `pattern`, `minimum`, `maximum`, `minItems`, `maxItems`, `minLength`, `maxLength` 등) | 소유 |
| `i18n/` (`invalid-translation`, `locale-fallback`, `translation-coverage`) | 5단계, 항상 `warning` | 소유 |
| `relationship/duplicate-id` | 6단계 | 소유 |
| `engineering/` (`deployment-*` 7종) | 7단계 | 소유 |
| `repository-evidence/` | 8단계 | 소유 |
| `<타입>/…`, `layout/constraint`(기본값), `composition/…` | 타입별 렌더러 | 행 6 |
| `internal/unclassified`, `internal/renderer-process` | 분류되지 않은 실패 | 소유(경계 규칙) |
| `cli/`, `delivery/`, `artifact/`, `finalize/`, `explainer/`, `delta/` | 공개 CLI, 게이트 | 다른 행 |

**생성 규칙.**

| 함수 | 동작 |
|---|---|
| `throwDiagnosticError(message, diagnostics)` | 각 진단을 `recordDiagnostic`(JSON 모드일 때만 기록) → `Error(message)`에 `archifyDiagnostics = diagnostics.map(normalizedDiagnostic)`를 달아 던진다. |
| `throwDiagnosticProblems(prefix, problems, {code='layout/constraint', subject, diagnostics})` | `problems`(문자열 목록)마다 진단 하나. 같은 `message`를 가진 상세 항목(`diagnostics`)을 **발생 순서대로** 하나씩 소비하고, 없으면 이미 기록된 같은 메시지의 진단을 쓰고, 그것도 없으면 `{code, severity:'error', message, subject, evidence:{}, supportedFixes:[]}`. 오류 메시지는 `<prefix>:\n- <문제1>\n- <문제2>`. |
| 스키마·근거·프로파일 | 위 함수를 직접 부른다. 근거는 `evidenceFailure(code, message, {subject, evidence, supportedFixes})`로 `subject.surface = 'repository-evidence'`를 항상 붙인다. 출력 경로는 `OutputPathError`가 같은 모양의 `archifyDiagnostics`를 가진다. |

**종료 코드와 stderr.** 렌더러 프로세스는 `uncaughtException` 핸들러로 실패를 번역한다(C-07).

| 상황 | stderr | 종료 코드 |
|---|---|---|
| 텍스트 모드(기본), 진단이 달린 오류 | 첫 줄 `error.message`(여러 줄 가능), 이어서 진단마다 한 줄 `[<code>] <message>` + (`supportedFixes`가 있으면) ` Fix: <fix1>; <fix2>.` | 1 |
| JSON 모드(`ARCHIFY_DIAGNOSTIC_FORMAT=json`) | 한 줄 JSON `{"schemaVersion":1,"ok":false,"source":"renderer","error":<message>,"diagnostics":[...]}` | 1 |
| 진단 없는 일반 오류, 텍스트 모드 | Node 기본 스택(핸들러가 다음 tick에 다시 던짐) | Node 기본(1) |
| 진단 없는 일반 오류, JSON 모드 | 위 JSON에 진단 1개 `internal/unclassified`(`subject.input` = `argv[2]` 절대경로, `evidence.errorName`) | 1 |
| 경고(`severity: warning`) | 텍스트: `archify: <message>`를 stderr로(`console.warn`), 실패하지 않음. JSON: 기록만 하고 stderr에 안 씀 | 0 |

공개 CLI(`validate` 등)는 같은 텍스트 형식(`formatDiagnostics`)을 자기 stderr에 쓰고, `--json`이면 stdout에 영수증을 쓴다(영수증 모양은 행 4·7). 영수증의 `stage`는 진단 중 `input/`으로 시작하는 `code`가 하나라도 있으면 `"input"`, 아니면 `"render"`다(`bin/archify.mjs:7015,7049,7085`).

#### C. 스키마 공통 meta 계약 (공유 계약 b)

`schemas/<type>.schema.json`(10종 + `explainer`)이 타입별 필드의 원본이고, 공통 정의는 `common.schema.json`의 `$defs`다(C-09~C-13). 모든 스키마는 최상위·`meta`·하위 객체에 `additionalProperties: false`라 모르는 필드는 `schema/additionalProperties`로 거부된다.

**공통 meta 필드** (타입별로 있고 없음은 아래 표):

| 필드 | 정의 | 제약 |
|---|---|---|
| `title` | string | `minLength 1`, 최대 없음. 모든 타입 필수. |
| `subtitle` | string | 제약 없음. |
| `locale` | `$defs/locale` | 정규식 `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`, `maxLength 35`. |
| `translations` | `$defs/translations` | 키 정규식 `^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)*$`, 값 string 길이 1~400, 항목 최대 600개. |
| `output` | architecture·workflow·sequence·dataflow·lifecycle: `$defs/portableOutputPath`; erd·tree·class·timeline·waterfall: 평범한 `string` | 형식 규칙은 R-04 (타입과 상관없이 같은 코드가 검사). |
| `animation` | enum `trace` \| `none` | |
| `visual_preset` | enum `classic` \| `signal-flow` \| `blueprint` \| `editorial` | |
| `quality_profile` | enum `standard` \| `showcase` | 렌더 시 해석은 행 6·4. |
| `repository` | `$defs/repository` | `url`(string, 길이≥1)·`revision`(정규식 `^[a-fA-F0-9]{40}$`) 필수, `provider` enum `github`\|`gitee`\|`gitlab`, `link_mode` enum `web`\|`local-only`. |
| `views` | `$defs/guidedViews` | 은퇴한 필드. 검증은 통과하지만 렌더러가 무시한다. 최대 5개, `label` ≤48자, `note` ≤140자, `focus` ≥1개 ID. |
| `legend` | `{mode: auto\|all\|hidden, entries: {<kind>: {label 1~80자, visible bool}}}` | `entries` 키는 타입별 고정 집합(`schemas/README.md`). |
| `viewBox` | `[w,h]` 숫자 2개 | 최소값은 타입별(architecture: 320×240). |

**타입별로 다른 점** (나머지 필드는 `schemas/<type>.schema.json`이 원본):

| 타입 | `schema_version` | 최상위 필수 배열 | `meta` 필수 | `meta`에 없는 공통 필드 | 타입 전용 `meta` |
|---|---|---|---|---|---|
| architecture | `1` | `components` | `title`, `output` | | `engineering_profile`(enum `deployment-ownership`) |
| workflow | `1` 또는 `2` | `lanes`, `nodes`, `edges` | `title`, `output` | | |
| sequence | `1` | `participants`, `messages` | `title`, `output` | | `column_fit` |
| dataflow | `1` | `stages`, `nodes`, `flows` | `title`, `output` | | |
| lifecycle | `3` | `mainPath`, `states`, `transitions` | `title`, `output` | `viewBox` | |
| erd | `1` | `entities` | `title` | | |
| tree | `1` | `nodes` | `title` | `legend` | |
| class | `1` | `types` | `title` | | |
| timeline | `1` | `events` | `title`, `evidence` | `legend`, `viewBox` | `evidence`(enum `observed`\|`illustrative`), `timezone` |
| waterfall | `1` | `spans` | `title`, `evidence` | `legend`, `viewBox` | `evidence`(enum `measured`\|`illustrative`), `unit` |

모든 스키마는 `diagram_type`을 해당 문자열 `const`로 고정한다. `engineering_profile`은 architecture에만 있어 다른 타입에 쓰면 `schema/additionalProperties`다.

**공유 정의 목록**(타입별 필드가 `$ref`): `id`(정규식 `^[a-zA-Z][a-zA-Z0-9_-]*$`), `side`(left/right/top/bottom), `componentType`(frontend backend database cloud security messagebus external), `variant`(default emphasis security dashed), `nodeIcon`, `brandMark`, `point`, `relationshipWidth`(최소 0.5), `cards`(`dot` enum cyan/emerald/violet/amber/rose/orange/slate), `sourceReferences`. 값은 C-11~C-13.

**ID 교차 계약 함수 위치.** `loadDiagram`이 하는 것은 관계 `id` 중복 하나뿐이다(R-08). 노드 ID 중복·끝점 존재 같은 참조 계약은 `loadDiagram` 이후 타입별 렌더러가 던진다(R-09). 관계 컬렉션은 C-03의 표와 같다(tree·timeline·waterfall은 관계 컬렉션이 없다).

| 타입 | 관계 `id` 중복(`loadDiagram`) | 노드 컬렉션 | 참조·중복 검증 함수(`renderers/` 기준, 렌더러 단계) | 대표 code 또는 메시지 |
|---|---|---|---|---|
| architecture | `connections` | `components` | `architecture/render-architecture.mjs:487` `validateArchitecture` (ID 중복 :494, 경계 `wraps` :635, 끝점 :801·:825) | `architecture/unknown-endpoint`, `layout/constraint` |
| workflow | `edges` | `nodes` | `workflow/workflow-compiler.mjs:2693` `validateWorkflow`(ID 중복 :2737-2748, 끝점 :2837), v2는 `:3038` `validateReadableInputsBeforeRouting`가 먼저(:3068, :3094, :3120, :3162). 컴파일러가 `validateSchema`·`validateCrossCollectionContracts`를 다시 호출(:1389) | `workflow/duplicate-lane-id`, `workflow/duplicate-node-id`, `workflow/unknown-edge-endpoint`, `workflow/unknown-node-lane`, `workflow/unknown-endpoint` |
| sequence | `messages` | `participants` | `sequence/render-sequence.mjs:554` `validateSequence`(:557, 끝점 :607, 활성 :906) | `sequence/unknown-endpoint` |
| dataflow | `flows` | `nodes` | `dataflow/dataflow-compiler.mjs:251` `validateDataflow`(:253, 끝점 ~:410-427) | `dataflow/unknown-endpoint` |
| lifecycle | `transitions` | `states` | `lifecycle/render-lifecycle.mjs:861` `validateStructure`(:869-894) | `lifecycle/duplicate-state`, `lifecycle/unknown-main-path-state`, `lifecycle/unknown-endpoint`, `lifecycle/main-path-gap` |
| erd | `relationships` | `entities` | `erd/render-erd.mjs:1074` `validateEr`(:1155, :1204-1233) | 메시지만(문제 문자열) |
| class | `relationships` | `types` | `class/render-class.mjs:652` `validateClassDiagram`(:663, :706-710), 상속 순환 `:623` | 메시지·상세 |
| tree | — | `nodes` | `tree/render-tree.mjs:55` `validateStructure` | `tree/duplicate-id`, `tree/missing-parent`, `tree/root-count`, 순환 |
| timeline | — | `events` | `timeline/render-timeline.mjs:75-106`(모듈 최상위 블록) | `timeline/duplicate-lane-id`, `timeline/duplicate-id`, `timeline/unknown-lane`, `timeline/invalid-timestamp`, `timeline/invalid-timezone` |
| waterfall | — | `spans` | `waterfall/render-waterfall.mjs:52-101`(모듈 최상위 블록) | `waterfall/duplicate-id`, `waterfall/missing-parent`, `waterfall/cycle` |

**엔지니어링 프로파일이 적용되는 타입**: architecture 하나, `engineering_profile == "deployment-ownership"`일 때만(R-10). 다른 값이나 타입은 7단계가 아무것도 하지 않는다(스키마가 먼저 거른다).

#### D. 저장소 근거 데이터

| 데이터 | 모양 | 의미·제약 |
|---|---|---|
| `meta.repository` | `{url, revision, provider?, link_mode?}` | 1.3 C 표. `url`은 `git remote get-url origin`이 알려 주는 원격 주소 정체성(로컬 경로 아님). `link_mode` 기본 `web`. |
| 노드의 `sources` | list(1~3개) of `{path, line?, end_line?, label?}` | `path` 길이 1~240, `line`·`end_line` 정수 ≥1, `label` 길이 1~48. `sources`가 붙는 노드 컬렉션: architecture `components`, workflow·dataflow·tree `nodes`, sequence `participants`, lifecycle `states`, erd `entities`, class `types`, timeline `events`, waterfall `spans`(C-20). |
| `verifyRepositoryEvidence` 결과 | `{schemaVersion:1, verified:true, repository:{url, revision, shortRevision, label, href \| linkMode}, referenceCount, nodes:{<nodeId>:[{path, line?, endLine?, label?, href?}]}}` 또는 `null` | `revision`은 소문자. `label`은 github이면 `owner/repo`, 아니면 `url`에서 스킴(`https://`, `ssh://git@`, `git@`)을 뗀 것. `link_mode == web`이면 `repository.href`와 소스마다 `href`, `local-only`이면 `repository.linkMode: "local-only"`뿐. `nodes`는 `sources`가 있는 노드만, 같은 `id`가 둘이면 뒤의 것이 덮어쓴다. |

**출력 경로 형식**(`portable-path.mjs` profile `output`, 3단계) 거절 사유를 검사 순서대로: 문자열 아님 `type`, 빈 문자열 `empty`, 절대경로(`/`·`\`로 시작 또는 `C:/`·`C:\`) `absolute`, 드라이브 상대(`C:x`) `drive-relative`, URI 스킴(`^[A-Za-z][A-Za-z0-9+.-]*:`) `uri`, 역슬래시 포함 `backslash`, 이후 `/`로 나눈 세그먼트마다 순서대로: 빈 세그먼트 `empty-segment`, `.`·`..` `dot-segment`, 제어문자 `control`, 짝 없는 서로게이트 `unpaired-surrogate`, `:` 포함 `windows-ads`, `<>"|?*` 포함 `windows-invalid-character`, 끝이 `.`·공백 `windows-trailing-dot-space`, Windows 예약 이름(`CON PRN AUX NUL CONIN$ CONOUT$ COM1-9 LPT1-9`, 위첨자 숫자 포함, 확장자 앞까지) `windows-reserved-name`, `~숫자` 8.3 모양 `windows-short-name`, UTF-8 255바이트 또는 UTF-16 255단위 초과 `component-too-long`.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `loadDiagram` 실행 | 1.1의 1→8 순서로 실행되고 앞 단계가 실패하면 뒤 단계는 실행되지 않는다. 실패는 진단 객체를 단 오류로 전달된다. 예: 나쁜 `meta.output`과 스키마 위반이 같이 있으면 `output/meta-absolute`만 나온다(스키마 오류는 안 나옴). | 실행 확인 (T-04) |
| R-02 | 입력 파일을 읽을 수 없음(파일시스템 오류만) | `input/read`, `subject.input`=절대경로, `evidence.{systemCode, reason}`, fix `provide one readable JSON input file`. 파일시스템 오류가 아닌 예외는 그대로 전파(`internal/unclassified`). | 실행 확인 (T-02) |
| R-03 | 내용이 JSON이 아님(`SyntaxError`) | `input/json-parse`, 메시지 `Input JSON could not be parsed: <JSON.parse 메시지>`, `evidence.reason`. 공개 CLI `validate`는 렌더러를 띄우기 전에 자기가 파싱하므로 `message`에 접두사가 없고 `error` 줄도 파싱 메시지뿐이다. code는 같다. | 실행 확인 (T-01) |
| R-04 | `meta.output !== undefined` (타입 무관) | 형식 검사(1.3 D 사유 목록). 절대경로면 `output/meta-absolute`, 다른 형식 위반은 `output/meta-path-syntax`(`evidence.reason`과 해당되면 `segmentIndex`·`segment`·`utf8Bytes`·`utf16CodeUnits`·`limit`). 통과하면 `path.posix.extname`이 대소문자 무시 `.html`이 아니면 `output/meta-extension`, 현재 작업 디렉터리(cwd) 기준 해석 후 심볼릭 링크를 따른 확장자가 `.html`이 아니면 `output/meta-resolved-extension`, cwd 밖이면 `output/meta-outside-cwd`. 값이 문자열이 아니면(`null`, 숫자) `type` 사유로 `output/meta-path-syntax`(코드 확인). 모두 `subject.path = "/meta/output"`(마지막 둘은 `output` 위주). 없으면(erd 등) 검사하지 않는다. | 실행 확인(절대·`..`·확장자·`a:b.html`: T-03~T-05) / 코드 확인(resolved·outside-cwd) |
| R-05 | 스키마 위반 | ajv `allErrors` 모드라 위반을 모두 모아 한 번에 던진다. 진단마다 `code=schema/<keyword>`, `subject={diagramType, path=<instancePath 또는 "/">, identity?}`, `evidence={keyword, expected=<해당 스키마 조각>, ...ajv params}`, `message="<path> [(id/label: "<값>")] <ajv 메시지>"`(params 없음). `supportedFixes`는 keyword별 고정 문구: `additionalProperties`→`remove unsupported property "<이름>"`, `required`→`add required property "<이름>"`, `type`→`use "<type>" at <path>`, `enum`→`choose one of the allowed values`, `pattern`→`match the required pattern "<p>"`, `minimum`/`maximum`→`use a value >=/<= <limit>`, `minItems`/`maxItems`/`minLength`/`maxLength`→`provide at least/at most <n> item(s)/character(s)`, 그 밖은 `[]`. 오류 메시지는 `<type> schema validation failed:\n` + 위반마다 `  <path> [(id/label: "…")] <ajv 메시지> <params JSON>`. | 실행 확인 (T-06) |
| R-06 | R-05에서 `id/label`을 붙이는 규칙 | `instancePath`를 세그먼트로 따라 내려가며(숫자 세그먼트는 배열 인덱스) 만나는 **배열이 아닌 객체**마다 `id ?? label`이 null이 아니면 `String(그 값)`을 힌트로 기억한다. 마지막으로 기억한 값이 사용된다(더 안쪽 객체에 `id`·`label`이 없으면 바깥 힌트가 유지). 오류가 가리키는 위치가 객체 자신이면 그 객체도 포함. 힌트가 없으면 접미사 없음, `subject.identity`도 없음. `title`은 보지 않는다. 최상위(`instancePath` 빈 문자열)는 `path: "/"`, 힌트 없음. | 실행 확인 (T-06, T-07) |
| R-07 | `meta.locale`이 있음(스키마 통과 후) | `registerLocale(locale, translations)`로 문서 카탈로그를 등록하고 경고를 만든다(실패 없음). 메시지 하나는 `유효한 meta.translations 값 → locale에 해당하는 번들 카탈로그 값 → 영어` 순으로 해석한다. 번들은 `locales/manifest.json`이 등록한 `en zh-CN zh-TW es ko ar`이고 태그는 **대소문자 무시**(`zh-cn`=`zh-CN`)이며 지역·스크립트 변형은 별개 태그(`en-US`는 번들이 아님). 번들도 유효한 `translations`도 없는 태그는 `fallback`: 영어로 해석되고 `i18n/locale-fallback` 경고. 유효한 `translations`가 하나라도 있으면 `fallback`이 아니며 나머지는 영어로 채우고 `i18n/translation-coverage` 경고. `translations`에 알 수 없는 키나 `{placeholder}` 집합이 영어 원문과 다른 값이 있으면 그 항목만 버리고 `i18n/invalid-translation` 경고(번들·영어 값 유지). 경고는 `severity: warning`이고 텍스트 모드는 stderr `archify: <message>`, JSON 모드는 기록만. `meta.locale`이 없으면 아무것도 하지 않고 영어. 이후 렌더러는 `resolveLocale(meta.locale)`로 `<html lang>`과 UI 문구를 정한다. | 실행 확인 (T-08~T-10) |
| R-08 | 관계 컬렉션(`connections`·`edges`·`messages`·`flows`·`transitions`·erd/class `relationships`)에 같은 `id`가 둘 이상 | `id`가 없음·`null`·`""`인 관계는 건너뛴다. 두 번째 이후 중복마다 `/<컬렉션>/<index>/id duplicates relationship id "<id>"`. `throwDiagnosticProblems('Relationship identity validation failed', …, {code:'relationship/duplicate-id', subject:{diagramType, collection}})`. evidence·fix는 비어 있다. tree·timeline·waterfall에는 검사 없음. | 실행 확인 (T-11) |
| R-09 | 노드 ID 중복·끝점이 없는 노드·ID 참조 오류 | `loadDiagram`은 검사하지 않는다. 통과한 뒤 타입별 렌더러가 던진다(1.3 C 표). 예: architecture에서 `connections[0].to`가 없는 컴포넌트면 `architecture/unknown-endpoint`(+`layout/constraint` 하나 더). | 실행 확인(architecture, T-12) / 코드 확인(나머지) |
| R-10 | `diagramType == architecture` 이고 `meta.engineering_profile == "deployment-ownership"` | `deploymentOwnershipDiagnostics`가 모은 진단 전체를 한 번에 던진다(순서는 C-17의 발생 순서). 오류 메시지는 `Engineering profile "deployment-ownership" failed:\n- <진단 메시지>…`. code는 `engineering/deployment-boundary-kind`·`-owner-missing`·`-region-scope`·`-region-ambiguous`·`-private-state`·`-private-region-consistency`·`-crossing-mechanism`. 진단이 없으면 통과. 프로파일 값이 없거나 다른 타입이면 아무 동작 없음. | 실행 확인(경계 종류 2건+컴포넌트 4건, T-13) / 코드 확인(나머지 code) |
| R-11 | 저장소 근거를 켜는 조건 | `meta.repository`가 있거나 근거 노드 컬렉션(1.3 D) 중 하나라도 `sources`가 비어 있지 않으면 켜진다. 둘 다 없으면 `null`을 돌려주고 `--repo-root`도 `git`도 요구하지 않는다. | 실행 확인 (T-14) |
| R-12 | 근거가 켜졌을 때 사전 검사 | 아래 순서로 첫 실패에서 던진다(단일 진단): ① `meta.repository` 없음 → `repository-evidence/repository-required`. ② `revision`이 40자 16진 아님 → `…/revision-invalid`(스키마가 같은 정규식으로 먼저 걸러 `loadDiagram`에서는 `schema/pattern`이 먼저 나온다). ③ `url`이 `parseRepositoryRemote(url,{authored:true,provider})`로 해석 안 됨 → `…/url-invalid`(로컬 경로처럼 보이면 `evidence.authoredValueLooksLike`). ④ `link_mode`가 `web`·`local-only`가 아님 → `…/link-mode-invalid`(스키마 enum이 먼저 거름). ⑤ `provider`가 있는데 `url` 호스트의 provider와 다름(`github.com`→github, `gitee.com`→gitee, `gitlab.com`→gitlab; 그 밖의 호스트는 `provider: "gitlab"` 힌트가 있을 때만 gitlab) → `…/provider-invalid`. ⑥ `link_mode == web`인데 provider 미해석 호스트이거나, https가 아니거나(ssh 포함), 표준 포트(443)가 아니거나, 경로가 github·gitee는 `owner/repo`·gitlab은 `group[/sub…]/project` 정규식에 안 맞음 → `…/links-unsupported`(`link_mode: local-only`는 이 검사를 건너뜀). ⑦ `--repo-root`(환경변수) 없음 → `…/root-required`. | 실행 확인 (T-15~T-20) / 코드 확인(②④) |
| R-13 | 로컬 저장소 확인 | ⑧ `fs.realpathSync(path.resolve(root))` 실패 → `…/root-unreadable`. ⑨ `git rev-parse --show-toplevel` 실패(깃 저장소 아님) → `…/git-command`, `subject={surface}`, `evidence={gitArgs, exitCode}`, 메시지 `Evidence root "<root>" is not a Git repository.`. ⑩ 실제 경로와 top-level이 같은 항목인지 `sameEntry`로 비교: 판정 불가 → `…/root-identity-indeterminate`, 다름 → `…/root-not-top-level`(fix `pass --repo-root <top-level>`). ⑪ `git remote get-url origin` 실패 → `…/git-command`(`Evidence repository must have an origin remote.`). ⑫ origin 주소와 `url`의 정체성 비교, 다르면 `…/origin-mismatch`(origin은 `redactRepositoryRemote`로 자격증명·쿼리를 가려서 메시지·`evidence.localOrigin`에 넣는다). ⑬ `git cat-file -e <revision 소문자>^{commit}` 실패 → `…/revision-unavailable`. | 실행 확인 (T-21~T-25) / 코드 확인(`root-identity-indeterminate`) |
| R-14 | origin 일치 규칙 | 정체성은 `JSON[호스트 소문자, 엔드포인트, 경로종류, 경로]`이다(C-23). 알려진 forge(github.com·gitee.com·gitlab.com, gitlab 힌트가 있는 임의 호스트)에서는 `https`(443)와 `ssh`(22, 사용자 `git`)가 같은 엔드포인트 `standard`라 `https://github.com/o/r`와 `git@github.com:o/r.git`·`ssh://git@github.com/o/r`가 같다. 알려진 forge는 끝의 `.git`을 뗀다(github는 대소문자 무시). github·gitlab 경로는 소문자화해서 비교하고 gitee는 대소문자 구분. 모르는 호스트는 `프로토콜+포트`를 엔드포인트로 가져 https와 ssh가 서로 다르고 경로도 대소문자 구분. 주소 해석 규칙: `https?`/`ssh` 스킴이나 `git@host:path`, 공백·역슬래시·제어문자·`?`·`#` 금지, 세그먼트는 비지 않고 `.`·`..` 아님, authored URL(http/https)은 사용자 정보 금지, ssh는 사용자 `git`·비밀번호 없음. origin 쪽은 `authored:false`라 앞뒤 공백 trim, 자격증명 허용. | 실행 확인(대소문자·.git·ssh↔https: T-22/T-23, 모르는 호스트 local-only: T-19) / 코드 확인(나머지) |
| R-15 | 소스 하나씩 검사(노드 순서 → `sources` 순서) | 각 소스에서 첫 실패를 진단으로 모으되 다음 소스로 계속한다(실패한 인용은 통과로 치지 않음). 검사 순서: ⓐ `path`: 빈 값·`/` 시작·`\` 포함·제어문자 → `…/path-invalid`; 빈 세그먼트·`.`·`..`·첫 세그먼트 `.git` → `…/path-escape`. ⓑ `end_line`만 있고 `line` 없음 → `…/line-required`. ⓒ `end_line < line` → `…/line-range-invalid`. ⓓ `<revision>:<path>`가 blob이 아니면: 트리에는 blob으로 있는데 로컬에 객체가 없는 경우(`git ls-tree -z <rev> -- <path>`가 `<mode> blob <sha>` 항목을 돌려줌) `…/object-unavailable`, 그 밖(없는 경로, 디렉터리, 서브모듈 등) `…/file-missing`. ⓔ `line`이 있으면 내용을 읽어 못 읽으면 `…/file-unreadable`. ⓕ 요구 줄(`end_line`이 있으면 그것, 없으면 `line`)이 줄 수보다 크면 `…/line-out-of-range`(`evidence={sourcePath, requestedLine, lineCount, revision}`). 줄 번호가 없는 소스는 ⓓ까지만 한다. 모든 소스를 본 뒤 모인 진단이 있으면 첫 번째 진단의 `message`를 오류 메시지로 하고 전부 한 번에 던진다. `git-unavailable`이면 즉시 중단(R-17). 메시지의 `path`(`subject.path`)는 `/<컬렉션>/<노드index>/sources/<i>`(+ `/path` 또는 `/end_line`). `subject`는 `{surface, path, diagramType, collection, nodeId}`이고 architecture는 `componentId`가 추가된다. | 실행 확인 (T-26~T-33) / 코드 확인(`object-unavailable`, `file-unreadable`) |
| R-16 | 소스를 모두 통과 | 근거가 켜졌는데 검증된 인용이 0개면(예: `meta.repository`만 있고 어느 노드에도 `sources`가 없음) `…/source-required`. 아니면 1.3 D 결과를 돌려준다. 순서상 `root-required`(⑦)가 `source-required`보다 먼저 나온다. | 실행 확인 (T-17, T-14) |
| R-17 | git 호출 방식 | 모든 호출이 `git --no-replace-objects -C <실제 root> …`(replace refs 무시), 환경에 `GIT_NO_LAZY_FETCH=1`, `GIT_ALLOW_PROTOCOL=''`(어떤 전송도 불가). 기본 경로에서 실제로 실행되는 명령은 `rev-parse --show-toplevel`, `remote get-url origin`, `cat-file -e <rev>^{commit}`, `cat-file --batch-check`(인용된 `<rev>:<path>`를 stdin으로 한 번에), `cat-file --batch`(줄 번호가 있어 내용이 필요한 blob만, 한 번에). 배치가 실패하거나 한 blob이 16 MiB(`MAX_SOURCE_BYTES`)를 넘거나 배치 응답을 해석 못 하면 소스별 `cat-file -t <rev>:<path>`, `git show <rev>:<path>`로 되돌아가고, 결과(진단 순서 포함)는 같다. 배치는 최적화일 뿐이다. 읽는 것은 **커밋 객체에 저장된 바이트**이고 작업트리·인덱스는 보지 않는다. `git`을 실행할 수 없거나(`result.error`: 설치 없음, `maxBuffer` 초과 포함) → `…/git-unavailable`(fix: Git 설치)이고 나머지 소스를 더 보지 않고 던진다. 내용은 UTF-8로 해석한다. | 실행 확인(명령 목록 `GIT_TRACE`, 작업트리 6줄·커밋 3줄 사례: T-34, T-30) / 코드 확인(폴백·16 MiB) |
| R-18 | 줄 수 계산 | 빈 내용은 0줄. 아니면 `\r\n`·`\n`·`\r`로 나눈 조각 수에서 끝이 줄바꿈이면 1을 뺀다. 즉 `a\nb\nc\n`은 3줄, 끝줄바꿈 없는 `a\nb`는 2줄. | 코드 확인 · 실행 확인(3줄 파일 line 3 통과, line 4/5 실패: T-30, T-31) |
| R-19 | 인용된 줄의 내용이 노드 설명과 맞는가 | **검증하지 않는다.** 코드는 `path`가 그 커밋의 blob인지와 줄 번호가 줄 수 이내인지만 본다. `sources[].label`은 결과에 그대로 복사될 뿐 비교에 쓰이지 않는다. 노드 `label`도 읽지 않는다. 노드와 무관한 파일·줄이 통과한다. | 실행 확인 (T-35) / 코드 확인(`verifyRepositoryEvidence` 전체에 내용 비교 코드 없음) |
| R-20 | `sources` 없음 / `--repo-root` 없음 | `sources`와 `meta.repository`가 모두 없으면 통과하고 `sourceEvidence = null`(R-11). `sources`는 있고 `meta.repository`가 없으면 `repository-required`. `meta.repository`가 있고 `--repo-root`가 없으면 `root-required`(`sources`가 있든 없든). `--repo-root`만 주고 근거가 없으면 무시된다(검증 안 함). | 실행 확인 (T-14, T-16~T-18) |
| R-21 | JSON 모드의 진단 기록 | JSON 모드에서만 `recordDiagnostic`이 동작해 진단을 정규화해 모은다(`code+message+JSON(subject)`가 같으면 한 번만). 실패 보고 때 오류에 진단이 달려 있으면 **기록된 목록이 있으면 그것을, 없으면 오류에 달린 목록을** 쓴다. 그래서 앞 단계에서 기록된 경고가 뒤 단계 실패의 진단 목록 앞에 같이 들어간다. | 실행 확인 (T-36) |
| R-22 | 공개 CLI 결합 | `validate`·`render`·`deliver`·`finalize`는 `--repo-root`를 환경변수로 렌더러에 전달하고(`rendererEnv`), 렌더러 stderr의 JSON(`ok:false`, `diagnostics`가 비어 있지 않음)을 다시 파싱해 영수증으로 만든다. 파싱 불가면 `internal/unclassified`(`Renderer failed before emitting a structured diagnostic.`), 프로세스가 시작 안 되면 `internal/renderer-process`. `validate`는 렌더러를 띄우기 전에 파일을 읽어 파싱하고 `meta.output`이 있으면 형식만(3단계), 없으면 스키마를 한 번 더 검사한다(`bin/archify.mjs:6998-7010`). 결과 code는 같다. 검증 실패의 종료 코드는 1이고, `--repo-root` 값 누락은 CLI 인자 오류라 종료 코드 2다. | 실행 확인(종료 코드 1·2, 영수증 `stage`: T-01, T-06, T-37) / 코드 확인(`internal/*`) |
| R-23 | 통과 후 | `sourceEvidence`와 `diagram`은 렌더러가 HTML 슬롯과 SVG에 쓴다(행 6). 렌더러가 끝날 때까지 `loadDiagram`이 정한 `outPath`는 `outputPathGuards`에 보관된다. 이 스펙은 그 이후를 정의하지 않는다. | 코드 확인 |

- 불변식: (1) `loadDiagram`은 입력·저장소·작업트리를 수정하지 않고 같은 입력과 같은 저장소 상태면 같은 결과를 낸다. 단 `git`과 파일시스템 상태에 의존한다. (2) 앞 단계가 통과해야 뒤 단계가 실행된다(R-01). (3) 진단 객체는 항상 1.3 B 정규화를 거친 6개 필드(+선택 `suppresses`)를 가진다.
- 미결정: 없음.
- 확인 한계: Windows 쪽 분기(`validateNativeOutputPath`의 win32 경로, `windows-*` 사유 실제 거절)와 심볼릭 링크 별칭(`output/meta-resolved-extension`, `output/meta-outside-cwd`), `object-unavailable`(부분 clone), `file-unreadable`, 16 MiB 초과 blob은 실행하지 않았다(코드 확인). 설치본이 레포와 바이트 동일함은 `diff -rq`로 확인했다.

### 1.5 필수 코드 참조 [필수]
라이선스 Apache-2.0(overview 1절). 짧게 가져온다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/renderers/shared/cli.mjs:33-46` `applyLocaleTranslations` | 로케일 등록과 경고 기록·출력(JSON 모드는 stderr에 안 씀). | R-07 |
| C-02 | `archify/renderers/shared/cli.mjs:48-102` `loadDiagram` | 단계 순서, 각 단계의 실패 코드와 호출 인자(`ARCHIFY_REPO_ROOT`). 단계 9(템플릿·출력 해석)는 범위 밖. | R-01~R-04, R-23 |
| C-03 | `archify/renderers/shared/cli.mjs:318-358` `RELATIONSHIP_COLLECTIONS`, `validateRelationshipIds`, `validateCrossCollectionContracts` | 관계 컬렉션 이름표와 중복 검사. | R-08 |
| C-04 | `archify/renderers/shared/diagnostics.mjs:11-31` `plainObject`, `normalizedDiagnostic` | 진단 객체 정규화(기본값·정리). | 1.3 B, R-21 |
| C-05 | `archify/renderers/shared/diagnostics.mjs:33-42,71-104` `recordDiagnostic`, `throwDiagnosticError`, `throwDiagnosticProblems` | 기록(중복 제거 키), 던지기, 문제 문자열 ↔ 상세 진단 대응 규칙. | 1.3 B, R-21 |
| C-06 | `archify/renderers/shared/diagnostics.mjs:106-145` `fallbackDiagnostic`, `rendererFailure`, `formatDiagnostics` | JSON 실패 객체, 기록 목록 우선 규칙, 텍스트 한 줄 형식. | 1.3 B, R-21 |
| C-07 | `archify/renderers/shared/diagnostics.mjs:159-208` `installRendererDiagnosticBoundary` | 텍스트·JSON 모드 stderr와 `process.exit(1)`, 분류 안 된 오류 처리. (JSON 쪽의 `writeSync` 루프는 큰 페이로드를 끝까지 쓰는 구현 세부.) | 1.3 B |
| C-08 | `archify/renderers/shared/validator.mjs:6-82` `annotatedPath`, `validateSchema` | `id/label` 힌트, 진단 필드 구성, keyword별 fix 표, 오류 메시지 형식. | R-05, R-06 |
| C-09 | `archify/schemas/common.schema.json:6-29` `id`, `locale`, `translations`, `animation`, `visualPreset`, `qualityProfile` | ID 정규식, 로케일 길이·정규식, 번역 제한, enum. | 1.3 C |
| C-10 | `archify/schemas/common.schema.json:30-53` `portableOutputPath` | 스키마 쪽 출력 경로 규칙(정규식 조합). 런타임은 `validatePortablePath`가 같은 규칙을 코드로 검사. | R-04 |
| C-11 | `archify/schemas/common.schema.json:54-133` `side`…`guidedViews` | 공유 enum·타입 정의 값. | 1.3 C |
| C-12 | `archify/schemas/common.schema.json:134-163` `repository`, `sourceReferences` | 저장소·소스 인용 필드와 한계. | R-12, R-15 |
| C-13 | `archify/schemas/common.schema.json:164-179` `cards` | 카드 필드·색 enum. | 1.3 C |
| C-14 | `archify/scripts/generate-validators.mjs:62-86` | 생성 검증기 래퍼: ajv 통과 뒤 `meta.output`에 `validatePortablePath`(profile `output`)를 다시 적용해 실패하면 `keyword: portablePath` 오류(`code: schema/portablePath`). `loadDiagram`에서는 3단계가 먼저라 이 오류에 닿지 않고, 스키마를 직접 부르는 경로(워크플로 컴파일러 등)에서만 보인다. | R-04, R-05 |
| C-15 | `archify/renderers/shared/output-path.mjs:76-96,323-357` `authoredOutputDiagnostic`, `validateAuthoredOutputPath` | 3단계 코드 매핑과 확장자·cwd 검사. | R-04 |
| C-16 | `archify/renderers/shared/portable-path.mjs:72-212` `validatePortablePath` | 1.3 D의 사유 순서가 이 함수의 검사 순서다(위 글이 그 요약). 구현 시 이 함수를 그대로 옮기는 편이 정확하다. | R-04 |
| C-17 | `archify/renderers/shared/engineering-profiles.mjs:3-157` | `deployment-ownership`의 진단 7종 조건과 발생 순서, 던지기. | R-10 |
| C-18 | `archify/renderers/shared/repository-evidence.mjs:8-36,89-97` 상수, `evidenceFailure`, `runGit`, `gitValue` | 정규식·16 MiB 한도, git 공통 인자·환경, 진단 생성 규칙. | R-12~R-17 |
| C-19 | `archify/renderers/shared/repository-evidence.mjs:99-124` `verifiedSourcePath`, `sourceLineCount` | 경로 사유 `path-invalid`·`path-escape`, 줄 수 계산. | R-15, R-18 |
| C-20 | `archify/renderers/shared/repository-evidence.mjs:130-153` `EVIDENCE_NODE_COLLECTIONS`, `hasRepositoryEvidence` | 타입별 노드 컬렉션 이름표, 근거를 켜는 조건. | R-11 |
| C-21 | `archify/renderers/shared/repository-evidence.mjs:155-250` `verifyRepositoryEvidence` 사전 검사 | 사전 검사 순서와 코드, 조건(R-12·R-13의 원본). | R-12, R-13, R-20 |
| C-22 | `archify/renderers/shared/repository-evidence.mjs:272-393` 소스 루프와 결과 | 소스별 검사 순서, 진단 모으기, `git-unavailable` 중단, 결과 객체. (38-87의 배치 읽기는 같은 결과를 내는 최적화.) | R-15~R-17 |
| C-23 | `archify/renderers/shared/repository-location.mjs:5-55` `PROVIDER_HOSTS`, `parseRepositoryRemote`, `redactRepositoryRemote` | 원격 주소 해석과 정체성 비교 키, 자격증명 가림. | R-12, R-14 |
| C-24 | `archify/renderers/shared/repository-location.mjs:57-71` `repositorySourceHref`, `repositoryTreeHref` | `link_mode: web`일 때 결과에 들어가는 `href` 만드는 방법(GitLab은 `/-/blob`, Markdown은 `?plain=1`, 줄 구간 표기 `#L1-L3`/`#L1-3`). | 1.3 D |
| C-25 | `archify/renderers/shared/i18n.mjs:85-109,126-129,157-196` `classifyTranslations`, `bundledLocaleFor`, `resolveCatalog` | 번역 우선순위, 폴백 판정, 플레이스홀더 일치 규칙. | R-07 |
| C-26 | `archify/renderers/shared/i18n.mjs:204-226,294-296` `catalogFor`, `registerLocale`, `resolveLocale` | 문서 카탈로그 등록(대소문자 무시 키)과 `resolveLocale`. | R-07 |
| C-27 | `archify/renderers/shared/i18n.mjs:231-292` `localeDiagnostics` | 세 경고의 조건·메시지·`evidence`(키 10개까지, 합계 별도). | R-07 |

### 1.6 수락 사례 [필수]
출처: 모두 원본 실행 관찰(로컬 설치본 `validate architecture`, 레포와 `diff -rq` 동일). 입력·출력 파일은 [spec-demos/input-validation](../../../artifacts/archify/spec-demos/input-validation/)에 있고, 스크립트는 `setup-repo.sh`(임시 git 저장소 4개, 커밋 SHA `0147eb22a7af41b58c218f2d2be4cbe3b366c87b`), `make-inputs.py`, `run.sh`, `run-other.sh`, `run-extra.sh`, `run-gittrace.sh`다. 기준 입력은 `inputs/ok.json`(architecture, 컴포넌트 `web`·`api`, 연결 `web-to-api`, `meta.output: "demo.html"`)이고 사례는 그 변형이다. 출력은 `out/<입력 이름>.<mode>.{stdout,stderr,exit}`(mode: `text` 텍스트, `receipt` `--json`, `noroot` `--repo-root` 없음). 따로 적지 않으면 `--repo-root <demo>/repo`로 실행했다. 대체물: 임시 저장소의 원격 주소는 이름일 뿐 접속하지 않았다. 그래서 실제 GitHub 원격과의 일치는 검증하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-22 | `inputs/broken-json.json`(`{ "schema_version": 1, `) | 종료 코드 1. stderr 마지막 줄 `[input/json-parse] Input JSON could not be parsed: … Fix: repair the JSON syntax and run validation again.` `--json` 영수증 `stage:"input"`. 렌더러 직접(`render`)은 첫 줄도 `Input JSON could not be parsed: …`. |
| T-02 | R-02 | 없는 파일 `inputs/does-not-exist.json` | 종료 코드 1. `[input/read] Input could not be read: ENOENT…`. |
| T-03 | R-04 | `meta.output: "/tmp/x.html"` / `"../x.html"` | 각각 `output/meta-absolute`, `output/meta-path-syntax`. 종료 코드 1. |
| T-04 | R-01, R-04 | `meta.output: "/tmp/x.html"`이고 `components[1].type: "banana"`(스키마 위반) | `output/meta-absolute` **하나만**. `schema/enum` 없음. |
| T-05 | R-04 | `meta.output: "x.txt"`; erd에서 `output: "a:b.html"`, `"x.txt"`; erd에서 `output` 생략 | `output/meta-extension`; erd `a:b.html`→`output/meta-path-syntax`(`uri`), `x.txt`→`output/meta-extension`; 생략은 통과(종료 0). |
| T-06 | R-05, R-06, R-22 | `inputs/schema-bad.json`: `meta.title` 삭제, `components[0].colour: "red"`, `components[1].type: "banana"` | 종료 코드 1. 진단 3개 순서대로 `schema/required`(`subject.path:"/meta"`, 힌트 없음), `schema/additionalProperties`(`path:"/components/0"`, `identity:"web"`, 메시지에 `(id/label: "web")`, fix `remove unsupported property "colour"`), `schema/enum`(`path:"/components/1/type"`, `identity:"api"`, `evidence.allowedValues` 7개). 영수증 `stage:"render"`. |
| T-07 | R-06 | `inputs-other/top-null.json`(내용 `null`) | `[schema/type] / must be object`, fix `use "object" at /`, 힌트 없음. |
| T-08 | R-07 | `meta.locale: "xx"` | 종료 0. stderr `archify: meta.locale "xx" has no bundled catalog and no usable meta.translations; … fall back to English.`. `--json` 영수증 `diagnostics`에 `i18n/locale-fallback`(severity `warning`, `evidence.bundledLocales`=`[en,zh-CN,zh-TW,es,ko,ar]`). |
| T-09 | R-07 | `locale: "ko"`, `"zh-cn"`; `"en-US"`; `"EN_us"` | `ko`, `zh-cn`: 경고 없음, 종료 0. `en-US`: `locale-fallback` 경고(번들 아님), 종료 0. `EN_us`: 스키마 실패 `schema/pattern`, 종료 1. |
| T-10 | R-07 | `locale:"xx"`+`translations`: ① `{"viewer.nope":"x","nonexistent.key":"y"}` ② `{"node.focus":"Focus {label}"}` ③ `{"node.focus":"Focus {name}"}` | ① 경고 2개: `invalid-translation`(2 unknown) + `locale-fallback`. ② 경고 1개: `translation-coverage` `1/486 … 485 fall back`(fallback 아님). ③ `invalid-translation`(1 placeholder mismatch)+`locale-fallback`. 모두 종료 0. |
| T-11 | R-08 | `connections`에 같은 `id:"web-to-api"` 두 번 | 종료 1. `[relationship/duplicate-id] /connections/1/id duplicates relationship id "web-to-api"`. 오류 메시지 `Relationship identity validation failed:\n- …`. |
| T-12 | R-09 | `connections[0].to: "ghost"` | 종료 1. `[architecture/unknown-endpoint] Connection "HTTPS" references unknown target "ghost"…`과 `[layout/constraint] … does not name a declared component.`. 스키마·ID 단계는 통과. |
| T-13 | R-10 | `meta.engineering_profile:"deployment-ownership"`, 경계·`tag` 없음 | 종료 1. 오류 메시지 `Engineering profile "deployment-ownership" failed:` + 6줄. 진단 순서: `deployment-boundary-kind`(region), `deployment-boundary-kind`(security-group), 컴포넌트 `web`의 `deployment-owner-missing`·`deployment-region-scope`, 컴포넌트 `api`의 같은 둘. `inputs-other/tree-engineering-profile.json`은 `schema/additionalProperties`. |
| T-14 | R-11, R-16, R-20 | `inputs/ok.json`(근거 없음) `--repo-root` 없이·있이 / `meta.repository`만 있고 `sources` 없음, `--repo-root` 있음 | 근거 없음: 종료 0, root 무관. `meta.repository`만: `[repository-evidence/source-required] /meta/repository requires at least one /components source reference.` 종료 1. |
| T-15 | R-12 | `url:"/Users/me/demo"` | `repository-evidence/url-invalid`, `evidence.authoredValueLooksLike`, fix에 `git remote get-url origin`. |
| T-16 | R-12, R-20 | `sources` 있고 `meta.repository` 없음 | `repository-evidence/repository-required`(`--repo-root` 없이도 이 code). |
| T-17 | R-12, R-16, R-20 | `meta.repository`+유효한 `sources`, `--repo-root` 없음 / `meta.repository`만+`--repo-root` 없음 | 둘 다 `repository-evidence/root-required`, 종료 1. |
| T-18 | R-12 | `url:"https://git.example.com/example/demo"`(web 모드), 모르는 호스트 | `repository-evidence/links-unsupported`(`--repo-root` 없이도). |
| T-19 | R-12, R-14 | repo `repo-selfhosted`(origin `https://git.example.com/example/demo`)에서: ① `link_mode:"local-only"` ② web 모드 ③ web+`provider:"gitlab"` | ① 종료 0. ② `links-unsupported`. ③ 종료 0. (`provider:"gitlab"`을 `github.com` 주소에 주면 `provider-invalid`.) |
| T-20 | R-12 | `provider:"gitlab"`, url `https://github.com/example/demo` | `repository-evidence/provider-invalid`. `provider:"bitbucket"`, `link_mode:"both"`, 짧은 `revision`은 스키마 단계 `schema/enum`·`schema/pattern`. |
| T-21 | R-13 | `--repo-root <demo>/repo/src`(하위 디렉터리) / 없는 디렉터리 / `/private/tmp`(git 아님) / `--repo-root`만 | `root-not-top-level`(fix `pass --repo-root <top-level>`) / `root-unreadable` / `git-command` `Evidence root "…" is not a Git repository.` / CLI 메시지 `--repo-root requires a repository path.` 종료 코드 **2**. |
| T-22 | R-14 | 저장소 `repo`(origin `https://github.com/example/demo.git`)와 `url:"https://github.com/Example/Demo.git"`; 저장소 `repo-ssh`(origin `git@github.com:Example/Demo.git`)와 `url:"https://github.com/example/demo"` | 둘 다 통과(종료 0). |
| T-23 | R-13, R-14 | `url:"https://github.com/example/other"`; origin 없는 저장소 `repo-noorigin` | `origin-mismatch`(메시지에 `"https://github.com/example/demo.git"`); `git-command` `Evidence repository must have an origin remote.`. |
| T-24 | R-13 | `revision: "0"×40`(형식은 맞고 객체 없음) | `repository-evidence/revision-unavailable`. |
| T-25 | R-12 | 짧은 `revision`(7자) | `schema/pattern`(`repository-evidence/revision-invalid`는 안 나옴). |
| T-26 | R-15 | `sources:[{"path":"src/nope.txt"}]` / `{"path":"src"}`(디렉터리) | 둘 다 `repository-evidence/file-missing`, `subject.path:"/components/0/sources/0/path"`, `evidence.{sourcePath,revision}`. |
| T-27 | R-15 | `{"path":"../a.txt"}` / `{"path":"/etc/passwd"}` | `path-escape` / `path-invalid`. |
| T-28 | R-15 | `{"path":"src/a.txt","end_line":2}` / `line:3,end_line:2` | `line-required`(`subject.path` …`/end_line`) / `line-range-invalid`(`evidence.{line:3,endLine:2}`). |
| T-29 | R-15 | `line:0` / `sources:[]` / 소스 4개 | 스키마 단계 `schema/minimum`, `schema/minItems`, `schema/maxItems`. |
| T-30 | R-15, R-17, R-18 | `src/a.txt`는 커밋에 3줄, 작업트리에는 6줄. `line:5` / `line:3` / `line:3` 파일 경로만(`src/nolines.txt`) | `line:5` → `[repository-evidence/line-out-of-range] /components/0/sources/0 requests line 5, but src/a.txt has 3 lines at revision 0147eb2…`(`evidence.{requestedLine:5, lineCount:3}`), 종료 1. 작업트리 편집을 보지 않음(`out/worktree-vs-commit.check`). `line:3`·줄 없는 소스는 통과. |
| T-31 | R-15, R-18 | `{line:2, end_line:4}` | `line-out-of-range`, `requestedLine:4`(끝 줄 기준). `{line:1,end_line:3}`은 통과(`ev-ok`). |
| T-32 | R-15 | `sources:[{"path":"src/nope.txt"},{"path":"src/a.txt","line":9}]` | 진단 **2개** 한 번에: `file-missing`(sources/0/path), `line-out-of-range`(sources/1). 오류 메시지는 첫 진단 메시지. |
| T-33 | R-12, R-15 | 모든 사전 검사가 통과하는 `inputs/ev-ok.json` | 종료 0, stdout `ok architecture …`. |
| T-34 | R-17 | `GIT_TRACE=<file>`로 `ev-ok` 실행(`run-gittrace.sh`) | `out/gittrace-ev-ok.commands`에 정확히 5개: `rev-parse --show-toplevel`, `remote get-url origin`, `cat-file -e '<sha>^{commit}'`, `cat-file --batch-check`, `cat-file --batch`. `git show`·`ls-tree` 없음. |
| T-35 | R-19 | `components[0].label`과 무관한 `sources:[{"path":"src/a.txt","line":2,"label":"totally unrelated claim"}]` | 종료 0. 내용 일치는 검사하지 않음. |
| T-36 | R-21 | `meta.locale:"xx"` + 중복 관계 `id`, `--json` | 영수증 `diagnostics` 순서 `i18n/locale-fallback`(warning), `relationship/duplicate-id`(error). 텍스트 모드 stderr에도 두 줄이 같은 순서. |
| T-37 | R-01, R-22 | `ARCHIFY_DIAGNOSTIC_FORMAT=json`로 `render architecture inputs/dup-relationship-id.json out/never-written.html`; `inputs-other/alias-copy.json`을 입력이자 출력으로 지정한 `render` | 첫째: 종료 1, stderr 한 줄 JSON `{"schemaVersion":1,"ok":false,"source":"renderer","error":"Relationship identity validation failed:\n- …","diagnostics":[{"code":"relationship/duplicate-id","severity":"error",…}]}`, 출력 파일 없음. 둘째: `[output/input-alias]`(9단계), 입력 파일 불변(`out-other/alias.check`). |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
레포 clone 기준 `repos/archify`@a406594. 실행 기록은 모두 [spec-demos/input-validation](../../../artifacts/archify/spec-demos/input-validation/) 하위.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02 `cli.mjs:48-102` | 코드 읽기 + T-04 실행. |
| R-02, R-03 | `cli.mjs:53-78`, `bin/archify.mjs:2646-2662` `inputDiagnostic`(공개 CLI 쪽 사본) | T-01·T-02. `render` 직접 호출과 `validate`의 메시지 접두사 차이는 `out/broken-json.render.stderr` 대 `out/broken-json.text.stderr`. |
| R-04 | C-15 `output-path.mjs:76-96,323-357`, C-16 `portable-path.mjs:72-212`, `cli.mjs:80-81` | T-03~T-05 실행. `meta-resolved-extension`·`meta-outside-cwd`는 심볼릭 링크가 필요해 코드만 읽음. |
| R-05, R-06 | C-08 `validator.mjs:6-82` | T-06·T-07 실행. `expected`는 ajv가 준 `schema` 조각이라 영수증에서 확인(`out/schema-bad.receipt.stdout`). |
| R-07 | C-01, C-25~C-27 | T-08~T-10 실행. `<html lang>` 효과는 행 6 범위라 확인하지 않음. 카탈로그 파일(`locales/*.json`) 내용은 읽지 않음(키 수 486은 경고 문구에서 관찰). |
| R-08 | C-03 `cli.mjs:318-358` | T-11 실행. |
| R-09 | 1.3 C 표의 각 `파일:줄` | architecture는 T-12 실행. 나머지 타입은 해당 함수의 검사 줄만 읽음(`unique`·`unknown`·`duplicate` grep 후 해당 구간). tree는 `inputs-other/tree-missing-parent.json` 실행으로 `[tree/missing-parent]`도 관찰(`out-other/`). |
| R-10 | C-17 `engineering-profiles.mjs:3-157`, `cli.mjs:85` | T-13 실행(6개 진단). 7개 code 중 `region-ambiguous`·`private-state`·`private-region-consistency`·`crossing-mechanism`은 실행하지 않음. |
| R-11, R-20 | C-20 `repository-evidence.mjs:149-157` | T-14, T-16, T-17 실행. |
| R-12 | C-21 `repository-evidence.mjs:155-250`, C-23 `repository-location.mjs:5-49` | T-15~T-20, T-25 실행. `revision-invalid`·`link-mode-invalid`는 스키마가 먼저 막아 `loadDiagram` 경로에서 도달 불가(T-20, T-25). `verifyRepositoryEvidence`를 직접 부르는 explainer 경로(`explainer/sources.mjs:220,272`)에서는 도달 가능할 수 있으나 행 10 범위. |
| R-13 | C-21 `:198-250` | T-21, T-23, T-24 실행. `root-identity-indeterminate`는 미실행. |
| R-14 | C-23 `repository-location.mjs:5-55` | T-22, T-19 실행. gitee·`ssh://`·임의 포트·http 사례는 코드만. |
| R-15 | C-19, C-22 `repository-evidence.mjs:272-393` | T-26~T-33 실행. `object-unavailable`, `file-unreadable`은 부분 clone이 필요해 코드만. |
| R-16 | C-22 `:374-393` | T-14, T-17 실행. 결과 객체 모양은 코드(`out/ev-ok.*`에는 결과가 안 보임: `validate`가 렌더 후 폐기). |
| R-17 | C-18 `:8-36`, C-22, `repository-evidence.mjs:38-87` 배치 읽기 | T-34 `GIT_TRACE` 5개 명령 + `out/worktree-vs-commit.check`. 폴백(`git show`·`ls-tree`·`cat-file -t`)과 16 MiB 한도는 코드만. `--no-replace-objects`·`-C`·환경변수는 코드(`GIT_TRACE`는 전역 옵션을 따로 보여 주지 않음). |
| R-18 | C-19 `:120-124` | T-30·T-31 실행(3줄 파일 경계). CRLF·CR·빈 파일은 코드만. |
| R-19 | `repository-evidence.mjs` 전체(`verifyRepositoryEvidence`)에서 `label`·노드 `label`·줄 내용을 읽는 코드가 없음을 확인. `authored.label`은 `source`에 복사(:291)될 뿐. | T-35 실행으로 확인. 부정적 주장이므로 `repository-evidence.mjs`(394줄)를 전부 읽은 범위에서만 `코드 확인`. 호출자에서 의미 비교를 하는지는 `verifyRepositoryEvidence`의 호출자(`cli.mjs:86`, `explainer/sources.mjs`) 중 `cli.mjs`만 확인. |
| R-21 | C-05 `diagnostics.mjs:33-42`, C-06 `:117-132` | T-36 실행. |
| R-22 | `bin/archify.mjs:2347-2372,2428-2433,2664-2690,4289-4311,6963-7090`, C-06 | T-01, T-06, T-21 실행(종료 코드, `stage`). `internal/unclassified`·`internal/renderer-process`는 코드만. |
| R-23 | `cli.mjs:88-102` | 코드만. |
| T-01~T-37 | 표 위 설명의 스크립트·출력 | 원본 실행 관찰. 대체물·한계는 1.6 머리말. |

**문서와 구현이 다른 곳.**
- `reports/archify/questions/q2-verification.md` 2.2 표와 overview 2절 feature map 5행은 4단계를 "관계가 가리키는 노드가 있는지, 관계 ID 중복 없는지"로 적었다. 구현의 `loadDiagram`은 **관계 `id` 중복만** 본다(`cli.mjs:356-358`). 노드 참조 검사는 각 렌더러 안에서 나중에 한다(R-09).
- q2는 줄 확인에 `git show`를 쓴다고 했다. 기본 경로는 `cat-file --batch-check`/`--batch`이고 `git show`는 폴백이다(T-34).
- q2는 "지원 호스트(GitHub·Gitee·GitLab)의 HTTPS 주소"라고 했다. 해석 단계는 `ssh://git@`·`git@host:path`도 받고, 웹 링크(`link_mode: web`)에만 https·표준 포트·정해진 경로 모양을 요구한다. `link_mode: local-only`는 모르는 호스트도 받는다.
- `schemas/README.md`는 "모든 다이어그램 스키마가 `meta.output`을 필수로 요구한다"고 적었으나 erd·tree·class는 `title`만, timeline·waterfall은 `title`+`evidence`만 필수이고 `output`은 선택이다. 값이 있으면 같은 형식 검사를 받는다(T-05).
- `generated-validators.mjs`는 `explainer`까지 11종이고 `loadDiagram`이 쓰는 것은 10종이다.

### 2.2 코드 읽는 순서 [선택]
`renderers/shared/cli.mjs:48` `loadDiagram` → 단계별로 `output-path.mjs:323` → `validator.mjs:38` → `i18n.mjs:157` → `cli.mjs:332` → `engineering-profiles.mjs:147` → `repository-evidence.mjs:155`(사전 검사 :155-250 → 소스 루프 :272-393) → 마지막으로 `diagnostics.mjs`(진단이 어떻게 만들어지고 stderr로 나가는지). 공개 CLI 쪽 결합은 `bin/archify.mjs:2347`(`--repo-root`)와 `:2664`(`rendererFailure`).

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙 없음. `verifyRepositoryEvidence`는 explainer(`explainer/sources.mjs`)가 재사용하고, `validateSchema`는 워크플로 컴파일러(`workflow-compiler.mjs:1388-1389`)가 다시 호출한다. 코드를 복사하지 않았다.
