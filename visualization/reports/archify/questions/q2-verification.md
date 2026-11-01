---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-01
updated: 2026-11-01
sources:
  - archify/SKILL.md
  - archify/bin/archify.mjs
  - archify/bin/finalize.mjs
  - archify/bin/visual-check.mjs
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/validator.mjs
  - archify/renderers/shared/repository-evidence.mjs
  - archify/renderers/shared/geometry.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/scripts/check-render-output.mjs
  - archify/references/delivery-contract.md
---

# [Q] 만들어진 결과물은 어떻게 검증하나

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 단계 구조·순서·확인 대상은 `코드 확인`. 각 검사의 임계값과 세부 판정은 대부분 `미확인`. 실행은 하지 못했다.

## 1. 질문 및 결론

- **질문**: LLM이 쓴 JSON과 그 결과 HTML이 맞는지 어떻게 확인하나. 그림이 틀린 내용을 담고 있는지도 확인하나.
- **결론**: 검증은 **5겹**이고 모두 "모양·치수·존재"를 본다. ① 입력 JSON의 모양(스키마·ID 관계·근거 파일의 존재), ② 렌더러 안의 배치 규칙(겹침·범위 밖·라벨 간격), ③ 만들어진 SVG의 정적 검사, ④ 산출물이 위 단계에서 나온 그대로인지(provenance 해시), ⑤ 실제 Chrome에서의 크기·넘침 측정. **그림의 내용이 코드와 일치하는지(의미)는 코드가 판단하지 않는다.** 근거는 "그 파일·줄이 그 커밋에 있다"까지만 확인한다. (`코드 확인`)

## 2. 동작 설명

### 2.1 단계 순서와 실패 시 동작

`finalize`는 `deliver → check → browser-check`를 순서대로 실행하고 하나라도 실패하면 멈춘다(`finalize.mjs:835`). 문서가 말하는 `validate`는 `deliver` 안에서 같이 일어난다(영수증에 `execution: 'embedded-in-deliver'`, `finalize.mjs:958`). 실패하면:

- 프로세스는 비정상 종료하고 영수증에 진단(`code`, `message`, `subject`, `evidence`, `supportedFixes`)이 남는다(`finalize.mjs:586` `compactFinalizeReceipt`).
- `deliver`는 staging 폴더에서 렌더하고 통과해야만 최종 경로로 교체하므로 **직전에 성공한 HTML이 남는다**(`archify.mjs:4870` → `:4904` → `:5124`). 실패 시 기존 파일을 지우는지 직접 실험하지는 않았다.
- 기본 품질은 `showcase`다(`archify.mjs:5938` `quality: qualityArgs.quality || 'showcase'`). 이 모드에서는 **경고(warning)가 하나라도 있으면 `deliver` 단계가 실패로 처리**된다(`finalize.mjs:926`).

### 2.2 ① 입력 검증 (`loadDiagram`, `renderers/shared/cli.mjs:48-107`)

한 번의 렌더러 실행 안에서 순서대로 실행된다(`cli.mjs:81-86`).

| 순서 | 무엇을 확인 | 위치 |
|---|---|---|
| 1 | JSON 문법, `meta.output` 경로 형식(상대·`.html`·위험 문자 금지) | `cli.mjs:81`, `output-path.mjs` |
| 2 | **스키마**(생성된 ajv 검증기). 오류 메시지에 `id/label`을 붙여 LLM이 고치기 쉽게 함 | `validator.mjs:38` `validateSchema` |
| 3 | 로케일 번역 적용 | `cli.mjs:83` |
| 4 | **관계 ID 중복 검사** 하나뿐(`cli.mjs:356-358`). 노드 중복·끝점 존재 검사는 이 단계가 아니라 각 렌더러가 한다 | `cli.mjs:356`, [input-validation](../capabilities/input-validation.md) 1.3 |
| 5 | 엔지니어링 프로파일(architecture의 `deployment-ownership`) | `cli.mjs:85` |
| 6 | **저장소 근거**: `sources`가 있으면 `--repo-root`로 대조(아래) | `cli.mjs:86`, `repository-evidence.mjs:155` |

**저장소 근거 확인 방식**(`repository-evidence.mjs:155-350`): 입력 → 대조 → 실패 시 진단.
- 40자리 커밋 SHA, 지원 호스트(GitHub·Gitee·GitLab)의 HTTPS 주소, 로컬 Git 최상위 디렉터리, `origin` 주소 일치를 확인한다.
- 그 커밋에 객체가 있는지(`git cat-file -e`), 각 `sources`의 경로가 그 커밋에 파일로 있는지(`file-missing`), 줄 번호가 파일 줄 수 안인지(`git show`, `line-out-of-range`)를 확인한다.
- **작업트리 변경분이 아니라 커밋된 바이트**를 기준으로 한다(문서 `repository-authoring.md` + `git show` 사용으로 확인).
- **확인하지 않는 것**: 그 줄의 내용이 노드 설명과 일치하는지. 이를 위한 의미 비교 코드는 이번에 읽은 범위에서 발견하지 못했다(`추론`: 없다고 보는 쪽이 맞다고 판단했지만 모든 코드를 읽진 않음). 문서도 "각 참조는 그 위치에서 보이는 사실만 증명한다"고 적는다.

### 2.3 ② 렌더러 안의 배치 검증

타입별 렌더러가 자체적으로 던지는 진단이다. architecture에서 확인한 것: 노드 겹침(`layout/component-overlap`), 캔버스 밖 노드·경로(`layout/*-out-of-bounds`), 경계 틀이 비소속 노드를 감쌈(`layout/boundary-encloses-non-member`), 라벨 겹침·화살촉 충돌(`composition/label-gap`, `arrowhead-collision`), 라벨 넘침(`architecture/component-label-overflow`), 알 수 없는 끝점(`architecture/unknown-endpoint`)(`render-architecture.mjs` 등에서 `code:` 문자열 검색, 코드 확인). `--layout-json`은 이 배치 보고서를 HTML 없이 JSON으로 낸다(`archify.mjs:6963` `commandValidate`, architecture·workflow만).

### 2.4 ③ 정적 SVG 검사 (`scripts/check-render-output.mjs`)

HTML 문자열을 읽어 검사한다(브라우저 없음). 확인한 항목 이름: `single_svg`(SVG가 정확히 하나), `finite_svg`(NaN·무한대 좌표 없음), `orthogonal_arrows`(화살표 선분이 직각), `relationship_crossings`, `relationship_corridors`, `label_route_clearance`, `container_border_runs`, `route_rhythm`, `legend_clearance`, `svg_path_data`, 그리고 데스크톱 가독성 계산(`collectDesktopReadability`). 임계값은 읽지 않았다(`미확인`).

### 2.5 ④ provenance

`check --require-provenance`와 `browser-check --require-provenance`는 산출물이 `deliver`가 만든 바로 그 바이트인지 확인한다. 어긋나면 브라우저를 열기 전에 실패한다(`delivery-contract.md`의 "A provenance failure exits before browser inspection", `finalize.mjs:514`). 즉 **수동으로 고친 HTML이나 다른 도구가 만든 HTML은 이 게이트를 통과하지 못한다**(`코드 확인` 중 호출, 판정 로직은 `미확인`). `finalize`는 마지막에도 후보 파일이 도중에 바뀌지 않았는지 해시로 한 번 더 확인한다(`finalize.mjs:1036` `finalize/candidate-changed`).

### 2.6 ⑤ 브라우저 측정 (`browser-check`)

Chrome/Chromium(없으면 Edge)을 DevTools 파이프로 띄워 **1440×900, 1600×1000, 1920×1080, 2048×1320** 뷰포트에서 측정한다(`visual-check.mjs:37-42`). 라이트 테마는 4개 뷰포트 전부, 다크 테마는 양 끝, READ/Still 상태까지 본다. 가로 넘침은 항상 실패이고, 세로 스크롤은 렌더러가 선언한 계약이 있고 글자가 읽을 만할 때만 허용된다. 투영된 글자 크기 6px가 실패 하한이다(`delivery-contract.md:416-490`, 문서 기준. 코드 임계값은 `미확인`). 스크린샷은 만들지 않고 영수증 JSON만 남긴다.

- 브라우저가 없으면 `skipped`(종료 코드 2). 런타임 오류는 `skipped`로 바꾸지 않고 실패로 둔다(문서).
- 이 컴퓨터에서 `browser-check`가 실제로 Chrome을 띄워 통과했다(`실행 확인`, `structure.browser-check.json`).
- explainer는 기본적으로 이 단계를 실행하지 않는다(`finalize.mjs:746` `needsBrowser = type !== 'explainer' || browserCheck`).

### 2.7 시각 검토

기본 `finalize`는 스크린샷도 사람의 눈도 쓰지 않으며 영수증에 `visualReview: "not-requested"`로 남긴다(`finalize.mjs:799`). 시각 검토는 사용자가 요청하거나 구체적 우려가 있을 때 `visual-check`로 캡처를 만들어 에이전트가 직접 보는 선택 절차다(`SKILL.md:97-103`). 응답에서 "검증됨"이라고 말할 때는 자동 검사 통과와 시각 검토를 구분하도록 지시한다(`SKILL.md`의 Output 절).

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 단계 순서 | `archify/bin/finalize.mjs:835` | `runFinalize` | 게이트 반복·첫 실패 중단 |
| showcase 경고 실패 | `archify/bin/finalize.mjs:926` | `runFinalize` | 경고 있으면 실패 |
| 스키마 | `archify/renderers/shared/validator.mjs:38` | `validateSchema` | ajv 생성 검증기 호출 |
| 근거 대조 | `archify/renderers/shared/repository-evidence.mjs:155` | `verifyRepositoryEvidence` | git으로 파일·줄 존재 확인 |
| 정적 검사 | `archify/scripts/check-render-output.mjs:111` | `addCheck` | 항목별 통과/실패 |
| 뷰포트 | `archify/bin/visual-check.mjs:37` | `VISUAL_CHECK_VIEWPORTS` | 4개 해상도 |
| 브라우저 게이트 | `archify/bin/archify.mjs:5663` | `executeBrowserEvidence` | 측정 실행 |

## 4. 검증 과정 및 실행 결과

- 코드는 읽기 위주였다. 설치된 스킬로 `finalize`를 실행했을 때 architecture는 4개 게이트(`browser-check` 포함) 모두 통과, explainer는 `browser-check`를 `not-run`으로 기록했다(`실행 확인`, 영수증 `diagrams/structure.finalize-summary.json`). 실패 사례는 만들어 보지 않았다.

## 5. 남은 질문 및 추가 조사 사항

- [ ] `check-render-output.mjs`·`visual-check.mjs`의 임계값(6px, 데스크톱 가독성 기준, 교차 허용 수).
- [ ] 의미 검증이 정말 없는지: `sources`의 `label`이나 `line`을 이용한 추가 비교가 있는지.
- [ ] 직접 실행해 실패 케이스(경로 오타, 존재하지 않는 줄, 겹치는 노드)가 어떤 진단을 내는지 확인.
- [ ] 임시로 고친 HTML이 provenance 게이트에서 실제로 막히는지(변조 실험).

## 6. 기능 스펙 작성 후 정정 (2026-11-02, `실행 확인`)

본문 2절은 코드를 읽은 시점의 서술이고, 아래는 스펙 조사에서 실행해 바로잡은 내용이다. 원본 근거는 각 스펙이다.

- **의미 검증 없음**: `sources[].label`을 읽는 코드가 없고 무관한 줄을 인용해도 통과한다 ([input-validation](../capabilities/input-validation.md) T-35). 지시문은 모든 요소에 근거를 요구하지만 코드는 근거가 총 1건 이상인지만 본다.
- **`check`는 노드 겹침을 보지 않는다**: 노드를 겹치게 옮긴 HTML도 종료 코드 0이다 ([verification-gates](../capabilities/verification-gates.md) T-12). 겹침은 렌더러 단계 진단이다.
- **글자 하한이 두 번 다르게 계산된다**: 정적 검사는 가용폭 930px을 가정하고 브라우저는 실제 렌더 폭을 쓴다. 글자 7.2는 정적 실패, 브라우저 통과였다(T-09).
- **`check` 통과가 `browser-check` 통과를 뜻하지 않는다**: workflow·dataflow 예제는 `check` 종료 0(경고 `composition/viewport-height`)이고 `browser-check`는 `viewer/viewport-overflow`로 실패했다(T-13).
- **provenance**: 사이드 파일이 있으면 `--require-provenance` 없이도 검증한다. 변조하면 Chrome 실행 전에 `delivery/provenance-mismatch`로 실패한다(T-03). 형식은 [delivery](../capabilities/delivery.md) R-10.
- **실패 후 상태**: `deliver`가 실패하면 HTML 바이트는 유지되지만 provenance가 `failed` 표지로 바뀌어 이후 `check`가 실패한다. 2.1의 "직전에 성공한 HTML이 남는다"는 HTML 바이트에만 맞는다. `showcase` 경고 실패는 교체 뒤에 일어나 새 HTML이 남는다 ([finalize-orchestration](../capabilities/finalize-orchestration.md) R-16, R-22).
- **`browser-check`는 자식 프로세스가 아니다**: `finalize` 안에서 같은 프로세스로 실행된다(`execution: in-process`). 마지막 변조 확인은 초안과 HTML·provenance 둘을 본다.
- **임계값(해소)**: 직각 허용 0.01, 회랑 겹침 8px, 라벨 여유 showcase 4px/standard 2px, 글자 하한 6px. 5절 첫 항목과 3번째 항목(변조 실험)은 스펙에서 해소됐다.
