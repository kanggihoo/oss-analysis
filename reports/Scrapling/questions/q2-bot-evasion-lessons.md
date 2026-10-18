---
sha: "7a684934907a8c7feaafe9ff1ccfd9d45cc26faf"
created: 2026-10-18
updated: 2026-10-18
sources:
  - scrapling/engines/static.py
  - scrapling/engines/constants.py
  - scrapling/engines/toolbelt/fingerprints.py
  - scrapling/engines/toolbelt/proxy_rotation.py
  - scrapling/engines/toolbelt/navigation.py
  - scrapling/engines/_browsers/_base.py
  - scrapling/engines/_browsers/_stealth.py
  - scrapling/engines/_browsers/_page.py
  - scrapling/engines/_browsers/_validators.py
  - scrapling/spiders/engine.py
  - scrapling/spiders/spider.py
  - scrapling/spiders/session.py
  - scrapling/spiders/throttle.py
  - scrapling/spiders/cache.py
  - docs/spiders/proxy-blocking.md
  - docs/fetching/dynamic.md
  - docs/fetching/choosing.md
---

# [Q2] Scrapling에서 배울 만한 봇 차단 대응 설계

- **상위 개요**: [overview.md](../overview.md)
- **관련**: [Q1 정적/동적 판단과 우회 3겹](./q1-static-dynamic-and-bot-evasion.md) (우회가 *무엇을 하는지*), 이 문서는 *어떻게 설계됐고 무엇을 가져갈 만한지*
- **검증 수준**: `코드 확인` (실행 안 함). 항목별로 표시

---

## 1. 질문 및 결론

- **질문**: 봇 차단 대응을 위해 이 프로젝트에서 배울 만한 설계는 무엇인가?
- **핵심 결론**: Scrapling의 강점은 "뚫는 기술"보다 **설계 원칙**에 있다. 9가지를 꼽는다. (1) 비싼 수단은 막혔을 때만 쓰는 **비용 사다리**, (2) 개별 위장보다 **층 사이 일관성**, (3) 챌린지를 **종류별로 분류하고 횟수를 제한**, (4) 차단 판정을 **교체 가능한 훅**으로, (5) 속도 조절을 차단 신호에 연결, (6) 프록시를 브라우저 구조에 맞게 설계, (7) 렌더링과 싸우지 않고 **XHR을 직접 잡기**, (8) 개발 중 **응답 캐시**로 대상 서버 부담 줄이기, (9) **한계를 솔직히 선**긋기. 단, 기본값은 보수적이지 않다(7절).

---

## 2. 배울 점 9가지

### 2.1 비용 사다리: 싼 수단으로 시작해 막히면 올린다 (`코드 확인` + 문서 예제)

```
Fetcher(HTTP, 싸고 빠름, 데이터센터 프록시)
   │ 차단됨 (is_blocked)
   ▼
StealthyFetcher(브라우저, 느리고 무거움, 주거용/모바일 프록시)
```

- `docs/spiders/proxy-blocking.md`의 최종 예제: `requests` 세션 + 싼 프록시 로테이터, `stealth` 세션(`lazy=True`) + 비싼 프록시 로테이터. `retry_blocked_request`에서 `request.sid = "stealth"`로 바꾼다.
- `lazy=True`는 해당 세션을 **처음 쓰일 때까지 시작하지 않는다** (`spiders/session.py` `_lazy_sessions`). 브라우저는 막힌 요청이 생기기 전엔 뜨지 않는다.
- 가져갈 점: 모든 요청에 가장 강한 수단을 쓰지 말고, 수단을 비용 순으로 줄 세워 **실패 신호로 승격**시킨다. 비용과 탐지 노출을 함께 줄인다.

### 2.2 일관성: 층마다 따로 속이면 어긋나서 들킨다 (`코드 확인`)

탐지는 "하나가 이상한가"보다 **"서로 안 맞는가"** 를 본다. 코드에 이를 의식한 곳이 여러 군데 있다.

| 맞추는 대상 | 어떻게 | 근거 |
|---|---|---|
| UA의 Chrome 버전 ↔ 실제 구동 브라우저 버전 | 설치된 playwright/patchright의 `browsers.json`에서 Chromium 버전을 읽어 UA 문자열의 `Chrome/NNN`을 교체 | `fingerprints.py` `driven_browser_version`, `generate_headers(browser_mode=True)` |
| 헤더 ↔ TLS 지문 | `impersonate`를 쓰면 curl이 맞는 헤더를 만들고, 쓰지 않을 때만 browserforge 헤더를 덧붙임 | `static.py` `_headers_job`("Curl will generate the suitable headers") |
| OS 이름 ↔ 헤더의 OS | 현재 기기 OS(`platform`)로 헤더 생성 | `fingerprints.py` `get_os_name` |
| 언어 ↔ Web Worker | 컨텍스트 옵션 `locale`은 메인 스레드만 바꾸므로 Worker와 불일치 → 실행 플래그 `--lang`, `--accept-lang`로 브라우저 전체에 적용 (주석에 "WAFs like Cloudflare flag the mismatch") | `_base.py` `__generate_options__` |
| WebRTC ↔ 프록시 | WebRTC가 프록시를 우회해 실제 IP를 흘리지 않게 플래그 | `_base.py` `block_webrtc` |
| WebGL | 끄면 오히려 의심받는다고 보고 **기본 켬** (주석: "many WAFs now check if WebGL is enabled") | `_base.py`, `StealthyFetcher` 인자 설명 |
| 색 구성 | `color_scheme: dark` (주석: creepjs의 `prefersLightColor` 검사 회피) | `_base.py` `__validate_routine__` |

- 가져갈 점: 위장 기능을 추가할 때마다 "다른 층과 모순되지 않는가"를 점검한다. 가장 흔한 실수는 UA만 바꾸고 나머지를 그대로 두는 것이다.

### 2.3 위장 층을 구분해서 각각 다른 도구로 (`코드 확인`)

| 층 | 서버가 보는 것 | Scrapling의 도구 |
|---|---|---|
| 연결 | TLS 핸드셰이크 모양 | `curl_cffi` impersonate |
| 요청 | 헤더 조합, referer | `browserforge`, Google referer |
| 브라우저 환경 | 자동화 흔적, 지문(캔버스·WebGL·WebRTC) | `patchright`, Chromium 플래그 |
| 행동 | 챌린지 위젯 클릭 방식 | 좌표 클릭 + 난수 |

- 가져갈 점: "봇 탐지 우회"를 하나의 기능으로 보지 말고 **층별 문제로 쪼갠 뒤 층마다 알맞은 도구**를 쓴다. 가벼운 층(연결·요청)에서 해결되면 브라우저를 띄울 필요가 없다.

### 2.4 챌린지 처리: 분류 → 종류별 전략 → 횟수 제한 → 우아한 실패 (`코드 확인`)

`_cloudflare_solver`의 구조 (`_stealth.py`, `_base.py`):

1. **분류 먼저**: `non-interactive`(기다리면 통과), `managed`/`interactive`(클릭 필요), `embedded`(페이지 안 위젯). 종류마다 다른 경로.
2. **성공 판정은 "챌린지가 사라졌는가"**: 클릭했다는 사실이 아니라 페이지에서 챌린지 표식이 없어졌는지(`_challenge_cleared`)로 확인.
3. **준비될 때까지 기다림**: iframe이 뜨고 보일 때까지 폴링 (`frame_element().is_visible()`), 20회×0.5초 제한.
4. **좌표 기반 접근**: Shadow DOM 안에 있어도 iframe의 `bounding_box`로 클릭 위치를 계산하므로 DOM 접근이 불필요.
5. **재시도 상한 3회**(`__CF_MAX_SOLVE_ATTEMPTS__`), 초과하면 에러 로그 후 **막힌 페이지를 그대로 반환**. 무한 루프도 예외 폭발도 아니다.
6. **타임아웃 하한**: 해결을 켜면 타임아웃을 60초 이상으로 자동 상향 (`_validators.py` `__post_init__`).
7. 클릭 좌표(`+26~28`, `+25~27`)와 클릭 지속(100~200ms)에 난수.

- 가져갈 점: 외부 서비스의 상태 머신을 다룰 때 이 틀이 유용하다. "종류 분류 → 대기 조건 → 성공 판정(결과 기준) → 상한 있는 재시도 → 실패 시 호출자가 판단하도록 그대로 반환".
- 한계: 분류가 `cType: 'managed'` 같은 **페이지 속 문자열**에 의존한다. 상대가 문구를 바꾸면 바로 깨진다 (`추론`, 코드가 문자열 매칭임은 `코드 확인`).

### 2.5 차단 판정을 교체 가능한 훅으로 (`코드 확인`)

- 기본 판정은 상태코드 집합 하나다 (`spider.py` `BLOCKED_CODES`, `is_blocked`). 본문 검사("access denied" 등)는 사용자가 `is_blocked`를 오버라이드해서 넣는다 (`proxy-blocking.md`).
- 재시도 시 엔진이 하는 일 (`spiders/engine.py` 247~264): 요청 복사 → 재시도 횟수 +1 → **우선순위 낮춤**(바로 재시도하지 않음) → `dont_filter=True`(중복 제거 우회) → **이전 프록시 인자 삭제**(로테이터가 새 프록시를 뽑게) → 사용자 훅 `retry_blocked_request` 호출 → 재큐잉. 상한 `max_blocked_retries`(기본 3)는 세션의 네트워크 재시도 횟수와 **별개 카운터**.
- 가져갈 점: "무엇이 차단인가"는 사이트마다 다르므로 코어는 합리적 기본값만 두고 **판정과 대응을 확장점으로 분리**한다. 재시도 요청에서 상태를 어디까지 지울지(프록시) 명시하는 것도 좋은 습관이다.

### 2.6 속도 조절을 차단 신호에 연결 (`코드 확인`)

`AutoThrottle` (`spiders/throttle.py`):

- 도메인별 지연을 응답 지연 시간으로 갱신: `new = max((현재 + 목표)/2, 목표)`, 목표 = `latency / target_concurrency`.
- 차단되면 지연을 **2배**로(`BLOCK_BACKOFF_FACTOR=2.0`) 하거나, 서버가 `Retry-After` 헤더(초 또는 HTTP 날짜)를 주면 **그 값만큼** 기다림. "차단이 속도를 올리는 일은 없다"(`max(new, penalty, current)`).
- 최대 지연 60초, 시작 지연 5초 기본.
- 가져갈 점: 차단 대응을 "더 잘 숨기기"로만 보지 말고 **서버가 보낸 신호(429, `Retry-After`)에 먼저 반응해 속도를 낮추는 것**도 같은 층의 해법이다. 서버를 덜 괴롭히는 것이 가장 싸게 안 걸리는 방법이다.
- 주의: 기본값은 꺼져 있다 (`autothrottle_enabled: False`, 7절).

### 2.7 프록시를 브라우저 구조에 맞게 (`코드 확인` + 문서)

- 브라우저는 **탭 단위로 프록시를 못 바꾼다**. 그래서 `ProxyRotator`를 쓰면 요청마다 **새 브라우저 컨텍스트**를 만들어 그 프록시를 적용하고 끝나면 닫는다(`_base.py` `_page_generator`의 proxy 분기, 문서 주석). 프록시 없을 땐 영속 컨텍스트 + 탭 풀(`_page.py` `PagePool`, 세션의 `max_pages`로 상한)로 재사용.
- `ProxyRotator`: 락으로 스레드 안전, 순환이 기본이고 `(proxies, index) -> (proxy, next_index)` 함수로 전략 교체(랜덤·가중치 예제는 문서). 문자열·Playwright dict 모두 지원.
- 프록시 오류 판별은 오류 메시지 문자열 매칭(`net::err_proxy`, `connection refused` 등, `is_proxy_error`). 간단하지만 브라우저/HTTP 오류를 한 함수로 처리.
- 요청 단위 `proxy=`로 특정 페이지만 지역 프록시 지정 가능.
- 가져갈 점: 격리 단위(탭/컨텍스트/브라우저)와 프록시 적용 단위가 맞는지 확인하고, 오류 상황에서 풀이 새지 않도록 `finally`로 컨텍스트를 닫는 구조를 따른다. 비용 사다리(2.1)와 결합해 프록시 등급도 나눈다.

### 2.8 렌더링과 싸우지 않고 데이터 경로를 잡는다: `capture_xhr` (`문서 확인`, 코드 연결 일부)

- 브라우저 세션에 정규식을 주면 페이지 로딩 중 발생한 XHR/fetch 응답을 `response.captured_xhr`에 모은다 (`docs/fetching/dynamic.md`, `_base.py` `_create_response_handler`의 `xhr_pattern`).
- 가져갈 점: SPA에서 화면을 파싱하기보다 화면이 호출하는 **내부 API 응답**을 가로채면 더 안정적이고, 이후에는 그 API만 가벼운 HTTP로 호출하는 단계(2.1의 아래 칸)로 내릴 수 있다. 탐지 회피라기보다 비용 절감 설계다 (이후 단계로 내리는 방법은 `추론`).

### 2.9 개발 중 응답 캐시: 같은 서버를 반복 두드리지 않는다 (`코드 확인`)

- `ResponseCacheManager`(`spiders/cache.py`)는 요청 지문(fingerprint)을 키로 응답을 디스크 JSON(본문 base64)에 저장하고, 개발 중 재실행 시 캐시 적중이면 네트워크 호출 없이 콜백만 돌린다 (`spiders/engine.py` 캐시 적중 분기, `stats.cache_hits`).
- 가져갈 점: 파서를 고치며 같은 페이지를 수십 번 요청하면 그 자체가 차단 사유가 된다. 응답을 저장해 두고 파싱만 반복하는 습관은 가장 값싼 "봇 취급 안 받기" 방법이다.

### 2.10 한계를 스스로 정한다 (`코드·문서 확인`)

- README는 Cloudflare Turnstile만 직접 다룬다고 적고, Akamai·DataDome·Kasada·Incapsula는 스폰서의 별도 API를 언급한다.
- 클릭 성공률, 문구 변화에 대한 내성, 최소 Chrome 버전(`MINIMUM_VERSION = 149`) 같은 값은 시간이 지나면 낡는다. 이 영역은 유지보수 비용이 크다는 것을 코드 상수가 보여 준다.
- 가져갈 점: 우회 코드에는 "어디까지 보장하는지"를 명시한다.

---

## 3. 코드 근거 (Source Evidence)

| 교훈 | 파일 | 식별자 |
|---|---|---|
| 2.1 비용 사다리 | `docs/spiders/proxy-blocking.md`, `scrapling/spiders/session.py` | "Customizing Retries" 예제, `SessionManager.add(lazy=)` |
| 2.2 일관성 | `engines/toolbelt/fingerprints.py`, `engines/_browsers/_base.py`, `engines/static.py` | `driven_browser_version`, `__generate_options__`, `_headers_job` |
| 2.4 챌린지 | `engines/_browsers/_stealth.py`, `_base.py`, `_validators.py` | `_cloudflare_solver`, `_detect_cloudflare`, `_challenge_cleared`, `StealthConfig.__post_init__` |
| 2.5 차단 훅 | `scrapling/spiders/spider.py`, `engine.py` | `BLOCKED_CODES`, `is_blocked`, `retry_blocked_request`, `_process_request` |
| 2.6 속도 | `scrapling/spiders/throttle.py` | `AutoThrottle.record`, `parse_retry_after` |
| 2.7 프록시 | `engines/toolbelt/proxy_rotation.py`, `_base.py`, `_page.py` | `ProxyRotator`, `is_proxy_error`, `_page_generator`, `PagePool` |
| 2.8 XHR | `docs/fetching/dynamic.md`, `_base.py` | `capture_xhr`, `_create_response_handler` |
| 2.9 캐시 | `scrapling/spiders/cache.py`, `engine.py` | `ResponseCacheManager`, 캐시 적중 분기 |

---

## 4. 검증 과정 및 실행 결과

- 실행 없음. 소스와 docs를 읽고 교차 확인했다.
- 정정: Q1에서 "권장 흐름을 문서에서 확인 못 했다"고 쓴 부분이 틀렸다. `proxy-blocking.md`에 있다. Q1을 고쳤다.
- 확인하지 못한 것: patchright 내부가 어떤 탐지 지점을 막는지, 캔버스 노이즈 플래그의 실제 동작, 각 기법이 실제 사이트에서 통하는지.

## 5. 기본값 주의 (`코드 확인`)

| 항목 | 기본값 | 근거 |
|---|---|---|
| `robots_txt_obey` | `False` (robots.txt를 따르지 않음) | `spiders/spider.py:76` |
| `autothrottle_enabled` | `False` | `spiders/spider.py:89` |
| `download_delay` | `0.0` | `spiders/spider.py:85` |
| `concurrent_requests_per_domain` | `0` (제한 없음) | `spiders/spider.py:84` |
| `stealthy_headers` | `True` | `static.py` |

즉 Spider를 그냥 돌리면 속도 제한도 robots 준수도 없다. 대상 사이트를 존중하는 설정은 사용자가 켜야 한다. 이 설정을 우리 쪽 도구에 가져올 때는 반대로 **기본을 보수적으로** 두는 편이 낫다 (판단, `추론`).

## 6. 남은 질문 및 추가 조사 사항

- [ ] `robots_txt_obey=True`일 때 실제 처리 코드 (`spiders/` 안 robots 처리 위치)
- [ ] `PagePool`과 영속 컨텍스트가 쿠키(예: Cloudflare 통과 쿠키) 재사용에 주는 효과 (`추론`, 검증 필요)
- [ ] `request._fp`(요청 지문) 계산 방식과 중복 제거
- [ ] patchright가 고치는 탐지 지점
