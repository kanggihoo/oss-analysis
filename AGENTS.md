# AGENTS.md — oss-analysis workspace instructions

이 레포는 원본 코드를 보관하는 곳이 아니라, **AI와 함께 오픈소스를 탐색하고 검증한 지식을 축적하는 작업 공간**으로 운영한다.
기본 흐름은 **archify로 파악 → 질문 → 코드 검증 → reports 기록 → wiki 축적**이다.

- Workspace root: `/Users/kkh/Desktop/oss-analysis`
- Templates: `./templates`
- Helper scripts: `./scripts`
- Repo clones: `./repos/<repo>` (로컬 clone, Git 추적 제외)
- Raw artifacts: `./artifacts/<repo>` (분석기 출력, 외부 baseline, 실행 로그)
- Detailed reports: `./reports/<repo>` (개요, 질문별 분석, archify 다이어그램, 다음 세션 메모)
- Long-term wiki: `./wiki` (프로젝트 요약, 개념, 비교, 질의)

## 기본 원칙

1. **오픈소스 분석의 본질**: 단순히 코드를 읽거나 요약하는 데 그치지 않고, **증거 기반 분석(Evidence-backed Analysis)**을 수행한다.
2. **4대 입력/산출물 분리**:
   - 실제 local checkout: `repos/<repo>` (Primary Evidence)
   - raw artifact / 외부 자료: `artifacts/<repo>` (Reference / Candidate)
   - 레포별 상세 보고서: `reports/<repo>` (Detailed Findings & Evidence)
   - 재사용 장기 지식: `wiki/` (Durable Synthesized Knowledge)
3. **외부 자료 및 분석 도구의 취급**: DeepWiki 등 외부 자료나 분석기 출력은 '정답'이 아니라 **'분석 후보 / second opinion'**이다. 중요한 동작과 설계는 실제 local source 코드로 검증한다. 공식 근거가 없는 개발자 의도는 반드시 `추론`으로 명시한다.
4. **archify 중심의 시각화**:
   - 첫 지도는 archify로 주요 모듈 중심 구조도와 대표 실행 흐름을 작성한다.
   - 처음부터 모든 파일을 포함하지 않고 점진적으로 구체화한다.
   - 원본 JSON과 standalone HTML은 `reports/<repo>/diagrams/`에 함께 보관한다.
5. **reports vs wiki의 명확한 역할 분담**:
   - **reports**: 특정 질문에 대한 구체적 호출 경로, 코드 위치, 상세 그림, 실행 결과 기록 (상세 조사 보존).
   - **wiki**: 프로젝트 핵심 요약, 설계 원리, 패턴, 비교 등 다시 꺼내 쓸 핵심 지식 요약.
   - **규칙**: 애매하면 `reports/`에 먼저 저장하고, 재사용할 핵심 지식만 `wiki/`로 요약한다. 그림과 상세 설명은 복제하지 않고 링크한다.
6. **검증 수준 명시**: 모든 중요한 답변과 코드 근거에는 검증 수준(`코드 확인 / 실행 확인 / 추론 / 미확인`)을 기록한다.

---

## 새 repo 분석 표준 흐름

1. **대상과 목적을 정합니다**
   - 레포 URL과 분석 목적(학습 / 설계 참고 / 도입 검토 등)을 확인한다.
   - 기존 `reports/`와 `wiki/`를 먼저 확인하여 중복 분석을 방지한다.
2. **코드 기준을 기록합니다**
   - `repos/<repo>/`에 clone 또는 update한다.
   - 원본 URL, commit SHA, 분석일, 작업트리 변경(clean/dirty) 여부를 기록한다 (`artifacts/<repo>/repo-metadata.txt` 및 `reports/<repo>/overview.md`).
3. **archify로 첫 지도를 만듭니다**
   - 주요 모듈 중심의 구조도와 대표 동작 하나의 실행 흐름을 생성한다.
   - 실제 코드로 관계를 확인하고 미확인 영역을 명시한다.
   - 산출물(JSON, HTML)은 `reports/<repo>/diagrams/`에 저장한다.
4. **그림을 보고 궁금한 부분을 질문합니다**
   - 사용자에게 그림을 읽는 순서와 함께 핵심 후속 질문 3~5개를 제안한다 (예: 모듈 분리 이유, 실패 처리, 확장 지점 등).
   - 필요 시 관련 상세 경로 추적 및 추가 다이어그램을 작성한다.
5. **답변을 저장하고 지식을 갱신합니다**
   - 질문별 답변 문서는 `reports/<repo>/questions/<question>.md`에 저장한다.
   - 기존 이해가 갱신되면 `overview.md`와 다이어그램을 수정한다.
   - 재사용 가치가 높은 지식은 `wiki/projects/<repo>.md`, `wiki/concepts/` 등에 반영한다.
6. **다음 시작점을 남깁니다**
   - 세션 마무리 시 `reports/<repo>/next.md`에 확인한 범위, 남은 질문, 다음에 볼 파일·함수, 분석 SHA를 갱신한다.
   - `wiki/index.md`와 `wiki/log.md`를 업데이트한다.

---

## CodeWiki (보조 분석기)

CodeWiki는 dependency graph 기반으로 레포 문서를 자동 생성하는 도구다. 결과는 **분석 후보(second opinion)**이므로 `artifacts/`에 두고, 코드로 검증한 내용만 `reports/`·`wiki/`로 옮긴다.

- 설치 위치: `repos/CodeWiki/.venv` (uv, Python 3.12, `uv pip install -e .`). 실행 파일: `repos/CodeWiki/.venv/bin/codewiki`
  - 시스템 Python(3.14)에는 설치하지 않는다. 네이티브 의존성(PythonMonkey 등) 호환 문제.
- 설정: `~/.codewiki/config.json` (전역). 현재 Claude Code 구독 모드, API 키 불필요 (`claude` CLI 로그인 필요).
  ```bash
  codewiki config set --provider claude-code \
    --main-model claude-sonnet-5-5 --cluster-model claude-sonnet-5-5
  codewiki config show
  ```
  - main model: 모듈별 페이지 작성 (긴 출력). cluster model: 컴포넌트를 모듈 트리로 묶음 (작은 JSON 출력).
  - `config set`은 넘긴 키만 바꾸므로 모델 변경 시 두 모델을 함께 지정한다.
  - `config validate`는 CLI 존재만 검사하고 모델명은 검증하지 않는다.
- 생성: 분석 대상 레포 디렉터리에서 실행한다 (대상 = 현재 작업 디렉터리). 기본 출력 `./docs`는 대상 레포를 오염시키므로 **반드시 `-o`로 `artifacts/<repo>/codewiki`를 지정**한다.
  ```bash
  cd repos/<repo>
  ../CodeWiki/.venv/bin/codewiki generate \
    -o ../../artifacts/<repo>/codewiki --github-pages \
    --instructions "모든 문서는 한국어로 작성하라. 코드 식별자, 파일 경로, 명령어, Mermaid 노드 ID는 원문 그대로 유지한다." \
    > ../../artifacts/<repo>/codewiki-generate.log 2>&1
  ```
  - 언어 옵션이 없으므로 한국어는 `--instructions`로 지정한다 (모듈명/파일명은 영어로 나올 수 있음).
  - 갱신: 같은 `-o` 경로로 `--update` (저장된 `temp/dependency_graphs/`와 비교).
  - 범위 조절: `--include`, `--exclude`, `--focus "src/core,src/api"`.
  - 세분화: `--max-depth`는 상한일 뿐이다. 모듈이 `--max-token-per-leaf-module`(기본 16000) 이상이어야 하위 모듈로 쪼개지므로 세분화는 이 값을 낮춘다. 같은 `-o`에 재실행하면 기존 `.md`를 건너뛰므로 새 폴더를 쓴다.
  - 결과 신뢰도(`reports/CodeWiki/questions/q1-output-quality.md`): 식별자·상수는 신뢰, 호출 주체·CLI 사용법은 코드로 재검증.
  - 실행 시간이 길고 구독 사용량을 소모하므로 백그라운드로 실행하고 로그를 남긴다. (CodeWiki 자체 기준 약 18분, CLI 표기 비용 약 $5.4)
  - Mermaid 검증은 다이어그램을 외부 서비스 `mermaid.ink`로 전송한다. 비공개 코드는 `MERMAID_VALIDATE=0`으로 끈다. 이 서비스의 503 응답도 로그에 "syntax errors"로 찍히므로 오류 로그만 보고 문법 오류로 판단하지 않는다.
- 출력: `overview.md`(시작점), 모듈별 `.md`, `module_tree.json`, `metadata.json`(모델·commit), `index.html`(`--github-pages`).
- 전체 옵션: `repos/CodeWiki/guides/cli-reference.md`, provider: `repos/CodeWiki/guides/providers.md`

## 작업 시 참고 파일

- 상세 절차 및 운영 가이드: `OSS_ANALYSIS_WORKFLOW.md`
- 분석 요청 및 문서 작성 템플릿: `templates/`
