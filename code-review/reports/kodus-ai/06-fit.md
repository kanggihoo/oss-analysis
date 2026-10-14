# kodus-ai — 우리 서비스 적용 (Q12, 분석자 의견)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q12 (+ 알려진 이슈·우선 읽을 파일)
- 검증 수준 요약: 이 문서의 판단은 대부분 **의견**이다. 근거가 되는 사실은 01~05의 표를 가리킨다. 다만 2026-10-13 정정에서 **3절 "비-ee 모듈의 재사용 결합" 표와 라이선스 헤더 범위는 코드를 다시 열어 확인한 사실**이다(코드 확인, 근거는 그 절의 표). 나머지는 추론·의견이다.
- 실행 여부: 정적 추적만. 아래 제안은 구현·검증하지 않았다.
- **이 문서 전체가 분석자 의견이다. 라이선스 항목은 법률 자문이 아니다.**

우리 서비스 목표(의견의 기준): GitHub/GitLab PR·MR 웹훅 → diff + 변경하지 않은 관련 기존 코드 + Jira 요구사항 + 팀 규칙 + 과거 피드백을 함께 리뷰, **팀 간 격리 필수**.

## 1. 한눈에: 무엇을 어디서 가져오나

| 영역 | Kodus 상태(사실 요약) | 가져올 가치 | 이유(의견) | 근거 문서 |
|---|---|---|---|---|
| SaaS 실행 기반(웹훅→outbox→큐→워커, 재시도, 리퍼, 드레인) | 구체적·견고. 단 재시도 후 파이프라인 오류가 삼켜짐 | **높음(패턴 재구현)** | 가장 많은 운영 사고가 코드에 녹아 있음(주석에 사고 이력). 비-ee 경로이나 AGPL | [04](04-saas-and-isolation.md) |
| 리뷰 알고리즘(finder+verifier Agent Loop, 샌드박스 도구, 예산·완료 게이트) | 활성. 동적 탐색 있음, verifier 기본 KEEP | **높음(설계 참고+AGPL 모듈 선택 재사용. 재사용 시 3절의 결합 비용 발생)** | 우리가 원하는 "변경하지 않은 호출부 탐색"을 이미 구현. `libs/agent-harness`·`libs/llm`·`libs/sandbox`는 ee가 아니나 **`@libs/core`·`@libs/common`·`@libs/code-review` 파일 일부에 의존**(3절 표) | [02](02-context-loop-verify.md) |
| 규칙 관리 | Mongo 조직 문서·범위·승인·동기화 있음. 우선순위·버전·팀 범위 없음. **구현이 ee** | **중간(스키마·UX 아이디어만)** | 그대로 쓸 수 없고 우리 요구(팀 범위, 우선순위)를 채우지도 못함 | [03 Q8](03-incremental-memory-rules.md#q8) |
| 피드백 메모리 | **비활성**(코드·문서 모두). 같은 PR 이력만 활성 | **낮음(데이터 모델 아이디어만)** | 가져올 동작 구현이 없음. 임베딩 클러스터링은 호출되지 않는 코드 | [03 Q7](03-incremental-memory-rules.md#q7) |
| Jira | 직접 연동 없음, MCP 경유 별도 단계(diff 한정 판정) | **낮음~중간** | 입력 삽입 패턴(`LoadExternalContextStage`)과 task-context capability는 참고 가능 | [03 Q9](03-incremental-memory-rules.md#q9) |

### 최종 질문에 대한 의견 요약

가져올 가치는 **SaaS 실행 기반과 리뷰 알고리즘**에 있다. 규칙 관리는 구조만, 피드백 메모리는 사실상 가져올 것이 없다. 외부 서비스(E2B·Morph·Exa·Langfuse) 없이도 리뷰 경로는 돌아가지만 **라이선스 때문에 코드 그대로의 재사용 범위가 좁다**: 파이프라인 조립·실행 진입·설정 로더·규칙 서비스가 Enterprise 경로(`ee/`, `.ee.`)다([05 6.3](05-dependencies.md#license)).

## 2. 가져올 것 / 직접 만들 것 / 운영해야 할 의존성

### 2.1 가져올 것 (패턴 재구현 우선, 코드 재사용은 라이선스 검토 후)

| 항목 | 위치 | 가져오는 방식(의견) |
|---|---|---|
| 트랜잭셔널 outbox + inbox + 지연 재시도 + DLX 파킹 | `libs/core/workflow/infrastructure/workflow-job-queue.service.ts:51-103`, `outbox-relay.service.ts`, `workflow-job-consumer.service.ts:387-546`, `libs/core/infrastructure/queue/rabbitmq-error.handler.ts:83-185` | **패턴 재구현.** 같은 설계를 새로 쓰는 편이 안전. 참고로 조직 컬럼을 outbox/inbox에도 추가하고 DLQ 소비자·알림을 만들 것 |
| 스테일 잡·inbox 리퍼, 드레인, 헬스 가드 | `outbox-relay.service.ts:500-585,342-481`, `apps/worker/src/worker-drain.service.ts:5-133`, `worker-health-guard.service.ts:43-46` | 패턴 재구현 |
| Agent harness 정책(예산·압축·완료 게이트·강제 제출) | `libs/agent-harness/infrastructure/policies/*`, `ai-sdk-agent-runner.ts:63-404` | 비-ee. 라이선스(AGPL) 검토 후 모듈 단위 재사용 또는 재구현. 정책 이름과 책임이 그대로 설계 문서가 됨 |
| 도구 레지스트리와 읽기 전용 샌드박스 도구 | `libs/code-review/infrastructure/agents/engine/agent-tools.factory.ts:300-986`, `libs/sandbox/*` | **재구현 권장**: `getCallers`는 call graph 문자열 파서일 뿐이라(코드 주석이 "0 tool calls in 170+ runs") 실시간 심볼 조회는 우리가 설계 |
| finder→후보별 verifier 구조와 "반증해야 제거" 프롬프트 | `finder.agent.ts:672-738`, `verifier-prompt.ts:17-47` | **아이디어 재구현.** 단 독립 모델·독립 문맥 verifier를 추가하는 것은 우리가 설계(Kodus verifier는 같은 슬롯) |
| 샌드박스 리스 키·무효화 이벤트 | `create-sandbox.stage.ts:98-102`, `githubPullRequest.handler.ts:229-309` | 키 구조(`org:repo:pr`)는 참고. 로컬 클론은 **컨테이너 격리 없이 워커 호스트에서 실행**되므로 그대로 쓰지 말 것 |
| 증분 리뷰 상태(`lastAnalyzedCommit`+고아 커밋 폴백) | `validate-new-commits.stage.ts:52-179` | 패턴 재구현 |
| 라인 매핑·유효 줄 스냅·위치 불일치 재시도 | `libs/common/utils/patch.ts:208-245`, `agent-review.stage.ts:135-180,224-286`, `commentManager.service.ts:1515-1652` | 알고리즘 재구현(GitLab position 구성 포함) |
| 사람 PR 댓글에서 규칙 생성 파이프라인 | `commentAnalysis.service.ts:220-345,500-583` | 아이디어(자기 댓글 제외, 필터→생성→dedup→품질 필터) |
| `PreviousReviewDecisions` 프롬프트 설계 | `prompt-builder.ts:415-419` | 같은 PR 중복 억제 아이디어 |

### 2.2 직접 만들 것

| 항목 | 이유 |
|---|---|
| **웹훅 서명 검증**(GitHub `x-hub-signature-256`, GitLab `x-gitlab-token`, 플랫폼별 조직 단위 시크릿) | Kodus에는 없다([04 1.3](04-saas-and-isolation.md)) |
| **테넌트 격리 강화**: 큐·outbox·inbox에 조직 컬럼/라우팅, `repositories`·AST 조회에 조직 조건, 캐시 키에 조직 접두사, 같은 외부 저장소를 여러 조직이 연결할 때의 규칙, Postgres RLS 또는 쿼리 계층 강제 | Kodus는 앱 수준 격리([04 3절](04-saas-and-isolation.md)) |
| **Jira 요구사항 Context Provider와 조건별 근거 탐색** | Kodus는 diff 한정 1회 판정([03 Q9](03-incremental-memory-rules.md#q9)) |
| **PR 간 피드백 메모리**(쓰기+읽기) | Kodus는 비활성. 답글·resolve·수정 신호 저장과 신뢰도·무효화 설계가 필요([03 Q7](03-incremental-memory-rules.md#q7)) |
| **팀 범위 규칙·우선순위·충돌 해결·버전 이력** | Kodus에 없음. 규칙은 조직 문서이고 팀 키가 있는 것은 설정(`parameters`)뿐이다([03 8.1절 범위 키 표](03-incremental-memory-rules.md#q8-scope)) |
| **Head SHA 고정과 실행 중 취소**: 시작 시 SHA를 고정해 모든 읽기를 그 SHA로, 새 푸시가 오면 이전 실행 취소(`AbortSignal`을 실행기까지 전파) | Kodus는 하나로 고정하지 않음([01 2.2](01-execution-and-diff.md#q2)) |
| **파이프라인 실패 → 잡 재시도 정책**: 오류를 삼키지 않고 분류해 재시도/영구 실패 구분 | Kodus는 대부분 COMPLETED로 끝남([04 2.3](04-saas-and-isolation.md)) |
| **격리된 샌드박스**(컨테이너/마이크로VM, 조직별 네트워크 정책) | 로컬 샌드박스는 호스트 실행(주석이 RCE 위험 명시). 도구 허용 목록으로 완화했으나 공격면은 남음 |

### 2.3 운영해야 할 의존성 (Kodus 구조를 따를 경우)

PostgreSQL(+vector 확장은 임베딩을 쓸 때만), MongoDB, RabbitMQ(delayed-message 플러그인. 이 레포의 `docker-compose.prod.yml`에는 서비스가 없어 외부에서 제공해야 한다, [05 4.1절](05-dependencies.md#rabbitmq-compose)), `git`·`ripgrep`, LLM API 한 곳, (선택) E2B/Morph/Exa/Langfuse/Sentry. Redis는 쓰지 않는다([05 3절](05-dependencies.md)). MongoDB와 PostgreSQL을 둘 다 운영하는 비용을 줄이려면 우리는 한 저장소로 합치는 설계를 고려할 수 있다(의견).

## 3. 재사용 vs 재구현 판단

| 대상 | 판단 | 이유 |
|---|---|---|
| `libs/core/workflow/**`(큐·outbox·inbox) | 재구현(패턴 복제) | 비-ee이지만 AGPL. 우리 서비스 코드로 가져오면 소스 공개 의무 검토 필요. 구조가 단순해 재구현 비용이 낮음 |
| `libs/agent-harness/**`, `libs/llm/**` | **선택적 재사용 후보(결합 비용 있음)** | ee가 아니며 비-spec 소스에 `@libs/ee` import가 없다(재확인). 두 모듈은 서로 import하고(순환), `libs/llm`은 `@libs/core/log`·`@libs/common/utils`의 파일에 의존한다(3절 표). `@license` 헤더는 이 두 디렉터리에 **없다**(전수 grep, 3절). AGPL 적용 여부는 법무 판단 |
| `libs/sandbox/**` | 재구현 또는 격리 강화 후 재사용 | 같은 이유+로컬 호스트 실행 위험. 추가로 `@libs/core`(로거·enum·락·Mongo 베이스)와 **`@libs/code-review` 서비스 파일 2개**에 의존(3절 표) |
| `libs/code-review/**` 파이프라인·에이전트 | 아이디어만 | 파이프라인 조립이 ee 파일에 의존, 18단계가 Kodus의 도메인(체크런·요약·크레딧)과 결합 |
| `libs/ee/**`, `*.provider.ee.ts` | **재사용 불가**(상용 라이선스 필요) | `license_ee.md`: 평가 목적 외 사용에는 라이선스 필요 |
| `libs/kodyRules/**`(비-ee 일부)와 `libs/ee/kodyRules/**` | 스키마·UX 아이디어만 | 서비스 구현이 ee |
| `libs/llm/**` BYOK 슬롯 해석 | 설계 참고 | 실제 슬롯 해석은 ee의 `permissionValidation.service.ts`를 경유 |

라이선스 요약(법률 자문 아님): 코드 복사 재사용이 가능한 부분은 **AGPL-3.0 비-ee 경로**이며, AGPL 코드를 SaaS에 포함하면 소스 공개 의무가 생길 수 있다. 그래서 상용 SaaS를 목표로 하면 "패턴·아이디어 재구현"이 기본이고 코드 재사용은 법무 검토가 선행되어야 한다. `ee/`는 평가 외 사용에 상용 계약이 필요하다. `@license … All rights reserved` 헤더는 **`libs/code-review`(5개)·`libs/core`(7개, 그중 3개는 `.ee.ts`)·`libs/kodyFineTuning`(1개)·`libs/ee`(5개) 등 18개 소스 파일**에만 있고 `libs/agent-harness`·`libs/llm`·`libs/sandbox`에는 없다(전수 grep, 아래 3.2절과 [05 6.1](05-dependencies.md#license)). 경로 규칙상 AGPL인 파일 중 10개에 이 헤더가 있다는 점은 법무 확인 사항이다.

<a id="reuse-coupling"></a>
### 3.1 비-ee 모듈의 재사용 결합 (2026-10-13 재확인, 코드 확인)

`libs/agent-harness`·`libs/llm`·`libs/sandbox`의 비-spec `.ts`(각 28·105·15개)에서 `from '@libs/...'`·`@apps`·`import(`·`require(`·`../../..` 상대 경로를 grep으로 전수 조사하고 해당 줄을 열어 확인했다. **`@libs/ee`는 세 디렉터리 모두 비-spec 소스에서 import하지 않는다.** 그러나 아래 의존이 있어 "디렉터리만 복사"로는 컴파일되지 않는다.

| 모듈 | 의존 대상(밖) | 위치 | 비고 |
|---|---|---|---|
| `libs/agent-harness` | `@libs/llm/{llm, ai-sdk-usage, byok-config, structured-output-repair, token-estimate, prompt-cache}` | `infrastructure/ai-sdk/ai-sdk-agent-runner.ts:18-20`, `infrastructure/verify/llm-verdict.ts:32`, `infrastructure/compression/token-estimator.ts:20`, `infrastructure/ai-sdk/prompt-cache.ts:7` | 하네스는 `libs/llm` 없이 못 쓴다 |
| `libs/llm` | `@libs/agent-harness/domain/contracts/run-state.contract`(타입) | `context-overflow.ts:16` | 위와 합쳐 **순환 의존**. 둘을 함께 가져가야 한다 |
| `libs/llm` | `@libs/core/log/logger` | `byok-limiter.ts:11`, `byok-model-wrapper.ts:31`, `reasoning-options.ts:10`, `structured-review-call.ts:68`, `model-failover.ts:20` | 로거. `libs/core/log/logger.ts`는 `pino`·OpenTelemetry만 import(추가 `@libs` 의존 없음) |
| `libs/llm` | `@libs/core/log/langfuse` | `reasoning-options.ts:11`, `model-invocation.ts:46`, `structured-review-call.ts:67`, `agent-loop-call.ts:48` | Langfuse 트레이싱 모듈. `@langfuse/*`·`ai` 패키지 필요 |
| `libs/llm` | `@libs/common/utils/crypto` | `model-builders.ts:16`, `byok-to-vercel.ts:11`, `migrate-byok-config.ts:27` | 이 파일은 **import 시점에 `API_CRYPTO_KEY`(32바이트 hex)를 검사하고 틀리면 예외**(`libs/common/utils/crypto.ts:5-9`). 이 파일을 로드하는 진입점에서만 해당하며 어느 진입점이 로드하는지는 추적하지 않음(추론) |
| `libs/llm` | `@libs/common/utils/parent-signal-compose` | `agent-run-context.ts:14` | 작은 유틸 |
| `libs/sandbox` | `@libs/core/log/logger`, `@libs/core/domain/enums`(`PlatformType`) | `local-sandbox.service.ts:2-3`, `e2b-sandbox.service.ts:1-2`, `git-auth-header.ts:1`, `domain/contracts/sandbox.provider.ts:1` | |
| `libs/sandbox` | `@libs/core/infrastructure/repositories/model/mongodb`(`CoreDocument`), `@libs/core/workflow/infrastructure/distributed-lock.service`, `@libs/common/utils/polling` | `infrastructure/repositories/schemas/sandbox-lease.model.ts:1`, `infrastructure/services/sandbox-lease-reaper.service.ts:9`, `infrastructure/services/sandbox-lease-manager.service.ts:20` | 리스가 Mongo 문서이고 reaper가 Postgres advisory 락 서비스를 쓴다 |
| `libs/sandbox` | **`@libs/code-review/infrastructure/adapters/services/collectCrossFileContexts.service`**(`RemoteCommands` 타입), **`.../shell-quote`**(`shSingleQuote`) | `local-sandbox.service.ts:29`, `e2b-sandbox.service.ts:14-15`, `domain/contracts/sandbox.provider.ts:2` | `libs/code-review`의 파일 2개. 첫째는 파일 머리 주석대로 **타입만 남은 파일**(서비스는 제거됨, import는 `@libs/common/utils/prompts/...` 타입 1개, `collectCrossFileContexts.service.ts:1-17`), 둘째는 13줄 함수 1개(`shell-quote.ts:12`). 즉 `libs/code-review` 전체가 아니라 이 2개 파일(또는 `RemoteCommands` 타입 이동)만 필요하다 |

재사용 비용 요약(코드 확인 + 추론):
- 세 모듈을 쓰려면 **`libs/core/log`(logger·langfuse), `libs/core/domain/enums`, `libs/core/infrastructure/repositories/model/mongodb`, `libs/core/workflow/infrastructure/distributed-lock.service.ts`, `libs/common/utils`의 `crypto`·`parent-signal-compose`·`polling`, `libs/code-review`의 2개 파일**이 함께 필요하다. 모두 비-ee 경로이므로 라이선스 경계상 새 ee 의존은 생기지 않지만 **AGPL 적용 범위가 세 모듈에서 이 파일들로 넓어진다**.
- `libs/llm`이 `@libs/ee`를 import하는 곳은 **테스트 파일뿐**이다(`libs/llm/strict-wire-schema.spec.ts:31,42`가 `@libs/ee/codeBase/...`, `@libs/ee/analytics-warehouse/...`를 import, `:306`은 ee 경로 문자열). 테스트까지 가져오면 ee 코드가 필요하다.
- 3절 표의 `libs/llm/** BYOK 슬롯 해석` 행이 말하는 "슬롯 해석은 ee의 `permissionValidation.service.ts`를 경유"([05 6.3](05-dependencies.md#license))는 `libs/llm` 밖 호출자 쪽 결합이다. 즉 라이브러리 내부 결합은 위 표가 전부지만, 모델 슬롯을 만드는 **호출 측 배선은 ee에 있다**.
- `libs/core/log/` 디렉터리 전체를 복사하면 `observability.service.ts:15,20`이 `@libs/llm`을 되돌아 import하고(`@libs/core/observability`, `@libs/core/infrastructure/config/types`도 import, `:5,10`) `token-usage-tu.ts:20`이 `@libs/common/utils/canonical-model`을 import한다. `libs/llm`·`libs/sandbox`가 실제로 쓰는 것은 `logger.ts`·`langfuse.ts` 두 파일이며 이 둘은 `@libs/*` import가 없다(해당 파일의 import 줄 확인). 필요한 파일만 가져와야 순환이 늘지 않는다.

<a id="license-header"></a>
### 3.2 `@license … All rights reserved` 헤더의 실제 범위 (2026-10-13 전수 grep)

소스 전체(`node_modules`·`.git` 제외)에서 `@license`를 검색한 결과 21개 파일이 나왔고 그중 3개(`apps/web/.../@licenses/page.tsx`, `scripts/security-benchmark/dataset.json`, `tests/e2e/playwright/stripe-billing.mjs`)는 헤더가 아닌 우연한 일치다. 실제 헤더는 **18개 소스 파일**이며 **`libs/agent-harness`·`libs/llm`·`libs/sandbox`에는 없다**(`All rights reserved`도 이 세 디렉터리에서 일치 없음). 헤더 `@license` 줄 번호는 아래와 같다.

| 구분 | 파일(`@license` 줄) |
|---|---|
| 경로가 `libs/ee/` (5) | `libs/ee/codeReview/fileReviewContextPreparation/file-review-context-preparation.service.ts:3`, `libs/ee/configs/environment/environment.dev.ts:2`, `.../environment/index.ts:2`, `libs/ee/kodyRules/service/kody-rules-validation.service.ts:2`, `libs/ee/license/license.module.ts:2` |
| 파일명이 `.ee.ts` (3) | `libs/core/providers/code-review-pipeline.provider.ee.ts:2`, `file-analyzer.provider.ee.ts:2`, `pipeline.provider.ee.ts:2` |
| **경로·파일명에 ee 표지 없음 (10)** | `libs/code-review/domain/contracts/FileAnalysisRule.contract.ts:2`, `libs/code-review/infrastructure/adapters/services/code-analysis/file/base-file-review.abstract.ts:3`, `.../file/noop-file-review.service.ts:2`, `libs/code-review/infrastructure/adapters/services/codeReviewHandlerService.service.ts:2`, `libs/code-review/pipeline/strategy/code-review-pipeline.strategy.ts:2`, `libs/core/domain/interfaces/file-review-context-preparation.interface.ts:2`, `libs/core/domain/interfaces/kody-fine-tuning-context-preparation.interface.ts:2`, `libs/core/infrastructure/pipeline/interfaces/pipeline-strategy.interface.ts:2`, `libs/core/infrastructure/pipeline/services/pipeline-factory.service.ts:2`, `libs/kodyFineTuning/infrastructure/adapters/services/fineTuningContext/fine-tuning.service.ts:3` |

해석(의견, 법률 자문 아님): `license.md:5-10`의 경로 규칙을 그대로 적용하면 마지막 10개 파일은 AGPL 대상인데 헤더는 "All rights reserved"여서 두 표시가 어긋난다. 이 10개는 모두 **리뷰 파이프라인 조립·파일 분석 계약·파인튜닝 컨텍스트**에 관련된 파일이고 우리가 재사용 후보로 본 세 모듈(`agent-harness`·`llm`·`sandbox`)에는 헤더가 없다. 따라서 세 모듈 재사용 판단에서 헤더는 쟁점이 아니지만, 위 3.1절에서 의존하는 파일(`libs/core/log/{logger,langfuse}.ts`, `libs/core/domain/enums`, `libs/core/infrastructure/repositories/model/mongodb`, `libs/core/workflow/infrastructure/distributed-lock.service.ts`, `libs/common/utils/{crypto,parent-signal-compose,polling}`, `libs/code-review`의 2개 파일)도 위 18개 목록에 없다. 그 외 `libs/ee/linked-repositories/*`는 `@license` 대신 "Enterprise Code — see `license_ee.md`" 문구와 자체 `LICENSE` 파일을 쓴다(`libs/ee/linked-repositories/index.ts:1-5`, `LICENSE`).

## 4. 새로 설계할 경계 (의견)

### 4.1 동적 탐색 (검색 도구의 실시간 심볼 이해)

Kodus는 `grep`/`readFile` + 사전 계산 call graph 문자열이다. 우리는 (a) PR 시작 시 **SHA를 고정한 읽기 전용 체크아웃**, (b) 도구 호출 결과에 `path@sha:line`을 붙이는 증거 객체, (c) `getCallers`/`getImplementations`를 심볼 인덱스(tree-sitter·LSP)에 연결하는 경계를 별도 인터페이스로 둔다. Kodus의 도구 레지스트리 패턴(`agent-tools.factory.ts`)이 좋은 출발점이다.

### 4.2 PR 간 메모리

쓰기 이벤트(답글·반박·resolve·수정·승인)와 읽기 함수를 **처음부터 함께** 설계한다. Kodus 사례의 교훈은 (1) 반응(👍/👎)만으로는 이유가 없어 학습에 부족(공식 문서가 인정, `kody_learning.mdx:10`), (2) 쓰기만 있고 읽기가 연결되지 않은 모듈이 남으면 죽은 코드가 된다는 점이다. 메모리 항목에는 조직·팀·저장소·경로·출처 PR/댓글/SHA·신뢰도·만료·충돌 처리를 넣고, 읽기는 **조직+팀 필터가 쿼리 계층에서 강제**되도록 한다.

### 4.3 Jira 근거 검증 (Q9 확장 지점)

[03 9.3](03-incremental-memory-rules.md#q9)의 확장 지점을 따른다: (1) 요구사항 수집은 `fetchTaskContext`와 같은 capability 계약 뒤에 Jira REST/MCP 제공자를 교체 가능하게 두고 (2) `LoadExternalContextStage`처럼 메인 리뷰 입력에 주입하며 (3) BusinessLogic 단계를 샌드박스 뒤로 옮겨 기준별 루프(`grep/readFile`)로 구현 근거를 찾고 (4) "이번 PR 범위의 기준"과 "티켓 전체 기준"을 분리하는 분류 단계를 추가한다.

### 4.4 팀 격리

[04 3절](04-saas-and-isolation.md)의 위험 후보 5개를 설계 요구사항으로 바꾼다: 웹훅 서명, 큐/outbox의 테넌트 필드, 캐시 키, 조직 조건 없는 조회 금지, 같은 저장소의 다중 조직 연결 규칙.

## 5. 우선 읽을 파일 (순서 제안)

1. `libs/code-review/pipeline/strategy/code-review-pipeline.strategy.ts` (단계 목록)
2. `libs/core/workflow/infrastructure/workflow-job-queue.service.ts`, `workflow-job-consumer.service.ts`, `libs/core/infrastructure/queue/rabbitmq-error.handler.ts`
3. `libs/automation/infrastructure/adapters/services/processAutomation/strategies/automationCodeReview.ts`
4. `libs/code-review/pipeline/stages/validate-new-commits.stage.ts`, `fetch-changed-files.stage.ts`, `create-sandbox.stage.ts`
5. `libs/code-review/infrastructure/agents/core/finder.agent.ts`, `verifier.agent.ts`, `prompts/prompt-builder.ts`, `engine/agent-tools.factory.ts`
6. `libs/agent-harness/infrastructure/ai-sdk/ai-sdk-agent-runner.ts`, `policies/*`
7. `libs/ee/kodyRules/service/kody-rules-validation.service.ts`(읽기만, 평가 목적), `libs/code-review/pipeline/stages/business-logic-validation.stage.ts`

## 6. 알려진 이슈·위험 (관찰, 모두 정적 추적)

| 이슈 | 위치 | 수준 |
|---|---|---|
| 웹훅 서명 검증 부재(Azure 외) | `apps/webhooks/src/controllers/*.ts` | 코드 확인 |
| Postgres 장애 시 웹훅 유실(200 선반환) | `github.controller.ts:53-87` | 코드 확인 |
| 파이프라인 오류가 삼켜져 잡 COMPLETED, 큐 재시도 없음 | `pipeline-executor.service.ts:211-285`, `automationCodeReview.ts:329-337`, `code-review-job-processor.service.ts:238` | 코드 확인+추론 |
| 실행 중 새 푸시 시 취소 없음, 비명령 충돌 시 새 실행이 버려짐 | `automationCodeReview.ts:185-246,394-396` | 코드 확인+추론 |
| PR 락 TTL 60초(갱신 없음)로 105분 리뷰 동안 execution 행 검사에만 의존 | `distributed-lock.service.ts:9-35`, `automationCodeReview.ts:42,170-173` | 코드 확인+추론 |
| 게시 전 기존 댓글 조회 없음(재시도 중복 가능) | `commentManager.service.ts:1283-1294` | 추론 |
| GitLab OAuth refresh 교환 없음 | `gitlab.service.ts:1130-1162` | 코드 확인+추론 |
| GitLab OAuth·GitHub 설치 토큰 스냅샷 평문 저장, CBC에 MAC 없음, 전역 단일 키 | `github.service.ts:544-579`, `crypto.ts:4-34` | 코드 확인 |
| 로컬 샌드박스가 컨테이너 격리 없이 워커 호스트에서 클론·실행(코드 주석이 RCE 위험 명시, 허용 목록 완화) | `local-sandbox.service.ts:515-545` | 코드 확인 |
| BYOK 슬롯 락이 PG 연결을 105분까지 점유할 수 있어 풀 12 대비 고갈 위험 | `code-review-job-processor.service.ts:204-206,300-319`, `worker.module.ts:78` | 추론 |
| `repositories`/AST 조회에 조직 조건 없음, GitHub 콘텐츠 캐시 키가 owner/repo 기준 | `agent-review.stage.ts:634-645`, `github.service.ts:5003-5005,6203` | 코드 확인+추론 |
| 디렉터리 규칙의 PR 전체 누수 가능성 | `kody-rules-validation.service.ts:144-150` | 추론 |
| `result.incomplete` 도달 불가 가능성(`finishReason` 값 불일치) | `base-code-review-agent.provider.ts:727-730`, `core-agent-loop.adapter.ts:346-348` | 추론 |
| `RunAnalyzersStage.backfillMissingPatches`가 immer로 얼려진 객체에 할당할 가능성 | `run-analyzers.stage.ts:274-279` | 추론(런타임 미확인) |
| 문서·주석 불일치 다수 | [00 7절](00-overview.md) | 코드 확인 |
