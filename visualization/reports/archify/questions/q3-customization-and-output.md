---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-01
updated: 2026-11-01
sources:
  - archify/SKILL.md
  - archify/references/authoring-defaults.md
  - archify/references/delivery-contract.md
  - archify/schemas/common.schema.json
  - archify/schemas/architecture.schema.json
  - archify/schemas/workflow.schema.json
  - archify/schemas/sequence.schema.json
  - archify/schemas/dataflow.schema.json
  - archify/schemas/lifecycle.schema.json
  - archify/schemas/erd.schema.json
  - archify/schemas/class.schema.json
  - archify/schemas/tree.schema.json
  - archify/schemas/timeline.schema.json
  - archify/schemas/waterfall.schema.json
  - archify/renderers/shared/output-path.mjs
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/utils.mjs
---

# [Q] 타입별·출력 위치 커스터마이징 여지

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 스키마를 파싱해 필드를 나열한 것이라 "필드가 있다"는 `코드 확인`. 각 필드가 화면에서 실제로 어떻게 보이는지는 렌더링하지 못해 `미확인`.

## 1. 질문 및 결론

- **질문**: 10개 타입마다 바꿀 수 있는 것이 무엇이고, 결과물 위치는 어떻게 정하나.
- **결론**: 색을 직접 지정하는 필드는 어느 스키마에도 없고(`color`·`fill`·`stroke` 검색 결과 없음), 모양은 **프리셋 4종 + 의미 타입(색은 타입이 정함)** 으로 정해진다. 바꿀 수 있는 것은 내용(라벨·카드·범례 문구), 언어, 프리셋, 품질 프로파일, 타입별 레이아웃 수치, 안내 뷰, 출력 경로다. 출력 경로는 **CLI 인자 > `meta.output` > `<type>.html`** 순으로 정해지고, `meta.output`은 필수이며 작업 디렉터리 안의 상대 경로여야 한다. (`코드 확인`)

## 2. 동작 설명

### 2.1 모든 타입 공통 (`meta`)

| 필드 | 값 | 효과 | 근거 |
|---|---|---|---|
| `title` | 문자열(필수, timeline·waterfall 제외) | 제목·`<title>` | `utils.mjs:190` |
| `output` | 상대 `.html` 경로(필수) | 출력 위치 기본값. 아래 2.3 | `common.schema.json`의 `portableOutputPath` |
| `locale` | `en`·`zh-CN`·`zh-TW`·`es`·`ko`·`ar`은 번들된 뷰어 문구 / 그 외는 `translations` 제공 또는 영어 폴백 | `<html lang>`, 뷰어 UI 문구 | `authoring-defaults.md`, `utils.mjs:190` |
| `translations` | 뷰어 UI 번역 | 번들에 없는 언어용 | 스키마 |
| `subtitle` | 문자열 | 부제. 비우면 안 나옴. 사용자가 요청할 때만 쓰도록 지시 | `utils.mjs:184`, `authoring-defaults.md` |
| `visual_preset` | `classic`(기본) · `signal-flow` · `blueprint` · `editorial` | `<html data-preset>`로 들어가 CSS가 바뀜. 지시문은 사용자가 요청할 때만 쓰라고 함 | `utils.mjs:190` |
| `quality_profile` | `standard` / `showcase` | 검사 엄격도. showcase는 경고도 실패 | `cli.mjs:368`, `finalize.mjs:926` |
| `animation` | `trace` / `none` | 값과 무관하게 동작이 같다(호환용). 켜고 끄기는 뷰어의 Live/Still 버튼 | `references/viewer-runtime.md` |
| `legend` | `mode`: `auto`·`all`·`hidden`, `entries.<종류>.label` | 범례 표시와 문구 | `common.schema.json` `legendMode` |
| `views` | 안내 뷰 최대 5개(`id`, `label`, `focus[]`, `note`) | 열면 지정한 노드를 강조 | `common.schema.json` `guidedViews` |
| `repository` | `url`, `revision`(40자), `provider`, `link_mode` | 근거 링크 | `repository-evidence.mjs` |
| `viewBox` | architecture·workflow·sequence·dataflow·erd·class·tree만 허용. lifecycle·timeline·waterfall은 항상 자동 계산 | 캔버스 고정. 새 도식은 생략하라고 지시 | 스키마, [rendering](../capabilities/rendering.md) |

### 2.2 타입별로 더 있는 것

| 타입 | 최상위 키 | 타입 고유 meta·layout | 비고 |
|---|---|---|---|
| architecture | `components`, `boundaries`, `connections`, `cards`, `layout` | `meta.engineering_profile`(`deployment-ownership`), `layout{cols,gapX,gapY,cellW,cellH,origin}`, 노드 `pos`·`size`·`row`·`col`·`icon`·`brand`·`tag`, 연결 `fromSide`·`toSide`·`via`·`route`·`labelAt`·`variant` | 노드 타입 7종(frontend·backend·database·cloud·security·messagebus·external), 경계 2종(region·security-group) |
| workflow | `lanes`, `phases`, `groups`, `mainPath`, `semanticChecks`, `nodes`, `edges` | schema v2 권장 | |
| sequence | `participants`, `segments`, `messages`, `activations` | `meta.column_fit`(`fixed`·`spread` 등) | |
| dataflow | `stages`, `nodes`, `flows` | 흐름 `variant`로 데이터·강조·보안·점선 구분 | |
| lifecycle | `mainPath`, `states`, `transitions` | schema v3 | |
| erd | `entities`, `relationships`, `layout` | `layout{entityW,headerH,rowH,gapX,gapY}`, 열 `key`(`pk`·`fk` 등) | 도메인별 `tag`에 `row`/`col` 필요 |
| class | `types`, `relationships`, `layout` | `layout{typeW,typeMaxW,gapX,gapY}` | |
| tree | `nodes`, `layout` | `layout.direction`(`down`·`right`), `gapX`, `gapY`, `nodeW`, `nodeMaxW` | |
| timeline | `lanes`, `events`, `layout` | `meta.evidence`, `meta.timezone`, `layout{width,breaks}` | 축 중간 휴지기 압축 선택 |
| waterfall | `spans`, `layout` | `meta.evidence`, `meta.unit`, `layout.width` | |

- 위 키는 `archify/schemas/<type>.schema.json`의 `properties`를 `python3`으로 읽어 얻었다(`실행 확인`, 스키마 값은 `코드 확인`). 타입 고유 필드의 상세 제약(예: workflow 노드 타입 enum)은 열지 않았다(`미확인`).
- 모든 타입 공통으로 **카드**(`dot`: cyan·emerald·violet·amber·rose·orange·slate 7색, `title`, `items`)가 붙는다.
- 노드의 `brand`(실제 제품 로고)는 사용자가 명시한 제품에만 쓰라고 지시한다(`authoring-defaults.md`). `archify brands` 명령으로 조회·URL 캡처가 가능하다(명령 이름만 확인).
- 색은 의미 타입이 정한다. `architecture`의 `type`이 색·범례 묶음을 정하고 `icon`은 장식일 뿐 타입·색을 바꾸지 않는다(`common.schema.json` `nodeIcon` 설명).

### 2.3 결과물 위치

우선순위(`renderers/shared/output-path.mjs:385-391`): **CLI 인자 → `meta.output` → `<type>.html`(현재 디렉터리)**.

| 경로 종류 | 규칙 | 근거 |
|---|---|---|
| CLI 인자 | 호스트의 경로 문법. 절대 경로·작업 디렉터리 밖도 허용. `.html`로 끝나야 하고 심볼릭 링크로 가리킨 끝도 `.html`이어야 함 | `output-path.mjs:412-433`, `delivery-contract.md:200-230` |
| `meta.output` | 이식 가능한 POSIX 상대 경로. 절대 경로·`..`·`\`·Windows 예약 이름·URI 금지, 작업 디렉터리 안에 머물러야 함 | 같은 문서 |
| 입력과 같은 경로 | 입력 JSON을 덮어쓰는 출력은 거부(`output/input-alias`) | `output-path.mjs:393-401` |

- `finalize`는 출력 경로를 **필수 인자**로 받는다(`archify.mjs:5888`의 `positional.length !== 3` 검사). 그래서 `finalize`를 쓰면 실제 위치는 CLI 인자가 정한다. 스키마는 그래도 `meta.output`을 필수로 요구한다(`required: ["title","output"]`, architecture·workflow·sequence에서 확인).
- **기본 폴더는 스킬의 지시문**이다: 사용자가 위치를 말하지 않으면 작업 디렉터리 아래 `.archify/<타입>-<slug>-<YYYYMMDD-HHMMSS>/`를 요청마다 새로 만들고 그 안에 후보 JSON과 HTML을 둔다(`SKILL.md:14`). 코드가 강제하는 값은 아니다.
- **함께 생기는 파일**: provenance 사이드 파일, `finalize` 영수증(`<stem>.finalize.json`, `<stem>.finalize-summary.json`), `browser-check` 영수증(`<stem>.browser-check.json`). `--out-dir`을 주면 영수증만 다른 폴더로 옮겨진다(`delivery-contract.md`의 "Automated browser evidence"). 정확한 파일 이름 규칙은 `미확인`.
- **템플릿은 바꿀 수 없다**: `loadDiagram`이 항상 `<스킬>/assets/template.html`을 읽는다(`cli.mjs:87`). `applyTemplate`은 자리표시자가 있는 다른 템플릿도 받아들이도록 쓰였지만 CLI에서 템플릿을 고르는 옵션은 찾지 못했다(`코드 확인`, 옵션 부재는 이번에 읽은 범위 기준).

### 2.4 정리: 어디까지 바꿀 수 있나

| 바꾸고 싶은 것 | 가능? | 방법 |
|---|---|---|
| 텍스트·구조·카드·범례 문구 | 가능 | JSON 수정 |
| 언어 | 가능 | `meta.locale`(6개 번들) |
| 전체 분위기 | 4가지 중 선택 | `meta.visual_preset` |
| 노드·엣지 색 | 불가(의미 타입으로만) | `type`·`variant` 선택 |
| 레이아웃 수치 | 가능(타입별 `layout`) | `layout.*`, `pos`/`size`, `via` |
| 결과 위치 | 가능 | CLI 인자 또는 `meta.output` |
| 뷰어 기능 | 코드 수정 필요 | `viewer/*`를 고치고 `scripts/generate-viewer.mjs`로 `archify/assets/template.html`을 다시 만든다(`generate-viewer.mjs:44-45` 확인) |
| 스킬 지시문(예: 기본 폴더) | 가능 | `SKILL.md`를 고치면 되지만 설치본이 레포와 같은 파일이므로 업데이트 때 덮어써질 수 있음(`미확인`) |

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 출력 우선순위 | `archify/renderers/shared/output-path.mjs:373` | `resolveOutputPath` | CLI > meta > 기본 |
| 템플릿 고정 | `archify/renderers/shared/cli.mjs:87` | `loadDiagram` | `assets/template.html` 읽기 |
| 프리셋·언어 주입 | `archify/renderers/shared/utils.mjs:190` | `applyTemplate` | `data-preset`, `lang` |
| 공통 enum | `archify/schemas/common.schema.json` | `$defs` | 프리셋·품질·타입·variant |

## 4. 검증 과정 및 실행 결과

- `python3`으로 스키마를 읽어 각 타입의 최상위 키·`meta`·`layout` 속성을 나열했다. `grep -l -i '"color"\|"fill"\|"stroke"' schemas/*.json` 결과는 없었다.
- 렌더링해 보진 못했다. 프리셋 4종의 실제 차이는 `미확인`.

## 5. 남은 질문 및 추가 조사 사항

- [ ] 프리셋 4종과 `legend.entries`가 화면에서 어떻게 달라지는지 예제 렌더링으로 확인.
- [ ] 노드 타입 enum(architecture 외 타입), `meta.views` 사용 방식.
- [ ] 영수증·provenance 파일의 정확한 이름 규칙과 `--out-dir`의 범위.
- [ ] 뷰어 기능을 끄거나 바꾸는 공식 방법이 있는지(없다면 `assets/template.html`을 직접 수정하는 수밖에 없는지).

## 6. 기능 스펙 작성 후 정정 (2026-11-02)

- `meta.views`는 스키마에만 있고 화면에 반영되지 않는다(2.1 표 참고). `meta.views`로 안내 뷰를 만들 수 있다고 쓴 이 문서의 이전 서술은 틀렸다.
- `meta.output` 필수 여부와 `viewBox` 허용 타입은 위처럼 타입마다 다르다. 영수증 파일 이름 규칙은 [finalize-orchestration](../capabilities/finalize-orchestration.md) 1.3에서 확정됐다(5절 마지막에서 두 번째 항목 해소).
- 프리셋 4종의 실제 차이는 여전히 미확인이다.
