---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/learnharness/src/agent/tools/plan.ts
  - repos/learnharness/src/agent/tools/mermaid-plan.ts
  - repos/learnharness/src/core/plan-tree.ts
  - repos/learnharness/src/core/contracts/plan.ts
  - repos/learnharness/src/core/phases.ts
  - repos/learnharness/src/agent/tools.ts
  - repos/learnharness/src/store/chats.ts
  - repos/learnharness/src/core/contracts/chat.ts
  - repos/learnharness/src/core/native-messages.ts
  - repos/learnharness/src/agent/prompts/teacher/10-planning.md
  - repos/learnharness/src/agent/tool-execute.ts
  - repos/learnharness/src/agent/tools/heal.ts
  - repos/learnharness/src/core/argument-heal.ts
  - repos/learnharness/src/core/tool-parts.ts
  - repos/learnharness/src/core/pending.ts
  - repos/learnharness/src/core/settings.ts
  - repos/learnharness/src/server/settings-body.ts
depends:
  - ./question-answer-contract.md
  - ./probe-measurement.md
status: ready
reimplementation: "Python 3 표준 라이브러리, [강제] R-ID의 순수 검증·변환·파생 로직만(권고 규칙과 UI는 제외). 4개 스펙(question-answer-contract, probe-measurement, plan-tree, teaching-cycle)의 1.6 T-ID 전부를 포함해 83개 테스트 통과. 원본과 같은 입력으로 비교하지 않음(원본은 TypeScript이고 실행하지 않았다). 결과: ../../../artifacts/learnharness/reimplementation/core/RESULT.md"
---

# 의존 관계 계획

> 프로브가 끝난 직후 교사가 학습자의 현재 수준에서 목표까지의 선행 관계 지도를 mermaid 블록으로 한 번 써서(`plan_init`) 보여 주고, 이후 진행 위치는 저장하지 않고 질문에 붙은 `nodeId` 태그에서 매번 파생한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 프로버가 `probe_done`으로 끝나면(`probe-measurement.md`) 핸드오프 메시지가 교사의 첫 턴을 일으킨다. 그 메시지는 "현재 이해에서 목표까지 전체 가르침을 계획하라, 방법론을 적용하고 충분히 생각한 뒤 `plan_init`을 호출해 제시하라"는 고정 문장이다.
2. 교사가 계획을 숙고한 뒤 `plan_init`에 mermaid `graph` 블록을 넘긴다. 도구는 블록을 해석하고 구조(중복·누락·순환)를 검증해 세션 기록에 **트리를 통째로 교체**하여 저장한다. 문제가 있으면 줄 번호가 붙은 문제 목록이 돌아오고 교사가 고쳐 다시 부른다.
3. 교사가 접근법을 산문으로 말하고 지도를 제시한다(지도는 화면에 라이브 다이어그램으로 보인다). 제시하는 턴은 거기서 끝난다.
4. 학습자가 자연스러운 글로 답한다: 변경 요청이면 교사가 `plan_init`을 다시 불러 새 트리로 교체하고 다시 제시, 수락이면 교사가 첫 노드 가르치기를 시작한다.
5. 가르치는 동안 교사의 질문(`quiz`/`explain`)은 모두 `nodeId`로 계획 노드를 가리킨다. 도구가 호출 시점에 그 id가 현재 트리에 있는지 검사한다.
6. 지도 위 위치(현재/지나옴/앞으로)는 저장되지 않고 기록 속 질문 호출의 `nodeId`에서 매번 계산한다. 가르치는 중 학습자의 사고가 계획과 다르면 교사가 `plan_init`을 다시 불러 구조를 고친다.

### 1.2 범위·통합 지점 [필수]
- 제공: `plan_init` 도구(입력, 해석 문법, 구조 검증, 저장, 결과), 트리 타입, 위치 파생 규칙, 질문 호출 때의 `nodeId` 검증, 단계 판정(probe/plan/teach), 계획에 관한 교사 프롬프트가 요구하는 행동.
- 제외:
  - 가르치기 사이클·질문 역할(`type`)의 교육적 의미 → `teaching-cycle.md`.
  - 질문·답 계약 → `question-answer-contract.md`.
  - 프로브 평가서 → `probe-measurement.md`.
  - 계획 화면(팝업, `plan-block` UI 메시지, 레이아웃). 화면용 `plan-block` 메시지는 모델에게 보이지 않는다는 사실만 있다.
  - 세션 기록 전체(S1, `미작성`)와 저장소 어댑터 본문. 여기서는 `saveTree`가 세션 기록의 `tree` 필드를 통째로 바꾼다는 것만.
- 외부 의존: 세션 저장소(`getChat`, `saveTree`), 에이전트 루프(pi)의 도구 실행, 질문 도구가 `nodeId` 검증을 호출. 에이전트 루프는 도구 인자를 실행 전에 스키마로 검증하는데(TypeBox `Value.Convert`로 형을 맞춘 뒤 `Value.Check`, 주석 근거) 그 거절 결과의 문구·모양은 이 레포 밖 라이브러리 소관이라 이 스펙이 정하지 않는다. 이 스펙이 "스키마가 거절한다"고 쓸 때는 "`execute`가 불리지 않고 오류 결과가 모델에게 돌아간다"까지만 뜻한다.
- 소유 상태·부작용: 세션 기록의 `tree`(노드·간선·`version`). 위치는 어디에도 저장하지 않는다. `saveTree`는 세션의 `updatedAt`을 바꾸지 않는다(사이드바 순서가 흔들리지 않게).

### 1.3 인터페이스와 데이터 의미 [필수]

**`plan_init` 입력**: `mermaid`(문자열, 1자 이상). 스키마의 `minLength`만 있어서 공백만 있는 문자열도 스키마는 통과하고 해석기가 "비어 있음"으로 거절한다(R-02). 스키마에 `additionalProperties` 지정은 없다(코드 확인: `src/` 전체 검색에 없음).

**트리 타입**

| 타입 | 필드 | 의미 |
|---|---|---|
| `PlanNode` | `id`(소문자 slug), `title`(비지 않음), `summary?` | `id`는 질문이 `nodeId`로 가리키는 영구 이름. `plan_init`이 만드는 노드에는 `summary`가 없다 |
| `PlanEdge` | `from`, `to` | `from`을 먼저 이해해야 `to`에 이를 수 있다(선행 관계) |
| `PlanTree` | `nodes`, `edges`, `version` | 진행 정보는 없고 구조만 있다. `plan_init`이 만든 트리의 `version`은 항상 1이고 어떤 코드도 이 값을 올리지 않는다(주석의 "변경마다 증가"는 낡은 서술, 2.1). 세션 기록 자체의 스키마 `version` 도장(`CURRENT_CHAT_VERSION`)과는 별개의 값 |

**mermaid 부분집합 문법** (손으로 만든 해석기, 정규식 원문은 C-02)

| 형태 | 의미 |
|---|---|
| 줄 처리 | `\r?\n`으로 줄을 나누고 줄마다 앞뒤 공백을 제거해 읽는다. 문제의 줄 번호는 원문 기준 1부터이며 빈 줄·주석 줄도 센다 |
| 헤더 | 첫 번째로 "비어 있지 않고 `%%`로 시작하지 않는" 줄(앞의 빈 줄·주석 줄은 건너뜀). `graph` 또는 `flowchart` + 공백 + 방향(`TD`/`TB`/`LR`/`RL`/`BT`, 대소문자 무관) + 끝(`^(graph\|flowchart)\s+(td\|tb\|lr\|rl\|bt)\s*$`)만 통과한다. `graph TD;`나 방향 없는 `graph`는 문제. 방향은 의미 없음(화면 배치는 따로 계산). 이 줄은 통과 여부와 무관하게 노드·간선으로 읽지 않고 다음 줄부터 해석한다 |
| `%% …` 줄, 빈 줄 | 무시. 줄 중간의 `%%`는 주석이 아니다 |
| 노드 줄 | 화살표가 없는 줄 하나가 끝점 하나. 못 읽으면 `can't parse` 문제 |
| 간선 줄 | 화살표(`-->`, `==>`, `-.->`, 모두 같은 선행 간선)가 하나라도 있는 줄. 화살표로 쪼갠 조각 하나하나가 끝점이고 인접 쌍이 간선(체인 `a --> b --> c` 펼침). 조각 하나라도 못 읽으면 그 줄은 `can't read the edge` 문제 하나만 내고 노드·간선을 하나도 등록하지 않는다. 화살표 라벨(`a -->\|x\| b`)·`---`는 지원하지 않는다 |
| 끝점 | id 후보 + 선택적 라벨. id 후보는 공백·`(`·`)`·`[`·`]`이 아닌 문자의 연속(대문자·점이 있어도 후보이며 슬러그 검사는 아래 규칙이 따로 한다). 라벨은 `[제목]`(제목에 대괄호 불가), `("제목")`, `(제목)`(제목에 괄호 불가) 중 하나이고 id와 라벨 사이 공백은 허용. 제목은 양끝 공백을 제거하고, 길이 2 이상이며 같은 종류 따옴표(`"` 또는 `'`) 한 쌍으로 감싸였으면 그 쌍을 벗겨 다시 공백을 제거한다. 빈 제목은 라벨 없음 |
| id 규칙 | 소문자·숫자 단어를 `-` 또는 `_` 한 글자로 이은 것(`^[a-z0-9]+([_-][a-z0-9]+)*$`; `a--b`, `a_-b`, `a-`는 위반). 이것이 유일하게 엄격한 규칙. 위반 id는 등록하지 않고 id마다 문제 하나 |
| 등록 규칙 | 간선 끝점으로만 나온 id도 노드로 등록. 노드 순서는 줄 순서, 한 줄 안에서는 왼쪽→오른쪽의 첫 등장 순(`nodeIds`·`tree.nodes`의 순서). 제목은 처음 등록될 때 정해지며(라벨이 있으면 라벨, 없으면 id) 이후 라벨은 **현재 제목이 id 문자열과 같을 때만** 덮어쓴다(라벨 없이 등록된 뒤에 라벨이 오면 채움; 부수효과로 `a[a]`처럼 제목이 id와 같은 노드도 뒤의 라벨이 덮어씀). 앞선 참조 허용 |
| 간선 규칙 | 같은 `from→to`는 한 번만(줄을 넘어서도). 자기 간선은 문제로 건너뜀. 반대 방향(`a→b`와 `b→a`)은 별개 간선이라 해석기는 통과시키고 구조 검증이 사이클로 거절 |
| 지원 안 함 | `subgraph`·스타일·클래스·방향 키워드 밖의 문법(해당 줄은 노드 줄로 읽히다 문제가 되거나 id 후보가 슬러그 검사에서 걸림) |

**`plan_init` 결과**
- 성공: 모델이 보는 `content`는 JSON 문자열 `{ok:true, nodeIds:[…], reminder:"These are the plan's node ids — the only valid nodeId values for every quiz and explain call from here on. Reference them exactly."}`이고, 트리 전체는 기록·화면용 `details:{ok:true, tree}`에만 둔다(모델이 방금 쓴 것을 되풀이하지 않음).
- 실패: 본문이 `{ok:false, error}` 객체를 돌려주고, 도구 실행 래퍼(`serverExecute`)가 이를 `content`=그 객체의 JSON 문자열 한 덩어리, `details`=같은 객체로 바꾼다(`text` 필드가 없으므로 "본문이 `{text, details}`를 돌려주는 경로"가 아니다). 해석 문제는 줄 번호가 붙은 문제를 줄바꿈(`\n`)으로 이은 문자열, 구조 문제는 오류 메시지 한 개. `isError`로 표시되지는 않는다(래퍼가 `isError`를 설정하는 코드가 없음). 질문 도구의 오류 결과(`isError:true`)와 다르다.

**위치 파생 결과** `DerivedPlanStatuses`: `current`(문자열 또는 null), `visited`(노드 id 집합). 노드 상태는 `current` / `visited` / `upcoming`이고 `current`가 `visited`보다 우선한다.

### 1.4 행동 규칙과 남은 질문 [필수]
범례: **[강제]** 코드가 지킴, **[권고]** 프롬프트·도구 설명이 모델에게 요청할 뿐 코드는 막지 않음.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] 도구 배치 | `plan_init`은 교사 도구 구성(`createTeacherTools`)에만 있고 프로버·연습에는 없다. **설정 쓰기 쪽이 끌 수 없게 막는다**: 설정에 쓸 수 있는 도구 키는 `research`·`demo`·`visual`·`pdf`(`TOGGLEABLE_TOOLS`)와 `explain`(퀴즈 방식 전환)뿐이고 그 밖의 키는 400 `unknown tool "<키>" (supported: research, demo, visual, pdf, explain)`로 거절된다. **도구 팩토리는 막지 않는다**: `createTeacherTools`는 `filterEnabledTools`로 `enabled[이름]===false`인 도구를 이름과 무관하게 레지스트리에서 빼고, 제외 키는 `quiz`·`explain`뿐이다(`withoutMechanics`). 설정을 읽는 쪽 정제기는 불리언 값의 키를 그대로 보존하므로, 디스크에 손으로 `plan_init:false`를 써 두면 팩토리까지 도달해 `plan_init`이 빠진다(프로버의 `probe_done`은 필터 뒤에 다시 붙여 팩토리 수준에서도 보호되지만 `plan_init`에는 그런 보호가 없다). 즉 "토글 불가"는 쓰기 검증의 보장이다. `quiz`는 `explain:true` 설정이면 `explain`으로 바뀌고 `quiz:false`는 효과 없음(키가 제거됨). 호출 횟수나 시점을 막는 코드는 없다(프로브 직후 한 번만이라는 것은 도구 설명의 권고) | 코드 확인 |
| R-02 | [강제] 해석 | 문법은 1.3대로. 문제는 하나에서 멈추지 않고 **모두** 모아 각각 `line N: …`로 시작하는 문자열 목록으로 반환한다(줄 순서, 한 줄에서 여러 id가 위반이면 id마다). 비어 있으면(빈 문자열·공백·주석만) 줄 번호 없이 "The plan is empty — expected a `graph TD` block with nodes and `-->` requires-edges." 노드가 하나도 없으면(헤더만 있는 경우 등) "No nodes found — the plan needs at least one." 이 "노드 없음"은 다른 문제가 하나도 없을 때만 나오고, 문제가 하나라도 있으면 문제 목록만 돌아온다. 성공하면 노드는 `{id, title}`(요약 없음)이고 순서는 등록 순서 | 코드 확인 |
| R-03 | [강제] 해석 문제의 종류 | 헤더가 `graph\|flowchart` + 방향이 아니면 ``line N: expected the header `graph TD` (or flowchart TD/TB) first, got `<그 줄>`.``. 슬러그가 아닌 id는 ``line N: node id `X` must be a lowercase slug (a-z, 0-9, joined by hyphens or underscores — e.g. `chain-rule-intuition`); ids are permanent and checks reference them.``. 읽을 수 없는 간선 줄은 `line N: can't read the edge …`, 읽을 수 없는 노드 줄은 `line N: can't parse …`(나머지 문구 전문은 C-02). 자기 간선(`a --> a`)은 ``line N: self-loop `a --> a` — a node can't require itself.``(체인에서는 그 쌍만 건너뛰고 나머지 쌍은 계속 읽음). 문제가 하나라도 있으면 저장하지 않는다 | 코드 확인 |
| R-04 | [강제] 구조 검증 | 해석 통과 뒤 `createTree`가 중복 노드 id, 끝점 없는 간선, 자기 순환, 중복 간선, **순환(사이클)**을 `PlanTreeError`로 거절한다. 검증은 노드 전체 → 간선 끝점 존재 → 간선을 입력 순서대로 하나씩(앞서 받아들인 간선들에 대해) 보고, **첫 위반에서 멈춰** 그 오류 하나만 돌려준다. 사이클이면 "이미 받아들인 간선을 따라 `to`에서 `from`에 닿게 되는" 첫 간선이 지목된다: ``Edge "b" → "a" would create a cycle: "a" already leads (directly or transitively) back to "b". "from" must be understood before "to" — the tree is a DAG.``(T-04). 결과는 `{ok:false, error:<메시지>}`. 해석기가 이미 중복 간선·자기 간선·끝점 등록을 처리하고 노드는 맵으로 중복을 없애므로 `plan_init` 경로에서 실제로 걸리는 것은 사실상 사이클이다 | 코드 확인(도달 가능성은 추론: 두 코드를 맞대어 읽음) |
| R-05 | [강제] 크기 | 노드·간선 수의 상한은 해석기·`createTree`·`saveTree` 어디에도 없다(노드 수를 비교하는 곳은 해석기의 "0개" 검사 하나뿐). 도구 설명은 "5–15 nodes … compress"를, 계획 프롬프트는 "No size ceiling"을 요구하지만 둘 다 권고일 뿐 강제되지 않는다. 최소 크기도 노드 1개(T-15) | 코드 확인(상한 검사 코드 부재: 세 파일 읽음 + `src`·`components` 전체에서 `nodes.length`·`edges.length`·`MAX_NODES` 계열 검색, 비교는 해석기의 `=== 0`뿐. "5–15"는 `plan.ts:71` 한 곳에만 있음) |
| R-06 | [강제] 성공 | 세션 기록의 `tree`가 새 `PlanTree`로 통째로 교체된다(`version`은 항상 1: `createTree`가 고정값 1을 돌려주고 올리는 코드는 없음). 이전 트리는 남지 않는다. `updatedAt` 불변. `saveTree`는 디스크의 기록을 읽어 `tree`만 바꿔 동기로 써 넣는다. 모델에게는 1.3의 content, 화면·기록에는 `details.tree` | 코드 확인 |
| R-07 | [강제] 세션 기록이 없음 | `{ok:false, error:"Chat not found: <chatId>"}`. 이 검사는 해석보다 먼저라서 mermaid가 잘못돼도 기록이 없으면 이 오류만 나온다. 기록 파일이 없거나 읽을 수 없거나 이 빌드보다 새 스키마 버전이어도 같다(`getChat`이 null) | 코드 확인 |
| R-08 | [강제] 재호출 | 부분 수정 도구는 없고 재호출이 전체 교체다. id는 영구해야 한다는 것은 권고일 뿐이어서 코드는 새 트리에 없는 id가 있어도 그대로 받는다 | 코드 확인 |
| R-09 | [강제] 위치 파생(`derivePlanStatusesLh`) | 기록의 assistant 메시지를 순서대로 훑어 도구 호출 이름이 `quiz` 또는 `explain`이고 인자 `nodeId`가 **현재 트리에 있는 문자열**인 것만 모은다(호출만 본다: 결과·정오·답 유무·오류 여부는 무관). 연속으로 같은 노드면 하나의 머무름으로 접는다(무시된 호출은 "연속" 판정에 끼지 않으므로 `quiz(a)`, `quiz(없는-id)`, `quiz(a)`는 한 번의 머무름). 읽는 대상은 기록에 저장된 **원 인자**(`arguments`)이고 인자 복구·형 변환 전의 값이다(기록은 원 인자를 보존한다는 주석 근거). `current` = 마지막 머무름의 노드(태그 호출이 없으면 null: 대체 현재 없음), `visited` = 마지막을 뺀 앞선 머무름들의 노드. 돌아오면(a→b→a) a는 visited이자 current이고 표시는 current. 현재 트리에 없는 `nodeId`(문자열이 아닌 값 포함)는 아무 것도 움직이지 않는다. `probe`·`recall`·`ask_user_question` 호출은 `nodeId`가 있어도 보지 않는다 | 코드 확인 |
| R-10 | [강제] 질문 호출 때 `nodeId` 검증 | `quiz`/`explain` 실행 시 **저장된 현재 기록**의 트리를 읽어 `nodeId`가 노드 id 중 하나인지 본다. 아니면 질문은 학습자에게 가지 않고 오류 결과로 돌아간다: 트리가 있으면 `nodeId "<x>" matches no node in this session's plan map. Copy one of your plan_init slugs exactly (<앞 5개 id를 ", "로 이음><6개 이상이면 ", …">).`, 트리가 없으면(기록이 없거나 `tree`가 없어도 같음) `nodeId "<x>" matches no node in this session's plan map. No plan map exists yet — call plan_init before posing quizzes.` 이 문제는 같은 호출의 다른 검증 문제들(`quizInputProblems`/`explainInputProblems`) **뒤에** 덧붙여 한 목록으로 반환되고, 결과는 `isError:true`, content `Invalid tool input for tool "quiz":\n- <문제>\n- <문제>…`(도구 이름은 `quiz` 또는 `explain`), `details:{tool, problems}`이다. `nodeId`는 인자 복구·따옴표 벗기기의 대상이 아니라서 `"\"a\""`(따옴표 박힌 문자열)는 그대로 거절되고, 빈 문자열은 스키마를 통과하지만 이 검사가 거절한다. 같은 턴에서 `plan_init`으로 저장된 트리가 곧바로 보인다(저장이 즉시 디스크에 쓰이므로) | 코드 확인 |
| R-11 | [강제] 단계 판정 | 세 단계 `probe` → `plan` → `teach`는 일방향이다. `probe`→`plan`은 `probe_done`의 **오류가 아닌** 결과가 기록에 들어올 때, `plan`→`teach`는 `plan` 단계에서 `nodeId`가 비지 않은 문자열인 `quiz`/`explain` 호출이 처음 나오는 assistant 메시지에서 일어난다(그 호출이 오류였어도). 질문 답의 정오는 쓰지 않는다. 단계 판정의 "태그됨"은 `nodeId`가 비지 않은 문자열이기만 하면 되고 트리 소속은 보지 않는다(R-09의 위치 파생은 트리 소속을 요구) | 코드 확인 |
| R-12 | [강제] 교사 첫 입력 | 교사의 첫 요청은 핸드오프 메시지(1.1 단계 1의 고정 문장)를 사용자 역할 메시지로 받는다. 이 문장이 "숙고 뒤 `plan_init`을 제시하라"를 지시한다(코드는 강제하지 않음) | 코드 확인 |
| R-13 | [권고] 계획 숙고 | 학습자 수준과 목표를 가지고 멈춰서 이 사람에게 이것을 가르치는 최선의 방법을 따져 본다: 분야의 핵심 개념·진짜 제1원리·표준 틀·흔한 함정을 짚고, 분야에 대한 그림이 흐릿하면 조사를 보내 확인한다. 무조건적 진실이 무엇이고 깨끗한 원자 단위("ALL X is done through {…}")가 있는가, 학습자가 이미 가진 것은 무엇인가. **최소 트리**: 이미 아는 것은 다시 가르치지 않고, 목표 경로 밖은 흥미로워도 가르치지 않으며, 목표까지의 유도는 주제가 허락하는 한 짧게. 동기 있는 발견 경로, 구간별 소크라테스식/설명식 선택 | 코드 확인(프롬프트 텍스트) |
| R-14 | [권고] 지도의 성격 | 지도이지 교과 과정이 아니다. 노드는 구조적 이정표(바닥의 무조건적 진실, 주요 정거장, 싱크의 목표)이고 한 노드가 추론 단계 하나일 수도 다섯일 수도 있다. 슬러그는 한 번 정하면 영구(`chain-rule-intuition`). `-->`는 "먼저 이해해야 함". 크기는 주제가 필요한 만큼(가독성은 압축이 아니라 올바른 구조에서 나온다) | 코드 확인(프롬프트 텍스트). 도구 설명의 "5–15 노드"와 다름: R-05 |
| R-15 | [권고] 제시 | 항상 가르치기 전에 두 가지: ① 접근법 산문(무엇을 어떤 순서로 왜, 프로브가 보여 준 경계와 목표에 비추어) ② 지도(`plan_init` 자체가 제시이므로 산문에 계획을 다시 그리거나 목록으로 되풀이하지 않는다. 라벨은 짧게). **제시는 턴을 끝낸다**: 학습자의 확인을 청하고, 변경 요청이면 `plan_init`을 다시 불러 다시 제시, 합의되면 첫 노드를 시작한다. 제시하는 턴에서 가르치지 않는다. 수업 중 재작성은 다시 제시하지 않고 계속한다 | 코드 확인(프롬프트 텍스트). 확인 전 가르치지 않음은 코드가 막지 않는다(R-01, R-10은 트리 존재만 요구) |
| R-16 | [권고] 뿌리 점검 | 기초로 둔 모든 노드가 정말 "이 학습자에게" 무조건적 진실인지, 더 단순한 것에서 도출되는 위장된 정리는 아닌지 따진다. 도출된다면 내려서 지도를 늘린다. 잘못된 뿌리는 그 위의 모든 것을 오염시킨다 | 코드 확인(프롬프트 텍스트) |
| R-17 | [권고] 지도는 학습자와 함께 움직인다 | 지도는 학습자에 대한 가설이고 프로브는 첫 스케치일 뿐이다. 가르치는 중 드러난 사고가 계획과 다르면 지도를 고친다(`plan_init` 재호출): 빠진 기초 추가, 이미 가진 것 가지치기, 우회. 구조가 안 바뀌었으면 다시 쓰지 않는다. 틀 밖의 혼란이 드러나면 한 턴에 글 덩어리로 "덮고" 계획으로 돌아가지 말고, 한 번에 한 추론 단계로 쌓는다 | 코드 확인(프롬프트 텍스트) |
| R-18 | [권고] 질문 태깅 | 교사의 모든 질문 도구 호출은 `nodeId`와 `type`을 둘 다 가진다(도구가 필수로 강제). 한 노드에 필요한 만큼 여러 질문, 다음 노드에 대해 묻는 것이 곧 이동 방법이다. 지도에 맞는 노드가 없는 확인은 `ask_user_question` | 코드 확인(필수 강제는 `question-answer-contract.md` R-01; 사용 방식은 프롬프트 텍스트) |

- 불변식: 위치(`current`/`visited`)는 기록의 질문 호출에서 언제든 다시 계산되며 어디에도 저장되지 않는다. 같은 기록과 같은 트리면 같은 결과다. 전제: 호출이 기록에 있는 한 결과가 없거나 오류여도 위치는 움직인다.
- 미결정: 없음
- 확인 한계: 코드를 실행하지 않았고 테스트를 열지 않았다. 교사가 프롬프트의 제시·확인 절차를 따르는지는 미확인. 계획 화면(UI)은 범위 밖이라 읽지 않았다. 스키마 거절의 결과 문구와 `Value.Convert`가 실제로 어떤 값을 바꾸는지는 외부 라이브러리(pi)라 코드로 읽지 못했고(1.2), "기록은 원 인자를 보존한다"(R-09)와 "경계에서 Convert 뒤 Check"는 주석 근거다. 따라서 id가 숫자뿐인 노드(`1`)에 모델이 숫자 `nodeId:1`을 보내면 경계에서 문자열로 바뀌어 통과하지만 기록에는 숫자로 남아 R-09·R-11이 읽지 못한다는 것은 이 주석 근거에서 이은 `추론`이다.

### 1.5 필수 코드 참조 [필수]
라이선스는 AGPL-3.0(overview 1절)이다. 프롬프트는 본문 인용 없이 파일:줄 범위로만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/agent/tools/plan.ts:14-15`, `:52-60`, `:62-109` `planInitInput`, `planTools`, `plan_init` | 입력 스키마·실행 순서(해석→검증→저장)·결과 모양·알림 문구 | R-01, R-06, R-07 |
| C-02 | `src/agent/tools/mermaid-plan.ts:44-55` `HEADER_RE`, `SLUG_RE`, `ARROW_RE`, `ENDPOINT_RE`; `:62-74` `parseEndpoint`; `:76-163` `parseMermaidPlan` | 부분집합 해석기 전체(문제 문구와 줄 번호 포함) | R-02, R-03, 1.3 |
| C-03 | `src/core/plan-tree.ts:22-27`, `:36-126` `PlanTreeError`, `assertValidNode`, `nodeMap`, `createsCycle`, `assertValidEdge`, `createTree` | 구조 검증과 오류 문구 | R-04 |
| C-04 | `src/core/contracts/plan.ts:13-43` 타입; `:68-80` `DerivedPlanStatuses`, `derivedNodeStatus`; `:130-149` `derivePlanStatusesLh` | 트리 타입, 위치 파생 | R-09 |
| C-05 | `src/agent/tools.ts:352-366` `nodeIdProblem`; `:375-391` `teachQuizToolFor` | 호출 시 `nodeId` 검증 | R-10 |
| C-06 | `src/core/phases.ts:51-60` `taggedNodeId`; `:163-195` `phaseAt3Lh` | 단계 판정 | R-11 |
| C-07 | `src/store/chats.ts:198-206` `saveTree` | 트리 통째 저장, `updatedAt` 불변 | R-06 |
| C-08 | `src/core/contracts/chat.ts:187-192` `HANDOFF_TEXT`; `src/core/native-messages.ts:157-167` | 교사 첫 입력 | R-12 |
| C-09 | `src/agent/prompts/teacher/10-planning.md:3-44` | 계획 독트린(숙고·지도·제시·재작성) | R-13~R-18 |
| C-10 | `src/core/pending.ts:60-106` `JOB_TOOLS`, `TOGGLEABLE_TOOLS`, `WRITABLE_TOOL_KEYS`, `EnabledTools`, `filterEnabledTools`; `src/server/settings-body.ts:156-172` 도구 키 쓰기 검증; `src/core/settings.ts:491-498` `sanitizeBooleanMap`; `src/agent/tools.ts:287-348` `createProberTools`; `:416-432` `quizMechanics`, `withoutMechanics` | 토글 쓰기 검증과 팩토리 필터의 차이, `quiz`·`explain` 제외 규칙 | R-01 |
| C-11 | `src/agent/tool-execute.ts:117-131` `invalidInputResult`; `:162-180` `toToolResult`; `:196-212` `serverExecute` | 실패·성공 결과가 모델에게 보이는 모양, `isError` 유무 | R-02, R-04, R-07, R-10 |
| C-12 | `src/core/plan-tree.ts:11-19` 주석(낡은 `version` 서술), `:29-32` `emptyTree`, `:111-126` `createTree` | `version` 처리와 검증 순서 | R-04, R-06 |
| C-13 | `src/core/contracts/plan.ts:82-102` `derivePlanStatuses`; `:104-123` `PlanToolResult` | 위치 파생의 옛 판과 결과 타입 | R-09 |
| C-14 | `src/store/chats.ts:53-77` `writeChat`, `getChat` | 저장은 동기 쓰기, 읽기는 매번 디스크, 더 새 스키마 기록은 부재 취급 | R-06, R-07, R-10 |
| C-15 | `src/agent/tools.ts:59-77` `prepareQuestionArguments`; `src/agent/tools/heal.ts:30-48`; `src/core/argument-heal.ts:25-96`; `src/core/tool-parts.ts:37-52` `boundaryParse` | 인자 복구 대상(`nodeId`는 아님)과 경계의 형 변환·원 인자 보존 주석 | R-09, R-10 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 코드를 실행하거나 원본 테스트를 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-06 | `graph TD\n a[One] --> b[Two] --> c[Three]` | 노드 [a,b,c](제목 One/Two/Three), 간선 [a→b, b→c], `version:1`로 저장. content의 `nodeIds`는 [a,b,c]이고 `reminder` 포함 |
| T-02 | R-03 | `graph TD\n A --> b` | `ok:false`. 오류에 2번 줄과 "node id `A` must be a lowercase slug". 저장 안 됨 |
| T-03 | R-03 | `a --> b`(헤더 없음) | 1번 줄에 "expected the header `graph TD` …" 문제. 첫 줄은 헤더 자리로 취급되어 간선으로는 읽히지 않으므로 노드가 없고, 문제가 있으면 `ok:false`가 먼저다. 저장 안 됨 |
| T-04 | R-04 | `graph TD\n a --> b\n b --> a` | `ok:false`, `error`가 정확히 `Edge "b" → "a" would create a cycle: "a" already leads (directly or transitively) back to "b". "from" must be understood before "to" — the tree is a DAG.` 저장 안 됨 |
| T-05 | R-03 | `graph TD\n a --> a` | "self-loop" 문제 |
| T-06 | R-02 | `a[One]`을 쓰고 나중에 `a[Two]` / 라벨 없이 `a`를 먼저 쓰고 나중에 `a[Title]` | 제목 One / 제목 Title(라벨 없던 노드는 뒤의 라벨로 채움) |
| T-07 | R-02 | `a-->b`, `a ==> b`, `a -.-> b`가 한 블록에 | 간선 `a→b` 하나 |
| T-08 | R-02 | 블록 안에 `%% 주석`과 빈 줄 | 무시되고 노드·간선만 남음 |
| T-09 | R-02 | `a-` 또는 `chain_rule`/`chain-rule` | `a-`는 슬러그 위반, 나머지 둘은 통과 |
| T-10 | R-09 | 트리 {a,b,c}, 기록의 질문 호출 순서: `quiz(a)`, `quiz(a)`, `explain(b)`, `quiz(없는-id)`, `quiz(a)` | 머무름 [a,b,a] → `current=a`, `visited={a,b}`. 노드 a 표시 current, b 표시 visited, c 표시 upcoming |
| T-11 | R-09 | 태그된 질문 호출이 하나도 없음 / 새 `plan_init`으로 트리를 바꿔 옛 `nodeId`가 사라짐 | `current=null`(대체 현재 없음) / 새 트리에 없는 id는 무시 |
| T-12 | R-10 | 트리가 없는 상태에서 `quiz(nodeId:"a")` / 트리 {x,y}에서 `quiz(nodeId:"z")` | 각각 "No plan map exists yet — call plan_init before posing quizzes." / `nodeId "z" matches no node … (x, y)`. 질문이 학습자에게 가지 않고 오류로 돌아감 |
| T-13 | R-11 | `probe_done` 결과가 정상 / 오류. 이후 `nodeId` 없는 `quiz`/`nodeId:"a"`인 `quiz` | 정상 결과 후 `plan`, 오류면 `probe` 유지. `nodeId` 없는 질문은 `teach`로 안 넘어가고, 태그된 호출이 처음 나온 메시지에서 `teach` |
| T-14 | R-07 | 존재하지 않는 chatId로 `plan_init` | `{ok:false,error:"Chat not found: …"}` |
| T-15 | R-05 | 노드 40개짜리 블록 | 저장 성공(상한 없음) |
| T-16 | R-03 | `%% c\n\nflowchart bt\n a --> b` / `graph TD;\n a --> b` / `graph\n a --> b` | 첫 블록은 통과(앞의 주석·빈 줄은 건너뜀, 방향은 대소문자 무관). 나머지 둘은 1번 줄 헤더 문제로 `ok:false` |
| T-17 | R-02 | 한 줄씩 `a["Quoted"]`, `b('Single')`, `c("Paren")`, `d(Plain text)`, `e[ ]`, `f` | 제목 Quoted / Single / Paren / Plain text / e / f(빈 제목과 라벨 없음은 id) |
| T-18 | R-03 | `graph TD\n a -->\|x\| b\n subgraph s` | 문제 두 개: `line 2: can't read the edge …`, `line 3: can't parse …`. 2번 줄에서 `a`·`b`는 등록되지 않고, 문제가 있으므로 "No nodes found"는 나오지 않음 |
| T-19 | R-02 | `graph TD\n b --> a\n c --> a\n b --> a` | `nodeIds`는 [b, a, c], 간선은 b→a, c→a 두 개(중복 한 번만) |
| T-20 | R-02, R-03 | `graph TD\n A --> b\n c -->\n D` | `error`는 세 문제를 `\n`으로 이은 문자열: 2번 줄 id `A` 슬러그 위반, 3번 줄 `can't read the edge`, 4번 줄 id `D` 슬러그 위반(줄 순서) |
| T-21 | R-04 | `graph TD\n a --> b --> c\n c --> a` | 세 번째 간선이 지목된 사이클 메시지: `Edge "c" → "a" would create a cycle: "a" already leads … back to "c". …` |
| T-22 | R-01 | 교사 도구 팩토리에 설정 `{plan_init:false}` / `{research:false}` / `{quiz:false}` / `{explain:true}`; 프로버 팩토리; 설정 쓰기 검증에 `tools:{plan_init:false}` | 순서대로: `plan_init`이 빠짐 / `research`만 빠짐 / 효과 없음(`quiz` 그대로) / `explain`이 있고 `quiz`가 없으며 `plan_init`은 있음. 프로버 팩토리에는 어떤 설정에서도 `plan_init`이 없음. 쓰기 검증은 `unknown tool "plan_init" (supported: research, demo, visual, pdf, explain)` 오류를 돌려줌 |
| T-23 | R-07 | 존재하지 않는 chatId에 헤더 없는 mermaid로 `plan_init` | `error`는 `Chat not found: <chatId>` 하나뿐(해석 문제 없음) |
| T-24 | R-09 | 트리 {a}. `probe`·`recall`·`ask_user_question` 호출에 `nodeId:"a"`; `quiz`에 `nodeId`가 숫자·null; `quiz(a)`, `quiz(없는-id)`, `quiz(a)` | 앞의 둘은 위치를 안 움직임. 마지막은 한 번의 머무름: `current=a`, `visited={}` |
| T-25 | R-10 | 트리 {a,b,c,d,e,f}에서 선택지가 잘못된 `quiz(nodeId:"z")` / 트리 {a,b,c,d,e}에서 `nodeId:"z"` | `isError:true`, content가 `Invalid tool input for tool "quiz":\n- <선택지 문제>\n- nodeId "z" matches no node … (a, b, c, d, e, …).`(nodeId 문제가 마지막) / 두 번째는 `… (a, b, c, d, e).`(5개 이하면 `, …` 없음) |
| T-26 | R-02, R-06 | `plan_init` 성공 / 해석 실패 | 성공 content는 공백 없는 JSON `{"ok":true,"nodeIds":[…],"reminder":"…"}`(키 순서 ok, nodeIds, reminder). 실패 content는 `{"ok":false,"error":"…"}` JSON 문자열이고 `isError`는 설정되지 않음 |
| T-27 | R-11 | 트리 {x}, `plan` 단계에서 첫 태그 호출이 `quiz(nodeId:"zzz")` | 단계는 `teach`로 넘어가지만(비지 않은 문자열이면 태그됨) 위치 `current`는 null |
| T-28 | R-06, R-08 | 같은 세션에 `plan_init`을 두 번(서로 다른 블록) | 두 번째 트리가 첫 번째를 통째로 교체, `version`은 둘 다 1, `updatedAt` 불변 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@b277ee3) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01, C-10 | 도구 레지스트리·토글 목록·쓰기 검증·읽기 정제기·팩토리 필터를 읽음. 쓰기 검증의 400 변환은 라우트 쪽이라 미열람(주석 근거) |
| R-02, R-03 | C-02, C-11 | 소스 전문 읽음. 정규식·문구는 줄 단위로 대조 |
| R-04 | C-03, C-02, C-12 | 소스 전문 읽음. 도달 가능성은 두 코드를 맞대어 추론 |
| R-05 | `plan.ts:71`(도구 설명), `10-planning.md:22`(프롬프트), `mermaid-plan.ts`, `plan-tree.ts`, `chats.ts:199-206` | 세 코드 파일을 전부 읽고 `grep -rnE "(MAX\|max)[_A-Za-z]*NODES\|nodes\.length *[<>]" src`에 결과 없음. 이 SHA에서 상한은 강제되지 않는다 |
| R-06~R-08 | C-01, C-07, C-11, C-12, C-14 | 소스 전문 읽음 |
| R-09 | C-04, C-13, C-15 | 소스 전문 읽음. "원 인자 기준"은 `tools.ts:62-64`·`tool-parts.ts:41-45` 주석 근거 |
| R-10 | C-05, C-11, C-14, C-15 | 소스 전문 읽음. "저장 즉시 디스크"는 `writeChat`의 동기 `writeFileSync`와 `getChat`의 매번 디스크 읽기(C-14)로 확인 |
| R-11 | C-06 | 소스 전문 읽음 |
| R-12 | C-08 | 소스 전문 읽음 |
| R-13~R-18 | C-09 | 프롬프트 전문 읽음 |
| 문서·코드 차이 | `core/contracts/plan.ts:32` 주석("Increments on every mutation"), `core/plan-tree.ts:15-18` 주석 | 트리 `version`이 변경마다 증가한다고 쓰지만 변경 연산은 모두 삭제됐고 `createTree`는 항상 `version:1`을 돌려준다(`plan-tree.ts:125`). `src`·`components` 전체에서 트리 `version`을 올리는 코드(`version + 1`, `++` 등)를 검색해 없음을 확인했다. `emptyTree()`(`plan-tree.ts:30`)는 `version:0`을 돌려주지만 `src`·`components`에는 사용처가 없고(import는 테스트뿐) 저장되지 않는 씨앗이다. 구현을 사실로 썼다 |
| 문서·코드 차이 | `core/pending.ts:65-78`, `server/chat-handler.ts:362-366`, `agent/teacher-agent.ts:111-115` 주석 | 주석은 "quiz·ask·파일 도구·plan·probe_done은 항상 켜져 있다"고 쓰지만 이를 지키는 것은 설정 쓰기 검증(`WRITABLE_TOOL_KEYS`)이고, 교사 팩토리의 `filterEnabledTools`는 `quiz`·`explain` 키만 제외하고 이름 무관하게 `false`를 뺀다. 프로버의 `probe_done`만 필터 뒤에 다시 붙어 팩토리 수준에서도 보호된다. 팩토리 동작을 사실로 썼다(R-01) |
| 문서·코드 차이 | `agent/tools/plan.ts:71` vs `prompts/teacher/10-planning.md:22` | "5–15 노드, 압축" vs "크기 상한 없음". 어느 쪽도 강제되지 않음(R-05; `src`·`components`에서 `nodes.length`·`edges.length`·`MAX_NODES` 계열을 다시 검색해 해석기의 `=== 0` 검사 외에 비교 없음, 수락 사례는 T-15) |
| 문서·코드 차이 | `core/contracts/plan.ts:82-102` `derivePlanStatuses`(UIMessage 판) | 같은 파생의 옛 판이 남아 있다. 현재 기록 형식에 쓰이는 것은 `derivePlanStatusesLh`(`:132-149`)이고 둘의 규칙은 같다. 구현을 사실로 썼다 |
| T-01~T-28 | 구현에서 도출 | 실행·원본 테스트 미열람. T-16~T-28은 재구현 검증(RESULT.md) 지적을 원본 코드로 확인해 추가 |

### 2.2 코드 읽는 순서 [선택]
`tools/plan.ts` → `tools/mermaid-plan.ts` → `core/plan-tree.ts` → `core/contracts/plan.ts`(파생) → `tools.ts:352-391`(`nodeId` 검증) → `core/phases.ts`(단계) → `prompts/teacher/10-planning.md`.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 코드를 복사한 범위 없음.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점(걸리는 곳) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-06, R-09 | 지도는 앱 화면(라이브 다이어그램)에 보이도록 설계됐다. 위치는 질문 호출의 `nodeId` 태그에서만 파생한다 | 터미널 스킬에는 별도 계획 창이 없고 질문 도구 호출도 없을 수 있다 | 계획을 텍스트(mermaid 또는 목록)로 보여 주고, 위치는 학습 기록 파일의 "현재 노드" 같은 필드로 대체할 수 있다. 그 경우 "위치를 저장하지 않고 파생한다"는 원본 성질이 바뀐다(T-10, T-11이 바뀜) |
| R-15 | 제시 후 학습자 확인을 기다리는 것은 프롬프트 규칙뿐이다 | 터미널에서는 확인을 묻는 한 턴으로 충분 | 변경 없음 |
