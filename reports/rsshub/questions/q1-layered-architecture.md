# [Q] 계층 구조(Entrypoint → app-bootstrap → registry → routes → 데이터 수집)의 각 계층 역할과 분리 이유

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- **검증 수준**: 코드 확인

---

## 1. 질문 및 결론

- **질문**: RSSHub는 단순 스크립트가 아니라 Entrypoint → app-bootstrap(미들웨어) → registry → routes/<site> → 실제 데이터 수집(HTTP fetch 또는 headless 브라우저) 순의 계층 구조로 되어 있다. 각 계층이 정확히 무엇을 담당하며, 왜 이렇게 나눴는가?
- **핵심 결론**: 각 계층은 "무엇이 바뀌는 단위인가"를 기준으로 분리되어 있다 — **호스팅 런타임**(Node vs Cloudflare Workers), **모든 사이트에 공통인 정책**(캐시/보안/쿼리파라미터), **URL→플러그인 라우팅 메커니즘**, **사이트별 비즈니스 로직**(1,902개, 서로 독립적으로 추가/변경됨) 이 네 가지는 변경 빈도와 변경 주체가 완전히 다르기 때문에 각각 다른 계층으로 격리했다. "실제 데이터 수집(HTTP vs 브라우저)"은 별도 계층이 아니라, routes 계층 내부에서 사이트별로 고르는 전략일 뿐이다.

---

## 2. 동작 설명 및 관련 그림

- 관련 다이어그램: [structure.html](../diagrams/structure.html)

### 계층별 역할

**1) Entrypoint (`lib/index.ts` / `lib/worker.ts`) — "어디서 실행되는가"**
- 순수하게 프로세스 기동/호스팅 책임만 진다. `lib/index.ts`는 Node의 `@hono/node-server`로 HTTP 서버를 열고 `cluster` 모듈로 멀티프로세스를 띄운다. `lib/worker.ts`(`wrangler.toml`로 배포)는 같은 앱을 Cloudflare Workers 런타임에 올린다.
- 두 파일 모두 결국 같은 `app.fetch`(아래 2번 계층)를 호출할 뿐이다 — **런타임이 바뀌어도 그 위의 로직은 전혀 안 바뀌게** 하기 위한 껍데기다. 실제로 이 구조 덕분에 RSSHub는 Node 서버/Docker/Vercel/Cloudflare Workers에 동일 코드베이스로 배포 가능하다 (`package.json`의 `worker-build`, `vercel-build`, `container-build` 스크립트가 각각 다른 진입점을 빌드).

**2) app-bootstrap.tsx — "모든 요청에 공통으로 적용할 정책"**
- Hono 앱을 만들고 미들웨어 체인을 순서대로 건다: `logger → trace → honeybadger/sentry(에러 리포팅) → accessControl → debug → template → header → antiHotlink → parameter → cache`.
- 이 계층의 존재 이유는 **1,902개 사이트 라우트가 각자 따로 구현하면 안 되는, 그러나 모든 라우트에 똑같이 필요한 로직**을 한 곳에 모으는 것이다. 구체적 근거:
  - `lib/middleware/cache.ts`: 요청 path+format+limit로 캐시 키를 만들고(`xxhash`), 동일 요청이 동시에 들어오면 하나만 원본 사이트를 fetch하고 나머지는 그 결과를 기다리는 **요청 합류(request coalescing)** 를 구현한다 (`cacheModule.globalCache.claim(controlKey, ...)`). 이건 라우트 핸들러 하나하나가 알 필요도, 알아서도 안 되는 인프라 로직이다.
  - `lib/middleware/parameter.ts`: `?format=`, `?limit=`, AI 요약(`getAiCompletion`) 같은 **모든 라우트에 공통인 쿼리 파라미터 처리**를 여기서 한 번만 구현한다. 라우트 핸들러는 RSS item만 반환하면 되고, 이 변환은 신경 쓸 필요가 없다.
  - `errors/`(onError/notFound), `access-control`(내부 API 접근 제어), `anti-hotlink`(이미지 hotlink 방지) 도 마찬가지로 "사이트가 몇 개든 상관없이 항상 같은 규칙"이라 미들웨어로 분리됨.
- 즉 이 계층을 분리하지 않으면 캐싱/파라미터 처리 로직이 3,964개 라우트 파일에 중복 구현되어야 한다.

**3) registry.ts (+ registry-helpers.ts, registry-dev.ts) — "URL을 어떤 플러그인에 배정할 것인가"**
- 순수 라우팅/디스패치 메커니즘만 담당하고, 사이트별 로직은 전혀 모른다. `registerRssRoutes()`가 각 namespace(사이트 폴더)를 `app.basePath('/<namespace>')`로 마운트하고, `sortRoutes()`로 리터럴 경로가 파라미터 경로(`:id`)보다 먼저 매칭되도록 정렬한다.
- 흥미로운 지점: prod에서는 라우트 핸들러를 즉시 로드하지 않고 `routeData.module()`이라는 **지연 함수**를 등록해뒀다가, 실제로 그 URL이 호출된 시점에만 `await routeData.module()`로 해당 파일을 동적 import한다 (`lib/registry-helpers.ts`의 `registerRssRoutes`/`registerApiRoutes`). dev 모드에서는 `registry-dev.ts`가 파일시스템을 스캔해 비슷한 지연 로딩을 흉내낸다.
  - **왜?** 사이트가 1,902개나 되는데 요청 한 번에 그 모든 핸들러 코드를 메모리에 올릴 이유가 없다. 실제로 호출된 라우트의 코드만 그때그때 로드해서 콜드스타트/메모리 사용량을 줄인다 — Cloudflare Workers 배포에서 특히 중요한 이유다.

**4) routes/<site>/*.ts — "이 사이트에서 무엇을 어떻게 가져올지"**
- 사이트별 독립 플러그인. 표준 스키마(`path`, `name`, `maintainers`, `radar`, `features`, `handler`)를 따르되, `handler` 내부 구현은 완전히 자유다.
- **여기가 "실제 데이터 수집"이 실제로 결정되는 지점이다** — 별도 계층이 아니라 이 안에서 사이트마다 다르게 선택한다:
  - 대부분: `lib/utils/ofetch.ts`/`got.ts`로 일반 HTTP 요청 후 HTML/RSS/JSON 파싱 (예: `lib/routes/github/activity.ts`가 `ofetch`로 GitHub의 공식 Atom 피드를 가져와 파싱).
  - 일부(`features.requirePuppeteer: true`로 표시된 라우트, 예: `lib/routes/autotrader/index.ts`): 대상 사이트가 JS 렌더링이 필요하거나 봇 탐지가 강해서 일반 fetch로는 안 되는 경우, `lib/utils/playwright.ts`의 `getPlaywrightPage()`로 실제 headless Chromium(`patchright`, 안티디텍션 패치된 playwright 포크)을 띄워 브라우저처럼 접근한다.
  - `requirePuppeteer`는 디스패치 로직에서 소비되지 않는 순수 메타데이터(`lib/types.ts:340`)다 — 즉 registry나 middleware가 "이 라우트는 브라우저가 필요하니 다르게 처리"하는 분기는 없다. 브라우저를 쓸지 말지는 그 라우트 파일 작성자가 코드 안에서 직접 결정한다.

### 계층을 나눈 근본 이유 (요약)

| 계층 | 담당 | 바뀌는 이유 | 바뀌는 주체 |
|---|---|---|---|
| Entrypoint | 프로세스/런타임 호스팅 | 배포 대상(Node/Workers/Vercel)이 바뀔 때 | 인프라 담당 |
| app-bootstrap | 전체 공통 정책(캐시/보안/파라미터) | 정책이 바뀔 때(모든 사이트에 영향) | 코어 메인테이너 |
| registry | URL→플러그인 매칭, 로딩 전략 | 라우팅 규칙/성능 전략이 바뀔 때 | 코어 메인테이너 |
| routes/<site> | 사이트별 수집·파싱 로직(HTTP or 브라우저 선택 포함) | 대상 사이트가 바뀔 때(개별적, 매우 빈번) | 각 사이트 기여자(오픈소스 PR) |

핵심은 마지막 행이다: RSSHub는 **수백 명의 외부 기여자가 각자 담당 사이트 라우트만 건드리는 오픈소스 프로젝트**이므로, 기여자가 실수로 캐싱/보안/라우팅 같은 공통 인프라를 건드리지 못하게(그리고 그럴 필요가 없게) 계층으로 격리한 것이 가장 실용적인 이유로 보인다.

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| Entrypoint | `lib/index.ts` | 최상위 스크립트 | Node HTTP 서버 기동, cluster 지원 |
| Entrypoint(대체) | `lib/worker.ts`, `wrangler.toml` | — | Cloudflare Workers 배포 진입점 |
| app-bootstrap | `lib/app-bootstrap.tsx` | `app.use(...)` 체인 | 미들웨어 순서 정의 |
| 공통 정책(캐시) | `lib/middleware/cache.ts` | `middleware`, `cacheModule.globalCache.claim` | 캐시 키 생성, 요청 합류(coalescing) |
| 공통 정책(파라미터) | `lib/middleware/parameter.ts` | `middleware`, `getAiCompletion` | `?format`/`?limit`/AI 요약 등 공통 쿼리 처리 |
| 라우팅 | `lib/registry.ts` | `registerRssRoutes`, `registerApiRoutes` (import) | namespace 로드 및 앱 마운트 |
| 라우팅(디스패치) | `lib/registry-helpers.ts` | `registerRssRoutes()`, `sortRoutes()` | path 매칭 우선순위, `routeData.module()` 지연 로딩 |
| 라우팅(dev) | `lib/registry-dev.ts` | `createDevRegistry` | 파일시스템 스캔 기반 dev용 지연 로딩 |
| 라우트 스키마 | `lib/types.ts:325-345` | `Route['features']` | `requirePuppeteer` 등 메타데이터 정의(디스패치에 미소비) |
| 수집(HTTP) | `lib/routes/github/activity.ts` | `route.handler` | `ofetch`로 GitHub Atom 피드 fetch + parse |
| 수집(브라우저) | `lib/routes/autotrader/index.ts` | `getPlaywrightPage` (import) | `lib/utils/playwright.ts`의 headless Chromium 사용 |
| 브라우저 유틸 | `lib/utils/playwright.ts` | `getLaunchOptions`, `chromium`(patchright) | proxy 지원 포함 브라우저 런치 옵션 |

---

## 4. 검증 과정 및 실행 결과

- **수행한 작업**: 위 파일들을 직접 열람하여 각 계층의 실제 구현을 확인 (별도 실행/테스트는 하지 않음).
- **판단 근거**: `grep -rn "requirePuppeteer" lib/*.ts lib/middleware lib/api`로 해당 플래그가 `lib/types.ts` 타입 정의 외에는 어디서도 참조되지 않음을 확인 → "브라우저 수집"이 별도 디스패치 계층이 아니라 라우트 핸들러 내부 선택임을 뒷받침.

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] `cache.ts`의 요청 합류(coalescing)가 memory/redis/KV 백엔드별로 어떻게 다르게 동작하는지(`supportsAtomicClaims` 분기) 상세 확인
- [ ] `registry-dev.ts`(dev lazy loading)와 prod의 `assets/build/routes.js` 프리컴파일 방식이 실제로 어떻게 다른 산출물을 만드는지 빌드 스크립트(`scripts/workflow/build-routes.ts`) 추적
- [ ] `features.requirePuppeteer` 같은 메타데이터가 실제로 어디서 소비되는지(문서 사이트? `/api` radar 응답?) — `lib/api/route` 쪽 확인 필요
