# 메모리·팀 규칙·Jira 비교 (Q6~Q9 중 Q7·Q8·Q9)

- 작성일: 2026-10-13
- 정정 반영: 2026-10-13 보고서 정정 반영
- 대상 SHA (`../repos.lock.tsv`):
  - pr-agent `330f0813b5fe0d1f54b794077c2d02aa85a1fb63`
  - open-code-review `57273a9ea28548b94b3d67c247ff13a63c01fc47`
  - kodus-ai `45676c5fe7ac016b6206ccea006e459677d92842`
- 기준: 각 레포 `reports/<repo>/03-incremental-memory-rules.md`(Q7·Q8·Q9)를 중심으로 `00`, `04`, `06`, `07`, `next.md`를 대조했다. **근거를 복제하지 않고 해당 절로 링크**한다. 점수·순위는 매기지 않는다.
- 약어: **PA** = pr-agent, **OC** = open-code-review, **KO** = kodus-ai. 링크 텍스트의 `03 7.2`는 그 레포 `03` 문서의 7.2절이다.
- 지원 수준은 GUIDE 3.3절 기준(지원 / 부분 지원 / 미지원 / 미확인). 세 레포 모두 **정적 추적만** 했고 실행 확인은 0건이다. 이 문서에서 직접 다시 연 코드는 5절에 따로 적었다.
- 이 문서의 1~3절은 보고서 근거를 정리한 비교이고, **4절만 분석자 의견**이다.

---

## 1. 메모리 쓰기·읽기 경로 비교 (Q7)

GUIDE 3.3절 규칙에 따라 **쓰기만 있고 조회가 없으면 "피드백 학습"이라 부르지 않는다.** 아래는 그 구분을 층위별로 적은 것이다.

### 1.1 층위별 한눈 비교

| 층위 | PA | OC | KO |
|---|---|---|---|
| 실행 대화 / 체크포인트 | 무상태 `[system, user]` 2메시지. 실행 안에서만 청크 결과 캐시. **지원(실행 내 한정)** [PA 03 7.1](../reports/pr-agent/03-incremental-memory-rules.md#q7) | 파일 하위 작업의 지역 `messages`, 실행 내 압축 요약(`MEMORY_COMPRESSION_TASK`, 영속 아님). 재개 없음. **지원(실행 내 한정)** [OC 03 7.1](../reports/open-code-review/03-incremental-memory-rules.md#q7) | 파이프라인 체크포인트 없음(`saveState/loadState` 호출처 없음). **미지원** [KO 03 6.2](../reports/kodus-ai/03-incremental-memory-rules.md#q6) |
| **같은 PR 이력** | **지원.** 리뷰 댓글에 숨긴 finding 상태, 사람이 resolve한 스레드 읽기, 인라인 fingerprint 마커, (GitLab·Azure) 이전 `/improve` 제안 스레드 [PA 03 7.1~7.4](../reports/pr-agent/03-incremental-memory-rules.md#q7) | **미지원.** 이전 리뷰·코멘트를 조회하지 않음 [OC 03 Q6](../reports/open-code-review/03-incremental-memory-rules.md#q6) | **지원.** Mongo `pullRequests.files.suggestions`를 `PrDecisionStoreService.load`로 읽어 프롬프트에 주입(같은 PR만) [KO 03 7.2](../reports/kodus-ai/03-incremental-memory-rules.md#q7), [6.4](../reports/kodus-ai/03-incremental-memory-rules.md#q6) |
| **PR 간 영속 메모리** | **미지원.** 찾아본 곳: DB·큐·파일 키워드 검색, `push_outputs`, `/improve` 스레드 읽기 [PA 03 7.5](../reports/pr-agent/03-incremental-memory-rules.md#q7) | **미지원.** 세션 JSONL은 기록용이며 읽는 쪽은 `ocr viewer`뿐 [OC 03 7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) | **부분 지원.** `type: MEMORY` 규칙(수동·MCP·채팅·사람 PR 댓글 생성)은 쓰기·읽기 모두 있다. 다만 **Kody 댓글에 대한 반응·답글에서 파생된 것이 아니다** [KO 03 7.4~7.5](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| **피드백 학습** (반응·답글·resolve → 다음 PR 조회) | **미지원** [PA 03 7.5](../reports/pr-agent/03-incremental-memory-rules.md#q7) | **미지원** [OC 03 7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) | **미지원.** 반응 수집(쓰기)과 임베딩·k-means 필터(읽기 로직) 코드는 있으나 읽기 진입점 `KodyFineTuningStage`가 `configureStages()`에 없다. 공식 문서도 "not currently active"라고 적는다 [KO 03 7.1, 7.3, 7.7](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| **유사 이슈 검색** (팀 메모리와 별개) | `similar_issue`: GitHub 이슈·댓글을 임베딩해 벡터 DB에 넣고 **이슈 URL**을 입력으로 검색. PR 메모리가 아님. 선택 설치 그룹. **부분 지원** [PA 03 7.6](../reports/pr-agent/03-incremental-memory-rules.md#q7) | 없음 [OC 03 7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) | 03에서 다루지 않음(**미확인**). `suggestion_embedded` 임베딩은 파인튜닝용이고 비활성 [KO 03 7.2](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |

### 1.2 레포별 쓰기 이벤트 · 저장소 · 읽기 함수 · 검색 방식 · 수명 관리

"조회 없음" 열이 **예**이면 기록만 있고 다음 리뷰에서 읽는 코드가 확인되지 않은 것이다.

| 레포 | 종류 | 쓰기 이벤트 | 저장소 | 읽기 함수·위치 | 검색 방식 | 수명 관리 | 기록만 있고 조회 없음? |
|---|---|---|---|---|---|---|---|
| PA | 같은 PR finding 상태 | **전체 리뷰 실행이 끝날 때마다**(증분 제외). 댓글 답변·승인·수정 이벤트 저장은 없음 | 리뷰 댓글 본문 끝의 숨은 HTML 주석 `pr-agent-review-state:v1` (별도 저장소 없음) | `_load_previous_findings_context()` → `render_previous_findings` → **최초 user 프롬프트에 JSON 주입**(호출 도구 아님) `pr_reviewer.py:224,681-694` | 없음(그 댓글 전체). 글자 예산 8000에 맞춰 ACTIVE → dismissed → RESOLVED 순 | ACTIVE/RESOLVED, 재발 시 reopened, RESOLVED 최근 20개만 보존. **신뢰도·승인·충돌 필드 없음** | 아니오 [PA 03 7.2~7.3](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| PA | 사람이 resolve한 스레드("dismissed") | 별도 쓰기 없음(사람의 resolve가 곧 신호) | 저장 안 함, 매 실행 provider에서 재조회 | `pr_reviewer.py:696-717`, `github_provider.py:1096-1141` | 마지막 텍스트 답글 750자 이내를 함께 주입 | 없음 | 아니오 [PA 03 7.4](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| PA | `push_outputs` (JSONL·웹훅·Slack) | 리뷰 결과 | 파일·외부 | **읽는 코드 없음** | - | - | **예** [PA 03 7.5](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| OC | 세션 JSONL | 모든 LLM 요청(diff·도구가 읽은 소스 포함)·응답·도구 호출 | `~/.opencodereview/sessions/<repo>/<UUID>.jsonl` (끌 수 없음) | 읽는 곳은 `internal/viewer/store.go`(읽기 전용 WebUI)뿐. `internal/agent`는 import하지 않음 | - | 삭제·만료 코드 없음 | **예** [OC 03 7.2~7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) |
| OC | 사용자 반응(답변·resolve·수정) | **수집 입력 경로 자체가 없음** | - | - | - | - | 해당 없음 [OC 03 7.2](../reports/open-code-review/03-incremental-memory-rules.md#q7) |
| KO | 같은 PR 이력(`PrDecisionStore`) | 리뷰 파이프라인이 제안 저장, `synchronize`마다 `CHECK_SUGGESTION_IMPLEMENTATION` 잡이 `implementationStatus` 갱신 | Mongo `pullRequests.files.suggestions` | `PrDecisionStoreService.load` (org + `repository.fullName` + PR 번호, 최근 40건) → `<PreviousReviewDecisions>` | 같은 PR만. 키워드·벡터 없음 | 구현됨 상태. PR 간 전파 없음 | 아니오 [KO 03 7.2, 6.4](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | `type: MEMORY` 규칙 | UI/API, MCP `KODUS_CREATE_MEMORY`, PR 댓글 채팅 에이전트(개발자 지시 문장 인용 필수), 사람 댓글 기반 cron 생성. 생성형 출처는 LLM "memory curator"가 create/skip/update 판정 | Mongo `kodyRules`(조직당 문서 1개의 `rules` 배열) | `CodeBaseConfigService.getConfig`가 리뷰마다 **조직 단위**로 읽음 → bug/security/performance/generalist **시스템 프롬프트**의 "Memory Rules (Team Conventions)" | **필터·검색 없음.** `title`·`rule` 평면 목록 | `status`(active/paused/pending/rejected/deleted…), 소프트 삭제, 승인 게이트(기본 꺼짐). **버전 이력·만료 없음** | 아니오 [KO 03 7.2, 7.4, 7.5, 8.3](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | 사람 PR 댓글 → 규칙 자동 생성 | cron(`KodyLearningCronProvider`): 첫 실행 3개월 백필, 이후 주간 델타. 봇·**Kody 자신의 댓글**·100자 이하 제외 | 위와 같은 `kodyRules`, `origin: PAST_REVIEWS`, 승인 게이트가 켜지면 `PENDING` | 일반 규칙과 동일(8절 읽기 경로) | - | LLM 필터 → 생성 → 기존 규칙 대비 dedup → 품질 필터 | 아니오 [KO 03 7.4](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | `codeReviewFeedback`(👍/👎 카운터) | cron → RabbitMQ consumer → `SaveCodeReviewFeedbackUseCase`(바뀐 카운트만) | Mongo | `KodyFineTuningService`(**파이프라인 미연결**), 이슈 상세 UI, 분석 적재 | - | 수명 관리 없음 | **예(리뷰 경로 기준)** [KO 03 7.2~7.3](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | `suggestion_embedded` (pgvector 컬럼) | `KodyFineTuningService.syncronizeSuggestions`(`startAnalysis` 경유만) | PG | 같은 서비스의 JS 코사인 + k-means. `<=>` 연산자 쿼리 없음 | 클러스터 유사도 | 없음 | **예(호출되지 않음)** [KO 03 7.3](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | `analytics.suggestion_feedback` [ee], `ruleLikes`, Kody Issues | 분석 적재 / UI 좋아요 / PR 닫힘 시 | PG / Mongo | 대시보드·UI·MCP 도구. 리뷰 입력 아님 | - | `ruleLikes`는 조직 필드 없음(테넌트 간 전역) | 리뷰 경로 기준 **예** [KO 03 7.2](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |
| KO | 고객 저장소 브랜치 `kodus/trace/v1`의 JSON | `apps/cli` trace | 고객 Git | `LoadExternalContextStage.loadTraceDecisions`, **알파 플래그 뒤, fail-closed** | 경로 기준 | - | 아니오(알파) [KO 03 7.2](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |

### 1.3 읽기 방식: 최초 입력 주입 vs 호출 가능한 도구

| 레포 | 방식 | 근거 |
|---|---|---|
| PA | **최초 user 프롬프트 주입**만. 도구 없음(Agent Loop가 없음) | [PA 03 7.2](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| OC | 해당 없음. 과거 지식을 모델에 주는 경로가 둘 다 없다. 사용자가 `--background`·`rule.json`에 **수동으로** 적은 텍스트가 정적 입력이 될 뿐 | [OC 03 7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) |
| KO | **시스템 프롬프트 주입**(MEMORY 규칙), **유저 프롬프트 주입**(`PreviousReviewDecisions`). 리뷰 에이전트가 메모리를 도구로 조회하는 경로는 03에서 확인되지 않았다(채팅 에이전트 쪽은 쓰기 도구 위주, 읽기 도구 여부는 미확인) | [KO 03 7.2, 7.5](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |

### 1.4 동의·해결을 신호로 해석하는 위험 (Q7 "무응답·resolve·수정을 동의로 간주")

| 레포 | 해석 | 보정 | 검증 | 근거 |
|---|---|---|---|---|
| PA | 이번 리뷰에서 **finding이 안 나왔다는 부재**를 "고쳐졌다(RESOLVED)"로 해석 | 증분·누락 청크·토큰 제외 파일·파싱 불가·**finding 포화(`num_max_findings` 이상)**이면 해결 금지. 모델 비결정성은 남음 | 추론(부재 기반 판정이라는 점) | [PA 03 7.3](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| PA | 사람이 resolve한 스레드를 "수정 없이 닫음(dismissed)"으로 전달. **코드가 실제로 수정됐는지는 구분하지 않음** | 없음 | 추론 | [PA 03 7.4](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| PA | 같은 finding 동일성은 **모델이 문구를 글자 그대로 복사**해야 유지(fingerprint는 경로+정규화 본문, 줄 번호 미포함) | 문구가 바뀌면 새 finding | 코드 확인 | [PA 03 7.2](../reports/pr-agent/03-incremental-memory-rules.md#q7) |
| OC | 해당 없음(해석할 입력이 없음) | - | 코드 확인 | [OC 03 7.3](../reports/open-code-review/03-incremental-memory-rules.md#q7) |
| KO | 무응답·resolve·수정을 동의로 해석하는 코드 없음. 무응답은 `pending`이며 프롬프트가 "NOT evidence the developer rejected this"라고 명시. `implementationStatus`는 같은 PR 안에서만 "이미 적용됨". 답글·resolve·댓글 수정은 **피드백으로 저장하지 않음**("reject/explanation signal is deferred, issue #1670") | 해당 신호 자체를 수집하지 않음 | 코드 확인 | [KO 03 7.3, 7.6](../reports/kodus-ai/03-incremental-memory-rules.md#q7) |

---

## 2. 팀 규칙 비교 (Q8)

### 2.1 범위 계층 · 소유자 · 우선순위

| 항목 | PA | OC | KO |
|---|---|---|---|
| 범위 계층 | 전역(호스트 설정·환경변수) → `extra_config_url` → 조직 `global_settings_repo` → 저장소 `.pr_agent.toml` → 경로별(모노레포, 옵트인, 최대 20개) → 명령 인자. 명령별 `extra_instructions` [PA 03 8.1](../reports/pr-agent/03-incremental-memory-rules.md#q8) | ① `--rule` ② `<repo>/.opencodereview/rule.json` ③ `~/.opencodereview/rule.json` ④ 바이너리 내장. **조직·팀·명령별 없음** [OC 03 8.1](../reports/open-code-review/03-incremental-memory-rules.md#q8) | 규칙: **전역(`repositoryId='global'`) → 저장소 → 디렉터리 그룹**, 그 안에서 `path` glob·`scope`(file/pull-request). 설정(`parameters`)은 별도로 `deepMerge(DEFAULT, global, repo, repoFile, directory, directoryFile)` [KO 03 8.1, 8.4](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |
| **팀 단위 범위** | 없음(조직/네임스페이스까지) | 없음 | **규칙은 조직 단위**(규칙에 `teamId` 없음, `findByOrganizationId`로 조직 전체를 읽음). 설정(`parameters`)만 팀 키. 둘을 혼동하지 않도록 주의(객체별 범위 키 표: [KO 03 8.1 표](../reports/kodus-ai/03-incremental-memory-rules.md#q8-scope)) [KO 03 8.1~8.2, 8.4](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |
| 소유자 | 운영자 / 조직 관리자 / 저장소 팀 / 하위 디렉터리 팀 / 사용자 | 호출자 / 저장소 사용자 / 로컬 사용자 / 프로젝트 | 조직(Mongo 문서). 생성은 UI·API·MCP·동기화·cron |
| 우선순위·충돌 | 키 단위 덮어쓰기(섹션 병합, 리스트·딕셔너리는 교체), 환경변수는 파일 설정 뒤 다시 적용해 최상위. **자연어 규칙끼리의 의미 충돌 해결 없음** [PA 03 8.2](../reports/pr-agent/03-incremental-memory-rules.md#q8) | **첫 번째로 일치한 계층의 규칙 텍스트 하나만** 사용, 계층 간 병합 없음. `include/exclude`도 가장 높은 계층 하나만 [OC 03 8.2](../reports/open-code-review/03-incremental-memory-rules.md#q8) | **우선순위·충돌 해결 없음.** ACTIVE 규칙을 모아 동일 `rule` 텍스트만 제거, `createdAt` 오름차순, 무료 플랜이면 최대 10개 [KO 03 8.2](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |
| 경로별 적용을 누가 하나 | **모델.** 코드가 경로 매칭으로 규칙을 고르지 않고 스킬 설명을 보고 모델이 선택 | **코드.** glob(`doublestar` + 중괄호 전개, 소문자 비교) 첫 일치 | **코드.** `path`·`fileScope`로 거르고 표준 규칙은 파일당 judge 1회. 단 디렉터리 규칙이 PR 전체에 누수될 가능성(추론) [KO 03 8.2](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |

### 2.2 생성 · 승인 · 버전 · 비활성화 · 추출

| 항목 | PA | OC | KO |
|---|---|---|---|
| 생성·편집 | git에 커밋된 설정 파일을 편집(전용 경로 없음) | JSON 파일 직접 편집. `ocr rules check`는 조회만 | `POST /kody-rules/create-or-update`(`TenantScopeGuard` + `PolicyGuard`), MCP, 저장소 파일 동기화, 라이브러리 808개 복제. UI는 이 분석 범위 밖(**미확인**) |
| 승인 | 그 저장소의 PR 리뷰 프로세스(추론: 별도 승인 코드를 찾지 못함) | 없음(Git이 대신할 뿐) | `kodyKnowledgeApproval.enabled`(**기본 false**)이면 생성형 출처·`repo_file_sync`가 `PENDING`, `/pending/apply`·`/discard` |
| 버전 관리 | 설정 파일의 git 이력 | 없음 | **규칙 버전 이력 없음.** 제자리 수정, 텍스트 변경 시 파생 `summary`·`atoms` 폐기. 감사 로그 이벤트만 있음 |
| 비활성화 | `use_repo_settings_file=false` 같은 설정 키 | `exclude` 패턴(파일 제외만, 규칙 단위 on/off 없음) | 소프트 삭제(DELETED), 일시중지(PAUSED)·재개 |
| 개발자 피드백에서 규칙 **추출** | **미지원** | **미지원** | **부분 지원**: 사람 PR 댓글 → 규칙(LLM 필터→생성→dedup→품질 필터, Kody 자기 댓글 제외). Kody 댓글에 대한 반응·답글에서의 추출은 없음 |
| 저장소 파일 동기화 | `repo_context_files`(기본 `AGENTS.md`, **기본 브랜치**에서 읽음) | 저장소 `rule.json`을 **PR head 작업 트리**에서 읽음 | `.kody/rules/**`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` 등. **병합된 PR**에서만 동기화(`ideRulesSyncEnabled` 기본 false) |
| 근거 | [PA 03 8.2~8.3](../reports/pr-agent/03-incremental-memory-rules.md#q8) | [OC 03 8.3](../reports/open-code-review/03-incremental-memory-rules.md#q8) | [KO 03 8.3, 7.4](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |

### 2.3 프롬프트 주입 위치와 분류

| 항목 | PA | OC | KO |
|---|---|---|---|
| 커스텀 프롬프트 | `extra_instructions` → system 메시지 `Extra instructions from the user:` | `--background`와 규칙은 서로 다른 슬롯(충돌 없음) | `v2PromptOverrides`(Postgres 설정, 승인 흐름 없음) |
| 규칙·지침 파일 | system 메시지 `Repository context:`(`<instruction_files>`, 줄 수 예산) / 스킬은 system 맨 앞 | **user** 메시지 `### Review Checklist` 아래 `{{system_rule}}`(Main·Plan, system 아님) | 표준 규칙: judge의 user 프롬프트 `<Rules>`(번호 `[n] title`). MEMORY: 비규칙 에이전트 **system** 프롬프트 |
| 저장·승인·버전 관리되는 팀 규칙 | **미지원** | **미지원** | **부분 지원**(저장·승인 게이트·감사 있음, 버전 이력 없음, 핵심 구현이 `libs/ee/`) |
| 자동화된 정책 엔진 | **미지원** (`ignore_*`는 리뷰 실행 여부만 결정) | **미지원** | **미지원** (정규식 detector도 후보를 LLM judge로 보낼 뿐) |
| 분류 | 커스텀 프롬프트 + 지침 파일 | 커스텀 프롬프트 파일 | 커스텀 프롬프트 + 저장·승인형 규칙 |
| 근거 | [PA 03 8.3](../reports/pr-agent/03-incremental-memory-rules.md#q8) | [OC 03 8.4](../reports/open-code-review/03-incremental-memory-rules.md#q8) | [KO 03 8.2~8.3](../reports/kodus-ai/03-incremental-memory-rules.md#q8) |

### 2.4 신뢰 경계 (규칙을 어디서 읽는가)

- PA: 저장소 설정이 바꿀 수 없는 키(LLM·Git·Jira 연결 정보 등)를 코드가 걸러낸다. 단 방어는 **금지 목록 + 키 이름 접미사 휴리스틱**이다 [PA 07 5.3](../reports/pr-agent/07-credentials.md).
- OC: 규칙을 **리뷰 대상 PR의 작업 트리**에서 읽는다. 예제 워크플로가 `pull_request_target`로 PR head를 체크아웃하므로 포크 PR이 자기 `rule.json`(프롬프트 주입 가능 텍스트)을 넣을 수 있다. 코드 확인 + 영향은 추론 [OC 03 8.4](../reports/open-code-review/03-incremental-memory-rules.md#q8).
- KO: 저장소 `kodus-config.yml`은 `kodusConfigFileOverridesWebPreferences`가 `true`일 때만(기본 `false`), **기본 브랜치**에서 읽고 기본값에 없는 키는 제거한다 [KO 03 8.4](../reports/kodus-ai/03-incremental-memory-rules.md#q8).

---

## 3. Jira / 요구사항 (Q9): 텍스트 주입 vs 조건별 근거 판정

GUIDE Q9의 구분을 세 단계로 나누어 표시한다.

- **(A) 텍스트 주입**: 요구사항 텍스트를 모델 입력에 넣는다.
- **(B) 조건별 판정**: 모델이 각 조건을 충족/미충족으로 분류한다. 단 **근거가 입력 diff뿐**이다.
- **(C) 조건별 근거 탐색**: 조건마다 **저장소의 코드를 찾아 읽어** 구현 근거를 확보하고 판정한다.

| 항목 | PA | OC | KO |
|---|---|---|---|
| Jira 연동 자체 | **있음, Jira Cloud 전용**(`atlassian-python-api`, `bitbucket` extra) | **없음**(레포 전체 검색 결과 없음) | **직접 어댑터 없음.** 관리형 MCP(Atlassian Rovo 등)를 경유 |
| 이슈 식별 | PR 제목+설명+브랜치명에서 `[A-Z]{2,10}-\d{1,7}`. `jira.project_keys` 허용 목록(비면 모든 키 조회), 시도 최대 10·성공 최대 5 | 없음 | 본문·제목·브랜치에서 `/[A-Za-z][A-Za-z0-9_]+-\d+/g`(오탐 가능), `#N`, `/issues/N`, 연결된 MCP 도메인 URL |
| 인증 | 호스트 설정 `jira_site`+email+API token. 저장소 `.pr_agent.toml`로 변경 불가 | 없음 | OAuth 또는 API 토큰, `mcp-manager`에 암호화 저장, **조직 단위**(팀 단위 아님) |
| 필드 추출 | `summary`, `description`, `labels`, 커스텀 요구사항 필드(각 1만 자 상한). 하위 작업·이미지 없음 | 없음 | `description`, `acceptanceCriteria`, `criteria`, `requirements`, ADF 정규화. **실행당 티켓 1건** |
| **(A) 텍스트 주입 위치** | user 메시지 `--PR Ticket Info--`(티켓 단위로 예산에 맞춰 절단) | Plan·Main user 메시지 `### Requirement Background (Optional)`. 값은 `--background` 문자열 1개(`--commit`이면 커밋 메시지) | **메인 리뷰 입력에는 들어가지 않음.** finder에는 PR 제목과 본문 앞 500자만. 티켓은 별도 Business Logic 단계의 입력 |
| **(B) 조건별 판정** | **부분 지원.** 모델이 요구사항을 bullet로 풀고 `fully_compliant` / `not_compliant` / `requires_further_human_verification`로 분류. 청크 분할 시 합집합으로 "부분 준수" 표시 | **미지원.** 요구사항 충족 판정 지시·결과 필드 없음 | **부분 지원.** 번호 매긴 `ACCEPTANCE_CRITERIA`를 PR diff와 대조해 IMPLEMENTED/MISSING/PARTIAL. 티켓 원문 인용이 없으면 finding 무효. 기준 품질(EMPTY~COMPLETE)이 약하면 LLM 호출 전 중단 |
| **(C) 조건별 근거 탐색** | **미지원** (탐색 수단 없음) | **미지원** | **미지원.** 분석기는 `tools: InMemoryToolRegistry([])`, `maxSteps: 1`이고 "전체 코드베이스가 아니라 diff만 본다"고 명시. diff에 없으면 "누락"이 됨. 선택적 `BusinessRulesVerifier`(기본 꺼짐)가 갭 주장을 반증 |
| 이번 PR 범위 vs 이슈 전체 범위 | **미지원.** 프롬프트가 "모든 요구사항·하위 작업·DoD·AC를 다시 적어라"고 지시 | **미지원** | **미지원.** 모든 기준을 PR diff와 대조 |
| 실행 조건·실패 시 | `/review`(`require_ticket_analysis_review=true` 기본), `/describe`. 조회 실패 시 그 티켓만 건너뛰고 리뷰 계속 | - | `business_logic` 옵션(기본 true) + task-management MCP 연결 + 티켓 키·링크 + **PR당 1회**. 문서의 "every PR review"와 코드 조건이 다르다. 샌드박스 **이전** 단계라 저장소 접근 없음 |
| 지원 수준(요약) | 부분 지원 | **미지원**(입력 슬롯만 부분) | 부분 지원 |
| 근거 | [PA 03 9.1~9.2](../reports/pr-agent/03-incremental-memory-rules.md#q9) | [OC 03 Q9](../reports/open-code-review/03-incremental-memory-rules.md#q9) | [KO 03 9.1~9.4](../reports/kodus-ai/03-incremental-memory-rules.md#q9) |

**요약**: 세 레포 모두 **(C) 조건별 근거 탐색과 "이번 PR 범위" 구분은 없다.** (B)는 PA(리뷰 응답의 한 필드)와 KO(전용 단계, 결과는 PR 수준 제안)에 있고, OC는 (A)의 입력 슬롯만 있다. 각 보고서가 제안한 확장 지점은 [PA 03 9.3](../reports/pr-agent/03-incremental-memory-rules.md#q9), [OC 03 Q9 확장 지점](../reports/open-code-review/03-incremental-memory-rules.md#q9), [KO 03 9.3](../reports/kodus-ai/03-incremental-memory-rules.md#q9)에 있다(모두 의견).

---

## 4. 의견: 우리 서비스(팀별 규칙 · PR 간 피드백 메모리 · Jira AC 대조)에 쓸 설계 요소와 빈 부분

**이 절은 분석자 의견이다.** 코드 근거는 1~3절의 링크를 따른다. 라이선스는 [GUIDE 2.1절](../GUIDE.md) 표 기준(PA MIT, OC Apache-2.0, KO는 Community/Enterprise 분리)이고 법률 자문이 아니다. KO의 규칙 서비스·설정 로더 핵심은 `libs/ee/`(상용)라서 **스키마·흐름 아이디어만 참고**하는 쪽이 안전하다([KO 06](../reports/kodus-ai/06-fit.md)).

### 4.1 팀별 규칙

| 쓸 수 있는 설계 요소 | 출처 | 비고 |
|---|---|---|
| 규칙 레코드 필드: 범위(저장소·디렉터리 그룹·`path` glob·`scope`), 출처(`origin`), 상태(`status`), 예시(`examples`) | KO `IKodyRule` [KO 03 8.1](../reports/kodus-ai/03-incremental-memory-rules.md#q8) | 스키마 아이디어. 구현은 ee |
| 생성형 출처는 `PENDING`으로 시작하고 사람이 apply/discard | KO 승인 게이트 [KO 03 8.3](../reports/kodus-ai/03-incremental-memory-rules.md#q8) | KO는 기본값이 꺼짐. 우리는 기본 켜는 쪽을 검토 |
| 사람 댓글 → 규칙 생성 파이프라인(필터 → 생성 → dedup → 품질 필터, 자기 댓글 제외로 루프 방지) | KO [KO 03 7.4](../reports/kodus-ai/03-incremental-memory-rules.md#q7) | 아이디어 참고 |
| 규칙 주입 이음새(`Resolver` 인터페이스를 서비스 저장소 구현으로 교체) | OC [OC 06](../reports/open-code-review/06-fit.md) | 코드 재사용 후보(Apache-2.0) |
| 경로 glob 첫 일치 + 소문자 비교 | OC [OC 03 8.1~8.2](../reports/open-code-review/03-incremental-memory-rules.md#q8) | 단순함. 병합 정책은 새로 정해야 함 |
| 기본 브랜치에서만 읽기, 호스트 전용 키는 저장소 설정으로 변경 불가 | PA [PA 03 8.1](../reports/pr-agent/03-incremental-memory-rules.md#q8), [PA 07 5.3](../reports/pr-agent/07-credentials.md) | 허용 목록 방식으로 더 엄격하게 |
| 규칙·지침을 system 메시지의 별도 블록으로 주입 | PA, KO | OC는 user 메시지 |

**세 레포 어디에도 없어서 직접 설계해야 하는 부분**

- **팀 범위**: KO도 규칙은 조직 단위다. 팀 A 규칙이 팀 B 리뷰에 섞이지 않도록 읽기 쿼리에 팀 필터를 강제해야 한다.
- **우선순위·충돌 해결**: PA는 키 덮어쓰기, OC는 첫 일치 하나, KO는 없음. 자연어 규칙 간 충돌은 세 레포 모두 미해결이다.
- **버전 이력·롤백**: KO도 제자리 수정이다.
- **코드 레벨 경로 선별**: PA는 모델에 위임한다. KO·OC의 방식을 합쳐 선별 결과를 로그로 남기는 편이 검증하기 쉽다.
- **규칙 효과 측정**(적용 횟수, 지적 수락률): 세 레포 모두 확인되지 않았다(미확인).

### 4.2 PR 간 피드백 메모리

| 쓸 수 있는 설계 요소 | 출처 | 비고 |
|---|---|---|
| 같은 PR 상태 머신(ACTIVE/RESOLVED/재발, 보존 상한)과 부분 커버리지·포화 시 해결 금지 보정 | PA `review_finding_state.py` [PA 03 7.2~7.3](../reports/pr-agent/03-incremental-memory-rules.md#q7), [PA 06](../reports/pr-agent/06-fit.md) | 순수 함수라 이식 쉬움(MIT). PR 간 메모리는 이 위에 새로 쌓는 구조 |
| 사람이 resolve한 스레드를 신호로 읽기(+마지막 답글) | PA [PA 03 7.4](../reports/pr-agent/03-incremental-memory-rules.md#q7) | "수정 후 resolve"와 구분하는 로직을 추가해야 함 |
| 메모리 쓰기 게이트(개발자 지시 문장을 그대로 인용해야 도구가 열림), LLM "memory curator"의 create/skip/update | KO [KO 03 7.5](../reports/kodus-ai/03-incremental-memory-rules.md#q7) | 아이디어 참고 |
| 무응답은 약한 신호라는 프롬프트 문구, 자기 댓글 제외 | KO [KO 03 7.3~7.4](../reports/kodus-ai/03-incremental-memory-rules.md#q7) | 동의 해석 보정의 출발점 |
| 반응 카운터 스키마 `{suggestionId, reactions, comment, pullRequest}` | KO `codeReviewFeedback` | 스키마만 참고. 읽기 쪽은 KO에도 없음 |
| 두 가지 읽기 경로(최초 입력 슬롯 + 조회 도구) | OC 제안 [OC 06](../reports/open-code-review/06-fit.md), PA 제안 [PA 06 5.3](../reports/pr-agent/06-fit.md) | 모두 의견 단계. 구현 레포 없음 |

**비어 있는 부분**

- **쓰기 이벤트 수집**: 답글·반박·resolve·수정 커밋을 저장하는 코드가 세 레포 모두 없다(KO는 "deferred, issue #1670"). 우리가 처음부터 만든다.
- **읽기 함수와 검색**: 팀·저장소·경로·심볼 필터를 **쿼리 계층에서 강제**하는 조회. KO의 MEMORY는 필터 없는 평면 목록이다.
- **수명 관리**: 신뢰도, 만료, 충돌, 과거 결정 무효화는 세 레포 모두 없다(PA는 RESOLVED 20개 상한이 전부).
- **동의 해석 보정**: "부재 = 해결"(PA) 같은 해석을 코드 비교(해당 줄이 실제로 바뀌었는가)로 대체하는 설계가 필요하다.
- **사람 승인 흐름**: 증류된 메모리를 `proposed → approved`로 올리는 경로. KO 규칙 승인 게이트가 유일한 참고 사례이고 기본값은 꺼져 있다.

### 4.3 Jira AC 대조

| 쓸 수 있는 설계 요소 | 출처 | 비고 |
|---|---|---|
| 이슈 키 추출 + 프로젝트 키 허용 목록 + 조회 상한 + 호스트 전용 인증 | PA `ticket_pr_compliance_check.py` [PA 03 9.1](../reports/pr-agent/03-incremental-memory-rules.md#q9) | 재사용 가능(MIT). 키 허용 목록은 KO의 광범위한 정규식 오탐 보완책 |
| 수락 기준을 `acceptanceCriteria[]`로 정규화하는 capability, 기준 품질 분류, 원문 인용 강제, "각 기준을 IMPLEMENTED/MISSING/PARTIAL로 판정" 프롬프트 | KO [KO 03 9.1~9.2](../reports/kodus-ai/03-incremental-memory-rules.md#q9) | 아이디어 참고 |
| 외부 문맥 로드 단계의 알파 게이트·fail-open 패턴 | KO `LoadExternalContextStage` [KO 03 9.3](../reports/kodus-ai/03-incremental-memory-rules.md#q9) | 메인 리뷰 입력에 요구사항을 주입할 때의 형태 |
| 청크 판정을 합집합으로 합쳐 "부분 준수" 표시 | PA `review_merge.py` [PA 03 9.2](../reports/pr-agent/03-incremental-memory-rules.md#q9) | 대형 PR 처리 |
| 조건별 별도 Agent Loop + `verdict{id, status, evidence[{path, 줄}]}` | OC 확장 제안 [OC 03 Q9 확장 지점](../reports/open-code-review/03-incremental-memory-rules.md#q9), KO 제안 [KO 03 9.3](../reports/kodus-ai/03-incremental-memory-rules.md#q9) | **두 보고서의 설계 제안일 뿐 구현 사례는 없다** |

**비어 있는 부분**

- **(C) 조건별 근거 탐색**: 세 레포 모두 없다. KO는 샌드박스를 만들기 **전에** Business Logic 단계가 돌고 분석기가 도구 없는 LLM 1회이므로, 단계 순서부터 바꿔야 한다([KO 03 9.2~9.3](../reports/kodus-ai/03-incremental-memory-rules.md#q9)).
- **이번 PR 범위 구분**: 세 레포 모두 없다. 위 (C) 앞에 "이 diff가 다루는 조건만 선별"하는 단계를 둬야 한다는 제안은 PA·OC·KO 보고서가 같다.
- **구조화된 AC 저장과 재사용**: PA는 매번 재조회, KO는 PR당 1회 판정이고 결과는 마크다운 키워드 매칭으로 분류한다.
- **팀별 Jira 연결**: PA는 호스트 설정 1벌, KO는 MCP 연결이 조직 단위다. 팀마다 다른 Jira 사이트·토큰이 필요하면 직접 설계한다(토큰 처리는 [credentials.md](credentials.md)).
- **리뷰 결과와의 통합**: KO의 결과는 PR 수준 제안으로 따로 게시된다(메인 finding과 분리). PA는 리뷰 응답의 한 필드다.

---

## 5. 보고서 간 모순과 검증 약점

### 5.1 보고서 간 모순·불일치

| # | 내용 | 위치 | 상태 |
|---|---|---|---|
| 1 | **OC `content_logging`**: 03은 한때 "켜면 프롬프트·응답을 이벤트에 싣는 옵션이 있다"고 적었으나 **정정 완료**: 03 7.4가 07과 같이 `ContentLogging()`을 호출하는 곳이 없어 **이 SHA에서는 효과 없는 설정**이라고 적는다. 이 문서 작성 중 `repos/open-code-review`에서 `ContentLogging` 참조를 직접 검색해 정의만 있고 호출처가 없음을 확인했다(`internal/telemetry/provider.go:70`) | [OC 03 7.4](../reports/open-code-review/03-incremental-memory-rules.md#q7), [OC 07 Q13-4 4.3](../reports/open-code-review/07-credentials.md) | 정정 완료(03 7.4가 07과 일치) |
| 2 | **OC 도구 개수**: **정정 완료.** 기준은 [OC 00 1절](../reports/open-code-review/00-overview.md)(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개, Provider 등록 5개, `task_done`은 직접 처리). 이 문서 5.3절의 직접 확인(`definitions.go` 항목 7개, `Unknown` 포함)과 일치 | OC 00 1절 | 정정 완료 |
| 3 | **PA "요청마다 새 provider"**: 04는 한때 요청마다 새 클라이언트를 만든다고 적었으나 07은 도구가 `get_git_provider()(pr_url)`로 추가 인스턴스를 만든다며 단정할 수 없다고 정정한다. **04 정정 반영됨(2026-10-13)**: Q10-1 토큰 수명 행과 Q10-3 provider 인스턴스 행을 07 3.2절에 맞춤 | [PA 04 Q10-1](../reports/pr-agent/04-saas-and-isolation.md), [PA 07 3.2](../reports/pr-agent/07-credentials.md) | 정정 완료 |
| 4 | **KO "(org, team, platform)당 1행"**(04 1.1) vs 07의 "인덱스일 뿐 `unique` 아님": `integrations (platform, org, team)`에 **DB 유일 제약이 없음이 확정**됐다(마이그레이션 59개 확인). 04 정정됨. 1행 유지는 앱 로직(`handleIntegration`의 update/create 분기)에 의존하며, **동시 요청 시 중복 행이 생기는지는 미확인** | [KO 04 1.1](../reports/kodus-ai/04-saas-and-isolation.md), [KO 07 2.1, 9절](../reports/kodus-ai/07-credentials.md) | 정정 완료(동시 요청 중복은 미확인) |
| 5 | **KO "규칙 vs 설정의 범위"**: 03 8.1은 규칙에 `teamId`가 없다고 하고 8.4는 설정이 팀 키라고 한다. 모순은 아니나 "팀 규칙 지원"으로 읽히기 쉽다. **규칙은 조직 범위(`organizationId`), 설정(`parameters`)만 팀 키**이며 03에 객체별 범위 키 표가 추가됐다 | [KO 03 8.1 표(앵커 `q8-scope`)](../reports/kodus-ai/03-incremental-memory-rules.md#q8-scope), [8.4](../reports/kodus-ai/03-incremental-memory-rules.md#q8) | 이 문서 2.1절에 구분해 적음 |
| 6 | **제품 문구와 코드 차이**(보고서가 이미 기록한 것): KO 문서의 `@kody remember` 핸들러는 코드에 없음, KO 문서 "every PR review"와 Business Logic 실행 조건 차이, KO `AGENTS.md`의 Jira/Linear 통합 서술과 어댑터 없음, PA 문서의 Jira 하위 작업·이미지 서술과 코드 불일치 | [KO 03 7.5, 9.1~9.2](../reports/kodus-ai/03-incremental-memory-rules.md#q7), [PA 00 7절](../reports/pr-agent/00-overview.md) | 보고서 간 모순은 아님(문서 vs 코드) |

### 5.2 검증 약점

- **KO 줄 번호의 재대조 현황(2026-10-13 정정 후)**: 02~05의 `path:range` 인용 약 650개(02 약 198, 03 약 205, 04 약 155 중 약 150, 05 약 95)를 모두 열어 범위·식별자를 대조하고 약 30건을 정정했다. **재대조하지 못한 범위**: 01 전체, 02의 긴 범위(`agent-tools.factory.ts:300-1757` 등), 03의 긴 범위(경계·핵심 식별자만 확인, 본문 전체 미독), 04의 `outbox-relay.service.ts:632-859`·`worker.module.ts:49-143`·`workflow.module.ts:121-148`(앵커만), 05의 파일명만 인용한 파일(각 문서 머리, [KO next](../reports/kodus-ai/next.md)). 반면 **KO 07은 모든 줄 번호를 작성자가 직접 열어 확인**했다고 밝히므로 신뢰 수준이 다르다. 이 문서의 KO 03 인용은 줄 번호를 옮기지 않고 절 링크만 단 이유다.
- **KO 문서 머리의 검증 수준 숫자**는 2026-10-13에 검증 열이 있는 표의 행을 스크립트로 재집계한 값이다(KO 03: 코드 확인 37 / 추론 6 / 미확인 0; 복수 표기 행은 중복 계산, 검증 열이 없는 표·본문은 제외). 표 행 단위 집계이므로 다른 레포 숫자와 비교하지 않는다. KO는 기능 지원 수준이 모든 행이 아니라 항목(Q) 단위 요약에만 붙어 있다([KO next](../reports/kodus-ai/next.md)).
- **KO 규칙 편집 UI(`apps/web`)는 범위 밖이라 미확인**이다. 승인·비활성화 UX는 API 기준으로만 비교했다.
- **KO 디렉터리 규칙 누수와 "죽은 분기"(`command` 강제 조건) 판단은 추론**이고 유닛 테스트도 확인하지 못했다([KO 03 8.2, 6.1](../reports/kodus-ai/03-incremental-memory-rules.md#q8)).
- **PA 03은 일부만 열람한 영역이 있다.** 경로별(모노레포) 설정 병합의 상세 규칙(`_get_per_directory_settings`)은 일부만 열람했고, `similar_issue`는 앞부분만 확인했다([PA 03 8.1, 7.6](../reports/pr-agent/03-incremental-memory-rules.md#q8), [PA next](../reports/pr-agent/next.md)).
- **PA의 "해결 해석 위험"과 "dismissed 해석 위험"은 추론**(코드 비교가 아니라 부재에 기반한다는 점에서 도출).
- **세 레포 모두 실행 확인이 0건**이다. 모델 비결정성이 관여하는 동작(PA의 문구 복사 의존, KO의 LLM 판정)은 실제 빈도를 알 수 없다.
- **OC는 PR 간 메모리·증분·Jira가 "없다"는 부정 결과**다. 검토한 저장 코드와 검색 범위가 03에 적혀 있다(검색 실패만으로 단정하지 않는다는 GUIDE 규칙에 따라 범위를 함께 읽을 것).

### 5.3 이 문서 작성 중 직접 확인한 것

- `repos/open-code-review`: `ContentLogging` 호출처 부재(정의 `internal/telemetry/provider.go:70`만 존재), `internal/tool/definitions.go`의 도구 항목 7개(`Unknown` 포함).
- 코드는 읽기만 했고 실행하지 않았다. 그 밖의 서술은 모두 보고서 링크 근거다.
