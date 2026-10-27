# practice-session 재구현 검증 결과

기준: `practice-session.md` 1부(1.1~1.6) + frontmatter, 선행 스펙 `question-answer-contract.md` 1부. 원본 SHA `b277ee3e…`를 `git show <SHA>:<path>`로만 읽었다. 원본은 실행하지 않았다. 아래 "통과"는 내가 쓴 테스트가 내 구현에 통과했다는 뜻이고 원본과 같은 출력을 냈다는 주장이 아니다.

## 1. 구현 언어·범위

- Python 3.14, 표준 라이브러리만, 테스트는 `unittest`. 파일: `practice.py`(구현), `test_practice.py`(테스트).
- 구현한 것(순수 상태·검증 로직):
  - `problem`/`conclude` 도구: 인자 복구(JSON 문자열로 감싼 enum·null·불리언·배열 풀기), `target` 정규화, 스키마 검증, 게이트(클로저), 오류 결과·`terminate` 결과.
  - 활성 문제 판정 `active_problem_of`, 건너뜀 대기 판정 `pending_problem_dismissal_of`, 공개 대상 `model_solution_for_conclude`.
  - 입력 파싱·검증·기록 추가(`thinking`/`next`/`dismiss-problem`/`text`/`continue`), 합성 `conclude{dismissed}` 쌍.
  - 마커 모양(`graph-context`, `practice-thinking`, `practice-next`, `problem-dismissed`), 세션 생성(`kind`, 모델 스탬프, 명제 필터·64개 상한, 연쇄 계산·줄 모양), 모델 입력 변환 `to_llm_messages`.
  - 도구 구성 이름 목록·프롬프트 조각 선택·에이전트 종류·컴팩션 종류·추출 트리거 조건(작은 술어 함수).
- 하지 않은 것: LLM 호출, UI, 네트워크, 프롬프트 본문, 영속 저장소, 에이전트 루프(스키마 검증기 자체는 최소 흉내만), 컴팩션 절단.

## 2. 테스트 결과

`python3 -m unittest -v` → **36개 실행, 36 통과, 0 실패**.
- 1.6의 T-01~T-16 16개 모두 옮겼다(테스트 이름에 T-ID). 일부 T-ID는 케이스가 여럿이라 한 테스트 안에서 나눠 확인한다.
- 그 밖에 추측·경계 확인용 테스트 20개(이름에 R-ID 또는 설명).
- 건너뛴 T-ID: 없다. 전부 [강제] 규칙이다.
- 완전히 옮기지 못한 T-ID:
  - T-14 "problem 결과가 기록에 남음": 영속 필터가 순수 층 밖이라 `terminate`·`details:null`·텍스트까지만 확인. "턴이 코드에 의해 끝나지 않음"도 `terminate=False`까지만.
  - T-13 "추출·그래프 쓰기·커버리지가 시작되지 않음": 실제 판단은 서버 배선에 있어서 `extraction_triggered(record, enabled)` 술어로 줄여 테스트했다. 사실상 같은 말을 되풀이하는 테스트라 약한 검증이다.

## 3. R-ID 구현 현황

| R-ID | 상태 |
|---|---|
| R-01 | 구현(세션 생성). `kind` 정확 일치, 모델 스탬프, 필터 후 64개 |
| R-02 | 구현(연쇄 계산·줄 모양) |
| R-03 | 구현(`agent_kind`, `extraction_triggered`). 비연습 분기는 스펙 밖이라 `"teach"` 문자열로만 |
| R-04 | 부분 구현: 도구 이름 목록, 프롬프트 조각 선택. 도구 본체는 `problem`/`conclude`만(`read`/`ls`/`find`/`grep`/`research`/`pdf`/그래프 도구는 이름만) |
| R-05~R-08 | 구현 |
| R-09 | 구현 |
| R-10~R-12 | 구현 |
| R-13 | 구현(마커 평탄화) + QA R-19의 끊긴 호출 합성(스펙 R-13에는 없음). 컴팩션 부분 제외 |
| R-14 | 공개 규칙 구현. "결과를 읽는 곳은 두 UI뿐"은 동작 규칙이 아니라 서술이라 제외 |
| R-15 | 구현(`compaction_kind`, 상수 수준). 실제 동작은 지도 행 9(미작성) |
| R-16~R-26 | [권고]라서 제외 |

QA 스펙(question-answer-contract) 전체는 구현하지 않았다. 연습 세션은 질문 도구를 쓰지 않는다고 practice 1.2에 적혀 있고 지시가 practice의 [강제] 규칙만 범위로 잡았기 때문이다. 연습 쪽이 QA에서 빌려 쓰는 것만 가져왔다: `invalidInputResult` 모양, `INTERRUPTED_TEXT`, 끊긴 호출 합성, `stripModelValueDebris`. `answer`/`dismiss` 입력은 `NotImplementedError`.

## 4. 추측·모호점 목록

(R-ID 또는 T-ID, 스펙이 말하지 않았거나 모호한 점, 내가 정한 방식)

1. R-06/T-01/T-02: "invalid input 오류"의 결과 모양이 practice 스펙에 없다. QA 1.5 C-12(`tool-execute.ts:117-131`)에서 `Invalid tool input for tool "<name>":\n- <문제>`, `isError:true`, `details:{tool,problems}`를 가져왔다. practice 1.5에는 이 참조가 없다.
2. T-05/R-05: "스키마 거절"의 오류 문구·형식이 스펙에 없다(외부 에이전트 루프 담당). 내 검증기가 임의 문구로 `is_error`를 돌려준다. 테스트는 `is_error`만 확인.
3. R-05(스키마): 필수 필드가 빈 문자열이어도 되는지, 추가 필드를 허용하는지 스펙에 없다. 코드의 `Type.String`에 최소 길이가 없는 것을 따라 **빈 `statement`·`modelSolution`을 통과**시키고 추가 필드도 허용했다. 스펙의 "(필수)"를 비어 있으면 안 된다로 읽을 수 있는 문장이다.
4. R-05: 그래프 노드 목록이 있을 때 **배열이 아닌 `target`**(예: 문자열 `"zzz"`, 풀리지 않는 값)은 코드에서 조용히 제거되어 태그 없는 문제로 통과한다. 노드 목록이 없으면 스키마가 거절한다. 스펙은 "풀 수 없는 문자열은 그대로 두어 execute가 거절"이라고만 써서 배열 원소 얘기인지 `target` 전체 얘기인지 모호하다. 코드를 따랐고 그 테스트를 둔다(`test_target_non_array_with_graph_is_silently_dropped`).
5. R-05: 이름 비교 쪽에도 같은 접두·접미 벗기기를 적용하는지, 대소문자 무시 외에 안쪽 공백은 어떤지, 이름이 겹치면 어느 것인지 스펙에 없다. 코드대로 이름도 벗기고, 안쪽 공백은 그대로, 겹치면 노드 저장 순서상 첫 번째로 했다. id 정확 일치가 이름보다 먼저.
6. R-05: 복구 순서가 도구 자체 복구 → 정규화 → 레지스트리 공통 복구(한 번 더, 멱등)인 것은 스펙의 "도구 레지스트리 공통 인자 복구"에서 짐작할 수밖에 없다. 코드 순서를 따랐다.
7. R-06: 오류 메시지의 `target [..]` 형식. 코드의 `JSON.stringify` 모양(공백 없음, 비ASCII 이스케이프 없음, 원문 문자열 그대로)을 따랐다. ①(이미 활성)이 ②(모르는 target)보다 먼저라는 순서도 스펙에는 번호로만 암시된다.
8. R-09: 한 assistant 메시지 안에서 블록을 어느 방향으로 읽는지 스펙에 없다. 코드대로 **뒤 블록부터**(같은 메시지의 `conclude`, `problem` 순서면 `problem`이 이긴다). `problem-dismissed` 마커의 `problemCallId`는 비교하지 않고 마커 존재만으로 비활성이다.
9. R-14: "가장 가까운 앞쪽의 깨끗한 problem"이라고 쓰였지만 코드는 `conclude`가 든 메시지부터 시작해 **그 메시지의 뒤 블록까지** 훑는다. 같은 메시지에 `conclude`와 새 `problem`이 같이 있으면 공개되는 것은 새 문제의 풀이다. 스펙 문장과 코드가 어긋나는 경계 사례라서 코드를 따르고 테스트에 표시했다(`test_R14_quirk_...`). 실제 발생 빈도는 모른다(도구가 순차 실행이라 가능은 하다고 추론).
10. R-10: 검증 순서와 세부가 스펙에 없다. 원본 `parseChatInput`을 따라 **파싱이 활성 확인보다 먼저**(`problemCallId`가 비어 있지 않은 문자열이 아니면 "thinking input requires problemCallId", 글이 공백뿐이어도 "빈 글" 400). 글은 자르지 않고 그대로 저장한다. `text` 입력의 빈 글 400도 같은 파서에 있어 구현했다.
11. R-12: `dismiss-problem` 입력의 형태 검증(누락된 `problemCallId` 등)은 스펙·참조 어디에도 없다. 검증 없이 id 불일치 → "targets no active problem" 400으로 떨어지게 했다.
12. R-12: 합성 쌍의 assistant 메시지에 어떤 자리표시 필드가 있는지 스펙은 "자리표시"라고만 한다. 코드의 값(`api:"faux"`, `provider:"synthetic"`, `model:"synthetic-conclude"`, 0 사용량, `stopReason:"toolUse"`)을 넣었다. 테스트는 이 필드를 확인하지 않는다.
13. R-12/T-09: 일반 `text` 입력이 만드는 사용자 메시지의 모양(`newUserMessage`), 메시지 `id`, `timestamp`는 스펙에 없다. `{role:"user", content:[{type:"text",text}]}`로 정하고 `id`는 만들지 않았다.
14. R-12: 입력 종류별로 쌍이 붙는 곳은 스펙의 "다음 입력(`text`·`continue`·`thinking`·`next`)"만으로 구현할 수 있었다. 단 `thinking`은 건너뛴 문제를 가리킬 수 없어(활성 아님 → 400) 사실상 쌍이 붙을 일이 없다는 것은 내가 테스트로 확인했다. 스펙에는 이 점이 없다. `dismiss-problem`만 턴을 시작하지 않는다는 것은 R-12 문장에서 읽었다.
15. R-01: 세션 `id` 형식, 제목 처리(`titleFromPrompt`는 참조 밖; `trim() || "Untitled session"`으로 추측), 모델 스탬프 구조(`{model:{provider,id}, thinkingLevel}`; 스펙은 "strong 슬롯 모델을 세션 설정으로 찍는다"만)는 코드에서 가져왔다. `strong.model`이 없으면 스탬프 없음.
16. R-02: (a) 어떤 연쇄에도 안 든 명제의 "단독 항목"이 연쇄 id 순서 정렬에서 **노드 id를 자기 id로 쓴다**는 점이 스펙에 없다. (b) 연쇄 줄의 이름은 **고른 시점 스냅샷이 아니라 현재 그래프의 이름**이고 그래프에 없으면 원 id로 대체된다는 점도 없다(스펙은 "스냅샷"을 명제 줄에만 말한다). (c) 전제 정렬 키는 이름이 아니라 id다. T-10·T-11 케이스는 이 셋을 구분하지 못한다. 정렬은 JS와 같은 UTF-16 코드 단위 비교로 했으나 비BMP 문자 케이스는 실행하지 않았다.
17. R-04: `research`가 `pdf`와 따로 없을 수 있다는 점(검색 엔진이 없으면 research만 빠짐)은 스펙에 "작업 맥락이 주어질 때"로만 나온다. chat-handler 주석("research honestly absent when no engine is live")을 보고 `research` 불리언을 따로 두었다(`jobTools` 본문은 읽지 않았으므로 추론). 프롬프트 조각 파일 이름 패턴 `FRAGMENT_RE`는 참조 밖이라 `^\d+-.+\.md$`로 추측했다.
18. R-13: 끊긴 호출 합성(QA R-19)이 연습 스펙에는 없는데 같은 함수가 한다. "그 뒤 **모든** 메시지에 결과가 있으면 답한 것"(바로 다음만이 아님)으로 구현했다.
19. 코드 주석과 스펙/동작이 어긋나는 곳(구현자가 혼란할 수 있음): `createPracticeAgent` 주석은 "전체 레지스트리는 problem + conclude"라고 쓰지만 실제는 R-04 목록이다. `concludeResult` 주석은 "NOT terminate — 같은 답에서 다음 문제를 낸다"고 쓰지만 `CONCLUDE_ACK_TEXT`와 R-24는 반대다. 스펙은 코드 동작을 따라 맞게 썼고 나는 스펙을 따랐다.

스펙 사이·T-ID와 규칙의 모순: 찾지 못했다. 위 4, 9번은 스펙 문장과 코드가 어긋나는 사례다.

## 5. 1.5 범위 밖에서 추가로 연 것

- `src/core/input-events.ts:150-196` (`parseChatInput`): R-10의 "빈 글이면 400"이 이 범위에 있는데 practice C-04는 `:44-57, :75-80, :132-148, :197-244`만 가리킨다(QA C-16의 `:154-170`도 `thinking` 분기 `171-180` 앞에서 끊김). **코드 참조 누락 후보.** 처음에 `$S:src`가 zsh 수식어로 풀려 빈 결과가 나와 SHA를 리터럴로 다시 열었다.
- `git grep -n "requires non-empty text" / "next input" / "targets no active problem"` (SHA 기준, `src`·`app` 전체): 오류 문구 위치를 찾으려고 했다. 출력에서 줄 번호만 봤고 다른 파일(`compaction.ts` 등)은 열지 않았다.
- QA 1.5 범위이지만 practice 1.5에는 없는 것: `src/agent/tool-execute.ts:117-131`(`invalidInputResult`), `src/core/native-messages.ts:45-60`(`INTERRUPTED_TEXT`; 51-55 범위를 앞뒤 몇 줄 포함해 읽음), `src/server/chat-handler.ts:280-303`.
- 읽지 않은 것: 프롬프트 파일(C-11, 구현 대상 아님), QA의 `question-core.ts` 등 질문 쪽 범위.

## 6. 스펙 개선 제안

1. practice 1.5에 `tool-execute.ts:117-131`(`invalidInputResult`)와 `INTERRUPTED_TEXT`(`native-messages.ts:51-55`) 참조를 추가하거나, 1.3에 오류 결과 모양을 한 줄로 쓴다.
2. C-04에 `input-events.ts:150-196`(파서)를 추가하고, R-10에 "파싱이 활성 확인보다 앞", "`problemCallId`는 비어 있지 않은 문자열", "공백뿐인 글도 빈 글", "글은 자르지 않고 저장"을 쓴다.
3. R-05에서 "풀 수 없는 문자열"이 배열 원소를 말하는지 정리하고, 노드 목록이 있을 때 배열이 아닌 `target`은 조용히 제거된다는 동작을 쓴다(아니면 코드 쪽 의도를 확인).
4. R-05/C-07에 이름 비교 쪽도 벗긴다는 것, 이름이 겹치면 첫 노드, id 정확 일치가 먼저라는 것을 명시한다.
5. R-02에 단독 항목이 노드 id를 연쇄 id로 쓴다는 것, 연쇄 줄의 이름은 현재 그래프에서 온다는 것(없으면 id), 전제는 id 순서로 정렬된다는 것을 쓰고, 이것을 가르는 T-ID를 하나 추가한다(고른 시점과 현재 이름이 다른 명제).
6. R-09/R-14에 한 메시지 안의 블록 방향을 쓴다. R-14의 "가장 가까운 앞쪽"은 같은 메시지 뒤 블록도 포함한다는 단서가 필요하다.
7. R-04에 `research`가 `pdf`와 독립적으로 빠질 수 있는 조건과 프롬프트 조각 파일 선택 규칙(`FRAGMENT_RE`)을 쓴다.
8. 1.3의 `problem`/`conclude` 스키마 설명에 "빈 문자열 허용 여부", "추가 필드 허용 여부", "스키마 위반 시 결과는 외부 에이전트 루프 몫"을 쓴다.
9. 빠진 수락 사례: `conclude` 스키마·복구(`rung:"null"`, `retest:"true"`), 같은 메시지의 `conclude`+`problem`(R-14), 공백뿐인 생각 글(R-10), `kind` 정확 일치와 모델 스탬프 유무(R-01), R-13의 끊긴 호출, R-15, R-04의 도구·조각 목록.
10. T-13은 순수 층에서 검증할 수 없다(서버 배선). "서버 통합 테스트 필요"라고 표시하거나 술어를 뽑아 둔 위치를 참조에 넣는다. T-14의 "기록에 남음"도 영속 필터(QA R-07의 미열람 부분)가 있어야 확인된다.
11. R-12의 합성 쌍에 대해 필드 목록(최소한 `isError:false`, `details`, 호출 id)을 쓰고 스탬프는 "의미 없음"이라고 명시하면 구현자가 임의로 채우지 않아도 된다.
12. `depends`가 QA 스펙을 가리키지만 실제 연습 쪽이 빌리는 것은 `invalidInputResult`, 끊긴 호출 합성, 값 찌꺼기 벗기기, 한 채팅 한 턴(QA R-20) 정도다. 본문에 "연습이 QA에서 쓰는 것" 목록을 두면 좋다.
