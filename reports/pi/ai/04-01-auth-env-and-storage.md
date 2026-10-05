# ai 04-01: 인증 보충 — API 키 환경변수와 로그인 저장 위치

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [04-auth](./04-auth.md)(인증 전체 구조, 특히 §4 해석 순서, §5 두 가지 방식, §6 로그인 흐름)
- **읽은 파일**: `ai/src/env-api-keys.ts`(195줄), `ai/src/auth/context.ts`, `ai/src/models.ts`(`login`, `logout`), `coding-agent/src/config.ts`(`:537-613`), `coding-agent/src/core/auth-storage.ts`(`:1-200`, `:327-506`), `coding-agent/src/core/resolve-config-value.ts`(앞부분), `coding-agent/docs/providers.md`, `docs/configuration.md`, `docs/environment-variables.md`. 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드와 저장소 안의 공식 문서를 읽은 `코드 확인`. **이 컴퓨터의 `auth.json`은 비밀 정보가 들어 있을 수 있어 열어 보지 않았다.** 실제 로그인과 서버 통신은 하지 않았다(`미확인`).

## 0. 이 문서의 질문
04에서 인증을 해석하는 순서(호출 옵션, 저장된 credential, 환경변수)를 봤다. 그 뒤에 남는 실용적인 질문 두 가지를 정리한다.

1. API 키를 환경변수로 줄 때 **이름은 무엇이고, 어디에 두어야 인식되는가?**
2. OAuth 로그인(브라우저든 디바이스 코드든)의 **결과는 어디에 어떤 경로로 저장되는가?**

## 1. API 키 환경변수: 이름과 위치 (`코드 확인`, `docs/providers.md`)
**pi를 실행하는 프로세스의 환경변수**에 있으면 된다. pi는 `process.env`를 읽는다(`auth/context.ts:25-28`). 공식 문서의 안내도 같다: "Set the variable before starting Pi"(`coding-agent/docs/providers.md`, "Use an API key from the environment").
```bash
export ANTHROPIC_API_KEY=sk-ant-...     # 쉘에서 설정하고
pi                                       # 같은 쉘에서 실행
```
- **영구적으로 쓰려면** 쉘 시작 파일(예: `~/.zshrc`, `~/.bashrc`)에 `export ...`를 적어 두는 일반적인 방법을 쓴다. 이것은 쉘의 일반 동작이며 pi 코드에서 확인한 것은 아니다.
- **`.env` 파일은 자동으로 읽지 않는 것으로 보인다.** `coding-agent/src`에서 `dotenv` 같은 로딩 코드를 찾지 못했다(`grep`, 완전한 증명은 아님).
- **빈 값이나 공백뿐인 값은 없는 것으로 본다**(`context.ts:27`).
- **환경변수 이름은 provider마다 정해져 있다.** 주요 것만 적는다(전체는 `docs/providers.md`와 `env-api-keys.ts:73-127`).
  | provider | 환경변수 |
  |---|---|
  | Anthropic | `ANTHROPIC_API_KEY` (그 외 `ANTHROPIC_OAUTH_TOKEN`는 API 키로, `ANTHROPIC_AUTH_TOKEN`는 Bearer 헤더로 인식) |
  | OpenAI | `OPENAI_API_KEY` |
  | Google Gemini | `GEMINI_API_KEY` |
  | GitHub Copilot | `COPILOT_GITHUB_TOKEN` |
  | OpenRouter | `OPENROUTER_API_KEY` |
  | DeepSeek | `DEEPSEEK_API_KEY` |
  | Mistral | `MISTRAL_API_KEY` |
  | Azure OpenAI | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_BASE_URL` 또는 `AZURE_OPENAI_RESOURCE_NAME` |
  | Amazon Bedrock | `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`+`AWS_SECRET_ACCESS_KEY`, `AWS_BEARER_TOKEN_BEDROCK` 등 |
- **환경변수 말고 키를 지정하는 다른 방법**(`docs/providers.md`, `core/resolve-config-value.ts`)
  - `/login`으로 저장한 키는 `auth.json`에 들어가고 **환경변수보다 우선**한다(§4.2).
  - `auth.json`의 `key`에 `!`로 시작하는 **명령**을 적으면 키가 필요할 때 그 명령을 실행해서 출력값을 쓴다(예: `"key": "!security find-generic-password -ws 'anthropic'"`). 결과는 프로세스가 사는 동안 캐시한다(문서의 설명).
  - `key` 값은 명령, 환경변수 참조(`$NAME`, `${NAME}`), 일반 문자열 중 하나로 해석된다(`resolve-config-value.ts` 머리말과 템플릿 파서). 참조 문법의 세부는 읽지 않았다(`미확인`).
  - 저장된 API 키 credential에 `env` 객체를 넣으면 **그 provider에 한해 프로세스 환경변수보다 우선**한다(예: Cloudflare 계정 ID, 문서 예시).

## 2. OAuth 로그인 결과는 어디에 저장되는가 (`코드 확인`)
브라우저 로그인이든 디바이스 코드 로그인이든 **마지막에는 똑같은 `OAuthCredential` 객체**(`{ type: "oauth", access, refresh, expires, ... }`)가 만들어지고, 그것이 같은 경로로 저장된다.
```
브라우저 / 디바이스 코드 로그인  →  OAuthCredential
   → models.login()          (models.ts:756-811)
   → credentials.modify(providerId, async () => credential)     (models.ts:777)
   → coding-agent 의 AuthStorage.modify  (core/auth-storage.ts:449-471)
   → auth.json 파일에 기록                                       (core/auth-storage.ts:186-188)
```
- **저장 파일**: `<agent-dir>/auth.json`. 기본 경로는 **`~/.pi/agent/auth.json`**이다.
  - `getAgentDir()`가 환경변수 `PI_CODING_AGENT_DIR`이 있으면 그 경로(`~` 확장 지원), 없으면 `join(homedir(), ".pi", "agent")`를 돌려준다(`coding-agent/src/config.ts:563-568`, `:583`).
  - 폴더 이름 `.pi`와 환경변수 이름은 앱 이름 설정에서 나온다(`config.ts:537-544`, `package.json`의 `piConfig`). 기본 이름이 `pi`이므로 `PI_CODING_AGENT_DIR`이다.
  - 공식 문서도 같다: "`<agent-dir>/auth.json`: Saved API keys and OAuth credentials", 위치는 `PI_CODING_AGENT_DIR` 환경변수나 SDK의 `agentDir` 옵션으로 바꾼다(`docs/configuration.md:7-17`).
- **파일 모양**: provider id를 키로 하는 JSON 객체다(`type AuthStorageData = Record<string, Credential>`, `auth-storage.ts:17`). 아래는 모양을 보이려는 예시이고 실제 내용이 아니다.
  ```json
  {
    "anthropic": { "type": "oauth", "access": "...", "refresh": "...", "expires": 1759000000000 },
    "openai":    { "type": "api_key", "key": "sk-..." }
  }
  ```
- **보호**: 파일을 **처음 만들 때** 권한을 `0o600`(소유자만 읽고 쓰기)으로, 폴더는 `0o700`으로 만든다(`auth-storage.ts:24-25`, `:56-67`). 주석: "모드는 생성할 때만 적용해서 관리자가 정한 권한과 ACL이 유지된다." **토큰은 평문 JSON으로 저장된다.** 공식 문서도 "`auth.json` can contain API keys and OAuth tokens. Keep it private and do not commit it"이라고 경고한다(`docs/providers.md`).
- **동시 접근 보호**: 쓸 때마다 `proper-lockfile`로 파일 락을 걸고 쓴다(`auth-storage.ts:9`, `:116-155`, `:157-200`). 락이 30초 넘게 남으면 낡은 것으로 본다(`staleMs = 30_000`). 락 파일이 어디에 생기는지는 이 라이브러리의 동작이며 코드에서 직접 확인하지 않았다(`미확인`).
- **갱신도 같은 곳에 저장된다.** 04 §5.1의 갱신(`resolveStoredOAuth`)은 `credentials.modify`를 쓰므로 새 토큰 쌍이 같은 `auth.json`에 다시 쓰인다.
- **로그아웃**: `/logout`은 `credentials.delete`로 그 provider 항목만 지운다(`models.ts:813-822`). 문서: 이것은 환경변수를 해제하거나, `models.json`의 인증을 지우거나, provider 쪽에서 토큰을 폐기하지는 않는다.
- **환경변수 API 키는 저장되지 않는다.** 환경변수는 프로세스가 읽을 뿐 `auth.json`에 쓰이지 않는다.
- `auth.json`이 읽기 전용이거나 깨졌을 때의 동작, `models.json`과 `settings.json`의 관계는 읽지 않았다(`미확인`).

## 3. 한 장 요약
| 출처 | 어디에 있나 | 우선순위 (04 §4.2) |
|---|---|---|
| 호출 옵션의 `apiKey` | 코드에서 직접 넘김 | 가장 높음 |
| **저장된 credential** (`/login`으로 저장한 API 키 또는 OAuth 토큰) | **`~/.pi/agent/auth.json`** (`PI_CODING_AGENT_DIR`로 변경 가능) | 그다음. 있으면 **환경변수는 보지 않는다** |
| **환경변수** | pi를 실행하는 프로세스의 환경 (`export ...` 후 `pi`) | 저장된 것이 **없을 때만** |

- 저장된 것이 있으면 환경변수를 몰래 대신 쓰지 않는다. 갱신이 실패하면 오류를 낸다(04 §4.2의 실험).
- 환경변수 API 키는 어디에도 저장되지 않는다. `auth.json`에 있는 것은 `/login`으로 저장한 것뿐이다.

## 4. 읽지 않은 것 (`미확인`)
- 이 컴퓨터의 `auth.json` 실제 내용과 권한
- 락 파일(`proper-lockfile`)이 생기는 정확한 위치
- `key` 값의 `$NAME`, `${NAME}` 참조 문법의 세부(`resolve-config-value.ts` 나머지 약 200줄)
- `auth.json`이 읽기 전용이거나 깨졌을 때의 동작, `models.json`과 `settings.json`과의 관계
- `ReadOnlyAuthStorage`의 사용처
