---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
sources:
  - skills/ppt-master/references/image-base.md
  - skills/ppt-master/references/image-generator.md
  - skills/ppt-master/references/image-searcher.md
  - skills/ppt-master/references/svg-image-embedding.md
  - skills/ppt-master/references/strategist-image.md
  - skills/ppt-master/references/executor-image.md
  - skills/ppt-master/references/executor-web-image.md
  - skills/ppt-master/scripts/docs/image.md
  - skills/ppt-master/scripts/image_gen.py
  - skills/ppt-master/scripts/image_search.py
  - skills/ppt-master/scripts/image_treat.py
  - skills/ppt-master/scripts/slice_images.py
  - skills/ppt-master/scripts/analyze_images.py
  - skills/ppt-master/scripts/resource_paths.py
  - skills/ppt-master/scripts/project_management/project_specs.py
  - skills/ppt-master/scripts/svg_quality/checker.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py
  - skills/ppt-master/scripts/svg_to_pptx/drawingml/utils.py
  - skills/ppt-master/workflows/generate-pptx.md
depends:
  - ../capabilities/generate-default-pipeline.md
  - ../capabilities/svg-authoring-and-quality.md
status: ready
---

# 이미지 파일 규약 (호환성 계약)

> `design_spec.md §VIII`의 이미지 행이 선언한 이미지를 외부 구현이 `images/<filename>`으로 만들 때, 나머지 시스템(Strategist spec, Executor SVG, `svg_quality_checker.py`, exporter)과 호환되도록 파일 위치·이름·형식·manifest 필드·`Status` 기록을 정하는 계약이다.

<!--
이 스펙은 이미지 "생성" 방법(provider API, 검색 provider, 슬라이스 알고리즘 내부)을 다루지 않는다. 사용자 결정(2026-11-17): 이미지 생성은 외부 API를 직접 구현하고 이 레포의 `image_gen.py`·backend·검색 provider는 쓰지 않는다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. Strategist(Step 4)가 `design_spec.md §VIII` 표에 이미지 행을 쓰고(`Status: Pending`), 배치된 행만 `spec_lock.md images`에 `images/<filename> | source=<Acquire Via> | crop=<adaptive|no-crop>`로 투영한다.
2. Step 5 트리거(`ai`/`web`/`slice` 행 또는 `Derived from` 파생 대기가 있음, 선행 스펙 R-29)에서, 우리 구현이 행마다 `<project>/images/<filename>`을 만든다. `ai`면 `image_prompts.json` 항목을, `web`이면 `image_sources.json` 항목을 함께 쓴다.
3. 우리 구현(또는 agent)이 각 §VIII 행의 `Status`를 terminal 값으로 직접 고쳐 쓴다. 도구는 자기 manifest 항목만 갱신하고 `design_spec.md`는 건드리지 않는다(R-14).
4. 파생 행(`Derived from …; treatment=…`)은 부모가 사용 가능해진 뒤 만든다. 부모가 `image_sources.json`에 있으면 파생 항목에 출처가 복사된다(R-18).
5. `analyze_images.py <project>/images`가 `analysis/image_analysis.csv`를 통째로 다시 쓴다(R-19). Step 6 Executor는 파일과 manifest를 읽어 `svg_output/*.svg`에 `<image href="../images/<filename>" …/>`를 쓰고, `attribution-required` 이미지에는 SVG `<text>` 크레딧을 넣는다(R-20, R-12).
6. 최종 checker가 §VIII 행 ↔ `spec_lock.md images` ↔ 실제 파일 ↔ `<image href>` ↔ provenance를 닫는다(R-21).
7. Step 7 직전 Image readiness GATE: 필수 행이 `Needs-Manual`이면 기대 파일이 모두 있어야 첫 명령을 실행한다(R-23).

### 1.2 범위·통합 지점

- 제공: 이미지 한 장당 호환 가능한 (행, 파일, manifest 항목, Status, SVG 참조)의 묶음 규약. 아래 "호환 최소셋" 표.
- 제외: provider별 API 호출(`scripts/image_backends/`), 웹 검색 provider(`scripts/image_sources/`, `image_search.py` 내부 랭킹), `slice_images.py` 키 제거·trim 알고리즘, `image_gen.py --manifest` 실행기의 동시성·재시도. 위치만 안내한다.
- 외부 의존·선행 계약: 선행 스펙 `generate-default-pipeline.md`(C1 디렉터리, C2 `design_spec`/`spec_lock`, Step 5 트리거 R-29~R-31, Step 7 gate R-42), `svg-authoring-and-quality.md`(`<image>` 문법, final 검사). 이 스펙은 두 파일의 이미지 관련 부분의 계약만 추가한다.
- 소유 상태·부작용: `images/` 아래 비트맵, `images/image_prompts.json`·`image_prompts.md`·`image_queries.json`·`image_sources.json`, `analysis/image_analysis.csv`(파생 view). §VIII `Status` 열과 `spec_lock.md images`는 agent(Strategist/Step 5 담당)가 소유한다.

**호환 최소셋** (원본 동작에서 도출. "선택"은 원본이 허용하지만 필수가 아닌 것)

| 우리 구현이 하는 일 | 최소 계약 | 필수/선택 | R-ID |
|---|---|---|---|
| 파일 쓰기 | `<project>/images/<filename>` 에 §VIII `Filename`과 같은 bare 이름, 지원 확장자(jpg/jpeg/png/webp/gif/bmp/tif/tiff/svg/emf/wmf), 열리는 유효 이미지, 확장자와 실제 포맷 일치 | 필수 | R-07 |
| §VIII `Status` 기록 | 행의 `Acquire Via`에 맞는 terminal 값(`ai`·`slice`→`Generated`, `web`→`Sourced`, `user`→`Existing`, `placeholder`→`Placeholder`; 어느 행이든 `Needs-Manual` 가능). `Pending`/`Failed`로 export하면 final 오류 | 필수 | R-03, R-04, R-14 |
| `spec_lock.md images` | 배치된 행마다 `images/<filename> | source=<Acquire Via> | crop=<§VIII Crop Policy>`. Illustration Sheet·`Type: Source` 행은 넣지 않는다. 우리 구현이 새 행을 만들면 이 행도 같이 써야 한다 | 필수 | R-06 |
| `image_prompts.json` (`ai` 행이 하나라도 있을 때만) | top-level `items`(비어 있지 않은 배열). 항목마다 `filename`, `prompt`, `aspect_ratio`(`W:H`), `status` 4개가 비어 있지 않은 문자열. `status` ∈ {`Pending`,`Generated`,`Failed`,`Needs-Manual`}(대소문자 일치) | 필수(ai 행 있을 때) | R-08, R-09 |
| `image_prompts.json` 나머지 | `project`, `generated_at`, `deck_rendering`, `color_scheme`, `items[].page_role/text_policy/type/image_size/model/alt_text/purpose/slice_grid/slice_names/last_error` | 선택(로더는 허용·검증만. `page_role` 누락은 `local`, `text_policy` 누락은 `none`으로 읽고 경고) | R-08 |
| `image_sources.json` (`web` 행이 `Sourced`일 때, 크레딧 있는 `user` 자산, 파생 부모가 출처 있음) | top-level `items` 배열. 항목마다 bare·유일한 `filename`, `license_tier` ∈ {`no-attribution`,`attribution-required`,`manual`}, `manual`이 아니면 비어 있지 않은 `attribution_text`, `attribution-required`면 비어 있지 않은 `author`. 크레딧 검사가 쓰므로 CC 라이선스면 `license_name`에 CC 문자열 | 필수(해당 행) | R-11, R-12 |
| `image_sources.json` 나머지 | `provider`, `source_page_url`, `download_url`, `license_url`, `width`, `height`, `selection_method`, `matched_query`, `stage` 등 | 선택(검사기는 읽지 않음) | R-11 |
| `analyze_images.py` 실행 | 모든 파일이 `images/`에 놓인 뒤 한 번 실행해 CSV를 새로 쓴다 | 필수(Step 4/5 gate 용) | R-19 |
| `image_prompts.md` | `image_gen.py --render-md`가 JSON을 렌더한 읽기 전용 사이드카. 우리가 대체 구현하면 사람이 붙여넣을 prompt 블록만 있으면 된다 | 선택(수동 경로의 handoff용. 검사기는 안 읽음) | R-10 |
| 파생 행 | 새 파일은 부모와 다른 이름, 부모 보존, 확장자 `.png`(불투명 부모면 `.jpg`도 가능) | 파생 행이 있을 때 | R-18 |

### 1.3 인터페이스와 데이터 의미

#### (a) `design_spec.md §VIII` 행

헤더는 `## VIII. Image Resource List`(`^##\s+VIII\.\s+Image Resource List`)이며, 그 절 안의 첫 `|`로 시작하는 표에서 `Filename` 헤더를 가진 줄이 열 이름이 된다. 열 이름은 원문 그대로 매칭된다(`Filename`, `Acquire Via`, `Status`, `Crop Policy`, `Image pattern`, `Type`, `Reference`). `Purpose`와 `Type`을 한 열로 합친 `Purpose / Type` 표기가 image-base.md에 있지만, 검사기는 `Type` 열 이름으로 읽으므로 `Type`이 따로 있어야 `Illustration Sheet`/`Source` 판정이 동작한다(R-01, 2.1).

| 열 | 값·허용 범위 | 의미·소비자 |
|---|---|---|
| `Filename` | `<name>.<ext>` 또는 `images/<name>.<ext>`만 허용(그 외 경로 조각은 `planned_image_invalid_filename` 오류). 행 사이 유일해야 함(대소문자 구분은 검사기 기준 정확 일치) | 모든 소비자의 키. 기준 이름은 basename |
| `Dimensions` | `800x600` 같은 계획 크기(+ 선택 `Ratio`). 도구가 파일을 만든 뒤 실제 픽셀을 되써야 한다(image-generator §7 "backfill the actual pixels"). 검사기는 읽지 않는다 | Strategist/Executor 배치 참고. 실제 크기는 CSV가 정답 |
| `Purpose`, `Type` | `Type`은 자유 문자열이되 예약어 둘: `Illustration Sheet`(배치 안 되는 슬라이스 원본), `Source`(배치 안 되고 파생만 만드는 원본). 그 밖은 `Photography`, `Illustrated icon` 등 | 예약어는 checker가 대소문자 무시로 판정(R-16, R-17) |
| `Image pattern` | 비어 있지 않은 글. catalog id(`#P1-02`)가 있으면 순서가 lock `pattern=`과 비교된다 | 현재 계약(`Crop Policy` 열이 있을 때)에서 비어 있으면 오류. 배치 힌트일 뿐 이미지 파일과는 무관 |
| `Crop Policy` | `adaptive` / `no-crop`(소문자 비교, 다른 값은 오류) | `no-crop`이면 SVG에 잘림 없는 완전 표시 1회 필요(R-22) |
| `Acquire Via` | `ai` / `web` / `slice` / `user` / `placeholder` (문서). 검사기는 `formula`도 허용(R-02) | 누가 파일을 만드는가(표 b) |
| `Status` | `Pending` / `Failed` / `Needs-Selection`(web 중간 상태) / `Generated` / `Sourced` / `Needs-Manual` / `Existing` / `Placeholder` (+ `formula` 행의 `Rendered`). enum 원본은 `svg-image-embedding.md`. 검사기는 소문자 비교 | R-03 |
| `Reference` | `ai`: 시각 의도 문장(prompt 아님). `web`: 정확한 주제·구도 의도. `slice`: 부모 시트와 칸. 파생: `Derived from <bare filename>; treatment=<op>; …` | 파생 판정과 `Source` 행의 자식 존재 검사가 이 열을 읽는다(R-17, R-18) |

AI 행의 조건부 필드(`page_role`, `text_policy`, `image_size`)는 §VIII에 쓰지 않고 `image_prompts.json` 항목 필드이다.

#### (b) `Acquire Via`별 제작 주체와 Status 전이

| `Acquire Via` | 누가 어떻게 파일을 만드는가 | 시작 | terminal | 실패·수동 | manifest |
|---|---|---|---|---|---|
| `ai` | 우리 구현이 `aspect_ratio`에 맞는 이미지를 `images/<filename>`에 쓴다. Default에서는 확정된 `AI Image Acquisition Path`(`design_spec.md §I`)가 `api`/`auto`/`host-native`/`manual` 중 하나여야 한다 | `Pending` | `Generated` | 소진 시 `Failed`로 두고 사용자에게 3택(재시도/수동 생성/취소); 수동 확정 후에만 `Needs-Manual`. 취소하면 `ai`와 의존 `slice` 행을 §VIII와 lock에서 제거(Step 4 post-confirmation override) | `image_prompts.json` 항목 필수 |
| `slice` | 부모 `Illustration Sheet`(`ai`)가 `Generated`가 된 뒤 `slice_images.py`로 칸 파일을 `images/<name>.png`로 만든다. 우리 구현이 시트를 만든 뒤에도 이 CLI를 쓰거나, 같은 출력(투명 RGBA PNG, 이름 = `slice_names`)을 직접 낸다 | `Pending` | `Generated` | 시트가 없으면 `Needs-Manual`(슬라이스 파일을 손으로 놓지 않고 시트를 놓고 재실행) | 부모 항목의 `slice_grid`+`slice_names`(함께 있어야 함) |
| `web` | 우리 구현이 허가된 라이선스(CC0·PD·CC BY·CC BY-SA 등)의 원본 한 장을 `images/<filename>`에 받고 출처를 기록 | `Pending` →(비전이면 `Needs-Selection`) | `Sourced` | 후보 소진은 `Needs-Manual`, provider/네트워크 실패는 재시도 가능한 `Failed`, 승격한 원본이 게이트 실패면 `Needs-Selection` 유지 | `image_sources.json` 항목 필수(검사기), 선택적으로 `image_queries.json` |
| `user` | 사용자가 준 파일을 `images/`에 놓는다(`import-sources`가 비트맵을 `images/`로 복사, 선행 R-13) | `Existing` | `Existing` | 파일이 없으면 `Needs-Manual` | 라이선스 조건이 함께 오면 `image_sources.json`에 등록 |
| `placeholder` | 만들지 않는다. SVG가 점선 `<rect stroke-dasharray="8,4">`+설명 텍스트를 그린다 | `Placeholder` | `Placeholder` | — | 없음 |
| (파생) | `Reference: Derived from …`가 있는 행. `image_treat.py`로 부모에서 `.png` 생성. 부모는 비파생 `user`/`web`/`ai`/`slice` 행이어야 함(placeholder·연쇄·순환·자기참조 금지) | `Pending` | 부모를 상속: `user→Existing`, `web→Sourced`, `ai`/`slice→Generated` | 부모가 쓸 수 없으면 `Needs-Manual` | 부모 항목이 있으면 `derived_from`·`treatments` 추가 |

전이 규칙(검증용으로 한 줄): `Pending →(성공) terminal`, `Pending →(실패) Failed →(재시도) terminal`, `Needs-Selection →(승격) Sourced | (소진) Pending(새 질의) | Needs-Manual`, `Needs-Manual →(파일 도착·검증) Existing/Generated/Sourced`.

#### (c) 파일 위치·이름·형식

| 항목 | 규약 |
|---|---|
| 위치 | `<project>/images/<filename>`. 하위 폴더 금지(lock 경로는 `images/<filename>` 정확히 두 구간) |
| 이름 | `/ \ :` 없는 bare 이름, `..` 금지. manifest 안에서 대소문자 무시 중복·같은 stem 중복 금지(`image_prompts.json`) |
| 확장자 | SVG `<image>` 로더가 허용하는 것: bmp, emf, gif, jpg/jpeg, png, svg, tif/tiff, webp, wmf. lock 경로도 이 확장자만 이미지 경로로 본다. `analyze_images.py`는 jpg/jpeg/png/gif/webp/bmp/tiff/tif를 직접 읽고 emf/wmf/svg는 `images/image_manifest.json` 항목이 있어야 분석한다 |
| 권장 형식(문서) | 불투명 AI 이미지는 `.jpg`, 알파·키가 필요한 것(일러스트 시트와 그 슬라이스, 투명 레이어)은 `.png`. `image_gen.py` manifest는 항목 `filename` 확장자 포맷으로 저장(`.jpg`는 JPEG 품질 90). 검사기는 이 권장을 강제하지 않고 "확장자 = 실제 포맷"만 본다 |
| 투명 PNG | 슬라이스 결과(`--alpha`)와 `image_treat.py` 파생(`.png`). 투명 소스는 `.jpg` 파생이 거부된다 |
| 슬라이스 시트 | `Type: Illustration Sheet`, `Acquire Via: ai`, 키색(`#00FF00`/`#0000FF`/`#FF0000`) 평면 배경. SVG에서 참조 금지, lock에 금지 |
| 유효성 | 비어 있거나 손상되거나 확장자와 포맷이 다르면 final 검사 오류(`external image … is empty, corrupt, or does not match`) |
| 크기 | 표시 크기의 약 1.5~2배 픽셀을 권장(문서). 검사기는 렌더 배율 2.0 초과면 경고(blocking 아님) |

#### (d) `image_prompts.json` / `image_sources.json` / `image_prompts.md`

`image_prompts.json` top-level: `project`, `generated_at`, `deck_rendering`(각각 있으면 비어 있지 않은 문자열), `color_scheme`(있으면 비어 있지 않은 문자열 쌍의 객체), `items`(필수, 비어 있지 않은 배열).

| `items[]` 필드 | 필수 | 검증 |
|---|---|---|
| `filename` | 필수 | 확장자 있는 bare 이름. 대소문자 무시 중복·stem 중복 금지 |
| `prompt` | 필수 | 비어 있지 않은 문자열 |
| `aspect_ratio` | 필수 | 임의의 양수 `W:H`(소수 허용). 형식 오류만 거부 |
| `status` | 필수 | 4값 중 하나 |
| `image_size` | 선택 | `512px`/`1K`/`2K`/`4K` 정규화 후 |
| `page_role`, `text_policy` | 선택(누락 허용) | `local`/`hero_page`(+legacy `full_page`), `none`/`embedded` |
| `type` | 선택 | 11개 구조 타입 + legacy 값. `illustration sheet`/`sheet`는 항목에서 제거(시트 항목은 `type` 생략) |
| `model`, `alt_text`, `purpose` | 선택 | 있으면 비어 있지 않은 문자열 |
| `slice_grid`+`slice_names` | 쌍으로만 | `RxC`; 이름 수 = R*C, 모두 유일, 확장자는 생략 또는 `.png`, 출력명이 다른 항목의 `filename`과 충돌 금지 |
| `last_error` | 선택 | 문자열(실패 사유) |

`image_prompts.md`는 `image_prompts.json`에서 `render_manifest_md`가 만드는 읽기 전용 렌더(속성 표 + `**Prompt**` + `**Alt Text**`). 손으로 고치지 않고 JSON 변경 뒤 다시 렌더한다.

`image_sources.json`:

| 필드 | 필수 | 의미 |
|---|---|---|
| `items` | 필수 | 객체 배열. 각 `filename`은 bare·유일(깨지면 final 검사 오류) |
| `items[].filename` | 필수 | `images/` 안 파일 이름 |
| `items[].license_tier` | web+Sourced 행은 필수 | `no-attribution`(CC0, PD, Pexels, Pixabay), `attribution-required`(CC BY, CC BY-SA, 출처 크레딧 요구), `manual`(`--from-url` 사용자 지정, 권리는 사용자 책임). 사용자가 준 파일은 `attribution-required`(CC BY/BY-SA) 또는 `no-attribution`(CC0, PD, 본인 작업) |
| `items[].attribution_text` | `manual` 외에는 필수 | 크레딧의 원천 문장 |
| `items[].author` | `attribution-required`면 필수 | 크레딧 바인딩에 쓰임 |
| `items[].license_name` | 크레딧 검사가 읽음 | CC 포함이면 `CC BY`/`CC BY-SA` 토큰을 크레딧에 요구 |
| `items[].attribution_required` (bool) | 선택 | true여도 크레딧 요구(tier와 OR) |
| 그 밖 `provider`, `title`, `source_page_url`, `download_url`, `license_url`, `width`, `height`, `selection_method`(`visual-thumbnail`/`metadata-ranked`), `matched_query`, `stage`, `metadata_dimensions`, `slide`, `purpose`, `orientation`, `search_query`, `status` | 선택 | 검사기는 읽지 않는다 |
| `items[].derived_from`, `items[].treatments` | 파생에서 도구가 추가 | 부모 파일명, 적용 연산 목록 |
| top-level `license_verification`, `generated_at` | 선택 | 도구가 채움 |

`image_queries.json`(web 배치 입력)은 우리가 `image_search.py`를 안 쓰므로 필요 없다. 쓴다면 항목 필수는 `filename`, `query`, `status`다.

#### (e) `analysis/image_analysis.csv`

`analyze_images.py <project>/images`가 `<project>/analysis/image_analysis.csv`를 만든다(`images/`의 형제 `analysis/`). 실행할 때마다 전체를 새로 쓰고(임시 파일 후 교체), 이미지가 없으면 헤더만 쓴다. 읽을 수 없는 지원 확장자 파일이 있으면 CSV는 쓰되 exit 1이다. 디렉터리가 없거나 폴더가 아니면 exit 1.

열: `No, Filename, Width, Height, AspectRatio, PixelAspectRatio, SourceDisplayRatio, RatioSource, Format, HasTransparentPixels, UsageCount, DisplayRatioVariants, AssetKind, SvgRenderable, PptxNativeSupported, SizeKB, Category`. 크기는 EXIF 방향 보정 후 값, `Category`는 비율 구간(`Ultra-wide`>2.0, `Wide landscape`>1.5, `Standard landscape`>1.2, `Near square`>0.8, `Portrait`). 시점: Step 4에서 사용자 이미지가 있을 때 §VIII 전(선행 R-16), Step 5 파생 후 SVG 전 한 번, Needs-Manual 파일이 도착한 뒤 다시.

#### (f) 파생 이미지

| 항목 | 규칙 |
|---|---|
| 선언 | 행의 `Reference`에 `Derived from <bare filename>; treatment=<operation>; …`. `Acquire Via` 분류보다 먼저 파생 여부를 본다 |
| 부모 | §VIII의 다른 비파생 행(`user`/`web`/`ai`/`slice`). placeholder·연쇄·순환·자기참조 금지 |
| 만드는 법 | 결정적 처리만 `image_treat.py <project_path> <source> --output <new>`: `--brightness`, `--contrast`, `--desaturate`/`--grayscale`/`--duotone`(상호 배타), `--blur`, `--fit WxH`(축소만, 업스케일 금지). 적용 순서 고정. 효과가 하나도 없으면 오류 |
| 출력 | `images/` 아래 새 이름의 `.png`(불투명 소스면 새 `.jpg` 가능). 기존 파일·원본 덮어쓰기 거부. 입력·출력은 bare 이름 |
| 출처 | 부모가 `image_sources.json`에 있으면 새 항목(`filename`=출력, `attribution_text`의 선두 부모 이름 치환, `derived_from`, `treatments`)을 쓴다. 출력이 이미 기록돼 있으면 오류 |
| Status | 부모를 상속(`Existing`/`Sourced`/`Generated`) |
| SVG 네이티브로 하는 것 | 크롭·클립·회전·불투명도·그림자·스크림은 파생 파일이 아니라 SVG가 한다. 파생에 굽지 않는다 |
| Source 행 | 원본이 어떤 페이지에도 안 쓰이면 그 행 `Type: Source`. lock·SVG 금지, 자식 행이 최소 하나 있어야 함 |
| 등록 레이어 파생 | image-generator §4.4(clean base + subject RGBA). 전체 캔버스 멤버는 `no-crop`이고 자르거나 trim하지 않는다. 이 스펙은 형식 계약만 언급한다 |

#### (g) SVG 참조와 크레딧

| 항목 | 규칙 |
|---|---|
| href | `<image href="../images/<filename>" x y width height preserveAspectRatio=…/>`. `href`(또는 `xlink:href`) 정확히 하나, 비어 있지 않음. 스킴·쿼리·프래그먼트·절대경로 없음, SVG 위치 기준 상대경로가 프로젝트 안의 실제 파일로 풀려야 함. `images/`·루트 추측 없음 |
| 경로 형태 | 문서·lock 계약은 `../images/<filename>`(svg_output에서). 검사기는 lock 경로(`images/<filename>`)로 풀린 파일과 같은 파일이어야 통과(`locked_image_reference_mismatch`) |
| 임베드 | `svg_output/`에는 `data:` href를 쓰지 않는다. 현재 계약 프로젝트에서는 `svg_inline_image_untracked` 오류. `data:` 형태는 `finalize_svg.py`가 `svg_final/`에 만드는 미리보기 |
| `width`/`height` | 명시적 양수 필수 |
| `preserveAspectRatio` | 생략 시 `xMidYMid meet`. 허용: `none` 단독, 또는 9개 anchor + `meet`/`slice` |
| 크롭 | `adaptive`: `meet` 또는 초점 안전 `slice`. `no-crop`: `none`·`clip-path`·`mask`·오버플로 클립·중첩 크롭 뷰포트 금지, 완전 표시 1개 필수(R-22) |
| 크레딧 | `attribution-required` 이미지는 그 이미지를 쓰는 모든 SVG에 보이는 `<text>`로 author + (CC면) `CC BY`/`CC BY-SA`. SVG `<title>`/`<desc>`, speaker notes, `total.md`에 두지 않는다. `no-attribution`/`manual`은 `<image>`만 |
| Needs-Manual | 파일이 없으면 점선 placeholder + 설명. 파일이 있는 `Needs-Manual` 행은 `<image>`로 참조돼야 한다(`locked_image_unreferenced`) |

checker가 닫는 조건은 R-21, 크레딧은 R-12.

#### (h) Step 7 Image readiness GATE

필수 행이 `Needs-Manual`이면 기대 파일과 slice 출력이 모두 `images/`에 있어야 Step 7의 첫 명령이 실행된다. 없으면 정확한 파일명을 나열하고 `finalize_svg.py`·`svg_to_pptx.py`를 돌리지 않으며 점선 placeholder를 내보내지 않는다. 파일이 도착하면 `analyze_images.py` 재실행 → placeholder 교체 → `no-crop` 컨테이너를 실제 비율에 맞춤 → final checker 재실행 → §VIII 행을 `Existing`/`Generated`/`Sourced`로 되써 맞춤(R-23).

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | §VIII 표 파싱 | `## VIII. Image Resource List` 절의 첫 표에서 `Filename` 헤더를 가진 줄이 열 이름이 되고, 구분선과 빈 행은 건너뛴다. 열은 이름으로 읽는다(`Type`, `Acquire Via`, `Status`, `Crop Policy`, `Image pattern`, `Reference`). 구버전 `Layout pattern`은 `Image pattern`이 비었을 때만 대체로 읽는다. 문서의 `Purpose / Type` 합친 표기는 코드가 `Type` 열을 따로 찾으므로 열을 나눠 쓴다 | 코드 확인 |
| R-02 | `Acquire Via` 값 | 문서는 `ai/web/slice/user/placeholder` 다섯 개를 말하고, checker·lock 파서는 여기에 `formula`를 더 허용한다(`formula`의 terminal은 `rendered`/`needs-manual`, 항상 `no-crop` 취급). 그 밖의 값은 `planned_image_invalid_acquisition` 오류 | 코드 확인 |
| R-03 | terminal Status 매핑 | checker 기준 terminal: `ai`→{generated, needs-manual}, `web`→{sourced, needs-manual}, `user`→{existing, needs-manual}, `slice`→{generated, needs-manual}, `placeholder`→{placeholder}, `formula`→{rendered, needs-manual}. 이 밖은 `planned_image_status_mismatch` 오류. enum 밖 값은 `planned_image_invalid_status` 오류 | 코드 확인 |
| R-04 | final 검사 시 `Pending`/`Failed` 행(`Needs-Selection`은 enum 밖이므로 `invalid_status`) | 각각 `planned_image_not_terminal` 오류로 final 보고서가 error>0이 되어 exporter가 막힌다(선행 R-36·R-42). 즉 Step 5 끝에는 `Pending`/`Failed`/`Needs-Selection`이 남지 않아야 한다 | 코드 확인 |
| R-05 | `Crop Policy`·`Image pattern` | `Crop Policy` 열이 있는 §VIII(또는 lock 행이 `legacy=false`)이면 모든 행의 `Crop Policy`는 `adaptive`/`no-crop`, `Image pattern`은 비어 있지 않아야 한다(각 `planned_image_invalid_crop_policy`, `planned_image_missing_pattern`) | 코드 확인 |
| R-06 | `spec_lock.md images` 투영 | 배치된 행(`Type`이 `Illustration Sheet`/`Source`가 아니고 `Acquire Via`가 유효)마다 lock에 정확히 한 행이 있다. 값은 `images/<filename> \| source=<via> \| crop=<policy>`(`pattern=…` 선택, 알 수 없는 필드·누락 필드·`images/<filename>` 이외 경로는 파싱 오류). `source`·`crop`은 §VIII 값과 같아야 하고, `pattern=`이 있으면 catalog id 순서(없으면 정규화한 글)가 §VIII와 같아야 한다. lock에만 있는 이미지, §VIII에만 있는 배치 행, 한 파일의 lock 중복 행은 각각 오류 | 코드 확인 |
| R-07 | `images/<filename>` 파일 | `Status`가 `Existing`/`Generated`/`Sourced`/`Rendered`면 lock 경로의 파일이 있어야 한다(`locked_image_file_missing`). `Needs-Manual`·`Placeholder`는 파일이 없어도 이 검사에서는 통과(Step 7 gate가 따로 막음). 파일은 확장자와 실제 포맷이 맞는 유효 이미지여야 final 검사의 `<image>` 로드를 통과 | 코드 확인 |
| R-08 | `image_prompts.json`을 `image_gen.py`가 읽을 때(우리 구현이 이 도구를 안 써도 같은 형식으로 쓰면 도구와 호환) | 1.3(d) 표대로 검증하고 실패하면 `ValueError`로 중단. 필수 4개 필드가 비거나 `status`가 4값 밖이면 거부, 필수·선택 외 필드는 로더가 무시한다 | 코드 확인 |
| R-09 | `image_prompts.json`의 `status` 쓰기 | 도구는 성공 시 `Generated`(+`last_error` 제거), 실패 시 `Failed`+`last_error`(500자 절단), 이미 `Generated`인 항목은 파일 검증에 실패하면 `Failed`로 되돌린다. `Needs-Manual` 항목은 건너뛴다. 항목의 `status`를 `Pending`으로 되돌리면 같은 경로를 재실행해 다시 만든다(variant). 우리 구현이 이 파일을 직접 쓸 때도 같은 전이를 지킨다 | 코드 확인 |
| R-10 | `image_prompts.md` | JSON에서 렌더한 읽기 전용 사이드카. 수동 경로·`host-native` 경로에서 사람/호스트에게 prompt를 넘기는 용도. 검사기와 exporter는 읽지 않는다 | 코드 확인 |
| R-11 | `image_sources.json` 쓰기 | 한 항목은 `filename` 키로 추가하거나 교체한다(대소문자만 다른 기존 이름이 있으면 오류, 읽을 수 없는 기존 파일이 있으면 쓰기를 막음, 원자적 교체). final 검사는 파일이 객체이고 `items`가 객체 배열이며 모든 `filename`이 bare·유일해야 한다고 본다 | 코드 확인 |
| R-12 | 크레딧 검사 | `image_sources.json`의 항목 중 `attribution_required`가 참이거나 `license_tier == attribution-required`인 항목의 파일이 한 SVG에서 보이는 `<image>`로 참조되면, 그 SVG의 보이는 `<text>` 중 하나가 항목 `author`(대소문자 무시 부분 문자열)를 포함하고, `license_name`에 CC가 있으면 `CC BY`(`BY-SA`면 `CC BY-SA`) 토큰도 포함해야 한다. 아니면 error. 이는 web 행에만 걸리지 않고 manifest에 있는 모든 파일(user, 파생)에 적용된다. 크레딧 하나가 여러 이미지를 덮는 일반 토큰은 인정되지 않는다 | 코드 확인 |
| R-13 | web+`Sourced` 행의 provenance | `image_sources.json` 파일이 없으면 `image_sources_missing`, 항목이 없으면 `sourced_image_missing_provenance`, `license_tier`가 3값 밖이면 `…invalid_license_tier`, `manual` 아닌데 `attribution_text`가 비면 `…missing_attribution_text`, `attribution-required`인데 `author`가 비면 `…missing_author` 오류 | 코드 확인 |
| R-14 | Status 되돌려 쓰기 | **agent(또는 우리 구현)가 각 §VIII 행의 terminal `Status`를 직접 되돌려 써야 한다. 도구는 자기 manifest만 갱신한다.** `image_gen.py`는 `image_prompts.json`의 `status`만, `image_search.py`는 `image_queries.json`/`image_sources.json`만 쓰고, 어느 도구도 `design_spec.md`·`spec_lock.md`를 쓰지 않는다(`image_gen.py`는 읽기만). Step 5 검증 4번이 "각 행의 terminal Status를 직접 써라, 도구는 자기 manifest만 갱신한다"고 명시한다. 파일 도착 후 `Needs-Manual` → `Existing`/`Generated`/`Sourced`로 맞추는 것도 같다 | 코드 확인(도구가 쓰지 않음), 문서 선언(의무) |
| R-15 | `Needs-Manual` 의미 | acquisition의 terminal이지 export의 terminal이 아니다. Default에서 `ai`는 수동 확정(`AI Image Acquisition Path: manual` 또는 소진 후 사용자의 "수동 생성" 선택)이 있을 때만 이 상태가 되고, 그 전에는 `Failed`로 둔다. `web`은 자동 전략 소진 후 `Needs-Manual`로 표시·보고하고 계속한다. `slice`는 부모 시트가 없을 때 | 코드 확인(문서 선언) |
| R-16 | Illustration Sheet / slice | 시트 행(`Type: Illustration Sheet`)은 lock에 없어야 하고(`sheet_in_lock`), 어느 SVG도 참조하면 안 되고(`sheet_referenced`), `Generated`인데 파일이 없으면 오류(`sheet_file_missing`). 슬라이스 행(`Acquire Via: slice`)은 lock에 있어야 한다. `slice_images.py <sheet> --grid RxC --names a,b,… --trim --alpha --bg KEY --strict-alpha`의 `--names` 수는 R*C이고 `--strict-alpha`는 불완전하면 아무것도 쓰지 않는다. 출력은 `.png`이고 기본 출력 디렉터리는 시트와 같다 | 코드 확인(검사기), 코드 확인(CLI 옵션 정의 `slice_images.py:1186-1231`; 알고리즘은 읽지 않음) |
| R-17 | `Type: Source` 행 | lock에 없어야 하고(`source_in_lock`), SVG가 참조하면 안 되고(`source_referenced`), `Reference`에 `Derived from <이 파일명>`이 있는 행이 최소 하나 있어야 한다(`source_without_derivative`). 부모 이름은 `derived\s+from\s+\`?([^;|\`]+?)\`?\s*(?:;|$)`로 추출해 `Path(...).name`으로 비교 | 코드 확인 |
| R-18 | 파생 생성 | `image_treat.py`는 효과가 없으면 오류, 출력이 기존 파일이거나 `image_sources.json`에 이미 있으면 오류, 원본을 보존한다. 부모가 `image_sources.json`에 있을 때만 파생 항목을 쓴다(없으면 manifest를 건드리지 않음). `--fit WxH`는 축소 전용이며 크롭 배치에서는 슬롯이 아니라 "슬롯을 덮는 비크롭 크기"를 준다 | 코드 확인 |
| R-19 | `analyze_images.py` | 1.3(e). 지원 확장자만 직접 읽는다. CSV는 `analysis/`가 없으면 만든다. 표시 비율이 아니라 EXIF 보정 픽셀 크기를 쓴다 | 코드 확인 |
| R-20 | SVG `<image>` 참조 | 1.3(g). 최종 검사는 모든 보이는 `<image>`에 대해 `href` 단일성, 내부 상대경로 풀이, 형식·바이트 유효성, 명시적 양수 `width`/`height`를 오류로 본다. 표시 배율이 2.0을 넘으면 경고만 한다 | 코드 확인 |
| R-21 | 최종 checker가 닫는 조건(현재 계약: `design_spec.md`에 `<!-- ppt-master-schema: design-spec/v1 -->`가 있을 때) | §VIII 행 ↔ lock 행 ↔ 파일 ↔ `<image href>`: (1) 모든 행이 유효 Filename·Acquire·Status·terminal이고 중복 없음 (2) 배치 행마다 lock 행 있음, 반대도 (3) lock `source`/`crop`/`pattern`이 §VIII와 일치 (4) terminal이 `Existing`/`Generated`/`Sourced`/`Rendered`면 파일 존재 (5) 파일이 있고 `Placeholder`·`Needs-Manual` 외 terminal이면 `svg_output`의 `<image>`가 lock 경로를 참조해야 하며(`locked_image_unreferenced`) 다른 경로 참조는 오류 (6) §VIII에 없는 파일을 SVG가 참조하면 `svg_image_missing_spec` (7) `svg_output`에 인라인 `data:` 이미지가 있으면 오류 (8) `no-crop` 규칙(R-22) (9) web+Sourced provenance(R-13). 검사는 `--quick-generate`, 템플릿 모드, `design_spec.md` 없음, 대상이 디렉터리가 아닌 경우에는 돌지 않는다 | 코드 확인 |
| R-22 | `no-crop` 이미지 | 사용하는 각 SVG 페이지에 잘림 없는 `meet` 배치(정렬이 `none`이 아니고 클립 메커니즘 없음)가 하나 있어야 한다. `preserveAspectRatio="none"`은 렌더 프레임이 소스 비율에서 2% 넘게 왜곡되면 오류(`no_crop_image_fit_mismatch`), 완전 배치가 없는 페이지에서 `slice`나 클립·마스크가 쓰이면 오류(`no_crop_image_clipped`). 이 검사는 `formula` 행에도 적용된다 | 코드 확인 |
| R-23 | Step 7 진입 | 1.3(h). 필수 `Needs-Manual` 행이 있고 기대 파일이 하나라도 없으면 Step 7을 시작하지 않고 파일명을 나열한다. 이 gate는 문서 규칙이며 checker는 파일 없는 `Needs-Manual`을 오류로 보지 않으므로(R-07) 우리 쪽에서 이 gate를 구현해야 한다 | 코드 확인(문서 선언), 코드 확인(검사기가 막지 않음) |
| R-24 | 사용자 자산의 라이선스 | `user` 자산이 저자·라이선스와 함께 오면 `image_sources.json`에 `filename`, `author`, `license_name`, `source_page_url`, `license_tier`, `attribution_text`로 등록하고 SVG 크레딧 규칙(R-12)을 같이 적용한다. 크레딧·라이선스를 `notes/*.md`나 SVG `<title>`/`<desc>`에 두지 않는다 | 코드 확인(문서 선언) |
| R-25 | 외부 생성 이미지의 크기 | 백엔드는 요청 비율의 최근접 크기를 낼 수 있어, 실제 픽셀을 §VIII `Dimensions`에 되쓰고 업스케일로 크기를 맞추지 않는다. 비율이 다르면 Executor가 `Crop Policy`로 맞춘다. 우리가 정확한 `aspect_ratio` 크기로 만들지 못하면 `no-crop` 행은 SVG 컨테이너를 실제 비율에 맞춰야 한다 | 코드 확인(문서 선언) |

- 불변식: terminal 행마다 `Status`와 파일 존재 여부가 R-07과 모순되지 않아야 final 검사를 통과한다. `analysis/image_analysis.csv`는 `images/` 내용의 파생 view이고 저장소가 아니므로 항상 재생성할 수 있다.
- 미결정: 없음. 아래는 원본이 문서와 구현에서 다르게 말하거나 정하지 않은 것이다(구현은 구현을 따른다).
  - **`Acquire Via: formula`(`Status: Rendered`)**: 코드는 허용한다(`project_management/project_specs.py:121-123`의 `_IMAGE_ACQUISITION_SOURCES`, `svg_quality/checker.py:8626`의 `formula: {rendered, needs-manual}`). 문서 enum에는 정의가 없다. 수식은 Strategist가 §IX에 LaTeX 본문을 적고 Executor가 text·inline·block 수식으로 실현하는 경로가 문서의 정본이라(`workflows/generate-pptx.md`의 "Formulas and hyperlinks") 이 스펙의 이미지 파일 규약 범위에서 제외한다. 연동 구현은 `formula` 행을 만들지 않으면 된다.
  - **§VIII `Status`를 되돌려 쓰는 주체**: 도구가 아니라 agent의 직접 편집이다. `references/image-base.md:43`이 "write each resource row's terminal `Status` back yourself, since the tools update only their own manifests"라고 정하고, `update_spec.py`에는 §VIII·`Status`·`Acquire`를 다루는 코드가 없다(`grep -n "VIII\|Status\|Acquire" scripts/update_spec.py` 결과 없음, R-14).
  - **`Needs-Selection`**: 문서 enum에는 있으나 checker의 `valid_statuses`(`checker.py:8612-8620`)에는 없다. 행에 남기면 final 검사가 `planned_image_invalid_status` 오류를 낸다(R-04). 의도 여부는 코드로 정해지지 않으므로 연동 구현은 이 상태를 §VIII에 남기지 않고 끝 상태로 바꾼다.
  - **`Needs-Manual` + 파일 없음 + SVG가 placeholder**: final 검사는 막지 않는다(R-07). exporter도 막지 않는다. `svg_to_pptx/` 안에는 `Needs-Manual`을 다루는 코드가 없고, 프로젝트의 `design_spec.md`를 읽는 곳은 템플릿 구조 코드(`pptx_package/template_structure.py:559`, 템플릿 디렉터리의 `design_spec.md`)뿐이다(`grep -rn -i "needs-manual\|design_spec" scripts/svg_to_pptx`, 메인 확인). 따라서 Step 7 Image readiness GATE(R-23)는 워크플로 규칙일 뿐 도구가 강제하지 않는다. 연동 구현이 내보내기 직전에 §VIII 행과 `images/` 파일을 직접 확인해야 한다.

- 확인 한계: 스크립트를 실행하지 않았다. `image_gen.py`의 backend·`image_search.py`의 provider·랭킹, `slice_images.py`의 알고리즘(키 제거·trim), `image_treat.py`의 픽셀 처리, `project_manager.py validate`가 §VIII를 확인하는 범위는 읽지 않았다. 외부 시스템(이미지 API)의 실제 출력 포맷 보장은 확인하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `skills/ppt-master/scripts/svg_quality/checker.py:8604-8629` `valid_acquisitions`, `valid_statuses`, `terminal_by_acquisition` | Acquire 값, Status 값, terminal 매핑 | R-02, R-03 |
| C-02 | `skills/ppt-master/scripts/svg_quality/checker.py:8575-9064` `_check_planned_image_closure` | §VIII ↔ lock ↔ 파일 ↔ SVG 닫힘 전체 | R-04~R-07, R-21, R-22 |
| C-03 | `skills/ppt-master/scripts/svg_quality/checker.py:9067-9150` `_check_sourced_image_provenance` | provenance 필수 조건 | R-13 |
| C-04 | `skills/ppt-master/scripts/svg_quality/checker.py:7062-7120` `_check_sourced_image_attribution` | 크레딧 바인딩 | R-12 |
| C-05 | `skills/ppt-master/scripts/project_management/project_specs.py:243-343` `parse_spec_lock_image_value` | lock `images` 값 문법 | R-06 |
| C-06 | `skills/ppt-master/scripts/image_gen.py:526-584`, `:586-843` `load_manifest` | `image_prompts.json` 필수·선택 필드와 검증 | R-08 |
| C-07 | `skills/ppt-master/scripts/analyze_images.py:388-452` `save_csv` | CSV 열 순서 | R-19 |
| C-08 | `skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py:375-415`, `:417-470` `load_project_image_source`, `project_image_errors` | `<image>` 검증 | R-20 |
| C-09 | `skills/ppt-master/scripts/image_treat.py:253-282`, `:433-487` `_treatment_plan`, `_prepare_provenance` | 파생 연산 목록, 출처 복사 | R-18 |

### 1.6 수락 사례

출처: 모두 구현에서 도출(원본 테스트는 열지 않음).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-04, R-07, R-21 | `ai` 행 `cover.jpg`, `Status: Generated`, `images/cover.jpg` 유효, lock `images/cover.jpg \| source=ai \| crop=adaptive`, SVG `<image href="../images/cover.jpg" …>` | `svg_quality_checker.py --stage final`에서 이 행에 대한 error 없음 |
| T-02 | R-04 | 같은 행의 `Status`가 `Pending`으로 남음 | `planned_image_not_terminal` error |
| T-03 | R-03 | `web` 행 `Status: Generated` | `planned_image_status_mismatch`(허용: needs-manual, sourced) |
| T-04 | R-13, R-12 | `web`/`Sourced` 행 `team.jpg`, `image_sources.json`에 `license_tier: attribution-required`, `author: Jane Doe`, `license_name: CC BY-SA 4.0`, `attribution_text` 있음, SVG는 이미지만 있고 크레딧 텍스트 없음 | `Missing image-specific inline attribution for sourced image team.jpg (Jane Doe; CC BY-SA)` error. `© Jane Doe / Wikimedia / CC BY-SA 4.0` 텍스트를 넣으면 통과 |
| T-05 | R-13 | `web`/`Sourced`인데 `image_sources.json`이 없음 | `image_sources_missing` error |
| T-06 | R-14 | `image_gen.py --manifest`가 모든 항목을 `Generated`로 쓴 뒤 §VIII 행은 그대로 `Pending` | manifest는 `Generated`지만 final 검사는 `planned_image_not_terminal`. 행을 직접 고쳐야 통과 |
| T-07 | R-16 | 시트 행 `illus_sheet.png`(`Type: Illustration Sheet`, `ai`, `Generated`)가 lock에 있음 | `sheet_in_lock` error |
| T-08 | R-18, R-17 | `Type: Source` 행 `photo.jpg`와 `Reference: Derived from photo.jpg; treatment=blur;`의 `photo_soft.png` 행 | `source_without_derivative` 없음. 자식 행을 지우면 error |
| T-09 | R-22 | `no-crop` 행을 `preserveAspectRatio="xMidYMid slice"`로만 배치 | `no_crop_image_fit_mismatch` error |
| T-10 | R-23, R-07 | `Needs-Manual` 행, 파일 없음, 점선 placeholder | final 검사는 이 행에 error 없음, 그러나 Image readiness GATE가 Step 7을 막고 파일명을 나열 |
| T-11 | R-08 | `image_prompts.json` 항목에 `status: "generated"`(소문자) | `ValueError`(status invalid, Valid 목록 출력) |
| T-12 | R-08, R-16 | `slice_grid: "2x3"`, `slice_names`가 5개 | `ValueError`(5 names vs 6 required) |
| T-13 | R-20 | `svg_output/a.svg`가 `<image href="data:image/png;base64,…">` | `svg_inline_image_untracked` error(현재 계약 프로젝트) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@3af3e8e) | 확인 방법·한계 |
|---|---|---|
| R-01 | `skills/ppt-master/scripts/svg_quality/checker.py:8188-8225` `_extract_image_resource_rows`, `:8229-8275` row helper들 | 코드 확인. image-base.md:13-15와 svg-image-embedding.md:14의 표는 `Purpose / Type` 대 `Purpose`+`Type`으로 서로 다르다. 구현은 `Type` 열을 읽으므로 구현 기준으로 썼다(문서와 구현 차이) |
| R-02 | C-01; `project_management/project_specs.py:121-123` `_IMAGE_ACQUISITION_SOURCES`; `references/strategist-image.md:9`(문서의 5값) | `formula` 검색: `grep -rn "formula" references/image-*.md references/strategist-image.md references/svg-image-embedding.md`로는 Acquire 값 정의를 찾지 못함(범위: 이 스펙 sources의 references 파일, 다른 디렉터리·`latex_render.py`·`formula` 언급은 열지 않음). 문서에 없는 값이 구현에 있는 차이 → U-01 |
| R-03 | C-01(`checker.py:8604-8629`), `references/svg-image-embedding.md:19-30` | 코드 확인. 문서 enum에 `Needs-Selection`이 있고 checker에는 없다(위 "원본이 정하지 않은 것"). `Rendered`는 문서에 없음 |
| R-04 | `checker.py:8696-8727` `planned_image_invalid_status`/`planned_image_not_terminal`/`planned_image_status_mismatch` | 코드 확인. final 보고서 error>0이면 exporter 거부는 선행 스펙 R-36·R-42 |
| R-05 | `checker.py:8675-8693` | 코드 확인 |
| R-06 | C-05, `checker.py:8276-8326`, `:8745-8850` lock 비교(`planned_image_missing_lock`, `locked_image_source_mismatch` 등), `references/strategist-image.md:9` | 코드 확인 |
| R-07 | `checker.py:8895-8912`(`locked_image_file_missing`의 `file_required`), `svg_to_pptx/drawingml/elements.py:375-415`, `_PROJECT_IMAGE_FORMATS`(`elements.py:124-139`) | 코드 확인. 권장(불투명 .jpg, 알파 .png)은 image-base.md:17, 구현은 강제하지 않음 |
| R-08 | C-06 | 코드 확인. "전부다"가 아닌 로더 기준이며 docs `image-generator.md:308-321` 표와 코드는 필수 필드가 다르다: 문서 표는 `page_role`·`text_policy`를 필수라 하지만 로더는 누락을 경고로 허용한다. `purpose`도 로더는 선택 |
| R-09 | `image_gen.py:909-1165`(주로 `:931-946`, `:1016-1025`, `:1040-1160`), `references/image-generator.md:421-423` | 코드 확인 |
| R-10 | `image_gen.py:1178-1272` | 코드 확인. 검사기가 `image_prompts.md`를 읽는지는 grep `image_prompts` in `svg_quality/checker.py`로 확인: 일치 0건(`checker.py`만 검색, 다른 모듈 `svg_to_pptx/`는 검색하지 않음) |
| R-11 | `image_search.py:1373-1490` `_read_existing_manifest`, `write_sources_manifest`; `checker.py:6981-7033`; `scripts/docs/image.md:556-581` | 코드 확인 |
| R-12 | C-04, `checker.py:1467-1473`(호출 조건 `not template_mode`), `references/executor-web-image.md:9-19` | 코드 확인 |
| R-13 | C-03 | 코드 확인 |
| R-14 | `references/image-base.md:43-44`(문서 의무); 도구가 `design_spec.md`/`spec_lock.md`를 쓰지 않음: `grep -n "design_spec\|spec_lock" image_gen.py image_search.py slice_images.py image_treat.py analyze_images.py` 결과 `image_gen.py`의 읽기 전용 가드(`:438-520`)뿐, 쓰기 호출 없음 | 부재 주장. 범위: 위 5개 파일. 놓칠 수 있는 곳: `project_manager.py`, `update_spec.py`, 동적 호출, `scripts/image_backends/`·`image_sources/`(열지 않음). U-02 |
| R-15 | `references/image-base.md:45-50`, `image-generator.md:363-388`, `svg-image-embedding.md:28` | 문서 선언 |
| R-16 | `checker.py:8050-8100`(시트 검사), `:8134-8186`, `slice_images.py:1186-1231`, `image_gen.py:586-843`(slice_grid/names), `references/image-generator.md:116-213` | 검사기·CLI 옵션은 코드 확인. 슬라이스 내부 알고리즘은 읽지 않음 |
| R-17 | `checker.py:8100-8132` | 코드 확인 |
| R-18 | C-09, `image_treat.py:561-597` `main`, `scripts/docs/image.md:236-294`, `references/image-base.md:19-33` | 코드 확인(처리 계획·출처 복사). 픽셀 처리 내부는 읽지 않음 |
| R-19 | C-07, `analyze_images.py:224-300`, `:456-496` | 코드 확인 |
| R-20 | C-08, `resource_paths.py:247-285`(`external_image_reference_path`, `resolve_external_image_reference`), `svg_to_pptx/drawingml/utils.py:513-542`, `checker.py:2691-2708`, `:5259-5395`, `:868` `IMAGE_UPSCALE_WARN_RATIO = 2.0` | 코드 확인 |
| R-21 | C-02, `checker.py:7531-7536`(호출 조건), `:8018-8040` | 코드 확인. "하지 않는다" 조건 목록은 `:7531-7536`에서 읽음 |
| R-22 | `checker.py:8947-9060`, `references/executor-image.md:21` | 코드 확인 |
| R-23 | `workflows/generate-pptx.md:324`, 선행 스펙 R-42, 검사기가 막지 않음: `checker.py:8895-8945`(`file_required`에서 `needs-manual`은 파일 필수에서 제외, `should_be_referenced`) | 코드 확인(문서 선언). U-04 |
| R-24 | `references/image-base.md:52-54`, `references/executor-web-image.md:7` | 문서 선언 |
| R-25 | `references/image-generator.md:357-361`, `scripts/docs/image.md:42` | 문서 선언 |
| C-01~C-09 | 위 해당 줄 | 줄 범위는 기준 SHA에서 읽은 구간이며 함수 경계로 잡았다 |
| T-01~T-13 | R-ID 열 참조 | 구현에서 도출. 실행하지 않았다 |

### 2.2 코드 읽는 순서

문서: `references/image-base.md`(공통, 상태·실패·크레딧) → `svg-image-embedding.md`(enum) → `strategist-image.md`(§VIII 쓰는 쪽) → `executor-image.md`/`executor-web-image.md`(소비 쪽). 코드: `checker.py:8018`(`_check_illustration_resource_contract`) → `:8575`(`_check_planned_image_closure`) → `:9067`(provenance) → `:7062`(크레딧). manifest: `image_gen.py:586`(`load_manifest`) → `:909`(`_run_manifest`) → `image_search.py:1373`.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 점검만. 이 스펙에 `depends`로 의존하는 스펙이 없다.
- 대조한 R-ID: R-04(checker의 `valid_statuses`에 `needs-selection` 없음, `checker.py:8612-8620`), R-07·R-23(exporter와 `svg_to_pptx/`에 `Needs-Manual`·프로젝트 `design_spec.md` 참조 없음), R-10(`image_prompts`가 `checker.py`에 0건, `svg_to_pptx`·`svg_finalize`에도 0건: `grep -rn "image_prompts" scripts/svg_to_pptx scripts/svg_finalize` 결과 없음), R-14(`image-base.md:43`과 `update_spec.py`에 §VIII·Status 코드 없음), R-02(`formula` 허용: `project_specs.py:121-123`, `checker.py:8626`). 미결정 U-01~U-04는 위 대조로 해소했다.
- 대조하지 않은 R-ID: 그 외 전부. 특히 R-15·R-24·R-25는 문서 선언이고, `checker.py`의 `_check_planned_image_closure`(8575-9064) 규칙별 판정과 2.1의 일부 줄 경계(8050-8100, 8100-8132, 8745-8850, 작성자가 1~2줄 어긋날 수 있다고 보고)는 확인하지 않았다. `svg-authoring-and-quality`의 크레딧 규칙과 이 스펙의 R-12·R-20~R-22가 같은지 대조하지 않았다.
- 재구현: 미수행

## 적용 메모

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-08, R-09, R-10 | 우리 구현은 `image_gen.py`·backend를 쓰지 않고 외부 API를 직접 호출하므로, `image_prompts.json`의 필수 4필드 + `status` 4값, 그리고 `Generated`/`Failed`/`Needs-Manual` 전이만 같은 형식으로 쓰면 된다. `image_prompts.md`는 우리 UI가 필요 없으면 생략 가능 | 사용자 결정(2026-11-17) | `image_gen.py --render-md`를 부르지 않으면 `.md`가 없다. 원본 수동 경로(R-15)의 사람용 handoff는 우리 쪽에서 별도로 제공 |
| R-23 | exporter 전에 우리 구현이 §VIII의 `Needs-Manual` 행과 `images/` 파일 존재를 직접 검사해 gate를 코드로 구현 | checker가 막지 않음(위 "원본이 정하지 않은 것") | Step 7 호출 전 사전 검사 단계 추가 |
