---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - book_to_skill/utils.py
  - book_to_skill/pdf_inspector_integration.py
  - book_to_skill/parsers/pdf.py
  - book_to_skill/cli.py
  - book_to_skill/dependencies.py
depends:
  - ./input-and-env.md
  - ./extract-artifacts.md
status: ready
---

# PDF 추출 엔진 선택·폴백

> PDF 파일 하나와 모드(`text`/`technical`)를 받아, pdf-inspector 지름길·스캔본 차단·Docling·pdftotext·pypdf·pdfminer 중 조건에 맞는 엔진으로 텍스트 한 덩어리를 뽑고, 어느 엔진을 썼는지(`extraction_method`)와 왜 돌아갔는지(`fallback_reason`)를 소스 결과 dict에 남긴다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 실행기(`cli.main`)가 먼저 `extract_single_file`을 감싸는 훅을 건다. 이후 `main`이 소스마다 부르는 `extract_single_file`은 이 래퍼다.
2. 래퍼는 이 소스의 이전 판정을 지우고, PDF처럼 보이면 pdf-inspector(설치돼 있을 때만)로 판정한다. 판정 결과는 모드와 상관없이 기록해 둔다.
3. 모드가 `text`이고 판정이 "믿을 만한 네이티브 텍스트"면 inspector의 Markdown을 정화·구조 감지해 곧바로 결과를 돌려준다(엔진 `pdf-inspector`). 정화 후 비면 4로 간다.
4. 아니면 원래 함수가 이어받는다. 포맷 판별과 의존성 점검(input-and-env R-08, R-09) 뒤, 앞 5쪽에서 텍스트가 안 나오면 스캔본으로 보고 중단한다.
5. `technical`이면 Docling을 먼저 시도한다. 성공하면(`docling`) 끝. 없거나 실패하거나 빈 결과면 이유를 기록하고 텍스트 체인으로 간다.
6. 텍스트 체인은 pdftotext → pypdf → pdfminer 순으로, 비어 있지 않은 텍스트를 처음 내는 엔진을 쓴다. 모두 실패하면 오류.
7. 쪽 수를 세고, 텍스트를 정화·구조 감지해(다른 스펙) 결과 dict를 만든다. 실행이 끝난 뒤 `cli.main`이 inspector 판정을 `metadata.json`에 덧붙인다.

### 1.2 범위·통합 지점
- 제공: 엔진 선택 순서와 각 엔진의 성공·실패 판정, 스캔본 차단, 쪽 수 계산, 결과 dict 중 이 기능이 정하는 필드(`extraction_method`, `fallback_reason`, `pages`, `pages_label`, `images_dropped`, `format`), inspector 판정의 기록.
- 제외: 텍스트 정리(`clean_pdftotext`; 엔진 세 개가 반환하기 전에 이미 적용한다는 사실만 경계로 쓴다), 정화(`sanitize_extracted_text`), 구조 감지·PDF outline(`detect_structure`, `apply_pdf_outline`), `pdf_pages.json`. 이들은 호출 순서와 입출력만 R-15에 쓴다.
- 선행 계약: [input-and-env](./input-and-env.md)(입력 해석, 매직바이트 판별, `prepare_dependencies`, `--mode` 정규화), [extract-artifacts](./extract-artifacts.md)(결과 dict가 소스 루프·`metadata.json`에서 쓰이는 방식, 한 소스의 `ExtractionError`는 그 소스만 건너뜀).
- 외부 의존: PATH의 `pdftotext`·`pdfinfo`(poppler), 선택 파이썬 패키지 `pdf_inspector`, `docling`, `pypdf`, `pdfminer.six`. 이 중 하나도 없을 수 있다.
- 소유 상태·부작용: 모듈 전역 `_INSPECTIONS`(경로 → inspector 판정, 프로세스 수명). `metadata.json` 사후 수정(R-16). 외부 프로세스 실행(`pdftotext`, `pdfinfo`)과 stdout/stderr 진행 문구.

### 1.3 인터페이스와 데이터 의미

**`extract_single_file(path, extraction_mode, install_mode)`** → 소스 결과 dict 또는 `ExtractionError`. 이 스펙에서 PDF에 해당하는 필드:

| 필드 | 값 |
|---|---|
| `format` | `"pdf"` (inspector 경로는 고정, 원래 경로는 확장자 또는 매직바이트 판별 결과) |
| `extraction_method` | `"pdf-inspector"` \| `"docling"` \| `"pdftotext"` \| `"pypdf"` \| `"pdfminer"`. 항상 실제로 텍스트를 낸 엔진 하나 |
| `fallback_reason` | `null` \| `"docling_unavailable"` \| `"docling_failed"` \| `"docling_empty"`. 의미는 R-10, R-14 |
| `pages`, `pages_label` | 정수와 고정 문자열 `"pages"`(키 `pages`는 하나). 값 규칙은 R-13 |
| `images_dropped` | 항상 `null`(PDF는 이미지 수를 세지 않음) |
| `text` | 엔진이 낸 텍스트에 정화까지 거친 결과. `chars`·`words`·`estimated_tokens`는 이 텍스트 기준 |
| 그 밖 | `source_file`, `filename`, `file_size_mb`, `sha256`, 구조 필드는 [extract-artifacts](./extract-artifacts.md) 1.3과 같다(두 경로가 같은 키 집합을 낸다) |

**엔진 선택표** (`text`/`technical`은 사용자가 준 모드)

| 모드 | inspector 상태 | 스캔본? | Docling | 선택 |
|---|---|---|---|---|
| text | 설치됨 + 신뢰 판정 + 정화 후 비지 않음 | (검사 안 함) | (안 씀) | `pdf-inspector` |
| text | 그 외 | 스캔본이면 중단 | (안 씀) | 텍스트 체인 |
| technical | 무관(판정 기록만) | 스캔본이면 중단 | 비지 않은 결과 | `docling` |
| technical | 무관 | 스캔본이면 중단 | 없음·실패·빈 결과 | 텍스트 체인 + `fallback_reason` |

**`metadata.json`에 덧붙는 `pdf_inspector` 객체**: 필드 목록은 C-03. 이 객체는 "inspector가 판정했다"는 기록이지 "inspector 결과를 썼다"는 뜻이 아니다. 썼는지는 `extraction_method`로 본다.

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 실행기가 `cli.main`을 거침(`python -m book_to_skill`, `scripts/extract.py`) | 소스 처리 전에 `extract_single_file`이 래퍼로 바뀌고(이미 걸려 있으면 그대로), 처리 후 `enrich_pdf_inspector_metadata`가 불린다. `utils.main`을 직접 부르면 훅이 없어 inspector가 전혀 쓰이지 않고 `pdf_inspector` 필드도 없다 | 코드 확인 |
| R-02 | 래퍼 호출 | 먼저 이 경로의 이전 판정을 지운다(이전 호출의 판정이 남지 않음). 소스가 PDF처럼 보이지 않으면(확장자가 `.pdf`(대소문자 무시)도 아니고 앞 4바이트가 `%PDF`도 아님. 읽기 실패는 아님으로 처리) 원래 함수로 바로 넘긴다. 그래서 `.txt` 확장자인데 내용이 `%PDF`로 시작하는 파일도 inspector 판정 대상이 되지만, 판정이 쓰이지 않으면 원래 함수가 확장자대로 텍스트로 처리한다(input-and-env R-08은 지원 확장자 파일을 내용으로 재판별하지 않음) | 코드 확인 |
| R-03 | PDF처럼 보임 | `pdf_inspector`가 import 안 되면 판정 없음(안내문도 없음). 판정 중 어떤 예외든 stderr에 `[warn] pdf-inspector preflight failed: …`를 내고 판정 없음. 판정이 있으면 `_INSPECTIONS[<절대 경로>]`에 저장한다. **판정은 모드와 무관하게 수행된다** | 코드 확인 |
| R-04 | 신뢰 판정(`native_markdown_trusted`) | 다음이 모두 참일 때만 참: Markdown이 공백 아닌 문자열, 정규화한 `pdf_type == "text_based"`, `confidence >= 0.90`, OCR 필요 쪽 목록이 비어 있음, 인코딩 문제 없음. 참이면 Markdown을 돌려주고, 거짓이면 판정 객체만 돌려준다 | 코드 확인 |
| R-05 | 모드 `text`, Markdown 있음 | `_result_from_inspector`가 정화 → 비어 있지 않음 확인 → 구조 감지 → PDF outline 적용 → 쪽 수 → 토큰 추정 → 크기·sha256 순으로 결과를 만든다. `extraction_method="pdf-inspector"`, `fallback_reason=null`, `pages = 판정의 page_count`(0이면 `count_pages`). **이 경로는 스캔본 검사, `prepare_dependencies`(설치 제안), 텍스트 정리를 거치지 않는다** | 코드 확인 |
| R-06 | R-05에서 정화 후 텍스트가 비어 있음 | 결과 없음(`None`)으로 돌아가 래퍼가 원래 함수로 넘어간다. 오류가 아니며, 원래 경로가 새로 추출한다 | 코드 확인 |
| R-07 | 판정이 있는데 R-05로 끝나지 않음(모드 `technical`, 불신뢰, R-06 포함) | stderr에 `pdf-inspector: <이유>; using the existing extraction chain.`을 낸 뒤 원래 함수로 넘긴다. 이유는 C-05의 우선순위(분류가 `text_based` 아님 → 인코딩 문제 → OCR 필요 쪽(앞 8개) → 신뢰도 < 0.90 → "native Markdown was not trustworthy")로 하나만 고른다. 따라서 `technical`이고 판정이 신뢰 가능한 경우에도 "not trustworthy"라고 나온다. 이 문구는 `fallback_reason`에 저장되지 않는다 | 코드 확인 |
| R-08 | 원래 함수 진입 | 파일이 없으면 `ExtractionError`, 포맷 판별과 `prepare_dependencies`(input-and-env R-08, R-09), 스캔본 검사(R-09), 엔진 선택(R-10, R-11) 순서다. `prepare_dependencies`는 `pdftotext`가 PATH에 있으면 PDF 텍스트용 패키지를 묻지 않고, `technical`이면 Docling 설치 제안을 한다 | 코드 확인 |
| R-09 | 스캔본 검사 | `pdftotext`가 PATH에 있고 `pdftotext -f 1 -l 5 -enc UTF-8 <pdf> -`(30초 제한)가 종료 코드 0인데 출력이 공백뿐이면 스캔본으로 본다. 이때 `ExtractionError`(OCR 안내 `ocrmypdf input.pdf output.pdf` 포함)로 그 소스를 중단하고 어떤 엔진도 시도하지 않는다. `pdftotext`가 없거나 실행 오류·시간 초과면 스캔본이 아니라고 보고 계속한다. 앞 5쪽만 보므로 앞 5쪽이 그림뿐이고 본문이 뒤에 있는 PDF도 중단된다 | 코드 확인(앞 5쪽 한계의 영향은 추론) |
| R-10 | 모드 `technical` | Docling을 시도한다(OCR 끔, 표 구조 인식 켬, Markdown으로 내보냄). 결과가 공백 아닌 텍스트면 `docling`, 폴백 없음, 텍스트 체인 생략. 아니면 텍스트 체인으로 가는데 `fallback_reason`은 이렇게 정한다: `docling` 패키지를 import할 수 없어 `None`이 나옴 → `docling_unavailable`; 변환 중 어떤 `Exception`이든 발생 → `docling_failed`(stderr에 예외 종류·메시지); 빈 문자열이거나 공백뿐인 문자열이 옴 → `docling_empty`. 폴백 시 이후 분기에서만 모드를 `text`로 본다. 결과의 `extraction_mode`(metadata.json 값)는 run의 모드 그대로다 | 코드 확인 |
| R-11 | 텍스트 체인 | 순서 pdftotext → pypdf → pdfminer. 엔진은 `None`이거나 `strip()` 후 빈 문자열이면 실패이고 다음으로 간다(이유는 기록하지 않는다). 엔진별 성공·실패는 C-07, C-09: pdftotext는 PATH에 있어야 하고(`-layout -enc UTF-8`, 120초) 종료 코드 0이며 정리 전 출력이 공백이 아니어야 성공 후보이고, 시간 초과·예외는 stderr 경고 후 실패. pypdf는 쪽 단위 추출 오류를 그 쪽만 빈 문자열로 처리하고 import 불가나 전체 예외면 실패. pdfminer는 import 불가나 예외면 실패. 세 엔진 모두 반환 전에 `clean_pdftotext`를 적용하므로 정리 결과가 공백뿐이면 실패와 같다. 성공한 엔진 이름이 `extraction_method`가 되고, 텍스트 체인에서 앞 엔진이 실패했어도 `fallback_reason`은 바뀌지 않는다 | 코드 확인 |
| R-12 | 세 엔진 모두 실패 | `ExtractionError`(`Could not extract text from PDF.` + 설치 안내). 그 소스는 건너뛰고 `fallback_reason` 등 부분 정보는 남지 않는다. `pdftotext`가 없으면 R-09 검사가 꺼져 있으므로, 텍스트 층이 없는 스캔본은 이 오류로 끝난다(OCR 안내 문구 없음) | 코드 확인 |
| R-13 | 엔진 텍스트 확보 뒤 | `pages`는 `count_pages`: `pdfinfo`가 PATH에 있으면 출력의 `Pages:` 값 → 없거나 실패하면 `pypdf` 쪽 수 → 실패하면 `pdfminer` 텍스트의 form feed 수(마지막이 form feed가 아니면 +1) → 모두 실패하면 0. 0은 "모름"이며 오류가 아니다. inspector 경로는 판정의 `page_count`가 0이 아니면 그 값을 쓴다 | 코드 확인 |
| R-14 | `fallback_reason`의 의미 | 값은 `technical` 모드에서 Docling을 못 쓴 경우에만 생긴다(R-10). `text` 모드에서 텍스트 체인 앞 엔진이 실패한 것, inspector가 불신뢰였던 것(R-07)은 기록되지 않는다. 그 정보는 `extraction_method`(체인 중 누가 성공했는지)와 `pdf_inspector` 객체(R-16)로만 간접 확인된다 | 코드 확인 |
| R-15 | 엔진 텍스트 확보 뒤(원래 경로) | 호출 순서: `sanitize_extracted_text`(정화 후 공백뿐이면 `ExtractionError`) → `estimate_tokens` → `detect_structure` → PDF면 `apply_pdf_outline` → 파일 크기·sha256(OSError는 `ExtractionError`) → dict. 결과 `text`는 정화 후 텍스트다. 인스펙터 경로는 같은 호출을 `(정화 → 비면 R-06) → 구조 → outline → 쪽 수 → 토큰 → 크기·sha` 순으로 한다. 규칙 본문은 각 스펙 | 코드 확인 |
| R-16 | `utils.main`이 정상 반환한 뒤 | `_INSPECTIONS`가 비어 있지 않고 `metadata.json`이 있으면 읽어서, `sources[]` 중 `source_file`을 `resolve()`한 경로가 판정의 키와 같은 항목마다 `pdf_inspector`를 넣는다. 일치가 정확히 1개이고 `total_sources == 1`이면 최상위에도 같은 객체를 넣는다. 일치가 없으면 파일을 다시 쓰지 않는다. 다시 쓸 때는 임시 파일에 쓰고 교체한다(들여쓰기 2, `ensure_ascii=False`). 읽기·JSON 오류는 stderr 경고 후 건너뜀. `main`이 `sys.exit`로 끝난 경우(전 소스 실패 등)에는 실행되지 않는다 | 코드 확인 |

- 불변식: 한 소스에 대해 inspector 경로가 성공하면 `extraction_method == "pdf-inspector"`이고 `fallback_reason == null`. `extraction_method == "docling"`이면 `fallback_reason == null`.
- 미결정: 없음
- 확인 한계: 정적 읽기만 했고 실행하지 않았다. `pdf_inspector` 패키지(Firecrawl)는 외부 코드라 `process_pdf`가 돌려주는 속성의 실제 타입과 `pdf_type`의 값 집합은 확인하지 않았다(코드는 `text_based`만 특별 취급하고 나머지는 `classified as <값>` 문자열로만 쓴다). 이 값들이 JSON으로 직렬화 가능하다는 가정에 `enrich_pdf_inspector_metadata`가 기대고 있으나(직렬화 오류는 잡지 않는다) 확인하지 못했다. Docling·pypdf·pdftotext의 추출 품질은 다루지 않는다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `book_to_skill/utils.py:1505-1576` (`extract_single_file`의 `.pdf` 분기) | 스캔본 검사 → Docling → 텍스트 체인의 분기와 `fallback_reason` 대입 위치, 마지막 `count_pages` | R-08~R-13 |
| C-02 | `book_to_skill/pdf_inspector_integration.py:108-115`, `196-236` `_looks_like_pdf`, `install_pdf_inspector_hook`(`wrapped`) | 래퍼 절차, PDF 판정, 중복 설치 방지 | R-01, R-02, R-05, R-07 |
| C-03 | `book_to_skill/pdf_inspector_integration.py:12-13`, `16-28`, `31-44`, `47-105` `_MIN_NATIVE_CONFIDENCE`, `_normalise_pdf_type`, `_package_version`, `_ocr_reasons`, `inspect_pdf` | 신뢰 임계값 0.90, `pdf_type` 정규화(`PdfType.TextBased`·`text-based` → `text_based`), 판정 객체 필드(`engine`, `version`, `pdf_type`, `confidence`(소수 4자리), `native_markdown_trusted`, `pages_needing_ocr`, `ocr_reasons_by_page`, `pages_with_tables`, `pages_with_columns`, `has_encoding_issues`, `is_complex_layout`, `page_count`) | R-03, R-04, R-16 |
| C-04 | `book_to_skill/pdf_inspector_integration.py:118-179` `_result_from_inspector` | inspector 경로의 결과 dict 구성과 순서 | R-05, R-06, R-15 |
| C-05 | `book_to_skill/pdf_inspector_integration.py:182-193` `_fallback_reason` | 폴백 이유 문구의 우선순위 | R-07 |
| C-06 | `book_to_skill/pdf_inspector_integration.py:239-280` `enrich_pdf_inspector_metadata` | 판정을 `metadata.json`에 덧붙이는 규칙 | R-16 |
| C-07 | `book_to_skill/parsers/pdf.py:84-98`, `101-117` `extract_with_pdftotext`, `looks_image_only` | pdftotext 명령행·제한 시간·성공 조건, 스캔 판정 | R-09, R-11 |
| C-08 | `book_to_skill/parsers/pdf.py:257-277` `extract_with_docling` | Docling 옵션과 반환(미설치는 `None`, 변환 예외는 호출자로 전파) | R-10 |
| C-09 | `book_to_skill/parsers/pdf.py:120-138`, `245-254` `extract_with_pypdf`, `extract_with_pdfminer` | 두 엔진의 실패 조건 | R-11 |
| C-10 | `book_to_skill/parsers/pdf.py:280-320` `count_pages` | 쪽 수 계산 사다리 | R-13 |
| C-11 | `book_to_skill/cli.py:17-30` `main` | 훅 설치 → `utils.main` → 판정 덧붙이기 순서 | R-01, R-16 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(정적 읽기, 실행 안 함). 원본 테스트는 이름만 확인했고 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-11, R-14 | 모드 `text`, inspector 없음, `pdftotext` 있고 텍스트가 있는 PDF | `extraction_method == "pdftotext"`, `fallback_reason == null`, `images_dropped == null`, `pages_label == "pages"`, `pdf_inspector` 필드 없음 |
| T-02 | R-04, R-05 | 모드 `text`, inspector가 `text_based`·0.95·OCR 쪽 없음·인코딩 문제 없음 | `extraction_method == "pdf-inspector"`, `pages == page_count`. `pdftotext`가 없어도 성공하고 의존성 질문 없음 |
| T-03 | R-04, R-07, R-14, R-16 | 모드 `text`, inspector 신뢰도 0.85, 소스 1개 | stderr에 `confidence below 0.90`, 체인으로 진행. `fallback_reason == null`. 최상위와 `sources[0]`에 `pdf_inspector`(`native_markdown_trusted: false`) |
| T-04 | R-10, R-14 | 모드 `technical`, Docling 미설치, `pdftotext` 있음 | `extraction_method == "pdftotext"`, `fallback_reason == "docling_unavailable"`. `metadata.json`의 `extraction_mode == "technical"` |
| T-05 | R-10 | `technical`, Docling이 예외를 던짐 | `fallback_reason == "docling_failed"`, 체인으로 계속 |
| T-06 | R-10 | `technical`, Docling이 공백 문자열을 돌려줌 | `fallback_reason == "docling_empty"` |
| T-07 | R-03, R-07, R-16 | `technical`, Docling 성공, inspector도 신뢰 가능 | `extraction_method == "docling"`, `fallback_reason == null`, stderr에 `native Markdown was not trustworthy`, `pdf_inspector.native_markdown_trusted == true` |
| T-08 | R-09 | `pdftotext` 있음, 앞 5쪽에서 텍스트가 안 나옴 | `ExtractionError`(OCR 안내), 그 소스만 건너뜀. 엔진 시도 없음 |
| T-09 | R-11, R-12 | `pdftotext` 없음, `pypdf` 있음 | `extraction_method == "pypdf"` |
| T-10 | R-12 | 엔진 셋 다 없음 | `ExtractionError`, 소스 제외(extract-artifacts R-03, R-04) |
| T-11 | R-06 | 모드 `text`, 신뢰 판정이지만 Markdown이 전부 보이지 않는 문자 | inspector 경로가 `None`을 내고 체인으로 넘어감. 오류 아님 |
| T-12 | R-16 | PDF 두 개를 `text`로 처리, 둘 다 inspector 판정 | 각 `sources[]`에 `pdf_inspector`, 최상위에는 없음 |
| T-13 | R-13 | `pdfinfo`·pypdf 불가, pdfminer 텍스트에 form feed 3개(끝이 아님) | `pages == 4` |
| T-14 | R-02, R-08 | `book.txt`(내용 `%PDF…`)를 명시 | 판정은 하지만 텍스트 파일로 처리됨 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-02, C-11; `book_to_skill/__main__.py:1-4`, `scripts/extract.py` | `utils.main`이 모듈 전역 `extract_single_file`을 호출하므로(`utils.py:1838`) 훅이 속성을 갈아끼우면 반영된다는 점은 파이썬 이름 해석에 기댄 추론 |
| R-02 | C-02 | 코드 읽기. 지원 확장자 파일은 재판별하지 않음은 `utils.py:1420`(`ext not in SUPPORTED_EXTENSIONS`일 때만 스니핑) |
| R-03, R-04 | C-03 | 코드 읽기. 외부 패키지 동작은 확인 한계 참조 |
| R-05, R-06, R-15 | C-04, C-02 | 코드 읽기. 원래 경로 순서는 `utils.py:1615-1660` |
| R-07 | C-02, C-05 | 코드 읽기 |
| R-08 | C-01; `book_to_skill/utils.py:1407-1408`, `1454`; `book_to_skill/dependencies.py:215-231` | 코드 읽기 |
| R-09 | C-07, C-01 | 코드 읽기. "앞 5쪽" 영향은 코드에서 `pages=5` 기본값으로만 확인하고 실제 PDF로 보지 않았다 |
| R-10 | C-01, C-08 | 코드 읽기. 사례 이름 확인: `tests/test_docling_fallback.py`(열지 않음) |
| R-11, R-12 | C-01, C-07, C-09 | 코드 읽기. pdftotext의 `-layout` 출력 형식 자체는 외부 프로그램이라 확인하지 않음 |
| R-13 | C-10 | 코드 읽기 |
| R-14 | C-01 | `fallback_reason` 대입이 `utils.py`에서 1464(초기값 `None`), 1472(EPUB 전용), 1519, 1532, 1535뿐임을 `grep`으로 확인했다. PDF에 해당하는 것은 1464와 1519·1532·1535이고, inspector 경로는 `None` 고정(`pdf_inspector_integration.py:168`) |
| R-16 | C-06, C-11 | 코드 읽기. 중복 경로 제거는 input-and-env R-06 |
| T-01~T-14 | 위 C-ID | 구현에서 도출, 실행하지 않음 |

문서와 구현의 차이 (구현이 사실):
- `README.md:174`는 "책 유형을 묻고 도구를 자동으로 고른다"고 하지만, 구현은 inspector 판정·설치 상태·실패에 따라 `technical`에서도 텍스트 체인으로 돌아간다.
- `README.md:176`의 스캔본 중단은 `pdftotext`가 있을 때만 작동한다(R-09). 없으면 일반 실패 메시지로 끝난다(R-12).
- `fallback_reason`은 `technical` 폴백 전용이라 inspector 불신뢰 사유와 체인 내 폴백은 같은 필드에 없다. 사유가 필요하면 `pdf_inspector` 객체를 본다.

### 2.2 코드 읽는 순서
`cli.py` `main` → `pdf_inspector_integration.py` `install_pdf_inspector_hook`(`wrapped`) → `inspect_pdf` → `_result_from_inspector` → 원래 함수 `utils.py` `extract_single_file`의 PDF 분기(1505~) → `parsers/pdf.py`의 엔진 함수 → `count_pages` → `enrich_pdf_inspector_metadata`.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-14 | 체인 내 폴백과 inspector 불신뢰 사유도 소스 결과에 구조화해 남긴다(예: `engine_attempts` 목록) | 지금은 `extraction_method`와 stderr로만 추측해야 한다 | 새 필드. T-03이 `fallback_reason` 외에 시도 목록을 확인하게 바뀐다 |
| R-09 | 스캔 판정을 `pdftotext` 없이도 하고, 앞 5쪽이 아니라 전체 중 일부 표본으로 본다 | `pdftotext`가 없으면 검사가 꺼지고, 앞 5쪽이 표지뿐인 책은 오판한다 | R-09, R-12, T-08 |
| R-07 | `technical` 모드에서는 "not trustworthy" 대신 "technical mode: inspector Markdown not used"로 안내한다 | 문구가 사실과 다르다 | stderr 문구만 변경 |
