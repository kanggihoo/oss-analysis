# kodus-ai — 의존성(Q11), 외부 서비스, 최소 구성, 라이선스 경계

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q11 (+Q10 운영 요구, 라이선스 경계)
- 검증 수준 요약(검증 열이 있는 표의 행을 스크립트로 센 값, 2026-10-13 재집계. 복수 표기 행은 각 수준에 중복 계산하고 검증 열이 없는 표·본문 서술은 제외): 코드 확인 35 / 실행 확인 0 / 추론 1 / 미확인 1
- 실행 여부: **정적 추적만**. 설치·빌드·compose 기동을 하지 않았다. 해석 버전은 `pnpm-lock.yaml`을 읽은 값이다.
- 줄 번호 재대조(2026-10-13): `path:range` 약 95개와 2절의 `package.json` 선언·`pnpm-lock.yaml` 줄 번호를 모두 확인했다. 정정: Exa 도구 인용, `agent-review.stage.ts:601` 범위, `teams-or-enterprise-tier-policy.ts` 범위, `@octokit/plugin-enterprise-server` 직접 선언, `ai` import 파일 수, 라이선스 헤더 범위, RabbitMQ·compose 서술(4.1절 신설). 파일명만 인용한 `agent-tools.factory.ts`·`structured-output-repair.ts`는 열지 않았다.
- 용어: "declared-unused"는 `apps/ libs/ scripts/ test/ docker/`의 `.ts`에서 `from|require(|import(`로 찾지 못했다는 뜻이다(동적·문자열 require는 놓칠 수 있음, 미확인). 일부 줄 번호는 조사 에이전트가 연 값이며 핵심(`package.json` 선언, `pnpm-lock.yaml` importer 항목, 미사용 패키지 import 부재, 라이선스 파일)은 작성자가 재대조했다.

## 1. 워크스페이스 구조 (루트 목록을 전체 스택으로 단정하지 않는다)

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 루트 | `kodus-orchestrator` 2.1.8, `"license": "UNLICENSED"`, `packageManager: pnpm@11.9.0`. Dockerfile은 `pnpm@10.34.1` 설치(불일치) | `package.json:3,6,7`, `docker/Dockerfile:37` | 코드 확인 |
| 워크스페이스 | `pnpm-workspace.yaml`에 `packages:` 목록이 없고 `nodeLinker: hoisted`. 루트 `pnpm-lock.yaml`의 importer는 `.` 하나 | `pnpm-workspace.yaml`, `pnpm-lock.yaml` | 코드 확인 |
| 백엔드 앱 | `apps/api`, `apps/worker`, `apps/webhooks`, `apps/mcp-manager`의 `package.json`은 `"dependencies": {}`로 **백엔드 의존성이 전부 루트 `package.json`에** 있음. `apps/ast-cli`, `apps/analytics-cli`는 `package.json`이 없음 | 각 `package.json` | 코드 확인 |
| 별도 설치 | `apps/web`(Next 16.3.0, React 19.2.8, next-auth 5.0.0-beta.32), `apps/cli`(commander 14.0.3, **simple-git 3.36.0**, `license: MIT` `apps/cli/package.json:49`), `apps/try`(Next 15.5.19, `yarn.lock`)는 각자 락파일을 가진 **별도 의존성 그래프** | 각 락파일 | 코드 확인 |
| 이중 런타임 | 이미지에 bun이 포함되어 `bun install -g @kodus/kodus-graph@0.3.0`을 실행(외부 npm CLI) | `docker/Dockerfile:148-216` | 코드 확인 |

→ 웹 프런트·CLI는 백엔드 의존성과 무관하다. `simple-git` 같은 패키지는 **백엔드 목록에 없다**.

## 2. 의존성 표 (핵심 패키지)

모두 루트 `package.json`의 `dependencies`(별도 표기 제외), 해석 버전은 루트 `pnpm-lock.yaml` importer `.` 항목이다(괄호는 줄 번호).

| 패키지 | 선언 | 해석 | 분류 | 호출 위치 → 리뷰 단계 | 역할 | 교체·제거 영향 | 근거 |
|---|---|---|---|---|---|---|---|
| `@nestjs/common`·`core` | 11.1.19 | 11.1.19 (108,114) | 필수·런타임 | 전역 | DI·모듈 | 제거 불가 | `package.json` |
| `@golevelup/nestjs-rabbitmq` | ^9.0.2 | 9.0.2 (72) | 필수 | `workflow-job-consumer.service.ts:2-5` `@RabbitSubscribe` → 잡 소비 | 큐 소비·발행 | 모든 소비자 영향 | 코드 확인 |
| `amqplib` / `amqp-connection-manager` | ^2.0.1 / ^5.0.0 | 2.0.1 (198) / 5.0.0 (195) | 필수 | `workflow-job-consumer.service.ts:7`, `rabbitmq-connection-logger.service.ts:11` | AMQP·재연결 | 헬스 가드 의존 | 코드 확인 |
| `typeorm`/`@nestjs/typeorm`/`pg` | ^0.3.31 / ^11.0.3 / ^8.23.0 | 0.3.31 (372) / 11.0.3 (144) / 8.23.0 (321) | 필수 | `libs/core/infrastructure/database/typeorm/ormconfig.ts:4`, `cross-process-events.bridge.ts:7`(raw `pg`) | Postgres, outbox/inbox/락/LISTEN | 전반 | 코드 확인 |
| `mongoose`/`@nestjs/mongoose`/`mongodb` | ^9.9.4 / ^11.0.4 / ^7.6.0 | 9.9.4 (291) / 11.0.4 (123) / 7.6.0 (288) | 필수 | `libs/core/infrastructure/database/mongodb/mongoose.factory.ts:6` | PR 상태·규칙·샌드박스 리스 | 전반 | 코드 확인 |
| `cache-manager`/`@nestjs/cache-manager` | ^7.2.9 / ^3.1.3 | 7.2.9 (219) / 3.1.3 (105) | 필수 | `libs/core/cache/cache.module.ts:1-13` (`store:'memory'`) | **인메모리 캐시**(Redis 아님) | GitHub 호출 캐시 전부 | 코드 확인 |
| `pgvector`(npm) | ^0.3.0 | 0.3.0 (324) | **declared-unused** | `.ts` import 없음. 단 Postgres `vector` **확장**은 마이그레이션이 생성(`docker/postgres/initdb.d/enable_pgvector.sql:1`, 마이그레이션 `1766026227000`) | 없음 | npm 패키지는 제거 가능, 확장은 별개 | 코드 확인 |
| `@octokit/rest` | ^22.0.1 | 22.0.1 (159) | 필수(GitHub) | `github.service.ts:11` | GitHub REST | GitHub 전부 | 코드 확인 |
| `@octokit/auth-app` | ^8.2.0 | 8.2.0 (150) | 필수(App 모드) | `github.service.ts:4`, `createAppAuth :417` | 설치 토큰 | App 모드 불가 | 코드 확인 |
| `@octokit/plugin-enterprise-server` | ^20.0.0 | 20.0.0 (156) | 사용됨(GHES) | `github.service.ts:7-10` | GHES | GHES 경로 | 코드 확인(`package.json:308`, `pnpm-lock.yaml:156`, 2026-10-13 정정: 이전 "선언 미확인"은 오류) |
| `@octokit/plugin-throttling`/`-retry` | 루트 `package.json`·importer에 직접 선언 없음 | 전이 | 사용됨 | `github.service.ts:7-10` | 스로틀·재시도 | hoisting에 의존(추론) | 코드 확인/추론 |
| `@octokit/auth-oauth-app`, `octokit`(umbrella) | ^9.0.3, ^5.0.5 | 9.0.3, 5.0.5 | **declared-unused** | 없음 | - | 제거 가능 | 코드 확인 |
| `@gitbeaker/rest` | ^43.8.0 | 43.8.0 (69) | 필수(GitLab) | `gitlab.service.ts:7` | GitLab | GitLab 전부 | 코드 확인 |
| `bitbucket` | ^2.12.0 | 2.12.0 (213) | 필수(Bitbucket Cloud) | `bitbucket-cloud.service.ts:92` | Bitbucket | 해당 Provider | 코드 확인 |
| `@llamaduck/forgejo-ts` | 15.0.7 | 15.0.7 (93) | 필수(Forgejo) | `forgejo.service.ts:154` | Forgejo | 해당 Provider | 코드 확인 |
| `azure-devops-node-api` | ^15.1.2 | 15.1.2 (207) | **declared-unused**(Azure는 `axios` 직접 호출, `azure-repos-request-helper.ts:2`) | 없음 | - | 제거 가능 | 코드 확인 |
| `ai`(Vercel AI SDK) | ^7.0.83 | 7.0.83 (189) | 필수 | `libs/llm/agent-loop-call.ts:31` 외 `from 'ai'` import 약 42개 파일(spec 제외, 포함하면 59, `apps/web` 제외) → 모든 LLM 호출 | `generateText`/`embed` | 핵심 | 코드 확인 |
| `@ai-sdk/anthropic`/`openai`/`google`/`google-vertex`/`amazon-bedrock`/`azure`/`openai-compatible` | ^4.0.44 / ^4.0.50 / ^4.0.56 / ^5.0.68 / ^5.0.66 / ^4.0.52 / ^3.0.39 | 4.0.44 / 4.0.50 / 4.0.56 / 5.0.68 / 5.0.66 / 4.0.52 / 3.0.39 | 필수(제공자별) | `libs/llm/providers/*`, `libs/llm/model-builders.ts:13-15`, `libs/llm/managed-slot.ts:12` | 모델 제공자 | 제공자별 | 코드 확인 |
| `openai`(공식 SDK) | ^7.8.0 | 7.8.0 (306) | **declared-unused**(`from 'openai'` 없음) | 없음 | - | 제거 가능(다른 패키지의 peer일 수 있어 락 확인 필요) | 코드 확인 |
| `@anthropic-ai/sdk` | ^0.122.0 (**devDependencies**) | 0.122.0 (394) | 개발 전용 | `scripts/benchmark/classify-fp.ts:30` | 벤치 스크립트 | 런타임 영향 없음 | 코드 확인 |
| `@langchain/*` | 미선언 | `@langchain/core@1.2.1` 전이(morphsdk 경유) | 전이만 | **import 없음** | - | - | 코드 확인 |
| `@modelcontextprotocol/sdk` | ^1.29.0 | 1.29.0 (96) | 선택(MCP 서버) | `libs/mcp-server/services/mcp-server.factory.ts:3`, `libs/mcp-server/mcp-adapter/client.ts` → 비즈니스 로직 fetcher | MCP 클라이언트·서버 | MCP 기능만 | 코드 확인 |
| `e2b` | ^2.46.1 | 2.46.1 (246) | 선택 | `e2b-sandbox.service.ts:5`, `sandboxSyntaxValidator.service.ts` → 샌드박스·committable 구문 검증 | 원격 샌드박스 | 로컬 샌드박스로 대체 | 코드 확인 |
| `@morphllm/morphsdk` | ^0.2.194 | 0.2.194 (99) | 선택 | `validate-suggestions.stage.ts:16` `applyEdit` → committable 검증 | 제안 적용 | 해당 단계(`partial`)만 | 코드 확인 |
| `diff` | ^9.0.0(`package.json:336`) | 9.0.0 (240). 락 importer의 specifier는 `>=8.0.3`(`pnpm-lock.yaml:240`)이며 `pnpm-workspace.yaml:32`의 override 때문 | 필수 | `validate-suggestions.stage.ts:18` `parsePatch`, `azureRepos.service.ts` `createTwoFilesPatch` | patch 생성·파싱 | 해당 기능 | 코드 확인 |
| `tiktoken` | ^1.0.22 | 1.0.22 (366) | 필수 | `libs/llm/token-estimate.ts:25,55`, `tokenChunking.service.ts:4` | BYOK 제한기·청킹 | 해당 기능 | 코드 확인 |
| `zod`/`ajv`/`zod-to-json-schema` | ^4.4.3 / ^8.20.0 / ^3.25.2 | 4.4.3 / 8.20.0 | 필수 | `agent-tools.factory.ts`, `libs/llm/structured-output-repair.ts` | 스키마·복구 | 핵심 | 코드 확인 |
| `@langfuse/*` | ^5.11.0 | 5.11.0 (78-90) | 선택(`LANGFUSE_TRACING`) | `libs/core/log/langfuse.ts:1` | LLM 트레이싱 | 트레이싱만 | 코드 확인 |
| `@casl/ability` | ^7.0.1 | 7.0.1 (63) | 필수 | `permissionsAbility.factory.ts:1` | RBAC | 인가 | 코드 확인 |
| `passport`/`passport-jwt`/`@nestjs/jwt`/`@nestjs/passport` | ^0.7.0 / ^4.0.1 / ^11.0.2 / ^11.0.5 | 0.7.0 / 4.0.1 / 11.0.2 / 11.0.5 | 필수 | `jwt-auth.strategy.ts:4` | JWT | 인증 | 코드 확인 |
| `@node-saml/passport-saml` | ^5.1.0 | 5.1.0 (147) | 선택(SSO, **ee**) | `libs/ee/sso/strategies/saml-auth.strategy.ts:9` | SAML | SSO만 | 코드 확인 |
| `ml-kmeans` | ^6.0.0 | 6.0.0 (279) | 필수(컴파일) | `kodyFineTuning.service.ts:3` — **활성 파이프라인에서 호출되지 않음** | 클러스터링 | 비활성 기능 | 코드 확인 |
| `exa-js` | ^2.19.0 | 2.19.0 (249) | 선택(`API_EXA_KEY`) | `documentation-search-exa.service.ts:19`(`import Exa`), 진입 메서드 `searchByFilePlan`(`:90`). `searchDocs`는 이 파일이 아니라 에이전트 도구로 등록됨(`review-agent.contract.ts:464`, `base-code-review-agent.provider.ts:83`) | 해당 도구 | 코드 확인 |
| `@sentry/*`, `@pyroscope/nodejs`, `posthog-node`, `resend`/`nodemailer` | 각각 | 각각 | 선택(환경변수 게이트) | 관측·알림 | 관측 | 손실만 | 코드 확인 |
| `date-fns`, `passport-saml-metadata`, `keyv` | | | **declared-unused**(백엔드). `keyv`는 `@nestjs/cache-manager`의 peer로 락에 보임 | 없음 | - | 제거 전 peer 확인 | 코드 확인 |
| tree-sitter / ts-morph / simple-git / isomorphic-git / ripgrep(npm) | 백엔드 미선언 | `isomorphic-git`, `@vscode/ripgrep`은 morphsdk 경유 전이 | 코드에서 사용 안 함 | **백엔드에 AST 라이브러리와 git 클라이언트 라이브러리가 없다.** 클론은 샌드박스의 `git` 바이너리, 검색은 apt `ripgrep` | - | - | 코드 확인(부정 grep) |
| Redis/BullMQ(`ioredis`,`redis`,`bull*`) | 없음 | 없음 | **Redis 사용 없음**(락은 Postgres advisory, 캐시는 메모리) | - | - | - | 코드 확인(부정 grep) |

- 자체 구현과 SDK의 경계: **루프 정책(예산·압축·완료 게이트·강제 종료)·도구·검증·dedup·outbox·락은 자체 구현**이고, LLM 호출 추상화·도구 호출 반복의 엔진 자체는 AI SDK(`generateText`)가 담당한다. 도구 결과를 대화에 붙이는 일도 SDK가 한다(SDK 내부는 이 레포에 없어 추론). `@langchain/*`·LiteLLM은 쓰이지 않는다.
- 같은 패키지의 다중 해석: `ai@7.0.83`과 `ai@7.0.48`, `openai@7.8.0`과 morphsdk가 끌어오는 `openai@4.104.0`이 락에 공존한다(조사 에이전트 확인).

## 3. 외부 서비스·바이너리

| 서비스/바이너리 | 최소 리뷰 루프에 필요? | 근거 | 검증 |
|---|---|---|---|
| PostgreSQL(+`vector` 확장) | **필요** | TypeORM, outbox/inbox/advisory 락/브리지. 확장은 마이그레이션이 생성 | 코드 확인 |
| MongoDB | **필요** | 워커·API가 `SharedMongoModule` import(`apps/worker/src/worker.module.ts:70`). PR 상태·규칙이 여기 | 코드 확인 |
| RabbitMQ + **delayed-message 플러그인** | **리뷰가 실제로 돌려면 필요**(코드가 요구). 단 이 레포의 `docker-compose.prod.yml`에는 정의되어 있지 않다 | 구성별 정의·연결 실패·비활성 시 동작은 [4.1절](#rabbitmq-compose). 요약: 기본값(`API_RABBITMQ_ENABLED`≠`false`)에서 worker·webhooks는 연결을 기다리다 실패하도록 설계(`rabbitmq.module.ts:84-113`), `false`면 모듈을 건너뛰어 앱은 뜨지만 잡이 소비되지 않는다 | 코드 확인 / 추론 |
| `git` 바이너리 | **필요**(로컬 샌드박스) | 이미지에 설치(`docker/Dockerfile:170`) | 코드 확인 |
| `ripgrep`(`rg`) | 조건부(모델 `grep` 도구) | `agent-tools.factory.ts:384`, `e2b-sandbox.service.ts:134`, 이미지에 apt 설치 | 코드 확인 |
| `kodus-graph` CLI(bun 전역) | 조건부(call graph) | `agent-review.stage.ts:601-654`(call graph 생성 `generateContext`/`generateContextLegacy` 호출은 `:636-654`), CLI 호출은 `libs/code-review/infrastructure/adapters/services/graph/kodus-graph-cli.ts`, 없으면 legacy 경로 또는 경고 | 코드 확인 |
| LLM API 한 곳(또는 조직 BYOK) | **필요** | `.env.example`에 제공자 키 다수. `API_OPEN_AI_API_KEY`는 임베딩 dedup용 선택 | 코드 확인 |
| E2B API | 불필요 | `SANDBOX_PROVIDER=auto`이면 키 없을 때 로컬 | `libs/sandbox/modules/sandbox.module.ts:26-51` | 코드 확인 |
| Morph API | 불필요(해당 단계만) | `validate-suggestions.stage.ts` | 코드 확인 |
| Exa, Langfuse, Sentry, Pyroscope, PostHog, BetterStack | 불필요(환경변수 게이트) | - | 코드 확인 |
| `mcp-manager` 서비스 | 불필요(Jira/Linear MCP를 쓰려면 필요) | `API_MCP_SERVER_ENABLED` 기본 off(doctor) | 코드 확인 |
| Docker | 불필요(앱이 리뷰에 docker를 쓰지 않음) | `child_process`는 로컬 샌드박스·doctor만 | 코드 확인(grep) |
| `telemetry.kodus.io` | 불필요하나 **자체 호스팅도 일일 익명 하트비트 전송**(`KODUS_TELEMETRY_DISABLED`로 끔) | `apps/worker/src/cron/self-hosted-beacon.cron.ts:10-77` | 코드 확인 |

## 4. Compose와 최소 구성

| 파일 | 역할 | 서비스 | 검증 |
|---|---|---|---|
| `docker-compose.prod.yml` | **자체 호스팅 프로덕션**. GHCR 사전 빌드 이미지, `API_CLOUD_MODE=false` | `api`, `worker`(`WORKER_ROLE=code-review`), `worker-analytics`(`WORKER_ROLE=analytics`), `webhooks`, `web`, `db_postgres`(`pgvector/pgvector:pg16`), `db_mongodb`(`mongo:8.2.11`)(`:17,37,56,75,98,112,133`). **`rabbitmq`·`mcp-manager` 서비스 없음**, `depends_on`은 DB 두 개뿐. RabbitMQ 처리는 [4.1절](#rabbitmq-compose) | 코드 확인 |
| `docker-compose.dev.yml` | 로컬 개발(`docker/Dockerfile.dev` 빌드) | `kodus-api`, `worker`, `worker-analytics`, `webhooks`, `mcp-manager`, `web`, `try`, `pyroscope`, `rabbitmq`(`./docker/rabbitMQ` 빌드), `db_postgres`, `db_mongodb` | 코드 확인 |
| `docker-compose.bench.yml` | 벤치(브랜치를 빌드해 실행하는 독립 compose). **`rabbitmq` 서비스 있음**(`:226-246`). 파일 머리 주석이 "prod compose pulls a fixed GHCR image and has no RabbitMQ (the review pipeline needs it)"라고 적는다(`:17-19`) | 코드 확인 |
| `docker-compose.preview*.yml`, `test.yml`, `sim.yml` | 프리뷰 오버레이(dev compose 위에 얹음, `docker-compose.preview.selfhosted.yml:1-5`), 테스트 인프라(PG·Mongo만, 서비스 `db_postgres`·`db_mongodb`), `sim`(`api`·`worker`·`webhooks`만, 사전 구운 로컬 이미지 `kodus-ai-*:local` 사용). 세 종류 모두 파일에 `rabbit` 문자열이 없다(grep 0건). `sim`의 용도는 파일 안에서 "Production Build - Simulation"(`docker-compose.sim.yml:5`)이라는 설명 외에 확인하지 못함 | 코드 확인 / 미확인 |
| `docker/rabbitMQ/Dockerfile` | `rabbitmq:4.2.2-management`+`rabbitmq_delayed_message_exchange` 4.2.0+prometheus | - | 코드 확인 |

<a id="rabbitmq-compose"></a>
### 4.1 RabbitMQ: 어느 구성에서 필수이고, 어디에 정의되며, prod compose는 무엇을 가정하는가 (2026-10-13 정정)

정정 이유: 이전 서술은 "RabbitMQ 필수"와 "prod compose에 서비스 없음"을 따로 적어 두 사실의 관계가 불분명했다. 아래는 모든 `docker-compose*.yml`·환경변수·모듈 초기화 코드를 다시 열어 정리한 것이다.

**A. 앱이 요구하는 것 (코드 확인)**

| 항목 | 사실 | 위치 |
|---|---|---|
| 모듈 등록 | api(`enableConsumers:false`), worker(code-review 역할은 `true`(`:79`), analytics 역할은 DI 때문에 소비자 없이 연결만 두는 `false`(`:124`, 주변 주석이 설명)), webhooks(`false`)가 모두 `RabbitMQWrapperModule.register`를 호출 | `apps/api/src/api.module.ts:121`, `apps/worker/src/worker.module.ts:79,124`, `apps/webhooks/src/modules/webhook-handler.module.ts:37` |
| 활성 스위치 | `API_RABBITMQ_ENABLED`가 문자열 `'false'`가 아니면 활성(기본 활성). 비활성이면 `RabbitMQModule` import를 건너뛰고 팩토리는 `null` 반환 | `libs/core/infrastructure/queue/rabbitmq.module.ts:49,70-82,182-192` |
| 연결 대기 | `connectionInitOptions.wait`: 컴포넌트가 `worker`·`webhook`이면 `true`(fail-fast), `api`는 `false`(HTTP는 계속 서빙, 재연결 관리자가 재시도), `API_RABBITMQ_WAIT=true|false`로 덮어씀. 타임아웃 5초. 코드 주석은 `wait:true`를 "worker/webhook: fail-fast"라 설명한다. **`wait:true` 실패 시 실제 부팅 실패는 `@golevelup/nestjs-rabbitmq` 라이브러리 동작이며 라이브러리 소스는 이 레포에 없어 확인하지 못했다(추론)** | `rabbitmq.module.ts:84-113` |
| URI | `API_RABBITMQ_URI`, 미설정이면 `amqp://localhost:5672/` | `libs/core/infrastructure/config/loaders/rabbitmq.loader.ts:8-9` |
| 지연 플러그인 | 토폴로지가 `x-delayed-message` 타입 교환 3개(`orchestrator.exchange.delayed`, `workflow.exchange.delayed`, `workflow.events.delayed`)를 선언하고, 주석이 `rabbitmq_delayed_message_exchange` 플러그인을 요구한다고 적는다(`:41-43`). 에러 핸들러는 `x-delay` 헤더로 재시도를 지연한다. 플러그인이 없는 브로커에서 선언이 실패하는지는 실행하지 않아 추론 | `libs/core/infrastructure/queue/config/rabbitmq-topology.config.ts:11-25,40-53,64-70`, `rabbitmq-error.handler.ts:158` |
| 비활성(`false`)일 때 | 앱은 뜨지만 리뷰가 안 돈다: `MessageBrokerService`는 `@Optional()` 연결로 경고만 남기고 `publishMessage`는 예외, outbox 릴레이는 브로커가 연결되지 않으면 매 사이클을 건너뛰어 outbox 행만 쌓인다. 레포의 doctor가 같은 결론을 낸다("Git events are never handed to the worker, so no review runs", `fail`) | `libs/core/infrastructure/queue/messageBroker/messageBroker.service.ts:16-23,34-40`, `libs/core/workflow/infrastructure/outbox-relay.service.ts:217-225`, `apps/api/src/doctor/checks/broker.checks.ts:84-96` |
| 헬스 | 비활성이면 워커 AMQP 헬스 요구가 꺼지고(`requireAmqp`), 웹훅 헬스는 `skipped` | `apps/worker/src/main.ts:111-117`, `apps/webhooks/src/controllers/webhook-health.controller.ts:101-107` |

비활성 시 "리뷰가 안 돈다"는 위 코드 조각을 종합한 결론이며 실행하지 않았다(추론).

**B. 구성별로 어디에 정의되는가 (코드 확인, 외부 레포는 미확인)**

| 구성 | RabbitMQ 정의 | 근거 |
|---|---|---|
| `docker-compose.dev.yml` | **있음.** `rabbitmq` 서비스(`./docker/rabbitMQ` 빌드, 포트 5672/15672/15692, 네트워크 별칭 `rabbitmq-local`·`rabbitmq`, healthcheck). api·worker 등은 `depends_on: rabbitmq`(`required: false`로 외부 브로커 사용 허용) | `docker-compose.dev.yml:541-580`, `:55-62` |
| `docker-compose.bench.yml` | **있음.** 같은 이미지 빌드 | `docker-compose.bench.yml:226-246` |
| `docker-compose.prod.yml` | **없음.** 서비스 7개에 RabbitMQ가 없고 `depends_on`도 DB뿐. 환경은 `${ENV_FILE:-.env.prod}`로 주입하며 사용법 주석은 `.env.example` 복사를 안내 | `docker-compose.prod.yml:7-10,17-133` |
| `preview*`, `sim`, `test` | 없음(`rabbit` 문자열 0건). preview는 dev compose 위 오버레이라 dev의 `rabbitmq`를 쓴다(`docker-compose.preview.selfhosted.yml:1-5`는 오버레이임을 명시) | 각 파일 |
| 이미지 | 이 레포가 `docker/rabbitMQ/Dockerfile`(`rabbitmq:4.2.2-management` + 지연 플러그인 4.2.0)을 두고 별도 워크플로로 GHCR에 게시("Kodus RabbitMQ: Build and Publish") | `docker/rabbitMQ/Dockerfile:5-9`, `.github/workflows/rabbitmq-build-push.yml:1-7,27` |
| 외부 `kodus-installer` | **이 레포에 없어 내용 미확인.** 간접 증거만 있다: `.env.schema`가 `USE_LOCAL_RABBITMQ`("Same logic as USE_LOCAL_DB … False if you bring your own broker")를 정의하고 설치기가 읽는 값이라고 적으며(`.env.schema:127-137`, 이 레포 코드에서 이 변수를 읽는 곳은 없음), 설치기 기본 URI `amqp://kodus:kodus@rabbitmq:5672/kodus-ai`를 힌트로 둔다(`.env.schema:312`). 공식 문서는 `./scripts/install.sh`가 `rabbitmq`를 포함한 서비스를 띄우고 `USE_LOCAL_RABBITMQ=false`로 관리형 브로커를 가리킬 수 있다고 한다(`docs/_snippets/deploy-basic-setup.mdx:36-39`, `docs/en/how_to_deploy/deploy_kodus/generic_vm.mdx:75-89`) | 문서 확인 / installer 코드 미확인 |

**C. prod compose는 무엇을 가정하는가**

- 코드 확인: prod compose에는 RabbitMQ 서비스·별칭이 없다. 그런데 prod compose가 복사하라고 안내한 `.env.example`의 기본 URI는 `amqp://dev:devpass@rabbitmq-local:5672/kodus-ai?heartbeat=60`(`.env.example:200`)이고 `rabbitmq-local` 호스트명은 dev compose의 네트워크 별칭이다(`docker-compose.dev.yml:559-567`). prod compose 네트워크에는 이 이름이 없다.
- 따라서 prod compose는 **브로커가 compose 밖에서(외부·관리형 서비스이거나 같은 Docker 네트워크에 사용자가 따로 붙인 컨테이너로) 제공되고 `.env.prod`의 `API_RABBITMQ_URI`가 그것을 가리킨다고 가정**하는 모양이다(추론). compose 파일 안에는 이 가정이 주석으로 적혀 있지 않아 **작성 의도는 확인하지 못했다**. `bench` compose 주석("prod compose … has no RabbitMQ")은 이 사실 자체를 개발자가 인지하고 있음을 보여주지만 의도를 설명하지는 않는다.
- 결론: "RabbitMQ 필수"는 **앱 코드와 dev·bench·설치기(문서 기준) 구성에서 맞고**, `docker-compose.prod.yml`만 단독으로 `up`하면 브로커가 없다(코드 확인). 기본 활성 상태에서 worker·webhooks가 브로커에 연결하지 못했을 때의 동작은 라이브러리에 달려 있다(추론).

**최소 자체 호스팅 구성(문서·설정 근거로 도출)**: `db_postgres`(pgvector 이미지), `db_mongodb`, **RabbitMQ(이 레포의 `docker-compose.prod.yml`에는 없음. 제공 방식은 [4.1절](#rabbitmq-compose) 참조)**, `api`, `worker`(`code-review`), `webhooks`, UI가 필요하면 `web`. `worker-analytics`와 `mcp-manager`는 선택. 런타임 이미지에 `git`·`rg`·`kodus-graph`가 포함된다. 첫 부팅 시 `RUN_MIGRATIONS=true`(`docker/prod-entrypoint.sh:51-58`). 처리량·메모리 수치는 측정하지 않았으므로 제시하지 않는다.

**필수 환경변수(이름만)**: Joi로 검증하는 필수는 `API_PORT`뿐(`libs/core/infrastructure/config/schemas/config.schema.ts:5`). 그 외 부팅에 필요한 것: `WORKER_ROLE`(`apps/worker/src/worker-role.ts:25-35`), `API_CRYPTO_KEY`(`libs/common/utils/crypto.ts:5-9`, import 시점), `CODE_MANAGEMENT_SECRET`·`CODE_MANAGEMENT_WEBHOOK_TOKEN`(`libs/common/utils/webhooks/webhookTokenCrypto.ts:4-14`, import 시점. `azureRepos.service.ts:81`이 import하므로 `PlatformModule`이 로드되는 곳에서 필요, 경로는 추론), `API_WEBHOOKS_PORT`(웹훅), `API_JWT_SECRET`(추론), Postgres(`DATABASE_URL` 또는 `API_PG_DB_*`), Mongo(`MONGODB_URI` 또는 `API_MG_DB_*`), RabbitMQ(`API_RABBITMQ_URI`, `API_RABBITMQ_ENABLED`), GitHub App 모드(`API_GITHUB_APP_ID`, `API_GITHUB_PRIVATE_KEY`, `GLOBAL_GITHUB_CLIENT_ID`, `API_GITHUB_CLIENT_SECRET`), Provider 웹훅 URL(`API_GITHUB_CODE_MANAGEMENT_WEBHOOK` 등). 세부는 `.env.example`(243개 변수명, `.env.schema`에서 자동 생성).

## 5. (참고) 비용·재시도 영향

LLM 비용은 finder+후보별 verifier 루프(후보 수에 비례)와 dedup·severity·포맷·요약 호출로 늘어난다. 실행당 토큰·금액 상한이 없어 비용 통제는 BYOK 한도·스텝 수·시간 제한에 의존한다([02 4.3](02-context-loop-verify.md#q4)). 수치는 측정하지 않았다.

<a id="license"></a>
## 6. 라이선스 경계 (법률 자문 아님)

이 절은 **파일 수준 사실과 코드 조건**만 적는다. 법적 해석은 하지 않는다.

### 6.1 저장소가 스스로 말하는 규칙

- `license.md`: "All source code **except** files or directories marked as 'enterprise edition' is licensed under AGPL-3.0", `.ee.`가 파일명에 있거나 `ee/`가 경로에 있으면 AGPL이 아니라 **상용 라이선스**(`license.md:5-10`). 코드 확인.
- `license_ee.md`: Enterprise 코드는 유효한 라이선스가 있을 때만 사용·복사·수정·배포 가능. **평가 목적의 로컬 열람·수정·테스트는 허용**하나 프로덕션·사내 배포는 라이선스 필요(`license_ee.md:5-19`), 오픈소스 포크에 병합 금지(`:25-28`). 코드 확인.
- `libs/ee/linked-repositories/LICENSE`: 자체 파일로 같은 규칙과 "Production use requires a valid Teams or Enterprise commercial agreement"(`:1-10`). 코드 확인.
- 불일치: 루트 `package.json`은 `"license": "UNLICENSED"`, `apps/cli/package.json:49`는 `MIT`, README 배지는 AGPLv3. AGPL-3.0 전문 파일과 `NOTICE`는 없다(`LICENSE*|NOTICE*|COPYING*` 검색). `@license Kodus Tech. All rights reserved.` 헤더는 **소스 18개 파일**에 있다(2026-10-13 전수 grep으로 정정; 이전 "일부 비-ee 파일" 서술은 범위가 불명확했다). 5개는 `libs/ee/` 경로, 3개는 `*.provider.ee.ts`라 경로 규칙상 이미 상용 대상이고, **나머지 10개는 경로·파일명에 ee 표지가 없다**: `libs/code-review`(5개, 예: `pipeline/strategy/code-review-pipeline.strategy.ts:1-4`, `infrastructure/adapters/services/codeReviewHandlerService.service.ts:1-4`), `libs/core`(4개: `domain/interfaces/*` 2개, `infrastructure/pipeline/{interfaces/pipeline-strategy.interface.ts,services/pipeline-factory.service.ts}`), `libs/kodyFineTuning/.../fine-tuning.service.ts:2-5`. 전체 목록과 줄 번호는 [06 3.2절](06-fit.md#license-header). **`libs/agent-harness`·`libs/llm`·`libs/sandbox`에는 헤더가 없다.** 경로 규칙상 이 10개 파일은 AGPL 대상이지만 헤더는 독점 의도를 시사한다 — 해석은 법무 판단 몫이다.
- `ee` 경로 전수(`find`): `libs/ee`, `apps/web/src/features/ee`, `test/unit/ee`, `libs/core/providers/{code-review-pipeline,file-analyzer,pipeline}.provider.ee.ts`. 코드 확인.

### 6.2 `ee` 위치별 내용

| 위치 | 내용 |
|---|---|
| `libs/ee/analytics-warehouse/` | 분석 스키마·적재·PR 분류기·마이그레이션 |
| `libs/ee/automation/` | `runCodeReview.use-case.ts` |
| `libs/ee/codeBase/` | `codeBaseConfig.service.ts`, `kodyIssuesAnalysis.service.ts` |
| `libs/ee/codeReview/` | `fileReviewContextPreparation/*`(레거시), `stages/kody-fine-tuning.stage.ts` |
| `libs/ee/codeReviewSettingsLog/` | 감사 로그 이벤트·핸들러 |
| `libs/ee/configs/environment/` | `environment.template.ts` 등. 런타임 `environment.ts`는 gitignore되어 **이미지 빌드 시 `sed`로 생성**(`API_CLOUD_MODE`를 컴파일 타임 상수로, `docker/Dockerfile:79-82`, `.gitignore:152`) |
| `libs/ee/infrastructure/ecs/` | ECS 태스크 보호 |
| `libs/ee/kodyRules/` | 규칙 서비스·Mongo 리포지토리·검증·detector 컴파일러·라이브러리 규칙 JSON 808개 |
| `libs/ee/license/` | 클라우드/자체 호스팅 라이선스 서비스, 티어 정책, `EnterpriseTierGuard` |
| `libs/ee/linked-repositories/` | 교차 저장소 문맥(자체 `LICENSE`) |
| `libs/ee/shared/` | `permissionValidation.service.ts` |
| `libs/ee/sso/` | SAML SSO |
| `apps/web/src/features/ee/` | cockpit, subscription, user-logs, sso, byok, linked-repositories, token-usage, onboarding UI |
| `libs/core/providers/*.provider.ee.ts` | **리뷰 파이프라인·파일 분석 컨텍스트를 조립**하는 3개 파일 |

### 6.3 리뷰 경로의 `ee` 의존 (치명적)

| ee 파일 | 경로상 이유 | 근거 | 검증 |
|---|---|---|---|
| `libs/core/providers/code-review-pipeline.provider.ee.ts` | `PipelineExecutor`+전략+옵저버를 묶는 유일한 배선 | `:22-53`, `libs/code-review/modules/codebase.module.ts:43-44` | 코드 확인 |
| `libs/core/providers/pipeline.provider.ee.ts` | `PipelineFactory` | `:14-25` | 코드 확인 |
| `libs/core/providers/file-analyzer.provider.ee.ts` | `FILE_REVIEW_CONTEXT_PREPARATION_TOKEN` 바인딩(주입처 없음) | `:15-25` | 코드 확인 |
| `libs/ee/automation/runCodeReview.use-case.ts` | 잡 프로세서가 import해 호출 | `libs/code-review/workflow/code-review-job-processor.service.ts:12,222-236` | 코드 확인 |
| `libs/ee/codeBase/codeBaseConfig.service.ts` | 설정 해석·자격증명 복호화 | `:651-659` | 코드 확인 |
| `libs/ee/shared/services/permissionValidation.service.ts` | 라이선스·트라이얼·BYOK 게이팅과 모델 슬롯 해결(비-ee·비-spec 파일 약 30개가 import, 2026-10-13 재집계) | `validate-prerequisites.stage.ts:35`, `permissionValidation.service.ts:206-300` | 코드 확인 |
| `libs/ee/license/*` | `ValidatePrerequisitesStage`가 import, `LicenseModule`이 다수 모듈에 import | `validate-prerequisites.stage.ts:30-31`, `license.module.ts:18-49` | 코드 확인 |
| `libs/ee/kodyRules/service/kodyRules.service.ts` | **규칙 서비스 토큰에 바인딩된 유일 구현** | `libs/kodyRules/modules/kodyRules.module.ts:12,120` | 코드 확인 |
| `libs/ee/configs/environment` | `main.ts` 등 24개 이상 import | `apps/api/src/main.ts:35`, `apps/webhooks/src/main.ts:28`, `libs/core/workflow/modules/workflow.module.ts:49` | 코드 확인 |
| `libs/ee/linked-repositories` | `agent-review.stage.ts:84` 컴파일 타임 import, 실행은 Teams/Enterprise 티어 게이트 | `agent-review.stage.ts:2941-2956` | 코드 확인 |
| `libs/ee/analytics-warehouse` | `worker.module.ts:6`이 파일 수준 import → 모든 워커 이미지에 컴파일되지만 `analytics` 역할에서만 사용 | `apps/worker/src/worker.module.ts:6,102-142` | 코드 확인 |
| ee 모델 | TypeORM 엔티티 레지스트리가 ee 모델을 import(DB 스키마 영향) | `libs/core/infrastructure/database/typeorm/entities.ts:8-9,38` | 코드 확인 |

의존 방향: 비-ee·비-테스트 소스 중 약 110개가 ee 경로를 import하고 `apps/web` 약 70개 파일이 `features/ee`를 import한다(grep 집계). **AGPL-only 트리는 그대로 컴파일되지 않는다**(`libs/ee/configs/environment`가 `main.ts`에 필요, 규칙 서비스·파이프라인 provider가 ee에서 바인딩). 빌드는 시도하지 않았다(추론).

### 6.4 런타임 라이선스 검사

- `LICENSE_SERVICE_TOKEN`은 `environment.API_CLOUD_MODE`이면 클라우드 `LicenseService`, 아니면 `SelfHostedLicenseService`(`libs/ee/license/license.module.ts:26-37`). `API_CLOUD_MODE`는 빌드 타임에 고정(`docker/Dockerfile:79-82`). 코드 확인.
- 자체 호스팅 라이선스는 Ed25519 JWT(조직 파라미터에 저장, 하드코딩 공개키로 검증, 5분 캐시, `plan`·`seats`·`exp`). 키가 없으면 `{valid:false}`(`libs/ee/license/self-hosted-license.service.ts:22-28,63-122`). 코드 확인.
- **키 없는 자체 호스팅(Community)**: `validateSelfHostedPermissions`가 `{allowed:true}`를 반환(좌석·사용자 제한 없음, `libs/ee/shared/services/permissionValidation.service.ts:662-680`). 라이선스가 있으면 좌석 검증(전역 좌석 상한, `self-hosted-license.service.ts:166-250`). 키 없는 인스턴스도 **핵심 리뷰 파이프라인은 실행된다**. 코드 확인.
- 기능 게이트: `EnterpriseTierGuard`는 SSO 설정(`apps/api/src/controllers/ssoConfig.controller.ts:50`)·코드리뷰 설정 로그(`codeReviewSettingLog.controller.ts:29`)를 Enterprise 아니면 403(fail-closed, `libs/ee/license/guards/enterprise-tier.guard.ts:39-92`). 링크 저장소·cockpit은 Teams/Enterprise(`tier/teams-or-enterprise-tier-policy.ts:6-43`(`isTeamsOrEnterpriseTierAllowed`는 `:25-43`)). 코드 확인.

### 6.5 stated rule상 AGPL(경로에 `ee/`·`.ee.` 없음)

`apps/api`, `apps/worker`, `apps/webhooks`, `apps/mcp-manager`, `apps/cli`, `apps/web`(`features/ee` 제외), `apps/ast-cli`, `apps/analytics-cli`, `apps/try`; `libs/code-review`, `libs/agent-harness`, `libs/llm`, `libs/sandbox`, `libs/platform`, `libs/core`(3개 `*.provider.ee.ts` 제외), `libs/identity`, `libs/integrations`, `libs/organization`, `libs/kodyRules`, `libs/automation`, `libs/cli-review`, `libs/cockpit`, `libs/telemetry` 등 `libs/ee` 밖 전부. 이는 저장소가 말하는 규칙을 경로에 적용한 것이며 법적 효과에 대한 판단이 아니다.

### 6.6 우리 서비스 관점의 사실 요약

- 코드를 복사해 쓰려면 **ee 경로를 쓰지 않는 구성**이어야 하는데, 현 구조에서는 리뷰 파이프라인 조립·실행 진입·설정 로더·규칙 서비스가 모두 ee라서 해당 부분은 다시 써야 한다.
- AGPL 부분을 네트워크로 제공하는 SaaS에 포함하면 소스 공개 의무가 따를 수 있다(AGPL 일반 조건, 법무 확인 필요).
- `libs/agent-harness`·`libs/llm`·`libs/sandbox`는 ee 경로가 아니고 비-spec 소스에 `@libs/ee` import가 없으며(재확인) `@license` 헤더도 없다(전수 grep). 다만 `libs/core`·`libs/common/utils`의 일부 파일과 `libs/code-review`의 파일 2개에 의존하므로 재사용 시 그 파일들도 함께 가져가야 한다([06 3.1절](06-fit.md#reuse-coupling)). `libs/llm`의 `@libs/ee` import는 테스트 파일(`strict-wire-schema.spec.ts:31,42`)에만 있다.

## 경로 사전 (짧은 이름 → 풀 경로)

- `github.service.ts`: `libs/platform/infrastructure/adapters/services/github/`; `gitlab.service.ts`, `forgejo.service.ts`: `libs/platform/infrastructure/adapters/services/`; `bitbucket-cloud.service.ts`: `.../services/bitbucket/`; `azureRepos.service.ts`: `.../services/azureRepos/`
- `workflow-job-consumer.service.ts`, `cross-process-events.bridge.ts`: `libs/core/workflow/infrastructure/`; `rabbitmq-connection-logger.service.ts`, `rabbitmq.module.ts`: `libs/core/infrastructure/queue/`
- `agent-review.stage.ts`, `validate-suggestions.stage.ts`, `validate-prerequisites.stage.ts`: `libs/code-review/pipeline/stages/`; `agent-tools.factory.ts`: `libs/code-review/infrastructure/agents/engine/`
- `e2b-sandbox.service.ts`: `libs/sandbox/infrastructure/providers/`; `sandboxSyntaxValidator.service.ts`, `documentation-search-exa.service.ts`: `libs/code-review/infrastructure/adapters/services/`
- `permissionsAbility.factory.ts`, `jwt-auth.strategy.ts`: `libs/identity/infrastructure/adapters/services/{permissions,auth}/`
- `kodyFineTuning.service.ts`: `libs/kodyFineTuning/infrastructure/adapters/services/`; `tokenChunking.service.ts`: `libs/core/infrastructure/services/tokenChunking/`
