---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-16
updated: 2026-11-16
sources:
  - archify/schemas/*.schema.json
  - archify/schemas/README.md
  - archify/references/authoring-defaults.md
  - archify/references/authoring-contract.md
  - archify/references/explainer-authoring.md
  - archify/references/brand-marks.md
  - archify/references/repository-authoring.md
  - archify/renderers/{workflow,sequence,dataflow,lifecycle,erd,class,tree,timeline,waterfall}/README.md
  - archify/renderers/architecture/{grid.mjs,render-architecture.mjs}
  - archify/renderers/workflow/workflow-compiler.mjs
  - archify/renderers/dataflow/dataflow-compiler.mjs
  - archify/renderers/shared/{geometry.mjs,utils.mjs}
  - archify/locales/en.json
  - archify/examples/
---

# [Q6] candidate.json의 구조와 모든 key·value (의미·사용 시점 포함)

- **상위 개요**: [overview.md](../overview.md)
- **관련**: [Q4](./q4-supported-diagram-types.md)(타입 목록), [Q5](./q5-what-ai-writes-per-type.md)(AI가 쓰는 것)

## 0. 이 문서를 어디에서 읽어 만들었나

기준 SHA `a7ed6fd`의 `repos/archify/archify/` 아래를 읽었다. 표의 "의미·언제 쓰나" 열 끝의 `[약어]`가 근거 위치다.

| 약어 | 읽은 파일 | 어떻게 읽었나 |
|---|---|---|
| 스키마 | `schemas/*.schema.json` 11개(`common` 포함) | 스크립트로 `$ref`를 풀어 구조·필수·enum·제약 표를 자동 생성. `description` 필드는 [SD] |
| SD | 같은 스키마의 `description` | 있는 것만(sequence `column_fit`, lifecycle `mainPath`·상태 `type`, timeline·waterfall `evidence` 등 약 20개) |
| SR | `schemas/README.md` 전체 | 전문 |
| AD | `references/authoring-defaults.md` 전체 | 전문 |
| AC | `references/authoring-contract.md` 전체 | 앞 700줄 전문(구성 수리, 라벨, 범례, 언어, 기하 규칙, 타입별 배치, 저장소 근거, 아이콘) |
| RW·RS·RD·RL·RE·RC·RT·RTL·RWF | `renderers/{workflow, sequence, dataflow, lifecycle, erd, class, tree, timeline, waterfall}/README.md` | 전문 9개 |
| EA | `references/explainer-authoring.md` 전체 | 전문 |
| BM | `references/brand-marks.md` | 앞 70줄(브랜드 결정 경로) |
| RA | `references/repository-authoring.md` | 앞 40줄(고정할 저장소 신원) |
| 코드 | `renderers/architecture/{grid,render-architecture}.mjs`, `renderers/workflow/workflow-compiler.mjs`, `renderers/dataflow/dataflow-compiler.mjs`, `renderers/shared/{geometry,utils}.mjs` | 키 이름으로 grep해 해당 줄 근처만. 줄 번호는 설명 안에 표기 |
| locales | `locales/en.json`의 `legend.*` | 타입 값의 기본 범례 이름(영어) |
| 스펙 | 이 작업 공간의 `capabilities/explainer.md` | 이전에 쓴 스펙(초안 문법 요약) |

**읽지 않은 것**: `architecture` 렌더러에는 README가 없다(코드로만 확인). `references/delivery-contract.md`(전달·검사), `viewer-runtime.md`, `update-awareness.md`, `architecture-layout-repair.md`, `brand-marks.md` 뒷부분, `repository-authoring.md` 뒷부분, 렌더러 코드 대부분(배치 알고리즘 본문)은 이 문서를 위해 읽지 않았다. 그래서 아래 표의 **"미확인"** 은 "문서와 읽은 코드에 설명이 없다"는 뜻이다.

## 1. 질문과 결론

- **질문**: 10종 `candidate.json` 구조가 모두 같은가, 모든 key와 value가 무엇을 의미하고 언제 쓰이는가.
- **결론: 뼈대는 같고 본문 배열이 다르다.** 10종 모두 최상위가 `schema_version` + `diagram_type` + `meta` + (타입별 본문 배열) + 선택 `cards`이고, 모든 객체에 `additionalProperties: false`라서 스키마에 없는 키는 거부된다(`schemas/README.md`). `diagram_type`이 `const`라서 파일의 타입은 이 값으로 정해지고, 렌더러가 그 타입의 스키마로 검증한다.
- 같은 것: 최상위 4개 필수 키 틀, `meta`의 큰 틀, 공통 정의(id 규칙, `componentType`, `variant`, `side`, `sources`, `cards`).
- 다른 것: 본문 배열 이름과 항목 키, `schema_version` 값(workflow 1·2, lifecycle 3, 나머지 1), `meta`의 일부 키, 위치를 주는 방식.
- **의미를 적은 방식**: 모든 키 행에 "의미·언제 쓰나" 열을 붙였다. 문서 근거가 있는 것만 적었고, 근거가 없으면 `미확인`으로 남겼다. 같은 키라도 타입마다 뜻이 다르면(예: `tag`, `variant`, `note`, `type`) 타입별 행에 따로 적었다.
- **스키마와 문서·구현의 어긋남(코드 확인)**:
  - `meta.output`은 architecture·workflow·sequence·dataflow·lifecycle에서만 필수이고 erd·class·tree·timeline·waterfall에서는 선택이며 경로 규칙도 없다. `schemas/README.md`는 "모든 스키마가 `output`을 요구한다"고 쓴다.
  - `meta.views`는 **폐기(retired)**: 스키마는 받지만 렌더러는 읽지 않는다(`schemas/README.md`, 소스 grep). Q4·Q5에서 선택 기능처럼 적은 부분은 이미 고쳤다.
  - `meta.animation`: README는 opt-in이라고 하고 `authoring-defaults.md`는 "모션은 자동이니 생략하라"고 한다. 이전 세션 확인(next.md)으로 렌더러는 값을 읽지 않는다.
  - **architecture 배치**(Q5 정정): `layout`을 생략하면 자유 배치라서 **모든 컴포넌트에 `pos`가 필수**(코드 `render-architecture.mjs:496-504`)이고, `layout.mode: "grid"`를 쓰면 `row`/`col`(또는 `pos`)이 필요하다. Q5에서 "`row`/`col`/`pos`는 스키마상 필수가 아니다"라고 쓴 것은 스키마만 본 결과이며 렌더러가 요구한다.
- **표 읽는 법**: `필수`는 그 객체 안에서의 필수다. 타입의 `string | object`는 둘 중 하나, `array<string>`은 문자열 배열, `[number, number]`는 좌표 쌍. 경로 끝 `[]`는 배열 원소. 길이·패턴은 스키마 값 그대로다.


## 2. 10종의 최상위 구조 비교

| 타입 | `schema_version` | 최상위 필수 키 |
|---|---|---|
| `architecture` | `1` | `['schema_version', 'diagram_type', 'meta', 'components']` |
| `workflow` | `[1, 2]` | `['schema_version', 'diagram_type', 'meta', 'lanes', 'nodes', 'edges']` |
| `sequence` | `1` | `['schema_version', 'diagram_type', 'meta', 'participants', 'messages']` |
| `dataflow` | `1` | `['schema_version', 'diagram_type', 'meta', 'stages', 'nodes', 'flows']` |
| `lifecycle` | `3` | `['schema_version', 'diagram_type', 'meta', 'mainPath', 'states', 'transitions']` |
| `erd` | `1` | `['schema_version', 'diagram_type', 'meta', 'entities']` |
| `class` | `1` | `['schema_version', 'diagram_type', 'meta', 'types']` |
| `tree` | `1` | `['schema_version', 'diagram_type', 'meta', 'nodes']` |
| `timeline` | `1` | `['schema_version', 'diagram_type', 'meta', 'events']` |
| `waterfall` | `1` | `['schema_version', 'diagram_type', 'meta', 'spans']` |

실제 예시 파일의 최상위 키(코드 확인, `examples/`를 읽음):

| 타입 | 파일 | 최상위 키 |
|---|---|---|
| `architecture` | `web-app.architecture.json` | `schema_version` · `diagram_type` · `meta` · `components` · `boundaries` · `connections` · `cards` |
| `workflow` | `agent-tool-call.workflow.json` | `schema_version` · `diagram_type` · `meta` · `lanes` · `phases` · `groups` · `mainPath` · `nodes` · `edges` · `cards` |
| `sequence` | `cache-miss-request.sequence.json` | `schema_version` · `diagram_type` · `meta` · `participants` · `segments` · `messages` · `activations` · `cards` |
| `dataflow` | `product-analytics.dataflow.json` | `schema_version` · `diagram_type` · `meta` · `stages` · `nodes` · `flows` · `cards` |
| `lifecycle` | `deployment-release.lifecycle.json` | `schema_version` · `diagram_type` · `meta` · `mainPath` · `states` · `transitions` · `cards` |
| `erd` | `orders.erd.json` | `schema_version` · `diagram_type` · `meta` · `layout` · `entities` · `relationships` · `cards` |
| `class` | `payments.class.json` | `schema_version` · `diagram_type` · `meta` · `layout` · `types` · `relationships` |
| `tree` | `payment-platform.tree.json` | `schema_version` · `diagram_type` · `meta` · `nodes` |
| `timeline` | `payment-incident.timeline.json` | `schema_version` · `diagram_type` · `meta` · `lanes` · `events` |
| `waterfall` | `checkout-request.waterfall.json` | `schema_version` · `diagram_type` · `meta` · `spans` |

## 3. 값(enum)의 의미 사전

표의 enum 값들이 무엇을 뜻하는지 한곳에 모았다. 기본 범례 이름은 `locales/en.json`의 `legend.*`(영어)다.

### 3.1 컴포넌트 `type` (`componentType` 7종)

색·범례 그룹을 정하는 값이다. **같은 값이 타입마다 다른 기본 이름**으로 범례에 나온다(코드 확인, `locales/en.json`).

| 값 | architecture 범례 | workflow 범례 | dataflow 범례 | 비고 |
|---|---|---|---|---|
| `frontend` | Frontend | User UI | — | 사용자 화면·클라이언트 |
| `backend` | Backend | Agent logic | — | 로직·서비스. `type` 생략 시 explainer 약식 행의 기본값 [EA] |
| `database` | Database | Context / trace | data store | 증거가 있는 저장소에만. dataflow는 노드가 실제 `database`일 때만 범례에 추가 [RD, AD] |
| `cloud` | Cloud | Cloud service | — | 클라우드 서비스 |
| `security` | Security | Policy | — | 인증·정책 |
| `messagebus` | Message bus | Tool action | — | 큐·버스. workflow에서는 도구 호출 |
| `external` | External | External system | — | 외부 행위자·시스템. 시스템 경계 밖에 둔다 [AC] |

sequence의 기본 범례는 컴포넌트 type이 아니라 **메시지 variant** 기준이다. 아이콘은 `type`이 정한 색·그룹을 바꾸지 않는다 [SD nodeIcon].

### 3.2 `variant` 값

| 값 | 선 의미 | 기본 범례 이름 (sequence / dataflow) |
|---|---|---|
| `default` | 일반 관계·의존·복귀·폴백 | message / data flow |
| `emphasis` | 주 요청·주 데이터 경로. 기본 선 굵기 1.5→1.8(dataflow·workflow는 1.4→1.8) | main request / primary data |
| `security` | 인증·동의·권한·정책·PII·제한 조인 | security / policy · PII |
| `dashed` | 비동기·배치·트레이스·이벤트·비차단 작업 | async trace / async batch |
| `return` | (sequence 전용) 조용한 응답 메시지, 회색 | return |

출처: [RS Design Rules, RD Design Rules, AD, 코드 선 굵기]. 소스가 그 의미를 지지할 때만 쓴다(`AD`). `phases`·`groups`·`lanes`의 `variant`는 프레임 색 강조이며 범례 의미는 문서에 없다(미확인).

### 3.3 `side`와 경로 프리셋 `route`

- `side`(`left`/`right`/`top`/`bottom`): 노드의 어느 변에서 나가고 들어오는지. 첫·끝 구간이 그 방향을 향해야 하며 틀리면 `clean-flow/endpoint-side-direction` [AC].
- 경로 프리셋은 타입마다 값이 다르다.

| 타입 | `route` 값 | 의미 |
|---|---|---|
| architecture | `auto`·`straight`·`orthogonal-h`·`orthogonal-v` | 자동 / 한 직선(변을 안 고정하면 대각선 가능) / 가로 우선 직교 / 세로 우선 직교 [AC, 스키마] |
| workflow | `auto`·`straight`·`drop`·`outside-right`·`return-left`·`bottom-channel`·`up-channel` | 자동 / 직선 / 레인 사이에서 꺾음(`bias`) / 오른쪽 바깥 통로 / 왼쪽 바깥 통로 / 아래 통로 / 위 통로 [RW, 코드 readablePresetVia] |
| dataflow | `auto`·`straight`·`vertical-channel`·`bottom-channel`·`top-channel` | 중간점 엘보 / 직선 / 세로 통로(`channelX`) / 아래·위 가로 통로(`channelY`) [RD, 코드 routeVia] |
| erd·class | `auto`·`straight`·`orthogonal-h`·`orthogonal-v` | architecture와 같은 라우터 사용 [RE, RC] |

### 3.4 `icon` 값 (`nodeIcon` 22종)

노드 모서리의 장식 아이콘이며 접근성 도구에는 숨겨진다 [AC Node icons].
- 일상 개념: `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`
- 컴포넌트 타입 기호: `frontend`·`backend`·`database`·`cloud`·`security`·`messagebus`·`external`
- 상태 기호: `start`·`active`·`waiting`·`decision`·`success`·`failure`·`stop`·`neutral`
- `none`: 아이콘 숨김. 생략하면 타입 기본값(lifecycle `start`·`active`·`neutral`은 기본 기호 없음) [AC, RL]

### 3.5 lifecycle 상태 `type`, class `kind`, timeline `kind`, waterfall `status`

각 행의 설명은 6장 해당 표에 있다. 기본 범례 이름: lifecycle(initial state, active, waiting, decision, success, failure / exit, neutral, external, final state), class 관계(Depends on, Association, Inherits, Implements, Composition, Aggregation), timeline(Event, Change, Alert, Response, Recovery), waterfall(Completed, Error, Cancelled, Incomplete (no recorded end)).

### 3.6 기타 값

| 키 | 값 | 의미 |
|---|---|---|
| `meta.visual_preset` | `classic`·`signal-flow`·`blueprint`·`editorial` | 기본 스타일 / 발광·모션 중심 / 고대비 엔지니어링 리뷰 / 따뜻한 출판물 스타일. 스타일만 바뀜 [SR] |
| `meta.quality_profile` | `standard`·`showcase` | 경고로 두는 / 실패로 처리하는 구성 품질 판정 [SR, RW] |
| `meta.animation` | `trace`·`none` | 모션 사용 여부. 실제로는 렌더러가 읽지 않음(1절) |
| `meta.legend.mode` | `auto`·`all`·`hidden` | 쓰인 종류만 / 전체 카탈로그 / 전부 숨김 [SR] |
| `meta.repository.provider` | `github`·`gitee`·`gitlab` | 링크 생성 forge [AC] |
| `meta.repository.link_mode` | `web`·`local-only` | 링크 생성 / 링크 없이 SRC 표시만 [AC] |
| `meta.column_fit` | `fixed`·`spread` | 옛 고정 좌표 / viewBox 맞춰 분산 [SD] |
| `meta.evidence` | `observed`·`illustrative` (timeline), `measured`·`illustrative` (waterfall) | 기록된 관측·측정 / 설명용 입력 [SD] |
| `meta.unit` | `us`·`ms`·`s` | waterfall 시간 단위 [SD] |
| `meta.engineering_profile` | `deployment-ownership` | 배포 소유 검토 계약(architecture) [SR] |
| `cards[].dot` | `cyan`·`emerald`·`violet`·`amber`·`rose`·`orange`·`slate` | 카드 제목 앞 점의 색(의미 규칙은 미확인) |


## 4. 공통 `$defs` (`common.schema.json`)

여러 타입이 `$ref`로 가져다 쓰는 값 정의다(의미는 3·5·6장 표에서 키별로 설명).

- `id`: `^[a-zA-Z][a-zA-Z0-9_-]*$`. 영문자로 시작, 영문·숫자·`_`·`-`.
- `locale`: `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`, 최대 35자(예 `en`, `zh-CN`, `es`).
- `translations`: 객체. 키 `^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)*$`(메시지 키), 값 1~400자, 최대 600개.
- `portableOutputPath`: `.html`로 끝나는 `/` 구분 상대 경로. 역슬래시·제어문자·`..`·Windows 예약어·끝의 점/공백·255자 초과 구성요소·`~숫자` 구성요소 금지(요약).
- `point`: `[x, y]` 숫자 2개.
- `side`: `left`·`right`·`top`·`bottom`.
- `relationshipWidth`: 숫자, 최소 0.5(선 굵기).
- `brandMark`: (a) 문자열 1~2048자 — 80자 이하 한 줄 이름 또는 `http(s)://` URL, 또는 (b) `{url(http(s) 8~2048자), sha256(64자 hex)}` 객체.
- `legendEntry`: `{label?: 1~80자, visible?: boolean}`, 최소 키 1개.
- `repository`, `sourceReferences`, `cards`: 5절·6절 표 참고. `sources`는 노드당 1~3개, 각 `{path(필수, 1~240자), line?, end_line?, label?(1~48자)}`.
- `guidedViews`: 폐기된 `meta.views` 모양(최대 5개).
- 나머지 enum은 3장 참고.


## 5. 공통 `meta`와 `cards`

`meta`는 타입마다 허용 키가 조금씩 다르다. 같은 경로가 두 줄이면 타입에 따라 필수 여부나 값 제약이 다르다는 뜻이다. `cards`는 10종 모두 최상위 선택 키다.

| 경로 | 타입 | 필수 | 값 제약·enum | 존재하는 타입 | 의미·언제 쓰나 |
|---|---|---|---|---|---|
| `meta` | object | 필수 |  | 전체 10종 | 다이어그램 메타 정보 객체. 제목·출력 경로·언어·품질·근거 저장소 등을 담는다 [SR]. |
| `meta.title` | string | 필수 | minLength `1` | 전체 10종 | HTML 문서 `<title>`과 화면 `<h1>` 제목. 한 줄로 간결하게 쓰고 설명은 다이어그램에 맡긴다. 범위를 좁혔다면 제목에 밝힌다 [AC Title hierarchy, AD, 코드 `applyTemplate`(utils.mjs:150)]. |
| `meta.locale` | string |  | pattern `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`; maxLength `35` | 전체 10종 | 뷰어 UI·`<html lang>`·문서 제목 접미사·기본 범례/접근성 문구의 언어 태그. 저자가 쓴 문장은 번역하지 않는다. 번들 카탈로그 `en`,`zh-CN`,`zh-TW`,`es`,`ko`,`ar`는 이 값만으로 선택. 생략하면 영어 [SR, AC Language consistency]. |
| `meta.translations` | object |  |  | 전체 10종 | 번들 카탈로그에 없는 언어이거나 일부 UI 문구만 바꿀 때 쓰는 메시지키→번역 문자열 맵. `{placeholder}`가 영어 원문과 같아야 하며 틀리면 해당 항목만 거부되고 경고 [SR, AC]. |
| `meta.subtitle` | string |  |  | 전체 10종 | 제목 아래 한 줄 부제. 사용자가 요청할 때만 쓰고 기본은 생략(생략해도 빈 줄 없음) [AC Title hierarchy, AD]. |
| `meta.output` | string | 필수 | pattern `^[^/]+(?:/[^/]+)*$`; minLength `1`; HTML 파일 경로 규칙(4절) | architecture, workflow, sequence, dataflow, lifecycle | 결과 HTML의 이식 가능한 POSIX 상대 경로(작업 디렉터리 안, `.html`로 끝남). 렌더러 CLI는 출력 인자를 생략하면 이 값을 쓴다. architecture·workflow·sequence·dataflow·lifecycle에서만 필수 [SR, AD, RW]. |
| `meta.output` | string |  |  | erd, class, tree, timeline, waterfall | 결과 HTML의 이식 가능한 POSIX 상대 경로(작업 디렉터리 안, `.html`로 끝남). 렌더러 CLI는 출력 인자를 생략하면 이 값을 쓴다. architecture·workflow·sequence·dataflow·lifecycle에서만 필수 [SR, AD, RW]. |
| `meta.animation` | enum |  | enum: `trace` · `none` | 전체 10종 | SVG 모션 옵션(`trace`/`none`). 문서마다 상충: README는 opt-in이라 하고 AD는 "모션은 자동, 생략하라"고 한다. 이전 세션 확인(next.md)으로 렌더러는 값을 읽지 않고 `data-animation="trace"`가 항상 붙는다 [SR, AD]. |
| `meta.visual_preset` | enum |  | enum: `classic` · `signal-flow` · `blueprint` · `editorial` | 전체 10종 | 뷰어 스타일 프리셋: `classic`(기본), `signal-flow`(발광·모션 중심), `blueprint`(고대비 엔지니어링 리뷰), `editorial`(따뜻한 출판물 스타일). 스타일만 바꾸고 id·기하는 그대로. 사용자가 스타일을 요청할 때만 쓴다 [SR, AC Visual preset default]. |
| `meta.quality_profile` | enum |  | enum: `standard` · `showcase` | 전체 10종 | 구성 품질 판정 강도. `showcase`는 교차·복도 겹침·짧은 구간·라벨 충돌을 실패로 처리(기본 권장), `standard`는 같은 항목을 경고로 둔다. 8테이블·50필드 넘는 ERD는 첫 작성을 `standard`로 [SR, AD, AC ERD, RW]. |
| `meta.engineering_profile` | enum |  | enum: `deployment-ownership` | architecture | architecture 전용 의미 계약. `deployment-ownership`은 배포 검토용: 외부 아닌 컴포넌트마다 `tag`에 소유자, 정확히 하나의 `region`, `region`·`security-group` 경계 둘 다, DB는 security-group 안, 경계를 넘는 연결은 `label`에 실제 통과 수단 [SR, AC Engineering profile default]. |
| `meta.repository` | object |  |  | 전체 10종 | 코드 근거용 저장소 고정 정보. 실제 레포를 그릴 때만 쓰고 `--repo-root`로 git origin·커밋·blob·줄 범위를 검증한다 [SR, RA, AC Repository evidence]. |
| `meta.repository.url` | string | 필수 | minLength `1` | 전체 10종 | 기대하는 git origin 주소(자격증명 없는 것). `link_mode: local-only`에서도 신원 확인용으로 필수 [AC Repository evidence]. |
| `meta.repository.provider` | enum |  | enum: `github` · `gitee` · `gitlab` | 전체 10종 | 링크 생성 대상 forge. github.com·gitee.com·gitlab.com은 자동 감지, 자체 호스팅 GitLab은 `gitlab`으로 선언 [AC]. |
| `meta.repository.link_mode` | enum |  | enum: `web` · `local-only` | 전체 10종 | `web`(기본)은 revision 고정 링크 생성, `local-only`는 링크 없이 SRC 표시·경로·줄·revision만 [AC]. |
| `meta.repository.revision` | string | 필수 | pattern `^[a-fA-F0-9]{40}$` | 전체 10종 | 근거를 고정하는 40자리 커밋 SHA. 검증은 작업 트리가 아니라 이 커밋의 blob을 읽는다 [AC, RA]. |
| `meta.views` | array<object> |  | maxItems `5` | 전체 10종 | 폐기된 안내 뷰 목록(최대 5). 스키마는 옛 파일 호환으로 받지만 렌더러는 무시하므로 쓰지 않는다 [SR retired, 소스 grep]. |
| `meta.views[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 전체 10종 | (폐기) 안내 뷰 id. 렌더러가 무시 [SR]. |
| `meta.views[].label` | string | 필수 | minLength `1`; maxLength `48` | 전체 10종 | (폐기) 안내 뷰 이름 [SR]. |
| `meta.views[].focus` | array<string> | 필수 | minItems `1`; items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 전체 10종 | (폐기) 뷰가 강조할 노드 id 목록. 로더가 id 존재를 검사하지만 렌더러는 뷰를 그리지 않는다 [SR Runtime validation, retired]. |
| `meta.views[].note` | string |  | maxLength `140` | 전체 10종 | (폐기) 뷰 설명 [SR]. |
| `meta.legend` | object |  |  | architecture, workflow, sequence, dataflow, lifecycle, erd, class | 범례 표시 설정. 생략하면 쓰인 종류만 보이는 `auto`. 추가하면 의도된 설정이 되어 맞지 않는 라벨은 진단으로 실패한다 [SR Legend, AC Legend contract]. |
| `meta.legend.mode` | enum |  | enum: `auto` · `all` · `hidden` | architecture, workflow, sequence, dataflow, lifecycle, erd, class | `auto` 쓰인 종류만, `all` 렌더러의 전체 카탈로그, `hidden` 범례 전체 제거(항목 override보다 우선) [SR]. |
| `meta.legend.entries` | object |  |  | architecture, workflow, sequence, dataflow, lifecycle, erd, class | 범례 항목별 override 맵. 키는 렌더러가 소유한 종류 이름만 허용(4.1절). 항목은 `label`(표시 문구)·`visible`(강제 표시/숨김) [SR]. |
| `meta.viewBox` | [number, number] |  | minItems `2`; maxItems `2` | architecture, workflow, sequence, dataflow, erd, class, tree | 캔버스 크기 `[너비, 높이]`. 생략하면 내용에 맞춰 자동 계산(새 문서 권장). 주면 고정이 되어 렌더러가 늘리지 않고 넘치면 진단으로 실패 [AD, SR, RD, RS, RW]. |
| `cards` | array<object> |  |  | 전체 10종 | SVG 아래에 그려지는 요약 카드 목록. 독자의 추가 질문에 답하는 보조 설명이며 필수 토폴로지를 대신할 수 없다 [AD, 코드 `renderCards`(utils.mjs:114)]. |
| `cards[].dot` | enum | 필수 | enum: `cyan` · `emerald` · `violet` · `amber` · `rose` · `orange` · `slate` | 전체 10종 | 카드 제목 앞 색 점(`cyan`,`emerald`,`violet`,`amber`,`rose`,`orange`,`slate`). 장식용 색 구분 [코드 `renderCards` card-dot 클래스; 색별 의미 규칙은 미확인]. |
| `cards[].title` | string | 필수 | minLength `1` | 전체 10종 | 카드 제목(`<h3>`) [코드 renderCards]. |
| `cards[].items` | array<string> | 필수 |  | 전체 10종 | 카드 본문 글머리 항목 목록(`<li>`). 긴 근거는 라벨에서 줄이고 여기로 옮긴다 [AD, 코드 renderCards]. |
| `meta.column_fit` | enum |  | enum: `fixed` · `spread` | sequence | sequence 참가자 열 배치. `spread`(기본)는 viewBox에 맞춰 열 간격·박스 폭을 계산, `fixed`는 86px 박스·108px 간격의 옛 좌표 유지 [SD, RS]. |
| `meta.evidence` | enum | 필수 | enum: `observed` · `illustrative` | timeline | timeline: 사건이 기록된 관측(`observed`)인지 설명용(`illustrative`)인지 / waterfall: 시간이 측정(`measured`)인지 설명용인지. 캔버스에 배지로 그려진다. 지어낸 시각·숫자를 관측·측정으로 표시하지 않는다 [SD, AC Timeline/Waterfall]. |
| `meta.evidence` | enum | 필수 | enum: `measured` · `illustrative` | waterfall | timeline: 사건이 기록된 관측(`observed`)인지 설명용(`illustrative`)인지 / waterfall: 시간이 측정(`measured`)인지 설명용인지. 캔버스에 배지로 그려진다. 지어낸 시각·숫자를 관측·측정으로 표시하지 않는다 [SD, AC Timeline/Waterfall]. |
| `meta.timezone` | string |  | minLength `1` | timeline | timeline 축·라벨에 쓰는 IANA 시간대(기본 UTC). 눈금이 그 시간대의 벽시계 시각에 놓인다. 모르는 값은 `timeline/invalid-timezone` [SD, RTL]. |
| `meta.unit` | enum |  | enum: `us` · `ms` · `s` | waterfall | waterfall `start`·`end`·`duration`의 단위(`us`/`ms`/`s`, 기본 ms) [SD, RWF]. |

### 5.1 `meta.legend.entries`에 쓸 수 있는 키(타입별)

각 키는 `{label?: 1~80자, visible?: boolean}`이다. `label`은 독자에게 보이는 이름만 바꾸고 종류 자체나 노드·관계를 바꾸지 않는다. `visible: false`는 항목을 숨기고 `true`는 쓰이지 않은 항목도 강제로 보인다. sequence 메시지·dataflow 흐름 항목은 시각 키일 뿐 Semantic Lens 간선 사실을 만들지 않는다 [SR]. 키의 기본 이름은 3.1~3.2절과 `locales/en.json`.

- `architecture`: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external`
- `workflow`: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external`
- `sequence`: `default` · `emphasis` · `security` · `dashed` · `return`
- `dataflow`: `default` · `emphasis` · `security` · `dashed` · `database`
- `lifecycle`: `start` · `active` · `waiting` · `decision` · `success` · `failure` · `neutral` · `external`
- `erd`: `pk` · `fk` · `uk` · `one` · `many` · `optional`
- `class`: `dependency` · `association` · `inheritance` · `realization` · `composition` · `aggregation`
- `tree`: legend 없음
- `timeline`: legend 없음
- `waterfall`: legend 없음

## 6. 타입별 본문 키

`meta`·`cards`는 5절에, `sources[]`는 아래 한 번(공통)만 적었다. 경로 끝 `[]`는 배열 원소다.

**공통 `sources`**

- `sources`: 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC].
- `sources[].path`: 근거 파일의 저장소 상대 POSIX 경로 [SR].
- `sources[].line`: 근거 시작 줄(1부터) [SR].
- `sources[].end_line`: 근거 끝 줄 [SR].
- `sources[].label`: 근거 표시 라벨(최대 48자) [SR 스키마 제약, 표시 위치 세부는 미확인].


### 6.1 `architecture`

컴포넌트 = 노드, `connections` = 연결선, `boundaries` = 컴포넌트를 `wraps`로 감싸는 영역. 격자(`layout.mode: grid`+`row`/`col`) 또는 자유 배치(`layout` 생략+`pos`).

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | 배치 방식. 생략하면 자유 배치(모든 컴포넌트에 `pos` 필수). `mode: grid`면 `row`/`col`로 배치 [코드 render-architecture.mjs:496-504, grid.mjs]. |
| `layout.mode` | enum | 필수 | enum: `grid` | `grid`만 허용. `layout`을 쓰면 반드시 `grid` [코드 grid.mjs validateGridPlacement]. |
| `layout.origin` | [number, number] |  | minItems `2`; maxItems `2` | 격자 원점(첫 셀 좌상단). 기본 `[40,80]` [코드 grid.mjs DEFAULT_GRID]. 주 흐름의 첫 노드를 원점 근처(약 40,40)에 두라는 지침 [AD]. |
| `layout.cols` | integer |  | min `1`; max `12` | 격자 열 수(1~12, 기본 4). 컴포넌트 `col`은 0..cols-1이어야 한다 [코드 grid.mjs]. |
| `layout.gapX` | number |  | min `0` | 격자 셀 가로 간격(기본 30) [코드 grid.mjs]. 셀 위치 = origin + col×(cellW+gapX). |
| `layout.gapY` | number |  | min `0` | 격자 셀 세로 간격(기본 40) [코드 grid.mjs]. |
| `layout.cellW` | number |  | min `40` | 격자 셀 너비(기본 130) [코드 grid.mjs]. |
| `layout.cellH` | number |  | min `24` | 격자 셀 높이(기본 64) [코드 grid.mjs]. |
| `components` | array<object> | 필수 | minItems `1` | 시스템 구성요소(노드) 목록. 필수 배열 [SK, 스키마]. |
| `components[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `connections`의 `from`/`to`, `boundaries[].wraps`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `components[].type` | enum | 필수 | enum: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` | 컴포넌트 종류 7종. 색·범례 그룹을 정한다. 기본 범례 이름: frontend=Frontend, backend=Backend, database=Database, cloud=Cloud, security=Security, messagebus=Message bus, external=External [locales/en.json `legend.architecture.*`]. |
| `components[].label` | string | 필수 | minLength `1` | 컴포넌트에 보이는 이름. 폭에 맞춰 글자 크기가 조정된다 [코드 render-architecture.mjs fittedNodeFontSize]. |
| `components[].sublabel` | string |  |  | 제목 아래 보조 줄(역할·프로토콜·기술명). 길어지면 정확한 역할·프로토콜만 남기고 보충 사실은 노트나 카드로 옮긴다 [AC Label repair, AD]. |
| `components[].tag` | string |  |  | 컴포넌트 아래쪽의 작은 보조 텍스트(fine 수준). `meta.engineering_profile: deployment-ownership`이면 소유자 이름을 여기에 적어야 한다 [코드 render-architecture.mjs:1092-1093, SR]. |
| `components[].icon` | enum |  | enum: `calendar` · `clock` · `person` · `briefcase` · `flag` · `moon` · `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` · `start` · `active` · `waiting` · `decision` · `success` · `failure` · `stop` · `neutral` · `none` | 노드 모서리의 장식 아이콘. 색·의미 그룹은 `type`이 정하고 아이콘은 바꾸지 않는다. 생략하면 타입 기본값, `none`은 숨김. 일상 주제에 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`을 쓴다 [SD, AC Node icons]. |
| `components[].brand` | string \| object |  | minLength `1`; maxLength `2048` ; object | 실제 제품·모델·채널 정체성을 보이는 브랜드 마크. `archify brands`가 돌려준 ID 문자열 또는 `brands capture`가 만든 `{url, sha256}`. 렌더·검증은 네트워크를 쓰지 않고, 이름은 지어내지 않는다 [SR, BM]. |
| `components[].brand(객체형).url` | string | 필수 | pattern `^https?://`; minLength `8`; maxLength `2048` | 브랜드 사이트 URL 객체형. `archify brands capture <url> --json`이 만든 값으로, 렌더·검증 중 즉석 네트워크 캡처는 하지 않는다 [SR, BM]. |
| `components[].brand(객체형).sha256` | string | 필수 | pattern `^[a-f0-9]{64}$` | 캡처한 아이콘의 64자리 sha256. 내용이 바뀌면 fail-closed 진단 [SR, BM]. |
| `components[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `components[].row` | integer |  | min `0` | 격자 행 번호. 위에서 아래 [AD, RE]. |
| `components[].col` | integer |  | min `0` | 격자 열 번호. 왼쪽에서 오른쪽 [AD, RE]. |
| `components[].pos` | [number, number] |  | minItems `2`; maxItems `2` | 절대 좌표 `[x,y]`. 격자 셀보다 우선한다. ERD·class에서는 한정된 예외에만 쓴다 [코드 grid.mjs, RE, AC]. |
| `components[].size` | [number, number] |  | minItems `2`; maxItems `2` | 컴포넌트 크기 `[w,h]`. 생략하면 120×60 [코드 render-architecture.mjs:64-65,94]. |
| `boundaries` | array<object> |  |  | 컴포넌트들을 감싸는 영역 프레임. 실제 격리·소유·런타임·영속성 사실을 나타낼 때만 쓰고 관계를 대신하지 않는다 [AD, AC Mode placement]. |
| `boundaries[].kind` | enum | 필수 | enum: `region` · `security-group` | `region`(지역·클러스터 등, 모서리 12) 또는 `security-group`(보안 그룹, 모서리 8, 제목 색 다름). 새 값은 스키마가 거부 [코드 render-architecture.mjs:1044-1051, AC Schema lookup]. |
| `boundaries[].label` | string | 필수 | minLength `1` | 경계 제목 [코드 structural-frame-label]. |
| `boundaries[].wraps` | array<string> | 필수 | minItems `1`; items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 경계가 감쌀 컴포넌트 id 목록. 프레임은 이 멤버들의 외곽 상자에 패딩을 더해 계산된다. 멤버는 하나의 촘촘한 직사각형 군집으로 두고 비멤버(특히 외부 액터)는 박스 밖에 둔다 [코드 boundaryRect, AC]. |
| `boundaries[].pad` | number |  | min `0` | 프레임 패딩(px, 기본 30) [코드 render-architecture.mjs:69,123]. |
| `connections` | array<object> |  |  | 컴포넌트 사이 관계선. 주 사용자 여정과 필요한 분기를 보존한다 [AD]. |
| `connections[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `connections[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `connections[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `connections[].label` | string |  |  | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `connections[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 선 스타일과 의미: `default` 일반, `emphasis` 주 경로(굵게), `security` 인증·정책·PII, `dashed` 비동기·배치. 소스가 그 의미를 지지할 때만 쓴다 [RD, RS, AD]. |
| `connections[].fromSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 출발 쪽(`left`/`right`/`top`/`bottom`). 방향 계약: 첫 구간이 그 방향으로 수직·바깥을 향해야 한다. 필요한 분기·복귀·지정 기하에만 고정 [AC Executable geometry]. |
| `connections[].toSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 도착 쪽. 마지막 구간이 그 방향으로 들어와야 한다 [AC]. |
| `connections[].route` | enum |  | enum: `auto` · `straight` · `orthogonal-h` · `orthogonal-v` | `auto` 자동, `straight` 한 직선(변을 고정하지 않으면 대각선 가능), `orthogonal-h`/`orthogonal-v` 가로/세로 우선 직교 [AC Executable geometry, 스키마 enum]. |
| `connections[].via` | array<array> |  | items: minItems `2`; maxItems `2` | 경로 꺾임점 목록 `[[x,y],...]`. 절대 좌표 핀이라 자동 포트 퍼뜨림이 꺼진다. 첫·끝 점은 `fromSide`/`toSide` 방향 규칙(AC 표)을 따라야 한다. 측정된 결함에만 쓴다 [AC Explicit via]. |
| `connections[].labelAt` | [number, number] |  | minItems `2`; maxItems `2` | 라벨 중심의 절대 좌표 핀 [코드 geometry.mjs labelPoint, AC]. |
| `connections[].labelDx` | number |  |  | 기본 라벨 위치에 더하는 가로 오프셋 [코드 labelPoint]. 진단이 준 값은 기존 값에 더해지지 않고 대체된다 [AC Repair order]. |
| `connections[].labelDy` | number |  |  | 기본 라벨 위치에 더하는 세로 오프셋 [코드 labelPoint]. |
| `connections[].labelSegment` | integer |  | min `0` | 라벨을 놓을 경로 구간 번호(0부터, 기본 1, 범위로 잘림). 점이 2개인 직선에서는 쓰이지 않는다 [코드 labelPoint]. |
| `connections[].width` | number |  | min `0.5` | 선 굵기(px). 생략 시 1.5(`emphasis`는 1.8) [코드 render-architecture.mjs:1060]. |

### 6.2 `workflow`

스윔레인(`lanes`)×논리 열(`col` 0..5)에 노드를 놓는다. 새 문서는 `schema_version: 2`로 쓰고 `meta.viewBox`를 생략한다 [AD].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `lanes` | array<object> | 필수 | minItems `1` | 스윔레인(소유 책임·런타임 경계·단계). 노드가 `lane`으로 참조 [RW Design Rules]. |
| `lanes[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 노드·그룹의 `lane`이 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `lanes[].label` | string | 필수 | minLength `1` | 레인 제목. 각 레인 위쪽 30px 제목 띠에 그려지고 노드는 그 아래에 놓인다 [RW Fixed v1 표]. |
| `lanes[].variant` | enum |  | enum: `normal` · `exception` | `normal` 기본, `exception`은 사람 대기·거부·재시도·폴백·실패 경로용 레인 [RW]. |
| `phases` | array<object> |  |  | 상위 이야기 단계(Intake·Plan·Execute·Report 등)를 첫 레인 위 헤더로 표시 [RW]. |
| `phases[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 표시용 식별자(참조처는 미확인). 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `phases[].label` | string | 필수 | minLength `1` | 단계 헤더에 보이는 이름(첫 레인 위, `fromCol..toCol` 폭) [RW]. |
| `phases[].fromCol` | integer | 필수 | min `0`; max `5` | 단계가 시작하는 열(0..5) [RW]. |
| `phases[].toCol` | integer | 필수 | min `0`; max `5` | 단계가 끝나는 열(0..5) [RW]. |
| `phases[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 단계 헤더 색 강조(`default`·`emphasis`·`security`·`dashed`) [스키마 enum, 색 매핑은 코드 `variantAccent`] |
| `groups` | array<object> |  |  | 한 레인 안에서 병렬 검사·분기 처리 등 묶음을 프레임으로 표시. 노드가 하나 이상 있어야 한다 [RW]. |
| `groups[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 표시용 식별자(참조처는 미확인). 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `groups[].label` | string | 필수 | minLength `1` | 그룹 프레임에 보이는 이름 [스키마; 표시 위치 세부는 미확인]. |
| `groups[].lane` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 그룹이 속한 레인 id [RW]. |
| `groups[].fromCol` | integer | 필수 | min `0`; max `5` | 그룹 시작 열 [RW]. |
| `groups[].toCol` | integer | 필수 | min `0`; max `5` | 그룹 끝 열 [RW]. |
| `groups[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 그룹 프레임 강조 [스키마 enum]. |
| `mainPath` | array<string> |  | minItems `2`; items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 행복 경로의 노드 id 순서. 렌더러가 연속 쌍마다 간선이 있고 왼쪽→오른쪽으로 가는지 검사한다 [RW]. |
| `semanticChecks` | object |  | minProps `1` | 소스가 증명한 도메인 사실을 계약으로 적는 선택 검사. 레이아웃 전에 평가되고 SVG는 바꾸지 않는다. 경로·라우팅 진단을 풀려고 약화하지 않는다 [RW Optional semantic checks, SR]. |
| `semanticChecks.allowedRoots` | array<string> |  | items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 들어오는 간선이 0개여도 되는 노드의 허용 목록(있으면 전체 허용 목록) [RW]. |
| `semanticChecks.allowedTerminals` | array<string> |  | items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 나가는 간선이 0개여도 되는 노드의 허용 목록 [RW]. |
| `semanticChecks.requiredEdges` | array<object> |  |  | 정확히 그 방향으로 존재해야 하는 간선 목록 [RW]. |
| `semanticChecks.requiredEdges[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 필수 간선 시작 [RW]. |
| `semanticChecks.requiredEdges[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 필수 간선 끝 [RW]. |
| `semanticChecks.requiredPaths` | array<object> |  |  | 중간 노드를 허용하되 간선 방향을 따라 도달 가능해야 하는 경로 목록 [RW]. |
| `semanticChecks.requiredPaths[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 경로 시작 [RW]. |
| `semanticChecks.requiredPaths[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 경로 끝 [RW]. |
| `nodes` | array<object> | 필수 | minItems `1` | 단계·행위 노드. `lane`+`col`로 배치하고 원시 SVG 좌표는 쓰지 않는다 [RW]. |
| `nodes[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `edges`/`flows`의 `from`·`to`, `mainPath`, `semanticChecks`, 트리의 `parent`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `nodes[].lane` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 노드가 속한 레인 id [RW]. |
| `nodes[].col` | integer | 필수 | min `0`; max `5` | 논리 열 순위(0..5). v2에서는 픽셀 중심이 측정 결과로 정해진다 [RW]. |
| `nodes[].type` | enum | 필수 | enum: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` | 노드 종류 7종. workflow 기본 범례 이름: frontend=User UI, backend=Agent logic, security=Policy, messagebus=Tool action, database=Context / trace, cloud=Cloud service, external=External system [locales/en.json `legend.workflow.*`]. |
| `nodes[].label` | string | 필수 | minLength `1` | 노드에 보이는 이름(트리는 단어 사이 줄바꿈) [RT, RW]. |
| `nodes[].sublabel` | string |  |  | 제목 아래 보조 줄(역할·프로토콜·기술명). 길어지면 정확한 역할·프로토콜만 남기고 보충 사실은 노트나 카드로 옮긴다 [AC Label repair, AD]. |
| `nodes[].tag` | string |  |  | 노드 아래쪽의 작은 보조 텍스트. 쓰면 노드 기본 높이가 52→68px, 노드 폭도 텍스트에 맞춰 늘 수 있다 [RW, AD]. |
| `nodes[].icon` | enum |  | enum: `calendar` · `clock` · `person` · `briefcase` · `flag` · `moon` · `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` · `start` · `active` · `waiting` · `decision` · `success` · `failure` · `stop` · `neutral` · `none` | 노드 모서리의 장식 아이콘. 색·의미 그룹은 `type`이 정하고 아이콘은 바꾸지 않는다. 생략하면 타입 기본값, `none`은 숨김. 일상 주제에 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`을 쓴다 [SD, AC Node icons]. |
| `nodes[].brand` | string \| object |  | minLength `1`; maxLength `2048` ; object | 실제 제품·모델·채널 정체성을 보이는 브랜드 마크. `archify brands`가 돌려준 ID 문자열 또는 `brands capture`가 만든 `{url, sha256}`. 렌더·검증은 네트워크를 쓰지 않고, 이름은 지어내지 않는다 [SR, BM]. |
| `nodes[].brand(객체형).url` | string | 필수 | pattern `^https?://`; minLength `8`; maxLength `2048` | 브랜드 사이트 URL 객체형. `archify brands capture <url> --json`이 만든 값으로, 렌더·검증 중 즉석 네트워크 캡처는 하지 않는다 [SR, BM]. |
| `nodes[].brand(객체형).sha256` | string | 필수 | pattern `^[a-f0-9]{64}$` | 캡처한 아이콘의 64자리 sha256. 내용이 바뀌면 fail-closed 진단 [SR, BM]. |
| `nodes[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `nodes[].width` | number |  | min `32` | 노드 폭. 생략하면 v2에서 92px로 시작해 라벨·sublabel·tag에 맞춰 200px까지 자란다 [AD, RW]. |
| `nodes[].height` | number |  | min `32` | 노드 높이(px). dataflow 기본 58, workflow 기본 52(tag 있으면 68) [RD, RW]. |
| `nodes[].yOffset` | number |  |  | 행/레인 기준 세로 보정. workflow에서는 레인 콘텐츠 영역 중심 기준(세 단계 스택은 -90/0/90). dataflow에서는 행 y에 더해진다 [RW, 코드 dataflow]. |
| `edges` | array<object> | 필수 |  | 단계 사이 연결. 결정·승인·프로토콜·비동기·복귀처럼 끝점이 함의하지 않는 의미를 라벨로 보존한다 [RW]. |
| `edges[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `edges[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `edges[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `edges[].label` | string |  |  | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `edges[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 선 스타일과 의미: `default` 일반, `emphasis` 주 경로(굵게), `security` 인증·정책·PII, `dashed` 비동기·배치. 소스가 그 의미를 지지할 때만 쓴다 [RD, RS, AD]. |
| `edges[].role` | enum |  | enum: `main` · `branch` · `async` · `return` · `error` | 간선의 역할 분류 `main`/`branch`/`async`/`return`/`error`. v2에서 `data-edge-role`로 출력되고 검사에 쓰인다. `return`·`error`는 뒤로 가는 경로에 대한 감점에서 제외되고, `main`이 아닌 간선은 같은 두 노드 사이 `main` 간선의 복도를 먼저 선점하지 않는다 [코드 workflow-compiler.mjs:3861, 2340, 5448]. 역할별 화면 차이는 미확인. |
| `edges[].fromSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 출발 쪽(`left`/`right`/`top`/`bottom`). 방향 계약: 첫 구간이 그 방향으로 수직·바깥을 향해야 한다. 필요한 분기·복귀·지정 기하에만 고정 [AC Executable geometry]. |
| `edges[].toSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 도착 쪽. 마지막 구간이 그 방향으로 들어와야 한다 [AC]. |
| `edges[].route` | enum |  | enum: `auto` · `straight` · `drop` · `outside-right` · `return-left` · `bottom-channel` · `up-channel` | 경로 프리셋: `auto`, `straight`, `drop`(레인 사이에서 꺾음, `bias`로 위치), `outside-right`(오른쪽 바깥 통로), `return-left`(왼쪽 바깥 통로), `bottom-channel`, `up-channel`. `via`보다 먼저 쓴다 [RW Design Rules, 코드 readablePresetVia]. |
| `edges[].via` | array<array> |  | items: minItems `2`; maxItems `2` | 경로 꺾임점 목록 `[[x,y],...]`. 절대 좌표 핀이라 자동 포트 퍼뜨림이 꺼진다. 첫·끝 점은 `fromSide`/`toSide` 방향 규칙(AC 표)을 따라야 한다. 측정된 결함에만 쓴다 [AC Explicit via]. |
| `edges[].labelAt` | [number, number] |  | minItems `2`; maxItems `2` | 라벨 중심의 절대 좌표 핀 [코드 geometry.mjs labelPoint, AC]. |
| `edges[].labelDx` | number |  |  | 기본 라벨 위치에 더하는 가로 오프셋 [코드 labelPoint]. 진단이 준 값은 기존 값에 더해지지 않고 대체된다 [AC Repair order]. |
| `edges[].labelDy` | number |  |  | 기본 라벨 위치에 더하는 세로 오프셋 [코드 labelPoint]. |
| `edges[].labelSegment` | integer |  | min `0` | 라벨을 놓을 경로 구간 번호(0부터, 기본 1, 범위로 잘림). 점이 2개인 직선에서는 쓰이지 않는다 [코드 labelPoint]. |
| `edges[].channelX` | number |  |  | 경로 프리셋이 쓰는 세로 통로의 x 좌표(절대 핀) [코드 workflow READABLE_PRESET_PIN_FIELDS, dataflow routeVia]. |
| `edges[].channelY` | number |  |  | 경로 프리셋이 쓰는 가로 통로의 y 좌표(절대 핀) [코드 같음]. |
| `edges[].bias` | number |  | min `0`; max `1` | workflow `route: drop`에서 레인 사이 간격의 어느 지점에서 꺾을지(0~1, 기본 0.5) [RW, 코드 workflow-compiler:4212]. |
| `edges[].width` | number |  | min `0.5` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |

### 6.3 `sequence`

참가자(열)와 메시지(`y`, 위→아래). `segments`/`activations`의 `from`/`to`는 참가자 id가 아니라 y 좌표.

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `participants` | array<object> | 필수 | minItems `2` | 대화 참가자(위쪽에 나열). 배열 순서가 열 순서이며 대화 역할 순으로 정렬한다. `pos`/`size`는 스키마가 거부 [AC Mode placement]. |
| `participants[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `messages`의 `from`/`to`, `activations[].participant`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `participants[].type` | enum | 필수 | enum: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` | 참가자 종류 7종(색·그룹). sequence의 기본 범례는 메시지 variant 기준이다 [스키마, RS]. |
| `participants[].label` | string | 필수 | minLength `1` | 참가자 박스 제목. 박스 폭보다 넓으면 렌더러가 진단으로 실패 [RS Design Rules]. |
| `participants[].sublabel` | string |  |  | 제목 아래 보조 줄(역할·프로토콜·기술명). 길어지면 정확한 역할·프로토콜만 남기고 보충 사실은 노트나 카드로 옮긴다 [AC Label repair, AD]. |
| `participants[].icon` | enum |  | enum: `calendar` · `clock` · `person` · `briefcase` · `flag` · `moon` · `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` · `start` · `active` · `waiting` · `decision` · `success` · `failure` · `stop` · `neutral` · `none` | 노드 모서리의 장식 아이콘. 색·의미 그룹은 `type`이 정하고 아이콘은 바꾸지 않는다. 생략하면 타입 기본값, `none`은 숨김. 일상 주제에 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`을 쓴다 [SD, AC Node icons]. |
| `participants[].brand` | string \| object |  | minLength `1`; maxLength `2048` ; object | 실제 제품·모델·채널 정체성을 보이는 브랜드 마크. `archify brands`가 돌려준 ID 문자열 또는 `brands capture`가 만든 `{url, sha256}`. 렌더·검증은 네트워크를 쓰지 않고, 이름은 지어내지 않는다 [SR, BM]. |
| `participants[].brand(객체형).url` | string | 필수 | pattern `^https?://`; minLength `8`; maxLength `2048` | 브랜드 사이트 URL 객체형. `archify brands capture <url> --json`이 만든 값으로, 렌더·검증 중 즉석 네트워크 캡처는 하지 않는다 [SR, BM]. |
| `participants[].brand(객체형).sha256` | string | 필수 | pattern `^[a-f0-9]{64}$` | 캡처한 아이콘의 64자리 sha256. 내용이 바뀌면 fail-closed 진단 [SR, BM]. |
| `participants[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `segments` | array<object> |  |  | 시간 구간을 나누는 배경 띠(단계 구분). `from`/`to`는 참가자 id가 아니라 y 픽셀 좌표. 띠 가장자리는 메시지 화살표에서 4px 이상 떨어져야 한다 [RS, AC]. |
| `segments[].from` | number | 필수 |  | 띠 시작 y 좌표 [RS]. |
| `segments[].to` | number | 필수 |  | 띠 끝 y 좌표(`to>from`) [RS]. |
| `segments[].label` | string | 필수 | minLength `1` | 띠 제목(짧게) [RS]. |
| `messages` | array<object> | 필수 | minItems `1` | 참가자 사이 메시지. 위에서 아래로 시간이 흐르고 `y`가 순서를 정한다. `from`≠`to`(자기 호출 미지원) [RS, AC]. |
| `messages[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `messages[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `messages[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `messages[].y` | number | 필수 | min `160` | 메시지의 세로 위치(최소 160, 정수 권장). 메시지 간격은 28px 이상 [RS, AC]. 노트가 있으면 다음 메시지까지 1줄 44·2줄 55·3줄 66px 이상 확보 [AD]. |
| `messages[].label` | string | 필수 | minLength `1` | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `messages[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` · `return` | 선 스타일과 의미: `default` 일반 메시지, `emphasis` 주 요청 경로, `security` 인증·동의·권한·정책 호출, `dashed` 비동기 트레이스·이벤트·로깅·비차단 작업, `return` 조용한 응답(회색) [RS Design Rules]. 범례 항목이 되고 Semantic Lens 간선 사실은 만들지 않는다 [RS Legend]. |
| `messages[].note` | string |  |  | 메시지 화살표 아래 7px 보조 텍스트(참가자 내부 동작을 이 메시지에 붙여 설명). 인접 열 간격 안에서 줄바꿈 [RS, AD]. |
| `activations` | array<object> |  |  | 참가자가 활성인 구간을 나타내는 막대 [RS]. |
| `activations[].participant` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 활성 막대를 그릴 참가자 id [RS]. |
| `activations[].from` | number | 필수 |  | 활성 시작 y [RS]. |
| `activations[].to` | number | 필수 |  | 활성 끝 y(`to>from`) [RS]. |
| `activations[].type` | enum |  | enum: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` | 활성 막대의 종류 필드(컴포넌트 타입 enum). 막대 색에 쓰일 것으로 추정되나 문서·읽은 코드에 설명이 없음 [스키마, 추론]. |

### 6.4 `dataflow`

단계(`stages`)×행(`row` 0~4) 격자 + 흐름. 노드는 `stage`/`row`, `pos`/`size`는 쓰지 않는다.

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `stages` | array<object> | 필수 | minItems `2`; maxItems `5` | 데이터 수명 단계 열(출처·수집·처리·저장·소비 등). 2~5개, 중심 x=100+stage×215 [RD, AC]. |
| `stages[].label` | string | 필수 | minLength `1` | 단계 머리글 [RD]. |
| `nodes` | array<object> | 필수 | minItems `2` | 단계×행 격자에 놓이는 데이터 노드. `pos`/`size`는 쓰지 않는다 [AC Dataflow]. |
| `nodes[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `edges`/`flows`의 `from`·`to`, `mainPath`, `semanticChecks`, 트리의 `parent`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `nodes[].type` | enum | 필수 | enum: `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` | 노드 종류 7종. 증거가 있는 저장소에는 `database`, 메모리 결과는 생성하는 `backend` 연산으로 표현 [AD]. |
| `nodes[].label` | string | 필수 | minLength `1` | 노드에 보이는 이름(트리는 단어 사이 줄바꿈) [RT, RW]. |
| `nodes[].sublabel` | string |  |  | 제목 아래 보조 줄(역할·프로토콜·기술명). 길어지면 정확한 역할·프로토콜만 남기고 보충 사실은 노트나 카드로 옮긴다 [AC Label repair, AD]. |
| `nodes[].tag` | string |  |  | 노드 아래쪽의 작은 보조 텍스트 [스키마 필드, 표시 세부는 미확인]. |
| `nodes[].icon` | enum |  | enum: `calendar` · `clock` · `person` · `briefcase` · `flag` · `moon` · `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` · `start` · `active` · `waiting` · `decision` · `success` · `failure` · `stop` · `neutral` · `none` | 노드 모서리의 장식 아이콘. 색·의미 그룹은 `type`이 정하고 아이콘은 바꾸지 않는다. 생략하면 타입 기본값, `none`은 숨김. 일상 주제에 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`을 쓴다 [SD, AC Node icons]. |
| `nodes[].brand` | string \| object |  | minLength `1`; maxLength `2048` ; object | 실제 제품·모델·채널 정체성을 보이는 브랜드 마크. `archify brands`가 돌려준 ID 문자열 또는 `brands capture`가 만든 `{url, sha256}`. 렌더·검증은 네트워크를 쓰지 않고, 이름은 지어내지 않는다 [SR, BM]. |
| `nodes[].brand(객체형).url` | string | 필수 | pattern `^https?://`; minLength `8`; maxLength `2048` | 브랜드 사이트 URL 객체형. `archify brands capture <url> --json`이 만든 값으로, 렌더·검증 중 즉석 네트워크 캡처는 하지 않는다 [SR, BM]. |
| `nodes[].brand(객체형).sha256` | string | 필수 | pattern `^[a-f0-9]{64}$` | 캡처한 아이콘의 64자리 sha256. 내용이 바뀌면 fail-closed 진단 [SR, BM]. |
| `nodes[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `nodes[].stage` | integer | 필수 | min `0` | 노드가 속한 단계(0부터, `stages` 인덱스) [RD]. |
| `nodes[].row` | integer | 필수 | min `0` | 행 번호 0~4(행 상단 y=128,242,356,470,584). 행은 병렬 스트림을 구분 [RD, AC]. |
| `nodes[].width` | number |  | min `48` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |
| `nodes[].height` | number |  | min `36` | 노드 높이(px). dataflow 기본 58, workflow 기본 52(tag 있으면 68) [RD, RW]. |
| `nodes[].yOffset` | number |  |  | 행/레인 기준 세로 보정. workflow에서는 레인 콘텐츠 영역 중심 기준(세 단계 스택은 -90/0/90). dataflow에서는 행 y에 더해진다 [RW, 코드 dataflow]. |
| `flows` | array<object> | 필수 |  | 노드 사이 데이터 이동. 모든 흐름에 비어 있지 않은 `label` 필요 [AC, AD]. |
| `flows[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `flows[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `flows[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `flows[].label` | string | 필수 | minLength `1` | 전송 방식이 아니라 데이터 자산의 이름(`clickstream`, `normalized facts` 등). 약 17 텍스트 단위 이내 권장 [RD, AD]. |
| `flows[].classification` | string |  |  | 민감도·거버넌스 맥락을 짧게(`PII touch`, `non-PII`, `approved only`, `batch`, `read-only`). 라벨 아래 줄로 그려지며 라벨 높이에 포함 [RD, 코드 label-capacity.mjs:6]. |
| `flows[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 선 스타일과 의미: `default` 일반, `emphasis` 주 경로(굵게), `security` 인증·정책·PII, `dashed` 비동기·배치. 소스가 그 의미를 지지할 때만 쓴다 [RD, RS, AD]. |
| `flows[].route` | enum |  | enum: `auto` · `straight` · `vertical-channel` · `bottom-channel` · `top-channel` | 경로 프리셋: `auto`(중간점 엘보), `straight`, `vertical-channel`(세로 통로, `channelX`), `bottom-channel`, `top-channel`(가로 통로, `channelY`) [RD, 코드 routeVia]. |
| `flows[].fromSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 출발 쪽(`left`/`right`/`top`/`bottom`). 방향 계약: 첫 구간이 그 방향으로 수직·바깥을 향해야 한다. 필요한 분기·복귀·지정 기하에만 고정 [AC Executable geometry]. |
| `flows[].toSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 도착 쪽. 마지막 구간이 그 방향으로 들어와야 한다 [AC]. |
| `flows[].channelX` | number |  |  | 경로 프리셋이 쓰는 세로 통로의 x 좌표(절대 핀) [코드 workflow READABLE_PRESET_PIN_FIELDS, dataflow routeVia]. |
| `flows[].channelY` | number |  |  | 경로 프리셋이 쓰는 가로 통로의 y 좌표(절대 핀) [코드 같음]. |
| `flows[].labelAt` | [number, number] |  | minItems `2`; maxItems `2` | 라벨 중심의 절대 좌표 핀 [코드 geometry.mjs labelPoint, AC]. |
| `flows[].labelDx` | number |  |  | 기본 라벨 위치에 더하는 가로 오프셋 [코드 labelPoint]. 진단이 준 값은 기존 값에 더해지지 않고 대체된다 [AC Repair order]. |
| `flows[].labelDy` | number |  |  | 기본 라벨 위치에 더하는 세로 오프셋 [코드 labelPoint]. |
| `flows[].labelSegment` | integer |  | min `0` | 라벨을 놓을 경로 구간 번호(0부터, 기본 1, 범위로 잘림). 점이 2개인 직선에서는 쓰이지 않는다 [코드 labelPoint]. |
| `flows[].via` | array<array> |  | items: minItems `2`; maxItems `2` | 경로 꺾임점 목록 `[[x,y],...]`. 절대 좌표 핀이라 자동 포트 퍼뜨림이 꺼진다. 첫·끝 점은 `fromSide`/`toSide` 방향 규칙(AC 표)을 따라야 한다. 측정된 결함에만 쓴다 [AC Explicit via]. |
| `flows[].width` | number |  | min `0.5` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |

### 6.5 `lifecycle`

`mainPath`(행복 경로)만 주고 나머지 기하는 렌더러가 소유한다. 레인·열·크기·라우팅 컨트롤이 없다 [RL].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `mainPath` | array<string> | 필수 | minItems `2`; items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 초기 상태에서 시작하는 행복 경로 상태 id(왼쪽→오른쪽 한 줄). 연속 쌍마다 전이가 필요. 되돌아가거나 건너뛰는 전이는 위쪽 호, 나머지 상태는 부모 아래 행 [SD, RL]. |
| `states` | array<object> | 필수 | minItems `2` | 상태 목록. 기하는 렌더러가 소유(레인·열·크기·라우팅 컨트롤 없음) [RL]. |
| `states[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `mainPath`, `transitions`의 `from`/`to`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `states[].type` | enum | 필수 | enum: `start` · `active` · `waiting` · `decision` · `success` · `failure` · `neutral` · `external` | 상태 종류 8종. `start` 초기, `active` 진행 중, `waiting` 사람·시간·입력 대기, `decision` 검토·분기(Mermaid `<<choice>>`), `success`/`failure` 좋은/나쁜 결과, `neutral` 보류·성공도 실패도 아닌 종료, `external` 외부 처리. 색과 모서리 기호가 타입을 따른다 [SD, RL, AC Lifecycle]. |
| `states[].label` | string | 필수 | minLength `1` | 상태 박스 제목(12px). 상태 폭이 140→220px로 자라 맞춘다 [RL]. |
| `states[].sublabel` | string |  |  | 제목 아래 보조 줄(역할·프로토콜·기술명). 길어지면 정확한 역할·프로토콜만 남기고 보충 사실은 노트나 카드로 옮긴다 [AC Label repair, AD]. |
| `states[].tag` | string |  |  | 상태 박스 안 8px 보조 텍스트. 텍스트가 맞도록 상태 폭이 140→220px까지 자란다 [RL Legend and state marks]. |
| `states[].icon` | enum |  | enum: `calendar` · `clock` · `person` · `briefcase` · `flag` · `moon` · `frontend` · `backend` · `database` · `cloud` · `security` · `messagebus` · `external` · `start` · `active` · `waiting` · `decision` · `success` · `failure` · `stop` · `neutral` · `none` | 노드 모서리의 장식 아이콘. 색·의미 그룹은 `type`이 정하고 아이콘은 바꾸지 않는다. 생략하면 타입 기본값, `none`은 숨김. 일상 주제에 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`을 쓴다 [SD, AC Node icons]. |
| `states[].brand` | string \| object |  | minLength `1`; maxLength `2048` ; object | 실제 제품·모델·채널 정체성을 보이는 브랜드 마크. `archify brands`가 돌려준 ID 문자열 또는 `brands capture`가 만든 `{url, sha256}`. 렌더·검증은 네트워크를 쓰지 않고, 이름은 지어내지 않는다 [SR, BM]. |
| `states[].brand(객체형).url` | string | 필수 | pattern `^https?://`; minLength `8`; maxLength `2048` | 브랜드 사이트 URL 객체형. `archify brands capture <url> --json`이 만든 값으로, 렌더·검증 중 즉석 네트워크 캡처는 하지 않는다 [SR, BM]. |
| `states[].brand(객체형).sha256` | string | 필수 | pattern `^[a-f0-9]{64}$` | 캡처한 아이콘의 64자리 sha256. 내용이 바뀌면 fail-closed 진단 [SR, BM]. |
| `states[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `states[].step` | string |  |  | 상태 위쪽 왼쪽에 작게 표시하는 단계 텍스트 [코드 render-lifecycle.mjs:79,1010]. |
| `transitions` | array<object> | 필수 |  | 상태 사이 전이. 메인 패스 전이도 모두 직접 작성한다. 복구 가능한 실패는 활성 상태로 되돌아가는 실제 전이가 필요 [AD, AC]. |
| `transitions[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `transitions[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `transitions[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `transitions[].label` | string |  |  | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `transitions[].note` | string |  |  | 전이의 부가 설명. 다른 출구와 공유될 때 라벨·노트·variant가 같아야 하며 공유시키려고 노트를 지우거나 복사하지 않는다 [RL, AC]. |
| `transitions[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 선 스타일과 의미: `default` 일반, `emphasis` 주 경로(굵게), `security` 인증·정책·PII, `dashed` 비동기·배치. 소스가 그 의미를 지지할 때만 쓴다 [RD, RS, AD]. |

### 6.6 `erd`

테이블 중심 배치(`row`/`col`). 모든 물리 컬럼을 속성에 넣는다 [AC].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | ERD 격자 배치 설정 [RE]. |
| `layout.mode` | enum | 필수 | enum: `grid` | `grid`만 허용. `row`/`col`로 배치 [RE]. |
| `layout.origin` | [number, number] |  | minItems `2`; maxItems `2` | 격자 원점. 도메인 띠 캡션이 캔버스 밖으로 나가지 않도록 패딩 이상 떨어뜨린다 [RE Domain bands]. |
| `layout.gapX` | number |  | min `0` | 셀 가로 간격. 도메인 띠 패딩보다 작으면 인접 표를 덮어 `erd/domain-not-drawn` [RE]. |
| `layout.gapY` | number |  | min `0` | 셀 세로 간격(위와 같음) [RE]. |
| `layout.entityW` | number |  | min `80` | 엔티티 박스 기본 폭(최소 80). 폭에 안 맞는 행은 조용히 잘리지 않고 진단 [RE Typography]. |
| `layout.headerH` | number |  | min `16` | 엔티티 헤더 높이(기본 30 단위) [RE Typography]. |
| `layout.rowH` | number |  | min `10` | 속성 행 높이(기본 20 단위) [RE Typography]. |
| `entities` | array<object> | 필수 | minItems `1` | 테이블(엔티티). 모든 물리 컬럼을 `attributes`에 넣는다(카드로 대체 금지). 자기 참조(`manager_id`)는 관계선이 아니라 fk 컬럼으로 [AC ERD]. |
| `entities[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 엔티티 id. 관계의 `from`/`to`와 `references`(`엔티티.속성`)가 이 값을 참조 [RE]. |
| `entities[].label` | string | 필수 | minLength `1` | 테이블 이름(헤더에 제목만 그려짐) [RE]. |
| `entities[].sublabel` | string |  |  | 그려지지 않는다. `data-node-sublabel`과 접근성 이름에만 남는다 [RE]. |
| `entities[].tag` | string |  |  | 기능 도메인 이름. 같은 tag의 테이블이 격자에서 직사각형(한 행·한 열·채운 블록)을 채우면 도메인 띠로 그려지고, 아니면 `erd/domain-not-drawn`으로 실패한다. tag가 있는 테이블은 `row`/`col` 필수 [RE Domain bands, AC ERD]. |
| `entities[].row` | integer |  | min `0`; max `12` | 격자 행(0~12). 태그가 있는 테이블은 절대 좌표에 격자 셀이 없으므로 반드시 `row`/`col` [AC ERD]. |
| `entities[].col` | integer |  | min `0`; max `12` | 격자 열(0~12) [AC ERD]. |
| `entities[].pos` | [number, number] |  | minItems `2`; maxItems `2` | 절대 좌표 `[x,y]`. 격자 셀보다 우선한다. ERD·class에서는 한정된 예외에만 쓴다 [코드 grid.mjs, RE, AC]. |
| `entities[].width` | number |  | min `80` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |
| `entities[].attributes` | array<object> |  |  | 컬럼 목록. 박스 높이는 선언된 속성 수를 따른다. 기본 `read` 수준에 보이므로 호버에 의존하지 않는다 [RE, AC]. |
| `entities[].attributes[].name` | string | 필수 | minLength `1` | 컬럼 이름 [RE]. |
| `entities[].attributes[].type` | string |  |  | SQL 타입 문자열. 별도 주석 필드가 없어 주석은 `SQL_TYPE｜중문备注` 형태로 같은 문자열에 넣는다 [AC ERD, RE]. |
| `entities[].attributes[].key` | enum \| array |  | enum: `pk` · `fk` · `uk` ; minItems `1` | 키 역할 `pk`/`fk`/`uk` 또는 목록. 조인 테이블 컬럼처럼 둘 이상이면 `["pk","fk"]`. 역할마다 배지가 그려지고 같은 역할을 두 번 써도 한 번만 그린다 [RE, AC]. |
| `entities[].attributes[].references` | string |  | pattern `^[^.]+\.[^.]+$`; minLength `3` | `fk`가 가리키는 `엔티티.속성`. 선언된 엔티티·속성과 대조해 검증된다. `fk`이면 필수 [RE, 스키마 if/then]. |
| `entities[].attributes[] (조건)` |  |  | `if key ∋ fk` → `references` 필수 | `key`에 `fk`가 있으면 `references` 필수(스키마 if/then) [스키마]. |
| `entities[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `relationships` | array<object> |  |  | 엔티티 사이 관계(까마귀발 표기). 서로 다른 두 엔티티를 연결해야 한다 [RE, AC]. |
| `relationships[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `relationships[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `relationships[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `relationships[].label` | string |  |  | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `relationships[].fromCardinality` | enum | 필수 | enum: `one` · `many` | `from` 끝의 최대 기수 `one`/`many`. 지어내지 않도록 필수. 발은 설명하는 엔티티 쪽으로 열려 화살표로 읽히지 않는다 [RE]. |
| `relationships[].toCardinality` | enum | 필수 | enum: `one` · `many` | `to` 끝의 최대 기수 [RE]. |
| `relationships[].fromOptional` | boolean |  |  | `from` 끝의 최소를 1→0으로 낮춤(선택 원 표시). `one`이면 0 또는 1, `many`면 0개 이상 [RE, AC]. |
| `relationships[].toOptional` | boolean |  |  | `to` 끝의 최소를 0으로 [RE]. |
| `relationships[].identifying` | boolean |  |  | `false`면 비식별 관계로 점선을 그린다. 이 점선은 `identifying`이 소유하며 실선이 되는 `variant`는 스키마가 거부 [RE, AC]. |
| `relationships[].variant` | enum |  | enum: `default` · `emphasis` · `security` · `dashed` | 선 스타일과 의미: `default` 일반, `emphasis` 주 경로(굵게), `security` 인증·정책·PII, `dashed` 비동기·배치. 소스가 그 의미를 지지할 때만 쓴다 [RD, RS, AD]. |
| `relationships[].fromSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 출발 쪽(`left`/`right`/`top`/`bottom`). 방향 계약: 첫 구간이 그 방향으로 수직·바깥을 향해야 한다. 필요한 분기·복귀·지정 기하에만 고정 [AC Executable geometry]. |
| `relationships[].toSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 도착 쪽. 마지막 구간이 그 방향으로 들어와야 한다 [AC]. |
| `relationships[].route` | enum |  | enum: `auto` · `straight` · `orthogonal-h` · `orthogonal-v` | 경로: `auto`, `straight`, `orthogonal-h`, `orthogonal-v` [스키마]. |
| `relationships[].via` | array<array> |  | items: minItems `2`; maxItems `2` | 경로 꺾임점 목록 `[[x,y],...]`. 절대 좌표 핀이라 자동 포트 퍼뜨림이 꺼진다. 첫·끝 점은 `fromSide`/`toSide` 방향 규칙(AC 표)을 따라야 한다. 측정된 결함에만 쓴다 [AC Explicit via]. |
| `relationships[].labelAt` | [number, number] |  | minItems `2`; maxItems `2` | 라벨 중심의 절대 좌표 핀 [코드 geometry.mjs labelPoint, AC]. |
| `relationships[].labelDx` | number |  |  | 기본 라벨 위치에 더하는 가로 오프셋 [코드 labelPoint]. 진단이 준 값은 기존 값에 더해지지 않고 대체된다 [AC Repair order]. |
| `relationships[].labelDy` | number |  |  | 기본 라벨 위치에 더하는 세로 오프셋 [코드 labelPoint]. |
| `relationships[].labelSegment` | integer |  | min `0` | 라벨을 놓을 경로 구간 번호(0부터, 기본 1, 범위로 잘림). 점이 2개인 직선에서는 쓰이지 않는다 [코드 labelPoint]. |
| `relationships[].width` | number |  | min `0.5` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |

### 6.7 `class`

타입의 격자 배치(상위 타입을 하위 위에) + 관계 6종 [RC].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | class 격자 배치 설정 [RC]. |
| `layout.mode` | enum | 필수 | enum: `grid` | `grid`(기본) [RC]. |
| `layout.origin` | [number, number] |  | minItems `2`; maxItems `2` | 격자 원점 [스키마, 세부 미확인]. |
| `layout.gapX` | number |  | min `0` | 셀 가로 간격(기본 128). 표기·라벨 공간 확보. 폭을 줄이는 컨트롤 [RC, AD]. |
| `layout.gapY` | number |  | min `0` | 셀 세로 간격(기본 84) [RC]. |
| `layout.typeW` | number |  | min `120` | 타입 박스 최소 폭(기본 180) [RC]. |
| `layout.typeMaxW` | number |  | min `160` | 자동 폭의 최대(기본 300). 긴 멤버는 이 폭까지 자란 뒤 줄바꿈 [RC, AD]. |
| `types` | array<object> | 필수 | minItems `1` | 타입(클래스·인터페이스 등). 설명에 필요한 멤버만 고르며 멤버가 없어도 된다 [AC Class]. |
| `types[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `relationships`의 `from`/`to`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `types[].label` | string | 필수 | minLength `1` | 타입 이름 [RC]. |
| `types[].kind` | enum | 필수 | enum: `class` · `abstract` · `interface` · `enum` · `record` | `class` 이름만, `abstract` «abstract»·이탤릭, `interface` «interface», `enum` «enumeration»(attributes가 상수), `record` «record». 색 계열: class·abstract=backend, interface=frontend, enum=messagebus, record=database [RC]. |
| `types[].sublabel` | string |  |  | 타입 보조 설명. Passport에서 `kind`와 함께 보인다 [RC Reader and export]. |
| `types[].row` | integer |  | min `0`; max `12` | 격자 행. 상위 타입을 하위 타입 위에 둔다 [AC]. |
| `types[].col` | number |  | min `0`; max `12` | 격자 열(소수 허용). 0.5 단위는 두 열 사이에 중앙 배치(상위 타입을 두 하위 타입 위에) [SD, RC]. |
| `types[].pos` | [number, number] |  | minItems `2`; maxItems `2` | 절대 좌표 `[x,y]`. 격자 셀보다 우선한다. ERD·class에서는 한정된 예외에만 쓴다 [코드 grid.mjs, RE, AC]. |
| `types[].width` | number |  | min `120` | 노드·엔티티·타입 박스 폭(px). 저자 값이 자동값보다 항상 우선한다 [RE, RC, AD]. 연결선이면 선 굵기(아래). |
| `types[].attributes` | array<object> |  |  | 필드 목록. `+ name: Type` 형태로 그려짐. 인터페이스 속성은 프로퍼티 계약이며 저장 상태를 뜻하지 않는다 [RC]. |
| `types[].attributes[].name` | string | 필수 | minLength `1` | 필드 이름. enum 멤버는 `name`만 가진 attribute [AC]. |
| `types[].attributes[].type` | string |  | minLength `1` | 필드 타입 문자열 [RC]. |
| `types[].attributes[].visibility` | enum |  | enum: `public` · `protected` · `package` · `private` | UML 기호: `public` +, `protected` #, `package` ~, `private` - [RC]. |
| `types[].attributes[].static` | boolean |  |  | true면 밑줄 [RC]. |
| `types[].methods` | array<object> |  |  | 메서드 목록. `+ name(parameters): Returns` 형태. `parameters`는 객체 배열이 아니라 `"msg: Message"` 같은 한 문자열 [RC, AC]. |
| `types[].methods[].name` | string | 필수 | minLength `1` | 메서드 이름 [RC]. |
| `types[].methods[].parameters` | string |  |  | 매개변수를 한 문자열로(`"msg: Message"`). 길면 `name(` 줄 끝, 매개변수 들여쓰기, `): Return`으로 줄바꿈 [RC, AC]. |
| `types[].methods[].returns` | string |  | minLength `1` | 반환 타입 문자열(`): Returns`) [RC]. |
| `types[].methods[].visibility` | enum |  | enum: `public` · `protected` · `package` · `private` | UML 기호 `+`/`#`/`~`/`-` (public/protected/package/private) [RC]. |
| `types[].methods[].static` | boolean |  |  | true면 밑줄 [RC]. |
| `types[].methods[].abstract` | boolean |  |  | true면 이탤릭(추상 메서드) [RC]. |
| `types[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |
| `relationships` | array<object> |  |  | 타입 관계. 표기는 `kind`가 소유한다 [RC]. |
| `relationships[].id` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 관계의 선택 식별자. 있으면 뷰어 링크 `#relation=<id>`가 배열 순서가 바뀌어도 유지된다. 같은 컬렉션 안에서 유일해야 한다 [SR]. |
| `relationships[].from` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 시작 노드 id(sequence는 참가자 id). 관계는 `from`→`to` 방향으로 읽는다 [RC, RE]. |
| `relationships[].to` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 연결의 끝 노드 id [RC, RE]. |
| `relationships[].kind` | enum | 필수 | enum: `dependency` · `association` · `inheritance` · `realization` · `composition` · `aggregation` | `dependency` from이 to를 사용(점선·열린 화살표), `association` from이 to를 참조(실선·열린 화살표), `inheritance` from이 to를 상속(실선·빈 삼각형), `realization` from이 인터페이스 to를 구현(점선·빈 삼각형), `composition` from이 to를 소유(채운 마름모, from 쪽), `aggregation` from이 to를 묶되 소유하지 않음(빈 마름모) [RC]. |
| `relationships[].label` | string |  |  | 관계 위에 놓이는 글자. 동작·프로토콜·방향·비동기·경계 통과 의미를 담는다. 충돌하면 삭제하지 말고 위치·간격·경로를 고치거나 문구를 줄인다. 양 끝점이 완전히 함의할 때만 생략 [AD, AC Label repair]. |
| `relationships[].fromSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 출발 쪽(`left`/`right`/`top`/`bottom`). 방향 계약: 첫 구간이 그 방향으로 수직·바깥을 향해야 한다. 필요한 분기·복귀·지정 기하에만 고정 [AC Executable geometry]. |
| `relationships[].toSide` | enum |  | enum: `left` · `right` · `top` · `bottom` | 도착 쪽. 마지막 구간이 그 방향으로 들어와야 한다 [AC]. |
| `relationships[].route` | enum |  | enum: `auto` · `straight` · `orthogonal-h` · `orthogonal-v` | 자동 경로 대신 쓰는 경로 프리셋(타입별로 값이 다름, 타입 표 참고). 먼저 `auto`를 쓰고 필요할 때만 지정한다 [AD, AC]. |
| `relationships[].via` | array<array> |  | items: minItems `2`; maxItems `2` | 경로 꺾임점 목록 `[[x,y],...]`. 절대 좌표 핀이라 자동 포트 퍼뜨림이 꺼진다. 첫·끝 점은 `fromSide`/`toSide` 방향 규칙(AC 표)을 따라야 한다. 측정된 결함에만 쓴다 [AC Explicit via]. |
| `relationships[].labelAt` | [number, number] |  | minItems `2`; maxItems `2` | 라벨 중심의 절대 좌표 핀 [코드 geometry.mjs labelPoint, AC]. |
| `relationships[].labelDx` | number |  |  | 기본 라벨 위치에 더하는 가로 오프셋 [코드 labelPoint]. 진단이 준 값은 기존 값에 더해지지 않고 대체된다 [AC Repair order]. |
| `relationships[].labelDy` | number |  |  | 기본 라벨 위치에 더하는 세로 오프셋 [코드 labelPoint]. |
| `relationships[].labelSegment` | integer |  | min `0` | 라벨을 놓을 경로 구간 번호(0부터, 기본 1, 범위로 잘림). 점이 2개인 직선에서는 쓰이지 않는다 [코드 labelPoint]. |

### 6.8 `tree`

`parent` 하나로 포함 관계를 만든다. 호출·데이터 이동에는 쓰지 않는다 [AC].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | 트리 배치 설정 [RT]. |
| `layout.direction` | enum |  | enum: `down` · `right` | `down`(기본, 얕고 균형 잡힌 분해) 또는 `right`(깊거나 잎이 많은 트리, 예: 저장소 레이아웃). `right`는 세로 스크롤 [RT, AC, AD]. |
| `layout.gapX` | number |  | min `16` | 형제 사이 간격 [RT]. |
| `layout.gapY` | number |  | min `24` | 세대 사이 간격 [RT]. |
| `layout.nodeW` | number |  | min `96` | 노드 최소 폭(기본 140) [RT]. |
| `layout.nodeMaxW` | number |  | min `120` | 노드 최대 폭(아래로 220, 오른쪽으로 200) [RT]. |
| `nodes` | array<object> | 필수 | minItems `1` | 트리 노드. 루트는 `parent`가 없는 정확히 하나. 링크는 포함 관계만 뜻하며 호출·데이터 이동·교차 가지 의존에는 쓰지 않는다 [AC Tree, RT]. |
| `nodes[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. `edges`/`flows`의 `from`·`to`, `mainPath`, `semanticChecks`, 트리의 `parent`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `nodes[].label` | string | 필수 | minLength `1` | 노드에 보이는 이름(트리는 단어 사이 줄바꿈) [RT, RW]. |
| `nodes[].parent` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 부모 노드 id(루트는 생략). 선언된 그대로 쓰며 추론하지 않는다. 없는 부모 `tree/missing-parent`, 루트 0개·여럿 `tree/root-count`, 순환 `tree/cycle` 거부. 자식은 선언 순서대로 읽는다 [RT, AC]. |
| `nodes[].sublabel` | string |  |  | 노드 제목 아래 줄. 라벨·sublabel은 단어 사이에서 줄바꿈된다 [RT Layout]. |
| `nodes[].collapsed` | boolean |  |  | true면 뷰어에서 가지를 접은 채 시작. SVG·내보내기에는 전체 트리가 그대로 있다 [RT]. |
| `nodes[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |

### 6.9 `timeline`

`at`(오프셋 포함 ISO 8601)이 위치를 정하는 시간 비례 축 [RTL].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | timeline 축 설정 [RTL]. |
| `layout.width` | number |  | min `480` | 시간축 폭(px, 기본 960) [SD, RTL]. |
| `layout.breaks` | enum |  | enum: `auto` · `none` | `auto`(기본)는 중앙 간격의 8배이고 전체 범위의 10%를 넘는 조용한 구간을 고정 폭 끊김으로 압축하고 생략된 기간을 표시, `none`은 한 비례 축 [SD, RTL]. |
| `lanes` | array<object> |  |  | 사건 출처·범주(release, monitoring, response 등) 줄. 쓰면 모든 사건이 레인 하나를 지목해야 한다 [AC, RTL]. |
| `lanes[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 노드·그룹의 `lane`이 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `lanes[].label` | string | 필수 | minLength `1` | 레인 제목. 각 레인 위쪽 30px 제목 띠에 그려지고 노드는 그 아래에 놓인다 [RW Fixed v1 표]. |
| `events` | array<object> | 필수 | minItems `1` | 시간에 놓이는 사건. 작성 순서와 무관하게 시간순으로 그려지고 동시·근접 사건은 카드가 쌓인다 [AC Timeline, RTL]. |
| `events[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 문서 안 식별자(다른 키가 참조하는 곳은 미확인). 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `events[].at` | string | 필수 | pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,3})?)?(Z\|[+-]\d{2}:\d{2})$` | ISO 8601 시각(`Z` 또는 ±HH:MM 오프셋 필수). 오프셋 없는 값은 추측하지 않고 거부, 불가능한 날짜는 `timeline/invalid-timestamp` [SD, RTL]. |
| `events[].title` | string | 필수 | minLength `1` | 카드에 보이는 사건 제목(`label`이 아니다) [AC]. |
| `events[].detail` | string |  |  | Semantic Passport에 표시되는 설명 [RTL]. |
| `events[].lane` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 사건이 놓일 레인 id. `lanes`를 쓰면 필수, 미선언 id는 `timeline/unknown-lane` [RTL]. |
| `events[].kind` | enum |  | enum: `default` · `change` · `alert` · `action` · `recovery` | 카드 색 구분 `default`/`change`/`alert`/`action`/`recovery`(범례: Event/Change/Alert/Response/Recovery). 색만 바꾼다 [AC, locales `legend.timeline.*`]. |
| `events[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |

### 6.10 `waterfall`

`start`+`end`/`duration`이 막대를 정하고 `parent`가 중첩을 만든다 [RWF].

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `layout` | object |  |  | waterfall 축 설정 [RWF]. |
| `layout.width` | number |  | min `360` | 시간축 폭(px, 기본 760) [SD, RWF]. |
| `spans` | array<object> | 필수 | minItems `1` | 한 요청·작업·에이전트 실행의 구간. 막대 위치·길이는 이 숫자에서만 나온다. 여러 루트 허용 [AC Waterfall, RWF]. |
| `spans[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 항목 식별자. 다른 span의 `parent`가 참조. 영문자로 시작하는 영문·숫자·`_`·`-`, 같은 컬렉션에서 유일 [스키마 pattern, AC]. |
| `spans[].name` | string | 필수 | minLength `1` | 왼쪽 이름 열에 보이는 구간 이름 [RWF]. |
| `spans[].start` | number | 필수 | min `0` | 공통 추적 시작점 기준 오프셋(`meta.unit`) [SD, RWF]. |
| `spans[].end` | number |  | min `0` | 끝 오프셋. `duration`과 같이 쓰면 일치해야 한다. 끝이 없으면 `status: incomplete`여야 한다 [RWF, AC]. |
| `spans[].duration` | number |  | min `0` | 지속 시간. `end`와 같이 쓰면 일치해야 함. 끝 앞선 값·불일치는 `waterfall/invalid-timing` [RWF]. |
| `spans[].parent` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` | 부모 span id. 자식은 부모 아래에 들여써서 DFS 순으로 나열. 부모·자식 시간은 포함 관계라 합산하지 않는다 [RWF]. |
| `spans[].status` | enum |  | enum: `ok` · `error` · `cancelled` · `incomplete` | `ok` 완료, `error` 오류(빨강은 이 값 전용), `cancelled` 취소, `incomplete` 끝이 기록되지 않음(점선 몸통, 마지막 기록 시점까지의 하한으로 `incomplete, ≥ X` 표시) [RWF, locales `legend.waterfall.*`]. |
| `spans[].service` | string |  | minLength `1` | 담당 서비스 이름. 서비스마다 색 계열이 나오고 (첫 등장 순, 5색 순환) 둘 이상이면 범례가 생긴다. 자식은 부모 서비스를 상속 [RWF]. |
| `spans[].detail` | string |  |  | Semantic Passport에 표시되는 설명 [스키마, 세부는 미확인]. |
| `spans[].sources` | array<object> |  | minItems `1`; maxItems `3` | 이 노드를 뒷받침하는 코드 근거 1~3개(저장소 상대 경로, 선택 줄 범위·라벨). `meta.repository`와 `--repo-root`가 있으면 git으로 검증하고 Semantic Passport·Node Finder에 표시 [SR, RA, AC]. |

## 7. explainer (`explainer.schema.json`)

JSON 초안을 직접 쓸 때의 정규 모델이다. Markdown 초안(`.archify.md`)도 이 모델로 파싱된다([explainer](../capabilities/explainer.md)). 공통 정의: `id`(`^[a-zA-Z][a-zA-Z0-9_-]*$`, 최대 100자), `text`(1~20000자), `short`(1~500자), `refs`(id 배열).

### 7.1 최상위

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `schema_version` | const | 필수 | const `1` | 1 고정 [스키마]. |
| `diagram_type` | const | 필수 | const `explainer` | `explainer` 고정 [스키마]. |
| `meta` | object | 필수 |  | 문서 메타. `id`·`title` 필수 [스키마]. |
| `meta.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 문서 id. Markdown 초안에서 생략하면 `explainer-<sha256(제목)[0:12]>` [explainer.md 스펙]. |
| `meta.title` | string | 필수 | minLength `1`; maxLength `500` | 페이지 제목(Markdown `# 제목`) [EA, 스펙]. |
| `meta.output` | string |  | pattern `^[^/]+(?:/[^/]+)*$`; minLength `1` | 결과 HTML 상대 경로(선택) [스키마]. |
| `meta.locale` | string |  | pattern `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`; maxLength `35` | 언어 태그(`@meta locale=`). 번들 카탈로그 `en`,`zh-CN`,`zh-TW`,`es`,`ko`,`ar` [EA Directive reference]. |
| `meta.quality_profile` | enum |  | enum: `standard` · `showcase` | `standard`/`showcase`(`@meta quality_profile=`). `finalize explainer`는 기본 `showcase`가 초안 값보다 우선 [explainer.md 스펙 1.3]. |
| `meta.style` | enum |  | enum: `clean` · `editorial` · `product` · `swiss` | 페이지 스타일 `clean`/`editorial`/`product`/`swiss`(`@meta style=`). 독자가 바꿀 수 있다 [EA]. |
| `meta.repository` | object |  |  | 코드 발췌(`@code`)의 저장소 정보(`@meta repo_url=`, `repo_revision=`, `repo_provider=`, `repo_link_mode=`). `--repo-root`가 있으면 origin·HEAD를 해석 [EA Inline links and sources]. |
| `meta.repository.url` | string | 필수 | minLength `1` | 저장소 origin URL [EA, native와 같은 규칙]. |
| `meta.repository.provider` | enum |  | enum: `github` · `gitee` · `gitlab` | forge 종류 [native meta.repository.provider와 같음]. |
| `meta.repository.link_mode` | enum |  | enum: `web` · `local-only` | `web`/`local-only` [native와 같음]. |
| `meta.repository.revision` | string | 필수 | pattern `^[a-fA-F0-9]{40}$` | 40자리 커밋 SHA [EA]. |
| `answer` | object | 필수 |  | 결론 영역. 페이지의 첫 내용 [EA]. |
| `answer.summary` | string | 필수 | minLength `1`; maxLength `20000` | 제목 바로 뒤 첫 문단, 질문에 대한 직접 결론 [EA Draft]. |
| `answer.reasons` | array<string> |  | maxItems `4`; items: minLength `1`; maxLength `20000` | 결론 뒤 평평한 비순서 목록, 이유 최대 4개 [EA, 스키마 maxItems 4]. |
| `answer.scope` | string |  | minLength `1`; maxLength `20000` | 결론이 성립하는 범위(`@answer scope="…"`). 값이 추정·미실측이면 여기에 밝힌다 [EA Writing]. |
| `panels` | array<object> | 필수 | minItems `1`; maxItems `500` | `##` 제목마다 하나씩 생기는 패널(질문 하나씩). 보드 배치는 페이지가 측정해 계획 [EA Panels]. |
| `panels[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 패널 id(`{#id}`). 링크·패널 교체(`patch explainer`)의 대상. 생략하면 `panel-<sha256(제목)[0:12]>` [EA, 스펙]. |
| `panels[].title` | string | 필수 | minLength `1`; maxLength `500` | 패널 제목. 구체적인 질문으로 쓴다 [EA]. |
| `panels[].span` | integer |  | min `1`; max `12` | 패널 폭 1~12열(`{#id span=7}`). 생략하면 페이지가 측정해 배치 [EA Panels and layout]. |
| `panels[].blocks` | array<object> | 필수 | minItems `1`; maxItems `500` | 패널 안 블록 목록(13종). 문단·목록·표·다이어그램 등 [EA]. |
| `panels[].blocks[].type` | enum | 필수 | enum: `prose` · `list` · `callout` · `comparison` · `facts` · `metric` · `steps` · `diagram` · `code` · `snippet` · `chart` · `diff` · `image` | 블록 종류 13종: `prose` 문단, `list` 목록, `callout` 경고·미해결 질문, `comparison` 비교표, `facts` 사실 목록, `metric` 한계 대비 수치, `steps` 다이어그램을 따라가는 단계, `diagram` native 다이어그램, `code` 저장소 발췌, `snippet` 리터럴 코드, `chart` 차트, `diff` 변경, `image` 이미지 [EA Choose the form, 스펙 C-08]. |
| `sources` | array<object> | 필수 | minItems `0`; maxItems `500` | 페이지 하단 출처 목록과 `[](source:id)` 인용의 대상. 독자가 혼자 확인하기 어려운 주장마다 `@source`를 단다 [EA Inline links and sources, Writing]. |
| `sources[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 출처 id(인용 `source:<id>`가 참조) [EA]. |
| `sources[].title` | string | 필수 | minLength `1`; maxLength `20000` | 출처 제목 [EA]. |
| `sources[].url` | string |  | minLength `1` | 출처 URL(안전한 HTTP(S)) [EA]. |
| `sources[].path` | string |  | minLength `1`; maxLength `500` | 저장소 내 파일 경로(코드 발췌용, `lines`와 함께) [EA]. |
| `sources[].lines` | [number, number] |  | minItems `2`; maxItems `2` | 줄 범위 `[시작,끝]`(초안에서는 `lines=시작:끝`) [EA]. |
| `sources[].revision` | string |  | pattern `^[a-fA-F0-9]{40}$` | 40자리 커밋 SHA [EA]. |

### 7.2 블록 13종 (`panels[].blocks[]`의 원소)

모든 블록은 `id`와 `type`(블록 종류 const)이 필수다. 경로는 `블록종류.키`다.

| 경로 | 타입 | 필수 | 값 제약·enum | 의미·언제 쓰나 |
|---|---|---|---|---|
| `prose.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `prose.type` | const | 필수 | const `prose` | 블록 종류 상수(`type`) [EA] |
| `prose.text` | string | 필수 | minLength `1`; maxLength `20000` | 평문 문단 텍스트(굵게·인라인 코드·안전한 링크만) [EA Inline links]. |
| `list.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `list.type` | const | 필수 | const `list` | 블록 종류 상수(`type`) [EA] |
| `list.items` | array<string> | 필수 | minItems `1`; maxItems `500`; items: minLength `1`; maxLength `20000` | 목록 항목들. 체크리스트는 한 목록 전체가 `- [ ]`일 때 [스펙]. |
| `list.ordered` | boolean |  |  | true면 번호 목록 [EA Directive reference]. |
| `list.checklist` | boolean |  |  | true면 체크리스트(독자가 페이지에서 체크) [EA]. |
| `callout.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `callout.type` | const | 필수 | const `callout` | 블록 종류 상수(`type`) [EA] |
| `callout.level` | enum | 필수 | enum: `note` · `warning` · `open-question` | `note`/`warning`/`open-question`(기본 note) [EA]. |
| `callout.title` | string |  | minLength `1`; maxLength `500` | 콜아웃 제목 [EA]. |
| `callout.text` | string | 필수 | minLength `1`; maxLength `20000` | 콜아웃 본문 [EA]. |
| `comparison.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `comparison.type` | const | 필수 | const `comparison` | 블록 종류 상수(`type`) [EA] |
| `comparison.labelColumn` | string |  | minLength `1`; maxLength `500` | 행 라벨 열의 머리글 [EA]. |
| `comparison.columns` | array<string> | 필수 | minItems `1`; maxItems `500`; items: minLength `1`; maxLength `500` | 비교 대상(옵션) 열 이름들 [EA]. |
| `comparison.rows` | array<object> | 필수 | minItems `1`; maxItems `500` | 비교 기준(행) 목록 [EA]. |
| `comparison.rows[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 행 id(`{#행id}`) [EA]. |
| `comparison.rows[].label` | string | 필수 | minLength `1`; maxLength `500` | 비교 기준 이름 [EA]. |
| `comparison.rows[].cells` | array<object> | 필수 | minItems `1`; maxItems `500` | 열마다의 셀 [EA]. |
| `comparison.rows[].cells[].text` | string | 필수 | minLength `1`; maxLength `20000` | 셀 내용 [EA]. |
| `comparison.rows[].cells[].assessment` | enum |  | enum: `good` · `caution` · `bad` | 셀 평가 `good`/`caution`/`bad`(`{good:Label}`). 결정에 쓰이는 셀 한두 개에만 표시 [EA]. |
| `comparison.rows[].cells[].verdict` | string |  | minLength `1`; maxLength `500` | 평가 배지 라벨(`{good:Faster}`의 Faster) [EA]. |
| `facts.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `facts.type` | const | 필수 | const `facts` | 블록 종류 상수(`type`) [EA] |
| `facts.entries` | array<object> | 필수 | minItems `1`; maxItems `500` | `키 \| 값` 사실 목록 [EA]. |
| `facts.entries[].key` | string | 필수 | minLength `1`; maxLength `500` | 사실 이름 [EA]. |
| `facts.entries[].value` | string | 필수 | minLength `1`; maxLength `20000` | 사실 값 [EA]. |
| `metric.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `metric.type` | const | 필수 | const `metric` | 블록 종류 상수(`type`) [EA] |
| `metric.label` | string | 필수 | minLength `1`; maxLength `500` | 수치 이름 [EA]. |
| `metric.value` | number |  |  | 현재 값. `value` 또는 `limit` 필요 [EA]. |
| `metric.limit` | number |  | > `0` | 기준 한계(0 초과). 한계 대비 수치를 보여 준다 [EA]. |
| `metric.unit` | string |  | minLength `1`; maxLength `500` | 단위 [EA]. |
| `metric.note` | string |  | minLength `1`; maxLength `20000` | 부가 설명 [EA]. |
| `metric.typical` | boolean |  |  | true면 대표값 표시 [EA, 세부 미확인]. |
| `steps.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `steps.type` | const | 필수 | const `steps` | 블록 종류 상수(`type`) [EA] |
| `steps.items` | array<object> | 필수 | minItems `1`; maxItems `500` | 다이어그램을 따라가는 단계들. 단계 제목은 가리키는 노드 라벨과 맞춘다 [EA]. |
| `steps.items[].id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 단계 id [EA]. |
| `steps.items[].text` | string | 필수 | minLength `1`; maxLength `20000` | 단계 제목 [EA]. |
| `steps.items[].detail` | string |  | minLength `1`; maxLength `20000` | 그 자리에서 할 일 설명 [EA]. |
| `steps.items[].target` | object |  |  | 단계가 가리키는 다이어그램 요소 [EA]. |
| `steps.items[].target.diagram` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 대상 다이어그램 블록 id [EA]. |
| `steps.items[].target.node` | string |  | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 강조할 노드 id(`route`와 배타) [EA]. |
| `steps.items[].target.route` | [number, number] |  | minItems `2`; maxItems `2` | 강조할 경로 `[from,to]`(`from~to`, `node`와 배타) [EA]. |
| `steps.items[].target.edges` | array<string> |  | items: pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 강조할 간선 id 목록 [EA]. |
| `diagram.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `diagram.type` | const | 필수 | const `diagram` | 블록 종류 상수(`type`) [EA] |
| `diagram.diagramType` | enum | 필수 | enum: `architecture` · `workflow` · `sequence` · `dataflow` · `lifecycle` · `erd` · `class` · `tree` · `timeline` · `waterfall` | native 다이어그램 타입 10종 중 하나 [EA Compact native diagrams]. |
| `diagram.spec` | object |  |  | native 다이어그램 JSON 전체. 초안에서는 약식 행이 변환되고 "inline JSON specs are for exceptional cases only" [EA]. |
| `diagram.source` | string |  | minLength `1`; maxLength `500` | (`@diagram dataflow source=파일.json`) 같은 디렉터리의 spec 파일. dataflow·lifecycle·class·waterfall 등 약식이 없는 타입에 쓴다 [EA]. |
| `diagram.nodeSources` | object |  |  | 노드 id→`@source` id 매핑. 호버하면 출처(저장소 파일은 고정 줄)를 보여 코드 투어가 된다 [EA, 스펙]. |
| `diagram.changes` | array<object> |  | minItems `1`; maxItems `500` | 비교용 변경 표시 `대상:added\|removed\|modified` [EA]. |
| `diagram.changes[].target` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 변경 대상 id [EA]. |
| `diagram.changes[].change` | enum | 필수 | enum: `added` · `removed` · `modified` | `added`/`removed`/`modified` [EA]. |
| `code.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `code.type` | const | 필수 | const `code` | 블록 종류 상수(`type`) [EA] |
| `code.source` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | `@source`의 id. 경로와 줄 범위가 있어야 하며, 코드는 Git 커밋에서 가져와 얼린다(저자가 코드를 쓰지 않음) [EA]. |
| `code.language` | string |  | minLength `1`; maxLength `500` | 코드 언어 표시 [EA]. |
| `snippet.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `snippet.type` | const | 필수 | const `snippet` | 블록 종류 상수(`type`) [EA] |
| `snippet.language` | string |  | minLength `1`; maxLength `500` | 펜스 언어 [EA]. |
| `snippet.title` | string |  | minLength `1`; maxLength `500` | 스니펫 제목(`title="…"`) [EA]. |
| `snippet.text` | string | 필수 | minLength `1`; maxLength `20000` | 리터럴 코드·명령(복사 버튼) [EA]. |
| `chart.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `chart.type` | const | 필수 | const `chart` | 블록 종류 상수(`type`) [EA] |
| `chart.title` | string |  | minLength `1`; maxLength `500` | 차트 캡션 [EA]. |
| `chart.text` | string |  | minLength `1`; maxLength `20000` | Mermaid 차트 소스(펜스) [EA Charts]. |
| `chart.data` | object |  |  | CSV/JSON 파일을 읽어 얼리는 데이터 지정(`@chart`) [EA]. |
| `chart.data.path` | string | 필수 | minLength `1`; maxLength `500` | 데이터 파일 경로(초안 디렉터리, 60행까지, 파이는 12) [EA]. |
| `chart.data.kind` | enum | 필수 | enum: `bar` · `line` · `pie` | `bar`/`line`/`pie` [EA]. |
| `chart.data.x` | string | 필수 | minLength `1`; maxLength `500` | 라벨 열 이름 [EA]. |
| `chart.data.y` | array<string> | 필수 | minItems `1`; maxItems `6`; items: minLength `1`; maxLength `500` | 값 열 이름들(시리즈, 1~6개, 파이는 첫 번째) [EA]. |
| `chart.data.unit` | string |  | minLength `1`; maxLength `500` | 단위 [EA]. |
| `diff.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `diff.type` | const | 필수 | const `diff` | 블록 종류 상수(`type`) [EA] |
| `diff.text` | string | 필수 | minLength `1`; maxLength `20000` | diff 본문(```diff 펜스) [EA]. |
| `diff.caption` | string |  | minLength `1`; maxLength `20000` | diff 캡션 [EA]. |
| `image.id` | string | 필수 | pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`; maxLength `100` | 블록 id. 문서 전체에서 유일. 단계·링크·패치가 대상으로 삼을 때만 쓰고 생략하면 `<type>-<sha256(패널id, 블록 JSON)[0:12]>` [EA Rules, 스펙] |
| `image.type` | const | 필수 | const `image` | 블록 종류 상수(`type`) [EA] |
| `image.path` | string | 필수 | minLength `1`; maxLength `500` | 초안 옆의 로컬 PNG/JPEG/GIF/WebP 경로(포함되어 전달) [EA]. |
| `image.alt` | string | 필수 | minLength `1`; maxLength `20000` | 대체 텍스트 [EA]. |
| `image.caption` | string |  | minLength `1`; maxLength `20000` | 캡션 [EA]. |
