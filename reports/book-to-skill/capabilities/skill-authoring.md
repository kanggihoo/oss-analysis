---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - SKILL.md
  - book_to_skill/utils.py
  - book_to_skill/config.py
  - tests/test_skill_template_full_text.py
  - docs/how-it-works.md
depends:
  - ./generation-setup.md
  - ./structure-detection.md
  - ./extract-artifacts.md
status: ready
---

# 스킬 작성과 질의 시 로딩

> 준비 단계에서 정해진 변수(`BOOK_TYPE`, `DEPTH`, `skill_name`, `SKILLS_HOME`)와 추출 산출물을 받아, 에이전트가 장 요약 파일, 보조 파일 3개, 4K 토큰 안의 마스터 `SKILL.md`로 이루어진 스킬 폴더를 쓰고, 이후 질문이 오면 색인으로 장 파일 하나만 읽게 하는 지시의 계약.

## 1부. 동작 설명

이 기능의 "코드"는 `SKILL.md`의 Step 6~9와 Quality Rules다. 에이전트(LLM)가 따르는 지시이므로 규칙은 "에이전트에게 주는 지시의 내용"이다. 파이썬 코드는 이 기능에 없고, 메타데이터 필드(`output_text`, `workdir`)만 코드로 확인했다. 검증 수준 표기는 1.4 머리말을 따른다.

### 1.1 한눈에 보는 흐름
1. 입력: [생성 준비](./generation-setup.md)가 정한 `BOOK_TYPE`, `DEPTH`, `skill_name`, `SKILLS_HOME`, Step 3의 장 목록과 제목·저자, 그리고 작업 디렉터리의 `full_text.txt`·`metadata.json`([S1](./extract-artifacts.md)).
2. (Step 6) `$SKILLS_HOME/<skill_name>/chapters/` 디렉터리를 만든다.
3. (Step 7) 장마다 해당 구간만 읽고 `chapters/ch<NN>-<slug>.md`를 쓴다. 분량은 `BOOK_TYPE`×`DEPTH` 표가 정한다.
4. (Step 8) `glossary.md`, `patterns.md`, `cheatsheet.md`를 쓴다.
5. (Step 9) 장 파일을 가리키는 마스터 `SKILL.md`를 쓴다: 핵심 틀(약 2,000 토큰) + 장 색인 + 주제 색인 + 보조 파일 목록 + 범위·한계. 본문은 4,000 토큰 미만.
6. (경계) 스캔(Step 9.5), 링크·정리·보고(Step 10)는 이 스펙 밖이다. 단 Step 10이 작업 디렉터리를 지우므로 R-17이 이 기능과 맞닿는다.
7. 사용 시점: 사용자가 이 스킬에 질문하면 마스터의 사용 안내와 색인으로 장 파일 하나만 읽어 답한다(R-16).

### 1.2 범위·통합 지점
- 제공: 생성된 스킬 폴더의 구조와 파일별 형식·예산, 작성 순서, 장 구간을 읽는 방법, 마스터 템플릿과 색인 규칙, 품질 규칙 7개, 질의 시 사용 방식(생성된 스킬 본문이 에이전트에게 주는 지시).
- 제외:
  - 비용 확인, 유형·목적 질문, 이름·저장 위치 결정: [생성 준비](./generation-setup.md).
  - `chapter_ranges`와 장 구조를 만드는 규칙: [구조 감지](./structure-detection.md). 이 스펙은 `chapter_ranges`가 "있을 수도 없을 수도 있다"는 것만 가정한다(R-03).
  - 호스트가 스킬을 발견·로드하는 방식, 컴팩션 동작: 호스트 소유.
  - 보안 스캔(Step 9.5), 심볼릭 링크·정리·최종 보고(Step 10), GitHub 게시(Step 11): feature map 행 11. 갱신·Fold-in(Update / Fold-in Workflow)과 그 안의 `patterns.md` 2,500 토큰 상한은 행 10.
  - Mode 3(사전 분석에서 생성): 입력 형식 미정의([생성 준비](./generation-setup.md) 1.2).
- 외부 의존·선행 계약: S1의 `metadata.json`(`chapter_ranges`, `output_text`, `workdir`, `images_dropped`, `pages`)과 `full_text.txt`. 에이전트는 shell과 파일 읽기·쓰기가 가능해야 한다. 쓰기 위치 승인은 호스트가 요구할 수 있다.
- 소유 상태·부작용: `$SKILLS_HOME/<skill_name>/` 아래에 `SKILL.md`, `chapters/*.md`, `glossary.md`, `patterns.md`, `cheatsheet.md`를 만든다. 작업 디렉터리는 읽기만 한다. 기존 스킬이 있는 경우의 처리는 생성 준비가 정하고, 이 기능은 새 디렉터리를 쓰는 것으로 시작한다.

### 1.3 인터페이스와 데이터 의미

**생성된 스킬 폴더**
| 파일 | 내용 | 예산 |
|---|---|---|
| `SKILL.md` | 마스터. 프런트매터(`name`, `description`) + 사용 안내 + 핵심 틀 + 장 색인 + 주제 색인 + 보조 파일 목록 + 범위·한계 | 본문 4,000 토큰 미만. 핵심 틀 절 약 2,000 |
| `chapters/ch<NN>-<slug>.md` | 장 하나의 요약. 질문이 올 때만 읽힘 | `BOOK_TYPE`×`DEPTH` 표(C-02). 파일당 목표이며 상한이 아님 |
| `glossary.md` | 용어 사전 | 최대 1,500 토큰 |
| `patterns.md` | 기법·패턴 | 최대 2,000 토큰 |
| `cheatsheet.md` | 판단 규칙 중심 참조표 | 최대 1,200 토큰 |

**입력 필드**
| 항목 | 의미 |
|---|---|
| `metadata.json` 최상위 `chapter_ranges` | `{title, start_line, end_line}` 목록. 줄 번호는 1부터, 시작·끝 포함, `full_text.txt`(배너 포함) 기준. 소스가 하나이고 PDF outline이 쓰였을 때만 있다(S1 R-06). 없으면 장 제목 grep으로 구간을 찾는다 |
| `sources[].chapter_ranges` | 같은 필드이나 그 소스 텍스트만의 줄 번호. `full_text.txt` 구간을 읽는 데 쓰지 않는다 |
| `output_text` | 작업 디렉터리 안의 `full_text.txt` 절대 경로 문자열 |
| `images_dropped` | 최상위 합계. 5 초과이면 마스터 끝에 알림을 넣는다 |

**장 파일 이름**: `ch<NN>-<slug>.md`. 예시는 `ch01`, `ch05`, `ch12`다. NN은 두 자리로 쓰인 것으로 읽힌다(2자리 초과·slug 규칙은 정의돼 있지 않다).

**장 파일 구조(순서)**: `# Chapter N: <Full Title>` → Core Idea → Frameworks Introduced → Key Concepts → Mental Models → Anti-patterns → Code Examples(`technical`만) → Reference Tables(`technical`만) → Worked Example(`DEPTH=study`만) → Key Takeaways → Connects To. 절별 내용·형식은 C-03.

**마스터 `SKILL.md` 구조(순서)**: 프런트매터 → `<!-- argument-hint: ... -->` 주석 → 제목과 메타 줄(저자, 쪽, 장 수, 생성일) → How to Use This Skill → Core Frameworks & Mental Models → Chapter Index(표) → Topic Index → Supporting Files → Scope & Limits. 원문은 C-06.

### 1.4 행동 규칙과 남은 질문
검증 수준: `코드 확인`은 파이썬 코드를 읽었다는 뜻이다. `코드 확인 (명세 텍스트)`는 `SKILL.md` 지시문을 읽었다는 뜻이다. 에이전트가 지시를 실제로 따르는지는 이 열이 아니라 확인 한계에 일괄 적는다(미확인).

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Step 6 | `mkdir -p "$SKILLS_HOME/<skill_name>/chapters"`로 스킬 디렉터리와 `chapters/`를 만든다 | 코드 확인 (명세 텍스트) |
| R-02 | Step 7 대상 | Step 3에서 식별한 장·주요 절마다 장 파일 하나를 만든다. 경로는 `$SKILLS_HOME/<skill_name>/chapters/ch<NN>-<slug>.md`. "주요 절"의 기준과 Step 3 목록·`chapter_ranges`가 어긋날 때의 우선순위는 정해져 있지 않다 | 코드 확인 (명세 텍스트) |
| R-03 | 장 내용 읽기 | 최상위 `chapter_ranges`가 있으면 그 장의 `start_line`~`end_line`(1부터, 양끝 포함)을 `sed`/`Read`로 읽는다. 없으면 장 제목을 grep해 구간을 찾는다. `sources[].chapter_ranges`는 `full_text.txt`에 쓰지 않는다. 책이 약 50k 토큰을 넘으면 Step 7·8의 읽기 전체가 구간 읽기(생성 준비 R-11)를 따른다. 최상위 `chapter_ranges`가 없는 경우는 다중 소스 또는 outline 없음이다(S1) | 코드 확인 (명세 텍스트) |
| R-04 | 장당 토큰 예산 | 표(C-02)에서 고른다: `text`/`reference` 800–1,200, `text`/`study` 1,000–1,800, `technical`/`reference` 1,200–1,800, `technical`/`study` 2,000–3,000 토큰. 파일당 목표이지 하드 상한이 아니다(밀도 높은 장은 넘고 얇은 장은 못 미칠 수 있음). 두 칸 사이에서 망설여지면 낮은 쪽을 쓴다. 길이를 채우려 패딩하지 않는다. 장 파일은 읽힐 때만 토큰을 쓴다 | 코드 확인 (명세 텍스트) |
| R-05 | `DEPTH=study` | 예산을 숫자가 아니라 내용으로 채운다: (a) `## Worked Example`에 장의 구체 사례 하나(예: 샘플 문서, 대화, 채워진 템플릿, 저자가 끝까지 푸는 결정)를 압축해 재구성한다. 가장 큰 수단이다. (b) 각 프레임워크의 "How"를 명시적 단계·기준으로 늘린다. (c) 상위 1~2개 프레임워크에 "왜 통하는가 / 실패 양상" 메모를 붙인다. 사례가 없고 늘릴 수 없는 장은 study 하한 아래에 두고 Core Idea가 얇다고 적는다. `DEPTH=reference`는 Worked Example을 생략하고 결정에 필요한 핵심만 둔다 | 코드 확인 (명세 텍스트) |
| R-06 | `BOOK_TYPE`별 강조 | `technical`은 Code Examples, Reference Tables, Commands & APIs를 우선하고 문법을 그대로 보존한다. `text`는 Frameworks Introduced, Mental Models, Key Takeaways를 우선하고 빈 기술 절은 건너뛴다(Code Examples·Reference Tables 절 생략) | 코드 확인 (명세 텍스트) |
| R-07 | 장 파일 내용 | 저자의 프레임워크 이름을 정확히 보존한다. Key Concepts는 5~10개의 한 문장 정의, Mental Models는 2~4개("Use X when Y" 형식), Key Takeaways는 3~7개의 실행 가능한 항목이다. 원문을 길게 복사하지 않고 합성한다. 단, 템플릿은 코드·표·사례의 재현을 요구한다(Code Examples는 가장 교육적인 스니펫을 들여쓰기 그대로, Reference Tables는 비교·매개변수·결정 표를 마크다운으로, Worked Example는 압축 재구성). "긴 원문"의 길이 기준은 없다 | 코드 확인 (명세 텍스트) |
| R-08 | Step 8 `glossary.md` | 책의 중요한 용어를 알파벳순으로, `**Term** — definition (Ch N)` 형식으로, 최대 1,500 토큰 | 코드 확인 (명세 텍스트) |
| R-09 | Step 8 `patterns.md` | 구체적 기법·설계 패턴·알고리즘 전부. 항목 형식 `## Pattern Name` + `**When to use**` + `**How**` + `**Trade-offs**`. 최대 2,000 토큰 | 코드 확인 (명세 텍스트) |
| R-10 | Step 8 `cheatsheet.md` | 판단을 돕는 참조표이며 키워드 목록이 아니다. 우선순위: 결정 규칙("X일 때 Y, 이유 Z"), 결정 트리·표(분기 3개 이상), 트레이드오프 매트릭스, 임계값·기본값, 징후·냄새. 맨 용어-정의 행(glossary 역할)과 산문 문단(장 파일 역할)은 피한다. 컴팩트한 표·결정 규칙 위주, 한 쪽 분량, 최대 1,200 토큰 | 코드 확인 (명세 텍스트) |
| R-11 | Step 9 마스터 | `SKILL.md` 본문을 4,000 토큰 미만으로 쓴다. 컴팩션이 끝에서부터 자르므로 가장 중요한 내용을 앞에 둔다(Core Frameworks 약 2,000 토큰, 정확한 이름 보존, "Use X when Y" 형식). 프런트매터는 `name: <skill_name>`과 `description: "Knowledge base from \"<Full Title>\" by <Author(s)>. Use when applying <author>'s frameworks for <key topics, 3–6 terms>, studying the book, or referencing its concepts."`다. 인자 힌트는 프런트매터가 아닌 HTML 주석이다. 제목 아래 메타 줄은 `Author | Pages: ~N | Chapters: N | Generated: YYYY-MM-DD`. 컴팩션 동작 자체는 호스트 소유이므로 이 문장의 효과는 확인하지 않았다 | 코드 확인 (명세 텍스트) / 미확인(컴팩션) |
| R-12 | 마스터 색인 | Chapter Index 표는 장마다 한 행: `[chNN](chapters/chNN-<slug>.md)`, 제목, 주요 프레임워크. Topic Index는 알파벳순으로 `**용어** → ch<N>[, ch<N>]`를 둔다. 색인 링크는 스킬 폴더 기준 상대 경로이며 R-02의 파일 이름과 일치해야 한다 | 코드 확인 (명세 텍스트) |
| R-13 | 마스터 `How to Use` | 사용 방식 네 가지를 적는다: 인자 없음→핵심 프레임워크 로드, 주제→색인된 주제의 장을 찾아 읽음, 장 번호(`ch05`)→해당 장 로드, "what chapters do you have?"→전체 색인 보여 줌. 그리고 Core에 없는 주제는 답하기 전에 해당 장 파일을 읽는다고 밝힌다 | 코드 확인 (명세 텍스트) |
| R-14 | 마스터 `Supporting Files`, `Scope & Limits` | glossary·patterns·cheatsheet 링크 줄 세 개와 `Full text: <metadata.json의 output_text> — grep it for depth the chapter files omit (local extraction, not shipped)` 줄을 둔다. 끝에는 이 스킬이 책 내용만 다룬다는 안내를 두고, `images_dropped > 5`이면 N개의 원본 이미지를 읽지 않았다고 적는다 | 코드 확인 (명세 텍스트) |
| R-15 | 작성 순서와 품질 규칙 | 단계 순서는 6→7→8→9다. 마스터가 장 파일을 색인하므로 마지막이다(추론: 순서 자체는 단계 번호, 이유는 색인의 의존). 품질 규칙 7개: (1) 요약이 아니라 구조를 뽑는다, (2) 저자의 정밀한 이름 보존, (3) 완전함보다 밀도(1,000토큰 요약이 10,000토큰 발췌보다 낫다), (4) 실무자 어조("Use X when Y"), (5) 마스터 앞쪽에 중요한 것(컴팩션이 처음 5,000토큰을 유지한다고 주장), (6) 장 파일은 읽힐 때만 예산을 쓴다, (7) 원문을 복사하지 않고 합성한다 | 코드 확인 (명세 텍스트) / 미확인(5번의 컴팩션 주장) |
| R-16 | 질의 시 사용(생성된 스킬이 에이전트에게 주는 지시) | 질문이 오면 에이전트는 마스터의 Core를 보고, 거기 없는 주제면 Topic Index로 장 번호를 찾아 `chapters/` 파일 하나를 읽은 뒤 답한다. 깊이가 더 필요하면 `Full text` 경로를 grep한다. 이 지시가 본문에 있다는 것은 코드로 확인했고, 호스트가 마스터만 먼저 로드하고 장 파일을 따로 읽게 하는지는 호스트 소유라 확인하지 않았다 | 코드 확인 (명세 텍스트) / 추론(호스트 동작) |
| R-17 | Step 9의 `Full text` 줄과 Step 10 정리 | 두 지시가 같은 `SKILL.md`에 모두 있다. 마스터에 쓰이는 값은 `metadata.json`의 `output_text`이고, 코드는 이를 `OUTPUT_DIR/full_text.txt`(작업 디렉터리 안)로 만든다. Step 10은 "이 실행이 사용한 작업 디렉터리"(`Workdir ->` 경로 = `metadata.json`의 `workdir`)를 `rm -rf`(또는 `shutil.rmtree`)로 지우라고 한다. 따라서 Step 10을 수행한 뒤에는 마스터에 적힌 경로의 파일이 존재하지 않는다(지시를 따랐을 때의 결과). 파이썬 코드는 작업 디렉터리를 지우지 않는다(삭제 호출 없음). 이것이 의도된 구성인지 모순인지는 원문이 정하지 않았다(1.4 확인 한계). 삭제는 `BOOK_SKILL_WORKDIR`로 지정한 경로에도 같다("Remove the work directory this run actually used") | 코드 확인 (명세 텍스트·메타데이터 코드) / 추론(삭제 후 파일 없음, 개발자 의도) |

- 불변식: 마스터 `SKILL.md`의 모든 장 링크는 같은 실행이 만든 `chapters/` 파일을 가리킨다(R-12). 마스터는 장 파일을 읽지 않고 가리키기만 한다.
- 미결정: 없음.
- 확인 한계:
  - 에이전트가 지시를 실제로 따르는지(예산 준수, 구간 읽기, 파일 이름·링크 일치)는 실행하지 않아 미확인이다. 토큰 예산을 검사하는 코드는 없다(`tools/`·`book_to_skill/`에서 예산·4,000 검색이 없음). 에이전트가 토큰을 어떻게 세는지도 지정되지 않았다.
  - R-17의 Step 9↔10 관계: 두 텍스트와 `output_text`가 작업 디렉터리 안에 있다는 것은 확인했다. 원본 테스트(`tests/test_skill_template_full_text.py`)는 템플릿이 이 경로를 가리키는 것을 요구하고 docstring에 "스킬이 실제 책의 색인으로 동작하도록"이라 적었으며, 줄은 #315 커밋(`182e185`, 2026-11-03)에서 추가됐고 Step 10 정리는 그 이전부터 있었다. 이 자료만으로는 "삭제 뒤에도 쓰이는 것이 의도였는지", "일회성 로컬 경로(`not shipped`)로 두었는지", 단순 누락인지 가릴 수 없다. 의도는 추론이며 단정하지 않는다.
  - 원문이 에이전트 재량으로 둔 곳: 장 `NN`이 99를 넘을 때와 `slug` 규칙, "major section"의 기준, Step 3 목록과 `chapter_ranges` 불일치 시 우선순위, 메타 줄 `Pages: ~N`의 값(비PDF는 `pages`가 0이거나 spine 수), "긴 원문"의 길이 한계, 다중 소스의 제목·저자 표기.
  - 호스트가 스킬을 발견·로드하는 방식과 컴팩션 동작은 외부 시스템이라 확인하지 않았다.
  - 구조 감지의 결과(`chapter_ranges` 존재 여부)는 [구조 감지](./structure-detection.md)가 소유한다. 이 스펙은 있을 수도 없을 수도 있다는 가정만 쓰고 그 규칙은 읽지 않았다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `SKILL.md:431-435` Step 6 | 디렉터리 생성 명령 | R-01 |
| C-02 | `SKILL.md:441-452` Step 7 예산 | `BOOK_TYPE`×`DEPTH` 표(445-448)와 예산 운용 문장 | R-04 |
| C-03 | `SKILL.md:454-518` Step 7 | study 깊이를 내용으로 채우는 방법(454-459), 장 읽기 규칙(461-465), `BOOK_TYPE` 강조(467-469), 장 파일 템플릿(471-518) | R-03, R-05~R-07 |
| C-04 | `SKILL.md:522-551` Step 8 | 보조 파일 3개의 형식·상한, cheatsheet 우선순위 | R-08~R-10 |
| C-05 | `SKILL.md:555-560` Step 9 도입 | 4,000 토큰 상한, 앞쪽 배치 이유 | R-11 |
| C-06 | `SKILL.md:562-623` Step 9 템플릿 | 마스터 전체 틀. 프런트매터, 사용 안내, 색인 표, 보조 파일 줄(613 `Full text`), 범위·한계 | R-11~R-14, R-16, R-17 |
| C-07 | `SKILL.md:871-879` Quality Rules | 품질 규칙 7개 | R-15 |
| C-08 | `SKILL.md:672-707` Step 10 정리 | 작업 디렉터리 삭제 지시(`rm -rf "$WORKDIR"`, 같은 효과의 `shutil.rmtree`). 680-687에서 코드 펜스가 닫히지 않은 채 산문이 섞여 있다 | R-17 |
| C-09 | `book_to_skill/config.py:27-28` `OUTPUT_DIR`, `OUTPUT_TEXT` | `full_text.txt`는 작업 디렉터리 안 | R-17 |
| C-10 | `book_to_skill/utils.py:1946-1947` | `metadata.json`에 `workdir`, `output_text`를 기록 | R-14, R-17 |

### 1.6 수락 사례
출처: 모두 명세 텍스트와 코드에서 도출(정적 읽기, 실행 안 함). 생성된 파일의 품질은 검증하지 않고 지시가 정하는 구조·경로·예산만 확인한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-06 | `BOOK_TYPE=text`, `DEPTH=reference` | 장 파일 목표 800–1,200 토큰. Code Examples·Reference Tables·Worked Example 절 없음 |
| T-02 | R-04~R-06 | `BOOK_TYPE=technical`, `DEPTH=study` | 목표 2,000–3,000. 세 절 모두 있음. Worked Example이 없는 장은 하한 미달로 두고 Core Idea가 얇다고 적음 |
| T-03 | R-03 | 단일 PDF, 최상위 `chapter_ranges`의 3번째 항목이 `{start_line:120, end_line:310}` | 해당 장은 `sed -n '120,310p'` 또는 `Read`(offset 120, limit 191)로 읽는다. 시작·끝 줄 포함 |
| T-04 | R-03 | 소스 2개. 최상위 `chapter_ranges` 없음, `sources[0].chapter_ranges`만 있음 | 장 제목 grep으로 구간을 찾는다. `sources[0]`의 줄 번호는 `full_text.txt`에 쓰지 않는다 |
| T-05 | R-02, R-12 | 장 12개 | `chapters/ch01-...`~`ch12-...` 12개. 마스터 Chapter Index 12행, 각 링크가 같은 이름의 파일을 가리킨다 |
| T-06 | R-12 | 주제 "replication"이 ch04·ch07에 나옴 | Topic Index에 `**replication** → ch04, ch07`이 알파벳 위치에 있다 |
| T-07 | R-14 | `output_text="/tmp/book_skill_work-123/full_text.txt"` | 마스터 Supporting Files에 그 문자열이 `Full text` 줄로 들어간다 |
| T-08 | R-17 | T-07 상태에서 Step 10까지 지시대로 수행 | `/tmp/book_skill_work-123/`가 지워지고 마스터의 `Full text` 경로는 가리키는 파일이 없다 |
| T-09 | R-14 | 최상위 `images_dropped=7` / `5` | 7: Scope & Limits에 "7 source images were not read" 취지의 문장. 5: 없음 |
| T-10 | R-10 | cheatsheet 초안에 용어→정의 행과 산문 문단만 있음 | 지시 위반. 결정 규칙·표·임계값·징후로 채워야 한다 |
| T-11 | R-13, R-16 | 마스터 로드 후 사용자 "ch05" | 마스터 색인의 ch05 행이 가리키는 `chapters/ch05-*.md` 하나만 읽는다(생성된 스킬의 지시 기준. 호스트 동작은 검증하지 않음) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 명세 텍스트 |
| R-02 | `SKILL.md:461-465`, C-03 | 명세 텍스트. 파일명 예시 `SKILL.md:465,598-599` |
| R-03 | `SKILL.md:463`, `SKILL.md:321`(Step 3·7·8에 프로브 방식 적용), S1 R-06 | 명세 텍스트. `chapter_ranges` 지시는 #315 커밋에서 추가됨(`git show 182e185 -- SKILL.md`로 확인). 문서 `docs/how-it-works.md`에는 이 규칙이 없다 |
| R-04, R-05 | C-02, C-03 | 명세 텍스트. 문서와 다름: `docs/how-it-works.md:33`은 장 요약을 "800–1,200 tokens"로만 적는다. `SKILL.md`의 4칸 표를 사실로 썼다 |
| R-06, R-07 | C-03 | 명세 텍스트. 서로 겹치는 지시: 493행·500행은 스니펫·표를 "복사/재현"하라 하고 506-507행·879행은 원문 복사 금지를 말한다. 규칙을 합쳐 R-07에 적었다 |
| R-08~R-10 | C-04 | 명세 텍스트 |
| R-11~R-14 | C-05, C-06. README `~4,000 tokens`(`README.md:81`)와 일치 | 명세 텍스트 |
| R-15 | C-07, `SKILL.md:557-558` | 명세 텍스트. "컴팩션이 처음 5,000토큰을 유지"(877행)와 "끝에서 자른다"(558행)는 호스트 동작에 대한 주장이라 미확인 |
| R-16 | `SKILL.md:573-581`(How to Use), `SKILL.md:605`(Topic Index) | 명세 텍스트. 호스트 로딩은 확인하지 않음 |
| R-17 | C-06(613행), C-08, C-09, C-10. 테스트 `tests/test_skill_template_full_text.py`(템플릿에 `<output_text from metadata.json>`와 `grep`이 있는지 확인)와 git 이력 | 코드·명세 읽기. 삭제 호출이 없는 것은 `book_to_skill/*.py`, `scripts/extract.py`에서 `rmtree`·`os.remove`·`unlink`를 검색해 확인(`utils.py:1751`의 `unlink`는 PDF 사이드카 임시 파일). 의도는 추론. 서식 결함: 674행에서 연 코드 펜스가 687행까지 닫히지 않아(684행의 ` ```bash`는 닫는 펜스가 될 수 없다) 산문과 코드가 한 블록처럼 보인다. 지시 내용 자체는 읽을 수 있다 |
| T-01~T-11 | 해당 R-ID의 근거 | 명세에서 도출, 실행하지 않음 |

문서와 명세의 차이: 위 R-03·R-04에 적은 `docs/how-it-works.md` 항목 외에, 같은 문서의 고정 경로 `/tmp/book_skill_work/`는 현재 코드의 실행별 디렉터리(`config.py:27`, S1 R-02)와 다르다. `SKILL.md`·코드를 사실로 썼다.

### 2.2 코드 읽는 순서
`SKILL.md` 431(Step 6) → 439(Step 7) → 522(Step 8) → 555(Step 9) → 871(Quality Rules). `Full text` 줄과 정리의 관계는 613 → 672-707 → `config.py:27-28` → `utils.py:1946-1947`.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-14, R-17 | 선택지 가능성: Step 10 전에 `full_text.txt`를 스킬 폴더로 복사해 경로를 그쪽으로 바꾸거나, 삭제하기로 했으면 `Full text` 줄을 템플릿에서 빼거나 "삭제됨"을 알리는 문구로 바꾼다. 이는 원본의 미결정을 해소하는 것이 아니라 재구현에서 고를 수 있는 대안이다 | 정리 뒤에도 마스터가 존재하지 않는 경로를 가리키는 것을 피하기 위해 | 마스터 `Supporting Files`의 한 줄, Step 10의 정리 대상, T-08(대체 사례 필요) |
