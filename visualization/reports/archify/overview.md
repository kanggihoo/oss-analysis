---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-01
updated: 2026-11-01
---

# archify Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/tt-a1i/archify`
- **작업트리 상태**: Clean (`artifacts/archify/repo-metadata.txt`)
- **분석 목적**: 학습·이해 — 사용자가 스킬을 트리거했을 때 **요청 → 산출 HTML 전달까지의 내부 흐름**. 특히 (a) JSON 초안과 HTML의 연결, (b) 무엇을 쓸지 정하는 방식, (c) 검증 방식, (d) 타입별·출력 위치 커스터마이징 여지. 스펙을 어디에 쓸지는 미정(재구현 계획 없음)
- **라이선스**: Apache-2.0 — `repos/archify/LICENSE`. 과거 MIT 부여분은 `LICENSE-MIT`·`NOTICE`에 유지
- **분석 대상 제품**: 스킬 패키지 `archify/`(CLI + 렌더러 + 뷰어 템플릿). 제외(부속): `website/`, `docs/`, `journal/`, `experiments/`, `benchmarks/`, `integrations/`, `test/`, `tools/`
- **스펙 범위**: 승인됨 — 행 1~12 전체 (사용자 요청 2026-11-02 "12개의 feature map에 대해서 조사 진행"). 부속 행 11·12도 사용자가 포함시킴. 제외 행 없음
- **로컬 설치본**: `~/.agents/skills/archify`(`~/.claude/skills/archify`가 가리킴)와 레포의 `archify/` 디렉터리는 `diff -rq` 결과 차이가 없다(`실행 확인`, 2026-11-01).

---

## 2. 프로젝트 개요

LLM 에이전트가 **정해진 JSON 스키마(또는 explainer용 Markdown 초안)** 를 쓰면, Node CLI(`archify/bin/archify.mjs`)가 그것을 검증하고 단일 HTML로 렌더링한 뒤 정적 검사와 실제 브라우저 측정까지 거쳐 전달한다. 스킬(`SKILL.md`)은 LLM에게 주는 지시문이고, 코드가 LLM을 호출하는 부분은 없다.

### Feature map

흐름 순서(트리거 → 전달)로 나눴다. "구분"의 핵심은 이번 목적(내부 흐름 이해) 기준이다. 검증 수준은 이번에 읽은 범위 기준이며, 읽지 않은 구현 내부는 7절 미탐색에 있다.

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 산출물 선택 | 요청 → native 다이어그램 / explainer 페이지 / 텍스트 답 중 무엇을 만들지. 규칙 줄 `[archify explainer: …]`이 기본값을 바꿈 | `archify/SKILL.md:18-30` | 없음 | 핵심 | [artifact-choice](./capabilities/artifact-choice.md) · ready | 코드 확인(지시문 읽음). 에이전트가 실제로 따르는지는 미확인 |
| 2 | 타입 선택·`guide` | 10종 native 타입 중 선택(Type router 표). 애매하면 `guide`가 시나리오 키워드 점수로 추천. Mermaid 입력은 타입 매핑 후 JSON 새로 작성 | `SKILL.md:58-85`, `bin/archify.mjs` `commandGuide`, `recipes/scenarios.mjs:387` `recommendScenario` | 1 | 핵심 | [type-routing](./capabilities/type-routing.md) · ready | 코드 확인(`guide` 점수 방식) / 라우터 표는 지시문 |
| 3 | 근거 수집·초안 작성 규칙 | LLM이 코드·설명을 읽고 JSON을 쓰는 규칙(근거 `sources`, 레포 고정, 기본 추상화 수준, 레이아웃 지침) | `references/repository-authoring.md`, `references/authoring-defaults.md`, `SKILL.md:32-46` | 2 | 핵심 | [authoring-contract](./capabilities/authoring-contract.md) · draft | 코드 확인(지시문). 코드가 강제하는 부분은 4~5행 |
| 4 | `finalize` 오케스트레이션 | 초안+출력 경로 → 단계 순서 실행, 영수증 기록, 후보 해시 고정, 첫 실패에서 중단 | `bin/archify.mjs:5888` `commandFinalize`, `bin/finalize.mjs:722` `runFinalize` | 5~8 | 핵심 | [finalize-orchestration](./capabilities/finalize-orchestration.md) · ready | 코드 확인 |
| 5 | 입력 로드·검증 | JSON 파싱 → 출력 경로 형식 → 스키마 → 로케일 → 관계 ID 중복 검사 → 엔지니어링 프로파일 → 저장소 근거(`--repo-root`). 노드·끝점 검사와 레이아웃 검증은 각 렌더러(행 6) 소관 | `renderers/shared/cli.mjs:48` `loadDiagram`, `validator.mjs:38`, `repository-evidence.mjs:155` | 없음 | 핵심 | [input-validation](./capabilities/input-validation.md) · ready | 코드 확인 + 실행 확인(진단 code 37개 사례) |
| 6 | 렌더링 | 검증된 JSON → 타입별 SVG → `assets/template.html` 슬롯 채움 → HTML. 원본 JSON은 HTML에 들어가지 않음 | `renderers/<type>/render-<type>.mjs`, `renderers/shared/utils.mjs:150` `applyTemplate`, `cli.mjs:234` `writeDiagram` | 5 | 핵심 | [rendering](./capabilities/rendering.md) · ready (하위: [architecture-routing](./capabilities/rendering-architecture-routing.md) ready, [workflow](./capabilities/rendering-workflow.md) ready, [contracts](./capabilities/rendering-contracts.md) ready, [other-types](./capabilities/rendering-other-types.md) draft(정합 재검증 필요)) | 코드 확인(architecture·공통). 나머지 9개 타입 렌더러 내부는 미확인 |
| 7 | 전달(deliver) | staging에서 렌더·검사 후 HTML과 provenance 파일을 한 쌍으로 교체. 실패하면 HTML 바이트는 유지되지만 provenance는 `failed` 표지로 바뀜(성공 전달로 복구). 출력 경로 우선순위 | `bin/archify.mjs:4400` `commandDeliver`, `:3236` `commitDeliveryPair`, `renderers/shared/output-path.mjs:373` | 6, 8 | 핵심 | [delivery](./capabilities/delivery.md) · ready | 코드 확인 + 실행 확인(provenance 필드, 재전달, 실패 후 상태). 잠금 경쟁·중단 복구는 코드만 |
| 8 | 자동 검증 게이트 | `check`(SVG 정적 검사, provenance 확인) → `browser-check`(Chrome 4개 뷰포트·테마·READ/Still 측정) | `scripts/check-render-output.mjs`, `bin/archify.mjs:5581` `commandCheck`, `:5663` `executeBrowserEvidence`, `bin/visual-check.mjs:37` | 7 | 핵심 | [verification-gates](./capabilities/verification-gates.md) · ready | 코드 확인 + 실행 확인(임계값 포함: 직각 0.01, 글자 하한 6px 등). 정적 검사와 브라우저의 글자 하한 계산이 다름 |
| 9 | 실패 진단·수리 루프 | 비정상 종료 + 진단 JSON(`nextAction`·`supportedFixes`) → 지침에 따라 초안 수정 → 재실행. 수리 한도는 코드가 세지 않고 지시문(5종)에만 있음. 시각 검토는 선택 | `references/delivery-contract.md:3`, `bin/finalize.mjs` `failureDiagnostics`, `SKILL.md:49-51` | 4, 8 | 핵심 | [repair-loop](./capabilities/repair-loop.md) · ready | 코드 확인 + 실행 확인(신호). 지시문 준수는 미확인 |
| 10 | explainer 경로 | Markdown 초안 → prepare(파싱·검증·근거·다이어그램·참조 일괄) → render → deliver·check. 기본은 브라우저 검사 없음. 패널 단위 `patch` | `explainer/prepare.mjs:19`, `validate.mjs:17`, `render.mjs:37`, `bin/finalize.mjs:746` | 5, 6, 7 | 핵심 | [explainer](./capabilities/explainer.md) · ready | 코드 확인 + 실행 확인(R-01~R-25, R-29). Ask(R-26~28)는 브라우저 미실행으로 코드 확인 |
| 11 | 결과 뷰어 | HTML 안의 포커스·경로 추적·검색·내보내기 | `viewer/*.js`, `assets/template.html`, `references/viewer-runtime.md` | 6 | 부속 | [viewer](./capabilities/viewer.md) · ready | 코드 확인 + 실행 확인(headless Chrome: 딥 링크·단축키·내보내기). 호버·패닝·클립보드·Safari/Firefox는 미확인 |
| 12 | `compare architecture`, `brands`, `migrate`, `preview`, `doctor`·`demo`·`examples` | 흐름 밖 보조 명령 | `bin/archify.mjs`의 같은 이름 함수, `delta/`, `bin/preview.mjs`. `doctor`·`demo`·`examples`도 포함. `update` 확인과 `recover`는 명령이 아니고 스크립트 | 7(설명용) | 부속 | [auxiliary-commands](./capabilities/auxiliary-commands.md) · draft | compare·migrate는 실행 확인, preview는 코드 확인, brands capture·examples는 인터페이스 수준 |

**공유 계약**

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 타입별 JSON 스키마 + 공통 정의(`$defs`) | 3, 5, 6 | `archify/schemas/*.schema.json`, `common.schema.json` | 소유: [input-validation](./capabilities/input-validation.md) 1.3 (공통 meta). 타입별 필드는 스키마 파일이 원본 | 코드 확인(최상위 키·meta 키·공통 enum). 타입별 세부 필드는 일부만 |
| 진단 객체(`code`, `message`, `subject`, `evidence`, `supportedFixes`) | 4, 5, 7, 8, 9 | `renderers/shared/diagnostics.mjs`, `cli.mjs`의 `throwDiagnosticError` | 소유: [input-validation](./capabilities/input-validation.md) 1.3 B. 필드는 `code, severity, message, subject, evidence, supportedFixes`(+선택 `suppresses`) | 코드 확인(모양) |
| 영수증·provenance 파일(산출물 해시 연결) | 4, 7, 8 | `bin/finalize.mjs` 영수증, `bin/archify.mjs`의 `*DeliveryProvenance*` | provenance(`<stem>.delivery.json`): [delivery](./capabilities/delivery.md). finalize 영수증·요약: [finalize-orchestration](./capabilities/finalize-orchestration.md) 1.3 | 코드 확인(존재와 쓰임) / 내용 형식은 미확인 |

**범위 결정 기록** (처음 제안은 행 4~9였고, 사용자가 전체 12행으로 확장해 승인함. 아래는 처음 제안 근거)

- 행 4~9: 사용자가 정한 관심사(전 과정 흐름, JSON→HTML, 검증)가 그대로 들어간다. 코드를 따라가야 하는 부분이라 스펙으로 쓸 가치가 있다.
- 행 1~3: LLM에게 주는 지시문이라 코드 스펙보다 `questions/q1`로 충분하다. 제외 권장.
- 행 10(explainer): 별도 파이프라인이라 따로 보려면 포함. 이번 관심사에 직접 닿지 않아 기본 제외 권장.
- 행 11·12: 부속, 제외.

**대조한 범위와 미탐색 영역**
- 대조: README의 "How it works"·타입 표(앞 140줄 읽음), `SKILL.md` 전체, `bin/archify.mjs`의 명령 사용법 표와 `switch`, `bin/finalize.mjs`의 `runFinalize`, `schemas/` 최상위 키.
- 문서와 구현의 차이: 아직 발견하지 못함. 비교는 `finalize`의 단계 목록(문서 4단계 vs 코드의 `validate`가 `deliver`에 내장)에서만 했다: 문서는 "validate, deliver, check, browser-check"라고 하지만 코드는 `deliver` 하나가 검증을 겸한다(`finalize.mjs:835`, 영수증의 `execution: 'embedded-in-deliver'`). 모순은 아니다.
- 미탐색: `viewer/*`와 `assets/template.html` 내부(787KB), 10개 렌더러 중 architecture 외 9개, `check-render-output.mjs`의 임계값, `visual-check.mjs` 내부, `atomic-output.mjs`·잠금·복구(`recover-output.mjs`), `explainer/` 내부, `update` 확인, `brands`, 테스트 316개.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 호출부터 전달까지 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 스킬 호출 → 초안 → finalize → 렌더러 → 전달 → 두 게이트 → 영수증 |
| 동작 과정 설명 페이지 (explainer, 7패널) | [trigger-flow.archify.md](./diagrams/trigger-flow.archify.md) | [trigger-flow.html](./diagrams/trigger-flow.html) | feature map 행 1~10을 한 페이지로: 산출물 선택, 실행 순서(sequence), 입력 검증 순서(workflow), 검증 겹과 한계, 커스터마이징, 행 대응표, 확인할 것 |

> **검증 상태** (`실행 확인`, 2026-11-01): 설치된 스킬로 `finalize`를 실행했다. 구조도는 `validate`·`deliver`·`check`·`browser-check` 모두 통과, `meta.repository` 근거 줄 번호도 `--repo-root`로 확인됐다. explainer 페이지는 `deliver`·`check` 통과, `browser-check`는 explainer 기본값이라 실행하지 않았다. 둘 다 시각 검토(사람 눈)는 하지 않았다(`visualReview: not-requested`). 구조도의 `receipt → 사용자` 점선 경로는 직접 지정한 `via` 좌표이며 겹침 여부는 자동 검사 통과만 확인했다.

### 그림 해설

**읽는 순서**: 왼쪽 위(사용자) → 오른쪽으로 `SKILL.md` → `candidate.json` → `finalize`, 아래 줄(렌더러 → 출력) → 가장 아래 줄(두 게이트) → 오른쪽 `receipt`가 점선으로 사용자에게 돌아온다.

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 사용자 + LLM | 요청을 해석하고 JSON을 쓰고 실패 진단을 읽어 고친다 | 요청 → 초안, 영수증 → 수정 | `archify/SKILL.md:18-24` | 지시문 확인 / 에이전트 행동은 미확인 |
| SKILL.md | 산출물 종류 선택, 타입 라우터, 작성 규칙을 LLM에게 준다 | 지시문 | `archify/SKILL.md:32-70` | 코드 확인(텍스트) |
| candidate.json | LLM이 쓴 초안(explainer는 `.archify.md`) | 스키마를 따르는 JSON | `SKILL.md:32-44` | 코드 확인 |
| finalize | 단계를 차례로 자식 프로세스로 실행하고 영수증을 쓴다 | 초안·출력 경로 → 영수증 | `bin/archify.mjs:5888` `commandFinalize`, `bin/finalize.mjs:835` | 코드 확인 |
| 타입별 렌더러 | 입력 검증 → SVG 생성 → 템플릿에 넣어 HTML 작성 | JSON → HTML | `renderers/shared/cli.mjs:48` `loadDiagram`, `:234` `writeDiagram`, `render-architecture.mjs:1178-1204` | 코드 확인(공통·architecture) |
| template.html | 뷰어 코드·스타일이 들어 있는 고정 껍데기. 제목·SVG·카드·언어 데이터 슬롯만 채워짐 | 슬롯 | `renderers/shared/utils.mjs:150` `applyTemplate` | 코드 확인 |
| 대상 Git 레포 | `sources`의 파일·줄이 고정 커밋에 있는지 대조당한다 | 파일 존재·줄 수 | `renderers/shared/repository-evidence.mjs:155` | 코드 확인(존재만 확인, 내용 일치는 미확인) |
| output.html + provenance | 산출 HTML과 그 해시를 묶은 사이드 파일 | 한 쌍으로 교체 | `bin/archify.mjs:3236` `commitDeliveryPair`, `:5124` | 코드 확인(호출), 내부 미확인 |
| check | 산출 HTML의 SVG를 정적으로 검사 | HTML → 통과/진단 | `scripts/check-render-output.mjs:111` | 코드 확인(구조) |
| browser-check | Chrome으로 열어 4개 뷰포트에서 측정 | HTML → 통과/진단 | `bin/archify.mjs:5663`, `references/delivery-contract.md:416` | 코드 확인(호출)·문서 |
| finalize receipt | 단계별 결과와 진단을 담은 JSON | 영수증 | `bin/finalize.mjs:586` `compactFinalizeReceipt` | 코드 확인 |

**미확인 영역**: 그림에 넣지 않은 explainer 경로, 뷰어 내부, `update` 확인, 복구 명령.

---

## 4. 질문 (Questions)

- [Q1: JSON과 HTML은 어떻게 연결되고, 무엇을 쓸지는 누가 정하나](./questions/q1-json-to-html-and-authoring.md) - *HTML에는 원본 JSON이 없다. 내용은 LLM이 정하고 코드는 모양과 근거 존재만 확인한다*
- [Q2: 만들어진 결과물은 어떻게 검증하나](./questions/q2-verification.md) - *스키마 → 레이아웃·근거 → 정적 검사 → 브라우저 측정 순. 인용한 줄의 내용이 주장과 맞는지는 코드가 확인하지 않는다*
- [Q3: 타입별·출력 위치 커스터마이징 여지](./questions/q3-customization-and-output.md) - *색은 못 바꾸고 프리셋 4종·언어·범례·레이아웃 수치·출력 경로는 바꿀 수 있다*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸 (16개 작성(12행 + 하위 4): ready 13 / draft 3)
