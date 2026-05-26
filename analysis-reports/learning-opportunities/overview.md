# learning-opportunities 분석 보고서

## 1. 이 프로젝트의 목적

`learning-opportunities`는 AI 코딩 도구가 코드를 생성하고 끝내는 흐름을 보완하기 위해, 사용자가 구현 결과에서 실제로 배울 수 있도록 짧은 학습 연습을 제안하는 스킬/플러그인 마켓플레이스다. 핵심 문제의식은 빠른 AI 생성 코드가 사용자의 능동적 생성, 예측, 회상, 메타인지 기회를 줄일 수 있다는 점이다.

근거:
- `README.md`: "Build your expertise, not just your projects."
- `learning-opportunities/skills/learning-opportunities/SKILL.md`: AI productivity trap을 끊고 진짜 전문성을 쌓도록 돕는다고 설명한다.
- `learning-opportunities/skills/learning-opportunities/resources/PRINCIPLES.md`: generation effect, testing, spacing, fluency illusion, metacognition을 학습 원리로 정리한다.

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 일반 애플리케이션이나 라이브러리가 아니라, Claude Code 및 Codex용 플러그인 마켓플레이스다. 루트의 marketplace 파일이 세 개의 설치 가능한 플러그인을 노출한다.

- `learning-opportunities`: 핵심 학습 연습 스킬
- `learning-opportunities-auto`: 커밋 이후 학습 제안을 자동으로 유도하는 hook 플러그인
- `orient`: 새 저장소를 학습하기 위한 `orientation.md` 생성 스킬

Codex 설치는 `codex plugin marketplace add https://github.com/DrCatHicks/learning-opportunities.git` 또는 로컬 경로 추가 방식이다. Claude Code 설치는 `/plugin marketplace add`, `/plugin install ...` 흐름을 따른다.

## 3. 핵심 기능

핵심 기능은 세 단계로 나뉜다.

1. 의미 있는 작업 이후 학습 연습 제안
   - 새 파일/모듈 생성, 스키마 변경, 아키텍처 결정, 리팩터링, 낯선 패턴 구현, 사용자의 "왜" 질문 이후에 10-15분짜리 선택형 학습 연습을 제안한다.

2. 사용자의 응답을 기다리는 상호작용형 학습
   - `SKILL.md`는 질문 후 즉시 멈추고, 예시 답변/힌트/연속 질문을 만들지 말라고 지시한다. 사용자가 먼저 예측하거나 설명하게 만든 뒤 피드백을 제공한다.

3. 저장소 오리엔테이션 학습
   - `orient` 스킬이 현재 프로젝트용 `orientation.md`를 만들고, `learning-opportunities orient`가 그 파일의 Suggested exercise sequence를 따라 새 코드베이스 이해 연습을 진행한다.

## 4. 실행/사용 진입점

주요 진입점은 코드 함수가 아니라 스킬 호출, 플러그인 manifest, hook 설정이다.

- 핵심 스킬: `learning-opportunities/skills/learning-opportunities/SKILL.md`
  - 명시 호출: `/learning-opportunities`
  - 인자 호출: `/learning-opportunities orient`
  - 트리거 설명: frontmatter `description`에 "completing features, making design decisions, or when user asks to understand code better"가 명시되어 있다.

- 오리엔테이션 스킬: `orient/skills/orient/SKILL.md`
  - 명시 호출: `/orient`
  - showboat 모드: `/orient showboat`
  - frontmatter에 "Invoke directly ... do not trigger automatically"가 있어 자동 트리거 대상이 아님을 밝힌다.

- 자동 hook: `learning-opportunities-auto/hooks.codex.json`, `learning-opportunities-auto/hooks/hooks.json`, `learning-opportunities-auto/hooks/post-tool-use.sh`
  - Codex: `PostToolUse` matcher가 `Bash|exec_command`
  - Claude Code: `PostToolUse` matcher가 `Bash`
  - hook script는 tool 입력 JSON에서 `"command"` 또는 `"cmd"` 필드에 `git commit`이 들어있는지 검사한다.

## 5. 주요 모듈과 책임

- `.agents/plugins/marketplace.json`
  - Codex marketplace 카탈로그다. 세 플러그인을 local path로 등록하고 category를 `Education`으로 둔다.

- `.claude-plugin/marketplace.json`
  - Claude Code marketplace 카탈로그다. 세 플러그인의 name, source, description, version, author, license, keywords, category를 정의한다.

- `learning-opportunities/.codex-plugin/plugin.json`
  - Codex용 핵심 스킬 플러그인 manifest다. `skills: "./skills/"`와 UI 표시 정보, default prompt를 포함한다.

- `learning-opportunities/.claude-plugin/plugin.json`
  - Claude Code용 핵심 플러그인 manifest다. 버전, 설명, 저자, 저장소, 라이선스 등 메타데이터 중심이다.

- `learning-opportunities/skills/learning-opportunities/SKILL.md`
  - 실제 학습 보조 behavior를 정의하는 핵심 파일이다.

- `learning-opportunities/skills/learning-opportunities/resources/PRINCIPLES.md`
  - SKILL.md의 교육학적 판단 근거다.

- `learning-opportunities/docs/MEASURE-THIS.md`
  - 팀 단위 실험으로 사용할 때 사전/사후 측정 방법을 제공한다.

- `learning-opportunities-auto/.codex-plugin/plugin.json`
  - Codex용 자동 hook 플러그인 manifest다. `hooks: "./hooks.codex.json"`가 핵심 연결점이다.

- `learning-opportunities-auto/hooks/post-tool-use.sh`
  - git commit 감지, session_id 기반 rate limit, 추가 context 출력 책임을 가진다.

- `orient/.codex-plugin/plugin.json`
  - Codex용 orient 플러그인 manifest다. `skills: "./skills/"`, capabilities `Read`, `Write`를 포함한다.

- `orient/skills/orient/SKILL.md`
  - 현재 repo를 훑어 `.codex/skills/learning-opportunities/resources/orientation.md` 또는 `.claude/skills/learning-opportunities/resources/orientation.md`를 생성하는 절차를 정의한다.

## 6. 핵심 개념과 용어

- Learning opportunity: 구현이 끝난 뒤 사용자가 설계 선택, 코드 흐름, 낯선 패턴을 이해하도록 만드는 짧은 학습 기회다.
- Pause point: 질문 직후 응답을 기다리는 강제 중단점이다. 스킬의 핵심 제약이다.
- Prediction -> Observation -> Reflection: 예측 후 실제 동작을 보고 차이를 성찰하는 연습 유형이다.
- Generation -> Comparison: 사용자가 먼저 설계/해법을 만들어 보고 실제 구현과 비교하는 연습이다.
- Retrieval check-in: 이전 세션에서 배운 내용을 다시 떠올리게 하는 회상 연습이다.
- Orientation mode: `learning-opportunities orient` 인자로 실행되는 특수 모드다.
- orientation.md: `orient`가 생성하고 `learning-opportunities`가 소비하는 repo-specific 학습 자료다.
- PostToolUse hook: shell command 실행 뒤 자동으로 `git commit` 여부를 보고 학습 제안 context를 주입하는 hook이다.

## 7. 입력/데이터/상태/제어 흐름

이 프로젝트의 런타임 흐름은 세 가지로 나뉜다. 핵심 스킬은 사용자의 동의를 받은 뒤 학습 연습을 진행하고, auto hook은 그 제안을 할 타이밍만 알려준다. `orient`는 별도 준비 단계로 `orientation.md`를 만든다.

### 한눈에 보는 구조

| 흐름 | 시작점 | 읽는 입력 | 생성/변경하는 것 | 최종 결과 |
|---|---|---|---|---|
| 핵심 학습 스킬 | `/learning-opportunities` 또는 agent의 상황 판단 | 최근 작업 맥락, 사용자 답변, 관련 코드 | 대화 내 학습 질문과 피드백 | 사용자가 코드/설계 선택을 직접 설명하고 비교함 |
| 자동 제안 hook | Bash/exec command 이후 `PostToolUse` | tool payload의 `command`/`cmd`, `session_id` | temp state file, `additionalContext` | agent에게 "학습 제안 고려" context 주입 |
| repo orientation | `/orient` | README, manifest, tree, entry point, tests, git history | `orientation.md` | `/learning-opportunities orient`에서 쓸 repo-specific 연습 생성 |
| orientation 연습 | `/learning-opportunities orient` | `orientation.md`의 Suggested exercise sequence | 대화 내 orientation 질문과 피드백 | 새 repo의 high-level mental model 형성 |

### 핵심 스킬 workflow

| 단계 | agent가 하는 일 | 사용자에게 보이는 형태 |
|---|---|---|
| 1. 트리거 감지 | 명시 호출 또는 기능 완료/설계 결정/리팩터링/코드 이해 질문을 학습 기회로 판단 | 아직 없음 |
| 2. 제안 가능 여부 확인 | 이미 거절했는지, 이미 2회 연습했는지, 작업이 충분히 의미 있는지 확인 | 아직 없음 |
| 3. 제안 | 연습을 바로 시작하지 않고 허락을 구함 | `Would you like to do a quick learning exercise on [topic]? About 10-15 minutes.` |
| 4. 수락 대기 | 사용자의 yes/no 응답을 기다림 | 사용자가 수락해야 진행 |
| 5. 연습 유형 선택 | 작업 성격에 맞는 연습을 고름 | 예측, 생성, trace, debug, teach-back, retrieval 중 하나 |
| 6. pause point | 질문 후 즉시 멈춤. 예시 답, 힌트, 추가 설명을 붙이지 않음 | `Your turn: ...` |
| 7. 답변 기반 피드백 | 사용자가 실제로 말한 내용만 근거로 피드백 | 맞은 점, 틀린 점, 실제 코드와의 차이 설명 |
| 8. 종료 또는 확장 | 10-15분 안에서 후속 질문을 하거나 종료 | 사용자가 더 할지 멈출지 선택 |

핵심 제약은 `pause point`다. 이 스킬은 AI가 설명을 먼저 제공하는 방식이 아니라, 사용자가 먼저 예측하거나 설명하게 만든 뒤 실제 코드와 비교한다.

### 연습 유형 선택 기준

| 연습 유형 | 적합한 상황 | 질문 형태 |
|---|---|---|
| `Prediction -> Observation -> Reflection` | 코드 실행 결과나 흐름을 이해해야 할 때 | "이 요청이 middleware에 들어오면 다음에 무엇이 일어날까요?" |
| `Generation -> Comparison` | 설계/구현 선택을 배워야 할 때 | "구현을 보기 전에 어떻게 나눌지 먼저 스케치해보세요." |
| `Trace the path` | 요청, 데이터, 상태 이동을 익혀야 할 때 | "이 값은 다음에 어느 함수로 넘어갈까요?" |
| `Debug this` | edge case나 실패 조건을 이해해야 할 때 | "이 순서를 유지하면 무엇이 깨질까요?" |
| `Teach it back` | 컴포넌트 이해도를 확인할 때 | "새 개발자에게 설명하듯 이 모듈을 설명해보세요." |
| `Retrieval check-in` | 이전 세션 내용을 다시 떠올릴 때 | "지난번에 이 컴포넌트가 이 상황을 어떻게 처리했는지 기억나나요?" |

### 자동 hook workflow

`learning-opportunities-auto`는 학습 연습을 직접 실행하지 않는다. `git commit` 직후 agent에게 "지금 학습 제안을 고려할 만한 시점"이라는 context만 넣는다.

| 단계 | 파일/설정 | 동작 |
|---|---|---|
| 1. hook 등록 | `learning-opportunities-auto/hooks.codex.json`, `hooks/hooks.json` | `PostToolUse`에 shell tool matcher 등록 |
| 2. script 실행 | `learning-opportunities-auto/hooks/post-tool-use.sh` | tool payload JSON을 표준 입력으로 읽음 |
| 3. commit 감지 | `post-tool-use.sh` | `"command"` 또는 `"cmd"`에 `git commit` 패턴이 없으면 종료 |
| 4. session 식별 | `post-tool-use.sh` | top-level `"session_id"`를 추출하지 못하면 종료 |
| 5. rate limit | temp file `${TMPDIR:-/tmp}/lo_auto_<session_id>.state` | 세션당 최대 2회까지만 제안 context 생성 |
| 6. context 주입 | `hookSpecificOutput.additionalContext` | "커밋된 작업이 의미 있으면 학습 연습을 제안하라"는 nudge 출력 |
| 7. 핵심 스킬로 연결 | agent 대화 상태 | agent가 사용자의 동의를 묻고, 수락 시 핵심 workflow 진행 |

자동 hook 흐름은 다음처럼 요약된다.

```text
shell command 완료
  -> PostToolUse hook 실행
  -> git commit 여부 검사
  -> session_id 추출
  -> 세션당 제안 횟수 확인
  -> additionalContext 주입
  -> agent가 학습 제안 여부 판단
```

### orientation workflow

`orient`는 학습 연습 자체가 아니라, 새 repo 학습을 위한 자료를 미리 만드는 스킬이다.

| 단계 | 호출/파일 | 동작 |
|---|---|---|
| 1. 생성 호출 | `/orient` | repo orientation 파일 생성을 시작 |
| 2. repo 조사 | `orient/skills/orient/SKILL.md` | README, docs, manifest, tree, entry point, tests, core modules, git history를 선택적으로 확인 |
| 3. 파일 작성 | `.codex/skills/learning-opportunities/resources/orientation.md` 또는 `.claude/skills/learning-opportunities/resources/orientation.md` | repo-specific orientation 자료와 정확히 2개의 exercise 작성 |
| 4. 연습 호출 | `/learning-opportunities orient` | 핵심 스킬이 `orientation.md`를 탐색 |
| 5. 없을 때 | `learning-opportunities/SKILL.md` | `No orientation file found...` 메시지로 중단 |
| 6. 있을 때 | `orientation.md` | Suggested exercise sequence를 따라 pause point 기반 연습 진행 |

orientation mode의 차이는 예측보다 이해와 종합에 초점을 둔다는 점이다. 사용자가 짧은 파일이나 섹션을 먼저 읽고, 그 내용을 자신의 말로 설명하도록 설계되어 있다.

### 전체 흐름 요약

```text
[일반 학습 연습]
작업 완료 또는 /learning-opportunities
  -> 제안 가능 여부 확인
  -> 짧은 학습 연습 제안
  -> 사용자 수락
  -> 연습 유형 선택
  -> 질문 후 hard stop
  -> 사용자 답변
  -> 실제 코드/동작과 비교 피드백
  -> 후속 질문 또는 종료
```

```text
[자동 제안]
git commit
  -> PostToolUse hook
  -> session_id/rate limit 확인
  -> additionalContext 주입
  -> agent가 일반 학습 연습 제안 흐름으로 진입
```

```text
[repo orientation]
/orient
  -> repo 조사
  -> orientation.md 생성
  -> /learning-opportunities orient
  -> orientation.md 기반 학습 연습
```

## 8. 설정 및 환경 구성

Codex 관련 설정:

- 루트 marketplace: `.agents/plugins/marketplace.json`
- 핵심 플러그인 manifest: `learning-opportunities/.codex-plugin/plugin.json`
- 자동 hook manifest: `learning-opportunities-auto/.codex-plugin/plugin.json`
- Codex hook config: `learning-opportunities-auto/hooks.codex.json`
- orient manifest: `orient/.codex-plugin/plugin.json`

Claude Code 관련 설정:

- 루트 marketplace: `.claude-plugin/marketplace.json`
- 각 플러그인의 `.claude-plugin/plugin.json`
- auto hook config: `learning-opportunities-auto/hooks/hooks.json`

Windows 관련 설정:

- `learning-opportunities-auto/README.md`는 native Windows에서 Claude Code hook이 bash script를 바로 실행하지 못할 수 있으므로 `CLAUDE_CODE_GIT_BASH_PATH` 설정을 안내한다.
- Codex 쪽은 `hooks.codex.json`이 동일한 script를 상대 경로 `bash ./hooks/post-tool-use.sh`로 실행하도록 구성되어 있다.

## 9. 의존성 구조

일반적인 package manager 의존성 파일은 없다. `package.json`, `pyproject.toml`, `Cargo.toml` 같은 빌드 manifest가 없다.

실질 의존성:

- 플러그인 런타임: Claude Code plugin marketplace, Codex plugin marketplace
- hook 실행 환경: Bash
- hook script 내부 도구: `grep`, `sed`, `head`, `cat`
- orient showboat 모드 선택 시: `uv`, `uvx showboat`

`learning-opportunities-auto`는 기능적으로 `learning-opportunities` 플러그인이 설치되어 있어야 의미가 있다. README와 manifest 설명 모두 "Requires the learning-opportunities plugin"이라고 명시한다.

## 10. 빌드/실행/테스트 방식

빌드 단계는 없다. 저장소는 문서와 plugin/skill 설정 파일 묶음이다.

실행 방식:

- Codex marketplace 추가 후 플러그인 설치
- Claude Code marketplace 추가 후 `/plugin install`
- 수동 스킬 호출: `/learning-opportunities`, `/learning-opportunities orient`, `/orient`
- 자동 hook: shell command 이후 `PostToolUse`에서 `git commit` 감지

테스트 관련:

- 별도 test suite나 CI 설정은 범위 내에서 확인되지 않았다.
- hook script는 입력 JSON이 들어왔을 때 패턴 매칭과 temp file 기반 상태 추적을 수행하지만, 이에 대한 자동 테스트 파일은 없다.

## 11. 에러 처리와 디버깅 포인트

- `learning-opportunities` orientation mode는 `orientation.md`가 없으면 "No orientation file found. Invoke the orient skill first..." 메시지로 중단하도록 되어 있다.
- `post-tool-use.sh`는 `git commit` 패턴이 없거나 `session_id`가 없으면 조용히 `exit 0` 한다.
- 자동 제안은 `session_id`별 temp state file로 최대 2회까지 제한한다.
- hook command 매칭은 regex `"command|cmd".*git.*commit`라서, 주석에도 적힌 것처럼 "git commit"이라는 문자열이 포함된 false positive가 가능하다. script는 이를 harmless로 간주한다.
- Windows Claude Code 환경에서는 bash 실행 경로가 핵심 디버깅 포인트다. `CLAUDE_CODE_GIT_BASH_PATH` 또는 PATH에 Git Bash가 없으면 auto hook이 동작하지 않을 수 있다.
- `CHANGELOG.md`에 따르면 Claude Code는 inline `plugin.json` hook이 아니라 `hooks/hooks.json`을 runtime에 읽는 형식으로 수정된 이력이 있다.

## 12. 확장하거나 기여할 때 봐야 할 구조

- 새 학습 연습 유형 추가: `learning-opportunities/skills/learning-opportunities/SKILL.md`의 Exercise types와 Facilitation guidelines를 수정한다.
- 학습 원리 보강: `resources/PRINCIPLES.md`에 근거를 추가하고, SKILL.md에서 해당 원리를 참조한다.
- 자동 트리거 조건 변경: `learning-opportunities-auto/hooks/post-tool-use.sh`의 git commit 감지 조건과 rate limit 로직을 수정한다.
- Codex hook 연결 변경: `learning-opportunities-auto/hooks.codex.json`
- Claude Code hook 연결 변경: `learning-opportunities-auto/hooks/hooks.json`
- plugin 버전 릴리스: `CLAUDE.md`에 따라 해당 plugin의 `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, 루트 `.claude-plugin/marketplace.json`, `CHANGELOG.md`를 함께 업데이트한다.
- orient 생성 형식 변경: `orient/skills/orient/SKILL.md`의 Step 4 template를 수정한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README.md`
   - 프로젝트 목적, 설치 방식, 세 플러그인의 관계를 먼저 파악할 수 있다.

2. `CLAUDE.md`
   - 저장소 구조와 릴리스 절차가 가장 짧게 정리되어 있다.

3. `learning-opportunities/skills/learning-opportunities/SKILL.md`
   - 핵심 동작, 트리거 조건, 연습 유형, pause 원칙, orientation mode가 들어 있다.

4. `learning-opportunities-auto/README.md`
   - 자동 prompting이 왜 별도 플러그인인지, hook이 언제 실행되는지 이해할 수 있다.

5. `learning-opportunities-auto/hooks/post-tool-use.sh`
   - 실제 자동 트리거 로직이 있는 유일한 script다.

6. `orient/skills/orient/SKILL.md`
   - repo orientation 파일 생성 방식과 `learning-opportunities orient`와의 연결을 이해할 수 있다.

7. `.agents/plugins/marketplace.json`, `.claude-plugin/marketplace.json`
   - marketplace가 어떤 플러그인을 어떤 경로에서 노출하는지 확인할 수 있다.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- Claude Code의 `.claude-plugin/plugin.json`에는 Codex manifest와 달리 `skills` 필드가 없다. 이 저장소 범위만으로는 Claude Code가 어떤 convention으로 `skills/`를 로드하는지 완전히 확인할 수 없다.
- `learning-opportunities-auto` hook의 "declined exercise this session" 상태는 script 자체에는 저장되지 않는다. script는 제안 횟수만 추적하고, decline 처리는 hook이 주입한 additional context와 agent의 대화 상태에 맡기는 구조로 보인다.
- README는 "After a successful commit"이라고 설명하지만 script 자체는 입력 payload에서 command string만 보고 성공 여부를 직접 검사하지 않는다. 실제 hook runtime이 성공한 tool use 이후에만 PostToolUse를 실행하는지에 의존하는 것으로 보인다.
- 저장소 안에는 자동 테스트가 없어, hook payload 형식 변화나 Windows bash 경로 문제는 수동 검증이 필요하다.
