---
sha: "5979991d5f0af542fbb02ba906bdba4de52b2b64"
created: 2026-11-17
updated: 2026-11-17
sources:
  - packages/lint/src/hyperframeLinter.ts
  - packages/lint/src/types.ts
  - packages/lint/src/context.ts
  - packages/lint/src/sourceLocations.ts
  - packages/lint/src/sourceCoordinates.ts
  - packages/lint/src/shouldBlockRender.ts
  - packages/lint/src/projectIgnore.ts
  - packages/lint/src/linkedFile.ts
  - packages/lint/src/project.ts
  - packages/lint/src/index.ts
  - packages/lint/src/browser.ts
  - packages/lint/src/rules/composition.ts
  - packages/lint/src/rules/core.ts
  - packages/lint/src/rules/structure.ts
  - packages/lint/src/rules/media.ts
  - packages/lint/src/rules/gsap.ts
  - packages/lint/src/rules/linkedClips.ts
  - packages/lint/src/rules/adapters.ts
  - packages/lint/src/rules/shaders.ts
  - packages/lint/src/rules/slideshow.ts
  - packages/lint/src/rules/rootPaths.ts
  - packages/lint/src/rules/captions.ts
  - packages/lint/src/rules/fonts.ts
  - packages/lint/src/rules/textures.ts
  - packages/lint/src/rules/audioAttributes.ts
  - packages/core/src/lint/index.ts
  - packages/core/src/compiler/staticGuard.ts
  - packages/core/src/compiler/htmlBundler.ts
  - packages/producer/src/services/hyperframeLint.ts
  - packages/producer/src/services/hyperframeLintWorker.ts
  - packages/producer/src/server.ts
  - packages/cli/src/commands/lint.ts
  - packages/cli/src/commands/check.ts
  - packages/cli/src/commands/validate.ts
  - packages/cli/src/commands/layout.ts
  - packages/cli/src/commands/render.ts
  - packages/cli/src/commands/render/execute.ts
  - packages/cli/src/commands/render/plan.ts
  - packages/cli/src/utils/lintProject.ts
  - packages/cli/src/utils/lintHtmlWorker.ts
  - packages/cli/src/utils/lintFormat.ts
  - packages/cli/src/utils/checkPipeline.ts
  - packages/cli/src/utils/checkTypes.ts
  - packages/cli/src/renderSetupWorker.ts
  - docs/packages/lint.mdx
  - docs/reference/lint-rules.mdx
depends:
  - ./composition-contract.md
status: draft
---

# 린트·검증

> 컴포지션 HTML과 프로젝트 파일을 입력으로 받아 규칙을 검사하고, 문제 목록(severity, code, 위치, 메시지, 수정 힌트)과 렌더 차단 여부를 만든다. CLI `lint`, `check`, `validate`, `layout`이 이 결과를 각자 다르게 쓴다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 입력은 `hyperframes lint`(프로젝트 폴더)다. 렌더 전 린트와 `check`도 같은 `lintProject`를 부른다.

1. CLI가 `lintProject(projectDir, entryFile?, hostOptions, {includeUnmounted})`를 부른다(R-08).
2. `lintProject`가 index.html과, 거기서 마운트된 `compositions/**.html`을 모은다. 파일마다 외부 CSS·JS를 읽어 `externalStyles`·`externalScripts`로 붙인다(R-08, R-10).
3. 파일 하나마다 `lintHyperframeHtml(html, options)`를 부른다. 이 함수가 `buildLintContext`로 HTML을 한 번 해석하고(R-06), 12개 규칙 그룹을 정해진 순서대로 하나씩 실행해 finding을 모은다(R-05).
4. 같은 문제는 한 번만 남기고(R-02), 규칙이 위치를 주지 않은 finding에는 원본 HTML에서 `line`·`column`을 붙인다(R-03).
5. 프로젝트 단위 규칙(파일 존재, 링크 에셋, 서브 컴포지션 사용 가능 판정 등)이 따로 돌아 finding을 해당 파일 결과에 더한다(R-09).
6. 호출자가 총 error·warning 수로 동작을 정한다. 렌더 명령은 `shouldBlockRender`로 차단 여부를 판정하고(R-15, R-16), `lint`는 error가 있으면 종료 코드 1을 내며(R-19), `check`는 브라우저 측정 결과와 합쳐 `ok`를 계산한다(R-20).

### 1.2 범위·통합 지점 [필수]

- 제공: 린트 엔진(규칙 실행, context, 위치 계산, dedupe), 프로젝트 단위 린트, 렌더 차단 판정 함수, producer의 `/lint` 서버 경로, CLI `lint`·`check`·`validate`·`layout`이 린트 결과를 쓰는 방식, 렌더 밖 호출처(publish, snapshot, media-treatment, preview, Studio 서버, R-25).
- 제외:
  - 규칙 12그룹 각각의 판정 조건 세부는 본문 R-ID에 쓰지 않고 부록 A(규칙 카탈로그)에 code별 한 줄로 둔다. 규칙 파일 위치는 1.5의 C-ID를 따른다.
  - 브라우저에서 도는 contrast·layout 측정의 세부 알고리즘(`contrast-*.ts`, `layout.ts` 본체, `*.browser.js`)은 호출 관계와 결과 형식까지만 쓴다(R-20~R-23).
  - 컴포지션 속성의 의미(`data-start` 문법, track, 서브 컴포지션 해석)는 선행 스펙을 따른다. 이 스펙은 린트가 그 속성을 어떻게 검사하는지만 R-12에 쓴다.
  - Studio UI가 finding을 보여 주는 방식은 범위 밖이다. Studio가 `host: "studio"`를 넘기는 사실만 R-02에 적는다.
- 외부 의존·선행 계약: 선행 스펙 [composition-contract.md](./composition-contract.md)(`readClipTiming`, `checkSubCompositionUsability`, `resolveReferencedStart` 등 `@hyperframes/parsers` 함수를 린트가 가져다 쓴다). 호출자는 프로젝트 폴더 파일 시스템을 제공한다. 단일 HTML 린트(`lintHyperframeHtml`)는 파일 시스템이 필요 없다(`lintMediaUrls`만 네트워크를 쓴다).
- 소유 상태·부작용: 린트 함수는 입력 파일을 쓰지 않는다. 결과는 호출마다 새로 만든다. 부작용은 `lintMediaUrls`의 HEAD 요청, producer `/lint`의 worker thread, CLI의 자식 프로세스 린트(R-07, R-17)뿐이다. `lintProject`는 디스크 파일을 읽기만 한다.

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `lintHyperframeHtml(html, options?)` | string, `HyperframeLinterOptions` → `Promise<HyperframeLintResult>` | 단일 HTML 린트. 파일 시스템을 읽지 않는다. 규칙이 async일 수 있어 항상 Promise다. |
| `HyperframeLinterOptions` | `filePath?`, `isSubComposition?`, `compSrcPath?`, `externalStyles?[]`, `externalScripts?[]`, `scriptsOutsideProjectUnread?[]`, `distributed?`, `projectFontFamilies?[]`, `host?: "studio" or "cli"` | `externalStyles`·`externalScripts`는 호출자(`lintProject`)가 읽어 넘긴 링크 파일 내용이다. `distributed`가 true일 때만 `system_font_will_alias`(warning)가 돈다. false이면 그 finding은 만들어지지 않는다(`types.ts:60-62` 주석은 info에서 warning으로 올린다고 쓰지만 `fonts.ts` 규칙은 `!options.distributed`이면 빈 배열을 반환한다). `host`가 `"studio"`이면 structure 규칙이 error, 그 밖에는 warning이다. 단 `clip_ends_past_root_duration`은 host와 무관하게 항상 warning이다(R-11, 부록 A). |
| `HyperframeLintFinding` | `code`, `severity`, `message`, `file?`, `line?`, `column?`, `selector?`, `elementId?`, `fixHint?`, `snippet?`, `suggestedComposition?` | `code`와 `severity`와 `message`만 필수다. `line`·`column`은 1부터 시작하고, 유일한 위치가 없으면 둘 다 없다(R-03). |
| `HyperframeLintResult` | `ok`, `errorCount`, `warningCount`, `infoCount`, `findings[]`, `timings?` | `ok`는 `errorCount === 0`이다(warning은 영향 없음). `timings`는 `{totalMs, groupMs, slowestRule, slowestRuleMs}`이고 `slowestRule`은 `<group>#<그룹 안 순번>`이다. |
| `lintProject(projectDir, entryFile?, hostOptions?, {includeUnmounted?})` | → `Promise<ProjectLintResult>` | 프로젝트 린트(R-08). `entryFile`은 절대 경로이고 프로젝트 밖이면 `Error`를 던진다. |
| `ProjectLintResult` | `results[{file, result, contentHash}]`, `totalErrors`, `totalWarnings`, `totalInfos`, `unmountedCompositions?` | `file`은 프로젝트 루트 기준 상대 경로(`/` 구분)다. `contentHash`는 파일 내용 sha256의 앞 16자리로, 같은 파일을 다시 린트했는지 구분하는 용도다. |
| `shouldBlockRender(strictErrors, strictAll, totalErrors, totalWarnings)` | boolean ×2, number ×2 → boolean | 순수 함수(R-15). |
| `lintMediaUrls(html, {timeoutMs?})` | → `Promise<finding[]>` | 원격 `video`/`audio`/`img`/`source`의 `src`에 HEAD를 보내 응답이 2xx가 아니거나 네트워크 오류이면 `inaccessible_media_url` error를 만든다. 기본 8000ms. `lintHyperframeHtml`과 따로 부르는 별도 단계이고, 이 SHA에서 CLI `lint`는 부르지 않는다(R-24). |
| `projectIgnore(projectDir)` | → ignore 매처 | 기본 패턴 `/renders/`, `/snapshots/`, `.*`에 `.hyperframesignore` 내용을 더한다(R-04). |
| CLI `lint [dir] --json --verbose --include-unmounted --lint-verbose` | `dir`은 프로젝트 폴더 또는 컴포지션 파일 하나 | R-19. |
| CLI `check`의 `lint` 섹션 | `{ok, errorCount, warningCount, infoCount, findings[], filesScanned}` | R-20. |

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 입출력 계약**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `lintHyperframeHtml(html, options)`를 부른다 | 반환값 `ok`는 error 개수가 0일 때만 true다. `errorCount`·`warningCount`·`infoCount`는 dedupe와 위치 계산이 끝난 `findings`를 센 값이다. `timings`는 항상 채워진다. 규칙 실행 순서와 개수는 R-05가 정한다. | 코드 확인 |
| R-02 | finding의 모양과 중복 | severity는 `"error"`, `"warning"`, `"info"` 세 단계다. `code`는 소문자 snake_case 문자열 리터럴이다(예: `negative_z_index`). 이 SHA에서 `code`의 열거형·레지스트리 타입은 없고 `string`이다. 같은 `code`·`severity`·`selector`·`elementId`·`message`를 가진 finding은 한 번만 남는다(먼저 만들어진 것이 남는다). `shader_unbounded_cosine_pow`만 `line`·`column`도 키에 넣는다. `filePath` 옵션이 있으면 `file`이 없는 finding에 그 값을 채운다. `lintProject`는 각 파일 호출에서 절대 경로(`filePath`)를 넘기므로 파일별 finding의 `file`은 절대 경로이고, 프로젝트 단위 규칙이 만든 finding의 `file`은 규칙이 정한다. dedupe는 `lintHyperframeHtml` 한 번 안에서만 하고 파일 사이에는 하지 않는다. | 코드 확인 |
| R-03 | 위치(소스 좌표) 계산 | `line`·`column`은 원본 HTML 문자열 기준 1부터 시작하는 값이고 UTF-16 offset으로 센다(CRLF와 CR도 줄바꿈 하나). 우선순위: ① 규칙이 `line`을 이미 줬거나, 규칙이 `locate(block, offset)`으로 계산해 넣었으면 그대로 쓴다. 외부 CSS·JS 블록(`index === -1`)은 그 파일 내용 안의 좌표와 그 파일 경로를 쓴다. ② 아니면 `createSourceLocator`가 `snippet`을 공백 정규화한 뒤 원본(주석은 가리고)에서 찾아 정확히 한 곳이면 그 위치를 쓴다. 두 곳 이상이거나 없으면 위치 없음이다. ③ snippet이 없으면 `elementId`(또는 selector가 `#id` 꼴일 때 그 id)를 가진 태그가 정확히 하나일 때만 그 태그 시작 위치를 쓴다. 여러 개이면 위치 없음이다(틀린 복사본을 가리키지 않으려는 의도적 동작). ④ 코드가 `shader_unbounded_cosine_pow`, `invalid_inline_script_syntax`, `non_deterministic_code`, `gsap_infinite_repeat`, `gsap_repeat_ceil_overshoot`, `gsap_repeat_floor_unclamped`인 finding과 snippet이 `externalStyles` 내용 안에 있는 finding은 ②③을 건너뛴다. 규칙 입력은 주석을 지우고 `<template>`을 풀어 낸 문자열이라서, 좌표는 `mappedHtmlSource`의 offset 표로 원본 위치로 되돌린다. | 코드 확인 |
| R-04 | 무시(ignore) 설정 | finding 단위나 규칙 단위로 끄는 설정(주석 지시자, 옵션, 설정 파일 키)은 이 SHA에서 찾지 못했다(2.1에 검색 범위). 있는 것은 파일 단위 제외뿐이다. `lintProject`가 `compositions/` 아래 `.html`을 순회할 때 `projectIgnore(projectDir)`로 거른다. 패턴은 `.gitignore` 문법(`ignore` 패키지)이고, 기본값은 `/renders/`, `/snapshots/`, `.*`(점으로 시작하는 파일·폴더)이며 프로젝트 루트의 `.hyperframesignore` 파일 내용을 그 뒤에 더한다. 물어보는 경로는 `compositions/<상대 경로>`이고 폴더는 끝에 `/`를 붙인다. 이 필터는 index.html과 `entryFile`에는 적용되지 않는다. 이 설정은 클라우드 publish의 파일 제외에도 같이 쓰인다(`publishProject.ts`가 `projectIgnore`를 import). `lintProject`는 무시 여부를 `compositions/<상대 경로>` 꼴(폴더는 끝에 `/`)로 묻는다(`project.ts:376-377`). 그래서 기본 패턴 `/renders/`, `/snapshots/`는 이 경로에서는 매치될 일이 없고, 린트에서 실제로 걸리는 기본 패턴은 `.*`(점으로 시작하는 파일·폴더 이름)뿐이다. 사용자가 `.hyperframesignore`에 쓰는 패턴도 `compositions/` 접두를 포함한 경로 기준으로 써야 한다(예: `compositions/draft/`). 프로젝트 루트 기준 경로를 묻는 다른 소비자(publish의 파일 제외)에서는 `/renders/`가 의미가 있을 수 있다(추론, 그 코드는 열지 않았다). | 코드 확인(없다 주장의 범위는 2.1) |

**B. 규칙 실행 구조**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-05 | 규칙 등록과 실행 | 규칙은 `(ctx: LintContext) => finding[] 또는 Promise<finding[]>` 모양의 함수다. 각 규칙 파일이 이런 함수의 배열(`coreRules`, `mediaRules`, `gsapRules`, `captionRules`, `compositionRules`, `adapterRules`, `textureRules`, `fontRules`, `slideshowRules`, `structureRules`, `shaderRules`, `rootPathRules`)을 내보내고, `hyperframeLinter.ts`의 `RULE_GROUPS`가 이 12개를 위 순서로 나열한다. 별도 등록 API나 동적 발견은 없다. 실행은 그룹 순서, 그룹 안 배열 순서대로 하나씩 `await`한다(병렬 아님). 규칙 하나는 함수 하나지만 finding의 `code`는 여러 개일 수 있다(예: `duplicate_media_id`와 `duplicate_media_discovery_risk`가 한 함수). 규칙 이름은 없고 `<그룹>#<순번>`으로만 구분하므로, 규칙을 넣거나 빼면 뒤 순번이 밀린다. `LINT_RULE_COUNT`와 `LINT_RULE_GROUP_COUNTS`가 빌드의 규칙 수를 내보낸다. `rules/` 폴더의 파일 14개 중 `linkedClips.ts`와 `audioAttributes.ts`는 그룹이 아니고 `media.ts`가 가져다 쓰는 helper다. | 코드 확인 |
| R-06 | 규칙이 받는 `LintContext` | `buildLintContext(html, options)`가 한 번 만들어 모든 규칙에 같은 객체를 준다. 필드는 `source`(주석 제거본), `rawSource`(원본), `tags`(열린 태그 목록: 이름, 속성 문자열, 위치), `styles`, `scripts`(내용과 시작 offset, 링크 파일은 `index: -1`), `compositionIds`, `rootTag`, `rootCompositionId`, `locate`, `options`다. DOM이 아니라 htmlparser2 기반 태그·블록 스캔이다. 처리: ① 주석을 고정점 삭제로 제거한다. ② 주석 밖 `<template>`이 있고 template 밖에 컴포지션 루트가 없으면 첫 template 안쪽을 `source`로 삼는다(서브 컴포지션 파일 모양). 루트가 template 밖에 이미 있으면 풀지 않는다. ③ `externalStyles`·`externalScripts`를 `styles`·`scripts` 뒤에 붙인다. `rootTag`는 `findRootTag`가 정한다(`body`에 컴포지션 표지가 있으면 body, 아니면 body 안 첫 비메타 태그). | 코드 확인 |
| R-07 | 규칙이 예외를 던진다 | `runRules`와 `lintHyperframeHtml`에는 try/catch가 없다. 규칙 하나가 던지면 그 호출의 Promise가 reject되고 그 파일의 부분 결과는 반환되지 않는다. 호출자별 처리는 다음과 같다. 프로젝트 단위의 `lintProject`도 파일 호출을 감싸지 않으므로 그대로 전파된다(파일 목록 탐색 한 곳인 `lintMultipleRootCompositions`만 자체 try/catch로 삼킨다). CLI `lint`는 catch해서 메시지를 stderr로 내거나 `--json`이면 `{ok:false, error:{code:"runtime_error"}, findings:[]...}`를 출력하고 종료 코드 1이다. `check`는 `check_lint_failure` 런타임 finding으로 바꿔 실패 보고서를 낸다. 렌더 전 린트(R-16)는 `signal`이 있으면 자식 프로세스(`runRenderSetupWorker("lint")`)에서 돌리고 자식의 실패는 렌더 명령의 오류가 된다(전파 방식은 추론). Studio(`lintHtmlOutOfProcess`)와 producer `/lint`(worker thread)는 메모리 512MB·시간 15초 제한 안에서 돌리고, 시간 초과·메모리 초과·프로세스 종료이면 `code: "lint_aborted"`, `severity: "error"` finding 하나만 가진 결과(`ok:false`, `errorCount:1`)로 바꾼다. 린트 프로세스가 아닌 쪽으로 대신 린트하는 fallback은 없다. | 코드 확인(렌더 명령 쪽 오류 표시는 추론) |
| R-08 | `lintProject`의 대상 선택과 결과 조립 | ① `entryFile`이 없으면 `<projectDir>/index.html`이 루트 파일이다. 있으면 프로젝트 밖일 때 `Error("Explicit lint entry is outside the project directory: ...")`를 던진다. 루트 파일이 index.html이 아니면 `compSrcPath`로 그 상대 경로를 쓴다. ② 루트 HTML에서 `[data-composition-src]` 호스트(template 안 포함)를 따라 마운트된 파일을 모은다. 원격·인라인·플레이스홀더 src, 프로젝트 밖 경로, private 경로(`isStudioPrivatePath`)는 건너뛴다. ③ 루트를 먼저 `lintHyperframeHtml`로 돌린 뒤, `entryFile`을 주지 않았고 `compositions/` 폴더가 있으면 그 아래 `.html`을 정렬해 순회한다. `compositions/components/`(최상위 하위 폴더)와 `._`로 시작하는 파일, `projectIgnore`가 거른 파일은 제외한다. ④ 마운트되지 않은 파일은 `includeUnmounted`가 false이면 린트하지 않고, 첫 태그에 `data-hf-snippet`이 없는 것만 `unmountedCompositions`에 적는다. `includeUnmounted`가 true이거나 마운트된 파일이면 린트한다. 단 `data-hf-snippet` 파일은 마운트돼도 개별 린트를 하지 않는다(프로젝트 규칙용 소스 목록에는 들어간다). 순회 파일은 `isSubComposition: true`로 돌린다. ⑤ `hostOptions`(`host`, `isSubComposition`)는 모든 파일 호출에 전달된다. ⑥ 파일 호출마다 `linkedSources`(R-10)를 붙이고, 마운트된 모든 소스에서 모은 `projectFontFamilies`(`@font-face`와 Google Fonts 링크)를 준다. ⑦ 파일 결과의 error·warning·info 수를 더해 `totalErrors`·`totalWarnings`·`totalInfos`를 만든다. | 코드 확인 |
| R-09 | 프로젝트 단위 규칙 | 파일별 린트가 끝난 뒤 `allHtmlSources` 전체를 보고 도는 규칙이 있다. `code`: `audio_file_without_element`, `audio_src_not_found`, `missing_local_asset`, `texture_mask_asset_not_found`, `missing_stylesheet_asset`, `multiple_root_compositions`(`entryFile` 없을 때만, 프로젝트 루트의 `.html` 중 `data-composition-id`를 가진 것이 둘 이상이면 error), `blank_root_with_standalone_composition`(`entryFile` 없을 때만, 비어 있는 루트와 독립 컴포지션이 따로 있으면 error이고 `suggestedComposition`을 채운다), `duplicate_audio_track`, `missing_or_empty_sub_composition`, 그리고 HEVC·영상 `mediaStart` 파일 끝 초과(`hevcPreviewLint.ts`)와 shader 스크립트(`projectShaders.ts`) 규칙이다. 이 규칙들의 finding은 `file`이 가리키는 파일의 결과에 붙고(맞는 파일이 없으면 루트 결과), error이면 그 결과의 `ok`를 false로 바꾸고 해당 총계도 올린다. `missing_or_empty_sub_composition`은 서브 컴포지션 사용 가능 판정을 렌더 사전 점검과 같은 함수(`checkSubCompositionUsability`)와 같은 detail 문구로 한다. 렌더의 사전 점검 규칙은 [composition-contract R-15~R-17](./composition-contract.md#14-행동-규칙과-남은-질문-필수)을 따르고, 린트는 이를 던지지 않고 finding(error)으로 바꾼다. 중첩 호스트는 재귀로 따라가며 방문한 파일은 건너뛴다. `entryFile`을 주면(렌더의 `--composition`, `lint <파일>`) `multiple_root_compositions`와 `blank_root_with_standalone_composition`은 돌지 않는다(`project.ts:432-435`의 `!entryFile` 조건). | 코드 확인 |
| R-10 | 링크 파일 읽기(`linkedSources`) | HTML의 `<link rel="stylesheet" href>`와 `<script src>`가 로컬 경로이고 프로젝트 안에 있으며 확장자가 맞으면(CSS `.css`, 스크립트 `.js .mjs .cjs`, importmap `.json .importmap`) 내용을 읽어 `externalStyles`·`externalScripts`로 `lintHyperframeHtml`에 넘긴다. `*.min.js`와 1MB(1,000,000자)를 넘는 스크립트는 건너뛴다. 프로젝트 밖으로 나가는 경로는 읽지 않고 `scriptsOutsideProjectUnread`에 src를 적는다. private 경로는 `missing`으로 취급해 읽지 않는다. 서브 컴포지션 파일이면 파일 옆 상대 경로를 먼저, 안 되면 프로젝트 루트 상대 경로를 시도한다. template 안 태그도 찾는다. `core`의 `staticGuard`도 같은 함수를 쓴다(R-18). | 코드 확인 |

**C. 규칙 종류**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | 규칙군 | 개념 수준이다. code별 판정 조건·severity는 부록 A에 있고, 규칙 파일 위치는 C-02다. `rules/` 파일 하나가 한 그룹이고 아래는 파일별 대표 `code`와 한 줄 설명이다. 파일별 `code` 개수는 파일 안에서 `code: "..."` 리터럴을 센 값이다. `core`(20): `root_missing_composition_id`, `root_missing_dimensions`(루트에 `data-composition-id`, `data-width`·`data-height`가 없다), `timeline_id_mismatch`(`window.__timelines` 키와 컴포지션 id가 다르다). `composition`(28): `duplicate_composition_id`, `negative_z_index`, `missing_data_no_timeline`(타임라인 등록 없는 컴포지션), `deprecated_data_layer`, `deprecated_data_end`, `timed_element_missing_clip_class`. `media`(27): `duplicate_media_id`, `imperative_media_control`(스크립트가 play/pause를 직접 호출), `media_missing_data_start`, `video_missing_muted`. `gsap`(28): `gsap_infinite_repeat`, `overlapping_gsap_tweens`, `gsap_css_transform_conflict`, `non_deterministic_code`(렌더가 같은 프레임을 다시 만들 수 없는 값). `captions`(7): `caption_exit_missing_hard_kill`, `caption_text_overflow_risk`. `structure`(6): `nested_structure_needs_subcomposition`, `timeline_element_missing_timing`, `clip_ends_past_root_duration`, `nested_clip_never_visible`. 이 그룹의 severity는 `options.host === "studio"`이면 error, 아니면 warning이다. 단 `clip_ends_past_root_duration`은 항상 warning이다. `isSubComposition`이면 첫 규칙 함수(`nested_structure_needs_subcomposition`, `timeline_element_missing_timing`, `caption_track_kind_missing`, `multiple_caption_tracks`, `clip_ends_past_root_duration`)를 건너뛰고 두 번째 함수(`nested_clip_never_visible`)는 돈다. `fonts`(3): `system_font_will_alias`, `font_family_without_font_face`. `textures`(4): `texture_drop_shadow_on_text`, `texture_class_missing_base`. `adapters`(2): `missing_lottie_script`, `missing_three_script`(해당 라이브러리를 쓰는데 스크립트가 없다). `slideshow`(2): `slideshow_invalid`, `slideshow_unresolved_ref`. `rootPaths`(2): `root_path_missing_in_preview`, `import_map_invalid`. `shaders`(1): `shader_unbounded_cosine_pow`. helper 모듈 `linkedClips`(2): `linked_clip_orphan`, `linked_clips_out_of_sync`. `audioAttributes`(1): `audio_attribute_unreadable`. 위 개수의 합은 133이고(파일별 합이라 파일 사이 중복은 빼지 않았다), 프로젝트 단위 규칙까지 포함해 rules·project·hevcPreviewLint·projectShaders·hyperframeLinter 파일에서 `code: "..."` 리터럴을 센 서로 다른 값은 145개다. docs `lint-rules.mdx`의 `###` 제목은 144개다. 두 집합을 직접 비교하면 코드에만 있는 것이 4개(`gsap_loaded_after_use`, `import_map_invalid`, `root_path_missing_in_preview`, `shader_unbounded_cosine_pow`), docs에만 있는 것이 3개(`color_grading_invalid_json`, `color_grading_invalid_structure`, `color_grading_non_media`)이고 나머지 141개는 같다. docs에만 있는 3개는 `rules/media.ts`의 한 규칙이 `report(code, ...)` 호출 인자로 만들어 `code: "..."` 리터럴이 없어서 grep에 잡히지 않은 것이다. 따라서 위 media 그룹 27과 145는 이 3개를 뺀 값이고, 동적 code까지 세면 서로 다른 code는 148개다. 규칙 함수(`LINT_RULE_COUNT`)는 코드 주석(`hyperframeLinter.ts:28`)이 86개라고 쓰지만 실행해 확인하지 못했다(U-01). 규칙별 세부는 부록 A에 있고 읽은 범위는 `rules/*.ts` 14개 전부다. | 코드 확인(개수는 grep 값이고 실행 전)·함수 개수는 미확인 |
| R-12 | 규칙이 `data-*` 속성을 검사하는 지점 | 린트는 속성 의미를 새로 정하지 않고 두 방식으로 읽는다. ① 파서 함수를 그대로 쓴다. `composition.ts`의 `readTagTiming`이 `readClipTiming`을 부르고 그 diagnostics의 `deprecated-layer`, `deprecated-end` 등을 `deprecated_data_layer`·`deprecated_data_end`(후자는 `data-end`가 `data-duration`과 어긋날 때 메시지가 다르다) finding으로 바꾼다(속성 의미는 composition-contract R-06, R-07). `structure.ts`는 `readClipTiming`의 `start`·`end`로 `clip_ends_past_root_duration` 등을 판정한다. ② 규칙이 `Number(readAttr(...))`로 직접 읽는다(`composition.ts`의 길이 파생·`subcomposition_blanks_before_host` 등). 이 경로는 composition-contract R-01의 `parseStartExpression`을 거치지 않는다. 참조 시작(`data-start="intro + 2"`)은 `Number()`가 NaN이라서, 한 규칙에서는 끝을 모르는 clip으로(`end = null`) 처리하고 다른 규칙에서는 `\|\| 0`으로 0초로 처리한다. 즉 린트의 시각 판정은 런타임·정적 해석기가 참조를 푼 결과(composition-contract R-04)와 다를 수 있다. 린트는 참조 대상 id가 실제로 있는지는 검사하지 않는다(R-14). `data-track-index`의 렌더 무영향(composition-contract R-11)은 `deprecated_data_layer`의 fixHint에도 같은 취지("Neither name is read by the render")로 적혀 있다. 서브 컴포지션 사용 가능 판정은 R-09다. 규칙별 읽기 방식 세부는 부록 A(읽은 범위: `rules/*.ts` 14개 전부)다. | 코드 확인 |
| R-13 | `negative_z_index` 교차 확인(docs가 언급한 code) | 존재하고 동작한다. 규칙(`compositionRules` 안 한 함수)이 `<style>`과 링크 CSS, 그리고 태그의 `style=""` 속성에서 음수 `z-index` 선언을 찾아 warning을 만든다. 선택자가 `.class`·`#id` 한 개이고 그 요소 부모가 CSS 또는 인라인에서 stacking context를 만든다고 확인되면(`isolation`, `transform`, `filter`, `opacity<1`, `contain: paint`, `will-change`) 건너뛴다. 확인할 수 없는 경우는 finding을 낸다. severity는 warning이라 `lint` 종료 코드와 `--strict`가 아닌 렌더에는 영향이 없다. 메시지·fixHint는 `docs/reference/lint-rules.mdx`의 문구와 같은 내용이다. | 코드 확인 |
| R-14 | 문서가 말하는데 구현에서 못 찾은 규칙 | `docs/packages/lint.mdx`의 "Invalid `data-start` references to nonexistent clip IDs" 항목에 해당하는 규칙(참조 id가 존재하지 않는 `data-start`를 error·warning으로 내는 `code`)을 `packages/lint/src`에서 찾지 못했다(검색어는 2.1). `docs/reference/lint-rules.mdx`에도 해당 제목이 없다. 이 SHA에서 존재하지 않는 참조는 린트가 아니라 런타임·정적 해석기가 조용히 0 또는 null로 처리한다(composition-contract R-03, R-04). | 코드 확인(없다 주장, 범위는 2.1) |

**D. 렌더 차단**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-15 | `shouldBlockRender(strictErrors, strictAll, totalErrors, totalWarnings)` | `(strictErrors && totalErrors > 0) \|\| (strictAll && (totalErrors > 0 \|\| totalWarnings > 0))`다. 두 strict가 모두 false이면 항상 false다. info는 인자에 없어 판정에 들어가지 않는다. 브라우저 entry와 Node entry가 같은 함수를 내보낸다. | 코드 확인 |
| R-16 | CLI `render`의 렌더 전 린트 | `executeRenderPlan`이 브라우저 준비 전에 `runRenderLint`를 먼저 부른다(배치 렌더 포함). `lintProject(project.dir, 렌더 대상이 index가 아니면 그 파일)`을 돌린다(`signal`이 있으면 자식 프로세스). error와 warning이 모두 0이면 조용히 지나간다. 아니면 요약(또는 `--lint-verbose`나 중단 시 전체 목록)을 출력한다. 중단 조건은 `blank_root_with_standalone_composition` finding이 있거나(`--strict` 여부와 무관, 기본 index.html이 비어 있다는 메시지) `shouldBlockRender(plan.strictErrors, plan.strictAll, ...)`가 true일 때다. `--strict`는 `strictErrors`를, `--strict-all`은 `strictAll`과 `strictErrors`를 모두 켠다. 중단하면 `Cannot render: N error(s), M warning(s). <첫 error의 code: message> Run hyperframes lint for details.`를 내고 `CliRuntimeError`를 던져 렌더를 시작하지 않는다. 기본값(strict 없음)에서는 error가 있어도 렌더를 계속하고 "Continuing render despite lint issues. Use --strict to block errors."를 출력한다. `--strict`만 켜고 error 없이 warning만 있으면 계속하며 안내 문구가 다르다("Continuing render despite lint warnings. Use --strict-all to block warnings.", `renderLintContinuationHint`, `execute.ts:51-55`). 렌더 대상이 `--composition`으로 정한 비-index 파일이면 `lintProject`가 `entryFile`을 받아 돌므로 `blank_root_with_standalone_composition`과 `multiple_root_compositions`가 실행되지 않고(R-09), 위의 "strict 없이도 중단" 예외도 발동하지 않는다. 그때는 `shouldBlockRender`만 남는다. | 코드 확인 |
| R-17 | producer의 린트 | producer 렌더 파이프라인(`compileForRender` 등)은 린트를 부르지 않는다(검색은 2.1). producer가 가진 것은 HTTP `POST /lint`뿐이다. 본문으로 `projectDir`(+`entryFile`), `files`, `html` 중 하나를 받아 진입 HTML 하나를 `lintHyperframeHtml`로 돌리고(링크 파일·프로젝트 단위 규칙은 없다) 결과를 `{success:true, requestId, entryFile, source, result}`로 항상 HTTP 200으로 반환한다. 입력이 잘못되면 400이다. error가 있어도 서버가 거절하지 않고 차단 판정은 호출자 몫이다. 동시 worker는 2개이고, 슬롯을 15초 안에 못 얻어도 `lint_aborted`다. | 코드 확인 |
| R-18 | `bundleToSingleHtml`의 정적 가드 | 번들러(프리뷰·검사용 번들, composition-contract R-24)는 기본으로 `validateHyperframeHtmlContract`를 부른다. 이 함수는 `lintHyperframeHtml`(링크 파일 포함)을 돌려 severity가 error인 finding 메시지를 모으고, 있으면 `console.warn("[StaticGuard] Invalid HyperFrame contract: ...")`만 남긴다. 번들은 계속된다(차단 안 함). `staticGuard: false` 옵션이나 마운트 셸이면 건너뛴다. `failureReason` 분류는 메시지에 `data-composition-id`, `data-width`/`data-height`, `window.__timelines`, `script syntax`가 들어 있는지 문자열 검색으로 한다. | 코드 확인 |
| R-25 | 렌더 밖의 `lintProject`·`lintHyperframeHtml` 호출처 | 이 SHA에서 찾은 호출처는 다음과 같다. ① `publish`: index.html이 있으면 `lintProject(dir)`를 돌려 요약을 출력하고, `hasDefinitiveEntryMismatch`(`blank_root_with_standalone_composition`)이면 "Aborting publish because the default index.html entry is blank."로 중단한다. 일반 error·warning으로는 막지 않는다(`publish.ts:114-130`). ② `snapshot`: `lintProject(project.dir)` 결과가 같은 entry 불일치이면 "Aborting snapshot ..."로 중단하고(`snapshot.ts:1914-1916` 이후), 따로 `selfClosedMediaWarning`이 `lintHyperframeHtml(source)`에서 `self_closing_media_tag` finding만 골라 경고 한 줄을 만든다(`snapshot.ts:1655-1668`). ③ `media-treatment`: 처리한 HTML을 `lintHyperframeHtml`로 돌려 `color_grading_`으로 시작하는 code만 남기고, 그 중 error가 없으면 `lint.ok`다(`media-treatment.ts:734-736`). ④ `preview`: 시작할 때 자식 프로세스 `lint`(background)로 돌려 요약만 출력하고 막지 않으며 실패하면 경고한다(`preview.ts:638-657`). ⑤ Studio: studio-server의 `GET /projects/:id/lint`가 어댑터의 `lintProject`와 `lint`(프로젝트가 덮지 않은 HTML)를 모아 `{findings}`로 응답하고 동시 실행은 2개다(`studio-server/src/routes/lint.ts:10-89`). 어댑터는 두 가지다. CLI 서버는 자식 프로세스(`lintHtmlOutOfProcess`와 `runRenderSetupWorker("lint")`)로 `host: "studio"`를 넘기고(`studioServer.ts:623-630`), Vite 개발 서버는 `@hyperframes/core/lint`를 같은 프로세스에서 불러 `host: "studio"`를 넘긴다(`studio/vite.adapter.ts:299-307`). ⑥ 개발용 스크립트 `core/scripts/check-hyperframe-static.ts:57`, `test-hyperframe-linter.ts:27`. 번들러의 staticGuard는 R-18, `lint`·`check`·`validate`는 R-19~R-21이다. | 코드 확인(호출 경로. 각 명령의 나머지 흐름은 열지 않았다) |

**E. CLI 명령**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | `hyperframes lint [dir]` | `dir`이 `.html` 파일이면 그 파일을 `entryFile`로(그리고 `compositions/` 아래이면 `isSubComposition: true`), 폴더나 생략이면 프로젝트로 `lintProject`를 부른다. `host`는 넘기지 않는다(structure 규칙은 warning). 종료 코드는 `totalErrors > 0`이면 1, 아니면 0이다(warning만 있으면 0). `--json`이면 `{ok, errorCount, warningCount, infoCount, findings, filesScanned, unmountedCompositions}`에 메타를 더해 출력한다. `findings`는 모든 파일의 finding을 평평하게 이은 목록이고 `--verbose`(또는 `--lint-verbose`)가 아니면 info를 뺀다. 카운트 필드는 info를 뺀 목록과 상관없이 전체 수다. 텍스트 모드는 error·warning이 모두 0이면 info가 있어도 `0 errors, 0 warnings`만 출력하고 끝내므로 `--verbose`로도 info를 볼 수 없다. 마운트되지 않은 컴포지션이 있으면 `unmountedNotice` 한 줄을 안내한다. 줄 형식은 `<prefix> [<file>:<line>:<column>] <code> [<elementId>]: <message>`와 다음 줄 `Fix: <fixHint>`이고 파일이 여럿일 때만 위치 없는 finding에도 `[<file>]`을 붙인다. 린트 자체가 던지면 R-07이다. | 코드 확인 |
| R-20 | `hyperframes check` | 한 번의 실행에서 lint, runtime, layout, motion, contrast(WCAG AA), craft, audio를 합친 보고서(`CheckReport`)를 만든다. 린트는 `lintProject(dir, undefined, {}, {includeUnmounted})`로 가장 먼저 돈다. `lint` 섹션은 모든 finding을 `CheckFinding` 모양(`code`, `severity`, `message`, `selector`(없으면 `#elementId`, 그것도 없으면 `[data-composition-id]`), `sourceFile`, `bbox`는 0 크기, `time` 0, `fixHint`)으로 바꾸고 `filesScanned`를 더한다. 린트에 `root_missing_composition_id` error가 루트 결과에 있으면 브라우저 단계를 건너뛰고(빈 브라우저 결과) "Layout, motion, and contrast were not checked" 안내를 낸다. 다른 린트 error는 브라우저 측정을 막지 않는다. `ok = errorCount === 0 && (!strict \|\| strictWarningCount === 0)`이고 `errorCount`는 모든 섹션(lint 포함)의 error 합이다. `--strict`일 때 warning 합에서 craft 경고와 가이드 성격의 layout 경고는 뺀다. 종료 코드는 `ok ? 0 : 1`이다. `--json`은 보고서 전체를 출력한다. 린트가 던지면 `check_lint_failure`(R-07). | 코드 확인 |
| R-21 | `hyperframes validate`(deprecated, 안내문에서 `check`를 권한다) | `lintProject(dir)` 결과에서 `missing_or_empty_sub_composition` error만 골라 콘솔 오류 목록(`errors`)에 먼저 넣는다. 나머지 린트 finding은 쓰지 않는다. 이유는 코드 주석에 있다. 번들러가 사용할 수 없는 서브 컴포지션을 경고만 남기고 건너뛰므로 브라우저 로드만 보면 깨진 영상이 "오류 없음"으로 나온다는 것이다. 그 다음 번들 HTML을 headless Chrome에 띄워 콘솔 오류·경고를 모으고, contrast 감사(기본 켬, `--contrast`)를 한다. contrast 실패는 `warnings` 쪽 요약(`contrastFailures` 개수)이고 종료 코드에 영향이 없다. 종료 코드는 `errors.length > 0`이면 1이다. `--json` 출력은 `{ok, errors, warnings, contrast, contrastFailures}`이다. | 코드 확인 |
| R-22 | `hyperframes layout`(deprecated) | 린트를 호출하지 않는다(파일에 lint 관련 호출이 없다). 번들 HTML을 headless Chrome에 띄우고 `layout-audit.browser.js`의 `window.__hyperframesLayoutAudit`를 시점마다 불러 `LayoutIssue[]`(`code`, `severity`, `time`, `selector`, `message`, `rect`, `fixHint` 등, `code`는 `text_box_overflow`, `canvas_overflow`, `text_occluded` 등 닫힌 목록)를 모은다. `ok = errorCount === 0 && (!strict \|\| warningCount === 0)`이고 종료 코드는 `ok ? 0 : 1`이다(JSON 모드와 텍스트 모드 모두). `--json` 보고서에 `ok`, `issues`, 개수, `schemaVersion: 1`이 들어간다. 시료 시점이 하나도 없으면(길이를 알 수 없음) 텍스트 모드는 오류를 내고 실패한다. `bundleToSingleHtml`을 거치는 명령은 모두 staticGuard로 린트를 간접 호출할 수 있다. `layout`뿐 아니라 `validate`(`validate.ts:453`)와 `check`의 브라우저 단계(`checkBrowser.ts:427-428`, `bundleWithLocalizedFonts`가 `bundleToSingleHtml`을 부름)도 해당하고, 결과는 `console.warn`만 남아 종료 코드·보고서에 반영되지 않는다(R-18). | 코드 확인 |
| R-23 | contrast 감사 결과 형식과 호출 관계 | contrast는 린트 엔진이 아니라 브라우저 안에서 `contrast-audit.browser.js`가 측정한다(`check`와 `validate`가 각자 페이지에 주입). 측정 결과 항목은 `{text, ratio, wcagAA, large, fg, bg, selector, bbox, time...}`이다. `check`는 `wcagAA`가 false인 항목을 `contrast_aa_failure` finding으로 바꾸고, 같은 요소가 2개 이상 시점에서 실패하면(또는 시점이 하나뿐이면) error, 아니면 warning으로 낮춘다(한 시점에서만 실패하는 요소는 진입·퇴장 중인 텍스트일 가능성이 높다는 코드 주석). `validate`는 항목을 그대로 경고로 보여 준다(R-21). 측정 알고리즘 세부(전경·배경 색 추정, occlusion, clip 판정)는 이 스펙 범위 밖이다. | 코드 확인(호출 관계와 형식). 알고리즘은 범위 밖 |
| R-24 | 패키지 경계와 중복 | 린트 구현은 `packages/lint`에 한 벌이다. `packages/core/src/lint/index.ts`는 `export * from "@hyperframes/lint"`만 하는 deprecated 재내보내기라서 구현이 없다(Studio vite 어댑터와 core 번들러는 이 경로 또는 `@hyperframes/lint`를 import). producer의 `hyperframeLint.ts`는 린트 엔진을 갖지 않고 타입만 import하고, worker가 `@hyperframes/lint`의 `lintHyperframeHtml`을 부른다. CLI `utils/lintProject.ts`는 `lintProject`·`shouldBlockRender`를 다시 내보내고 `blank_root_with_standalone_composition` 판정 helper를 더한다. 브라우저용 entry(`@hyperframes/lint/browser`)는 `lintHyperframeHtml`, `lintMediaUrls`, `shouldBlockRender`만 내보내고 `lintProject`는 없다. `lintMediaUrls`는 `lintHyperframeHtml` 안에서 부르지 않는다. 이 SHA에서 `packages/lint/src` 밖의 호출처를 찾지 못했다(검색은 2.1). | 코드 확인 |

- 불변식: `shouldBlockRender`는 순수하다. `lintHyperframeHtml`은 같은 `html`·`options`에 대해 같은 findings를 낸다(시간·난수를 쓰지 않는다. `timings`는 제외). 한 호출 안에서 dedupe 키가 같은 finding은 없다. 깨지는 곳: `lintProject`는 파일 시스템 내용에 의존한다.
- 미결정: 아래 표.

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-05, R-11 | `LINT_RULE_COUNT`(규칙 함수 수)의 실제 값은 얼마인가. 코드 주석(`hyperframeLinter.ts:28`)은 86이다. `code` 집합 차이는 R-11에서 이미 비교했다(코드에만 4개, docs에만 3개이고 후자는 동적 생성). | 학습에는 영향이 없다. 재구현자가 규칙 수나 회귀 비교용 `slowestRule` 번호를 맞추려면 필요하다. | 의존성을 설치해 `LINT_RULE_COUNT`를 출력한다. |

- 확인 한계: 린트·CLI 명령을 실행하지 않았다(의존성 설치 없음). 렌더 전 린트에서 자식 프로세스가 던진 오류가 사용자에게 어떻게 표시되는지는 `render` 명령의 바깥 오류 처리까지 따라가지 않았다(R-07). `.hyperframesignore` 패턴의 세부 의미는 `ignore` 패키지(외부 의존)에 따른다. 부록 A의 한계: 각 규칙 파일 앞부분의 순수 helper(CSS 파서 보조, `composition.ts`의 canvas `zoom` 선택자 매칭, `gsap.ts`의 GSAP window·표현식 파서, `utils.ts`)와 `shaderDomains.ts`의 패턴은 열지 않았고, helper가 판정하는 세부 조건은 규칙 이름과 호출 맥락으로만 적었다. 규칙은 실행하지 않았고 테스트 본문도 열지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스는 Apache-2.0(overview 1절)이고 인용을 허용한다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `packages/lint/src/types.ts:1-75` | severity, finding, result, options, `LintRule` 타입 | R-01, R-02 |
| C-02 | `packages/lint/src/hyperframeLinter.ts:37-177` `RULE_GROUPS`, `dedupeKeyFor`, `runRules`, `collectFindings`, `lintHyperframeHtml` | 규칙 그룹 순서, dedupe 키, 실행 루프, 위치 보정 예외 목록, 결과 조립 | R-01, R-02, R-03, R-05, R-07 |
| C-03 | `packages/lint/src/hyperframeLinter.ts:181-269` `extractMediaUrls`, `lintMediaUrls` | 원격 media HEAD 검사 | R-24 |
| C-04 | `packages/lint/src/context.ts:8-103` `LintContext`, `buildLintContext` | context 필드, 주석 제거, template 해제, 링크 파일 병합, `locate` | R-06, R-03 |
| C-05 | `packages/lint/src/sourceLocations.ts:7-68` `normalized`, `createSourceLocator`, `snippetOffset` | snippet·id 기반 위치 찾기, 모호하면 위치 없음 | R-03 |
| C-06 | `packages/lint/src/sourceCoordinates.ts:8-37` `mappedHtmlSource`, `sourcePosition` | 주석 제거 후 offset 되돌리기, 1부터 시작하는 line·column | R-03 |
| C-07 | `packages/lint/src/shouldBlockRender.ts:5-12` | 렌더 차단 진리식 | R-15 |
| C-08 | `packages/lint/src/projectIgnore.ts:1-13`, `packages/lint/src/linkedFile.ts:1-7` | 무시 기본 패턴과 `.hyperframesignore`, private 경로 읽기 거부 | R-04, R-10 |
| C-09 | `packages/lint/src/project.ts:95-110`, `185-246`, `292-316`, `334-460`, `1071-1075` `ProjectLintResult`, `linkedSources`, `collectExternalScripts`, `mountedSources`, `lintProject`, `isSnippetFragment` | 프로젝트 린트 흐름, 대상 선택, 링크 파일 읽기, 결과 분배 | R-08, R-09, R-10 |
| C-10 | `packages/lint/src/project.ts:980-1069` `lintMissingOrEmptySubComposition` | 서브 컴포지션 사용 가능 판정을 finding으로 바꾸는 규칙 | R-09 |
| C-11 | `packages/lint/src/rules/composition.ts:840-873`, `1272-1317` | `negative_z_index` 판정과 메시지 | R-13 |
| C-12 | `packages/lint/src/rules/composition.ts:89-91`, `1060-1095`, `1455-1470`, `1975-1985`, `packages/lint/src/rules/structure.ts:180-215` | 린트가 `data-*` 시간 속성을 읽는 두 방식(`readClipTiming`과 `Number()`) | R-12 |
| C-13 | `packages/lint/src/rules/structure.ts:231-254` `structureRules` | host에 따른 severity 분기 | R-11 |
| C-14 | `packages/producer/src/services/hyperframeLint.ts:123-285`, `hyperframeLintWorker.ts:1-12`, `packages/producer/src/server.ts:835-880` | `/lint` 입력 정리, worker 격리, `lint_aborted`, 응답 형식 | R-07, R-17 |
| C-15 | `packages/cli/src/commands/render/execute.ts:53-69`, `284-359` `renderLintShouldAbort`, `runRenderLint`, `presentRenderLintAbort` | 렌더 전 린트와 중단 조건·메시지 | R-16 |
| C-16 | `packages/cli/src/commands/render/plan.ts:677-678`, `packages/cli/src/utils/lintProject.ts:1-23` | `--strict`·`--strict-all` 해석, entry 불일치 판정 | R-16 |
| C-17 | `packages/cli/src/commands/lint.ts:55-143` | `lint` 명령의 인자 해석, JSON 모양, 종료 코드 | R-19 |
| C-18 | `packages/cli/src/utils/checkPipeline.ts:1727-1760`, `1985-1987`, `2010-2050`, `2062-2155` | `check`의 린트 호출, 브라우저 건너뛰기 조건, 섹션 변환, `ok` 계산, contrast finding | R-20, R-23 |
| C-19 | `packages/cli/src/commands/validate.ts:385-395`, `435-449`, `716-731` | `validate`가 쓰는 린트 code와 종료 코드 | R-21 |
| C-20 | `packages/cli/src/commands/layout.ts:545-580` | `layout`의 `ok`와 종료 코드(린트 호출 없음) | R-22 |
| C-21 | `packages/core/src/compiler/staticGuard.ts:15-45`, `packages/core/src/compiler/htmlBundler.ts:1140-1154` | 번들러의 정적 가드(경고만) | R-18 |
| C-22 | `packages/cli/src/utils/lintHtmlWorker.ts:30-68`, `packages/cli/src/renderSetupWorker.ts:44-60` | 자식 프로세스 린트와 `lint_aborted` | R-07 |
| C-23 | `packages/cli/src/commands/publish.ts:114-130`, `snapshot.ts:1655-1668`, `snapshot.ts:1914-1916`, `media-treatment.ts:734-736`, `packages/studio-server/src/routes/lint.ts:10-89` | 렌더 밖 호출처가 린트 결과에서 쓰는 code와 중단 조건 | R-25 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출. 원본 테스트 파일은 열지 않았다(`negative_z_index`의 테스트 이름만 검색으로 확인). 실행하지 않았고 코드 경로를 따라 기대값을 계산했다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-13, R-03, R-02 | `<style>#bg { z-index: -1 }</style>`와 `<div id="bg">`(부모에 stacking context 없음)가 든 컴포지션 HTML에 `lintHyperframeHtml` | `code: "negative_z_index"`, `severity: "warning"`, `selector: "#bg"`, `snippet`이 있는 finding이 나온다. 그 snippet이 원본에서 한 곳에만 있으면 `line`·`column`(1부터)이 붙는다. `ok`는 다른 error가 없으면 true다. |
| T-02 | R-13 | 같은 선언인데 부모 `#stage { isolation: isolate }`가 CSS에 있다 | `negative_z_index` finding이 없다. |
| T-03 | R-15 | `shouldBlockRender(false,false,5,5)`, `(true,false,0,3)`, `(true,false,1,0)`, `(false,true,0,1)` | false, false, true, true. |
| T-04 | R-16 | `hyperframes render`(옵션 없음), 프로젝트에 error 1개가 있다 | 요약과 "Continuing render despite lint issues. Use --strict to block errors."를 출력하고 렌더를 계속한다. `--strict`를 주면 `Cannot render: 1 error(s), 0 warning(s). <code>: <message> ...`를 내고 렌더를 시작하지 않는다. warning만 있고 `--strict`이면 계속하고, `--strict-all`이면 막는다. |
| T-05 | R-16, R-09 | index.html에 자식이 없는 `data-composition-id` 루트가 있고 `compositions/intro.html`이 독립 컴포지션이다 | `blank_root_with_standalone_composition` error. `--strict` 없이도 렌더가 `Cannot render: the default index.html entry is blank.`로 중단한다. |
| T-06 | R-19 | `hyperframes lint --json`, warning 2개와 info 1개만 있다 | `ok: true`, `warningCount: 2`, `infoCount: 1`, `findings`에는 warning 2개(info는 `--verbose`일 때만 포함). 종료 코드 0. error가 1개면 `ok: false`, 종료 코드 1. |
| T-07 | R-19 | 텍스트 모드, error·warning 0개, info 1개, `--verbose` | `0 errors, 0 warnings`만 출력되고 info는 나오지 않는다(R-19의 조기 반환). |
| T-08 | R-20 | `check`, 린트 warning 1개와 `contrast_aa_failure` error 없음, `--strict` 없음 | `ok: true`, 종료 코드 0. `--strict`를 주면 lint warning이 `strictWarningCount`에 들어가 `ok: false`, 종료 코드 1이다. |
| T-09 | R-20 | `check`, index.html 루트에 `data-composition-id`가 없다 | `root_missing_composition_id` error가 lint 섹션에 있고, 브라우저 단계는 실행하지 않아 layout·motion·contrast가 비어 있다. 종료 코드 1. |
| T-10 | R-21 | `validate`, `compositions/a.html`이 빈 파일이고 `index.html`이 마운트 | 린트 finding `missing_or_empty_sub_composition` error가 `errors`에 들어가 종료 코드 1이다. 같은 프로젝트의 `negative_z_index` warning은 `validate` 출력에 나오지 않는다. |
| T-11 | R-04 | `.hyperframesignore`에 `compositions/draft/`가 있고 `compositions/draft/x.html`이 오류를 가진다 | `lintProject`가 그 파일을 순회에서 제외하므로 `results`에 없다. index.html에 같은 오류가 있으면 제외되지 않는다. |
| T-12 | R-07 | `lintHtmlOutOfProcess` 자식이 15초 안에 끝나지 않는다 | `lint_aborted` error 하나를 가진 결과(`ok:false`, `errorCount:1`)를 반환하고 같은 프로세스에서 다시 린트하지 않는다. |
| T-13 | R-03 | 같은 `id="a"` 태그가 두 개 있고 finding에 `elementId: "a"`만 있고 snippet이 없다 | `line`·`column`이 붙지 않는다. |
| T-14 | R-08 | `lintProject(dir, "/other/place/x.html")`(프로젝트 밖) | `Explicit lint entry is outside the project directory: ...` Error를 던진다(CLI `lint`는 `runtime_error`와 종료 코드 1). |
| T-15 | R-16 | `hyperframes render --strict`, 프로젝트에 warning만 있고 error는 없다 | 요약 뒤에 "Continuing render despite lint warnings. Use --strict-all to block warnings."를 출력하고 렌더를 계속한다. `--strict-all`이면 `Cannot render: 0 error(s), N warning(s). ...`로 중단한다. |
| T-16 | R-16, R-09 | `hyperframes render --composition compositions/a.html`이고 index.html은 빈 루트다 | `lintProject`가 `entryFile`로 돌아 `blank_root_with_standalone_composition` 규칙이 실행되지 않으므로 strict 없이도 중단하는 예외가 발동하지 않는다. error가 있어도 `--strict`가 없으면 렌더를 계속한다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@5979991 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-01, C-02: `hyperframeLinter.ts:74-83`, `165-177` | 코드 확인. 문서 `docs/packages/lint.mdx:76-80`의 "each result entry: { file, result }"에는 `contentHash`가 빠져 있다(구현은 `project.ts:96`에 `contentHash`가 있다). 구현을 사실로 썼다. |
| R-03 | C-02 `hyperframeLinter.ts:140-163`, C-05, C-06, C-04 `context.ts:82-90` | 코드 확인. 줄 번호 계산은 `sourcePosition`과 `createSourceLocator`의 `at`이 같은 식을 쓴다. 예외 코드 목록은 `hyperframeLinter.ts:144-151`을 옮겼다. 실행해 값을 확인하지 않았다. |
| R-04 | C-08 `projectIgnore.ts:1-13`, `project.ts:372-377`, `publishProject.ts:16`(import), `rules/gsap.ts:1922-1923`(주석: "No suppression by design: there is intentionally no per-line/per-file opt-out") | "finding 단위 무시 설정이 없다"는 주장이다. 검색: `grep -rniE "lint-ignore\|lintignore\|hyperframesignore\|disable.*rule\|ignoreRules\|suppress" --include=*.ts --include=*.mdx` 대상 `packages/lint/src`, `packages/cli/src`, `packages/producer/src`, `docs`(changelog 제외). `hyperframesignore`는 `projectIgnore.ts`와 클라우드·publish 코드에서만 나왔다. `lint-ignore` 계열은 나오지 않았다. 놓쳤을 가능성: `packages/studio`·`packages/sdk` 등 검색하지 않은 패키지, 규칙 안의 지시자 주석을 다른 이름으로 읽는 코드(규칙 함수 전체를 읽지는 않았다). 기본 패턴 `.*`가 렌더 출력 등을 거르는 목적은 코드에 이유 주석이 없다(추론 아님, 목적 서술하지 않음). 무시 경로 형식은 `project.ts:376-377`(`relPath`를 `compositions/` 접두로 `ignores`에 넘김)에서 확인했다. |
| R-05 | C-02 `hyperframeLinter.ts:25-61`, `rules/*.ts`의 `export const ...Rules` 12개(`adapters.ts:10`, `captions.ts:3`, `composition.ts:907`, `core.ts:450`, `fonts.ts:210`, `gsap.ts:1114`, `media.ts:489`, `rootPaths.ts:58`, `shaders.ts:16`, `slideshow.ts:50`, `structure.ts:231`, `textures.ts:133`), `media.ts:21-22`(`linkedClips`, `audioAttributes` import) | 코드 확인. "등록 API나 동적 발견이 없다"는 `RULE_GROUPS` 하나가 유일한 목록이라는 뜻이다. 검색: `RULE_GROUPS`, `Rules` 배열 import를 `packages/lint/src`에서 확인했다. 다른 패키지에서 규칙을 추가하는 코드는 찾지 않았다. `RULE_GROUPS` 순서(`hyperframeLinter.ts:41-52`)를 직접 읽어 core, media, gsap, captions, composition, adapters, textures, fonts, slideshow, structure, shaders, rootPaths임을 확인했고 1.4 R-05의 나열과 같다. |
| R-06 | C-04 | 코드 확인. `utils.ts`의 `parseHtmlStructure`, `findRootTag` 본문은 앞 부분만 읽었다(htmlparser2 기반인 점과 `findRootTag`의 body 우선 규칙까지). |
| R-07 | C-02 `hyperframeLinter.ts:90-117`(try/catch 없음), `lint.ts:120-142`, `checkPipeline.ts:1743-1754`, `lintHtmlWorker.ts:20-75`, `hyperframeLint.ts:217-285`, `renderSetupWorker.ts:44-62`, `studioServer.ts:623`, `execute.ts:292-295` | 코드 확인. "규칙 함수 안 try/catch가 없다"는 `runRules`·`lintHyperframeHtml` 범위만 확인했다. 개별 규칙 내부에서 예외를 삼키는지는 전체를 읽지 않아 모른다(예: `lintMultipleRootCompositions`는 삼킨다, 코드 확인). 렌더 명령의 바깥 오류 표시는 추론이다. |
| R-08 | C-09 `project.ts:334-460`, `292-316`, `1071-1075` | 코드 확인. |
| R-09 | `project.ts:425-457`, 각 함수 `:462`, `503`, `552`, `602`, `688`, `753`, `805`, `935`, `980`, `hevcPreviewLint.ts:264`(`lintVideoMediaStartPastEof`), `projectShaders.ts` | `code` 이름은 `grep -n 'code: "' project.ts`로 확인했다. 각 규칙 판정 세부는 열지 않았다(부록 A는 `rules/*.ts`만 다루고 프로젝트 단위 규칙은 포함하지 않는다). 선행 스펙과의 연결은 C-10이 `checkSubCompositionUsability`를 `@hyperframes/parsers/sub-composition-validity`에서 import(`project.ts:27`)하는 것으로 확인했다. |
| R-10 | C-09 `project.ts:127-246`, C-08 `linkedFile.ts:1-7`, C-21 | 코드 확인. |
| R-11 | `rules/*.ts` | 파일별 `code` 개수는 `grep -oE 'code: "[a-z0-9_]+"' <file>`에 `sort -u`, `wc -l`을 이어 센 결과다(adapters 2, audioAttributes 1, captions 7, composition 28, core 20, fonts 3, gsap 28, linkedClips 2, media 27, rootPaths 2, shaders 1, slideshow 2, structure 6, textures 4). 145는 테스트 파일을 뺀 `rules/*.ts`, `project.ts`, `hevcPreviewLint.ts`, `projectShaders.ts`, `hyperframeLinter.ts`를 합쳐 센 서로 다른 값이다. docs 144는 `lint-rules.mdx`에서 `### ` 제목을 센 값이다. 두 목록을 `comm`으로 비교한 차이는 코드에만 4개, docs에만 3개이고, docs에만 있는 `color_grading_*` 3개는 `media.ts:544-595`가 `report(code, ...)` 인자로 만들어 리터럴 grep에서 빠진다. 규칙 함수 개수는 코드 주석 86을 인용했을 뿐 직접 세지 못했다(U-01). 규칙 조건은 부록 A에서 `rules/*.ts` 14개 전부의 규칙 배열과 그 안에서 부르는 규칙 함수를 읽어 정리했다(범위와 한계는 1.4의 확인 한계). 부록에서 확인한 code 수는 core 20, gsap 28, composition 28, media 30(리터럴 27과 동적 `color_grading_*` 3), captions 7, structure 6, fonts 3, textures 4, adapters 2, slideshow 2, rootPaths 2, shaders 1, linkedClips 2, audioAttributes 1이다. |
| R-12 | C-12 | 코드 확인. `readTagTiming` 사용은 `composition.ts:89`와 호출 지점을 읽었다. composition-contract R-01과의 차이는 `composition.ts:1464`(`Number(...) \|\| 0`)와 `:1978-1982`(비유한 start를 `null`로)에서 확인했다. 이 외의 규칙에도 `Number()` 직접 읽기가 더 있을 수 있다(전수 확인 안 함). 린트에 참조 id 존재 검사가 없다는 주장은 R-14. 부록 A를 쓰면서 읽은 규칙 본문에서 `Number()` 직접 읽기를 더 확인했다(`media.ts`의 `nested_media_start_basis_ambiguous`·`data-volume` 읽기, `linkedClips.ts`의 timing 필드, `slideshow.ts`의 `parseTiming`, `composition.ts`의 `subcomposition_blanks_before_host`·`deriveDurationFromClips`). 파일 앞부분의 순수 helper는 열지 않았다. |
| R-13 | C-11, `rules/composition.test.ts:2913-3029`(테스트 이름 검색으로 케이스 존재만 확인, 본문 안 읽음), `docs/reference/lint-rules.mdx:147-151` | 코드 확인. 실행은 안 했다. 문서의 severity(Warning)와 코드(`composition.ts:858`)가 같다. |
| R-14 | `docs/packages/lint.mdx`("Invalid `data-start` references to nonexistent clip IDs" 항목), `packages/lint/src` 검색 | "없다" 주장이다. 검색: `grep -rnEi "nonexistent\|does not exist\|no element with id\|unknown (clip\|element)\|refId\|reference.*(id\|clip)\|invalid.*start" packages/lint/src --include=*.ts --exclude=*.test.ts`, 그리고 `start-reference\|invalid-start\|reference_\|invalid_data_start\|missing_reference\|unresolved_start\|invalid_start`. 나온 것은 무관한 줄(에셋·HEVC 참조 등)뿐이다. `docs/reference/lint-rules.mdx`에서 `grep -n "start-reference\|nonexist\|invalid.*start\|data_start"`는 `media_missing_data_start`만 나왔다. 놓쳤을 가능성: 규칙이 `code`에 `start`를 쓰지 않고 `readClipTiming`의 `unresolved-start-reference` diagnostics를 다른 이름으로 노출하는 경우. `structure.ts`는 `readClipTiming`의 `start`·`end`만 쓰고 diagnostics를 보지 않는 것까지 확인했다(`:182`, `:210-213`). |
| R-15 | C-07 | 코드 확인. 사용처는 `grep -rn "shouldBlockRender" packages`로 확인했고 이 함수를 호출하는 곳은 CLI `render/execute.ts:65` 하나다(테스트 제외). |
| R-16 | C-15 `execute.ts:100`(호출 위치), `53-69`, `284-310`, `341-359`, C-16 `render/plan.ts:677-678`, `render.ts:346-355`(플래그 설명), `utils/lintProject.ts:9-12` | 코드 확인. `lintProject`의 실패 경우는 R-07. 비-index 렌더의 `entryFile`은 `render/plan.ts:331-332`(`resolveCompositionEntryArg(args.composition ...)`)와 `execute.ts:291`로 확인했다. |
| R-17 | C-14, `server.ts:11`(주석 "POST /lint — blocking Hyperframe lint"), `index.ts:158-160` | "producer 렌더 파이프라인이 린트를 부르지 않는다"는 주장이다. 검색: `grep -rniE "lint" --include=*.ts --exclude=*.test.ts packages/producer/src`에서 `services/hyperframeLint*.ts`를 제외하면 `index.ts`(재내보내기), `server.ts`(`/lint` 경로), 무관한 줄(`renderRequest.ts`의 `assertOptionalInteger`, `probeStage.ts:327` 주석, `captureSegmentedStage.ts` 문자열)만 나왔다. 놓쳤을 가능성: 서버의 `/render` 핸들러 앞단 미들웨어나 외부 호출자(클라우드 서비스)가 먼저 `/lint`를 부르는 구성은 이 레포에서 확인하지 않았다. 주석의 "blocking"은 요청이 린트 완료까지 기다린다는 뜻으로 읽었다(추론). 렌더를 막는다는 뜻이 아니라는 근거는 핸들러가 항상 200과 result를 반환하는 코드다. |
| R-18 | C-21, `htmlBundler.ts:1141`(`options?.staticGuard !== false && !mountedShell`) | 코드 확인. |
| R-19 | C-17, `lintFormat.ts:19-110`, `utils/project.ts:103-115`(`resolveLintTarget`) | 코드 확인. info 조기 반환은 `lint.ts:106-109`와 `formatLintFindings`의 `verbose` 처리를 함께 읽고 도출했다. |
| R-20 | C-18, `check.ts:330-380`, `checkPipeline.ts:2495`(`lintProject` 호출 인자) | 코드 확인. `strictWarningCount`는 `checkPipeline.ts:2117-2121`. 브라우저 단계 세부(`runBrowserCheck`)는 읽지 않았다. 호출 관계는 `checkBrowser.ts:1225-1229`(스크립트 주입)까지 확인했다. 정규 종료 코드 규칙(0 성공, 1 실패, 2 사용법 오류)은 `packages/cli/AGENTS.md`의 서술이다. |
| R-21 | C-19, `validate.ts:700-715` | 코드 확인. |
| R-22 | C-20, `layout.ts:296-312`(`window.__hyperframesLayoutAudit`), `utils/layoutAudit.ts:14-75`(`LayoutIssue`) | "layout이 린트를 부르지 않는다"는 주장이다. 검색: `grep -n "lint\|Lint" packages/cli/src/commands/layout.ts` 결과 없음. 간접 호출(`layout.ts`가 import한 모듈이 린트를 부르는 경우)은 `utils/layoutAudit.ts`·`motionAudit.ts`·`staticProjectServer.ts`를 열지 않아 확인하지 못했다. 번들러가 `staticGuard`로 린트를 부르므로(R-18) `bundleToSingleHtml`을 거치는 `layout`은 린트 error를 `console.warn`으로 간접 노출할 수 있다(`layout.ts:166-169`에서 `bundleToSingleHtml` 호출 확인, `staticGuard` 기본값 true는 `htmlBundler.ts:1141`에서 확인. 종합은 추론). `check`와 `validate`의 `bundleToSingleHtml` 호출은 `utils/bundleWithLocalizedFonts.ts:27`, `validate.ts:453`에서 확인했다. |
| R-23 | C-18 `checkPipeline.ts:2010-2050`, `checkTypes.ts:101-139`, `checkBrowser.ts:1229`, `validate.ts:560-566` | 코드 확인(호출 관계와 형식). `contrast-audit.browser.js` 본문은 열지 않았다. |
| R-24 | `core/src/lint/index.ts:1-2`, `lint/src/index.ts:1-17`, `browser.ts:1-19`, `producer/src/services/hyperframeLint.ts:13`, `hyperframeLintWorker.ts:4`, `docs/packages/lint.mdx:15-25`(core 재내보내기 설명) | "중복 구현이 아니다"는 `grep -rn "from \"@hyperframes/lint\|core/lint" packages --include=*.ts --exclude=*.test.ts`로 호출 경로를 보고 판단했다. `lintMediaUrls` 호출처: `grep -rn "lintMediaUrls" packages --include=*.ts --include=*.tsx --exclude=*.test.ts`를 돌려 `packages/lint/src` 밖의 결과가 없음을 확인했다("호출처 없음" 주장). 놓쳤을 가능성: 문자열로 조합한 동적 호출, `docs`의 예시 코드, 외부 소비자(이 레포 밖). |
| R-25 | `publish.ts:114-130`, `snapshot.ts:1655-1668`, `snapshot.ts:1914-1916`, `media-treatment.ts:734-736`, `preview.ts:638-657`, `studio-server/src/routes/lint.ts:10-89`, `studioServer.ts:623-630`, `studio/vite.adapter.ts:299-307`, `core/scripts/check-hyperframe-static.ts:57`, `test-hyperframe-linter.ts:27` | 호출처 목록이 그 밖에 없다는 전칭 주장이다. 검색은 `lintProject`, `lintHyperframeHtml`, `@hyperframes/lint`, `core/lint`를 `packages` 아래 `.ts`와 `.tsx`(테스트 제외)에서 찾아 나온 파일을 열어 호출 여부를 확인했다. 놓쳤을 가능성: 변수로 조합한 동적 import, type import로 보여 열지 않은 `packages/sdk`·`packages/player` 등의 파일, 이 레포 밖 소비자. |
| T-01~T-14 | 각 관련 R-ID의 근거 | 모두 구현에서 도출. 실행하지 않았다. |

### 2.2 코드 읽는 순서 [선택]

1. `packages/lint/src/types.ts`로 finding·result 모양을 본다.
2. `hyperframeLinter.ts`의 `lintHyperframeHtml`(133행)에서 `buildLintContext`(context.ts) → `runRules` → 위치 보정 순서로 읽는다.
3. 규칙 하나를 끝까지 본다. 가장 짧은 `rules/adapters.ts`의 `missing_lottie_script`(destructuring한 context 필드와 finding 한 개), 그 다음 `composition.ts`의 `negative_z_index`.
4. `project.ts`의 `lintProject`(334행)에서 파일 선택 → 파일별 `lintHyperframeHtml` → 프로젝트 단위 규칙 순서로 읽는다.
5. 호출자는 `cli/src/commands/lint.ts`, `render/execute.ts`의 `runRenderLint`, `utils/checkPipeline.ts`의 `runCheckPipeline` 순서로 본다.

### 2.3 비교·재사용 출처 [선택]

없음.

### 2.4 검토 기록 [필수, ready 스펙]

`draft` 스펙이라 해당 없음. 메인 점검 전이다.

## 적용 메모 [선택]

없음.

## 부록 A. 규칙 카탈로그

`packages/lint/src/rules/*.ts`를 읽고 `code`마다 severity와 발동 조건을 적은 표다. 이 SHA 구현이 사실이고 docs와 다르면 구현을 따랐다. 읽는 방법: severity가 두 가지로 적힌 규칙은 조건에 따라 분기한다. 테스트 파일은 열지 않았다. 그룹 순서는 R-05의 `RULE_GROUPS` 순서다.

| 파일 그룹 | code | severity | 발동 조건·임계값 |
|---|---|---|---|
| core | `id_requires_css_escape` | error 또는 warning | 태그 `id`가 숫자로 시작한다. 같은 컴포지션의 CSS·스크립트 선택자가 `#<id>`로 그 id를 실제로 가리키면 error, 가리키지 않으면 warning. |
| core | `root_missing_composition_id` | error | `rootTag`가 없거나 루트에 `data-composition-id`가 없다. 서브 컴포지션 파일에도 적용된다. |
| core | `root_missing_dimensions` | error | `isSubComposition`이 아니고 루트에 `data-width` 또는 `data-height`가 없다(값이 비어도 해당). |
| core | `root_dimensions_mismatch` | warning | 서브 컴포지션이 아니고 루트의 `data-width`·`data-height`가 있을 때, `html, body` CSS의 width·height 또는 `<meta viewport>` 크기 문자열이 둘 중 하나라도 다르다. body CSS가 어긋나면 "clips" 문구, viewport meta만 어긋나면 "stale metadata, not a clipping risk" 문구다. severity는 같다. |
| core | `unbalanced_style_tags` | error | `<style>` 여는 태그 수와 `</style>` 닫는 태그 수가 다르다(여는 쪽이 많으면 미닫힘, 닫는 쪽이 많으면 조기 종료 문구). |
| core | `visible_markup_comment` | error | HTML 본문(style·script 등 보호 구간과 태그 안쪽 제외)에 `/* ... */` 블록 주석이 있다. |
| core | `missing_timeline_registry` | error | `window.__timelines` 등록 패턴(초기화, 대입, 객체 리터럴 세 가지)이 소스와 외부 스크립트 어디에도 없다. 건너뛰는 조건: `isSubComposition`, 원본이 `<template`으로 시작, 루트에 `data-no-timeline`, `scriptsOutsideProjectUnread`가 비어 있지 않음. |
| core | `timeline_id_mismatch` | error | `window.__timelines["<key>"]`의 key가 이 HTML의 어떤 `data-composition-id`와도 다르다(key마다 하나). |
| core | `css_transition_used` | warning | `<style>`이나 인라인 `style=""`에 transition 계열 선언이 있다. `transition: none`·`transition-property: none`이고, duration·delay·`transition` 단축형에서 시간이 전부 0이면 제외하며, 값에 `var(`가 있으면 0이어도 발동한다. |
| core | `css_parse_error` | error | `<style>` 블록을 postcss가 파싱하지 못한다. 가능하면 오류 offset으로 위치를 준다. |
| core | `repeated_id_descendant_selector` | error | 선택자가 `#a #a`처럼 같은 id를 자기 후손으로 요구한다(id마다 한 번). |
| core | `inline_style_attribute_selector` | error | CSS 선택자가 inline `style` 속성(`[style...]`)을 읽는다(선택자마다 한 번). |
| core | `runtime_hidden_style_opacity` | error | 규칙이 `opacity: 0`을 강제하면서 선택자가 런타임이 쓰는 숨김 스타일(`visibility`·`opacity` 속성 선택자 꼴)을 가리킨다(선택자마다 한 번). |
| core | `id_override_reduced_specificity` | warning | `!important`가 아닌 위치 속성(`POSITION_PROPERTIES`)을 선언하는 규칙의 선택자가 `[id=...]` 또는 `:where(#id)`라서 id 우선순위보다 낮다(선택자마다 한 번). |
| core | `unclosed_tag_swallowed_element` | error | 태그 속성 문자열 안에 따옴표 밖 `<`가 있다(앞 태그의 `>` 누락). |
| core | `invalid_inline_script_syntax` | error | ① 잘못된 `</script>` 닫힘 문법이 있다(위치 없음). ② `src`가 없고 `type`이 면제 목록(`SCRIPT_SYNTAX_EXEMPT_TYPES`)에 없는 인라인 스크립트가 JS 구문 오류를 낸다(오류 offset으로 위치를 준다). |
| core | `host_missing_composition_id` | error | `data-composition-src` 호스트 태그에 `data-composition-id`가 없다. |
| core | `scoped_css_missing_wrapper` | warning | CSS가 `[data-composition-id="X"]` 범위를 쓰는데 이 HTML에 그 id의 컴포지션이 없다(id마다 하나). |
| core | `studio_missing_editable_id` | warning | 루트가 아닌 Studio 타임라인 요소(`isStudioTimelineElement`)에 `id`가 없다. |
| core | `non_deterministic_code` | error | 스크립트(주석, 문자열 리터럴, 내장 GSAP 라이브러리 제외)에 `Math.random(`, `Date.now(`, 인자 없는 `new Date()`, `performance.now(`, `crypto.getRandomValues(`, `crypto.randomUUID(`, `gsap.utils.random(` 중 하나가 있다. GSAP 문자열 값 `"random(숫자` 꼴은 문자열 안에서도 잡는다. 패턴마다 스크립트당 한 번. |
| gsap | `gsap_undefined_css_variable` | warning | GSAP 색 속성(from·to 값)이 폴백 없는 `var(--x)`를 쓰는데 정적 CSS 선언이나 `data-composition-variables`에 `--x` 정의가 없다(selector·property·변수 조합마다 한 번). |
| gsap | `overlapping_gsap_tweens` | warning | 같은 대상(identity가 같고 식별 가능)의 두 GSAP 창이 시간상 겹치고 공유 속성이 있다. 둘 중 하나가 `overwrite: "auto"`이면 제외. 실행 중인 tween 도중에 `set`이 발동하는 경우는 메시지가 다르다. |
| gsap | `gsap_repeated_fromto_without_baseline` | warning | 같은 selector에 `fromTo`(`immediateRender: false` 아님)가 2개 이상이고 from 속성을 공유하며, 첫 fromTo 위치 이하의 전역 아닌 `set` 기준선이 앞에 없다. |
| gsap | `gsap_fullscreen_overlay_starts_visible` | error | 전체 프레임을 덮는 스타일(`styleLooksFullFrameOverlay`)의 태그가 CSS로는 숨지 않았고, 0.05초(`SCENE_BOUNDARY_EPSILON_SECONDS`) 이내에 숨기는 GSAP·standalone 숨김도 없으며, 첫 가시화 tween 뒤에 다른 tween(`from` 제외)이 다시 숨긴다. |
| gsap | `gsap_animates_clip_element` | error | GSAP 창의 대상 selector가 클립(`class="clip"`) 요소의 `#id`나 클래스이고, 속성에 `visibility`, `display`, `autoAlpha`가 있다. |
| gsap | `gsap_css_transform_conflict` | error | CSS(`<style>` 또는 인라인)가 `transform`에 `translate`나 `scale`을 선언한 selector를, `gsap.timeline`이 있는 스크립트의 `to`·`set` 계열 호출이 충돌 속성(`x`·`y`·`xPercent` 등 translate 계열 또는 `scale` 계열)으로 건드린다. `from`·`fromTo`는 제외. selector마다 한 번. |
| gsap | `gsap_loaded_after_use` | error | 인라인 스크립트가 `gsap.(to\|from\|fromTo\|timeline\|set\|registerPlugin)`를 실행 시점에 쓰는데, GSAP core `<script src>`가 그보다 뒤에 있거나 defer·async·module이다. 인라인 GSAP이 있거나 서브 컴포지션·`<template>` 시작이면 제외. |
| gsap | `missing_gsap_script` | error | 인라인 스크립트가 `gsap.(to\|from\|fromTo\|timeline\|set\|registerPlugin)`를 쓰는데 GSAP core `<script src>`도 인라인 GSAP 본문도 없다. 서브 컴포지션·`<template>` 시작 파일은 호스트에서 상속한다고 보고 제외. |
| gsap | `missing_gsap_plugin` | error | 스크립트가 `motionPath`를 쓰는데 첫 사용 전에 실행되는 스크립트 중 MotionPathPlugin을 로드·import·정의한 것이 없다(blocking·defer·module·async 실행 순서를 따진다). 서브 컴포지션·`<template>` 시작이면 제외. |
| gsap | `audio_reactive_single_tween_per_group` | warning | 캡션 스타일이 있고, 스크립트가 오디오 데이터(`AUDIO`, `bands[` 등)와 캡션 그룹 `forEach` 루프를 쓰며 안쪽 샘플링 루프(`group.start`부터 도는 `for`, `while < group.end`)는 없고 `peakBass`·`peakTreble`·`peakEnergy`와 `group.start`가 있다. |
| gsap | `gsap_infinite_repeat` | error 또는 warning | 스크립트(주석 제외)에 정규식 `repeat\s*:\s*-1`이 있다. 루트 `data-duration`이 0보다 큰 유한 숫자이면 warning, 아니면 error. |
| gsap | `gsap_repeat_ceil_overshoot` | warning | `repeat: Math.ceil(...) - 1` 꼴이 있다(주석 제거 안 한 원문에서 찾는다). |
| gsap | `gsap_repeat_floor_unclamped` | warning | `repeat: Math.floor(...) - 1` 꼴이 있다. `Math.max(0, ...)`로 감싼 형태는 매치하지 않는다. |
| gsap | `gsap_timeline_not_registered` | error | `gsap.timeline`을 쓰는 인라인 스크립트(`index !== -1`)에 `window.__timelines` 대입이나 객체 리터럴 등록이 없다. 서브 컴포지션·`<template>` 시작이면 제외. |
| gsap | `gsap_timeline_registered_before_async_build` | error | 한 스크립트에서 `window.__timelines[...] =` 대입이 `document.fonts.ready` 또는 `document.fonts.load(`보다 앞에 있고, 그 뒤에 `.to\|from\|fromTo(` 또는 `buildEffect(` 호출이 있다. |
| gsap | `gsap_cold_seek_hidden_fromto_missing_reveal` | error | CSS `opacity: 0`이나 standalone 숨김으로 시작하는 selector에 `fromTo`가 있고, from 값은 보이는 상태인데 도착 속성에 `opacity`·`autoAlpha`가 없다. |
| gsap | `gsap_from_opacity_noop` | error | CSS `opacity: 0`인 selector에 `gsap.from`의 `opacity` 값이 0이다(0에서 0으로 움직여 안 보임). |
| gsap | `gsap_non_transform_motion` | error | `gsap.timeline`이 있는 스크립트의 tween(`set` 제외, `fromTo`의 from 속성 포함)이 위치 속성(`left`, `right`, `top`, `bottom`, `margin*`), 텍스트 리플로우 속성(`letterSpacing`, `wordSpacing`, `fontSize`) 또는 `roundProps`를 쓴다. 위치 속성은 대상이 전부 `<canvas layoutsubtree>` 안 요소일 때만 면제, 나머지는 면제 없음. `width`·`height`는 일부러 제외했다. |
| gsap | `gsap_relative_value_second_writer` | error | `to`·`set` 계열 tween의 값이 상대값(`+=`·`-=`)이고, 시작 시점에 같은 속성·같은 요소를 쓰는 다른 tween이 아직 활동 중이다(`other.position <= 시작 < other.end`). `from`·`fromTo`, `overwrite: "auto"`, 식별 불가 대상은 제외. |
| gsap | `gsap_repeat_refresh_relative_value` | error | `repeatRefresh: true`가 든 객체 리터럴의 최상위에 상대값(`+=`·`-=`)이 있다. |
| gsap | `gsap_function_value_hazard` | error 또는 warning | 타임라인 tween 변수 중 함수 값이 있다. 본문이 `getBoundingClientRect(`, `getComputedStyle(`, `gsap.getProperty(`를 읽거나 첫 번째 인자(숫자 index)에 멤버 접근을 하면 error. `getTotalLength`, `getBBox`, `offsetWidth` 같은 레이아웃 읽기만 있으면 warning. |
| gsap | `gsap_callback_dom_measurement` | warning | `tl.add`·`tl.call`·`tl.eventCallback("on...")`·tween vars의 `onStart` 등 콜백이 인라인 함수이거나 측정 함수 이름인데, 그 본문이 DOM 측정(`gsap.getProperty` 제외)에 닿는다. 콜백 위치(site)마다 한 번. |
| gsap | `gsap_timeline_return_used_as_tween` | error | 타임라인 변수의 `.to\|from\|fromTo\|set\|call\|add(...)` 반환값을 `.push(`로 배열에 모으거나, 변수에 담은 뒤 그 변수에 `kill`·`revert`·`pause`·`seek`·`progress` 등 tween용 호출을 한다. |
| gsap | `gsap_group_selector_keyframes` | warning | `.to\|from\|fromTo("a, b", {... keyframes` 꼴로 쉼표가 든 selector 하나에 keyframes를 준다(대상 수는 메시지에만 쓴다). |
| gsap | `svg_drawon_css_dasharray_conflict` | error | CSS(규칙 또는 인라인)가 요소에 두 성분 이상의 `stroke-dasharray`(예: `10 10`)를 선언했고, 스크립트의 `set`·`to`·`fromTo`가 그 요소에 `strokeDasharray`를 쓰는데 GSAP 값이 두 성분이 아니다. 결합자가 든 selector 그룹은 상관시키지 않는다. |
| gsap | `gsap_timeline_set_initial_hide` | warning | 타임라인의 첫 tween보다 앞에 있는 즉시 구간(`set`이거나 길이 0인 `to`·`fromTo`)이 위치 0이고 숨김 상태(opacity·visibility·display 숨김, `scale: 0`, 0이 아닌 `strokeDashoffset`)를 만든다. 전역·`immediateRender: true`·이미 CSS나 standalone `gsap.set`으로 숨겨진 대상은 제외. |
| gsap | `svg_round_cap_hidden_dash` | warning | 태그의 `stroke-linecap`이 `round` 또는 `square`이고, `pathLength`, `stroke-dashoffset`, `stroke-dasharray`가 모두 유한 수이며 다음 dash 시작점이 `pathLength`와 오차 1e-6 비율 안에서 같다(숨긴 줄 알았는데 점이 찍히는 경우). |
| gsap | `svg_measure_before_path_d` | error 또는 warning | `<path>`(정적 `d` 없음, CSS `d: path(` 없음)에 `getTotalLength()`를 부르는데, 측정 앞에서 같은 변수의 `d` 대입이 같은 범위에 없다. 그 변수의 `d` 대입이 함수 본문 안에만 있으면 warning, 어디에도 없으면 error. `createElementNS`로 만든 경로는 제외. |
| media | `nested_media_start_basis_ambiguous` | warning | `isSubComposition`이고 `video`·`audio`의 `data-start`가 0보다 큰 유한 숫자인데 `data-hf-media-start-basis`가 `local`·`global`이 아니다. 참조식 start는 `Number()`가 NaN이라 건너뛴다. |
| media | `duplicate_media_id` | error | 같은 `id`를 가진 `video`·`audio`(media 태그)가 2개 이상이다. |
| media | `duplicate_media_discovery_risk` | warning | `tag이름\|src\|data-start\|data-duration`이 모두 같은 media 태그가 2개 이상이다. |
| media | `color_grading_non_media` | error | `data-color-grading`이 있는 태그가 media 그룹 태그나 허용 원본 태그(`video`, `img`, `canvas`)가 아니다. 문서에는 있고 코드에는 `report(code, ...)` 인자로만 있어서 리터럴 grep에는 안 잡힌다(R-11). |
| media | `color_grading_invalid_json` | error | `data-color-grading` 값이 `{` 또는 `[`로 시작하는데 `JSON.parse`가 실패한다. 다른 문자로 시작하는 값(프리셋 이름 등)은 검사하지 않는다. |
| media | `color_grading_invalid_structure` | error | JSON이 파싱되지만 `validateColorGradingContract`가 이슈를 낸다(이슈마다 finding 하나). |
| media | `video_missing_muted` | error | `video`에 `data-start`가 있는데 `muted`도 `data-has-audio`도 선언하지 않았다. |
| media | `video_muted_with_declared_audio` | error | `video`에 `muted`와 `data-has-audio="true"`가 함께 있다. |
| media | `video_nested_in_timed_element` | error | `data-start`가 있는 `video`가 `data-start`를 가진 래퍼(컴포지션 루트 제외, `video`·`audio`·void 요소 제외) 안에 중첩돼 있다. |
| media | `self_closing_media_tag` | error | 소스에 `<audio .../>` 또는 `<video .../>` 자기닫힘 꼴이 있다. |
| media | `media_src_kind_mismatch` | error | `<video>`의 `src` 종류(확장자나 data URL MIME으로 판정)가 video가 아니거나, `<img>`의 `src`가 image가 아니다. 종류를 못 정하면 건너뛴다. |
| media | `placeholder_media_url` | error | media 태그 `src`가 `placehold.co`, `placeholder.com`, `placekitten.com`, `picsum.photos`, `example.com`, `via.placeholder.com`, `dummyimage.com` 중 하나를 포함한다. |
| media | `base64_media_prohibited` | error | `src="data:(audio\|video)/...;base64,<20자 이상>"`이 있다. 샘플 200자의 고유 문자가 15 미만이거나 디코딩 크기가 1000B 초과 50000B 미만이면 메시지에 "likely fabricated data"를 붙이고 severity는 같다. |
| media | `media_missing_data_start` | error | `video`·`audio`가 해석 가능한 src(본인 또는 자식 `<source src>`)를 가졌는데 `data-start`가 없다. 시간 있는 래퍼 안의 video는 fixHint가 다르다. |
| media | `media_missing_id` | error | `video`·`audio`에 `data-start`가 있는데 `id`가 없다. |
| media | `media_variable_src_no_fallback` | warning | `data-start`와 `id`가 있고 src가 없는데 `data-var-src`가 있다. |
| media | `media_missing_src` | error | `data-start`와 `id`가 있고 src도 `data-var-src`도 없다. |
| media | `media_preload_none` | warning | `video`·`audio`에 `preload="none"`이 있다. |
| media | `media_crossorigin_breaks_preview` | error | `video`·`audio`에 `crossorigin` 속성이 있다(값 무관). |
| media | `video_audio_double_source` | error | `data-start`가 있는 소리 나는 `video`(`isAudibleVideoTag`)와 `<audio>`(`data-timeline-role="room-tone"` 제외)가 같은 `src`이고 시간 창이 겹친다. |
| media | `imperative_media_control` | error | 인라인 스크립트가 media로 확인되는 대상(`getElementById`·`querySelector` 직접 호출이나 그 결과를 담은 변수)에 `.play(`, `.pause(`, `.currentTime =`, `.muted =`를 쓴다(주석·문자열 안은 제외). |
| media | `media_runtime_src_mutation` | warning | 스크립트가 `.src =` 또는 `setAttribute('src', ...)`로 기존 `video`·`audio`(또는 그 `<source>`)의 src를 바꾼다. |
| media | `speed_ramp_on_non_media` | warning | `video`·`audio`가 아닌 태그의 `data-automation`에 `"target":"rate"` 레인이 있다. |
| media | `audio_volume_double_automation` | warning | media 태그에 `id`와 `data-automation`의 `"target":"volume"` 레인이 있고, 스크립트에 그 id selector의 같은 호출(괄호 깊이를 세어 범위 결정) 안에 `volume` 키 tween이 있다. 레인이 이기고 tween은 무시된다. |
| media | `audio_volume_tween_overrides_gain` | warning | media 태그에 `id`가 있고 `data-volume`이 1이 아닌 유한 숫자(속성이 없으면 1로 본다)이며 `data-automation`이 없는데, 스크립트의 같은 호출 안에 `volume` tween이 있다. 메시지에 dB 환산값(20·log10)을 쓴다. |
| media | `audio_carve_ungrouped_sources` | warning | `data-fx-carve` JSON(`{`로 시작)의 `sources`가 배열이고 `hf-audio-group` id가 아닌 문자열 id를 2개 이상 담는다. |
| media | `audio_group_no_members` | error | `hf-audio-group`(id 있음)에 속한 clip이 없다. 이 파일에서 `data-audio-group`을 선언한 clip(`audio` 또는 소리 나는 `video`)이 하나라도 있어야 판정하고, `data-composition-src` 호스트가 있으면(다른 파일에 멤버가 있을 수 있어서) 건너뛴다. |
| media | `audio_group_timing_attrs` | warning | `hf-audio-group`에 `data-start`, `data-duration`, `data-track-index` 중 하나라도 있다. |
| media | `audio_group_holds_elements` | warning | `hf-audio-group` 안(여는 태그와 닫는 태그 사이)에 다른 태그가 하나라도 있다. 자기닫힘 `/>`는 닫히지 않아 뒤 형제를 삼킨다. |
| media | `audio_group_carve_attr` | warning | `hf-audio-group`에 `data-fx-carve` 속성이 있다. |
| composition | `invalid_composition_variables_declaration` | error | `data-composition-variables`(JSON)가 유효하지 않다. 경우: JSON 파싱 실패, 배열이 아님, 항목이 객체가 아님, 항목에 `id`·`type`(string, number, color, boolean, enum, font, image 중 하나)·`label`·`default`가 없거나 잘못됨, default가 type과 안 맞거나 enum에 `options` 배열이 없음. 문제마다 finding 하나. |
| composition | `unloadable_media_variable_default` | error | `image` 타입이거나 `data-var-src`로 바인딩된 변수의 default URL이 런타임 `isSafeMediaUrl`을 통과하지 못한다(허용: 상대 경로, http(s), `blob:`, `data:image/*`). |
| composition | `negative_z_index` | warning | R-13 참조. 음수 `z-index` 선언이 있고, 선택자가 `.class`·`#id` 하나이며 그 요소 부모가 stacking context로 확인되면 제외. |
| composition | `missing_data_no_timeline` | warning | 루트나 `data-composition-id` 호스트에 `window.__timelines` 등록도 `data-no-timeline`도 없다(`data-composition-src`·`data-composition-file`로 소스를 마운트한 호스트, `<template>` 안 호스트, 서브 컴포지션의 루트는 제외). 파일에 `<script src>`가 있거나 계산된 키로 등록하는 코드가 있으면 판정하지 않는다. 렌더러가 등록을 최대 45초 기다리는 문제를 메시지로 알린다. |
| composition | `duplicate_composition_id` | error | 같은 `data-composition-id` 값을 가진 요소가 2개 이상이다(`<template>` 안 요소와 `data-composition-src` 마운트 호스트는 제외, 공백뿐인 id 제외). |
| composition | `invalid_parent_traversal_in_asset_path` | error | `src`, `href`, 인라인 `style`·`<style>`의 CSS `url()`이 `../`로 프로젝트 루트 위로 올라간다(파일 자신의 폴더 깊이 `compSrcPath` 기준으로 계산하며 `../assets/x`가 `compositions/`에서 루트 안에 남으면 통과). 레지스트리 원본·설치 파일은 건너뛴다. 파일당 finding 하나에 개수를 합친다. |
| composition | `composition_file_too_large` | warning | 구조상 줄 수가 300(`MAX_COMPOSITION_LINES`)을 넘는다. 레지스트리 원본·설치 파일은 제외. |
| composition | `timeline_track_too_dense` | warning | `data-start`를 가진 요소(`audio`, `script`, `style`, `video`, 자막 cue, 컴포지션 루트·마운트 제외)가 파일당 3개(`MAX_TIMED_ELEMENTS_PER_FILE`)를 넘는다. |
| composition | `deprecated_data_layer` | error | `readClipTiming` diagnostics에 `deprecated-layer`가 있다(요소에 `data-layer`). 렌더는 두 이름 모두 읽지 않는다. |
| composition | `deprecated_data_end` | error | diagnostics에 `deprecated-end`가 있다. `data-duration` 없이 `data-end`만 있으면 "uses data-end without data-duration", `data-duration`과 `data-end`가 어긋나면(`conflicting-end`) "disagrees" 문구다. 둘이 일치하면 발동하지 않는다. |
| composition | `split_data_attribute_selector` | error | CSS나 스크립트에 `[data-composition-id="x" data-foo="y"]`처럼 속성 두 개를 한 대괄호 안에 쓴 선택자가 있다. |
| composition | `template_literal_selector` | error | 스크립트에 `querySelector`·`querySelectorAll`의 인자가 `${...}`를 포함한 템플릿 리터럴이다. |
| composition | `timed_element_missing_clip_class` | warning | `data-start` 또는 `data-duration`이 있고 `class`에 `clip`이 없는 요소(`audio`, `img`, `video`, `script`, `style`, `template`, 컴포지션 루트·호스트 제외). `data-track-index`만 있으면 제외. error가 아닌 이유는 런타임이 `data-start`로 가시성을 정하기 때문이라고 코드 주석에 있다. |
| composition | `standalone_composition_wrapped_in_template` | error | `isSubComposition`이 아니고 원본이 `<template`으로 시작한다. |
| composition | `root_composition_missing_html_wrapper` | error | `isSubComposition`이 아니고 `<template` 시작이 아니며, 원본에 `data-composition-id`가 있는데 `<!doctype` 또는 `<html`로 시작하지 않는다. |
| composition | `requestanimationframe_in_composition` | error | 스크립트(문자열·주석 제외)에 `requestAnimationFrame(`이 있다. 레지스트리 원본·설치 파일은 제외. |
| composition | `invalid_variable_values_json` | error | `data-variable-values`가 JSON 파싱에 실패하거나 객체가 아니다(배열, null 포함). |
| composition | `unknown_variable_binding` | warning | `data-var-src`·`data-var-text`가 가리키는 id가 `data-composition-variables`에 선언되지 않았다. `<html>`이 없고 자체 선언도 없는 조각 파일, 선언 JSON이 깨진 파일은 건너뛴다. |
| composition | `subcomposition_blanks_before_host` | warning | 루트의 `data-duration`이 0보다 큰 유한 숫자이고, `data-composition-src` 호스트가 시작 0.5초 이내(`START_TOLERANCE`)에서 유한한 길이로 시작해 루트 끝보다 0.5초(`EPSILON`)를 넘게 일찍 끝나며, 루트 끝 근처까지 덮는 다른 timed 요소가 없다. `data-start`는 `Number() \|\| 0`으로 읽고 길이를 모르는 요소는 끝이 무한대인 것으로 본다. |
| composition | `subcomposition_root_styled_by_class` | error | `isSubComposition`이고 루트에 class가 있으며 CSS 규칙의 가장 왼쪽 복합 선택자가 루트 자신의 class다. 레지스트리 원본 파일은 제외. 코드 주석이 이 규칙은 지금 렌더 버그를 막는 것이 아니라 일관성 제약이라고 적는다. |
| composition | `subcomposition_style_outside_template` | warning | `isSubComposition`이고 `<template>`이 있는데, `<template>` 밖에 `<style>` 또는 `<head>` 밖 `<link rel=stylesheet>`가 있다(태그마다 하나). |
| composition | `root_composition_duration_derived` | warning | 서브 컴포지션이 아닌 루트에 `data-composition-id`가 있고 `data-duration`이 없으며, GSAP 타임라인 등록이 없고, 비GSAP 애니메이션 신호(Lottie, `THREE.`, WAAPI `.animate(`, CSS `animation`)가 없는데 clip들에서 길이를 유도할 수 있다(`deriveDurationFromClips`가 `derived`). |
| composition | `root_composition_missing_duration_source` | error | 위와 같은 전제에서 다음 중 하나다. ① 비GSAP 신호도 clip 유도도 없다. ② `THREE.`를 쓰는데 `data-duration`이 없다. ③ 무한 CSS 애니메이션(`animation... infinite`)이 있고 Lottie·WAAPI는 쓰지 않는데 `data-duration`이 없다. 유한 CSS·WAAPI·Lottie만 있으면 런타임이 길이를 추론하므로 발동하지 않는다. |
| composition | `composition_heavy_overlay_count_high` | warning | "무거운 overlay" CSS(`filter: blur`, 큰 `radial-gradient`, `clip-path`)를 가진 요소가 25개 이상(`HEAVY_OVERLAY_ELEMENT_COUNT_WARN`)이다. 인라인 style, 또는 그 CSS를 가진 class·id 규칙으로 센다. `opacity:0`·`visibility:hidden`도 센다. 인라인 `display:none`, 면제 태그, 컴포지션 루트·마운트, 레지스트리 파일은 센다에서 뺀다. |
| composition | `root_zoom_rescales_a_fixed_canvas` | error | 루트 또는 그 위의 `html`·`body`에 CSS `zoom`이 걸려 있다(인라인 또는 스타일시트, 캔버스를 가리키는 선택자로 판정, 첫 hit만 보고). 후손의 `zoom`은 검사하지 않는다. 확대(1 초과 또는 100% 초과)이면 "content past the frame's edge" 문구, 축소이면 "dead space" 문구이고 severity는 같다. |
| composition | `composition_exceeds_inspection_viewport_cap` | warning | 루트 `data-width` 또는 `data-height`를 `parseInt`한 값이 4096(`INSPECTION_VIEWPORT_CAP`)을 넘는다. 렌더는 영향 없고 check·validate·snapshot 등 검사 명령만 4096으로 자른다는 설명이다. |
| composition | `subcomposition_linked_style_names_root_id` | warning | `isSubComposition`이고 루트에 `id`가 있으며, 링크된 외부 CSS(`style.index === -1`)에 `#<루트 id>` 선택자가 있다(링크 CSS는 컴파일러가 재작성하지 않는다). |
| composition | `multiple_scene_templates` | warning | 문서에 `[data-composition-id]` 요소가 없고(살아 있는 루트 없음), `<template>` 안에 `data-composition-id`를 가진 템플릿이 2개 이상이다. |
| adapters | `missing_lottie_script` | error | `data-lottie-src` 속성이 있거나 스크립트에 `lottie.(loadAnimation\|setSpeed\|play\|stop\|destroy)`가 있는데, `<script src>` 중 `lottie`(대소문자 무시)를 포함한 것이 없다. 서브 컴포지션·`<template>` 시작이면 호스트에서 상속한다고 보고 제외. |
| adapters | `missing_three_script` | error | 스크립트에 `THREE.`가 있는데, `src`에 `three`가 든 스크립트, `"three"`를 가진 importmap, `three`를 포함한 import·from 경로가 모두 없다. 서브 컴포지션·`<template>` 시작이면 제외. |
| captions | `caption_exit_missing_hard_kill` | error | 자막 컴포지션(파일 경로에 `caption`, 루트 id가 `captions`, 또는 `.caption-group`·`.cg-` 계열 CSS가 있음)의 스크립트에 `forEach`와 자막 class 이름이 있고, `.to(..., {opacity: 0})` 퇴장 tween은 있는데 `.set(..., {visibility:"hidden"\|opacity:0})` 같은 hard kill은 없다. |
| captions | `caption_text_overflow_risk` | warning | `.caption-(group\|container\|text\|line\|word)` 또는 `#caption-container` 규칙에 `white-space: nowrap`이 있고 `max-width`가 없다. |
| captions | `caption_transcript_not_inline` | error | 자막 파일(경로에 `caption` 또는 `.caption-group`·`.caption-word` CSS)이고, `const\|let\|var TRANSCRIPT\|script = [` 인라인 배열은 없는데 `fetch("...transcript...")`가 있다. |
| captions | `caption_container_relative_position` | error | `.caption-(group\|container\|text\|line)` 또는 `#caption-container` 규칙에 `position: relative`가 있다. |
| captions | `caption_overflow_clips_scaled_words` | error | 스크립트에 `scale: 1.2`~`1.9`와 `caption\|word\|cg-`가 함께 있고, `.caption-(group\|container)` 또는 `#caption-(layer\|container)` 규칙에 `overflow: hidden`이 있다. |
| captions | `caption_textshadow_on_group_container` | warning | 자막 CSS가 있는 파일에서 스크립트가 그룹 컨테이너(`#cg-N`, `.caption-group`, 또는 `div`·`groupEl` 등 변수)에 `.to(... textShadow ...)`를 건다. |
| captions | `caption_fittext_scale_mismatch` | warning | `fitTextFontSize(... maxWidth: N)`와 `scale: 1.x`가 한 스크립트에 있고 자막 문맥이며, `N × (가장 큰 scale)`이 1760을 넘는다. fixHint는 `floor(1700 / scale)`을 제안한다. |
| slideshow | `slideshow_invalid` | error | 슬라이드쇼 island(`<script type="application/hyperframes-slideshow+json">`)가 있고 `parseSlideshowManifest`가 예외를 던진다(JSON이나 구조 오류). island가 없으면 아무것도 하지 않는다. |
| slideshow | `slideshow_unresolved_ref` | error | manifest가 파싱된 뒤 `resolveSlideshow(manifest, scenes)`가 errors를 반환한다. 장면 목록은 `data-composition-id`가 scene 꼴이고 `data-start`와 길이(`data-duration`, 또는 `data-end`·`data-hf-authored-end`)가 유한한 요소에서 만든다. 오류마다 finding 하나. |
| rootPaths | `root_path_missing_in_preview` | warning | `/x`처럼 서버 루트에서 시작하는 경로가 링크 CSS의 `url()`(링크 파일만, `rootRelativePath`가 있는 스타일)이나 스크립트의 `fetch("/x")`·`new URL("/x")`에 있다(`//`로 시작하거나 템플릿 `${`가 든 경로는 제외). 렌더는 프로젝트를 루트에 서빙하고 Studio 프리뷰는 하위 경로에 서빙해서 찾지 못한다는 설명이다. |
| rootPaths | `import_map_invalid` | warning | `type="importmap"` 스크립트의 내용이 `JSON.parse`에 실패한다. |
| shaders | `shader_unbounded_cosine_pow` | warning | 스크립트(`src` 없음, JS·module 또는 GLSL 타입)에서 `shaderDomainOffsets`가 `pow(1 - dot(...), ...)` 꼴로 코사인 위쪽이 제한되지 않은 위치를 찾는다. offset마다 finding 하나이고 dedupe 키에 line·column이 들어간다(R-02). 패턴 세부는 `shaderDomains.ts`라서 이 부록에서 열지 않았다. |
| structure | `nested_structure_needs_subcomposition` | error 또는 warning | `isSubComposition`이 아닌 파일에서, 루트 직속 timeline 행(서브 컴포지션 호스트 제외)이 인라인 텍스트 태그(`span`, `b`, `a` 등)가 아닌 레이아웃 자식을 가진다. `svg`, `canvas`, `video` 등 불투명 태그와 `style`·`script`·`template`은 자식으로 세지 않는다. `host === "studio"`이면 error, 아니면 warning. |
| structure | `timeline_element_missing_timing` | error 또는 warning | 같은 행 중 `video`·`audio`·`img`가 아니고 `data-duration`도 `data-end`도 없으며 서브 컴포지션 호스트가 아니다. host 분기는 위와 같다. |
| structure | `caption_track_kind_missing` | error 또는 warning | 행이 자막처럼 보이는데(`trackKindOf`의 source가 `legacy-captions`) `data-track-kind="captions"`가 없다. host 분기는 위와 같다. |
| structure | `multiple_caption_tracks` | error 또는 warning | 자막 행의 `data-track-index`(없으면 `data-track`) 값이 2종류 이상이다. host 분기는 위와 같다. |
| structure | `clip_ends_past_root_duration` | warning | 루트에 `data-composition-id`와 `data-duration`이 있고, 행의 `readClipTiming` 끝이 루트 길이 + `TIMING_TOLERANCE_SECONDS`를 넘는다. host와 무관하게 항상 warning이다(R-11의 "그룹 severity는 host 분기" 서술의 예외). 서브 컴포지션 파일에서는 이 규칙 함수 자체를 건너뛴다. |
| structure | `nested_clip_never_visible` | error 또는 warning | 행 안에 중첩된 clip(`audio`와 `data-hf-media-start-basis="global"`은 제외)의 시간 창이 부모 행의 창과 겹치지 않는다. 부모는 서브 컴포지션 호스트가 아닌 행이고, 부모·자식 모두 `readClipTiming`의 start·end가 정해져 있어야 한다. 이 규칙은 `isSubComposition`이어도 돈다(두 번째 규칙 함수). host 분기는 위와 같다. |
| linkedClips(media 호출) | `linked_clip_orphan` | warning | 같은 컴포지션 범위 안에서 `data-link` 값이 같은 태그가 하나뿐이다. |
| linkedClips(media 호출) | `linked_clips_out_of_sync` | warning | `data-link`가 같은 태그가 2개 이상이고, `data-start`·`data-duration`·`data-playback-start`(또는 `data-media-start`)·`data-playback-rate` 중 하나가 멤버 사이에서 0.001초(`SYNC_TOLERANCE_S`) 넘게 다르다(없으면 start·duration·media-start는 0, rate는 1). |
| audioAttributes(media 호출) | `audio_attribute_unreadable` | error | `data-automation` 또는 `data-fx-chain` 값이 비어 있지 않은데 JSON 객체가 아니거나, `version`이 1이 아니거나, `lanes`(automation) / `nodes`(chain) 배열이 없거나, 항목이 객체가 아니거나, automation 항목에 `target`(문자열)·`points`(배열)가 없거나, chain 항목에 문자열 `type`이 없다. 레인 target·효과 type의 유효성은 렌더가 판정하므로 여기서는 보지 않는다. |
| fonts | `system_font_will_alias` | warning | `options.distributed`가 true일 때만 돈다(false이면 finding 자체가 없다). 사용한 font family 중 `@font-face`·프로젝트 폰트로 선언되지 않았고 별칭 표(`resolveAliasDisplayName`)가 다른 표시 이름으로 바꾸는 것이 있다. 한 파일에 finding 하나로 합친다. |
| fonts | `font_family_without_font_face` | error | 사용한 font family(CSS `font-family`·`font` 단축형, `var()` 최대 8단계 해석, generic family 제외)가 `@font-face`, 프로젝트 폰트, Google Fonts 링크·`@import`, 자동 해석 별칭 목록(`FONT_ALIAS_KEYS`) 어디에도 없다. 레지스트리 파일은 제외. 한 파일에 finding 하나로 합치고, 근거 선언이 정확히 하나일 때만 위치를 준다. |
| fonts | `font_face_local_only` | warning | `@font-face`의 `src`가 `local()`만 있고 `url()`이 없다. 레지스트리 파일은 제외. |
| textures | `texture_drop_shadow_on_text` | warning | `hf-texture-text` 요소에 `filter: drop-shadow(...)`가 직접 걸려 있다(규칙 선택자가 질감 class를 직접 가리키거나, 단순 선택자가 그 태그와 맞거나, 인라인 style에 있음). |
| textures | `texture_class_missing_base` | warning | `hf-texture-*` 재질 class(`hf-texture-text` 제외)가 있는데 `hf-texture-text`가 없다. |
| textures | `texture_text_missing_mask` | warning | `hf-texture-text`가 있는데 재질 class도 인라인 `mask-image`도 없다. |
| textures | `texture_class_unknown` | error | 태그의 `hf-texture-*` 재질 class가 로컬 CSS에 정의돼 있지 않다. |
