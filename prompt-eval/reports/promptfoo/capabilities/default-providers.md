---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/providers/defaults.ts
  - src/providers/credentials.ts
  - src/providers/env.ts
  - src/envars.ts
  - src/envOverrides.ts
  - src/providers/openai/defaults.ts
  - src/providers/openai/codexDefaults.ts
  - src/providers/anthropic/defaults.ts
  - src/providers/google/ai.studio.ts
  - src/providers/google/vertex.ts
  - src/providers/google/auth.ts
  - src/providers/mistral/defaults.ts
  - src/providers/xai/defaults.ts
  - src/providers/webSearchUtils.ts
  - src/types/providers.ts
  - src/types/index.ts
  - src/matchers/providers.ts
  - src/matchers/rubric.ts
  - src/matchers/llmGrading.ts
  - src/matchers/comparison.ts
  - src/matchers/rag.ts
  - src/matchers/similarity.ts
  - src/matchers/moderation.ts
  - src/matchers/classification.ts
  - src/matchers/search.ts
  - src/matchers/agent.ts
  - src/assertions/utils.ts
  - src/evaluator.ts
  - src/node/doEval.ts
  - src/util/config/load.ts
  - src/commands/eval.ts
  - src/commands/optimize.ts
  - src/commands/generate/dataset.ts
  - src/commands/generate/assertions.ts
  - src/testCase/synthesis.ts
  - src/assertions/synthesis.ts
  - src/suggestions.ts
  - src/optimizer/promptOptimizer.ts
  - site/docs/configuration/expected-outputs/model-graded/index.md
depends: []
status: ready
reimplementation: 미실행
---

# 기본 provider 선택 규칙

> 사용자가 grader·제안·테스트 생성 모델 등을 따로 지정하지 않았을 때, 환경변수(API 키)의 유무로 "기본 provider 묶음"(채점·제안·합성·임베딩·moderation·웹검색)을 고르고, 설정(`--grader`, `defaultTest.options.provider`, `assert[].provider`)이 있으면 그것으로 덮어쓰는 규칙.

<!--
이 스펙 안의 용어
- 기본 묶음(DefaultProviders): `getDefaultProviders()`가 돌려주는 객체. 역할별 provider 8칸(1.3).
- grader(채점 provider): 모델 채점 어서션(`llm-rubric` 등)이 채점 호출에 쓰는 provider. 평가 대상(target) provider와 별개다.
- 폴백 계열: OpenAI·Anthropic·Gemini 키와 Azure 조건이 모두 없을 때만 후보가 되는 Vertex(ADC)·Mistral·xAI·Codex.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. 모델 채점 어서션, `--suggest-prompts`, `optimize`, `generate dataset|assertions` 등이 "역할"(채점·제안·합성·임베딩·moderation·웹검색)에 맞는 provider가 필요해지면 `getDefaultProviders()`를 **인자 없이** 부른다(호출 때마다 선택을 다시 한다). (R-01, R-17)
2. 선택기는 환경변수에서 provider 키·자격 유무를 읽어 위에서부터 8단계 사다리로 하나의 계열을 고른다. 첫 매칭에서 멈춘다. `OPENAI_API_KEY`가 있으면 항상 OpenAI 계열이다. (R-02~R-06)
3. 고른 계열이 역할별 provider 인스턴스를 채운 기본 묶음을 만든다. 계열마다 모델 이름과 비는 칸이 다르다. (R-07~R-10)
4. 모델 채점 어서션은 먼저 설정에서 grader를 찾고(`assert[].provider` → `test.options.provider`, 여기에 `defaultTest.options.provider`와 `--grader`가 합쳐져 있음), 없으면 `cliState.config.defaultTest` 쪽 폴백(주의: 대상 모델용 `defaultTest.provider`도 포함)을 보고, 그래도 없으면 3의 기본 묶음 칸을 쓴다. (R-12~R-16)
5. 제안(`--suggest-prompts`·`optimize`)은 설정으로 바꿀 방법 없이 기본 묶음 `suggestionsProvider`만 쓴다. `generate`는 `--provider`가 있으면 그것, 없으면 `synthesizeProvider`를 쓴다. (R-18, R-19)
6. 선택 입력에 평가 대상 provider는 들어가지 않는다. 대상과 grader가 같은 계열이 되는지는 코드가 점검하지 않는다. (R-20)

### 1.2 범위·통합 지점 [필수]

- 제공: 환경변수 기반 기본 묶음 선택, 모델 채점 어서션용 grader 해석 순서(설정 덮어쓰기 포함), 제안·합성 provider 선택, 임베딩·moderation 기본값.
- 제외: 개별 provider의 호출 구현·인증 상세(provider-contract 스펙 참조), 채점 프롬프트 본문과 결과 JSON 해석(model-graded-matchers 스펙), 레드팀 전용 provider 선택(`RedteamProviderManager` 등. `src/providers/defaults`를 import하는 곳은 아래 소비처뿐이라는 것만 확인했고 레드팀 쪽은 읽지 않았다), 원격 채점 서버 경로의 세부 조건.
- 외부 의존: 환경변수·`.env`·설정 `env:` 블록(1.3 환경변수 층 순서), 파일 시스템(`~/.codex/auth.json` 존재 확인), Google Application Default Credentials(ADC) 탐색, Codex SDK 패키지가 설치돼 있고 버전 범위에 맞는지.
- 소유 상태·부작용: 모듈 전역에 provider 인스턴스(OpenAI·Mistral 기본 묶음은 모듈 로드 때 한 번 생성해 공유, Anthropic은 `cliState.envScope`별, Codex는 자격 지문별 최대 32개)와 ADC 탐색 결과 캐시. 선택 자체는 네트워크 호출을 하지 않지만 ADC 탐색은 로컬 인증 파일·GCP 메타데이터를 시도할 수 있다(추론, R-05). 키가 하나도 없어도 선택은 오류 없이 OpenAI 묶음을 돌려준다.

### 1.3 인터페이스와 데이터 의미 [필수]

**기본 묶음 `DefaultProviders`** (`getDefaultProviders(env?)` → `Promise<DefaultProviders>`; 소비처는 모두 `env` 없이 호출)

| 칸 | 필수 | 쓰는 곳 |
|---|---|---|
| `gradingProvider` | 예 | 텍스트 채점 일반(factuality, closed-qa, g-eval, select-best, RAG 계열, deepeval 계열) |
| `gradingJsonProvider` | 예 | JSON 응답을 기대하는 채점의 기본. `llm-rubric`·`trajectory:goal-success` 등 `runJsonGradingPrompt`가 `llmRubricProvider`가 없을 때 쓴다 |
| `llmRubricProvider` | 아니오 | `runJsonGradingPrompt`에서 `gradingJsonProvider`보다 우선(있는 계열: Anthropic, AI Studio, Codex) |
| `suggestionsProvider` | 예 | `--suggest-prompts`(`generatePrompts`), `optimize` |
| `synthesizeProvider` | 예 | `generate dataset`, `generate assertions` |
| `embeddingProvider` | 예 | `similar`, `answer-relevance` |
| `moderationProvider` | 예 | `moderation` 어서션 |
| `webSearchProvider` | 아니오 | `search-rubric` |

**환경변수 층** (`resolveProviderApiKey(undefined, env, 이름목록)`): 높은 층부터 ① provider 층 명시값 ② provider 층 ③ 호출자 `env` ④ suite 층(설정 파일 `env:`) ⑤ file 층(`--env-file`) ⑥ `process.env`. 각 층에서 이름 목록 순서대로 본다. 값이 정의돼 있고 비어 있지 않으면 그 값을 쓴다. **빈 문자열은 "없음"이며 그 이름을 마스킹해 더 낮은 층의 같은 이름을 막는다**. 선택기는 값의 존재 여부(boolean)만 쓴다.

**선택 입력과 이름 목록** (모두 위 규칙으로 해석)

| 입력 | 환경변수 |
|---|---|
| OpenAI 키 | `OPENAI_API_KEY` |
| Anthropic 키 | `ANTHROPIC_API_KEY` |
| Gemini(AI Studio) 키 | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `PALM_API_KEY` |
| Azure 키 | `AZURE_API_KEY`, `AZURE_OPENAI_API_KEY` |
| Azure 서비스 주체 | `AZURE_CLIENT_ID`·`AZURE_CLIENT_SECRET`·`AZURE_TENANT_ID` 셋 모두 |
| Azure 배포명 | `AZURE_DEPLOYMENT_NAME`과 `AZURE_OPENAI_DEPLOYMENT_NAME` **둘 다** |
| Mistral 키 / xAI 키 | `MISTRAL_API_KEY` / `XAI_API_KEY` |
| Codex 자격 | `CODEX_API_KEY`(선택 단계에서는 `OPENAI_API_KEY`가 이미 없는 상태이므로 사실상 이것만), 또는 `CODEX_HOME`(기본 `~/.codex`) 아래 비어 있지 않은 `auth.json` + Codex SDK 패키지 설치·버전 적합 |
| Google ADC | 키 없이 Google 기본 자격이 잡히는지(`hasGoogleDefaultCredentials`, 결과 캐시) |
| Azure Content Safety | `AZURE_CONTENT_SAFETY_ENDPOINT` |

**계열별 구성** (기본 모델은 각 계열 `defaults` 파일의 상수. 아래 "—"는 그 칸이 비어 있음)

| 계열 | grading / suggestions / synthesize | gradingJson | llmRubric | embedding | moderation | webSearch |
|---|---|---|---|---|---|---|
| OpenAI | `gpt-6-sol` chat(synthesize는 gradingJson과 같은 JSON 모드 인스턴스) | `gpt-6-sol` chat + `response_format: json_object` | — | `text-embedding-3-large` | `omni-moderation-latest` | `gpt-6-sol` Responses + `web_search_preview` |
| Azure | 배포명 `AZURE_OPENAI_DEPLOYMENT_NAME`의 Azure chat 인스턴스 하나를 네 칸이 공유(JSON 모드 없음) | 위와 같음 | — | R-09의 Azure 임베딩 규칙 | OpenAI의 moderation | — |
| Anthropic | `claude-sonnet-5` messages 인스턴스 하나를 공유 | 같은 인스턴스 | `claude-sonnet-5` + 강제 도구 `grade_output`(pass·score·reason)를 받아 `output`을 그 객체로 변환 | OpenAI의 임베딩 | OpenAI의 moderation | `claude-sonnet-5` + `web_search_20260209`(max_uses 5) |
| Google AI Studio | `gemini-3.8-flash` | 같은 모델 + `response_mime_type: application/json` | `gemini-3.8-flash`(JSON 설정 없음) | **Vertex** `gemini-embedding-001` | OpenAI의 moderation | — |
| Google Vertex | `gemini-3.8-flash`(region `global`) | grading과 같은 인스턴스 | — | Vertex `gemini-embedding-001` | OpenAI의 moderation | — |
| Mistral | `mistral-large-latest` | 같은 모델 + `json_object` | — | Mistral 임베딩 | OpenAI의 moderation | — |
| xAI | `grok-4.3` | 같은 모델 + `json_object` | — | OpenAI의 임베딩 | OpenAI의 moderation | `grok-4.3` Responses + `web_search` |
| Codex SDK | Codex SDK provider(모델 미지정, `read-only` 샌드박스, 승인 `never`, 임시 작업 디렉터리). grading·suggestions·synthesize가 같은 인스턴스 | 같은 SDK + 출력 스키마(pass·score·reason) | gradingJson과 같은 인스턴스 | OpenAI의 임베딩 | OpenAI의 moderation | 같은 SDK + 스키마·`web_search_mode: live`·네트워크 허용 |

"OpenAI의 임베딩/moderation"은 OpenAI 키가 없는 계열에서도 OpenAI provider 객체를 쓴다는 뜻이다. 그 계열에 `OPENAI_API_KEY`가 없으면 사용 시점에 provider가 실패한다(추론, 아래 R-09·R-10).

**grader 설정 입력** (`GradingConfig.provider`, `assert[].provider`, `options.provider`가 같은 형태)

| 형태 | 의미 |
|---|---|
| 문자열 | provider id로 로드(`loadApiProvider`). 모든 역할에 같은 provider를 쓰므로 임베딩 역할에 텍스트 provider를 주면 오류(R-16) |
| `{ id, config, ... }` | ProviderOptions로 로드 |
| ApiProvider 인스턴스 | 그대로 사용(라이브러리 사용) |
| `{ text?, embedding?, classification?, moderation? }` | 역할별 지정(값은 위 세 형태 중 하나). 필요한 역할 키가 없으면 오류(R-14) |

**설정으로 grader를 바꾸는 곳**: CLI `--grader <provider>`(`commandLineOptions.grader`로도 설정), `defaultTest.options.provider`, `tests[].options.provider`, `assert[].provider`. 대상 모델 지정용 `defaultTest.provider`/`tests[].provider`는 grader를 지정하는 필드가 아니지만 R-15의 폴백에 걸린다.

### 1.4 행동 규칙과 남은 질문 [필수]

**A. 기본 묶음 선택**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 키 존재 판정 | 모든 키·자격 판정은 1.3의 환경변수 층 순서로 읽고 값이 비어 있지 않을 때만 "있음"이다. 소비처는 모두 `getDefaultProviders()`를 `env` 없이 호출하며(검색 결과), 호출 때마다 판정을 다시 한다(선택 결과 캐시 없음). | 코드 확인 |
| R-02 | 선택 사다리: 위에서부터 첫 매칭. ① **Azure**: OpenAI 키 없음 + (Azure 키 또는 서비스 주체 3종) + `AZURE_DEPLOYMENT_NAME`과 `AZURE_OPENAI_DEPLOYMENT_NAME` 둘 다 있음 ② **Anthropic**: OpenAI 키 없음 + Anthropic 키 ③ **Google AI Studio**: OpenAI·Anthropic 키 없음 + Gemini 계열 키 ④ **Vertex**: 폴백 게이트 통과 + ADC 있음 ⑤ **Mistral**: 폴백 게이트 + ADC 없음 + Mistral 키 ⑥ **xAI**: 폴백 게이트 + ADC 없음 + Mistral 키 없음 + xAI 키 ⑦ **Codex**: 폴백 게이트 + ADC 없음 + Mistral·xAI 키 없음 + Codex 자격 ⑧ 그 외 **OpenAI** | 위 순서대로 정확히 한 계열이 선택된다. | 코드 확인 |
| R-03 | Azure 계열이 Anthropic·Gemini 키와 함께 있을 때(OpenAI 키 없음) | Azure 조건(R-02 ①)이 먼저 평가되므로 Azure가 이긴다. Azure 조건이 하나라도 빠지면(예: 배포명 변수 둘 중 하나 없음) Azure는 건너뛴다. | 코드 확인 |
| R-04 | `OPENAI_API_KEY`가 있음 | Azure·Anthropic·AI Studio·Vertex·Mistral·xAI·Codex 후보가 모두 꺼지고 OpenAI 계열이 선택된다. 다른 키(Anthropic 등)가 같이 있어도 마찬가지이므로, 평가 대상이 Claude여도 grader는 OpenAI다. | 코드 확인 |
| R-05 | 폴백 게이트: Azure 비선택 + OpenAI·Anthropic·Gemini 키 모두 없음 | 이때만 ADC를 탐색하고(`hasGoogleDefaultCredentials`) Mistral·xAI·Codex 후보를 평가한다. 게이트가 닫혀 있으면 ADC 탐색을 하지 않는다. ADC가 잡히면 Mistral·xAI·Codex 키가 있어도 Vertex가 이긴다. Mistral > xAI > Codex 순이다. | 코드 확인(탐색 구현 내부의 네트워크 시도는 추론) |
| R-06 | 어떤 키도 없음(또는 모든 후보 탈락) | 오류 없이 OpenAI 묶음이 선택된다. 실제 호출 때 OpenAI provider가 키 부재로 실패하는지는 provider 쪽이며 이 스펙은 보장하지 않는다. | 코드 확인(선택), 미확인(호출 실패 형태) |
| R-07 | 선택된 계열의 구성 | 1.3 "계열별 구성" 표대로 8칸을 채운다. 비필수 칸(`llmRubricProvider`, `webSearchProvider`)은 표의 "—" 계열에서 `undefined`다. | 코드 확인 |
| R-08 | 계열 간 불균일 | 같은 `gradingProvider`라도 `llm-rubric`은 `llmRubricProvider ?? gradingJsonProvider`를 쓰므로 OpenAI에서는 JSON 모드 인스턴스, Anthropic에서는 강제 도구 인스턴스, AI Studio에서는 JSON 설정 없는 인스턴스, Codex에서는 스키마 지정 인스턴스가 쓰인다. 반면 factuality·closed-qa·g-eval·select-best·RAG 계열은 `gradingProvider`를 쓴다(OpenAI의 `gradingProvider`는 JSON 모드가 아님). | 코드 확인 |
| R-09 | `embeddingProvider` 선택 | Anthropic·xAI·Codex·AI Studio(Vertex 임베딩)·Mistral·Vertex 계열은 1.3 표대로다. Azure 계열은 순서대로: ① `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`이 있으면 Azure 임베딩 배포 ② Gemini 계열 키 → AI Studio `gemini-embedding-001` ③ Mistral 키 → Mistral 임베딩 ④ `VOYAGE_API_KEY` → Voyage `voyage-3.5` ⑤ ADC 있음 → Vertex 임베딩 ⑥ OpenAI `text-embedding-3-large`. Azure **채팅** 배포는 임베딩 배포로 쓰이지 않는다. | 코드 확인 |
| R-10 | `moderationProvider` | 모든 계열에서 OpenAI `omni-moderation-latest`. 단 `AZURE_CONTENT_SAFETY_ENDPOINT`가 있으면 계열과 무관하게 Azure Content Safety(`text-content-safety`)로 바뀐다. `moderation` 어서션은 추가로 `OPENAI_API_KEY`가 **없고**(`getEnvString`, 층 순서는 R-01과 같으나 별칭 없음) `REPLICATE_API_KEY` 또는 `REPLICATE_API_TOKEN`이 있으면 위 기본값 대신 Replicate의 Llama Guard를 기본으로 쓴다. | 코드 확인 |
| R-11 | 전역 덮어쓰기 `setDefaultCompletionProviders(p)`, `setDefaultEmbeddingProviders(p)` | 호출 후 `getDefaultProviders()`는 선택 결과의 completion 5칸(`gradingJson`·`grading`·`llmRubric`·`suggestions`·`synthesize`) 또는 `embedding` 칸을 모두 그 provider로 바꾼다. `llmRubricProvider`가 원래 비어 있던 계열에서도 채워진다. Azure Content Safety 덮어쓰기(R-10)는 이 둘보다 먼저 적용된다. 기준 SHA에서 이 두 함수를 부르는 곳은 테스트뿐이고 CLI·설정·공개 export(`src/index.ts`)에서는 닿지 않는다. | 코드 확인 |
| R-21 | 인스턴스 수명 | 같은 계열을 다시 선택하면 새 인스턴스를 만들지 않을 수 있다: OpenAI·Mistral은 `env`가 없으면 모듈 전역 공유 인스턴스, Anthropic은 같은 `cliState.envScope`에서 키·URL·헤더가 같으면 캐시, Codex는 자격 지문별 LRU 32개. 선택 규칙(R-02)은 캐시와 무관하게 매번 적용된다. | 코드 확인 |

**B. grader 해석(모델 채점 어서션)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | 어서션이 grader를 해석한다 | `getAndCheckProvider(type, provider, defaultProvider, checkName)` → `getGradingProvider`: ① `provider`가 문자열이면 로드 ② 객체이고 `id()` 함수가 있으면 그대로 ③ 객체이면 `provider[type]`이 있으면 그 값으로(문자열·옵션·인스턴스), 없고 `provider.id`가 있으면 옵션으로 로드, 배열이면 오류, 그 외는 "Invalid provider definition" 오류 ④ `provider`가 null/undefined면 R-15의 폴백, 거기서도 못 찾으면 `defaultProvider`(기본 묶음의 해당 칸). 어서션마다 쓰는 `type`·기본 칸은 R-17. | 코드 확인 |
| R-13 | 설정 층의 우선순위 | 어서션에 전달되는 `provider`는 `assert[].provider`가 있으면 그것, 없으면 `test.options.provider`다(`getFinalTest`). `test.options`는 `defaultTest.options`와 테스트 자체 옵션을 합친 것이며 테스트 쪽이 이긴다. `--grader`는 설정 로드 때 `defaultTest.options.provider`의 초깃값으로 들어가지만 설정 파일의 `defaultTest.options.provider`가 덮어쓴다. 그런데 실행 직전(`doEval`, 재개 실행 아님)에 `cmdObj.grader`가 있으면 `defaultTest.options.provider`를 `--grader`로 **다시 덮어쓴다**. 따라서 우선순위는 `assert[].provider` > `tests[].options.provider` > `--grader` > 설정의 `defaultTest.options.provider` > R-15 폴백 > 기본 묶음이다. | 코드 확인 |
| R-14 | 역할별 객체 `{text, embedding, ...}` | 호출 역할(`text`·`embedding`·`classification`·`moderation`)의 키가 있어야 한다. 예: `defaultTest.options.provider: { embedding: ... }`만 있으면 `llm-rubric`(역할 `text`)이 오류("Invalid provider definition for output type 'text'")를 낸다. 역할 키 값이 문자열·옵션이면 로드 때 `cliState.env`가 적용된다. | 코드 확인 |
| R-15 | `provider`가 비어 있을 때의 폴백 | `cliState.config.defaultTest`가 객체이면 후보를 순서대로 본다: ① `defaultTest.provider`(**대상 모델 지정 필드**) ② `defaultTest.options.provider.text` ③ `defaultTest.options.provider`. 첫 번째 truthy 후보(`promptfoo:simulated-user`로 판정되는 것은 건너뜀)를 R-12로 다시 해석한다. 후보가 하나도 없으면 `defaultProvider`. 즉 `defaultTest.provider: openai:...`처럼 대상을 고정하고 grader를 따로 안 주면 **대상 모델이 grader가 된다**(공식 문서도 같은 경고를 싣는다). ②③은 R-13의 병합 때문에 보통 이미 `provider`에 들어와 있어 폴백까지 오는 일이 드물다. | 코드 확인 |
| R-16 | 타입 검증과 대체 | 해석된 provider가 없으면 `defaultProvider`(경고 로그), 그것도 없으면 오류. `embedding` 역할은 `callEmbeddingApi` 또는 `callSimilarityApi`, `classification`은 `callClassificationApi`, `moderation`은 `callModerationApi`가 있어야 유효하다. 유효하지 않을 때: 사용자가 `provider`를 **명시**했으면 오류(`Provider ... is not a valid <type> provider for '<check>'`), 명시하지 않았는데(폴백 후보가 부적합) 기본 provider가 있으면 경고 후 기본 provider로 대체, 없으면 오류. | 코드 확인 |
| R-17 | 어서션별 `type`·기본 칸 | `llm-rubric`·`trajectory:goal-success`(공통 `runJsonGradingPrompt`): `text`, `llmRubricProvider ?? gradingJsonProvider`. factuality·`model-graded-closedqa`·g-eval·`select-best`·`context-recall`·`context-relevance`·`context-faithfulness`·deepeval 계열: `text`, `gradingProvider`. `answer-relevance`: `embedding`은 `embeddingProvider`, `text`는 `gradingProvider`를 각각 해석(같은 `provider` 설정을 두 역할에 적용). `similar`: `embedding`, `embeddingProvider`. `moderation`: `moderation`, R-10의 기본. `classifier`: `classification`, 기본 provider 없음(`null`). | 코드 확인(deepeval 계열은 호출 지점만 확인) |
| R-22 | `search-rubric`·`agent-rubric` | 별도 규칙이다. `search-rubric`: 설정 grader가 있으면 `getGradingProvider('text', ..., null)`(R-15 폴백 포함)로 해석하되 웹검색 능력이 없으면 기본 묶음 `webSearchProvider`→`llmRubricProvider`→`gradingProvider` 중 웹검색 가능한 것으로 바꾸고, 그것도 없으면 `loadWebSearchProvider(true)`가 Anthropic(`claude-opus-5-5`) → OpenAI Responses(`gpt-6-sol`) → Perplexity → Google → Vertex → xAI 순으로 로드를 시도하며, 모두 실패하면 오류. `agent-rubric`: 설정 grader가 없으면 Codex 기본 묶음의 `llmRubricProvider`를 쓰고, 에이전트형 provider가 아니면 오류. | 코드 확인 |
| R-23 | 레드팀 설정이 있고 grader 미지정인 `llm-rubric` | `redteam` 설정이 있고 `redteam.provider`가 없고 `rubricPrompt`가 없고 `shouldUseRemoteGrading`이 참이면 기본 묶음 대신 promptfoo 원격 채점으로 간다. 일반 평가(`redteam` 설정 없음)에는 해당이 없다. | 코드 확인(조건 구조), 미확인(`shouldGenerateRemote` 내부) |

**C. 제안·합성 provider**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | `--suggest-prompts`(평가 중 프롬프트 변형 제안), `optimize`(후보 프롬프트 생성) | 둘 다 `getDefaultProviders().suggestionsProvider`를 쓴다. 이 provider를 바꾸는 설정·옵션이 없다(`optimize` 옵션은 `-c`, `--prompt-index`, `--provider-index`, `--validation-split`, `--env-file`뿐). `--grader`·`defaultTest.options.provider`의 영향을 받지 않는다. 환경변수(R-02)와 R-11만 바꾼다. | 코드 확인 |
| R-19 | `generate dataset`, `generate assertions`(및 같은 함수를 부르는 호출자) | `--provider <provider>`(합성 함수의 `provider`)가 정의돼 있으면 `loadApiProvider(provider, {basePath})`로 로드한 것을, 아니면 `getDefaultProviders().synthesizeProvider`를 쓴다. CLI 도움말은 "기본 grading provider"라고 하지만 구현은 `synthesizeProvider`이며, OpenAI 계열에서는 `gradingProvider`와 다른 JSON 모드 인스턴스다(2.1). | 코드 확인 |

**D. 독립성**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | 평가 대상 provider와 grader의 관계 | 선택 함수 어디에도 평가 대상 provider를 입력으로 받는 곳이 없다(`getDefaultProviders`는 `env`만, `getGradingProvider`는 `type`·`provider`·`defaultProvider`만 받는다). 대상이 Claude이고 `ANTHROPIC_API_KEY`만 있으면 grader도 Anthropic(`claude-sonnet-5`)이 되고, 같은 계열인지 비교하거나 피하는 코드는 없다. 예외적으로 R-15가 대상 모델을 grader로 만든다. 어서션이 grader를 부를 때 평가 대상 provider를 `providerCallContext.originalProvider`로 **전달**은 하지만 선택에는 쓰이지 않는다. | 코드 확인 |

- 불변식: (1) R-04: `OPENAI_API_KEY`가 해석되면 선택은 항상 OpenAI 계열. (2) 선택기는 가용성 검사 없이 키 "존재"만 본다: 키가 유효한지·모델이 접근 가능한지는 호출 시점의 문제다. (3) `moderationProvider`·`embeddingProvider`는 completion 계열 선택과 독립적으로 OpenAI로 남을 수 있다(R-09·R-10).
- 미결정: 없음.
- 확인 한계:
  - 실행하지 않았다(설치·빌드·네트워크 금지). 모든 규칙은 정적 읽기다. 테스트는 `test/providers/defaults.test.ts`·`credentials.test.ts`·`default-env-scope.test.ts`의 사례명만 훑었고 열지 않았다(테스트를 읽은 것도 실행 확인이 아님).
  - Codex 기본 계열의 실제 모델은 Codex SDK/계정 기본값이라 코드로 정해지지 않는다(미확인). 각 provider의 `id()` 문자열 형태, 키 부재 시 호출 실패 메시지는 읽지 않았다(provider-contract 영역).
  - 라이브러리 `evaluate()`(`src/node/evaluate.ts`)는 `cliState.config`를 설정하는 코드가 파일 안에 없다(검색 결과). 따라서 그 경로에서는 R-15 폴백이 비어 있을 수 있다(추론). 병합된 `test.options.provider`(R-13)는 평가기(`evaluator.ts`)가 합치므로 그대로 동작한다.
  - 공식 문서(`site/docs/.../model-graded/index.md`)는 레드팀 실행에서 `RedteamProviderManager`가 `defaultTest.provider`를 `options.provider`보다 먼저 고른다고 쓴다. 이 부분은 읽지 않았다(미확인).
  - ADC 탐색(`GoogleAuthManager.getOAuthClient`) 내부는 읽지 않았다. "로컬 파일·메타데이터 시도"는 `suppressExpectedGcpMetadataLookupWarning` 이름에서 한 추론이다.

### 1.5 필수 코드 참조 [필수]

라이선스: 루트 MIT(overview 1절). 인용 시 저작권·허가 문구를 유지한다. 아래 범위는 모두 MIT 코어 파일이다(`src/external/`은 Apache-2.0이며 이 스펙의 범위 밖).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/providers/defaults.ts:63-126` `DefaultProviderPreferences`, `getDefaultProviderPreferences` | 선택 플래그 7개의 정의와 게이트 관계(R-02~R-05의 정확한 불리언 식) | R-02, R-03, R-04, R-05 |
| C-02 | `src/providers/defaults.ts:140-259` `getDefaultProviders` | 플래그 → 계열 분기 순서, 계열별 8칸 채우기, Azure Content Safety 덮어쓰기, 전역 덮어쓰기 적용 순서 | R-02, R-07, R-10, R-11 |
| C-03 | `src/providers/defaults.ts:21-61` `COMPLETION_PROVIDERS`, `EMBEDDING_PROVIDERS`, `getEmbeddingProviderForAzureDefaults` | 덮어쓰기 대상 칸 목록, Azure 계열 임베딩 선택 사슬 | R-09, R-11 |
| C-04 | `src/providers/credentials.ts:10-21` `resolveProviderApiKey`, `src/providers/env.ts:5-33` `resolveProviderEnv` | 환경변수 층 순서와 빈 문자열 마스킹 | R-01 |
| C-05 | `src/providers/openai/defaults.ts:8-25` `createProviders`, `src/providers/anthropic/defaults.ts:9`, `:26-65`, `:116-136`, `src/providers/mistral/defaults.ts:5-18`, `src/providers/xai/defaults.ts:9-47`, `src/providers/google/ai.studio.ts:655-668`, `src/providers/google/vertex.ts:1530-1550` | 계열별 기본 모델 상수와 칸 구성 | R-07, R-08 |
| C-06 | `src/providers/openai/codexDefaults.ts:157-166`, `:168-189`, `:365-416` `hasCodexDefaultCredentials`, `getCodexDefaultProviderConfig`, `getCodexDefaultProviders` | Codex 자격 판정과 기본 묶음 구성(샌드박스·출력 스키마·칸 공유) | R-02, R-07 |
| C-07 | `src/matchers/providers.ts:205-296` `getGradingProvider`, `:298-350` `getAndCheckProvider` | grader 해석 분기, defaultTest 폴백, 타입 검증과 대체/오류 | R-12~R-16 |
| C-08 | `src/assertions/utils.ts:12-52` `getFinalTest` | 어서션 `provider` > 테스트 `options.provider` 합성 | R-13 |
| C-09 | `src/node/doEval.ts:788-803`, `src/util/config/load.ts:1294-1300` | `--grader` 주입 위치(로드 시 초깃값, 실행 전 덮어쓰기) | R-13 |
| C-10 | `src/matchers/rubric.ts:905-913` `runJsonGradingPrompt`의 기본 칸 선택 | `llmRubricProvider ?? gradingJsonProvider` | R-17 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드 읽기). 실행하지 않았다. 환경변수는 "다른 관련 변수는 모두 없음"을 전제하고, ADC·Codex 자격도 없다고 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-06 | 환경변수 없음 | 기본 묶음 = OpenAI 계열. 오류 없음 |
| T-02 | R-04, R-20 | `OPENAI_API_KEY`와 `ANTHROPIC_API_KEY` 둘 다 있음, 대상 모델은 Claude | `llm-rubric`의 grader = OpenAI `gpt-6-sol`(JSON 모드). 대상이 Claude여도 바뀌지 않음 |
| T-03 | R-02, R-07, R-08 | `ANTHROPIC_API_KEY`만 있음 | `suggestions`·`synthesize`·`grading` = `claude-sonnet-5`; `llm-rubric`은 강제 도구 `grade_output` 인스턴스, `embeddingProvider`는 OpenAI 객체 |
| T-04 | R-02, R-03 | `ANTHROPIC_API_KEY`와 Azure 키·두 배포명 변수 | Azure 계열 선택(Anthropic은 쓰이지 않음) |
| T-05 | R-02, R-03 | Azure 키와 `AZURE_OPENAI_DEPLOYMENT_NAME`만 있고 `AZURE_DEPLOYMENT_NAME` 없음, Anthropic 키도 없음 | Azure 조건 불충족 → 폴백 게이트 통과, 다른 후보 없음 → OpenAI 계열 |
| T-06 | R-02, R-05 | `GEMINI_API_KEY`와 `MISTRAL_API_KEY` | AI Studio 계열(`gemini-3.8-flash`). Mistral 조건은 평가되지 않음 |
| T-07 | R-05 | `MISTRAL_API_KEY`와 `XAI_API_KEY`, ADC 없음 | Mistral 계열 |
| T-08 | R-05 | 키 없음, ADC 있음 | Vertex 계열 |
| T-09 | R-01 | `OPENAI_API_KEY`를 `--env-file`에서 비어 있지 않은 값으로 주고 설정 `env:`에서 `OPENAI_API_KEY: ""` | suite 층이 file 층보다 높으므로 그 이름이 마스킹되어 OpenAI 키 "없음"으로 판정 |
| T-10 | R-13 | `--grader anthropic:messages:X`와 설정 `defaultTest.options.provider: openai:Y`, 테스트·어서션에는 provider 없음 | grader = X(실행 전 덮어쓰기) |
| T-11 | R-13 | 같은 설정에서 어떤 `llm-rubric`에 `provider: openai:Z` | 그 어서션의 grader = Z. `--grader`가 이기지 못함 |
| T-12 | R-15 | `defaultTest.provider: openai:gpt-X`만 있고 grader 지정 없음 | `llm-rubric` grader = `openai:gpt-X`(대상과 동일) |
| T-13 | R-15 | T-12에 `defaultTest.options.provider: anthropic:messages:Y` 추가 | grader = Y(`test.options.provider`가 채워져 폴백에 닿지 않음) |
| T-14 | R-16 | `similar` 어서션에 `provider: openai:gpt-X`(문자열) | 임베딩 역할 검증 실패 → 사용자가 명시했으므로 오류 |
| T-15 | R-16 | `answer-relevance`, `defaultTest.provider`만 텍스트 provider이고 grader 미지정 | 폴백 후보가 임베딩으로 부적합 → 경고 후 `embeddingProvider` 기본으로 대체, 텍스트 역할은 폴백 후보 사용 |
| T-16 | R-14 | `defaultTest.options.provider: { embedding: openai:embeddings:... }`만 있고 `llm-rubric` 사용 | 역할 `text` 키 없음 → 오류 |
| T-17 | R-18 | `optimize` 실행, `--grader`와 `defaultTest.options.provider` 지정 | 후보 생성은 여전히 `suggestionsProvider`(환경변수로 선택된 모델) |
| T-18 | R-19 | `generate dataset` 인자 `--provider` 없음, OpenAI 키만 있음 | `synthesizeProvider`(JSON 모드 `gpt-6-sol`) 사용 |
| T-19 | R-10 | OpenAI 키 없음, Replicate 키 있음, `moderation` 어서션 | 기본 moderation = Replicate Llama Guard |
| T-20 | R-11 | 테스트 코드에서 `setDefaultCompletionProviders(p)` 호출 후 `getDefaultProviders()` | completion 5칸이 모두 `p`, `embedding`·`moderation`은 영향 없음 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

| R-ID / T-ID | 근거 (repo@dfe2d45 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-04, `src/envars.ts:515-559` `getEnvOverrides`, `getEnvString`; `src/providers/defaults.ts:76-92`; 호출 지점 검색 `getDefaultProviders(` (`src/matchers/*.ts`, `suggestions.ts`, `optimizer/promptOptimizer.ts`, `testCase/synthesis.ts`, `assertions/synthesis.ts`, `external/*`) | 코드 읽기와 `grep`. 전 호출이 인자 없음 |
| R-02 ~ R-05 | C-01, C-02 | 코드 확인. ADC 탐색은 `src/providers/google/auth.ts:568-599` `hasDefaultCredentials`(탐색 실패면 false, 결과 캐시) |
| R-02 (Codex 자격) | C-06; `src/providers/openai/codexDefaults.ts:120-135` `hasCodexAuthFile`, `:137-155` `canLoadCodexSdkPackage` | `OPENAI_API_KEY`가 목록에 있지만 R-04로 이미 선택이 끝나므로 이 단계에서는 `CODEX_API_KEY`·`auth.json`만 의미(추론: C-01 `useCodexDefaults`가 `!hasOpenAiCredentials`를 요구하는 식에서 도출) |
| R-06 | C-02의 최종 `else`(`defaults.ts:227-239`) | 호출 실패 형태는 provider 구현 미읽음 |
| R-07, R-08 | C-05, C-06; `src/providers/anthropic/defaults.ts:67-93` `AnthropicLlmRubricProvider.callApi` | 모델 문자열은 각 파일 상수. `gpt-6-sol`·`gemini-3.8-flash` 등은 코드에 적힌 값이며 실제 모델 존재 여부는 미확인 |
| R-09 | C-03; `defaults.ts:174-187`, `:188-194`, `:213-219`, `:220-226` | 코드 확인 |
| R-10 | `defaults.ts:241-244`; `src/matchers/moderation.ts:33-50` | Replicate 분기는 `getEnvString` 직접 사용(`resolveProviderApiKey` 아님) |
| R-11 | C-02 `:246-257`; 호출 지점 `grep`: `src/` 아래 정의 외 호출 없음, 호출은 `test/commands/eval.gradingOwnership.test.ts:110`·`test/providers/defaults.test.ts` | `src/index.ts` export에 없음(검색) |
| R-12, R-14, R-15, R-16 | C-07 | 코드 확인. 폴백 후보의 `simulated-user` 판정은 `providers.ts:182-203` |
| R-13 | C-08, C-09; `src/evaluator.ts:3049-3077` `prepareTestCaseForEval`, `:2915-2940` `mergeScenarioTest` | 문서(`model-graded/index.md:225-262`)는 폴백이 `--grader`, `assertion.provider`, `test.options.provider`/`defaultTest.options.provider` 뒤에 온다고만 쓰고 이 셋 사이의 우선순위는 명시하지 않는다. R-13의 순서는 구현에서 도출했다 |
| R-17 | `src/matchers/rubric.ts:905-913`; `llmGrading.ts:343-347`, `:402-406`, `:467-471`; `comparison.ts:27-32`; `rag.ts:41-56`, `:165-169`, `:278-282`, `:412-416`; `similarity.ts:217-223`; `classification.ts:24-29`; `external/matchers/deepeval.ts:42`, `external/assertions/deepeval.ts:96` | deepeval 호출 지점은 `gradingProvider` 인자만 확인 |
| R-18 | `src/suggestions.ts:59`; `src/optimizer/promptOptimizer.ts:214`; `src/commands/optimize.ts:143-156` | 코드 확인 |
| R-19 | `src/testCase/synthesis.ts:204-209`; `src/assertions/synthesis.ts:455-460`; `src/commands/generate/dataset.ts:143-145`, `assertions.ts:155-157` | **문서와 구현 차이**: CLI 도움말은 "Defaults to the default grading provider"이나 구현은 `synthesizeProvider` |
| R-20 | `getDefaultProviders`·`getGradingProvider` 시그니처(C-02, C-07); `src/assertions/index.ts:621-628` `providerCallContext.originalProvider` | 부재 증명은 시그니처 읽기로 한계 있음 |
| R-21 | `src/providers/openai/defaults.ts:27-40`; `src/providers/anthropic/defaults.ts:21-23`, `:107-115`; `src/providers/openai/codexDefaults.ts:88`, `:346-363` | 코드 확인 |
| R-22 | `src/matchers/search.ts:36-62`; `src/providers/webSearchUtils.ts:129-200`; `src/matchers/agent.ts:32-35` | `hasWebSearchCapability` 세부 판정은 일부만 읽음 |
| R-23 | `src/matchers/llmGrading.ts:198-225` | `shouldGenerateRemote` 미읽음 |
| T-01 ~ T-20 | 위 R-ID의 근거 | 전부 구현에서 도출. 테스트 파일명만 확인(`test/providers/defaults.test.ts` 사례명: Mistral/xAI/Codex/AI Studio/Azure 선택, 우선순위, 마스킹), 사례 본문은 열지 않았다 |
| 문서와 구현 차이 | ① R-19: 위. ② 문서 `model-graded/index.md:229`의 "OpenAI, Anthropic, Gemini, Mistral, Azure OpenAI, Codex login"은 활성 계열을 나열할 뿐 우선순위는 쓰지 않는다. 구현의 우선순위는 R-02다. ③ R-13: `load.ts:1294-1300`만 읽으면 설정 파일의 `defaultTest.options.provider`가 `--grader`를 이기는 것처럼 보이나 `doEval.ts:788-803`이 나중에 덮어써 CLI가 이긴다. | 코드 확인 |

### 2.2 코드 읽는 순서 [선택]

1. `src/providers/defaults.ts` 전체(259줄)와 `credentials.ts`·`env.ts`로 선택 사다리와 키 판정을 본다.
2. 계열별 `defaults.ts`(OpenAI, Anthropic, Mistral, xAI, AI Studio, Vertex)로 모델·칸을 본다. Codex는 `openai/codexDefaults.ts`의 `getCodexDefaultProviders`(365줄~)만 보면 된다(앞 300줄은 인스턴스 수명 관리).
3. 소비처: `matchers/providers.ts`(grader 해석), `matchers/rubric.ts:876-` `runJsonGradingPrompt`, 각 `matchers/*.ts`의 `getAndCheckProvider` 호출.
4. 설정 주입: `assertions/utils.ts` `getFinalTest`, `node/doEval.ts:788-803`, `evaluator.ts:3049-3077`.

### 2.3 비교·재사용 출처 [선택]

없음(다른 레포의 같은 기능 스펙 없음). 원본 코드를 복사하지 않았다.

## 적용 메모 [선택]

SKILL.md를 여러 모델로 평가하고 모델 적합도를 기록하는 환경에서 가져올 때의 점검 사항이다. 원본 동작이 아니라 우리 쪽 결정 후보이며, 원본의 미결정을 해소한 것이 아니다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-04, R-20 | grader는 원본에서 키 조합이 정한다. 평가 대상과 같은 계열이 될 수 있다(예: Anthropic 키만 있고 대상이 Claude이면 judge도 `claude-sonnet-5`). 자기 채점 편향을 막으려면 judge를 키에 맡기지 말고 평가 설정에서 명시하고, 대상 계열과 겹치면 경고하거나 거부하는 검사를 추가한다 | 원본에는 계열 비교 코드가 없다 | judge 해석 앞에 "대상 계열 ≠ judge 계열" 검사. 원본의 T-02·T-03에 대응하는 대체 사례 필요 |
| R-15 | `defaultTest.provider`가 grader로 새는 폴백은 가져오지 않는다 | 대상이 judge가 되는 암묵 경로다. 원본 문서도 경고 | 폴백 단계 제거. T-12 대신 "judge 미지정이면 오류" |
| R-13, R-18 | `--grader`는 `optimize`·`--suggest-prompts`에 영향이 없다. 개선 루프에서 제안 모델도 명시 선택하게 하려면 제안 provider 옵션이 필요하다 | 원본에는 제안 모델 지정 수단이 없다 | `suggestions` 역할에 provider 설정 입력 추가 |
| R-09, R-10 | 비OpenAI 계열에서도 임베딩·moderation은 OpenAI 객체로 남는다. 우리 환경이 임베딩·moderation을 쓰지 않으면 이 칸은 가져오지 않는다 | 키 부재 시 사용 시점에 실패 | 8칸 중 completion 칸만 유지 |
