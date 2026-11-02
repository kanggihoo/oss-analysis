---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/bin/archify.mjs
  - archify/bin/preview.mjs
  - archify/bin/open-artifact.mjs
  - archify/bin/recover-output.mjs
  - archify/bin/delivery-update.mjs
  - archify/bin/finalize.mjs
  - archify/delta/architecture-delta.mjs
  - archify/migrations/workflow-v2.mjs
  - archify/renderers/workflow/workflow-migration-geometry.mjs
  - archify/renderers/shared/brand-marks.mjs
  - archify/scripts/check-update.mjs
  - archify/scripts/update-contract.mjs
  - archify/references/update-awareness.md
  - archify/references/delivery-contract.md
  - archify/references/brand-marks.md
  - README.md
depends: []
status: draft            # compare·migrate·preview는 깊이 조사했으나, brands capture·update 확인·recover·examples는 요청에 따라 인터페이스 수준만 확인해 내부가 미결정
---

# 보조 명령 (compare architecture · migrate · preview · brands · doctor · demo · examples, update 확인, recover)

> 트리거→전달 흐름 밖에서 쓰는 CLI 명령(`archify.mjs`의 하위 명령 7개)과 흐름 주변 스크립트 2개(`check-update.mjs`, `recover-output.mjs`)가 각각 어떤 인자를 받아 무엇을 쓰고 어떤 코드로 끝나는지.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 진입점 `archify.mjs`는 첫 인자를 명령 이름으로 보고 `switch`로 분기한다. 이름이 없거나 `help`/`-h`/`--help`면 사용법, 알 수 없는 이름이면 사용법과 함께 종료 코드 2다. `<명령> --help` 한 가지 형태만 명령별 파싱을 건너뛰고 전체 사용법을 출력한다(R-01).
2. 깊이 조사한 세 명령의 대표 흐름:
   - `compare architecture base.json head.json out.html`: 양쪽을 읽고 검증·렌더한 뒤(각각 정식 렌더+정적 검사) 구성요소·연결·경계를 안정 id로 대조해 Before/Delta/After HTML과 영수증 JSON을 한 쌍으로 쓴다(R-02~R-07).
   - `migrate workflow old.json new.json --to-schema 2`: v1 워크플로를 v2 스키마로 바꾸되 x 좌표 고정 지정을 새 열 중심으로 옮기고, 스테이징에서 렌더·검사까지 통과해야 대상 파일을 교체한다(R-08~R-11).
   - `preview <type> in.json [out.html]`: 루프백 서버를 띄워 입력 파일을 감시하고, 안정된 저장본마다 `deliver`를 돌려 통과한 것만 화면과 출력 파일에 올린다(R-12~R-15).
3. 나머지는 인터페이스 수준: `brands`(내장 브랜드 카탈로그 조회 / URL 아이콘 캡처), `doctor`(설치 자체 점검), `demo`(샘플 렌더), `examples`(예제 일괄 재렌더), 흐름 주변의 `update` 확인과 `recover`(R-16~R-22).

### 1.2 범위·통합 지점 [필수]
- 제공: 위 명령의 인자·출력·종료 코드·부작용. compare·migrate·preview는 입력 검증과 변환·비교 규칙, 실패 시 출력 보존까지.
- 제외:
  - `guide` 명령(type-routing 소관), `render`·`validate`·`deliver`·`patch`·`finalize`·`check`·`browser-check`·`visual-check`·`inspect`(전달 흐름 소관).
  - `compare`가 호출하는 정식 렌더·검사(검증 파이프라인)와 delta HTML을 열었을 때 보이는 UI(delta 페이지 안의 Review 재생 등)의 내부. 여기서는 만드는 쪽의 입출력만 다룬다.
  - 인터페이스 수준만 확인한 것의 내부 알고리즘(요청 범위): `brands capture`의 아이콘 탐색·네트워크 방어, `update` 확인의 캐시·잠금·백오프 상태 기계, `recover` 복구 절차, `examples`의 예제 목록. 이 내부 때문에 status가 draft다(1.4 미결정).
- 외부 의존·선행 계약: Node.js ≥18(`doctor`가 점검). `compare`·`migrate`는 정식 렌더러와 `check-render-output`을 자식 프로세스로 실행하며, `preview`는 `archify.mjs deliver`를 자식 프로세스로 실행하고 이 명령의 `--json` 영수증(`ok`, `artifact.sha256/bytes`, `validation.*`, `diagnostics[]`)을 읽는다. 출력 경로 해석(`resolveOutputPath`)·원자적 교체(`atomic-output`)는 전달 흐름 쪽 공유 모듈이며 여기서는 호출 규칙만 쓴다.
- 소유 상태·부작용: compare는 HTML과 영수증 JSON(쌍), migrate는 대상 JSON 하나, preview는 출력 HTML 하나와 출력 폴더 안의 `.archify-preview-*` 스테이징 폴더(종료 때 제거)와 로컬 서버·감시자, demo는 `archify-demo.html` 하나. brands 조회·doctor는 읽기 전용이다. `examples`는 설치 폴더 안의 `examples/`를 다시 쓴다(R-20).

### 1.3 인터페이스와 데이터 의미 [필수]

**명령 요약** (사용법 문자열 원문은 C-01)

| 명령 | 입력 | 출력 | 종료 코드 | 부작용 |
|---|---|---|---|---|
| `compare architecture <base.json> <head.json> [output.html] [--receipt path] [--json] [--quality standard\|showcase] [--repo-root path]` | 아키텍처 JSON 2개(둘 다 `schema_version` 1, `diagram_type` `architecture`) | stdout 3줄(`compared architecture <html>` / `<통과>/<전체> checks; completeness complete; <proofLevel>; sha256 <12자>` / `receipt <path>`) 또는 `--json`이면 영수증 JSON | 0 성공, 1 단계 실패(보고 후), 2 사용법·알 수 없는 옵션 | HTML+영수증 한 쌍 기록(기본 `architecture-delta.html`, `architecture-delta.receipt.json`). 실패하면 기존 파일 유지 |
| `migrate workflow <old.json> <new.json> --to-schema 2 [--output portable.html] [--json] [--repo-root path]` | 워크플로 JSON(v1 또는 v2) | stdout 한 줄 `migrated workflow schema v1→v2: <src> → <dst>`(v2 입력이면 `verified workflow schema v2 migration: …`) 또는 `--json` 보고서 | 0 성공, 1 실패(보고 후), 2 사용법 | 대상 JSON 하나 기록(2칸 들여쓰기+개행). 소스는 쓰지 않음. 실패하면 대상 유지 |
| `preview <type> <input.json> [output.html] [--no-open] [--quality standard\|showcase] [--repo-root path]` | 다이어그램 JSON(타입 10종, `explainer` 제외) | stdout 3줄(`preview <url>`, `watching <input>`, `output <output>`), 이후 서버가 상태를 SSE로 내보냄 | 2 사용법·알 수 없는 옵션·explainer·미지원 타입, 1 시작 실패, 종료 신호 후에는 0(코드상 정상 반환, 실행하지 않음) | 루프백 서버, 파일 감시, 출력 HTML 갱신, 스테이징 폴더 |
| `brands [name\|alias\|domain\|category] [--json]` | 질의(여러 단어는 공백으로 이음, 없으면 전체) | 텍스트(`category: id, id, …` 줄들) 또는 JSON | 0, 알 수 없는 `--옵션` 2 | 없음(읽기 전용) |
| `brands capture <url> [--json]` | HTTP(S) URL 하나 | 텍스트는 `brand` 값 JSON 한 줄, `--json`은 `{schemaVersion, ok, command, brand, evidence}` | 0, 인자·URL 형식 오류·캡처 실패 2 | **네트워크 접근**(대상 사이트) |
| `doctor` | 없음 | `[ok] …` 줄들과 마지막 `Archify is ready.` | 0 정상, 1 문제 있음 | 없음(읽기 전용). 추가 인자·옵션은 2 |
| `demo [output-directory]` | 출력 폴더(기본 현재 폴더) | `archify-demo.html`과 안내 문구 | 0, 인자 2개 이상·옵션 2, 폴더 생성 실패 1, 렌더 실패는 렌더러의 종료 코드 | 폴더 생성, HTML 하나 |
| `examples` | 없음 | 예제 일괄 렌더 스크립트의 출력 | 0, 추가 인자·옵션 2, 스크립트 실패 시 그 코드 | 설치 폴더 `examples/` 덮어쓰기 |
| `node scripts/check-update.mjs [--snooze <eventKey>\|--ignore <eventKey>\|--ack <x>]` | 없음 또는 위 | 한 줄 JSON(`{"status":…}`) | 항상 0(오류는 `silent`로 표현) | **네트워크 접근**(기본), 캐시·선호 파일 |
| `node bin/recover-output.mjs <private-recovery-directory> [--json]` | `.archify-remove-<id>` 폴더 | `<status>: <reason>` 또는 JSON 한 줄 | 0 `recovered`/`absent`, 2 `preserved`, 1 그 밖, 64 사용법 | 은퇴한 게시물을 다시 보이게 복구 |

공통 규칙: 인자 오류는 `fail()`이 stderr에 쓰고 종료 코드 2다(compare·migrate·preview의 사용법 오류 포함). 각 명령 자신의 단계 실패는 `process.exitCode = 1`로 끝난다. `--quality`·`--repo-root`는 모든 명령 앞단에서 먼저 떼어내므로 위치는 자유다.

**compare 입력·출력 계약**

| 항목 | 값·의미 |
|---|---|
| 위치 인자 | 정확히 `architecture`, 베이스, 헤드, 선택 출력. 3~4개가 아니면 사용법(2) |
| 출력 HTML | 기본 `architecture-delta.html`. 확장자는 `.html`이어야 하며 아니면 `output/cli-extension`(1). 입력과 같은 경로이면 `output/input-alias`(1) |
| 영수증 | 기본은 출력 이름에서 만든 `<stem>.receipt.json`(HTML 옆, 이름 길이는 사이드카 규칙으로 제한). `--receipt`는 `.json`이고 HTML과 같은 디렉터리여야 하며 아니면 `delta/receipt-directory`(1) |
| 영수증 필드 | `schemaVersion`(1), `ok`, `command`, `type`, `comparatorVersion`(1), `canonicalVersion`(1), `completeness`(`complete`), `proofLevel`(`authored`\|`revision-pinned`), `base`/`head`(`title`, `rawSha256`, `semanticSha256`, `bytes`, 있으면 `revision`), `summary`, `changes`, 있으면 `provenance`, `identity`, `view.visualPreset`(헤드의 `meta.visual_preset` 또는 `classic`), `limitations[]`, `artifact`(`sha256`, `bytes`), `validation`(`checksPassed`, `checkCount`, `baseComposition`, `headComposition`) |
| `summary` | `components`{added, changed, evidenceChanged, removed, moved}, `connections`{added, changed, removed, rerouted}, `boundaries`{added, changed, removed, geometryChanged}, `presentationChanged`(bool), `provenanceChanged`(bool) |
| `changes.*[]` | 컴포넌트·연결은 `id`, 경계는 `key`(`kind:label`); `status`; `classifications[]`; `changedFields[]`(JSON 포인터 `/필드`, 정렬) |
| 실패 보고 | 텍스트는 stderr, `--json`은 stdout에 `{schemaVersion:1, ok:false, command:'compare', type:'architecture', stage, error, diagnostics:[{code, severity:'error', message, subject, evidence, supportedFixes}]}`. 종료 코드 1 |
| 실패 단계(`stage`) | `prepare`(경로·디렉터리·스테이징), `input`(읽기·검증·렌더), `compare`(비교 불가), `artifact`, `commit`, `internal` |

**migrate 입력·출력 계약**

| 항목 | 값·의미 |
|---|---|
| 위치 인자 | 정확히 `workflow`, 소스, 대상. `--to-schema`는 문자열 `2`만 허용(`--to-schema=2`도 가능). 그 밖이면 사용법(2) |
| `--output <path>` | 마이그레이션 후보의 `meta.output`만 이 값으로 교체(소스는 쓰지 않음). 값은 이식 가능한 `.html` 경로여야 함. 소스의 `meta.output`이 없거나 잘못된 문서를 고치는 유일한 경로 |
| 품질 | 별도 `--quality` 없음. 소스의 `meta.quality_profile`(없으면 `standard`)을 모든 단계에 고정 |
| 보고서(`--json`) | `{ok, command:'migrate', type:'workflow', source{path,sha256,bytes}, destination{path,sha256,bytes}, fromSchemaVersion, toSchemaVersion:2, preExistingDiagnostics[], migrationDiagnostics[], newSchemaDiagnostics[], changedCoordinates[{path,from,to}], oldRequiredViewBox, newRequiredViewBox}`. 성공이면 stdout, 실패면 `--json`일 때 stdout, 아니면 진단을 stderr에 |
| 진단 구분 | `preExistingDiagnostics`: 소스 자체의 문제(스키마·옛 레이아웃). `migrationDiagnostics`: 마이그레이션 단계 문제(`migration/*`). `newSchemaDiagnostics`: v2로 바꾼 결과의 문제 |

**preview 서버 계약**

| 항목 | 값·의미 |
|---|---|
| 바인딩 | `127.0.0.1`, 임의 포트. `Host` 헤더가 `127.0.0.1:<포트>`가 아니면 403 `Forbidden host` |
| 메서드 | `GET`·`HEAD`만. 그 외 405(`Allow: GET, HEAD`) |
| 경로 | `/` 셸 페이지(CSP `default-src 'none'; frame-src 'self'; connect-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'`), `/state` 상태 JSON, `/artifact.html` 검증된 최신 산출물(첫 검증 전 404 `No verified artifact yet`), `/events` SSE(`retry: 1000` 후 `event: state`), 그 밖 404. 모든 응답 `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` |
| 상태 객체 | `{schemaVersion:1, status:'checking'\|'verified'\|'needs-fix', generation, revision, lastVerified:{sha256, bytes, checksPassed, checkCount, compositionProfile, compositionStatus}\|null, failure:{stage, code?, evidence?, message}\|null}` |
| 타이밍 기본값 | 디바운스 400ms, 폴링 800ms, 종료 유예 3000ms, 강제 종료 대기 750ms |
| 셸 페이지 | iframe이 `/artifact.html?revision=<n>&sha=<sha256 앞 12자>`를 보여 주고(`revision`이 바뀔 때만 다시 로드), 상태 칩에 `Checking · generation N` / `Verified · rev N` / `Needs fix · showing rev N`(검증본 없으면 `no verified revision`)을 표시. 실패 시 진단 복사 버튼 |

**내장 브랜드 카탈로그** (`brands` 조회)

| 항목 | 값·의미 |
|---|---|
| 항목 필드 | `id`, `title`, `category`, `aliases[]`, `domains[]`, `viewBox`, `hex`, `provenance`(아이콘 출처·버전). 내부 `path`는 출력에서 제외 |
| 매칭 | 질의를 trim·소문자로 한 뒤 `id`·`title`·`category`·`aliases`·`domains` 중 하나에 부분 문자열로 들어 있으면 일치. 질의가 비면 전체 |
| 규모 | 107개, 카테고리 9종(collaboration 10, cloud 13, framework 13, engineering 18, ai 13, data 17, channel 10, language 5, business 8) |
| 텍스트 출력 | 카테고리별 `category: id, id, …`. 일치 없으면 `No built-in brand matched "<질의>". Run "archify brands capture <url> --json", then use the returned digest-pinned brand value.`(종료 코드 0) |
| `--json` | `{schemaVersion:1, ok:true, command:'brands', query, count, marks[], fallback}` |

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 명령 이름 없음/`help`/`-h`/`--help`, 알 수 없는 명령, `<명령> --help` | 사용법을 stdout에 출력하고 0(명령 이름 없음·`help`·`--help`). 알 수 없는 명령은 `Unknown command "<x>".`와 사용법을 stderr에 쓰고 2. 사용법 표는 `COMMAND_USAGE` 한 곳에서 만들며 `preview --help`도 전체 사용법을 출력 | 실행 확인 |
| R-02 | compare 인자 | `architecture` 외 타입·위치 인자 3개 미만·5개 이상이면 사용법(2). 알 수 없는 `--옵션`은 `Unknown compare option "<x>".`(2). `--receipt`는 값 필수. 출력은 `.html`, 영수증은 `.json`이며 같은 디렉터리여야 함. 출력·영수증이 입력과 별칭이면 거부 | 실행 확인(`out.txt`→`output/cli-extension`, 입력과 같은 경로→`output/input-alias`, 다른 디렉터리 영수증→`delta/receipt-directory`, `sequence` 타입→2) |
| R-03 | compare 비교 가능 조건 | 양쪽 `schema_version`이 1이 아니면 `delta/schema-version-mismatch`, `diagram_type`이 `architecture`가 아니면 `delta/type-mismatch`. 구성요소는 모두 고유 `id` 필요(없으면 `delta/stable-id-required`, 중복은 `delta/duplicate-stable-id`). 연결은 모두 고유 `id` 필요(없으면 `delta/relationship-id-required`, 증거 `paths:["/connections/0/id"]`). 경계는 `kind`+`label` 키가 유일해야 함(`delta/boundary-key-ambiguous`). 양쪽이 공유하는 구성요소 id가 하나도 없으면 `delta/no-shared-component-id`. 양쪽 `meta.repository`가 있고 저장소 정체성이 다르면 `delta/repository-mismatch`. 스키마 위반(`schema/required` 등)과 중복 연결 id(`relationship/duplicate-id`)는 정식 검증이 `input` 단계에서 먼저 막음 | 실행 확인(`no-shared-component-id`, `relationship-id-required`, `schema/required`, `relationship/duplicate-id`), 코드 확인(나머지) |
| R-04 | compare 변경 분류 | 같은 id끼리 필드 묶음별로 비교한다. 컴포넌트 묶음: 의미(type·label·sublabel·tag·brand·icon)/근거(sources)/기하(row·col·pos·size), 연결: 위상(from·to)/의미(label·variant)/기하(fromSide·toSide·route·via·labelAt·labelDx·labelDy·labelSegment·width), 경계: 범위(wraps)/기하(pad). 한쪽에만 있으면 `added`/`removed`(분류는 컴포넌트 `semantic`, 연결 `topology`, 경계 `scope`). 둘 다 있으면 `statusFor`로 `changed`/`evidence-changed`/`moved`·`rerouted`·`geometry-changed`/제외(같음). 비교 전에 `sources`·`wraps`는 정렬해 순서 차이를 무시. 요약 `presentationChanged`는 제목·로케일·부제·애니메이션·프리셋·품질·엔지니어링 프로파일·범례·viewBox·레이아웃·카드가 다를 때 true. 연결 id가 같고 from/to가 바뀐 것은 새 연결이 아니라 `changed`(위상) | 실행 확인(체크아웃 예제 전체, T-01), 코드 확인(필드 묶음 C-03) |
| R-05 | compare 증명 수준 | `proofLevel`은 양쪽에 `meta.repository`가 있고, 양쪽 렌더에서 소스 근거가 검증됐으며, 두 revision이 모두 40자리 16진수일 때만 `revision-pinned`, 아니면 `authored`. `provenance`는 저장소 URL·revision·provider·link_mode 중 달라진 필드(`/url` 등, 한쪽만 있으면 `/repository`)를 기록 | 코드 확인(예제는 저장소 정보 없음이라 `authored`만 실행 관찰) |
| R-06 | compare 정상 실행 | 양쪽 JSON을 컬렉션 순서를 정규화(`canonicalArchitecture`)한 뒤 각각 정식 검증·렌더·정적 검사(`check-render-output`)를 거친다. 두 면의 SVG에 상태 표시를 달고 Delta SVG를 만들어 Before/Delta/After HTML을 쓴 뒤 자체 검증(`validateArchitectureDeltaHtml`)을 통과해야 한다. `validation.checkCount`는 양쪽 검사 + delta 검사의 합. HTML에는 원본 JSON의 `rawSha256`·`bytes`를 넣지 않고 영수증에만 넣어, 서식만 다른 입력은 같은 HTML(같은 `artifact.sha256`)을 만든다. 출력 파일 이름이 달라도 HTML·영수증 바이트가 같다. 같은 입력끼리의 비교는 성공(0)이며 모든 요약 카운트가 0, `presentationChanged` false | 실행 확인(T-01, T-02, 이름 달라도 sha256 동일) |
| R-07 | compare 실패 시 출력 | 실패(1)이면 새 HTML·영수증을 만들지 않고 기존 파일을 건드리지 않는다. 성공이면 HTML과 영수증을 쌍으로 교체(기존 파일 백업 후 교체, 도중 실패는 복구 디렉터리에 남김). 스테이징 `.archify-*` 잔여물이 출력 폴더에 남지 않는다. 쓰기 전 경로 재검증이 실패하면 `commit` 단계 | 실행 확인(실패 시 기존 `OLD` 유지, 성공 시 교체, 잔여 스테이징 0), 코드 확인(백업·복구 디렉터리) |
| R-08 | migrate 인자·소스 | 사용법 위반(`workflow` 아님, 위치 인자 ≠3, `--to-schema` ≠`2`)은 2. 소스를 읽고 JSON 파싱하지 못하면 입력 진단과 함께 1. 소스와 대상이 같은 파일(별칭 포함)이면 `migration/source-destination`(1) 이고 소스는 그대로. `--output`은 `.html` 이식 경로 검증 후 후보의 `meta.output`만 교체 | 실행 확인(`--to-schema 3`→2, 소스=대상→1·소스 불변, 없는 소스→1, `--output` 적용), 코드 확인(경로 검증) |
| R-09 | migrate 변환 규칙 | 먼저 소스를 워크플로 스키마로 검증(실패는 `preExistingDiagnostics`, 예: `schema_version` 3은 `schema/enum`). 소스가 이미 v2면 컴파일만 확인하고 문서를 그대로 돌려줌(바이트는 다시 직렬화됨). v1이면 ①옛 열 중심(고정 v1 레이아웃)과 ②v2 순위 열 중심(`intrinsicWorkflow`; 실패하면 경로 지정 간선을 뺀 `planningWorkflow`)을 구해 ③x 좌표를 열 중심 대응으로 구간별 선형 변환(`createHorizontalRankMapper`; 범위 밖은 가장 가까운 구간으로 외삽, 소수 6자리)해 `edges[].via[][0]`, `edges[].labelAt[0]`, `edges[].channelX`에 적용하고 바뀐 것을 `changedCoordinates`에 기록, ④`schema_version`을 2로, 나머지 필드는 그대로. v2 컴파일이 `workflow/viewbox-capacity`로만 실패하고 `meta.viewBox`가 저작된 경우 필요한 만큼 viewBox를 키운 뒤 다시 컴파일(줄이지 않음). 최종 컴파일·스키마 검증이 실패하면 실패. 옛 레이아웃이 이미 실패하던 진단은 `preExistingDiagnostics`에 남기되, v2 결과가 통과하면 성공 | 실행 확인(최소 v1→성공 + 옛 `workflow/column-capacity` 진단 보존, v2 재변환 멱등, v3→`schema/enum`), 코드 확인(좌표 변환·viewBox 확장) |
| R-10 | migrate 검증·커밋 | 결과를 대상 폴더 안 `.archify-migration-*` 스테이징에 쓰고, 정식 워크플로 렌더러로 HTML을 만들고(`migration-check.html`), `check-render-output`을 통과해야 한다(실패는 `newSchemaDiagnostics`에 합쳐 렌더러·검사기의 종료 코드로 끝냄). 커밋 직전 소스 바이트가 처음과 같은지(`migration/source-changed`), 대상이 캡처 때와 같은지(`migration/destination-changed`), 후보가 그대로인지(`migration/candidate-changed`)를 다시 확인한다. 대상은 없거나 일반 파일이어야 함(`migration/destination-type`). 성공하면 대상을 교체(기존 파일은 백업 후 복구 가능). 실패하면 기존 대상은 그대로고 스테이징은 정리된다 | 실행 확인(기존 대상 교체, 실패 시 기존 대상 유지·스테이징 잔여 0, 같은 입력→같은 출력 바이트), 코드 확인(커밋 직전 재검증) |
| R-11 | migrate 보고 | 성공·실패 모두 R-08 표의 필드를 가진 보고서. 같은 소스를 두 번 변환하면 대상 바이트가 같음. 번들 v1 예제(`incident-response`, `release-delivery`)는 v3.2.0에서 `workflow/route-preset-conflict`(`newSchemaDiagnostics`)로 마이그레이션이 실패해 대상 파일이 생기지 않는다 | 실행 확인 |
| R-12 | preview 인자·사전 검사 | `--no-open` 외 알 수 없는 `--옵션`은 `Unknown preview option "<x>".`(2). 타입·입력이 없거나 위치 인자 4개 이상이면 사용법(2). `explainer`는 안내 문구와 함께 2. 알 수 없는 타입은 `Unknown diagram type …`(2). 입력이 JSON으로 파싱되는데 `meta.output`이 잘못됐거나 없으면 서버·감시자·스테이징을 만들기 전에 `Could not start live preview: …`(1). 읽을 수 없거나 JSON이 깨진 입력은 허용(라이브 수리). 출력 경로는 `[output.html]` → 시작 시점 `meta.output` → `<type>.html` 순 | 실행 확인(2 종료 3종: explainer·알 수 없는 옵션·알 수 없는 타입), 코드 확인(나머지) |
| R-13 | preview HTTP 표면 | 1.3 서버 계약 표대로. `Host` 검증·메서드 제한·헤더·CSP는 요청 처리 첫 단계에 있다 | 코드 확인(서버를 띄우지 않음) |
| R-14 | preview 빌드 루프 | 입력 디렉터리를 `fs.watch`하고 800ms마다 폴링. 입력 바이트의 SHA-256이 400ms 디바운스 뒤에도 그대로여야 빌드(안정 저장본), 마지막 성공 저장본과 같으면 빌드·리로드 없음. 한 번에 자식 하나(`pendingBuild`로 대기, 에포크로 낡은 결과 폐기). 빌드는 입력 바이트를 스테이징 `generation-N.json`(0600)으로 스냅샷해 `node archify.mjs deliver <type> <스냅샷> <후보.html> --json [--quality …] [--repo-root …]`를 실행. 종료 0이고 `receipt.ok`이며 낡지 않았으면 커밋: 후보의 해시·크기가 영수증과 같은지, 입력 해시가 빌드 시작 때와 같은지(다르면 되돌려 재빌드), 출력 슬롯이 그대로인지 확인한 뒤 출력 HTML을 원자적으로 게시하고 `verified`, 산출물 해시가 바뀐 경우에만 `revision` +1, `failure` 해제. 실패는 `needs-fix`와 `failure{stage, code?, message}`(메시지는 경로를 `<input.json>`·`<output.html>`·`<archify-skill>` 등으로 치환, 6000자 상한, 진단 12개까지)이며 마지막 검증본 화면과 출력 파일은 그대로. 삭제·반쯤 쓰인 입력도 마지막 검증본을 유지. 빌드 끝나면 후보·스냅샷·deliver 사이드카를 소유권 확인 후 삭제 | 코드 확인(서버를 띄우지 않음) |
| R-15 | preview 시작·종료 | 시작 시 출력 폴더를 만들고 그 실제 경로 안에 `.archify-preview-*` 스테이징을 만든다. `--no-open`이 아니면 OS 열기 명령(macOS `open`, Linux `xdg-open`, Windows PowerShell `Start-Process`)으로 URL을 연다. 실패하면 `Could not open the preview (<status>). … Target: <url>`을 stderr에 쓰고 계속 실행. 시작 실패는 `Could not start live preview: <사유>`(1). `SIGINT`/`SIGTERM` 1회: 서버를 닫고 진행 중 deliver를 3000ms 기다린 뒤 `SIGTERM`, 750ms 뒤 `SIGKILL`, 검증된 소유 파일만 정리. 2회: 즉시 강제 종료(소켓 파괴, 자식 `SIGKILL`). 마지막 검증본 출력 파일은 보존 | 코드 확인(실행하지 않음) |
| R-16 | `brands` 조회 | 1.3 카탈로그 표대로. `google`→`firebase`, `google-cloud`, `google-gemini`(3개), `Hugging Face`→`hugging-face`, `claude --json`→1개(`id:"claude"`, `category:"ai"`, `domains:["claude.ai"]`, `hex:"D97757"`). 읽기 전용이며 일치가 0개여도 종료 코드 0. 알 수 없는 `--옵션`은 `Unknown brands option "<x>".`(2) | 실행 확인 |
| R-17 | `brands capture <url>` | 위치 인자 정확히 1개(아니면 `Usage: archify brands capture <url> [--json]`, 2). URL은 `http`/`https`만(아니면 `brand capture requires one HTTP(S) URL`, 2). 카탈로그 도메인과 맞으면 네트워크 없이 프리셋 `id`를 `brand`로 반환(`evidence.status: "preset"`). 아니면 대상 사이트에서 아이콘을 받아 `{url, sha256}`(다이제스트 고정 값)을 `brand`로 반환하고 `evidence{status, source, sha256, contentType}`를 붙임. 실패는 `brand capture failed: …`(2). 한계값: HTML ≤256KiB, 이미지 ≤1MiB, 기본 8000ms(`ARCHIFY_BRAND_CAPTURE_TIMEOUT_MS`로 변경), 사설·루프백 IP 거부. **인터페이스 수준만 확인** | 코드 확인(인터페이스·한계값), 실행 확인(인자 오류 2, `ftp://` 거부 2). 캡처 성공 경로는 네트워크가 필요해 실행하지 않음(미확인) |
| R-18 | `doctor` | 27개 점검 줄을 `[ok] <라벨>`로 출력(Node ≥18, 템플릿·예제 렌더러·미리보기·시각 검사·finalize·출력 경로·원자적 출력·경로 의미·사이드카·이식 경로 런타임, 시나리오 가이드, 참조 문서 3개, compare 런타임+체크아웃 예제 2개, 독립 검증기가 `TYPES` 전부를 함수로 내보내는지, 타입 11종 각각의 렌더러·스키마·예제, explainer 런타임). 실패는 `[missing]`/`[invalid]`/`[unsupported]`로 표시. 모두 통과면 `Archify is ready.`(0), 아니면 stderr `Archify is not ready: <사유 요약>.`(1). 추가 인자·옵션은 2. **인터페이스 수준만 확인** | 실행 확인(정상 설치에서 27줄 `[ok]`, 0), 코드 확인(실패 분기는 실행하지 않음) |
| R-19 | `demo [dir]` | 폴더(기본 현재)를 만들고 아키텍처 렌더러로 번들 예제 `web-app.architecture.json`을 `<dir>/archify-demo.html`로 렌더. 렌더만 하며 `deliver`의 검사·provenance 파일은 만들지 않는다. 성공 시 `Demo ready: <경로>`와 다음 단계 안내. 인자 2개 이상·옵션은 사용법(2), 폴더 생성 실패 1. **인터페이스 수준만 확인** | 실행 확인(정상, 인자 2개→2, 옵션→2), 코드 확인(실패 분기) |
| R-20 | `examples` | 설치 폴더에서 `scripts/render-examples.mjs`를 실행(출력 루트 인자 없이 호출하므로 설치 폴더의 `examples/`에 쓴다). 추가 인자·옵션은 2. **인터페이스 수준만 확인** | 코드 확인(설치 폴더를 건드리므로 실행하지 않음) |
| R-21 | 업데이트 확인 | CLI 명령이 아니라 별도 스크립트. 인자 없음=확인, `--snooze <eventKey>`=7일 보류, `--ignore <eventKey>`=그 릴리스만 무시, `--ack`=무동작. 그 밖 인자는 `silent`(`invalid-arguments`). 결과는 stdout 한 줄 JSON이며 오류는 `{"status":"silent","reason":…}`. `ARCHIFY_UPDATE_CHECK_DISABLED=1`이면 즉시 `{"status":"silent","reason":"disabled"}`(snooze·ignore 포함, 상태 파일을 쓰지 않음). 기본 매니페스트 URL `https://tt-a1i.github.io/archify/skill-updates/archify/stable.json`, 확인 TTL 24h, 응답 ≤32KiB, 기본 제한 시간 1000ms. `deliver`·`finalize`는 같은 확인을 병렬로 돌려 영수증의 `update`에 넣는다(`deliver`는 최대 1000ms, `finalize`는 브라우저 검사가 있으면 4000ms, 없으면 200ms까지만 기다림. 확인이 안 되면 `status:"unavailable"`이고 전달을 막지 않음). `update.noticeRequired:true`이면 에이전트가 안내하며, 설치·다운로드·실행은 자동으로 하지 않는다. **인터페이스 수준만 확인** | 실행 확인(`DISABLED=1`일 때 두 호출), 코드 확인(상수·연동). 네트워크 확인 경로는 실행하지 않음(미확인) |
| R-22 | `recover-output` | 인자는 복구 디렉터리 하나와 선택 `--json`. `-h`/`--help` 단독이면 사용법을 stdout에 쓰고 0. 그 밖의 잘못된 인자·옵션은 사용법을 stderr에 쓰고 64. 결과 상태가 `recovered`·`absent`면 0, `preserved`(대상 자리에 다른 것이 있어 건드리지 않음)면 2, 나머지는 1. 출력은 `<status>: <reason.code>` 또는 JSON 한 줄. 디렉터리 스캐너가 아니라 지정한 `.archify-remove-<id>`만 복구. **인터페이스 수준만 확인** | 실행 확인(인자 없음 64, `--help` 0, 잘못된 옵션 64), 코드 확인(상태→종료 코드). 복구 절차 내부는 미확인 |

- 불변식: compare·migrate는 실패할 때 기존 출력 파일을 바꾸지 않는다(R-07, R-10). migrate는 소스 파일을 절대 쓰지 않는다. compare의 HTML과 영수증은 같은 입력이면 출력 이름과 상관없이 같은 바이트다(R-06, 이름이 영수증 내용에 들어가지 않는 범위에서). preview는 검증을 통과한 산출물만 화면과 출력 파일에 올린다(R-14, 코드 확인).
- 미결정:
  - R-17 · `brands capture`의 아이콘 탐색 순서·리다이렉트·방어 세부 → 재구현하려면 `brand-marks.mjs`의 `captureRemoteBrand`를 따로 읽어야 한다.
  - R-21 · 업데이트 확인의 캐시 정책·작업 잠금·백오프·매니페스트 검증(`update-contract.mjs`) → 인터페이스만 정해졌다.
  - R-22 · `recoverRetiredPublication`의 점검·복구 절차 → 종료 코드 매핑만 정해졌다.
  - R-20 · `examples`가 렌더하는 예제 목록 → `render-examples.mjs`를 읽지 않았다.
- 확인 한계: preview는 서버를 띄우지 않아 R-13~R-15는 코드 읽기뿐이다. `brands capture`·업데이트 확인의 네트워크 경로와 `examples`는 실행하지 않았다. 실행 확인은 로컬 설치본(`~/.claude/skills/archify`, 레포 `archify/`와 바이트 동일)에서 scratch 폴더 안에서만 했고, Node v26.10.0, macOS다. compare는 번들 체크아웃 예제 한 쌍(저장소 정보 없음)으로만 확인했다. migrate의 번들 v1 예제 2개는 실패해서, 성공 경로는 직접 쓴 최소 v1 문서(노드 3개, 열 겹침 있음)로만 확인했다. 좌표 변환 `changedCoordinates`가 실제로 채워지는 성공 사례는 실행하지 못했다(최소 문서에 절대 좌표가 없음).

### 1.5 필수 코드 참조 [필수]
Apache-2.0이므로 인용은 허용된다(overview 1절).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/bin/archify.mjs:2192-2225` `COMMAND_USAGE`, `usage` | 명령별 사용법 원문과 `Types` 목록 | R-01, R-02, R-08, R-12 |
| C-02 | `archify/bin/archify.mjs:7207-7289` 진입 `switch` | 명령 이름→함수 대응, `<명령> --help` 처리(`soleCommandHelp`), 알 수 없는 명령, 인자 오류 처리(`archifyArgument` → JSON 보고 대상 명령 5개만) | R-01 |
| C-03 | `archify/delta/architecture-delta.mjs:119-146,184-218,229-257` `stableIndex`, `boundaryKey`, `COMPONENT_FIELDS`·`CONNECTION_FIELDS`·`BOUNDARY_FIELDS`, `statusFor`, `compareEntities`, `presentationChanged` | 안정 id 규칙과 오류 코드, 필드 묶음→분류→상태 표 | R-03, R-04 |
| C-04 | `archify/delta/architecture-delta.mjs:259-355` `compareArchitecture` | 비교 가능 조건, `proofLevel`, 요약·영수증 모양 | R-03~R-06 |
| C-05 | `archify/delta/architecture-delta.mjs:37-100` `normalizeRepository`, `canonicalArchitecture` | 정규화(출력 경로 제거, 저장소 URL 소문자화, 컬렉션 정렬) | R-04, R-06 |
| C-06 | `archify/bin/archify.mjs:2825-2858` `extractCompareOptions`, `compareReceiptPath` | compare 옵션 파싱과 기본 영수증 이름 | R-02 |
| C-07 | `archify/migrations/workflow-v2.mjs:116-277` `migrateWorkflowDocument`, `serializeMigratedWorkflow` | v1→v2 변환 순서와 진단 구분, 직렬화(2칸+개행) | R-09 |
| C-08 | `archify/renderers/workflow/workflow-migration-geometry.mjs:82-153` `createHorizontalRankMapper`, `mapExplicitCoordinates` | 구간 선형 x 변환과 변경 좌표 기록 | R-09 |
| C-09 | `archify/bin/archify.mjs:6404-6442` `extractMigrationOptions` | migrate 옵션 파싱 | R-08 |
| C-10 | `archify/bin/preview.mjs:24-30,433-500` | 타이밍 기본값, 서버 요청 처리(Host·메서드·경로·헤더) | R-13 |
| C-11 | `archify/bin/preview.mjs:150-190,568-690,860-905` `compactMessage`, `redactDiagnostic`, `commitCandidate`, `queueStableBuild`, `observeSource` | 진단 가공(6000자·경로 치환), 커밋 검증 순서, 안정 저장본·디바운스 | R-14 |

C-ID 범위 안의 내부 helper는 1.3·1.4로 풀었다: `resolveOutputPath`(`requestedOutput` → 저작 `meta.output` → 기본값 순, 입력과 별칭이면 거부, 확장자 규칙)와 `captureAtomicOutput`·`commitComparePair`(출력 슬롯 스냅샷 후 검증·백업·교체)는 전달 흐름 소관이며 여기서는 "이 규칙을 호출한다"로만 쓴다. `COMPARE_SIDECAR_SUFFIXES`·`boundedSidecarStem`은 영수증 이름을 파일 시스템 이름 길이 한도 안에 맞추는 규칙이고 짧은 이름에서는 `<stem>.receipt.json`과 같다(긴 이름 사례는 확인하지 않음).

### 1.6 수락 사례 [필수]
출처: 모두 원본 실행 관찰(scratch 사본, 로컬 설치본). R-13~R-15는 실행 사례 없음. 입력·스크립트·출력은 [compare](../../../artifacts/archify/spec-demos/auxiliary/compare/), [migrate](../../../artifacts/archify/spec-demos/auxiliary/migrate/), [misc](../../../artifacts/archify/spec-demos/auxiliary/misc/)에 있다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-06 | `compare architecture base.json head.json out/delta.html`(체크아웃 예제: Session Cache 제거, Fraud Gate 추가, 결제 연결 변경 등) | 종료 0. `summary`: components{added 1, changed 1, evidenceChanged 0, removed 1, moved 1}, connections{added 1, changed 2, removed 1, rerouted 1}, boundaries{changed 2}, presentationChanged true, provenanceChanged false. 변경: `cache` removed, `checkout` changed(`/sublabel`), `fraud` added, `queue` moved(`/pos`), 연결 `authorize-payment` changed(분류 geometry+topology, `/from /fromSide /toSide /via`), `fraud-check` added, `persist-order` changed(`/label`), `publish-order` rerouted(`/labelDy`), `session-read` removed, 경계 `region:Production region`·`security-group:Checkout trust zone` changed(`/wraps`). `proofLevel` authored, `validation` 28/28, `base/head.composition` pass, stdout 3줄과 `delta.receipt.json` 생성 |
| T-02 | R-06 | 같은 파일 둘을 비교, 그리고 `--json --receipt out/delta2.receipt.json`으로 출력 이름만 바꿔 T-01을 반복 | 같은 입력 비교는 종료 0·모든 카운트 0·`presentationChanged` false. T-01과 이름만 다른 실행은 HTML `sha256`(`03a1f32e…`)과 영수증 바이트가 같다 |
| T-03 | R-03 | 컴포넌트·연결 id를 모두 접두사로 바꾼 헤드와 비교 `--json` | 종료 1, stdout JSON `stage:"compare"`, 진단 `delta/no-shared-component-id`, `supportedFixes:["preserve at least one authored component id across snapshots"]` |
| T-04 | R-03 | 헤드의 `connections[0].id` 삭제 / 두 연결이 같은 id / `schema_version` 1이지만 컴포넌트 `type` 삭제 | 각각 1: `stage:"compare"` `delta/relationship-id-required`(`subject.side:"head"`, `evidence.paths:["/connections/0/id"]`) / `stage:"input"` `relationship/duplicate-id` / `stage:"input"` `schema/required` |
| T-05 | R-02 | `…out.txt` / 출력을 입력 `base.json`과 같은 경로로 / `--receipt`를 다른 디렉터리로 / 타입 `sequence` / `--bogus` | 각각 1(`prepare` `output/cli-extension`) / 1(`prepare` `output/input-alias`, `base.json` 그대로) / 1(`delta/receipt-directory`) / 2(사용법) / 2(`Unknown compare option "--bogus".`) |
| T-06 | R-07 | `keep.html`·`keep.receipt.json`에 `OLD`를 써 두고 T-03 입력으로 실행, 이어서 정상 입력으로 같은 경로에 실행 | 실패(1) 뒤 두 파일 내용은 `OLD` 그대로, 성공(0) 뒤 둘 다 새 내용(`<!doctype html>`, 영수증 JSON). 출력 폴더에 `.archify*` 잔여물 0개. 출력 이름 생략 시 현재 폴더에 `architecture-delta.html`·`architecture-delta.receipt.json` |
| T-07 | R-08, R-09 | 최소 v1(`lanes` 2, `nodes` 3, `edges` 2, 열 0·1·2)을 `migrate workflow v1-min.json out2/min-v2.json --to-schema 2` | 종료 0, `migrated workflow schema v1→v2: …`. 대상은 소스와 `schema_version`만 1→2로 다름(키 순서·값 동일, 2칸+개행). `--json`: `ok:true`, `fromSchemaVersion:1`, `preExistingDiagnostics`에 `workflow/column-capacity`("Workflow columns 1→2 place nodes n2 and n3 … overlap by 12px under the fixed-v1 layout."), `changedCoordinates` 0개, `oldRequiredViewBox [720,404]`, `newRequiredViewBox [772,404]`. 같은 소스를 다시 변환하면 같은 바이트, 결과를 다시 migrate해도 같은 바이트, 결과는 `render workflow`로 렌더됨 |
| T-08 | R-08, R-09 | 같은 소스에 `--output portable.html` / `--to-schema 3` / 소스=대상 / 없는 소스 `--json` / `schema_version` 3 소스 `--json` | 각각 0(대상 `meta.output`=`portable.html`) / 2(`Usage: archify migrate workflow … --to-schema 2 …`) / 1(`migration/source-destination`, 소스 바이트 그대로) / 1 / 1(`preExistingDiagnostics:["schema/enum"]`) |
| T-09 | R-10, R-11 | 번들 `incident-response.workflow.json`(v1)과 `release-delivery.workflow.json`(v1)을 migrate(그 위치에 `{"keep":"old"}` 대상 파일을 먼저 둔 경우 포함) | 둘 다 1. 보고서 `ok:false`, `newSchemaDiagnostics:["workflow/route-preset-conflict"]`(예: `Workflow edge "alert->page" cannot satisfy route preset "drop": candidate violates lane/phase/group label clearance.`), `changedCoordinates`는 incident에서 `/edges/7/via/0/0` 430→454 등 채워짐. 대상 파일은 생기지 않고, 먼저 둔 `{"keep":"old"}`는 그대로. 스테이징 잔여 0개 |
| T-10 | R-16 | `brands claude --json`, `brands google --json`, `brands "Hugging Face" --json`, `brands zzzznotabrand`, `brands --x` | 각각 count 1(`claude`, 카테고리 ai), count 3(`firebase,google-cloud,google-gemini`), count 1(`hugging-face`), 안내 문구와 종료 0, 종료 2. `brands --json`은 count 107과 9개 카테고리 |
| T-11 | R-17 | `brands capture`(인자 없음), `brands capture ftp://example.com` | 둘 다 종료 2, 후자는 `brand capture requires one HTTP(S) URL`(네트워크 접근 전) |
| T-12 | R-18, R-19 | `doctor`, `demo <scratch>`, `demo a b`, `demo --x` | `doctor`: `[ok]` 줄 27개 후 `Archify is ready.` 종료 0. `demo`: 종료 0, `<scratch>/archify-demo.html` 생성, 마지막 안내 `Next: open the HTML in your browser, …`. 나머지 둘 종료 2 |
| T-13 | R-12, R-01 | `preview explainer x.md`, `preview workflow in.json --bogus`, `preview nope in.json`, `help`, `foo`, `preview --help` | 종료 2(explainer 안내 문구), 2(`Unknown preview option "--bogus".`), 2(`Unknown diagram type "nope". Expected one of: …`), 0(사용법), 2(`Unknown command "foo".` + 사용법), 0(전체 사용법). 서버는 뜨지 않음 |
| T-14 | R-21, R-22 | `ARCHIFY_UPDATE_CHECK_DISABLED=1 node scripts/check-update.mjs` 및 `--snooze somekey`, `node bin/recover-output.mjs`(인자 없음), `--help`, `-x` | 각각 stdout `{"status":"silent","reason":"disabled"}` 종료 0(둘 다), 사용법 stderr 종료 64, 사용법 stdout 종료 0, 사용법 stderr 종료 64 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
repo@a4065941f12be7967436261d9934784e381d423c 기준. 실행 기록은 모두 [spec-demos/auxiliary/](../../../artifacts/archify/spec-demos/auxiliary/) 아래다.

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, T-13 | C-01, C-02, [misc/run.log](../../../artifacts/archify/spec-demos/auxiliary/misc/run.log) | 로컬 설치본 실행. `fail()` 기본 종료 코드 2는 `archify.mjs:2227-2230` |
| R-02, T-05 | C-06, `archify/bin/archify.mjs:3675-3720,3940-4040`, [compare/run.sh](../../../artifacts/archify/spec-demos/auxiliary/compare/run.sh), [run2.sh](../../../artifacts/archify/spec-demos/auxiliary/compare/run2.sh) | 실행 확인. 출력·영수증 경로 해석 순서는 `commandCompare` 앞부분 |
| R-03, T-03, T-04 | C-03, C-04, `archify/bin/archify.mjs:4040-4130`(단계별 `reportCompareFailure`) | 실행 확인(4건), 나머지 코드 확인. 스키마·중복 id가 `input` 단계로 나오는 것은 실행 관찰, `error.compareStage || 'validate'` 폴백과의 관계는 미확인 |
| R-04, T-01 | C-03, C-05, [compare/inspect.out](../../../artifacts/archify/spec-demos/auxiliary/compare/inspect.out) | 실행 확인(번들 예제 한 쌍). 분류 규칙은 코드 확인 |
| R-05 | C-04, `archify/bin/archify.mjs:4128-4140` | 코드 확인. 예제에는 `meta.repository`가 없어 `revision-pinned` 경로는 실행하지 못함 |
| R-06, T-02 | `archify/bin/archify.mjs:4100-4220`, C-04 | 실행 확인(같은 입력·이름만 다른 실행의 `artifact.sha256` 동일, 영수증 `cmp` 동일) |
| R-07, T-06 | `archify/bin/archify.mjs:3960-4060,4215-4262`(캡처·`commitComparePair`·실패 분기), [compare/run2.log](../../../artifacts/archify/spec-demos/auxiliary/compare/run2.log) | 실행 확인(보존·교체·잔여 0). 백업·복구 디렉터리 내부는 코드 확인 |
| R-08, T-07, T-08 | C-09, `archify/bin/archify.mjs:6443-6540`, [migrate/run.log](../../../artifacts/archify/spec-demos/auxiliary/migrate/run.log), [run2.log](../../../artifacts/archify/spec-demos/auxiliary/migrate/run2.log) | 실행 확인 |
| R-09 | C-07, C-08, [migrate/run2.log](../../../artifacts/archify/spec-demos/auxiliary/migrate/run2.log) | 성공 경로는 최소 v1으로만 실행 확인. 좌표 변환은 코드 확인(실행 사례는 T-09의 `changedCoordinates`가 실패 보고서에 채워진 것뿐) |
| R-10 | `archify/bin/archify.mjs:6560-6900`, [migrate/run.log](../../../artifacts/archify/spec-demos/auxiliary/migrate/run.log) | 실행 확인(교체·실패 시 유지). 커밋 직전 재검증은 코드 확인 |
| R-11, T-09 | `archify/bin/archify.mjs:6346-6400` `migrationReport`, [migrate/run.log](../../../artifacts/archify/spec-demos/auxiliary/migrate/run.log) | 실행 확인 |
| R-12 | `archify/bin/archify.mjs:5352-5394` `commandPreview` | 종료 2 경로 3종 실행 확인. 사전 검사(JSON 파싱 후 `meta.output` 검증)는 코드 확인 |
| R-13 | C-10 | 코드 확인 |
| R-14 | C-11, `archify/bin/preview.mjs:725-860` | 코드 확인(서버를 띄우지 않음) |
| R-15 | `archify/bin/preview.mjs:540-620,945-970`, `archify/bin/open-artifact.mjs:1-30,100-110` | 코드 확인 |
| R-16, T-10 | `archify/bin/archify.mjs:6246-6300`, `archify/renderers/shared/brand-marks.mjs:82-89`, [misc/run.log](../../../artifacts/archify/spec-demos/auxiliary/misc/run.log), [run2.log](../../../artifacts/archify/spec-demos/auxiliary/misc/run2.log) | 실행 확인 |
| R-17, T-11 | `archify/bin/archify.mjs:6250-6275`, `archify/renderers/shared/brand-marks.mjs:21-25,553-567` | 인터페이스 수준. 네트워크 경로 미실행 |
| R-18, T-12 | `archify/bin/archify.mjs:6007-6196` | 정상 경로 실행 확인(27줄). 실패 분기는 코드 확인 |
| R-19, T-12 | `archify/bin/archify.mjs:6302-6330` | 실행 확인 |
| R-20 | `archify/bin/archify.mjs:5999-6005`, `archify/scripts/render-examples.mjs:10` | 코드 확인. 설치 폴더를 쓰므로 실행하지 않음 |
| R-21, T-14 | `archify/scripts/check-update.mjs:30-44,1680-1717`, `archify/scripts/update-contract.mjs:3`, `archify/bin/delivery-update.mjs:1-40`, `archify/bin/finalize.mjs:23,817-818,1048`, `archify/references/update-awareness.md` | `DISABLED=1` 두 호출만 실행 확인. 네트워크 경로 미확인 |
| R-22, T-14 | `archify/bin/recover-output.mjs:1-41`, `archify/references/delivery-contract.md:118-128` | 사용법 경로 실행 확인. 복구 내부 미확인 |

**문서와 구현의 차이·발견** (구현을 사실로 썼다)
- feature map(행 12)과 요청은 `update` 확인과 `recover` "계열"을 명령처럼 적지만, 둘은 `archify.mjs`의 `switch`·사용법 표에 없다. `update` 확인은 `scripts/check-update.mjs`(와 `deliver`/`finalize` 영수증의 `update` 필드), `recover`는 `bin/recover-output.mjs`다. 사용법 표에 있는 보조 명령은 `compare`, `preview`, `migrate`, `brands`(조회·capture), `doctor`, `demo`, `examples`다(`inspect`·`guide`는 다른 행).
- 번들 v1 워크플로 예제 2개(`incident-response`, `release-delivery`)는 `migrate`가 `workflow/route-preset-conflict`로 실패한다(R-11). 이를 약속하는 문서는 찾지 못했다.
- `delivery-contract.md`는 `migrate … --output`을 "migration-candidate exception"으로 설명하며 구현과 일치한다(R-08).
- README의 "Last-good live preview" 설명(직전 정상본 유지)과 `delivery-contract.md`의 설명은 `preview.mjs`의 상태 전이와 일치한다(코드 확인).

### 2.2 코드 읽는 순서 [선택]
1. `archify.mjs`의 `COMMAND_USAGE`(2192)와 진입 `switch`(7207)로 명령→함수를 잡는다. 함수 위치: `commandCompare` 3675, `commandPreview` 5352, `commandDoctor` 6007, `commandBrands` 6246, `commandDemo` 6302, `commandMigrate` 6443.
2. compare: `commandCompare`의 경로 해석(3700~4040) → 스테이징·정규화·렌더(4040~4130) → `delta/architecture-delta.mjs`의 `compareArchitecture`(259) → `renderArchitectureDeltaHtml`(751)·`validateArchitectureDeltaHtml`(1240) → `commitComparePair`.
3. migrate: `commandMigrate` → `migrations/workflow-v2.mjs`의 `migrateWorkflowDocument` → `renderers/workflow/workflow-migration-geometry.mjs`.
4. preview: `commandPreview`(사전 검사) → `bin/preview.mjs`의 `startPreview`(서버 433, 빌드 `beginBuild`·`commitCandidate`, 감시 `observeSource`) → `runPreview`(종료 처리).
5. 구현 전략: compare·migrate·preview 모두 "스테이징에서 만들고 검증한 뒤 마지막에 원자적으로 교체"한다. 스냅샷·잠금·경로 별칭 검사가 길게 붙어 있는데, 규칙의 핵심은 위 R-ID에 있다.
