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
  - src/main/utils/toolExtraction.ts
  - src/main/services/parsing/SessionParser.ts
  - src/main/types/messages.ts
  - src/main/ipc/sessions.ts
  - src/main/services/infrastructure/DataCache.ts
  - src/main/services/parsing/ClaudeMdReader.ts
  - test/main/utils/pathDecoder.test.ts
  - test/main/services/discovery/ProjectScanner.cwdSplit.test.ts
  - test/main/utils/jsonl.test.ts
  - test/main/services/parsing/SessionParser.test.ts
---

# [Q1] Claude Code 세션 로그를 어떻게 찾고 읽는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 코드 확인 (claude-devtools) + 실행 확인 (이 PC의 실제 Claude Code 2.1.301 로그 형식) / 레포 테스트는 미실행
- **이 문서로 만든 스펙**: [claude-code-session-log-reading](../capabilities/claude-code-session-log-reading.md)
- **선행 자료**: 이전 wiki 노트 `wiki/concepts/claude-devtools-session-discovery-and-jsonl-parsing.md` (`16cc3c8` 기준, 2026-10-16 삭제. 원문은 `git show b52364d:wiki/concepts/claude-devtools-session-discovery-and-jsonl-parsing.md`). 이번에 `1486f20`에서 다시 확인

---

## 1. 질문 및 결론

- **질문**: claude-devtools는 `~/.claude/projects`에서 프로젝트와 세션을 어떻게 찾고, 세션 JSONL을 어떻게 메시지로 바꾸며, 바뀌지 않은 파일을 어떻게 다시 읽지 않는가?
- **핵심 결론**: 디렉터리 이름은 경로를 복원할 수 없는 인코딩이라 **세션 안의 `cwd`를 진짜 프로젝트 경로로 쓴다**. JSONL은 줄 단위 스트리밍으로 읽고, **깨진 줄과 모르는 type은 건너뛴다**. 바뀌었는지는 **`mtime-크기` 지문**으로 판단해, 같으면 파싱도 전송도 하지 않는다.

---

## 2. 동작 설명

### 2.1 프로젝트 찾기
- 입력: Claude 기본 폴더(`~/.claude`, 설정으로 바꿀 수 있음) 아래 `projects/`.
- 처리:
  1. 하위 디렉터리 중 인코딩 규칙에 맞는 이름만 남긴다 (`isValidEncodedPath`).
  2. 디렉터리마다 맨 위의 `*.jsonl` 파일만 세션으로 본다. 하위 폴더(`<sessionId>/subagents/`)는 세션이 아니다.
  3. 로컬이면 세션마다 첫 `cwd`를 읽는다. SSH면 본문을 읽지 않는다(느려서).
  4. **서로 다른 실제 `cwd`가 2개 이상**이면 한 디렉터리를 여러 프로젝트로 나눈다. ID는 `<디렉터리이름>::<sha256(cwd) 앞 8자리>`. `cwd`가 없는 옛 세션은 나누는 판단에서 빼고 같은 프로젝트로 본다.
  5. 프로젝트를 최근 수정 시각 순으로 정렬한다.
- 출력: `Project { id, path, name, sessions[], createdAt, mostRecentSession }`.
- 실패: 디렉터리 하나가 실패해도 나머지는 돌려준다(`Promise.allSettled`로 성공만 모음).

### 2.2 디렉터리 이름 규칙 (Claude Code가 정함)
- claude-devtools는 "`/`와 `\`를 `-`로 바꾼다"고 가정한다 (`encodePath`).
- **이 PC에서 실제로 본 이름**: `C:\Users\SSAFY\.herdr\worktrees\...` → `C--Users-SSAFY--herdr-worktrees-...`. `:`, `\`, `.`이 모두 `-`가 됐고, 한글 폴더는 `Desktop----`처럼 글자마다 `-`가 된 것으로 보인다. (실행 확인: 디렉터리 이름 관찰. 정확한 변환 규칙은 Claude Code 소스가 아니라 관찰이므로 macOS·Linux는 미확인)
- 그래서 이름 → 경로 복원(`decodePath`)은 항상 추측이다. 표시 이름은 `cwd`의 마지막 부분을 먼저 쓰고, 없을 때만 복원 결과를 쓴다 (`extractProjectName`).
- 반대 방향(경로 → 이름, `encodePath`)은 `ClaudeMdReader`가 `MEMORY.md`를 찾을 때 쓴다. Windows 경로나 `.`이 들어간 경로에서는 실제 이름과 달라 못 찾을 것으로 보인다. (추론: 코드와 관찰한 이름을 비교한 것이며 실행하지 않음)

### 2.3 세션 목록
- 입력: 프로젝트 ID.
- 처리:
  1. 하위 프로젝트 ID면 로컬에서는 디렉터리를 다시 스캔해 그 `cwd`에 속한 세션만 남긴다(새 세션이 숨지 않게).
  2. 로컬에서는 **보여줄 내용이 없는 세션**(노이즈만 있는 세션)을 뺀다. 보여줄 내용 = 사이드체인이 아닌 assistant(모델 `<synthetic>` 제외) 또는 실제 user 입력·도구 결과. `<system-reminder>`, `<local-command-caveat>`만 있는 user 줄은 노이즈.
  3. 목록용 정보를 파일 한 번 읽기로 만든다 (`analyzeSessionFileMetadata`): 첫 사용자 메시지(최대 500자, 명령어·중단 메시지 제외, 없으면 `/명령어` 이름), 메시지 수, git 브랜치.
  4. 위 두 결과는 파일 경로별로 `mtime`과 크기가 같으면 다시 계산하지 않는다(메모리 캐시).
  5. 생성 시각 = 첫 사용자 메시지 시각, 없으면 파일 생성 시각. 생성 시각 내림차순으로 정렬한다.

### 2.4 세션 읽기 (JSONL → 메시지)
- 입력: 세션 파일 경로.
- 처리:
  1. 파일을 통째로 올리지 않고 줄 단위로 읽는다.
  2. 빈 줄은 건너뛰고, **JSON이 깨진 줄은 로그만 남기고 다음 줄로** 간다.
  3. `uuid`가 없는 줄은 건너뛴다(메타데이터 줄).
  4. type이 `user / assistant / system / summary / file-history-snapshot / queue-operation`이 아니면 건너뛴다.
  5. 남은 줄을 공통 메시지로 바꾼다: `uuid`, `parentUuid`, type, 시각(없으면 **지금 시각**), role, content(문자열 또는 블록 배열), usage, model, `requestId`, `cwd`, `gitBranch`, `isSidechain`, `isMeta`, 도구 호출(`tool_use` 블록), 도구 결과(`tool_result` 블록).
- 출력: 메시지 배열(파일 순서 유지). 이어서 사용자/내부 사용자/assistant/system, 메인/사이드체인으로 분류한다.
- 토큰 합계는 `requestId`마다 마지막 줄 하나만 센다 (`deduplicateByRequestId`). 메시지 배열 자체는 중복 제거하지 않는다.

**실제 로그에서 본 것** (실행 확인, Claude Code 2.1.301, 1552줄 세션 1개):
- 줄 type이 16종이다. `mode`, `attachment`, `ai-title`, `api-request` 등 claude-devtools 목록에 없는 type이 많다. `attachment` 말고는 모두 `uuid`가 없다.
- 첫 줄에는 `cwd`가 없고 5번째 줄(index 4)에 처음 나온다.
- assistant `requestId` 116개 중 80개가 여러 줄(최대 6줄)이다. 80개 모두 같은 `message.id`이고, **줄마다 다른 블록 하나**(`thinking`/`text`/`tool_use`)를 담고, **usage는 모든 줄이 같다**.
- 즉 한 응답이 블록 단위로 나뉘어 저장된다. 내용은 모든 줄을 이어야 하고, 토큰은 한 번만 세야 한다. `deduplicateByRequestId` 주석의 "output_tokens가 점점 늘어난다"는 이번 관찰과 다르다(옛 버전 동작일 수 있음, 미확인).

### 2.5 바뀌지 않은 세션은 다시 읽지 않기
- 입력: 프로젝트 ID, 세션 ID, 화면이 마지막으로 받은 지문(선택).
- 처리:
  1. 파일을 `stat`해서 지문 `"<mtimeMs>-<size>"`를 만든다. 실패하면 지문 없이 진행한다.
  2. 받은 지문과 같으면 `{ unchanged: true }`만 돌려준다(파싱·전송 없음).
  3. 다르면 메모리 캐시를 본다. 캐시는 최대 50개, 10분 TTL, 구조 버전 2. 지문이 다르면 그 항목을 버린다.
  4. 없으면 파싱 → 하위 에이전트 연결 → 화면용 묶음(chunk) 생성 후, **파싱 전에 잰 지문**과 함께 캐시에 넣는다.
  5. 돌려줄 때 원본 메시지 배열은 비운다(화면은 묶음만 씀).
- 실패: 예외가 나면 `null`.

### 2.6 원본의 약점 (스펙에서 '변경' 후보)
- **`extractCwd`는 깨진 줄 하나에 멈춘다.** `JSON.parse`가 반복문 바깥 `try`에 있어서, `cwd`보다 앞에 깨진 줄이 있으면 `null`을 돌려준다. 다른 읽기 함수는 깨진 줄을 건너뛴다. (코드 확인)
- **시각이 없는 줄은 '지금'으로 채운다.** 파일을 읽을 때마다 값이 바뀌고 정렬이 흔들린다. (코드 확인, 영향은 추론)
- **경로 → 디렉터리 이름 변환이 실제 규칙과 다르다** (2.2).
- **하위 프로젝트 정보는 프로세스 메모리에만 있다.** 전체 스캔 때 지워지고 다시 만든다. 로컬은 목록 조회 때 다시 스캔해서 맞추지만, SSH는 그대로라 오래된 분할이 남을 수 있다. (코드 확인, 영향은 추론)

---

## 3. 코드 근거 (`1486f20`)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 기본 폴더 | `src/main/utils/pathDecoder.ts:301-322` | `setClaudeBasePathOverride`, `getClaudeBasePath`, `getProjectsBasePath` | `~/.claude` 또는 설정값, 그 아래 `projects` |
| 이름 규칙 | `src/main/utils/pathDecoder.ts:27-95` | `encodePath`, `decodePath`, `extractProjectName` | 손실 있는 인코딩, legacy Windows `C--` 처리(:50-58), `cwd` 우선(:87-91) |
| 이름 검증 | `src/main/utils/pathDecoder.ts:124-198` | `isValidEncodedPath`, `isValidProjectId`, `extractBaseDir` | 하위 프로젝트 ID `::` + 8자리 hex |
| 프로젝트 스캔 | `src/main/services/discovery/ProjectScanner.ts:110-150` | `scan` | 이름 필터(:124-126), 배치 병렬(:129-133), 최근순(:137) |
| 디렉터리 스캔 | `src/main/services/discovery/ProjectScanner.ts:203-363` | `scanProject` | 맨 위 `.jsonl`(:209-211), 로컬만 `cwd`(:226-242), `cwd` 묶기(:258-268), 1개면 분할 안 함(:270-302), 분할(:304-358) |
| 하위 프로젝트 ID | `src/main/services/discovery/SubprojectRegistry.ts:33-42` | `register` | `sha256(cwd)` 앞 8자리 |
| `cwd` 읽기 | `src/main/utils/metadataExtraction.ts:41-75` | `extractCwd` | 첫 `cwd`에서 중단, 파싱 오류 시 전체 `null`(:55-72) |
| 세션 목록 | `src/main/services/discovery/ProjectScanner.ts:395-463` | `listSessions` | 하위 프로젝트 필터(:410-413), 노이즈 제외(:427-437), 생성순(:456) |
| 하위 프로젝트 재스캔 | `src/main/services/discovery/ProjectScanner.ts:1008-1014` | `getSessionFilterForProject` | 로컬만 다시 스캔 |
| 목록 정보 | `src/main/utils/jsonl.ts:360-648` | `analyzeSessionFileMetadata` | 메시지 수(:426-437), 브랜치(:439-441), 첫 메시지(:443-491) |
| 목록 정보 캐시 | `src/main/services/discovery/ProjectScanner.ts:781-841` | `buildLightSessionMetadata` | `mtime`+크기 비교(:799-820), 생성 시각(:823-827) |
| 노이즈 판단 | `src/main/services/discovery/SessionContentFilter.ts:38-43`, `:61`, `:113`, `:147` | `HARD_NOISE_*`, `hasNonNoiseMessages`, `isDisplayableEntry` | 보여줄 줄이 하나라도 있으면 true |
| 노이즈 캐시 | `src/main/services/discovery/ProjectScanner.ts:1409-1437` | `hasDisplayableContent` | `mtime`+크기 메모, 실패 시 false |
| 부분 실패 허용 | `src/main/services/discovery/ProjectScanner.ts:1335-1354` | `collectFulfilledInBatches` | 성공한 것만 모음 |
| 줄 단위 파싱 | `src/main/utils/jsonl.ts:52-82` | `parseJsonlFile` | 빈 줄 건너뜀(:69), 줄별 `try`(:71-78) |
| 줄 → 메시지 | `src/main/utils/jsonl.ts:104-217` | `parseChatHistoryEntry`, `parseMessageType` | `uuid` 없음 제외(:106-108), 시각 기본값(:173), 허용 type(:199-217) |
| 도구 블록 | `src/main/utils/toolExtraction.ts:10-63` | `extractToolCalls`, `extractToolResults` | `tool_use`/`tool_result` |
| 토큰 중복 제거 | `src/main/utils/jsonl.ts:233-309` | `deduplicateByRequestId`, `calculateMetrics` | `requestId`당 마지막 줄 |
| 분류 | `src/main/services/parsing/SessionParser.ts:68-140`, `src/main/types/messages.ts:125`, `:165`, `:270` | `parseSession`, `processMessages`, `isParsedRealUserMessage` 등 | 실제/내부 user, 메인/사이드체인 |
| 지문·캐시 | `src/main/ipc/sessions.ts:198-297` | `handleGetSessionDetail` | 지문(:224-231), unchanged(:239-245), 캐시(:248, :279), 메시지 제거(:287-292) |
| 캐시 | `src/main/services/infrastructure/DataCache.ts:37-43`, `:75`, `:156-175` | `DataCache` | 50개·10분·버전 2, 지문 불일치 시 폐기, 가득 차면 가장 오래 안 쓴 것 제거 |
| 역변환 사용처 | `src/main/services/parsing/ClaudeMdReader.ts:229-236` | `readAutoMemoryFile` | `encodePath(cwd)`로 `MEMORY.md` 경로 구성 |

---

## 4. 검증 과정 및 실행 결과

- **코드 읽기**: 위 표의 파일을 `1486f20`에서 직접 읽음.
- **레포 테스트**: `node_modules`가 없어 실행하지 않음(설치는 7.5 정책상 보류). 관련 테스트 위치만 확인: `test/main/utils/pathDecoder.test.ts`(:79 legacy Windows, :105-112 `cwdHint`, :156 잘못된 `:`), `test/main/services/discovery/ProjectScanner.cwdSplit.test.ts`(:35 분할 안 함, :73 분할), `test/main/utils/jsonl.test.ts:140`(목록 정보 한 번에), `test/main/services/parsing/SessionParser.test.ts`(:112 실제/내부 user, :152 사이드체인). **`requestId` 중복 제거 테스트는 없음.**
- **실제 로그 형식 확인** (대화 내용은 출력하지 않음):
  ```bash
  python -I artifacts/claude-devtools/log-format-demos/inspect_session_log.py <session.jsonl>
  ```
  결과: [`artifacts/claude-devtools/log-format-demos/2026-10-16-output.txt`](../../../artifacts/claude-devtools/log-format-demos/2026-10-16-output.txt) (2.4의 "실제 로그에서 본 것").

---

## 5. 남은 질문

- [ ] Claude Code의 정확한 디렉터리 이름 규칙(어떤 문자를 `-`로 바꾸는가), macOS·Linux에서도 같은가.
- [ ] `requestId` 반복 줄의 usage가 옛 버전에서는 점점 늘었는가 (원본 주석의 근거).
- [ ] `encodePath` 때문에 Windows에서 `MEMORY.md`를 실제로 못 찾는지 실행으로 확인.
- [ ] 세션 진행 중 판단(`isOngoing`, 5분 stale 규칙)과 하위 에이전트 파일 연결은 이 문서 범위 밖.
