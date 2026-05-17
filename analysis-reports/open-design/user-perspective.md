# Open Design 사용자 관점 조사

조사 기준: 기존 `analysis-reports/open-design/overview.md`와 `open-design` 저장소의 Markdown 문서(`README.md`, `QUICKSTART.md`, `deploy/README.md`, `docs/*.md`, `design-systems/README.md`, `craft/README.md`, 주요 skill/template README)를 기준으로 정리했다. 이번 조사는 코드 흐름이나 구현 검증이 아니라, 실제 사용자가 설치하고 실행한 뒤 어떤 기능을 어떻게 쓰고 결과물을 어떻게 확인/저장/공유할 수 있는지에 초점을 둔다.

## 1. 한 줄 요약

Open Design은 로컬 또는 데스크톱/브라우저 환경에서 실행하는 AI 디자인 생성 도구다. 사용자는 디자인 작업을 프롬프트로 요청하고, Open Design은 사용자의 기존 코드 에이전트 CLI 또는 BYOK API provider를 통해 랜딩 페이지, 대시보드, 모바일 화면, 발표자료, 문서형 산출물, 이미지/영상/오디오 결과물을 생성한 뒤 iframe 미리보기와 파일 형태로 보여준다.

사용자 입장에서 가장 중요한 점은 다음 세 가지다.

- Open Design 자체가 모델을 제공하기보다, 사용자가 가진 `claude`, `codex`, `cursor-agent`, `gemini`, `opencode` 같은 CLI 또는 Anthropic/OpenAI/Azure OpenAI/Google Gemini API 키를 사용한다.
- 산출물은 채팅 텍스트로만 끝나지 않고 `.od/projects/<id>/`, `.od/artifacts/` 같은 로컬 파일로 남는다.
- 결과물은 앱 안에서 미리보고, `Save to disk`, ZIP, HTML, PDF, PPTX, Markdown 같은 형태로 저장/공유하는 흐름을 지향한다.

## 2. 설치와 실행 선택지

### 2.1 데스크톱 앱

문서상 가장 빠른 사용 경로는 사전 빌드된 데스크톱 앱이다.

- 다운로드 위치: `open-design.ai` 또는 GitHub Releases
- 장점: Node, pnpm, 저장소 clone 없이 시작 가능
- 적합한 사용자: Open Design을 제품처럼 바로 써보고 싶은 사람

문서상 데스크톱 앱은 Electron 셸로 설명되며, 기존 개발 서버의 `.od/` 데이터를 데스크톱 앱 데이터 위치로 옮기는 migration 안내도 있다. 이미 저장소 개발 모드로 프로젝트를 만든 사용자는 데스크톱 앱과 dev-server가 서로 다른 데이터 디렉터리를 쓸 수 있다는 점을 알아야 한다.

### 2.2 Docker 실행

Docker는 Node.js와 pnpm을 로컬에 설치하지 않고 브라우저에서 써보는 경로다.

```bash
git clone https://github.com/nexu-io/open-design.git
cd open-design/deploy
docker compose up -d
```

접속 URL:

```text
http://localhost:7456
```

주요 Docker 명령:

```bash
docker compose logs -f
docker compose restart
docker compose down
docker compose pull
docker compose up -d
docker compose down -v
```

Docker 데이터는 `open_design_data` volume에 저장되고 컨테이너 내부 `/app/.od`에 mount된다. `docker compose down -v`를 실행하면 로컬 앱 데이터까지 제거된다.

주의점:

- 문서상 Docker 이미지는 Claude/Codex/Gemini 같은 코드 에이전트 CLI 바이너리를 번들하지 않는다.
- Docker로 서버 배포할 때 local CLI를 쓰려면 별도 private runtime layer나 컨테이너 내부 설치가 필요하다.
- 공용 네트워크에 daemon을 직접 노출하지 말라고 문서가 명시한다. 비브라우저 클라이언트에 대한 API 인증이 없을 수 있으므로 reverse proxy, SSH tunnel, VPN 같은 보호 계층이 필요하다.

### 2.3 소스에서 실행

개발자 또는 로컬 CLI 에이전트를 자연스럽게 쓰고 싶은 사용자는 소스 실행이 가장 직접적이다.

필수 환경:

- Node.js `~24`
- pnpm `10.33.x`
- macOS, Linux, WSL2가 주 경로
- Windows native는 지원하지만 별도 troubleshooting 문서가 있다.

실행:

```bash
git clone https://github.com/nexu-io/open-design.git
cd open-design
corepack enable
corepack pnpm --version
pnpm install
pnpm tools-dev run web
```

`pnpm tools-dev run web`은 daemon과 web을 foreground로 실행하고, 출력되는 web URL을 브라우저에서 열어 사용한다.

백그라운드/데스크톱 포함 실행:

```bash
pnpm tools-dev
```

운영/진단 명령:

```bash
pnpm tools-dev status
pnpm tools-dev logs
pnpm tools-dev check
pnpm tools-dev stop
pnpm tools-dev restart
pnpm tools-dev restart --daemon-port 7457 --web-port 5175
```

문서상 `pnpm dev`, `pnpm start`, `pnpm daemon` 같은 예전 별칭은 사용하지 않고 `pnpm tools-dev`를 단일 lifecycle 진입점으로 사용한다.

## 3. 첫 실행에서 사용자가 보는 흐름

문서 기준 첫 실행 흐름은 다음과 같다.

1. 앱이 설치된 코드 에이전트 CLI를 감지한다.
2. 감지된 CLI 중 하나를 자동 선택하거나, 사용자가 Settings에서 execution mode를 바꾼다.
3. CLI가 없으면 BYOK API mode를 선택해 provider, base URL, API key, model을 설정한다.
4. 기본값으로 `web-prototype` skill과 `Neutral Modern` 계열 design system이 선택된다.
5. 사용자가 프롬프트를 입력하고 Send를 누른다.
6. Open Design이 먼저 질문 폼을 띄워 목적, 대상, 톤, 브랜드 문맥, 제약을 확인한다.
7. 에이전트가 todo/progress를 스트리밍하고 `<artifact>` 결과를 생성한다.
8. 오른쪽 미리보기 영역에서 sandboxed iframe으로 결과를 확인한다.
9. 완료 후 `Save to disk` 또는 export/download 흐름으로 결과를 저장한다.

이 구조 때문에 사용자는 처음부터 긴 완성 프롬프트를 완벽하게 쓰기보다, 짧은 brief를 넣고 질문 폼에 답하면서 방향을 좁히는 방식으로 쓰는 것이 문서상 의도에 가깝다.

## 4. 실행 모드: Local CLI와 BYOK API

Open Design의 생성 방식은 크게 두 가지다.

| 방식 | 사용 조건 | 사용자 경험 |
|---|---|---|
| Local CLI | `claude`, `codex`, `cursor-agent`, `gemini`, `opencode` 등 지원 CLI가 PATH에 있음 | daemon이 해당 CLI를 project folder에서 실행하고 결과를 SSE로 받아 미리보기에 반영 |
| BYOK API | 로컬 CLI가 없거나 provider API를 직접 쓰고 싶음 | Anthropic/OpenAI/Azure OpenAI/Google Gemini 계열 API 키와 모델을 설정하고 동일한 artifact parser/iframe preview 사용 |

문서상 Local CLI는 PATH와 CLI별 설정 디렉터리를 스캔한다. GUI로 실행할 때 macOS 등에서 PATH가 짧게 잡히면 CLI가 설치되어도 감지되지 않을 수 있으므로 Settings의 Rescan과 실행 프로세스의 PATH 확인이 필요하다.

BYOK API mode는 로컬 CLI가 없어도 같은 미리보기 파이프라인을 쓰게 해주는 fallback이다. 다만 로컬 파일시스템/도구 사용 능력은 Local CLI 모드와 차이가 있을 수 있다.

## 5. 사용자가 선택하는 주요 개념

### 5.1 Skill

Skill은 “무엇을 만들 것인가”를 정하는 작업 능력이다. 문서상 각 skill은 `SKILL.md` 중심의 폴더로 구성되고, Open Design UI의 Skill picker에 나타난다.

대표 범주:

- Prototype: 랜딩 페이지, SaaS 페이지, 대시보드, 가격 페이지, 문서 페이지, 블로그 글, 모바일 앱 화면, 온보딩, 이메일 마케팅, 소셜 캐러셀, 포스터, 모션 프레임 등
- Deck: `guizang-ppt`, `simple-deck`, `replit-deck`, `weekly-update` 같은 발표자료/슬라이드
- Office/operations: PM spec, OKR, 회의록, kanban board, runbook, finance report, invoice, HR onboarding 등
- Template: 이미 검증된 템플릿을 채워 빠르게 결과를 만드는 방식
- Design System: 다른 산출물의 입력이 되는 `DESIGN.md`를 만드는 방식

문서상 `README.md`는 built-in skill 31개를 말하고, Quickstart는 기본 skill 예시와 mode별 picker를 설명한다.

### 5.2 Design System

Design System은 “어떤 시각 언어로 만들 것인가”를 정한다. 각 design system은 `DESIGN.md` 문서로 표현되며, top-bar의 Design system dropdown에서 선택한다.

문서상 제공 예시:

- Neutral Modern, Warm Editorial 같은 starter
- Linear, Stripe, Vercel, Airbnb, Tesla, Notion, Apple, Anthropic, Cursor, Supabase, Figma 등 product system
- awesome-design-skills 기반 design system

사용자는 design system을 바꾼 뒤 다음 생성부터 같은 brief를 다른 브랜드/시각 언어로 렌더링할 수 있다. 직접 design system을 추가하려면 새 폴더에 `DESIGN.md`를 넣고 refresh/restart하면 picker에 나타나는 구조로 설명되어 있다.

### 5.3 Craft

Craft는 브랜드와 무관한 디자인 품질 규칙이다. 예를 들어 typography, color, anti-ai-slop, accessibility, animation discipline, form validation 같은 규칙이 skill에 의해 필요한 만큼 prompt에 주입된다.

사용자가 직접 조작하는 옵션이라기보다는, 특정 skill이 더 나은 결과를 내도록 뒤에서 적용되는 품질 레이어에 가깝다.

## 6. 주요 기능

### 6.1 디자인/프로토타입 생성

Prototype mode는 단일 화면 또는 짧은 flow를 HTML/JSX로 생성한다. 예시는 랜딩 페이지, 대시보드, 모바일 앱 화면, pricing page, docs page, blog post 등이다.

사용 방식:

1. Prototype mode 또는 관련 skill 선택
2. Design system 선택
3. brief 입력
4. 질문 폼 응답
5. 오른쪽 iframe preview 확인
6. chat/comment/refinement로 수정 요청
7. HTML/PDF/ZIP 등으로 저장

문서상 preview는 sandboxed iframe을 사용하며, HTML은 `srcdoc`, JSX는 React/Babel 기반 렌더링으로 설명된다.

### 6.2 발표자료/Deck 생성

Deck mode는 다중 슬라이드 HTML presentation을 만든다. `guizang-ppt`는 magazine-style web PPT의 기본 deck skill로 설명된다.

사용 방식:

1. Deck mode 선택
2. `guizang-ppt`, `simple-deck` 등 deck skill 선택
3. 주제, outline, slide count, theme 관련 정보를 입력
4. iframe preview에서 화살표/스크롤/터치 기반으로 확인
5. PDF/PPTX/ZIP 등으로 export

문서상 PPTX export는 deck skill이 `slides.json` 같은 중간 구조를 제공할 때 더 잘 동작하고, 없으면 page capture fallback이 될 수 있다.

### 6.3 Template mode

Template mode는 agent가 처음부터 디자인 결정을 하기보다, curated template의 slot을 채우는 방식이다.

적합한 경우:

- 빠른 결과가 필요할 때
- layout 품질을 template에 맡기고 content만 바꾸고 싶을 때
- prompt에 익숙하지 않은 사용자가 안정적인 결과를 원할 때

문서상 Template mode는 Prototype보다 빠르지만, template 밖으로 크게 벗어나는 자유도는 낮다.

### 6.4 Design System 생성

Design System mode는 `DESIGN.md` 자체를 만든다. 입력은 screenshot, brand guide PDF, public URL, 자유 텍스트 brief 등이 될 수 있다고 문서화되어 있다.

출력:

- `DESIGN.md`
- `preview.html`
- 선택적 `tokens.json`

이 결과를 active design system으로 설정하면 이후 prototype/deck/template 생성에 같은 브랜드 룰을 적용할 수 있다.

### 6.5 이미지/영상/오디오/HyperFrames

README는 같은 채팅 화면에서 이미지, 영상, 오디오, HyperFrames HTML-to-MP4 motion graphics 생성도 다룬다고 설명한다.

문서상 예시:

- Image: `gpt-image-2` via Azure/OpenAI
- Video: `seedance-2.0`
- HTML to MP4: HyperFrames
- prompt gallery: 이미지/영상/HyperFrames 템플릿 prompt

결과물은 `.png`, `.mp4` 같은 실제 파일로 project workspace에 남고, turn 종료 후 download chip으로 표시되는 흐름으로 설명되어 있다.

### 6.6 Claude Design ZIP import

README는 Claude Design export ZIP을 welcome dialog에 drop하면 Open Design project로 가져와 계속 편집할 수 있다고 설명한다. API 경로는 `/api/import/claude-design`로 언급된다.

이미 Claude Design에서 만든 산출물이 있고, Open Design에서 이어서 수정/저장/공유하고 싶은 사용자에게 중요한 migration 기능이다.

### 6.7 Plugin과 Marketplace

Plugin은 하나 이상의 skill, design system, craft rule, asset, preview, `open-design.json`을 묶은 배포 단위다.

사용자 관점:

- marketplace에서 plugin을 선택해 workflow를 실행할 수 있다.
- CLI나 headless 환경에서도 `od plugin install`, `od run ...` 형태로 같은 workflow를 실행하는 방향이다.
- private marketplace/self-hosted registry도 문서화되어 있다.

작성자 관점 주요 명령:

```bash
od plugin scaffold --id vendor/plugin-name --title "Plugin name" --out ./plugins/community
od plugin validate ./plugins/community/plugin-name
od plugin pack ./plugins/community/plugin-name --out ./dist
od plugin login
od plugin publish vendor/plugin-name --to open-design --repo https://github.com/vendor/plugin-name
od marketplace refresh official
od plugin install vendor/plugin-name
```

주의: plugin/marketplace 문서는 v1 spec 성격이 강한 부분이 섞여 있으므로, 실제 UI 완성도는 앱 실행 검증이 필요하다.

## 7. 결과 확인 방법

Open Design의 결과 확인은 크게 네 곳에서 이뤄진다.

1. Chat/progress pane: 에이전트의 질문, todo, tool stream, 생성 진행상태 확인
2. Preview iframe: `<artifact>`로 감싼 HTML/JSX 결과물의 실시간 미리보기
3. File workspace: agent가 만든 파일, asset, 산출물 확인
4. Local disk: `.od/projects/<id>/`, `.od/artifacts/<timestamp>-<slug>/` 아래 실제 파일 확인

문서상 첫 생성 결과는 오른쪽 sandboxed iframe에서 렌더링되고, 완료 후 `Save to disk`를 누르면 `./.od/artifacts/<timestamp>-<slug>/index.html` 같은 형태로 저장된다.

대표 저장 구조:

```text
.od/
├── app.sqlite
├── artifacts/
│   └── <timestamp>-<slug>/
│       ├── artifact.json
│       ├── index.html
│       └── assets/
└── projects/<id>/
```

`app.sqlite`에는 projects, conversations, messages, tabs, saved templates 같은 상태가 저장되고, artifact 파일은 별도의 폴더로 남는다.

## 8. 결과 저장, export, 공유

문서상 지원/지향 export 형태:

- HTML: CSS와 asset을 inline 처리한 self-contained HTML
- PDF: browser rendering 기반 PDF
- PPTX: deck skill의 `slides.json` 또는 agent-driven export 기반
- ZIP: artifact folder 전체 압축
- Markdown: `.md` artifact 직접 복사 또는 skill-defined render

사용자가 결과를 공유하는 방법:

- 앱에서 `Save to disk` 후 `.od/artifacts/<...>/index.html`을 직접 열거나 전달
- project ZIP으로 다운로드해 다른 사람에게 공유
- HTML/PDF/PPTX로 export해 비개발자에게 전달
- `.od/artifacts/`를 git에 추가해 PR에서 디자인 결과를 리뷰
- media 결과물은 `.png`, `.mp4` download chip 또는 workspace 파일로 공유

문서상 artifact store는 plain files를 전제로 하며, `git add ./.od/artifacts/`로 디자인을 PR에서 리뷰할 수 있다고 설명한다. 다만 `.od/`는 기본적으로 machine-local/gitignored 성격이므로, 어떤 artifact를 팀 공유 대상으로 삼을지는 사용자가 명시적으로 선택하는 방식이 적절하다.

## 9. 실제 사용 시나리오별 추천 흐름

### 9.1 빠르게 제품 느낌 보기

1. 데스크톱 앱 또는 Docker 실행
2. BYOK API mode 또는 감지된 CLI 선택
3. `web-prototype` 또는 `saas-landing` 선택
4. `Neutral Modern`, `Linear`, `Vercel`, `Stripe` 같은 design system 선택
5. “우리 제품의 랜딩 페이지를 만들어줘” 수준의 brief 입력
6. 질문 폼에 답하고 preview 확인
7. 마음에 들면 `Save to disk` 또는 ZIP export

### 9.2 대시보드/운영 화면 만들기

1. Prototype mode에서 `dashboard` skill 선택
2. 데이터 밀도, sidebar 여부, KPI, table/chart 요구사항을 질문 폼에 입력
3. Preview에서 정보 구조 확인
4. 필요한 경우 “이 카드를 위로”, “테이블 컬럼 줄여줘” 같은 chat 수정 요청
5. HTML/ZIP으로 저장해 개발자에게 전달

### 9.3 발표자료 만들기

1. Deck mode 선택
2. `guizang-ppt` 또는 `simple-deck` 선택
3. slide count, audience, outline, tone 지정
4. iframe에서 슬라이드 네비게이션 확인
5. PDF/PPTX/ZIP으로 export

### 9.4 브랜드 스타일 먼저 만들기

1. Design System mode 선택
2. screenshot, URL, brand guide, 또는 텍스트 brief 입력
3. 생성된 `DESIGN.md`와 sample preview 확인
4. active design system으로 설정
5. 이후 Prototype/Deck/Template 생성에 적용

### 9.5 기존 Claude Design 결과 이어가기

1. Claude Design export ZIP 준비
2. Open Design welcome dialog에 ZIP drop
3. import된 project에서 기존 artifact 확인
4. chat으로 수정 요청하거나 다른 skill로 변환
5. Open Design의 저장/export 흐름으로 공유

## 10. 운영과 데이터 관리

소스 실행 기준 `.od/`는 repo root에 자동 생성된다. 별도 `od init` 단계는 없다.

데이터 위치 변경:

```bash
OD_DATA_DIR=<path> pnpm tools-dev run web
```

미디어 credential 위치만 분리:

```bash
OD_MEDIA_CONFIG_DIR=<dir> pnpm tools-dev run web
```

초기화:

```bash
pnpm tools-dev stop
rm -rf .od
pnpm tools-dev run web
```

Docker 기준 데이터는 volume에 있으므로, 완전 초기화는 다음 명령을 사용한다.

```bash
docker compose down -v
```

reverse proxy 앞에 둘 경우 SSE 라우트는 buffering/gzip을 끄고 긴 timeout을 둬야 한다는 nginx 관련 안내가 있다.

## 11. 자주 막히는 지점과 확인법

### 11.1 에이전트 CLI가 감지되지 않음

확인할 것:

- CLI executable이 daemon 프로세스의 `PATH`에 있는지
- GUI 앱이 최소 PATH로 뜬 것은 아닌지
- Settings -> Execution mode에서 Rescan했는지
- CLI가 실제로 로그인/인증되어 있는지

CLI가 없으면 Settings에서 API mode로 전환해 provider key를 설정한다.

### 11.2 Claude Code가 실행되지만 실패함

문서상 같은 환경에서 다음을 확인하라고 안내한다.

```bash
claude --version
claude auth status --text
printf 'hello' | claude -p --output-format stream-json --verbose --permission-mode bypassPermissions
```

인증 오류가 나오면 같은 환경에서 `claude`를 실행해 로그인한 뒤 다시 Open Design을 실행한다.

### 11.3 artifact가 렌더링되지 않음

문서상 원인은 모델이 `<artifact>` 태그 없이 일반 텍스트만 낸 경우가 대표적이다.

대응:

- daemon log에서 system prompt가 들어갔는지 확인
- 더 강한 모델로 변경
- 더 엄격한 skill 선택
- brief를 더 구체화해 재생성

### 11.4 media generation 실패

문서상 image/video/audio/HyperFrames skill은 daemon이 agent에 주입하는 환경 변수에 의존한다.

중요 변수:

- `OD_BIN`
- `OD_DAEMON_URL`
- `OD_PROJECT_ID`
- `OD_PROJECT_DIR`

`OD_BIN` 누락, `apps/daemon/dist/cli.js` 누락, `http://127.0.0.1:0` 같은 daemon URL 문제가 나오면 daemon CLI build 후 runtime을 재시작하라고 안내한다.

```bash
pnpm --filter @open-design/daemon build
pnpm tools-dev restart --daemon-port 7457 --web-port 5175
```

### 11.5 Windows native

Windows native는 지원하지만 별도 troubleshooting 문서가 필요할 만큼 setup 변수가 많다.

문서상 주요 확인 항목:

- Node 24
- pnpm/Corepack
- build scripts 승인
- Visual Studio Build Tools / `gyp`
- PowerShell execution policy
- Windows native와 WSL의 CLI credential store 차이

## 12. 문서 기준으로 본 지원 기능 정리

| 영역 | 사용자에게 보이는 기능 |
|---|---|
| 실행 | 데스크톱 앱, Docker, 소스 실행, headless/CLI 지향 |
| 생성 엔진 | Local CLI auto-detect, BYOK API fallback |
| 디자인 생성 | prototype, landing, dashboard, mobile, docs, blog, pricing, email, social carousel 등 |
| 발표자료 | magazine web PPT, simple deck, product walkthrough, weekly update |
| 문서/업무 산출물 | PM spec, OKR, meeting notes, runbook, finance report, invoice, onboarding |
| 브랜드 적용 | `DESIGN.md` 기반 design system picker |
| 품질 규칙 | craft rules, anti-ai-slop, accessibility, typography, color 등 |
| 미리보기 | sandboxed iframe, artifact parser, deck navigation |
| 저장 | `.od/app.sqlite`, `.od/projects/<id>/`, `.od/artifacts/` |
| 공유 | Save to disk, ZIP, HTML, PDF, PPTX, Markdown, git-based artifact review |
| 가져오기 | Claude Design ZIP import, folder import 문서화 |
| 확장 | `SKILL.md`, `DESIGN.md`, plugin/marketplace, private registry |

## 13. 실제 사용자에게 권장하는 시작 순서

1. 단순 체험이면 데스크톱 앱 또는 Docker로 시작한다.
2. 로컬 CLI 에이전트를 적극적으로 쓰려면 소스 실행 또는 CLI가 들어간 private Docker runtime을 사용한다.
3. CLI가 감지되지 않으면 바로 BYOK API mode로 전환해 첫 결과를 확인한다.
4. 처음에는 `web-prototype` + `Neutral Modern` 또는 잘 아는 브랜드 design system으로 짧은 brief를 넣는다.
5. 결과가 나오면 skill을 바꿔 목적을 좁힌다. 예: landing은 `saas-landing`, 운영 화면은 `dashboard`, 발표자료는 `guizang-ppt`.
6. 팀 공유가 필요하면 `Save to disk` 후 ZIP/HTML/PDF/PPTX로 내보낸다.
7. 반복 작업이 많아지면 custom `DESIGN.md`와 custom skill/plugin을 만든다.

## 14. 아직 불확실하거나 실행 검증이 필요한 부분

- 문서끼리 built-in design system 수치가 다르다. `README.md`는 129개, Quickstart의 일부 문장은 71/72개를 말한다. 기존 `overview.md`도 실제 체크아웃 기준 더 큰 수치를 언급한다. 사용자 문서 기준으로는 “많은 built-in system이 있고, 버전/문서 위치에 따라 수치가 다르다”고 보는 것이 안전하다.
- `docs/modes.md`에는 Template mode와 Design System mode가 자세히 설명되어 있지만, Quickstart 마지막 부분은 “현재 ship skills는 첫 두 mode 중심”이라고 말한다. 실제 UI에서 어느 정도 노출되는지는 실행 확인이 필요하다.
- plugin/marketplace 문서는 v1 spec과 roadmap 성격이 섞여 있다. CLI 명령과 UX 방향은 명확하지만, 현재 체크아웃의 실제 완성도는 별도 실행 검증이 필요하다.
- export 문서는 HTML/PDF/PPTX/ZIP/Markdown을 설명하지만, PPTX는 deck skill의 중간 구조나 agent-driven output에 따라 품질 차이가 있을 수 있다.
- 실제 생성 품질은 선택한 agent CLI, 모델, 인증 상태, provider, skill, design system 조합에 크게 좌우된다.

## 15. 근거 문서

- `analysis-reports/open-design/overview.md`
- `open-design/README.md`
- `open-design/QUICKSTART.md`
- `open-design/deploy/README.md`
- `open-design/docs/modes.md`
- `open-design/docs/architecture.md`
- `open-design/docs/agent-adapters.md`
- `open-design/docs/design-systems.md`
- `open-design/docs/skills-protocol.md`
- `open-design/docs/plugins-spec.md`
- `open-design/docs/publishing-a-plugin.md`
- `open-design/docs/critique-theater.md`
- `open-design/docs/windows-troubleshooting.md`
- `open-design/design-systems/README.md`
- `open-design/craft/README.md`
- `open-design/design-templates/*/README.md`
