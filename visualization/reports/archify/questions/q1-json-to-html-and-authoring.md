---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-01
updated: 2026-11-01
sources:
  - archify/SKILL.md
  - archify/references/repository-authoring.md
  - archify/references/authoring-defaults.md
  - archify/bin/archify.mjs
  - archify/bin/finalize.mjs
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/utils.mjs
  - archify/renderers/architecture/render-architecture.mjs
  - archify/recipes/scenarios.mjs
---

# [Q] JSON과 HTML은 어떻게 연결되고, 무엇을 쓸지는 누가 정하나

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 연결 부분은 `코드 확인`, "무엇을 쓸지"는 지시문을 읽은 것이라 LLM이 실제로 어떻게 판단하는지는 `미확인`

## 1. 질문 및 결론

- **질문**: LLM이 JSON을 쓰고 그것으로 HTML을 만든다고 하는데 둘이 어떻게 이어지는가. 처음에 LLM이 무엇을 어떻게 읽고 어떤 내용을 쓰기로 정하는가.
- **결론 (연결)**: 이어주는 것은 **파일 경로 하나**다. `finalize`가 `node archify.mjs deliver <type> <json> <html>`을 자식 프로세스로 실행하고, 그 안에서 `renderers/<type>/render-<type>.mjs`가 또 하나의 자식 프로세스로 JSON을 읽어 HTML을 쓴다. HTML은 **고정 템플릿의 빈칸**(제목, SVG, 카드, 언어 데이터)에 렌더러가 만든 값을 채운 것이고, 원본 JSON은 HTML 안에 들어가지 않는다. (`코드 확인`)
- **결론 (내용 결정)**: 무엇을 그릴지 정하는 것은 **LLM**이다. 코드는 그 판단을 대신하지 않고, `SKILL.md`와 `references/*.md`가 판단 기준(어떤 타입을 쓸지, 몇 단계 추상화로 그릴지, 어떤 근거를 붙일지)을 글로 준다. 코드가 확인하는 것은 결과물의 모양과 근거의 존재뿐이다. (`코드 확인` + 지시문)

## 2. 동작 설명

### 2.1 연결 — 입력 → 내부 동작 → 반환

작은 모형(실제 코드를 줄인 것):

```js
// finalize: 단계를 차례로 실행, 첫 실패에서 멈춤
for (const stage of ['deliver','check','browser-check']) {
  const r = await run(`archify.mjs ${stage} ...`);   // 자식 프로세스
  if (r.status !== 0) break;
}
// deliver 안: 임시(staging) 폴더에 렌더 → 검사 → 통과하면 교체
run(`render-<type>.mjs <json> <staging/out.html>`);
run(`check-render-output.mjs <staging/out.html>`);
commitDeliveryPair(html, provenance);
// render-<type>.mjs: JSON 읽기 → 검증 → SVG → 템플릿에 채움 → 파일 쓰기
const { diagram, template, outPath } = loadDiagram(...);
writeDiagram({ outPath, template, svg: renderSvg(), cards, ... });
```

| 모형 | 실제 위치 | 검증 |
|---|---|---|
| 단계 반복 | `archify/bin/finalize.mjs:835` (`['deliver','check','browser-check']`, explainer는 `browser-check` 생략) | 코드 확인 |
| 단계별 자식 프로세스 | `finalize.mjs:501` `defaultRunner`(`execFile(process.execPath, [cliPath, ...args])`), `finalize.mjs:514` `stageArguments` | 코드 확인 |
| 렌더러 경로 선택 | `bin/archify.mjs:2243` `rendererPath(type)` → `renderers/<type>/render-<type>.mjs` | 코드 확인 |
| 렌더러를 staging 파일 경로로 실행 | `bin/archify.mjs:4870` `runNode([renderer, specificationSnapshotPath, candidatePath])` | 코드 확인 |
| 직후 검사 | `bin/archify.mjs:4904` `check-render-output.mjs` 실행 | 코드 확인 |
| 통과 후 교체 | `bin/archify.mjs:5124` `commitDeliveryPair` | 코드 확인(호출만) |
| JSON 읽기·검증·템플릿 읽기 | `renderers/shared/cli.mjs:48-107` `loadDiagram` | 코드 확인 |
| 빈칸 채우기 | `renderers/shared/utils.mjs:150` `applyTemplate`: `<h1>`, `<title>`, SVG 슬롯, 카드 슬롯, i18n 데이터 `<script>`, 근거 데이터 `<script>` | 코드 확인 |
| 파일 쓰기 | `renderers/shared/cli.mjs:234` `writeDiagram` | 코드 확인 |
| architecture의 마지막 호출 | `renderers/architecture/render-architecture.mjs:1178-1204`(`validateArchitecture()` 후 `writeDiagram`) | 코드 확인 |

- **스키마(`schemas/*.schema.json`)가 JSON과 렌더러의 계약**이다. 스키마에서 검증용 코드가 미리 생성돼 있고(`renderers/shared/generated-validators.mjs`, 파일 크기가 커서 열어 보진 않음), 렌더러는 그 검증을 통과한 JSON만 받는다(`validator.mjs:38` `validateSchema`).
- **원본 JSON이 HTML에 없다**: 템플릿 슬롯 목록에 JSON을 넣는 칸이 없고, 예제 `examples/web-app-rendered.html`에서 `diagram_type`을 검색하면 0건이다(`실행 확인`, grep). 그래서 HTML에서 JSON을 되살릴 수 없고, 수정은 JSON을 고쳐 다시 렌더링하는 방식이다. 재렌더가 필요한 이유가 이것이다. explainer는 다른 경로이며 이 확인은 native 타입에만 해당한다.
- **JSON ↔ 산출물을 묶는 것은 provenance 파일**이다. HTML과 같은 이름 규칙의 사이드 파일에 산출물 해시를 기록하고, 이후 `check --require-provenance`가 그것을 확인한다(`bin/archify.mjs:5581` `commandCheck`, `finalize.mjs:514`). 내부 형식은 미확인.

### 2.2 "무엇을 쓸지"를 어떻게 정하나

코드에는 내용을 정하는 로직이 없다. 정하는 순서는 `SKILL.md`에 적힌 **LLM용 절차**다(`archify/SKILL.md`, 코드 확인 = 텍스트를 읽음).

1. **산출물 종류**(`SKILL.md:18-30`): "그려 달라"고 하면 native 다이어그램, "한 페이지로" 같은 요청이거나 규칙 줄이 켜져 있으면 explainer, 그 외엔 텍스트 답.
2. **타입 선택**(`SKILL.md:58-70` Type router 표): 질문에 맞는 타입 10종 중 하나. 표의 "Use for" 열이 기준이다. 애매하면 `archify guide "<시나리오>"`를 실행할 수 있다. 이 명령은 LLM이 아니라 **키워드 가중치 합산**이다(`recipes/scenarios.mjs:387` `recommendScenario`: 레시피마다 `signals: [['deployment topology', 14], …]`의 일치 점수를 더해 최고점을 고르고, 14 이상이면 high, 7 이상이면 medium). 추천은 제안일 뿐 강제가 아니다.
3. **근거를 어떻게 모으나**(`references/repository-authoring.md`): 코드 도식이면 레포의 `git rev-parse HEAD`, `git remote get-url origin`을 먼저 기록해 `meta.repository`에 고정하고, 진입점·매니페스트를 읽고 import와 호출을 따라가며 요청한 책임이 실제 입력·출력·부수효과에 닿을 때까지 읽는다. 읽으면서 파일 경로와 줄 범위를 `sources`로 남긴다. 확인 못 한 것은 "미확인"으로 곁에 적고 서비스를 지어내지 않는다. 멈추는 조건은 "요청한 책임·관계·경계가 모두 소스로 뒷받침되고 남은 불확실성이 그 범위를 못 바꿀 때"이고 노드 수 목표는 없다.
4. **무엇을 넣고 뺄지**(`references/authoring-defaults.md`): Architecture는 기본이 "주 사용자 여정 중심의 시스템 개요". 책임·제어 소유·신뢰 경계·영속성이 흐려질 때만 노드를 나눈다. 부가·선택 기능은 노트로 둔다. 요청된 책임·관계 방향·프로토콜·조건은 전부 보존한다. 노드·엣지 개수 상한은 두지 않는다.
5. **작성과 첫 실행**(`SKILL.md:32-46`): 예제를 "모양만 배우고 사실은 베끼지 않는다"는 전제로 읽고 후보를 한 번에 쓴 뒤 곧바로 `finalize`를 돌린다. 미리 검증하거나 임시 다이어그램을 만들지 않는다.

### 2.3 사용자 입력 형태별 차이

| 입력 | 처리 | 근거 |
|---|---|---|
| 시스템 설명(레포 없음) | 설명을 바탕으로 JSON 작성. 모르는 개인 정보는 묻는다 | `SKILL.md:58-85` (지시문) |
| 실제 레포 | 위 3번대로 읽고 `sources` + `--repo-root`로 전달 | `repository-authoring.md` |
| Mermaid | 모양만 보고 JSON을 새로 쓴다. 기계 변환 없음 | `SKILL.md`의 "Mermaid input" 절 |
| 이미 쓴 후보(JSON) | 읽지 않고 `finalize`부터 실행 | `SKILL.md`의 "Existing candidate handoff" |

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 진입 | `archify/bin/archify.mjs:5888` | `commandFinalize` | `finalize` 인자를 받아 `runFinalize` 호출 |
| 단계 실행 | `archify/bin/finalize.mjs:835` | `runFinalize` | 단계별 자식 프로세스 실행·영수증 |
| 렌더러 선택 | `archify/bin/archify.mjs:2243` | `rendererPath` | 타입 → 렌더러 파일 |
| 입력 로드 | `archify/renderers/shared/cli.mjs:48` | `loadDiagram` | 읽기·검증·템플릿 로드·출력 경로 결정 |
| 템플릿 채움 | `archify/renderers/shared/utils.mjs:150` | `applyTemplate` | 슬롯 치환 |
| 타입 추천 | `archify/recipes/scenarios.mjs:387` | `recommendScenario` | 키워드 점수 |

## 4. 검증 과정 및 실행 결과

- 실행한 명령(읽기 전용): `grep -c "diagram_type" archify/examples/web-app-rendered.html`, `diff -rq ~/.agents/skills/archify <repo>/archify`.
- 결과: 앞은 `0`, 뒤는 차이 없음(출력 없음).
- 설치된 스킬(레포와 바이트 동일)로 `finalize`를 두 번 실행해 통과했다(architecture, explainer). 위 흐름은 코드를 읽어 정리한 것이고, 실행은 "통과한다"까지만 확인했다. 단계별 자식 프로세스 호출을 추적하진 않았다(`코드 확인` + 통과 `실행 확인`).

## 5. 남은 질문 및 추가 조사 사항

- [ ] 실제 LLM이 `SKILL.md` 절차를 어느 정도 따르는지(예: 한 번에 쓰고 곧바로 `finalize`) 샘플 실행으로 확인(`미확인`).
- [ ] 타입별로 JSON 필드 → SVG 변환이 어떻게 다른지(architecture 외 9개 렌더러 미확인).
- [ ] provenance 파일의 정확한 형식과 이름 규칙.

## 6. 기능 스펙 작성 후 정정 (2026-11-02)

- `browser-check`는 자식 프로세스가 아니라 `finalize` 안에서 실행된다(`execution: in-process`, [finalize-orchestration](../capabilities/finalize-orchestration.md)). 자식 프로세스는 `deliver`와 `check`뿐이다.
- `guide`가 추천하는 타입은 6종뿐이다(architecture·workflow·sequence·dataflow·lifecycle·erd). class·tree·timeline·waterfall은 추천 대상이 아니다 ([type-routing](../capabilities/type-routing.md) R-18).
- `meta.output`은 5개 타입(architecture·workflow·sequence·dataflow·lifecycle)에서만 필수다. 지시문(`authoring-defaults.md:39`)은 모두 필수라고 적는다.
- "코드가 확인하는 것은 결과물의 모양과 근거의 존재뿐"이라는 결론은 `실행 확인`으로 올라갔다. 근거는 [input-validation](../capabilities/input-validation.md) T-35.
