---
sha: "a44493f6ec20e32197a1bca4c3e000be2cd6fe70"
created: 2026-10-15
updated: 2026-10-24
---

# teamai-cli Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/Tencent/teamai-cli`
- **기준 SHA**: `a44493f` (2026-10-23, 앱 버전 `package.json` 0.22.0 그대로). 이전 기준 `7ba8bcc`(2026-10-15)에서 갱신했다.
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습 (팀 단위 AI 자산 배포·동기화 구조 파악, `skills-manager`/`cc-switch`와 비교)
- **라이선스**: MIT (`LICENSE`: "Tencent is pleased to support the open source community … teamai-cli is licensed under MIT", "Copyright (C) 2026 Tencent"). 하위 디렉터리에 다른 LICENSE 없음 (`find . -name 'LICENSE*'`로 확인). `package.json`도 `"license": "MIT"`.
- **분석 대상 제품**: npm 패키지 `teamai-cli`(바이너리 `teamai` = `dist/index.js`, `package.json` `bin`) 하나. TypeScript ESM, Node 20+, `commander`·`simple-git`·`zod`·`tsup`·`vitest`·`web-tree-sitter`. 같이 배포되는 에이전트용 콘텐츠: `skills/teamai/SKILL.md`(입구 스텁), `skill-data/{core,setup,share,wiki}/`(CLI가 서빙하는 내장 스킬), `agents/teamai-recall.md`. 중첩 패키지·별도 서버 없음. 개발용 `scripts/mock-teamai-server.mjs`가 있다.
- **스펙 범위**: 지도만 (사용자 요청: overview 재작성, archify 생략). 스펙 범위 승인 전.
- **규모**: 테스트 제외 `src/**/*.ts` 159,708줄(`find src -name '*.ts' -not -path '*__tests__*' | xargs cat | wc -l`), 테스트 `src/__tests__` 728개 `.ts`. 이전 문서의 "src/ 약 29만 줄, 테스트 584개"는 센 범위가 달라 직접 비교하지 않는다(이전 계산 방식 미기록).

> 이번 갱신은 기능 지도를 새로 쓴 것이다. 읽은 것은 `src/index.ts`의 명령 등록부(설명·옵션), `resources/index.ts`, `types.ts`의 `ResourceType`, `known-agents.ts`, 각 기능의 진입 파일 머리와 공개 함수 목록, `docs/product-overview.md`, `docs/designs/README.md`, README 에이전트 표 머리다. 내부 동작 본문은 거의 열지 않았다. 빌드·실행·테스트는 하지 않았다.

### 이전 기준(`7ba8bcc`) 대비 달라진 점

`git diff 7ba8bcc..a44493f`: 578개 파일, +65,684/−7,239. 소스에서 추가된 것은 `src/workflow/` 14개, `src/dashboard/` 5개, `src/session-flow/` 5개(`agent-session.ts`, `session-cmd-shared.ts`, `session-migrate-cmd.ts`, `adapters/opencode.ts`, `adapters/platform-facts.ts`), `src/tools.ts`, `tool-home.ts`, `tool-home-record.ts`, `launch-context.ts`, `locate.ts`, `scope-selection.ts`, `team-ref.ts`, `skill-use.ts`, `agent-observation.ts`, `codex-project-trust.ts`, `cursor-user-rules.ts`, `openclaw-home.ts`, `resources/places.ts`, `resources/repo-resource.ts`, `providers/mr-threads.ts`, `utils/git-answers.ts`, `utils/git-discovery.ts`와 `vitest.windows.config.ts`다.

| 항목 | 이전 문서 | 지금 (코드 확인) |
|---|---|---|
| 리소스 타입 | "7종: skills, rules, docs, env, agents, hooks, mcp" | **14종**. `ResourceType`에 `models`, `claudemd`, `learnings`, `wiki`, `workflows`, `prompts`, `scorers`가 늘었다(`types.ts:1218`, 이전 `types.ts:1141`은 7종). 새 7종은 `RepoResourceHandler` 한 클래스로 처리한다(`resources/index.ts`, `resources/repo-resource.ts`). |
| 워크플로 명령 | `start`, `next`, `report` | `start`, `next`, `report`에 `respond`, `retry`, `resume`, `cancel`이 늘었다(`index.ts:797`~`:860`). 엔진 파일은 `src/workflow/`에 25개로 늘었고 `engine.ts`는 1,293줄이다. |
| 세션 명령 | `session save/migrate` | `session` 아래 `save`(index.ts)와 `platforms`, `push`, `pull`, `list`, `resume`, `search`, `rollback`, `migrate`(`session-flow/session-cmd.ts`, `session-migrate-cmd.ts`). 이 하위 명령들은 `argv`에 `session`이 있을 때만 등록된다(`session-flow/register-gate.ts`). |
| 에이전트 | README 표 "20개 행" | 코드 `KNOWN_AGENTS` **38개 항목**(`known-agents.ts:84`~; `claude-internal`, `tclaude`, `codex-internal`, `tcodex`, `openclaw` 계열 4종, `dsh`, `agents` 포함). 이전 문서의 20은 README 표 행 수이지 코드 목록이 아니다. |
| 도구 경로 | — | `types.ts`에 `DEFAULT_TOOL_PATHS`(에이전트별 skills·rules·settings·claudemd·agents·mcp 경로)와 코드 주석(MCP는 확인된 도구만 경로를 둔다)이 생겼다. |
| 대시보드 | `dashboard*.ts` 파일명만 | `dashboard/` 하위 모듈 11개(`client`, `delivery`, `distribution`, `http`, `locales`, `resources`, `resources-skills`, `shell`, `styles`, `workflow-runs`, `workspaces`) 중 `delivery`, `distribution`, `http`, `resources-skills`, `workflow-runs` 5개가 새로 생겼다. |
| TypeScript | `^5.7.0` | `^7.0.2`(`package.json` devDependencies) |

**기존 질문 문서 재확인 필요**: [Q1](./questions/q1-solo-per-project-management.md)이 인용한 `init.ts`, `projects.ts`, `resource-namespaces.ts`가 이번 구간에서 바뀌었다. 이 문서는 `7ba8bcc` 기준 사실로 읽고, 다시 볼 때 새 SHA에서 확인한다 (워크플로 5장).

---

## 2. 프로젝트 개요

팀이 쓰는 **AI 자산(skills, rules, agents, hooks, MCP, env, models, learnings 등)을 하나의 git 저장소(팀 repo)에 두고**, 팀원 각자의 AI 코딩 도구에 자동 배포·동기화하는 CLI(`teamai`)다. 팀원은 한 번 `teamai init <repo>`를 하고, 이후 AI 세션이 시작될 때마다 훅이 `pull`을 돌려 최신 자산을 받는다 (문서 근거: `README.md`, `docs/product-overview.md`. `push`·`pull` 명령 등록은 코드 확인: `index.ts:194`, `:215`).

```
teamai push → branch + PR → 리뷰/머지
                               ↓
SessionStart hook → teamai pull → 각 AI 도구 디렉터리에 설치
```
(문서 근거: `docs/product-overview.md` "How it flows")

문서는 기능을 세 계층으로 나눈다: **Team Execution**(skills·rules·env·agents·hooks·MCP·models), **Team Context** (beta, learnings·codebase graph·teamwiki), **Team Improvement** (beta, usage·sessions). 아래 지도의 행 묶음 이름이 이 계층이다.

- **팀 repo 레이아웃**: `skills/<name>/SKILL.md`, `rules/*.md`, `claudemd/*.md`, `agents/<name>.yaml`, `culture.md`, `env/env.yaml`, `hooks/hooks.yaml`, `mcp/mcp.yaml`, `models/models.yaml`, `packages`(`teamai.yaml`), `docs/`, `learnings/`, `teamwiki/` (문서 근거: `docs/product-overview.md`). `<namespace>/` 하위 자산은 선언한 role·project에게만 간다(같은 문서).
- **진입 구조**: `bin.ts`가 Node 컴파일 캐시를 켠 뒤 `./cli.js`를 동적 import한다(코드 확인: `src/bin.ts`). 명령은 `src/index.ts`(1,680줄)의 `commander` 정의에 모여 있고, 대부분 `await import('./<module>.js')`로 늦게 불러온다(코드 확인: 예 `codebase`, `import --cache-status`). 숨은 명령(`hidden: true`)은 훅이 부르는 `hook-dispatch`, `track`, `track-slash`, `dashboard-report`, `contribute-check`, `todowrite-hint`, `mr-hint`, `deep-enrich`, `reconcile-plugins` 9개다(코드 확인: `index.ts`의 `.command(…, { hidden: true })`).
- **지원 에이전트**: 코드의 `KNOWN_AGENTS` 38개 항목(코드 확인). README 표는 20개 행으로 기능별 지원 여부(✓/—)를 적는데, 표의 개별 셀은 코드로 검증하지 않았다(문서 근거). 에이전트별 훅 어댑터 파일(`codex-team-hooks.ts`, `pi-hooks.ts`, `omp-hooks.ts`, `opencode-hooks.ts`, `openclaw-hooks.ts`, `hermes-hooks.ts`, `dsh-hooks.ts`, `claude-hook-host.ts`, `copilot-hook-claim.ts`)가 따로 있다(파일 존재 확인).
- **Git 호스트**: 코드의 provider 6종 `tgit`, `github`, `cnb`, `gitlab`, `gitcode`, 일반 `git`(코드 확인: `providers/registry.ts`의 import). 알 수 없는 호스트는 transport만 하는 일반 provider로 간다(`registry.ts` 머리 주석).

### 기능 지도

<!-- 한 행 = 스펙 하나의 작업 단위. 분할과 경로는 제안이다. 선행은 재구현에 필요한 계약. -->

#### Team Execution

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 팀 repo 연결·초기화 | `teamai init <repo>`: Git provider 판별, 팀 repo clone, 멤버 등록, project/user scope 결정, 로컬 설정 기록. 팀 repo 쪽 관리자 작업(roles/projects 초기화)은 포함하지 않음 | `src/init.ts`(2,308줄) `resolveInitScope`, `resolveActiveProjects`; `src/config.ts`; `src/clone.ts`; `src/members.ts`; `src/providers/registry.ts` | Git provider 계약, 팀 repo 레이아웃·manifest | 핵심 | `capabilities/team-init.md` · 미작성 | 코드 확인(명령 등록, 진입 함수 존재) / 미확인(본문) |
| 배포 `pull` | 팀 repo 최신화 → 원하는 상태 계산 → 각 도구 디렉터리에 설치·갱신·정리. 사용자가 고친 복사본 보호, git exclude 관리, 훅 타임아웃 안에서 동작 | `src/pull.ts`(4,022줄); `src/resources/desired.ts`(`resolveDesiredSkills/Rules/Agents`); `src/resources/delivered-copies.ts`; `src/git-exclude*.ts`; `src/instruction-targets.ts`; `src/team-ref.ts`; `src/post-pull.ts` | 리소스 핸들러, 배포 대상 제어, 도구 경로 | 핵심 | `capabilities/pull-delivery.md` · 미작성 | 코드 확인(`pull.ts`·`desired.ts` 머리, `desired.ts` 설계 주석) / 미확인(본문, 복사본 보호 규칙) |
| 공유 `push` | 로컬 리소스를 팀 repo 브랜치로 올리고 PR 생성 흐름. 공유 대상 namespace 결정, 미반영 항목 보관 | `src/push.ts`(2,320줄) `push`; `src/push-namespaces.ts`; `src/utils/pending-push.ts`; `src/utils/pre-push-sync.ts`; provider의 MR 생성 | Git provider 계약, 배포 대상 제어 | 핵심 | `capabilities/push-sharing.md` · 미작성 | 코드 확인(명령 등록, 진입 함수) / 미확인(본문) |
| 조회·제거·언인스톨 | `status`(로컬 vs 팀 repo diff), `list [type]`, `remove <type> <names…>`(팀 repo와 모든 도구에서 삭제), `uninstall`(이 머신의 teamai 자산·훅 전부 제거) | `src/status.ts` `status`, `list`; `src/remove.ts` `remove`; `src/uninstall.ts`(2,846줄) `uninstall` | 리소스 핸들러, 배포 `pull` | 핵심 | `capabilities/status-remove-uninstall.md` · 미작성 | 코드 확인(명령 등록, 진입 함수) / 미확인(본문) |
| 규칙·에이전트 형식 변환 (패밀리) | 하나의 `rules/*.md`·`agents/*.yaml`·`claudemd`를 도구별 형식으로 변환·배치(Cursor `.mdc`, Kiro steering, Copilot instructions, Qoder·Trae·JoyCode·CodeBuddy·OMP 규칙 등) | `src/resources/rule-format.ts`, `agent-format.ts`, `cursor-mdc.ts`, `kiro-steering.ts`, `copilot-instructions.ts`, `qoder-rule.ts`, `trae-rule.ts`, `joycode-rule.ts`, `codebuddy-rule.ts`, `omp-rule.ts`, `team-rule.ts`; `src/instruction-targets.ts` | 도구 경로 레지스트리, 리소스 핸들러 | 핵심 | `capabilities/rule-agent-formats.md` · 미작성 | 구조(파일 목록) / 미확인(공통 규칙, 도구별 차이) |
| 배포 대상 제어 | role·project·tag·namespace로 누가 무엇을 받을지 결정. `roles`(init/list/set/add/remove/update), `projects`(list/set/add/update/remove/members), `tags`(list/subscribe/unsubscribe/add/remove), 워크스페이스가 안에 든 repo의 선택까지 전달 | `src/roles-cmd.ts`, `projects-cmd.ts`, `tags.ts`; `src/roles.ts`, `projects.ts`, `namespace-resolver.ts`, `resource-namespaces.ts`, `manifest-schema.ts`, `manifest-edit.ts`, `workspace-children.ts`, `scope-selection.ts` | 팀 repo 레이아웃·manifest | 핵심 | `capabilities/distribution-targeting.md` · 미작성 | 코드 확인(명령 등록, `desired.ts` 머리 주석이 "namespace rule applied (#707)"라고 설명) / 이전 SHA에서 [Q1](./questions/q1-solo-per-project-management.md)이 일부 읽음(재확인 필요) |
| 훅 주입·디스패치 | 도구 설정 파일에 teamai 훅(내장 + 팀 `hooks/hooks.yaml`)을 주입·제거·목록. 훅은 `teamai hook-dispatch <event>` 한 진입점이 한 번에 여러 핸들러로 분기 | `src/hooks.ts`(4,065줄) `TEAMAI_HOOK_SUBCOMMANDS`; `src/hooks-cmd.ts`; `src/builtin-hooks.ts`; `src/hook-dispatch.ts` `HookHandler`; `src/hook-dispatch-cli.ts`; `src/hook-handlers.ts`; 에이전트별 `*-hooks.ts` | 도구 경로 레지스트리 | 핵심 | `capabilities/hooks.md` · 미작성 | 코드 확인(`hook-dispatch.ts` 머리 설계 주석, `hooks.ts` 상수) / 미확인(본문, 도구별 차이, 타임아웃 처리) |
| MCP 동기화 | 팀 `mcp/mcp.yaml`의 서버를 각 도구의 MCP 설정 형식으로 주입·제거·목록. 확인된 경로가 있는 도구만 건드림 | `src/mcp-cmd.ts` `mcpList`, `mcpInject`, `mcpRemove`; `src/resources/mcp.ts`, `mcp-format.ts`; `src/mcp-reconcile.ts`; `src/mcp-resolved-files.ts` | 도구 경로 레지스트리 | 핵심 | `capabilities/mcp-sync.md` · 미작성 | 코드 확인(명령 등록, `DEFAULT_TOOL_PATHS` 주석) / 미확인(본문) |
| 환경변수·시크릿 | 팀 env 공유, 값은 디렉터리(scope)별로 해석, 시크릿은 선언만 팀 repo에 두고 값은 로컬에. `env exec -- <cmd>`로 주입 실행 | `src/env-commands.ts` `envList`, `envSet`, `envUnset`; `src/env-exec.ts`, `env-resolution.ts`, `env-reserved.ts`; `src/secret-store.ts`; `src/resources/env.ts`, `secrets.ts`; 설계 `docs/designs/team-secrets.md`, `env-by-directory.md` | 배포 대상 제어 | 핵심 | `capabilities/env-secrets.md` · 미작성 | 코드 확인(명령 등록) / 문서 근거(설계 문서 "Implemented") / 미확인(본문) |
| 모델 프로필 | 팀·개인 게이트웨이 모델 프로필 목록·추가·API 키 설정, 호환되는 에이전트 설정을 프로필로 전환(`switch`)하고 첫 전환 전 상태로 복구(`restore`) | `src/models-cmd.ts` `modelsList`, `modelsAdd`, `modelsConfigure`; `src/models/profile.ts`, `switch.ts`(1,403줄), `aliases.ts`; `src/model-pricing.ts` | 도구 경로 레지스트리 | 핵심 | `capabilities/model-profiles.md` · 미작성 | 코드 확인(명령 등록, `switch.ts`가 도구별 환경변수·설정 파일을 직접 다루는 import와 키 목록) / 미확인(전환·복구 본문) |
| 멀티 소스·패키지 | 팀 repo 외 소스(repo, HTTP) 추가·제거·목록·탐색, 소스의 스킬 정리. `teamai.yaml`이 선언한 npm 패키지·Claude 플러그인 설치(`packages`) | `src/source.ts`(1,627줄) `sourceAdd`; `src/pkg/commands.ts`, `register-command.ts`, `adapters/npm.ts`, `adapters/claude-plugin.ts`, `manifest.ts`; `src/plugin-lifecycle.ts`; `src/resources/marketplace.ts` | 팀 repo 레이아웃·manifest | 핵심 | `capabilities/sources-packages.md` · 미작성 | 코드 확인(명령 등록, `packages` 기본 동작이 `install`임) / 미확인(본문) |
| 스킬 조회·제외·내장 스킬 서빙 | `skill list/get/path/show`(저장소·설치분·CLI가 서빙하는 내장 카탈로그), 개인 제외 목록(`skill exclude`). 내장 스킬 본문은 설치된 CLI가 직접 출력 | `src/skill-cmd.ts` `skillList`, `skillShow`; `src/skill-command.ts`; `src/skill-content.ts`; `src/builtin-skills.ts`; `src/exclude.ts`; 설계 `docs/designs/skill-serving.md` | 리소스 핸들러 | 핵심 | `capabilities/skill-serving.md` · 미작성 | 코드 확인(명령 등록·설명) / 문서 근거(설계 문서) / 미확인(본문) |
| 워크플로 엔진 | 팀 repo의 `workflows/<name>.yaml`(command·prompt 단계, `needs`, 병렬, 루프, `for_each`, `approve`·`choose` 사람 확인, 작업 공간·브랜치)을 검증해 실행. 드라이버가 `next`로 단계를 임대받고 `report`로 결과를 돌려주는 계약, 로컬 드라이버 실행 | `src/workflow-commands.ts`(`writeEnvelope`); `src/workflow/engine.ts`(1,293줄) `startRun`, `leaseNext`, `reportAttempt`; `local-driver.ts` `runLocalDriver`; `run-controls.ts`; `parse*.ts`; `expression.ts`; `step-state.ts`; `store.ts`; `workspace.ts`, `worktree.ts`; 문서 `docs/dev/workflow-engine.md`, `docs/guide/workflow*.md` | 팀 repo 레이아웃, 리소스 핸들러(`workflows`) | 핵심 | `capabilities/workflow-engine.md` · 미작성 | 코드 확인(명령 등록 7개, `engine.ts` import, 출력은 JSON envelope) / 문서 근거(`workflow-engine.md`의 "run은 `settleRun`에서만 끝난다" 등 규칙) / 미확인(본문) |
| 진단·셀프 업데이트 | `doctor`(설정 진단, 도구별 배포 검증), `update`(npm으로 CLI 업그레이드, 레지스트리 판별) | `src/doctor.ts` `buildChecks`, `runChecks`; `src/doctor-delivery.ts`, `doctor-agent-models.ts`, `doctor-git-exclude.ts`; `src/update.ts`, `update-policy.ts` | 배포 `pull`(검증 대상) | 핵심 | `capabilities/doctor-update.md` · 미작성 | 코드 확인(명령 등록, 진입 함수 존재) / 미확인(본문) |
| 팀 스크립트·웹훅 | 팀이 `teamai.yaml`에 선언한 Node 스크립트를 `preInit`·`postInit`·`prePull`·`postPull`·`postDeploy`에 실행. 웹훅 엔드포인트 목록과 테스트 이벤트 발송 | `src/script-commands.ts` `scriptRun`; `src/team-scripts.ts`; `src/webhook.ts` `sendWebhook`, `listWebhooks`; `src/webhook-formatters.ts` | 팀 repo 레이아웃·manifest | 부속 | `capabilities/scripts-webhooks.md` · 미작성 | 코드 확인(명령 등록·설명) / 미확인(본문) |

#### Team Context (beta)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| recall 검색 | `teamai recall <query>`로 learnings·docs·(옵션) 코드 지식 검색. `--depth route|context|lookup`, `--check`(관련성 사전 확인), 켜고 끄기(기본 off). 점수 임계값은 learnings/docs와 코드 지식이 다름(코드 지식 4.0) | `src/recall.ts`(825줄); `src/utils/search-index.ts`, `tokenizer.ts`; `src/recall-toggle.ts`, `recall-quality.ts`, `recall-log.ts`, `recall-adoption.ts`; `src/votes.ts`; `src/code-knowledge-recall.ts` | 지식 저장 포맷(teamwiki), 팀 repo 레이아웃 | 핵심 | `capabilities/recall.md` · 미작성 | 코드 확인(`recall.ts` 상단 상수, 명령 옵션) / 미확인(점수 계산 본문) |
| 학습 공유(contribute) | 반복 교정·재시도가 있던 세션 끝에 교훈 공유 제안, `contribute`로 팀 repo에 기여(기본 목적지 projects 안내), 대기 큐 | `src/contribute.ts`; `src/contribute-check.ts`; `src/utils/pending-learnings.ts`, `learnings-publish.ts`, `learnings-mirror.ts`, `learnings-branch.ts`, `learnings-roots.ts` | 팀 repo 레이아웃, Git provider 계약, 배포 대상 제어 | 핵심 | `capabilities/contribute.md` · 미작성 | 코드 확인(명령 등록·설명) / 미확인(본문, 공유 제안 조건) |
| 지식 유지보수 | `recall maintenance`(`--prune`, `--archive`, `--confidence-writeback`, `--update-quality`, `--dry-run`), `recall promote`(고신뢰 학습을 docs/skills/rules로 승격), `recall feedback`(`--positive/--negative`) | `src/maintenance/{confidence,prune,promote,hot-cold,quality-update,paths}.ts`; `src/votes.ts` `recallFeedback` | recall 검색 | 핵심 | `capabilities/knowledge-maintenance.md` · 미작성 | 코드 확인(`index.ts`에서 `recallCmd`의 하위 명령 3개 확인) / 미확인(본문) |
| 지식 import (로컬·MR·iWiki·조직) | `teamai import`: 로컬 디렉터리 스캔·AI 분류·대화형 검토(`--dir`, `--from-claude`), 병합된 MR/PR에서 학습 추출(`--from-mr`), iWiki(`--from-iwiki`), 조직의 repo 화이트리스트 생성(`--from-org`), 캐시 상태·정리 | `src/import.ts`(467줄) `importFromX` 분기; `src/import-local.ts`, `import-mr.ts`, `import-iwiki.ts`, `import-org.ts`, `iwiki-dual.ts`; `src/cache-cmd.ts`; `src/providers/*/mr-fetch.ts`, `mr-threads.ts`; `src/utils/iwiki-client.ts` | Git provider 계약, 지식 저장 포맷 | 핵심 | `capabilities/knowledge-import.md` · 미작성 | 코드 확인(`import.ts` import 목록, 옵션 목록) / 미확인(본문, 외부 서비스 iWiki 동작) |
| 코드베이스 지식 그래프 (teamwiki) | `import --from-repo`/`--from-repo-list`/`--dir`로 repo를 clone·추출해 `teamwiki/`에 그래프와 문서 저장(증분, AI 보강 생략 옵션). `codebase`로 lint·reconcile·상태·deep-enrich. 언어별 추출기 패밀리(config, go, java, python, rust, scala, swift, typescript) | `src/import-repo.ts` `importFromRepo`; `src/import-repo-list.ts`; `src/codebase-extract.ts`(1,185줄) `extractCodebase`; `src/wiki-engine/code-knowledge/code-graph.ts` `buildCodeGraph`, `ast/`, `extractors/`; `src/wiki-engine/knowledge-reconciler.ts`; `src/codebase-cmd.ts` `codebaseCmd`; `src/codebase-freshness.ts`; `src/enrich-with-ai.ts`, `deep-enrich.ts` | 지식 저장 포맷, 지식 import | 핵심 | `capabilities/codebase-graph.md` · 미작성 | 코드 확인(진입 함수 존재, `extractors/` 파일 8개, `tree-sitter-wasms`·`web-tree-sitter` 의존) / 미확인(추출 파이프라인, 언어별 추출기 공통 계약) |
| 리뷰·CI 통합 | 대기 중인 지식 변경(`.teamai/pending-review.jsonl`) 검토·적용·`--dry-run`, 팀 repo 브랜치 상태 점검, CI에서 MR/PR 지식 추출 후 댓글 또는 repo 기록(`ci extract-mr`) | `src/review-cmd.ts` `reviewCmd`; `src/review-store.ts`, `review-branch.ts`; `src/ci/extract-mr.ts` `ciExtractMr`, `mr-comment.ts`, `read-rejections.ts`; `examples/ci/*` | 코드베이스 지식 그래프, Git provider 계약 | 부속 | `capabilities/review-ci.md` · 미작성 | 코드 확인(명령 등록, 진입 함수) / 미확인(본문) |

#### Team Improvement (beta)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 사용량 추적·통계 | 훅이 도구·슬래시 명령·스킬 사용을 기록(`track`, `track-slash`), `stats`로 로컬 집계, 스킬 건강도·추천 | `src/usage-tracker.ts`; `src/stats.ts` `aggregateUsage`, `showStats`; `src/skill-use.ts`; `src/skill-health.ts` `calculateSkillHealth`; `src/skill-recommend.ts` | 훅 주입·디스패치, 로컬 데이터 홈 | 핵심 | `capabilities/usage-stats.md` · 미작성 | 코드 확인(명령 등록·숨김, 진입 함수) / 미확인(본문) |
| 세션 요약 저장 | `session save`: 개인정보를 가린(redact) 세션 요약을 로컬 월별 로그에 기록, 세션 수집·분석·소유자 기록 | `src/save-session.ts` `saveSession`; `src/session-collector.ts`; `src/session-analytics.ts`; `src/transcript-parser.ts`; `src/utils/redact.ts`; `src/session-owners.ts` | 로컬 데이터 홈 | 핵심 | `capabilities/session-save.md` · 미작성 | 코드 확인(명령 등록, 진입 함수) / 미확인(본문) |
| 세션 이전·팀 세션 동기화 (SessionFlow) | 에이전트 간 세션 이전(`session migrate`), 팀 세션 저장소로 push/pull/list/resume/search/rollback. 플랫폼 어댑터 패밀리(Claude Code, Codex, CodeBuddy, CodeBuddy IDE, WorkBuddy, Cursor, OpenCode) | `src/session-flow/session-cmd.ts` `registerSessionFlowCommands`; `session-migrate-cmd.ts`; `sync.ts`(1,342줄); `migrate.ts`; `ir.ts`; `adapters/index.ts` `ADAPTER_REGISTRY`; `search.ts`; `scrub.ts`; 문서 `docs/dev/agent-sessions.md` | Git provider 계약, 팀 repo 레이아웃 | 핵심 | `capabilities/session-flow.md` · 미작성 | 코드 확인(하위 명령 8개, `ADAPTER_REGISTRY` import 7개) / 미확인(본문, 중간 표현 `ir.ts` 형식) |
| 대시보드 | `teamai dashboard`: 로컬 웹 UI 서버. 훅이 보고한 세션 상태(`dashboard-report`)와 이벤트 로그를 읽어 세션을 보여 줌. 비용·배포 현황·워크플로 실행 표시는 `dashboard/` 파일 이름(`delivery`, `workflow-runs`)과 `session-trends` import로 본 추론 | `src/dashboard.ts`(666줄); `src/dashboard-collector.ts`(2,533줄); `src/dashboard/{http,workspaces,delivery,distribution,resources,resources-skills,workflow-runs,client,shell,styles,locales}.ts`; `src/dashboard-html.ts`; `src/viz.ts` | 로컬 데이터 홈, 훅 주입·디스패치 | 핵심 | `capabilities/dashboard.md` · 미작성 | 코드 확인(`dashboard.ts` 머리의 `events.jsonl` → `rebuildSessions` 구조 주석) / 미확인(본문) |
| 팀 보고·digest | 사용량·세션 지표·투표를 팀 repo의 보고 브랜치로 올리고(`team-push`), `digest`로 주간 팀 활동 요약 | `src/team-push.ts`(1,215줄); `src/digest.ts` `summarizeInterventions`; `src/utils/reports-branch.ts`; `src/session-trends.ts`; 문서 `docs/guide/reporting.md` | 사용량 추적·통계, Git provider 계약 | 핵심 | `capabilities/team-reporting.md` · 미작성 | 코드 확인(파일 import 목록, 명령 등록) / 미확인(본문, 보고 형식) |

#### 부속 (본체와 별개의 연동·콘텐츠·빌드)

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| ClawPro HTTP 로컬 에이전트 연동 | `bind-project`로 워크스페이스를 ClawPro 프로젝트에 묶고 HTTP 소스(`source add-http`)로 보고·동기화·확인 | `src/index.ts` `bind-project`(`:1213`); `src/local-agent.ts`(5,070줄) `DEFAULT_ROUTES`, `loadLocalAgentConfig` | 멀티 소스 | 부속 | `capabilities/clawpro-local-agent.md` · 미작성 | 코드 확인(명령 등록, 파일 규모·상수) / 미확인(외부 서비스, 본문) |
| 내장 스킬·에이전트 콘텐츠 | CLI가 서빙하는 `core`·`setup`·`share`·`wiki` 스킬 문서와 스크립트(`scan_repo.py`, `validate_kb.py`), 에이전트에 실제로 배포되는 입구 스킬 `skills/teamai/SKILL.md`, recall 서브에이전트 `agents/teamai-recall.md`. `skill-data/core/references/commands.md`는 명령 표에서 생성 | `skills/teamai/SKILL.md`; `skill-data/*/SKILL.md`; `agents/teamai-recall.md`; `src/builtin-skills.ts`, `builtin-agents.ts`, `builtin-rules.ts`, `commands-reference.ts` | 스킬 조회·제외·내장 스킬 서빙 | 부속 | `capabilities/bundled-skills.md` · 미작성 | 코드 확인(파일 존재, `AGENTS.md`의 생성 규칙 설명) / 미확인(본문) |
| 빌드·배포·테스트 하네스 | tsup 번들(ASCII 출력 강제, 컴파일 캐시용 `bin.ts`/`cli.js` 분리), 공개 npm 이름 `teamai-cli`와 사내 이름 `@tencent/teamai-cli`를 CI가 바꿔 배포, e2e 테스트 구성 | `tsup.config.ts`; `src/bin.ts`; `.coding-ci.yaml`; `vitest*.config.ts`; `scripts/mock-teamai-server.mjs`; `src/providers/registry.ts` 머리 주석 | 없음 | 부속 | `capabilities/build-release.md` · 미작성 | 코드 확인(`tsup.config.ts` 머리, `bin.ts`, `registry.ts` 주석) / 미확인(CI 설정은 기본 제외 영역) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 팀 repo 레이아웃·manifest (`teamai.yaml`, `manifest/roles.yaml`, `manifest/projects.yaml`, 리소스 디렉터리) | 초기화, pull, push, 배포 대상 제어, 스크립트, 패키지, 워크플로 | `src/types.ts` `TeamaiConfig`, `ResourceType`; `src/manifest-schema.ts`; `src/config.ts` | `capabilities/team-repo-layout.md` · 미작성 | 코드 확인(`ResourceType` 14종, `RESOURCE_TYPES`), 필드 정의는 미확인 |
| 리소스 핸들러 (`ResourceHandler`, 14종 타입, 델타 계산) | pull, push, status·list·remove, 스킬 조회, 워크플로 | `src/resources/base.ts`; `src/resources/index.ts` `getHandler`; `src/resources/repo-resource.ts` `RepoResourceHandler`; 전용 핸들러 7개 | `capabilities/resource-handlers.md` · 미작성 | 코드 확인(핸들러 표), 본문 미확인 |
| 도구(에이전트) 경로 레지스트리 | pull, 훅, MCP, 규칙 변환, 모델 프로필, 세션 어댑터, doctor | `src/known-agents.ts` `KNOWN_AGENTS`(38); `src/types.ts` `DEFAULT_TOOL_PATHS`; `src/tool-home.ts`, `tools.ts`, `tool-home-record.ts` | `capabilities/agent-paths.md` · 미작성 | 코드 확인(개수·필드), 경로 표는 패밀리로 묶을 수 있음(추론) |
| Git provider 인터페이스 (6종) | 초기화, push, import, CI, 세션 동기화, 보고 | `src/providers/types.ts` `GitProvider`; `src/providers/registry.ts`; `providers/{tgit,github,cnb,gitlab,gitcode,git}/` | `capabilities/git-providers.md` · 미작성 | 코드 확인(등록부), 호출 계약은 미확인 |
| 지식 저장 포맷 (`learnings/`, `docs/`, `teamwiki/`의 그래프 인덱스·프로토콜) | recall, import, 코드베이스 그래프, 유지보수, 리뷰 | `src/wiki-engine/core/graph-index.schema.ts`; `src/wiki-engine/core/wiki-protocol.ts`; `src/utils/search-index.ts` | `capabilities/knowledge-format.md` · 미작성 | 구조(파일·스키마 이름) / 미확인(필드) |
| 로컬 데이터 홈·이벤트 로그 (`events.jsonl`, 사용 이벤트, 보고 스냅샷) | 사용량, 세션 요약, 대시보드, 팀 보고 | `src/types.ts` `getDataHome`, `getReportsDir`; `src/dashboard-collector.ts`; `src/usage-tracker.ts`; 설계 `docs/designs/data-directory-layout.md` | `capabilities/local-data-home.md` · 미작성 | 구조 / 문서 근거(설계 문서 "Implemented") |

**대조한 범위와 미탐색 영역**
- 대조: `src/index.ts`의 `.command(` 전체(`program`에 직접 붙은 최상위 41개 + 하위 명령, 숨김 9개 확인), `registerPackagesCommand`와 `registerSessionFlowCommands`가 등록하는 명령, README의 세 계층과 에이전트 표 머리, `docs/product-overview.md`의 자산 위치 표, `docs/designs/README.md`의 상태 표, `src/` 디렉터리 목록 전체.
- 문서와 구현의 차이: `docs/designs/README.md`는 "Management backend"(`management-backend.md`)를 Proposal로 표시하며 "nothing in the CLI implements it yet"이라 한다. `src/`에는 대응하는 명령이 없다(이름으로 확인: `index.ts`의 명령 목록에 없음). 이전 overview의 "7종 리소스 타입", "에이전트 20개"는 이번 SHA 기준으로는 14종·38개(위 변경 표).
- 미탐색: 모든 기능의 본문(호출 경로 안쪽), `hooks.ts` 4천 줄, `pull.ts` 4천 줄, `local-agent.ts` 5천 줄, 각 도구별 훅·세션 어댑터, 워크플로 표현식 언어, 외부 서비스(iWiki, ClawPro, Git 호스트 API) 동작. 기본 제외 영역(CONTRIBUTING·CI 설정·테스트·번역본·변경 이력)은 열지 않았다. README 번역본 4개와 `docs/guide/zh-CN/`도 열지 않았다.

---

## 3. 구조도

이번 갱신에서는 archify 구조도를 만들지 않았다(사용자 지시). 아직 `diagrams/`가 없다. 글로 쓴 구조는 2절 "진입 구조", 아래 "읽는 순서"를 본다.

### 글로 쓴 구조 해설

**읽는 순서**
1. `src/bin.ts` → `src/index.ts` — 명령 표(약 1,680줄). 각 명령이 어느 모듈로 가는지 본다. (코드 확인)
2. 자산 흐름: `pull.ts` → `resources/desired.ts`(원하는 상태 계산) → `resources/*` 핸들러 → 도구 디렉터리. (코드 확인: import 관계)
3. 훅 흐름: 도구 설정에 주입된 훅 → `teamai hook-dispatch <event>` → `hook-dispatch.ts`의 핸들러 분기(`Promise.allSettled`로 한 핸들러가 죽어도 다른 핸들러는 진행). (코드 확인: `hook-dispatch.ts` 머리 주석)
4. 지식 흐름: `import-*.ts` → `wiki-engine/`·`codebase-extract.ts` → `teamwiki/`·`learnings/` → `recall.ts`. (구조: import 관계와 파일명)
5. 개선 흐름: 훅(`track`, `dashboard-report`, `contribute-check`) → 로컬 이벤트 로그 → `dashboard.ts`·`stats.ts`·`team-push.ts`·`digest.ts`. (구조)

**모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 | 검증 수준 |
|---|---|---|---|---|
| `index.ts` | 명령 정의와 지연 import 분기 | argv → 모듈 함수 | `index.ts` | 코드 확인 |
| `resources/*` | 리소스 타입별 목록·델타·설치 | 팀 repo 파일 ↔ 도구 디렉터리 | `resources/index.ts` 핸들러 표 | 코드 확인(표) |
| `resources/desired.ts` | 멤버가 받아야 할 스킬·에이전트·규칙·claudemd 집합 계산(namespace 규칙 적용). `pull`, `doctor`, `recall`, `contribute`가 같이 씀 | 팀 설정·상태 → 항목 집합 | 머리 주석 | 코드 확인(주석) |
| `hook-dispatch.ts` | 훅 이벤트를 한 프로세스로 받아 핸들러에 분기 | stdin JSON → 출력 병합 | 머리 주석 | 코드 확인(주석) |
| `providers/*` | Git 호스트별 URL 해석, clone, MR/PR | repo URL → provider | `registry.ts` | 코드 확인(주석) |
| `workflow/*` | 워크플로 파싱·실행 상태·임대(lease) | YAML → run 상태 → JSON envelope | `engine.ts` import 목록 | 구조 |
| `session-flow/*` | 에이전트 세션 중간 표현으로 변환·이전·팀 동기화 | 플랫폼별 세션 ↔ `ir.ts` | `adapters/index.ts` | 구조 |
| `wiki-engine/*` | 코드 사실 추출·그래프 병합·정합성 검사 | 소스 → 그래프 인덱스 | `code-graph.ts`, `knowledge-reconciler.ts` | 구조 |
| `dashboard*.ts`, `dashboard/*` | 로컬 웹 서버와 집계 | `events.jsonl` → 세션 → HTTP | `dashboard.ts` 주석 | 코드 확인(주석) |

**미확인 영역**: 위 "구조" 행의 동작, 에이전트별 어댑터 차이, recall 점수 계산, 외부 서비스.

---

## 4. 질문 (Questions)

사용자 질문의 답이다. 확정된 동작은 기능 스펙에 반영하고 여기서는 결론만 적는다. 아래 문서는 `7ba8bcc` 기준이다(1절 재확인 필요 목록 참고).

- [Q1: 혼자 쓰면서 프로젝트별로 나누기, 프로젝트마다 조금 다를 때](./questions/q1-solo-per-project-management.md) - *가능. `projects.yaml` namespace로 나누고, 차이는 같은 이름으로 통째 교체하거나 추가 파일·env로 뺀다*
- [Q2: `packages`(npm·Claude 플러그인)와 `mcp`는 어떻게 동작하고 원본 변경을 감지하나](./questions/q2-packages-and-mcp-sync.md) - *업스트림 변경 감지와 "무엇이 바뀌었나" diff는 둘 다 없다. 선언 변경(선언 해시·엔트리 해시)과 선언 대비 설치 불일치(`doctor`)만 본다. 고정(pin)한 선언을 여러 기기에 맞추는 설치기로는 쓸 만하다. 코드 읽기 + 순수 함수 실행 일부*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸. 현재 모두 미작성, 범위 승인 전.
- **비교 후보**: [skills-manager](../skills-manager/overview.md), [cc-switch](../cc-switch/overview.md) — 둘은 개인 로컬 도구이고 teamai는 git 기반 팀 배포라는 차이가 있어 보임 *(추론)*
