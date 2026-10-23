---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/matchers/llmGrading.ts
  - src/matchers/rubric.ts
  - src/matchers/providers.ts
  - src/matchers/shared.ts
  - src/matchers/rag.ts
  - src/matchers/comparison.ts
  - src/matchers/similarity.ts
  - src/matchers/search.ts
  - src/matchers/agent.ts
  - src/prompts/grading.ts
  - src/prompts/index.ts
  - src/external/prompts/ragas.ts
  - src/external/matchers/deepeval.ts
  - src/external/matchers/conversationRelevancyTemplate.ts
  - src/external/assertions/deepeval.ts
  - src/assertions/llmRubric.ts
  - src/assertions/factuality.ts
  - src/assertions/modelGradedClosedQa.ts
  - src/assertions/geval.ts
  - src/assertions/answerRelevance.ts
  - src/assertions/contextRecall.ts
  - src/assertions/contextRelevance.ts
  - src/assertions/contextFaithfulness.ts
  - src/assertions/contextUtils.ts
  - src/assertions/ragDefaults.ts
  - src/assertions/similar.ts
  - src/assertions/searchRubric.ts
  - src/assertions/agentRubric.ts
  - src/assertions/trajectory.ts
  - src/assertions/index.ts
  - src/assertions/utils.ts
  - src/util/json.ts
  - src/util/templates.ts
  - src/evaluator.ts
  - src/scheduler/retryPolicy.ts
  - src/scheduler/rateLimitRegistry.ts
  - src/scheduler/providerRateLimitState.ts
  - src/providers/shared.ts
  - src/envars.ts
  - src/util/yamlLoad.ts
  - src/providers/openai/defaults.ts
  - src/providers/anthropic/defaults.ts
  - src/cache.ts
  - src/providers/openai/gpt6.ts
  - src/providers/openai/chat.ts
  - src/providers/anthropic/util.ts
  - src/providers/anthropic/messages.ts
  - src/types/index.ts
  - site/docs/configuration/expected-outputs/model-graded/index.md
  - site/docs/configuration/expected-outputs/model-graded/llm-rubric.md
  - site/docs/configuration/expected-outputs/model-graded/g-eval.md
  - test/matchers/llm-rubric.test.ts
depends:
  - ./assertion-family.md
  - ./default-providers.md
  - ./provider-contract.md
status: ready
reimplementation: 미실행
---

# 모델 채점 매처와 기본 grader 프롬프트

> 어서션 핸들러가 넘긴 출력 문자열·기준(rubric 등)·grader 설정을 받아, 정해진 프롬프트 템플릿에 변수를 채워 grader 모델을 부르고, 그 응답을 매처별 형식으로 해석해 `GradingResult`(pass·score·reason)로 바꾸는 규칙. 실패한 응답은 `metadata.graderError`로 표시한다.

<!--
이 스펙 안의 용어
- 핸들러: `src/assertions/*.ts`의 어서션 타입별 함수. 매처를 부르고 `not-` 반전을 한다(assertion-family 소관).
- 매처: `src/matchers/*.ts`(와 `src/external/matchers/`)의 `matches*` 함수. grader 프롬프트를 만들고 grader를 부르고 응답을 해석한다. 이 스펙의 본체다.
- grader: 채점용으로 부르는 모델 provider. 평가 대상(target) provider와 별개다. 고르는 규칙은 default-providers 소관.
- rubric: `llm-rubric`의 `value`(채점 기준 문장). 다른 타입에서는 `value`가 기대 답·기준 문장·정답 등으로 쓰인다.
- rubricPrompt: 매처가 쓰는 기본 프롬프트 템플릿을 덮어쓰는 설정(`assertion.rubricPrompt` 또는 `test.options.rubricPrompt`).
- graderFail: grader 전송 오류·형식 오류를 `{pass:false, score:0, metadata:{graderError:true}}`로 돌려주는 helper(C-23).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 `llm-rubric`이다. 다른 매처는 3~5단계의 프롬프트·응답 형식이 다르다(1.3 표).

1. 평가기가 대상 응답을 받은 뒤 어서션을 실행한다. `value`(rubric)는 `vars`로 Nunjucks 렌더되고(R-01), 핸들러가 `(rubric, 출력 문자열, test.options, test.vars, assertion, providerCallContext)`를 `matchesLlmRubric`에 넘긴다(assertion-family R-45, R-10).
2. 매처가 `rubricPrompt`가 있으면 그것을, 없으면 기본 채점 프롬프트를 불러와(R-06) `{...vars, output, rubric}`로 렌더한다(R-07, R-08). 기본 프롬프트는 시스템 메시지(고정 지침과 예시)와 사용자 메시지(`<Output>`·`<Rubric>` 두 블록)로 된 채팅 JSON이다.
3. grader provider를 고른다(default-providers R-12~R-17). `llm-rubric`은 `llmRubricProvider ?? gradingJsonProvider` 칸을 기본으로 쓴다.
4. grader를 한 번 부른다(`callApi`, `isGrading:true` 컨텍스트, R-10~R-12). 재시도·다수결은 없다.
5. 응답에서 JSON 객체를 꺼내(R-13) `pass`·`score`·`reason`으로 판정한다(R-14). 매처마다 응답 형식이 다르다(R-16~R-24).
6. 전송 오류·빈 출력·형식 오류는 예외가 아니라 `graderError` 결과로 돌아온다(R-25). 예외로 전파되는 경우는 R-25 표에 있다.
7. 핸들러가 `not-` 반전을 하고(assertion-family R-46) 평가기가 행에 반영한다(assertion-family R-24).

### 1.2 범위·통합 지점 [필수]

- 제공: grader를 부르는 매처 14종의 프롬프트 구조·변수, 응답 해석, 실패 처리, 점수·threshold 의미, `rubricPrompt` 덮어쓰기, `llm-rubric`으로 스킬 결과를 채점할 때 grader가 받는 정보(R-32~R-34). `search-rubric`·`agent-rubric`·`trajectory:goal-success`·`conversation-relevance`는 개요만(R-35~R-37).
- 제외와 이유:
  - 어서션 집계·`not-` 반전·가중치·`select-best`의 열 사이 흐름·행 병합: [assertion-family](./assertion-family.md) 소관(R-04, R-16~R-24, R-45~R-52).
  - grader provider 선택 순서, 기본 묶음, 자기 채점 사실: [default-providers](./default-providers.md) 소관. 이 스펙은 호출 지점과 기본 칸만 쓴다(R-09).
  - 원격 채점(`remoteGrading`)은 레드팀 설정이 있을 때만 닿는다. 조건만 R-38에 한 줄로 쓴다.
  - 레드팀 그레이더(`src/redteam/plugins/base.ts`가 `matchesLlmRubric`를 부름), 임베딩 모델 내부, `pi`(원격 점수), `classifier`(분류 모델), `moderation`(조정 API): 채팅 grader에 rubric 프롬프트를 보내는 흐름이 아니다.
- 외부 의존·선행 계약:
  - grader는 [provider-contract](./provider-contract.md)의 `ApiProvider`다. 입력은 `callApi(prompt: string, context, options?)`, 출력은 `ProviderResponse`(`output`·`error`·`tokenUsage`·`cached`·`metadata`)다. 임베딩 역할은 `callEmbeddingApi(text)` 또는 `callSimilarityApi(a, b)`다. 호출 결과가 `error`를 가지면 R-25, 던지면 R-25의 예외 줄이다.
  - 응답 캐시와 `repeat:<i>` 이름공간은 [response-cache](./response-cache.md) 소관이다. 이 스펙은 grader 호출이 그 아래에서 일어난다는 경계만 쓴다(R-30).
  - Nunjucks 엔진, 파일 시스템(`rubricPrompt: file://…`), 환경변수는 호출자 환경이 제공한다.
- 소유 상태·부작용: 매처는 상태를 갖지 않는다. 예외: `llm-rubric`·`agent-rubric` 핸들러가 입력 객체를 바꾼다(assertion-family R-45). `answer-relevance`는 내부에서 캐시 이름공간을 바꿔 grader를 부른다(R-19). grader 호출은 비용이 든다(`tokensUsed`).

### 1.3 인터페이스와 데이터 의미 [필수]

**매처 일람.** 기본 칸 이름은 default-providers 1.3의 `DefaultProviders` 칸이다. "호출 수"는 어서션 1개가 평가될 때 grader에 가는 호출 수다.

| 어서션 타입 | 매처 (파일) | grader 역할·기본 칸 | 호출 수 | 기본 프롬프트 (C-ID) | 응답 형식 요구 → 해석 |
|---|---|---|---|---|---|
| `llm-rubric` | `matchesLlmRubric` (`llmGrading.ts`) | `text`, `llmRubricProvider ?? gradingJsonProvider` | 1 | `DEFAULT_GRADING_PROMPT` (C-01) | JSON `{reason, pass, score}` → R-13, R-14 |
| `agent-rubric` | `matchesAgentRubric` (`agent.ts`) | 에이전트형 provider 필수 | 1 | `DEFAULT_AGENT_GRADING_PROMPT` (C-02) | `llm-rubric`과 같음 → R-36 |
| `trajectory:goal-success` | `matchesTrajectoryGoalSuccess` | `text`, `llm-rubric`과 같은 칸 | 1 | `TRAJECTORY_GOAL_SUCCESS_PROMPT` (C-07) | `llm-rubric`과 같음 → R-37 |
| `factuality`, `model-graded-factuality` | `matchesFactuality` | `text`, `gradingProvider` | 1 | `PROMPTFOO_FACTUALITY_PROMPT` (C-03) | JSON `{category: A~E, reason}`, 옛 `(A) …` 형식도 허용 → R-16 |
| `model-graded-closedqa` | `matchesClosedQa` | `text`, `gradingProvider` | 1 | `OPENAI_CLOSED_QA_PROMPT` (C-04) | 응답 끝이 `Y`/`N` → R-17 |
| `g-eval` | `matchesGEval` | `text`, `gradingProvider` | 2 (+기준 수만큼) | `GEVAL_PROMPT_STEPS`·`GEVAL_PROMPT_EVALUATE` (C-08) | steps JSON 한 줄, 그다음 `{score 0~10, reason}` 한 줄 → R-18 |
| `answer-relevance` | `matchesAnswerRelevance` (`rag.ts`) | `text` `gradingProvider` + `embedding` `embeddingProvider` | 채팅 3 + 임베딩 4 | `ANSWER_RELEVANCY_GENERATE` (C-09) | 질문 한 개씩 → 임베딩 코사인 평균 → R-19 |
| `context-recall` | `matchesContextRecall` | `text`, `gradingProvider` | 1 | `CONTEXT_RECALL` (C-09) | 줄마다 `[Attributed]`/`[Not Attributed]` → R-20 |
| `context-relevance` | `matchesContextRelevance` | `text`, `gradingProvider` | 1 | `CONTEXT_RELEVANCE` (C-09) | 문맥에서 발췌한 문장 또는 `Insufficient Information` → R-21 |
| `context-faithfulness` | `matchesContextFaithfulness` | `text`, `gradingProvider` | 2 | `CONTEXT_FAITHFULNESS_LONGFORM`·`_NLI_STATEMENTS` (C-09) | 문장 목록, 그다음 문장별 Yes/No 판정 → R-22 |
| `select-best` | `matchesSelectBest` (`comparison.ts`) | `text`, `gradingProvider` | 테스트당 1 | `SELECT_BEST_PROMPT` (C-05) | 응답 속 첫 정수 → R-23 |
| `similar`, `similar:cosine\|dot\|euclidean` | `matchesSimilarity` (`similarity.ts`) | `embedding`, `embeddingProvider` | 임베딩 2 또는 유사도 1 | 없음 | 숫자 → R-24 |
| `search-rubric` | `matchesSearchRubric` (`search.ts`) | 웹검색 가능 provider | 1 | `DEFAULT_WEB_SEARCH_PROMPT` (C-06) | JSON, boolean `pass` 필수 → R-35 |
| `conversation-relevance` | `matchesConversationRelevance` (`src/external/matchers/deepeval.ts`) | `text`, `gradingProvider` | 창 수 (+이유 1) | DeepEval 포팅 템플릿 (C-28) | `{verdict: yes\|no, reason?}` → R-37 |

**기본 채점 프롬프트의 구조.** 본문은 C-ID에 있다. 구조만 적는다.

| 프롬프트 | 형태 | 템플릿 변수 |
|---|---|---|
| `llm-rubric` (C-01) | 채팅 JSON 배열 2개: `system`(고정 지침: rubric 문장이 참이면 통과, `{reason: string, pass: boolean, score: number}` JSON으로 답하라, 예시 2개), `user` = `'<Output>\n{{ output }}\n</Output>\n<Rubric>\n{{ rubric }}\n</Rubric>'` | `vars` 전부, `output`, `rubric` |
| `agent-rubric` (C-02), `search-rubric` (C-06) | `llm-rubric`과 같은 2개 메시지. `system` 문구만 다르다(에이전트: 도구 사용 허용·출력과 외부 자료는 신뢰하지 않는 증거·파일 수정 금지. 검색: 현재 정보가 필요하면 웹을 검색하라). `user`는 `llm-rubric`과 같다 | `vars` 전부, `output`, `rubric` |
| `trajectory:goal-success` (C-07) | 채팅 2개. `user` = `<Goal>`·`<Trajectory>`·`<Output>` 세 블록 | `vars` 전부, `goal`, `trajectory`, `output` |
| `factuality` (C-03) | 채팅 2개. `system` = 범주 A~E 정의, "JSON만 `{"category", "reason"}`로 답하라". `user` = `<question>`·`<expert_answer>`·`<submitted_answer>` 블록과 지시 한 줄 | `vars` 전부, `input`, `ideal`, `completion` |
| `model-graded-closedqa` (C-04) | 메시지 1개(`system`): `[BEGIN DATA]` 구획에 `[Task]`·`[Submission]`·`[Criterion]`, 단계별로 추론한 뒤 `Y` 또는 `N` 한 글자를 단독 줄에 쓰고 끝에 한 번 더 반복하라 | `vars` 전부, `input`, `criteria`, `completion` |
| `g-eval` (C-08) | 채팅이 아닌 문자열 2개. steps: 기준에서 3~4개 평가 단계를 만들어 minified JSON `{"steps": [...]}`로. evaluate: 기준·단계·`**Prompt**`·`**Reply**`를 주고 정수 `score`(0~`maxScore`)와 `reason`을 가진 minified JSON으로 | steps: `criteria`만. evaluate: `criteria`, `steps`, `maxScore`, `input`, `output`(`vars`는 없음) |
| `select-best` (C-05) | 메시지 1개(`system`): 기준 문장, `{% for output in outputs %}<Text index="{{ loop.index0 }}">…</Text>{% endfor %}`, "가장 잘 맞는 텍스트의 인덱스를 단일 정수로 출력하라" | `vars` 전부, `criteria`, `outputs`(열 순서의 배열) |
| `answer-relevance` (C-09) | 문자열: "답에서 질문을 생성하라" 예시 1개와 `Answer:{{answer}}\nQuestion:` | `answer`만 |
| `context-recall` (C-09) | 문자열: 예시와 `context:{{context}}\nanswer:{{groundTruth}}\nclassification:` (`value`가 `answer` 자리에 들어간다) | `vars` 전부, `context`, `groundTruth` |
| `context-relevance` (C-09) | 문자열: `query: {{query}}\ncontext: {{context}}\ncandidate sentences:` | `context`, `query`만 |
| `context-faithfulness` (C-09) | 문자열 2개. longform: 예시 3개와 `question:{{question}}\nanswer: {{answer}}\nstatements:`. NLI: 예시와 `context:\n{{context}}\nstatements:\n{{statements\|join("\\n")}}\nAnswer:` | longform: `vars` 전부, `question`, `answer`. NLI: `vars` 전부, `context`, `statements`(배열) |

**설정 입력** (외부 계약이므로 원문 이름 그대로)

| 이름 | 위치 | 의미 |
|---|---|---|
| `value` | `assert[]` | rubric(`llm-rubric`·`agent-rubric`·`search-rubric`), 정답/기준(factuality·closedqa·context-recall·select-best·similar·g-eval). 문자열이 기본이고 `llm-rubric`은 객체도 받는다(R-02) |
| `rubricPrompt` | `assert[]`, `options`(test·defaultTest) | 기본 프롬프트를 덮어쓴다. 문자열(JSON 채팅 배열 문자열 또는 일반 텍스트 또는 `file://…`)·`{role, content}[]`·(g-eval) `{steps, evaluate}` 객체·(context-faithfulness) 문자열 2개 배열. 같은 값이 그 테스트의 모든 모델 채점 어서션에 적용된다(R-06) |
| `provider` | `assert[]`, `options` | grader 지정. 우선순위는 assertion-family R-10·default-providers R-13 |
| `threshold` | `assert[]` | 의미가 타입마다 다르다(R-28) |
| `options.factuality` | test·defaultTest | `{subset, superset, agree, disagree, differButFactual}` 점수표 덮어쓰기(R-16). 기본 A=1, B=1, C=1, D=0, E=1 |
| `transform` | `assert[]` | 채점 대상 출력을 바꾼다(`llm-rubric`에서 이미지·오디오 첨부가 꺼진다, R-34) |
| `contextTransform`, `vars.context`, `vars.query` | `assert[]`, `vars` | RAG 계열의 문맥·질문 입력(R-20~R-22) |
| `config.windowSize` | `assert[]` | `conversation-relevance` 창 크기(기본 5) |
| `PROMPTFOO_DISABLE_OBJECT_STRINGIFY` | 환경변수 | 켜면 객체 변수를 JSON 문자열로 바꾸지 않아 `{{output.text}}`처럼 속성 접근이 된다(R-07) |
| `PROMPTFOO_GRADING_MAX_IMAGES`, `…_IMAGE_MAX_BYTES`, `…_IMAGE_MAX_TOTAL_BYTES`, `…_IMAGE_MAX_RAW_CHARS`, `…_IMAGE_MAX_TOTAL_RAW_CHARS` | 환경변수 | 이미지 첨부 한도(R-34). 기본 4장, 개당·합계 20 MiB |

**결과 `GradingResult`** (`src/types/index.ts:546`) 쓰임: `pass`·`score`·`reason`은 R-14~R-24. `tokensUsed`는 grader 호출들의 합(`normalizeMatcherTokenUsage`, C-23). `metadata`에 들어가는 키: `renderedGradingPrompt`(grader에 보낸 최종 프롬프트 문자열. `llm-rubric`·`agent-rubric`·`trajectory:goal-success`만), `cachedResponse`(grader 응답이 캐시에서 왔을 때), `graderError`(R-25), RAG 계열의 `context`·`contextUnits`·`graderOutputs` 등(R-20~R-22), `llm-rubric`은 grader provider 응답의 `metadata`도 합친다(R-15). `assertion`은 핸들러가 붙인다.

### 1.4 행동 규칙과 남은 질문 [필수]

**A. rubric·rubricPrompt·출력이 매처에 닿는 형태**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `value` 문자열(rubric 등) | 어서션 실행 단계에서 비 grader 모드 Nunjucks로 `vars`를 써서 한 번 렌더된다(assertion-family R-08). 정의되지 않은 변수는 빈 문자열이 된다(오류 아님). 환경변수 `PROMPTFOO_DISABLE_TEMPLATING`이 켜져 있으면 이 단계는 렌더하지 않는다. 렌더된 문자열은 이후 grader 프롬프트에 변수 값으로 들어가고 다시 렌더되지 않는다(R-07). | 코드 확인 |
| R-02 | `llm-rubric`·`agent-rubric`의 `value` 형태 | 문자열·객체·`undefined`만 허용한다(그 외는 invariant 오류로 던져 행 `ERROR`). `undefined`는 rubric `''`이 된다. 핸들러가 `assertion.value`를 `rubricPrompt`로 채우는 것은 표시용이며 이미 정해진 rubric에는 영향이 없다. 객체 rubric은 R-07로 JSON 문자열로 보인다. `factuality`·`closedqa`·`context-recall`·`search-rubric`은 문자열을 요구하고(아니면 invariant 오류), `factuality`·`closedqa`·`context-recall`은 렌더된 prompt도 필요하다. | 코드 확인 |
| R-03 | 어서션에서 매처로 가는 `rubricPrompt`와 grader 설정 | 매처가 받는 `grading`은 `test.options`이고 `provider = assertion.provider \|\| test.options.provider`, `rubricPrompt = assertion.rubricPrompt \|\| test.options.rubricPrompt`다(assertion-family R-10). `llm-rubric`·`agent-rubric` 핸들러는 객체형 `rubricPrompt`를 `JSON.stringify`한 문자열로 바꿔 매처에 넘긴다. | 코드 확인 |
| R-04 | 채점 대상 출력 | 매처는 `outputString = coerceString(output)`를 받는다(`output`은 `assertion.transform` 적용 후. 객체이면 `JSON.stringify`). 텍스트 grader 매처는 이 문자열을 `tryParse`(JSON으로 파싱되면 그 값, 아니면 원문)해 `output`·`completion`·`answer` 변수로 쓴다. 따라서 JSON으로 파싱되는 출력은 원문 서식이 아니라 R-07의 정규화된 값으로 grader에 보인다. 문자열 리터럴 JSON(`"hello"`)은 따옴표가 벗겨진 값이 되고, 숫자 문자열(`0.10`)은 숫자로 파싱돼 재서식된다(`0.1`). `answer-relevance`·`context-faithfulness`의 질문·출력 인자는 `outputString`이 아니라 `output`(문자열 필수)이고, `search-rubric`은 `providerResponse.output`을 그대로 넘겨 `assertion.transform`이 반영되지 않는다. | 코드 확인 |
| R-05 | 원본 prompt가 쓰이는 곳 | `factuality`(`{{input}}`), `model-graded-closedqa`(`{{input}}`, 프롬프트 안 `[Task]`), `g-eval`(`{{input}}`)에는 렌더된 최종 prompt 문자열이 통째로 들어간다(채팅 형식 prompt면 메시지 배열 JSON 문자열 전체, 비어 있으면 `g-eval`은 `No source text to estimate reply`를 던짐). `answer-relevance`는 문자열 `vars.query`가 있으면 그것을, 없으면 prompt 전체를 질문으로 쓴다. `context-recall`은 `vars.context`·`contextTransform`이 없을 때 prompt 전체를 문맥으로 쓴다. **`llm-rubric`·`select-best`·`search-rubric`·`agent-rubric`에는 원본 prompt가 변수로 주어지지 않는다.** | 코드 확인 |

**B. 프롬프트 로드와 렌더**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | `loadRubricPrompt(rubricPrompt, 기본 프롬프트)` | 값이 없거나 빈 객체면 기본 프롬프트. `file://` 문자열: 경로를 Nunjucks로 렌더하고 `경로:함수` 접미를 떼며 `cliState.basePath` 기준으로 풀어, JS/TS 파일이면 그 함수를 인자 없이 호출한 결과를, 그 밖의 확장자(`.json`·`.yaml`·`.txt` 포함)는 파일 **원문 텍스트**를 쓴다(없으면 `File does not exist: <절대경로>`). 그 밖의 값은 `maybeLoadFromExternalFile`을 거친다. 최종 값이 객체(배열 포함)면 `JSON.stringify`하고, 결과는 문자열이어야 한다(invariant). 이 값이 **그 테스트의 모든 모델 채점 어서션**에 쓰이므로 `llm-rubric`용으로 둔 문자열 `rubricPrompt`는 `factuality` 등에도 적용되고 그 응답 형식에 맞지 않을 수 있다. 예외 해석: `g-eval`은 비배열 객체의 `steps`·`evaluate` 키만 읽고 문자열·배열은 무시한다(기본 프롬프트로 돌아감). `context-faithfulness`는 배열(원소 2개)이어야 하고 아니면 invariant 오류(`Invariant failed: rubricPrompt must be an array`)로 던진다. `conversation-relevance`는 프롬프트를 Nunjucks로 렌더한다. | 코드 확인 |
| R-07 | `renderLlmRubricPrompt(프롬프트, 변수)` | ① 변수 중 객체는 최상위에서 `JSON.stringify`된 문자열로 바꾼다(배열은 배열을 유지하고 객체 원소만 문자열화). `PROMPTFOO_DISABLE_OBJECT_STRINGIFY`가 켜져 있으면 바꾸지 않는다. ② 프롬프트가 JSON으로 파싱되면 **모든 문자열 값**(키 제외)을 Nunjucks로 렌더해 `JSON.stringify`한 문자열을 돌려준다(채팅 배열이면 채팅 JSON 문자열). 변수 값에 따옴표·줄바꿈이 있어도 JSON 구조가 깨지지 않는다. ③ JSON이 아니면 프롬프트 전체를 Nunjucks로 렌더한다. grader 모드 Nunjucks는 `PROMPTFOO_DISABLE_TEMPLATING`과 무관하게 항상 켜져 있고, 정의되지 않은 변수는 빈 문자열이다. 변수 값(출력·rubric 등)은 템플릿 원문이 아니라 데이터이므로 그 안의 `{{ … }}`·`{% … %}`는 해석되지 않고 그대로 grader에 간다. 전역 `env`가 있고, 변수 이름이 `env`이면 변수가 이긴다. | 코드 확인 |
| R-08 | 변수 병합 순서 | 사용자 `vars`를 먼저 펼치고 매처의 예약 변수가 덮어쓴다. 따라서 `llm-rubric`에서 사용자 변수 `output`·`rubric`은 실제 출력·rubric으로 가려진다. 예약 변수 목록은 1.3 표. `g-eval`·`answer-relevance`·`context-relevance`는 `vars`를 아예 펼치지 않아 사용자 변수를 프롬프트에서 쓸 수 없다. | 코드 확인 |

**C. grader 호출**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-09 | grader 선택 지점 | 모든 매처가 `getAndCheckProvider(역할, grading.provider, 기본 칸, 점검 이름)`로 grader를 정한다. 어떤 매처가 어떤 역할·기본 칸을 쓰는지는 1.3 표. 선택 순서(설정 층 우선순위, 환경변수 사다리, `defaultTest.provider` 폴백, 타입 검증)와 대상=grader 문제는 default-providers R-12~R-17, R-20이 정한다. 점검 이름은 오류·경고 메시지에만 쓰인다. `grading`이 없는 호출은 `Cannot grade output without grading config…` 오류를 던지지만 핸들러 경로에서는 `test.options`가 항상 있어 닿지 않는다. | 코드 확인 |
| R-10 | `callProviderWithContext(provider, prompt, 라벨, vars, 컨텍스트, promptConfig?)` | `provider.callApi(prompt, ctx, options?)`를 부른다. `ctx = {...어서션의 providerCallContext, isGrading: true, prompt: {raw: prompt, label: 라벨, config?}, vars}`. 어서션의 컨텍스트에서 이어받는 것은 `originalProvider`(평가 대상 provider)와 추적 헤더(`traceparent`)이고, 컨텍스트의 `prompt`·`vars`는 grader 호출의 것(위 `prompt`, 매처가 쓴 변수)으로 덮어쓴다. 라벨: `llm-rubric`, `trajectory:goal-success`, `factuality`, `model-graded-closedqa`, `g-eval-steps`, `g-eval`, `answer-relevance`, `context-recall`, `context-relevance`, `context-faithfulness-longform`, `context-faithfulness-nli`, `select-best`, `search-rubric`, `agent-rubric`, `conversation-relevance`(+`-reason`). 평가 실행 컨텍스트에 취소 신호가 있으면 `options = {abortSignal}`이 붙는다. 매처는 `temperature`·`max_tokens` 같은 샘플링 설정을 지정하지 않는다(R-29). 프롬프트는 문자열이며 채팅 JSON 배열 문자열이면 provider가 메시지로 해석한다(provider-contract 소관). | 코드 확인 |
| R-11 | 평가 중 grader 호출의 스케줄링과 재시도 | 평가 실행 컨텍스트 안에서는 grader 호출이 provider 추적 스팬과 속도 제한 레지스트리·호출 대기열을 거친다. 취소됐으면 시작하지 않는다. 기본 재시도 정책: 레이트리밋 판정 결과 또는 일시 오류 예외(메시지에 `timeout`·`econnrefused`·`network`·`502`·`503`·`504`가 있거나 연결 오류)에서 최대 3회, 1초 시작 지수 백오프(+지터 20%, 최대 60초), 서버 `Retry-After` 우선. 쿼터 소진 오류는 재시도하지 않는다. provider `config.maxRetries`(0 이상 정수)가 있으면 그 값, `handlesOwnRetries`이면 0이다. 평범한 `{error: '…'}` 결과는 레이트리밋·재시도 판정에 걸리지 않으면 재시도 없이 R-25로 간다. 환경변수 `PROMPTFOO_SCHEDULER_QUEUE_TIMEOUT_MS`(기본 5분, 0이면 끔)는 대기열 대기 한도다. 모델 채점 어서션이 있는 테스트는, `--max-concurrency 1`이고 평가 단계 타임아웃·`_conversation` 변수가 없을 때 평가기가 채점을 대상 호출 뒤로 미루고 grader provider별로 묶어 실행한다(조건만 확인했고 묶는 방식은 읽지 않았다. 결과 의미는 같다고 읽었다 — 추론). 평가 실행 컨텍스트 밖(라이브러리가 매처를 직접 부름)에서는 이 래퍼 없이 `callApi`를 부른다. | 코드 확인(구조·상수) / 어떤 응답이 레이트리밋으로 판정되는지는 미탐색 |
| R-12 | 같은 어서션의 호출 횟수·재시도 | grader 호출 수는 1.3 표와 같다. 응답이 파싱에 실패하거나 형식이 틀려도 **다시 묻거나 고쳐 달라고 하지 않는다**. 같은 출력을 여러 번 채점해 합의·평균을 내는 경로는 없다(예외로 보이는 `g-eval` 배열은 기준마다, `answer-relevance`는 질문 생성 샘플링 3회이며 합의가 아니다). 점수 변동을 줄이는 장치는 grader 설정(R-29)과 캐시(R-30)뿐이다. | 코드 확인 |

**D. 응답 해석과 판정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | JSON 판정 계열(`llm-rubric`·`agent-rubric`·`trajectory:goal-success`)의 응답 파싱 | `resp.error`가 있거나 `resp.output`이 falsy면 R-25의 전송·빈 출력 실패. 문자열 출력: `extractJsonObjects`(C-24)로 객체를 꺼낸다. 문자열 전체가 JSON 객체면 그것이고, 아니면 본문의 `{ … }` 후보를 균형 괄호로 훑고 실패 시 YAML 호환 파서(`//` 주석 허용, 닫는 괄호 누락 보정)로 재시도해 객체 목록을 만든다. **목록의 첫 객체만** 쓴다. 객체가 없으면 `Could not extract JSON from <라벨> response`, 추출 중 예외면 `<라벨> produced malformed response: …`. 첫 후보가 배열·기타면 `… not able to parse the response as JSON`. 객체 출력(예: Anthropic 강제 도구 결과)은 그대로 쓰고, 배열·그 밖의 형태는 `output must be string or object`로 실패한다. | 코드 확인 |
| R-14 | `{pass, score}`에서 판정 도출(`deriveVerdictFromGrader`, C-11) | 숫자 `threshold`(문자열도 `Number`로 변환, 유한할 때만)를 `hasThreshold`라 한다. `pass`가 없거나 null: `score`가 유한 숫자(숫자 문자열 가능)여야 하고 아니면 실패(`Grader response contained neither a pass verdict nor a finite numeric score`), 통과는 `hasThreshold ? score >= threshold : score > 0`. `pass`가 있으면: boolean은 그대로, 그 밖의 값은 문자열화해 `true`·`yes`·`pass`·`y`(대소문자 무시)일 때만 참(숫자 `1`은 거짓). `score`는 숫자면 그대로, 아니면 `Number(score)`가 유한할 때 그 값(`null`·`""`은 0), 아니면 `Number(pass)`(참 1, 거짓 0). `hasThreshold`이면 `pass = pass && score >= threshold`. 즉 `pass`가 명시되면 `score`는 `threshold`가 없는 한 통과에 영향이 없다(`{pass:true, score:0}` 통과). | 코드 확인 |
| R-15 | JSON 판정 계열의 결과 구성 | `reason = grader의 reason(truthy) \|\| (pass ? 'Grading passed' : 'Score <score> below threshold <threshold>')`(threshold가 없으면 `undefined`가 그대로 찍힌다). `tokensUsed`는 응답의 `tokenUsage`를 정규화한 것(`completionDetails`는 응답에 없으면 grader JSON의 것). `metadata = {...grader provider 응답의 metadata(JSON 직렬화 가능한 객체일 때만, 배열은 무시), renderedGradingPrompt: 렌더된 최종 프롬프트, 이미지·오디오 첨부 표시, cachedResponse?}`. `cachedResponse`는 provider 응답의 `cached`가 참일 때만 붙고 provider metadata가 주장하는 값은 버린다. | 코드 확인 |
| R-16 | `factuality` 응답 | 응답 문자열에서 첫 JSON 객체를 꺼내(`extractFirstJsonObject`) `category`를 `trim`·대문자화한다. 문자열이 아니거나 없으면(또는 JSON이 아니면) 옛 형식으로 넘어간다. `A`~`E`가 아니면 `Invalid category value: <값>`으로 실패(옛 형식으로 가지 않음). 옛 형식: 정규식 `/\s*\(?([a-eA-E])\)/`의 **첫 일치**(응답 어디든)에서 글자를 취하고 reason은 첫 `)` 뒤 텍스트(없으면 전체). 일치가 없으면 `Factuality checker output did not match expected format: <응답>`으로 실패. 점수표(`options.factuality`로 덮어쓰기, 기본 A·B·C·E=1, D=0): `score = 표[범주]`, 점수가 0보다 크면 통과, 0 이하면 실패. reason은 JSON `reason`(비면 `Category <X>: <범주 설명>`). `threshold`는 읽지 않는다. 응답이 문자열이 아니면 invariant 오류를 **던진다**. | 코드 확인 |
| R-17 | `model-graded-closedqa` 응답 | 응답이 문자열이어야 한다(아니면 던짐). `trimEnd()` 후 끝 글자가 `Y`이면 `{pass:true, score:1, reason:'The submission meets the criterion:\n<응답>'}`, `N`이면 `{pass:false, score:0, reason:'The submission does not meet the criterion:\n<응답>'}`(정상 판정이며 `graderError` 없음). 그 밖은 `Model grader produced a malformed response:\n<응답>`으로 실패. | 코드 확인 |
| R-18 | `g-eval` | ① steps 호출(변수 `criteria`) 응답에서 정규식 `/\{"steps".+\}/g`의 첫 일치를 `JSON.parse`해 `steps`를 얻는다. `.`은 줄바꿈과 일치하지 않고 `{`와 `"steps"`는 붙어 있어야 하므로, 들여써서 여러 줄로 정렬한 JSON(`{` 다음 줄바꿈)은 일치하지 않는다. `steps`는 비어 있지 않은 배열이고 모든 원소가 비어 있지 않은 문자열이어야 한다. ② evaluate 호출(`criteria`, `steps`를 `'\n- '`로 이은 문자열, `maxScore='10'`, `input`·`output` tryParse) 응답에서 `/\{.+\}/g` 첫 일치를 파싱한다(역시 한 줄). `score`는 숫자 또는 비지 않은 숫자 문자열, 유한, 0 이상 10 이하(정수 강제 없음), `reason`은 비지 않은 문자열이어야 한다. 점수 `score/10`, `pass = score/10 >= threshold`(핸들러는 이 값을 무시하고 `>= threshold`로 다시 계산, 기본 0.7). 어느 단계든 위반하면 단계별 메시지로 `graderFail`(`tokensUsed`는 두 호출 누적). 응답이 문자열이 아니면 `LLM-proposed … response is not a string`으로 `graderFail`. `rubricPrompt` 객체의 `steps`·`evaluate`로 각 단계 프롬프트를 덮어쓴다. | 코드 확인 |
| R-19 | `answer-relevance` | grader는 `text`·`embedding` 두 역할을 같은 `provider` 설정으로 각각 해석한다. `answer` 변수로 질문 생성 프롬프트를 렌더하고 grader를 **3번** 부른다(첫 호출은 현재 캐시 이름공간, 둘째·셋째는 `answer-relevance:sample:1`·`:2` 이름공간 — 같은 프롬프트의 캐시 적중으로 세 질문이 같아지는 것을 막는다). 응답 전체가 한 질문이다. 입력(R-05)과 세 질문을 임베딩해 각 코사인을 평균한다. `pass = 평균 >= threshold - Number.EPSILON`(기본 0.5), `score = 평균`(클램프 없음), reason `Relevance <x.xx> is greater than\|less than threshold <t>`, `metadata = {generatedQuestions: [{question, similarity}], averageSimilarity, threshold}`. 어떤 호출이든 오류·빈 값이면 그 즉시 `graderFail`(누적 토큰 포함). | 코드 확인 |
| R-20 | `context-recall` | 문맥은 `vars.context`(문자열 또는 문자열 배열)가 우선, 없으면 prompt 전체, 그 위에 `contextTransform`이 있으면 그 결과(문자열 또는 문자열 배열, 아니면 오류)가 덮는다. 문맥이 비면 오류를 던진다(`Invariant failed: Context is required for context-based assertions…`). 배열 문맥은 `\n\n`으로 잇는다. 응답 줄 중 `[Attributed]` 또는 `[Not Attributed]`(대소문자 무시)를 포함한 줄만 센다. `[Not Attributed]`를 포함하면 미귀속, 아니면 귀속. `score = 귀속 줄 수 / 센 줄 수`, `pass = score >= threshold - Number.EPSILON`(기본 0.5). 센 줄이 0이면(거절·설명만) `pass:false, score:0`이고 `metadata.graderError = true`이며 reason `Grader returned no [Attributed]/[Not Attributed] classifications`. `metadata = {sentenceAttributions, totalSentences, attributedSentences, score}`와 핸들러가 붙이는 `context`. | 코드 확인 |
| R-21 | `context-relevance` | `vars.query`(문자열)가 필수다. 문맥 해석은 R-20과 같다(문맥이 없으면 오류, prompt 폴백은 없음). 응답에 `Insufficient Information`이 있으면 관련 문장 0개. 아니면 응답을 문맥과 같은 단위로 나눠(문맥이 배열이거나 비지 않은 줄이 2개 이상이면 줄 단위, 아니면 문장 단위 `splitTextIntoSentences`) 문맥 본문(소문자·공백 정규화)에 **그대로 인용된** 단위만 센다(정규화한 같은 문장은 한 번). 센 단위가 0인데 응답이 비어 있지 않고 `Insufficient Information`도 아니면 `pass:false, score:0, metadata.graderError = true`, reason `Grader output does not quote the provided context`. 그 밖: `score = min(인용 단위 수, 문맥 단위 수) / 문맥 단위 수`, `pass = score >= threshold - Number.EPSILON`(기본 0.5). 문맥 단위는 배열이면 비지 않은 원소, 문자열이면 R-21 분할. | 코드 확인 |
| R-22 | `context-faithfulness` | `vars.query` 필수, 출력은 문자열 필수. 1단계(longform, `question`=query, `answer`=tryParse(출력)) 응답의 비지 않은 줄을 statements로 삼는다(서두 문장도 한 줄이면 문장으로 센다). 0줄이면 `Could not extract context-faithfulness statements`. 2단계(NLI, 문맥과 statements 배열) 응답을 소문자로 바꿔 해석한다. ① `final verdict for each statement in order:`가 있으면 그 뒤를 `.`로 나눈 비지 않은 조각이 모두 `yes` 또는 `no` 단어를 포함해야 하고, `yes`를 포함하지 않는 조각을 미지지로 센다. ② 표지가 없으면 `verdict: no`·`verdict: yes` 출현 횟수를 센다. 어느 쪽도 해석되지 않으면 `Could not parse context-faithfulness verdicts`. `score = 1 - (미지지 + 누락(= statements 수 - 판정 수, 0 이상)) / statements 수`, 0~1로 클램프, `pass = score >= threshold - Number.EPSILON`(기본 0.5). | 코드 확인 |
| R-23 | `select-best` | `outputs` 2개 미만이면 invariant 오류를 던진다(`Invariant failed: select-best assertion must have at least two outputs to compare between`). 변수 `criteria`(=`value`), `outputs`(열 순서 그대로, 각각 tryParse). 응답을 `trim`해 **첫 정수 숫자열**(부호 무시, `-1`은 1)을 취한다. 숫자가 없거나 범위(0 이상 `outputs.length` 미만) 밖이면 모든 출력이 `Invalid select-best verdict: <값>`으로 실패한다(`fail`이며 `graderError` 표시 없음). 그 밖은 열마다 `pass: 선택됨, score: 선택됨 ? 1 : 0`, reason `Output selected as the best: <criteria>` 또는 `Output not selected: <criteria>`. 전송 오류·빈 출력도 `fail`(`graderError` 없음)이 열마다 돌아온다. 출력 순서를 섞지 않는다. | 코드 확인 |
| R-24 | `similar` 계열 | 역할 `embedding`. 코사인이고 provider가 `callSimilarityApi`를 가지면 그것을 부르고(1회), 아니면 `callEmbeddingApi`로 기대 문장과 출력을 병렬 임베딩한다. 둘 다 없으면 오류를 던진다. 거리 `euclidean`·`dot_product`는 임베딩만 된다. 유사도: `pass = inverse ? 값 <= threshold + EPS : 값 >= threshold - EPS`, `score = inverse ? 1 - 값 : 값`. 유클리드(거리): `pass = inverse ? 거리 >= threshold - EPS : 거리 <= threshold + EPS`, `score = 1 / (1 + 거리)`(반전이면 `1 - 그 값`). 유한하지 않으면 `Invalid similarity score`. 전송·임베딩 오류는 `fail`(`graderError` 없음). 기본 threshold 0.75와 배열 `value` 규칙은 assertion-family R-47. | 코드 확인 |

**E. 실패와 오류**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | grader 호출·응답이 정상이 아닐 때 | 세 갈래다. ① **`graderFail` 결과**(던지지 않음): `{pass:false, score:0, reason:<원인>, tokensUsed, metadata:{graderError:true}}`. 해당: `resp.error` 또는 빈 `output`(`llm-rubric`·`factuality`·`closedqa`·`g-eval`·RAG 계열·`search-rubric`·`conversation-relevance`), 형식·범위 위반(R-13~R-22), `search-rubric`의 판정 파싱 실패. `llm-rubric` 계열은 실패 응답이 캐시에서 왔으면 `metadata.cachedResponse = true`를, 사용량 보고가 없는 새 실패면 `numRequests = 1`을 채운다. ② **`fail` 결과**(`graderError` 없음): `select-best`(R-23), `similar`(R-24)의 전송·형식 오류. ③ **예외 전파**(평가기가 행을 `ERROR`로 만든다, assertion-family R-24): 비문자열 `output`을 요구하는 매처의 invariant(`factuality`·`closedqa`·RAG 계열·`select-best`·`answer-relevance`가 grader 응답이 문자열이 아닐 때), 입력 invariant(R-02, R-05의 `g-eval` 빈 prompt, RAG의 `query`·`context` 누락, `rubricPrompt` 형태 오류), `getAndCheckProvider` 오류(잘못된 provider 정의, 역할 불일치), 이미지·오디오 한도 초과, `callApi`가 던지는 예외. invariant 메시지는 `Invariant failed: <메시지>` 형태다. `llm-rubric`은 `throwOnError` 옵션이 없는 핸들러 경로에서 `resp.error`를 예외로 만들지 않는다. | 코드 확인 |
| R-26 | `graderFail`이 행에 남는 모양 | 행은 `success=false`, `failureReason=ASSERT`, `error = reason`이 되어 grader의 "불합격" 판정과 행 수준 필드가 같다. 구분은 `gradingResult.componentResults[i].metadata.graderError`뿐이다(`not-` 반전에서는 뒤집지 않고 실패를 유지: assertion-family R-46). 평가기는 `graderError`를 읽지 않는다(`src/evaluator.ts`에 참조 없음). `fail` 결과(R-25 ②)는 이 표시조차 없다. | 코드 확인 |
| R-27 | 시간 제한 | 매처 수준 타임아웃은 없다. 제한은 ① provider HTTP 요청 타임아웃(`REQUEST_TIMEOUT_MS`, 기본 300000ms, 예: `fetchWithCache` 기본 인자) ② 스케줄러 대기열 한도(R-11) ③ 평가 단계 타임아웃(환경변수 `PROMPTFOO_EVAL_TIMEOUT_MS`, 기본 0=없음; 대상 호출과 채점을 합친 단계가 넘으면 취소 신호를 보내고 행이 `Evaluation timed out after <ms>ms: …`, `failureReason=ERROR`가 됨) ④ 사용자 취소다. ①이 넘으면 provider가 `{error}`를 돌려주면 R-25 ①, 던지면 R-25 ③이다. 어느 쪽인지는 provider 구현 소관이며 이 스펙은 확인하지 않았다. | 코드 확인(상수·구조) / provider별 오류 형태 미확인 |

**F. 점수 의미와 `threshold`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | 타입별 점수 범위와 threshold | `llm-rubric`·`agent-rubric`·`trajectory:goal-success`: `score`는 **클램프하지 않는다**(프롬프트가 0.0~1.0을 요청할 뿐 grader가 준 값이 그대로 쓰이고 `threshold`와 비교됨. `not-`일 때만 `[0,1]`로 클램프, assertion-family R-46). `threshold`는 R-14. `factuality`: 점수표 값, `threshold` 무시. `closedqa`: 0 또는 1, `threshold` 무시. `g-eval`: `score/10`(0~1), 기본 0.7. `answer-relevance`: 코사인 평균(음수 가능), 기본 0.5. `context-recall`·`relevance`·`faithfulness`: 0~1, 기본 0.5, 비교는 `score >= threshold - Number.EPSILON`. `select-best`: 0 또는 1, `threshold` 없음. `similar`: R-24, 기본 0.75. `search-rubric`: R-35. `conversation-relevance`: 창별 판정 비율, 기본 0.5. 테스트 수준 `threshold`는 점수 집계(assertion-family R-19) 소관이다. | 코드 확인 |

**G. 점수 신뢰도에 관한 사실**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-29 | grader 샘플링 설정 | 매처는 샘플링 설정을 grader에 넘기지 않는다. 기본 grader 둘은 코드상 `temperature`를 보내지 않는다. OpenAI `gpt-6-sol` chat: `reasoning_effort`가 `none`이 아니거나 지정이 없으면 `applyGpt6RequestRules`가 `temperature`·`top_p`를 지운다(`gpt-6.1-sol`은 항상). Anthropic `claude-sonnet-5`: 모델 표에서 샘플링 매개변수 폐기 모델이라 `temperature`·`top_p`·`top_k`를 보내지 않고 사고(thinking)가 기본으로 켜져 있다. 샘플링을 고정하려면 grader를 `{id, config: {…}}` 객체로 지정한다(`assert[].provider`·`options.provider`·`--grader`). 어서션의 `provider`는 `options.provider`를 병합하지 않고 통째로 대체하므로(`getFinalTest`) 전역 객체의 `config`는 어서션에 쓴 문자열 provider에 상속되지 않는다(우선순위는 default-providers R-13). 같은 설정에서도 모델이 결정적이라는 보장은 코드에 없다. 반환되는 `GradingResult`에는 grader 모델 id·샘플링 설정이 들어 있지 않다(`metadata`에는 provider 응답 metadata가 들어갈 뿐). | 코드 확인(기본 grader 구성 읽음, 실제 API 수락 여부는 미확인) |
| R-30 | grader 응답 캐시 | grader 호출도 provider의 응답 캐시를 그대로 탄다(예: OpenAI chat은 `fetchWithCache`). 같은 프롬프트·같은 grader 설정이면 두 번째부터 같은 응답이 재사용되고 결과에 `metadata.cachedResponse = true`가 붙으며 토큰은 `cached`로 집계된다(assertion-family R-18). `--no-cache`이면 읽기·쓰기가 없다. 평가기는 `runEval` 전체(대상 호출과 채점)를 같은 `repeat:<i>` 이름공간 아래서 실행하므로 `--repeat N`은 반복마다 grader 응답을 따로 얻는다([response-cache](./response-cache.md) R-07). `select-best` 비교 단계도 같은 이름공간으로 감싼다. 어떤 provider가 캐시를 쓰는지·키 재료는 response-cache 소관. | 코드 확인 |
| R-31 | 편향 관련 호출 지점 | 이 스펙의 모든 매처는 grader를 default-providers R-12~R-17로 고르고, 대상과 같은 계열인지 점검·회피하지 않는다(default-providers R-20; 어서션이 대상을 `originalProvider`로 **전달**만 하고 선택에는 쓰지 않음, R-10). 위치 편향: `select-best`는 출력을 열 순서대로 번호를 매겨 한 번만 묻고 순서를 섞거나 되묻지 않는다(R-23). 길이·서식 편향을 줄이는 코드는 없다. | 코드 확인 |

**H. `llm-rubric`으로 스킬 결과를 채점할 때 grader가 받는 것**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | 기본 프롬프트(R-06)·문자열 출력일 때 grader가 받는 최종 입력 | `callApi`에 가는 프롬프트는 채팅 JSON 배열 문자열 한 개다. `system` 메시지는 C-01의 고정 지침과 예시이고, `user` 메시지는 `<Output>\n<출력>\n</Output>\n<Rubric>\n<rubric>\n</Rubric>`이다. `<출력>`은 R-04의 정규화를 거친 대상 provider의 `output` 문자열이고 `<rubric>`은 R-01로 렌더된 `value`다. **원본 prompt, SKILL.md 내용, 대상 모델·provider 이름, 테스트 `vars`, 스킬·도구 호출 기록(`metadata.skillCalls` 등)은 기본 프롬프트에 들어가지 않는다.** 이 최종 프롬프트는 `metadata.renderedGradingPrompt`에 저장된다. | 코드 확인 |
| R-33 | 원본 prompt·변수·메타데이터를 grader에 주고 싶을 때 쓸 수 있는 경로 | ① rubric 문자열에 `{{변수}}`를 쓴다(R-01, 테스트 `vars`가 값). ② 커스텀 `rubricPrompt`(R-06)에서 `{{변수}}`로 `vars`를 쓴다(`output`·`rubric` 예약, R-08). ③ `assertion.transform`이 출력을 바꾼다. 변환 함수는 `(output, {vars, prompt: {label: 렌더된 prompt}, metadata: 응답 metadata})`를 받으므로(`src/assertions/index.ts:443-450`) 응답 metadata나 렌더된 prompt를 출력 문자열에 합쳐 grader에 줄 수 있다. 렌더된 prompt를 템플릿 변수로 직접 주는 기능은 `llm-rubric`에 없다. 값을 `vars`에 따로 넣어야 한다. | 코드 확인 |
| R-34 | 대상 응답에 이미지·오디오가 있을 때 | `llm-rubric` 핸들러만, `assertion.transform`이 없고 응답에 `images` 또는 `audio`가 있을 때 `providerResponse`를 매처에 넘긴다. 이때 grader 프롬프트 마지막 사용자 메시지에 이미지(provider 종류별 형식: OpenAI·Responses·Anthropic·Gemini)나 오디오(OpenAI 오디오 입력 형식 grader만, WAV·MP3)가 붙고 텍스트 출력이 이미지 base64 문자열이면 `[Image output attached…]` 자리표시자로 바뀐다. 한도: 이미지 4장·개당 20 MiB·합계 20 MiB·원문 문자 수(1.3 환경변수 표), 오디오 20 MiB. 원격 URL·blob 참조·잘못된 base64는 오류를 던진다. 텍스트 전용 provider는 이미지를 받지 못한다. | 코드 확인(개요) |

**I. 하위 절: 별도 grader 사슬을 가진 매처, 경계 한 줄들**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-35 | `search-rubric` (개요) | grader 사슬은 default-providers R-22. 핸들러는 `rubric`이 문자열이 아니면 던진다. 프롬프트는 C-06(변수 `vars`+`output`+`rubric`, 대상 출력은 `providerResponse.output`로 `transform` 미반영). 응답은 `extractFirstJsonObject`로 첫 객체를 꺼내 **boolean `pass`가 필수**(문자열 `"true"`·없음이면 `Expected a JSON object with a boolean "pass" field`로 실패하며 `graderError`). `score`는 숫자면 그 값, 아니면 `pass ? 1 : 0`. `assertion.threshold`가 정의돼 있으면 `pass = pass && score >= threshold`. reason 기본 `No reason provided`. `metadata = {searchResults, searchProvider: grader id}`. 전송 오류·빈 출력은 `Search rubric evaluation failed: …`로 `graderFail`. | 코드 확인 |
| R-36 | `agent-rubric` (개요) | grader 사슬은 default-providers R-22. 설정 grader가 없으면 Codex 기본 `llmRubricProvider`를 쓰고, 에이전트형 provider가 아니면 던진다. 프롬프트·파싱·판정은 `llm-rubric`과 같은 `runJsonGradingPrompt`(R-13~R-15, C-02). 대상 응답 `metadata.workingDir`가 이 프로세스가 만든 격리 작업공간이면 grader 호출의 prompt 설정 `working_dir`로 넘겨 grader가 그 작업공간을 볼 수 있다. `metadata.agentProvider`에 grader id. | 코드 확인 |
| R-37 | `trajectory:goal-success`, `conversation-relevance` (개요) | `trajectory:goal-success`: 핸들러가 트레이스를 요약(`summarizeTrajectoryForJudge`)해 변수 `trajectory`로, `goal`·출력과 함께 C-07로 `runJsonGradingPrompt`를 부른다(R-13~R-15와 같은 파싱·판정). 트레이스가 없으면 핸들러가 던진다. `conversation-relevance`: `vars._conversation`(없으면 `[{input: prompt, output}]`)을 창 크기(기본 5)로 잘라 창마다 grader를 한 번 부르고 `{verdict: 'yes'\|'no'}` JSON(첫 객체)을 얻는다(`yes`면 1, 아니면 0, 그 밖의 값은 `graderFail`). 점수 = `yes` 창 비율, 기본 threshold 0.5, 비관련 창이 있고 점수가 1 미만이면 이유 요약을 위해 grader를 한 번 더 부른다. 사용자 메시지·출력은 템플릿이 아닌 데이터로 취급한다(주석의 SSTI 방지). 이 둘의 세부(트레이스 요약, 창 구성)는 읽지 않았다. | 코드 확인(구조) / 세부 미탐색 |
| R-38 | 원격 채점(`remoteGrading`) | 범위 밖. 일반 평가에는 닿지 않는 조건만 쓴다: `llm-rubric`은 `rubricPrompt`가 없고, (`options.preferRemote` 또는 내부 플래그 또는 `grading.provider`가 없음)이며, `cliState.config.redteam`이 있고 `redteam.provider`가 없고, `shouldUseRemoteGrading(…)`이 참일 때만 원격으로 간다. `similar`(코사인)는 `cliState.config.redteam`이 있고 `shouldUseRemoteGrading({requireEmbeddingProvider: true})`일 때. `redteam` 설정이 없는 평가는 항상 로컬 grader다. 원격 호출이 실패하면 `Could not perform remote grading: …`로 `graderFail`(`llm-rubric`)이나 `fail`(`similar`). default-providers R-23과 같은 조건이다. | 코드 확인(조건 구조) / 원격 내부 미탐색 |

- 불변식: (1) 핸들러 경로에서 grader 호출은 `getAndCheckProvider` 한 곳을 거쳐 provider가 결정되고, 응답은 한 번만 해석한다(재시도·다수결 없음, R-12). (2) 변수 값(출력·rubric·문맥)은 grader 프롬프트에서 템플릿으로 재해석되지 않는다(R-07). (3) `graderError` 결과는 `pass:false, score:0`이며 `not-` 반전으로 통과하지 않는다(핸들러 소관, assertion-family R-46).
- 미결정: 없음.
- 확인 한계:
  - 설치·빌드·실행·네트워크 호출을 하지 않았다. 모든 규칙은 정적 읽기다. 테스트는 `test/matchers/`·`test/assertions/`의 파일명과 `llm-rubric.test.ts`의 사례명만 훑었고 `:1917-2050`의 점수·문자열 `pass` 사례만 열었다(테스트를 읽은 것은 실행 확인이 아님). 그 사례는 R-14와 어긋나지 않았다.
  - 어떤 provider 응답이 레이트리밋·재시도 대상인지(`isProviderResponseRateLimited` 등), 각 provider가 시간 초과를 `{error}`로 돌려주는지 던지는지는 읽지 않았다(스케줄러·provider 패밀리 소관, R-11, R-27).
  - `maybeLoadFromExternalFile`의 배열 원소 `file://` 경로와 `loadFromJavaScriptFile` 내부, `GradingConfigSchema` 검증이 `options.rubricPrompt`의 비배열 객체(g-eval의 `{steps, evaluate}`)를 거부하는지는 읽지 않았다(추론: `options.rubricPrompt` 스키마 합집합에 평범한 객체가 없다).
  - `trajectory:goal-success`·`conversation-relevance`·이미지·오디오 grading은 개요 수준이다. `shouldGenerateRemote`·`doRemoteGrading` 내부는 읽지 않았다.
  - OpenAI·Anthropic 기본 grader에서 `temperature`를 지우는 것은 요청 본문을 만드는 코드 기준이며 실제 API 응답은 확인하지 않았다.

### 1.5 필수 코드 참조 [필수]

라이선스: 루트 MIT(overview 1절). 단 `src/external/prompts/ragas.ts`(RAGAS)·`src/external/matchers/deepeval.ts`·`conversationRelevancyTemplate.ts`·`src/external/assertions/deepeval.ts`(DeepEval)는 Apache-2.0 포팅이며 `src/external/APACHE_LICENSE`가 적용된다(C-09, C-28). 인용하면 그 고지를 유지한다. 나머지 범위는 MIT 코어 파일이다. 프롬프트 본문은 C-01~C-09가 원본이다(글로 옮기지 않았다).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/prompts/grading.ts:11-30` `DEFAULT_GRADING_PROMPT` | `llm-rubric` 기본 프롬프트 전문 | R-06, R-32 |
| C-02 | `src/prompts/grading.ts:32-55` `DEFAULT_AGENT_GRADING_PROMPT` | `agent-rubric` 기본 프롬프트 | R-36 |
| C-03 | `src/prompts/grading.ts:57-103` `PROMPTFOO_FACTUALITY_PROMPT` | `factuality` 프롬프트 | R-16 |
| C-04 | `src/prompts/grading.ts:105-122` `OPENAI_CLOSED_QA_PROMPT` | `closedqa` 프롬프트 | R-17 |
| C-05 | `src/prompts/grading.ts:146-161` `SELECT_BEST_PROMPT` | `select-best` 프롬프트 | R-23 |
| C-06 | `src/prompts/grading.ts:163-187` `DEFAULT_WEB_SEARCH_PROMPT` | `search-rubric` 프롬프트 | R-35 |
| C-07 | `src/prompts/grading.ts:189-222` `TRAJECTORY_GOAL_SUCCESS_PROMPT` | 궤적 목표 달성 프롬프트 | R-37 |
| C-08 | `src/prompts/index.ts:252-307` `GEVAL_PROMPT_STEPS`, `GEVAL_PROMPT_EVALUATE` | `g-eval` 두 프롬프트 | R-18 |
| C-09 | `src/external/prompts/ragas.ts:4-73` | RAGAS 포팅 프롬프트(답변 관련성·문맥 재현율·문맥 관련성·충실도 longform·NLI)와 표지 상수 `[Attributed]`·`[Not Attributed]`·`Insufficient Information` | R-19~R-22 |
| C-10 | `src/matchers/rubric.ts:61-160` `loadRubricPrompt`, `processContextForTemplating`, `renderLlmRubricPrompt` | 프롬프트 로드·변수 문자열화·JSON 문자열 값 렌더 | R-06, R-07 |
| C-11 | `src/matchers/rubric.ts:767-979` `parseJsonGradingResponse`, `graderFailureFromResponse`, `deriveVerdictFromGrader`, `runJsonGradingPrompt` | JSON 판정 계열의 파싱·판정·결과 구성 전체 | R-13, R-14, R-15 |
| C-12 | `src/matchers/rubric.ts:734-765` `buildGradingProviderPrompt`; `:314-394` `materializeImageOutputsForGrading` | 이미지·오디오 첨부 프롬프트와 한도 | R-34 |
| C-13 | `src/matchers/llmGrading.ts:48-129`, `:323-442` | `factuality` 점수표·JSON/옛 형식 파싱, `closedqa` 판정 | R-16, R-17 |
| C-14 | `src/matchers/llmGrading.ts:181-267` `matchesLlmRubric`; `:269-298` `matchesTrajectoryGoalSuccess` | `llm-rubric`·궤적 매처의 변수 구성과 원격 분기 | R-08, R-38 |
| C-15 | `src/matchers/llmGrading.ts:454-612` `matchesGEval` | `g-eval` 전체 | R-18 |
| C-16 | `src/matchers/rag.ts:34-155` `matchesAnswerRelevance` | 질문 3회 생성·임베딩 평균 | R-19 |
| C-17 | `src/matchers/rag.ts:157-269`, `:271-401`, `:403-529` | 문맥 재현율·관련성·충실도 | R-20, R-21, R-22 |
| C-18 | `src/matchers/shared.ts:101-150` `tryParse`, `splitIntoSentences`, `splitTextIntoSentences` | 파싱·문장 분할 helper | R-04, R-21, R-22 |
| C-19 | `src/matchers/comparison.ts:16-92` `matchesSelectBest` | `select-best` 매처 | R-23 |
| C-20 | `src/matchers/similarity.ts:29-240` | 유사도 계산·판정·provider 사용 | R-24 |
| C-21 | `src/matchers/providers.ts:71-164` `callGradingProvider`, `callProviderWithContext` | grader 호출 컨텍스트·스케줄링 래퍼 | R-10, R-11 |
| C-22 | `src/matchers/providers.ts:205-350` `getGradingProvider`, `getAndCheckProvider` | grader 해석(선택 규칙 본문은 default-providers) | R-09 |
| C-23 | `src/matchers/shared.ts:1-71` `normalizeMatcherTokenUsage`, `fail`, `graderFail`, `invertScore` | 실패 결과 모양·토큰 정규화 | R-25 |
| C-24 | `src/util/json.ts:134-421` `isEscapedQuote`, `convertSlashCommentsToHash`, `findJsonStringEnd`, `findJsonObjectEnd`, `extractJsonObjects`, `extractFirstJsonObject`; `src/util/yamlLoad.ts` `loadYaml`(js-yaml, `{json: true}`) | 관대한 JSON 객체 추출 알고리즘 | R-13, R-16, R-35 |
| C-25 | `src/assertions/contextUtils.ts:20-104` `resolveContext`, `serializeContext` | RAG 문맥 해석 | R-20, R-21 |
| C-26 | `src/assertions/utils.ts:12-52` `getFinalTest`, `:88-93` `coerceString`; `src/assertions/index.ts:483-566`, `:613-652` | `rubricPrompt`·`provider` 병합, 값 렌더, 컨텍스트 구성 (assertion-family C-07·C-11에 같은 위치) | R-01, R-03, R-04 |
| C-27 | `src/matchers/search.ts:20-149`; `src/matchers/agent.ts:17-75` | `search-rubric`·`agent-rubric` 매처 | R-35, R-36 |
| C-28 | `src/external/matchers/deepeval.ts:32-120`; `src/external/matchers/conversationRelevancyTemplate.ts`; `src/external/assertions/deepeval.ts:14-142` | `conversation-relevance` 매처·템플릿·창 처리 | R-37 |
| C-29 | `src/scheduler/retryPolicy.ts:10-89` | 기본 재시도 정책 상수·재시도 판정 | R-11 |

핸들러 쪽(`llmRubric.ts`, `factuality.ts`, `geval.ts`, `similar.ts`, `ragDefaults.ts` 등)과 `deriveVerdictFromGrader`의 호출 경계는 assertion-family C-22·C-23이 이미 가진다. 여기서 반복하지 않았다.

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(코드를 읽고 손으로 따라가 계산, 실행하지 않음). grader는 "응답 문자열을 정해진 대로 돌려주는 대체물"로 가정한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06~R-08, R-32 | `llm-rubric`, `value: 'Content contains a greeting'`, 출력 `Hello world`, `rubricPrompt` 없음. grader 응답 `{"reason":"ok","pass":true,"score":1}` | grader가 받은 프롬프트 = JSON 배열 문자열 `[{"role":"system","content":<C-01 system>},{"role":"user","content":"<Output>\nHello world\n</Output>\n<Rubric>\nContent contains a greeting\n</Rubric>"}]`. 결과 `pass:true, score:1, reason:'ok'`, `metadata.renderedGradingPrompt`가 같은 문자열 |
| T-02 | R-01, R-04, R-07 | `vars: {city:'Paris'}`, `value: 'Mentions {{city}}'`, 출력 `{"a": 1,  "b": [1, 2]}`(JSON 문자열) | user 메시지 = `<Output>\n{"a":1,"b":[1,2]}\n</Output>\n<Rubric>\nMentions Paris\n</Rubric>`(출력은 한 줄 JSON으로 정규화, rubric은 렌더). 출력이 `{{ city }}`라는 평문이면 grader에는 `{{ city }}` 그대로 간다 |
| T-03 | R-08, R-33 | 커스텀 `rubricPrompt: '[{"role":"user","content":"Q:{{question}} A:{{output}} R:{{rubric}}"}]'`, `vars: {question:'Q1', output:'USER'}`, 출력 `X`, `value: 'R1'` | 프롬프트 `[{"role":"user","content":"Q:Q1 A:X R:R1"}]`(사용자 변수 `output`은 실제 출력에 가려짐). 원본 prompt는 변수로 없다 |
| T-04 | R-14, R-15 | grader 응답을 바꿔 가며, 어서션 `threshold`: (a) 0.8, `{"pass":true,"score":0.6}` (b) 0.8, `{"pass":false,"score":0.9}` (c) 없음, `{"score":0.3,"reason":"r"}` (d) 없음, `{"score":0}` (e) 없음, `{"reason":"x"}` (f) 없음, `{"pass":"yes","score":"0.9"}` (g) 없음, `{"pass":1}` | (a) `pass:false, score:0.6, reason:'Score 0.6 below threshold 0.8'` (b) `pass:false, score:0.9`, reason이 같은 형식 (c) `pass:true, score:0.3, reason:'r'` (d) `pass:false, score:0, reason:'Score 0 below threshold undefined'` (e) `pass:false, score:0, graderError:true, reason:'Grader response contained neither a pass verdict nor a finite numeric score'` (f) `pass:true, score:0.9` (g) `pass:false, score:0` |
| T-05 | R-13, R-25, R-26 | grader 응답 (a) `Sure! The answer is yes.` (b) `Here is my verdict: {"pass": false, "score": 0.2, "reason": "x"} thanks` (c) `{"example":1} {"pass":true,"score":1}` | (a) `pass:false, score:0, reason:'Could not extract JSON from llm-rubric response', metadata.graderError:true` (b) 첫 객체 사용: `pass:false, score:0.2, reason:'x'` (c) 첫 객체만 보므로 T-04(e)와 같은 `graderError` 실패 |
| T-06 | R-25, R-26 | grader가 `{error:'HTTP 500'}`를 응답. 어서션을 `llm-rubric` / `factuality` / `select-best`로 각각 | `llm-rubric`·`factuality`: `pass:false, score:0, reason:'HTTP 500', graderError:true`(행은 `failureReason=ASSERT`). `select-best`: 모든 열 `pass:false, score:0, reason:'HTTP 500'`이고 `graderError` 없음 |
| T-07 | R-16 | `factuality`. 응답 (a) `{"category":"d","reason":"conflict"}` (b) `{"category":"F"}` (c) `(B) The submission adds detail.` (d) (c)에 `options.factuality:{superset:0}` | (a) `pass:false, score:0, reason:'conflict'` (b) `graderFail`, reason `Invalid category value: F` (c) `pass:true, score:1, reason:'The submission adds detail.'` (d) `pass:false, score:0` |
| T-08 | R-17 | `model-graded-closedqa`. 응답 (a) `…reasoning…\nY\nY` (b) `…\nN\nN` (c) `maybe` | (a) `pass:true, score:1, reason:'The submission meets the criterion:\n<응답>'` (b) `pass:false, score:0`(정상 판정, `graderError` 없음) (c) `graderFail`, reason `Model grader produced a malformed response:\nmaybe` |
| T-09 | R-18, R-05 | `g-eval`, 기준 하나, `threshold` 없음(0.7). (a) steps 응답 `{"steps":["a","b"]}`, evaluate 응답 `{"score":8,"reason":"ok"}` (b) steps 응답이 `{\n  "steps": ["a"]\n}` (c) evaluate 응답 `{"score":11,"reason":"x"}` (d) prompt가 빈 문자열 | (a) grader 2회 호출, `score:0.8, pass:true, reason:'ok'` (b) `graderFail`, reason이 `LLM-proposed evaluation steps are not in JSON format: …`로 시작 (c) `graderFail`, reason `G-Eval result score 11 is outside the expected 0-10 range` (d) `No source text to estimate reply`를 던져 행 `ERROR` |
| T-10 | R-23 | `select-best`, 출력 3개, `value: 'most concise'`. grader 응답 (a) `2` (b) `I pick text 1.` (c) `-1` (d) `7` (e) `none`. 출력이 1개인 경우 (f) | (a) `[false,false,true]`, reason `Output not selected: most concise` / `Output selected as the best: most concise` (b) 1번 선택 (c) 1번 선택(부호 무시) (d) 모두 `pass:false`, reason `Invalid select-best verdict: 7` (e) `Invalid select-best verdict: NaN` (f) `Invariant failed: select-best assertion must have at least two outputs to compare between`를 던짐 |
| T-11 | R-22 | `context-faithfulness`, `vars.query` 있음, 기본 threshold. longform 응답 `A is X.\nB is Y.`, NLI 응답 `… Final verdict for each statement in order: Yes. No.` / NLI 응답이 `unclear` / `rubricPrompt: 'x'`(문자열) | `score 0.5`, `pass:true`, reason `Faithfulness 0.50 is >= 0.5` / `graderFail`, reason `Could not parse context-faithfulness verdicts` / `Invariant failed: rubricPrompt must be an array`를 던져 행 `ERROR` |
| T-12 | R-20, R-05 | `context-recall`, `value: 'Paris is the capital.'`, `vars.context` 없음, `contextTransform` 없음. grader 응답 (a) `1. Paris is the capital. So [Attributed]\n2. Moon is cheese. So [Not Attributed]` (b) `I cannot do that` | 문맥 = 렌더된 prompt 전체. (a) `score 0.5, pass:true, reason:'Recall 0.50 is >= 0.5'` (b) `pass:false, score:0, metadata.graderError:true, reason:'Grader returned no [Attributed]/[Not Attributed] classifications'` |
| T-13 | R-21 | `context-relevance`, `vars.query` 있음, `vars.context: ['Paris is the capital of France.','The sky is blue.','Cats purr.']`. grader 응답 (a) `Paris is the capital of France.` (b) `Insufficient Information` (c) `I cannot answer` | (a) 관련 1/문맥 3 → `score 0.33, pass:false, reason:'Context relevance 0.33 is < 0.5'` (b) `score 0, pass:false`, `metadata.insufficientInformation:true` (c) `pass:false, score:0, graderError:true, reason:'Grader output does not quote the provided context'` |
| T-14 | R-19 | `answer-relevance`, `vars.query: 'Q'`, 생성 질문 3개의 코사인이 0.9·0.8·0.7 | grader 채팅 3회(이름공간 기본·`answer-relevance:sample:1`·`:2`)와 임베딩 4회. `score` 약 0.8, `pass:true`, reason `Relevance 0.80 is greater than threshold 0.5`, `metadata.generatedQuestions` 3개. 둘째 grader 호출이 `{error}`이면 그 즉시 `graderFail` |
| T-15 | R-24 | `similar`(코사인), `value: 'hi'`, 기본 threshold. provider가 `callSimilarityApi`로 0.8 / provider가 임베딩만 가지고 두 벡터가 같음 / `similar:euclidean`, 거리 1, `threshold: 2` / provider 오류 | `pass:true, score:0.8, reason:'Similarity 0.80 is greater than or equal to threshold 0.75'` / 코사인 1로 통과 / `pass:true, score:0.5, reason:'Distance 1.00 is less than or equal to threshold 2'` / `pass:false, score:0, reason:<오류>`(`graderError` 없음) |
| T-16 | R-30, R-38 | 같은 `llm-rubric`을 캐시를 켠 채 같은 입력·같은 grader로 두 번 평가 / `--repeat 2` / 설정에 `redteam`이 없음 | 둘째 호출은 `metadata.cachedResponse:true`·토큰 `cached` 집계 / repeat마다 별개 이름공간이라 grader를 각각 호출 / 원격 채점이 아니라 로컬 grader를 호출 |
| T-17 | R-25 | grader 응답 `output`이 객체 `{category:'A'}`. 어서션 `factuality` / `llm-rubric`(응답 `{pass:true,score:1}` 객체) | `factuality`: `Invariant failed: factuality produced malformed response`를 던져 행 `ERROR`. `llm-rubric`: 객체를 판정으로 받아 `pass:true, score:1` |
| T-18 | R-06 | `rubricPrompt: file://rubric.json`, 파일 내용 `[{"role":"user","content":"A: {{output}} / R: {{rubric}}"}]`, 파일 없음인 경우도 | 파일 원문을 읽어 JSON 문자열 값을 렌더하고 `JSON.stringify`한 배열 문자열이 grader 프롬프트가 된다. 파일이 없으면 `File does not exist: <절대경로>`를 던진다 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]

기준: `promptfoo@dfe2d45e6f72be85c866b746e3852de0dd7622c5`, 줄 번호는 이 SHA.

| R-ID / T-ID | 근거 (`파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `src/assertions/index.ts:483-566`(문자열 값 렌더, `getNunjucksEngine()` `:324`); `src/util/templates.ts:474-503`(비 grader 모드는 `PROMPTFOO_DISABLE_TEMPLATING`이면 원문 반환) | 코드 읽기 |
| R-02 | `src/assertions/llmRubric.ts:16-27`, `agentRubric.ts:16-26`, `factuality.ts:16-21`, `modelGradedClosedQa.ts:16-21`, `searchRubric.ts:17-19`, `contextRecall.ts:28-32` | 코드 읽기 |
| R-03 | `src/assertions/utils.ts:12-52`; `llmRubric.ts:22-27` | 코드 읽기. 병합 규칙은 assertion-family R-10 |
| R-04 | `src/assertions/index.ts:443-450,644-651`, `utils.ts:88-93`; `matchers/shared.ts:101-106`; `assertions/answerRelevance.ts:15-20`, `contextFaithfulness.ts:28-35`; `searchRubric.ts:21-29` | 코드 읽기. `0.10`→`0.1`은 `JSON.parse` 의미에서 도출(실행 안 함) |
| R-05 | `src/evaluator.ts:1601-1631`(`prompt: renderedPrompt`), `:877-893`; `llmGrading.ts:337-338,396-397`, `:462-467`; `answerRelevance.ts:20`; `contextRecall.ts:34`; `llmGrading.ts:250-253`(`llm-rubric` 변수에 prompt 없음) | 코드 읽기 |
| R-06 | C-10 `rubric.ts:61-111`; `llmGrading.ts:481-485,539-543`(g-eval 객체 키); `rag.ts:421-434`; `external/matchers/deepeval.ts:65-74` | 코드 읽기. `maybeLoadFromExternalFile` 배열 경로·JS 로더 내부는 미탐색 |
| R-07 | C-10 `rubric.ts:113-160`; `src/util/templates.ts:474-503` | 코드 읽기. `test/matchers/llm-rubric.test.ts`의 `renderLlmRubricPrompt` 사례명(`:2633-2776`)만 확인 |
| R-08 | `llmGrading.ts:250-253,338,397`; `rag.ts:60,175-179,288-291,436-440,466-470`; `comparison.ts:35-39`; `search.ts:79-83`; `agent.ts:61-65`; `test/matchers/llm-rubric.test.ts:169`의 사례명("reserved output and rubric vars ahead of user vars") | 코드 읽기, 사례명 확인 |
| R-09 | C-22 `providers.ts:205-350`; 각 매처의 `getAndCheckProvider` 호출: `llmGrading.ts:343-348,402-407,467-472`, `rubric.ts:905-913`, `rag.ts:42-53,165-170,278-283,412-417`, `comparison.ts:27-32`, `similarity.ts:217-223` | 코드 읽기. 선택 규칙 본문은 default-providers |
| R-10 | C-21 `providers.ts:132-164`, `:46-49`; `src/assertions/index.ts:613-628`(`providerCallContext`) | 코드 읽기. `isGrading`을 읽는 곳은 `providers/openai/decisions.ts`뿐(grep) |
| R-11 | C-21 `providers.ts:71-129`; C-29 `scheduler/retryPolicy.ts:10-15,45-89`; `scheduler/rateLimitRegistry.ts:56-66,142,194-232`; `providerRateLimitState.ts:118-137,200-330`(일부); `src/evaluator.ts:5935-5937`, `:560-590` | 코드 읽기. 레이트리밋 판정 함수(`isProviderResponseRateLimited`)·대기열 세부는 미탐색 |
| R-12 | `src/matchers/*.ts` 전체를 읽고 `callProviderWithContext` 호출 지점 대조; `src/assertions/geval.ts:36-56`; `rag.ts:62-88` | 코드 읽기. "없다"는 이 디렉터리 안에서 찾지 못했다는 뜻 |
| R-13 | C-11 `rubric.ts:767-809`; C-24 `util/json.ts:334-421` | 코드 읽기. 대체물 없이 `extractJsonObjects`의 분기만 따라감 |
| R-14 | C-11 `rubric.ts:837-874`, `:938-951`; 문서 `llm-rubric.md` "Pass vs. Score Semantics"와 일치; `test/matchers/llm-rubric.test.ts:1917-2050`(문자열 점수·문자열 `pass`·점수 누락 사례를 읽어 R-14와 대조) | 코드 읽기. `pass:1`→거짓, `score:null`→0은 코드 의미에서 도출 |
| R-15 | C-11 `rubric.ts:811-835`, `:950-978` | 코드 읽기 |
| R-16 | C-13 `llmGrading.ts:48-129`, `:323-380`; `types/index.ts:174-199`(`factuality` 점수표 타입) | 코드 읽기 |
| R-17 | C-13 `llmGrading.ts:382-442` | 코드 읽기 |
| R-18 | C-15 `llmGrading.ts:454-612`; C-08 `prompts/index.ts:252-307`; `src/assertions/geval.ts:24,88-115` | 코드 읽기. 정규식 `.`이 줄바꿈과 일치하지 않는다는 점은 JS 정규식 의미에서 도출 |
| R-19 | C-16 `rag.ts:34-155`; `cache.ts:272-286`; `assertions/answerRelevance.ts:7-35` | 코드 읽기 |
| R-20 | C-17 `rag.ts:157-269`; C-25 `contextUtils.ts:20-104`; `assertions/contextRecall.ts:18-54` | 코드 읽기 |
| R-21 | C-17 `rag.ts:271-401`; C-18 `shared.ts:108-150`; `assertions/contextRelevance.ts:18-58` | 코드 읽기 |
| R-22 | C-17 `rag.ts:403-529`; `assertions/contextFaithfulness.ts:18-64` | 코드 읽기 |
| R-23 | C-19 `comparison.ts:16-92`; `src/assertions/index.ts:914-943`(`runCompareAssertion`); `src/evaluator.ts:5170-5207` | 코드 읽기. 열 사이 흐름은 assertion-family R-49~R-52 |
| R-24 | C-20 `similarity.ts:29-240`; `assertions/similar.ts:6-108` | 코드 읽기 |
| R-25 | C-23 `shared.ts:35-61`; `rubric.ts:811-835,927-936`; `llmGrading.ts:357-361,415-419,498-505,561-568`; `rag.ts:79-81,102-104,192-194,303-305,454-456,484-486`; `comparison.ts:61-69,71-78`; `similarity.ts:126-135,170-178` | 코드 읽기 |
| R-26 | `src/evaluator.ts:624-640`; `src/` 전체에서 `graderError` 검색(평가기에 읽는 곳 없음; 읽는 곳은 `redteam/`·`assertions/`의 반전 처리); assertion-family R-20·R-46 | 코드 읽기, grep 결과 |
| R-27 | `src/providers/shared.ts:92-96`; `cache.ts:919`; `scheduler/rateLimitRegistry.ts:44`; `src/evaluator.ts:4508-4575`, `:3860-3894`; `src/envars.ts:639-641` | 코드 읽기. provider별 오류 형태 미확인 |
| R-28 | `rubric.ts:837-874`; `llmGrading.ts:66-84,606-611`; `rag.ts:126-155,250-268,372-398,519-527`; `assertions/ragDefaults.ts:6`, `geval.ts:24`, `similar.ts:22`; `external/assertions/deepeval.ts:15-16`; 문서 `llm-rubric.md`의 "0.0-1.0"·"Threshold Support" | 코드 읽기. 문서는 클램프를 말하지 않고 코드에도 클램프가 없다(2.1 아래 차이 참조) |
| R-29 | `src/providers/openai/gpt6.ts:331-399`, `chat.ts:488-516,625-672`; `src/providers/anthropic/util.ts:249-323`(Sonnet 5 행), `:522-570`, `messages.ts:946-949,985-1000`; `src/providers/openai/defaults.ts`·`anthropic/defaults.ts`(기본 모델 이름); 문서 `model-graded/index.md`의 "built-in OpenAI grader … does not send temperature" | 코드 읽기. 요청 본문 구성만 확인했고 API 수락은 미확인. OpenAI 문서 문장과 일치 |
| R-30 | `src/evaluator.ts:1760-1762`(`runEval`), `:4329-4335`, `:5181-5207`; `cache.ts:179-286`; `providers/openai/chat.ts:910-930`(`fetchWithCache`); response-cache R-06·R-07 | 코드 읽기. 캐시 키·적중 규칙은 response-cache |
| R-31 | `src/matchers/providers.ts:132-164`; `comparison.ts:35-48`; default-providers R-20 | 코드 읽기 |
| R-32 | C-01 `prompts/grading.ts:11-30`; `llmGrading.ts:239-255`; `rubric.ts:902-979` | 코드 읽기. 최종 문자열 형태는 R-07 규칙에서 도출 |
| R-33 | `llmGrading.ts:250-253`; `src/assertions/index.ts:443-450,553` | 코드 읽기 |
| R-34 | `llmRubric.ts:29-39`; `llmGrading.ts:131-179,206-211`; `rubric.ts:31-52,314-394,396-765`; 문서 `llm-rubric.md`의 "Audio output" | 코드 읽기, 개요 수준 |
| R-35 | C-27 `search.ts:20-149`; `assertions/searchRubric.ts:7-50`; C-06 | 코드 읽기. grader 사슬은 default-providers R-22 |
| R-36 | C-27 `agent.ts:17-75`; `assertions/agentRubric.ts:7-39` | 코드 읽기 |
| R-37 | `llmGrading.ts:269-298`; `assertions/trajectory.ts:632-665`; C-28 `external/matchers/deepeval.ts:32-120`, `external/assertions/deepeval.ts:14-142` | 코드 읽기. 트레이스 요약(`trajectoryUtils.ts:498`)·템플릿 `generateReason` 본문은 미탐색 |
| R-38 | `llmGrading.ts:200-237`; `similarity.ts:198-215`; `matchers/providers.ts:33-44`; default-providers R-23 | 코드 읽기. `shouldGenerateRemote` 내부는 미탐색 |
| T-01~T-18 | 해당 R-ID의 근거 | 손으로 따라 계산. 실행·테스트 확인 없음 |

문서와 구현이 다른 곳(구현을 사실로 썼다):

- `site/docs/…/model-graded/llm-rubric.md`는 `llm-rubric`의 점수가 "0.0~1.0"이라고 쓰나 구현은 점수를 클램프하지 않는다(R-28). 문서의 `threshold`가 "LLM이 준 점수에 적용된다"는 문장은 코드와 같다.
- 같은 문서의 "built-in OpenAI grader already defaults to `temperature=0`"는 구현과 다르다. 기본 OpenAI grader(`gpt-6-sol` chat)는 temperature를 보내지 않는다(R-29). `model-graded/index.md`의 반대 문장("does not send `temperature`")이 구현과 같다. 같은 문서의 기본 grader 이름(`gpt-5`)·`g-eval.md`의 `gpt-4.1-2025-04-14`는 코드의 기본 grader(default-providers 1.3)와 다르다(문서가 낡음).
- `llm-rubric.md`의 "Option 1: rubricPrompt Override … works with `llm-rubric`, `g-eval`, and `model-graded-closedqa`"에서 `g-eval`은 맞지 않는다. `g-eval`은 문자열·배열 `rubricPrompt`를 무시하고 `{steps, evaluate}` 객체만 읽는다(R-06, R-18). 같은 규칙이 `options.rubricPrompt`의 평범한 객체를 허용하는 설정 스키마와 맞는지는 확인하지 못했다.
- `model-graded/index.md`는 `context-faithfulness`의 `rubricPrompt` 형식을 따로 적지 않는다. 구현은 문자열 `rubricPrompt`를 배열이 아니라는 이유로 던진다(R-06). 그러므로 테스트 전체에 걸친 `llm-rubric`용 `rubricPrompt`와 함께 `context-faithfulness`를 쓰면 행이 `ERROR`가 된다.
- 개요(overview) 기능 지도 행의 근거 칸 "프롬프트 템플릿 본문 미탐색"은 이 스펙으로 해소됐다(C-01~C-09).

### 2.2 코드 읽는 순서 [선택]

1. `src/assertions/llmRubric.ts` → `src/matchers/llmGrading.ts:181` `matchesLlmRubric` → `src/matchers/rubric.ts:876` `runJsonGradingPrompt`(프롬프트 로드·렌더·grader 선택·호출·파싱·판정이 한 함수에 있다) → `src/prompts/grading.ts:11` 기본 프롬프트.
2. 호출 경로: `src/matchers/providers.ts:132` `callProviderWithContext` → `:71` `callGradingProvider`(스케줄링).
3. 응답 형식이 다른 매처: `llmGrading.ts` 아래쪽(`factuality`, `closedqa`, `g-eval`), `rag.ts`(RAGAS 포팅, 줄·문장 단위 해석), `comparison.ts`(`select-best`), `similarity.ts`(임베딩).
4. 원본 전략: 프롬프트 템플릿과 변수는 매처가 직접 구성하고, 판정은 응답 문자열을 정규식·JSON 추출로 해석한다. grader는 구조화 출력(JSON 스키마)을 강제하지 않고 지시문으로 요청한다(예외: default-providers의 계열별 `llmRubricProvider`가 응답 형식을 provider 쪽에서 강제할 수 있다, default-providers R-08).

## 적용 메모

내 스킬 평가 환경에 가져올 때의 메모다. 본문(원본 동작)과 구분한다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-25, R-26 | grader 장애(`graderError`·`fail`)를 판정 "불합격"과 같은 행 필드로 두지 않고 `failureReason`(또는 별도 필드)으로 분리해 기록한다. `select-best`·`similar`의 `fail`에도 같은 표시를 붙인다 | 원본은 둘 다 `ASSERT` 실패로 합쳐져 모델 적합도 수치에 grader 장애가 섞인다 | 결과 레코드 필드 추가. T-06을 "전 어서션 `graderError` 표시"로 대체 |
| R-12, R-13, R-29 | 심판 점수의 흔들림을 재려면 같은 (출력, rubric)을 N회 채점하는 모드와, grader id·샘플링 설정을 결과에 남기는 기록을 둔다. grader는 `{id, config}`로 고정해 모델 버전·샘플링 설정을 명시한다 | 원본은 1회 호출·재시도 없음·기본 grader가 `temperature`를 보내지 않아 같은 입력에서 점수가 흔들릴 수 있고, 어떤 grader로 채점했는지가 결과에 남지 않는다 | 결과에 `graderId`·`graderConfig` 추가, 반복 채점 연산 추가 |
| R-13 | JSON 추출을 "첫 객체"가 아니라 `pass`/`score` 키를 가진 객체를 고르거나 마지막 객체를 쓰도록 하고, 추출 실패를 한 번 재요청하는 선택지를 둔다 | 사고 과정에 예시 JSON이 먼저 나오는 grader에서는 첫 객체가 판정이 아니다(T-05 c) | 파서 규칙 변경, T-05(c)를 바꾼 규칙에 맞춰 대체 |
| R-14, R-28 | `score`를 0~1로 검증·클램프하고, `pass`와 `score`가 어긋날 때(예: `pass:true, score:0`)를 오류나 경고로 다룬다. `pass`가 없으면 거부 | 원본은 `pass:true, score:0` 통과, `pass:1`을 거짓으로 읽는 등 예외 규칙이 많다 | 판정 규칙 단순화, T-04 일부 대체 |
| R-05, R-32, R-33 | 스킬 결과 채점용 기본 프롬프트에 원 요청(렌더된 prompt)·스킬 이름·대상 모델·`skillCalls` 요약을 변수로 넣는다. 스킬 본문(SKILL.md)은 토큰이 크므로 요약·해시로 대신한다 | 원본 `llm-rubric`은 출력과 rubric만 보여 "요청 의도에 맞게 스킬이 동작했는가"를 판단하기 어렵고, `factuality`·`g-eval`에 prompt 전체(스킬 본문 포함)가 가면 비용이 커진다 | `llm-rubric` 변수 확장, T-01에 변수 추가 |
| R-23, R-31 | 여러 모델 출력 비교에서 열 순서를 섞어 여러 번 묻고 위치 편향을 평균한다 | 원본은 순서를 고정하고 한 번만 묻는다 | `select-best`의 호출 수 증가 |
