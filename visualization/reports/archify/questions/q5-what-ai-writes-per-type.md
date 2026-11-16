---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-16
updated: 2026-11-16
sources:
  - archify/SKILL.md
  - archify/schemas/*.schema.json
  - archify/renderers/shared/cli.mjs
  - archify/bin/finalize.mjs
  - archify/bin/archify.mjs
---

# [Q5] 타입별로 AI가 만들어야 하는 것

- **상위 개요**: [overview.md](../overview.md)
- **관련**: [Q1](./q1-json-to-html-and-authoring.md)(JSON→HTML 연결), [Q4](./q4-supported-diagram-types.md)(타입 목록)
- **검증 수준**: 스키마의 `required`와 `SKILL.md` 절차는 `코드 확인`(텍스트·파싱). 렌더러가 각 값으로 무엇을 계산하는지는 [rendering-other-types](../capabilities/rendering-other-types.md)(draft)와 [explainer](../capabilities/explainer.md)(ready)에 의존한다. 이 문서에서 새로 렌더링하지는 않았다. AI가 실제로 어떤 JSON을 쓰는지는 `미확인`.

## 1. 질문과 결론

- **질문**: AI가 10종과 explainer를 그리려면 무엇을 만들어야 하나. 별도 script로 HTML을 빠르게 만든다는 이해가 맞나.
- **결론**: 맞다. **AI는 HTML·SVG·CSS를 쓰지 않는다.** 타입별 **JSON 파일 하나**(explainer만 `.archify.md` 초안 하나, JSON도 가능)를 쓰고, 그다음 명령 한 줄을 실행하면 렌더러 스크립트가 SVG와 HTML을 만든다(코드 확인).

  ```bash
  node bin/archify.mjs finalize <type> <candidate.json> <output.html> --quality showcase --json
  node bin/archify.mjs finalize explainer <draft.archify.md> <output.html> ...
  ```

  `finalize`는 `validate` → `deliver`(렌더 + 정적 검사) → `check` → `browser-check`(explainer는 기본 생략)를 차례로 돌리고, 하나라도 실패하면 HTML을 내놓지 않는다([Q1](./q1-json-to-html-and-authoring.md), `SKILL.md:39-49`). 그래서 AI의 일은 **내용 JSON을 맞게 쓰고, 실패하면 진단을 읽고 JSON을 고치는 것**이다.
- **AI가 정하는 것 / 스크립트가 계산하는 것**: 의미(노드·관계·순서·라벨·근거)는 AI, 기하(노드 크기, 연결선 경로, 라벨 위치, viewBox, 색, 애니메이션)는 스크립트다. 다만 타입에 따라 AI가 줘야 하는 좌표 성격의 값이 다르다(3절).

## 2. 파이프라인 전체에서 AI가 맡는 단계

`SKILL.md:32-49` 순서다. 코드가 아니라 LLM용 지시문이다.

| 단계 | AI가 하는 일 | 만드는 산출물 |
|---|---|---|
| 1. 산출물 종류 | native 다이어그램 / explainer / 텍스트 답 중 선택 | 없음 |
| 2. 타입 선택 | Type router 표로 10종 중 하나. 애매하면 `archify guide`(키워드 점수) | 없음 |
| 3. 읽기 | `references/authoring-defaults.md`, 해당 타입 예시 JSON, 스키마(architecture 외 타입은 타입 스키마와 `common.schema.json`까지). 코드 도식이면 대상 레포의 진입점·import·호출 | 없음 |
| 4. 후보 작성 | 완성된 JSON을 한 번에 쓴다. 좌표를 글로 미리 계획하지 않는다 | `<candidate>.json` |
| 5. 실행 | `finalize` 한 번 | HTML + `<out>.delivery.json`, `<out>.finalize.json`, `<out>.finalize-summary.json`(사이드 파일, [explainer](../capabilities/explainer.md) 1.2) |
| 6. 실패 시 수리 | 진단을 읽고 연결된 부분만 고쳐 같은 명령 재실행(횟수 제한은 `references/delivery-contract.md`) | JSON 수정본 |

## 3. 타입별로 AI가 쓰는 JSON

공통으로 모든 JSON이 가진다: `schema_version`, `diagram_type`, `meta.title`. `meta.output`(출력 경로)은 architecture·workflow·sequence·dataflow·lifecycle에서 필수다. 코드 기반이면 `meta.repository`(커밋 SHA·URL)와 요소별 `sources`(파일 경로·줄 범위)를 AI가 채우고, `--repo-root`로 근거를 검증한다(`repository-authoring.md`, [Q2](./q2-verification.md)). `meta.quality_profile`은 특별한 요청이 없으면 `showcase`로 쓰라고 지시한다(`SKILL.md:38`).

"AI가 줘야 하는 위치 값" 열이 타입별 부담이 다른 부분이다.

| 타입 | AI가 만드는 필수 배열 | 각 항목의 필수 키 | AI가 줘야 하는 위치 값 | 스크립트가 계산하는 것 |
|---|---|---|---|---|
| `architecture` | `components` (+ 선택 `connections`, `boundaries`) | 컴포넌트 `id`·`type`·`label`, 연결 `from`·`to`, 경계 `kind`·`label`·`wraps` | `row`/`col` 또는 `pos`가 스키마상 필수는 아니지만 **렌더러가 요구한다**: `layout` 생략이면 모든 컴포넌트에 `pos`, `layout.mode:"grid"`면 `row`/`col`(코드 `render-architecture.mjs:496-504`, [Q6](./q6-json-schema-reference.md) 정정). 연결 경로는 `route:"auto"`를 먼저 쓰고 필요할 때만 명시 | 노드 크기, 연결선 라우팅(`createRouter`), 라벨 위치, viewBox |
| `workflow` | `lanes`, `nodes`, `edges` | 레인 `id`·`label`, 노드 `id`·`lane`·`col`·`type`·`label`, 엣지 `from`·`to` | 노드의 `lane`(스윔레인)과 `col`(칸 번호) | 엣지 경로(`route` 7종 중 자동), 레이아웃 보정 |
| `sequence` | `participants`, `messages` | 참가자 `id`·`type`·`label`, 메시지 `from`·`to`·**`y`**·`label` | **메시지마다 `y` 좌표**(저자가 직접 준다). 선택 `segments`(`from`·`to`는 y 구간) | 참가자 열 간격, 화살표, 활성 바 |
| `dataflow` | `stages`, `nodes`, `flows` | 스테이지 `label`, 노드 `id`·`type`·`label`·**`stage`**·**`row`**, 흐름 `from`·`to`·`label` | 노드의 `stage`(열)와 `row`(행) | 노드 좌표, 흐름 경로·라벨 |
| `lifecycle` | `mainPath`, `states`, `transitions` | 상태 `id`·`type`(8종)·`label`, 전이 `from`·`to` | **없음**. 행복 경로 `mainPath`(상태 id 순서)만 준다. 나머지는 자동 | 전체 배치(척추 + BFS 행) |
| `erd` | `entities` (+ `relationships`) | 엔티티 `id`·`label`, 속성 `name`(+`type`, `key`, fk면 `references`), 관계 `from`·`to`·`fromCardinality`·`toCardinality` | 엔티티 `row`/`col`(태그가 있는 테이블은 필수라고 `SKILL.md:38`가 지시, 도메인이 직사각형이 아니면 `erd/domain-not-drawn`) | 엔티티 박스 크기, 관계선 |
| `class` | `types` (+ `relationships`) | 타입 `id`·`label`·`kind`, 관계 `from`·`to`·`kind` | 타입 `row`/`col`(선택) | 박스 크기, 관계선 |
| `tree` | `nodes` | `id`·`label`(+ `parent`, 루트는 생략) | **없음** | 전체 배치 |
| `timeline` | `events` (+ 선택 `lanes`) | `id`·`at`(시각 문자열)·`title`. `meta.evidence`(observed·illustrative) 필수 | 없음(시간 값이 위치를 정함) | 시간 비례 배치, 휴지기 압축 |
| `waterfall` | `spans` | `id`·`name`·`start`(+ `end` 또는 `duration`). `meta.evidence`(measured·illustrative) 필수 | 없음(시간 값이 위치를 정함) | 막대 폭·중첩 행 |

- **ERD만 따로 요구가 많다**: 물리 컬럼을 전부 `attributes`에 넣고, SQL 타입과 키 역할(`pk`·`fk`·`uk`, 조인 컬럼은 `["pk","fk"]`)을 적고, 모든 `fk`에 `references: "orders.id"`를 붙인다. 컬럼을 카드로 옮기는 것은 금지(`SKILL.md:38`). 8테이블·50컬럼을 넘으면 첫 작성은 `standard`로 하라고 한다.
- **숫자 한도**: 스키마가 정한 값(예: dataflow `row` 0~4, [rendering-other-types](../capabilities/rendering-other-types.md) A)을 넘으면 진단 code로 실패한다. 타입별 치수 예산(authoring-contract R-18)은 [authoring-contract](../capabilities/authoring-contract.md)에서 아직 미결정(draft).
- **선택 기능**: `meta.legend`, `meta.visual_preset`(4종), `brand`(브랜드 마크, 요청이 명시된 경우만), `icon`, `cards`(요약 카드, `common.schema.json`의 `cards`).

## 4. explainer: JSON이 아니라 `.archify.md` 초안

explainer는 native 10종과 다른 경로다. AI는 **Markdown 초안 하나**를 쓰고(`# 제목`으로 시작, 첫 글자가 `{`·`[`면 JSON으로 취급), `finalize explainer <초안> <out.html>`을 실행한다([explainer](../capabilities/explainer.md) 1.3).

| 쓰는 것 | 형식 | 결과 |
|---|---|---|
| 제목 | `# 제목 {#id}` | `meta.title` |
| 결론 | 제목 바로 뒤 평문 한 문단 | `answer.summary` |
| 이유 | 그 뒤 비순서 목록(스키마상 최대 4) | `answer.reasons` |
| 근거 | `@source <id> title=… path=… lines=시작:끝 …` | `sources[]` (`sources`는 스키마 필수) |
| 패널 | `## 질문 {#id span=1..12}` 뒤에 블록 | `panels[]` (스키마 필수) |
| 블록 | 문단, 목록, 표, 펜스, `@callout`·`@facts`·`@metric`·`@steps`·`@code`·`@diff`·`@image`·`@chart`·`@comparison` | 13종 블록 |
| **본문 다이어그램** | `@architecture`·`@workflow`… 또는 `@diagram <타입>`에 **약식 행**(`parse` C-11) | 같은 렌더러로 SVG를 만들어 페이지에 내장 |

**explainer에서 쓸 수 있는 다이어그램 타입 (10종 모두 가능, 입력 방식만 다르다)**

| 방식 | 타입 | AI가 쓰는 것 |
|---|---|---|
| 약식 행(초안 안에 직접) | `architecture`, `workflow`, `sequence`, `tree`, `timeline`, `erd` (6종) | `@<타입> id=… title=…` 아래 파이프 행. 노드 `id \| 라벨 \| 타입`, 간선 `from > to \| 라벨 \| variant` 등 [explainer-authoring.md "Compact native diagrams"] |
| 별도 spec 파일 | `dataflow`, `lifecycle`, `class`, `waterfall` (4종) | 같은 디렉터리에 native JSON(Q6 구조) 파일을 따로 쓰고 초안에서 `@diagram <타입> source=파일.json`으로 참조. 명시 좌표가 필요한 다이어그램도 이 방식 [같은 문서] |
| JSON 초안 | 10종 전부 | `diagram` 블록의 `diagramType`+`spec`(native JSON 전체를 객체로) [explainer.schema.json] |

그래서 explainer 작업은 `.archify.md` 하나가 기본이지만, 위 4종을 쓰면 JSON 파일이 추가로 생긴다. 차트(`pie`, `xychart-beta` 등)는 native 다이어그램이 아니라 ```` ```mermaid ```` 펜스이고, 순서도·시퀀스 등 Mermaid는 위 약식 문법을 쓰라고 한다. 본문 다이어그램 개수는 문서에 "최대 4개"라고 적혀 있지만 코드에는 상한이 없다([explainer](../capabilities/explainer.md) 2.1, [next.md](../next.md)).

즉 explainer 안에 다이어그램을 넣을 때도 별도 JSON 파일이 아니라 초안 안의 약식 행으로 쓴다. `finalize`가 본문 다이어그램마다 native 렌더러와 `check-render-output.mjs`를 자식 프로세스로 실행하고, 문장 속 `node:`·`route:` 링크를 렌더된 SVG에 대조한다(explainer 1.1 2번). 하나라도 오류면 HTML이 만들어지지 않는다. 고칠 때는 `patch explainer <html> <패널id> <교체파일> <out.html>`로 패널 하나만 바꿀 수 있다.

## 5. 정리: "별도 script로 빠르게" 부분의 정확한 의미

- HTML을 만드는 script는 `renderers/<type>/render-<type>.mjs`이고 AI가 호출하지 않는다. `finalize`가 호출한다(`finalize.mjs`, `bin/archify.mjs:4870`).
- **빠르다고 보기 어려운 부분**: `browser-check`는 실제 브라우저를 띄워 측정한다(native 기본 포함). 한 번의 `finalize`가 렌더 + 정적 검사 + 브라우저 측정이라, 실패하면 수정 → 재실행 반복이 생긴다. 걸리는 시간은 측정하지 않았다(`미확인`).
- AI가 쓰는 JSON은 짧지 않다. 예시 `examples/orders.erd.json`·`cache-miss-request.sequence.json`을 보면 노드마다 여러 키가 있고, sequence는 메시지마다 `y`를 직접 계산해 줘야 한다(코드 확인, 파일을 읽음).

## 5.1 AI가 파일을 만든 다음 과정 (`finalize` 한 번의 내부)

출처: [finalize-orchestration](../capabilities/finalize-orchestration.md), [delivery](../capabilities/delivery.md), [Q2](./q2-verification.md)(코드 확인, 실행은 이전 세션에서 일부). AI는 `finalize`만 부르고, 나머지는 `finalize`가 내부에서 부른다.

| 순서 | 호출되는 것 | 하는 일 | 만들어지는 것 |
|---|---|---|---|
| 0 | (explainer만) 초안 prepare | 파싱·검증·근거 동결·본문 다이어그램 렌더 검사. 오류가 하나라도 있으면 HTML을 만들지 않음 | 임시 번들(명령이 끝나면 정리) |
| 1 | `archify deliver <type> <입력> <출력>` (자식 프로세스) | staging 폴더에서 `renderers/<type>/render-<type>.mjs`로 JSON을 읽어 검증(스키마, 관계 id 중복, `--repo-root`가 있으면 근거 확인)하고 SVG→HTML로 렌더한 뒤 정적 검사. 통과하면 HTML과 provenance를 최종 위치에 둠. `validate`는 이 안에 포함 | **HTML**, `<이름>.delivery.json`(HTML 해시를 담은 provenance) |
| 2 | `archify check <출력> --require-provenance` (자식 프로세스) | 산출물이 deliver가 만든 바이트 그대로인지 확인하고 SVG 정적 검사(직각 화살표, 교차, 라벨 간격 등) | 검사 영수증(JSON, 이 문서에서 파일 위치는 미확인) |
| 3 | `browser-check` (같은 프로세스에서 Chrome 실행; explainer는 기본 생략) | 1440×900 등 4개 뷰포트에서 가로 넘침·글자 크기를 측정 | 영수증 JSON(스크린샷은 만들지 않음) |
| 4 | 마지막 확인 | provenance가 현재인지, 산출물과 입력이 도중에 안 바뀌었는지 | `<이름>.finalize.json`(전체 영수증), `<이름>.finalize-summary.json`(요약). 요약은 stdout에도 출력 |

- 첫 실패에서 멈추고 진단(`code`, `subject`, `evidence`, `supportedFixes`)을 영수증에 남긴다. AI는 이를 읽고 JSON을 고쳐 `finalize`를 다시 실행한다.
- 기본 품질이 `showcase`이면 경고가 하나라도 있을 때 `deliver` 단계가 실패로 처리된다.
- `deliver`가 실패하면 기존 HTML 바이트는 그대로 두되 provenance를 "실패"로 바꾸고 이후 `check`를 막는다([delivery](../capabilities/delivery.md) T-04). Q2의 "직전 성공 파일 유지" 표현보다 이 설명이 더 정확하다.
- 기본 `finalize`는 사람 눈 검토를 하지 않는다. 영수증에 `visualReview: "not-requested"`가 남는다.
- 각 검사의 임계값과 세부 판정은 미확인이다([Q2](./q2-verification.md)).

### 5.2 브라우저 검증(3단계)은 어떻게 판정하나

결론: 측정과 pass/fail 판정은 전부 스크립트가 한다. AI는 화면을 보지 않고 영수증 JSON의 진단만 읽어 candidate.json을 고친다. 출처: `archify/bin/visual-check.mjs`, `references/delivery-contract.md` "Automated browser evidence"(코드 확인, 읽기만 했고 실행은 안 함).

| 순서 | 누가 | 하는 일 |
|---|---|---|
| 1 | 스크립트 | Chrome/Chromium/Edge를 자식 프로세스로 띄워 DevTools 프로토콜(CDP)로 조종. `ARCHIFY_CHROME`가 있으면 그 경로만 쓰고 대체 탐색 안 함 |
| 2 | 스크립트 | 1440×900, 1600×1000, 1920×1080, 2048×1320 4개 뷰포트로 `file://…?theme=light` 열기. 다크 테마(양 끝 뷰포트)와 READ/Still 상태도 확인 |
| 3 | 스크립트 | 폰트 로딩과 레이아웃 안정화를 기다린 뒤 페이지 안에서 JS로 값을 측정 |
| 4 | 스크립트 | 측정값을 기준과 비교해 `status: pass\|fail` 결정 |
| 5 | 스크립트 | `<이름>.browser-check.json` 영수증 기록(artifact SHA-256 포함, 스크린샷 없음, `visualReview: "not-requested"`) |
| 6 | AI | 실패하면 영수증의 진단(`minimumProjectedNodeText`, `owner`, `supportedFixes` 등)을 읽고 JSON을 고쳐 `finalize` 재실행 |

측정 항목(코드 확인):

- **가로 넘침**: `document.documentElement.scrollWidth > innerWidth`이면 실패(`visual-check.mjs:1947`). 가로 넘침은 항상 실패. 세로 스크롤은 렌더러가 `data-reader-fit` 선언을 하고 글자가 읽을 만할 때만 허용(`overflowDisposition: "readable-vertical-scroll"`).
- **글자 크기**: 각 SVG `<text>`의 `font-size`에 화면 배율을 곱한 projected px의 최솟값이 `MIN_PROJECTED_NODE_TEXT_PX` 미만이면 실패(`:1738-1759`, `:1958`). `authoring-defaults.md`는 6px을 실패 기준, 1440px에서 7.5px 이상을 목표로 적었다.
- **겹침·잘림**: `getBoundingClientRect`로 범례·도크 같은 Viewer UI와 다이어그램의 충돌, SVG가 패널 안에 있는지 확인.
- **종료 상태**: pass는 exit 0, fail은 exit 1, 브라우저가 없으면 skipped는 exit 2. 런타임 오류는 skipped로 바꾸지 않고 fail로 둔다.

한계: 이 검사는 넘침·글자 크기·겹침만 잰다. 의미가 맞는지, 보기 좋은지는 보지 않는다(추론: 코드가 측정하는 항목에 그런 것이 없음). `MIN_PROJECTED_NODE_TEXT_PX`의 상수 값은 열어 보지 않았다.

### 5.3 candidate.json이 맡는 일

candidate.json은 "무엇을 그릴지"만 적은 데이터이고, 좌표 계산과 SVG 생성은 렌더러가 한다(코드 확인, 3절·5절 참조). AI의 작업은 (1) 요청이나 레포를 읽고 노드·연결·라벨·카드를 정해 구조화하고 `sources`에 근거를 붙이는 것, (2) 타입과 노드 `type`·연결 `variant` 같은 의미 속성을 고르는 것(색과 범례가 여기서 정해짐), (3) 타입별 배치 힌트를 주는 것(architecture `row/col`, workflow `lane+col`, sequence `y`, tree `parent`만)이다. 선 경로, 박스 크기, 색, 애니메이션, 범례 위치, HTML 템플릿은 AI가 건드리지 않는다. 같은 JSON이 같은 HTML을 낳는지는 두 번 돌려 비교하지 않아 추론이다.

### 5.4 explainer: steps용 다이어그램, 이미지, 좌우 배치

출처: [explainer](../capabilities/explainer.md) R-08·R-09·R-13·R-14·R-15, `archify/explainer/render.mjs:95-106`, `layout.mjs`, `reader.css:221,449`(코드 확인, 브라우저 실행은 안 함).

**steps가 가리키는 native 다이어그램에 별도 candidate.json이 필요한가**: steps는 그림을 그리지 않고 같은 문서의 diagram 블록 id를 가리킨다. 다이어그램을 쓰는 방식에 따라 다르다.

| 방식 | 별도 파일 | 대상 |
|---|---|---|
| 약식 행(`@workflow` 등) | 불필요(초안 안에 씀) | sequence, architecture, workflow, tree, timeline, erd |
| `@diagram <타입> source=파일.json` | 필요(같은 폴더의 native JSON, candidate.json과 같은 스키마) | dataflow, lifecycle, class, waterfall은 이 방식뿐 |
| JSON 초안의 `diagram` 블록(`diagramType`+`spec`) | 불필요(인라인) | 10종 전부 |

`@steps` 행의 4~7번째 칸(다이어그램 id, 노드, `from~to`, 엣지 id)으로 연결하고, prepare 마지막에 렌더된 SVG의 노드·엣지와 대조한다(없으면 `diagram-node-reference`·`diagram-edge-reference`, 경로가 방향 엣지로 도달 불가면 `diagram-route-reference`). 별도 JSON을 써도 `finalize explainer`는 한 번이고, 다이어그램은 prepare 안에서 `render-<타입>.mjs`와 `check-render-output.mjs`를 받는다. 자식 다이어그램의 browser-check는 하지 않는다.

**이미지**: `@image path=… alt=…`에 초안 파일 기준 상대 경로를 쓴다. 초안 디렉터리 안의 일반 파일이어야 하고(심볼릭 링크·`..` 금지), PNG·JPEG·GIF·WebP만(확장자와 바이트 시그니처 일치), 장당 8 MiB·합계 32 MiB 이하다. `data:` URL로 HTML에 내장되며 http 같은 외부 이미지 참조는 `check`가 거부한다.

**왼쪽 설명, 오른쪽 workflow 그림**: 한 패널에 diagram 블록이 정확히 하나이고, 그 diagram의 노드·경로를 가리키는 `@steps`가 같은 패널에 있으면 `guided` 패널이 된다(`render.mjs:101`). 텍스트(`guide-text`)는 왼쪽, 그림(`guide-figure`)은 오른쪽이고 `flex-flow: row-reverse wrap`이라 폭이 모자라면 줄바꿈된다(`reader.css:221`). 패널 폭은 diagram 캔버스 viewBox 폭이 1000을 넘으면 12칸, 아니면 8칸이다(`layout.mjs`). 조건 `figures.length === 1`이라 한 패널에 diagram이 둘이면 좌우 구성이 안 된다. 1255px 이하에서는 diagram 패널과 이웃 패널이 12칸이 된다(`reader.css:449`). 패널 안의 좌우 비율을 저자가 정하는 방법은 코드에서 찾지 못했다. 실제 화면은 `미확인`.

## 6. 확인 못 한 것

- LLM이 타입별로 필수 키를 한 번에 맞게 쓰는 비율과 평균 수리 횟수(미실행).
- `architecture` 컴포넌트에 `row`/`col`/`pos`를 생략했을 때 렌더러가 어떻게 배치하는지(스키마상 필수가 아님만 확인, 실행 안 함).
- 타입별 README(`renderers/<type>/README.md`)에 있는 작성 지침.
- explainer 약식 행(C-11)의 타입별 문법. 이 문서는 [explainer](../capabilities/explainer.md) 요약만 따랐다.
