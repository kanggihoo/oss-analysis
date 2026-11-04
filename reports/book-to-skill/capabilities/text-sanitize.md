---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - book_to_skill/sanitize.py
  - book_to_skill/utils.py
  - book_to_skill/pdf_inspector_integration.py
  - book_to_skill/parsers/pdf.py
  - tests/test_sanitize_bidi_controls.py
depends:
  - ./pdf-extraction.md
status: ready
---

# 텍스트 정화 (`sanitize_extracted_text`)

> 어떤 형식에서 뽑은 텍스트든 보이지 않는 문자(제로폭·방향 제어·태그 블록 등)를 지워 문서에 숨긴 프롬프트 주입을 막고, 깨진 PDF 글꼴이 만든 Kangxi 부수 문자를 원래 한자로 접어 주며, 정화 뒤에 보이는 내용이 없으면 그 소스를 거부한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 형식별 추출이 소스 하나의 텍스트를 만든다(PDF는 엔진 체인까지 끝난 뒤. pdf-inspector 경로는 4번 이후를 자체로 한다).
2. `sanitize_extracted_text`가 텍스트를 받는다. 전부 ASCII면 그대로 돌려준다.
3. 아니면 텍스트에 실제로 쓰인 코드포인트마다 보면서, 지울 코드포인트면 모든 자리에서 지우고, Kangxi 부수면 대응 한자로 바꾼다.
4. 지운 개수가 0보다 크면 stderr에 한 줄을 남긴다(접은 수는 세지 않는다).
5. 정화 결과에서 `strip()`이 비어 있으면 그 소스를 거부한다. 일반 경로는 `ExtractionError`로 중단하고 호출자(`main`)가 그 소스만 건너뛴다. pdf-inspector 경로는 오류 없이 기존 추출 체인으로 돌아간다.
6. 정화된 텍스트로 글자 수·단어 수·토큰 추정·구조 감지를 하고 소스 결과(`text` 포함)를 돌려준다.

### 1.2 범위·통합 지점
- 제공: 삭제 대상·유지 대상의 경계, Kangxi 접기, 삭제 수 보고, 정화 뒤 빈 소스의 거부, 호출 위치와 실패 전달.
- 제외:
  - 생성된 스킬 스캔(`tools/scan_generated_skill.py`). 다만 그 스캐너가 같은 판정 함수 `is_invisible_codepoint`를 가져다 쓴다(R-14).
  - PDF 머리말·쪽번호·하이픈 정리(행 3). 정리가 먼저, 정화가 나중이다(R-11).
  - 쪽 단위 사이드카 기록의 상세(행 6). 정화 호출부의 경계만 R-12에 둔다.
  - 파일명·경로·`metadata.json` 필드·`SOURCE:` 배너의 정화(하지 않는다, R-13).
- 외부 의존·선행 계약: 표준 유니코드 정규화(NFKC)뿐이다. 선행 스펙 `pdf-extraction`은 PDF 엔진 체인이 텍스트 하나를 돌려주는 시점까지를 정하고, 이 스펙은 그 텍스트를 입력으로 받는다. 입력 경계는 "형식별 추출이 끝난 문자열 하나"이다.
- 소유 상태·부작용: 없음(문자열 → (문자열, 정수) 순수 함수). 호출부가 stderr에 알림을 쓴다. 호출 순서상 정화된 텍스트만 `full_text.txt`와 메트릭에 들어간다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `sanitize_extracted_text` | in: string, out: (string, int) | 정화된 텍스트와 **삭제한 코드포인트 수**. 접은 수는 포함하지 않는다. 입력이 전부 ASCII면 `(입력, 0)`. |
| `is_invisible_codepoint` | in: int(코드포인트), out: bool | 삭제 대상인지 판정. 스캐너와 공유하는 공개 함수. |
| `fold_cjk_radicals` | in: string, out: string | Kangxi 부수만 접는다. 삭제 수에 들어가지 않는 별도 공개 함수. `sanitize_extracted_text`는 이 함수를 부르지 않고 같은 접기 표(`_KANGXI_RADICAL_FOLD`)를 직접 쓴다. 소스 안의 다른 호출처는 없다(테스트가 단독 호출). |
| 알림 | stderr 한 줄 | 삭제 수 > 0일 때만: `  [security] removed <N> invisible Unicode code point(s) from <파일명>` (두 호출부 같은 문구) |
| 거부 | 일반 경로: `ExtractionError("Extracted text from <파일명> contained no visible content after Unicode sanitization.")` | pdf-inspector 경로는 오류 대신 기존 체인으로 폴백(R-10). |

삭제 대상 집합은 코드가 글보다 짧고 정확해서 C-01~C-04로 넘긴다. 어떤 코드포인트가 지워지는지는 `is_invisible_codepoint`가 참인 것이 전부다. 경계는 R-04~R-05가 규칙으로 정한다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 일반 경로(`extract_single_file`): EPUB·PDF(Docling 결과 포함)·텍스트·HTML·DOCX·RTF·Calibre 형식 | 형식 분기가 끝난 뒤, 토큰 추정·구조 감지 전에 `sanitize_extracted_text`를 한 번 부른다. 형식별 파서는 정화되지 않은 텍스트를 만든다. | 코드 확인 |
| R-02 | PDF이고 pdf-inspector가 받아들인 Markdown(`text` 모드) | `_result_from_inspector`가 같은 함수를 자체로 부른다. 이 경로의 결과는 `extract_single_file`을 거치지 않으므로 R-01의 호출을 지나지 않는다. | 코드 확인 |
| R-03 | 입력이 전부 ASCII | 텍스트 변경 없음, 삭제 수 0. | 코드 확인 |
| R-04 | 코드포인트가 C-01·C-02의 집합·범위에 든다 | 그 코드포인트는 텍스트의 모든 자리에서 지워진다. 순서는 무관하다. 대상 범주: 제로폭·보이지 않는 구분자(U+200B, 200C, 200D, 2060, FEFF, 00AD, 034F, 180E, 2061-2064), 방향 제어(U+200E, 200F, 061C, 202A-202E, 2066-2069), 한글 필러 4개(U+115F, 1160, 3164, FFA0), 폐기·주석 형식 제어(U+206A-206F, FFF9-FFFB), Default_Ignorable 운반자(U+180B-180D, 180F, 17B4, 17B5, 1BCA0-1BCA3), 음악 형식 제어(U+1D173-1D17A), 태그 블록(U+E0000-E007F), 변이 선택자(U+FE00-FE0F, E0100-E01EF). 위 나열은 C-01·C-02의 요약이고 불일치하면 C-ID가 기준이다. | 코드 확인 |
| R-05 | 코드포인트가 위 집합에 없다 | 유지한다. 경계로 명시: U+2800 점자 공백과 점자 문자는 유지(점자에서 낱말 사이 공백이라 지우면 낱말이 붙는다). 한글 필러 4개는 문자(letter)라 공백 정규화를 지나므로 지운다. 변이 선택자와 Mongolian 자유 변이 선택자는 지운다. 가시 Mongolian·Khmer 문자(U+180A 몽골 니루구, U+17B6 크메르 모음 AA, U+1BC9F 듀플로이안 마침표)는 유지한다. Cf 범주 전체를 지우지 않으며 집합 밖 Cf(아랍·카이티 숫자 기호, 이집트 상형문자 결합자)는 유지한다. 일반 공백(스페이스·탭·NBSP·U+2000-200A)과 줄바꿈은 건드리지 않는다. 범위 끝 바로 바깥(U+2070, U+E0080, U+E01F0, U+1D172, U+1D17B)도 유지한다. | 코드 확인 |
| R-06 | 지워진 문자의 대가 | 변이 선택자를 지우면 이모지·텍스트 표시 힌트가 사라지고, U+200D를 지우면 이모지 ZWJ 시퀀스가 갈라지며, U+200C를 지우면 ZWNJ 철자(예: 페르시아어)가 바뀌고, 몽골·크메르 글에서는 글자 모양 힌트가 사라진다. 소스 주석이 이 손실을 받아들였다고 적었다. 하류의 구조 감지는 이 때문에 ZWJ/ZWNJ가 없는 철자도 인식하도록 되어 있다(`utils.py:259-262`, `:444-448`). | 코드 확인 |
| R-07 | 지워지는 것은 **문자 자체**뿐 | 문자 사이·뒤에 있는 가시 글자는 남는다. 주석 앵커(U+FFF9)~종결(U+FFFB) 사이 글자는 컨트롤만 지워져 본문 안에 평문으로 남는다. 방향 제어는 지워져 화면 순서가 논리 순서와 같아진다. 태그 블록·변이 선택자로 인코딩한 숨은 페이로드는 문자 자체가 지워져 사라진다. 지운 텍스트를 사람에게 보이거나 차단하지는 않는다. | 코드 확인 |
| R-08 | Kangxi 부수(U+2F00-2FDF) 중 NFKC로 다른 문자가 되는 코드포인트 | 그 한자(NFKC 결과)로 바꾼다. 전체 텍스트에 NFKC를 걸지 않는다(전각 형태·합자·원문자·CJK 호환 한자는 그대로). CJK Radicals Supplement(U+2E80-2EF3)는 접지 않는다. 접기는 길이를 바꾸지 않아 삭제 수에 들어가지 않는다. 같은 표를 문자열에 직접 적용하는 `fold_cjk_radicals`가 따로 있지만 정화 흐름은 이 함수를 거치지 않는다. | 코드 확인 |
| R-09 | 반환값 | 삭제 수 = 입력 길이 − 출력 길이(코드포인트). 접기가 1코드포인트를 1코드포인트로 바꾸므로 삭제만 길이를 줄인다. | 코드 확인 |
| R-10 | pdf-inspector 경로에서 정화 뒤 `strip()`이 비었다 | 오류가 아니라 `None`을 돌려 호출자가 inspector 결과를 버리고 원래 `extract_single_file`로 다시 추출한다. 삭제 알림은 이미 출력됐다. 이어지는 폴백 안내 문구는 정화가 아니라 `_fallback_reason`이 고른 일반 문구다. | 코드 확인 |
| R-11 | PDF 엔진 체인(pdftotext → pypdf → pdfminer) | 엔진 간 폴백은 **정화 전** 텍스트의 `strip()`으로 정한다. 정화 전에는 `strip()`이 비지 않지만(제로폭 문자만 있는 경우 등) 정화 후 비는 텍스트는 다음 엔진으로 가지 않고 그 소스가 거부된다. PDF 정리(행 3)가 정화보다 먼저 일어난다. | 코드 확인 |
| R-12 | 쪽 단위 사이드카 경로(`extract_pypdf_page_records`) | 쪽마다 raw 텍스트에 같은 함수를 따로 부르고(PDF 정리 없음), 삭제 수가 0보다 크면 `low_confidence_reasons`에 `sanitized_invisible_text`를 추가한다. 접기만 일어나면 사유가 없다. 이 경로에는 stderr 알림이 없다. 상세는 행 6. | 코드 확인 |
| R-13 | 정화의 대상 | 소스의 텍스트 본문만이다. 파일명과 경로는 `SOURCE:` 배너에, 그 밖의 값은 `metadata.json`에 정화 없이 들어간다. | 코드 확인 |
| R-14 | `is_invisible_codepoint` | 생성된 스킬 스캐너가 같은 함수를 가져다 쓴다(`tools/scan_generated_skill.py:33, 122`). 스캐너 동작은 이 스펙의 범위 밖이다. | 코드 확인 |
| R-15 | 일반 경로에서 정화 뒤 `strip()`이 비었다 | `ExtractionError`(1.3 문구). 사전에 텍스트가 이미 공백뿐이었던 소스(예: 빈 RTF)도 같은 메시지로 거부된다. `main`은 그 소스를 경고와 함께 건너뛰고 다른 소스는 계속한다(S1 R-03). 모든 소스가 실패하면 종료 코드 1(S1 R-04). `strip()`은 파이썬 기준 공백만 뗀다: U+2800만 있는 텍스트는 보이는 내용이 있다고 본다. | 코드 확인 |
| R-16 | 정화 뒤 메트릭 | 소스의 `chars`·`words`·`estimated_tokens`와 구조 감지는 정화된 텍스트로 계산한다(S1 1.3). | 코드 확인 |
| R-17 | 정화가 같은 입력을 두 번 받음 | 한 번 정화한 텍스트를 다시 정화해도 변하지 않는다(삭제 뒤 새 삭제 대상이 생기지 않고 접은 한자는 대상이 아님). | 추론 |

- 불변식: 정화 결과에는 `is_invisible_codepoint`가 참인 코드포인트가 없고 접기 대상 Kangxi 코드포인트도 없다(코드 확인, 전제: 문자열은 코드포인트 열). 삭제 수는 길이 차이와 같다(R-09).
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했고 실행하지 않았다. 접기 대상이 정확히 몇 개인지는 파이썬 `unicodedata`의 NFKC 결과로 정해져 유니코드 버전에 의존한다(U+2F00-2FDF 중 U+2FD5까지 214개가 한 코드포인트 한자로 매핑됨을 표준 유니코드 데이터로 별도 확인했고, 레포 코드는 실행하지 않았다). 삭제 집합은 정적 목록이라 새 유니코드 버전이 Default_Ignorable 문자를 더하면 따라가지 않는다(소스 주석이 인정한 절충).

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `book_to_skill/sanitize.py:11-118` `_ZERO_WIDTH_CODEPOINTS`, `_BIDI_CONTROL_CODEPOINTS`, `_INVISIBLE_LETTER_CODEPOINTS`, `_ANNOTATION_FORMAT_CODEPOINTS`, `_DEFAULT_IGNORABLE_CARRIER_CODEPOINTS`, `_INVISIBLE_CODEPOINTS` | 삭제 대상 명시 집합 5개와 그 합집합. 주석이 각 그룹을 삭제한 이유와 유지한 이웃(U+180A, U+17B6, U+1BC9F, U+2800)을 적는다 | R-04, R-05, R-06 |
| C-02 | `book_to_skill/sanitize.py:122-138, 155` `_TAG_BLOCK_START/_END`, `_VARIATION_SELECTOR_RANGES`, `_MUSICAL_FORMAT_RANGE` | 범위로 지우는 것: 태그 블록, 변이 선택자 두 범위, 음악 형식 제어. 같은 파일의 `_DEPRECATED_FORMAT_RANGE`(145)와 `_ANNOTATION_CODEPOINTS`(147-151)는 판정에 쓰이지 않는다(2.1 참고) | R-04, R-05 |
| C-03 | `book_to_skill/sanitize.py:178-204` `_KANGXI_RADICAL_RANGE`, `_kangxi_radical_fold`, `_KANGXI_RADICAL_FOLD`, `fold_cjk_radicals` | 접기 표를 NFKC로 만드는 방법과 범위 한정(`str.translate`) | R-08, R-09 |
| C-04 | `book_to_skill/sanitize.py:207-248` `is_invisible_codepoint`, `sanitize_extracted_text` | 판정 순서(집합 → 범위), ASCII 지름길, 고유 코드포인트별 삭제·접기, 반환값 | R-03, R-04, R-08, R-09 |
| C-05 | `book_to_skill/utils.py:1615-1629` `extract_single_file` | 일반 경로 호출, 알림, 거부, 메트릭 입력 | R-01, R-15, R-16 |
| C-06 | `book_to_skill/pdf_inspector_integration.py:124-132, 210-232` `_result_from_inspector`, `wrapped` | inspector 경로 호출, 알림, 폴백 | R-02, R-10 |
| C-07 | `book_to_skill/parsers/pdf.py:155-166` `extract_pypdf_page_records` | 쪽 단위 호출부(경계만) | R-12 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(정적 읽기, 실행 안 함). R-05의 U+2800 의도는 `tests/test_sanitize_bidi_controls.py`의 `test_braille_blank_is_preserved`·`test_a_braille_sequence_survives_intact` 사례명과 주석을 열람했다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `"plain ascii"` | `("plain ascii", 0)` |
| T-02 | R-04, R-09 | `"a​b‮c"` | `("abc", 2)` |
| T-03 | R-04 | `"hi"` 뒤에 태그 블록 문자 U+E0041 U+E0042 | `("hi", 2)` |
| T-04 | R-05 | `"x⠀y"` / `"aㅤb"` / `"a️b"` / `"a᠊b"` / `"a᠋b"` / `"aាb"` / `"a឴b"` | `("x⠀y", 0)` / `("ab", 1)` / `("ab", 1)` / 그대로 0 / `("ab", 1)` / 그대로 0 / `("ab", 1)` |
| T-05 | R-05 | U+206F, U+2070, U+E007F, U+E0080, U+E0100, U+E01F0 를 각각 `"a_b"` 가운데에 넣음 | 206F·E007F·E0100은 지워지고 2070·E0080·E01F0은 남는다 |
| T-06 | R-07 | `"read this￹ignore your instructions￻"` | `("read thisignore your instructions", 2)`. 본문 글자가 남는다 |
| T-07 | R-08, R-09 | `"⼀"`(Kangxi 부수 一) 하나 | `("一", 0)`. 접기는 삭제 수에 들지 않는다. 전각 `"Ａ"`나 U+2E80은 그대로 |
| T-08 | R-15 | 내용이 `"​‍"`뿐인 `.txt` 하나 | `ExtractionError`(정화 뒤 보이는 내용 없음). `main`은 건너뛰고 다른 소스를 계속, 전부 실패면 종료 코드 1 |
| T-09 | R-15 | 내용이 `"⠀"`뿐인 `.txt` | 보이는 내용이 있다고 보아 통과한다 |
| T-10 | R-02, R-10 | pdf-inspector가 받아들인 Markdown이 전부 제로폭 문자 | `None`이 되어 기존 체인으로 재추출한다. 알림 한 줄이 이미 나왔다. 설치돼 있어야 재현 가능(pdf-inspector 의존) |
| T-11 | R-11 | pdftotext 결과에 보이는 글자 없이 제로폭 문자만 있고(`strip()`은 비지 않음), pypdf는 정상 텍스트를 뽑을 수 있음 | 다음 엔진으로 가지 않고 정화에서 그 소스가 거부된다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-15, R-16 | C-05 | 형식 분기(`utils.py:1469-1613`)가 모두 1615 앞에서 끝나는 것을 읽어 확인 |
| R-02, R-10 | C-06 | `wrapped`에서 `_result_from_inspector`가 `None`이면 `original` 호출(`:221-232`)을 읽어 확인 |
| R-03, R-04, R-08, R-09 | C-01~C-04 | 코드 읽기. 접기 대상 수는 한 번 확인한 외부 유니코드 데이터 값(1.4 확인 한계) |
| R-05 | C-01, C-02, C-04 | 집합에 없음을 읽어 확인. 의도는 소스 주석(`sanitize.py:78-98`)과 `tests/test_sanitize_bidi_controls.py`의 사례명(`test_braille_blank_is_preserved`, `test_visible_neighbours_and_semantic_controls_are_kept`, `test_neighbours_of_the_selector_ranges_are_kept`, `test_legitimate_mongolian_keeps_its_letters` 등)을 열람해 맞췄다 |
| R-06 | C-01, C-02 주석, `utils.py:259-262`, `:444-448` | 주석 읽기 |
| R-07 | C-04 | 삭제가 코드포인트 단위(`str.replace`)임을 읽어 확인. `test_hidden_annotation_text_is_removed_with_its_controls`는 이름과 달리 컨트롤 삭제만 단언한다 |
| R-11 | `utils.py:1543-1573`(체인), C-05 | 체인의 `text and text.strip()` 검사가 정화 호출 앞임을 확인 |
| R-12 | C-07 | 호출부와 `if removed` 분기를 읽어 확인 |
| R-13 | `utils.py:1836-1862`(S1 C-05) | 정화 호출이 `res["text"]` 내부에 있고 배너는 `res['filename']`을 그대로 쓴다 |
| R-14 | `tools/scan_generated_skill.py:33, 122` | import와 사용 줄을 읽음 |
| R-17 | C-04 | 구조에서 짐작한 것. 실행하지 않았다 |
| T-01~T-11 | 위 C-ID | 구현에서 도출, 실행하지 않음 |

문서와 구현의 차이:
- `sanitize.py:16`의 주석은 U+FEFF를 "BOM outside position 0"이라 적지만 판정은 위치와 무관하다. 문서 시작의 U+FEFF도 지운다(`is_invisible_codepoint`는 위치를 보지 않음).
- 상수 `_DEPRECATED_FORMAT_RANGE`(`:145`)와 `_ANNOTATION_CODEPOINTS`(`:147-151`)는 정의만 있고 판정에 쓰이지 않는다. 같은 코드포인트는 `_ANNOTATION_FORMAT_CODEPOINTS`(`:66-76`)로 이미 지워진다. 이 스펙은 판정에 쓰이는 것만 기준으로 삼았다.
- 소스 주석의 그룹 번호(1~9)가 순서대로가 아니다. 의미 차이는 없다.
- 테스트 `test_hidden_annotation_text_is_removed_with_its_controls`의 이름은 숨은 글자가 지워진다고 읽히지만 구현은 컨트롤만 지운다(R-07).

### 2.2 코드 읽는 순서
`sanitize.py` `sanitize_extracted_text`(228) → `is_invisible_codepoint`(207) → 상수(11-155) → `fold_cjk_radicals`(196). 호출부는 `utils.py:1615`, `pdf_inspector_integration.py:124`. 구현 전략: 고유 코드포인트만 순회하며 `str.replace`를 해서 다국어 텍스트에서 문자별 조회를 피한다.

### 2.3 비교·재사용 출처
없음. 코드를 복사하지 않았다. 원본 라이선스는 MIT(overview 1절).

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-07 | 주석 앵커~종결 사이에 숨은 글자가 있으면 경고하거나 함께 제거 | 원본은 컨트롤만 지워 지시문이 평문으로 남는다 | 반환값에 "의심 구간 수"가 늘고 T-06 기대값이 바뀐다 |
| R-11 | 엔진 간 폴백 판정을 정화 뒤 텍스트로 | 지금은 정화로만 빈 텍스트가 되면 다음 엔진을 시도하지 않는다 | 체인 순서가 "추출 → 정화 → 폴백 판정"으로 바뀌고 T-11 기대값이 바뀐다 |
| R-15 | 사전에 이미 빈 텍스트인 소스는 정화 문구와 다른 메시지로 | 오류 문구가 원인을 오도한다 | 오류 문구만 바뀐다 |
