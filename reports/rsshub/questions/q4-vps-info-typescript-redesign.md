# [Q] vps-info가 TypeScript 상주 수집기로 재설계된 뒤, RSSHub에서 가져올 구조는 무엇인가

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: rsshub `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc` / vps-info 아키텍처 결정 `docs/adr/0005`–`0009` (2026-09-24)
- **검증 수준**: 코드 확인 (RSSHub 측). vps-info 측은 아직 구현 전이라 결정 문서 기준
- **작성 일자**: `2026-09-24`

---

## 1. 질문 및 결론

- **질문**: [Q3](./q3-vps-info-adoption.md)는 옛 Python one-shot 수집기를 기준으로 썼다. vps-info가 TypeScript(Fastify + Drizzle), 상주 수집기, DB 기반 스케줄로 재설계된 지금, RSSHub에서 가져올 구조와 Q3에서 유효하지 않게 된 부분은 무엇인가?
- **핵심 결론**: Q3의 결론인 "**엔드포인트 카탈로그로만 쓴다**"와 provider 우선순위는 그대로 유효하다. 언어가 같아지면서 새로 생긴 선택지는 **RSSHub가 쓰는 MIT 라이브러리**(`ofetch`, `rss-parser`, `cheerio`)를 그대로 쓰는 것이다. 라우트 코드는 AGPL-3.0이라 복사하지 않는다. 구조 쪽에서는 "공통 정책은 코어에, 사이트 지식은 플러그인에"라는 분리만 가져오고, 등록 방식(디렉터리 스캔)은 규모가 달라 반대로 간다.

---

## 2. 동작 설명

### 2-1. 가져온 것

| RSSHub 구조 | vps-info 반영 | 근거 |
|---|---|---|
| 라우트 자기선언 (`export const route: Route = {…}`) | Handler 파일이 이름, 파라미터 타입, 수집 함수를 함께 선언 | vps-info ADR-0009 |
| 공통 HTTP 클라이언트 (`ofetch.create`) | 코어가 설정한 클라이언트를 Handler에 주입. **타임아웃 10초를 켜고**, 재시도는 네트워크 오류·타임아웃·408/425/429/5xx에만 한다 | vps-info ADR-0009 |
| `Data.allowEmpty` + 0건이면 예외 | 같은 규칙. 단 값은 Handler 반환값이 아니라 **Feed 선언**에 둔다 | vps-info ADR-0008·0009 |
| 공통 정책의 미들웨어 격리 | 재시도, 타임아웃, 중복 판정, 저장, 0건 판정을 코어가 맡고 Handler는 Entry 목록만 반환 | vps-info CONTEXT.md의 Handler 정의 |

### 2-2. RSSHub와 반대로 간 것

| RSSHub | vps-info | 이유 |
|---|---|---|
| 디렉터리 스캔 자동 등록 (dev: `directoryImport`, prod: `assets/build/routes.js`) | `handlers/index.ts`에 import 한 줄씩 적는 명시적 목록 | Handler가 5~10개 수준. 명시적 목록이면 Feed 선언 파라미터를 타입으로 검사할 수 있다 |
| 400·409를 포함한 9종 상태 코드 재시도, 타임아웃 주석 처리 | 4xx는 408/425/429만 재시도, 타임아웃 10초 | 같은 요청을 다시 보내도 결과가 같은 4xx는 재시도해 봐야 소용없다 |
| `parameter.ts`가 `pubDate` 내림차순으로 정렬 | First Seen(최초 수집 시각)이 정렬 축 | 오래전에 게시된 글이 뒤늦게 목록에 올라와도 새 Entry로 보이게 하기 위해서다 |

### 2-3. 가져오지 않은 것 (Q3과 같은 결론, 이유는 갱신)

- 캐시와 요청 합류: 상주 스케줄러가 하나이고 Feed를 순차로 실행하므로 동시 중복 요청이 생기지 않는다. Q3에서는 advisory lock을 근거로 들었지만 그 장치는 없어졌다.
- 오류 타입 분류(`NotFound`/`Reject`/`ConfigNotFound`/`Captcha`): 지금은 Fetch Attempt의 오류 메시지로 충분하다.
- `features.requireConfig`: 토큰이 필요한 첫 Handler(GitHub trending 등)가 생길 때 추가한다.
- 지연 import, Hono 멀티 런타임, RSS/Atom 렌더링, Radar

### 2-4. Q3에서 유효하지 않게 된 부분

| Q3 위치 | 바뀐 점 |
|---|---|
| 1장 표의 vps-info 열 | one-shot 실행, `items`/`job_run`, `PARTIAL`, `last_seen_at`이 모두 없어졌다. 지금은 상주 수집기, `entry`, `fetch_attempt`, `next_run_at`이다 |
| 2-2 `name:feed` job_key, `SOURCES` dict | Feed는 코드로 만들고 DB가 운영 값을 소유한다. Feed 식별자는 문자열 slug다 |
| 2-3 "host cron이 맞다" | 상주 컨테이너로 바뀌었다 (vps-info ADR-0007) |
| 3장 `ArchiveItem` 필드 대조 | Python 스키마는 폐기됐다. 공통 컬럼 + `extra` + `raw` 구조로 바뀌었다 (vps-info ADR-0006) |
| 5장 daily.dev Python 스케치 | TypeScript Handler로 다시 써야 한다. GraphQL 쿼리와 필드 매핑 지식은 유효하다 |

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 라우트 스키마 | `lib/types.ts:372` | `interface Route` / `RouteItem` | `path`, `parameters`, `features.requireConfig`, `handler` 자기선언 |
| 0건 판정 | `lib/middleware/parameter.ts:71` | `middleware` | `item`이 비어 있고 `allowEmpty`가 아니면 `throw new Error('this route is empty…')` |
| 정렬 | `lib/middleware/parameter.ts` (같은 미들웨어) | `toSorted(… pubDate …)` | `?sorted=false`가 아니면 `pubDate` 내림차순 |
| HTTP 클라이언트 | `lib/utils/ofetch.ts` | `rofetch` | `retryStatusCodes: [400, 408, 409, 425, 429, 500, 502, 503, 504]`, `retryDelay: 1000`, `timeout` 주석 처리 |
| 오류 분류 | `lib/errors/index.tsx`, `lib/errors/types/*` | `errorHandler` | `RejectError`→403, `NotFoundError`→404, 나머지 503 |
| 자동 등록 | `lib/utils/directory-import.ts`, `lib/registry.ts:42-62` | `directoryImport`, `namespaces` | dev는 디렉터리 스캔, prod는 `assets/build/routes.js` |
| RSS 파서 | `lib/utils/rss-parser.ts` | `parser` | `rss-parser` 3.13.0 인스턴스. `package.json`에 `cheerio` 1.2.0, `ofetch` 1.5.1 |
| 라이선스 | `LICENSE` | — | AGPL-3.0 |

---

## 4. 검증 과정 및 실행 결과

- **수행한 명령**:
  ```bash
  git -C repos/rsshub rev-parse HEAD
  grep -rn "allowEmpty" lib/middleware lib/errors lib/*.ts*
  sed -n 60,85p lib/middleware/parameter.ts
  cat lib/utils/ofetch.ts
  grep -n "rss/\|parseURL\|\.xml" lib/routes/theverge/index.ts
  grep -rn "rss.xml" lib/routes/openai
  ```
- **실행 결과**: HEAD는 `0a4ecdb0…`로 위키와 같다. `allowEmpty` 검사는 `parameter.ts:71`에 있다. `ofetch.ts`의 `timeout` 줄은 주석 처리돼 있다. theverge는 `https://www.theverge.com/rss/index.xml`을 `parser.parseURL`로 읽은 뒤 본문을 따로 가져오고, openai는 `common.tsx:56`에서 `https://openai.com/news/rss.xml`을 쓴다.
- **판단 근거**: 위키 `[[rsshub]]`의 주요 주장(영속 계층 없음, 자기선언, HN HTML 스크래핑, 공식 RSS 프록시)을 모두 코드로 다시 확인했다. 새로 확인한 사실은 `allowEmpty`, 재시도 상태 코드, 꺼져 있는 타임아웃이다.

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] daily.dev GraphQL(`version: 54`)이 실제로 200을 돌려주는지 **실행 확인** (Q3에서 넘어온 항목)
- [ ] `config.requestRetry`의 기본값과 `x-prefer-proxy` 헤더가 프록시 전환에 쓰이는 방식
