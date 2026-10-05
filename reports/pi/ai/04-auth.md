# ai 04: 인증 — 키와 토큰은 어디서 와서 어떻게 요청에 붙는가

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **보충 문서**: [04-01-auth-env-and-storage](./04-01-auth-env-and-storage.md) (환경변수 이름과 위치, 로그인 저장 경로)
- **선행 문서**: [02-models-registry](./02-models-registry.md) §4.4(`applyAuth`), [03-1-api-anthropic](./03-1-api-anthropic.md) §4.2(`createClient`), [03-4-api-openai-codex-legacy](./03-4-api-openai-codex-legacy.md) §4.1
- **읽은 파일**: `auth/types.ts`(250줄 전체), `auth/resolve.ts`(188줄 전체), `auth/helpers.ts`, `auth/credential-store.ts`, `auth/context.ts`, `env-api-keys.ts`(195줄 전체), `auth/oauth/anthropic.ts`(298줄 전체), `auth/oauth/openai-codex.ts`(435줄 전체), `auth/oauth/callback-server.ts`(183줄 전체), `auth/oauth/pkce.ts`, `auth/oauth/load.ts`, `auth/oauth/openai-chatgpt.ts`(앞부분과 `toAuth`), `auth/oauth/device-code.ts`(앞부분), `providers/anthropic.ts`의 `anthropicApiKeyAuth`, `models.ts`의 `getAuth`, `login`, `applyAuth`(02에서 읽음). `coding-agent/src/core/auth-storage.ts`는 구조만 `grep`으로 봤다. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 인증 해석과 OAuth 갱신 락은 실제 코드를 불러서 가짜 provider로 돌려 확인했다(`실행 확인`, §7). **실제 로그인(브라우저 인증)과 실제 서버와의 토큰 교환은 하지 않았다**(`미확인`). 외부 서비스 접속과 계정 로그인이 필요해서 허락 없이 하지 않는다.

## 0. 이 문서의 질문
03에서 통신 코드는 `options.apiKey`와 `options.headers`를 받아서 서버에 보냈다(Claude는 API 키 또는 OAuth 토큰, Codex는 OAuth JWT). 그 값이 **어디서 오는가**를 본다.

1. 호출 때마다 "어떤 키를 쓸지"는 어떤 순서로 정해지는가?
2. 저장된 로그인 정보는 어디에 있고, 만료되면 어떻게 되는가?
3. 브라우저 로그인(OAuth)은 어떻게 동작하는가?
4. 여러 호출이 동시에 만료된 토큰을 만나면 어떻게 되는가?

## 1. 용어 정리
| 용어 | 뜻 |
|---|---|
| **API 키** | 서비스가 발급한 비밀 문자열. 요청마다 붙여 보낸다. 만료되지 않는다. |
| **OAuth 토큰** | 브라우저 로그인으로 받는 임시 열쇠. 두 가지가 한 쌍이다: `access`(요청에 쓰는 토큰, 곧 만료됨)와 `refresh`(새 `access`를 받아 오는 데 쓰는 토큰). |
| **credential(자격 증명)** | 저장해 둔 로그인 정보. API 키 또는 OAuth 토큰 쌍 |
| **구독 로그인** | ChatGPT Plus/Pro, Claude Pro/Max 같은 **구독 계정**으로 로그인하는 것. API 키 없이 구독 한도 안에서 쓴다. |

## 2. 한눈에 보는 구조
```
호출  models.streamSimple(model, context, options)
  └ applyAuth(model, options)                               (02 §4.4, models.ts:837)
       └ getAuth(model, { apiKey, env, signal })            (models.ts:737)
            └ resolveProviderAuth(provider, credentials, authContext, overrides)   (auth/resolve.ts:33)
                 ① 호출 옵션 apiKey          ← 가장 우선
                 ② 저장된 credential         ← OAuth 또는 API 키
                 ③ 환경변수 등 주변 설정      ← ②가 없을 때만
            → AuthResult { auth: { apiKey, headers, baseUrl }, env, source }
       └ 요청 옵션에 합침 (호출자가 직접 준 값이 우선)
  └ provider.streamSimple(requestModel, transcript, requestOptions)   → 03의 통신 코드가 받음
```
인증은 **"provider별 인증 방법"**(`ProviderAuth`)을 정의하고, **"저장소"**(`CredentialStore`)에서 저장된 값을 읽고, **"환경"**(`AuthContext`)에서 환경변수를 읽어 한 번의 `AuthResult`로 합치는 구조다.

## 3. 타입 (`auth/types.ts`)

### 3.1 결과: `ModelAuth`와 `AuthResult` (`:4-11`, `:103-110`)
```ts
interface ModelAuth {                // :7-11    요청 하나에 쓸 인증
    apiKey?: string;                 //   키 또는 토큰
    headers?: ProviderHeaders;       //   인증 헤더 (예: Authorization: Bearer ...)
    baseUrl?: string;                //   계정에 따라 주소가 달라지는 경우
}

interface AuthResult {               // :104-110  getAuth()가 돌려주는 결과
    auth: ModelAuth;                 //   ← 위의 ModelAuth가 이 안에 들어 있다 (포함 관계)
    env?: ProviderEnv;               //   provider 전용 설정값 (예: Cloudflare 계정 ID)
    source?: string;                 //   출처 라벨 ("ANTHROPIC_API_KEY", "OAuth", "stored credential")
}
```
**`ModelAuth`는 "서버에 보낼 열쇠"이고, `AuthResult`는 "그 열쇠 + 부가 정보(설정값, 출처)가 든 봉투"다.**
| | `ModelAuth` | `AuthResult` |
|---|---|---|
| 한 줄 | 요청에 붙일 **인증 값** | 인증 값 + **설정값(`env`) + 출처 표시(`source`)** |
| 용도 | 서버에 실제로 보낼 것 | 호출 준비와 상태 화면에 쓸 것 |
| 누가 만드나 | OAuth의 `toAuth(credential)`가 돌려줌 (`types.ts:239`) | `resolveProviderAuth`와 `ApiKeyAuth.resolve`가 돌려줌 (`types.ts:194-198`) |

주석(`:4-6`)이 나눈 기준을 말해 준다: "요청 인증은 `apiKey`, `headers`, `baseUrl` 중 하나로 표현할 수 있어야 하고, 표현할 수 없는 값은 인증이 아니라 provider 설정이다." 그래서 **요청 인증**은 `ModelAuth`에, **provider 설정값**(`env`)과 **출처**(`source`)는 바깥의 `AuthResult`에 둔 구조로 읽힌다(이 구분의 의도는 주석에서 읽은 해석).

**어디서 어떻게 쓰이나** (`코드 확인`)
1. **OAuth는 `ModelAuth`를 만들고 `resolve.ts`가 `AuthResult`로 감싼다.**
   ```ts
   // auth/resolve.ts:157-158
   return { auth: await oauth.toAuth(credential), source: "OAuth" };
   //        ↑ ModelAuth ({ apiKey: access 토큰 })         ↑ 출처 라벨을 붙여서 AuthResult로
   ```
   `toAuth`는 인증 값만 만들고(`{ apiKey: credential.access }`), 출처 `"OAuth"`는 `resolve.ts`가 붙인다.
2. **API 키 방식은 처음부터 `AuthResult`를 만든다.**
   ```ts
   // auth/helpers.ts:21, :26  (envApiKeyAuth)
   return { auth: { apiKey: credential.key }, env: credential.env, source: "stored credential" };
   return { auth: { apiKey: value },                                 source: envVar };          // 예: "OPENAI_API_KEY"
   ```
3. **`env`나 `headers`가 필요한 예** (`providers/anthropic.ts`)
   ```ts
   // workload identity federation: 키는 없고 설정값만 있다                              (:69)
   return { auth: {}, env: federation, source: "workload identity federation" };
   // ANTHROPIC_AUTH_TOKEN: 키가 아니라 헤더로 나간다                                      (:36-40)
   return { auth: { headers: { Authorization: `Bearer ${authToken}` } }, source: "ANTHROPIC_AUTH_TOKEN" };
   ```
4. **`applyAuth`가 두 부분을 나눠서 쓴다** (`models.ts:856-863`)
   ```ts
   const auth = resolution.auth;                                   // ModelAuth → 요청에 들어가는 값
   const apiKey = options?.apiKey ?? auth.apiKey;
   let headers = mergeHeaders(auth.headers, options?.headers);
   const env = resolution.env || options?.env ? {...} : undefined; // AuthResult.env → 요청 옵션의 env
   const requestModel = auth.baseUrl ? { ...model, baseUrl: auth.baseUrl } : model;
   ```
   `ModelAuth`의 `apiKey`, `headers`, `baseUrl`은 요청 옵션과 모델 주소에 합쳐지고, `AuthResult.env`는 요청 옵션의 `env`로 전달된다. **`source`는 요청에 쓰이지 않는다.** 인증 상태를 보여 주는 화면용 라벨이다(`checkProviderAuth`가 `source: resolution.source`로 돌려줌, `models.ts:668`).

### 3.2 저장된 값: `Credential` (`:17-37`)
| 타입 | 모양 | 설명 |
|---|---|---|
| `ApiKeyCredential` | `{ type: "api_key", key?, env? }` | 저장된 API 키와 provider 설정 |
| `OAuthCredential` | `{ type: "oauth", refresh, access, expires, ... }` | OAuth 토큰 쌍과 만료 시각(밀리초). `[key: string]: unknown`이라 provider별 추가 필드를 담는다(예: Codex의 `accountId`, `openai-codex.ts:323-329`) |

### 3.3 저장소: `CredentialStore` (`:65-94`)
**로그인 정보(API 키나 OAuth 토큰)를 저장하고 꺼내는 "보관함"의 규칙**이다. 규칙(인터페이스)만 정해 두고 저장 위치는 앱이 정한다.

**무엇을 보관하나**: provider id를 키로 **provider당 credential 하나**를 보관한다(§3.2의 두 모양 중 하나).
```
보관함
 ├ "anthropic" → { type: "oauth", access: "...", refresh: "...", expires: 1759... }
 ├ "openai"    → { type: "api_key", key: "sk-..." }
 └ "google"    → { type: "api_key", key: "..." }
```
이 예시는 모양을 보이려는 것이고 실제 저장 내용이 아니다.

**메서드 네 개**
| 메서드 | 하는 일 |
|---|---|
| `read(providerId)` | 저장된 credential을 읽는다. 없으면 `undefined`. 만료된 것도 그대로 준다(표시용). |
| `list()` | 비밀 값 없이 `{ providerId, type }` 목록만 준다. 구현은 설정된 명령을 실행해서는 안 된다(주석). |
| **`modify(providerId, fn)`** | **유일한 쓰기 방법.** `fn`이 현재 값을 받아 새 값을 돌려주면 그 값으로 저장한다. `undefined`를 돌려주면 변경 없음. |
| `delete(providerId)` | 삭제(로그아웃) |

**쓰기가 `modify` 하나뿐인 이유**
```ts
await credentials.modify("anthropic", async (current) => {
    // current = 지금 저장된 값
    return 새로운값;          // 이것이 저장된다
});
```
- 같은 provider에 대한 `modify`는 **한 번에 하나씩** 실행된다. 읽고, 바꾸고, 쓰는 사이에 다른 쓰기가 끼어들지 못한다.
- 그래서 OAuth 토큰 갱신이 동시에 여러 번 일어나도 한 번만 갱신된다. §7.1 실험에서 동시 5개 호출에 `refresh`가 1번만 불린 것이 이 덕분이다.
- 주석에는 "가능하면 프로세스 사이에서도 파일 락으로 막는다"고 적혀 있다(`:78-85`).
- 오류 규칙: `read`는 없으면 `undefined`를 돌려주고, 메서드는 **저장소 자체가 실패했을 때만** reject한다. `Models`가 그것을 `ModelsError("auth")`로 감싼다(주석 `:59-63`).

**누가 읽고 쓰나** (`코드 확인`)
| 시점 | 동작 | 위치 |
|---|---|---|
| 호출 때 인증 해석 | `read` | `resolve.ts:70` (`readCredential`) |
| 토큰이 곧 만료될 때 | `modify`로 갱신 후 저장 | `resolve.ts:126` |
| 로그인 | `modify`로 저장 | `models.ts:777` |
| 로그아웃 | `delete` | `models.ts:817` |
| 모델 목록 갱신 때 | `read`, `modify` | `models.ts:565`, `:618` |

**구현은 앱이 정한다**: ai 패키지는 규칙만 정하고 저장 위치는 정하지 않는다.
| 구현 | 위치 | 저장 |
|---|---|---|
| `InMemoryCredentialStore` | `ai/src/auth/credential-store.ts` | **메모리뿐.** 프로그램을 끄면 사라진다. 아무것도 안 넘기면 이것을 쓴다(`models.ts:394`). provider id별 Promise 사슬로 `modify`를 직렬화한다(`:11-28`). |
| `AuthStorage` | `coding-agent/src/core/auth-storage.ts` | `getAgentDir()` 아래 `auth.json`, 파일 권한 `0o600`, `proper-lockfile`로 프로세스 간 락 (헤더 주석과 `grep`으로 구조만 확인) |
| `ReadOnlyAuthStorage` | 같은 파일 | `auth.json`을 읽기만 하고, `modify`와 `delete`는 "Read-only credential storage cannot modify auth.json" 오류 (구조만 확인) |

`coding-agent`는 `createModels({ credentials, modelsStore })`로 자기 저장소를 넘긴다(`model-runtime.ts:211`). 그래서 pi를 다시 켜도 로그인이 유지된다. 이 부분은 호출 코드만 확인했고 `AuthStorage`의 나머지 동작은 `미확인`이다.

**한 줄 정리**: `CredentialStore` = provider별로 로그인 정보를 읽고(`read`), 안전하게 바꾸고(`modify`), 지우는(`delete`) 보관함의 규칙이고, 실제 저장 방식은 앱이 끼워 넣는다.

### 3.4 환경: `AuthContext` (`:97-101`, 구현 `auth/context.ts`)
`env(name)`(환경변수 읽기)과 `fileExists(path)`(파일 존재 확인, `~` 지원). 기본 구현은 `process.env`에서 읽되 **빈 문자열이나 공백뿐이면 `undefined`**로 본다(`context.ts:25-28`). 브라우저에서는 `process`가 없어서 `undefined`/`false`다. Node 모듈은 변수로 지정한 `import()`로 불러서 번들러가 따라가지 않게 한다(`:11-12`). 테스트에서 다른 구현을 주입할 수 있다.

### 3.5 provider별 인증 방법: `ProviderAuth` (`:166-250`)
```ts
interface ProviderAuth { apiKey?: ApiKeyAuth; oauth?: OAuthAuth }      // 최소 하나는 필수
```
| | `ApiKeyAuth` (`:170-199`) | `OAuthAuth` (`:216-240`) |
|---|---|---|
| `name` | 표시 이름 | 표시 이름 |
| `login` | 키를 입력받음. 없으면 "환경변수 등 주변 설정만 쓰는" provider | **브라우저 로그인**을 수행하고 `OAuthCredential`을 돌려줌 |
| `resolve` | 저장값과 환경변수에서 키를 찾음. `undefined`면 "설정 안 됨" | (없음) |
| `refresh` | (없음) | **리프레시 토큰으로 새 토큰 받기.** 네트워크 호출, 실패하면 던짐 |
| `toAuth` | (없음) | 유효한 credential에서 **요청용 `ModelAuth`를 만듦.** 부작용 없음 |
| `check` | 선택. 부작용 없이 "설정되었는지"만 확인 | (없음) |
| `isSubscription`, `loginLabel` | (없음) | 구독 로그인 표시, 선택 화면 라벨 |

OAuth가 `refresh`와 `toAuth`로 나뉜 이유는 주석에 있다: "`Models`가 락을 건 갱신 패턴을 직접 관리하게 하려는 것. `refresh`는 credential을 만들고, `toAuth`는 저장된 credential에서 요청용 인증을 얻는다"(`:211-215`).

## 4. 호출 때 인증이 정해지는 순서: `resolveProviderAuth` (`auth/resolve.ts:33-93`)
설명 주석(`:24-28`): "저장된 credential이 provider를 **소유한다.** 주변 설정(환경변수 등)은 저장된 것이 **없을 때만** 본다. 갱신이 실패했거나 맞는 처리기가 없는 credential 유형일 때 조용히 환경변수로 넘어가지 않는다."

```
resolveProviderAuthWithSignal (:46-93)
  ① overrides.apiKey 가 있고 provider에 apiKey 방식이 있으면                (:56-68)
        → 그 키로 resolveApiKey (저장소는 읽지 않음)                            ★ 가장 우선
  ② 저장된 credential 을 읽는다                                              (:70)
        ├ 저장된 것이 oauth 이고 provider에 oauth 방식이 있으면                (:72-81)
        │     → resolveStoredOAuth (§5.1)
        ├ 저장된 것이 api_key 이고 provider에 apiKey 방식이 있으면            (:82-88)
        │     → resolveApiKey (저장된 키에 호출 env 를 덧씌움)
        └ 그 외 (저장된 유형을 처리할 방법이 없음) → undefined                 ← 환경변수로 넘어가지 않음
  ③ 저장된 것이 없으면 → apiKey 방식의 resolve 에 credential 없이 맡김          (:89-93)
        → 환경변수, AWS 프로필, ADC 파일 등
```
- ①의 `overrides`는 `Models.getAuth(model, { apiKey, env, signal })`의 인자이며, `applyAuth`가 호출 옵션의 `apiKey`, `env`, `signal`을 넣어 준다(02 §4.4).
- 호출 옵션의 `env`는 `AuthContext`에 덧씌워진다(`overlayEnvAuthContext`, `:95-100`): `env(name)`이 호출 옵션 쪽을 먼저 보고 없으면 원래 환경을 본다.
- `resolveApiKey`는 provider의 `resolve`를 부르고, 실패하면 `ModelsError("auth")`로 감싼다(`:164-176`).
- 호출 중 취소(`signal`)가 오면 `raceWithAbortSignal`로 즉시 중단한다(`:33-44`).

### 4.1 `getAuth`가 `applyAuth` 앞에서 하는 추가 일 (`models.ts:737-754`)
- provider를 모르면 `undefined`.
- `resolveProviderAuth` 결과에 **모델의 `headers`를 합친다**(모델 전용 헤더, 예: 특정 모델에만 붙는 헤더).
- 결과가 `undefined`이면 `applyAuth`가 `ModelsError("auth", "Provider is not configured: ...")`를 던지고, 이것이 03에서 본 것처럼 스트림의 `error` 이벤트가 된다(02 §4.4).

### 4.2 "저장된 credential이 provider를 소유한다"는 말의 뜻 (`resolve.ts:24-28`, `:70-93`, `실행 확인`)
**한 줄**: provider에 **저장된 로그인 정보가 하나라도 있으면 그것만 쓰고, 환경변수 같은 다른 출처는 아예 보지 않는다.** 저장된 것이 쓸 수 없는 상태여도 환경변수로 몰래 바꿔 쓰지 않고 **오류를 낸다.**

주석 원문: "A stored credential owns the provider: ambient/env is consulted only when nothing is stored. No silent env fallback after a failed refresh or for a credential type without a matching handler."

코드(`:70-93`)는 이렇게 생겼다.
```ts
const stored = await readCredential(...);
if (stored) {                                              // 저장된 것이 있으면
    if (stored.type === "oauth" && provider.auth.oauth)   return resolveStoredOAuth(...);   // oauth 로 처리 (갱신 실패하면 여기서 던짐)
    if (stored.type === "api_key" && provider.auth.apiKey) return resolveApiKey(...);       // api_key 로 처리
    return undefined;                                      // 맞는 처리기가 없으면 "설정 안 됨" (환경변수로 안 감)
}
// 저장된 것이 없을 때만 여기로 온다
return provider.auth.apiKey ? resolveApiKey(..., undefined, ...) : undefined;     // 환경변수, AWS 프로필, ADC 파일 등
```
**`stored`가 있으면 어떤 경우에도 마지막 줄(환경변수)에 도달하지 않는다.** 이를 가짜 provider로 네 경우 돌려 봤다(`artifacts/pi/ai-demos/auth-owner-demo.ts`, 로그 `auth-owner-demo.2026-10-05.log`). 모든 경우에 환경변수(`DEMO_API_KEY=KEY_FROM_ENV`)가 설정되어 있다.

| 경우 | 저장된 것 | 결과 |
|---|---|---|
| 1 | 유효한 OAuth 로그인 | `apiKey=STORED_OAUTH`, `source=OAuth` → **환경변수 키를 무시하고 로그인 토큰을 씀** |
| 2 | 만료 임박한 OAuth + **갱신 실패** | **오류** `[oauth] OAuth refresh failed for demo: invalid_grant ...` → 환경변수 키로 넘어가지 **않음** |
| 3 | OAuth인데 provider에 **oauth 처리기가 없음** | `undefined`("설정 안 됨") → 환경변수 키로 넘어가지 **않음** |
| 4 | 저장된 것 **없음** | `apiKey=KEY_FROM_ENV`, `source=DEMO_API_KEY` → 이때만 환경변수를 씀 |

**이렇게 한 이유** (코드에 직접 적혀 있지는 않아서 `추론`): 구독 로그인(예: ChatGPT, Claude 구독)으로 쓰고 있다고 믿는 사용자가 있는데, 로그인이 만료되자 조용히 환경변수의 API 키로 바뀌면 **종량제 요금이 청구되거나 다른 계정으로 호출**될 수 있다. 그래서 문제가 있으면 오류로 알려서 사용자가 다시 로그인하게 한다. 실제 의도는 주석의 "silent"(조용히)라는 단어에서 읽은 해석이다.

## 5. 두 가지 인증 방식

### 5.1 OAuth: 저장된 토큰이 곧 만료될 때의 갱신 (`auth/resolve.ts:102-162`)
`resolveStoredOAuth`가 하는 일이다. 주석: "double-checked locking: 남은 유효 시간이 5분 미만인 토큰은 락을 걸고, 락 안에서 만료 여부를 다시 확인하고, 전체에서 한 번만 갱신하고, 바뀐 credential을 저장한 뒤 락을 푼다."

```
저장된 credential 의 expires 가 지금 + 5분 이하인가?                         (:119, :122)  ← 낙관적 확인
  아니오 → 그대로 toAuth(credential)                                          (:157-158)
  예    → credentials.modify(providerId, async (current) => {                 (:126-142)  ← 락 안에서
              current 가 oauth 가 아니면 (그 사이 로그아웃) → 변경 없음           (:129)
              current 가 이미 갱신되어 5분 넘게 남았으면 (다른 요청이 갱신함) → 변경 없음   (:130)  ← 권위 있는 확인
              아니면 oauth.refresh(current, 신호) 실행. 15초 제한                (:131-136)
              실패하면 ModelsError("oauth", "OAuth refresh failed for ...")     (:137-139)
         })
       갱신된 credential 로 toAuth(credential)
```
- **5분 여유**(`DEFAULT_OAUTH_MINIMUM_VALIDITY_MS`, `:102`)를 두는 이유는 요청이 시작된 직후 토큰이 만료되는 일을 피하려는 것으로 보인다(`추론`). `OpenAI ChatGPT` 흐름은 자체로 3분 여유를 둔다(`openai-chatgpt.ts` `EXPIRY_MARGIN_MS`).
- `modify`는 provider별로 직렬화되므로, 같은 토큰으로 요청 여러 개가 동시에 들어와도 **첫 번째만 갱신하고 나머지는 대기했다가 갱신된 값을 그대로 본다**(§7 실험).
- 갱신이 실패하면 저장된 credential은 그대로 남는다(재시도 가능). `getAuth`의 주석: "토큰 갱신 실패는 코드 `oauth`, 재로그인으로 해결"(`models.ts:296-298`). 갱신 실패 후 환경변수 키로 **조용히 넘어가지 않는다**(`:24-28` 주석).
- `toAuth`가 요청용 인증을 만든다: Anthropic과 OpenAI Codex 모두 `{ apiKey: credential.access }`다(`anthropic.ts:295-297`, `openai-codex.ts:432-434`). 즉 **OAuth 액세스 토큰이 그대로 `options.apiKey`가 된다.**

### 5.2 API 키: `envApiKeyAuth`와 provider별 구현
**표준형** `envApiKeyAuth(name, envVars)` (`auth/helpers.ts:9-31`)
- `resolve`: ① 저장된 credential의 `key`가 있으면 그것(`source: "stored credential"`), ② 없으면 `envVars`를 순서대로 보고 값이 있는 첫 환경변수(`source: 환경변수 이름`), ③ 없으면 `undefined`.
- `login`: 비밀 입력창(`type: "secret"`)으로 키를 입력받아 `{ type: "api_key", key }`를 돌려준다.
- 예: OpenAI는 `envApiKeyAuth("OpenAI API key", ["OPENAI_API_KEY"])`(`providers/openai.ts`).

**Anthropic 전용형** (`providers/anthropic.ts:28-70`) 환경변수가 여러 가지라 직접 구현한다.
| 순서 | 출처 | 결과 |
|---|---|---|
| 1 | 저장된 credential의 `key` | `apiKey` (`source: "stored credential"`) |
| 2 | `ANTHROPIC_AUTH_TOKEN` | `apiKey`가 아니라 **`Authorization: Bearer` 헤더**로 |
| 3 | `ANTHROPIC_OAUTH_TOKEN`, 그다음 `ANTHROPIC_API_KEY` | `apiKey` |
| 4 | workload identity federation 환경변수 세 개(`ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_IDENTITY_TOKEN_FILE`)가 모두 있으면 | `auth: {}` + `env`에 설정값 (키 없음. 토큰 교환은 Anthropic SDK가 함) |

**provider별 환경변수 이름** (`env-api-keys.ts:73-127`, 일부)
| provider | 환경변수 |
|---|---|
| `anthropic` | `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `google` | `GEMINI_API_KEY` |
| `github-copilot` | `COPILOT_GITHUB_TOKEN` |
| `azure-openai-responses` | `AZURE_OPENAI_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| 그 외 약 30개 | 같은 방식 (위 파일의 `envMap`) |

- **키 없이 주변 설정으로 인증되는 provider**: `google-vertex`(ADC 파일과 `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`이 모두 있으면), `amazon-bedrock`(`AWS_PROFILE`, IAM 키, `AWS_BEARER_TOKEN_BEDROCK`, ECS/IRSA 환경변수 중 하나)는 `getEnvApiKey`가 `"<authenticated>"`라는 표시 문자열을 돌려준다(`:160-192`). 실제 비밀 값이 아니다.
- **`env-api-keys.ts`의 `getEnvApiKey`는 `compat.ts:229`(구 전역 API)에서만 쓰인다.** 새 구조에서는 각 provider가 자기 `ApiKeyAuth`를 갖는다. 다만 `providers/anthropic.ts`는 이 파일의 환경변수 이름 상수를 가져다 쓴다.

### 5.3 API 키 환경변수의 이름과 위치
환경변수 이름은 provider마다 정해져 있고(예: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`), **pi를 실행하는 프로세스의 환경변수**(`process.env`)에 있으면 인식된다. `.env` 파일은 자동으로 읽지 않는 것으로 보인다. 자세한 표와 다른 지정 방법(`!명령`, `env` 객체)은 [04-01 §1](./04-01-auth-env-and-storage.md)에 정리했다.

## 6. 브라우저 로그인(OAuth) 흐름

### 6.1 구성 요소
| 파일 | 역할 |
|---|---|
| `auth/oauth/pkce.ts` | **PKCE**: 로그인 가로채기를 막는 장치. 무작위 32바이트를 만들어 `verifier`로 쓰고, 그 SHA-256 해시를 `challenge`로 만든다(`generatePKCE`, `:21-34`). 인증 서버에는 `challenge`를 먼저 보내고, 토큰을 교환할 때 `verifier`를 보내서 "처음 로그인을 시작한 쪽이 맞다"는 것을 증명한다. |
| `auth/oauth/callback-server.ts` | **로컬 콜백 서버**: `node:http`로 내 컴퓨터(`127.0.0.1`)에 임시 서버를 열고, 브라우저가 로그인을 마친 뒤 돌아오는 주소(`/callback`)를 받는다(`startOAuthCallbackServer`, `:50-148`). `state`가 다르면 400, 이미 처리했으면 409, 오류가 있으면 400을 응답한다. 시간 제한과 취소를 지원한다. |
| `waitForCallbackOrManualInput` (`:155-183`) | 콜백 서버가 응답하기를 기다리는 동시에 **사용자가 주소나 코드를 직접 붙여 넣는 입력창**도 연다. 둘 중 먼저 끝나는 쪽을 쓴다. SSH 접속처럼 브라우저가 이 컴퓨터의 `127.0.0.1`에 닿지 않는 경우를 위한 것이다(주석). |
| `auth/oauth/device-code.ts` | **디바이스 코드 로그인**(브라우저가 없는 환경): 사용자에게 코드를 보여 주고, 다른 기기에서 승인할 때까지 주기적으로 확인한다(`pollOAuthDeviceCodeFlow`). RFC 8628의 규칙(간격 기본 5초, `slow_down`이면 5초 증가)을 따른다. |
| `auth/oauth/load.ts` | OAuth 구현을 **지연 로딩**한다. 변수로 지정한 `import()`를 써서 번들러가 Node 전용 코드(`node:http`, `node:crypto`)를 따라가지 않게 한다. Bun 단일 실행 파일에서는 `registerBundledOAuthFlowLoaders`로 미리 묶은 구현을 등록한다. |
| `lazyOAuth` (`auth/helpers.ts:40-59`) | `OAuthAuth`를 감싸서 `login`/`refresh`/`toAuth`가 **처음 불릴 때** 구현을 불러온다. provider 정의(`providers/anthropic.ts`)는 로그인 코드를 import하지 않고 `lazyOAuth({ load: loadAnthropicOAuth })`만 둔다. |

### 6.2 Claude Pro/Max 로그인: `auth/oauth/anthropic.ts`
`login`은 먼저 방식을 묻는다(`:273-281`): **브라우저 로그인(기본)** 또는 **코드 복사 로그인(headless)**.

**브라우저 로그인** (`loginAnthropic`, `:138-189`)
```
1. PKCE verifier/challenge 생성                                         (:139)
2. 로컬 콜백 서버 시작 (127.0.0.1:53692 /callback). 실패해도 계속 진행     (:140-148)
3. 로그인 주소를 사용자에게 알림 (auth_url 이벤트)                        (:151-166)
     https://claude.ai/oauth/authorize?client_id=...&code_challenge=...&state=...&scope=...
4. 브라우저 콜백 또는 붙여 넣기 중 먼저 오는 것을 기다림                    (:168-171)
     붙여 넣기면 state 가 verifier 와 같은지 확인("OAuth state mismatch")  (:178)
5. 받은 code 로 토큰 교환                                               (:185, :94-136)
     POST https://platform.claude.com/v1/oauth/token
     { grant_type: "authorization_code", client_id, code, state, redirect_uri, code_verifier }
6. { type: "oauth", refresh, access, expires } 를 돌려줌                (:130-135)
     expires = 지금 + expires_in*1000 - 5분
```
**갱신** (`refreshAnthropicToken`, `:231-267`): 같은 토큰 주소에 `{ grant_type: "refresh_token", client_id, refresh_token }`를 POST하고 새 토큰 쌍을 받는다. `expires`도 같은 방식으로 5분 줄여 계산한다.

### 6.3 ChatGPT 구독 로그인(Codex): `auth/oauth/openai-codex.ts`
구조는 Claude와 같고 다른 점만 적는다.
| | Claude (`anthropic.ts`) | OpenAI Codex (`openai-codex.ts`) |
|---|---|---|
| 로그인 방식 | 브라우저 / 코드 복사 | 브라우저 / **디바이스 코드** |
| 콜백 주소 | `127.0.0.1:53692/callback` | `127.0.0.1:1455/auth/callback` (Codex CLI와 같은 포트. 사용 중이면 붙여 넣기로 넘어간다, `:361`) |
| 토큰 교환 | JSON 본문 POST | `application/x-www-form-urlencoded` POST (`:151-162`) |
| `state` | PKCE verifier를 그대로 씀 | 별도 무작위 16바이트(`:62-67`) |
| 토큰 후처리 | 없음 | **JWT에서 계정 ID를 꺼내 credential에 `accountId`로 저장** (`credentialsFromToken`, `:317-330`). 없으면 "Failed to extract accountId from token" 예외 |
| `expires` | `now + expires_in - 5분` | `now + expires_in` (여유 없음, 갱신 여유는 `resolve.ts`의 5분이 담당) |
| `toAuth` | `{ apiKey: access }` | `{ apiKey: access }` |

현재 `openai` provider의 구독 로그인은 `auth/oauth/openai-chatgpt.ts`다("Sign in with ChatGPT"). 로그인마다 동적으로 클라이언트를 등록하는 방식(`DYNAMIC_CLIENT_ID`), 토큰 주소 `auth.openai.com/api/accounts/oauth/token`, 3분 여유(`EXPIRY_MARGIN_MS`)가 Codex 흐름과 다르다. `toAuth`는 `{ apiKey: credential.access }`로 같고, 이 토큰은 `api.openai.com`으로 직접 보내진다(파일 머리말). 이 파일은 이후 거의 다 읽어서 [03-2 §7](./03-2-api-openai-responses.md)에 로그인 흐름(발급된 `clientId` 저장, 3분 마진, 콜백 서버 직접 구현 등)을 정리했다.

### 6.4 로그인이 저장되는 경로 (`models.ts:756-811`)
`models.login(providerId, type, interaction)`:
1. provider의 `oauth.login` 또는 `apiKey.login`을 실행해 credential을 받는다(없으면 "does not support ... login" 오류).
2. `credentials.modify(providerId, async () => credential)`로 저장한다. 저장 도중 취소되면 저장이 시작되기 전인지에 따라 취소 오류를 낸다.
3. `models.logout`은 `credentials.delete`다(`:813-822`).
**로그인 화면과 저장 위치는 앱(coding-agent)이 정한다.** `interaction`(`prompt`, `notify`)과 `CredentialStore`를 앱이 넘겨 준다.

### 6.5 로그인 결과는 어디에 저장되는가
브라우저 로그인이든 디바이스 코드 로그인이든 결과는 같은 `OAuthCredential`이고 `models.login` → `credentials.modify` → `AuthStorage` → **`~/.pi/agent/auth.json`**(`PI_CODING_AGENT_DIR`로 변경 가능, 파일 권한 `0o600`, 토큰은 평문 JSON)에 저장된다. 갱신도 같은 파일에 다시 쓰인다. 경로, 파일 모양, 보호, 로그아웃은 [04-01 §2](./04-01-auth-env-and-storage.md)에 정리했다.

## 7. 실험: 실제 코드로 확인 (`실행 확인`)
`models.ts`, `auth/credential-store.ts`, `auth/helpers.ts`를 그대로 불러서 **가짜 provider**(`createProvider`)와 **가짜 OAuth 구현**으로 돌렸다. 실제 서버와 통신하지 않았다. 스크립트는 `artifacts/pi/ai-demos/auth-resolve-demo.ts`, 출력은 `auth-resolve-demo.2026-10-05.log`다.

### 7.1 동시 5개 호출이 만료 임박 토큰을 만났을 때
저장된 토큰의 만료를 1분 뒤로(5분 이내) 해 두고 `getAuth`를 동시에 5번 불렀다. 가짜 `refresh`는 100ms 걸리게 했다.
```
[+   2ms] 저장된 토큰: access=OLD_ACCESS, 만료까지 1분 (5분 이내 → 갱신 대상)
[+  11ms] 동시에 getAuth 5번 호출
[+  12ms]   refresh() 호출됨 (누적 1번) - 네트워크 요청이라고 가정하고 100ms 걸림
[+ 114ms] 결과 apiKey: NEW_ACCESS, NEW_ACCESS, NEW_ACCESS, NEW_ACCESS, NEW_ACCESS
[+ 114ms] refresh 호출 횟수: 1  (5번 호출했지만 갱신은 1번)
[+ 114ms] source 라벨: OAuth
[+ 114ms] 이미 갱신된 토큰으로 getAuth 다시 호출
[+ 114ms] refresh 호출 횟수: 1  (유효하므로 늘지 않음)
```
- **갱신은 1번만 일어났고, 5개 호출이 모두 새 토큰을 받았다.** `modify`의 직렬화와 락 안의 재확인(`:130`)이 의도대로 동작한다.
- 갱신된 뒤에는 5분 넘게 유효하므로 다시 불러도 갱신하지 않는다.

### 7.2 API 키 찾는 우선순위
`envApiKeyAuth("Fake API key", ["FAKE_API_KEY"])`를 쓰는 가짜 provider로 확인했다.
```
① 환경변수 FAKE_API_KEY=from-env 만 있음            → apiKey=from-env,     source=FAKE_API_KEY
② + 저장된 credential(from-store)                  → apiKey=from-store,   source=stored credential
③ + 호출 옵션 apiKey=from-option                   → apiKey=from-option,  source=stored credential
④ 환경변수도 저장값도 없음                           → apiKey=undefined,    source=undefined
```
- 우선순위는 **호출 옵션 > 저장된 credential > 환경변수**다(§4와 일치).
- ③에서 눈에 띄는 점: 값은 호출 옵션인데 `source`는 `"stored credential"`로 나온다. `resolveProviderAuth`가 호출 옵션 키를 가짜 credential(`{ type: "api_key", key: 옵션값 }`)로 만들어 `resolve`에 넘기기 때문이다(`:56-68`). 상태 화면용 라벨이 호출 옵션 출처를 구분하지 못한다는 뜻이다(`코드 확인` + 실험).
- ④처럼 하나도 없으면 `getAuth`는 `undefined`를 돌려주고, `applyAuth`가 "Provider is not configured" 오류를 낸다.

## 8. 인증이 03의 통신 코드로 이어지는 경로
`getAuth`의 결과(`AuthResult`)는 `applyAuth`가 호출 옵션과 합쳐서 `requestOptions`를 만든다(02 §4.4, `models.ts:858-868`).
| 요청 옵션 | 값 |
|---|---|
| `apiKey` | 호출 옵션 `apiKey` ?? 인증 결과 `apiKey` |
| `headers` | 인증 결과 `headers` → 호출 옵션 `headers`로 덮어쓰기 → `transformHeaders` |
| `env` | 인증 결과 `env` + 호출 옵션 `env` |
| 모델 `baseUrl` | 인증 결과가 `baseUrl`을 주면 교체 |

### Claude (03-1): OAuth 토큰과 일반 API 키를 구분한다
- 로그인으로 받은 `access`가 `options.apiKey`로 들어온다(`toAuth`).
- `createClient`는 `apiKey.includes("sk-ant-oat")`이면 **OAuth 토큰으로 판단**해서 Bearer 방식과 Claude Code 흉내 헤더 경로를 탄다(`anthropic-messages.ts:980-982`, `:1016-1036`). 이 접두사 규칙은 코드로 확인했고, 실제 구독 로그인 토큰이 그 접두사로 시작하는지는 토큰을 받아 보지 않아서 `미확인`이다.
- `ANTHROPIC_AUTH_TOKEN`처럼 헤더로 오는 인증은 `hasRequestAuth`가 `Authorization` 헤더를 보고 인정한다(`:318-325`).
- 인증이 하나도 없으면 `streamSimple`이 "No API key for provider: ..."를 던진다(`:327-329`, `:935-937`).

### Codex (03-4, legacy): OAuth JWT에서 계정 ID를 다시 꺼낸다
- `access`(JWT)가 `options.apiKey`로 들어오고, `stream`이 `extractAccountId(apiKey)`로 계정 ID를 JWT에서 꺼내 `chatgpt-account-id` 헤더에 넣는다(`openai-codex-responses.ts:270`, `:1627-1655`).
- 로그인 때 `accountId`를 credential에 저장해 두지만(`openai-codex.ts:323-329`), `toAuth`는 `access`만 넘긴다. 그래서 통신 코드가 JWT에서 **같은 값을 다시 계산**한다.

## 9. 설계 포인트
1. **인증을 한 곳에서 합친다.** 키 찾기, 저장된 로그인, 환경변수, 호출 옵션이 모두 `resolveProviderAuth` 하나를 통과한다. 통신 코드는 최종 `apiKey`와 `headers`만 받는다.
2. **저장된 credential이 환경변수보다 우선이고, 실패해도 조용히 넘어가지 않는다.** 로그인이 만료되었는데 다른 키로 몰래 호출되는 일을 막으려는 설계로 읽힌다(`추론`).
3. **`modify` 하나로 모든 쓰기를 직렬화한다.** 갱신과 로그인이 동시에 일어나도 토큰이 이중으로 갱신되지 않는다.
4. **ai 패키지는 저장 위치를 정하지 않는다.** `CredentialStore`는 인터페이스이고 기본 구현은 메모리뿐(`InMemoryCredentialStore`)이다. 파일 저장은 앱이 넣는다. `coding-agent`의 `AuthStorage`가 `getAgentDir()` 아래 `auth.json`(파일 권한 `0o600`)에 저장하고 `proper-lockfile`로 프로세스 사이 락을 건다(`coding-agent/src/core/auth-storage.ts`의 헤더 주석과 `grep` 결과만 확인, 파일 경로의 정확한 위치와 나머지 동작은 `미확인`). 저장된 `key`는 설정 값(환경변수 참조나 명령 실행)으로 해석되는 경로가 있다(`resolveConfigValue`, `:266`, `:446`, `미확인`).
5. **로그인 코드는 필요할 때만 불러온다.** `lazyOAuth`와 `load.ts`가 Node 전용 코드를 브라우저 번들에서 분리한다.
6. **브라우저 로그인은 두 갈래를 항상 연다.** 콜백 서버가 막히는 환경(SSH 등)을 위해 붙여 넣기 입력창을 같이 열고 먼저 끝나는 쪽을 쓴다.

## 10. 읽지 않은 것 (`미확인`)
- 실제 로그인 흐름 실행, 토큰 교환 응답의 모양, 구독 로그인 토큰의 접두사
- `auth/oauth/github-copilot.ts`(507줄), `kimi-coding.ts`, `meta.ts`, `xai.ts`, `openrouter.ts`, `radius.ts` (`openai-chatgpt.ts`는 03-2 §7에서 읽음)
- `coding-agent`의 `AuthStorage`(`auth-storage.ts` 506줄), `runtime-credentials.ts`, `resolve-config-value.ts`
- 인증을 쓰는 곳에서의 `check`(`models.ts:645-669`)와 `getAvailable`의 동작 상세는 02에서 읽은 범위까지만
- Bedrock/Vertex 등 클라우드 인증은 통신 코드(`bedrock-converse-stream.ts` 등)에서 별도 처리하며 읽지 않았다.

## 11. 다음
05 utils: `retry`, `json-parse`(`parseStreamingJson`), `estimate`, `overflow`, `validation` 등 03에서 이름만 나온 것들. 06 호출 경로 종합.
