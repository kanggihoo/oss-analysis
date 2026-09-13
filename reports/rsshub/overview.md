# rsshub Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/diygod/rsshub`
- **분석 Commit SHA**: `0a4ecdb02390fb047bb675a1764e1dedbf5cf9bc`
- **분석 일자**: `2026-09-11`
- **작업트리 상태**: `clean`
- **분석 목적**: 학습 + 설계 참고 + 도입 검토 (RSS 생성기 아키텍처/라우팅/캐싱 이해, 본인 프로젝트 적용 패턴 발굴, 실사용 기술 검토 겸용)

---

## 2. 프로젝트 개요

RSSHub는 RSS 피드가 없는 웹사이트를 RSS/Atom/JSON 피드로 변환해주는 오픈소스 라우트 모음 서버다. Hono 기반 서버 위에 `lib/routes/<site>/<route>.ts` 형태의 독립 플러그인 3,964개(사이트 1,902곳)가 등록되어 있으며, 각 라우트는 표준 스키마(`path`, `name`, `maintainers`, `radar`, `features`, `handler`)를 따른다. 요청 흐름은 `lib/index.ts`(서버 기동) → `app-bootstrap.tsx`(미들웨어 체인: logger/trace/access-control/cache/parameter 등) → `registry.ts`(라우트 매칭) → 개별 라우트 `handler`(원본 사이트 fetch → parse → RSS item 반환) → `template` 미들웨어(RSS/Atom/JSON 렌더링) 순이다. prod는 `assets/build/routes.js`로 라우트를 프리컴파일하고, dev는 `registry-dev.ts`가 lazy-load한다. 캐시(memory/redis/Cloudflare KV)와 Node/Cloudflare Workers 등 멀티 런타임 배포를 지원한다.

*(코드 확인: `lib/index.ts`, `lib/app-bootstrap.tsx`, `lib/registry.ts`, `lib/routes/github/activity.ts` 직접 열람, 2026-09-11 기준 commit `0a4ecdb0`)*

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도 및 대표 실행 흐름 다이어그램입니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 요청 경로 중심 주요 컴포넌트와 대표 실행 흐름 (commit `0a4ecdb0` 기준 코드 확인) |
| URL→플러그인 매칭 시퀀스 | [url-to-plugin-flow.sequence.json](./diagrams/url-to-plugin-flow.sequence.json) | [url-to-plugin-flow.html](./diagrams/url-to-plugin-flow.html) | `GET /github/activity/DIYgod` 예시로 본 registry→routes 플러그인 디스패치 (Q2 근거) |

### 그림 읽는 가이드
1. **진입점**: `Client` → `Entrypoint`(index.ts/worker.ts) → `app-bootstrap.tsx`(미들웨어 체인) 순으로 요청이 들어온다.
2. **라우팅과 실행**: `registry.ts`가 namespace/route를 매칭해 `routes/<site>/*.ts`로 넘기면, 해당 라우트 handler가 `Target Website`를 fetch/parse하고 `template` 미들웨어가 RSS/Atom/JSON으로 렌더링해 클라이언트에 응답한다(응답 화살표는 가독성을 위해 생략, HTTP 요청/응답 왕복으로 암묵 표현).
3. **1차 지도라 단순화한 부분**: cache 미들웨어, errors 핸들러, `/api` 메타데이터 엔드포인트는 이번 구조도에 노드로 넣지 않고 카드 설명으로만 남겨뒀다(범위 확대는 다음 질문에서 다이어그램 추가 예정). `routes/<site>/*.ts`도 1,902개 사이트를 모두 나열하지 않고 하나의 대표 노드(github/activity.ts 근거)로 집약했다 — 미확인 영역.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

다이어그램을 탐색하며 도출된 질문과 코드 기반 검증 보고서 링크입니다.

- [Q1: 계층 구조(Entrypoint → app-bootstrap → registry → routes → 데이터 수집)의 역할과 분리 이유](./questions/q1-layered-architecture.md) - *각 계층은 "무엇이 바뀌는 단위인가"로 분리됨(런타임/공통정책/라우팅/사이트별 로직); 브라우저 vs HTTP 수집은 별도 계층이 아니라 routes 계층 내부의 사이트별 선택*
- [Q2: Worker 실행 모델 / bootstrap 개념 / registry-routes 관계 / site 문서화](./questions/q2-worker-model-and-plugin-dispatch.md) - *worker.ts는 Cloudflare의 V8 isolate 기반 서버리스 엣지 함수(요청당 CPU 과금이 증거); app-bootstrap은 프로세스/isolate당 1회만 실행되는 부팅; registry는 URL 첫 세그먼트(namespace)+path 패턴으로 자기 선언된 routes 플러그인을 매칭만 함; site 문서는 README 대신 코드 필드가 `/api/namespace/*`로 동적 노출됨*

---

## 5. 지원 사이트/라우트 카탈로그

`lib/routes/`가 실제로 지원하는 사이트와 URL을 정적 분석(코드 실행 없이 regex 파싱)으로 뽑은 카탈로그. 요약: 사이트 1,906곳·라우트 3,462개, 그중 브라우저(headless) 수집 3.0%(104개), 그중에서도 로그인/쿠키 등 별도 인증정보가 필요한 건 7개뿐 — 나머지는 일반 HTTP fetch로 바로 호출 가능. 사이트 언어 분포(`namespace.ts`의 `lang` 필드 전수 집계): 중국어권(zh-CN/TW/HK) 58.2%, 영어 31.0% — 대학/정부 카테고리는 85~93%가 중국 기관.

- **개요 + 집계 + 한계**: [routes-catalog-overview.md](./routes-catalog-overview.md)
- **라우트 단위 원본 데이터(3,462행)**: [routes-catalog.csv](./routes-catalog.csv)
- **사이트 단위 롤업(1,906행)**: [routes-catalog-by-site.csv](./routes-catalog-by-site.csv)

---

## 6. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/rsshub.md](../../wiki/projects/rsshub.md)
