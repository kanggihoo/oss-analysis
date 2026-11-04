---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - book_to_skill/utils.py
  - book_to_skill/dependencies.py
  - book_to_skill/config.py
  - book_to_skill/cli.py
  - SKILL.md
depends: []
status: ready
---

# 입력·환경 준비

> 명령줄 인자(경로·폴더·glob, 옵션)를 받아 처리할 지원 파일 목록과 실행 설정(`--mode`, 설치 모드)을 정하고, 포맷별 선택 의존성을 점검·설치 제안(또는 `--check` 보고)하며, 추출 전에 작업 디렉터리를 준비한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 시작하면 stderr에 소개 두 줄을 찍는다. 인자에 `-h`/`--help`가 있으면 usage를 찍고 종료 코드 0, `--check`가 있으면 의존성 보고만 하고 종료 코드 0으로 끝난다(파일·작업 디렉터리는 건드리지 않는다).
2. `parse_arguments`가 인자를 (입력 경로 목록, 추출 모드, 설치 모드)로 나눈다.
3. `resolve_input_files`가 경로·폴더·glob을 지원 확장자 파일의 절대 경로 목록으로 풀고 중복을 없앤다. 비면 종료 코드 1.
4. `prepare_output_dir`로 작업 디렉터리를 만든다(규칙은 [extract-artifacts](./extract-artifacts.md) R-01).
5. 파일마다 추출을 시작하는 첫머리에서 (a) 확장자가 지원 목록 밖이면 앞 바이트로 PDF·EPUB·DOCX를 판별하고, (b) 그 포맷의 선택 의존성을 점검해 필요하면 설치를 제안하고, (c) MOBI/AZW는 Calibre 존재를 확인한다. 실제 추출은 이 뒤에 시작한다(다른 스펙).

### 1.2 범위·통합 지점
- 제공: 인자 해석, 입력 해석, 포맷 판별(매직바이트), 의존성 점검·설치 제안·`--check` 보고, 이 단계들의 실패 처리.
- 제외: 실제 추출(PDF는 [pdf-extraction](./pdf-extraction.md), 나머지는 별도 행), 작업 디렉터리 안전 규칙·경로 결정([extract-artifacts](./extract-artifacts.md) R-01, R-02), `--pdf-page-sidecar`가 하는 일(행 6; 여기서는 인자로 받아들이는 것까지만).
- 외부 의존: PATH 상의 `pdftotext`, `ebook-convert`; 파이썬 `importlib`; `pip`(`sys.executable -m pip`); `sys.stdin.isatty()`; 환경변수 `BOOK_SKILL_INSTALL_MISSING`.
- 소유 상태·부작용: 입력 목록·모드는 `main`의 지역값이다. 부작용은 (1) 사용자가 허락했거나 `yes` 모드일 때 `pip install`로 환경이 바뀌는 것, (2) 작업 디렉터리 생성, (3) stdout/stderr 안내문이다. 모듈 상태는 없다.

### 1.3 인터페이스와 데이터 의미

**명령줄 계약** (원문 이름)
| 항목 | 의미 |
|---|---|
| `<경로>...` | `-`로 시작하지 않는 인자 전부. 파일·폴더·glob. 입력 순서가 기본 처리 순서 |
| `--mode technical\|text` | 기본 `text`. 값은 소문자로 바꾼 뒤 둘 중 하나가 아니면 조용히 `text`. 값 없이 마지막에 오면 무시(`text`) |
| `--install-missing [값]` | 다음 토큰이 `--`로 시작하지 않으면 값으로 삼킨다(경로여도). 값 없으면 `yes` |
| `--no-install-missing` | 설치 모드 `no`. `--install-missing`보다 우선 |
| `--pdf-page-sidecar` | `parse_arguments`는 받아들이기만 하고, 효과는 `main`이 `sys.argv`를 직접 보고 낸다 |
| `--check` | 의존성 보고 후 종료(`main`이 파싱보다 먼저 처리) |
| `-h`, `--help` | usage 후 종료 코드 0 |
| 그 외 `-`로 시작하는 인자 | stderr 경고 `Unknown flag`, 무시 |
| `BOOK_SKILL_INSTALL_MISSING` | 설치 모드 기본값. 없으면 `ask` |

**설치 모드** (`normalize_install_mode`의 반환): `yes` / `no` / `ask`. 값 → 모드 대응은 C-03.

**`resolve_input_files(paths) -> list[Path]`**: 절대·정규화된(`resolve()`) 경로. 존재하지 않는 명시 경로도 포함될 수 있다(R-07). 호출자 소유의 새 리스트.

**지원 확장자**: C-01의 `SUPPORTED_EXTENSIONS`(소문자 비교).

**종료 코드**: `--help`·`--check` 0. 인자 없음·입력 경로 없음·지원 파일 없음·전 소스 실패 1.

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `main` 시작 | 순서: 소개(stderr) → `-h/--help`(어느 위치든) 종료 0 → `--check` 종료 `run_dependency_check()` 반환값(항상 0) → 인자 없음(`argv` 길이 < 2)이면 usage·종료 1 → `parse_arguments` → 입력 경로 0개면 stderr `ERROR`·종료 1 → `resolve_input_files` → 결과 0개면 stderr `ERROR`·종료 1 → `prepare_output_dir` → 소스 루프 | 코드 확인 |
| R-02 | `parse_arguments` | `--mode`는 다음 토큰을 무조건 값으로 가져간다(`--`로 시작해도). `--install-missing`은 다음 토큰이 `--`로 시작하지 않을 때만 가져간다. 그래서 `--install-missing book.pdf`는 `book.pdf`를 입력이 아니라 설치 모드 값으로 삼켜 입력 목록에서 사라진다. `-`로 시작하는 나머지는 경고 후 무시, 그 외는 입력 경로 | 코드 확인 |
| R-03 | `--mode` 값이 `technical`·`text` 외(대소문자 무시 후) | `text`로 바뀌고 경고 없음. 따라서 이후 모든 단계와 `metadata.json`의 `extraction_mode`는 두 값뿐이다 | 코드 확인 |
| R-04 | 설치 모드 결정 | 우선순위: `--no-install-missing`(`no`) > `--install-missing`(값 있으면 그 값, 없으면 `yes`) > 환경변수 > `ask`. 값은 C-03 표로 `yes`/`no`/`ask`가 되고, 표에 없으면 `ask`. 결정은 `argv` 문자열 검사라서 R-02에서 입력으로 잘못 삼켜진 토큰도 값으로 쓰인다 | 코드 확인 |
| R-05 | 입력 인자 하나 | `~`를 먼저 전개한다. 그 경로가 **존재하지 않고** `*`, `?`, `[` 중 하나가 있으면 glob(`recursive=True`, `**` 가능): 일치한 것 중 파일이고 확장자(소문자)가 지원 목록인 것만 남기고 `str().lower()` 기준으로 정렬한다. 존재하는 폴더면 `os.walk`로 하위까지 내려가며 지원 확장자 파일을 모아 같은 기준으로 정렬한다(심볼릭 링크 폴더는 따라가지 않음). 그 밖은 명시 파일로 보고 확장자와 상관없이 그대로 넣는다 | 코드 확인 |
| R-06 | 목록 조립 | 인자 순서대로 이어 붙인다(명시 파일은 입력 순서, glob·폴더 확장분은 각자 정렬된 덩어리). 이어서 `resolve()`한 경로 기준으로 첫 등장만 남기는 중복 제거. 확장자 없는 파일이나 지원 밖 확장자 파일은 폴더·glob 확장에서는 조용히 빠진다(매직바이트 판별 대상이 아니다) | 코드 확인 |
| R-07 | 존재하지 않는 비-glob 경로, 또는 일치 0개인 glob | 존재하지 않는 비-glob 경로는 목록에 남고 이후 `File not found`로 그 소스만 건너뛴다(전부 실패하면 종료 1). 일치가 없는 glob은 아무것도 더하지 않고 경고도 없다 | 코드 확인 |
| R-08 | 파일의 확장자가 지원 목록 밖(확장자 없음 포함) | 앞 8바이트를 읽는다. 읽기 실패는 `ExtractionError`. `%PDF`로 시작하면 PDF. `PK`로 시작하면 ZIP을 열어 `mimetype`이 `application/epub`로 시작하면 EPUB, `word/document.xml`이 있으면 DOCX, 아니면 `ExtractionError`(`Unsupported ZIP-based format`). 열기 실패(BadZipFile·OSError 등)도 같은 오류. 그 외는 `ExtractionError`(`Unsupported format`). 판별되면 이후 `format`·분기는 판별된 포맷을 쓴다. **지원 확장자를 가진 파일은 내용을 보지 않는다**(`x.pdf`가 실제로 EPUB이어도 PDF로 처리) | 코드 확인 |
| R-09 | 소스마다, R-08 직후 | `prepare_dependencies(ext, 추출 모드, 설치 모드)`를 부른다. 판별된 확장자·모드에 따라 C-06 표의 항목만 제안 대상이다. 호출은 소스마다 다시 일어나 같은 패키지가 계속 없으면 같은 질문이 소스마다 반복된다. 예외를 던지지 않는다(설치 실패도 폴백 안내로 끝난다). 이 점검의 모드는 사용자가 준 모드이고, 추출 중 일어나는 폴백(예: Docling 실패)과 무관하다 | 코드 확인 |
| R-10 | 제안 대상 모듈이 있음 | 모듈 존재는 `find_spec` 결과로만 판단한다(실제 import 성공까지 확인하지 않음). 모듈이 다 있으면 조용히 끝, `any_of`면 하나라도 있으면 조용히 끝. 아니면 안내문(`<기능> uses … if installed[, otherwise <폴백>].`)을 stdout에 낸다. 설치 여부: `yes`면 설치, `ask`이고 stdin이 TTY면 `y`/`yes`/`install` 입력 시 설치, 그 밖(`no`, 또는 `ask`인데 비대화형)은 설치 안 하고 "비대화형 또는 설치 비활성" 안내 후 `Using fallback: …`. `any_of`일 때 설치하는 것은 **첫 번째 없는 패키지 하나**, 아니면 없는 것 전부 | 코드 확인 |
| R-11 | 설치 시도 | `[sys.executable, -m, pip, install, 패키지…]`, 타임아웃 600초, 출력은 터미널로 직통. 반환 코드 0이고 재점검에서 충족(`any_of`면 하나라도 있음, 아니면 전부 있음)이면 `Package installation complete.`. 아니면 stderr에 미충족/실패를 알리고 폴백 안내를 낸다. 어느 경우도 예외를 올리지 않고 추출은 계속된다 | 코드 확인 |
| R-12 | MOBI/AZW/AZW3(판별된 확장자) | R-09 뒤에 `ebook-convert`가 PATH에 없으면 `ExtractionError`로 그 소스를 건너뛴다(폴백 없음) | 코드 확인 |
| R-13 | `--check` | 그룹 8개(C-08)를 순서대로 모듈·시스템 명령 유무(`✓`/`✗`)와 한 줄 상태(`ready` / `MISSING — required, no fallback`(필수 그룹인 MOBI/AZW만) / `fallback available (install for best quality)`)로 보여 준다. 충족 판정: `any_tool_suffices` 그룹은 모듈 하나 또는 시스템 명령 하나면 충족. 그 밖의 그룹은 모듈 조건(`any_of`는 하나, 아니면 전부; 모듈이 없는 그룹은 충족)을 만족해야 하고, 거기에 시스템 명령이 하나라도 없으면 미충족. 없는 pip 패키지는 중복 제거해 `<파이썬> -m pip install …` 한 줄로, 없는 시스템 도구는 `# <이름>: <설치 안내>` 줄로 낸다. 전부 있으면 `All optional dependencies are installed…`. 반환 코드는 항상 0이다. 없는 모듈과 같은 이름의 실행 파일이 PATH에 있으면(예: pipx로 설치한 docling) 격리 환경 안내 한 줄(`↳`)을 더하되 그 모듈을 있다고 치지는 않는다 | 코드 확인 |
| R-14 | 작업 디렉터리 | `main`이 R-01 순서대로 지원 파일이 1개 이상일 때만, 소스 루프 이전에 `prepare_output_dir(OUTPUT_DIR)`를 부른다. 실패(`ExtractionError`)는 소스 루프 밖이라 잡히지 않고 파이썬 기본 동작(트레이스백, 종료 1)으로 끝난다. 안전 규칙과 경로 결정은 extract-artifacts R-01·R-02 | 코드 확인 |

- 불변식: 같은 인자·같은 파일 시스템이면 입력 목록은 같다(폴더·glob 확장분은 정렬, 중복은 첫 등장 유지).
- 미결정: 없음
- 확인 한계: 정적 읽기만 했고 실행하지 않았다. `ask` + TTY에서 `input()`이 EOF(Ctrl-D)를 받으면 예외가 처리되지 않는 것으로 보이나 이는 파이썬 동작에 기댄 추론이다. `find_spec`이 있다고 하는 모듈이 실제로 import되는지는 이 단계에서 보장하지 않는다(그 실패는 추출 쪽에서 `ImportError`로 처리되는 포맷별 규칙).

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `book_to_skill/config.py:37-45`, `60-61` `TEXT_EXTENSIONS`, `HTML_EXTENSIONS`, `CALIBRE_EBOOK_EXTENSIONS`, `SUPPORTED_EXTENSIONS`, `supported_formats_message` | 지원 확장자 집합과 오류 메시지용 목록 | R-05, R-06, R-08 |
| C-02 | `book_to_skill/utils.py:1222-1257` `parse_arguments` | 토큰 소비 규칙, 모드 정규화 | R-02, R-03 |
| C-03 | `book_to_skill/dependencies.py:137-151` `normalize_install_mode` | 설치 모드 우선순위와 값 → 모드 표(`yes`: 1·true·y·yes·install, `no`: 0·false·n·no·fallback·skip) | R-04 |
| C-04 | `book_to_skill/utils.py:1260-1316` `resolve_input_files` | 입력 해석(`~`, glob, 폴더, 명시 파일), 정렬, 중복 제거 | R-05~R-07 |
| C-05 | `book_to_skill/utils.py:1420-1452` (`extract_single_file` 안 매직바이트 블록) | 매직바이트 판별과 오류 | R-08 |
| C-06 | `book_to_skill/dependencies.py:215-264` `prepare_dependencies` | 확장자·모드 → 제안 대상 모듈·폴백 문구 표(PDF technical → docling; PDF이고 `pdftotext` 없음 → pypdf·pdfminer 중 하나; EPUB → ebooklib+bs4; HTML → trafilatura·bs4 중 하나; DOCX → docx; RTF → striprtf) | R-09 |
| C-07 | `book_to_skill/dependencies.py:80-81`, `110-115`, `118-134`, `154-212`; `book_to_skill/config.py:47-57` `python_module_available`, `missing_python_packages`, `install_python_packages`, `offer_dependency_install`, `PYTHON_DEPENDENCIES` | 점검·질문·설치·재점검 절차와 모듈 → pip 패키지명 표 | R-10, R-11 |
| C-08 | `book_to_skill/dependencies.py:16-77`, `84-107`, `267-343` `DEPENDENCY_GROUPS`, `isolated_install_hint`, `run_dependency_check` | `--check` 그룹 정의·충족 판정·출력 | R-13 |
| C-09 | `book_to_skill/utils.py:1454-1460` | `prepare_dependencies` 호출 위치와 Calibre 점검 | R-09, R-12 |
| C-10 | `book_to_skill/utils.py:1804-1830` `main` 앞부분 | 진입 순서·종료 코드 | R-01, R-14 |

### 1.6 수락 사례
출처: 모두 구현에서 도출(정적 읽기, 실행 안 함). 원본 테스트는 열지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-03 | `--mode Technical`, `--mode foo` | 각각 `technical`, `text` |
| T-02 | R-02, R-04 | 인자가 `--install-missing book.pdf`뿐 | 입력 경로 0개라 `No input document…` 종료 1. 설치 모드는 `ask`(값 `book.pdf`는 표에 없음) |
| T-03 | R-04 | 환경변수 `BOOK_SKILL_INSTALL_MISSING=no`에 `--install-missing` | `yes`. `--no-install-missing`도 같이 주면 `no` |
| T-04 | R-05, R-06 | 폴더에 `B.PDF`, `a.txt`, `c.zip`, `sub/d.epub` | `a.txt`, `B.PDF`, `sub/d.epub`가 소문자 경로 순서로 나오고 `c.zip`은 빠진다 |
| T-05 | R-07 | `*.pdf`가 일치 0개인 glob 하나만 | 목록 비어 `No supported files found…` 종료 1 |
| T-06 | R-07 | 없는 경로 `nope.pdf` 하나 | 목록에 있고 `File not found`로 건너뜀, 전 소스 실패라 종료 1 |
| T-07 | R-08 | 명시 파일 `book.bin`이 `%PDF-`로 시작 | `format == "pdf"`로 처리 |
| T-08 | R-08 | 명시 파일 `x.dat`이 `PK`로 시작하는 일반 ZIP | `Unsupported ZIP-based format` |
| T-09 | R-08 | `fake.pdf`가 실제로는 EPUB | 내용을 보지 않고 PDF로 처리 |
| T-10 | R-09, R-10 | `--mode technical`, PDF, Docling 없음, 설치 모드 `ask`, 비대화형 | `Technical PDF extraction uses docling if installed, otherwise the PDF text fallback chain.` 후 폴백 안내. pip 실행 안 함 |
| T-11 | R-10 | PDF, `pdftotext` 없음, pypdf·pdfminer 둘 다 없음, 모드 `yes` | `pypdf` 한 개만 설치 시도 |
| T-12 | R-12 | `.mobi`, `ebook-convert` 없음 | 그 소스 `ExtractionError`로 건너뜀 |
| T-13 | R-13 | `--check`, 모든 모듈·`pdftotext` 있음 | 종료 0, `All optional dependencies are installed…`, 작업 디렉터리 안 만듦 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-14 | C-10; `book_to_skill/cli.py:17-30` | `main`·`cli.main` 읽기. 소스 루프 밖에서 `prepare_output_dir` 호출(`utils.py:1830`)과 `try`가 루프 안(`1837-1842`)에만 있음을 확인 |
| R-02, R-03 | C-02 | 코드 읽기 |
| R-04 | C-03 | 코드 읽기. `argv`는 `parse_arguments`가 받은 `sys.argv` 전체(프로그램 이름 포함) |
| R-05~R-07 | C-04, C-01 | 코드 읽기. 틸드 처리 사례 이름만 확인(`tests/test_tilde_expansion.py`), 열지 않음 |
| R-08 | C-05 | 코드 읽기 |
| R-09 | C-06, C-09 | 코드 읽기 |
| R-10, R-11 | C-07 | 코드 읽기 |
| R-12 | C-09 | 코드 읽기 |
| R-13 | C-08 | 코드 읽기. 상태 문구의 의미는 코드가 정한 대로만 적었다 |
| T-01~T-13 | 위 C-ID | 구현에서 도출, 실행하지 않음 |

문서와 구현의 차이 (구현이 사실):
- `SKILL.md:110`의 지원 확장자 목록에는 `.text`, `.asciidoc`, `.xhtml`이 없지만 `config.py:37-45`에는 있다. 구현 기준으로 쓴다.
- usage는 `--install-missing ask|yes|no`만 보이지만(`utils.py:1793`) 실제로는 C-03 표의 동의어도 받는다.
- `SKILL.md:242`는 `$INPUT_PATHS`를 따옴표 없이 넘긴다. 공백이 든 경로는 에이전트의 셸에서 갈라질 수 있다(추출기 동작이 아니라 명세 텍스트의 관찰).
- `--check` 보고에서 필수 의존성이 없는 PDF(텍스트용) 그룹도 `fallback available…`으로 나온다(필수 표시는 MOBI/AZW 그룹만 가짐: `dependencies.py:68-76`, `320-323`). 실제 PDF 추출은 엔진이 모두 없으면 실패한다는 점과 어긋나 보인다(후자는 pdf-extraction R-12).
- `parse_arguments`의 docstring과 usage는 `--install-missing`이 경로를 삼킬 수 있다는 점을 말하지 않는다(R-02).

### 2.2 코드 읽는 순서
`utils.py` `main`(1804~) → `parse_arguments`(1222) → `normalize_install_mode`(`dependencies.py:137`) → `resolve_input_files`(1260) → `extract_single_file` 앞부분(1403~1460) → `prepare_dependencies`/`offer_dependency_install` → `run_dependency_check`.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-02 | `--install-missing` 값은 알려진 값(`yes`/`no`/`ask`와 동의어)일 때만 소비하고, 아니면 경로로 둔다 | 입력 경로가 조용히 사라지는 것을 막는다 | T-02가 "book.pdf가 입력으로 남고 설치 모드는 `yes`"로 바뀐다 |
| R-06 | 폴더·glob 확장에서 건너뛴 지원 밖 파일을 한 줄로 알린다 | 폴더 안 확장자 없는 PDF가 말없이 빠진다 | 새 stderr 안내 |
