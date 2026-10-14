# 의존성 비교 매트릭스

- 작성일: 2026-10-13
- 정정 반영: 2026-10-13 보고서 정정 반영
- 대상 SHA (`../repos.lock.tsv`와 일치)
  - pr-agent: `330f0813b5fe0d1f54b794077c2d02aa85a1fb63` (2026-10-11)
  - open-code-review: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (2026-06-21)
  - kodus-ai: `45676c5fe7ac016b6206ccea006e459677d92842` (2026-10-12)
- 관련 공통 항목: Q11 (+ Q10 운영 요구, 라이선스)
- 근거 방식: 3개 레포 보고서의 `05-dependencies.md`·`04`·`06`을 근거로 하고, 근거는 복제하지 않고 링크한다. **점수·순위는 매기지 않는다.**
- 실행 여부: 3개 보고서 모두 **정적 추적만**(설치·빌드·실행 없음). 이 문서도 같다.
- 표기: 지원 수준 = 지원 / 부분 지원 / 미지원 / 미확인. "교체 비용" 열은 **분석자 의견(추론)**이며 숫자(시간·비용)는 만들지 않았다. 이 문서를 쓰며 `repos/<repo>`를 읽기 전용으로 다시 확인한 항목에는 **(재확인)** 을 붙였다.
- 링크 약어: [PA-05](../reports/pr-agent/05-dependencies.md) · [OC-05](../reports/open-code-review/05-dependencies.md) · [KD-05](../reports/kodus-ai/05-dependencies.md)

> 법률 자문이 아니다. 라이선스 절은 파일에 적힌 사실과 일반적 이해만 적었고, 사용 전 법무 확인이 필요하다.

---

## 1. 핵심 기능별 실제 의존

각 칸의 "필수/선택"은 선언이 아니라 **import → 호출 위치 → 리뷰 단계**까지 보고서가 확인한 기준이다(GUIDE 3.3절: 패키지 선언은 기능의 증거가 아니다).

| 기능 | 레포 | 실제 의존 (필수/선택) | 교체 비용 (의견) | 외부 서비스·바이너리 | 근거 |
|---|---|---|---|---|---|
| **LLM 호출** | pr-agent | `litellm==1.104.0` 필수(base). 모든 호출 통로. 핸들러가 LiteLLM 내부 모듈을 직접 import해 버전 결합이 강함. OpenAI·LangChain 핸들러는 설정이 아니라 코드 주입 전용 | 핸들러 주입 지점(`PRAgent(ai_handler=...)`)이 있어 교체는 가능. 단 기본 핸들러가 3666줄이라 그대로 재사용하기보다 필요한 부분만 쓰는 편이 현실적 | LLM API (필수) | [PA-05 §2](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | `anthropic-sdk-go v1.47.0`, `openai-go/v3 v3.39.0` 직접. 둘 다 "요청·응답 변환 + 재시도"만 담당하고 루프는 자체 구현. 프로토콜 2종, 프리셋 12종 | 어댑터가 얇아(`internal/llm/client.go`) 교체 쉬움. 단 `internal/` 패키지라 다른 모듈에서 import 불가 | LLM API (필수) | [OC-05 직접 의존 표](../reports/open-code-review/05-dependencies.md) |
| | kodus-ai | Vercel AI SDK `ai@7.0.83` + `@ai-sdk/*` 7종 필수(제공자별). 모든 호출이 `LLM.run` 한 곳을 지남. LangChain·LiteLLM은 쓰이지 않음 | AI SDK에 깊이 묶임(`from 'ai'` import 약 42개 파일, spec 포함 시 59, [KD-05 §2](../reports/kodus-ai/05-dependencies.md)). 조직 BYOK 슬롯 해석이 ee 경로의 `permissionValidation.service.ts`를 거쳐 가져오면 같이 따라옴 | LLM API (필수, 조직 BYOK 또는 환경변수) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md), [KD-06 §3](../reports/kodus-ai/06-fit.md) |
| **도구 호출 루프(Agent Loop)** | pr-agent | **없음.** `[system, user]` 두 메시지, `tools` 없음. `pr_agent/**/*.py`에서 `tool_calls\|tool_choice\|mcp` 검색 0건 | 새로 만들어야 함 | - | [PA-00 결론 2](../reports/pr-agent/00-overview.md) |
| | open-code-review | 루프·종료 조건·도구 실행 **전부 자체 구현**(`internal/agent/agent.go`). 외부 에이전트 프레임워크 없음 | 코드가 작아(`cmd`+`internal` 비테스트 약 1.2만 줄) 읽고 포크하기 쉬움. 서비스에 맞추려면 종료·예산 정책 수정 필요 | - | [OC-05 경계 표](../reports/open-code-review/05-dependencies.md), [OC-06 §12.2](../reports/open-code-review/06-fit.md) |
| | kodus-ai | 정책(예산·압축·완료 게이트·강제 종료)은 자체 구현(`libs/agent-harness`), **반복 엔진 자체는 AI SDK `generateText`**. 도구 결과를 대화에 붙이는 일도 SDK(SDK 내부는 레포에 없어 추론) | 정책 모듈은 재구현 가능. 엔진은 AI SDK 의존. 코드로 가져오면 `libs/llm`과 순환 의존이라 함께 가져가야 함([§6.1](#61-kodus-ai-ee-의존이-리뷰-경로에-걸려-있음)) | - | [KD-05 §2 하단](../reports/kodus-ai/05-dependencies.md), [KD-06 §3.1](../reports/kodus-ai/06-fit.md#reuse-coupling) |
| **diff 파싱·전처리** | pr-agent | 전부 자체(`git_patch_processing.py`, `pr_processing.py`), `difflib`(표준). `unidiff==0.7.5`는 **plain-diff 입력에만** 사용 | 이 레포에서 재사용 가치가 가장 큰 영역. 전역 Dynaconf 설정 결합을 감싸야 함 | - | [PA-05 경계 표](../reports/pr-agent/05-dependencies.md), [PA-06 §3](../reports/pr-agent/06-fit.md) |
| | open-code-review | 자체 정규식 파서. 외부 diff 라이브러리 없음. `git diff -U3`, 주변 줄 확장 없음 | 파서 자체는 작음. 문맥 확장·대형 diff 분할이 없어 부족분은 직접 | `git` (필수) | [OC-05 경계 표](../reports/open-code-review/05-dependencies.md) |
| | kodus-ai | Provider가 준 patch를 그대로 사용 + 자체 `patch.ts`. `diff@9`는 committable 검증(`parsePatch`)·Azure(`createTwoFilesPatch`)에만. 주변 줄 확장은 활성 경로에 없음 | 줄 번호·위치 보정 알고리즘만 선택 재구현 | - | [KD-01 Q2 §2.3](../reports/kodus-ai/01-execution-and-diff.md) |
| **Git Provider 연동** | pr-agent | `PyGithub 2.10.0`(extra `github`), `python-gitlab 8.3.0`(extra `gitlab`) 등 provider별 **선택 extra**. 어댑터는 자체 | 설정 결합만 풀면 재사용 이득이 큼 | Git 호스팅 REST API (필수) | [PA-05 §1·§2](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | **엔진에 없음.** 로컬 git 저장소만 입력. 게시는 예제 YAML(GitHub `createReview`, GitLab `discussions`) | 전부 직접 | - | [OC-07 Q13-1](../reports/open-code-review/07-credentials.md) |
| | kodus-ai | `@octokit/rest 22.0.1`, `@octokit/auth-app 8.2.0`, `@gitbeaker/rest 43.8.0`, `bitbucket`, `@llamaduck/forgejo-ts` 각 필수(해당 Provider). Azure는 `axios` 직접 호출 | AGPL 경로. 패턴 참고 | Git 호스팅 REST API (필수) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| **코드 확보(clone·git 실행)** | pr-agent | **리뷰 경로에서 clone 안 함.** provider API로 변경 파일의 base/head 본문(50개 초과 시 본문 생략). `git` 실행 파일은 clone 계열(`/help_docs`는 비활성)에서만 호출. `GitPython`은 local·Gerrit 경로 전용 | 저장소 전체 접근은 직접 만들어야 함 | `git`은 리뷰 경로에 불필요 | [PA-05 §1·§3](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | `git` 하위 프로세스 필수(`diff, show, merge-base, ls-files, ls-tree, grep, log, rev-parse`). **clone·fetch 코드 없음**, 미리 준비된 로컬 체크아웃 전제 | 서비스가 clone·SHA 고정을 맡고 엔진에 경로를 넘김 | `git` (필수), 로컬 작업 트리 | [OC-07 Q13-1](../reports/open-code-review/07-credentials.md) |
| | kodus-ai | 샌드박스에서 `git init` + `git fetch --depth=1 <PR refspec>`. 백엔드에 git 클라이언트 라이브러리 없음. 파일·패치는 Provider API | 샌드박스 계층 재구현(격리 강화) | `git` (필수, 이미지에 설치) | [KD-01 Q2 §2.1](../reports/kodus-ai/01-execution-and-diff.md), [KD-05 §2 하단](../reports/kodus-ai/05-dependencies.md) |
| **코드 검색·탐색 도구** | pr-agent | **없음.** 모델이 요청하는 검색·파일 읽기 도구 없음 | 새로 만들어야 함 | - | [PA-00 결론 1·2](../reports/pr-agent/00-overview.md) |
| | open-code-review | 자체 도구 6종(`task_done, code_comment, file_read, file_find, file_read_diff, code_search`). `git grep`·`git show <ref>:<path>`·`git ls-tree` 기반. 심볼 의미는 모름. 도구 이름이 코드에 고정이라 MCP 같은 외부 도구 추가 불가 | 도구 형태는 그대로 참고할 만함. 심볼 단위 도구는 직접 추가 | `git` (PCRE 필요, 추론) | [OC-02 §3.3](../reports/open-code-review/02-context-loop-verify.md), (재확인) `internal/tool/definitions.go` |
| | kodus-ai | `grep`(ripgrep), `readFile`, `listDir`, `findFile`, `checkTypes`, `getCallers`(주입된 call graph 문자열 파서) 등. **샌드박스 체크아웃이 있을 때만 등록**. call graph는 외부 npm CLI `@kodus/kodus-graph@0.3.0`(bun 전역) 조건부 | AST·call graph 생성기가 외부 CLI라 이를 쓰려면 CLI 도입 또는 대체 필요(파서 소스는 레포에 없음, 미확인) | `rg`(apt), `fd`/`find`, `kodus-graph` CLI(조건부), 로컬 샌드박스에서는 `checkTypes` 실행이 막힘 | [KD-02 §3.2](../reports/kodus-ai/02-context-loop-verify.md), [KD-05 §3](../reports/kodus-ai/05-dependencies.md) |
| **샌드박스·격리 실행** | pr-agent | 없음 | - | Docker·샌드박스 요구 없음 | [PA-05 §3](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | 없음. 프로세스가 호출자 환경·홈 디렉터리를 그대로 사용 | 서비스화 시 격리는 직접 | Docker 요구 없음, Dockerfile 없음 | [OC-05 외부 요구](../reports/open-code-review/05-dependencies.md), [OC-04 §C](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | `libs/sandbox`: null / local / E2B 선택. `e2b ^2.46.1`은 **선택**(키 없으면 local). **local은 컨테이너 격리 없이 워커 호스트에서 clone·실행**(코드 주석이 위험 명시) | 격리형 샌드박스(컨테이너·마이크로VM)는 직접 설계 | E2B API (선택). Docker는 리뷰에 쓰이지 않음 | [KD-05 §3](../reports/kodus-ai/05-dependencies.md), [KD-06 §2.2](../reports/kodus-ai/06-fit.md) |
| **큐·비동기 실행** | pr-agent | **없음.** FastAPI `BackgroundTasks`가 같은 프로세스에서 실행. 중복 제거·슬롯은 프로세스 로컬 | 큐·재시도·취소 전부 직접 | - | [PA-04 Q10-2](../reports/pr-agent/04-saas-and-isolation.md) |
| | open-code-review | 없음(1회 실행 CLI) | 전부 직접 | - | [OC-04 §10.1](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | RabbitMQ(`@golevelup/nestjs-rabbitmq 9.0.2`, `amqplib 2.0.1`) + Postgres 트랜잭셔널 outbox/inbox. 지연 재시도에 **delayed-message 플러그인** 필요(미설치 시 연결 설정 실패, 추론). Redis·BullMQ 없음. **dev·bench compose에만 `rabbitmq` 서비스가 있고 prod compose에는 서비스가 없어 외부 제공을 가정하는 모양(추론)**, `API_RABBITMQ_ENABLED=false`이면 부팅은 되나 publish 예외로 리뷰가 실행되지 않음(추론), 외부 `kodus-installer`는 미확인([KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)) | 패턴은 재구현이 쉬운 구조라고 보고서가 판단. 코드 복사는 AGPL 검토 필요 | RabbitMQ + delayed-message 플러그인 (앱 요구, 제공 방식은 구성별로 다름) | [KD-04 §2](../reports/kodus-ai/04-saas-and-isolation.md), [KD-05 §3](../reports/kodus-ai/05-dependencies.md), [KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose) |
| **DB·영속 저장** | pr-agent | **요구 없음.** 같은 PR 상태는 리뷰 댓글의 숨은 HTML 마커. `similar-issue` 그룹(lancedb 로컬 파일 / pinecone / qdrant, pandas)은 `/similar_issue` 전용·선택·Docker 미포함 | 우리가 DB를 새로 도입 | DB 없음 | [PA-05 §3](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | 없음. 홈 `~/.opencodereview/`에 `config.json`(평문 키)·세션 JSONL(끌 수 없음, 소스 평문 기록) | 서비스화 시 세션 로그·설정 경로 분리 필수 | 홈 디렉터리 쓰기 | [OC-04 §C·F](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | PostgreSQL(`typeorm 0.3.31`, `pg 8.23`, `vector` 확장은 마이그레이션이 생성) **필수** + MongoDB(`mongoose 9.9.4`) **필수**(PR 상태·규칙·샌드박스 리스). Redis 없음 | 두 저장소를 모두 운영해야 함. 하나로 합치는 설계를 고려할 수 있다고 보고서가 의견 제시 | PostgreSQL(pgvector 이미지) + MongoDB (필수) | [KD-05 §2·§3](../reports/kodus-ai/05-dependencies.md), [KD-06 §2.3](../reports/kodus-ai/06-fit.md) |
| **캐시·분산 락** | pr-agent | 프로세스 메모리(repo context, 조직 전역 설정, 봇 ID, delivery ID) | 다중 워커에서는 외부 저장소·분산 락으로 교체 | - | [PA-04 Q10-3](../reports/pr-agent/04-saas-and-isolation.md) |
| | open-code-review | 없음 | - | - | - |
| | kodus-ai | `cache-manager`(`store:'memory'`, Redis 아님) + Postgres advisory lock(고정 QueryRunner로 연결 1개 점유, TTL 갱신 없음) | 락 TTL 60초·갱신 없음이 105분 리뷰와 어긋나는 점은 가져오지 말 것 | - | [KD-04 §2.1·§3](../reports/kodus-ai/04-saas-and-isolation.md) |
| **토큰 계산** | pr-agent | `tiktoken==0.14.0`(기본 로컬 예산 계산). **`force_accurate=True` 경로 한정**으로 LiteLLM provider-native 카운트를 추가 시도: (재확인) `algo/token_handler.py`의 `_acount_tokens`가 `litellm.acount_tokens`를 호출하고, 로컬 추정만 나오면 0을 돌려 보정 계수 추정으로 돌아감. **호출자는 비활성 `/help_docs`뿐**(`tools/pr_help_docs.py:632`, `/help_docs`는 `agent/pr_agent.py:69-71`에서 명령 매핑 제외 — 재확인)이라 이 SHA의 기본 명령 경로에서는 호출되지 않는 것으로 보임(다른 진입점의 간접 호출은 추론). provider API를 실제로 부르는지는 LiteLLM 내부라 **미확인** | 압축·청크 로직이 토큰 계산에 묶여 있어 같이 가져와야 함 | (provider 카운트 경로는 `force_accurate=True` 한정, 외부 호출 여부 미확인) | [PA-05 토큰 계산 경로](../reports/pr-agent/05-dependencies.md), [PA-05 §2 `tiktoken`](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | `tiktoken-go v0.1.8`, **항상 `cl100k_base`**(모델명 미전달), BPE 1.7MB 임베드, 실패 시 `bytes/4`. Claude·Qwen에는 근사 오차(추론) | 토큰 가드(80% 사전 검사, 60/80% 압축) 전체가 이것에 의존 | 네트워크 불필요 | [OC-05 직접 의존 표](../reports/open-code-review/05-dependencies.md) |
| | kodus-ai | `tiktoken ^1.0.22`는 BYOK 제한기·청킹. **사전 예산 추정 자체는 4글자≈1토큰 비율** | 정확도 필요 시 직접 | - | [KD-01 §2.3 토큰 초과](../reports/kodus-ai/01-execution-and-diff.md) |
| **MCP** | pr-agent | **없음(미지원).** `a2a-sdk`(extra `mosaico`)는 A2A 서버이며 MCP가 아님 | - | MCP 서버 요구 없음 | [PA-05 §3](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | **없음(미지원).** `go.mod`·소스·문서에 MCP 없음, 도구 이름 고정 | - | - | [OC-05 부재 표](../reports/open-code-review/05-dependencies.md) |
| | kodus-ai | `@modelcontextprotocol/sdk ^1.29.0` **선택**. Jira·Linear는 `apps/mcp-manager`를 거치는 MCP로만 연결. **finder 도구에는 MCP가 노출되지 않음**. `mcp-manager`의 JWT 검증은 `decode`만(서명 미검증, [KD-07 §5.4](../reports/kodus-ai/07-credentials.md)) | Jira를 직접 REST로 붙이면 MCP 의존을 피할 수 있음(의견) | `mcp-manager` 서비스(선택, prod compose에 없음) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md), [KD-03 Q9](../reports/kodus-ai/03-incremental-memory-rules.md) |
| **Jira·요구사항** | pr-agent | `atlassian-python-api==3.41.4`(**extra `bitbucket`**)로 Jira Cloud REST 조회. **선언만으로는 켜지지 않고** `[jira]` 호스트 설정 + 이 extra 설치가 필요. Asana도 선택 | 키 추출·인증 경계 코드는 부분 재사용 가능 | Jira Cloud REST (선택) | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md), [PA-03 Q9](../reports/pr-agent/03-incremental-memory-rules.md) |
| | open-code-review | 없음. `--background` 문자열 슬롯 하나 | 전부 직접 | - | [OC-03 Q9](../reports/open-code-review/03-incremental-memory-rules.md) |
| | kodus-ai | 직접 Jira 어댑터 없음. MCP(Atlassian Rovo 등) 경유 별도 "Business Logic" 단계 | 입력 삽입 패턴만 참고 | MCP 서버(선택) | [KD-03 Q9](../reports/kodus-ai/03-incremental-memory-rules.md) |
| **임베딩** | pr-agent | OpenAI 임베딩은 `/similar_issue` 한정(`openai` 클라이언트) | 팀 메모리와 무관 | OpenAI 임베딩 + 벡터 DB (선택) | [PA-05 §3](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | 없음 | - | - | - |
| | kodus-ai | 리뷰 dedup의 임베딩 가드에 OpenAI 임베딩(`API_OPEN_AI_API_KEY`, 선택). npm `pgvector`·벡터 쿼리(`<=>`)는 쓰이지 않음 | - | OpenAI 임베딩 (선택) | [KD-05 §3](../reports/kodus-ai/05-dependencies.md), [KD-02 §5.1 dedup](../reports/kodus-ai/02-context-loop-verify.md) |
| **관측** | pr-agent | `opentelemetry-*`·`prometheus-client`·`langfuse`가 base에 선언되나 **설정으로 켜질 때만** 호출. 꺼도 동작 | 제거 영향 작음 | OTLP·Prometheus·Langfuse (선택) | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | OpenTelemetry v1.43.0 계열 9개. **기본 꺼짐**(`OCR_ENABLE_TELEMETRY=1` 또는 설정 파일). 엔진 로직과 분리 | 제거하면 `internal/telemetry` 삭제 | OTLP gRPC (선택) | [OC-05 직접 의존 표](../reports/open-code-review/05-dependencies.md) |
| | kodus-ai | `@langfuse/* 5.11`(`LANGFUSE_TRACING`), Sentry, Pyroscope, PostHog 등 환경변수 게이트. **자체 호스팅도 `telemetry.kodus.io`로 일일 익명 하트비트 전송**(`KODUS_TELEMETRY_DISABLED`로 끔) | 끄는 설정만 확인하면 됨 | 외부 관측 SaaS (선택), `telemetry.kodus.io`(기본 켜짐) | [KD-05 §3](../reports/kodus-ai/05-dependencies.md) |
| **설정·시크릿 관리** | pr-agent | `dynaconf`(전역 계층 설정, 프롬프트도 TOML) + `starlette-context`. 시크릿 제공자 AWS Secrets Manager / GCS(선택). 요청마다 설정을 deepcopy | **라이브러리로 쓸 때 가장 큰 결합점.** 요청마다 컨텍스트로 감싸야 함 | AWS SM·GCS (선택) | [PA-05 §2 `dynaconf`](../reports/pr-agent/05-dependencies.md), [PA-04 Q10-5](../reports/pr-agent/04-saas-and-isolation.md) |
| | open-code-review | `~/.opencodereview/config.json`(평문, 0600), `OCR_LLM_*` 환경변수, 셸 rc 파일(`~/.zshrc` 등)을 정규식으로 파싱. 설정 파일에 유효 엔드포인트가 있으면 환경변수 무시 | 서비스화 시 `llm.ResolvedEndpoint`를 직접 채워 이 탐색 경로를 제거 | - | [OC-04 §D·F](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | 자격증명은 Postgres `auth_integrations`에 저장, AES-256-CBC(MAC 없음, 전역 키 `API_CRYPTO_KEY`, 회전 없음). 일부(GitLab OAuth 토큰, GitHub 설치 토큰 스냅샷)는 평문. KMS·시크릿 매니저 미사용 | 가져오지 말고 봉투 암호화 등으로 재설계(보고서 의견) | - | [KD-07 §2](../reports/kodus-ai/07-credentials.md) |
| **웹 프레임워크·서버** | pr-agent | `fastapi`, `starlette`, `uvicorn`, `gunicorn`(base). 엔진(`PRAgent.handle_request`)과 분리 가능 | 자체 서버를 쓰면 `pr_agent/servers/`는 불필요 | - | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | 서버 없음(`net/http`는 로컬 세션 뷰어뿐) | - | - | [OC-04 §10.1](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | NestJS 11 모노레포. **백엔드 의존성 전부가 루트 `package.json`에 있음**(앱별 `package.json`은 비어 있음). `apps/web`·`apps/cli`·`apps/try`는 별도 의존 그래프 | 프레임워크째 가져오는 선택지는 EE 결합 때문에 비현실적(아래 §6) | - | [KD-05 §1](../reports/kodus-ai/05-dependencies.md) |
| **스키마·응답 파싱** | pr-agent | `PyYAML`(모델 응답이 YAML), `pydantic 2.13.3`(**경고 수준** 검증), `Jinja2`(프롬프트 렌더) | 프롬프트·출력이 YAML·Jinja에 묶임 | - | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| | open-code-review | 표준 라이브러리 위주(JSON 도구 스키마는 `tools.json`) | - | - | [OC-02 §3.3](../reports/open-code-review/02-context-loop-verify.md) |
| | kodus-ai | `zod 4.4.3`, `ajv 8.20`, 구조화 출력 복구 모듈 | - | - | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| **사용자 인증·인가** | pr-agent | 해당 없음(웹훅 서명 + 운영자 단일 자격). `IdentityProvider` 확장 지점만(기본 항상 ELIGIBLE) | 직접 | - | [PA-04 Q10-1](../reports/pr-agent/04-saas-and-isolation.md) |
| | open-code-review | 해당 없음 | 직접 | - | [OC-04 §10.1](../reports/open-code-review/04-saas-and-isolation.md) |
| | kodus-ai | `@casl/ability`, `passport`, `passport-jwt`, `@nestjs/jwt` 필수. `TenantScopeGuard`는 7개 컨트롤러에만 적용 | 격리가 앱 수준이라 그대로 신뢰하지 말 것 | - | [KD-04 §3](../reports/kodus-ai/04-saas-and-isolation.md) |

---

## 2. 선언만 있고 쓰이지 않는 패키지·설정

"쓰이지 않음"의 판정 근거를 구분했다. **직접 import 없음**은 해당 패키지를 우리가 직접 호출하는 코드가 없다는 뜻이지, 간접 의존(다른 패키지가 내부에서 사용)까지 부정하는 것이 아니다.

### 2.1 직접 import가 확인되지 않은 선언

| 레포 | 패키지·설정 | 선언 | 확인 내용 | 판정 수준 | 근거 |
|---|---|---|---|---|---|
| pr-agent | `anthropic` | `>=0.69.0`, base | `pr_agent/**/*.py`에 `import anthropic` 직접 호출 없음. Claude 호출은 LiteLLM 경유. LiteLLM 내부가 이 SDK를 쓰는지는 **미확인** (재확인: `import anthropic\|from anthropic` 검색 0건) | 코드 확인(부재는 grep 근거) | [PA-05 §2](../reports/pr-agent/05-dependencies.md) |
| kodus-ai | `pgvector`(npm) | `^0.3.0` | `apps`·`libs`의 `.ts`에서 import 없음. 단 Postgres `vector` **확장**은 마이그레이션이 생성하므로 별개. (재확인: `apps/cli` 테스트에 문자열 `pgvector`가 정규식 안에 있을 뿐 import 아님) | 코드 확인(정규식 grep, 동적 require 누락 가능) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `openai`(공식 SDK) | `^7.8.0` | `from 'openai'` 없음 (재확인: `apps`·`libs`에서 0건). 실제 OpenAI 연동은 `@ai-sdk/openai`. morphsdk가 끌어오는 `openai@4.104.0`이 락에 공존 | 코드 확인(부재) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `azure-devops-node-api` | `^15.1.2` | Azure Repos는 `axios`를 직접 호출 | 코드 확인(부재) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `@octokit/auth-oauth-app`, `octokit`(umbrella) | `^9.0.3`, `^5.0.5` | import 없음 | 코드 확인(부재) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `date-fns`, `passport-saml-metadata`, `keyv` | - | 백엔드 import 없음. `keyv`는 `@nestjs/cache-manager`의 peer로 락에 보임 | 코드 확인(부재), 제거 전 peer 확인 필요 | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `GITHUB_TOKEN` 환경변수 | `.env.example:488-489` | 서버 코드에서 읽는 곳 없음(주석 1곳뿐) | 코드 확인(부정 grep) | [KD-07 §1.1](../reports/kodus-ai/07-credentials.md) |
| open-code-review | (직접 의존 없음) | - | 직접 의존 전부가 import로 확인됨 | - | [OC-next 완료 기준](../reports/open-code-review/next.md) |
| open-code-review | 템플릿 `MAIN_TASK/PLAN_TASK/MEMORY_COMPRESSION_TASK.timeout` | 파싱만 | 읽는 곳이 없음(읽는 것은 `REVIEW_FILTER_TASK`, `RE_LOCATION_TASK`뿐). **패키지가 아니라 설정** | 코드 확인 | [OC-02 §4](../reports/open-code-review/02-context-loop-verify.md), [OC-05 차이 표](../reports/open-code-review/05-dependencies.md) |

### 2.2 선언·import는 있으나 리뷰 경로에서는 쓰이지 않거나 조건부

| 레포 | 패키지 | 실제 쓰임 | 근거 |
|---|---|---|---|
| pr-agent | `GitPython` | base 선언이지만 `local_git_provider.py`·`gerrit_provider.py`에서만 import. GitHub/GitLab 경로 미사용. 일반 `clone()`은 GitPython이 아니라 `git` 바이너리 subprocess | [PA-05 §1](../reports/pr-agent/05-dependencies.md) |
| pr-agent | `unidiff` | base 선언. plain-diff 입력 파싱·base 복원에만 | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| pr-agent | `ujson` | GCS 시크릿 제공자 한 곳 | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| pr-agent | `langfuse` | import가 아니라 LiteLLM 콜백 이름 검사로 켜질 때만 | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| pr-agent | `langchain` extra | `LangChainOpenAIHandler` 전용, 설정으로 선택되지 않고 코드 주입으로만, `all`에도 없음 | [PA-05 §1](../reports/pr-agent/05-dependencies.md) |
| pr-agent | `pandas`, `pinecone`, `lancedb`, `qdrant-client` | dependency group `similar-issue`. `/similar_issue` 한정, Docker 미포함 | [PA-05 §2 표](../reports/pr-agent/05-dependencies.md) |
| kodus-ai | `ml-kmeans` | `kodyFineTuning.service.ts`가 import하지만 **활성 파이프라인에서 호출되지 않음**(피드백 학습은 이 SHA에서 비활성) | [KD-05 §2](../reports/kodus-ai/05-dependencies.md), [KD-03 §7.3](../reports/kodus-ai/03-incremental-memory-rules.md) |
| kodus-ai | `@anthropic-ai/sdk` | **devDependencies**. 벤치 스크립트(`scripts/benchmark/classify-fp.ts`)만 | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `@langchain/*` | 전이 의존(morphsdk 경유)만, import 없음 | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| kodus-ai | `@morphllm/morphsdk`, `exa-js`, `e2b`, `@langfuse/*`, `@node-saml/passport-saml`(ee) | 환경변수·플랜 게이트 뒤 선택 기능 | [KD-05 §2](../reports/kodus-ai/05-dependencies.md) |
| open-code-review | `charm.land/bubbletea·bubbles·lipgloss` | `ocr config provider/model` TUI 3개 파일에서만. 엔진 패키지는 import하지 않음 | [OC-05 직접 의존 표](../reports/open-code-review/05-dependencies.md) |
| open-code-review | OpenTelemetry·OTLP | 기본 꺼짐, 켜졌을 때만 | [OC-05 직접 의존 표](../reports/open-code-review/05-dependencies.md) |
| open-code-review | `standard-webhooks`(간접 의존) | 모듈 목록에만 있고 import 없음. **웹훅 처리 기능의 증거가 아님** | [OC-05 간접 의존](../reports/open-code-review/05-dependencies.md) |

---

## 3. 이 SHA에 없음이 확인된 패키지·구성 (미지원 판정 근거)

| 후보 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| MCP SDK | 없음 (`pr_agent/**/*.py` 검색) | **없음.** `go.mod`·`go.sum`·소스·문서에 `modelcontextprotocol` 없음 | **있음** `@modelcontextprotocol/sdk ^1.29.0`(선택) |
| AWS SDK | `boto3`는 **extra `codecommit`**(CodeCommit·AWS Secrets Manager·Bedrock 인증) 선택 | **없음.** `aws-sdk-go-v2` 없음, 프로토콜은 anthropic·openai 두 가지뿐 | Bedrock은 `@ai-sdk/amazon-bedrock`(제공자별 선택) |
| Redis·BullMQ | 없음 | 없음 | **없음**(락은 Postgres, 캐시는 메모리) |
| 벡터 쿼리 코드 | `/similar_issue` 한정 | 없음 | 확장만 생성, 쿼리(`<=>`) 없음 |
| tree-sitter·LSP | 없음 | 없음(`go.mod` 직접·간접 전체) | 백엔드 없음(AST는 외부 CLI `kodus-graph`) |
| git 클라이언트 라이브러리 | `GitPython`(local·Gerrit 한정) | 없음(`git` 바이너리) | 백엔드 없음(`simple-git`은 `apps/cli`에만) |
| `cobra`·`pflag` (GUIDE 후보) | - | **없음.** 표준 `flag` + 자체 래퍼 | - |

근거: [PA-00 결론 2](../reports/pr-agent/00-overview.md), [OC-05 부재 표](../reports/open-code-review/05-dependencies.md), [KD-05 §2·§3](../reports/kodus-ai/05-dependencies.md).

---

## 4. 외부 서비스·바이너리 요구 한눈에

"필수"는 리뷰 경로가 동작하기 위한 최소 요건 기준이다.

| 요구 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| LLM API | 필수 (LiteLLM이 지원하는 provider) | 필수 (Anthropic Messages 또는 OpenAI Chat 호환) | 필수 (한 곳 또는 조직 BYOK) |
| Git 호스팅 API | 필수 | 엔진은 불필요(예제 YAML 게시 단계만) | 필수 |
| `git` 실행 파일 | 리뷰 경로엔 불필요(이미지에는 apt 설치) | **필수**(+ 로컬 체크아웃) | **필수** |
| `ripgrep` | - | - | 조건부(모델 `grep` 도구) |
| PostgreSQL | 없음 | 없음 | **필수** (+ `vector` 확장 생성) |
| MongoDB | 없음 | 없음 | **필수** |
| RabbitMQ (+ delayed-message 플러그인) | 없음 | 없음 | **필수**(앱 요구. prod compose에는 서비스가 없고 외부 제공 가정 — 추론, [KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)) |
| Redis | 없음 | 없음 | 없음 |
| 샌드박스(E2B 등) | 없음 | 없음 | 선택(없으면 로컬 = 호스트 실행) |
| Docker | 이미지 배포 선택 | Dockerfile 없음 | 앱이 리뷰에서 사용하지 않음(배포는 compose) |
| Jira | 선택 (REST, extra 필요) | 없음 | 선택 (MCP 경유) |
| Node·bun | 없음 | npm 래퍼는 선택 설치 편의 | 이미지에 bun 포함, `kodus-graph` CLI(조건부) |
| 임베딩 API | `/similar_issue` 한정 | 없음 | 선택 (dedup 가드) |
| 시크릿 매니저 | 선택 (AWS SM, GCS) | 없음 | 없음(KMS 미사용) |
| 관측 수집기 | 선택 | 선택 (OTLP) | 선택 |
| **의도치 않게 나가는 외부 통신 후보** | (`force_accurate=True` 경로의 provider 토큰 카운트: 호출자는 비활성 `/help_docs`뿐, 외부 호출 여부 미확인) | npm 래퍼의 **백그라운드 업데이트 확인**(`OCR_NO_UPDATE`로 끔), 세션 JSONL에 소스 평문 기록 | **자체 호스팅도 일일 하트비트**(`KODUS_TELEMETRY_DISABLED`), Morph 사용 시 파일 전체 본문이 외부 SaaS로 전달 |

근거: [PA-05 §3](../reports/pr-agent/05-dependencies.md), [OC-05 외부 요구](../reports/open-code-review/05-dependencies.md), [KD-05 §3](../reports/kodus-ai/05-dependencies.md), [KD-01 §2.1](../reports/kodus-ai/01-execution-and-diff.md).

---

## 5. 최소 실행 구성 (레포별·모드별)

문서·설정 근거로 도출한 구성이며 **실행해서 확인하지 않았다.** 처리량·메모리·이미지 크기 같은 숫자는 3개 보고서 모두 측정하지 않았으므로 적지 않는다.

| 모드 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| **CLI / 1회 실행** | `pip install 'pr-agent[github]'` + `github.user_token`(`deployment_type="user"`) + LLM 키. GitHub Action도 있음 | 바이너리 1개 + `git` + LLM 3요소(`OCR_LLM_URL`, `OCR_LLM_TOKEN`, `OCR_LLM_MODEL`). 설정 파일에 유효 엔드포인트가 있으면 그것이 우선 | `apps/cli`는 별도 의존 그래프(`commander`, `simple-git`)이며 서버 스택과 분리. CLI 경로 세부는 이번 분석 범위 밖(미확인) |
| **웹훅 서버** | GitHub App: base + `github` extra, `github.app_id`·`github.private_key`·`github.webhook_secret`. GitLab: base + `gitlab` extra, `gitlab.url`·토큰·`gitlab.shared_secret`. DB·큐 없이 한 프로세스(`BackgroundTasks`) | **없음** (서버·워커 없음) | `apps/webhooks`(수신 전용)는 PostgreSQL에 outbox로 적재하므로 PostgreSQL이 필요하고, 실제 리뷰는 `apps/worker`가 RabbitMQ로 소비. worker·webhooks는 `connectionInitOptions.wait: true`(fail-fast)로 설정돼 있으나 실제 부팅 실패는 라이브러리 동작이라 추론 |
| **SaaS형(멀티테넌트)** | **구성 없음.** 큐·ack/재시도·실패 저장·테넌트 격리 계층이 없고 "운영자 한 벌의 자격증명" 서버 | **해당 없음** (단일 사용자 CLI). 서비스 워커화 시 분리할 항목(TUI, 세션 로그, 홈 설정, 전역 stdout)이 정리돼 있음 | `api` + `worker`(`WORKER_ROLE=code-review`) + `webhooks` + PostgreSQL(pgvector 이미지) + MongoDB + RabbitMQ(delayed-message 플러그인; prod compose에는 서비스가 없어 별도로 제공해야 함, [KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)). UI가 필요하면 `web`. `worker-analytics`·`mcp-manager`는 선택. 런타임 이미지에 `git`·`rg`·`kodus-graph` 포함. 첫 부팅 시 `RUN_MIGRATIONS=true` |

kodus-ai 부팅에 필요한 환경변수 이름(값 아님): `API_PORT`, `WORKER_ROLE`, `API_CRYPTO_KEY`, `CODE_MANAGEMENT_SECRET`, `CODE_MANAGEMENT_WEBHOOK_TOKEN`, `API_WEBHOOKS_PORT`, `API_JWT_SECRET`(추론), Postgres·Mongo 접속 정보, `API_RABBITMQ_URI`, GitHub App 모드의 `API_GITHUB_APP_ID`·`API_GITHUB_PRIVATE_KEY` 등([KD-05 §4](../reports/kodus-ai/05-dependencies.md)).

**주의 (RabbitMQ 제공 방식)**: [KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)이 구성별로 정리했다. `rabbitmq` 서비스는 **dev·bench compose에만 정의**되고(preview는 dev 오버레이라 dev의 것을 씀), **prod·sim·test compose에는 없다**((재확인) `docker-compose.prod.yml`에 `rabbit` 검색 결과 없음). `API_RABBITMQ_ENABLED=false`이면 앱은 부팅하되 `publishMessage`가 예외를 던지고 outbox 릴레이는 연결이 없어 건너뛰므로 **리뷰가 실행되지 않는다(추론, 실행 안 함)**. prod compose가 복사하라는 `.env.example`의 기본 URI 호스트(`rabbitmq-local`)는 dev compose의 네트워크 별칭이라 prod 네트워크에 없다. 보고서는 prod compose가 브로커를 외부 제공으로 가정하는 모양이라고 **추론**하며 의도는 확인하지 못했다. 외부 설치 스택 `kodus-installer`의 내용은 **미확인**(이 레포의 `.env.schema`·문서는 설치기가 `rabbitmq`를 띄운다고 시사하나 문서 확인에 그침). 따라서 "프로덕션 compose만으로 최소 구성이 완성된다"고 읽으면 안 된다.

---

## 6. 라이선스 비교와 재사용 가능 범위

> **법률 자문이 아니다.** 아래 "재사용 가능 범위"는 파일에 적힌 규칙과 일반적 이해를 바탕으로 한 분석자 의견이며, 실제 사용 전 법무 검토가 필요하다. 서드파티·전이 의존성의 라이선스는 3개 보고서 모두 조사하지 않았다(미확인).

| 항목 | pr-agent | open-code-review | kodus-ai |
|---|---|---|---|
| 라이선스 | **MIT** | **Apache-2.0** | **듀얼**: 기본 AGPL-3.0, `.ee.` 파일명 또는 `ee/` 경로는 **상용(Enterprise)** |
| 파일 근거 | `LICENSE:1-3`("Copyright (c) 2026 The PR Agent") | `LICENSE:1-4`, 스킬 문서 머리 `license: Apache-2.0`. `NOTICE` 없음, 하위 별도 라이선스 파일 없음 | `license.md:5-10`, `license_ee.md:5-28`, `libs/ee/linked-repositories/LICENSE` |
| 일반적으로 알려진 조건(일반 이해, 확인 필요) | 저작권·허가 고지 유지 | 저작권·라이선스 고지, 변경 사실 표기, NOTICE가 있다면 유지 | AGPL: 네트워크로 제공하는 SaaS에 포함하면 소스 공개 의무가 따를 수 있음. EE: 유효한 계약 없이 프로덕션·사내 배포 불가, 평가 목적의 열람·수정·테스트만 허용 |
| 코드 재사용 가능성(의견) | **가능** (고지 유지) | **가능** (고지·변경 표기) | **비-ee 경로: 코드 복사는 AGPL 검토 선행.** ee 경로: **재사용 불가**(상용 계약 필요). 아이디어·패턴 재구현은 가능 |
| 상표·로고 | README의 Qodo 표기는 코드 라이선스와 별개, 가져올 때 제외(의견) | - | - |
| 확인된 불일치·주의 | README가 스스로 "community-maintained legacy project of Qodo"라고 함(`README.md:27`) → 장기 유지 위험(의견). 하위 디렉터리 라이선스 전수 확인은 안 함 | 모듈 경로가 `github.com/open-code-review/open-code-review`로 저장소 URL(alibaba)과 다름(`go.mod:1`). 엔진 전부가 `internal/`이라 **다른 모듈에서 import 불가**(포크 후 공개 패키지로 노출 필요) | 루트 `package.json`은 `"license": "UNLICENSED"`, `apps/cli/package.json`은 `MIT`, README 배지는 AGPLv3. AGPL 전문 파일·`NOTICE` 없음. `@license Kodus Tech. All rights reserved.` 헤더가 소스 18개 파일에 있고 그중 10개는 ee 표지 없는 경로(`libs/code-review` 5, `libs/core` 4, `libs/kodyFineTuning` 1)라 경로 규칙(AGPL)과 어긋남(해석은 법무 몫, [KD-06 §3.2](../reports/kodus-ai/06-fit.md#license-header)) |

### 6.1 kodus-ai: ee 의존이 리뷰 경로에 걸려 있음

[KD-05 §6.3](../reports/kodus-ai/05-dependencies.md#license)이 정리한 대로 파이프라인 조립(`libs/core/providers/*.provider.ee.ts` 3개), 실행 진입(`libs/ee/automation/runCodeReview.use-case.ts`), 설정 로더, 규칙 서비스가 모두 ee다. 보고서는 AGPL-only 트리가 그대로 컴파일되지 않는다고 추론한다(빌드는 시도하지 않음). 자체 호스팅에서 라이선스 키가 없어도 핵심 리뷰 파이프라인은 실행된다([KD-05 §6.4](../reports/kodus-ai/05-dependencies.md)). 그러나 이것은 "실행해도 되는가"의 사실이고, "코드를 가져와 우리 SaaS에 넣어도 되는가"는 별개의 법무 질문이다.

**재확인한 사실** (읽기 전용 grep + [KD-06 §3.1](../reports/kodus-ai/06-fit.md#reuse-coupling) 대조):
- `libs/agent-harness`, `libs/llm`, `libs/sandbox`의 **비테스트 소스는 `@libs/ee`를 import하지 않는다.** `libs/llm`의 spec 파일 2개(`strict-wire-schema.spec.ts`, `structured-output-phase-contracts.spec.ts`)만 ee를 import하므로 테스트까지 가져오면 ee 코드가 필요하다. 보고서의 "비-spec ee import 없음" 서술과 일치한다.
- 이 세 디렉터리에는 `All rights reserved` 라이선스 헤더가 **0건**이다. 헤더가 있는 파일은 **18개**이고, 그중 10개가 ee 표지(경로의 `ee/`·파일명의 `.ee.`) 없는 경로다: `libs/code-review` 5, `libs/core` 4, `libs/kodyFineTuning` 1(나머지 8개는 `libs/ee/` 5 + `.ee.ts` 3). 우리가 재사용 후보로 보는 세 모듈에는 헤더가 없고, 아래 결합 대상 파일도 18개 목록에 없다 — [KD-06 §3.2](../reports/kodus-ai/06-fit.md#license-header).
- 다만 **완전히 독립된 모듈은 아니다.** 비-ee 모듈 재사용 비용([KD-06 §3.1](../reports/kodus-ai/06-fit.md#reuse-coupling)):
  - `libs/agent-harness`는 `libs/llm`을 import하고 `libs/llm`은 `libs/agent-harness`의 타입을 import하는 **순환 의존**이라 둘을 함께 가져가야 한다.
  - `libs/llm`은 `libs/core/log`(logger·langfuse)와 `libs/common/utils`(`crypto`, `parent-signal-compose`)에 의존한다. `crypto.ts`는 **import 시점에 `API_CRYPTO_KEY`(32바이트 hex) 길이를 검사하고 틀리면 예외**를 던진다(이 파일을 로드하는 진입점에서만 해당, 어느 진입점인지는 추적하지 않아 추론).
  - `libs/sandbox`는 `libs/core`(로거·enum·분산 락·Mongo 베이스)와 `libs/common/utils/polling`, 그리고 `libs/code-review`의 **파일 2개**(타입만 남은 `collectCrossFileContexts.service.ts`, 13줄 `shell-quote.ts`)에 의존한다.
  - `libs/core/log/` 디렉터리를 통째로 복사하면 `observability.service.ts`가 `@libs/llm`을 되돌아 import한다. 실제로 필요한 것은 `logger.ts`·`langfuse.ts` 두 파일이므로 필요한 파일만 가져와야 순환이 늘지 않는다.
  - 모두 비-ee 경로라 새 ee 의존은 생기지 않지만 **AGPL 적용 범위가 세 모듈에서 이 파일들로 넓어진다.** 모델 슬롯을 만드는 호출 측 배선은 ee(`permissionValidation.service.ts`)에 있다.

### 6.2 재사용 가능 범위 요약 (의견)

| 구성요소 | 라이선스 분류 | 가능한 재사용 방식 |
|---|---|---|
| pr-agent provider·diff·게시·finding 상태 모듈 | MIT | 코드 재사용 가능 (Dynaconf·요청 컨텍스트 결합을 감싸야 함) |
| open-code-review 루프·도구·위치 해석 | Apache-2.0 | 코드 재사용 가능 (Go 서비스일 때. `internal/` 노출 필요) |
| kodus-ai `libs/agent-harness`·`libs/llm`·`libs/sandbox` | AGPL-3.0 (경로 규칙상) | 코드 복사는 법무 검토 후. 기본은 패턴 재구현. 디렉터리만 복사해서는 컴파일되지 않는다: `agent-harness`↔`llm` 순환, `libs/core/log`·`libs/common/utils`·`libs/code-review` 파일 2개 등이 따라오고 AGPL 범위가 그만큼 넓어진다(§6.1) |
| kodus-ai outbox/inbox·큐·락(`libs/core/workflow`) | AGPL-3.0 (경로 규칙상) | 패턴 재구현 (보고서도 재구현을 권함, [KD-06 §3](../reports/kodus-ai/06-fit.md)) |
| kodus-ai 파이프라인 조립·규칙 서비스·설정 로더·`libs/ee/**` | **상용(EE)** | 재사용 불가. 읽기·평가 외 사용에는 상용 계약 필요 |

---

## 7. 이 비교의 검증 약점과 보고서 간 불일치

| # | 항목 | 내용 | 영향 |
|---|---|---|---|
| 1 | **"해석 버전"의 산정 방식이 서로 다르다** | pr-agent는 `uv.lock`, kodus-ai는 `pnpm-lock.yaml` importer를 읽은 값이고, open-code-review는 `go.sum`이 단일 버전임을 대조했다(`go list -m all`·`go mod graph` 미실행). **셋 다 실제 설치·해석 결과가 아니고 방법도 같지 않다.** | 버전 칸을 레포 간 같은 신뢰도로 읽으면 안 됨 |
| 2 | kodus-ai 줄 번호의 재대조 범위 | 2026-10-13 정정에서 02~05의 `path:range` 인용 약 650개(02 약 198, 03 약 205, 04 약 155 중 약 150, 05 약 95)를 모두 열어 범위·식별자를 대조하고 약 30건을 정정했다. **미대조**: 01 전체, 02의 긴 범위, 03·04·05의 일부 긴 범위·파일명만 인용한 파일([KD-00](../reports/kodus-ai/00-overview.md), 각 문서 머리, [KD-next](../reports/kodus-ai/next.md)) | 미대조 범위의 근거를 인용할 때는 해당 줄을 다시 열 것 |
| 3 | kodus-ai "선언-미사용" 판정은 정규식 grep | 동적·문자열 require를 놓칠 수 있다고 [KD-05](../reports/kodus-ai/05-dependencies.md)가 명시. `from 'openai'`와 `pgvector`는 이번에 다시 확인해 일치 | 낮음 |
| 4 | pr-agent `anthropic`은 "쓰이지 않음"이 아니라 "직접 import 없음", 토큰 계산은 `force_accurate=True` 경로 한정 | `anthropic`: `pr_agent/`에 직접 import 없음(재확인), LiteLLM 내부 사용 여부는 미확인. 토큰 계산: [PA-05](../reports/pr-agent/05-dependencies.md)가 정정됐다 — 기본은 `tiktoken` 로컬 추정이고, `force_accurate=True`일 때만 `litellm.acount_tokens`를 추가 시도한다. (재확인) 호출자는 비활성 `/help_docs`뿐(`tools/pr_help_docs.py:632`, `agent/pr_agent.py:69-71`)이라 이 SHA의 기본 명령 경로에서는 호출되지 않는 것으로 보인다(다른 진입점의 간접 호출은 추론). provider API를 실제로 부르는지는 LiteLLM 내부라 미확인 | 비공개 코드가 외부 API로 나가는 경로 점검 시 이 경로는 비활성 명령 한정이며 외부 호출 여부는 확인 필요 |
| 5 | open-code-review 도구 개수 표기 | **정정 완료.** 기준은 [OC-00 1절](../reports/open-code-review/00-overview.md)(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개, Provider 등록 5개, `task_done`은 직접 처리). (재확인) `internal/tool/definitions.go`의 알려진 도구 6개(`task_done`, `code_comment`, `file_read`, `file_find`, `file_read_diff`, `code_search`) + `Unknown`과 일치 | 없음 |
| 6 | kodus-ai 최소 구성이 prod compose와 맞지 않는다 | RabbitMQ는 앱 요구이나 dev·bench compose에만 정의되고 prod compose에는 서비스가 없다(위 §5 주의, [KD-05 §4.1](../reports/kodus-ai/05-dependencies.md#rabbitmq-compose)). prod의 외부 제공 가정은 추론, 외부 installer는 미확인 | 최소 구성 완성도 낮음 |
| 7 | kodus-ai 비-ee 모듈 재사용 결합 | [KD-06 §3.1](../reports/kodus-ai/06-fit.md#reuse-coupling)에 결합 표가 신설돼 `libs/core/log`·`libs/common/utils`·`libs/code-review` 파일 2개·`agent-harness`↔`llm` 순환·`crypto.ts` import 시점 검사가 반영됨(§6.1). (재확인) `libs/core/log/observability.service.ts:15,20`의 `@libs/llm` import, `libs/common/utils/crypto.ts:5-9`의 `API_CRYPTO_KEY` 길이 검사, `shell-quote.ts` 13줄. 나머지 결합은 보고서의 grep 대조를 따랐고 이 문서에서 다시 열지 않았다 | 재사용 비용은 §6.1 기준으로 읽을 것 |
| 8 | 문서 머리의 "검증 수준 요약" 숫자는 레포마다 집계 기준이 다르다 | 2026-10-13 각 보고서가 기준을 머리에 명시하고 재집계했다: pr-agent는 머리 줄 제외 본문 문자열 출현 횟수("대략 집계"), open-code-review는 증거 표 행 단위·검증 칸 첫 판정(06은 의견 문서라 집계 제외), kodus-ai는 검증 열이 있는 표의 행 스크립트 집계. 이 문서는 옛 숫자를 인용하지 않는다 | 숫자를 신뢰도 척도로 쓰거나 레포 간 비교하지 말 것 |
| 9 | 3개 모두 정적 추적만 | 호출 순서·의존 해석·기본 동작을 실행으로 확인한 항목이 없다 | 운영 전 실제 설치·실행 검증 필요(`adoption-for-us.md` 5절) |
| 10 | 전이 의존성 라이선스·호출 위치 미조사 | pr-agent는 185개 `[[package]]`, open-code-review는 `go mod why` 미실행, kodus-ai는 락파일 전체 미조사 | 라이선스 검토가 불완전 |
