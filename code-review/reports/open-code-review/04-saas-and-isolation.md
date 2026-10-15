# open-code-review — SaaS 해당 없음과 서비스 워커화 시 분리할 의존성

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q10 (단일 사용자 CLI이므로 "해당 없음" + 분리할 의존성 중심)
- 검증 수준 요약: 코드 확인 30 / 실행 확인 0 / 추론 0 / 미확인 0 (보조: 코드 확인 행에 추론 병기 2행, 미확인 병기 1행. 집계 기준: 이 문서 증거 표의 행 단위, 검증 칸 맨 앞 판정으로 분류(1행=1판정). 검증 칸 안에 보조로 병기된 추론·미확인은 괄호로 별도 표기. 설명 칸 안의 인라인 표기와 서술 문단은 집계 제외)
- 실행 여부: 정적 추적만

경로는 `code-review/repos/open-code-review/` 기준이다.

---

## Q10. SaaS: 인증, 큐, 격리, 장애 복구 {#q10}

### 10.1 해당 없음 판정과 찾아본 범위

| 항목 | 판정 | 찾아본 범위 / 근거 | 검증 |
|---|---|---|---|
| 웹훅 서명 검증·이벤트 필터링 | **미지원** | `cmd/`, `internal/` 전체. HTTP 서버는 `internal/viewer`(세션 뷰어, `internal/viewer/server.go:15-60`)뿐이고 웹훅 핸들러·서명 검증 없음 | 코드 확인 |
| GitHub App 설치 토큰·GitLab 토큰 수명·보관 | **미지원**(엔진). 예제 YAML이 CI가 주는 `GITHUB_TOKEN`·`CI_JOB_TOKEN`·`GITLAB_API_TOKEN`을 게시 스크립트에 사용 | `examples/github_actions/ocr-review.yml:117-120`, `examples/gitlab_ci/.gitlab-ci.yml:69-86` | 코드 확인 |
| 큐 발행·소비·ack/nack·재시도 | **미지원** | 큐·브로커 클라이언트 의존성 없음(`go.mod` 직접 의존 목록, `05-dependencies.md`), 코드에 작업 큐 개념 없음 | 코드 확인 |
| 실패 작업 저장·장애 복구 | **미지원**. 실패는 `warnings`/`subtask_error`로 결과 JSON에 담길 뿐 재시도 큐 없음. 프로세스 종료 시 부분 결과 유실 | `internal/agent/agent.go:418-424`, `cmd/opencodereview/output.go:210-244` | 코드 확인, 유실은 추론 |
| 테넌트 격리 | **해당 없음**(단일 사용자 가정). DB·캐시·벡터 검색·메모리 조회 자체가 없음. clone 경로·세션 경로는 호출자의 `$HOME`과 `--repo`에 의존 | `internal/session/persist.go:92-112`, `cmd/opencodereview/review_cmd.go:48-51` | 코드 확인 |
| 외부 서비스 장애·지연·비용 영향 | 영향 지점은 LLM API 한 곳. 단계별 영향: Plan 실패→계획 없이 진행, Main 실패→해당 파일 실패, 압축 실패→원본 유지, 필터 실패→필터 생략 | `internal/agent/agent.go:478-487`, `:873-877`, `compression.go:205-212`, `agent.go:576-585` | 코드 확인 |
| 비용·부하 상한 | 파일당 최대 30라운드 × 동시 8파일 × 라운드마다 누적 컨텍스트. **총 토큰·비용 예산 상한 없음**(토큰은 집계만 함) | `agent.go:386-394`, `:883-886`, `internal/config/template/task_template.json:37` | 코드 확인 |

기능 지원 수준 (Q10): **미지원 / 해당 없음**.

---

## 서비스 워커화 시 분리할 의존성 (분석 중점)

엔진 본체는 `agent.New(agent.Args{...})` + `Run(ctx)` 형태로 의존성을 인자로 받는다(`internal/agent/agent.go:26-99`, `:179-252`). 문제는 그 바깥(진입점, 전역 상태, 홈 디렉터리 파일, 환경변수)에 있다.

### A. 패키지 접근성 (가장 먼저 부딪히는 제약)

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| `internal/` 경계 | 엔진은 전부 `internal/...`(Go 규칙상 **다른 모듈에서 import 불가**). 외부 서비스가 쓰려면 ① 포크해 `pkg/`로 노출, ② `ocr` 바이너리를 하위 프로세스로 호출 중 하나 | `go.mod:1` (모듈 `github.com/open-code-review/open-code-review`), 패키지 경로 전부 `internal/` | 코드 확인 |
| `package main`에 묶인 로직 | 설정 로드(`LoadAppConfig`, `defaultConfigPath`), 플래그, 출력 렌더링, 라인 해석 호출 순서(`review_cmd.go:157`)가 `cmd/opencodereview`(main 패키지)에 있어 재사용하려면 복사 필요 | `cmd/opencodereview/review_cmd.go:23-191`, `config_cmd.go:14-20` | 코드 확인 |

### B. TUI

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| Bubble Tea/Lip Gloss/Bubbles | **리뷰 엔진에는 없음.** `ocr config provider`/`config model` 대화형 설정 화면에만 쓰임(`charm.land` 임포트 파일: `provider_cmd.go`, `provider_tui.go`, 테스트) | `cmd/opencodereview/provider_tui.go`, `provider_cmd.go` | 코드 확인(임포트 grep) |
| 터미널 진행 출력 | 엔진이 진행 상황을 `stdout`에 직접 쓴다: `fmt.Fprintf(stdout.Writer(), "[ocr] ...")` 다수, ANSI 색 코드, 도구 호출 로그 | `internal/agent/agent.go`(다수), `internal/telemetry/events.go:84-106` | 코드 확인 |
| 전역 출력 스위치 | `stdout.Quiet()`가 **프로세스 전역** writer를 `io.Discard`로 바꾼다. 주석이 "main goroutine에서만, 중첩·병렬 금지"를 명시 → 한 프로세스에서 리뷰를 동시에 여러 개 돌리면 안전하지 않음 | `internal/stdout/stdout.go:9-40`, `review_cmd.go:136-144` | 코드 확인 |
| 직접 출력 | 일부 경로는 전역 writer를 쓰지 않고 `fmt.Printf`/`os.Stderr`로 바로 씀(세션 기록기 경고, diff 파서 경고) → 로그 수집 시 섞임 | `internal/session/history.go:122`, `internal/session/persist.go:117`, `internal/diff/parser.go:114-115`, `:123` | 코드 확인 |

### C. 파일 시스템

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| **로컬 git 작업 트리 필수** | 코드 접근이 전부 `exec git` + 작업 트리/로컬 객체 DB. 서비스는 리뷰마다 clone/fetch 후 `--repo`에 넘겨야 함(엔진이 clone하지 않음) | `internal/gitcmd/runner.go:43-127`, `internal/diff/git.go:335-343` | 코드 확인 |
| 홈 디렉터리 설정 | `~/.opencodereview/config.json`(LLM 키 평문, 파일 0600) 읽기. `runReview`가 항상 읽음 | `cmd/opencodereview/review_cmd.go:78-91`, `config_cmd.go:14-20`, `provider_cmd.go:277-293` | 코드 확인 |
| 홈 디렉터리 규칙 | `~/.opencodereview/rule.json`(전역 규칙) 자동 로드. 워커 계정 홈에 우연히 있으면 모든 테넌트 리뷰에 섞임 | `internal/config/rules/system_rules.go:307-325` | 코드 확인 |
| 저장소 규칙 | `<repo>/.opencodereview/rule.json`(PR head 작업 트리) 로드 → 신뢰 경계 문제(`03-incremental-memory-rules.md#q8`) | `system_rules.go:339-353` | 코드 확인 |
| 세션 로그 쓰기 | **끌 수 없음.** `agent.New`는 `Args.Session`이 비면 `session.New`를 호출하고 항상 `$HOME/.opencodereview/sessions/...jsonl`을 연다(실패하면 경고만 출력하고 계속). `SessionHistory`의 저장 필드가 비공개라 외부에서 "저장 없는 세션"을 만들 방법도 없음. 로그에는 diff와 도구가 읽은 **소스 코드 전체**가 평문으로 들어감 | `internal/agent/agent.go:186-198`, `internal/session/history.go:105-129`, `persist.go:92-112` | 코드 확인 |
| `.gitignore` 파싱 | 저장소 루트의 `.gitignore`를 직접 읽음 | `internal/diff/git.go:163-178` | 코드 확인 |
| 작업 디렉터리 | `--repo` 미지정 시 `os.Getwd()` | `cmd/opencodereview/review_cmd.go:193-200` | 코드 확인 |
| 외부 바이너리 | `git`(PATH 의존). `code_search`는 `git grep -P`를 쓰므로 PCRE 지원 빌드가 필요(추론) | `internal/tool/code_search.go:52-78` | 코드 확인, PCRE는 추론 |

### D. 환경변수와 암묵적 설정 탐색

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| LLM 엔드포인트 해석 순서 | 설정 파일 → `OCR_LLM_URL/TOKEN/MODEL/AUTH_HEADER`, `OCR_USE_ANTHROPIC` → `ANTHROPIC_BASE_URL/AUTH_TOKEN/MODEL` → **`~/.zshrc`, `~/.bashrc`, `~/.bash_profile`, `~/.profile`을 정규식으로 파싱해 `export ANTHROPIC_*`를 읽음** | `internal/llm/resolver.go:49-77`, `:80-115`, `:328-343`, `:346-429` | 코드 확인 |
| 프리셋 제공자 키 | 제공자별 환경변수 폴백(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY` 등) | `internal/llm/providers.go:19-217`, `resolver.go:187-195` | 코드 확인 |
| 우선순위 함정 | 설정 파일에 유효 엔드포인트가 있으면 환경변수가 무시됨(첫 유효 전략 사용). 워커에서 테넌트별 키를 환경변수로 주입하려면 설정 파일이 없어야 함 | `resolver.go:62-74` | 코드 확인 |
| telemetry | `OCR_ENABLE_TELEMETRY=1`, `OTEL_*`, `OCR_CONTENT_LOGGING=1`(**읽히지만 효과 없음**: `ContentLogging()` 호출처 없음, [07](07-credentials.md#diff-from-existing) 4번), 설정 파일 `telemetry` 키. 전역 OTel provider 초기화(`main`에서 1회) | `internal/telemetry/config.go:40-59`, `provider.go:28-62` | 코드 확인 |

### E. 전역 상태와 프로세스 모델

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 전역 변수 | `llm.AppVersion`, tiktoken BPE 로더(`tiktoken.SetBpeLoader`), tokenizer 캐시, telemetry provider, `stdout` writer | `internal/llm/client.go:21`, `:242`, `embedded_loader.go:20-23`, `internal/telemetry/provider.go:14-23`, `internal/stdout/stdout.go:9-12` | 코드 확인 |
| 프로세스 수명 | 1회 실행 후 종료 모델(`main` → `os.Exit(1)` 오류 시). 장기 실행 서버에서의 누수·재진입은 검증되지 않음 | `cmd/opencodereview/main.go:15-28` | 코드 확인, 장기 실행 안정성은 미확인 |
| 취소 | 엔진 `Run(ctx)`는 ctx를 받지만 CLI는 `context.Background()`만 넘김. 서비스는 자체 ctx로 취소 가능하나 비동기 코멘트 작업은 `WithoutCancel`이라 취소 후에도 진행 | `review_cmd.go:146`, `agent.go:1037` | 코드 확인 |
| 결과 형식 | `[]model.LlmComment` + `Warnings()` + 토큰 합계. 엔진 반환형이 단순해 어댑터 작성은 쉬움 | `agent.go:206-302`, `internal/model/review.go:4-12` | 코드 확인 |
| 자원 제한 | 동시 파일 수·git 프로세스 수 제한은 있으나 **프로세스 단위**(테넌트 단위 쿼터 없음) | `agent.go:386-394`, `gitcmd/runner.go:11-41` | 코드 확인 |

### F. 서비스 워커에서의 권장 분리 요약 (의견)

| 분리 대상 | 방법 | 이유 |
|---|---|---|
| LLM 설정 해석 | `llm.ResolvedEndpoint` 구조체를 서비스가 직접 채워 `llm.NewLLMClient(ep)`에 전달(`client.go:194-206`). 설정 파일·환경변수·셸 rc 탐색 경로 제거 | 테넌트별 키, 암묵적 홈 탐색 차단 |
| 세션 로그 | 저장 위치/비활성화 옵션 추가 또는 구조화 이벤트 싱크로 교체 | 소스 평문 기록 방지, 전역 `$HOME` 쓰기 제거 |
| 출력 | `stdout` 전역 writer 대신 `io.Writer`/이벤트 콜백을 `Agent`에 주입 | 동시 리뷰 안전, 로그 구조화 |
| 규칙 로드 | 전역(`~`)·저장소(PR head) 규칙 경로 제거, 서비스 저장소/DB에서 `rules.Resolver` 구현체 주입(`Resolver` 인터페이스가 이미 있음, `system_rules.go:15-18`) | 신뢰 경계, 테넌트 규칙 |
| 코드 확보 | 서비스가 clone/fetch·SHA 고정(`--to`에 SHA) 후 `--repo`로 전달, 또는 `FileReader`를 인터페이스로 바꿔 Provider API 읽기 구현 | 엔진은 로컬 git 가정 |
| 진입점 | `runReview`의 오케스트레이션을 라이브러리 함수로 복제(`cmd` main 패키지라 import 불가) | `internal/` 경계 |
