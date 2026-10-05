---
title: "pi-ai: Provider/API Separation and Compat Data"
created: 2026-10-06
updated: 2026-10-06
type: concept
tags: [architecture, pattern, agent-framework, developer-tools]
sources:
  - reports/pi/ai/01-types.md
  - reports/pi/ai/02-models-registry.md
  - reports/pi/ai/03-3-api-openai-compare.md
  - repos/pi/packages/ai/src/types.ts
  - repos/pi/packages/ai/src/models.ts
  - repos/pi/packages/ai/src/api/openai-completions.ts
  - repos/pi/packages/ai/src/providers/anthropic.ts
confidence: high
---

# pi-ai: Provider/API Separation and Compat Data

여러 LLM 회사를 한 인터페이스로 다룰 때 pi-ai가 택한 구조다. 사례 전체는 [[pi]].

## 아이디어
**"어느 서비스인가(provider)"와 "어떤 말투로 통신하는가(api)"를 서로 다른 축으로 둔다.** 같은 말투를 쓰는 여러 서비스가 통신 코드를 공유하고, 서비스마다 다른 점은 코드가 아니라 **모델 데이터의 `compat` 필드**로 표현한다.

## 구조 (source-verified)
| 개념 | 위치 | 설명 |
|---|---|---|
| `Model.api` / `Model.provider` | `types.ts:1097-1108` | 모델 명세서가 두 축을 모두 기록한다. 응답(`AssistantMessage`)도 둘 다 기록해서 모델을 바꿔도 출처를 안다(`:547-549`) |
| `Provider` | `models.ts:144-233` | 서비스 하나: 주소, 인증 방법, 모델 목록, 통신 코드 |
| `createProvider({ id, auth, models, api })` | `models.ts:1034-1175` | 부품으로 조립. `api`는 통신 코드 하나 또는 `model.api`별 대응표 |
| 모델별 `compat` | `types.ts:789-967`, `models.ts` | `api`에 따라 타입이 갈리는 방언 메모(OpenAI 호환은 약 40개 플래그) |
| 자동 감지 | `api/openai-completions.ts:1585-1726` | `provider` 이름과 `baseUrl`로 기본값을 정하고 `model.compat`이 **필드 단위로** 덮어쓴다 |
| 지연 로딩 | `api/lazy.ts:73`, `providers/anthropic.ts` | 통신 코드는 첫 호출 때 `import()` |

## 왜 유용한가
- 한 서비스 안에 여러 회사의 모델이 섞여도(예: GitHub Copilot은 모델 계열별로 3가지 `api`) 같은 구조로 처리된다.
- 모델 데이터 집계(2026-10-04 생성, `reports/pi/ai/03-3` §1): `openai-completions`가 26개 provider, 716개 모델을 맡는다. 서비스를 추가할 때 통신 코드를 새로 쓰지 않는다.
- 호출하는 쪽은 `Context` 하나만 알면 되고, 회사별 차이(지침 위치, 추론 설정 형식, 최대 출력 필드 이름 등)는 통신 코드 안에 갇힌다.

## 대가와 주의
- 방언이 많은 쪽(`openai-completions.ts`)은 1726줄이 되고, 추론 설정만 11가지 `thinkingFormat`으로 갈라진다.
- **알 수 없는 서버는 표준(OpenAI)과 같다고 가정**한다. 다르면 `model.compat`으로 알려 줘야 한다(`reports/pi/ai/03-3` §6.3 실험).
- 감지는 문자열 포함 검사(`baseUrl.includes(...)`)라서 주소가 바뀌면 놓칠 수 있다(`추론`).

## 재사용할 때 체크
1. 통신 방식과 서비스 이름을 한 필드에 섞지 않는다.
2. 서비스별 차이는 데이터(플래그)로, 통신 방식별 차이는 코드로 둔다.
3. 데이터가 코드를 덮어쓰는 단위(필드별)를 정한다.
4. 기본값이 "표준과 같다"일 때 어긋나는 서버를 알릴 경로를 만든다.

관련: [[stealable-pattern-async-event-stream-with-final-result]], [[stealable-pattern-stored-credential-owns-provider]].
