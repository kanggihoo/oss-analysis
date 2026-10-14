# 문맥 확보·반복·검증 전략 비교

- 작성일: 2026-10-13
- 정정 반영: 2026-10-13 보고서 정정 반영
- 대상 SHA (`../repos.lock.tsv`와 일치)
  - pr-agent: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63`
  - open-code-review: `57273a9ea28548b94b3d67c247ff13a63c01fc47`
  - kodus-ai: `45676c5fe7ac016b6206ccea006e459677d92842`
- 기준: 각 레포 `reports/<repo>/01`·`02` (근거 줄 번호는 보고서에 있다. 여기서는 대표 위치만 적고 보고서 절로 링크한다). 정적 추적만 했고 실행 확인은 없다. 점수·순위는 매기지 않는다.
- 표기: 대표 위치 뒤의 **(재확인)** 은 이 문서를 쓰며 `repos/<repo>`를 읽기 전용으로 직접 다시 열어 보고서 주장과 일치함을 확인했다는 뜻이다. 표시가 없는 위치는 보고서에서 가져온 값이며, kodus-ai 02~05 줄 번호는 2026-10-13 보고서 정정에서 약 650개 인용을 모두 열어 범위·식별자를 대조하고 약 30건을 정정했다. 다만 **01 전체와 02의 긴 범위(`agent-tools.factory.ts:300-1757`, `agent-review.stage.ts:992-1508` 등), 03·04·05의 일부 긴 범위는 아직 재대조하지 못했으므로**(각 문서 머리, [`next.md`](../reports/kodus-ai/next.md) 참조) 그 범위는 인용 전에 다시 열 것.
- 전제: LiteLLM(pr-agent), `anthropic-sdk-go`/`openai-go`(open-code-review), AI SDK `generateText`(kodus-ai) 같은 호출 라이브러리를 쓴다는 사실은 구조 판단 근거가 아니다. 아래는 실제 호출 경로에 도구 호출 반복이 있는지로 구분했다.

---

## 1. 다섯 가지 방식 구분 (레포별 해당 항목)

GUIDE 4절 Q4의 구분표를 3개 레포에 같은 틀로 채웠다. 각 칸에 보고서 링크를 붙였다.

| 구분 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| **고정 문맥 확장** (프로그램이 자동 수집) | **있음, 가장 두껍다.** 번호 붙은 diff + 같은 파일 hunk 주변 줄(앞 5/뒤 1, 동적 문맥 최대 10줄), PR 제목·설명, 티켓, 지침 파일(`AGENTS.md`), 이전 finding, CI 아티팩트. 대표: `algo/git_patch_processing.py:78-234`(재확인), `tools/pr_reviewer.py:237-277`. [02#q3 3.1](../reports/pr-agent/02-context-loop-verify.md#q3) | **있음, 좁다.** 파일 1개의 `git diff -U3` + 다른 변경 파일의 **경로 목록**(내용 없음) + 경로별 규칙 체크리스트 + `--background` 텍스트 + (50줄 이상 변경 시) 같은 모델이 도구 없이 만든 계획. 문맥 확장 알고리즘 없음. 대표: `internal/diff/git.go:17`(재확인), `internal/agent/agent.go:467-487`(재확인). [02#q3 3.1](../reports/open-code-review/02-context-loop-verify.md#q3) | **있음, 확장 알고리즘은 없다.** 번호 붙은 diff(Provider hunk 그대로), 커버리지 대상 목록, PR 제목·본문 앞 500자, 커밋, 이전 라운드 결정, 규칙·메모리, **call graph(`<CallGraph>`)**. 대표: `prompt-builder.ts:629-670,690-697`, `build-orchestrator-input.ts:87-159`. [02#q3 3.1](../reports/kodus-ai/02-context-loop-verify.md#q3), 주변 줄 확장 부재: [01#q2 2.3](../reports/kodus-ai/01-execution-and-diff.md#q2) |
| **동적 탐색** (모델이 요청) | **없음.** 도구를 주는 코드가 없다. 저장소 파일을 읽는 경로는 있으나 `repo_context_files`에 적힌 **고정 경로**만 프로그램이 읽는다. [02#q3 3.1~3.2](../reports/pr-agent/02-context-loop-verify.md#q3) | **있음.** `file_read`, `file_find`, `code_search`(`git grep`), `file_read_diff`. 대표: `internal/agent/agent.go:963-1074`, `internal/tool/*.go`. [02#q3 3.3](../reports/open-code-review/02-context-loop-verify.md#q3) | **조건부 있음.** 샌드박스 체크아웃이 있을 때만 `grep`(rg), `readFile`, `listDir`, `findFile`, `checkTypes`, `getCallers`. 없으면 도구 없이 diff만. 대표: `agent-tools.factory.ts:191-193`(재확인: `remoteCommands` 없으면 `{}`). [02#q3 3.2·3.6](../reports/kodus-ai/02-context-loop-verify.md#q3) |
| **재시도 / fallback** | **있음.** 같은 모델 재시도 2회(tenacity), 모델 체인 순차 교체(`config.model` → `fallback_models`), 예산 초과 시 `FallbackEligibleError`로 더 큰 창 모델, `/improve` 실패 청크만 뒤 모델로 복구. 대표: `litellm_ai_handler.py:149,285-299`, `pr_processing.py:830-872`. [02#q4 4.1·4.2](../reports/pr-agent/02-context-loop-verify.md#q4) | **최소.** SDK 내부 재시도 옵션(`WithMaxRetries(5)`)만. **모델 교체 fallback 없음.** "도구를 호출하라"는 재요청은 루프 라운드를 소모. Plan·압축·위치 재해석·필터 실패는 각각 "없이 진행/원본 유지/줄 번호 0/통과"로 넘어감. 대표: `internal/llm/client.go:299,495`, `agent.go:478-487`. [02#q4 4.1·4.6](../reports/open-code-review/02-context-loop-verify.md#q4) | **있음.** AI SDK 스텝당 `maxRetries 3`, 1회 호출은 TRANSIENT만 1회 재발행, 모델 failover(primary→fallback 1단, 첫 루프 스텝이 나간 뒤에는 불가), `OverflowRecoveringRunner`(작은 창으로 1회). 대표: `libs/llm/agent-loop-call.ts:57,210`(재확인: `maxRetries`·`stepCountIs`), `retry-policy.ts:20-35`. [02#q4 4.1·4.4](../reports/kodus-ai/02-context-loop-verify.md#q4) |
| **다중 호출** (같은 프롬프트, 다른 입력) | **있음.** `/improve`는 기본으로 파일 묶음(≤3) 병렬 호출, `/review`는 옵션(`enable_large_pr_chunking`, 기본 false). 청크는 서로의 입력·출력을 보지 못함. 대표: `pr_reviewer.py:981-1077`, `pr_processing.py:423-552`. [02#q4 4.1](../reports/pr-agent/02-context-loop-verify.md#q4), [02#q3 3.4](../reports/pr-agent/02-context-loop-verify.md#q3) | **있음.** 파일 1개 = 하위 작업, 동시 8. 대화는 파일마다 완전 분리. 대표: `agent.go:374-445`, `:494-516`. [02#q3 3.5](../reports/open-code-review/02-context-loop-verify.md#q3) | **있음(조건부).** 토큰 예산 초과 시 파일 배치별 finder+verifier를 순차 실행, Kody Rules는 파일당 1회 + PR 1회. 대표: `base-code-review-agent.provider.ts:421-505`, `context-fit-planner.ts:237-282`. [02#q4 4.1](../reports/kodus-ai/02-context-loop-verify.md#q4) |
| **다단계 파이프라인** (단계마다 다른 프롬프트, 고정 순서) | **`/improve`만**: 생성 → self-reflect(점수). `/review`는 단일 프롬프트 + 코드 후처리. 대표: `pr_code_suggestions.py:1062-1081`(재확인). [02#q4 4.1](../reports/pr-agent/02-context-loop-verify.md#q4) | **있음.** 파일마다 Plan(조건부, 도구 없음) → Main 루프 → 위치 재해석(조건부) → Review Filter(도구 없음). 대표: `agent.go:467-540`(재확인). [02#q4 4.1](../reports/open-code-review/02-context-loop-verify.md#q4) | **있음, 가장 길다.** 약 18단계: 비즈니스 로직 → 샌드박스 → 분석기 → `AgentReviewStage`(finder→verifier→dedup→severity→포맷) → 댓글 생성·게시. 대표: `code-review-pipeline.strategy.ts:70-109`(재확인). [02#q4 4.1](../reports/kodus-ai/02-context-loop-verify.md#q4) |
| **Agent Loop** (도구 호출 → 결과를 대화에 넣어 재추론) | **없음.** `[system, user]` 두 메시지, 요청 kwargs에 도구 없음. 유지보수자 주석도 "single-shot ... no tool-use loop". 대표: `litellm_ai_handler.py:2863-2868,2987-2991`, `configuration.toml:579-591`. [02#q4](../reports/pr-agent/02-context-loop-verify.md#q4) | **있음, 한 곳(Main 루프).** Plan·Filter·압축·위치 재해석은 도구 없는 단발 호출. 대표: `agent.go:848-958`(재확인). [02#q4](../reports/open-code-review/02-context-loop-verify.md#q4) | **있음, 여러 곳.** finder, 후보별 verifier, 증거 게이트 재검증, synthesis rescue, heavy resample, 비즈니스 로직 fetcher(MCP). Kody Rules 판정·dedup·severity·포맷은 루프 아님. 대표: `finder.agent.ts:207-258`(재확인), `verifier.agent.ts:288-372`(재확인). [02#q4](../reports/kodus-ai/02-context-loop-verify.md#q4) |

**읽는 법**: 세 레포는 같은 스펙트럼의 점이 아니라 **다른 축에서 강하다.** pr-agent는 "무엇을 어떤 규칙으로 미리 넣을까"(고정 문맥)에, open-code-review는 "모델이 파일 하나를 조사하는 한 번의 대화"(루프 골격)에, kodus-ai는 "루프를 서비스 파이프라인 안에서 어떻게 감싸는가"(예산·게이트·큐)에 코드가 집중돼 있다.

---

## 2. 반복의 단위와 종료 조건

### 2.1 반복의 단위

| 레포 | 반복의 단위 | 한 번의 반복이 의미하는 것 | 반복 횟수의 상한 |
|---|---|---|---|
| pr-agent | (Agent Loop 없음) 호출 1회 / 청크 1개 / 모델 체인의 모델 1개 | 같은 입력을 모델만 바꿔 다시 보내거나, 다른 파일 묶음을 병렬로 보냄. 앞 호출의 결과를 대화에 넣어 다시 추론하는 일은 없음 | 청크 `max_number_of_calls=3`, 같은 모델 재시도 2회, 체인 길이 ([02#q4 4.3](../reports/pr-agent/02-context-loop-verify.md#q4)) |
| open-code-review | **LLM 호출 1회 = 라운드 1** (파일당 Main 루프) | 모델이 도구를 골라 호출 → 결과가 `tool` 메시지로 쌓임 → 다시 호출. 파일마다 대화가 분리됨 | 파일당 30라운드(기본, `--max-tools` 10 이상으로 덮어씀) ([02#q4 4.5](../reports/open-code-review/02-context-loop-verify.md#q4)) |
| kodus-ai | **에이전트 실행 1회 안의 `generateText` 다단계(스텝)** — finder는 (카테고리 × 파일 배치)당 1회, verifier는 **후보 1건당 1회** | 도구 호출 스텝의 누적. 상위 단위는 finder 1회 → 후보 N건 → verifier N회(동시성 4) | finder fast 3~4 / normal 20 / security·performance 12 / deep 100 스텝, verifier light 5 / full 10 스텝 ([02#q4 4.2](../reports/kodus-ai/02-context-loop-verify.md#q4)) |

### 2.2 open-code-review Main 루프의 종료 조건 (보고서 4.5절 표)

| 종료 조건 | 동작 | 오류 여부 | 대표 위치 |
|---|---|---|---|
| **정상 종료** | 모델이 `task_done` 호출 → 같은 응답의 나머지 호출을 실행한 뒤 `break`. `state` 값(`DONE`/`FAILED`)은 읽지 않음 | 정상 | `agent.go:907-934`(재확인), `:969-971` |
| **도구 호출 없음** | **종료가 아니다.** "도구를 호출하라" 문구를 user로 추가하고 `continue`. 연속 빈 라운드 가드(3회)는 이 분기 앞에서 `continue`하므로 적용되지 않아, 모델이 텍스트만 내면 최대 라운드까지 소모 | 정상 흐름(라운드 소모) | `agent.go:893-901`(재확인) |
| **최대 반복** | 라운드 카운터가 0이 되면 루프 종료. **`nil` 반환**이고 `warnings`에 기록하지 않음(stdout 문구만). 수집된 코멘트는 유지되고 Review Filter로 진행 | 오류 아님 | `agent.go:849,953-957`(재확인), `flags.go:170-177` |
| **토큰 한도(사전)** | 초기 프롬프트가 `MAX_TOKENS × 80%`(47110) 초과면 해당 파일 건너뜀(`token_threshold_exceeded` 경고). 단일 파일 diff가 그 한도를 넘으면 파일 통째 제외 | 경고 | `agent.go:518-530`, `:682-705` |
| **토큰 한도(루프 중)** | 압축 후에도 80% 이상이면 `break`("Context compression exceeded threshold") | 오류 아님, 경고 기록 없음 | `agent.go:946-950`(재확인), `compression.go:163-171` |
| **시간 한도** | 파일 하위 작업 전체(plan+main+filter)에 `--timeout`(기본 10분). 루프 맨 앞 `ctx.Done()` → `ctx.Err()` 반환 → `subtask_error` 경고. 쌓인 코멘트는 남고 Review Filter는 건너뜀 | 경고 | `agent.go:394-419,854-858` |
| **LLM 요청 한도** | 요청당 5분(SDK 옵션) | - | `internal/llm/client.go:284-301` |
| **취소** | 루트 ctx는 `context.Background()`뿐, 신호 처리 없음. Ctrl-C는 프로세스 종료(결과는 마지막에 출력되므로 부분 결과 유실, 추론) | 해당 없음 | `review_cmd.go:146` |
| **모델 오류** | SDK 재시도 5회 후에도 오류면 하위 작업 실패. 모든 파일이 실패하면 실행 전체 오류 | 경고/오류 | `agent.go:873-877,418-424,439-442` |
| **"충분히 조사했다"** | 프로그램이 판정하지 않음. 모델의 `task_done`이 유일한 신호 | - | `main_task_system.md:22-25` |

미확인(보고서 `next.md`): SDK 내부 재시도의 오류 범위·백오프, 압축이 큰 diff에서 조기 종료를 일으키는지(코드 어긋남은 확인, 결과는 추론), "도구 호출 없음" 반복으로 30라운드를 소모하는 비율(실행 안 함).

### 2.3 kodus-ai의 finder / verifier 구조

```text
AgentReviewStage (샌드박스 체크아웃이 있으면 도구 활성, 없으면 self-contained)
 └─ finder  (카테고리별 병렬, 파일 배치마다)           ← Agent Loop #1
     │   입력: system + user(번호 붙은 diff, call graph, PR 텍스트, 커버리지 목록)
     │   도구: grep / readFile / listDir / findFile / checkTypes / getCallers / (searchDocs, readReference)
     │   종료: submitResult 호출 (CompletionGatePolicy 통과 시) 또는 stepCountIs(maxSteps)
     │   보강: 산문 복구(구조화 1회), synthesis rescue(루프 재실행), heavy resample×2
     ▼
   후보 finding N건
     └─ verifier  (후보마다 1회, 동시성 4)               ← Agent Loop #2 (후보당)
         │   입력: 파일·줄·claim·코드 + 같은 PR의 이전 결정
         │   도구: finder와 같은 도구 레지스트리 (읽기 캐시 공유는 추론)
         │   깊이: 후보 confidence ≥5 이면 light(5스텝), <5 이면 full(10스텝)
         │   종료: submitVerdict 또는 마지막 2스텝에서 텍스트 JSON 판정 강제
         │   결과: 반증했을 때만 DROP. 판정 불가·예외는 KEEP(기본값)
         ▼
       증거 게이트: finder가 읽지 않은 파일의 finding은 forceFull verifier로 재검증
     ▼
   → dedup(LLM + 임베딩 가드) → severity 재분류 → 포맷 → committable 검증 → 게시
```

(구조 근거: [02#q4 4.1·4.2](../reports/kodus-ai/02-context-loop-verify.md#q4), 코드 재확인: `finder.agent.ts:225-258·668-740`, `verifier.agent.ts:288-372`, `code-review-pipeline.strategy.ts:70-109`)

**kodus-ai 종료 조건 (보고서 4.3절 요약)**

| 조건 | 동작 | 검증 수준 |
|---|---|---|
| 정상 종료 | `submitResult`/`submitVerdict` 호출 → 게이트 통과 시 루프 정지. 마지막 2스텝은 제출 도구만 활성화(`ForceFinalizePolicy`) | 코드 확인 |
| 완료 게이트 | **`fileTiers`가 있을 때만** critical 대상이 남아 있으면 제출을 거부. 티어 맵이 없으면(`criticalTotal=0`) 거부하지 않음 — `completion-gate.policy.ts:81-96`에서 `criticalTotal > 0 && criticalPending > 0`일 때만 veto(재확인) | 코드 확인 |
| 도구 호출 없음 | 텍스트만 내면 AI SDK 루프가 끝남(SDK 동작은 레포 밖). finder가 finding을 산문으로 쓰면 구조화 복구 1회 | 코드 확인 + **추론** |
| 최대 반복 | `stepCountIs(maxSteps)` | 코드 확인 |
| 토큰·금액 한도 | **실행당 상한 없음.** 압축·오버플로 복구는 있으나 비용은 기록만 | 코드 확인(부정 grep) |
| 시간 한도 | 모델 1왕복 20분, 에이전트 80분(finder+verify가 하나의 컨텍스트 공유), 잡 105분 | 코드 확인 (주석이 인용한 운영 수치는 주석 인용일 뿐 직접 측정 아님) |
| 취소 | 부모 잡 `signal`이 에이전트에 합성됨. **파이프라인 실행기는 `signal`을 확인하지 않음** | 코드 확인 + **추론** |
| 모델 오류 | primary→fallback 1회, 스텝당 재시도 3. finder 실패는 `RunState{error}`, **verifier 실패는 KEEP(fail-open)** | 코드 확인 |
| "충분히 조사했다" | 모델의 `submitResult`가 유일한 신호(하드 게이트는 위 조건에서만) | 코드 확인 |
| (결함 후보) incomplete 판정 | base provider가 `finishReason`의 `'timeout'`/`'tool-calls'`로 incomplete를 판단하는데, core 어댑터는 `RunStatus`(`completed/stopped/budget-exhausted/error`)를 `finishReason`에 넣음. 값이 맞지 않아 이 경로에서 `result.incomplete`에 도달하지 못해 보임 — `base-code-review-agent.provider.ts:727-730`, `core-agent-loop.adapter.ts:348`, `run-state.contract.ts:63` | 두 위치와 `RunStatus` 타입을 직접 읽어 값 불일치 확인(재확인). 실제 도달 불가 여부는 호출 경로 추적 없이는 **추론** |

### 2.4 종료 조건 3개 레포 크로스 비교

| 종료 조건 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| 정상 종료 | 응답 수신 → YAML 파싱 성공 → 후처리·게시 | `task_done` | `submitResult`/`submitVerdict` (+완료 게이트) |
| 도구 호출 없음 | 해당 없음(도구 개념 없음) | 종료 아님, 재요청 + 라운드 소모 | 루프 종료(SDK 동작, 추론) |
| 최대 반복 | 호출 수 상한(청크 3, 재시도 2) | 30라운드(오류 아닌 `nil`) | 에이전트별 `maxSteps` |
| 토큰 한도 | 사전 예산 → 압축/청크/`FallbackEligibleError`, 입력은 `max_model_tokens=32000` 상한 | 프롬프트 80% 초과면 파일 제외, 루프 중 80%면 중단 | 실행당 상한 없음, 압축·오버플로 복구 |
| 시간 한도 | 호출당 120초, 리뷰 전체 제한은 미확인 | 파일 10분, 요청 5분 | 왕복 20분 / 에이전트 80분 / 잡 105분 |
| 취소 | 명시적 취소 API 없음 | 신호 처리 없음 | 에이전트는 취소됨, 파이프라인 실행기는 신호 미확인(추론) |
| 모델 오류 | fallback 체인 → 소진 시 실패 댓글 | SDK 재시도 5 → 파일 실패(모델 교체 없음) | 스텝 재시도 3 + failover 1단, finder 실패는 기록, verifier 실패는 KEEP |
| "충분히 조사했다" | 해당 없음 | 모델의 `task_done`뿐 | 모델의 `submitResult`뿐(조건부 게이트) |

---

## 3. 검증 단계의 독립성 비교

| 항목 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| **검증 단계가 별도 LLM 호출인가** | `/review`: **없음.** `/improve`: 있음(self-reflect 호출 1회, 제안 전체 대상) | 있음(Review Filter, 파일당 1회) | 있음(후보 1건당 verifier 1회) |
| **생성과 같은 모델인가** | `model_reasoning`을 지정하면 다른 모델, 아니면 같은 모델 체인 | **같은 모델·같은 클라이언트**(`a.args.Model`) | **같은 모델 슬롯**(`modelId`·`fallbackModelId`가 finder와 동일, 재확인) |
| **생성 대화·문맥을 공유하는가** | 대화 기록은 공유 안 함, 입력 diff는 같음 | 공유 안 함(새 메시지 2개) — Main의 도구 결과·계획을 보지 못함 | 새 실행·새 메시지. 프롬프트는 같은 계열이고 **읽기 도구 캐시는 공유**(추론) |
| **추가 파일을 읽을 수 있는가** | **불가**(diff와 제안 문자열만) | **불가**(`Tools` 없이 호출 + 프롬프트가 diff만으로 판정하라고 제한, 재확인) | **가능**(finder와 같은 도구, light 5/full 10 스텝) |
| **기본 판정 방향** | 점수 임계값 미만만 제거, 반성 실패 시 기본 점수 7로 통과 | diff로 **틀렸다고 입증된 것만** 제거, 판단 불가면 의심스러워도 통과 | 명시적 **반증**일 때만 제거, "의심"은 KEEP("When in doubt, KEEP") |
| **검증 실패 시** | 모든 제안이 점수 7로 통과 | 파싱 실패·호출 오류면 아무것도 제거 안 함 | 판정 파싱 불가·예외면 KEEP |
| **무엇을 못 거르는가** | 호출부·다른 파일 근거 | 다른 파일의 로직·런타임 동작이 걸린 주장(설계상 통과) | 같은 모델의 상관된 오류(추론), 근거 위치를 강제하지 않음(보고서에 근거 위치 강제 구현은 없음) |
| **단위** | 제안 목록 1회 | 파일별 1회, 다른 파일의 코멘트와 비교 안 함 | 후보별, 이후 파이프라인에서 PR 전체 dedup |
| **중복 제거** | 청크 병합은 정규화 동일 문자열만, 재실행은 finding fingerprint | 파일 간·재실행 간 **없음** | LLM dedup + 임베딩 가드(실패 시 병합 안 함), 같은 PR 이전 결정을 프롬프트로 |
| **evals와 실제 경로 연결** | 없음 | 미발견(README 수치는 재현 경로 미확인) | 있음(프로덕션 TS를 로드, 도구 출력은 녹화본 재생, golden 매칭은 LLM 판정) |
| **링크** | [02#q5](../reports/pr-agent/02-context-loop-verify.md#q5) | [02#q5](../reports/open-code-review/02-context-loop-verify.md#q5) | [02#q5](../reports/kodus-ai/02-context-loop-verify.md#q5) |

**해석 (분석자 정리)**

- 세 검증기 모두 **"생성 단계와 모델이 다르고, 도구로 근거를 다시 찾으며, 근거 위치 없이는 확정을 막는" 독립 검증자가 아니다.** 독립성을 얻는 방법이 서로 다르다. open-code-review는 **문맥을 줄여서**(diff만) 생성자의 확신에 끌려가지 않게 하지만 그 대가로 다른 파일 근거는 검증하지 못한다. kodus-ai는 **도구를 줘서** 근거를 다시 찾게 하지만 같은 모델이라 오류가 상관될 수 있고 기본값이 KEEP이다. pr-agent는 `/improve`에서만 점수를 다시 매긴다.
- 세 곳 모두 검증 실패 시 **통과 쪽(fail-open)** 으로 기운다(pr-agent 점수 7, open-code-review 아무것도 제거 안 함, kodus-ai KEEP). 검증기를 늘려도 오탐이 줄어드는 정도는 보고서만으로는 알 수 없고(세 곳 모두 오탐률 실측 없음) 우리 평가 세트가 필요하다.

---

## 4. 사용자가 겪은 "고정 주변 줄 확장의 한계"는 코드상 어디서 오는가

### 4.1 pr-agent: 한계의 원인

사용자 체감("고정 diff 주변 줄 확장만으로는 문맥 부족")은 코드와 일치한다는 것이 pr-agent 보고서의 결론이다. 단정 대신 코드 위치로 분해하면 다음과 같다.

| # | 원인 | 코드 위치 | 보고서 | 검증 |
|---|---|---|---|---|
| 1 | 확장이 **같은 파일의 hunk 주변**으로 한정. 기본 앞 5줄/뒤 1줄, 동적 문맥은 위로 최대 10줄. 다른 파일의 호출부·구현체는 구조상 입력에 못 들어옴 | `algo/git_patch_processing.py:78-234`, `settings/configuration.toml:58-67`(재확인) | [01#q2b 3.3](../reports/pr-agent/01-execution-and-diff.md#q2b) | 코드 확인 |
| 2 | "함수 경계"는 AST가 아니라 **git이 hunk 헤더에 붙인 함수 문자열을 `section_header in line`(부분 문자열 포함)으로 찾는 휴리스틱**. 찾지 못하면 고정 5줄. 문서의 "코드 구조에 따라 동적으로"는 이 구현이며 모델 주도가 아님 | `git_patch_processing.py:137-160`(재확인) | [01#q2b 3.3·3.9](../reports/pr-agent/01-execution-and-diff.md#q2b) | 코드 확인 |
| 3 | base 본문이 비면 **확장 자체를 하지 않음**: 새 파일, 변경 파일 50개 초과(본문을 빈 문자열로 둠), 본문 조회 실패 | `git_patch_processing.py:35`, `git_provider.py:52`, `github_provider.py:496-503` | [01#q2a 2.3](../reports/pr-agent/01-execution-and-diff.md#q2a) | 코드 확인 |
| 4 | **토큰 예산을 넘으면 확장을 포기**하고 git 기본 3줄 patch를 압축해 사용 | `pr_processing.py:259-298` | [01#q2b 3.3](../reports/pr-agent/01-execution-and-diff.md#q2b) | 코드 확인 |
| 5 | **모델에게 도구가 없다.** 요청은 `[system, user]`뿐이라 모델이 "호출부를 보여 달라"고 요청할 수단이 없음. 저장소의 다른 파일을 읽는 코드는 있으나 호스트가 설정한 고정 경로(`repo_context_files`)만 읽음 | `algo/ai_handlers/litellm_ai_handler.py:2863-2868,2987-2991`, `algo/repo_context.py:337` | [02#q3 3.1·3.2](../reports/pr-agent/02-context-loop-verify.md#q3) | 코드 확인(부재는 grep 근거) |
| 6 | **프롬프트가 추측을 막는다**: "너는 변경된 코드 조각(diff hunk)만 본다", "diff 문맥에서 영향받는 코드 경로를 식별하지 못하면 다른 코드가 깨질 것이라고 추측하지 말라" | `settings/pr_reviewer_prompts.toml:17,24` | [02#q3 3.3](../reports/pr-agent/02-context-loop-verify.md#q3) | 코드 확인 |
| 7 | 청크 분할 시 파일 묶음이 **독립 호출**이라 같은 모듈의 두 파일이 다른 묶음으로 갈라지면 서로를 못 봄 | `pr_reviewer.py:1042-1048`, `pr_processing.py:423-552` | [02#q3 3.4](../reports/pr-agent/02-context-loop-verify.md#q3) | 코드 확인 |

보고서의 정적 추적 예(`apply_discount` 반환 타입 변경, 호출부는 hunk에서 7줄 떨어진 `checkout()`)는 "호출부 결함은 구조적으로 다룰 수 없거나 억제된다"로 정리되지만, 실제 모델 출력은 실행하지 않았으므로 **추론**이다([01#q2b 3.8](../reports/pr-agent/01-execution-and-diff.md#q2b)).

### 4.2 open-code-review: 같은 문제를 어떻게 다르게 푸는가

| 구분 | 내용 | 보고서 |
|---|---|---|
| 고정 문맥은 pr-agent보다 **더 좁다** | `git diff -U3`만 사용하고 문맥 확장 알고리즘이 없음(`internal/diff/git.go:17`, 재확인). 더 넓은 문맥은 **모델이 `file_read`로 요청**해야 얻음. `file_read` 도구 설명이 hunk 헤더에서 `start_line = m-50, end_line = m+n+50`을 계산하라고 모델에게 안내 | [01#q2 2.3](../reports/open-code-review/01-execution-and-diff.md#q2) |
| 호출부를 **모델이 직접 찾는다** | `code_search`(`git grep -n -F`)로 호출부를 열거하고 `file_read`로 맥락을 읽음. 단 `git grep`은 문자열 일치이며 오버로드·동명 함수 구분은 모델 몫 | [02#q3 3.3·3.4](../reports/open-code-review/02-context-loop-verify.md#q3) (실행 예는 미실행) |
| 그런데 **보고 대상은 현재 diff로 한정** | 시스템 프롬프트: "문맥 도구는 이해 목적으로만 쓴다. 다른 파일에서 발견한 문제는 코멘트 대상으로 삼으면 안 된다" (`main_task_system.md:18-20`). 변경 안 한 호출부에서 발견한 결함은 설계상 코멘트하지 않음. 변경한 쪽이 호출부와 맞지 않는지 확인하는 용도로만 읽음 | [02#q3 3.2](../reports/open-code-review/02-context-loop-verify.md#q3) |
| 파일 단위 하위 작업 → 파일 간 결함은 **보장 로직 없음** | 파일마다 대화가 완전히 분리되고 마지막에 PR 전체를 보는 종합 패스가 없음. 한 파일의 하위 작업이 다른 파일을 조사하려면 자기 도구 예산(30라운드, 컨텍스트 80%)을 써야 함. README의 "관련 파일 번들링"은 코드에 없음 | [02#q3 3.5](../reports/open-code-review/02-context-loop-verify.md#q3), [05 README↔코드 차이](../reports/open-code-review/05-dependencies.md) |
| 큰 변경 | 분할·압축 없이 **큰 파일을 통째 제외**(47110 토큰 초과). 제외된 파일은 다른 파일의 변경 목록에서도 빠짐 | [01#q2 2.2·2.6](../reports/open-code-review/01-execution-and-diff.md#q2) |

### 4.3 kodus-ai: 같은 문제를 어떻게 다르게 푸는가

| 구분 | 내용 | 보고서 |
|---|---|---|
| 주변 줄 확장 알고리즘이 **활성 경로에 없다** | diff는 Provider hunk 그대로(Azure만 context 3). 레거시 파일 단위 코드에만 확장 흔적이 있고 주입처가 없음. 오케스트레이터는 에이전트 입력에서 파일 본문을 **제거**하고 모델이 `readFile`로 읽게 함 | [01#q2 2.1·2.3](../reports/kodus-ai/01-execution-and-diff.md#q2) |
| 호출부는 **두 경로**로 확보 | (a) 고정: `kodus-graph`(외부 npm CLI)가 만든 call graph를 `<CallGraph>`로 프롬프트에 주입(힌트: "도구로 다시 확인하라"). (b) 동적: 모델이 `grep(rg)`로 호출자를 찾고 `readFile`로 맥락을 읽음. finder 프롬프트가 "변경된 각 메서드의 호출 체인을 따라가라"고 절차를 지시 | [02#q3 3.3·3.4](../reports/kodus-ai/02-context-loop-verify.md#q3) |
| **전제 조건**: 샌드박스 체크아웃 | 체크아웃이 없으면 도구 없이 diff(+파일 본문 inline)만 봄 → 이때는 pr-agent와 비슷한 "고정 문맥만" 상태가 됨. `null` 샌드박스에서는 도구는 있으나 호출이 모두 오류가 될 수 있음(추론) | [02#q3 3.6](../reports/kodus-ai/02-context-loop-verify.md#q3) |
| 그런데 **보고 대상은 변경 줄에 묶임** | finder 프롬프트 "Root cause must be in lines added or modified by this PR"(`prompt-builder.ts:569`), finding이 어떤 hunk와도 겹치지 않으면 코드가 `DISCARDED_BY_CODE_DIFF`로 폐기. 다른 파일의 결함은 변경된 트리거 줄에 앵커될 때만 보고됨(보고서의 **추론**) | [02#q3 3.5](../reports/kodus-ai/02-context-loop-verify.md#q3), [02#q5 5.1](../reports/kodus-ai/02-context-loop-verify.md#q5) |
| 큰 PR | 파일 순서대로 탐욕적으로 배치를 만들고 **각 배치에서 에이전트는 그 배치의 diff만** 봄(call graph·도구는 전체 체크아웃 대상) | [01#q2 2.3](../reports/kodus-ai/01-execution-and-diff.md#q2), [02#q3 3.5](../reports/kodus-ai/02-context-loop-verify.md#q3) |

### 4.4 세 해법 비교: "변경하지 않은 호출부" 문제

| 질문 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| 호출부를 누가 고르는가 | 프로그램의 규칙(같은 파일 hunk 근처만) | 모델(`git grep` 결과 중) | 프로그램(call graph) + 모델(`rg`) |
| 다른 파일의 호출부가 입력에 들어올 수 있는가 | **불가**(구조상) | 가능(모델이 요청할 때만) | 가능(call graph 고정 주입 + 모델 요청), 단 샌드박스가 있을 때 |
| 심볼 의미를 도구가 이해하는가 | 해당 없음 | 아니오(텍스트 검색) | 부분(call graph는 외부 CLI의 정적 분석 결과, `getCallers`는 그 문자열 조회. 파서 소스는 이 레포에 없어 미확인) |
| 호출부에서 찾은 결함을 보고할 수 있는가 | 프롬프트가 추측 금지 | **설계상 불가**(다른 파일 발견 무시) | 변경 hunk와 겹쳐야만 가능(추론) |
| 비용 구조 | 호출 1회(청크 시 ≤3) | 파일 수 × 최대 30라운드, 총 비용 상한 없음 | finder + 후보 수 × verifier, 실행당 비용 상한 없음 |
| 실패 모드 | 호출부 결함을 우연히만 발견 | 라운드·컨텍스트 한도에서 조기 종료(압축 어긋남 가능성, 추론), 도구 호출 없음 반복 | 체크아웃 불가 시 diff-only로 조용히 강등(경고 `SANDBOX_UNAVAILABLE`), `incomplete` 판정 경로 불일치 가능 |

**핵심 관찰 (분석자 정리)**: 세 곳 모두 **탐색 능력과 보고 정책이 분리돼 있다.** open-code-review와 kodus-ai는 모델이 호출부를 찾아 읽을 수 있는데도 프롬프트·후처리가 보고 대상을 변경 줄로 묶는다(오탐 억제 의도로 읽히나 보고서가 개발자 의도를 밝힌 곳은 `review_filter` 프롬프트의 "에이전트가 볼 수 있는 문맥을 검증자는 못 본다" 정도이고, 보고 정책의 의도는 **추론**이다). 따라서 "동적 탐색을 갖췄다"와 "변경하지 않은 호출부의 결함을 리뷰에 올린다"는 다른 질문이다. 후자를 원하면 탐색 도구보다 먼저 이 정책(프롬프트의 앵커 조건, hunk 겹침 필터, 검증기의 통과 기준)을 바꿔야 한다. 이 정책을 바꿨을 때 오탐이 얼마나 늘지는 세 보고서 어디에도 측정이 없다(open-code-review `next.md` 질문 4번).

---

## 5. 이 문서의 검증 강도와 보고서 간 불일치

### 5.1 이 문서를 쓰며 직접 다시 확인한 것 (읽기 전용, 실행 없음)

세 레포 `HEAD`가 `repos.lock.tsv`와 일치함을 확인한 뒤 다음을 열었다. 모두 보고서 주장과 일치했다.

| 레포 | 확인한 것 |
|---|---|
| open-code-review | `internal/tool/definitions.go`(이름 목록), `agent.go`의 Plan 생략 조건, 도구 없음 분기, 최대 라운드 소진 시 `nil` 반환, Review Filter의 `ChatRequest`에 `Tools` 필드 없음, `internal/diff/git.go`의 `DiffContextLines` |
| kodus-ai | `code-review-pipeline.strategy.ts` 단계 목록, `agent-tools.factory.ts` 도구 레지스트리 가드, `finder.agent.ts` 정책 구성·verifier 호출·증거 게이트, `verifier.agent.ts` 모델·도구·깊이 구성, `completion-gate.policy.ts`의 `criticalTotal` 조건, `agent-loop-call.ts`의 `stepCountIs`, `run-state.contract.ts`, `base-code-review-agent.provider.ts`·`core-agent-loop.adapter.ts`의 `finishReason` |
| pr-agent | `configuration.toml` 확장 기본값, `git_patch_processing.py`의 동적 문맥 탐색 루프, `litellm_ai_handler.py` 요청 kwargs 시작부, `pr_code_suggestions.py`의 생성→self-reflect 흐름 |

직접 열지 않아 보고서 값 그대로 인용한 것: pr-agent의 `pr_processing.py`·`pr_reviewer.py`·프롬프트 줄 번호, open-code-review의 압축·위치 해석·시간 한도 줄 번호, kodus-ai의 `prompt-builder.ts`·오케스트레이터·샌드박스·dedup 줄 번호(kodus-ai 02~05는 2026-10-13에 보고서에서 인용 범위를 재대조했으나 01 전체와 긴 범위 일부는 미대조, 위 머리 참조).

### 5.2 보고서 간 모순·검증 약점

| # | 내용 | 영향 |
|---|---|---|
| 1 | open-code-review 도구 수 표기: **정정 완료.** 기준은 [OC 00 1절](../reports/open-code-review/00-overview.md)(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개, Provider 등록 5개, `task_done`은 직접 처리). 이 문서의 "모델이 호출하는 도구 6개"와 일치 | 정정 완료, 영향 없음 |
| 2 | kodus-ai `incomplete` 판정 불일치와 "도구 호출 없음 시 루프 종료"는 보고서가 **추론**으로 표시한 항목이다. 이 문서에서 값 불일치까지는 직접 확인했으나 실제 도달 불가 여부와 SDK 종료 동작은 확인하지 못했다. | 종료 조건 표에 추론으로 표기 |
| 3 | kodus-ai 02의 verifier 독립성 서술("읽기 캐시 공유")은 보고서도 추론이다. 같은 모델 슬롯은 코드로 확인했다. | 3절 표에 추론으로 표기 |
| 4 | pr-agent는 "고정 문맥이 `commit_messages_str`을 수집하지만 `/review` 프롬프트에 쓰지 않음" 등 문서·코드 차이가 이미 기록돼 있다([pr-agent 00 7절](../reports/pr-agent/00-overview.md)). 이 문서는 코드 기준 값을 사용했다. | 영향 없음 |
| 5 | 세 보고서 모두 정적 추적이다. 호출부 탐색 실행 예(pr-agent `apply_discount`, open-code-review `Load()` 시그니처, kodus-ai 함수 `F`)는 모두 **실행하지 않은 예상 경로**다. 실제 모델이 그 순서로 호출하는지는 확인되지 않았다. | 4절의 "~할 수 있다"는 가능성 표현으로만 읽을 것 |
| 6 | open-code-review 앵커 표기(`{#q3}`)는 일부 렌더러에서 앵커로 동작하지 않을 수 있다. | 링크가 안 맞으면 절 제목으로 이동 |
