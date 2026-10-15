# open-code-review — 다음 세션 메모

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q1-Q12 (잔여 항목 정리)
- 검증 수준 요약: 증거 표가 없는 메모 문서 — 집계 대상 아님(이전 "코드 확인 0 / 추론 2 / 미확인 1"은 근거 없는 숫자라 삭제). 대신 미확인 체크리스트 12개, 문서별 집계는 각 문서 머리(기준은 문서 머리에 명시)
- 실행 여부: 정적 추적만

## 확인한 범위

- `cmd/opencodereview/`(TUI `provider_tui.go` 제외), `internal/` 비테스트 Go 12,159줄 전수.
- 프롬프트 10개(`internal/config/template/prompts/`), `task_template.json`, `tools.json`, 규칙 JSON·문서, 허용 확장자·제외 패턴 JSON.
- `examples/github_actions/ocr-review.yml`, `examples/gitlab_ci/.gitlab-ci.yml`, `.github/workflows/ocr-review.yml`(앞부분), `skills/`·`plugins/` 문서(앞부분).
- `go.mod`, `go.sum`(직접 의존 대조), `Makefile`, `package.json`, `bin/ocr.js`, `scripts/install.js`(체크섬 부분).
- `07-credentials.md`: 자격증명·세션 로그·OTel 경로(`internal/llm/resolver.go`, `internal/telemetry/*`, `internal/session/persist.go`, `cmd/opencodereview/provider_cmd.go` 등).
- 코드 확보는 `repos/open-code-review` 읽기 전용, 파일 수정·실행 없음. SHA 고정과 clean 상태 확인.

## 미확인 항목 체크리스트

- [ ] LLM SDK(`anthropic-sdk-go` v1.47.0, `openai-go/v3` v3.39.0)의 `WithMaxRetries(5)`가 재시도하는 오류 범위·백오프 (모듈 소스 미열람)
- [ ] 실제 모델이 루프에서 보이는 행동: 호출 횟수 분포, `task_done` 호출 빈도, "도구 호출 없음" 반복으로 30라운드를 소모하는 비율 (실행하지 않음)
- [ ] `git grep --max-count`가 파일당 상한이라는 해석(추론) 실행 확인
- [ ] 병합 커밋을 `--commit`으로 줄 때 파싱 결과가 0개인지(추론) 실행 확인
- [ ] 컨텍스트 압축이 큰 diff에서 조기 종료를 일으키는지(`02-...#4.7`) 재현
- [ ] `go list -m all` / `go mod graph`로 해석 버전 확인(현재는 `go.sum` 단일 버전 대조), 간접 의존 귀속(`go mod why`)
- [ ] 서드파티 의존 라이선스, 간접 의존 포함
- [ ] `internal/viewer`의 핸들러·호스트 가드·템플릿 세부, `provider_tui.go` TUI 세부 (범위 밖으로 둠)
- [ ] `scripts/update.js`(자동 업데이트 확인 동작), `scripts/platform.js`, `.github/workflows/release.yml` 세부
- [ ] README 벤치마크(200 PR, 1,505 이슈) 재현 코드·데이터 존재 여부(`pages/src/components/BenchmarkSection.tsx` 미열람)
- [ ] 장기 실행 서버에 임베드했을 때의 전역 상태 안정성(OTel, tiktoken 로더, `stdout` writer)
- [ ] `.claude/commands/`, `.claude-plugin/`, `plugins/open-code-review/CODEX*.md` 전체 내용

## 다음에 볼 파일과 함수

| 파일 | 함수/영역 | 목적 |
|---|---|---|
| `internal/agent/compression.go` | `partitionMessages`, `computeActiveZoneSize`, `runCompression` | 압축 동작 어긋남 재검증 |
| `internal/agent/agent.go` | `performLlmCodeReview`, `executeReviewFilter`, `buildChangeFilesExcept` | 이슈 표(`06-fit.md`) 재확인, 실행 시 로그와 대조 |
| `internal/llm/client.go` | Anthropic `buildAnthropicParams`의 tool_result 변환, `mapOpenAIResponse`의 `reasoning_content` | 프로토콜별 Tool Call 표현 차이 |
| `internal/diff/parser.go`, `git.go` | 병합 커밋·rename·대규모 변경 | 실행 사례로 검증 (사용자와 실행 합의 필요) |
| `cmd/opencodereview/provider_tui.go`, `internal/viewer/*` | TUI와 뷰어 | 서비스 분리 시 제거 범위 확인 |
| 포크 검토용 | `agent.Args`(`agent.go:26-99`)에서 인터페이스로 바꿀 후보: `FileReader`, `Session`, 출력 writer, `Resolver` | `06-fit.md` 12.4 B안 구체화 |

## README ↔ 코드 차이 (05 표 + 07 "기존 보고서와 다른 점" 반영)

| 문서 주장 | 코드 | 위치 | 상세 |
|---|---|---|---|
| 환경변수가 "highest priority" | 우선순위는 설정 파일 > `OCR_*` env > Claude Code env > 셸 rc. `provider` 설정 후 키가 없으면 다음 전략으로 안 넘어가고 오류 | `README.md:168-177` vs `internal/llm/resolver.go:56-59` | [05](05-dependencies.md), [07 5번](07-credentials.md#diff-from-existing) |
| `telemetry.content_logging`이 프롬프트·응답을 내보냄 | `ContentLogging()`은 정의만 있고 호출처 없음 → 효과 없음 | `README.md:520` vs `internal/telemetry/provider.go:69-76` | [05](05-dependencies.md), [07 4번](07-credentials.md#diff-from-existing) |
| (문서 없음) `OTEL_EXPORTER_OTLP_PROTOCOL` 지원처럼 보임 | 읽기만 하고 사용 안 함(gRPC 고정) | `internal/telemetry/config.go:53-55` | [07 6번](07-credentials.md#diff-from-existing) |
| 설정 "파일 0600"(기존 04 서술) | 디렉터리 `~/.opencodereview`는 config 쪽 생성 0755, 세션 쪽 0700 | `cmd/opencodereview/provider_cmd.go:279`, `internal/session/persist.go:99` | [07 3번](07-credentials.md#diff-from-existing) |

기존 05 표의 7건(번들링, 반성 모듈, `--max-tools`, `make run --staged`, GitLab 예제 경로, 템플릿 timeout, 벤치마크)은 [05](05-dependencies.md) 참조.

## 분석 중 생긴 질문

1. 모델이 `code_comment`로 `path` 인자를 직접 넣으면 현재 파일이 아닌 파일에 코멘트가 붙을 수 있다(`code_comment.go:71-73`, `agent.go:985-989`). 필터는 `CommentsForPath(newPath)`만 대상이라 이런 코멘트는 필터를 통과한다. 실제로 발생하는가?
2. "도구 호출 없음"이 반복되는 모델(예: reasoning 중심 모델)에서 30라운드 소모가 흔한가? `--max-tools` 하한 10과의 상호작용은?
3. 큰 PR에서 47110 토큰 초과로 조용히 제외되는 파일의 비율은? 서비스에서는 분할 리뷰가 필요한가?
4. 우리 서비스에서 "다른 파일 발견 무시" 지시를 바꾸면(변경 안 한 호출부의 결함도 보고) 오탐이 얼마나 늘 것인가? (평가 세트 필요)
5. `pull_request_target` + 작업 트리 `rule.json` 로드(`03-...#q8`)를 실제 포크 PR에서 악용할 수 있는가? (실행 합의 필요)

## GUIDE 8절 "레포 하나의 완료 기준" 자체 점검

| 항목 | 상태 | 비고 |
|---|---|---|
| 모든 문서 머리의 SHA가 `repos.lock.tsv`와 같다 | 충족 | 8개 문서 모두 `57273a9...` |
| Q1 호출 흐름 다이어그램이 있고 노드마다 코드 위치가 있다 | 충족 | `01-...#1.4`, `00-overview.md` |
| 고정 문맥 확장 / 동적 탐색 / 재시도 / Agent Loop가 구분되어 있다 | 충족 | `02-...#3.1`, `#4.1` |
| 종료 조건(정상, 도구 없음, 최대 반복, 토큰·시간, 취소, 모델 오류)을 각각 확인했거나 미확인으로 표시했다 | **부분 충족** | 모두 코드로 확인. 단 SDK 내부 재시도 범위와 취소 시 실제 동작(프로세스 종료)은 추론/미확인 |
| 검증 단계의 독립성과 추가 파일 접근 여부를 답했다 | 충족 | `02-...#5.2` (같은 모델·새 대화·추가 파일 접근 불가) |
| 메모리는 쓰기와 읽기 양쪽을 추적했고, 한쪽이 없으면 찾아본 범위와 함께 적었다 | 충족 | `03-...#q7` (쓰기: 세션 JSONL, 읽기: 뷰어뿐) |
| 의존성 표에서 선언 버전과 해석 버전, 선택/필수, 호출 위치가 채워져 있다. 선언만 있고 쓰이지 않는 패키지가 구분돼 있다 | **부분 충족** | 해석 버전은 `go.sum` 대조이며 모듈 그래프 명령은 미실행. 간접 의존 귀속은 추론. 선언만 있고 쓰이지 않는 직접 의존은 없음(전부 임포트 확인) |
| 모든 주장에 검증 수준과 기능 지원 수준이 붙어 있고, `추론`에는 근거가 있다 | 충족(자체 판단) | 서술형 문단 일부는 표의 검증 칸 대신 문장에 표기 |
| README·제품 문구와 코드가 다른 곳이 기록돼 있다 | 충족 | `05-dependencies.md`의 차이 표(9행) + 본 문서 위 표(07 확인분) |
| 5절의 최종 질문에 답했다 | 충족 | `00-overview.md` 6절, `06-fit.md` |
| 정적 추적만 한 항목과 실행한 항목이 분리돼 있다 | 충족 | 실행 항목 없음(전부 정적 추적), 각 문서 머리에 명시 |

미충족·부분 충족은 위 두 항목과 "미확인 항목 체크리스트"에 있다. 실행이 필요한 항목은 사용자와 합의 후 진행한다(GUIDE 2.2절).

## 정정 이력(2026-10-13)

- 도구 개수 표기 통일: 00(5종)·01·02(5개/이름 6개)·03·05(7개)·06(5종)·07(7개)이 제각각이었음. `internal/tool/definitions.go:13-21`을 직접 열어 `Tool` 값 7개 = 모델 호출 가능 6개(`file_read, file_find, code_search, file_read_diff, code_comment, task_done`) + 내부 `Unknown` 1개, Provider 등록은 5개(`review_cmd.go:272-280`, `task_done`은 `agent.go:969-971`에서 직접 처리)임을 확인하고 기준을 00 1절에 명시, 전 문서가 이를 참조. 05·07의 "7개/7종 모델용"은 오류였음.
- `content_logging`: 03 7.4가 "켜면 프롬프트·응답을 내보낸다"고 썼으나 `ContentLogging()`(`provider.go:70`)은 호출처가 `cmd/`·`internal/`에 없음을 grep으로 재확인(07 지적이 맞음). 03을 "효과 없음"으로 고치고 04 D절·00 4절·05 README↔코드 표에 반영.
- 검증 수준 집계: 문서마다 기준(행 수/서술 포함/근사치)이 달라 00 "코드 확인 9/미확인 3"(표 실제 9/2), 07 "약 55/추론 7/미확인 4" 등이 어긋났음. 모든 문서 머리에 "증거 표 행 단위, 검증 칸 첫 판정" 기준을 명시하고 실제 행 수로 재계산(00: 10/0/0/2, 01: 57/0/1/0, 02: 48/0/0/0, 03: 34, 04: 30, 05: 30/0/0/1, 07: 62/0/2/2). 06은 "의견 문서 — 코드 근거 없음", 본 문서는 집계 대상 아님으로 표기.
- README↔코드 차이 누락: 07 "기존 보고서와 다른 점"의 env 우선순위·content_logging·OTLP 프로토콜·디렉터리 권한이 00·next.md에 없었음. 00 4절 4번과 본 문서 위 표에 추가, 05 표에 2행 추가.
- 07 "기존 보고서와 다른 점" 절에 "정정 반영됨(2026-10-13)" 표시와 반영 위치를 기록.
