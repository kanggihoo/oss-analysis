---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - README.md
  - AGENTS.md
  - LICENSE
  - package.json
  - pnpm-workspace.yaml
  - Dockerfile
  - architecture/layers.json
  - docs/architecture/packages.md
  - plugins/AGENTS.md
  - helm/chart/promptfoo/values.yaml
  - code-scan-action/action.yml
  - src/main.ts
  - src/entrypoint.ts
  - src/index.ts
  - src/constants.ts
  - src/cache.ts
  - src/telemetry.ts
  - src/updates.ts
  - src/share.ts
  - src/util/sharing.ts
  - src/util/config/manage.ts
  - src/node/doEval.ts
  - src/node/evaluate.ts
  - src/commands/eval.ts
  - src/commands/optimize.ts
  - src/commands/mcp/server.ts
  - src/commands/modelScan.ts
  - src/evaluator.ts
  - src/evaluatorHelpers.ts
  - src/prompts/index.ts
  - src/prompts/grading.ts
  - src/prompts/processors/text.ts
  - src/optimizer/promptOptimizer.ts
  - src/providers/registry.ts
  - src/providers/registryTypes.ts
  - src/providers/defaults.ts
  - src/providers/agentic-utils.ts
  - src/providers/claude-agent-sdk.ts
  - src/providers/opencode-sdk.ts
  - src/providers/openai/codexSkillMetadata.ts
  - src/providers/pricing.ts
  - src/assertions/index.ts
  - src/assertions/skill.ts
  - src/matchers/llmGrading.ts
  - src/matchers/similarity.ts
  - src/types/index.ts
  - src/types/providers.ts
  - src/redteam/remoteGeneration.ts
  - src/redteam/shared.ts
  - src/redteam/plugins/base.ts
  - src/redteam/plugins/index.ts
  - src/redteam/strategies/types.ts
  - src/redteam/strategies/index.ts
  - src/redteam/providers/registry.ts
  - src/redteam/AGENTS.md
  - src/server/server.ts
  - src/codeScan/scanner/index.ts
  - src/external/APACHE_LICENSE
  - src/redteam/providers/crescendo/LICENSE
  - plugins/promptfoo/skills/promptfoo-provider-setup/scripts/vendor/LICENSE
  - site/docs/guides/test-agent-skills.md
  - site/docs/usage/prompt-optimization.md
  - site/docs/configuration/telemetry.md
  - site/docs/configuration/caching.md
  - site/docs/usage/sharing.md
  - docs/scheduler-architecture.md
  - src/remoteGrading.ts
  - examples/claude-agent-sdk/skill-comparison/promptfooconfig.yaml
  - examples/compare-gpt-vs-claude-vs-gemini/promptfooconfig.yaml
---

# promptfoo Analysis Overview

경로 표기: 이 문서의 `파일:줄`과 `파일 심볼`은 모두 `repos/promptfoo/` 기준이다(작업 폴더는 `prompt-eval/`). 검증 수준은 `코드 확인` / `추론` / `미확인`만 쓴다. 이번 분석은 설치·빌드·실행을 하지 않았으므로 `실행 확인`은 없다. 레포 안 `site/docs`(문서 사이트 원문)는 코드가 아니므로, 그 문장만 근거인 항목은 `미확인`으로 표시한다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/promptfoo/promptfoo` (`../../artifacts/promptfoo/repo-metadata.txt`)
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 브랜치 `main`, 커밋 날짜 2026-10-22, 기준 SHA `dfe2d45e6f72be85c866b746e3852de0dd7622c5`)
- **분석 목적**: 내가 만든 스킬(SKILL.md)·프롬프트를 평가하고, 어떤 모델에서 가장 잘 되는지 비교하고, 개선하는 데 쓸 도구인지 파악한다(도입 검토). 레포 전체 기능 지도는 별도로 레포 전체를 대상으로 하고, 목적 질문(Q1~Q3)의 초기 답은 2절 아래 소절에 둔다.
- **라이선스**: MIT (코드 확인). 루트 `LICENSE`는 제목 줄 없이 "Copyright (c) Promptfoo 2025"와 MIT 허가 문구 본문으로 시작한다. `package.json`의 `"license": "MIT"`, `README.md`의 "MIT licensed"도 같다. 하위 디렉터리에 다른 LICENSE가 3개 있다(`find`, node_modules 제외).
  - `src/external/APACHE_LICENSE`: Apache License 2.0. `src/external/assertions/deepeval.ts`는 DeepEval에서, `src/external/prompts/ragas.ts`는 RAGAS에서 옮겨 온 코드이고 각 파일 머리 주석이 이 라이선스를 가리킨다.
  - `src/redteam/providers/crescendo/LICENSE`: "Some files in this directory are based on code from ... Azure/PyRIT"로 시작하고 Microsoft 저작권 표기가 이어진다(본문은 끝까지 읽지 않았고 종류는 확인하지 않았다 — 미확인).
  - `plugins/promptfoo/skills/promptfoo-provider-setup/scripts/vendor/LICENSE`: "(The MIT License) Copyright (C) 2011-2015 by Vitaly Puzrin"으로 시작하는 MIT(벤더링한 외부 스크립트용).
- **분석 대상 제품**: 단일 npm 패키지 `promptfoo` 0.124.1(`package.json:5`, 바이너리 `promptfoo`·`pf` → `dist/src/entrypoint.js`, Node >=22.22.0). 워크스페이스 2개 `src/app`(웹 UI)·`site`(문서 사이트)(`pnpm-workspace.yaml`, `package.json` `workspaces`). 별도 배포 입구: `code-scan-action/`(GitHub Action `@promptfoo/code-scan-action` 0.2.2), `Dockerfile`, `helm/chart/promptfoo`, `plugins/promptfoo`(Codex·Claude Code 공용 스킬 번들 4개). 라이브러리 export는 `.`과 `./contracts` 두 개(`package.json` `exports`). (코드 확인)
- **스펙 범위**: 2026-10-22 승인. 목적은 내 스킬의 평가·개선·모델 적합도 기록 환경을 만드는 데 쓸 부분만 스펙으로 쓴다.
  - 승인한 행(12): 설정·프롬프트·테스트 로딩(공유 계약 `config-schema`를 같은 스펙에 합침), 평가 실행 파이프라인, 프로바이더 계약(공유 계약만, 패밀리 본체는 제외), 에이전트 SDK 프로바이더 + 스킬 호출 메타, 어서션 패밀리(공유 계약 `assertion-contract`를 같은 스펙에 합침), 모델 채점 매처·기본 grader, 결과 저장·출력·결과 관리 명령, 프롬프트 최적화(`optimize`), 테스트·어서션 생성(`generate`), 웹 UI·로컬 서버(범위 제한: 결과 저장 위에서 서빙하는 서버 API와 결과 표·비교 화면만. 레드팀 설정·리포트와 모델 감사 화면 제외), 스크립트 브리지·확장 훅, 응답 캐시.
  - 선행으로 함께 쓰는 공유 계약(4): `provider-contract`, `skill-calls-metadata`, `eval-records`, `default-providers`.
  - 제외(이유: 사용자 제외 또는 이번 목적 밖): 스케줄러, 프로바이더 패밀리 본체, 커스텀 타깃 프로바이더, 트레이싱(OTLP), Node 라이브러리 API, 레드팀 4행, 부속 중 MCP 서버·호스팅 서비스 연동·코드 스캔·모델 파일 스캔·에이전트 플러그인 번들·문서 사이트·컨테이너·Helm, 공유 계약 `remote-generation`.
  - 웹 UI를 그대로 쓸지 다시 만들지는 미정이다(결과 저장 스펙 이후 결정).

---

## 2. 프로젝트 개요

README는 promptfoo를 "LLM 기반 앱을 평가하고 레드팀 테스트하는 CLI·라이브러리"로 소개한다(`README.md:12`의 소개문). 코드로 보면 한 패키지 안에 세 겹이 있다. ① 설정 파일(`prompts` × `providers` × `tests`/`assert`)을 읽어 모든 조합을 실행하고 채점하는 **평가 엔진**(`src/evaluator.ts`), ② 같은 엔진 위에서 공격 테스트를 만들어 돌리는 **레드팀**(`src/redteam`), ③ 결과를 SQLite에 저장하고 보여 주는 **웹 UI·서버**와 호스팅 서비스 연동(공유·로그인·원격 생성·telemetry). 모든 입구는 `src/main.ts`가 commander로 등록한 서브커맨드이거나 `src/index.ts`가 내보내는 Node API이다. (코드 확인: `src/main.ts:71-135`, `src/index.ts`)

내부 경계는 `architecture/layers.json`이 계층으로 선언한다: `contracts`·`validation`(말단) → `legacy-contracts`·`legacy-runtime`·`node` → `providers` → `redteam` → `core`(assertions·matchers·prompts·scheduler·testCase) → `view-server` → `cli` → `app` → `facade`(`src/index.ts`). 모듈 안 import 방향의 근거이고, 이 지도의 분할 기준은 아니다. (코드 확인: `architecture/layers.json`의 `tierOrder`·`layers`)

### 목적 질문에 대한 초기 답

이 소절은 사용자 목적(내 SKILL.md·프롬프트 평가, 모델 간 비교, 개선)에 한정한다. 레포 전체 지도는 아래 "기능 지도"다.

**Q1. 평가: 프롬프트/SKILL.md를 여러 모델에 같은 케이스로 돌려 비교하려면**

1. 입력 형식. 설정 파일 하나에 `providers`(여러 모델·에이전트, 각각 `id`·`label`·`config`), `prompts`(문자열·`file://`·객체), `tests`(`vars`+`assert`), `defaultTest`(모든 테스트에 공통인 `assert`·`options`)를 쓴다(코드 확인: `src/types/index.ts:1312-1360` `TestSuiteConfigSchema`). 실행기는 provider마다 허용된 prompt를 돌며 열을 만든다(코드 확인: `src/evaluator.ts:2516` `buildLivePromptColumns`). 같은 케이스를 여러 모델에 돌리는 전형적 예: `providers`에 `openai:chat:...`·`anthropic:messages:...`·`google:...`를 나열하고 `defaultTest.assert`+`tests`를 공유한다(코드 확인: 예제 파일 `examples/compare-gpt-vs-claude-vs-gemini/promptfooconfig.yaml`의 구조를 읽음. 실행은 안 함). 반복 실행은 `--repeat`(코드 확인: `src/commands/eval.ts` 옵션, `src/evaluator.ts:475-480`이 repeat별 캐시 이름공간을 따로 씀).
2. 스킬 호출 코드. `deriveSkillCalls`(`src/providers/claude-agent-sdk.ts:311`)는 이 provider가 모은 `toolCalls` 중 `name === 'Skill'`인 것만 골라, `input.skill` 문자열을 이름으로 하는 `SkillCallEntry { name, input, is_error, source: 'tool' }`로 바꾼다. 호출은 `:2434`, 결과는 성공·실패 두 반환 경로 모두 `response.metadata.skillCalls`에 실린다(`:2474`, `:2518`). 항목 모양은 `src/types/providers.ts:49` `SkillCallEntry`. 그 위에 `skill-used`/`not-skill-used` 어서션이 있다(`src/assertions/index.ts:305` 등록, `src/types/index.ts:732`). `handleSkillUsed`(`src/assertions/skill.ts`)는 `providerResponse.metadata.skillCalls` 중 `is_error`가 `true`가 아닌 항목만 보고, 값으로 문자열·문자열 배열·`{name|pattern, min, max}`를 받는다. (코드 확인) 즉 이 코드는 "스킬이 호출됐는가"를 채점하는 장치이고, SKILL.md 내용을 평가 입력으로 주입하는 코드가 아니다.
3. 다른 에이전트 provider의 같은 메타데이터. OpenCode는 `tool === 'skill'` 부분을 `source: 'tool'`로 변환한다(`src/providers/opencode-sdk.ts:1939`). Codex는 shell 명령 문자열 안의 `.agents/skills/<이름>/SKILL.md` 경로를 정규식으로 찾아 `source: 'heuristic'`으로 기록하고, 성공한 명령만 `skillCalls`, 시도 전체는 `attemptedSkillCalls`로 분리한다(`src/providers/openai/codexSkillMetadata.ts` `extractCodexSkillPathCandidates`·`buildCodexSkillMetadata`). 그래서 Codex의 `skill-used`는 추정치다. (코드 확인)
4. SKILL.md를 평가 대상으로 넣는 경로. 전용 API는 없고 **provider 설정으로 만든다**. `anthropic:claude-agent-sdk`의 `config`에 `working_dir`(SKILL.md가 든 폴더), `setting_sources: ['project']`, `skills: ['이름']`을 주면 이 값이 SDK 옵션으로 그대로 넘어간다(코드 확인: `src/providers/claude-agent-sdk.ts:590` 옵션 정의·주석, `:1642-1662` `config.tools`가 없고 `allow_all_tools`가 아닐 때만 `skills`가 있으면 `Skill`을 사용 가능 도구(`tools`)에 추가(허용 목록이 아님, agent-providers R-12), `:1733` `skills: config.skills` 전달). SKILL.md를 찾아 읽는 쪽은 Claude Agent SDK(Claude Code)이고, 그 내부 동작은 이 레포 밖이라 `미확인`이다. 공식 가이드는 v1/v2 폴더 두 개에 SKILL.md 버전을 두고 provider 두 개로 비교하는 구성을 보여 준다(`site/docs/guides/test-agent-skills.md`, 실제 설정 파일 `examples/claude-agent-sdk/skill-comparison/promptfooconfig.yaml`을 읽어 같은 구조임을 확인. 코드 확인(설정 구조) / 문서 서술은 미확인). 이 구성이 비교하는 것은 스킬 **버전**(model은 두 provider가 같음)이다. 여러 **모델** 비교는 `model`만 다른 provider 항목을 나열하면 되는데(추론: `model: config.model` 전달, `:1703`), Claude Agent SDK는 Claude 계열만 부를 것으로 보인다(추론). 다른 벤더 모델에서 스킬을 돌리려면 다른 에이전트 런타임이 필요하다: Codex(`openai:codex-sdk`, 스킬 위치 `.agents/skills`), OpenCode(`opencode:sdk`, `provider_id`+`model` 필드로 벤더·모델 선택: `src/providers/opencode-sdk.ts:266-270`). 런타임마다 스킬 발견 위치·호출 신호가 다르다(코드 확인: Codex 경로 정규식, OpenCode `skill` 도구 / 위치 규칙 자체는 문서 근거라 미확인).
5. 에이전트가 아닌 provider(`anthropic:messages`, `openai:chat` 등)에는 스킬 호출 메타데이터를 채우는 코드가 없다. `skillCalls`를 만드는 곳은 `claude-agent-sdk.ts`, `opencode-sdk.ts`, Codex 계열(`codexSkillMetadata.ts` 사용처)과 `codex-security.ts`뿐이다(코드 확인: `src/` 전체 grep). 따라서 이 provider들에는 `skill-used`를 쓸 수 없다.
6. 우회: SKILL.md를 일반 프롬프트로 넣기(추론). 로딩 동작은 코드로 확인했다. `prompts: file://SKILL.md`는 확장자 `.md`를 `processTemplateFile`로 읽어 파일 내용을 그대로 프롬프트 원문으로 쓴다(코드 확인: `src/prompts/index.ts:49`, `src/prompts/processors/text.ts:58`). 이 원문은 Nunjucks로 렌더링되므로(코드 확인: `src/evaluatorHelpers.ts:512` `nunjucks.renderString`) SKILL.md 안의 `{{`, `{%`는 변수·태그로 해석될 수 있다(영향은 추론). 또는 chat 형식 JSON 프롬프트의 system 메시지에 `{{skill}}`을 두고 `vars: { skill: file://SKILL.md }`로 넣는다(코드 확인: `src/evaluatorHelpers.ts` `renderPrompt`가 `file://` 변수를 파일 텍스트로 읽음, 해당 분기는 `:370` 부근). 단 이것은 "SKILL.md 본문을 항상 컨텍스트에 넣은 모델"을 비교할 뿐이다. 스킬 발견·점진 로딩·도구 호출 같은 에이전트 동작은 재현하지 않는다(추론). 이 우회에서 점검할 수 있는 것은 출력 품질 어서션(`llm-rubric`, `javascript` 등)뿐이다.

**Q2. 개선: `src/optimizer/promptOptimizer.ts`**

- 정체: `promptfoo optimize` 명령의 구현. 호출 경로는 `src/main.ts:110` `optimizeCommand` → `src/commands/optimize.ts` `doOptimize` → `optimizePromptTestSuite(config, testSuite, {promptIndex, providerIndex, validationSplit})`. (코드 확인) 라이브러리 export(`src/index.ts`)에는 포함되지 않는다(코드 확인: export 목록에 없음).
- 입력: 보통의 eval 설정 파일(`-c`, 생략 시 `promptfooconfig.yaml`) 하나. 옵션은 `--prompt-index`, `--provider-index`(기본 0·0), `--validation-split`(0 초과 0.5 이하), `--env-file`뿐이다(코드 확인: `src/commands/optimize.ts`). 최적화 대상은 **프롬프트 하나 × provider 하나**이고, 프롬프트는 문자열 리터럴이어야 한다(함수형 prompt는 오류, 코드 확인: `promptOptimizer.ts` "literal string prompts only"). 테스트나 시나리오가 최소 1개 필요하고, `validationSplit`은 시나리오 설정과 함께 쓸 수 없다(코드 확인).
- 동작: 기준선 평가 → 실패 사례(최대 6)와 성공 사례(최대 3)·점수 이력을 JSON으로 만들어 제안 모델에 보냄(시스템 메시지 `OPTIMIZE_PROMPT_SYSTEM_MESSAGE`, `src/prompts/grading.ts:133`) → 후보 프롬프트 3개(`DEFAULT_CANDIDATE_COUNT`, 원문·중복 제외) → 시드+후보를 같은 테스트로 평가 → 점수가 높은 것 채택(검증 분할이 있으면 검증 점수 우선) → 최대 3라운드(`DEFAULT_ROUNDS`). 라운드 1에서 후보를 못 얻으면 오류, 이후 라운드면 경고 후 지금까지의 최선을 유지. (코드 확인)
- 출력: 로그에 기준선·최선 점수(`metrics.score`)와 **최선 프롬프트 원문**을 찍는 것이 전부다. 설정 파일이나 SKILL.md를 고쳐 쓰지 않는다(코드 확인: `src/commands/optimize.ts`에 파일 쓰기 없음). 내부 평가는 `persisted: false`, `outputPath` 제거, `cache: false`라서 DB·출력 파일·캐시에 남지 않는다(코드 확인: `createEvaluationOptions`, `optimizePromptTestSuite`의 `new Eval(optimizationConfig, { persisted: false })`).
- 제안 모델: 대상 provider와 별개이며 `getDefaultProviders().suggestionsProvider`다. 환경변수의 API 키로 정해지고(OpenAI 키가 있으면 OpenAI, 없고 Anthropic 키가 있으면 Anthropic 등) `optimize`에는 이 모델을 지정하는 옵션이 없다(코드 확인: `src/providers/defaults.ts` `getDefaultProviderPreferences`·`getDefaultProviders`, `optimize.ts` 옵션 목록).
- 의미와 한계: 점수는 `assert` 결과에 달려 있어 어서션이 약하면 최적화도 무의미하다(추론). Claude Agent SDK에 SKILL.md를 `working_dir`로 주는 구성에서는 prompt가 사용자 요청 문장이라서, 최적화되는 것은 SKILL.md가 아니라 그 요청 문장이다(추론). SKILL.md를 prompt로 직접 넣는 우회(Q1-6)에서는 SKILL.md 텍스트가 최적화 대상이 되지만 `{{변수}}` 보존을 코드가 보장하지 않는다(추론: 후보 정규화는 비어 있음·원문과 같음·중복만 거름. `normalizeCandidates`).

**Q3. 한계: 비용·캐시, 데이터 유출, 라이선스**

- 비용. 호출 비용은 전부 사용자 키로 나가고, 응답마다 `cost`·`tokenUsage`가 집계된다(코드 확인: `src/evaluator.ts:5700` `eval_ran`의 `totalCost` 등). Claude Agent SDK는 SDK가 준 `total_cost_usd`를 쓰고(코드 확인: `claude-agent-sdk.ts`의 cost 계산부) `max_budget_usd`로 세션 상한을 줄 수 있다(코드 확인: 옵션 정의 `:596`). 모델 채점 어서션(`llm-rubric` 등)은 grader 모델을 한 번 더 부른다(추론: `src/matchers/llmGrading.ts`). `optimize`는 기준선 1회 + 라운드마다 (시드+후보 3)열 평가를 최대 3라운드 하므로 prompt 열 기준 최대 13회분 × 테스트 수가 들고, 검증 분할을 쓰면 검증용 평가가 더 붙으며 캐시도 꺼져 있다(코드 확인: `promptOptimizer.ts`의 라운드 루프, `createCandidateTestSuite`가 `[seedPrompt, ...candidates]`로 구성, `createEvaluationOptions`의 `cache: false`).
- 캐시. 기본 켜짐, 디스크(`~/.promptfoo/cache`, `PROMPTFOO_CACHE_PATH`·`PROMPTFOO_CONFIG_DIR`로 변경), TTL 14일(`src/cache.ts:55-68`, `src/util/config/manage.ts:15-17`). 끄기는 `--no-cache`(`src/commands/eval.ts`, `src/node/doEval.ts:627` `disableCache()`). 스킬 평가에 중요한 점: Claude Agent SDK의 캐시 키에 `working_dir` 안 모든 파일의 mtime 지문이 들어가므로(`src/providers/agentic-utils.ts:99-141` `getWorkingDirFingerprint`, `:205` `initializeAgenticCache`), SKILL.md가 `working_dir` 안에 있으면 수정 시 캐시가 무효화된다(코드 확인). 지문은 `working_dir`만 훑으므로, SKILL.md가 그 밖(사용자 홈 `.claude/skills`, 다른 경로의 `plugins`)에 있으면 내용이 바뀌어도 같은 키가 될 수 있다(추론: 캐시 키 재료는 `prompt`·`cacheKeyQueryOptions`·지문뿐이고 `plugins`는 경로 문자열만 들어감). 캐시 우회 조건(격리 워크스페이스, MCP, 상태 있는 세션 등)이 `:1833` 부근에 있다(코드 확인). 개발 중에는 `--no-cache`가 안전하다는 점은 레포의 `AGENTS.md`도 같다.
- 데이터 외부 전송. README는 "LLM evals run 100% locally - your prompts never leave your machine"(`README.md:74`)이라고 쓴다. 코드로는 평가가 로컬 프로세스에서 돌고 결과가 로컬 SQLite(`~/.promptfoo`)에 저장되는 것이 맞지만(코드 확인: `src/node/doEval.ts:874` `Eval.create`, `src/util/config/manage.ts:17`), 프롬프트·출력은 **내가 지정한 대상·채점·제안 provider로** 나간다(당연한 동작). 그 밖에 나가는 것:
  - telemetry: 기본 켜짐, `PROMPTFOO_DISABLE_TELEMETRY`로 끔(`src/telemetry.ts` `disabled`). PostHog(`https://a.promptfoo.app`)와 `https://r.promptfoo.app/`로 이벤트를 보낸다(`src/constants.ts:43-46`, `src/telemetry.ts` `sendEvent`). `eval_ran`의 속성은 프롬프트·테스트 수, `providerPrefixes`, `assertionTypes`, 토큰·비용 합계 같은 집계값이다(코드 확인: `src/evaluator.ts:5700-5725`). 로그인 정보가 있으면 이메일이 `r.promptfoo.app` 요청 본문에 들어간다(코드 확인: `sendEvent`의 `email: personProperties.email`). 문서는 "프롬프트·출력·테스트 케이스·API 키·전체 설정은 포함하지 않는다"고 하나(`site/docs/configuration/telemetry.md`, 미확인), 모든 `telemetry.record` 호출의 속성을 전수 확인하지는 않았다.
  - 업데이트 확인: 시작 시 `https://api.promptfoo.dev/api/latestVersion`을 GET(`src/updates.ts:15`, `src/main.ts` `checkForUpdates`). `PROMPTFOO_DISABLE_UPDATE`나 `CI` 환경변수가 있으면 건너뜀(`src/main.ts:56-60`). 문서는 "NPM 레지스트리를 확인"이라 쓰는데 코드의 대상은 promptfoo 도메인이다(문서와 구현의 차이).
  - 공유: 로그인(클라우드)하지 않으면 자동 공유가 없고, 로그인했으면 `--no-share`나 `PROMPTFOO_DISABLE_SHARING`이 없는 한 자동 공유가 기본이다(코드 확인: `src/util/sharing.ts` `shouldShareResults`). 공유는 프롬프트·vars·출력 등 결과 스냅샷을 올린다(문서 서술 `site/docs/usage/sharing.md`, 미확인 / 업로드 구현 `src/share.ts` 전체는 미탐색).
  - 원격 생성·채점: 레드팀 설정(`redteam`)이 있을 때만 `llm-rubric`·`similar`가 promptfoo API(`https://api.promptfoo.app`)로 갈 수 있다(코드 확인: `src/matchers/llmGrading.ts`, `src/matchers/similarity.ts`의 `cliState.config?.redteam` 조건과 `src/redteam/remoteGeneration.ts`). 일반 평가에는 해당이 없다. `PROMPTFOO_DISABLE_REMOTE_GENERATION`으로 끔.
  - 웹 UI: `promptfoo view`는 `httpServer.listen(port, ...)`으로 호스트를 지정하지 않고 기본 포트 15500(`src/server/server.ts:560`, `src/constants.ts:27`)이며 `cors()`를 전체에 적용한다(`:124`). 호스트 미지정 listen은 Node 기본 바인딩(모든 인터페이스)이라 같은 네트워크에서 접근될 수 있다(추론: Node 동작).
  - 에이전트 provider: `working_dir` 파일을 에이전트가 읽으므로 그 내용이 해당 벤더로 나간다(추론). 로컬 Claude Code 세션 인증으로 API 키 검사를 건너뛰는 `apiKeyRequired: false`가 있다(코드 확인: `claude-agent-sdk.ts:444`, `:1574`).
- 라이선스. 코어는 MIT(상업적 사용·수정·재배포 가능, 저작권·허가 문구 유지). 일부 파일은 Apache-2.0 코드를 옮겨 왔다(DeepEval·RAGAS 유래, 1절). 레드팀 crescendo는 PyRIT 기반이라 고지 문구가 있다. (코드 확인) 호스팅 서비스·모델 제공사의 이용 약관은 이 레포 밖이며 `미확인`이다.

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 설정·프롬프트·테스트 로딩 | `promptfooconfig.yaml`(+`file://`)을 읽어 `providers`·`prompts`·`tests`·`defaultTest`·`scenarios`를 `TestSuite`로 만듦. 테스트 입력은 YAML·JSON·CSV·xlsx·Sheets·HF 데이터셋 등. 프롬프트는 `.txt/.md/.json/.yaml/.py/.js/.csv`, 실행 파일 | `src/util/config/load.ts` `resolveConfigs`, `src/types/index.ts:1312` `TestSuiteConfigSchema`, `src/prompts/index.ts:25` `processPromptFile`, `src/util/testCaseReader.ts:749` `readTests` | 없음 | 핵심 | [config-loading](capabilities/config-loading.md) · ready | 코드 확인(스키마·확장자 분기) / 데이터 소스별 로더 내부는 미탐색 |
| 평가 실행 파이프라인(`eval`) | provider별 허용 prompt 열 × 테스트 × repeat를 돌며 렌더 → 호출 → 변환 → 채점 → 집계. 필터·재개·재시도·`--watch`·출력 파일·공유 결정 | `src/main.ts:88` `evalCommand`, `src/node/doEval.ts:276` `doEval`, `src/evaluator.ts:4053` `Evaluator`·`:1759` `runEval`·`:2516` `buildLivePromptColumns` | 설정 로딩, 프로바이더 패밀리, 어서션 패밀리, 결과 저장 | 핵심 | [eval-run](capabilities/eval-run.md) · ready | 코드 확인(진입·열 구성·호출 순서) / `Evaluator` 6천 줄 중 helper 다수 미탐색 |
| 스케줄러(동시성·레이트리밋·재시도) | provider별 호출 큐, 적응형 동시성, 429 재시도, 취소. 기본 동시성 4 | `src/scheduler/index.ts`, `src/scheduler/providerWrapper.ts` `wrapProviderWithRateLimiting`, `src/constants.ts:8`, `docs/scheduler-architecture.md` | 평가 실행 | 핵심 | `capabilities/scheduler.md` · 미작성 (승인 범위 밖) | 코드 확인(evaluator의 import·기본값) / 내부 알고리즘 미탐색 |
| 프로바이더 패밀리(범용 LLM API) | `id` 접두어(`openai:`, `anthropic:`, `google:`, `bedrock:`, `ollama:` …)로 provider를 만들어 `callApi(prompt, context)`로 응답·토큰·비용을 받음. 약 100개 factory(줄 패턴 집계, 추론) | `src/providers/registry.ts:421` `providerMap`·`:2013` `getProviderFactories`, `src/providers/registryTypes.ts` `ProviderFactory`, `src/types/providers.ts:139` `ApiProvider` | 공유 계약(ApiProvider) | 핵심 | `capabilities/provider-family.md` · 미작성 (승인 범위 밖) | 코드 확인(등록 구조·공통 인터페이스) / 개별 구현은 대표만 확인(Claude Agent SDK) |
| 에이전트 SDK 프로바이더 + 스킬 호출 메타 | Claude Agent SDK·Codex SDK/app-server·OpenCode SDK를 도구 허용·작업 디렉터리·스킬·플러그인 설정과 함께 호출. 도구·스킬 호출을 `metadata`에 기록 | `src/providers/claude-agent-sdk.ts:311` `deriveSkillCalls`·`:590` `skills`·`:1833` 캐시, `src/providers/opencode-sdk.ts:1939`, `src/providers/openai/codexSkillMetadata.ts`, `src/providers/agentic-utils.ts` | 프로바이더 패밀리, 응답 캐시 | 핵심 | [agent-providers](capabilities/agent-providers.md) · ready | 코드 확인(스킬 메타·캐시 키·옵션 전달) / SDK 쪽 스킬 로딩은 미확인(외부) |
| 커스텀 타깃 프로바이더 | 임의 앱·스크립트를 평가 대상으로: `http`(`python:`/`ruby:`/`golang:`/`exec:`는 script-bridges 스펙 소관), `websocket`, `browser`, MCP, A2A | `src/providers/registry.ts:432-435` `createScriptBasedProviderFactory`, `src/providers/http.ts`, `src/providers/websocket.ts`, `src/providers/browser.ts`, `src/providers/mcp` | 프로바이더 패밀리, 스크립트 브리지 | 핵심 | `capabilities/custom-target-providers.md` · 미작성 (승인 범위 밖) | 코드 확인(등록 위치) / 각 구현 미탐색 |
| 어서션 패밀리 | `assert`의 `type`별 핸들러가 출력을 채점해 `GradingResult`를 돌려줌. 결정적(contains·regex·is-json·cost·latency…), 트레이스·trajectory, `skill-used`, 코드(js·python·ruby·webhook), `not-` 반전 | `src/assertions/index.ts:229-322` `ASSERTION_HANDLERS`(약 68개 키), `src/assertions/skill.ts` `handleSkillUsed`, `src/types/index.ts:858` `AssertionParams` | 공유 계약(어서션 핸들러), 프로바이더 패밀리 | 핵심 | [assertion-family](capabilities/assertion-family.md) · ready | 코드 확인(등록부·`skill-used` 본문) / 나머지 핸들러 본문 미탐색 |
| 모델 채점 매처·기본 grader 선택 | `llm-rubric`, `factuality`, `g-eval`, `similar`, `select-best` 등이 grader 모델을 호출. grader는 설정 또는 환경변수 키로 정한 기본 provider | `src/matchers/llmGrading.ts:181` `matchesLlmRubric`, `src/matchers/comparison.ts`, `src/matchers/similarity.ts`, `src/providers/defaults.ts` `getDefaultProviders` | 어서션 패밀리, 프로바이더 패밀리 | 핵심 | [model-graded-matchers](capabilities/model-graded-matchers.md) · ready | 코드 확인(기본 provider 선택·원격 채점 조건) / 프롬프트 템플릿 본문 미탐색 |
| 결과 저장·출력·결과 관리 명령 | 평가 결과를 SQLite에 저장하고 `list/show/export/import/delete/retry`, `-o` 출력(json·csv·html·jsonl 등)으로 다룸 | `src/models/eval.ts`, `src/database/tables.ts`, `drizzle/`, `src/util/output.ts:748` `writeMultipleOutputs`, `src/commands/{list,show,export,import,delete,retry}.ts` | 평가 실행 | 핵심 | [results-store](capabilities/results-store.md) · ready | 코드 확인(경로·명령 등록) / 테이블 스키마·마이그레이션 세부 미탐색 |
| 응답 캐시 | provider 응답을 디스크(기본)·메모리에 TTL 14일로 저장, `--no-cache`·repeat별 이름공간. 에이전트 provider는 작업 디렉터리 지문을 키에 포함 | `src/cache.ts:55`·`:57`·`:60`, `src/providers/agentic-utils.ts:99`·`:205`, `src/evaluator.ts:6294` | 없음 | 핵심 | [response-cache](capabilities/response-cache.md) · ready | 코드 확인 |
| 프롬프트 최적화(`optimize`) | 프롬프트 1개×provider 1개를 평가 결과로 제안 모델에게 개선시켜 후보를 다시 평가, 최선 프롬프트를 출력 | `src/commands/optimize.ts` `doOptimize`, `src/optimizer/promptOptimizer.ts` `optimizePromptTestSuite`, `src/prompts/grading.ts:133` | 평가 실행, 모델 채점 매처(기본 provider) | 핵심 | [prompt-optimize](capabilities/prompt-optimize.md) · ready | 코드 확인(전체 흐름·옵션·출력) |
| 테스트·어서션 생성(`generate`) | 설정의 프롬프트로 합성 테스트 케이스(`generate dataset`)와 추가 어서션(`generate assertions`)을 만들어 YAML로 출력. 실제 LLM 호출은 페르소나 1회 + 케이스 ⌈total/20⌉회(어서션은 질문 1회 + 변환 N회)이고 변수 추출은 LLM이 아니라 로컬 정규식이다 | `src/commands/generate/dataset.ts`, `src/commands/generate/assertions.ts`, `src/testCase/synthesis.ts:170` `synthesize` | 프로바이더 패밀리(기본 provider) | 핵심 | [generate-datasets](capabilities/generate-datasets.md) · ready | 코드 확인(명령·함수 존재) / 본문 미탐색 |
| 트레이싱(OTLP) | provider가 보낸 OpenTelemetry span을 로컬 수신·저장해 `trace-*`·`trajectory:*` 어서션과 UI에 제공 | `src/tracing/otlpReceiver.ts`, `src/tracing/store.ts`, `src/assertions/index.ts`(trace 핸들러), `src/server/routes/traces.ts` | 평가 실행, 어서션 패밀리 | 핵심 | `capabilities/tracing.md` · 미작성 (승인 범위 밖) | 코드 확인(구성 요소 존재·마운트) / 수신 프로토콜 세부 미탐색 |
| 스크립트 브리지·확장 훅 | Python·Ruby·Go 워커로 provider·어서션·프롬프트·변수를 실행하고, `extensions`의 beforeAll/afterEach 훅을 호출 | `src/python/workerPool.ts`, `src/python/wrapper.py`, `src/ruby/wrapper.rb`, `src/golang/wrapper.go`, `src/evaluatorHelpers.ts:756` `runExtensionHook` | 없음 | 핵심 | [script-bridges](capabilities/script-bridges.md) · ready | 코드 확인(파일·훅 함수 존재) / 프로토콜 미탐색 |
| Node 라이브러리 API | `import promptfoo from 'promptfoo'`로 `evaluate`, `assertions`, `cache`, `loadApiProvider`, `redteam.*`, `guardrails`, `getModelPricing` 사용. `./contracts` 별도 export | `src/index.ts`, `src/node/evaluate.ts:65` `evaluate`, `src/contracts.ts` | 평가 실행 | 핵심 | `capabilities/node-api.md` · 미작성 (승인 범위 밖) | 코드 확인(export 목록) |
| 레드팀 파이프라인(`redteam init/generate/run/report/setup/discover`) | 대상 앱의 목적을 추출하고 플러그인×전략으로 공격 케이스를 생성(`redteam.yaml`) 후 평가·리포트 | `src/redteam/shared.ts:24` `doRedteamRun`, `src/redteam/commands/generate.ts:273` `doGenerateRedteam`, `src/main.ts:124-135` | 평가 실행, 레드팀 플러그인·전략 | 핵심 | `capabilities/redteam-pipeline.md` · 미작성 (승인 범위 밖) | 코드 확인(진입·`doEval` 호출) / 생성 내부 미탐색 |
| 레드팀 플러그인·그레이더 패밀리 | 취약점 종류(`pii`, `harmful`, `sql-injection`, …)별로 테스트를 생성하고 응답을 채점하는 클래스·팩토리 | `src/redteam/plugins/base.ts:42` `RedteamPluginBase`·`:398` `RedteamGraderBase`, `src/redteam/plugins/index.ts:94` `PluginFactory`·`:715` `Plugins`, `src/redteam/graders.ts` | 프로바이더 패밀리, 어서션 패밀리 | 핵심 | `capabilities/redteam-plugins.md` · 미작성 (승인 범위 밖) | 코드 확인(공통 계약·등록부) / 디렉터리 항목 약 69개 중 개별 플러그인 미탐색 |
| 레드팀 전략 패밀리 | 생성된 케이스를 변형(`base64`, `jailbreak`, 다국어, 다중 턴 등)하는 `Strategy.action` | `src/redteam/strategies/types.ts:94` `Strategy`, `src/redteam/strategies/index.ts:62` `Strategies` | 레드팀 플러그인 | 핵심 | `capabilities/redteam-strategies.md` · 미작성 (승인 범위 밖) | 코드 확인(계약·등록부) / 디렉터리 항목 약 35개 개별 미탐색 |
| 레드팀 공격 프로바이더 | 반복·트리·crescendo·GOAT·hydra 등 다중 턴 공격을 provider로 구현 | `src/redteam/providers/registry.ts:138` `redteamProviderFactories`, `src/redteam/providers/iterative.ts`, `.../crescendo`, `.../goat.ts`, `.../hydra` | 프로바이더 패밀리, 원격 생성 연동 | 핵심 | `capabilities/redteam-attack-providers.md` · 미작성 (승인 범위 밖) | 코드 확인(등록부·파일 존재) / 각 알고리즘 미탐색 |
| 웹 UI·로컬 서버(`view`) | 결과 표·비교 보기, eval 생성기, 레드팀 설정·리포트, 모델 감사 화면. Express 서버 + React 앱 | `src/commands/view.ts`, `src/server/server.ts:370` `startServer`·`:326-335` 라우터, `src/app/src/routes.tsx`, `src/app/package.json` | 결과 저장 | 부속 | [web-ui](capabilities/web-ui.md) · ready | 코드 확인(서버 라우터 목록) / React 앱 내부 미탐색 |
| MCP 서버(`mcp`) | 평가 실행·비교·어서션 실행·공유 등을 MCP 도구로 외부 에이전트에 노출 | `src/commands/mcp/index.ts`, `src/commands/mcp/server.ts` `createMcpServer`, `src/commands/mcp/tools/*`(파일 13개) | 평가 실행, 레드팀 파이프라인 | 부속 | `capabilities/mcp-server.md` · 미작성 (승인 범위 밖) | 코드 확인(도구 등록 목록) / 도구 본문 미탐색 |
| 호스팅 서비스 연동 | 로그인(`auth`), 결과 공유(`share`), 클라우드 설정, 원격 생성·채점, telemetry, 업데이트 확인 | `src/commands/auth.ts`, `src/commands/share.ts`, `src/share.ts:60` `isSharingEnabled`, `src/util/sharing.ts`, `src/telemetry.ts`, `src/updates.ts`, `src/redteam/remoteGeneration.ts` | 결과 저장 | 부속 | `capabilities/hosted-integration.md` · 미작성 (승인 범위 밖) | 코드 확인(엔드포인트 상수·공유 결정 로직) / 업로드 프로토콜(`share.ts` 1051줄) 미탐색 |
| 코드 스캔(`code-scans` + GitHub Action) | PR diff를 promptfoo API로 보내 LLM 보안 취약점을 찾고 PR 코멘트·SARIF로 보고 | `src/codeScan/commands/run.ts`, `src/codeScan/scanner/index.ts:204`(기본 호스트 `https://api.promptfoo.app`), `code-scan-action/action.yml`, `code-scan-action/src/main.ts` | 호스팅 서비스 연동 | 부속 | `capabilities/code-scan.md` · 미작성 (승인 범위 밖) | 코드 확인(진입점·기본 호스트·입력) / 스캐너 내부 미탐색 |
| 모델 파일 스캔(`model-scan`) | 외부 파이썬 도구 `modelaudit`을 자식 프로세스로 실행해 모델 파일 보안 스캔, 결과 저장·공유 | `src/commands/modelScan.ts:187` `spawn('modelaudit')`, `src/models/modelAudit.ts` | 호스팅 서비스 연동(선택) | 부속 | `capabilities/model-scan.md` · 미작성 (승인 범위 밖) | 코드 확인(spawn 위치) / `modelaudit` 자체는 이 레포 밖(미확인) |
| 에이전트 플러그인 번들 | Codex·Claude Code에 설치되는 스킬 4개(`promptfoo-evals`, `-provider-setup`, `-redteam-setup`, `-redteam-run`). promptfoo를 **쓰는 법**을 에이전트에게 가르치는 용도이고, 평가 대상이 아님 | `plugins/promptfoo/skills/*/SKILL.md`, `plugins/AGENTS.md` | 없음 | 부속 | `capabilities/agent-plugin-bundle.md` · 미작성 (승인 범위 밖) | 코드 확인(`plugins/AGENTS.md`·SKILL.md 앞부분) / references·scripts 미탐색 |
| 문서 사이트(`site/`) | Docusaurus 문서·블로그(추적 파일 약 1300개)와 `functions/_middleware.ts`(배포 대상은 추론하지 않음). 설정·provider 사용 가이드의 1차 문서 | `site/package.json`, `site/docusaurus.config.ts`, `site/docs/`, `site/functions/_middleware.ts` | 없음 | 부속 | `capabilities/docs-site.md` · 미작성 (승인 범위 밖) | 코드 확인(구성) / 문서 본문은 필요한 것만 읽음 |
| 컨테이너·Helm 배포 | 공식 이미지(Node 24 Alpine + Python)를 빌드하고 Kubernetes 차트로 배포. 이미지 `ghcr.io/promptfoo/promptfoo` | `Dockerfile`, `helm/chart/promptfoo/values.yaml`·`templates/deployment.yaml` | 웹 UI·로컬 서버 | 부속 | `capabilities/container-helm.md` · 미작성 (승인 범위 밖) | 코드 확인(Dockerfile 앞부분·values) / 차트 템플릿 세부 미탐색 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| `ApiProvider`·`ProviderResponse`: `id()`, `callApi(prompt, context, options) → {output, error, tokenUsage, cost, metadata…}`, `ProviderFactory{test, create}` 접두어 디스패치 | 프로바이더 패밀리, 에이전트·커스텀 provider, 모델 채점, 최적화, 생성, 레드팀 | `src/types/providers.ts:139`, `src/providers/registryTypes.ts`, `src/providers/registry.ts:421`, `src/redteam/providers/registry.ts:138` | [provider-contract](capabilities/provider-contract.md) · ready | 코드 확인 |
| `TestSuite`/`UnifiedConfig` 설정 스키마(`providers`, `prompts`, `tests`, `defaultTest`, `scenarios`, `sharing`, `env`, `extensions` …) | 설정 로딩, 평가 실행, 최적화, 레드팀 생성, 서버 | `src/types/index.ts:1312` `TestSuiteConfigSchema`, `src/util/config/load.ts` | [config-loading](capabilities/config-loading.md)에 합침 · ready | 코드 확인(스키마 앞부분) / 전체 필드 미탐색 |
| 어서션 핸들러 계약: `(AssertionParams) → GradingResult`, `not-` 접두어 반전, 가중치·임계값·`metric` | 어서션 패밀리, 모델 채점, 레드팀 플러그인의 `getAssertions` | `src/types/index.ts:858` `AssertionParams`, `src/assertions/index.ts:229-322`, `src/redteam/plugins/base.ts` `getAssertions` | [assertion-family](capabilities/assertion-family.md)에 합침 · ready | 코드 확인 |
| `SkillCallEntry` 메타데이터: `response.metadata.skillCalls[{name,input,path,source,is_error}]` | 에이전트 provider(생산자) ↔ `skill-used` 어서션(소비자) | `src/types/providers.ts:49`, `src/assertions/skill.ts` | [skill-calls-metadata](capabilities/skill-calls-metadata.md) · ready | 코드 확인 |
| 평가 결과 레코드(`Eval`, `EvalResult`, `CompletedPrompt.metrics`, `EvaluateResult`) | 평가 실행, 결과 저장, 최적화(비영속), 서버, 공유, 내보내기 | `src/models/eval.ts`, `src/models/evalResult.ts`, `src/database/tables.ts` | [eval-records](capabilities/eval-records.md) · ready | 코드 확인(사용처) / 테이블 정의 세부 미탐색 |
| 기본 provider 선택 규칙(환경변수 키 → grader·suggestions·synthesize·embedding provider) | 모델 채점, 최적화, 생성, 레드팀 추출 | `src/providers/defaults.ts` `getDefaultProviderPreferences`·`getDefaultProviders` | [default-providers](capabilities/default-providers.md) · ready | 코드 확인 |
| 원격 생성·채점 클라이언트(`https://api.promptfoo.app/api/v1/task`, 클라우드 로그인 시 해당 호스트) | 레드팀 플러그인·전략·공격 provider, 레드팀 설정 하의 채점 | `src/redteam/remoteGeneration.ts`, `src/remoteGrading.ts` | `capabilities/remote-generation.md` · 미작성 (승인 범위 밖) | 코드 확인(엔드포인트 결정) / 서버 쪽 동작 미확인 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 기능 목록("Test prompts and models", "red teaming", "Compare models", "CI/CD", "code scanning", "Share results"), `src/main.ts`가 등록한 서브커맨드 전체(eval·init·view·mcp·redteam·share·auth·cache·code-scans·config·debug·delete·export·generate·feedback·import·list·logs·model-scan·optimize·retry·validate·show), `src/index.ts` export, `src/assertions/index.ts` 핸들러 맵, `src/providers/registry.ts` `providerMap`, `src/server/server.ts` 라우터, 루트·중첩 `package.json`(`code-scan-action`, `src/app`, `site`, 예제 하위는 제외), `architecture/layers.json`, `plugins/AGENTS.md`, `Dockerfile`, `helm/chart/promptfoo`, 루트 `AGENTS.md`(진입점 후보로 읽음). 문서는 코드 안에서 생성되는 것까지 역할로 찾았다(`site/docs/guides/test-agent-skills.md`, `.../usage/prompt-optimization.md`, `.../configuration/{caching,telemetry}.md`).
- 문서와 구현의 차이: ① README의 "prompts never leave your machine"은 provider 호출·telemetry를 뺀 의미로 읽어야 한다(`README.md:74` vs 위 Q3). ② 텔레메트리 문서는 업데이트 확인을 "NPM 레지스트리"라 하나 코드는 `https://api.promptfoo.dev/api/latestVersion`을 부른다(`src/updates.ts:15`). ③ 스킬 가이드는 `skills:` 필터가 SDK 0.2.120에서 추가됐다고 하고 코드의 SDK 최소 버전 안내는 `^0.3.273`(`claude-agent-sdk.ts` 주석)이라 서로 다른 시점을 가리킨다(차이가 아니라 시점 차이일 수 있음 — 추론).
- 중첩 매니페스트·배포 입구를 찾은 결과: `package.json`은 루트·`src/app`·`site`·`code-scan-action`(이상 분석 대상)과 `examples/**`(예제, 제외)·`test/__fixtures__/**`(테스트 fixture, 제외)에 있다. `pip install promptfoo`/`brew install promptfoo`는 README가 말하지만(`README.md` Quick Start), 해당 패키징 코드는 이 레포에서 찾지 못했다(미확인: 별도 저장소일 가능성).
- 미탐색: `test/`·`.github/`·`CHANGELOG.md`·`CONTRIBUTING.md`·`codecov.yml`·biome/prettier/knip 설정(기본 제외 규칙), `examples/`(구조만 보고 스킬·비교 예제 2개만 읽음), `drizzle/` 마이그레이션, `scripts/`, `docs/plans/`, `.claude/`·`.agents/`(레포 개발용 스킬), `src/app/src` 화면 코드, `src/providers/*`의 개별 provider(Claude Agent SDK 외), `src/redteam/plugins/*`·`strategies/*` 개별 파일, `src/share.ts` 본문, `src/importers/openaiEvals`, `src/integrations/*`(Helicone·Langfuse·Portkey·HF), `src/guardrails.ts`, `src/blobs`, `site/blog`·`site/static`. 이유: 지도 단계는 진입점·사용자 동작·주요 호출을 설명할 수 있으면 멈춘다(워크플로 2장 3번).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 입구·로딩·평가 실행기·프로바이더·채점·저장과 최적화·레드팀·웹 UI·외부 서비스의 관계 |

실행 흐름도는 그리지 않았다(선택 사항).

### 그림 해설

그림을 열지 않고 이 글만 읽어도 구조가 이해되도록 쓴다. 그림은 왼쪽에서 오른쪽으로 읽고, 세로로 긴 파란 상자(입구)가 가운데 열의 세 모듈로 갈라진다. 선의 의미는 호출 방향이다.

**읽는 순서**
1. `src/main.ts`(CLI 서브커맨드 등록)와 `src/index.ts`(라이브러리 export) — 모든 기능의 입구.
2. `eval` 경로: `src/node/doEval.ts` `doEval` → `src/util/config/load.ts` `resolveConfigs` → `src/evaluator.ts` `Evaluator`.
3. 평가 한 건: `runEval` → 프롬프트 렌더(`renderPrompt`) → provider `callApi` → 어서션 → 결과 저장.
4. 갈라지는 길: `optimize`(Q2), `redteam`, `view`. 이 셋은 모두 평가 실행기를 다시 부르거나 그 결과를 읽는다.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 설정 파일(외부) | 사용자가 쓰는 `promptfooconfig.yaml` | `prompts`·`providers`·`tests`·`defaultTest` → 입구 | `src/types/index.ts:1312` `TestSuiteConfigSchema` | 코드 확인 |
| CLI·라이브러리 입구 | 서브커맨드 등록과 Node API. 가장 긴 상자 하나가 아래 세 모듈과 외부 서비스로 호출을 보낸다 | 인자·설정 경로 → 로딩·최적화·레드팀 호출, telemetry·업데이트 확인 | `src/main.ts:71-135`, `src/index.ts`, `src/entrypoint.ts` | 코드 확인 |
| 설정·프롬프트 로딩 | 설정·프롬프트·테스트 파일을 `TestSuite`로 변환 | 설정 경로 → `TestSuite`(평가 실행기로) | `src/util/config/load.ts` `resolveConfigs`, `src/prompts/index.ts:25` | 코드 확인(진입점) |
| 프롬프트 최적화 | 기준선 평가 → 제안 모델 → 후보 평가를 반복 | `TestSuite` → 평가 실행기 호출 여러 번, 최선 프롬프트 출력 | `src/optimizer/promptOptimizer.ts` `optimizePromptTestSuite` | 코드 확인 |
| 레드팀 | 공격 케이스 생성 후 평가 실행 | 목적 추출·플러그인·전략 → 케이스 → `doEval` | `src/redteam/shared.ts:24` `doRedteamRun`, `:141`의 `doEval` 호출 | 코드 확인 |
| 평가 실행기 | provider × prompt × test 조합 실행, 동시성·재시도, 집계 | `TestSuite` → provider 호출·어서션 호출·결과 저장 | `src/evaluator.ts:4053` `Evaluator`, `:1759` `runEval` | 코드 확인 |
| SQLite·캐시 | 결과 영속, 응답 캐시(디스크). 평가 실행기가 결과를 저장하고, 캐시는 provider 호출 계층이 읽고 씀 | `Eval`·`EvalResult` 레코드, 캐시 항목 | `src/models/eval.ts`, `src/database/tables.ts`, `src/cache.ts`, `src/providers/agentic-utils.ts:234` | 코드 확인(구성 요소·사용처) |
| 어서션·매처 | `assert` 핸들러가 출력·메타데이터를 채점. 모델 채점은 grader provider를 호출하지만 이 그림에는 그 선을 그리지 않았다 | `AssertionParams` → `GradingResult` | `src/assertions/index.ts:229-322`, `src/matchers/llmGrading.ts:181` | 코드 확인 |
| 프로바이더 | 접두어 레지스트리로 모델·에이전트·스크립트 대상을 만들고 `callApi` 호출 | 프롬프트·context → `ProviderResponse` | `src/providers/registry.ts:421`, `src/types/providers.ts:139` | 코드 확인 |
| LLM API·에이전트 SDK(외부) | 실제 모델·에이전트 런타임 | HTTPS·SDK 호출 | `src/providers/claude-agent-sdk.ts`(대표) | 코드 확인(호출 쪽만) / 외부 동작 미확인 |
| 웹 UI·서버 | 저장된 결과를 REST로 서빙, React 앱이 표시. 서버는 평가 실행도 요청받는다 | HTTP `/api/eval` 등 ↔ DB 조회 | `src/server/server.ts:326-335`, `src/server/routes/eval.ts`(`evaluateWithSource` import) | 코드 확인(라우터·import) / 요청별 흐름 미탐색 |
| promptfoo 호스팅(외부) | telemetry·업데이트 확인·공유·원격 생성의 상대 | HTTPS | `src/constants.ts:43-46`, `src/updates.ts:15`, `src/redteam/remoteGeneration.ts` | 코드 확인(호출 쪽) / 서버 쪽 미확인 |

**그림에서 생략한 선과 부속**
- 모델 채점이 grader provider를 다시 부르는 선, `optimize`가 제안 모델을 부르는 선, 입구에서 웹 UI를 띄우는 `view` 선은 정리를 위해 그리지 않았다(코드 근거는 위 Q2·Q3와 기능 지도 행에 있다).
- 부속 배포 단위(문서 사이트 `site/`, `helm`·`Dockerfile`, `code-scan-action`, `plugins/promptfoo` 스킬 번들, 모델 파일 스캔)는 노드를 12개 이내로 두려고 그림에 넣지 않았고 카드 한 장으로만 표기했다. 지도 표의 해당 행을 본다.

**검증 결과** (세 가지를 구분한다)
- 산출물 검증(`archify deliver`, 기준 `--quality showcase`, `--repo-root repos/promptfoo`): 통과. 아티팩트 검사 9개 중 9개 통과, 구도 오류 0·경고 0, 저장소 근거 12건 확인(리비전 `dfe2d45…`). 명세 sha256 `2d8d4f50…`, HTML sha256 `29cea2dc…`. 이것은 결정적 산출물 검사이며 브라우저 확인이 아니다.
- 브라우저 확인(`archify visual-check`): 통과. 로컬 Chrome으로 1440×900·1600×1000·1920×1080·2048×1320(라이트)에서 가로·세로 넘침 없음, 노드 글자 최소 투영 크기 7.3px(기준 6px). 결과 파일은 [`../../artifacts/promptfoo/structure-visual-check/structure.visual-check.json`](../../artifacts/promptfoo/structure-visual-check/structure.visual-check.json)과 같은 폴더의 PNG 4장이다. 브라우저 도구(Claude in Chrome)는 쓰지 않았다.
- 시각 검토: 1440×900 라이트 스크린샷 한 장만 직접 보았다. 노드 겹침·잘림·선 교차가 보이지 않았고 텍스트는 읽을 수 있었다. 다크 테마와 다른 해상도 캡처는 사람이나 별도 검토자가 보지 않았다(`visualReview`는 `pending`으로 남음).

**미확인 영역**
- 에이전트 provider가 스킬을 실제로 로드·호출하는 외부 SDK(Claude Code·Codex·OpenCode)의 동작.
- 호스팅 서버(api.promptfoo.app 등)가 받은 데이터를 어떻게 쓰는지.
- 평가 실행기 내부의 helper 다수, 개별 provider·플러그인·전략, 웹 앱 화면 코드.

---

## 4. 질문 (Questions)

아직 없음. 목적 질문 Q1~Q3의 초기 답은 2절 "목적 질문에 대한 초기 답"에 있다. 상세 확인이 필요하면 `questions/qN-*.md`로 분리한다.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **스펙 작성 후 정정·보강** (스펙 2.1의 "문서와 구현이 다른 곳"이 원본이다. 이 문서의 표와 Q1~Q3 서술을 아래 기준으로 읽는다):
  - `skills`가 있어도 `Skill`은 허용 목록이 아니라 사용 가능 도구(`tools`)에 더해지고, `config.tools`가 없고 `allow_all_tools`가 아닐 때만이다(agent-providers R-12).
  - 에이전트 provider 캐시는 인스턴스마다 새 UUID가 키에 들어가 새 프로세스에서는 재사용되지 않는다. Codex SDK·app-server는 응답 캐시가 없다(response-cache, agent-providers).
  - `generate`의 호출 수는 페르소나 1회 + 케이스 ⌈total/20⌉회이고 변수 추출은 로컬 정규식이다(generate-datasets).
  - `optimize`는 옵션이 `--prompt-index`·`--provider-index`·`--validation-split`뿐이고 라운드 3×후보 3이 고정이며 열 점수는 행 점수의 합이다(prompt-optimize).
  - grader를 따로 지정하지 않으면 평가 대상 provider가 grader가 되고, 자기 채점 회피 장치가 없다(default-providers R-15·R-20).
  - `view` 서버는 인증이 없고 CORS가 전체 허용이며 host 옵션이 없다(web-ui).
  - 원본 UI와 CLI에는 모델·스킬 버전별 시간순 조회나 태그 읽기가 없다(results-store, web-ui).
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(승인 범위 15개는 모두 ready, 나머지 행은 승인 범위 밖이라 미작성).
- 범위 승인 때 물을 것: 사용자 목적에 직접 닿는 행은 "에이전트 SDK 프로바이더 + 스킬 호출 메타", "프롬프트 최적화", "응답 캐시", "어서션 패밀리"(특히 `skill-used`), "프로바이더 패밀리"다. 부속 8개 행(웹 UI, MCP 서버, 호스팅 서비스 연동, 코드 스캔, 모델 파일 스캔, 에이전트 플러그인 번들, 문서 사이트, 컨테이너·Helm)은 각각 스펙으로 쓸지 따로 묻는다.
- 사용자 목적에서 아직 코드로 닫지 못한 것: Claude Agent SDK가 `working_dir` 밖의 스킬(사용자 홈 `.claude/skills`)을 찾는 조건, 에이전트 provider의 비용 집계 세부, `llm-rubric` grader 프롬프트와 기본 grader 모델 이름.
