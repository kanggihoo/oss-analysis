---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-17
updated: 2026-11-17
sources:
  - archify/explainer/render.mjs
  - archify/explainer/reader.js
  - archify/explainer/reader.css
  - archify/explainer/parse.mjs
  - archify/explainer/layout.mjs
  - archify/explainer/diagrams.mjs
  - archify/explainer/page-bundle.mjs
  - archify/references/explainer-authoring.md
  - viewer/README.md
---

# [Q7] explainer 페이지는 어떻게 만들어지나 (template.html, `@facts`, 밑줄, 좌우 배치, `@steps`)

- **상위 개요**: [overview.md](../overview.md)
- **관련**: [Q5](./q5-what-ai-writes-per-type.md)(AI가 쓰는 것), [explainer 스펙](../capabilities/explainer.md), [viewer 스펙](../capabilities/viewer.md)
- **계기**: 2026-11-17에 사용자가 `skill-explainers/cloudflare/security-audit/candidate.archify.md`를 렌더해 보며 물은 질문 8개를 순서대로 정리했다. 링크 커스텀(explainer만)을 하려면 explainer 페이지가 어떤 부품으로 도는지 알아야 해서 나온 질문들이다.

## 0. 이 문서를 어디에서 읽어 만들었나

기준 SHA `a7ed6fd`의 `repos/archify/archify/explainer/`를 읽었다. 렌더 결과는 직접 열어 보지 않았다. 사용자가 보내 준 스크린샷 2장과 `candidate.archify.md`로 코드 읽기와 맞춰 봤다.

| 읽은 파일 | 어디를 |
|---|---|
| `explainer/render.mjs` | 페이지 조립(128행), 블록별 HTML(66~84행), 패널 배치(97~106행) |
| `explainer/reader.js` | 안쪽 다이어그램 dialog(325~374행), 노드 이름 연결 `linkTerms`(407~445행), steps walk(474~491행) |
| `explainer/reader.css` | `.term`(176행), `.guided`(219~224행), 좁은 화면(449행), `.facts`(150~154행) |
| `explainer/parse.mjs` | 제목 `{#id span=N}`(87~89행), 지시문 행 수집(164행), 표 → comparison(259~261행) |
| `explainer/layout.mjs`, `diagrams.mjs`, `page-bundle.mjs` | 12칸 배치, 안쪽 다이어그램 렌더 호출(482~483행), gzip 저장 |
| `references/explainer-authoring.md` | 선택표(60~77행), 제목 문법(254행), Directive reference(212~232행) |

## 1. explainer는 `template.html`을 쓰나

**쓰지 않는다. 대신 explainer 안의 다이어그램은 `template.html`을 쓴 일반 HTML이다.** 파일이 두 겹이다.

```
explainer 페이지 (바깥 HTML)
 ├─ 본문·패널·표·차트  → render.mjs가 문자열로 직접 조립 + reader.css + reader.js
 └─ @architecture, @workflow 등 다이어그램 (안쪽 HTML)
      → render-<type>.mjs로 만든 일반 다이어그램 HTML (template.html + 뷰어 포함)
      → gzip+base64로 바깥 페이지의 JSON 안에 저장
```

| 주장 | 근거 | 검증 수준 |
|---|---|---|
| 바깥 페이지는 `render.mjs:128`이 `<!doctype html>`부터 한 문자열로 만든다. `explainer/*.mjs`와 `reader.js`에 `template.html`·`applyTemplate` 참조가 없다 | `render.mjs:128`, grep | 코드 확인 |
| 안쪽 다이어그램은 `renderers/<type>/render-<type>.mjs`를 `node`로 실행해 만들고 `check-render-output.mjs`로 검사한다 | `diagrams.mjs:482-483` | 코드 확인 |
| 안쪽 HTML은 gzip 압축되어 `htmlGzip`으로 들어가고, 사용자가 다이어그램을 열 때 `reader.js`가 풀어 `<iframe srcdoc>`에 넣는다 | `page-bundle.mjs:13-16`, `reader.js:325-374` | 코드 확인 |
| 안쪽 HTML 안의 뷰어(Passport·Route·검색)는 일반 다이어그램과 같은 `template.html`의 뷰어다 | 위 두 줄에서 따라감 | 추론(안쪽 HTML을 열어 보지는 않음) |

**바깥과 안쪽이 대화하는 방식.** `reader.js`는 안쪽 HTML을 `srcdoc`에 넣을 때 `</body>` 앞에 브리지 스크립트를 끼운다(`reader.js:367`). 바깥이 `postMessage`로 `{theme, preset, hash}`를 보내면 안쪽이 반영한다. 안쪽은 해시가 `''`, `focus=<id>`, `route=<a>~<b>` 세 형태일 때만 받는다(`reader.js:348`의 정규식). 즉 explainer 링크가 안쪽 뷰어에 요청할 수 있는 것은 노드 포커스와 경로 둘뿐이다. 코드 확인.

**링크 커스텀에서의 의미.** 본문 링크 `[x](node:…)`, `[x](route:…)`는 바깥 `reader.js`가 위 `postMessage`로 처리한다. 상대 `.html` 같은 새 링크 대상은 바깥 쪽(`inline.mjs` → `render.mjs` → `check.mjs`)에서 풀고, 뷰어(`viewer/`)는 바꿀 이유가 없다. 코드 확인 + 추론(실행 전).

## 2. `@facts`는 무엇인가 (그리고 `@fact`는?)

`@facts`는 "라벨 하나에 값 하나"를 나열하는 블록이다. 철자가 `@facts`(복수)이고, `@fact`는 `parse.mjs:179`의 `Unsupported component @fact.` 오류가 난다. 코드 확인.

```
@facts id=term-facts
| parent | 사용자와 대화하며 감사를 진행하는 메인 에이전트 |
```

- 행은 정확히 2칸(`rowWidth(rows,2,2)`, `parse.mjs`). 3칸 이상이면 오류다.
- 렌더는 `<dl><dt>라벨</dt><dd>값</dd></dl>`(`render.mjs:69`). 왼쪽 라벨은 회색 13px, 오른쪽 값은 14px 굵게, 행마다 가로선(`reader.css:150-154`).
- 쓸 곳: 서버 스펙·설정값처럼 "항목: 값"으로 읽는 정보. 선택표는 `explainer-authoring.md:60-77`.

### 2.1 `@facts`의 범위

`@` 줄 아래부터 **빈 줄, `#`·`##` 제목, 다음 `@` 줄이 나오기 전까지**의 `|` 행이 이 블록의 행이다(`parse.mjs:164`). 사용자의 `candidate.archify.md`에서는 `@facts id=relation-facts` 바로 아래 4행까지가 `@facts`이고, 빈 줄 뒤의 `| rel-id | 상대 | … |` 표는 `@facts` 밖이다. 코드 확인.

### 2.2 `@facts`가 없는 표와의 차이

`@` 없이 쓴 `|` 행 묶음은 일반 Markdown 표로 읽혀 `comparison` 블록이 된다(`parse.mjs:259-261`).

| | `@facts` | 일반 표(comparison) |
|---|---|---|
| 열 수 | 정확히 2 | 2 이상 |
| 헤더·구분행(`\| --- \|`) | 없음 | 필수. 없으면 오류 |
| HTML | `<dl>` | `<table>`, 행마다 `<th scope="row">` |
| 셀 평가 칩 | 없음 | 셀에 `{good}`·`{caution}`·`{bad}`를 붙이면 칩 |

표가 "알아서 렌더링되는 것처럼" 보이는 이유는 일반 표가 오류 없이 `comparison`으로 처리되기 때문이다. 코드 확인.

**미확인**: `@facts` 행의 값 칸에 `[](source:skm-fm)` 같은 인용 링크를 넣었을 때의 처리. 스크린샷에는 각주 번호가 붙어 나왔으므로 동작은 하는 것으로 보이나 `inline` 처리 코드는 읽지 않았다.

## 3. `## 제목 {#files span=12}`

| 부분 | 의미 | 근거 |
|---|---|---|
| `##` | 패널 하나의 시작. 번호 배지는 문서 안 순서(배열 위치+1)로 렌더 때 붙는다. 직접 쓰는 번호가 아니다 | `parse.mjs:239`, `render.mjs:105` |
| `{#files}` | 패널 id. 생략하면 제목 해시로 `panel-<12hex>`가 자동 생성된다. 직접 정하면 `[..](block:files)` 링크와 `patch explainer <html> files <교체파일> <out>`이 안정적으로 가리킨다 | `parse.mjs:88-89,239` |
| `span=12` | 12칸 그리드에서 이 패널이 차지할 폭(1~12). 12면 한 줄 전체, 6이면 반 줄 | `layout.mjs`, `explainer-authoring.md:254` |

`span`을 쓰면 자동 배치가 절대 바꾸지 않는다(`layout.mjs` 주석 "Explicit spans never change"). 가이드는 `span` 생략을 권한다(페이지가 내용을 재서 정한다). 코드 확인. 고정 폭 패널이 실제로 잘리거나 겹치는지는 렌더를 안 열어 **미확인**.

## 4. 단어 아래 점선 밑줄은 무엇인가

**본문·표의 단어가 같은 문서 다이어그램의 노드 이름과 같을 때 `reader.js`가 붙이는 연결 표시다.** Markdown 문법이 아니고 렌더 후 브라우저에서 붙는다. `linkTerms()`(`reader.js:407-445`), 스타일은 `reader.css:176`의 `.term`(점선 밑줄). 코드 확인.

**동작** (입력 → 내부 → 결과)
1. `.diagram-preview` 안의 `[data-node-id][data-node-label]`에서 노드 라벨과 노드 id를 모은다.
2. 라벨을 소문자로 바꿔 후보에 넣는다. 한자 라벨은 2글자 이상, 그 밖(영어·한글)은 3글자 이상이어야 한다(`\p{Script=Han}`로 구분).
3. 노드 id가 `[a-z]` 3글자 이상이면(예: `findings`, `critic`, `setup`) 영어 본문에서 그 노드를 가리키는 이름으로도 넣는다.
4. 각 패널의 본문 텍스트를 훑어 후보와 일치하는 단어를 `<span class="term" data-diagram data-node>`로 감싼다. 패널당 단어마다 첫 번째만. 코드(`code`, `pre`), 링크(`a`), 다이어그램 본문, `thead`는 건너뛴다.
5. 밑줄 단어에 마우스를 올리면 다이어그램의 그 노드가 강조되고, 노드에 올리면 단어 배경이 밝아진다(`reader.js:439-443`).

**사용자 문서에서 확인한 대응**(`candidate.archify.md` 100~109행의 `@workflow id=audit-flow`, 스크린샷 비교)

| 밑줄이 보인 단어 | 연결된 노드 | 이유 |
|---|---|---|
| 모드 판단?, 감사 설정, 범위 점검?, 후보 검증, 최종 검증, 보고서 | `mode`, `setup`, `critic`, `validate`, `final`, `report` | 라벨과 글자가 같음 |
| `findings.json`의 findings, `coverage critic`의 critic | `findings`, `critic` | 노드 id(영어 3글자 이상) |
| 정찰, 사냥에는 밑줄 없음 | `recon`, `hunt` | 한글 라벨이 2글자라 규칙에서 빠짐(규칙은 코드 확인, 스크린샷과의 대응은 추론) |

연결을 끄는 옵션은 찾지 못했다(**미확인**). 피하려면 노드 라벨·id를 바꾸는 수밖에 없어 보인다.

## 5. 설명(왼쪽)과 workflow 그림(오른쪽)은 어떻게 좌우로 놓이나

**두 단계**다.

1. **렌더 시 구조 결정**(`render.mjs:101-103`). 패널에 다이어그램이 정확히 1개 있고, `@steps`의 행 중 하나 이상이 그 다이어그램을 가리키면(`target.diagram === 그림 id`) "guided" 패널이 된다. HTML은 `panel-body.guided` 안에 `div.guide-figure`(그림)와 `div.guide-text`(나머지 블록)가 들어간다. 소스 주석: "text left, diagram right".
2. **CSS 배치**(`reader.css:221-224`). `.guided`는 `flex-flow: row-reverse wrap`이다. DOM 순서는 그림이 먼저지만 `row-reverse`라서 그림이 오른쪽에 놓인다. 그림은 필요한 폭만 차지하고 설명이 나머지(`flex: 1 1 320px`)를 쓴다. 스크롤해도 그림은 `position: sticky`로 화면에 남는다.

설명 쪽에 320px가 남지 않으면 그림이 설명 위로 올라가 위아래 배치가 된다. 화면 폭이 1255px 이하면 `reader.css:449`가 패널을 12칸 전체로 만든다. 코드 확인(CSS 주석 포함).

`@steps`에 다이어그램 id·노드 id를 비우면 연결 없는 순서 목록이 되어 좌우 배치도 일어나지 않을 것이다. **추론**(렌더 확인 안 함).

## 6. `@steps`는 native 다이어그램인가

**아니다. explainer 문서 안에서만 쓰는 블록이다.**

- native 다이어그램은 10개(`architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `class`, `tree`, `timeline`, `waterfall`, `parse.mjs:4`의 `TYPES`)이고 `steps`는 없다. `@steps`는 explainer 블록 13종 중 하나이고 `<ol class="steps">`로 렌더된다. 일반 `archify render`로는 `steps` 타입을 그릴 수 없다. 코드 확인.
- 역할은 그림을 그리는 것이 아니라 **단계 목록을 다이어그램 노드에 연결하는 것**이다. 연결된 단계가 2개 이상이면 단계를 하나씩 넘기며 노드를 따라가는 walk 버튼이 생긴다(`reader.js:474-483`). 항목에 마우스를 올리면 노드가 밝아진다(`reader.js:404`).

### 6.1 `@steps` 행의 칸과 id 세 가지

행 형식: `id | title | detail? | diagram-id? | node? | from~to? | edge-ids?`(`explainer-authoring.md`의 Directive reference). `candidate.archify.md` 123행으로 보면:

```
| s-mode | 모드 판단? | **입력** 사용자 요청 ... | audit-flow | mode |
   ①         ②             ③                      ④          ⑤
```

| 칸 | 값 | 정체 | 어디서 정해지나 |
|---|---|---|---|
| ① | `s-mode` | **단계 id**. HTML에서 `li#s-mode`가 되어 `[..](block:s-mode)` 링크 대상이 된다. 생략하면 자동 생성 | `@steps` 행 첫 칸 |
| ② | `모드 판단?` | 단계 제목 | `@steps` 행 둘째 칸 |
| ④ | `audit-flow` | **다이어그램 id**. 연결할 그림 | `@workflow id=audit-flow …`의 `id=` |
| ⑤ | `mode` | **노드 id**(화면 라벨이 아님) | `@workflow`의 노드 행 첫 칸, 예: `\| mode \| 모드 판단? \| external \| start \| … \|` |

`@workflow`의 선도 노드 id로 쓴다(`| mode > setup | 전체 감사 |`). 그래서 `s-mode`(단계)와 `mode`(노드)는 이름이 비슷할 뿐 별개이고, 연결은 ④⑤ 칸이 만든다. 코드 확인(`candidate.archify.md`와 문서 대조).

## 7. 정정과 남은 것

- 2026-11-17 대화에서 "`audit-flow`는 7번째 칸"이라고 한 것은 틀렸다. 4번째 칸이다.
- 같은 대화에서 explainer 링크 대상 해석을 `inline.mjs`에서 고친다고 한 것은 [next.md](../next.md) 5.6 기준이다. 바깥 `reader.js`가 `node:`·`route:` 링크를 `postMessage`로 안쪽에 넘기는 부분(위 1절)은 아직 끝까지 읽지 않았다. 상대 `.html` 링크를 추가할 때 바꿀 파일에 `reader.js`가 들어가는지는 **미확인**.
- 안쪽 다이어그램 HTML 본문과 `@facts` 행 안의 인용 링크 처리는 직접 열어 보지 않았다.
