# kodus-ai — SaaS: 인증·큐·테넌트 격리·장애 복구 (Q10)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q10
- 검증 수준 요약(검증 열이 있는 표의 행을 스크립트로 센 값, 2026-10-13 재집계. 복수 표기 행은 각 수준에 중복 계산하고 검증 열이 없는 표·본문 서술은 제외): 코드 확인 66 / 실행 확인 0 / 추론 8 / 미확인 4
- 실행 여부: **정적 추적만**. 큐·락·재시도는 코드로만 읽었고 브로커·DB를 띄우지 않았다.
- 줄 번호 재대조(2026-10-13): 약 155개 중 약 150개를 직접 열어 확인했고 어긋난 인용 4건(Morph, `assertTeamInCallerOrganization` 파일, `critical` 근거, 이벤트 브리지)과 약한 인용 몇 건을 고쳤다. **앵커만 확인한 범위**: `outbox-relay.service.ts:632-859`(최대 시도·백오프·하트비트 줄만), `worker.module.ts:49-143`, `workflow.module.ts:121-148`(특정 줄만). 1.1·1.2절의 `integrations` 유일성·설치 토큰 재발급·E2B 토큰 전달은 [07](07-credentials.md)에 맞춰 정정했다.
- 표기: "전달됨(carried)"은 조직 ID가 인자·페이로드로 넘어간다는 뜻이고, "강제됨(enforced)"은 쿼리·가드·키가 실제로 그 조건으로 제한한다는 뜻이다. 둘을 구분했다. 줄 번호 중 큐 정책·인증 일부는 조사 에이전트가 연 값이며 핵심 근거는 작성자가 재대조했다(웹훅 컨트롤러, `TenantScopeGuard`, `crypto.ts`, 분산 락, 소비자, 에러 핸들러, 큐 인자).

## 1. 인증·자격증명·웹훅 검증

### 1.1 자격증명 보관

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 저장 위치 | Postgres `auth_integrations.authDetails`(jsonb), org·team FK. `integrations`(platform, org, team)에 연결. **(org, team, platform)당 1행은 DB가 보장하지 않는다**: `(platform, org, team)`은 일반 인덱스일 뿐 유일 제약이 없고 마이그레이션에도 없다(2026-10-13 정정, 근거 [07 2.1절](07-credentials.md)). 1행 유지는 앱 로직(`handleIntegration`의 update/create 분기)에 의존 | `libs/integrations/infrastructure/adapters/repositories/schemas/authIntegration.model.ts:9-27`, `integration.model.ts:19-59`(인덱스 `:25-31`), `libs/core/infrastructure/database/typeorm/migrations/1774034826247-indexes.ts:10`, `1763402134271-baseline.ts:103-115` | 코드 확인 |
| 조회 | `integrationService.findOne({organization.uuid, team.uuid, platform})`. 리포지토리는 `organization.uuid`가 없으면 `undefined` 반환 | `libs/integrations/infrastructure/adapters/services/integration.service.ts:125-144`, `.../repositories/integration.repository.ts:77-124` | 코드 확인 |
| 암호화 | AES-256-CBC, 랜덤 IV, 출력 `iv:hex`. **MAC/인증 태그 없음**. 단일 전역 키 `API_CRYPTO_KEY`(32바이트 hex, import 시점 검증). 회전 코드 없음 | `libs/common/utils/crypto.ts:4-34` | 코드 확인 |
| 적용 범위 | PAT·BYOK 키는 `encrypt()`. **GitLab OAuth 토큰과 GitHub 설치 토큰 스냅샷은 평문**으로 `authDetails`에 저장 | 아래 표 | 코드 확인 |

### 1.2 Provider별 자격증명

| Provider | 저장 형태 | 수명·갱신 | 사용처 | 근거 | 검증 |
|---|---|---|---|---|---|
| GitHub App(`AuthMode.OAUTH`) | `installationId` 등 + 온보딩 시 설치 토큰 `authToken`(평문 스냅샷) | 리뷰·clone·GraphQL 경로는 저장된 `authToken`을 읽지 않고 `installationId`로 `@octokit/auth-app`을 통해 **재발급**한다(2026-10-13 정정: 추론에서 코드 확인으로 격상, [07 3.1절](07-credentials.md)). 저장된 스냅샷은 사실상 쓰기 전용 | `getInstallationAuthentication` | `libs/platform/infrastructure/adapters/services/github/github.service.ts:544-579,2611-2657`, 재발급 호출부 `:3170-3183,6502-6527` | 코드 확인 |
| GitHub App 자체 | **인스턴스 하나의 전역 App**(`API_GITHUB_APP_ID`, `API_GITHUB_PRIVATE_KEY`, `API_GITHUB_CLIENT_SECRET`)이 모든 테넌트를 서비스 | - | `createAppAuth` | `github.service.ts:367-428` | 코드 확인 |
| GitHub 설치 토큰 캐시 | 프로세스 메모리 캐시, 키는 **`installationId` 원문**(Kodus 조직 접두사 없음), TTL 50분(`github.service.ts:174`), 캐시 적중 시마다 `rateLimit.get()`으로 유효성 확인. `generateAndCacheNewToken`은 키 `installationId`로 저장 | 설치 ID는 GitHub 전역 유일이라 충돌은 두 조직이 같은 설치를 공유할 때만(추론) | `getCachedToken` | `github.service.ts:2659-2696` | 코드 확인 |
| GitHub PAT | `encrypt(token)`+(GHES용) `host` | 갱신 없음 | 사용 시 `decrypt` | `github.service.ts:650-658,3300-3306` | 코드 확인 |
| GitLab OAuth | **평문** `accessToken`·`refreshToken`·`tokenType`·`scope`(+`host`) | `authorization_code`만 있고 **refresh 교환 코드를 찾지 못했다**(`refresh_token|refreshToken|grant_type` 검색). GitLab 토큰이 만료되면 재인증 전까지 실패할 수 있다(추론, 만료 시간은 외부 지식) | `@gitbeaker/rest` 클라이언트 | `libs/platform/infrastructure/adapters/services/gitlab.service.ts:344-356,1130-1162` | 코드 확인 / 추론 |
| GitLab PAT | `encrypt(token)` | 갱신 없음 | - | `gitlab.service.ts:1195-1216` | 코드 확인 |
| Bitbucket / Azure / Forgejo | `encrypt(token)` | 갱신 없음 | Basic 헤더 등 | `.../bitbucket/bitbucket-cloud.service.ts:3897`, `azureRepos.service.ts:2671`, `forgejo.service.ts:1058` | 코드 확인 |
| 제3자로의 토큰 노출 | E2B를 쓰면 클론 인증 헤더 `GIT_AUTH_HEADER`를 **그 명령의 `envs`로만** 전달하지만, 명령 문자열이 `git -c http.extraHeader="$GIT_AUTH_HEADER" fetch …`라 쉘이 변수를 풀어 헤더가 **git 프로세스 argv에 남는다**(VM 안. 코드 주석도 "the E2B clone path still passes it via `-c`"라고 인정). 로컬 샌드박스는 `GIT_CONFIG_*` 환경변수라 argv에 남지 않는다. 설치 토큰은 clone params(`auth.token`)에도 복사됨(2026-10-13 정정: 이전 "env로 전달"만 적은 서술을 [07 4.2절](07-credentials.md)에 맞춤) | - | `libs/sandbox/infrastructure/providers/e2b-sandbox.service.ts:443,462,816,833,980,986`, `.../providers/submodule-fetch.ts:523-528`(주석), 로컬 `local-sandbox.service.ts:122-174`, clone params `github.service.ts:6490-6528` | 코드 확인(주석) / 추론(쉘 확장) |

### 1.3 웹훅 서명·시크릿 검증 (컨트롤러별)

| 플랫폼 | 등록 방식 | 컨트롤러 검증 | 근거 | 검증 |
|---|---|---|---|---|
| GitHub (App 모드) | 웹훅은 GitHub App에 설정. Kodus는 설정하지 않음 | **없음**. `x-github-event`만 읽고 200 | `apps/webhooks/src/controllers/github.controller.ts:18-87`, `github.service.ts:458-461` | 코드 확인 |
| GitHub (PAT 모드) | `repos.createWebhook`에 `config:{url, content_type:'json', insecure_ssl:'0'}`, **`secret` 없음** | 없음 | `github.service.ts:5784-5889` | 코드 확인 |
| GitLab | `ProjectHooks.add(... enableSslVerification:true)`, **토큰 없음** | **없음** | `gitlab.service.ts:3067-3089`, `apps/webhooks/src/controllers/gitlab.controller.ts:17-30` | 코드 확인 |
| Bitbucket | 시크릿 없이 URL+이벤트만 | **없음**(IP 허용 목록도 못 찾음) | `bitbucket-cloud.service.ts:3345-3361`, `bitbucket.controller.ts:18-93` | 코드 확인 |
| Forgejo | `config:{url, content_type:'json'}`, 시크릿 없음 | **없음**. 헤더 4종(`x-forgejo-event`, `x-gitea-event`, `x-github-event`, `x-gogs-event`) 모두 수용 | `forgejo.service.ts:4075-4091`, `forgejo.controller.ts:23-95` | 코드 확인 |
| Azure Repos | URL에 `?token=`(전역 `CODE_MANAGEMENT_WEBHOOK_TOKEN`을 AES-256-CBC로 암호화) | `validateWebhookToken`, 실패 시 403. **모든 테넌트 공유 토큰**. 비교는 `===`(상수 시간 아님) | `apps/webhooks/src/controllers/azureRepos.controller.ts:19-29`, `libs/common/utils/webhooks/webhookTokenCrypto.ts:24-35` | 코드 확인 |
| Billing | HMAC-SHA256(`rawBody`)+`timingSafeEqual`, 시크릿 없으면 거부 | 있음 | `apps/webhooks/src/controllers/billing.controller.ts:317-350` | 코드 확인 |

- 전역 미들웨어는 `helmet`, `express-rate-limit`, 25MB JSON 파서(`rawBody` 보관)뿐이고 Provider별 인증은 없다(`apps/webhooks/src/main.ts:89-95,123-130`). 모든 Git 컨트롤러는 `@Public()`.
- 검색: `createHmac|timingSafeEqual|x-hub-signature|x-gitlab-token|x-gitea-signature|x-forgejo-signature`를 `libs/ apps/`에서 → billing(`billing-signature.ts`, `billing-signature.guard.ts`)·doctor·LLM 파일과 테스트 파일만 일치. `apps/webhooks/AGENTS.md`의 "Only Azure Repos validates webhook tokens"와 코드가 일치한다.
- **의미(추론)**: 누구든 임의의 호스트에서 `repository.id`를 지정한 페이로드를 보내면 해당 저장소가 연결된 조직의 리뷰 잡이 발행될 수 있다. 이어서 코드는 Provider API로 PR을 다시 조회하지만(대부분의 파일·패치는 API에서 받음) 페이로드의 `pull_request.number` 등은 신뢰한다. 조직 간 데이터 유출이 아니라 **서비스 남용(비용·스팸)** 위험이 주다.
- 웹훅 응답 순서: 컨트롤러가 200을 **먼저** 보내고 `setImmediate`로 저장하므로 Postgres 장애 시 이벤트는 로그만 남기고 사라진다(`github.controller.ts:53-87`, `enqueue-webhook.use-case.ts:62-93`). outbox가 보장하는 것은 브로커 장애 구간이다. 코드 확인+추론.
- 원본 웹훅 페이로드 전체가 `workflow_jobs.payload`(jsonb)에 저장된다(`enqueue-webhook.use-case.ts:68-72`). 코드 확인.

### 1.4 GitHub rate-limit gate

`GitHubRateLimitGateService.check()`는 잡이 `PROCESSING`이 되기 전 GitHub에서만 `/rate_limit`을 조회해 `remaining < 200`이면 `RateLimitError(resetAt)`을 던진다. 캐시 TTL 30초(`remaining < 600`이면 5초). **오류 시 통과(fail-open)**. 캐시 키 `rl:github:${organizationId}:${teamId ?? 'no-team'}`는 프로세스 메모리(워커별). octokit 스로틀은 `onRateLimit`이 `false`를 반환해 즉시 던지고, 에러 핸들러가 리셋 시각에 맞춘 지연으로 재발행한다(`libs/platform/infrastructure/adapters/services/github/github-rate-limit-gate.service.ts:39-42,67-104,136-207`, `github.service.ts:3179-3264`, `libs/core/infrastructure/queue/rabbitmq-error.handler.ts:253-259`). 코드 확인.

## 2. 큐와 장애 복구

### 2.1 구성요소

| 구성요소 | 동작 | 근거 | 검증 |
|---|---|---|---|
| enqueue | 한 트랜잭션에서 잡+outbox 생성. 라우팅 `workflow.jobs.created.<WorkflowType>`, 메시지 본문에 `organizationId`·`teamId` | `libs/core/workflow/infrastructure/workflow-job-queue.service.ts:51-103` | 코드 확인 |
| outbox 릴레이 | 재귀 `setTimeout` 폴링, 배치 50, 작업이 있으면 100ms·유휴 시 최대 3초, 브로커 단절 시 사이클 건너뜀 | `libs/core/workflow/infrastructure/outbox-relay.service.ts:132-135,157-225` | 코드 확인 |
| outbox 클레임 | `UPDATE … WHERE uuid IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING *`, `attempts` 증가, `lockedBy`=호스트명 | `libs/core/workflow/infrastructure/repositories/outbox-message.repository.ts:86-139` | 코드 확인 |
| 발행·재시도 | persistent+타임아웃(기본 15초). 실패 시 READY로 되돌리고 지수 백오프(기본 2초~1시간, ±10% 지터). `WORKFLOW_OUTBOX_MAX_ATTEMPTS`(기본 10) 초과면 outbox FAILED+**잡 FAILED/PERMANENT**+하트비트 알림 | `outbox-relay.service.ts:58-66,632-859`, `outbox-message.repository.ts:170-236` | 코드 확인 |
| outbox 리퍼 | 5분마다 advisory lock 아래서 5분 넘게 `PROCESSING`인 행을 READY로 | `outbox-relay.service.ts:274-316` | 코드 확인 |
| inbox claim | `(consumerId, messageId)` 원자적 upsert. 이미 PROCESSED면 skip, PROCESSING이 `claimTimeoutMinutes`보다 오래면 재클레임. 큐별: webhook 20, cli_code_review 35, ast_graph_build 30, ast_graph_incremental 15, 그 외 150분 | `libs/core/workflow/infrastructure/repositories/inbox-message.repository.ts:53-103`, `workflow-job-consumer.service.ts:273-280` | 코드 확인 |
| 소비자 | 6개 quorum 큐(webhook, code_review, cli_code_review, check_implementation, ast_graph_build, ast_graph_incremental)+DLX `workflow.exchange.dlx`(키 `workflow.job.failed`). AST 큐는 single-active-consumer+`x-consumer-timeout`(25/15분), prefetch 5. 나머지 채널 기본 prefetch 20. `errorBehavior: ACK` | `libs/core/workflow/infrastructure/workflow-queue-arguments.ts:17-55`, `workflow-job-consumer.service.ts:66-265`, `libs/core/infrastructure/queue/rabbitmq.module.ts:128-172` | 코드 확인 |
| 실패 시 | 잡을 `FAILED/PERMANENT`로 표시 → `releaseLock`(10초 제한) → 오류 재던짐 → `RabbitMQErrorHandler`가 지연 교환(`x-delay`)으로 재발행(총 시도 = 최대 재시도+1) 또는 DLX. 재발행 실패 시 "CRITICAL … may be lost"를 던짐 | `workflow-job-consumer.service.ts:458-546`, `rabbitmq-error.handler.ts:83-185,233-259` | 코드 확인 |
| DLQ | `workflow.jobs.dlq` 등이 선언·바인딩되지만 **소비자가 없다**(모든 `@RabbitSubscribe` 지점을 확인, 릴레이 주석도 "the DLX has no consumer"). 사람이 처리하는 주차장 큐 | `libs/core/infrastructure/queue/rabbitmq-dlq.initializer.ts:201-231`, `outbox-relay.service.ts:489-490` | 코드 확인 |
| 지연 플러그인 | 토폴로지가 `x-delayed-message` 교환을 연결 시 선언하므로 플러그인이 없으면 연결 설정이 실패(추론). 이미지는 `rabbitmq:4.2.2-management`에 `rabbitmq_delayed_message_exchange` 4.2.0을 설치 | `libs/core/infrastructure/queue/config/rabbitmq-topology.config.ts:30-53`, `docker/rabbitMQ/Dockerfile:1-49` | 코드 확인 / 추론 |
| 잡 타임아웃 | webhook 9분, 코드리뷰 105분, CLI 28분, 구현 확인 9분, AST 빌드 19분, 증분 9분. 브로커 `consumer_timeout`보다 짧게 | `libs/core/workflow/infrastructure/job-processor-router.service.ts:23-34,53-104` | 코드 확인 |
| 스테일 `PROCESSING` 잡 리퍼 | 기본 10분 주기, `updatedAt`이 180분 넘게 갱신 안 된 `PROCESSING`을 FAILED로(재실행하지 않음). PENDING·WAITING은 안 건드림 | `outbox-relay.service.ts:68-84,500-585`, `libs/core/workflow/infrastructure/repositories/workflow-job.repository.ts:273-309` | 코드 확인 |
| inbox 리퍼 | 5분 주기, 소비자별 타임아웃(코드리뷰 150분 등). `cli_code_review`는 리퍼 맵에 없음 | `outbox-relay.service.ts:86-94,342-481` | 코드 확인 |
| 분산 락 | **Postgres advisory lock**을 **고정된 QueryRunner**(풀 연결 1개를 락 수명 동안 점유)로 획득. `ttl`은 단순 `setTimeout` 자동 해제이며 **갱신 없음** | `libs/core/workflow/infrastructure/distributed-lock.service.ts:9-35,94-194` | 코드 확인 |
| BYOK 동시성 게이트 | 조직 BYOK 슬롯에 `maxConcurrentRequests`가 있으면 advisory lock 슬롯을 시도. 모두 사용 중이면 15초부터 2배(상한 5분)로 최대 10회 지연, 그래도 안 되면 `exhausted`로 실패 처리+작성자 1회 알림. **슬롯 락은 TTL 없이 job 끝까지 보유(최대 105분)하며 PG 연결 1개를 점유** → 워커 풀 12(`worker.module.ts:78`)에 비해 prefetch 20이면 풀 고갈 위험(추론) | `libs/code-review/workflow/byok-concurrency-gate.service.ts:33-150,267-307`, `code-review-job-processor.service.ts:105-206,300-319` | 코드 확인 / 추론 |
| 워커 역할 분리 | `WORKER_ROLE=code-review`(소비자·파이프라인·릴레이·모니터, PG 풀 12), `analytics`(소비자 끔, 풀 4). 미설정이면 부팅 실패 | `apps/worker/src/worker-role.ts:23-35`, `apps/worker/src/worker.module.ts:49-143` | 코드 확인 |
| 드레인 | `WorkerDrainService`가 소비자를 먼저 취소(5초 상한)하고 연결을 닫음(25초 기본), `WorkflowJobConsumer`가 활성 잡을 기다린 뒤 `releaseAllByInstance`. 채널·브로커 헬스 가드가 죽은 소비자(90초)·단절(120초)에서 프로세스를 내림 | `apps/worker/src/worker-drain.service.ts:5-133`, `workflow-job-consumer.service.ts:548-640`, `apps/worker/src/worker-health-guard.service.ts:43-46` | 코드 확인 |
| ECS 태스크 보호 | `API_CLOUD_MODE && worker`에서만 실제 구현(`libs/ee/infrastructure/ecs`, **ee**). 그 외 NoOp | `workflow-job-consumer.service.ts:303-347`, `libs/core/workflow/modules/workflow.module.ts:121-148` | 코드 확인 |
| 이벤트 브리지 | Postgres `LISTEN/NOTIFY`(at-most-once)+폴링 폴백. `pull-request.closed`, `pr-execution.updated`만 전달. 리뷰 잡 채널이 아님 | `libs/core/workflow/infrastructure/cross-process-events.bridge.ts:11-12,143,154-158,317-331` | 코드 확인 |
| `WAITING_FOR_EVENT` | 상태와 처리 코드는 있으나 `WorkflowPausedError`를 던지는 단계가 없어 코드리뷰에서는 사실상 미사용 | `code-review-job-processor.service.ts:274-283` | 코드 확인(부정 grep) |

### 2.2 재시도 정책의 실제 값과 문서 불일치

`AGENTS.md`는 "max 5 retries"라고 하지만 핸들러 상수 기본은 2(`rabbitmq-error.handler.ts:23,65-67`), 설정 로더 기본은 5(`libs/core/infrastructure/config/loaders/workflow-queue.loader.ts:36-39`), `.env.example`은 3이다. `Number.isFinite(maxRetries)`이므로 설정 키가 있으면 로더 값이 쓰여 **환경변수가 없으면 실효 5**(핸들러 주석의 "lowered 5→2"는 오해 소지). 런타임에서 관측하지 못했다. 코드 확인+추론. 또 소비자 주석이 "slow Mongo"라 하지만 inbox는 Postgres(`kodus_workflow.inbox_messages`)에 있다.

### 2.3 파이프라인 오류의 의미 (중요)

파이프라인 실행기는 단계 예외를 기록하고 계속 진행하며(`pipeline-executor.service.ts:211-285`), 자동화 전략은 오류를 문자열로 바꿔 반환하고(`automationCodeReview.ts:329-337`), 유스케이스도 대부분 삼키며(`runCodeReview.use-case.ts:247-265`), 프로세서는 이후 `markCompleted`를 호출한다(`code-review-job-processor.service.ts:238`). 결과적으로 **GitHub·LLM 장애가 파이프라인 중간에 나면 execution이 ERROR/PARTIAL_ERROR, 체크런은 FAILURE/NEUTRAL이 되지만 잡은 COMPLETED이고 RabbitMQ 재시도가 일어나지 않는다.** 재시도 되는 경우는 **프로세서 수준에서 던져진 예외**다: `catch`가 모든 오류를 `handleFailure` 후 다시 던지므로(`code-review-job-processor.service.ts:290-299`) rate-limit 사전 게이트·분류된 `RateLimitError`뿐 아니라 라우터 타임아웃·중단도 `RabbitMQErrorHandler` 재시도 대상이다. 예외 없이 반환하는 지연 경로로 BYOK 슬롯 지연(`:104-111`)과 PR 충돌 지연(`:259-268`)이 따로 있다. 파이프라인 단계 오류는 이 경로에 닿지 않는다(위). 코드 확인+추론.

### 2.4 외부 장애가 영향을 주는 리뷰 단계

| 장애 | 영향 | 근거 | 검증 |
|---|---|---|---|
| GitHub rate limit | 잡 시작 전 게이트가 지연 재발행. 파이프라인 내부 403은 단계 오류로 기록 | `github-rate-limit-gate.service.ts:95-104`, `code-review-job-processor.service.ts:100-103,253-299` | 코드 확인 |
| GitHub API 장애(429 외) | octokit retry(2회) 후 단계 오류, 파일 가져오기 실패는 `critical` | `github.service.ts:3181-3186`(octokit retry), `libs/core/infrastructure/pipeline/abstracts/base-stage.abstract.ts:32`(기본 `critical`), `pipeline-executor.service.ts:258-260` | 코드 확인+추론 |
| LLM 제공자 | 루프 스텝당 `maxRetries 3`, 1회 호출은 TRANSIENT만 1회 재시도. AgentReviewStage는 기본값 `critical`이지만 이는 스테이지가 예외를 던질 때만 해당하고, 에이전트별로는 핵심 4종(generalist·bug·security·performance)만 `critical`, 보조 에이전트(kody-rules 등)와 잘린 실행은 `partial`(GitHub NEUTRAL)이다(`agent-review.stage.ts:796-832`) | `libs/llm/agent-loop-call.ts:57,210`, `libs/llm/retry-policy.ts:22-51` | 코드 확인+추론 |
| RabbitMQ 중단 | 릴레이가 사이클을 건너뛰고 outbox 행이 쌓임. 웹훅 enqueue는 Postgres만 쓰므로 성공. 워커·웹훅은 `wait:true`로 연결을 기다리도록 설계됨(부팅 실패는 `@golevelup/nestjs-rabbitmq` 라이브러리 동작이라 추론, api는 `wait:false`로 계속 서빙). `API_RABBITMQ_ENABLED=false`면 앱은 뜨지만 잡이 소비되지 않음([05 4.1절](05-dependencies.md#rabbitmq-compose)) | `outbox-relay.service.ts:218-225`, `rabbitmq.module.ts:84-113` | 코드 확인 |
| Postgres 중단 | 잡·inbox·outbox·advisory 락·브리지 전체 정지. 웹훅은 유실. PR 락은 fail-open | `github.controller.ts:53-87`, `automationCodeReview.ts:174-183` | 코드 확인+추론 |
| Mongo 중단 | PR 상태·규칙·샌드박스 리스에 영향. 단계별로는 추적하지 않음 | - | 미확인 |
| E2B / 샌드박스 | 리스 생성 3회 재시도(60초/120초 백오프) 실패 시 self-contained로 계속 | `libs/code-review/pipeline/stages/create-sandbox.stage.ts:130-132,197-227`, `libs/sandbox/infrastructure/services/sandbox-lease-manager.service.ts:730-758` | 코드 확인 |
| Morph | committable 검증 단계만(`partial`) | `validate-suggestions.stage.ts:28,434,544,561-568` | 코드 확인 |

## 3. 테넌트 격리 매트릭스

**모든 테이블이 테넌트 공유이고 Postgres RLS는 없다**(`ROW LEVEL SECURITY|CREATE POLICY|set_config|SET LOCAL|current_org`를 `libs apps docker`에서 검색, 해당 없음). 격리는 애플리케이션 수준이다. 코드 확인(부정 grep).

| 리소스 | 조직 범위 전달? | 어디서 강제? | 근거 | 검증 |
|---|---|---|---|---|
| Postgres `integrations`/`auth_integrations`/`integration_configs` | 예 | `IntegrationRepository.findOne`이 org 조건을 추가하고 `organization.uuid`가 없으면 `undefined` 반환 | `integration.repository.ts:77-124` | 코드 확인 |
| Postgres `organization_parameters`(BYOK 등) | 예 | `findByKey`가 `organization_id = :organizationId` | `libs/organization/infrastructure/adapters/repositories/organizationParameters.repository.ts:243-262` | 코드 확인 |
| Postgres `workflow_jobs` | 컬럼 `organizationId`·`teamId`(인덱스 있음) | `findOne(id)`는 `uuid`만으로 조회. `findMany`는 호출자가 넘길 때만 필터. 리퍼·릴레이는 테넌트 비의존 | `libs/core/workflow/infrastructure/repositories/schemas/workflow-job.model.ts:12-17,62-66`, `workflow-job.repository.ts:214-217,243-249` | 코드 확인 |
| Postgres `outbox_messages`/`inbox_messages` | **조직 컬럼 없음**(조직 ID는 `payload` 안에만) | - | 스키마 | 코드 확인 |
| Postgres `repositories`·`ast_nodes`·`ast_edges` | `repo_id`(uuid) 키. `repositories`는 **`UNIQUE (platform, external_id)`가 전역**이고 `integration_config_id` 하나에 연결 | 리뷰는 `findByExternalId(platform, repository.id)`로 **조직 조건 없이** 조회. 두 조직이 같은 플랫폼 저장소 ID를 등록하면 한 `repositories` 행·AST 그래프를 공유할 수 있음(조회 형태는 코드 확인, 영향은 추론) | `libs/code-review/infrastructure/adapters/repositories/schemas/repository.model.ts:15-27`, `.../repository.repository.ts:72-79`, `agent-review.stage.ts:631-645` | 코드 확인 / 추론 |
| Postgres cockpit warehouse(`analytics.*`) | 예 | 원시 SQL `WHERE "organizationId" = $1` | `libs/cockpit/infrastructure/services/cockpit-validation.service.ts:16-25` | 코드 확인 |
| Mongo `pullRequests` | 스키마에 `organizationId` 필수 | 대부분의 쿼리가 AND. `update()`는 방어적으로 AND. `findById(uuid)`·`findOne(filter)`는 org 조건 없음 | `libs/platformData/infrastructure/adapters/repositories/pullRequests.repository.ts:63-69,151-163,2031-2043` | 코드 확인 |
| Mongo `kodyRules` | 조직당 문서 | 읽기는 `organizationId` 필터. **쓰기는 해당 조직 문서 `_id`로 하며 org 조건 없음**(`update/addRule/updateRule/delete/deleteRule`). 범위 확인은 유스케이스가 JWT 조직으로 하고 `findById(ruleId, organizationId)` | `libs/ee/kodyRules/repository/kodyRules.repository.ts:46-64,276-379`, `libs/kodyRules/application/use-cases/delete-rule-in-organization-by-id.use-case.ts:65-92` | 코드 확인 |
| Mongo 그 외 | `sandbox_leases`·`issues`·`pullRequestMessages`·`codeReviewFeedback` 등은 `organizationId` 보유. `documentationSearchCache`·`featured_public_reviews`·`ruleLikes`·`observability_metrics`는 스키마에 **없음**(첫째는 공유 캐시) | 스키마 grep | 코드 확인(스키마) / 미확인(쿼리) |
| RabbitMQ | 조직 ID는 **메시지 본문에만**. 라우팅 키에 테넌트 세그먼트 없음. 모든 테넌트가 6개 큐 공유(테넌트별 큐·우선순위·공정성 없음). 소비자는 `jobId`로 잡을 읽어 잡 행의 조직을 신뢰. **JWT 가드는 RabbitMQ 컨텍스트에 `true`를 반환**하고 브로커 메시지 검증은 주석 처리 | `workflow-job-queue.service.ts:54,61-69`, `libs/identity/infrastructure/adapters/services/auth/jwt-auth.guard.ts:94-102` | 코드 확인 |
| 캐시·락 | 메모리 캐시 키가 혼재. 조직 포함: `rl:github:${org}:${team}`, `etag:${org}:${team}:`, `gh:pr-files:${org}:…`, `gh:default-branch:${org}:…`, `gh:user:${org}:…`. **미포함**: `<installationId>`, `gh:contents:${owner}/${repo}@${branch}:${path}`(`github.service.ts:6203`)와 `gh:contents:${org}/${repo}:${sha}:${filename}`(`:5003-5005`, 둘 다 GitHub owner/repo 기준). 락은 Postgres이며 `CODE_REVIEW:${org}:${repo}:${pr}`·`byok-concurrency::${org}::…`는 조직 포함. **Redis 없음**(메모리 캐시 `store:'memory', max:50000`) | `github.service.ts:174,2662-2677,2699,4172,5003-5005,5127,5620,6203,6699`, `github-rate-limit-gate.service.ts:206`, `libs/core/cache/cache.module.ts:9-13` | 코드 확인 |
| 샌드박스·클론 경로 | 리스 키 `prKey`=`${orgId}:${repoId}:${prNumber}`(CLI는 `:cli:${branch}`, 그래프는 `:graph:${jobId}`), 로컬 클론 디렉터리는 **랜덤 `mkdtemp`로 조직이 경로에 없음**, E2B는 리스당 별도 VM. 다른 워커가 로컬 리스를 공유하는지는 미추적 | `libs/sandbox/infrastructure/repositories/sandbox-lease.repository.ts:8-50`, `create-sandbox.stage.ts:98-102`, `local-sandbox.service.ts:115` | 코드 확인 / 미확인 |
| 코드 검색·AST·벡터 | 검색(`rg`)은 리스별 체크아웃 안에서 실행. AST는 위 `repositories` 항목. 벡터 쿼리(`<=>`)는 없음(extension만 생성) | `e2b-sandbox.service.ts:134` | 코드 확인(부정 grep) |
| LLM/BYOK 키 | 조직별 조회(`findByKey(BYOK_CONFIG, orgAndTeam)`), 저장 시 암호화. 동시성 게이트는 `sha256(provider+apiKey+baseURL)`로 스코프 | `byok-concurrency-gate.service.ts:213-290` | 코드 확인 |
| API 인증 | 전역 `APP_GUARD`=`JwtAuthGuard`, `JwtStrategy.validate`가 **이메일로 DB에서 사용자를 읽어** 조직을 클레임이 아닌 DB에서 결정 | `libs/shared/infrastructure/shared-core.module.ts:11-14`, `jwt-auth.guard.ts:27-91`, `jwt-auth.strategy.ts:31-51` | 코드 확인 |
| API 인가 | CASL `PolicyGuard`는 `canInOrg`가 조건에 `organizationId`를 넣지만 `checkPermissions`가 **문자열 subject로 `ability.can(action, resource)`**를 호출해 요청이 준 조직 ID를 비교하지 않는다. 핸들러는 `request.user.organization.uuid` 존재와 ACTIVE만 확인 | `permissionsAbility.factory.ts:22-98`, `policy.handlers.ts:53-71`, `policy.guard.ts:29-58` | 코드 확인 |
| **`TenantScopeGuard`** | 클라이언트가 준 `organizationId`가 JWT 조직과 다르면 403, `teamId`가 JWT 조직 소속이 아니면 404. **7개 컨트롤러에만 적용**: `parameters`, `agent`, `spendLimit`, `organizationParameters`, `kodyRules`, `codeManagement`, `pullRequestMessages` | `apps/api/src/guards/tenant-scope.guard.ts:17-83` | 코드 확인 |
| 가드 없는 컨트롤러 | `integrationConfig`·`pullRequest` 대시보드는 `teamId`를 클라이언트에서 받되 조직을 `request.user`에서 도출해 쿼리가 AND → 외부 팀은 빈 결과. 코크핏은 `CockpitTierGuard`가 쿼리 조직을 JWT와 비교. **`@Public() GET /cockpit/source/:organizationId`**는 인증 없이 임의 조직의 데이터 소스 라우팅 결정을 반환(코드 주석: PII 없음). 나머지 컨트롤러(`license`, `integration`, `organization`, `pullRequest` 나머지 경로)는 개별 감사하지 않음 | `getIntegrationConfigsByIntegrationCategory.use-case.ts:33-56`, `libs/cockpit/infrastructure/guards/cockpit-tier.guard.ts:71-109`, `apps/api/src/controllers/cockpit.controller.ts:104-114` | 코드 확인 / 미확인 |
| 팀 CLI 키 | 접두사 조회+bcrypt 비교, 키가 자기 팀·조직으로 해석됨. 관리 유스케이스는 `assertTeamInCallerOrganization`으로 404. CLI 잡 상태는 `jobOrgId !== organizationId`이면 404인데 **조직 ID가 없는 잡은 통과** | `libs/organization/infrastructure/adapters/services/team-cli-key.service.ts:65-91`, `libs/organization/application/use-cases/team-cli-key/manage.use-case.ts:48,72-85`, `libs/cli-review/application/use-cases/get-cli-review-job-status.use-case.ts:66-83` | 코드 확인 |
| 웹훅 → 테넌트 | 워커가 repository id로 결정(`WebhookContextService.getContext`). 서명 검증 없음. 같은 저장소가 여러 팀에 연결되면 **활성 automation이 있는 첫 후보**가 선택됨. GitLab만 host로 후보를 좁힘 | `webhook-context.service.ts:46-165` | 코드 확인 |

**결론(추론)**: "조직 ID가 인자로 전달된다"는 대부분 참이지만 "쿼리가 조직 조건으로 보장된다"는 리소스마다 다르다. 특히 (1) `repositories`/AST 그래프의 조직 조건 없는 조회, (2) GitHub 콘텐츠 캐시 키가 GitHub owner/repo 기준, (3) `kodyRules` 쓰기가 조직 문서 `_id` 기준이고 범위가 유스케이스에 의존, (4) `outbox/inbox`·큐가 조직 컬럼/라우팅 없이 공유, (5) 같은 저장소가 여러 조직에 연결된 경우 선택 규칙이 "첫 활성"이라는 점이 팀 A·B 혼입 위험의 후보다. 이 중 (1)·(2)·(5)는 **같은 외부 저장소 ID를 서로 다른 조직이 등록한 경우**에 한정되며 일반 흐름에서는 드물 수 있다(추론). 팀 간 격리가 필수인 우리 서비스에서는 이 조건을 막는 설계가 필요하다([06](06-fit.md)).

## 4. Q10 지원 수준

**부분 지원.**
- 지원: outbox/inbox 멱등성·지연 재시도·DLX 파킹·리퍼·드레인·워커 역할 분리·BYOK 동시성 제한, 조직별 BYOK 키, Provider 자격증명 저장(PAT 암호화), JWT가 DB에서 조직 결정, 일부 컨트롤러의 `TenantScopeGuard`.
- 미지원(충분히 추적한 범위): GitHub/GitLab/Bitbucket/Forgejo 웹훅 서명·시크릿 검증, GitLab OAuth refresh, DLQ 소비자, Postgres RLS, 파이프라인 체크포인트, 실행 중 Head SHA 취소, 큐·outbox의 테넌트 분리.
- 미확인: 모든 API 컨트롤러의 테넌트 범위, 로컬 샌드박스 리스의 워커 간 공유, Mongo 장애의 단계별 영향.

## 경로 사전 (짧은 이름 → 풀 경로)

- `github.service.ts`: `libs/platform/infrastructure/adapters/services/github/`; `gitlab.service.ts`, `forgejo.service.ts`: `libs/platform/infrastructure/adapters/services/`; `bitbucket-cloud.service.ts`: `.../services/bitbucket/`; `azureRepos.service.ts`: `.../services/azureRepos/`
- `integration.repository.ts`: `libs/integrations/infrastructure/adapters/repositories/`; `integration.service.ts`: `libs/integrations/infrastructure/adapters/services/`
- `permissionsAbility.factory.ts`, `policy.guard.ts`, `policy.handlers.ts`: `libs/identity/infrastructure/adapters/services/permissions/`; `jwt-auth.guard.ts`, `jwt-auth.strategy.ts`: `libs/identity/infrastructure/adapters/services/auth/`
- `outbox-relay.service.ts`, `workflow-job-consumer.service.ts`, `workflow-job-queue.service.ts`, `distributed-lock.service.ts`, `job-processor-router.service.ts`: `libs/core/workflow/infrastructure/`; `*-message.repository.ts`, `workflow-job.repository.ts`: `libs/core/workflow/infrastructure/repositories/`
- `rabbitmq-error.handler.ts`, `rabbitmq.module.ts`, `rabbitmq-dlq.initializer.ts`: `libs/core/infrastructure/queue/`
- `byok-concurrency-gate.service.ts`, `code-review-job-processor.service.ts`: `libs/code-review/workflow/`
- `automationCodeReview.ts`: `libs/automation/infrastructure/adapters/services/processAutomation/strategies/`; `runCodeReview.use-case.ts`: `libs/ee/automation/`
- `local-sandbox.service.ts`, `e2b-sandbox.service.ts`, `sandbox-lease.repository.ts`: `libs/sandbox/infrastructure/providers/` (리포지토리는 `.../repositories/`)
- `agent-review.stage.ts`, `create-sandbox.stage.ts`, `validate-suggestions.stage.ts`: `libs/code-review/pipeline/stages/`
- `pipeline-executor.service.ts`: `libs/core/infrastructure/pipeline/services/`
- `tenant-scope.guard.ts`: `apps/api/src/guards/`; `cockpit.controller.ts`, `kodyRules.controller.ts`: `apps/api/src/controllers/`
- `cockpit-tier.guard.ts`, `cockpit-validation.service.ts`: `libs/cockpit/infrastructure/{guards,services}/`
