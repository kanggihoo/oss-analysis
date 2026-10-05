# ai 03-3: OpenAI 계열 통신 코드 세 가지의 차이 — `openai-completions` / `openai-responses` / `openai-codex-responses`

- **기준 commit**: `3874b3e98` / **분석일**: 2026-10-05
- **선행 문서**: [03-1-api-anthropic](./03-1-api-anthropic.md)(Claude, 같은 뼈대), [03-2-api-openai-responses](./03-2-api-openai-responses.md)(현재 경로), [03-4-api-openai-codex-legacy](./03-4-api-openai-codex-legacy.md)(legacy Codex 상세), [01-types](./01-types.md) §2.6(compat), [02-models-registry](./02-models-registry.md) §3(`createProvider`)
- **읽은 파일**: `api/openai-completions.ts`(1726줄 전체), `api/openai-responses.ts`(415줄 전체), `api/openai-codex-responses.ts`(1697줄 전체), `api/openai-responses-shared.ts`(`processResponsesStream`과 `mapStopReason`, `:433-809`). 줄 번호는 모두 이 commit 기준이다.
- **검증 수준**: 코드 읽기는 `코드 확인`. 자동 설정 감지(`detectCompat`)는 줄 범위 그대로 복사해서 돌렸다(`실행 확인`, §6). 모델 데이터는 02에서 `hydrate-model-data`로 만든 JSON(2026-10-04 생성)을 집계했다(`실행 확인`). **실제 서버와 통신해서 확인한 것은 없다**(`미확인`).

## 0. 한 줄 답
세 파일은 모두 "OpenAI 쪽 서버와 통신하는 코드"이지만 **서버의 API 종류가 다르다.**

| 파일 | 상대 서버의 API | 한 줄 성격 |
|---|---|---|
| `openai-completions.ts` | **Chat Completions** (`messages` 배열로 주고받는 방식) | **OpenAI 호환을 표방하는 여러 서버**를 하나의 코드로 처리하는 범용 코드. 서버마다 다른 점이 많아 compat 처리가 크다. |
| `openai-responses.ts` | **Responses** (`input` 항목과 종류가 정해진 `response.*` 이벤트로 주고받는 방식) | OpenAI 공식 최신 API용. SDK를 쓰고 단순하다. |
| `openai-codex-responses.ts` | **ChatGPT 구독의 Codex 백엔드**(`chatgpt.com/backend-api`) | Responses와 비슷한 프로토콜을 SDK 없이 직접 통신. WebSocket 우선. |

README도 같은 구분을 적는다: "Anthropic models use `anthropic-messages`, OpenAI uses `openai-responses`, while xAI, Groq, Cerebras, OpenRouter, and most others share `openai-completions`"(`README.md:241`).

## 1. 누가 어느 코드를 쓰는가 (실제 모델 데이터 집계)
02 §6에서 만든 JSON을 `api`별로 모아서 센 것이다(2026-10-04 시점, `chat` 모델만).

| `api` | provider 수 | 모델 수 | provider (모델 수 많은 순) |
|---|---|---|---|
| `openai-completions` | 26 | 716 | openrouter(385), huggingface(76), opencode(26), baseten(22), nvidia(21), qwen-token-plan-cn(20), qwen-token-plan(20), opencode-go(19), cloudflare-ai-gateway(18), cloudflare-workers-ai(18), together(17), … 그 외 15개 |
| `openai-responses` | 7 | 131 | **openai(44)**, opencode(30), cloudflare-ai-gateway(24), github-copilot(18), opencode-go(6), meta(5), xai(4) |
| `openai-codex-responses` | 1 | 9 | **openai-codex(9)** |
| (참고) `azure-openai-responses` | 1 | 44 | azure-openai-responses(44). 별도 파일(`azure-openai-responses.ts`, 351줄)이며 공용 변환기를 쓴다(`:22`). 이 문서에서는 읽지 않았다. |

- **`openai`(OpenAI 본사)는 `openai-responses`다.** `completions`가 아니다.
- `openai-completions`는 **26개 provider에 걸쳐 716개 모델**을 맡는다. 가장 많은 모델을 처리하는 통신 코드다.
- 한 provider가 둘 이상을 쓰기도 한다: `opencode`는 `completions` 26개와 `responses` 30개, `github-copilot`은 `completions` 6개와 `responses` 18개(02 §3.2 대응표 구조).

## 2. 구조 비교

### 2.1 파일과 의존
| | completions | responses | codex |
|---|---|---|---|
| 줄 수 | 1726 | **415** | 1697 |
| 요청 보내기 | `openai` SDK (`client.chat.completions.create`, `:371`) | `openai` SDK (`client.responses.create`, `openai-responses.ts:184`) | **SDK 없음.** `fetch`(`:400`)와 `WebSocket`(`:1096`) |
| 응답 읽기 | SDK가 주는 `ChatCompletionChunk` 스트림을 파일 안의 `for await`(`:553`)가 직접 해석 | SDK 스트림을 **공용** `processResponsesStream`에 넘김 | 직접 만든 `parseSSE`/`parseWebSocket` + 공용 `processResponsesStream` |
| 메시지 변환 | 파일 안 `convertMessages`(`:1185-1472`) | **공용** `convertResponsesMessages` | **공용** `convertResponsesMessages` (+ `includeSystemPrompt: false`) |
| 재시도 | 공용 `retryProviderRequest` | 공용 `retryProviderRequest` | **자체 구현**(03-4 §6.2) |

- `openai-responses-shared.ts`(809줄)는 **Responses 계열(responses, codex, azure)이 함께 쓰는 변환기**다. `completions`는 이것을 쓰지 않고 변환과 해석을 모두 자기 파일에 가진다.
- 그래서 `openai-responses.ts`는 415줄로 짧고(요청 준비만 하고 나머지는 공용), `completions`와 `codex`는 각자 1700줄대다. 단 길어진 이유는 서로 다르다(§0의 성격 참고: completions는 서버 방언, codex는 WebSocket).

### 2.2 모두 같은 뼈대
세 파일 모두 03-1에서 정리한 뼈대를 따른다(`new AssistantMessageEventStream()` → `(async () => { try { ... } catch { ... } })()` → `return stream`). 코드 위치만 적는다.
| | `stream` 시작 | `return stream` | `start` push | `done` push | `error` push |
|---|---|---|---|---|---|
| completions | `:299` | `:728` | `:379` | `:700-701` | `:723-724` |
| responses | `:127` | `:235` | `:192` | `:212-213` | `:230-231` |
| codex | `:237` | `:497` | `:319`(WS), `:473`(SSE) | `:334-339`, `:482-483` | `:492-493` |

## 3. 요청이 어떻게 다른가

### 3.1 한 장 표
| | completions | responses | codex |
|---|---|---|---|
| 대화 필드 | `messages: [...]` | `input: [...]` | `input: [...]` |
| 시스템 프롬프트 | `messages` 안의 `developer` 또는 `system` 메시지 (`:1225`, `:1249-1252`) | `input` 안의 메시지(변환기가 처리) | **`instructions` 필드** (`:551-557`) |
| 최대 출력 | `max_completion_tokens` 또는 `max_tokens`(compat로 선택, `:837-844`) | `max_output_tokens`, 최소 16 (`:340-342`) | **보내지 않음** |
| 스트리밍 | `stream: true` + (지원하면) `stream_options: { include_usage: true }` (`:818-831`) | `stream: true` | `stream: true` |
| 저장 안 함 | `store: false`, **compat가 허용할 때만** (`:833-835`) | `store: false` 항상 (`:337`) | `store: false` 항상 (`:555`) |
| 프롬프트 캐시 | `prompt_cache_key`(조건부), `prompt_cache_retention: "24h"` (`:821-826`), Anthropic식 `cache_control` 표시(compat, `:860-862`) | `prompt_cache_key`, `prompt_cache_retention`/`prompt_cache_options` (`:334-336`) | `prompt_cache_key`(세션 ID) |
| 추론 설정 | **`thinkingFormat` 11가지에 따라 다른 필드** (§3.2) | `reasoning: { effort, summary }` + `include: ["reasoning.encrypted_content"]` (`:363-379`) | 위와 같음 + `text.verbosity`, 항상 `include` (`:559-597`) |
| 도구 형식 | `tools: [{ type: "function", function: { name, description, parameters, strict? } }]` 또는 문법 제약 `type: "custom"` (`:1474-1509`) | `convertResponsesTools` (공용, 모양은 읽지 않음) | 위와 같음 |
| 도구 호출 병렬 | 지정하지 않음 | 지정하지 않음 | `parallel_tool_calls: true` (`:563`) |
| 전송 | SSE | SSE | **WebSocket 우선**, SSE 폴백 (03-4 §5) |
| 이어 붙이기(`previous_response_id`) | 없음 | 없음 | WebSocket에서만, 서버가 지원할 때 (03-4 §5.2) |

### 3.2 completions의 추론 설정이 길어지는 이유 (`:875-972`)
`reasoning: "high"` 같은 pi의 통일된 값을 **서버가 받는 형식**으로 바꾸는 부분인데, 서버마다 형식이 달라서 `thinkingFormat`별로 갈라진다.

| `thinkingFormat` | 요청에 들어가는 모양 |
|---|---|
| `openai` (기본) | `reasoning_effort: "<값>"` (`:964-966`) |
| `openrouter` | `reasoning: { effort }` (`:933-942`) |
| `deepseek` | `thinking: { type: "enabled" \| "disabled" }` + `reasoning_effort` (`:923-932`) |
| `zai` | `thinking: { type, clear_thinking }` (`:875-887`) |
| `qwen` | 최상위 `enable_thinking: boolean` (`:888-895`) |
| `qwen-chat-template` | `chat_template_kwargs: { enable_thinking, preserve_thinking }` (`:896-900`) |
| `chat-template` | 설정으로 지정한 `chat_template_kwargs` (`:901-905`) |
| `baseten` | `chat_template_args` + `reasoning_effort` (`:906-922`) |
| `together` | `reasoning: { enabled }` + `reasoning_effort` (`:948-956`) |
| `string-thinking` | 최상위 `thinking: "<문자열>"` (`:957-963`) |
| `ant-ling` | `reasoning: { effort }` (`:943-947`) |

추가로 추론에 쓸 토큰 상한을 따로 걸 수 있다(`thinkingTokenBudgetField`, `:974-980`). 이유는 코드 주석에 있다: "추론과 답변이 `max_tokens`를 나눠 쓰므로, 상한이 없으면 추론이 응답 전체를 써 버려서 답과 도구 호출이 없을 수 있다."

반면 `responses`와 `codex`는 `reasoning: { effort, summary }` **한 가지 형식**이다. 이것이 두 파일의 가장 큰 크기 차이를 만든다.

### 3.3 메시지 변환의 차이 (completions, `:1185-1472`)
같은 `Message`를 Chat Completions 형식으로 바꿀 때 서버 방언에 맞추는 규칙들이다. 각 규칙은 compat 값으로 켜고 끈다.
| 규칙 | 줄 | 설명 |
|---|---|---|
| **지침 역할** | `:1225` | 추론 모델이고 `supportsDeveloperRole`이면 `developer`, 아니면 `system` |
| **도구 호출 ID 정규화** | `:1194-1218` | Responses 계열이 만든 `call_id|item_id` 형식의 긴 ID(400자 이상, 특수문자)를 `call_id_item_id`로 바꾸고 40자로 줄인다(넘으면 해시). OpenAI는 40자로 자른다. **모델을 Responses 계열에서 completions 계열로 바꿔도 이전 도구 호출이 이어진다**(01의 hand-off). |
| **도구 결과 뒤 보강** | `:1233-1238` | `requiresAssistantAfterToolResult`이면 도구 결과 직후 `user`가 오기 전에 가짜 `assistant` 메시지 `"I have processed the tool results."`를 끼워 넣는다. |
| **assistant 내용은 문자열** | `:1322-1329` | 배열(`[{type:"text",...}]`)이 아니라 문자열로 보낸다. 주석: 배열로 보내면 DeepSeek V3.2(NVIDIA NIM) 같은 모델이 그 구조를 그대로 흉내 내서 출력이 재귀적으로 중첩된다. |
| **추론 내용 되돌리기** | `:1302-1341` | 이전 응답의 추론을 다음 요청에 돌려보낼 때: `requiresThinkingAsText`이면 일반 글로, 아니면 응답에서 쓴 필드 이름(`reasoning_content`, `reasoning`, `reasoning_text`)이나 `reasoning_details`로 돌려보낸다. |
| **빈 `assistant` 건너뛰기** | `:1385-1396` | 내용도 도구 호출도 없는 `assistant`(중단된 응답)는 뺀다. |
| **도구 결과 이름** | `:1421-1423` | `requiresToolResultName`이면 `name` 필드를 넣는다. |
| **도구 결과의 이미지** | `:1426-1459` | 도구 결과는 글만 보내고, 이미지는 별도의 `user` 메시지(`"Attached image(s) from tool result:"`)로 보낸다. |
| **도구 목록 비어 있을 때** | `:855-858` | 대화에 도구 호출 기록이 있는데 도구가 없으면 `tools: []`를 보낸다. 주석: LiteLLM 같은 프록시 뒤의 Anthropic이 요구한다. |

## 4. 응답이 어떻게 다른가

### 4.1 이벤트 모양
| | completions (`ChatCompletionChunk`) | responses / codex (`response.*` 이벤트) |
|---|---|---|
| 구조 | 조각 하나가 `choices[0].delta`와 `finish_reason`을 가진다. **이벤트 종류가 따로 없다.** | `response.output_text.delta`, `response.function_call_arguments.delta`, `response.output_item.done` 등 **종류가 정해진 이벤트** (03-2 §5.1) |
| 글 | `delta.content` (`:586-600`) | `response.output_text.delta` |
| 추론 | `delta.reasoning_content` / `reasoning` / `reasoning_text` 중 **첫 번째 비어 있지 않은 것**(중복 방지, `:602-633`), 또는 `reasoning_details` (`:665-676`) | `response.reasoning_summary_text.delta` 등 |
| 도구 호출 | `delta.tool_calls[]`를 `index`나 `id`로 이어 붙임 (`:635-663`, `ensureToolCallBlock` `:494-551`) | `response.function_call_arguments.delta` |
| 사용량 | 조각의 `usage`(`stream_options`로 요청) (`:563-574`) | `response.completed`의 `usage` |
| 종료 | `finish_reason` 필드 (`:576-584`) | `response.completed`/`incomplete`의 `status` |

### 4.2 completions에서 눈에 띄는 점 두 가지 (`코드 확인`)
**(1) `*_end` 이벤트가 모든 블록에 대해 스트림이 끝난 뒤 한꺼번에 나온다.** Chat Completions에는 "이 블록이 끝났다"는 신호가 없어서, 반복문이 끝난 뒤 `for (const block of blocks) finishBlock(block)`(`:680-682`)에서 `text_end`, `thinking_end`, `toolcall_end`를 한꺼번에 낸다. Claude(블록마다 `content_block_stop`)와 Responses(블록마다 `output_item.done`)는 블록이 끝나는 즉시 `*_end`를 낸다. 호출한 쪽에서는 completions의 도구 호출이 **응답 끝에서야 확정**된다는 뜻이다.

**(2) 글 블록과 추론 블록이 각각 하나뿐이다.** `textBlock`, `thinkingBlock` 변수가 하나씩이고(`:398-399`) `ensureTextBlock`/`ensureThinkingBlock`이 이미 있으면 재사용한다(`:474-493`). 글과 추론이 번갈아 와도 각각 한 블록에 이어 붙는다. 도구 호출만 여러 블록이 된다.

### 4.3 종료 사유 변환
| | completions (`mapStopReason` `:1554-1578`) | responses / codex (공용 `mapStopReason`) |
|---|---|---|
| 정상 | `stop`, `end` → `stop` | `completed` → `stop` |
| 길이 초과 | `length` → `length` | `incomplete` + `max_output_tokens` → `length` |
| 도구 호출 | **`tool_calls`, `function_call` → `toolUse`** (서버가 알려 줌) | 상태에는 없어서 **도구 호출이 있으면 pi가 `toolUse`로 보정** |
| 오류 | `content_filter`, `network_error`, 그 외 → `error` | `failed`, `cancelled`, 그 외 `incomplete` → `error` |

`finish_reason`을 보내지 않는 서버를 위한 처리도 있다: `compat.supportsFinishReason`이 `false`이면 도구 호출이 있으면 `toolUse`, 없으면 `stop`으로 **추정**한다(`:690-692`). `true`인데 끝까지 안 오면 "Stream ended without finish_reason"으로 실패한다(`:696-698`).

### 4.4 사용량
- completions의 `parseChunkUsage`(`:1511-1552`)는 서버마다 캐시 토큰을 다른 이름으로 주는 것을 한곳에서 흡수한다: `prompt_tokens_details.cached_tokens`(OpenAI, OpenRouter), `prompt_cache_hit_tokens`(DeepSeek), 최상위 `cached_tokens`(Kimi). 일부 서버(Moonshot)는 `usage`를 `choice.usage`에 넣어서 그것도 읽는다(`:570-574`). 그 안에서 `calculateCost`를 부른다(`:1550`).
- responses와 codex는 `response.completed`에서 `input_tokens - cached - cache_write`로 계산하고 `calculateCost`를 한 번 부른다(03-2 §5.3, 03-4 §7.3).

## 5. 오류와 마무리
세 파일 모두 `catch`에서 `stopReason`을 정하고 `error` 이벤트를 push한 뒤 `end()`한다. 오류 문구 정리는 `formatProviderError(normalizeProviderError(error))`이고, completions는 OpenRouter가 `error.metadata.raw`에 주는 추가 정보를 덧붙인다(`:715-722`). responses는 provider 이름을 붙이고 ChatGPT 사용 한도 안내를 더한다(`:222-229`).

## 6. compat 자동 감지: 서버가 달라도 한 코드로 (`코드 확인`, `실행 확인`)
completions 코드가 서버마다 다른 점을 처리하는 방식이다. 01 §2.6에서 "미지정이면 baseUrl로 자동 감지한다"고 한 부분이 이 코드다.

### 6.1 두 단계 (`:1585-1726`)
```
getCompat(model)
 ① detectCompat(model)      provider 이름과 baseUrl 문자열을 보고 기본 설정을 정한다     (:1585-1682)
 ② model.compat 이 있으면, 필드마다 model.compat 값 ?? 감지한 값                         (:1688-1726)
```
- `model.compat`이 **필드 단위로** 감지 결과를 덮어쓴다(`??`).
- 감지는 `provider === "deepseek"` 같은 이름 비교와 `baseUrl.includes("api.deepseek.com")` 같은 주소 포함 검사로 한다. 호출마다 다시 계산한다(`getCompat`을 `:305`, `:337` 등에서 부름).

### 6.2 감지 결과가 어떻게 갈리는가
`detectCompat`이 따로 처리하는 서버들(`:1589-1603`)을 기준으로 정해지는 설정이다.
| 설정 | 정해지는 방식 |
|---|---|
| `supportsStore`, `supportsDeveloperRole` | "비표준" 서버 목록(NVIDIA, Cerebras, xAI, Together, DeepSeek, Z.ai, Moonshot, Cloudflare, OpenCode, Ant Ling 등)이면 `false`. OpenRouter는 `developer` 역할이 `false`이지만 모델 id가 `anthropic/` 또는 `openai/`로 시작하면 `true` |
| `maxTokensField` | DeepSeek, Moonshot, Together, NVIDIA, Z.ai, Cloudflare AI Gateway, Ant Ling, chutes.ai는 `max_tokens`, 나머지는 `max_completion_tokens` |
| `supportsReasoningEffort` | xAI(Grok), Z.ai, Moonshot, Together, Cloudflare AI Gateway, NVIDIA, Ant Ling이면 `false` |
| `thinkingFormat` | DeepSeek `deepseek`, Z.ai `zai`, Together `together`, Ant Ling `ant-ling`, OpenRouter `openrouter`, 그 외 `openai` |
| `requiresReasoningContentOnAssistantMessages` | DeepSeek만 `true` |
| `cacheControlFormat` | OpenRouter이고 모델 id가 `anthropic/`로 시작하면 `"anthropic"` |
| `sendSessionAffinityHeaders` | OpenRouter만 `true` |
| `supportsLongCacheRetention` | Together, Cloudflare, NVIDIA, Ant Ling은 `false` |
| `supportsStrictMode`, `supportsOpenAIGrammarTools`, `supportsMidConvo*` | 기본 `false` (주석: "OpenAI 호환만으로는 엄격한 JSON 스키마 도구를 지원한다고 볼 수 없다") |

### 6.3 실험: 같은 코드에 서로 다른 모델을 넣어 보기
`detectCompat`과 `getCompat`(`:1585-1726`)을 그대로 복사해서 네 가지 모델 정보를 넣었다(`artifacts/pi/ai-demos/completions-compat-demo.ts`, 로그 `completions-compat-demo.2026-10-05.log`).

| 설정 | OpenAI (`api.openai.com`) | DeepSeek | OpenRouter + `anthropic/` 모델 | 알 수 없는 로컬 서버 |
|---|---|---|---|---|
| `supportsStore` | true | **false** | true | true |
| `supportsDeveloperRole` | true | **false** | true | true |
| `supportsReasoningEffort` | true | true | true | true |
| `maxTokensField` | max_completion_tokens | **max_tokens** | max_completion_tokens | max_completion_tokens |
| `thinkingFormat` | openai | **deepseek** | **openrouter** | openai |
| `requiresReasoningContentOnAssistantMessages` | false | **true** | false | false |
| `supportsStrictMode` | false | false | false | false |
| `cacheControlFormat` | (없음) | (없음) | **anthropic** | (없음) |
| `sendSessionAffinityHeaders` | false | false | **true** | false |
| `supportsLongCacheRetention` | true | true | true | true |

- 위 표는 **`model.compat` 없이** `provider`와 `baseUrl`만으로 정한 결과다.
- **알 수 없는 로컬 서버는 OpenAI와 같은 설정이 된다.** 이름이나 주소가 위 목록에 없으면 "OpenAI 표준과 같다"고 가정한다. 로컬 서버가 다르게 동작하면 `model.compat`으로 알려 주어야 한다(실험에서 `{ maxTokensField: "max_tokens", supportsStrictMode: true }`를 주면 두 값이 그대로 덮어써졌다).
- 이 실험은 감지 코드만 돌린 것이다. 감지된 값이 실제 요청에 쓰이는 곳은 §3의 `buildParams`와 `convertMessages`다.

## 7. 정리: 무엇을 쓰는가 / 왜 이렇게 나뉘어 있나
| 질문 | 답 |
|---|---|
| OpenAI 본사의 모델을 API 키로 쓰면? | `openai` provider → `openai-responses` |
| ChatGPT 구독으로 Codex 모델을 쓰면? | `openai-codex` provider(legacy) → `openai-codex-responses` |
| OpenRouter, DeepSeek, 로컬 서버, 대부분의 서드파티는? | `openai-completions` + compat로 방언 처리 |
| 한 provider 안에서 섞이는 경우는? | GitHub Copilot, OpenCode 등은 모델마다 다른 `api`(02 §3.2) |

**왜 두 개의 OpenAI 계열 방식(`completions`, `responses`)이 따로 있는가**
- 코드 쪽 사실: 모델 데이터의 `api` 값이 모델마다 `openai-completions` 또는 `openai-responses`로 정해져 있고(§1), 두 코드는 요청 필드와 응답 이벤트 모양이 완전히 다르다(§3, §4).
- 서드파티 서버 다수가 Chat Completions를 흉내 낸다는 점은 README(`:241`)와 `detectCompat`의 서버 목록에서 확인된다. Responses를 지원하는 서버는 데이터상 7개 provider뿐이다(§1).
- 이 두 API가 OpenAI 안에서 어떤 관계인지(어느 쪽이 새것인지 등)는 이 저장소의 코드와 문서로는 직접 확인되지 않는다(`미확인`).

**읽는 순서 제안**: 응답 해석이 가장 단순한 `openai-responses.ts`(415줄)를 먼저 보고, 변환 규칙은 공용 `openai-responses-shared.ts`에서 보고, `openai-completions.ts`는 compat가 왜 필요한지 이해한 뒤 `detectCompat`부터 읽는 것이 좋다.

## 8. 읽지 않은 것 (`미확인`)
- `openai-responses-shared.ts`의 `convertResponsesMessages`, `convertResponsesTools`(`:145-410`): Responses 계열의 요청 변환 규칙
- `azure-openai-responses.ts`(351줄)
- `completions`의 `reasoning_details` 처리(OpenRouter 전용 재생 데이터) 세부, `constrained-sampling.ts`, `openai-prompt-cache.ts`
- 모델 JSON 안의 모델별 `compat` 값이 `detectCompat`과 얼마나 다른지(02에서 Opus 5.5 한 건만 확인함)
- 실제 서버와의 통신
