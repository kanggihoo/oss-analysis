---
sha: "1486f2042c87bb547a4e34808ab54ab34a33f132"
created: 2026-10-16
updated: 2026-10-16
sources:
  - src/main/utils/pathDecoder.ts
  - src/main/services/discovery/ProjectScanner.ts
  - src/main/services/discovery/SubprojectRegistry.ts
  - src/main/services/discovery/SessionContentFilter.ts
  - src/main/utils/metadataExtraction.ts
  - src/main/utils/jsonl.ts
  - src/main/ipc/sessions.ts
  - src/main/services/infrastructure/DataCache.ts
  - src/main/services/parsing/ClaudeMdReader.ts
  - test/main/utils/pathDecoder.test.ts
  - test/main/services/discovery/ProjectScanner.cwdSplit.test.ts
status: draft
reimplementation: 미실행
---

# Claude Code 세션 로그 탐색과 읽기

> Claude Code가 디스크에 남긴 세션 로그 폴더를 받아, 프로젝트 목록 → 세션 목록 → 세션 메시지를 돌려주고, 바뀌지 않은 세션은 다시 읽지 않는다.

적용 목적(가정): Claude Code를 감싸지 않고 이미 저장된 로그만 읽어 대화 기록·사용량을 보여 주는 다른 도구에 넣는다. 로컬 디스크만 대상으로 한다.

## A. 재구현 계약

### A0. 한눈에 보는 흐름
1. 로그 루트 아래 프로젝트 디렉터리를 나열한다.
2. 디렉터리마다 세션 파일을 찾고, 세션 안의 `cwd`로 실제 프로젝트 경로를 정한다. 경로가 여럿이면 프로젝트를 나눈다.
3. 프로젝트를 고르면 보여줄 내용이 있는 세션만 목록 정보와 함께 돌려준다.
4. 세션을 고르면 파일을 줄 단위로 읽어 공통 메시지 배열로 바꾼다.
5. 다시 요청이 오면 파일 지문을 비교해 같으면 "변경 없음"만 돌려준다.

### A1. 목적·범위·통합 지점
- 제공: 프로젝트 목록, 세션 목록(미리보기 포함), 세션 메시지 배열, 토큰 합계, 변경 없음 판정.
- 제외: 화면용 대화 묶기(chunk), 하위 에이전트 파일 연결, 컨텍스트 토큰 분석, 진행 중 판정, 원격(SSH) 읽기, 파일 감시, 검색.
- 외부 의존성: 디렉터리 나열, 파일 정보(수정 시각·크기·생성 시각), 줄 단위 읽기, 홈 디렉터리, 해시 함수(SHA-256).
- 소유 상태·부작용: 로그를 **읽기만** 한다. 선택적으로 메모리 캐시(파일 경로 → 지문 + 결과)를 가진다.

### A2. 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `listProjects(root?)` | → list<Project> | `root` 기본값은 `<home>/.claude/projects`. 없으면 빈 목록(오류 아님). |
| `listSessions(projectId)` | → list<SessionSummary> | 프로젝트 하나의 세션 |
| `readSession(projectId, sessionId, knownFingerprint?)` | → `{unchanged: true, fingerprint}` 또는 `{messages, metrics, fingerprint}` | |
| Project | `id`: string, `path`: string, `pathIsGuess`: bool, `name`: string, `sessionIds`: list<string>, `lastModified`: int(ms) | `id`는 디렉터리 이름, 나뉜 경우 `<디렉터리 이름>::<sha256(cwd) 16진수 앞 8자>`. 같은 입력이면 같은 id. |
| SessionSummary | `id`, `preview`: optional string(≤500자), `turnCount`: int, `gitBranch`: optional string, `createdAt`·`updatedAt`: int(ms) | `id` = 파일 이름에서 `.jsonl`을 뺀 것 |
| Message | `uuid`, `parentUuid`: optional, `type`, `timestamp`: optional 시각, `role`, `content`: string 또는 list<Block>, `usage`: optional, `model`, `requestId`, `cwd`, `gitBranch`, `isSidechain`: bool, `isMeta`: bool, `toolCalls`, `toolResults` | 배열 순서 = 파일의 줄 순서. `isMeta=true`인 user는 도구 결과·시스템이 만든 줄. |
| Block | `type`이 `text`/`thinking`/`tool_use`/`tool_result`/`image` 등 | 모르는 블록 type도 그대로 둔다 |
| Metrics | `inputTokens`, `outputTokens`, `cacheReadTokens`, `cacheCreationTokens`, `totalTokens`(네 값의 합), `messageCount`(메시지 배열 길이), `durationMs`(가장 늦은 시각 − 가장 이른 시각): int | 토큰은 R-11 규칙으로 센다. 값이 없으면 0 |
| 실제 사용자 입력 | Message에 대한 판정 | `type=user`, `isMeta`가 아님, 내용이 문자열이면 비어 있지 않고, 배열이면 `text`나 `image` 블록이 있음. 단 내용(또는 텍스트 블록)이 `<local-command-stdout>`·`<local-command-stderr>`·`<local-command-caveat>`·`<system-reminder>`·`<teammate-message`로 시작하거나, 블록이 `[Request interrupted by user`로 시작하는 텍스트 하나뿐이면 아님. `<command-name>`(슬래시 명령)은 사용자 입력이다. |
| Fingerprint | string `"<수정시각 ms>-<바이트 크기>"` | 같으면 내용이 같다고 본다 |

### A3. 행동 계약과 미결정 사항

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 채택 | 원본 검증 |
|---|---|---|---|---|
| R-01 | 루트 바로 아래 항목 | 디렉터리이면서 이름 규칙(아래 A4)을 통과한 것만 프로젝트 후보. 후보 하나가 실패해도 나머지는 돌려준다. | 원본 유지 | 코드 확인 |
| R-02 | 프로젝트 디렉터리 | 바로 아래 `*.jsonl` 파일만 세션이다. 하위 폴더 안 파일은 세션이 아니다. | 원본 유지 | 코드 확인 |
| R-03 | 디렉터리 이름 | 이름에서 경로를 복원하는 것은 **추측**이다(여러 문자가 모두 `-`가 됨). `path`는 세션에서 처음 나오는 `cwd`를 쓰고, `cwd`가 없을 때만 복원값을 쓰며 `pathIsGuess=true`. `name`은 `path`의 마지막 부분. | 원본 유지 (+`pathIsGuess` 신규) | 코드 확인, 이름 규칙은 실행 확인(Windows) |
| R-04 | `cwd` 찾기 중 깨진 줄 | 깨진 줄을 건너뛰고 다음 줄에서 계속 찾는다. | **변경** (원본은 전체 실패) | 코드 확인 |
| R-05 | 한 디렉터리에 서로 다른 실제 `cwd`가 2개 이상 | `cwd`별로 프로젝트를 나누고 id는 `::해시`(해시 입력은 드라이브 문자를 대문자로 바꾼 `cwd` 문자열). `cwd`가 없는 세션은 나눌지 판단에 넣지 않는다. 나눌 때는 그것끼리 별도 프로젝트(`pathIsGuess=true`). `cwd`가 1개 이하면 나누지 않는다. | 원본 유지 | 코드 확인 + 원본 테스트 |
| R-06 | 프로젝트 목록 | 세션 파일 수정 시각의 최댓값(`lastModified`) 내림차순. | 원본 유지 | 코드 확인 |
| R-07 | 세션 목록 | 보여줄 줄이 하나도 없는 세션은 뺀다. 보여줄 줄 = 사이드체인이 아닌 assistant(모델 `<synthetic>` 제외), 또는 `<system-reminder>`·`<local-command-caveat>`만으로 된 것이 아닌 user. | 원본 유지 | 코드 확인 |
| R-08 | 세션 목록 정보 | `preview` = `isMeta`가 아닌 첫 user 텍스트(`<local-command-stdout>`·`<local-command-stderr>`로 시작하는 명령 출력, 중단 메시지, `<command-name>`으로 시작하는 것 제외, 500자 자름). 없으면 첫 `<command-name>`의 `/명령어` 이름. `turnCount` = 실제 사용자 입력(A2) 수 + 각 입력 뒤 첫 메인 assistant(사이드체인·`<synthetic>` 제외) 응답 수. `gitBranch` = 처음 나온 값. `createdAt` = preview 시각, 없으면 파일 생성 시각. `createdAt` 내림차순. | 원본 유지 | 코드 확인 |
| R-09 | 세션 줄 읽기 | 줄 단위로 읽는다(파일 전체를 메모리에 올리지 않음). 빈 줄·깨진 줄은 건너뛰고 개수만 센다. `uuid`가 없는 줄, type이 `user`/`assistant`/`system`/`summary`/`file-history-snapshot`/`queue-operation`이 아닌 줄은 건너뛴다. | 원본 유지 (+깨진 줄 개수 신규) | 코드 확인, 모르는 type이 많음은 실행 확인 |
| R-10 | `timestamp`가 없는 줄 | `timestamp`를 비워 둔다. 정렬이 필요하면 줄 순서를 쓴다. | **변경** (원본은 읽은 시점의 현재 시각) | 코드 확인 |
| R-11 | 같은 `requestId`의 assistant 줄 여러 개 | 모든 줄을 메시지로 남긴다(한 응답의 블록이 줄마다 나뉘어 있음). 토큰 합계(`metrics`)는 `requestId`마다 마지막 줄 하나만 더한다. | 원본 유지 | 코드 확인, 형식은 실행 확인 |
| R-12 | `readSession`에 `knownFingerprint`가 현재 지문과 같음 | `{unchanged: true}`만 돌려주고 파일을 읽지 않는다. 지문을 못 구하면 이 단축을 쓰지 않는다. | 원본 유지 | 코드 확인 |
| R-13 | 캐시 저장 | 결과는 **읽기 전에 잰 지문**과 묶는다. 읽는 도중 파일이 바뀌면 다음 요청에서 지문이 달라 다시 읽는다. | 원본 유지 | 코드 확인 |
| R-14 | `cwd`로 프로젝트를 찾아야 할 때 | 경로를 인코딩해 디렉터리 이름을 만들지 않는다. `listProjects` 결과의 `path`와 비교해 찾는다. | **변경** (원본은 단순 인코딩으로 이름을 만듦) | 추론 (원본이 Windows에서 실패할 것으로 봄, 미실행) |

- 불변식: 로그 파일을 수정하지 않는다. 같은 파일 상태(지문)에서는 같은 결과를 낸다(R-10 변경이 이를 위한 것).
- 미결정:
  - R-01 이름 규칙의 정확한 형태. Claude Code가 어떤 문자를 `-`로 바꾸는지 공식 근거가 없다. 관찰상 `:`, `\`, `/`, `.`, 한글이 `-`가 된다(Windows만 확인). 엄격하게 검사하면 새 형식을 놓칠 수 있다.
  - R-05 나뉜 프로젝트에서 `cwd` 없는 세션을 별도 프로젝트로 둘지, 가장 짧은 `cwd` 프로젝트에 붙일지.

### A4. 커스텀 선택지

| 관련 ID | 기본 정책 | 대안과 선택 기준 | 바꾸면 달라지는 보장 · 관련 사례 |
|---|---|---|---|
| R-01 | `-`로 시작하거나 `<드라이브 문자>--`로 시작하고, 영숫자·`_`·`.`·공백·`-`(그리고 맨 앞 드라이브 `:`)만 있는 이름 | 모든 디렉터리를 후보로 받기: 새 이름 형식을 놓치면 안 될 때 | 관계없는 폴더가 프로젝트로 보일 수 있다 · T-01 |
| R-07 | 노이즈 세션 숨김 | 모두 보여주기: 디버깅 도구일 때 | 세션 수가 Claude Code 화면과 달라진다 |
| R-12·R-13 | 메모리 캐시 최대 50개, 10분, 가장 오래 안 쓴 것부터 제거 | 캐시 없음: 메모리가 작거나 요청이 드물 때 | 같은 세션을 다시 열 때 다시 읽는다. 지문 단축(R-12)은 캐시 없이도 동작 · T-06 |

### A5. 핵심 수락 사례

| 사례 | 요구사항·정책 | Given / When | Then (출력·사후 상태) | 출처 |
|---|---|---|---|---|
| T-01 | R-03 | 디렉터리 `-Users-name-claude-devtools`, 세션 `cwd` = `/Users/name/claude-devtools` / `listProjects` | `name` = `claude-devtools`(복원만 하면 `devtools`), `pathIsGuess=false` | 원본 테스트 |
| T-02 | R-05 | 한 디렉터리에 `cwd`가 있는 세션 1개 + `cwd`가 없는 세션 1개 | 프로젝트 1개, id = 디렉터리 이름(`::` 없음), 세션 2개 | 원본 테스트 |
| T-03 | R-05 | 한 디렉터리에 `cwd`가 `/a/p`, `/a/other-p`인 세션 | 프로젝트 2개, 둘 다 id에 `::` + 8자리 16진수 | 원본 테스트 |
| T-04 | R-04, R-09 | 세션 줄: 정상 user / 깨진 JSON / `cwd` 있는 정상 assistant | 메시지 2개, 깨진 줄 1개로 집계. 프로젝트 `path` = 그 `cwd` | 계약에서 도출 (R-04는 원본과 다름) |
| T-05 | R-09, R-11 | 같은 `requestId`의 assistant 줄 3개(블록 `thinking`/`text`/`tool_use` 각 1개, usage 입력 10·출력 5로 같음) + `uuid` 없는 `mode` 줄 | 메시지 3개, `mode` 줄 없음. metrics 입력 10·출력 5 (30·15가 아님) | 계약에서 도출, 형식은 실제 로그 관찰 |
| T-06 | R-12 | `readSession`이 돌려준 지문을 파일을 바꾸지 않고 다시 전달 | `{unchanged: true}`, 파일 읽기 0회. 파일에 한 줄을 추가한 뒤에는 새 메시지 배열과 다른 지문 | 계약에서 도출 |

## B. 근거와 참조 구현

### B1. 요구사항별 근거 지도
근거 상세: [q1](../questions/q1-session-discovery-and-jsonl-parsing.md). 모든 위치는 `claude-devtools@1486f20`.

A5 원본 테스트 위치: T-01 `test/main/utils/pathDecoder.test.ts:105-112`, T-02 `test/main/services/discovery/ProjectScanner.cwdSplit.test.ts:35-71`, T-03 같은 파일 `:73-107`. 레포에 R-04·R-11·R-12를 검사하는 테스트는 없다.

| ID | 원본에서 관찰한 동작 | 채택·변경 이유 | 근거 | 검증 수준 |
|---|---|---|---|---|
| R-01 | 이름 정규식 필터, `allSettled`로 성공만 모음 | — | `ProjectScanner.ts:124-133` `scan`, `:1335-1354` `collectFulfilledInBatches`, `pathDecoder.ts:124-160` `isValidEncodedPath` | 코드 확인 |
| R-02 | 맨 위 `.jsonl`만 | — | `ProjectScanner.ts:209-211` `scanProject` | 코드 확인 |
| R-03 | `cwd` 우선, 복원은 대체용 | 추측 여부를 데이터로 드러내려고 `pathIsGuess` 추가 | `pathDecoder.ts:45-95` `decodePath` `extractProjectName`; 실제 이름은 [로그 관찰](../../../artifacts/claude-devtools/log-format-demos/2026-10-16-output.txt) | 코드 확인 + 실행 확인 |
| R-04 | `JSON.parse` 예외가 반복문 밖에서 잡혀 `null` | 앞쪽 깨진 줄 하나로 프로젝트 경로를 잃지 않게 | `metadataExtraction.ts:55-72` `extractCwd` | 코드 확인 |
| R-05 | 실제 `cwd` 2개 이상일 때만 분할, `sha256(cwd)` 8자 | — | `ProjectScanner.ts:258-358`, `SubprojectRegistry.ts:33-42` `register` | 코드 확인 |
| R-06 | 최근 수정 시각 내림차순 | — | `ProjectScanner.ts:137`, `:278-285` | 코드 확인 |
| R-07 | 노이즈 type·태그 판단, `mtime`+크기로 메모 | — | `SessionContentFilter.ts:38-43`, `:113` `isDisplayableEntry`; `ProjectScanner.ts:1409-1437` | 코드 확인 |
| R-08 | 파일 한 번 읽기로 목록 정보 계산 | — | `jsonl.ts:426-491` `analyzeSessionFileMetadata`, `ProjectScanner.ts:823-827`, `:456` | 코드 확인 |
| R-09 | 줄별 `try`, `uuid`·type 필터 | 문제 파일을 찾을 수 있게 깨진 줄 개수 추가 | `jsonl.ts:52-82` `parseJsonlFile`, `:104-113`, `:199-217` `parseMessageType` | 코드 확인 + 실행 확인(type 16종) |
| R-10 | `timestamp` 없으면 `new Date()` | 같은 파일이면 같은 결과가 나오게 | `jsonl.ts:173` | 코드 확인 |
| R-11 | 메시지는 그대로, 합계만 `requestId`당 마지막 줄 | — (원본 주석의 "출력 토큰이 늘어난다"는 관찰과 다름) | `jsonl.ts:233-309` `deduplicateByRequestId` `calculateMetrics` | 코드 확인 + 실행 확인 |
| R-12 | `mtimeMs-size` 비교 후 sentinel | — | `ipc/sessions.ts:224-245` `handleGetSessionDetail` | 코드 확인 |
| R-13 | 파싱 전 지문으로 캐시, 50개·10분·버전 2 | — | `ipc/sessions.ts:248-279`, `DataCache.ts:37-43`, `:75`, `:156-175` | 코드 확인 |
| R-14 | `encodePath`는 `/`·`\`만 `-`로 바꿈 | 실제 이름에서는 `.`·`:`도 `-`라서 맞지 않음 | `pathDecoder.ts:27-36`, `ClaudeMdReader.ts:229-236` `readAutoMemoryFile` | 추론 |

### B2. 코드 읽는 순서

| 순서·역할 | repo@SHA | `파일:라인` · 심볼 | 여기서 볼 것 |
|---|---|---|---|
| 1. 경로 규칙 | claude-devtools@1486f20 | `src/main/utils/pathDecoder.ts:27-198` | 인코딩·복원·검증, 하위 프로젝트 id 형태 |
| 2. 프로젝트 찾기 | claude-devtools@1486f20 | `src/main/services/discovery/ProjectScanner.ts:110-363` `scan` `scanProject` | `cwd`로 나누는 판단 |
| 3. 세션 목록 | claude-devtools@1486f20 | `ProjectScanner.ts:395-463` `listSessions`, `src/main/utils/jsonl.ts:360-648` `analyzeSessionFileMetadata` | 노이즈 제외, 목록 정보 |
| 4. 줄 → 메시지 | claude-devtools@1486f20 | `src/main/utils/jsonl.ts:52-217` `parseJsonlFile` `parseChatHistoryEntry` | 건너뛰는 줄, 필드 매핑 |
| 5. 변경 감지·캐시 | claude-devtools@1486f20 | `src/main/ipc/sessions.ts:198-297` `handleGetSessionDetail`, `src/main/services/infrastructure/DataCache.ts:75-175` | 지문 단축, 캐시 폐기 조건 |

### B3. 구현 비교·언어별 참고
- 비교 레포 없음. 같은 로그를 읽는 codeburn(`reports/codeburn/`), claude-code-history-viewer(`reports/claude-code-history-viewer/`), tokscale과의 비교는 다음 단계.
- 원본은 SSH일 때 R-03(`cwd` 읽기)·R-07(노이즈 제외)을 건너뛰고, 실패하면 파일 정보만으로 목록을 만든다(`ProjectScanner.ts:226`, `:400`, `:847-896`). 원격을 지원할 때 참고.

### B4. 재사용 출처 메모
- MIT (`repos/claude-devtools/LICENSE`). 이 스펙은 코드를 옮기지 않았다.

관련: [overview](../overview.md), [Q1](../questions/q1-session-discovery-and-jsonl-parsing.md).
