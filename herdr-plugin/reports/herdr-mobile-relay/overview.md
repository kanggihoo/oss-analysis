---
sha: "278b8c2697e47d9b3da0e0e311841123b78226de"
created: 2026-10-24
updated: 2026-10-24
sources:
  - herdr-plugin.toml
  - README.md
  - QUICKSTART.md
  - LICENSE
  - go.mod
  - Dockerfile.gateway
  - install.sh
  - Makefile
  - relay/plugin-build.sh
  - relay/plugin-on-event.sh
  - relay/open-plugin-pane.sh
  - relay/plugin-setup-menu.sh
  - relay/start.sh
  - relay/herdr-mobile-relay-service.sh
  - relay/common.sh
  - relay/pi-commands.sh
  - relay/pi-command-bridge/bridge.mjs
  - cmd/herdr-mobile-relay/main.go
  - cmd/herdr-gateway/main.go
  - cmd/fake-herdr/main.go
  - internal/config/config.go
  - internal/eventhook/eventhook.go
  - internal/herdr/client.go
  - internal/herdr/events.go
  - internal/herdr/capabilities.go
  - internal/herdr/socket_api.go
  - internal/herdr/send_input.go
  - internal/herdr/literal_key.go
  - internal/app/server.go
  - internal/app/hybrid.go
  - internal/app/pane_watch.go
  - internal/app/uploads.go
  - internal/coordinator/poller.go
  - internal/coordinator/udp.go
  - internal/coordinator/dispatch.go
  - internal/coordinator/approval.go
  - internal/coordinator/lifecycle.go
  - internal/protocol/protocol.go
  - internal/question/attention.go
  - internal/question/parser.go
  - internal/transport/auth.go
  - internal/transport/e2ee.go
  - internal/transport/gateway.go
  - internal/deviceauth/store.go
  - internal/deviceauth/resolver.go
  - internal/gateway/server.go
  - internal/gateway/probe.go
  - internal/gatewaywire/gatewaywire.go
  - internal/push/manager.go
  - internal/panesize/manager.go
  - internal/conversation/reader.go
  - internal/workspace/inspector.go
  - internal/fsutil/listdir.go
  - internal/speech/speech.go
  - internal/speech/voices.go
  - internal/update/manager.go
  - internal/update/worker.go
  - internal/appdeploy/worker.go
  - internal/pibridge/client.go
  - internal/web/handler.go
  - internal/setuphelper/setuphelper.go
  - internal/childenv/command.go
  - internal/audit/logger.go
  - frontend/package.json
  - frontend/src/main.ts
  - relay/setup.sh
  - relay/stable-setup.sh
  - relay/change-hostname.sh
  - docs/security.md
  - docs/transports.md
  - docs/pane-size-leasing.md
  - docs/mobile-app.md
  - docs/slash-command-discovery.md
  - docs/agent-directories.md
  - internal/release/manifest.go
  - internal/activity/journal.go
  - internal/history/history.go
  - internal/support/support.go
  - internal/upload/upload.go
  - internal/slashcmd/catalog.go
  - internal/copyresponse/copy.go
  - internal/clipboard/clipboard.go
  - internal/agentroots/agentroots.go
  - internal/sqliteexec/exec.go
  - internal/profiles/resolver.go
  - internal/webrtclink/manager.go
  - internal/portmap/portmap.go
  - internal/app/pi_commands.go
  - internal/push/policy.go
  - internal/push/payload.go
  - internal/panesize/terminal_unix.go
  - internal/update/stage.go
  - internal/appdeploy/manager.go
  - internal/gateway/relay.go
  - internal/gateway/client.go
  - internal/transport/ws.go
  - frontend/src/lib/device-auth.ts
  - frontend/src/lib/security.ts
---

# herdr-mobile-relay Analysis Overview

범례: 검증 수준은 `코드 확인`(구현부를 직접 읽음) / `추론` / `미확인`. 이 문서는 실행하지 않고 읽기만 했으므로 `실행 확인`은 없다. 경로는 모두 `repos/herdr-mobile-relay/` 기준이고, `파일:줄`은 기준 SHA에서 직접 열어 확인한 줄이다. README·docs·AGENTS.md는 후보로만 읽었고, 코드로 확인한 것만 표에 옮겼다.

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/0cv/herdr-mobile-relay` (`artifacts/herdr-mobile-relay/repo-metadata.txt`)
- **기준 SHA**: `278b8c2697e47d9b3da0e0e311841123b78226de` (commit 2026-10-23, main)
- **작업트리 상태**: Clean (repo-metadata.txt, 추적 파일 876개)
- **분석 목적**: 학습·도입 검토. (1) herdr 플러그인이 `herdr-plugin.toml`과 herdr 소켓·CLI로 어떻게 연동하는지, (2) 폰에서 에이전트를 보고 조작하는 원격 제어가 어떤 경로로 안전하게(또는 안전하지 않게) 도는지.
- **라이선스**: GNU Affero General Public License v3.0 or later. 루트 `LICENSE` 1~4줄에 "Copyright (C) 2026 Christophe Vidal / Licensed under the GNU Affero General Public License v3.0 or later."라고 적혀 있고, 8~9줄부터 AGPL 3 본문이다(코드 확인: 파일을 직접 열음). 하위 LICENSE는 글꼴 두 개뿐이다: `frontend/public/fonts/nerd-symbols-mono-v3.4.0.license.txt`, `web/fonts/nerd-symbols-mono-v3.4.0.license.txt`(MIT, Nerd Fonts 글리프. 코드 확인: `git ls-files`와 파일 첫 줄). NOTICE·COPYING 파일은 없다.
- **분석 대상 제품**:
  - Go 모듈 하나(`go.mod`, `github.com/0cv/herdr-mobile-relay`, go 1.27.0)에 바이너리 셋:
    - `cmd/herdr-mobile-relay`: 컴퓨터에서 도는 릴레이 본체. 같은 바이너리가 `serve` 외에 설치·검증·업데이트용 서브명령도 가진다.
    - `cmd/herdr-gateway`: 별도로 배포하는 "눈먼" 중계 서버(`Dockerfile.gateway`로 컨테이너화). 릴레이와 따로 돈다.
    - `cmd/fake-herdr`: 테스트용 가짜 herdr CLI(개발 도구).
  - `frontend/`: 폰 앱(Svelte 5 + Vite, bun). 빌드 산출물 `web/`을 레포에 커밋해 두고 릴레이가 서빙한다.
  - `relay/`: 설치·설정·서비스 셸 스크립트 33개와 Pi용 확장 `relay/pi-command-bridge/`. 루트에 `install.sh`, `scripts/`(빌드·패키징).
  - `contracts/fixtures`(Go와 TS가 같이 쓰는 JSON 픽스처), `tests/`(blackbox Go, mobile)는 검증 자산이라 분석 밖.
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음

### 용어

- **herdr**: 코딩 에이전트용 터미널 멀티플렉서. workspace > tab > pane 계층을 가진다. 이 문서에서 "에이전트"는 pane 안에서 도는 Claude Code, Codex 같은 CLI를 말한다.
- **플러그인**: herdr가 `herdr-plugin.toml`을 읽어 빌드하고 액션·pane·이벤트 훅으로 등록하는 외부 프로그램.
- **릴레이(relay)**: 컴퓨터마다 하나 도는 Go 프로세스. herdr를 읽고 조작하고, 폰과 암호화된 통신을 한다. 폰 앱은 여러 컴퓨터의 릴레이를 한 화면에 합친다.
- **게이트웨이(gateway)**: 릴레이와 폰을 이어 주는 중계 서버. 암호화된 프레임을 그대로 복사만 한다. 프로젝트가 공동체용으로 운영하는 것(`gw1/gw2.herdr-mobile.dev`)과 직접 세우는 것이 있다.
- **Cloudflare 터널**: `cloudflared`가 컴퓨터에서 Cloudflare로 바깥 연결을 열어, 공개 HTTPS 주소로 릴레이에 닿게 하는 방식. 임시(trycloudflare.com)와 고정(내 도메인)이 있다.
- **E2EE**: 폰과 릴레이 둘만 풀 수 있는 종단 간 암호화. 중간(터널·게이트웨이)은 암호문만 본다.
- **릴레이 키(relay key)**: 설치 때 만들어 `relay.env`에 `HERDR_RELAY_TOKEN`으로 저장하는 32바이트 문자열. 첫 페어링의 비밀이다.
- **초대(invitation)와 부트스트랩**: 폰을 등록하는 일회용 비밀. 부트스트랩 초대는 릴레이 키로 만들고 10분간 유효하다. 등록이 끝나면 폰은 기기별 자격 증명(credential)을 받는다.
- **컨트롤러/리더**: 기기 역할. 컨트롤러는 조작할 수 있고, 리더는 읽기만 한다.
- **QR 설정 링크**: 폰 앱 주소 뒤 `#` 조각에 설정 값을 담은 URL. `#` 뒤는 HTTP 요청에 실리지 않는다.
- **PWA**: 홈 화면에 설치하는 웹 앱. 브라우저 저장소와 PWA 정체성은 "origin"(주소)마다 따로 있다.
- **WebRTC DataChannel / STUN / ICE**: 폰과 컴퓨터가 서로 직접(P2P) 통신하는 길. STUN은 내 바깥 주소를 알려 주는 서비스, ICE는 이어지는 길을 찾는 절차다.
- **푸시(Web Push) / VAPID**: 브라우저·OS 푸시 서비스(FCM, Apple 등)를 통해 폰에 알림을 보내는 표준과 그 서명 키.
- **attention(주의)**: 에이전트가 사람의 입력을 기다리는 상태(승인, 질문). 릴레이가 pane 화면을 읽어 분류한다.
- **소켓 API / CLI**: herdr가 여는 로컬 소켓(줄 단위 JSON)과 `herdr` 명령. 릴레이는 둘 다 쓴다.

---

## 2. 프로젝트 개요

herdr에서 도는 에이전트를 책상 앞이 아니라 폰에서 돌본다. 릴레이가 컴퓨터에서 herdr의 목록을 읽어 폰에 보여 주고, 폰의 승인·답변·프롬프트·키 입력을 herdr 명령으로 바꿔 pane에 넣는다. 폰과 릴레이 사이는 세 경로 중 하나로 이어지고(Cloudflare 터널, 공동체 게이트웨이, 내 게이트웨이), 게이트웨이 경로는 가능하면 직접 P2P로 올라탄다. 모든 경로는 같은 E2EE를 쓴다.

구성은 글로 이렇게 읽힌다. 폰 PWA → (전송 경로) → 컴퓨터의 릴레이(`127.0.0.1:8375`) → herdr(소켓·CLI) → pane 속 에이전트. 반대 방향으로 herdr 이벤트 훅(UDP `127.0.0.1:8376`)과 소켓 이벤트 스트림이 상태를 올린다.

### 릴레이가 하는 일 (README·docs와 코드 대조)

| # | 주장 | 근거 | 검증 수준 |
|---|---|---|---|
| 1 | 매니페스트는 `id = herdr-mobile-relay.events`, 버전 0.22.13, `min_herdr_version = 0.7.5`, macOS·Linux 전용. `[[build]]` 1개, `[[actions]]` 9개, `[[panes]]` 9개, `[[events]]` 1개다. `[[startup]]`이 없어서 herdr가 릴레이를 자동으로 띄우지 않는다. 릴레이는 setup 계열 액션이나 OS 서비스로 시작한다. | `herdr-plugin.toml:18-25,32-33,38-103,107-160,167-169` | 코드 확인(매니페스트). herdr가 이를 해석하는 방식은 미확인 |
| 2 | 릴레이 바이너리는 인자 없으면 `serve`. 그 밖에 `version`, `event-hook`, `update-worker`, `verify-readiness`, `verify-public`, `app-deploy-worker`, `app-deploy-configured`, `pages-projects`, `stable-state`, `speech-voices`, `support`, `verify-release`, `release-manifest`, `activate-release`, `seal-release`, `prune-releases`, `setup-fragment`, `normalize-origin`, `qr` 서브명령이 있다. | `cmd/herdr-mobile-relay/main.go:43-49,65,70,79,84,98,103,112,161,166,172,190,255,281,328-349` | 코드 확인 |
| 3 | 설치 훅은 소스를 컴파일하지 않는다. `plugin-build.sh`가 `install.sh <version>`을 실행해 GitHub 릴리스의 `herdr-mobile-relay_<ver>_<os>_<arch>.tar.gz`와 `checksums.txt`를 받고, SHA-256 일치를 확인하고, 압축을 풀어 `verify-release`(내장 매니페스트 검증)와 태그 커밋 일치를 확인한 뒤 `~/.local/share/herdr-mobile-relay/releases/<...>`에 설치한다. 서명(gpg·cosign) 검증 코드는 없다. 체크섬은 같은 릴리스 위치에서 받는다. 즉 레포 소스가 아니라 릴리스 바이너리가 실행된다. | `relay/plugin-build.sh:543-545`, `install.sh:359,375-431,440-458` | 코드 확인(서명 검증 부재는 `install.sh`·`internal/release`에서 검색, 해당 단어 없음) |
| 4 | 에이전트 목록은 소켓 이벤트 스트림과 폴링을 같이 쓴다. 시작 때 `session.snapshot`으로 기준선을 잡고 `events.subscribe`로 위상 이벤트 20개를 받는다. 스트림이 살아 있으면 폴링은 15초 간격 점검으로 느려지고, 없으면 `HERDR_RELAY_POLL_INTERVAL`(기본 2초)로 돈다. 스트림이 끊기면 15초 뒤 재연결한다. | `internal/coordinator/poller.go:17,267-310,430-435`, `internal/herdr/events.go:232,317,355-383`, `internal/config/config.go:76` | 코드 확인 |
| 5 | `pane.agent_status_changed`는 소켓 구독 목록에 없고, 플러그인 이벤트 훅으로 받는다. 훅은 `HERDR_PLUGIN_EVENT_JSON`을 읽어 `127.0.0.1:8376`(`HERDR_RELAY_PLUGIN_PORT`)로 UDP 한 번 보낸다. 릴레이의 UDP 리스너는 `socket_path`가 자기 herdr 소켓과 같을 때만 상태를 반영한다. UDP에 인증은 없다(루프백 한정). | `herdr-plugin.toml:167-169`, `internal/eventhook/eventhook.go:47-83,85-122`, `internal/coordinator/udp.go:67-125`, `internal/app/server.go:1231-1237` | 코드 확인 |
| 6 | 승인 응답은 화면 읽기로 한다. 폰이 고른 선택지 번호·문구·지문(fingerprint)이 지금 pane 화면의 분류 결과와 같을 때만 `Up/Down/Enter` 키를 보낸다. 다르면 "선택지가 더 이상 없다"로 실패한다. | `internal/coordinator/approval.go:37,100-140,141-153`, `internal/question/attention.go:33-60,117` | 코드 확인 |
| 7 | 승인·질문 파서가 지원하는 에이전트는 claude, codex, omp/pi, opencode, qoder, hermes다. README는 Hermes를 승인 대상에 넣고 `docs/mobile-app.md`는 뺀다. 코드의 `Supports`에는 hermes가 있다. | `internal/question/parser.go:103-118,120-147` | 코드 확인 |
| 8 | 프롬프트는 `herdr agent prompt`(CLI)로 보낸다. Qoder만 `pane send-text` 뒤 `Enter` 키를 따로 보낸다. 길이 상한 100,000자. | `internal/coordinator/dispatch.go:359-413`, `internal/herdr/client.go:769` | 코드 확인 |
| 9 | 입력은 세 갈래다. `send_input`은 소켓 `pane.send_input`(텍스트 최대 64KiB, 의미 있는 키 이름만), `send_keys`는 CLI `pane send-keys`, `send_secret`은 최대 256자를 글자별 키와 `Enter`로 보내며 활동 기록에는 "Password entered"만 남긴다. | `internal/herdr/send_input.go:10,138`, `internal/herdr/client.go:739-760`, `internal/coordinator/dispatch.go:466,507-545` | 코드 확인 |
| 10 | 터미널 보기는 폰이 `watch_pane`을 걸면 기본 250ms마다 `pane.read`(소켓, 실패 시 CLI `pane read`)로 화면을 읽어 변경분을 보낸다. 줄 수 상한은 history.MaxLines(10,000). 푸시·분류용 읽기는 80줄 ANSI. | `internal/app/pane_watch.go:14,47-70`, `internal/herdr/client.go:696-713`, `internal/history/history.go:17` | 코드 확인 |
| 11 | Resize Session은 기기별 옵트인이다. herdr에 절대 크기 API가 없다는 가정으로 pane 셸의 TTY를 `ps`로 찾아 `TIOCSWINSZ` ioctl로 창 크기를 직접 바꾼다. 열 40~240, 행 10~120, 임대 120초. | `internal/panesize/manager.go:29-56`, `internal/panesize/terminal_unix.go:58`, `internal/panesize/terminal.go:65-72` | 코드 확인(herdr 쪽 부작용은 문서 주장이라 추론) |
| 12 | 대화 기록은 에이전트가 디스크에 남긴 세션 파일을 읽는다. Claude·Qoder·Codex·Pi·Oh My Pi·Oh My OpenCode·Cursor는 JSONL류, Hermes·OpenCode는 SQLite(내장 모듈 또는 `sqlite3` CLI, `HERDR_SQLITE_BACKEND`). 파일 16MiB, 한 페이지 기본 80개·최대 200개. 어느 위치를 뒤질지는 `HERDR_*_CONFIG_DIRS`로 정한다. | `internal/conversation/reader.go:19-30,132,168-236`, `internal/sqliteexec/exec.go:12-25`, `internal/agentroots/agentroots.go:54-57` | 코드 확인 |
| 13 | 워크스페이스 검사는 읽기 전용이다. 에이전트의 `cwd`를 `os.Root`로 열어 그 안의 상대 경로만 읽고(트리 4,000개, 텍스트 1MiB, 이미지 5MiB, diff 1MiB), git 상태·diff는 `git`을 실행한다(8초 제한). 읽기 액션이라 리더 기기도 쓸 수 있다. 디렉터리 브라우저는 `$HOME` 아래로 제한된다. | `internal/workspace/inspector.go:20-27,94,148,211,323,348,415`, `internal/app/server.go:1013-1048`, `internal/fsutil/listdir.go:24-48` | 코드 확인 |
| 14 | 푸시는 `webpush-go`로 보낸다. VAPID 키를 생성·저장하고, 구독 주소는 https:443의 FCM·Mozilla·Apple·Windows 호스트만 받는다. 전송 큐는 디스크에 남아 재시도한다. 카테고리는 attention·question·brief·finished·update·test, 미리보기는 hidden·question·brief. TTL 300초. | `internal/push/manager.go:83-135,329-346,1051-1075`, `internal/push/policy.go:18-37`, `internal/app/server.go:1597-1626` | 코드 확인(페이로드 암호화는 webpush-go 표준이라 추론) |
| 15 | 기기 인증은 `device-auth/devices.json`(모드 0600)에 자격 증명 비밀을 평문으로 저장한다. 부트스트랩 초대는 릴레이 키 자체를 비밀로 쓰고 10분 유효, 실패 5회면 소진, 마지막 컨트롤러는 폐기할 수 없다. 변경 액션은 기본 컨트롤러 전용이고, 푸시 구독·정책은 리더도 자기 것만 바꿀 수 있다. | `internal/deviceauth/store.go:19-31,191-244,420-455`, `internal/deviceauth/resolver.go:24-76`, `internal/app/server.go:284-326` | 코드 확인 |
| 16 | 전송 암호화는 ECDH P-256 임시 키 교환, HKDF-SHA256 키 유도, AES-256-GCM(키 32바이트)이다. 서브프로토콜 `herdr-e2ee-v2`. 키가 있는 릴레이는 `Authorization` 헤더나 `?token=` 쿼리가 있는 업그레이드를 거절한다. 키 없는 릴레이는 루프백에만 묶이고 origin 검사를 한다. | `internal/transport/e2ee.go:206-300,429-435`, `internal/transport/auth.go:10-41`, `internal/config/config.go:146-152` | 코드 확인 |
| 17 | 모든 변경(쓰기) 액션은 감사 로그 `remote-writes.jsonl`(0600, 5MiB 회전)에 시도·결과를 남긴다. 프롬프트 내용은 남기지 않고 크기와 SHA-256만 남긴다. 활동 피드(`get_activity`)는 따로 있고 프롬프트 발췌(최대 100,000자)를 디스크에 둔다. | `internal/audit/logger.go:16,52-57,94`, `internal/app/server.go:696-698,3125-3165,3206-3208`, `internal/activity/journal.go:20-23`, `internal/coordinator/dispatch.go:978-1012` | 코드 확인 |
| 18 | 로컬 HTTP는 `127.0.0.1:8375`가 기본이고 `/ws`(WebSocket), `/health`, `/healthz`, `/readyz`, 나머지는 폰 앱 정적 파일이다. 키 없이 비루프백 주소에 바인딩하면 시작을 거부한다. `/healthz`는 인증 없이 인스턴스 ID·버전·게이트웨이 주소·번들 해시를 돌려준다. | `internal/config/config.go:68-70,146-152`, `internal/app/server.go:1289-1293,2278-2330`, `internal/web/handler.go:23-38` | 코드 확인 |
| 19 | 게이트웨이 경로: 릴레이가 `HERDR_GATEWAY_URL`(ws/wss)로 바깥 연결을 열어 `/relay`에 등록한다. 등록 ID와 약속 키는 릴레이 키에서 HKDF로 유도한다. 후보가 여럿이면 `ordered` 또는 `latency`로 고르고 15초마다 공개 경로를 점검해 두 번 실패하면 갈아탄다. | `internal/transport/gateway.go:27-45,165-200,502-530`, `internal/gatewaywire/gatewaywire.go:89-110`, `internal/config/config.go:103-107`, `internal/app/hybrid.go:100-130` | 코드 확인 |
| 20 | 직접 P2P: 게이트웨이가 있고 `HERDR_TRANSPORT_FORCE_RELAY`가 아니면 pion WebRTC로 DataChannel `herdr-dc-v1`(최대 16세션)을 연다. 주소 발견은 게이트웨이의 UDP 3478에서 하고, 공유기 포트 매핑(PCP, NAT-PMP, UPnP)을 기본으로 시도한다(`HERDR_REACHABILITY_PORT_MAPPING` 기본 켜짐). 30분마다 도달성 자체 점검을 한다. | `internal/app/hybrid.go:23-50,100-155,231`, `internal/webrtclink/manager.go:29-55`, `internal/portmap/portmap.go:1-50`, `internal/config/config.go:82` | 코드 확인(실제 NAT 통과는 미확인) |
| 21 | 게이트웨이 서버(`cmd/herdr-gateway`)는 `/relay`, `/connect`, `/healthz`, `/whoami`, `POST /probe` 다섯 라우트를 가진다. 기본 한도: 릴레이 1,024, 동시 폰 512, 릴레이당 8, 분당 접속 30, 릴레이당 월 5GiB. `/probe`는 호출자가 관찰된 출처 주소로만 UDP를 보내고 1024 미만 포트를 거절한다. | `internal/gateway/server.go:68-76,242-246`, `internal/gateway/probe.go:35-60`, `cmd/herdr-gateway/main.go:103-163` | 코드 확인 |
| 22 | 폰에서 업데이트를 설치할 수 있다. `install_update`는 launchd(macOS) 또는 `systemd-run`(Linux) 워커를 띄우고, 워커가 GitHub에서 릴리스를 받아 검증한 뒤 `herdr plugin install 0cv/herdr-mobile-relay --ref <커밋> --yes`를 실행하고 헬스 체크로 확인한다. 새 버전 확인은 GitHub API(`api.github.com/repos/0cv/herdr-mobile-relay`)다. | `internal/update/manager.go:26-27,127,200,515-541`, `internal/update/worker.go:28,83-182,184-204`, `internal/app/server.go:714-746` | 코드 확인 |
| 23 | 앱 배포는 `npx --yes wrangler@<고정 버전> pages deploy <web>`로 Cloudflare Pages에 올린다. `CLOUDFLARE_API_TOKEN`·`CLOUDFLARE_ACCOUNT_ID`는 `relay.env`에서 읽고, GitHub 토큰은 자식 프로세스에서 제거한다. | `internal/appdeploy/worker.go:79,150-175,187-205,272-300`, `internal/childenv/command.go:10-30` | 코드 확인 |
| 24 | 응답 읽어 주기는 컴퓨터 안에서 합성한다. 엔진 후보는 Piper, macOS `say`, espeak-ng, espeak 순으로 등록되고(선택 규칙 `selectEngine`은 미탐색) 텍스트는 외부 TTS 서버로 가지 않는다. 다운로드는 Piper 런타임(GitHub)과 목소리 파일(HuggingFace)뿐이고 런타임 아카이브의 SHA-256 고정값이 코드에 있다(검증 호출은 미탐색). 문장 400자, WAV 900KiB 상한. | `internal/speech/speech.go:25-33,81-120,289-330`, `internal/speech/voices.go:60-62,164-180` | 코드 확인(목소리 파일 체크섬 검증은 미탐색) |
| 25 | 응답 복사(`copy_agent_response`)는 에이전트 자신의 복사 메뉴를 키로 조작한 뒤 컴퓨터 클립보드(`pbpaste`·`wl-paste`·`xsel`·`xclip`)에서 읽는다. | `internal/copyresponse/copy.go:15-25,53`, `internal/clipboard/clipboard.go:20-30`, `internal/app/server.go:2386-2445` | 코드 확인(에이전트별 메뉴 절차는 미탐색) |
| 26 | 에이전트 시작·정리는 herdr 명령으로 한다. 폰이 정하는 것은 프로필 ID, 이름(`[a-z][a-z0-9_-]{0,31}`), 작업 디렉터리, 첫 프롬프트이고, 실행 파일은 릴레이가 아는 프로필 argv만 쓴다. `tab create` → `pane run` → `agent start --kind --pane --timeout` 순서이고 제한 시간 40초. | `internal/coordinator/dispatch.go:659-700`, `internal/coordinator/lifecycle.go:73-109,200,232,266`, `internal/profiles/resolver.go:26-35` | 코드 확인 |
| 27 | 서비스 래퍼 `herdr-mobile-relay-service.sh`는 릴레이와 `cloudflared tunnel run`을 함께 띄우고 `cloudflared`나 설정 파일이 없으면 종료 코드 78로 끝난다. 임시 터널 경로는 포그라운드 `start.sh`가 `cloudflared tunnel --url`을 띄운다. 게이트웨이 경로는 `start.sh`가 릴레이만 띄우고 등록을 기다려 QR을 그린다. | `relay/herdr-mobile-relay-service.sh:36-48,85-89`, `relay/start.sh:101,113-135,152` | 코드 확인 |
| 28 | 폰 앱의 기기 자격 증명은 브라우저 `localStorage`(`herdr_device_auth_v1`)에 있다. 기기 잠금은 WebAuthn 플랫폼 인증기(`userVerification: required`)다. | `frontend/src/lib/device-auth.ts:3,165-187`, `frontend/src/lib/security.ts:207-213,262-266` | 코드 확인(화면 동작은 미탐색) |

### 기능 지도

사용자가 실제로 겪는 기능을 먼저, 내부 구조를 뒤에 둔다. 한 행은 "사용자 동작과 검증 경계"로 묶었고 디렉터리 하나와 일치하지 않는다.

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| F1 에이전트 목록·상태 모니터링 | 폰에서 컴퓨터별·workspace별로 에이전트와 상태(working, blocked 등)를 본다. herdr 위상 변화는 이벤트로, 상태 전환은 훅(UDP)과 폴링으로 반영. 쓰기 없음 | `internal/coordinator/poller.go:88,267` `Run`/`RunEvents`, `internal/coordinator/udp.go:67` `UDPListener.Run`, `internal/herdr/events.go:232` | C1, C2 | 핵심 | `capabilities/agent-inventory.md` · 미작성 | 코드 확인 |
| F2 승인·구조화 질문 응답 | 에이전트 화면의 승인 대화상자와 질문(객관식·자유 입력·플랜 질문)을 폰에 폼으로 보여 주고 답을 키 입력으로 넣는다. 화면 파싱이라 에이전트 UI에 의존. 지원: Claude, Codex, OMP/Pi, OpenCode, Qoder, Hermes(승인/질문 범위는 에이전트별로 다름) | `internal/question/attention.go:117` `Classify`, `internal/question/parser.go:120` `Parse`, `internal/coordinator/approval.go:37` `handleApproval`, `:206` `handleQuestion` | C1, C2 | 핵심(에이전트별 파서 패밀리) | `capabilities/attention-approval-question.md` · 미작성 | 코드 확인(에이전트별 파서 세부 미탐색) |
| F3 프롬프트·키·슬래시 명령 입력 | 프롬프트, 터미널 키, 의미 키(`Enter`, `ctrl+c`, F1~F24), 비밀번호 입력, 슬래시 명령 팔레트(에이전트별 카탈로그, 최대 4,096개). 읽기만 하는 리더 기기는 불가 | `internal/coordinator/dispatch.go:246` `Handle`, `:359` `handlePrompt`, `:466` `handleInput`, `:507` `handleSecret`, `internal/slashcmd/catalog.go:15-18`, `internal/app/server.go:964` | C1, C2 | 핵심 | `capabilities/prompt-input.md` · 미작성 | 코드 확인(슬래시 제공자별 탐색 규칙 미탐색) |
| F4 첨부 업로드 | 사진·스크린샷·문서를 청크로 올려(파일 8개, 개당 20MiB, 묶음 50MiB) 에이전트 대상에 묶고, 프롬프트의 참조가 현재 pane과 같을 때만 호스트 경로로 확장한다 | `internal/upload/upload.go:30-37`, `internal/app/uploads.go:14,25,72`, `internal/app/server.go:887` | C2 | 핵심 | `capabilities/attachments.md` · 미작성 | 코드 확인(내용 검증 세부 미탐색) |
| F5 터미널 보기 | 폰에서 pane 화면을 거의 실시간(250ms)으로 보고, 스크롤백 이력(최대 10,000줄)과 Claude류 화면 이력 캡처(4초마다)를 본다 | `internal/app/pane_watch.go:47` `startPaneWatch`, `internal/coordinator/dispatch.go:1170` `HandleReadPane`, `internal/history/history.go:17`, `internal/app/server.go:2072` | C1, C2 | 핵심 | `capabilities/terminal-view.md` · 미작성 | 코드 확인(델타 인코딩 `panedelta` 미탐색) |
| F6 터미널 폭 임대(Resize Session) | 기기가 옵트인하면 열린 터미널이 있는 동안 pane TTY 크기를 폰에 맞춘다. 임대 중 데스크톱 화면이 깨진다고 코드 주석이 공개한다 | `internal/panesize/manager.go:212,551`, `internal/panesize/terminal_unix.go:58`, `internal/app/server.go:754,1435` | C1 | 핵심 | `capabilities/pane-size-lease.md` · 미작성 | 코드 확인 |
| F7 네이티브 대화 기록·플랜 보기 | 에이전트의 디스크 세션(JSONL, SQLite)을 읽어 대화·도구 호출·Oh My OpenCode 플랜을 검색 가능한 형태로 보여 준다 | `internal/conversation/reader.go:168` `ReadWithProject`, `internal/app/server.go:774,2163`, `internal/agentroots/agentroots.go:54` | C2 | 핵심(에이전트별 reader 패밀리) | `capabilities/conversation-history.md` · 미작성 | 코드 확인(에이전트별 파싱 세부 미탐색) |
| F8 워크스페이스·워크트리·에이전트 수명주기 | workspace 만들기·이름·순서·닫기, git worktree 생성·열기·삭제, 탭 이름·순서, 에이전트 시작·이름·초기화·재시작·중지 | `internal/app/server.go:895` 액션 분기, `internal/coordinator/dispatch.go:575-860`, `internal/coordinator/lifecycle.go:73`, `internal/herdr/client.go:421-560` | C1, C2 | 핵심 | `capabilities/workspace-lifecycle.md` · 미작성 | 코드 확인(워크스페이스 그룹 닫기 동의 절차 미탐색) |
| F9 워크스페이스 읽기 전용 검사 | 에이전트 작업 디렉터리의 파일 트리·파일·이미지·git 상태·diff, 새 작업용 디렉터리 브라우저($HOME 이하) | `internal/workspace/inspector.go:148,211,348,415`, `internal/app/server.go:1013`, `internal/fsutil/listdir.go:24` | C2 | 핵심 | `capabilities/workspace-inspection.md` · 미작성 | 코드 확인(경로 정규화 `safePath` 세부 미탐색) |
| F10 푸시 알림 | 기기별 카테고리·침묵 시간·스누즈·미리보기 수준을 정하고, 에이전트가 막히거나 끝나면 웹 푸시를 받는다. 알림에는 승인 버튼을 두지 않는다(문서 주장) | `internal/push/manager.go:83,601,774,1051`, `internal/push/policy.go:99`, `internal/app/server.go:1597` `publishAgentPush`, `:1085-1190` | C2, C3 | 핵심 | `capabilities/push-notifications.md` · 미작성 | 코드 확인(정책 평가 규칙·로컬라이즈 미탐색) |
| F11 응답 읽어 주기·응답 복사 | 컴퓨터가 합성한 WAV를 폰이 재생(5개 언어), 목소리 설치·삭제, 에이전트 응답을 컴퓨터 클립보드로 복사 | `internal/speech/speech.go:289` `Synthesize`, `internal/speech/voices.go:470`, `internal/copyresponse/copy.go:53`, `internal/app/server.go:2386,2454` | C2 | 부속 | `capabilities/speech-and-copy.md` · 미작성 | 코드 확인 |
| F12 기기 페어링·역할·QR | QR(또는 링크)로 첫 컨트롤러 등록, 컨트롤러가 일회용 초대를 만들어 다른 폰을 등록, 이름 변경·폐기·초기화, 리더/컨트롤러 구분 | `internal/deviceauth/store.go:157,191,290,320`, `internal/deviceauth/resolver.go:24,76`, `internal/setuphelper/setuphelper.go:14`, `internal/app/server.go:284,787` | C3, C4 | 핵심 | `capabilities/device-pairing.md` · 미작성 | 코드 확인(초대 소비 원자성 세부 미탐색) |
| F13 E2EE 전송과 로컬 서버 | 폰 WebSocket을 받아 핸드셰이크·암호화 프레임·전송 버퍼·청크 처리. 모든 경로(터널·게이트웨이·P2P)가 같은 계층을 쓴다 | `internal/transport/ws.go:113,131`, `internal/transport/e2ee.go:206`, `internal/transport/auth.go:10`, `internal/framing/framing.go` | C3, C4 | 핵심 | `capabilities/e2ee-transport.md` · 미작성 | 코드 확인(프레임 시퀀스·재전송 세부 미탐색) |
| F14 Cloudflare 터널 경로 | 임시 터널(`cloudflared tunnel --url`, 실행마다 새 호스트명, 매번 새 부트스트랩) 또는 고정 터널(`cloudflared tunnel create`, DNS 라우트, 서비스 설치, 호스트명 변경·해체) | `relay/start.sh:80-82,152,205`, `relay/stable-setup.sh:759,844`, `relay/herdr-mobile-relay-service.sh:85-89`, `relay/change-hostname.sh:155` | F17 | 핵심 | `capabilities/cloudflare-tunnel-path.md` · 미작성 | 코드 확인(고정 터널 마법사 분기 세부 미탐색) |
| F15 게이트웨이·직접 WebRTC 경로 | 게이트웨이에 바깥 연결로 등록, 폰이 게이트웨이를 거쳐 접속한 뒤 직접 연결로 갈아타기. STUN·포트 매핑·도달성 점검 | `internal/transport/gateway.go:165,502`, `internal/app/hybrid.go:100,157`, `internal/webrtclink/manager.go:155`, `internal/portmap/portmap.go`, `internal/reachability/reachability.go` | C3, C4 | 핵심 | `capabilities/gateway-webrtc-path.md` · 미작성 | 코드 확인(ICE·NAT 세부 미탐색) |
| F16 게이트웨이 서버 | 릴레이 등록과 폰 연결을 짝지어 암호문 프레임을 복사하고, 한도·월 사용량·STUN·`/probe`를 제공하는 별도 배포 서버 | `cmd/herdr-gateway/main.go:39,103`, `internal/gateway/server.go:242-246`, `internal/gateway/relay.go:54`, `internal/gateway/client.go:52`, `Dockerfile.gateway` | C5 | 부속(릴레이와 따로 배포) | `capabilities/gateway-server.md` · 미작성 | 코드 확인(사용량 영속화·STUN 구현 세부 미탐색) |
| F17 herdr 플러그인 등록·설치·설정 메뉴 | `herdr plugin install` → 릴리스 번들 설치 → 설정 메뉴(임시 터널, 공동체 게이트웨이, 내 게이트웨이, 고정 터널, 호스트명, QR, 앱 배포, 상태)와 제거·해체 액션 | `herdr-plugin.toml:32-169`, `relay/plugin-build.sh:543`, `install.sh:359-453`, `relay/open-plugin-pane.sh:18-30`, `relay/plugin-setup-menu.sh:240-262` | C1, C4 | 핵심 | `capabilities/plugin-install-setup.md` · 미작성 | 코드 확인(셸 스크립트 33개 중 일부만 읽음) |
| F18 herdr 이벤트 훅 | herdr가 `pane.agent_status_changed`마다 훅을 실행하면 릴레이에 UDP로 알려 폰이 즉시 반응 | `herdr-plugin.toml:167-169`, `relay/plugin-on-event.sh:5-11`, `internal/eventhook/eventhook.go:47` | C1 | 핵심 | `capabilities/event-hook.md` · 미작성 | 코드 확인 |
| F19 폰 앱 번들 서빙·PWA | 릴레이가 `web/`의 허용 목록 자산과 릴리스 설명자만 서빙. Svelte 앱: 에이전트 목록, 터미널, 설정, 알림, 기기 잠금 | `internal/web/handler.go:23,53,149`, `frontend/src/main.ts`, `frontend/src/App.svelte`, `frontend/src/lib/transports/index.ts` | C2, C3 | 핵심 | `capabilities/phone-app.md` · 미작성 | 코드 확인(진입점·저장 키만. 화면 동작 `frontend/src/components` 미탐색) |
| F20 자체 업데이트·릴리스 검증 | 폰에서 새 버전 확인·설치(워커가 `herdr plugin install` 실행), 릴리스 매니페스트 봉인·검증·활성화·정리용 서브명령 | `internal/update/manager.go:127,200`, `internal/update/worker.go:83,184`, `internal/release/manifest.go:61,162,182`, `cmd/herdr-mobile-relay/main.go:190-250` | C1 | 부속 | `capabilities/self-update.md` · 미작성 | 코드 확인(롤백·잠금 세부 미탐색) |
| F21 앱 배포(Cloudflare Pages) | 한 릴레이를 "배포 소유자"로 지정해 폰 앱을 별도 Pages 프로젝트에 올리고 공개 번들을 검증 | `internal/appdeploy/worker.go:79,187`, `internal/appdeploy/manager.go:124`, `relay/configure-app-deploy.sh`, `Makefile:1-30` | F14 | 부속 | `capabilities/app-deploy.md` · 미작성 | 코드 확인(쉘 스크립트 세부 미탐색) |
| F22 Pi 슬래시 명령 브리지 | Pi 프로필에 릴레이 소유 확장을 설치하면 실행 중인 Pi의 확장·스킬·템플릿 명령을 폰 팔레트에 보여 준다 | `relay/pi-commands.sh:7-40`, `relay/pi-command-bridge/bridge.mjs`, `internal/pibridge/client.go:108,157`, `internal/app/pi_commands.go:43` | F3 | 부속 | `capabilities/pi-command-bridge.md` · 미작성 | 코드 확인(브리지 소켓 인증 세부 미탐색) |
| F23 감사·활동·진단 | 쓰기 감사 로그, 활동 피드, 지원 스냅샷(`support`), `/health*` 엔드포인트, 설정 상태 화면 | `internal/audit/logger.go:52`, `internal/activity/journal.go:20`, `internal/support/support.go:13`, `internal/app/server.go:2278-2330` | C2 | 부속 | `capabilities/audit-and-diagnostics.md` · 미작성 | 코드 확인 |
| F24 개발·검증 도구 | 가짜 herdr(`fake-herdr`), 계약 픽스처, blackbox·mobile 테스트, Makefile·scripts | `cmd/fake-herdr/main.go:1`, `Makefile:1-50`, `contracts/fixtures`, `tests/` | 없음 | 부속(분석 밖) | 해당 없음 | 미확인(테스트·CI는 기본적으로 열지 않음. `fake-herdr`는 첫 30줄만 읽음) |

**공유 계약** (여러 기능이 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1 herdr 호출 계약(소켓 메서드 + CLI 명령 + 이벤트 구독 + 환경변수) | F1~F3, F5, F6, F8, F17, F18, F20 | `internal/herdr/client.go`, `internal/herdr/socket_api.go`, `internal/herdr/events.go` (아래 표) | `capabilities/herdr-call-contract.md` · 미작성 | 코드 확인(herdr 서버 쪽 동작은 미확인) |
| C2 폰↔릴레이 메시지 프로토콜(액션 카탈로그 72개(읽기 25, 변경 47), 읽기/변경 구분, 프로토콜 버전 3, 감사 대상 표시) | F1~F13, F19, F22, F23 | `internal/protocol/protocol.go:105-178,292`, `:502` `Capabilities` | `capabilities/phone-relay-protocol.md` · 미작성 | 코드 확인 |
| C3 E2EE 핸드셰이크·프레임 | F12, F13, F15, F19 | `internal/transport/e2ee.go:206-330`, `internal/framing/framing.go` | `capabilities/e2ee-handshake.md` · 미작성 | 코드 확인 |
| C4 릴레이 환경·상태 파일(`relay.env`, `devices.json`, 캐시 디렉터리) | F12~F15, F17, F20, F21 | `internal/config/config.go:66-144`, `relay/common.sh:776-804` | `capabilities/relay-config.md` · 미작성 | 코드 확인 |
| C5 게이트웨이 와이어(opcode, hello, HKDF 유도) | F15, F16 | `internal/gatewaywire/gatewaywire.go:30-110` | `capabilities/gateway-wire.md` · 미작성 | 코드 확인 |

#### C1 herdr 호출 상세 (소켓)

소켓은 `HERDR_SOCKET_PATH`, 없으면 `$XDG_CONFIG_HOME/herdr/herdr.sock`이다(`internal/config/config.go:121`). 요청은 줄 단위 JSON이며 응답의 `result.type`을 확인한다(`internal/herdr/socket_api.go:70-155`).

| 메서드 | 쓰는 곳 | 근거 | 검증 수준 |
|---|---|---|---|
| `ping` | 서버 버전·프로토콜·기능 점검(30초마다) | `internal/herdr/capabilities.go:240`, `internal/app/server.go:1337` | 코드 확인 |
| `events.subscribe` | 위상 이벤트 스트림(아래 이벤트 20개 + 조건부 `workspace.reordered`) | `internal/herdr/events.go:232,355-383` | 코드 확인 |
| `session.snapshot` | 이벤트 스트림 기준선 | `internal/herdr/events.go:317` | 코드 확인 |
| `agent.list`, `pane.list`, `workspace.list`, `tab.list` | 인벤토리 조립 | `internal/herdr/client.go:380,396,412,581` | 코드 확인 |
| `pane.get`, `pane.process_info` | 개별 pane 상태·포그라운드 프로세스 | `internal/herdr/client.go:646,662` | 코드 확인 |
| `pane.read` | 화면 읽기(`source`: recent_unwrapped, recent, visible, ANSI 또는 텍스트) | `internal/herdr/socket_api.go:185-215` | 코드 확인 |
| `pane.send_input` | 텍스트와 의미 키 입력 | `internal/herdr/send_input.go:138` | 코드 확인 |
| `pane.send_keys` | 글자 하나 키 입력(리터럴 키) | `internal/herdr/literal_key.go:59` | 코드 확인 |
| `workspace.close`, `workspace.move`, `workspace.move_block`, `tab.move` | workspace 닫기·순서, 탭 순서 | `internal/herdr/client.go:476`, `internal/herdr/socket_api.go:356,363,378` | 코드 확인 |

이벤트 20개: pane.created, closed, updated, moved, exited, agent_detected / tab.created, closed, renamed, moved / workspace.created, updated, metadata_updated, closed, renamed, moved, focused / worktree.created, opened, removed. `workspace.reordered`는 `workspace.move_block` 기능 탐지가 통과해야만 구독에 넣는다. 구형 herdr가 이름 하나만 모르면 구독 전체를 거절하기 때문이다(`internal/herdr/events.go:350-380`, 코드 주석). 구독 목록에 `pane.agent_status_changed`와 `pane.output_changed`는 없다.

#### C1 herdr 호출 상세 (CLI)

릴레이는 `herdr` 바이너리(`HERDR_BIN`, 없으면 PATH와 몇몇 설치 위치에서 탐색, `internal/config/config.go:221`)를 자식 프로세스로 실행한다. 동시 8개까지, 기본 15초 제한, 환경에서 `GH_TOKEN`·`GITHUB_TOKEN`·`HERDR_GITHUB_TOKEN_FILE`을 빼고 `HERDR_SOCKET_PATH`를 자기 소켓으로 덮어쓴다(`internal/herdr/client.go:18-25,874-910`, `internal/childenv/command.go:10-30`).

| 명령 | 쓰는 곳 | 근거 | 검증 수준 |
|---|---|---|---|
| `workspace create`, `workspace rename` | workspace 만들기·이름 | `internal/herdr/client.go:424,444` | 코드 확인 |
| `worktree list/create/open/remove --workspace` | git worktree 관리(`--no-focus`) | `internal/herdr/client.go:484,494,508,524` | 코드 확인 |
| `tab create`, `tab rename` | 에이전트 시작용 탭, 이름 변경 | `internal/herdr/client.go:557,591` | 코드 확인 |
| `pane run`, `pane close` | 프로필 argv 실행, 에이전트 중지 | `internal/herdr/client.go:612,778` | 코드 확인 |
| `pane send-keys`, `pane send-text`, `pane read` | 키·텍스트 입력, 소켓 실패 때 읽기 대체 | `internal/herdr/client.go:744,764,704` | 코드 확인 |
| `agent get`, `agent prompt`, `agent rename`, `agent start --kind --pane --timeout` | 에이전트 조회·프롬프트·이름·시작 | `internal/herdr/client.go:620,769,783,800` | 코드 확인 |
| `integration status` | 어떤 에이전트 통합이 설치됐는지 → 시작 프로필 목록 | `internal/herdr/client.go:822`, `internal/profiles/resolver.go:248-280` | 코드 확인 |
| `--version` | 설치된 herdr 클라이언트 버전 | `internal/herdr/capabilities.go:437` | 코드 확인 |
| `plugin install 0cv/herdr-mobile-relay --ref <커밋> --yes` | 폰에서 시작한 자체 업데이트 | `internal/update/worker.go:184-204` | 코드 확인 |
| `plugin pane open --plugin --entrypoint --placement --env PATH --focus [--target-pane]` | 액션이 대화형 pane을 여는 래퍼 | `relay/open-plugin-pane.sh:18-30` | 코드 확인 |
| `plugin action invoke setup --plugin herdr-mobile-relay.events` | 설치 2초 뒤 설정 메뉴 자동 실행(`HERDR_MOBILE_RELAY_NO_AUTO_SETUP=1`이면 생략) | `relay/plugin-build.sh:648-657` | 코드 확인 |
| `plugin config-dir herdr-mobile-relay.events` | 설정 디렉터리 위치 조회 | `relay/plugin-build.sh:38-40` | 코드 확인 |

herdr가 플러그인에 주는 환경변수로 코드가 읽는 것: `HERDR_PLUGIN_EVENT_JSON`(`internal/eventhook/eventhook.go:49`), `HERDR_PLUGIN_CONFIG_DIR`(`:127`, `internal/config/config.go:168-175`), `HERDR_PLUGIN_ID`·`HERDR_BIN_PATH`·`HERDR_PANE_ID`(`relay/open-plugin-pane.sh:5,6,26`), `HERDR_SOCKET_PATH`(`internal/eventhook/eventhook.go:86`). 코드 확인. 이 변수를 herdr가 언제 어떻게 채우는지는 미확인.

### 외부 서비스·네트워크 호출, 인증·비밀 보관, 데이터가 나가는 곳

이 소절은 보안상 중요한 부분이라 따로 모았다.

**릴레이가 먼저 여는 바깥 연결**

| 대상 | 언제 | 무엇이 나가는가 | 근거 | 검증 수준 |
|---|---|---|---|---|
| 게이트웨이(`wss://gw1.herdr-mobile.dev`, `gw2` 기본 후보, 또는 내 주소) | 게이트웨이 경로를 골랐을 때 상시 | 암호문 프레임, 등록 hello(유도한 relay_id), 15초마다 `/healthz` 점검 | `relay/common.sh:1072`, `internal/transport/gateway.go:502`, `internal/config/config.go:103-107` | 코드 확인 |
| 게이트웨이 UDP 3478(STUN)과 `POST /probe` | 직접 연결 준비·30분마다 점검 | 공유기가 본 UDP 출처 주소, 32바이트 토큰 | `internal/webrtclink/manager.go:29-55`, `internal/app/hybrid.go:23-50,231`, `internal/gateway/probe.go:35-60` | 코드 확인 |
| 공유기 | 직접 연결 준비 때(기본 켜짐) | PCP·NAT-PMP·UPnP 포트 매핑 요청(UDP 포트가 인터넷에 열림) | `internal/portmap/portmap.go:1-50`, `internal/config/config.go:82` | 코드 확인 |
| Cloudflare(`cloudflared`, 터널 경로) | 터널 경로일 때 상시 | 폰과 릴레이 사이 암호문 전체가 Cloudflare 엣지를 지남. 임시 터널은 폰 앱 JS도 이 길로 서빙 | `relay/start.sh:152`, `relay/herdr-mobile-relay-service.sh:89` | 코드 확인 |
| `cloudflare-dns.com` DNS-over-HTTPS | 임시 터널 호스트명이 살아날 때까지 | 터널 호스트명 조회 | `relay/start.sh:186` | 코드 확인 |
| `api.github.com`, `github.com` releases | 설치·새 버전 확인·폰 업데이트 | 버전 조회, 릴리스 tarball·checksums 다운로드. 토큰이 있으면 인증 헤더 | `install.sh:375-406`, `internal/update/manager.go:26-27`, `internal/update/stage.go:34-80` | 코드 확인 |
| 푸시 서비스(FCM, Apple, Mozilla, Windows) | 알림 전송 때 | VAPID 서명, 구독 키로 암호화된 페이로드(표준). 허용 호스트 5종만 | `internal/push/manager.go:329-346,1057` | 코드 확인(암호화는 라이브러리 표준이라 추론) |
| `huggingface.co`, `github.com/rhasspy/piper` | Piper 설치·음성 다운로드 | 파일 다운로드만(텍스트는 안 나감) | `internal/speech/voices.go:60-62,164-180` | 코드 확인 |
| `npx wrangler` → Cloudflare Pages API | 앱 배포 때 | 폰 앱 정적 번들, Cloudflare API 토큰 사용 | `internal/appdeploy/worker.go:160,187-205,272-300` | 코드 확인 |
| `herdr.dev/install.sh` | `relay/setup.sh`가 herdr가 없을 때 안내·설치 | 쉘 스크립트를 받아 `sh`로 실행하는 줄이 있음 | `relay/setup.sh:77` | 코드 확인(실행 조건 세부 미탐색) |

**릴레이가 받는 연결**: 기본 TCP `127.0.0.1:8375`(WebSocket과 정적 파일), UDP `127.0.0.1:8376`(훅). 바깥에서 닿는 길은 터널·게이트웨이·직접 UDP뿐이다(코드 확인: `internal/config/config.go:68-70`, `internal/coordinator/udp.go`, `internal/app/server.go:1231`). 직접 경로는 ICE 세션 자격 증명과 DTLS 지문이 암호 채널 안에서만 오간다는 설명이 `docs/transports.md`에 있다(후보).

**인증과 비밀 보관**

| 비밀 | 어디에 어떻게 | 근거 | 검증 수준 |
|---|---|---|---|
| 릴레이 키(`HERDR_RELAY_TOKEN`, 32바이트) | `openssl rand -hex 16`으로 생성해 `relay.env`(0600, 플러그인 설정 디렉터리)에 평문 저장. 부트스트랩 초대의 비밀로도 쓰임. 임시·수동 설정 안내 화면에는 키가 그대로 출력됨 | `relay/common.sh:636-640,776-795`, `internal/app/server.go:277-282`, `relay/start.sh:140-146` | 코드 확인 |
| QR 설정 링크 | `#setup=<릴레이 키>&label=...` (게이트웨이 경로는 후보 게이트웨이 목록도 포함). `#` 뒤는 HTTP 요청에 실리지 않음 | `internal/setuphelper/setuphelper.go:14-22`, `relay/start.sh:124-127`, `relay/common.sh:1360-1365` | 코드 확인 |
| 기기 자격 증명 | 릴레이 쪽 `device-auth/devices.json`(0600, 디렉터리 0700)에 비밀을 평문 보관, 폰 쪽은 브라우저 `localStorage` | `internal/deviceauth/store.go:420-470`, `frontend/src/lib/device-auth.ts:3,165-187` | 코드 확인 |
| VAPID 비공개 키, 푸시 참조 서명 키 | 푸시 디렉터리(0700)의 파일, 서명 키는 0600 | `internal/push/manager.go:83-110,137-190`, `internal/push/payload.go:42-60` | 코드 확인 |
| GitHub 토큰(비공개 레포용) | 별도 토큰 파일 경로만 `relay.env`에 두고, 릴레이·cloudflared·에이전트 자식 프로세스에는 환경변수로 넘기지 않음 | `relay/common.sh:776-803`, `internal/childenv/command.go:10-30` | 코드 확인 |
| Cloudflare API 토큰 | `relay.env`에서 읽어 wrangler 자식 프로세스 환경에만 주입 | `internal/appdeploy/worker.go:272-300` | 코드 확인 |

**폰으로 나가는 민감 데이터와 디스크에 남는 것**

- 폰으로 가는 것: 에이전트 목록, pane 화면 전체(최대 10,000줄), 대화 기록, 컴퓨터의 파일 내용(에이전트 `cwd` 안, 읽기 액션이라 리더 기기도 가능), git diff, 디렉터리 이름($HOME 아래). 암호화 계층은 F13이고 암호화 이전에 접근을 가르는 것은 역할(컨트롤러/리더)뿐이다(코드 확인: `internal/app/server.go:284-326`, `internal/workspace/inspector.go:211-260`).
- 디스크에 남는 것: 활동 피드(프롬프트 발췌 최대 100,000자, `<cache>/` 아래 0600), 감사 로그(해시만), 푸시 큐와 구독, 업로드(7일 보존), 대화·pane 이력 캐시(`claude-history`, `conversation-history`). 비밀번호(`send_secret`) 값은 활동·감사에 남기지 않는다(코드 확인: `internal/coordinator/dispatch.go:540`, `internal/app/server.go:3190-3203`, `internal/activity/journal.go:20-23`, `internal/upload/upload.go:30-37`, `internal/history/history.go:213`).
- 약한 지점(코드로 확인한 사실만): (1) 루프백 UDP 8376은 인증이 없고 `socket_path`는 보낸 쪽이 적는 값이라, 같은 컴퓨터의 아무 프로세스나 에이전트 상태 이벤트를 주입할 수 있다(`internal/coordinator/udp.go:67-110`). (2) `/healthz`·`/readyz`는 인증이 없어서 터널로 공개되면 인스턴스 ID·버전·번들 해시가 보인다(`internal/app/server.go:2284-2330`). (3) 설치 무결성은 같은 릴리스 위치의 `checksums.txt`에 기대고 서명 검증은 없다(`install.sh:375-431`). (4) 기기 비밀은 암호화 없이 0600 파일에 있다(`internal/deviceauth/store.go:420-455`).

**대조한 범위와 미탐색 영역**
- 대조: README 전체(요구 사항, "What you get", 전송 선택 표, 보안 한 단락), `herdr-plugin.toml` 전체, `QUICKSTART.md`(설치·페어링·게이트웨이), `docs/security.md`(포트·감사·E2EE·기기 권한·헬스), `docs/transports.md`(세 경로·직접 업그레이드), `docs/pane-size-leasing.md`(프로토콜·폭 임대), `docs/mobile-app.md` 앞부분(기능 목록), `docs/slash-command-discovery.md` 앞부분, `docs/agent-directories.md` 앞부분을 위 코드로 확인했다. 후보로만 읽어 코드로 확인한 항목만 표에 옮겼다.
- 문서와 구현의 차이:
  - 승인 지원 에이전트 목록이 문서마다 다르다. README는 Codex, Claude Code, Hermes, Qoder, OpenCode, Oh My Pi, Pi, `docs/mobile-app.md`는 Codex, Claude Code, Qoder, Oh My Pi, Pi(OpenCode는 질문만), 코드(`internal/question/parser.go:103-111`)는 claude, codex, omp/pi, opencode, qoder, hermes를 모두 포함한다. 에이전트별 실제 지원 폭은 파서 파일 단위로 따로 확인해야 한다(미탐색).
  - README는 "Cloudflare 터널이 기본"이라 쓰지 않고 공동체 게이트웨이를 추천하지만 `docs/transports.md`는 "Cloudflare tunnel — The default"라고 적는다. 코드상 기본은 `HERDR_GATEWAY_URL`이 비어 있으면 터널 경로다(`relay/start.sh:80,113`, `.env.example` 주석). 설정 메뉴의 기본 선택(1번)은 임시 터널이다(`relay/plugin-setup-menu.sh:247`, 코드 확인).
  - `docs/security.md`가 "Notifications never expose an approval action"이라 한 부분은 푸시 페이로드 구성 코드(`internal/push/payload.go`)를 읽지 않아 미확인이다.
  - README의 "Native Windows is not supported"는 매니페스트 `platforms = ["macos","linux"]`(`herdr-plugin.toml:25`)와 일치한다(코드 확인).
  - `docs/pane-size-leasing.md`의 "herdr 0.9.3에 절대 크기 API 없음"은 herdr 쪽 사실이라 미확인이다. 릴레이가 TTY ioctl을 쓴다는 점만 코드 확인이다.
- 미탐색: 테스트·CI·CHANGELOG·기여 문서(기본 제외, 열지 않음, `.github/`, `tests/`, `contracts/fixtures`는 이름만 확인), `frontend/src/components/*`와 `lib/store.ts`(3,267줄)의 화면 동작, 에이전트별 질문·승인 파서 본문(`internal/question/parser.go` 150줄 이후와 `testdata`), `internal/slashcmd/*` 제공자별 규칙, `internal/conversation/*`의 에이전트별 파싱, `internal/push/policy.go`·`queue.go` 정책 평가·재시도, `internal/transport/ws.go`·`sendbuffer.go`·`conn.go`, `internal/webrtclink`·`portmap`·`reachability` 세부, `internal/gateway/quota.go`·`stun.go`, `internal/coordinator/state.go`·`workspace.go`·`triage.go`, `internal/panedelta`, `relay/*.sh` 33개 중 `plugin-build.sh`·`open-plugin-pane.sh`·`plugin-setup-menu.sh`·`start.sh`·`herdr-mobile-relay-service.sh`·`common.sh` 일부만 열람(고정 터널 마법사 `stable-setup.sh` 등은 grep만), `scripts/*`, `docs/gateway-self-hosting.md`·`docs/cloudflare-tunnel.md`·`docs/updates.md`·`docs/development.md`·`docs/mobile-device-ci.md`. `AGENTS.md`는 레포 안 에이전트 지침이라 지시가 아니라 참고 자료로도 열지 않았다.

---

## 3. 구조 해설

시각화는 사용자 지시로 만들지 않았다. 글만으로 읽는 순서와 모듈 역할을 적는다.

### 읽는 순서

1. `herdr-plugin.toml`: herdr가 이 플러그인에서 무엇을 등록하는지(빌드, 액션 9, pane 9, 이벤트 훅 1, startup 없음).
2. `relay/plugin-build.sh` → `install.sh`: 릴리스 번들이 어떻게 설치되는지. 레포 소스가 아니라 릴리스가 실행된다는 점.
3. `relay/open-plugin-pane.sh`와 `relay/plugin-setup-menu.sh`: 액션이 pane을 열고 설정 메뉴가 전송 경로를 고르는 과정. 이어서 `relay/start.sh`(포그라운드 시작과 QR).
4. `cmd/herdr-mobile-relay/main.go:43-49,328-349`: `serve` → `internal/app/server.go:160` `New`(부품 조립), `:546` `Run`(HTTP 서버와 백그라운드 작업 시작).
5. `internal/herdr`(소켓·CLI·이벤트 클라이언트)와 `internal/coordinator`(목록 상태·명령 디스패처).
6. `internal/protocol/protocol.go:105-178`: 폰이 보낼 수 있는 72개 액션과 읽기/변경 구분. 이것이 기능 전체의 목차다.
7. `internal/transport`(ws.go, e2ee.go, gateway.go)와 `internal/deviceauth`: 폰 접속을 어떻게 인증하고 암호화하는지.
8. 기능별 패키지: `question`, `conversation`, `workspace`, `push`, `speech`, `panesize`, `upload`.
9. 별도 배포: `cmd/herdr-gateway` + `internal/gateway`, 그리고 `frontend/`.

### herdr 연동 지점

- **매니페스트**(`herdr-plugin.toml`): `[[build]]` `bash relay/plugin-build.sh`. `[[actions]]` 9개는 모두 `bash relay/open-plugin-pane.sh <이름>`이고 `[[panes]]` 9개가 그 대화형 절반이다(`setup`, `quick-start`, `install-service`, `setup-link`, `change-hostname`, `configure-app-deploy`, `stable-teardown`, `uninstall`은 `zoomed`, `status`는 `overlay`). `[[events]]`는 `pane.agent_status_changed` 하나이고 `sh relay/plugin-on-event.sh`를 실행한다. `[[startup]]`은 없다. 코드 확인(`herdr-plugin.toml:32-169`). herdr가 이 필드를 실제로 어떻게 해석하는지는 미확인(추론: 매니페스트 주석 설명).
- **액션 → pane**: `open-plugin-pane.sh`는 `herdr plugin pane open --plugin <id> --entrypoint <이름> --placement <zoomed|overlay> --env PATH=... --focus [--target-pane $HERDR_PANE_ID]`를 실행한다. 코드 확인(`relay/open-plugin-pane.sh:18-30`).
- **이벤트 훅**: `plugin-on-event.sh`가 설치된 릴리스 바이너리 `event-hook`을 실행 → `HERDR_PLUGIN_EVENT_JSON`을 UDP로 로컬 릴레이에 전달. 코드 확인(`relay/plugin-on-event.sh:5-11`, `internal/eventhook/eventhook.go:47-83`).
- **런타임 호출**: 릴레이가 `HERDR_BIN`과 `HERDR_SOCKET_PATH`로 herdr를 부른다. 읽기와 입력 일부는 소켓, 변경 대부분은 CLI다(위 C1 표 둘). 폴링과 이벤트를 모두 쓴다(`poller.go:88,267`).
- **소켓 기능 탐지**: 시작과 30초마다 `ping`으로 서버 버전·프로토콜을 보고 `workspace.move_block`, `tab.move`, `pane.read`는 실제로 한 번 시험 호출해서 지원 여부를 기록한다. 지원되지 않으면 기능을 끄거나 CLI로 대체한다. 코드 확인(`internal/herdr/capabilities.go:240,486,512,538`, `internal/herdr/client.go:696-713`).
- **자기 업데이트**: 폰이 시작하면 릴레이가 `herdr plugin install`을 다시 부른다(위 표). 코드 확인(`internal/update/worker.go:184-204`).
- 미확인: herdr 서버가 액션·pane·이벤트 훅·`HERDR_*` 환경변수를 어떻게 처리하는지.

### 대표 흐름 하나: 에이전트가 승인을 기다릴 때

1. herdr가 `pane.agent_status_changed`를 발생시킨다 → 훅이 UDP로 릴레이에 보낸다. — 입력 `HERDR_PLUGIN_EVENT_JSON` → 출력 `agent_event` UDP 패킷 (`eventhook.go:47-83`)
2. 릴레이 UDP 리스너가 `CommitEventForSession`으로 상태를 `blocked` 등으로 반영하고 폰에 `agent_update`를 브로드캐스트한다. — (`udp.go:117-125`, `server.go:1239-1262`)
3. 전환 처리기가 `pane.read`로 화면 80줄(ANSI)을 읽어 `question.Classify`로 승인/질문/잡담을 분류한다. — (`server.go:1875,1902`, `attention.go:117`)
4. 분류 결과가 붙은 `agent_update`와 `attention` 카테고리 푸시가 큐에 들어간다. 푸시는 기기 정책(카테고리·스누즈·화면에 보고 있는 pane)을 통과해야 전송된다. — (`server.go:1597-1626`, `push/manager.go:601,1051`)
5. 폰이 `respond`(선택지 번호·문구·지문)를 보낸다 → E2EE로 풀고 컨트롤러인지 확인 → 감사 기록 → 디스패처가 화면을 다시 읽어 지문이 같을 때만 `Up/Down/Enter`를 보낸다. — (`server.go:696-698`, `approval.go:100-140`)
6. 350ms 간격으로 화면을 다시 읽어 승인이 반영됐는지 확인하고 `accepted`→확인/미확인 단계를 폰에 알린다. — (`approval.go:15,155-205`)

### 모듈별 역할

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `cmd/herdr-mobile-relay` | 서브명령 분기, `serve` 시작(설정·로거·시그널), 설치·검증용 CLI | 인자·환경 → `app.New().Run` | `main.go:43` `run`, `:328` `runServe` | 코드 확인 |
| `internal/config` | 환경변수 로딩과 검증(키 32바이트, 비루프백이면 키 필수, 게이트웨이 URL 형식) | 환경 → `Config` | `config.go:66` `Load`, `:146` `validate` | 코드 확인 |
| `internal/app` | 서버 조립, `/ws`·`/healthz` 라우팅, 액션 분기(카탈로그 72개), 권한 검사, 전환 처리·푸시 발행, 하이브리드 전송 | 폰 메시지 ↔ coordinator/herdr/기능 패키지 | `server.go:160,546,640-1200`, `hybrid.go:100` | 코드 확인(4,032줄 중 라우팅·전환 일부) |
| `internal/herdr` | herdr 소켓·CLI·이벤트 클라이언트, 기능 탐지, 오류 분류(재시도 안전 여부) | 소켓 JSON, CLI 인자 ↔ 구조체 | `client.go:204-215`, `socket_api.go`, `events.go`, `capabilities.go` | 코드 확인 |
| `internal/coordinator` | 에이전트 목록 상태, 폴러, 이벤트 반영, 명령 디스패처(직렬화·세대 검증), 승인·질문, 수명주기 | herdr 인벤토리 → 폰용 상태, 폰 명령 → herdr 호출 | `poller.go:88,267`, `dispatch.go:246`, `approval.go:37`, `lifecycle.go:73` | 코드 확인(`state.go`·`workspace.go` 세부 미탐색) |
| `internal/question` | pane 화면 문자열을 승인·질문·입력 대기로 분류, 에이전트별 파서 | ANSI 텍스트 → `Classification`, `Interaction` | `attention.go:117`, `parser.go:120` | 코드 확인(에이전트별 파서 미탐색) |
| `internal/protocol` | 폰↔릴레이 메시지 타입, 액션 카탈로그, 오류 코드, 기능(capabilities) 목록 | JSON ↔ `Inbound` | `protocol.go:105,292,502` | 코드 확인 |
| `internal/transport` | WebSocket 허브, E2EE 핸드셰이크, 프레임, 게이트웨이 클라이언트 | 원시 연결 ↔ 인증된 `ClientConn` | `ws.go:113,131`, `e2ee.go:206`, `gateway.go:165,502`, `auth.go:10` | 코드 확인 |
| `internal/deviceauth` | 초대·자격 증명 저장, 역할, 폐기, E2EE 비밀 해석 | 선택자 → 비밀·신원 | `store.go:191,420`, `resolver.go:24,76` | 코드 확인 |
| `internal/gateway`, `internal/gatewaywire` | 별도 게이트웨이 서버(라우트·한도·STUN·`/probe`)와 와이어 계약·키 유도 | 암호문 프레임 복사 | `server.go:242`, `relay.go:54`, `gatewaywire.go:89` | 코드 확인 |
| `internal/webrtclink`, `portmap`, `reachability`, `framing` | 직접 P2P DataChannel, 공유기 포트 매핑, 도달성 점검, 큰 프레임 분할 | SDP·ICE 후보·UDP 패킷 | `webrtclink/manager.go:155`, `portmap/portmap.go`, `reachability/reachability.go` | 코드 확인(세부 미탐색) |
| `internal/push` | VAPID 키, 구독 저장, 정책, 영속 큐, 웹 푸시 전송 | 이벤트 키 → 푸시 | `manager.go:83,601,1051`, `policy.go:99` | 코드 확인 |
| `internal/conversation`, `session`, `agentroots`, `sqliteexec`, `history` | 에이전트 세션 파일·DB 읽기, 세션 이름, 탐색 루트, pane 이력 캐시 | 에이전트·cwd·세션 ID → 대화 페이지 | `conversation/reader.go:168`, `agentroots/agentroots.go:54` | 코드 확인(파서 세부 미탐색) |
| `internal/workspace`, `fsutil` | 읽기 전용 파일·git 검사, 디렉터리 브라우저 | cwd(+상대 경로) → 트리·파일·diff | `inspector.go:148,211,348,415`, `listdir.go:24` | 코드 확인 |
| `internal/panesize`, `panedelta` | PTY 크기 임대, 화면 변경분 계산 | 폭·행 → ioctl | `panesize/manager.go:212`, `terminal_unix.go:58` | 코드 확인(`panedelta` 미탐색) |
| `internal/speech`, `copyresponse`, `clipboard` | 로컬 TTS 합성과 목소리 관리, 응답 복사 | 텍스트 → WAV, 에이전트 복사 메뉴 → 클립보드 | `speech.go:289`, `copy.go:53` | 코드 확인 |
| `internal/update`, `release`, `appdeploy`, `launchd`, `stablestate`, `readiness` | 릴리스 확인·설치 워커, 매니페스트 검증, Pages 배포, launchd 워커, 터널 기록, 준비 점검 | GitHub 릴리스·wrangler | `update/worker.go:83`, `release/manifest.go:61`, `appdeploy/worker.go:79` | 코드 확인(`stablestate`·`readiness` 미탐색) |
| `internal/eventhook` | herdr 이벤트 훅의 UDP 전달기 | `HERDR_PLUGIN_EVENT_JSON` → UDP | `eventhook.go:47` | 코드 확인 |
| `internal/audit`, `activity`, `support` | 쓰기 감사, 활동 피드, 지원 스냅샷 | 이벤트 → 0600 파일 | `audit/logger.go:52`, `activity/journal.go:20`, `support/support.go:13` | 코드 확인 |
| `internal/web` | 폰 앱 번들 서빙(허용 목록, 릴리스 설명자) | HTTP GET → 정적 자산 | `handler.go:23,53` | 코드 확인 |
| `internal/pibridge`, `relay/pi-command-bridge` | Pi 실행 중 명령 메타데이터 조회용 소켓 브리지 | 소켓 질의 → 명령 카탈로그 | `pibridge/client.go:108,157` | 코드 확인(인증 세부 미탐색) |
| `frontend/` (+ `web/` 산출물) | 폰 PWA(Svelte 5). E2EE·전송 선택·상태 저장소·화면 | 릴레이 WebSocket/WebRTC ↔ UI | `src/lib/transports/`, `src/lib/e2ee.ts`, `src/lib/device-auth.ts` | 코드 확인(진입점·저장만) |
| `relay/*.sh`, `install.sh`, `scripts/` | 설치·설정 메뉴·터널·서비스·업데이트·제거 | 사용자 입력 → 파일·서비스·herdr CLI | `plugin-build.sh:543`, `start.sh:101,152`, `common.sh:776` | 코드 확인(일부만 열람) |

**미확인 영역**
- herdr 서버가 매니페스트·액션·pane·이벤트 훅·환경변수를 실제로 어떻게 처리하는지(herdr 소스 또는 실행 필요).
- 이 레포를 빌드·실행하지 않았으므로 E2EE 핸드셰이크, 직접 P2P, 푸시 전송, 승인 키 전송이 실제로 도는지는 `실행 확인` 아님.
- 폰 앱 화면 동작(`frontend/src/components`)과 에이전트별 질문·승인 파서 세부.
- 릴리스 바이너리가 이 SHA의 소스로 빌드됐는지(`release.yml`·`scripts/package-release.sh`는 열지 않음).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

다음에 볼 곳:
- 승인·질문 파서의 에이전트별 실제 지원 폭(`internal/question/parser.go` 150줄 이후, `internal/coordinator/approval.go:206` 이후)과 문서 불일치 정리.
- `internal/transport/ws.go`·`conn.go`·`sendbuffer.go`의 연결 수명·역압 처리, `internal/webrtclink` 세션 인증.
- `internal/push/payload.go`·`policy.go`: 푸시에 실리는 내용과 승인 액션 미노출 주장 확인.
- `relay/stable-setup.sh`·`relay/common.sh` 나머지(고정 터널 마법사, 서비스 설치)와 `scripts/package-release.sh`·`.github/workflows/release.yml`(릴리스 빌드 출처, 예외로 열 이유: 설치되는 바이너리의 출처를 정하는 파일).
- herdr 쪽: `herdr plugin pane open`·`plugin action invoke`·이벤트 훅·`HERDR_PLUGIN_*` 환경변수 처리(herdr 소스 또는 실행 확인).
- 기능 스펙은 사용자 승인 후 지도 순서(F1→F2→…)대로 작성.
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성)
