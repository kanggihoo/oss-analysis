# CC Switch Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/farion1231/cc-switch.git`
- **분석 Commit SHA**: `d35726e28695844deaf0098450b34911f5be7b78` (2026-10-06)
- **분석 일자**: `2026-10-15`
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습. "프록시로 CLI를 관측하는 도구인가?"라는 초기 가설 검증, 프록시 동작 원리 파악

> 이번 세션은 사용자 질문에 답하며 코드를 부분적으로 읽은 1차 분석이다. archify 다이어그램은 아직 만들지 않았다.

---

## 2. 프로젝트 개요

Claude Code, Codex, Gemini CLI 등 AI 코딩 CLI의 **provider 전환과 설정(MCP/Skills/Prompts) 관리** 데스크톱 앱 (Tauri 2, Rust 백엔드). 각 CLI의 JSON/TOML/YAML 설정을 대신 편집해 준다.

**처음 가설("프록시로 CLI를 관측")은 절반만 맞다.**

- 주목적은 관측이 아니라 provider 전환이다.
- 프록시("Local Routing")는 선택 기능이고, 목적은 **다른 provider/API 형식으로 CLI를 쓰는 것**과 failover다. 사용량 기록은 부수 기능이다.
- 대화 기록(Session Manager)과 사용량 통계는 프록시가 아니라 **로컬 로그 파일 읽기**가 기본 경로다.

---

## 3. 핵심 아키텍처 지도

다이어그램은 미작성. 텍스트 구조도 (검증 수준은 각 질문 문서 참조):

```
[Claude Code]  ~/.claude/settings.json 의 env
   ANTHROPIC_BASE_URL=http://127.0.0.1:15721, ANTHROPIC_AUTH_TOKEN=PROXY_MANAGED
        │ POST /v1/messages
        ▼
[CC Switch 앱 프로세스 안의 Rust HTTP 서버 :15721]  (proxy/server.rs, axum+hyper)
   provider_router → 모델 매핑 → 형식 변환(providers/transform_*.rs) → 진짜 키로 교체 → usage 기록
        │
        ▼
[최종 LLM provider]  Anthropic / OpenAI / Gemini / 중계 서비스

(별도 경로, 프록시 불필요)
Session Manager ── ~/.claude/projects/**/*.jsonl 파싱 (session_manager/providers/claude.rs)
Usage(무프록시)  ── 각 도구의 로컬 세션 로그 스캔 (services/session_usage*.rs)
```

### 그림 읽는 가이드
1. 프록시 관련 코드는 `src-tauri/src/proxy/`, CLI별 설정 쓰기는 `src-tauri/src/live/project/*.rs`와 `mode/controller.rs`.
2. 제어 흐름은 "설정 파일의 base URL 변경 → CLI가 로컬 서버로 요청 → 서버가 변환 후 중계"다.
3. 미확인: 켜고 끌 때의 설정 복구, 비정상 종료 처리, `startup()` 동작.

---

## 4. 핵심 질문 및 세부 답변 목록

- [Q1: 프록시는 요청을 어떻게 "가로채는가"](./questions/q1-how-proxy-intercepts.md) - *가로채는 게 아니라 CLI의 base URL 설정을 로컬 주소로 바꿔 둔다.*
- [Q2: 설치하면 settings.json이 바뀌는가](./questions/q2-settings-json-when-changed.md) - *설치/실행만으로는 안 바뀐다. 이 PC에서 실제 확인.*
- [Q3: Session Manager와 프록시의 관계, 프록시가 하는 일](./questions/q3-session-manager-vs-proxy.md) - *Session Manager는 로컬 JSONL 읽기이고 프록시와 무관하다.*
- [Q4: 형식 변환과 유지보수 부담](./questions/q4-format-conversion-and-maintenance.md) - *Anthropic↔Gemini/OpenAI 변환을 프록시가 직접 하고, 이력상 유지보수 부담이 크다.*
- [Q5: Skills/MCP 관리와 같은 이름 스킬 처리](./questions/q5-skills-mcp-management.md) - *SSOT 한 곳에서 배포하며 앱별 변형은 보존되지 않고 재동기화 때 덮어쓴다 (실행 확인).*
- [Q6: MCP 앱별 변환과 plugin 처리](./questions/q6-mcp-per-app-conversion.md) - *MCP는 공통 형식 DB + 앱별 변환, 항목 단위로 추가/제거. plugin은 관리하지 않고 보존만 한다 (코드 읽기).*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **이전 wiki 요약**: 2026-10-16 삭제. 원문은 `git show b52364d:wiki/projects/cc-switch.md`
