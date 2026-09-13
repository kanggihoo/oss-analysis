# Agent-Reach 채널별 동작 전략 분석

- 기준 checkout: `repos/Agent-Reach` @ `a7c56eb474f915308f02c39b9fa0c20f1abff222`
- DeepWiki baseline:
  - `artifacts/Agent-Reach/deepwiki/pages-md/3-channels.md`
  - `artifacts/Agent-Reach/deepwiki/pages-md/3.1-channel-architecture.md`
- 실제 검증 대상 소스:
  - `repos/Agent-Reach/agent_reach/channels/base.py`
  - `repos/Agent-Reach/agent_reach/channels/__init__.py`
  - `repos/Agent-Reach/agent_reach/channels/*.py`
  - `repos/Agent-Reach/agent_reach/doctor.py`

## 1. 한 줄 결론

Agent-Reach는 **브라우저 기반 웹 자동화 프레임워크가 아니라**, 플랫폼별로 서로 다른 백엔드(공개 API, CLI, MCP, 브라우저 세션 재사용, 헤드리스 브라우저, 쿠키 주입 등)를 **라우팅하는 Python 채널 시스템**이다.

즉, “모든 채널을 Chrome/headless로 통일”하는 구조가 아니라, **채널마다 가장 싼 경로부터 비싼 경로까지 서로 다른 전략을 쓴다**.

## 2. 공통 아키텍처

### 2.1 Channel 추상화
`agent_reach/channels/base.py` 기준으로 각 채널은 다음 책임을 가진다.

- `can_handle(url)` : 이 URL을 맡을 채널인지 판별
- `check(config)` : 현재 백엔드가 살아 있는지 실제로 점검
- `backends` : 우선순위가 있는 후보 백엔드 목록
- `active_backend` : 현재 실제로 사용 가능한 백엔드

중요한 점은 `backends`가 단순 목록이 아니라 **우선순위 있는 후보 리스트**라는 것이다. `ordered_backends()`는 config/env override(`<channel>_backend`, `<CHANNEL>_BACKEND`)를 반영해 순서를 바꾼다.

### 2.2 registry 라우팅
`agent_reach/channels/__init__.py`의 `ALL_CHANNELS`가 라우팅 순서를 결정한다. 실제 현재 checkout의 채널은 다음 13개다.

1. `GitHubChannel`
2. `TwitterChannel`
3. `YouTubeChannel`
4. `RedditChannel`
5. `BilibiliChannel`
6. `XiaoHongShuChannel`
7. `LinkedInChannel`
8. `XiaoyuzhouChannel`
9. `V2EXChannel`
10. `XueqiuChannel`
11. `RSSChannel`
12. `ExaSearchChannel`
13. `WebChannel`

`WebChannel`은 `can_handle()`가 항상 `True`라서 **fallback catch-all** 역할을 한다.

### 2.3 `doctor`가 보는 관점
`agent_reach/doctor.py`는 각 채널의 `check()` 결과와 `active_backend`를 모아 보고한다. 즉 이 프로젝트는 “명령이 존재하나?”가 아니라, **실제로 실행 가능한지**를 따진다.

## 3. DeepWiki vs 현재 소스의 차이

DeepWiki의 `3-channels.md`, `3.1-channel-architecture.md`는 방향성은 맞지만 **현재 checkout과는 꽤 다르다**.

### 3.1 구조 설명은 대체로 맞음
DeepWiki가 말하는 핵심 개념은 현재 코드와 일치한다.

- 채널 단위 책임 분리
- `can_handle()` 기반 URL 라우팅
- `check()` 기반 헬스체크
- registry 순회 후 첫 번째 매칭 선택
- tier로 설치 복잡도를 표현

### 3.2 하지만 채널 목록/티어 설명은 오래됨
현재 소스에는 DeepWiki가 적은 일부 채널이 없다.

- DeepWiki 쪽에 등장하지만 현재 소스에서 확인되지 않은 것들:
  - `WeiboChannel`
  - `DouyinChannel`
  - `WeChatChannel`
  - `InstagramChannel`
  - `BossZhipinChannel`

반대로 현재 소스에 있는데 DeepWiki 표가 놓치기 쉬운 것들:

- `WebChannel`
- `RSSChannel`
- `ExaSearchChannel`
- `XiaoyuzhouChannel`
- `V2EXChannel`
- `XueqiuChannel`

### 3.3 `Channel` 인터페이스 설명도 약간 과장됨
DeepWiki는 채널이 표준화된 `read()`/`search()`를 제공하는 것처럼 서술하지만, 현재 base class는 **`can_handle()`와 `check()`만 강제**한다.

실제 데이터 fetch 메서드는 채널마다 다르다.

- `WebChannel.read(url)`
- `V2EXChannel.get_hot_topics()`, `get_topic()`, `get_user()`, `search()`
- `XueqiuChannel.get_stock_quote()`, `search_stock()`, `get_hot_posts()`
- `YouTubeChannel.transcribe()`

즉, 이 시스템은 **완전 표준화된 CRUD API가 아니라, 채널별 도메인 메서드를 가진 라우터**다.

### 3.4 tier 예시도 현재 소스와 차이 있음
예를 들어 `ExaSearchChannel`은 현재 소스에서 `tier = 0`인데, DeepWiki 쪽 표는 더 높은 tier로 설명하는 흔적이 있다.

## 4. 채널별 동작 전략

아래 표는 “어떻게 데이터를 가져오는가”를 기준으로 정리한 것이다.

| 채널 | 현재 백엔드 / 전략 | 브라우저 의존성 | 실제 동작 방식 |
|---|---|---:|---|
| `web` | `Jina Reader` (`r.jina.ai`) | 아니오 | 모든 URL을 받아 Jina Reader로 텍스트/마크다운을 가져오는 범용 fallback. `urllib.request`로 직접 GET하고 `User-Agent`, `Accept: text/plain`만 넣는다. |
| `github` | `gh CLI` | 아니오 | `gh auth status`를 실제 실행해 상태를 확인. 인증되면 read/search/fork/issue/PR까지 가능한 공식 CLI 경로를 사용한다. |
| `youtube` | `yt-dlp` | 아니오 | `yt-dlp --version`으로 실행 가능 여부를 확인하고, JS runtime/ffmpeg 여부까지 추가로 검사한다. 자막/메타데이터 추출이 주 목적이고, 필요 시 `transcribe()`로 음성 전사를 붙인다. |
| `reddit` | `OpenCLI` → `rdt-cli` | 경우에 따라 예 | 데스크톱에서는 OpenCLI가 실제 Chrome 로그인 세션을 재사용한다. 서버/대체 경로는 `rdt-cli`이고, 둘 다 로그인 상태가 핵심이다. 익명 경로는 사실상 없음. |
| `bilibili` | `bili-cli` → `OpenCLI` → 검색 API | 경우에 따라 예 | 우선 `bili-cli`를 쓰고, 그 다음 OpenCLI가 브라우저 로그인 세션으로 보완한다. 마지막엔 검색 API fallback. 현재 코드에서 `yt-dlp`는 Bilibili용 백엔드가 아니다. |
| `xiaohongshu` | `OpenCLI` → `xiaohongshu-mcp` → `xhs-cli` | **예** | 데스크톱은 OpenCLI가 Chrome 로그인 세션을 재사용한다. 서버는 `xiaohongshu-mcp`의 **headless browser**가 담당한다. 기존 `xhs-cli`는 레거시 fallback이다. |
| `linkedin` | `linkedin-scraper-mcp` → `Jina Reader` | 보통 예 | `mcporter` 설정으로 MCP 서비스가 붙어 있으면 그쪽을 사용한다. 없으면 Jina Reader로 기본 읽기만 제공하는 형태다. |
| `xiaoyuzhou` | `groq-whisper` + `ffmpeg` | 아니오 | URL 수집보다는 팟캐스트 오디오 다운로드/전사 파이프라인이다. `ffmpeg`, 전사 스크립트, Groq/OpenAI 키가 핵심이다. |
| `v2ex` | Public JSON API | 아니오 | `https://www.v2ex.com/api/...`를 직접 호출한다. UA는 `agent-reach/1.0`이고, 검색은 API가 없어서 별도 처리를 안내한다. |
| `xueqiu` | Public API + cookie-aware HTTP | 부분적 예 | `~/.agent-reach/config.yaml` 또는 로컬 브라우저 쿠키를 먼저 시도하고, 실패하면 homepage fallback으로 `acw_tc`만 받는다. 이후 `User-Agent` + `Referer`를 붙여 JSON API를 친다. |
| `rss` | `feedparser` | 아니오 | RSS/Atom URL을 직접 파싱한다. 가장 단순한 정적 피드 경로다. |
| `exa_search` | `Exa via mcporter` | 아니오 | URL 채널이 아니라 search-only 채널이다. `mcporter config list`로 Exa MCP 연결 여부를 확인한다. |
| `twitter` | `twitter-cli` → `OpenCLI` → `bird` | 경우에 따라 예 | 쿠키 인증 기반이다. `twitter status`를 실제 실행해 상태를 본다. 1차는 `twitter-cli`, 2차는 OpenCLI, 3차는 legacy bird CLI다. |

## 5. “브라우저 기반인가?”에 대한 정확한 답

### 5.1 전체적으로는 아니다
대부분의 채널은 브라우저가 필요 없다.

- `web` = Jina Reader
- `github` = gh CLI
- `youtube` = yt-dlp
- `rss` = feedparser
- `v2ex` = public API
- `xiaoyuzhou` = ffmpeg + Whisper
- `exa_search` = MCP 기반 search

### 5.2 브라우저가 중요한 채널은 일부다
브라우저/헤드리스가 중요한 곳은 주로 아래다.

- `twitter` : 로그인 세션 재사용 또는 쿠키 인증
- `reddit` : 로그인 세션 재사용 / cookie import
- `bilibili` : OpenCLI fallback에서 브라우저 로그인 세션 활용
- `xiaohongshu` : **desktop Chrome(OpenCLI)** 또는 **headless browser(xiaohongshu-mcp)**
- `xueqiu` : 로컬 브라우저 쿠키를 가져오거나 쿠키 문자열을 저장해 재사용
- `linkedin` : MCP 백엔드가 실제로 브라우저 자동화를 내부적으로 쓸 가능성이 높고, 문서도 그 방향을 전제

### 5.3 “처음부터 headless Chrome 하나로 통일”은 왜 안 하냐
이 프로젝트는 굳이 그렇게 하지 않는다. 이유는 간단하다.

1. **많은 플랫폼은 headless가 필요 없다.**
   - API/CLI가 더 빠르고 안정적이다.

2. **브라우저는 무겁고 깨지기 쉽다.**
   - 로그인, 세션, 확장, 화면 환경, anti-bot 탐지 등 변수가 많다.

3. **채널마다 실패 원인이 다르다.**
   - 어떤 것은 API key 문제, 어떤 것은 cookie 문제, 어떤 것은 CLI 미설치 문제다.

4. **로컬 Chrome 세션을 재사용하는 게 더 싸고 안정적인 경우가 있다.**
   - 특히 `OpenCLI` 류는 “이미 사용자가 로그인해 둔 브라우저”를 그대로 쓰는 게 강점이다.

즉, Agent-Reach의 설계는 **브라우저 우선이 아니라, 채널별 최적 경로 우선**이다.

## 6. 채널별 관찰 포인트

### 6.1 `web`
- 가장 범용적인 fallback
- 사실상 “웹 문서 읽기” 전용
- 브라우저 자동화가 아니라 서버형 텍스트 변환 서비스 활용

### 6.2 `github`
- 가장 정석적인 공식 CLI 경로
- 브라우저나 scraping보다 `gh` API 인증 상태가 중요

### 6.3 `youtube`
- 다운로드/자막 추출은 `yt-dlp` 중심
- JS runtime이 없으면 경고를 띄우는 점이 중요
- 브라우저가 아니라 외부 CLI 생태계에 의존

### 6.4 `reddit`
- 익명 접근이 아니라 **login session 중심**
- desktop Chrome에서는 OpenCLI가, 서버에서는 `rdt-cli`가 대응

### 6.5 `bilibili`
- `yt-dlp`는 제거되고 `bili-cli`가 핵심
- OpenCLI는 자막 같은 보조 기능 보완용
- search API fallback이 있어 “기본 검색만 살리는” 전략도 가능

### 6.6 `xiaohongshu`
- Agent-Reach에서 가장 명확한 **브라우저/헤드리스 분기 채널**
- desktop = OpenCLI
- server = xiaohongshu-mcp(headless)
- legacy = xhs-cli

### 6.7 `linkedin`
- `mcporter` 기반 MCP 연동 채널
- 완전한 브라우저 자동화라기보다, 외부 MCP 서버를 붙이는 구조

### 6.8 `xueqiu`
- HTTP API 채널이지만, 실제로는 쿠키/세션 문제를 해결하는 로직이 핵심
- `homepage fallback`은 완전한 인증 경로가 아니라 anti-DDoS 토큰 보완용
- 즉, “헤더만 바꾸는 단순 우회”가 아니라 **쿠키 초기화 전략**이 포함됨

### 6.9 `v2ex`
- 매우 단순한 public API 채널
- 브라우저/세션/쿠키 없음
- 검색은 API 부재로 인해 제한됨

### 6.10 `rss`
- 가장 단순한 파서형 채널
- 네트워크나 브라우저 추상화가 거의 없음

### 6.11 `exa_search`
- URL 읽기가 아니라 search-only
- `mcporter`가 연결된 Exa MCP를 확인하는 구조

### 6.12 `twitter`
- cookie auth를 전제하는 채널
- OpenCLI가 있으면 브라우저 로그인 세션 재활용 가능
- `bird`는 레거시 fallback

### 6.13 `xiaoyuzhou`
- 웹 스크래핑보다 오디오 전사 파이프라인
- 브라우저가 아니라 media toolchain + LLM transcription

## 7. 실무적 평가

### 7.1 가장 안정적인 축
다음은 브라우저 없이도 상대적으로 안정적이다.

- `gh CLI`
- `yt-dlp`
- `feedparser`
- `v2ex public API`
- `Jina Reader`

### 7.2 가장 환경 의존적인 축
다음은 환경 의존성이 크다.

- `OpenCLI` 계열: 데스크톱 Chrome + 확장 + 로그인 세션
- `xiaohongshu-mcp`: headless browser + 서버 서비스
- `reddit` / `twitter`: cookie/session 상태
- `xueqiu`: cookie + referer + user-agent + API behavior

### 7.3 이 프로젝트의 진짜 가치
Agent-Reach의 가치는 “하나의 브라우저 자동화 엔진”이 아니라,
**플랫폼별로 다른 현실적인 접근 경로를 빠르게 골라주는 레이어**라는 데 있다.

즉,
- 브라우저가 가능한 곳은 브라우저를 쓰고
- CLI가 더 좋은 곳은 CLI를 쓰고
- public API가 있으면 API를 쓰고
- 마지막에만 headless/browser automation으로 내려간다.

## 8. 최종 결론

`Agent-Reach`는 **Chrome/Chromium 기반 프로젝트가 아니다**. 다만 일부 채널에서:

- 데스크톱 Chrome 세션 재사용(OpenCLI)
- headless browser(MCP 계열)
- 브라우저 쿠키 추출

이 사용될 뿐이다.

따라서 이 repo를 볼 때는 “브라우저 자동화 도구”로 분류하기보다,
**플랫폼별 데이터 추출 경로를 선택/체크/대체하는 채널 라우터**로 보는 게 정확하다.

## 9. 참고한 실제 소스 경로

- `repos/Agent-Reach/agent_reach/channels/base.py`
- `repos/Agent-Reach/agent_reach/channels/__init__.py`
- `repos/Agent-Reach/agent_reach/channels/web.py`
- `repos/Agent-Reach/agent_reach/channels/github.py`
- `repos/Agent-Reach/agent_reach/channels/youtube.py`
- `repos/Agent-Reach/agent_reach/channels/reddit.py`
- `repos/Agent-Reach/agent_reach/channels/bilibili.py`
- `repos/Agent-Reach/agent_reach/channels/xiaohongshu.py`
- `repos/Agent-Reach/agent_reach/channels/linkedin.py`
- `repos/Agent-Reach/agent_reach/channels/xiaoyuzhou.py`
- `repos/Agent-Reach/agent_reach/channels/v2ex.py`
- `repos/Agent-Reach/agent_reach/channels/xueqiu.py`
- `repos/Agent-Reach/agent_reach/channels/rss.py`
- `repos/Agent-Reach/agent_reach/channels/exa_search.py`
- `repos/Agent-Reach/agent_reach/doctor.py`
- `artifacts/Agent-Reach/deepwiki/pages-md/3-channels.md`
- `artifacts/Agent-Reach/deepwiki/pages-md/3.1-channel-architecture.md`
