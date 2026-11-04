---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - book_to_skill/utils.py
  - book_to_skill/parsers/pdf.py
  - book_to_skill/pdf_inspector_integration.py
depends:
  - ./text-sanitize.md
  - ./extract-artifacts.md
status: ready
---

# 구조 감지·장 범위 (`detect_structure`, `apply_pdf_outline`, `chapter_line_ranges`)

> 정화된 텍스트 한 덩어리(PDF면 원본 PDF 경로도)를 받아 장 수·장 제목 샘플·ToC 유무를 정하고, PDF 북마크(outline)가 쓸 만하면 그 제목으로 장별 줄 범위(`chapter_ranges`)까지 계산한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 소스 하나의 추출 텍스트가 정화를 마치면(정화 결과가 비면 이 단계에 오지 않는다) `detect_structure(text)`를 부른다.
2. **numeric 스캔**: 코드 펜스 밖의 모든 줄에서 장 제목 모양("Chapter 5", "第三章", "1  Intro" 등)을 찾고 **서로 다른 장 번호**를 센다. 2개 이상이면 `numeric`으로 끝낸다.
3. 2개 미만이면 **structural 스캔**(Markdown/AsciiDoc/RST 제목)을 하고, numeric 개수와 비교해 `structural`/`numeric`/`none` 중 하나로 정한다. numeric·structural이 모두 0이면 "Part N"만으로 세는 폴백이 있다.
4. ToC 유무(`has_toc`)는 앞 30,000자에서 ToC 머리말 줄을 찾아 정한다. 장 방법과 무관하다.
5. 소스가 PDF이면 `apply_pdf_outline(structure, pdf_path)`가 북마크에서 장·부록 등을 거른 제목을 2개 이상 얻을 때 위 결과를 `outline`으로 덮는다. 모자라면 2~4의 결과를 그대로 둔다.
6. `outline`인 소스는 `metadata.json`을 만들 때 `chapter_line_ranges(text, chapter_titles, range_end_titles=…)`로 제목마다 텍스트에서 시작 줄을 찾고, 다음 장 시작 또는 "끝 경계" 제목까지를 그 장의 범위로 계산한다(어느 텍스트에 적용하는지는 [S1 R-06](./extract-artifacts.md)). 못 찾은 제목은 경고 후 건너뛴다.

### 1.2 범위·통합 지점
- 제공: 4개 구조 필드(`chapters_detected`, `chapters_method`, `chapter_headings_sample`, `has_toc`)의 값을 정하는 규칙, outline일 때의 `chapter_titles`와 `chapter_ranges` 값을 정하는 규칙.
- 제외: 장 요약 생성, 여러 소스를 합칠 때의 병합·재감지와 `chapter_ranges`의 위치·최상위 덮어쓰기([S1](./extract-artifacts.md) R-05~R-08), 경고 문구 출력 위치(S1 R-09), 형식별 추출(행 2~4, 7).
- 선행 계약: 입력 텍스트는 정화를 마친 문자열이다([text-sanitize](./text-sanitize.md)). 이 기능은 정화를 호출하지 않는다. 장 라벨의 다국어 패턴 일부(싱할라 ZWJ, 페르시아 ZWNJ)는 "정화가 해당 문자를 이미 지웠다"를 전제하되 지우지 않은 입력도 받도록 쓰여 있다(C-03, C-05).
- 외부 의존: `pypdf`(없거나 읽기 실패면 outline 제목이 빈 목록이 된다). 다른 외부 호출은 없다.
- 소유 상태·부작용: 상태 없음. 순수 함수이고, 부작용은 `chapter_line_ranges`가 못 찾은 제목마다 stderr에 쓰는 경고뿐이다.

### 1.3 인터페이스와 데이터 의미

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `detect_structure(text)` | 정화된 텍스트 → dict 4필드 | 아래 표. 항상 4필드가 있다 |
| `apply_pdf_outline(structure, pdf_path)` | `detect_structure` 결과, PDF 경로 → dict | outline 채택 시 `structure`의 복사본에 `chapters_detected`, `chapters_method="outline"`, `chapter_headings_sample`, `chapter_titles`, `chapter_range_end_titles`를 덮어 쓴 새 dict. 아니면 입력 그대로(같은 객체) |
| `pdf_outline_titles(pdf_path)` | PDF 경로 → string 목록 | 최상위 북마크 제목. 읽기 실패·북마크 없음이면 `[]` |
| `pdf_outline_all_titles(pdf_path)` | PDF 경로 → string 목록 | 모든 깊이의 북마크 제목, 문서 순서 |
| `chapter_line_ranges(text, chapter_titles, *, range_end_titles=None)` | 텍스트, 제목 목록 → `[{title, start_line, end_line}]` | 줄 번호는 1부터, 시작·끝 포함. 못 찾은 제목은 목록에서 빠진다 |

**`detect_structure` 결과**
| 필드 | 값 |
|---|---|
| `chapters_detected` | 정수(0 이상) |
| `chapters_method` | `numeric` / `structural` / `none` (`apply_pdf_outline`이 `outline`을 더함) |
| `chapter_headings_sample` | 문자열 최대 10개. 방법에 따라 출처가 다르다(R-05, R-06, R-17) |
| `has_toc` | bool |

`chapter_titles`와 `chapter_range_end_titles`는 `outline`일 때만 구조 dict에 있다. `chapter_range_end_titles`는 소스 항목 dict 안에서만 쓰이고 `metadata.json`에는 쓰이지 않는다(R-20). 필드가 `metadata.json`의 어디에 놓이는지는 [S1 1.3](./extract-artifacts.md).

### 1.4 행동 규칙과 남은 질문

**입력과 순서**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 소스 하나의 정화된 텍스트 | 정화 직후 `detect_structure`를 부르고, 소스가 `.pdf`이면 이어서 `apply_pdf_outline`을 부른다. pdf-inspector 경로(Markdown을 그대로 쓰는 PDF)도 같은 두 호출을 같은 순서로 한다. 결과 dict는 소스 결과에 펼쳐 들어가고, 결과 한 줄 `chapters: N (method)`를 출력한다 | 코드 확인 |
| R-02 | 줄 단위 처리 | 텍스트를 `str.splitlines()`로 나눈다. 닫힌 코드 펜스(C-07)에 든 줄은 numeric·structural 두 스캔 모두에서 건너뛰고, 건너뛴 줄은 "윗줄"(`prev`)도 비운다. 닫히지 않은 펜스는 본문으로 취급한다(뒤의 제목을 모두 잃지 않으려는 의도) | 코드 확인 |

**numeric 스캔**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-03 | 빈 줄이 아니고 펜스 밖인 모든 줄(텍스트 전체, 앞부분만이 아니다) | `_chapter_number(line, prev)`가 정수를 돌려주면 장 제목 후보. `prev`는 바로 위의 비어 있지 않은 줄이고 빈 줄·펜스에서 비워진다. 후보 줄(strip)을 `headings`에 **중복 포함해 순서대로** 쌓고, 번호는 집합에 넣어 **서로 다른 번호 개수**를 센다. 그래서 ToC 항목과 본문 제목이 같은 번호면 1개로 센다. 번호 공간은 모든 라벨 형식이 공유한다("Chapter 1"과 "1  Intro"와 "I: …"는 모두 1) | 코드 확인 |
| R-04 | 후보 줄에서 Markdown 접두사(`#`, `=`)를 뗀 제목이 `part N`(숫자 또는 로마 숫자)으로 시작 | 장이 아니라 Part로 분리한다(`part_headings`, `part_numbers`). 장 개수에 들어가지 않는다. 일반 장 번호가 2개 이상이어도 Part는 무시된다 | 코드 확인 |
| R-05 | 서로 다른 장 번호 ≥ 2 | `chapters_method="numeric"`, `chapters_detected`=번호 개수, `chapter_headings_sample`=`headings`의 앞 10개. structural 스캔은 하지 않는다 | 코드 확인 |

**numeric < 2일 때의 판정(structural 포함)**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 서로 다른 번호 < 2 | `structural_count`를 구한 뒤 `chapters_detected = max(numeric_count, structural_count)`. 방법은 `structural_count > numeric_count`이면 `structural`, 아니고 `numeric_count > 0`이면 `numeric`, 둘 다 0이면 `none`. 샘플은 `structural`이면 structural 제목 앞 10개, 아니면 `headings` 앞 10개. 같은 개수(예: 1 대 1)는 `numeric`이 이긴다 | 코드 확인 |
| R-07 | numeric 0개이고 structural 0개 | Part 폴백: 개수를 `len(part_numbers)`로, 샘플 원본을 `part_headings`로 바꾼다. 개수가 양수면 방법은 `numeric`. 일반 장이 1개라도 있으면 폴백은 일어나지 않는다 | 코드 확인 |

**장 제목 모양과 오탐 방어(`_chapter_number`)**

판정 순서는 아래 R-08~R-13이다. 각 분기에서 정규식이 맞으면 그 분기의 결과(번호 또는 `None`)로 판정이 끝나고 다음 분기로 가지 않는다(단 R-08의 diff 마커 예외). 줄은 먼저 `strip`하고 Kangxi 부수 숫자 4개(⼀⼆⼋⼗)를 일반 한자로 바꾼다. 줄이 80자를 넘으면 `None`이다.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | `숫자(1~999)` + 공백 2개 이상 + 비공백("1  Introduction") | 그 숫자가 장 번호. 공백 하나("1. Item", "1 Item")는 해당 없음(목록 항목 방어). 비공백 첫 글자가 `+`나 `-`면(통합 diff 줄) 이 분기만 건너뛰고 아래 분기로 내려간다 | 코드 확인 |
| R-09 | 라틴 장 단어(`chapter`·`unit`·`lesson`·`module`·`lecture`·`part`·`chapitre`·`kapitel`·`capítulo`·`capitolo`·`hoofdstuk`·`chương`·`ch`·`ch.`, 대소문자 무시) + 숫자 1~2자리 또는 로마 숫자 + 꼬리 | 꼬리가 줄 끝이거나 `. : - — –`로 시작하거나 "공백 + 소문자 a-z가 아닌 글자"로 시작해야 장 제목. 소문자로 이어지는 문장("Chapter 6 explores…")과 번호 바로 뒤에 `)` 같은 위 조건 밖 문자가 오는 줄("Chapter 6)")는 상호 참조/본문으로 보고 `None`(이 분기에서 끝). 연도처럼 3자리 이상 숫자는 `\b` 때문에 맞지 않는다 | 코드 확인 |
| R-10 | R-09의 꼬리가 마침표로 시작하고(`Chapter 4. …`), 제목이 `#`/`==` 접두사 없이 쓰였으며, 윗줄이 있고 문장 끝 문자(`. ! ? … : ; " ' ” ’ ) ]`)로 끝나지 않음 | 윗줄에서 이어진 문장이 열 너비에서 접힌 것으로 보고, 마침표 뒤 단어(영문·숫자 포함 토큰)가 0개이거나 8개를 넘으면 `None`. 8개 이하의 제목 같은 꼬리는 장으로 둔다. 윗줄이 없거나(빈 줄·펜스 뒤) 문장이 끝난 줄이면 제목으로 둔다. 접두사가 붙은 제목("## Chapter 4. …")은 윗줄과 무관하게 신뢰한다 | 코드 확인 |
| R-11 | 로마 숫자 장 번호 | 대문자 로마 숫자 + `:`/`.` + 공백 + 대문자·숫자·따옴표·`(`로 시작하는 제목("II. The Carpet-Bag"), 또는 `#` 접두사가 붙은 소문자 로마 숫자("## i. introduction")만 인정. 값은 1~200의 정규형이어야 한다(`IIII`, `VV`는 `None`). R-09의 로마 숫자(`Part IV`)도 같은 변환을 쓴다 | 코드 확인 |
| R-12 | 비라틴 라벨: 중국어(第N章/回/卷/节/篇/讲, `## 一 · …`), 태국어, 힌디, 벵골, 오리야, 타밀, 싱할라, 텔루구, 칸나다, 말라얄람, 구자라트, 펀자브, 러시아어, 그리스어, 히브리어, 아르메니아어, 한국어(제N장/편/절/관), 페르시아어 | 라벨 단어 바로 뒤에 숫자가 있어야 한다("라벨 단어만 있는 문장"과 어형 변화형은 거부). 현지 숫자는 아라비아 숫자로 바꾼다(중국어는 십·백·천 단위 합성, 1~999). 한국어·페르시아어는 라틴식 대문자 판별이 없어 "줄 끝 / 구두점 / 공백 뒤 내용"을 꼬리 조건으로 쓴다(`제5장에서`는 거부). 페르시아어는 단어 서수 1~34도 받고 짧은 서수(1~10)는 구분자가 있어야 한다. 대부분 `#` 접두사를 정규식 안에서 허용한다. 판정 순서는 C-11의 분기 순서 | 코드 확인 |
| R-13 | 위 분기들이 모두 `None`이고 줄이 `#`~`######` 또는 `=`~`======` + 공백으로 시작 | 접두사를 떼고 같은 판정을 한 번 더 한다(`heading_marked=True`, 윗줄 없음). 그래서 Docling 같은 Markdown 출력도 일반 텍스트와 같은 장을 센다. 단, 접두사가 붙은 줄은 R-10의 마침표 꼬리 검사를 받지 않는다 | 코드 확인 |

**structural 스캔(`_structural_chapter_headings`)**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | 펜스 밖의 줄 | 제목 후보 두 종류. (a) ATX/AsciiDoc: `#`~`######` 또는 `=`~`======` + 공백 + 제목(끝의 `#`들 제거). 깊이는 표지 글자 수. 제목이 비었거나 `\w`가 하나도 없으면(표 테두리 `=====`) 거부. (b) setext/RST 밑줄: `=`(깊이 1) 또는 `-`(깊이 2) 2개 이상으로만 된 줄이 **바로 윗줄이 비어 있지 않고, 윗줄이 밑줄 줄 자체가 아니며, 윗줄 길이 ≤ 밑줄 길이이고, 윗줄에 `\w`가 있을 때**. 후보 제목은 깊이별로 대소문자 무시(casefold) 중복 제거하되 첫 등장의 원문을 샘플로 둔다. 밑줄 없는 `=====`는 RST 장식으로 보고 무시한다 | 코드 확인 |
| R-15 | 후보 제목이 앞표지·머리말 등(`cover`, `preface`, `foreword`, `acknowledg(e)ments`, `dedication`, `copyright`, `epigraph`, `prologue`), 뒷부분(`bibliography`, `references`, `works cited`, `further reading`, `index`, `glossary`, `notes`, `endnotes`, `footnotes`, `colophon`, `about the author(s)`) 중 **제목 전체가 일치**하거나, ToC 머리말과 전체 일치하거나, `appendix`/`appendices`로 시작하거나, `part N`으로 시작 | 장 후보에서 제외한다(깊이별 집합에 넣지 않는다). "Indexing Strategies", "Glossary of Terms"처럼 전체가 다른 제목은 장으로 남는다. 단 제외된 제목 줄도 본문 길이 계산에서 구역 경계(R-16)로는 쓰인다 | 코드 확인 |
| R-16 | 첫 글자가 숫자인 ATX 제목("## 1. Introduction", "## 5 Setup") | 즉시 장으로 세지 않고 깊이별로 모아 두었다가, 그 깊이의 항목이 **3개 이상**이고 각 항목 본문 길이의 **중앙값이 200자 이상**일 때만 장으로 받아들인다. 본문 길이는 그 제목 다음 줄부터 다음 제목 줄(모든 깊이의 ATX 제목과 setext 밑줄 줄, 장 후보에서 제외된 제목 포함, 펜스 안 줄은 제목으로 세지 않음)까지 줄 길이(글자 수) 합이다. 번호가 1부터 오름차순인지는 보지 않는다. 단계 목록("Step 1/2/3")과 논문·책의 번호 절을 가르는 휴리스틱이다 | 코드 확인 |
| R-17 | 깊이별 후보가 모인 뒤 | 후보가 **서로 다른 제목 2개 이상**인 가장 얕은 깊이의 제목 목록을 돌려준다("# 책 제목 / ## 장" 구조에서 최상위가 1개뿐인 경우 H2를 고르는 효과). 그런 깊이가 없으면 모든 깊이의 제목을 얕은 깊이부터 이어 붙여 돌려준다(얇은 문서용 폴백. 깊이마다 제목이 1개씩이면 깊이 수만큼 나온다). 아무 후보도 없으면 빈 목록. 이 호출은 numeric < 2일 때만 일어난다 | 코드 확인 |

**has_toc**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | 텍스트의 **앞 30,000자** | 한 줄 전체가 ToC 머리말(C-06: 영어·스페인어·포르투갈어·프랑스어·독일어·이탈리아어·네덜란드어 단어, 중국어 目录/目錄/目次, 앞에 `#` 허용, 대소문자 무시)이면 `has_toc=True`. 줄 중간의 "contents of this chapter"는 맞지 않는다. 본문 구조 방법(numeric/structural/outline)과 독립이다 | 코드 확인 |

**PDF outline**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | `pdf_outline_titles` | 최상위 북마크 제목만 읽는다(자식 목록은 건너뜀). 제목이 `Part N`이고 바로 뒤에 자식 목록이 있으면 그 Part 대신 **자식의 제목들**(자식의 자식은 제외)을 쓴다. 자식 목록이 없는 Part는 그대로 남는다. 빈 제목은 버린다. `pypdf` 임포트·열기·`outline` 읽기 중 어떤 예외든 `[]` | 코드 확인 |
| R-20 | `apply_pdf_outline` | `pdf_outline_titles`에서 R-15의 "장 아님"(front/back matter, ToC, appendix, Part)을 걸러낸 제목이 **2개 미만이면 입력 `structure`를 그대로** 돌려준다(휴리스틱 결과 유지, 경고 없음). 2개 이상이면 `chapters_detected=len(제목)`, `chapters_method="outline"`, 샘플=앞 10개, `chapter_titles`=걸러진 전체 제목, `chapter_range_end_titles`=`pdf_outline_all_titles`(모든 깊이)에서 "장 아님"인 제목들. `has_toc`는 텍스트 스캔 값 그대로다. `chapter_range_end_titles`는 소스 dict에만 남고 `metadata.json`에는 쓰이지 않는다 | 코드 확인 |
| R-21 | `pdf_outline_all_titles` | 모든 북마크 제목을 깊이 우선 문서 순서로 평탄화한다. 읽기 예외·빈 outline이면 `[]` | 코드 확인 |

**장별 줄 범위(`chapter_line_ranges`)**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | 제목 목록을 문서 순서대로 | 제목마다 직전 장 시작 줄의 다음 줄부터 텍스트 끝까지 위에서 아래로 검색해 **처음 맞는 줄**을 시작으로 삼는다(탐색은 단조 증가). 못 찾으면 stderr에 `WARNING: outline chapter not found in extracted text: '<title>'`를 쓰고 그 제목만 건너뛴다(다음 제목은 같은 위치에서 계속 탐색). 찾은 제목이 하나도 없으면 `[]`. 따라서 `len(chapter_ranges) < len(chapter_titles)`일 수 있고 `chapters_detected`는 줄어들지 않는다. 같은 호출이 `sources[]`용과 단일 소스 최상위용으로 따로 일어나 경고가 두 번 나올 수 있다 | 코드 확인 |
| R-23 | 줄 하나가 제목 하나의 시작인지(순서대로 처음 맞는 규칙) | (0) 빈 줄, 쪽 머리말(`숫자 | Chapter 숫자`), 점 3개 이상 이어진 줄(ToC 안내선)은 후보에서 제외. 제목 `bare`는 북마크 제목에서 선두 `Chapter N[.:]`을 뗀 것, `full`은 북마크 제목 전체. (1) 줄에서 `#`/`=` 접두사를 떼고 끝의 `.`을 제거한 뒤 casefold한 값이 `bare`나 `full`과 같거나, 줄 원문 casefold가 `bare`와 같으면 시작. (2) 이 줄 + 공백 + 다음 줄(다음 줄도 제외 대상 아님)이 `bare`나 `full`과 같으면 시작(제목이 두 줄로 접힌 경우, 접두사 정규화는 하지 않음). (3) 이 줄이 `CHAPTER <숫자>`만 있는 줄이면 이후 3줄 안에서 제외 대상이 아닌 줄의 정규화 제목이 `bare`와 같거나 두 줄 합이 `bare`와 같을 때 시작은 이 `CHAPTER N` 줄이다. (1)·(2)로 시작이 정해졌는데 바로 윗줄이 `CHAPTER <숫자>`뿐이면 시작을 그 윗줄로 한 줄 올린다 | 코드 확인 |
| R-24 | 시작 줄이 정해진 뒤 끝 줄 | 끝은 **다음 장 시작 줄(없으면 텍스트 끝) 직전**이 기본이다. 단 시작 다음 줄부터 다음 장 시작 전까지 훑어 처음 만나는 "끝 경계" 줄이 있으면 그 줄 직전에서 끊는다(경계 줄과 그 뒤 다음 장 시작 전까지는 어느 장의 범위에도 속하지 않는다). 끝 경계는 (a) 줄의 정규화 제목(R-23 (1)과 같은 정규화)이 `range_end_titles`(R-20) 중 하나와 정확히 같을 때(위치·고립 여부 무관), (b) `Part N` 또는 `appendix`/`appendices`로 시작하는 제목 줄이 앞뒤가 모두 빈 줄(또는 문서 처음·끝)인 단독 줄일 때. 쪽 머리말 줄은 경계가 아니다. 결과 범위는 `{title, start_line(1부터), end_line}`이고 `end_line`은 끝 줄 번호(포함)다. 범위 안에 선행·후행 빈 줄이 들어 있을 수 있다 | 코드 확인 |

**실패 방식과 경고**
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | 장이 1개로 잡히는 경우 | 장 제목이 번호 라벨이 아니고 Markdown/AsciiDoc/RST 제목도 아닌 순수 텍스트·PDF(북마크 없음)는 `none`, 0개다. 책이 H1 한 개 + 장 없는 구조이거나 서로 다른 깊이에 하나씩이면 R-17의 폴백으로 `structural` 1~2개가 나온다. `structural`인데 `chapters_detected ≤ 1`이고 전체 단어 수 > 5000이면 실행 요약에 "chapter detection likely failed" 경고가 나온다([S1 R-09](./extract-artifacts.md)). `none`·`numeric` 1개는 이 경고가 없고, ToC가 없다는 경고만 있다. 어느 경우도 중단하지 않고 값만 기록한다 | 코드 확인(경고 조건은 S1) |
| R-26 | outline이 있어도 본문에서 제목을 못 찾는 경우 | R-22의 경고와 건너뜀. outline 제목이 본문에서 변형된 경우(쪽 머리말 섞임, 대소문자·구두점 차이는 casefold로 흡수되지만 단어 차이는 흡수되지 않음, 한 줄 초과로 접힘)는 못 찾을 수 있다. ToC 쪽에 안내선 없이 제목만 있는 줄이 있으면 첫 일치가 ToC 줄로 잡힐 수 있다(윗줄·아랫줄 검사가 없다) | 코드 확인(앞부분), 추론(ToC 줄 오인) |
| R-27 | 줄 번호 기준 | 줄은 `splitlines()`로 센다. `\n` 외에 `\r`, `\f`, `\v`, U+0085, U+2028/2029 등도 줄 끝이다. `full_text.txt`를 `\n` 기준으로 읽는 소비자와 줄 번호가 어긋날 수 있는 입력은 이 문자들이 텍스트에 남아 있을 때뿐이다 | 코드 확인(함수 선택), 추론(어긋남) |

- 불변식: 같은 정화 텍스트와 같은 PDF는 같은 구조 결과를 낸다(난수·시간·외부 호출 없음, outline 읽기는 PDF 파일만 본다). 네 개의 `detect_structure` 필드는 항상 존재한다. `chapter_ranges`의 각 항목은 `start_line ≤ end_line`, 항목 사이는 겹치지 않고 문서 순서다.
- 미결정: 없음
- 확인 한계: 정적 읽기만 했고 실제 PDF·pypdf를 실행하지 않았다. `pypdf`의 `outline`이 "Destination 객체와 하위 목록이 번갈아 나오는 목록"이라는 구조는 코드(`isinstance(item, list)`)가 가정한 모양이며 외부 라이브러리 동작은 확인하지 않았다. 언어별 라벨 판별이 실제 책에서 얼마나 맞는지는 확인하지 않았다(코드가 정한 판별만 규칙으로 썼다).

### 1.5 필수 코드 참조
정규식·언어 표·판별 알고리즘은 아래 범위를 그대로 가져가는 편이 글보다 짧고 정확하다. 각 범위가 쓰는 내부 상수·helper는 같은 표의 다른 C-ID에 있다(괄호에 연결을 적었다).

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `book_to_skill/utils.py:111-156` `_EXPLICIT_CHAPTER`, `_HEADING_TAIL`, `_PERIOD_TAIL`, `_TAIL_WORD`, `_TITLE_TAIL_MAX_WORDS`, `_SENTENCE_END`, `_ROMAN_HEAD`, `_LC_MD_ROMAN`, `_ROMAN_VALUES`, `_MD_HEADING_PREFIX` | 라틴 장 단어 목록·꼬리 규칙·마침표 꼬리 임계값(8단어)·로마 숫자 머리말·Markdown 접두사 정규식 | R-09~R-11, R-13 |
| C-02 | `book_to_skill/utils.py:158-191` `_CN_NUM_VALUES`, `_CN_NUM_UNITS`, `_CN_NUM_CLASS`, `_KANGXI_NUMERAL_TRANS`, `_FW_DIGITS`, `_CN_CHAPTER`, `_MD_CN_HEADING` | 중국어 장 정규식, Kangxi 부수 숫자 4개 치환, 전각 숫자 허용 | R-12 |
| C-03 | `book_to_skill/utils.py:193-379` `_TH_*`, `_HI_*`, `_BN_*`, `_OR_*`, `_TA_*`, `_SI_*`, `_TE_*`, `_KN_*`, `_ML_*`, `_GU_*`, `_PA_*`, `_RU_CHAPTER`, `_EL_CHAPTER`, `_HE_CHAPTER`, `_HY_CHAPTER` | 비라틴 언어별 장 단어·자릿수 표·숫자 치환표(`str.maketrans`). 순수 표라 구현은 이 표를 그대로 옮긴다 | R-12 |
| C-04 | `book_to_skill/utils.py:381-395` `_KO_CHAPTER` | 한국어 `제N장/편/절/관(의N)` + 꼬리 조건 | R-12 |
| C-05 | `book_to_skill/utils.py:397-483` `_FA_*`, `_fa_ordinal_map`, `_fa_chapter_number` | 페르시아어 라벨·숫자·서수 1~34 표와 꼬리 규칙(`_FA_ORDINALS`는 ZWNJ를 지운 철자도 등록) | R-12 |
| C-06 | `book_to_skill/utils.py:486-545` `_TOC_HEADERS`, `_TOC_CJK_PATTERN`, `_TOC_PATTERN`, `_FRONT_MATTER_HEADERS`, `_BACK_MATTER_HEADERS`, `_NON_CHAPTER_HEADERS`, `_NON_CHAPTER_PREFIX`, `_is_non_chapter_section` (`_PART_HEADER`는 C-17) | ToC 머리말 정규식과 "장 아님" 판정(전체 일치 단어 목록, appendix 접두사, Part) | R-15, R-18, R-20 |
| C-07 | `book_to_skill/utils.py:548-595` `_ATX_HEADING`, `_SETEXT_UNDERLINE`, `_CODE_FENCE`, `_closed_fence_line_numbers` | 제목·밑줄·펜스 정규식과 "닫힌 펜스만" 제외하는 CommonMark식 열고 닫기 규칙 | R-02, R-14 |
| C-08 | `book_to_skill/utils.py:598-629` `_MIN_NUMBERED_TITLES`, `_MIN_NUMBERED_BODY_CHARS`, `_numbered_titles_are_structural` | 숫자로 시작하는 제목을 장으로 받는 기준(3개, 중앙값 200자) | R-16 |
| C-09 | `book_to_skill/utils.py:632-725` `_structural_chapter_headings`, `_structural_chapter_count` | structural 스캔 전체 알고리즘(후보 수집, 깊이 선택, 폴백) | R-14~R-17 |
| C-10 | `book_to_skill/utils.py:728-771` `_cn_numeral_to_int`, `_int_to_roman`, `_roman_to_int` | 중국어 숫자 합성(1~999)과 로마 숫자 변환·정규형 검사(≤200) | R-11, R-12 |
| C-11 | `book_to_skill/utils.py:774-947` `_is_prose_period_tail`, `_match_chapter_number`, `_chapter_number` | 마침표 꼬리 문맥 판정, 분기 순서(plain → 라틴 → 로마 → 중국어 → 태국 → 힌디 → 벵골 → 오리야 → 타밀 → 싱할라 → 텔루구 → 칸나다 → 말라얄람 → 구자라트 → 펀자브 → 러시아 → 그리스 → 히브리 → 아르메니아 → 한국 → 페르시아), 80자 제한, 접두사 제거 2차 판정 | R-08~R-13 |
| C-12 | `book_to_skill/utils.py:950-1026` `_line_title_text`, `_TOC_LEADER`, `_PAGE_CHAPTER_HEADER`, `_CHAPTER_MARKER`, `_OUTLINE_CHAPTER_PREFIX`, `_outline_bare_title`, `_normalized_heading`, `_is_disqualified_chapter_line`, `_chapter_start_at`, `_line_matches_outline_title`, `_find_outline_chapter_start` | outline 제목이 시작하는 줄을 찾는 규칙 | R-22, R-23 |
| C-13 | `book_to_skill/utils.py:1028-1063` `_is_isolated_heading_line`, `_is_chapter_content_boundary`, `_first_chapter_boundary`, `_range_end_title_keys` | 장 끝 경계 판정 | R-24 |
| C-14 | `book_to_skill/utils.py:1066-1103` `chapter_line_ranges` | 시작 탐색 루프, 경고, 범위 조립(`end_line = 경계 줄의 0-기준 인덱스`) | R-22, R-24 |
| C-15 | `book_to_skill/utils.py:1106-1195` `detect_structure` | numeric 스캔, `numeric`/`structural`/`none` 판정, Part 분리·폴백, `has_toc` | R-03~R-07, R-18 |
| C-16 | `book_to_skill/utils.py:1198-1219` `apply_pdf_outline` | outline 채택 조건과 추가 필드 | R-20 |
| C-17 | `book_to_skill/parsers/pdf.py:12` `_PART_HEADER`; `book_to_skill/parsers/pdf.py:187-242` `pdf_outline_titles`, `pdf_outline_all_titles` | `Part N` 정규식, outline 읽기·Part 펼침·평탄화 | R-04, R-15, R-19, R-21 |
| C-18 | `book_to_skill/utils.py:1615-1635` `extract_single_file`(정화 뒤); `book_to_skill/pdf_inspector_integration.py:140-146` `_result_from_inspector` | 호출 순서(정화 → `detect_structure` → PDF면 `apply_pdf_outline`)와 요약 출력 | R-01 |
| C-19 | `book_to_skill/utils.py:1877-1897`, `book_to_skill/utils.py:1971-1981` `main` | `chapter_line_ranges` 호출 위치와 인자(소유는 [S1](./extract-artifacts.md) R-06) | R-22 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(정적 읽기, 실행하지 않음). 사례 이름만 비슷한 원본 테스트(`tests/test_chapter_numeric_false_positives.py`, `test_numbered_headings.py`, `test_pdf_outline_chapters.py`, `test_chapter_content_split.py`, `test_structural_framing_sections.py`, `test_part_chapter_count.py`)가 있음을 파일·사례명으로만 확인했고 본문은 `test_chapter_content_split.py`의 일부만 읽었다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03, R-05 | 본문에 "Chapter 1"(ToC와 본문에 한 번씩), "Chapter 2", "Chapter 3" 줄이 있음 | `numeric`, `chapters_detected == 3`(중복 번호는 1개), 샘플에는 ToC·본문 줄이 순서대로 중복 포함 |
| T-02 | R-09, R-10 | "as we cover in" 다음 줄에 "Chapter 6. Closures create types that many other words will always follow" 한 줄, 다른 장 제목 없음 | 마침표 꼬리 단어 > 8이고 윗줄이 문장을 끝내지 않았으므로 후보 아님. `none`, 0 |
| T-03 | R-02, R-08 | 닫힌 ```` ``` ```` 펜스 안에 "1  + use std::io;" 와 "12  - use x;" | 어느 줄도 장이 아님. 펜스를 지우면 두 줄 모두 `+`/`-` 마커 때문에 plain 분기에서 거부됨 |
| T-04 | R-06, R-14, R-15, R-17 | `# Book` / `## Preface` / `## Setup` / `## Usage` / `## Index`, 숫자 장 없음 | `structural`, `chapters_detected == 2`(Preface·Index 제외, 깊이 1은 1개뿐이라 깊이 2 선택), 샘플 `["## Setup", "## Usage"]` |
| T-05 | R-16 | `## 1. Step` / `## 2. Step` / `## 3. Step`, 각 본문이 20자 | 중앙값 < 200이라 장 아님. `none`, 0. 각 본문을 500자로 바꾸면 `structural`, 3 |
| T-06 | R-07 | 숫자 장·Markdown 제목 없이 "Part 1", "Part 2" 줄만 있음 | `numeric`, 2, 샘플은 Part 줄. 같은 텍스트에 "Chapter 1" 줄이 하나 더 있으면 numeric 1개라 `numeric`, 1(Part 무시) |
| T-07 | R-19, R-20 | PDF 북마크: Preface / Chapter 1 / Chapter 2 / Chapter 3 / Index | 걸러진 제목 3개 → `outline`, 3, `chapter_titles`는 장 3개, `chapter_range_end_titles == ["Preface", "Index"]` |
| T-08 | R-20 | 북마크가 장 1개(+ Index)뿐이거나 `pypdf`가 없음 | `apply_pdf_outline`이 입력 `structure`를 그대로 돌려줌(`numeric`/`structural`/`none` 유지) |
| T-09 | R-19 | 북마크: "Part I" 아래 자식 "Chapter 1", "Chapter 2" | 제목 목록은 `["Chapter 1", "Chapter 2"]`(Part 제외) |
| T-10 | R-22, R-23 | `chapter_line_ranges("CHAPTER 1\nIntroduction and Overview\nbody", ["Chapter 1. Introduction and Overview"])` | `[{"title": ..., "start_line": 1, "end_line": 3}]`. 텍스트 맨 앞에 `1. Introduction and Overview. . . . . 7` 같은 안내선 줄이나 `806 | Chapter 1: …` 쪽 머리말 줄이 있어도 시작으로 잡히지 않음 |
| T-11 | R-22, R-26 | 두 번째 북마크 제목 "Chapter 2. Missing"이 본문에 없음 | stderr에 경고 한 줄, `chapter_ranges`에 첫 장만 있음. `chapters_detected`와 `chapter_titles`는 그대로 2 |
| T-12 | R-24 | 장 본문 중간에 단독 줄 "Part I Conclusion"(끝 경계 제목) 뒤에 "tail" | 그 장의 `end_line`은 "Part I Conclusion" 줄 바로 앞 줄. 본문 문장 속의 "index"라는 단어(줄 전체가 아님)는 경계가 아니다 |
| T-13 | R-18 | 앞 30,000자 안에 단독 줄 "Table of Contents" 또는 "## 目录" | `has_toc == True`. 30,001자 이후에만 있으면 False |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-18; `utils.py:1629-1635` | 두 호출 지점이 같은 순서임을 확인 |
| R-02 | C-07 `_closed_fence_line_numbers`; C-15 `utils.py:1122-1147`; C-09 `utils.py:648-702` | 코드 읽기 |
| R-03 | C-15 `utils.py:1125-1147`, `utils.py:1148` | `headings`는 리스트, `numbers`는 집합 |
| R-04 | C-15 `utils.py:1140-1144`; C-17 `_PART_HEADER` | 코드 읽기 |
| R-05~R-07 | C-15 `utils.py:1148-1185` | 판정 분기를 줄 단위로 따라감 |
| R-08 | C-11 `utils.py:805-823` | 코드 읽기 |
| R-09 | C-01 `utils.py:117-125`; C-11 `utils.py:825-831` | 주석은 대문자 시작 제목(À-Þ)을 인정한다고 쓰지만 실제 `_HEADING_TAIL`은 `(?![a-z])`로 ASCII 소문자만 거부한다. 구현을 사실로 썼다 |
| R-10 | C-01 `utils.py:126-141`; C-11 `utils.py:774-788`, `utils.py:827-828`, `utils.py:939-946` | 주석(이슈 #237)과 코드가 같은 규칙. 8단어 상수 `_TITLE_TAIL_MAX_WORDS` |
| R-11 | C-01 `utils.py:149-151`; C-10 `utils.py:746-771`; C-11 `utils.py:833-835` | 코드 읽기 |
| R-12 | C-02~C-05, C-11 `utils.py:837-895` | 라벨 단어 목록·숫자 변환은 표를 가져가면 되는 영역이라 언어별 세부는 읽지 않았다(분기 순서와 "숫자 필수" 방어만 확인) |
| R-13 | C-11 `utils.py:900-947`, C-01 `_MD_HEADING_PREFIX` | 코드 읽기 |
| R-14 | C-07 `utils.py:552-555`; C-09 `utils.py:660-701` | 코드 읽기. 밑줄 줄 번호가 제목 줄 번호 집합에 들어가는 점은 R-16의 본문 길이 계산에 영향(제목 줄 자체가 윗 구역 본문에 포함됨) |
| R-15 | C-06 `utils.py:508-545`; C-09 `utils.py:682-698` | 코드 읽기 |
| R-16 | C-08 `utils.py:606-629`; C-09 `utils.py:695-706` | 코드 읽기. 수치 근거(측정 중앙값)는 주석 인용이고 직접 측정하지 않았다 |
| R-17 | C-09 `utils.py:708-720` | 코드 읽기 |
| R-18 | C-06 `utils.py:486-502`; C-15 `utils.py:1187-1188` | 코드 읽기 |
| R-19 | C-17 `parsers/pdf.py:187-210` | 코드 읽기. `pypdf` 동작은 확인 한계 |
| R-20 | C-16 `utils.py:1207-1219`; 소스 dict 합류 `utils.py:1643-1659`; 메타데이터 필드 구성 `utils.py:1879-1897`, `utils.py:1949-1983` | `chapter_range_end_titles`가 `sources[]` 구성에 나열되지 않음을 확인 |
| R-21 | C-17 `parsers/pdf.py:213-242` | 코드 읽기 |
| R-22 | C-14, C-19 | 호출이 `1893`(단일 소스 최상위)과 `1974`(소스별) 두 곳임을 확인 |
| R-23 | C-12 `utils.py:988-1016` | 코드 읽기. 원본 테스트 `test_chapter_content_split.py:55-70`(안내선·쪽 머리말·`CHAPTER 1`)로 의도 확인 |
| R-24 | C-13, C-14 `utils.py:1090-1103` | 코드 읽기. `test_chapter_content_split.py:42-52`, `:72-89`로 `end_line` 의미와 "단어 index는 경계 아님"을 확인(테스트는 의도 확인용) |
| R-25 | C-15, C-09 `utils.py:716-720`; 경고 조건 `utils.py:2014-2025` | 경고 코드는 S1 R-09 |
| R-26 | C-12, C-14 | ToC 줄 오인은 코드에 해당 검사가 없다는 데서 짐작한 추론 |
| R-27 | `utils.py:1073`, `:648`, `:1122` `splitlines`; 정화가 U+2028 등을 지우지 않는 것은 `sanitize.py` 상수 표에서 해당 코드 포인트를 찾지 못한 것(전체 표를 읽지는 않음) | 코드 확인(호출 지점), 추론(어긋남) |
| T-01~T-13 | 위 R-ID의 C-ID | 구현에서 도출, 실행하지 않음 |

### 2.2 코드 읽는 순서
`utils.py` `detect_structure`(1106) → `_chapter_number`(900) → `_match_chapter_number`(791) → `_EXPLICIT_CHAPTER`와 꼬리 정규식(111~156) → `_structural_chapter_headings`(632) → `_numbered_titles_are_structural`(610) → `apply_pdf_outline`(1198) → `pdf.py` `pdf_outline_titles`(187) → `chapter_line_ranges`(1066) → `_line_matches_outline_title`(988) → `_is_chapter_content_boundary`(1036). 언어별 표(C-02~C-05)는 필요할 때 찾아본다.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-22, R-27 | `chapter_ranges`를 쓰는 쪽(행 9의 sed·grep)이 `\n` 기준으로 줄을 센다면, 구현에서 줄 나누기를 `\n`으로 통일하거나 정화 단계에서 `\f`·U+2028 등을 `\n`으로 바꾸는 것을 검토 | 줄 번호 소비자와 생성자의 기준을 같게 하려고 | 변경은 아직 결정하지 않음. 소비 쪽 스펙(행 9)에서 줄 번호 해석을 확인한 뒤 정한다 |
| R-22 | 못 찾은 제목을 건너뛰면서도 `chapters_detected`는 그대로 두는 것을 구현할 때 경고에 개수를 같이 내거나 `chapter_titles`와 `chapter_ranges` 길이 차이를 호출자에게 알리는 방안 | 에이전트가 장 수와 범위 수가 다름을 알아채기 어렵다 | 새 필드·경고 문구는 원본에 없음 |
