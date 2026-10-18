---
sha: "1486f2042c87bb547a4e34808ab54ab34a33f132"
created: 2026-10-17
updated: 2026-10-17
sources:
  - src/main/services/discovery/WorktreeGrouper.ts
  - src/main/services/parsing/GitIdentityResolver.ts
  - src/main/services/discovery/ProjectScanner.ts
  - src/main/services/infrastructure/ConfigManager.ts
  - src/renderer/components/layout/SidebarHeader.tsx
  - src/renderer/components/sidebar/DateGroupedSessions.tsx
  - src/renderer/components/sidebar/SessionItem.tsx
  - src/renderer/utils/dateGrouping.ts
  - src/renderer/store/slices/sessionSlice.ts
  - test/main/services/discovery/WorktreeGrouper.test.ts
  - test/main/services/parsing/GitIdentityResolver.test.ts
status: draft
reimplementation: 미실행
---

# Claude Code 세션 선택 목록

> 로그 폴더의 프로젝트들을 git 저장소 단위로 묶어 고르게 하고, 고른 프로젝트의 세션을 "고정 → 날짜 그룹" 순으로, 20개씩 이어서 보여 준다.

적용 목적(가정): 세션 로그를 HTML로 보여 주는 로컬 도구의 첫 화면(세션 고르기). 사용자 한 명, 로컬 디스크, 로그는 읽기만 한다. **worktree는 무시한다**: 같은 저장소의 worktree가 따로 나와도 묶지 않고, 로그 프로젝트 폴더 하나를 선택지 하나로 본다(R-01~R-04 제외, 결정: 2026-10-17). 그래서 이 도구에서 저장소 > worktree 2단계는 "프로젝트" 1단계가 된다. 프로젝트·세션을 찾고 읽는 일은 [claude-code-session-log-reading](./claude-code-session-log-reading.md)(이하 "읽기 스펙")이 하고, 이 스펙은 그 결과를 **어떻게 묶고 정렬해 고르게 하는지**만 다룬다.

## A. 재구현 계약

### A0. 한눈에 보는 흐름
1. 읽기 스펙의 `listProjects`로 프로젝트 목록을 얻는다.
2. 프로젝트마다 어느 git 저장소의 것인지 알아내 같은 저장소끼리 묶는다(저장소 > worktree).
3. 사용자가 저장소(그리고 worktree)를 고른다. 세션이 없는 것은 선택지에서 뺀다.
4. 고른 프로젝트의 세션을 최근 수정순으로 20개 가져오고, 더 있으면 이어서 가져온다.
5. 화면에는 고정한 세션을 맨 위에, 나머지를 날짜 그룹(Today / Yesterday / Previous 7 Days / Older)으로 보여 준다. 숨긴 세션은 빼고, 정렬을 "컨텍스트 사용량순"으로 바꿀 수 있다.

### A1. 목적·범위·통합 지점
- 제공: 저장소 그룹 목록, worktree 목록, 세션 한 쪽(page), 세션 행 표시 정보, 고정·숨김 상태, 날짜 그룹.
- 제외: 세션 내용 읽기(읽기 스펙), 하위 에이전트, 검색, 여러 창/탭, 일괄 선택, 원격(SSH) 목록, 실시간 갱신.
- 외부 의존성: 읽기 스펙, 파일 읽기(git 메타 파일), 설정 저장소(고정·숨김을 담을 JSON 파일 등).
- 소유 상태·부작용: 고정·숨김 목록을 **로그와 별개의 설정 저장소**에 쓴다. 로그 파일은 수정하지 않는다.

### A2. 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `listRepositories()` | → list<RepositoryGroup> | 세션이 1개 이상 있는 저장소만. `mostRecentSession` 내림차순 |
| RepositoryGroup | `id`: string, `name`: string, `worktrees`: list<Worktree>, `totalSessions`: int, `mostRecentSession`: optional int(ms) | `id`는 R-02. `worktrees`는 세션이 있는 것만 |
| Worktree | `id`: string(= 프로젝트 id), `path`, `name`(표시명, R-04), `gitBranch`: optional, `isMain`: bool, `sessionIds`: list, `mostRecentSession` | 같은 저장소 안에서 메인이 먼저, 그다음 `mostRecentSession` 내림차순 |
| `listSessionRows(projectId, cursor?, limit=20)` | → `{sessions: list<SessionRow>, nextCursor: optional string, hasMore: bool}` | 정렬은 R-06 |
| SessionRow | `id`, `title`: string, `messageCount`: int, `createdAt`·`updatedAt`: int(ms), `isOngoing`: optional bool, `contextConsumption`: optional int | `title` = 읽기 스펙 `preview`, 없으면 "Untitled". `messageCount`는 읽기 스펙 `turnCount` 계산을 따른다 |
| Cursor | string = base64(JSON `{timestamp: int(ms), sessionId: string}`) | 이전 쪽 마지막 세션의 수정 시각과 id |
| Pin / Hidden | 프로젝트 id → list<`{sessionId, pinnedAt}` / `{sessionId, hiddenAt}`> | 최근에 한 것이 앞. 설정 저장소에 저장 |
| DateCategory | `Today` / `Yesterday` / `Previous 7 Days` / `Older` | 표시 순서도 이 순서 |
| SessionSortMode | `recent`(기본) / `most-context` | |

### A3. 행동 계약과 미결정 사항

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 채택 | 원본 검증 |
|---|---|---|---|---|
| R-01 | 프로젝트 하나의 저장소 판별 | 프로젝트 경로에서 위 폴더로 올라가며 가장 가까운 `.git`을 찾는다. `.git`이 **디렉터리**면 메인 저장소. **파일**이면 worktree이고, 파일 안 `gitdir: <경로>`(보통 `<메인>/.git/worktrees/<이름>`)에서 두 단계 위가 메인 `.git`이다. | **제외** (worktree·저장소 묶기를 하지 않음) | 코드 확인 |
| R-02 | 저장소 id | 메인 `.git`의 `origin` 원격 주소가 **있으면** 메인 저장소 **폴더 이름**, **없으면** 메인 저장소 **경로 전체**를 식별 문자열로 쓴다. 이를 소문자·양끝 공백 제거한 뒤 SHA-256 16진수 앞 12자가 id. 같은 id인 프로젝트는 한 그룹. | **제외** (worktree·저장소 묶기를 하지 않음) | 코드 확인 |
| R-03 | 경로가 디스크에 없음(삭제된 worktree) 또는 `.git`을 못 찾음 | 경로 모양으로 저장소 이름만 추정한다(예: `.cursor/worktrees/<repo>/<이름>`, `.claude-worktrees/<repo>/<이름>`, 그 외는 마지막 폴더). id는 **프로젝트 경로 전체**를 R-02의 "없으면" 방식으로 해시하므로 **그 프로젝트 하나만의 그룹**이 된다(메인 저장소와 합쳐지지 않음). 이름조차 못 구하면 저장소 없음으로 보고 프로젝트 id를 그룹 id로 쓴다. | **제외** (worktree·저장소 묶기를 하지 않음) | 코드 확인 (합쳐지지 않는 결과는 코드에서 도출, 미실행) |
| R-04 | worktree 표시명 | 메인이면 현재 브랜치(없으면 `main`). 일반 git worktree면 `.git/worktrees/<이름>`의 이름, 없으면 브랜치, 없으면 경로 마지막 폴더. 도구별 폴더 규칙(vibe-kanban, conductor, ccswitch 등)이 있으면 그 규칙의 이름. 저장소가 아니면 경로 마지막 폴더. | **제외** (worktree·저장소 묶기를 하지 않음) | 코드 확인 |
| R-05 | 선택지 필터 | 세션 수가 0인 저장소·worktree는 목록에서 뺀다. 저장소 안 worktree가 전부 비면 저장소도 뺀다. 이때 세션 수는 읽기 스펙 R-07의 노이즈 제외를 **하지 않고** 센다(기본 동작, 엄격 모드는 환경 변수로 켠다). | 원본 유지 | 코드 확인 |
| R-06 | 세션 정렬·쪽 나누기 | 파일 수정 시각 내림차순, 같으면 세션 id 오름차순. `cursor`가 있으면 그 지점 **다음** 항목부터 `limit`개. 한 개 더 가져와 `hasMore`를 정한다. 쪽 안에서 노이즈 세션(읽기 스펙 R-07)은 건너뛰고 채운다. | 원본 유지 | 코드 확인 |
| R-07 | 세션 행 정보 | 첫 화면 목록은 읽기 스펙의 가벼운 정보만 쓴다: `title`, `messageCount`, `createdAt`, `updatedAt`. `isOngoing`·`contextConsumption`은 이 가벼운 목록에는 없고, 깊은(`deep`) 목록에서만 계산된다(원본 화면은 `deep`을 요청하지 않는다). | 원본 유지 | 코드 확인 |
| R-08 | 날짜 그룹 | `max(updatedAt, createdAt)`이 오늘이면 Today, 어제면 Yesterday, 오늘과의 일수 차이가 7 이하면 Previous 7 Days, 나머지는 Older. 그룹 안은 입력 순서를 유지한다. 빈 그룹은 보이지 않는다. | 원본 유지 | 코드 확인 |
| R-09 | 고정 | 고정한 세션은 날짜 그룹과 따로 맨 위 "Pinned"에 최근 고정순으로 둔다. 고정하면 목록 맨 앞에 추가, 해제하면 제거(목록이 비면 프로젝트 항목 삭제). 이미 고정된 것은 다시 추가하지 않는다. | 원본 유지 | 코드 확인 |
| R-10 | 숨김 | 숨긴 세션은 기본으로 빼고, "숨긴 것 보기"를 켜면 포함해 보여 준다. 고정과 같은 방식으로 프로젝트별 저장. | 원본 유지 | 코드 확인 |
| R-11 | `most-context` 정렬 | 보이는 세션 전체를 컨텍스트 사용량 내림차순 한 줄로 보여 준다. 날짜 헤더와 Pinned 구역은 없다. 화면은 불러온 세션만 순위에 둔다(안내 문구 근거). 값이 비어 있는 세션의 순서는 정하지 않았다. | 원본 유지 | 코드 확인 (정렬 모드), 값이 채워지는 경로는 미확인 |
| R-12 | 프로젝트 id | 읽기 스펙의 프로젝트 id(`::해시` 포함)를 그대로 쓴다. 고정·숨김의 키도 이 id. | 원본 유지 | 코드 확인 |

- 불변식: 로그 파일을 수정하지 않는다. 같은 파일 상태와 같은 설정이면 같은 목록·같은 순서가 나온다(정렬에 id를 보조 키로 쓰는 이유).
- 미결정:
  - R-05 숨긴 노이즈 세션 수가 선택지의 `totalSessions`와 목록의 실제 개수가 다를 수 있다(세션 수는 노이즈를 세고, 목록은 건너뜀). 맞출지 정하지 않았다.
  - R-03 삭제된 worktree를 메인 저장소와 합칠지(경로 규칙으로 얻은 저장소 이름으로 묶기). 원본은 합치지 않는다.
  - R-09·R-10 설정 저장소 위치와 동시에 두 번 쓸 때의 규칙. 원본은 한 프로세스가 쓴다고 가정한다.
  - R-11 `most-context`가 쓰는 `contextConsumption`이 어디서 채워지는지. 목록은 항상 `light`로 요청하고 `light`에는 이 값이 없다. `deep`에서만 계산됨(B1 R-11 참고)까지만 확인했고, 화면이 값을 어떻게 얻는지는 못 찾았다. 재구현 시에는 `deep`으로 요청하거나 값이 없는 세션을 맨 뒤로 두는 규칙이 필요하다.
  - R-06 한 번에 수천 개 세션이 있을 때의 성능(원본은 쪽마다 폴더를 다시 읽고 정렬함).

### A4. 커스텀 선택지

| 관련 ID | 기본 정책 | 대안과 선택 기준 | 바꾸면 달라지는 보장 · 관련 사례 |
|---|---|---|---|
| R-01·R-03 | 파일 시스템의 `.git`을 읽어 판별 | 프로젝트 경로 모양만으로 묶기: 읽지 못하는 환경 | 삭제된 worktree도 묶을 수 있으나 같은 이름의 다른 저장소가 섞일 수 있다 · T-02 |
| R-04 | 도구별 이름 규칙 포함 | 일반 git 규칙만: 쓰는 도구가 정해져 있을 때 | 표시명이 달라질 수 있다(id는 그대로) |
| R-06 | 쪽 크기 20 | 전부 한 번에: 세션이 수백 개 이하일 때(정적 HTML 목록) | `nextCursor` 없이 한 번에 반환 |
| R-08 | 4개 날짜 그룹 | 월별 그룹: 오래된 세션이 많을 때 | 그룹 이름만 바뀐다 |

### A5. 핵심 수락 사례

| 사례 | 요구사항·정책 | Given / When | Then (출력·사후 상태) | 출처 |
|---|---|---|---|---|
| T-01 | R-01·R-02 | 메인 저장소 폴더(`.git`이 디렉터리)와, `.git` 파일이 그 메인을 가리키는 worktree 폴더를 각각 프로젝트로 둠 / `listRepositories` | 저장소 1개, worktree 2개. 메인이 먼저 | 원본 테스트 |
| T-02 | R-03 | 디스크에 없는 경로 `/x/.cursor/worktrees/app/feat-a`와 `/x/app`(메인, 디스크에 있음) | 그룹 2개(합쳐지지 않음). 앞쪽 그룹의 이름은 `app` | 계약에서 도출 (코드에서 읽은 것, 미실행) |
| T-03 | R-05 | 세션이 0개인 worktree와 1개인 worktree가 있는 저장소 | 선택지에는 1개짜리만. 둘 다 비면 저장소도 없음 | 계약에서 도출 |
| T-04 | R-06 | 수정 시각이 같은 세션 `b`, `a`, 더 오래된 `c`, limit=2 | 첫 쪽 `[a, b]`, `hasMore=true`. 그 쪽의 `nextCursor`로 다음 쪽 `[c]`, `hasMore=false` | 계약에서 도출 |
| T-05 | R-08 | 오늘 10시, 어제, 5일 전, 20일 전 수정된 세션 | 그룹: Today 1, Yesterday 1, Previous 7 Days 1, Older 1 | 계약에서 도출 |
| T-06 | R-09 | 세션 A를 고정한 뒤 B를 고정 | Pinned 순서 `[B, A]`. A를 다시 고정해도 그대로. A 해제 후 `[B]` | 계약에서 도출 |
| T-07 | R-10 | 세션 3개 중 1개를 숨김 | 기본 목록 2개. "숨긴 것 보기" 켜면 3개 | 계약에서 도출 |

## B. 근거와 참조 구현

### B1. 요구사항별 근거 지도
모든 위치는 `claude-devtools@1486f20`. 앞쪽 읽기 스펙의 근거는 [q1](../questions/q1-session-discovery-and-jsonl-parsing.md).

A5 원본 테스트 위치: T-01 `test/main/services/discovery/WorktreeGrouper.test.ts:48` (메인+worktree 그룹), `test/main/services/parsing/GitIdentityResolver.test.ts:38-45` (메인·worktree 판별). 레포에 R-03·R-05~R-11을 검사하는 테스트는 없다(`WorktreeGrouper` 테스트는 `it` 1개).

| ID | 원본에서 관찰한 동작 | 채택·변경 이유 | 근거 | 검증 수준 |
|---|---|---|---|---|
| R-01 | 위로 올라가며 `.git` 탐색, 파일이면 `gitdir:` 정규식으로 파싱해 메인 `.git` 계산 | — | `GitIdentityResolver.ts:39-110` `findGitPath` `resolveIdentity`, `:300-320` | 코드 확인 |
| R-02 | 원격 있으면 폴더 이름, 없으면 전체 경로, 소문자 SHA-256 12자 | — | `GitIdentityResolver.ts:391-420` `generateRepoId` | 코드 확인 |
| R-03 | 경로 없음/오류 시 `resolveIdentityFromPath`, 이름만 패턴 추정, id는 프로젝트 경로 해시 | 합쳐지지 않는 점은 미결정으로 남김 | `GitIdentityResolver.ts:136-200` `resolveIdentityFromPath` `extractRepoNameFromPath` | 코드 확인 (결과 도출은 미실행) |
| R-04 | 출처(`WorktreeSource`)별 switch | 출처별 규칙은 목적 따라 선택 | `GitIdentityResolver.ts:579-675` `getWorktreeDisplayName` | 코드 확인 |
| R-05 | 0개 worktree·저장소 제외. 기본은 노이즈 검사 생략(`CLAUDE_DEVTOOLS_STRICT_SESSION_FILTER=1`일 때만) | 숫자 불일치는 미결정 | `WorktreeGrouper.ts:52-175`, `SidebarHeader.tsx:316` | 코드 확인 |
| R-06 | 수정 시각 내림차순+id 보조 키, base64 cursor, limit+1로 `hasMore` | — | `ProjectScanner.ts:474-700` `listSessionsPaginated` | 코드 확인 |
| R-07 | 화면은 `metadataLevel: 'light'`, 첫 쪽 20개. light에는 `isOngoing`·`contextConsumption` 없음 | — | `sessionSlice.ts:127-150` `fetchSessionsInitial`, `ProjectScanner.ts:781-846` `buildLightSessionMetadata`, `SessionItem.tsx` 행 표시 | 코드 확인 |
| R-08 | `date-fns` `isToday`/`isYesterday`/`differenceInDays` | — | `dateGrouping.ts:24-48` `groupSessionsByDate` | 코드 확인 |
| R-09 | 앞에 추가, 해제 시 빈 목록 삭제 | — | `ConfigManager.ts:752-777`, `dateGrouping.ts:77-97` `separatePinnedSessions` | 코드 확인 |
| R-10 | 같은 구조로 `hiddenSessions` 저장, 기본 필터 | — | `ConfigManager.ts:790-810`, `DateGroupedSessions.tsx:111-114` | 코드 확인 |
| R-11 | `most-context`면 평평한 리스트. 목록 요청은 항상 `light`라 값의 출처는 미확인 | 값이 비는 문제는 미결정으로 남김 | `DateGroupedSessions.tsx:132-150`, `:409`, `ProjectScanner.ts:771` | 코드 확인 (정렬), 미확인 (값의 출처) |
| R-12 | 고정·숨김 키는 프로젝트 id | — | `ConfigManager.ts:196-197` | 코드 확인 |

### B2. 코드 읽는 순서

| 순서·역할 | repo@SHA | `파일:라인` · 심볼 | 여기서 볼 것 |
|---|---|---|---|
| 1. 저장소 판별 | claude-devtools@1486f20 | `src/main/services/parsing/GitIdentityResolver.ts:39-200` | `.git` 파일/디렉터리, id 해시, 경로 추정 |
| 2. 묶기 | claude-devtools@1486f20 | `src/main/services/discovery/WorktreeGrouper.ts:52-175` `groupByRepository` | 메인 먼저·최근순, 빈 것 제외 |
| 3. 세션 한 쪽 | claude-devtools@1486f20 | `src/main/services/discovery/ProjectScanner.ts:474-700` | cursor, limit+1 |
| 4. 화면 규칙 | claude-devtools@1486f20 | `src/renderer/components/sidebar/DateGroupedSessions.tsx:111-210`, `src/renderer/utils/dateGrouping.ts` | 고정→날짜 그룹, 숨김, 정렬 모드 |
| 5. 고정·숨김 저장 | claude-devtools@1486f20 | `src/main/services/infrastructure/ConfigManager.ts:752-810` | 프로젝트별 목록, 최근이 앞 |

### B3. 구현 비교·언어별 참고
- 비교 레포 없음. 같은 목적의 claude-code-history-viewer 등과의 비교는 다음 단계.
- 이 도구는 읽기 전용이라 정적 HTML 목록이면 쪽 나누기(R-06)·`nextCursor` 없이도 된다(A4).
- 관찰: 이 PC의 로그 폴더에는 `herdr` worktree 경로(`-Users-kkh--herdr-worktrees-…`)가 많다. 디스크에 남아 있으면 R-01로 메인과 합쳐지고, 지워졌으면 R-03대로 각자 한 그룹이 된다(미실행).

### B4. 재사용 출처 메모
- MIT (`repos/claude-devtools/LICENSE`). 이 스펙은 코드를 옮기지 않았다.

관련: [overview](../overview.md), [읽기 스펙](./claude-code-session-log-reading.md).
