# open-code-review — 증분 리뷰, 장기 메모리, 팀 규칙, Jira

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q6, Q7, Q8, Q9
- 검증 수준 요약: 코드 확인 34 / 실행 확인 0 / 추론 0 / 미확인 0 (집계 기준: 이 문서 증거 표의 행 단위, 검증 칸 맨 앞 판정으로 분류(1행=1판정). 검증 칸 안에 보조로 병기된 추론·미확인은 괄호로 별도 표기. 설명 칸 안의 인라인 표기와 서술 문단은 집계 제외)
- 실행 여부: 정적 추적만

경로는 `code-review/repos/open-code-review/` 기준이다.

---

## Q6. 증분 리뷰 {#q6}

기능 지원 수준: **미지원**(엔진). 찾은 범위: `cmd/opencodereview`, `internal/agent`, `internal/diff`, `internal/session` 전체. "마지막으로 리뷰한 SHA", "이미 게시한 코멘트", "이벤트 ID"를 저장하거나 조회하는 코드가 없다.

| 항목 | 현황 | 위치 | 검증 |
|---|---|---|---|
| 비교 기준 | 매 실행마다 새로 계산. range: `merge-base(from,to)..to` 전체, commit: 단일 커밋, workspace: `HEAD` 대비 전체 미커밋 변경(+미추적). "지난번 이후"라는 개념 없음 | `internal/diff/git.go:112-146` | 코드 확인 |
| 이전 실행 결과 저장 | 세션 JSONL에 `diffFrom/diffTo/diffCommit` 메타가 **쓰이지만** 다음 실행이 읽지 않음 | `internal/session/persist.go:125-155`, 읽기 코드는 `internal/viewer`뿐(아래 Q7 참조) | 코드 확인 |
| 이벤트 중복·연속 업데이트·작업 재시도 | 엔진에 이벤트 개념 없음. 예제 워크플로의 `concurrency: group per PR, cancel-in-progress: true`가 GitHub 쪽에서 이전 실행을 취소 | `examples/github_actions/ocr-review.yml:21-23` | 코드 확인(예제 YAML 한정) |
| 새 커밋 트리거 | 예제는 `pull_request_target: types: [opened]`와 `issue_comment: created`만 구독. `synchronize`(새 푸시) 미구독 → **푸시 후 자동 재리뷰 없음**, 수동 코멘트 트리거만 | `examples/github_actions/ocr-review.yml:29-32` | 코드 확인 |
| GitLab 쪽 장치 | `interruptible: true`, `resource_group: mr-review-$CI_MERGE_REQUEST_IID` (동일 MR 작업 직렬화) | `examples/gitlab_ci/.gitlab-ci.yml:27-28` | 코드 확인 |
| 실행 중 Head 변경 시 폐기 | 없음. `--to`에 SHA를 넘기면(예제 방식) 일관, 브랜치명을 넘기면 도중 이동 영향 가능 | `examples/github_actions/ocr-review.yml:95-110`, `01-execution-and-diff.md#q2` | 코드 확인 |
| 이전 코멘트 유지/수정/해결 | 없음. 예제 스크립트는 기존 리뷰·코멘트를 조회하지 않고 `createReview`/`discussions`로 **매번 새로 게시** | `examples/github_actions/ocr-review.yml:228-237`, `examples/gitlab_ci/.gitlab-ci.yml:204-224` (조회 API 호출 없음: `list`, `resolve`, `outdated` 검색 결과 없음) | 코드 확인 |

→ 서비스화 시 증분 리뷰는 **전부 새로 구현**해야 한다(의견은 `06-fit.md`).

---

## Q7. 장기 메모리 (쓰기와 읽기 양쪽) {#q7}

기능 지원 수준: **PR 간 영속 메모리 미지원.** 같은 실행 안의 대화·압축만 있다.

### 7.1 종류별 구분

| 종류 | 존재 | 위치 | 검증 |
|---|---|---|---|
| 실행 대화 | 있음. 파일 하위 작업의 지역 `messages` | `internal/agent/agent.go:494-516`, `:848-958` | 코드 확인 |
| 실행 내 압축 요약 | 있음. 이름이 `MEMORY_COMPRESSION_TASK`이지만 **실행 중 컨텍스트 요약**이며 영속하지 않음. 요약은 user 메시지 끝 `<previous_review_summary>`에만 삽입 | `internal/agent/compression.go:177-241`, `internal/config/template/prompts/memory_compression_task_system.md:1-31` | 코드 확인 |
| 실행 체크포인트(재개) | 없음. 세션 JSONL은 기록용이며 재개 로직 없음 | `internal/session/*.go`, 읽기 소비자 없음 | 코드 확인 |
| 같은 PR의 이전 리뷰 이력 | 없음(Q6) | - | 코드 확인 |
| **PR 간 영속 메모리(팀 지식)** | **없음** | 아래 검토 범위 | 코드 확인(부재는 검토 범위 내) |

### 7.2 쓰기 경로 (있는 것: 관측용 로그)

| 쓰는 것 | 저장소 | 스키마 | 위치 | 검증 |
|---|---|---|---|---|
| 모든 LLM 요청 메시지(프롬프트·**diff·도구가 읽은 소스 코드**), 응답, 도구 호출·결과, 토큰 사용량, 실패 수 | `~/.opencodereview/sessions/<인코딩된 저장소 경로>/<세션 UUID>.jsonl` (디렉터리 0700, 파일 0600, 열 때 `O_TRUNC`) | JSONL 레코드: `session_start`, `llm_request`, `llm_response`, `llm_error`, `tool_call`, `session_end` (`uuid`/`parentUuid` 체인) | `internal/session/persist.go:92-112`, `:124-282`, `internal/session/history.go:105-129` | 코드 확인 |
| 사용자 반응(답변·반박·수정·승인·resolve) | **수집 코드 없음** | - | 입력 경로 자체가 없음(엔진은 Git 호스팅 이벤트를 받지 않음, `01-execution-and-diff.md#q1`) | 코드 확인 |
| 원문 로그 → 재사용 지식 변환 | **없음** | - | `internal/session`, `internal/agent` 전체에 요약·추출 로직 없음(압축 요약은 실행 내 한정) | 코드 확인 |

### 7.3 읽기 경로 (리뷰에서 읽는 것은 없음)

- `~/.opencodereview/sessions`를 읽는 코드는 `internal/viewer/store.go`(`SessionsRoot`, JSONL 파서)뿐이고, 이는 `ocr viewer`가 띄우는 **읽기 전용 WebUI**용이다(`internal/viewer/store.go:1-24`, `cmd/opencodereview/viewer_cmd.go:28-40`). `internal/viewer` 임포트는 `cmd/opencodereview/viewer_cmd.go` 하나뿐이고 `internal/agent`는 임포트하지 않는다(임포트 grep).
- 따라서 **"기록만 있고 조회가 없다"**: 세션 로그는 다음 리뷰의 입력이 되지 않는다. "피드백 학습"이라 부를 수 없다.
- 검토한 저장 코드와 범위: `internal/session/history.go`, `internal/session/persist.go`, `internal/viewer/store.go`, `internal/config/rules/system_rules.go`(규칙 파일), `cmd/opencodereview/config_cmd.go`(설정 파일), `~/.opencodereview` 참조 전체(`config.json`, `rule.json`, `sessions/`; grep 결과 `config_cmd.go:14-20`, `rules_cmd.go:65-66`, `resolver.go:76`, `system_rules.go:179-340`, `telemetry/config.go:61,124-130`, `viewer/store.go:3,23`, `persist.go:17,98`).
- 읽기 방식 비교(최초 입력 주입 vs 호출 가능한 도구): 해당 없음. 과거 지식을 모델에 주는 경로가 둘 다 없다. 사용자가 `--background`나 `rule.json`에 **수동으로** 적은 텍스트가 정적 입력이 될 뿐이다.
- 동의 해석 위험(무응답/resolve/코드 수정을 동의로 간주): 해당 없음(해석할 입력이 없음).
- 유사 이슈 검색: 없음.

### 7.4 서비스화 관점 주의

- 세션 JSONL에는 **리뷰한 소스 코드 전체**가 들어간다. 서비스 워커에서 그대로 두면 테넌트 코드가 워커 디스크의 홈 디렉터리에 평문으로 쌓인다(`04-saas-and-isolation.md`).
- telemetry의 `content_logging`은 README(`README.md:520`)가 "프롬프트·응답을 내보낸다"고 설명하지만 **이 SHA에서는 효과가 없다.** 설정 값은 읽히고(`internal/telemetry/config.go:25`, `:56-58`) `ContentLogging()`이 정의돼 있으나(`internal/telemetry/provider.go:69-76`) 이 함수를 호출하는 곳이 `cmd/`·`internal/` 어디에도 없어(재확인: 정의 외 호출처 0) 켜도 프롬프트·응답이 내보내지지 않는다. 기본은 꺼짐(`telemetry/config.go:15`). 상세와 근거 범위: [07 4.3절·"기존 보고서와 다른 점" 4번](07-credentials.md#diff-from-existing). 코드 확인.

---

## Q8. 팀 규칙 {#q8}

기능 지원 수준: **부분 지원** — 경로별 자연어 체크리스트를 파일로 계층 적용하는 기능은 있다. 조직·팀 범위, 승인·버전·비활성화 관리, 피드백에서의 자동 추출은 **미지원**.

### 8.1 범위 계층과 스키마

| 계층(우선순위 높음→낮음) | 로드 위치 | 소유자 | 위치 | 검증 |
|---|---|---|---|---|
| ① 실행 지정 | `--rule <path>` JSON | 호출자 | `internal/config/rules/system_rules.go:327-337` | 코드 확인 |
| ② 저장소 | `<repoDir>/.opencodereview/rule.json` (**작업 트리**에서 읽음. range 모드에서도 `--to` ref가 아님) | 저장소 사용자 | `system_rules.go:339-353` | 코드 확인 |
| ③ 전역 | `~/.opencodereview/rule.json` | 로컬 사용자 | `system_rules.go:307-325` | 코드 확인 |
| ④ 내장 | 바이너리 임베드 `system_rules.json` + `rule_docs/*.md` (기본 1 + 경로 패턴 15종) | 프로젝트 | `system_rules.go:83-109`, `internal/config/rules/system_rules.json:2-19` | 코드 확인 |

스키마: `{"rules":[{"path":"<glob>","rule":"<자연어>"}], "include":[...], "exclude":[...]}` (`system_rules.go:179-190`). 글롭은 `doublestar` + `{a,b}` 중괄호 직접 전개, **경로를 소문자로 바꿔** 비교(`system_rules.go:127-138`, `:156-177`, `:383-397`). 조직·팀·명령별 범위는 없다.

### 8.2 우선순위와 충돌 처리

- 계층 순서대로 보고 **첫 번째로 일치한 계층의 규칙 텍스트 하나만** 쓴다. 계층 간 **병합하지 않는다**(`system_rules.go:356-367`). 계층 안에서도 선언 순서상 첫 일치가 이긴다(`:383-397`). 빈 `rule` 문자열은 일치로 치지 않고 다음 계층으로 넘어간다(`:357-362`의 `rule != ""` 검사).
- `include/exclude`는 `custom > project > global` 중 include·exclude가 있는 **가장 높은 계층 하나**만 적용하고 합치지 않는다(`system_rules.go:285-305`). 필터 판정 순서: 바이너리 → 사용자 exclude → (include 일치 시 통과) → 확장자 허용 → 기본 제외 경로(`internal/agent/preview.go:45-71`).
- 충돌 시 사용자 입력(`--background`)과 규칙은 서로 다른 슬롯이라 충돌하지 않는다. 둘 다 프롬프트에 들어간다.

### 8.3 생성·편집·승인·버전·비활성화

| 항목 | 현황 | 검증 |
|---|---|---|
| 생성·편집 | 사용자가 JSON 파일을 직접 수정. 편집 UI·API 없음. `ocr rules check <file>`로 어떤 규칙이 적용되는지 **조회만** 가능 | 코드 확인 (`cmd/opencodereview/rules_cmd.go:26-79`) |
| 승인·버전 관리 | 없음(파일을 Git에 두면 Git이 대신할 뿐, 코드 기능 아님) | 코드 확인(부재) |
| 비활성화 | `exclude` 패턴으로 파일 제외만 가능. 규칙 단위 on/off 없음 | 코드 확인 |
| 개발자 피드백에서 규칙 추출 | 없음(트리거·검증 단계 모두 없음) | 코드 확인(`internal/` 전체에서 피드백 입력 경로 부재, Q7) |

### 8.4 리뷰 시 읽기와 모델 입력 위치

| 단계 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 로드 | 실행 시작 시 1회 `NewResolver` | `cmd/opencodereview/review_cmd.go:62-65` | 코드 확인 |
| 선택 | 파일마다 `resolveSystemRule(strings.ToLower(newPath))` | `internal/agent/agent.go:465`, `:674-679` | 코드 확인 |
| 삽입 | Main·Plan의 **user 메시지** `### Review Checklist` 아래 `{{system_rule}}` (system 메시지가 아님, 순서는 요구사항 배경 → 체크리스트 → 계획) | `internal/config/template/prompts/main_task_user.md:14-22`, `plan_task_user.md:14-18`, `agent.go:500` | 코드 확인 |
| 기본 규칙 내용 예 | `default.md`: 정확성·보안·성능·유지보수성·테스트 5축 질문 목록. `.go`용 전용 문서는 없음(매핑에 `*.go` 없음) | `internal/config/rules/rule_docs/default.md:1-22`, `system_rules.json:3-19` | 코드 확인 |

구분: OCR의 규칙은 **"커스텀 프롬프트 파일"**이다. 저장·승인·버전 관리되는 팀 규칙 시스템도, 자동화된 정책 엔진도 아니다.

신뢰 경계 주의(코드 확인 + 영향은 추론): `.opencodereview/rule.json`은 **리뷰 대상 작업 트리**에서 읽는다. 예제 워크플로가 `pull_request_target`(시크릿 접근 가능)으로 PR head를 체크아웃한 채 `ocr`를 실행하므로(`examples/github_actions/ocr-review.yml:26-29`, `:64-68`), 포크 PR이 자기 `rule.json`(프롬프트 주입 가능 텍스트)을 넣을 수 있다. 서비스화 시 규칙은 PR head가 아니라 기본 브랜치/서비스 저장소에서 읽어야 한다(의견).

---

## Q9. Jira / 요구사항 {#q9}

기능 지원 수준: Jira·이슈 트래커 연동 **미지원**. 요구사항 **텍스트를 프롬프트에 넣는 입력 슬롯**만 **부분 지원**. 조건별 근거 탐색·판정은 **미지원**.

찾아본 곳: 레포 전체(`.git`, `graphify-out`, `node_modules` 제외)에서 `jira|atlassian|confluence|linear.app|tapd|yunxiao|codeup` 검색 결과 없음(README 포함). `cmd/`, `internal/`, `skills/`, `plugins/`, `examples/`의 `issue|ticket|acceptance|requirement` 검색은 일반 단어 용례와 `--background` 관련 줄뿐.

| 항목 | 현황 | 위치 | 검증 |
|---|---|---|---|
| 이슈 식별(브랜치명·제목·링크) | 없음 | - | 코드 확인(부재) |
| 인증·필드 추출(Acceptance Criteria) | 없음 | - | 코드 확인(부재) |
| 요구사항 텍스트 입력 | `--background/-b` 문자열 1개. `--commit`이면 커밋 메시지 자동 사용 | `cmd/opencodereview/flags.go:131`, `review_cmd.go:56-60` | 코드 확인 |
| 삽입 위치 | Plan·Main user 메시지의 `### Requirement Background (Optional)` 아래 `{{requirement_background}}` | `main_task_user.md:14-16`, `plan_task_user.md:14-15`, `agent.go:503`, `:778` | 코드 확인 |
| 입력 vs 조건별 판정 | **입력뿐.** 시스템 프롬프트에 "요구사항 충족 여부를 판정하라"는 지시나 요구사항별 결과 필드가 없다(`main_task_system.md` 전체, `LlmComment` 필드: `internal/model/review.go:4-12`) | 위 | 코드 확인 |
| PR 범위 vs 이슈 전체 범위 구분 | 없음 | - | 코드 확인(부재) |
| 요구사항 수집 위임 | 엔진 밖. `skills/open-code-review/SKILL.md`가 코딩 에이전트에게 "비즈니스 컨텍스트를 요약해 `--background`로 넘겨라"고 안내 | `skills/open-code-review/SKILL.md` ("Step 1: Gather Business Context") | 코드 확인(문서) |

### 확장 지점 제안 (의견)

요구사항 수집과 요구사항별 근거 탐색을 넣는다면 아래 위치가 자연스럽다. 코드 근거가 아니라 설계 제안이다.

| 필요 기능 | 삽입 위치 | 제안 시그니처/동작 |
|---|---|---|
| 요구사항 수집 | `runReview`의 `opts.background` 결정부(`review_cmd.go:56-60`) 앞 | `type Requirement struct{ID, Title, Text string; Source string}`, `type RequirementProvider interface{ Fetch(ctx, ref ChangeRef) ([]Requirement, error) }` (Jira·Linear·PR 본문 어댑터). 결과를 `agent.Args`에 `Requirements []Requirement`로 전달 |
| 이번 PR 범위 구분 | 수집 직후 | `ScopeFilter(reqs, diffs) []Requirement`: LLM 1회로 "이번 diff가 다루는 조건"만 선별, 나머지는 `out_of_scope`로 표기 |
| 입력 주입 | `agent.go:494-516`의 `strings.ReplaceAll` 치환 목록 | `{{requirements}}` 자리표시자 추가(조건별 번호 포함). 현재 `{{requirement_background}}`는 단일 문자열 |
| **조건별 근거 탐색·판정** | `dispatchSubtasks` 반환 직전(`agent.go:434-445`) | 새 단계 `verifyRequirements(ctx, reqs)`: 요구사항마다 **별도 Agent Loop**를 돌리되 기존 Provider 구현 5개(`task_done` 제외, 기준: [00 1절](00-overview.md))를 재사용하고 `requirement_verdict{id, status: satisfied\|violated\|unknown, evidence:[{path,start_line,end_line}]}` 도구를 추가. 종료는 `task_done` 대신 verdict 제출. `tool.OfName` 고정 목록(`definitions.go:13-21`, `:32-34`)에 이름을 추가해야 함 |
| 결과 모델 | `model.LlmComment`(`review.go:4-12`) | `RequirementID string` 필드 추가 또는 별도 `RequirementFinding` 타입 |
