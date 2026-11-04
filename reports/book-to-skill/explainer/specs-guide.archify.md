# book-to-skill은 PDF 한 권을 어떤 순서로 AI용 스킬로 바꾸나? {#book-to-skill-specs}

두 단계로 바꿉니다. 먼저 파이썬 프로그램이 PDF를 텍스트 파일 하나(`full_text.txt`)와 크기·장 정보 파일 하나(`metadata.json`)로 만들고, 그다음 AI 에이전트가 `SKILL.md`의 지시대로 이 두 파일에서 장별 요약 스킬을 씁니다. 분석한 8개 스펙 중 6개가 앞 단계, 2개가 뒤 단계입니다.

- 두 단계를 잇는 것은 `full_text.txt`와 `metadata.json` 두 파일뿐입니다. 에이전트는 PDF 원본이 아니라 이 파일을 읽습니다.[](source:skillmd)
- PDF에서 글자를 뽑는 엔진은 다섯 개이고, 파일 상태와 모드(`text`/`technical`)를 보고 하나가 골라집니다.[](source:pdfparser)
- 머리말·쪽번호 정리는 엔진 세 개의 결과에만 걸립니다. 같은 책도 어느 엔진이 뽑았는지에 따라 `full_text.txt`가 달라집니다.
- 요약은 장 하나당 파일 하나로 쓰고, 질문이 오면 에이전트는 장 파일 하나만 읽습니다.[](source:skillmd)

@answer scope="커밋 e7bb659 · 정적 코드 읽기 기준 · PDF를 실제로 실행해 보지 않음"
@meta locale=ko
@source repo title="book-to-skill 저장소 (커밋 e7bb659)" url=https://github.com/virgiliojr94/book-to-skill/tree/e7bb659d3261491c8b28793dcb9102fa64a46c22
@source skillmd title="SKILL.md: 에이전트가 따르는 생성 지시" url=https://github.com/virgiliojr94/book-to-skill/blob/e7bb659d3261491c8b28793dcb9102fa64a46c22/SKILL.md
@source pdfparser title="parsers/pdf.py: PDF 엔진과 쪽 정리" url=https://github.com/virgiliojr94/book-to-skill/blob/e7bb659d3261491c8b28793dcb9102fa64a46c22/book_to_skill/parsers/pdf.py
@source utils title="utils.py: 실행기, 정화, 구조 감지" url=https://github.com/virgiliojr94/book-to-skill/blob/e7bb659d3261491c8b28793dcb9102fa64a46c22/book_to_skill/utils.py
@source inspector title="pdf_inspector_integration.py: 빠른 길 판정" url=https://github.com/virgiliojr94/book-to-skill/blob/e7bb659d3261491c8b28793dcb9102fa64a46c22/book_to_skill/pdf_inspector_integration.py
@source sanitize title="sanitize.py: 보이지 않는 문자 목록" url=https://github.com/virgiliojr94/book-to-skill/blob/e7bb659d3261491c8b28793dcb9102fa64a46c22/book_to_skill/sanitize.py

## 8개 기능은 어떤 순서로 이어지나? {#flow}

PDF를 넣은 뒤 일어나는 일을 순서대로 놓은 그림입니다. 위 줄은 파이썬 코드가 하는 일이고, 아래 줄은 에이전트가 지시문을 읽고 하는 일입니다. 점선은 엔진에 따라 쪽 정리를 건너뛰는 길입니다.

@workflow id=overall-flow title="PDF 입력부터 질문 답변까지"
| lane py | 파이썬 추출기 (코드) |
| lane ai | 에이전트 (SKILL.md 지시) |
| inp | 입력 풀기 | external | py |
| eng | 엔진 선택 | backend | py |
| cln | 쪽 정리 | backend | py |
| san | 문자 정화 | backend | py |
| str | 장 구조 감지 | backend | py |
| out | 두 파일 쓰기 | database | py |
| ask | 비용·유형 확인 | frontend | ai |
| wr | 장 요약 쓰기 | backend | ai |
| mst | 마스터 SKILL.md | backend | ai |
| qa | 질문 시 장 하나 | external | ai |
| inp > eng | |
| eng > cln | 엔진 3개 |
| eng > san | 정리 생략 | dashed |
| cln > san | |
| san > str | |
| str > out | |
| out > ask | 두 파일 |
| ask > wr | |
| wr > mst | |
| mst > qa | |

@steps id=flow-steps
| s-inp | 입력 풀기 | 경로·폴더·glob을 지원 파일 목록으로 풀고, 확장자가 없으면 앞 바이트로 PDF·EPUB·DOCX를 가립니다. 스펙: `input-and-env` | overall-flow | inp |
| s-eng | 엔진 선택 | PDF에서 글자를 뽑을 엔진을 고르고 실패하면 다음 엔진으로 넘어갑니다. 스펙: `pdf-extraction` | overall-flow | eng |
| s-cln | 쪽 정리 | 머리말·꼬리말·쪽번호를 지우고 줄 끝 하이픈을 잇습니다. 엔진 세 개의 결과에만 적용됩니다. 스펙: `pdf-text-cleanup` | overall-flow | cln |
| s-san | 문자 정화 | 보이지 않는 문자를 지우고 Kangxi 부수를 한자로 접습니다. 모든 형식에 적용됩니다. 스펙: `text-sanitize` | overall-flow | san |
| s-str | 장 구조 감지 | 장 수와 장 제목을 찾고, PDF 북마크가 쓸 만하면 장별 줄 범위를 계산합니다. 스펙: `structure-detection` | overall-flow | str |
| s-out | 두 파일 쓰기 | `full_text.txt`와 `metadata.json`을 작업 디렉터리에 씁니다. 스펙: `extract-artifacts` | overall-flow | out |
| s-ask | 비용·유형 확인 | 토큰 추정을 보여 주고 확인받은 뒤 책 유형과 목적을 묻고 스킬 이름·위치를 정합니다. 스펙: `generation-setup` | overall-flow | ask |
| s-wr | 장 요약 쓰기 | 장마다 파일 하나, 그리고 용어집·패턴집·치트시트를 씁니다. 스펙: `skill-authoring` | overall-flow | wr |
| s-mst | 마스터 SKILL.md | 장 색인과 주제 색인이 있는 4,000토큰 미만의 입구 파일을 씁니다. 스펙: `skill-authoring` | overall-flow | mst |
| s-qa | 질문 시 장 하나 | 질문이 오면 색인으로 장 번호를 찾아 장 파일 하나만 읽고 답합니다. 스펙: `skill-authoring` | overall-flow | qa |

## 입력을 넣을 때 조용히 사라지는 것이 있나? {#input-gotchas}

입력을 풀어 주는 코드(`input-and-env`)는 오류를 내지 않고 넘어가는 경우가 몇 개 있습니다. 결과가 기대와 다를 때 가장 먼저 볼 곳입니다.[](source:utils)

| 상황 | 일어나는 일 | 이유 |
| --- | --- | --- |
| `--install-missing book.pdf` | `book.pdf`가 입력이 아니라 설치 모드 값으로 읽혀 입력 목록에서 빠집니다 {caution:입력 소실} | `--install-missing`은 다음 토큰이 `--`로 시작하지 않으면 값으로 가져갑니다 |
| 폴더·glob 안에 확장자가 없는 PDF | 경고 없이 빠집니다 {caution:조용히 제외} | 폴더·glob 확장은 지원 확장자만 모읍니다. 파일을 직접 지정해야 앞 8바이트(`%PDF`, `PK`)로 형식을 가립니다 |
| `--mode`에 `technical`·`text`가 아닌 값 | `text`로 바뀌고 경고가 없습니다 | 이후 모든 단계는 두 값만 다룹니다 |
| 일치하는 파일이 없는 glob | 아무것도 더하지 않습니다. 입력이 0개면 종료 코드 1 | 이 glob에 대한 경고는 따로 없습니다 |
| 작업 디렉터리가 심볼릭링크이거나 다른 사용자 소유 | 안전 점검에서 막혀 트레이스백으로 끝납니다 | 이 점검은 소스 루프 밖에서 일어나 오류가 잡히지 않습니다 |

## PDF 글자는 어느 엔진이 뽑나? {#engine}

PDF에는 글자 정보가 들어 있는 파일도 있고 쪽마다 이미지뿐인 스캔본도 있습니다. 그래서 book-to-skill은 파일 상태와 사용자가 고른 모드를 보고 엔진을 정합니다.[](source:pdfparser)

@workflow id=engine-flow title="PDF 엔진 선택과 폴백"
| pdf | PDF 입력 | external |
| fast | 빠른 길 가능? | backend |
| insp | pdf-inspector 결과 | backend |
| scan | 스캔본인가? | backend |
| stop | 중단 | security |
| tech | technical 모드? | backend |
| doc | Docling | backend |
| chain | 텍스트 엔진 체인 | backend |
| pdf > fast | |
| fast > insp | 예 | emphasis |
| fast > scan | 아니오 |
| scan > stop | 예 |
| scan > tech | 아니오 |
| tech > doc | 예 |
| tech > chain | 아니오 |
| doc > chain | 실패·빈 결과 | dashed |

@steps id=engine-steps
| e-fast | 빠른 길 가능? | `text` 모드에서만 봅니다. pdf-inspector가 설치돼 있고, 판정이 `text_based`, 신뢰도 0.90 이상, OCR이 필요한 쪽 없음, 인코딩 문제 없음이어야 합니다. 정화 뒤 내용이 비면 이 길을 버리고 아래로 내려갑니다. | engine-flow | fast |
| e-scan | 스캔본인가? | 앞 5쪽을 `pdftotext`로 읽어 글자가 나오지 않으면 스캔본으로 보고 그 소스를 중단합니다. `pdftotext`가 PATH에 없으면 이 검사는 동작하지 않습니다. | engine-flow | scan |
| e-tech | technical 모드? | 사용자가 책에 코드·표·수식이 많다고 답하면 `technical`이고, Docling을 먼저 시도합니다. | engine-flow | tech |
| e-doc | Docling | OCR 없이(`do_ocr=False`) 구조를 살려 뽑습니다. 없거나 실패하거나 결과가 비면 `fallback_reason`에 `docling_unavailable`, `docling_failed`, `docling_empty` 중 하나를 남기고 체인으로 갑니다. | engine-flow | doc |
| e-chain | 텍스트 엔진 체인 | `pdftotext`, `pypdf`, `pdfminer` 순서로 시도해 비어 있지 않은 텍스트를 처음 내는 엔진을 씁니다. 셋 다 비면 오류입니다. | engine-flow | chain |

@callout level=note title="어느 엔진이 썼는지 확인하는 방법"
| `metadata.json`의 `extraction_method`에 실제로 쓴 엔진이, `fallback_reason`에 돌아간 이유가 남습니다.
| `technical`로 골랐는데 `extraction_method`가 `pdftotext`라면 Docling이 쓰이지 않은 것입니다. `fallback_reason`을 보세요.

## 쪽 정리와 정화는 무엇을 지우나? {#cleanup}

엔진이 낸 글자는 바로 쓰이지 않고 두 번 손질됩니다. 쪽 정리(`pdf-text-cleanup`)는 PDF 엔진 세 개의 결과에만 걸리고, 정화(`text-sanitize`)는 모든 경로에 걸립니다.

| 경로 | 쪽 정리 | 정화 | 구조 감지 |
| --- | --- | --- | --- |
| `pdf-inspector` | 안 함 | 함 | 함 |
| `docling` | 안 함 {caution:머리말 제거 없음} | 함 | 함 |
| `pdftotext`·`pypdf`·`pdfminer` | 함 {good:적용} | 함 | 함 |
| PDF 아닌 형식 | 안 함 | 함 | 함 |

쪽 정리는 쪽이 3개 이상일 때만 머리말과 쪽번호를 지웁니다. 쪽이 2개 이하이면 하이픈만 잇습니다.

| 대상 | 지우는 조건 | 남기는 경우 |
| --- | --- | --- |
| 머리말·꼬리말 | 쪽의 첫 줄이나 마지막 줄에 같은 문자열이 쪽 수의 절반을 넘는 쪽에서 나옴 | 쪽 중간의 같은 문자열은 남깁니다. 본문의 절 제목이 지워지지 않습니다 |
| 쪽번호 | 쪽의 첫·마지막 줄이 1~4자리 숫자 하나, 또는 로마 숫자 1~99 | 5자리 이상 숫자와 `MIX`처럼 로마 숫자 꼴이 아닌 철자는 남깁니다 |
| 줄 끝 하이픈 | `informa-` 다음 줄이 `tion`처럼 글자로 이어짐 | `well-` 다음 줄 `known`도 `wellknown`으로 붙습니다. 소스 주석이 알려진 한계로 적었습니다 |

10쪽짜리 PDF에서 같은 머리말이 6쪽의 첫 줄에 있으면 6표가 절반 5를 넘어 지웁니다. 5쪽에만 있으면 5표로 넘지 못해 남습니다.[](source:pdfparser)

정화는 문서 안에 눈에 안 보이는 글자로 숨긴 지시문(프롬프트 주입)을 막으려고 있습니다.[](source:sanitize)

| 처리 | 대상 | 비고 |
| --- | --- | --- |
| 지움 | 제로폭 문자, 방향 제어, 한글 필러, 태그 블록, 변이 선택자 | 지운 글자가 있으면 stderr에 한 줄을 남깁니다 |
| 접음 | 깨진 PDF 글꼴이 만드는 Kangxi 부수(U+2F00–2FDF)를 대응 한자로 | 전체 텍스트에 NFKC를 걸지 않아 전각·합자는 그대로입니다 |
| 남김 | 점자 공백(U+2800), 눈에 보이는 몽골·크메르 문자 | 지우면 낱말이 붙기 때문입니다 |
| 거부 | 정화 뒤 `strip()`이 비는 소스 | 일반 경로는 그 소스만 건너뛰고, pdf-inspector 경로는 기존 추출로 되돌아갑니다 |

@callout level=warning title="정화가 막지 못하는 것"
| 정화는 보이지 않는 문자만 지웁니다. 눈에 보이는 글자로 쓴 지시문은 그대로 남습니다.
| 주석 앵커 사이에 숨은 글자가 있으면 제어 문자만 지워지고 글자는 평문으로 남습니다.

## 장은 어떻게 찾고, `chapter_ranges`는 무엇인가? {#structure}

장 정보가 있어야 에이전트가 책 전체가 아니라 장 하나만 읽을 수 있습니다. 그래서 정화가 끝난 텍스트에서 장을 찾고, PDF 북마크가 쓸 만하면 장마다 줄 번호 범위까지 계산합니다.

@workflow id=structure-flow title="장 구조 감지 순서"
| txt | 정화된 텍스트 | external |
| num | 장 번호 2개 이상? | backend |
| m1 | numeric | backend |
| st | 제목 줄이 더 많나? | backend |
| m2 | structural | backend |
| m3 | numeric 또는 none | backend |
| pdf | 북마크 장 2개 이상? | backend |
| m4 | outline | backend |
| rng | 장별 줄 범위 | database |
| txt > num | |
| num > m1 | 예 | emphasis |
| num > st | 아니오 |
| st > m2 | 예 |
| st > m3 | 아니오 |
| m1 > pdf | PDF만 |
| m2 > pdf | |
| m3 > pdf | |
| pdf > m4 | 예 | emphasis |
| m4 > rng | |

@steps id=structure-steps
| t-num | 장 번호 2개 이상? | `Chapter 5`, `第三章`, `제5장`, `1  Intro`(숫자 뒤 공백 둘 이상) 같은 줄에서 서로 다른 번호를 셉니다. 코드 펜스 안은 건너뜁니다. 2개 이상이면 `numeric`으로 끝냅니다. | structure-flow | num |
| t-st | 제목 줄이 더 많나? | `#` 제목, AsciiDoc `=` 제목, RST 밑줄 제목을 셉니다. numeric보다 많으면 `structural`입니다. 같은 수이면 `numeric`이 이기고, 둘 다 0이면 `none`입니다. | structure-flow | st |
| t-pdf | 북마크 장 2개 이상? | 북마크에서 표지·머리말·목차·부록·Part를 거른 제목이 2개 이상이면 위 결과를 `outline`으로 덮어씁니다. 모자라면 위 결과를 그대로 둡니다. | structure-flow | pdf |
| t-rng | 장별 줄 범위 | 북마크 제목마다 본문에서 처음 맞는 줄을 찾고, 다음 장 시작 직전까지를 그 장의 범위로 정합니다. 못 찾은 제목은 경고 후 건너뛰므로 `chapter_ranges`가 `chapter_titles`보다 짧을 수 있습니다. | structure-flow | rng |

@callout level=warning title="북마크가 없는 PDF는 장 범위가 없습니다"
| `chapter_ranges`는 소스가 하나이고 `chapters_method`가 `outline`일 때만 `metadata.json` 최상위에 생깁니다.
| 북마크가 없으면 에이전트가 장 제목을 `grep`으로 찾아 구간을 읽어야 합니다. 장 제목이 번호 라벨도 Markdown 제목도 아닌 PDF는 `none`, 장 0개로 나옵니다.

## 두 파일에는 무엇이 들어 있나? {#artifacts}

앞 단계와 뒤 단계를 잇는 것은 작업 디렉터리의 두 파일입니다. 에이전트는 이 파일만 보고 생성을 진행하므로, 여기에 무엇이 적히는지가 두 단계의 약속입니다.

@facts id=artifact-facts
| `full_text.txt` | 정화된 텍스트를 소스마다 `SOURCE: <파일명> (Path: …)` 배너와 함께 이어 쓴 파일입니다. 소스가 하나여도 배너가 붙습니다. |
| `metadata.json` | 쪽 수, 글자·단어 수, `estimated_tokens`, 소스별 `extraction_method`·`fallback_reason`, 장 수·방법·제목을 담습니다. |
| `pdf_pages.json` | `--pdf-page-sidecar`를 줄 때만 쓰는 쪽 단위 근거 파일입니다. 이 분석 범위 밖입니다. |
| 위치 | `BOOK_SKILL_WORKDIR`가 있으면 그 경로, 없으면 `<임시폴더>/book_skill_work-<PID>`입니다. 권한은 0700입니다. |
| 토큰 추정 | CJK가 없으면 단어 수 ÷ 0.75입니다. 90,000단어면 120,000토큰입니다. |
| 실패 처리 | 소스 하나가 실패하면 그 소스만 건너뜁니다. 전부 실패하면 두 파일을 쓰지 않고 종료 코드 1입니다. |

## 생성 전에 무엇을 묻고 얼마를 보여 주나? {#setup}

여기부터는 파이썬 코드가 아니라 에이전트가 읽는 `SKILL.md` 지시입니다. 그래서 규칙은 "에이전트에게 이렇게 하라고 적혀 있다"는 뜻입니다.[](source:skillmd)

| 시점 | 질문 | 답과 결과 |
| --- | --- | --- |
| 추출 전 | 어떤 내용의 책인가 | 1번 코드·표·수식 중심이면 `technical`, 2번 일반 글이면 `text`, 3번 모름이면 `text`. 이 값이 `--mode`로 넘어갑니다 |
| 추출 후 | 이 비용으로 진행할까 | 토큰·시간 추정을 보여 주고 답을 받기 전에는 생성하지 않습니다. `analyze only`라고 답하면 분석 보고서만 내고 끝납니다 |
| 생성 직전 | 책을 어디에 쓰려는가 | 3번 특정 장·개념 참조만 고르면 `reference`, 1·2·4번 중 하나라도 있으면 `study` |
| 저장 전 | 이름과 위치 | 이름 후보 두 개(`author-concept`, 책 제목)를 제안합니다. 같은 이름이 이미 있으면 Update·Overwrite·Rename을 묻습니다 |

비용 추정은 입력 토큰 = `estimated_tokens` × 1.3, 출력 토큰 = 장 수 × 장당 중간값 + 4,000 + 4,500입니다. 장당 중간값은 `text`가 약 1,000, `technical`이 약 1,800입니다. 예를 들어 `text` 책이 120,000토큰에 20장이면 입력은 120,000 × 1.3 = 156,000토큰, 출력은 20 × 1,000 + 4,000 + 4,500 = 28,500토큰입니다.

책이 약 50k 토큰을 넘으면 에이전트는 `full_text.txt`를 통째로 읽지 않고 `wc`, `grep`, `sed`로 필요한 구간만 읽습니다.

## 스킬 폴더에는 무엇이 생기고, 질문은 어떻게 읽히나? {#authoring}

만들어진 스킬이 책 전체를 매번 읽으면 AI에게 빠르게 설명을 맡기려는 목적이 무너집니다. 그래서 장마다 파일을 나누고 마스터 `SKILL.md`에 색인을 둡니다.

@tree id=skill-folder title="생성되는 스킬 폴더"
| root | 스킬 폴더 | - |
| master | SKILL.md | root |
| chapters | chapters | root |
| ch | ch01-제목.md ··· | chapters |
| glossary | glossary.md | root |
| patterns | patterns.md | root |
| cheat | cheatsheet.md | root |

장 파일 하나의 목표 분량은 책 유형과 목적이 정합니다. 목표이지 상한은 아닙니다.

| 장당 토큰 | `reference` | `study` |
| --- | --- | --- |
| `text` | 800–1,200 | 1,000–1,800 |
| `technical` | 1,200–1,800 | 2,000–3,000 |

마스터 `SKILL.md`는 4,000토큰 미만이고, 앞쪽 약 2,000토큰에 핵심 프레임워크를 둡니다. 질문이 오면 에이전트는 먼저 그 핵심을 보고, 거기 없는 주제면 주제 색인에서 장 번호를 찾아 `chapters/` 파일 하나만 읽습니다. 200쪽 책이 약 75k 토큰이므로, 장 하나(약 1,000~3,000토큰)만 읽으면 매 질문의 부담이 크게 줄어듭니다.

## 아직 확인하지 못한 것은 무엇이고, 어떻게 확인하나? {#open}

이 페이지의 규칙은 모두 코드를 읽어 얻은 것입니다. 실행은 한 번도 하지 않았습니다.

@callout level=open-question title="남은 미확인 3개"
| 마스터 `SKILL.md`에는 `full_text.txt` 경로를 적게 돼 있는데, 생성 마지막 단계는 작업 디렉터리를 지웁니다. 삭제 뒤에는 그 파일이 없습니다. 의도인지 모순인지 가리지 못했습니다.
| `chapter_ranges`는 `splitlines()` 기준 줄 번호입니다. `\f`나 U+2028이 텍스트에 남아 있으면 `sed`로 읽을 때 줄 번호가 어긋날 수 있습니다(추론).
| 사전 분석만 하는 Mode 3은 어느 기능 행도 맡고 있지 않습니다.

직접 확인하려면 PDF 한 권으로 아래를 해 보세요.

- [ ] `--mode text`로 텍스트 PDF를 돌린 뒤 `metadata.json`의 `extraction_method`가 `pdf-inspector`인지 본다.
- [ ] 같은 PDF를 `--mode technical`로 돌려 `extraction_method`가 `docling`인지, 아니면 `fallback_reason`이 무엇인지 본다.
- [ ] 쪽이 3개 이상인 PDF에서 `full_text.txt`에 머리말과 쪽번호가 남았는지 `grep`으로 본다. 엔진이 `pdftotext`·`pypdf`·`pdfminer`일 때만 정리됩니다.
- [ ] 북마크가 있는 PDF에서 `chapter_ranges`의 `start_line`로 `sed -n`을 해 그 줄이 장 제목인지 본다.
- [ ] 스킬을 만든 뒤 마스터 `SKILL.md`의 `Full text` 경로에 파일이 아직 있는지 본다.
