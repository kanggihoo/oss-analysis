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

### 5.3 결정 (2026-11-17 사용자 답)

- **분석 목적**: "내부 흐름 이해 + fork 후 커스텀"으로 확정.
- **방식**: fork는 `https://github.com/kanggihoo/archify`이고 2026-11-18에 `C:\Users\SSAFY\Desktop\archify`로 clone했다(폴더 이름은 `archify`). 확인 결과: `origin`만 있고 `upstream` remote와 `custom` branch는 아직 없다. HEAD는 `44781293`(2026-11-17)이고 분석 기준 `a7ed6fd`의 후손이며 4 commit 앞서 있다. 그 4개는 `docs/`, `journal/`, `website/`, `llms.txt`만 바꿔서 `archify/`(스킬 본체), `explainer/`, `viewer/`, `schemas/`는 `a7ed6fd`와 같다. 그래서 지금까지의 스펙·Q 문서는 이 clone에도 그대로 맞는다. `node_modules`는 아직 설치하지 않았다.
  커스텀 작업은 이 clone의 `custom` branch에서 한다. 커스텀 작업은 fork clone의 `custom` branch에서 한다(`repos/archify`는 upstream 분석용으로 둔다). fork URL은 사용자에게서 받아 `repos.lock.tsv`에 적는다.
- **링크 범위**: explainer만. native 노드 링크(5.6 앞 3행)는 하지 않는다.
- **뷰어 유지 여부**: 사용자가 뷰어의 의미를 몰라 미정. 아래 "뷰어가 무엇인가"를 읽고 정한다.

**뷰어가 무엇인가** (`코드 확인`, `a7ed6fd`, 상세는 [viewer](./capabilities/viewer.md))

뷰어는 별도 앱이 아니라 렌더된 다이어그램 HTML 안에 인라인으로 들어 있는 JS·CSS 런타임이다. 원본은 `viewer/*.js` 14개와 `viewer.css`, 셸 `template.source.html`이고, `scripts/generate-viewer.mjs`가 이를 `archify/assets/template.html` 한 파일로 합친다. 렌더러는 이 template의 슬롯에 SVG만 채운다. 그래서 `archify render`로 만든 모든 HTML을 브라우저에서 열면 노드 클릭 Passport, Route·Reach, 검색(`/`), 테마, 내보내기(PNG·SVG·WebM)가 이미 동작한다.

explainer와의 관계: explainer 페이지 자체는 뷰어가 아니라 `explainer/reader.js`와 `reader.css`로 돈다. 하지만 `@architecture` 같은 native 다이어그램은 페이지 안에서 `viewer-dialog`로 열리고, 그 안에서는 이 뷰어가 돈다. 본문 링크 `[x](node:…)`, `[x](route:…)`는 뷰어를 `#focus=`, `#route=` 해시로 여는 딥 링크다. 따라서 explainer 본문 링크만 확장하면 `explainer/inline.mjs`, `render.mjs`, `check.mjs`만 고치면 되고 뷰어는 건드리지 않아도 된다(추론, 실행 전). 뷰어를 고칠 때만 `npm run generate:viewer`가 필요하다.

### 5.4 만들 문서

- `questions/q8-explainer-link-extension.md`: 5.2의 질문 중 5~9번 읽기로 풀린 것만 `코드 확인`으로 쓴다.
- AI 지침(`SKILL.md`·`AGENTS.md` 수정본)은 `reports/`가 아니라 vendoring한 위치에 둔다. `reports/`는 특정 SHA의 사실을 적는 곳이라 지침과 섞지 않는다.

### 5.5 지금 보지 않아도 되는 것

`archify/` 안: `locales/`, `brand-marks/`, `recipes/`, `delta/`, `migrations/`, `renderers/`의 나머지 9개 타입 폴더, `explainer/`의 `charts.mjs`·`patch.mjs`·`reader.js`, `bin/` 대부분. 루트: `docs/`, `website/`, `experiments/`, `benchmarks/`, `journal/`, `integrations/`, `community/`, `tools/`, `.agents/`, `.github/`, `scripts/`(`generate-viewer.mjs`·`run-tests.mjs` 제외). `package.json`의 `build:*`, `test:webm`, `test:browser`, `*:brand-marks`, `render:examples`, `check:release-identity`.

### 5.6 수정 지점 탐색 결과 (2026-11-17, `a7ed6fd`, 읽기만 함)

| 하고 싶은 것 | 손볼 곳 | 확인한 사실 |
|---|---|---|
| 노드에 필드 추가(예: `link`) | `schemas/<type>.schema.json` → `generate:validators`로 `renderers/shared/generated-validators.mjs` 재생성 | architecture `components[]` 노드는 `additionalProperties:false`이고 키는 `id,type,label,sublabel,tag,icon,brand,sources,row,col,pos,size`뿐이라 새 키는 스키마를 고치지 않으면 거부된다(코드 확인). 타입마다 노드 스키마가 따로라 타입 수만큼 고쳐야 한다(추론) |
| 그 값을 SVG 노드에 싣기 | `renderers/shared/cli.mjs:393` `focusNodeAttrs`(공유)와 각 `render-<type>.mjs`의 호출부(architecture는 `render-architecture.mjs:1098`) | 노드 `<g>`는 `tabindex="0" role="button" aria-pressed` 속성과 `data-node-*`로 그려진다(코드 확인). `<a>`로 감싸면 role=button과 겹치므로, `data-node-link` 같은 속성을 추가하고 뷰어가 읽게 하는 쪽이 충돌이 적다(추론) |
| 클릭 시 보이는 곳에 링크 표시 | `viewer/focus.js:336-376` `renderSourceEvidence`와 `:380-381` `setPassportValue`, 마크업은 `viewer/template.source.html:495-540`(Passport) | Passport는 `data-node-*` 속성(kind·context·tag·brand)을 읽어 칸에 채우고, 소스 근거는 `<a target=_blank rel=noopener>`로 만든다(코드 확인). 같은 방식으로 링크 칸을 하나 더 넣을 수 있다(추론) |
| 뷰어 수정 반영 | `viewer/*` 수정 후 `archify/`에서 `npm run generate:viewer` | `archify/assets/template.html`은 생성물이고 `check:viewer`가 최신 여부를 검사한다(`viewer/README.md`, `package.json`). 생성기 `scripts/generate-viewer.mjs`는 `archify/` 밖에 있다 |
| explainer 본문 링크 대상 확장 | `explainer/inline.mjs`(대상 해석, `http(s)`·`source:`·`block:`·`#`·`typical:`·`node:`·`route:`) | 상대 `.html` 같은 새 대상은 여기서 `null`이 되어 `explainer/target` 오류가 난다(코드 확인). 렌더 쪽은 `render.mjs`의 `inline`이 `kind`별로 HTML을 만든다 |

풀린 질문(5.2): 스키마가 새 필드를 거부하는 것은 확인했다. `<a>` 감싸기와 포커스 충돌은 `role="button"` 때문에 가능성이 높지만 실행은 안 했다. `check-render-output.mjs`가 SVG 안 `<a href>`를 거부하는지는 `href`·`<a`·`external` 검색에 걸리는 규칙을 못 찾았다(미확인, 다른 규칙이 막을 수 있음). 명령행 `finalize`와 `check`로 실제로 통과하는지 돌려 봐야 한다.


### 5.7 커스텀 후보 (2026-11-18, 사용자 승인 전 후보로만 기록)

범위는 explainer(5.3 결정)다. 아래는 [Q7](./questions/q7-explainer-page-structure.md)과 대화에서 나온 후보이고, fork가 이 PC에 clone되기 전까지는 구현하지 않는다.

| 후보 | 하려는 것 | 손볼 곳 | 확인 안 한 것 |
|---|---|---|---|
| A. explainer 본문 링크 확장 | `[x](새 대상)`으로 다른 explainer 페이지로 이동 | `explainer/inline.mjs`(대상 해석), `render.mjs`(HTML 생성), `check.mjs`(검사). 바깥 `reader.js`가 `node:`·`route:`를 iframe에 `postMessage`로 넘기는 부분(`reader.js:348`은 `focus=`·`route=`·빈 해시만 받음)도 바뀔 수 있다 | `reader.js`의 링크 클릭 처리 전체, `check.mjs`가 상대 `.html`을 어떻게 보는지(실행) |
| B. `@steps` 구조화 | step 안에서 `입력·참조·출력·처리·다음`을 칸으로 나눠 `<dl>`로 렌더. 지금 `detail`은 inline 문단 하나라 AI가 `**입력**` 같은 굵은 글씨로 흉내 낸다 | `parse.mjs`의 steps 케이스(칸 정의), `render.mjs:76`(`<li>` 렌더), 필요하면 `reader.css`. 입력 형식은 `입력: … \| 참조: …` 같은 규칙이거나 `@steps` 행 칸 확장 | `reader.js`의 walk(`:474-491`)와 `check.mjs`가 새 DOM과 충돌하는지, 칸 규칙 설계 |
| C. 지시문 재작성 | AI가 위 형식을 항상 쓰도록 `SKILL.md`와 `explainer-authoring.md`를 우리 규칙으로 | vendoring한 위치(5.4: `reports/`에 두지 않음) | — |

현재 archify만으로 할 수 있는 대안은 `@steps`를 짧게 쓰고 상세를 같은 패널의 `@comparison` 표로 두는 것이다(Q7 6절 아래 대화 기준. 표는 step 안이 아니라 별도 블록이고 walk 연결은 없다). B를 하면 이 우회가 필요 없다.

후보 A의 실제 사용처(2026-11-18 확인): `skills-analize/skill-explainers/cloudflare/security-audit/`는 개요 1개와 상세 9개(`security-audit.<이름>.html`)로 나뉘어 있고, 페이지끼리 링크를 못 걸어 한 단계 위 `cloudflare/index.html`에서만 이동한다. 본문에는 `security-audit.setup.html`이 inline 코드(클릭 불가)로만 있다. 설치본 `validate explainer`로 `[x](security-audit.setup.html)`을 넣으면 `explainer/inline-target` 오류가 난다(실행 확인). `https://…`로 바꾸면 통과한다(실행 확인). 즉 http(s) 절대 URL만 가능하고 `file:`·상대 경로는 안 된다.

후보 A 읽기 결과(2026-11-18, fork clone `44781293` = `a7ed6fd`와 같은 explainer 코드, 읽기만 함):
- `explainer/check.mjs:75-80`: `<a href>`에서 `javascript:`·`vbscript:`만 거부하고, `#` 앵커는 id가 있어야 한다. `security-audit.setup.html` 같은 상대 href를 막는 규칙은 없다(코드 확인). 막는 곳은 `inline.mjs`의 `referenceFor`뿐이다.
- `explainer/inline.mjs:133`: web 링크는 `<a href target="_blank" rel="noopener noreferrer">`로 렌더된다. 새 `page` 종류는 같은 자리에서 target 없이(같은 탭) `<a href>`로 만들면 된다(추론).
- `explainer/validate.mjs:98-103`: 링크 종류별 검증이 `if(ref.kind==='source'|'block'|'node'|'route'|'typical')`로 나뉜다. 새 종류를 넣어도 여기서 무시되지만, 형식 검사(파일명 규칙)를 하려면 분기를 추가해야 한다(코드 확인 + 추론).
- 바꿀 곳 3개로 좁혀짐: `inline.mjs`(`referenceFor` 파싱 + 렌더 분기), `validate.mjs`(선택: 파일명 검사), 그리고 prepared payload가 `references` 종류를 목록으로 검사하는지(`prepare.mjs`, 미확인).

후보 A 구현 결과(2026-11-18, fork clone `custom` branch, commit 전 working tree 변경, 실행 확인):
- 문법: `[라벨](page:파일명.html)`. 파일명은 같은 폴더의 형제 파일만(디렉터리·`..`·선행 `.`·쿼리·앵커 불가, `.html`로 끝남). 정규식 `^[\p{L}\p{N}_-][\p{L}\p{N}_.-]*\.html$`.
- 렌더: `<a class="page-link" href="파일명.html">라벨</a>`, `target` 없음(같은 탭). 파일이 있는지는 검사하지 않는다.
- 바꾼 파일 3개: `archify/explainer/inline.mjs`(파싱 `referenceFor` + 렌더 + 오류 문구), `archify/references/explainer-authoring.md`(Inline links 문단 1문장), `test/explainer-inline.test.mjs`(테스트 1개 추가: 허용 2건, 거부 11건).
- 확인: `node --test test/explainer-inline.test.mjs` 6개 통과. explainer 관련 6개 파일 63개 통과(parser·validation·renderer·check·writing·layout). `validate explainer`와 `finalize explainer`(`--quality standard`)가 `page:` 링크 2개를 넣은 샘플에서 통과하고 `check:pass`. `prepare.mjs`·`validate.mjs`·`check.mjs`는 고치지 않았는데도 통과했다. 미확인이던 `prepare.mjs`의 링크 종류 검사는 영향이 없었다.
- 하지 않은 것: `browser-check`(브라우저로 실제 클릭 이동), `test:full`·`test:generated`, `patch explainer` 경로, 페이지 이미지·PDF 내보내기에서의 모양, `archify.zip`·`llms.txt` 등 배포 문서 동기화.

후보 A 실사용 확인(2026-11-18): `skills-analize/skill-explainers/cloudflare/security-audit`의 원고 10개를 fork clone의 `work/security-audit/`(`.git/info/exclude`로 git 제외)에 복사하고, inline 코드로 적힌 `security-audit*.html` 67곳을 `page:` 링크로 바꿔 fork CLI로 `finalize explainer --repo-root skills-analize --quality showcase` 실행. 10개 모두 `validate·deliver·check` 통과, 개요 `browser-check` 통과, 렌더된 `page-link` 67개가 모두 같은 폴더의 실제 HTML 10개로 이어짐(링크 대상 존재 검사는 스크립트로 별도 확인). `recon` 페이지에 문체 경고 1개(`writing-paragraph-length`), 원본 대비 여부는 확인 안 함. 브라우저에서 링크를 눌러 이동하는 동작은 사람이 확인 전.

후보 B 구현 결과(2026-11-18, fork clone `custom` branch, commit 전, 실행 확인): `@steps`의 `detail`이 `**입력** … · **참조** … · **출력** …`처럼 짧은 굵은 라벨로 시작하면 라벨 행(`<dl class="step-fields">`)으로 렌더한다. 문법과 스키마는 그대로이고 렌더 시점 변환만 한다.
- 규칙: detail이 `**라벨**`(8자 이하, 공백·backtick 없음, 뒤에 공백)로 시작하고 라벨이 2개 이상일 때만 적용. 라벨 사이 텍스트가 그 필드이고 끝의 `·`와 공백은 뗀다. inline 코드 안의 `**`와 긴 굵은 문구는 라벨로 보지 않는다. 그 밖의 detail은 이전처럼 문단 하나.
- 바꾼 파일: 새 `archify/explainer/step-fields.mjs`(분리 함수), `render.mjs`(steps 케이스가 `stepDetail` 호출), `reader.css`(`.step-fields` 스타일과 walk 흐림 선택자에 `dl` 추가), `explainer-authoring.md`(규칙 한 문단), 새 `test/explainer-step-fields.test.mjs`.
- 확인: 새 테스트 2개와 explainer 관련 8개 파일 71개 통과. `work/security-audit/candidate.archify.md`(원고 수정 없음)를 `finalize --quality showcase --browser-check`로 렌더해 `validate·deliver·check·browser-check` 통과, step 10개가 모두 `step-fields`로 렌더. headless Chrome 스크린샷에서 1단계가 `입력/참조/출력/처리/다음` 라벨 행으로 보이는 것을 직접 확인(나머지 단계 모양과 라이트 테마·좁은 화면·walk 동작은 확인 못 함).
- 미확인: 배포 파일 목록·release identity 검사(`test:generated`)가 새 `step-fields.mjs`를 알아야 하는지, 단계 수가 많은 페이지의 세로 길이 증가.

fork 정리 결과(2026-11-18, fork clone `custom` branch, 삭제는 `git rm`으로 stage만 했고 commit 전): `journal/`, `integrations/`, `.agents/`, `community/`와 이것에 의존하는 `test/archify-tuning.test.mjs`, `test/community-packages.test.mjs`, `scripts/check-community-packages.mjs`를 지웠다(추적 파일 127개). 삭제 목록은 `fork/prune.list`, 다시 지우는 스크립트는 `fork/prune.mjs`(`--check` 지원), upstream 병합과 conflict 처리 지침은 `fork/FORK.md`.
- 지우기 전 확인(실행): 5개 폴더를 모두 숨기면 `.github/`에 의존하는 CI 테스트가 깨졌다(8개 파일 실패, 원래는 통과). `.github/`를 남기고 4개만 숨기면 `archify-tuning`(`.agents/` 의존)과 `community-packages`(`community/` 의존)만 실패했다. 그래서 `.github/`는 남기고 두 테스트와 스크립트를 목록에 넣었다. `browser-gate.test.mjs`의 2개 실패는 upstream 상태에서도 있던 것이다.
- 지운 뒤 확인(실행): `test:generated` 통과, explainer 관련 8개 파일 71개 통과, `test:core` 19개 통과, CI 관련 3개 파일 통과. `test:full`은 25분 넘게 끝나지 않아 중단했고 결과 없음. `website/test/`는 `community/`에 의존하나 루트 테스트 스크립트에 포함되지 않아 돌리지 않았다.
- 남긴 판단: `docs/`(204개, 약 39MB)와 `website/`(121개)는 지우지 않았다(코드가 가장 많이 언급).

fork commit·push와 설치 결과(2026-11-18, 실행 확인):
- fork `custom` branch에 2 commit(`bf29d3d6` 기능, `1e3721b0` 정리·문서·설치 스크립트)을 만들고 `origin/custom`으로 push했다. `custom`은 `44781293`(upstream)에서 갈라졌다.
- 설치 방법 1(GitHub branch): `npx skills add https://github.com/kanggihoo/archify/tree/custom/archify -g`. 설치하지 않고 `--list --full-depth`만 실행해 `@ custom (archify)`에서 skill `archify` 1개가 인식됨을 확인했다. `npx skills update`가 `custom`을 따라가는지는 미확인.
- 설치 방법 3(junction): `fork/link-install.ps1 install -Force`로 `~/.agents/skills/archify`(실제 폴더, 백업 없이 삭제)를 fork의 `archify/` 폴더로 가는 junction으로 교체했다. `~/.claude/skills/archify`는 기존 링크가 그대로 따라온다. 설치된 경로의 CLI로 `page:` 링크가 `validate`를 통과함을 확인했다. 지금 AI가 읽고 실행하는 archify는 이 fork의 working tree다.
- `my-skills`(`bc8df82`, main에 push): `upstream.json`에서 archify 제거, `known.json`에 `untracked_dependency:archify`와 이유 기록, `EXTERNAL-SKILLS.md`와 `wf-report`·`tutor`의 `SOURCES.md`에 fork 사실 기록, changeset 추가. `upstream-review/check.mjs`는 네트워크 fetch에서 20분 넘게 멈춰 중단했고 `selftest.mjs`는 이 PC에서 symlink 권한 오류로 실패해, `known` 분류는 코드 읽기로만 확인했다.
- `skills-analize/EXPLAINER-PROMPT.md`는 아직 안 바꿨다(249행 "explainer는 로컬 HTML 링크를 만들 수 없다"와 253행 "백틱으로 적는다"가 옛 설명). 설치본이 fork가 되었으므로 AI는 `page:`를 쓸 수 있지만, 이 프롬프트가 그렇게 시키지 않는다.

다음 순서(제안): A를 browser-check와 실제 `security-audit` 문서로 확인 → fork에 commit → B는 walk·check 충돌을 읽고 결정.
