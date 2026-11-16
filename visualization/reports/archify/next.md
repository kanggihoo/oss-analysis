---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-01
updated: 2026-11-16
---

# Next Session Plan: archify

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션 결과 (2026-11-02, 작업을 여기서 중단)

- feature map 12행 전체를 스펙으로 썼다: [capabilities/](./capabilities/) 16개 파일(12행 + `rendering` 하위 4개). **ready 13 / draft 3**. 상태는 [overview.md](./overview.md) 2절 "스펙·상태" 칸이 기준이다.
- ready(13): artifact-choice, type-routing, input-validation, rendering, rendering-architecture-routing, rendering-workflow, rendering-contracts, delivery, verification-gates, finalize-orchestration, repair-loop, explainer, viewer.
- 실행 확인은 설치본 CLI(레포 `archify/`와 `diff -rq` 차이 없음)로 했고 입력·출력은 `../../artifacts/archify/spec-demos/`에 있다. 레포 clone의 코드는 직접 실행하지 않았다.

## 2. 미정이거나 다시 해야 하는 것

**draft 스펙 3개**

| 스펙 | 남은 일 |
|---|---|
| [rendering-other-types](./capabilities/rendering-other-types.md) | U-01~U-06 해소 문구를 썼지만 편집이 도중에 끊겨 정합을 검증하지 못했다. 1.5 C-ID(C-36~C-43), 1.6 T-ID(T-22~T-32), 2.1 행이 본문 R-41~R-47과 맞는지 확인하고 ready로 올린다. |
| [authoring-contract](./capabilities/authoring-contract.md) | R-18(치수 예산 `32+14(k−1)`, `6.5×단위+21`, 1240px 중 진단으로 강제되는 것)이 미결정. 부분 실행 기록만 `spec-demos/authoring-budget/`(`run.py`, `run.out.txt`)에 있고 스펙에는 반영하지 못했다. 단서: 코드에서 찾은 건 `desktop-readability.mjs:7`의 1.55 비율뿐. input-validation이 ready라 depends 승격도 판단한다. |
| [auxiliary-commands](./capabilities/auxiliary-commands.md) | `brands capture`(R-17), update 확인(R-21), recover(R-22), `examples`(R-20)는 인터페이스 수준만 확인했다. compare·migrate·preview는 조사 끝, preview는 서버를 띄우지 않았다. |

**아직 하지 않은 것**

- 통합 검토(워크플로 4장 5번) 4항목 중 4번: 기능을 가로지르는 대표 흐름 하나를 입력부터 결과까지 글로 잇기. 스펙 간 교차 정합도 q1~q3·overview 반영 수준에서 끝났고 12개 문서 전체를 서로 대조하지는 않았다.

**feature map 보정 제안 (판단 대기, 미반영)**

- 행 6 아래 하위 스펙 4개를 표 행으로 둘지(지금은 행 6 칸의 링크만).
- 출력 쓰기 기본 연산(`atomic-output.mjs`의 하드링크 백업→격리 제거→link)은 render·finalize·preview·explainer·deliver가 공유한다. 소유 행을 정하거나 `rendering-contracts`의 비교표를 공유 계약으로 지정.
- 출력 경로·사이드 파일 규칙(`output-path`, `portable-path`)을 별도 공유 계약 행으로 분리할지.
- 행 5 → 행 6: 타입별 구조·참조·레이아웃 검증은 `loadDiagram`이 아니라 각 렌더러 소관. `path-semantics.mjs`는 SVG가 아니라 OS 경로 비교라 행 6 진입점에서 행 7로 이동.
- 행 10 선행에 5·6 추가, 행 12는 행 7에 설명용 의존, 행 11의 가이드 뷰 제거(템플릿에 없음), 브랜드 마크(`brand-marks.mjs`, `archify brands`)를 새 행 후보로.
- `routeMeetsCompositionFloors`(구간 하한 micro 8·interior 16)가 렌더러와 검증 게이트에서 같은 predicate를 쓰는지 연결.

**원본 문서와 구현의 차이 (구현이 사실, 스펙에 기록됨)**

- `schemas/README.md:27`의 `meta.animation: trace` opt-in은 틀림: 렌더러가 읽지 않고 `data-animation="trace"`가 항상 붙는다.
- `authoring-defaults.md:39`의 "`meta.output` 필수"는 5개 타입에만 맞다. `schemas/README.md`도 동일.
- `explainer-authoring.md`의 본문 다이어그램 4개 상한과 `@metric` 필수 필드는 코드에 없거나 다르다.
- `delivery-contract.md`의 stdout "compact JSON 한 개"는 `--json`일 때만.
- 지시문끼리 충돌: `delivery-contract.md:11`(`--quality showcase` 재실행) vs `SKILL.md:44`(`meta.quality_profile`과 같은 값), `SKILL.md:93`(위치 수리 2회차 금지) vs `architecture-layout-repair.md:18`(bounded second repair 허용).

**확인하지 못한 환경·동작**

- `--quality`만 줬을 때 architecture·sequence 본문은 `meta.quality_profile`만 봐서 정적 검사와 어긋난다(코드·일부 실행 확인). 영향 범위의 전수 실행은 안 했다.
- 사람 눈 시각 검토 없음. `inspect-sequence-width` 권고는 fixed 5명 입력 1건만 실행했다.
- 브라우저: viewer의 호버·패닝·실제 클립보드·Safari/Firefox, explainer Ask의 `navigator.clipboard` 없음 경로(추론: 복사가 안 됐는데 "복사됨" 토스트가 뜰 수 있음).
- 네트워크 update 경로, Windows 분기, 프로세스 kill·잠금 경쟁은 실행하지 않았다(코드 확인만, 잠금 파일을 미리 만든 12건은 실행).
- 레포 clone의 `bin/archify.mjs` 직접 실행은 자동 승인에서 거부됐고 설치본으로 대체했다.

## 3. 다음 세션 시작 순서

1. 이 문서와 overview 2절 상태 칸을 읽는다.
2. `rendering-other-types` 정합 확인 → `authoring-contract` R-18 → `auxiliary-commands` 내부 순서로 draft를 닫는다.
3. 통합 검토 4번(대표 흐름)을 쓰고 feature map 보정 제안의 판단을 받는다.
4. 커스텀(링크 확장)이 목적이면 위 순서 대신 [5절](#5-커스텀을-위해-앞으로-볼-코드-2026-11-16-추가)의 읽기 순서를 따른다.

## 4. 참고

- `../../artifacts/archify/spec-demos/input-validation/`의 임시 git 저장소는 `setup-repo.sh`로 재생성된다(`.gitignore`에서 제외).
- 로컬 설치본: `node ~/.claude/skills/archify/bin/archify.mjs ... --repo-root visualization/repos/archify`.

## 기준 SHA 갱신 (2026-11-16)

- `repos/archify`를 `a7ed6fd`로 올렸다. 스킬 본체 변경은 `check-render-output.mjs` 1개이고 규칙은 바뀌지 않았다([overview 1절 변경 표](./overview.md)).
- `repos/archify`는 최신 HEAD 상태다. 기준 SHA 원본을 다시 읽으려면 `a406594`(대부분의 스펙 `sha`)를 checkout한다.

## 5. 커스텀을 위해 앞으로 볼 코드 (2026-11-16 추가)

목적이 하나 더 생겼다. archify를 vendoring하거나 fork해서 (a) 다이어그램 노드를 누르면 상세 페이지로 이동하게 하고(drill-down), (b) explainer 페이지끼리 링크로 잇고, (c) AI에게 주는 지침(`SKILL.md`)을 우리 규칙으로 다시 쓰는 것이다. 1~4절의 스펙 마무리와는 별개의 작업이고, 어느 쪽을 먼저 할지는 `handoff.md`의 결정에 달려 있다. 아래는 모두 `a7ed6fd` 기준이다(`archify/` 본체는 `a406594`와 `check-render-output.mjs` 1개만 다르다).

### 5.1 읽는 순서

입력에서 출력 쪽으로 따라간다. 이미 쓴 분석 문서가 있는 단계는 그것을 먼저 읽고 코드는 필요한 곳만 연다. `SKILL.md`는 [번역본](./translations/SKILL.ko.md)으로 먼저 읽을 수 있다.

| 순서 | 열 파일 | 확인할 것 | 먼저 읽을 분석 |
|---|---|---|---|
| 1 | `archify/SKILL.md` | AI가 JSON을 쓰기까지 따르는 규칙, Type router | [authoring-contract](./capabilities/authoring-contract.md), [type-routing](./capabilities/type-routing.md) |
| 2 | `examples/web-app.architecture.json`과 같은 이름의 렌더 HTML | 입력 JSON 한 줄이 출력 HTML의 어디로 가는지 | 없음(직접 비교) |
| 3 | `schemas/common.schema.json`, `schemas/architecture.schema.json` | 노드(`components[]`)가 받는 키, 새 필드를 거부하는지(`additionalProperties`), 링크 필드를 넣을 자리 | [q3](./questions/q3-customization-and-output.md) |
| 4 | `renderers/shared/cli.mjs`, `renderers/shared/utils.mjs` | `loadDiagram`, `writeDiagram`, `applyTemplate`(슬롯 8종)의 공통 흐름 | [rendering](./capabilities/rendering.md) 1.1~1.3 |
| 5 | `renderers/architecture/render-architecture.mjs` (`focusNodeAttrs`, `focusNodeTitle` 검색으로 진입) | 노드 하나가 SVG `<g>`로 그려지는 곳. 링크 `<a>`로 감쌀 자리 | rendering 1.3 E·F·G |
| 6 | `assets/template.html`의 5196~5202, 5206, 5528행 근처만 | 슬롯 자리. CSS(약 4900줄)와 뷰어 JS(약 9200줄)는 건너뜀 | rendering 1.3 B |
| 7 | `viewer/focus.js` | 노드 클릭 시 포커스 핸들러가 `<a>` 이동과 충돌하는지 | [viewer](./capabilities/viewer.md) |
| 8 | `explainer/inline.mjs`, `explainer/parse.mjs` | 본문 링크 대상 6종(R-06)과 상대 `.html`을 허용하려면 고칠 곳 | [explainer](./capabilities/explainer.md) R-06, C-07 |
| 9 | `scripts/check-render-output.mjs`, `explainer/check.mjs` | 정적 검사가 `<a href>`를 거부하는지, explainer `explainer_structure`의 `javascript:`·미해결 `#앵커` 검사와의 관계 | [verification-gates](./capabilities/verification-gates.md), explainer R-21 |

### 5.2 풀어야 할 질문 (모두 `미확인`)

- 스키마를 고쳐 노드에 `link` 필드를 넣으면 `schemas/*.schema.json` 외에 `renderers/shared/generated-validators.mjs`를 `generate:validators`로 다시 만들어야 한다(파일 머리말에 "Do not edit by hand"). 스키마가 `additionalProperties:false`를 쓰는 것은 확인했고, `components[]` 노드가 정확히 어떻게 거부하는지는 열지 않았다.
- `<a>`로 감싼 노드가 뷰어의 포커스·키보드 조작(`tabindex`, `role="button"`)과 충돌하는가.
- `check`와 `finalize`가 SVG 안의 `<a href>`를 허용하는가.
- explainer 안의 native 다이어그램은 gzip+base64 자식 문서라서, 노드 링크를 부모 페이지(`#패널id` 등)로 연결할 수 있는가. 안 되면 explainer는 본문 링크만 확장한다.
- 뷰어를 유지할지, 끄고 `template.html`을 직접 고칠지. `viewer/` + `generate-viewer.mjs`를 같이 가져오면 원본 방식을 유지할 수 있다.
- `archify/` 폴더만 복사했을 때 `render`와 `finalize`가 루트 없이 도는가(`archify/package.json`의 `test` 등은 `--prefix ..`로 루트를 가정한다).
- 프로젝트의 `.claude/skills/archify`와 설치본 `~/.agents/skills/archify`가 겹칠 때 어느 쪽이 쓰이는가.
- (q3에서 이어짐) 프리셋 4종의 실제 화면 차이.

### 5.3 결정 대기

[handoff.md](../../../handoff.md)의 archify 행에 올렸다.

- 분석 목적 확정(`visualization/GUIDE.md`는 아직 "미정"): 지금은 "내부 흐름 이해"가 `overview.md`의 목적이고, 커스텀 목적은 이 절에서 추가됐다.
- 방식: vendoring / fork 후 `custom` branch / `sparse-checkout`.
- 링크 범위: native 노드 → 상세 페이지 / explainer 본문 링크 / 둘 다.
- 뷰어 유지 여부.

### 5.4 만들 문서

- `questions/q4-drill-down-links.md`: 5.2의 질문 중 5~9번 읽기로 풀린 것만 `코드 확인`으로 쓴다.
- AI 지침(`SKILL.md`·`AGENTS.md` 수정본)은 `reports/`가 아니라 vendoring한 위치에 둔다. `reports/`는 특정 SHA의 사실을 적는 곳이라 지침과 섞지 않는다.

### 5.5 지금 보지 않아도 되는 것

`archify/` 안: `locales/`, `brand-marks/`, `recipes/`, `delta/`, `migrations/`, `renderers/`의 나머지 9개 타입 폴더, `explainer/`의 `charts.mjs`·`patch.mjs`·`reader.js`, `bin/` 대부분. 루트: `docs/`, `website/`, `experiments/`, `benchmarks/`, `journal/`, `integrations/`, `community/`, `tools/`, `.agents/`, `.github/`, `scripts/`(`generate-viewer.mjs`·`run-tests.mjs` 제외). `package.json`의 `build:*`, `test:webm`, `test:browser`, `*:brand-marks`, `render:examples`, `check:release-identity`.
