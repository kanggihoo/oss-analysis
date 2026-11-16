---
sha: "a7ed6fd6657da90414831d1d42cf95987188750c"
created: 2026-11-16
updated: 2026-11-16
sources:
  - archify/SKILL.md
---

# archify `SKILL.md` 한국어 번역

- **원문**: `archify/SKILL.md` (137줄, `repos/archify`의 `a7ed6fd` 기준. `a406594`와 내용이 같다. `git diff a4065941..a7ed6fd -- archify/SKILL.md`가 비어 있음을 확인했다).
- **번역 방식**: 요약하지 않고 문장 단위로 옮겼다. 명령어, 파일 경로, 필드 이름, 코드 블록은 원문 그대로 둔다. `finalize`, `candidate`, `receipt`, `gate`, `explainer`처럼 이 작업 공간 문서에서 이미 쓰는 용어는 영어로 둔다.
- **링크 표기**: 원문의 상대 링크(`references/…md#앵커`)는 이 폴더에서 열리지 않으므로 `` `경로#앵커` `` 형태의 경로 표기로 바꿨다. 경로는 `archify/` 폴더 기준이다.
- **중국어 문구**: 원문에 있는 중국어 예시(`做成一页`, `用页面讲`, 마지막 제안 문장)는 원문을 그대로 두고 괄호에 뜻을 붙였다.
- **주의**: 번역에는 오류가 있을 수 있다. 동작 규칙이 중요한 부분(명령 옵션, `--out-dir` 규칙 등)은 원문과 대조한다. 이 문서는 지시문 번역이며, 코드가 이 지시문대로 동작하는지는 확인하지 않았다.

---

## 원문 frontmatter

| 필드 | 값 |
|---|---|
| `name` | `archify` |
| `description` | 검증된 architecture, workflow, sequence, data-flow, lifecycle/state, ERD, class, tree, timeline, waterfall 다이어그램을 다크/라이트 테마, 모션, 이미지/SVG/WebM 내보내기를 갖춘 탐색 가능한 standalone HTML로 만든다. 요구사항이나 Mermaid를 받는다. 코드 기반 다이어그램에서는 저장소 근거를 조사한다. 시스템, API 호출, 파이프라인, 스키마, 이력, 타이밍, 또는 일상의 단계·부품·관계·상태를 시각화할 때 쓴다. 또한 사용자가 페이지, explainer, 공유할 답변을 요청할 때(做成一页, 用页面讲), 또는 사용자의 규칙에 `[archify explainer: ...]` 줄이 있어 선제적으로 쓰도록 했을 때, 답변을 결론 먼저, 구조화된 패널, native 다이어그램과 차트를 갖춘 한 페이지 explainer로 바꾼다. 대시보드용이 아니다. |
| `license` | Apache-2.0 |
| `metadata.version` | `"3.2"` |
| `metadata.author` | `tt-a1i` |

---

# Archify

검사를 거친 standalone HTML을, native 다이어그램 또는 질문에 답하는 한 페이지짜리 explainer로 만든다.

명령은 작업 디렉터리에서 실행한다. 사용자가 다른 위치를 지정하지 않으면, 새 artifact 요청마다 작업 디렉터리 아래에 `.archify/<type>-<slug>-<YYYYMMDD-HHMMSS>/` 폴더를 따로 만든다(로컬 시간이며 한 번만 정한다). candidate와 `<slug>.html`은 그 폴더에 두고, 수리할 때도 같은 폴더를 다시 쓴다. native 다이어그램은 `candidate.json`을 쓰고 `meta.output`은 작업 디렉터리 기준 상대 경로로 둔다. explainer는 `candidate.archify.md`와 이식 가능한(portable) 출력 파일 이름을 쓸 수 있다. 이후의 요청은 새 폴더를 쓴다. 모든 명령에서 `bin/archify.mjs`는 설치된 패키지의 절대 경로, 또는 작업 디렉터리 기준 상대 경로로 바꿔 쓴다. CLI의 입력·출력 경로는 그 디렉터리를 기준으로 해석된다.

실제 코드베이스를 native 다이어그램으로 그릴 때는, 요청된 동작을 추적하는 동안 [Repository authoring](`references/repository-authoring.md`)을 읽는다. 시스템 설명은 아래의 native 단계를 따르고, 고정된(frozen) candidate는 handoff 경로를 따른다.

## 산출물 고르기

- 사용자가 시스템, 흐름, 스키마, 이력을 그리거나 시각화해 달라고 하면 native 다이어그램과 Type router를 쓴다.
- 사용자가 답을 페이지로 달라고 하면 `explainer`를 쓴다. 예를 들면 페이지, 한 페이지, explainer, 공유할 것(“做成一页”(한 페이지로 만들어 줘), “用页面讲”(페이지로 설명해 줘), “answer with a page”)이다. 이런 요청이 없으면 텍스트로 답하거나 요청된 다이어그램을 그린다. 요청에 따라 만든 페이지는, 답변 끝에 Output 절의 한 줄짜리 모드 제안을 붙인다.
- 컨텍스트에 규칙 줄이 있으면 이 기본값이 바뀐다.
  - `[archify explainer: proactive]`: 표, 단계, 여러 절이 필요한 설명·비교·trade-off·결정·진단·리뷰·계획에는 요청이 없어도 페이지를 함께 만든다.
  - `[archify explainer: always-on]`: 결론에 이르는 모든 답변에 패널 4개 이하의 간결한 페이지도 붙이되, 열지 않고 전달하며 답변은 그 링크로 끝낸다.
  - `[archify explainer: on-demand]`: 요청받았을 때만 만들고, 모드 제안은 하지 않는다.
- 어느 모드에서든 페이지는 구조를 뒷받침할 만한 결론이 있을 때만 만든다. 잡담, 한 줄 답변, 명령 출력 원문, 텍스트만 요청한 경우에는 만들지 않는다.
- `explainer`는 결론, 이유, 범위, 보드 레이아웃, 선택적 native 다이어그램에 대해 [Explainer authoring](`references/explainer-authoring.md`)을 읽는다. 초안을 완성해서 쓴 뒤, 검증과 atomic 전달과 artifact 검사를 위해 `finalize explainer`를 실행한다. 일부 내용만 고칠 때는 panel patch를 쓴다.

## 기존 candidate 넘겨받기 (handoff)

사용자가 고정된 candidate를 주면 먼저 `finalize`를 CLI 호출 한 번으로 실행한다. 통과한 receipt가 자동 gate의 완료를 뜻한다. 시각 품질을 말하기 전에 Delivery 절의 시각 검토 권고가 있으면 따른다. 수리가 필요하면 5단계를 따른다.

`finalize`는 delivery receipt 안에 제한된 범위의 업데이트 확인을 포함한다. Update awareness를 참고한다.

## native 다이어그램 작성

일반적인 생성에는 이 경로를 쓴다. 분기 reference는 명시된 조건이 해당될 때만 읽는다.

1. 질문에 맞춰 `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `class`, `tree`, `timeline`, `waterfall` 중 하나를 고른다.
2. Type router에 있는 정확한 schema와 예제 경로를 쓰고, 그 디렉터리 목록을 따로 조회하지 않는다. [Authoring defaults](`references/authoring-defaults.md`)와 해당 모드의 예제는, 프로젝트 문서나 전체 schema와 별도의 묶음으로 한 번에 읽어서 어느 쪽도 잘리지 않게 한다. 빠진 절이 있으면 쓰기 전에 보충한다. Architecture는 해당하는 showcase 예제를 쓴다. Architecture를 제외한 모든 모드는 모드 schema와 공통 schema도 읽는다. 새 필드, enum, 제약이 있는 텍스트(특히 boundary kind)를 고르기 전에는 관련 schema 정의를 읽는다. 예제는 모양을 가르쳐 줄 뿐 사실을 알려 주지 않는다. 새 ID, 표현, 레이아웃을 쓴다. 사전 help, doctor, 시작용 validation, 임시 다이어그램, 출력 경로 목록 조회 없이 곧바로 candidate로 간다. 브랜드는 명시적으로 요청된 마크에 대해서만 조회하고, 사용자가 URL을 준 알 수 없는 마크는 [Brand marks](`references/brand-marks.md`)를 읽는다.
3. 요청된 범위와, 실제 코드베이스라면 [source evidence](`references/repository-authoring.md`)가 확보되면, 좌표를 문장으로 미리 계획하지 말고 완성된 candidate를 바로 쓴다. 좌표를 정하기 전에 Authoring defaults에 따라 Architecture의 추상화 수준과 연결된 배치를 먼저 고른다. 주요 사용자 여정과 필요한 분기를 보여 주고, 제어 역할과 동작을 바꾸는 조건을 보존하고, 실제 relationship 라벨이 들어갈 공간을 충분히 남긴다. node, relationship, source, view, card, boundary 개수는 목표치도 상한도 아니다. 먼저 자동 경로를 쓰고, 꼭 필요한 분기·복귀, 주어진 geometry, 측정된 수리일 때만 명시적 라우팅을 추가한다. 사용자가 밀도 높은 `standard`를 요청하지 않는 한 `meta.quality_profile`은 `"showcase"`로 둔다.
   - **ERD**는 table-first 레이아웃을 쓴다. 모든 물리 컬럼을 `entities[].attributes`에 보이고, SQL 타입과 소스 주석을 유지하고, 컬럼이 가진 모든 key 역할을 적는다(`key`는 역할 하나 또는 목록을 받으므로 junction 컬럼은 `["pk", "fk"]`이고, 모든 `fk` 컬럼에는 `"orders.id"` 같은 `references`도 필요하다). 컬럼을 table 대신 card로 옮겨 놓지 않는다.
   - 배치 전에 table을 기능 도메인으로 분류하고, 도메인마다 간결한 `tag`를 주고, 구성원을 격자 셀의 꽉 찬 직사각형 하나에 놓는다. 한 행, 한 열, 또는 채워진 직사각형 블록이어야 하고 L자나 대각선은 안 된다. tag가 붙은 table에는 항상 `row`/`col`이 필요하다. 절대 좌표에는 격자 셀이 없고, table이 직사각형을 채우지 않는 도메인은 band로 그릴 수 없기 때문이다. 이 경우 renderer는 도메인 이름을 보일 수 없는 다이어그램을 내보내는 대신 `erd/domain-not-drawn`을 보고한다.
   - 도메인이 여럿인 schema는 도메인 하나를 한 열(각 `tag`가 세로 줄)에 두는 것이 가장 잘 읽힌다. reader가 넓은 캔버스는 reader 폭까지 키우고 긴 캔버스는 페이지가 맞을 때까지 줄이기 때문에, 가로로 넓은 배치가 노트북 viewport 안에서 완전하고 읽기 쉽게 남는다.
   - 대략 table 8개 또는 필드 50개를 넘는 schema-first ERD는 그 자체로 밀도 높은 지도다. 첫 번째로 필드를 모두 담은 초안은 `standard`로 쓰고, 레이아웃이 여전히 읽힐 때만 올린다.
4. 완성된 첫 candidate를 쓰면 바로 `finalize`를 실행한다. 첫 gate가 showcase 검증이므로, 첫 초안이 성공하는 경우에는 별도의 사전 검증이 필요 없다. 명령이 도는 동안 candidate를 바꾸지 않는다.

   ```bash
   node bin/archify.mjs finalize <type> <candidate.json> <output.html> --quality showcase --json
   ```

   저장소 기반 candidate는 첫 초안에 근거(evidence)를 포함하고, 완전한 첫 명령을 쓴다. `node bin/archify.mjs finalize <type> <candidate.json> <output.html> --repo-root <repo-root> --quality showcase --json`. `--quality`는 `meta.quality_profile`과 맞춘다. 예를 들어 밀도 높은 첫 ERD는 `standard`다.

   통과한 receipt는 포함된 `validate`, `deliver`, strict `check`, 실제 브라우저 `browser-check` gate가 모두 통과했음을 증명한다. receipt의 compact summary를 쓰고, 별도 요청이거나 실패를 집중 진단할 때만 단독 명령을 실행한다.

5. 종료 코드가 0이 아니면 성공이 아니다. compact stdout 또는 `evidence.summaryReceipt`를 읽고, 수리 한도를 포함해 [실패한 gate를 수리](`references/delivery-contract.md#failed-finalize-and-candidate-repair`)한다. 요청된 의미와 소스 근거를 보존한다. 얽힌 Architecture route가 여럿이면 [Architecture layout repair](`references/architecture-layout-repair.md`)를 읽고, 측정된 필드나 geometry 실패는 [Authoring contract](`references/authoring-contract.md`)를 읽는다. 연결된 이웃 부분을 고치고 4단계의 `finalize` 명령을 처음부터 다시 실행한다. 한 번이라도 `browser-check`에 도달했다면 그 출력 경로가 그 evidence를 소유한다. 이후 실행마다 자기 `--out-dir <folder>/review-<n>`을 준다.

## Update awareness

`finalize`와 단독 `deliver`는 receipt에 `update`를 포함한다. 같은 전달에 대해 따로 확인을 실행하지 않는다. `update.noticeRequired`가 true이면 `references/update-awareness.md`를 읽고, quality gate가 실패한 경우에도 사용자에게 가는 최종 답변에 간결한 업데이트 안내를 한 번 남긴다. 다이어그램이 여럿인 작업은 최종 답변에서 업데이트를 한 번만 언급한다. 사용자가 명시적으로 요청할 때만 알림을 snooze하거나 무시한다. 스스로 설치하거나 업데이트하지 않는다.

첫 candidate를 쓰기 전에는 Archify 구현이나 테스트가 아니라 작성용 reference와 관련 저장소 소스를 쓴다. 집중 수리 뒤에도 진단이 조치할 수 없는 내용으로 남을 때만 Archify 구현을 살펴본다.

## Type router

| Type | 쓰는 곳 | Schema | 예제 |
|---|---|---|---|
| `architecture` | 컴포넌트, 서비스, 클라우드/보안 경계, 인프라. 일상적인 것이 무엇으로 이루어졌는지 | `schemas/architecture.schema.json` | 시스템 설명, 서비스, 라이브러리, CLI 저장소는 `examples/web-app.architecture.json`, 배포 저장소는 `examples/production-deployment.architecture.json` |
| `workflow` | 프로세스, 승인 gate, 도구 호출, runbook, CI/CD. 계획과 단계별 생활 절차 | `schemas/workflow.schema.json` | `examples/agent-tool-call.workflow.json` |
| `sequence` | API 호출 체인, 요청 lifecycle, 비동기 trace, 반환. 사람 사이의 주고받기 | `schemas/sequence.schema.json` | `examples/cache-miss-request.sequence.json` |
| `dataflow` | 파이프라인, ETL/ELT, lineage, 거버넌스, 소비자. 돈이나 문서가 어디로 가는지 | `schemas/dataflow.schema.json` | `examples/product-analytics.dataflow.json` |
| `lifecycle` | 상태 전이, 재시도, 대기와 종료 상태. 신청이나 주문이 어디에 와 있는지 | `schemas/lifecycle.schema.json` | `examples/deployment-release.lifecycle.json` |
| `erd` | table/entity, 속성, primary/foreign/unique key, 그 사이의 cardinality | `schemas/erd.schema.json` | `examples/orders.erd.json` |
| `tree` | 부모가 하나인 포함 관계. 저장소/모듈 트리, 역량이나 기능 분해, 조직도식 분해 | `schemas/tree.schema.json` | `examples/payment-platform.tree.json` |
| `class` | class, interface, 선택한 멤버, 타입 사이의 dependency/association/inheritance/realization/composition | `schemas/class.schema.json` | `examples/payments.class.json` |
| `timeline` | 언제 일어났는가. 사고 리뷰, 릴리스 이력, 소스별 lane이 있는 비례 시계 위의 타임스탬프 이벤트 | `schemas/timeline.schema.json` | `examples/payment-incident.timeline.json` |
| `waterfall` | 시간이 어디로 갔는가. 한 요청이나 agent 실행의 span 지속시간, 겹침, 중첩을 공통 시간축에 | `schemas/waterfall.schema.json` | `examples/checkout-request.waterfall.json` |

native 다이어그램 타입 중 무엇을 고를지 애매하면 `node bin/archify.mjs guide "<scenario>" --json`을 실행한다. 시나리오 증명 예제는 구조 참고용이고 그대로 베낄 사실이 아니다.

일상적인 주제는 같은 다이어그램 모드와 semantic type을 유지하되 독자에게 맞는 이름을 붙인다. [Node icons](`references/authoring-contract.md#node-icons`)처럼 일상적인 `icon` 값과 `meta.legend` 라벨을 쓴다. 빠진 개인 사실은 날짜, 금액, 규칙을 지어내지 말고 사용자에게 묻는다.

## Mermaid 입력

Mermaid는 구조와 의미를 읽는 용도로만 보고, Archify JSON을 새로 작성한다. Mermaid의 스타일을 기계적으로 렌더하지 않는다.

- `flowchart` / `graph` → `workflow`, 컴포넌트 지도이면 `architecture`.
- `sequenceDiagram` → `sequence`. participant는 semantic participant가 되고 화살표는 message가 된다.
- `stateDiagram` → `lifecycle`. 상태와 전이는 의미를 유지하고 Mermaid 스타일은 유지하지 않는다.
- `erDiagram` → `erd`. entity와 relationship 이름, key, cardinality는 의미를 유지하고 Mermaid 스타일은 유지하지 않는다.
- `classDiagram` → `class`. 타입 종류, 선택한 멤버, relationship 종류는 의미를 유지하고 Mermaid 스타일은 유지하지 않는다.

## Delivery

첫 candidate와 수리 뒤에는 위의 `finalize` 명령을 쓴다.

`finalize`는 통과하지 않은 첫 gate에서 멈춘다. compact stdout과 `<output-stem>.finalize-summary.json`은 일반적인 evidence다. 통과한 실행은 스크린샷을 만들지 않고 `visualReview: "not-requested"`를 보고한다.

통과한 Architecture receipt가 `visualReviewRecommendation.signals.resolvedCrossovers`를 보고하면, candidate를 따로 복사해 두고 node 위치와 크기만 바꾸는 한 번의 편집으로 hint를 적용한다. 모든 node, relationship(`from`과 `to` 포함), 라벨, source는 그대로 둔다. 이전 HTML이 이미 자신의 browser evidence를 소유하므로 완전한 `finalize`를 `--out-dir <folder>/review-2`와 함께 한 번 다시 실행한다. `--out-dir`는 새 browser-check와 기본 finalize receipt의 위치만 옮기고, HTML과 그 delivery receipt는 옮기지 않는다. 전달에 성공하면 요청한 출력 경로의 그 쌍을 다시 쓰고, 이전 검토 evidence는 원래 artifact 바이트에 묶인 채로 남는다. [검토 evidence 경로](`references/delivery-contract.md#a-new-candidate-at-an-existing-output-path`)를 본다. 그 실행이 실패하거나, 교차를 더 보고하거나, 같은 교차에 `signals.routesOverSuggestedBends`가 더 많아지면, 복사본을 복원해 `--out-dir <folder>/review-3`으로 finalize한다. 두 번째 배치 라운드는 시작하지 않는다. 불필요한 꺾임만 지적하는 hint는 선택 사항이다.

`layoutReviewRecommendation.action`이 `inspect-sequence-width`이면, 새로 작성한 Sequence를 넘기기 전에 [Sequence width review](`references/delivery-contract.md#sequence-width-review`)를 따른다.

새로 배치한 Architecture를 포함해 일반적인 생성에서 지각적(perceptual) 검토는 선택 사항이다. 사용자가 시각 검토를 요청했을 때, 개발 감사 때, 또는 구체적인 route/browser 우려가 있을 때, `--out-dir <folder>/visual-check`와 함께 [Optional capture evidence](`references/delivery-contract.md#optional-capture-evidence`)를 쓴다. `visualReviewRecommendation`은 참고용이다. 시각 품질을 주장하기 전에 캡처를 확인하고, 지각적 검토가 이루어지지 않았다면 어떤 검사 주장이든 자동 검사라고 한정해서 말한다.

실패한 gate, 단독 명령, provenance/recovery, 반복 전달, 내보내기, 열기에 대해서는 [Delivery contract](`references/delivery-contract.md`)를 읽는다. native 다이어그램의 recovery는 `deliver` → strict provenance `check` → `browser-check` 순서를 따르며, 캡처에는 strict provenance가 필요하다. explainer 전달은 작성 가이드에 설명된 대로 validate, deliver, check를 쓴다.

workflow viewport 넘침은 다음 레이아웃 편집 전에 [Workflow viewport repair](`references/authoring-contract.md#workflow-viewport-repair`)를 읽는다.

검증 내용을 보고할 때는 artifact 검사, 브라우저 evidence, 캡처, 실제 지각적 검토를 구분해서 말한다. 즉시 미리보기나 활성 데스크톱 루프를 명시적으로 요청한 경우는 [Optional opening](`references/delivery-contract.md#optional-opening`)을 본다.

## 선택적 viewer 기능

Live motion은 렌더된 모든 다이어그램에서 기본으로 켜져 있으므로 `meta.animation`은 쓰지 않는다. 재생은 Viewer의 Live/Still 버튼이 제어한다.

`references/viewer-runtime.md`는 사용자가 Share Cards, Route/Reach 카드, motion, deep link, 발표(presentation), 검색/포커스, 또는 그 밖의 Viewer Runtime 기능을 명시적으로 요청할 때만 읽는다.

## 설정과 fallback

스킬 패키지 안에서는 설치가 필요 없다. 설정 문제를 진단할 때는 다음으로 확인한다.

```bash
node bin/archify.mjs doctor
node bin/archify.mjs demo <output-directory>
```

native 다이어그램에서 shell을 쓸 수 없으면, architecture SVG를 `assets/template.html`에 직접 넣고, 인라인 색 대신 CSS semantic class를 쓰고, `references/delivery-contract.md`의 시각 검토 계약을 따른다. explainer는 renderer와 실제 delivery gate가 필요하다. 그것을 쓸 수 없으면 한계를 보고하고, 도움이 되면 텍스트 답을 주되 HTML을 전달했다고 주장하지 않는다.

## Output

사용자의 언어로, 결과가 허락하는 한 짧게 답한다. 내용은 다이어그램이 담고 있으므로 다이어그램 하나에는 보통 한 줄이면 된다.

- HTML에 대한 클릭 가능한 Markdown 링크로 시작한다. 파일 이름이 아니라 설명적인 제목을 쓰고, 절대 경로를 쓰며, 경로에 공백이 있으면 `<...>`로 감싼다.
- 사용자가 설명된 대상을 그리는 것이 아니라 시스템이나 코드베이스를 이해하려는 것이면, 핵심 takeaway를 한두 문장 덧붙인다. 다이어그램이 이미 분명히 보여 주는 내용을 되풀이하는 문장은 생략한다.
- 다이어그램을 읽는 방식을 바꾸는 사항은 밝힌다. 독자가 기대할 만한 부분을 일부러 뺐다면 추상화 수준이나 생략한 부분, 측정값이 아닌 예시 값, 빠진 소스 근거, 수리 중에 빠지거나 합쳐진 요청 내용이 해당한다.
- 다이어그램이 여럿이면 완료를 한 번만 보고하고, 기존 개요 페이지 링크 또는 간결한 다이어그램별 링크를 준다. 디렉터리 경로는 주지 않는다.

명령, 수리 라운드, 해시, quality profile, 검사 목록을 되풀이하지 않는다. 그것들은 receipt에 남는다. 다이어그램이 검증되었는지 물으면 “자동 검사는 통과했고 시각 검토는 하지 않았습니다.”처럼 한 줄로 답한다. receipt 링크와 상세는 재현이나 문제 해결이 목적일 때만 준다. 요청된 시각 검토를 실행하지 못했다면 밝히고, 시각 검사는 실제로 했을 때만 했다고 말한다. 필수 업데이트 안내는 Update awareness에 따라 유지한다.

예: `Created [Checkout request timing](/abs/path/checkout-timing.html). Durations are illustrative, not measured.` (`[Checkout request timing](…)`을 만들었습니다. 지속시간은 측정값이 아닌 예시입니다.)

explainer는 두세 줄로 답한다. 결론과 페이지 링크다. gate 하나가 실패했거나 글쓰기 warning이 남았을 때만 gate를 언급하고, 초안을 붙여 넣지 않는다.

요청에 따라 explainer를 만든 뒤, 컨텍스트에 `[archify explainer: ...]` 줄이 없으면, 대화당 한 번, 답변 끝에 선제 모드를 권하는 선택 사항 한 줄을 붙인다. 예: “需要的话，以后遇到解释、对比、排查这类问题，我可以主动做成这样的页面，要开启吗？” (필요하시면, 앞으로 설명·비교·원인 조사 같은 질문에는 제가 먼저 이런 페이지로 만들어 드릴 수 있습니다. 켤까요?) 사용자가 수락하면 현재 agent의 전역 규칙 파일(`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.config/devin/AGENTS.md` 등)에 `[archify explainer: proactive] Make an Archify explainer page, unasked, for explanations, comparisons, decisions, diagnoses, reviews and plans that need a table, steps or several sections.`를 추가하고 그 파일 이름을 알려 준다. 이 줄을 지우면 기능이 꺼진다. 사용자가 거절하면 같은 질문이 다시 나오지 않도록 `[archify explainer: on-demand]`를 추가해 주겠다고 제안한다.
