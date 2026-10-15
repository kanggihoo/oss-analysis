# mitmproxy Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/mitmproxy/mitmproxy.git`
- **분석 Commit SHA**: `77355977e5ea540b51ed029a40ed1dc2f1c2ba7b` (`v12.2.3-103-g77355977e`, commit 2026-10-13)
- **분석 일자**: `2026-10-15`
- **작업트리 상태**: `clean`
- **분석 목적**: `사용 중심 정리` — 제공 기능, 설치/삭제 방법, 사용법을 파악(소스 분석은 후순위). 도입 여부는 미정
- **메타데이터**: [`artifacts/mitmproxy/repo-metadata.txt`](../../artifacts/mitmproxy/repo-metadata.txt), [`github-repo-view.json`](../../artifacts/mitmproxy/static-analysis/github-repo-view.json)
- **규모**: MIT, ⭐45.6k, fork 4.8k (2026-10-15 GitHub 조회). Python 3.12+ (`pyproject.toml`), `mitmproxy/` 비테스트 `.py` 약 47k줄 (`git ls-files` 기준 단순 줄 수, tokei 미설치). 웹 UI는 `web/`(JS)
- **의존 핵심**: `mitmproxy_rs`(Rust 바인딩, local/WireGuard/TUN 모드 담당으로 보임), h11/h2/wsproto/aioquic (HTTP/WS/QUIC 스택). 의존 목록은 `pyproject.toml`, `docs/.../protocols.md` 기준

---

## 2. 프로젝트 개요

GitHub 설명: "An interactive TLS-capable intercepting HTTP proxy for penetration testers and software developers." 클라이언트와 서버 사이에 끼어들어 HTTP(S) 트래픽을 **보고, 멈추고, 수정하고, 재생**하는 중간자(MITM) 프록시다. TLS는 자체 CA로 즉석 서명한 인증서를 제시해 복호화한다(클라이언트가 그 CA를 신뢰해야 함, `docs/src/content/concepts/certificates.md`).

README 기준 첫 문장: "an interactive, SSL/TLS-capable intercepting proxy with a console interface for HTTP/1, HTTP/2, and WebSockets." 단, 소스를 보면 실제 범위는 README 문구보다 넓다(아래 표 참고).

### 진입점 (3개 CLI, 같은 코어)

| 명령 | 역할 | 엔트리 |
|---|---|---|
| `mitmproxy` | 터미널 TUI | `mitmproxy.tools.main:mitmproxy` → `mitmproxy/tools/console/` |
| `mitmdump` | CLI, "tcpdump for HTTP" | `mitmproxy.tools.main:mitmdump` → `mitmproxy/tools/dump.py` |
| `mitmweb` | 웹 UI | `mitmproxy.tools.main:mitmweb` → `mitmproxy/tools/web/` + `web/` |

(`pyproject.toml:101-104` 코드 확인)

### 주요 기능

| 기능 | 설명 | 코드 근거 | 검증 수준 |
|---|---|---|---|
| HTTP/1, HTTP/2 가로채기 | h11 기반 자체 HTTP/1 스택, HTTP/2 지원. 프로토콜 위반도 일부러 그대로 전달 | `mitmproxy/proxy/layers/http/_http1.py`, `_http2.py`, `docs/.../protocols.md` | 코드 확인(존재) / 문서 확인 |
| HTTP/3 · QUIC | aioquic 기반. 문서상 reverse, local, WireGuard 모드에서만 가능, cURL 위주로 시험됨 | `layers/http/_http3.py`, `layers/quic/`, `protocols.md` | 코드·문서 확인 |
| WebSocket | wsproto 기반. HTTP Upgrade 핸드셰이크 이후 메시지 단위로 보고 수정·주입 | `layers/websocket.py`, `mitmproxy/websocket.py`, `examples/addons/websocket-simple.py`, `websocket-inject-message.py` | 코드 확인(존재) |
| TLS 복호화 (MITM) | 자체 CA를 만들고 도메인별 인증서를 즉석 발급. 클라이언트 측 CA 신뢰 등록이 전제 | `mitmproxy/certs.py`, `layers/tls.py`, `addons/tlsconfig.py`, `addons/onboarding.py` | 코드 확인(존재) / 인증서 발급 동작 `미확인` |
| 다양한 프록시 모드 | regular, transparent, upstream, reverse, SOCKS5, DNS, WireGuard, **local**(OS 레벨), TUN | `mitmproxy/proxy/mode_specs.py` 클래스 `RegularMode`…`TunMode` | 코드 확인 |
| Local Capture | 앱 설정 없이 같은 PC의 트래픽을 투명하게 캡처. 전체 / 프로세스명 / PID 지정(`--mode local:curl`, `local:42`, 부정 `!`). **Windows·Linux·macOS 지원**(Linux는 WSL 미지원 등 제약) | `LocalMode` (`mode_specs.py:297`, `mitmproxy_rs.local` 사용), `docs/.../modes.md:67-115` | 코드·문서 확인 / 실행 `미확인` |
| 범용 TCP / UDP 프록시 | HTTP가 아닌 연결은 원문 바이트로 중계. 연결 시작 바이트로 HTTP 여부를 판별해 `TCPLayer`로 폴백하며 `SSH`로 시작하면 HTTP가 아니라고 판단. **STARTTLS 업그레이드는 감지 못함**. 프로토콜 해석(DB 쿼리 등)은 없음 | `addons/next_layer.py:175-197`, `layers/tcp.py`, `layers/udp.py`, `protocols.md:69-92` | 코드·문서 확인 |
| DNS 프록시/서버 | DNS 요청 캡처·서버 모드 | `layers/dns.py`, `DnsMode` (`mode_specs.py:262`), `contentviews/_view_dns.py` | 코드 확인(존재) |
| 필터 · 가로채기(intercept) | 필터식으로 흐름을 고르고, 요청·응답을 일시 정지해 수정 후 전달 | `mitmproxy/flowfilter.py`, `addons/intercept.py`, `docs/.../filters.md` | 코드 확인(존재) |
| 수정 · 리다이렉트 | 헤더/본문 수정, 로컬 파일 응답(map local), 다른 URL로 전달(map remote), blocklist | `addons/modifyheaders.py`, `modifybody.py`, `maplocal.py`, `mapremote.py`, `blocklist.py` | 코드 확인(존재) |
| 재생 (Replay) | 저장한 흐름을 클라이언트/서버 재생. TCP는 재생 불가(문서) | `addons/clientplayback.py`, `serverplayback.py` | 코드 확인(존재) |
| 저장 · 내보내기 | flow 파일 저장/읽기, HAR 저장, 요청을 cURL 등으로 export | `addons/save.py`, `readfile.py`, `savehar.py`, `export.py`, `mitmproxy/io/` | 코드 확인(존재) |
| 콘텐츠 뷰 | JSON, XML/HTML, GraphQL, MQTT, Socket.IO, multipart, 이미지, JS/CSS, zip 등을 보기 좋게 표시 | `mitmproxy/contentviews/_view_*.py` | 코드 확인(존재) |
| 애드온 / 스크립팅 | Python 애드온으로 이벤트 훅(`request`, `response`, `websocket_message`, `tcp_message` 등)에 코드 연결. 예제 다수 | `mitmproxy/addonmanager.py`, `addons/script.py`, `examples/addons/` (30여 개) | 코드 확인(존재) |
| 프록시 인증 · 업스트림 | 프록시 인증, upstream proxy 체이닝 | `addons/proxyauth.py`, `upstream_auth.py`, `UpstreamMode` | 코드 확인(존재) |
| 온보딩 | 프록시로 `mitm.it`에 접속하면 CA 인증서 설치 안내·다운로드 | `addons/onboarding.py`, `addons/onboardingapp/` | 코드 확인(존재) / 동작 `미확인` |

- 위 표는 **기능의 존재 확인**이다. 각 모드·레이어의 실제 동작은 질문별 분석에서 다룬다.
- 대화 중 "기억 기반이라 미확인"이라 했던 항목(transparent / SOCKS5 / WireGuard / local 모드, 비HTTP TCP 중계)은 위에서 `mode_specs.py`·`next_layer.py`로 **존재가 확인**됐다. README 첫 문장만 보면 HTTP 계열 전용처럼 보이지만 실제로는 더 넓다.
- 활용 예(일반): 웹/모바일/CLI 앱이 보내는 HTTPS API 요청 디버깅, 보안 점검, 응답 목킹과 수정, 트래픽 재생. 특정 클라이언트가 프록시 환경변수나 CA 신뢰 설정을 따르는지는 클라이언트 쪽 사항이라 이 레포로는 알 수 없다(`미확인`, 대상별로 실험 필요).

---

## 3. 설치 · 삭제 · 사용법

이 프로젝트는 소스 분석보다 **무엇을 제공하고, 어떻게 깔고 지우고 쓰는가**를 우선한다. 출처는 레포 안 공식 문서(`docs/src/content/`)이며, 문서에 없는 내용은 `추론` 또는 `일반 지식`으로 표시했다. 실제 설치·실행은 하지 않았다(검증 수준: `문서 확인`).

### 3.1 설치

| 환경 | 방법 (공식 문서 `overview/installation.md`) |
|---|---|
| **Windows** | mitmproxy.org의 설치 프로그램 또는 Microsoft Store(자동 업데이트). 설치 후 `mitmproxy`, `mitmdump`, `mitmweb`이 PATH에 추가됨. standalone 바이너리는 임시 폴더에 풀기 때문에 시작이 느림. 콘솔 UI는 Windows Terminal 권장. WSL에서는 Linux 방식으로 설치 |
| macOS | `brew install --cask mitmproxy` 또는 바이너리 |
| Linux | mitmproxy.org의 standalone 바이너리 권장. 배포판 패키지는 있으나 최신과 어긋날 수 있음 |
| PyPI (애드온이 추가 파이썬 패키지를 쓸 때) | `uv tool install mitmproxy`, 패키지 추가는 `uv tool install --with <패키지> mitmproxy` |
| Docker | DockerHub 공식 이미지 `mitmproxy/mitmproxy` |
| 소스 | `CONTRIBUTING.md` 참고 (개발용) |

- 바이너리와 Docker 이미지는 파이썬·OpenSSL을 내장하고 의존성이 릴리스 시점에 고정된다. 보안 이슈를 위해 **정기적으로 업데이트**하라고 문서가 안내한다.
- 업데이트 확인 같은 "phone home"을 하지 않는다(문서 명시).
- 파이썬 3.12 이상 필요(`pyproject.toml`)하지만 바이너리 설치에서는 내장이라 무관.

### 3.2 삭제

**공식 문서에는 삭제 절차가 없다**(`uninstall` 검색 결과 없음). 아래는 설치 방식별 일반적인 방법이며 `추론/일반 지식`이다.

| 항목 | 방법 | 검증 |
|---|---|---|
| 설치 프로그램 / Store 버전 | Windows "설치된 앱"에서 제거 | 일반 지식, 미확인 |
| uv 설치 | `uv tool uninstall mitmproxy` | 일반 지식, 미확인 |
| Homebrew | `brew uninstall --cask mitmproxy` | 일반 지식, 미확인 |
| Docker | 컨테이너·이미지 삭제 | 일반 지식 |
| **CA 인증서 (중요)** | 설치 때 OS/브라우저/기기에 등록한 mitmproxy CA를 **반드시 따로 제거**. 프로그램을 지워도 신뢰 등록은 남는다 | 추론 (문서에 제거법 없음. 등록은 `certutil -addstore root ...`처럼 문서에 있으므로 반대로 제거) |
| 설정 폴더 | `~/.mitmproxy`(Windows는 사용자 홈 아래) 삭제. 여기에 **CA 개인키**(`mitmproxy-ca.pem`)가 있음 | 문서 확인(생성 위치) |
| 프록시 설정 | 브라우저·OS에 넣은 프록시(`localhost:8080`)와 환경변수 원복 | 일반 지식 |

CA는 설치 때마다 고유하게 생성되어 다른 PC와 공유되지 않는다(문서). 그래도 키 파일이 남아 있으면 그 PC에서 트래픽을 가로챌 수 있는 CA가 신뢰 목록에 계속 있는 셈이므로, 쓰지 않을 때는 신뢰 등록을 지우는 편이 안전하다(`추론`).

### 3.3 기본 사용 흐름 (`overview/getting-started.md`)

1. **도구 선택해서 실행**: `mitmproxy`(터미널 UI) / `mitmweb`(브라우저 UI) / `mitmdump`(비대화형 출력). 인자 없이 시작하면 **regular HTTP 프록시로 `localhost:8080`**에서 대기.
2. **트래픽을 프록시로 보내기**: 브라우저·OS·앱의 프록시 설정으로 `localhost:8080` 지정. 앱마다 방식이 달라서(OS 전역, 브라우저 자체 설정, 환경변수 등) 검색해서 맞추라고 문서가 안내.
3. **연결 확인**: 프록시를 거친 상태에서 `http://mitm.it` 접속 시 CA 설치 페이지가 뜨면 성공.
4. **CA 설치**: mitm.it의 OS별 안내를 따름. 처음 실행 때 `~/.mitmproxy`에 CA가 자동 생성됨.
5. **HTTPS 확인**: `https://mitmproxy.org`를 열어 새 flow로 보이면 TLS 복호화가 되는 것.

문제가 있을 때(문서 `modes.md` Troubleshooting): 이벤트 로그에 `client connect`가 없으면 클라이언트가 프록시에 닿지 못한 것(주소·포트 오류, Wi-Fi 클라이언트 격리). 프록시 설정을 무시하는 앱(예: Android 앱)은 WireGuard, Local Capture, transparent 모드를 써야 함.

### 3.4 CA 설치 상세 (`concepts/certificates.md`)

- 생성 파일: `mitmproxy-ca.pem`(인증서+**개인키**), `mitmproxy-ca-cert.pem`(대부분의 비Windows용), `mitmproxy-ca-cert.p12`(Windows용), `mitmproxy-ca-cert.cer`(일부 Android).
- 가장 쉬운 방법은 mitm.it. 수동 설치 예(문서 명시):
  - curl: `curl --proxy 127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com/`
  - wget: `wget -e https_proxy=127.0.0.1:8080 --ca-certificate ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com/`
  - Windows(관리자): `certutil -addstore root mitmproxy-ca-cert.cer`
  - Java: `keytool -importcert ... -file ~/.mitmproxy/mitmproxy-ca-cert.pem`
- **인증서 고정(pinning)** 앱은 mitmproxy 인증서를 거부함. 내용이 중요하지 않으면 `--ignore-hosts`로 그 도메인을 가로채지 않게 제외(`howto/ignore-domains.md`).
- 자체 서버 인증서: `--certs *.example.com=cert.pem`, 자체 CA: `--set confdir=DIRECTORY`.
- 프록시 설정을 따르지 않는 특정 프로그램(예: Node.js 앱)에 CA를 신뢰시키는 방법은 이 문서 범위 밖(해당 프로그램 쪽 설정, `미확인`).

### 3.5 모드별 사용법 (`concepts/modes.md`)

| 모드 | 시작 | 언제 |
|---|---|---|
| Regular (기본) | `mitmproxy` / `mitmweb` / `mitmdump` 인자 없이 | 클라이언트에 HTTP 프록시를 설정할 수 있을 때. 가장 쉽고 안정적 |
| Local Capture | `mitmproxy --mode local` (전체), `--mode local:curl` (프로세스명), `--mode local:42` (PID), `local:!curl` (제외), `local:curl,wget` (목록) | 프록시 설정 없이 같은 PC의 앱을 캡처. 앱은 프록시를 모름. **Windows·Linux·macOS 지원** (Linux는 WSL 미지원 등 제약) |
| WireGuard | `mitmweb --mode wireguard` 후 대상 기기에서 WireGuard 클라이언트로 mitmproxy가 제공한 설정 import | 외부 기기(폰 등)나 Android 앱. 사용자 영역에서 동작해 관리자 권한 불필요. 단 **mitmproxy가 도는 PC 자신의 트래픽은 못 잡음**. 기본 포트 51820/udp, 키는 `~/.mitmproxy/wireguard.conf` |
| Reverse | `mitmdump --mode reverse:https://example.com` (포트 `@80` 등으로 변경) | 특정 서버 앞에 두고 요청을 그 서버로 전달하며 관찰 |
| Transparent / TUN / Upstream / SOCKS / DNS | `--mode transparent`, `tun`, `upstream:...`, `socks5`, `dns` | 라우팅·네트워크 구성을 직접 할 수 있을 때 쓰는 고급 모드. 문서는 transparent 대신 WireGuard·Local Capture를 권장 |

`--mode`는 여러 번 줄 수 있어 서로 다른 포트에서 여러 서버를 함께 띄울 수 있다. 어떤 모드든 세 도구(mitmproxy/mitmweb/mitmdump) 모두에서 쓸 수 있다.

### 3.6 자주 쓰는 작업 (문서 확인)

| 하고 싶은 것 | 방법 |
|---|---|
| 특정 요청 잡아서 수정 후 전송 | 대화형 UI에서 `set intercept <필터>`(단축키 `i`), 예 `~u <URL 정규식>`. 멈춘 요청을 고쳐서 재개 (`cli-tutorials/`) |
| 저장 / 다시 읽기 | `mitmdump -w 파일`로 저장, `mitmproxy -r 파일`로 열기 (`tutorials/client-replay.md`) |
| 클라이언트 재생 | `mitmdump -C 파일` — 저장한 요청을 하나씩 다시 보냄. `anticache` 옵션과 함께 쓰면 완전한 응답을 받기 좋음 |
| 서버 재생 | 저장한 응답을 같은 요청에 대해 돌려줌 (`features.md`) |
| 광고·추적 등 요청 차단 | `block_list` 옵션, 예 `:~d google-analytics.com:404`, 상태코드 444는 응답 없이 연결 종료 |
| 응답을 로컬 파일로 대체 | `map_local` 옵션, 예 `\|example.com/main.js\|~/main-local.js` |
| 다른 URL로 전달 | `map_remote` 옵션 |
| 헤더·본문 수정 | `modify_headers`, `modify_body` 옵션 |
| 필터식으로 흐름 고르기 | `~u`(URL), `~m`(메서드), `~b`(본문), `~d`(도메인), `~q`/`~s`(요청/응답), `!`, `&`, `\|` 조합 (`concepts/filters.md`) |
| 가로채지 않을 도메인 | `--ignore-hosts <정규식>` (pinning 앱, 불필요 트래픽) |
| 큰 파일 스트리밍 | `stream_large_bodies` 크기 지정 시 본문을 버퍼링하지 않음. 단 본문 접근·수정 불가 |
| 파이썬 애드온 | `mitmdump -s ./addon.py`. `request`/`response` 등 이벤트 메서드를 가진 객체를 `addons` 리스트에 넣음 (`addons/overview.md`, `examples/addons/`) |
| 옵션 지정 | `--set 옵션=값`, 설정 파일, 대화형 UI에서 변경 |

### 3.7 쓸 때 주의할 점

- **민감정보**: 복호화된 요청·응답에는 토큰, 쿠키, 비밀번호가 평문으로 보인다. `-w`로 저장한 파일, 로그, 스크린샷을 공유하지 말 것(`추론`: 도구 특성에서 도출).
- **CA 개인키 보호**: `mitmproxy-ca.pem`은 유출되면 안 된다.
- **비HTTP 프로토콜**: TCP는 원문 바이트 중계만 하며 STARTTLS 감지 불가, TCP 재생 불가(`concepts/protocols.md`). SSH는 HTTP가 아닌 것으로 취급됨(코드 확인, `next_layer.py:191`).
- **HTTP/3**: reverse, local, WireGuard 모드에서만 가능하고 cURL 위주로 시험됨(문서).
- **허가된 대상만**: 본인 소유·관리 트래픽에만 쓴다(도구 용도 설명이 "penetration testers and software developers").

---

## 4. 핵심 아키텍처 지도 (archify Diagrams)

> 이 프로젝트는 사용 관점 정리를 우선하므로 구조도 작성은 후순위다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | — | — | 미작성 (다음 단계) |
| 대표 실행 흐름 | — | — | 미작성 (후보: 클라이언트 연결 → `next_layer` → TLS → `HttpLayer` → addon hook) |

### 지도 작성 시 출발점 (소스 구조 관찰, `코드 확인(디렉터리 존재)`)

1. `mitmproxy/proxy/` — 프록시 코어. 프로토콜을 **Layer 스택**으로 쌓는 구조(`layer.py`, `layers/`)로 보이며, `server.py`/`mode_servers.py`가 모드별 서버를 띄움 (`추론`: 파일 구성에서 본 것)
2. `mitmproxy/addons/` — 거의 모든 기능(필터, 저장, 재생, 수정 등)이 addon으로 구현됨. `next_layer.py`가 "다음에 어떤 프로토콜 Layer를 붙일지" 결정하는 훅
3. `mitmproxy/tools/{console,dump.py,web}` — 같은 코어(`master.py`) 위의 세 가지 프런트엔드
4. `mitmproxy/contentviews/` — 본문 렌더링 플러그인
5. `mitmproxy_rs`(외부 Rust 패키지) — local/WireGuard/TUN은 여기서 처리하는 것으로 보임 (`mode_specs.py`가 `mitmproxy_rs.local`을 import). 이 레포 안에는 구현이 없음 → 이 레포로는 `미확인` 영역

---

## 5. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: Claude Code의 API 요청을 mitmproxy로 캡처할 수 있는가?](./questions/q1-capture-claude-code.md) - *가능. `HTTPS_PROXY`와 `NODE_EXTRA_CA_CERTS`를 프로세스에만 주면 되고 system prompt가 `/v1/messages`의 `system` 필드에 그대로 보임 (실행 확인)*
- 추가 제안 질문은 [next.md](./next.md) 참고

---

## 6. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **공식 문서 정리**: [docs-guide.md](./docs-guide.md) — `docs/src/content/` 전체를 폴더별로 정리(개념, 모드, 인증서, 프로토콜, howto, 애드온)
- **축적된 위키 지식**: 아직 없음 (`wiki/projects/mitmproxy.md` 미작성)
