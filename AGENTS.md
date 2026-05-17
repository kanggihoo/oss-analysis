# Project Context

이 디렉터리는 관심 있는 오픈소스 저장소를 하위 디렉터리에 clone한 뒤, Codex가 해당 오픈소스의 목적과 동작 구조를 빠르게 파악하도록 돕는 분석용 작업공간이다.

## 핵심 구성

- `.codex/skills/open-source-codebase-understanding/SKILL.md`: 처음 보는 오픈소스를 분석할 때 메인 에이전트가 따르는 workflow.
- `.codex/agents/codebase-mapper.toml`: 메인 에이전트가 범위별 코드 구조 분석을 맡길 때 사용하는 읽기 전용 subagent 설정.
- `.codex/config.toml`: subagent thread 수와 depth 같은 Codex agent 실행 설정.
- 하위 저장소 디렉터리: 실제 분석 대상 오픈소스가 clone되는 위치. 예: `rtk/`.

## 작업 목표

사용자가 분석 대상 오픈소스를 가져오면, 메인 에이전트는 먼저 전체 코드를 깊게 읽지 말고 루트 구조, README, 빌드/의존성 파일, 주요 디렉터리, entry point 후보만 빠르게 확인한다. 이후 프로젝트 유형과 규모에 따라 필요한 경우 `codebase_mapper` subagent를 범위별로 호출해 구조와 동작 흐름을 파악하고, 최종적으로 사용자가 이해하기 쉬운 한국어 설명으로 종합한다.

## 역할 분리

- 메인 에이전트는 프로젝트 유형 판단, 분석 범위 분할, subagent 호출 여부, 2차 follow-up 여부, 결과 통합, 최종 설명 작성을 담당한다.
- `codebase_mapper` subagent는 메인 에이전트가 지정한 범위만 읽고, 근거 파일/심볼을 포함해 해당 범위의 책임과 동작 단서를 요약한다.
- subagent는 추가 분석이 필요해 보여도 직접 범위를 넓히지 않고 `추가 확인 후보`로만 제안한다. 2차 분석 여부와 새 subagent 생성 여부는 메인 에이전트가 결정한다.

## 분석 원칙

- 이 작업공간의 목적은 코드 리뷰, 보안 감사, 리팩터링 제안이 아니라 오픈소스 동작 이해다.
- 분석 대상 저장소의 코드를 수정하지 않는다. 사용자가 명시적으로 요청한 경우에만 수정한다.
- 같은 범위의 추가 확인은 가능한 한 기존 subagent thread에 follow-up으로 보낸다. 같은 범위인데 subagent를 종료하고 새로 만들지 않는다.
- `.git`, `node_modules`, `dist`, `build`, `target`, `.next`, `coverage`, `vendor`, generated docs/code, vendored dependencies는 크기 판단과 범위 분할에서 기본적으로 제외한다.
- 불확실한 내용은 추측하지 말고 `확인 필요` 또는 `범위 내 단서 없음`으로 표시한다.

## 응답 스타일

- 한국어로 정확하고 명확하게 응답한다.
- 파일, 함수, 클래스, 설정 이름 등 실제 근거를 기반으로 설명한다.
- 최종 설명은 사용자가 처음 보는 프로젝트의 목적, 사용 방식, entry point, 주요 모듈, 흐름, 설정, 의존성, 테스트/실행 방식, 기여자가 먼저 읽을 파일을 파악할 수 있게 작성한다.
