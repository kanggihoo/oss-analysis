---
sha: "556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/extractor-registry.ts
  - src/fetch.ts
  - src/utils/linkedom-compat.ts
  - website/src/index.ts
  - website/src/convert.ts
  - website/wrangler.toml
  - package.json
---

# Q1. 지원 사이트 목록, defuddle.md/API 키는 무엇인가, Cloudflare Worker는 왜 나오는가, 헤드리스 브라우저를 쓰는가

## 결론 (요약)

- 등록된 추출기는 24개이지만, 그중 2개는 특정 사이트가 아니라 URL 경로 패턴(마스토돈류 인스턴스, Discourse류 포럼)을 매칭하고, 1개는 "아무 URL에나 매칭되는 범용 폴백"이다. 실질적으로 이름 붙은 사이트는 21곳.
- `defuddle.md`와 API 키는 라이브러리 본체와 무관한 **별개의 상용 호스팅 서비스**다(같은 저장소의 `website/` 서브 프로젝트).
- Cloudflare Worker는 그 호스팅 서비스를 돌리는 배포 플랫폼이다. npm 패키지(`defuddle`)와는 배포 단위가 다르다.
- **틀렸다**: Puppeteer/Playwright 같은 헤드리스 브라우저를 쓰지 않는다. 평범한 HTTP `fetch()`로 HTML 문자열을 받아 `linkedom`(자바스크립트를 실행하지 않는 가벼운 DOM 파서)으로 파싱한다.

---

## 1. 지원 사이트 (24개 등록, 실제로는 21개 사이트 + 패턴 2개 + 범용 폴백 1개)

`src/extractor-registry.ts`의 `ExtractorRegistry.initialize()`(45~236행)에 등록된 순서 그대로다. 등록 순서가 우선순위다 — 위에서부터 URL과 매칭되는 첫 번째 추출기가 쓰인다(`findByPredicate`, 243~285행).

| 순서 | 대상 | 매칭 방식 | 비고 |
|---|---|---|---|
| 1~3 | X(Twitter) | `x.com`, `twitter.com` 도메인 | 추출기 3개가 겹쳐 등록(`XArticleExtractor` → `TwitterExtractor` → `XOembedExtractor` 순으로 시도, 먼저 `canExtract()`가 `true`인 것을 씀) |
| 4 | Gmail | `mail.google.com` | |
| 5 | Reddit | `reddit.com` 계열 서브도메인 | |
| 6 | YouTube | `youtube.com`, `youtu.be` | |
| 7 | Bilibili | `bilibili.com` | |
| 8 | Hacker News | `news.ycombinator.com` | |
| 9 | ChatGPT | `chatgpt.com/c/` 또는 `/share/` 정규식 | |
| 10 | Claude | `claude.ai` | |
| 11 | Grok | `grok.com/chat` 또는 `/share` | |
| 12 | Gemini | `gemini.google.com/app/` | |
| 13 | GitHub | `github.com` | |
| 14 | LinkedIn | `linkedin.com` | |
| 15 | Threads | `threads.net`, `threads.com` | |
| 16 | Bluesky | `bsky.app` | |
| 17 | Medium | `medium.com` 및 서브도메인 | |
| 18 | C2 Wiki | `wiki.c2.com` | |
| 19 | Substack | `substack.com` | |
| 20 | NYTimes | `nytimes.com` | |
| 21 | Wikipedia | `wikipedia.org` | |
| 22 | Mastodon | **정규식 `/\/@[^/]+\/\d+/`** (특정 도메인이 아니라 "/@사용자명/숫자ID" 경로 형태) | 마스토돈 호환 인스턴스는 도메인이 제각각이라 경로 패턴으로 잡는다. **추론**: 마스토돈 공식 사이트 구조 문서로 교차 검증하지 않음 |
| 23 | Discourse | **정규식 `/\/t\/[^/]+\/\d+/`** ("/t/제목/숫자ID" 경로 형태) | Discourse 포럼 소프트웨어를 쓰는 모든 사이트에 적용되는 패턴 |
| 24 | (그 외 전부) | **정규식 `/.*/`** → `BbcodeDataExtractor` | 위 23개 중 아무것도 안 걸리면 무조건 실행되는 폴백. "사이트 지원"이라기보다 범용 bbcode/포럼 데이터 보정용 마지막 단계 |

**검증 수준**: 코드 확인(등록 목록·우선순위). 각 추출기 내부가 실제로 무엇을 뽑아내는지(예: ChatGPT 추출기가 멀티턴 대화를 어떻게 합치는지)는 이번 질문에서 열어보지 않았다 — 필요하면 별도 스펙/질문으로 다룬다.

---

## 2. `defuddle.md`와 API 키는 무엇인가

라이브러리 자체(`npm install defuddle`)와는 **다른 제품**이다. 저장소 안의 `website/` 폴더가 그 제품의 코드다.

- **무엇을 하나**: `https://defuddle.md/<임의의 URL>` 형태로 요청하면, 서버가 그 URL의 페이지를 대신 가져와(`fetch`) defuddle 코어로 파싱한 뒤 Markdown(기본)이나 HTML(`/html/` 접두사)을 돌려준다. 즉 "직접 설치해서 코드로 쓰는 라이브러리"가 아니라 "URL만 던지면 변환 결과를 받는 웹 API"다 (`website/src/index.ts` 516~656행, `website/src/convert.ts` 22~27행).
- **왜 API 키가 있나**: 무료로는 IP 기준 월 1,000건까지만 쓸 수 있고(`MONTHLY_RATE_LIMIT`, `website/src/index.ts` 18행), 그 이상 쓰려면 Stripe로 결제해서 API 키를 사고(1,000/10,000/100,000건 단위 블록, `BLOCKS` 상수, 20~24행), 그 키를 `Authorization: Bearer df_...` 헤더로 보내는 구조다.
- **키 잔액은 어디 저장되나**: Cloudflare의 Durable Object(`ApiKeyBalanceDO`, 658~731행)에 저장하고 KV에도 미러링한다. 결제가 끝났다는 Stripe 웹훅이 오면 `CheckoutFulfillmentDO`(785~842행)가 한 번만 크레딧을 지급한다.

**검증 수준**: 코드 확인(로직 자체). Stripe 결제·동시 요청 상황에서 실제로 장애 없이 동작하는지는 실행해보지 않아 **미확인**이다.

---

## 3. Cloudflare Worker는 왜 갑자기 나오는가

"Cloudflare Worker"는 Cloudflare가 제공하는 서버리스 실행 환경(요청이 올 때마다 전 세계 edge에서 짧게 떠서 처리하고 꺼지는 방식, Node.js 서버를 직접 띄우는 것과 다름)이다. `website/` 폴더가 바로 이 환경에 배포되도록 작성된 코드라서 나온 것이다. 근거:

- `website/wrangler.toml` — `name = "defuddle"`, `main = "src/index.ts"`: Cloudflare의 배포 도구 `wrangler`가 이 파일을 보고 `website/src/index.ts`를 Worker로 배포한다. KV 네임스페이스(`RATE_LIMIT`)와 Durable Object 바인딩(`ApiKeyBalanceDO`, `CheckoutFulfillmentDO`)도 여기서 선언한다.
- `website/package.json`의 `"deploy": "wrangler deploy"` 스크립트.

즉 라이브러리(`defuddle` npm 패키지)와는 완전히 다른 배포 단위다. 라이브러리는 그냥 코드를 import해서 쓰는 것이고, `website/`는 그 코드를 가져다 **Cloudflare에 띄운 별도 서비스**다. 같은 git 저장소에 같이 들어있을 뿐이다. (`overview.md`에서 "부속"이라고 표시한 이유도 이것 — 라이브러리 본체 기능이 아니라서 분리했다.)

---

## 4. 헤드리스 브라우저(Puppeteer/Playwright)를 쓰는가 — **아니다**

질문하신 "puppeteer 같은 걸로 headless 브라우저 방식으로 html 가져와서 필터링한 뒤 .md로 변환"이라는 추측은 **틀렸다**. 근거:

1. **의존성에 없다**: `package.json`, `website/package.json` 어디에도 `puppeteer`/`playwright` 패키지가 없다(`grep -rniE "puppeteer|playwright|headless|chromium" src website package.json`로 전체 검색, 결과 0건).
2. **HTML을 가져오는 방식**: `src/fetch.ts`의 `fetchPage()`(190~230행 부근)는 그냥 표준 `fetch(targetUrl, { headers, redirect: 'follow' })`다. 브라우저를 띄우는 게 아니라 HTTP GET 요청 한 번 보내는 것 — `curl`로 페이지를 받아오는 것과 사실상 같다.
3. **HTML을 파싱하는 방식**: 받아온 HTML 문자열은 `linkedom`(`src/utils/linkedom-compat.ts`)으로 파싱한다. linkedom은 `<script>` 태그의 자바스크립트를 **실행하지 않는**, HTML 문자열을 DOM 트리 객체로만 바꿔주는 가벼운 라이브러리다. 실제 브라우저가 페이지를 렌더링하는 것과는 다르다.
4. **그래서 생기는 한계**: 자바스크립트가 실행돼야 내용이 나타나는 SPA(클라이언트 렌더링 페이지)는 처음 받은 HTML에 본문이 비어 있을 수 있다. 이게 바로 `src/defuddle.ts`의 재시도 로직(단어 수가 적으면 옵션을 바꿔 가며 최대 4번 재시도, `parseAsync()`에서 추출기의 `extractAsync()` — 예: YouTube 자막처럼 **별도 API를 직접 호출**해서 데이터를 가져오는 방식)과, README에 적힌 "third-party services"(X 트윗을 FxTwitter API로 가져오는 것)가 존재하는 이유다. 브라우저로 렌더링해서 우회하는 게 아니라, 애초에 그런 페이지는 렌더링을 포기하고 그 사이트의 별도 API를 호출하도록 사이트별 추출기가 짜여 있다.

**검증 수준**: 코드 확인(의존성 부재, fetch 구현, linkedom 파싱). "왜 헤드리스 브라우저 대신 이 방식을 택했는가"는 README·커밋에 명시적 설명이 없어 **추론**이다 — CLI/Node/Worker 어디서나 가볍게 동작해야 하므로(Cloudflare Worker는 애초에 Chromium을 띄울 수 없는 환경) 그랬을 가능성이 높다.
