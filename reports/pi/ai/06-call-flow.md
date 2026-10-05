# ai 06: 호출 경로 종합 — `models.streamSimple(...)` 한 번이 지나가는 길

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **이 문서의 위치**: 00~05에서 따로 본 조각을 **한 번의 호출 순서**로 엮는 종합 문서다. 새 코드를 읽은 것은 `api/lazy.ts`의 `lazyStream`/`lazyApi` 줄 번호 확인뿐이고, 나머지는 앞 문서의 내용을 이어 붙였다.
- **검증 수준**: 각 단계의 근거는 아래 표의 문서와 줄 번호에 있다(`코드 확인`). **종단 실험**(§4)은 실제 `Models`, `createProvider`, `lazyApi`, `lazyStream`, 인증, `EventStream` 코드를 그대로 쓰고 **서버와 통신하는 부분만 가짜**로 바꿔서 돌렸다(`실행 확인`). 실제 서버와 통신한 것은 없다.

## 0. 문서 지도
| 문서 | 다룬 것 | 이 문서에서 쓰이는 곳 |
|---|---|---|
| [00-role](./00-role.md) | ai 패키지의 역할, 다른 패키지와의 관계 | §1 |
| [01-types](./01-types.md) | `Message`, `Context`, `Model`, `AssistantMessageEvent` 등 타입 | 전 구간 |
| [02-models-registry](./02-models-registry.md) | `Models`, `Provider`, `createProvider`, 모델 데이터, `applyAuth` | 단계 ①~④ |
| [03-0-event-stream](./03-0-event-stream.md) | `EventStream`, `push`와 `for await` | 단계 ⑦~⑧ |
| [03-1](./03-1-api-anthropic.md), [03-2](./03-2-api-openai-responses.md), [03-3](./03-3-api-openai-compare.md), [03-4](./03-4-api-openai-codex-legacy.md) | 통신 코드(Claude, OpenAI Responses, completions 비교, legacy Codex) | 단계 ⑥ |
| [04-auth](./04-auth.md), [04-01](./04-01-auth-env-and-storage.md) | 인증, 환경변수, 로그인 저장 | 단계 ③ |
| [05-utils](./05-utils.md) | 재시도, 오버플로, 토큰 추정, JSON, 오류 정리 | 단계 ⑥, 오류 경로 |

## 1. 한 장 그림
`agent`나 앱이 `models.streamSimple(model, context, options)`를 한 번 부를 때의 길이다.

```
[호출한 쪽]  models.streamSimple(model, context, options)                          ← ②
   │ 즉시 스트림 C를 돌려받는다 (이 시점에 인증도 통신도 아직 끝나지 않았을 수 있다)
   ▼
[Models]  (models.ts:895-902)
   normalizeContext(context)  Context → TranscriptContext                         ← ② 동기
   lazyStream(model, setup)   빈 스트림 C 생성·반환, setup 은 뒤에서 비동기 실행
      setup:
       ③ requireChatProvider(model)         model.provider 로 Provider 를 찾는다   (:832-835)
       ③ applyAuth(model, options)          인증 확정 → requestModel, requestOptions (:837-869)
              └ getAuth → resolveProviderAuth   호출 옵션 > 저장된 credential > 환경변수  (auth/resolve.ts:33-93)
              └ OAuth 토큰이 곧 만료되면 modify 락 안에서 갱신                           (resolve.ts:102-162)
       ④ provider.streamSimple(requestModel, transcript, requestOptions)
   ▼
[Provider]  (createProvider 가 만든 것, models.ts:1065-1076, 1116-1118)
   dispatch: 모델의 api 값으로 통신 코드를 고른다. 없으면 error 스트림
   ⑤ lazyApi 의 streamSimple → lazyStream (스트림 B), 통신 코드를 import() 로 불러온다  (api/lazy.ts:73~)
   ▼
[통신 코드]  api/anthropic-messages.ts, openai-responses.ts 등
   ⑥ streamSimple: reasoning 을 서버 설정으로 변환, maxTokens 를 컨텍스트에 맞게 자름
      stream(): 상자 A 를 만들어 즉시 반환하고, 안쪽 비동기 함수가
         요청 본문 만들기 → retryProviderRequest 로 전송 → 응답 조각을 pi 이벤트로 변환해 A 에 push
         → usage 와 비용 계산 → done 또는 error push → end()
   ▼
[전달]  A ──forwardStream(복사)──▶ B ──forwardStream(복사)──▶ C
   ⑦ 호출한 쪽: for await (const e of C) 로 이벤트를 받는다
   ⑧ await C.result() 또는 models.complete(...) 로 최종 AssistantMessage 를 받는다
```
- 번호는 §4의 종단 실험 로그와 같은 번호다.
- 스트림 A, B, C는 모두 `AssistantMessageEventStream` 객체(메모리 안의 대기열)이고 네트워크 연결이 아니다(03-0).

## 2. 단계별 정리

### ① 앱이 시작될 때: 레지스트리를 만든다
| 하는 일 | 위치 | 문서 |
|---|---|---|
| `createModels({ credentials, modelsStore })`로 빈 `Models` 생성. 아무것도 안 주면 메모리 저장소 | `models.ts:985`, `:393-397` | 02 §4 |
| provider 등록: 내장은 `builtinModels()`가 42개를 `setProvider` | `providers/all.ts:184-190` | 02 §1.1 |
| provider는 `createProvider({ id, auth, models, api })`로 조립. `models`는 빌드 때 생성한 JSON에서, `api`는 `import()` 지연 로딩 래퍼 | `models.ts:1034`, `providers/anthropic.ts` | 02 §2~§3, §6 |
| (선택) 동적 모델 목록은 `models.refresh()`로 저장소 복원 후 서버에서 갱신 | `models.ts:546-606` | 02 §5 |
| `coding-agent`는 자기 `AuthStorage`(`auth.json`)와 `ModelsStore`를 넘긴다 | `core/model-runtime.ts:211` | 04-01 §2 |

### ② 호출한 쪽이 `Model`, `Context`, `options`를 만든다
- `Model`: `models.getModel("anthropic", "claude-...")`로 메모리에서 꺼낸다(네트워크 없음, `models.ts:472`). 데이터이지 함수가 아니다(01 §2.5, 02 §1.1).
- `Context`: `{ systemPrompt, messages, tools }`. `messages`에는 `UserMessage`, `AssistantMessage`(글, 추론, 도구 호출 조각), `ToolResultMessage`가 들어간다(01 §2.1~§2.3).
- `options`(`SimpleStreamOptions`): `reasoning`, `maxTokens`, `apiKey`, `signal`, `headers`, `cacheRetention`, `sessionId` 등(01 §2.4).

### `Models.streamSimple`이 하는 동기 일과 비동기 일 (`models.ts:895-902`)
```ts
streamSimple(model, context, options) {
    const transcript = normalizeContext(context);              // 동기: Context → TranscriptContext (utils/transcript.ts:30-34)
    return lazyStream(model, async () => {                     // 빈 스트림 C 를 즉시 돌려주고, 아래는 뒤에서
        const provider = this.requireChatProvider(model);       // ③
        const { requestModel, requestOptions } = await this.applyAuth(model, options);   // ③
        return provider.streamSimple(requestModel, transcript, requestOptions);          // ④
    });
}
```
- **`normalizeContext`**: `systemPrompt`와 `tools`를 맨 앞 `SystemMessage` 한 줄로 합친다. 이유는 회사마다 지침을 넣는 자리가 달라서 입력을 먼저 한 가지 모양으로 통일하기 위해서다(01 §2.3).
- **`lazyStream`**: 인증 확정과 통신 코드 로딩이 시간이 걸리는 비동기 작업인데 `streamSimple`은 즉시 반환해야 해서, 빈 스트림(outer)을 먼저 돌려주고 나중에 생기는 진짜 스트림(inner)을 `forwardStream`으로 복사한다. 준비 중 실패는 던지지 않고 `error` 이벤트로 넣는다(03-0 §8.1).

### ③ 인증을 확정한다 (`applyAuth`, `models.ts:837-869`)
1. `getAuth(model, { apiKey, env, signal })` → `resolveProviderAuth`: **호출 옵션 `apiKey` > 저장된 credential > 환경변수** 순서(04 §4). 저장된 것이 있으면 환경변수는 보지 않고 갱신이 실패해도 환경변수로 넘어가지 않는다(04 §4.2).
2. 저장된 OAuth 토큰이 5분 안에 만료되면 `credentials.modify` 락 안에서 한 번만 갱신한다(04 §5.1).
3. 결과(`AuthResult`)를 호출 옵션과 합쳐 `requestOptions`를 만든다: 호출자가 직접 준 값이 우선, 헤더는 인증 결과 → 호출 옵션 → `transformHeaders` 순(04 §3.1, 02 §4.4).
4. 설정이 없으면 `ModelsError("auth", "Provider is not configured: ...")`. 이것이 `error` 이벤트가 된다(§5).

### ④⑤ Provider가 통신 코드를 고른다 (`createProvider`의 `dispatch`, `models.ts:1065-1076`)
- `provider.streamSimple` → 모델의 `api` 값으로 통신 코드를 찾는다(통신 코드 하나이면 그것, 대응표이면 `model.api`로). 없으면 "no API implementation" 오류가 담긴 스트림(02 §3).
- 통신 코드는 `lazyApi(() => import("./anthropic-messages.ts"))`로 감싸져 있어 **첫 호출 때 불러온다**(02 §2.3).

### ⑥ 통신 코드가 서버와 통신한다 (03-1~03-4)
같은 뼈대를 모든 통신 코드가 따른다.
| 단계 | 하는 일 | 문서 |
|---|---|---|
| `streamSimple` | `reasoning`을 서버 설정으로 변환(Claude는 adaptive 또는 토큰 예산, OpenAI는 `reasoning.effort`), `buildBaseOptions`가 `maxTokens`를 `컨텍스트 창 - 추정 토큰 - 4096`으로 자름 | 03-1 §3, 03-2 §3, 05 §3.1 |
| `stream()` 시작 | 빈 `AssistantMessageEventStream`(스트림 A)을 만들고 안쪽 비동기 함수를 시작한 뒤 즉시 반환 | 03-1 §1.1, 03-0 |
| 요청 만들기 | `resolveTranscript`, `transformMessages`(모델을 바꿨을 때 이력 보정), `convertMessages`, `convertTools`, 추론 설정, 캐시 표시 | 03-1 §4, 03-2 §4, 03-3 §3 |
| 전송 | `retryProviderRequest`(1층 재시도) 안에서 SDK 또는 `fetch`/`WebSocket`으로 요청 | 03-1 §1.2, 05 §2.1 |
| 응답 읽기 | Claude: pi가 SSE를 직접 해석. OpenAI Responses: SDK가 해석. completions: SDK 청크를 직접 해석 | 03-1 §5.1, 03-2 §1.2, 03-3 §4 |
| 변환 | 서버 이벤트마다 `output`(공유 `AssistantMessage`)을 갱신하고 `stream.push(...)` | 03-1 §5.2, 03-2 §5.1 |
| 마무리 | 사용량과 `calculateCost`, 종료 사유를 `StopReason`으로 변환, `done` push, `end()` | 03-1 §5.4, 03-2 §5.3 |

### ⑦⑧ 호출한 쪽이 받는다
- 이벤트는 A → B → C로 **두 번 복사**된다(`lazyStream`이 `lazyApi`와 `Models.stream` 두 곳에 있기 때문, 03-0 §8.1).
- **`for await (const e of C)`**: 이벤트를 하나씩 받는다. 비어 있으면 열쇠를 맡기고 잠들고, 다른 코드가 실행된다(03-0 §6).
- **`await C.result()`**: 최종 `AssistantMessage`. `done`/`error` 이벤트가 push되면 채워지고 **절대 reject하지 않는다**(03-0 §5.4).
- **`models.completeSimple(...)`**: 이벤트를 꺼내지 않고 `.result()`만 기다리는 포장이다(`models.ts:904-910`).

## 3. 한 번의 호출에서 만들어지는 것들
### 3.1 스트림 세 개와 만드는 곳
| 스트림 | 만드는 곳 | 소비하는 곳 |
|---|---|---|
| **A** | 통신 코드의 `stream()`(예: `anthropic-messages.ts:578`) | `lazyApi`의 `forwardStream`(`api/lazy.ts:35`) |
| **B** | `lazyApi`가 만드는 `lazyStream`(`api/lazy.ts:73~`) | `Models.stream`의 `forwardStream`(`api/lazy.ts:35`) |
| **C** | `Models.streamSimple`의 `lazyStream`(`models.ts:897`) | **호출한 쪽**(`agent-loop.ts:414`의 `for await`) |

### 3.2 데이터가 변해 가는 모양
| 단계 | 모양 | 어디서 |
|---|---|---|
| 호출 입력 | `Context { systemPrompt, messages, tools }` | 호출한 쪽 |
| Models 입구 | `TranscriptContext { messages: [system(지침+도구), ...] }` | `normalizeContext` |
| 인증 후 | `requestModel`(주소가 바뀔 수 있음), `requestOptions { apiKey, headers, env, ... }` | `applyAuth` |
| 통신 코드 입구 | 모델이 중간 시스템 메시지를 못 받으면 한 줄로 합침 | `resolveTranscript` |
| 서버로 가는 것 | 회사별 요청 본문(Claude `messages`+`system`, OpenAI `input`, completions `messages`) | `buildParams` + 변환 함수 |
| 서버가 보내는 것 | 회사별 이벤트(`content_block_delta`, `response.output_text.delta`, `ChatCompletionChunk`) | SSE, WebSocket, SDK |
| pi 이벤트 | `AssistantMessageEvent`(`text_delta` 등 12종) + 공유 `partial` | 통신 코드가 `push` |
| 최종 | `AssistantMessage { content[글,추론,도구호출], usage, stopReason }` | `.result()` |

## 4. 종단 실험 (`실행 확인`)
**실제 코드**: `createModels`, `createProvider`, `lazyApi`, `lazyStream`, `applyAuth`, `resolveProviderAuth`, `envApiKeyAuth`, `normalizeContext`, `AssistantMessageEventStream`. **가짜**: 통신 코드(서버와 통신하는 부분). 가짜 통신 코드는 자기가 받은 인자를 찍은 뒤 `start`, `text_*`, `done`을 push한다. 스크립트는 `artifacts/pi/ai-demos/call-flow-demo.ts`, 출력은 `call-flow-demo.2026-10-05.log`다.

### 호출 1: 정상
```
[+  4ms] ① getModel → demo/fake-1 (api=fake-api)
[+  5ms] ② streamSimple() 반환됨   ← 호출한 쪽은 스트림 객체를 이미 받았다
[+  5ms]   (지연 로딩) 통신 코드 모듈을 불러옴
[+ 15ms]   ⑥ 통신 코드 streamSimple() 호출됨
[+ 15ms]      model: provider=demo, api=fake-api, id=fake-1, baseUrl=https://example.invalid/v1
[+ 15ms]      context(TranscriptContext): messages=system, user
[+ 16ms]      맨 앞 system 메시지: content="너는 도우미야", toolsAdded=["read"]
[+ 16ms]      options: apiKey=KEY_FROM_ENV, reasoning=high, headers=undefined
[+ 47ms]   ⑦ 호출한 쪽이 받은 이벤트: start
         ... text_start, text_delta "안", text_delta "녕", text_end
[+ 88ms] ⑧ result(): stopReason=stop, content=[{"type":"text","text":"안녕"}]
```
확인된 것:
1. **`streamSimple()`은 `+5ms`에 반환되고, 통신 코드는 `+15ms`에 호출된다.** 반환 뒤에 인증 확정과 통신 코드 로딩이 진행된다(02 §4.3의 ①~⑤).
2. **통신 코드가 받은 `context`는 `system, user` 두 메시지**이고, 맨 앞 system 메시지에 `systemPrompt`가 `content`로, `tools`가 `toolsAdded`로 들어 있다. `normalizeContext`가 합친 결과다(01 §2.3).
3. **`apiKey=KEY_FROM_ENV`**: 환경변수 `DEMO_FLOW_KEY`가 `applyAuth`를 거쳐 `options.apiKey`로 들어왔다(04).
4. `reasoning=high`는 그대로 전달된다(`streamSimple`의 변환은 통신 코드가 한다).

### 호출 2: 환경변수 키를 지운 뒤 같은 호출
```
[+ 89ms] streamSimple() 반환됨 (예외가 던져지지 않았다)
[+ 95ms] 이벤트: error
[+ 95ms] result(): stopReason=error, errorMessage=Provider is not configured: demo
```
- **인증 실패는 예외가 아니라 `error` 이벤트와 `stopReason: "error"`로 전달된다.**
- 이 호출에서는 `(지연 로딩) 통신 코드 모듈을 불러옴` 줄이 **나오지 않았다.** 인증 확정(③)이 통신 코드 선택과 로딩(④⑤)보다 먼저라서, 인증이 실패하면 통신 코드는 불러지지도 않는다.
- 이 호출 도중 직전 호출 1의 소비자가 `done` 이벤트를 찍은 것(`+89ms`)도 보인다. 호출 1의 `.result()`는 소비자가 `done`을 꺼내기 전에 이미 채워졌다(03-0 §7).

### 호출 3, 4
- `completeSimple`은 이벤트를 꺼내지 않고도 최종 결과를 돌려준다(`stopReason=stop`, `text=안녕`).
- 호출 4에서 `apiKey: "KEY_FROM_OPTION"`과 `headers: { "x-trace": "abc" }`를 옵션으로 넘기자 통신 코드에 그대로 도착했다(`options: apiKey=KEY_FROM_OPTION, headers={"x-trace":"abc"}`). 호출 옵션이 환경변수보다 우선한다(04 §4).
- 호출 3과 4에서 `(지연 로딩) ...` 줄이 **매번** 나온다. 이 실험의 로더가 `import()`처럼 결과를 캐시하지 않기 때문이다. **`lazyApi` 자체는 로드 함수를 호출마다 부르고, 중복 로딩 방지는 `import()`의 실행 환경 캐시에 맡긴다**(`api/lazy.ts` 주석: "the host's import cache deduplicates loads").

## 5. 오류가 지나가는 길
어느 단계에서 실패하든 호출한 쪽은 **같은 방식**으로 받는다: 예외가 아니라 `stopReason: "error" | "aborted"`인 `AssistantMessage`와 `error` 이벤트.
| 실패 지점 | 어떻게 전달되나 | 문서 |
|---|---|---|
| provider를 모름, 채팅 모델이 아님 | `ModelsError("provider")`가 `lazyStream`의 `catch`에서 `error` 이벤트로 | 02 §4, 05 §5.2 |
| 인증 없음, OAuth 갱신 실패, 저장소 오류 | `ModelsError("auth" \| "oauth")` → `error` 이벤트(§4 호출 2에서 확인) | 04 §4~§5 |
| 모델의 `api`에 맞는 통신 코드 없음 | `ModelsError("stream")`가 담긴 스트림 | 02 §3.3 |
| 통신 코드 안(요청 본문 만들기, 전송, 응답 해석) | 통신 코드의 `try`/`catch`가 `error` push + `end()` | 03-1 §6, 03-2 §6 |
| 일시 오류(503, 429 등) | 1층 재시도(`retryProviderRequest`, 응답 시작 전)가 먼저 시도 | 05 §2.1 |
| 취소(`signal`) | `aborted`로 구분되어 `error` 이벤트 | 03-1 §6 |
| **직접 호출한 통신 코드의 인증 누락** | **동기 throw**(`streamSimple`이 `Models`를 거치지 않을 때만) | 03-1 §3 |

**`stream`이 끝난 뒤의 2층 재시도와 컨텍스트 초과 처리는 ai 패키지가 하지 않는다.** ai는 판정 함수(`isRetryableAssistantError`, `isContextOverflow`)와 반복문(`retryAssistantCall`)만 제공하고, 실제로 부르는 것은 `coding-agent`와 `durable`이다(05 §2.3).

## 6. 책임 분담표
| 일 | 누가 | 위치 |
|---|---|---|
| `Context`를 통일된 모양으로 | `normalizeContext` | `utils/transcript.ts:30` |
| 어느 Provider인지 | `Models.requireChatProvider` (`model.provider`) | `models.ts:832` |
| 키와 토큰 | `applyAuth` + `resolveProviderAuth` + `CredentialStore` | `models.ts:837`, `auth/resolve.ts` |
| 어느 통신 코드인지 | `createProvider`의 `dispatch` (`model.api`) | `models.ts:1065` |
| 통신 코드를 언제 불러올지 | `lazyApi` | `api/lazy.ts:73` |
| 서버 말투로 요청 | 통신 코드(`buildParams`, `convertMessages`) | `api/*.ts` |
| 서버 응답을 공용 이벤트로 | 통신 코드 / 공용 `processResponsesStream` | `api/*.ts`, `openai-responses-shared.ts` |
| 이벤트 전달과 최종 결과 | `AssistantMessageEventStream` | `utils/event-stream.ts` |
| 요청 단위 재시도 | `retryProviderRequest` | `utils/provider-retry.ts` |
| 비용 계산 | `calculateCost`를 통신 코드가 부름 | `models.ts:1193` |
| **도구 실행, 응답 단위 재시도, 압축, 저장** | **ai가 아니라 `agent`, `coding-agent`** | 00 §4 |

## 7. 설계의 패턴 (코드에서 확인된 것)
1. **입력을 먼저 통일하고 출력을 공용 이벤트로 통일한다.** 중간의 회사별 차이는 통신 코드 안에 가둔다(`TranscriptContext`, `AssistantMessageEvent`).
2. **즉시 반환 + 뒤에서 채우기.** `streamSimple`도 `stream`도 빈 스트림을 먼저 돌려주고, 비동기 작업이 `push`로 채운다(`lazyStream`, 통신 코드의 `(async () => {...})()`).
3. **실패도 값으로 전달한다.** 예외 대신 `error` 이벤트와 `stopReason`. `.result()`는 reject하지 않는다.
4. **조립식 provider.** `createProvider`로 "주소 + 인증 + 모델 + 통신 코드"를 조립하고, 하나의 통신 코드를 여러 provider가 재사용하며 차이는 `compat`로 맞춘다(03-3 §6).
5. **필요할 때 불러온다.** 통신 코드와 OAuth 구현을 지연 로딩한다.
6. **판정은 제공하고 정책은 위에 맡긴다.** 재시도 여부, 컨텍스트 초과 판정은 함수로 제공하지만 실제 반복과 압축은 `coding-agent`가 한다.
7. **저장 위치는 앱이 정한다.** `CredentialStore`, `ModelsStore`는 인터페이스이고 기본 구현은 메모리다.

## 8. 이전 분석(Q4)과 달라진 점 정리
이전 [Q4](../questions/q4-ai-package-roles.md)는 SHA `4259686d9` 기준이다. 이번에 이 commit에서 다시 확인하고 바로잡은 것이다.
| Q4의 서술 | 이 commit에서 확인한 것 |
|---|---|
| 재시도는 agent-core의 `harness/...`가 한다 | harness는 삭제되었다(`7fd478a2e`). 지금은 `coding-agent`(`agent-session.ts`)와 `durable`이 한다(05 §2.3) |
| "`streamSimple`을 직접 호출했는데 인증이 없으면 동기로 throw한다(`types.ts:755` 주석)" | **어느 `streamSimple`인지에 따라 다르다.** `Models.streamSimple`은 던지지 않고 `error` 이벤트(§4 호출 2). **통신 코드 모듈의 `streamSimple`을 직접 부를 때만** 동기 throw(03-1 §3). 이 문서와 [01-types](./01-types.md) §3의 "인증 누락만 동기 throw"도 이 구분을 붙여 읽어야 한다 |
| 줄 번호(`createProvider :1028`, `calculateCost :1187`, `refresh :545`) | 각각 `:1034`, `:1193`, `:546` (02 §9) |
| "레포 안에서 런타임 카탈로그를 쓰는 provider는 `radius`뿐" | ai 안에서는 맞고, `coding-agent`에도 `refreshModels`를 쓰는 곳이 더 있다(02 §3.3) |
| (언급 없음) | `openai` provider의 ChatGPT 구독 로그인이 새 경로이고 `openai-codex`는 legacy(03-2 §0) |
| (언급 없음) | SSE 해석은 통신 코드마다 다르다: Claude는 pi가 직접, OpenAI Responses는 SDK, legacy Codex는 pi가 직접(03-2 §1.2) |

## 9. 아직 보지 않은 영역 (`미확인`)
- **다른 통신 코드**: `google-generative-ai.ts`, `google-vertex.ts`, `bedrock-converse-stream.ts`, `mistral-conversations.ts`, `pi-messages.ts`(Radius), `azure-openai-responses.ts`. 뼈대는 같을 것으로 보이나 세 파일에서 확인한 것을 일반화한 `추론`이다.
- **chat 이외의 호출**: 이미지 생성(`generateImages`, `images*.ts`), 분류(`classify`, `api/*classify*`), deferred 응답(`fetchDeferred`, `cancelDeferred`)
- **`providers/faux.ts`**(테스트용 가짜 provider, 710줄)와 `test/` 디렉터리의 테스트 방식
- **`compat.ts`**(구 전역 API), `session-resources.ts`, `bun-oauth.ts`, `cli.ts`
- `assistant-message-frame.ts`(스트림 진행을 저장하는 프레임), `node-http-proxy.ts`
- 다른 OAuth 구현(GitHub Copilot, xAI, Kimi 등), `coding-agent`의 `AuthStorage` 나머지
- 실제 서버와의 통신, 실제 로그인

## 10. ai 패키지 정리와 다음
- **ai 패키지는 "어떤 회사의 모델이든 같은 입력(`Context`)으로 부르고 같은 출력(이벤트 스트림과 `AssistantMessage`)을 받는" 층**이다. 위 00~06이 그 구조를 코드 줄 단위로 확인한 기록이다.
- **다음 단계**: `agent` 패키지. 이 commit에서 `agent`는 6개 파일(`agent-loop.ts`, `agent.ts`, `types.ts`, `stream-fn.ts`, `proxy.ts`, `index.ts`)로 줄었으므로(00 §7) 이전 Q5(agent loop), Q6(Agent 클래스)를 새 기준으로 다시 읽고, 이 문서의 ⑦(`agent-loop.ts:414`가 스트림을 받는 곳)에서 이어 간다.
- **wiki 정리**: AGENTS.md의 규칙상 재사용할 핵심은 `wiki/projects/pi.md`(없음)로 요약해야 한다. ai 패키지를 마친 이 시점에 00~06의 핵심만 `wiki/projects/pi.md`에 쌓고 `wiki/index.md`, `wiki/log.md`를 갱신하는 것이 좋다.
