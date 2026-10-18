---
sha: "7a684934907a8c7feaafe9ff1ccfd9d45cc26faf"
created: 2026-10-18
updated: 2026-10-18
sources:
  - scrapling/fetchers/__init__.py
  - scrapling/engines/static.py
  - scrapling/engines/constants.py
  - scrapling/engines/toolbelt/fingerprints.py
  - scrapling/engines/toolbelt/proxy_rotation.py
  - scrapling/engines/_browsers/_base.py
  - scrapling/engines/_browsers/_stealth.py
  - scrapling/engines/_browsers/_controllers.py
  - scrapling/engines/_browsers/_validators.py
  - scrapling/spiders/spider.py
  - scrapling/spiders/engine.py
  - docs/fetching/choosing.md
  - docs/fetching/static.md
  - docs/fetching/stealthy.md
  - docs/overview.md
---

# [Q1] 정적/동적 판단과 봇 차단 우회 전략

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: `코드 확인` (실제 사이트에 실행해 보지 않았다. 우회가 **실제로 통하는지**는 `미확인`)

---

## 1. 질문 및 결론

- **질문 1**: 크롤링할 사이트가 정적인지 동적인지 알아서 판단하는가?
- **결론 1**: **아니다.** 자동 판단 코드를 찾지 못했다. 사용자가 `Fetcher`(HTTP만) / `DynamicFetcher`(브라우저) / `StealthyFetcher`(스텔스 브라우저) 중 직접 고른다. 문서도 "각 fetcher는 용도가 다르다"며 비교표로 고르게 한다 (`docs/fetching/choosing.md`).
- **질문 2**: 봇 차단(Cloudflare Turnstile 등)을 어떻게 우회하는가?
- **결론 2**: 한 가지 마법이 아니라 **3겹**이다. ① 요청 자체를 진짜 브라우저처럼 보이게 만들기(HTTP 위장) ② 브라우저를 쓰되 자동화 흔적 지우기(스텔스 브라우저) ③ Turnstile 위젯이 뜨면 **사람처럼 그 칸의 좌표를 클릭**해서 통과(solver). 그 위에 프록시 교체와 재시도가 붙는다. 암호를 푸는 방식이 아니라 "탐지되지 않는 진짜 브라우저로 사람이 하는 클릭을 흉내"내는 방식이다.

---

## 2. 동작 설명

### 2.1 정적/동적 판단: 없음

- `Fetcher`는 HTTP 요청만 보낸다. JS를 실행하지 않으므로 JS로 그려지는 내용은 못 본다 (`choosing.md`: JavaScript loading ❌).
- 브라우저 fetcher 둘은 JS까지 실행한다 (`load_dom` 기본 켜짐, `network_idle`, `wait_selector` 옵션).
- `is_static`, `detect` 같은 식별자를 `scrapling/` 전체에서 검색했으나 없었다 (`ad_domains.py` 제외).
- **Spider 쪽도 자동 전환은 없다**: 차단 응답이면 같은 요청을 재시도할 뿐이다. 차단 판정 기본값은 상태코드 `{401, 403, 407, 429, 444, 500, 502, 503, 504}` (`spiders/spider.py` `BLOCKED_CODES`, `is_blocked`). 여러 세션(HTTP, 브라우저)을 만들어 요청마다 `sid`로 고르게 할 수는 있지만(`spiders/request.py` `sid`) 고르는 건 사용자 코드다.
- 대신 "먼저 `Fetcher`로 하다가 **차단당하면** 스텔스 브라우저로 올린다"는 패턴을 문서가 예제로 보여 준다(`docs/spiders/proxy-blocking.md` "Customizing Retries": `retry_blocked_request`에서 `request.sid = "stealth"`). 이것도 사용자가 코드로 짜는 것이고, 판단 기준은 "JS가 필요한가"가 아니라 "차단됐는가"다. 자세한 설계는 [Q2](./q2-bot-evasion-lessons.md) 참고. (정정: 처음 작성 때 이 예제를 놓쳐 "문서에서 확인하지 못했다"고 썼다.)

### 2.2 봇 차단 우회 3겹

봇 차단 시스템은 대략 (a) 요청의 겉모습(헤더, TLS 지문), (b) 브라우저 환경(자동화 흔적, 지문), (c) 행동·챌린지(Turnstile 클릭)를 본다. Scrapling은 각 층마다 대응 코드를 둔다.

#### 1겹. HTTP 위장 (`Fetcher`, `engines/static.py`)

| 대응 | 하는 일 | 근거 |
|---|---|---|
| TLS 지문 모방 | `curl_cffi`의 `impersonate`로 "Chrome이 보내는 TLS 핸드셰이크"를 흉내. 기본값 `"chrome"`, 리스트를 주면 요청마다 랜덤 선택 | `static.py` `_ConfigurationLogic.__init__`(`impersonate` 기본 `"chrome"`), `_select_random_browser` |
| 진짜 헤더 | `browserforge`로 실제 브라우저 헤더 조합 생성(Chrome ≥149, Firefox ≥147, Edge ≥145, OS는 현재 기기 기준) | `toolbelt/fingerprints.py` `generate_headers`, `MINIMUM_VERSION=149` |
| Google referer | 검색엔진에서 들어온 것처럼 `referer: https://www.google.com/` | `static.py` `_headers_job` |
| 프록시 | 단일 또는 `ProxyRotator`(기본 순환, 전략 함수 교체 가능) | `toolbelt/proxy_rotation.py` |
| 재시도 | 기본 3회 | `static.py` `retries` 기본 3 |

설명: TLS 지문이란 "서버가 연결 순간 보는 클라이언트 특유의 암호 설정 조합"이다. Python `requests`는 이 지문이 브라우저와 달라서 바로 들킨다. `curl_cffi`는 실제 브라우저와 같은 지문으로 연결한다.

#### 2겹. 스텔스 브라우저 (`StealthyFetcher`, `_stealth.py`, `_base.py`)

- **patchright 사용**: `_stealth.py`는 `patchright`를 import한다(자동화 탐지 지점을 고친 Playwright 포크). 반면 `DynamicFetcher` 쪽 `_controllers.py`는 일반 `playwright`를 import한다. 즉 **스텔스 수준 차이는 엔진 자체가 다르다** (`코드 확인`).
- **Chromium 실행 인자**: `STEALTH_ARGS`에 `--disable-blink-features=AutomationControlled`(자동화 표시 제거), `--start-maximized`(헤드리스 판별 우회 주석) 등 약 50개. 기본 자동화 인자 `--enable-automation` 등은 `HARMFUL_ARGS`로 제거 (`engines/constants.py`, `_base.py:447` `ignore_default_args`).
- **환경 일관성**: 해상도 1920×1080, `color_scheme: dark`(주석: creepjs의 `prefersLightColor` 검사 회피), 지역·언어를 브라우저 전체 플래그(`--lang`, `--accept-lang`)로 설정해 Web Worker와의 불일치를 막음(주석: Cloudflare가 이 불일치를 잡는다고 적혀 있음) (`_base.py` `__generate_options__`).
- **지문 대응 옵션**: `block_webrtc`(WebRTC로 실제 IP 새는 것 방지), `hide_canvas`(캔버스 지문에 노이즈. 플래그 `--fingerprinting-canvas-image-data-noise` 전달까지만 확인, **그 플래그가 실제 Chromium에서 동작하는지는 미확인**), `allow_webgl`(기본 켬. 꺼 놓으면 WAF가 의심한다고 주석), `dns_over_https`, `real_chrome`(설치된 진짜 Chrome 사용), `cdp_url`(이미 떠 있는 브라우저에 연결).
- **User-Agent**: 헤드리스일 때 `generate_headers(browser_mode=True)`로 만든 UA를 쓰되, Chrome 버전을 **실제 구동되는 Chromium 버전**으로 맞춘다 (`fingerprints.py` `driven_browser_version`). UA와 실제 브라우저가 어긋나면 탐지되기 때문이다.
- 리소스 차단(`disable_resources`: 이미지·폰트·CSS 등)은 속도용 옵션.

#### 3겹. Cloudflare Turnstile 해결 (`solve_cloudflare=True`)

`StealthyFetcher`에서만 쓰는 옵션이다(`PlaywrightConfig`에는 없고 기본 False, `_validators.py:211`). 켜면 페이지 로딩 직후 `_cloudflare_solver`가 돈다 (`_stealth.py`).

1. **챌린지 종류 판별** (`_base.py` `_detect_cloudflare`): 페이지 HTML에서 `cType: 'non-interactive'` / `'managed'` / `'interactive'` 문자열을 찾는다. 없으면 `challenges.cloudflare.com/turnstile/v…` 스크립트가 있는지 보고 `embedded`(페이지 안에 박힌 위젯)로 분류.
2. **non-interactive**(그냥 기다리면 지나가는 대기 화면): 1초 간격으로 "대기 페이지"가 사라질 때까지 폴링. 사라지면 성공, 아니면 재귀 재시도.
3. **managed/interactive/embedded**(체크박스형): 
   - 위젯 iframe(`challenges.cloudflare.com/cdn-cgi/challenge-platform/...` 패턴)이 뜰 때까지 최대 20회(0.5초) 대기.
   - iframe의 화면 좌표(`bounding_box`)를 얻어 박스 안쪽 `x+26~28, y+25~27` 위치(체크박스 위치)를 `page.mouse.click(..., delay=100~200ms)`로 클릭. 좌표와 클릭 지속시간에 난수를 넣어 매번 조금 다르게 한다.
   - 클릭 뒤 챌린지 문구가 사라졌는지 확인. 남아 있으면 다시 시도. **최대 3회**(`__CF_MAX_SOLVE_ATTEMPTS__`) 후 실패 로그를 남기고 페이지를 그대로 반환.
4. `solve_cloudflare`를 켜면 타임아웃이 60초 미만일 때 자동으로 60초로 올라간다 (`_validators.py` `StealthConfig.__post_init__`).
5. 이 과정은 patchright 브라우저 안에서 진행되므로 1·2겹(진짜 같은 환경)이 전제다. 환경이 의심스러우면 클릭해도 Cloudflare가 통과시키지 않는다.

즉 "Turnstile을 푼다"는 것은 **챌린지를 계산으로 해독하는 것이 아니라**, 탐지되지 않는 브라우저에서 위젯을 알아보고 체크박스 위치를 사람처럼 클릭하는 것이다. 위젯이 Shadow DOM 안에 있어도 iframe 좌표로 클릭하는 방식이라 DOM 접근이 필요 없다는 점이 핵심이다 (코드 주석: "closed Shadow iframe").

#### 보조: 프록시와 재시도 (`_stealth.py` `fetch`)

`retries`만큼 반복하면서 시도마다 `ProxyRotator.get_proxy()`로 새 프록시를 받는다. 실패 원인이 프록시 오류(`net::err_proxy`, `connection refused` 등 문자열 매칭, `is_proxy_error`)면 "프록시 실패, 재시도" 로그를 남기고 다음 시도에서 다른 프록시를 쓴다. 차단 여부(Cloudflare 문구, 403 등)에 따라 프록시를 바꾸는 로직은 fetcher 단계에는 없고, Spider가 `is_blocked`일 때 요청을 복사해 재큐잉하며 `proxy` 인자를 지워 로테이터가 새 프록시를 뽑게 한다 (`spiders/engine.py` 247~257).

### 2.3 요약 그림 (텍스트)

```
요청 ─ Fetcher ───────── curl_cffi: Chrome TLS 지문 + 실제 헤더 + Google referer + 프록시
     │   (JS 못 돌림)
     ├ DynamicFetcher ─── 일반 playwright 브라우저 (JS 실행, 스텔스 약함)
     └ StealthyFetcher ── patchright + 스텔스 인자 + 지문 옵션
                              └ solve_cloudflare=True → 종류 판별 → 대기 or 체크박스 좌표 클릭(최대 3회)
           (공통) ProxyRotator, retries / Spider: 차단 응답이면 재큐잉
```

### 2.4 한계와 주의

- **통과 보장은 없다.** 3회 실패하면 막힌 페이지를 그대로 돌려준다. 실제 사이트별 성공률은 실행해 보지 않았다 (`미확인`).
- README가 직접 한계를 밝힌다: Turnstile만 다루고, Akamai·DataDome·Kasada·Incapsula 같은 상용 방어는 스폰서(Hyper Solutions)의 별도 API를 소개한다 (`README.md` 스폰서 절). 즉 모든 봇 차단을 넘는 도구가 아니다.
- 캔버스 노이즈, 헤더 최소 버전 등은 시간이 지나면 낡는다. 지문 탐지는 계속 변하는 영역이다.
- 사이트의 이용약관·robots.txt·법적 허용 범위는 별개 문제다. 이 문서는 구현 방식을 설명할 뿐 사용을 권하지 않는다.

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 | 식별자 | 설명 |
|---|---|---|---|
| fetcher 구성 | `scrapling/fetchers/__init__.py` | `_LAZY_IMPORTS` | 3종 fetcher, 자동 선택 없음 |
| TLS·헤더 | `scrapling/engines/static.py` | `_ConfigurationLogic`, `_headers_job`, `_select_random_browser` | impersonate 기본 chrome, Google referer |
| 헤더 생성 | `scrapling/engines/toolbelt/fingerprints.py` | `generate_headers`, `driven_browser_version` | browserforge, UA 버전 맞춤 |
| 스텔스 인자 | `scrapling/engines/constants.py` | `STEALTH_ARGS`, `HARMFUL_ARGS` | Chromium 플래그 |
| 스텔스 설정 | `scrapling/engines/_browsers/_base.py` | `StealthySessionMixin.__generate_stealth_options`, `__generate_options__` | WebRTC/WebGL/캔버스/언어 |
| 챌린지 판별 | `scrapling/engines/_browsers/_base.py` | `_detect_cloudflare`, `_challenge_cleared` | `cType` 문자열, turnstile 스크립트 |
| solver | `scrapling/engines/_browsers/_stealth.py` | `_cloudflare_solver`, `__CF_MAX_SOLVE_ATTEMPTS__`, `fetch` | 좌표 클릭, 재시도 |
| 엔진 차이 | `_stealth.py` vs `_controllers.py` | import `patchright` vs `playwright` | 스텔스 수준 차이의 근거 |
| 프록시 | `scrapling/engines/toolbelt/proxy_rotation.py` | `ProxyRotator`, `is_proxy_error` | 순환·오류 판별 |
| 차단 재시도 | `scrapling/spiders/spider.py`, `engine.py` | `BLOCKED_CODES`, `is_blocked`, 재큐잉 | 상태코드 기반 |

---

## 4. 검증 과정 및 실행 결과

- 실행 없음. 소스·docs를 읽고 코드 흐름을 따라갔다.
- 부정 확인: `is_static|is_dynamic|detect.*(js|dynamic|static)|auto.?(select|detect)`를 `scrapling/` 전체에서 검색해 자동 판단 로직이 없음을 확인(광고 도메인 목록 제외).

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] 실제 Turnstile 데모 페이지(예: docs가 쓰는 `nopecha.com/demo/cloudflare`)에서 `solve_cloudflare=True`를 실행해 성공 여부와 로그 확인 (실행 실험, 9장 절차 필요)
- [ ] `--fingerprinting-canvas-image-data-noise`가 Chromium 본가에서 동작하는지
- [ ] patchright가 구체적으로 어떤 탐지 지점(CDP `Runtime.enable` 등)을 고치는지 (패키지 쪽 조사)
- [ ] `adaptive=True` 파서가 요소를 다시 찾는 알고리즘 (`parser.py`, `core/storage.py`)
- [ ] Spider의 `AutoThrottle`·`sid` 기반 다중 세션 라우팅 상세
