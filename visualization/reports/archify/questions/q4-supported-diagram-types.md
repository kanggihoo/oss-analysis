---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-16
updated: 2026-11-16
sources:
  - archify/SKILL.md
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
  - archify/schemas/explainer.schema.json
  - archify/recipes/scenarios.mjs
  - archify/delta/architecture-delta.mjs
---

# [Q4] archify가 지원하는 시각화 타입

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 타입 목록·필드·enum은 `schemas/*.schema.json`을 파싱해 뽑은 것이라 `코드 확인`. 각 타입이 화면에서 어떻게 보이는지(모양, 가독성)는 이 문서에서 렌더링하지 않아 `미확인`. 타입별 배치 알고리즘은 [rendering-other-types](../capabilities/rendering-other-types.md)(draft)와 [rendering](../capabilities/rendering.md)에 있다.

## 1. 결론

native 다이어그램 타입은 **10종**이다: `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `tree`, `class`, `timeline`, `waterfall`(`SKILL.md:58-73` Type router, `schemas/` 10개 파일이 일치). 여기에 **페이지형 `explainer`**(`schemas/explainer.schema.json`의 `diagram_type`)가 하나 더 있고, 이것은 다이어그램이 아니라 설명 페이지다. Mermaid는 입력 소스일 뿐 출력 타입이 아니다. 5종(`flowchart`/`graph`, `sequenceDiagram`, `stateDiagram`, `erDiagram`, `classDiagram`)만 위 타입으로 옮기고, 표에 없는 종류(gantt, pie, mindmap 등)는 규칙이 없다(`SKILL.md:77-85`, [type-routing](../capabilities/type-routing.md) R-07).

타입은 크게 세 부류로 나뉜다.

| 부류 | 타입 | 공통점 |
|---|---|---|
| 노드·연결선 | architecture, workflow, dataflow, lifecycle, sequence | 구성요소 타입 7종(`frontend`…`external`)을 공유(lifecycle은 자체 8종), 연결선 라벨·variant |
| 구조·관계 | erd, class, tree | 열·필드·멤버 같은 내부 구조가 있는 박스, 또는 단일 부모 트리 |
| 시간 | timeline, waterfall | 시간축에 놓고 연결선이 없음. `meta.evidence`가 필수 |

## 2. 타입별 정리

"필수"는 스키마 `required`다(모든 타입 공통: `schema_version`, `diagram_type`, `meta`). `meta.title`은 전 타입 필수이고, `meta.output`은 아래 5개(architecture·workflow·sequence·dataflow·lifecycle)만 필수다.

| 타입 | 무엇을 그리나 | 최상위 필수 키 | 핵심 요소와 enum | 배치 방식(저자가 정하는 것) | 증명 예시 |
|---|---|---|---|---|---|
| `architecture` | 컴포넌트·서비스·클라우드/보안 경계·인프라 | `components` | 컴포넌트 `type` 7종, `boundaries[].kind` = `region`·`security-group`(`wraps`로 컴포넌트를 감쌈), `connections[]`(`route`: auto·straight·orthogonal-h·orthogonal-v) | `layout.mode`, 컴포넌트 `row`/`col` 또는 `pos`. 유일하게 `meta.engineering_profile: deployment-ownership` 있음 | `web-app`, `production-deployment`, `brand-aware-delivery` |
| `workflow` | 프로세스·승인 게이트·도구 호출·런북·CI/CD | `lanes`, `nodes`, `edges` | 스윔레인(`variant`: normal·exception), `phases`·`groups`, `mainPath`, `semanticChecks`, 엣지 `role` = main·branch·async·return·error, 엣지 `route` 7종 | 노드마다 `lane` + `col`. `schema_version` 1 또는 2(유일하게 2개 허용) | `agent-tool-call`, `release-delivery`, `incident-response`, `holiday-planning` |
| `sequence` | API 호출 체인·요청 수명·비동기 왕복·반환 | `participants`, `messages` | 참가자(컴포넌트 타입 7종), `segments`, `activations`, 메시지 `variant`에 `return` 있음 | 메시지마다 `y` 좌표를 저자가 준다. `meta.column_fit` | `cache-miss-request`, `async-job-roundtrip` |
| `dataflow` | 파이프라인·ETL·계보·거버넌스·소비자 | `stages`, `nodes`, `flows` | 스테이지×행 격자, 흐름 `classification`(데이터 분류 문자열), `route`(vertical-channel·bottom-channel·top-channel 등) | 노드마다 `stage`, `row`(행은 0~4, [rendering-other-types](../capabilities/rendering-other-types.md) A) | `product-analytics`, `event-stream` |
| `lifecycle` | 상태 전이·재시도·대기·종료 상태 | `mainPath`, `states`, `transitions` | 상태 `type` 8종(start·active·waiting·decision·success·failure·neutral·external). `schema_version` 3 고정, 자동 메인 패스 레이아웃 | `mainPath`(왼쪽→오른쪽 행복 경로)만 주고 나머지는 자동 | `deployment-release`, `agent-run` |
| `erd` | 테이블·엔티티·속성·PK/FK/UK·카디널리티 | `entities` | 속성 `key` = pk·fk·uk(배열 가능), fk는 `references`(`테이블.컬럼`) 필수, 관계 `fromCardinality`/`toCardinality` = one·many, `fromOptional`·`toOptional`·`identifying` | `layout.mode`, 엔티티 `row`/`col`/`pos`/`width` | `orders`, `subscription-billing` |
| `class` | 클래스·인터페이스·멤버·상속 등 관계 | `types` | `kind` = class·abstract·interface·enum·record, 관계 `kind` 6종(dependency·association·inheritance·realization·composition·aggregation), `attributes`·`methods` | `layout.mode`, 타입 `row`/`col`/`pos` | `payments`, `payment-processors` |
| `tree` | 단일 부모 포함 관계: 레포·모듈 트리, 기능 분해, 조직 | `nodes` | 노드 `parent`(루트는 생략), `collapsed`, `layout.direction` | `parent`만 주면 배치는 자동 | `payment-platform`, `archify-repository` |
| `timeline` | 사건이 언제 일어났나: 인시던트 리뷰·릴리스 이력 | `events` | 이벤트 `at`(시각 문자열), `kind` = default·change·alert·action·recovery, 선택 `lanes`, `meta.timezone`, `layout.breaks`(휴지기 압축) | 시간 비례 시계. `meta.evidence`(observed·illustrative) 필수 | `payment-incident`, `archify-dev-activity` |
| `waterfall` | 시간이 어디에 쓰였나: 요청·에이전트 실행의 span 겹침·중첩 | `spans` | span `start`와 `end` 또는 `duration`, `parent`, `status` = ok·error·cancelled·incomplete, `meta.unit` = us·ms·s(기본 ms), `meta.evidence` = measured·illustrative 필수 | 공통 시간축, `parent`로 중첩 | `checkout-request`, `example-rebuild` |
| `explainer` (페이지형) | 결론 먼저, 패널 구조의 한 장짜리 설명 페이지. 본문 안에 native 다이어그램·차트를 담는다 | `answer`, `panels`, `sources` | [explainer](../capabilities/explainer.md) | — | `delivery.explainer.json` |

공통 `meta` 키(전 타입): `title`, `locale`, `translations`, `subtitle`, `output`, `animation`(`trace`·`none`), `visual_preset`(`classic`·`signal-flow`·`blueprint`·`editorial`), `quality_profile`(`standard`·`showcase`), `repository`. (`views`는 스키마가 받지만 폐기된 키라 렌더러가 무시한다. [Q6](./q6-json-schema-reference.md)) 타입마다 일부 키가 없다: `legend`는 tree·timeline·waterfall에 없고, `viewBox`는 lifecycle·timeline·waterfall에 없다. 타입 고유 키: architecture의 `engineering_profile`, sequence의 `column_fit`, timeline의 `evidence`(observed·illustrative)·`timezone`, waterfall의 `evidence`(measured·illustrative)·`unit`.

## 3. 타입을 고르는 세 경로

1. **LLM이 라우터 표로 고른다**(`SKILL.md:58-73`). 일상 주제도 같은 10종을 쓰고 `icon`·`meta.legend` 라벨만 바꾼다.
2. **`archify guide "<시나리오>"`**: 레시피 13개의 키워드 점수로 추천한다. 레시피 분포는 architecture 3 / workflow 3 / sequence 2 / dataflow 2 / lifecycle 2 / erd 1이고 **class·tree·timeline·waterfall은 레시피가 없어 `guide`가 추천하지 않는다**(코드 확인, [type-routing](../capabilities/type-routing.md) R-18). 이 네 타입은 라우터 표와 LLM 판단으로만 선택된다.
3. **Mermaid 입력**: 위 5종만 매핑한다. `timeline`·`waterfall`·`tree`로 가는 Mermaid 매핑은 없다.

## 4. 타입별 기능 차이 (코드로 확인한 것만)

- **`delta`(변경 비교)는 architecture만 받는다.** `delta/architecture-delta.mjs:114`가 `diagram_type !== 'architecture'`이면 `delta/type-mismatch`로 실패한다(코드 확인). base/head 두 architecture를 비교하는 예시 쌍이 `examples/checkout-platform.{base,head}.architecture.json`이다.
- **연결선이 없는 타입**: timeline·waterfall(선 라우팅 없음, [rendering-other-types](../capabilities/rendering-other-types.md) 1.1 4번). 노드 링크로 이동하게 만들 때(`next.md` 5절) 이 두 타입은 노드 `<g>`가 아니라 이벤트·span 막대가 대상이다(추론).
- **`icon`·`brand`가 없는 타입**: erd(엔티티 박스 + 속성 행), class(타입 박스 + 멤버), tree(`nodes`만, 타입·아이콘·브랜드 없음). (tree 노드 키: `id`·`label`·`parent`·`sublabel`·`collapsed`·`sources`). timeline·waterfall도 `icon`·`brand`가 없다.
- **`brand` 마크와 `icon`을 받는 타입**: architecture·workflow·sequence·dataflow·lifecycle(노드 객체에 `brand`·`icon`). 렌더 전에 브랜드 마크 변형이 필요한 비동기 경로는 dataflow·lifecycle·sequence다(rendering-other-types 1.1 1번).
- **`sources`**(근거 파일 참조)는 11종 모두의 노드·항목에 있다(timeline은 `events[].sources`, waterfall은 `spans[].sources`).

## 5. 확인 못 한 것

- 타입별 시각 결과물. 예시 HTML(`examples/*-rendered.html`)은 열지 않았다.
- "일상 주제에서 어느 타입이 잘 맞는가"는 지시문(`SKILL.md:75`)만 읽었다.
- `explainer` 안의 native 다이어그램이 10종 전체를 받는지는 [explainer](../capabilities/explainer.md) 범위로 이 문서에서 다시 확인하지 않았다.
- 각 타입 README(`renderers/<type>/README.md`)에 적힌 타입별 작성 지침은 읽지 않았다.
