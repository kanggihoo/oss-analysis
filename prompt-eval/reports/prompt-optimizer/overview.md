---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - README.md
  - LICENSE
  - package.json
  - pnpm-workspace.yaml
  - vercel.json
  - wrangler.jsonc
  - middleware.js
  - api/auth.js
  - Dockerfile
  - docker/nginx.conf
  - docker/supervisord.conf
  - docker/generate-config.sh
  - docker/generate-auth.sh
  - scripts/run-structured-compare-calibration.mjs
  - packages/core/package.json
  - packages/core/src/index.ts
  - packages/core/src/services/prompt/service.ts
  - packages/core/src/services/prompt/types.ts
  - packages/core/src/services/evaluation/service.ts
  - packages/core/src/services/evaluation/types.ts
  - packages/core/src/services/evaluation/structured-compare-prompts.ts
  - packages/core/src/services/evaluation/rewrite-from-evaluation.ts
  - packages/core/src/services/compare/service.ts
  - packages/core/src/services/llm/service.ts
  - packages/core/src/services/llm/types.ts
  - packages/core/src/services/llm/adapters/registry.ts
  - packages/core/src/services/llm/adapters/abstract-adapter.ts
  - packages/core/src/services/llm/adapters/openai-adapter.ts
  - packages/core/src/services/llm/adapters/anthropic-adapter.ts
  - packages/core/src/services/model/manager.ts
  - packages/core/src/services/model/types.ts
  - packages/core/src/services/model/defaults.ts
  - packages/core/src/services/storage/factory.ts
  - packages/core/src/services/template/processor.ts
  - packages/core/src/services/template/default-templates/index.ts
  - packages/core/src/services/template/default-templates/optimize/general-optimize_en.ts
  - packages/core/src/services/template/default-templates/iterate/iterate_en.ts
  - packages/core/src/services/template/default-templates/user-optimize/user-prompt-basic_en.ts
  - packages/core/src/services/template/default-templates/evaluation/content.ts
  - packages/core/src/services/data/manager.ts
  - packages/core/src/utils/environment.ts
  - packages/mcp-server/package.json
  - packages/mcp-server/src/index.ts
  - packages/mcp-server/src/config/environment.ts
  - packages/mcp-server/src/config/models.ts
  - packages/mcp-server/src/config/templates.ts
  - packages/mcp-server/src/adapters/core-services.ts
  - packages/mcp-server/src/adapters/parameter-adapter.ts
  - packages/ui/src/composables/prompt/usePromptTester.ts
  - packages/ui/src/composables/prompt/useEvaluationHandler.ts
  - packages/ui/src/composables/prompt/compareEvaluation.ts
  - packages/ui/src/composables/system/useAppInitializer.ts
  - packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue
  - packages/ui/src/components/context-mode/ContextSystemWorkspace.vue
  - packages/ui/src/router/workspaceRoutes.ts
  - packages/ui/src/utils/runTasksSequentially.ts
  - packages/ui/src/utils/remote-backup.ts
  - packages/ui/src/integrations/prompt-garden.integration.ts
  - packages/web/src/main.ts
  - packages/extension/public/manifest.json
  - packages/extension/public/background.js
  - packages/desktop/main.js
  - packages/desktop/package.json
  - site/package.json
  - site/README.md
  - mkdocs/mkdocs.yml
---

# prompt-optimizer Analysis Overview

경로 표기: 이 문서의 `파일:줄`은 모두 `prompt-eval/repos/prompt-optimizer/` 기준이다. 검증 수준은 `코드 확인` / `추론` / `미확인`만 쓴다. 설치·빌드·실행은 하지 않았으므로 `실행 확인`은 없다. 문서(README, `docs/`)의 주장은 코드로 확인하기 전까지 후보로만 읽었다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/linshenkx/prompt-optimizer` (`prompt-eval/artifacts/prompt-optimizer/repo-metadata.txt`)
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 브랜치 `develop`(기본), 기준 커밋 날짜 2026-10-22, 루트 `package.json` 버전 2.11.13)
- **분석 목적**: 내가 만든 스킬(SKILL.md)·프롬프트를 (1) 평가하고, (2) 어떤 모델에서 가장 잘 되는지 비교하고, (3) 개선하는 데 쓸 수 있는 도구인지 파악한다. 이 문서는 기능 지도와 구조도까지(범위 승인 전)이고, 기능 스펙은 쓰지 않았다.
- **라이선스**: AGPL-3.0 only — `LICENSE`(1~4줄: "Prompt Optimizer, Copyright (C) 2025 linshenkx ... licensed under the GNU Affero General Public License v3.0 only", 이어 AGPL v3 전문 669줄). `package.json`의 `license` 필드는 루트(`package.json:85`), `packages/desktop`(`:104`), `packages/mcp-server`(`:27`), `packages/ui`(`:5`) 모두 `AGPL-3.0-only`로 LICENSE와 같다. `packages/core`·`web`·`extension`·`site`의 `package.json`에는 `license` 필드가 없다. 하위 디렉터리에 별도 LICENSE 파일은 없다(`git ls-files`와 `find`로 확인, `node_modules` 제외). (코드 확인)
- **분석 대상 제품**: pnpm 워크스페이스 `packages/*`(`pnpm-workspace.yaml`) 6개 — `core`, `ui`, `web`, `extension`, `desktop`, `mcp-server`. 워크스페이스 밖의 배포 입구: `api/auth.js` + `middleware.js` + `vercel.json`(Vercel), `wrangler.jsonc`(Cloudflare), `Dockerfile` + `docker/`(Docker), `site/`(별도 Vite 홍보 사이트, 자체 `package.json`·`pnpm-lock.yaml`), `mkdocs/`(문서 사이트). (코드 확인)
- **스펙 범위**: 2026-10-22 승인. 목적은 내 스킬의 평가·개선·모델 적합도 기록 환경을 만드는 데 쓸 부분만 스펙으로 쓴다.
  - 승인한 행(6): LLM 평가(평가 요청·응답 계약을 같은 스펙에 포함), 반복 개선·평가 기반 재작성, 프롬프트 최적화, 템플릿 렌더링 규칙(공유 계약만, 관리 UI·저장은 제외), 히스토리·버전 체인(데이터 모델 중심), 구조화 비교 보정 스크립트(부속, 사용자 승인).
  - 제외(이유: 사용자 제외 또는 이번 목적 밖): 다중 모델 테스트 영역(promptfoo 매트릭스가 대신함), 텍스트 diff 비교, 이미지 모드·이미지 어댑터, 모델 관리·텍스트 LLM 어댑터(경계로만 다룸), Pro 모드, 즐겨찾기, 데이터 가져오기·내보내기, MCP 서버, 웹 앱 셸, 부속 중 Prompt Garden·데스크톱·Chrome 확장·Docker·Vercel/Cloudflare·사이트.

용어(처음 한 번만).
- **워크스페이스(앱 화면)**: 앱의 작업 화면. 라우트는 `/basic/{system,user}`, `/pro/{multi,variable}`, `/image/{text2image,image2image,multiimage}` 7개(`packages/ui/src/router/workspaceRoutes.ts:1-22`). (코드 확인)
- **스냅샷**: 평가 요청의 한 실행 단위. 프롬프트 + 실제 출력 + 모델 key를 묶은 것(`packages/core/src/services/evaluation/types.ts` `EvaluationSnapshot`). (코드 확인)
- **메타 프롬프트**: 사용자의 프롬프트를 "입력 데이터"로 받아 고쳐 쓰라고 시키는 내장 템플릿. 이 문서에서는 `default-templates/` 아래 파일을 가리킨다.

---

## 2. 프로젝트 개요

README는 이 프로젝트를 "AI 프롬프트 최적화 도구"라 소개하고 웹·데스크톱·Chrome 확장·Docker 네 방식으로 쓴다고 한다(`README.md` "Project Introduction"). 코드로 보면 한 벌의 **TypeScript 코어**(`packages/core`: 최적화·평가·테스트·모델 호출 서비스, 내장 메타 프롬프트)와 한 벌의 **Vue UI**(`packages/ui`)가 있고, `web`·`extension`·`desktop`은 그 UI를 서로 다른 환경에 싣는 껍데기다. 같은 코어를 Node에서 쓰는 두 번째 입구가 `packages/mcp-server`(MCP 도구 3개)다. 최적화 알고리즘은 "내장 메타 프롬프트를 템플릿에 채워 선택한 LLM을 한 번 호출"하는 구조이고, 평가도 "평가용 메타 프롬프트로 LLM을 심판으로 호출해 JSON 점수를 받는" 구조다. 규칙 기반 지표나 데이터셋 일괄 실행기는 찾지 못했다(아래 Q1).

### 목적 질문에 대한 초기 답

이 소절은 사용자 목적(Q1~Q3)에 한정한다. 기능 전체 지도는 그 아래 표를 본다.

#### Q1. 평가: 프롬프트를 여러 모델에 돌려 비교하나? 케이스를 일괄로 돌리나?

**결론: 즉석 1회 비교다. 한 화면에서 같은 입력 1개를 최대 4개 (프롬프트 버전 × 모델) 조합에 병렬로 돌리고, 점수화는 별도 LLM 심판이 한다. 평가셋(여러 케이스) 일괄 실행은 UI·코어에서 찾지 못했다.**

| 주장 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|
| 테스트 영역은 열 a/b/c/d 최대 4개이고 열마다 프롬프트 버전(workspace/previous/original/특정 버전)과 모델 key를 따로 고른다 | `packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue:879` `ALL_VARIANT_IDS`, `:890` `variantModelKeyModels`, `:1047-1076`·`:1152` `getVariantTestInput` | 코드 확인 |
| 입력은 시스템 프롬프트 모드에서 텍스트 1개(`logic.testContent`) + 선택 이미지. 각 열은 "버전의 프롬프트를 system, 테스트 입력을 user"로 보낸다 | `BasicSystemWorkspace.vue:1152-1182` `getVariantTestInput` → `:1185` `runVariant` → `promptService.testPromptStream(systemPrompt, userPrompt, modelKey, callbacks)` | 코드 확인 |
| "전체 실행"은 활성 열을 병렬로 돌린다. 테스트 모드·webdriver 환경에서는 순차 | `BasicSystemWorkspace.vue:1277` `runAllVariants`, `packages/ui/src/utils/runTasksSequentially.ts:12-37` `detectTaskExecutionMode`, `:28` `runTasksWithExecutionMode` | 코드 확인 |
| 실제 호출 경로: `PromptService.testPromptStream` → `LLMService.sendMessageStream` → 모델 key로 어댑터 선택 → SDK 호출. 사용자 프롬프트가 user 모드면 system 없이 user 한 개만 보낸다 | `packages/core/src/services/prompt/service.ts:456` `testPromptStream`, `:383` `testPrompt`(system 비어 있으면 생략), `packages/core/src/services/llm/service.ts:126` `sendMessageStream`, `llm/adapters/registry.ts` `TextAdapterRegistry` | 코드 확인(testPrompt, 레지스트리) / `testPromptStream` 본문 세부는 testPrompt와 같은 구조로 추론 |
| 실행 결과는 점수 없이 열별 텍스트·reasoning만 쌓인다. 점수는 사용자가 "평가"를 눌러야 생긴다 | `usePromptTester.ts:129-145` `onToken`/`onReasoningToken`, `BasicSystemWorkspace.vue:1404` `comparePayload`, `packages/ui/src/composables/prompt/useEvaluationHandler.ts:331` `handleEvaluate` | 코드 확인 |
| 모델 간 비교 평가: 열들을 스냅샷으로 묶어 `type: 'compare'` 평가 요청을 만든다. 같은 프롬프트 + 공유 테스트 케이스 + 서로 다른 modelKey이면 `crossModelComparison`으로 자동 판정 | `BasicSystemWorkspace.vue:1404-1422` `comparePayload`, `packages/core/src/services/evaluation/service.ts:2005-2015` `normalizeCompareRequest`(`crossModelComparison`), `evaluation/types.ts` `CompareEvaluationRequest` | 코드 확인 |
| 평가 방식은 LLM 심판이다. 평가용 모델은 `evaluationModelKey`로 별도 지정한다. 결과 JSON: `score.overall`(0-100) + 차원 점수 + `improvements` + `summary` + `patchPlan`. result 평가의 차원은 goalAchievement·outputQuality·constraintCompliance·promptEffectiveness, compare는 5개 차원 | `evaluation/types.ts` `EvaluationRequestBase.evaluationModelKey`·`EvaluationResponse`, `evaluation/service.ts:275` `evaluate`, `default-templates/evaluation/content.ts:927`·`:970`(JSON 계약) | 코드 확인 |
| 구조화 비교(structured compare): 역할(target/baseline/reference/…)이 정해진 열 쌍마다 판정 LLM 호출을 `Promise.all`로 병렬 실행하고, 그 결과를 합성(synthesis) LLM 호출 한 번으로 묶는다. 총 호출 수 = 쌍 수 + 1 | `evaluation/service.ts:2163` `evaluateStructuredCompare`, `:2281-2309` `executeStructuredCompareJudgePlan`, `structured-compare-prompts.ts` | 코드 확인 |
| 코어 요청 타입은 `testCases: EvaluationTestCase[]`·`snapshots[]`(스냅샷 2개 이상)를 받지만, 기본 화면은 공유 케이스 1개만 만든다. 시스템 모드는 `testCases: [buildSharedTextTestCaseDraft()]`, Pro 멀티 모드는 열마다 대화 케이스 1개 | `BasicSystemWorkspace.vue:1358` `buildSharedTextTestCaseDraft`, `ContextSystemWorkspace.vue:1702`, `packages/ui/src/composables/prompt/compareEvaluation.ts` `buildCompareEvaluationPayload` | 코드 확인 |
| 데이터셋·CSV·배치 실행 코드는 `core/src`·`ui/src`에서 찾지 못했다(검색어 dataset, csv, batch, test suite: 변수 가져오기 `VariableImporter.vue`와 템플릿 문구만 일치) | `packages/core/src`·`packages/ui/src` 전체 검색 | 추론(전수 검색이 아닌 키워드 검색) |
| 코어를 Node에서 직접 호출해(live 케이스 1개만 4개 스냅샷을 실행하고 합성 5개는 소스에 박힌 출력으로 평가)  평가·재작성까지 돌리는 개발자용 스크립트가 있다. 케이스는 파일 안에 하드코딩이고(`LIVE_BASIC_SYSTEM_CASE`, `SYNTHETIC_CASES`), 모델은 `.env.local`의 `custom`·`deepseek` 두 개로 고정 | `scripts/run-structured-compare-calibration.mjs:50`·`:89`·`:1127-1160` `createServices`·`:1170` `runLiveCase`, `package.json` `compare:calibrate` | 코드 확인(구조) / 실행하지 않음 |

의미: 내 스킬(SKILL.md)을 시스템 프롬프트 칸에 붙여 넣고 같은 입력을 4개 모델에 한 번에 돌려 눈으로 비교하고, LLM 심판의 점수·근거를 보는 용도는 맞다. 여러 입력 케이스를 모아 모델별 평균 점수를 내는 용도는 이 레포만으로는 안 된다(`추론`: 코어 API를 직접 반복 호출하는 코드를 따로 써야 한다). 점수는 LLM 심판의 주관 판정이라 같은 입력에서도 흔들릴 수 있고, 이를 보정하려는 스크립트가 있다는 점이 오히려 그 불안정을 개발자도 의식했다는 신호다(`추론`).

#### Q2. 개선: 최적화 알고리즘의 실체와 MCP 도구

**결론: 알고리즘은 "내장 메타 프롬프트(템플릿)에 사용자 프롬프트를 채워 선택한 모델을 1회 호출하고 응답 전체를 새 프롬프트로 쓰는" 단일 호출이다. 반복 개선은 사용자가 요구사항을 적고 `iterate` 템플릿으로 다시 호출하는 수동 루프이고, 평가 결과를 요구사항으로 바꿔 넣는 "스마트 재작성"이 평가→개선을 잇는다. MCP는 도구 3개(최적화 2 + 반복 1)뿐이며 평가·테스트 도구는 없다.**

| 주장 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|
| 최적화 호출: 템플릿 조회 → `TemplateProcessor.processTemplate`로 메시지 배열 생성 → `llmService.sendMessage` 1회 → 빈 응답이면 오류. 결과 문자열이 그대로 반환값 | `prompt/service.ts:133` `optimizePrompt`, `:909` `resolveOptimizationMessages` | 코드 확인 |
| 템플릿이 문자열이면 "템플릿 = system, 원본 프롬프트 = user"로, 배열이면 Mustache 렌더링한 메시지들로 바뀐다 | `packages/core/src/services/template/processor.ts:84-96`(문자열), `:99-117`(배열) | 코드 확인 |
| 시스템 프롬프트 모드(`optimizationMode: 'system'`)는 `optimize` 유형 템플릿을 쓴다: `general-optimize`(Role/Profile/Skills/Rules/Workflows/Initialization 구조로 확장), `analytical-optimize`, `output-format-optimize`, `soul-openclaw-compose`, `soul-hermes-compose`(SOUL.md 작성용). 모두 `default-templates/optimize/` | `default-templates/index.ts` import 목록, `optimize/general-optimize_en.ts`(본문 읽음) | 코드 확인(general-optimize 본문) / 나머지는 id·파일 이름만 확인 |
| 사용자 프롬프트 모드(`'user'`)는 `userOptimize` 유형: `user-prompt-basic`(명료성·구체성 개선, "프롬프트를 실행하지 말고 고쳐 쓰기만" 규칙. 이 규칙은 사용자 모드 3종 모두에 있고 시스템 모드에서는 `analytical-optimize`와 `soul-*`에만 있다: prompt-optimize R-05~R-07), `user-prompt-professional`, `user-prompt-planning`. `default-templates/user-optimize/` | `user-optimize/user-prompt-basic_en.ts`(본문 읽음), `index.ts` | 코드 확인(basic) / professional·planning은 이름만 확인 |
| 두 모드의 차이는 요청의 `optimizationMode`가 템플릿 유형을 고르는 것뿐이고(`"user" ? "userOptimize" : "optimize"`), 그 외 분기는 같은 함수다. 변수 `{{...}}`는 템플릿 문구로 "그대로 보존" 지시 | `prompt/service.ts:909-915`, `general-optimize_en.ts` 끝 문단 | 코드 확인 |
| 기본 템플릿은 상수 `DEFAULT_TEMPLATES`(optimize=`general-optimize`, iterate=`iterate`)가 있으나, 최적화 경로의 기본 선택은 `listTemplatesByType` 목록의 첫 번째다. 목록 순서는 내장이 먼저이고 `ALL_TEMPLATES` 선언 순서다(`default-templates/index.ts:157-190`): 시스템 모드는 `general-optimize`, 사용자 모드는 `user-prompt-professional`이며 `DEFAULT_TEMPLATES.OPTIMIZE`는 읽히지 않는다(prompt-optimize R-04) | `prompt/service.ts:27-31`, `:992-1010` `getDefaultTemplateId`, `packages/mcp-server/src/config/templates.ts` `getDefaultTemplateId` | 코드 확인(선택 방식) / 코드 확인(정렬) |
| 반복 개선: `iteratePrompt(originalPrompt, lastOptimizedPrompt, iterateInput, modelKey, templateId)`는 한 번의 LLM 호출이다. 배열형 템플릿만 허용하고 `lastOptimizedPrompt`·`iterateInput`을 JSON 증거로 넣는다. "요구사항을 실행하지 말고 프롬프트에 녹여 넣어라"는 예시 3개가 템플릿에 있다 | `prompt/service.ts:274-380` `iteratePrompt`, `iterate/iterate_en.ts` | 코드 확인 |
| 반복 횟수·종료 조건을 코어가 관리하지 않는다. 호출할 때마다 한 번이고, 버전 체인은 UI의 히스토리 매니저가 저장한다(서비스 코드 주석: "히스토리 저장은 UI층") | `prompt/service.ts:161`·`:365`(주석), `packages/core/src/services/history/manager.ts` `createNewChain`·`addIteration` | 코드 확인 |
| 평가→개선 연결: 평가 결과(`summary`·`improvements`·`patchPlan`·compare 신호)를 압축해 `buildRewritePromptFromEvaluation`으로 "재작성 입력문"을 만들고, 이를 `runIterateWithInput`으로 iterate 흐름에 넣는다. 평가가 `skip` 권고면 재작성하지 않는다 | `useEvaluationHandler.ts:566-597`, `packages/core/src/services/evaluation/rewrite-from-evaluation.ts`, `default-templates/evaluation-rewrite/` | 코드 확인 |
| 문서(`docs/architecture/test-area-auto-iterate-one-round.md`)가 말하는 "테스트→평가→재작성 자동 1라운드" 전용 코드(`autoIterate` 등)는 `ui/src`에서 찾지 못했다. 그 문서 자체가 "최초 방안"이라고 밝힌다 | `ui/src` 키워드 검색(autoIterate, auto-iterate), 문서 머리말 | 추론(키워드 검색) |
| 최적화에 쓰는 모델은 호출마다 `modelKey`로 고르고, 평가·재작성·테스트 모델과 서로 독립이다(최적화용 모델과 테스트 대상 모델을 따로 설정) | `OptimizationRequest.modelKey`(`prompt/types.ts:80-85`), `EvaluationRequestBase.evaluationModelKey`, `BasicSystemWorkspace.vue:100-135`(`basic-system-model-select` 등 모델·템플릿 선택 칸) | 코드 확인 |

**MCP 서버 (`packages/mcp-server`)가 노출하는 도구** — README가 "확인하지 못했다"던 부분을 코드로 확인했다.

| 도구 | 입력(필수는 `*`) | 동작 | 근거 |
|---|---|---|---|
| `optimize-user-prompt` | `prompt*`(string), `template`(enum: `userOptimize` 유형 템플릿 id) | `promptService.optimizePrompt({targetPrompt, modelKey:'mcp-default', optimizationMode:'user', templateId})` 결과 문자열을 text로 반환 | `packages/mcp-server/src/index.ts:86-103`·`:160-210` |
| `optimize-system-prompt` | `prompt*`, `template`(enum: `optimize` 유형 id) | 같은 호출을 `optimizationMode:'system'`으로 | `index.ts:106-123`·`:212-262` |
| `iterate-prompt` | `prompt*`, `requirements*`, `template`(enum: `iterate` 유형 id) | `promptService.iteratePrompt(prompt, prompt, requirements, 'mcp-default', templateId)`. 원본과 "직전 최적화본"에 같은 문자열을 넣는다 | `index.ts:126-147`·`:264-330` |

(모두 코드 확인) 입력 검증은 prompt 비어 있지 않음·50,000자 이하, requirements 10,000자 이하(`adapters/parameter-adapter.ts`). 모델은 호출자가 고르지 못한다. 서버가 환경변수로 만든 `mcp-default` 하나만 쓰고(`config/models.ts:66`, `MCP_DEFAULT_MODEL_PROVIDER`로 후보 선택, 없으면 켜진 첫 모델), 켜진 모델이 없으면 도구 호출이 오류를 낸다(`index.ts:184-194`). 평가·테스트·모델 비교 도구는 없다. 전송은 stdio와 HTTP(`/mcp`, 세션 ID 관리) 두 가지이고 `/healthz`가 따로 있다(`index.ts:363-468`, `src/health.ts`). (코드 확인) 템플릿 `enum`은 서버 시작 시 `TemplateManager`에서 읽는다(`index.ts:71-78`). 사용자 템플릿 추가는 이 서버의 메모리 저장소(`MemoryStorageProvider`)에만 있어 기본으로는 내장 템플릿만 보인다(`adapters/core-services.ts`, 추론).

#### Q3. 한계: 데이터가 어디로 나가나, 키는 어디에 저장되나, 라이선스

**결론: "서버를 거치지 않는 클라이언트 직결" 주장은 이 SHA의 웹·데스크톱 경로에서는 코드와 맞는다(`api/`에는 인증 엔드포인트만 있고 LLM 프록시가 없다). 하지만 MCP를 쓰는 Docker 경로는 서버(컨테이너)가 공급자를 호출한다. API 키는 브라우저 저장소에 평문 JSON으로 저장되고, Docker·Vercel에서 환경변수로 넣은 키는 브라우저에 노출된다. 라이선스는 AGPL-3.0 only다.**

| 주장 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|
| 브라우저 경로: 어댑터가 공급자 SDK를 브라우저에서 직접 부른다(`dangerouslyAllowBrowser`). 중간 프록시 호출 코드는 없다 | `llm/adapters/openai-adapter.ts:912`, `anthropic-adapter.ts:774`, `core/src/services/llm/service.ts:389` `isRunningInElectron` 분기만 있고 그 외는 어댑터 직접 호출 | 코드 확인 |
| `api/`에는 `auth.js` 하나뿐이다. 비밀번호 확인과 쿠키 설정만 하고 모델 호출을 중계하지 않는다. `middleware.js`는 `ACCESS_PASSWORD`가 있을 때 쿠키가 없으면 인증 페이지를 돌려주는 게이트다 | `git ls-files api`(1개 파일), `api/auth.js:14-54`, `middleware.js:13-60` | 코드 확인 |
| 그 게이트의 쿠키 값은 비밀번호 그대로(`vercel_access_token=${accessPassword}`)이고 `middleware.js`가 같은 문자열로 비교한다 | `api/auth.js:32`, `middleware.js` 쿠키 비교부 | 코드 확인 |
| `vercel.json`은 `/api/*`를 그대로 통과시키고 나머지를 `index.html`로 보낸다. `wrangler.jsonc`는 `packages/web/dist`를 정적 자산으로만 서빙한다(서버 코드 없음) | `vercel.json` `rewrites`, `wrangler.jsonc` `assets` | 코드 확인 |
| Docker: nginx는 정적 파일 + `/mcp`·`/healthz`만 `localhost:3000`(MCP 서버)으로 프록시한다. 모델 API 프록시는 없고, "프록시 기능은 제거됨"이라는 주석 처리된 블록이 남아 있다 | `docker/nginx.conf:30-69`(`/mcp`, `/healthz`), `:73-77`(주석), `docker/supervisord.conf`(nginx + mcp-server 두 프로세스) | 코드 확인 |
| Docker의 `/mcp`는 `auth_basic off`이고 Express 쪽에도 인증이 없으며 `allowedOrigins: ['*']`, DNS rebinding 보호 꺼짐이다. 포트에 닿는 누구나 컨테이너에 설정된 API 키로 공급자를 호출할 수 있다 | `docker/nginx.conf:30-35`, `packages/mcp-server/src/index.ts:389-408` | 코드 확인 |
| MCP 경로의 데이터 흐름: 클라이언트 → 컨테이너의 mcp-server → 코어 어댑터 → 공급자. 프롬프트가 컨테이너를 거친다 | `index.ts`, `core-services.ts`(`createLLMService`·`createPromptService`) | 코드 확인 |
| 데스크톱: 렌더러가 아니라 Electron 메인 프로세스가 `createLLMService`로 공급자를 호출하고, 렌더러는 IPC(`llm-sendMessageStream` 등)로 요청한다. 네트워크 프록시 설정(`proxy-dispatcher.js`, `network-settings.js`)이 따로 있다 | `packages/desktop/main.js:727`, `:1000`, `packages/desktop/config/proxy-dispatcher.js`(앞부분만 확인) | 코드 확인(호출 경로) / 프록시 설정 세부는 미탐색 |
| 키 저장 위치: 웹은 IndexedDB(Dexie), 데스크톱은 `FileStorageProvider`(userData), MCP는 메모리. 모델 설정(`connectionConfig.apiKey` 포함)은 JSON 문자열로 `models` 키에 저장된다. 암호화 코드는 저장 계층에서 찾지 못했다 | `ui/src/composables/system/useAppInitializer.ts:272`, `desktop/main.js:682`, `core/src/services/model/manager.ts:29`·`:230`, `model/types.ts:61-66`, `storage/*.ts`에서 `encrypt`·`crypto` 검색 결과 없음 | 코드 확인 / 암호화 부재는 추론(검색) |
| 데이터 내보내기는 모델 설정 전체를 포함한다(`exportData` → `getAllModels`). 키를 걸러내는 코드는 이 경로에서 못 찾았다. 원격 백업(S3·R2·WebDAV·Google Drive)은 사용자가 설정하면 내보낸 데이터를 외부 저장소로 올린다 | `core/src/services/data/manager.ts:73`, `model/manager.ts:1265`, `ui/src/utils/remote-backup.ts:14-35` | 코드 확인(경로) / UI의 백업 패키지가 키를 따로 가공하는지는 미확인 |
| 환경변수로 키를 주는 경로: Docker 시작 때 `VITE_*` 변수를 전부 `config.js`(`window.runtime_config`)에 써서 브라우저에 내려준다. 즉 이미지에 넣은 키는 페이지를 여는 누구에게나 보인다. README도 공개 프런트엔드에는 `VITE_*` 키를 넣지 말라고 경고한다 | `docker/generate-config.sh:27-52`, `core/src/utils/environment.ts:294-303` `getEnvVar`, `README.md` Vercel 항목 | 코드 확인 |
| 외부로 나가는 그 밖의 호출: Vercel 배포에서만 Vercel Analytics 스크립트 로드(`VITE_VERCEL_DEPLOYMENT === 'true'`). 홍보 사이트 `site/`는 `@vercel/analytics`를 항상 `inject()`한다. Prompt Garden 가져오기 기본 주소는 `https://garden.always200.com` | `packages/web/src/main.ts:49-65`, `site/src/main.js:1-4`, `core/src/utils/default-env.ts:3`, `ui/src/integrations/prompt-garden.integration.ts` | 코드 확인 |
| 웹에서는 공급자의 CORS 정책에 막힐 수 있다. 어댑터가 `corsRestricted` 플래그를 갖고, README는 데스크톱을 권한다 | `llm/types.ts` `TextProvider.corsRestricted`, `cloudflare-adapter.ts:45`, `README.md` FAQ | 코드 확인(플래그) / 공급자별 실제 차단 여부는 미확인 |
| 라이선스: AGPL-3.0 only(1절). AGPL 13절은 수정한 프로그램을 네트워크로 사용자에게 제공할 때 그 소스를 제공하도록 요구한다. 수정 없이 내 기기·내 서버에서 평가용으로만 쓰는 경우 이 의무가 걸리는지는 법적 판단이므로 이 문서는 결론 내리지 않는다. 입력한 프롬프트·SKILL.md 자체가 AGPL 대상이 되는지도 같은 이유로 미확인이다 | `LICENSE`(전문 포함) | 코드 확인(라이선스 종류) / 영향 범위는 미확인(법률 해석, 외부 자료) |

의미: 내 SKILL.md는 선택한 모델 공급자에게만 가고 이 레포 운영자 서버로 가지 않는다(웹·데스크톱, `코드 확인`). 다만 MCP·Docker 경로는 자기 서버가 중계자가 되고, 그 서버를 인터넷에 열면 키가 사실상 공개된다. 이 레포 코드를 고쳐서 팀에 서비스로 제공할 계획이면 AGPL 검토가 필요하다.

### 기능 지도

한 행 = 스펙 하나의 작업 단위. 구분은 "라이브러리 본체(코어+UI)에 속하면 핵심, 별도 배포 단위·환경 껍데기·부가 도구면 부속"으로 정했다. 분할과 경로는 제안이다. 상태 칸은 승인 범위 6개가 `ready`이고 나머지는 승인 범위 밖이라 `미작성`이다.

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 프롬프트 최적화 | 프롬프트 입력 + 모델·템플릿 선택 → 최적화된 프롬프트(스트리밍 가능). 시스템/사용자 모드. 이미지 입력 있으면 이미지 이해 서비스 경유. 제외: 반복 개선, 이미지 생성 | `packages/core/src/services/prompt/service.ts` `optimizePrompt`(:133), `optimizePromptStream`(:524), `resolveOptimizationMessages`(:909) | 템플릿 관리·렌더링, 모델 관리·LLM 어댑터 | 핵심 | [prompt-optimize](capabilities/prompt-optimize.md) · ready | 코드 확인(호출 경로·모드 분기) / 이미지 입력 분기는 시그니처만 |
| 반복 개선·평가 기반 재작성 | 직전 결과 + 요구사항 → 개선본. 평가 결과를 재작성 입력문으로 압축해 같은 흐름에 투입. 제외: 자동 다회 루프(코드 미확인) | `prompt/service.ts` `iteratePrompt`(:274), `iteratePromptStream`(:721), `evaluation/rewrite-from-evaluation.ts` `buildRewritePayload`·`buildRewritePromptFromEvaluation`, `ui/.../useEvaluationHandler.ts:566-597` | 프롬프트 최적화, 평가 | 핵심 | [iterate-rewrite](capabilities/iterate-rewrite.md) · ready | 코드 확인(iterate, 재작성 입구) / `rewrite-from-evaluation.ts` 압축 규칙 세부는 미탐색 |
| 다중 모델 테스트 영역 | 한 입력을 열 최대 4개(프롬프트 버전 × 모델)에 병렬 실행, 열별 결과·reasoning 표시, 이미지 첨부 가능. 제외: 점수화, 케이스 일괄 | `packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue:879`·`:1185`·`:1277`, `ui/.../usePromptTester.ts:35`, `core/.../prompt/service.ts` `testPromptStream`(:456) | 모델 관리·LLM 어댑터 | 핵심 | `capabilities/test-area.md` · 미작성 (승인 범위 밖) | 코드 확인(실행·병렬·페이로드) / 열 개수 UI 제약(`canUseFourColumns`)과 세션 저장 세부는 미탐색 |
| LLM 평가(결과·비교·구조화 비교) | 평가 유형 4개(result, compare, prompt-only, prompt-iterate) × 모드별 템플릿. 평가 모델 지정, 포커스 문구, JSON 점수·개선안·패치 계획. compare는 역할을 주면 쌍별 판정 + 합성(structured), 아니면 단일 호출(generic) | `packages/core/src/services/evaluation/service.ts` `evaluate`(:275), `evaluateStructuredCompare`(:2163), `normalizeCompareRequest`(:1974), `types.ts`, `ui/.../compareEvaluation.ts`, `useEvaluation.ts` | 템플릿 관리·렌더링, 모델 관리 | 핵심 | [llm-evaluation](capabilities/llm-evaluation.md) · ready | 코드 확인(요청 검증·템플릿 ID·구조화 비교 호출 구조) / 3443줄 중 JSON 파싱·패치 정규화·멀티모달 평가 구간은 미탐색 |
| 텍스트 diff 비교 | 원문과 개선본의 단어/문자 단위 diff 조각과 통계. LLM 호출 없음. 제외: 모델 출력 비교 | `packages/core/src/services/compare/service.ts` `CompareService.compareTexts`, UI 사용처는 미확인(`ui/.../evaluation/InlineDiff.vue` 이름만 확인) | 없음 | 핵심 | `capabilities/text-diff.md` · 미작성 (승인 범위 밖) | 코드 확인(전체 224줄) |
| 모델 관리·텍스트 LLM 어댑터(패밀리) | 모델 추가·수정·활성화, 연결 테스트, 모델 목록 동적 조회, 파라미터(`paramOverrides`). 공급자 16종을 레지스트리에 등록 | `packages/core/src/services/model/manager.ts`, `model/defaults.ts`(환경변수 → 기본 모델), `llm/service.ts`, `llm/adapters/registry.ts` `initializeAdapters`, `adapters/abstract-adapter.ts` | 없음 | 핵심 | `capabilities/model-llm.md` · 미작성 (승인 범위 밖) | 코드 확인(레지스트리·추상 클래스·서비스 흐름) / 어댑터별 요청 변환은 openai·anthropic 일부만 |
| Pro 모드: 멀티 메시지·변수·변수 추출/생성 | 대화형 메시지 편집·테스트, `{{변수}}` 치환·전역/임시 변수, Function Calling 테스트, LLM으로 변수 추출·값 생성 | `core/.../prompt/service.ts` `optimizeMessage`(:178)·`testCustomConversationStream`(:1103), `core/.../variable-extraction/service.ts` `extract`, `variable-value-generation/service.ts` `generate`, `ui/.../context-mode/` | 프롬프트 최적화, 평가, 템플릿 | 핵심 | `capabilities/pro-mode.md` · 미작성 (승인 범위 밖) | 코드 확인(진입점 시그니처·호출처) / 본문 세부 미탐색 |
| 템플릿 관리·렌더링 | 내장 템플릿(중/영, 유형별)과 사용자 템플릿 저장·가져오기·내보내기, Mustache 렌더링, 언어 전환 | `packages/core/src/services/template/manager.ts`, `processor.ts` `processTemplate`, `default-templates/index.ts` | 없음 | 핵심 | [template-rendering](capabilities/template-rendering.md) · ready | 코드 확인(processor 전체 분기, manager 시그니처) / 사용자 템플릿 검증 규칙은 미탐색 |
| 히스토리·버전 체인 | 최적화·반복 결과를 체인(버전)으로 저장·조회·삭제. 서비스는 저장하지 않고 UI가 호출 | `packages/core/src/services/history/manager.ts` `createNewChain`(:210)·`addIteration`(:235) | 없음 | 핵심 | [history-chain](capabilities/history-chain.md) · ready | 코드 확인(시그니처) / 저장 규칙 세부 미탐색 |
| 즐겨찾기(프롬프트 자산) | 프롬프트 저장, 카테고리·태그, 버전·예시, 가져오기/내보내기(HTML/PNG 공유 포함) | `packages/core/src/services/favorite/manager.ts`, `ui/src/utils/favorite-*.ts`, `ui/src/components/favorites/` | 없음 | 핵심 | `capabilities/favorites.md` · 미작성 (승인 범위 밖) | 코드 확인(매니저 시그니처 목록) / 세부 미탐색 |
| Prompt Garden 가져오기 | 외부 서비스의 가져오기 코드로 프롬프트를 워크스페이스·즐겨찾기에 가져옴. `VITE_ENABLE_PROMPT_GARDEN_IMPORT` 플래그로 선택 등록 | `packages/ui/src/integrations/prompt-garden.integration.ts`, `ui/src/composables/app/useAppPromptGardenImport.ts`(이름만) | 즐겨찾기 | 부속 | `capabilities/prompt-garden.md` · 미작성 (승인 범위 밖) | 코드 확인(등록부) / 가져오기 본문 미탐색 |
| 이미지 모드(T2I·I2I·멀티이미지)와 이미지 어댑터(패밀리) | 이미지 프롬프트 최적화 + 이미지 생성 + 결과 평가. 이미지 공급자 10종을 레지스트리에 등록. 제외: 텍스트 모드 | `packages/core/src/services/image/service.ts` `generate`(:254)·`generateMultiImage`(:249), `image/adapters/registry.ts`, `default-templates/image-optimize/`, `ui/src/components/image-mode/` | 모델 관리(이미지 모델 매니저), 템플릿 | 핵심 | `capabilities/image-mode.md` · 미작성 (승인 범위 밖) | 코드 확인(서비스·레지스트리 시그니처) / 어댑터 본문·평가 템플릿 미탐색 |
| 데이터 가져오기·내보내기·원격 백업 | 히스토리·모델·템플릿·설정을 한 파일로 내보내고 복원. 원격(Google Drive·R2·S3 호환·WebDAV) 백업 | `packages/core/src/services/data/manager.ts`, `packages/ui/src/utils/remote-backup.ts`, `remote-snapshot-backup.ts`(이름만) | 모델·템플릿·히스토리 등 각 매니저의 `exportData` | 핵심 | `capabilities/data-backup.md` · 미작성 (승인 범위 밖) | 코드 확인(`exportData` 연결 부분) / 원격 백업 흐름 미탐색 |
| MCP 서버 | MCP 클라이언트가 도구 3개로 최적화·반복 개선 호출. stdio 또는 HTTP `/mcp`(세션), `/healthz`. 모델은 서버 환경변수의 `mcp-default` 하나 | `packages/mcp-server/src/index.ts`(도구 목록 `:82`, 호출 `:154`, 전송 `:356`), `config/models.ts`, `config/templates.ts`, `adapters/core-services.ts` | 프롬프트 최적화, 반복 개선, 모델 관리 | 핵심(별도 패키지·진입점) | `capabilities/mcp-server.md` · 미작성 (승인 범위 밖) | 코드 확인(도구 정의·입력·호출·전송) |
| 웹 앱 셸·워크스페이스·세션 | 7개 워크스페이스 라우트, 모드별 세션 저장, 초기화(`useAppInitializer`)에서 서비스 조립. `packages/web`은 `PromptOptimizerApp`만 마운트 | `packages/web/src/main.ts`, `packages/ui/src/router/workspaceRoutes.ts`, `ui/src/composables/system/useAppInitializer.ts:255-300`, `ui/src/stores/session/` | 위 핵심 기능 전반 | 핵심 | `capabilities/app-shell.md` · 미작성 (승인 범위 밖) | 코드 확인(라우트·웹/일렉트론 분기) / 세션 스토어 본문 미탐색 |
| 데스크톱 앱(Electron) | 메인 프로세스가 코어 서비스를 직접 생성해 IPC로 노출, 파일 저장, 네트워크 프록시 설정, 자동 업데이트. `web` 빌드를 `web-dist`로 복사해 로드 | `packages/desktop/main.js:680-730`(저장소·서비스 생성)·`:954-1232`(IPC), `packages/desktop/package.json`, `preload.js` | 위 핵심 기능, 앱 셸 | 부속 | `capabilities/desktop.md` · 미작성 (승인 범위 밖) | 코드 확인(서비스 생성·IPC 이름 목록) / 3314줄 중 업데이트·메뉴·네트워크 설정은 미탐색 |
| Chrome 확장 | 아이콘 클릭 시 확장 페이지(`index.html`)를 새 탭으로 열어 UI 실행. `permissions: []`, 오프라인 가능 | `packages/extension/public/manifest.json`, `public/background.js`, `src/main.ts` | 앱 셸 | 부속 | `capabilities/extension.md` · 미작성 (승인 범위 밖) | 코드 확인(전체 파일이 짧음) |
| Docker 배포 | 이미지 하나에 nginx(정적 웹 + `/mcp` 프록시) + mcp-server, 시작 때 `VITE_*`를 `config.js`로 주입, `ACCESS_PASSWORD`로 Basic 인증 | `Dockerfile`, `docker/nginx.conf`, `docker/supervisord.conf`, `docker/start-services.sh`, `generate-config.sh`, `generate-auth.sh` | MCP 서버, 앱 셸 | 부속 | `capabilities/deploy-docker.md` · 미작성 (승인 범위 밖) | 코드 확인(주요 파일 읽음) / `docker-compose*.yml`은 열지 않음 |
| Vercel·Cloudflare 배포와 비밀번호 게이트 | Vercel: `middleware.js`가 비밀번호 쿠키를 확인, `api/auth.js`가 로그인·로그아웃, SPA rewrite. Cloudflare: 정적 자산만 | `vercel.json`, `middleware.js`, `api/auth.js`, `wrangler.jsonc` | 앱 셸 | 부속 | `capabilities/deploy-vercel-cf.md` · 미작성 (승인 범위 밖) | 코드 확인 |
| 홍보 사이트·문서 사이트 | `site/`: always200.com용 독립 Vite 정적 사이트(다국어·테마). `mkdocs/`: docs.always200.com용 MkDocs Material 문서 | `site/package.json`, `site/src/main.js`, `site/vercel.json`, `mkdocs/mkdocs.yml`, `mkdocs/vercel.json` | 없음(제품 코드와 분리) | 부속 | `capabilities/sites.md` · 미작성 (승인 범위 밖) | 코드 확인(구성·배포 설정) / 본문(문서·번역)은 열지 않음 |
| 구조화 비교 보정 스크립트 | Node에서 코어를 직접 써서 하드코딩 케이스(live 1개는 4개 스냅샷 실행, 합성 5개는 고정 증거)로 → 평가 → 재작성 → 결과 파일 저장. 평가기 품질 확인용 개발 도구 | `scripts/run-structured-compare-calibration.mjs:1127`·`:1170`, 루트 `package.json` `compare:calibrate` | 평가, 반복 개선 | 부속 | [calibration-script](capabilities/calibration-script.md) · ready | 코드 확인(조립부) / 케이스 정의·판정 기준(`1488줄 중 대부분`)은 미탐색, 실행하지 않음 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 템플릿(`Template`: 문자열 또는 메시지 배열 + 메타) → `Message[]` 렌더링 규칙, 템플릿 ID 명명(`evaluation-{mode}-{subMode}-{type}`) | 최적화, 반복 개선, 평가, Pro 모드, 이미지, 변수 서비스, MCP | `core/.../template/processor.ts:84-117`, `template/types.ts`, `evaluation/service.ts:587` `getTemplateId` | [template-rendering](capabilities/template-rendering.md) · ready | 코드 확인 |
| 모델 설정(`TextModelConfig`: providerMeta, modelMeta, `connectionConfig.apiKey/baseURL`, `paramOverrides`)과 어댑터 계약(`ITextProviderAdapter`) | 최적화, 테스트, 평가, MCP, 데스크톱 IPC | `core/.../model/types.ts:44-70`, `llm/types.ts:263-` `ITextProviderAdapter`, `llm/adapters/abstract-adapter.ts` | `capabilities/model-llm.md` | 코드 확인 |
| 저장소 계약(`IStorageProvider`: Dexie/localStorage/memory/file) | 모델·히스토리·템플릿·즐겨찾기·설정·세션 | `core/.../storage/factory.ts`, `storage/types.ts`(이름만) | — | 코드 확인(팩토리) / 인터페이스 본문 미탐색 |
| 평가 요청·응답 계약(`EvaluationRequest`: result/compare/prompt-only/prompt-iterate, `EvaluationSnapshot`, `EvaluationResponse` JSON) | 테스트 영역, 평가, 재작성, 보정 스크립트 | `core/.../evaluation/types.ts` | [llm-evaluation](capabilities/llm-evaluation.md) · ready | 코드 확인 |
| 환경변수 계약(`VITE_*_API_KEY`, `VITE_CUSTOM_API_*_<suffix>`, `window.runtime_config`) | 기본 모델 생성, Docker 주입, MCP 환경 매핑, 보정 스크립트 | `core/.../utils/environment.ts:294` `getEnvVar`, `model/defaults.ts`, `mcp-server/src/config/environment.ts` | — | 코드 확인 |

**패밀리로 묶은 것과 공통 규칙**
- 텍스트 LLM 어댑터 16종(openai, openai-compatible, deepseek, siliconflow, zhipu, anthropic, gemini, dashscope, openrouter, modelscope, ollama, minimax, cloudflare, grok, chrome-built-in, xiaomi-mimo-token-plan)은 `TextAdapterRegistry`가 한 번에 등록한다(`llm/adapters/registry.ts:52-89`). 공통 규칙: `AbstractTextProviderAdapter`의 템플릿 메서드가 메시지 검증 후 `doSendMessage`/`doSendMessageStream`을 부른다(`abstract-adapter.ts` `sendMessage`·`sendMessageStream`). 12개는 `OpenAIAdapter`를 상속(OpenAI SDK + `baseURL` 정규화)하고 anthropic·gemini·chrome-built-in만 추상 클래스를 직접 상속한다(`export class ... extends` 검색). 고유 구현이 큰 anthropic·gemini는 별도 행으로 빼지 않고 행 6의 세부로 둔다. (코드 확인)
- 이미지 어댑터 10종(gemini, seedream, siliconflow, openai, openrouter, dashscope, modelscope, ollama, cloudflare, grok)은 `AbstractImageProviderAdapter`를 상속하고 `ImageAdapterRegistry`가 등록한다(`image/adapters/registry.ts:47-67`). (코드 확인)

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 전체(기능 목록, 설치, MCP, API 키, FAQ), 루트 `package.json`·`pnpm-workspace.yaml`, `git ls-files` 전체 이름(1,924개), `packages/{core,ui,web,extension,desktop,mcp-server}`의 매니페스트·진입점, `api/`·`middleware.js`·`vercel.json`·`wrangler.jsonc`, `Dockerfile`·`docker/*`, `site/`·`mkdocs/`의 매니페스트·배포 설정. 공개 입구는 MCP 도구 3개(`index.ts:86-147`), 워크스페이스 라우트 7개, 코어 `index.ts`의 서비스 팩토리(`createPromptService`, `createEvaluationService` 등)와 대조했다.
- 문서와 구현의 차이: ① README "Secure Architecture: Pure client-side processing, bypassing intermediate servers"는 웹·데스크톱 경로에서는 맞지만 Docker의 MCP 경로는 서버가 공급자를 호출한다(Q3). ② README의 지원 모델 목록(OpenAI, Gemini, DeepSeek, Grok, Zhipu, SiliconFlow, MiniMax 등)보다 레지스트리의 텍스트 어댑터가 16종으로 더 많다(`registry.ts`). ③ README "Multi-round iterative improvements"는 코어에 반복 루프가 있다는 뜻이 아니라 사용자가 `iteratePrompt`를 반복 호출하는 것으로 읽힌다(Q2). ④ `docs/architecture/test-area-auto-iterate-one-round.md`가 설계한 자동 1라운드 기능은 코드에서 찾지 못했다(Q2, 추론). ⑤ README의 MCP `MCP_DEFAULT_MODEL_PROVIDER` 선택지 목록에 `anthropic`이 있고 코드는 환경변수 매핑 목록에서 `VITE_ANTHROPIC_API_KEY`를 `ANTHROPIC_API_KEY`로 옮기지 않는다(`mcp-server/src/config/environment.ts:51-61`). 다만 코어 기본 모델 쪽에는 `VITE_ANTHROPIC_API_KEY`가 있어(`model/defaults.ts:16`) 실제로 Anthropic이 MCP에서 동작하는지는 미확인.
- 미탐색: 테스트·E2E(`tests/`, `**/__tests__`), CI(`.github/`), `docs/` 본문(개발 문서·아카이브·`docs/workspace/` — 구조화 비교 보정 결과 포함), `CHANGELOG.md`, `releases/`, `mkdocs/docs/` 번역·본문, `packages/ui/src/i18n`·`locales`, 이미지 에셋. 코드 쪽: `evaluation/service.ts` 3443줄 중 파싱·정규화·멀티모달 구간, `ui`의 즐겨찾기·이미지 모드·세션 스토어·변수 가져오기 본문, 어댑터 대부분의 요청 변환, `desktop/main.js`의 업데이트·메뉴·네트워크 설정, `preload.js`, `docker/docker-compose*.yml`, `packages/ui`의 `components/` 대부분(이름만 확인).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 패키지·배포 입구와 데이터가 나가는 경로 |

실행 흐름도는 그리지 않았다(범위: 구조도 하나).

**구조도 검증 결과** (세 가지를 구분한다)

| 구분 | 결과 |
|---|---|
| 산출물 검증 (`archify deliver --quality showcase`) | 통과. 아티팩트 검사 9/9, composition errors 0, warnings 0. 명세 SHA-256 `07ad7c17…`, HTML `7ecfda6c…`. 노드 11개, 연결 11개 |
| 브라우저 확인 (`archify visual-check`) | `status: pass`. 로컬 Chrome 사용. 1440×900, 1600×1000, 1920×1080, 2048×1320에서 가로·세로 넘침 없음(자동 측정). 스크린샷·JSON은 `prompt-eval/artifacts/prompt-optimizer/structure-visual-check/`에 있다. 이 증거는 자동 측정이며 시각 품질 승인이 아니다 |
| 시각 검토 | 이미지를 볼 수 있는 검토자(이 분석을 한 에이전트)가 1440×900 라이트와 2048×1320 다크 스크린샷을 직접 봤다. 텍스트 겹침·화살표 가림 없음, 점선(부속)·실선(핵심) 구분이 보임. 단 사람이 따로 검토한 것은 아니므로 `visual-check`의 `visualReview`는 `pending`으로 둔다 |

구조도에서 일부러 생략한 것: 데스크톱 렌더러가 `web` 빌드를 로드하는 관계(노드 부제에만 반영), 원격 백업 대상(S3 등), Prompt Garden, `site/`·`mkdocs/`, 보정 스크립트. 이유는 노드 12개 제한과 가독성이다.

### 그림 해설

**읽는 순서**
1. `packages/core/src/index.ts`(서비스 팩토리 목록) → `services/prompt/service.ts`·`evaluation/service.ts`: 모든 기능이 여기를 지난다.
2. `packages/ui/src/composables/system/useAppInitializer.ts:255-300`: 웹은 Dexie 저장소 + 실제 서비스, 일렉트론은 프록시 서비스로 조립된다.
3. `packages/ui/src/components/basic-mode/BasicSystemWorkspace.vue`: 테스트 영역(열 4개)과 평가 호출이 이어지는 곳.
4. `packages/mcp-server/src/index.ts`: 코어를 서버로 부르는 두 번째 입구.
5. 배포 래퍼: `docker/nginx.conf` → `middleware.js`·`api/auth.js`.

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| packages/core | 최적화·반복·테스트·평가·모델·템플릿·히스토리·즐겨찾기·이미지·저장소 서비스. 내장 메타 프롬프트 보유 | 요청 객체 → 문자열/JSON. 모델 호출은 `LLMService`가 어댑터로 | `packages/core/src/index.ts`, `services/prompt/service.ts`, `services/evaluation/service.ts` | 코드 확인 |
| packages/ui | Vue 앱, 워크스페이스 7개, 테스트 영역, 평가 패널, 세션·즐겨찾기 UI. 서비스 조립 | 사용자 입력 → 코어 서비스 호출. 결과 스트림을 열별 상태에 누적 | `ui/src/composables/system/useAppInitializer.ts`, `BasicSystemWorkspace.vue`, `router/workspaceRoutes.ts` | 코드 확인 |
| packages/web | UI를 웹으로 마운트하는 껍데기. Vercel 배포에서만 Analytics 로드 | `PromptOptimizerApp` 마운트 | `packages/web/src/main.ts`, `src/App.vue` | 코드 확인 |
| packages/extension | 아이콘 클릭 시 확장 페이지를 새 탭으로 열고 같은 UI 실행 | `chrome.tabs.create({url: index.html})` | `packages/extension/public/background.js:1-4`, `manifest.json` | 코드 확인 |
| packages/desktop | Electron 메인이 코어 서비스를 만들고 IPC로 노출, 파일 저장, 프록시·업데이트 | 렌더러 IPC(`llm-*`, `prompt-*`, `model-*`) ↔ 메인의 서비스 | `packages/desktop/main.js:680-730`·`:954-1232` | 코드 확인(앞 두 구간) / 나머지 미탐색 |
| mcp-server | 코어의 최적화·반복 개선을 MCP 도구 3개로 노출. 메모리 저장소, 환경변수로 기본 모델 1개 구성 | MCP `tools/call` ↔ `promptService` | `packages/mcp-server/src/index.ts`, `adapters/core-services.ts`, `config/models.ts` | 코드 확인 |
| Docker 이미지 | nginx(정적 서빙, `/mcp`·`/healthz` 프록시, Basic 인증) + supervisord로 mcp-server 동시 실행, `VITE_*`를 `config.js`로 주입 | 80포트 → 정적/`localhost:3000` | `Dockerfile`, `docker/nginx.conf:30-66`, `docker/supervisord.conf`, `docker/generate-config.sh` | 코드 확인 |
| Vercel 게이트 | `ACCESS_PASSWORD` 쿠키 확인 미들웨어와 로그인 엔드포인트. LLM 프록시 아님 | 쿠키 ↔ 인증 페이지/통과 | `middleware.js:13-60`, `api/auth.js` | 코드 확인 |
| 모델 공급자 API | 외부 LLM 서비스 | 코어 어댑터의 SDK 요청 ↔ 응답 | `llm/adapters/openai-adapter.ts:912`, `anthropic-adapter.ts:774` | 코드 확인(클라이언트 쪽) / 공급자 쪽 동작은 미확인 |
| 저장소 | 모델 설정(API 키 포함)·히스토리·템플릿 등 JSON 저장. 웹=Dexie, 데스크톱=파일, MCP=메모리 | `IStorageProvider` | `storage/factory.ts`, `useAppInitializer.ts:272`, `desktop/main.js:682`, `core-services.ts` | 코드 확인 |
| MCP 클라이언트 | Claude Desktop 등 외부 도구 | 도구 호출 JSON-RPC | `index.ts:389-468` | 코드 확인(서버 쪽) / 클라이언트 쪽은 미확인 |

**미확인 영역**
- 공급자가 실제로 키와 프롬프트를 어떻게 다루는지(공급자 정책), 브라우저에서 공급자별로 CORS가 실제로 막히는지.
- 데스크톱 `main.js`의 업데이트·네트워크 설정, 원격 백업·즐겨찾기·이미지 모드의 실행 흐름(구조도에 넣지 않음).
- 설치·빌드·실행으로 확인한 것은 없다. 위 평가·최적화 동작은 모두 코드 읽기 기준이다.

---

## 4. 질문 (Questions)

아직 없음. 목적 질문 Q1~Q3의 초기 답은 2절에 있다.

---

## 5. 다음 작업 및 연계 링크

- **스펙 범위**: 1절에 승인한 범위를 적었다. 승인 범위 6개가 모두 ready다(capabilities/ 참고).
- **먼저 더 읽을 곳(목적 기준)**: `evaluation/service.ts`의 결과 파싱(`parseEvaluationResult`)과 점수 안정성, `docs/workspace/compare-evaluation-analysis/structured-compare-calibration/`의 보정 기록(문서 후보), 평가 모델과 테스트 모델을 같은 모델로 쓸 때의 편향.
- **다음 세션 계획**: [next.md](./next.md)
- **스펙 작성 후 정정·보강** (스펙 2.1이 원본이다. 이 문서의 표와 Q1~Q3 서술을 아래 기준으로 읽는다):
  - 구조화 비교는 "역할이 주어지면"이 아니라 `compareHints.mode==='structured'` + `target` 역할 + 판정 쌍 1개 이상이 모두 필요하다. `crossModelComparison`은 모드 스위치가 아니다(llm-evaluation).
  - compare 평가의 응답은 전체 점수 하나뿐이고 스냅샷별·모델별 점수가 없다(llm-evaluation).
  - 심판 모델을 평가 대상과 다르게 강제하는 장치는 코어·UI·MCP 어디에도 없다(llm-evaluation).
  - 평가 결과는 히스토리 기록에 붙지 않고 UI 세션에 유형별 최신 1건만 남는다(history-chain, llm-evaluation).
  - "테스트→평가→재작성 자동 1라운드"는 구현이 없다. 평가→재작성은 사용자 클릭 2번이다(iterate-rewrite R-30).
  - `skip` 권고는 compare 평가에서만 나오고 UI 핸들러만 막는다. 코어 함수는 `skip`이어도 입력문을 만든다(iterate-rewrite).
  - 보정 스크립트는 심판 안정성 측정 방법이 아니다. 반복·순서 교대·심판 교체·통과 기준이 없고 종료 코드도 판정을 반영하지 않는다(calibration-script).
  - `onError`는 한 스트리밍 실패에 1~3번 불린다(prompt-optimize R-13·R-22).
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸.
