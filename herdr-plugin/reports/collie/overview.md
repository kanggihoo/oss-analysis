---
sha: "c6a690d817bf8035092e69f4a7429f26b225a66a"
created: 2026-10-24
updated: 2026-10-24
sources:
  - herdr-plugin.toml
  - package.json
  - README.md
  - LICENSE
  - TRADEMARKS.md
  - .env.example
  - commands.toml.example
  - keys.toml.example
  - launchers.toml.example
  - quick-replies.toml.example
  - theme.toml.example
  - cache-rules.toml.example
  - systemd/collie.service
  - flake.nix
  - scripts/collie-ctl.sh
  - scripts/install.sh
  - scripts/build-nerd-font.sh
  - cli/main.ts
  - cli/program.ts
  - cli/lifecycle.ts
  - cli/unit.ts
  - cli/serve.ts
  - cli/context.ts
  - cli/update.ts
  - cli/sys.ts
  - cli/history.ts
  - cli/mux.ts
  - cli/hooks.ts
  - cli/beacon.ts
  - cli/hold.ts
  - cli/walky.ts
  - cli/crew.ts
  - cli/durable-attach.ts
  - cli/install-kind.ts
  - bridge/index.ts
  - bridge/server.ts
  - bridge/config.ts
  - bridge/state-engine.ts
  - bridge/event-poker.ts
  - bridge/notifications.ts
  - bridge/notify-prefs.ts
  - bridge/push.ts
  - bridge/pairing.ts
  - bridge/update.ts
  - bridge/sources.ts
  - bridge/machines.ts
  - bridge/worktree-folder.ts
  - bridge/mux/registry.ts
  - bridge/mux/types.ts
  - bridge/mux/capabilities.ts
  - bridge/mux/herdr/client.ts
  - bridge/mux/herdr/adapter.ts
  - bridge/mux/herdr/events.ts
  - bridge/mux/herdr/sessions.ts
  - bridge/mux/herdr/machine-list.ts
  - bridge/mux/tmux/adapter.ts
  - bridge/mux/zellij/adapter.ts
  - bridge/mux/tern/adapter.ts
  - bridge/mux/tuios/adapter.ts
  - bridge/mux/durable/adapter.ts
  - bridge/journal/registry.ts
  - bridge/surface/protocol.ts
  - bridge/stt/config.ts
  - bridge/stt/index.ts
  - bridge/stt/whistle-pins.ts
  - bridge/walky/socket.ts
  - bridge/walky/address.ts
  - bridge/crew/router.ts
  - bridge/crew/transport.ts
  - bridge/crew/enrollment.ts
  - bridge/cache/engine.ts
  - web/src/router.tsx
  - web/src/routes/home.tsx
  - web/src/stt/worker.ts
  - web/src/lib/harness/registry.ts
  - packages/durable-sdk/package.json
  - web/public/stt/needle-3-93e88ede/PROVENANCE.md
---

# collie Analysis Overview

범례: 검증 수준은 `코드 확인`(구현부를 직접 읽음) / `추론` / `미확인`. 이 문서는 실행하지 않고 읽기만 했으므로 `실행 확인`은 없다. 경로는 모두 `herdr-plugin/repos/collie/` 기준이고, `파일:줄`은 기준 SHA에서 직접 열어 확인한 줄이다. README·ARCHITECTURE.md·HERDR_API.md·MUX_CONTRACT.md·CREW_PROTOCOL.md·PACK_DEPUTY_RFC.md·CLAUDE.md는 후보로만 읽었고, 코드로 확인한 것만 표에 옮겼다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/AltanS/collie`
- **기준 SHA**: `c6a690d817bf8035092e69f4a7429f26b225a66a` (commit 2026-10-23, main)
- **작업트리 상태**: Clean (추적 파일 3667개, `git ls-files` 집계)
- **분석 목적**: 학습·도입 검토. (1) herdr 플러그인이 `herdr-plugin.toml`·소켓·CLI로 herdr와 어떻게 연동하는지, (2) herdr 밖의 멀티플렉서까지 어떻게 같은 구조로 묶는지, (3) 폰 웹 UI가 어떤 기능을 주는지.
- **라이선스**: MIT, 루트 `LICENSE`에 직접 확인("Copyright (c) 2026 Altan Sarisin"). 하위 라이선스는 아래와 같다(`git ls-files`에서 `LICENSE*`를 찾아 각각 열어 확인).
  - `packages/durable-sdk/LICENSE`: MIT. 루트 `LICENSE`와 `diff` 결과 동일(저작권자도 Altan Sarisin). `package.json`의 `license`도 `MIT`.
  - `tools/oxlint/anti-slop/LICENSE`: MIT, "Copyright (c) 2026 Dillon Mulroy". 외부 oxlint 플러그인을 복사해 넣은 것(`tools/oxlint/README.md`: 출처 `dmmulroy/anti-slop`, commit `446268e`).
  - `web/public/stt/needle-3-93e88ede/LICENSE`: Apache License 2.0. 음성 엔진 needle(Cactus Compute)을 그대로 복사한 것(`PROVENANCE.md`).
  - `web/public/fonts/LICENSE-*.txt` 6개(aldrich, atkinson-hyperlegible-next, geist, ibm-plex-sans, play, space-grotesk): 각각 SIL Open Font License 1.1(파일 첫 문단에 명시). `web/public/fonts/LICENSE.txt`: MIT, "Copyright (c) 2014 Ryan L McIntyre". `scripts/build-nerd-font.sh:43`이 Nerd Fonts 압축본의 `LICENSE`를 이 이름으로 복사하므로 `nerd-symbols-*.woff2` 쪽 라이선스다.
  - `TRADEMARKS.md`가 있다. 이름 "ColliePWA/Collie"와 로고 사용 조건을 적은 문서다(코드 라이선스와 별개). 조건 내용은 읽지 않았다.
- **분석 대상 제품**: 단일 레포 안에 배포 단위가 여럿이다.
  - 루트 앱 `collie` v1.24.0(`herdr-plugin.toml`, `package.json`): `cli/`(Bun 단일 바이너리 `bin/collie`), `bridge/`(Bun HTTP 서버), `web/`(Vite PWA)가 한 제품이다.
  - 별도 npm 패키지 `@colliepwa/durable-sdk` 0.1.0(`packages/durable-sdk/package.json`).
  - 부속·실험: `examples/`, `experiments/`, `packaging/`(AUR·Omarchy·Nix), `flake.nix`, `systemd/`, `integration/`, `tools/oxlint`, `scripts/`.
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음

### 레포 규모 (디렉터리별 추적 파일 수, `git ls-files` 집계)

| 위치 | 파일 수 | 성격 |
|---|---|---|
| `web/src` | 2336 (그중 `fixtures` 1078, `lib` 647, `components` 375, `hooks` 102) | 폰 PWA 본체 |
| `bridge/` | 567 | 서버 |
| `scripts/` | 137 | 설치·빌드·릴리스·하네스 점검 도구 |
| `cli/` | 133 | `collie` 명령 전부 |
| `.adr/` | 116 | 결정 기록 |
| `web/e2e` | 72 | 브라우저 테스트 |
| `examples/durable-member`, `examples/durable-harness` | 40, 22 | SDK 예제 |
| `web/public` | 39 | 아이콘·폰트·STT 엔진 |
| `packages/durable-sdk` | 31 | npm 패키지 |
| `docs/` | 마크다운 24 + 이미지 23 | 사용자 문서(후보로만 읽음) |
| `tools/oxlint` | 21 | 복사해 온 린트 플러그인 |
| `experiments/` | 17 + 3 | 실험 |
| `packaging/` | aur 6, nix 2, omarchy 2 | 패키지 정의 |

### 용어

- **herdr**: 코딩 에이전트용 터미널 멀티플렉서. workspace > tab > pane 계층을 가진다. collie는 workspace를 "space"라 부른다.
- **멀티플렉서(mux)**: 한 터미널 안에서 여러 pane을 돌리는 도구. herdr, tmux, zellij, tuios, tern이 여기에 든다.
- **브리지(bridge)**: 폰과 멀티플렉서 사이에 서는 Bun 프로세스. UI 정적 파일과 JSON API를 내고 멀티플렉서를 폴링한다.
- **PWA**: 홈 화면에 설치하는 웹 앱.
- **Tailscale / `tailscale serve`**: 개인 VPN(tailnet). `serve`는 tailnet 안에서만 HTTPS로 로컬 포트를 열어 준다. `funnel`은 인터넷에 공개하는 명령이라 쓰면 안 된다고 문서가 못 박는다(후보).
- **front door(정문)**: 브리지 앞에서 TLS를 끝내고 요청을 넘겨 주는 하나의 입구. 기본은 `tailscale serve`.
- **하네스(harness)**: Claude Code, Codex 같은 에이전트 CLI 하나. collie는 하네스별로 화면 문법(web)과 세션 로그 읽기(bridge)를 따로 둔다.
- **journal**: 에이전트가 디스크에 쓰는 대화 로그. 터미널 스크롤백 대신 이것을 읽어 히스토리를 보여 준다.
- **Ask**: 에이전트 화면의 질문·권한 대화상자를 읽어 폰의 눌러서 답하는 카드로 바꾼 것.
- **페어링**: 터미널에서 일회용 코드를 만들고 폰이 그것을 토큰과 바꾸는 절차. 이후 모든 요청에 토큰이 필요하다.
- **crew**: 여러 머신의 collie를 한 URL 뒤에 묶은 것. lead 하나와 peer들, 미리 지정한 deputy로 구성된다.
- **walky talky**: 에이전트 세션끼리, 또는 폰에서 세션으로 짧은 메시지를 보내는 기능.
- **durable agent**: 화면이 없는 장기 실행 프로그램. collie가 그 프로그램을 "세션"으로 보여 준다(실험).
- **beacon**: 에이전트가 자기 hook으로 남기는 "이 pane의 에이전트는 이것"이라는 힌트 파일.
- **Whistle**: collie가 쓰는 음성 인식 엔진 이름(Cactus Compute의 needle WebAssembly + 모델).

---

## 2. 프로젝트 개요

터미널 안에서 도는 AI 에이전트를 폰에서 보고 답하게 하는 자체 호스팅 웹 앱이다. 터미널 키보드로 SSH 접속하는 불편(특수키, 소프트 키보드)을 없애는 것이 출발점이다(README, 후보). 폰이 멀티플렉서에 직접 닿지 않고, 로컬 브리지가 멀티플렉서에서 스냅샷을 폴링해 JSON으로 내주며, 폰의 입력은 브리지가 실제 터미널 pane에 타이핑한다. herdr는 기본 대상이고, herdr 플러그인으로 설치하는 경로도 지원한다.

핵심 설계 한 줄: 서버는 herdr 플러그인 pane이 아니라 별도 서비스로 돌고, herdr 플러그인은 서비스를 켜고 끄는 얇은 런처(액션 11개 + 빌드 1개)다(코드 확인, 아래 C1).

### 코드로 확인한 주장 (README·ARCHITECTURE와 코드 대조)

| # | 주장 | 근거 | 검증 수준 |
|---|---|---|---|
| 1 | 매니페스트는 `[[build]]` 1개와 `[[actions]]` 11개뿐이다(`start` `stop` `restart` `uninstall` `update` `update-major` `url` `status` `version` `push-keys` `push-test`). 모두 `contexts = ["workspace"]`, `platforms = ["linux","macos"]`, `min_herdr_version = "0.7.0"`. `[[startup]]`·`[[panes]]`·`[[events]]`는 없다. | `herdr-plugin.toml:1-6,31-33,35-117`(`grep`으로 섹션 집계: 12개 섹션 모두 `[[build]]`/`[[actions]]`) | 코드 확인(매니페스트). herdr가 이를 어떻게 해석·강제하는지는 미확인 |
| 2 | 모든 액션 명령은 `bash scripts/collie-ctl.sh <verb>`이고, 이 셸은 `bin/collie`가 없으면 Bun으로 `cli/main.ts build`를 돌려 바이너리를 만든 뒤 `exec`로 넘긴다. 셸 자체는 동사를 구현하지 않는다. | `scripts/collie-ctl.sh:96-119`, `herdr-plugin.toml:35-117` | 코드 확인 |
| 3 | `[[build]]`는 `collie-ctl.sh build`다. 이 단계는 Bun이 PATH에 있어야 한다. | `herdr-plugin.toml:31-33`, `scripts/collie-ctl.sh:96-107` | 코드 확인(herdr가 `plugin install` 때만 실행한다는 주석은 herdr 쪽이라 미확인) |
| 4 | 브리지는 `collie _exec-bridge`로 뜬다. 이 동사는 `.env`를 합쳐 `process.env`에 넣고 `bridge/index.ts`를 같은 프로세스에서 `import`한다. systemd unit의 `ExecStart`가 이것이다. | `cli/lifecycle.ts:1234-1242`, `systemd/collie.service`(`ExecStart=@PLUGIN_ROOT@/bin/collie _exec-bridge`) | 코드 확인 |
| 5 | 서비스 감독자는 4가지다: `systemd --user`, `launchd`, Windows Task Scheduler, 감독 없음. 순서대로 탐지한다. `COLLIE_SUPERVISOR`로 고정할 수 있다. | `cli/lifecycle.ts:111-113,168-180` | 코드 확인 |
| 6 | unit/plist에는 `HERDR_SOCKET_PATH`, `COLLIE_PORT`, `HERDR_PLUGIN_CONFIG_DIR`, `COLLIE_PLUGIN_ROOT`(+ 있으면 `COLLIE_INSTANCE`, `COLLIE_TAILSCALE_HOSTS`)를 구워 넣는다. herdr가 주입하는 환경변수에 의존하지 않고 서비스가 스스로 가진다. | `cli/unit.ts:114-129` | 코드 확인 |
| 7 | 브리지는 기본 `127.0.0.1`에만 바인드하고, 루프백이 아닌 `COLLIE_HOST`는 `COLLIE_ALLOW_NON_LOOPBACK_BIND=1` 없이는 시작을 거부한다. | `bridge/config.ts:459-500`, `bridge/server.ts:2407-2409` | 코드 확인 |
| 8 | herdr 소켓 경로는 `HERDR_SOCKET_PATH`, 없으면 `~/.config/herdr/herdr.sock`(Windows는 `%APPDATA%\herdr\herdr.sock`). | `bridge/config.ts:510-523,697` | 코드 확인 |
| 9 | herdr RPC는 요청 하나당 새 연결을 열고 한 줄 JSON `{id, method, params}`를 보내 한 줄 응답을 받는다. 기본 5초, worktree 생성·열기는 60초 제한. Windows는 named pipe를 `node:net`으로 뚫는다. | `bridge/mux/herdr/client.ts:282,289,313-380`, `bridge/dial.ts:83` | 코드 확인(Windows 파이프 실제 동작은 미확인) |
| 10 | 상태는 폴링이 진실이다. 한 번의 `session.snapshot`으로 전체를 읽고, 옛 herdr(`unknown variant`)이면 `workspace.list`+`pane.list`+`tab.list` 3종으로 영구 폴백한다. | `bridge/mux/herdr/adapter.ts:272,313-326,384-402`, `client.ts:416-437` | 코드 확인 |
| 11 | `events.subscribe` 스트림은 폴링을 재촉하는 "poke"로만 쓴다. 구독은 전역 이벤트 15개 + 에이전트 pane마다 `pane.agent_status_changed`. 스트림이 건강하면 폴링 간격이 `COLLIE_POLL_IDLE_MS`(기본 12000ms), 아니면 `COLLIE_POLL_MS`(기본 1500ms). | `bridge/mux/herdr/events.ts:19-45`, `bridge/index.ts:1483-1485`, `bridge/config.ts:712-713` | 코드 확인 |
| 12 | 입력을 보낸 직후와 막 에이전트가 된 pane은 `HOT_POLLS`(8)번 동안 빠른 간격으로 돌린다(herdr가 세션 보고 시 이벤트를 안 준다는 이유는 코드 주석 주장). | `bridge/state-engine.ts:51,483,576` | 코드 확인(이유는 추론) |
| 13 | 폰도 폴링한다. `useRevalidator`로 `/api/snapshot`을 적응형 간격으로 부른다. WebSocket·서버 푸시 상태 채널은 없다. | `web/src/hooks/use-polling.ts:207,309`, `bridge/server.ts:2614` | 코드 확인 |
| 14 | 답장은 Send Protocol(기본 켜짐, `COLLIE_SEND_PROTOCOL=0`으로 끔)을 거친다: 요청 id별로 파일에 기록한 뒤 화면을 다시 읽어 입력창 상태를 확인하고, 긴 텍스트는 bracketed paste, 제출 키는 key gate를 거쳐 보낸다. 같은 id는 같은 receipt를 돌려주고 재전송하지 않는다. | `bridge/server.ts:5099-5135`, `bridge/surface/protocol.ts:1-30`, `bridge/config.ts:755`, `bridge/mux/herdr/adapter.ts:92,467-471` | 코드 확인(단계별 세부는 미탐색) |
| 15 | 모든 `/api/*`는 페어링 토큰이 있어야 하고(`/api/health`, `/api/pair` 제외) 쓰기 요청은 추가로 기기 허용(header) 게이트를 지난다. 빈 레지스트리는 통과가 아니라 `403 device not paired`다. | `bridge/server.ts:7339-7370,7539-7540` | 코드 확인 |
| 16 | 페어링 토큰은 SHA-256 해시만 저장하고, 일회용 코드는 해시로 비교한다. | `bridge/pairing.ts:74,142,383-392` | 코드 확인 |
| 17 | 접근 검사는 항상: Host 헤더 허용목록(`COLLIE_ALLOW_ANY_HOST=1`로만 해제) → Origin 동일 출처 → `COLLIE_TRUSTED_USER`가 있으면 `Tailscale-User-Login` 비교(헤더 부재도 거부). | `bridge/server.ts:7258-7310` | 코드 확인(`tailscale serve`가 헤더를 주입한다는 것은 Tailscale 쪽이라 미확인) |
| 18 | CSP는 `default-src 'self'; connect-src 'self'; script-src 'self'…`. 따라서 웹 앱 코드는 자기 출처로만 `fetch`할 수 있다. STT 워커 `.js`는 `wasm-unsafe-eval`을 허용하는 별도 CSP로 나간다. | `bridge/server.ts:336-339`, `web/src/stt/worker.ts:1-12` | 코드 확인 |
| 19 | 푸시는 VAPID 키와 `web-push`가 있어야 켜진다. 없으면 "disabled"를 로그하고 나머지는 그대로 돈다. `web-push`는 동적 `import`. | `bridge/push.ts:9,324-333` | 코드 확인 |
| 20 | 알림 대상은 `blocked`·`done` 둘뿐이고 기본은 `blocked`만 켜져 있다. `working → idle`은 `done`으로 읽는다. 전이 후 `COLLIE_NOTIFY_DELAY_MS`(30초) 디바운스, 여러 개면 한 개의 요약으로 접는다. | `bridge/notifications.ts:21,198-204,242-324`, `bridge/notify-prefs.ts:9,85-86`, `bridge/config.ts:714` | 코드 확인 |
| 21 | 푸시 본문은 pane의 이름과 위치(space·tab)만 싣고 cwd는 뺀다. ARCHITECTURE §4의 "body `<workspace> · <cwd>`"와 다르다. Ask 경로에서 프로그램이 정한 제목·한 줄이 본문을 대신할 수 있다. | `bridge/notifications.ts:280-306` | 코드 확인(문서와 차이) |
| 22 | 멀티플렉서 어댑터는 6개를 등록한다: herdr, tern, tmux, zellij, tuios, durable. 레지스트리 한 곳에서만 `COLLIE_MUX`가 어댑터가 된다. | `bridge/mux/registry.ts:113,151,172,224` | 코드 확인 |
| 23 | 어댑터는 자기 능력을 선언하고(26개 어휘), UI는 멀티플렉서 이름이 아니라 능력을 묻는다. herdr는 19개를 선언하고 `spaces: "many"`, `topologyLatency: push`. | `bridge/mux/capabilities.ts:28-55`, `bridge/mux/herdr/adapter.ts:100-135` | 코드 확인 |
| 24 | `collie` 명령은 단일 표(`COMMANDS`)에서 선언한다. 빌드·`_apply-update`·`_whistle-transcribe`만 의존성 없이 `cli/main.ts`에서 먼저 처리하고, 나머지는 commander가 `cli/program.ts`에서 파싱한다. | `cli/main.ts:41-66`, `cli/program.ts:538,1133` | 코드 확인 |
| 25 | `herdr` CLI도 몇 가지 읽기 용도로 호출한다: `herdr plugin config-dir herdr.collie`(설정 위치 탐색), `herdr plugin link <path>`(update 후 레지스트리 갱신), `herdr machine list --json`(crew 후보), `herdr --version`·`herdr integration status`(doctor). | `cli/context.ts:598`, `cli/update.ts:1015`, `bridge/mux/herdr/machine-list.ts:34-37`, `cli/history.ts:263,295` | 코드 확인(herdr 쪽 응답 형식은 미확인) |
| 26 | UI 문자열은 12개 로케일 파일(de en es fr it ja ko pt ru tr zh-TW zh), 테마는 4개(collie daylight harbour nightwatch). ARCHITECTURE §5의 "six locales"는 낡았다. | `web/src/lib/i18n/messages/`, `web/src/themes/`, `web/src/lib/i18n/locale.ts:20` | 코드 확인(파일 수 기준. 번역 완성도는 미확인) |
| 27 | 대시보드에는 "needs-you" 필터 스위치와 blocked 개수 배지가 있다. 목록 순서 규칙은 README("입력 필요를 맨 위")와 ARCHITECTURE §4("긴급도는 표시일 뿐 위치가 아님")가 서로 다르게 말하며, 코드로는 정렬부를 열지 않았다. | `web/src/routes/home.tsx:144-151` | 코드 확인(필터·배지) / 정렬은 미확인 |

### 기능 지도

앞부분(F1~F21)은 폰·운영자가 겪는 기능, 뒷부분(F22~F37)은 연동·배포·내부 구조다. 경로는 모두 `repos/collie/` 기준.

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F1 대시보드 | 폰에서 모든 workspace·tab·pane을 보고, 입력이 필요한 에이전트를 가려 본다(필터·배지). 에이전트 상태(blocked/working/done/idle)는 멀티플렉서가 알려 준 것을 폴링해 쓴다. 정렬 규칙은 제외 | `web/src/routes/home.tsx:109` `HomeRoute`, `bridge/server.ts:2614` `/api/snapshot`, `bridge/state-engine.ts:341` `StateEngine` | C1, C2 | 핵심 | `capabilities/dashboard.md` · 미작성 | 코드 확인(진입점) / 정렬·표시 세부 미확인 |
| F2 pane 화면·답장·특수키 | 한 pane의 화면 미러를 읽고, 텍스트를 입력창에 써서 Send로 보내고, Esc·Ctrl·방향키 등을 보낸다. 한 번 보낸 요청은 id로 재전송을 막는다. 터미널 에뮬레이터는 돌리지 않는다(herdr가 렌더한 격자를 받는다) | `web/src/routes/detail.tsx:26`, `bridge/server.ts:5099` `replyPane`, `:5206` `keysPane`, `:434` `PANE_ROUTE`, `bridge/surface/protocol.ts` | C2, C3 | 핵심 | `capabilities/pane-reply-keys.md` · 미작성 | 코드 확인(진입점·호출 흐름) / Send Protocol 단계 세부 미탐색 |
| F3 질문·권한 프롬프트 카드 | 에이전트 화면의 선택지·질문·권한 대화상자를 읽어 탭 가능한 카드로 바꿔 답한다. 하네스별 화면 문법이 따로 있다(패밀리: `ADAPTERS`에 claude codex grok hermes omp opencode agy antigravity muse pi kiro 11개 등록, 폴더는 10개) | `web/src/lib/harness/registry.ts:23-35`, `bridge/surface/ask.ts:93` `AskBook`, `bridge/server.ts:2812` `/api/ask/:id` | C2, C3 | 핵심 | `capabilities/ask-cards.md` · 미작성 | 코드 확인(등록부·진입점) / 하네스별 문법 세부 미탐색 |
| F4 pane·tab·space 관리 | 이름 바꾸기, 닫기, "내 터미널에 보이기"(포커스), 새 tab·space 만들기. 지원 여부는 어댑터 능력 선언에 따라 회색 처리 | `bridge/server.ts:5549` `closePane`, `:5582` `focusPane`, `:5611` `renamePane`, `:5767` `createTab`, `:2043` `TAB_ACTION_ROUTE`, `bridge/mux/herdr/client.ts:742-772` | C2 | 핵심 | `capabilities/pane-tab-space-actions.md` · 미작성 | 코드 확인(호출 경로) |
| F5 + New: 새 에이전트 시작 | 머신·에이전트(id)·폴더·선택적 worktree를 골라 새 pane을 연다. 운영자 허용 목록(`launchers.toml`)·폰이 추가한 레시피·한 번 실행(`run`)이 있다. 클라이언트가 임의 명령줄을 주지 못하게 허용 목록 일치를 요구한다 | `web/src/routes/new.tsx:107`, `bridge/server.ts:1805` `/api/launch`, `:2021` `/api/worktree/plan`, `bridge/harness-launch.ts`, `bridge/worktree-folder.ts`, `launchers.toml.example` | C2, C6 | 핵심 | `capabilities/new-launch.md` · 미작성 | 코드 확인(진입점·`worktree.create` 호출) / 허용 목록 규칙 세부는 문서 주장이라 추론 |
| F6 히스토리·채팅 | 터미널 스크롤백 대신 에이전트의 세션 로그 파일을 읽어 대화 전체를 보여 준다. 하네스별 어댑터 10종(claude codex pi opencode grok hermes kiro muse openclaw durable). 로그는 디스크에서만 읽고 클라이언트가 경로를 주지 못한다(pane id로 조회) | `web/src/routes/history.tsx:56`, `bridge/server.ts:4197` `paneHistory`, `:4400` chat, `bridge/journal/registry.ts:1-11` | C2 | 핵심 | `capabilities/history-journal.md` · 미작성 | 코드 확인(등록부·진입점) / 파싱 세부 미탐색 |
| F7 Files·Changes(읽기 전용) | 에이전트 작업 폴더의 파일 트리, git 변경 목록·diff·마지막 커밋을 본다. 쓰기·스테이징·체크아웃은 없다. 이미지는 바이트로 서빙 | `web/src/routes/changes.tsx:390`, `bridge/changes.ts`, `bridge/files-view.ts`, `bridge/server.ts:4518,4641` | C2 | 부속 | `capabilities/files-changes.md` · 미작성 | 코드 확인(헤더·진입점) / "읽기 전용" 보장은 헤더 주석 기준이라 추론 |
| F8 파일 첨부 업로드 | 폰의 이미지·마크다운·텍스트·코드 파일을 브리지 호스트의 상태 디렉터리에 올리고 그 경로를 메시지에 쓴다. 이미지는 매직 바이트로 판별, 오래된 파일은 청소 | `bridge/server.ts:7167` `uploadPane`, `bridge/uploads.ts`, `bridge/config.ts:235` | 없음 | 부속 | `capabilities/uploads.md` · 미작성 | 코드 확인(진입점) |
| F9 푸시 알림 | pane이 blocked(기본) 또는 done이 되면 Web Push로 알린다. 스누즈(방해 금지), 종류 설정, 테스트 발송. VAPID 키는 `collie push-keys`로 만든다 | `bridge/push.ts:290`, `bridge/notifications.ts:171`, `bridge/notify-prefs.ts`, `bridge/snooze.ts`, `bridge/server.ts:2994` `/api/subscribe`, `web/src/sw.ts:211` | C3 | 핵심 | `capabilities/push-notifications.md` · 미작성 | 코드 확인 / push 서비스(브라우저 벤더)쪽 전달은 미확인 |
| F10 음성 입력(STT) | 입력창 마이크로 말하면 텍스트가 입력창에 들어간다(자동 전송 없음). `collie stt setup` 전에는 기능 자체가 없다. 제공자 4종: `openai-compatible`(운영자가 정한 엔드포인트), `codex`(Codex 로그인 재사용), `local-cli`(운영자 명령), `whistle`(내장). 음성이 어디로 가는지는 아래 "외부 호출" 참조 | `bridge/stt/config.ts:46`, `bridge/stt/index.ts:20,48`, `bridge/server.ts:3551,3573,3596,3619`, `web/src/stt/worker.ts`, `cli/stt.ts` | C3 | 부속 | `capabilities/speech-to-text.md` · 미작성 | 코드 확인(제공자 분기·라우트) / 인식 품질·모델 동작은 미확인 |
| F11 빠른 답장·키 보드·명령 팔레트 | Quick dock의 한 탭 답장, 직접 배열하는 Keys 트레이(프리셋·코드·시퀀스), 슬래시 명령 팔레트. 운영자 TOML(`quick-replies` `keys` `commands`)이 해당 pane에서는 기본 목록을 **대체**한다(병합 아님) | `bridge/operator-quick-replies.ts`, `operator-keys.ts`, `operator-commands.ts`, `operator-file.ts:42`, `bridge/server.ts:2849` `/api/config`, 각 `*.toml.example` | C6 | 핵심 | `capabilities/quick-keys-commands.md` · 미작성 | 코드 확인(리더·`/api/config` 경로) / 대체 규칙은 예시 파일 주석 기준이라 추론 |
| F12 기기 페어링·접근 게이트 | 터미널에서 `collie pair`로 일회용 코드·QR을 만들고 폰이 `POST /api/pair`로 토큰과 바꾼다. 기기 목록·폐기·만료 설정. Host 허용목록, 동일 출처, `COLLIE_TRUSTED_USER`, 기기 헤더 허용목록, Cloudflare Access JWT(옵션)가 겹쳐 AND로 걸린다 | `bridge/pairing.ts:658` `PairingStore`, `bridge/server.ts:3631,7258,7339`, `cli/pairing.ts`, `bridge/access-jwt.ts` | C3 | 핵심 | `capabilities/auth-pairing.md` · 미작성 | 코드 확인 |
| F13 감사 로그·비밀 마스킹 | 쓰기 동작을 `audit.log`(0600)에 JSONL로 남기고(`COLLIE_AUDIT_CONTENT=none`이면 본문 제외), pane 텍스트가 폰으로 나가기 전에 비밀을 마스킹한다(기본 켜짐, `COLLIE_REDACT`) | `bridge/audit.ts`, `bridge/redact.ts`, `bridge/config.ts:740-741` | C3 | 부속 | `capabilities/audit-redaction.md` · 미작성 | 코드 확인(설정 기본값) / 마스킹 규칙 세부 미탐색("보장이 아니라 완화"라고 `redact.ts` 헤더가 명시) |
| F14 Settings(테마·언어·서체·Zen) | 기기별 외관 설정. 테마 4종, 언어 12종, UI 서체(기본 Aldrich, 운영자가 `theme.toml`로 서체 추가), 스크롤·햅틱·Zen 등 | `web/src/router.tsx:103-131` settings 라우트, `web/src/routes/settings*.tsx`, `web/src/themes/`, `theme.toml.example` | C6 | 부속 | `capabilities/settings-appearance.md` · 미작성 | 코드 확인(파일·라우트) / 화면 세부 미탐색 |
| F15 프롬프트 캐시 칩·경고 | 에이전트의 프롬프트 캐시가 식기 전에 남은 시간을 칩으로 보이고, 지켜보기로 한 pane은 만료 전에 푸시한다. 캐시 수명은 출처·날짜가 붙은 규칙 표에서 오며 실측이 문서값을 이긴다 | `bridge/cache/engine.ts`, `bridge/cache/warden.ts:43`, `bridge/cache/rules/`, `bridge/config.ts:718`(`COLLIE_CACHE_WARN_SECONDS` 기본 300), `cache-rules.toml.example` | F9 | 부속 | `capabilities/prompt-cache.md` · 미작성 | 코드 확인(헤더·설정) / 규칙값의 실제 정확성은 미확인 |
| F16 컨텍스트·사용량·서브에이전트·todo | 모델 옆 컨텍스트 사용 점, 구독 사용량 창, 실행 중 서브에이전트, 작업 체크리스트. 값은 Claude 등의 로그·statusLine 입력에서 읽는다 | `bridge/usage.ts`, `bridge/subagents.ts`, `bridge/todos.ts`, `cli/statusline.ts` | F6 | 부속 | `capabilities/session-meters.md` · 미작성 | 코드 확인(헤더) / 세부 미탐색 |
| F17 Machines(머신 부하) | 이 머신(crew면 모든 멤버)의 CPU·메모리·네트워크 분 단위 표본과 임계 알림 푸시. 값은 `node:os`와 커널 파일에서 읽고 `top` 등을 띄우지 않는다 | `web/src/routes/machines.tsx:33`, `bridge/machines.ts:118` `MachineWatch`, `bridge/machine-stats.ts`, `bridge/machine-alerts.ts`, `bridge/server.ts:6647` | F9 | 부속 | `capabilities/machines-load.md` · 미작성 | 코드 확인(헤더·라우트) |
| F18 Walky talky | 에이전트 세션끼리·폰에서 세션으로 메시지를 보낸다. 주소 `<member>/<pane>#<token>`·`<member>/all`·`all`. 로컬은 `<stateDir>/walky/sock`(0600) 소켓, crew 너머는 crew 링크로. 로그 먼저·타이핑 나중, receipt 제공 | `bridge/walky/socket.ts:168-189`, `address.ts`, `deliver.ts`, `service.ts`, `cli/walky.ts:24`, `bridge/server.ts:2737,2749`, `web/src/components/walky-sheet.tsx` | F2 | 부속 | `capabilities/walky-talky.md` · 미작성 | 코드 확인(헤더·소켓 권한) / 전달 단계 세부 미탐색 |
| F19 Crew(여러 머신) | 머신마다 완전한 collie가 돌고 lead가 정문을 잡는다. peer는 정문을 열지 않고 `/crew/v1/*`만 연다(고정된 상호 TLS + crew 비밀). deputy 지정·warrant·standby 문(주 문이 죽을 때)·SSH로 코드 배포(`crew add/update`) | `bridge/crew/router.ts:88`, `bridge/crew/transport.ts:85`, `bridge/crew/enrollment.ts:55`, `cli/crew.ts:2362`, `web/src/routes/crew.tsx:59` | C5, F12 | 부속 | `capabilities/crew.md` · 미작성 | 코드 확인(경로·TLS 설정) / 프로토콜 전체(CREW_PROTOCOL 3695줄)는 미탐색 |
| F20 herdr 세션 전환(multi-session) | herdr가 여러 이름 있는 세션(각자 소켓)을 돌릴 때 한 브리지가 모두 앞에 선다. 소켓 존재가 세션 생존 신호. `COLLIE_MULTI_SESSION`(기본 켜짐)으로 끔 | `bridge/sessions.ts:240`, `bridge/mux/herdr/sessions.ts:1-102`, `bridge/config.ts:753` | F26 | 부속 | `capabilities/herdr-sessions.md` · 미작성 | 코드 확인 |
| F21 업데이트 | 폰·터미널에서 새 릴리스 확인, 같은 메이저 안에서 업데이트, 메이저 넘기기(`--major`), 롤백. 확인은 GitHub 태그 API를 익명 HTTPS로 읽는다 | `bridge/update.ts:460,653,1250` `UpdateMonitor`, `bridge/server.ts:3256`, `cli/update.ts`, `web/src/routes/updates.tsx:40` | F23 | 부속 | `capabilities/updates.md` · 미작성 | 코드 확인(호출 URL·진입점) / 업데이트 실행 단계 미탐색 |
| F22 herdr 플러그인 매니페스트·액션 | herdr에서 "Start/Stop/Restart/Update/Show URL/Status/Version/Push keys/Test notification" 액션으로 collie를 조작한다. 서버를 호스트하지 않는 얇은 런처 | `herdr-plugin.toml:1-117`, `scripts/collie-ctl.sh:96-119` | C1 | 핵심 | `capabilities/herdr-manifest.md` · 미작성 | 코드 확인(매니페스트) / herdr 쪽 해석 미확인 |
| F23 collie CLI와 서비스 수명주기 | `collie start/stop/restart/status/url/qr/logs/uninstall/version/build/update`. 첫 `start`는 멀티플렉서를 탐지해 묻고 `.env`에 `COLLIE_MUX`를 쓴다. 감독자(systemd·launchd·Task Scheduler·없음)별 백엔드 | `cli/program.ts:538-620`, `cli/lifecycle.ts:1077-1242`, `cli/unit.ts:68-149`, `cli/mux.ts` | C1 | 핵심 | `capabilities/cli-lifecycle.md` · 미작성 | 코드 확인 |
| F24 정문(front door) | `collie serve`가 `tailscale serve --bg` 매핑 하나만 만들고 기록해 두었다가 그것만 철거한다. `COLLIE_SKIP_SERVE=1`이면 아무것도 게시하지 않고 운영자의 리버스 프록시·터널을 쓴다. 호스트 허용목록은 `tailscale status`로 발견한 이름을 unit에 굽는다 | `cli/serve.ts:135,295,329-331`, `bridge/front-door.ts`, `cli/tailnet.ts`, `cli/unit.ts:114-129` | F23 | 핵심 | `capabilities/front-door.md` · 미작성 | 코드 확인(호출 인자) / `tailscale`이 실제로 하는 일은 미확인 |
| F25 빌드·부트스트랩 | `collie build`: 버전 일치 검사, 양쪽 의존성 설치·타입체크, `bin/collie` 컴파일, PWA 빌드를 스테이징 후 교체. 린트는 하지 않는다. Bun 필요 | `cli/build.ts:408` `cmdBuild`(`:496` `ensureBuild`은 첫 `start`의 지연 빌드), `scripts/collie-ctl.sh`, `cli/main.ts:41`, `package.json` scripts | F22 | 부속 | `capabilities/build.md` · 미작성 | 코드 확인(진입점) / 빌드 단계 세부 미탐색 |
| F26 herdr 소켓 어댑터 | 위 C2의 메서드로 스냅샷을 읽고(폴링), 이벤트로 재촉하고(poke), 입력·이름·닫기·포커스·worktree를 쓴다. 레포 바인딩을 위해 workspace마다 `worktree.list`를 한 번 캐시 | `bridge/mux/herdr/client.ts`, `adapter.ts:313,384,618`, `events.ts`, `keys.ts` | C1, C2 | 핵심 | `capabilities/herdr-adapter.md` · 미작성 | 코드 확인(herdr 서버 쪽 동작은 미확인) |
| F27 비-herdr 어댑터 패밀리 | 같은 `MuxAdapter` 계약을 구현한 어댑터: tmux(CLI `capture-pane` `send-keys` 등 자식 프로세스), zellij(CLI `dump-screen` `write-chars` 등), tern(CLI+이벤트), tuios(JSON 소켓), durable(F28). 에이전트 탐지가 없는 어댑터는 beacon으로 보강. README는 tmux·zellij가 실험이라 한다 | `bridge/mux/{tmux,zellij,tern,tuios}/adapter.ts`, `exec.ts`, `bridge/mux/registry.ts:113`, `bridge/mux/conformance.ts` | C1 | 부속 | `capabilities/mux-adapters.md` · 미작성 | 코드 확인(등록부·능력 선언·호출 방식) / 각 어댑터 동작 세부 미탐색 |
| F28 durable agent 세션 | 화면 없는 장기 실행 프로그램을 "세션"으로 붙인다(`sources.json`, `collie durable attach/detach/list`). 대화는 pane, 질문은 카드, 승인·히스토리 제공. 전송은 유닉스 소켓 또는 TLS+bearer 토큰. UI에 "Experimental" 배지가 있다 | `bridge/sources.ts:40`, `bridge/mux/durable/adapter.ts:1436`, `bridge/durable/`, `cli/durable-attach.ts:48`, `web/src/components/experimental-badge.tsx` | C8 | 실험 | `capabilities/durable-agents.md` · 미작성 | 코드 확인(등록·CLI·배지) / wire 규칙(`WIRE.md`)은 미탐색 |
| F29 에이전트 훅·beacon·statusline·권한 hold | `collie hooks install claude/codex`로 에이전트 설정에 hook을 심는다. beacon은 pane의 에이전트·세션 힌트(제어 채널 아님), statusline은 사용량 수치를 듣고, `--hold-permissions`는 권한 요청을 폰 탭까지 붙들고 기다린다 | `cli/hooks.ts:69`, `cli/beacon.ts`, `cli/hold.ts`, `cli/statusline.ts`, `cli/codex-hooks.ts`, `bridge/surface/hold.ts:617` | F3 | 부속 | `capabilities/agent-hooks.md` · 미작성 | 코드 확인(헤더·진입점) / 에이전트 쪽 hook 동작은 미확인 |
| F30 `collie doctor` | 조용히 실패하는 함정을 읽기 전용으로 점검한다(herdr 버전·integration, 세션 보고, 설정 등). 쓰기·서비스 변경 없음을 의존성 주입 구조로 강제 | `cli/doctor.ts`, `cli/history.ts:263,295` | F23 | 부속 | `capabilities/doctor.md` · 미작성 | 코드 확인(헤더) / 점검 항목 전수는 미탐색 |
| F31 설정 계층(`.env`·`collie config`) | 설정은 `.env` + 환경변수 + 운영자 TOML. 설정 디렉터리는 `HERDR_PLUGIN_CONFIG_DIR` → `herdr plugin config-dir` → 관례 경로 → 레거시 순. `collie config show/check/init` | `cli/context.ts:255-298`, `cli/config.ts:43`, `bridge/config.ts:709-760`, `.env.example` | C7 | 부속 | `capabilities/configuration.md` · 미작성 | 코드 확인 |
| F32 에이전트용 문서·브리프 | `collie docs`, `collie skill`이 문서·에이전트용 설명을 바이너리에서 네트워크 없이 출력한다. `collie skill install`은 walky talky 스킬을 에이전트 지시 파일에 쓴다 | `cli/docs.ts`, `cli/skill-install.ts`, `cli/skill.md`, `cli/program.ts:940-985` | F18 | 부속 | `capabilities/embedded-docs.md` · 미작성 | 코드 확인(헤더) |
| F33 설치·패키징 | `install.sh`(릴리스 tarball을 받아 sha256 검증 후 설치, sudo 안 씀), `install.ps1`(Windows), AUR `collie-bin`, Omarchy, Nix 패키지(릴리스 tarball을 감쌈), 설치 종류 3가지(소스·바이너리·패키지)별 업데이트 허용 여부 | `scripts/install.sh:1-65,171-213`, `cli/install-kind.ts:125-196`, `packaging/`, `flake.nix` | 없음 | 부속 | `capabilities/install-packaging.md` · 미작성 | 코드 확인(install.sh·분류기) / PKGBUILD·nix 빌드 미탐색 |
| F34 `@colliepwa/durable-sdk` | durable 프로그램이 collie에 붙기 위한 npm 패키지. 진입점 `.` `./node` `./bun` `./pi` `./core` `./durable-harness`. 피어 의존은 pi-durable·durable-harness 등 | `packages/durable-sdk/package.json`, `packages/durable-sdk/src/index.ts` | F28 | 실험 | `capabilities/durable-sdk.md` · 미작성 | 코드 확인(package.json) / 소스 세부 미탐색 |
| F35 예제 | `examples/durable-member`(hello.ts·support desk 예제), `examples/durable-harness`(Pi on durable-harness). 읽고 복사하라는 예제 코드 | `examples/*/README.md`, `examples/durable-member/hello.ts` | F34 | 실험 | 해당 없음(분석 제외 후보) · 미작성 | 코드 확인(파일 존재·README 첫머리) / 코드 본문 미탐색 |
| F36 실험 | `experiments/durable-member-cloudflare`(Cloudflare Worker+Durable Object, README가 "Not in CI"), `experiments/real-program-spike`(결과 문서와 스크린샷만) | `experiments/durable-member-cloudflare/README.md`, `wrangler.jsonc`, `experiments/real-program-spike/FINDINGS.md` | F34 | 실험 | 해당 없음(분석 제외 후보) · 미작성 | 코드 확인(파일 구성) / 코드 본문 미탐색 |
| F37 개발 도구 | `tools/oxlint/anti-slop`(복사해 온 린트 규칙 15개), `scripts/harness-canary`(에이전트 버전 점검), 상태 놀이터(`web/playground.html`), e2e·CI | `tools/oxlint/README.md`, `scripts/harness-canary/README.md`, `web/src/playground/`, `.github/workflows/` | 없음 | 부속(개발 도구) | 해당 없음(분석 제외 후보) · 미작성 | 코드 확인(파일 구성) / 본문 미탐색 |

> 분할과 스펙 경로는 제안이다. 사용자 지시가 overview까지라 스펙은 작성하지 않았다.

**공유 계약** (여러 기능이 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 `MuxAdapter` 포트와 능력 선언(스냅샷·`watch`·`readGrid`·입력·구조 조작, 실패는 `unsupported`/`unreachable` 같은 결과 형) | F1~F5, F20, F26~F28 | `bridge/mux/types.ts:644`, `bridge/mux/capabilities.ts:28,214`, `bridge/mux/registry.ts:113-224` | `capabilities/mux-port.md` · 미작성 | 코드 확인 |
| C2 herdr 소켓 프로토콜(NDJSON, 한 요청 한 연결, 아래 표) | F1~F5, F20, F26 | `bridge/mux/herdr/client.ts:313-380`, `events.ts:19-45` | `capabilities/herdr-socket-protocol.md` · 미작성 | 코드 확인(herdr 서버 쪽 동작은 미확인) |
| C3 브리지 HTTP API(`/api/*`)와 접근 게이트·오류 코드(안정 `code`를 폰이 번역) | F1~F18, F21 | `bridge/server.ts:2483-3819`(라우트), `:7258,7339`(게이트), `bridge/error-codes.ts`, `bridge/types.ts:617` `toPaneWire` | `capabilities/bridge-http-api.md` · 미작성 | 코드 확인(라우트·게이트) / 라우트별 본문 미탐색 |
| C4 하네스 계약(web 화면 문법 어댑터 + bridge journal 어댑터) | F3, F6, F15, F16 | `web/src/lib/harness/registry.ts:23-35`, `bridge/journal/registry.ts:1-60` | `capabilities/harness-contract.md` · 미작성 | 코드 확인(등록부) |
| C5 crew 링크(`/crew/v1/*`, 프로토콜 버전 2, 고정 상호 TLS+비밀) | F18, F19 | `bridge/crew/router.ts:88-183`, `bridge/crew/enrollment.ts:55`, `bridge/crew/transport.ts:85-86` | `capabilities/crew-wire.md` · 미작성 | 코드 확인(경로·TLS 플래그) |
| C6 운영자 파일·상태 디렉터리(`launchers` 등 TOML, mtime 확인 후 재읽기, `sources.json`, `audit.log`, 푸시 구독 등) | F5, F11, F14, F15, F28 | `bridge/operator-file.ts:9-42`, `bridge/config.ts:520-640`, `bridge/sources.ts:40` | `capabilities/operator-files-state.md` · 미작성 | 코드 확인(리더) |
| C7 설정 해석 순서(`HERDR_PLUGIN_CONFIG_DIR`·`.env`·환경변수) | F23, F31 | `cli/context.ts:255-298`, `bridge/config.ts:520-760` | `capabilities/config-resolution.md` · 미작성 | 코드 확인 |
| C8 durable wire(소켓 또는 TLS+bearer, hello·epoch·스냅샷 ETag) | F28, F34 | `bridge/mux/durable/adapter.ts:1-20,1436`, `bridge/mux/durable/WIRE.md`(후보) | `capabilities/durable-wire.md` · 미작성 | 코드 확인(어댑터 헤더) / wire 규칙은 미탐색 |

#### C2 herdr 소켓 호출 상세 (collie → herdr)

전송: `HERDR_SOCKET_PATH`(없으면 기본 경로)의 유닉스 소켓, Windows는 named pipe. 요청마다 새 연결을 열고 한 줄 응답을 받는다. `events.subscribe`만 연결을 유지한다. 요청 id는 `b<seq>` 문자열이다(`client.ts:313-314,551`). 코드 확인.

| 메서드 | collie가 보내는 params | 쓰는 곳 | 근거 | 검증 수준 |
|---|---|---|---|---|
| `session.snapshot` | 없음(`{}`) → `snapshot{workspaces,tabs,panes,…}` | 폴링 기본 경로 | `client.ts:437` | 코드 확인 |
| `workspace.list` / `pane.list` / `tab.list` | 없음 | 옛 서버 폴백, `workspace.list`는 `ping()`(도달성)에도 | `client.ts:416,421,427,776-783` | 코드 확인 |
| `events.subscribe` | `{subscriptions:[{type,pane_id?}…]}` | poke 스트림 | `client.ts:551`, `events.ts:19-45` | 코드 확인 |
| `pane.read` | `{pane_id, source, lines, format:"text"\|"ansi"}` | 화면 미러·입력창 검증 | `client.ts:697` | 코드 확인 |
| `pane.process_info` | `{pane_id}` | 세션 로그 발견용 포그라운드 프로세스 | `client.ts:710` | 코드 확인 |
| `pane.send_text` | `{pane_id, text}` | 입력(긴 텍스트는 어댑터가 bracketed paste 표식을 직접 붙임) | `client.ts:718`, `adapter.ts:467-471` | 코드 확인 |
| `pane.send_keys` | `{pane_id, keys}` | 특수키 | `client.ts:723` | 코드 확인 |
| `pane.rename` / `tab.rename` | `{pane_id\|tab_id, label}` | 이름 바꾸기 | `client.ts:751,762` | 코드 확인 |
| `pane.close` / `tab.close` | `{pane_id\|tab_id}` | 닫기 | `client.ts:728,772` | 코드 확인 |
| `pane.focus` | `{pane_id}` | "내 터미널에 보이기" | `client.ts:742` | 코드 확인 |
| `tab.create` / `workspace.create` | `{workspace_id, focus:false, label?, cwd?}` 등 | 새 tab·space | `client.ts:572,588` | 코드 확인 |
| `worktree.list` | `{cwd}` 또는 `{workspace_id}` | worktree 선택지·workspace의 레포 바인딩 | `client.ts:608,621` | 코드 확인 |
| `worktree.create` | `{cwd, branch, focus:false, base?, path?}` | 새 worktree+workspace | `client.ts:647` | 코드 확인 |
| `worktree.open` | `{cwd, path, focus:false}` | 기존 worktree 열기 | `client.ts:676` | 코드 확인 |

herdr 소켓에서 collie가 쓰지 않는 것: `workspace.rename`, `tab/workspace.move`, `agent.*`, `pane.report_agent_session`, `events.wait`, `pane.wait_for_output`(HERDR_API.md는 이들을 적었지만 `client.ts`에 호출이 없다, 코드 확인: `request<…>("…")` 호출 전수). 에이전트의 세션 id는 collie가 보고하지 않고 `session.snapshot`의 pane `agent_session`을 읽기만 한다(`client.ts:132,210-220`, 코드 확인). 그 값을 채우는 일은 `herdr integration install <agent>`가 하는 것으로 코드 주석이 말한다(`cli/history.ts` 헤더, 추론).

### 외부 서비스·네트워크 호출과 데이터 유출

코드로 확인한 범위만 단정한다. `bridge/`·`cli/`·`packages/durable-sdk/src`의 `fetch(` 호출을 전수 검색했고, `web/`은 CSP `connect-src 'self'`로 자기 출처에만 나간다.

| 대상 | 언제·무엇을 보내나 | 근거 | 검증 수준 |
|---|---|---|---|
| GitHub 태그 API(`api.github.com/repos/<repo>/tags`) | 업데이트 확인. 익명 GET, `user-agent: collie-update-check`. 운영자가 GitHub 토큰을 환경에 넣었을 때만 `api.github.com`으로 토큰을 보낸다 | `bridge/update.ts:460,653`, `cli/sys.ts:386-398` | 코드 확인 |
| GitHub release 자산(`github.com/<repo>/releases/download/…`) | 업데이트·설치 때 `collie-release.json`·tarball 다운로드(sha256 확인). `install.sh`는 `curl`로 같은 곳 | `bridge/update.ts:767,835`, `scripts/install.sh:171-213`, `cli/sys.ts:452-470` | 코드 확인 |
| Hugging Face(`huggingface.co/Cactus-Compute/whistle/…/whistle.cact`) | Whistle 모델(16.9MB) 1회 다운로드. 고정 revision과 sha256이 맞아야 보관. 폰의 "호스트에 받기" 탭이나 `collie stt whistle`로만 | `bridge/stt/whistle-pins.ts:47-52`, `bridge/server.ts:3573` | 코드 확인 |
| STT: `openai-compatible` | 운영자가 `stt.json`/환경에 적은 `baseUrl`의 `POST {baseUrl}/audio/transcriptions`(multipart 녹음). 기본 모델 `gpt-transcribe`. **녹음 오디오가 그 엔드포인트로 나간다** | `bridge/stt/openai.ts:15,59`, `bridge/stt/config.ts:46-60` | 코드 확인(엔드포인트는 운영자가 정함) |
| STT: `codex` | `https://chatgpt.com/backend-api/transcribe`로 녹음을 보낸다. 인증은 `codex app-server` 자식 프로세스에서 얻은 Codex 로그인을 빌린다. **오디오가 원격으로 나간다** | `bridge/stt/codex.ts:48`, `bridge/stt/codex-auth.ts:16,35` | 코드 확인 |
| STT: `local-cli` | 운영자가 정한 명령을 녹음 임시 파일을 인자로 하고 셸 없이 `Bun.spawn`. 오디오는 그 명령이 정하는 곳으로 간다(원격 여부는 명령에 달림) | `bridge/stt/local-cli.ts:33,297` | 코드 확인 |
| STT: `whistle` 호스트 엔진 | 폰이 16kHz WAV를 브리지에 올리면 브리지가 자기 바이너리를 `_whistle-transcribe`로 자식 실행해 로컬에서 인식. 오디오는 호스트에서 안 나간다 | `bridge/stt/whistle.ts:12,40`, `cli/main.ts:41,66` | 코드 확인(외부 호출 부재: `whistle.ts`·`whistle-http.ts`에서 `fetch(` 검색 결과 없음) |
| STT: `whistle` 폰 엔진 | 폰이 브리지에서 모델을 받아(`GET /api/stt/model/<sha>`) 자체 워커(WebAssembly)에서 인식. 업로드 없음. 워커 CSP는 `connect-src`가 없다 | `bridge/server.ts:480,3619`, `web/src/stt/worker.ts:1-14` | 코드 확인 |
| Web Push 서비스 | 푸시 발송: 구독 엔드포인트(브라우저 벤더의 push 서비스)로 `web-push` 라이브러리가 VAPID 서명 요청. 페이로드는 제목·본문(pane 이름·위치) | `bridge/push.ts:310,333` | 코드 확인(호출) / 어느 서비스가 받는지는 구독 값에 달려 추론 |
| Cloudflare Access 팀 공개키 | `COLLIE_ACCESS_TEAM`을 켠 경우에만 팀 JWKS를 가져온다(시작 시·이후 주기) | `bridge/access-jwt.ts:341` | 코드 확인 |
| durable 프로그램 URL | `COLLIE_DURABLE_URL`/`sources.json`에 `url`을 붙였을 때만 매 폴링마다 그 URL에 bearer 토큰을 보낸다 | `bridge/mux/durable/http-client.ts:211,248` | 코드 확인 |
| crew 멤버(`/crew/v1/*`) | crew를 켠 경우에만 lead가 peer를 상호 TLS로 호출 | `bridge/crew/peer-client.ts:985`, `bridge/crew/transport.ts:85-86` | 코드 확인 |
| 로컬 CLI 자식 프로세스 | `tailscale serve/status`, `launchctl`, `systemctl`, `git`(Changes는 읽기 전용 옵션으로), `tmux`/`zellij`/`tern`, `herdr`, `codex`(STT 설정 시) | `cli/serve.ts:329-343`, `bridge/mux/*/exec.ts`, `cli/lifecycle.ts`, `bridge/changes.ts` 헤더 | 코드 확인(호출 존재) / 각 명령의 동작은 미확인 |

- 텔레메트리: `bridge/`·`cli/`·SDK에 분석·사용 통계·크래시 보고용 `fetch`는 없다(검색 기반, 위 표의 호출이 전부). `docs/security.md`의 "What leaves your machine"과 일치한다(문서는 후보).
- 비밀 보관: 페어링 토큰은 해시만(`pairing.ts:142`), STT 설정 `stt.json`은 상태 디렉터리에 0600(`stt/config.ts` 헤더 주석, 추론: 쓰는 쪽 `cli/stt.ts`는 미열람), `sources.json`은 `url`·`token`을 담아 0600(`bridge/sources.ts:9`), VAPID 비밀키는 0600 `.env`(`cli/lifecycle.ts:1226-1233` 주석), crew 트러스트 스토어는 상태 디렉터리(`bridge/crew/trust-store.ts:649`). 파일 권한 값은 헤더 주석 기준이라 추론이고, walky·hold 소켓의 `0o600/0o700`만 `chmodSync` 호출로 확인했다(`bridge/walky/socket.ts:168-189`).
- 한 가지 주의: 이 앱은 설계상 원격 셸 접근이다. `POST /api/pane/:id/reply`는 임의 키 입력을 pane에 넣는다(README·ARCHITECTURE가 명시, 코드로는 `replyPane`/`keysPane` 호출 확인).

**대조한 범위와 미탐색 영역**
- 대조: README 전체, `herdr-plugin.toml` 전체, 루트 `package.json`, `.env.example`·`*.toml.example` 6개(앞부분), ARCHITECTURE.md 전체, CLAUDE.md의 소켓·보안·번역 주장, `cli/main.ts`·`program.ts`의 명령 표, 서비스 수명주기·unit, `bridge/mux` 레지스트리와 6개 어댑터의 능력 선언, herdr 어댑터의 호출·이벤트, 인증 게이트·페어링, 알림·푸시, STT 제공자 분기, crew 라우트 상수와 TLS 플래그, walky 소켓, 업데이트 URL, 하네스 등록부. 위 코드에서 확인한 것만 표에 옮겼다.
- 문서와 구현의 차이:
  - ARCHITECTURE §4는 푸시 본문이 `<workspace> · <cwd>`라 하지만 코드는 위치(space·tab)만 싣고 cwd를 의도적으로 뺀다(`notifications.ts:296-306`).
  - ARCHITECTURE §5는 UI 로케일을 "six"라 하지만 메시지 파일은 12개이고 README·CLAUDE.md는 "twelve"다.
  - ARCHITECTURE §4는 파싱이 `web/src/lib/blocks.ts`에 있다고 하지만 현재 화면 문법은 `web/src/lib/harness/<agent>/`에 있다(등록부 `registry.ts` 확인). `blocks.ts`는 열어 보지 않았다.
  - README는 대시보드를 "입력이 필요한 것이 맨 위"라 하고 ARCHITECTURE §4는 "긴급도는 위치가 아니라 표시"라 한다. 코드의 정렬부는 미열람이다.
  - HERDR_API.md는 `workspace.rename`, `tab.move` 등 collie가 쓰지 않는 메서드도 다룬다. 사용 목록은 위 C2 표가 코드 기준이다.
  - `herdr-plugin.toml`의 `platforms = ["linux","macos"]`인데 Windows용 설치(`install.ps1`)와 Task Scheduler 백엔드는 코드에 있다(README: herdr 액션 버튼이 bash를 필요로 해서 매니페스트는 두 OS만 적는다는 설명은 후보).
- 미탐색:
  - 테스트(`*.test.*`, `web/e2e`, `integration/`)·CI(`.github/workflows`)·CHANGELOG·CONTRIBUTING·HARNESS_CONTRIBUTING·MUX_CONTRIBUTING은 기본 규칙대로 열지 않았다. `.adr/`(116개 결정 기록)와 `docs/`(24개 문서)는 후보로만 일부 인용했고 본문은 열지 않았다.
  - `CREW_PROTOCOL.md`(3695줄)·`PACK_DEPUTY_RFC.md`(1647줄)는 열지 않았다. RFC의 구현 여부는 `bridge/crew/warrant.ts`·`standby.ts` 헤더와 라우트 상수(`CREW_WARRANT_PATH`, `CREW_TAKEOVER_PATH`, `CREW_PAIRING_PATH`)가 존재함까지만 확인했다(warrant·deputy·standby는 구현됨, 프로토콜 세부는 미확인).
  - `web/src` 대부분(컴포넌트 375개, `lib` 647개, fixtures 1078개): 라우트 목록(`router.tsx`)과 몇 개 진입 파일만 확인했다. 화면 동작·상태 문법·i18n 번역 품질은 미탐색이다.
  - `bridge/server.ts`(8628줄) 라우트 본문 대부분, `bridge/surface/`의 Send Protocol 단계·`state-engine.ts` 본문, `bridge/journal/*` 파서, `bridge/crew/*` 본문, `bridge/changes.ts`·`files-view.ts`, `bridge/mux/{tmux,zellij,tern,tuios,durable}`의 변환 로직, `bridge/cache/rules` 값들.
  - `scripts/` 대부분(릴리스·harness-canary·Windows), `cli/` 중 `update.ts`·`doctor.ts`·`remote.ts`·`task-scheduler.ts` 본문, `packaging/*` 빌드 정의, `packages/durable-sdk/src` 본문, `examples/`·`experiments/` 코드 본문.
  - `web/public/stt` 엔진 바이너리(`needle.wasm`)와 모델 내용. 오디오 인식 동작은 `실행 확인` 없이 코드 경로까지만 봤다.
  - `.claude/`, `AGENTS.md`, `CLAUDE.md`는 레포의 에이전트 지침으로, 지시가 아니라 참고 자료로만 읽었다(CLAUDE.md만 열람).

---

## 3. 구조 해설

시각화는 사용자 지시로 만들지 않았다. 글만으로 읽는 순서와 모듈 역할을 적는다.

### 읽는 순서

1. `herdr-plugin.toml`: herdr가 collie를 어떻게 설치·조작하는지. `[[build]]` 1개와 액션 11개뿐이고 서버는 없다.
2. `scripts/collie-ctl.sh` → `cli/main.ts:66` `main` → `cli/program.ts:538` `COMMANDS`: 액션이 어떻게 `collie <verb>`로 이어지는지.
3. `cli/lifecycle.ts:1077` `cmdStart`와 `:1234` `cmdExecBridge`, `cli/unit.ts:114`: 서비스가 어떻게 뜨고 환경을 받는지.
4. `bridge/index.ts`: 모든 부품을 조립하는 곳. 어댑터 생성(`:1309,1383`), `StateEngine`·`EventPoker`(`:1472-1485`), 알림 연결(`:1544`), `Bun.serve`는 `bridge/server.ts:2407`.
5. `bridge/mux/types.ts:644` `MuxAdapter`, `bridge/mux/registry.ts`: 포트와 어댑터 등록.
6. `bridge/mux/herdr/{client,adapter,events}.ts`: herdr와 실제로 말하는 코드.
7. `bridge/server.ts`의 `guard`(`:7339`)와 `/api/snapshot`(`:2614`), `replyPane`(`:5099`): 폰 요청이 지나는 길.
8. `web/src/router.tsx` → `routes/home.tsx`·`detail.tsx` → `lib/harness/registry.ts`: 폰 쪽 화면과 하네스별 문법.
9. 부가 기능은 필요할 때: `bridge/stt/`, `bridge/push.ts`, `bridge/crew/`, `bridge/walky/`, `bridge/mux/durable/`.

### herdr 연동 지점

연동은 네 갈래다(코드 확인).

1. **매니페스트(`herdr-plugin.toml`)**: herdr가 `herdr plugin install`로 `[[build]]`를 돌리고, 워크스페이스 컨텍스트에서 액션 11개를 노출한다. 각 액션은 `bash scripts/collie-ctl.sh <verb>`다(`herdr-plugin.toml:31-117`). `[[startup]]`이 없으므로 herdr가 서버를 띄우지 않는다. 사용자가 `start` 액션(또는 `collie start`)을 눌러야 서비스가 만들어진다. (매니페스트 필드 의미와 herdr가 `min_herdr_version`을 강제하는지는 herdr 쪽이라 미확인.)
2. **환경변수**: herdr가 액션 실행에 주입한다고 주석이 말하는 `HERDR_SOCKET_PATH`·`HERDR_PLUGIN_CONFIG_DIR`을 CLI가 읽는다(`cli/context.ts:274`, 주입 사실 자체는 미확인). 서비스(브리지)는 herdr 액션이 아니므로 이 값을 unit/plist에 구워 넣어 스스로 가진다(`cli/unit.ts:114-129`). `HERDR_PLUGIN_STATE_DIR`은 일부러 무시한다(`bridge/config.ts:529` 주석). 에이전트 hook(beacon)은 `HERDR_PANE_ID`와 `HERDR_SOCKET_PATH`를 보고 어느 pane인지 대 준다(`cli/beacon.ts:123-124`).
3. **소켓**: 브리지가 위 C2 표의 메서드로 읽고 쓴다. 이벤트 구독은 있지만 폴링을 재촉하는 용도뿐이다(`events.ts:1-45`, 코드 확인). 그래서 "이벤트 구독인지 폴링인지"의 답은 "폴링이 진실, 이벤트는 poke"다.
4. **herdr CLI**: 설정 디렉터리 탐색(`herdr plugin config-dir herdr.collie`), 업데이트 후 레지스트리 갱신(`herdr plugin link`), crew 후보 머신(`herdr machine list --json`), doctor의 버전·integration 점검(`herdr --version`, `herdr integration status`). 어느 것도 서비스 동작에 필수는 아니다(`machine-list.ts`는 없거나 실패해도 후보 없음, 코드 확인). 사용자 안내 문구는 herdr 액션 호출(`herdr plugin action invoke update --plugin herdr.collie`)로 쓴다는 규칙이 CLAUDE.md에 있다(후보).

herdr 서버 쪽 동작(액션 실행 환경, 이벤트 발행 시점, `session.snapshot` 응답 필드 전부)은 herdr 소스를 보지 않았으므로 미확인이다.

### mux 어댑터 패밀리

같은 `MuxAdapter` 계약(`types.ts:644`)을 구현한다. 어댑터는 자기가 하는 일만 `capabilities`로 선언하고, 선언되지 않은 칸은 "지원 안 함"이다(fail-closed, `capabilities.ts` 헤더 주석, `declareCapabilities` `:214`). 선택은 `COLLIE_MUX`(`registry.ts:151`의 기본값은 `herdr`이나 첫 `start`가 탐지해 묻고 기록한다, `cli/mux.ts` 헤더).

| 어댑터 | 전송·호출 | 선언한 능력(요약) | 이벤트 | 비고 | 근거 | 검증 수준 |
|---|---|---|---|---|---|---|
| herdr | 유닉스 소켓(Windows 파이프) NDJSON | 19개: 에이전트 탐지·세션 ref·worktree·세션 목록 포함 | `events.subscribe` 푸시 | 기본 대상 | `mux/herdr/adapter.ts:100-135` | 코드 확인 |
| tmux | `tmux` 자식 프로세스(`capture-pane`, `send-keys`, `list-*`, `display-message`, `new-window` 등, `-C` 문자열이 `protocol.ts`에 있음) | 13개. 에이전트 탐지·세션 ref·worktree 없음. space=tmux session(`adapter.ts` 헤더) | `topologyLatency: push` 선언(수단은 추론) | 에이전트는 beacon으로 보강 | `mux/tmux/adapter.ts:1052`, `tmux/protocol.ts`, `capabilities` 선언 줄 | 코드 확인 |
| zellij | `zellij` 자식 프로세스(`dump-screen`, `write-chars`, `send-keys`, `list-panes`, `subscribe`…) | 10개. space는 세션 하나뿐(`spaces:"one"`) | pane 이벤트만 푸시, 구조 변화는 주기 점검(상한 `ZELLIJ_CENSUS_MAX_MS`) | `XDG_RUNTIME_DIR`가 있어야 탐색 | `mux/zellij/adapter.ts:204,228`, `zellij/protocol.ts` | 코드 확인 |
| tern | `tern` 자식 프로세스 + `tern events` 스트림. `COLLIE_TERN_BIN` | 11개. pane 이름 변경·에이전트 탐지·세션 목록 없음 | 구조 변화 푸시 선언 | 실험 표기는 README(후보) | `mux/tern/adapter.ts:92-93`, `tern/exec.ts:56,83,108,147` | 코드 확인 |
| tuios | tuios 데몬의 JSON 소켓(`dialHerdr` 재사용, 요청당 연결) | 15개: 에이전트 탐지·세션 ref 포함 | 푸시 | 데몬 프로토콜 `hello` 버전 교섭 | `mux/tuios/adapter.ts:137-155`, `tuios/client.ts` 헤더 | 코드 확인 |
| durable | 프로그램의 유닉스 소켓 또는 URL+bearer(HTTP). pty 없음 | 터미널이 필요한 동작은 모두 `unsupported`. 상한이 있는 폴링(`bounded`) | 로그 읽기(`events.ts`) | 화면 없는 "프로그램" | `mux/durable/adapter.ts:1-20,362-363,1436` | 코드 확인(능력 목록 전수는 미열람) |

에이전트를 스스로 알려 주지 않는 어댑터(tmux·zellij·tern)는 beacon 데코레이터로 pane에 에이전트 신원을 붙인다(`withBeaconsIfBlind`, `bridge/index.ts:1471`, 코드 확인). herdr처럼 자기 신호가 있는 어댑터는 감싸지 않는다(`registry.ts` 주석).

### 한 번의 폴링과 한 번의 답장 (대표 흐름)

폴링(코드 확인):
1. `StateEngine`이 `cfg.pollMs`(1500ms)마다, 스트림이 건강하면 `pollIdleMs`(12000ms)마다 어댑터의 `snapshot()`을 부른다. — `bridge/index.ts:1472,1484`, `bridge/state-engine.ts:341`
2. herdr 어댑터가 `session.snapshot` 1회를 보내고 pane·space·tab을 Collie 도메인 모델로 바꾼다. — `adapter.ts:313-326,384-402`
3. 같은 틱에 git HEAD·프롬프트 캐시·todo·서브에이전트·사용량을 별도로 갱신한다(폴링을 기다리게 하지 않는다). — `bridge/index.ts:1488-1540`
4. 상태 전이(`working→blocked` 등)가 `NotificationCoordinator`로 가서 디바운스 후 푸시 한 건(요약)이 된다. — `bridge/index.ts:1544-1550`, `notifications.ts:171`
5. 폰은 `/api/snapshot`을 자기 간격으로 폴링해 같은 스냅샷을 받는다. — `server.ts:2614`, `use-polling.ts:309`

답장(코드 확인):
1. 폰이 입력창에서 `POST /api/pane/:id/reply`(텍스트+기대 프롬프트 정보). — `server.ts:434,2156`
2. 접근 게이트: Host·Origin·신원 → 기기 헤더(쓰기) → 페어링 토큰. — `server.ts:7339-7370`
3. `replyPane`이 본문을 검증하고 Send Protocol을 돌려 화면을 다시 읽고 입력창 상태를 확인한 뒤 `pane.send_text`(긴 텍스트는 bracketed paste) 다음 제출 키를 key gate로 보낸다. — `server.ts:5099-5135`, `surface/protocol.ts:1-30`
4. 결과 receipt를 요청 id로 저장하고 응답한다. 감사 로그에 한 줄. — `surface/protocol.ts`(accept 단계), `bridge/audit.ts`
5. 직후 해당 pane은 빠른 폴링 구간에 들어간다. — `state-engine.ts:51,483`

### 모듈별 역할

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `herdr-plugin.toml`, `scripts/collie-ctl.sh` | herdr에 등록되는 얇은 런처. 액션을 `bin/collie`로 넘김 | 입력: herdr 액션 → 출력: `collie <verb>` 실행 | `herdr-plugin.toml:31-117`, `collie-ctl.sh:96-119` | 코드 확인 |
| `cli/` | `collie` 모든 동사(서비스·페어링·crew·STT·업데이트·hook·doctor). 순수 로직은 `bridge/`에서 가져오고 `bridge/`는 `cli/`를 import하지 않는 방향 규칙 | 입력: argv·환경 → 출력: 서비스 조작·파일 쓰기·출력 | `cli/main.ts:66`, `program.ts:538`, `lifecycle.ts:1077-1242` | 코드 확인(방향 규칙은 `bridge/update-action.ts` 헤더 주석 기준이라 추론) |
| `bridge/index.ts` | 조립: 설정·저장소·어댑터·엔진·알림·서버 구성 | 입력: 설정 → 출력: 실행 중인 서비스 | `bridge/index.ts:724-1485,1544`, `server.ts:2407` | 코드 확인(2979줄 중 일부) |
| `bridge/server.ts` | HTTP 라우팅, 접근 게이트, 모든 `/api/*` 핸들러, 정적 PWA, CSP | 입력: HTTP → 출력: JSON·파일 | `server.ts:2407,2614,5099,7258,7339` | 코드 확인(일부) |
| `bridge/state-engine.ts` + `event-poker.ts` | 폴링 루프, 이벤트 poke·간격 조절, 상태 전이 이벤트, HOT_POLLS | 입력: 어댑터 → 출력: 스냅샷·전이 콜백 | `state-engine.ts:341,51`, `event-poker.ts:43` | 코드 확인(일부) |
| `bridge/mux/` | 멀티플렉서 포트·능력 선언·레지스트리·어댑터 6개 | 입력: Collie 요청 → 출력: 멀티플렉서별 호출 | `mux/types.ts:644`, `registry.ts:113`, `capabilities.ts:28` | 코드 확인(어댑터 본문 일부) |
| `bridge/surface/` | 입력 프레임 읽기, Send Protocol, Ask(질문 카드), 훅이 붙든 권한, 보류된 전송 | 입력: 화면·hook edge → 출력: receipt·ask | `surface/protocol.ts:1`, `ask.ts:93`, `hold.ts:617` | 코드 확인(헤더) |
| `bridge/journal/` | 하네스별 세션 로그 읽기(10종), 경로 포함 검사 | 입력: pane의 세션 ref → 출력: 턴·텍스트 | `journal/registry.ts:1-60` | 코드 확인(등록부) |
| `bridge/stt/` | 음성→텍스트 제공자 틈새(4종), 설정 mtime 재읽기 | 입력: 녹음 → 출력: 문자열 | `stt/config.ts:46`, `stt/index.ts:20,48` | 코드 확인 |
| `bridge/push.ts`, `notifications.ts`, `notify-prefs.ts`, `snooze.ts` | Web Push, 디바운스·요약, 종류·방해 금지 | 입력: 상태 전이 → 출력: push 발송 | `push.ts:290`, `notifications.ts:171` | 코드 확인 |
| `bridge/pairing.ts`, `access-jwt.ts`, `front-door.ts` | 기기 페어링, Cloudflare Access 검증, tailscale 정문 소유 기록 | 입력: 코드·토큰·헤더 → 출력: 허용/거부 | `pairing.ts:658`, `front-door.ts` | 코드 확인 |
| `bridge/crew/`, `bridge/walky/` | 멀티 머신 연합과 에이전트 간 메시지 | 입력: `/crew/v1/*`·로컬 소켓 → 출력: 병합 스냅샷·전달 | `crew/router.ts:88`, `walky/socket.ts:168` | 코드 확인(헤더·경로) |
| `bridge/cache/`, `usage.ts`, `subagents.ts`, `todos.ts`, `machines.ts` | 프롬프트 캐시 칩·경고, 컨텍스트·서브에이전트·todo, 머신 부하 | 입력: 폴링된 pane·로그 → 출력: 스냅샷 필드·푸시 | `cache/warden.ts:43`, `machines.ts:118` | 코드 확인(헤더) |
| `web/` | PWA. React Router 데이터 모드, Vite, 하네스별 화면 문법, 서비스 워커(push 처리), 로컬라이제이션 12종 | 입력: `/api/*` → 출력: 화면·요청 | `web/src/router.tsx:82-185`, `hooks/use-polling.ts`, `sw.ts:211`, `lib/harness/registry.ts` | 코드 확인(라우트·진입) / 화면 세부 미탐색 |
| `packages/durable-sdk` | durable 프로그램용 npm 클라이언트(소켓 서버·HTTP·pi 연동) | 입력: 프로그램의 대화·질문 → 출력: durable wire | `packages/durable-sdk/package.json` | 코드 확인(매니페스트) / 소스 미탐색 |

**미확인 영역**
- herdr 서버가 매니페스트·액션 환경변수·이벤트·`session.snapshot` 필드를 실제로 어떻게 처리하는지(herdr 소스·실행 필요).
- 이 레포를 빌드·실행하지 않았으므로 동작과 성능은 `실행 확인`이 아니다. 특히 STT 인식, 푸시 도착, `tailscale serve` 동작, 업데이트 실행은 코드 경로까지만 봤다.
- tmux·zellij·tern·tuios 어댑터가 실제 멀티플렉서와 맞는지(캡처 fixture는 `bridge/mux/*/captures/`에 있으나 열지 않았다).
- 레포 문서가 내세우는 숫자(예: 테스트 수, 분 단위 측정치, 릴리스 게이트의 37개 브라우저 케이스)는 후보로만 읽었다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

다음에 볼 곳:
- herdr 연동만 더 파려면: `bridge/mux/herdr/adapter.ts` 나머지(입력 검증, `pasteBlock`, 키 철자 `keys.ts`), `bridge/event-poker.ts`의 재연결·디바운스, `bridge/dial.ts`의 Windows 파이프 경로.
- 핵심 사용자 흐름: `bridge/surface/protocol.ts`의 단계(S0·probe·write·submit)와 `web/src/lib/harness/claude/*`의 프롬프트 문법.
- 보안 모델 전체: `bridge/server.ts`의 crew 분기(`/crew/v1` 먼저 처리되고 그 뒤 loopback 피어 검사)와 `bridge/crew/`.
- 기능 스펙은 사용자 승인 후 지도 순서(F1→F2→…)로. 범위를 좁히려면 먼저 핵심 행(F1~F6, F9, F11, F12, F22~F24, F26)부터.
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성)
