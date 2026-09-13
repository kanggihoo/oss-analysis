# Agent-Reach 분석 메모

- repo checkout: `repos/Agent-Reach` @ `a7c56eb474f915308f02c39b9fa0c20f1abff222`
- 기준 자료: `artifacts/Agent-Reach/deepwiki/pages-md/1-overview.md`, `2-cli-reference.md`, `3-channels.md`

## 결론
Agent-Reach는 **Chrome/Chromium 브라우저 기반 프로젝트가 아니라**, 여러 외부 도구/백엔드를 **라우팅하는 Python CLI/설치기**에 가깝다.

다만 일부 채널은 브라우저 세션이나 브라우저 쿠키를 활용한다.

## 근거
- `pyproject.toml`의 기본 의존성은 `requests`, `feedparser`, `yt-dlp`, `rich` 등이며, `playwright`는 **optional extra**(`browser`)로만 선언돼 있다.
- `agent_reach/core.py` 주석과 문서 문자열은 이 프로젝트를 “installer, doctor, and configuration tool”로 설명하며, 읽기/검색은 **upstream tool을 직접 호출**한다고 적고 있다.
- `agent_reach/channels/__init__.py`는 `web`, `github`, `twitter`, `youtube`, `reddit`, `bilibili`, `xiaohongshu`, `linkedin`, `rss`, `exa_search`, `xueqiu` 등 **채널별 백엔드**를 등록한다.
- `agent_reach/backends/opencli.py`는 예외적으로 **실제 데스크톱 Chrome 세션**을 쓰는 OpenCLI를 다루며, `desktop-only (no headless)`라고 명시한다.
- `agent_reach/channels/xiaohongshu.py`는 OpenCLI → `xiaohongshu-mcp` → `xhs-cli` 순으로 fallback 하며, 주석에서 `xiaohongshu-mcp (self-contained headless browser)`를 명시한다.
- `agent_reach/channels/xueqiu.py`와 `cookie_extract.py`는 Chrome/Firefox 등 로컬 브라우저 쿠키를 추출하거나 재사용하는 경로를 제공한다.

## 해석
- 이 프로젝트의 중심은 **브라우저 자동화**가 아니라 **“플랫폼별 최적 백엔드 선택”**이다.
- 그래서 대부분의 채널은 Chrome과 무관하게 동작한다: `Jina Reader`, `yt-dlp`, `gh CLI`, `feedparser`, `Exa via mcporter` 등.
- 브라우저가 중요한 곳은 주로:
  1. **OpenCLI**: 사용자 로그인 세션을 재사용하는 데스크톱 Chrome 기반
  2. **xiaohongshu-mcp / linkedin-scraper-mcp**: 서버 측에서 headless browser 사용
  3. **cookie_extract / xueqiu**: 로컬 브라우저 쿠키 재사용

## 한 줄 평가
Agent-Reach는 “Chrome으로 웹을 읽는 툴”이라기보다, **읽기 가능한 최적의 도구를 골라 쓰게 해주는 레이어**다. 브라우저는 일부 채널의 로그인/쿠키/자동화 옵션일 뿐, 전체 아키텍처의 전부는 아니다.
