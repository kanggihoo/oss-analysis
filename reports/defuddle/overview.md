---
sha: "556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5"
created: 2026-10-23
updated: 2026-10-23
---

# defuddle (kepano/defuddle) Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/kepano/defuddle`
- **작업트리 상태**: Clean (새로 clone, `artifacts/defuddle/repo-metadata.txt` 참고)
- **분석 목적**: 학습 / 설계 참고
- **라이선스**: MIT — `LICENSE` (저작권 2025 Steph Ango). 하위 디렉터리(`website/`)에 별도 LICENSE 파일 없음
- **분석 대상 제품**: 루트 npm 패키지 `defuddle`(core/full/node 번들 + CLI), 중첩 프로젝트 `website/`(Cloudflare Worker, 도메인 `defuddle.md`, 별도 `package.json`·`wrangler.toml`)
- **스펙 범위**: 2026-10-23, 지도만(기능 스펙 보류) — 사용자가 이번 세션에서는 스펙 작성을 보류하고 지도까지만 확인. 제외: `defuddle.md 웹 서비스`, `API 키 발급·과금` (이유: 사용자 제외, 라이브러리 본체와 별개인 호스팅 서비스라 범위에서 뺌)

### 이전 기준 대비 달라진 점

이전 캡처(`reports/defuddle/initial-capture.md`, SHA `9db7260`)는 지도 없이 초기 사실만 모은 문서였다. 이번에 레포를 새 HEAD로 다시 clone하고 `overview.md`를 처음으로 작성했다. SHA 간 주요 변경(`git diff --stat 9db7260..556d74e`, 343 files changed):

| 영역 | 변경 |
|---|---|
| 버전 | `0.18.1` → `0.19.5` (+ `Unreleased` 1건), `CHANGELOG.md` 신설 |
| 사이트별 추출기 | `bilibili`, `gmail` 추가 (총 24개 패턴 등록, 이전 캡처 기준 추정 15개) |
| 보안/프로젝트 문서 | `CLAUDE.md` 삭제, `AGENTS.md` 신설(innerHTML 금지·URL sanitize 규칙 등 보안 불변식 명문화) |
| CI | `.github/workflows/ci.yml`, `release.yml` 신설 (이전엔 `.github/` 자체가 없었음) |
| 신규 모듈 | `src/frontmatter.ts`(YAML frontmatter 생성, CLI `--frontmatter` + website 공용) |
| 의존성 | `mathml-to-latex`가 `optionalDependencies` → `dependencies`로 승격 |
| website | URL→Markdown/HTML 변환 API에 Stripe 결제, API 키 발급/충전, Durable Objects 잔액 관리, KV 레이트리밋이 추가됨(이전 캡처는 단순 변환 경로만 기록) |

## 2. 프로젝트 개요

Defuddle은 웹 페이지에서 광고·내비게이션·사이드바 등 잡음을 제거하고 본문만 남기는 콘텐츠 추출 라이브러리다(Mozilla Readability의 대안을 표방). 브라우저/Node.js/CLI 세 가지 실행 환경에서 같은 핵심 파이프라인(`src/defuddle.ts`)을 공유하며, Reddit·YouTube·GitHub·ChatGPT 공유 링크 등 24개 사이트는 전용 추출기로 처리한다. 별도 배포 단위인 `website/`는 이 라이브러리를 Cloudflare Worker API(`defuddle.md`)로 노출하고 과금까지 포함한다.

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 핵심 추출 파이프라인 | `Document` → 본문 후보 탐색(스코어링) → 제거 단계 적용 → 결과(`content`+메타데이터). 콘텐츠가 너무 적으면 단계적으로 옵션을 끄고 최대 4단계 재시도, schema.org 텍스트와 비교해 재추출 | `src/defuddle.ts` `Defuddle.parse()`/`parseAsync()`/`parseInternal()` | 없음 | 핵심 | 미작성 | 코드 확인(파이프라인·재시도 로직) |
| 사이트별 추출기 패밀리 (24종) | URL 패턴이 매칭되면 해당 사이트 전용 로직이 `contentSelector`/`variables`(title·author 등)를 돌려주고, 코어 파이프라인이 그 선택자로 재실행됨. 동기(`canExtract`/`extract`)·비동기(`canExtractAsync`/`extractAsync`, 예: YouTube 자막) 두 계약 | `src/extractor-registry.ts` `ExtractorRegistry.findExtractor/findByPredicate`, `src/extractors/_base.ts` | 핵심 추출 파이프라인 | 핵심(패밀리) | 미작성 | 코드 확인(등록 목록·탐색 로직) |
| HTML 표준화 및 정리 | 각주/콜아웃/수식/코드블록/제목을 표준 마크업으로 통일하고, 선택자·점수·숨김요소·작은이미지·본문패턴 기준으로 비본문 요소 제거 | `src/standardize.ts` `standardizeContent()`, `src/elements/*`, `src/removals/*` | 핵심 추출 파이프라인 | 핵심 | 미작성 | 코드 확인(진입점) / 추론(개별 휴리스틱 전부) |
| 메타데이터 추출 | 메타태그·schema.org·URL에서 title/author/published/site/description/image/language 등을 뽑아 공통 필드로 반환 | `src/metadata.ts` `MetadataExtractor.extract()` | 없음 | 핵심 | 미작성 | 코드 확인(진입점) |
| 마크다운 변환 | 정리된 HTML을 turndown 규칙으로 Markdown으로 변환(각주·콜아웃·수식·코드블록 규칙 포함). core 번들에는 없고 full/node/CLI에서만 동작 | `src/markdown.ts` `toMarkdown()`/`createMarkdownContent()` | 핵심 추출 파이프라인, HTML 표준화 | 핵심 | 미작성 | 코드 확인(진입점) |
| 라이브러리 임베딩 진입점 (browser/full/node) | `new Defuddle(document).parse()`(core, 의존성 없음) / `index.full.ts`(수식 full 변환 포함) / `node.ts`의 `Defuddle(doc, url, opts)`(비동기, 임의의 DOM 구현체 허용) | `src/index.ts`, `src/index.full.ts`, `src/node.ts` | 핵심 추출 파이프라인, 마크다운 변환(full/node) | 핵심 | 미작성 | 코드 확인(진입점) |
| CLI | 로컬 파일·URL·stdin 입력을 받아 `--markdown/--json/--frontmatter/--property/--debug/--lang/--user-agent` 옵션으로 출력. URL 입력 시 기본 UA로 실패하면 bot UA로 재시도 | `src/cli.ts` `createProgram()`/`parseSource()`, `src/fetch.ts` | 라이브러리 임베딩 진입점(node), 마크다운 변환, 프론트매터 빌더 | 핵심 | 미작성 | 코드 확인(진입점) |
| 프론트매터 빌더 | 추출 결과(title/author/site/published/domain/language/description/word_count)로 YAML frontmatter 블록 생성. CLI `--frontmatter`와 website 양쪽이 공유 | `src/frontmatter.ts` `buildFrontmatter()` | 메타데이터 추출 | 핵심 | 미작성 | 코드 확인 |
| defuddle.md 웹 서비스 | URL 경로를 받아 해당 페이지를 fetch → 코어로 파싱 → Markdown(기본)/HTML(`/html/` 접두사) 응답. 정적 페이지(랜딩/문서/플레이그라운드/가격)도 같은 Worker가 서빙, edge 캐시 적용 | `website/src/index.ts` `fetch()`/`handleRequest()`, `website/src/convert.ts` | 핵심 추출 파이프라인, 프론트매터 빌더 | 부속 | 미작성 | 코드 확인(라우팅) |
| API 키 발급·과금 | Stripe Checkout으로 요청 블록(1,000/10,000/100,000건) 구매, API 키는 Durable Object(`ApiKeyBalanceDO`)에 잔액 저장(KV에 미러링), 웹훅 완료 시 `CheckoutFulfillmentDO`가 1회성 지급 처리. 미인증 요청은 IP 기준 월 1,000건 KV 레이트리밋 | `website/src/index.ts` `createCheckoutFlow()`, `ApiKeyBalanceDO`, `CheckoutFulfillmentDO` | defuddle.md 웹 서비스 | 부속 | 미작성 | 코드 확인(로직) / 미확인(Stripe·DO 실제 과금 흐름의 운영 동작) |

**공유 계약**

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 출력 새니타이즈(보안 불변식) | 핵심 추출 파이프라인(폴백 경로 포함), 마크다운 변환, website 응답 전체 | `src/utils/dom.ts` `isDangerousUrl()`/`parseHTML()`/`escapeHtml()`, `src/defuddle.ts` `_stripUnsafeElements()` (1166행에서 무조건 실행) | 미작성 | 코드 확인. `AGENTS.md`(Security 절)가 "innerHTML 금지, href/src의 `javascript:`/`blob:`/non-image `data:` 제거" 등을 명문 규칙으로 선언 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md`(Usage/Response/Bundles/Options/CLI/HTML standardization/Third-party services/Debugging 전 절), `package.json`(exports/bin/scripts/dependencies), `website/package.json`·`website/wrangler.toml`(배포 설정), `src/extractor-registry.ts`(등록된 24개 패턴 전부 코드로 대조), `AGENTS.md`(보안·빌드·런타임 호환성 규칙)
- 문서와 구현의 차이: README의 Options 표에 없는 `removeContentPatterns`(기본 `true`) 옵션이 `src/defuddle.ts` `parseInternal()` 기본값 객체에 존재한다(`removeByContentPattern` 제거 단계를 끄는 스위치). 기능 스펙 작성 시 원본(코드) 기준으로 반영 필요
- 미탐색: 개별 추출기 24개의 내부 로직(각 추출기의 DOM 파싱 세부), `src/elements/*`·`src/removals/*`의 개별 휴리스틱(스코어링 가중치, 선택자 목록), `tests/`의 fixture 기반 기대 동작, website의 각 정적 페이지(`landing.ts`/`docs.ts`/`playground.ts`/`pricing.ts` 등) 콘텐츠. 이들은 승인된 행의 기능 스펙(4장) 단계에서 필요한 만큼만 연다

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 진입점 → 코어 파이프라인 → 처리 단계(추출기 레지스트리/표준화/메타데이터/새니타이즈/fetch) → website(부속) |

### 그림 해설

**읽는 순서**
1. 상단 4개 진입점(core/full/node bundle, CLI)에서 시작
2. 모두 `src/defuddle.ts`(코어)로 모이는지 확인
3. 코어가 호출하는 4개 처리 단계(추출기 레지스트리, 표준화, 메타데이터, 새니타이즈)를 본다
4. full/node/CLI에서만 쓰이는 마크다운 변환, CLI 전용 fetch·프론트매터를 본다
5. 맨 아래 별도 영역(website/)이 코어를 그대로 import해 쓰는 것을 본다

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 진입점 4종 | 번들/런타임별 공개 API 표면. core는 의존성 없이 동기 `parse()`만, full은 수식 변환 추가, node는 임의 DOM 입력 비동기 파싱, CLI는 파일/URL/stdin 처리 | `Document`/HTML 수신 → `DefuddleResponse` 또는 CLI 출력 문자열 반환 | `src/index.ts:1-5`, `src/index.full.ts:11-37`, `src/node.ts:13-46`, `src/cli.ts:156-202` | 코드 확인 |
| Defuddle 코어 | 본문 탐색·재시도·schema.org 교차검증을 포함한 추출 파이프라인의 조정자 | 진입점으로부터 `Document`/옵션 수신 → 추출기 레지스트리·표준화·메타데이터·새니타이즈 호출 → `DefuddleResponse` 반환 | `src/defuddle.ts:38-62`(생성자), `src/defuddle.ts:816-839`(`parseAsync`) | 코드 확인 |
| 추출기 레지스트리 + 사이트별 추출기(24) | URL 패턴으로 사이트 전용 추출기를 찾아 `contentSelector`/`variables`를 받아옴 | 코어로부터 `(document, url, schemaOrgData)` 수신 → 매칭된 추출기 인스턴스 반환 | `src/extractor-registry.ts:243-285`(탐색), `src/extractor-registry.ts:45-236`(등록 목록) | 코드 확인 |
| HTML 표준화 | 각주/콜아웃/수식/코드블록 등을 표준 마크업으로 바꾸고 비본문 요소를 제거 | 코어로부터 본문 엘리먼트 수신 → 정리된 엘리먼트를 코어에 반환(in-place) | `src/standardize.ts:180`(`standardizeContent`) | 코드 확인(진입점) |
| 메타데이터 추출 | 메타태그/schema.org/URL에서 공통 메타데이터 필드 산출 | 코어로부터 `(doc, schemaOrgData, metaTags, url)` 수신 → `DefuddleMetadata` 반환 | `src/metadata.ts:4-9` | 코드 확인(진입점) |
| DOM 새니타이저 | 위험 요소/속성(스크립트, `javascript:`/`data:` URL 등) 제거. 코어의 모든 출력 경로에서 무조건 실행 | 코어·폴백 경로로부터 엘리먼트 수신 → in-place로 위험 요소 제거 | `src/utils/dom.ts:73-124`(`isDangerousUrl`), `src/utils/dom.ts:125-158`(`parseHTML`) | 코드 확인 |
| 마크다운 변환 | turndown 기반으로 정리된 HTML을 Markdown으로 변환(full/node/CLI 전용, core 번들 제외) | full/node 진입점으로부터 `DefuddleResponse` 수신 → `content`를 Markdown으로 치환 | `src/markdown.ts:1014`(`toMarkdown`) | 코드 확인(진입점) |
| URL fetch (CLI 전용) | CLI가 URL을 입력받았을 때 HTML을 가져옴. 기본 UA 실패 시 bot UA로 재시도 | CLI로부터 URL 수신 → 대상 웹페이지에 GET 요청 → HTML 반환 | `src/fetch.ts:1-17` | 코드 확인 |
| 프론트매터 빌더 | 추출 결과로 YAML frontmatter 블록 생성. CLI와 website가 동일 함수 공유 | CLI/website convert API로부터 `DefuddleResponse` 수신 → frontmatter 문자열 반환 | `src/frontmatter.ts:44-67` | 코드 확인 |
| website(부속): 변환 API | 경로의 URL을 fetch → 코어(`src/defuddle.ts`)를 직접 import해 파싱 → Markdown/HTML 응답, edge 캐시 적용 | HTTP 요청 수신 → 대상 페이지 fetch → 코어 호출 → HTTP 응답 | `website/src/convert.ts:22-27`, `website/src/index.ts:621-656` | 코드 확인 |
| website(부속): API 키·과금 | Stripe Checkout 세션 생성, API 키 잔액을 Durable Object에 저장(KV 미러링), 웹훅으로 결제 완료 처리, 미인증 요청은 KV로 IP당 월 1,000건 제한 | 변환 API/퍼블릭 라우트로부터 호출 → Stripe/Durable Object/KV와 통신 → 잔액·세션 상태 반환 | `website/src/index.ts:185-235`(API 키 헬퍼), `website/src/index.ts:658-731`(`ApiKeyBalanceDO`), `website/src/index.ts:785-842`(`CheckoutFulfillmentDO`) | 코드 확인 |
| website(부속): 정적 페이지 | 랜딩/문서/플레이그라운드/가격 페이지 서빙 | HTTP 요청(정적 경로) 수신 → HTML 응답 | `website/src/index.ts:1-16`(페이지 모듈 import), `website/src/index.ts:382-391`(라우팅) | 코드 확인 |

**미확인 영역**
- 그림은 모듈 간 "무엇을 호출하는지"만 보이며, 각 추출기 24개 내부의 사이트별 DOM 파싱 분기는 생략했다(기능 스펙 단계에서 필요한 만큼 전개)
- website의 정적 페이지 콘텐츠(마케팅 문구 등)는 구조만 표시하고 내용은 다루지 않았다
- Stripe 결제·Durable Object 영속성의 실제 운영 동작(동시성, 장애 복구)은 코드 읽기로만 확인했고 실행 검증은 하지 않았다(`미확인`)

자동 검증: archify `finalize` (validate/deliver/check/browser-check) 통과. 교차선 10개에 대한 시각적(perceptual) 재검토는 수행하지 않음 — 자동 검사만 통과한 상태다.

---

## 4. 질문 (Questions)

- [Q1: 지원 사이트 목록, defuddle.md/API 키, Cloudflare Worker, 헤드리스 브라우저 여부](./questions/q1-supported-sites-and-website-service.md) - *24개 등록 중 실제 사이트는 21곳(+패턴 2개+범용 폴백 1개); defuddle.md/API 키는 라이브러리와 별개인 Cloudflare Worker 상용 호스팅 서비스; 헤드리스 브라우저는 안 쓰고 평범한 `fetch()` + `linkedom`(JS 미실행 DOM 파서) 조합*
- [Q2: YouTube 자막은 어떻게 가져오는가](./questions/q2-youtube-transcript-fetch.md) - *처음 fetch한 HTML엔 자막 트랙의 URL 목록만 있고, 실제 자막 텍스트는 그 URL로 추가 요청(+ YouTube 비공식 InnerTube API 확인)을 거쳐야 받는다*
- [Q3: YouTube 자막 언어 지정 방법, "가끔 아랍어" 버그 원인](./questions/q3-youtube-language-priority-and-arabic-bug.md) - *CLI `--lang`으로 지정 가능(최우선 적용); 미지정 시 기본 언어 추측이 실패하면 알파벳순 0번째 트랙(종종 Arabic)이 선택되는 버그(#410)가 있었음. 소스(SHA `556d74e`)엔 수정이 들어갔지만 npm 레지스트리 확인 결과 아직 미배포 — `npx defuddle`는 여전히 버그 있는 `0.19.5`를 받는다*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸. 사용자가 이번 세션엔 보류를 선택해 전부 미작성 — 다음 세션에서 스펙을 쓰려면 `next.md` 3절부터 시작
