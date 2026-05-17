# Open Design 문서 중심 분석

분석 기준: 전체 소스 구현을 깊게 읽지 않고, `README.md`, `QUICKSTART.md`, `docs/`, `deploy/`, `design-systems/README.md`, `craft/README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, 루트 `package.json`, 주요 패키지 메타데이터를 중심으로 사용 방식과 기능을 정리했다.

## 1. 이 프로젝트의 목적

Open Design은 Claude Design의 오픈소스 대안으로 소개되는 로컬 우선 디자인 생성 제품이다. 사용자가 자연어로 “랜딩 페이지”, “대시보드”, “피치덱”, “모바일 앱 화면”, “디자인 시스템” 같은 산출물을 요청하면, Open Design이 로컬 데몬과 웹 UI를 통해 사용자의 기존 코딩 에이전트 CLI를 호출하고, 그 결과물을 샌드박스 iframe에서 미리보기 가능한 HTML/JSX/문서/미디어 산출물로 보여주는 구조다.

핵심 차별점은 자체 모델이나 자체 에이전트 루프를 새로 만들기보다, 사용자의 `claude`, `codex`, `cursor-agent`, `gemini`, `opencode` 등 기존 CLI를 디자인 엔진처럼 활용한다는 점이다. CLI가 없으면 Anthropic/OpenAI/Azure OpenAI/Google Gemini 계열 BYOK API 모드로도 실행할 수 있다.

근거 파일:
- `README.md`
- `QUICKSTART.md`
- `docs/spec.md`
- `docs/architecture.md`
- `docs/agent-adapters.md`
- `package.json`

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 단일 라이브러리가 아니라, 로컬 데몬 + Next.js 웹 앱 + 선택적 Electron 데스크톱 + CLI + 디자인 카탈로그가 포함된 대형 TypeScript 모노레포다. `pnpm-workspace.yaml` 기준 워크스페이스는 `apps/*`, `packages/*`, `tools/*`, `e2e`로 구성된다.

사용 방식은 크게 네 가지다.

1. 빠르게 써보기: 사전 빌드된 데스크톱 앱을 다운로드해서 실행한다.
2. Docker로 실행: `deploy/docker-compose.yml`을 사용해 `http://localhost:7456`에서 브라우저로 접속한다.
3. 소스에서 개발 실행: Node 24와 pnpm 10.33.x를 준비한 뒤 `pnpm tools-dev run web`을 실행한다.
4. 헤드리스/CLI 사용: 빌드된 `od` CLI로 프로젝트, 플러그인, 마켓플레이스, 런, 파일, 미디어 생성 작업을 제어한다.

일반 사용자는 소스 코드를 볼 필요 없이 “앱 실행 → 에이전트/API 모드 선택 → Skill 선택 → Design System 선택 → 프롬프트 입력 → 질문 폼 응답 → 결과 미리보기/저장” 흐름으로 사용하면 된다.

## 3. 핵심 기능

- 로컬 에이전트 CLI 자동 감지: `PATH`와 설정 디렉터리를 보고 Claude Code, Codex, Cursor Agent, Gemini CLI, OpenCode, Devin 등 여러 CLI를 후보로 잡는다.
- BYOK API 모드: 로컬 CLI가 없거나 특정 모델을 쓰고 싶을 때 API 키와 base URL을 설정해 사용할 수 있다.
- Skill 기반 산출물 생성: `SKILL.md`가 있는 폴더가 하나의 디자인 능력 단위가 된다.
- Design System 적용: `DESIGN.md` 기반 브랜드/시각 언어를 선택해 다음 생성에 주입한다.
- Craft 규칙 주입: 타이포그래피, 컬러, 접근성, 상태 커버리지, anti-ai-slop 같은 범용 디자인 품질 규칙을 스킬별로 주입한다.
- Artifact 미리보기: `<artifact>`를 파싱해 샌드박스 iframe으로 렌더링한다.
- 프로젝트 영속성: `.od/app.sqlite`, `.od/projects/<id>/`, `.od/artifacts/`에 대화, 프로젝트, 산출물, 열린 탭 등을 저장한다.
- 미디어 생성: 이미지, 비디오, 오디오, HyperFrames 템플릿 흐름이 문서와 changelog에 포함되어 있다.
- 플러그인/마켓플레이스: `SKILL.md` + `open-design.json` 기반으로 플러그인을 설치, 검증, 게시, 실행할 수 있는 방향으로 확장되어 있다.

## 4. 실행/사용 진입점

주요 사용자 진입점:

- Docker 실행:
  - `cd deploy`
  - `docker compose up -d`
  - `http://localhost:7456`
- 소스 실행:
  - `corepack enable`
  - `pnpm install`
  - `pnpm tools-dev run web`
- 데스크톱 포함 백그라운드 실행:
  - `pnpm tools-dev`
- 상태/로그/진단:
  - `pnpm tools-dev status`
  - `pnpm tools-dev logs`
  - `pnpm tools-dev check`
  - `pnpm tools-dev stop`
- 빌드/검증:
  - `pnpm typecheck`
  - `pnpm --filter @open-design/daemon build`
  - `pnpm --filter @open-design/web build`

CLI 진입점은 루트 `package.json`의 `bin.od = ./apps/daemon/dist/cli.js`와 `apps/daemon/package.json`의 `bin.od`다. `apps/daemon/src/cli.ts`에는 `media`, `mcp`, `research`, `plugin`, `ui`, `marketplace`, `project`, `run`, `files`, `conversation`, `daemon`, `atoms`, `skills`, `design-systems`, `craft`, `status`, `version`, `doctor`, `config` 같은 서브커맨드 라우팅이 보인다.

## 5. 주요 모듈과 책임

- `apps/web`: Next.js 16 + React 18 웹 UI. 채팅, 파일 워크스페이스, iframe 미리보기, 설정, 디자인/미디어 탭, BYOK/데몬 provider UI를 담당한다.
- `apps/daemon`: Node/Express 로컬 데몬. `/api/*`, SSE 스트리밍, SQLite, 에이전트 spawn, 스킬/디자인 시스템 로딩, 산출물 저장, 정적 파일 제공, `od` CLI를 담당한다.
- `apps/desktop`: Electron 셸. 웹 URL을 sidecar IPC로 발견하고 데스크톱 앱 형태로 감싼다.
- `apps/packaged`: 패키징된 Electron 런타임 진입부.
- `packages/contracts`: 웹/데몬 사이의 DTO, 이벤트, 공용 타입 계약.
- `packages/sidecar`, `packages/sidecar-proto`, `packages/platform`: sidecar 프로토콜과 OS/process 공통 유틸.
- `tools/dev`: `pnpm tools-dev` 로컬 개발 라이프사이클.
- `tools/pack`: 데스크톱/배포 패키징 도구.
- `tools/pr`: 유지보수자용 PR 관리 도구.
- `skills/`: 범용 기능 스킬. 현재 체크아웃 기준 `SKILL.md` 131개.
- `design-templates/`: 실제 렌더링용 디자인 템플릿 카탈로그. 현재 체크아웃 기준 `SKILL.md` 110개.
- `design-systems/`: 브랜드/스타일별 `DESIGN.md`. 현재 체크아웃 기준 149개.
- `craft/`: 브랜드와 무관한 디자인 품질 규칙.
- `plugins/`: 공식 atom/scenario/plugin 및 마켓플레이스 확장 기반.
- `deploy/`: Dockerfile, compose, 배포 문서.

## 6. 핵심 개념과 용어

- Skill: `SKILL.md`를 중심으로 한 하나의 에이전트 작업 능력. 예: 랜딩 페이지, 대시보드, PPT, 문서, 이미지 생성, Figma 관련 작업.
- Design System: `DESIGN.md` 9섹션 스키마로 표현되는 시각 언어. 브랜드 스타일, 색, 타이포그래피, 컴포넌트, 금지 패턴 등을 담는다.
- Craft: 브랜드와 무관하게 적용되는 품질 규칙. 예: 타이포그래피 위계, 컬러 남용 방지, 접근성, 상태 커버리지.
- Artifact: 에이전트가 생성한 HTML/JSX/문서/미디어 결과물. 웹 UI에서 iframe 또는 파일 뷰어로 본다.
- Local daemon: 브라우저/데스크톱 UI와 실제 파일시스템/에이전트 CLI 사이의 권한 있는 프로세스.
- BYOK: 사용자가 직접 API 키를 가져와 provider를 설정하는 방식.
- Plugin: 하나 이상의 Skill, 디자인 시스템, craft, assets, `open-design.json` 메타데이터를 묶은 배포 단위.
- Atom: 플러그인 pipeline에서 조합 가능한 1차 기능 단위. 예: `discovery-question-form`, `direction-picker`, `todo-write`, `live-artifact`, `critique-theater`.
- Critique Theater: 산출물을 다차원으로 평가하고 재시도/개선을 유도하는 품질 루프.

## 7. 입력/데이터/상태/제어 흐름

일반적인 생성 흐름은 다음과 같다.

1. 사용자가 웹/데스크톱 UI에서 Skill과 Design System을 고르고 프롬프트를 입력한다.
2. 웹 UI가 데몬의 `/api/chat` 또는 관련 run API로 요청을 보낸다.
3. 데몬은 활성 Skill, Design System, Craft, 프로젝트 메타데이터를 조합해 시스템 프롬프트/컨텍스트를 만든다.
4. 로컬 CLI 모드이면 데몬이 `.od/projects/<id>/`를 cwd로 에이전트 CLI를 spawn한다.
5. API 모드이면 `/api/proxy/{anthropic,openai,azure,google}/stream` 형태로 provider SSE를 정규화한다.
6. 에이전트 출력은 SSE로 웹 UI에 스트리밍된다.
7. UI는 Todo, tool call, 질문 폼, 텍스트 델타, `<artifact>`를 갱신한다.
8. 산출물은 `.od/projects/<id>/`와 `.od/artifacts/`에 저장되고, 대화/탭/프로젝트 상태는 `.od/app.sqlite`에 저장된다.

설계상 에이전트는 실제 파일을 읽고 쓰는 작업자로 취급된다. 따라서 결과물은 단순 채팅 텍스트가 아니라 로컬 디스크의 프로젝트 파일로 남는다.

## 8. 설정 및 환경 구성

필수 환경:

- Node.js `~24`
- pnpm `10.33.x`, 루트 `packageManager`는 `pnpm@10.33.2`
- macOS, Linux, WSL2가 주 경로
- Windows native도 지원하지만 `docs/windows-troubleshooting.md`의 별도 절차가 있다.

중요한 환경/설정:

- `.od/`: 로컬 런타임 데이터. gitignore 대상.
- `OD_DATA_DIR`: `.od` 데이터 위치 변경.
- `OD_MEDIA_CONFIG_DIR`: 미디어 API 키 설정 파일 위치 분리.
- `OD_BIN`, `OD_DAEMON_URL`, `OD_PROJECT_ID`, `OD_PROJECT_DIR`: 데몬이 에이전트 세션에 주입하는 미디어/도구 실행용 변수.
- `OPEN_DESIGN_PORT`: Docker 호스트 포트.
- `OPEN_DESIGN_MEM_LIMIT`: Docker 메모리 제한.
- `OPEN_DESIGN_ALLOWED_ORIGINS`: reverse proxy/CORS 허용 origin.
- `OPEN_DESIGN_IMAGE`: 사용할 Docker 이미지.

운영 노트:

- Docker 문서는 데몬 API가 비브라우저 클라이언트에 대해 인증되지 않을 수 있으므로, 공용 네트워크에 직접 노출하지 말고 인증 reverse proxy, SSH tunnel, VPN 앞에 두라고 설명한다.
- nginx 등 프록시 앞에서는 SSE 라우트에 buffering/gzip을 끄는 설정이 필요하다.

## 9. 의존성 구조

루트는 TypeScript ESM 모노레포다.

주요 의존성:

- 웹: `next`, `react`, `react-dom`, `lucide-react`, `openai`, `@anthropic-ai/sdk`, Tailwind/PostCSS, Vitest.
- 데몬: `express`, `better-sqlite3`, `chokidar`, `undici`, `multer`, `jszip`, `tar`, `@modelcontextprotocol/sdk`, OpenTelemetry/PostHog 관련 패키지.
- 데스크톱: `electron`.
- 도구: `cac`, `esbuild`, `tsx`, `typescript`.

워크스페이스 내부 의존성은 `@open-design/contracts`, `@open-design/platform`, `@open-design/sidecar`, `@open-design/sidecar-proto`, `@open-design/plugin-runtime`, `@open-design/registry-protocol`, `@open-design/agui-adapter` 등을 중심으로 연결된다.

## 10. 빌드/실행/테스트 방식

사용자 실행:

```bash
corepack enable
pnpm install
pnpm tools-dev run web
```

Docker 실행:

```bash
cd deploy
docker compose up -d
```

주요 개발 명령:

```bash
pnpm tools-dev
pnpm tools-dev start web
pnpm tools-dev run web
pnpm tools-dev restart --daemon-port 7457 --web-port 5175
pnpm tools-dev status
pnpm tools-dev logs
pnpm tools-dev check
pnpm tools-dev stop
pnpm typecheck
pnpm guard
pnpm --filter @open-design/daemon build
pnpm --filter @open-design/web build
```

루트 `AGENTS.md`는 `pnpm dev`, `pnpm start`, `pnpm daemon` 같은 레거시 루트 별칭을 되살리지 말고 `pnpm tools-dev`를 단일 로컬 라이프사이클 진입점으로 쓰라고 명시한다.

## 11. 에러 처리와 디버깅 포인트

문서상 자주 보는 문제와 확인 지점:

- 에이전트가 감지되지 않음: CLI가 `PATH`에 있는지, GUI 프로세스가 최소 PATH로 시작하지 않았는지, Settings의 Rescan을 확인한다.
- Claude Code 실패: 같은 환경에서 `claude --version`, `claude auth status --text`, non-interactive smoke test를 실행해 인증 상태를 확인한다.
- `better-sqlite3` ABI 문제: Node 버전 변경 후 `pnpm install` 또는 `pnpm --filter @open-design/daemon rebuild better-sqlite3`.
- 미디어 생성 실패: `OD_BIN`, `OD_DAEMON_URL`, `OD_PROJECT_ID`, `OD_PROJECT_DIR`가 실제 값인지 확인한다. `OD_DAEMON_URL`이 `http://127.0.0.1:0`이면 잘못된 상태다.
- artifact 미렌더링: 모델이 `<artifact>` 태그 없이 일반 텍스트를 낸 경우다. 더 강한 모델 또는 stricter skill이 필요할 수 있다.
- nginx 앞 SSE 끊김: `proxy_buffering off`, `gzip off`, 긴 timeout 설정 필요.
- Windows: Node 24, pnpm/Corepack, `pnpm approve-builds`, Visual Studio Build Tools, PowerShell execution policy를 점검한다.

## 12. 확장하거나 기여할 때 봐야 할 구조

기여자가 가장 빠르게 기여할 수 있는 표면은 문서 기준으로 세 가지다.

1. 새 산출물 종류 추가: `skills/<your-skill>/SKILL.md` 또는 최근 구조상 `design-templates/<your-template>/SKILL.md`를 추가한다.
2. 새 브랜드 스타일 추가: `design-systems/<brand>/DESIGN.md` 한 파일을 추가한다.
3. 새 에이전트 CLI 연결: `apps/daemon/src/agents.ts` 및 runtime 정의/stream parser 쪽을 확장한다.

플러그인 생태계 쪽은 `SKILL.md` + `open-design.json`을 기준으로 한다. `docs/plugins-spec.md`, `docs/publishing-a-plugin.md`, `docs/self-hosting-a-registry.md`에 따르면, 플러그인은 GitHub/HTTPS/local folder/registry에서 설치되고, marketplace JSON을 통해 검색/설치/검증/게시될 수 있다.

기여 전 확인할 문서:

- `CONTRIBUTING.md`
- `docs/skills-contributing.md`
- `docs/skills-protocol.md`
- `docs/design-systems.md`
- `docs/agent-adapters.md`
- `docs/plugins-spec.md`
- 루트 `AGENTS.md`
- 하위 디렉터리별 `AGENTS.md`

## 13. 처음 기여자가 먼저 읽어야 할 파일

사용자/운영자 관점:

1. `README.md`
2. `QUICKSTART.md`
3. `deploy/README.md`
4. `docs/windows-troubleshooting.md` (Windows인 경우)
5. `docs/architecture.md`

스킬/디자인 시스템 기여자 관점:

1. `CONTRIBUTING.md`
2. `docs/skills-contributing.md`
3. `docs/skills-protocol.md`
4. `design-systems/README.md`
5. `craft/README.md`
6. 가까운 기존 `skills/*/SKILL.md` 또는 `design-templates/*/SKILL.md`

코드 기여자 관점:

1. 루트 `AGENTS.md`
2. `apps/AGENTS.md`, `packages/AGENTS.md`, `tools/AGENTS.md`, `e2e/AGENTS.md`
3. `apps/web/package.json`
4. `apps/daemon/package.json`
5. `packages/contracts`
6. `tools/dev`

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- README와 하위 문서/현재 체크아웃 사이에 수치 불일치가 있다. 예를 들어 README 앞부분은 디자인 시스템 72개를 말하지만, `design-systems/README.md`와 실제 파일 수는 더 큰 카탈로그를 보여준다. 현재 체크아웃 기준 `design-systems/*/DESIGN.md`는 149개다.
- `docs/spec.md`와 `docs/roadmap.md` 일부는 “초기 설계/로드맵” 성격이 강하고, 현재 `CHANGELOG.md`와 실제 디렉터리 구조는 그보다 더 진행된 상태를 보여준다. 예를 들어 초기 spec의 non-goal에는 데스크톱 앱을 배제하는 내용이 있지만 현재는 `apps/desktop`, `apps/packaged`, Electron 패키징 문서가 존재한다.
- `plugins/` 하위 구조는 매우 크고, 이번 분석은 사용법 중심이라 전체 플러그인 구현 코드를 깊게 읽지 않았다. 실제 플러그인 런타임의 완성도는 별도 분석이 필요하다.
- `CHANGELOG.md`의 0.7.0 항목은 기능 추가 범위가 매우 넓다. 문서와 UI가 모두 최신 기능을 동일하게 설명하는지는 실제 앱 실행 후 확인하는 편이 좋다.
- 실제 생성 품질은 선택한 에이전트 CLI, 모델, 인증 상태, API provider, Skill/Design System 조합에 크게 좌우된다. 문서상 구조는 견고하지만, 사용자 경험 평가는 실행 검증이 필요하다.

## 사용자 관점 추천 사용 순서

1. 코드를 수정하지 않고 써볼 목적이면 Docker 또는 데스크톱 앱부터 사용한다.
2. 로컬 CLI 에이전트를 이미 쓰고 있다면 먼저 그 CLI가 같은 쉘의 `PATH`에서 동작하는지 확인한다.
3. 앱 첫 실행 후 Settings에서 Execution mode를 확인하고, CLI가 감지되지 않으면 BYOK API 모드로 시작한다.
4. 처음에는 기본 Skill과 기본 Design System으로 짧은 프롬프트를 입력한다.
5. 결과가 마음에 들면 `Design system`을 브랜드에 맞게 바꾸고, 목적에 맞는 Skill 또는 Template을 선택한다.
6. 피치덱/발표자료는 deck 계열, 랜딩/대시보드는 prototype/template 계열, 브랜드 룰을 먼저 만들고 싶으면 design-system 계열 흐름을 사용한다.
7. 산출물은 `.od/projects/<id>/`와 `.od/artifacts/`에 남으므로, 재사용하거나 백업하려면 이 폴더를 확인한다.

