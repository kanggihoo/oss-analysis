# Q3: RSSHub를 vps-info(signal-archive)에 어디까지 가져올 것인가 + 어떤 provider를 가져올 것인가

- **상위 개요**: [overview.md](../overview.md)
- **분석 대상 Commit SHA**: rsshub `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc` / vps-info `/Users/kkh/Desktop/vps/vps-info` (작업트리 직접 열람)
- **작성 일자**: `2026-09-20`
- **질문**: 별도 스케줄러로 주기적으로 DB에 적재하는 vps-info 구조를 유지하면서, RSSHub에서 **어디까지** 가져오고 **어떤 provider**를 가져올 것인가.
- **제약(사용자 결정)**: `diygod/rsshub` 컨테이너는 띄우지 않는다.

> **2026-09-24 갱신**: vps-info가 TypeScript(Fastify + Drizzle), 상주 수집기, DB 기반 스케줄로 재설계됐다.
> 이 문서의 vps-info 쪽 서술(1장 표, 2-2·2-3의 `SOURCES`·host cron·advisory lock, 3장 `ArchiveItem`, 5장 Python 스케치)은
> 옛 구조 기준이다. 유효한 부분은 **2-1 엔드포인트 카탈로그**와 **4장 provider 선정**이다.
> 재설계 기준의 재검토는 [Q4](./q4-vps-info-typescript-redesign.md)를 본다.

---

## 0. 결론 3줄

1. **두 프로젝트는 성격이 다르다** — RSSHub는 영속 저장이 **전혀 없는** 요청 시점 변환기다(코드 확인: DB 의존성 0, 캐시 TTL 300초가 상태의 전부). vps-info는 시계열 아카이브다. 겹치는 구간은 "사이트 → 정규화된 item 리스트" **한 단계뿐**이고, 그 바깥(스케줄링·dedup·이력·질의)은 RSSHub에 아예 없다.
2. 따라서 RSSHub는 **의존성이 아니라 카탈로그로 쓴다.** 컨테이너도, 코드 포팅도 아니고, `lib/routes/<site>/*.ts`를 열어 **그 사이트를 어떤 엔드포인트로 긁는지**만 베껴온다. 엔드포인트 발굴이 provider 추가의 실제 비용이고, RSSHub는 그걸 1,906개 사이트분 대신 해놓은 사전이다.
3. **스키마를 RSSHub에 맞출 이유도 없다.** 두 포맷은 겹치는 8개 필드가 이미 1:1로 매핑돼 있고, 나머지는 서로 목적이 달라 상대에게 없다 — `DataItem`에만 있는 13개는 전부 피드 렌더링용(`enclosure_*`, `itunes_*`, `media`, `image`)이고, `ArchiveItem`/`items`에만 있는 11개는 전부 저장·중복판정·이력용(`source`, `dedup_key`, `first_seen_at`/`last_seen_at`)이다. 필드 대조는 3장.

---

## 1. 두 프로젝트의 경계 (코드 확인)

| | RSSHub | vps-info (signal-archive) |
|---|---|---|
| 실행 모델 | 요청이 올 때만 동작(pull, stateless) | 스케줄러가 주기적으로 실행(one-shot 컨테이너) |
| 영속성 | **없음.** `package.json`에 postgres/sqlite/prisma/drizzle/mongo 의존성 0개. 상태는 `lib/utils/cache/`(memory·redis·kv·http)뿐이고 `routeExpire` 300초 / `contentExpire` 3600초 TTL (`lib/config.ts:795-796`) | PostgreSQL `items` + `job_run` (`alembic/versions/20260819_0{1,2}_*.py`) |
| 과거 | **모른다.** 피드에서 밀려난 항목은 영구 소실 | `dedup_key` + `first_seen_at`/`last_seen_at`으로 "언제 처음 봤나"를 보존 |
| 중복 처리 | 없음(매 요청 새로 생성) | `uq_items_source_dedup_key` upsert |
| 실행 관측 | 없음 | `job_run` 부모/자식 계층 + SUCCESS/PARTIAL/FAILED (`collector.py`) |
| 출력 | RSS/Atom/JSON 렌더링(`lib/views/`) | JSON API + 프론트엔드 |
| 겹치는 구간 | **사이트 → 정규화된 item 리스트** | 동일 |

→ "RSSHub에서 뭘 가져오나"라는 질문은 사실상 **"저 한 칸을 어떻게 채우나"**로 좁혀진다. 나머지 칸은 vps-info에만 있으므로 참고할 대상 자체가 없다.

---

## 2. Part A — 어디까지 가져오나

### 2-1. 가져오는 것: 엔드포인트 지식 (코드 아님)

provider 하나를 붙일 때 실제로 드는 비용은 파이썬 코드가 아니라 **"이 사이트를 뭘 호출해야 목록이 나오는가"**를 알아내는 일이다. RSSHub route 파일이 그 답을 이미 들고 있다.

| 대상 | RSSHub route가 때리는 엔드포인트 | 파일 |
|---|---|---|
| daily.dev | `POST https://api.daily.dev/graphql` — `anonymousFeed(ranking: POPULARITY)` 익명 쿼리 | `lib/routes/daily/{utils.tsx,popular.ts}` |
| Hugging Face | `huggingface.co/api/blog`, `/api/*` (daily-papers) | `lib/routes/huggingface/` |
| dev.to (기간별 top) | `dev.to/search/feed_content` | `lib/routes/dev.to/` |
| npm | `registry.npmjs.org/<pkg>` | `lib/routes/npm/` |
| Docker Hub | `hub.docker.com/v2/repositories/...` | `lib/routes/dockerhub/` |
| GitHub | `api.github.com` + trending은 HTML + GraphQL 하이브리드 | `lib/routes/github/` |
| TechCrunch | `techcrunch.com/wp-json/wp/v2/...` | `lib/routes/techcrunch/` |

이 표가 이 문서의 실질적 산출물이다. 코드는 한 줄도 안 가져오고, **URL과 파라미터 조합만** 가져온다.

### 2-2. 가져오는 것: 규약 2개

| 가져오는 것 | vps-info 반영 | 비용 |
|---|---|---|
| `<namespace>/<route-path>` 주소 규약 | job_key를 `dailydev:popular`처럼. 이미 `hackernews:best`로 `name:feed` 규약이 있음 | 0줄 |
| `features.requireConfig` 자기선언 | `SOURCES` 항목에 `requires_env: ("GITHUB_ACCESS_TOKEN",)`. 수집 실패 후 로그를 뒤지는 대신 시작 전 fail fast | 3줄, **GitHub trending을 붙일 때만** |

### 2-3. 가져오지 않는 것

| 안 가져옴 | 이유 |
|---|---|
| `diygod/rsshub` 컨테이너 | 사용자 결정. 아래 2-4에 그 대가를 기록 |
| `DataItem` 스키마 | 절반이 렌더링용 필드. `ArchiveItem`이 이미 상위 집합(3-1 표) |
| Hono / `worker.ts` / edge 런타임 | VPS에 상주 프로세스가 있고 소비자가 내부 스케줄러 하나다 |
| `registry.ts` 지연 import 로딩 | 라우트 3,462개를 위한 장치. provider 4~10개엔 `SOURCES` dict가 더 짧다 |
| `middleware/cache.ts` 요청 합류 | 동시 중복 요청이 생길 수 없음 — `pg_try_advisory_lock`이 단일 실행을 이미 보장 |
| `views/` RSS/Atom/JSON 렌더링 | vps-info의 목적은 저장이지 재발행이 아니다 |
| 스케줄러/큐 패턴 | **RSSHub에 없다.** on-demand pull이 전부. host cron이 `docker compose run --rm collector`를 때리는 현재 방식이 맞다 |

### 2-4. 컨테이너를 안 띄우는 대가 (기록용)

| | 컨테이너 | 직접 구현 |
|---|---|---|
| provider 추가 비용 | `SOURCES` dict 한 줄 | 공식 RSS 있으면 한 줄 / 없으면 `sources/<name>.py` 40~60줄 |
| 대상 사이트가 바뀌었을 때 | 업스트림이 고쳐줌 (`docker pull`) | **직접 고쳐야 함** |
| 운영 부담 | 서비스 +1, 이미지 ~150MB, 네트워크 홉 +1 | 없음 |
| 손익 분기 | provider 10개 이상 + 비공식 엔드포인트 위주 | provider 1~5개 |

현재 목표 provider가 5개 이하이므로 **직접 구현이 맞다.** 다만 `daily.dev`처럼 비공식 GraphQL을 쓰는 provider가 3개를 넘어가고 깨짐이 반복되면, 그때 이 판단을 다시 본다.

---

## 3. Part B — 스키마: 필드 대조

### 3-1. 두 포맷의 전체 필드

**RSSHub `DataItem`** (`lib/types.ts:32-77`, `*`는 필수):

```
title*  description  pubDate  link  category  author  doi  guid  id
content{html,text}  summary  image  banner  updated  language
enclosure_url  enclosure_type  enclosure_title  enclosure_length
itunes_duration  itunes_item_image  media  attachments[]
upvotes  downvotes  comments  _extra
```

**vps-info `ArchiveItem`** (`signal_archive/schemas.py`) + DB `items` 전용 컬럼:

```
source*  source_method*  title*  url*
external_id  summary  source_item_url  author  published_at
score  comments_count  rank  item_type  tags  raw
── items 테이블에만: dedup_key*  first_seen_at*  last_seen_at*
```

### 3-2. 겹치는 것 (8) — 1:1 대응, 조치 없음

| `DataItem` | `ArchiveItem` |
|---|---|
| `title` | `title` |
| `link` | `url` |
| `guid` / `id` | `external_id` |
| `pubDate` | `published_at` |
| `author` | `author` |
| `category[]` | `tags` |
| `summary` / `description` | `summary` |
| `upvotes` / `comments` | `score` / `comments_count` |

### 3-3. `DataItem`에만 있는 것 (13) — 전부 렌더링/미디어용

`doi` · `content.html` · `image` · `banner` · `updated` · `language` · `downvotes` · `enclosure_url/type/title/length` · `itunes_duration` · `itunes_item_image` · `media` · `attachments[]`

팟캐스트(`enclosure_*`, `itunes_*`), 첨부(`attachments`), 학술(`doi`), 썸네일(`image`/`banner`) — 피드로 **다시 내보내기 위한** 필드다. vps-info가 아쉬울 수 있는 건 현실적으로 **`image`(썸네일)** 하나이고, 프론트가 카드 썸네일을 요구하면 그때 추가한다.

> 이전 판에서 "`ArchiveItem`이 `DataItem`의 상위 집합"이라고 쓴 것은 틀렸다. 전체 필드 집합으로는 상위 집합이 아니다. 정확히는 **저장·질의라는 축에서만** `ArchiveItem`이 `DataItem`을 덮고 더 갖고 있다.

### 3-4. `ArchiveItem`/`items`에만 있는 것 (11) — RSSHub에 대응 개념 없음

`source` · `source_method` · `source_item_url` · `score`/`comments_count`/`rank`(정수 검증) · `item_type` · `raw` · `dedup_key` · `first_seen_at` · `last_seen_at`

### 3-5. 성격 차이가 드러나는 지점 (코드 확인)

| | RSSHub `DataItem` | vps-info `ArchiveItem` |
|---|---|---|
| **필수 필드** | `title` **하나뿐**. `link`조차 optional — 통과 기준이 "RSS로 렌더링 가능한가" | `source`/`source_method`/`title`/`url` 4개 + `url`은 `HttpUrl` 검증 — 기준이 "저장하고 중복 판정할 수 있는가" |
| **출처의 위치** | **item에 없음.** URL 경로(`/daily/popular`)가 곧 출처이고 item은 그걸 모른다 | `source`가 item 필수 필드이자 중복 판정의 스코프 (`ON CONFLICT (source, dedup_key)`, `repository/items.py`) |
| **링크** | `link` 하나 — "원문 URL"과 "사이트 내 게시물 URL"을 구분 못 함. `/hackernews/*`가 원문 URL을 description HTML에 묻는 이유 | `url` / `source_item_url` 분리 |
| **타입 엄격도** | `upvotes?: number`로 선언해놓고 hackernews 라우트가 `string \| number`로 덮어씀 | `StrictInt` + `extra="forbid"`, 원본은 `raw: dict`에 격리 |
| **중복 판정** | 없음 (매 요청 새로 생성) | `external_id` 우선, 없으면 정규화 URL의 sha256 (`make_dedup_key`, ADR-0001) |

→ **`ArchiveItem`을 고치지 않는다.** "공통 포맷을 맞춘다"는 목표에서 실제로 할 일은 없다 — 겹치는 8개는 이미 매핑돼 있고 나머지는 각자 목적에만 필요한 필드다. 선택지는 `image` 하나 추가 여부뿐이다.

### 3-6. 참고: 컨테이너를 쓰는 경우에만 유효한 함정 (보류)

이번 결정으로 적용되지 않지만, 나중에 컨테이너 방식으로 선회하면 반드시 다시 볼 것:

- `upvotes`/`downvotes`/`comments`는 **Atom 출력에만** `rsshub:` 확장 요소로 실린다(`lib/views/atom.tsx:40-42`). RSS 2.0과 JSON Feed(`lib/views/json.ts`)에는 매핑이 아예 없어 `score`/`comments_count`가 조용히 `None`이 된다. → `?format=atom` 강제.
- feedparser는 이를 `rsshub_upvotes`/`rsshub_comments` 문자열로 노출한다(**실행 확인**: vps-info `.venv`, 합성 Atom 입력).
- `rank`는 어떤 포맷으로도 오지 않는다.

## 4. Part C — 어떤 provider를 가져오나

판단 기준은 컨테이너 유무와 무관하게 동일하다: **공식 RSS가 있으면 그걸 직접 쓴다.** RSSHub는 없을 때만 참고한다.

### 4-1. Tier B 먼저 — 코드 0줄, dict 한 줄

RSSHub route 소스를 열어보니 **공식 피드를 그대로 프록시**하거나 공식 피드가 존재한다. 여기서 시작하는 게 비용 대비 효과가 가장 크다.

| 대상 | 직접 쓸 URL | 근거 |
|---|---|---|
| The Verge | `https://www.theverge.com/rss/index.xml` | `lib/routes/theverge/`가 **그 URL을 그대로 가져다 쓴다** |
| OpenAI News | `https://openai.com/news/rss.xml` | `lib/routes/openai/` 내 URL 상수로 확인 |
| dev.to (최신) | `https://dev.to/feed` | 기간별 top이 필요 없으면 충분 |
| TechCrunch | 공식 `/feed` | RSSHub route는 `wp-json` 기반 — 카테고리 분리가 필요할 때만 참고 |

`_rss_source()`가 이미 있으므로 **각각 `SOURCES`에 한 줄**이다.

### 4-2. Tier A — 직접 구현할 가치가 있는 것

| 라우트 | 왜 직접 짜나 | score/comments |
|---|---|---|
| **daily.dev `/daily/popular`, `/daily/upvoted/:period`** | 공식 RSS 없음. **`score`/`comments_count`/`rank`를 실제로 채워주는 거의 유일한 추가 개발자향 소스** | **있음** (`lib/routes/daily/utils.tsx:89-90`) |
| `/huggingface/daily-papers` | 공식 RSS 없음, API 기반, 투표수 포함 | **있음** |
| `/anthropic/news`, `/anthropic/engineering`, `/openai/research`, `/claude/code/changelog`, `/cursor/changelog` | 공식 RSS 없는 1차 출처. 단 **HTML 스크래핑이라 직접 구현 시 유지보수를 떠안는다** — 우선순위 낮춤 | 없음 |
| `/npm/package/:name`, `/dockerhub/tag/...` | registry/API 기반이라 안정적. 다만 "시그널"이 아니라 운영 성격 | 없음 |

**1순위는 daily.dev 하나다.** vps-info의 `score`/`comments_count`/`rank` 컬럼은 현재 hackernews만 채우고 있고, upvotes를 실제로 emit하는 RSSHub 라우트 전수 조사(`upvotes:` grep) 결과 개발자향으로 남는 건 `daily`와 `huggingface`뿐이다.

### 4-3. Tier C — 가져오지 않음

| 대상 | 이유 |
|---|---|
| **`/hackernews/:section?`** | **현재 구현이 상위 호환.** vps-info는 공식 Firebase API로 `score`/`descendants`를 정수로, 원문 URL과 HN 아이템 URL을 분리해 받는다. RSSHub는 HTML 스크래핑이고 점수·댓글이 문자열이며 원문 URL이 description HTML에 묻힌다(`lib/routes/hackernews/index.ts`). 교체는 다운그레이드 |
| `/producthunt/today` | 이미 공식 피드 사용 중. RSSHub route도 upvotes를 싣지 않는다(`lib/routes/producthunt/today.tsx` 확인) |
| `/github/trending` | 가치 높으나 `GITHUB_ACCESS_TOKEN` 필수 + HTML/GraphQL 하이브리드라 직접 구현 시 유지보수 부담이 가장 크다. 2-2의 `requires_env`부터 |
| `/lemmy/*` | `ALLOW_USER_SUPPLY_UNSAFE_DOMAIN` 필요 |
| 중국어권(58.2%) / `university` / `government` | vps-info 목적과 무관 |
| 한국어 라우트(`/yna`, `/naver/search`, `/dcinside`, `/kbs`) | 동작은 하지만 "개발자·인디 제품 시그널" 축 밖 |

---

## 5. 구현 스케치 — daily.dev

RSSHub `popular.ts`의 GraphQL 쿼리에서 **실제로 필요한 필드만 남기면** 아래로 줄어든다. 나머지(`userState`, `bookmark`, `clickbaitTitleDetected`, `collectionSources` 등)는 daily.dev 웹앱 UI용이라 전부 뺀다.

```python
# signal_archive/sources/dailydev.py  (hackernews.py와 같은 자리)
NAME, METHOD = "dailydev", "unofficial_rss"
GQL = "https://api.daily.dev/graphql"
QUERY = """
query AnonymousFeed($first: Int, $ranking: Ranking, $version: Int) {
  page: anonymousFeed(first: $first, ranking: $ranking, version: $version) {
    edges { node {
      id title permalink commentsPermalink createdAt
      numUpvotes numComments summary tags type
      author { name }
      sharedPost { title summary permalink }
    } }
  }
}
"""

def fetch(limit: int) -> FetchResult:
    body = {"query": QUERY, "variables": {"first": limit, "ranking": "POPULARITY", "version": 54}}
    edges = _post(GQL, body)["data"]["page"]["edges"]          # _http_retry 정책 재사용
    items, skipped = [], 0
    for rank, edge in enumerate(edges, start=1):
        node = edge["node"]
        post = node["sharedPost"] if node.get("type") == "share" else node
        if not post.get("title"):
            skipped += 1
            continue
        items.append(ArchiveItem(
            source=NAME, source_method=METHOD,
            external_id=node["id"],
            title=post["title"],
            url=node["permalink"],                    # 원문으로 redirect되는 daily.dev 짧은 링크
            source_item_url=node.get("commentsPermalink"),
            summary=post.get("summary"),
            author=(node.get("author") or {}).get("name"),
            published_at=node["createdAt"],           # ISO8601 → ArchiveItem validator가 UTC 정규화
            score=node.get("numUpvotes"),
            comments_count=node.get("numComments"),
            rank=rank,                                # POPULARITY 정렬이므로 순서 = 순위
            item_type=node.get("type"),
            tags=node.get("tags") or [],
            raw={k: node.get(k) for k in ("id", "type", "numUpvotes", "numComments", "permalink")},
        ))
    return FetchResult(items=items, skipped=skipped, retry_count=0)
```

- `sources/__init__.py`의 `SOURCES`에 `{"name","method","target","fetch","fetch_raw"}` 항목 추가 + `collection_jobs()`에 `"dailydev"` 추가.
- `_http_retry.py`의 재시도 정책(429/502/503, `Retry-After` 존중)을 그대로 재사용한다.
- **주의**: `permalink`은 `api.daily.dev/r/<id>` 형태의 **리다이렉트 URL**이지 최종 원문 URL이 아니다. 최종 URL이 필요하면 HEAD 요청 한 번을 더 해야 하는데, dedup이 `url` 기준이면 이게 중복 판정에 영향을 준다. 우선은 리다이렉트 URL 그대로 저장하고, 중복이 실제로 문제가 되면 그때 해소한다.
- 검증: `tests/test_sources.py`에 edges 픽스처 하나. 매핑이 깨지면 값이 조용히 `None`이 되는 종류라 검증 하나는 필요하다.

**총 변경량**: Tier B 4개 = dict 4줄. daily.dev = 새 파일 ~50줄 + dict 1줄 + 테스트 1개. 컨테이너 0개.

---

## 6. 검증 수준

| 항목 | 수준 |
|---|---|
| RSSHub에 영속 계층이 없음(DB 의존성 0, 캐시 TTL만) | **코드 확인** — `package.json`, `lib/utils/cache/`, `lib/config.ts:795-796` |
| 라우트별 대상 엔드포인트, `DataItem`/`views` 필드 출력 | **코드 확인** (commit `0a4ecdb0`) |
| feedparser의 `rsshub_*` 노출 | **실행 확인** (컨테이너 미사용 결정으로 현재는 미적용) |
| vps-info 현재 구조(스키마·마이그레이션·collector·compose) | **코드 확인** (작업트리 직접 열람) |
| 라우트별 config/browser 요구, 카테고리·언어 분포 | **코드 확인**(정적 카탈로그 — regex 추출 한계는 [routes-catalog-overview.md](../routes-catalog-overview.md) 참고) |
| 5장 스케치가 실제로 200을 반환하는가 | **미확인** — daily.dev GraphQL을 호출해본 적 없음. `version: 54`는 RSSHub가 고정해둔 값이라 상향될 수 있고, 익명 쿼리가 막힐 수도 있다 |
| 각 대상의 공식 RSS 존재 여부 | theverge/openai는 route가 공식 URL을 직접 참조하므로 **코드 확인**, 나머지는 **추론** |
