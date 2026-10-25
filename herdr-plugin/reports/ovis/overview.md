---
sha: "5e4491326143c1f37c7a19631af966d18a960e52"
created: 2026-10-24
updated: 2026-10-24
sources:
  - herdr-plugin.toml
  - README.md
  - INSTALL.md
  - package.json
  - LICENSE
  - ovis-site/assets/fonts/LICENSE
  - install.sh
  - app/package.json
  - app/capacitor.config.json
  - app/web/shell.js
  - app/mac/README.md
  - scripts/plugin.ts
  - scripts/with-bun.sh
  - scripts/generate-protocol-types.ts
  - scripts/herdr-schema.json
  - scripts/build-site.ts
  - scripts/install-gjc-integration.ts
  - server/index.ts
  - server/managed.ts
  - server/supervisor.ts
  - server/herdr/client.ts
  - server/herdr/methods.ts
  - server/collector.ts
  - server/core/server-core.ts
  - server/core/socket.ts
  - server/core/status.ts
  - server/core/terminal-process.ts
  - server/core/input.ts
  - server/core/composer.ts
  - server/pty/session.ts
  - server/pty/pty-host.mjs
  - server/mirror.ts
  - server/watch.ts
  - server/conversation.ts
  - server/prompt.ts
  - server/dialogs/live.ts
  - server/dialogs/index.ts
  - server/push.ts
  - server/auth.ts
  - server/access.ts
  - server/devices.ts
  - server/tailscale.ts
  - server/portal.ts
  - server/machines.ts
  - server/ssh.ts
  - server/remote-bundle.ts
  - server/remote-host.ts
  - server/remote-entry.ts
  - server/file-routes.ts
  - server/file-view.ts
  - server/paste.ts
  - server/repo-diff.ts
  - server/usage.ts
  - server/voice.ts
  - server/updater.ts
  - server/herdr-update.ts
  - server/herdr-profiles.ts
  - server/herdr-sidebar.ts
  - server/telemetry.ts
  - server/plugin-routes.ts
  - server/workspace-routes.ts
  - server/pane-routes.ts
  - server/agent-launch.ts
  - shared/protocol.ts
  - shared/notify-policy.ts
  - shared/push.ts
  - shared/telemetry.ts
  - shared/machines.ts
  - push-relay/README.md
  - push-relay/worker.ts
  - telemetry/README.md
  - telemetry/worker.ts
  - public/sw.js
  - src/lib/settings.ts
  - src/lib/usage.ts
  - docs/guide.md
  - docs/native-app.md
---

# Ovis Analysis Overview

범례: 검증 수준은 `코드 확인`(구현부를 직접 읽음) / `추론` / `미확인`. 이 문서는 실행하지 않고 읽기만 했으므로 `실행 확인`은 없다. 경로는 모두 `herdr-plugin/repos/ovis/` 기준이고, `파일:줄`은 기준 SHA에서 직접 열어 확인한 줄이다. README·docs·AGENTS.md·CLAUDE.md·DESIGN.md는 후보로만 읽었고, 코드로 확인한 것만 표에 옮겼다. 파일이 2227개인 큰 레포라 "진입점 + 호출 경로"까지만 읽은 행이 많다. 그런 행은 검증 수준에 `진입점`이라고 적었다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/devswha/ovis` (`herdr-plugin/artifacts/ovis/repo-metadata.txt`)
- **기준 SHA**: `5e4491326143c1f37c7a19631af966d18a960e52` (commit 2026-10-23, main)
- **작업트리 상태**: Clean (repo-metadata.txt, 추적 파일 2227개)
- **분석 목적**: 학습·도입 검토. (1) herdr 플러그인이 매니페스트와 소켓·CLI로 herdr와 어떻게 연동하는가, (2) 브라우저·폰에서 에이전트 pane을 보고 조작하는 기능이 어떻게 구성되는가, (3) 외부로 나가는 데이터(푸시·텔레메트리·사용량·음성)가 무엇인가.
- **라이선스**: MIT (루트 `LICENSE` 전문을 직접 열어 확인. `Copyright (c) 2026 devswha`). 하위 `ovis-site/assets/fonts/LICENSE`는 SIL Open Font License 1.1, 저작권자 "The Geist Project Authors" (Geist 폰트, 첫 줄에서 확인). 루트 `THIRD_PARTY_NOTICES.md`가 있다(내용은 열지 않음). 그 외 `src/fonts/`(Pretendard·JetBrains Mono·Nerd Font 서브셋 96개)에는 LICENSE 파일이 추적되지 않는다(`git ls-files`에서 LICENSE 이름 파일은 위 두 개뿐).
- **분석 대상 제품**: 아래 표. 루트는 하나의 Bun 프로젝트(`package.json` name `ovis`, version 0.4.13, private)이고, 배포·실행 단위가 여럿 섞여 있다.

| 단위 | 위치 | 하는 일 | 구분 |
|---|---|---|---|
| herdr 플러그인 (매니페스트) | `herdr-plugin.toml`, `scripts/plugin.ts`, `scripts/plugin.ps1`, `scripts/with-bun.sh`, `scripts/preflight.*` | herdr가 빌드·시작·액션으로 부르는 입구 | 핵심 |
| 서버 (Bun HTTP+WebSocket) | `server/`(564개), `shared/`(44개) | herdr 소켓·CLI와 브라우저 사이의 브리지. 이 레포의 본체 | 핵심 |
| 브라우저·폰 클라이언트 (React PWA) | `src/`(870개, 대부분 `src/lib`·`src/components`), `index.html`, `public/`, `vite.config.ts` | 화면. 서버가 빌드 결과(`dist`)를 서빙 | 핵심 |
| 네이티브 앱 셸 | `app/`(157개: `ios/` `android/` `mac/` `web/` `store/`) | Capacitor로 만든 iOS·Android 래퍼, macOS 원클릭 설치 앱 | 부속 |
| 푸시 릴레이 | `push-relay/`(6개) | Cloudflare Worker. 네이티브 앱용 APNs/FCM 중계 | 부속 (별도 배포) |
| 텔레메트리 수신기 | `telemetry/`(6개) | Cloudflare Worker. 익명 설치·활성 집계 수신 | 부속 (별도 배포) |
| 설치 스크립트 | `install.sh`, `install.ps1` | herdr·Bun·Node 설치 후 플러그인 설치, Tailscale 안내 | 부속 (배포 입구) |
| 문서·랜딩 사이트 | `ovis-site/`(64개, ovis.sh), `site/`(13개, herdrweb.dev 전달·데모), `docs/`(97개) | 사이트와 브라우저 데모(`site/demo`는 픽스처로 도는 앱) | 부속 |
| 원격 PC 번들 | `scripts/build-remote-bundle.ts`, `server/remote-*.ts` | 다른 PC에 SSH로 올리는 런타임 번들(Bun+서버) | 핵심(원격 PC 기능의 일부) |
| GJC 확장 | `integrations/gjc.ts`, `scripts/install-gjc-integration.ts` | gjc 에이전트용 확장을 설치해 세션 id를 알림 | 부속 |
| 개발·QA | `scripts/*-regression.ts`·`*-qa.ts`·`ci-*`(약 270개), `.github/`(15개), `evidence/`(9개), `patches/`(2개), `changelog.d/`(42개), `server/fixtures/`(128개) | 테스트·CI·릴리스·증거 이미지 | 부속 (분석 밖, 열지 않음) |

- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음

### 용어

- **herdr**: 코딩 에이전트용 터미널 멀티플렉서. workspace > tab > pane 계층을 가진다. Ovis는 herdr를 대체하지 않고 같은 pane에 붙는 또 하나의 클라이언트다.
- **플러그인**: herdr가 `herdr-plugin.toml`을 읽어 빌드·시작하는 외부 프로그램. Ovis는 이 방식으로 설치된다.
- **bridge(브리지)**: 이 문서에서 Ovis 서버를 가리키는 말. herdr와 브라우저 사이를 잇는다. 코드에서도 "bridge"라고 부른다.
- **소켓 API**: herdr가 `HERDR_SOCKET`이 가리키는 Unix 소켓(Windows는 named pipe)에 여는 줄 단위 JSON(NDJSON) 인터페이스. 요청마다 새로 연결한다(`events.subscribe`만 연결을 유지).
- **attach**: `herdr terminal attach <terminal id>` 명령. pane의 실제 터미널 바이트 스트림을 받는다. Ovis는 이것을 PTY(가짜 터미널)에 물려 브라우저로 전달한다.
- **sidecar**: Bun 서버가 따로 띄우는 Node 보조 프로세스(`server/pty/pty-host.mjs`). node-pty를 Node에서만 안정적으로 쓸 수 있어서 분리했다(코드 주석).
- **chat(채팅 뷰)**: 터미널 출력이 아니라 에이전트가 직접 쓰는 세션 파일(transcript)을 읽어 대화로 보여 주는 화면.
- **transcript**: Claude Code·Codex 등이 대화를 이어 붙여 쓰는 세션 파일(JSONL이나 SQLite).
- **카드(prompt card)**: 에이전트 화면에 뜬 승인·질문·플랜 메뉴를 파싱해 버튼으로 바꾼 것.
- **페어링**: 소유자가 PC에서 짧은 코드를 만들고 새 기기가 그 코드를 한 번 보내 기기 전용 토큰을 받는 절차.
- **PWA**: 홈 화면에 설치되는 웹 앱. 서비스 워커로 푸시와 오프라인 셸을 처리한다.
- **Web Push / VAPID**: 브라우저 벤더(FCM·APNs·Mozilla) 푸시 서비스로 암호화한 알림을 보내는 표준(RFC 8030/8291/8292).
- **Tailscale serve**: Tailscale 네트워크(tailnet) 안에서만 HTTPS로 로컬 포트를 공개하는 명령.
- **Portal**: 별도로 설치하는 터널 도구(`gosuda/portal-tunnel`). 공개 HTTPS 주소를 만들 때 선택적으로 쓴다.
- **supervisor**: 서버를 빌드·재시작·교체하는 상위 프로세스(`server/supervisor.ts`). 업데이트 때 새 릴리스로 넘긴다.

---

## 2. 프로젝트 개요

Ovis는 herdr가 이미 돌리고 있는 에이전트 pane(Claude Code, Codex 등)을 브라우저와 폰에서 보고 조작하게 해 주는 웹 클라이언트다. 같은 pane을 (1) 에이전트 자체 세션 파일을 읽은 채팅, (2) 실제 터미널, (3) 상태 알림과 푸시로 보여 주고, 메시지·키·승인 응답을 같은 pane에 입력한다. herdr가 프로세스와 스크롤백을 소유하고 Ovis는 소켓과 CLI로 붙는다. 서버는 Bun 하나로 HTTP·WebSocket을 모두 받고, 계정 DB가 없다. 접근은 토큰, 기기 페어링 쿠키, Tailscale 로그인으로 판단한다. 자체 호스팅 중계 서비스는 없고, 선택 기능에서만 외부 서비스를 부른다(아래 "외부 호출·비밀·텔레메트리").

이 폴더의 다른 플러그인(herdr-auto-title 등)이 폴링으로 소켓을 읽는 것과 달리, Ovis는 `events.subscribe` 이벤트 구독을 쓰고 스냅샷으로 보정한다. 또 소켓뿐 아니라 herdr CLI(`terminal attach`, `terminal session observe`, `machine list`, `update`)도 자식 프로세스로 실행한다.

### Ovis가 하는 일 (README·docs와 코드 대조)

| # | 주장 | 근거 | 검증 수준 |
|---|---|---|---|
| 1 | 매니페스트가 빌드(preflight → `bun install` → `bun run build`), startup 한 번, 액션(start/stop/status/phone), zoomed pane(`phone`)을 선언한다. 플랫폼별(`sh` vs `powershell`) 항목이 따로 있다. `min_herdr_version = "0.9.0"`. | `herdr-plugin.toml:1-6,9-32,34-40,42-83,84-97,98-111` | 코드 확인(매니페스트). herdr가 필드를 어떻게 해석·강제하는지는 미확인 |
| 2 | startup 훅은 한 번 도는 초기화 명령이라 `plugin.ts start`가 서버를 detached로 직접 띄우고 pid를 상태 디렉터리에 기록한다. 이미 응답 중이면 건드리지 않는다(멱등). | `scripts/plugin.ts:1-12`(주석), `:317-361`(`start`: `health()`, `spawn(... "server/managed.ts")`, `PID_FILE`) | 코드 확인 |
| 3 | herdr가 주는 `HERDR_SOCKET_PATH`를 서버가 읽는 `HERDR_SOCKET`으로 옮겨 넘긴다. 설정 파일에 `HERDR_SOCKET`이 있으면 그쪽이 이긴다. 플러그인 설정(토큰 등)은 `HERDR_PLUGIN_CONFIG_DIR`의 `env`·`.env`에서 읽는다. | `scripts/plugin.ts:16-20`(주석), `:136`, `:353` | 코드 확인 |
| 4 | 서버는 기본 `127.0.0.1:7317`에 바인드하고 포트가 막히면 다음 후보(17317…)로 옮겨 기억한다. | `shared/protocol.ts:849`(`DEFAULT_PORT`), `scripts/plugin.ts:147`(`HOST`), `:275-315`(`settlePort`), `server/index.ts:239-244`(`Bun.serve`) | 코드 확인 |
| 5 | 에이전트 상태는 `events.subscribe`로 받는다. pane별 `pane.agent_status_changed` 구독(한 연결에 여러 pane), 구조 이벤트(workspace·worktree·tab·pane·layout 20종) 구독, `pane.focused` 구독이 따로 있고, 끊기면 다시 열고 스냅샷으로 놓친 변화를 보정한다. 60초 보정 타이머도 있다. | `server/collector.ts:1-47`(주석), `:49`, `:285-306`, `:322-326`, `:556`; `server/herdr/client.ts:831-944` | 코드 확인 |
| 6 | 브라우저 연결이 열리면 `session.snapshot`을 받아 첫 `snapshot` 프레임으로 보낸다. 이후 변화는 `pane-status`·`session-changed` 등으로 밀어 준다. | `server/core/socket.ts:97-117`(`open`), `server/core/status.ts:134-153`(`clientSnapshot`), `shared/protocol.ts:791-843` | 코드 확인 |
| 7 | 터미널 화면은 `herdr terminal attach <terminal_id>`를 Node PTY sidecar에 물려 받는다. terminal id는 `session.snapshot`의 pane에서 읽는다. 환경에 `HERDR_SOCKET_PATH`를 넣어 같은 herdr 세션으로 붙인다. 서버 토큰은 sidecar에 넘기지 않는다. | `server/core/terminal-process.ts:146-160`, `:425-438`; `server/pty/session.ts:33-47`, `pty-host.mjs:1-25` | 코드 확인 |
| 8 | herdr에 attach가 없는 환경(Windows)에서는 `pane.read`로 화면을 읽어 바뀐 줄만 같은 `pty-data` 프레임으로 보낸다(화면 미러). | `server/herdr/client.ts:38-41`, `:325-330`; `server/mirror.ts:1-19` | 코드 확인 |
| 9 | 채팅은 pane의 에이전트를 herdr가 알려 준 `agent`로 구분하고(`agent.get`의 `agent_session` 포함), 에이전트별 세션 저장소(Claude `~/.claude/projects`, Codex 롤아웃, omp·omo·gjc·pi·cmd 세션 파일, OpenCode·Devin·Hermes·agy SQLite·원장, Grok 로그)를 읽는다. 인식 못 하면 `source: "scrollback"`으로 터미널 텍스트에 맡긴다. | `server/conversation.ts:1-47`(주석), `:925-1019`(`resolveTranscript`), `:1061`(`paneConversation`), `server/pane-routes.ts:250-276` | 코드 확인(디스패치). 각 저장소 파서 세부는 미탐색 |
| 10 | 메시지는 같은 pane에 입력한다. 채팅 전송은 `agent.prompt`(+필요 시 `pane.send_keys` Enter), 키 입력·비밀번호 입력은 `pane.send_keys`/`pane.send_text`. attach가 가능하면 일반 타이핑은 attach PTY로 간다. | `server/core/composer.ts:483`, `:220,379,469`; `server/core/input.ts:114,157,235,288-300` | 코드 확인 |
| 11 | 승인·질문·플랜 카드는 `pane.read`(`source: "detection"`, 텍스트)로 화면을 읽어 에이전트별 reader(Claude·Codex·omp·omo·pi·hermes·gjc·opencode·grok·agy·devin·cmd·fallback)로 파싱한다. 답은 키 입력으로 보낸다. | `server/dialogs/live.ts:191-204`, `server/dialogs/index.ts:17`, `server/prompt.ts:895` | 코드 확인(진입점). reader 규칙은 미탐색 |
| 12 | 알림은 이전 상태가 있고 `blocked`(입력 대기) 또는 `done`(완료)로 바뀔 때만 인정한다. 기기별 설정(입력 알림 on/off, 완료 알림 off/long/always)이 있고, 푸시는 기본 10초(질문)·60초(완료) 기다렸다가, 그동안 상태가 바뀌면 취소한다. 앱 창이 하나라도 사용 중(보이고 포커스)이면 푸시를 보내지 않는다. | `shared/notify-policy.ts:10-15,51-73`, `server/push.ts:65-73`(`DEFAULT_ALERT_TIMING`), `:1-35`(주석), `:482-490` | 코드 확인(정책·타이밍). 대기 취소 구현은 주석으로만 확인 |
| 13 | 푸시 본문은 `{machine_id?, pane_id, workspace_id?, title, body, tag}`이고 `web-push`로 RFC 8291(aes128gcm) 암호화·VAPID 서명해 구독 endpoint로 `fetch` POST한다(리다이렉트 금지, TTL 12시간). 키는 상태 디렉터리 `vapid.json`. | `shared/push.ts:11-20`, `server/push.ts:56,188-219,269-300` | 코드 확인 |
| 14 | 접근 판단에 사용자 DB가 없다. 요청이 어디서 왔는지(루프백, 프록시 헤더), Tailscale 로그인 헤더, 기기 쿠키, 공유 토큰으로 `full`/`none`을 정한다. 토큰을 설정하면 페어링된 기기 외에는 모두 토큰이 필요하다. | `server/access.ts:1-30`(주석), `:157`(`decideAccess`), `server/auth.ts:1-14,110-117`, `server/index.ts:255-340` | 코드 확인 |
| 15 | 페어링 코드는 10분 유효·5회 시도 제한이고, 기기 토큰은 해시만 `devices.json`에 저장한다(0600). 기기는 조작 가능/보기 전용 역할을 가진다. 쿠키는 HttpOnly·SameSite=Strict, 최대 1년. | `server/devices.ts:1-9,20-21,68,247-288`, `server/auth.ts:46,129-136` | 코드 확인 |
| 16 | 원격 PC는 SSH ControlMaster와 `-L` 포워딩으로 연결하고, 상대 PC에 런타임 번들(Bun+서버)을 올려 브리지를 띄운다. 번들 매니페스트 기본 위치는 GitHub Releases(`remote-v32`). SSH는 `StrictHostKeyChecking=yes`, 에이전트·X11 포워딩은 끈다. | `server/ssh.ts:115-141,203-204,324-332`, `server/remote-bundle.ts:12-21`, `server/remote-host.ts:23-26`, `server/remote-entry.ts:1-40`, `shared/machines.ts:7-8` | 코드 확인(진입점). 설치 스크립트 세부는 미탐색 |
| 17 | 구독 사용량 미터는 기본 꺼져 있다(`showUsage: false`). 켜면 서버가 이 PC의 다른 CLI 로그인(Claude·Codex·Cursor·Grok·Copilot·OpenCode·Antigravity)을 읽어 각 제공사 사용량 API로 보낸다. 토큰 갱신은 하지 않는다. | `src/lib/settings.ts:327`, `src/components/Composer.tsx:267`, `server/usage.ts:1-15,262-310,333-369,570-585`, `server/usage.ts:924,1039` | 코드 확인(기본값·읽는 위치). 각 제공사 엔드포인트 호출 세부는 미탐색 |
| 18 | 음성 입력은 서버에 사용자 OpenAI 키(`OVIS_OPENAI_API_KEY` 또는 `voice.json`)가 있으면 클립을 `/audio/transcriptions`로 보내고, 정리 모드면 `/chat/completions`도 부른다. 키가 없으면 브라우저 `SpeechRecognition`을 쓴다. | `server/voice.ts:1-4,15-16,81-83,245,309,347`, `src/lib/voice.ts:1-5` | 코드 확인 |
| 19 | 앱 업데이트는 `git fetch origin +refs/tags/v*`로 태그만 받아, 상태 디렉터리의 `release-*`에 사설 체크아웃을 만들고 `bun install --frozen-lockfile`, `typecheck`, `build` 후 supervisor가 새 릴리스로 넘어간다. 자동 설치는 기본 꺼짐(`OVIS_AUTO_UPDATE`). 5분마다 확인한다. | `server/updater.ts:287,296-298,418-432`, `server/supervisor.ts:100`, `docs/guide.md:498-524`(기본값 표) | 코드 확인 |
| 20 | 텔레메트리는 기본 켜짐이지만 화면 고지를 본 뒤 10분이 지나야 보낸다. `OVIS_TELEMETRY=0`·`DO_NOT_TRACK`·`CI`·herdr 테스트 환경이면 막힌다. 보내는 대상은 `herdr-web-ui-telemetry.devswha.workers.dev`. | `server/telemetry.ts:19-26,79-91,182,357-362,419-432` | 코드 확인 |
| 21 | 파일 뷰어는 pane cwd 기준 상대 경로뿐 아니라 절대 경로도 연다(인증된 요청만). 첨부 파일·붙여 넣은 이미지는 `<pane cwd>/.ovis`(또는 `OVIS_PASTE_DIR`)에 저장하고 경로를 입력창에 넣는다. | `server/file-routes.ts:43-50`, `server/file-view.ts:124`, `server/paste.ts:81-90`, `server/pane-routes.ts:390-420`, `shared/attachments.ts`(32MB 상한) | 코드 확인 |
| 22 | 저장소 변경 보기는 git을 argv 배열(셸 없이)로 실행하고 외부 diff 드라이버·fsmonitor를 끄며 바이트·시간 상한을 둔다. 읽기 전용. | `server/repo-diff.ts:1-20,60,84,316` | 코드 확인 |
| 23 | 네이티브 푸시 릴레이(`push.ovis.sh`)는 코드와 테스트가 있으나 `docs/native-app.md`는 "배포 안 됨(not deployed yet), 2026-10-23"이라 쓴다. iOS 앱의 알림 복호화 확장(Notification Service Extension) 소스·타깃은 추적 파일에 없다(`project.pbxproj`에 `NotificationService`·`app-extension` 없음). Android는 `ovis-push` 모듈에 `WebPushDecrypt.java`가 있다. | `push-relay/worker.ts:1-30`, `docs/native-app.md:1-8`, `app/android/settings.gradle:7-13`, `app/android/ovis-push/src/main/java/sh/ovis/push/` | 코드 확인(파일 존재). 배포 여부는 미확인 |

### 기능 지도

범례: 선행 `C*`는 아래 공유 계약. "스펙·상태" 경로는 제안이며 모두 미작성이다. 구분의 "핵심"은 herdr 연동과 pane 조작, "부속"은 선택 기능·별도 배포·개발 도구다.

**사용자가 직접 겪는 기능**

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F1 workspace·tab·pane 레이아웃 보기 | 사이드바·탭 스트립·분할 pane에 herdr 구조와 각 에이전트 상태를 본다. 명령 팔레트로 PC·workspace·pane 검색. herdr `config.toml`의 사이드바 행 토큰을 읽기 전용으로 반영 | `src/App.tsx:221` `App`, `src/components/Sidebar.tsx:187`, `TabStrip.tsx:60`, `PaneCanvas.tsx:58`, `CommandPalette.tsx:149`, `server/index.ts:472-478`(`/api/session`), `server/herdr-sidebar.ts:20,123` | C2, C3, C5 | 핵심 | `capabilities/layout-view.md` · 미작성 | 코드 확인(진입점). 화면 컴포넌트 세부 미탐색 |
| F2 에이전트 상태 수집(RUN/INPUT/DONE) | herdr 이벤트 구독으로 모든 pane의 상태를 모아 브라우저에 `pane-status`로 방송. 놓친 변화는 스냅샷 재생으로 보정 | `server/collector.ts:243` `startStatusCollector`, `server/core/status.ts:38,253-300`, `server/completion.ts:55` | C2, C3 | 핵심 | `capabilities/status-collector.md` · 미작성 | 코드 확인(구독 목록·재연결). 보정 규칙 세부 미탐색 |
| F3 workspace·tab·worktree 조작 | 만들기(폴더 선택·`first_message`), 이름 변경, 순서 이동, 닫기, git worktree 생성·열기·삭제 | `server/workspace-routes.ts:39,102,204,275,312`, `server/herdr/client.ts:433-590` | C2, C4 | 핵심 | `capabilities/workspace-ops.md` · 미작성 | 코드 확인(라우트→소켓 메서드) |
| F4 pane 조작 | 분할·줌·교체·크기 조정·비우기·포커스·닫기·이름 변경, 레이아웃 비율 | `server/pane-routes.ts:35,340-390,321`, `server/herdr/client.ts:740-802` | C2, C4 | 핵심 | `capabilities/pane-ops.md` · 미작성 | 코드 확인(라우트→소켓 메서드) |
| F5 새 에이전트 시작 | 폴더·에이전트 종류·인자를 골라 새 workspace/tab/worktree에 에이전트를 띄움. herdr가 아는 종류는 `agent.start`, 셸에서 시작하는 종류는 pane에 명령 입력 | `server/agent-launch.ts:15,32`, `server/shell-agent.ts:157,280-297`, `server/agents-routes.ts:32`, `src/components/NewSessionDialog.tsx:93`, `shared/supported-agents.ts` | F3, C2 | 핵심 | `capabilities/agent-launch.md` · 미작성 | 코드 확인(진입점·호출) |
| F6 라이브 터미널 | pane의 실제 터미널(xterm.js). 여러 브라우저가 한 attach를 공유(재생·역압), 키 바(Esc/Ctrl 등), 찾기, 선택 복사, 읽기 전용 관찰(`watch`), Windows 화면 미러 | `server/core/terminals.ts:57`, `server/core/terminal-process.ts:161-495`, `server/pty/session.ts:33`, `server/mirror.ts`, `server/watch.ts:82`, `src/components/PaneTerminal.tsx:148`, `KeyBar.tsx:190` | C2, C3 | 핵심 | `capabilities/live-terminal.md` · 미작성 | 코드 확인(attach 실행·환경). 흐름 제어·재시도 규칙 세부 미탐색 |
| F7 채팅 뷰 (에이전트별 세션 파일 reader 패밀리) | 같은 pane을 대화로 본다. Claude·Codex·omp·omo·gjc·pi·cmd·OpenCode·Devin·Hermes·Grok·agy 12종의 세션 저장소를 읽고 턴 단위로 접어 보여 준다. 인식 실패는 터미널로 대체 | `server/conversation.ts:925,1020,1061`, `server/pane-routes.ts:250`, `server/claude-transcript.ts:417`, `server/codex.ts:200,345`, `server/transcript-records.ts:406`, `server/opencode.ts:463`, `src/components/ChatView.tsx:958`, `ChatTimeline.tsx:31` | C2, C3, C9 | 핵심 (패밀리: 같은 `ConversationTurn` 계약) | `capabilities/chat-readers.md` · 미작성 | 코드 확인(디스패치). 각 reader 내부 미탐색 |
| F8 메시지 보내기 (컴포저) | 채팅 입력. 작업 중이면 다음 턴으로 큐잉, Send now, Stop, 비밀번호 입력(저장·큐 없이 바로 전송), 파일·이미지 첨부, `/`·`@` 완성 | `server/core/composer.ts:230`, `server/core/pending.ts:66`, `server/core/input.ts:26`, `server/pane-routes.ts:277,390`, `shared/protocol.ts:731-735`, `src/components/Composer.tsx:232`, `SecretInput.tsx:9` | C2, C3 | 핵심 | `capabilities/composer-send.md` · 미작성 | 코드 확인(호출 경로). 큐·재시도·초안 규칙 세부 미탐색 |
| F9 승인·질문·플랜 카드 | 에이전트 화면의 메뉴를 카드로 바꿔 탭으로 답한다. 답하기 전에 메뉴가 아직 현재인지 확인 | `server/prompt.ts:895`, `server/dialogs/live.ts:191-204`, `server/dialogs/index.ts`(13개 reader), `src/components/PromptCard.tsx:34` | C2, C3 | 핵심 (패밀리: 에이전트별 reader) | `capabilities/prompt-cards.md` · 미작성 | 코드 확인(진입점). reader 규칙 미탐색 |
| F10 알림 (앱 내 + 웹 푸시) | 입력 대기·완료·터미널 종료를 알림. 앱이 닫혀 있어도 푸시. 기기별 알림 설정, 지연·취소 | `server/push.ts:188,269,524`, `shared/notify-policy.ts:10`, `public/sw.js:197`, `src/lib/push.ts:72`, `src/lib/notifications.ts` | F2, C8 | 핵심 | `capabilities/alerts-push.md` · 미작성 | 코드 확인 |
| F11 인증·접근·기기 페어링 | 토큰·Tailscale 로그인·페어링 코드로 접근. 기기별 조작/보기 전용, 폐기 시 스트림 종료 | `server/access.ts:157`, `server/auth.ts:301`, `server/devices.ts:68,247`, `src/components/AccessGate.tsx:29`, `DevicesPanel.tsx:42` | C4, C6 | 핵심 | `capabilities/access-pairing.md` · 미작성 | 코드 확인 |
| F12 폰 접속 설정 (Tailscale·QR) | `Phone setup` pane과 `phone` 액션이 `tailscale serve`로 tailnet HTTPS 주소를 만들고 QR로 보여 준다 | `herdr-plugin.toml:84-111`, `scripts/plugin.ts:569,634`, `server/tailscale.ts:98,122,126`, `src/components/PhonePanel.tsx:22` | C1, F11 | 핵심 | `capabilities/phone-setup.md` · 미작성 | 코드 확인(진입점). `tailscale` 출력 파싱 세부 미탐색 |
| F13 PWA 설치·오프라인 셸 | 홈 화면 설치, 서비스 워커(탐색은 네트워크 우선, 정적 자산은 캐시 우선, API·WS는 가로채지 않음) | `public/sw.js:1-12,197`, `public/manifest.webmanifest`, `src/pwa.ts:1-9` | 없음 | 핵심 | `capabilities/pwa-shell.md` · 미작성 | 코드 확인 |
| F14 파일 브라우저·뷰어·저장소 변경 보기 | 경로 클릭으로 이미지·영상·PDF·텍스트·마크다운 열기, 폴더 탐색, git working tree/staged/commit 비교 diff | `server/file-routes.ts:32`, `server/file-view.ts:124`, `server/directories.ts:60`, `server/repo-diff.ts:316`, `server/workspace-routes.ts:74-96`, `src/components/FilesDialog.tsx:32`, `FileViewer.tsx:147`, `RepoChanges.tsx:32`, `RepoDiffViewer.tsx:78` | C4 | 핵심 | `capabilities/files-diff.md` · 미작성 | 코드 확인(진입점). 페이지 렌더·미디어 주소 규칙 미탐색 |
| F15 슬래시 명령·스킬 메뉴 | 에이전트별 명령·스킬 목록을 읽어 `/` 메뉴를 만든다(내장 목록 + 스킬 폴더) | `server/commands.ts:29`, `server/skills/index.ts:52`, `server/pane-routes.ts:73,89` | C2 | 핵심 (패밀리: 에이전트별 source) | `capabilities/agent-commands.md` · 미작성 | 코드 확인(진입점) |
| F16 세션 기록·재개 | "Earlier sessions"에서 지난 세션을 찾아 같은 에이전트로 재개 | `server/session-history-routes.ts:26-27,156,245`, `server/session-history.ts:63`, `src/components/SessionHistory.tsx:60` | F7, C4 | 핵심 | `capabilities/session-history.md` · 미작성 | 코드 확인(진입점) |
| F17 계획·백그라운드 작업 표시 | Claude Code·Codex 계획 진행률, OmO 작업·Claude 서브에이전트·백그라운드 명령 목록, "BG" 상태 | `server/session-plan.ts:44`, `server/tasks-routes.ts:16`, `server/plan-routes.ts:18`, `server/omo-tasks.ts:64`, `server/claude-subagents.ts`, `server/background-wait.ts:45`, `src/components/BackgroundTasks.tsx:38` | F7 | 부속 | `capabilities/plan-tasks.md` · 미작성 | 코드 확인(진입점). 추적 규칙 미탐색 |
| F18 원격 PC (SSH) | 사이드바에 다른 PC를 SSH로 추가(키/비밀번호 askpass), 번들 설치·업데이트, 같은 UI로 원격 workspace 조작·알림 | `server/machines.ts:165`, `server/machine-api.ts:53`, `server/machine-relay.ts:31`, `server/ssh.ts:81`, `server/remote-host.ts`, `server/remote-bundle.ts`, `server/remote-entry.ts`, `server/herdr-profiles.ts:53`, `src/components/MachineSidebar.tsx:30` | C2, C7, F11 | 핵심 (선택 기능) | `capabilities/remote-pcs.md` · 미작성 | 코드 확인(진입점). 설치 스크립트·Windows 경로 미탐색 |
| F19 음성 입력 | 마이크로 채팅·터미널 입력줄에 받아쓰기(자동 전송 없음) | `server/voice.ts:208,370`, `shared/voice.ts`, `src/components/VoiceInput.tsx:234` | 없음 | 부속 | `capabilities/voice-input.md` · 미작성 | 코드 확인 |
| F20 구독 사용량 미터·Hub | 설정에서 켜면 각 AI 구독의 5시간·주간 한도 표시. CLIProxyAPI Hub(URL+관리 키)에서 계정 가져오기 | `server/usage.ts:924,1039`, `server/usage-login.ts:22`, `server/cliproxy.ts:15`, `server/cliproxy-routes.ts`, `src/components/UsageMeters.tsx:88` | C4 | 부속 | `capabilities/usage-meters.md` · 미작성 | 코드 확인(기본값·읽는 위치). 제공사별 파서 미탐색 |
| F21 Portal 공개 주소 | 별도 설치한 `portal`을 설정에서 시작·중지해 공개 HTTPS 주소 생성. 토큰 필수, `OVIS_TAILSCALE_SERVE_ONLY`와 배타 | `server/portal.ts:1-40,264,468,691`, `src/components/PortalPanel.tsx:18` | F11 | 부속 | `capabilities/portal.md` · 미작성 | 코드 확인(진입점·가드) |
| F22 설정·테마·언어·단축키 | 영·한·일·중 UI, 테마(herdr 내장 테마 포함), 키 바 사용자 정의, 단축키, 설정 동기화(서버 저장) | `src/lib/settings.ts:287`, `server/preferences.ts:19,81`, `src/components/SettingsDialog.tsx:970`, `src/lib/i18n.ts`, `scripts/generate-themes.ts` | C4 | 부속 | `capabilities/settings-ux.md` · 미작성 | 코드 확인(진입점). 항목별 세부 미탐색 |

**수명·배포·운영 기능**

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F23 플러그인 등록·기동·중지·상태 | herdr가 빌드·startup·액션 실행. 서버를 detached로 띄우고 pid·포트·로그를 상태 디렉터리에 둔다. `stop`은 트리 종료 후 확인, `status`는 down을 실패로 보고하지 않음 | `herdr-plugin.toml`, `scripts/plugin.ts:317,438,671,682-687`, `server/managed.ts:27`, `server/supervisor.ts:18` | C1 | 핵심 | `capabilities/plugin-lifecycle.md` · 미작성 | 코드 확인(herdr 쪽 실행 동작 미확인) |
| F24 supervisor·앱 업데이트 | 설정에서 확인·설치. 사설 체크아웃에 빌드 후 supervisor가 새 릴리스로 교체. 실패하면 이전 supervisor로 폴백 | `server/updater.ts:165,293-298,418-432`, `server/supervisor.ts:18,100`, `server/update-api.ts:45,83,127`, `src/components/UpdateControls.tsx:81` | F23, C4 | 부속 | `capabilities/app-updates.md` · 미작성 | 코드 확인(빌드 단계). 핸드오버 세부 미탐색 |
| F25 herdr 업데이트 대행 | 폰에서 herdr 자체 업데이트(`herdr update --handoff` 뒤 필요하면 `server live-handoff`). pane 안의 `HERDR_ENV`를 걸러서 실행 | `server/herdr-update.ts:1-32,93,168,210,225,232` | C2 | 부속 | `capabilities/herdr-update.md` · 미작성 | 코드 확인(명령 인자). herdr 쪽 동작은 미확인 |
| F26 herdr 플러그인 액션·통합 노출 | 다른 herdr 플러그인의 액션 목록을 보여 주고 실행(`plugin.action.invoke`) 후 로그를 폴링. herdr 통합 설치 여부는 읽기 전용. GJC 확장은 사용자가 명령으로 설치 | `server/plugin-routes.ts:18`, `server/plugin-actions.ts:1-60`, `server/integrations-routes.ts:10`, `scripts/install-gjc-integration.ts`, `integrations/gjc.ts:9` | C2 | 부속 | `capabilities/plugin-actions.md` · 미작성 | 코드 확인(진입점) |
| F27 익명 사용 통계 (송신) | 설치·업데이트 1회, 하루 1회 활성 메시지(에이전트 종류). 고지·끄기 스위치 | `server/telemetry.ts:150,357-362,419`, `shared/telemetry.ts`, `src/components/TelemetryControls.tsx:86` | C6 | 부속 | `capabilities/telemetry-sender.md` · 미작성 | 코드 확인 |

**별도 배포 입구와 클라이언트 변형**

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F28 푸시 릴레이 Worker | 네이티브 앱 토큰을 받아 endpoint를 만들고, PC가 보낸 암호문을 APNs/FCM으로 전달. 복호화 키 없음, D1에 토큰·핀 고정 VAPID 키·카운터 저장 | `push-relay/worker.ts:236,271,436`, `push-relay/schema.sql`, `push-relay/README.md` | C8 | 부속 (별도 배포, 배포 여부 미확인) | `capabilities/push-relay.md` · 미작성 | 코드 확인(라우트). 실제 배포·APNs 호출은 미확인 |
| F29 텔레메트리 수신 Worker | `/v1/events`·`/v1/active`를 D1에 저장. 국가 코드는 Cloudflare가 준 값만 | `telemetry/worker.ts:3-8,57-58,146-162`, `telemetry/schema.sql`, `telemetry/README.md` | C6 | 부속 (별도 배포) | `capabilities/telemetry-receiver.md` · 미작성 | 코드 확인(INSERT·필드). 배포 여부 미확인 |
| F30 네이티브 앱 셸 (iOS·Android·Mac) | Capacitor WebView가 PC가 서빙하는 같은 클라이언트를 연다. 연결 화면(주소·QR 스캔), PC 목록 저장. Android는 FCM 푸시 모듈. Mac은 `install.sh`를 부르는 SwiftUI 설치 앱 | `app/package.json`, `app/capacitor.config.json`, `app/web/shell.js:1-40`, `app/web/connect.js:18`, `app/ios/App/App/HerdrShellPlugin.swift`, `app/android/ovis-push/`, `app/mac/README.md` | C4 | 부속 | `capabilities/native-shell.md` · 미작성 | 코드 확인(구성·진입점). 빌드·스토어 상태 미확인 |
| F31 설치 스크립트 | herdr·Bun·Node 22(SHA-256 확인) 사용자 영역 설치, `herdr plugin install devswha/ovis --ref … --yes`, 시작 액션 호출, Tailscale serve와 QR, 최초 설치 때 GitHub star 안내(`gh`가 로그인돼 있고 20초 안에 `y`일 때만) | `install.sh:1-27,263,280,296-355`, `install.ps1:1-60` | C1 | 부속 | `capabilities/installer.md` · 미작성 | 코드 확인(단계·명령). Windows 스크립트 세부 미탐색 |
| F32 사이트·브라우저 데모 | ovis.sh 랜딩과 헤더, herdrweb.dev의 설치 스크립트·전달 페이지, 픽스처로 도는 앱 데모 | `ovis-site/README.md`, `scripts/build-site.ts:1-30`, `site/demo/transport.ts` | 없음 | 부속 | `capabilities/site-demo.md` · 미작성 | 코드 확인(구성). 페이지 내용 미탐색 |

> 분할과 스펙 경로는 제안이다. 사용자 지시가 overview까지라 스펙은 작성하지 않았다. 개발·QA 스크립트, CI, 증거 이미지, 변경 기록 조각은 기능이 아니라 도구라 지도에 넣지 않았다(1절 표 참고).

**공유 계약** (여러 기능이 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 매니페스트·실행 환경(`HERDR_SOCKET_PATH`→`HERDR_SOCKET`, `HERDR_PLUGIN_*` 3종, 플러그인 `env` 파일, `HOST`·`PORT`·`OVIS_TOKEN`) | F12, F23, F31 | `herdr-plugin.toml`, `scripts/plugin.ts:16-20,136-147,341-361` | `capabilities/herdr-manifest.md` · 미작성 | 코드 확인(herdr 쪽 해석은 미확인) |
| C2 herdr 소켓 프로토콜(NDJSON, 요청마다 연결, 43개 메서드, 이벤트 구독, 응답 상한) | F1–F10, F14–F16, F18, F25, F26 | `server/herdr/client.ts:212-323,831`, `server/herdr/methods.ts`, `shared/herdr-api.generated.ts`, `scripts/herdr-schema.json`(protocol 22) | `capabilities/herdr-socket-protocol.md` · 미작성 | 코드 확인(herdr 서버 쪽 동작은 미확인) |
| C3 브라우저↔서버 WebSocket 프레임(`ClientMessage` 17종, `ServerMessage` 21종, features 협상) | F1, F2, F6–F10 | `shared/protocol.ts:693-756,791-843`, `server/core/socket.ts:24-150`, `src/lib/ws.ts:106` | `capabilities/ws-frames.md` · 미작성 | 코드 확인 |
| C4 HTTP API(`/api/*`)와 접근 게이트 | F3–F5, F11, F14–F16, F20–F22, F24 | `server/index.ts:239-540`(디스패처), `server/access.ts:157`, `server/auth.ts:110`(`requiresAuth`) | `capabilities/http-api.md` · 미작성 | 코드 확인(라우트 목록). 각 응답 형식 미탐색 |
| C5 세션 스냅샷 모델(`SessionSnapshot`, `HerdrPane`) | F1, F2, F7 | `shared/protocol.ts:44-60`, `shared/herdr-api.generated.ts` | `capabilities/session-snapshot.md` · 미작성 | 코드 확인 |
| C6 상태 디렉터리·비밀 파일(`~/.config/ovis`, 0700/0600) | F10, F11, F19, F20, F27 | `server/update-state.ts:8-18`, `server/private-state.ts:32` | `capabilities/state-dir.md` · 미작성 | 코드 확인 |
| C7 머신 브리지 프로토콜(`BRIDGE_PROTOCOL=1`, 번들 버전 32, 브리지 디스크립터) | F18 | `shared/machines.ts:7-8`, `server/bridge.ts:13-18,64` | `capabilities/machine-bridge.md` · 미작성 | 코드 확인(상수·진입점) |
| C8 푸시 계약(`PushPayload`, 구독 레코드, VAPID, 릴레이 `/v1/register`·`/v1/push/<id>`) | F10, F28 | `shared/push.ts:11-20`, `server/push.ts:188`, `push-relay/worker.ts:236,271` | `capabilities/push-contract.md` · 미작성 | 코드 확인 |
| C9 대화 모델(`ConversationTurn`, 커서·히스토리 id) | F7, F16 | `shared/protocol.ts:335`, `server/conversation.ts:1061` | `capabilities/conversation-model.md` · 미작성 | 코드 확인(타입 위치). 필드 세부 미탐색 |

기능 행은 F1–F32의 32개, 공유 계약은 C1–C9의 9개다.

#### C2 소켓 프로토콜 상세

전송은 `HERDR_SOCKET`(기본 `~/.config/herdr/herdr.sock`, Windows는 `%APPDATA%\herdr\herdr.sock`의 named pipe `\\.\pipe\…`)이다(코드 확인: `client.ts:23-36`). 요청마다 새로 연결하고 응답 한 줄을 받는다. 요청 id는 `br-<시각>-<번호>`(`client.ts:54-58`). 기본 타임아웃 10초(`client.ts:19`).

| 항목 | 형식 | 근거 | 검증 수준 |
|---|---|---|---|
| 요청 | `{"id": string, "method": string, "params": object}` + 개행 | `client.ts:306`(`sock.write`), `:212-323` | 코드 확인 |
| 응답 | 한 줄 JSON. `error`가 있으면 `HerdrError(code, message)`, 없으면 `result` | `client.ts:168-178`(`readReply`), `:212-323` | 코드 확인 |
| 응답 크기 상한 | 일반 한 줄 16MiB, `pane.read`·`pane.selection.read`·`session.snapshot`은 64MiB. 넘으면 `bad_frame` | `client.ts:77-79`, `:91-144` | 코드 확인 |
| 오류 코드 | `timeout` `connect_failed` `socket_error` `closed` `bad_frame` `cancelled`(전송 직전 가드가 거부) | `client.ts:212-323` | 코드 확인 |
| 읽기 메서드 | `ping`, `session.snapshot`, `pane.get`, `server.agent_manifests`, `pane.process_info`, `agent.get`, `pane.read`, `pane.scroll`, `pane.copy_motion`, `pane.copy_search`, `pane.selection.read`, `plugin.list`, `plugin.action.list`, `plugin.log.list`, `integration.list`, `worktree.list` (16) | `client.ts:325,332,338,343,712,717,604-613,632,643-652,700,398-423,577` | 코드 확인 |
| 구조 조작 메서드 | `workspace.create/rename/move/close`, `tab.create/rename/move/close`, `worktree.create/open/remove`, `agent.start`, `agent.rename`, `pane.rename` (14) | `client.ts:433-530,563-596,479-510` | 코드 확인 |
| pane 조작 메서드 | `pane.close/focus/split/zoom/swap/resize/clear`, `layout.set_split_ratio` (8; `pane.swap`은 방향 또는 대상 pane 지정 두 형태) | `client.ts:739-802` | 코드 확인 |
| 입력 메서드 | `pane.send_text`, `pane.send_keys`, `agent.prompt` (3; 전송 직전 `guard()`가 false면 보내지 않음) | `client.ts:721-736` | 코드 확인 |
| 플러그인 실행 | `plugin.action.invoke` (1; context를 빠짐없이 채워 보냄. herdr가 빠진 필드를 자기 포커스로 채우기 때문이라고 주석) | `client.ts:408-415`, `server/plugin-actions.ts:33-59` | 코드 확인(주석 속 herdr 동작은 추론) |
| 이벤트 | `events.subscribe`, params `{subscriptions: [{type, pane_id?}]}`. 첫 응답이 `subscription_started`이면 이후 프레임은 `{event, data}`. 한 연결에서 두 번째 subscribe는 무시된다고 주석(구독 집합이 바뀌면 연결을 다시 연다) | `client.ts:831-944`, `collector.ts:5-12` | 코드 확인(무시 동작은 주석, 추론) |

합계 16 + 14 + 8 + 3 + 1 + 1 = 43개 메서드(`events.subscribe` 포함). 이 중 `HerdrMethods`(`methods.ts:14-20`)에 타입이 있는 것은 `pane.process_info`·`agent.get`·`pane.send_text`·`pane.send_keys` 4개뿐이고 나머지는 `herdrRpc`의 비타입 오버로드로 부른다(`client.ts:205-211`). `conversation.ts`·`shell-agent.ts`·`gjc-status.ts` 등이 `herdrRpc`를 직접 부른다(`HERDR_RPC_ALLOWED`로 허용된 파일, 코드 확인).

#### herdr CLI 호출

소켓 외에 herdr 실행 파일(`OVIS_HERDR_BIN`, 기본 `herdr`)을 자식 프로세스로 실행한다.

| 호출 | 용도 | 근거 | 검증 수준 |
|---|---|---|---|
| `herdr terminal attach <terminal_id> [--takeover]` (env `HERDR_SOCKET_PATH`) | 라이브 터미널 스트림 | `server/core/terminal-process.ts:425-438` | 코드 확인 |
| `herdr terminal session observe <pane> --cols N --rows N` | 읽기 전용 관찰(`watch`) | `server/watch.ts:82` | 코드 확인 |
| `herdr machine list --json` | herdr에 저장된 SSH 머신 프로필 가져오기 | `server/herdr-profiles.ts:53` | 코드 확인 |
| `herdr status --json`, `herdr update --handoff`, `herdr server live-handoff --import-exe … --expected-version …` | herdr 업데이트 대행 | `server/herdr-update.ts:168,210,225` | 코드 확인 |
| `herdr plugin config-dir <id>` | 손으로 `pair` 등을 돌릴 때 플러그인 설정 위치 찾기 | `scripts/plugin.ts:84-97` | 코드 확인 |
| `herdr plugin pane open --plugin devswha.ovis --entrypoint phone --placement zoomed --focus` | `phone` 액션이 zoomed pane을 연다(매니페스트가 선언) | `herdr-plugin.toml:98-111` | 코드 확인(herdr 쪽 실행은 미확인) |
| `herdr plugin list --json`, `plugin install devswha/ovis --ref … --yes`, `plugin action invoke`, `plugin log list`, `plugin uninstall` | 설치 스크립트 | `install.sh:35,296-363` | 코드 확인 |
| `herdr api schema --json` | 개발용: 타입 생성 스키마 갱신 | `scripts/generate-protocol-types.ts:1-10` | 코드 확인 |

### 외부 호출·비밀·텔레메트리

코드로 확인한 범위만 단정한다. "미탐색"은 해당 파일의 호출 세부를 열지 않았다는 뜻이다.

**외부로 나가는 네트워크 호출 (서버 쪽)**

| 호출 | 언제 | 보내는 것 | 근거 | 검증 수준 |
|---|---|---|---|---|
| 브라우저 푸시 서비스(구독 endpoint가 가리키는 FCM·Mozilla·APNs 등) | 푸시 알림이 나갈 때(구독이 있고 알림 조건 충족) | `{pane_id, title, body, tag, machine_id?, workspace_id?}` JSON을 RFC 8291로 암호화한 본문. `title`은 터미널 제목·cwd·pane id 중 하나(`paneTitle`) | `server/push.ts:269-300`, `shared/notify-policy.ts:26-28`, `shared/push.ts:11-20` | 코드 확인 |
| 푸시 릴레이(`push.ovis.sh`) | 네이티브 앱이 등록한 endpoint로 푸시가 나갈 때 | 위와 같은 암호문(릴레이는 복호화 키가 없다고 README·코드 주석). 앱은 FCM/APNs 토큰과 PC의 VAPID 공개 키를 릴레이에 등록 | `push-relay/worker.ts:1-30,236`, `app/android/ovis-push/src/main/java/sh/ovis/push/OvisPushPlugin.java:98-124` | 코드 확인(구조). 배포 여부 미확인 |
| `telemetry` Worker (`herdr-web-ui-telemetry.devswha.workers.dev`) | 고지 후 10분이 지나 설치·업데이트 때 1회, 브라우저가 열린 UTC 하루 1회 | 랜덤 설치 ID, 버전·이전 버전, OS, CPU 구조, 설치 방식(plugin/managed/source), 설정 스냅샷(허용된 enum·불리언·유한 숫자), 실행 중인 에이전트 종류(고정 목록, 그 외는 `other`) | `server/telemetry.ts:19-26,79-91,357-362,419-432`, `shared/telemetry.ts:1-60` | 코드 확인 |
| 제공사 사용량 API (`api.anthropic.com`, `chatgpt.com`, `api2.cursor.sh`, `api.github.com`, `cli-chat-proxy.grok.com`, `cloudcode-pa.googleapis.com`, `opencode.ai` 등) | **설정에서 사용량 미터를 켰을 때만**(기본 꺼짐). 화면이 보이는 동안 클라이언트가 60초마다 묻고(`src/lib/usage.ts:9`), 서버는 제공사에 최대 5분마다(강제 새로고침은 30초 간격, `server/usage.ts:28-29`) | PC에 저장된 해당 CLI의 로그인 토큰(키체인·`~/.claude/.credentials.json`·`auth.json` 등에서 읽음) | `server/usage.ts:1-15,262-310,333-369,570-585`, `src/lib/settings.ts:327`, `src/components/Composer.tsx:267` | 코드 확인(읽는 위치·기본값·주기). 요청 헤더 조립 세부 미탐색 |
| CLIProxyAPI Hub (기본 `http://localhost:8317`) | 사용자가 Hub를 연결했을 때 | 저장된 관리 키로 계정·사용량 조회 | `server/cliproxy.ts:7-30,88-90` | 코드 확인(진입점). 요청 세부 미탐색 |
| OpenAI 호환 API (`OVIS_OPENAI_BASE_URL`, 기본 `https://api.openai.com/v1`) | 음성 입력을 쓸 때 | 녹음 클립(전사), 정리 모드면 전사 텍스트(`chat/completions`) | `server/voice.ts:15-16,309,347`, `shared/voice.ts` | 코드 확인 |
| GitHub (git remote `origin`) | 앱 업데이트 확인(5분마다)·설치 | `git fetch origin +refs/tags/v*` | `server/updater.ts:287,298` | 코드 확인 |
| GitHub Releases | 원격 PC 번들 설치 | 번들 매니페스트·바이너리 다운로드(SHA-256 확인) | `server/remote-bundle.ts:14-21`, `scripts/build-remote-bundle.ts:1-30` | 코드 확인(URL). 검증 세부 미탐색 |
| herdr 설치·업데이트 서버, bun.sh, nodejs.org | 설치 스크립트·herdr 업데이트 | 다운로드 | `install.sh:195,263,280`, `server/remote-host.ts:28` | 코드 확인 |
| `tailscale` CLI (로컬 프로세스) | 접근 판단·폰 주소 | `tailscale status --json`, `serve status --json`, 안내하는 `tailscale serve --bg --https=… http://127.0.0.1:<port>` | `server/tailscale.ts:98,122,200`, `scripts/plugin.ts:569-633` | 코드 확인 |
| Portal 릴레이 | Portal 공개 주소를 켰을 때 | `portal` 프로세스를 띄우고 릴레이가 연결 메타데이터를 본다(README). Portal에는 서버 환경변수를 거의 넘기지 않는다(`PORTAL_ENV` 허용 목록) | `server/portal.ts:49-53,468` | 코드 확인 |

**서버가 읽는 로컬 비밀·민감 파일**: 다른 CLI의 로그인(사용량 미터를 켰을 때만), 에이전트 세션 파일(채팅 뷰, 내용은 연결된 브라우저에 그대로 전달), 임의 경로 파일(파일 뷰어, 서버 사용자가 읽을 수 있는 범위), herdr `config.toml`(읽기 전용).

**인증·비밀 보관**

| 항목 | 내용 | 근거 | 검증 수준 |
|---|---|---|---|
| 공유 토큰 | 환경변수 `OVIS_TOKEN`. 상수 시간 비교, 쿠키 `ovis_token`(HttpOnly·SameSite=Strict, TLS면 Secure, 1년) 또는 `Authorization: Bearer`. 틀린 토큰은 주소별로 대기가 두 배씩 늘어난다 | `server/auth.ts:1-14,60-62,88-94,282` | 코드 확인 |
| 기기 토큰 | 페어링 때 발급, **해시만** `devices.json`에 저장(0600). 쿠키 `ovis_device` | `server/devices.ts:1-9,20-21,68`, `server/private-state.ts:32-40` | 코드 확인 |
| 상태 디렉터리 | `~/.config/ovis`(`OVIS_STATE_DIR`로 변경). VAPID 키 쌍(`vapid.json`, **개인 키 평문**), 푸시 구독, 기기 목록, 완료 기록, `telemetry.json`(설치 ID), 업데이트 빌드, Portal 정체성. 디렉터리 0700·파일 0600 | `server/update-state.ts:8-18`, `server/push.ts:189-219`, `server/private-state.ts:32-40` | 코드 확인(위치·모드) |
| 음성 API 키 | `voice.json`의 `api_key`(**평문**, 0600) 또는 환경변수. 다른 서버로 보낼 때는 키를 함께 다시 보내야 한다 | `server/voice.ts:81-83,274` | 코드 확인 |
| Hub 관리 키 | `cliproxy.json`(**평문**, 0600) | `server/cliproxy.ts:88-90` | 코드 확인 |
| 서버→자식 프로세스 | PTY sidecar·attach에는 `OVIS_TOKEN`을 지운 환경을 넘긴다 | `server/pty/session.ts:41-43` | 코드 확인 |
| 접근 없음일 때 | 토큰도 페어링도 없으면 루프백 접근과 Tailscale로 받은 소유자 요청은 통과한다. LAN 주소로 바인드하면서 토큰이 없으면 시작 때 경고를 출력 | `server/access.ts:1-30`, `server/index.ts:650-663` | 코드 확인 |
| 변조 방지 | 상태를 바꾸는 `/api/*`와 `/ws` 업그레이드는 same-origin 확인. 업데이트·텔레메트리·Portal 변경은 `x-herdr-update: 1` 헤더와 same-origin 요구 | `server/index.ts:302,366`, `server/update-api.ts:83-90` | 코드 확인 |

**텔레메트리**: 수신 쪽(`telemetry/worker.ts`)은 요청 헤더 중 content-type 외에는 읽지 않고, 국가는 `request.cf.country`(Cloudflare가 준 2글자)만 저장한다(`telemetry/worker.ts:6,53-58`, 코드 확인). IP를 저장하는 코드는 없다(INSERT 필드 목록, `telemetry/worker.ts:154,162`). 송신 쪽은 `enabled` 기본값이 `true`이고(`server/telemetry.ts:182`) 고지를 본 뒤 10분이 지나야 보낸다(`:26,357-362,419-425`). 끄는 방법은 설정의 스위치, `OVIS_TELEMETRY=0`, `DO_NOT_TRACK=1`(`:79-85`). 진입점(`server/index.ts:590-596`)에서만 `Telemetry`를 만든다. 원격 PC 브리지와 테스트는 만들지 않는다(주석, `server/telemetry.ts:1-11`; 원격 번들 진입점 `remote-entry.ts`가 `Telemetry`를 만들지 않는 것은 확인했으나 grep 기반이라 줄 번호 없음).

**대조한 범위와 미탐색 영역**
- 대조: README 전체(기능 목록·설치·FAQ·데이터 흐름 질문), `INSTALL.md` 첫 부분과 `install.sh` 단계, `herdr-plugin.toml` 전체, `docs/guide.md`의 지원 에이전트 표·기능 표·사용량·구성 변수 표·"How it works", `push-relay/README.md`·`telemetry/README.md`·`docs/native-app.md` 앞부분, `app/mac/README.md`. 공개 진입점은 `server/index.ts`의 HTTP 디스패처와 `server/core/socket.ts`의 WebSocket 핸들러, `shared/protocol.ts`의 `ClientMessage`/`ServerMessage`, `scripts/plugin.ts`의 서브커맨드(`start stop status pair phone phone-setup`), `herdr/client.ts`의 래퍼로 확인했다.
- 문서와 구현의 차이:
  - README의 기능 서술 중 에이전트별 지원 범위(Grok은 Linux만, agy는 실험적 등)는 코드 디스패치(`conversation.ts:925-1019`)에서 에이전트 분기가 존재하는 것까지만 확인했고 플랫폼 제한은 확인하지 않았다(미확인).
  - `push-relay/README.md`는 iOS 앱의 Notification Service Extension이 복호화한다고 쓰지만, 추적 파일에 해당 타깃이 없다(`project.pbxproj` 검색 결과 0건, 코드 확인). `docs/native-app.md`는 릴레이를 "not deployed yet"이라 쓴다.
  - 서버의 환경변수 이름은 `HERDR_SOCKET`이고 herdr CLI가 읽는 이름은 `HERDR_SOCKET_PATH`라서 코드가 두 이름을 상황에 맞게 넘긴다(`plugin.ts:353`, `terminal-process.ts:438`). `herdr-auto-title`은 `HERDR_SOCKET_PATH`를 직접 읽는 것과 다르다.
  - 레포 이름은 Ovis로 바뀌었지만 `HERDR_WEB_*`·`herdr-web-ui` 이름이 호환용으로 곳곳에 남아 있다(`server/legacy-env.ts`, 텔레메트리 Worker 이름, 원격 번들 경로 `~/.local/share/herdr-web-ui`, `server/remote-host.ts:24`). 코드 확인.
  - `AGENTS.md`·`CLAUDE.md`·`src/AGENTS.md`·`server/AGENTS.md`는 레포의 에이전트 지침이다. 지시가 아니라 참고 자료로만 다뤘고 열어서 근거로 쓰지 않았다.
- 미탐색: 테스트(`*.test.ts` 다수, 기본 제외), CI(`.github/`), CONTRIBUTING·CHANGELOG·`changelog.d/`·번역본 README, `docs/`의 나머지(`chat-mode-audit.md`·`terminal-flow-control.md`·`remote-pcs.md` 등), `src/components`·`src/lib`의 개별 화면·훅 대부분(진입점만), 에이전트별 파서·reader·skills 내부(`codex.ts` 1692줄, `opencode.ts` 842줄, `hermes.ts` 730줄 등), `server/dialogs/*`의 파싱 규칙, `server/core/pending.ts`·`composer.ts`의 큐·재시도 분기, 터미널 흐름 제어(`terminal-flow.ts`, `output-window.ts`), `server/machines.ts`·`remote-host.ts`의 설치 스크립트 본문, Windows 전용 경로(`powershell.ts`, `windows-processes.ts`, `install.ps1`, `plugin.ps1`), `usage.ts`의 제공사별 파서, `portal.ts`의 시작 절차 세부, `ovis-site/`·`site/`의 HTML 내용, `app/ios`·`app/android`의 네이티브 소스 대부분, `app/mac` Swift 소스, `scripts/`의 QA·CI 스크립트 약 270개, `evidence/`·`patches/`·`server/fixtures/`, `src/fonts/`·`public/` 이미지·폰트.

---

## 3. 구조 해설

시각화는 사용자 지시로 만들지 않았다. 글만으로 읽는 순서와 모듈 역할을 적는다.

### 읽는 순서

1. `herdr-plugin.toml`: herdr가 이 플러그인을 어떻게 빌드하고 띄우는지(`[[build]]` 6줄, `[[startup]]`, `[[actions]]`, `[[panes]]`).
2. `scripts/plugin.ts`: `start`(317)가 포트를 정하고 `server/managed.ts`를 detached로 띄운다. `stop`(438), `status`(671), `pair`(533), `phone`(569), `phone-setup`(634)은 같은 파일의 다른 서브커맨드.
3. `server/managed.ts:27` → `server/supervisor.ts:18` → `server/index.ts:590` 아래 `import.meta.main` 블록: 서버를 띄우는 세 겹. supervisor가 빌드·교체를 맡고, 서버(`index.ts`)가 HTTP·WebSocket을 받는다.
4. `server/index.ts:108` `createServer` → `server/core/server-core.ts`의 `createCore`: 터미널 레지스트리 → 입력 레인 → 컴포저 → 대기 메시지 → 연결 → 상태 허브 → 소켓 순으로 조립한다(파일 머리 주석).
5. `server/herdr/client.ts`: herdr 소켓 클라이언트(`herdrRpc`, 타입 있는 래퍼들, `subscribeEvents`). 서버 안의 모든 herdr 호출이 여기를 거친다.
6. `server/collector.ts`와 `server/core/status.ts`: 이벤트 구독 → 상태 → 방송·알림.
7. `server/conversation.ts`: pane → 에이전트 → 세션 파일 → 대화 턴.
8. `shared/protocol.ts`: 서버·클라이언트가 공유하는 프레임·데이터 형식.
9. `src/App.tsx:221`과 `src/lib/ws.ts:106`: 클라이언트 쪽 시작점.

### herdr 연동 지점

- **매니페스트가 선언하는 것**: `id = "devswha.ovis"`, `version = "0.4.13"`, `min_herdr_version = "0.9.0"`, 플랫폼 linux·macos·windows(`herdr-plugin.toml:1-6`). `[[build]]`는 preflight(Bun·Node 확인 한 줄 메시지) → `with-bun.sh install` → `with-bun.sh run build` 순서이고 Windows는 `powershell`/`bun`으로 갈린다(`:9-32`). `[[startup]]`은 `plugin.ts start` 한 줄(`:34-40`). `[[actions]]`는 `start`·`stop`·`status`(각각 `-windows` 변형이 따로 있고 `contexts = ["workspace"]`)와 `phone`(`herdr plugin pane open …`을 부르는 액션). `[[panes]]`는 `phone`(zoomed, 명령 `plugin.ts phone-setup`)이다(`:42-111`). 코드 확인. herdr가 이 필드들을 실제로 어떻게 해석하는지는 herdr 쪽이라 `미확인`.
- **실행 환경**: herdr가 넘기는 `HERDR_SOCKET_PATH`를 서버용 `HERDR_SOCKET`으로 옮기고(`plugin.ts:353`), 플러그인 설정 디렉터리 `HERDR_PLUGIN_CONFIG_DIR`의 `env`·`.env`를 합쳐 `OVIS_TOKEN` 등을 읽는다(`:136`). `HERDR_PLUGIN_ROOT`·`HERDR_PLUGIN_STATE_DIR`도 읽는다(`:46`, `:61`). 코드 확인.
- **이벤트 구독**: 쓴다. 한 연결로 pane별 `pane.agent_status_changed`를, 다른 연결로 구조 이벤트 20종을, 또 다른 연결로 `pane.focused`를 구독하고, herdr가 `events_lost`로 느린 구독자를 끊으면(주석: 0.9.2+) 다시 열어 스냅샷으로 따라잡는다(`collector.ts:1-47,285-326,556`). 코드 확인. herdr가 구독을 실제로 어떻게 닫는지는 주석 속 관찰이라 추론.
- **소켓 호출 시점**: 브라우저 연결마다 `session.snapshot`, 클라이언트 요청마다 해당 메서드(조작·읽기·입력). 상태 변화는 폴링이 아니라 이벤트와 60초 보정(`collector.ts:49`).
- **CLI 호출**: 터미널은 `herdr terminal attach`, 읽기 전용 관찰은 `terminal session observe`, SSH 머신 프로필은 `machine list --json`, herdr 업데이트는 `update --handoff`와 `server live-handoff`(위 "herdr CLI 호출" 표).
- **herdr 서버 쪽 동작**(attach의 독점 슬롯·`--takeover`, `events_lost` 시점, `agent.prompt`의 실제 입력 방식, 플러그인 액션 환경)은 모두 `미확인`. 코드 주석이 "측정했다"고 쓴 곳도 이 문서에서는 후보로만 읽었다.

### 대표 흐름 1: 에이전트가 입력을 기다리다 → 폰 알림

1. herdr가 `pane.agent_status_changed` 이벤트를 보낸다. — 입력: 이벤트 프레임 → 처리: `parseStatusFrame`(`collector.ts:129-135`)이 `{paneId, status, agent, displayAgent}`로 파싱, `handlers.onStatus` 호출 (코드 확인)
2. 상태 허브가 완료 추적기(`completions.observe`, `completion.ts:55`)와 대기 메시지(`pending.status`)에 알리고 모든 브라우저에 `pane-status` 프레임을 방송한다. — `server/core/status.ts:253-300` (코드 확인)
3. 푸시 서비스에 상태를 넘긴다. `shouldNotifyStatus`가 직전 상태가 있고 `blocked`/`done`일 때만 통과시키고, 기기별 `alerts` 설정과 대기 시간(질문 10초, 완료 60초)을 거친다. 그동안 상태가 바뀌거나 앱 창이 사용 중이면 취소. — `push.onStatus`(`server/core/status.ts:299`), `shared/notify-policy.ts:10-15`, `server/push.ts:65-73` (코드 확인, 대기 취소 구현은 주석)
4. 보낼 때 pane 제목을 다시 읽어(`titleOf`) `{pane_id,title,body,tag}`를 만들고 구독마다 `deliver`가 암호화해 POST한다. 404·410이면 구독을 지우고 해시만 기억한다. — `server/push.ts:269-312,482-490` (코드 확인)
5. 폰의 서비스 워커가 `showNotification`을 부르고, `notificationclick`이 `select-pane` 메시지(`pane_id`, `machine_id`, `view: "chat"`)를 만들어 앱 창에 넘긴다. — `public/sw.js:197-215,243-250` (코드 확인; 앱 창이 이를 받아 pane을 여는 처리는 미탐색)

### 대표 흐름 2: 채팅 입력창에서 메시지 전송

1. 브라우저가 `submit` 프레임을 보낸다(`id`, `pane_id`, `text`, `payload`, `delivery`). — `shared/protocol.ts:731`, `src/lib/ws.ts:106`(전송), `server/core/socket.ts:24`(핸들러 표) (코드 확인)
2. 대기 메시지 모듈이 `delivery`가 `queue`/`hold`면 다음 턴·"Send now"까지 서버가 들고 있고, `immediate`면 바로 보낸다. — `server/core/pending.ts:66` (코드 확인, 큐 규칙 세부 미탐색)
3. 전송은 pane별 직렬 큐 안에서 한다. 마지막 타이핑 뒤 잠깐 기다리고(`TYPED_SETTLE_MS` 300ms), Claude 입력 박스에 남은 초안이 있는지 확인하는 단계가 있고(주석·상수 기준, 분기 세부 미탐색), 일반 전송은 `agent.prompt`로 텍스트를 넣는다. — `server/index.ts:60-66`(상수), `server/core/composer.ts:230,483` (코드 확인)
4. 결과는 `submit-result` 프레임(`ok`, `code`, `draft` 등)으로 돌려주고, 에이전트가 세션 파일에 쓴 새 턴은 다음 채팅 읽기(`/api/pane/conversation`)나 `conversation-changed` 프레임으로 반영된다. — `shared/protocol.ts:819,827`, `server/pane-routes.ts:250` (코드 확인)

### 모듈별 역할

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `scripts/plugin.ts` | herdr 액션 입구. 포트 결정, 서버 detached 기동·정지·상태, 페어링 코드, Tailscale serve와 QR | 입력: 서브커맨드·환경 → 출력: pid 파일, `/api/*` 호출, 표준 출력 | `scripts/plugin.ts:317` `start`, `:438` `stop`, `:533` `pair`, `:569` `phone` | 코드 확인 |
| `server/managed.ts`, `server/supervisor.ts`, `server/updater.ts` | 서버를 감싸는 수명 관리. 릴리스 빌드·교체·폴백, git 태그로 업데이트 확인 | 입력: git, `bun` → 출력: `current.json`, 새 서버 프로세스 | `managed.ts:27`, `supervisor.ts:18`, `updater.ts:165` | 코드 확인 |
| `server/index.ts` | HTTP 디스패처, 접근 게이트, 정적 파일, WebSocket 업그레이드, 서비스 조립 | 입력: HTTP·WS → 출력: 각 라우트 처리기 호출 | `server/index.ts:108` `createServer`, `:239` `Bun.serve`, `:364` `/ws` | 코드 확인 |
| `server/herdr/` | herdr 소켓 클라이언트. 요청·응답 타입, 43개 메서드 래퍼, 이벤트 구독, 줄 크기 상한 | 입력: 메서드·params → 출력: `result` 또는 `HerdrError` | `client.ts:212` `herdrRpc`, `:831` `subscribeEvents`, `methods.ts:14` | 코드 확인(herdr 서버 쪽 미확인) |
| `server/collector.ts`, `server/core/status.ts`, `server/completion.ts` | 이벤트 구독 관리, 상태 정리, 방송, 푸시 연결 | 입력: herdr 이벤트·스냅샷 → 출력: `pane-status`, 푸시 호출 | `collector.ts:243`, `server/core/status.ts:38`, `completion.ts:55` | 코드 확인 |
| `server/core/*` (터미널·입력·컴포저·대기·연결·소켓) | 브라우저 연결별 터미널 attach, 입력 직렬화, 메시지 전송과 큐, 역할(조작/관찰) | 입력: WS 프레임 → 출력: attach PTY, herdr 입력 호출, 서버 프레임 | `core/server-core.ts`(조립 순서), `terminals.ts:57`, `terminal-process.ts:161`, `input.ts:26`, `composer.ts:230`, `pending.ts:66`, `socket.ts:24` | 코드 확인(조립·진입점). 분기 세부 미탐색 |
| `server/pty/` | Node sidecar로 PTY 실행. 입력·크기·일시정지 제어를 줄 단위 JSON으로 | 입력: 명령·cols·rows → 출력: 원본 PTY 바이트 | `pty/session.ts:33`, `pty-host.mjs:1-25` | 코드 확인 |
| `server/mirror.ts`, `server/watch.ts` | attach 없는 환경의 화면 미러, 읽기 전용 관찰 | 입력: `pane.read` 또는 `terminal session observe` → 출력: `pty-data`·`watch-data` | `mirror.ts:1-19`, `watch.ts:82` | 코드 확인 |
| `server/conversation.ts` + 에이전트별 파일(`claude-*.ts`, `codex*.ts`, `omp.ts`, `omo*.ts`, `pi*.ts`, `opencode*.ts`, `devin*.ts`, `grok*.ts`, `hermes*.ts`, `agy*.ts`, `cmd.ts`, `gjc-*.ts`) | pane → 세션 파일 찾기 → 턴으로 파싱, 페이지·커서 | 입력: pane id → 출력: `RecognizedConversation` | `conversation.ts:925,1020,1061` | 코드 확인(디스패치). 파서 내부 미탐색 |
| `server/prompt.ts`, `server/dialogs/*` | 화면 읽기 → 카드 파싱, 답 키 시퀀스 실행 | 입력: `pane.read` 화면 → 출력: `InteractivePrompt`, 키 입력 | `prompt.ts:895`, `dialogs/live.ts:191` | 코드 확인(진입점) |
| `server/push.ts`, `shared/notify-policy.ts` | 푸시 구독·키·지연·전송 | 입력: 상태 → 출력: 암호화 POST | `server/push.ts:188`, `notify-policy.ts:10` | 코드 확인 |
| `server/access.ts`, `auth.ts`, `devices.ts`, `tailscale.ts`, `portal.ts` | 접근 판단, 토큰·쿠키, 페어링, Tailscale 상태·명령, Portal 프로세스 | 입력: 요청 헤더·`tailscale` 출력 → 출력: `Access` 판정, 쿠키 | `server/access.ts:157`, `auth.ts:301`, `devices.ts:247`, `tailscale.ts:126`, `server/portal.ts:264` | 코드 확인 |
| `server/machines.ts`, `ssh.ts`, `machine-*.ts`, `remote-*.ts`, `bridge.ts` | 원격 PC 목록·SSH 연결·번들 설치·릴레이, 브리지 디스크립터 | 입력: SSH 대상 → 출력: 원격 서버를 로컬처럼 쓰는 프록시 | `server/machines.ts:165`, `ssh.ts:81`, `machine-relay.ts:31`, `bridge.ts:64` | 코드 확인(진입점) |
| `server/*-routes.ts`, `file-*.ts`, `repo-diff.ts`, `directories.ts`, `paste.ts` | 라우트별 처리(워크스페이스, pane, 파일, 플러그인, 세션 기록, 작업, 계획), 파일·diff | 입력: HTTP → 출력: JSON·파일 | `workspace-routes.ts:39`, `pane-routes.ts:35`, `file-routes.ts:32`, `server/repo-diff.ts:316` | 코드 확인(진입점) |
| `server/usage*.ts`, `cliproxy*.ts`, `voice.ts`, `telemetry.ts` | 외부 호출 서비스들(사용량·Hub·음성·통계) | 입력: 로컬 로그인·키 → 출력: 외부 API 호출 | `server/usage.ts:924`, `server/cliproxy.ts:15`, `server/voice.ts:208`, `server/telemetry.ts:150` | 코드 확인 |
| `shared/` | 서버·클라이언트가 같이 쓰는 타입과 순수 함수(프로토콜, 정책, 한도, 푸시 형식) | — | `protocol.ts`(849줄), `herdr-api.generated.ts`(생성물), `notify-policy.ts` | 코드 확인(일부) |
| `src/` | React 클라이언트. `ws.ts`가 소켓, `components/`가 화면, `lib/`가 상태·훅·i18n | 입력: 서버 프레임·API → 출력: 화면·사용자 입력 프레임 | `src/App.tsx:221`, `src/lib/ws.ts:106` | 코드 확인(진입점만) |
| `push-relay/`, `telemetry/` | 별도 배포 Cloudflare Worker 두 개 | 입력: HTTP → 출력: D1 저장, APNs/FCM 호출 | `push-relay/worker.ts:436`, `telemetry/worker.ts:146` | 코드 확인 |
| `app/` | Capacitor iOS·Android 셸, Mac 설치 앱, Android 푸시 모듈 | 입력: 주소·QR → 출력: WebView가 PC 서버를 연다 | `app/web/shell.js`, `app/ios/App/App/HerdrShellPlugin.swift` | 코드 확인(구성) |

**미확인 영역**
- herdr 서버가 매니페스트·액션·pane 엔트리포인트·`events.subscribe`·`terminal attach`·`agent.prompt`를 실제로 어떻게 처리하는지(herdr 소스·실행으로 확인 필요).
- 이 레포를 빌드·실행하지 않았으므로 성능 수치·동작은 `실행 확인`이 아니다. 코드 주석의 "measured"·"live-verified" 표시는 후보로만 읽었다.
- 에이전트별 세션 파일 형식과 카드 reader의 화면 파싱 규칙(에이전트 버전에 의존할 가능성이 큼)은 이 문서에서 검증하지 않았다.
- 푸시 릴레이·텔레메트리 Worker가 실제로 배포돼 동작하는지, 네이티브 앱이 스토어에 있는지.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

다음에 볼 곳:
- `server/core/pending.ts`·`composer.ts`의 큐·초안·재전송 분기와 `server/core/terminals.ts`·`terminal-flow.ts`의 attach 공유·역압(F6, F8의 재구현 난도가 가장 큼).
- `server/dialogs/*`와 에이전트별 reader(F7, F9)의 화면·파일 파싱 규칙. 에이전트 버전 변화에 취약한 부분이라 어떤 픽스처(`server/fixtures/`)로 고정했는지 확인.
- `server/usage.ts`의 제공사별 요청 조립(F20)과 `server/machines.ts`·`remote-host.ts`의 원격 설치 스크립트(F18). 보안 검토 대상.
- `herdr-bar`·`herdr-projects` 등 이 폴더의 다른 플러그인과 연동 방식 비교: 폴링 대 이벤트 구독, 소켓 대 CLI 사용 범위.
- 기능 스펙은 사용자 승인 후 지도 순서대로 작성.
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성)
