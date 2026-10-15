# open-code-review — 우리 서비스 적용 (분석자 의견)

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q12
- 검증 수준 요약: **의견 문서 — 코드 근거 없음**(집계 대상 아님). 근거가 되는 사실의 검증 수준은 01~05의 표를 따른다. 단 "알려진 이슈" 표 13행은 01~05에서 확인한 사실의 재인용이며, 그중 추론 표기는 6·7·13번 3행
- 실행 여부: 정적 추적만

> **이 문서의 판단은 모두 "의견"이다.** 근거가 되는 사실은 `01`~`05` 문서의 코드 근거 표에 있고, 여기서는 그 사실에서 도출한 재사용·재구현 판단을 적는다. 법률 자문이 아니다.

경로는 `code-review/repos/open-code-review/` 기준이다. 서비스 목표: GitHub/GitLab PR 웹훅 → diff + 관련 기존 코드 + Jira 요구사항 + 팀 규칙 + 과거 피드백을 함께 리뷰하며, 동적 코드 탐색·검증·PR 간 메모리를 포함한다.

---

## Q12. 적용 의견 {#q12}

### 12.1 서비스 목표 대비 OCR이 주는 것과 안 주는 것 (사실 요약 + 의견)

| 서비스 목표 | OCR 제공 수준 | 사실 근거 | 의견: 직접 구현 필요 |
|---|---|---|---|
| PR 웹훅 수신·이벤트 처리 | 미지원 | `01-execution-and-diff.md#q1`, `04-saas-and-isolation.md#q10` | 전부 구현(서명 검증, 정규화, 큐, 중복 방지) |
| diff 획득 | 부분 지원(로컬 git만) | `01-execution-and-diff.md#q2` | Provider 어댑터 + clone/fetch + SHA 고정 |
| 관련 기존 코드 **동적 탐색** | **지원**(grep+파일읽기 수준) | `02-context-loop-verify.md#q3`, `#q4` | 심볼 단위 탐색(참조·정의), 변경 안 한 호출부의 결함을 코멘트 대상으로 허용할지 정책 결정 |
| finding 검증 | 부분 지원(diff-only 반증 필터) | `02-context-loop-verify.md#q5` | 근거 탐색이 가능한 독립 검증 에이전트 |
| Jira 요구사항 | 미지원(`--background` 텍스트 슬롯만) | `03-incremental-memory-rules.md#q9` | 수집·범위 구분·조건별 판정 전부 |
| 팀 규칙 | 부분 지원(파일 기반 경로별 체크리스트) | `03-incremental-memory-rules.md#q8` | 조직·팀 범위, 승인·버전, 저장소 |
| 과거 피드백·PR 간 메모리 | 미지원 | `03-incremental-memory-rules.md#q7` | 쓰기·읽기 경로 전부 |
| 증분 리뷰·재게시 | 미지원 | `03-incremental-memory-rules.md#q6` | 마지막 리뷰 SHA, 코멘트 상태 동기화 |

### 12.2 가져올 것 / 직접 만들 것 / 운영해야 할 의존성

**가져올 가치가 있는 것 (참고 또는 코드 재사용)**

| 대상 | 위치 | 판단 | 이유 |
|---|---|---|---|
| Tool-Calling 루프 골격(라운드 상한, 도구 결과를 `tool` 메시지로 누적, 도구 오류를 문자열로 반환) | `internal/agent/agent.go:848-1074` | **구조를 참고해 재구현** 권장 | 단순하고 읽기 쉬움. 다만 종료 조건·예산 한도는 서비스 요구에 맞게 바꿔야 함(아래 12.4) |
| 도구 Provider 5개와 입출력 형식(`task_done` 제외, 기준: [00 1절](00-overview.md); 줄번호 붙은 `file_read` 출력, `git grep` 어댑터, ref 기준 읽기) | `internal/tool/*.go` | **재사용 후보** | `git show <ref>:<path>`/`git grep <ref>`로 **PR head 고정 상태**를 읽는 방식은 SHA 일관성에 유리. 로컬 clone이 있을 때만 성립 |
| 코멘트 위치 해석 3단(헝크 매칭 → 파일 스캔 → LLM 재해석) | `internal/diff/resolver.go`, `relocation.go` | **재사용 후보** | 모델에게 줄 번호를 말하게 하지 않고 `existing_code`로 복원하는 설계가 인라인 게시에 직접 도움. **side(옛/새) 정보를 추가**해야 함(`01-...#2.4`) |
| 파일 필터(허용 확장자, 기본 제외 glob, include 우회), 큰 diff 제외 | `internal/agent/preview.go`, `internal/config/allowlist/` | 참고 | 단순한 규칙 집합. 제외된 파일이 모델에 알려지지 않는 점은 개선 필요 |
| 컨텍스트 압축(60%/80% 이중 임계, frozen+요약+active 3구역) | `internal/agent/compression.go` | 아이디어 참고 | 동작 어긋남 가능성이 있어(`02-...#4.7`) 그대로 가져오기보다 재설계 |
| 프롬프트 전략("현재 diff만 코멘트", 반증 전용 필터) | `main_task_system.md`, `review_filter_task_*.md` | 아이디어 참고 | 오탐 억제 의도가 분명. 단, 우리 목표(변경 안 한 코드 근거 탐색)와는 "다른 파일 발견 무시" 지시가 상충 |
| LLM 어댑터(Anthropic/OpenAI 이중, 캐시 컨트롤, 사용량 파싱) | `internal/llm/client.go` | 선택 | 얇은 변환층. 서비스 언어가 Go면 재사용, 아니면 SDK 직접 사용이 낫다 |
| 세션 JSONL 트레이스 구조 | `internal/session/persist.go` | 아이디어 참고 | 요청·응답·도구호출 체인(`uuid/parentUuid`)은 디버깅·평가 데이터 설계에 유용. 저장 위치·평문 기록은 그대로 쓰면 안 됨 |
| `Resolver` 인터페이스(규칙 주입 지점) | `internal/config/rules/system_rules.go:15-18` | 재사용 후보 | 파일 기반 구현을 서비스 저장소 구현으로 갈아 끼울 수 있는 이음새 |

**직접 만들어야 하는 것**

| 항목 | 이유(사실 근거) | 제안 경계(의견) |
|---|---|---|
| 웹훅·큐·워커·테넌트 격리·인증·장애 복구 | 엔진에 전혀 없음(`04-...`) | OCR과 무관하게 서비스 기반으로 설계 |
| Git Provider 어댑터와 코드 확보 | 엔진은 로컬 git 가정, 게시 코드는 예제 YAML뿐 | `ChangeSet{base, head sha, files, hunks}` + `Publisher` 인터페이스. 엔진에는 `FileReader` 인터페이스 주입 |
| 증분 리뷰·코멘트 동기화 | 비교 기준·코멘트 상태 저장 없음(`03-...#q6`) | `ReviewState{pr, lastHeadSHA, postedComments[]}` 저장소 |
| 동적 탐색 고도화 | 도구가 텍스트 검색뿐, 호출부 열거를 모델 추론에 의존(`02-...#3.3`) | `find_references(symbol)`, `find_definition(symbol)` 도구 추가(tree-sitter 또는 LSP 서버). 도구 이름이 코드에 고정(`Tool` 값 7개 = 모델 호출 가능 6개 + 내부 `Unknown`)이라 `definitions.go:13-21`·`:32-34`와 `tools.json` 수정 필요 |
| 독립 검증 | 필터는 diff만 보고 추가 파일 접근 불가(`02-...#5`) | 아래 12.3 |
| Jira·요구사항 | 미지원(`03-...#q9`) | 아래 12.3 |
| PR 간 메모리(쓰기·읽기) | 미지원(`03-...#q7`) | 아래 12.3 |
| 팀 규칙 관리 | 승인·버전·범위 없음(`03-...#q8`) | `rules.Resolver` 구현체를 DB 기반으로 교체, 스코프 계층(조직>팀>저장소>경로) 추가 |
| 비용·예산 상한, 취소 | 총 토큰 상한 없음, 신호/취소 경로 없음(`04-...#10.1`, `02-...#4.5`) | 리뷰 단위 토큰 예산과 ctx 취소를 `Agent.Args`에 주입 |
| 결과 중복 제거 | 파일 간·재실행 간 없음 | finding 지문(경로+정규화 `existing_code`+의도) 기반 dedup |

**운영해야 할 의존성(OCR 엔진을 쓸 경우)**: LLM API, `git` 실행 파일과 clone 저장 공간(워커 로컬 디스크), (선택) OTLP 수집기. DB·큐·샌드박스 요구는 OCR 쪽에는 없다(`05-dependencies.md`). 이 부분은 OCR이 서비스 기반 비용을 늘리지 않는 대신 줄여주지도 않는다.

### 12.3 새로 설계해야 할 경계 (구체 제안, 의견)

**(1) 독립 검증 에이전트** — OCR의 `executeReviewFilter`(`internal/agent/agent.go:544-601`) 자리에 대체.
- 입력: finding(`content`, `existing_code`, 위치) + 읽기 전용 도구 세트(`file_read`, `code_search` 재사용).
- 출력: `verdict{confirmed | refuted | inconclusive, evidence:[{path, start_line, end_line, quote}]}`. **근거 위치 없는 confirmed 금지**를 프로그램이 강제.
- 독립성: 생성 모델과 다른 모델/프롬프트, 생성 대화·사고 비공유. OCR 필터는 같은 모델, 도구 없음(`02-...#5.2`)이므로 이 점이 차별점.
- 도구 호출 상한과 종료 조건은 생성 루프와 별도 설정.

**(2) Jira 요구사항** (`03-...#q9` 확장 지점 표 참조)
- `RequirementProvider.Fetch(ctx, ChangeRef) ([]Requirement, error)`를 `runReview`의 `opts.background` 결정부(`review_cmd.go:56-60`) 앞에 두고, `verifyRequirements(ctx, reqs)`를 `dispatchSubtasks` 반환 직전(`agent.go:434-445`)에 단계로 추가. 조건별로 별도 루프를 돌려 `requirement_verdict` 도구로 충족/위반/불명 + 근거 위치를 제출.
- Jira가 없는 상태로 시작한다면 PR 본문·연결 이슈 텍스트를 `Requirement`로 정규화하는 어댑터만 먼저 만들고 판정 단계는 그대로 둔다.

**(3) PR 간 메모리**
- 쓰기: Git 호스팅 이벤트(코멘트 답변·resolve·수정 커밋)를 받아 `MemoryCandidate{tenant, repo, source(PR, comment, SHA), 원문, 증류 규칙, 상태: proposed}`로 저장하고 사람이 승인하면 활성화. 무응답·resolve를 동의로 자동 해석하지 않음.
- 읽기: 두 경로를 모두 제공. (a) `main_task_user.md`의 `### Review Checklist` 다음에 `### Team Memory` 슬롯 추가(`agent.go:494-516` 치환 목록에 자리표시자 추가), (b) `memory_search{query, paths[], symbols[]}` 도구 추가. 조회 조건에 `tenant`·`repo`를 반드시 포함.
- OCR에는 이 경로가 전혀 없으므로(`03-...#q7`) 새 모듈로 설계한다.

**(4) 관련 파일 묶음·종합 패스**
- OCR 코드는 파일당 하위 작업이고 PR 전체 종합 패스가 없다(`02-...#3.5`). 우리 서비스에서는 변경된 심볼 기준으로 관련 파일 그룹을 만들거나, 파일별 결과 후 "파일 간 결함" 전용 종합 단계를 추가하는 것을 의견으로 제안한다.

### 12.4 재사용 방식 3안 (의견)

| 안 | 내용 | 장점 | 단점 | 적합 |
|---|---|---|---|---|
| A. 바이너리 하위 프로세스 호출 | 워커가 clone 후 `ocr review --from --to <sha> --format json --audience agent` 실행, JSON 파싱 | 구현 최소 | 검증·메모리·Jira·규칙 주입 불가(템플릿 임베드 고정), 홈 디렉터리 설정·세션 로그(소스 평문), 취소·예산 제어 약함, 1프로세스=1리뷰 | PoC·비교 기준선 |
| B. 포크 후 `internal/` → 공개 패키지 | `Agent`, `tool`, `diff`를 노출하고 `FileReader`·`Resolver`·세션 싱크·출력 writer를 인터페이스로 주입 | 루프·도구·위치 해석 재사용, 우리 확장 지점 삽입 가능 | 업스트림 추적 부담, Go 서비스 전제 | 서비스를 Go로 만들 때 |
| C. 아이디어만 참고해 자체 엔진 | 12.2의 "아이디어 참고" 항목을 자체 언어로 구현 | 목표(동적 탐색·검증·메모리)에 맞게 처음부터 설계 | 초기 구현량 큼 | 서비스 언어가 Go가 아닐 때 |

권장(의견): 목표가 "스스로 탐색·검증·기억"이므로 A는 비교용에 그치고, **B(Go) 또는 C**를 택한다. OCR 엔진 코드는 약 1.2만 줄 규모(`cmd`+`internal` 비테스트 Go 파일 합계 12,159줄, 줄 수 집계)로 읽고 포크하기에 작다.

### 12.5 라이선스

- `LICENSE`는 Apache License 2.0(`LICENSE:1-4`), 하위 디렉터리별 별도 라이선스 파일은 레포 루트 `find`로 찾지 못했다. Apache-2.0은 수정·재배포·상업적 사용이 가능하고 저작권·라이선스 고지, 변경 사실 표기, NOTICE 유지 조건이 붙는다(의견: 일반적 이해이며 법무 검토 필요). 레포에 `NOTICE` 파일은 없다(`find -maxdepth 3 -iname "NOTICE*"` 결과 없음).
- 서드파티 의존의 라이선스는 조사하지 않았다(미확인).

---

## 우선 읽을 파일 (순서)

1. `internal/agent/agent.go` — 전체 파이프라인과 루프(`:206-540`, `:848-1074`)
2. `internal/config/template/prompts/main_task_system.md`, `main_task_user.md` — 모델에게 주는 것
3. `internal/tool/code_search.go`, `file_read.go`, `filereader.go`, `file_find.go` — 탐색 수단
4. `internal/diff/git.go`, `parser.go`, `resolver.go`, `relocation.go` — diff와 위치
5. `internal/agent/compression.go` — 컨텍스트 관리
6. `internal/config/template/prompts/review_filter_task_*.md` — 검증 단계
7. `internal/llm/client.go` — 프로토콜 어댑터
8. `examples/github_actions/ocr-review.yml`, `examples/gitlab_ci/.gitlab-ci.yml` — 게시 방식

## 알려진 이슈·주의 (코드 확인, 실행하지 않음)

| # | 이슈 | 위치 | 비고 |
|---|---|---|---|
| 1 | "도구 호출 없음"이 종료가 아니라 재요청(라운드 소모) | `agent.go:893-901` | 텍스트만 내는 모델은 30라운드를 다 씀 |
| 2 | `task_done`의 `state: FAILED`를 무시 | `agent.go:969-971` | 실패 보고가 성공 종료로 처리 |
| 3 | 삭제 파일이 `<other_changed_files>`에 `/dev/null`로 표기, `file_read_diff` 불가 | `diff/parser.go:98-101`, `agent.go:347-361`, `:646-670` | |
| 4 | 필터로 제외된 파일이 변경 파일 목록에서 빠짐 | `agent.go:220-227` vs `:646-670` | |
| 5 | 큰 diff(47110 토큰 초과) 파일은 조용히 제외, 경고 기록 없음 | `agent.go:682-705` | 대규모 PR에서 누락 |
| 6 | 압축 파티션이 "압축 불필요" 주석과 달리 전체 압축, 활성 구간 예산이 frozen 토큰 미반영 | `compression.go:106-111`, `:67-87`, `:182-185` | 결과는 추론 |
| 7 | `code_search`의 `--max-count`가 파일당이라 총량 상한 아님 | `code_search.go:65`, `:146-148` | 추론(git 의미) |
| 8 | 옛 쪽 일치 시 옛 줄 번호가 side 표기 없이 사용됨 | `diff/resolver.go:102-109`, `model/review.go:4-12` | 인라인 게시 오위치 가능 |
| 9 | `finish_reason` 미검사(길이 초과 응답 처리 없음) | `llm/client.go:454`, `:745` | |
| 10 | 템플릿 `timeout` 3종이 읽히지 않음 | `template.go:32`, `agent.go`(참조 없음) | |
| 11 | 세션 로그가 끌 수 없고 소스를 평문으로 기록 | `agent.go:186-198`, `persist.go:92-112` | 서비스화 시 필수 수정 |
| 12 | `.opencodereview/rule.json`을 PR head 작업 트리에서 읽음 | `system_rules.go:339-353` | 프롬프트 주입 경로 |
| 13 | 병합 커밋 `--commit`에서 파일 0개 파싱 가능성 | `diff/git.go:125`, `parser.go:18` | 추론(미실행) |
