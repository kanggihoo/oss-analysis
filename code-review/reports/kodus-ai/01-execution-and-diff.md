# kodus-ai — 실행 경로(Q1)와 코드 접근·Diff 처리(Q2)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약(검증 열이 있는 표의 행을 스크립트로 센 값, 2026-10-13 재집계. 복수 표기 행은 각 수준에 중복 계산하고 검증 열이 없는 표·본문 서술은 제외): 코드 확인 54 / 실행 확인 0 / 추론 1 / 미확인 1
- 실행 여부: **정적 추적만**. 아래 "짧은 예"도 실제 함수를 읽고 손으로 추적한 결과이며 실행하지 않았다.
- 줄 번호 재대조: 2026-10-13 정정 작업에서는 이 문서의 줄 번호를 다시 대조하지 않았다(범위 밖).
- 표기: `경로:줄`은 레포 루트 기준. `ee`는 경로에 `ee/` 또는 파일명에 `.ee.`가 있어 `license_ee.md` 규칙의 대상이 되는 파일([05 6절](05-dependencies.md#license)).

<a id="q1"></a>
## Q1. 실행 경로: 이벤트에서 댓글 게시까지

### 1.1 진입점과 디렉터리 구조

| 진입점 | 역할 | 근거 | 검증 |
|---|---|---|---|
| `apps/webhooks` | 웹훅 수신 전용(생산자). RabbitMQ를 소비하지 않음 (`RabbitMQWrapperModule.register({ enableConsumers: false })`) | `apps/webhooks/src/modules/webhook-handler.module.ts:26-53`, `apps/webhooks/AGENTS.md` | 코드 확인 |
| `apps/worker` | Nest 애플리케이션 컨텍스트(HTTP 서버 없음)로 큐 소비·리뷰 실행·outbox 릴레이·cron. `WORKER_ROLE`이 `code-review` 또는 `analytics` | `apps/worker/src/worker-role.ts:23-35`, `apps/worker/src/worker.module.ts:49-143` | 코드 확인 |
| `apps/api` | REST, 인증, 규칙·설정 CRUD, 일부 cron | `AGENTS.md` Structure | 코드 확인(문서)·세부 미확인 |
| `libs/*` | 도메인 모듈. 리뷰 엔진은 `libs/code-review`, 큐·워크플로는 `libs/core/workflow`, Provider 어댑터는 `libs/platform` | 디렉터리 | 코드 확인 |
| 별도 CLI 리뷰 경로 | `CLI_CODE_REVIEW` 잡(별도 큐) | `libs/core/workflow/infrastructure/workflow-job-consumer.service.ts:127-151` | 코드 확인(경로 존재만, 이 문서의 대상 아님) |

### 1.2 호출 순서 (이벤트 → 게시)

| # | 단계 | 위치 | 식별자 | 설명 | 검증 |
|---|---|---|---|---|---|
| 1 | 웹훅 수신·필터 | `apps/webhooks/src/controllers/github.controller.ts:18-88` | `GithubController.handleWebhook` | `x-github-event`가 `pull_request/issue_comment/pull_request_review_comment/push`이고 `pull_request`는 액션이 `opened/synchronize/closed/reopened/ready_for_review`일 때만 통과. 200을 먼저 반환하고 `setImmediate`로 enqueue. **서명 검증 없음** | 코드 확인 |
| 1' | GitLab | `apps/webhooks/src/controllers/gitlab.controller.ts:17-62` | `GitlabController` | `Merge Request Hook`/`Note Hook`만 통과. 검증 없음 | 코드 확인 |
| 1'' | Azure | `apps/webhooks/src/controllers/azureRepos.controller.ts:19-29`, `libs/common/utils/webhooks/webhookTokenCrypto.ts:24-35` | `validateWebhookToken` | `?token=`을 AES-256-CBC로 복호화해 전역 `CODE_MANAGEMENT_WEBHOOK_TOKEN`과 비교. 틀리면 403 | 코드 확인 |
| 2 | 작업 발행 | `libs/platform/application/use-cases/webhook/enqueue-webhook.use-case.ts:62-93` | `EnqueueWebhookUseCase.execute` | **이벤트를 정규화하지 않고 raw payload 그대로** `WEBHOOK_PROCESSING`/`WEBHOOK_RAW` 잡으로 저장 (`maxRetries: 1`) | 코드 확인 |
| 3 | 잡+outbox 저장 | `libs/core/workflow/infrastructure/workflow-job-queue.service.ts:38-116` | `WorkflowJobQueueService.enqueue` | 한 DB 트랜잭션에서 `workflow_jobs`와 `outbox_messages` 생성. 라우팅 키 `workflow.jobs.created.<WorkflowType>` | 코드 확인 |
| 4 | 릴레이 | `libs/core/workflow/infrastructure/outbox-relay.service.ts:182-225`, `libs/core/workflow/infrastructure/repositories/outbox-message.repository.ts:86-139` | `OutboxRelayService.poll/processOutbox` | 재귀 `setTimeout` 폴링(배치 50, 유휴 시 최대 3초), `FOR UPDATE SKIP LOCKED`로 클레임, 발행 실패는 지수 백오프, 기본 10회 실패 시 잡도 FAILED | 코드 확인 |
| 5 | 소비 | `libs/core/workflow/infrastructure/workflow-job-consumer.service.ts:66-120,350-546` | `WorkflowJobConsumer` | 큐 `workflow.jobs.webhook.queue`, `workflow.jobs.code_review.queue` 등 6개. inbox `claim` 후 `jobProcessor.process(jobId)` | 코드 확인 |
| 6 | 라우팅·타임아웃 | `libs/core/workflow/infrastructure/job-processor-router.service.ts:53-104,149-166` | `JobProcessorRouterService.process` | WorkflowType별 프로세서 선택, 웹훅 9분·코드리뷰 105분 등 타임아웃 | 코드 확인 |
| 7 | 웹훅 잡 처리 | `libs/automation/webhook-processing/webhook-processing-job.processor.ts:63-227` | `WebhookProcessingJobProcessorService.process` | 플랫폼 핸들러의 `canHandle`/`execute` 호출 | 코드 확인 |
| 8 | **이벤트 정규화·테넌트 결정** | `libs/platform/infrastructure/webhooks/github/githubPullRequest.handler.ts:114-196`, `libs/platform/application/services/webhook-context.service.ts:46-127` | `GitHubPullRequestHandler.handlePullRequest`, `WebhookContextService.getContext` | 페이로드의 `repository.id`로 integration config를 찾아 org/team과 활성 코드리뷰 automation을 결정. 없으면 조용히 종료 | 코드 확인 |
| 9 | PR 저장 + 리뷰 잡 발행 | `githubPullRequest.handler.ts:158-196`, `libs/core/workflow/application/use-cases/enqueue-code-review-job.use-case.ts:35-61` | `SavePullRequestUseCase`, `EnqueueCodeReviewJobUseCase` | `CODE_REVIEW` 잡 생성(`PIPELINE_SYNC`, `maxRetries: 1`). 같은 PR·SHA에 대한 중복 키 없음 | 코드 확인 |
| 10 | 리뷰 잡 처리 | `libs/code-review/workflow/code-review-job-processor.service.ts:51-320` | `CodeReviewJobProcessorService.process` | GitHub rate-limit gate → BYOK 동시성 gate → `PROCESSING` → 유스케이스 실행 → `COMPLETED` | 코드 확인 |
| 11 | 페이로드 매핑 | `libs/ee/automation/runCodeReview.use-case.ts:28-266` (ee) | `RunCodeReviewAutomationUseCase.execute` | `IMappedPlatform`으로 action/repository/pullRequest/users를 매핑(`libs/common/utils/webhooks/github.ts:16-143`, `gitlab.ts:17-142`). **모든 예외를 삼킴**(`PrReviewInProgressError`만 재던짐) | 코드 확인 |
| 12 | 자동화 전략 | `libs/automation/infrastructure/adapters/services/processAutomation/strategies/automationCodeReview.ts:108-352` | `AutomationCodeReviewService.run` | PG advisory 락 `CODE_REVIEW:org:repo:pr`(TTL 1분, 실패 시 fail-open), 30분 내 진행 중 execution 검사, execution 행 생성, 직전 SUCCESS execution 조회 | 코드 확인 |
| 13 | 핸들러 | `libs/code-review/infrastructure/adapters/services/codeReviewHandlerService.service.ts:186-390` | `CodeReviewHandlerService.handlePullRequest` | 초기 컨텍스트 구성, `pipelineFactory.getPipeline('CodeReviewPipeline')` 실행, 결과를 ERROR/PARTIAL_ERROR/SUCCESS로 분류. 바깥 `catch`는 `null`을 반환하고 재던지지 않음 | 코드 확인 |
| 14 | 파이프라인 조립 | `libs/core/providers/code-review-pipeline.provider.ee.ts:22-53`, `libs/core/providers/pipeline.provider.ee.ts:14-25` (ee) | `new PipelineExecutor().execute(...)` | 파이프라인 실행기·전략·옵저버를 묶는 **유일한 배선**이 `.ee.` 파일 | 코드 확인 |
| 15 | 18단계 | `libs/code-review/pipeline/strategy/code-review-pipeline.strategy.ts:70-109` | `CodeReviewPipelineStrategy.configureStages` | 아래 1.3 | 코드 확인 |
| 16 | 완료 기록 | `automationCodeReview.ts:556-596` | `_handleExecutionCompletion` | `dataExecution.lastAnalyzedCommit` 등을 execution 행에 저장 | 코드 확인 |

### 1.3 파이프라인 단계 (순서 고정)

실행기는 단순 순차 루프다(단계별 타임아웃 없음). 단계가 예외를 던지면 `context.errors`에 `critical`(기본) 또는 `partial`로 기록하고 **다음 단계로 계속 진행**한다. 근거: `libs/core/infrastructure/pipeline/services/pipeline-executor.service.ts:211-285`. 코드 확인.

단계 파일은 모두 `libs/code-review/pipeline/stages/` 아래이며 `ee/` 경로가 아니다(조사 에이전트의 grep).

| # | 단계(파일:줄) | 목적 | LLM | 외부 코드 접근 |
|---|---|---|---|---|
| 1 | ValidatePrerequisitesStage (`validate-prerequisites.stage.ts:95-324`) | 닫힘/락/무시 사용자/라이선스·트라이얼·BYOK 검증. 실패 시 SKIPPED | 없음 | Provider API(반응) |
| 2 | ValidateNewCommitsStage (`validate-new-commits.stage.ts:25-251`) | 직전 SUCCESS의 `lastAnalyzedCommit` 이후 새 커밋 계산, force-push 고아 커밋 감지, 새 커밋 없으면 SKIPPED | 없음 | Provider API(커밋 목록) |
| 3 | ResolveConfigStage (`resolve-config.stage.ts:33-132`) | 변경 파일 메타데이터와 설정 로드. 오류는 SKIPPED | 없음 | Provider API(파일 목록) |
| 4 | ValidateConfigStage (`validate-config.stage.ts:43-192`) | BYOK 슬롯, 리뷰 주기, draft/브랜치/제목 규칙 | 없음 | 없음 |
| 5 | FetchChangedFilesStage (`fetch-changed-files.stage.ts:26-184`) | ignorePaths 필터, 최대 2000파일, 파일 본문·번호 매긴 패치 생성 | 없음 | Provider API(GraphQL/REST) |
| 6 | LoadExternalContextStage (`load-external-context.stage.ts:34-370`) | 외부 참조, 이전 라운드 결정, (알파 게이트) Trace 결정. fail-open | 없음 | DB/Git |
| 7 | LoadCiEvidenceStage (`load-ci-evidence.stage.ts:25-103`) | head SHA의 CI 결과 | 없음 | Provider API |
| 8 | InitialCommentStage (`initial-comment.stage.ts:14-127`) | 이전 요약 접기, "리뷰 시작" 댓글 신규 작성 | 없음 | Provider API |
| 9 | BusinessLogicValidationStage (`business-logic-validation.stage.ts:30-…`) | PR 본문의 티켓 vs diff. 게이트 있음([03 Q9](03-incremental-memory-rules.md#q9)) | **예**(MCP 도구 에이전트+도구 없는 분석) | MCP |
| 10 | CreateSandboxStage (`create-sandbox.stage.ts:37-228`) | 샌드박스 리스 획득, 저장소 체크아웃 | 없음 | **git fetch** |
| 11 | RunAnalyzersStage (`run-analyzers.stage.ts:32-227`) | 결정적 분석 도구(기본 꺼짐) | 없음 | 샌드박스 |
| 12 | AgentReviewStage (`agent-review.stage.ts:287-1865`) | call graph, finder/verifier Agent Loop, 라인 스냅, dedup, severity | **예**(다수) | 샌드박스 도구 + AST 그래프 |
| 13 | CreatePrLevelCommentsStage (`create-pr-level-comments.stage.ts:22-…`) | PR 수준 댓글 | 없음 | Provider API |
| 14 | ValidateSuggestionsStage (`validate-suggestions.stage.ts:26-124`) | committable suggestion 검증. `enableCommittableSuggestions`이고 GitHub일 때만 | **예**(Morph+LLM) | 전체 파일 본문을 Morph로 전송 |
| 15 | CreateFileCommentsStage (`create-file-comments.stage.ts:41-237`) | 구현된 스레드 resolve, 인라인 댓글 게시, Mongo 저장, `lastAnalyzedCommit` 설정 | 없음 | Provider API |
| 16 | AggregateResultsStage (`aggregate-result.stage.ts:8-114`) | 결과 재집계(게시 이후 실행) | 없음 | 없음 |
| 17 | UpdateCommentsAndGenerateSummaryStage (`finish-comments.stage.ts:46-472`) | PR 요약 생성, 초기 댓글을 최종 본문으로 수정 | **예**(요약) | Provider API |
| 18 | RequestChangesOrApproveStage (`finish-process-review.stage.ts:17-234`) | critical 있으면 request changes, 0건이면 자동 승인 | 없음 | Provider API |

활성 경로가 아닌 것: `KodyFineTuningStage`(`libs/ee/codeReview/stages/kody-fine-tuning.stage.ts`)는 모듈에 등록돼 있으나(`libs/code-review/pipeline/code-review-pipeline.module.ts:37,200`) `configureStages`에 없다. 레거시 파일 단위 리뷰 컨텍스트(`FILE_REVIEW_CONTEXT_PREPARATION_TOKEN`)도 주입처가 없다. 코드 확인(grep 부정 결과).

### 1.4 명령별 경로 분리

| 트리거 | 경로 | 근거 | 검증 |
|---|---|---|---|
| PR 열림/푸시(자동) | 위 1.2 전체 | - | 코드 확인 |
| `@kody start-review` 류 명령 | 댓글 이벤트 → `isReviewCommand && !hasMarker` → `action: 'synchronize'`, `origin: 'command'`로 PR을 API에서 재조회해 리뷰 잡 발행. 새 커밋 가드 우회 | `githubPullRequest.handler.ts:460-613`(`handleComment`의 명령 분기, `origin`/`reviewDirective`/`heavy` 설정은 567-580), `validate-new-commits.stage.ts:316-328` | 코드 확인 |
| 일반 `@kody` 멘션/스레드 답글 | `ChatWithKodyFromGitUseCase` (대화 에이전트, 리뷰 파이프라인과 별개) | `githubPullRequest.handler.ts:615-625` | 코드 확인 |
| PR 닫힘/병합 | 이슈 생성, 샌드박스 무효화 outbox, 병합 시 AST 그래프 증분 갱신 잡, 이벤트 발행 | `githubPullRequest.handler.ts:288-309` | 코드 확인 |
| `synchronize` | 구현 확인 잡(`CHECK_SUGGESTION_IMPLEMENTATION`) 별도 발행 | `githubPullRequest.handler.ts:198-227` | 코드 확인 |


### 1.5 Q1 지원 수준

**지원.** 진입점부터 게시까지 호출 순서를 파일·줄로 추적했다. Azure/Bitbucket/Forgejo 쪽 매퍼·게시 본문은 열지 않았다(미확인).

<a id="q2"></a>
## Q2. 코드 접근과 Diff 처리

### 2.1 코드 접근: 어떤 경로로 무엇을 가져오는가

| 필요 | 수단 | 조건/플래그 | 대체 경로 | 근거 | 검증 |
|---|---|---|---|---|---|
| 변경 파일 목록·패치 | **Provider API**(GitHub `pulls.listFiles`, GitLab `MergeRequests.allDiffs`). `lastAnalyzedCommit`이 있으면 compare(base...head) 결과를 PR 파일 목록과 교집합 | 항상. 증분이면 compare | 없음. 패치가 없는 파일은 주 경로에서 재조회하지 않음 | `libs/code-review/infrastructure/adapters/services/pullRequestManager.service.ts:295-342`, `libs/platform/infrastructure/adapters/services/github/github.service.ts:4020-4084,4158-4212`, `gitlab.service.ts:2236-2263` | 코드 확인 |
| Azure 패치 | 기준·대상 파일 본문에서 `diff` 라이브러리 `createTwoFilesPatch`로 계산(context 3) | Azure Repos | - | `azureRepos/azureRepos.service.ts:4037-4049` | 코드 확인 |
| 변경 파일 전체 본문 | GitHub는 GraphQL 50개 배치(blob SHA), 실패 시 REST `getContent`. 다른 Provider는 REST 파일별(동시성 30). REST의 `ref`는 **브랜치명**(SHA 아님), 오류 시 base ref | `enrichFilesWithContent`가 항상 실행 | 배치 실패→REST | `pullRequestManager.service.ts:354-484`, `github.service.ts:4982-5096,5108-5260` | 코드 확인 |
| 패치 누락(대용량·바이너리) | PR 전체 `.diff`를 받아 파일별 패치 보강 | **RunAnalyzersStage에서 샌드박스가 있고 분석 도구가 켜진 경우에만** | 아니면 패치 없는 채로 유지 | `run-analyzers.stage.ts:83-94,248-291`, `github.service.ts:2834-2890` | 코드 확인 |
| 저장소 체크아웃(모델 도구용) | **샌드박스**: `git init` + `git fetch --depth=1 <PR refspec>` + checkout | `changedFiles`가 비어 있지 않으면 시도. 제공자는 `SANDBOX_PROVIDER`(`null`/`local`/`e2b`), 기본 `auto`는 `API_E2B_KEY`가 있으면 E2B, 없으면 로컬 | 샌드박스 없음 → self-contained(diff만) | `create-sandbox.stage.ts:81-87`, `libs/sandbox/modules/sandbox.module.ts:26-51` | 코드 확인 |
| 로컬 클론 위치 | `os.tmpdir()/kodus-sandbox-XXXX`(`mkdtemp`), 훅 비활성, depth 1 | 로컬 제공자 | - | `libs/sandbox/infrastructure/providers/local-sandbox.service.ts:115,138-206` | 코드 확인 |
| E2B 클론 | 원격 VM의 `/home/user/repo`, `git fetch --depth=1`. 따뜻한 샌드박스는 `fetch + checkout -f + clean -fd`로 재동기화 | E2B 제공자 | - | `libs/sandbox/infrastructure/providers/e2b-sandbox.service.ts:41,407-470,572-593,754-830` | 코드 확인 |
| PR 참조 | GitHub `refs/pull/N/head`, GitLab `refs/merge-requests/N/head`, Bitbucket DC `refs/pull-requests/N/from`, Bitbucket Cloud `refs/heads/<branch>`, Azure `refs/pull/N/merge`. PR 모드에는 **SHA 고정 옵션이 없음**(CLI 전용) | - | - | `local-sandbox.service.ts:1140-1164`, `libs/code-review/pipeline/services/clone-params-resolver.service.ts:108-129` | 코드 확인 |
| 샌드박스 획득 실패 | 3회 재시도(`createWithRetry`), 실패하면 로그만 남기고 계속 | 제공자 불가 또는 `cloneParams` 없음이면 `NULL_SANDBOX_INSTANCE` | self-contained | `libs/sandbox/infrastructure/services/sandbox-lease-manager.service.ts:730-758`, `create-sandbox.stage.ts:197-227` | 코드 확인 |
| AST/call graph | 샌드박스 안에서 외부 npm CLI `@kodus/kodus-graph@0.3.0`(bun 전역 설치) 실행. `repo.astGraphStatus === READY`이면 DB 기준선 서브그래프, 아니면 `git show`로 base 그래프를 재구성하는 legacy 경로 | `sandbox.run` 존재 && `!adaptiveProfile.dropCallGraph` | 실패 시 call graph 비움+경고 | `agent-review.stage.ts:601-677`, `libs/code-review/infrastructure/adapters/services/graph/graph-context.service.ts:41-134,191-262` | 코드 확인 |
| `apps/ast-cli` | AST 그래프 빌드 잡을 enqueue하는 백필 스크립트. **리뷰 경로 아님** | - | - | `apps/ast-cli/src/main.ts:1-40` | 코드 확인 |

- **로컬/clone/API/샌드박스 구분**: 파일·패치는 Provider API로, 저장소 탐색은 샌드박스 체크아웃으로 나뉜다. 백엔드에 git 클라이언트 라이브러리는 없고(`simple-git` 등은 `apps/cli`에만 있음) 클론은 샌드박스 제공자가 `git` 바이너리를 호출한다. 근거: [05](05-dependencies.md)의 의존성 조사. 코드 확인(부정 grep).
- **Base / Head / Merge Base**: 증분이면 `lastAnalyzedCommit`(base) ~ 현재 head를 compare. 일반 리뷰는 PR 파일 목록. merge base를 명시적으로 계산하는 코드는 활성 경로에서 확인하지 못했다(미확인). 미커밋 변경은 해당 없음(CLI 경로 제외).
- **"전체 저장소에 접근 가능"과 "전체 코드를 모델에 넣는다"**: 전체 파일 본문은 4단계에서 API로 받아 오지만, 오케스트레이터가 에이전트 입력에서 **본문을 제거**한다(`review-orchestrator.service.ts:186-194`: "Agents access full source on demand via readFile in the sandbox"). 프롬프트에는 번호 붙은 diff만 들어가고, 모델은 도구로 필요한 부분만 읽는다. 예외로 샌드박스가 없는 self-contained 모드에서는 파일 본문이 프롬프트에 inline된다(`prompt-builder.ts:1010-1016` docstring, 조사 에이전트 확인). 코드 확인.
- **전체 파일이 외부로 나가는 경우**: ValidateSuggestionsStage가 파일 전체 본문을 Morph SDK `applyEdit`(외부 SaaS)로 보낸다. `enableCommittableSuggestions`이고 GitHub이고 지원 언어일 때만(`validate-suggestions.stage.ts:138-162,486-545`). 코드 확인. Morph 없이도 리뷰는 동작한다(해당 단계는 `partial` 심각도).

### 2.2 실행 중 SHA 일관성 (중요)

**Head SHA가 하나로 고정되지 않는다.** 코드 확인 + 추론.

| 대상 | 사용하는 SHA/ref | 근거 | 검증 |
|---|---|---|---|
| 웹훅이 준 `pullRequest.head.sha`/`head.ref` | 체크런 생성, CI 증거, 캐시 키, 댓글 앵커 후보 | `libs/common/utils/webhooks/github.ts:50-72`, `libs/code-review/infrastructure/observers/code-review-pipeline.observer.ts:38-49,71-90`, `load-ci-evidence.stage.ts:52-69` | 코드 확인 |
| 파일 목록·패치 | 호출 시점의 **라이브** 값 | `github.service.ts:4186-4190` | 코드 확인 |
| 파일 본문 | 브랜치명 `head.ref` 기준 | `github.service.ts:5014-5019` | 코드 확인 |
| 샌드박스 체크아웃 | `refs/pull/N/head`의 **그 시점 팁** | `local-sandbox.service.ts:1140-1164` | 코드 확인 |
| 인라인 댓글 앵커 | 웹훅 head SHA가 **지금도 PR에 속해 있으면** 그것, 아니면 라이브 마지막 커밋. 이 값이 다음 증분의 `lastAnalyzedCommit`이 됨 | `libs/code-review/infrastructure/adapters/services/commentManager.service.ts:1225-1251` | 코드 확인 |

**실행 중 새 푸시를 취소·폐기하는 장치는 없다**(`supersed|stale head|headShaChanged|cancelPrevious|abortPrevious|sha mismatch|headSha !==`를 `libs apps`에서 검색, 해당 없음). 존재하는 것은 다음뿐이다.

1. 댓글 앵커를 "리뷰가 읽은 head"에 고정하려는 시도(위 표 마지막 행). 코드 주석이 의도를 설명한다: "A push landing during the review would otherwise move every anchor to a tree this review never looked at".
2. `synchronize`에서 force-push로 보이면(`payload.before`가 PR 커밋에 없음) `sandbox.invalidate` outbox를 쓰는 것(`githubPullRequest.handler.ts:229-309`, `libs/sandbox/domain/events/sandbox-invalidate.event.ts:1-8`). 샌드박스를 **획득 중인** 리뷰는 샌드박스 없이 계속하고(`create-sandbox.stage.ts:198-216`), 이미 보유한 리뷰는 멈추지 않는다(추론).
3. 자동 승인 cron이 라이브 head와 `lastAnalyzedCommit`을 비교하는 사후 검사(`apps/api/src/cron/CheckIfPRCanBeApproved.cron.ts:499-547`, 조사 에이전트 확인).
4. 새 푸시의 `CODE_REVIEW` 잡은 락 또는 진행 중 execution 행과 충돌하며, **비명령 원점이면 그냥 버려진다**(`automationCodeReview.ts:185-246,394-396`, `libs/code-review/domain/errors/pr-review-in-progress.error.ts:3-15`). 따라서 가장 최근 커밋은 다음 이벤트나 `@kody review` 전까지 리뷰되지 않을 수 있다(추론).
5. 도구 읽기(샌드박스·`head.ref` 본문)와 앵커 SHA가 다를 수 있어 줄 불일치가 날 수 있다. 이를 `commentManager.service.ts:1515-1652`의 최대 3회 위치 보정 재시도가 완화한다(추론).

### 2.3 Diff 처리

**파일 변경 객체**: `FileChange` (`libs/core/infrastructure/config/types/general/codeReview.type.ts:228-256`). 필드: `filename, sha, status, additions, deletions, changes, patch, previous_filename, fileContent, patchWithLinesStr, astFormattedContent` 등. 코드 확인.

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| GitHub 빌더 | `filename, sha, status, additions, deletions, changes, patch`만 유지. **`previous_filename`을 버림** → rename은 새 이름으로만 리뷰되고 구경로 정보 없음 | `github.service.ts:4192-4200` | 코드 확인 / 추론(영향) |
| GitLab 빌더 | `filename = new_path`, `patch = diff` | `gitlab.service.ts:2251-2262` | 코드 확인 |
| 삭제 파일·ignorePaths | `status === 'removed'` 또는 glob 일치는 분석에서 제외, 분석 도구용으로만 보관. glob은 picomatch `dot: true` | `fetch-changed-files.stage.ts:99-111,143-145,180-182`, `libs/common/utils/glob-utils.ts:41-44` | 코드 확인 |
| 대규모 변경 | 2000파일 초과면 SKIPPED. (같은 파일의 주석에는 레거시 한도 350도 언급) | `fetch-changed-files.stage.ts:38-41,223-239` | 코드 확인 |
| 바이너리/패치 누락 | `patch` 없는 파일은 `patchWithLinesStr` 없음, 프롬프트는 `patch ?? ''`. 주 경로에서 재조회 없음 | `fetch-changed-files.stage.ts:251-253`, `prompt-builder.ts:1053` | 코드 확인 |
| **주변 줄 확장** | **활성 파이프라인에는 hunk 주변 줄 확장 알고리즘이 없다.** diff는 Provider가 준 hunk 그대로(Azure만 context 3). 문맥은 모델이 `readFile`로 읽는다. 검색어 `expandContext|contextLines|surrounding lines|relevantContent|extractRelevantContent`는 레거시 파일 단위 코드(`base-file-review.abstract.ts`, `libs/ee/codeReview/fileReviewContextPreparation/…`)에만 있고 주입처가 없음 | `libs/code-review`, `libs/ee`, `libs/common/utils` 검색 | 코드 확인(부정 grep) |
| 문자열 처리 | `libs/common/utils/patch.ts`: `handlePatchDeletions/omitDeletionHunks`(삭제만 있는 hunk 제거, 8-64), `convertToUnifiedDiffWithLineNumbers`(새 파일 기준 줄 번호 부여, 50,000줄 절단, 208-245) | `libs/common/utils/patch.ts:8-64,74,208-245` | 코드 확인 |
| 유효 줄 범위 | `extractValidDiffLines`가 **원본 patch**에서 RIGHT 측 범위를 계산 | `agent-review.stage.ts:135-180` | 코드 확인 |
| `diff` 라이브러리 | `createTwoFilesPatch`(Azure), `parsePatch`(committable suggestion 검증) | `azureRepos.service.ts:4037-4049`, `validate-suggestions.stage.ts:18,279-376` | 코드 확인 |
| AST/정규식 | 주변 줄 확장이 없으므로 해당 없음. 함수 경계 파악은 모델 도구와 call graph(kodus-graph, 외부 CLI)가 맡음 | - | 코드 확인 |

**토큰 초과 처리** (`libs/code-review/infrastructure/agents/collaborators/context-fit-planner.ts`): 글자/토큰 4(`CHARS_PER_TOKEN = 4`, 35), 프롬프트 예산 비율 0.55(43), 정적 오버헤드 62,000자(50). `chunkFilesByTokenBudget`(237-282)는 **파일 순서대로 탐욕적으로** 묶고 한 파일의 diff를 쪼개지 않는다(너무 큰 단일 파일은 자체 청크). 청크는 순차 실행되며 각 청크가 finder+verifier를 따로 돈다(`libs/code-review/infrastructure/agents/providers/base-code-review-agent.provider.ts:421-505`, `collaborators/batch-runner.ts:47,86-187`). 청크 간 dedup은 파이프라인 후반의 LLM dedup에서 일어난다. 저신호 파일(테스트·md·css)은 큰 PR에서 먼저 걸러진다(68-77, 225-235). 코드 확인. 진짜 tiktoken은 `libs/llm/token-estimate.ts:11,25`에서 BYOK 제한기 등에 쓰이고, 사전 예산 추정 자체는 4글자 비율이다(위 파일 17-34의 주석).

**Provider가 diff를 잘라 반환했을 때**: GitHub/GitLab의 주 경로에서는 복구하지 않는다(패치 누락 파일은 패치 없이 진행, 복구는 분석 도구 단계에서만). 코드 확인.

**줄 번호 변환**
- 모델 입력: 새 파일 기준 번호(컨텍스트·`+` 줄에 번호, `-` 줄은 공백). 코드 확인: `patch.ts:233-241`.
- 모델 출력 → 유효성: finding의 줄이 diff hunk와 겹치지 않으면 `DISCARDED_BY_CODE_DIFF`로 버리고, 겹치면 스냅. 줄이 없으면 첫 hunk로. `agent-review.stage.ts:224-286,992-1041`. 코드 확인.
- 게시: 댓글 범위는 `calculateCommentStartLine/EndLine`(15줄 초과 범위는 시작 줄 하나로 축약, `libs/common/utils/comment-builder.utils.ts:10-40`). GitHub는 `pulls.createReviewComment({line, start_line, side:'RIGHT', commit_id, path})`(`github.service.ts:4353-4364`). GitLab은 `position{baseSha, startSha(versions[0]), headSha(리뷰한 커밋), newPath, newLine, endLine}`로 discussion 생성(`gitlab.service.ts:2461-2502`)하고 게시 전에 `resolveAddedLineAnchor`로 추가된 줄에 스냅(`create-file-comments.stage.ts:434-490`). 줄 불일치는 `start_line=line`, 이어서 `line=start_line`로 최대 3회 재시도(`commentManager.service.ts:1515-1652`). 코드 확인.
- Azure·Forgejo·Bitbucket 게시 로직: **미확인**(열지 않음).

### 2.4 짧은 예 (정적 추적, 미실행)

입력 `src/foo.ts`, 상태 `modified`, GitHub `file.patch`:

```
@@ -10,4 +10,5 @@ export class Foo {
   const a = 1;
-  const b = 2;
+  const b = 3;
+  const c = 4;
   return a;
 }
```

1. `changedFiles` 항목: `{filename:'src/foo.ts', status:'modified', additions:2, deletions:1, patch:<원본>, fileContent:<head 본문>}`.
2. `handlePatchDeletions`는 `+` 줄이 있으므로 hunk를 유지(`patch.ts:30-64`).
3. `convertToUnifiedDiffWithLineNumbers`가 모델이 보는 텍스트를 만든다(`patch.ts:233-241`).
```
## file: 'src/foo.ts'
@@ -10,4 +10,5 @@ export class Foo {
    10    const a = 1;
       -  const b = 2;
    11 +  const b = 3;
    12 +  const c = 4;
    13    return a;
    14  }
```
4. 오케스트레이터가 `fileContent`를 제거(`review-orchestrator.service.ts:186-194`). 프롬프트에는 `### src/foo.ts`와 위 diff 블록이 들어간다(`prompt-builder.ts:1045-1078`).
5. `extractValidDiffLines(file.patch)`는 `[[10,14]]`. 12줄 finding은 유지, 30줄은 버려짐(`agent-review.stage.ts:1004-1041`).
6. 게시: `createReviewComment({line:12, side:'RIGHT', commit_id:<앵커 SHA>, path:'src/foo.ts'})`.

### 2.5 Q2 지원 수준

**부분 지원.** 파일·패치·본문은 Provider API, 저장소 탐색은 샌드박스로 확보하고 줄 매핑·재시도가 구현돼 있다. 그러나 주변 줄 자동 확장은 활성 경로에 없고, Head SHA가 하나로 고정되지 않으며, rename 구경로는 GitHub 빌더에서 버려지고, Provider가 자른 diff를 복구하지 않는다.

## 경로 사전 (짧은 이름 → 풀 경로)

- `github.service.ts`: `libs/platform/infrastructure/adapters/services/github/`; `gitlab.service.ts`: `libs/platform/infrastructure/adapters/services/`; `azureRepos.service.ts`: `libs/platform/infrastructure/adapters/services/azureRepos/`
- `pullRequestManager.service.ts`, `commentManager.service.ts`: `libs/code-review/infrastructure/adapters/services/`
- `*.stage.ts`: `libs/code-review/pipeline/stages/`
- `prompt-builder.ts`: `libs/code-review/infrastructure/agents/prompts/`; `review-orchestrator.service.ts`: `libs/code-review/infrastructure/agents/`
- `local-sandbox.service.ts`, `e2b-sandbox.service.ts`: `libs/sandbox/infrastructure/providers/`
- `patch.ts`, `glob-utils.ts`, `comment-builder.utils.ts`: `libs/common/utils/`
- `automationCodeReview.ts`: `libs/automation/infrastructure/adapters/services/processAutomation/strategies/`
- `outbox-message.repository.ts`: `libs/core/workflow/infrastructure/repositories/`
