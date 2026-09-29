# claude-devtools Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/matt1398/claude-devtools.git`
- **분석 Commit SHA**: `1486f2042c87bb547a4e34808ab54ab34a33f132` (`v0.5.0-8-g1486f20`)
- **분석 일자**: `2026-09-29`
- **작업트리 상태**: `clean`
- **분석 목적**: `미정 (사용자 확인 필요)`
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

- 아직 없음

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/claude-devtools.md](../../wiki/projects/claude-devtools.md), [[claude-devtools-electron-process-and-ipc]], [[claude-devtools-session-discovery-and-jsonl-parsing]], [[claude-devtools-context-token-and-session-analysis]]
