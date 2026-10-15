# teamai-cli Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/Tencent/teamai-cli`
- **분석 Commit SHA**: `7ba8bcc374cfa11e85da54cb75c572f54c687fab` (2026-10-15, v0.22.0)
- **분석 일자**: `2026-10-15`
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습 (팀 단위 AI 자산 배포·동기화 구조 파악, `skills-manager`/`cc-switch`와 비교)
- **라이선스 / 스택**: MIT, TypeScript(ESM) CLI (`commander`, `simple-git`, `zod`, `tsup`, `vitest`). `src/` 약 29만 줄, 테스트 파일 584개 *(`wc -l`, `find`로 확인)*

> 검증 수준: **코드 확인** = `repos/teamai-cli` 소스를 직접 읽음 / **문서 근거** = README·`docs/` 주장(코드 미검증) / **미확인** = 아직 보지 않음. 실행은 하지 않았다.

---

## 2. 프로젝트 개요

팀이 쓰는 **AI 자산(skills, rules, agents, hooks, MCP, env, models, learnings 등)을 하나의 git 저장소에 두고**, 팀원 각자의 AI 코딩 도구(Claude Code, Codex, Cursor 등)에 자동 배포·동기화하는 CLI(`teamai`)다. 팀원은 한 번 `teamai init <repo>`만 하면, 이후 AI 세션이 시작될 때마다 `pull`이 돌아 최신 자산이 반영된다. *(문서 근거: `README.md`, `docs/product-overview.md`)*

해결하려는 문제: 팀원마다 skill·rule·MCP 설정이 달라 에이전트가 "팀의 방식"으로 일하지 않는 것, 팀이 겪은 시행착오(learnings)가 공유되지 않는 것.

핵심 흐름 (`docs/product-overview.md`; `push`/`pull` 명령은 `src/index.ts`에서 확인):

```
teamai push → branch + PR → 리뷰/머지
                               ↓
SessionStart hook → teamai pull → 각 AI 도구 디렉터리에 설치
```

---

## 3. 주요 기능

문서는 기능을 세 계층으로 나눈다. 아래 "코드 위치"는 `src/index.ts`의 명령 등록과 `src/` 파일명을 확인한 것이며, 각 기능의 내부 동작은 아직 읽지 않았다(미확인).

### 3.1 Team Execution — 모든 에이전트가 팀 방식으로 일하게 하기

| 기능 | 설명 | 명령 / 코드 위치 | 검증 |
|---|---|---|---|
| **리소스 동기화** | 팀 repo를 clone·pull 하여 각 도구 디렉터리에 설치. 워크스페이스(project) scope와 user(`~/`) scope 지원 | `init`, `push`, `pull`, `status`, `update`, `uninstall` / `src/init.ts`, `pull.ts`, `push.ts` | 명령 등록 확인, 내부 미확인 |
| **7종 리소스 타입** | `skills, rules, docs, env, agents, hooks, mcp`를 타입별 핸들러가 처리 | `src/types.ts`의 `ResourceType`, `src/resources/index.ts` | 코드 확인 |
| **Skills** | `skills/<name>/SKILL.md` 공유. 목록/조회/제외/경로 조회 | `teamai skill list/get/path/show`, `skill exclude` / `src/skill-cmd.ts`, `resources/skills.ts` | 명령 등록 확인 |
| **Rules / 공유 지침** | `rules/*.md`, `claudemd/*.md`를 도구별 형식으로 변환 (Cursor `.mdc`, Kiro steering, Copilot instructions, Trae·Qoder·JoyCode·CodeBuddy 규칙 등) | `src/resources/rule-format.ts`, `cursor-mdc.ts`, `kiro-steering.ts` 등 | 파일 존재 확인, 변환 규칙 미확인 |
| **Agents** | `agents/<name>.yaml`을 도구별 에이전트 정의로 배포 | `src/resources/agents.ts`, `agent-format.ts` | 파일 존재 확인 |
| **Hooks** | 팀 훅(`hooks/hooks.yaml`)과 내장 운영 훅을 각 도구 설정에 주입/제거. 내장 훅은 `teamai hook-dispatch <event>` 단일 진입점으로 통합. 호스트 훅 타임아웃(약 10초)을 피하려 foreground 7초 hard-exit + 백그라운드 자식 프로세스 구조 | `teamai hooks list/inject/remove`, `src/hooks.ts`, `builtin-hooks.ts`, `hook-dispatch*.ts` | `hook-dispatch` 명령·주석 코드 확인 |
| **MCP** | `mcp/mcp.yaml`의 MCP 서버를 각 도구 설정 형식으로 주입 | `teamai mcp list/inject/remove`, `src/resources/mcp.ts`, `mcp-reconcile.ts` | 명령 등록 확인 |
| **Env / Secrets** | 팀 환경변수 공유, `env exec`로 주입 실행. 팀이 선언한 secret 값은 팀 repo가 아닌 로컬 `~/.teamai/secrets/`에 보관 | `teamai env list/add/set/unset/exec`, `src/env-*.ts`, `secret-store.ts` | `secret-store.ts` 주석 확인 |
| **Models 프로필** | 모델 프로필(게이트웨이/API 키 플레이스홀더) 정의 후 `switch`/`restore`로 전환 | `teamai models list/add/configure/switch/restore/remove` / `src/models-cmd.ts` | 명령 등록 확인 |
| **배포 대상 제어** | `<namespace>/` 하위 자산은 해당 role·project만 수신. role, project, tag 구독 | `teamai roles`, `projects`, `tags`, `src/roles.ts`, `projects.ts`, `namespace-resolver.ts`, `manifest-schema.ts` | 명령·스키마 확인, 해석 로직 미확인 |
| **멀티 소스** | 팀 repo 외 추가 소스(repo/HTTP) 등록 | `teamai source add/remove/add-http/remove-http` | 명령 등록 확인 |
| **무결성/진단** | 배포 파일 해시 원장으로 사용자 수정본 보호, `doctor` 진단, git exclude 관리 | `resources/delivered-copies.ts`, `doctor*.ts`, `git-exclude*.ts` | 파일명·import만 확인 |
| **웹훅 / 스크립트 / 워크플로** | 웹훅 목록·테스트, 이벤트별 팀 스크립트 실행, 워크플로 start/next/report | `teamai webhook`, `script run`, `workflow` | 명령 등록만 확인 |

### 3.2 Team Context (beta) — 에이전트가 팀 지식을 이해하게 하기

| 기능 | 설명 | 명령 / 코드 위치 | 검증 |
|---|---|---|---|
| **Learnings & Recall** | 팀 교훈을 `learnings/`에 쌓고, recall을 켜면(기본 off) 작업 전에 에이전트가 검색. learnings/docs는 TF-IDF 계열 점수, 코드베이스 그래프는 별도 임계값(4.0) 사용 | `teamai recall enable/disable/status`, `recall <query>`, `src/recall.ts`, `utils/search-index.ts` | `recall.ts` 상단 확인 |
| **교훈 공유·승격** | 반복 교정/재시도가 있던 세션 종료 시 공유 제안, `promote`·`maintenance --prune` | `recall maintenance/promote`, `contribute` / `src/contribute.ts` | 명령 등록 확인 |
| **Codebase 지식 그래프** | 외부 repo를 import해 코드 지식 그래프를 `teamwiki/`에 저장. tree-sitter(wasm) 의존성, 신선도 검사 | `teamai import --from-repo`, `codebase`, `src/import-repo.ts`, `codebase-extract.ts`, `codebase-freshness.ts` | 의존성·파일명 확인, 파이프라인 미확인 |
| **다양한 import 소스** | repo/조직/로컬/MR/iWiki | `src/import-{repo,org,local,mr,iwiki}.ts` | 파일명 확인 |
| **Review** | 가져온 지식·MR 검토 흐름 | `teamai review`, `review ci`, `extract-mr` / `src/review-cmd.ts` | 명령 등록 확인 |

### 3.3 Team Improvement (beta) — 실행 결과가 팀을 개선하게 하기

| 기능 | 설명 | 명령 / 코드 위치 | 검증 |
|---|---|---|---|
| **사용량 추적/통계** | 도구·skill 호출을 훅으로 기록(`track`)하고 집계 | `teamai stats`, `src/usage-tracker.ts`, `stats.ts` | 숨김 명령 등록 확인 |
| **세션 저장/이전** | 마스킹한 세션 요약 저장, 도구 간 transcript 이전, 팀 세션 아카이브/검색/복원 | `teamai session save/migrate`, `src/save-session.ts`, `transcript-parser.ts`, `utils/redact.ts` | 문서 근거 + 파일명 |
| **Digest / Dashboard** | 주간 팀 digest, 로컬 대시보드 | `teamai digest`, `dashboard`, `src/digest.ts`, `dashboard*.ts` | 명령 등록 확인 |
| **Skill 건강도/추천** | skill 상태 점검과 추천 | `src/skill-health.ts`, `skill-recommend.ts` | 파일명만 확인 |

### 3.4 지원 에이전트 범위

README 표 기준 **20개 에이전트 행**(Claude Code, Codex, Cursor, CodeBuddy, WorkBuddy, GitHub Copilot CLI, OpenCode, Pi, Oh My Pi, OpenClaw, Hermes, DeepSeek Harness, Qoder, Qoder CN, Kiro, Trae, Trae CN, ZCode, JoyCode, Muse Code)을 지원하며, 에이전트마다 지원 기능이 다르다(예: models는 Cursor/Copilot/Kiro 등 미지원, usage/sessions는 OpenCode/Pi 등 미지원). *(문서 근거, 표의 개별 셀은 코드로 검증하지 않음)* 코드에는 에이전트별 hook 어댑터(`pi-hooks.ts`, `opencode-hooks.ts`, `hermes-hooks.ts`, `codex-team-hooks.ts` 등)가 따로 있다.

### 3.5 사용 방식 (UX)

- AI 도구에 한 줄을 보내 `skills/teamai` skill을 설치하면, 이후 `/teamai ...`로 설치·팀 가입·공유·대시보드를 자연어로 진행한다. *(`skills/teamai/` 존재만 확인, 동작 미확인)*
- 지원 git 호스트: GitHub, GitLab, GitCode, CNB, TGit, 사설 Git. 시작 템플릿은 `teamai-hub` org를 fork. *(문서 근거)*
- 배포 대상은 팀 repo의 `teamai.yaml`, `manifest/roles.yaml`, `manifest/projects.yaml`로 선언한다. *(`manifest-schema.ts` 주석 확인)*

---

## 4. 핵심 아키텍처 지도 (archify Diagrams)

아직 생성하지 않았다. 다음 세션에서 (1) 모듈 구조도, (2) `SessionStart → pull` 실행 흐름을 만든다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | 미생성 | 미생성 | `index.ts` → 명령 모듈 → `resources/*Handler` → 도구별 어댑터 |
| 대표 실행 흐름 | 미생성 | 미생성 | `SessionStart → hook-dispatch → pull → 리소스 설치` |

### 그림 읽는 가이드 (예정)
1. 진입점 `src/index.ts`(약 1,590줄, commander 명령 등록)에서 시작.
2. 자산 흐름: `pull.ts` → `resources/desired.ts`(원하는 상태 계산) → `resources/*` 핸들러.
3. 훅 경로: `hook-dispatch-cli.ts` → `hook-handlers.ts`. 미확인: 에이전트별 어댑터, recall/codebase 파이프라인.

---

## 5. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: 혼자 쓰면서 프로젝트별로 나누기, 프로젝트마다 조금 다를 때](./questions/q1-solo-per-project-management.md) - *가능. `projects.yaml` namespace로 나누고, 차이는 같은 이름으로 통째 교체하거나 추가 파일·env로 뺀다*

다른 후보는 [next.md](./next.md) 참고.

---

## 6. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: 아직 없음 (`wiki/projects/teamai-cli.md`는 코드 검증 후 작성)
- **비교 후보**: [skills-manager](../skills-manager/overview.md), [cc-switch](../cc-switch/overview.md) — 둘은 개인 로컬 도구이고 teamai는 git 기반 팀 배포라는 차이가 있어 보임 *(추론)*
