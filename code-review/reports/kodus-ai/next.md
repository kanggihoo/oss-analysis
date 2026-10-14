# kodus-ai — next (확인 범위·미확인·다음 시작점)

- 분석 SHA: `45676c5fe7ac016b6206ccea006e459677d92842` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q1~Q12 전체
- 검증 수준 요약: 실행 확인 0. 문서별 건수는 각 문서 머리(검증 열이 있는 표를 스크립트로 센 값). 추론·미확인은 아래 체크리스트
- 실행 여부: 정적 추적만. `repos/kodus-ai`는 읽기만 했고 clean·고정 SHA 상태를 `rev-parse`/`status --porcelain`으로 확인했다.

## 1. 확인한 범위

- 웹훅 수신(5개 Provider) → raw payload 저장(outbox) → 릴레이 → 소비 → 플랫폼 핸들러(GitHub, GitLab 상세) → 리뷰 잡 → 자동화 전략 → 18단계 파이프라인 → 게시([01](01-execution-and-diff.md)).
- finder/verifier Agent Loop, 도구, 고정·동적 문맥, 검증, evals, 샌드박스·E2B·Morph·임베딩 사용 조건([02](02-context-loop-verify.md)).
- 증분 리뷰, 메모리 쓰기·읽기 매트릭스, 규칙 스키마·읽기·승인·동기화·설정 계층, Jira/MCP([03](03-incremental-memory-rules.md)).
- 자격증명·웹훅 검증·큐·복구·테넌트 격리 매트릭스([04](04-saas-and-isolation.md)), 의존성·compose·라이선스 경계([05](05-dependencies.md)), 적용 의견([06](06-fit.md)).
- 조사 방식: 후반부 세부는 병렬 조사 에이전트 4개의 보고(파일을 열어 확인한 줄 번호)를 받았고, 작성자가 핵심 근거 약 20곳을 다시 열어 대조했다(전부 일치). 2026-10-13 정정 작업에서 02~05의 줄 번호를 다시 대조했다(문서별 범위·미대조 범위는 각 문서 머리). 01의 줄 번호는 재대조하지 않았다.

## 2. GUIDE 8절 완료 기준 자체 점검

| 기준 | 상태 | 비고 |
|---|---|---|
| 모든 문서 머리의 SHA가 `repos.lock.tsv`와 같다 | 충족 | 8개 문서 모두 `45676c5f…2842` |
| Q1 호출 흐름 다이어그램이 있고 노드마다 코드 위치가 있다 | 충족(주의) | [00 3절](00-overview.md) mermaid. 일부 노드는 축약 파일명을 쓰고 풀 경로는 01 표에 있음 |
| 고정 문맥 / 동적 탐색 / 재시도 / Agent Loop 구분 | 충족 | [02 3.1](02-context-loop-verify.md#q3) |
| 종료 조건 각각 확인 또는 미확인 표시 | 충족 | [02 4.3](02-context-loop-verify.md#q4). 도구 호출 없음 종료·SDK 내부 동작은 추론(SDK 소스 없음) |
| 검증 단계의 독립성과 추가 파일 접근 여부 | 충족 | [02 5.1](02-context-loop-verify.md#q5) |
| 메모리는 쓰기·읽기 양쪽 추적 | 충족 | [03 7.2](03-incremental-memory-rules.md#q7) |
| 의존성 표에 선언·해석 버전, 선택/필수, 호출 위치, 선언만 있는 패키지 구분 | 대체로 충족 | [05 2절](05-dependencies.md). 일부 `@octokit/plugin-*`는 루트 직접 선언 여부 미확인, 일부 행은 줄 번호 생략 |
| 모든 주장에 검증 수준과 지원 수준 | 부분 충족 | 표 단위로는 검증 수준 표기. **기능 지원 수준은 항목(Q) 단위 요약에 있고 모든 행에 붙이지는 않았다** |
| README·제품 문구와 코드가 다른 곳 기록 | 충족 | [00 7절](00-overview.md) 외 각 문서 |
| 5절 최종 질문에 답 | 충족 | [00 6절](00-overview.md), [06](06-fit.md) |
| 정적 추적과 실행 항목 분리 | 충족 | 전부 정적 추적, 각 문서 머리에 명시 |
| 문서 머리의 검증 수준 요약 숫자 | 재집계 완료 | 2026-10-13 스크립트로 검증 열이 있는 표의 행을 셌다(복수 표기 행 중복 계산, 검증 열 없는 표 제외). 기능 지원 수준 열은 따로 없음 |

## 3. 미확인·미충족 항목 체크리스트

- [ ] Azure Repos / Bitbucket / Forgejo의 이벤트 매핑·file-change 빌더·댓글 게시 본문(이 분석은 GitHub·GitLab 중심)
- [ ] GitHub 기본 diff hunk 컨텍스트 줄 수(Provider API 기본값, 레포 밖 동작)
- [ ] merge base를 명시적으로 계산하는 코드 유무(활성 경로에서 못 찾음, 미확인)
- [ ] `updateSummarizationInPR` 내부, `SuggestionLLMValidator`, `getCloneParams` 본문
- [ ] `@kodus/kodus-graph` 파서 소스(외부 npm 패키지, 이 레포에 없음)
- [ ] 모든 API 컨트롤러의 테넌트 범위(`license`, `integration`, `organization`, `pullRequest` 일부 경로)
- [ ] 로컬 샌드박스 리스를 다른 워커가 공유하는지
- [ ] Mongo 장애가 파이프라인 단계별로 미치는 영향
- [ ] `AddLibraryKodyRulesUseCase` 내부, 규칙 편집 UI, `matchesAnyPath`(trace) 구현, Azure 반응 집계 세부
- [ ] BUSINESS_LOGIC PR 수준 제안이 `prLevelSuggestions`에 저장되어 `previousDecisions`로 돌아오는지
- [ ] 외부 `kodus-installer` 스택의 실제 compose·RabbitMQ 포함 여부(레포 밖, 이 레포의 `.env.schema`·공식 문서가 포함한다고 안내하는 것만 확인, [05 4.1절](05-dependencies.md#rabbitmq-compose)). `docker-compose.sim.yml`은 "Production Build - Simulation" 주석 외 용도 미확인. 같은 문서 4.1절: prod compose 작성 의도(외부 브로커 가정)는 추론
- [ ] `wait:true` 연결 실패 시 worker·webhooks 부팅이 실제로 실패하는지(`@golevelup/nestjs-rabbitmq` 라이브러리 동작, 소스 없음)
- [ ] `integrations`에 동시 요청 시 같은 (org, team, platform) 중복 행이 실제로 생기는지(DB 유일 제약이 없음은 확인, 경쟁 시나리오는 미확인)
- [ ] `store:'memory'`/`max` 옵션을 `@nestjs/cache-manager` 3 + `cache-manager` 7이 실제로 따르는지
- [ ] 재시도 실효값(환경변수 미설정 시 5인지 2인지)은 런타임 미관측
- [ ] 선언-미사용 판정의 동적 require 누락 가능성
- [ ] 줄 번호: 02~05는 2026-10-13에 재대조했으나 문서 머리에 적은 "본문 전체 미독" 긴 범위가 남아 있고 01은 재대조하지 않았다 → 인용 전에 해당 줄을 다시 열 것
- [x] (해소, 2026-10-13) `@license … All rights reserved` 헤더 전수 grep: 18개 소스 파일, `libs/agent-harness`·`libs/llm`·`libs/sandbox`에는 없음([06 3.2절](06-fit.md#license-header))
- [ ] 실행 확인 0건: 이 레포는 실행하지 않았으므로 호출 순서·타이밍은 모두 정적 추적

## 4. 다음에 볼 파일과 함수

1. `libs/code-review/infrastructure/adapters/services/codeReviewHandlerService.service.ts:186-390` (`handlePullRequest` 중간 로직, 크레딧·반응)
2. `libs/platform/infrastructure/adapters/services/azureRepos/*`, `bitbucket/*`, `forgejo.service.ts`의 file-change·게시 함수
3. `libs/code-review/infrastructure/agents/collaborators/batch-runner.ts:86-187`(청크 간 상태 전달 여부)
4. `libs/agent-harness/infrastructure/policies/compression.policy.ts`와 `overflow-recovering-runner.ts`(컨텍스트 압축이 도구 결과 정확도에 미치는 영향)
5. `libs/code-review/infrastructure/agents/engine/agent-tools.factory.ts:1540-1669`(`getCallers`가 call graph 문자열만 보는 이유와 주석 처리된 DB 버전 이력)
6. `libs/kodyRules/infrastructure/adapters/services/kodyRulesSync.service.ts`(동기화 분기 전체)
7. `apps/mcp-manager`의 OAuth 흐름과 `libs/agents/skills/capabilities/task-context/*`(Jira 확장 설계 전 상세 읽기)

## 5. 분석 중 생긴 질문

- 같은 외부 저장소를 두 조직이 연결하면 `WebhookContextService`·`repositories`·AST·GitHub 콘텐츠 캐시에서 실제로 어떻게 섞이는가(동일 repo id 충돌 시나리오를 코드로 더 따라갈 것).
- 재시도 실효값이 5인지 2인지, 파이프라인 오류가 삼켜진 뒤 실제 운영에서 "잡 COMPLETED + 리뷰 없음"이 얼마나 자주 나는지(코드 주석의 사고 이력 참고).
- `KodyFineTuning`을 파이프라인에서 뺀 배경 이슈(#1670 "negative-feedback context")와 재도입 계획이 코드에 있는가.
- `libs/agent-harness`·`libs/llm`·`libs/sandbox`를 AGPL 비-ee 모듈로 재사용할 때 AGPL 의무의 실제 범위(법무 확인). 개별 파일 `@license` 헤더는 이 세 디렉터리에 없음을 확인했고(06 3.2절), 재사용 시 `libs/core`·`libs/common/utils`·`libs/code-review` 파일 2개가 딸려 오는 결합은 [06 3.1절](06-fit.md#reuse-coupling).
- 3개 레포 비교 단계(`comparisons/`)에서 kodus-ai의 "지원 수준" 칸을 채울 때 근거 링크: Q3 지원(조건부), Q4 지원, Q5 부분 지원, Q6 부분 지원, Q7 학습 미지원/규칙형 메모리 부분 지원, Q8 부분 지원, Q9 부분 지원, Q10 부분 지원.

<a id="corrections-2026-10-13"></a>
## 6. 정정 이력(2026-10-13)

무엇을 왜 바꿨는지 한 줄씩. 지적과 실제 코드가 다른 곳은 "지적과 다름"으로 표시했다.

- 04 1.1 `integrations` "(org, team, platform)당 1행": 엔티티·마이그레이션 59개를 열어 DB 유일 제약이 없음을 확정하고 07과 일치시킴(07의 미확인 해소). 지적대로.
- 04 1.2 GitHub 설치 토큰 재발급 "추론": 호출부(`github.service.ts:3170-3183,6502-6527`)를 열어 코드 확인으로 격상. 지적대로.
- 04 1.2 E2B `GIT_AUTH_HEADER`: env 전달은 맞으나 쉘이 풀어 argv에 남는다고 정정(`e2b-sandbox.service.ts:443,462`, `submodule-fetch.ts:523-528` 주석). 지적대로. 07 9절·1.2에 "정정 반영됨" 표시.
- 03 8.1·8.4·범위 요약: 규칙(조직 키, 팀 키 없음)과 설정(`parameters`, 팀 키) 범위 키 표 추가. 지적대로(규칙 쪽 `teamId` 부재를 `IKodyRule`·스키마·리포지토리 검색으로 재확인).
- 00·05·06·04·next RabbitMQ 서술: "필수"만 적던 것을 구성별(앱 요구 / dev·bench 정의 / prod 미정의 / installer 미확인)로 분리해 05 4.1절 신설. 지적대로이나 추가 발견: `API_RABBITMQ_ENABLED=false`이면 앱은 부팅하되 리뷰가 안 돌고, bench compose 주석이 "prod compose has no RabbitMQ"를 스스로 인정, prod가 복사하라는 `.env.example`의 URI 호스트(`rabbitmq-local`)는 prod 네트워크에 없음.
- 06 3.1 비-ee 모듈 재사용 결합 표 신설, 00·05·06 관련 문장 수정: `@libs/ee` 비-spec import 없음은 지적대로. 추가 확인: agent-harness↔llm 순환, `libs/llm`→`crypto.ts`(import 시점 `API_CRYPTO_KEY` 검사), sandbox→`@libs/code-review` 2개 파일(타입 파일과 13줄 유틸), `libs/llm` 테스트 파일은 `@libs/ee`를 import.
- 05 6.1·6.6, 06 3.2 `@license` 헤더: "일부 비-ee 파일"을 전수 grep한 18개 파일 목록으로 정정. 세 모듈에 헤더 없음 확인으로 지적과 같음. 단 경로 규칙상 AGPL인 10개 파일(`libs/code-review` 5, `libs/core` 4, `libs/kodyFineTuning` 1)에는 헤더가 있다.
- 02·03·04·05 줄 번호·서술: 조사 에이전트 4개가 각 문서의 인용을 모두 열어 대조, 어긋난 인용과 서술 오류 약 30건 정정(02: `prompt-builder` 범위, call graph legacy 폴백, E2B 사용처, dedup 예외, `readReference` 설명 / 03: library 복제 근거, `parentSignal` 부정 grep 문구, MEMORY 쓰기 거절 시점, summary/atoms 폐기 조건 등 / 04: Morph·CLI 키·`critical` 근거, 재시도 범위 / 05: Exa·tier 정책 범위·`plugin-enterprise-server` 선언·ee import 수). 문서 머리에 재대조 범위와 못 한 범위를 명시.
- 00~05·07 머리의 검증 수준 요약 숫자: 이전 값(약 70/14/10 등)이 실제 표 행 수와 달라 스크립트 재집계 값으로 교체하고 집계 기준을 명시.
- 07 9절: 04에 반영된 항목에 "정정 반영됨(2026-10-13)" 표시, 07의 `integrations` 유일 제약 미확인 항목을 해소로 변경.
