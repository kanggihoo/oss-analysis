---
sha: "a4065941f12be7967436261d9934784e381d423c"
created: 2026-11-02
updated: 2026-11-02
sources:
  - archify/SKILL.md
  - archify/references/repository-authoring.md
  - archify/references/authoring-defaults.md
  - archify/references/authoring-contract.md
  - archify/renderers/shared/cli.mjs
  - archify/renderers/shared/repository-evidence.mjs
  - archify/renderers/shared/desktop-readability.mjs
  - archify/renderers/erd/render-erd.mjs
  - archify/schemas/common.schema.json
  - archify/schemas/architecture.schema.json
  - archify/schemas/waterfall.schema.json
  - archify/schemas/timeline.schema.json
  - archify/schemas/lifecycle.schema.json
  - archify/schemas/workflow.schema.json
  - archify/schemas/dataflow.schema.json
depends:
  - type-routing.md
status: draft
---

# 근거 수집과 초안 작성 규칙

> 타입이 정해진 요청에서 LLM이 레포 근거를 모으고 JSON 초안(`candidate.json`)을 쓰는 규칙이다. 대부분 지시문이고, 일부는 스키마·`repository-evidence`가 강제한다. 규칙마다 둘을 구분해 표시한다.

status가 `draft`인 이유: (1) 링크한 `input-validation.md`(행 5)가 아직 없다. (2) R-18의 수치 예산을 어느 단계가 강제하는지 이 스펙에서 확인하지 못했다(행 6·8 범위).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 작업 폴더를 정한다(R-01). 레포가 대상이면 `git`으로 신원(URL, 40자 커밋)을 고정한다(R-04).
2. 진입점에서 필요한 만큼만 읽으며 주장마다 `파일:줄 범위`를 모은다(R-09~R-11). 모르는 것은 모른다고 적는다.
3. 예시·스키마·기본값 문서를 한 번에 읽는다(R-12). 예시는 모양만 가르치고 값은 새로 정한다.
4. 요청 범위와 근거가 채워지면 완성된 초안을 한 번에 쓴다(R-13). 추상화·배치·표현은 기본값을 따른다(R-14~R-20).
5. 곧바로 `finalize`를 돌린다(R-21). 강제 규칙은 CLI의 입력 검증에서 걸린다. 순서는 `meta.output` 형식 → 스키마 → 로케일 번역 → ID 교차 계약 → 엔지니어링 프로파일 → 저장소 근거(`cli.mjs:80-86`). 이 단계의 내부는 `input-validation.md`가 푼다.

### 1.2 범위·통합 지점 [필수]
- 제공: 근거 수집 절차, `sources`·`meta.repository` 작성 규칙, 추상화·배치·언어·표현 기본값, 어느 규칙이 코드로 강제되는지의 표시.
- 제외: explainer 초안(`candidate.archify.md`) 작성 문법(행 10), 타입 선택(`type-routing.md`), 검증 단계 내부(`input-validation.md`), 렌더링(행 6), 실패 수리(행 9), 타입별 스키마 필드 전체(공유 계약), 뷰어 기능, `brands`.
- 외부 의존·선행 계약: 선행 `type-routing.md`(타입 확정). 호스트의 셸·`git`. 검증 쪽 계약은 [input-validation.md](input-validation.md)(작성 전일 수 있음).
- 소유 상태·부작용: `candidate.json`과 작업 폴더. 이 기능은 코드를 실행하지 않고 파일을 쓰는 주체는 LLM이다.

표기 규칙: R-ID의 조건 칸 앞에 `[지시문]`, `[강제·단계]`를 붙인다. `[강제·...]`는 실제로 위반 시 진단이 나오는 것이고, 단계는 `output-path`·`schema`·`repository-evidence`·`renderer`다. 이외는 모두 지시문이다.

### 1.3 인터페이스와 데이터 의미 [필수]
외부 계약이므로 원문 이름 그대로 쓴다.

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 작업 폴더 | `.archify/<type>-<slug>-<YYYYMMDD-HHMMSS>/` | 요청마다 하나, 로컬 시각, 한 번만 정함. 후보와 `<slug>.html`을 두고 수리에 재사용(R-01) |
| `meta.output` | string, 작업 디렉터리 기준 POSIX 상대 `.html` 경로 | 5개 타입(architecture, workflow, sequence, dataflow, lifecycle)은 스키마 필수, 나머지 5개 타입은 선택(R-02) |
| `meta.repository` | `{url, revision, provider?, link_mode?}` | `revision`은 `^[a-fA-F0-9]{40}$`, `provider`는 `github\|gitee\|gitlab`, `link_mode`는 `web\|local-only`(기본 `web`). 추가 키 금지(C-02) |
| `sources` | `[{path, line?, end_line?, label?}]`, 1~3개 | 주 요소에만 둔다. 컬렉션 이름은 C-03 표. `path` ≤240자, `label` ≤48자, 라인은 1 이상 정수(C-02) |
| `--repo-root <path>` | CLI 옵션 | 근거를 선언한 초안은 필수. Git 최상위 디렉터리여야 하고 `origin`이 `meta.repository.url`과 같은 저장소를 가리켜야 함 |
| `meta.quality_profile` | `standard\|showcase` | 지시문 기본 `showcase`. 생략해도 검증은 통과하고 SVG에 `data-quality-gates="advisory"`가 붙음(R-19) |
| `meta.locale` | 언어 태그 문자열 | 패턴 `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`, ≤35자(R-22) |

### 1.4 행동 규칙과 남은 질문 [필수]
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지시문] 새 산출물 요청(사용자가 다른 위치를 안 줌) | 작업 폴더(1.3)를 한 번 정하고 후보와 HTML을 그 안에 둔다. 수리는 같은 폴더를 재사용하고 다음 요청은 새 폴더를 쓴다. native는 `candidate.json`과 작업 디렉터리 기준 `meta.output`, explainer는 `candidate.archify.md`와 이식 가능한 파일명 | 코드 확인(지시문). 폴더 규칙을 강제하는 코드는 찾지 못함 |
| R-02 | [강제·output-path/schema] `meta.output` | 형식이 틀리면 스키마 전에 `output/meta-path-syntax`(`..` 포함 등), `output/meta-extension`(`.html` 아님) 진단. 필수 여부는 타입별로 다르다(1.3). 지시문(`authoring-defaults.md:39`)은 "required"라고 하지만 class·erd·tree·timeline·waterfall 스키마는 `title`만(timeline·waterfall은 `evidence`도) 요구한다 | 실행 확인(architecture), 필수 목록은 코드 확인 |
| R-03 | [강제·schema] 초안 최상위·`meta`·요소에 스키마에 없는 필드 | `schema/additionalProperties` 진단(`meta.foo`, 관계에 `sources` 등). 열거값 위반은 `schema/enum`(예: `meta.animation:"pulse"`, `componentType`, Architecture 경계 `kind`는 `region\|security-group`), 식별자는 `^[a-zA-Z][a-zA-Z0-9_-]*$` 패턴. "필드를 지어내지 말고 쓰기 전에 스키마 정의를 읽어라"는 지시문의 강제판이다 | 실행 확인(`unknown-meta-field`, `animation-invalid`, `sources-on-connection`), 열거 목록은 코드 확인 |
| R-04 | [지시문] 레포 기반 초안 시작 | 대상 레포에서 `git rev-parse HEAD`, `git remote get-url origin`, `git status --short`를 기록한다. HTTP(S) 사용자 정보(이름·비밀번호·토큰)는 제거하고 전송 방식·포트·경로·`.git` 접미를 보존한다(SSH를 HTTPS로 바꾸지 않음). 이 URL과 40자 커밋을 `meta.repository`에 고정한다. SSH·미지원 포지·의도적 로컬은 `link_mode:"local-only"`. 작업트리가 더럽거나 변경 경로를 인용하면 답에 적는다(초안엔 필드 없음). 커밋되지 않은 바이트를 `HEAD` 근거로 제시하지 않는다 | 코드 확인(지시문) |
| R-05 | [강제·repository-evidence] 근거 선언(`meta.repository` 있음 또는 어느 주 요소에 `sources`가 있음) | 아래가 어긋나면 첫 진단에서 실패하고 인용 오류는 모아서 보고한다: `meta.repository` 없음 `repository-required`, `--repo-root` 없음 `root-required`, `revision` 비-40자 `schema/pattern`, URL 형식(자격 증명·쿼리·점 세그먼트 불가) `url-invalid`, `web` 모드인데 GitHub/Gitee/GitLab HTTPS 표준 URL이 아님 `links-unsupported`, `provider` 불일치, 로컬 `origin`이 URL과 다른 저장소 `origin-mismatch`, 커밋이 로컬에 없음 `revision-unavailable`, 근거가 한 건도 없음 `source-required`. 단계 상세는 `input-validation.md` | 실행 확인(`sources-without-repository`, `repository-without-sources`, `evidence-without-repo-root`, `short-revision`, `wrong-origin`), 나머지 코드 확인 |
| R-06 | [강제·schema+repository-evidence] `sources` 항목 | 배열은 1~3개(`schema/maxItems`), 항목 키는 `path`·`line`·`end_line`·`label`뿐. 관계·메시지·흐름·전이에는 `sources`가 없다(`schema/additionalProperties`). 컬렉션은 C-03. `path`는 저장소 상대 POSIX이고 `/`·`\`·제어문자·`.`·`..`·`.git` 불가(`path-invalid`, `path-escape`). 고정 커밋에 파일(blob)이 있어야 하고(`file-missing`), `end_line`은 `line`이 있어야 하며 `end_line ≥ line`, `end_line`(없으면 `line`)이 그 시점 파일 줄 수 이하여야 한다(`line-out-of-range`). 작업트리가 아니라 커밋된 바이트 기준이다 | 실행 확인(`four-sources`, `file-missing`, `line-out-of-range`, `sources-on-connection`), 나머지 코드 확인 |
| R-07 | [지시문] 근거가 어떤 요소에 놓이는가 | 관계·메시지·흐름·전이의 증거는 그것을 소유한 요소(호출자, 쓰는 쪽, 떠나는 상태)에 두고 더 긴 증거는 노트나 카드에 둔다. 폴더 노드는 자기 README나 진입 파일, Timeline 이벤트는 그 시점 기록 파일, 실측이 없는 Waterfall은 `meta.evidence:"illustrative"`로 표시한다. 파일·DB 엣지는 실제로 읽고 쓰는 코드를 가리켜야 한다 | 코드 확인(지시문). `meta.evidence`는 waterfall(`measured\|illustrative`)·timeline(`observed\|illustrative`)에서 스키마 필수라 [강제·schema] |
| R-08 | [지시문] 근거의 범위 | "모든 저장소 기반 구성요소에 `sources`"는 지시문이다. 코드는 근거 한 건 이상만 요구하며 일부 요소만 인용한 초안도 통과한다. 인용한 줄의 내용이 주장과 맞는지도 확인하지 않는다(존재·줄 범위만) | 실행 확인(`ok-with-evidence`: 요소 b에 `sources` 없이 통과), 내용 불일치 미검사는 코드 확인 |
| R-09 | [지시문] 근거 수집 | 필요한 만큼만 연결된 조각을 읽는다. 순서는 프로젝트 지침·매니페스트·진입점·등록·배포 설정 → 요청 책임이 실제 입력·출력·부작용에 닿을 때까지 import와 호출 지점을 따라감. 이름이나 설명으로 서비스를 지어내지 않는다 | 코드 확인(지시문) |
| R-10 | [지시문] 소유 추적 | 런타임·I/O 관계는 호출 지점의 실제 주체·동작·대상에서 이끌어 낸다. 요청하는 컨트롤러, 실행하는 런타임, 바이트를 받는 저장소를 구분한다. 설정된 제공자·주입된 어댑터·로컬 스텁·내구성 서비스는 다른 주장이므로 소스가 뒷받침하는 쪽으로 라벨한다. 권위 있는 상태 변경은 실제 쓰기·실행 지점과 조건까지 추적한다. 정상 경로에서 호출되지 않는 export·설정은 선택 기능이다 | 코드 확인(지시문) |
| R-11 | [지시문] 불확실성과 종료 | 모르는 것은 그 주장 옆에 쓰거나 명시적 미지로 남긴다(예: "`writeFile`이 여기서 호출됨, 내구성은 미상"). 요청된 책임·관계·경계가 근거로 채워지고 남은 미지가 그 범위를 못 바꾸면 멈춘다. 노드·엣지·인용·뷰·카드·경계 개수에 목표나 상한이 없다. 줄 번호가 있는 발췌(`nl -ba file \| sed -n 'a,bp'`)로 읽고 화면에 보인 시작·끝 줄을 그대로 옮기며, 끝줄이 파일 끝이면 실제 마지막 줄을 쓴다 | 코드 확인(지시문) |
| R-12 | [지시문] 작성 전 읽기 | `authoring-defaults.md`와 모드 예시를 프로젝트 문서·전체 스키마와 별도의 묶음으로 한 번에 읽는다. Architecture 외 모드는 모드 스키마와 공통 스키마도 읽는다. 새 필드·열거값·제한 문자열을 고르기 전에 그 스키마 정의를 읽는다. 예시는 모양만 가르치므로 ID·문구·배치·값을 새로 쓰고 예시의 선택 표현 필드(`meta.subtitle`, `meta.viewBox`, `meta.column_fit`, `via`, `labelAt`)를 기본값으로 삼지 않는다. 사전 도움말·`doctor`·시작 검증·임시 다이어그램·출력 경로 목록 조회 없이 바로 후보로 간다. 브랜드는 명시 요청이 있을 때만 조회하고, 사용자 URL이 있는 미등록 마크는 브랜드 가이드를 읽는다 | 코드 확인(지시문) |
| R-13 | [지시문] 쓰기 시점 | 요청 범위와(레포면) 근거가 채워지면 좌표를 말로 계획하지 않고 완성된 후보를 한 번에 쓴다. 자동 경로를 먼저 쓰고 명시 경로는 필요한 분기·복귀·주어진 기하·측정된 수리에만 쓴다. `meta.quality_profile`은 사용자가 밀집 `standard`를 요청하지 않으면 `"showcase"`. ERD는 표 우선(`entities[].attributes`에 모든 물리 컬럼, SQL 타입·주석, 키 역할 `key`는 역할 또는 목록, 모든 `fk`에 `references: "orders.id"`), 도메인마다 `tag`와 `row`/`col`로 꽉 찬 직사각형. 8표·50필드 이상의 스키마 우선 ERD는 첫 완전 초안을 `standard`로 | 코드 확인(지시문). ERD 도메인이 직사각형이 아니면 `erd/domain-not-drawn`을 렌더러가 낸다(`render-erd.mjs:1108`) → [강제·renderer], 코드 확인 |
| R-14 | [지시문] Architecture 추상화 기본값 | 별도 요청이 없으면 주 사용자 여정이 이끄는 시스템 개요. 협력하는 역할은 정확한 이름의 하위 시스템으로 묶되 제어 소유·신뢰·영속 경계·생명주기를 가릴 때는 분리. 부차·선택 기능은 근거 있는 짧은 노트로 두고 좁힌 범위는 제목에 적는다. 요청된 책임·방향·프로토콜·행동을 바꾸는 조건을 보존하고 승인·인가·상태 전이 게이트는 해당 노드·관계에 표시한다(카드로 무조건 화살표를 한정할 수 없다). 경계는 실제 격리·소유·런타임·영속 사실일 때만. 카드는 필수 토폴로지를 대체하지 못한다 | 코드 확인(지시문) |
| R-15 | [지시문] 관계 라벨 | 라벨은 의미(동작·프로토콜·방향·비동기·경계 횡단)를 담는다. 스키마가 라벨 생략을 허용하고 양 끝점이 완전히 암시할 때만 생략한다. 충돌은 간격·경로 수리로 풀고 의미를 줄이지 않는다 | 코드 확인(지시문) |
| R-16 | [지시문] Architecture 배치 | 관계를 먼저 분류한 뒤 배치한다: 주 경로는 읽는 순서로 인접, 분기·저장소는 소유 노드 바로 위아래 가운데, 복귀는 분기가 없는 쪽 빈 복도, 이미 들어오는 엣지가 있는 노드의 두 번째 입구는 다른 변, 한 변에 관계 k개면 최소 `32 + 14 × (k − 1)`px. 주 행위자와 첫 단계는 캔버스 원점 근처(약 `[40, 40]`)에 둔다. 새 Architecture는 `meta.viewBox`를 생략한다. `via`·`channelX`·`channelY`·라벨 좌표는 측정된 결함에만 | 코드 확인(지시문) |
| R-17 | [지시문] Architecture 치수 예산 | 좌우로 인접한 라벨 달린 엣지는 `6.5px × ASCII 단위 + 21px`(CJK는 2단위)의 빈 간격. 경계 프레임 안에는 비구성원을 두지 않는다. 캔버스 너비 1240px 이하, 가로세로비 1.55 이상이면 1790px 이하. 부제는 `5.4px × 단위 + 8px`. 의미나 가독성을 교차 수와 맞바꾸지 않는다 | 코드 확인(지시문). 강제 단계는 R-18 |
| R-18 | [지시문, 일부 측정] R-16·R-17의 수치 | 1.55 비율은 `desktop-readability.mjs:7`의 `DECLARED_WIDE_READER_RATIO`에 있다. 나머지 수치(32+14(k−1), 6.5·단위+21, 1240)가 코드에서 진단으로 강제되는지는 확인하지 못했다. 렌더러·`browser-check`(행 6·8)의 측정이 일부를 잡는다고 추론한다 | 코드 확인(상수 1건), 강제 범위는 미확인 |
| R-19 | [지시문+schema] 표현 기본값 | 생략이 기본: `meta.animation`(모션은 자동. 허용값 `trace\|none`), `meta.visual_preset`(classic. 허용 `classic\|signal-flow\|blueprint\|editorial`), `meta.subtitle`(사용자가 요청할 때만), `meta.legend`, `meta.engineering_profile`(허용값 `deployment-ownership`뿐. 켜면 `validateEngineeringProfile`이 검사). 값이 열거를 벗어나면 `schema/enum`. 지시문을 어겨도(부제 사용 등) 검증은 통과한다. `meta.quality_profile`을 생략해도 `validate`는 통과하고, 렌더 시 `--quality` 값 → 환경변수 `ARCHIFY_QUALITY_PROFILE` → `meta.quality_profile` 순으로 정해지며 셋 다 없으면 `data-quality-gates="advisory"`가 붙는다 | 실행 확인(`subtitle-allowed`, `quality-profile-omitted`, `animation-invalid`), 우선순위는 코드 확인(`cli.mjs:366-370`). `--quality`와 `meta.quality_profile` 불일치 시 경고·오류가 있는지는 미확인 |
| R-20 | [지시문] 타입별 기본값 | Workflow는 새 초안에 스키마 v2, `meta.viewBox`·노드 `width` 생략(노드 92px에서 200px까지 자람). Sequence는 `meta.viewBox`·`meta.column_fit` 생략, 참가자 내부 동작은 메시지의 노트로(자기 메시지 루프 없음), 노트 줄 수별 다음 메시지까지 간격 44/55/66px 이상. Dataflow는 2~5 단계·행 0~4, 흐름 라벨 약 17단위 이하, 모든 흐름에 비어 있지 않은 `label`, `variant`는 의미대로. Lifecycle은 스키마 v3, `mainPath`에 행복 경로를 두고 모든 전이를 작성. Class는 `meta.viewBox` 생략, 열 3개(타입 폭이 180px 근처일 때만 4). Tree는 레포·디렉터리면 `layout.direction:"right"` | 코드 확인(지시문). 스키마 버전은 [강제·schema](workflow `[1,2]`, lifecycle `3`, 나머지 `1`)이고 Dataflow 흐름의 `from`·`to`·`label` 필수도 스키마(`dataflow.schema.json`)다 |
| R-21 | [지시문] 첫 검증 호출 | 완성 후보 직후 `node bin/archify.mjs finalize <type> <candidate.json> <output.html> --quality showcase --json`을 실행한다(별도 사전 검증 없음). 레포 기반이면 같은 명령에 `--repo-root <repo-root>`를 첫 호출부터 넣는다. `--quality`는 `meta.quality_profile`과 맞춘다. 실행 중에는 후보를 바꾸지 않는다 | 코드 확인(지시문). 명령 형식은 `archify.mjs:2197` 사용법 줄과 일치 |
| R-22 | [지시문+schema] 언어 | 주 작성 언어를 하나 고른다(사용자 명시 > 요청 언어 > 대화 우세 언어). `meta.locale`은 형식이 맞는 언어 태그(패턴은 [강제·schema]). 번들 카탈로그는 `en`, `zh-CN`, `zh-TW`, `es`, `ko`, `ar`(태그는 대소문자 무시, `es-MX`·`zh-Hant`는 번들 아님). 그 밖 언어는 `meta.translations`를 주거나, 못 주면 `meta.locale`을 생략하고 뷰어 UI·`<html lang>`이 영어라고 사용자에게 알린다. 작성 콘텐츠는 번역 대상이 아니므로 요청 언어로 직접 쓰고 제품·코드·명령·프로토콜 이름은 원문 유지. 번들 없는 로케일을 번역 없이 쓰면 검증은 통과하되 `i18n/locale-fallback` 경고가 난다(`i18n.mjs:257`). 잘못된 번역 키·자리표시자는 `i18n/invalid-translation` 경고로 무시된다 | 실행 확인(`locale-unbundled`: 통과 + `i18n/locale-fallback`), 나머지 코드 확인(지시문) |
| R-23 | [지시문+schema] 일상 주제 아이콘 | `icon`은 공통 스키마 `nodeIcon` 열거에서 고르고 `"none"`이면 숨긴다. 일상 개념은 `calendar`·`clock`·`person`·`briefcase`·`flag`·`moon`. 아이콘은 색·유형을 바꾸지 않고(유형이 색·그룹을 정함) 노드 라벨은 의미를 가져야 한다. `meta.legend.entries.<kind>.label`로 독자용 이름을 준다. URL·원시 SVG는 받지 않는다 | 코드 확인(지시문, `common.schema.json:74` 열거 정의) |

- 불변식: R-05·R-06의 강제 항목은 입력 검증에서 렌더링 전에 걸리므로, 통과한 초안의 모든 `sources`는 고정 커밋에서 파일과 줄 범위가 존재한다. 단 내용 일치와 `revision`이 `HEAD`인지는 보장하지 않는다(R-08, R-04의 `HEAD` 기록은 지시문).
- 미결정: R-18 · 치수 예산 중 어느 것이 진단으로 강제되는지 · 재구현자가 "지시문 복제"만 하면 되는지 "측정 진단까지"인지가 달라진다(행 6·8 스펙에서 결정).
- 확인 한계: 지시문을 에이전트가 실제로 따르는지는 미확인이다. `--repo-root`를 레포 clone에 지정한 사례는 `git` 읽기 명령만 실행됐고 설치본(레포 `archify/`와 `diff -rq` 동일)으로 검증했다. Architecture 외 타입 렌더러의 레이아웃 진단과 `validateEngineeringProfile` 내부는 읽지 않았다.

### 1.5 필수 코드 참조 [필수]
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `archify/renderers/shared/cli.mjs:80-86` `loadDiagram` | 입력 검증 순서(출력 경로 형식 → 스키마 → 로케일 → 교차 계약 → 엔지니어링 프로파일 → 저장소 근거) | R-02, R-03, R-05, R-22 |
| C-02 | `archify/schemas/common.schema.json:134-163` `repository`, `sourceReferences` | `meta.repository`와 `sources`의 형식·제한 | R-05, R-06 |
| C-03 | `archify/renderers/shared/repository-evidence.mjs:130-153` `EVIDENCE_NODE_COLLECTIONS`, `hasRepositoryEvidence` | 타입별 `sources` 컬렉션(architecture `components`, workflow·dataflow·tree `nodes`, sequence `participants`, lifecycle `states`, erd `entities`, class `types`, timeline `events`, waterfall `spans`)과 "근거 선언" 판정 | R-05, R-06 |
| C-04 | `archify/renderers/shared/repository-evidence.mjs:155-166, 196-201, 374-379` `verifyRepositoryEvidence` | `repository-required`·`revision-invalid`·`root-required`·`source-required` 조건 | R-05 |
| C-05 | `archify/renderers/shared/cli.mjs:366-370` `svgRootAttrs` | 품질 프로파일 우선순위와 `advisory` 표시 | R-19 |
| C-06 | `archify/references/repository-authoring.md:10-25` | `meta.repository` 고정과 `local-only` 선택 지시문 전문(문구가 정확해야 해서 인용) | R-04 |

### 1.6 수락 사례 [필수]
출처: T-01~T-09는 설치본 `validate architecture <file> --json`을 실행한 관찰(`artifacts/archify/spec-demos/authoring-enforcement-demo.py`, 출력 `authoring-enforcement-demo.out.txt`). 대상 레포는 clone(`repos/archify`)이고 `revision`은 기준 SHA다. 모두 종료 코드와 `diagnostics[].code`를 본다. T-10 이후는 구현에서 도출한 LLM 평가 사례.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05, R-06 | 컴포넌트 둘, `meta.repository:{url:"https://github.com/tt-a1i/archify", revision:<기준 SHA>}`, 컴포넌트 `a`에만 `sources:[{path:"archify/SKILL.md",line:18,end_line:30}]`, `--repo-root <clone>` | 종료 0, `ok:true`(컴포넌트 `b`에 `sources` 없어도 통과, R-08) |
| T-02 | R-05 | T-01에서 `meta.repository`만 제거 | 종료 1, `repository-evidence/repository-required` |
| T-03 | R-05 | T-01에서 `sources`만 제거 | 종료 1, `repository-evidence/source-required` |
| T-04 | R-05 | T-01 그대로, `--repo-root` 없이 | 종료 1, `repository-evidence/root-required` |
| T-05 | R-05 | `revision`을 7자(`a406594`)로 | 종료 1, `schema/pattern` |
| T-06 | R-06 | `sources`에 같은 항목 4개 / 관계(`connections[0]`)에 `sources` | `schema/maxItems` / `schema/additionalProperties` |
| T-07 | R-06 | `line:9999` / `path:"archify/NOPE.md"` | `repository-evidence/line-out-of-range` / `repository-evidence/file-missing` |
| T-08 | R-05 | `url`을 `https://github.com/other/other`로 | `repository-evidence/origin-mismatch` |
| T-09 | R-02, R-03, R-19, R-22 | `meta.output:"../t.html"` / `"t.txt"` / `meta.animation:"pulse"` / `meta.foo:1` / `meta.subtitle:"s"` / `meta.quality_profile` 생략 / `meta.locale:"fr"` | `output/meta-path-syntax` / `output/meta-extension` / `schema/enum` / `schema/additionalProperties` / 통과 / 통과 / 통과 + `i18n/locale-fallback` 경고 |
| T-10 | R-04 | LLM 평가: `git status --short`에 변경이 있는 레포 | 답에 변경 경로를 적고, 커밋되지 않은 바이트를 `HEAD` 근거로 인용하지 않음 |
| T-11 | R-04 | LLM 평가: 원격이 `https://user:token@github.com/o/r.git` | `meta.repository.url`에 사용자 정보가 없고 `.git`을 유지 |
| T-12 | R-07, R-10 | LLM 평가: 함수가 "tasks를 관리" 한다고만 설명하는 소스 | 그 설명만으로 파일·DB 엣지를 만들지 않고 실제 읽기·쓰기 지점을 근거로 인용 |
| T-13 | R-20 | LLM 평가: 새 Workflow·Sequence | `schema_version` 2(workflow), `meta.viewBox` 없음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]
| R-ID / T-ID | 근거 (archify@a406594 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | `SKILL.md:14` | 텍스트. 폴더 규칙·`meta.output` 해석 코드는 읽지 않음(행 7) |
| R-02 | `renderers/shared/cli.mjs:81`→`output-path.mjs:323` `validateAuthoredOutputPath`, 5개 `schemas/*.schema.json`의 `meta.required`, `authoring-defaults.md:39` | 진단 코드는 `authoring-enforcement-demo.out.txt`. 필수 목록은 스키마를 파이썬으로 열거. 문서와 구현 차이는 아래 |
| R-03 | `renderers/shared/validator.mjs:38` `validateSchema`, `schemas/common.schema.json:6-30`, `architecture.schema.json:105-112` | 데모 실행 + 스키마 읽음 |
| R-04 | `repository-authoring.md:10-25`(C-06) | 텍스트. `HEAD`·`status`를 검사하는 코드는 `repository-evidence.mjs`에 없다(문자열 검색 결과 `git status` 호출 없음) |
| R-05 | C-01, C-03, C-04, `repository-evidence.mjs:167-240` | 데모 5건 실행 + 코드 읽음 |
| R-06 | C-02, C-03, `repository-evidence.mjs:99-118, 275-372` | 데모 5건 + 코드 읽음 |
| R-07 | `repository-authoring.md:76-90`, `schemas/waterfall.schema.json:25,59`, `timeline.schema.json:25,59` | 지시문 텍스트, `meta.evidence` 열거는 스키마 |
| R-08 | `repository-evidence.mjs:374-379`(총 근거 0건일 때만 실패), `authoring-enforcement-demo.out.txt` `ok-with-evidence` | 실행 확인 |
| R-09~R-12 | `repository-authoring.md:27-74`, `SKILL.md:36-37`, `authoring-defaults.md:27-31` | 텍스트 |
| R-13 | `SKILL.md:38`, `renderers/erd/render-erd.mjs:1108` | 텍스트, ERD 진단은 코드만 읽음(실행 안 함) |
| R-14, R-15 | `authoring-defaults.md:5-11` | 텍스트 |
| R-16, R-17 | `authoring-defaults.md:13-25` | 텍스트 |
| R-18 | `renderers/shared/desktop-readability.mjs:7` | 상수 한 줄만 확인. 나머지 수치의 강제는 미탐색 |
| R-19 | `authoring-defaults.md:35-39`, `authoring-contract.md:125-149`, C-05, `schemas/common.schema.json:21-29` | 데모 + 텍스트 |
| R-20 | `authoring-defaults.md:41-55`, `schemas/workflow.schema.json`(`schema_version` enum), `lifecycle.schema.json`, `dataflow.schema.json` | 텍스트 + 스키마 |
| R-21 | `SKILL.md:39-47`, `bin/archify.mjs:2197` | 텍스트 + 사용법 문자열 |
| R-22 | `authoring-contract.md:62-123`, `schemas/common.schema.json:10-14`, `renderers/shared/i18n.mjs:257` | 데모(`locale-unbundled`) + 텍스트 |
| R-23 | `authoring-contract.md:627-645`, `SKILL.md:75`, `schemas/common.schema.json:74` | 텍스트 |
| T-01~T-09 | `artifacts/archify/spec-demos/authoring-enforcement-demo.out.txt` | 설치본 실행 |

문서와 구현의 차이:
- `authoring-defaults.md:39`는 `meta.output`을 "required"라고 하지만 스키마는 architecture·workflow·sequence·dataflow·lifecycle만 필수이고 class·erd·tree·timeline·waterfall은 선택이다. 선택일 때 기본 출력 이름은 `<type>.html`이다(`cli.mjs:88-93`). 구현을 사실로 썼다.
- `authoring-contract.md:545-548`의 "Repository evidence"는 `sources`를 Architecture·Workflow·Data Flow·Sequence·Lifecycle 컬렉션으로 나열하지만, 코드는 10개 타입 모두(`EVIDENCE_NODE_COLLECTIONS`)와 스키마가 허용한다.
- `repository-authoring.md`는 모든 저장소 기반 요소에 근거를 요구하지만(R-08) 코드는 총 1건 이상만 확인한다.

### 2.2 코드 읽는 순서 [선택]
`SKILL.md:32-47` → `repository-authoring.md` → `authoring-defaults.md` → (강제 확인) `cli.mjs:80-86` `loadDiagram` → `validator.mjs:38` → `repository-evidence.mjs:155`.

## 적용 메모 [선택]
없음.
