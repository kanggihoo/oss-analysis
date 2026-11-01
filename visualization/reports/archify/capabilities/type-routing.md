---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/SKILL.md
  - archify/bin/archify.mjs
  - archify/recipes/scenarios.mjs
  - archify/schemas/common.schema.json
depends:
  - artifact-choice.md
status: ready
reimplementation: 미실행
---

# 타입 선택과 `guide`

> 네이티브 다이어그램으로 가기로 한 요청에서 10종 타입 중 하나를 고르고(Type router 표, Mermaid 매핑), 애매하면 `guide "<시나리오>" [--json] [--lang en|zh]`가 키워드 점수로 레시피 하나와 신뢰도를 돌려준다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. `artifact-choice.md`의 R-02로 native 다이어그램이 정해졌다.
2. LLM이 질문의 성격으로 10종 중 하나를 고른다(R-01~R-03). 입력이 Mermaid면 먼저 종류를 타입으로 옮기되 JSON은 새로 쓴다(R-06).
3. 애매하면 `archify guide "<시나리오>" --json`을 실행한다(R-04). CLI가 쿼리를 정규화하고(R-12) 레시피 13개의 키워드 점수를 계산해(R-13) 승자·신뢰도·대안 2개를 JSON이나 텍스트로 출력한다(R-14~R-17).
4. LLM은 추천을 참고해 타입과 예시를 정한다. `guide`는 강제하지 않는다(R-19).

### 1.2 범위·통합 지점 [필수]
- 제공: 타입 라우팅 표와 Mermaid 매핑(지시문), `guide` 명령(코드).
- 제외: 타입별 스키마·작성(`authoring-contract.md`와 행 5), 렌더링(행 6), `layout-repair` 레시피가 가리키는 수리 절차(행 9), 레시피 `prompt`로 시작하는 웹 가이드·시작 페이지 빌드(`scripts/build-guide.mjs`, `build-start.mjs`는 같은 레시피 데이터를 쓰는 부속).
- 외부 의존: 없음. `guide`는 파일·네트워크·레포를 읽지 않고 쓰지도 않는다(R-19).
- 소유 상태·부작용: 없음. 출력은 stdout, 오류는 stderr와 종료 코드뿐이다.

### 1.3 인터페이스와 데이터 의미 [필수]
**명령** `archify guide [scenario or question] [--json] [--lang en|zh]` (원문 이름 그대로, C-08·C-09)

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 위치 인자 | string 0개 이상 | 공백으로 이어 붙여 앞뒤를 자른 것이 쿼리 |
| `--json` | flag | JSON 출력(2칸 들여쓰기) |
| `--lang en\|zh`, `--lang=en\|zh` | enum | 출력 언어를 고정. 그 외 값이나 값 없음은 오류(R-08) |
| 알 수 없는 `--옵션` | — | `Unknown guide option "--x".`를 stderr에 쓰고 종료 코드 2 |
| 목록 결과(쿼리 없음) | `{ok:true, mode:"list", lang, recipes[]}` | `lang`은 `--lang` 또는 `"en"`(자동 감지 없음) |
| 추천 결과 | `{ok:true, mode:"recommendation", lang, query, confidence, matchedSignals[], recommendation, alternatives[]}` | `query`는 정규화 전 쿼리 문자열. 점수(`score`)는 `alternatives[]` 항목에만 있고 승자에는 없다 |
| 레시피 객체 | `{id, type, proof, presentation:{preset, motion}, title, question, summary, useWhen, avoidWhen, include[], prompt}` | 선택된 언어의 문구. `proof`는 `examples/`의 증명 예시 이름 |
| 레시피 13개 | 아래 표 | 정의 순서가 동점 해소 순서다 |

| 순서 | id | type | preset · motion |
|---|---|---|---|
| 1 | `system-overview` | architecture | classic · static |
| 2 | `deployment-ownership` | architecture | blueprint · trace |
| 3 | `agent-tool-call` | workflow | signal-flow · trace |
| 4 | `delivery-workflow` | workflow | classic · trace |
| 5 | `incident-runbook` | workflow | signal-flow · trace |
| 6 | `api-request` | sequence | classic · trace |
| 7 | `async-roundtrip` | sequence | signal-flow · trace |
| 8 | `data-lineage` | dataflow | classic · trace |
| 9 | `event-stream` | dataflow | signal-flow · trace |
| 10 | `object-lifecycle` | lifecycle | classic · trace |
| 11 | `deployment-lifecycle` | lifecycle | signal-flow · trace |
| 12 | `database-schema` | erd | classic · static |
| 13 | `layout-repair` | architecture | classic · static |

신호(키워드, 가중치) 목록은 레시피마다 영어·중국어 쌍으로 있고 C-06이 원본이다.

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 네이티브 다이어그램 요청 | 타입은 `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `class`, `tree`, `timeline`, `waterfall` 10종 중 질문으로 고른다. 사용처는 C-01 표가 원본이다 | 코드 확인(지시문) |
| R-02 | 타입이 정해짐 | 스키마는 `schemas/<type>.schema.json`, 예시는 C-01 표의 경로. Architecture는 시스템·라이브러리·CLI 레포에 `web-app`, 배포 레포에 `production-deployment` 예시. 예시는 형태 참고용이지 사실이 아니다 | 코드 확인(지시문) |
| R-03 | 타입이 둘 이상 맞을 수 있음 | R-04로 간다 | 코드 확인(지시문) |
| R-04 | 타입 선택이 애매함 | `node bin/archify.mjs guide "<scenario>" --json`을 실행한다 | 코드 확인(지시문) |
| R-05 | 일상 주제(예: 휴일 계획) | 같은 10종 타입을 그대로 쓰고 `icon`·`meta.legend` 라벨로 독자용 이름을 붙인다. 빠진 개인 사실(날짜·금액·규칙)은 지어내지 않고 사용자에게 묻는다 | 코드 확인(지시문) |
| R-06 | 입력이 Mermaid | 위상과 의미만 읽고 JSON을 새로 쓴다. 스타일을 기계적으로 옮기지 않는다. 매핑은 C-02: `flowchart`/`graph`는 `workflow`(구성요소 지도면 `architecture`), `sequenceDiagram`은 `sequence`, `stateDiagram`은 `lifecycle`, `erDiagram`은 `erd`, `classDiagram`은 `class` | 코드 확인(지시문) |
| R-07 | Mermaid 종류가 R-06 표에 없음(gantt, pie, journey, mindmap, timeline, gitGraph 등) | 원본에 규칙이 없다. 코드에도 Mermaid를 읽는 부분이 없다(생성 검증기 `generated-validators.mjs`의 스키마 문자열 외 `.mjs` 0건). `stateDiagram`의 세부 매핑(`[*] -->`는 `mainPath` 첫 상태, `<<choice>>`는 `decision`, 복합 상태는 평탄화)은 `references/authoring-contract.md:520-532`에 있고 지시문이다. 재구현도 표 밖의 종류에 매핑을 만들지 않는다 | 코드 확인(규칙 부재) |
| R-08 | `guide`의 잘못된 옵션 | 알 수 없는 `--x`, `--lang` 값이 `en`·`zh`가 아니거나 없음 → stderr 메시지와 종료 코드 2. 메시지는 `Unknown guide option "--x".` 또는 `--lang must be "en" or "zh".` | 실행 확인(`--bogus`, `fr`), 값 없음은 코드 확인 |
| R-09 | 쿼리가 비었음(인자 없음, 공백뿐 포함) | 목록 모드. `--json`이면 목록 결과(1.3), 아니면 `formatScenarioList` 텍스트. 종료 코드 0 | 실행 확인(인자 없음), 공백뿐인 경우는 코드 확인 |
| R-10 | `recipes/scenarios.mjs`를 불러오지 못함 | `Could not load the scenario recipe guide: <원인>`을 stderr에 쓰고 종료 코드 1 | 코드 확인(실행 안 함) |
| R-11 | 추천 모드의 언어 | `--lang`이 `en`·`zh`면 그 값. 아니면 쿼리에 한자(U+3400–U+9FFF)가 있으면 `zh`, 없으면 `en`. 언어는 출력 문구만 바꾸고 점수에는 영향이 없다(신호는 항상 두 언어 모두 검사) | 실행 확인 |
| R-12 | 정규화 | 쿼리와 신호 모두 NFKC → 소문자 → 연속 공백·밑줄을 공백 하나로 → 앞뒤 자름(C-04) | 코드 확인, 일부 실행 확인(`database_schema`) |
| R-13 | 점수 계산 | 정규화한 쿼리가 비면 점수 0. 쿼리가 레시피 `id` 또는 `id`의 `-`를 공백으로 바꾼 것과 같으면 점수 100, `matchedSignals`는 `[id]`. 그 외에는 각 신호의 정규화 문자열이 쿼리의 부분 문자열이면 가중치를 더하고(단어 경계 없음, 신호 항목마다 한 번이라 같은 문자열이 두 항목이면 두 번) 일치한 신호의 원문을 정의 순서로 모은다(C-05) | 실행 확인 |
| R-14 | 순위 | 점수 내림차순, 동점은 정의 순서(앞선 레시피가 이김). 최고점이 0이면 승자는 1번 `system-overview`, 점수 0, `matchedSignals` `[]` | 실행 확인 |
| R-15 | 신뢰도 | 승자 점수 ≥ 14 `high`, ≥ 7 `medium`, 그 미만(0 포함) `low`. 일치가 없어도 종료 코드는 0이다 | 실행 확인 |
| R-16 | 대안 | 승자를 뺀 점수 > 0 레시피를 순위대로 최대 2개, 각각 레시피 객체에 `score`를 더해 담는다. 없으면 `[]` | 실행 확인 |
| R-17 | 텍스트 출력 | `formatScenarioRecommendation`(C-07): `Recommendation: <title>  [<type>]`, `Confidence`, `Question answered`, 빈 줄, `Use when`, `Avoid when`, `Must include`(`; `로 연결), `Presentation: <preset> · <motion>`, 빈 줄, `Copy-ready prompt:`와 `prompt`, 대안이 있으면 `Other possible fits: <title> [<type>] · ...`. 라벨은 `zh`면 중국어 | 실행 확인(`en` 한 건), 나머지 코드 확인 |
| R-18 | 레시피 커버리지 | 레시피는 architecture 3, workflow 3, sequence 2, dataflow 2, lifecycle 2, erd 1개. `class`, `tree`, `timeline`, `waterfall`은 레시피가 없어 `guide`가 추천하지 않는다 | 실행 확인(분포 덤프) |
| R-19 | `guide` 실행 전반 | 읽기 전용이다. 파일·레포·네트워크를 쓰거나 읽지 않고, 추천은 참고일 뿐 이후 단계가 따르는지 검사하지 않는다 | 코드 확인(`commandGuide` 전체) |

- 불변식: 같은 쿼리와 `--lang`이면 출력은 항상 같다(시간·환경 입력 없음, R-13~R-16). 목록 순서와 동점 해소는 `RAW_RECIPES` 정의 순서에 묶인다.
- 알려진 특이점(원본 동작이므로 재현 대상): (a) 부분 문자열 일치라 `via`(`layout-repair`, 7점)가 `api gateway via cdn`에서 걸려 `layout-repair`가 `medium`으로 이긴다(T-12). (b) `async-roundtrip`의 `webhook`이 영어·중국어 목록에 모두 있어 쿼리에 `webhook`이 있으면 20점이고 `matchedSignals`에 두 번 나온다(T-11). (c) `layout-repair`의 `type`은 `architecture`지만 그 `avoidWhen`은 "새 다이어그램 타입 선택에는 쓰지 말라"고 한다. 추천 타입이 기존 다이어그램의 타입을 뜻하지 않는다.
- 미결정: 없음.
- 확인 한계: 에이전트가 R-04에서 실제로 `guide`를 실행하는지, 추천을 따르는지는 미확인. 라우터 표와 Mermaid 매핑에서 LLM이 어느 타입을 고르는지는 실행하지 않았다. 레시피 문구(`prompt` 등)와 중국어 신호 전체는 C-06이 원본이고 이 스펙은 점수 계산에 필요한 규칙만 푼다. `guide` 실행은 설치본(`~/.claude/skills/archify`, 레포 `archify/`와 `diff -rq` 동일)으로 했다.

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/SKILL.md:58-73` `## Type router` | 타입별 용도·스키마·예시 경로 표와 `guide` 호출 문구 | R-01~R-04 |
| C-02 | `archify/SKILL.md:77-85` `## Mermaid input` | Mermaid 종류 → 타입 매핑 | R-06, R-07 |
| C-03 | `archify/recipes/scenarios.mjs:331-333` `detectGuideLanguage` | 한자 유무로 언어 감지 | R-11 |
| C-04 | `archify/recipes/scenarios.mjs:350-364` `normalized`, `localized` | 정규화 규칙과 레시피 객체 모양 | R-12, 1.3 |
| C-05 | `archify/recipes/scenarios.mjs:370-405` `scoreRecipe`, `recommendScenario` | 점수·순위·신뢰도·대안·결과 객체 | R-11, R-13~R-16 |
| C-06 | `archify/recipes/scenarios.mjs` 각 레시피의 `signals:` 줄(9, 30, 55, 76, 97, 122, 143, 164, 189, 214, 235, 260, 281-290) | 레시피별 신호와 가중치 | R-13 |
| C-07 | `archify/recipes/scenarios.mjs:407-446` `formatScenarioList`, `formatScenarioRecommendation` | 텍스트 출력 형식과 영·중 라벨 | R-09, R-17 |
| C-08 | `archify/bin/archify.mjs:6193-6244` `commandGuide` | 인자 파싱, 목록/추천 분기, 오류 처리, JSON 출력 | R-08~R-10, R-19 |
| C-09 | `archify/bin/archify.mjs:2205` | 사용법 문자열 | 1.3 |

### 1.6 수락 사례 [필수]
출처: T-01~T-13은 설치본 `guide`를 실행한 관찰(`artifacts/archify/spec-demos/guide-demo.sh`, `guide-score-demo.sh`, `guide-extra-demo.mjs`와 각 `.out.txt`). T-14는 구현에서 도출. 모두 종료 코드 0이고 `--json` 사용, 아니면 따로 표기.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-13, R-15, R-16 | `guide "ci/cd release workflow with rollback" --json` | `lang:"en"`, `confidence:"high"`(14+14+8=36), `matchedSignals:["ci/cd","release workflow","rollback"]`, `recommendation.id:"delivery-workflow"`, `type:"workflow"`, `alternatives:[]` |
| T-02 | R-14, R-15 | `guide "hello" --json` | `confidence:"low"`, `matchedSignals:[]`, `recommendation.id:"system-overview"`, `alternatives:[]` |
| T-03 | R-09, R-18 | `guide --json` | `{ok:true, mode:"list", lang:"en"}`, `recipes` 길이 13, 항목 키는 `id,type,proof,presentation,title,question,summary,useWhen,avoidWhen,include,prompt` |
| T-04 | R-15 | `guide "cache miss" --json` / `guide "kafka topology" --json` | 13점 `medium` `api-request` / 14점 `high` `event-stream` |
| T-05 | R-15 | `guide "components" --json` / `guide "region" --json` | 6점 `low` `system-overview` / 7점 `medium` `deployment-ownership` |
| T-06 | R-14, R-16 | `guide "state machine and er diagram" --json` | 승자 `object-lifecycle`(15점, 동점에서 앞선 순서), `alternatives:[{id:"database-schema",score:15,...}]` |
| T-07 | R-13 | `guide "database schema" --json` | `matchedSignals:["database-schema"]`, `high`, `erd`. `guide "database_schema"`도 같다(밑줄 정규화) |
| T-08 | R-11, R-12 | `guide "API 请求 调用链" --json` | `lang:"zh"`, `api-request`, `matchedSignals:["api 请求","调用链"]`, `high` |
| T-09 | R-11, R-13 | `guide "api request" --lang zh --json` | `lang:"zh"`, `recommendation.title:"API 请求链"`, `matchedSignals:["api-request"]` |
| T-10 | R-08 | `guide --bogus` / `guide x --lang fr` | 종료 코드 2, stderr `Unknown guide option "--bogus".` / `--lang must be "en" or "zh".`, stdout 비어 있음 |
| T-11 | R-13 | `guide "webhook" --json` | `matchedSignals:["webhook","webhook"]`, `high`, `async-roundtrip` |
| T-12 | R-13 | `guide "api gateway via cdn" --json` | `confidence:"medium"`, `matchedSignals:["via"]`, `layout-repair`(`type:"architecture"`) |
| T-13 | R-17 | `guide "api request"` (텍스트) | 첫 줄 `Recommendation: API request chain  [sequence]`, 둘째 줄 `Confidence: high`, `Presentation: classic · trace`, `Copy-ready prompt:` 다음 줄에 prompt. 대안 줄 없음 |
| T-14 | R-01, R-06 | LLM 평가: "주문 테이블 관계도" / "요청 하나의 구간별 소요 시간" / "Mermaid `sequenceDiagram` 원문" | `erd` / `waterfall` / `sequence`로 새 JSON 작성(Mermaid 스타일 복사 안 함) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (archify@a406594 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01~R-05 | C-01, `SKILL.md:36`, `SKILL.md:75` | 지시문 텍스트를 읽음 |
| R-06 | C-02 | 텍스트. 읽는 쪽은 LLM |
| R-07 | C-02 전체와 `.mjs` 대상 검색(`mermaid` 일치는 렌더러가 아닌 문서·생성 파일뿐) | 레포 `grep -rIli mermaid archify`로 `.mjs` 중 `generated-validators.mjs`만 걸리고 그 내용은 스키마 문자열. `explainer-authoring.md:210`은 explainer의 Mermaid가 차트 전용이고 흐름도 등은 네이티브 약식 문법을 쓴다고 함(행 10) |
| R-08, R-09, R-10, R-19 | C-08 `commandGuide` | 읽음. R-08·R-09는 `guide-demo.out.txt`로 실행 확인. R-10은 실행하지 않음 |
| R-11, R-12 | C-03, C-04 | 읽음. `guide-demo.out.txt`(T-08, T-09), `guide-extra-demo.out.txt`(`database_schema`) |
| R-13~R-16 | C-05, C-06 | 읽고 `guide-score-demo.out.txt`, `guide-demo.out.txt`로 점수·경계·동점·대안 확인. `webhook` 중복은 `guide-extra-demo.out.txt` |
| R-17 | C-07 | 영어 텍스트 한 건만 `guide-demo.out.txt`에서 확인. 중국어 라벨은 코드만 읽음 |
| R-18 | `guide-extra-demo.out.txt` `types` 줄 | 설치본의 `publicGuideData()` 덤프. 설치본은 레포 `archify/`와 `diff -rq` 동일 |
| 특이점 (a)~(c) | `scenarios.mjs:281-290`(`via`), `:141-160`(`webhook` 중복 `signals:` 줄 143), `layout-repair`의 `avoidWhen` 문구(`:279-300`) | (a)(b) 실행 확인, (c) 텍스트 |
| T-01~T-13 | `artifacts/archify/spec-demos/guide-demo.out.txt`, `guide-score-demo.out.txt`, `guide-extra-demo.out.txt` | 설치본 실행 관찰 |

문서와 구현의 차이: `SKILL.md:73`·README 297행은 `guide`를 "애매할 때"의 도구로만 쓰라고 하고, `layout-repair` 레시피가 신규 타입 선택에 부적합하다고 스스로 적지만 코드는 `via` 같은 일반 어휘로도 그 레시피를 추천한다(특이점 c). 구현을 사실로 썼다.

### 2.2 코드 읽는 순서 [선택]
`SKILL.md:58-85`(라우터·Mermaid) → `bin/archify.mjs:7264` `case 'guide'` → `commandGuide`(6193) → `recipes/scenarios.mjs:370`(`scoreRecipe`) → `:387`(`recommendScenario`) → `:421`(텍스트 형식). 레시피 데이터는 `scenarios.mjs:1-318`이고 신호만 필요하면 `signals:` 줄을 본다.

## 적용 메모 [선택]
없음.
