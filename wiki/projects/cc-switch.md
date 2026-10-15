---
title: cc-switch
created: 2026-10-15
updated: 2026-10-15
type: project
tags: [open-source, project, architecture, proxy, claude-code, tauri, rust]
sources:
  - reports/cc-switch/overview.md
  - repos/cc-switch/README.md
  - repos/cc-switch/src-tauri/src/live/project/claude.rs
  - repos/cc-switch/src-tauri/src/proxy/server.rs
  - repos/cc-switch/src-tauri/src/proxy/providers/transform_gemini.rs
  - repos/cc-switch/src-tauri/src/session_manager/providers/claude.rs
  - repos/cc-switch/src-tauri/src/services/skill.rs
  - artifacts/cc-switch/skill-dup-probe/output.txt
confidence: medium
---

# cc-switch

Claude Code, Codex, Gemini CLI 등의 **provider 전환과 설정 관리** Tauri 2(Rust) 데스크톱 앱. 분석 SHA `d35726e`. 상세: `reports/cc-switch/overview.md`. 1차 분석이라 설정 복구/요청 처리 본문은 미확인.

## 핵심 (코드 확인)

- **"프록시로 관측하는 도구"는 오해다.** 주목적은 provider 전환이고, 프록시("Local Routing")는 선택 기능이며 사용량 기록은 부수 기능이다.
- **가로채기 방식**: MITM이 아니라 CLI의 base URL 설정을 `http://127.0.0.1:15721`로 바꾸고 키를 `PROXY_MANAGED`로 둔다. Claude Code는 `settings.json`의 `env.ANTHROPIC_BASE_URL` (`live/project/claude.rs proxy_projection`). 진짜 URL/키는 앱 SQLite에만 있다.
- **프록시 서버**: 앱 프로세스 안의 Rust(axum 0.7 + hyper + tokio) 서버. 요청 중계, 모델 별칭 매핑, 형식 변환, failover, 사용량 기록.
- **형식 변환**: Anthropic ↔ Gemini/OpenAI Chat/Responses 양방향(요청·응답·SSE). Claude Code UI를 유지한 채 Gemini 등을 쓸 수 있는 이유. 변환 파일 합계 약 2.7만 줄, `proxy/providers/` 커밋 193개(최근 83개는 2026-07 이후)로 유지보수 부담이 큼.
- **설치만으로는 설정이 안 바뀐다.** provider 활성화나 라우팅 on 때 쓴다. 첫 쓰기 전 원본을 `~/.cc-switch/backups/live-first-write/`에 백업(README 기준).
- **Session Manager와 무프록시 사용량 통계는 프록시와 무관**: `~/.claude/projects/**/*.jsonl` 등 로컬 로그를 읽는다.
- **Skills**: 원본은 `~/.cc-switch/skills/`(SSOT) 한 곳, 앱 폴더에는 symlink/복사로 배포. 비활성화는 앱 폴더 쪽만 삭제하고 원본은 유지, 삭제는 백업 후 전부 제거. 폴더째 옮기므로 Codex의 `agents/openai.yaml`도 같이 간다.
- **같은 이름·다른 내용 스킬은 앱별 변형이 보존되지 않는다** (실행 확인): 가져오기에서 먼저 발견된 쪽(Claude)이 원본이 되고, 재동기화/토글 때 다른 앱 폴더가 원본으로 통째로 교체되어 Codex 전용 yaml이 사라진다. Pi/Mcode만 충돌 시 덮어쓰기를 거부한다.
- **MCP**: 공통 형식으로 DB에 저장하고 앱별(Claude JSON, Codex TOML, OpenCode local/remote 등)로 변환해 id 단위로 추가/제거한다. DB에 없는 항목은 건드리지 않고, 가져오기에서 같은 id는 DB 정의가 이긴다 (코드 읽기, 미실행). **plugin/hooks/permissions는 관리하지 않고 provider 전환 때 보존만 한다.** 상세: `reports/cc-switch/questions/q6-mcp-per-app-conversion.md`.

## 미확인

- 라우팅 on/off, 앱 종료, 비정상 종료 시 설정 복구 (README 설명만 확인)
- 프록시가 요청 본문을 저장하는지(`usage/logger.rs`)
- 변환 품질 (실행 안 함)

관련: [[codeburn]] (로컬 로그 기반 사용량 분석), [[claude-devtools]] (Claude Code 세션 로그 읽기)
