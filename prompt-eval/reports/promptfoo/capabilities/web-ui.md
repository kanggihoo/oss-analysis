---
sha: "dfe2d45e6f72be85c866b746e3852de0dd7622c5"
created: 2026-10-22
updated: 2026-10-22
sources:
  - src/commands/view.ts
  - src/util/server.ts
  - src/constants.ts
  - src/server/server.ts
  - src/server/index.ts
  - src/server/errors.ts
  - src/server/middleware/csrfProtection.ts
  - src/server/routes/eval.ts
  - src/server/routes/providers.ts
  - src/server/services/evalJobService.ts
  - src/server/services/promptCacheService.ts
  - src/server/utils/downloadHelpers.ts
  - src/server/AGENTS.md
  - src/types/api/eval.ts
  - src/types/api/server.ts
  - src/types/evalConstants.ts
  - src/contracts/api/common.ts
  - src/types/index.ts
  - src/types/standaloneEval.ts
  - src/database/signal.ts
  - src/models/eval.ts
  - src/models/evalPerformance.ts
  - src/models/evalMutation.ts
  - src/util/database.ts
  - src/util/standaloneEvalCache.ts
  - src/util/eval/evalTableUtils.ts
  - src/util/exportToFile/index.ts
  - src/presentation/evalTableCells.ts
  - src/util/sanitizer.ts
  - src/util/sharing.ts
  - src/providers/registry.ts
  - src/evaluate.ts
  - src/app/src/routes.tsx
  - src/app/src/constants.ts
  - src/app/src/constants/routes.ts
  - src/app/src/utils/api.ts
  - src/app/src/utils/api/downloads.ts
  - src/app/src/pages/eval/components/Eval.tsx
  - src/app/src/pages/eval/components/ResultsView.tsx
  - src/app/src/pages/eval/components/ResultsTable.tsx
  - src/app/src/pages/eval/components/EvalOutputCell.tsx
  - src/app/src/pages/eval/components/EvalOutputPromptDialog.tsx
  - src/app/src/pages/eval-creator/components/RunTestSuiteButton.tsx
  - src/commands/evalSetup.ts
  - src/app/src/pages/eval/components/EvalSelectorDialog.tsx
  - src/app/src/pages/eval/components/FilterModeSelector.tsx
  - src/app/src/pages/eval/components/ResultsCharts.tsx
  - src/app/src/pages/eval/components/DownloadMenu.tsx
  - src/app/src/pages/eval/components/SetScoreDialog.tsx
  - src/app/src/pages/eval/components/store.ts
  - src/app/src/pages/eval/components/hooks.ts
  - src/app/src/pages/eval/components/utils.ts
  - src/app/src/pages/evals/components/EvalsTable.tsx
  - src/app/src/pages/history/page.tsx
  - src/app/src/pages/history/History.tsx
  - SECURITY.md
  - Dockerfile
  - site/docs/usage/web-ui.md
  - site/docs/usage/command-line.md
  - site/docs/usage/self-hosting.md
depends:
  - results-store.md
  - eval-records.md
status: ready
reimplementation: 미실행
---

# 웹 UI·로컬 서버 — `promptfoo view`의 결과 조회·비교 (범위 제한판)

> `promptfoo view [directory]`가 로컬 SQLite의 평가 기록을 Express HTTP + Socket.IO 서버와 React 앱으로 열어, 평가 목록·결과 표(열=프롬프트×provider, 행=테스트)·필터·검색·두 평가 비교·사람 평점·내보내기를 제공하는 방식과, 같은 서버 API를 그대로 재사용하거나 대시보드를 다시 만들 때 필요한 API 계약·보안 경계를 정리한다.

<!--
이 스펙의 범위는 "결과 조회·비교"다. 레드팀 설정·리포트, 모델 감사, eval 생성기(설정 편집), 공유(`share`)·호스팅 연동, React 컴포넌트 내부 구현은 다루지 않는다.
최종 선택(view를 그대로 쓸지 / API만 재사용할지 / 대시보드를 새로 만들지)은 사용자 미정이므로 본문은 원본 동작만 쓴다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. `promptfoo view [directory]`가 `.env`를 읽고, `directory`가 있으면 설정 디렉터리(DB·신호 파일 위치)를 바꾼 뒤 `startServer(port, browserBehavior)`를 부른다. 이 Promise는 서버가 종료될 때까지 끝나지 않는다(R-01, R-02).
2. `startServer`는 DB 마이그레이션을 적용하고, 신호 파일 감시자를 켜고, **host 없이** `listen(port)`한다. 인증은 없고 CORS는 전체 허용이다(R-02~R-04).
3. 브라우저가 `/`로 오면 React 앱이 `/eval`로 보내고, 소켓 `init`으로 받은 "가장 최근 평가" 또는 URL의 `/eval/:evalId`를 `GET /api/eval/:id/table`로 한 페이지(기본 50행) 가져와 결과 표를 그린다(R-10, R-19, R-23).
4. 페이지 이동·필터 모드·검색·구조화 필터를 바꿀 때마다 같은 `/table`을 다시 부른다. 표의 행 선택·페이지네이션·"필터 적용 시 통과율"은 서버가 계산한다(R-10~R-12, R-25).
5. 사용자가 "Compare"로 다른 평가를 고르면 `comparisonEvalIds`가 붙은 `/table`이 같은 `testIdx`의 칸을 옆 열로 붙여 돌려준다(R-13, R-26).
6. 셀의 엄지·점수·코멘트·하이라이트는 `POST /api/eval/:evalId/results/:id/rating`으로 행을 바꾸고 열 `metrics`를 증감한다(R-17, R-27).
7. 다른 프로세스(예: `promptfoo eval`)가 DB를 갱신하고 `evalLastWritten`을 쓰면 서버가 250ms 디바운스 뒤 소켓 `update`를 보내고, 화면이 해당 평가를 다시 읽는다(R-18, R-19).

### 1.2 범위·통합 지점

- 제공: `view` 명령 옵션과 서버 시작·종료, 바인딩·인증·CORS·CSRF 사실, 결과 조회·비교·변경에 쓰이는 API의 입출력, 실시간 갱신 신호, 결과 표·평가 목록·비교·평점 화면이 보여 주는 정보와 사용자 입력의 의미, 서버가 평가 실행도 받는다는 경계(R-20).
- 제외(이유):
  - 레드팀 설정·리포트(`/api/redteam`, `/reports`), 모델 감사(`/api/model-audit`), eval 생성기(`/setup`) 화면, 공유(`/api/results/share*`)·클라우드 연동. 범위 밖이라 일람과 경계 사실만 R-20·1.3에 적는다.
  - `/api/blobs`·`/api/media`·`/api/traces`·`/api/configs`·`/api/user`·`/api/version`·`/api/telemetry`·`/api/providers/*` 본문. 이름과 위험 성격만 R-20에 적는다.
  - React 컴포넌트 내부 구현(상태 관리 라이브러리, 스타일, 필터 폼의 입력 위젯 세부). 관찰되는 의미만 적는다.
  - 레거시 v3 평가(`evals.results.table` 비정규화 저장)의 표 경로. `/table` 라우트는 v4(행이 `eval_results`에 있는 형식) 평가를 전제로 읽었고, 클라이언트는 `version < 4`일 때 평점을 `PATCH /api/eval/:id`로 보낸다는 입구만 R-27에 적는다.
- 외부 의존·선행 계약:
  - 저장 위치·`evalLastWritten`·태그·`/api/history`의 캐시와 `limit`·내보내기 형식·비밀 정제 범위는 [results-store](results-store.md)(R-16, R-17, R-18, R-36~R-39)가 정한다. 레코드(`Eval`, `EvalResult`, `CompletedPrompt.metrics`, 표 행 `EvaluateTableRow`)와 평점의 열 `metrics` 보정은 [eval-records](eval-records.md)(R-23~R-25)가 정한다. 여기서는 복제하지 않고 서버·화면이 그것을 어떻게 소비하는지만 적는다.
  - 브라우저(React 앱 실행)·Node `http` 바인딩 기본 동작·OS 파일 감시(`fs.watch`)는 이 스펙이 실행해 보지 못한 외부 동작이다(1.4 확인 한계).
- 소유 상태·부작용: 서버 프로세스 메모리(평가 job 맵, `/api/prompts` 캐시, `/api/history` LRU, 소켓 연결), 브라우저 `localStorage`(`eval-settings` 표 보기 설정). 데이터의 정본은 DB이고 서버는 읽기와 아래 R-16·R-17·R-20의 쓰기 경로만 가진다.

### 1.3 인터페이스와 데이터 의미

**CLI·환경변수**

| 이름 | 의미 |
|---|---|
| `promptfoo view [directory]` | `directory`는 설정(DB) 디렉터리 경로로 쓰인다(생략 시 기본 설정 디렉터리) |
| `-p, --port <number>` | 기본값 `getDefaultPort()` = 환경변수 `API_PORT` 정수값, 없으면 15500. `Number.parseInt(val, 10)`만 하고 범위·NaN 검증은 없다 |
| `-y, --yes` / `-n, --no` | 브라우저 자동 열기 / 열지 않음. 둘 다 주면 `--yes`가 이긴다. 둘 다 없으면 `Open URL in browser? (y/N)` 프롬프트(기본 아니오) |
| `--env-file, --env-path <path>` | `.env` 경로 |
| `--filter-description <pattern>` | 폐기됨. 값을 주면 경고만 하고 무시한다 |
| (없음) | **host/bind 주소 옵션은 없다.** `eval setup`·`redteam setup`·`redteam init`도 같은 `startServer`를 쓴다 |

**서버가 여는 표면** (`createApp`, 등록 순서대로)

| 표면 | 내용 |
|---|---|
| 미들웨어 | `cors()`(옵션 없음) → `csrfProtection` → `compression` → `express.json`·`urlencoded`(둘 다 한도 100mb) |
| `GET /health` | `{status:'OK', version}` |
| 결과 조회 API | 아래 표. 모두 `/api` 아래 |
| 그 밖의 라우터 | `/api/media`, `/api/blobs`, `/api/providers`, `/api/redteam`, `/api/user`, `/api/configs`, `/api/model-audit`, `/api/traces`, `/api/version`, `/api/telemetry`, `/api/dataset/generate`, `/api/results/share*`, `/api/remote-health` (이 스펙 범위 밖) |
| 정적 파일 | 빌드된 React 앱(`dist/src/app` 등). 확장자 `.js/.mjs/.cjs`는 `application/javascript`로 응답. 알 수 없는 GET은 `index.html`(SPA) |
| Socket.IO | 같은 HTTP 서버, 기본 경로 `/socket.io`, `cors.origin:'*'` |

**결과 조회·비교·변경 API** (`/api` 접두 생략, 오류 본문은 `{error: string}` 형태이고 검증 실패는 400)

| 메서드·경로 | 입력 | 출력(성공) | 규칙 |
|---|---|---|---|
| `GET /results` | query `datasetId?`, `type?`(`eval`\|`redteam`), `includeProviders?`(문자열 `'true'`만 참) | `{data: EvalSummary[]}` — `evalId`, `createdAt`(ms), `description`, `numTests`, `datasetId`, `isRedteam`, `passRate`(%), `label`, `providers[{id,label}]`(`includeProviders`일 때만 채움), `attackSuccessRate?`(`type=redteam`일 때만) | R-06 |
| `GET /results/:id` | 없음 | `{data: ResultsFile}` (평가 전체: 설정·열·**모든 행**·traces). 없으면 404 `Result not found` | R-08 |
| `GET /history` | query `tagName?`, `tagValue?`, `description?` | `{data: StandaloneEval[]}` (평가 × 열 한 행씩) | R-07 |
| `GET /prompts`, `GET /prompts/:sha256hash`, `GET /datasets` | `sha256hash`는 64자리 16진수 | `{data: PromptWithMetadata[]}` / `{data: ...}` | R-09 |
| `GET /eval/:id/table` | query `limit`, `offset`, `filterMode`, `search`, `filter`(반복), `comparisonEvalIds`(반복), `format`(`csv`\|`json`) | `EvalTableDTO`(아래) 또는 파일 | R-10~R-14 |
| `GET /eval/:id/metadata-keys`, `GET /eval/:id/metadata-values` | `comparisonEvalIds`(반복) / `key` | `{keys: string[]}` / `{values: string[]}` | R-15 |
| `PATCH /eval/:id` | `{config?, table?}` | `{message}` | R-16 |
| `PATCH /eval/:id/author` | `{author: email}` | `{message}` | R-16 |
| `POST /eval/:id/copy` | `{description?}` | 201 `{id, distinctTestCount}` | R-16 |
| `DELETE /eval/:id` / `DELETE /eval` | — / body `{ids: string[≥1]}` | `{message}` / 204 | R-16 |
| `POST /eval/:id/results` | 행 배열(`promptIdx`, `testIdx`, `success`, `score` 필수, 나머지 통과) | 204 | R-16 |
| `POST /eval` | v3 `{data:{results,config}}` 또는 v4 `{config, prompts?, results, author?, createdAt?, vars?}` | `{id}` | R-16 |
| `POST /eval/:evalId/results/:id/rating` | 본문 `GradingResult`(`pass`, `score` 필수, 나머지 통과) | 갱신된 행(`id`, `success`, `score` + 나머지) | R-17 |
| `POST /eval/job`, `GET /eval/job/:id`, `POST /eval/replay` | 평가 설정 / — / `{evaluationId, testIndex?, prompt, variables?}` | `{id}` / job 상태 / `{output, error?, response?}` | R-20 |

**`EvalTableDTO`** (`GET /eval/:id/table` 성공 본문; 형식은 `src/types/api/eval.ts`의 `EvalTableResponseSchema` — 최상위 필드만 검증하고 `table` 내부는 `head`(객체)·`body`(배열)만 확인하며 나머지는 통과시킨다)

| 필드 | 타입 | 의미 |
|---|---|---|
| `table.head.prompts` | list&lt;CompletedPrompt&gt; | 열. provider×프롬프트 하나가 한 원소. 각 원소는 열 `metrics`를 가진다(eval-records C-01). 비교 중이면 뒤에 비교 평가의 열이 붙는다(R-13) |
| `table.head.vars` | list&lt;string&gt; | 변수 이름(기본 순서는 설정의 순서). 비교 중이어도 기준 평가의 것만 |
| `table.body` | list&lt;EvaluateTableRow&gt; | 이번 페이지의 행. 행 = `{description?, vars[], test, testIdx, outputs[]}`, `outputs[promptIdx]` = 셀(`EvaluateTableOutput`). 순서는 `testIdx` 오름차순 |
| `totalCount` | int | 이 평가의 서로 다른 `testIdx` 수(필터 무관) |
| `filteredCount` | int | 필터·검색을 적용한 서로 다른 `testIdx` 수(페이지네이션 무관) |
| `filteredMetrics` | list&lt;PromptMetrics&gt; \| null | 필터가 하나라도 있을 때 열별로 **필터 적용 후** 다시 집계한 `metrics`. 필터가 없으면 `null`. 길이가 기준 평가의 열 수와 다르면 `null`로 대체 |
| `config` | object | 평가의 `evals.config`. **`redactAzureBlobSasTokens`만** 적용(R-30) |
| `author` | string \| null | |
| `version` | int | 3 또는 4(eval-records R-23) |
| `id` | string | 평가 id |
| `stats` | EvaluateStats | `successes`/`failures`/`errors`(열 `metrics`의 합), `tokenUsage`, `durationMs?`, `cacheHits?` 등 |

**셀 `EvaluateTableOutput`이 담는 정보**: `id`(행 id), `text`(보이는 출력 문자열, `getTableCellText`: 응답 `output`이 객체면 JSON 문자열, 비었으면 `error`, 검증이 있으면 통과 행은 `output || error`·실패 행은 `output`, 검증이 없고 오류가 있으면 `error`), `prompt`(최종 프롬프트), `provider`(label 우선, 없으면 id, 없으면 `unknown provider`), `pass`, `score`, `namedScores`, `gradingResult`(+`componentResults`, `comment`), `failureReason`, `cost`, `latencyMs`, `tokenUsage`, `metadata`, `testCase`, `response`, 선택 `error`·`audio`·`video`·`images`. (행→표 변환 `convertTestResultsToTableRow`; 레코드 의미는 eval-records R-22·R-23.)

**소켓 이벤트** (서버 → 클라이언트만; 클라이언트가 보내는 이벤트는 없다)

| 이벤트 | 페이로드 | 의미 |
|---|---|---|
| `init` | `{evalId}` \| `null` | 연결 직후 `Eval.latest()`의 id. 평가가 하나도 없으면 `null` |
| `update` | `{evalId}` | 그 평가가 생성·변경됨 |
| `update` | `{deletedEvalIds: string[]}` | 그 평가들이 삭제됨. **빈 배열은 "전부 삭제"** |
| `update` | `{evalId}`(= 가장 최근 평가) 또는 `null` | 평가 id가 정해지지 않은 갱신("최신으로 새로 고침"). 평가가 없으면 `null` |

**화면 라우트**(결과 조회 범위만): `/`→`/eval`; `/eval`(가장 최근 평가를 따라감)·`/eval/:evalId`(고정)·`?evalId=`도 같은 화면; `/evals`(평가 목록); `/history`(열 단위 평면 목록); `/prompts`(`/api/prompts`)·`/datasets`(`/api/datasets`). `/dashboard`는 `/eval`로 간다. `/eval` URL의 query: `search`, `filter`(JSON 배열 문자열), `rowId`, `view=report`, hash로 셀 상세.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `view` 실행 | 1.3 표의 옵션을 받는다. 순서: `setupEnv(envPath)` → `--filter-description`이 있으면 경고 → `directory`가 있으면 `setConfigDirectoryPath` → 브라우저 동작 결정(`--yes`=OPEN, `--no`=SKIP, 그 외 ASK) → `startServer(port, behavior)`. 문서(`command-line.md`)의 옵션 표와 일치. `view`는 이미 실행 중인 서버를 검사하지 않는다(`eval setup`은 `checkServerRunning` 뒤 있으면 브라우저만 연다) | 코드 확인 |
| R-02 | 서버 시작·종료 | `createApp()` → `http.createServer` → Socket.IO 부착 → `runDbMigrations()` → 신호 파일 감시자 → `listen`. 성공하면 로그 `Server running at http://localhost:<port> and monitoring for new evals.`(이 URL은 표기일 뿐 바인딩 주소와 무관)를 찍고 `openBrowser(behavior, port)`: ASK면 프롬프트 후 열기, OPEN이면 바로 열기, SKIP이면 열지 않음. 브라우저 실행 실패는 로그만 남기고 서버는 계속된다. 시작 오류: `EADDRINUSE`는 `Port <n> is already in use. Do you have another Promptfoo instance running?`, 그 밖은 `Failed to start server: ...`이며 `ServerError`로 reject된다. 실행 중 `error` 이벤트는 서버를 닫고 reject. `SIGINT`/`SIGTERM`: 감시자·Socket.IO·HTTP 서버를 닫고(5초 안에 못 닫으면 `ESHUTDOWN` 오류) Promise가 resolve된다. 같은 서버를 `src/server/index.ts`(Docker·`npm run dev:server`)가 `API_PORT`와 `BrowserBehavior.SKIP`으로 시작하며 이미 같은 버전이 떠 있으면 `exitCode=1`로 끝낸다 | 코드 확인 |
| R-03 | 바인딩 | `httpServer.listen(port, callback)` — **host 인자가 없다.** 서버 코드·CLI·환경변수 어디에도 host를 정하는 경로가 없다(`listen(`·`HOST`·`API_HOST` 전수 grep: `src/server/server.ts:560`만이 이 서버의 listen이고, Dockerfile의 `ENV HOST=0.0.0.0`을 읽는 소스 코드는 없다). Node는 host를 생략하면 지정 안 된 주소(IPv6 사용 가능하면 `::`, 아니면 `0.0.0.0`)에 바인딩하므로 **모든 네트워크 인터페이스에서 접속된다**(Node 문서에 근거한 추론, 실행하지 않음). `SECURITY.md`는 같은 네트워크에서 접근될 수 있는 호스트에서는 "기본 바인딩에 의존하지 말고 루프백에 명시 바인딩"하라고 권고하지만 `view`에는 그럴 옵션이 없다 | 코드 확인(host 인자 부재) / 추론(Node 기본 바인딩) |
| R-04 | 인증·CORS·CSRF | **인증·세션·토큰 검사는 어디에도 없다**(`self-hosting.md`도 "No built-in authentication or SSO"). `cors()`는 옵션이 없어 모든 origin에 `Access-Control-Allow-Origin: *`를 준다. Socket.IO도 `origin:'*'`. `csrfProtection`은 `GET/HEAD/OPTIONS`가 아닌 요청에만 적용된다: ① 브라우저가 `Sec-Fetch-Site`를 보냈고 `cross-site`가 아니면 통과; `cross-site`이면 `Origin`과 `Host`의 호스트명이 둘 다 `localhost`·`127.0.0.1`·`[::1]`·`::1`·`local.promptfoo.app`이거나 `Origin`이 환경변수 `PROMPTFOO_CSRF_ALLOWED_ORIGINS`(쉼표 목록)에 있으면 통과, 아니면 403 `Cross-site requests are not allowed`; ② `Sec-Fetch-Site`가 없고 `Origin`이 있으면 호스트명이 `Host`와 같거나 위 허용에 들면 통과, 아니면 403 `Cross-origin requests are not allowed`; ③ 브라우저 헤더가 없는 요청(curl·스크립트)은 통과. 즉 **읽기(GET) 요청과 브라우저 헤더 없는 쓰기 요청은 막히지 않는다**. 이 검사는 "best-effort 하드닝이며 보안 경계가 아니다"라고 `SECURITY.md`가 선언한다 | 코드 확인(`server.ts:119-128`, `csrfProtection.ts`, 정적 읽기) / 브라우저 쪽 실제 차단 동작은 미실행 |
| R-05 | 문서가 선언한 신뢰 경계 | `SECURITY.md`: `promptfoo view`는 "단일 사용자 개발 도구"이며 CLI와 같은 권한으로 "설정을 읽고, 평가를 실행하고, 출력을 쓰고, 설정된 provider를 호출"한다. 이 인터페이스로 들어오는 provider 설정·transform·assertion은 "신뢰된 코드와 데이터"로 취급하고, 신뢰할 수 없는 네트워크·사용자에게 노출하지 말며, 원격 노출 시 네트워크 제한·인증·리버스 프록시를 쓰라고 한다. 서버 코드 규약(`src/server/AGENTS.md`)은 로컬 서버 라우트에 rate limit을 두지 않는다고 명시한다 | 코드 확인(문서 문장 그대로의 요지; 문서의 실행 보장은 아님) |
| R-06 | `GET /api/results` | `getEvalSummaries(datasetId, type, includeProviders)`. `datasetId`는 평가↔데이터셋 연결의 `datasetId` 일치, `type`은 `isRedteam` 참/거짓으로 거른다. **정렬 `createdAt` 내림차순, 같으면 `id` 내림차순. `limit`·페이지네이션이 없어 전체 평가를 돌려준다.** `numTests` = **첫 열**의 `testPassCount+testFailCount+testErrorCount`. `passRate` = (모든 열의 `testPassCount` 합) ÷ (`numTests` × 열 수) × 100로, **오류 행을 분모에 포함**하며 분모가 0이면 0. `label` = `description (evalId)` 또는 `evalId`. `config`는 `includeProviders`일 때만 읽고 그때만 `providers`를 `{id,label}`로 펼친다(문자열·문자열 배열·`{id,...}`·`{'openai:gpt-4': {...}}` 형태 지원). 태그는 응답에 없다. 쿼리 검증 실패는 400 | 코드 확인 |
| R-07 | `GET /api/history` | `tagName`과 `tagValue`가 **둘 다** 있어야 태그 필터가 켜진다(하나만 있으면 무시). `description`은 정확 일치. `getStandaloneEvals`에 위임하며 한도 100·조인 행 기준 LIMIT·`createdAt` 내림차순·2시간 TTL LRU 캐시(변경 시 비움)는 results-store R-16(c)가 정한 그대로다. 각 행 = 평가 id·`description`·`promptId`·`datasetId`·`createdAt`(ms)·`isRedteam`·`pluginPassCount/FailCount`·`uuid`(요청마다 새 UUID) + **열(`CompletedPrompt`)의 필드**(`raw`, `label`, `provider`, `metrics` 등). 응답에 태그 값은 없고 시각·열 점수는 있다. 이 서버 쪽 `getStandaloneEvals`는 고유 평가마다 평가 전체를 다시 읽어 표를 만들므로(`eval_.getTable()`) 무겁다(구현 사실) | 코드 확인 |
| R-08 | `GET /api/results/:id` | `readResult`가 `Eval.findById(id)` → `toResultsFile()`(설정은 `sanitizeConfigForOutput`로 정제, 열·**모든 행**·traces 포함)을 돌려주고 `{data:{...result, config: redactAzureBlobSasTokens(config)}}`로 응답한다. 평가가 없거나 **DB 오류가 나도** 404 `Result not found`다(`readResult`가 오류를 삼키고 `undefined`를 돌려줌). 대형 평가는 한 번에 전부 직렬화하므로 무겁다 | 코드 확인 |
| R-09 | 프롬프트·데이터셋 목록 | `GET /api/prompts`: 최근 100개 평가를 읽어 열의 `sha256(raw)`로 묶은 `PromptWithMetadata[]`(`id`, `prompt`, `recentEvalDate`, `recentEvalId`, `count`, `evals[{id, datasetId, metrics}]`)를 프로세스 캐시로 돌려준다. 새 신호가 올 때마다 캐시를 비운다. `GET /api/prompts/:sha256hash`: `sha256(JSON(config.tests ?? []))`가 같은 평가들의 같은 모양. `GET /api/datasets`: `getTestCases()`(데이터셋 해시별 묶음)에 `redactAzureBlobSasTokens`. 묶는 규칙·한도는 results-store R-13과 같다(`evals[]` 원소에는 시각이 없고 `recentEvalDate`만 있다) | 코드 확인 |
| R-10 | `GET /api/eval/:id/table` 입력·응답 | 평가가 없으면 404 `Eval not found`. query: `limit` 기본 50(양의 정수), `offset` 기본 0, **`format`이 없으면 `limit ≤ 1000`**(초과 시 400 `limit must be less than or equal to 1000`), `filterMode`는 `all`·`failures`·`different`·`highlights`·`errors`·`passes`·`user-rated`(기본 `all`), `search` 기본 `''`, `filter`와 `comparisonEvalIds`는 한 번 또는 반복(문자열 하나면 1개 배열). `format`이 있으면 `limit=무제한, offset=0`으로 덮는다(R-14). 응답은 1.3의 `EvalTableDTO`이고 `config`는 R-30. `EvalTableResponseSchema`를 통과하지 못하면 500 `Failed to render eval table`. 직렬화가 `RangeError`(너무 큼)면 각 셀의 `prompt` 문자열을 **긴 것부터** 비우며(`''`) 이진 탐색으로 필요한 최소 개수만 비워 응답하고, 비울 프롬프트가 없거나 다 비워도 크면 413 `Eval too large to display. Try reducing the page size.` | 코드 확인 |
| R-11 | 행 선택 의미(`filterMode`·`search`·`filter`) | 행은 **`testIdx` 단위**로 선택된다: 조건에 맞는 `eval_results` 행이 하나라도 있는 `testIdx`가 대상이고 `ORDER BY test_idx`로 `OFFSET/LIMIT`을 건 뒤, 그 `testIdx`들의 **모든 열의 행**(조건과 무관하게)을 가져와 한 표 행으로 묶는다. 모드: `errors`=`failure_reason=ERROR`; `failures`=`success=0 AND failure_reason≠ERROR`; `passes`=`success=1`; `highlights`=`gradingResult.comment`가 `!highlight`로 시작; `user-rated`=`gradingResult.componentResults`에 `assertion.type='human'`이 있음; **`all`·`different`는 조건 없음**. `search`는 부분 문자열(`LIKE %q%`)이고 정규식이 아니다. `filter`는 각 항목이 JSON 문자열 `{logicOperator, type, operator, value, field}`이며 형식이 틀린 항목은 경고 후 무시한다. 지원: `metric`(`is_defined`, 옛 `equals`(필드 없이 값=메트릭 이름), `eq/neq/gt/gte/lt/lte` 숫자 비교; `namedScores` 키), `metadata`(`equals/contains/not_contains/exists`), 레드팀 전용 `plugin`·`strategy`·`severity`·`policy`. 조건은 앞에서부터 이어 붙이되 `logicOperator`가 `or`(대소문자 무시)일 때만 OR, 그 밖은 AND이며 **괄호 없이** 연결하므로 SQL 우선순위(AND가 OR보다 먼저)가 적용된다. 모든 값은 바인딩 파라미터다 | 코드 확인(필터 SQL 분기 정적 읽기, 실행 아님) / OR·AND 우선순위 결과는 추론(SQL 일반 규칙) |
| R-12 | 필터와 요약의 일관성 · `different` | (a) `different`는 서버에서 **아무 것도 거르지 않는다**(`all`과 같은 행). 다만 `filterMode≠all`이라 필터 활성으로 취급되어 `filteredMetrics`는 계산된다(조건이 없으므로 전체 행의 재집계). 화면 라벨은 "Different outputs — 출력이 다른 테스트만"이지만 실제로는 보이는 열이 둘 이상일 때 각 셀을 **첫 열 출력과의 텍스트 차이(JSON이면 `diffJson`, 아니면 문장/단어 diff)로 강조**만 한다(R-26). (b) 필터가 있으면 `filteredMetrics`를 `calculateFilteredMetrics`(같은 WHERE로 열별 재집계)로 계산하고, 실패하면 오류만 로그하고 `null`을 준다. (c) **불일치**: `filter`가 없을 때 행 선택은 최적화 경로(`queryTestIndicesOptimized`)를 타는데 이 경로의 `search`는 **`response`만** 검색한다. 반면 `filteredMetrics`와 `filter`가 있을 때의 행 선택은 `buildFilterWhereSql`의 검색 대상 7곳(`response`, 채점 `reason`, `comment`, `namedScores`, 사용자 가시 `metadata`, `testCase.vars`, `testCase.metadata`)을 쓴다. 그래서 필터 없이 검색만 할 때, 단어가 `response` 밖(예: 변수)에만 있으면 행은 0개인데 `filteredMetrics`는 0이 아닐 수 있다 | 코드 확인(정적 추적, 실행 아님) |
| R-13 | 두 평가 비교(서버) | `comparisonEvalIds`가 있으면 기준 평가의 이번 페이지 `testIdx` 목록을 만들고, 각 비교 평가에서 **같은 `testIdx`**의 행을 `filterMode:'all'`로 가져온다(비교 평가에는 `search`·`filter`가 적용되지 않는다). 하나라도 없는 평가 id면 404 `Comparison eval not found`. `mergeComparisonTables`: `head.prompts` = 기준 열들(`label`을 `[<기준 evalId>] <label>`로) + 각 비교 평가의 열들(`[<evalId>] <label>`), `head.vars`는 기준 것만, 각 행은 기준 행 + 같은 `testIdx`의 비교 행들의 `outputs`를 **이어 붙인 배열**(`vars`·`test`는 기준 것). **정렬 키는 `testIdx` 하나뿐**이라 두 평가가 같은 행 목록(같은 `tests`)이어야 의미가 맞는다. 서버는 `datasetId`(같은 `tests`)를 검증하지 않는다. 비교 평가에 그 `testIdx` 행이 없거나 일부 열이 비면 해당 `outputs`가 **패딩 없이 짧아져**(`filter`·`flatMap`) 이후 비교 평가의 셀이 앞 열 위치로 밀릴 수 있다(코드 추적, 실행 아님). 비교는 열을 나란히 보이게 할 뿐 두 평가 사이의 점수 차이·회귀 판정을 계산하지 않는다. `filteredMetrics`는 기준 평가 열에 대해서만 계산된다 | 코드 확인(정적 추적; 밀림은 추론) |
| R-14 | 내보내기(`format`) | `format=csv`: `generateEvalCsv`(CLI `-o x.csv`와 같은 포맷 함수)가 전체 행(무제한)을 `filterMode`·`search`·`filter`·`comparisonEvalIds`를 적용해 CSV로 만든다. 비교 평가가 없으면 404. `format=json`: 같은 선택·비교 병합 뒤 `{head:{prompts,vars}, body}`(= `table`과 같은 모양, 페이지 정보·`filteredMetrics`·`config`는 없음)를 돌려준다. 둘 다 `Content-Disposition: attachment; filename="<id>.csv|json"`, 캐시 금지 헤더. **React 앱의 "Download Results CSV/JSON"은 `?format=`만 붙여 불러 평가 전체를 필터 없이 받는다**(현재 필터·비교가 반영되지 않음). 그 밖의 다운로드(config YAML, 실패 테스트 YAML, DPO JSON, Human Eval YAML, Burp payload)는 클라이언트가 이미 불러온 현재 페이지 `table`에서 파일을 만든다 | 코드 확인 |
| R-15 | `metadata-keys`·`metadata-values` | 평가 id는 3~128자. `keys`: 기준+비교 평가들의 `eval_results.metadata`에서 키를 모아 **정렬한 최대 1000개**(스캔 1만 행 상한), 내부 키 `__promptfoo` 제외. 평가가 없으면 404, 비교 평가가 없으면 400 `Comparison evals not found: ...`. `values`: 한 키(점 표기 중첩 지원)의 고유 값 최대 1000개(공백 제거·빈 값 제외). `__promptfoo` 키는 빈 배열. `values`는 `comparisonEvalIds`를 쓰지 않는다. 오류는 500(`Failed to fetch metadata keys/values`) | 코드 확인 |
| R-16 | 변경 라우트 | `PATCH /eval/:id`: `config`와 `table`을 `updateResult`로 저장(`config`는 저장된 SAS 토큰 복원). **평가가 없어도 `updateResult`가 오류 로그만 남기고 반환하므로 응답은 200 `Eval updated successfully`**다. `PATCH /eval/:id/author`: 없으면 404, 있으면 `author` 저장하고 서버 사용자 이메일이 없으면 이 값으로 설정한다(부작용). `POST /eval/:id/copy`: 없으면 404, 모든 행·연결을 복사해 새 id 반환(201). `DELETE /eval/:id`: 없으면 404 `Evaluation not found`, 있으면 연결 테이블·행·평가를 한 트랜잭션으로 삭제(results-store R-33). `DELETE /eval`(일괄): 존재하지 않는 id는 무시하고 204, 실패 시 500. `POST /eval/:id/results`: 평가가 없으면 404, 행을 그대로 추가(204). `POST /eval`: 클라이언트가 보낸 평가를 새 id로 저장(`Eval.create` 또는 v3 쓰기). 모두 인증 없이 호출되며(R-04) 삭제·저장은 `evalLastWritten`을 갱신해 소켓 `update`를 일으킨다(R-18) | 코드 확인 |
| R-17 | 사람 평점 API·열 `metrics` 증감 | `POST /eval/:evalId/results/:id/rating`: 본문은 `pass`·`score` 필수의 `GradingResult`(`comment`, `componentResults`, `reason` 등 통과). 행이 없거나 `result.evalId≠evalId`면 404 `Result not found`, 평가가 없으면 404 `Eval not found`, 열 `metrics`가 없으면 400 `Prompt metrics not found`, 열이 없으면 500. 행의 `gradingResult`·`success`·`score`를 본문 값으로 바꾸고, 열 `metrics`를 **본문이 오기 전 행 상태와 비교**해 증감한다: 통과 여부가 바뀌면 `testPass/FailCount`를 ±1, `assertPass/FailCount`를 ±1(이미 사람 평점이 있던 행이면 반대편 assert 카운트를 −1), `score`를 점수 차이만큼 더한다(**`score` 보정은 통과 여부가 바뀔 때만**이라 점수만 바꾸면 열 `score`는 그대로다). 통과 여부가 안 바뀌고 **사람 평점 `componentResult`(`assertion.type='human'`)가 없던 행이면 그 행의 현재 `success`에 따라 `assertPassCount` 또는 `assertFailCount`를 +1** 한다. 이어서 행과 평가를 저장하고 갱신된 행을 돌려준다. 증감 후 `testErrorCount`·`failureReason`·`error`는 건드리지 않는다(eval-records R-25). 따라서 코멘트·하이라이트만 바꾸는 저장도(통과 여부 불변·사람 평점 없음) 호출마다 assert 카운트를 하나 올린다(UI 호출 형태는 R-27) | 코드 확인(정적 추적, 실행 아님) |
| R-18 | 서버의 실시간 갱신 | 시작 때 `evalLastWritten`(없으면 만들어 현재 시각을 씀)에 `fs.watch`를 걸고 변경마다 **250ms 디바운스**한 뒤 신호를 읽는다(형식은 results-store R-36). 처리 순서: ① `/api/prompts` 캐시 비움 ② 신호 분류 ③ 삭제·"전부 삭제"·id 없는 갱신이면 평가 카운트 캐시 전체 비움, 아니면 해당 id들만 비움(`/api/history` LRU는 어느 쪽이든 비워짐) ④ 삭제 성분이 있으면 `update {deletedEvalIds}` ⑤ 갱신 id마다 평가가 아직 있으면 `update {evalId}`(없으면 보내지 않음) ⑥ id 없는 갱신이면 `Eval.latest()`로 `update {evalId}` 또는 `null`. 처리 실패는 경고만 하고 서버는 계속된다. 소켓이 새로 연결되면 `init`으로 최신 평가 id를 준다. **신호는 알림일 뿐이고 서버가 평가 내용을 소켓으로 보내지 않는다.** 다른 프로세스가 쓴 변경은 이 신호로만 서버 캐시에 반영된다(신호가 유실되면 `/api/history` 캐시는 최대 2시간 오래된 값일 수 있다는 것은 캐시 TTL에서의 추론) | 코드 확인 / 실행하지 않음 |
| R-19 | 화면의 실시간 갱신 | 로컬 모드(`VITE_IS_HOSTED` 미설정)에서만 소켓을 연다(경로는 `apiBaseUrl`·`VITE_PUBLIC_BASENAME`에서 유도). 이벤트는 **도착 순서대로 직렬 처리**한다. 고정 URL `/eval/:id`은 자기 `evalId`의 갱신에만 다시 읽고(평가 목록도 동시에 새로 고침), 루트 `/eval`은 최신 평가를 따라간다(`init`, id 없는 갱신, 현재/최신 평가의 갱신에 반응). 다시 읽기는 화면 깜박임 없이 현재 필터·검색·`comparisonEvalIds`로 첫 페이지를 다시 요청하고 그동안 `isStreaming`을 켠다. 표시 중인 평가가 삭제되면: 루트는 최신 평가로 이동, 고정 URL은 최신 평가의 URL로 `replace` 이동(남은 평가가 없으면 빈 화면, 목록을 못 받으면 루트로). 평가가 하나도 없으면 빈 상태 화면 | 코드 확인 |
| R-20 | 실행·부작용 API (경계 사실) | 같은 서버가 **평가·provider 호출·코드 실행을 요청받는다.** `POST /api/eval/job`: 본문은 평가 설정(`prompts`는 배열 필수, `providers`·`tests`·`defaultTest`·`evaluateOptions?`·`sourceEvalId?` 등. `basePath`는 본문 값을 무시하고, `sourceEvalId`가 있으면 그 평가의 `basePath`·Azure SAS 토큰을 복원) → 즉시 `{id: uuid}` 반환하고 백그라운드에서 `evaluateWithSource`(`writeLatestResults:true`, `eventSource:'web'`)를 돌린다. 결과는 CLI와 같이 DB에 저장되어(R-18의 신호로 화면에 나타남) `sharing`을 본문이 주지 않으면 `shouldShareResults({})`(클라우드 로그인 상태이고 공유가 꺼져 있지 않으면 **자동 공유**)를 따른다. `GET /api/eval/job/:id`: `{status:'in-progress', progress, total, logs}` \| `{status:'complete', result: EvaluateSummary\|null, evalId, logs}` \| `{status:'error', logs}`, 없으면 404 `Job not found`. job은 **프로세스 메모리 맵**에만 있고(재시작·다른 인스턴스에서 사라짐) 취소 라우트는 없다. 완료 결과 본문은 비 Windows에서 0700 임시 디렉터리의 0600 파일로 스냅샷한다. `POST /api/eval/replay`: 저장된 평가의 provider 하나(`providers[testIndex % 길이]`)에 임의 `prompt`·`variables`를 캐시 없이 한 번 실행해 `{output(문자열화), error?, response?}`를 준다(DB에 저장하지 않음). `POST /api/providers/test`는 요청 본문의 provider 설정으로 `loadApiProvider`를 불러 연결 시험을 한다. provider 레지스트리는 `exec:`·`python:` 같은 스크립트 provider를 포함하므로(`registry.ts:432-434`) 이 입력은 **임의 코드를 실행할 수 있는 입력**이다([script-bridges](script-bridges.md) 참조). `test-request-transform`·`test-response-transform`은 본문의 JS `transformCode`를 `createTransformRequest` 등으로 컴파일해 실행한다(격리 여부는 미확인). 이 입력들은 `SECURITY.md`가 "신뢰된 코드"로 다루며 인증이 없다(R-04, R-05) | 코드 확인(라우트·입력 형태·`writeLatestResults` 분기) / 코드 실행 가능성은 추론(레지스트리 항목에서) / 변환 코드의 격리는 미확인 |
| R-21 | 화면 구성(결과 조회 범위) | 결과 화면(`/eval[/:id]`)은 머리(평가 설명(description) 편집, id·author 칩, 평가 선택기, "Show Charts", 표 설정, 액션 메뉴), 필터 영역, 결과 표로 이루어진다. 액션 메뉴: 이름 편집(`PATCH /eval/:id`), 재실행(생성기로 이동, 범위 밖), **Compare**, 설정(YAML) 보기, **Download**, **Copy**, Share(범위 밖), **Delete**(확인 대화상자; 삭제 뒤 다음 평가로 이동). `Ctrl/⌘+K`는 평가 선택기. `view=report`는 레드팀 리포트(범위 밖). 표시 중인 평가가 레드팀(`config.redteam` 있음)이면 보기·필터가 일부 달라진다(범위 밖) | 코드 확인 |
| R-22 | 평가 목록 화면 | `/evals`와 평가 선택기·비교 선택기는 모두 `EvalsTable`이고 `GET /api/results`(캐시 금지)를 한 번 읽는다. 열: Evaluation(설명 또는 label), ID(기본 숨김), Created, Type(Eval/Red Team; 레드팀 평가가 있을 때만), Pass Rate(≥90 초록, ≥60 주황, 그 미만 빨강), Tests. 기본 정렬 `createdAt` 내림차순, 전역 검색, 열 정렬·열 표시 토글, CSV 내보내기(클라이언트가 현재 행으로 만듦: ID·Created(ISO)·Type·Description·Pass Rate·# Tests). `/evals`는 행 선택 후 일괄 삭제(`DELETE /api/eval`). 목록에는 태그·provider 열이 없다(provider는 응답에 있으나 이 화면이 요청하지 않는다). `/history`는 `GET /api/history`를 **필터 파라미터 없이** 한 번 읽어 **평가×열 한 행씩** 평면 표로 보이며 열은 Eval(링크), Dataset, Provider, Prompt(`[promptId 6자] raw`), Pass Rate %, Pass Count, Fail Count(실패+오류), Raw score이다. 시각 열은 없고 기본 정렬은 `evalId` 내림차순인데, `evalId`는 `eval-<임의 3자>-<ISO 초 단위>`라서 이 문자열 정렬은 **시간순이 아니다**(임의 3자가 앞이므로 추론). 전역 검색, CSV·JSON 내보내기(클라이언트) | 코드 확인 / 정렬 결과는 추론 |
| R-23 | 결과 표의 구조 | 열 그룹 3개: **Variables**(`head.vars`마다 한 열; 변환 후 표시용 변수 `metadata.transformDisplayVars`가 있으면 추가 열), **Outputs**(`head.prompts`마다 한 열 = 프롬프트×provider), 선택적 **Description** 열. 행 = 테스트(`testIdx`). 열 머리: provider 이름, 통과율·통과 건수, 오류 건수 칩(누르면 `errors` 모드), 사용자 정의 메트릭(`metrics.namedScores`) 요약, 프롬프트 라벨(없으면 `display`·`raw`; 길면 줄이고 펼치면 `raw`), 상세 통계(R-24). 셀: 출력 텍스트(기본 250자에서 줄임; 마크다운·JSON 정리 선택), 통과/실패 배지와 점수, 실패(선택적으로 통과) 이유, `namedScores` 알약, 사람 코멘트(`!highlight`는 강조 표시 + 코멘트 본문), 토큰·지연·tok/s·비용 한 줄(`showStats`일 때), 셀 상세(프롬프트·출력·채점·메시지·메타데이터·트레이스 탭), 이미지·오디오·비디오. 열·변수 숨김·너비·글자 수 제한·마크다운·줌 등 보기 설정은 `localStorage`(`eval-settings`)에 저장된다. **표에는 열 정렬이 없고 행 순서는 항상 `testIdx` 오름차순**이다 | 코드 확인 |
| R-24 | 통과율·비용·지연 요약 | 열별 값은 모두 서버가 준 열 `metrics`에서 클라이언트가 계산한다. 통과율 = `testPassCount ÷ (testPassCount+testFailCount) × 100`(소수 둘째 자리, 분모 0이면 0; **오류 행은 분모에서 제외**), 표시 `N.NN% passing (통과/전체 cases)`. 필터가 켜져 있으면 `filteredMetrics`로 같은 식을 한 번 더 계산해 "필터 N% (a/b filtered, c/d total)"을 보인다. 총 비용 = `metrics.cost`(평균 = 비용 ÷ `testPass+testFail`, 툴팁), 평균 지연 = `totalLatencyMs ÷ (testPass+testFail)`, tok/s = `tokenUsage.completion ÷ (totalLatencyMs/1000)`, 요청 수·assert 통과/전체·토큰 사용량도 같은 열에 나온다(세부 항목 표시는 `renderTokenMetrics`; 항목별 규칙은 읽지 않음). 비용·지연은 분자에 오류 행이 들어가고 분모에서는 빠지는 점은 eval-records R-24가 정한 그대로다. 평가 전체의 소요 시간·성공/실패/오류 수는 `stats`로 온다. **목록의 passRate(R-06)와 표 머리의 통과율은 분모가 달라**(전자는 오류 포함·모든 열 합산, 후자는 열별·오류 제외) 같은 평가에서도 값이 다를 수 있다 | 코드 확인 |
| R-25 | 필터·검색·페이지 UI | 페이지 크기 선택지 `10/50/100/500/1000`(`EVAL_TABLE_MAX_PAGE_SIZE` 이하), 필터 결과가 10건 넘으면 기본 50, 아니면 10; 페이지·필터·검색 변경 시 `/table`을 다시 부른다. 표시 모드 선택기는 `all`·`failures`·`passes`·`errors`·`different`(보이는 열이 둘 이상일 때만)·`highlights`·`user-rated`. 검색은 입력 300ms 디바운스 후 `search`로 보내고 URL `?search=`와 동기화. 구조화 필터는 `metric`·`metadata`(레드팀이면 `plugin`·`strategy`·`severity`·`policy` 추가)를 여러 개 추가해 `and`/`or`로 잇고, 값이 채워진 것만 서버로 보내며 URL `?filter=`(JSON)에 직렬화된다. 잘못된 `filter` JSON이면 토스트. 모드·필터·검색을 바꾸면 행 딥링크(`rowId`, hash)가 지워진다. `failures` 모드에서 열이 둘 이상이면 열마다 "Show failures" 체크박스가 있다 | 코드 확인 |
| R-26 | 비교 화면 | Compare 메뉴가 `GET /api/results?datasetId=<현재 평가의 datasetId>`를 읽는 평가 선택 대화상자("Only evals with the same dataset can be compared.")를 연다. 자기 자신을 고르면 아무 것도 안 한다. 고르면 `comparisonEvalIds`에 **추가**(여러 개 가능)하고 비교 모드를 켜 `/table`(와 metadata 조회)을 `comparisonEvalIds`와 함께 다시 부른다. 결과는 R-13의 병합 표이므로 열 머리의 프롬프트 라벨이 `[evalId] label`이고 한 행에서 기준·비교 평가의 셀이 가로로 나란하다(각 열의 통과율·비용·지연은 그 평가의 열 `metrics`). `different` 모드에서는 각 셀이 첫 열(기준 평가 첫 열) 출력과의 diff로 표시된다(문서: 추가 녹색·삭제 빨강). **비교를 해제하는 UI는 없고**, 다른 평가로 이동(`fetchId` 변경)하면 비교 상태가 초기화된다. 비교 모드에서는 평점 저장을 하지 않는다(R-27). 두 평가의 점수 차·회귀 요약을 보여 주는 화면은 없다. 산점도 차트("Compare two prompts head-to-head")는 **같은 평가 안**의 두 열 비교다(R-28) | 코드 확인 / 문서와 구현이 같음 |
| R-27 | 사람 평점·코멘트·하이라이트 UI | 셀 동작: 엄지 위=통과(점수 1), 엄지 아래=실패(점수 0), 같은 엄지를 다시 누르면 사람 평점 해제(`pass=null`), 숫자 점수(0~1; 범위 밖이면 입력 오류), 코멘트 편집, 하이라이트 토글(코멘트 앞에 `!highlight `를 붙이거나 뗌). 사람 평점은 `componentResults`에 `{assertion:{type:'human'}, reason:'Manual result (overrides all other grading results)', pass, score, comment}`를 넣거나 갱신하고 행 전체 `pass`·`score`를 그 값으로 덮는다. 해제하면 그 항목을 지우고 남은 `componentResults`로 `pass`(전부 통과일 때만 참)·`score`(평균)를 다시 계산한다. 클라이언트가 만든 `GradingResult`를 **v4 평가면 `POST …/rating`**, 아니면 `PATCH /eval/:id`(표 전체)로 저장한다. 코멘트·하이라이트만 바꿀 때도 같은 API로 `pass`·`score`는 기존 값을 그대로 담아 보낸다. **비교 모드에서는 화면만 바꾸고 저장하지 않고** "Ratings are not saved in comparison mode" 토스트를 띄운다. 저장 실패는 콘솔 오류만 남고 화면의 낙관적 갱신은 되돌리지 않는다. 사람 평점은 `user-rated` 모드·머리의 "N user-rated" 배지로, 하이라이트는 `highlights` 모드·"N highlighted" 배지로 모아 볼 수 있다. 문서(`web-ui.md`)가 말하는 "평점·코멘트가 export에 포함된다"는 행 `gradingResult`가 export되는 범위에서 성립한다 | 코드 확인(저장 실패 처리는 호출부 `catch`에서 확인) |
| R-28 | 차트·셀 상세·다운로드 | 차트 3개(레드팀 평가가 아니고 표시 가능할 때 기본 표시): **Pass Rate** 막대(평가 전체 열 `metrics` 기준), 점수 분포 히스토그램(점수 종류가 3개 이하이고 메트릭이 둘 이상이면 메트릭 막대로 대체)과 **산점도**(두 열 선택, 행별 점수 비교, 색: 둘째가 높음=초록·첫째가 높음=빨강·같음=회색)는 **지금 불러온 페이지의 행**(`table.body`)에서 만든다. 셀 상세 대화상자 탭: prompt/output, evaluation(채점 결과), messages, metadata, traces. 다운로드 대화상자: 결과 CSV·JSON(R-14), 설정 YAML(`# yaml-language-server` 주석 포함), 실패 테스트만의 설정 YAML(현재 페이지에서 실패 행만), DPO JSON(현재 페이지에서 행마다 통과한 출력=`chosen`, 실패한 출력=`rejected`), Human Eval YAML, Burp payload(레드팀) | 코드 확인 / 차트가 현재 페이지 기준이라는 점은 `table.body` 사용에서 추론 |
| R-29 | 시간순·태그별 모음 기능의 유무 | **UI에는 태그로 거르거나 보여 주는 화면이 없고**, 시간순으로 모으는 화면은 `/evals`(`createdAt` 내림차순 평가 목록; 시각 표시) 하나뿐이다. `/history`는 시각 열이 없고 필터가 없다. **API에는** `GET /api/history?tagName&tagValue&description`(R-07; 태그 한 쌍 정확 일치+설명 정확 일치, 시간 내림차순, 한도 100 행)와 `GET /api/results`(전체, 시간 내림차순, 태그 없음)가 있다. 태그 값 자체를 돌려주는 목록 API는 없고, 평가 하나의 `config.tags`는 `/table`·`/results/:id`의 `config`에서만 읽힌다(results-store R-17). 같은 프롬프트 원문(`GET /api/prompts`)·같은 `tests`(`GET /api/prompts/:hash`)로 모으는 목록은 있으나 최근 100개 평가 한정이다. 두 평가를 비교하는 화면은 **있다**(R-26): 입력은 기준 평가 id(URL)와 비교 평가 id들(UI 선택 → API `comparisonEvalIds`)이고 열·행을 `testIdx`로 맞춘다. provider·모델별로 여러 평가를 모아 시간순으로 보는 화면·API는 없다(results-store R-18 참조) | 코드 확인(서버 라우트 전수·화면 라우트 전수) |
| R-30 | 응답별 설정 정제 | 같은 평가의 설정이 응답마다 다르게 나온다. `GET /eval/:id/table`의 `config`는 DB에 저장된 설정에 **Azure Blob SAS 토큰 정제만** 적용한다(소스 주석: "broader output sanitization ... 적용하지 않음"). 따라서 설정에 리터럴로 쓴 provider `apiKey` 등 results-store R-37이 말한 DB 안의 비밀이 그대로 이 응답과 화면의 "설정 보기"·설정 YAML 다운로드에 나올 수 있다. `GET /results/:id`의 `config`는 `toResultsFile`의 `sanitizeConfigForOutput`(results-store R-38)을 거친다. `/api/prompts`·`/api/history`·`/api/results`는 설정 대부분을 싣지 않는다(`/results`는 `includeProviders`일 때 `providers`의 `id`·`label`만). 행 단위 데이터(셀의 `prompt`·`response`·`testCase`)는 저장 시 정제된 값(results-store R-37)이고 사용자 데이터의 비밀은 걸러지지 않는다 | 코드 확인(정적 읽기, 실제 DB 내용·응답은 실행 확인하지 않음) |

- 불변식: (1) 표의 행은 `testIdx`로만 묶이고 비교 병합도 `testIdx`로만 맞춘다(R-11, R-13). (2) `totalCount`는 필터와 무관, `filteredCount`는 페이지와 무관하며, 열 `metrics`(전체)와 `filteredMetrics`(필터 적용)는 서로 다른 집계다(R-10, R-24). (3) 서버는 평가 내용을 소켓으로 보내지 않고 id만 알린다(R-18). (4) 쓰기 경로(R-16, R-17, R-20)는 항상 신호 파일 갱신을 일으켜 접속한 모든 화면이 다시 읽게 한다. 전제: 신호 파일 감시가 동작할 때.
- 미결정: 없음. 단 R-13의 "비교 행이 비는 경우 셀 위치가 밀린다"는 정적 추적이고(1.6 T-07), 이를 재현하려는 구현은 원본의 이 동작을 따를지 별도로 정해야 한다(적용 메모에서 다룸).
- 확인 한계: 서버·브라우저·테스트를 실행하지 않았다. (a) Node의 host 미지정 `listen` 바인딩(`::`/`0.0.0.0`)은 Node 문서에 근거한 추론이다. (b) `fs.watch`의 플랫폼별 신뢰성(이벤트 중복·누락)은 확인하지 않았다. (c) 브라우저가 실제로 CORS `*` 응답을 다른 origin 페이지에 읽게 하는지(예: Private Network Access 제한)는 확인하지 않았다. (d) `calculateFilteredMetrics`의 SQL 전체와 `ResultsFilters/*` 폼 컴포넌트, DataTable 전역 검색 세부, 레드팀 전용 보기, 원본 테스트 파일은 열지 않았다. (e) 제외 범위(공유·레드팀·모델 감사·eval 생성기·blob/media/traces/configs/user)는 라우트 목록만 대조했다.

### 1.5 필수 코드 참조

라이선스: 루트 MIT(overview 1절). 아래는 위치와 가져올 규칙이고 코드를 옮겨 적지 않았다. 신호 파일 읽기·쓰기(`src/database/signal.ts:72-349`)는 results-store C-20, 평가 요약·행 변환·열 `metrics` 필드는 eval-records C-01·표 변환, `getStandaloneEvals`는 results-store C-08을 쓴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/commands/view.ts:9-56` `viewCommand` | 옵션·기본값·브라우저 동작 결정 | R-01 |
| C-02 | `src/server/server.ts:119-135, 326-366` `createApp` | 미들웨어 순서·라우터 등록 목록·정적 파일·SPA 폴백 | R-02, R-04, 1.3 |
| C-03 | `src/server/server.ts:370-452, 546-576` `startServer` | 소켓 부착, 신호 처리 순서와 이벤트 매핑, `listen(port)`, 종료 처리 | R-02, R-03, R-18 |
| C-04 | `src/server/middleware/csrfProtection.ts:5-115` | 안전 메서드, 로컬 호스트 목록, `Sec-Fetch-Site`·`Origin` 경로 3개와 오류 문구 | R-04 |
| C-05 | `src/server/server.ts:154-229` | `/api/results`, `/api/results/:id`, `/api/prompts`, `/api/history`, `/api/prompts/:hash`, `/api/datasets` 핸들러 | R-06~R-09 |
| C-06 | `src/models/eval.ts:1850-1979` `getEvalSummaries` | 목록 정렬·`passRate`·`numTests`·`providers` 펼치기 | R-06 |
| C-07 | `src/server/routes/eval.ts:304-472` `GET /:id/table` | 파라미터 처리, `format` 분기, 비교 병합 호출, `filteredMetrics` 길이 검사, 응답 필드 | R-10, R-12~R-14 |
| C-08 | `src/server/routes/eval.ts:36-131` `sendEvalTableResponse` | 대형 응답의 프롬프트 비우기·413 | R-10 |
| C-09 | `src/types/api/eval.ts:90-134` | table 쿼리·응답 스키마(제약 포함) | R-10 |
| C-10 | `src/models/eval.ts:147-167, 956-1215` `combineFilterConditions`, `buildFilterWhereSql` | 모드·검색 7곳·구조화 필터 유형×연산자 SQL 규칙, AND/OR 결합 | R-11, R-12 |
| C-11 | `src/models/evalPerformance.ts:95-165` `queryTestIndicesOptimized` | 필터 없을 때 검색이 `response`만 대상 | R-12 |
| C-12 | `src/models/eval.ts:1224-1417` `queryTestIndices`, `getFilteredMetrics`, `getTablePage` | `testIdx` 선택→전체 열 행 묶기, 카운트 | R-10, R-11 |
| C-13 | `src/util/eval/evalTableUtils.ts:558-563, 627-662, 681-741` `evalTableToJson`, `mergeComparisonTables`, `generateEvalCsv` | 비교 병합 규칙과 CSV·JSON 내보내기 | R-13, R-14 |
| C-14 | `src/server/routes/eval.ts:709-804` 평점 라우트 | 검증·404/400 분기·열 `metrics` 증감·저장 | R-17 |
| C-15 | `src/app/src/pages/eval/components/ResultsTable.tsx:830-1020, 1687-1736` | 사람 평점 `componentResult` 구성, 해제 시 재계산, v4/레거시 저장 경로, 비교 모드 저장 차단 | R-17, R-27 |
| C-16 | `src/server/routes/eval.ts:133-233, 587-707` | 평가 job·상태·replay 입출력 | R-20 |
| C-17 | `src/server/services/evalJobService.ts:111-206` `EvalJobService` | job 메모리 맵 상태 전이 | R-20 |
| C-18 | `src/app/src/pages/eval/components/Eval.tsx:171-255, 423-493` | 소켓 이벤트별 재조회·삭제 처리·직렬 처리 | R-19 |
| C-19 | `src/app/src/pages/eval/components/store.ts:587-660` `fetchEvalData` | `/table` 요청 파라미터 구성(페이지·모드·검색·필터·비교) | R-10, R-25, R-26 |
| C-20 | `src/app/src/pages/eval/components/hooks.ts:25-110` | 열별 통과율·건수(전체/필터) 계산 | R-24 |
| C-21 | `src/presentation/evalTableCells.ts:3-29` `getTableCellText` | 셀 텍스트 선택 규칙 | 1.3 |
| C-22 | `SECURITY.md:14-23, 113` | 로컬 인터페이스의 신뢰 경계·CSRF 성격·바인딩 권고 | R-03~R-05 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트 미열람, 실행하지 않음). "대체한 범위"는 없다(모두 정적 추적 기대값).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `promptfoo view -y -n -p 8080` | 포트 8080, `--yes`가 이겨 서버 시작 직후 브라우저 열기 |
| T-02 | R-01 | `promptfoo view --filter-description foo` | 경고 로그 후 무시하고 정상 시작 |
| T-03 | R-02 | 15500이 이미 사용 중 | `Port 15500 is already in use...` 오류로 종료(reject) |
| T-04 | R-04 | `POST /api/eval/job`을 `Sec-Fetch-Site: cross-site`, `Origin: https://evil.example`, `Host: localhost:15500`으로 호출 | 403 `{error:'Cross-site requests are not allowed'}` |
| T-05 | R-04 | 같은 `POST`를 헤더 없이(curl) 호출 | 통과(검증 후 처리). `GET /api/results/:id`는 헤더와 무관하게 통과 |
| T-06 | R-06 | 평가 하나, 열 2개, 열마다 `testPass=2, testFail=1, testError=1` | `numTests=4`, `passRate = 4÷(4×2)×100 = 50`. 같은 열의 표 머리 통과율은 `2÷3 = 66.67%` |
| T-07 | R-07 | `GET /api/history?tagName=skill` (값 없음) | 태그 필터 없이 최근 행 반환(`tagValue`도 줘야 필터) |
| T-08 | R-10 | `GET /api/eval/<id>/table?limit=1001` / `…?limit=5000&format=csv` | 400 `limit must be less than or equal to 1000` / CSV 전체(한도 없음) |
| T-09 | R-11 | 열 2개 평가에서 `filterMode=failures`, 0번 열만 실패한 `testIdx=3` | `body`에 `testIdx=3` 행이 있고 `outputs`에 **두 열 모두** 들어 있다(통과한 열 포함) |
| T-10 | R-12 | `filterMode=different` / 필터 없이 `search=<변수에만 있는 단어>` | 전자는 `all`과 같은 행 집합. 후자는 `filteredCount=0`·`body=[]`인데 `filteredMetrics`는 변수까지 검색한 집계라 0이 아닐 수 있다 |
| T-11 | R-13 | 기준 A(열 2개, `testIdx` 0,1,2)와 `comparisonEvalIds=B`(열 1개) | `head.prompts` 길이 3, 라벨 `[A] …`×2 + `[B] …`; 각 행 `outputs` 길이 3. B가 존재하지 않는 id면 404 `Comparison eval not found` |
| T-12 | R-13 | B에 `testIdx=1` 행이 없음 | A의 `testIdx=1` 행 `outputs` 길이가 2(B 셀 없음, 다른 비교 평가가 있으면 셀 위치가 밀림) |
| T-13 | R-14 | `…/table?format=csv&filterMode=failures&comparisonEvalIds=B` / UI의 "Download Results CSV" | 필터·비교가 반영된 CSV / 필터 없는 전체 CSV |
| T-14 | R-16 | 없는 id로 `PATCH /api/eval/zzz` `{config:{}}` / `DELETE /api/eval/zzz` | 200 `Eval updated successfully` / 404 `Evaluation not found` |
| T-15 | R-17 | 열 `metrics{testPass:2,testFail:1,assertPass:0,assertFail:1}`, 행 `success=false`, 사람 평점 없음. `POST …/rating` `{pass:true,score:1}` | 행 `success=true, score=1`; `testPass=3, testFail=0, assertPass=1`, `assertFail=1` 유지, `score`는 +1 |
| T-16 | R-17 | 같은 행(`success=true`, 사람 평점 없음)에 `{pass:true, score:1, comment:'x'}` | 통과 여부 불변·사람 평점 없음 → `assertPassCount`가 +1 |
| T-17 | R-17 | `evalId`가 맞지 않는 `result id` | 404 `Result not found` |
| T-18 | R-18, R-19 | 다른 프로세스가 평가 E를 새로 저장하고 신호 파일 쓰기. `/eval`(루트)을 연 화면 | 250ms 뒤 `update {evalId:E}`, 화면이 E를 다시 읽어 표시. `/eval/F`에 고정된 화면은 반응하지 않음 |
| T-19 | R-18, R-19 | 평가 E 삭제(`DELETE /api/eval/E`), `/eval/E`에 고정된 화면 | `update {deletedEvalIds:['E']}`, 화면은 가장 최근 평가의 URL로 이동 |
| T-20 | R-20 | `POST /api/eval/job` 본문 `{prompts:['hi {{x}}'], providers:['echo'], tests:[{vars:{x:'a'}}]}` → `GET /api/eval/job/<id>` 반복 | 처음 `in-progress{progress,total,logs}`, 끝나면 `complete{result,evalId}`; `evalId`로 `/api/eval/<evalId>/table` 조회 가능; 서버 재시작 후 같은 job id는 404 |
| T-21 | R-26 | 현재 평가의 `datasetId`=D | 비교 선택기는 `/api/results?datasetId=D`의 평가만 보인다. 자기 id를 고르면 변화 없음 |
| T-22 | R-27 | 비교 모드에서 엄지 위 클릭 | 화면 셀은 통과로 바뀌지만 API 호출 없음, 토스트 "Ratings are not saved in comparison mode" |
| T-23 | R-30 | 설정에 `providers:[{id:'openai:gpt-4', config:{apiKey:'sk-…20자↑'}}]`를 저장한 평가 | `GET /api/eval/<id>/table`의 `config`에는 키가 그대로, `GET /api/results/<id>`의 `config`에는 `[REDACTED]` |

## 2부. 근거

### 2.1 요구사항별 근거 지도

기준은 repo@`dfe2d45e6f72be85c866b746e3852de0dd7622c5`, 경로는 `repos/promptfoo/` 기준이다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01; `src/util/server.ts:32-40, 141-170`; `src/constants.ts:27-29`; `site/docs/usage/command-line.md` `promptfoo view`; `src/commands/evalSetup.ts:20-40`(`checkServerRunning`) | 코드 읽기. 문서 옵션 표와 일치. `eval setup`과의 차이는 evalSetup 파일을 읽어 확인 |
| R-02 | C-03; `src/server/errors.ts:1-45`; `src/server/index.ts:1-35` | 코드 읽기 |
| R-03 | `src/server/server.ts:560`; 전수 grep `\.listen\(`(`src/server/server.ts`, `src/commands/mcp/server.ts`, `src/tracing/otlpReceiver.ts`)·`HOST`·`API_HOST`; `Dockerfile:88`; `SECURITY.md:113` | 부재는 grep으로 확인. Node 기본 바인딩은 Node 문서 지식이며 이 레포 코드로 확인되지 않음(실행 없음). overview 2절의 "호스트 미지정 listen" 보고를 코드로 재확인 |
| R-04 | C-02, C-04; `src/server/server.ts:377-381`; `SECURITY.md:23`; `site/docs/usage/self-hosting.md:43` | 코드 읽기. 브라우저의 실제 동작은 미실행 |
| R-05 | C-22; `src/server/AGENTS.md`(Guidelines 마지막 항목) | 문서 문장을 읽은 것. 문서가 선언한 정책이지 코드가 강제하는 보장이 아님 |
| R-06 | C-05 `server.ts:154-177`; C-06; `src/contracts/api/common.ts:44-48`; `src/types/index.ts:1546-1566` | 코드 읽기 |
| R-07 | C-05 `server.ts:205-218`; `src/types/api/server.ts:52-60`; `src/util/database.ts:487-583`(results-store C-08); `src/util/standaloneEvalCache.ts:10-23`; `src/types/standaloneEval.ts` | 코드 읽기. 한도·캐시는 results-store R-16이 확인한 내용을 따름 |
| R-08 | C-05 `server.ts:179-199`; `src/util/database.ts:169-183`; `src/models/eval.ts:1623-1645`; `src/util/sanitizer.ts:978-1000` | 코드 읽기 |
| R-09 | C-05 `server.ts:201-237`; `src/server/services/promptCacheService.ts:1-34`; `src/util/database.ts:215-275, 336-342`; `src/types/index.ts:370-386` | 코드 읽기. `getTestCases` 본문은 results-store R-13에 의존 |
| R-10 | C-07, C-08, C-09; `src/types/evalConstants.ts` | 코드 읽기 |
| R-11 | C-10, C-12 | 코드 읽기. 필터 SQL은 분기를 읽었고 실행하지 않음. OR/AND 우선순위 결과는 SQL 일반 규칙을 전제로 한 추론 |
| R-12 | C-07(`:421-457`), C-10, C-11; `src/app/src/pages/eval/components/FilterModeSelector.tsx:19-27`; `ResultsTable.tsx:2181`; `EvalOutputCell.tsx:257-275, 556-558`; 전수 grep `'different'`(`src/types/index.ts`, `FilterModeSelector.tsx`, `ResultsTable.tsx`, `FilterModeProvider.tsx` 외 서버 사용처 없음) | 코드 읽기(정적 추적). 문서(`web-ui.md` "Display mode … Different")·툴팁("Show only tests with different outputs")과 구현이 다름: 서버는 거르지 않고 클라이언트는 diff 강조만 함 |
| R-13 | C-07(`:374-409`), C-13; `src/models/eval.ts:1300-1325` | 코드 읽기. 밀림은 `filter`/`flatMap`과 `testIdx` 일치 규칙에서 도출(실행 아님). eval-records의 "`testIdx`는 구성이 바뀌면 달라진다"(1.3)와 results-store R-18(e)가 정렬 키의 한계 근거 |
| R-14 | C-07(`:329-372, 411-418`), C-13; `src/server/utils/downloadHelpers.ts`; `src/app/src/utils/api/downloads.ts:11-13`; `DownloadMenu.tsx:195-262, 365-398` | 코드 읽기 |
| R-15 | `src/server/routes/eval.ts:474-553`; `src/models/eval.ts:233-322`; `src/types/api/eval.ts:12-65` | 코드 읽기 |
| R-16 | `src/server/routes/eval.ts:235-302, 555-585, 806-953`; `src/util/database.ts:185-213, 425-471`; `src/models/evalMutation.ts` | 코드 읽기 |
| R-17 | C-14; eval-records R-25(근거 `eval.ts:709-805`); `src/types/api/eval.ts:261-290`; `src/models/eval.ts:725`(저장 시 신호) | 코드 읽기. 코멘트만 바꾸는 저장의 카운트 증가는 UI가 보내는 본문(C-15)과 C-14 분기를 이어 도출한 정적 추적(실행 아님) |
| R-18 | C-03; `src/models/evalMutation.ts:33-53`; results-store C-20(`signal.ts`) | 코드 읽기. 실제 파일 감시 동작은 미실행 |
| R-19 | C-18; `src/app/src/constants.ts:2` | 코드 읽기. 소켓 경로 유도는 `Eval.tsx:428-458` |
| R-20 | C-16, C-17; `src/evaluate.ts:298-355`; `src/util/sharing.ts:35-64`; `src/server/routes/providers.ts:49-95, 205-254`; `src/providers/registry.ts:432-434`; `src/app/src/pages/eval-creator/components/RunTestSuiteButton.tsx:114-144` | 코드 읽기. 변환 코드 컴파일 함수 `createTransformRequest`의 내부와 provider 스크립트 실행의 격리는 열지 않음. 임의 코드 실행 가능성은 레지스트리 등록(`exec`, `python`)과 라우트의 입력 전달에서 추론 |
| R-21 | `src/app/src/routes.tsx`; `ResultsView.tsx:386-433, 579-612, 654-725, 773-810, 996-1005`; `EvalSelectorKeyboardShortcut.tsx:37`; `Eval.tsx:517-548` | 코드 읽기 |
| R-22 | `src/app/src/pages/evals/components/EvalsTable.tsx:45-95, 148-176, 177-345`; `src/app/src/pages/history/page.tsx`, `History.tsx:24-250`; `src/models/eval.ts:99-101`(`createEvalId`) | 코드 읽기. 정렬 결과는 문자열 정렬로부터의 추론 |
| R-23 | `ResultsTable.tsx:1135-1215, 2017-2230`; `EvalOutputCell.tsx:1265-1470, 1470-1691`; `src/presentation/evalTableCells.ts`; `src/util/exportToFile/index.ts:8-71`; `store.ts:395-500` | 코드 읽기 |
| R-24 | C-20; `ResultsTable.tsx:621-810, 1030-1075, 1135-1160`; eval-records R-24 | 코드 읽기 |
| R-25 | C-19; `ResultsTable.tsx:86-87, 1658-1680, 1930-1990`; `ResultsView.tsx:288-345`; `FilterModeSelector.tsx`; `Eval.tsx:304-418`; `store.ts:219-259, 590-660` | 코드 읽기. 필터 폼 위젯 세부는 읽지 않음 |
| R-26 | `ResultsView.tsx:425-433, 996-1005`; `EvalSelectorDialog.tsx`; `EvalsTable.tsx:40-105`; `store.ts:417-418, 599-636`; `Eval.tsx:405-407`; C-13; `web-ui.md` Eval Actions "Compare" | 코드 읽기. "해제 UI 없음"은 `setComparisonEvalIds` 전수 grep(Eval.tsx 초기화와 ResultsView 추가 두 곳뿐)으로 확인. 문서("green = added, red = removed")는 diff 강조 구현과 같은 방향 |
| R-27 | C-15; `EvalOutputCell.tsx:1315-1460`; `SetScoreDialog.tsx:26-35`; `hooks`/`utils.ts:160-181`; `web-ui.md` Cell Actions | 코드 읽기 |
| R-28 | `ResultsCharts.tsx:84-110, 186-200, 221-320, 500-541`; `EvalOutputPromptDialog.tsx:385-430`; `DownloadMenu.tsx:117-262` | 코드 읽기 |
| R-29 | 서버 라우트 전수(`server.ts`, `routes/*.ts`의 `Router.get/post/...` 목록)와 `routes.tsx` 화면 전수; results-store R-16·R-17·R-18; `EvalsTable.tsx`, `History.tsx` 열 정의 | 부재는 라우트·화면 목록 전수로 확인(코드 확인). 필터 폼이 태그 항목을 가진다는 증거는 없음(`ResultsFilterType`에 태그 없음, `store.ts:219-225`) |
| R-30 | `src/server/routes/eval.ts:456-466`(`config: redactAzureBlobSasTokens(eval_.config)`); `src/util/sanitizer.ts:978-981`(주석); results-store R-37·R-38 | 코드 읽기. 실제 응답 내용은 실행 확인하지 않음 |
| T-01~T-23 | 위 R-ID의 근거에서 도출 | 모두 정적 도출. 원본 테스트·실행 미사용 |

### 2.2 코드 읽는 순서

1. `src/commands/view.ts` → `src/server/server.ts`(`createApp`, `startServer`) → `src/server/middleware/csrfProtection.ts`.
2. `src/server/routes/eval.ts`(table·평점·job) → `src/models/eval.ts`(`getTablePage`, `buildFilterWhereSql`, `getEvalSummaries`) → `src/util/eval/evalTableUtils.ts`(비교·CSV).
3. 갱신 경로: `src/models/evalMutation.ts` → `src/database/signal.ts` → `server.ts:385-452` → `Eval.tsx:171-255`.
4. 화면: `src/app/src/routes.tsx` → `pages/eval/components/{Eval,ResultsView,ResultsTable,EvalOutputCell,store,hooks}` → `pages/evals`, `pages/history`.

### 2.3 비교·재사용 출처

다른 레포의 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다. 문서(`site/docs/usage/web-ui.md`)와 구현의 차이는 R-12(`different` 모드), R-26(Compare), 검색이 정규식이라는 문서 설명(`Search - Text or regex`)과 구현의 `LIKE` 부분 일치(R-11)에 있다.

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-03, R-04, R-05 | `view`를 그대로 쓰면 host 지정 옵션이 없고 인증도 없다. 안전하게 쓰려면 ① 컨테이너·방화벽·SSH 터널·리버스 프록시로 루프백 밖 접근을 막거나 ② `startServer`를 쓰지 말고 읽기 전용 라우트만 가진 얇은 서버를 `127.0.0.1`에 바인딩해 만든다 | 원본은 host를 정할 수 없고(`startServer(port, behavior)`가 서명 전부), 같은 서버가 평가·provider·변환 코드 실행 라우트를 함께 연다 | 새 서버는 `/api/results`, `/api/results/:id`, `/api/history`, `/api/eval/:id/table`(읽기)만 노출. T-04·T-05를 "비 loopback 접속 거부", "쓰기 라우트 없음" 사례로 대체 |
| R-20 | 대시보드만 쓸 때는 `/api/eval/job`·`/replay`·`/providers/*`·`/redteam/*`·`/model-audit/*`·`POST /api/eval*`를 노출하지 않는다 | 이 라우트들이 신뢰된 설정 가정 아래 임의 코드를 돌릴 수 있다(R-05) | 평가 실행은 CLI(`promptfoo eval`)로만 하고 서버는 DB 읽기 + 신호만 사용 |
| R-07, R-29 | "스킬·모델 적합도를 시간순·태그별로 보기"는 원본 API로 부족하다: 태그 값이 목록 응답에 없고 provider·스킬 버전 필터가 없고 `/api/history`는 태그 한 쌍·100행 한도다 | R-07, R-29와 results-store R-18 | 대시보드는 평가 시 `--tag k=v`로 넣은 라벨(스킬·버전·모델)을 DB에서 직접 읽는 자체 조회를 둔다(results-store 적용 메모와 같은 방향). `GET /api/eval/:id/table`의 `config`에서 태그를 읽는 방법도 있으나 R-30의 비밀 노출 때문에 권장하지 않는다 |
| R-13, R-26 | 두 평가 비교를 `testIdx` 위치 대신 케이스 안정 id로 맞추고, 비교 평가에 행이 없으면 빈 칸으로 패딩하며, 두 평가의 통과율·비용·지연 차이와 회귀(통과→실패) 케이스 목록을 계산해 보여 준다 | 원본 비교는 같은 `testIdx`끼리 열만 나란히 놓고 차이를 계산하지 않으며 행이 비면 셀 위치가 밀릴 수 있다(R-13) | 입력은 (기준 평가 id, 비교 평가 id)와 케이스 키. T-11~T-12를 패딩·키 정렬 사례로 대체 |
| R-17, R-27 | 사람 평점·코멘트는 `evals`/행을 직접 고치지 않고 별도 레이블 저장소에 쓰고, 열 `metrics`는 읽을 때 행에서 다시 집계한다 | 원본은 열 `metrics`를 증감하는 방식이라 코멘트 저장마다 assert 카운트가 오르고 오류 행 처리가 어긋난다(R-17, eval-records R-25) | 같은 행에 여러 번 저장해도 집계가 바뀌지 않는 사례(T-16 대체) |
| R-24, R-06 | 목록과 표 머리의 통과율 분모를 하나로 정한다(예: 오류 행 제외 또는 포함을 명시) | 원본은 두 화면의 분모가 달라 같은 평가에서 값이 다르다 | T-06 대체 |
| R-10, R-14 | 내보내기에서 "현재 필터·비교 반영"을 UI에서도 지원하거나 반영 여부를 표시한다 | 원본 UI 다운로드는 필터·비교를 반영하지 않지만 API는 반영한다 | T-13 대체 |
