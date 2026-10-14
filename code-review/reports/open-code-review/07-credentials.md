# open-code-review — 비공개 저장소 접근과 자격증명(토큰) 관리

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치, `git rev-parse HEAD`로 재확인)
- 분석일: 2026-10-13
- 관련 공통 항목: Q13 (보조: Q2 코드 접근, Q10 서비스화, Q12 의견)
- 검증 수준 요약: 코드 확인 62 / 실행 확인 0 / 추론 2 / 미확인 2 (보조: 코드 확인 행에 추론 병기 2행, 미확인 병기 3행. 별도로 "미확인 / 한계" 표 4행은 이 집계에 포함하지 않음. 집계 기준: 이 문서 증거 표의 행 단위, 검증 칸 맨 앞 판정으로 분류(1행=1판정). 검증 칸 안에 보조로 병기된 추론·미확인은 괄호로 별도 표기. 설명 칸 안의 인라인 표기와 서술 문단은 집계 제외. 2026-10-13 정정: "약 55/추론 7/미확인 4" 근사치를 행 수 재계산으로 교체)
- 실행 여부: 정적 추적만. 설치·빌드·실행·파일 수정 없음. `graphify-out/`는 근거로 쓰지 않음. 실제 키·토큰 값은 기록하지 않고 변수명·설정 키 경로만 적음.

경로는 `code-review/repos/open-code-review/` 기준이다. 기존 결론은 [01](01-execution-and-diff.md), [04](04-saas-and-isolation.md), [00](00-overview.md)를 따르고, 여기서는 **자격증명 관점에서 새로 확인한 것**만 적는다.

---

## 0. 한눈 요약

| 질문 | 답 | 지원 수준 |
|---|---|---|
| Git Provider 토큰이 필요한가 | **엔진은 필요 없다.** 코드를 로컬 git 저장소에서만 읽고(git 하위 프로세스), GitHub/GitLab API·clone·fetch·댓글 게시 코드가 엔진에 없다. 게시용 토큰은 예제 CI YAML에만 있다 | Provider 연동 **미지원**(엔진), 예제 YAML **부분 지원** |
| 비공개 저장소 | 사용자가 **미리 clone/fetch한 로컬 체크아웃**을 `--repo`로 넘겨야 한다. 인증은 엔진 밖(git/CI) 책임 | 해당 없음(엔진 밖) |
| LLM 키 | env / `~/.opencodereview/config.json`(평문, 0600) / 셸 rc 파싱. **CLI 플래그 없음**, 시크릿 매니저·키체인 없음 | 지원(평문 저장) |
| 소스·키 전송 | 소스는 LLM URL로(필수) + 세션 JSONL에 평문 기록(끌 수 없음) + OTel 켜면 경로·오류 문자열 외부 전송. 키는 JSONL·OTel에 기록하는 코드 없음 | - |
| AWS / MCP / 시크릿 매니저 | 이 SHA에 **없음** | 미지원 |

---

## Q13-1. 코드는 어디서 가져오는가 — Git Provider 토큰이 필요한가 {#q13-1}

| 구분 | 위치 | 식별자 | 확인 내용 | 검증 |
|---|---|---|---|---|
| 입력 플래그 | `cmd/opencodereview/flags.go:121-135` | `parseReviewFlags` | 입력은 `--repo`(로컬 경로), `--from/--to`(ref), `--commit`, `--rule`, `--tools`, `--model` 등. **URL·PR 번호·토큰 플래그 없음** | 코드 확인 |
| git 저장소 검증 | `cmd/opencodereview/review_cmd.go:33-35`, `:193-223` | `requireGitRepo`, `resolveRepoDir` | `git -C <dir> rev-parse --git-dir`로 로컬 저장소인지만 확인. 아니면 `... is not a git repository, code review requires a valid git repository` 오류 | 코드 확인 |
| git 호출 래퍼 | `internal/gitcmd/runner.go:43-127` | `Runner.Run/Output/RunSplit/Stream` | `exec.CommandContext(ctx, "git", args...)` + `cmd.Dir = repoDir`. **`cmd.Env`를 설정하지 않는다**(부모 환경 상속) | 코드 확인 |
| diff 생성 | `internal/diff/git.go:118`, `:125`, `:268`, `:275` | `GetDiff`, `workspaceTrackedDiff` | `git diff`(range/workspace), `git show`(commit), `git diff --staged` | 코드 확인 |
| merge-base·미추적 | `internal/diff/git.go:260`, `:317` | `computeMergeBase`, `untrackedFilesList` | `git merge-base`, `git ls-files --others --exclude-standard` | 코드 확인 |
| 파일 원문 | `internal/diff/parser.go:103-111`, `internal/tool/filereader.go:119-134` | `finalizeDiff`, `readFromGitShow` | `git show <ref>:<path>` (ref 모드). workspace 모드는 디스크 읽기(`filereader.go:79-89`) | 코드 확인 |
| 탐색 도구 | `internal/tool/code_search.go:52-78`, `internal/tool/file_find.go:73-78` | `buildGrepArgs`, `listGitFiles` | `git grep`, `git ls-tree`/`git ls-files` | 코드 확인 |
| 보조 호출 | `cmd/opencodereview/git.go:9-21`, `internal/agent/util.go:106-107` | `runGitCmd`, `detectGitBranch` | `git log -1`, `git rev-parse` | 코드 확인 |
| 엔진 전체의 서브커맨드 | 위 모든 git 호출 | - | 쓰이는 서브커맨드는 `diff, show, merge-base, ls-files, ls-tree, grep, log, rev-parse`뿐. **`clone, fetch, pull, push, remote, ls-remote`를 호출하는 코드 없음**(`"clone"/"fetch"/"remote"/"ls-remote"` 문자열 검색 결과 없음, 검색 범위 `cmd/`, `internal/` 비테스트 Go) | 코드 확인 |
| HTTP 클라이언트 | `internal/viewer/*.go` 외 | - | `net/http` 임포트는 `internal/viewer`(로컬 세션 뷰어 서버)뿐. 엔진의 외부 HTTP는 LLM SDK(`internal/llm/client.go`)와 OTLP gRPC(`internal/telemetry/exporter.go`)뿐 | 코드 확인 |
| GitHub/GitLab 문자열 | `cmd/`, `internal/` 전체 | - | `api.github.com`, `PRIVATE-TOKEN`, `GITHUB_TOKEN`, `GITLAB` 등 **엔진 소스에 없음**(`github.com`은 import 경로·안내문·`version.go:24`뿐) | 코드 확인 |

**결론**: 이 도구는 **로컬 git 저장소가 유일한 입력**이다. PR/MR 조회, clone, fetch, 댓글 게시를 엔진이 하지 않으므로 **엔진 자체에는 Git Provider 자격증명(PAT, App 토큰, OAuth, `CI_JOB_TOKEN`)이 필요 없다.** 토큰이 등장하는 곳은 예제 YAML(`examples/`)의 "게시" 단계뿐이다(아래 Q13-6).

기능 지원 수준: 원격 PR/MR 조회·clone·게시 **미지원**(찾은 범위: `cmd/`, `internal/` 전체 비테스트 Go의 git 서브커맨드 목록, HTTP 사용처, GitHub/GitLab 문자열). 예제 YAML 게시는 **부분 지원**. 기존 [01 Q1](01-execution-and-diff.md)·[04 10.1](04-saas-and-isolation.md)의 결론과 일치.

---

## Q13-2. 비공개 저장소를 리뷰하려면 사용자가 무엇을 하는가 {#q13-2}

### 사용자가 해야 하는 일 (코드 근거로 도출)

1. **`ocr review`를 실행하는 호스트에 대상 저장소의 로컬 체크아웃이 이미 있어야 한다.** 엔진은 `--repo`(기본 `os.Getwd()`)가 git 저장소인지만 확인한다(`review_cmd.go:193-223`). 비공개 저장소 접근 권한은 clone을 한 사람/CI가 해결한다(엔진 밖). 근거: Q13-1 표. 코드 확인.
2. **range 모드(`--from`, `--to`)라면 두 ref가 로컬에 존재해야 한다.** `validateReviewRefs`가 `git rev-parse --verify --end-of-options <ref>^{commit}`로 검사하고 없으면 오류로 중단한다(`review_cmd.go:225-250`). 엔진은 누락 ref를 fetch하지 않는다. 그래서 예제 YAML이 `fetch-depth: 0`과 `git fetch origin pull/N/head`를 **엔진 밖에서** 실행한다(`examples/github_actions/ocr-review.yml:64-71`, `examples/gitlab_ci/.gitlab-ci.yml:32-33`). 코드 확인.
3. **LLM 키는 별도로 설정한다**(Q13-3).

### git 실행 시 환경변수·credential helper 상속

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 환경 상속 | 모든 git 호출이 `cmd.Env`를 설정하지 않아 **부모 프로세스 환경을 그대로 상속**한다. `GIT_*`, `HOME`(→ `~/.gitconfig`), `GIT_ASKPASS` 등이 자식 git에 전달된다. 엔진이 환경을 정제하거나 `GIT_TERMINAL_PROMPT=0` 같은 값을 주입하는 코드 없음 | `internal/gitcmd/runner.go:50-53`, `:63-65`, `:75-77`, `:96-98`; `internal/diff/git.go:339-341`; `cmd/opencodereview/git.go:11-12` (`os.Environ`·`Setenv`·`cmd.Env` 검색 결과 `cmd/`, `internal/`에 없음) | 코드 확인 |
| credential helper 사용 | 쓰이는 서브커맨드(diff/show/merge-base/ls-files/ls-tree/grep/log/rev-parse)는 **로컬 객체 DB만 읽으므로 정상 상황에서 네트워크 인증(credential helper)이 호출되지 않는다.** helper·URL·헤더에 토큰을 넣는 코드도 없다 | Q13-1 표 | 코드 확인 |
| 예외 가능성 | **부분 clone(`--filter=blob:none` 등)** 체크아웃에서 `git show`/`git grep`이 누락 blob을 만나면 git이 자체적으로 원격에서 lazy fetch를 시도하고 이때 상속된 credential 설정이 쓰일 수 있다. 엔진 코드가 직접 하는 일은 아니며 git 동작에 대한 일반 지식 기반 | `internal/tool/filereader.go:119-134` 등 | 추론 |
| `.git/config` 토큰 | 엔진은 `.git/config`를 읽거나 쓰지 않는다. clone을 하지 않으므로 URL에 토큰이 박히는 경로가 엔진엔 없다(clone 주체의 책임) | Q13-1 표 | 코드 확인(부재) |

기능 지원 수준: 비공개 저장소 접근은 **엔진 책임 아님(해당 없음)**. 엔진은 "이미 접근 가능한 로컬 체크아웃"을 전제한다.

---

## Q13-3. LLM API 키 주입 경로 {#q13-3}

### 3.1 해석 순서

`runReview`는 `defaultConfigPath()`(`~/.opencodereview/config.json`)를 읽고 `llm.ResolveEndpointWithModelOverride(cfgPath, opts.model)`로 엔드포인트를 해석한다(`review_cmd.go:78-98`). **설정 파일 경로를 바꾸는 플래그는 없다**(`flags.go:121-135`). 해석은 4개 전략을 순서대로 시도해 **URL·토큰·모델이 모두 채워진 첫 전략**을 쓴다(`internal/llm/resolver.go:49-77`).

| 순위 | 전략 | 키가 오는 곳 | 위치 | 비고 | 검증 |
|---|---|---|---|---|---|
| 1 | OCR config file | `provider` 설정 시: `providers.<name>.api_key` 또는 `custom_providers.<name>.api_key`, 비어 있으면 **프리셋별 환경변수 폴백**. `provider` 미설정 시: 레거시 `llm.auth_token` | `resolver.go:147-165`, `:169-195`, `:293-325` | `provider`가 설정됐는데 키가 없으면 **다음 전략으로 넘어가지 않고 오류 반환**(`:193-195`, `:62-66`). 레거시 `llm` 블록은 필드가 비면 다음 전략으로 넘어감(`:298-300`) | 코드 확인 |
| 2 | OCR environment | `OCR_LLM_URL`, `OCR_LLM_TOKEN`, `OCR_LLM_MODEL`, `OCR_LLM_AUTH_HEADER`, `OCR_USE_ANTHROPIC` | `resolver.go:24-30`, `:80-115` | 세 값이 모두 있어야 성립 | 코드 확인 |
| 3 | Claude Code environment | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` | `resolver.go:33-37`, `:328-343` | 항상 `authorization`(Bearer) 헤더. **`ANTHROPIC_API_KEY`는 이 전략에서 읽지 않는다** | 코드 확인 |
| 4 | Shell rc file | `~/.zshrc`, `~/.bashrc`, `~/.bash_profile`, `~/.profile`을 읽어 `export ANTHROPIC_*=...` 줄을 정규식으로 파싱 | `resolver.go:346-429` (`exportRe` `:377`) | rc 파일의 **평문 토큰을 직접 읽는다.** 변수 확장(`$FOO`)은 하지 않고 문자열 그대로 취함 | 코드 확인 |

프리셋 제공자의 폴백 환경변수(전략 1에서 `provider`+프리셋 선택 시에만 사용): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, `DASHSCOPE_TOKENPLAN_KEY`, `ARK_API_KEY`, `DEEPSEEK_API_KEY`, `TENCENT_TOKENHUB_API_KEY`, `TENCENT_HUNYUAN_TOKENPLAN_KEY`, `MOONSHOT_API_KEY`, `Z_AI_API_KEY`, `MIMO_API_KEY`, `MINIMAX_API_KEY`(`internal/llm/providers.go:19-170`, 폴백 적용 `resolver.go:187-192`). 코드 확인.

**실무상 함정(코드 확인)**: ① 설정 파일에 유효한 엔드포인트가 있으면 환경변수가 무시된다(`resolver.go:56-59`, `:62-74`). README는 "Environment variables (highest priority)"라고 적었지만 코드는 반대다(8절). ② `ANTHROPIC_API_KEY`만 export하고 `ocr config set provider anthropic`을 하지 않으면 전략 3이 성립하지 않아 `no valid LLM endpoint configured` 오류가 난다(`resolver.go:76`, `:328-337`). ③ `--preview`는 LLM 설정을 읽기 전에 반환하므로 키 없이 동작한다(`review_cmd.go:62-69` → `:78-98`).

### 3.2 헤더와 SDK 전달

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| Anthropic 프로토콜 | `authorization`이면 `option.WithAuthToken`(Bearer), `x-api-key`이면 `option.WithAPIKey`, 그 외 임의 헤더명이면 `WithHeader`. 반대편 기본 헤더는 삭제 | `internal/llm/client.go:486-511` | 코드 확인 |
| OpenAI 프로토콜 | `openaiopt.WithAPIKey(cfg.APIKey)` + `WithBaseURL` | `internal/llm/client.go:283-304` | 코드 확인 |
| 요청 대상 | **사용자가 정한 URL**(프리셋 `BaseURL` 또는 `custom_providers.<name>.url`/`llm.url`)로 소스가 전송된다. 사내 게이트웨이·프록시도 가능 | `resolver.go:200-220`, `client.go:194-206` | 코드 확인 |
| SDK 자체의 환경변수 기본값 | Anthropic/OpenAI Go SDK가 `ANTHROPIC_API_KEY`·`OPENAI_API_KEY` 등을 클라이언트 생성 시 자동으로 읽는지 | SDK 소스(모듈 캐시에 없어 열지 못함) | **미확인.** 코드는 어떤 경우든 `option.WithAPIKey/WithAuthToken`으로 명시 값을 덮어쓰고 반대 헤더를 지운다(`client.go:500-511`) |

### 3.3 설정 파일: 위치·권한·평문·마스킹

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 위치 | `$HOME/.opencodereview/config.json` (`os.UserHomeDir`). 고정 경로, 변경 플래그 없음 | `cmd/opencodereview/config_cmd.go:14-21` | 코드 확인 |
| 평문 | 키는 JSON 평문 필드: `providers.<name>.api_key`, `custom_providers.<name>.api_key`, `llm.auth_token`. 암호화·키체인·시크릿 매니저 코드 없음 | `config_cmd.go:84-112`, `internal/llm/resolver.go:117-144` | 코드 확인 |
| 권한 | 파일은 `0600`으로 쓰고 `os.Chmod(path, 0o600)`로 재확인. 그러나 **디렉터리 `~/.opencodereview`는 `MkdirAll(..., 0o755)`**(config 쪽 생성 시). 세션 쪽 생성 시는 `0700`(`persist.go:99`). 먼저 만든 쪽 권한이 부모 디렉터리에 남음 | `cmd/opencodereview/provider_cmd.go:277-293`, `internal/session/persist.go:98-107` | 코드 확인 |
| 기록 방법 | `ocr config set providers.<name>.api_key <값>`는 **값을 argv로 받는다**(셸 히스토리·프로세스 목록에 노출 가능, 일반 OS 동작 기반). 도움말은 환경변수 사용을 "recommended"라 하면서도 예시는 `"$ANTHROPIC_API_KEY"`를 `config set`에 넘겨 **결국 파일에 평문 저장**한다. 대화형 `ocr config provider`는 TUI 입력이 `EchoPassword`(`*` 표시) | `cmd/opencodereview/flags.go:274-300`, `config_cmd.go:153-251`, `provider_tui.go:143-147`, `:177-181` | 코드 확인, argv 노출은 추론 |
| 마스킹 | `config set`이 키 이름이 `apikey`/`authtoken`으로 끝나면 출력값을 `maskKey`로 가림: 8자 이하는 `***`, 그 외 **앞 4자 + `***` + 뒤 4자**. 이 마스킹은 **표시용 한 곳뿐**이다 | `config_cmd.go:55-81`, `provider_cmd.go:295-303` | 코드 확인 |
| 출력 시 유출 | `ocr llm test`는 `Source`, `URL`, `Model`만 출력하고 토큰은 출력하지 않음. 엔진 코드에 키를 로그·에러 메시지에 넣는 곳이 없음 | `cmd/opencodereview/llm_cmd.go:86-88`; `Token`/`APIKey` 사용처는 `client.go`·설정 저장 코드뿐 | 코드 확인 |
| 에러 문자열의 키 포함 여부 | LLM SDK가 반환하는 오류 문자열(`err.Error()`)에 요청 정보가 얼마나 들어가는지. 이 문자열은 세션 JSONL(`history.go:282-292`), 결과 JSON `warnings`(`agent.go:423`), 콘솔(`agent.go:420`), OTel(`agent.go:421-422`)로 간다. **엔진에는 redaction 코드가 없다**(`redact`/`mask`/`sanitize` 검색: `sanitizeTerminal`(터미널 제어문자 제거, `output.go:150`)과 `maskKey`(표시용)뿐) | `internal/session/history.go:282-292`, `internal/agent/agent.go:418-425` | 코드 확인(redaction 부재), SDK 오류 내용은 **미확인** |

기능 지원 수준: LLM 키 주입은 **지원**(env·설정 파일·셸 rc, 평문). CLI 키 플래그·시크릿 매니저·키체인은 **미지원**(찾은 범위: `flags.go` 전체 플래그, `go.mod`, `cmd/`·`internal/`에서 `keyring|keychain|vault|kms|secret` 검색).

---

## Q13-4. 소스 코드와 키가 어디로 전송·기록되는가 {#q13-4}

### 4.1 외부 전송 및 기록 경로 목록

| # | 경로 | 보내거나 쓰는 것 | 기본값 | 끌 수 있는가 | 위치 | 검증 |
|---|---|---|---|---|---|---|
| 1 | **LLM API 호출** | 시스템 규칙, diff, `--background`/커밋 메시지, 도구가 읽은 파일 원문, 대화 누적. 인증 헤더에 키 | 항상(리뷰의 본질) | 아니오 | `internal/llm/client.go:194-206`; `review_cmd.go:56-60`(`--commit`이면 커밋 메시지를 background로 채움) | 코드 확인 |
| 2 | **세션 JSONL (로컬 디스크)** | `llm_request`의 **전체 메시지**(규칙·diff·도구 결과=파일 원문), `llm_response` 내용·도구 호출 인자, `tool_call` 인자·결과, `llm_error` 오류 문자열, `cwd`·브랜치·모델 | 항상 | **아니오** | 아래 4.2 | 코드 확인 |
| 3 | **OpenTelemetry** (span/metric) | 아래 4.3 | **꺼짐**(`OCR_ENABLE_TELEMETRY=1` 또는 `telemetry.enabled`일 때만) | 기본이 꺼짐 | `internal/telemetry/config.go:40-59`, `provider.go:28-62` | 코드 확인 |
| 4 | 터미널(stdout/stderr) | 진행 로그, 도구 호출 요약(경로·검색어), 서브태스크 오류 | 항상(`--format json`/`--audience agent`면 stdout 억제) | 부분(`stdout.Quiet`) | `internal/telemetry/events.go:84-129`, `agent.go:420`, `review_cmd.go:135-144` | 코드 확인 |
| 5 | 결과 JSON/텍스트 | 코멘트, `existing_code`, `suggestion_code`, warnings(오류 문자열 포함) | 호출자가 받음 | - | `review_cmd.go:181-188`, `agent.go:423` | 코드 확인 |
| 6 | **세션 뷰어 HTTP 서버** | JSONL 전체를 브라우저에 서빙. 인증 없음, Host 헤더 허용 목록만. 기본 `localhost:5483`, `--addr :3000`이면 전 인터페이스 바인드 | `ocr viewer` 실행 시만 | 실행 안 하면 없음 | `cmd/opencodereview/viewer_cmd.go:18`, `:50-54`; `internal/viewer/server.go:15-63`, `hostguard.go:10-12` | 코드 확인 |
| 7 | git 네트워크 | 없음(Q13-1) | - | - | - | 코드 확인 |
| 8 | npm 래퍼의 자체 업데이트·바이너리 다운로드 | 엔진 데이터와 무관. 버전 조회(`registry.npmjs.org`)·릴리스 다운로드 | `OCR_NO_UPDATE` 미설정 시 | `OCR_NO_UPDATE` | `bin/ocr.js:20-45`, `scripts/update.js:27`, `package.json:27-28` | 코드 확인(상세 미열람) |

Anthropic/OpenAI 호출은 **키 외에는 호출자 지정 URL 하나로만 간다.** 다른 텔레메트리·분석 서비스로 보내는 코드는 찾지 못했다(`cmd/`, `internal/`에서 외부 HTTP 클라이언트는 LLM SDK와 OTLP gRPC뿐).

### 4.2 세션 JSONL: 소스는 평문, 키는 기록 코드 없음 (기존 결론 재확인)

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 항상 생성 | `agent.New`는 `Args.Session`이 비면 `session.New(...)`를 호출한다. `ocr review`는 세션을 넘기지 않는다 | `internal/agent/agent.go:186-198`, `cmd/opencodereview/review_cmd.go:114-133` | 코드 확인 |
| `--preview`도 생성 | `runPreview`도 `agent.New`를 호출하므로 세션 파일이 열린다(이 경우 LLM 레코드는 없음) | `review_cmd.go:252-261`, `agent.go:186-198` | 코드 확인 |
| 위치·권한 | `$HOME/.opencodereview/sessions/<repo 경로 인코딩>/<UUID>.jsonl`, 디렉터리 `0700`, 파일 `0600`, `O_TRUNC`. 열기 실패 시 경고만 출력하고 **리뷰는 계속** | `internal/session/persist.go:92-112`, `history.go:120-126` | 코드 확인 |
| 끄는 옵션 | 없음. 환경변수·플래그·설정 키로 세션 기록을 끄는 코드를 찾지 못함 | `flags.go:121-135`, `config_cmd.go:95-103`(Config 필드: provider/model/providers/custom_providers/llm/language/telemetry) | 코드 확인 |
| 요청 기록 | `llm_request.messages`에 **role/content 전체**(도구 결과 포함). 도구 결과에는 `file_read`가 읽은 **파일 전체 원문**이 들어간다 | `history.go:171-188`, `:205-221`, `:299-313`; `persist.go:157-177`, `:232-255` | 코드 확인 |
| 응답·오류 기록 | `llm_response`(content, tool_calls 인자, usage), `llm_error`(오류 문자열) | `persist.go:179-230`, `history.go:226-292` | 코드 확인 |
| **키·토큰 기록 여부** | `session_start`는 `cwd`, `gitBranch`, `model`, 리뷰 모드·ref만 기록. **엔드포인트 URL·API 키·인증 헤더 필드는 레코드에 없다.** 단 다음 경우 키/비밀이 남을 수 있다: ① 리뷰 대상 파일·diff에 하드코딩된 시크릿(`.env` 등 포함 가능, 아래), ② `--background`·규칙 파일에 사용자가 넣은 값, ③ SDK 오류 문자열(미확인) | `persist.go:124-155` | 코드 확인(필드 부재) / ①②는 코드 정황, ③ 미확인 |
| 민감 파일 필터 | **없음.** 제외는 하드코딩 디렉터리(`.git/`, `vendor/`, `node_modules/` 등)와 `.gitignore`뿐. workspace 모드는 **gitignore되지 않은 미추적 파일 전체**를 diff로 만든다(`.env`가 ignore되지 않았다면 포함). 파일 읽기 도구는 저장소 밖 경로를 거부하지만 저장소 안 파일은 제한 없음 | `internal/diff/git.go:19-33`, `:278-314`, `internal/tool/filereader.go:91-112` | 코드 확인 |
| 보존·삭제 | 세션 파일을 삭제·만료시키는 코드 없음(`internal/session`, `internal/viewer`, `cmd/`에서 `os.Remove`/`RemoveAll`/보존기간 검색 결과 없음) | - | 코드 확인(부재) |
| 소스의 자기 인정 | 뷰어 주석: JSONL은 "LLM request bodies = source code being reviewed and the LLM's analysis of it" | `internal/viewer/server.go:49-52` | 코드 확인 |

기존 [04 C절](04-saas-and-isolation.md)의 "끌 수 없는 세션 로그, 소스 평문 기록" 결론은 **그대로 맞다.** 추가로 확인한 것: 키 자체는 기록 필드에 없지만 **보존·삭제·민감 파일 필터가 없다**.

### 4.3 OpenTelemetry로 나가는 데이터

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 활성 조건 | 기본 꺼짐. `OCR_ENABLE_TELEMETRY=1` 또는 `config.json`의 `telemetry.enabled`. 켜지면 기본 exporter는 `console`(stdout 출력), `OTEL_EXPORTER_OTLP_ENDPOINT` 또는 `telemetry.otlp_endpoint`가 있으면 `otlp`(gRPC) | `internal/telemetry/config.go:11-16`, `:42-59`, `:90-105`; `provider.go:28-56` | 코드 확인 |
| 프로토콜 | `OTEL_EXPORTER_OTLP_PROTOCOL`을 읽어 `cfg.OTLPProtocol`에 저장하지만 **어디서도 쓰이지 않는다.** exporter는 gRPC 전용. `WithInsecure`/TLS 옵션 설정 코드도 없음(전송 보안은 SDK 기본값 의존) | `config.go:53-55`; `exporter.go:29-60` (`OTLPProtocol` 사용처 없음) | 코드 확인; TLS 기본값은 **미확인** |
| span/event 속성 | `repo.dir`(절대 경로, `review.started`), 파일 경로(`file.path`, span 이름 `subtask.execute.<path>`), 줄 수, 토큰 수, 단계명, **오류 문자열**(`subtask.error`, `plan.failed`의 `err.Error()`, `review.run`의 `error`), 도구 이름 | `agent.go:236-241`, `:418-425`, `:449-454`, `:472-490`, `:523-530`; `review_cmd.go:146-153`; `telemetry/events.go:35-61` | 코드 확인 |
| metric 속성 | `model`, `status`, `tool.name`, 토큰 합계·시간 | `internal/telemetry/metrics.go:102-140` | 코드 확인 |
| **프롬프트·소스 본문** | span/metric 속성에 **diff·파일 원문·프롬프트를 넣는 코드를 찾지 못했다.** | `internal/telemetry/*.go`, `agent.go`의 `telemetry.*` 호출 전부 | 코드 확인 |
| `content_logging` | `OCR_CONTENT_LOGGING=1`/`telemetry.content_logging`을 `cfg.ContentLog`로 읽고 `telemetry.ContentLogging()`을 정의하지만 **호출하는 곳이 없다**(`cmd/`, `internal/` 전체 검색). README는 이 옵션이 "프롬프트·응답을 내보낸다"고 설명 → 이 SHA에서는 **효과 없는 설정**(8절). 또 `ContentLogging()`은 `ResolveConfig("")`로 JSON 설정을 건너뛰어 env만 반영 | `provider.go:69-76`, `config.go:56-58`; `README.md:520` | 코드 확인 |
| 리소스 속성 | `resource.WithFromEnv/WithProcess/WithOS/WithHost`로 프로세스·OS·호스트 정보가 모든 span/metric에 붙는다. `WithProcess`가 **명령행 인자(`process.command_args`)를 포함하는지**는 OTel SDK 동작에 따른다(SDK 소스 미열람, 알려진 동작 기반으로는 포함 가능). 포함된다면 `--background` 값이 OTLP 수집기로 나간다 | `provider.go:40-45` | 추론(SDK 미열람) |
| 인증 헤더 | OTLP 수집기 인증은 코드에 없다. `OTEL_EXPORTER_OTLP_HEADERS` 같은 SDK 표준 환경변수 처리 여부는 SDK 의존 | `exporter.go:29-60` | 미확인 |

**정리**: OTel을 켜도 소스 본문과 키는 나가지 않는 것으로 보이나(속성에 없음), **파일 경로·저장소 절대경로·오류 문자열**이 외부 수집기로 나간다. 기본은 꺼짐이므로 "OTel이 소스를 보낸다"는 일반론은 이 SHA에서는 틀리다.

---

## Q13-5. AWS·MCP·기타 자격증명 경로 {#q13-5}

| 항목 | 결과 | 찾아본 범위 | 검증 |
|---|---|---|---|
| `aws-sdk-go-v2` / Bedrock / SigV4 | **없음** | `go.mod:5-22`(직접 의존 16개)와 간접 의존 블록 전체, `go.sum`에서 `aws|bedrock|modelcontext|mcp|keyring|keychain` 검색 결과 없음. `cmd/`, `internal/` 비테스트 Go에서 `\baws\b|aws-sdk|bedrock|sigv4|\bmcp\b|vault|\bkms\b|keyring|keychain` 검색 결과 없음. 프로토콜 구현은 `anthropic`, `openai` 둘뿐(`internal/llm/client.go:192-206`) | 코드 확인(부재) |
| MCP 서버 토큰 | **없음** | `go.mod`·`go.sum`, 소스, `*.json|*.md|*.yml` 검색(`graphify-out/`·`pages/` 제외)에서 MCP 관련 결과 없음. 모델이 쓰는 도구는 코드에 고정(`internal/tool/definitions.go:13-21`): 모델 호출 가능 6개(`task_done, code_comment, file_read, file_find, file_read_diff, code_search`) + 내부 항목 `unknown` 1개 = `Tool` 값 7개(기준: [00 1절](00-overview.md)) | 코드 확인(부재). [05](05-dependencies.md)의 결론과 일치 |
| 명령 실행 도구 | 모델용 쉘/명령 실행 도구 없음. 도구는 읽기 전용 git/파일 접근(`buildToolRegistry`) | `cmd/opencodereview/review_cmd.go:272-280`, `definitions.go:13-21` | 코드 확인 |
| 시크릿 매니저·키체인·암호화 저장 | **없음** | 위 검색 + `config_cmd.go`·`provider_cmd.go`의 저장 코드(평문 JSON) | 코드 확인(부재) |
| `standard-webhooks` 간접 의존 | go.mod에 간접 의존(`github.com/standard-webhooks/standard-webhooks/libraries`)이 있으나 `cmd/`·`internal/`에서 import하지 않음. 웹훅 서명 검증 기능이 아님(SDK의 간접 의존으로 추정) | `go.mod` 간접 의존 블록, `cmd/`·`internal/` 임포트 | 코드 확인(미사용) / 출처는 추론 |
| 웹훅 시크릿 | 없음(웹훅 수신 코드 없음) | [04 10.1](04-saas-and-isolation.md) | 코드 확인(부재) |

기능 지원 수준: AWS/Bedrock·MCP 토큰·시크릿 매니저 **미지원**. 기존 보고서가 맞다.

---

## Q13-6. 실행 형태별 자격증명 차이 {#q13-6}

| 실행 형태 | Git 쪽 자격증명 | LLM 키 | 소스·키 보관 위치 | 위치 | 검증 |
|---|---|---|---|---|---|
| **로컬 CLI (`ocr review`)** | 없음(로컬 체크아웃 전제) | env / `~/.opencodereview/config.json` / 셸 rc | 세션 JSONL이 사용자 홈에 평문 누적 | Q13-1~4 | 코드 확인 |
| **GitHub Actions 예제** | 체크아웃·`git fetch origin pull/N/head`는 워크플로 단계(`actions/checkout`의 기본 인증, 파일에 명시 안 됨). 게시는 `secrets.GITHUB_TOKEN`, 권한 `contents: read`, `pull-requests: write` | `secrets.OCR_LLM_URL`, `secrets.OCR_LLM_AUTH_TOKEN`(`OCR_LLM_MODEL`·`OCR_LLM_USE_ANTHROPIC`) → **`ocr config set llm.auth_token ${{ secrets.… }}`로 러너의 `~/.opencodereview/config.json`에 평문 기록**(argv 전달) | 러너 홈의 config·세션 JSONL(러너 폐기 시 소멸), 결과 JSON은 `/tmp/ocr-result.json` | `examples/github_actions/ocr-review.yml:10-17`, `:34-36`, `:64-71`, `:81-87`, `:117-120` | 코드 확인 |
| **GitLab CI 예제** | 게시는 `GITLAB_API_TOKEN`(주석: PAT/프로젝트 토큰, `api` scope) 우선, 없으면 `CI_JOB_TOKEN`. 헤더는 각각 `PRIVATE-TOKEN` / `JOB-TOKEN`. 체크아웃은 러너 기본(`GIT_DEPTH: 0`) | `OCR_LLM_AUTH_TOKEN`(주석: "Masked" 권장) → `ocr config set llm.auth_token $OCR_LLM_AUTH_TOKEN` | 위와 동일(컨테이너 `node:20` 내부) | `examples/gitlab_ci/.gitlab-ci.yml:7-14`, `:32-33`, `:42-46`, `:69-86`, `:191` | 코드 확인 |
| **웹훅 서버 / SaaS** | 해당 코드 없음 | - | - | [04 10.1](04-saas-and-isolation.md) | 코드 확인(부재) |

예제 관련 관찰:
- GitHub 예제는 `pull_request_target`(시크릿 접근 가능)에서 **PR head SHA를 체크아웃**한다. 예제 주석은 "OCR은 diff만 읽고 코드를 실행하지 않아 안전"이라 설명한다(`ocr-review.yml:26-28`). 엔진은 PR 코드를 실행하지 않지만, **PR head 작업 트리의 `<repo>/.opencodereview/rule.json`을 로드**하므로(`internal/config/rules/system_rules.go:339-353`, [03 Q8](03-incremental-memory-rules.md#q8)) 포크 PR 작성자가 리뷰 프롬프트(규칙)를 바꿀 수 있다. LLM 키 자체는 range 모드의 파일 읽기가 `git show`(`filereader.go:68-77`)이고 도구가 저장소 밖 경로를 거부해(`filereader.go:91-112`) 모델이 `~/.opencodereview/config.json`을 읽을 도구는 없다. 따라서 키 유출보다 **프롬프트 주입으로 리뷰 품질 조작** 쪽이 위험이다(추론: 도구 목록과 경로 가드 기반).
- 두 예제 모두 `ocr` 실패 시 stderr 내용을 PR/MR 댓글로 게시한다(`ocr-review.yml:130-141`, `.gitlab-ci.yml:165-175`). 엔진에 오류 문자열 redaction이 없으므로(Q13-3.3) 오류에 포함된 정보는 그대로 공개 댓글이 된다(추론).
- `.gitlab-ci.yml:39`의 `mkdir -p ~/.open-code-review`는 엔진이 쓰는 `~/.opencodereview`(점·하이픈 없음)와 이름이 다르다(무해하지만 오타로 보임, 코드 확인).

---

## 의견: 서비스 워커에서 여러 팀의 비공개 저장소를 리뷰하려면 {#opinion}

> 아래는 **분석자 의견**이며 코드 근거는 위 표에만 있다. 근거 문서: [04](04-saas-and-isolation.md), [06 Q12](06-fit.md#q12).

1. **엔진은 "토큰 없는 로컬 git 소비자"로 쓰는 것이 자연스럽다.** 엔진이 clone·fetch·게시를 하지 않으므로, 토큰 처리는 **엔진 바깥 오케스트레이터**가 맡는 구조가 된다. 즉 엔진에 Provider 토큰 처리를 억지로 이식하기보다 "워커가 체크아웃을 준비해 주고 엔진은 읽기만"으로 경계를 유지한다.
2. **Git 토큰 수명·범위는 워커가 관리한다.** GitHub는 팀별 App 설치 토큰(저장소 한정, 약 1시간 수명, 필요한 권한 `contents:read`, 게시용 `pull_requests:write`)을 리뷰 작업 시작 시 발급하고 작업 종료와 함께 폐기, GitLab은 프로젝트/그룹 토큰을 시크릿 매니저·암호화 저장소에서 팀별로 조회. 토큰을 DB에 평문으로 두지 않는다. (수명·권한 값은 각 플랫폼 일반 지식이며 이 레포 근거 아님.)
3. **clone/fetch 시 토큰이 `.git/config`·URL에 남지 않게 한다.** `-c http.extraheader=...`나 일회용 `GIT_ASKPASS`로 주입하고, 작업 디렉터리는 **작업 단위 임시 경로**(테넌트·PR·SHA별)로 만들어 리뷰 후 삭제한다. 엔진은 부모 환경을 그대로 상속하므로(`runner.go:50-53`), 워커 프로세스 환경에 다른 테넌트 토큰이 섞이지 않게 **리뷰 프로세스 단위로 격리**한다(작업마다 별도 프로세스·컨테이너). 이 조언은 git 일반 동작 기반이다.
4. **LLM 키는 팀별로 주입하되 설정 파일 경로를 쓰지 않는다.** CLI 바이너리를 쓴다면 작업별 `HOME`을 임시 디렉터리로 지정해(Go의 `os.UserHomeDir`는 Unix에서 `$HOME`을 따름, 일반 지식) `~/.opencodereview/config.json`·`rule.json`·세션 로그가 테넌트 간에 섞이지 않게 하고, 키는 `OCR_LLM_TOKEN`으로 전달하되 설정 파일이 없어야 환경변수가 적용되는 점을 지킨다(`resolver.go:56-74`). 더 나은 방법은 포크해서 `llm.ResolvedEndpoint`를 서비스가 직접 채워 `llm.NewLLMClient(ep)`에 넘기는 것이다(`client.go:194-206`, [04 F절](04-saas-and-isolation.md)). 팀별 키를 아예 두지 않고 **사내 LLM 게이트웨이**가 팀별 키·쿼터를 처리하게 하고 엔진에는 게이트웨이 URL만 주는 방식도 `custom_providers.<name>.url`로 가능하다(`resolver.go:210-220`).
5. **세션 로그는 서비스에서 반드시 막아야 한다.** 소스 평문이 홈 디렉터리에 누적되고(4.2절) 끌 수 없으므로, 작업별 `HOME`을 쓰고 작업 종료 시 통째로 삭제하거나, 포크해서 세션 싱크를 주입형으로 바꾼다. 키·토큰은 기록 필드에 없지만 **민감 파일 필터가 없으므로** 워커 쪽에서 `.env`류 제외 규칙과 시크릿 스캐너를 앞단에 둔다.
6. **새로 만들어야 하는 것**: 테넌트별 토큰 저장·발급·폐기, 웹훅 서명 검증, 오류 문자열 redaction(댓글·로그 게시 전), 게시 어댑터(GitHub `createReview`, GitLab discussions — 예제 YAML 로직을 참고), 감사 로그. 엔진에서 가져올 것은 읽기 전용 탐색·루프 골격까지다.
7. **OTel**을 쓴다면 속성에 파일 경로·저장소 경로·오류 문자열이 실리므로(4.3절) 테넌트 식별자를 리소스 속성으로 붙이고 수집기 접근을 제한한다. 이 SHA에서는 `content_logging`이 무효이므로 프롬프트 수집이 필요하면 직접 구현해야 한다.

---

## 기존 보고서와 다른 점 {#diff-from-existing}

**정정 반영됨(2026-10-13)**: 아래 4번(content_logging)은 [03 7.4](03-incremental-memory-rules.md)·[04 D절](04-saas-and-isolation.md)·[00 4절](00-overview.md)에, 5번(env 우선순위)·4번은 [05 README↔코드 표](05-dependencies.md)·[00 4절](00-overview.md)·[next.md](next.md)에, 7번(도구 개수 표기)은 전 문서에 반영했다.

| # | 기존 서술 | 이번 확인 | 위치 | 영향 |
|---|---|---|---|---|
| 1 | [04 C절](04-saas-and-isolation.md): "`runReview`가 홈 디렉터리 설정을 **항상** 읽음" | `--preview`는 LLM 설정을 읽기 전에 반환한다. 그러나 `agent.New`가 세션 파일은 연다 | `review_cmd.go:62-69`, `:78-98`, `:252-261`, `agent.go:186-198` | 사소. 미리보기에는 키 불필요 |
| 2 | [04 D절](04-saas-and-isolation.md) 우선순위 함정: "설정 파일에 유효 엔드포인트가 있으면 환경변수가 무시" | 맞음. 추가로 `provider`가 설정된 상태에서 키가 없으면 **오류로 중단**(다음 전략으로 안 넘어감), 레거시 `llm` 블록은 넘어감 | `resolver.go:62-66`, `:193-195`, `:298-300` | 보완 |
| 3 | [04 C절](04-saas-and-isolation.md): 설정 "파일 0600" | 파일은 0600이지만 `~/.opencodereview` 디렉터리는 config 쪽 생성 시 0755, 세션 쪽 생성 시 0700(생성 주체에 따라 달라짐) | `provider_cmd.go:277-293`, `persist.go:98-99` | 보완 |
| 4 | [04 D절](04-saas-and-isolation.md): "`OCR_ENABLE_TELEMETRY=1`, … `OCR_CONTENT_LOGGING=1`" 항목으로 나열 | `ContentLogging()`을 호출하는 곳이 없어 **content logging은 이 SHA에서 효과가 없다.** README는 프롬프트·응답을 내보낸다고 설명 | `provider.go:69-76`, `README.md:520` | **README와 코드 불일치.** [05의 README↔코드 표](05-dependencies.md)에 추가 후보 |
| 5 | (기존 문서에 없음) | README는 환경변수가 "highest priority"라 하지만 코드 우선순위는 설정 파일 > OCR env > Claude Code env > 셸 rc | `README.md:168-177` vs `resolver.go:56-59` | **README와 코드 불일치** |
| 6 | (기존 문서에 없음) | OTel `OTEL_EXPORTER_OTLP_PROTOCOL`은 읽히지만 쓰이지 않음(gRPC 고정) | `config.go:53-55`, `exporter.go:29-60` | 사소 |
| 7 | [05](05-dependencies.md)·[00](00-overview.md): AWS/MCP 없음 | 재확인, 동일. 도구 고정(모델 호출 가능 6개 + 내부 `Unknown` 1개 = `Tool` 값 7개)도 동일. 이전 "모델용 7종" 표기는 부정확해 정정 | `definitions.go:13-21`, `:32-34` | 표기 정정(7→6+1) |
| 8 | [04 C절](04-saas-and-isolation.md): 세션 로그 끌 수 없음·소스 평문 | 재확인, 동일. 키 필드는 레코드에 없음, 보존·삭제 코드 없음, 민감 파일 필터 없음을 추가 | `persist.go:92-155`, `internal/diff/git.go:19-33` | 보완 |

---

## 미확인 / 한계

| 항목 | 이유 | 다음에 볼 곳 |
|---|---|---|
| Anthropic/OpenAI Go SDK의 환경변수 자동 읽기, 오류 문자열 내용(요청 정보 포함 여부) | SDK 소스가 로컬 모듈 캐시에 없어 열지 못함(`go mod download`는 설치·실행 금지 범위라 하지 않음) | `github.com/anthropics/anthropic-sdk-go@v1.47.0`, `github.com/openai/openai-go/v3@v3.39.0`의 클라이언트 옵션·`apierror` |
| OTLP gRPC의 TLS 기본값, `OTEL_EXPORTER_OTLP_HEADERS` 처리, `WithProcess`의 `process.command_args` 포함 여부 | OTel SDK 소스 미열람 | `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc@v1.43.0`, `sdk/resource` |
| 부분 clone에서의 lazy fetch·credential 상속 실제 동작 | 실행하지 않음(정적 추적) | 실제 부분 clone 저장소에서 `ocr review` 실행 시 네트워크 호출 관찰 |
| `npm` 래퍼(`bin/ocr.js`, `scripts/*.js`)의 환경변수·네트워크 세부 | 이번 범위에서 엔진 데이터 경로가 아니라 일부만 열람(`bin/ocr.js:20-45`, `scripts/update.js:27`) | `scripts/install.js`, `update.js` 전체 |
