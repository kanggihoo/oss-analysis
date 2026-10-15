# open-code-review — 의존성

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q11
- 검증 수준 요약: 코드 확인 30 / 실행 확인 0 / 추론 0 / 미확인 1 (집계 기준: 이 문서 증거 표의 행 단위, 검증 칸 맨 앞 판정으로 분류(1행=1판정). 검증 칸 안에 보조로 병기된 추론·미확인은 괄호로 별도 표기. 설명 칸 안의 인라인 표기와 서술 문단은 집계 제외. 2026-10-13 정정: README↔코드 표에 2행 추가로 28→30)
- 실행 여부: 정적 추적만. `go list -m all`, `go mod graph`, `go build`를 실행하지 않았다(다운로드·캐시 변경 방지).

경로는 `code-review/repos/open-code-review/` 기준이다.

## 해석 버전을 어떻게 구했나 (범위 명시)

- **선언 버전** = `go.mod`의 `require`(직접 블록 `go.mod:5-22`, 간접 블록 `:24-67`). Go 모듈 요구는 "최소 버전"이다.
- **해석 버전**은 모듈 그래프 계산(`go list -m all`)으로 얻어야 하지만 실행하지 않았다. 대신 `go.sum`을 확인했다: 아래 직접 의존 전부가 `go.sum`에 **단일 버전**(소스 해시 `h1:` + `go.mod` 해시 각 1줄)으로만 존재하고 그 버전이 `go.mod` 선언과 같다(`go.sum:1-6`, `:7-8`, `:15-16`, `:68-69`, `:72-73`, `:96-97` 등). 이는 선택된 버전이 선언과 같다는 강한 정황이지만, **모듈 그래프 명령으로 직접 확인한 것은 아님**이다. 표의 "해석 버전"은 모두 이 기준(검증: 코드 확인 = 파일 대조, 그래프 실행은 미확인).
- Go 버전: `go 1.25.0` (`go.mod:3`). 빌드는 `CGO_ENABLED=0` 정적 바이너리 (`Makefile:22-26`, `.github/workflows/release.yml:40`, `:50`).
- 레포 안의 `graphify-out/`는 근거로 쓰지 않았다.

## 직접 의존 표

| 패키지 | 선언 버전 | 해석 버전 | 분류 | 호출 위치 | 역할 | 교체·제거 영향 | 근거 |
|---|---|---|---|---|---|---|---|
| `github.com/anthropics/anthropic-sdk-go` | v1.47.0 | v1.47.0 (`go.sum:7-8`) | 직접, 필수(Anthropic 프로토콜 선택 시), 런타임 | `internal/llm/client.go:13-14`, `:475-542`, `:545-653` | Messages API 요청 생성(system/user/assistant/tool_use/tool_result 블록, 캐시 컨트롤), 응답에서 text·thinking·tool_use 추출, 재시도 5회·타임아웃 설정 | 제거하면 Anthropic 프로토콜 불가. 대신 HTTP 직접 구현 필요. 루프·도구 실행은 자체 구현이라 SDK는 "요청/응답 변환+재시도"만 담당 | 코드 확인 |
| `github.com/openai/openai-go/v3` | v3.39.0 | v3.39.0 (`go.sum:68-69`) | 직접, 필수(OpenAI 호환 프로토콜 선택 시), 런타임 | `internal/llm/client.go:15-17`, `:283-335`, `:338-402`, `:405-464` | Chat Completions 요청(tools=function, `MaxCompletionTokens`), 응답의 tool_calls·`reasoning_content` 추출, 재시도 5회 | 제거하면 OpenAI 호환 엔드포인트(DashScope, DeepSeek 등 프리셋 대부분 포함) 불가 | 코드 확인 |
| `github.com/pkoukk/tiktoken-go` | v0.1.8 | v0.1.8 (`go.sum:72-73`) | 직접, 필수, 런타임 | `internal/llm/client.go:18`, `:208-272`, `internal/llm/embedded_loader.go:10-23` | **토큰 예산 근사**: 프롬프트 80% 사전 검사, 큰 diff 제외, 압축 임계(60/80%). 항상 `cl100k_base`(모델명을 넘기지 않음), BPE 데이터 1.7MB를 바이너리에 임베드해 네트워크 불필요. 로드 실패 시 `bytes/4` 근사 | 제거하면 토큰 기반 가드 전체 재작성. Claude·Qwen 등에는 근사 오차가 있음(추론) | 코드 확인 (임베드는 `cl100k_base`만 존재: `internal/llm/bpe_data/`. `o200k_base`는 URL 매핑만 있고 파일 없음 → 사용되면 폴백) |
| `github.com/bmatcuk/doublestar/v4` | v4.10.0 | v4.10.0 (`go.sum:15-16`) | 직접, 필수, 런타임 | `internal/config/rules/system_rules.go:12`, `:127-138`, `:204-234`, `internal/config/allowlist/allowed_ext.go:33`, `:88-97` | **경로 패턴**: 규칙 매칭, include/exclude, 기본 제외 경로(`**`, `{a,b}` 중괄호는 코드가 직접 전개) | 제거하면 규칙·필터 전부 재구현 | 코드 확인 |
| `charm.land/bubbletea/v2` | v2.0.7 | v2.0.7 (`go.sum:3-4`) | 직접, **선택적 기능**(대화형 설정), 런타임 | `cmd/opencodereview/provider_tui.go`, `provider_cmd.go` (`tea` 임포트 3곳) | `ocr config provider/model` TUI | **리뷰 엔진은 의존하지 않음**(엔진 패키지 `internal/agent`, `internal/tool`, `internal/diff`, `internal/llm`에 `charm.land` 임포트 없음) → 서비스 워커에서 TUI 파일만 제외하면 제거 가능 | 코드 확인(임포트 grep) |
| `charm.land/bubbles/v2` | v2.1.0 | v2.1.0 (`go.sum:1-2`) | 직접, 선택적(TUI) | `cmd/opencodereview/provider_tui.go` (`textinput`) | 입력 위젯 | 위와 동일 | 코드 확인 |
| `charm.land/lipgloss/v2` | v2.0.3 | v2.0.3 (`go.sum:5-6`) | 직접, 선택적(TUI) | `cmd/opencodereview/provider_tui.go` | 스타일링 | 위와 동일 | 코드 확인 |
| `go.opentelemetry.io/otel`, `/metric`, `/trace`, `/sdk`, `/sdk/metric` | v1.43.0 | v1.43.0 (`go.sum:96-97` 등) | 직접, 선택적(기본 꺼짐), 런타임 | `internal/telemetry/*.go`. 호출은 `agent.go`의 `telemetry.StartSpan/Event/RecordLLMRequest/RecordToolCall` | LLM 호출·도구·파일·리뷰 시간/토큰 관측(span/metric). `OCR_ENABLE_TELEMETRY=1` 또는 설정 파일일 때만 활성(꺼지면 no-op span) | 제거하면 관측 코드 삭제 필요. 엔진 로직에는 영향 없음 | 코드 확인 (`internal/telemetry/provider.go:28-62`, `span.go:19-27`) |
| `go.opentelemetry.io/otel/exporters/stdout/{stdouttrace,stdoutmetric}` | v1.43.0 | v1.43.0 | 직접, 선택적 | `internal/telemetry/exporter.go:14-25`, `:61-` | 콘솔 exporter(기본 exporter) | 위와 동일 | 코드 확인 |
| `go.opentelemetry.io/otel/exporters/otlp/{otlptrace/otlptracegrpc,otlpmetric/otlpmetricgrpc}` | v1.43.0 | v1.43.0 | 직접, 선택적 | `internal/telemetry/exporter.go:12-13`, `:29-60` | OTLP gRPC 전송(`OTEL_EXPORTER_OTLP_ENDPOINT` 설정 시) | 위와 동일. gRPC·protobuf가 간접 의존으로 따라옴 | 코드 확인 |

## 간접 의존 (go.mod `// indirect`)

- 직접 임포트가 없는 것(임포트 grep 결과: 위 직접 의존 외에 서드파티 임포트 없음)은 전부 간접이다. 대표적으로 `github.com/invopop/jsonschema`, `github.com/standard-webhooks/standard-webhooks/libraries`, `github.com/tidwall/{gjson,sjson,match,pretty}`, `github.com/buger/jsonparser`(OpenAI/Anthropic SDK 계열로 추정), `google.golang.org/grpc`, `protobuf`, `genproto`, `grpc-gateway`(OTLP gRPC 계열), `github.com/charmbracelet/*`, `github.com/atotto/clipboard`, `mattn/go-runewidth`, `rivo/uniseg`, `muesli/cancelreader`(Bubble Tea 계열), `go.yaml.in/yaml/v4`, `golang.org/x/{net,sync,sys,text}`, `github.com/dlclark/regexp2`(tiktoken 계열 추정).
- **어느 직접 의존이 어느 간접 의존을 끌고 오는지는 `go mod why`/`go mod graph`를 실행하지 않아 확인하지 않았다.** 위 괄호 안 귀속은 추론이다.
- `standard-webhooks`가 모듈 목록에 있다는 사실만으로 웹훅 처리 기능이 있다고 볼 수 없다. 이 레포 코드에서 임포트되지 않는다(임포트 grep).

## GUIDE 후보 중 이 SHA에 없는 패키지 (미지원 판정 근거)

| 후보 | 결과 | 찾은 범위 | 검증 |
|---|---|---|---|
| `modelcontextprotocol/go-sdk` (MCP) | **없음** | `go.mod`, `go.sum`, `cmd`·`internal` 소스, `Makefile`, README·스킬·플러그인 문서에서 `mcp|modelcontextprotocol` 검색 결과 없음. 도구 이름도 코드에 고정: `Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown` 1개(`internal/tool/definitions.go:13-21`, `:32-34`, 기준: [00 1절](00-overview.md)) → MCP 도구 등록·발견·실행 경로 없음 | 코드 확인(부재는 위 범위) |
| `aws-sdk-go-v2/config` (Bedrock/AWS) | **없음** | 동일 범위에서 `aws|bedrock` 검색 결과 없음. 지원 프로토콜은 `anthropic`, `openai` 두 가지뿐(`internal/llm/client.go:192-206`) → AWS 필수 의존 없음 | 코드 확인(부재) |
| `spf13/cobra`, `pflag` | **없음** | `go.mod`, `go.sum`에 없음. CLI는 표준 `flag` + 직접 만든 단축 플래그 확장(`cmd/opencodereview/flags.go:12-93`) | 코드 확인 |
| `tree-sitter`, LSP, 벡터 DB 라이브러리 | **없음** | `go.mod` 직접·간접 목록 전체 | 코드 확인 |
| DB·큐·샌드박스 클라이언트 | **없음** | 동일 | 코드 확인 |

## 자체 구현 vs 외부 라이브러리 경계

| 기능 | 구현 주체 | 위치 |
|---|---|---|
| Tool-Calling 루프, 종료 조건, 도구 실행 | **자체 구현** | `internal/agent/agent.go:848-1074` |
| 컨텍스트 압축 | 자체 구현(LLM 요약 호출) | `internal/agent/compression.go` |
| 코드 검색·파일 읽기 | 자체 구현 + **`git` 하위 프로세스** | `internal/tool/code_search.go`, `file_find.go`, `filereader.go` |
| diff 파싱 | 자체 구현(정규식). 외부 diff 라이브러리 없음 | `internal/diff/parser.go`, `hunk.go` |
| LLM 요청/응답 변환·재시도·타임아웃 | SDK(anthropic-sdk-go, openai-go) + 얇은 어댑터 | `internal/llm/client.go` |
| 토큰 계산 | tiktoken-go (근사) | `internal/llm/client.go:208-272` |
| 경로 패턴 | doublestar + 자체 중괄호 전개 | `internal/config/rules/system_rules.go:156-177` |
| CLI 파싱 | 표준 `flag` + 자체 래퍼 | `cmd/opencodereview/flags.go` |

## 외부 서비스·바이너리 요구

| 요구 | 필수 여부 | 사용처 | 근거 | 검증 |
|---|---|---|---|---|
| LLM API (Anthropic Messages 또는 OpenAI Chat Completions 호환) | **필수** | 모든 LLM 호출(Plan, Main, 압축, 위치 재해석, 필터) | `internal/llm/client.go:192-206`. 프리셋 12종(anthropic, openai, dashscope, dashscope-tokenplan, volcengine, deepseek, tencent-tokenhub, hy-tokenplan, kimi, z-ai, mimo, minimax)과 사용자 정의 URL | 코드 확인 (`internal/llm/providers.go:19-217`, `resolver.go:169-290`) |
| `git` 실행 파일 | **필수** | diff, 파일 읽기, 검색, 목록 | `internal/gitcmd/runner.go:50`, `internal/diff/git.go:339-342`, `internal/tool/*.go`. `git grep -P`는 PCRE 지원 필요(추론). `--end-of-options`를 쓰므로 비교적 최신 git 필요(추론) | 코드 확인 |
| 로컬 git 저장소(작업 트리 + 객체) | **필수** | 코드 접근 전부 | `review_cmd.go:33-54` | 코드 확인 |
| 홈 디렉터리 쓰기 권한 | 사실상 필요(없어도 세션 로그 경고만 출력하고 진행) | 세션 JSONL, 설정 | `internal/session/history.go:120-126` | 코드 확인 |
| OTLP 수집기 | 선택 | telemetry exporter=otlp일 때만 | `internal/telemetry/exporter.go:29-60` | 코드 확인 |
| Node.js/npm | 선택(설치 편의) | npm 배포 래퍼 `bin/ocr.js`가 네이티브 바이너리를 호출. `postinstall`이 GitHub Releases에서 바이너리를 내려받고 sha256 확인. **래퍼는 기본적으로 백그라운드 업데이트 확인을 띄움**(`OCR_NO_UPDATE`로 끔) | `package.json:5-9`, `:16`, `:27-28`, `scripts/install.js:197-236`, `bin/ocr.js:16-41` | 코드 확인 |
| Docker, DB, 큐, 샌드박스, MCP 서버 | **요구 없음** | - | 레포에 Dockerfile 없음(`find`로 확인), `go.mod`에 클라이언트 없음 | 코드 확인 |

## 최소 실행 구성 (문서·설정 근거)

- 바이너리 1개(`go build ./cmd/opencodereview`, `Makefile:29-30`의 `build` 타깃은 `./dist/opencodereview`) + `git` + LLM 엔드포인트 3요소(URL, 토큰, 모델)면 동작한다. 환경변수만으로 가능: `OCR_LLM_URL`, `OCR_LLM_TOKEN`, `OCR_LLM_MODEL`, (`OCR_USE_ANTHROPIC`)(`internal/llm/resolver.go:24-30`, `:80-115`). 단 홈 디렉터리 설정 파일에 유효 엔드포인트가 이미 있으면 그것이 우선한다(`resolver.go:56-57`).
- 수치(메모리·처리량)는 측정하지 않았다.

## README·문서와 코드가 다른 곳

| 문서 주장 | 코드 | 위치 | 검증 |
|---|---|---|---|
| 관련 파일을 번들로 묶어 하위 에이전트로 실행 | 파일당 하위 작업. 번들링 코드 없음 | `README.md:72` vs `internal/agent/agent.go:397-426` | 코드 확인 |
| "독립적인 위치 지정·**반성(reflection)** 모듈이 내용 정확도 향상" | 반성에 해당하는 것은 diff만 보는 반증 필터 1회. `CommentWorkerPool` 주석은 "tracking, re-tracking, reflection, suggestion validation"을 말하지만 비동기 작업의 실제 내용은 라인 해석+재해석뿐 | `README.md:74`, `internal/agent/agent.go:127-135` vs `:1003-1030`, `:544-601` | 코드 확인 |
| `--max-tools`는 "템플릿 기본값보다 클 때만 적용" | 지정 값이 0보다 크면 **무조건 덮어씀**(10 미만이면 10으로 올림). 줄일 수도 있음 | `README.md:342` vs `cmd/opencodereview/review_cmd.go:41-43`, `flags.go:170-177` | 코드 확인 |
| `make run`은 `--staged` 사용 | `--staged` 플래그는 정의되어 있지 않음(알 수 없는 플래그 오류가 날 것) | `Makefile:38-39` vs `flags.go:121-135` | 코드 확인(실행 안 함) |
| GitLab 예제가 `~/.open-code-review` 생성 | 실제 설정 디렉터리는 `~/.opencodereview` | `examples/gitlab_ci/.gitlab-ci.yml:39` vs `cmd/opencodereview/config_cmd.go:20` | 코드 확인 |
| 템플릿 `MAIN/PLAN/MEMORY_COMPRESSION.timeout` | 파싱만 하고 사용하지 않음 | `task_template.json:3-22`, `template.go:32`, `:48` vs `agent.go`(읽는 곳 없음) | 코드 확인 |
| 환경변수가 "highest priority" | 코드 우선순위는 설정 파일 > `OCR_*` env > Claude Code env > 셸 rc | `README.md:168-177` vs `internal/llm/resolver.go:56-59` | 코드 확인 |
| `telemetry.content_logging`이 LLM 프롬프트·응답을 내보냄 | `ContentLogging()`은 정의만 있고 호출처 없음 → 효과 없음 | `README.md:520` vs `internal/telemetry/provider.go:69-76` | 코드 확인 |
| README 벤치마크 우위(정밀도·토큰 1/9 등) | 재현 코드·데이터를 레포에서 찾지 못함 | `README.md:37-50`, `imgs/benchmark-*.png` | 미확인 |

## 라이선스

- 레포 `LICENSE`는 Apache License 2.0이다(`LICENSE:1-4`). 하위 디렉터리별 별도 라이선스 파일은 찾지 못했다(`find`로 `LICENSE*` 확인 범위: 레포 루트). 스킬 문서 머리에도 `license: Apache-2.0`(`skills/open-code-review/SKILL.md:11`). 서드파티 의존 라이선스는 조사하지 않았다(미확인).
