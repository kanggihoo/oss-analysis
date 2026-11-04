---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - book_to_skill/utils.py
  - book_to_skill/config.py
  - book_to_skill/pdf_inspector_integration.py
  - SKILL.md
depends: []
status: ready
---

# 추출 산출물 계약 (`full_text.txt`, `metadata.json`)

> 추출기가 문서 여러 개를 받아 소스 경계가 표시된 텍스트 한 파일(`full_text.txt`)과 크기·구조 정보(`metadata.json`)를 작업 디렉터리에 쓰고, 에이전트가 이 둘만 읽고 생성 단계를 진행한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 러너가 작업 디렉터리를 만든다(소유자·심볼릭링크 점검, 권한 0700).
2. 입력 파일마다 추출한다. 실패한 소스는 경고만 남기고 건너뛴다.
3. 성공한 소스 텍스트를 `SOURCE:` 배너와 함께 이어 붙여 `full_text.txt`에 쓴다.
4. 소스별·전체 크기와 구조 정보를 모아 `metadata.json`에 쓴다.
5. (옵션) `--pdf-page-sidecar`이면 같은 디렉터리에 `pdf_pages.json`을 더 쓴다(별도 행 6의 계약).
6. 요약을 출력하고 세 경로를 알려 준다. 에이전트는 출력된 경로나 `metadata.json`의 `workdir`을 쓴다.

### 1.2 범위·통합 지점
- 제공: 파일 두 개의 위치·형식·필드 의미, 여러 소스를 합칠 때의 규칙.
- 제외: 형식별 추출 방식(행 2~4, 7), 구조 감지 규칙(행 5), `pdf_pages.json`(행 6), 이 파일을 읽는 에이전트 동작(행 8, 9).
- 외부 의존: 임시 디렉터리(`tempfile.gettempdir()`), 환경변수 `BOOK_SKILL_WORKDIR`.
- 소유 상태·부작용: 작업 디렉터리 하나와 그 안의 파일들. 삭제는 추출기가 아니라 에이전트가 한다(`SKILL.md` Step 10).

### 1.3 인터페이스와 데이터 의미

**위치**
| 항목 | 의미 |
|---|---|
| 작업 디렉터리 | `BOOK_SKILL_WORKDIR`가 비어 있지 않으면 그 경로. 아니면 `<tempdir>/book_skill_work-<PID>` |
| `full_text.txt` | 작업 디렉터리 아래. UTF-8, 줄바꿈 `\n` 고정 |
| `metadata.json` | 작업 디렉터리 아래. UTF-8, 들여쓰기 2, 비ASCII 그대로(`ensure_ascii=False`) |

**`full_text.txt` 형식**: 소스마다 `\n\n` + `=`×80 + `\nSOURCE: <filename> (Path: <절대 경로>)\n` + `=`×80 + `\n\n` + 정화된 텍스트를 순서대로 이어 붙이고, 전체를 `strip()`한다. 소스가 하나여도 배너가 붙는다.

**`metadata.json` 최상위 필드**
| 필드 | 의미 |
|---|---|
| `source_file`, `filename`, `format`, `extraction_method` | 소스 1개면 그 소스의 값. 2개 이상이면 각각 `"Consolidated from multiple sources"`, `"multi-source"`, `"mixed"`, `"multi-method"` |
| `extraction_mode` | 이번 실행의 `--mode` 값(`text`/`technical`). 잘못된 값은 `text`로 정규화됨 |
| `file_size_mb` | 소스 크기 합(MB, 소수 2자리) |
| `pages`, `chars`, `words`, `estimated_tokens`, `estimated_tokens_human`, `images_dropped` | 합계. `pages`는 소스별 `pages` 합(PDF는 쪽 수, EPUB은 spine 항목 수, 나머지 형식은 0), `chars`·`words`·토큰은 합쳐진 전체 텍스트 기준. `estimated_tokens_human`은 `"~<N>K"`(정수 나눗셈) |
| `workdir`, `output_text` | 이번 실행의 작업 디렉터리와 `full_text.txt` 경로(문자열) |
| `total_sources` | 성공한 소스 수 |
| `sources[]` | 성공한 소스별 항목. 입력 순서 |
| `chapters_detected`, `chapters_method`, `chapter_headings_sample`, `has_toc` | 전체 구조. 규칙은 행 5 |
| `chapter_titles`, `chapter_ranges` | 소스 1개이고 `chapters_method`가 `outline`일 때만 최상위에 있다. `chapter_ranges`는 `full_text.txt`(배너 포함) 줄 기준 |
| `pdf_inspector` | 판정이 있었고 `sources`와 판정이 정확히 1개씩 맞고 `total_sources == 1`일 때만 최상위에 추가(행 2). 소스별 항목에는 판정이 있었던 소스마다 `sources[].pdf_inspector`로 들어간다 |

**`sources[]` 항목**: `source_file`, `filename`, `format`, `extraction_method`, `fallback_reason`, `file_size_mb`, `sha256`(파일 바이트), `pages`, `pages_label`(`pages` 또는 `sections`/`spine_items`), `chars`, `words`, `estimated_tokens`, `images_dropped`, `chapters_detected`, `chapters_method`, `chapter_headings_sample`, `has_toc`. pdf-inspector가 판정했으면 `pdf_inspector`. outline이 쓰였으면 `chapter_titles`와 `chapter_ranges`가 더 있다. 이 `chapter_ranges`는 **그 소스 텍스트만의** 줄 번호이고 `full_text.txt` 줄 번호가 아니다. 줄 번호는 1부터, 시작·끝 모두 포함. 항목은 `{title, start_line, end_line}`.

**토큰 추정** `estimated_tokens`: CJK가 없으면 `int(공백 단위 단어 수 / 0.75)`, 있으면 `int(CJK 제외 단어 수 / 0.75 + CJK 글자 수 / 1.5)`. 빈 텍스트는 0. 결정적이다.

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 작업 디렉터리 경로가 심볼릭링크이거나, 디렉터리가 아니거나, 다른 사용자 소유 | `ExtractionError`로 중단(추출 시작 전). 소스 루프 밖에서 일어나 잡히지 않으므로 트레이스백으로 끝난다(`utils.py:1830`, 루프의 `try`는 1837-1842). 이미 있고 본인 소유면 권한을 0700으로 바꾸고 재사용. 없으면 0700으로 생성 | 코드 확인 |
| R-02 | 기본 경로 | 프로세스마다 다른 디렉터리(PID가 이름에 들어감). `BOOK_SKILL_WORKDIR=""`은 미설정으로 취급 | 코드 확인 |
| R-03 | 소스 하나가 `ExtractionError` | 그 소스만 건너뛰고 경고. 나머지는 계속. 건너뛴 것은 `sources[]`·`total_sources`에 없다 | 코드 확인 |
| R-04 | 모든 소스가 실패 | 오류 목록을 stderr에 쓰고 종료 코드 1. 두 파일 모두 쓰지 않는다 | 코드 확인 |
| R-05 | 소스가 둘 이상 | `full_text.txt`에 입력 순서로 배너와 함께 이어 붙임. 구조는 배너를 뺀 소스 텍스트(`\n\n`으로 연결)에서 다시 감지 | 코드 확인 |
| R-06 | 소스 1개 + `chapters_method == "outline"` | 최상위 `chapters_*`, `chapter_titles`를 소스 값으로 덮고, `chapter_ranges`를 배너 포함 `full_text.txt` 기준으로 새로 계산해 최상위에 둔다 | 코드 확인 |
| R-07 | 소스 2개 이상이고 `structural` 소스가 있고 `numeric` 소스가 없음 | 장 수를 `structural` 소스(장 2개 이상인 것)의 합으로, 샘플을 그 소스들의 샘플 이어 붙임(앞 10개)으로 바꾸고 방법을 `structural`로 한다 | 코드 확인 |
| R-08 | `has_toc` | 소스별 값 중 하나라도 참이면 참(전체 재감지가 아님) | 코드 확인 |
| R-09 | 추출 직후 | 구조가 `structural`이고 장 ≤ 1이며 단어 > 5000이면 "chapter detection likely failed" 경고를 출력한다(파일에는 안 씀). ToC가 없으면 경고 | 코드 확인 |
| R-10 | `full_text.txt` 쓰기 | 줄바꿈 변환 없이 `\n` 그대로(Windows에서 CRLF 겹침 방지) | 코드 확인 |
| R-11 | 에이전트가 읽을 때 | 최상위 `filename`/`source_file` 또는 첫 `SOURCE:` 줄로 요청한 문서인지 확인해야 한다(다른 실행의 출력과 섞일 수 있음) | 코드 확인(명세 텍스트) |
| R-12 | 정상 종료 | 출력에 `Workdir ->`, `Text ->`, `Meta ->`(옵션이면 `PDF pages ->`) 줄. 에이전트는 이 경로를 쓴다 | 코드 확인 |

- 불변식: `chars`·`words`·`estimated_tokens` 최상위 값은 `full_text.txt` 내용 기준이므로 배너 글자도 포함한다. 소스별 값은 배너 없는 텍스트 기준이다.
- 미결정: 없음
- 확인 한계: 정적 읽기만 했고 실제 실행 결과는 보지 않았다. 구조 필드의 세부 의미(`chapters_method`의 값 `numeric`·`structural`·`outline`·`none`)는 행 5가 정한다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `book_to_skill/config.py:5-29` `default_output_dir`, `OUTPUT_DIR`, `OUTPUT_TEXT`, `OUTPUT_META` | 작업 디렉터리 이름·환경변수 처리 | R-02 |
| C-02 | `book_to_skill/utils.py:1663-1686` `prepare_output_dir` | 디렉터리 안전 점검과 권한 | R-01 |
| C-03 | `book_to_skill/utils.py:92-109` `estimate_tokens` | 토큰 추정식(상수 0.75·1.5는 `config.py:31-35`, CJK 범위는 `utils.py:85-89`) | 1.3 |
| C-04 | `book_to_skill/utils.py:1643-1660` `extract_single_file` 반환 dict | 소스별 결과 필드 | 1.3 |
| C-05 | `book_to_skill/utils.py:1836-1862` | 소스 순회, 건너뛰기, 배너 문자열, 파일 쓰기 | R-03~R-05, R-10 |
| C-06 | `book_to_skill/utils.py:1864-1997` | 합계 계산, 구조 재감지·병합, `metadata.json` 필드 구성과 쓰기 | R-05~R-08, 1.3 |
| C-07 | `book_to_skill/utils.py:2003-2041` | 요약 출력과 경고 | R-09, R-12 |
| C-08 | `book_to_skill/pdf_inspector_integration.py:239-285` `enrich_pdf_inspector_metadata` | `pdf_inspector` 필드를 `metadata.json`에 추가하는 규칙 | 1.3 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(정적 읽기, 실행 안 함).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-04 | PDF 하나와 확장자 없는 일반 파일 하나를 넣음 | 두 번째는 경고 후 제외. `total_sources == 1`. 둘 다 실패면 종료 코드 1이고 파일 없음 |
| T-02 | R-05 | `a.txt`, `b.txt` 두 개 | `full_text.txt`에 배너 두 개가 순서대로. `filename == "multi-source"`, `format == "mixed"` |
| T-03 | R-06 | 북마크가 있는 PDF 하나 | 최상위와 `sources[0]` 모두 `chapter_ranges`가 있고, 최상위는 배너 때문에 시작 줄이 소스 쪽보다 큼 |
| T-04 | R-01 | 작업 디렉터리 경로가 심볼릭링크 | 중단, 파일 안 씀 |
| T-05 | 1.3 | 공백으로 단어 750개인 영어 텍스트 | `estimated_tokens == 1000` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-01, C-02 | 코드 읽기 |
| R-03~R-05, R-10, R-12 | C-05, C-07 | `main` 읽기 |
| R-06~R-09 | C-06, C-07 | `main` 읽기. 소스별 `chapter_ranges`는 `src["text"]`, 최상위는 `consolidated_text`를 넘기는 것을 확인(utils.py:1893-1897, 1974-1978) |
| R-11 | `SKILL.md:257` | 명세 텍스트 |
| T-01~T-05 | 위 C-ID | 구현에서 도출, 실행하지 않음 |

### 2.2 코드 읽는 순서
`utils.py` `main`(1804~) → `extract_single_file` 반환부(1643) → `prepare_output_dir`(1663) → `config.py`.
