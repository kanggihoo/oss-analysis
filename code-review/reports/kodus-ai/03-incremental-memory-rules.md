# kodus-ai — 증분 리뷰(Q6)·장기 메모리(Q7)·팀 규칙(Q8)·Jira(Q9)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q6, Q7, Q8, Q9
- 검증 수준 요약(검증 열이 있는 표의 행을 스크립트로 센 값, 2026-10-13 재집계. 복수 표기 행은 각 수준에 중복 계산하고 검증 열이 없는 표·본문 서술은 제외): 코드 확인 37 / 실행 확인 0 / 추론 6 / 미확인 0
- 실행 여부: **정적 추적만**
- 줄 번호 재대조(2026-10-13): `path:range` 약 205개를 모두 열어 확인했다. 줄 번호·식별자가 어긋난 인용 5건과 서술 오류 6건을 고쳤다(수정한 곳에 "2026-10-13 정정"을 표시). 긴 범위는 경계와 핵심 식별자 위주로 확인했고 본문 전체를 읽지는 않았다. 8.1·8.4·"조직·팀 범위 전달 요약"은 범위 키 표를 추가해 다시 썼다.
- 표기: `[ee]`는 `ee/` 경로 또는 `.ee.` 파일명(라이선스 규칙 대상, [05 6절](05-dependencies.md#license)). 조사 에이전트가 연 줄 번호 중 일부(규칙 필터, 설정 로더, 프롬프트 위치, 기본 설정값)는 작성자가 재대조했다.

<a id="q6"></a>
## Q6. 증분 리뷰

### 6.1 비교 기준

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 기준점 | 같은 팀 automation·PR 번호·저장소의 **가장 최근 `SUCCESS` execution**의 `dataExecution.lastAnalyzedCommit` | `libs/code-review/pipeline/stages/validate-new-commits.stage.ts:52-72`, `libs/automation/infrastructure/adapters/services/processAutomation/strategies/automationCodeReview.ts:287-296` | 코드 확인 |
| 새 커밋 계산 | 커밋 목록에서 `lastAnalyzedCommit` 다음부터 슬라이스 | `validate-new-commits.stage.ts:143-148` | 코드 확인 |
| 변경 파일 | compare(base...head)와 PR 현재 파일 목록의 교집합(병합으로 들어온 파일 제외) | `libs/platform/infrastructure/adapters/services/github/github.service.ts:4054-4083` | 코드 확인 |
| 고아 커밋(리베이스·force-push) | 기준 커밋이 PR에 없으면 `forceFullRerun`+`orphanedBaseCommit`, 전체 리뷰로 폴백 | `validate-new-commits.stage.ts:143-179` | 코드 확인 |
| 새 커밋 없음 | `SKIPPED` "No changes detected since last review". 명령(`command*`) 원점은 우회 | `validate-new-commits.stage.ts:316-364` | 코드 확인 |
| `lastAnalyzedCommit` 설정 | 게시 성공 경로에서 리뷰가 읽은 head(PR에 아직 속해 있으면) 또는 라이브 마지막 커밋. 래퍼 실패 시 `null`→다음은 전체 리뷰 | `libs/code-review/infrastructure/adapters/services/commentManager.service.ts:1225-1251`, `automationCodeReview.ts:779-792` | 코드 확인 |
| **오직 SUCCESS만 기준** | ERROR/PARTIAL_ERROR 이후에는 더 오래된 SUCCESS 실행 또는 전체 리뷰가 기준 | `automationCodeReview.ts:667-692`+위 필터 | 추론 |
| 명령 강제 | `command-force`는 항상 전체. 일반 `command`는 이전 실행이 `PRLevelReviewStage`/`FileAnalysisStage`에서 실패했을 때만 강제인데 **이 두 이름은 현재 단계 목록에 없다**(죽은 분기로 보임) | `validate-new-commits.stage.ts:31-38,253-308`, `code-review-pipeline.strategy.ts:70-109` | 추론 |

GitLab 쪽 트리거 필터는 별도다: MR `update` 이벤트는 `last_commit.id !== oldrev`일 때만(새 커밋), 설명 수정은 무시, draft→ready 전환은 허용(`libs/platform/infrastructure/webhooks/gitlab/gitlabPullRequest.handler.ts:54-103`). GitHub는 `synchronize`를 모두 통과시킨다(`apps/webhooks/src/controllers/github.controller.ts:36-50`). 코드 확인.

### 6.2 중복 이벤트·연속 업데이트·재시도

| 상황 | 장치 | 근거 | 검증 |
|---|---|---|---|
| 같은 웹훅 재전송 | **enqueue 시점 SHA 기반 중복 키 없음.** `maxRetries: 1`. 사실상의 SHA 멱등성은 증분 기준(`lastAnalyzedCommit`) 때문에 "새 커밋 없음"으로 SKIPPED되는 것뿐 | `libs/core/workflow/application/use-cases/enqueue-code-review-job.use-case.ts:35-61`, `validate-new-commits.stage.ts:346-364` | 코드 확인 |
| 같은 PR 동시 실행 | PG advisory 락 `CODE_REVIEW:org:repo:pr`(TTL 60초, 갱신 없음, 락 서비스 장애 시 fail-open)+30분 내 `IN_PROGRESS` execution 검사. 리뷰는 최대 105분 돌 수 있으므로 60초 후에는 execution 행 검사만 남는다 | `automationCodeReview.ts:42,163-246`, `libs/core/workflow/infrastructure/distributed-lock.service.ts:9-35,94-194` | 코드 확인 |
| 충돌한 **비명령** 실행 | 조용히 버려짐(`refuseCommand`가 명령이 아니면 반환). 새 푸시가 진행 중 리뷰와 겹치면 최신 커밋이 다음 트리거까지 미리뷰일 수 있음 | `automationCodeReview.ts:185-246,394-396`, `libs/code-review/domain/errors/pr-review-in-progress.error.ts:3-15` | 코드 확인 + 추론 |
| 충돌한 **`@kody review` 명령** | `PrReviewInProgressError`를 던져 잡 프로세서가 지연 재시도(deferral) 후 한도 초과 시 PR에 거절 안내 | `libs/code-review/workflow/pr-review-deferral.service.ts:37-101`, `code-review-job-processor.service.ts:255-272,322-359` | 코드 확인 |
| 메시지 재전달 | inbox `(consumerId,messageId)` 원자적 claim. 이미 PROCESSED면 skip | `libs/core/workflow/infrastructure/workflow-job-consumer.service.ts:387-430` | 코드 확인 |
| 파이프라인 중 크래시 | **체크포인트 없음**(`PipelineStateManager.saveState/loadState` 호출처 없음). 실행 행이 `IN_PROGRESS`로 남고 watchdog이 180분 후 정리, 스테일 잡 리퍼가 `PROCESSING` 180분 초과 잡을 FAILED로 | `libs/core/workflow/engine/state/pipeline-state-manager.service.ts:25-86`, `apps/api/src/cron/staleReviewWatchdog.cron.ts:20-37`, `outbox-relay.service.ts:73,500-585` | 코드 확인 |
| 재시도로 댓글 중복 | 게시 전에 **기존 플랫폼 댓글을 조회하지 않는다**. 이전 결정은 게시 후에 저장된다. 게시 중 크래시/5xx 재시도는 중복 댓글 가능성이 있다 | `commentManager.service.ts:1283-1294,1568-1584`, `create-file-comments.stage.ts:314-340` | 추론(코드 정황) |
| 모든 인라인 게시 실패 | 파이프라인 오류를 쌓지 않고 `lastAnalyzedCommit`이 전진해 SUCCESS로 끝날 수 있음. 실패한 finding은 이후 증분에서 재시도되지 않음 | `create-file-comments.stage.ts:189-219` | 추론 |

### 6.3 실행 중 Head SHA 변경 시 취소·폐기

**없다.** [01 2.2절](01-execution-and-diff.md#q2) 참조. 취소 장치는 없고, 댓글 앵커 고정·샌드박스 무효화(force-push 휴리스틱)·사후 자동 승인 검사만 있다. `Pipeline`은 취소 신호를 확인하지 않는다(`pipeline-executor.service.ts`에서 `parentSignal|aborted|AbortSignal` 검색 결과 없음). `libs/code-review/pipeline`에는 필드 선언(`context/code-review-pipeline.context.ts:298-302`의 `parentSignal?: AbortSignal`)과 에이전트 루프로의 전달(`build-orchestrator-input.ts:158`)만 있고 실행기·단계가 확인하는 곳은 없다. 에이전트 루프만 신호를 소비한다(2026-10-13 정정: 이전 "검색 결과 없음"은 필드 선언·전달을 놓친 부정확한 문구). 코드 확인(부정 grep)+추론.

### 6.4 이전 댓글의 유지·수정·해결

| 항목 | 동작 | 근거 | 검증 |
|---|---|---|---|
| 이전 요약 댓글 | GitHub에서 `<!-- kody-codereview-completed-… -->` 태그를 찾아 접기(minimize)하고 **매 실행 새 댓글**을 만든다. 최종 요약은 그 댓글을 수정 | `libs/code-review/pipeline/stages/initial-comment.stage.ts:33-67`, `commentManager.service.ts:928-939,1118-1132,2774-2910` | 코드 확인 |
| 구현된 제안의 스레드 | `implementationStatus`가 구현됨인 제안의 스레드를 CreateFileCommentsStage 시작에서 resolve | `create-file-comments.stage.ts:100-106`, `libs/code-review/infrastructure/adapters/services/suggestion.service.ts:2080-2170` | 코드 확인 |
| 구현 여부 판정 | `synchronize`마다 별도 잡 `CHECK_SUGGESTION_IMPLEMENTATION`(LLM이 이후 커밋 패치로 판정) | `githubPullRequest.handler.ts:198-227`, `implementation-verification.processor.ts:109-250` | 코드 확인 |
| 이전 결정을 프롬프트로 | `PreviousReviewDecisions`(Kody가 이 PR에 이미 게시한 제안, "never report the problem an entry raised again") | `libs/code-review/infrastructure/agents/prompts/prompt-builder.ts:415-419` | 코드 확인 |
| 마커 | `<!-- kody-codereview -->`는 Kody 자신의 댓글에 든 명령을 사용자 명령으로 오인하지 않게 하는 용도. 중복 방지 키가 아님 | `libs/common/utils/codeManagement/codeCommentMarkers.ts:60,296-299`, `githubPullRequest.handler.ts:460-467` | 코드 확인 |

### 6.5 Q6 지원 수준

**부분 지원.** 직전 SUCCESS 기준 증분·고아 커밋 폴백·명령 지연 재시도는 있다. 그러나 이벤트 단위 SHA 멱등 키가 없고, 실행 중 Head 변경 취소가 없으며, 체크포인트가 없고, 게시 전 기존 댓글 조회가 없다.

<a id="q7"></a>
## Q7. 장기 메모리 (쓰기와 읽기를 모두 추적)

### 7.1 결론

**피드백(반응·답글·resolve)에서 학습해 다음 PR 리뷰에 쓰는 루프는 이 SHA에서 동작하지 않는다.** 반응 수집(쓰기)과 임베딩·k-means 기반 필터(읽기 로직) 코드는 있지만, 읽기의 유일한 진입점 `KodyFineTuningStage`가 파이프라인에 등록되지 않았다. 공식 문서도 같은 말을 한다: "Reaction-based fine-tuning is not currently active. 👍/👎 reactions and suggestion implementation status can be recorded, but they do not train a model, build preference clusters, or filter the next review."(`docs/en/how_to_use/code_review/learning/kody_learning.mdx:7`) — 반응 기반 파인튜닝은 현재 비활성이다. 코드 확인.

따라서 "피드백 **학습**"이라 부르지 않는다. 반면 아래 두 가지는 실제 쓰기+읽기 경로가 있다: (a) `type: MEMORY` Kody Rule, (b) 같은 PR 이력.

### 7.2 쓰기·읽기 매트릭스

| 저장소 | 쓰는 쪽 | 읽는 쪽 | 리뷰 시 읽기? | 학습인가 |
|---|---|---|---|---|
| Mongo `kodyRules` 컬렉션(규칙과 MEMORY, 조직 문서 1개에 `rules` 배열) | UI/API, MCP 도구, 병합 PR 동기화, 생성 cron, 라이브러리 추가, 중앙 설정 동기화, 채팅 메모리 도구 | `CodeBaseConfigService.getConfig`가 리뷰마다 조직 단위로 읽음 → 규칙 judge·메모리는 모든 비규칙 에이전트 시스템 프롬프트 | **예** (`libs/ee/codeBase/codeBaseConfig.service.ts:120-122,167-183`, `prompt-builder.ts:576-577,1080-1088`) | 사람이 큐레이션한 영속 지식: 예. 사람 리뷰어의 PR 댓글에서 자동 생성: 예(아래 7.4). **Kody 댓글에 대한 반응/답글에서 파생: 아님** |
| Mongo `codeReviewFeedback`(`{organizationId, suggestionId, reactions{thumbsUp,thumbsDown}, comment, pullRequest}`) | cron `CodeReviewFeedbackCronProvider`(최근 7일 SUCCESS/PARTIAL_ERROR 실행) → RabbitMQ consumer → `SaveCodeReviewFeedbackUseCase`(바뀐 카운트만 기록) | `KodyFineTuningService`(미연결), 이슈 상세 UI, 분석 적재 | **아니오** | 아니오. 카운터만, 수명 관리 없음 (`libs/core/infrastructure/queue/messageBroker/consumers/codeReviewFeedback.consumer.ts`, `libs/code-review/application/use-cases/codeReviewFeedback/save-feedback.use-case.ts:27-153`) |
| PG `suggestion_embedded`(pgvector 컬럼) | `KodyFineTuningService.syncronizeSuggestions`(`startAnalysis` 경유만) | 같은 서비스의 JS 코사인+k-means | **아니오**(호출되지 않음) | 아니오(비활성) |
| Mongo `pullRequests.files.suggestions`(+`implementationStatus`) | 리뷰 파이프라인, 구현 확인 잡 | `PrDecisionStoreService.load`(org+`repository.fullName`+PR 번호, 최근 40건 `MAX_PR_DECISIONS`) | **예**, 같은 PR만 | 같은 PR 이력일 뿐 PR 간 메모리 아님 (`pr-decision-store.service.ts:113-150`, `pr-decision-store.contract.ts:76`) |
| 고객 저장소 Git 브랜치 `kodus/trace/v1`의 JSON | `apps/cli` trace | `LoadExternalContextStage.loadTraceDecisions` | 예, **알파 플래그 `kodus-trace-review-context` 뒤, fail-closed** | 코딩 세션 의도 메모리(경로 기준). 리뷰 피드백 아님. 알파 (`load-external-context.stage.ts:66-101,120-174`) |
| Mongo `kodus-agent-sessions` | 대화 에이전트 | 같은 `threadId` | 아니오(리뷰 경로 밖) | 아니오 |
| PG `analytics.suggestion_feedback` [ee] | `FeedbackIngestionService` | 대시보드 | 아니오 | 분석 전용 (`libs/ee/analytics-warehouse/ingestion/feedback-ingestion.service.ts:30-48`) |
| Mongo `ruleLikes` | UI의 라이브러리 규칙 좋아요 | 라이브러리 목록 | 아니오 | 아니오. **조직 필드 없음**(테넌트 간 전역) |
| Kody Issues(`libs/issues`) | PR 닫힘 시 | UI·MCP 도구 | 아니오 | 결과 저장소일 뿐 |

### 7.3 임베딩 파인튜닝: 코드는 있으나 죽어 있음

- 실행되면 하는 일: 닫힌 PR의 제안 중 비중립 반응 또는 구현된 것을 `suggestion_embedded`에 동기화(OpenAI `text-embedding-3-small`)하고, 50건 이상이면 `ml-kmeans`(`maxIterations: 1`)로 클러스터링한 뒤 새 제안을 클러스터 중심과의 코사인 유사도와 클러스터 피드백 만장일치로 KEEP/DISCARD/UNCERTAIN 판정한다(`libs/kodyFineTuning/infrastructure/adapters/services/kodyFineTuning.service.ts:393-467,548-691,694-1058`). 유사도는 Node에서 계산하며 `<=>` 같은 pgvector 연산자 쿼리는 코드 어디에도 없다. 코드 확인(부정 grep).
- 죽은 이유: `KodyFineTuningStage`는 모듈에 등록(`libs/code-review/pipeline/code-review-pipeline.module.ts:200`)됐지만 `configureStages()`에 없고(`code-review-pipeline.strategy.ts:70-97`), `KODY_FINE_TUNING_CONTEXT_PREPARATION_TOKEN`은 제공·export만 되고 주입처가 없다(`libs/kodyFineTuning/kodyFineTuningContext.module.ts:22-28`). 코드 확인.
- 반응 해석: 👍>👎면 긍정, 반대면 부정, 같거나 없으면 중립으로 버림. 구현됨은 긍정. 무응답은 `pending`이고 프롬프트가 "NOT evidence the developer rejected this"라고 명시(`prompt-builder.ts:398`). 코드 확인.
- 답글·resolve·댓글 수정은 피드백으로 **저장되지 않는다**. 저장소 계약 주석이 거절·설명 신호가 이 단계에 없고 이슈 #1670으로 미뤄졌다고 적는다(원문 "There is no rejection/explanation signal in this phase … issue #1670, deferred", `libs/code-review/domain/contracts/pr-decision-store.contract.ts:11-24`). 코드 확인(주석 인용).
- 수명·신뢰도·삭제·충돌 처리: 없음(규칙 쪽도 버전 이력·만료 없음, 7.2/8.3 참조).

### 7.4 사람 PR 댓글에서 규칙 자동 생성 (과거 리뷰 학습)

피드백이 아니라 **사람 리뷰어의 댓글**에서 규칙을 뽑는다. 쓰기 경로와 읽기 경로가 모두 있다.

- 트리거: cron `KodyLearningCronProvider`(`API_CRON_KODY_LEARNING`). 팀의 `kodyLearningStatus`가 DISABLED이면 건너뛰고, 저장소는 `kodyRulesGeneratorEnabled`(기본 true, `default-kodus-config.yml:1171`)로 선택. 첫 실행은 3개월 백필, 이후 지난 1주 델타 (`apps/api/src/cron/kodyLearning.cron.ts:57-158,293-330`). 코드 확인.
- 필터: 봇 제외, **Kody 자신의 댓글 제외**(`isKodyAuthoredBody`, 자기 피드백 루프 방지), 제외 리뷰어 목록, 100자 이하 제외, 최대 100건 (`libs/code-review/infrastructure/adapters/services/commentAnalysis.service.ts:500-583`).
- 파이프라인: LLM 댓글 필터 → 규칙 생성 → 기존 규칙 대비 LLM dedup → LLM 품질 필터(`commentAnalysis.service.ts:220-345`). 생성 프롬프트: "You are a professional code reviewer, you are great at identifying common patterns."(`libs/common/utils/prompts/kodyRulesGenerator.ts:30`) — 공통 패턴을 찾는 리뷰어.
- 저장: `origin: PAST_REVIEWS`, 승인 게이트가 켜져 있으면 `PENDING`, 아니면 `ACTIVE`(`libs/kodyRules/application/use-cases/generate-kody-rules.use-case.ts:472-495`).
- 읽기: 일반 규칙과 같은 경로(8.2).

### 7.5 "메모리" = `type: MEMORY` 규칙

- 생성: MCP `KODUS_CREATE_MEMORY`(`libs/mcp-server/tools/kodyRules.tools.ts:953-1045`)와 PR 댓글 채팅 에이전트. 채팅 프롬프트가 "도구는 `act`를 선언해야 열리고, 선언하려면 개발자의 지시 문장을 그대로 인용해야 한다"고 **요구**한다(`libs/agents/infrastructure/services/agents/conversation/conversation-prompt.ts:193`). 구현은 도구를 숨기지 않고(숨기면 모델이 도구가 없다고 오판해 철회했다고 주석이 적음) 선언·인용 없는 쓰기를 **실행 시점에 거절 메시지로 돌려준다**(`write-authorization.ts:1-14,40-43`). 프롬프트의 요구와 코드의 실행 시 거절을 구분한다(2026-10-13 정정). 생성형 출처(과거 리뷰·MCP)는 LLM "memory curator"가 create/skip/update를 판정(`libs/ee/kodyRules/service/kodyRules.service.ts:1905-2019,2166-2260,2327-2374` [ee], 프롬프트 `libs/common/utils/prompts/kodyMemoryResolution.ts:15`).
- 읽기: 리뷰 시 활성 메모리가 **평면 목록으로 모든 비규칙 에이전트(bug/security/performance/generalist) 시스템 프롬프트**에 "## Memory Rules (Team Conventions)"로 들어간다. `title`과 `rule`만 쓰고 `path`·키워드로 필터하지 않는다(`prompt-builder.ts:476,574-577,595-608,1080-1088`). 벡터·키워드 검색 없음. 코드 확인.
- 문서가 말하는 `@kody remember` 명령 핸들러는 코드에 없다. 명령은 `@kody -v business-logic`과 일반 `@kody` 대화뿐(`libs/platform/application/use-cases/codeManagement/chatWithKodyFromGit.use-case.ts:55-59`). 코드 확인.

### 7.6 동의 해석 위험

무응답·resolve·코드 수정을 동의로 해석하는 코드는 없다. 무응답은 약한 신호라는 문구가 프롬프트에 있다. 구현됨(`implementationStatus`)은 같은 PR에서 "이 문제는 이미 적용됨"으로만 쓰이며 PR 간 신호로 전파되지 않는다(위 파인튜닝 경로는 죽어 있음). 코드 확인.

### 7.7 Q7 지원 수준

- 피드백 학습(반응/답글→다음 PR 조회): **미지원**. 찾아본 범위: `libs/code-review`, `libs/platform`, `libs/agents`, `libs/ai-engine`, `libs/kodyFineTuning`, `libs/core/.../consumers`에서 `codeReviewFeedback`/`thumbsUp`/`lessons|learnedFrom|feedbackMemory|negativeFeedback|dismissed|wontfix|false positive` 검색 + 읽기 진입점 `KodyFineTuningStage` 호출 추적. 읽기 쪽에서 유일하게 있는 것은 같은 PR 이력.
- 규칙형 메모리(`MEMORY` 규칙)·사람 댓글 기반 규칙 생성: **부분 지원**(구현·읽기 경로 있음, 피드백 파생 아님).

<a id="q8"></a>
## Q8. 팀 규칙

### 8.1 스키마와 소유자

- 저장: Mongo 컬렉션 `kodyRules`, **조직당 문서 1개에 `rules` 배열**(`libs/kodyRules/infrastructure/adapters/repositories/schemas/kodyRules.model.ts:4-28`, `libs/kodyRules/domain/interfaces/kodyRules.interface.ts:45-51`). Postgres에는 설정(`parameters`, `organization_parameters`)만 있다. **규칙에 `teamId` 필드는 없다**(변경 입력과 링크에만 등장). 코드 확인.
<a id="q8-scope"></a>
**규칙과 설정은 범위 키가 다르다 (오독 주의, 2026-10-13 재확인)**: "팀 규칙(Team Conventions)"이라는 프롬프트 헤더·제품 문구와 달리 **규칙 자체에는 팀 키가 없고**, 팀 키가 있는 것은 **설정**이다. 8.1의 "규칙에 `teamId` 없음"과 8.4의 "설정은 팀 키"는 서로 다른 객체 이야기이며 둘을 합쳐 "팀 규칙 지원"이라고 읽으면 안 된다.

| 객체 | 저장소 | 소유·범위 키 | 읽는 쿼리 | 팀 키 | 근거 | 검증 |
|---|---|---|---|---|---|---|
| **Kody 규칙**(표준·MEMORY 모두) | Mongo `kodyRules` | `organizationId` 하나. 문서 1개 안에 `rules[]`. 규칙 필드의 범위는 `repositoryId`(`'global'`은 조직 전체)·`directoryId`·`path`뿐 | `findByOrganizationId(organizationId)` 후 `filterKodyRules`가 PR의 `repositoryId`·`directoryId`로 거름 | **없음**. `IKodyRule`에 `teamId` 필드가 없고(`kodyRules.interface.ts:28-207`, `libs/kodyRules/domain`·`libs/kodyRules/infrastructure/adapters/repositories`에서 `teamId` 검색 일치 없음), 스키마는 `organizationId`만 필수(`kodyRules.model.ts:14-18`). `teamId`는 생성·동기화 요청의 입력과 권한·저장소 확인에만 나타나고 규칙 문서에는 저장되지 않는다(`create-or-update.use-case.ts:68-80,158,592-612`, DTO `change-status-kody-rules.dto.ts:13`, `add-library-kody-rules.dto.ts:40`) | `codeBaseConfig.service.ts:120-122`, `kody-rules-validation.service.ts:98-182`, `kodyRules.model.ts:4-28` | 코드 확인 |
| **코드 리뷰 설정**(`CODE_REVIEW_CONFIG`: 전역·저장소·디렉터리 설정, 리뷰 옵션, 프롬프트 오버라이드) | Postgres `parameters` | **팀**(`team_id`+`active`). 활성 행은 (팀, 키)당 하나로 DB 유일 제약이 있다 | `parametersService.findOne({configKey, team:{uuid: teamId}, active:true})` | **있음** | `codeBaseConfig.service.ts:110-114`, `parameters.model.ts:16-20,32-34`, 마이그레이션 `2026052600000-DedupeAndEnforceOneActiveParameter.ts:49` | 코드 확인 |
| 언어(`LANGUAGE_CONFIG`) | Postgres `parameters` | 팀 | `parametersService.findByKey(key, orgAndTeam)`가 `team_id`로 조회 | 있음 | `codeBaseConfig.service.ts:115-118`, `libs/organization/infrastructure/adapters/repositories/parameters.repository.ts:194-210` | 코드 확인 |
| 조직 설정(BYOK, `KODY_FINE_TUNING_CONFIG`) | Postgres `organization_parameters` | 조직 | `organizationParametersService.findByKey(key, orgAndTeam)` | 없음(조직 키) | `codeBaseConfig.service.ts:824-841`, [04 3절](04-saas-and-isolation.md#3-테넌트-격리-매트릭스) | 코드 확인 |
| 저장소 `kodus-config.yml` | 고객 저장소 기본 브랜치 | 저장소·디렉터리(팀 설정 위에 덮음, 기본 꺼짐) | 8.4절 | 팀 키는 위 `parameters`에서 옴 | 8.4절 | 코드 확인 |

읽기 쪽 결과: 같은 조직의 **모든 팀이 같은 규칙 배열을 읽는다**. 어떤 규칙이 한 PR에 적용되는지는 `repositoryId`·`directoryId`·`path`로만 갈리고, 팀 단위로 규칙 집합을 나누려면 규칙의 `repositoryId`를 해당 팀 저장소로 지정하는 간접 방식뿐이다. 저장소가 한 팀에만 연결된다는 가정이 필요하다(추론: 저장소→팀 연결은 `integration_configs` 쪽이며 이 문서에서 규칙 필터와의 연결은 추적하지 않음). 팀 간 격리가 필요한 우리 서비스 관점에서는 규칙에 팀 키(또는 정책 범위)를 새로 설계해야 한다([06](06-fit.md)).

- `IKodyRule`(`kodyRules.interface.ts:67-207`): 식별(`uuid`, `title`, `rule`, `examples[{snippet,isCorrect}]`, `severity`), 범위(`repositoryId`(`'global'`은 센티널), `directoryId`, `path`(쉼표 구분 glob), `scope`(`file`/`pull-request`), `inheritance`), 출처(`origin`, `sourcePath`, `sourceRepositoryId`, `lastContentHash`, `pinnedSync`), 수명(`status`, `lockedByPlan`, `requestType`, `targetRuleUuid`, `resolvedAt`, `resolvedBy`), 리뷰용 파생(`detector`, `summary`, `atoms`, `contextNeed`, `fileScope`, `compileAttempt`, `centralizedConfig`).
- 열거형(`:451-506`): origin = manual/library/past_reviews/repo_file_sync/global_repo_file_sync/onboarding_repo_analysis/mcp_agent/cli, status = active/rejected/pending/applied/deleted/paused, scope = pull-request/file, type = standard/memory. 코드 확인.
- 범위 계층: **전역 → 저장소 → 디렉터리 그룹**, 그 안에서 `path` glob으로 파일 좁힘. `directoryId`는 설정의 디렉터리 그룹 ID이지 경로가 아니다. 팀 범위·명령별 범위는 없음(찾아본 범위: `libs/kodyRules`, `libs/ee/kodyRules`, `apps/api/src/controllers/kodyRules.controller.ts`). 코드 확인.
- 라이브러리 규칙 808개: `libs/ee/kodyRules/service/data/library-kody-rules.json` [ee]. `origin: LIBRARY`로 복제하는 곳은 `libs/kodyRules/application/use-cases/add-library-kody-rules.use-case.ts:64,104`다(`libs/ee/kodyRules/service/kodyRules.service.ts:627-633`은 감사 로그에 CLONE/CREATE를 기록하는 줄이며, 2026-10-13 정정: 이전에 이 줄을 복제 근거로 인용함). 코드 확인.

### 8.2 읽기 쿼리와 모델 입력 위치

| 단계 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 1 | `getConfig`가 `findByOrganizationId(organizationId)`로 **조직 전체 규칙**을 읽음(팀 필터 없음) | `libs/ee/codeBase/codeBaseConfig.service.ts:120-122` [ee] | 코드 확인 |
| 2 | `filterKodyRules(rules, repositoryId, directoryId, limited)`: ACTIVE(또는 유료 플랜의 `lockedByPlan` PAUSED)만. `PENDING_ADD`(중앙 설정) 제외, 전역은 항상, 저장소 규칙은 `repositoryId` 일치만, 디렉터리 규칙은 `directoryId` 일치. 동일 `rule` 텍스트 중복 제거, `createdAt` 오름차순, **무료 플랜(`limited`)이면 최대 10개**. **우선순위·충돌 해결 없음** | `libs/ee/kodyRules/service/kody-rules-validation.service.ts:98-182,24` [ee] | 코드 확인 |
| 3 | 표준 규칙과 MEMORY로 분리해 `kodyRules`/`kodyMemoryRules`에 저장 → `buildOrchestratorInput`이 `kodyRules`·`memoryRules`로 매핑 | `codeBaseConfig.service.ts:167-183`, `libs/code-review/pipeline/stages/build-orchestrator-input.ts:109,122` | 코드 확인 |

모델 입력 위치:

| 종류 | 위치 | 근거 |
|---|---|---|
| MEMORY | bug/security/performance/generalist 에이전트의 **시스템 프롬프트**, `<Role>/<Mindset>/<Workflow>/<Scope>` 뒤·오버라이드 섹션 뒤, 헤더 `## Memory Rules (Team Conventions)` | `prompt-builder.ts:476,574-577,595-608,1080-1088` |
| 표준 규칙(파일 범위) | `KodyRulesAgentProvider`가 활성 표준 규칙만 골라 **파일당 judge 1회**. 시스템 `SHARD_SYSTEM_PROMPT`, 유저는 `<Rules>`(번호 `[n] title`, description, examples) → PR 제목·설명 → `<FileContent>` → `<File>` diff → `<Context>` → `<PreviousReviewDecisions>` → `<Candidates>` | `kody-rules-agent.provider.ts:124-149`, `kody-rules-sharded.judge.ts:365-393,658-731` |
| 표준 규칙(PR 범위) | 전체 PR 호출 1회(diff 최대 150k자) | `kody-rules-sharded.judge.ts:374,742-797,886` |
| 긴 규칙 | `summary`/`atoms`가 `rule` 대신 사용됨 | `agent-review.stage.ts:357-372` |

핵심 프롬프트: "Only flag lines ADDED in this diff"(`libs/code-review/infrastructure/agents/collaborators/kody-rules-sharded.judge.ts:368`, 이 diff에서 추가된 줄만 지적), "Identify the violated rule by its number … Never invent a number; if a real issue matches no listed rule, DROP it."(같은 파일 `:370`, 규칙은 번호로만 식별하고 목록에 없으면 버린다). 코드 확인.

**디렉터리 규칙 누수 가능성(추론)**: `directoryId`가 해석되지 않았는데 규칙에 `directoryId`가 있으면 저장소 규칙으로 들어간다(`kody-rules-validation.service.ts:144-150`). 설정 해석기는 일치하는 디렉터리 그룹이 2개 이상이면 저장소 설정으로 폴백한다(`codeBaseConfig.service.ts:999-1006`). 그래서 디렉터리 전용 규칙이 PR 전체에 적용될 수 있다(리뷰 시 `path`·`fileScope`만 추가로 거른다, `kody-rules-sharded.judge.ts:810-830`). 유닛 테스트는 찾지 못했다.

`inheritance`와 `getKodyRulesForFile/Folder`는 **리뷰 시 쓰이지 않는다**(호출처는 UI의 상속 규칙 조회 `libs/kodyRules/application/use-cases/get-inherited-kody-rules.use-case.ts:103`와 `findMemories`뿐). 코드 확인.

### 8.3 생성·편집·승인·버전·비활성화

| 항목 | 경로 | 근거 | 검증 |
|---|---|---|---|
| 생성·수정 API | `POST /kody-rules/create-or-update`, `TenantScopeGuard`+`PolicyGuard(Action.Create, ResourceType.KodyRules)` → 유스케이스가 저장소 권한 확인. 중앙 설정이 켜져 있으면 설정 저장소 PR로 라우팅 | `apps/api/src/controllers/kodyRules.controller.ts:106-177`, `libs/kodyRules/application/use-cases/create-or-update.use-case.ts:88-142` | 코드 확인 |
| 영속화 | `KodyRulesService.createOrUpdate`. 무료 한도 초과 규칙은 거절하지 않고 `PAUSED`+`lockedByPlan`으로 생성 | `libs/ee/kodyRules/service/kodyRules.service.ts:540-857` [ee] | 코드 확인 |
| 승인 | `kodyKnowledgeApproval.enabled`(기본 `false`)이면 생성형 지식(PAST_REVIEWS, ONBOARDING_REPO_ANALYSIS, MCP_AGENT)과 `repo_file_sync`가 `PENDING`. `POST /kody-rules/pending/apply`, `/pending/discard`(→REJECTED) | `default-kodus-config.yml:1173-1174`, `libs/common/utils/kody-rules/knowledge-approval.ts:18-30`, `controller :508-545` | 코드 확인 |
| 삭제·비활성화 | 소프트 삭제(DELETED, `updateRulesStatusByFilter` `:1357-1400`, `deleteRuleLogically` `:1402`·`deleteRuleWithLogging` `:1409`), 일시중지(PAUSED)는 플랜 한도 처리(`resolveStatusWithinPlanLimit` `:1471` 부근)와 enum(`libs/kodyRules/domain/interfaces/kodyRules.interface.ts:476-488`)에 있음 | `libs/ee/kodyRules/service/kodyRules.service.ts:1357-1456` | 코드 확인 |
| **버전 관리** | **규칙 버전 이력 없음.** 제자리 수정이고 **규칙 텍스트가 바뀌면 `summary`와 `atoms`를 모두, 예시만 바뀌면 `atoms`만** 버림(`kodyRules.service.ts:801-821`). 감사 이벤트(`AuditLogEvents.KODY_RULES`)만 있음 | `libs/ee/kodyRules/service/kodyRules.service.ts:801-834,627-638,722-734` | 코드 확인 |
| 저장소 파일 동기화 | `.kody/rules/**`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` 등을 발견(`libs/common/utils/kody-rules/file-patterns.ts:8-60`). **병합된 PR**에서 `pull-request.closed` 리스너가 분산 락 아래 동기화. `ideRulesSyncEnabled` 기본 false이며 파일 내 `@kody-sync` 마커가 강제 동기화. `.kody/rules/**`는 LLM 없이 가져오고 그 외는 LLM 추출 | `libs/kodyRules/infrastructure/adapters/listeners/kody-rules-sync.listener.ts:77-185`, `libs/kodyRules/infrastructure/adapters/services/kodyRulesSync.service.ts:429-538,2169-2260`, `default-kodus-config.yml:1170` | 코드 확인 |
| 저장 시 파생 | detector(정규식 라우팅)·`contextNeed`·`fileScope`·`summary`·`atoms`를 저장 시/야간 점검에서 컴파일 | `kodyRules.interface.ts:89-135`, `libs/kodyRules/infrastructure/adapters/services/kody-rule-detector-sweep.service.ts` | 코드 확인(필드), 추론(스케줄) |

**세 가지 구분**: (1) **커스텀 프롬프트**: `v2PromptOverrides`(Postgres 설정, 승인 흐름 없음). (2) **저장·승인되는 팀 규칙**: Mongo 규칙, 버전 이력 없음, 승인 게이트·감사 로그 있음. (3) **자동 정책 엔진**: 찾지 못했다. 가장 가까운 것은 정규식 detector인데 후보를 LLM judge로 라우팅할 뿐이다(`kody-rules-agent.provider.ts:165-197`). 코드 확인.

### 8.4 설정 계층과 우선순위

- 출처: `parameters` 테이블(`configKey=CODE_REVIEW_CONFIG`, **팀 키**, `active`, `version`)(`libs/organization/infrastructure/adapters/repositories/schemas/parameters.model.ts:8-44`). **이 "팀 키"는 설정에만 해당하며 8.1의 규칙에는 적용되지 않는다**([범위 키 표](#q8-scope)). 규칙은 같은 `getConfig` 안에서 조직 단위로 읽혀 위 팀 설정과 병합된 `repository`·`directory` 해석 결과로만 필터된다(`codeBaseConfig.service.ts:110-125,164-173`).
- 병합: `deepMerge(DEFAULT, global, repo, repoFile, directory, directoryFile)`. `deepMerge`는 배열을 **교체**하고 null/undefined는 건너뜀(`codeBaseConfig.service.ts:393-474`, `libs/common/utils/deep/index.ts:7-36`). 디렉터리 해석은 파일의 상위 폴더가 일치하는 그룹이 **정확히 1개**일 때만 그 그룹, 2개 이상이면 저장소 설정(`:935-1017`).
- **저장소의 `kodus-config.yml`은 기본적으로 꺼져 있다**: `kodusConfigFileOverridesWebPreferences`가 `true`일 때만 읽고(기본 `false`, `default-kodus-config.yml:6`), **기본 브랜치**에서 읽으며(PR 브랜치 아님), 기본값에 없는 키는 제거되고 디렉터리 그룹 파일 오버라이드는 미지원(`codeBaseConfig.service.ts:476-498,724-761,781-785`). 저장소 루트 `kodus-config.yml`(31줄)은 kodus-ai 레포 자신의 설정일 뿐이다. 코드 확인.
- 언어(`languageResultPrompt`)는 `LANGUAGE_CONFIG` 파라미터에서 온다(`:115-118,177-179`).
- 웹 UI(`apps/web`)는 같은 모노레포에 있으나 이 분석의 제외 범위라 규칙 편집 UI 동작은 확인하지 않았다(미확인).

### 8.5 Q8 지원 수준

**부분 지원.** 범위(전역/저장소/디렉터리/path)·소유자(조직)·승인 게이트·소프트 삭제·감사 로그·저장소 파일 동기화·사람 댓글 기반 생성이 있다. 우선순위/충돌 해결, 팀 범위, 버전 관리, 자동 정책 엔진은 없고 구현 핵심이 `libs/ee/`다.

<a id="q9"></a>
## Q9. Jira / 요구사항

### 9.1 실제 구현

`AGENTS.md`는 "Project management integrations: Jira, Linear, Azure Boards"라고 하지만 **직접 연동 어댑터는 없다**(찾아본 범위: `libs/`, `apps/`에서 `jira|linear|azure.?boards|PROJECT_MANAGEMENT|AZURE_BOARDS`). 남아 있는 것은 enum(`PlatformType.JIRA`, `AZURE_BOARDS`, `libs/core/domain/enums/platform-type.enum.ts:5,10`), 팀 플래그 계산용 `IntegrationCategory.PROJECT_MANAGEMENT`(`libs/organization/infrastructure/adapters/repositories/team.repository.ts:242-283`), 미사용 `JiraAccessTokenDTO`(`apps/api/src/dtos/jira.dto.ts`)다. 코드 확인.

실제 경로는 **MCP**다.

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 관리형 MCP | `apps/mcp-manager/src/config/managed-mcp-servers.json`: Git Issues, Linear, Atlassian Rovo(Jira 포함), Notion 등, 카테고리 `task-management`. 이름 힌트로 Jira/Linear/Notion/ClickUp/Google Docs 인식 | `apps/mcp-manager/src/config/managed-mcp-servers.json`, `business-logic-validation.stage.ts:76-84` | 코드 확인 |
| 인증·보관 | OAuth 토큰은 `mcp_integration_oauth.auth`에 `EncryptionUtils`로 암호화, `(organizationId, integrationId)` 유일. 연결 `mcp_connections`는 `organizationId` 키. **조직 단위, 팀 단위 아님** | `apps/mcp-manager/src/modules/integrations/entities/mcp-integration-oauth.entity.ts:11-42`, `mcp-connection.entity.ts:18-60` | 코드 확인 |
| 이슈 식별 | PR 본문·제목·브랜치에서 Jira형 키 `/[A-Za-z][A-Za-z0-9_]+-\d+/g`(`ABC-123` 모양 텍스트는 모두 매치), `#N`, `/issues/N` URL, 연결된 MCP 도메인 URL | `business-logic-validation.stage.ts:52,89-97,732-767` | 코드 확인 |
| 필드 추출 | `description`, `acceptanceCriteria`, `criteria`, `requirements`, Atlassian ADF 등을 정규화. **실행당 티켓 1건** | `libs/agents/skills/capabilities/task-context/result-normalization.ts:141-256`, `libs/agents/skills/capabilities/types.ts:1-8` | 코드 확인 |
| 메인 리뷰 입력 | 티켓 내용은 **들어가지 않는다.** finder 유저 프롬프트에는 `<PRContext>`의 PR 제목과 본문 앞 500자만 | `prompt-builder.ts:626-629,1035-1043` | 코드 확인 |

### 9.2 Business Logic 단계의 동작

- 순서: `… → BusinessLogicValidationStage → CreateSandbox → RunAnalyzers → AgentReview → …`(`code-review-pipeline.strategy.ts:70-80`). **샌드박스보다 앞**이라 저장소 접근이 없다.
- 실행 게이트(`evaluateSkip`, `business-logic-validation.stage.ts:401-471`): `reviewOptions.business_logic` 켜짐(기본 `true`, `default-kodus-config.yml:1148`) + task-management MCP 연결 + PR 본문·제목·브랜치에 연결된 MCP와 맞는 티켓 키·링크 + **PR당 1회**(`businessLogicValidatedAt`). `@kody review --force`와 `@kody -v business-logic`가 재실행. docs는 "every PR review"라고 하지만 코드는 위 조건이다.
- 에이전트: `BusinessRulesValidationAgentProvider`. PR 본문 → MCP로 티켓 문맥 → 품질 분류(EMPTY/MINIMAL/PARTIAL/COMPLETE, 약하면 LLM 전에 중단) → diff 조회 → **도구 없는 LLM 1회**(`tools: new InMemoryToolRegistry([])`, `maxSteps: 1`)(`libs/agents/infrastructure/services/agents/business-rules-validation/blueprint.ts:147-394`, `blueprint.tooling.ts:74-132`, `businessRulesValidationAgent.ts:644-663`).
- 입력: 번호 매긴 `ACCEPTANCE_CRITERIA`, `FULL_TASK_CONTEXT`, `PR_DIFF`, `PR_DESCRIPTION`(`analysis-prompt.builder.ts:6-65`). 기준 추출 폴백은 불릿·번호 목록 파싱(`:116-148`).
- 핵심 프롬프트: "Check EACH acceptance criterion against the PR_DIFF. For each one, determine: IMPLEMENTED, MISSING, or PARTIAL."(`analysis-prompt.builder.ts:56`) — 각 기준을 diff와 대조해 구현/누락/부분으로 판정. "Quote the source: Each finding MUST include the exact text from the task that establishes the requirement. If you cannot quote a specific sentence, the finding is INVALID"(`libs/agents/skills/business-rules-validation/SKILL.md:72`) — 티켓 원문 인용이 없으면 finding 무효. "The analyzer sees the task context and the PR diff, not the entire codebase."(`SKILL.md:77`).
- **구분**: 요구사항 텍스트를 입력에 넣고 기준별로 판정하지만, 근거는 **PR diff 안에서만** 찾는다. diff에 없으면 "누락"이 되고 저장소 전체에서 구현 근거를 찾는 단계는 없다(도구 없음). 선택적 `BusinessRulesVerifier`(기본 꺼짐)가 갭 주장을 반증할 수 있다. 결과는 마크다운이고 분류는 키워드 매칭(`business-logic-validation.stage.ts:790-849`)이다. 결과는 PR 수준 제안으로 게시된다: 라벨 `BUSINESS_LOGIC` 부여는 `business-logic-validation.stage.ts:290,337,358`, 게시 단계가 결과를 합치는 줄은 `create-pr-level-comments.stage.ts:83`.
- **PR 범위 vs 티켓 범위**: 티켓 하나 전체 요구사항을 이번 PR 범위와 구분하는 구현은 없다. 모든 기준을 PR diff와 대조한다.

### 9.3 확장 지점 제안 (의견)

사용자의 서비스 목표(Jira 요구사항을 diff·기존 코드와 함께 검토)를 위해 코드에서 확인한 삽입 위치다. 이 절은 **분석자 의견**이다.

| 목적 | 위치 | 비고 |
|---|---|---|
| 요구사항 수집 Context Provider | `fetchTaskContext` capability(`libs/agents/skills/capabilities/task-context-read.ts:113-285`)가 이미 `acceptanceCriteria[]`를 산출(`types.ts:1-8`) | 직접 Jira REST 어댑터를 새로 두거나 이 capability 뒤에 제공자를 교체 |
| 메인 리뷰에 주입 | `ReviewRuleConfig`/`PrReviewContext`(`libs/code-review/infrastructure/agents/review-agent.contract.ts:111-133,175-196`)에 요구사항 필드 추가 → `LoadExternalContextStage.executeStage`(`load-external-context.stage.ts:236-349`)에서 로드(알파 게이트 패턴 `:66-101,120-174` 참조. 게이트는 오류 시 기능을 끄는 fail-closed이고 리뷰는 계속 진행한다) → `buildOrchestratorInput`(`build-orchestrator-input.ts:87-159`)에서 연결 → `prompt-builder.ts`의 `formatTraceDecisions`/`formatPreviousDecisions` 옆(`:271-309,382-420`, 호출 `:630-636,690-697`)에서 렌더 | 현재 `traceDecisions`/`previousDecisions`가 같은 패턴 |
| 조건별 근거 탐색 | BusinessLogic 단계가 샌드박스보다 앞이므로 **샌드박스 생성 뒤로 옮기거나** 요구사항을 `AgentReviewStage`로 넘겨야 한다(`context.sandboxHandle?.remoteCommands`, `build-orchestrator-input.ts:93,100`). 분석기 단계(`blueprint.ts:384-393`의 `type: 'llm'`, `maxSteps: 1`은 `libs/agents/infrastructure/services/agents/business-rules-validation/businessRulesValidationAgent.ts:658-660`)를 `agent-tools.factory.ts`의 `grep/readFile`을 쓰는 기준별 루프로 교체하고 기준별 판정 스키마(`ValidationResult`, `types.ts:66-75`)를 확장. 스킬 계약(`SKILL.md:24-30`의 `analyzer-max-iterations: 1`, `allowed-tools`)도 바뀐다 | PR 범위 구분은 `파일 diff` 기준 "이번 PR이 다루는 기준" 분류 단계를 별도로 추가해야 함 |
| 티켓 식별 | `TICKET_KEY_PATTERN`/`buildSignalSources`(`business-logic-validation.stage.ts:52,499-504`) | 프로젝트 키 허용 목록으로 오탐 줄이기 |

### 9.4 Q9 지원 수준

**부분 지원.** MCP 경유 티켓 문맥 수집과 기준별 판정(diff 한정)이 별도 단계로 있고 직접 Jira 연동은 없다. 메인 리뷰 에이전트 입력과 저장소 근거 탐색에는 연결돼 있지 않다.

## 링크 저장소·교차 저장소 문맥 (참고)

`libs/ee/linked-repositories/**`[ee, 자체 `LICENSE`]는 최대 3개 저장소에 `grep/readFile`(`repo` 인자)을 확장한다. Teams/Enterprise 플랜과 경계 게이트로 제한(`agent-review.stage.ts:2945-2970,2977-3068`)되고, `<CrossRepoBoundary>`로 시스템 프롬프트에 표시된다(`prompt-builder.ts:51-79`). 규칙이나 요구사항에는 쓰이지 않는다. 코드 확인.

## 조직·팀 범위 전달 요약

| 쿼리·저장소 | 범위 |
|---|---|
| 규칙 읽기(`findByOrganizationId`) | 조직만. 팀 필터 없음 (`codeBaseConfig.service.ts:120-122`). 규칙에는 팀 키 자체가 없음([8.1 범위 키 표](#q8-scope)) |
| 규칙 id 조회 | `findById(uuid, organizationId)` (`libs/ee/kodyRules/repository/kodyRules.repository.ts:46-64`). 쓰기는 조직 문서 `_id`로 하며 유스케이스가 JWT 조직으로 범위를 정함(상세 [04](04-saas-and-isolation.md)) |
| 설정(`parameters`, 코드 리뷰 설정·언어) | 팀 uuid + `active`. **규칙이 아니라 설정**이 팀 범위([8.1 범위 키 표](#q8-scope)) |
| `codeReviewFeedback` | `organizationId` 필드+`(organizationId, suggestionId)` 인덱스(유일 제약 아님) |
| `suggestion_embedded` | `organization_id` FK. 단 `findOne(suggestionId)`·`update`에는 조직 필터 없음(`libs/kodyFineTuning/infrastructure/adapters/repositories/suggestionEmbedded.repository.ts:120-137,157-176`) |
| 같은 PR 이력 | org + `repository.fullName` + PR 번호 |
| MCP 연결·OAuth | `organizationId` |
| `ruleLikes` | 조직 필드 없음(전역) |

(위 표의 일부는 조사 에이전트가 연 줄이며, 팀 단위 키가 필요한 리소스는 팀 범위가 아니라 조직 범위라는 점이 요점이다.)

## 경로 사전 (짧은 이름 → 풀 경로)

- `prompt-builder.ts`: `libs/code-review/infrastructure/agents/prompts/`; `kody-rules-agent.provider.ts`: `libs/code-review/infrastructure/agents/providers/`; `kody-rules-sharded.judge.ts`: `libs/code-review/infrastructure/agents/collaborators/`
- `*.stage.ts`: `libs/code-review/pipeline/stages/`; `agent-review.stage.ts`, `build-orchestrator-input.ts`도 같은 폴더
- `commentManager.service.ts`, `commentAnalysis.service.ts`: `libs/code-review/infrastructure/adapters/services/`
- `automationCodeReview.ts`: `libs/automation/infrastructure/adapters/services/processAutomation/strategies/`
- `github.service.ts`: `libs/platform/infrastructure/adapters/services/github/`
- `types.ts:1-8`: `libs/agents/skills/capabilities/types.ts`; `types.ts:66-75`와 `SKILL.md`(`:24-30`, `:72`, `:77`): `libs/agents/skills/business-rules-validation/{types.ts,SKILL.md}`
- `kodyRules.service.ts`, `kody-rules-validation.service.ts`, `codeBaseConfig.service.ts`: `libs/ee/kodyRules/service/`, `libs/ee/codeBase/` [ee]
- `outbox-relay.service.ts`: `libs/core/workflow/infrastructure/`
