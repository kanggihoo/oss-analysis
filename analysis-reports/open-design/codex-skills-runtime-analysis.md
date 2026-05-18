# Open Design의 Codex 연동과 Skills 전달 방식 분석

## 분석 범위

이 문서는 Open Design 프로젝트를 실제 코드 구현보다는 Markdown 문서와 로컬 런타임 디렉터리 관찰을 기준으로 정리한 것이다.

확인한 로컬 프로젝트 런타임 경로:

```text
C:\Users\SSAFY\AppData\Roaming\Open Design\namespaces\release-stable-win\data\projects\974b35da-4f30-4d9a-8839-3481ab7b7459
```

주요 참고 문서:

- `open-design/QUICKSTART.md`
- `open-design/README.ko.md`
- `open-design/docs/agent-adapters.md`
- `open-design/docs/skills-protocol.md`
- `open-design/docs/plugins-spec.md`

## 핵심 결론

Open Design 화면에서 말하는 "Skill trigger"는 Codex의 네이티브 `~/.codex/skills` 스킬 시스템과 동일한 개념이 아니다.

Open Design은 선택된 `SKILL.md`, `DESIGN.md`, 프로젝트 메타데이터, 필요 시 스킬 사이드 파일을 조합해서 Codex CLI에 전달한다. 전달 방식은 크게 두 가지다.

1. 에이전트가 지원하면 네이티브 skill 위치에 연결해서 읽게 한다.
2. 그렇지 않으면 `SKILL.md` 본문과 관련 문서를 프롬프트에 주입한다.

Codex는 버전과 실행 방식에 따라 Open Design의 skill을 네이티브로 인식하지 못할 수 있다. 이 경우 Codex 입장에서는 "skill이 트리거되었다"는 사실을 자체적으로 아는 것이 아니라, Open Design이 주입한 지침을 일반 프롬프트로 받는 구조다.

## 로컬 런타임 경로에서 확인한 내용

사용자가 제시한 프로젝트 경로의 루트에는 일반적인 `skills/` 디렉터리가 없었다.

대신 다음 경로가 존재했다.

```text
C:\Users\SSAFY\AppData\Roaming\Open Design\namespaces\release-stable-win\data\projects\974b35da-4f30-4d9a-8839-3481ab7b7459\.od-skills\agent-browser\SKILL.md
```

즉 현재 프로젝트에서는 Open Design이 `skills/`가 아니라 `.od-skills/` 아래에 필요한 skill 문서를 스테이징하고 있었다.

따라서 "프로젝트에 별도의 skills 디렉터리가 비어 있다"는 관찰 자체는 이상 현상이라기보다 Open Design의 런타임 저장 방식과 맞아 보인다.

## Open Design 문서상 Prompt Composition

`QUICKSTART.md`는 Open Design이 매 전송마다 다음 세 레이어로 시스템 프롬프트를 만든다고 설명한다.

```text
BASE_SYSTEM_PROMPT
   + active design system body  (DESIGN.md)
   + active skill body          (SKILL.md)
```

또한 Local CLI 모드에서는 별도 system channel이 없는 CLI도 있기 때문에, 조합된 프롬프트를 user message에 접어서 전달한다고 설명한다.

정리하면, 화면에서 `DESIGN.md`와 어떤 지침을 선택하거나 준다고 해서 Codex에 사용자 입력만 그대로 보내는 구조는 아니다. Open Design daemon이 선택된 디자인 시스템과 skill 본문을 합성한 뒤 Codex 실행에 전달한다.

## README.ko.md 기준 동작 모델

`README.ko.md`는 daemon이 프로젝트의 작업 디렉터리를 에이전트의 cwd로 설정해서 CLI를 spawn한다고 설명한다.

문서상 프롬프트 스택은 다음 요소를 포함한다.

- Discovery 지시문
- 공식 디자이너 프롬프트
- 활성 `DESIGN.md`
- 활성 `SKILL.md`
- 프로젝트 메타데이터
- skill 사이드 파일

그리고 daemon은 다음 흐름으로 에이전트를 실행한다.

```text
spawn(cli, [...], { cwd: .od/projects/<id> })
```

데스크톱 패키지에서는 이 `.od/projects/<id>`에 해당하는 위치가 AppData 아래의 프로젝트 경로로 보인다.

## Codex가 Skill을 인식하지 못하는 이유

`docs/agent-adapters.md`는 skill 전달 방식을 다음처럼 구분한다.

### Native skill loading

에이전트가 자기 `~/.<agent>/skills/` 위치를 스캔한다. 이 방식은 Claude Code, 일부 Codex 버전, OpenCode에서 가능하다고 되어 있다.

Codex는 문서상 "version-dependent"로 표시되어 있으므로 항상 보장되는 경로가 아니다.

### Prompt injection fallback

Open Design이 `SKILL.md` 본문과 `references/*.md`를 읽어서 시스템 프롬프트에 합치고, `assets/` 파일은 cwd로 복사한다.

문서에는 이 경우 "agent has no concept of skills but has the instructions"라는 취지로 설명되어 있다. 즉 에이전트는 skill이라는 개념을 모를 수 있지만, 그 지침 자체는 받는다.

따라서 Codex가 화면의 "triggered skill"을 네이티브 skill로 인식하지 못하는 것은 가능한 동작이다. 이때 Open Design의 역할은 Codex에 skill 본문을 프롬프트로 주입하거나 `.od-skills`에 파일로 제공하는 것이다.

## `.od-skills`의 의미

`docs/plugins-spec.md`에는 Open Design이 `SKILL.md`, `DESIGN.md`, craft, atoms를 프로젝트 cwd의 `.od-skills/` 안에 스테이징한다는 설명이 있다.

문서 예시는 다음과 같은 흐름을 보여준다.

```text
cd "$CWD"
claude code "Read .od-skills/ and produce the deliverables the active plugin describes."
```

즉 `.od-skills/`는 Codex의 네이티브 skill 설치 위치가 아니라, Open Design이 해당 프로젝트 실행에 필요한 디자인/스킬 문맥을 내려놓는 런타임 컨텍스트 폴더로 보는 것이 맞다.

## `DESIGN.md`는 어떻게 쓰이나

`docs/skills-protocol.md`는 모든 비 design-system skill이 활성 `DESIGN.md`를 사용할 수 있다고 설명한다.

주입 방식은 다음과 같다.

1. 시스템 프롬프트 prefix로 주입
2. cwd에 `DESIGN.md` 파일로 제공
3. skill 본문이 `{{ design_system }}` 같은 변수를 쓰면 템플릿 변수로 제공

따라서 UI에서 선택한 디자인 시스템은 단순한 화면 옵션이 아니라, 다음 에이전트 실행의 프롬프트와 파일 컨텍스트에 반영되는 지침이다.

## 현재 상황에 대한 해석

사용자가 본 상황은 다음처럼 해석된다.

- Open Design UI는 특정 skill이 선택되었거나 trigger되었다고 표시한다.
- 실제 Codex 실행 cwd는 AppData 아래 프로젝트 디렉터리다.
- 그 프로젝트 디렉터리에는 `skills/`가 없고 `.od-skills/agent-browser/SKILL.md`가 있다.
- Codex는 이 파일을 자동으로 네이티브 skill로 인식하지 않을 수 있다.
- Open Design이 Codex에 보내는 프롬프트 안에 skill 본문 또는 `.od-skills`를 읽으라는 지시가 포함되어야 Codex가 해당 skill 지침을 따른다.

즉 "Codex가 skill을 인식하지 못한다"는 현상은 Open Design의 UI 표현과 Codex의 네이티브 skill 시스템을 같은 것으로 기대했을 때 생기는 혼동이다.

## 확인하면 좋은 항목

문제가 실제로 발생하는지 확인하려면 다음을 보면 된다.

1. Open Design daemon 로그에서 Codex에 전달된 첫 프롬프트에 `Active skill`, `SKILL.md`, `.od-skills` 관련 내용이 있는지 확인한다.
2. Open Design 설정의 `CODEX_HOME`이 실제 Codex 홈인 `C:\Users\SSAFY\.codex`를 바라보는지 확인한다.
3. Codex 네이티브 skill로 쓰려는 것인지, Open Design의 prompt-injection skill로 쓰려는 것인지 구분한다.
4. Codex 세션 안에서 직접 `.od-skills/agent-browser/SKILL.md`를 읽으라는 지시를 주면 정상적으로 따르는지 확인한다.

## 실무적 결론

Open Design의 skill은 "Codex에 설치된 skill"이라기보다 "Open Design이 Codex 실행에 붙여 보내는 지침 묶음"에 가깝다.

따라서 Codex가 자동으로 skill trigger를 감지하기를 기대하면 안 된다. Codex가 그 지침을 따르게 하려면 Open Design이 프롬프트에 skill 본문을 넣거나, Codex가 `.od-skills/`를 읽도록 명시해야 한다.

현재 로컬 프로젝트에서 `.od-skills/agent-browser/SKILL.md`가 발견된 점은 Open Design이 최소한 일부 skill 컨텍스트를 프로젝트 cwd에 스테이징하고 있다는 근거다.
