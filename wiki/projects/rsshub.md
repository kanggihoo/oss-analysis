---
title: RSSHub
created: 2026-09-14
updated: 2026-09-24
type: project
tags: [open-source, project, architecture, developer-tools, pattern]
sources: [repos/rsshub/package.json, repos/rsshub/lib/index.ts, repos/rsshub/lib/app-bootstrap.tsx, repos/rsshub/lib/app.worker.tsx, repos/rsshub/lib/registry.ts, repos/rsshub/lib/registry-helpers.ts, repos/rsshub/lib/middleware/cache.ts, repos/rsshub/lib/middleware/parameter.ts, repos/rsshub/lib/utils/ofetch.ts, repos/rsshub/lib/errors/index.tsx, repos/rsshub/lib/types.ts, repos/rsshub/lib/routes/github/activity.ts, repos/rsshub/lib/routes/github/trending.tsx, repos/rsshub/lib/routes/hackernews/index.ts, repos/rsshub/lib/routes/yna/index.ts, repos/rsshub/lib/utils/playwright.ts, repos/rsshub/lib/api/namespace/one.ts, repos/rsshub/wrangler.toml, repos/rsshub/AGENTS.md, reports/rsshub/overview.md, reports/rsshub/routes-catalog-overview.md, reports/rsshub/questions/q4-vps-info-typescript-redesign.md]
confidence: high
---

# RSSHub

RSSHub는 RSS 피드가 없는 웹사이트를 RSS/Atom/JSON 피드로 변환해주는 오픈소스 서버다. 이 페이지는 로컬 checkout `repos/rsshub/`(commit `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`)의 source로 검증한 요약이며, 상세 근거는 [reports/rsshub/overview.md](../../reports/rsshub/overview.md)에 있다. 다이어그램은 복제하지 않고 링크한다: [structure.html](../../reports/rsshub/diagrams/structure.html), [url-to-plugin-flow.html](../../reports/rsshub/diagrams/url-to-plugin-flow.html).

## 한 줄 정의

**"피드를 만드는" 엔진 전체가 오픈소스인 레포다** — 크롤링·파싱·서빙이 한 레포에 다 있고 셀프호스팅이 완전히 가능하다. [[folo]]와 정확히 상보 관계.

> 이 페이지의 결론은 `repos/` 로컬 source 검증에 기반한다 ([[evidence-backed-analysis]]). reports/wiki 역할 분담은 [[workspace-boundaries]]를 따른다.

## Verification snapshot

- Repository: `https://github.com/diygod/rsshub`
- Local checkout: `repos/rsshub/`
- Verified commit: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- License: AGPL-3.0

## 계층 구조와 분리 이유

각 계층은 **"무엇이 바뀌는 단위인가"**를 기준으로 나뉘어 있다. 상세 근거는 [q1 문서](../../reports/rsshub/questions/q1-layered-architecture.md).

| 계층 | 담당 | 바뀌는 이유 / 주체 |
|---|---|---|
| Entrypoint (`lib/index.ts` / `lib/worker.ts`) | 프로세스·런타임 호스팅만 | 배포 대상 변경 / 인프라 담당 |
| `app-bootstrap.tsx` | 전 요청 공통 정책(캐시·보안·파라미터) | 정책 변경 / 코어 메인테이너 |
| `registry.ts` | URL → 플러그인 매칭, 로딩 전략 | 라우팅·성능 전략 / 코어 메인테이너 |
| `routes/<site>/*.ts` | 사이트별 수집·파싱 | 대상 사이트 변경 / **외부 기여자(매우 빈번)** |

핵심은 마지막 행이다 — 수백 명의 외부 기여자가 자기 사이트 라우트만 건드리는 구조라, 기여자가 캐싱·보안·라우팅 같은 공통 인프라를 **건드릴 필요도 없고 건드릴 수도 없게** 격리한 것이 실질적 이유로 보인다(추론).

## 라우트 플러그인 모델

- URL 구조는 `/<namespace>/<route-path>` (예: `/github/activity/DIYgod` = namespace `github` + `/activity/:user`)
- 각 라우트 파일이 **자기 자신을 선언**한다: `export const route: Route = { path, name, maintainers, radar, features, handler }`
- `registry.ts`는 사이트별 지식을 전혀 갖지 않고, `app.basePath('/<namespace>')`로 마운트한 뒤 `sortRoutes()`로 리터럴 경로를 파라미터 경로보다 먼저 매칭시킨다
- prod에서는 핸들러를 즉시 로드하지 않고 `routeData.module()`로 **호출 시점 지연 import**한다 — 1,902개 사이트 코드를 매번 메모리에 올리지 않기 위함(Cloudflare Workers 콜드스타트에 특히 중요)

## 공통 미들웨어에서만 하는 일

라우트가 개별 구현하면 안 되는 것들이 `app-bootstrap.tsx` 체인에 모여 있다:

- `middleware/cache.ts` — path+format+limit로 캐시 키 생성(xxhash), **동일 요청 동시 유입 시 하나만 원본을 fetch하는 요청 합류(request coalescing)**
- `middleware/parameter.ts` — `?format`·`?limit`·AI 요약 등 **모든 라우트 공통 쿼리 파라미터** 처리. 여기서 **0건 판정**도 한다: `item`이 비어 있고 라우트가 `allowEmpty`를 돌려주지 않으면 예외를 던진다(`:71`). 이어서 `pubDate` 내림차순으로 정렬한다
- `utils/ofetch.ts` — 라우트가 쓰는 공통 HTTP 클라이언트(`ofetch.create`). 400·408·409·425·429·5xx를 재시도하고, **`timeout`은 주석 처리돼 있다**
- `errors/`, `access-control`, `anti-hotlink` 등도 동일 논리로 분리. 오류는 타입으로 나뉜다(`RejectError`→403, `NotFoundError`→404, 나머지 503)

## 수집 방식: HTTP vs 브라우저

"브라우저로 가져오는가"는 **별도 계층이 아니라 라우트 핸들러 내부의 선택**이다. `features.requirePuppeteer`는 디스패치에 소비되지 않는 순수 메타데이터(`lib/types.ts`)다.

정적 분석 카탈로그 기준([routes-catalog-overview.md](../../reports/rsshub/routes-catalog-overview.md)):

- 사이트 1,906곳 / 라우트 3,462개
- 브라우저(headless, playwright/patchright) 사용 라우트 **104개(3.0%)** — 나머지는 `ofetch`/`got` 기반 일반 HTTP
- 그중 **로그인·쿠키 등 인증까지 필요한 건 7개뿐**
- 언어 분포: 중국어권 58.2%, 영어 31.0% (`namespace.ts`의 `lang` 필드 전수 집계)
- 브라우저가 필요한 이유는 "IT 분야라서"가 아니라 **그 사이트의 스크래핑 방어 수준**이다 — 브라우저 라우트 다수가 중국 대학 홈페이지·뉴스/SNS에 몰려 있다

## 문서화 방식

사이트별 README를 **의도적으로 금지**한다(레포 자체 `AGENTS.md` 규칙 #7). 문서는 코드 안의 구조화된 필드(`namespace.ts`의 name/url/description, route의 description/parameters/radar)로만 존재하고, `GET /api/namespace/{namespace}`가 이를 JSON으로 노출한다(`lib/api/namespace/one.ts`). 외부 문서 사이트와 RSSHub Radar 확장이 이를 소비해 문서를 동적으로 생성하는 구조로 보인다(추론, docs 레포 미확인).

## 여기서 가져올 만한 것 (재사용 가치)

1. **플러그인 자기선언 패턴** — 코어를 수정하지 않고 파일 하나 추가로 기능이 늘어나는 구조. 기여자 수가 많은 프로젝트의 정석.
2. **요청 합류(request coalescing)** — 같은 피드를 동시에 요청해도 원본은 한 번만 때린다. 외부 API/사이트를 감싸는 모든 서비스에 그대로 쓸 만하다.
3. **공통 쿼리 파라미터를 미들웨어로** — `?limit`·`?format` 같은 건 핸들러가 아니라 파이프라인에서 한 번만 구현.
4. **지연 import 기반 라우트 로딩** — 수천 개 핸들러가 있어도 콜드스타트/메모리를 지킨다.
5. **코드가 곧 문서** — 메타데이터 필드 → API로 노출 → 문서 사이트가 소비. 문서 표류(drift)를 구조적으로 막는다.

## 소비하는 쪽에서 쓸 때

**RSSHub에는 영속 계층이 없다** (코드 확인): `package.json`에 postgres/sqlite/prisma/drizzle/mongo 의존성이 0개이고, 상태는 `lib/utils/cache/`(memory·redis·kv·http)의 TTL 캐시가 전부다 — `routeExpire` 300초, `contentExpire` 3600초(`lib/config.ts:795-796`). 즉 **요청 시점 변환기**이지 아카이브가 아니다. 피드에서 밀려난 항목은 영구 소실된다.

따라서 수집·저장형 프로젝트와 겹치는 구간은 **"사이트 → 정규화된 item 리스트" 한 단계뿐**이고, 그 한 단계를 가져오는 방법은 둘이다. 판단 근거는 [q3 문서](../../reports/rsshub/questions/q3-vps-info-adoption.md).

| 방식 | provider 추가 비용 | 사이트가 바뀌면 | 손익 분기 |
|---|---|---|---|
| `diygod/rsshub` 컨테이너 + HTTP 소비 | 피드 URL 한 줄 | 업스트림이 고쳐줌 | provider 10개 이상 |
| **엔드포인트 카탈로그로만 사용** — route 파일에서 호출 URL만 베끼고 직접 구현 | 40~60줄 | 직접 고쳐야 함 | provider 1~5개 |

후자가 실용적인 이유: provider 추가의 실제 비용은 코드가 아니라 **"이 사이트를 뭘 호출해야 목록이 나오는가"**인데, RSSHub가 그걸 1,906개 사이트분 대신 해뒀다. 예: daily.dev → `POST api.daily.dev/graphql`의 `anonymousFeed` 익명 쿼리, npm → `registry.npmjs.org`, Docker Hub → `hub.docker.com/v2/repositories`, dev.to 기간별 top → `dev.to/search/feed_content`.

그 외 소비 시 알아둘 것:

- **TypeScript 소비자는 라이브러리를 그대로 쓰되 라우트 코드는 복사하지 않는다.** `ofetch`, `rss-parser`, `cheerio`는 MIT지만 RSSHub 라우트 코드는 AGPL-3.0이다. 베낄 것은 엔드포인트와 파라미터뿐이다.
- **공통 정책을 코어에 모으는 구조는 가져올 만하지만, 설정은 베끼지 않는다.** 다시 보내도 결과가 같은 4xx(400·409)까지 재시도하고 타임아웃은 꺼져 있다. 스케줄러 기반 수집기라면 타임아웃을 켜고 재시도를 408/425/429/5xx로 좁힌다.
- **디렉터리 스캔 자동 등록은 라우트 수천 개를 위한 장치다.** 플러그인이 10개 안팎이면 명시적 import 목록이 더 짧고, 플러그인 파라미터를 타입으로 검사할 수 있다. vps-info 적용 사례는 [Q4](../../reports/rsshub/questions/q4-vps-info-typescript-redesign.md).

- **`DataItem`을 공통 포맷으로 채택할 이유는 없다.** 절반이 피드 렌더링 전용 필드(`enclosure_*`, `itunes_*`, `media`, `banner`)이고, 저장·질의에 필요한 dedup 키·최초/최종 관측 시각·수집 실행 이력에 대응하는 개념이 아예 없다.
- **공식 RSS가 있는 대상은 RSSHub를 거치지 마라.** 일부 라우트는 공식 피드를 그대로 프록시한다 — `lib/routes/theverge/`는 `theverge.com/rss/index.xml`을, `lib/routes/openai/`는 `openai.com/news/rss.xml`을 그대로 쓴다.
- **공식 API가 있는 대상은 RSSHub가 하위 호환일 수 있다.** `/hackernews/*`는 Firebase 공식 API가 아니라 news.ycombinator.com HTML 스크래핑이고, 점수/댓글이 문자열이며 원문 URL이 description HTML 안에 묻힌다(`lib/routes/hackernews/index.ts`).
- **포맷별로 필드가 소리 없이 사라진다** (컨테이너 방식일 때): `upvotes`/`downvotes`/`comments`는 **Atom 출력에만** `rsshub:` 확장 요소로 실린다(`lib/views/atom.tsx:40-42`). RSS 2.0과 JSON Feed(`lib/views/json.ts`)에는 매핑이 없다. feedparser는 이를 `rsshub_upvotes`/`rsshub_comments` 문자열로 노출한다(실행 확인). `rank`는 어떤 포맷으로도 오지 않는다.
- **점수·댓글을 실제로 싣는 라우트는 소수다** (`upvotes:` 전수 grep): `daily`(daily.dev), `hackernews`, `huggingface`, `bsky`, `lemmy`, `metacritic`, `mixcloud`, `unraid`, `voronoiapp`, `zodgame`. 개발자향 애그리게이터로 남는 실질 후보는 **daily.dev**다.
- 셀프호스팅 시 `redis`/`browserless`는 기본적으로 불필요하다: 캐시 기본값이 `memory`, 브라우저 필요 라우트는 3.0%뿐. `diygod/rsshub`는 chromium 미포함 태그다.

## 실용 메모

- 셀프호스팅: Node/Docker/Vercel/Cloudflare Workers 모두 지원(`wrangler.toml`, `tsdown-*.config.ts`)
- 개발자향 트렌드 라우트 예: `/hackernews/:section?`, `/github/trending/:since/:language`(**`GITHUB_ACCESS_TOKEN` 필요**), `/dev.to/top/:period`, `/producthunt/today`, `/v2ex/topics/hot`, `/juejin/aicoding`, `/hackerone/hacktivity`, `/npm/package/:name`
- GitHub 트렌딩은 공식 API가 없어 **트렌딩 페이지 HTML 스크래핑 + GraphQL API로 메타데이터 보강**하는 하이브리드다(그래서 토큰이 필수)
- Reddit/Lobsters 라우트는 존재하지 않는다

## 관련 페이지

- [[folo]] — 피드를 *읽는* 쪽 클라이언트. 백엔드가 비공개라는 점에서 RSSHub와 대비된다.
