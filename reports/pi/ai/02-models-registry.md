# ai 02: `Models` 레지스트리와 `Provider` — 모델 목록과 호출 입구

- **기준 commit**: `3874b3e98` (2026-10-02, worktree clean) / **분석일**: 2026-10-04
- **선행 문서**: [00-role](./00-role.md), [01-types](./01-types.md)
- **읽은 파일**: `src/models.ts`(1256줄 전체), `src/providers/anthropic.ts`(90줄), `openai-codex.ts`(20줄), `openai.ts`(23줄), `groq.ts`(15줄), `all.ts`(190줄 중 60~190), `models-store.ts`(46줄), `model-catalog.ts`(81줄), `api/lazy.ts`(앞 80줄), `scripts/model-data.ts`(앞부분). 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 구조와 동작은 `코드 확인`. 모델 데이터 값은 `npm run hydrate-model-data`를 실행해서 `실행 확인`했다(§6.6, §6.8). 단, 그 데이터는 실행한 시점(2026-10-04)의 외부 사이트 기준이라 commit에 고정된 값이 아니다.
- 이 문서는 "01에서 본 타입을 담는 그릇과 호출 입구"를 다룬다. 호출 한 번의 전체 경로는 마지막 문서(06)에서 합친다.

## 0. 이 문서의 질문
1. `models.getModel("anthropic", "claude-...")`의 `Model`은 어디서 오는가?
2. `provider`는 무엇이고 `api`와 어떻게 연결되는가?
3. `Models`는 호출 때 무슨 일을 하는가?
4. 모델 목록은 어떻게 갱신되는가?

## 1. 한눈에 보는 구조

### 1.1 먼저 구분할 세 타입: `Model`, `Provider`, `Models`
이름이 비슷해서 헷갈리기 쉽다.

| 타입 | 정체 | 한 줄 설명 | 위치 |
|---|---|---|---|
| `Model` (단수) | 데이터 | 모델 한 개의 명세서. `id`, `api`, `provider`, `baseUrl`, `cost`, `contextWindow`, `compat` 등을 담는다. 함수는 없다. | `types.ts:1111` |
| `Provider` | 객체 | 서비스 하나. 모델 목록, 인증 방법, 통신 코드를 가지고 `getModels()`, `stream()` 등의 메서드를 가진다. | `models.ts:144` |
| `Models` (복수) | 객체 | `Provider`들을 모아 둔 상자이자 호출 입구. `getModel()`, `stream()`, `complete()`, `refresh()` 등을 가진다. | `models.ts:244`, `:384` |

```
Models (상자)
 └ Provider "anthropic"
      └ Model "claude-opus-..." , Model "claude-sonnet-..." , ...
 └ Provider "openai"
      └ Model ...
```
- `Provider`는 `Model`들을 **가진다** (`provider.getModels()`, `models.ts:166`).
- `Model`은 자기 소속 provider를 **이름으로 기록한다** (`model.provider`가 `"anthropic"` 같은 문자열, `types.ts:1101`).
- 사용 순서: `models.getModel("anthropic", "claude-...")`로 `Model`을 꺼내고, 그 `Model`을 `models.stream(model, context, options)`에 인자로 넘긴다. `stream`은 `Model`의 메서드가 아니라 `Models`와 `Provider`의 메서드다.

### 1.2 `stream`은 세 층에 있다
같은 이름의 `stream`이 세 곳에 있고 서로 다른 객체의 메서드다. `model`은 세 호출에 계속 인자로 넘어간다.

```
호출한 쪽
 └ models.stream(model, context, options)               1층 Models.stream      (models.ts:871)  준비
      ├ Context를 TranscriptContext로 변환, 빈 스트림 반환, provider 찾기, 인증 확정
      └ provider.stream(model, transcript, options)     2층 Provider.stream    (models.ts:1116) 통신 코드 선택
           └ model.api로 통신 코드를 골라서
             통신코드.stream(model, transcript, options)  3층 통신 코드의 stream (api/*.ts)      실제 통신
```

| 층 | 메서드 | 받는 대화 | 하는 일 |
|---|---|---|---|
| 1 | `Models.stream` | `Context` | 준비. 호출하는 쪽이 부르는 입구 |
| 2 | `Provider.stream` | `TranscriptContext` | `model.api`로 통신 코드를 고른다. |
| 3 | 통신 코드의 `stream` | `TranscriptContext` | 회사 서비스와 실제로 통신한다. (03에서 읽는다) |

### 1.3 `Models`의 내부 구성
```
Models (레지스트리)  ← createModels() / builtinModels()
 ├ Provider "anthropic"  { 인증, 모델 목록, api: anthropic-messages }
 ├ Provider "openai-codex" { 인증(OAuth), 모델 목록, api: openai-codex-responses }
 ├ Provider "openai"     { ... }
 └ ... (내장 42개)

Provider 안:  auth (키 찾는 법) + models (Model 목록) + api (통신 코드, 지연 로딩)
```

| 개념 | 한 줄 설명 | 위치 |
|---|---|---|
| `Provider` | "한 회사/계정"을 다루는 실행 단위. 인증 방법, 모델 목록, 호출 구현을 가진다. | `models.ts:144-233` (인터페이스) |
| `Models` | `Provider`들의 모음. 모델 조회, 인증 적용, 호출 입구를 제공한다. | `models.ts:244-353` (인터페이스), `:384` (`ModelsImpl`) |
| `createModels()` | 빈 `Models`를 만든다. | `models.ts:985` |
| `createProvider()` | 부품(id, 인증, 모델, api)으로 `Provider`를 조립한다. | `models.ts:1034` |
| `builtinModels()` | 내장 provider 42개를 모두 등록한 `Models`를 만든다. | `providers/all.ts:184` |

## 2. `Provider`: 한 회사를 다루는 단위

### 2.1 인터페이스의 주요 항목 (`models.ts:144-233`)
| 항목 | 역할 |
|---|---|
| `id`, `name`, `baseUrl`, `headers` | 식별자와 기본 주소, 기본 헤더 |
| `auth: ProviderAuth` | 키를 찾고 로그인하는 방법. `apiKey`, `oauth` 중 하나 이상이 필수다(주석: 로컬 서버처럼 키가 없는 provider도 `apiKey` 방식으로 "설정되었는지"를 알려 준다). |
| `getModels()` | 지금 아는 chat 모델 목록. 동기 함수이고 예외를 던지면 안 된다. |
| `getAllModels?()` | chat, image, classifier 모델 전체 |
| `refreshModels?()` | 동적 provider만: 저장된 목록을 복원하고 네트워크에서 새 목록을 가져온다. |
| `filterModels?()` | 인증 정보에 따라 쓸 수 있는 모델을 거른다. |
| `stream()`, `streamSimple()` | 정규화된 `TranscriptContext`를 받아 스트림을 돌려준다. |
| `fetchDeferred?`, `cancelDeferred?`, `generateImages?`, `classify?` | 선택 기능 |

`stream`이 `TranscriptContext`를 받는다는 점이 중요하다. `Models`가 호출자의 `Context`를 먼저 정규화한 뒤에 provider로 넘긴다(주석, `models.ts:201`).

### 2.2 실제 provider 두 개: OpenAI Codex와 Anthropic (`코드 확인`)
**OpenAI Codex** (`providers/openai-codex.ts`, 20줄)
```ts
export function openaiCodexProvider(): Provider<"openai-codex-responses"> {
  return createProvider({
    id: "openai-codex",
    name: "OpenAI Codex (legacy)",
    baseUrl: "https://chatgpt.com/backend-api",
    auth: { oauth: lazyOAuth({ name: "OpenAI (ChatGPT Plus/Pro)", isSubscription: true, load: loadOpenAICodexOAuth }) },
    models: Object.values(OPENAI_CODEX_MODELS),     // openai-codex.models.ts의 모델 목록
    api: openAICodexResponsesApi(),                  // Codex 전용 통신 코드 (api/openai-codex-responses.ts)
  });
}
```
- 인증은 `oauth`뿐이다. API 키 방식이 없고, ChatGPT Plus/Pro 구독으로 로그인해서 쓴다(`isSubscription: true`).
- 이름에 `(legacy)`가 붙어 있다. `CHANGELOG.md:70`에 "Renamed the OpenAI Codex provider to 'OpenAI Codex (legacy)'; Sign in with ChatGPT on the `openai` provider supersedes it."이라고 적혀 있다. 지금은 `openai` provider의 ChatGPT 로그인이 이를 대체한다.
- 현재 `openai` provider(`providers/openai.ts`)는 `apiKey`(`OPENAI_API_KEY` 환경변수)와 `oauth`(ChatGPT 구독) 두 방식을 모두 갖고, `api`는 `openAIResponsesApi()`(`openai-responses`)다. 같은 OpenAI라도 provider에 따라 쓰는 통신 방식(api)이 다르다.

**Anthropic** (`providers/anthropic.ts`, 90줄)
- 모양은 같다. 차이는 `auth`에 `apiKey`와 `oauth`(Claude Pro/Max 구독 로그인) 두 가지가 있고, `api`가 `anthropicMessagesApi()`라는 점이다.
- 키를 찾는 순서: 저장된 credential, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`, workload identity 순이다(`anthropic.ts:28-70`). 인증 상세는 04에서 다룬다.

정리하면 provider 하나는 **"주소 + 인증 방법 + 모델 목록 + 통신 코드"의 조합**이다. 01에서 본 "api(통신 방식)와 provider(회사/계정)는 별개 축"이 코드로는 `api:` 한 줄이 둘을 잇는 모양이다. 여러 provider가 한 api를 공유하는지는 `api/*.lazy.ts`를 쓰는 provider들을 비교해서 03에서 확인한다(`미확인`).

### 2.3 `api`는 지연 로딩이다
```ts
// api/anthropic-messages.lazy.ts
export const anthropicMessagesApi = (): ProviderStreams =>
  lazyApi(() => import("./anthropic-messages.ts"));
```
`anthropicMessagesApi()`는 통신 코드를 바로 읽지 않고, 첫 호출 때 `import()`로 불러온다(`api/lazy.ts`의 `lazyApi`, 주석: "The module loads on first stream call"). 내장 provider 42개를 등록해도 쓰지 않는 회사의 SDK는 불러오지 않는다. 이유는 코드에 직접 적혀 있지 않다. 번들 크기와 시작 시간 때문으로 보이며 이는 `추론`이다.

## 3. `createProvider()`: 부품으로 `Provider`를 만든다 (`models.ts:1034-1175`)
부품을 넘기면 호출 가능한 `Provider` 객체를 만들어 주는 함수다. 내장 provider와 사용자 정의 provider(`models.json`)가 모두 이 함수를 쓴다(`:1027` 주석). 아래에서 입력, 내부 동작, 반환값으로 나누어 설명한다.

### 3.1 입력: `CreateProviderOptions` (`:989-1024`)
| 항목 | 뜻 | 필수 |
|---|---|---|
| `id` | provider 이름표 (예: `"anthropic"`) | 필수 |
| `name` | 화면에 보일 이름. 없으면 `id`를 쓴다. | 선택 |
| `baseUrl`, `headers` | 기본 주소, 기본 헤더 | 선택 |
| `auth` | 키를 찾고 로그인하는 방법 | 필수 |
| `models` | 처음부터 아는 모델 목록 | 필수 |
| `api` | 채팅 호출을 실제로 수행하는 통신 코드 | 아래 참고 |
| `fetchModels` | 서버에서 최신 모델 목록을 받아 오는 함수 | 선택 |
| `filterModels`, `filterAllModels` | 인증 정보에 따라 쓸 수 있는 모델을 거르는 함수 | 선택 |
| `images`, `classifiers` | 이미지 생성, 분류 통신 코드 | 선택 |

`api`, `images`, `classifiers` 중 **하나는 반드시 있어야** 한다. 셋 다 없으면 에러를 던진다(`:1045-1047`).

**`api`에 넘기는 두 가지 형태**
- **통신 코드 하나**: 이 provider의 모든 모델이 같은 통신 방식을 쓸 때. 예: Claude는 `api: anthropicMessagesApi()`.
- **대응표**: "모델의 `api` 값이 X이면 통신 코드 X"를 적은 표. 예: `{ "anthropic-messages": ..., "openai-responses": ... }`.

### 3.2 왜 대응표가 필요한가: provider는 회사가 아니라 서비스다
통신 방식(`api`)은 **모델을 만든 회사가 정한 말투**다. Claude 모델은 Anthropic식, GPT 모델은 OpenAI식으로 요청해야 한다(README `:241`: "Anthropic models use `anthropic-messages`, OpenAI uses `openai-responses`").

대부분의 provider는 한 회사의 모델만 제공하므로 통신 코드가 하나면 된다. 그런데 **여러 회사의 모델을 한 계정으로 제공하는 서비스**가 있다. 이 경우 모델마다 통신 방식이 다르다.
- GitHub Copilot: `anthropic-messages`, `openai-completions`, `openai-responses` 세 가지 (`providers/github-copilot.ts:28-32`)
- OpenRouter: `anthropic-messages`, `openai-completions` (`openrouter.ts:28-31`)
- README는 "Mixed-API providers (GitHub Copilot, OpenCode Zen) dispatch per model"이라고 적었다(`:241`).

예를 들어 GitHub Copilot에서 Claude 모델을 부르면 `anthropic-messages` 통신 코드를, GPT 모델을 부르면 `openai-responses` 통신 코드를 호출한다. 어느 모델이 어느 방식인지는 모델 데이터(JSON)에 들어 있다. 2026-10-04에 생성한 데이터로 확인하면 GitHub Copilot은 Claude 10개가 `anthropic-messages`, Gemini 6개가 `openai-completions`, GPT 18개가 `openai-responses`로 묶여 있다(`실행 확인`, §6.8).

**왜 3개를 다 넣는가**: `createProvider()`는 앱 시작 때 한 번 부르는 준비 단계라서, 어떤 모델이 선택될지 아직 모른다. 한 번의 호출에는 통신 코드가 1개만 쓰이지만, 다음 호출에서 다른 모델을 고를 수 있으므로 그 provider의 모델들이 쓰는 통신 방식을 모두 넣어 둔다. 하나만 넣으면 다른 방식의 모델을 골랐을 때 에러가 난다. 통신 코드는 지연 로딩이라 실제로 호출되기 전에는 읽히지 않아서 여러 개를 넣어도 낭비가 아니다.

### 3.3 내부 동작
1. **입력 검사** (`:1045`): `api`, `images`, `classifiers`가 모두 비어 있으면 에러를 던진다.
2. **`api` 형태 구분** (`:1035-1039`): 통신 코드 하나인지 대응표인지 판단한다. 기준은 넘어온 값에 `stream` 함수가 있는지다.
3. **모델 목록 준비** (`:1049-1062`):
   - 넘겨받은 `models`를 "기본 목록"으로 기억하고, 서버에서 받은 최신 목록은 "동적 목록"이라는 별도 변수에 둔다(처음에는 비어 있음).
   - 목록 요청이 오면 기본 목록에 동적 목록을 합쳐서 돌려준다. `type`과 `id`가 같은 모델은 동적 목록의 것으로 바꾸고, 없던 모델은 추가한다.
4. **모델에 맞는 통신 코드 고르기** (`:1063`): `api`가 하나면 그것을 쓰고, 대응표면 `model.api` 값으로 표에서 찾는다.
5. **호출 전달** (`:1065-1076`): 호출이 오면 4번으로 통신 코드를 찾아 호출한다. 표에 없는 `api`면 "Provider X has no API implementation for ..." 에러를 `error` 이벤트로 낸다.
6. **`Provider` 객체 조립** (`:1078-1119`):
   - `id`, `name`, `baseUrl`, `headers`, `auth`는 받은 값 그대로 넣는다.
   - `getModels()`는 3번의 합친 목록에서 채팅 모델만 돌려준다.
   - `refreshModels`는 `fetchModels`가 있을 때만 만든다. 순서는 저장된 목록 복원, 서버에서 받기, 알 수 없는 종류 제거, 저장하고 동적 목록 교체다.
   - `stream()`, `streamSimple()`은 5번의 호출 전달로 만든다.
7. **선택 기능 추가** (`:1121-1172`): 비동기 응답(`fetchDeferred`, `cancelDeferred`), 이미지 생성(`generateImages`), 분류(`classify`)는 해당 구현이 있을 때만 붙인다.

### 3.4 반환값: `Provider<TApi>` (`:1174`)
```
Provider {
  id, name, baseUrl, headers, auth        ← 받은 값 그대로
  getModels()                             ← 모델 목록 (기본 + 동적)
  getAllModels()                          ← 이미지, 분류 모델까지 포함
  refreshModels()   (fetchModels를 줬을 때만)
  filterModels(), filterAllModels()       ← 받은 함수 그대로
  stream(model, context, options)         ← 2층: model.api로 통신 코드를 고르고, 그 통신 코드의 stream을 호출
  streamSimple(model, context, options)   ← 위와 같음 (통신 코드의 streamSimple을 호출)
  fetchDeferred, cancelDeferred, generateImages, classify   ← 구현이 있을 때만
}
```

### 3.5 한 줄 요약
입력은 부품(이름, 인증, 모델 목록, 통신 코드), 내부 동작은 조립, 반환값은 호출 가능한 `Provider` 객체다. 채팅 호출에서 핵심은 `stream()`이 **모델의 `api` 값을 보고 맞는 통신 코드를 호출한다**는 점이다.

## 4. `Models`: 레지스트리와 호출 입구

### 4.1 모델 조회 (동기)
| 함수 | 동작 | 위치 |
|---|---|---|
| `getProviders()`, `getProvider(id)` | 등록된 provider 조회 | `:416-422` |
| `getModels(provider?)` | 알려진 chat 모델 목록. provider의 `getModels()`가 예외를 던지면 빈 목록으로 처리한다. | `:424-444` |
| `getModel(provider, id)` | `getModels(provider)`에서 `id`가 같은 모델을 찾는다. 없으면 `undefined`. | `:472-474` |
| `getModelsOfType`, `getAllModels` | image, classifier까지 | `:446-478` |

`getModel`은 네트워크 없이 메모리에서 찾는다. 반환 타입이 `Model<Api> | undefined`이므로, 특정 api로 좁히려면 `hasApi(model, "anthropic-messages")` 가드를 쓴다(`:1189`).

### 4.2 "쓸 수 있는 모델": `getAvailable()` (`:696-706`)
`getModels()`는 전체 목록이고, `getAvailable()`은 **인증이 설정된 provider의 모델만** 돌려준다. 각 provider의 인증이 완전한지 `checkAuth`로 확인하고(OAuth 갱신은 하지 않는다), 통과한 provider의 `getModels()`에 `filterModels`를 적용한다. 모델 선택 화면에서 "내가 키가 있는 모델만" 보여 줄 때 쓰는 용도로 보인다(`추론`).

### 4.3 호출 입구: `stream*`, `complete*` (`:871-910`)
`models.stream(...)`을 부르면 `Models` 안에서 일어나는 일을 순서대로 적은 것이다. 번호는 아래 코드의 ①~⑤와 같다.

| 번호 | 하는 일 | 쉬운 설명 |
|---|---|---|
| ① | `normalizeContext(context)` | 보낼 대화를 내부용 모양(`TranscriptContext`)으로 바꾼다. 지침과 도구를 맨 앞 시스템 메시지에 합친다. |
| ② | `lazyStream(...)` | 빈 스트림을 먼저 돌려주고, ③~⑤는 뒤에서 진행한다. |
| ③ | `requireChatProvider(model)` | `model.provider` 이름으로 `Provider`를 찾는다. 없으면 에러. |
| ④ | `applyAuth(model, options)` | 인증과 헤더를 확정한다(§4.4). |
| ⑤ | `provider.stream(...)` | 찾은 `Provider`의 `stream`을 호출해서 실제 통신을 시작한다(§1.2의 2층). |

즉 `Models.stream`은 준비 단계(변환, 빈 스트림, provider 찾기, 인증)를 거친 뒤 `Provider`에게 넘기는 역할이고, 실제 통신은 하지 않는다.

01에서 정리한 4개 함수다.
```ts
stream(model, context, options) {
  const transcript = normalizeContext(context);              // Context → TranscriptContext
  return lazyStream(model, async () => {                      // 빈 스트림을 먼저 돌려주고 뒤에서 준비
    const provider = this.requireChatProvider(model);         // model.provider로 provider 찾기
    const { requestModel, requestOptions } = await this.applyAuth(model, options);
    return provider.stream(requestModel, transcript, requestOptions);
  });
}
complete(...) { return this.stream(...).result(); }
```
`streamSimple`/`completeSimple`도 같은 모양이고 `provider.streamSimple`을 부른다.

### 4.4 `applyAuth`: 호출 직전에 요청을 완성한다 (`:837-869`)
```
1. provider가 등록돼 있는지 확인 (없으면 ModelsError "provider")
2. getAuth(model, { apiKey, env, signal }) 로 인증 결과를 얻음
     └ 설정이 없으면 ModelsError "auth": "Provider is not configured: ..."
3. 요청 옵션을 합침
     apiKey   : options.apiKey가 있으면 그것, 없으면 인증 결과의 apiKey
     headers  : 인증 결과의 헤더 → options.headers로 덮어쓰기 → transformHeaders(마지막)
     env      : 인증 결과의 env + options.env
     baseUrl  : 인증 결과가 baseUrl을 주면 모델의 baseUrl을 교체
4. { requestModel, requestOptions } 반환
```
- 호출자가 직접 준 옵션이 인증 결과보다 우선한다("Explicit request options win per-field").
- `transformHeaders`는 `Models` 전용 옵션으로, 헤더가 모두 합쳐진 뒤 마지막에 한 번 바꿀 수 있다(`:106-109`). provider로 넘어가기 전에 제거된다(`:864`).
- `getAuth(model)`은 모델에 `headers`가 있으면 인증 헤더와 합친다(`:746-753`).
- 인증 실패는 예외로 호출자에게 던져지는 것이 아니라 `lazyStream` 안에서 잡혀 `error` 이벤트가 된다. `getAuth` 주석에도 "Request paths surface rejections as stream errors"라고 적혀 있다(`:299`). 앞서 정리한 "인증은 호출 직후 뒤에서 확인한다"가 이 코드다.

### 4.5 `ModelsError` 코드
코드 안에서 확인한 값은 `"provider"`(provider 없음/미지원), `"auth"`(인증 설정 또는 저장소 실패), `"oauth"`(토큰 갱신 실패), `"stream"`(api 구현 없음), `"model_source"`(목록 갱신 실패)이다(`models.ts`의 `new ModelsError(...)`). 정의 파일 `utils/models-error.ts`는 읽지 않았다(`미확인`).

### 4.6 image와 classifier 호출은 규칙이 다르다 (`:948-982`)
`generateImages`, `classify`는 **예외를 던지지 않고** 에러가 담긴 결과 객체를 돌려준다(`imageErrorResult`, `classifierErrorResult`). chat의 "에러도 스트림 이벤트로"와 같은 철학이다.

## 5. 모델 목록 갱신: `refresh()` (`:546-606`)
동적 provider의 목록을 최신으로 만드는 흐름이다. 정적 provider는 건너뛴다.

```
각 동적 provider마다 (병렬)
 1. 저장된 credential 읽기
 2. [오프라인] 저장소(ModelsStore)에 있던 목록을 복원해서 반영      ← 네트워크 없이도 목록을 쓸 수 있게
 3. allowNetwork가 false이면 여기서 끝
 4. 갱신용 credential 확정 (OAuth 만료 시 갱신, API 키는 resolve)
 5. [온라인] provider.refreshModels() → 서버에서 새 목록 받기
 6. publish(): 저장소에 쓰고, 메모리 목록을 교체
```
- **세대(generation) 검사** (`:480-525`): `refresh`를 다시 부르거나 provider를 교체하면 이전 갱신이 진행 중이라도 취소하고, 오래된 결과는 버린다. 늦게 끝난 오래된 요청이 새 결과를 덮어쓰는 것을 막는다.
- **저장소** (`models-store.ts`): `ModelsStore`는 `read`, `write`, `delete` 세 개뿐인 인터페이스다. 기본 구현은 메모리(`InMemoryModelsStore`). `coding-agent`가 `createModels({ credentials, modelsStore })`로 파일 기반 저장소를 넣는다(`model-runtime.ts:211`, 저장소 종류는 Q4 기록, 이 commit에서는 `미확인`). 저장하는 항목은 `models`, `lastModified`, `checkedAt`, `etag`로, HTTP 조건부 요청(`If-None-Match`)에 쓰는 값들이다(`:3-15`).
- 개별 provider의 실패는 `errors` 맵에 담아 돌려주고 전체를 reject하지 않는다(`:582-590`, `:605`).

## 6. 모델 데이터는 어디서 오나

`scripts/generate-models.ts`(3680줄)를 읽고 정리했다. 스크립트는 실행하지 않았다(외부 네트워크 접근이 필요하고 레포 규칙상 빌드류 명령은 요청이 있을 때만 실행하기 때문이다). 모든 내용은 `코드 확인`이다.

### 6.1 한 줄 요약
모델 정보(가격, 컨텍스트 크기 등)는 사람이 직접 쓰지 않는다. **빌드할 때 스크립트가 외부 사이트에서 내려받아 JSON 파일로 저장하고, 앱은 실행 중에 그 JSON만 읽는다.**

### 6.2 전체 흐름 (Claude 모델 기준)
```
[빌드할 때]  npm run generate-models   (= node scripts/generate-models.ts --strict)

 ① 외부에서 모델 정보를 내려받는다
      models.dev/api.json  → Anthropic, OpenAI, Google 등 대부분의 provider   (generate-models.ts:1759)
      OpenRouter, Vercel AI Gateway, NVIDIA, Radius → 각 서비스의 자체 목록    (:1300, :1350, :1280, :1329)

 ② pi의 Model 형식으로 바꾼다
      Claude 예시 (:1808-1832): models.dev의 anthropic 항목 중 tool_call이 true인 것만 가져와서
        id, name, api: "anthropic-messages", baseUrl: "https://api.anthropic.com",
        reasoning, input(text/image), cost, contextWindow, maxTokens 를 채운다.

 ③ 보정한다
      모델별 규칙으로 compat, 추론 수준 매핑(thinkingLevelMap), 프롬프트 캐시 정보 등을 채우는
      apply...Metadata 함수들이 있다 (예: :807-1030). 외부 사이트에 없는 값을 소스 코드의 규칙으로 보충한다.
      models.dev에 아직 없는 모델은 스크립트가 직접 추가한다
      (예: claude-opus-5-5, claude-sonnet-5-5, 주석 "until models.dev includes it", :2775-2800).

 ④ 저장한다
      src/providers/data/<provider>.json              ← 모델 값 본문 (git에서 제외)
      src/providers/<provider>.models.ts              ← JSON을 코드에서 쓸 수 있게 감싸는 파일 (git에 포함)
      src/models.generated.ts                         ← 모든 *.models.ts를 모은 파일 (git에 포함)

[앱 실행 중]
      <provider>.models.ts가 JSON을 읽어서 만든 목록이 Provider의 models가 된다.
      이때는 스크립트를 실행하지 않고, 네트워크도 쓰지 않는다.
```
- `package.json`의 `"build": "npm run generate-models && npm run build:offline"`처럼 빌드 명령이 스크립트를 먼저 실행한다.
- 그래서 앱을 쓰는 사람이 새 모델 정보를 받으려면 새로 빌드된 버전을 받아야 한다.

### 6.3 파일 세 가지 구분
| 파일 | 내용 | git |
|---|---|---|
| `data/<provider>.json` | 모델 값 본문 (가격, 한도, compat 등) | 제외 (`.gitignore` 11번째 줄) |
| `<provider>.models.ts` | JSON을 import해서 `ANTHROPIC_MODELS` 같은 객체로 만드는 코드 | 포함 |
| `models.generated.ts` | 모든 `*.models.ts`를 모아 `MODELS`, `IMAGE_MODELS`, `CLASSIFIER_MODELS`로 내보냄 | 포함 |

`.models.ts`의 `flattenChatModelCatalog`(`model-catalog.ts:62`)가 JSON 안의 모델 중 `type === "chat"`인 것만 골라 `{ id: Model }` 객체로 만든다. 이 객체가 `providers/anthropic.ts`의 `models: Object.values(ANTHROPIC_MODELS)`로 들어간다.

### 6.4 JSON의 모양: api별로 묶는다 (`generate-models.ts:3502-3515`)
```
data/anthropic.json = {
  "anthropic-messages": {                     ← 통신 방식(api)별로 묶고
    "chat:claude-...": { ...Model... },       ← 그 안에 "종류:모델id" → 모델 명세
    ...
  }
}
```
한 provider 안에 통신 방식이 여러 개인 경우(§3.2의 GitHub Copilot 등)에는 api마다 묶음이 따로 생긴다. 각 모델이 어느 `api`를 쓰는지는 이 JSON에 들어 있고, 같은 provider에서 id가 겹치면 에러를 낸다.

### 6.5 실행 옵션 (`:49-95`)
| 명령 (`package.json`) | 옵션 | 하는 일 |
|---|---|---|
| `generate-models` | `--strict` | JSON, `.models.ts`, `models.generated.ts`를 모두 새로 만든다. |
| `hydrate-model-data` | `--strict --data-only` | **JSON만** 다시 만든다. `.models.ts`와 `models.generated.ts`는 건드리지 않는다(`:3536-3560`의 `if (!dataOnly)`). 이 checkout처럼 JSON이 없는 상태를 채울 때 쓴다. |
| `generate-model-catalog` | `--strict --json-only --json-output <폴더>` | 지정한 폴더에 JSON 카탈로그만 만든다. |

- `--strict`는 외부 목록을 하나라도 못 받으면 건너뛰지 않고 실패하게 한다(`:1294`, `:1324`, `:1339` 등의 `if (generatorOptions.strict) throw error`).
- 저장은 임시 폴더에 먼저 만들어 검증한 뒤 교체한다. 실패하면 이전 데이터를 복원한다(`:3512-3535`, `:3620-3630`).

### 6.6 실제로 실행해 본 결과 (`실행 확인`)
처음에는 이 checkout에 `data/*.json`이 없었다. 사용자의 허락을 받고 `packages/ai`에서 다음을 실행했다.
```
node scripts/generate-models.ts --strict --data-only        # npm run hydrate-model-data 와 같은 명령
```
- `node_modules` 없이도 실행되었다(스크립트가 Node 내장 모듈과 레포 안의 파일만 쓰기 때문, 종료 코드 0).
- `src/providers/data/`에 JSON 42개와 `.manifest.json`이 생겼다. `generatedAt`은 `2026-10-04T14:12:07Z`다.
- `data/`는 `.gitignore` 대상이라 `git status`는 그대로 clean이다. `.models.ts`와 `models.generated.ts`는 `--data-only`라서 바뀌지 않았다.
- 실행 로그는 `artifacts/pi/hydrate-model-data.2026-10-04.log`에 보관했다. 로그에는 provider별 모델 수가 나온다(예: github-copilot 34, openrouter 400 + 이미지 59 + 분류 13, vercel-ai-gateway 253, openai-codex 9, azure-openai-responses 44).
- **주의**: 이 데이터는 commit이 아니라 **실행한 시점의 외부 사이트(models.dev 등) 기준**이다. 같은 commit이라도 다른 날 실행하면 모델 수와 가격이 달라질 수 있다. 문서에 인용하는 값에는 이 시점이 붙는다.

### 6.7 실행 중에 최신 모델을 받는 방법과의 차이
| | 빌드 때 생성 (이 절) | 실행 중 갱신 (§5 `refresh`) |
|---|---|---|
| 시점 | 개발자가 빌드할 때 | 앱이 실행되는 동안 |
| 쓰는 provider | 내장 provider 대부분 | `fetchModels`를 구현한 일부 provider (`radius` 등) |
| 결과물 | `data/*.json`, `*.models.ts` | 메모리 목록 + `ModelsStore` 저장소 |

Radius는 두 방식을 모두 쓴다. 스크립트가 빌드 때 공개 목록을 받아 JSON에 넣고(`:1329`, 주석: "authenticated clients overlay it at runtime"), 실행 중에는 인증된 사용자의 목록으로 덮어쓴다.

### 6.8 실제 모델 한 건: Claude Opus 5.5 (`data/anthropic.json`, 2026-10-04 생성, `실행 확인`)
`data/anthropic.json`에는 `anthropic-messages` 묶음 하나만 있고, 그 안에 Claude 모델 16개가 있다. 그중 한 건이다.

```json
{
  "id": "claude-opus-5-5", "name": "Claude Opus 5.5",
  "api": "anthropic-messages", "provider": "anthropic", "baseUrl": "https://api.anthropic.com",
  "reasoning": true, "input": ["text", "image"],
  "cost": { "input": 4, "output": 20, "cacheRead": 0.2, "cacheWrite": 5 },
  "contextWindow": 1000000, "maxTokens": 128000,
  "thinkingLevelMap": { "off": null, "minimal": null, "low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "max" },
  "compat": { "supportsMidConvoEffort": true, "supportsMidConvoSystemMessages": true, "supportsMidConvoToolChanges": true,
              "forceAdaptiveThinking": true, "supportsTemperature": false, "supportsStrictTools": true },
  "promptCache": { "short": 300, "long": 3600 },
  "inputLimits": { "maxRequestBytes": 33554432, "images": { "maxPerRequest": 600, "resize": { "maxWidth": 2000, "maxHeight": 2000, "maxBytes": 4718592, "jpegQuality": 80 } } },
  "type": "chat"
}
```

| 필드 | 값의 뜻 | 01에서 본 타입 |
|---|---|---|
| `api`, `provider`, `baseUrl` | 통신 방식, 소속 provider, 주소 | `BaseModel` (`types.ts:1097`) |
| `cost` | 100만 토큰당 달러. 입력 4, 출력 20, 캐시 읽기 0.2, 캐시 쓰기 5 | `ModelCost` |
| `contextWindow`, `maxTokens` | 입력 컨텍스트 한도 100만 토큰, 한 번에 낼 수 있는 출력 최대 12.8만 토큰 | `Model` |
| `thinkingLevelMap` | pi의 추론 수준을 이 모델의 값으로 바꾸는 표. `off`와 `minimal`이 `null`이므로 이 모델은 추론을 끌 수 없고 `minimal`도 없다. | `ThinkingLevelMap` |
| `compat.supportsTemperature: false` | 이 모델은 `temperature` 값을 거부하므로 보내지 않는다. `types.ts:922-926` 주석의 "Opus 4.7+는 거부한다"와 일치한다. | `AnthropicMessagesCompat` |
| `compat.forceAdaptiveThinking: true` | 모델 id와 상관없이 `adaptive` 추론 형식을 쓴다. | 〃 |
| `compat.supportsMidConvo*` | 대화 중간 시스템 메시지, 도구 추가/제거, effort 변경을 지원한다. 01에서 본 `SystemMessage`의 중간 변경 기능이 이 모델에서 켜진다는 뜻이다. | 〃 |
| `promptCache` | 프롬프트 캐시 유지 시간(초). `short` 300초, `long` 3600초 | `ModelPromptCache` |
| `inputLimits` | 요청 크기 한도 32MB, 요청당 이미지 최대 600장, 이미지는 2000x2000 이내와 약 4.5MB로 줄여서 보낸다. | `ModelInputLimits` |

이 모델은 스크립트가 직접 추가한 모델이다(§6.2 ③, `generate-models.ts:2775-2800`). 스크립트 안에 하드코딩된 값(id, 이름, 가격, 한도, `thinkingLevelMap`)은 JSON과 같고, 거기에 없던 `compat`, `promptCache`, `inputLimits`는 보정 단계에서 붙은 값이다(코드의 해당 블록과 JSON을 비교해서 확인, 어느 함수가 붙였는지는 `미확인`).

**GitHub Copilot의 `api` 묶음** (`data/github-copilot.json`)
| `api` | 개수 | 모델 예 |
|---|---|---|
| `anthropic-messages` | 10 | claude-fable-5, claude-haiku-4.5, claude-opus-4.7 |
| `openai-completions` | 6 | gemini-3.5-flash, gemini-3.6-flash |
| `openai-responses` | 18 | gpt-5-mini, gpt-5.4 |

같은 provider 안에서 모델 계열에 따라 `api`가 나뉜다. §3.2의 "여러 통신 코드를 대응표로 받는 이유"가 데이터로 확인되었다. 참고로 `openai` provider는 44개 모두 `openai-responses`, `openai-codex`는 9개 모두 `openai-codex-responses`다.

## 7. 호출과 무관하게 `models.ts`에 같이 있는 함수

| 함수 | 역할 | 위치 |
|---|---|---|
| `calculateCost(model, usage)` | 토큰 수와 모델 가격으로 `usage.cost`를 채운다. 입력 토큰 구간별 가격(`tiers`) 중 가장 높게 맞는 것을 요청 전체에 적용한다. Anthropic 1시간 캐시 쓰기는 입력 가격의 2배로 계산한다. 이 함수는 `Models`가 부르지 않고, 각 통신 코드(`api/*.ts`)가 응답에서 토큰 수를 받은 직후에 부른다(예: `anthropic-messages.ts:690, 859`). | `:1193-1213` |
| `getSupportedThinkingLevels(model)` | 이 모델이 지원하는 추론 수준 목록. `reasoning`이 false면 `["off"]`. `thinkingLevelMap`에서 `null`인 수준은 제외하고, `xhigh`, `max`는 명시된 경우만 포함한다. | `:1217-1226` |
| `clampThinkingLevel(model, level)` | 요청한 수준을 지원하지 않으면 가까운 지원 수준으로 맞춘다. 같거나 높은 쪽을 먼저 찾고, 없으면 낮은 쪽을 찾는다. | `:1228-1247` |
| `hasApi(model, api)` | `model.api`가 맞는지 확인하며 타입을 좁힌다. | `:1189` |
| `modelsAreEqual(a, b)` | type, id, provider가 같으면 같은 모델로 본다. | `:1253-1256` |

`calculateCost`의 계산 규칙(Anthropic 2배 등)이 공용 `models.ts` 안에 있는 것은 눈에 띄는 점이다. 이유는 `추론`이지만, 비용 계산을 `Usage`를 채우는 단계 한 곳에서 처리하려는 것으로 보인다.

## 8. 설계 포인트
1. **`Models`는 호출을 직접 처리하지 않고 위임한다.** 인증과 헤더 조립(`applyAuth`)만 하고, 실제 호출은 `provider.stream`에 넘긴다. 주석도 "Providers own request behavior; `Models` resolves auth and delegates"라고 적고 있다(`:235-239`).
2. **provider는 조립식 부품이다.** `createProvider({ id, auth, models, api })`로 만들고, 내장 provider와 사용자 정의 provider(`models.json`)가 같은 경로를 쓴다(`:1027` 주석). 새 회사를 붙일 때 통신 코드를 새로 만들 필요 없이 기존 `api`를 재사용할 수 있다.
3. **지연 로딩 + 즉시 반환.** 통신 코드는 첫 호출 때 불러오고, 호출 함수는 빈 스트림을 먼저 돌려준다(`lazyApi`, `lazyStream`).
4. **오프라인 우선 모델 목록.** `refresh`는 저장된 목록을 먼저 복원하고(네트워크 없이), 그다음 네트워크로 갱신한다. 세대 번호로 오래된 갱신 결과를 버린다.
5. **실패를 값으로 돌려준다.** chat은 `error` 이벤트, image와 classifier는 에러가 담긴 결과 객체, `refresh`는 `errors` 맵이다.

## 9. 이전 분석(Q4)과의 대조
- Q4의 "`createProvider` models.ts:1028", "`calculateCost` models.ts:1187", "`Models.refresh` :545"는 이 commit에서 각각 `:1034`, `:1193`, `:546`이다. 내용은 같고 줄만 이동했다.
- Q4의 "레포 안에서 런타임 카탈로그를 쓰는 provider는 `radius.ts`뿐"은 ai 패키지 안에서는 맞다. 다만 `coding-agent`에도 `refreshModels`를 쓰는 곳이 더 있다(`remote-catalog-provider.ts`, `extensions/llama/provider.ts`).

## 10. 남은 질문 (다음 문서로)
- `api/anthropic-messages.ts`: 요청을 어떻게 만들고, Anthropic의 raw 이벤트를 어떻게 `AssistantMessageEvent`로 바꾸는가? → 03
- `streamSimple`의 `reasoning`은 provider별 설정으로 어떻게 바뀌는가? → 03
- `openai-completions.ts`의 compat 자동 감지는 실제로 어떻게 동작하는가? → 03
- `envApiKeyAuth`, `lazyOAuth`, `getAuth`가 돌려주는 `AuthResult`의 구조, OAuth 갱신의 락 → 04
- 모델 JSON 한 건의 실제 모양 → 필요하면 `hydrate-model-data` 실행 후 확인(사용자 허락 필요)
