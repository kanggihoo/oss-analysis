# open-code-review — 문맥 확보, Agent Loop, 검증

- 분석 SHA: `57273a9ea28548b94b3d67c247ff13a63c01fc47` (repos.lock.tsv와 일치)
- 분석일: 2026-10-13
- 관련 공통 항목: Q3, Q4, Q5 (이 문서가 가장 중요)
- 검증 수준 요약: 코드 확인 48 / 실행 확인 0 / 추론 0 / 미확인 0 (보조: 코드 확인 행에 추론 병기 2행, 미확인 병기 1행. 집계 기준: 이 문서 증거 표의 행 단위, 검증 칸 맨 앞 판정으로 분류(1행=1판정). 검증 칸 안에 보조로 병기된 추론·미확인은 괄호로 별도 표기. 설명 칸 안의 인라인 표기와 서술 문단은 집계 제외)
- 실행 여부: 정적 추적만 (아래 "실행 예"는 코드를 따라가 구성한 것이며 실제 실행 로그가 아님)

경로는 `code-review/repos/open-code-review/` 기준이다. 핵심 permalink:
- Tool-Calling 루프: https://github.com/alibaba/open-code-review/blob/57273a9ea28548b94b3d67c247ff13a63c01fc47/internal/agent/agent.go#L848-L958
- 결함 검증(`executeReviewFilter`): https://github.com/alibaba/open-code-review/blob/57273a9ea28548b94b3d67c247ff13a63c01fc47/internal/agent/agent.go#L544-L601

---

## Q3. 문맥 확보와 동적 탐색 {#q3}

### 3.1 자동 수집 vs 모델 요청 (반드시 분리)

| 구분 | 무엇을 | 누가 결정 | 위치 | 검증 |
|---|---|---|---|---|
| **고정 문맥(프로그램 자동)** | 해당 파일의 diff 원문(`git diff -U3`, 헤더 포함) | 프로그램 | `internal/diff/git.go:17`, `internal/config/template/prompts/main_task_user.md:8-10` | 코드 확인 |
| 고정 문맥 | **다른** 변경 파일 목록(`MODIFIED/ADDED/RENAMED/DELETED  경로` 형식, 내용 없음) | 프로그램 | `internal/agent/agent.go:646-670`, `main_task_user.md:1-4` | 코드 확인 |
| 고정 문맥 | 경로별 리뷰 체크리스트(`{{system_rule}}`) | 프로그램(glob 매칭) | `internal/agent/agent.go:674-679`, `internal/config/rules/system_rules.go:356-367` | 코드 확인 |
| 고정 문맥 | `--background` 요구사항 텍스트(`{{requirement_background}}`), `--commit`이면 커밋 메시지 | 사용자/프로그램 | `cmd/opencodereview/review_cmd.go:56-60`, `main_task_user.md:14-16` | 코드 확인 |
| 고정 문맥 | 계획 결과(`{{plan_guidance}}`): 같은 모델에게 도구 없이 시킨 사전 분석(변경 50줄 이상일 때만) | 프로그램(조건) + 모델(내용) | `internal/agent/agent.go:467-487`, `:767-805` | 코드 확인 |
| **동적 탐색(모델 요청)** | `file_read`, `file_find`, `code_search`, `file_read_diff` 호출 결과 | **모델** | `internal/agent/agent.go:907-930`, `:963-1074`, `internal/tool/*.go` | 코드 확인 |
| 전체 파일 원문 자동 주입 | **없음.** `NewFileContent`는 라인 번호 보정에만 사용 | - | `internal/diff/resolver.go:169-196` (`NewFileContent` grep 결과 전체) | 코드 확인 |
| 파일 간 의존·호출 그래프, AST/LSP, 임베딩 | **없음** | - | 찾은 범위: `internal/tool`(Provider 구현 5개 전부 + `definitions.go`), `internal/agent`, `internal/diff`, `go.mod`(tree-sitter·LSP·벡터 라이브러리 없음) | 코드 확인(부재는 grep+go.mod 범위) |

기능 지원 수준 (Q3 동적 탐색): **지원**(모델이 호출부·구현체를 직접 찾아 읽는 도구 루프가 있음). 단, 심볼 관계를 이해하는 도구는 없고 **텍스트 검색(git grep)+모델 추론**이다. 고정 문맥 확장은 **부분 지원**(`-U3`만, 함수 경계 확장 없음).

### 3.2 프롬프트 근거 (원문 인용 + 번역)

`internal/config/template/prompts/main_task_system.md:10`

> When the context is unclear, use tools to obtain contextual information rather than judging based on assumptions.

맥락이 불명확하면 가정으로 판단하지 말고 도구로 문맥 정보를 얻어라.

`main_task_system.md:18-20`

> Context tools are for understanding purposes only. Findings from other files must NOT become the subject of your comments.
> If you discover a potential issue in another file while gathering context, ignore it — your task is limited to the current diffs.

문맥 도구는 이해 목적으로만 쓴다. 다른 파일에서 발견한 문제를 코멘트 대상으로 삼으면 안 된다. 문맥을 모으다 다른 파일의 잠재 문제를 발견해도 무시하라. 임무는 현재 diff로 한정된다.

`main_task_system.md:22-25`: 완료하면 `task_done`, 확정된 결함은 `code_comment`, 확인이 더 필요하면 문맥 도구를 호출하라는 3지선다(전문은 파일 참조).

→ **설계상 "변경하지 않은 호출부에서 발견한 결함"은 코멘트 대상이 아니다.** 변경된 줄이 호출부와 맞지 않는지(변경 쪽 결함)를 확인하는 용도로만 호출부를 읽는다.

### 3.3 도구 입출력 스키마 표 (도구 정의는 `tools.json`, 구현은 `internal/tool`)

도구 이름은 Go 코드에 고정돼 있다. `definitions.go:13-21`의 `Tool` 값은 7개로, **모델이 호출 가능한 도구 6개**(`task_done, code_comment, file_read, file_find, file_read_diff, code_search`) **+ 내부 항목 1개**(`Unknown`, 이름 해석 실패용 센티널이며 `tools.json`에 정의 없음)다(`:32-34` `allTools()`, 기준: [00 1절](00-overview.md)). 아래 표는 모델 호출 가능 6개를 모두 다룬다(Provider 구현은 `task_done` 제외 5개). `--tools`로 JSON을 바꿔도 **정의(설명·스키마)와 plan/main 활성 여부만** 바뀌고, 모르는 이름은 `NotAvailableMsg`가 반환된다(`agent.go:964-967`). 즉 MCP 같은 외부 도구를 추가할 수 없다.

| 도구 | 입력 | 출력 | 탐색 방식 | 위치 | 검증 |
|---|---|---|---|---|---|
| `file_read` | `file_path`(필수), `start_line`, `end_line` | `File: <path> (Total lines: N)` / `IS_TRUNCATED: bool` / `LINE_RANGE: a-b` / `<줄번호>\|<내용>` 줄들. 최대 500줄, 초과 시 안내문 | 파일 읽기(workspace: 디스크, range/commit: `git show <ref>:<path>`). 변경 **후** 버전만 | `internal/tool/file_read.go:9-75`, `internal/tool/filereader.go:68-245` | 코드 확인 |
| `file_find` | `query_name`(필수), `case_sensitive` | 일치 경로 줄바꿈 목록(최대 100) 또는 `// The file was not found` | `git ls-files --cached --others --exclude-standard`(range/commit은 `git ls-tree -r --name-only <ref>`) 후 **파일명 부분 문자열** 비교. 확장자 없는 파일은 `Makefile` 등 5종만 허용 | `internal/tool/file_find.go:11-129` | 코드 확인 |
| `code_search` | `search_text`(필수), `file_patterns[]`(git pathspec), `case_sensitive`, `use_perl_regexp` | `File: <path>\nMatch lines: n\n<줄>\|<내용>` 묶음. 10초 타임아웃 | `git grep -n -F`(또는 `-P`), 기본 대소문자 무시(`-i`). 정규식·텍스트 매칭이며 **심볼 의미는 모름** | `internal/tool/code_search.go:14-187` | 코드 확인 |
| `file_read_diff` | `path_array[]`(필수) | `==== FILE: <path> ====\n<diff>` | 시작 시 만든 `DiffMap`(필터 전 전체 diff, 삭제 파일 제외) 조회. git 호출 없음 | `internal/tool/file_read_diff.go:8-71`, `internal/agent/agent.go:347-361` | 코드 확인 |
| `code_comment` | `comments[]` 각 `{content, existing_code, suggestion_code?}`. `path`는 스키마에 없고 현재 파일이 자동 주입 | `"Successfully commented."` (또는 파싱 오류 문자열) | 수집기에 추가. 줄 번호는 `existing_code` 매칭으로 해석 | `internal/tool/code_comment.go:36-82`, `internal/agent/agent.go:985-1056` | 코드 확인 |
| `task_done` | `state: DONE\|FAILED` | `"Task completed successfully."` | 종료 신호. `state` 값은 **읽지 않아** `FAILED`도 성공 종료와 같음 | `internal/agent/agent.go:969-971`, `:909-915` | 코드 확인 |

- plan 단계에서는 `code_search`, `file_read_diff`, `file_find`만 "참고용 텍스트"로 프롬프트에 적히고 **실제 도구 정의는 보내지 않는다** (`ChatRequest`에 `Tools` 없음, `agent.go:787-791`; 텍스트 렌더링 `:807-843`, 문구 `"Available Tools (reference only — do not call)"`, `:814`).
- `code_search`의 `--max-count 100`(`code_search.go:65`)은 git grep에서 **파일당** 상한이다. 총 결과 수 상한이 아니므로 "상위 100개만 반환"이라는 도구 설명·`Note: ... truncated` 문구(`:146-148`)는 실제 상한과 어긋난다. 큰 결과가 컨텍스트에 그대로 들어갈 수 있다. 검증: 추론(git 문서 의미, 미실행).
- 도구 호출 인자 JSON이 깨지면 파싱 오류 문구가 도구 결과로 모델에 돌아간다(`agent.go:978-981`). `finish_reason`(길이 초과 등)은 저장만 하고 어디서도 검사하지 않는다(`internal/llm/client.go:114`, `:454`, `:745`, 사용처 grep 없음). 응답이 잘려 인자가 깨져도 별도 처리 없이 위 경로로 간다.

### 3.4 실행 예: "변경하지 않은 호출부 찾기" (정적 추적, 미실행)

가정: `internal/foo/bar.go`의 `Load(path string)` 시그니처를 `Load(ctx context.Context, path string)`로 바꾼 diff.

| 라운드 | 모델 요청(예상) | 프로그램 동작 | 위치 |
|---|---|---|---|
| 1 | `code_search{search_text:"Load(", file_patterns:["*.go"], use_perl_regexp:false}` | `git grep --no-pager -i -F -n --no-color --max-count 100 -e "Load(" [<ref>] -- "*.go"` 실행, 결과를 파일별로 묶어 문자열 반환 | `code_search.go:52-78`, `:106-187` |
| 2 | `file_read{file_path:"cmd/main.go", start_line:30, end_line:70}` | workspace면 디스크 / range면 `git show <to>:cmd/main.go`에서 해당 줄 반환 | `file_read.go:20-75` |
| 3 | `code_comment{comments:[{content:"호출부 cmd/main.go:48이 새 시그니처와 불일치...", existing_code:"func Load(ctx context.Context, path string)..."}]}` + (같은 응답 또는 다음 라운드에) `task_done` | 코멘트 큐(`CommentWorkerPool`)에 비동기 제출 후 `"Successfully commented."` 반환 | `agent.go:1032-1046` |

실제 LLM이 이 순서로 호출할지는 모델 판단이다. 프로그램은 어느 호출부를 볼지 지정하지 않는다. 호출부 열거도 `git grep`이 문자열로 한다(셀렉터·오버로드·동명 함수 구분은 모델 몫).

### 3.5 파일 그룹별 리뷰와 파일 간 결함 누락 가능성

- **실제 단위는 "파일 1개 = 하위 작업 1개"**다(`internal/agent/agent.go:397-426`). README의 "관련 파일을 묶어 하나의 리뷰 단위로"(`README.md:72`)에 해당하는 번들링 코드를 찾지 못했다(`cmd`, `internal` 전체에서 `bundle`/`group` 검색: 압축 라운드·뷰어 FileGroup뿐). 규칙 문서가 `*{mapper,dao}*.xml` 같은 패턴을 묶는 것은 규칙 매칭이지 리뷰 번들이 아니다. → README와 코드 불일치로 기록.
- 파일마다 **대화가 완전히 분리**된다(각자 `messages` 슬라이스, `agent.go:494-516`). 공유되는 것은 `CommentCollector`뿐이고 모델에게 보이지 않는다.
- 파일 A의 하위 작업이 파일 B의 결함을 알 수 있는 경로: (a) `<other_changed_files>` 경로 목록, (b) `file_read_diff`로 B의 diff 열람, (c) `file_read`/`code_search`로 B 현재 내용 열람. 다만 시스템 프롬프트가 "다른 파일 발견은 무시"를 지시한다(3.2).
- 누락 위험 요인(코드 확인): ① 필터(테스트·미지원 확장자·큰 파일)로 제외된 파일은 목록에서 빠짐(`agent.go:646-670`, `01-execution-and-diff.md#2.6`). ② 삭제 파일은 목록에 `/dev/null`로 나오고 `file_read_diff` 불가. ③ 파일 A·B 각각이 **서로의 변경에 의존하는 결함**(예: 인터페이스 변경 + 구현체 변경)은 한쪽 하위 작업이 도구 호출 예산(최대 30회, 컨텍스트 80%)을 상대 파일 조사에 써야만 발견된다. 이를 보장하는 프로그램 로직은 없다. ④ 마지막에 **전체 PR을 보는 종합 패스가 없다**(`agent.go:434-445`는 수집만 함).
- 중복 제거: 파일 간·재실행 간 **없음**(`CommentCollector.Add`는 단순 append, `internal/tool/comment_collector.go:21-26`; 코멘트 텍스트 유사도 비교 코드 grep 없음).

---

## Q4. Agent Loop {#q4}

### 4.1 반복 단위 구분표

| 구분 | OCR에서의 해당 | 위치 | 검증 |
|---|---|---|---|
| **Agent Loop** (모델이 도구 호출 → 결과를 대화에 넣어 재추론) | **있음.** 파일당 Main 루프. 상한 `MAX_TOOL_REQUEST_TIMES = 30` | `internal/agent/agent.go:848-958`, `internal/config/template/task_template.json:37` | 코드 확인 |
| 재시도 / fallback | LLM SDK 내부 재시도 옵션(`WithMaxRetries(5)`)만. **모델 교체 fallback 없음**. 도구 없는 응답 시 "도구를 호출하라" 재요청은 루프 라운드를 소모 | `internal/llm/client.go:299`, `:495`, `agent.go:893-901` | 코드 확인(옵션 값), 재시도 대상 오류 범위는 SDK 내부라 미확인 |
| 다중 호출 | 파일별 하위 작업(동시 8, `--concurrency`) | `agent.go:386-426`, `flags.go:128` | 코드 확인 |
| 다단계 파이프라인 | **있음.** 파일마다 Plan(조건부, 도구 없음) → Main 루프 → (코멘트마다 위치 재해석 LLM, 조건부) → Review Filter(도구 없음) | `agent.go:467-540` | 코드 확인 |
| 컨텍스트 압축 | 루프 중 토큰 60%/80%에서 LLM 요약 호출 | `internal/agent/compression.go:17-20`, `:129-172` | 코드 확인 |

"에이전트"라고 부를 수 있는 부분은 **Main 루프 한 곳**이고, 나머지(Plan, Filter, ReLocation, Compression)는 도구 없는 단발 호출이다. LLM 라이브러리는 `anthropic-sdk-go`, `openai-go`를 직접 쓰고 루프·도구 실행은 자체 구현이다(`internal/llm/client.go` 316-335, 520-542; 루프는 `agent.go`).

### 4.2 최초 모델 입력 재구성 (Main)

| 메시지 | 내용 | 위치 |
|---|---|---|
| system | 역할·원칙·"Strict Focus Rules"·종료 규칙 + (설정 시) `\n\nAlways respond in <language>.` | `internal/config/template/prompts/main_task_system.md:1-25`, `template.go:125-134` |
| user | `<other_changed_files>`, `<current_file_path>`, `<current_file_diff>`, 현재 시각, `<user_task>`(요구사항 배경, 리뷰 체크리스트, 리뷰 계획) | `internal/config/template/prompts/main_task_user.md:1-25`, 치환 `agent.go:494-516` |
| tools | 모델 호출 가능 도구 6개 `task_done, code_comment, file_read, code_search, file_read_diff, file_find` 정의 | `tools.json`, `agent.go:866-871` |

- 계획이 비어 있으면 `### Review Plan (Optional)` 블록 자체를 정규식으로 제거한다(`internal/agent/util.go:22-34`, `agent.go:511-513`).
- 언어 지시(`ApplyLanguage`)는 Main·Plan·Compression의 system에만 붙고 **Review Filter·ReLocation에는 붙지 않는다**(`template.go:125-134`). 필터는 ID 배열만 돌려주므로 영향은 작다.
- **모델이 선택하는 것**: 어떤 도구를 몇 번 호출할지, 무엇을 코멘트할지, 언제 `task_done`을 부를지. **프로그램이 고정하는 것**: 파일 선정·필터, 규칙 선택, 계획 실행 여부(50줄 기준), 도구 집합, 최대 라운드, 토큰 임계값, 코멘트 위치 해석, 필터 단계 실행.

### 4.3 상태 구조와 도구 결과 반영

- 상태는 **파일 하위 작업마다 지역 변수 `messages []llm.Message`** 하나다. 영속 저장·체크포인트 없음.
- 도구 결과는 `assistant(tool_calls)` 메시지 뒤에 `role:"tool"` 메시지로 이어 붙인다(`internal/agent/compression.go:151-161`). Anthropic 프로토콜일 때는 `tool` 메시지를 모아 하나의 user `tool_result` 블록 메시지로 변환한다(`internal/llm/client.go:550-564`, `:573-574`).
- **병렬 도구 호출**: 모델이 한 응답에 여러 호출을 내면 **순차 실행**한다(`agent.go:907-930`의 for 루프). `code_comment`만 워커풀에 비동기 제출한다(`agent.go:1032-1046`; 기본 CLI는 항상 풀을 넘김 `review_cmd.go:127`).
- 도구 오류는 예외가 아니라 **문자열로 모델에게 반환**된다(`agent.go:1065-1068`, 인자 파싱 오류 `:978-981`, 미등록 도구 `:964-967`).

### 4.4 상태·입력·종료 조건 표

| 단계 | 반복 단위 | 입력(상태) | 모델 선택 | 프로그램 고정 | 종료 조건 | 위치 |
|---|---|---|---|---|---|---|
| 파일 선정 | 변경 파일 | `git diff` 결과 | 없음 | 확장자·경로·바이너리·크기 필터 | 필터 후 0개면 종료(`No supported files`) | `agent.go:223-234`, `:381-384` |
| Plan | 파일당 1회 | system+user(diff, 목록, 규칙, 배경, 도구 설명 텍스트) | JSON 계획 내용 | 변경 줄 < 50이면 생략. 실패 시 계획 없이 계속 | 1회 응답 후 끝 | `agent.go:467-487`, `:767-805` |
| **Main 루프** | LLM 호출 1회 = 라운드 1 | `messages`(system, user, [assistant/tool]\*) | 도구 선택·인자, 코멘트, `task_done` | 최대 30라운드, 도구 실행, 압축 | 4.5절 표 참조 | `agent.go:848-958` |
| 위치 재해석 | 코멘트당 | diff, 코멘트, `existing_code` | 발췌 코드 | 1·2순위 문자열 매칭 실패 시에만 | 1회 응답 후 끝 | `agent.go:1003-1030`, `diff/relocation.go:19-69` |
| 컨텍스트 압축 | 임계 초과 시 | frozen 2개 외 이전 라운드 | 요약 내용 | 60%(비동기)/80%(동기) | 요약 삽입 또는 실패 시 원본 유지 | `compression.go:129-241` |
| Review Filter | 파일당 1회(코멘트 있을 때) | diff + 해당 파일 코멘트 JSON | 제거할 ID 배열 | 도구 없음, 제한시간 60초(템플릿) | 파싱 실패 시 아무것도 제거 안 함 | `agent.go:544-601` |

### 4.5 종료 조건 각각 (Main 루프)

| 종료 조건 | 동작 | 위치 | 검증 |
|---|---|---|---|
| **정상 종료** | 모델이 `task_done`을 호출하면 같은 응답의 다른 호출을 순서대로 실행한 뒤 루프 `break`. `state` 값은 무시 | `agent.go:907-915`, `:932-934`, `:969-971` | 코드 확인 |
| **도구 호출 없음** | **종료 조건이 아니다.** 어시스턴트 텍스트를 붙이고 `"You did not successfully call any tools. Please try again or use task_done if finished."`를 user로 추가한 뒤 `continue`. 연속 빈 라운드 가드(3회)는 이 분기 **앞에서** `continue`하므로 적용되지 않아, 모델이 계속 텍스트만 내면 **최대 라운드까지 소모**한다 | `agent.go:850-851`, `:893-901`, `:935-944` | 코드 확인 |
| **최대 반복** | `toolReqCount`(기본 30, `--max-tools`로 10 이상 지정 가능)가 0이 되면 루프 종료. **오류가 아니라 `nil` 반환**이며 `warnings`에도 기록하지 않음(stdout 문구만). 이미 수집한 코멘트는 유지되고 이어서 Review Filter 실행 | `agent.go:849`, `:853`, `:860`, `:953-957`, `:532-538`, `flags.go:170-177`, `review_cmd.go:41-43` | 코드 확인 |
| **토큰 한도(사전)** | 초기 프롬프트가 `MAX_TOKENS×80%`(=47110) 초과면 해당 파일 건너뜀, `token_threshold_exceeded` 경고 | `agent.go:518-530` | 코드 확인 |
| **토큰 한도(루프 중)** | 압축 후에도 80% 이상이면 `"Context compression exceeded threshold"` 출력 후 `break`(오류 아님, 경고 기록 없음) | `agent.go:946-950`, `compression.go:163-171` | 코드 확인 |
| **시간 한도** | 파일 하위 작업 전체(plan+main+filter)에 `--timeout`(기본 10분) 컨텍스트. 루프 맨 앞에서 `ctx.Done()`면 `ctx.Err()` 반환 → `subtask_error` 경고. 진행 중 LLM 요청도 취소됨. Review Filter는 건너뜀(오류 반환 시). 이미 쌓인 코멘트는 남음 | `agent.go:394-419`, `:854-858`, `:532-538` | 코드 확인 |
| **LLM 요청 시간 한도** | 요청당 기본 5분 타임아웃(SDK 옵션) | `internal/llm/client.go:284-286`, `:301`, `:476-478`, `:497` | 코드 확인 |
| **취소** | 프로세스 내 취소 수단은 루트 `context.Background()` 뿐이며 신호 처리 없음. Ctrl-C는 OS 기본 동작(프로세스 종료, 결과는 마지막에 출력되므로 부분 결과 유실) | `review_cmd.go:146`, `os/signal` 사용처 없음 | 코드 확인, 종료 시 동작은 추론 |
| **모델 오류** | SDK 재시도(5) 후에도 오류면 `LLM completion error` 반환 → 하위 작업 실패 경고. 모든 파일이 실패하면 실행 전체 오류 | `agent.go:873-877`, `:439-442`, `:418-424` | 코드 확인 |
| **"충분히 조사했다" 판단** | 프로그램이 판정하지 않음. 모델이 `task_done`을 부르는 것이 유일한 신호(프롬프트 `main_task_system.md:22-25`) | `main_task_system.md:22-25` | 코드 확인 |
| 도구가 유효 결과를 못 낸 라운드 | 결과가 **빈 문자열**일 때만 "빈 라운드"로 세며 3회 연속이면 중단. 오류 문자열도 유효 결과로 취급해 이 가드는 사실상 잘 발동하지 않음 | `agent.go:916-929`, `:935-944` | 코드 확인, 발동 빈도는 추론 |

### 4.6 오류 이후 재시도 범위

| 대상 | 실패 시 | 위치 | 검증 |
|---|---|---|---|
| Plan | 경고 출력 후 **계획 없이** Main 진행 | `agent.go:478-487` | 코드 확인 |
| Main 호출 | 하위 작업 실패(재시도는 SDK 내부 5회만) | `agent.go:873-877` | 코드 확인 |
| 압축 | 원본 `messages` 유지(요약 실패가 컨텍스트 폐기보다 낫다고 주석) | `compression.go:205-212` | 코드 확인 |
| 위치 재해석 | 실패 시 줄 번호 없이 코멘트 유지 | `agent.go:1008-1028`, `diff/relocation.go:52-60` | 코드 확인 |
| Review Filter | 실패·파싱 불가 시 필터링 없이 통과 | `agent.go:576-585`, `:624-634` | 코드 확인 |
| 코멘트 비동기 작업 | 오류는 stdout 출력만. 컨텍스트는 `WithoutCancel`이라 파일 타임아웃과 무관하게 진행 | `agent.go:162-165`, `:1037` | 코드 확인 |

### 4.7 컨텍스트 압축 (세션 내 "메모리", 영속 아님)

- 임계값: 토큰 수의 60%에서 **비동기 요약**, 80%에서 **동기 요약**(`compression.go:17-20`, `:129-172`). 토큰은 `cl100k_base` 근사(Claude 모델에도 동일, `agent/util.go:84-90`, `llm/client.go:252-254`).
- 구조: 앞 2개 메시지(system, user)는 고정, 그 뒤 라운드는 요약본으로 대체해 user 메시지 끝의 `<previous_review_summary>`에 붙이고, 최근 라운드(토큰 예산 안)만 원문 유지(`compression.go:92-123`, `:226-240`). 요약 프롬프트는 "발견 이슈, 도구 호출 결론, 완료/대기 과제, 현재 초점" 5항목(`prompts/memory_compression_task_system.md:1-31`).
- 알려진 어긋남(코드 확인 + 결과는 추론): `partitionMessages`가 "모두 들어가면 압축 불필요"라 주석하며 `compressEnd = len(messages)`를 반환하는데(`compression.go:106-111`), 호출자 `runCompression`은 `compressEnd > frozenEnd`이면 그대로 진행해(`compression.go:182-185`) **전체 이력을 요약**한다. 또한 활성 구간 예산은 frozen(diff 포함) 토큰을 빼지 않아(`compression.go:67-87`) 압축 후에도 80%를 넘어 루프가 중단될 수 있다. 큰 diff에서 조기 종료 원인이 될 수 있으나 실행으로 재현하지 않았다.
- 템플릿의 `MAIN_TASK/PLAN_TASK/MEMORY_COMPRESSION_TASK.timeout`(120/180/120)은 파싱만 되고 `agent`에서 읽지 않는다. 읽는 곳은 `REVIEW_FILTER_TASK.timeout`(`agent.go:566`)과 `RE_LOCATION_TASK.timeout`(`diff/relocation.go:32`)뿐이다(`Timeout` grep 결과). 선언만 있고 쓰이지 않는 설정이다.

---

## Q5. 검증 (finding 필터링) {#q5}

### 5.1 검증 단계 표

| 단계 | 입력 | 출력 | 모델·문맥 독립성 | 추가 파일 접근 | 위치 | 검증 |
|---|---|---|---|---|---|---|
| ① 구조화 출력 검증(도구 스키마) | `code_comment` 인자 | 필수 필드(`content`, 경로) 누락 항목 제거, 파싱 실패 시 오류 문자열 | 모델 아님(프로그램) | 해당 없음 | `internal/tool/code_comment.go:36-82` | 코드 확인 |
| ② 위치 유효성 | `existing_code` + diff | 줄 번호(없으면 0). **의미 검증 아님** | 모델 아님 (필요 시 재해석 LLM 1회, 위치만) | 없음 | `internal/diff/resolver.go:59-70`, `relocation.go:19-69` | 코드 확인 |
| ③ **Review Filter(별도 결함 검증)** | 해당 파일 diff + 그 파일의 코멘트들(`content`, `existing_code`만, ID `c-N`) | 틀렸다고 입증된 코멘트 ID JSON 배열 | **같은 모델·같은 LLM 클라이언트**, 그러나 **새 대화**(Main 대화·도구 결과·plan 공유 안 함) | **불가.** `Tools` 없이 호출하고, 프롬프트도 diff만으로 판정하라고 제한 | `internal/agent/agent.go:544-601` | 코드 확인 |
| ④ 사람/바깥 에이전트 판단 | 최종 JSON | (엔진 밖) 스킬·플러그인 문서가 "코멘트를 High/Medium/Low로 평가해 낮은 것 버려라" 지시 | 엔진 밖 | 바깥 에이전트 몫 | `plugins/open-code-review/commands/review.md` (Step 2) | 코드 확인(문서 파일, 엔진 코드 아님) |

### 5.2 Review Filter 상세

프롬프트 원문 `internal/config/template/prompts/review_filter_task_system.md:3-7`:

> These review comments come from an Agent that can invoke tools to obtain the full code context. You can currently only see the code diff.
> Therefore, your task is NOT to verify whether all review comments are correct, but to **filter out only those review comments that can be confirmed as incorrect based solely on the current diff**.
> For review comments whose correctness cannot be determined from the diff alone, even if you find them suspicious, you should let them pass — because the Agent may have access to context that you cannot see.

이 코멘트들은 전체 코드 문맥을 얻기 위해 도구를 호출할 수 있는 에이전트가 만든 것이고, 당신은 diff만 볼 수 있다. 따라서 모든 코멘트의 정확성을 검증하는 것이 아니라 **현재 diff만으로 틀렸다고 확인되는 코멘트만 걸러라.** diff만으로 판정 못 하면 의심스러워도 통과시켜라. 에이전트는 당신이 못 보는 문맥을 가졌을 수 있다.

`review_filter_task_user.md:7-11, 33-55`는 "검증이 아니라 **반증(falsify)**"을 핵심 원칙으로 두고, 출력은 ID 배열 JSON(`["c-0","c-2"]` 형태, 없으면 `[]`)이다.

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 생성과 검증이 같은 모델·문맥인가 | 모델/엔드포인트는 같음(`a.args.Model`, `a.args.LLMClient`). 문맥은 분리(새 메시지 2개)되고 Main의 사고·도구 결과를 보지 못함. **독립 모델 앙상블은 아님** | `agent.go:572-580` | 코드 확인 |
| 검증자가 추가 파일을 읽는가 | 아니오. 도구 정의 미전달 + 프롬프트 제약 | `agent.go:576-580`, `review_filter_task_system.md:3-7` | 코드 확인 |
| 무엇을 걸러내는가 | diff 안에서 모순이 드러나는 주장(예: 존재하지 않는 줄을 지목, 보이는 코드와 반대로 서술) | `review_filter_task_user.md:15-31` | 코드 확인 |
| 무엇을 못 거르는가 | 다른 파일의 로직·런타임 동작·비즈니스 의미가 걸린 주장은 통과시키도록 설계됨 → **호출부 근거를 다시 확인하지 않는다** | 위와 동일 | 코드 확인 |
| 실패 시 | 파싱 실패 또는 호출 오류면 모두 통과 | `agent.go:576-585`, `:624-634` | 코드 확인 |
| 단위 | 파일별 1회. 다른 파일의 코멘트와 비교하지 않음 | `agent.go:550`, `:599` | 코드 확인 |
| 제거 방식 | 파일 내 코멘트 순번(`c-N`)을 모아 컬렉터에서 삭제 | `internal/tool/comment_collector.go:52-72` | 코드 확인 |
| 중복 제거 | 없음(파일 간·실행 간) | `comment_collector.go:21-26` | 코드 확인 |

기능 지원 수준 (Q5 검증): **부분 지원.** 별도 결함 검증 단계는 있으나 **diff-only 반증 필터**이고 추가 근거 탐색을 하지 않는다. "코드 근거로 검증"은 Main 루프 안에서 모델이 스스로 `file_read`/`code_search`로 확인하는 것에 의존한다.

### 5.3 평가(evals)

- 저장소에 실행 가능한 평가 스크립트·벤치마크 데이터를 찾지 못했다. 찾은 범위: `scripts/`(설치·배포·GitHub 코멘트 게시 JS 테스트뿐), `cmd/testdiff`(diff 파서 확인용 개발 도구), `.github/workflows/`(release, pages, 자체 리뷰), `internal/**/*_test.go`.
- README의 벤치마크 수치(200개 PR, 1,505개 정답 이슈 등)는 이미지와 웹페이지 컴포넌트(`imgs/benchmark-*.png`, `pages/src/components/BenchmarkSection.tsx`)로만 존재하고 재현 경로는 확인하지 못했다(`git show --stat HEAD`로 확인한 최신 커밋도 이미지와 TSX만 변경). 제품 문구이므로 근거로 쓰지 않는다.
- 단위 테스트는 `diff`, `tool`(file_read, code_search), `llm`, `rules`, `session` 등에 있으나 Main 루프·압축·Review Filter(`performLlmCodeReview`, `runCompression`, `parseFilterResponse`)를 직접 검증하는 테스트는 없다(`*_test.go`에서 해당 심볼 grep 결과 없음).
