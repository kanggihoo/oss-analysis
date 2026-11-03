---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/explainer/parse.mjs
  - archify/explainer/validate.mjs
  - archify/explainer/inline.mjs
  - archify/explainer/writing.mjs
  - archify/explainer/sources.mjs
  - archify/explainer/diagrams.mjs
  - archify/explainer/charts.mjs
  - archify/explainer/diff.mjs
  - archify/explainer/prepare.mjs
  - archify/explainer/revision.mjs
  - archify/explainer/layout.mjs
  - archify/explainer/render.mjs
  - archify/explainer/page-bundle.mjs
  - archify/explainer/check.mjs
  - archify/explainer/patch.mjs
  - archify/explainer/reader.js
  - archify/renderers/explainer/render-explainer.mjs
  - archify/schemas/explainer.schema.json
  - archify/schemas/common.schema.json
  - archify/bin/archify.mjs
  - archify/bin/finalize.mjs
  - archify/scripts/check-render-output.mjs
  - archify/references/explainer-authoring.md
depends: [delivery.md]    # delivery.md 는 다른 작업자가 작성 중이며 2026-11-02 현재 파일이 없다
status: ready            # 2026-11-02: 이 스펙 자체의 미결정 없음, 선행 스펙 ready
---

# explainer 경로 (Markdown 초안 → 검증된 단일 HTML 페이지, 패널 단위 수정)

> `.archify.md` 초안(또는 같은 모델의 JSON 초안) 하나를 받아, 문법·참조·근거·네이티브 다이어그램을 모두 동결·검증한 뒤 패널 id가 보존된 단일 HTML 페이지로 전달하고, 이후 패널 하나만 바꾸는 `patch explainer`와 독자의 Ask(클립보드 메시지)를 제공한다.

용어: **초안**은 작성자가 쓴 `.archify.md`, **bundle**은 `prepareExplainer`가 만드는 동결 묶음, **native 경로**는 feature map 행 5·6·7(JSON 입력 → 단일 렌더러)이다. 라이선스는 Apache-2.0이고(overview 1절) 이 스펙은 원본 코드를 줄 범위로 가리키기만 하며 복사하지 않았다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 에이전트가 초안을 쓰고 `finalize explainer <초안> <out.html>`(또는 `validate`/`deliver`)을 실행한다. 명령이 초안 바이트를 읽는다.
2. **prepare**(`prepareExplainer`)가 한 번에 다음을 한다. ① 파싱(`parseExplainer`), ② 스키마·의미 검증과 글쓰기 린트(`validateExplainer`), ③ 근거 해석·동결(`resolveExplainerSources`: Git 발췌, 이미지, 차트 데이터), ④ 본문 다이어그램마다 native 렌더러와 `check-render-output.mjs`를 자식 프로세스로 실행(`prepareExplainerDiagrams`), ⑤ 문장 속 `node:`/`route:` 링크와 steps 대상을 실제 렌더된 SVG 그래프에 대조(`validatePreparedTargets`). 결과가 bundle이다. 어느 단계든 오류가 하나라도 있으면 HTML은 만들어지지 않는다.
3. bundle을 `explainer.prepared.json`으로 staging(또는 임시) 디렉터리에 쓰고, `renderers/explainer/render-explainer.mjs`를 `ARCHIFY_EXPLAINER_PREPARED`와 함께 실행한다. 렌더러는 bundle이 원고 바이트·정규화 문서와 같은지 다시 확인한 뒤 `renderExplainer`로 HTML을 만든다.
4. 일반 `deliver` 규칙(staging 렌더 → 검사 → 쌍 교체 → provenance)은 선행 스펙 delivery.md를 따른다. explainer의 차이는 검사기가 `checkExplainerHtml`이라는 것, 교체 직전 동결 자원을 다시 확인한다는 것, provenance에 `explainer` 필드가 붙는다는 것이다(R-19).
5. `finalize`는 prepare를 한 번 하고 같은 bundle로 validate·deliver·check를 돌린다. native와 달리 **browser-check는 기본으로 하지 않는다**(`--browser-check`일 때만).
6. 독자가 페이지에서 Ask를 쓰면 페이지·파일·패널 id·인용문이 담긴 메시지가 클립보드로 복사된다. 에이전트는 그 패널 id로 `patch explainer`를 실행해 그 패널만 바꾼 새 HTML을 전달한다.

### 1.2 범위·통합 지점

- 제공: 초안 문법과 검증 진단, 근거 동결, 본문 안 native 다이어그램의 내장 렌더, 최종 HTML 구조, explainer 고유의 deliver·check·finalize 차이, `patch explainer`, reader의 Ask와 인용 버튼, 표시 언어 결정.
- 제외(이유): 같은 이름의 native 렌더러 내부(행 6), 일반 deliver 규칙·출력 경로 우선순위·원자 교체(delivery.md), `browser-check`의 측정 내용(행 8. 여기서는 기본 생략·실행 가능 여부·뷰포트 정책 이름만 다룸), reader의 보드 배치·다이어그램 Explore·내보내기·워크스루(행 11 후보, Ask만 범위), `vendor/pele`가 하는 Mermaid 차트 SVG 생성 내부, `reader.css`의 시각 디자인. 모두 이 스펙의 입력·출력 계약에는 필요하지 않다.
- 외부 의존·선행 계약: delivery.md의 `deliver`(staging, 쌍 교체, provenance, 실패 시 직전 파일 유지). 입력으로 필요한 로컬 환경은 `node`, 레포 근거를 쓸 때의 `git`과 일치하는 로컬 체크아웃(`--repo-root`), 이미지·차트 데이터·`source=` JSON이 놓일 초안 디렉터리다.
- 소유 상태·부작용: 이 기능이 만드는 것은 출력 HTML 하나와 deliver·finalize가 옆에 쓰는 사이드 파일(`<out>.delivery.json`, `<out>.finalize.json`, `<out>.finalize-summary.json`)이다. 초안과 입력 자원은 읽기만 한다. prepare의 임시 파일(`explainer.prepared.json`, 자식 렌더 디렉터리)은 명령이 끝나면 정리된다.

### 1.3 인터페이스와 데이터 의미

**명령** (외부 계약이므로 원문 이름)

| 연산 | 입력·출력 | 의미·제약 |
|---|---|---|
| `validate explainer <초안> [--quality standard\|showcase] [--repo-root 경로] [--writing warn\|strict\|off] [--json]` | 출력 파일 없음. 통과 시 rc 0과 `nextAction`(finalize 인자) | prepare + 임시 디렉터리 렌더 + 렌더 결과 check까지 수행한다. 실패 시 rc 1, `--json`이면 `{ok:false, stage, diagnostics}`. 품질 기본값은 초안 `@meta quality_profile`, 없으면 `standard` |
| `deliver explainer <초안> [out.html] [동일 옵션]` | HTML + provenance | 품질 기본값은 validate와 같다(`--quality` > 초안 `quality_profile` > `standard`) |
| `finalize explainer <초안> <out.html> [--browser-check] [동일 옵션] [--candidate-sha256 …] [--out-dir …] [--json]` | HTML + 사이드 파일 3개, 요약 JSON | 품질 기본값은 **`showcase`**이고 초안의 `quality_profile`보다 우선한다. `--browser-check`가 없으면 `gates.browser-check:"not-run"` |
| `check <html>` | 영수증 JSON | explainer HTML이면 `checkExplainerHtml`(R-21) |
| `patch explainer <artifact.html> <panel-id> <replacement-file> <output.html> [--json] [--quality …] [--repo-root …] [--writing …]` | HTML | 위치 인자 정확히 4개. 그 밖의 `--` 옵션은 `cli/usage`. 품질 기본값은 `--quality`, 없으면 원본 bundle의 `quality`, 없으면 `standard` |
| `preview explainer …` | 거부 | "Live preview supports the ten diagram types only" |
| `--writing`(validate·deliver·finalize·patch) | `warn`(기본) \| `strict` \| `off` | explainer가 아닌 타입에 쓰면 `cli/unsupported-option`. 값이 틀리거나 두 번 쓰면 `cli/invalid-arguments` |

**초안 형식**: 첫 비공백 문자가 `{` 또는 `[`이면 JSON(아래 정규 모델 그대로), 아니면 Markdown이다. Markdown 문법은 C-01~C-05, 인라인 문법은 C-07이 정본이다. 아래 표는 그 요약이다.

| 위치 | 문법 | 만들어지는 것 |
|---|---|---|
| 문서 시작 | `# 제목 {#id}` 하나 | `meta.title`, `meta.id`(생략 시 `explainer-<sha256(제목)[0:12]>`) |
| 제목 다음 첫 문단 | 평문 한 문단 | `answer.summary` |
| 그 바로 뒤 | 평평한 비순서 목록 | `answer.reasons`(스키마상 최대 4) |
| 첫 `##` 전(패널 뒤에서도 가능) | `@answer scope="…"` | `answer.scope` |
| 같은 곳 | `@meta locale=… quality_profile=… style=… repo_url=… repo_revision=… repo_provider=… repo_link_mode=…` | `meta.*`, `meta.repository` |
| 같은 곳 | `@source <id> title=… url=… path=… lines=시작:끝 revision=…` | `sources[]`(행 없음) |
| 패널 | `## 질문 {#id span=1..12}` | `panels[]`. id 생략 시 `panel-<sha256(제목)[0:12]>` |
| 패널 안 | 평문 문단 / 목록 / 표 / 펜스 / `@지시문` | 블록. 블록 id 생략 시 `<type>-<sha256(패널id, 블록 JSON)[0:12]>`(내용이 바뀌면 id도 바뀜) |

지시문별 허용 인자(`parse.mjs:175-178`이 정본)와 행 모양:

| 지시문 | 인자 | 행(`\|`로 나눈 셀, 위치 고정) |
|---|---|---|
| `@prose` | id, text | 셀 1개 |
| `@list` | id, ordered | 셀 1개 |
| `@callout` | id, level(`note`\|`warning`\|`open-question`, 기본 note), title, text | 셀 1개. 행이 없고 `text=`도 없으면 바로 뒤 평문 문단이 본문 |
| `@facts` | id | 셀 2개 `key \| value` |
| `@metric` | id, label, value, limit, unit, note, typical | 행 금지 |
| `@steps` | id | 셀 2~7개 `id \| 제목 \| 설명? \| 다이어그램id? \| 노드? \| from~to? \| 엣지id,…?` (5번째 칸에 `~`가 있고 6번째가 비면 경로로 취급) |
| `@<native타입>` 또는 `@diagram <타입>` | id, title, changes(`대상:added\|removed\|modified,…`), (`@diagram`만) source, spec | 약식 행(C-11). `source:<id>` 셀이 있으면 그 노드에 근거 연결 |
| `@code` | id, source, language | 행 금지. 근거가 `path`와 `lines`를 가진 `@source`여야 함 |
| `@diff` | id, caption | 바로 뒤 ```` ```diff ```` 펜스(또는 행) |
| `@image` | id, path, alt, caption | 행 금지 |
| `@chart` | id, title, type(`bar`\|`line`\|`pie`), data(`.csv`/`.json`), x, y(쉼표), unit | 행 금지 |
| `@comparison` | id, columns, label | 셀 2개 이상. 일반 Markdown 표가 더 흔한 입력 |
| 표 | 헤더·구분선(`---` 3개 이상)·행 | 첫 헤더 칸이 행 라벨 열 이름. 셀 끝 `{good\|caution\|bad[:라벨]}`, 행 라벨 끝 `{#행id}` |
| 목록 | `- 항목`, `1. 항목`, `- [ ] 항목` | 체크리스트는 한 목록 전체가 `- [ ]`여야 함 |
| 펜스 | ```` ```언어 title="…" ```` | 언어 `diff` → diff 블록, `mermaid` → chart 블록(text), 그 외 → snippet |

**정규 문서 모델(JSON)**: `{schema_version:1, diagram_type:"explainer", meta:{id,title,output?,locale?,quality_profile?,style?,repository?}, answer:{summary,reasons?,scope?}, panels:[{id,title,span?,blocks[]}], sources:[{id,title,url?,path?,lines?,revision?}]}`. 블록 종류는 `prose, list, callout, comparison, facts, metric, steps, diagram, code, snippet, chart, diff, image` 13개다(C-08). 정규 모델은 사용자가 직접 쓸 수도 있고(JSON 초안), Markdown 파서는 같은 모델과 source map(포인터 → 줄·열·오프셋)을 만든다.

**한도** (스키마·상수. 숫자 이름은 C-08, C-13)

| 대상 | 한도 |
|---|---|
| 초안 | 16 MiB (`explainer/source-limit`). bundle 64 MiB (`explainer/resource-limit`) |
| 패널 수 | 1~500. 패널당 블록 1~500. `sources` 0~500 |
| `answer.reasons` | 0~4개 |
| 문자열 | 본문류(`text`) 1~20000자, 제목·라벨류(`short`) 1~500자, id는 `^[A-Za-z][A-Za-z0-9_-]*$` 100자 이하 |
| 목록 항목, 표 열·행·셀, steps 항목, `changes`, `nodeSources` | 각 500 이하(`minItems` 1) |
| `span` | 정수 1~12 |
| 데이터 차트 | `y` 1~6열, 행 60개(pie는 12), 데이터 파일 2 MiB |
| 이미지 | 장당 8 MiB, 문서 합계 32 MiB, PNG/JPEG/WebP/GIF만 |
| 코드·근거 파일 | 16 MiB, UTF-8 텍스트, NUL·비밀 패턴 없음 |
| native 다이어그램 | 입력 JSON 4 MiB, 결과 HTML 32 MiB, 자식 프로세스 타임아웃 120000 ms |
| 약식 다이어그램 | architecture 최대 12열, workflow 열 0~5·lane당 노드 6개 이하, 약식은 6종(sequence, architecture, workflow, tree, timeline, erd)만 |
| 본문 안 다이어그램 개수 | 코드에 상한 없음(문서는 "최대 4개"라고 씀. 2.1 참고) |

**진단 객체**(공유 계약 "진단 객체"를 따름): `{code:"explainer/…", severity, message, subject:{line, column, component, path(JSON 포인터), panelId?, input?}, evidence:{reason, example}, supportedFixes[]}`. 줄은 원본 초안 기준이다(JSON 초안도 값의 위치를 보존).

**bundle 필드**(`prepareExplainer`가 반환, 디스크에는 `explainer.prepared.json`): `schemaVersion:1, kind:"archify-explainer-prepared", document, sourceMap, format("markdown"\|"json"), sourceText, diagnostics(경고만 남음), sourcePath, baseDir, quality, writingMode, source:{sha256,bytes}, preparedSources:{sources, assets, charts?, repository?}, preparedDiagrams:{diagrams}, dependencies[], digest`. `digest`는 `digest` 필드를 뺀 JSON의 sha256이다. 동결 자원은 `contentBase64`로 바이트를 싣고 `{kind: repository\|image\|data\|diagram-spec, id, sha256, bytes}`로 식별된다. deliver provenance와 manifest에는 `contentBase64`가 빠진다.

**최종 HTML 구조**(C-16, R-22): `<html lang data-style data-archify-artifact="explainer" data-artifact="<meta.id>" data-revision="<revision>">` 아래 `.shell` > `header.masthead`(h1 제목, 테마·스타일·내보내기 도구) · `main#board > .board` · `footer`(typical 주석, 출처 목록, colophon) · `dialog#diagram-dialog` · `#toast`. 결론은 `section#answer.panel.answer-panel`, 각 패널은 `section.panel#<panel.id>`(번호 배지는 배열 위치+1), 블록은 `div.block.block-<type>#<block.id>`, 표 행은 `tr#<row.id>`, steps 항목은 `li#<item.id>`, 출처는 `li#source-<id>`다. 스크립트는 JSON 3개(`archify-explainer-prepared`, `explainer-manifest`, `explainer-reader-words`), head의 소프트웨어 고지 JSON(`archify-software-notices`), 인라인 reader JS 하나이며 외부 자원이 없다.

**Ask 메시지**(reader.js, R-26~28): 줄 순서는 `Page`, `File`, `Where`, (`Quote`), `Question`, (패널일 때만) 패치 안내 한 줄이다. 라벨 단어는 `explainer-reader-words`의 `askPage/askFile/askWhere/askQuoteLabel/askQuestion/askPatch`를 쓴다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 초안을 읽음 | 첫 비공백 문자가 `{`/`[`면 JSON, 아니면 Markdown. JSON 초안도 같은 검증을 통과해 같은 HTML이 된다. 입력이 올바른 UTF-8이 아니면 `explainer/source-encoding`, 16 MiB 초과면 `explainer/source-limit`. 파싱 오류가 하나라도 있으면 `document:null`이고 일부만 전달되는 일은 없다 | 실행 확인(Markdown·JSON 통과: `in/ok.archify.md`, `in/ok-json.archify.md`). 인코딩·크기 분기는 코드 확인 |
| R-02 | Markdown 문서 구조 | 제목 `# …` 정확히 하나가 첫 패널 전에 필요하고(`parse-title`, 제목 뒤 두 번째 `#`는 `parse-heading`), 제목 다음 평문 한 문단이 답이다(없으면 `parse-answer`, 두 문단이면 `parse-answer`). 패널은 1개 이상(`parse-panel`). 패널 앞에 블록이 오면 `parse-<블록종류>`("Blocks must follow a question panel heading"). 이유 목록은 비순서·평평해야 한다(`parse-answer`) | 실행 확인(b03, b04, b05, c09, c10, c11, c12) |
| R-03 | `@지시문 key=value …` | 알 수 없는 지시문은 `parse-directive`("Unsupported component @foo"), 알 수 없는 인자는 `parse-<종류>`, 중복 키·닫히지 않은 따옴표·공백 없이 붙은 인자는 `parse-directive`, 행 셀 수가 맞지 않으면 `parse-<종류>`(C-02, C-03). `@answer`·`@meta`에 행을 붙이면 `parse-answer`/`parse-meta`. 값 따옴표는 `"…"`/`'…'`와 `\` 이스케이프. 행의 `\|`는 파이프 문자, 백틱 안의 `\|`는 구분자가 아님 | 실행 확인(b01, b02, c07, c08, c13). 나머지는 코드 확인 |
| R-04 | 표·목록·펜스·산문 | 표는 헤더+구분선+데이터 행 1개 이상이고 모든 행이 헤더 너비와 같아야 한다(`parse-comparison`). 체크리스트는 목록 전체가 `- [ ]`(`parse-list`). 중첩 목록, 인용(`>`), `###` 이상 제목, 가로줄, 목록·산문 안의 펜스는 `parse-list`/`parse-prose`("outside the restricted author grammar"). 펜스는 닫혀야 하고 내용이 있어야 한다(`parse-snippet`). `@diff`의 ```` ```diff ```` 펜스가 닫히지 않으면 `parse-diff` | 실행 확인(b09, b10, b20, b25). 펜스 분기는 코드 확인 |
| R-05 | id | 패널·블록·steps 항목·표 행은 하나의 id 이름공간이다. 형식 위반은 `parse-<컴포넌트>`, 중복은 파싱 단계에서 `parse-<컴포넌트>`(메시지에 먼저 쓴 줄을 적음), 출처 id 중복과 JSON 경로의 중복은 `explainer/duplicate-id`. `answer`, `explainer-` 접두, `board`, `diagram-dialog`, `diagram-dialog-title`, `toast`는 예약(`reserved-id`), 출처 id `x`가 있으면 `source-x`도 예약. 블록 id가 자기 패널 id와 같으면(다이어그램 제외) `<패널id>-<종류>`로 바뀐다 | 실행 확인(b06, b11, b24, c29). 개명 규칙은 코드 확인 |
| R-06 | 인라인 언어 | 지원: `**굵게**`, `*기울임*`, `` `코드` ``, `[라벨](대상)`. 대상은 `http(s)://`(자격증명 없음), `source:id`, `block:id` 또는 `#id`, `node:다이어그램.노드`, `route:다이어그램.from~to`, `typical:설명`뿐이다. 원시 HTML, `![]()`, `~~`, `[^1]`, 닫히지 않은 코드·강조·링크는 각각 `explainer/inline-html\|image\|decoration\|footnote\|code\|emphasis\|link\|target` 오류다. `[](source:id)`처럼 라벨이 빈 링크는 source 대상만 허용 | 실행 확인(c01~c06). 나머지는 코드 확인 |
| R-07 | 스키마 | `validateExplainer`가 정규 모델을 생성된 검증기로 검사하고, 오류마다 `explainer/schema-<keyword>`(`required`, `additionalProperties`, `type`, `const`, `enum`, `oneOf`, `minimum`, `exclusiveMinimum`, `maximum`, `pattern`, `minItems`, `maxItems`, `minLength` 등)를 낸다. 스키마 오류가 있으면 의미 검증으로 넘어가지 않는다. 예: 이유 5개 → `schema-maxItems`, 빈 패널 → `schema-minItems`, `level=danger` → `schema-enum`, `locale=KOREAN` → `schema-pattern`(`^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`) | 실행 확인(b08, b22, b23, c15, c25, c31) |
| R-08 | 의미 검증 | 존재하지 않는 `source:`·`block:`·`@code source=`·`nodeSources`·steps 엣지 → `unresolved-reference`. 같은 참조 반복 → `duplicate-reference`. 노드와 경로를 동시에 지정 → `diagram-target-exclusive`. 초안에 인라인된 `spec`에서 노드/경로 끝점이 없으면 `diagram-node`/`diagram-route`. `source.lines`가 역순 → `source-lines`, `url`이 http(s)·자격증명 없음이 아님 → `source-url`. `@code`의 근거에 `path`가 없으면 `code-source-kind`. 표 행 셀 수 불일치 → `table-width`. 차트가 text와 data를 둘 다/둘 다 안 가짐 → `chart`. 다이어그램 `spec.diagram_type`이 선언과 다르면 `diagram-type`, 네이티브 스키마 위반은 `native-<네이티브 code>`(예: `explainer/native-schema/required`). diff 형식 오류는 `diff-combined\|binary\|header\|hunk-header\|hunk-range\|hunk-count\|header-order\|newline-marker\|row\|empty\|secret`. 선언만 하고 인용하지 않은 출처는 오류가 아니다 | 실행 확인(b07, b12, b18, b19, c16, c17, c20, c23, c24, c26~c29). 나머지는 코드 확인 |
| R-09 | 약식 다이어그램 행(`@sequence` 등) | C-11이 정본. 요약: 6종만 지원하고 `dataflow`·`lifecycle`·`class`·`waterfall`은 `diagram-shorthand-unsupported`이며 `@diagram <타입> source=파일.json`이 필요. 행 셀 수가 틀리면 `diagram-row`, 한 타입에 id 중복은 `diagram-id-duplicate`/`diagram-actor-collision`, 한도 초과는 `diagram-shorthand-limit`. 약식은 스펙에 `meta.title`(없으면 패널 제목), 품질 프로파일을 넣고 workflow는 `schema_version` 2, 나머지는 1로 만든 뒤 네이티브 `validateSchema`를 거친다 | 실행 확인(b13, b21). 나머지는 코드 확인 |
| R-10 | 글쓰기 린트 | 본문·답·표·목록 등 산문 필드에 C-10 규칙을 적용한다. 규칙 id: `qualification, light-verb, cliche, filler, vague-quantity, number-boundary, plain-word, redundancy, scope-length, verdict-emphasis, paragraph-length, de-chain, sentence-length`. 코드는 `explainer/writing-<규칙>`. 기본 `warn`은 경고(통과, 영수증·JSON 진단에 남음), `strict`는 같은 항목이 오류, `off`는 검사 생략. 숫자: 한 문장 한자 포함이면 50단위, 아니면 영어 28단위 초과(`sentence-length`), 산문 문단 120단위 초과 또는 4문장 초과(`paragraph-length`), `@answer scope` 50단위 초과(`scope-length`), 요약의 굵게 비율이 60% 초과이고 12단위 이상(`verdict-emphasis`), 한 문장 `的` 3회 이상(`de-chain`). 단위는 한자 글자 수 + 라틴·숫자 단어 수. 코드·URL은 제외 | 실행 확인(d01 경고 34단위/한도 28, `--writing strict`→오류 rc 1, `off`→진단 없음, d02 규칙 3종). 나머지 규칙·한도는 코드 확인 |
| R-11 | 근거 해석(`@code`, Git 발췌) | `@code`가 쓰는 `@source`는 `path`와 `lines`가 있어야 한다(`code-source`). 레포 위치는 `@meta repo_url/repo_revision`이 있으면 그것을, 없으면 `--repo-root`의 `git remote get-url origin`과 `HEAD`를 쓴다(`--repo-root` 없으면 `repository-root`, origin 해석 불가 `repository-origin`). 소스 `revision`이 있으면 문서 리비전과 같아야 한다(`source-revision`). 파일·줄 범위는 `verifyRepositoryEvidence`(native와 같은 함수)로 확인하고 실패하면 `repository-location`. 발췌는 **작업트리가 아니라 `git show <rev>:<path>`** 바이트에서 줄 범위를 잘라 동결하며, UTF-8 텍스트이고 NUL·비밀 패턴이 없어야 한다(`source-encoding`, `secret-content`). 경로는 상대·`..`/`.git`/인코딩 불가 문자 금지(`source-path`), 비밀 파일명 클래스(`.env`, 키·자격증명 파일 등)는 `secret-path` | 실행 확인(b14: root 없음→`repository-root`, `--repo-root`로 통과, b15 `repository-location`, b17 `secret-path`). 비밀 내용·인코딩 분기는 코드 확인 |
| R-12 | 근거 해석(인용만 한 레포 근거) | `@code`가 쓰지 않는 `@source path=… lines=…`는 `--repo-root`가 있고 검증되면 발췌를 얻어 reader 카드에 싣지만, 검증이 실패하거나 읽을 수 없으면 **오류 없이 평문 참조로 남는다**. native 경로(`meta.repository`가 있으면 줄 범위·파일 존재 오류, q2 참조)와 다르고, `@code`와도 다르다. 어느 쪽이든 인용한 줄의 내용이 주장과 맞는지는 확인하지 않는다 | 실행 확인(`in/cite-bad-lines.archify.md`: `lines=1:99999` 인용이 finalize 통과, bundle의 해당 source에 `text` 없음, 의존성 0) |
| R-13 | 이미지·차트 데이터 | `@image`는 초안 디렉터리 안의 일반 파일이어야 한다(상대 경로, 심볼릭 링크·`..` 금지, 읽는 동안 변경되면 `asset-changed`). 확장자와 바이트 시그니처가 같은 PNG/JPEG/GIF/WebP만, 장당 8 MiB, 합계 32 MiB(`asset-budget`). 읽을 수 없으면 `asset-read`. 결과는 `data:` URL로 HTML에 들어가고 외부 이미지 참조는 `check`가 거부한다. `@chart data=`는 `.csv`/`.json`을 2 MiB 이내로 읽어 Mermaid 차트 텍스트로 바꾼다(빈 값은 0이 아니라 오류, `chart-data`). 펜스 ```` ```mermaid ````는 pie, xychart-beta, quadrantChart, sankey-beta, radar-beta, venn-beta만 허용하고 flowchart·sequence 등은 "native shorthand를 쓰라"는 `explainer/chart` 오류 | 실행 확인(b16 `asset-read`, c17, c18). 나머지는 코드 확인 |
| R-14 | 본문 안 native 다이어그램의 내장 렌더 | 다이어그램 블록마다: ① 약식 행이면 spec으로 컴파일, `source=`면 초안 디렉터리의 `.json`을 안전하게 읽어(심볼릭 링크·`..`·4 MiB 초과 거부) 바이트를 동결, ② `spec.diagram_type`이 블록 타입과 같은지 확인, ③ spec의 `meta.output`을 `diagram.html`로, `meta.quality_profile`을 문서 품질로 덮고(인라인 spec은 `locale`이 없을 때 문서 `locale` 상속) `validateSchema`, ④ 임시 디렉터리에서 **`node renderers/<타입>/render-<타입>.mjs <in.json> <out.html>`**(env `ARCHIFY_QUALITY_PROFILE`, `ARCHIFY_REPO_ROOT`, `ARCHIFY_DIAGNOSTIC_FORMAT=json`)을 실행, ⑤ **`node scripts/check-render-output.mjs <out.html>`**을 실행해 영수증 `ok`를 확인, ⑥ HTML의 `data-quality-profile`이 있는 `<svg>` 하나를 정적 미리보기로 쓰고 `data-node-id`/`data-edge-*`에서 노드·엣지 목록(semantic)을 추출, `changes`로 `data-explainer-change`를 표시. 자식에 대한 browser-check는 하지 않는다. 자식 실패는 `explainer/diagram-render`·`diagram-check`·`diagram-schema` 등으로 줄 번호와 함께 보고된다 | 코드 확인. 정상 경로는 실행 확인(bundle에 `diagrams.miss-flow.checks.{validate,render,check}`, 검증 JSON의 `explainer_native_diagrams: miss-flow: pass`) |
| R-15 | 참조 대상 검증 | prepare 마지막에 모든 `node:`/`route:` 링크와 steps `target`을 **렌더된 SVG의 노드·엣지**에 대조한다. 노드 없음 `diagram-node-reference`, 엣지 id 없음 `diagram-edge-reference`, 경로는 두 끝점이 실제 노드이고 **방향 있는 엣지로 도달 가능**해야 한다(`diagram-route-reference`) | 실행 확인(c19: `route:sq.b~a`, 엣지는 a→b뿐 → `diagram-route-reference`) |
| R-16 | prepare 출력과 동결 | bundle(1.3)을 만든다. 동결 의존: 레포 발췌(`repository`), 이미지(`image`), 차트 데이터(`data`), 다이어그램 입력(`diagram-spec`, 인라인이면 `inline:true`). 로컬 파일 의존은 `assertPreparedDependencies`가 sha256·바이트를 다시 확인해 준비 도중 변경되면 `dependency-changed`. 렌더러·검사 쪽이 bundle을 읽을 때(`readPreparedBundle`)는 경로·digest·원고 바이트·품질·writing 모드·정규화 문서가 모두 같아야 하며 다르면 `prepared-mismatch`/`prepared-invalid` | 코드 확인. `explainer.deliver` 영수증의 `explainer.dependencies`는 실행 확인(`repository:router`, `diagram-spec:miss-flow`) |
| R-17 | 품질 프로파일 | `validate`·`deliver`: 인자 `--quality` > 초안 `@meta quality_profile` > `standard`. `finalize`: 인자 > **`showcase`**(초안 값 무시). `patch`: 인자 > 원본 bundle의 `quality` > `standard`. 값은 `standard`\|`showcase`만. 품질은 native 자식 렌더·검사에 전달된다 | 실행 확인(`@meta quality_profile=standard` 초안: finalize 결과 bundle `quality:showcase`, deliver `standard`) |
| R-18 | `validate explainer` | prepare → 임시 디렉터리에서 렌더 → 렌더 결과에 `check-render-output.mjs`까지 수행하고 파일은 남기지 않는다. 오류는 `stage:"render"`(prepare 실패 포함)로 보고되고 rc 1이다. 성공 JSON의 `checks`는 `explainer_structure`, `explainer_payload_identity`, `explainer_dependencies`, `explainer_native_diagrams`이고 `nextAction`이 `finalize` 호출 인자를 `--candidate-sha256`과 함께 제시한다 | 실행 확인(ok.validate.json) |
| R-19 | `deliver explainer`의 native와 다른 점 | ① prepare를 렌더 전에 CLI 프로세스에서 하고 bundle을 staging에 `explainer.prepared.json`으로 동결해 렌더러에 `ARCHIFY_EXPLAINER_PREPARED`(+`ARCHIFY_EXPLAINER_SNAPSHOT_INPUT`, `ARCHIFY_EXPLAINER_PAGE_DIR`)로 넘긴다. native는 렌더러가 JSON을 직접 읽는다. ② 렌더러는 `renderers/explainer/render-explainer.mjs`이고 출력 기본 이름은 `explainer.html`이다. ③ 검사는 `check-render-output.mjs`가 explainer HTML을 감지해 `checkExplainerHtml`로 분기한다(SVG 정적 검사 아님). ④ 쌍 교체 직전에 `assertPreparedDependencies`를 한 번 더 호출한다. ⑤ provenance(`*.delivery.json`)에 `explainer:{preparedSha256, dependencies[{kind,id,path?,revision?,sha256,bytes}]}`가 추가된다. ⑥ 출력 이름: Markdown 초안에는 `meta.output`을 쓸 지시문이 없어 명령행 출력 경로가 쓰이고(없으면 `explainer.html`), JSON 초안만 `meta.output`을 쓸 수 있으며 있으면 `validateAuthoredOutputPath`를 통과해야 한다. 그 밖의 staging·교체·실패 시 직전 파일 유지·출력 경로 우선순위는 delivery.md | 코드 확인. provenance 필드는 실행 확인(`out/deliver/ok.delivery.json`) |
| R-20 | `finalize explainer` | 초안을 한 번 prepare(품질 R-17)하고 bundle을 임시 디렉터리에 동결한 뒤 `runFinalize`가 validate·deliver·check를 순서대로 돌린다. `needsBrowser = type!=='explainer' \|\| browserCheck`이므로 기본은 browser-check를 하지 않고 영수증은 `gates.browser-check:"not-run"`, `browserCheck:{requested:false,ran:false}`, `visualReview:"not-requested"`. `--browser-check`를 주면 Chrome으로 1280·1440 폭 × light·dark 뷰포트(`explainer-desktop-v1`)를 검사한다. prepare 단계에서 실패하면 영수증 파일 없이 stdout에 `{ok:false, gates:{전부 "not-run"}, diagnostics}`를 내고 rc 1, HTML도 만들지 않는다. 경고만 있으면 통과하고 진단이 영수증에 남는다. 일반 finalize 규칙(단계 순서, 영수증, 후보 해시)은 행 4 | 실행 확인(기본 통과, 실패 시 gates 전부 not-run, `--browser-check` 통과 시 `browser-check:"pass"`). 측정 내용은 확인 한계 |
| R-21 | `check`(explainer HTML) | HTML이 `data-archify-artifact="explainer"`이거나 `archify-explainer-prepared` 스크립트를 가지면 explainer로 분기한다. 검사 4종: `explainer_structure`(DOM id 중복, `on*` 핸들러, 외부 `script src`, `iframe/object/embed`, `javascript:` URL, 외부 이미지, 해결 안 되는 `#앵커`), `explainer_payload_identity`(payload JSON 3개 존재·이스케이프, bundle digest, 원고 sha, 임베드 초안 재파싱 = 문서, manifest의 문서 해시·리비전·id, 모든 패널·블록·출처 id가 DOM에 존재), `explainer_dependencies`(매니페스트와 동결 자원의 해시·바이트·바인딩), `explainer_native_diagrams`(자식 HTML 해시, 중첩 explainer 금지, 각 자식에 native 검사 재실행). **보이는 본문 텍스트가 임베드 초안과 같은지는 보지 않는다** | 실행 확인(본문만 직접 고친 사본은 `check` 통과, 임베드 초안까지 고친 사본은 `bundle-hash, bundle-source-hash, source-hash, content-revision, document-hash`로 실패) |
| R-22 | 최종 HTML | 1.3의 구조. 모든 패널·블록 id와 `source-<id>`가 DOM id로 보존된다(`check`가 강제). 레이아웃은 결론을 5칸으로 두고 패널을 12칸 보드에 순서대로 채우며(`layoutExplainerPanels`) 명시한 `span`은 바뀌지 않는다. native 자식 HTML은 gzip+base64(`htmlGzip`)로 payload에 들어가 독자가 Explore를 열 때 풀린다. 출처 번호는 본문 첫 인용 순이고 인용 안 된 출처는 선언 순으로 뒤에 붙는다. `data-revision`은 초안·정규 문서·동결 자원·자식 해시로 계산되는 `computeExplainerRevision`이고 파일 위치에는 의존하지 않는다 | 실행 확인(ok.html의 id 집합, script id 4종(소프트웨어 고지 포함), `html lang`). 레이아웃 수치는 코드 확인 |
| R-23 | `patch explainer` 성공 경로 | ① 원본을 `check`로 먼저 검사(실패하면 그 진단 또는 `patch-artifact`), 검사한 바이트가 이후 바뀌면 `patch-artifact-changed`. ② 페이지의 `archify-explainer-prepared`가 정확히 하나여야 하고(`patch-payload`) gzip을 풀어 digest·원고 해시·정규 문서를 다시 맞춘다. ③ 문서의 `panels`에서 id가 `panel-id`인 패널을 찾는다. ④ 그 패널의 원고 구간(`##` 줄 시작~다음 `##` 줄 시작 또는 파일 끝, 그 사이의 지시문·빈 줄 포함)을 교체 파일 내용으로 바꾼 새 원고를 만든다. ⑤ 새 원고 전체를 다시 파싱·검증(writing 모드는 인자 > 원본 값 > `warn`)하고 바뀐 블록만 다시 준비한다. 안 바뀐 다이어그램(`source=` 포함)·이미 동결한 코드 발췌·경로가 같은 이미지·같은 data 차트는 원본에 동결된 바이트를 재사용하므로 원래 파일이나 체크아웃이 없어도 된다. 품질이 바뀌면 모든 다이어그램을 다시 검증한다. ⑥ 새 원고를 임시 파일(`patched-draft.json`이라는 이름이지만 내용은 새 원고)에 쓰고 `deliver explainer <임시> <output> --quality … --writing …`을 prepared bundle과 함께 실행한다. ⑦ 결과 영수증 = deliver 영수증 + `{command:"patch", panelId, original:{path,revision,sourceSha256}, replacement:{path}, revision, sourceSha256}`. finalize 영수증과 browser-check는 만들지 않는다 | 실행 확인(p1-good: 3열 표로 교체, 다른 패널·다이어그램 sha 동일, 새 `revision`≠원본, 원본 파일은 그대로) |
| R-24 | `patch explainer`가 거부하는 변경 | 존재하지 않는 id, `answer` 포함 → `patch-target`. 교체 후 패널 수가 달라지거나(교체 파일에 `##`가 둘, 마지막 줄 끝 개행이 없어 다음 `##`가 붙음) 같은 위치 패널의 id가 바뀌거나(id 없는 제목은 해시 id가 되어 달라짐) → `patch-identity`. 패널 밖 정규 문서가 조금이라도 달라지면(예: 교체 구간에 `@source` 추가는 실행 확인, `@answer`·`@meta` 지시문을 넣는 경우는 코드상 같은 경로) → `patch-scope`. 새 원고가 일반 규칙을 어기면(없는 지시문, 다른 블록과 id 중복) 그 진단을 **새 원고 전체 기준 줄 번호**로 낸다. 임베드 payload가 없는 HTML(예: native 다이어그램 페이지) → `patch-payload`. 교체 파일이 UTF-8이 아니면 `patch-source-encoding`. 모든 거부에서 출력 파일은 만들어지지 않는다 | 실행 확인(p2~p10, `out/patch2` b). `@answer`·`@meta` 포함 교체는 미실행 |
| R-25 | `patch` 부수 규칙 | 명시 `id`가 없는 블록의 id는 내용 해시라 패치로 내용이 바뀌면 id가 바뀐다(표 `comparison-a5e7…` → `comparison-739f…`). 그 블록을 가리키는 링크가 필요하면 `id=`를 줘야 한다. 출력이 원본과 같은 경로여도 되고(제자리 덮어쓰기) 연쇄 패치도 된다. 화면에서 HTML 본문만 손으로 고친 파일은 `check`를 통과하고, patch는 임베드 초안에서 다시 렌더하므로 그 손 수정은 사라진다. `--repo-root` 없이도 바뀐 블록이 새 레포 발췌를 요구하지 않으면 성공 | 실행 확인(p1, `out/patch2` a·c·d·e) |
| R-26 | Ask 열기·인용 | 모든 `.panel`(결론 포함)의 머리에 Ask 버튼이 붙고 누르면 다이얼로그가 열린다. 본문 일부를 선택하면 공백을 하나로 줄인 텍스트가 **2자 이상**일 때만 떠 있는 "Ask about this" 버튼이 나타나고, 눌렀을 때 쓰이는 인용문은 **앞 400자**로 잘린다(UTF-16 단위). 선택이 패널 밖이거나 다이얼로그가 열려 있으면 버튼은 숨는다. 칩(제안 질문)은 누르면 입력 칸에 한 줄 추가되고 다시 누르면 빠진다. 이미지 내보내기용 복제본에서는 Ask 요소가 제거된다(reader.js:263) | 코드 확인(브라우저 실행 없음) |
| R-27 | Ask 메시지 형식 | 제출(버튼 또는 Cmd/Ctrl+Enter)하면 다음 줄들을 `\n`으로 이어 복사한다. `Page: "<h1 텍스트>"`, `File: <file: 페이지면 경로(디코딩), 아니면 해시 뺀 URL>`, `Where: Panel <번호> "<제목>" (ID: <panel.id>)`(결론이면 `Where: Answer`로 id 없음), 인용이 있으면 `Quote: "<인용>"`, `Question: <입력 내용, 비었으면 첫 칩 문구>`, 패널일 때만 마지막에 "Revise only this panel with Archify panel replacement (patch explainer), keeping its ID." 영어면 `": "`와 `"…"`, 중국어면 `：`와 `「…」`와 `面板 <번호>「제목」（ID: …）`를 쓴다. 이 메시지의 패널 id가 `patch explainer`의 `<panel-id>`다 | 코드 확인(reader.js:555-566). 실제 클립보드 내용은 확인 한계 |
| R-28 | Ask 클립보드 실패 | `navigator.clipboard?.writeText(text)`가 **거부(reject)**되면 다이얼로그를 닫지 않고 입력 칸 내용을 메시지 전체로 바꾸고 선택해 사용자가 수동 복사하게 한다. 코드 블록의 복사 버튼은 거부 시 "Copy failed."(중국어 "复制失败。") 토스트만 띄운다. `navigator.clipboard`가 **없으면**(비보안 컨텍스트 등) `writeText`가 호출되지 않고 `undefined`가 `Promise.resolve`로 성공 처리되어, 복사가 안 됐는데도 다이얼로그가 닫히고 "복사됨" 토스트가 나온다(코드가 그렇게 읽힌다) | 코드 확인(reader.js:568). 위 마지막 문장의 실제 브라우저 동작은 추론 |
| R-29 | 표시 언어와 Ask UI 문구 | HTML의 `lang`은 `@meta locale`, 없으면 `zh-CN`이다. 컨트롤·Ask·출처 제목 등 모든 UI 문구는 **`en`과 `zh` 사전 두 개뿐**이고, `locale`이 `zh`로 시작하면 중국어, **그 밖의 모든 값(`ko` 포함)은 영어**를 쓴다(`render.mjs:39-42`의 `english = !locale.startsWith('zh')`, reader.js:8도 같은 판정). 그래서 `@meta locale=ko`여도 Ask UI(Ask, Copy question, Panel …)와 메시지 라벨은 영어이고, `@meta`를 쓰지 않은 한국어 초안은 `lang="zh-CN"`이라 중국어 UI가 나온다. 한국어 사전은 없고 본문은 작성자 문장 그대로다. 초안(Markdown)에 대한 locale 경고는 없다(`specificationLocaleDiagnostics`가 JSON 입력만 읽음) | 실행 확인(`out/deliver/loc-{ko,en,zh-CN,none}.html`의 `explainer-reader-words`: ko→`ask=Ask`, none→`lang=zh-CN`, `ask=追问`) + 코드 확인(원인) |

- 불변식: 같은 초안·같은 근거 바이트·같은 옵션이면 prepare가 만드는 정규 문서와 id는 같다(자동 id는 내용 해시). 렌더러는 bundle의 원고 바이트와 다른 입력은 거부한다. 출력 HTML의 모든 패널·블록 id는 정규 문서의 id와 일치한다(check가 강제).
- 미결정: 없음. (선행 스펙 delivery.md가 아직 없어 status를 draft로 둔다.)
- 확인 한계: ① 브라우저에서 reader.js를 실행해 Ask 메시지·클립보드 거부/부재 경로를 직접 관찰하지 않았다(R-26~28은 코드 확인). ② `--browser-check`는 통과 여부만 확인했고 측정 항목은 읽지 않았다. ③ `vendor/pele` 차트 렌더 내부와 reader의 보드 배치·Explore·내보내기는 범위 밖이다. ④ native 렌더러 9종의 내부 규칙은 행 6 범위다. ⑤ 시각 검토(사람 눈)는 하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/explainer/parse.mjs:4-45,83` 상수·`stable`·`csv`·`rowLabel`·`locate`·`unsupported` | 형식 판별(24행), 지원 타입 목록(4행), id 정규식(5행), 자동 id 해시(6행), 제한 문법에서 거부하는 Markdown 정규식(44행), 빈 문서 골격(83행) | R-01, R-04, R-05 |
| C-02 | `parse.mjs:103-152` `cells`/`attributes`/`rowWidth`/`boolean`/`number`/`select` | 표·지시문 행의 셀 분리(`\|` 이스케이프, 백틱), `key=value` 인자 파서, 숫자·불린 형식 | R-03 |
| C-03 | `parse.mjs:153-224` `directive` | 지시문 한 개 → 블록. 허용 인자표(175-178행), 블록별 변환 switch(193-216행), 오류 규칙(179-182, 217행) | R-03, R-04, R-09 |
| C-04 | `parse.mjs:225-230` `assessment` | 표 셀의 `{good\|caution\|bad[:라벨]}` 배지 추출 | R-04 |
| C-05 | `parse.mjs:231-282` 메인 루프 | `#`/`##`/`@`/펜스/표/목록/문단 분기와 제목·답·이유·패널 순서 오류 | R-02, R-04 |
| C-06 | `parse.mjs:283-299` `identity`, 반환 | 파싱 단계 id 검사·중복, `document:null` 규칙 | R-01, R-05 |
| C-07 | `archify/explainer/inline.mjs:7-30,33-114,125-155` | 링크 대상 5종 문법, 인라인 오류 코드, HTML 변환(citations·typical 주석) | R-06 |
| C-08 | `archify/schemas/explainer.schema.json` 전체 | 정규 문서 모델, 블록별 필드, 한도(500·20000·500·reasons 4·span 12 등) | R-07 |
| C-09 | `archify/explainer/validate.mjs:17-138` `validateExplainer` | 스키마 오류 → `schema-<keyword>`, id 이름공간·예약어, 참조 해석, 블록별 의미 검증 | R-05, R-07, R-08 |
| C-10 | `archify/explainer/writing.mjs:5-22,67-139` `RULES`, `lintExplainerWriting` | 규칙 정규식 목록, 단위 계산, 문장·문단·scope·굵게 한도 | R-10 |
| C-11 | `archify/explainer/diagrams.mjs:107-331` `compileExplainerDiagram` | 6종 약식 행 → 네이티브 spec 변환(셀 수, 접두 `actor`/`lane`/`entity`/`phase`, `a > b` 엣지, 배치, 한도) | R-09 |
| C-12 | `diagrams.mjs:354-389,434-445,447-517` `readSpec`, `nativeProcess`, `prepareExplainerDiagrams`, `validateExplainerDiagramTarget` | 다이어그램 입력 동결, 렌더러·검사기 자식 프로세스 호출, 결과 SVG 추출, 참조 대상 검증(경로는 BFS 도달성) | R-14, R-15 |
| C-13 | `archify/explainer/sources.mjs:10-17,54-66,170-318` | 크기 상수, 비밀 파일명·내용 패턴, 안전 경로, `resolveExplainerSources` 전체(레포 발췌, 인용 발췌의 조용한 폴백, 이미지, 차트 데이터) | R-11, R-12, R-13 |
| C-14 | `archify/explainer/prepare.mjs:11-131` | `prepareExplainer` 순서, bundle 모양·digest, 동결 의존 재확인, `readPreparedBundle`의 일치 조건, `validatePreparedTargets` | R-16, R-15 |
| C-15 | `archify/renderers/explainer/render-explainer.mjs:10-42` | 렌더러 진입: bundle 읽기, 출력 경로 해석, 원자 게시 | R-19 |
| C-16 | `archify/explainer/render.mjs:31-42,95-106,128` + `layout.mjs:5-35` | 언어 사전과 `english = !locale.startsWith('zh')`, 패널 DOM, HTML 골격과 payload 스크립트 3종 | R-22, R-29 |
| C-17 | `archify/explainer/check.mjs:15-167` `isExplainerHtml`, `checkExplainerHtml` | explainer 감지와 4개 검사의 모든 오류 코드 | R-21 |
| C-18 | `archify/explainer/patch.mjs:21-117` + `archify/bin/archify.mjs:5304-5350` `commandPatch` | 패치 전 과정과 모든 `patch-*` 거부 | R-23, R-24, R-25 |
| C-19 | `archify/explainer/reader.js:8,524-527,530-580` `setupAsk` + `render.mjs:31-34` 사전의 `ask*` 키 | Ask 다이얼로그, 인용 2자/400자, 메시지 줄 구성, 클립보드 폴백 | R-26, R-27, R-28 |
| C-20 | `archify/bin/archify.mjs:5888-5970`, `archify/bin/finalize.mjs:746` | finalize의 explainer 분기(품질 `showcase`, prepare 선행, `needsBrowser`) | R-17, R-20 |
| C-21 | `archify/explainer/revision.mjs:5-20` | `data-revision` 계산(경로 비의존 신원) | R-22 |

### 1.6 수락 사례

출처: 모두 원본 실행 관찰이다. 입력은 [spec-demos/explainer/](../../../artifacts/archify/spec-demos/explainer/)의 파일이고, 각 사례의 기대 출력은 그 실행에서 관찰한 값이다(스크립트 `run-bad.sh`, `run-deliver.sh`, `run-patch.sh`, `run-patch2.sh`, `run-misc.sh`, `run-cite.sh`, 공통 `env.sh`). 다른 구현은 같은 입력에 대해 같은 code·줄·rc를 내야 한다. 줄 번호는 입력 파일 기준이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-14, R-18, R-20, R-22 | `in/ok.archify.md`(@meta locale=en, 패널 4개, `@sequence`·`@steps`·표·`@facts`·`@callout`·체크리스트, `@source path=…layout.mjs lines=1:5`)를 `--repo-root <archify 체크아웃>`으로 `validate` 후 `finalize explainer … out.html` | validate rc 0, checks 4종 true. finalize rc 0, `gates:{validate,deliver,check:"pass","browser-check":"not-run"}`, `quality:"showcase"`, HTML의 DOM id에 `answer, flow, miss-flow, miss-steps, options, checks, source-router, source-docs`가 있고 id 없던 표·facts·callout·목록은 `comparison-<12hex>` 등 자동 id |
| T-02 | R-03 | `in/bad/b01`: `@foo id=x` 뒤에 행 | `explainer/parse-directive` 줄 7 "Unsupported component @foo." rc 1, HTML 없음 |
| T-03 | R-02 | `in/bad/b03`(제목 없음), `b04`(답 문단 없음), `b05`(패널 없음) | 각각 `parse-answer`+`parse-title`(줄 1), `parse-answer`(줄 1), `parse-panel`(줄 1) |
| T-04 | R-05 | `in/bad/b11`: 패널 id `explainer-x`와 `board` | `reserved-id` 줄 5, 줄 9 |
| T-05 | R-07 | `in/bad/b08`: 이유 5개 | `explainer/schema-maxItems` 줄 5 "/answer/reasons must NOT have more than 4 items" |
| T-06 | R-08 | `in/bad/b07`: `Claim.[](source:nope)`(출처 선언 없음) | `explainer/unresolved-reference` 줄 7 |
| T-07 | R-08, R-15 | `in/bad/b12`(`[B](node:sq.zzz)`)와 `in/bad/c19`(`route:sq.b~a`, 엣지는 a→b뿐) | b12 `explainer/diagram-node` 줄 12, c19 `explainer/diagram-route-reference` 줄 12(렌더 후 단계) |
| T-08 | R-09 | `in/bad/b13`: `@dataflow` 약식 | `explainer/diagram-shorthand-unsupported` 줄 7 |
| T-09 | R-06 | `in/bad/c01`~`c06`: 본문에 `<b>`, `*미완`, `[x](ftp://…)`, `![x](a.png)`, `~~x~~`, `[^1]` | 각각 `inline-html`, `inline-emphasis`, `inline-target`, `inline-image`(+`inline-target`), `inline-decoration`, `inline-footnote`, 모두 줄 7 |
| T-10 | R-10 | `in/bad/d01`(34단위 영어 문장). `validate --writing warn`/`strict`/`off` | warn: rc 0, 진단 `writing-sentence-length` severity warning("34 reading units … limit of 28"). strict: 같은 code가 error, rc 1. off: 진단 없음 |
| T-11 | R-11 | `in/bad/b14`(`@code`, 근거 `path=…layout.mjs lines=1:5`)를 `--repo-root` 없이, 그리고 `b15`(`lines=1:99999`)·`b17`(`.env`)을 `--repo-root`로 | b14(root 없음) `explainer/repository-root`, b15 `repository-location`, b17 `secret-path`. b14를 `--repo-root`로 실행하면 rc 0 |
| T-12 | R-12 | `in/cite-bad-lines.archify.md`(`[](source:s1)`, `lines=1:99999`, `@code` 없음)를 `--repo-root`와 함께 finalize | rc 0 통과, bundle의 `s1`에 `text` 없음, `dependencies` 비어 있음 |
| T-13 | R-17 | `@meta locale=en quality_profile=standard`가 있는 `in/q-standard.archify.md`를 finalize / deliver | 결과 HTML의 bundle `quality`가 각각 `showcase` / `standard` |
| T-14 | R-20 | `in/bad/b07`을 finalize | rc 1, stdout JSON `gates`가 네 단계 모두 `"not-run"`, 첫 진단 `explainer/unresolved-reference`, 출력 HTML 없음. 이어서 정상 초안 `in/ok.archify.md`에 `finalize --browser-check`를 주면 `browser-check:"pass"`, `browserCheck:{requested:true,ran:true}` |
| T-15 | R-19 | `deliver explainer in/ok.archify.md out.html --repo-root …`의 `*.delivery.json` | `command:"deliver"`, `type:"explainer"`, `explainer.dependencies`에 `repository:router`(path·40자 revision·sha256·bytes), `diagram-spec:miss-flow`(`inline:true`), `contentBase64`는 없음 |
| T-16 | R-21 | `out/deliver/ok.html`에서 본문 한 단어만 바꾼 사본, 그리고 본문과 임베드 초안을 함께 바꾼 사본을 `check` | 앞 사본: rc 0, `ok:true`. 뒤 사본: rc 1, 진단 `bundle-hash`, `bundle-source-hash`, `source-hash`, `content-revision`, `document-hash` |
| T-17 | R-23 | `ok.html` 사본에서 `patch explainer … options in/patch/p1-good.md out.html --repo-root …`(같은 id, 표에 열 하나 추가) | rc 0. `panelId:"options"`, `original.revision`≠`revision`, 패널 id `flow, options, checks, answer` 유지, 다이어그램 `miss-flow` sha256 동일, 표 자동 id만 바뀜, 원본 파일 불변 |
| T-18 | R-24 | 같은 원본에 교체 파일 `p2`(id `options-v2`), `p3`(`##` 둘), `p4`(`@source` 추가), `p6`(끝 개행 없음), `p8`(id 없는 제목), 존재하지 않는 id `nope`, `answer`, `p5`(`@foo`) | 각각 `patch-identity`, `patch-identity`, `patch-scope`, `patch-identity`, `patch-identity`, `patch-target`, `patch-target`, `parse-directive` 줄 29(새 원고 전체 기준). 모두 rc 1, 출력 없음 |
| T-19 | R-24 | `structure.html`(native 다이어그램 페이지) 사본에 patch | rc 1 `explainer/patch-payload`("Embedded native diagram payload cannot be inflated.") |
| T-20 | R-25 | patch 결과를 다시 다른 패널(`checks`)로 patch, 같은 경로로 제자리 덮어쓰기, `--repo-root` 없이 patch | 세 경우 모두 rc 0. 제자리는 파일 내용이 바뀜 |
| T-21 | R-29 | `@meta locale`을 `ko`, `en`, `zh-CN`로 바꾼 사본과 `@meta` 줄이 없는 사본을 각각 finalize | `explainer-reader-words`의 `ask`: ko→`Ask`, en→`Ask`, zh-CN→`追问`, 줄 없음→`追问`(`html lang="zh-CN"`). `askCopy`: `Copy question` / `复制追问` |
| T-22 | R-26~R-28 | (코드 기준, 브라우저 미실행) 결론이 아닌 패널 `options`에서 "Read latency"를 선택해 Ask, 질문 칸 비움 | 복사 메시지(영어): `Page: "<h1>"` / `File: <경로>` / `Where: Panel 2 "<제목>" (ID: options)` / `Quote: "Read latency"` / `Question: I do not follow this part` / `Revise only this panel with Archify panel replacement (patch explainer), keeping its ID.`. 선택이 1자면 인용 버튼이 뜨지 않음, 500자 선택이면 인용 앞 400자만 |
| T-23 | R-08 | `in/bad/b26`: `@tree` 다이어그램 5개 | rc 0 통과(문서의 "최대 4개"는 강제되지 않음) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

문서와 구현이 다른 곳(구현을 사실로 썼다):

- `references/explainer-authoring.md`는 "A document holds up to four native diagrams"라고 쓰지만 코드에 개수 상한이 없다(`explainer/*.mjs`에서 검색해도 없음). `in/bad/b26`의 5개 문서가 통과했다(T-23).
- 같은 문서의 `@metric` 행은 "`value` or `limit` required"인데 스키마 `required`는 `id,type,label`뿐이다(`schemas/explainer.schema.json` metric). `@metric label=Latency`가 통과하고 HTML에는 빈 "上限"이 나온다(`in/bad/c14`, `out/misc/metric.html`).
- 같은 문서의 `@meta` 표는 `locale (en, zh-CN, zh-TW, es, ko, ar)`를 나열하지만 UI 사전은 en·zh뿐이라 `zh`로 시작하는 `zh-CN`·`zh-TW`만 중국어 UI이고 `en`·`es`·`ko`·`ar`는 모두 영어 UI다(R-29).
- 디렉티브 표가 빠뜨린 것: `@meta`의 `repo_provider`, `repo_link_mode`, `@source`의 `revision`, `@diagram`의 `spec`·`changes`(파서는 허용, `parse.mjs:175-178`).
- overview feature map 10행은 "prepare·validate·sources → render"로 적었지만 구현에서 `prepareExplainer`가 validate·sources·diagram을 모두 포함하는 하나의 prepare이고(`prepare.mjs:29-47`) `validate` 명령은 렌더·검사까지 한다(R-18). 같은 행의 "선행 7"은 실제로는 native 렌더러·`check-render-output`(6)과 스키마 검증(5)도 쓴다(`diagrams.mjs:480-486`).

| R-ID / T-ID | 근거 (repo@a406594 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-06, `bin/archify.mjs:2416-2425` `prepareExplainerInput`, `prepare.mjs:19-28` | JSON 초안 통과는 `in/ok-json.archify.md`(`out/misc/json-draft.json`). 인코딩·크기는 코드만 |
| R-02 | C-05 `parse.mjs:231-282`; `out/bad-summary.tsv` b03·b04·b05·c09~c12 | 실행 |
| R-03 | C-02, C-03; b01, b02, c07, c08, c13 | 실행. 인자 쪽 세부(따옴표 이스케이프)는 코드 |
| R-04 | C-01 `:44`, C-05; b09, b10, b20, b25 | 실행. 펜스 오류(`parse-snippet`)는 코드만 |
| R-05 | C-06, C-09 `validate.mjs:56-74`; b06, b11, b24, c29 | 실행 |
| R-06 | C-07; c01~c06 | 실행 |
| R-07 | C-08, C-09 `:28-55`; b08, b22, b23, c15, c25, c31 | 실행. `maxItems`를 제외한 `schema-<keyword>` 전부는 코드 |
| R-08 | C-09 `:56-135`, `diff.mjs:27-123`; 위 목록의 실행 | 일부만 실행 |
| R-09 | C-11; b13, b21 | 실행(6종 정상 변환은 sequence·workflow 약식을 ok.archify.md와 기존 `trigger-flow.archify.md`로 확인, 나머지 4종은 코드만) |
| R-10 | C-10; d01, d02; `out/misc/writing-*.json` | 실행. 한자 문장 한도 50 등은 코드 |
| R-11 | C-13 `sources.mjs:170-263`, `repository-evidence.mjs`(행 5 범위, 호출만 확인); b14, b15, b17, b28 | 실행. `verifyRepositoryEvidence` 내부는 행 5 |
| R-12 | C-13 `sources.mjs:264-284` | 실행(`out/cite/`). 의도는 코드 주석이 밝힘(`sources.mjs:264-265`, 코드 확인) |
| R-13 | C-13 `:102-168,292-316`, `charts.mjs:24-70`; b16, c17, c18 | 실행(오류 경로). 정상 이미지·차트 경로는 코드만 |
| R-14 | C-12 `diagrams.mjs:447-500`; `out/ok.validate.json`의 `explainer_native_diagrams` | 자식 프로세스 인자는 코드, 통과는 실행 |
| R-15 | C-12 `:502-517`, C-14 `:103-131`; c19 | 실행 |
| R-16 | C-14; `out/deliver/ok.delivery.json`의 `explainer` | 필드는 실행, 불일치 분기는 코드 |
| R-17 | C-20 `archify.mjs:5925,5944`, `prepare.mjs:33`; `in/q-standard.archify.md` | 실행(T-13) |
| R-18 | `archify.mjs:6968-7140` `commandValidate`; `out/ok.validate.json` | 실행 |
| R-19 | C-15, `archify.mjs:4480-4490,4859-4873,5120-5126,5017`, `scripts/check-render-output.mjs:44-48` | 코드 + provenance 실행 |
| R-20 | C-20, `finalize.mjs:746,148-156`, `archify.mjs:5967`; `out/misc/finalize-*.json`, `out/deliver/ok.finalize-summary.json` | 실행 |
| R-21 | C-17; `out/patch2/tampered*.check.json` | 실행 |
| R-22 | C-16, C-21; `out/deliver/ok.html` | 구조·id는 실행, 레이아웃 수치는 코드 |
| R-23~R-25 | C-18; `out/patch/*.json`, `out/patch2/*.json` | 실행 |
| R-26~R-28 | C-19 `reader.js:530-580`, `:524-527` | 코드만. 클립보드 부재 경로는 추론 |
| R-29 | C-16 `render.mjs:36-42`, `reader.js:8`; `out/deliver/loc-*.html` | 실행 + 코드로 원인 확정 |
| T-01~T-21, T-23 | 위 스크립트와 `out/` | 원본 실행 관찰 |
| T-22 | C-19 | 코드 기준. 브라우저 미실행 |

### 2.2 코드 읽는 순서

`bin/archify.mjs:5888` `commandFinalize` → `prepareExplainerInput:2416` → `explainer/prepare.mjs:29` `prepareExplainer` → `parse.mjs:18` → `validate.mjs:17` → `sources.mjs:171` → `diagrams.mjs:448` → `render-explainer.mjs` → `render.mjs:37` → `check.mjs:57`. 패치는 `archify.mjs:5304` → `patch.mjs:21`. Ask는 `reader.js:530`. 구현 전략: 자식 프로세스로 native 렌더러를 재사용하고(언어 경계), 모든 외부 바이트를 해시와 함께 동결해 bundle 하나로 만들며, 그 bundle을 HTML 안에도 넣어 patch가 원본 파일 없이 다시 쓸 수 있게 한다.
