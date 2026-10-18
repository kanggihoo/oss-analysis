---
sha: "7a684934907a8c7feaafe9ff1ccfd9d45cc26faf"
created: 2026-10-18
updated: 2026-10-18
---

# Scrapling Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/d4vinci/Scrapling`
- **기준 SHA**: `7a684934` (2026-10-11), 버전 0.4.15 (`pyproject.toml`)
- **작업트리 상태**: Clean
- **분석 목적**: 학습. 특히 (1) 정적/동적 사이트 판단 방식, (2) 봇 차단 우회 전략
- **언어/규모**: Python ≥3.10, `scrapling/` 안 `.py` 약 1.6만 줄(광고 도메인 목록 3,537줄 포함), BSD 라이선스

---

## 2. 프로젝트 개요

HTML 파싱 + 페이지 가져오기(fetch) + 크롤링(spider)을 한 라이브러리로 묶은 Python 웹 스크래핑 프레임워크다. (출처: README "adaptive Web Scraping framework")

### 주요 기능

| 기능 | 설명 (출처: README·docs) | 코드 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| 3종 fetcher | `Fetcher`(HTTP만), `DynamicFetcher`(브라우저), `StealthyFetcher`(스텔스 브라우저). **사용자가 고른다** | `scrapling/fetchers/__init__.py` `_LAZY_IMPORTS`, `docs/fetching/choosing.md` 비교표 | 코드 확인 |
| 정적/동적 자동 판단 | 사용자가 궁금해한 기능 | **없음.** 판단 로직을 찾지 못함 (Q1 2절) | 코드 확인(검색 결과 없음) |
| HTTP 위장 | TLS 지문 모방 + 실제 브라우저 헤더 + Google referer | `engines/static.py` `impersonate`(기본 `"chrome"`), `_headers_job`, `engines/toolbelt/fingerprints.py` `generate_headers` | 코드 확인 |
| 스텔스 브라우저 | patchright 기반 Chromium, 자동화 흔적 제거 플래그, 캔버스·WebRTC 처리 | `engines/_browsers/_stealth.py`, `_base.py` `StealthySessionMixin`, `engines/constants.py` `STEALTH_ARGS` | 코드 확인 (실제 탐지 회피 효과는 미실행) |
| Cloudflare Turnstile/Interstitial 해결 | `solve_cloudflare=True` | `_stealth.py` `_cloudflare_solver`, `_base.py` `_detect_cloudflare`·`_challenge_cleared` | 코드 확인 (실제 사이트 미실행) |
| 프록시 로테이션·재시도 | 요청마다 프록시 교체, 프록시 오류 시 재시도 | `engines/toolbelt/proxy_rotation.py` `ProxyRotator`·`is_proxy_error`, `_stealth.py` `fetch` 재시도 루프 | 코드 확인 |
| Spider(크롤러) | 스크래피풍 비동기 크롤, 차단 응답 재시도, 자동 속도 조절 | `scrapling/spiders/engine.py`, `spider.py` `is_blocked`·`BLOCKED_CODES`, `throttle.py` `AutoThrottle` | 코드 확인 |
| 적응형 파서 | 사이트 구조가 바뀌어도 요소를 다시 찾음 (`adaptive=True`) | `scrapling/parser.py` (1,398줄), `core/storage.py` | 추론 (미열람) |
| CLI·MCP·AI 연동 | 터미널 도구, MCP 서버 | `scrapling/cli.py`, `core/ai.py`, `core/shell.py` | 추론 (파일 존재만) |

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

미작성 (사용자 요청으로 건너뜀).

## 4. 질문과 조사 기록 (Questions)

- [Q1: 정적/동적 판단과 봇 차단 우회 전략](./questions/q1-static-dynamic-and-bot-evasion.md) - *자동 판단은 없고 사용자가 fetcher를 고른다. 우회는 HTTP 위장 → 스텔스 브라우저 → Turnstile 클릭 해결의 3단계.*
- [Q2: 봇 차단 대응에서 배울 점](./questions/q2-bot-evasion-lessons.md) - *비용 사다리, 층 간 일관성, 챌린지 분류·상한, 차단 판정 훅, AutoThrottle, 프록시·컨텍스트, XHR 직접 수집, 응답 캐시. 기본값은 robots 미준수·속도 제한 없음.*

## 5. 다음 작업 및 연계 링크

- **기능 스펙**: 없음
