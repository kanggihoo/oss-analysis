# [Q] Worker 실행 모델 / bootstrap 개념 / registry-routes 관계 / site 문서화

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- **검증 수준**: 코드 확인 (일부 Cloudflare Workers 실행 모델 일반 지식은 `추론` — 공식 문서 미대조)

---

## 1. 질문 및 결론

- **질문 (5개)**:
  1. `worker.ts`의 "worker"는 24시간 서버가 아니라 AWS Lambda 같은 엣지 함수 개념인가?
  2. `app-bootstrap.tsx`는 컴퓨터 부팅처럼 "초기 설정"을 담당하는 게 맞나?
  3. registry가 "URL을 플러그인에 배정한다"는 게 무슨 뜻이고, 여기서 "플러그인"이란 무엇인가?
  4. registry와 routes의 역할 구분이 잘 안 되는데, 실제 URL 구조와 매칭 흐름은?
  5. `routes/<site>/`의 "site"가 뭘 의미하는지 문서화되어 있나?
- **핵심 결론**:
  1. 맞다 — Cloudflare Workers는 V8 isolate 기반 서버리스 엣지 함수다. 다만 AWS Lambda(컨테이너/VM 콜드부트)보다 더 가볍고(수 ms), 유휴 시 완전히 죽었다가 다음 요청에 다시 뜨는 것도 맞지만 "매 요청마다 새로 뜬다"는 아니고 warm 상태면 재사용된다. `wrangler.toml`의 "Free plan has 10ms CPU time limit per request / Paid plan has 30s"가 이 모델의 직접적 증거다.
  2. 맞다 — `app-bootstrap.tsx`의 코드(`new Hono()`, `app.use(...)` 체인)는 프로세스(또는 isolate)가 뜰 때 **딱 한 번** 실행되고, 그 이후 모든 요청은 이미 조립된 미들웨어 체인을 그냥 통과한다. "매 요청마다 재부팅"이 아니다.
  3. registry는 URL의 첫 세그먼트(namespace)로 어떤 `routes/<site>/` 폴더가 처리할지 고르고, 그 안에서 정의된 path 패턴으로 세부 handler를 고른다. "플러그인"이란 `routes/<site>/*.ts`가 스스로 `{ path, handler }`를 선언한 독립 모듈을 뜻하며, registry는 그 선언을 읽어서 마운트만 할 뿐 사이트별 로직을 전혀 갖고 있지 않다.
  4. URL 구조는 `/<namespace>/<route-path>` (예: `/github/activity/DIYgod` = namespace `github` + route-path `/activity/:user`). 흐름은 [url-to-plugin-flow.html](../diagrams/url-to-plugin-flow.html) 시퀀스 다이어그램 참고.
  5. 별도 README는 의도적으로 금지되어 있다(레포 자체 `AGENTS.md` 규칙 #7). 대신 `Route.description`/`Route.parameters`/`namespace.ts`에 코드로 문서를 적으면 `/api/namespace/:namespace` 같은 엔드포인트가 이를 JSON으로 노출하고, 이걸 외부 docs.rsshub.app과 RSSHub Radar 확장이 소비해서 "동적으로 생성되는 문서"를 만든다.

---

## 2. 동작 설명 및 관련 그림

- 관련 다이어그램: [structure.html](../diagrams/structure.html) (전체 구조), [url-to-plugin-flow.html](../diagrams/url-to-plugin-flow.html) (URL→플러그인 매칭 시퀀스, 신규)

### (1) Worker = 엣지 서버리스 함수, 24시간 서버 아님

- `wrangler.toml`에 명시된 주석이 결정적 증거다: `# Free plan has 10ms CPU time limit per request` / `# Paid plan has 30s CPU time limit per request`. **요청 단위로 CPU 시간이 과금/제한**되는 건 "항상 켜져 있는 서버 프로세스"가 아니라 **요청이 올 때만 실행되는 함수** 모델의 전형적 특징이다 (Lambda의 과금 방식과 동일한 사고방식).
- 다만 정확히 짚을 부분(추론): Cloudflare Workers는 Lambda처럼 매 요청마다 컨테이너/VM을 새로 띄우는 게 아니라 **V8 isolate**(Node의 Worker Threads와 비슷한, 훨씬 가벼운 격리 단위)를 쓴다. 그래서 콜드스타트가 수 ms 수준으로 Lambda보다 훨씬 빠르고, 트래픽이 있으면 isolate가 "warm" 상태로 재사용되어 매번 처음부터 뜨지 않는다. 트래픽이 끊기면 결국 회수(evict)된다는 점은 Lambda와 개념적으로 같다 — "24시간 떠 있는 서버가 아니라 필요할 때만 살아있다"는 사용자의 이해가 맞다.
- 코드 근거: `lib/app.worker.tsx`가 `lib/app-bootstrap.tsx`와 별도로 존재하는 이유도 이 실행 모델 때문이다 — Workers 환경에는 Node 전용 모듈(`compress()`, honeybadger/sentry Node SDK 등)이 없어서 뺐고, 대신 `KVNamespace`(캐시), `BROWSER` 바인딩(Cloudflare의 Browser Rendering API — 브라우저 자동화가 필요한 라우트를 위해 실제 프로세스를 띄우는 대신 Cloudflare가 제공하는 원격 브라우저를 씀), `PLAYWRIGHT_SERVICE`(원격 Playwright 서비스 바인딩) 같은 **Workers 전용 환경 바인딩**을 요청마다 주입한다(`app.use(async (c, next) => { setBrowserBinding(c.env?.BROWSER); ... })`).
  - 즉 이전 구조도에서 "Entrypoint = index.ts 또는 worker.ts, 둘 다 같은 app-bootstrap을 부른다"고 단순화했었는데, 정확히는 **Node용 app-bootstrap.tsx와 Workers용 app.worker.tsx가 별도 파일**이며 미들웨어 목록이 거의 같지만 완전히 동일하지는 않다 — 구조도의 의도적 단순화 지점.

### (2) app-bootstrap = 부팅, 맞다 — 단 "한 번만" 실행된다는 게 핵심

- `lib/app-bootstrap.tsx`를 보면 `const app = new Hono(); app.use(...9개 미들웨어...); app.route('/', registry); export default app;` 형태로, **모듈이 import되는 시점에 딱 한 번** 실행되는 코드다. 요청이 100개 오든 100만 개 오든 이 조립 코드는 다시 실행되지 않는다.
- 컴퓨터 부팅 비유가 정확한 이유: 부팅이 끝나면 OS는 매 사용자 동작마다 재부팅하지 않고, 이미 초기화된 커널/드라이버 위에서 요청을 처리한다. 여기서도 마찬가지로 "부팅"(미들웨어 체인 조립)이 끝난 뒤에는 각 HTTP 요청이 이미 만들어진 파이프라인을 통과할 뿐이다.
- 다만 이 "부팅"이 일어나는 **단위**가 다르다: Node(`index.ts`)에서는 프로세스가 뜰 때 한 번(그리고 `cluster`로 띄운 각 워커 프로세스마다 한 번씩), Cloudflare Workers에서는 **isolate가 새로 뜰 때(콜드스타트)마다** 한 번 — isolate가 warm 상태로 재사용되는 동안은 재부팅되지 않는다.

### (3)+(4) registry ↔ routes: "플러그인"의 정확한 의미와 URL 매칭

- **"플러그인"이 가리키는 것**: `lib/routes/github/activity.ts` 같은 파일이 `export const route: Route = { path: '/activity/:user', handler: async (ctx) => {...} }` 형태로 **자기 자신을 스스로 선언**한다. registry는 이 선언을 걷어서 앱에 등록할 뿐, `routes/` 폴더 안의 어떤 사이트가 뭘 하는지에 대한 지식을 전혀 갖고 있지 않다. 이것이 "플러그인" — 코어(registry)를 수정하지 않고도 새 `.ts` 파일 하나 추가만으로 새 기능(새 사이트 지원)이 등록되는 구조.
- **URL 구조**: `https://rsshub.app/<namespace>/<route-path>`
  - `namespace` = `lib/routes/` 바로 아래 폴더 이름 (예: `github`) — `lib/registry-helpers.ts`의 `collectNamespaceRoots()`가 `namespace.ts` 파일이 있는 디렉터리를 namespace root로 수집한다.
  - `route-path` = 그 폴더 안 라우트 파일이 선언한 `path` 패턴 (예: `/activity/:user`)
- **매칭 2단계** (코드 근거: `lib/registry-helpers.ts`의 `registerRssRoutes()`):
  1. `app.basePath('/github')`로 namespace별 sub-app을 미리 다 마운트해둔다(이건 앱 시작 시, 즉 "부팅" 단계에서 한 번 수행).
  2. 실제 요청이 오면 Hono 라우터가 `/github` sub-app 안에서 `/activity/:user` 패턴과 매칭한다. 이때 리터럴 경로가 파라미터 경로보다 항상 먼저 매칭되도록 `sortRoutes()`가 미리 정렬해둔다(그래야 `/user/settings` 같은 리터럴 경로가 `/user/:id` 파라미터 경로에 잘못 먹히지 않는다).
  3. 매칭된 라우트의 실제 handler 함수가 아직 로드 안 됐으면(prod 빌드 최적화) 그 시점에 `routeData.module()`로 지연 import한다.
- 이 흐름을 URL 예시 하나(`GET /github/activity/DIYgod`)로 시각화한 시퀀스 다이어그램을 새로 그렸다 → [url-to-plugin-flow.html](../diagrams/url-to-plugin-flow.html)

**registry vs routes 구분에 대한 질문("사용자 입장에서 모든 사이트의 플러그인을 알 필요 없이 URL만 알면 되도록 나눈 것인가")에 대한 답: 정확히 맞다.** 이건 관심사 분리(separation of concerns)의 두 방향을 동시에 만족시킨다:
- **사용자 쪽**: URL 규칙(`/namespace/route-path`)만 알면 되고, 내부에 1,902개 플러그인이 있다는 걸 몰라도 된다.
- **기여자 쪽**: 새 사이트를 추가하는 사람은 `routes/<new-site>/`에 파일만 추가하면 되고, registry나 라우팅 메커니즘을 전혀 건드릴 필요가 없다(오히려 건드리면 안 된다 — 위 Q1 답변의 계층 분리 이유와 동일한 논리).

### (5) `routes/<site>/`의 "site" 문서화

- 레포 안에 사이트별 `README.md`는 **의도적으로 없다.** 레포 자체 `AGENTS.md`(리뷰 가이드)의 규칙 #7: *"Do not create separate README.md or radar.ts files. Put descriptions in `Route['description']` and radar rules in `Route['radar']`."* — 즉 "문서"는 코드 안의 구조화된 필드(`namespace.ts`의 `name`/`url`/`description`, 각 route 파일의 `description`/`parameters`/`radar`)로만 존재한다.
- 이게 어떻게 "사람이 읽는 문서"가 되냐면: `lib/api/namespace/one.ts`가 `GET /api/namespace/{namespace}` 엔드포인트로 해당 namespace의 전체 registry 데이터(모든 route의 path/name/description/parameters 포함)를 JSON으로 반환한다(코드 확인: `ctx.json(namespaces[...])`). 외부 공식 문서 사이트(docs.rsshub.app)와 "RSSHub Radar" 브라우저 확장은 이 API를 소비해서 문서 페이지를 **동적으로 생성**하는 구조로 보인다(이 레포 안에는 docs 사이트 자체는 없음 — 별도 레포로 추정, 미확인).
- **"site가 뭘 의미하는가"**: `routes/<site>/`의 `site`는 RSS 피드로 변환하고 싶은 **하나의 대상 웹사이트/서비스**를 의미한다(예: `github`, `bilibili`, `weibo`). 그 폴더 안에는:
  - `namespace.ts`: 이 사이트 전체에 대한 메타(이름, URL, 설명) — 사용자 말대로 "공통 정보"에 해당.
  - `<route>.ts` 여러 개: 그 사이트 안에서 가져올 수 있는 **개별 피드 종류** 각각(예: github이면 `activity.ts`, `issue.ts`, `repos.ts`, `star.ts` 등 25개 파일 확인됨) — 각 파일이 "실제 데이터 가져오기 로직 + 공통 포맷(`DataItem`/`Data` 타입, `lib/types.ts`)으로 반환"을 모두 담당한다. 사용자의 이해가 정확하다.

---

## 3. 코드 근거 (Source Evidence)

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| Workers 실행 모델 근거 | `wrangler.toml` | 주석 (CPU time limit) | 요청당 CPU 과금 → 서버리스 함수 모델 |
| Workers 전용 bootstrap | `lib/app.worker.tsx` | `app.use(async (c, next) => {...})` | KV/Browser/Playwright 바인딩 요청마다 주입 |
| Workers 런타임 감지 | `lib/utils/is-worker.ts` | `isWorker` | `'caches' in globalThis && 'WebSocketPair' in globalThis` |
| Node bootstrap(1회 실행) | `lib/app-bootstrap.tsx` | 모듈 최상위 코드 | `new Hono()` + `app.use()` 체인은 import 시 1회 |
| namespace root 수집 | `lib/registry-helpers.ts` | `collectNamespaceRoots()` | `namespace.ts` 있는 디렉터리 = namespace |
| 라우트 등록/매칭 | `lib/registry-helpers.ts` | `registerRssRoutes()`, `sortRoutes()` | basePath 마운트, path 정렬, 지연 import(`routeData.module()`) |
| 플러그인 선언 예시 | `lib/routes/github/activity.ts` | `export const route: Route` | path/handler 자기 선언 |
| 사이트 메타 예시 | `lib/routes/github/namespace.ts` | `export const namespace: Namespace` | name/url/description |
| 문서화 없음 규칙 | `repos/rsshub/AGENTS.md` (레포 자체) | 규칙 #7 | README/radar.ts 별도 생성 금지 |
| 문서 동적 노출 | `lib/api/namespace/one.ts` | `handler`, `ctx.json(namespaces[...])` | `/api/namespace/:namespace`가 전체 registry 데이터 반환 |

---

## 4. 검증 과정 및 실행 결과

- **수행한 작업**: 위 파일 직접 열람. `grep -rn "requirePuppeteer"`(이전 질문에서 수행), `wrangler.toml`/`app.worker.tsx`/`is-worker.ts`/`registry-helpers.ts`/`api/namespace/one.ts` 신규 열람.
- **판단 근거**: 코드에서 직접 확인한 사실(파일 경로/함수명 명시)과, Cloudflare Workers의 V8 isolate 실행 모델 자체는 이 레포 코드만으로 100% 검증되지 않으므로 "추론"으로 구분 표시함.
- Archify 산출물: `url-to-plugin-flow.sequence.json`/`.html` — showcase 품질 검증 9/9 통과, 뷰포트 오버플로우 없음(1440~2048px 확인).

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] Cloudflare Workers의 isolate warm/cold 전환 정책(유휴 시간 임계값 등)은 RSSHub 코드 밖의 플랫폼 사양이라 공식 문서 대조 필요
- [ ] docs.rsshub.app이 실제로 `/api/namespace/*`를 소비하는지, 아니면 빌드 타임에 별도 크롤링하는지는 별도 레포(docs) 확인 필요 — 미확인
- [ ] `registry-dev.ts`(dev 모드 지연 로딩)가 prod의 `assets/build/routes.js` 프리컴파일과 산출물이 정확히 어떻게 다른지 (`scripts/workflow/build-routes.ts`) — 이전 질문에서도 남겨둔 항목, 아직 미조사
