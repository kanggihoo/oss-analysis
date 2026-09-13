# RSSHub 지원 사이트/라우트 카탈로그 (개요)

- **상위 개요**: [overview.md](./overview.md)
- **분석 Commit SHA**: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- **검증 수준**: 코드 확인(정적 추출, 실행/빌드 없이 소스만 파싱) — regex 기반 best-effort 추출이라 일부 라우트는 누락/오분류될 수 있음(아래 한계 참고)

---

## 어떻게 만들었나

`npm install` + RSSHub 자체 빌드(`build:routes`)를 돌리면 정확한 라우트 레지스트리(`assets/build/routes.json`)를 얻을 수 있지만, 의존성 설치(Chromium 등 대용량 바이너리 포함)와 4천여 개 파일을 실제로 import/실행해야 해서 무겁고 부작용이 크다. 대신 **`lib/routes/**/*.ts`를 실행 없이 정적으로 파싱**하는 스크립트로 각 라우트 파일에서 `path`, `name`, `categories`, `features.requirePuppeteer`, `features.requireConfig`, `features.antiCrawler`를 정규식으로 뽑아 카탈로그를 만들었다.

- 스캔 대상: `namespace.ts`가 있는 디렉터리 1,980개(=사이트), 그 안에서 `export const route`/`apiRoute`를 선언한 파일
- 추출 성공: **3,462개 라우트** (파일 수 기준 약 4,000개 중 나머지는 `path`가 동적으로 조립되는 등 regex로 못 뽑은 케이스 — 아래 "한계" 참고)

## 산출물

| 파일 | 내용 |
|---|---|
| [routes-catalog.csv](./routes-catalog.csv) | 라우트 단위 3,462행 — `namespace, namespace_name, namespace_url, namespace_lang, route_path, route_name, category, uses_browser, requirePuppeteer_flag, anti_crawler, require_config_vars, file` |
| [routes-catalog-by-site.csv](./routes-catalog-by-site.csv) | 사이트(namespace) 단위 1,906행 — `lang`(사이트 언어), 라우트 개수, 브라우저/설정 필요 여부 롤업 |

`route_path` 컬럼이 곧 **실제 호출 URL**이다 (예: `/github/activity/DIYgod`처럼 `:param` 부분만 채우면 됨). `file` 컬럼으로 해당 라우트의 실제 구현 코드(`repos/rsshub/<file>`)를 바로 열어볼 수 있다.

---

## 집계 요약

| 항목 | 값 |
|---|---|
| 사이트(namespace) 수 | 1,906 |
| 라우트(URL 패턴) 수 | 3,462 |
| **브라우저(headless) 로 수집하는 라우트** (`features.requirePuppeteer: true`) | **104개 (3.0%)** |
| 그 중 route 파일에서 playwright를 직접 import하는 것으로 확인된 라우트 | 76개 (나머지는 같은 폴더의 `utils.ts` 등 헬퍼를 통해 간접 사용 — 예: `javdb/index.ts`) |
| `requireConfig`로 별도 환경변수/인증정보가 필요한 라우트 | 156개 (4.5%) |
| `antiCrawler: true`로 표시된 라우트(봇 탐지 있음, 브라우저 필요와는 별개) | 282개 |
| **브라우저 + 별도 인증정보 둘 다 필요한 라우트** | **7개뿐** |

**결론**: 압도적 다수(97%)는 일반 HTTP fetch(`ofetch`/`got`)로 대상 사이트의 API나 페이지·RSS를 가져와 파싱하는 방식이고, 로그인/토큰 없이 바로 호출 가능하다. 브라우저 자동화가 필요한 라우트는 전체의 3%뿐이며, 그중에서도 **로그인/쿠키 같은 별도 인증이 필요한 경우는 7개**로 매우 드물다:

| route_path | 필요한 환경변수 |
|---|---|
| `/fanbox/:creator` | `FANBOX_SESSION_ID` |
| `/iwara/subscriptions` | `IWARA_USERNAME`, `IWARA_PASSWORD` |
| `/weibo/keyword/:keyword/...` | `WEIBO_COOKIES` |
| `/weibo/super_index/:id/...` | `WEIBO_COOKIES` |
| `/weibo/user/:uid/...` | `WEIBO_COOKIES` |
| `/xiaohongshu/user/:user_id/...` | `XIAOHONGSHU_COOKIE` |
| `/xsijishe/rank/:type` | `XSIJISHE_COOKIE`, `XSIJISHE_USER_AGENT` |

즉 "이 라우트만 가져다 쓴다"는 관점에서: 대부분의 라우트는 **환경변수 없이 바로 배포/호출**해도 되고, 위 7개(+`requireConfig`가 있는 나머지 149개 — 이건 브라우저와 무관하게 API 키가 필요한 일반 fetch 라우트들, 예: 특정 사이트의 앱 토큰)만 별도 자격증명 세팅이 필요하다.

## 카테고리 분포 (상위)

| 카테고리 | 라우트 수 |
|---|---|
| new-media (뉴미디어/포털) | 504 |
| university (대학 공지) | 448 |
| programming | 218 |
| social-media | 214 |
| traditional-media | 206 |
| multimedia | 189 |
| finance | 156 |
| government | 155 |
| game | 142 |
| blog | 128 |
| program-update | 128 |

전체 카테고리 목록/사이트별 세부는 `routes-catalog-by-site.csv`의 `categories` 컬럼 참고.

---

## 사이트 언어/지역 분포 — "대부분 중국 사이트인가?"

각 `namespace.ts`는 `lang` 필드로 대상 사이트의 언어를 스스로 선언한다(추측이 아니라 코드 자체의 선언). 1,906개 사이트 전수 집계:

| 언어 | 사이트 수 | 비중 |
|---|---|---|
| `zh-CN` (중국 대륙 간체) | 1,004 | 52.7% |
| `en` (영어) | 591 | 31.0% |
| `zh-TW` (대만 번체) | 83 | 4.4% |
| `ja` (일본어) | 65 | 3.4% |
| `zh-HK` (홍콩 번체) | 21 | 1.1% |
| (미표기) | 99 | 5.2% |
| 기타(ko/de/ru/es/fr 등) | 43 | 2.3% |
| **중국어권 합계(zh-CN+zh-TW+zh-HK)** | **1,109** | **58.2%** |

**결론: 맞다, 절반 이상(58%)이 중국어권 사이트다.** 카테고리로 보면 이게 더 뚜렷한데, `university`(448개 라우트) 중 93.5%, `government`(155개) 중 85%가 중국 대학/정부 기관 공지사항 페이지였다(정적 확인). RSSHub 자체가 중국인 개발자(DIYgod)가 만들고 중국 인디 개발자 커뮤니티에서 특히 널리 쓰인 오픈소스라, "학교 공지·정부 공고·중국 SNS(微博/知乎/哔哩哔哩/小红书 등)를 RSS로 받아보고 싶다"는 롱테일 수요가 라우트 절대다수를 차지한 것으로 보인다(추론 — RSSHub 프로젝트 히스토리/커뮤니티에 대한 것이라 이 레포 코드만으로 검증 불가).

다만 영어권(31%)과 일본어(3.4%) 등도 결코 적지 않다 — GitHub, Twitter/X, Reddit류의 국제 서비스나 프로그래밍 블로그, 게임(Nintendo 등) 라우트는 전부 영어권으로 분류된다.

## 각 사이트가 뭘 의미하는지 — 읽는 법 + 상위 30개 예시

카탈로그에서 "이 사이트가 뭘 하는 곳인지"는 3개 컬럼 조합으로 파악한다:
- `namespace_name`/`url`: 사이트 자체가 무엇인지 (예: `weibo` → 微博/weibo.com = 중국판 트위터급 SNS)
- `category`: 대분류(social-media, university, government, finance, game, ...)
- `route_name`(라우트 단위 CSV): 그 사이트에서 **구체적으로 무엇을 가져오는지** (예: weibo면 `유저 타임라인`, `키워드 검색`, `슈퍼톡 게시판` 등 라우트별로 나뉨)
- 일부 사이트는 `namespace.ts`에 `description`까지 있지만(예: weibo는 쿠키 필요 여부·출력 포맷 옵션을 표 형태로 설명하는 긴 마크다운), 이번 카탈로그에는 이 필드를 넣지 않았다 — 대부분 사이트는 비어 있고(단순히 name/url/lang만 선언), 있는 경우도 대부분 원문(중국어)이라 그대로 노출해도 큰 도움이 안 돼서 뺐다. 특정 사이트가 궁금하면 `file` 컬럼으로 `repos/rsshub/lib/routes/<site>/namespace.ts`를 직접 열어보는 게 가장 정확하다.

라우트 개수 기준 상위 30개 사이트(무엇을 하는 곳인지 간단 설명 추가):

| 사이트 | 카테고리 | 라우트 수 | 뭘 가져오는 곳인가 |
|---|---|---|---|
| bilibili (哔哩哔哩) | social-media | 43 | 중국 최대 동영상/애니 커뮤니티 — 업로더 영상, 랭킹, 다이나믹(피드) 등 |
| ecnu (화동사범대학) | university | 30 | 중국 대학 공지사항 |
| github | programming | 23 | 레포/이슈/PR/릴리스/유저 활동 등 |
| javlibrary | multimedia | 17 | 성인 콘텐츠 DB(리뷰/신작) |
| zzu (정저우대학) | university | 16 | 중국 대학 공지사항 |
| furaffinity | social-media | 13 | 퍼리(furry) 아트 커뮤니티 신작 |
| nju (난징대학) | university | 13 | 중국 대학 입학/공지 |
| sspai (少数派) | new-media | 13 | 중국 IT/생산성 테크 매체 |
| zhihu (知乎) | social-media | 13 | 중국판 Q&A 커뮤니티(쿼라 유사) |
| gcores (机核网) | game | 11 | 중국 게임 매체/팟캐스트 |
| juejin (掘金) | programming | 11 | 중국 개발자 커뮤니티(기술 블로그) |
| tingshuitz (停水通知) | forecast | 11 | 중국 다롄시 단수(斷水) 공고 |
| xueqiu (雪球) | finance | 11 | 중국 투자/주식 커뮤니티 |
| publico | traditional-media | 10 | 스페인 뉴스 매체 |
| yicai (第一财经) | traditional-media | 10 | 중국 경제 뉴스 매체 |
| gov/cmse | (government) | 9 | 중국 유인우주공정(정부기관) 소식 |
| huxiu (虎嗅) | new-media | 9 | 중국 IT/비즈니스 매체 |
| twitter (X) | social-media | 9 | X(구 트위터) 유저 타임라인 등 |
| uestc (전자과기대학) | university | 9 | 중국 대학 공지 |
| wechat | new-media | 9 | 위챗 미니프로그램 관련 정보 |
| bupt (베이징우전대학) | university | 8 | 중국 대학 공지 |
| javdb | multimedia | 8 | 성인 콘텐츠 DB |
| nintendo | game | 8 | 닌텐도 공식 뉴스/eShop 등 |
| pts (공視新聞網) | traditional-media | 8 | 대만 공영방송 뉴스 |
| thenewslens (關鍵評論) | new-media | 8 | 대만 시사/오피니언 매체 |
| ustc (중국과학기술대학) | university | 8 | 중국 대학 공지 |
| bnu (베이징사범대학) | university | 7 | 중국 대학 공지 |
| chikubi | multimedia | 7 | 일본 성인 콘텐츠 사이트 |
| logclub (罗戈网) | new-media | 7 | 중국 물류업계 매체 |
| newslaundry | new-media | 7 | 인도 독립 저널리즘 매체 |

전체 목록은 `routes-catalog-by-site.csv`를 라우트 수(`route_count`) 기준 내림차순 정렬해서 보면 된다.

---

## 개발자向 IT 트렌드 추천 라우트

`category=programming`(218개) 및 관련 라우트를 코드로 직접 확인해 고른 목록. 전부 브라우저 불필요·일반 HTTP fetch 기반이며, 표시된 것 외엔 별도 인증/설정 불필요(코드 확인).

| 라우트 | 뭘 가져오나 | 예시 URL | 인증/설정 |
|---|---|---|---|
| `/hackernews/:section?/:type?/:value?` | Hacker News — index/newest/ask/show/jobs/threads 등 섹션별 스토리 | `/hackernews/newest` | 불필요 |
| `/github/trending/:since/:language/:spoken_language?` | GitHub 트렌딩 레포 (daily/weekly/monthly, 언어 필터) | `/github/trending/daily/javascript/en` | **`GITHUB_ACCESS_TOKEN` 필요** |
| `/github/topics/:name` | GitHub 특정 Topic(예: `framework`) 최신 레포 | `/github/topics/framework` | 불필요 |
| `/github/search/:query/:sort?/:order?` | GitHub 코드/레포 검색 결과 피드 | `/github/search/rsshub` | 불필요 |
| `/dev.to/top/:period` , `/dev.to/guides` | DEV Community 인기글/가이드 | `/dev.to/top/week` | 불필요 |
| `/producthunt/today` | Product Hunt 오늘의 신규 제품 런칭 | `/producthunt/today` | 불필요 |
| `/v2ex/topics/:type` (`hot`/`latest`) | V2EX(중국 개발자 대형 포럼) 인기/최신 글 | `/v2ex/topics/hot` | 불필요 |
| `/juejin/trending/:category/:type` | 掘金(중국 개발자 커뮤니티) 카테고리별(android/frontend/backend/ios 등) 인기글 | `/juejin/trending/frontend/monthly` | 불필요 |
| `/juejin/aicoding/:tag?/:sort?` | 掘金 AI 코딩 전용 태그 피드 | `/juejin/aicoding` | 불필요 |
| `/oschina/news/:category?` | 开源中国(OSChina) 오픈소스/IT 뉴스 | `/oschina/news` | 불필요 |
| `/infoq/recommend` | InfoQ 추천 아티클(소프트웨어 엔지니어링) | `/infoq/recommend` | 불필요 |
| `/hackerone/hacktivity` | HackerOne 공개 버그바운티 취약점 공개 피드(보안 트렌드) | `/hackerone/hacktivity` | 불필요 |
| `/npm/package/:name` | 특정 npm 패키지 릴리스 피드(의존성 업데이트 추적) | `/npm/package/react` | 불필요 |
| `/trendingpapers/papers/:category?/:time?/:cited?` | arXiv 트렌딩 논문(cs.AI 등 분야별) | `/trendingpapers/papers/cs.AI` | 불필요 |
| `/<tool>/changelog` 계열 | 개발 도구 릴리스 노트: `cursor`, `windsurf`, `gitpod`, `claude/code`, `raycast`, `typora` 등 다수(`category=program-update`, 128개) | `/cursor/changelog` | 대부분 불필요 |

**참고**: Reddit(r/programming 등)와 Lobsters는 레포에 라우트 자체가 없다(직접 확인 — `lib/routes/`에 `reddit`/`lobsters` 디렉터리 없음). 일반 IT 뉴스 매체(TechCrunch/The Verge)도 `new-media` 카테고리에 있다(`/techcrunch/news`, `/theverge/:hub?`).

---

## 한국(`lang: 'ko'`) 사이트 — 전체 11곳

`namespace.ts`의 `lang: 'ko'` 선언 기준 전수 확인(코드 확인). 대부분 라우트 1개짜리 소규모 지원이다.

| 사이트 | URL | 뭘 가져오나 |
|---|---|---|
| `yna` | yna.co.kr | 연합뉴스 — `/yna/:lang?/:channel?` |
| `kbs` | world.kbs.co.kr | KBS 월드 뉴스/투데이 — `/kbs/news/...`, `/kbs/today/...` |
| `joins` | joins.com | 중앙일보 — **중문판만** 지원(`/joins/chinese/:category?`), 한국어판 라우트는 없음 |
| `naver` | naver.com | 네이버 웹툰(`/naver/comic/:id`), 네이버 검색(`/naver/search/:category/:keyword`) |
| `melon` | melon.com | 멜론 음원 차트 — `/melon/chart/:category?` |
| `dcinside` | m.dcinside.com | 디시인사이드 특정 갤러리 게시판 — `/dcinside/board/:id` |
| `bntnews` | bntnews.co.kr | 연예/엔터 뉴스 — `/bntnews/:category?` |
| `etoland` | etoland.co.kr | 이토랜드 커뮤니티 게시판 |
| `kimlaw` | kimlaw.or.kr | 한국해양법학회 논문(Thesis) |
| `kcna` | kcna.kp | 조선중앙통신(북한 관영 매체) |
| `rodong` | rodong.rep.kp | 로동신문(북한 관영 매체) |

전부 브라우저 불필요·별도 인증 불필요(코드 확인). 눈에 띄는 점: 한국 대형 커뮤니티(에펨코리아, 클리앙, 뽐뿌 등)나 네이버 카페/블로그, 다음(Daum) 계열은 지원 목록에 없다 — 즉 "한국 커버리지"는 얇은 편이고, 뉴스통신사(연합/KBS) + 니치 커뮤니티 한두 개 정도로 요약된다.

**연합뉴스는 이미 자체 RSS를 공식 제공한다** (`lib/routes/yna/index.ts` 코드 확인) — RSSHub의 `/yna` 라우트는 스크래핑이 아니라 연합뉴스가 직접 운영하는 공식 RSS XML(`https://www.yna.co.kr/rss/<channel>.xml`, 영어판은 `https://en.yna.co.kr/RSS/<channel>.xml`)을 그대로 가져온다. 언어(`ko/en/cn/jp/ar/es/fr`)와 채널(정치/경제/스포츠 등, 연합뉴스 RSS 페이지에 나열된 값 그대로)을 경로 파라미터로 받는다. RSSHub가 여기 더하는 값은 **원문 전문(全文) 스크래핑** — 연합뉴스 공식 RSS는 요약/링크만 주는 경우가 많아서, RSSHub가 각 기사 링크에 추가로 접속해 본문 HTML을 긁어와 `description`에 채워 넣는다(관련 기사 박스, 기자 정보 블록 등은 제거). 즉 "RSS가 없어서 만든 것"이 아니라 "이미 있는 RSS를 본문까지 나오게 보강한 것"에 가깝다.

## YouTube / X(Twitter) / Facebook / Instagram 지원 현황

| 서비스 | 라우트 수 | 인증 필요 여부 | 비고 |
|---|---|---|---|
| **YouTube** | 8개 | 라우트마다 다름 — 아래 표 | 채널/재생목록/실시간방송/커뮤니티 게시글/차트 등 |
| **X (Twitter)** | 9개 | 대부분 `TWITTER_AUTH_TOKEN` 필요 (아래 설명) | 홈 타임라인, 유저 타임라인, 키워드 검색, 좋아요, 리스트, 트렌드 등 |
| **Facebook** | **0개 — 지원 안 함** | - | `lib/routes/`에 `facebook` 디렉터리 자체가 없음(직접 확인) |
| **Instagram** | **0개 — 지원 안 함** | - | 마찬가지로 디렉터리 없음 |
| Meta | 1개 | 불필요 | `/meta/ai/blog` — Facebook이 아니라 Meta사(社)의 공식 AI 블로그 |
| Threads | 2개 | 불필요 | 유저 타임라인/검색 |
| TikTok | 2개 | 불필요 | 유저 피드/라이브 |

Facebook/Instagram이 아예 없는 건 메타 계열이 스크래핑 방어가 극도로 강하고 공식 API도 비즈니스 승인이 필요해서 메인테이너가 아예 라우트를 만들지 않은 것으로 보인다(추론).

### YouTube 라우트 8개 상세 (코드 확인: `lib/routes/youtube/*.ts`)

| 라우트 | 뭘 가져오나 | 예시 | 인증 |
|---|---|---|---|
| `/youtube/channel/:id/:routeParams?` | 채널 ID로 최신 영상 목록 | `/youtube/channel/UCDwDMPOZfxVV0x_dz0eQ8KQ` | `YOUTUBE_KEY` **선택**(optional — 없어도 동작) |
| `/youtube/user/:username` | `@handle`로 최신 영상 목록 | `/youtube/user/@JFlaMusic` | `YOUTUBE_KEY` 선택 |
| `/youtube/c/:username` | 구(舊) Custom URL(`/c/...`)로 채널 조회 | `/youtube/c/YouTubeCreators` | `YOUTUBE_KEY` **필수** |
| `/youtube/playlist/:id` | 특정 재생목록의 영상 목록 | `/youtube/playlist/PLqQ1Rwlx...` | `YOUTUBE_KEY` 선택 |
| `/youtube/community/:handle` | 채널 커뮤니티 탭 게시글(텍스트/이미지 포스트, 영상 아님) | `/youtube/community/@JFlaMusic` | 불필요 |
| `/youtube/charts/:category?/:country?` | 유튜브 뮤직 차트(인기 아티스트/곡/뮤비, 국가별) | `/youtube/charts` | 불필요 |
| `/youtube/live/:username` | 채널의 현재 라이브 방송 | `/youtube/live/@GawrGura` | `YOUTUBE_KEY` **필수** |
| `/youtube/subscriptions` | **내 계정**의 구독 피드(내가 구독한 채널들의 통합 피드) | `/youtube/subscriptions` | 완전한 OAuth 필요(`YOUTUBE_KEY`+`CLIENT_ID`+`CLIENT_SECRET`+`REFRESH_TOKEN`) |

`channel`/`user`/`playlist`는 코드 주석에 "**YouTube provides official RSS feeds for channels**"라고 명시되어 있다 — 실제로 유튜브 자체가 채널마다 `https://www.youtube.com/feeds/videos.xml?channel_id=...`라는 공식 RSS를 이미 제공하고, RSSHub는 이를 기반으로 하되 `YOUTUBE_KEY`(선택)를 주면 추가 메타데이터를 API로 보강한다. 반면 `live`(현재 방송 중 여부 판별)와 `subscriptions`(내 계정 데이터)는 공식 RSS로 커버가 안 돼서 API 키/OAuth가 필수다.

### X(Twitter) 라우트 9개 상세 (코드 확인: `lib/routes/twitter/*.ts`)

| 라우트 | 뭘 가져오나 | 예시 |
|---|---|---|
| `/twitter/user/:id` | 특정 유저 타임라인 | `/twitter/user/_RSSHub` |
| `/twitter/home` | (인증 계정 기준) 홈 타임라인 — 팔로우 중인 사람들 피드 | `/twitter/home` |
| `/twitter/home_latest` | 홈 타임라인의 "최신순" 버전 | `/twitter/home_latest` |
| `/twitter/keyword/:keyword` | 키워드/해시태그 검색 결과 | `/twitter/keyword/RSSHub` |
| `/twitter/likes/:id` | 특정 유저가 좋아요한 트윗 | `/twitter/likes/DIYgod` |
| `/twitter/list/:id` | 특정 트위터 리스트의 타임라인 | `/twitter/list/1502570462752219136` |
| `/twitter/media/:id` | 특정 유저의 미디어(이미지/영상) 트윗만 | `/twitter/media/_RSSHub` |
| `/twitter/trends/:woeid?` | 지역별 실시간 트렌드(Yahoo WOEID로 국가/도시 지정) | `/twitter/trends/23424856` |
| `/twitter/tweet/:id/status/:status` | 트윗 1건 단건 조회(답글 스레드 포함) | `/twitter/tweet/DIYgod/status/1650844643997646852` |

**인증 방식 정정** — 지난 답변에서 "실계정 로그인(USERNAME/PASSWORD)"과 "playwright로 로그인 자동화"라고 말씀드린 건 부정확했다. `lib/routes/twitter/namespace.ts` 설명과 실제 코드를 다시 보니:
- `TWITTER_USERNAME`/`PASSWORD` 방식은 코드에서 **주석 처리(비활성)**되어 있고, namespace.ts에도 취소선과 함께 "2025년 10월부터 Twitter의 모바일 클라이언트 검증(attestation) 때문에 더 이상 작동하지 않음"이라고 명시돼 있다. 이걸 쓰던 `lib/routes/twitter/api/web-api/login.ts`(playwright 사용)도 호출부(`utils.ts`)에서 이제 주석 처리되어 죽은 코드다(코드 확인) — 즉 **현재는 브라우저 자동화를 쓰지 않는다.**
- 현재 실제로 쓰이는 방법은 둘 중 하나: (1) **`TWITTER_AUTH_TOKEN`**(권장) — 본인이 브라우저에서 X에 로그인한 뒤 나오는 `auth_token` 쿠키 값을 그대로 환경변수에 넣는 방식(RSSHub가 로그인을 대행하지 않음, 사람이 최초 1회 로그인해서 쿠키만 추출), (2) **`TWITTER_CONSUMER_KEY`/`SECRET`**(+선택적 `ACCESS_TOKEN`/`SECRET`) — X의 유료 Developer API 사용.
- 정리: X 라우트를 실제로 쓰려면 브라우저 자동화가 아니라 "로그인된 브라우저에서 쿠키 하나 복사해오기" 또는 "유료 API 키 구매" 둘 중 하나가 필요하다.

## IT 관련 "브라우저(headless) 필수" 라우트

전체 브라우저 라우트 104개 중 IT/프로그래밍/게임 카테고리는 **10개**뿐이고, 전부 로그인 없이 접근 가능하다(코드 확인):

| 라우트 | 뭘 가져오나 |
|---|---|
| `/alternativeto/software/:name/...`, `/alternativeto/platform/:name/...` | AlternativeTo — 소프트웨어 대안 추천/리뷰 |
| `/apkpure/versions/:pkg/:region?` | APKPure — 안드로이드 앱 버전 업데이트 |
| `/google/play/:id/:lang?` | Google Play 스토어 앱 업데이트 |
| `/hitcon/zeroday/vulnerability/:status?` | HITCON Zero-Day — 대만 보안 취약점(CVE류) 공개 피드 |
| `/perplexity/changelog` | Perplexity AI 체인지로그 |
| `/dailypush/:sort?`, `/dailypush/tag/:tag/...` | DailyPush — IT/개발 뉴스 큐레이션 |
| `/bluestacks/release/5` | BlueStacks(안드로이드 에뮬레이터) 릴리스노트 |
| `/fortnite/news/:options?` | 포트나이트 게임 뉴스 |

브라우저 라우트 104개의 나머지 대부분(22개)은 오히려 `university`(중국 대학 홈페이지가 JS 렌더링 기반인 경우), `traditional-media`/`social-media`(anti-crawler 강한 뉴스/SNS 사이트)에 몰려 있다 — "IT라서 브라우저가 필요하다"기보다는 "그 사이트가 얼마나 스크래핑 방어를 하는가"가 브라우저 필요 여부를 가르는 진짜 기준으로 보인다.

---

## 한계 (중요)

- **정적 regex 추출**이라 다음 케이스는 놓치거나 부정확할 수 있다:
  - `path`가 변수 조합·`join`·조건부로 동적 생성되는 소수 파일 (실행 없이는 못 뽑음)
  - `requirePuppeteer` 플래그가 실제 구현과 다르게 표시된 경우 (RSSHub 자체 기여 가이드에 "플래그를 정확히 표시하라"는 규칙이 있다는 건 반대로 실수 사례가 있었다는 의미로 추론됨)
  - 브라우저 사용 여부를 route 파일이 아니라 **같은 폴더의 `utils.ts` 같은 헬퍼 파일**에서 import하는 경우, 이 스크립트는 route 파일만 봐서 `uses_browser`가 `False`로 나올 수 있음 (그래서 `requirePuppeteer_flag`를 1차 지표로 사용함)
- **정확한 값이 필요하면**: `pnpm install && npm run build:routes`로 RSSHub가 실제로 만드는 `assets/build/routes.json`을 생성해 대조하는 게 정답이다. 이번엔 의존성 설치/실행 부담 때문에 하지 않았다 — 필요하면 다음 세션에서 실행 확인으로 격상 가능.
- 사이트 수(1,906)가 `namespace.ts` 파일 수(1,980)보다 적은 건, 일부 namespace 디렉터리에 이 스크립트가 인식하는 형태의 route 파일이 하나도 없었기 때문(중첩 namespace 구조 등) — 실행 확인 아님.
