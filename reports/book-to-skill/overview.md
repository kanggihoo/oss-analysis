---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - SKILL.md
  - README.md
  - docs/architecture.md
  - book_to_skill/cli.py
  - book_to_skill/config.py
  - book_to_skill/dependencies.py
  - book_to_skill/pdf_inspector_integration.py
  - book_to_skill/sanitize.py
  - book_to_skill/utils.py
  - book_to_skill/parsers/pdf.py
  - tools/scan_generated_skill.py
---

# book-to-skill Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/virgiliojr94/book-to-skill` (branch `master`)
- **작업트리 상태**: Clean
- **분석 목적**: 학습 + 설계 참고. PDF 책을 주면 내부에서 파싱·전처리해 텍스트와 장 구조를 만드는 부분을 우선으로 보고, 그 결과로 AI가 책 내용을 빠르게 설명해 사용자가 빨리 인사이트를 얻게 하는 흐름까지 본다(스펙을 어디에 쓸지: 미정. 재구현 또는 Claude Code 학습 스킬의 재료 중 하나). 세밀도는 PDF 전처리 쪽(행 1~6)을 가장 잘게, 비PDF 형식과 배포·측정은 한 행으로 굵게 둔다
- **라이선스**: MIT License (LICENSE 파일에 적힌 그대로, Copyright (c) 2025 virgiliojr94) — `LICENSE.md`. 하위 디렉터리 LICENSE는 `find`로 찾지 못했다(코드 확인)
- **분석 대상 제품**: 루트 Python 패키지 `book_to_skill/`(추출기: `cli.py`, `utils.py`, `parsers/`, `sanitize.py`, `dependencies.py`, `pdf_inspector_integration.py`), 루트 `SKILL.md`(생성기 명세, 에이전트가 따름), `tools/`(검증·스캔·측정), `evals/`, `docs/`(MkDocs 문서 사이트). 별도 서버·결제 없음
- **스펙 범위**: 2026-11-04 승인(권장안 + 행 병합): 행 1~5, 8, 9와 공유 계약 S1. 제외: 6(쪽 인용이 필요할 때만, 사용자 제외), 7·10·11·12(목적 밖). 처음 feature map은 15행이었으나 같은 날 8·9를 병합해 12행으로 줄였다(`SKILL.md` 지시문 약 400줄(Step 2의 호스트 경로 탐색 셸 블록 제외)에 파이썬은 `estimate_tokens`·`parse_arguments` 정도라 잘게 나눌 이유가 없음)
- **검증 방식**: 모든 항목은 소스를 읽어 확인했다(정적 읽기). 추출기를 실제로 실행한 적은 없다. 실행 시도가 권한 설정으로 거부됐고 우회하지 않았다. 그래서 "동작한다"가 아니라 "코드가 이렇게 쓰여 있다" 수준이다

---

## 2. 프로젝트 개요

책·문서(PDF, EPUB, DOCX 등)를 에이전트 스킬 폴더로 바꾸는 도구다. 두 부분으로 나뉜다(코드 확인: `docs/architecture.md`, `AGENTS.md`).

1. **추출기**(Python, 결정적): 문서 → `full_text.txt` + `metadata.json`. LLM을 쓰지 않는다.
2. **생성기**(`SKILL.md`, 에이전트가 단계대로 실행): 추출된 텍스트를 읽고 `SKILL.md`(핵심 틀 + 색인), `chapters/*.md`, `glossary.md`, `patterns.md`, `cheatsheet.md`를 쓴다. 이후 질문이 오면 에이전트가 색인으로 해당 장 파일만 읽는다.

PDF 쪽 핵심 흐름은 이렇다. 사용자가 고른 책 유형(`technical`/`text`)이 추출 방식(`--mode`)을 정한다. `text` 모드는 (설치돼 있으면) pdf-inspector가 믿을 만하다고 판정할 때 그 Markdown을 그대로 쓰고, 아니면 pdftotext → pypdf → pdfminer 순으로 폴백한다. `technical` 모드는 Docling을 먼저 시도하고 실패하면 같은 텍스트 체인으로 간다. 스캔본은 OCR하지 않고 중단한다. 그 뒤 보이지 않는 문자를 지우고, PDF 북마크(outline)나 "Chapter N" 패턴으로 장 구조를 찾아 `metadata.json`에 기록한다(코드 확인).

### Feature map

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 입력·환경 준비 | 경로·폴더·glob → 지원 파일 목록(폴더·glob은 지원 확장자만 통과, 명시한 파일은 확장자가 지원 목록 밖일 때만 매직바이트로 PDF·EPUB·DOCX 판별). 포맷별 선택 의존성 점검·설치 제안(`--check`, 비대화형은 폴백). 작업 디렉터리 권한·심볼릭링크 점검. 포함 안 함: 실제 추출 | `book_to_skill/utils.py` `resolve_input_files`, `parse_arguments`, `prepare_output_dir`; `book_to_skill/dependencies.py` `prepare_dependencies`, `run_dependency_check`, `normalize_install_mode`, `offer_dependency_install` | 없음 | 핵심 | [input-and-env](./capabilities/input-and-env.md) · ready | 코드 확인 |
| 2. PDF 추출 엔진 선택·폴백 | PDF 1개 → 텍스트 1덩어리. 모드·설치 상태·판정 결과에 따라 엔진을 고르고, 실패하면 다음으로. 스캔본은 중단. 포함 안 함: 텍스트 정리, 구조 감지 | `book_to_skill/utils.py` `extract_single_file`(PDF 분기); `book_to_skill/pdf_inspector_integration.py` `inspect_pdf`, `install_pdf_inspector_hook`, `_result_from_inspector`, `enrich_pdf_inspector_metadata`; `book_to_skill/parsers/pdf.py` `looks_image_only`, `extract_with_docling`, `extract_with_pdftotext`, `extract_with_pypdf`, `extract_with_pdfminer` | 1 | 핵심 | [pdf-extraction](./capabilities/pdf-extraction.md) · ready | 코드 확인 |
| 3. PDF 텍스트 정리 | 쪽 머리말·꼬리말·쪽번호 제거, 줄 끝 하이픈 이어 붙이기. pdftotext·pypdf·pdfminer 결과에만 적용(Docling·pdf-inspector 결과에는 없음) | `book_to_skill/parsers/pdf.py` `clean_pdftotext`, `_PDF_PAGE_NUM`, `_ROMAN_1_99`, `_PDF_HYPHEN_WRAP` | 2 | 핵심 | [pdf-text-cleanup](./capabilities/pdf-text-cleanup.md) · ready | 코드 확인 |
| 4. 텍스트 정화 | 모든 형식 공통. 제로폭·방향 제어·태그 블록 등 보이지 않는 문자 삭제(문서에 숨긴 프롬프트 주입 방어), CJK 부수 문자를 원래 한자로 접기. 일반 경로는 정화 후 비면 그 소스 거부, pdf-inspector 경로는 오류 없이 기존 추출 체인으로 폴백 | `book_to_skill/sanitize.py` `sanitize_extracted_text`, `fold_cjk_radicals`; `book_to_skill/utils.py` `extract_single_file`(정화 호출부); `book_to_skill/pdf_inspector_integration.py` `_result_from_inspector`(정화 호출부) | 2 | 핵심 | [text-sanitize](./capabilities/text-sanitize.md) · ready | 코드 확인 |
| 5. 구조 감지·장 범위 | 텍스트 → 장 수·장 제목·ToC 유무·장별 줄 범위(`chapter_ranges`). PDF outline이 쓸 만하면(Part를 펼치고 front/back matter·ToC·appendix를 뺀 제목이 2개 이상) 우선, 아니면 "Chapter N"·Markdown 제목 패턴. 포함 안 함: 장 요약 | `book_to_skill/utils.py` `detect_structure`, `apply_pdf_outline`, `chapter_line_ranges`, `_chapter_number`, `_match_chapter_number`, `_structural_chapter_headings`, `_find_outline_chapter_start`, `_is_chapter_content_boundary`; `book_to_skill/parsers/pdf.py` `pdf_outline_titles`, `pdf_outline_all_titles` | 4, S1 | 핵심 | [structure-detection](./capabilities/structure-detection.md) · ready | 코드 확인 |
| 6. PDF 쪽 단위 근거(옵션) | `--pdf-page-sidecar`일 때 pypdf로 쪽마다 텍스트를 따로 뽑아 `pdf_pages.json`에 저장(쪽 번호·원본 해시·낮은 신뢰 사유). `full_text.txt`와 글자 위치는 연결되지 않음. 표 셀이 붙었을 수 있는 소수 표기(`0.2070.110`)는 고치지 않고 표시만(`possible_joined_decimal_cells`) | `book_to_skill/utils.py` `write_pdf_page_sidecar`; `book_to_skill/parsers/pdf.py` `extract_pypdf_page_records` | 2, 4, S1 | 핵심 | `capabilities/pdf-page-sidecar.md` · 미작성 | 코드 확인 |
| 7. 비PDF 형식 파서 패밀리 | EPUB(ebooklib→zip), DOCX(python-docx→zip/XML, DTD 거부), HTML(trafilatura→bs4→stdlib), RTF, MOBI/AZW(Calibre), 텍스트·Markdown. **목적 밖이라 한 행으로 묶음. 공통 규칙만 보고 개별 파서는 안 읽음(미탐색)** | `book_to_skill/parsers/{epub,docx,html,rtf,calibre,text}.py`; `book_to_skill/utils.py` `extract_single_file`(형식 분기) | 1 | 핵심 | `capabilities/non-pdf-parsers.md` · 미작성 | 추론(분기 구조만 코드 확인, 파서 본문 미확인) |
| 8. 생성 준비 | 추출 결과의 `estimated_tokens`로 비용을 보여 주고 확인받기, 50k 토큰 넘는 책은 통째로 읽지 않고 grep·sed로 구간만 읽게 지시, 책 유형(`BOOK_TYPE`)·목적(`DEPTH`) 질문과 `--mode` 결정, 책 앞 8,000자로 제목·저자·핵심 틀 파악, 스킬 이름·저장 위치 결정. 포함 안 함: 스킬 파일 쓰기, Mode 3(사전 분석에서 생성)과 갱신 분기(Mode 4) — 현재 Mode 3은 소유하는 행이 없음 | `SKILL.md` Step 1.5, 2.5, 2.6, 3, 4, 5; `book_to_skill/utils.py` `estimate_tokens`, `parse_arguments` | S1 | 핵심 | [generation-setup](./capabilities/generation-setup.md) · ready | 코드 확인(명세 텍스트), 에이전트 실제 행동은 미확인 |
| 9. 스킬 작성·질의 시 로딩 | 장마다 `chapters/chNN-slug.md`(토큰 예산은 `BOOK_TYPE`×`DEPTH` 표, 원문 복사 금지, `chapter_ranges`로 해당 구간만 읽음), `glossary.md`·`patterns.md`·`cheatsheet.md`, 4K 토큰 안의 마스터 `SKILL.md`(핵심 틀 + 장 색인 + 주제 색인). 생성된 스킬 폴더 형식과, 질문이 오면 색인으로 장 파일 하나만 읽는 사용 방식 포함. 호스트가 스킬을 읽는 방식은 제외 | `SKILL.md` Step 6, 7, 8, 9, Quality Rules | 5, 8, S1 | 핵심 | [skill-authoring](./capabilities/skill-authoring.md) · ready | 코드 확인(명세 텍스트), 질의 시 호스트 동작은 추론 |
| 10. 갱신·재실행 가드 | 같은 이름 스킬이 있으면 중단하고 선택을 묻기, 끊긴 실행의 작업 디렉터리 재사용 안전 판정(`sha256`·모드 일치), 새 자료를 기존 스킬에 접어 넣기 | `SKILL.md` Step 0~1(Re-run guard), Update/Fold-in Workflow; `book_to_skill/utils.py` `reuse_is_safe` | S1, 9 | 핵심 | `capabilities/update-and-rerun.md` · 미작성 | 코드 확인(`reuse_is_safe`는 테스트에서만 호출되고 명세가 가리킴) |
| 11. 검증·설치·배포 | 생성 스킬 보안 스캔(9.5), 호스트별 규칙 검증(`validate_skill`), 호스트별 설치 위치·심볼릭 링크(Step 5, 10), GitHub 게시(Step 11) | `SKILL.md` Step 5, 9.5, 10, 11; `tools/scan_generated_skill.py`; `tools/validate_skill.py` | 4, 8, 9 | 부속 | `capabilities/validate-and-publish.md` · 미작성 | 추론(스캔 규칙 본문·호스트별 경로 미확인) |
| 12. 측정·평가 도구 | 토큰 절감 측정(`discovery_tax`), 점진적 공개 평가(`evals/`, `tools/evals/`) | `tools/discovery_tax.py`; `tools/evals/`; `docs/research/progressive-disclosure-evals.md` | 9 | 부속 | `capabilities/measurement.md` · 미작성 | 미확인(머리말만 읽음) |

**공유 계약**

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 추출 산출물 (`full_text.txt`, `metadata.json`) | 2~6, 8~10 | `book_to_skill/utils.py` `main`(저장부), `extract_single_file`(반환 dict); `book_to_skill/config.py` | [extract-artifacts](./capabilities/extract-artifacts.md) · ready | 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: README 첫 문단·3단계 설명, `docs/architecture.md`, `config.py`의 지원 확장자와 선택 의존성, `utils.py`의 `main`·`extract_single_file`·구조 감지, `parsers/pdf.py` 전체, `pdf_inspector_integration.py` 전체, `sanitize.py` 앞부분과 `sanitize_extracted_text`, `SKILL.md`의 Step 1.5·2·2.5·2.6·3·4·7·9·9.5·10과 Quality Rules.
- 문서와 구현의 차이·주의 (모두 정적 읽기 기준):
  - `pdf-inspector` 지름길은 `extraction_mode == "text"`일 때만 쓴다. `technical` 모드는 Docling 쪽으로 가고 inspector는 판정 메타데이터만 남긴다(`pdf_inspector_integration.py` `wrapped`). 코드 확인.
  - `clean_pdftotext`(머리말·쪽번호·하이픈 정리)는 pdftotext·pypdf·pdfminer 경로에서만 호출된다. Docling과 pdf-inspector 결과는 거치지 않는다(`utils.py` PDF 분기, `pdf_inspector_integration.py` `_result_from_inspector`). 코드 확인.
  - 스캔 PDF는 OCR하지 않고 "ocrmypdf로 먼저 처리하라"는 오류로 끝난다. Docling도 `do_ocr = False`다. 코드 확인.
  - Step 10이 작업 디렉터리를 `rm -rf`로 지우는데, Step 9 템플릿은 마스터 `SKILL.md`에 `output_text` 경로(`full_text.txt`)를 적어 두라고 한다("local extraction, not shipped"). 정리 뒤에는 그 경로가 사라진다. 두 텍스트는 코드 확인, 정리 뒤에는 그 경로의 파일이 없다(코드·명세 텍스트 확인). 의도인지 모순인지는 가리지 못했다: `tests/test_skill_template_full_text.py`의 docstring은 "스킬이 실제 책의 색인으로 동작하도록"이라고 적고, 이 줄은 Step 10 정리보다 나중에 추가됐다(`skill-authoring` R-17).
  - 쪽 머리말·번호 정리는 엔진이 반환하기 직전에 적용돼서, 정리 결과가 공백뿐이면 그 엔진은 실패로 처리되어 다음 엔진으로 간다. 정화 후에야 비는 텍스트는 다음 엔진으로 가지 않고 소스가 거부된다(`pdf-extraction` R-11, `text-sanitize` R-15). 코드 확인.
  - 스캔본 차단은 `pdftotext`가 PATH에 있을 때만 동작하고 앞 5쪽만 본다. 신뢰된 pdf-inspector 경로에서는 스캔본 검사 자체가 없다. 코드 확인.
  - `technical` 모드에서도 pdf-inspector 판정은 항상 실행되어 `metadata.json`에 남는다. 지름길만 `text` 모드 전용이다. 코드 확인.
  - `SKILL.md` Step 2·Step 5의 확장자 목록과 구현(`config.py`)이 다르고(`.text`, `.asciidoc`, `.xhtml`은 구현에만), `docs/how-it-works.md`는 장 요약 예산을 "800–1,200"으로만 적고 작업 디렉터리를 고정 경로로 적는다. `SKILL.md`와 코드가 최신이라 그쪽을 사실로 썼다. 코드 확인.
  - `--install-missing <경로>`처럼 값 없는 옵션 뒤에 경로를 두면 경로가 설치 모드 값으로 삼켜져 입력에서 사라진다(`utils.py:1237-1241`). 코드 확인.
  - `reuse_is_safe`는 테스트 외에는 파이썬에서 호출되지 않고 `SKILL.md`가 "실행 가능한 형태"로 가리킨다. 코드 확인(호출처 grep).
- 미탐색: `parsers/` 중 PDF 외 파일 본문, `tools/`·`evals/` 본문, `tests/`(기본 제외, 사례명 검색만), `docs/` 사이트 소스, Step 11 게시, Update/Fold-in 상세, Mode 3. 장 번호 판별 helper·`sanitize.py` 상수 표·`dependencies.py`는 기능 스펙 작성 때 읽었다. 추출기와 생성기는 실행해 보지 않았다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | PDF 한 권이 추출기를 지나 작업 디렉터리 파일이 되고, 에이전트가 그것으로 스킬을 만들고, 질문 때 장 하나만 읽히는 흐름 |

archify 자동 검사(validate·deliver·check·browser-check)는 통과했다. 사람이 눈으로 확인한 것은 아니다.

### 그림 해설

**읽는 순서**
1. 왼쪽 위 `PDF 책 + 사용자`에서 시작해 오른쪽으로 `추출 러너` → `pdf-inspector 판정`을 본다.
2. `pdf-inspector 판정`에서 갈라지는 두 길을 본다. 아래로 곧장 내려가면 빠른 길, 오른쪽 `스캔본 차단`으로 가면 기존 체인이다.
3. 오른쪽 열 위에서 아래로 `스캔본 차단` → `Docling`/`텍스트 체인`을 보고, 가운데 열을 따라 왼쪽으로 `텍스트 정화` → `구조 감지` → `작업 디렉터리`로 돌아온다.
4. 맨 아래 줄은 에이전트 쪽이다. `작업 디렉터리` → `에이전트 생성` → `생성된 스킬` → `질문 → 장 로드`.

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| PDF 책 + 사용자 | 책 유형(technical/text)을 답하고 스킬을 호출 | PDF 경로, `--mode` | `SKILL.md` Step 1.5, Step 2 명령줄 | 코드 확인 |
| 추출 러너 | 훅을 걸고 입력을 해석하고 소스마다 추출, 결과를 합쳐 저장 | 입력: 경로들. 출력: `full_text.txt`, `metadata.json` | `cli.py` `main`; `utils.py` `main` | 코드 확인 |
| pdf-inspector 판정 | 설치돼 있으면 PDF 종류·신뢰도를 판정. 네이티브 텍스트이고 신뢰도 0.90 이상, OCR 필요 쪽·인코딩 문제 없을 때만 그 Markdown 사용 | 입력: PDF. 출력: 신뢰 시 Markdown, 항상 판정 메타데이터 | `pdf_inspector_integration.py` `inspect_pdf`, `wrapped`, `_MIN_NATIVE_CONFIDENCE` | 코드 확인 |
| 스캔본 차단 | 앞 5쪽에서 텍스트가 안 나오면 즉시 실패(OCR 안내). `pdftotext`가 있을 때만 동작 | 입력: PDF 경로. 출력: 통과 또는 `ExtractionError` | `parsers/pdf.py` `looks_image_only`; `utils.py` `extract_single_file` | 코드 확인 |
| Docling | `technical` 모드에서 레이아웃 인식 변환(표 구조 켬, OCR 끔) → Markdown. 없거나 실패·빈 결과면 `fallback_reason` 기록 후 텍스트 체인 | 입력: PDF. 출력: Markdown | `parsers/pdf.py` `extract_with_docling`; `utils.py` PDF 분기 | 코드 확인 |
| 텍스트 체인 + 정리 | pdftotext(`-layout`) → pypdf → pdfminer 순으로 시도하고, 성공한 결과에 머리말·쪽번호·하이픈 정리 | 입력: PDF. 출력: 정리된 텍스트 | `parsers/pdf.py` `extract_with_pdftotext`, `clean_pdftotext` | 코드 확인 |
| 텍스트 정화 | 숨은 문자 제거와 CJK 부수 접기. 결과가 비면 거부 | 입력: 추출 텍스트. 출력: 정화 텍스트, 제거 개수 | `sanitize.py` `sanitize_extracted_text` | 코드 확인 |
| 구조 감지 | 장 수·제목·ToC를 찾는다. PDF 북마크에서 Part를 펼치고 front/back matter·ToC를 뺀 제목이 2개 이상이면 그것을 쓴다(줄 범위 계산은 `main`의 metadata 구성 단계) | 입력: 정화 텍스트(+PDF outline). 출력: `chapters_*`, `chapter_ranges` | `utils.py` `detect_structure`, `apply_pdf_outline`, `chapter_line_ranges` | 코드 확인 |
| 작업 디렉터리 | 소스 경계 표시를 붙인 `full_text.txt`와 토큰·장 정보가 든 `metadata.json`. 임시 폴더, 프로세스 ID로 구분, 권한 0700 | 입력: 위 결과. 출력: 파일 | `config.py` `default_output_dir`; `utils.py` `prepare_output_dir`, `main` | 코드 확인 |
| pdf_pages.json | 옵션. 쪽마다 pypdf 텍스트와 신뢰 사유. 원본 해시가 바뀌면 사용 불가 표시 | 입력: PDF. 출력: JSON | `utils.py` `write_pdf_page_sidecar`; `parsers/pdf.py` `extract_pypdf_page_records` | 코드 확인 |
| 에이전트 생성 | 비용 추정 후, 장 구간만 grep·sed로 읽어 장 요약·보조 파일·마스터를 씀 | 입력: 위 두 파일. 출력: 스킬 폴더 | `SKILL.md` Step 2.5~9 | 코드 확인(명세 텍스트), 실행 미확인 |
| 생성된 스킬 | 마스터 `SKILL.md`(4K 토큰) + `chapters/` + 보조 3파일 | 출력: 파일들 | `SKILL.md` Step 9 | 코드 확인(명세 텍스트) |
| 스킬 스캔 | 주입 문구·숨은 문자·권한 확대 등을 점검. 실패 시 사람 검토를 요구 | 입력: 스킬 폴더. 출력: 종료 코드와 규칙·위치 | `SKILL.md` Step 9.5; `tools/scan_generated_skill.py` | 추론(스캔 본문 미확인) |
| 질문 → 장 로드 | 질문이 오면 색인으로 장 파일을 찾아 그 파일만 읽음 | 입력: 질문. 출력: 답 | `SKILL.md` Step 9 템플릿 | 추론(호스트 동작 미확인) |

**실행 흐름: PDF 한 권 → 스킬 → 질문**
1. 입력 해석 — 입력 경로 → `resolve_input_files` → 지원 확장자 파일 목록(`utils.py:resolve_input_files`).
2. 판정 — `install_pdf_inspector_hook`이 `extract_single_file`을 감싼다. 신뢰할 수 있는 text 모드면 inspector Markdown을 쓰고 4번으로 간다(`pdf_inspector_integration.py:wrapped`).
3. 추출 — 스캔본이면 중단. `technical`이면 Docling, 실패하면 pdftotext → pypdf → pdfminer(`utils.py:extract_single_file`).
4. 정화·구조 — `sanitize_extracted_text` → `detect_structure` → PDF면 `apply_pdf_outline`(`utils.py:extract_single_file`).
5. 저장 — 소스들을 합쳐 `full_text.txt`, `metadata.json`을 쓰고 옵션이면 `pdf_pages.json`도(`utils.py:main`).
6. 생성 — 에이전트가 `metadata.json`으로 비용을 알리고, 장 구간만 읽어 스킬 파일을 쓴 뒤 스캔한다(`SKILL.md` Step 2.5~9.5).
7. 정리 — 작업 디렉터리를 삭제한다(`SKILL.md` Step 10).
8. 질문 — 이후 질문은 색인을 거쳐 장 파일 하나만 읽는다(`SKILL.md` Step 9 템플릿).

단계별 스펙: 1단계 [input-and-env](./capabilities/input-and-env.md), 2~3단계 [pdf-extraction](./capabilities/pdf-extraction.md)·[pdf-text-cleanup](./capabilities/pdf-text-cleanup.md), 4단계 [text-sanitize](./capabilities/text-sanitize.md)·[structure-detection](./capabilities/structure-detection.md), 5단계 [extract-artifacts](./capabilities/extract-artifacts.md), 6~8단계 [generation-setup](./capabilities/generation-setup.md)·[skill-authoring](./capabilities/skill-authoring.md).

**미확인 영역**
- 실제 PDF로 돌려 본 결과(Docling·pdf-inspector의 품질, 장 감지 정확도, 소요 시간)는 확인하지 않았다.
- 에이전트가 `SKILL.md`를 얼마나 충실히 따르는지, 호스트가 생성된 스킬을 어떻게 불러오는지는 코드로 확인할 수 없다.
- 비PDF 파서와 `tools/`·`evals/` 본문은 읽지 않았다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸 (승인 범위 8개 모두 ready, 나머지 5행은 범위 밖이라 미작성)
