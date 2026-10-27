---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/learnharness/src/agent/tools/probe.ts
  - repos/learnharness/src/core/contracts/probe.ts
  - repos/learnharness/src/agent/tools/graph.ts
  - repos/learnharness/src/agent/tools/jobs.ts
  - repos/learnharness/src/core/session-clusters.ts
  - repos/learnharness/src/core/coverage.ts
  - repos/learnharness/src/core/pending.ts
  - repos/learnharness/src/agent/tool-execute.ts
  - repos/learnharness/src/server/turn-service.ts
  - repos/learnharness/src/agent/tools.ts
  - repos/learnharness/src/agent/teacher-agent.ts
  - repos/learnharness/src/agent/prompt-segments.ts
  - repos/learnharness/src/core/native-messages.ts
  - repos/learnharness/src/core/contracts/jobs.ts
  - repos/learnharness/src/core/contracts/chat.ts
  - repos/learnharness/src/core/graph.ts
  - repos/learnharness/src/core/settings-resolution.ts
  - repos/learnharness/src/server/chat-handler.ts
  - repos/learnharness/src/agent/subagents/extraction.ts
  - repos/learnharness/src/agent/prompts/prober/10-probe-doctrine.md
  - repos/learnharness/src/agent/system-prompt.md
depends:
  - ./question-answer-contract.md
status: ready
reimplementation: "Python 3 표준 라이브러리, [강제] R-ID의 순수 검증·변환 로직만(권고 규칙과 UI는 제외). 4개 스펙(question-answer-contract, probe-measurement, plan-tree, teaching-cycle)의 1.6 T-ID 전부를 포함해 83개 테스트 통과. 원본과 같은 입력으로 비교하지 않음(원본은 TypeScript이고 실행하지 않았다). 결과: ../../../artifacts/learnharness/reimplementation/core/RESULT.md"
---

# 이해도 측정 (프로버)

> 학습자의 목표를 구체화하고, 목표가 기대는 "가닥"마다 학습자가 확실히 아는 수준(바닥)과 막히는 수준(천장)을 질문 하나씩 이진 탐색으로 찾아, 가닥별 평가서(`probe_done`)로 끝내고 교사에게 넘긴다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 새 세션(기록에 `probe_done` 호출이 없는 학습 세션)의 요청마다 **프로버 에이전트**가 만들어진다. 시스템 프롬프트는 공통 기반 + 프로버 독트린 + 공유 조각이다.
2. (설정으로 열려 있으면) 프로버가 `list_sessions`/`list_propositions`로 이전 세션에서 이미 쌓인 명제 이름을 읽는다. 단단한 가닥은 다시 묻지 않는다.
3. 프로버가 `ask_user_question`으로 목표를 구체화하고, 목표가 기대는 가닥을 추려 낸다.
4. 가닥마다 `probe`(객관식) 또는 `recall`(자유서술)로 한 번에 질문 하나를 낸다. 학습자의 정오·확신도·사고글을 함께 읽어 다음 질문의 난이도 위치를 정하며 바닥과 천장 사이를 좁힌다(질문·답 계약은 `question-answer-contract.md`).
5. 모든 가닥의 바닥·천장이 잡히고 목표가 구체적이면 `probe_done`을 **한 번** 호출한다. 입력이 가닥별 평가서이고, 도구는 **턴이 시작될 때 저장돼 있던 기록**(이번 턴의 메시지는 아직 없음)에서 대기 중인 질문이 없는지·이미 끝나지 않았는지 확인한다.
6. 성공하면 고정 안내문이 결과로 돌아가고, 교사의 첫 턴을 일으키는 "핸드오프" 깨움이 큐에 들어간다. 프로버는 짧은 맺음말 뒤 턴을 끝낸다.
7. 이후 모든 요청은 기록의 `probe_done` 호출을 이음새로 **교사**를 만든다(`plan-tree.md`로 이어짐).

### 1.2 범위·통합 지점 [필수]
- 제공: 프로버의 도구 구성과 프롬프트가 요구하는 측정 절차, `probe_done`의 입력·거절 조건·핸드오프, 이전 지도 읽기 도구 두 개, 프로브 단계 판정(기록의 `probe_done`).
- 제외:
  - 질문 도구의 입력·답 계약 → `question-answer-contract.md`.
  - 계획 작성과 교사 → `plan-tree.md`, `teaching-cycle.md`.
  - 깨움(wake) 파이프라인 내부(큐, 발화 시점, 유예 시간)와 job 프로토콜(지도 행 10, `미작성`). 여기서는 "`probe_done`이 steer 한 개를 전달하고, 프로버 턴이 끝난 뒤 새 요청이 시작된다"는 경계만 둔다.
  - 지식 그래프 저장·원장(지도 행 15, `미작성`), 그래프 추출(행 13, `미작성`). 이전 지도 읽기는 읽기 전용 목록 형식만 쓴다.
  - 컨텍스트 컴팩션(행 9, `미작성`). 프로브 단계는 컴팩션 종류 `"probe"`로 취급된다는 사실만 있다.
  - 사용자 오버라이드 파일 관리와 설정 화면(행 7, `미작성`). 프롬프트 조립 규칙(어떤 조각을 어떤 순서로 어떻게 잇는가)은 R-02에 둔다.
  - `research`·`pdf` 작업 도구의 내부(행 11, `미작성`).
- 외부 의존: 세션 저장소(`getChat`), 그래프 저장소(읽기만, 이전 지도 도구. 노드의 `id`·`name`·`provenance[].chatId`, 채팅 목록의 `id`·`title`·`createdAt`·`updatedAt`, 가져온 노트 출처의 `id`·`filePath`·`importedAt`을 입력으로 받고 `getGraph`의 노드 병합은 행 15의 일), wake 파이프라인의 `deliver(steer)`, 질문 도구와 답 계약(`question-answer-contract.md`: 대기 질문 판정 R-09, 도구 결과 모양 R-25, 기록 저장 시점 R-27, 스키마 검증 경계 R-24).
- 소유 상태·부작용: `probe_done` 호출(= 가닥별 평가서)이 세션 기록에 남는다. 평가서는 **이 호출의 인자에만** 있고 다른 곳에 복사하지 않는다. 핸드오프 steer 메시지가 기록에 붙는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**`probe_done` 입력** (스키마 위반은 에이전트 루프가 실행 전에 거절)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `assessment.strands` | list(1개 이상) | 수업이 기대는 의존 가닥 목록 |
| `assessment.strands[].strand` | string | 가닥 이름. 계획 노드를 걸 수 있는 이름 |
| `assessment.strands[].assessment` | string(자유) | 그 가닥에서 학습자의 경계: 바닥, 천장, 발견한 오개념, 거기서부터 쌓을 것 |
| `assessment.summary` | string? | 학습자의 목표와 가르침이 들어갈 지점의 선택적 종합 |

**`probe_done` 결과**: 성공이면 텍스트가 고정 문장 `PROBE_DONE_ACK_TEXT`("Assessment recorded — it is shown to the learner now and the teacher plans from it. Say your closing sentence and end your turn; the teaching phase takes over from here."), `details:{ok:true}`. 평가서를 결과에 되풀이하지 않는다(컨텍스트 절약). 거절이면 `{ok:false, error}` 객체를 반환하고 도구 결과 메시지로는 `content`가 그 객체의 JSON 문자열(예: `{"ok":false,"error":"The probe is already concluded — probe_done fires exactly once."}`), `details`가 같은 객체이며 `isError`는 붙지 않는다(`question-answer-contract.md` R-25).

**핸드오프 steer**: 기록에 들어가는 `role:"custom"`, `customType:"probe-handoff"`, `id = "steer_probe_<chatId>"`(채팅마다 결정적), `display:true`, `timestamp`(밀리초), `details:{chatId}`, 모델이 읽는 `content = HANDOFF_TEXT`(계획을 세우라고 교사에게 시키는 고정 문장, 코드 원문은 C-03). 화면에는 조용한 시스템 줄로 보인다.

**이전 지도 읽기 도구** (프로버 전용, 읽기 전용, 이름·종류·개수·날짜·id만. 명제 본문과 세션 내용은 주지 않는다)

| 도구 | 입력 | 출력 |
|---|---|---|
| `list_sessions` | 없음 | 그래프에 세션이 하나도 없으면 "The knowledge graph is empty — no session has contributed propositions yet." 아니면 "N session(s) in the knowledge graph, most recent first:\n" + 줄마다 `i. <이름> (<kind>, <n> proposition(s), born <createdAt 또는 "unknown date">[, last active <updatedAt>]) — id: <id>`. `i`는 1부터. `n`이 1이면 "1 proposition", 아니면 "n propositions"(괄호 `(s)` 문자 그대로가 아니다). 날짜는 저장된 ISO 문자열 그대로이고 `updatedAt`이 없으면 `, last active …` 부분을 뺀다. 정렬은 R-22 |
| `list_propositions` | `session`(비지 않은 문자열, `list_sessions`의 id) | 그 세션에서 태어난 명제가 없으면 `No propositions born in session "<id>". Call list_sessions for the current ids.` 있으면 "n proposition(s) covered in this session:\n" + `- <이름>` 줄들(여기서는 `(s)`가 문자 그대로). 줄 순서는 R-22 |

### 1.4 행동 규칙과 남은 질문 [필수]
범례: **[강제]** 코드가 지킴, **[권고]** 프롬프트가 모델에게 요청할 뿐 코드는 막지 않음.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] 학습 세션(연습 아님)의 요청 | 합쳐진 기록(= 저장된 기록 + 이번 입력이 붙이는 메시지)에 `probe_done` 도구 호출이 **어떤 상태로든** 하나라도 있으면 교사, 없으면 프로버를 만든다. 호출만으로 충분하다(결과 상태 무관, 컴팩션 이전 메시지 포함 전체를 훑는다). 이 판정은 요청마다 기록에서 다시 계산한다 | 코드 확인 |
| R-02 | [강제] 프로버 시스템 프롬프트 | 조각 순서: 공통 기반(`system-prompt.md`) → `prober/` 폴더에서 파일명이 `^\d+-[\w.-]+\.md$`인 파일(번호 접두가 없는 파일은 불러오지 않음)을 **문자열 순서**로 정렬한 것(숫자 크기가 아니다: `100-…`은 `20-…`보다 앞선다) → `shared/`에서 같은 규칙의 파일을 같은 방식으로 정렬한 것. 각 조각의 텍스트는 사용자 오버라이드 스위치가 켜져 있고(`agent.prompts[<조각 경로>] === true`) 그 오버라이드 파일이 있으면 오버라이드 텍스트, 아니면 원본(읽을 수 없으면 빈 문자열). 조립: 각 텍스트를 `trim()`하고 빈 문자열을 버린 뒤 `"\n\n---\n\n"`로 잇는다(앞뒤에는 구분자 없음) | 코드 확인 |
| R-03 | [강제] 프로버 도구 | 질문 도구는 `probe`(또는 자유서술이면 `recall`) + `ask_user_question`, 학습자 파일 `read`·`ls`·`find`·`grep`, `research`, `pdf`, `probe_done`, 설정이 열려 있으면 `list_sessions`·`list_propositions`. 계획 도구·`nodeId`·`type`은 없다. `demo`·`visual`은 교사 전용 | 코드 확인 |
| R-04 | [강제] `probe_done`은 끌 수 없다 | 설정 쓰기 API가 받는 `agent.tools` 키(`research`·`demo`·`visual`·`pdf`·`explain`)에 `probe_done`이 없고(그 밖의 키는 400), 손으로 `probe_done:false`를 써 둬도 프로버 팩토리가 필터 뒤에 `probe_done`을 다시 넣어 무효로 만든다. 이유: 이 도구가 단계를 끝내는 수단이라 없으면 프로버가 영영 끝낼 수 없다. (프로버의 다른 도구는 필터가 `false`를 이름 불문 빼므로 설정 파일 편집으로는 빠질 수 있다 — `question-answer-contract.md` R-01) | 코드 확인 |
| R-05 | [강제] `probe_done` 호출 시 대기 중인 질문이 있음 | 판정은 `question-answer-contract.md` R-09(`danglingQuestionOf`)를 **턴이 시작될 때 저장된 기록**에 적용한 것이다(그 기록 = 이전 턴들 + 이번 입력의 쓰기 선행 추가분, 같은 문서 R-27). 이번 턴의 assistant 메시지(같은 배치의 `probe` 호출 포함)는 기록에 아직 없으므로 보이지 않는다. 그래서 이 거절은 턴이 시작될 때 기록의 최신 assistant 메시지에 결과 없는 질문 호출이 남아 있을 때만 걸린다(예: 학습자가 질문에 답하지 않고 일반 `text` 입력을 보낸 경우 — 서버는 `text` 입력을 대기 질문과 상관없이 받는다). 결과: `{ok:false, error:"A question is still open — resolve it (or let him answer) before concluding the probe. probe_done only fires with no question outstanding."}`. 핸드오프 없음. 모델이 질문을 해소한 뒤 다시 호출 | 코드 확인 |
| R-06 | [강제] 기록에 이미 `probe_done` 호출이 있음 | `{ok:false, error:"The probe is already concluded — probe_done fires exactly once."}`. R-05가 먼저 평가된다(대기 질문 검사 → 이미 끝남 검사 순). 읽는 것은 R-05와 같은 저장된 기록이라 **이번 턴 안에서 이미 낸 `probe_done` 호출은 보이지 않는다**(R-23). 기록에 `probe_done`이 있으면 다음 요청은 교사를 만들어 이 도구가 없으므로(R-01) 이 거절은 방어선에 가깝다 | 코드 확인(조건·문구). 방어선이라는 서술은 추론 |
| R-07 | [강제] 세션 기록이 없음 | `{ok:false, error:"Chat not found: <chatId>"}` | 코드 확인 |
| R-08 | [강제] 성공한 `probe_done` | 평가서는 호출 인자에만 기록되고 결과는 1.3의 고정 안내문(에코 없음). 핸드오프 steer 한 개(`buildProbeHandoffSteer(chatId)`)를 wake 파이프라인의 `deliver`에 전달한다. 멱등: `steerDelivered(기록, steerId)`는 기록의 어떤 메시지든 `id`가 같으면 참이고, wake가 steer를 턴에 싣는 지점(`handleChatInput`)이 `steers.filter(s => !steerDelivered(record.messages, s.id))`로 이미 기록에 있는 steer를 걸러 중복으로 붙지 않는다. `deliver`(큐) 쪽이 따로 중복을 거르는지는 wake 파이프라인 본문을 읽지 않아 알 수 없다 | 코드 확인(걸러지는 지점). 큐 쪽은 미열람 |
| R-09 | [강제] 핸드오프 전달이 예외 | 오류를 로그로만 남기고 평가서는 유효하며 결과는 성공이다. 깨움은 최적화일 뿐 관문이 아니다: 학습자의 다음 메시지가 R-01 이음새로 교사를 구성한다 | 코드 확인 |
| R-10 | [강제] 핸드오프의 소비 | 핸드오프는 프로버 턴이 끝난 뒤 발화되어 교사의 첫 턴(계획 작성)을 일으킨다. 학습자에게는 평가에서 계획으로 한 흐름이다 | 추론: 발화 시점은 주석(`probe.ts:36-44`, `jobs.ts:423-431`)과 `deliver` 주입 지점만 읽음, wake 파이프라인 본문 미열람 |
| R-11 | [강제] 그래프 읽기 도구 등록 | 두 도구는 조합 루트가 `graphStore`를 넘길 때만 등록되고, 넘기는 조건은 `graph.enabled && (agent.graphTools.enabled ?? true)`(기본 켜짐)다. 읽기 쪽 설정 정리는 `graphTools.enabled`가 불리언일 때만 그 값을 쓰고 모양이 틀리면 키를 버려 기본(켜짐)으로 돌아간다 | 코드 확인 |
| R-12 | [강제] `research`·`pdf` | 프로버에도 있고 검색 공급자 키 없이도 등록된다. `jobTools`가 `research`·`demo`·`visual`·`pdf` 네 개를 **조건 없이** 만들고, 프로버 팩토리는 `...(jobs.research ? {research} : {})`와 `pdf: jobs.pdf!`로 그중 둘을 고른다. `jobs.research`는 항상 정의돼 있으므로 이 조건문은 항상 참이다(분기가 죽어 있음). 컨텍스트의 `searchAvailable`은 어디서도 읽지 않는다. 사용자 토글(`agent.tools.research:false`·`pdf:false`)로만 빠진다 | 코드 확인(`tools/jobs.ts:131-166`, `tools.ts:335-336`). `chat-handler.ts:408-411`·`:429-431`의 "엔진이 없으면 research가 빠진다"는 주석은 이 코드와 맞지 않는다(2.1) |
| R-13 | [강제] 평가서의 영속 위치 | 이해도 평가서와 학습자의 답·사고글은 세션 기록에만 있다. 그래프 추출기의 입력(`proseView`)은 기록의 **role이 `assistant`인 모든 메시지의 `text` 블록**(공백뿐인 블록 제외, 사고 블록·도구 호출은 제외)이다. 줄은 블록마다 `TEACHER [<message.id>] <text.trim()>`이고 줄들을 `"\n\n"`로 잇고, 제목이 비지 않으면 앞에 `# <제목>\n\n`을 붙인다. 라벨은 항상 `TEACHER`이므로 프로브 단계의 프로버가 쓴 텍스트도 포함된다. 학습자 메시지·사고글·도구 호출(평가서가 든 `probe_done` 인자 포함)·도구 결과는 들어가지 않으므로 평가서는 그래프로 가지 않는다 | 코드 확인 |
| R-14 | [권고] 측정의 순서와 단위 | 일은 두 가지 측정뿐이다: 목표(`ask_user_question`)와 현재 이해(`probe`/`recall`). 한 번에 질문 하나: 질문→답→답을 보고 다음 질문. 이전 세션 지도를 먼저 읽고(도구가 없으면 지도가 꺼진 것이니 그냥 탐색) 단단한 가닥은 다시 묻지 않는다. 전체 수업이 이 지도를 바탕으로 계획되므로 정밀해야 한다 | 코드 확인(프롬프트 텍스트) |
| R-15 | [권고] 목표 구체화 | "LLM을 이해하고 싶다" 같은 모호한 목표는 질문으로 구체화한다. 질문만 하고 설명하지 않는다. 학습자가 지형을 모르면 "목표는 오리엔테이션부터 시작한다"고 기록할 뿐 지도를 직접 그리지 않는다 | 코드 확인(프롬프트 텍스트) |
| R-16 | [권고] 가닥 | 목표에서 수업이 기대는 의존을 가닥으로 삼는다: 가르친다면 어디서 시작하고 무엇 위에 쌓아야 하는가. 가닥의 경계는 관련성뿐이다 | 코드 확인(프롬프트 텍스트) |
| R-17 | [권고] 가닥별 이진 탐색 | 경계는 "확실히 맞히는 것(바닥)"과 "틀리거나 모르는 것(천장)"으로 잡는다. 질문은 답의 정오·확신도·사고글을 함께 보고 고른다. ① 위쪽에서 시작(성인이 고급 주제를 찾으면 기초는 보통 안다) ② 이미 보인 수준 아래로 열지 않고 한 가닥이 높게 뚫리면 이웃 가닥도 높게 시작 ③ 맞고 확신 → 크게 올림 ④ 맞았으나 주저(낮은 확신, 얇은 사고글) → 취약, 조금 올리고 취약함의 성질을 파악 ⑤ 틀림 → 천장이 내려가고 정확한 위치까지 다시 좁힘 ⑥ 오답 하나는 좌표 하나일 뿐(실수·공백·오개념이 똑같아 보임)이라 주변을 더 묻고, 오개념은 범위를 파고든 뒤 넘어감 ⑦ 안 깨지는 가닥은 끝난 게 아니라 깨질 때까지 올림 | 코드 확인(프롬프트 텍스트) |
| R-18 | [권고] 질문의 가치 | 모든 질문은 어딘가의 경계를 움직여야 한다. 군더더기 질문, 직전 답이 이미 보여 준 것을 다시 묻기, 이미 경계가 잡힌 구간으로 내려가기는 하지 않는다. 아낀 질문이 더 구체적이고 미묘한 질문을 할 여유가 된다 | 코드 확인(프롬프트 텍스트) |
| R-19 | [권고] 종료 | 모든 가닥이 경계로 잡히고 목표가 구체적이면 `probe_done`을 한 번 호출한다. 가닥마다 이름·바닥·천장·오개념·거기서부터 쌓을 것을 증거로 쓴다. 호출 뒤 짧은 맺음말 한 문장으로 턴을 끝낸다 | 코드 확인(프롬프트 텍스트) |
| R-20 | [권고] 근거 자료 | 학습자가 로컬 파일을 말하면 `read`로 직접 보고 PDF는 `pdf` 도구(인용 달린 brief)로 읽는다. `research`는 아껴 쓴다: 프로빙은 측정이지 탐색이 아니다 | 코드 확인(프롬프트 텍스트) |
| R-21 | [권고] 어조 | 칭찬·열광·동의 편향·순화 없이 건조하게. 틀린 답은 있는 그대로 말한다. 정확하지 않은 것은 확실히 말하지 않는다 | 코드 확인(`shared/10-voice.md`, `15-accuracy.md` 머리) |
| R-22 | [강제] 그래프 읽기 도구의 정렬 | `list_sessions`: 세션 항목은 채팅(레코드가 남아 있으면 `kind:"chat"`, 이름=제목, 날짜=`createdAt`·`updatedAt`)이거나 노트 출처(`kind:"file"`, 이름=`filePath`가 있으면 그것 아니면 id, 날짜=`importedAt` 둘 다)이고, 레코드가 둘 다 없으면 이름=id, 날짜 `null`. 개수는 노드의 첫 출처 채팅 id(`provenance[0].chatId`, 출처가 없으면 세션 없음)로 묶은 명제 수다. 정렬 키: `updatedAt` 내림(`null`은 빈 문자열로 보아 맨 뒤) → `createdAt` 내림 → `id` 오름(코드 단위 비교). 날짜 비교는 `localeCompare`지만 같은 형식의 ISO 문자열이면 문자열 내림차순과 같다. `list_propositions`: 첫 출처 채팅 id가 `session`인 노드를 노드 id 오름(코드 단위 비교)으로 | 코드 확인(정렬 키·집계). ISO 문자열에서 `localeCompare`가 문자열 순서와 같다는 점은 추론 |
| R-23 | [강제] 같은 턴 안의 `probe_done` 중복 | 기록에는 턴 끝에야 메시지가 붙으므로(`question-answer-contract.md` R-27) 한 턴 안의 `probe_done` 호출은 서로를 보지 못하고 `probe_done` 도구는 순차 실행으로 지정돼 있지도 않다. 같은 턴에서 두 번 호출하면 둘 다 R-05·R-06 검사를 통과해 성공하고 둘 다 같은 id의 steer를 전달한다(기록에서는 이후 R-01 이음새가 한 번의 전환으로 본다) | 코드 확인(저장 시점·무순차). 중복 호출 결과는 코드 읽기에서 도출 |

- 불변식: **요청을 가로질러** 학습 세션마다 `probe_done` 호출은 많아야 한 번 성공한다(R-05·R-06, 이후 요청은 교사를 만든다). 한 턴 안의 중복 호출은 막히지 않는다(R-23). 전제: 평가서는 모델이 쓰므로 정확성은 모델에 달려 있다.
- 미결정: 없음
- 확인 한계: 코드를 실행하지 않았고 원본 테스트는 `tests/question-tools.test.ts:266-287`(프로버 토글)만 읽었다(실행 아님, 코드 읽기와 일치). 프롬프트 규칙(R-14~R-21)을 모델이 따르는 정도, 질문 수·종료 시점은 미확인. 깨움 발화 시점(R-10)은 wake 파이프라인 본문을 읽지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스는 AGPL-3.0(overview 1절)이다. 프롬프트는 본문 인용 없이 파일:줄 범위로만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/agent/tools/probe.ts:21-23` `probeConcluded`, `:48-96` `probeDoneTool` | 거절 조건·성공 결과·핸드오프 전달·예외 처리 | R-05~R-09 |
| C-02 | `src/core/contracts/probe.ts:47-72` `probeDoneInputSchema`; `:93-94` `PROBE_DONE_ACK_TEXT` | 입력 스키마와 고정 안내문 | 1.3, R-08 |
| C-03 | `src/core/native-messages.ts:157-167` `newHandoffMessage`; `:621-630` `hasProbeDone`; `:602-619` `danglingQuestionOf`; `:485-493` `resultIdsFrom`; `src/core/contracts/jobs.ts:432-441` `buildProbeHandoffSteer`, `steerDelivered`; `src/core/contracts/chat.ts:187-192` `HANDOFF_TEXT`; `src/server/chat-handler.ts:267-278` | 핸드오프 메시지 모양·멱등·단계 판정 | R-01, R-05, R-08 |
| C-04 | `src/server/chat-handler.ts:343-352`, `:391-452` | 요청마다 프로버/교사/연습 에이전트 선택 | R-01 |
| C-05 | `src/agent/tools.ts:287-348` `createProberTools` | 프로버 도구 구성과 `probe_done` 상시 | R-03, R-04, R-12 |
| C-06 | `src/agent/tools/graph.ts:32-78` `proberGraphTools`; `src/core/graph.ts:603-685` `GraphSessionEntry`, `graphSessionIndex`, `graphSessionPropositions`; `src/core/settings-resolution.ts:249-254` `graphToolsEnabled` | 이전 지도 읽기 도구와 게이트 | R-11, R-22, 1.3 |
| C-07 | `src/agent/prompt-segments.ts:62-125` `listSourceSegments`, `effectivePromptSegments`; `src/agent/teacher-agent.ts:74-81` `composeInstructions`; `src/core/prompt-segments.ts:17` `FRAGMENT_RE` | 프롬프트 조립 순서·파일 규칙·오버라이드 선택·구분자 | R-02 |
| C-08 | `src/agent/prompts/prober/10-probe-doctrine.md:3-39` | 프로버 독트린(절차·이진 탐색·종료) | R-14~R-20 |
| C-09 | `src/agent/system-prompt.md:1-11`; `src/agent/prompts/shared/10-voice.md:1-12`; `shared/15-accuracy.md:1-3` | 공통 기반·어조·정확성(권고) | R-21 |
| C-10 | `src/agent/subagents/extraction.ts:126-139` `proseView`; `src/core/coverage.ts:29-55` `textOf`, `messageViewLines` | 그래프 추출이 보는 것과 줄 서식 | R-13 |
| C-11 | `src/core/session-clusters.ts:48-76` `birthSessionOf`, `birthSessionPartition` | 명제의 출생 세션과 세션별 개수 | R-22 |
| C-12 | `src/agent/tools/jobs.ts:18-30`, `:131-166` `jobTools` | `research`·`pdf` 등록의 근거(조건 없이 네 도구를 만듦) | R-12 |
| C-13 | `src/core/pending.ts:60-106` `TOGGLEABLE_TOOLS`, `WRITABLE_TOOL_KEYS`, `filterEnabledTools`; `src/agent/tools.ts:416-432` `quizMechanics`, `withoutMechanics`; `src/server/settings-body.ts:156-172` | 토글 쓰기 검증·필터와 `probe_done` 예외 | R-04 |
| C-14 | `src/server/turn-service.ts:50-84` `persistTurn`; `src/server/chat-handler.ts:305-324`, `:499-502` | 턴 메시지가 기록에 붙는 시점(`probe_done`이 읽는 기록) | R-05, R-06, R-23 |
| C-15 | `src/agent/tool-execute.ts:155-212` `toToolResult`, `serverExecute` | `{ok,error}`·`{text,details}` 반환의 결과 메시지 변환 | 1.3, R-05~R-08 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 코드를 실행하거나 원본 테스트 사례를 옮기지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05 | 턴이 시작될 때 저장된 기록의 마지막 assistant 메시지에 결과 없는 `probe` 호출이 있고 그 뒤에 학습자 `text` 메시지. 프로버가 `probe_done` 호출 | `{ok:false,error:"A question is still open …"}`. 전달된 steer 없음 |
| T-02 | R-06 | 기록에 이미 `probe_done` 호출이 있고 다시 호출 | `{ok:false,error:"The probe is already concluded — probe_done fires exactly once."}` |
| T-03 | R-08 | 대기 질문 없고 `probe_done` 없음. 가닥 2개의 평가서로 호출 | 결과 텍스트가 고정 안내문, `details.ok=true`, `deliver`가 `id="steer_probe_<chatId>"`인 steer로 정확히 한 번 호출됨 |
| T-04 | R-09 | T-03 상황에서 `deliver`가 예외 | 결과는 여전히 성공. 예외는 로그. 평가서는 호출 인자에 남음 |
| T-05 | 1.3 | `strands:[]` | 스키마가 거절(`minItems:1`), `execute` 미호출 |
| T-06 | 1.3 | `assessment`가 문자열 | 스키마가 거절 |
| T-07 | R-01 | 기록에 `probe_done` 호출이 있음(결과 없음/오류 포함) / 없음 | 교사 / 프로버 구성 |
| T-08 | R-04 | 설정에서 `agent.tools.probe_done=false` | 프로버 레지스트리에 `probe_done`이 남아 있음 |
| T-09 | R-11 | 설정 그래프 꺼짐 / 켜짐 | 프로버 도구에 `list_*` 없음 / 있음 |
| T-10 | 1.3 | 그래프가 비었을 때 `list_sessions` | "The knowledge graph is empty — no session has contributed propositions yet." |
| T-11 | R-08 | 기록에 같은 `steer_probe_<chatId>`가 이미 있고 wake가 그 steer를 입력으로 싣는다 | 턴 구성 단계에서 걸러져 기록에 같은 id의 메시지가 둘이 되지 않음 |
| T-12 | R-22 | 그래프에 세션 둘: 채팅 `chat_a`(제목 "Calc", `createdAt` `2026-10-01T09:00:00.000Z`, `updatedAt` `2026-10-02T10:00:00.000Z`, 명제 3개), 노트 출처 `src_1`(`filePath` "notes/x.md", `importedAt` `2026-10-03T00:00:00.000Z`, 명제 1개). `list_sessions` | `2 session(s) in the knowledge graph, most recent first:\n1. notes/x.md (file, 1 proposition, born 2026-10-03T00:00:00.000Z, last active 2026-10-03T00:00:00.000Z) — id: src_1\n2. Calc (chat, 3 propositions, born 2026-10-01T09:00:00.000Z, last active 2026-10-02T10:00:00.000Z) — id: chat_a` |
| T-13 | R-22 | `chat_a`에서 태어난 명제 둘: id `n_b` 이름 "Chain rule", id `n_a` 이름 "Limit". `list_propositions(session:"chat_a")` | `2 proposition(s) covered in this session:\n- Limit\n- Chain rule`(노드 id 오름). 없는 세션 `x`이면 `No propositions born in session "x". Call list_sessions for the current ids.` |
| T-14 | R-02 | 공통 기반 텍스트 "B"; `prober/`에 `10-a.md`("  A\n"), `100-b.md`("C"), `20-c.md`("D"), `readme.md`; `shared/`에 `05-s.md`("") | `B\n\n---\n\nA\n\n---\n\nC\n\n---\n\nD`(`readme.md`는 불러오지 않고, `10-a.md` < `100-b.md` < `20-c.md` 문자열 순서, 빈 조각은 버림) |
| T-15 | R-23, R-05 | 대기 질문 없는 기록. 한 턴에서 `probe_done`을 두 번 호출 | 둘 다 성공(`details.ok=true`), `deliver`가 두 번 호출됨. 같은 턴의 `probe`+`probe_done` 배치도 `probe_done`이 성공(이번 턴의 `probe` 호출은 기록에 아직 없음) |
| T-16 | R-06, 1.3 | `probe_done` 거절 / 성공을 도구 결과 메시지로 만들 때 | 거절: `content[0].text`=`{"ok":false,"error":"The probe is already concluded — probe_done fires exactly once."}`, `details`=그 객체, `isError` 없음. 성공: `content[0].text`=고정 안내문, `details={ok:true}` |
| T-17 | R-13 | 제목 "T", 기록 [user "q"(id m0), assistant(id m1) 블록 [text " A ", thinking "…", toolCall `probe`], assistant(id m2) 블록 [text "B"]] | `# T\n\nTEACHER [m1] A\n\nTEACHER [m2] B`. m2가 프로브 단계의 프로버 메시지여도 같음 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@b277ee3) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03, C-04 | `chat-handler.ts:349` `teaching = hasProbeDone(merged)`, `:398-452` 분기 확인 |
| R-02 | C-07 | 소스 전문 읽음. 합쳐진 문자열 구분자는 `teacher-agent.ts:75-81`의 `\n\n---\n\n`(`trim`·빈 조각 제거 포함). 조각 정렬은 `readdirSync(...).sort()`(기본 정렬, `prompt-segments.ts:79`·`:91`), 오버라이드 선택은 `:121` |
| R-03, R-04, R-12 | C-05, C-12, C-13 | 소스 전문 읽음. R-04: `pending.ts:60-106`·`settings-body.ts:156-172`·`tools.ts:287-348`. 테스트 `tests/question-tools.test.ts:266-287`이 `probe_done:false`·`quiz:false` 사례를 확인(읽기만) |
| R-05~R-09, R-23 | C-01, C-03, C-14, C-15 | 소스 전문 읽음. `jobs.ts:432-441`의 멱등은 `steerDelivered(messages, steerId)`가 `m.id === steerId` 비교, 적용은 `chat-handler.ts:267-272`의 `steers.filter(...)`. 기록 저장 시점: `turn-service.ts:50-84`가 `onFinish`(`chat-handler.ts:499-502`)에서만 호출되고 턴 중간에 턴 메시지를 쓰는 `saveMessages`는 없다 |
| R-10 | `probe.ts:36-44`, `jobs.ts:423-431` | 주석 근거. wake 파이프라인(`src/server/jobs.ts`) 미열람 |
| R-11 | C-06 | 소스 전문 읽음. 조합 루트의 조건은 `chat-handler.ts:449`(`...(graphToolsEnabled(effective) ? { graphStore } : {})`) |
| R-13 | C-10 | `extraction.ts:126-139`, `coverage.ts:29-55` 소스 읽음. 주석은 "교사 텍스트만"이라 하지만 코드는 role이 assistant인 모든 메시지를 `TEACHER`로 라벨한다(2.1 아래 문서·코드 차이) |
| R-22 | C-06, C-11 | `graph.ts:630-685`, `session-clusters.ts:48-76` 소스 읽음 |
| R-14~R-20 | C-08 | 프롬프트 전문 읽음 |
| R-21 | C-09 | `10-voice.md` 전문, `15-accuracy.md` 첫 줄들 |
| 문서·코드 차이 | `prompts/prober/10-probe-doctrine.md:3`, `:19` | 독트린 본문은 질문 도구를 "`quiz` 또는 `explain`"이라고 부르지만 프로버에 실제로 등록된 이름은 `probe`/`recall`이다(2026-10-09 이름 바꿈, `tools.ts:197-261`). 구현을 사실로 썼다. 프롬프트 갱신 누락으로 보이나 모델이 이름을 어떻게 해석하는지는 미확인 |
| 문서·코드 차이 | `chat-handler.ts:408-411`, `:429-431`, `tools/jobs.ts:123-130` | 핸들러 주석은 "라이브 엔진이 없으면 교사(와 연습) 레지스트리에 research가 없다"고 하지만 `jobTools`는 조건 없이 `research`를 만들고(`jobs.ts:131-141`), 주석(`:128`, `:26-29`)도 "키 없이도 가능, `searchAvailable`은 의존하지 않음"이라 쓴다. `tools.ts:335`의 `jobs.research ?`도 항상 참이다. 구현을 사실로 썼다 |
| 문서·코드 차이 | `core/contracts/probe.ts:2-15` 주석("durable in the transcript by the tool result itself") | 평가서는 도구 **인자**에 있고 결과는 고정 안내문이다(`probe.ts:87-94`). 구현을 사실로 썼다 |
| 문서·코드 차이 | `extraction.ts:126-135` 주석, `coverage.ts:39-47` 주석("TEACHER PROSE ONLY") | 주석은 교사 텍스트만이라 하지만 `messageViewLines`는 `role === "assistant"`만 보고 에이전트 종류를 구별하지 않는다. 프로브 단계의 프로버 텍스트도 `TEACHER [id]`로 들어간다. 구현을 사실로 썼다(R-13) |
| T-01~T-17 | 구현에서 도출 | 실행·원본 테스트 사례 미반영. T-12~T-17은 재구현 검증(RESULT.md)의 지적을 코드로 확인해 추가(예시 값은 코드 읽기에서 옮겨 적은 것) |

### 2.2 코드 읽는 순서 [선택]
`chat-handler.ts:343-452`(에이전트 선택) → `tools.ts:287-348`(프로버 도구) → `tools/probe.ts`(종료 도구) → `contracts/probe.ts`(스키마) → `prompts/prober/10-probe-doctrine.md`.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 코드를 복사한 범위 없음.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점(걸리는 곳) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-03, R-17, R-18 | 프로버 독트린은 `probe`/`recall` 도구와 확신도 슬라이더, 사고글 필드(UI)를 전제한다 | 터미널 대화에는 질문 카드·슬라이더가 없다 | 객관식을 글로 내고 확신도를 "0~100 중 하나"로 묻는 방식이 필요하다(`question-answer-contract.md` 적용 메모와 같은 이유). 한 번에 질문 하나는 터미널에서도 그대로 유지 가능 |
| R-05~R-10 | `probe_done`, 핸드오프 깨움, 단계 판정은 "한 세션 안에서 두 에이전트가 바뀌는" 앱 구조 때문에 있다 | 터미널 스킬은 한 에이전트가 두 단계를 이어 할 수 있다 | 평가서를 호출 인자로 남기는 대신 학습 기록 파일에 쓰는 방식으로 대체할 수 있다. 단, 원본의 "평가서는 기록에만 있고 그래프에 안 간다"는 성질은 새로 정해야 한다 |
| R-11 | 이전 지도 읽기가 이름만 주고 본문을 안 준다 | 원본은 조직(지도의 구성)만 프로버의 일이라고 정했다 | 학습 기록을 스스로 관리하면 명제 본문도 읽게 할지는 별도 결정 |
