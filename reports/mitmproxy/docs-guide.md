# mitmproxy 공식 문서 정리 (docs/src/content 기준)

- **상위 개요**: [overview.md](./overview.md)
- **출처**: `repos/mitmproxy/docs/src/content/*.md` (Hugo 소스, 공개본 <https://docs.mitmproxy.org/>). `api/`(자동 생성 API 레퍼런스)와 빈 `addons-api.md`는 제외
- **기준 SHA**: `77355977e5ea540b51ed029a40ed1dc2f1c2ba7b` / 작성일 2026-10-15
- **검증 수준**: 전부 `문서 확인`(문서를 읽고 정리함). 실행하지 않았으므로 동작은 `미확인`. 문서 밖 보충은 `일반 지식`/`추론`으로 표시
- Hugo 단축 코드(`{{< >}}`)로 들어가는 그림·영상·자동 생성 표(`generated/filters.html`, `options.html`)는 원문에서 직접 읽지 못한 부분

## 0. 문서 구성 한눈에

| 폴더 | 파일 | 내용 |
|---|---|---|
| `_index.md` | 소개 | 3개 도구, 핵심 기능 목록 |
| `overview/` | installation, getting-started, features | 설치, 첫 실행, 옵션 기반 기능 모음 |
| `concepts/` | how-mitmproxy-works, modes, certificates, protocols, filters, options, commands | 동작 원리와 개념 |
| `howto/` | transparent, transparent-vms, ignore-domains, wireshark-tls, install-system-trusted-ca-android, kubernetes | 상황별 가이드 |
| `cli-tutorials/` | 01~04, whats-next | 터미널 UI 4단계 튜토리얼 (영상 중심, 본문 짧음) |
| `web-tutorials/` | web-01~05 | mitmweb 튜토리얼. **본문이 제목 수준으로 짧음**(영상 임베드로 보임, 추론) |
| `tutorials/` | client-replay, highscores | 응용 예제 |
| `addons/` | overview, event-hooks, options, commands, contentviews, api-changelog, examples | 파이썬 애드온 개발 |

---

## 1. 소개 (`_index.md`)

- 한 줄 정의: HTTP/1, HTTP/2, WebSocket용 **SSL/TLS 지원 가로채기 프록시** 도구 모음.
- 기능: HTTP(S) 요청·응답 가로채서 즉석 수정 / 대화 저장 후 재생·분석 / 클라이언트 쪽 재생 / 녹화한 서버 응답 재생 / reverse 모드 / **transparent 모드(macOS, Linux)** / 파이썬 스크립팅 / 인터셉트용 인증서 즉석 생성.
- 세 도구는 **같은 코어의 서로 다른 프런트엔드**:

| 도구 | 성격 | 특징 |
|---|---|---|
| `mitmproxy` | 터미널 UI | 모든 flow를 메모리에 보관 → **작은 표본 분석용**. 화면마다 `?`로 문맥 도움말 |
| `mitmweb` | 브라우저 UI | 같은 메모리 보관 특성. **베타**: 노출된 기능은 안정적이나 mitmproxy 기능을 많이 못 담음 |
| `mitmdump` | 비대화형 CLI | "tcpdump for HTTP". 저장·필터·재생·스크립트 실행 |

mitmdump 예(문서 명시):

| 목적 | 명령 |
|---|---|
| 저장 | `mitmdump -w outfile` |
| 저장한 파일을 필터링해서 다른 파일로 | `mitmdump -nr infile -w outfile "~m post"` (`-n`: 프록시 포트 바인딩 안 함) |
| 클라이언트 재생 | `mitmdump -nC outfile` (재생 결과를 `-w dstfile`로 저장 가능) |
| 스크립트 실행 | `mitmdump -s script.py` |
| 파일을 스크립트로 변환 | `mitmdump -ns script.py -r srcfile -w dstfile` |

---

## 2. 시작하기 (`overview/`)

### 2.1 설치 (`installation.md`)
- Windows: mitmproxy.org 설치 프로그램 또는 Microsoft Store(자동 업데이트). 설치 후 세 도구가 PATH에 추가. standalone 바이너리는 임시 폴더에 풀어서 시작이 느림. Windows Terminal 권장, WSL도 지원(Linux 방식).
- macOS: `brew install --cask mitmproxy`. Linux: standalone 바이너리 권장(배포판 패키지는 최신과 어긋날 수 있음).
- PyPI: `uv tool install mitmproxy` (패키지 추가는 `--with`). Docker: DockerHub 공식 이미지.
- 바이너리·Docker는 의존성이 릴리스 시점에 고정 → **정기 업데이트 권장**. "phone home" 안 함(업데이트 확인 없음).
- **삭제 절차는 문서에 없음.**

### 2.2 첫 실행 (`getting-started.md`)
1. 도구 하나 실행 → 기본은 regular 프록시, `http://localhost:8080`.
2. 브라우저·기기에 프록시 설정(방식은 검색해서 맞추라고 안내).
3. `http://mitm.it` 접속 → CA 설치 페이지가 뜨면 연결 성공 → CA 설치.
4. `https://mitmproxy.org`가 flow로 보이면 TLS 복호화 정상.

### 2.3 옵션 기반 기능 모음 (`features.md`)
모두 옵션(`--set` 또는 설정 파일)으로 켠다. 패턴 구분자는 첫 글자로 정해진다(`/`, `|`, `:` 등).

| 기능 | 옵션 | 핵심 |
|---|---|---|
| Anticache | `anticache` | `if-none-match`, `if-modified-since` 제거 → 304 방지, 완전한 응답 확보. 재생 때 유용 |
| Blocklist | `block_list` | `/필터/상태코드`. 444는 응답 없이 연결 종료. 예 `:~d google-analytics.com:404`. "example.com만 허용" 패턴은 비HTTP 프로토콜로 우회 가능하므로 보안 수단 아님 |
| Client replay | — | 저장한 요청을 하나씩 순차 재전송(원래의 동시성과 다를 수 있음) |
| Server replay | `server_replay` | 저장한 응답을 매칭해서 반환. 기본은 URL+메서드로만 매칭. 날짜·쿠키 만료 헤더를 **상대 시간 유지하도록 갱신**(`server_replay_refresh`로 끔) |
| Map Local | `map_local` | URL 정규식에 맞는 요청을 로컬 파일·디렉터리로 대체. 파일 변경은 즉시 반영(캐시 없음), 디렉터리 이탈 불가 |
| Map Remote | `map_remote` | 요청 URL을 치환해 다른 곳에서 가져옴 |
| Modify Body | `modify_body` | `/필터/정규식/치환` 또는 `@파일` 내용으로 치환. **스트리밍된 본문에는 효과 없음** |
| Modify Headers | `modify_headers` | 헤더 추가·덮어쓰기·삭제(값이 비면 삭제), `@파일` 가능 |
| Proxy Authentication | `proxyauth` | HTTP Basic만 지원. 인증 헤더는 서버로 전달 안 함. transparent 모드와 궁합이 나쁘고 SOCKS 인증은 미구현 |
| Sticky Auth / Cookies | `stickyauth`, `stickycookie` | 한 번 본 Authorization 헤더 / 가장 최근 쿠키를 이후 요청에 자동 부착(curl 등으로 인증된 리소스에 접근할 때 유용). Digest 인증 미지원 |
| Streaming | `stream_large_bodies` | 크기 기준 초과 시 본문을 버퍼링 없이 중계 → **본문 접근·수정 불가**. 헤더는 여전히 버퍼링. 스크립트에서 `.stream = True`로 개별 지정 |

---

## 3. 개념 (`concepts/`)

### 3.1 동작 원리 (`how-mitmproxy-works.md`)
- **Explicit HTTP**: 클라이언트가 `GET http://example.com/index.html` 형태(절대 URL)로 프록시에 요청 → 프록시가 서버로 전달.
- **Explicit HTTPS**: `CONNECT example.com:443`으로 터널을 요청. 일반 프록시는 내용을 못 보지만 mitmproxy는 서버인 척(클라이언트에게)·클라이언트인 척(서버에게) 양쪽을 중개하며 복호화. 그러려면 mitmproxy가 **신뢰된 CA**여야 함.
- 인증서를 정확히 만들기 위한 세 가지 복잡성과 해법:
  1. 호스트명 모름(IP로 CONNECT) → **업스트림 인증서 sniffing**: 클라이언트를 잠시 멈추고 서버와 먼저 TLS 연결해 인증서의 CN을 확인.
  2. SAN(대체 도메인) → CN뿐 아니라 SAN도 복사해 가짜 인증서에 넣음.
  3. SNI → 클라이언트 핸드셰이크에서 SNI가 오는 시점까지 진행시킨 뒤 멈추고, 그 SNI로 서버에 연결.
- 전체 HTTPS 흐름 8단계(CONNECT → `200 Connection Established` → 클라이언트 TLS 시작 → mitmproxy가 서버와 TLS → 서버 인증서 수신 → 가짜 인증서 생성·핸드셰이크 재개 → 요청 → 서버로 전달).
- **Transparent**: 방화벽(iptables, pf)이 연결을 프록시로 돌리고, 플랫폼 모듈(`mitmproxy/platform`)이 **원래 목적지**를 조회. TLS는 ClientHello를 보고 포트와 무관하게 자동 감지.

### 3.2 모드 (`modes.md`) — 모든 모드는 세 도구에서 사용 가능

| 모드 | 시작 예 | 요점 |
|---|---|---|
| **Regular** | (기본) | 가장 단순·안정. 안 보이면 이벤트 로그에서 `client connect` 확인(없으면 주소·포트 오류, 또는 Wi-Fi 클라이언트 격리). 프록시 설정을 무시하는 앱은 다른 모드 필요 |
| **Local Capture** | `--mode local`, `local:curl`, `local:42`, `local:!curl`, `local:curl,wget` | 같은 기기의 앱을 투명하게 캡처, 앱은 프록시를 모름. **Windows·Linux·macOS 지원**. Linux 제약: 송신만, `sudo`로 권한 있는 하위 프로세스 필요(mitmweb은 CLI에서 직접 `--mode local`로 시작해야 비밀번호 입력 가능), 커널 6.8+ 공식 지원, 프로세스명 16자까지만 매칭, 컨테이너는 host network만, **WSL 미지원**. macOS 제약: 송신만 |
| **WireGuard** | `mitmweb --mode wireguard` | mitmproxy가 WireGuard VPN 서버가 됨. 대상 기기에서 WireGuard 클라이언트로 제공된 설정을 import. 사용자 영역 동작(**관리자 권한 불필요**). 기본 51820/udp, 키는 `~/.mitmproxy/wireguard.conf`. 제약: **mitmproxy가 도는 호스트 자신의 트래픽은 불가**, IPv6 지원 제한적. `AllowedIPs`로 터널 대상 범위 조절 |
| **Reverse** | `--mode reverse:https://example.com` | 서버 앞에 두는 프록시. 기본 포트 8080(DNS는 53), `@포트`로 변경, 여러 `--mode` 동시 가능. 스킴 표: `http`/`https`/`dns`/`http3`/`quic`/`tcp`/`tls`/`udp`/`dtls`. Host 헤더는 자동으로 업스트림에 맞춰 재작성(`keep_host_header`로 끔). **응답 속 절대 URL은 재작성 안 함**, 대화형 사이트 복제에는 부족 |
| Transparent | `--mode transparent` | **Linux, macOS**. 네트워크 레벨에서 트래픽을 돌림. 문서도 "WireGuard·Local Capture를 먼저 고려"하라고 권장(설정이 쉽고 UDP도 지원) |
| TUN | `sudo mitmdump --mode tun` | **Linux** 전용. 가상 네트워크 장치 생성, root 또는 `CAP_NET_ADMIN` 필요. 대부분 로컬 라우팅 테이블을 직접 설정해야 함 |
| Upstream | `--mode upstream:http://host:8081` | 모든 요청을 다른 프록시로 연결(체이닝) |
| SOCKS | `--mode socks5` | SOCKS5 프록시(연결 설정만 SOCKS) |
| DNS | `--mode dns` | DNS 서버(기본 53, `dns@5353`). OS 리졸버 사용, `dns_use_hosts_file`, `dns_name_servers` 옵션 |

Reverse 활용 예(문서): 내부 API 앞에서 디버깅, hosts 파일로 개발 서버 트래픽 기록, 장난감 프로젝트에 TLS 붙이기(`mitmdump -p 443 --mode reverse:http://localhost:80/`), `reverse:tls://host:port`로 HTTP 아닌 (D)TLS 관찰, `reverse:dns://8.8.8.8`로 DNS 캡처.

### 3.3 인증서 (`certificates.md`)
- 첫 실행 때 `~/.mitmproxy`에 **PC마다 고유한 CA** 생성. 파일: `mitmproxy-ca.pem`(인증서+**개인키**), `mitmproxy-ca-cert.pem`, `.p12`(Windows), `.cer`(Android 일부).
- 설치: mitm.it(가장 쉬움) 또는 수동. 문서의 예: curl `--cacert`, wget `--ca-certificate`, macOS `security add-trusted-cert`, Windows `certutil -addstore root mitmproxy-ca-cert.cer`, Java `keytool`, iOS(설정 > 일반 > 인증서 신뢰 설정에서 **전체 신뢰 활성화**), Android 등.
- 인증서 pinning 앱은 거부 → 내용이 불필요하면 `ignore_hosts`로 제외, 필요하면 앱 패치(apk-mitm, objection, ssl-kill-switch2, android-unpinner).
- 사용자 지정: `--certs *.example.com=cert.pem`(서버 인증서), `--set confdir=DIR`(CA 위치, 없으면 생성). 자체 CA는 `Key Usage: Certificate Sign`, `Basic Constraints: CA:TRUE` 필요.

### 3.4 프로토콜 (`protocols.md`)

| 프로토콜 | 기반 | 알려진 제한 |
|---|---|---|
| HTTP/1 | 자체 스택(h11) | 트레일러 미지원. 문법 위반을 일부러 그대로 전달 |
| HTTP/2 | hyper-h2 | PRIORITY 프레임 무시, Push Promise 미광고, **h2c(평문 HTTP/2) 미지원**. 서버가 h2 미지원이면 HTTP/1로 번역 |
| HTTP/3 | aioquic | reverse·local·WireGuard 모드에서만. client replay 고장, QUIC v1만, cURL 위주 시험 |
| WebSocket | wsproto | replay 불가, PING/PONG은 로그만, 알 수 없는 확장은 경고 후 통과 |
| DNS | 자체 구현 | replay 불가, DoT/DoH/DoQ 미지원 |
| 범용 TCP/TLS | — | TLS는 시작 부분에서 감지해 MITM 후 나머지는 그대로 전달. `tcp_hosts` 옵션으로 명시. **replay 불가, STARTTLS 감지 불가** |
| 범용 UDP/DTLS | — | `udp_hosts` 옵션 |

대부분의 프로토콜은 해당 옵션으로 끌 수 있다.

### 3.5 필터식 (`filters.md`)
- 명령과 옵션 곳곳에서 flow를 고를 때 쓰는 식. 연산자 표는 자동 생성 파일이라 직접 읽지 못함(`~u`, `~m`, `~b`, `~d`, `~q`, `~s`, `~t`, `~h` 등은 문서 예제에서 확인).
- 파이썬 정규식, 대소문자 무시(`MITMPROXY_CASE_SENSITIVE_FILTERS=1`로 변경), 괄호·공백·`~`·따옴표가 든 정규식은 따옴표 필요, 연산자 없는 문자열은 요청 URL 매칭, 기본 이항 연산자는 `&`.
- 대화형 선택자: `@all`, `@focus`, `@shown`, `@hidden`, `@marked`, `@unmarked`.

### 3.6 옵션 (`options.md`)
- 공통 설정 파일 `~/.mitmproxy/config.yaml`(YAML). **런타임 동작 전부가 옵션**이고 CLI 플래그는 대부분 옵션의 별칭.
- 전체 목록은 `--options`(주석 달린 YAML 덤프). mitmproxy/mitmweb에는 옵션 편집기가 있어 변경이 즉시 반영, 설정 파일로 저장 가능. 지정: `--set 옵션=값`(예 `mitmweb --set ignore_hosts=example.com --set ignore_hosts=example.org`).
- 애드온이 정의한 옵션도 같은 방식으로 다뤄짐.

### 3.7 명령 (`commands.md`)
- 사용자가 애드온과 상호작용하는 수단. 대화형 UI의 모든 동작은 **키에 바인딩된 명령**. `:`로 명령 프롬프트(탭 완성), 레퍼런스는 `--commands`, `C` 키로 명령 브라우저.
- flow 인자는 필터식으로 지정: `:replay.client @focus`, `@all`, `"~d google.com"`.
- 키 바인딩 사용자 정의: `~/.mitmproxy/keys.yaml`(`key`, `cmd` 필수, `context`, `help`).

---

## 4. 상황별 가이드 (`howto/`)

| 문서 | 요지 |
|---|---|
| `transparent.md` | Linux(iptables `REDIRECT`, IP forwarding, ICMP redirect 차단), OpenBSD·macOS(pf), **Windows**(관리자 권한, `IPEnableRouter` 레지스트리, `RemoteAccess` 서비스, 송신 ICMP redirect 차단 후 `mitmproxy --mode transparent --showhost`), 테스트 기기의 기본 게이트웨이를 mitmproxy 머신으로 지정. 호스트 자체 트래픽을 돌리는 우회법. "Full transparent mode"(Linux)는 mitmproxy 7 이상에서 사용 불가. 새 방식(WireGuard·local)이 훨씬 쉽다고 안내 |
| `transparent-vms.md` | VirtualBox + Ubuntu 프록시 VM + dnsmasq(DHCP/DNS) + iptables로 내부 네트워크의 VM 전체를 투명 프록시 |
| `ignore-domains.md` | `--ignore-hosts <정규식>`(`host:port`와 매칭). 용도: pinning 앱(Twitter 앱, Windows Update, App Store), 불필요한 트래픽. 한계: transparent 모드는 IP와 SNI로 매칭, regular·upstream 모드는 **명시적 HTTP 요청은 무시되지 않고 CONNECT에만 적용**. 대안: `view_filter`(표시만 제한), `tcp_hosts`(비HTTP 내용 보기), streaming(큰 본문) |
| `wireshark-tls.md` | `SSLKEYLOGFILE=경로 mitmproxy`로 TLS 마스터 시크릿 기록 → Wireshark의 `(Pre)-Master-Secret log filename`에 지정하면 복호화. 다른 프로그램(Firefox, Chrome)도 이 변수를 따르므로 문제 시 `MITMPROXY_SSLKEYLOGFILE` 사용 |
| `install-system-trusted-ca-android.md` | Android 7부터 앱이 **사용자 CA를 무시**하므로 에뮬레이터의 시스템 인증서 저장소에 설치(Magisk 방식 / `-writable-system` 방식, API 28 기준 분기). 앱이 자체 CA를 쓰면 앱 패치 필요 |
| `kubernetes.md` | 외부 프로젝트 kubetap(kubectl 플러그인)으로 Kubernetes Service에 mitmproxy 배치 — 링크만 있음 |

---

## 5. 튜토리얼

- **`cli-tutorials/`**(영상 중심, 본문 짧음): 01 UI(flow 목록) → 02 intercept(`set intercept <필터>`, 키 `i`, 예 `~u <정규식>`) → 03 intercept한 요청 수정 후 전송 → 04 replay(client replay = 같은 요청 재전송, server replay = 같은 요청에 녹화 응답 반환). `whats-next`: 튜토리얼은 curl 요청으로 진행했고 브라우저 등은 프록시 설정 필요.
- **`web-tutorials/`**: mitmweb 5단계(UI, intercept, 분석, 수정, replay). 본문이 거의 없음.
- **`tutorials/client-replay.md`**: `mitmdump -w 파일`로 Wi-Fi 로그인 과정을 녹화 → `mitmdump -C 파일`로 재생(자동 접속 스크립트 활용). 불필요한 CSS·JS·이미지 요청은 mitmproxy로 열어 정리 가능.
- **`tutorials/highscores.md`**: iPhone 게임의 Game Center 점수 제출 POST를 mitmproxy로 확인·수정하는 예(CA 설치 + 폰의 프록시 설정). **보안 점검 사례 소개이며, 남의 서비스에 적용하면 부정 행위일 수 있음**(추론: 내용상).

---

## 6. 애드온 개발 (`addons/`)

- **개념**: mitmproxy 자체 기능의 상당수가 내장 애드온. 애드온은 **이벤트 훅 메서드**(`request`, `response` 등)를 가진 객체이고, 모듈의 전역 `addons` 리스트에 넣으면 로드. `mitmdump -s ./anatomy.py`(세 도구 모두 같은 플래그). 클래스 없이 모듈 수준 함수만 두는 약식 문법도 가능.
- **라이브 리로드**: `-s`로 올린 스크립트는 파일 수정 시간을 감시해 약 1초 내 재등록(프록시 재시작·다른 애드온 상태 유지). import/configure/running 오류는 로그만 남기고 이전 버전이 해제된 상태로 남음, 이벤트 핸들러 오류는 로그만 남기고 애드온 유지.
- **테스트**: 일반 파이썬 파일이므로 직접 import해서 핸들러 호출(내부 테스트 헬퍼는 안정 API 아님).
- **옵션**(`options.md`): `load` 이벤트의 `Loader`로 타입이 있는 옵션 선언. 지원 타입 `str`/`int`/`float`/`bool`, `Optional`, `Sequence`. `configure` 이벤트에서 변경 검증, `OptionsError`를 던지면 해당 변경 전체 롤백. 예: `env http_proxy=http://localhost:8080 curl -I http://google.com`로 확인, mitmproxy에서 `O` 키로 옵션 편집기.
- **명령**(`commands.md`): `@command.command("애드온.이름")` 데코레이터, 타입 주석 필수(반환 타입 포함), flow 시퀀스 인자는 필터식으로 확장(`:myaddon.addheader @focus`).
- **콘텐츠 뷰**(`contentviews.md`): 바이너리 본문을 사람이 읽게 예쁘게 출력. 일부는 대화형(편집 후 다시 인코딩). `Contentview` 기반 클래스, 출력은 스타일 없는 `str`, 구문 강조는 정해진 형식 중 선택(tree-sitter 기반). 핫 리로드 지원(mitmproxy만 자동 재렌더링, mitmweb은 아님).
- **API 변경 이력**(`api-changelog.md`): mitmproxy 12에서 Contentviews API가 크게 단순화, `mitmproxy.dns.Message` → `DNSMessage`. 9.1에서 `connection.Client/Server`는 키워드 인자만 허용.
- **예제**: `examples/addons/`에 30여 개(`http-add-header.py`, `websocket-simple.py` 등).

---

## 7. 문서 간 불일치·주의

- `_index.md`는 transparent 모드를 "macOS와 Linux"라고 하지만 `howto/transparent.md`에는 **Windows 절차**도 있음(관리자 권한, 라우팅 서비스). 반면 `modes.md`의 Transparent는 "Availability: Linux, macOS". → Windows에서는 transparent보다 **Local Capture가 공식 권장 경로**로 보임(추론).
- `_index.md`의 "mitmweb 베타" 표기와 달리 `getting-started`는 세 도구를 동등하게 소개. 기능 격차는 mitmweb이 더 클 수 있음.
- 튜토리얼과 하이스코어 예제는 오래된 앱(iOS, 구형 Ubuntu)을 전제로 해서 그대로 따라 하기 어려울 수 있음(추론).

## 8. 이 문서로 아직 답할 수 없는 것 (`미확인`)

- Windows에서 Local Capture의 실제 권한 요구와 동작(Linux 쪽 제약만 문서화됨).
- 특정 프로그램(예: Node.js CLI)이 프록시 환경변수와 CA를 따르는 방법(클라이언트 쪽 사항).
- 자동 생성 표(필터 연산자, 전체 옵션 목록)의 정확한 내용 → `mitmproxy --options`, 공개 사이트 또는 `docs/build.py` 실행으로 확인 필요.
- 삭제 절차(문서 없음, overview.md 3.2절 참고).
