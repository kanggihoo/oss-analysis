# claude-devtools Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/matt1398/claude-devtools.git`
- **분석 Commit SHA**: `1486f2042c87bb547a4e34808ab54ab34a33f132` (`v0.5.0-8-g1486f20`)
- **분석 일자**: `2026-09-29`
- **작업트리 상태**: `clean`
- **분석 목적**: `학습` — Claude Code가 쓰는 세션 `.jsonl` 로그를 claude-devtools가 어떻게 읽고(파싱), 묶고(chunk), 해석하는지 확인
- **메타데이터**: [`artifacts/claude-devtools/repo-metadata.txt`](../../artifacts/claude-devtools/repo-metadata.txt)
- **이전 baseline**: 2026-06 1차 분석과 DeepWiki snapshot(`artifacts/claude-devtools/deepwiki/`, 54/54 pages)은 `16cc3c8`(v0.5.0) 기준. 당시 메타데이터는 [`repo-metadata.2026-05-deepwiki-baseline.txt`](../../artifacts/claude-devtools/repo-metadata.2026-05-deepwiki-baseline.txt)에 보관
- **baseline 이후 변경**: 8 commits, 13 files, +39/−5 — docker compose 포트 override, standalone 서버 URL 출력, copy 버튼 확장, context navigation 후 AI group 펼침 유지 설정. 기존 wiki의 아키텍처 설명에 영향 없는 수준 (검증 수준: `코드 확인` — `git diff --stat 16cc3c8 HEAD`만 확인)
- **이전 산출물**: [initial-capture.md](./initial-capture.md), [wiki-ingestion-plan.md](./wiki-ingestion-plan.md)

---

## 2. 프로젝트 개요

GitHub 설명: "The missing DevTools for Claude Code — inspect session logs, tool calls, token usage, subagents, and context window in a visual UI." (MIT, ⭐3.9k, fork 301). Claude Code를 감싸지 않고 `~/.claude/projects`에 이미 쓰인 JSONL 세션 로그를 읽어 시각화하는 Electron + Vite + React TypeScript 앱. TS/TSX ~57.6k LOC, 399 files (`artifacts/claude-devtools/static-analysis/tokei.txt`).

### 소스 구성 (`src/`, 각 폴더에 `CLAUDE.md` 존재)

| 폴더 | 역할 (1차 wiki 기준, `16cc3c8`에서 코드 확인) |
|---|---|
| `src/main` | Electron main — `ServiceContext`(ProjectScanner/SessionParser/ChunkBuilder/DataCache/FileWatcher), IPC 핸들러, `http/` sidecar, `standalone.ts` |
| `src/preload` | typed `window.electronAPI` 노출 |
| `src/renderer` | React + Zustand UI |
| `src/shared` | main/renderer 공용 타입·유틸 |

### 주요 기능

제품 포지셔닝: Claude Code가 터미널에서 `Read 3 files` 같은 요약만 보여주는 문제(README "The Problem")를 겨냥해, 이미 저장된 로그에서 상세 내용을 재구성한다. Claude Code를 wrap·수정하지 않고(README "Not a Wrapper"), API 키·설정이 필요 없다. 설명의 1차 출처는 `README.md`이고, 아래 표의 "코드 근거"는 `1486f20` 로컬 소스에서 존재를 확인한 위치다.

| 기능 | 설명 (README 기준) | 코드 근거 | 검증 수준 |
|---|---|---|---|
| Tool Call Inspector | Read는 구문 강조, Edit는 inline diff, Bash 출력, subagent 트리까지 도구 호출별 전용 뷰어 | `src/renderer/components/chat/viewers/`(`CodeBlockViewer`, `DiffViewer`, `MarkdownViewer`, `MermaidViewer`), `src/main/services/analysis/ToolExecutionBuilder.ts` | 코드 확인(존재) / 동작 미확인 |
| Context Reconstruction | 턴별 context 토큰을 출처별로 귀속 (CLAUDE.md, @멘션 파일, tool I/O, thinking, 팀 오버헤드, 사용자 텍스트) | `src/renderer/types/contextInjection.ts`의 `ContextInjection` union | 코드 확인 — **README는 7개 카테고리(skills 포함)라 하나 union은 6개**(`claude-md`, `mentioned-file`, `tool-output`, `thinking-text`, `task-coordination`, `user-message`). skills 처리 위치 `미확인` |
| Compaction Visualization | context가 한계에 도달해 압축되는 시점과 손실 지점 표시 | `src/renderer/components/chat/CompactBoundary.tsx` | 코드 확인(컴포넌트 존재) |
| Team & Subagent Trees | agent별 실행 트리, tool trace, 토큰·시간·비용, 중첩 agent 재귀 렌더링 | `src/main/services/discovery/SubagentResolver.ts`, `analysis/SubagentDetailBuilder.ts`, `analysis/ProcessLinker.ts`, `src/main/ipc/subagents.ts` | 코드 확인(존재) |
| SSH Remote Sessions | `~/.ssh/config`를 읽어 원격 머신의 세션을 같은 pipeline으로 조회 | `infrastructure/SshConnectionManager.ts`, `SshConfigParser.ts`, `SshFileSystemProvider.ts`, `src/main/ipc/ssh.ts` | 코드 확인(존재) / 전환 동작 `미확인` |
| Notification Triggers | `.env` 접근, tool 에러, 고토큰 사용, 사용자 정의 regex에 시스템 알림 | `infrastructure/TriggerManager.ts`(builtin trigger, mode `content_match`/`error_status`/`token_threshold`, 기본 임계 8000 토큰), `NotificationManager.ts`, `error/` | 코드 확인 |
| Project Memory 뷰어 | `~/.claude/projects/<project>/memory/`의 `MEMORY.md`와 layer 파일을 렌더링, wikilink 이동, 외부 에디터 열기 | `discovery/MemoryReader.ts`, `src/main/ipc/memory.ts`, `src/renderer/components/memory/` | 코드 확인(존재) |
| 세션 검색 / Command Palette | Cmd+K로 세션 간 검색 | `discovery/SessionSearcher.ts`, `SearchTextCache.ts`, `src/renderer/components/search/` | 코드 확인(존재) |
| Multi-pane 레이아웃 | 여러 세션을 나란히 열고 탭을 드래그 | `src/renderer/components/layout/TabbedLayout.tsx`, store의 pane 관련 slice | 코드 확인(존재) / 드래그 동작 `미확인` |
| Export / Copy | 메시지·코드 블록 one-click 복사, 세션을 Markdown / JSON / plain text로 export | `src/renderer/utils/sessionExporter.ts`(`ExportFormat = 'markdown' \| 'json' \| 'plaintext'`) | 코드 확인 |
| 실시간 갱신 | JSONL 변경을 감지해 UI에 push | `infrastructure/FileWatcher.ts` (구조도 참고) | 코드 확인 |
| 배포 형태 | Electron 데스크톱(macOS/Linux/Windows) 외에 Docker/standalone(Fastify REST + SSE, 기본 포트 3456, `CLAUDE_ROOT`·`HOST`·`PORT` 환경변수) | `src/main/standalone.ts`, `infrastructure/HttpServer.ts` | 코드 확인(존재) / README의 "outbound network 호출 0"은 `미확인` |

- 위 표는 **기능의 존재 확인**이다. 각 기능의 실제 동작, 토큰 귀속 알고리즘, 설정 UI 세부는 질문별 분석에서 다룬다.
- 사용자 대상 흐름은 "세션 목록 → 세션 상세(chunk 기반 대화 뷰) → tool/subagent/context 상세 → 알림·검색·export"로 요약된다(`추론`: 컴포넌트 구성에서 본 것이며 화면 흐름을 실행해 확인하지 않음).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 12개 노드: renderer → preload/HTTP → IPC → ServiceContext → 파일시스템, FileWatcher push 경로 |
| 대표 실행 흐름 | — | — | 미작성 (다음 단계) |

- 기준: fresh clone `1486f20` (2026-09-29 재clone)
- 근거: `src/main/index.ts:114-156`(FileWatcher 이벤트 wiring), `:251-290`(서비스 생성·IPC 등록), `src/main/ipc/sessions.ts:214-279`(session detail: cache → parse → subagent → chunk), `src/renderer/api/index.ts`(electronAPI / HttpAPIClient 전환), `ServiceContext.ts:65-78`(context 구성원)
- archify 검증: showcase 9/9 checks, 0 error / 0 warning, 소스 참조를 `--repo-root`로 `1486f20`에서 확인, visual-check 통과(1440·1600·1920·2048, light/dark)
- **검증 수준**: 컴포넌트 존재·import·호출 관계 = `코드 확인` / Renderer 내부 컴포넌트 구조, SSH 전환 시 동작 = `미확인`

### 그림 읽는 가이드
1. **위쪽 `Renderer UI → api adapter`에서 시작합니다.** renderer 코드는 `window.electronAPI`를 직접 쓰지 않고 `api` Proxy만 씁니다. Electron이면 preload로, 브라우저면 `HttpAPIClient`로 갑니다.
2. **초록 굵은 선이 세션 조회 경로입니다.** `preload → IPC handlers → ServiceContextRegistry.getActive() → Session pipeline → FileSystemProvider → ~/.claude/projects`. 캐시에 fingerprint가 맞는 결과가 있으면 파싱을 건너뜁니다.
3. **왼쪽 `FileWatcher`는 반대 방향(push)입니다.** JSONL 변경을 감지하면 `file-change`를 renderer로 보내고, 에러 줄은 `NotificationManager`로 넘깁니다. 같은 이벤트가 HttpServer SSE로도 broadcast되지만 그림에는 생략했습니다.
4. **오른쪽 `HttpServer`(점선)는 standalone/Docker 모드입니다.** 같은 ServiceContext 서비스를 Fastify REST + SSE로 노출합니다.
5. **주의할 점**: `FileSystemProvider`가 Local/SSH(SFTP)를 추상화하므로 SSH 원격 세션도 같은 pipeline을 탑니다. `SshConnectionManager`·`ConfigManager`·`UpdaterService`는 생략했습니다.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: Claude Code 세션 로그를 어떻게 찾고 읽는가](./questions/q1-session-discovery-and-jsonl-parsing.md) - *디렉터리 이름 대신 세션 안의 `cwd`로 프로젝트 경로를 정하고, 깨진 줄·모르는 type은 건너뛰며, `mtime-크기` 지문이 같으면 다시 읽지 않는다. 실제 로그에서 같은 `requestId`의 줄이 블록 단위로 나뉘어 있음을 확인*
- [Q2: system prompt는 로그에 있고 devtools는 보여 주는가](./questions/q2-attachment-and-system-prompt.md) - *로그에는 `attachment`/`prompt_snapshot`으로 system prompt가 있고, devtools는 `attachment` 줄을 type 필터에서 버려 보여 주지 않는다(숨기려는 의도는 코드에서 확인되지 않음)*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: [capabilities/claude-code-session-log-reading.md](./capabilities/claude-code-session-log-reading.md) (draft), [capabilities/claude-code-session-picker.md](./capabilities/claude-code-session-picker.md) (draft)
- **이전 wiki 요약**: 2026-10-16 삭제. 원문은 `git show b52364d:wiki/projects/claude-devtools.md`, `git show b52364d:wiki/concepts/claude-devtools-electron-process-and-ipc.md`, `git show b52364d:wiki/concepts/claude-devtools-session-discovery-and-jsonl-parsing.md`, `git show b52364d:wiki/concepts/claude-devtools-context-token-and-session-analysis.md`
