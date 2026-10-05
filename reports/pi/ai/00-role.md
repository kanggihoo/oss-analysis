# ai 00: pi에서 `ai` 패키지의 역할

- **기준 commit**: `3874b3e98` (2026-10-02) / **분석일**: 2026-10-04
- **대상**: `repos/pi/packages/ai` (`@earendil-works/pi-ai` v1.0.0)
- **검증 수준**: 의존 관계, export, 연결 지점, import 횟수 모두 이 commit(`3874b3e98`)에서 직접 확인했다(`코드 확인`). 집계 방법은 §7에 적었다.
- 이전 분석 [Q4](../questions/q4-ai-package-roles.md)의 결론을 이 commit에서 다시 확인한 내용이다.

## 1. 한 문장
**`ai`는 "어떤 AI 회사의 모델이든 같은 방식으로 호출하고, 같은 모양의 답을 받게 해 주는" 통역 층이다.** 모델 목록, 로그인/인증, 통신 방식 차이, 비용 계산까지 책임진다. 대화를 이어 가는 일, 도구를 실행하는 일은 하지 않는다.

패키지 설명도 같다: `"Unified LLM API with automatic model discovery and provider configuration"` (`ai/package.json`).

## 2. pi 전체에서의 위치

```
coding-agent  (제품: pi CLI, 세션 저장, 화면, 도구 구현)
     │ 사용
     ▼
agent         (반복 실행: AI 호출 → 도구 실행 → 다시 호출)
     │ 사용
     ▼
ai            (AI 회사별 차이를 숨김)   ← 여기
     │ 호출
     ▼
Anthropic / OpenAI / Google / Bedrock / Mistral ... (외부 서비스)
```

- `ai`는 **다른 pi 패키지에 의존하지 않는다.** 내부 의존은 `pi-telemetry`(추적 정보 전달)뿐이다(`ai/package.json` dependencies, `코드 확인`). 외부 SDK는 `@anthropic-ai/sdk`, `openai`, `@google/genai`, `@aws-sdk/client-bedrock-runtime` 등이다.
- `ai`를 의존하는 패키지: `agent`, `coding-agent`, `evals`, `durable` (4개 `package.json`에 선언, `src`에서 실제 import도 확인, `코드 확인`).
- 나머지(`tui`, `mcp`, `codemode`, `telemetry`, `chord`, `client`, `protocol`, `server`)는 `src`에서 `pi-ai`를 import하지 않는다. `mcp`는 주석, `client`/`server`는 테스트 설정 파일에서 이름만 언급한다(`코드 확인`).
- 이전 SHA 기준 분석과 달라진 점: `agent`의 `src` import가 50회에서 4회로 줄었고, `packages/session-backends`는 없어졌다. 자세한 내용은 §7.

비유하면 `ai`는 통역사, `agent`는 통역사를 데리고 일을 시키는 반장, `coding-agent`는 반장이 일하는 사무실(제품)이다. 이 비유는 [learning-guide](../learning-guide.md)에서 쓴 것이다.

## 3. `ai`가 하는 일 (6가지)

| # | 일 | 쉬운 설명 | 대표 위치 |
|---|---|---|---|
| 1 | **공용 서식 정의** | 대화, 모델, 도구, 사용량, 알림 서식을 하나로 정한다. | `types.ts` ([01-types](./01-types.md)) |
| 2 | **모델 목록 관리** | "쓸 수 있는 모델이 뭔가"를 회사별로 모으고 최신으로 갱신한다. | `models.ts`, `providers/*`, `models-store.ts` |
| 3 | **호출 진입점** | `stream`/`streamSimple`/`complete`로 모델을 부르면 알맞은 통신 코드로 연결한다. | `models.ts` |
| 4 | **회사별 통신 번역** | 요청을 각 회사 형식으로 바꿔 보내고, 도착하는 응답을 공용 알림으로 되돌린다. | `api/*.ts` |
| 5 | **인증** | API 키, 환경변수, 저장된 로그인(OAuth) 중 쓸 것을 정하고 만료를 갱신한다. | `auth/*`, `env-api-keys.ts` |
| 6 | **이어 쓰기 지원** | 대화 도중 모델을 바꿔도 이전 기록을 새 모델에 맞게 고치고, 사용량과 비용을 계산한다. | `api/transform-messages.ts`, `models.ts` |

이 표는 Q4의 기능 표를 요약했다. 파일 역할 대부분은 `코드 확인`이지만, 각 파일 내부 동작은 아직 단계별로 읽는 중이다.

### 3.1 `api`와 `provider`: 이 패키지의 핵심 구분
- **api**: 통신 방식. 예: `anthropic-messages`, `openai-completions`. `src/api/`에 구현이 있고 `KnownApi`는 10종이다(`types.ts:17`).
- **provider**: 회사/계정. 예: `anthropic`, `openai`. `src/providers/`에 있고 "주소 + 인증 방법 + 모델 목록 + 쓸 api"를 묶는다.
- 여러 회사가 한 api를 공유한다. OpenAI식 통신(`openai-completions`)을 쓰는 여러 호환 회사가 같은 통신 코드를 쓰고, 미세한 차이는 모델별 `compat` 설정으로 맞춘다(Q4, `코드 확인`. 이 commit에서 일부 provider만 직접 확인).

## 4. `ai`가 하지 않는 일 (경계)

| 하지 않는 일 | 누가 하나 | 근거 |
|---|---|---|
| 도구 실행, "AI 호출 → 도구 → 다시 호출" 반복 | `agent` (`agent-loop.ts`) | Q5 |
| 재시도 실행 | `agent`, `coding-agent` | `ai`는 `isRetryableAssistantError`, `isContextOverflow` 같은 **판정 함수만** 제공한다(`utils/retry.ts`, `utils/overflow.ts`, Q4). |
| 대화 저장, 요약(compaction) | `coding-agent` | Q8 |
| 화면 출력 | `tui`, `coding-agent` | |

## 5. 위쪽과 연결되는 지점 (`코드 확인`)

- `agent`는 `ai`의 모델 레지스트리를 모른다. `agent`는 주입받은 `streamFn`을 쓰고, 없으면 `setDefaultStreamFn()`으로 등록된 기본 함수를 쓴다. 둘 다 없으면 에러를 던진다(`agent/src/stream-fn.ts:11-17`).
- `coding-agent`가 연결한다.
  - `core/sdk.ts:39`: `setDefaultStreamFn(streamSimple)`로 기본 함수를 등록한다.
  - `core/model-runtime.ts:211`: `createModels({ credentials, modelsStore })`로 모델 런타임을 만든다.
- `ai` 루트 export(`index.ts`)는 `types`, `models`, `auth` 타입, `utils`(event-stream, retry, overflow, validation, transcript 등), `providers/faux`, `typebox`의 `Type`을 내보낸다. 카탈로그와 회사별 코드는 `/providers/*`, `/api/*`, `/compat`, `/oauth` subpath로 분리되어 있다(`package.json` exports, `index.ts`).

## 6. 이 단계에서 확인되지 않은 것 (`미확인`)
- 위 6가지 일의 내부 동작 대부분은 아직 줄 단위로 읽지 않았다. 순서는 [01-types](./01-types.md) → `transcript.ts`, `event-stream.ts`, `compat.ts` → 모델 레지스트리 → `api/anthropic-messages.ts` → 인증이다.
- import 횟수는 이전 SHA 기준이다. 필요하면 현재 commit에서 다시 집계한다.

## 7. 현재 commit 기준 import 집계 (`코드 확인`)

집계 명령: `grep -rhoE '"@earendil-works/pi-ai[^"]*"' packages/<pkg>/src` 후 종류별 개수. 테스트는 `test/`로 따로 센다.

| 패키지 | `src` | `test` | `src`에서 쓰는 subpath |
|---|---|---|---|
| `coding-agent` | 108 | 149 | 루트 73, `/compat` 16, `/providers/all` 5, `/oauth` 4, `/providers/radius-config` 3, `/utils/model-operations` 2, 그 외 5종 각 1 |
| `durable` | 19 | 92 | 루트 12, `/utils/transcript` 2, `/utils/retry` 2, `/utils/validation`, `/utils/overflow`, `/utils/estimate` 각 1 |
| `agent` | 4 | 6 | 루트만. `agent.ts`, `types.ts`, `agent-loop.ts`, `proxy.ts` |
| `evals` | 2 | 0 | 루트 1, `/utils/transcript` 1 |

- 이전 집계(`cross-package-imports.txt`, `4259686d9`)와 비교:
  - `agent`는 50회에서 4회로 줄었다. `7fd478a2e`(2026-10-01) `feat(agent): remove the experimental harness from pi-agent-core` 커밋이 harness를 삭제했고, `packages/agent/src`는 6개 파일(`agent-loop`, `agent`, `index`, `proxy`, `stream-fn`, `types`)만 남았다. 이전 SHA 대비 112개 파일에서 약 3.1만 줄이 삭제되었다. `agent/package.json`에서 `chord` 의존도 사라졌다.
  - `coding-agent`는 94회에서 108회로 늘었다.
  - `session-backends`는 `packages/` 아래에 더 이상 없다. 이전 SHA에는 33개 파일이 있었다.
- 영향: [Q4](../questions/q4-ai-package-roles.md)의 "재시도는 agent-core의 `harness/runtime/drive/response.ts`, `harness/compaction`이 한다"는 부분은 이 commit에서는 맞지 않는다. 그 경로가 삭제되었기 때문이다. 현재 재시도 주체는 별도로 다시 확인해야 한다(`미확인`).
- 이 변화는 `agent` 단계에서 다시 분석해야 하는 항목이다. 이전 `agent` 보고서(Q5, Q6)도 이 commit 기준으로 재검증이 필요하다.
