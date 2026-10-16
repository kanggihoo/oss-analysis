# e2e (tester-army) Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/tester-army/e2e`
- **분석 Commit SHA**: `dbdec7088693d9d91f771ea4b6fad2e838e209c0` (`feat: add claude and codex plugins (#1107)`, 2026-10-14)
- **분석 일자**: 2026-10-14
- **작업트리 상태**: Clean (`--depth 50` shallow clone)
- **분석 목적**: 학습 (초기 구조 파악)
- **메타데이터**: [repo-metadata.txt](../../artifacts/e2e/repo-metadata.txt)
- **검증 수준 범위**: 아래 내용은 모두 `코드 확인`(파일을 읽음)이다. 빌드·테스트는 **실행하지 않았다**(`미확인`).

---

## 2. 프로젝트 개요

웹·모바일 앱용 E2E 테스트 프레임워크다. 테스트 안에서 자연어 목표(`agent.act('...')`)를 쓰면 LLM 에이전트가 앱을 조작하고, 검증은 locator/`expect`로 한다. (README)

핵심 아이디어는 **replay cache**다. `act` 뒤에 검증 단계가 통과하면 그 행동 기록을 저장하고, 다음 실행에서는 모델 호출 없이 재생한다. 앱이 바뀌어 재생이 어긋나면 그 지점부터 에이전트가 이어받는다 (`docs/cache.mdx`, 코드로 확인: `agent/step-cache.ts` `begin()`).

pnpm 모노레포. 추적 파일 1,821개. 핵심은 `packages/e2e` (약 594개 파일, `src` 비테스트 TS 약 6만 줄).

| 패키지 | 역할 (README) |
|---|---|
| `packages/e2e` | SDK + runner + CLI (`e2e`) |
| `packages/web` | 브라우저 엔진 (Playwright) |
| `packages/mobile` | iOS/Android 엔진 (agent-device) |
| `packages/decision` | 모델 없이 쓰는 decision executor |
| `packages/github`, `kernel`, `limrun`, `eas`, `smol` | PR 코멘트 reporter, 호스팅 브라우저·시뮬레이터 |
| `apps/*`, `examples/*` | testbed, 벤치마크, 프레임워크별 예제 |
| `skills/`, `plugins/e2e`, `docs/` | 코딩 에이전트용 skill, Claude/Codex plugin, 문서(mdx) |

`packages/e2e/src` 모듈 크기 (비테스트 TS 줄 수, 코드 확인):
`agent` 12.3k · `run` 11.8k · `report` 5.5k · `internal` 4.3k · `cli` 4.2k · `cache` 3.2k · `engine` 2.7k · `config` 3.5k · `collect` 2.1k · `expect` 2.0k · `mcp` 1.9k · `locator` 1.6k

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | CLI → run → worker/TargetExecutor → agent / cache / engine |
| 대표 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | `agent.act()` 한 번: 캐시 조회 → 재생 or 모델 폴백 → 기록 |

검증: 두 그림 모두 `deliver` showcase 9/9 검사 통과, `visual-check` 통과(자동 브라우저 증거). 시각적 품질의 사람 검토는 `pending`.

### 그림 읽는 가이드
1. **구조도 위쪽 줄**: CLI(`cli/index.ts main()`) → `run()`(`run/runner.ts`) → 테스트 수집(`collect/`) → `TargetExecutor`(`run/execute.ts`). 테스트 한 번(attempt)을 실행하는 곳이 `TargetExecutor.runAttempt`다.
2. **오른쪽 열**: `TargetExecutor`가 만든 `agent` fixture → `agent.act()`. 여기서 캐시(아래)와 엔진(오른쪽)과 모델 루프(왼쪽)가 갈라진다. 이 노드가 이 프로젝트의 중심이다.
3. **실행 흐름 그림**: `begin()`이 캐시를 읽어 재생을 시도하고, `undefined`면(= 못 이어받으면) `executor.runStep()`으로 모델 루프를 돈다. 끝나면 `conclude()`가 기록 여부를 정한다. 실제 저장은 attempt 끝에 검증이 통과한 뒤다.
4. **단순화한 부분**: 흐름 그림에서 엔진 호출(replay의 행동, executor의 `ctx.actions`)과 `ActResult` 반환은 가독성 때문에 뺐다. 구조도의 `collect → TargetExecutor` 화살표도 단순화다.

---

## 4. 확인한 사실 (코드 근거)

| 사실 | 근거 | 수준 |
|---|---|---|
| `act` 단계만 캐시 대상. assert는 상태를 바꾸지 않으므로 trace가 비어 캐시하지 않음 | `agent/act.ts` `ActDispatch` 생성자 (`spec.kind === 'act' && executor.cache !== 'off'`) | 코드 확인 |
| 한 step의 흐름: `stepCache.begin()` 결과가 있으면 그 verdict를 쓰고, 없으면 `executor.runStep(context)` | `agent/act.ts` `dispatchStep()` | 코드 확인 |
| 재생 실패는 에러가 아니라 miss. 못 읽거나 깨진 entry도 miss | `cache/decide.ts` 머리 주석, `agent/step-cache.ts` `begin()` | 코드 확인 |
| 시작 route가 다르면 재생 안 함(`wrong-context`). `navigate`로 시작하는 trace는 예외 | `cache/decide.ts` `decideTraceReplay` | 코드 확인 |
| `cache.strict`에서는 낡은 recording을 모델에 넘기지 않고 `REPLAY_STALE`로 실패 | `agent/step-cache.ts` `failIfStale()` | 코드 확인 |
| 저장은 파일 하나/키(`.e2e/cache/`), 임시 파일 + atomic rename, lock 없음(last-write-wins) | `cache/store.ts` 머리 주석 | 코드 확인 |
| `conclude`: 실패면 재생에 쓴 entry를 evict, 성공이면 stage 또는 keep. 모델이 응답하지 못한 실패는 evict하지 않음 | `agent/step-cache.ts` `conclude()`, `failedStepOutcome()` | 코드 확인 |
| 기본 cache mode는 `read-write` | `config/resolve.ts:355` | 코드 확인 |
| 모델 루프는 교체 가능한 `StepExecutor` 인터페이스. 내장은 `createToolLoopExecutor`(AI SDK 사용) | `agent/executor.ts`, `agent/tool-loop.ts:184` | 코드 확인 |
| 엔진은 `Engine` 인터페이스(SPI v1) 뒤에 숨는다. `createEngineSession`이 attempt용 세션을 만든다 | `engine/contract.ts:25`, `engine/index.ts:654`, `run/execute.ts:607` | 코드 확인 |
| AI SDK(`ai`, `@ai-sdk/*`)는 optional peer dependency. 모델 없이도 locator 테스트는 동작한다고 문서화 | `packages/e2e/package.json`, `docs/core-concepts.mdx` | 코드 확인(package.json) / 문서 주장(동작 자체는 `미확인`) |

### 미확인
- 빌드·테스트·실제 `npx e2e` 실행 (설치와 모델 호출 비용, 사용자 확인 필요)
- runner ↔ worker 프로세스 사이 IPC 프로토콜(`run/worker/protocol.ts`), scheduler 동작
- `replayTrace`가 어떻게 요소를 다시 찾는지(`cache/relocate.ts`, `cache/anchors.ts`), end-state 검증 기준
- cache key 구성(`cache/identity.ts`) 상세
- tool-loop의 프롬프트·도구 정의·loop guard
- `report/`, `mcp/`, `explore/`, `oauth/`, `web`/`mobile` 엔진 구현, `decision` 패키지

---

## 5. 질문과 답변 (대화 기록, 2026-10-14)

모두 읽은 파일 기준이며 실행은 하지 않았다. "일반 지식"은 이 레포나 웹 검색으로 확인하지 않은 내용이다.

### Q1. `agent.act()`는 무엇이고 flow.html은 무엇을 그린 것인가
- `agent.act('목표')`는 테스트 코드에서 자연어로 목표 하나를 넘기는 함수다. 어떤 버튼을 누를지는 LLM이 화면을 보고 정한다. 끝나면 반환하고, 실패하면 예외가 난다. (`docs/core-concepts.mdx`)
- flow.html은 이 호출 한 번의 내부 처리다: `begin()`으로 캐시 조회 → 기록이 있으면 모델 없이 재생 → 없거나 어긋나면 `runStep`으로 모델 루프 → `conclude()`가 기록 여부 결정. 실제 저장은 뒤따르는 검증이 통과한 뒤다. (`코드 확인`: `agent/act.ts` `dispatchStep`, `agent/step-cache.ts`)

### Q2. 별도 API가 필요한가, claude-code나 codex CLI를 쓸 수 있는가
- CLI를 빌려 쓰는 구조가 아니다. Vercel AI SDK(`ai`, `@ai-sdk/*`, optional peer dependency)로 모델을 직접 호출한다. provider는 anthropic, google, openai, openai-compatible, xai. (`코드 확인`: `packages/e2e/package.json`)
- 인증: API 키, 또는 `npx e2e login <provider>` OAuth로 구독을 쓴다. 문서에 나온 구독은 ChatGPT Plus/Pro, GitHub Copilot, OpenCode Console, SuperGrok/X Premium+. (`src/oauth/`는 파일 목록만 확인, `docs/subscriptions.mdx`)
- Claude Max/Team은 로그인이 아니라 "플랜의 월간 API 크레딧으로 결제되는 API 키"로 문서에 적혀 있다. 실제 과금은 `미확인`.
- locator와 `expect`만 쓰는 테스트, 캐시 재생, custom executor/`@e2e-dev/decision`은 모델이 필요 없다는 것이 문서 주장이다. 동작 자체는 `미확인`.

### Q3. Claude Code가 Playwright 코드를 쓰고 고치는 방식과 무엇이 다른가
- 핵심 차이는 AI가 일하는 시점이다. Playwright 직접 작성은 코드 작성 때 1회이고, 이후 실행에는 AI가 없다. e2e는 첫 실행과 앱이 바뀌어 재생이 어긋났을 때 모델이 일한다.
- 실질적인 차이는 좁다. (1) 깨졌을 때 사람이 고치는가 모델이 이어받는가, 고친 내용이 코드 diff에 남는가 캐시 파일에 남는가, (2) CI에서 자동 복구 여부와 진짜 버그를 덮을 위험(`cache.strict`가 이를 막는 옵션: `코드 확인` `failIfStale`), (3) 테스트가 selector 코드냐 자연어 의도냐, (4) 모바일까지 같은 문법.
- 결론: 웹 앱 하나에 화면이 안정적이면 "Claude Code가 작성 → 실행 → 에러 시 수정" 방식으로 충분하다. 복구 성공률은 실행하지 않아 `미확인`.
- 공통점: 웹 엔진은 내부적으로 Playwright다.

### Q4. 환경별로 내부에서 무엇이 돌아가는가
| 환경 | 패키지 | 내부 도구 (`코드 확인`: package.json) |
|---|---|---|
| 웹 (Chromium/Firefox/WebKit) | `@e2e-dev/web` | `playwright-core` |
| iOS/Android (시뮬레이터, 에뮬레이터, 연결된 폰) | `@e2e-dev/mobile` | `agent-device` (Callstack) |

- 코어는 `Engine` SPI(`engine/contract.ts`)만 안다. 엔진이 선언한 동작만 모델의 도구로 노출된다. `agent-device` 아래의 도구는 `미확인`.
- 어느 엔진을 쓸지는 `e2e.config.ts` target 설정으로 정해지는 것으로 보인다 (`추론`, `config/` 미확인).
- 기기·브라우저 공급처: `kernel`, `smol`(웹), `limrun`, `eas`(모바일).

### Q5. 안드로이드는 Kotlin인데 테스트도 TypeScript인가
- 그렇다. 테스트는 앱 언어와 무관하게 TypeScript다. `examples/with-compose`는 `app/`(Kotlin) + `e2e/`(Node 프로젝트, `tests/*.e2e.ts`)로 구성된다. 에뮬레이터에 설치된 앱을 밖에서 조작하는 블랙박스 방식이다. (`코드 확인`)
- 앱이 `testID`를 노출해야 `getByTestId`가 동작한다. Compose에서 어떻게 노출되는지는 `app/` 미확인.
- 일반 지식: Kotlin 개발자는 보통 Espresso, Compose UI Test(앱 프로젝트 안, Kotlin)를 쓴다. UI Automator, Maestro(YAML, Android/iOS), Appium도 있다. Android만 한다면 e2e의 Node/TS 환경은 주류 선택이 아니다 (판단).

### Q6. Maestro는 어떤 도구인가
- 일반 지식: YAML 시나리오로 쓰는 모바일 UI 테스트 도구로 Android/iOS에서 같은 파일이 돈다. 앱 언어와 무관(Flutter, React Native 포함). 웹 지원 여부와 성숙도는 확신이 없다(`미확인`).
- e2e와의 차이: Maestro는 사람이 단계를 적고 모델 없이 결정적으로 돈다. e2e는 목표를 적고 모델이 풀고 캐시로 재생한다.

### Q7. 지원하는 환경은 웹, 모바일 외에 무엇이 있는가
- 기본 제공 UI 엔진은 웹과 모바일뿐이다.
- API 테스트: `fetch` + `expect`로 UI 테스트와 같은 파일에서 쓴다. `app`만 받는 테스트는 모델을 부르지 않는다. (`docs/api-testing.mdx`)
- 데스크톱, TV 등은 `defineEngine`으로 엔진을 직접 구현해야 한다고 문서에 적혀 있다 (`docs/writing-an-engine.mdx`). 기본 제공 근거는 찾지 못했다. 직접 만든 엔진의 난이도는 `미확인`.
- 받은편지함, DB 같은 것은 엔진이 아니라 `test.extend` fixture로 처리한다.

---

## 6. 분석자 평가 (2026-10-14)

- 사용자 판단: "그렇게 매력이 느껴지는 오픈소스는 아니다." 이에 따라 초기 분석에서 멈추고 후속 분석은 진행하지 않았다.
- 이유로 정리하면: 웹 하나라면 Claude Code로 Playwright를 쓰는 편이 더 단순하고, Android만 한다면 Espresso/Compose UI Test/Maestro가 주류이며, 이 도구의 고유 가치는 "자연어 목표 + 검증 후 재생 캐시"에 한정된다. (판단)
- 다시 볼 만한 부분: replay cache 설계(검증 통과 후에만 저장, miss는 에러가 아님, `cache.strict`)와 모델 루프/엔진을 인터페이스로 분리한 구조.

---

## 7. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md) (후속 질문 후보는 그쪽에 남아 있다)
- **이전 wiki 요약**: 2026-10-16 삭제. 원문은 `git show b52364d:wiki/projects/e2e.md`
