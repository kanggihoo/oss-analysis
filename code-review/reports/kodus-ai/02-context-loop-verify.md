# kodus-ai — 문맥 확보(Q3)·Agent Loop(Q4)·검증(Q5)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q3, Q4, Q5 (+ evals, 샌드박스/E2B/Morph/임베딩 사용 여부)
- 검증 수준 요약(검증 열이 있는 표의 행을 스크립트로 센 값, 2026-10-13 재집계. 복수 표기 행은 각 수준에 중복 계산하고 검증 열이 없는 표·본문 서술은 제외): 코드 확인 27 / 실행 확인 0 / 추론 4 / 미확인 1
- 실행 여부: **정적 추적만**. 아래 "실행 예"는 실행하지 않았다.
- 줄 번호 재대조(2026-10-13): 문서 안 `path:range` 약 198개를 모두 열어 범위와 식별자를 확인했고(그중 약 70개는 서술 내용까지 대조) 어긋난 인용 1건과 서술 오류 4건을 고쳤다. 조사 에이전트가 연 파일을 작성자가 다시 열어 정정 항목을 확인했다. **본문 전체를 읽지 못한 긴 범위**: `agent-tools.factory.ts:300-1757`(도구별 시작 줄만), `agent-review.stage.ts:992-1508`, `commentManager.service.ts:290-640`, `ai-sdk-agent-runner.ts:245-375`, `kody-rules-sharded.judge.ts:1200-1365`, `core-agent-loop.adapter.ts:57-244`, `base-code-review-agent.provider.ts:421-505`, `validate-suggestions.stage.ts:93-272`, `implementation-verification.processor.ts:109-250`, `evals/README.md:9-51` 일부. `libs/mcp-server/mcp-adapter/client.ts`는 줄 번호 없이 파일만 인용.
- 표기: `경로`는 레포 루트 기준. 짧은 파일명은 이 문서 끝 "경로 사전"에 풀 경로가 있다. `ee` 표시는 `ee/` 경로 또는 `.ee.` 파일명.

## 0. 먼저 읽는 결론

1. **모든 LLM 호출은 `LLM.run` 한 곳을 지난다.** `loop`가 있으면 AI SDK `generateText`의 도구 호출 반복, `schema`가 있으면 구조화 1회 호출, 둘 다 없으면 텍스트 1회 호출이다(`libs/llm/llm.ts:160-236`, `libs/llm/agent-loop-call.ts:207-243`). LangChain·LiteLLM은 런타임 의존성이 아니다(`LiteLLM`은 `model-context-windows.json`의 데이터 출처로만 언급, `libs/llm/README.md:96-97`). 코드 확인.
2. **진짜 Agent Loop가 있다.** finder, 후보별 verifier, 재합성(synthesis rescue), heavy resample이 `AiSdkAgentRunner` 위에서 도구와 함께 반복한다(`libs/agent-harness/infrastructure/ai-sdk/ai-sdk-agent-runner.ts:63-404`). 코드 확인.
3. **Kody Rules 에이전트는 Agent Loop가 아니다.** 변경 파일 × 규칙을 도는 도구 없는 구조화 1회 호출의 반복이다(`libs/code-review/infrastructure/agents/providers/kody-rules-agent.provider.ts:151-163,276-283`). 코드 확인.
4. **검증 단계가 활성이다**: finder 직후 후보마다 verifier가 도구로 반증을 시도하고 반증 못 하면 유지한다(기본 KEEP). 같은 모델 슬롯·같은 프롬프트 계열이라 독립 모델은 아니다.
5. **고정 문맥이 먼저, 동적 탐색은 선택**이다. diff·PR 텍스트·커밋·이전 결정·call graph 문자열이 프롬프트에 먼저 들어가고, 모델은 샌드박스 체크아웃이 있을 때만 `grep/readFile/…`로 더 읽는다.
6. **E2B·Morph·Exa·임베딩은 필수가 아니다**(7절). 샌드박스 기본값 `auto`는 `API_E2B_KEY`가 있을 때만 E2B이고 아니면 로컬이다.

<a id="q3"></a>
## Q3. 문맥 확보와 동적 탐색

### 3.1 고정 문맥 확장 / 동적 탐색 / 재시도 / Agent Loop 구분표 (Q3·Q4 공통)

| 구분 | Kodus에서 해당하는 것 | 결정 주체 | 근거 | 검증 |
|---|---|---|---|---|
| **고정 문맥 확장**(프로그램이 자동 수집) | 번호 붙은 diff, 커버리지 대상 목록, PR 제목·본문(앞 500자), 커밋, 리뷰 지시문, CI 증거, 결정적 스캐너 결과, Kody 메모리 규칙, 이전 라운드 결정, call graph(`<CallGraph>`), (선택) 외부 참조·Trace 결정, 링크된 저장소 설정 | 프로그램 | `libs/code-review/infrastructure/agents/prompts/prompt-builder.ts:629-670,690-697,700-704,713`, `libs/code-review/pipeline/stages/build-orchestrator-input.ts:87-159` | 코드 확인 |
| **동적 탐색**(모델이 요청) | `grep`, `readFile`, `listDir`, `findFile`, `checkTypes`, `getCallers`, `searchDocs`, `readReference`(연결 저장소) | 모델 | `libs/code-review/infrastructure/agents/engine/agent-tools.factory.ts:300-1757` | 코드 확인 |
| **재시도 / fallback** | AI SDK 스텝당 `maxRetries: 3`, 1회 호출 재발행(TRANSIENT만), 모델 failover(primary→fallback 1단), `OverflowRecoveringRunner`(60% 창으로 1회) | 프로그램 | `libs/llm/agent-loop-call.ts:57,210`, `libs/llm/retry-policy.ts:20-35`, `libs/llm/model-failover.ts:12-17,75-114`, `libs/code-review/infrastructure/agents/core/overflow-recovering-runner.ts:32-54` | 코드 확인 |
| **다중 호출**(파일·청크별 같은 프롬프트) | 토큰 예산 초과 시 파일 배치별 finder+verifier 순차 실행, Kody Rules는 파일당 1회+PR 1회 | 프로그램 | `base-code-review-agent.provider.ts:421-505`, `kody-rules-sharded.judge.ts:1233-1347` | 코드 확인 |
| **다단계 파이프라인**(단계별 다른 프롬프트, 고정 순서) | 비즈니스 로직 → 샌드박스 → finder → verifier → dedup → severity → 포맷 → committable 검증 → 요약 | 프로그램 | `code-review-pipeline.strategy.ts:70-109`, `agent-review.stage.ts:992-1508` | 코드 확인 |
| **Agent Loop** | finder, verifier, synthesis, heavy resample, 비즈니스 로직 fetcher/verifier | 모델(도구 선택·종료 호출) | `core-agent-loop.adapter.ts:57-244`, `verifier.agent.ts:288-372` | 코드 확인 |

### 3.2 도구 입출력 스키마

스키마는 zod가 아니라 raw JSON Schema(`mkTool`/`jsonSchema`)이고 출력은 항상 문자열이다. 도구는 `remoteCommands`(샌드박스 핸들)가 있을 때만 등록된다(`agent-tools.factory.ts:191-193`: `if (!remoteCommands) return {}`). 코드 확인.

| 도구 | 입력(* 필수) | 출력 | 탐색 방식 | 위치 |
|---|---|---|---|---|
| `grep` | `pattern*`, `glob`, `path`, `namesOnly`, `excludeTests`, `repo`† | 매치 문자열(상한 50매치/40그룹) | **ripgrep**(`rg -n -C 2`) 명령 실행. 로컬 샌드박스에서는 `exec`가 `rg`를 거부해 호스트 `rg -n`으로 폴백. 심볼 의미는 이해하지 않음, 모델이 추론 | `agent-tools.factory.ts:300-551,17,25`, `local-sandbox.service.ts:401-433,534-545,607-612` |
| `readFile` | `path*`, `startLine`, `endLine`, `repo`† | 줄 번호가 붙은 본문(최대 8000자) | `sed`/`cat` | `agent-tools.factory.ts:553-727,26` |
| `listDir` | `path`, `maxDepth`(≤4), `repo`† | 디렉터리 트리 문자열 | `find`/`listDir` | `agent-tools.factory.ts:729-858` |
| `findFile` | `pattern*`, `path`, `extension` | 경로 목록 | `fd`→`find`→`listDir` | `agent-tools.factory.ts:860-986` |
| `checkTypes` | `path` | 컴파일러 출력 | `npx tsc --noEmit`, `go vet`, `cargo check`, `mypy` 등 **저장소 코드 실행**. 로컬 샌드박스 허용 목록이 모두 막음 | `agent-tools.factory.ts:1074-1461`, `local-sandbox.service.ts:523-545` |
| `getCallers` | `functionName*` | 호출자/피호출자 문자열 | **주입된 `callGraph` 문자열을 파싱**. DB·샌드박스 조회 없음. DB 기반 구현은 "0 tool calls in 170+ runs"라는 주석과 함께 주석 처리됨 | `agent-tools.factory.ts:1540-1669` |
| `searchDocs` | `packageName*`, `query*` | 문서 요약 | Exa 웹 검색+캐시+LLM 포맷. `API_EXA_KEY` 없으면 "not available" | `agent-tools.factory.ts:1672-1757`, `documentation-search-exa.service.ts:77-87` |
| `readReference` | `repo*`, `path*`, `branch` | 파일 본문 | `https://api.github.com/repos/${repo}/contents/…` 호출, 헤더 `Authorization: Bearer ${gitHubToken}`. 토큰은 **clone 토큰**이며 플랫폼 확인 없이 `api.github.com` 고정이다(비-GitHub 조직 토큰 전송 가능성, 추론, [07 4.6절](07-credentials.md)). 2026-10-13 정정: 이전 "ee 링크 저장소 경로" 표기는 부정확. `gitHubToken`이 있으면 등록되며(`:1469-1470`) 링크 저장소(ee)의 `repo` 인자 경로와는 별개다(코드 주석은 규칙의 `@file:org/repo/…` 외부 참조용이라고 설명, `:1463-1468`) | `agent-tools.factory.ts:1469-1533` |
| `submitResult` / `submitVerdict` | 결과 JSON | no-op, 페이로드를 아티팩트로 수집 | - | `finder.agent.ts:90-150`, `verifier.agent.ts:49-69`, `ai-sdk-agent-runner.ts:511-541` |

† `repo`는 링크된 저장소가 활성일 때만(Teams/Enterprise 플랜+경계 게이트+설정, `agent-review.stage.ts:2977-3068`). 읽기 도구는 실행 단위로 메모이즈되고 캐시는 finder와 verifier가 공유한다(`finder-tools.adapter.ts:52-60,115-141`; verifier가 finder의 읽기 캐시를 재사용한다는 점은 추론). MCP는 finder 도구에 노출되지 않는다(`finder-tools.adapter.ts:79-92`). 코드 확인.

### 3.3 모델이 선택하는 것 / 프로그램이 고정하는 것

- 프로그램: 프롬프트, 도구 레지스트리, 정책(예산·압축·완료 게이트·강제 종료), 최대 스텝, 파일 배치, 타임아웃.
- 모델: 어떤 도구를 어떤 인자로 언제 부를지, `submitResult`를 언제 호출할지.
- 프롬프트가 탐색 절차를 지시한다. 예: "For each method CHANGED in the diff, trace the call chain: a) grep("exactMethodName\\(", excludeTests=true) → find who calls it" (`prompt-builder.ts:504-506`) — "변경된 각 메서드의 호출 체인을 따라가라: grep으로 호출자를 찾아라". 코드 확인.

### 3.4 "변경하지 않은 호출부 찾기" 정적 실행 예 (미실행)

함수 `F`를 A 파일에서 수정했고, 변경하지 않은 호출자는 B 파일에 있다.

1. **고정 경로**: `AgentReviewStage`가 `repo.astGraphStatus === READY`이면 `graphContext.generateContext`를 호출한다(`agent-review.stage.ts:631-656`). 샌드박스 안에서 `kodus-graph`를 돌리고 Postgres `ast_edges`에서 `F` 노드 이웃을 꺼내 `<CallGraph>` XML로 렌더링해 프롬프트에 주입한다(`graph-context.service.ts:41-124`, `astGraph.repository.ts:370-410`; 주입은 `prompt-builder.ts:641-643`, 힌트는 "…but still verify with tools before reporting"). `astGraphStatus`가 READY가 아니면 DB 기준선 없이 샌드박스에서 직접 만드는 `generateContextLegacy`를 호출하고(`agent-review.stage.ts:650`), `generateContext` 자체도 저장소 미조회·예외 시 `generateContextLegacy`로 폴백한다(`graph-context.service.ts:91,132`). `callGraph=''`와 경고는 이 폴백까지 실패하거나 샌드박스·파일 경로가 없을 때다(`agent-review.stage.ts:657-676`). 2026-10-13 정정: 이전 서술은 "실패하면 빈 call graph"로 legacy 폴백을 빠뜨렸다. 코드 확인.
2. **동적 경로**: 모델이 `grep("F\\(", excludeTests=true)`를 호출한다. E2B에서는 `rg -n -C 2 'F\(' …`를 `exec`로 실행하고 로컬 샌드박스에서는 `exec`가 `rg`를 거부해 호스트 `rg -n`으로 폴백한다. 이어 `readFile(B, line-15, line+30)`로 호출 맥락을 읽고, `getCallers("F")`는 call graph 문자열을 조회한다.
3. verifier가 후보를 검증할 때 2번을 자체적으로 반복할 수 있다.

### 3.5 파일 그룹별 리뷰에서 파일 간 결함을 놓칠 가능성 (추론)

- finder 프롬프트가 "Root cause must be in lines added or modified by this PR"(`prompt-builder.ts:569`)이라 말하고, finding이 어떤 hunk와도 겹치지 않으면 코드가 버린다(`agent-review.stage.ts:992-1041`). 따라서 **다른 파일의 결함은 변경된 트리거 줄에 앵커될 때만** 보고된다.
- 토큰 초과 시 배치마다 에이전트는 **그 배치의 diff만** 본다(`batch-runner.ts:113-124`). 단 call graph와 도구는 전체 체크아웃을 대상으로 한다.
- 코드 안에 회수율 언급이 있다: ">500-line PRs ~35% vs ~46% medium" recall(`review-orchestrator.service.ts:353-358`). 코드 주석 인용이며 직접 측정한 값이 아니다.

### 3.6 샌드박스가 없을 때 (코드 확인 + 일부 추론)

- `acquire`가 던지면 `sandboxHandle`이 없고 → `remoteCommands`가 없어 `buildAgentTools`가 `{}`를 반환 → **self-contained 프롬프트로 도구 없이 diff(+파일 본문)만** 본다(`create-sandbox.stage.ts:197-227`, `build-orchestrator-input.ts:90-93`, `prompt-builder.ts:459-461,613-615`). 코드 확인.
- 반대로 provider `null`이거나 클론 파라미터가 없어 **null 샌드박스**가 반환되면 `remoteCommands`는 있지만 모든 호출이 "No sandbox configured"로 던진다(`libs/sandbox/infrastructure/providers/null-sandbox.service.ts:37-51`). 이때 모델은 도구가 있는 프롬프트를 받고 호출이 오류가 될 수 있다(추론). `agent-review.stage.ts:620-629`가 `SANDBOX_UNAVAILABLE` 경고를 내보낸다. 코드 확인.

### 3.7 Q3 지원 수준

**지원(조건부).** 체크아웃이 있으면 호출자·구현체·설정·테스트를 모델이 `grep/readFile`로 직접 찾는다. call graph는 고정 문맥이며 `getCallers`는 그 문자열 파서일 뿐 실시간 심볼 조회가 아니다. AST/LSP/임베딩 기반 검색 도구는 모델에 노출되지 않는다. 체크아웃이 없으면 동적 탐색은 불가하다.

<a id="q4"></a>
## Q4. Agent Loop

### 4.1 호출 지점 (실행 순서)

| # | 지점(파일:줄) | 방식 | 모델 슬롯 | 입력 | 출력 | 게이트 |
|---|---|---|---|---|---|---|
| 1 | 비즈니스 로직 fetcher (`libs/agents/skills/generic-skill-runner.service.ts:300-335`) | Agent Loop(MCP 도구), `maxSteps` 2~4 | `businessValidation` | PR 본문·티켓 키 | 텍스트 | `reviewOptions.business_logic`+task MCP+티켓 신호 |
| 1b | 비즈니스 분석기 (`businessRulesValidationAgent.ts:639-677`) | 도구 없는 1회(`maxSteps:1`) | 동일 | diff+티켓 텍스트 | 텍스트 | 동일 |
| 1c | 비즈니스 verifier (`businessRulesValidationAgent.ts:396-444`) | 에이전트 실행, 기본 off | 동일 | 분석 결과 | 판정 | 정책(미확인) |
| 2 | **finder** (`finder.agent.ts:207-258`, `core-agent-loop.adapter.ts:212-244`) | **Agent Loop**. 카테고리별 병렬(`review-orchestrator.service.ts:227-229`). 일반 모드 `generalist`(+`kody-rules`), deep은 bug/security/performance | `codeReview` | 시스템+유저 프롬프트(diff, call graph, PR 텍스트…) | `submitResult` 도구 `{reasoning, suggestions[]}` | 항상 |
| 2b | 산문 복구 (`finder.agent.ts:435-491`) | 구조화 1회 | 동일 | finder 산문 | suggestions | finder가 finding을 산문으로 썼을 때 |
| 2c | synthesis rescue (`finder.agent.ts:922-933`) | finder 루프 재실행 | 동일 | 프롬프트+조사한 파일+현재 finding | `submitResult` | fast/self-contained/작은 창 제외 |
| 2d | heavy resample ×2 (`finder.agent.ts:945-976`) | finder 루프 2회 동시 | 동일 | 원 프롬프트 | `submitResult` | `heavy` 옵션+알파 게이트 `heavyReview` |
| 3 | **verifier** (`verifier.agent.ts:336-372`) | **Agent Loop**, 후보별, 동시성 4(`verification-pass.ts:43`), light 5 / full 10 스텝 | 동일 슬롯 | 파일·줄·claim·코드 | `submitVerdict` 또는 JSON 텍스트 | 후보가 있으면 항상 |
| 3b | 증거 게이트 재검증 (`finder.agent.ts:699-738`) | verifier `forceFull` | 동일 | finder가 읽지 않은 파일의 finding | 판정 | 자동 |
| 4 | Kody Rules 판정 (`kody-rules-agent.provider.ts:283-310`, `kody-rules-sharded.judge.ts:1200-1365`) | **구조화 1회**, 동시성 4, 파일당 1회+PR 1회 | `kodyRulesReview` | 한 파일 hunk(+본문 ≤4000줄/40k자)+규칙 | `{violations[]}` | 활성 표준 규칙이 있을 때 |
| 5 | LLM dedup (`agent-review.stage.ts:2228-2316`) | 구조화 1회(전체 finding 한 번에) | 조직 슬롯 또는 기본 | 요약들 | `{groups, unique}` | finding ≤1이면 생략 |
| 5b | dedup 가드: OpenAI `text-embedding-3-small` 임베딩+동점 판정 (`agent-review.stage.ts:2039-2149`) | `embed`+구조화 1회 | 임베딩은 플랫폼 OpenAI 키 고정 | 쌍 | boolean | 키 없으면 어휘 거부(병합 안 함) |
| 6 | severity 재분류 (`classify-severity.ts:38-95`, 단계 `:1203-1244`) | 텍스트 1회 | 슬롯 또는 기본 | 요약+내용 | `{classifications}`; 실패 시 전부 `medium` | 항상 |
| 7 | 제안 포맷 (`format-suggestion-content.ts`, 단계 `:1342-1404`) | 텍스트 1회 | 슬롯 | 내용+코드 | 재작성 문장 | 분석기 finding 제외 |
| 8 | committable 검증 (`validate-suggestions.stage.ts:93-245`) | 구조화 1회 ×2+Morph | 슬롯 | `improvedCode` | boolean | `enableCommittableSuggestions`+GitHub |
| 9 | PR 요약 (`commentManager.service.ts:290-640`) | 텍스트 1회(파일 청크) | `prSummary` | 패치+finding | 마크다운 | 요약 설정 |

(2~9의 파일:줄은 조사 에이전트가 연 값이며, 2·3은 작성자가 재대조했다.)

### 4.2 상태·입력·종료 조건 표

공유 엔진 `AiSdkAgentRunner.run`은 `[seedMessages…, {role:'user', content: prompt}]`로 시작하고 시스템 프롬프트는 별도 인자로 넘긴다. `LLM.run({loop:{tools,maxSteps,stopWhen,prepareStep,onStepFinish}})`으로 AI SDK 루프를 실행한다(`ai-sdk-agent-runner.ts:97-103,245-308`). 도구 오류는 `"ERROR: …"` 문자열이 되고(`:89-92`), 도구 결과를 대화에 붙이는 일은 AI SDK가 한다(SDK 내부는 이 레포에 없어 추론). 실패는 `RunState{status:'error'}`가 된다(`:309-375`). 정책은 `prepareStep`에서 사용자 턴으로 안내문을 주입한다(시스템이 아님, `:151-191,475-481`).

| 단계 | 반복 단위 | 입력(상태) | 모델 선택 | 프로그램 고정 | 종료 조건 | 위치 |
|---|---|---|---|---|---|---|
| finder | 에이전트(카테고리)×파일 배치당 `generateText` 다단계 1회 | system + user(diff, call graph, PR 텍스트, 커버리지 목록) + 누적 도구 결과 | 도구·인자·`submitResult` 시점 | 도구 레지스트리, 정책, `maxSteps` | `stopWhen`: 정책 `shouldStop` 또는 `stepCountIs(maxSteps)`. `CompletionGatePolicy`는 `submitResult`를 **critical 커버리지 대상이 남지 않은 경우에만** 인정. 마지막 2스텝은 `ForceFinalizePolicy`가 `activeTools`를 `submitResult`로 제한 | `finder.agent.ts:227-258`, `libs/agent-harness/infrastructure/policies/completion-gate.policy.ts:81-96`, `libs/agent-harness/infrastructure/policies/force-finalize.policy.ts:31-53` |
| finder 스텝 예산 | 에이전트별 `maxSteps` | - | - | fast 3~4, normal bug/general 20, security/performance 12, deep 100, 8파일 초과 시 파일당 +0.5(상한 100) | `stepCountIs` | `review-orchestrator.service.ts:74-88,335-371` |
| finder 시간·취소 | 에이전트 전체 | - | - | `AGENT_TIMEOUT_MS` 80분(finder+recall+verify가 하나의 `createAgentRunContext` 공유), 모델 1왕복 20분, 잡 타임아웃 105분(바깥). 부모 잡 `signal`이 합성됨 | 타임아웃·취소 시 `abortSignal` | `libs/llm/llm-call.ts:12-35`, `libs/llm/agent-run-context.ts:24-44`, `core-agent-loop.adapter.ts:207-210`, `job-processor-router.service.ts:30` |
| finder 조사 충분 판정 | - | - | - | **하드 게이트는 `fileTiers`가 있을 때만**(큰 PR·작은 컨텍스트 창 경로). 티어 맵이 없으면 `criticalTotal=0`이라 게이트가 거부하지 않고 "Do not finalize until…" 안내문만 있다 | 게이트 | `libs/code-review/infrastructure/agents/engine/coverage-ledger.ts:50-106,228-241`, `completion-gate.policy.ts:92` (추론: 두 파일을 조합) |
| verifier | 후보 1건당 에이전트 실행 | `buildVerifierPrompt`(파일·줄·claim·코드·이전 결정) | 읽을 파일·판정 | finder와 같은 도구 레지스트리, light 5/full 10 스텝 | `BudgetPolicy`+`ForceTextFinalizePolicy`(마지막 2스텝에 텍스트 JSON 판정 요구). 판정 파싱 불가 → **keep**, 예외 → **keep** | `verifier.agent.ts:89-134,213-218,288-372`, `verification-pass.ts:38-70`, `force-text-finalize.policy.ts:52-75` |
| 비즈니스 fetcher | MCP 루프 | PR 본문 | MCP 도구 | `maxSteps` 2(스킬 선언 `libs/agents/skills/business-rules-validation/SKILL.md:29`의 `fetcher-max-iterations: 2`. 러너 기본값은 4, `generic-skill-runner.service.ts:884`) | 스텝 상한 | `generic-skill-runner.service.ts:300-335,884` |
| Kody Rules 판정 | 파일당 1회 | 규칙+hunk | 해당 없음(도구 없음) | 1회 구조화 호출 | 응답 | `kody-rules-agent.provider.ts:151-163` |

### 4.3 종료 조건 점검

| 조건 | 확인 결과 | 검증 |
|---|---|---|
| 정상 종료 | 모델이 `submitResult`/`submitVerdict` 호출 → (게이트 통과 시) 루프 정지. 마지막 2스텝은 제출 도구만 활성화해 강제 | 코드 확인 |
| 도구 호출 없음 | 모델이 도구 없이 텍스트만 내면 AI SDK 루프가 끝난다(SDK 동작은 레포 밖, 추론). finder가 finding을 산문으로 쓴 경우 구조화 복구 1회(`finder.agent.ts:376-385,435-491`) | 코드 확인 + 추론 |
| 최대 반복 | `stepCountIs(maxSteps)`(`libs/llm/agent-loop-call.ts:234`). 상태값 `budget-exhausted`가 있다 | 코드 확인 |
| 토큰 한도 | **실행당 토큰·금액 상한은 없다**(`libs/agent-harness`, `libs/llm/agent-loop-call.ts` 검색). 컨텍스트는 `CompressionPolicy`/`OverflowRecoveringRunner`가 줄일 뿐이다. 비용은 기록만(`recordAgentRunUsage`) | 코드 확인(부정 grep) |
| 시간 한도 | 모델 1왕복 20분, 에이전트 80분, 잡 105분. 코드 주석이 근거로 14일치 `AgentReviewStage` 소요(n=94: p50 3.1분, p90 11.6, p99 29.5, max 32.2)를 인용한다(주석 인용, 직접 측정 아님). `createAgentRunContext` 주석은 기본값이 "30 min"이라고 적어 낡았다 | 코드 확인 |
| 취소 | 부모 잡 `signal`이 에이전트 `signal`로 합성됨. **파이프라인 실행기는 `signal`을 확인하지 않는다**(`parentSignal`의 소비자는 `build-orchestrator-input.ts:158`과 에이전트 루프뿐). 잡 프로세서는 유스케이스 전체를 신호와 `raceWithAbortSignal`로 경주시켜 풀어주지만 메모리 속 파이프라인은 취소되지 않는다(추론) | 코드 확인 + 추론 |
| 모델 오류 | primary→fallback 1회 failover(첫 루프 스텝이 나가면 failover 불가), 스텝당 `maxRetries 3`. finder 실패는 `RunState{error}`, verifier 실패는 **유지**(fail-open) | 코드 확인 |
| "충분히 조사했다" 판단 | 모델이 `submitResult`를 부르는 것이 유일한 신호. 하드 게이트는 `fileTiers`가 있을 때만 | 코드 확인 |
| (결함 후보) 한계 도달 판정 | base provider는 `finishReason === 'timeout'` 또는 `source==='empty' && finishReason==='tool-calls'`로 "incomplete"를 판단하는데(`base-code-review-agent.provider.ts:727-730`), core 어댑터는 `finishReason`에 `completed/stopped/budget-exhausted/error`를 넣는다(`core-agent-loop.adapter.ts:346-348`). 값이 맞지 않아 `result.incomplete`(`agent-review.stage.ts:829-862`)는 이 경로에서 도달 불가로 보인다 | 추론(두 파일 대조, 조사 에이전트) |

### 4.4 재시도 범위

- 1회 호출: TRANSIENT만 1회 재발행(지터 500ms~10s, 429 제외), BYOK 제한기가 쿨다운이면 생략(`libs/llm/retry-policy.ts:20-51`, `libs/llm/structured-review-call.ts:776-804`).
- 루프: 스텝당 `maxRetries 3`, 도구 호출 인자 오류는 `repairToolCall`로 같은 모델에 자가 수정(`libs/llm/agent-loop-call.ts:210,218-231`). 코드 확인.
- 잡 수준 재시도는 [04](04-saas-and-isolation.md)의 큐 정책을 따르지만, 파이프라인 안의 오류는 대부분 삼켜져 잡이 `COMPLETED`로 끝난다([01](01-execution-and-diff.md#q1) 13단계, [04 2절](04-saas-and-isolation.md)).

### 4.5 모델 선택(BYOK)과 라우팅

`PermissionValidationService.resolveTaskSlot`(**ee**)이 조직의 BYOK 설정(`organization_parameters`, 조직 스코프)을 읽고, `StaticTaskStrategy`가 폴더/저장소 오버라이드 > `routing.taskOverrides[task]` > `routing.defaultModelId` 순으로 슬롯을 정하고 실패 시 `fallbackModelId`를 쓴다. BYOK가 없으면 환경변수의 관리형 기본 모델이다. 복잡도 기반 라우팅은 없고 작업(task)별이다. 근거: `libs/ee/shared/services/permissionValidation.service.ts:955-987,1170-1186`, `libs/llm/static-task-strategy.ts:1-19`, `libs/llm/resolve-task-model.ts:47-90`, `libs/llm/README.md:13-19,43-45`. 코드 확인.

### 4.6 Q4 지원 수준

**지원.** finder와 verifier는 모델이 도구를 호출하고 결과를 대화에 넣어 다시 추론하는 Agent Loop이며 예산·완료 게이트·강제 제출·타임아웃·취소가 구현돼 있다. 한계: 실행당 토큰·금액 상한 없음, 파이프라인 실행기는 취소 신호를 확인하지 않음, "incomplete" 판정 불일치 가능성.

<a id="q5"></a>
## Q5. 검증 (finding 필터링)

### 5.1 검증 단계 표

| 단계 | 입력 | 출력 | 모델·문맥 독립성 | 추가 파일 접근 | 위치 |
|---|---|---|---|---|---|
| finder 내 **후보별 verifier** | finding 1건(파일·줄·claim·코드)+같은 PR의 이전 결정 | `keep:false`는 **명시적 반증**일 때만. 기본 keep, 실패도 keep | 새 메시지의 새 실행이지만 **같은 모델 슬롯·같은 프롬프트 계열·같은 도구 캐시**. 별도 모델 아님 | **있음**(같은 도구, light 5/full 10 스텝) | `verifier.agent.ts:288-372`, `verification-pass.ts:38-70` |
| 증거 게이트 | finder가 읽지 않은 파일의 finding | `forceFull` 재검증 | 동일 | 있음 | `finder.agent.ts:699-738` |
| 줄 유효성 | finding vs diff hunk | 겹침 없으면 `DISCARDED_BY_CODE_DIFF`, 있으면 스냅, 줄 없으면 첫 hunk | 결정적(모델 아님) | 없음 | `agent-review.stage.ts:224-286,992-1041` |
| 경로 유효성 | `relevantFile` vs 변경 파일 | `@@PATH_MISMATCH@@` 드롭 | 결정적 | 없음 | `finding-mapper.ts:253-281`, `base-code-review-agent.provider.ts:700-722` |
| LLM dedup+임베딩 가드 | 같은 실행 내 모든 비규칙 finding | 그룹 병합. 어휘 ≥0.3이면 허용, 코사인 ≥0.7 허용/<0.4 거부/사이는 LLM 판정. 임베딩을 못 쓰면 병합 거부(전부 유지)가 기본이나 분석기 finding을 모델이 다시 쓴 쌍(`restatesAnalyzerFinding`)만 예외로 병합(`agent-review.stage.ts:2072-2090`) | LLM 같은 슬롯, 임베딩은 OpenAI | 없음 | `agent-review.stage.ts:2039-2110,2228-2316`, `dedup-prompt.ts:52,207-208` |
| Kody 규칙 dedup | `ruleUuid` | PR 수준은 1건, 파일 수준은 최선+"Also found in" | 결정적 | 없음 | `agent-review.stage.ts:1098-1122,1885-1925` |
| claim checker(규칙) | `claimKind`가 unused/missing/duplicate인 finding | grep/exists 1회 확인, **fail-closed 드롭** | 결정적(모델 아님) | 저장소 조회 | `claim-checker.ts:1-30`, `kody-rules-agent.provider.ts:685-710` |
| severity 필터 | 재분류 후 | 임계 미만 드롭(규칙 finding은 기본 면제) | 모델(분류) | 없음 | `agent-review.stage.ts:1246-1297` |
| bad-fix 게이트 | `improvedCode` | 사용 불가 코드는 제거, 댓글은 유지 | 결정적 | 없음 | `agent-review.stage.ts:1452-1508` |
| 재실행 dedup | `previousDecisions` | verifier가 "이미 제기된 문제"면 DROP, finder는 "never report again" | LLM | - | `verifier-prompt.ts:35`, `prompt-builder.ts:415-419` |
| committable 검증 | 병합 코드 | `isCommittable` 표시. **드롭하지 않음** | Morph+샌드박스 구문 검사+LLM | - | `validate-suggestions.stage.ts:93-272` |
| 구현 확인 | 이후 커밋 패치 vs 보낸 제안 | `implementationStatus` 설정. 정확도 필터가 아님. **별도 워크플로 잡** | LLM | 없음 | `libs/code-review/workflow/implementation-verification.processor.ts:109-250` |

- **구조화 출력(스키마 검증)과 결함 검증을 구분하면**: 스키마·경로·줄 검증은 결정적이고 의미적 결함 검증은 verifier 에이전트와 claim checker가 맡는다. 줄 유효성 검증은 의미를 검증하지 않는다.
- **독립성**: verifier는 새 실행이지만 같은 모델 슬롯이라 finder와 상관된 오류를 공유할 수 있다(추론). 실제로 "recall이 정밀도보다 중요"하다는 프롬프트가 기본 KEEP을 고정한다.

verifier 프롬프트 핵심 문장 (`libs/code-review/infrastructure/agents/prompts/verifier-prompt.ts`):
- "The bar to remove a finding is a REFUTATION, not a doubt." (`:21`) — 제거 기준은 의심이 아니라 반증이다.
- "KEEP the finding (this is the DEFAULT) whenever you cannot refute it." (`:37`) — 반증하지 못하면 유지가 기본이다.
- "When in doubt, KEEP — a human reviewer makes the final call." (`:42`) — 애매하면 유지, 최종 판단은 사람.
- 프롬프트는 "up to 4 tool-call steps"(`:47`)라고 하지만 설정은 5/10 스텝(`verifier.agent.ts:317-327`)이다.

finder 프롬프트(`prompt-builder.ts`): "Assume every change is broken until you prove it is safe."(`:491`, 모든 변경은 안전함이 증명될 때까지 깨져 있다고 가정), "A later verifier will filter unsupported claims."(`:494`, 근거 없는 주장은 이후 verifier가 거른다).

코드 주석이 인용하는 운영 수치: `ForceTextFinalizePolicy` 도입 전 verifier 154회 중 20%가 판정을 내지 못했다(`libs/agent-harness/infrastructure/policies/force-text-finalize.policy.ts:18-22`). 주석 인용이며 직접 측정이 아니다.

### 5.2 evals/

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 측정 대상 | 엔진 PR마다 wiring smoke(스크립트 모델, 수치 측정 없음), 야간 finder recall(30개 PR 세트, 저가 모델 하나, 하한 게이트), 주간 tier-0 모델별 smoke | `evals/README.md:9-51` | 코드 확인 |
| 실제 코드와 연결 | 하니스가 `ts-node/register`로 **프로덕션 TS**를 로드해 `GeneralistAgentProvider`·`runAgentLoopViaCore`를 호출. 단, **도구 출력은 녹화본 재생**이며 녹화에 없는 탐색은 "loop-fidelity"로 표시. 탐색 도구 변경과 다운스트림(cap/dedup/anchoring/delivery)은 범위 밖 | `evals/investigation/agent-provider.js:1-2,480-483,625-628`, `evals/README.md:28`, `evals/investigation/README.md:45-53` | 코드 확인 |
| 오탐·누락 측정 | LLM 판정자가 PR의 golden bug와 finding을 매칭. recall=golden 커버율, precision=golden에 맞은 finding 비율, fair-recall은 재생 코퍼스에 없는 golden 제외 | `evals/investigation/README.md:39-47` | 코드 확인 |
| 한계 | golden에 없는 실제 버그가 오탐으로 집계됨(추론) | 위 정의 | 추론 |
| 단계별 | dedup(잃은 golden 0 목표, 실제 프롬프트+`LLM.run`), anchoring(실제 `snapLinesToDiff`), kody-rules, review-rounds(finder→verifier→severity→format, 샌드박스만 대체), verifier-verdict(결정적 파싱 점검), promotion(보고 전용), review-chain(grep으로 resilience 마커 확인, "NOT behavioral coverage" 명시) | `evals/dedup/README.md:15-28`, `evals/anchoring/README.md:12-35`, `evals/review-rounds/README.md:20-45`, `evals/review-chain/README.md:14-24` | 코드 확인 |
| 문서 불일치 | `evals/kody-rules/README.md`는 "same agent loop… same tools"라 하지만 코드는 도구 없는 judge. `investigation/README.md:36` "Sonnet judge" vs `targets.json:17-18` haiku | 위 경로 | 코드 확인 |

### 5.3 Q5 지원 수준

**부분 지원.** 후보별 verifier 에이전트가 추가 파일을 읽으며 반증하고 결정적 필터·dedup·severity·bad-fix 게이트가 있다. 그러나 verifier는 같은 모델 슬롯이고 기본 KEEP이며, committable 검증은 드롭하지 않고, 구현 확인은 정밀도 필터가 아니다.

## 6. 규칙·메모리 입력 위치 (참고)

규칙·메모리가 모델 입력의 어디에 들어가는지는 [03 Q8](03-incremental-memory-rules.md#q8)에 있다.

<a id="sandbox"></a>
## 7. 샌드박스·E2B·Morph·임베딩·MCP: 실제 사용 조건

| 항목 | 시작 지점·게이트 | 필수 여부 | 근거 | 검증 |
|---|---|---|---|---|
| 샌드박스 제공자 | `SANDBOX_PROVIDER`=`null`/`local`/`e2b` 명시, 기본 `auto`는 `API_E2B_KEY`가 있으면 E2B, 아니면 `LocalSandboxService`. `none` 같은 값은 `auto` 분기로 떨어짐 | **E2B 불필요** | `libs/sandbox/modules/sandbox.module.ts:26-51` | 코드 확인 |
| 로컬 샌드박스 | 워커 호스트 임시 디렉터리에 클론(클론 예산 `API_SANDBOX_CLONE_TIMEOUT_MS` 기본 120초). `exec` 허용 프로그램은 `sg ast-grep cat wc head tail file fd find grep`뿐. **컨테이너 격리 없음**(코드 주석이 RCE 위험을 명시) | 대체 경로 | `local-sandbox.service.ts:44-47,523-545` | 코드 확인 |
| E2B | `E2BSandboxService`, 샌드박스 구문 검증(`sandboxSyntaxValidator.service.ts:36-45`), `e2b-sandbox/template.ts:33-47`이 템플릿에 git·ripgrep·프록시·betterleaks·osv-scanner 설치. 클론 인증 헤더가 `GIT_AUTH_HEADER` 환경변수로 E2B 명령에 전달되고 쉘이 풀어 git 인자(`-c http.extraHeader=…`)로 넘기므로 VM 안 프로세스 argv에 남는다([07 4.2절](07-credentials.md)). AST 그래프 빌드 프로세서(`ast-graph-build-job.processor.ts:168-181`)는 E2B를 직접 참조하지 않고 provider 중립인 `leaseManager.acquire`를 쓴다(2026-10-13 정정: 이전에 E2B 사용처로 분류함) | 선택 | `e2b-sandbox.service.ts:462,833` | 코드 확인 |
| Morph | `validate-suggestions.stage.ts`의 `applyEdit`만(`:16,537-545`). 게이트: `enableCommittableSuggestions`+GitHub+지원 언어+짧은 `improvedCode`. 키 없을 때 폴백 없음(null, committable 아님) | **선택**, 해당 단계는 `partial` 심각도 | `validate-suggestions.stage.ts:138-162,391-420,561-568` | 코드 확인 |
| Exa | `searchDocs`. 키 없으면 "not available" | 선택 | `documentation-search-exa.service.ts:77-87` | 코드 확인 |
| 임베딩 | (1) dedup 가드: 플랫폼 OpenAI 키 고정, 없으면 어휘 거부. (2) `kodyFineTuning`의 `suggestion_embedded`(pgvector 컬럼)는 **활성 파이프라인에서 호출되지 않음**. npm `pgvector`는 import 없음 | 선택 | `libs/common/utils/document.ts:52-87`, `libs/code-review/pipeline/code-review-pipeline.module.ts:200` vs `strategy:70-109` | 코드 확인 |
| MCP SDK | 클라이언트로 비즈니스 로직 fetcher·대화 에이전트가 사용. finder 도구에는 없음. 서버로서 외부 클라이언트에 Kodus 도구를 노출(`libs/mcp-server`) | 선택 | `libs/mcp-server/mcp-adapter/client.ts`, `finder-tools.adapter.ts:79-92` | 코드 확인 |
| `kodus-graph` | 외부 npm CLI(`@kodus/kodus-graph@0.3.0`)를 샌드박스에서 bun으로 설치·실행. 파서 소스는 이 레포에 없음 | 조건부(없으면 call graph 비움) | `libs/code-review/infrastructure/adapters/services/graph/kodus-graph-cli.ts:7,36-76` | 코드 확인 / 파서 미확인 |

AST 그래프 저장: Postgres `ast_nodes`/`ast_edges`(`repo_id` 키). 리뷰 시 조회는 `findByExternalId(platform, externalId)`이고 내보내기 쿼리는 `repo_id`만 조건이다. **조직 조건 없음**(추론). 근거: `agent-review.stage.ts:634-645`, `libs/code-review/infrastructure/adapters/repositories/repository.repository.ts:72-79`, `astGraph.repository.ts:370-395`, `repository.model.ts:15-31`. `context.callGraphJson`은 어디서도 할당되지 않아 파일 우선순위 점수기의 그래프 입력은 이 경로에서 비어 있다(`build-orchestrator-input.ts:132`, `file-priority-scorer.ts:99-115`, 추론).

### 죽은 코드 (활성 경로에 호출이 없음, 추론+grep)

`SafeguardPipelineService`/`LLMAnalysisService.filterSuggestionsSafeGuard`(호출처 없음, `codebase.module.ts:106,120` 등록만), `repeatedCodeReviewSuggestionClustering`(레거시 prioritizer에서만, `suggestion.service.ts:735`), `sortAndPrioritizeSuggestions`(외부 호출 없음). "별도 critic 패스"는 주석(`finder.agent.ts:518-520`)에만 있고 실제는 resample 2회+synthesis다.

## 8. ee/ 라이선스 표시 (이 문서 범위)

`libs/core/providers/code-review-pipeline.provider.ee.ts`(파이프라인 실행 배선), `libs/ee/shared/services/permissionValidation.service.ts`(BYOK 슬롯 해결·라이선스 게이팅, 거의 모든 에이전트 provider가 import), `libs/ee/linked-repositories/**`(자체 `LICENSE`, 운영 사용은 Teams/Enterprise 계약 필요), `libs/ee/codeReview/stages/kody-fine-tuning.stage.ts`(미사용). 반면 finder·verifier·orchestrator·프롬프트·도구·dedup·`libs/llm`·`libs/agent-harness`·`libs/sandbox`는 `ee/` 경로가 아니며 `@libs/ee` import가 없다고 조사됐다(grep). 일부 비-ee 파일에 `@license Kodus Tech. All rights reserved.` 헤더가 있어 경로 규칙과 해석이 어긋날 수 있다([05](05-dependencies.md#license)).

## 경로 사전 (짧은 이름 → 풀 경로)

- `finder.agent.ts`, `verifier.agent.ts`, `core-agent-loop.adapter.ts`: `libs/code-review/infrastructure/agents/core/`
- `prompt-builder.ts`, `verifier-prompt.ts`, `dedup-prompt.ts`: `libs/code-review/infrastructure/agents/prompts/`
- `review-orchestrator.service.ts`: `libs/code-review/infrastructure/agents/`
- `agent-tools.factory.ts`: `libs/code-review/infrastructure/agents/engine/`
- `finder-tools.adapter.ts`: `libs/code-review/infrastructure/agents/adapters/`
- `base-code-review-agent.provider.ts`, `kody-rules-agent.provider.ts`: `libs/code-review/infrastructure/agents/providers/`
- `kody-rules-sharded.judge.ts`, `context-fit-planner.ts`, `batch-runner.ts`, `claim-checker.ts`: `libs/code-review/infrastructure/agents/collaborators/`
- `agent-review.stage.ts`, `build-orchestrator-input.ts`, `create-sandbox.stage.ts`, `validate-suggestions.stage.ts`: `libs/code-review/pipeline/stages/`
- `ai-sdk-agent-runner.ts`: `libs/agent-harness/infrastructure/ai-sdk/`; `verification-pass.ts`: `libs/agent-harness/infrastructure/orchestration/`; `*.policy.ts`: `libs/agent-harness/infrastructure/policies/`
- `graph-context.service.ts`, `kodus-graph-cli.ts`: `libs/code-review/infrastructure/adapters/services/graph/`
- `classify-severity.ts`, `format-suggestion-content.ts`, `coverage-ledger.ts`, `dedup-prompt.ts`, `file-priority-scorer.ts`: `libs/code-review/infrastructure/agents/engine/`
- `finding-mapper.ts`: `libs/code-review/infrastructure/agents/collaborators/`; `overflow-recovering-runner.ts`: `libs/code-review/infrastructure/agents/core/`
- `retry-policy.ts`, `model-failover.ts`, `structured-review-call.ts`, `llm-call.ts`, `agent-run-context.ts`, `agent-loop-call.ts`, `llm.ts`: `libs/llm/`
- `astGraph.repository.ts`, `repository.repository.ts`: `libs/code-review/infrastructure/adapters/repositories/` (`repository.model.ts`는 `schemas/`)
- `documentation-search-exa.service.ts`, `commentManager.service.ts`, `sandboxSyntaxValidator.service.ts`: `libs/code-review/infrastructure/adapters/services/`
- `local-sandbox.service.ts`, `e2b-sandbox.service.ts`, `null-sandbox.service.ts`: `libs/sandbox/infrastructure/providers/`
- `generic-skill-runner.service.ts`: `libs/agents/skills/`; `businessRulesValidationAgent.ts`: `libs/agents/infrastructure/services/agents/business-rules-validation/`
- `implementation-verification.processor.ts`: `libs/code-review/workflow/`
