---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/learnharness/src/agent/prompts/teacher/05-method.md
  - repos/learnharness/src/agent/prompts/teacher/20-teaching.md
  - repos/learnharness/src/agent/prompts/teacher/28-predictions.md
  - repos/learnharness/src/agent/prompts/teacher/30-question-principles.md
  - repos/learnharness/src/agent/prompts/shared/16-mental-model.md
  - repos/learnharness/src/agent/prompts/shared/20-question-tools.md
  - repos/learnharness/src/agent/prompts/shared/25-confidence.md
  - repos/learnharness/src/core/question-core.ts
  - repos/learnharness/src/agent/tools.ts
  - repos/learnharness/src/agent/teacher-agent.ts
  - repos/learnharness/src/agent/prompt-segments.ts
  - repos/learnharness/src/agent/subagents/extraction.ts
  - repos/learnharness/src/core/argument-heal.ts
  - repos/learnharness/src/agent/tools/heal.ts
  - repos/learnharness/src/agent/tools/jobs.ts
  - repos/learnharness/src/agent/tool-execute.ts
  - repos/learnharness/src/core/value-debris.ts
  - repos/learnharness/src/core/coverage.ts
  - repos/learnharness/src/core/pending.ts
  - repos/learnharness/src/core/prompt-segments.ts
  - repos/learnharness/src/server/settings-body.ts
  - repos/learnharness/components/chat.tsx
depends:
  - ./question-answer-contract.md
  - ./plan-tree.md
  - ./probe-measurement.md
status: ready
reimplementation: "Python 3 표준 라이브러리, [강제] R-ID의 순수 검증·변환·파생 로직만(권고 규칙과 UI는 제외). 4개 스펙(question-answer-contract, probe-measurement, plan-tree, teaching-cycle)의 1.6 T-ID 전부를 포함해 83개 테스트 통과. 원본과 같은 입력으로 비교하지 않음(원본은 TypeScript이고 실행하지 않았다). 결과: ../../../artifacts/learnharness/reimplementation/core/RESULT.md"
---

# 가르치기 (교사)

> 계획 지도를 따라 학습자가 이미 참으로 받아들인 것에서 출발해 한 번에 한 추론 단계씩 가르치고, 단계마다 예측 → 설명 → 확인의 사이클로 이해를 검증하며, 틀리면 진단·보강한 뒤에만 다음 단계로 간다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 계획이 제시되고 학습자가 합의하면(`plan-tree.md`) 교사가 첫 노드의 첫 단계로 들어간다.
2. **예측(predict)**: 아직 가르치지 않은 다음 단계에 대해 질문 도구를 `type:"predict"`로 부른다. 학습자 답이 오면 그 예측을 먼저 해소하며 가르치기를 연다.
3. **설명**: 한 단계 = 한 사실. 학습자가 이미 참으로 가진 것에서 동기 있는 한 걸음으로 새 사실에 도달하게 서술하거나(설명식) 학습자가 먼저 시도하게 하고 공개한다(소크라테스식).
4. **확인(check)**: 단계 설명이 끝난 뒤 `type:"check"`로 질문한다. 설명이 기록에서 확인보다 위에 있어야 한다. 화면에서는 확인이 "Check your understanding" 버튼 뒤에 접혀 있다.
5. 확인 답의 정오·확신도·사고글(읽는 동안의 생각 포함)을 읽는다. 틀렸으면 그 단계가 안 닿은 것이므로 진단·보수·재설명을 하고 다음 확인 전에는 위에 쌓지 않는다. 맞았으면 다음 단계의 예측으로 간다.
6. 모든 질문 호출의 `nodeId`가 지도 위 위치를 정한다. 학습자가 드러낸 사고가 계획과 다르면 `plan_init`으로 지도를 다시 쓴다.
7. 세션의 교사 설명문(텍스트)은 이후 지식 그래프 추출의 입력이 된다.

### 1.2 범위·통합 지점 [필수]
- 제공: 교사가 따라야 하는 교수법(두 원칙, 단계 규칙, 예측·확인 사이클, 확인 질문 원칙, 학습자 답 읽기)과 그 중 코드가 강제하는 부분(교사 질문 도구의 `type`·`nodeId` 필수, 접힘 규칙, 위치 태그, 프롬프트 조립 순서).
- 제외:
  - 질문 도구의 입력·답 계약·확신도 칸 → `question-answer-contract.md`.
  - 계획 작성·`nodeId` 검증·위치 파생·단계 판정 → `plan-tree.md`. 프로브 → `probe-measurement.md`.
  - 작업(job) 프로토콜과 깨움, `research`·`pdf`·`demo`·`visual` 하위 에이전트(지도 행 10~12, `미작성`). 교사 프롬프트의 `40-jobs.md`, `50-demos.md`는 이 스펙이 다루지 않는다(교사 프롬프트 조립에는 포함됨, R-01).
  - 지식 그래프 추출·원장(행 13, 15, `미작성`). 여기서는 R-08에서 입력이 어떤 텍스트인지(assistant 텍스트 블록뿐)와 줄 서식만.
  - 컨텍스트 컴팩션(행 9), 프롬프트 사용자 오버라이드(행 7, `미작성`).
  - 화면의 접힘·읽기 사고 필드 UI 구현. 접힘 규칙의 데이터 의미만 R-03에.
- 외부 의존: 질문 도구와 답 계약, 계획 트리와 `nodeId` 검증, 세션 기록, 교사 에이전트가 프로브 이후 세션에서 만들어진다는 단계 이음새. 에이전트 루프(pi)가 도구 인자를 실행 전에 스키마로 검증하는 것(TypeBox `Value.Convert` 뒤 `Value.Check`, 주석 근거)과 그 거절 결과의 문구·모양은 이 레포 밖 라이브러리 소관이라 정하지 않는다. 이 스펙의 "스키마가 거절한다"는 "`execute`가 불리지 않고 오류 결과가 모델에게 돌아간다"까지만 뜻한다.
- 소유 상태·부작용: 이 기능 자체는 상태를 소유하지 않는다. 교사의 질문 호출·설명문·답이 세션 기록에 쌓이고 그것이 위치와 지식 그래프의 원천이 된다.

### 1.3 인터페이스와 데이터 의미 [필수]

**교사의 질문 도구가 이 기능에서 더하는 필드**(나머지 필드는 `question-answer-contract.md`)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `type` | "predict" \| "check" (필수, 두 리터럴의 합집합, 따옴표 없는 맨 단어) | 그 질문의 사이클 속 역할. `predict` = 단계를 가르치기 전에 던지는 질문(자기 턴, 열린 채 도착), `check` = 단계 설명이 끝난 뒤 던지는 질문(접힌 채 도착) |
| `nodeId` | string (필수) | 이 질문이 다루는 계획 노드의 정확한 id. 위치는 이 태그에서 파생된다(`plan-tree.md`). 스키마는 문자열이기만 하면 통과시키고(빈 문자열 포함) 트리 소속은 실행 단계의 `nodeId` 검증(`plan-tree.md` R-10)이 본다 |

두 필드는 스키마의 맨 앞 속성이다(모델이 긴 호출에서 뒤쪽 필드를 빼먹는 일이 있어 가장 덜 빠뜨리게 앞에 둠).

**화면 도달 규칙**(데이터 의미): 질문이 접힌 채 도착해야 하는지는 함수 `questionNeedsReveal(tool, input, phase)`가 정한다.

| 도구 | 단계 | `type` | 접힘(확인 버튼 뒤) |
|---|---|---|---|
| `quiz` 또는 `explain` | `teach` | `predict` | 아니오(열림) |
| `quiz` 또는 `explain` | `teach` | `check` 또는 `type`이 없음/알 수 없음(옛 기록) | 예 |
| 그 밖의 모든 경우(`probe`, `recall`, `ask_user_question`, 다른 단계) | — | — | 아니오 |

### 1.4 행동 규칙과 남은 질문 [필수]
범례: **[강제]** 코드가 지킴, **[권고]** 프롬프트가 모델에게 요청할 뿐 코드는 막지 않음. 아래 [권고] 규칙은 모델이 따르는지 실행으로 확인하지 못했다(확인 한계).

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] 교사 에이전트 구성 | 도구(`createTeacherTools`): `quiz`(설정 `explain:true`이면 `quiz` 대신 `explain`, 둘이 함께 있지 않음) + `ask_user_question` + `read`·`ls`·`find`·`grep` + `plan_init` + 작업 도구 넷(`research`·`demo`·`visual`·`pdf`, 조건 없이 모두 만들어짐). 이 목록에서 `enabled[이름]===false`인 도구는 `quiz`·`explain` 키를 제외하고는 이름과 무관하게 빠진다(`quiz:false`는 효과 없음). 설정 쓰기가 허용하는 키는 `research`·`demo`·`visual`·`pdf`·`explain`뿐이라 `quiz`·`ask_user_question`·파일 도구·`plan_init`은 설정으로 못 끄지만 그것은 쓰기 검증의 보장이고 팩토리의 보장이 아니다(`plan-tree.md` R-01). 완성된 레지스트리의 모든 도구는 인자 복구 래퍼로 감싸진다(R-02). `ctx` 없이 만든 교사 에이전트(테스트 경로, 핸들러는 항상 `ctx`를 넘김)는 `nodeId` 검증 없는 `quiz`와 `ask_user_question`만 가진다. 시스템 프롬프트는 `system-prompt.md` → `teacher/` 번호 접두 조각(정렬: `05-method`, `10-planning`, `20-teaching`, `28-predictions`, `30-question-principles`, `40-jobs`, `50-demos`) → `shared/` 조각(`10-voice`, `15-accuracy`, `16-mental-model`, `20-question-tools`, `25-confidence`, `30-learner-files`, `40-formatting`)을 이은 것. 조각은 파일명이 `^\d+-[\w.-]+\.md$`인 `.md`만 대상이고 폴더 안에서는 파일명 기본 문자열 정렬(사전식이라 접두 숫자 자릿수가 다르면 `100-x`가 `20-y`보다 앞)이며, 조각마다 `trim()`하고 빈 조각은 버린 뒤 `\n\n---\n\n`(빈 줄, `---`, 빈 줄)으로 잇는다. 오버라이드 스위치가 켜져 있고 오버라이드 파일이 있는 조각은 그 텍스트로 대체된다(행 7, `미작성`) | 코드 확인 |
| R-02 | [강제] 교사의 `quiz`/`explain` 호출 | `type`("predict"/"check" 둘 중 하나)과 `nodeId`가 모두 필수다. 빠지거나 값이 다르면 실행 전 스키마 검증에서 거절되고(1.2) 질문을 같은 턴에서 고쳐 다시 부르게 된다. **인자 복구**(`healEncodedArguments`): 스키마 검증보다 앞의 `prepareArguments` 단계에서 돈다. 도구 고유의 준비 단계(질문 도구는 `options`가 문자열이면 JSON으로 푼다)가 먼저 돌고 그 결과에 복구가 적용된다. 복구 대상은 (a) 인자가 객체(배열 아님)이고 스키마가 최상위 `properties`를 가질 때, (b) 그 속성의 **값이 문자열**일 때뿐이며 중첩 속성은 보지 않는다. 문자열을 `JSON.parse`해(실패하면 복구 안 함) 속성 종류별로 본다: 리터럴 합집합이면 원문이 이미 허용 값이면 그대로 두고, 파싱 결과가 허용 값 중 하나면 그 값으로 교체한다(따옴표가 값에 박힌 `"\"predict\""`가 `predict`로 풀리는 경로); null 허용이면 `"null"`→null; boolean이면 `"true"`/`"false"`→불리언; number/integer면 숫자로 파싱되는 문자열→숫자; array면 JSON 배열 문자열→배열. 어디에도 해당하지 않으면 건드리지 않는다(문자열 속성인 `nodeId`는 대상이 아니다). 복구된 키가 없으면 입력과 같은 객체를 돌려주고 있으면 그 키만 바꾼 얕은 복사본을 돌려준다(멱등). 따라서 `'predict'`(작은따옴표)·`Predict`·`predict `(공백)은 JSON이 아니거나 허용 값이 아니라 복구되지 않고 스키마가 거절한다. 같은 복구를 레지스트리의 모든 도구에 씌우고, 화면 파싱도 같은 함수로 한 번 더 복구한다(기록에는 원 인자가 남는다는 주석 근거) | 코드 확인(필수·열거·복구 규칙: `argument-heal.ts` 본문 전체) |
| R-03 | [강제, UI] 접힘 규칙 | 1.3의 표대로. 예측은 어떤 경우에도 접히지 않는다(가르침을 게이트하므로). 이 규칙은 도달 방식만 정하고 모델이 예측을 먼저 던지는지는 강제하지 않는다. 판정에 쓰는 `type`은 표시 쪽의 정규화(`normalizeQuizType`)를 거친다: 문자열이 아니면 "없음"이고, 문자열이면 양끝의 연속된 공백·`:`·`.`·`"`·`'`·백틱을 벗긴 뒤 정확히(대소문자 구분) `predict` 또는 `check`일 때만 그 값, 아니면 "없음"이다. `predict`가 아니면 모두 접힘이므로 인자 복구가 못 푼 원 기록의 `"\"predict\""`·`":predict"`도 화면에서는 열린 채 도착한다 | 코드 확인 |
| R-04 | [강제] 위치 | 질문 호출의 `nodeId` 태그가 지도 위치를 움직이며 `type`과 정오는 무관하다. 예측도 확인도 같은 방식으로 위치를 정한다 | 코드 확인(`plan-tree.md` R-09) |
| R-05 | [강제] 한 턴에 질문 하나 | 도구가 막지는 않으나 질문 도구는 모두 `executionMode:"sequential"`이라 병렬 질문은 호출 순서대로 순차 실행되고 마지막 답이 올 때만 반응 턴이 시작된다(`question-answer-contract.md` R-08, R-18). 한 턴에 하나는 프롬프트 권고(R-16) | 코드 확인 |
| R-06 | [강제] 확인 질문 정답 노출 | 객관식은 답 뒤 `explanation`이, 자유서술은 제출 뒤 `committed`가 화면에 보인다(질문 계약). 모델이 채점 기준을 질문 앞에 확정한다 | 코드 확인(`question-answer-contract.md` R-13) |
| R-07 | [강제] 질문이 검증 실패 | `execute` 단계의 검증(질문 계약의 문제들 + `nodeId` 문제)이 실패하면 `isError:true`, content `Invalid tool input for tool "quiz":\n- <문제>…`(`plan-tree.md` R-10)로 모델에게 돌아가고 학습자에게는 질문이 가지 않는다. 턴 종료 판단(`makeQuestionStopper`)은 이번 배치의 질문 호출(`quiz`·`probe`·`ask_user_question`·`explain`·`recall`)의 결과 중 `isError`가 하나라도 있으면 턴을 끝내지 않으므로 모델이 같은 턴에서 재시도하고, 모두 정상이면 턴을 끝낸다(질문 호출이 없는 배치는 이 규칙이 끝내지 않는다). 스키마 단계 거절의 결과가 `isError`로 오는지는 외부 라이브러리라 코드로 못 읽었다(`추론`: 주석이 "검증 실패는 같은 턴에서 재시도"라고 쓴 `teacher-agent.ts:132-140`) | 코드 확인(`execute` 단계), 스키마 단계는 추론 |
| R-08 | [강제] 설명문의 용도 | 그래프 추출기의 입력은 `proseView`가 만든다. 모든 메시지에 `messageViewLines(message, message.id)`를 적용해 **`role`이 `assistant`인 메시지**만 줄을 만든다(학습자 메시지·`toolResult`·마커 메시지는 줄 없음). `content`가 문자열이면 공백 제거 뒤 비어 있지 않을 때 한 줄, 배열이면 `type:"text"` 블록 중 공백만이 아닌 것마다 한 줄이고(사고 블록·도구 호출 블록·빈 텍스트 제외) 줄 서식은 `TEACHER [<메시지 id>] <텍스트를 trim한 것>`이다. 줄은 빈 줄(`\n\n`)로 잇고 세션 제목이 비어 있지 않으면 앞에 `# <제목>\n\n`을 붙인다(줄이 없어도 제목은 붙음). "TEACHER"는 역할 판별이 아니라 모든 assistant 메시지의 고정 접두어라서 프로브 단계의 assistant 텍스트도 입력에 들어간다(`role`만 보고 프로버와 교사를 가르지 않음). 교사의 설명문이 지식 그래프의 원천이다 | 코드 확인(`extraction.ts:126-139`, `coverage.ts:29-55`) |
| R-09 | [권고] 방법의 호 | 학습자가 이미 참으로 가진 것에서 시작해 한 번에 한 추론 단계씩 간다. 이해의 목표는 범위가 아니라 깊이이고 진도 일정은 없다. "클릭" = 낱낱의 사실이 소수의 생성 사실로 무너져 구조가 되는 순간이며 세션의 종료 조건은 목표 이해가 낱 사실이 아니라 그 구조 안에서 당연한 것이 된 상태 | 코드 확인(프롬프트 텍스트) |
| R-10 | [권고] 원칙 i: 무조건적 진실 먼저 | 주의·예외 없이 그대로 받아들일 수 있는 사실부터 굳힌다. 위에 쌓기 전에 각 기초가 그 학습자에게 정말 당연하게 읽히는지 짧게 확인하고, 흔들리면 멈추고 기초를 고친다. "무조건적 진실"은 그 사실이 **어떻게 받아들여지는가**의 속성이고 "공리"는 **그래프 어디에 있는가**(아무 것에서도 도출되지 않음)의 속성이어서 겹치지만 같지 않으니 기본은 "무조건적 진실"이라고 부르고 공리는 정말 바닥일 때만 쓴다. 강한 형태 둘: 예외 없는 전칭 진술("모든 X는 Y"), 진짜 정의(성질 나열이 아닌 것) | 코드 확인(프롬프트 텍스트) |
| R-11 | [권고] 원칙 ii: "내가 어떻게 직접 발견할 수 있었을까" | 모든 단계에 동기를 붙인다: 왜 이걸 하는가에서 시작해, 왜 이 식을 시도하고 왜 이렇게 변형하는지까지. 결과는 연결 안 된 명제가 연결된 명제가 되는 것(간선 추가). 아무 것도 허공에서 나오지 않게 한다 | 코드 확인(프롬프트 텍스트) |
| R-12 | [권고] 단계 규칙 | ① 한 단계 한 사실(설명이 둘 필요하면 두 단계) ② 그 단계에 가장 흡수가 좋은 형태를 단계마다 고른다(기초 무조건적 진실은 그냥 단언, 유도 단계는 서술하거나 학습자에게서 끌어냄) ③ 연결은 산문의 흐름에 두고 연결 자체가 수업일 때만 명시. "이제 X를 세우고 Y에 잇겠습니다" 같은 진행 안내와 노드 장 제목("Node 3: …")은 쓰지 않는다(지도는 학습자의 풍경이지 길이 아님) ④ 매 단계 이해 확인. 틀리면 진단·보수·강화 후에만 위에 쌓는다. 학습자가 보여 주지 않은 단계 위에 쌓지 않는다 ⑤ 믿음에 기대는 주장이 있으면 받아들이기 쉽게 동기를 주거나 쌓기 전에 확인 ⑥ 한 가닥에서 경계가 불확실하면 다음 단계 전에 보유한 곳에서 모르는 곳으로 가는 짧은 `quiz` 연속으로 재탐색. 방법은 내부 규율이고 출력은 팽팽하고 명료해야 한다(장황함은 간접비) | 코드 확인(프롬프트 텍스트) |
| R-13 | [권고] 소크라테스식 vs 설명식 | 주제와 학습자의 에너지에 따라 구간마다 고른다. 학습자가 추론으로 도달할 수 있어 보이면 소크라테스식(동기 문제를 던져 발견을 시도시킨 뒤 공개, 기본값), 맨 추론으로는 닿기 어렵거나 에너지가 낮거나 전달을 원하면 설명식. 정답이 있는 질문은 열린 형태여도 `quiz`/`explain`으로 묻고(채점 가능), `ask_user_question`은 정답 없는 갈림길(선호·방향·다음에 원하는 것)에만 쓴다 | 코드 확인(프롬프트 텍스트) |
| R-14 | [권고] 예측(predict) | 단계를 가르치기 **전**에 자기 턴으로 던지고 학습자가 먼저 답한 뒤 가르침이 그것을 해소한다. 주제는 **다음** 단계(아직 안 가르침)이고 지금까지 내용으로 답할 수 있지 않아도 된다. 시험이 아니라 넌지시 건네는 질문: 현재 상태의 문제를 짚되 더 알려 주지 않고 발견하려 시도하게 한다. 완전히 시도하지 못해도 괜찮고 시도 자체가 목적. 답이 오면 가르침을 시작할 때 예측을 명시적으로 해소한다(학습자가 예측한 것, 실제 참인 것, 이유). 다음 단계가 없는 턴(마무리, 오답 뒤 순수 보수)에서는 예측을 생략하되 습관으로 만들지 않는다 | 코드 확인(프롬프트 텍스트) |
| R-15 | [권고] 확인(check) | 단계 가르침이 **끝난 뒤** 던진다. 결과는 이후를 정하는 데이터: 계속, 보수, 재명확화 | 코드 확인(프롬프트 텍스트) |
| R-16 | [권고] 사이클과 도달 규율 | 순서: 예측 → 학습자의 예측 → 가르침(예측 해소) → 확인 → 학습자의 답 → 반응 → 다음 예측. 한 턴에 질문 하나. **설명·다이어그램·예제는 모두 확인보다 위에**(앞에 글이 없는 확인은 실패한 확인). 생각을 끝낸 뒤에만 확인을 발사하고 설명 중간에 쏘지 않는다. 오답이면 가르침을 재개(진단·보수·재설명)한 뒤에만 다음 확인. 확인 버튼은 관문이지 퀴즈쇼 벨이 아니다. 열린 질문이 수업 중간에 있어도 괜찮지만 그에 속한 글을 먼저 쓴다 | 코드 확인(프롬프트 텍스트) |
| R-17 | [권고] 확인 질문의 원칙 | 그 세션에서 다룬 것만으로 추론해 답할 수 있어야 한다(길이 없는 확인은 동전 던지기). 방금 위 문장을 외워 되돌리게 하지 않는다. 새 사례에 적용·예측·확장하는 **적용 문제**를 먼저 쓰고 정말 적용할 수 없을 때만 회상 확인을 폴백으로 쓴다. 오답이 어떤 잘못된 모델인지 이름이 붙게 설계한다(객관식에서는 각 오답이 특정 오개념을 가진 사람의 답). 답은 신호지 판결이 아니다: 우연히 맞은 것은 아무 것도 아니고 정직한 확인의 오답은 금이다. 이 원칙은 `check`에 적용되고 예측은 처음 두 원칙을 의도적으로 어긴다 | 코드 확인(프롬프트 텍스트) |
| R-18 | [권고] 학습자 답 읽기 | 정오·확신도 해석표(`question-answer-contract.md` R-21)와 사고 필드 두 채널을 함께 읽고 모델의 학습자 상을 답마다 고친다. 학습자 이해가 계획과 다르면 계획이 고쳐진다(`plan-tree.md` R-17). 정답을 흐리게 하거나 친절로 틀린 답을 맞다고 하지 않는다 | 코드 확인(프롬프트 텍스트) |

- 불변식: 교사 질문 호출은 항상 `type`과 `nodeId`를 가지며(R-02) 위치는 `nodeId`에서만 파생된다(R-04). 전제: 이 규칙들은 모델이 프롬프트를 따를 때 의도한 효과를 낸다. 코드가 강제하는 것은 R-01~R-08이다.
- 미결정: 없음
- 확인 한계: 코드를 실행하지 않았고 테스트를 열지 않았다. 스키마 단계 거절의 결과 문구·`isError` 여부와 `Value.Convert`가 바꾸는 값은 외부 라이브러리(pi)라 읽지 못했다(1.2, R-07). R-09~R-18은 프롬프트가 요구하는 것을 읽은 것이며 모델이 실제로 따르는 정도(예: 확인보다 설명을 먼저 쓰는지, 오답 뒤 재설명을 하는지)는 미확인이다. 화면의 접힘이 실제로 렌더되는 모양은 `chat.tsx`의 `requiresReveal` 호출 한 곳만 확인했다.

### 1.5 필수 코드 참조 [필수]
라이선스는 AGPL-3.0(overview 1절)이다. 프롬프트는 본문 인용 없이 파일:줄 범위로만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/question-core.ts:209-248` `QUIZ_QUESTION_TYPES`, `normalizeQuizType`, `questionNeedsReveal`, `predictCheckType`; `:256-268` `quizInputObject`; `:326-338` `explainInputObject` | 교사 질문 입력(`type`·`nodeId` 필수), 접힘 규칙 | R-02, R-03 |
| C-02 | `components/chat.tsx:508` | 접힘 규칙을 쓰는 곳(화면은 이 한 지점에서 판단) | R-03 |
| C-03 | `src/agent/tools.ts:221-239` `teachExplainToolFor`; `:352-391` `nodeIdProblem`, `teachQuizToolFor`; `:434-466` `createTeacherTools` | 교사 도구 구성과 질문 실행 | R-01, R-02, R-07 |
| C-04 | `src/agent/teacher-agent.ts:74-81` `composeInstructions`; `src/agent/prompt-segments.ts:62-97` `listSourceSegments` | 교사 프롬프트 조립 | R-01 |
| C-05 | `src/agent/prompts/teacher/05-method.md:1-44` | 방법의 두 원칙 | R-09~R-11 |
| C-06 | `src/agent/prompts/teacher/20-teaching.md:1-33` | 단계 규칙, 소크라테스식/설명식, 도달 규율 | R-12, R-13, R-16 |
| C-07 | `src/agent/prompts/teacher/28-predictions.md:1-22` | 예측·확인·사이클 | R-14~R-16 |
| C-08 | `src/agent/prompts/teacher/30-question-principles.md:1-11` | 확인 질문 원칙 | R-17 |
| C-09 | `src/agent/prompts/shared/16-mental-model.md:1-5`; `shared/25-confidence.md:1-11`; `shared/20-question-tools.md:5-28` | 답 읽기(사고글·확신도·질문 제작) | R-18 |
| C-10 | `src/agent/subagents/extraction.ts:126-139` `proseView` | 그래프 추출 입력은 교사 텍스트뿐 | R-08 |
| C-11 | `src/core/argument-heal.ts:1-24`, `:58` `healEncodedArguments` | 문자열로 감싼 enum 값 복구 | R-02 |
| C-12 | `src/core/coverage.ts:29-55` `textOf`, `messageViewLines` | 추출기 입력의 줄 선택·서식(`TEACHER [id] text`) | R-08 |
| C-13 | `src/core/argument-heal.ts:25-96` 헬퍼와 `healEncodedArguments` 본문; `src/agent/tools/heal.ts:30-48` `withArgumentHeal`, `healToolRecord`; `src/agent/tools.ts:59-77` `prepareQuestionArguments` | 인자 복구 규칙 전체와 적용 순서 | R-02 |
| C-14 | `src/core/value-debris.ts:20-26` `stripModelValueDebris` | 접힘 판정용 `type` 정규화에서 벗기는 글자 | R-03 |
| C-15 | `src/agent/teacher-agent.ts:132-169` `makeQuestionStopper`; `:269-308` `createTeacherAgent`, `bareQuestionTools`; `src/agent/tool-execute.ts:117-131` `invalidInputResult` | 검증 실패 뒤 턴 계속 규칙, ctx 없는 에이전트, 오류 결과 모양 | R-01, R-07 |
| C-16 | `src/core/pending.ts:60-106` `TOGGLEABLE_TOOLS`, `WRITABLE_TOOL_KEYS`, `filterEnabledTools`; `src/server/settings-body.ts:156-172`; `src/agent/tools.ts:416-432` `quizMechanics`, `withoutMechanics`; `src/agent/tools/jobs.ts:131-166` `jobTools` | 도구 토글과 제외 키, 작업 도구는 조건 없이 생성 | R-01 |
| C-17 | `src/core/prompt-segments.ts:17` `FRAGMENT_RE`; `src/agent/prompt-segments.ts:105-125` `effectivePromptSegments` | 조각 파일 이름 규칙과 오버라이드 대체 | R-01 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 코드를 실행하거나 원본 테스트를 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 교사의 `quiz` 호출에 `type` 누락 / `nodeId` 누락 | 스키마가 거절, `execute` 미호출 |
| T-02 | R-02 | `type:"maybe"` | 스키마가 거절(열거 값은 `predict`, `check`뿐) |
| T-03 | R-02 | `type:"\"predict\""`(따옴표 포함) | 복구되어 `predict`로 통과(`argument-heal.ts` 본문 근거) |
| T-04 | R-03 | `questionNeedsReveal("quiz", {type:"check"}, "teach")` / `("quiz",{type:"predict"},"teach")` / `("explain",{},"teach")` / `("quiz",{type:"check"},"plan")` / `("ask_user_question",{},"teach")` / `("probe",{},"probe")` | true / false / true(옛 기록은 check) / false / false / false |
| T-05 | R-04 | 트리 {a,b}. 호출 순서 `quiz(predict,a)`, `quiz(check,a)`, `explain(check,b)` | `current=b`, `visited={a}`(`plan-tree.md` T-10과 같은 규칙) |
| T-06 | R-02, R-07 | `nodeId`가 트리에 없는 `quiz` | 오류 결과, 질문이 학습자에게 가지 않음, 같은 턴에서 재시도 |
| T-07 | R-01 | 교사 프롬프트 조립 | `system-prompt.md`, `teacher/05,10,20,28,30,40,50`, `shared/10,15,16,20,25,30,40` 순서, 조각마다 `trim`·빈 조각 제외, 사이는 `\n\n---\n\n` |
| T-08 | R-08 | 세션에 교사 텍스트·학습자 메시지·`quiz` 호출이 섞여 있음 | 추출기 입력에는 assistant 텍스트 블록만 들어감 |
| T-09 | R-02 | `type`이 `"'predict'"` / `"Predict"` / `"predict "` | 복구되지 않고 스키마가 거절(값은 원문 그대로) |
| T-10 | R-02 | 트리에 `a`가 있고 `nodeId:"\"a\""`(따옴표 포함) | 복구되지 않고 `nodeId` 검증이 원문 그대로 인용해 거절 |
| T-11 | R-02 | 복구 함수에 (스키마 속성 → 인자): `k`가 `["a","b"]` 합집합일 때 `{k:"\"a\""}` / `{k:"a"}`; `n`이 number일 때 `{n:"3"}`; `s`가 string일 때 `{s:"3"}`; `b`가 boolean일 때 `{b:"true"}`; 배열 인자 | `{k:"a"}` / 입력과 같은 객체(같은 참조) / `{n:3}` / 입력 그대로(문자열 속성은 대상 아님) / `{b:true}` / 입력 그대로 |
| T-12 | R-03 | `questionNeedsReveal("quiz",{type:"\"predict\""},"teach")` / `("quiz",{type:":predict."},"teach")` / `("quiz",{type:"Predict"},"teach")` / `("quiz",{type:3},"teach")` | false / false / true / true |
| T-13 | R-01 | 교사 도구 레지스트리를 설정 `{}` / `{explain:true}` / `{research:false}` / `{quiz:false}`로 만듦 | 순서대로: `quiz` 있고 `explain` 없음 / `explain` 있고 `quiz` 없음 / `research`만 빠짐 / 효과 없음. 어느 경우든 `ask_user_question`, 파일 도구 넷, `plan_init`, `demo`·`visual`·`pdf`는 있고, 모든 도구가 복구 래퍼를 거침(`{k:"\"a\""}` 같은 입력이 풀림) |
| T-14 | R-01 | 프롬프트 폴더에 `100-x.md`(본문 `"  A\n"`), `20-y.md`(본문 `""`), `30-z.md`(본문 `"B"`), `README.md` | `README.md`는 제외, 순서는 `100-x.md`, `20-y.md`, `30-z.md`(사전식). 본문은 `trim`하고 빈 조각을 버려 `A\n\n---\n\nB` |
| T-15 | R-07 | 한 배치의 질문 호출 둘 중 하나의 결과가 `isError:true` / 모두 정상 / 질문 호출이 없는 배치 | 턴을 끝내지 않음(재시도) / 끝냄 / 끝내지 않음 |
| T-16 | R-08 | id `m1` assistant 메시지 content `[사고 블록, text " hi ", 도구 호출, text "  "]`, id `m2` assistant 메시지 content가 문자열 `"  x "`, user 메시지, 제목 `T` | 입력은 정확히 `# T\n\nTEACHER [m1] hi\n\nTEACHER [m2] x` |


## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@b277ee3) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03, C-04, C-15~C-17 | 소스 전문 읽음. `git ls-tree`로 `teacher/`·`shared/` 파일 목록 확인(7개씩). 쓰기 검증의 400 변환은 라우트 쪽이라 미열람 |
| R-02 | C-01, C-11, C-13 | 스키마 전문 읽음. 복구 동작은 `argument-heal.ts` 본문 전체(C-13)로 확인(이전에는 머리 주석만 읽었음) |
| R-03 | C-01, C-02, C-14 | `question-core.ts:212-235` 전문, `value-debris.ts` 전문, `chat.tsx:508` 호출 한 곳 |
| R-04, R-05, R-06, R-07 | C-03, C-15, `plan-tree.md`, `question-answer-contract.md` | 소스 전문 읽음. R-07의 스키마 단계는 주석 근거 |
| R-08 | C-10, C-12 | `proseView`와 `messageViewLines`·`textOf` 본문 전체 읽음. 추출 배치(`extraction.ts:1139-1165`)가 같은 `proseView`를 쓰는 것도 확인 |
| R-09~R-18 | C-05~C-09 | 프롬프트 전문 읽음 |
| 문서·코드 차이 | `prompts/teacher/20-teaching.md:33`, `components/chat.tsx:508`, `question-core.ts:223-235` | 프롬프트는 "이 접힘 법칙은 `ask_user_question`에도 적용된다: 확인처럼 버튼 뒤에 도착한다"고 쓰지만 `questionNeedsReveal`은 `quiz`/`explain`만 접고 `ask`는 접지 않는다(함수 주석도 "ask는 접지 않는다"). 구현을 사실로 썼다(1.3 표) |
| 문서·코드 차이 | `core/pending.ts:65-78`, `agent/teacher-agent.ts:111-115` 주석 | "quiz·ask·파일 도구·plan·probe_done은 항상 켜져 있다"고 쓰지만 이를 지키는 것은 설정 쓰기 검증이고 교사 팩토리는 `quiz`·`explain` 키만 제외하고 `false`인 이름을 모두 뺀다(R-01, `plan-tree.md` 2.1). 팩토리 동작을 사실로 썼다 |
| 문서·코드 차이 | `prompts/teacher/20-teaching.md:10`, `:22`, `28-predictions.md` | 프롬프트는 도구 이름 `quiz`를 쓰지만 자유서술 설정이면 `explain`이 등록된다. `10-planning.md:33`은 "`quiz` 또는 `explain`"을 병기한다. 구현을 사실로 썼다(R-01) |
| T-01~T-16 | 구현에서 도출 | 실행·원본 테스트 미열람. T-09~T-16은 재구현 검증(RESULT.md) 지적을 원본 코드로 확인해 추가 |

### 2.2 코드 읽는 순서 [선택]
`prompts/teacher/05-method.md` → `20-teaching.md` → `28-predictions.md` → `30-question-principles.md` → `core/question-core.ts:209-268` → `agent/tools.ts:352-391` → `components/chat.tsx:508`.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 코드를 복사한 범위 없음.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점(걸리는 곳) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-03, R-16 | "Check your understanding" 접힌 버튼, 읽는 동안의 사고 필드, 확신도 슬라이더는 앱 UI의 일부다 | 터미널에는 접힌 버튼이 없다 | 설명을 쓴 뒤 같은 턴 끝에 확인 질문을 두는 것으로 "설명 먼저, 확인 나중"을 지킬 수 있다. 예측은 설명 전 별도 턴에 던진다. T-04가 바뀐다 |
| R-12, R-14, R-17 | 교수법 규칙(R-09~R-18)은 도구와 무관한 글이라 거의 그대로 쓸 수 있다 | 규칙의 효과는 모델이 따를 때만 나온다 | 변경 없음. 단 터미널에서는 질문 도구 호출이 아니라 텍스트 질문으로 바뀌므로 `type`·`nodeId` 태깅이 필요 없다면 위치 파생이 사라진다 |
