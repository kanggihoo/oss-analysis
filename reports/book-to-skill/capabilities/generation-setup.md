---
sha: "e7bb659d3261491c8b28793dcb9102fa64a46c22"
created: 2026-11-04
updated: 2026-11-04
sources:
  - SKILL.md
  - book_to_skill/utils.py
  - book_to_skill/config.py
  - tests/test_scope_selection_contract.py
  - docs/how-it-works.md
depends:
  - ./extract-artifacts.md
status: ready
---

# 생성 준비 (비용 확인, 책 유형·목적 질문, 이름·저장 위치)

> 추출이 끝난 `metadata.json`의 크기 정보로 비용을 사용자에게 보여 주고 확인받은 뒤, 책 유형(`BOOK_TYPE`)과 목적(`DEPTH`)을 질문으로 정하고, 책 앞부분에서 제목·저자·구조를 파악하고, 스킬 이름과 저장 위치(`SKILLS_HOME`)를 정하는 에이전트 지시의 계약.

## 1부. 동작 설명

이 기능의 "코드"는 `SKILL.md`의 단계별 지시문이다. 에이전트가 따르는 명세이므로 아래 규칙은 "에이전트에게 주는 지시의 내용"이다. 파이썬 코드가 있는 부분(`estimate_tokens`, `parse_arguments`의 `--mode`, 메타데이터 필드)만 실제 코드로 확인했다. 검증 수준 표기는 1.4 머리말에 정의한다.

### 1.1 한눈에 보는 흐름
1. (Step 1.5) 추출 전에 사용자에게 내용 유형을 묻고 `BOOK_TYPE`(`technical` / `text`)을 정한다.
2. (Step 2, 경계) `BOOK_TYPE` 값을 `--mode`로 넘겨 추출기를 실행한다. 결과는 [추출 산출물 계약](./extract-artifacts.md)의 `full_text.txt`·`metadata.json`이다.
3. (Step 2.5) `metadata.json`으로 입력·출력 토큰과 시간을 추정해 보여 주고, 사용자 확인을 기다린다. 확인 전에는 생성하지 않는다. 사용자가 "analyze only"라고 하면 분석 전용 모드로 바뀐다.
4. (Step 2.6) 책이 약 50k 토큰을 넘으면 이후 단계에서 `full_text.txt`를 통째로 읽지 않고 `wc`·`grep`·`sed`·구간 `Read`로 필요한 구간만 읽는다.
5. (Step 3) `full_text.txt` 앞 8,000자를 읽어 제목·저자·장 구조·핵심 주제를 파악하고, 목차가 있으면 그것으로 장 목록을 만든다. 분석 전용 모드는 여기서 보고서를 내고 끝난다.
6. (Step 4) 목적을 묻고 답에서 `DEPTH`(`reference` / `study`)를 정한다(추가 질문 없음).
7. (Step 5) 스킬 이름과 저장 위치를 정하고, 같은 이름이 이미 있으면 처리 방법을 묻는다. 이후 스킬 파일 쓰기(Step 6~)는 [스킬 작성·질의 시 로딩](./skill-authoring.md)이다.

### 1.2 범위·통합 지점
- 제공: 질문 두 개(`BOOK_TYPE`, 목적)와 그 답이 만드는 변수, `--mode` 결정, 비용 추정과 확인 지점, 큰 책의 읽기 방식 지시, 책 앞부분 분석과 분석 전용 보고서 틀, 스킬 이름·저장 위치(범위·호스트별 규칙)·이름 충돌 처리.
- 제외:
  - 스킬 파일 쓰기(장 요약, 보조 파일, 마스터): `./skill-authoring.md`.
  - 입력 경로 검증과 확장자 해석(Step 0 일부, Step 1, feature map 행 1), 추출 실행과 엔진 선택(Step 2, 행 2~4), `full_text.txt`·`metadata.json` 형식(S1).
  - 재실행 가드와 끊긴 실행의 작업 디렉터리 재사용(Step 0, 행 10), 갱신·Fold-in 본체(Update / Fold-in Workflow, 행 10). 이 스펙은 "Fold-in으로 분기한다"까지만 정한다.
  - 스킬 스캔·심볼릭 링크·정리·보고·게시(Step 9.5, 10, 11, 행 11). 호스트별 설치 후 발견 확인(`hermes skills list` 등)도 여기에 속한다.
  - "사전 분석에서 생성"(Mode 3): 입력인 분석 노트의 형식이 어디에도 정의돼 있지 않고, 원문이 Step 4 실행 여부와 `BOOK_TYPE` 출처를 서로 모순되게 적고 있어(2.1) 이 스펙의 흐름에 넣지 않았다. 이 스펙은 Mode 1(전체 변환)과 Mode 2(분석 전용)의 준비 단계를 다룬다.
- 외부 의존·선행 계약: [추출 산출물 계약](./extract-artifacts.md)의 `metadata.json` 필드(`total_sources`, `sources[].filename`·`format`, `images_dropped`, `pages`, `words`, `estimated_tokens`, `workdir`)와 `full_text.txt`. 호출자는 사용자에게 질문하고 답을 받을 수 있는 대화 환경이다.
- 소유 상태·부작용: 변수 `BOOK_TYPE`, `DEPTH`, `SKILL_NAME`/`skill_name`, `SKILLS_HOME`(대화 안의 값). 디스크에는 Step 6 전까지 스킬 파일을 쓰지 않는다. 예외는 Step 5에서 사용자가 고른 "Overwrite"(기존 스킬 삭제)와 Claude Code의 실제 디렉터리 이전 제안(R-22)뿐이다. 추출기가 만든 작업 디렉터리는 S1 소유다.

### 1.3 인터페이스와 데이터 의미
| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `BOOK_TYPE` | enum `technical` \| `text`. Step 1.5 질문의 답 1(기술 중심)→`technical`, 2(글 중심)→`text`, 3(모름)→`text` | 질문은 추출 전에 한다. 값이 추출 방식(`--mode`)을 정하고, Step 2.5 추정과 Step 7 예산 행에도 쓰인다. 모든 답이 둘 중 하나로 정해지므로 "미정" 값은 없다 |
| `--mode` (추출기 옵션) | `--mode <technical\|text>`. `parse_arguments`가 읽는다 | 값은 소문자로 바꿔 받는다. `technical`·`text` 외의 값은 경고 없이 `text`로 바뀐다. 기본값 `text`. `--mode` 뒤 토큰은 무엇이든 값으로 소비한다(플래그나 경로여도). 값이 없으면(마지막 인자) 기본값 `text`. 기록은 `metadata.json`의 `extraction_mode`(S1) |
| 비용 추정 | 읽는 값: `total_sources`, 소스별 `filename`·`format`, `images_dropped`, `pages`, `words`, `estimated_tokens`. 출력: 입력 토큰, 출력 토큰, 합계, 시간(분) | 토큰 수만 보고하고 금액은 사용자의 현재 단가를 곱하게 한다. 시간 산식은 없다(1.4 확인 한계) |
| `estimated_tokens` | int. 추출기가 계산 | 규칙은 S1 1.3. CJK가 없으면 `int(단어 수 / 0.75)`. Step 2.5 추정과 Step 2.6 기준(50k)이 이 값에 의존한다. 최상위 값은 `SOURCE` 배너 글자를 포함한다(S1 불변식) |
| 큰 책 기준 | 약 50k 토큰(`estimated_tokens` 기준으로 읽힘) | 넘으면 구간 읽기 지시가 "선호"로 적용된다. 이하이면 한 번의 `Read`로 충분하다고 명시한다. 정확한 경계(50,000 포함 여부)는 정해져 있지 않다 |
| Step 3 읽기 범위 | `full_text.txt`의 앞 8,000자 | 파일은 소스 배너로 시작하므로(S1) 배너 글자도 이 안에 든다. 문자 단위이며 읽는 도구는 지정되지 않았다 |
| `DEPTH` | enum `reference` \| `study` | Step 4의 답에서 유도한다. 별도 질문 없음. 답이 옵션 3(특정 장·개념 참조)만이면 `reference`, 1·2·4 중 하나라도 있으면 `study`. 분석 전용·사전 분석 모드처럼 Step 4가 생략되면 `study` |
| 목적 답 | 옵션 1~4, 복수 선택 허용("Pick one or more") | 마스터 `SKILL.md` Core 절에서 무엇을 강조할지에도 가중치를 준다 |
| `SKILL_NAME` | optional string(슬러그) | 마지막 인자가 존재하는 파일·폴더·glob이 아니고 슬러그처럼 생겼으면(소문자·숫자·하이픈) 이름으로 취급(Step 0, 경계). 있으면 그대로 스킬 이름 |
| 이름 후보 | 두 형태: author-concept `{저자성}-{핵심개념}`, title(책 제목을 소문자·하이픈으로) | `SKILL_NAME`이 없을 때 둘을 제안하고 사용자가 고른다. 책이 방법론으로서 정체성이 뚜렷하면 author-concept를 기본으로 둔다 |
| 범위(scope) | `personal` \| `project`. 입력은 사용자의 명시 요청 또는 환경변수 `BOOK_TO_SKILL_SCOPE`(`project`·`personal`) | 요청이 없으면 개인 범위 기본값. 둘 다 가능하다는 이유로 범위를 묻지 않는다. 파이썬 코드는 이 환경변수를 읽지 않는다(에이전트만 읽음) |
| `SKILLS_HOME` | 경로 | 범위와 호스트로 정한 저장 루트. 스킬은 `$SKILLS_HOME/<skill_name>/`에 놓인다. 선택된 루트도 호스트의 쓰기 승인을 요구할 수 있다 |

### 1.4 행동 규칙과 남은 질문
검증 수준: `코드 확인`은 파이썬 코드를 읽었다는 뜻이다. `코드 확인 (명세 텍스트)`는 `SKILL.md` 지시문을 읽었다는 뜻이고, 에이전트가 그 지시를 실제로 따르는지는 이 열이 아니라 아래 확인 한계에 일괄 적는다(미확인).

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Full Conversion·분석 전용·Fold-in 흐름의 Step 1.5 | 추출 전에 내용 유형을 3지선다로 묻는다. 답 1→`technical`, 2→`text`, 3(모름)→`text`("빠른 방법을 쓰고 품질이 제한되어 보이면 경고")이다. 질문·선택지 문구는 C-02. 3번의 "경고"를 언제 어떻게 내는지는 지정돼 있지 않다 | 코드 확인 (명세 텍스트) |
| R-02 | `BOOK_TYPE`이 정해진 직후 | `technical`이면 "Docling을 시도하되 EPUB 등 다른 형식은 기존 추출기를 쓰고 코드·표·수식 구조가 손실될 수 있으니 각 소스의 `extraction_method`·`fallback_reason`을 보라"고 안내한다. `text`이면 "형식별로 가장 빠른 추출기, PDF는 pdftotext(있으면)"라고 안내한다. 문구는 C-02 | 코드 확인 (명세 텍스트) |
| R-03 | Step 2 명령 | 명령은 `--mode <BOOK_TYPE>`을 붙인다. `BOOK_TYPE`은 `technical`·`text`뿐이라 `parse_arguments`의 정규화(비허용 값→`text`)는 정상 흐름에서 일어나지 않는다. `--mode` 값은 소문자화되고, 값 없는 `--mode`와 비허용 값은 `text`가 된다 | 코드 확인 |
| R-04 | 추출 직후(Step 2→2.5) | 생성 전에 S1 R-11의 문서 확인(요청한 문서인지)을 거쳐 `metadata.json`을 읽는다. 이 확인 규칙은 S1이 소유한다 | 코드 확인 (명세 텍스트) |
| R-05 | Step 2.5 | 어떤 생성 단계보다 먼저, 다음을 사용자에게 보인다: 소스 수와 소스별 파일명·형식, 합산 쪽/절 수·단어 수·총 토큰(`~N K`), 입력·출력·합계 토큰, 시간, 생성될 파일(`SKILL.md` + 장 파일 + glossary + patterns + cheatsheet), 진행 여부 질문. 표시 틀은 C-05 | 코드 확인 (명세 텍스트) |
| R-06 | R-05의 입력 토큰 | `estimated_tokens` × 1.3(장별 패스의 프롬프트 오버헤드) | 코드 확인 (명세 텍스트) |
| R-07 | R-05의 출력 토큰 | `장 수 × 장당 예산 중간값 + 4,000(마스터 SKILL.md) + 4,500(glossary+patterns+cheatsheet)`. 장당 중간값은 `text`≈1,000, `technical`≈1,800이다. `DEPTH`는 Step 4에서 정해지므로 더 오를 수 있다. 사용자가 이미 참조용/깊은 학습을 밝혔으면 Step 7 매트릭스의 해당 행을 쓴다. 장 수가 어느 값인지(`chapters_detected`인지 Step 3 목록인지)는 지정돼 있지 않다 | 코드 확인 (명세 텍스트) |
| R-08 | 비용 표기 | 단가·모델 이름을 고정해 쓰지 않는다. 토큰 수에 사용자 모델의 현재 1M 토큰당 입력·출력 단가를 곱하라고 안내하고, 금액을 보이면 추정이며 날짜를 붙인다 | 코드 확인 (명세 텍스트) |
| R-09 | 사용자의 답 | 확인을 받기 전에는 진행하지 않는다. 답이 "analyze only"이면 Mode 2(분석 전용)로 바뀐다. 거절·그 밖의 답의 처리(중단 여부)는 명시되지 않았고 진행하지 않는다는 데까지가 문장 근거다 | 코드 확인 (명세 텍스트) / 추론(거절 시 중단) |
| R-10 | `images_dropped`(최상위) > 5 | R-05의 표시에 "N개의 원본 이미지를 읽지 않았다"는 경고를 넣는다. 추출기도 EPUB 하나의 이미지가 5개를 넘으면 별도 경고를 낸다(같은 숫자, 별개 경고, `images_dropped`가 None인 비EPUB는 합계에서 0) | 코드 확인 |
| R-11 | 책이 약 50k 토큰 초과 | Step 3·Step 7·Step 8에서 경계 없는 `Read(full_text.txt)` 대신 프로브를 쓰라고 지시한다: `wc -w`로 크기, `grep -n -E "^\s*(Chapter\|CHAPTER)\s+[0-9]+"`로 장 위치, `sed -n 'start,endp'`로 구간, `grep -c -i`로 프레임워크 언급 확인, `Read`의 offset/limit. 이 지시는 "prefer"이며 금지가 아니다. 명령 예는 C-06 | 코드 확인 (명세 텍스트) |
| R-12 | 책이 50k 토큰 이하 | 한 번의 `Read`로 충분하다(R-11 방식이 필수가 아니다). 이유 서술: 200쪽 책 ≈ 75k 토큰이고 장마다 전체를 다시 읽으면 28패스 ≈ 2M 입력 토큰이 든다 | 코드 확인 (명세 텍스트) |
| R-13 | Step 3 | `full_text.txt` 앞 8,000자에서 책 제목, 저자, 장 구조("Chapter N", "PART I", 번호 제목, 목차), 핵심 주제·분야, 대략의 장 수를 파악한다. 목차 절이 있으면 그것을 읽어 모든 장을 매핑한다. 소스가 여러 개여도 같은 앞 8,000자이며 소스별 처리는 지정돼 있지 않다 | 코드 확인 (명세 텍스트) |
| R-14 | 분석 전용 모드 | Step 3까지만 하고 추출 보고서를 낸 뒤 멈춘다. 스킬 파일은 만들지 않는다. 보고서 틀: 저자의 핵심 프레임워크, 핵심 원칙, 기법, 안티패턴, 제안 스킬 이름(`{author-lastname}-{core-concept}`), 감지한 장 표(번호·제목·주요 프레임워크). 보고서 저장 위치는 지정돼 있지 않다 | 코드 확인 (명세 텍스트) |
| R-15 | Step 4(전체 변환 전용) | 생성 전에 목적을 묻는다(복수 선택): 1 작업 중 프레임워크 적용, 2 저자의 사고 모델로 생각하기, 3 특정 장·개념 참조, 4 모두. 답으로 마스터 Core 절의 강조를 가중한다 | 코드 확인 (명세 텍스트) |
| R-16 | R-15의 답 | 옵션 3만 → `DEPTH=reference`. 1·2·4 중 하나라도 포함 → `DEPTH=study`. "공부 vs 참조"를 따로 묻지 않는다. `BOOK_TYPE`과 `DEPTH`가 합쳐 Step 7 장당 토큰 예산을 정한다 | 코드 확인 (명세 텍스트) |
| R-17 | Step 4가 생략되는 모드(원문은 "Modes 2/3") | `DEPTH=study`가 기본이다 | 코드 확인 (명세 텍스트) |
| R-18 | 이름 | `SKILL_NAME`이 있으면 그대로 쓴다. 없으면 author-concept와 title 두 후보를 제안하고 사용자가 고르게 한다. 방법론적 정체성이 뚜렷한 책은 author-concept가 기본이다 | 코드 확인 (명세 텍스트) |
| R-19 | 저장 위치 결정 순서 | 먼저 범위를 정한다(명시 요청 또는 `BOOK_TO_SKILL_SCOPE`). "프로젝트 로컬/프로젝트 출력" 요청은 프로젝트 행을, "개인/전역" 요청은 개인 행을 고른다. 요청이 없으면 개인 기본값(비 Hermes 호스트는 `~/.agents/skills`)이다. 범위를 필수 질문으로 묻지 않는다. 그다음 호스트를 파악한다. 이 규칙은 Step 0 재실행 가드의 "목적지 먼저 결정"에서도 같은 것을 쓴다 | 코드 확인 (명세 텍스트) |
| R-20 | 호스트별 루트 | 개인 기본은 교차 에이전트 루트 `~/.agents/skills`(Copilot CLI, Amp, Codex, OpenCode는 기본 탐색. Claude Code는 스캔하지 않으므로 Step 10이 `~/.claude/skills/<name>`에서 심볼릭 링크). 예외 호스트: Hermes는 `$HERMES_HOME/skills/<category>`(`HERMES_HOME` 기본 `~/.hermes`, 책 주제에 맞는 category, 링크 없음), OpenClaw는 `${OPENCLAW_STATE_DIR:-~/.openclaw}/skills`(공유 루트 `~/.agents/skills`는 상태 디렉터리가 미설정·기본일 때만 유효). 프로젝트 로컬 행과 전체 표는 C-09 | 코드 확인 (명세 텍스트) |
| R-21 | 선택 규칙(`Selection rules` 1~8) | (1) 개인 설치는 `~/.agents/skills`(없으면 만든다). 단 `~/.agents/skills`가 없고 호스트의 개인 전용 루트에 이미 스킬이 있으면 그 루트를 쓰고 보고서에 이유를 적는다. (2) Claude Code 링크는 Step 10. (3) Hermes 개인 설치는 Hermes 행, 링크 없음. (4) 사용자가 호스트 전용 루트(`~/.copilot/skills`, `~/.claude/skills`, `~/.config/agents/skills`, `~/.config/amp/skills`)를 명시하면 따르고 링크는 생략. (5) 프로젝트 로컬을 명시하면 그 호스트의 프로젝트 행. (6) 선택에 호스트가 필요한데 파악이 안 되면 "OpenCode, OpenClaw, Hermes Agent, GitHub Copilot CLI, Amp, Codex, Claude Code 중 어디에서 실행 중인가?"를 묻는다. (7·8) OpenClaw 개인 출력은 활성 상태 루트. 규칙 목록은 하나의 연속된 1..N 목록이어야 한다는 것이 원본 테스트로 고정돼 있다 | 코드 확인 (명세 텍스트) |
| R-22 | 이름 충돌 검사 | `$SKILLS_HOME/<skill_name>/`가 이미 있는지 본다. Claude Code이면 `~/.claude/skills/<skill_name>`이 심볼릭 링크가 아닌 실제 디렉터리로 있는지도 보고, 있으면 `~/.agents/skills/`로 옮기고 원래 자리를 심볼릭 링크로 바꾸는 이전을 계속하기 전에 제안한다 | 코드 확인 (명세 텍스트) |
| R-23 | 스킬이 이미 있음 | 세 가지를 묻는다: 1 Update / Fold-in(Mode 4), 2 Overwrite(삭제 후 처음부터 재생성), 3 Rename(`-2`를 붙이거나 다른 슬러그). 1을 고르면 Update / Fold-in Workflow(행 10)로 가고 Step 3·4·6·7·8·9는 건너뛴다 | 코드 확인 (명세 텍스트) |

- 불변식: 사용자 확인(R-09) 이전에 스킬 파일을 쓰지 않는다. `BOOK_TYPE`은 추출 전에, `DEPTH`는 추출·확인 이후(Step 4)에 정해진다. 따라서 `--mode`는 `DEPTH`에 영향을 받지 않는다.
- 미결정: 없음.
- 확인 한계:
  - 에이전트가 이 지시들을 실제로 따르는지(질문 순서, 확인 대기, 구간 읽기)는 실행하지 않아 미확인이다. 추출기 코드는 실행하지 않았다.
  - 원문이 에이전트 재량으로 둔 곳(결과를 정해 쓴 것이 아니라 지시 자체가 정의하지 않는 곳): 시간 추정 산식, R-07의 "장 수" 출처, 다중 소스일 때의 제목·저자 선택, 3번 답의 경고 시점, Overwrite 시 삭제 시점과 범위, Rename 뒤 재검사 여부, `BOOK_TO_SKILL_SCOPE`와 사용자 요청이 충돌할 때의 우선순위, "호스트의 개인 전용 루트"가 정의되지 않은 호스트(Codex 등), 호스트를 파악하는 방법.
  - 외부 호스트가 `~/.agents/skills` 등을 실제로 탐색하는지는 외부 시스템의 동작이라 확인하지 않았다(명세가 그렇게 가정한다는 것만 확인).

### 1.5 필수 코드 참조
표·템플릿·예산 수치는 원문이 더 정확하므로 그대로 넘긴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `SKILL.md:43-65` Modes of Operation | 네 모드의 트리거·단계 범위(1 전체, 2 분석 전용, 3 사전 분석, 4 갱신) | R-09, R-14, R-17, R-23 |
| C-02 | `SKILL.md:116-135` Step 1.5 | 질문·선택지 원문, 답→`BOOK_TYPE` 매핑, 두 안내 문구 | R-01, R-02 |
| C-03 | `SKILL.md:242` | `--mode <BOOK_TYPE> --install-missing ask` 명령 줄 | R-03 |
| C-04 | `book_to_skill/utils.py:1222-1257` `parse_arguments` | `--mode` 소비·소문자화·정규화, 기본값 `text` | R-03 |
| C-05 | `SKILL.md:261-294` Step 2.5 | 비용 표시 틀(265-286), 추정 규칙(288-293), 확인 대기(294) | R-05~R-10 |
| C-06 | `SKILL.md:298-323` Step 2.6 | 50k 기준, 프로브 명령 예시, 적용 대상 단계 | R-11, R-12 |
| C-07 | `SKILL.md:327-358` Step 3 | 앞 8,000자 읽기 항목, 분석 전용 보고서 틀 | R-13, R-14 |
| C-08 | `SKILL.md:362-378` Step 4 | 목적 질문 원문, `DEPTH` 유도 규칙 | R-15~R-17 |
| C-09 | `SKILL.md:382-419` Step 5 | 이름 후보, 범위 해석, 호스트별 루트 표(393-405, 표 안에 설명 문단이 끼어 있음), Hermes·OpenClaw·OpenCode 설명, 선택 규칙 1~8 | R-18~R-21 |
| C-10 | `SKILL.md:421-427` | 기존 스킬 검사, 실제 디렉터리 이전 제안, 세 선택지 | R-22, R-23 |
| C-11 | `book_to_skill/utils.py:92-108` `estimate_tokens` | 토큰 추정식. 상수 `config.py:31,35`, CJK 범위 `utils.py:85-89`. 전체 설명은 S1 1.3 | R-06, R-07, 1.3 |
| C-12 | `SKILL.md:88` | 생성 스킬의 기본 루트와 `BOOK_TO_SKILL_SCOPE` 설명 | R-19 |

### 1.6 수락 사례
출처: 모두 명세 텍스트와 코드에서 도출(정적 읽기, 실행 안 함). T-02·T-03은 원본 테스트에도 같은 취지의 사례가 있다(2.1).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-03 | 사용자가 유형 질문에 "3. Not sure" | `BOOK_TYPE=text`, 명령에 `--mode text` |
| T-02 | R-03 | `parse_arguments(["extract.py","a.pdf","--mode","TECHNICAL"])` | 모드 `technical`, 입력 경로 `["a.pdf"]` |
| T-03 | R-03 | `--mode invalid`, 또는 `--mode`가 마지막 인자 | 모드 `text`, 경고 없음 |
| T-04 | R-06, R-07 | `estimated_tokens=90,000`, `text`, 장 12개 | 입력 ≈117,000, 출력 ≈ 12×1,000+4,000+4,500=20,500, 합계 ≈137,500 |
| T-05 | R-07 | `technical`, 장 20개 | 출력 ≈ 20×1,800+8,500=44,500 |
| T-06 | R-10 | 최상위 `images_dropped=7` | 표시에 이미지 경고. `5`이면 경고 없음 |
| T-07 | R-09 | 비용 표시 뒤 사용자가 "analyze only" | Mode 2: Step 3 보고서 후 종료, 스킬 파일 없음 |
| T-08 | R-11, R-12 | `estimated_tokens=60,000` / `40,000` | 60k: 구간 읽기 지시 적용. 40k: 단일 `Read` 허용 |
| T-09 | R-16 | 목적 답 "3" / "1, 3" / "4" | `reference` / `study` / `study` |
| T-10 | R-21 | `~/.agents/skills`가 없고 `~/.claude/skills`에 스킬이 이미 있는 Claude Code | 개인 루트로 `~/.claude/skills`를 쓰고 이유를 보고. 링크 생략 |
| T-11 | R-23 | 같은 이름의 스킬이 있고 사용자가 Rename 선택 | 슬러그에 `-2` 또는 새 슬러그를 쓴다. 재검사 여부는 확인 한계 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-02 `SKILL.md:116-135` | 명세 텍스트 읽기 |
| R-03 | C-03, C-04. 테스트 `tests/test_book_to_skill.py:559-568`(technical, invalid→text) | 코드 읽기. `parse_arguments` 1222-1257을 직접 확인. `--mode` 분기 1231-1236, 정규화 1254-1255 |
| R-04 | `SKILL.md:253-257`, S1 R-11 | 명세 텍스트 |
| R-05~R-10 | C-05. R-10의 5는 `utils.py:64` `_EPUB_IMAGE_NOTICE_THRESHOLD`, 사용 `utils.py:1499`, 합계 `utils.py:1870-1872` | R-10의 추출기 쪽은 코드 확인 |
| R-11, R-12 | C-06 | 명세 텍스트. "Use this approach for Step 3, 7, 8"(321행) |
| R-13, R-14 | C-07 | 명세 텍스트. 문서와 다름: `docs/how-it-works.md`는 "구조 분석이 모든 소스를 아우른다"고 쓰지만 `SKILL.md`는 앞 8,000자를 읽는다고 쓴다. `SKILL.md`를 사실로 썼다 |
| R-15~R-17 | C-08 | 명세 텍스트. 원문 모순: 378행은 Step 4가 생략되는 "Modes 2/3"의 기본값을 정하지만, 59행은 Mode 3이 "Steps 4–9를 실행"한다고 쓴다. Mode 3이 이 스펙에서 빠진 이유 |
| R-18 | `SKILL.md:384-389`, Step 0 `SKILL.md:99-101` | 명세 텍스트 |
| R-19~R-21 | C-09, C-12. 테스트 `tests/test_scope_selection_contract.py`(범위 기본값, 규칙 목록 연속성, OpenCode 행) | 명세 텍스트. 환경변수는 `.py`에서 읽지 않음을 `grep`으로 확인. 서식 결함: 표 앞뒤 문단이 끼어 OpenCode 행(405행)이 표 밖에 놓이고 Hermes 문단이 402행·407행에 중복된다. 테스트는 OpenCode 행이 정확히 하나라는 것만 요구한다 |
| R-22, R-23 | C-10, C-01 | 명세 텍스트. 순서 이상: 427행은 Fold-in 선택 시 "Step 2.5 뒤로 바로 가고 Step 3·4를 건너뛴다"고 쓰지만 Step 5는 Step 3·4 다음이다. Step 0 가드가 이름을 미리 잡으면 3·4 전에 갈라지지만 이름이 Step 5에서 정해지면 이미 실행된 뒤다. 순서가 모순인지 의도인지는 정해지지 않았다 |
| T-02, T-03 | C-04 | 코드에서 도출 |
| T-04, T-05 | C-05 | 산술 |
| 기타 T | 해당 R-ID의 C-ID | 명세에서 도출 |

문서와 구현·명세의 차이:
- `docs/how-it-works.md`(33행)는 장 요약을 "800–1,200 tokens each"로, 작업 디렉터리를 고정 경로 `/tmp/book_skill_work/`로 적는다. `SKILL.md`는 `BOOK_TYPE`×`DEPTH` 매트릭스(skill-authoring)와 실행마다 다른 `book_skill_work-<pid>`를 쓴다. `SKILL.md`를 사실로 썼다.
- Step 2.5의 보조 상수 4,500은 Step 8 최대치 합(1,500+2,000+1,200=4,700)과 다르다. 추정용 근삿값이라 모순으로 보지 않았다(추론).
- Step 2.5의 "Pages/Sections" 값은 `metadata.json` `pages`의 합이다. `utils.py:1465,1496,1576`에서 PDF는 쪽 수, EPUB은 spine 항목 수, 나머지 형식은 0이다(S1 1.3은 "PDF 외는 0"으로 적었으나 EPUB은 0이 아니다. S1을 고치지 않고 여기 남긴다).

### 2.2 코드 읽는 순서
`SKILL.md` 116(Step 1.5) → 242(명령) → `utils.py:1222`(`parse_arguments`) → 261(Step 2.5) → 298(Step 2.6) → 327(Step 3) → 362(Step 4) → 382(Step 5). 토큰 추정은 `utils.py:92`.

## 적용 메모
없음.
