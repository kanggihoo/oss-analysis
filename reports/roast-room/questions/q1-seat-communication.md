---
sha: "e40f40652d5690c4d9f928c4794c673a99f2cd0e"
created: 2026-10-26
updated: 2026-10-26
sources:
  - .claude/skills/roast-room/SKILL.md
  - .claude/skills/roast-room/references/round-prompts.md
  - .claude/agents/council-musk.md
  - .claude/skills/roast-room/references/live-room.md
  - app/lib/council.mjs
  - app/lib/anthropic.mjs
  - app/lib/seats.mjs
  - app/lib/watch.mjs
  - app/server.mjs
---

# [Q] 좌석(AI)끼리 어떻게 대화하나, mesh 통신이 있나

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 주장마다 표기. 실행은 하지 않았다(`실행 확인` 없음).

## 1. 질문 및 결론

- **질문**: 한 주제를 여러 AI가 역할을 맡아 토론한다고 아는데, 서로 어떻게 대화하고, mesh처럼 서로에게 직접 말하는 통신이 어떻게 가능한가.
- **핵심 결론**: mesh는 없다. 좌석(서브에이전트)끼리 메시지를 주고받는 채널이 코드에 없고, 같은 상대가 말한 내용을 "의장이 파일에 모아 다음 라운드 프롬프트에 붙여 주는" 방식이다. 토폴로지는 의장을 중심으로 한 hub-and-spoke이고, 대화는 라운드 단위의 동기 배치다. `코드 확인` (`grep -rniE "mesh|SendMessage|direct message"`가 `brains/`·`sessions/`·vendor 밖에서 0건)

## 2. 동작 설명

용어: **의장(Chair)** = `/roast-room`을 실행한 메인 Claude 세션. **좌석(seat)** = `council-<key>` 서브에이전트 하나. **카드(card)** = 좌석이 한 라운드에 낸 정해진 양식의 답.

### 2.1 라운드 한 번의 흐름 (Claude Code 스킬 경로)

1. 의장이 좌석 전원을 **한 메시지에서 병렬·포그라운드**로 띄운다(`subagent_type: council-<seat>`). `코드 확인`
2. 좌석은 서로를 모르는 채 각자 `brief.md`(와 이전 라운드 파일)를 **직접 읽고** 카드를 반환한다. 좌석 에이전트의 도구는 `Read, Grep, Glob`뿐이라 다른 에이전트 호출·파일 쓰기가 불가능하다. `코드 확인`
3. 의장이 카드를 **그대로** `round-N.md`에 `## <Seat>` 제목으로 저장한다. 이 파일이 공유 게시판이다. `코드 확인`
4. 의장이 쟁점(cruxes)을 뽑아 `cruxes.json`에 쓰고, 2라운드 프롬프트에 "누구의 어떤 논거에 답하라"를 넣는다. `코드 확인`
5. 2라운드 좌석은 `round-1.md`를 읽고 "I DISAGREE MOST WITH: [seat]" 양식으로 **다른 좌석 카드에 반박·양보**한다. 이것이 "서로 대화"의 실체다: 직접 전송이 아니라, 같은 파일을 읽고 서로의 카드를 인용하는 것이다. `코드 확인`
6. 의장이 `draft-resolution.md`를 쓰고, 3라운드에서 좌석이 자기 2라운드 카드와 초안만 읽고 Endorse/Amend/Dissent 투표. 4라운드는 없다. `코드 확인`

### 2.2 같은 프로토콜의 앱 구현 (`COUNCIL_RUNNER=api`)

앱이 직접 돌릴 때는 파일 대신 **프롬프트 문자열에 카드를 이어 붙인다**.

```js
// 모형: 2라운드 프롬프트 = 브리프 + 1라운드 전원 카드 + 쟁점
const r1 = seats.map(k => `### ${k}\n${cards[1][k].text}`).join("\n\n");
await Promise.all(seats.map(k => ai.stream({ system: persona(k), messages:[{role:"user", content: brief + r1 + cruxes}] })));
```

| 모형 | 실제 코드 |
|---|---|
| 전원 카드를 이어 붙임 | `app/lib/council.mjs` `cardsBlock` L93-95 |
| 2라운드 프롬프트 조립 | `round2Prompt` L97-128 (`ROUND 1, EVERY SEAT'S CARD` L107) |
| 좌석별 호출 | `runSeat` L304-322 → `ai.stream` (`anthropic.mjs` L26, `/v1/messages` 직접 fetch) |
| 라운드 내 병렬 | `roundAll` L324-331, `Promise.all` + 좌석당 350ms 시차(말풍선 연출용) |
| 좌석 페르소나 | `seats.mjs` `systemFor` L37-49: 에이전트 .md + 브레인 5개 파일을 system에 통째로 주입 |

`코드 확인`. 좌석 호출은 서로 독립된 단발 API 호출이라 라운드 사이에 좌석의 기억이 이어지지 않는다. 이어지는 것은 프롬프트에 다시 붙인 카드 텍스트뿐이다(3라운드는 자기 2라운드 카드 `round3Prompt` L139-140). `코드 확인`

### 2.3 "실시간 통신"처럼 보이는 부분은 UI 쪽이다

- 의장이 쓴 파일을 `watch.mjs`가 1초마다(`setInterval(scan, 1000)` L226) 훑어 `seat_done` 등 이벤트로 바꾸고, 서버가 **SSE**(`/api/stream/<id>`, `server.mjs` L52-60, `text/event-stream`)로 브라우저에 보낸다. `코드 확인`
- 앱 러너 모드는 `council.mjs` `emit` L37-43이 같은 이벤트를 SSE 구독자에게 쓴다. `코드 확인`
- 이 SSE는 **사람(브라우저) 쪽 표시용**이고 좌석 간 통신이 아니다. 앱은 `127.0.0.1`에만 바인드한다(`server.mjs` L83). `코드 확인`

## 2.4 후속 확인 (2026-10-26)

- 12개 좌석 파일 모두 `tools: Read, Grep, Glob`, `maxTurns: 12`(`.claude/agents/council-*.md` L4-5). `코드 확인`. 허용 목록을 강제하는 주체는 Claude Code 런타임이며, 이 동작은 공식 문서·실행으로 확인하지 않았다. `미확인`
- 좌석은 라운드마다 새로 스폰한다(`SKILL.md` L89 "Spawn every seat again", L97). 라운드 사이 좌석 기억은 없다. `코드 확인`
- 2라운드 좌석은 `round-1.md` 전체(전원 카드 + Chair notes)를 읽는다(`round-prompts.md` L58). 의장이 개별 좌석에 주는 것은 쟁점 목록과 그 좌석이 답할 논거 한 줄이다(L60-62). 3라운드는 자기 2라운드 카드와 `draft-resolution.md`만 읽는다(L90). `코드 확인`
- `.json`(`council/cruxes/draft/verdict`)은 웹앱 화면용 사본이고 좌석은 읽지 않는다. 앱 없이도 협의는 진행된다(`live-room.md` L3, L10). `코드 확인`
- 좌석이 지시 범위 밖의 파일을 `Read`로 열 수 있는지: 도구상 가능하다. 프롬프트 지시만으로 막는다. `추론`

## 3. 코드 근거

| 구분 | 파일 | 식별자 | 설명 |
|---|---|---|---|
| 프로토콜 정의 | `.claude/skills/roast-room/SKILL.md` L77-99 | Step 3~6 | 병렬 스폰, 카드 저장, 쟁점, 2·3라운드 |
| 프롬프트 양식 | `references/round-prompts.md` L3, L51-79 | Round 2 | "Seats read the brief and earlier rounds from the session folder", `I DISAGREE MOST WITH` |
| 좌석 권한 | `.claude/agents/council-musk.md` L4 | `tools: Read, Grep, Glob`, `maxTurns: 12` | 읽기 전용, 타 에이전트 호출 불가 (다른 좌석 파일은 이 하나만 확인) |
| 의장 규칙 | SKILL.md L109-114 | Chair rules | 의장은 입장을 내지 않고 카드를 고치지 않음 |
| 에이전트 없는 런타임 | SKILL.md L129 | Without sub-agents | 한 세션이 좌석을 순차로 연기, 좌석 사이 "머리 비우기" |
| 앱 러너 | `app/lib/council.mjs` L93-128, L304-331 | `cardsBlock`, `round2Prompt`, `runSeat`, `roundAll` | 위 표 |
| 표시 경로 | `app/lib/watch.mjs`, `app/server.mjs` L52-60 | `scan`, SSE | 파일 → 이벤트 → 브라우저 |

## 4. 검증 과정

- 수행: `grep -rniE "mesh|peer-to|agent teams|SendMessage|direct message"`(brains·sessions·vendor 제외) → 0건. 위 파일 전문 열람(`SKILL.md`, `round-prompts.md`, `council-musk.md`, `council.mjs`, `anthropic.mjs`, `settings.json`)과 `watch.mjs`·`server.mjs`·`seats.mjs` 일부 열람.
- 판단 근거: 좌석 호출은 전부 의장/앱 코드가 만들고 결과를 의장이 받는다. 좌석끼리의 호출 경로가 코드에 없다.

## 5. 남은 질문 및 미확인

- [ ] `미확인`: `/newroaster`가 만드는 좌석도 같은 권한 틀인지(`agent-template.md` 미열람).
- [ ] `미확인`: Claude Code 서브에이전트가 "서브에이전트는 다른 서브에이전트를 못 만든다"는 런타임 제약. 이 레포는 도구 목록으로 이미 막혀 있어 이 제약에 의존하지 않는다. 런타임 사실은 공식 문서 확인이 필요하다.
- [ ] 질문자가 "mesh"를 떠올린 출처가 Claude Code의 Agent Teams(팀원끼리 메시지)일 수 있다. 이 레포는 그 기능을 쓰지 않는다. `코드 확인`(위 grep)
- [ ] 기능 스펙 후보: "라운드 기반 다중 에이전트 토론 프로토콜". 아직 요청받지 않아 `next.md`에 적지 않았다(이번 세션에서 한 줄 문의로 대체).
