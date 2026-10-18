---
sha: "aeac41d4d005999432bb7312f7ff06383a91d59d"
created: 2026-10-17
updated: 2026-10-17
---

# agent-skills Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/addyosmani/agent-skills.git`
- **분석 Commit SHA**: `aeac41d4d005999432bb7312f7ff06383a91d59d` (`0.6.13`, 2026-10-13)
- **작업트리 상태**: `Clean`
- **분석 목적**: `학습` — Claude Code hook을 어떤 이벤트에 어떻게 연결하고 동작에 반영하는지, 그리고 hook이 "강제"인지 "보조"인지 확인 (context-mode와 비교)
- **메타데이터**: [`artifacts/agent-skills/repo-metadata.txt`](../../artifacts/agent-skills/repo-metadata.txt)

---

## 2. 프로젝트 개요

`.claude-plugin/plugin.json` 설명: "Production-grade engineering skills for AI coding agents — covering the full software development lifecycle from spec to ship." 라이선스 MIT, 버전 0.6.13 (`plugin.json`: 코드 확인). 핵심은 **skill 모음**(`skills/` 25개 디렉토리: 코드 확인)이고 hook은 부수 요소다.

### 소스 구성

| 위치 | 역할 | 검증 수준 |
|---|---|---|
| `skills/` | 개발 단계별 skill (예: `source-driven-development`, `spec-driven-development`) | 디렉토리 확인, 내용 `미확인` |
| `.claude/commands/`, `commands/` | slash command (`/spec`, `/code-simplify` 등) | 존재만 확인 |
| `agents/` | persona(역할) 정의 | 존재만 확인 |
| `hooks/` | hook 스크립트 3종 + 테스트 + 설명 문서. **hooks.json 없음** | 코드 확인 |
| `.claude-plugin/`, `.codex-plugin/`, `.gemini/`, `.opencode/` | 호스트별 플러그인 매니페스트 | 존재만 확인 |
| `evals/` | skill 평가 (`plugin.json`의 `experimental.evals`) | 존재만 확인 |

### 주요 기능 (hook 관점)

| 기능 | 설명 | 코드 근거 | 검증 수준 |
|---|---|---|---|
| `session-start.sh` | `SessionStart`에서 `using-agent-skills` 메타 skill을 `additionalContext`로 주입. **Claude Code 플러그인은 이를 등록하지 않음**(Claude Code가 skill을 자체 라우팅하므로 이중 라우터 방지). skill 라우팅이 없는 호스트용 | `hooks/session-start.sh`, `CONTRIBUTING.md` 93행, `docs/codex-setup.md` 35행 | 코드 확인 |
| `simplify-ignore.sh` | `/code-simplify` 중 `simplify-ignore-start/end`로 표시한 코드 블록을 모델이 못 보게 함. `PreToolUse Read`에서 파일을 백업하고 블록을 `BLOCK_<hash>` placeholder로 **파일 자체를 바꿔 쓰고**, `PostToolUse Edit\|Write`에서 복원, `Stop`에서 남은 placeholder를 복원 | `hooks/simplify-ignore.sh`, `hooks/SIMPLIFY-IGNORE.md` | 코드 확인(구성) / 동작 `미확인` |
| `sdd-cache-pre/post.sh` | `WebFetch` 결과를 URL 기준으로 캐시. `PreToolUse`에서 HEAD 요청(`ETag`/`Last-Modified`)으로 최신 여부 확인 후 304이면 **exit 2로 fetch를 막고 캐시 내용을 stderr로 에이전트에 전달**. `PostToolUse`(`async`)에서 저장 | `hooks/sdd-cache-pre.sh` 106행 `exit 2`, `hooks/SDD-CACHE.md` | 코드 확인(exit 2) / 실제 동작 `미확인` |

### hook 등록 방식

- 플러그인이 hook을 자동 등록하지 않는다. 사용자가 `.claude/settings.json`에 직접 붙여 넣는 방식이다 (`hooks/SIMPLIFY-IGNORE.md`, `SDD-CACHE.md`의 Setup: 코드 확인). 이 레포 자신의 `.claude/`에도 `settings.json`이 없다 (`commands`, `rules`만 있음: 코드 확인).
- 경로는 `${CLAUDE_PROJECT_DIR}/hooks/<script>.sh`. 항목에 `timeout`(10)과 `async: true`를 쓴다 (`SDD-CACHE.md`).
- 결론: 이 레포의 hook은 **opt-in 보조 도구**이고, 규칙을 강제하는 장치가 아니다. 강제는 skill 문서(지시문)가 맡는다 (`추론`: skill 내용은 아직 읽지 않음).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

`미작성`

---

## 4. 질문과 조사 기록 (Questions)

- [Q1: Claude Code hook 설정과 트리거 시 동작](./questions/q1-claude-code-hook-setup-and-trigger.md) - *settings.json에 이벤트→matcher→command로 설정, 트리거되면 stdin JSON을 받고 exit 0 통과 / exit 2 차단+stderr 전달*

---

## 5. 다음 작업 및 연계 링크

- **기능 스펙**: 없음
