---
sha: "a201f47d2b17d6cf6a9347f336691b00c98720a1"
created: 2026-10-22
updated: 2026-10-22
sources:
  - scripts/run-structured-compare-calibration.mjs
  - package.json
  - .npmrc
  - env.local.example
  - packages/core/src/services/model/defaults.ts
  - packages/core/src/utils/environment.ts
  - packages/core/src/services/llm/service.ts
  - packages/core/src/services/llm/adapters/openai-adapter.ts
  - packages/core/src/services/llm/adapters/deepseek-adapter.ts
  - packages/core/src/services/template/default-templates/evaluation-structured-compare/content.ts
  - docs/workspace/compare-evaluation-analysis/structured-compare-calibration/README.md
  - docs/workspace/compare-evaluation-analysis/structured-compare-calibration/latest/summary.md
  - docs/workspace/compare-evaluation-analysis/structured-compare-calibration/latest/summary.json
  - docs/workspace/compare-evaluation-analysis/structured-compare-calibration/latest/live-basic-system-boundary-control/llm-calls.json
  - docs/workspace/compare-evaluation-analysis/structured-compare-calibration/latest/live-basic-system-boundary-control/executions.json
  - docs/workspace/compare-evaluation-analysis/auto-compare-rewrite-effect-analysis.md
  - docs/workspace/compare-evaluation-analysis/protocol-migration-minimal-plan.md
depends:
  - ./llm-evaluation.md
  - ./iterate-rewrite.md
status: ready
reimplementation: 미실행
---

# 구조화 비교 보정 스크립트 (부속, 개발자용)

> 인자 없이 `pnpm compare:calibrate`로 실행하면, 하드코딩된 6개 케이스(실모델 1 + 합성 5)를 차례로 코어 평가 서비스(구조화 비교)에 넣고, 결과 신호를 케이스에 적힌 "허용 값 목록"과 대조해 적중 수를 세고, 같은 평가 결과로 만든 재작성 입력문을 모델에 한 번 보낸 뒤, 모든 입출력과 LLM 호출 로그를 `docs/…/structured-compare-calibration/latest/`에 파일로 남기는 일회 실행 스크립트다.

경로 표기: 모든 `파일:줄`은 `repos/prompt-optimizer/` 기준이다. 라이선스는 AGPL-3.0-only(overview 1절)라서 코드·케이스 본문(중국어 프롬프트·샘플 출력)은 복사하지 않고 C-ID(위치)로만 가리키며 구조·규칙을 글로 쓴다. 설치·빌드·네트워크·모델 호출·스크립트 실행은 하지 않았다(검증 수준은 모두 읽기 기준. 커밋된 `latest/` 산출물은 원작성자의 과거 실행 기록을 열람한 것이고 우리가 실행한 것이 아니다).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 개발자가 레포 루트에서 `pnpm compare:calibrate`를 실행한다. pnpm 스크립트가 먼저 `@prompt-optimizer/core`를 빌드하고 나서 `.mjs`를 실행한다(R-01). 인자는 없다.
2. 스크립트가 루트 `.env.local`을 읽고(R-02), 출력 폴더 `latest/`를 통째로 지운 뒤(R-16), 메모리 저장소 위에 코어 서비스를 직접 조립한다. `custom`·`deepseek` 두 모델이 활성인지 확인하고 둘 다 `temperature 0.2`·`timeout 180000ms`로 덮어쓴다(R-03, R-04). LLM 서비스는 호출 기록·재시도 래퍼로 한 번 감싼다(R-05, R-06).
3. 케이스 6개를 고정 순서(live → 합성 5개)로 하나씩 처리한다. 케이스 선택·필터는 없다(R-07).
4. **live 케이스만** 스냅샷 4개를 실제 모델로 만든다(같은 사용자 입력을 {워크스페이스 프롬프트, 이전 프롬프트} × {target 모델 `custom`, teacher 모델 `deepseek`}로 순차 실행, R-12). 합성 케이스 5개는 스냅샷 출력이 소스에 박혀 있어 이 단계가 없다(R-09).
5. `type: 'compare'` 평가 요청을 만들어 `evaluationService.evaluate`를 한 번 부른다. 역할 힌트가 있으므로 구조화 비교가 돌고(llm-evaluation R-18~R-22), 판정 호출 3~4회 + 합성 1회가 일어난다(R-13).
6. 평가 응답의 `compareStopSignals`·`compareJudgements`·`conflictSignals`를 케이스의 `expected`와 대조해 항목별 적중 여부를 계산한다. 이 값은 보고만 되고 종료 코드·중단에 쓰이지 않는다(R-19, R-20).
7. 평가 응답으로 재작성 입력문을 만들어(iterate-rewrite R-20·R-21) 반복 템플릿 없이 단일 user 메시지로 `rewriteModelKey` 모델에 한 번 보내고 출력을 저장한다(R-14, R-15).
8. 케이스마다 파일 14~15개를, 전체 종료 시 `summary.json`·`summary.md`를 쓴다(R-17, R-18). 한 케이스라도 예외가 나면 거기서 중단하고 종료 코드 1이며 총괄 요약은 만들어지지 않는다(R-16).

한 번 실행의 LLM 호출 수(재시도 제외): live 9(실행 4 + 판정 3 + 합성 1 + 재작성 1), 합성 중 medical·ecommerce·legal·teaching 각 5, hiring 6(replica 쌍이 하나 더 있음), 합계 35. 합성 케이스는 실행 호출이 없어 `custom` 모델은 live 케이스의 a·b 스냅샷 2번에만 쓰이고 나머지 33번은 `deepseek`이다.

### 1.2 범위·통합 지점 [필수]
- 제공: 실행 방법·환경변수·모델 고정, 케이스 정의 구조와 기대 판정 표기, 단계별 입출력, 결과 파일 형식·위치, 기대 대조의 의미와 "통과/실패"가 어디에도 정의돼 있지 않다는 사실, 심판 안정성을 이 스크립트가 측정하는지 여부(R-21).
- 제외:
  - 평가 서비스 내부(요청 검증, 판정·합성 메시지, 파싱, 신호 도출): [llm-evaluation](./llm-evaluation.md)(R-17~R-23, R-29~R-31)을 따르고 복제하지 않는다.
  - 재작성 입력문을 만드는 규칙(payload 압축, `rewriteGuidance`, 템플릿): [iterate-rewrite](./iterate-rewrite.md)(R-12~R-24). 여기서는 호출 모양만 정한다.
  - 실제 실행·모델 응답 품질. 모델 어댑터·모델 관리자 내부는 경계만 쓴다.
- 외부 의존·선행 계약:
  - 코어 빌드 산출물 `packages/core/dist/index.js`의 export: `MemoryStorageProvider`, `createPreferenceService`, `createTemplateLanguageService`, `createTemplateManager`, `createModelManager`, `createLLMService`, `createEvaluationService`, `buildRewritePayload`, `buildRewritePromptFromEvaluation`. 빌드가 없으면 import 단계에서 실패한다(R-01).
  - `dotenv` 패키지(루트 `package.json`에는 없고 `packages/core` 등에 있다. 루트 `.npmrc`의 `shamefully-hoist=true`로 루트에서 해석될 것으로 추론, R-02).
  - 외부 LLM 서비스 2개: `.env.local`이 가리키는 OpenAI 호환 엔드포인트(`custom`)와 DeepSeek(`deepseek`).
  - llm-evaluation의 `evaluate`(비스트림), iterate-rewrite의 `buildRewritePayload`·`buildRewritePromptFromEvaluation`.
- 소유 상태·부작용: 프로세스 안의 메모리 저장소와 호출 로그 배열(케이스마다 비움). 디스크 부작용은 `latest/` 삭제 후 재생성 하나뿐이고(R-16), 이 폴더는 git 추적 대상이다(커밋된 `latest/` 기록 87개 파일). 모델 설정 변경(이름·temperature·timeout)은 메모리 저장소에만 있고 영속하지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**실행 인터페이스**

| 항목 | 값 | 의미·제약 |
|---|---|---|
| 명령 | 루트 `package.json`의 스크립트 `compare:calibrate` = `pnpm -F @prompt-optimizer/core build && node scripts/run-structured-compare-calibration.mjs` | 패키지 매니저는 pnpm(`engines`가 npm·yarn을 막음). 직접 `node …mjs`로 부르면 빌드를 건너뛴다. C-01 |
| CLI 인자·옵션 | 없음 | `process.argv`를 읽지 않는다. 케이스 선택, 반복 횟수, 출력 경로, 모델 선택 옵션이 모두 없다. 바꾸려면 소스를 고친다. |
| 환경변수 | 스크립트가 직접 읽는 것은 없음. `<루트>/.env.local`을 `dotenv.config`로 로드하면 코어가 읽는다 | 아래 두 줄. `.env.local`은 `.gitignore`에 있다. |
| `custom` 모델 | `VITE_CUSTOM_API_KEY`, `VITE_CUSTOM_API_BASE_URL`, `VITE_CUSTOM_API_MODEL`, `VITE_CUSTOM_API_HEADERS` | 넷 중 **하나라도** 비어 있지 않으면 활성. 기본값: baseURL `http://localhost:11434/v1`, 모델 ID `custom-model`. 키 유효성은 검사하지 않는다. C-07 |
| `deepseek` 모델 | `VITE_DEEPSEEK_API_KEY` | 값이 비어 있지 않으면 활성. 모델 ID는 환경변수가 아니라 DeepSeek 어댑터의 첫 정적 모델이다. 표시 이름을 스크립트가 "DeepSeek Chat (Calibration)"으로 바꾸지만 실제 ID와 무관한 고정 문자열이다. |
| 고정 파라미터 | 두 모델 모두 `temperature: 0.2`, `timeout: 180000` | 기존 `paramOverrides` 위에 덮어씀. `top_p`·seed 고정은 없다. 재시도 상수 `CALIBRATION_MAX_RETRIES=3`. C-01, C-07 |

**케이스 구조.** 케이스는 소스 상수 `LIVE_BASIC_SYSTEM_CASE` 1개와 배열 `SYNTHETIC_CASES` 5개(C-02, C-03). 두 종류가 `kind`로 구분되고 필드가 다르다.

| 필드 | live | synthetic | 의미 |
|---|---|---|---|
| `id`, `kind`, `title`, `description` | ○ | ○ | `id`가 결과 하위 폴더 이름. `kind`는 `'live'` 또는 `'synthetic'`. 설명 문자열은 시나리오 의도를 중국어로 서술. |
| `mode` | `{functionMode:'basic', subMode:'system'}` | 같음 | 6개 모두 basic/system. |
| `focus` | ○ | ○ | 평가 요청의 `focus.content`로 전달(`source:'system'`, `priority:'highest'`). 무엇을 중점으로 볼지 케이스 의도를 적은 문장. |
| `evaluatorModelKey` | `'deepseek'` | `'deepseek'` | 평가(판정·합성) 모델. 6개 모두 deepseek. |
| `rewriteModelKey` | `'deepseek'` | `'deepseek'` | 재작성 호출 모델. 6개 모두 deepseek. |
| `targetModelKey`, `teacherModelKey` | `'custom'`, `'deepseek'` | 없음 | live의 스냅샷 실행 모델. target 쪽 2개 스냅샷은 custom, teacher 쪽 2개는 deepseek. |
| `previousPrompt`, `workspacePrompt`, `userInput` | ○ | 없음 | live의 두 프롬프트(이전/현재)와 공용 사용자 입력 1개. |
| `targetWorkspacePrompt`, `targetPreviousPrompt` | 없음 | ○ | 합성 케이스의 현재/이전 프롬프트. 평가 요청의 `target.workspacePrompt`·`target.referencePrompt`와 재작성 입력에 쓰인다. |
| `testCases` | 없음(스크립트가 `tc-1` 1개를 만듦, 라벨 "사용자 입력") | ○ (`tc-1` 1개씩) | 평가 요청 `testCases`. |
| `snapshots` | 없음(실행 결과로 생성) | ○ 4개(hiring은 5개) | 손으로 쓴 스냅샷: `{id a~e, label, testCaseId, promptRef, promptText, output, modelKey, versionLabel}`. `output`은 소스에 박힌 샘플 출력이고 `modelKey`는 라벨일 뿐 실제 호출은 없다. |
| `compareHints` | 스크립트가 고정 생성 | ○ | 모두 `mode:'structured'`, 공유 케이스·같은 프롬프트·교차 모델 힌트 3개 `true`. |
| `expected` | **없음**(탐색 전용) | ○ | 기대 판정. 아래. |

역할 배정은 6개 케이스 모두 a=`target`, b=`baseline`, c=`reference`, d=`referenceBaseline`이고, hiring만 e=`replica`가 추가된다. 구성 의도: a는 "현재 프롬프트 × 대상 모델", b는 "이전 프롬프트 × 대상 모델", c·d는 같은 두 프롬프트를 teacher 모델로 돌린 기준선이다. 합성 케이스의 스냅샷은 시나리오(예: 샘플 트리거 하드코딩)에 맞춰 사람이 출력까지 써 둔 것이고, hiring의 replica `e`는 같은 프롬프트의 "재실행"이지만 실제 재실행이 아니라 `a`와 다른 결론(`hold` 대 `hire`)을 손으로 써 둔 것이다.

**기대 판정 `expected` 표기.** 세 갈래 모두 선택적이고 **허용 값의 목록**으로 적는다(단일 정답이 아니라 허용 집합).

| 갈래 | 모양 | 비교 대상 |
|---|---|---|
| `stopSignals` | map<신호 이름, list<허용 값>> | 응답 `metadata.compareStopSignals[이름]`(llm-evaluation R-23 병합 결과) |
| `pairSignals` | map<쌍 종류, list<허용 값>> | 응답 `metadata.compareJudgements` 중 그 `pairType`인 판정들의 `pairSignal` |
| `conflictSignals` | list<충돌 신호 이름> | 응답 `metadata.compareInsights.conflictSignals` |

사용된 값(C-03에서 각 케이스의 정확한 목록): `stopSignals`는 `targetVsBaseline`, `overfitRisk`, `stopRecommendation`; `pairSignals`는 `targetBaseline`, `targetReference`, `referenceBaseline`, `targetReplica`; 충돌 신호는 `improvementNotSupportedOnReference`, `regressionOutweighsCosmeticGains`, `improvementUnstableAcrossReplicas`.

| 케이스 id | 시나리오 의도(한 줄) | 기대 항목 수 |
|---|---|---|
| `live-basic-system-boundary-control` | "JSON만 출력" 경계 규칙을 강화한 프롬프트가 실제 모델 출력에서 이득으로 보이는가. 사용자 입력이 "먼저 설명하라"고 시켜 경계를 시험 | 없음(탐색) |
| `synthetic-medical-latent-trigger-overfit` | 현재 샘플 문구에만 맞춘 하드코딩 규칙을 이득으로 오판하지 않는가 | 5 |
| `synthetic-ecommerce-schema-no-model-worship` | teacher 출력이 더 유려해도 스키마·래퍼 변경을 회귀로 보는가 | 6 |
| `synthetic-legal-flat-not-unclear` | 표현만 바뀌고 결론이 같으면 `flat`으로 보는가(`unclear`로 물러나지 않는가) | 3 |
| `synthetic-teaching-overfit-regression` | 문제 하나에 맞춘 암기 문구로 일반 원리를 잃은 회귀를 잡는가 | 6 |
| `synthetic-hiring-replica-semantic-instability` | 같은 프롬프트 재실행에서 결론이 갈리는 **대상 출력**의 불안정을 `unstable`로 보는가 | 4 |

**재작성 단계의 데이터.** 평가 응답은 그대로 재작성 함수의 `result`가 되고, `type:'compare'`, `mode`는 케이스의 값, `language:'zh'` 고정, `workspacePrompt`/`referencePrompt`는 live는 `workspacePrompt`/`previousPrompt`, 합성은 `targetWorkspacePrompt`/`targetPreviousPrompt`다. live의 평가 요청에는 `target.referencePrompt`가 없는데 재작성 입력에는 `previousPrompt`가 `referencePrompt`로 들어간다(비대칭).

**결과 파일.** 위치 `docs/workspace/compare-evaluation-analysis/structured-compare-calibration/latest/`(루트 기준, 경로 고정).

| 파일 | 내용 |
|---|---|
| `summary.json`, `summary.md` | 총괄. `{generatedAt, rows[]}`와 표. 행 필드·열은 R-18 |
| `<caseId>/scenario.md` | 제목, caseId, kind, 설명, focus |
| `<caseId>/request.json`, `request.md` | 평가 요청 객체(markdown은 json 코드펜스) |
| `<caseId>/response.json`, `response.md` | 평가 응답 전체(`EvaluationResponse`) |
| `<caseId>/pair-judge-payloads.json` | `[{phase, payload}]`. 판정 호출의 user 메시지에서 마커 `Pair Judge Evidence Payload (JSON):` 뒤를 `JSON.parse`한 것. 파싱 실패 항목은 조용히 빠진다 |
| `<caseId>/synthesis-payload.json` | 합성 user 메시지에서 마커 `Synthesis Payload (JSON):` 뒤를 파싱한 값, 없으면 `null` |
| `<caseId>/rewrite-payload.json` | `buildRewritePayload` 결과(재작성 입력문 속 payload와 같은 함수) |
| `<caseId>/rewrite-input.txt`, `rewrite-output.txt` | 모델에 보낸 재작성 입력문, 모델 응답(trim) |
| `<caseId>/llm-calls.json`, `llm-calls.md` | 그 케이스의 모든 LLM 호출: `{phase, modelKey, attempts[], messages[{role,content}], response 또는 error, retryCount}` |
| `<caseId>/summary.json`, `summary.md` | 케이스 요약 + 기대 대조 표 + 재작성 출력(R-17) |
| `<caseId>/executions.json` | live 케이스만: 실행 4개의 스냅샷 객체 |

### 1.4 행동 규칙과 남은 질문 [필수]

**가. 실행·환경·모델**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 실행 명령과 인자 | 스크립트 `compare:calibrate`는 코어를 빌드한 뒤 `.mjs`를 실행한다. `.mjs`는 `packages/core/dist/index.js`를 정적 import하므로 dist가 없으면 아무 케이스도 돌지 못한다. `process.argv`·`process.env`를 직접 읽는 코드가 없어 외부에서 바꿀 수 있는 입력은 `.env.local`(과 그것이 영향을 주는 셸 환경)뿐이다. | 코드 확인 |
| R-02 | `.env.local` 로드 | `dotenv.config({path: <루트>/.env.local})`를 모듈 최상위에서 실행한다(ESM이라 코어 import가 먼저 평가되지만, 코어는 환경변수를 `ModelManager` 초기화 시점의 `getEnvVar`로 읽으므로 로드 뒤에 반영된다). 셸에 이미 있는 변수를 `.env.local`이 덮어쓰는지는 dotenv의 기본 동작(덮어쓰지 않음)에 따른다고 추론한다. 파일이 없어도 이 줄은 오류를 내지 않고, 이후 R-04 모델 활성 검사에서 실패한다. | 코드 확인(순서) / dotenv 동작은 추론 |
| R-03 | 모델 고정 | 케이스가 가리키는 모델 key는 `custom`·`deepseek` 두 가지뿐이다. `createServices`는 두 모델이 `getModel(...).enabled`인지 확인하고, 하나라도 아니면 중국어 오류 메시지("모델 미활성, `.env.local` 확인")를 던져 케이스를 시작하기 전에 종료한다(종료 코드 1). 두 모델 모두 `paramOverrides`에 기존 값을 유지한 채 `temperature: 0.2`, `timeout: 180000`을 덮어쓰고 표시 이름을 "Calibration" 접미 문구로 바꾼다. `custom`의 실제 모델 ID·엔드포인트는 `.env.local`에 달려 있어 저장소에서 알 수 없다(표시 이름의 "SiliconFlow Qwen3-32B"는 고정 문자열이다). 합성 케이스만 돌려도 `custom` 활성 검사는 통과해야 한다. | 코드 확인 |
| R-04 | 서비스 조립 | `MemoryStorageProvider` 하나를 `PreferenceService` → `TemplateLanguageService`(`initialize` 후 `setLanguage('zh-CN')`) → `TemplateManager`, `ModelManager`에 공유한다. `LLMService`를 만들고 R-05 래퍼로 감싼 것을 `EvaluationService`에 넣는다. 언어가 `zh-CN`이라 구조화 비교의 판정·합성 프롬프트는 중국어 판이 쓰이고(llm-evaluation R-20) 재작성도 `'zh'`로 호출된다(R-14). 서비스 인스턴스는 모든 케이스가 공유한다. | 코드 확인 |
| R-05 | LLM 호출 래퍼 | `sendMessage(messages, modelKey)`만 감싼다: 호출을 기록하고(R-06) 재시도한다. 최대 3회 시도. 재시도 대상은 오류 메시지에 `Socket timeout`, `ERR_SOCKET_TIMEOUT`, `ETIMEDOUT`, `ECONNRESET`, `429`, `502`, `503` 중 하나가 부분 문자열로 들어 있는 경우뿐이고, 대기는 `시도번호 × 3000ms`(3초, 6초)다. 재시도 대상이 아니거나 3번째도 실패하면 오류를 그대로 던진다(기록에는 `attempts`·`error`·`retryCount`가 남는다). **평가 서비스의 판정·합성 호출도 이 래퍼를 지나므로 같은 재시도를 받는다**(llm-evaluation R-22는 서비스 자체에는 재시도가 없다고 했으나, 이 스크립트에서는 래퍼가 더한다). 응답 문자열이 왔지만 파싱에 실패하는 경우는 재시도하지 않는다. `sendMessageStream`은 감싸지 않고 통과시키며 기록하지 않는다(스크립트는 쓰지 않음). OpenAI SDK 어댑터는 자체적으로도 비스트림 `maxRetries: 3`을 설정하므로 이 재시도는 그 위에 더해진다. | 코드 확인 |
| R-06 | 호출 기록과 단계 이름 | 호출마다 `{phase, modelKey, attempts, messages, response/error, retryCount}`를 케이스 단위 배열에 **완료 순서대로** 넣는다. 단계 이름: 첫 system 메시지에 `Structured_Compare_Pair_Judge` 또는 `结构化对比成对判断专家`가 있으면 `pair-judge:<pairKey>`(키는 user 메시지의 `Pair Key:` 줄 또는 JSON의 `"pairKey"`, 없으면 `unknown`), `structured compare synthesizer` 또는 `结构化对比综合专家`가 있으면 `structured-compare-synthesis`, 그 밖에는 호출자가 `withPhase`로 지정한 현재 이름(`execute:<caseId>:<snapshotId>`, `evaluate:<caseId>`, `rewrite:<caseId>`). 판정이 병렬이라 기록의 판정 순서는 판정 계획 순서와 다를 수 있다(커밋된 live 로그에서 `target-vs-reference`가 먼저 기록됨). 이 문자열 판별은 평가 템플릿의 역할 문구에 의존한다(템플릿 문구가 바뀌면 이름이 `idle` 또는 현재 단계로 떨어지고 payload 추출이 비게 된다). | 코드 확인(커밋된 live 호출 로그 열람으로 순서·단계 이름 일치 확인) |

**나. 케이스와 단계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 케이스 목록·순서 | `[LIVE_BASIC_SYSTEM_CASE, ...SYNTHETIC_CASES]` 순서로 직렬 처리한다(live, medical, ecommerce, legal, teaching, hiring). 케이스마다 시작 전에 호출 기록 배열을 비운다. 케이스 선택·건너뛰기·병렬 실행이 없다. 어떤 케이스든 `kind`가 `'live'`면 R-12 경로, 아니면 합성 경로다. | 코드 확인 |
| R-08 | live 케이스의 정의 | 프롬프트 두 개와 사용자 입력 하나로 4개 실행을 정의한다(1.3). 사용자 입력이 시스템 프롬프트의 "JSON만 출력" 규칙과 충돌하는 요청("먼저 설명한 뒤 결과")을 담도록 설계됐다. `expected`가 없어 대조 항목이 0개이고 요약에는 `exploratory`로 나온다. | 코드 확인 |
| R-09 | 합성 케이스의 정의 | 스냅샷·테스트 케이스·`compareHints`·`expected`를 모두 소스에 박은 정적 입력이다. 스크립트는 이 값을 그대로 평가 요청에 넣는다(실행 호출 없음). 따라서 합성 케이스에서 측정되는 것은 "평가기가 이 고정 증거를 어떻게 판정하는가"뿐이고, 증거(출력)는 시나리오 작성자가 정한 것이다. | 코드 확인 |
| R-10 | 기대 판정의 표현 | 1.3의 `expected` 세 갈래. 허용 목록에 여러 값을 두어 "이 중 하나면 합격"을 표현한다(예: `targetBaseline`에 `flat`/`improved`). 부정 조건("이 값이면 안 됨"), 점수 범위, 응답 문구, 재작성 출력에 대한 기대는 표현할 수 없고 `score.overall`은 어떤 케이스에서도 단정하지 않는다. | 코드 확인 |
| R-11 | 케이스 입력의 비결정 요소 | 합성 케이스의 평가 입력은 고정이므로 두 번 실행해도 같은 요청이 간다. live 케이스는 실행 4개가 모델 출력에 따라 달라진다. 평가·재작성 호출은 temperature 0.2이지만 같은 입력이 같은 출력을 낸다는 보장은 코드 어디에도 없다. | 코드 확인 |
| R-12 | live 스냅샷 실행 | 순서 a→b→c→d로 **직렬** 4회 `sendMessage([system=프롬프트, user=사용자 입력], 모델)`을 보낸다(a: 현재 프롬프트·`targetModelKey`, b: 이전 프롬프트·target, c: 현재·`teacherModelKey`, d: 이전·teacher). 응답은 `trim`해서 스냅샷 `output`에 넣고, `promptRef`는 a·c가 `workspace`, b·d가 `version 1`이다. 각 스냅샷은 `testCaseId:'tc-1'`, `modelKey`, `versionLabel`을 가진다. 실행이 빈 문자열을 돌려주면 다음 평가의 요청 검증(스냅샷 `output` 비어 있음 불가, llm-evaluation R-04)에서 실패해 실행이 중단된다. 4개 스냅샷은 `executions.json`으로도 저장된다. | 코드 확인 |
| R-13 | 평가 요청과 호출 | 요청: `type:'compare'`, `evaluationModelKey`=케이스의 `evaluatorModelKey`, `mode`, `focus{content, source:'system', priority:'highest'}`, `target{workspacePrompt}`(합성은 `referencePrompt`도), `testCases`(1개), `snapshots`, `compareHints`. `evaluate`를 한 번(비스트림) 호출한다. 힌트의 역할 배정이 판정 계획 조건을 만족하므로 구조화 비교 경로가 돈다(llm-evaluation R-18, R-19). 이 호출은 `evaluate:<caseId>` 단계 안에서 일어난다. 평가 오류(검증·파싱·호출 실패)는 R-16으로 전파된다. | 코드 확인 |
| R-14 | 재작성 입력문 생성과 호출 | `buildRewritePayload`(→ `rewrite-payload.json`)와 `buildRewritePromptFromEvaluation`(→ 입력문)을 같은 인자로 **각각** 호출한다. 인자: `result`=평가 응답, `type:'compare'`, `mode`, `language:'zh'`, 워크스페이스·참조 프롬프트(1.3). 입력문 문자열을 **단일 user 메시지 1개**(`[{role:'user', content: 입력문}]`)로 `sendMessage(…, rewriteModelKey)` 한 번에 보낸다. 반복(`iterate`) 템플릿도 system 메시지도 감싸지 않는다. `rewriteGuidance`가 `skip`이어도 호출하며(가드 없음), 응답은 `trim`해서 저장하고 내용을 검증하지 않는다(워크스페이스 프롬프트와 같은지, 형식이 맞는지 확인하는 코드 없음). | 코드 확인 |
| R-15 | UI 재작성 경로와의 차이(iterate-rewrite R-28·R-31과 대조) | UI는 같은 입력문을 반복 템플릿 `iterate`의 `iterateInput` JSON 문자열 필드 안에 넣고 `lastOptimizedPrompt`를 따로 실어 `[system, user]` 두 메시지로 최적화 모델에 보내므로 대상 프롬프트가 두 번 실리고 "요구사항을 녹여 넣어 고쳐 쓰라"는 지시가 먼저 작동한다. 이 스크립트는 입력문만 단일 user 메시지로 보내 재작성 템플릿의 "프롬프트 본문만 출력, `skip`이면 원문 그대로" 지시가 **단독 지시**가 된다. 따라서 스크립트의 재작성 출력은 UI가 만드는 결과의 재현이 아니라 재작성 템플릿 단독 효과를 보는 것이다. 또한 UI는 `compare`의 `skip` 권고에서 호출 자체를 막지만(iterate-rewrite R-26 ④) 스크립트는 막지 않는다. 사용 모델도 다르다(UI: 최적화 모델, 스크립트: 케이스의 `rewriteModelKey`=deepseek). 어느 쪽이 모델 응답에서 더 잘 지켜지는지는 확인하지 못했다. | 코드 확인(호출 모양) / 모델 반응은 미확인 |

**다. 결과 기록·오류**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | 시작과 오류 | `main`은 먼저 `latest/` 폴더를 `rm -r -f`로 지우고 다시 만든다. **이전 실행 기록(커밋된 파일 포함)은 새 실행이 시작되면 즉시 사라진다.** 케이스 루프에는 개별 예외 처리가 없어 첫 오류(평가·재작성 호출 실패, 모델 비활성, 파싱 실패 등)에서 루프가 끝나고 `console.error`와 종료 코드 1이 된다. 이때 앞서 끝난 케이스의 폴더는 남고, 총괄 `summary.json`·`summary.md`는 쓰이지 않는다. 케이스 폴더는 평가가 성공한 뒤 만들어지고, 재작성 호출이 실패하면 빈 폴더만 남는다(폴더 생성 → 재작성 호출 → 파일 쓰기 순서). 부분 재개 기능은 없다. 기대 불일치는 오류가 아니다(R-20). | 코드 확인 |
| R-17 | 케이스 파일 | 재작성 호출 후 호출 로그에서 payload를 추출해(R-06의 마커) 1.3 표의 파일들을 `latest/<caseId>/`에 쓴다. 케이스 `summary.json`: `{generatedAt, case{id,title,kind}, summary, expectationResults}`. `summary`는 `{compareMode, summary(응답 한 문장), score(=score.overall 또는 null), improvements, stopSignals(=compareStopSignals), conflictSignals, pairJudgements[{pairType, pairSignal, verdict, confidence}], expected}`. `expectationResults`는 R-19의 항목 배열. 케이스 `summary.md`: 설명, 위 `summary`의 JSON 코드블록, 기대 대조 표(`| 유형 | 키 | 기대 | 실제 | 적중 |`, 항목이 없으면 "사전 단정 없음, 탐색용 샘플" 문구), 재작성 출력. 코드가 추출하는 `rewritePayloadFromMessage`(재작성 호출 메시지에서 읽은 payload)는 계산만 하고 파일로 쓰지 않는다. `generatedAt`은 모듈 로드 시각 하나를 모든 파일이 공유한다. | 코드 확인 |
| R-18 | 총괄 요약 | 모든 케이스가 끝난 뒤에만 쓴다. `summary.json` = `{generatedAt, rows[]}`, 행 = `{caseId, title, kind, score, stopRecommendation, targetVsBaseline, targetVsReferenceGap, expectationMatched, expectationTotal}`(값이 없으면 `null`; 기대가 없는 케이스는 `expectationMatched`·`expectationTotal`이 `null`). `summary.md`는 `generatedAt`, 출력 루트의 **절대 경로**(실행 환경 경로가 박혀 커밋된 기록에는 작성자의 Windows 경로가 있다), 열 `Case/Kind/Score/targetVsBaseline/targetVsReferenceGap/stopRecommendation/Expectation Match`(적중은 `n/m` 또는 `exploratory`)의 표와 고정 설명 문장 3개를 담는다. 모델 key·모델 ID·temperature·시도 횟수는 요약에 넣지 않는다(호출 로그에는 `modelKey`만 있다). | 코드 확인 |

**라. 판정 안정성: 무엇을 재고 무엇을 통과/실패로 말하는가**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | 기대 대조 계산 | `stopSignals`: 각 이름에 대해 `actual = compareStopSignals[이름]`, 값이 있고 허용 목록에 포함되면 `matched`(값이 없으면 항상 불일치, `actual`은 `null`로 기록). `pairSignals`: 쌍 종류마다 응답의 판정 중 그 `pairType`인 것들의 `pairSignal` 배열을 만들고, **하나라도** 허용 목록에 있으면 `matched`(replica 쌍이 여러 개여도 하나만 맞으면 적중, 판정이 없으면 불일치). `conflictSignals`: 기대 신호마다 응답의 충돌 신호 배열에 **포함**되면 `matched`(기대하지 않은 신호가 더 있어도 감점이 없다). 결과는 항목마다 `{type, key, expected, actual, matched}` 하나. 케이스 점수·가중치·"전부 적중해야 통과" 같은 합산 판정이 없고, 총괄은 적중 개수와 전체 개수만 센다. | 코드 확인 |
| R-20 | **통과/실패 기준** | **없다.** 임계값(예: "n/m 이상이면 통과")·종료 코드·경고·테스트 프레임워크 어설션이 코드에 없다. 불일치가 몇 개든 실행은 정상 종료(코드 0)이고, 종료 코드 1은 예외로 중단된 경우뿐이다(R-16). 적중 수를 읽고 판단하는 것은 사람이며, 불일치는 "프롬프트를 고칠지 케이스를 고칠지" 사람이 정하는 단서로 쓰인다(문서의 사용 지침, C-12). 같은 이유로 CI·`test:*` 스크립트에 연결돼 있지 않다(루트 `package.json`에서 `compare:calibrate`는 독립 스크립트이고 `test:gate` 등이 부르지 않는다). | 코드 확인 |
| R-21 | **안정성 측정 여부** | 이 스크립트는 심판의 안정성을 측정하지 않는다. (a) **반복**: 케이스당 평가 1회, 반복 횟수 설정·루프·분산/일치율 계산이 없다. (b) **순서 교대**: 구조화 판정의 left/right는 쌍 종류로 고정이고(llm-evaluation R-09) 스크립트도 스냅샷 순서를 바꿔 다시 평가하지 않는다. (c) **모델 교체**: 평가 모델은 6개 케이스 모두 `deepseek` 하나이고 교차 심판·다중 심판 비교 코드가 없다. 모델을 바꾸려면 소스 상수를 고쳐 다시 돌려야 하고, 결과를 비교하는 기능은 없다. (d) **독립성**: live 케이스에서 teacher 스냅샷(c, d)의 생성 모델, 평가 모델, 재작성 모델이 모두 `deepseek`이다(심판이 자기 출력을 채점하는 구성이고 llm-evaluation R-07대로 이를 막거나 표시하지 않는다). (e) **수치 점수**: `score.overall`은 요약 표에 찍히지만 어떤 단정에도 쓰이지 않는다. 안정성과 관련된 장치는 `temperature 0.2` 하나뿐이고, 허용 값 목록(R-10)은 "정답이 여럿일 수 있다"는 설계 시점의 사전 관용이지 실측한 변동 폭이 아니다. 혼동하기 쉬운 점: `targetReplica`/`stability` 신호와 hiring 케이스의 "semantic instability"는 **평가 대상 프롬프트의 출력이 재실행마다 흔들리는지**를 심판이 판정하는 기능이고(재실행 증거는 손으로 쓴 값), 심판 자신의 재현성을 재는 것이 아니다. | 코드 확인(스크립트 전체에 반복·교대·교체 구성 없음) |
| R-22 | 기록 문서의 결론(후보로 읽음) | 보정 README(`structured-compare-calibration/README.md`)와 분석 문서(`auto-compare-rewrite-effect-analysis.md`)는 "구조화 비교가 하드 문제(스키마 이탈, 회귀, 과적합, flat/unclear 구분, replica 불안정)를 **안정적으로** 식별한다"고 쓴다. 근거는 한 번 실행한 기록(`latest/`, 2026-03-22 생성, 출력 경로가 Windows 경로)이고 반복 실행 근거는 없다. 그 기록의 대조 결과: ecommerce 6/6, legal 3/3, teaching 6/6, hiring 4/4, **medical 3/5**(불일치 2개: `targetBaseline` 기대 `flat`/`improved` ← 실제 `regressed`, 기대 충돌 `improvementNotSupportedOnReference` ← 실제 `regressionOutweighsCosmeticGains`+`sampleOverfitRiskVisible`), live는 `exploratory`. medical 불일치는 문서가 "실패"가 아니라 "평가기가 의도보다 더 보수적으로 판정한 새 발견"으로 해석했고, 이 SHA의 소스에는 **기대값이 그대로**(수정되지 않음) 남아 있어 현재 코드를 그대로 돌리면 이 불일치가 반복될 가능성이 있다(기록과 현재 코드·템플릿이 일치하는지는 확인하지 못함). 문서 간 불일치: 같은 live 케이스를 README는 `stopRecommendation=review`라 하고, 같은 폴더의 `latest/summary.md`는 `continue`로 기록한다(어느 한쪽이 다른 실행의 값일 수 있음. 한 번 실행에서의 변동인지 문서 시점 차이인지 판단 불가). `protocol-migration-minimal-plan.md`는 같은 목적으로 다른 케이스 이름(`synthetic-schema-drift-regression` 등)과 다른 점수를 적고 있어 케이스 집합이 시간에 따라 바뀌었음을 보여 준다(과거 기록과 직접 비교 불가). | 코드 확인(문서 열람) / 문서의 "안정적" 진술은 미확인(반복 근거 없음) |

- 불변식: 호출 기록 배열은 케이스마다 비워지고, 한 케이스의 평가·재작성이 끝나야 다음 케이스가 시작된다. 합성 케이스의 평가 입력은 실행마다 같다(R-11). 어떤 경우에도 스크립트는 소스 케이스·템플릿·코어를 수정하지 않는다(쓰는 것은 `latest/` 하나).
- 미결정: 없음. 선행 스펙 llm-evaluation과 iterate-rewrite가 모두 `ready`가 되어 이 스펙도 `ready`다.
- 확인 한계: 설치·빌드·실행·모델 호출을 하지 않았다. `dotenv`의 변수 우선순위와 `jsonrepair` 등 외부 라이브러리는 소스를 보지 않았다. `custom` 모델의 실제 모델 ID·엔드포인트는 개발자의 `.env.local`에만 있어 알 수 없고, 커밋된 기록이 만들어진 환경(Windows, 2026-03-22)과 이 SHA의 코드·템플릿이 일치하는지, 문서 간 불일치(R-22)의 원인이 무엇인지 확인하지 못했다. 이 스크립트를 대상으로 한 원본 테스트는 검색(`calibrat`)에서 찾지 못했다. 케이스 6개의 프롬프트·출력 본문(중국어)은 구조 위주로 읽었고 의미 해석은 하지 않았다.

### 1.5 필수 코드 참조 [필수]
라이선스: AGPL-3.0-only(overview 1절). 아래는 복사본이 아니라 위치다. 재구현자는 해당 범위를 읽고 직접 구현한다. 케이스 본문(프롬프트·샘플 출력)은 가져오지 않고 구조만 쓴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `scripts/run-structured-compare-calibration.mjs:1-48` import·상수·`isRetryableCalibrationError`; `package.json:43` `compare:calibrate` | 출력 루트 경로, 타임아웃·재시도 상수, 재시도 가능 오류 7개 부분 문자열, 빌드 후 실행 스크립트 | R-01, R-02, R-05 |
| C-02 | `scripts/run-structured-compare-calibration.mjs:50-87` `LIVE_BASIC_SYSTEM_CASE` | live 케이스의 필드 모양(모델 key 4개, 프롬프트 2개, 입력 1개, `expected` 없음) | R-08, R-12 |
| C-03 | `scripts/run-structured-compare-calibration.mjs:89-808` `SYNTHETIC_CASES`; 케이스별 `compareHints` `:205-216`·`:349-360`·`:489-500`·`:629-640`·`:785-797`, `expected` `:217-227`(medical)·`:361-372`(ecommerce)·`:501-509`(legal)·`:641-652`(teaching)·`:798-807`(hiring) | 합성 케이스 필드 모양, 역할 배정, 기대 판정의 정확한 허용 값 | R-09, R-10, R-22 |
| C-04 | `scripts/run-structured-compare-calibration.mjs:859-923` 마커 상수·`extractJsonAfterMarker`·`collectPromptPayloadArtifacts` | 판정·합성·재작성 payload 마커 문자열과 "마커 뒤 전부를 JSON.parse, 실패하면 null" 추출 | R-06, R-17 |
| C-05 | `scripts/run-structured-compare-calibration.mjs:925-943` `summarizeCaseResult` | 케이스 요약 필드 | R-17 |
| C-06 | `scripts/run-structured-compare-calibration.mjs:945-1014` `evaluateExpectations`, `renderExpectationMarkdown` | 기대 대조 알고리즘(포함·하나라도·값 없음=불일치)과 표 형식 | R-19, R-20 |
| C-07 | `scripts/run-structured-compare-calibration.mjs:1119-1168` `createServices` | 서비스 조립 순서, 모델 활성 검사와 오류, temperature·timeout 덮어쓰기, 이름 변경 | R-03, R-04 |
| C-08 | `scripts/run-structured-compare-calibration.mjs:1032-1117` `createLoggedLLMService` | 단계 이름 판별, 시도 루프·대기 시간, 기록 항목 모양, 스트림 통과 | R-05, R-06 |
| C-09 | `scripts/run-structured-compare-calibration.mjs:1170-1277` `runLiveCase` | live 4개 직렬 실행, 스냅샷·요청·힌트 구성 | R-12, R-13 |
| C-10 | `scripts/run-structured-compare-calibration.mjs:1279-1306` `runSyntheticCase` | 합성 평가 요청 구성(`referencePrompt` 포함) | R-09, R-13 |
| C-11 | `scripts/run-structured-compare-calibration.mjs:1312-1343` | 재작성 payload·입력문 생성, `:1341-1343` 단일 user 메시지 호출 | R-14, R-15 |
| C-12 | `scripts/run-structured-compare-calibration.mjs:1345-1412` `writeCaseArtifacts`(파일 쓰기), `:1414-1460` `writeOverallSummary`, `:1462-1488` `main` | 파일 목록·형식, 총괄 행 필드, 삭제 후 재생성, 직렬 루프, 오류 시 종료 코드 | R-07, R-16~R-18, R-20 |
| C-13 | `docs/workspace/compare-evaluation-analysis/structured-compare-calibration/README.md:33-43`, `:69-75` | 최신 결론 문구와 "불일치 시 무엇을 고칠지" 사용 지침(문서, 후보) | R-20, R-22 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 모델 호출을 대체물로 바꾼 사례는 없다(모델 호출이 필요한 사례는 응답 값을 가정한 입력으로 계산 규칙만 검증한다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `.env.local`에 `VITE_DEEPSEEK_API_KEY`만 있고 `VITE_CUSTOM_API_*`가 모두 비어 있다 | 케이스를 시작하기 전에 `custom` 미활성 오류로 종료(코드 1). 합성 케이스만 쓰려 해도 마찬가지 |
| T-02 | R-19 | 기대 `stopSignals: {overfitRisk: ['high']}`, 응답의 `compareStopSignals`에 `overfitRisk`가 없음 | 항목 `{type:'stopSignal', key:'overfitRisk', actual:null, matched:false}` |
| T-03 | R-19 | 기대 `pairSignals.targetReplica: ['unstable']`, replica 판정 두 개의 `pairSignal`이 `stable`, `unstable` | `matched: true`(하나라도 허용 목록에 있음). 둘 다 `stable`이면 `false`. `targetReplica` 판정이 없으면 `false` |
| T-04 | R-19 | 기대 충돌 `['regressionOutweighsCosmeticGains']`, 응답 충돌 신호 `['regressionOutweighsCosmeticGains','sampleOverfitRiskVisible']` | `matched: true`(추가 신호는 불이익 없음) |
| T-05 | R-05 | 판정 호출이 첫 시도에서 메시지에 `429`가 든 오류, 두 번째 시도 성공 | 3초 대기 후 재시도, 기록 `retryCount: 1`, `attempts` 1개. 메시지가 `401 Unauthorized`였다면 재시도 없이 즉시 던져 케이스(전체 실행)가 중단 |
| T-06 | R-05 | 3번 연속 `503` | 3초, 6초 대기 후 3번째 실패에서 오류를 던진다(대기는 마지막 실패 뒤에는 없음) |
| T-07 | R-14, R-15 | 어떤 케이스의 평가가 끝남 | 재작성 호출의 메시지 배열이 정확히 1개(`role:'user'`)이고 system 메시지·반복 템플릿 문구가 없다. 평가 응답이 `skip` 권고여도 호출은 일어난다 |
| T-08 | R-20, R-16 | 모든 합성 케이스에서 기대 항목이 하나도 맞지 않지만 예외는 없음 | 총괄 요약이 각 케이스 `0/n`으로 기록되고 프로세스는 종료 코드 0 |
| T-09 | R-16 | 세 번째 케이스의 평가 호출에서 예외 | 앞 두 케이스 폴더만 `latest/`에 남고(이전 실행 기록은 이미 삭제됨), `summary.json`·`summary.md`는 없으며 종료 코드 1 |
| T-10 | R-16 | 케이스의 평가는 성공했는데 재작성 호출이 실패 | 그 케이스 폴더는 생성되었으나 비어 있고(파일 쓰기가 재작성 호출 뒤) 실행은 종료 코드 1로 중단 |
| T-11 | R-12 | live 실행 a가 공백만 돌려줌 | 평가 요청 검증이 `output` 비어 있음으로 거절해 실행 중단. 다른 스냅샷 출력은 `executions.json`에도 남지 않는다(케이스 파일은 평가 성공 후에만 쓴다) |
| T-12 | R-01 | `pnpm compare:calibrate`를 인자(`-- --case=live`)와 함께 실행 | 인자는 무시되고 6개 케이스 전부 실행 |
| T-13 | R-06, R-17 | hiring 케이스 한 번 실행 | `llm-calls.json`에 판정 4개(target-vs-baseline, target-vs-reference, reference-vs-reference-baseline, target-vs-replica), 합성 1개, 재작성 1개가 있고 판정 4개의 순서는 완료 순서 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
경로는 모두 `repos/prompt-optimizer@a201f47` 기준이다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 (`package.json:43`), `scripts/run-structured-compare-calibration.mjs:1-15`(import), 파일 전체의 `process.` 검색 결과 `:1487`(exitCode)뿐 | 코드 읽기. `argv`/`process.env` 미사용은 문자열 검색으로 확인 |
| R-02 | `:4`·`:27`, `packages/core/src/utils/environment.ts` `getEnvVar`(process.env → import.meta.env → 기본값), `packages/core/src/services/model/defaults.ts:127-131` | `dotenv` 소스 미열람(우선순위는 추론). `.npmrc`의 `shamefully-hoist=true`와 `packages/core/package.json`의 dotenv 의존으로 루트 해석 가능성을 추론(설치 안 함) |
| R-03 | C-07; `defaults.ts:17`(deepseek 환경변수), `:96-117`(모델별 활성 조건), `:126-178`(custom: 4개 변수 중 하나, 기본 baseURL·모델 ID); `deepseek-adapter.ts:22-48`(정적 모델 목록·`thinking_type: disabled` 기본), `:303-330`; `openai-adapter.ts:856-870`(timeout·`maxRetries`), `:946-961`(`paramOverrides` 확장 → 요청) | temperature가 chat completions 요청에 실리는 경로를 읽음. `custom`이 쓰는 어댑터(`openai-compatible`)가 이 경로를 그대로 쓰는지는 개요의 "12개가 OpenAIAdapter 상속" 진술에 의존 |
| R-04 | C-07 `:1119-1168` | 코드 읽기. 평가 서비스가 `getCurrentBuiltinTemplateLanguage`를 `zh-CN`에서 중국어로 해석하는 것은 llm-evaluation R-20 |
| R-05 | C-08 `:1032-1117`(특히 `:1058-1114`), `:1160`(래퍼가 평가 서비스에 주입됨) | 코드 읽기. llm-evaluation R-22와의 차이는 래퍼가 서비스 밖에서 재시도를 더하기 때문 |
| R-06 | C-08 `:1036-1056`; 템플릿 역할 문구 `evaluation-structured-compare/content.ts:16`·`:44`·`:117`·`:139`; 마커 문구 `:81`·`:92`·`:151`·`:162`; 커밋된 `latest/live-basic-system-boundary-control/llm-calls.json`(9개 호출, 단계 이름·완료 순서) | 문자열 일치와 커밋된 로그로 확인(원작성자 기록 열람) |
| R-07 | C-12 `:1462-1483` | 코드 읽기 |
| R-08, R-09 | C-02, C-03, C-10 | 구조는 필드 이름 검색과 케이스 전체 훑기로 확인. 본문 의미 해석은 하지 않음 |
| R-10 | C-06 `:945-997`, C-03의 `expected` 블록 | 코드 읽기 |
| R-11 | C-09, C-10; `:1170-1277` | 추론 일부(출력 동일 보장 부재는 코드에 해당 장치가 없다는 부정 근거) |
| R-12, R-13 | C-09 `:1170-1277`; llm-evaluation R-04(빈 출력 검증), R-18~R-19; 커밋된 `executions.json`(모델 4개 출력 모양) | 코드 읽기 |
| R-14 | C-11 `:1312-1343`; iterate-rewrite R-20·R-21 | 코드 읽기 |
| R-15 | C-11 `:1341-1343`; iterate-rewrite R-26 ④, R-27, R-28, R-31 | 두 호출 경로를 선행 스펙과 대조. 모델 반응은 미확인 |
| R-16 | C-12 `:1462-1488`, `:1308-1312`(폴더 생성), `:1341-1343`, `:1350-1381`; `git ls-files`로 `latest/` 87개 추적 확인 | 코드 읽기 |
| R-17, R-18 | C-12 `:1350-1460`, C-05, C-04(`:859-923`; `rewritePayloadFromMessage`는 `:921`에서 반환만 되고 `:1346` 이후 쓰이지 않음); 커밋된 `latest/summary.md`(Windows 절대 경로) | 파일 목록은 코드와 커밋된 폴더 목록(live 15개·합성 14개)이 일치 |
| R-19, R-20 | C-06 `:945-997`, C-12 `:1414-1460`, `:1485-1488`; 루트 `package.json:29-48`(`test*` 스크립트가 `compare:calibrate`를 부르지 않음), `scripts/*.test.mjs`·`packages/*/tests`에서 `calibrat` 검색 결과 없음 | 정의 부재는 코드 전체 읽기와 키워드 검색에 근거(추론 성격) |
| R-21 | 스크립트 전체(루프·교체·교대 구성 없음), `:1140-1156`(temperature), `evaluatorModelKey` 값 6개(C-02, C-03), llm-evaluation R-07·R-09 | 부재 판정은 전체 읽기(1488줄)와 `for`/`argv`/`swap`류 구성 검색에 근거 |
| R-22 | `docs/workspace/compare-evaluation-analysis/structured-compare-calibration/README.md:33-43`(결론), `auto-compare-rewrite-effect-analysis.md:21-52`(요약·적중 수)·`:217-240`(medical), `latest/summary.md`·`latest/summary.json`·`latest/<case>/summary.json`(`expectationResults`), `protocol-migration-minimal-plan.md:10-20` | 문서는 후보로 읽고 커밋된 `summary.json`의 `expectationResults`로 수치 확인. 문서 간 live 값 불일치는 원인 미확인 |
| T-01~T-13 | 각 R-ID의 근거와 같음 | 모두 구현에서 도출한 기대값이고 실행해 보지 않았다 |

문서와 구현이 다른 점(구현을 사실로 썼다): ① 보정 README와 분석 문서는 구조화 비교를 "안정적으로 식별한다"고 쓰지만 스크립트는 케이스당 1회 실행만 하며 반복·교대·모델 교체 측정이 없다(R-21, R-22). ② README는 live 케이스의 `stopRecommendation`을 `review`로 쓰고 같은 폴더의 `latest/summary.md`는 `continue`로 기록한다. ③ README의 "재시도 내장"은 코드의 일시 오류 7종·3회 재시도와 맞는다(일치). ④ 프로토콜 문서가 적은 이전 케이스 이름·점수는 현재 케이스 집합과 다르다.

### 2.2 코드 읽는 순서 [선택]
`main`(C-12 `:1462`) → `createServices`(C-07) → `createLoggedLLMService`(C-08) → `runLiveCase`/`runSyntheticCase`(C-09, C-10) → `writeCaseArtifacts`(C-11, C-12) → `evaluateExpectations`(C-06) → 케이스 데이터(C-02, C-03)는 마지막에 필요한 부분만 본다. 1488줄 중 약 720줄(`:89-808`)이 합성 케이스 데이터이고 나머지 약 770줄이 로직·헬퍼다. 스크립트 안에는 한 번 쓰고 버리는 구성(전역 `nowIso`, 직렬 루프, 단일 래퍼 객체)만 있고 함수 간 추상화는 얕다.

### 2.3 비교·재사용 출처 [선택]
- 같은 기능을 다른 레포에서 스펙화한 것은 없다. 코드를 복사하지 않았다.
- 선행 스펙과의 관계: 평가 호출의 입출력은 [llm-evaluation](./llm-evaluation.md), 재작성 입력문은 [iterate-rewrite](./iterate-rewrite.md)(특히 R-28, R-30의 "가장 가까운 자동 연결은 이 스크립트" 진술, C-24)와 같은 호출을 가리킨다.

## 적용 메모 [선택]

**판정: 심판 점수 안정성을 측정하는 일반 방법을 담고 있지 않다. 구조화 비교 한 기능의 프롬프트·신호 경계를 한 번 눈으로 점검하는 개발용 회귀 확인 도구에 가깝다.** 근거는 R-20(통과/실패 기준 없음), R-21(반복·순서 교대·모델 교체·평가자 독립성 측정 없음), R-22(문서의 "안정적"이 1회 실행 기록). 사용자의 목적("여러 모델에 평가하고 모델 적합도를 기록할 때 심판 점수의 흔들림을 측정·보정")에는 이 스크립트가 해법을 주지 않으므로 흔들림 측정 방법은 따로 설계해야 한다. 가져갈 수 있는 부분과 새로 만들어야 할 부분은 다음과 같다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-10, R-19 | (가져옴) 케이스에 "허용 값 목록"으로 기대를 적고, 수치 점수보다 범주형 신호(예: improved/flat/regressed)의 적중으로 점검한다. 매칭 규칙(하나라도 포함, 추가 신호 무시)은 목적에 맞게 엄격하게 바꾼다(예: 금지 값, 전부 일치) | 범주형 신호는 점수보다 반복 간 비교가 쉽다. 단 이 스크립트는 그 안정성을 실측하지 않았으므로 "범주형이 더 안정하다"는 가정은 우리가 검증해야 한다(추론) | 기대 표기에 `forbidden`·`mustAll` 추가 가능. 새 사례: 같은 응답에 대해 허용 목록 적중/미적중 계산 |
| R-21 | (추가) 같은 케이스를 N회 반복해 신호별 일치율·점수 표준편차를 계산한다 | 원본에 없음. 흔들림의 크기를 알아야 허용 범위를 정할 수 있다 | 인터페이스: 실행 옵션 `repeat`, 출력: 케이스×신호 분포. 신호 분포가 한 값에 몰리는 정도(일치율)로 "안정" 기준을 정해야 한다(임계값은 우리가 정함, 원본 미결정 아님) |
| R-21 | (추가) 비교형 평가에서 좌우(스냅샷) 순서를 바꿔 다시 평가하고 판정이 뒤집히는 비율을 센다 | 원본은 left/right를 고정(llm-evaluation R-09)하고 교대하지 않는다 | 흐름: 같은 쌍을 2회(원순서·교대) 평가 후 `targetBaseline` 방향 일치 여부 비교 |
| R-21 | (추가) 평가 모델을 바꿔 같은 케이스를 돌리고 모델 간 일치도를 센다. 평가 대상 모델과 평가 모델을 분리하거나 같으면 표시한다 | 원본은 평가 모델 1개 고정이고 자기 채점을 막지 않는다(R-21(d), llm-evaluation R-07) | 케이스에 `evaluatorModelKeys[]`, 출력에 `selfJudged` 표식 |
| R-20 | (추가) 통과/실패를 정의한다: 케이스별 적중 기준과 전체 합격선, 종료 코드, CI 연결 | 원본은 사람이 n/m을 읽는다 | 종료 코드 규칙과 임계값은 우리 결정 |
| R-05, R-03 | (가져옴) 호출 기록 래퍼(단계 이름·attempts)와 낮은 temperature·긴 timeout·일시 오류 재시도 | 비용·장애 분석과 재현에 유용. 단 재시도가 평가 서비스 밖에서 일어나는 점을 감안해 "재시도 횟수"를 요약에 남긴다(원본은 요약에 없음) | 요약 행에 `retryCount` 합계 추가 |
| R-12, R-09 | (바꿈) 합성 증거(손으로 쓴 출력)와 실모델 출력을 케이스 종류로 구분해 안정성은 실모델 출력으로도 측정한다 | 원본 합성 케이스는 평가기만 시험하고 대상 모델 변동을 시험하지 않는다. 우리 목적은 모델 적합도라 대상 모델 변동까지 필요하다 | 케이스 종류별 반복 단위 정의 필요: 평가만 반복 / 실행+평가 반복 |
| R-14, R-15 | (제외) 재작성 단계와 재작성 단독 호출은 우리 모델 적합도 기록에 필요 없으면 뺀다 | 심판 안정성과 무관 | 재작성 호출·출력 파일 생략 |
| R-16 | (바꿈) 시작 시 이전 결과를 지우지 않고 실행 ID별 폴더에 쌓는다 | 원본은 `latest/`를 삭제해 커밋된 기록이 사라지고, 반복 실행 비교에도 부적합하다 | 출력: `runs/<timestamp>/…` |
