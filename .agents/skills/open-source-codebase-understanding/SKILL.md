---
name: open-source-codebase-understanding
description: Use when the user wants to understand an unfamiliar open-source project's purpose, structure, runtime behavior, setup, and contribution entry points.
---

# Open Source Codebase Understanding

Use this skill to coordinate a fast, bounded understanding pass over an unfamiliar open-source project. The goal is not code review. Do not focus on vulnerabilities, refactoring ideas, style, or optimization unless the user explicitly asks.

## Main Agent Workflow

1. Do not read the whole codebase up front.
2. First inspect only structure and metadata:
   - top-level files and directories
   - README and docs index
   - package/build/dependency files
   - extension counts, excluding generated/vendor/build output paths
   - important directory file counts, excluding generated/vendor/build output paths
   - tests, examples, docs, config directories
   - likely execution entry points
3. Exclude these paths from size and range decisions unless the project clearly treats one as source: `.git`, `node_modules`, `dist`, `build`, `target`, `.next`, `coverage`, `vendor`, generated docs, generated code, lockfile caches, and vendored dependencies.
4. Tentatively classify project type before range splitting: library, CLI, application, framework, plugin, infrastructure/tooling, monorepo, or mixed.
5. Classify project size from source-relevant files and responsibility-bearing directories:
   - small: about 50 files or fewer, or 2-3 main directories
   - medium: about 50-300 files, or 3-6 main directories
   - large: more than about 300 files, or more than 6 main modules/packages
6. Split the first pass into broad responsibility areas. For very small projects, analyze directly or use 1 subagent. For small projects, use 0-2 subagents. For medium or large projects, use 3-4 subagents.
7. Keep at least 1-2 thread slots available when possible. Do not use every available thread in the first pass unless the project clearly needs it.
8. Assign each range to `codebase_mapper` with a concrete path range and concrete questions.
9. After subagents return, synthesize a draft and identify gaps, conflicts, "범위 내 단서 없음", and "확인 필요" items.
10. Before closing any subagent thread, run a lifecycle check:
   - Are there unresolved gaps, conflicts, "범위 내 단서 없음", or "확인 필요" items inside that subagent's original range?
   - Did the final report already incorporate every follow-up answer needed from that range?
   - Would closing this thread force a new subagent to re-read the same range if the user asks one more question?
11. If any lifecycle-check answer shows more work inside the same range, do not close that subagent. Send a focused follow-up to the same thread first.
12. The main agent decides whether a second-pass subagent follow-up is needed. Subagents may suggest "추가 확인 후보", but they do not decide whether to continue analysis, widen scope, spawn another subagent, or stop.
13. For missing or conflicting details inside an existing range, reuse the same subagent thread with a focused follow-up. Do not close and recreate a subagent for the same range because that loses context and pays the system/developer prompt cost again.
14. Spawn a new subagent only when the missing point belongs to a different range, the original thread is closed/unavailable, genuinely parallel extra work is needed, or the prior result is so incomplete that re-analysis is cheaper and clearer than follow-up.
15. Normally stop after one broad pass and one narrow follow-up pass. Use a third pass only for essential unclear runtime flow, config loading, build/test behavior, contradictory subagent findings, or user-requested deeper resolution.
16. Unless the user asks otherwise, write one final report outside the cloned target repository at `analysis-reports/<target-repo-name>/overview.md`.
17. Close subagents only after the final report is written, the lifecycle check passes, and no same-range follow-up is pending. Do not close subagents just to "clean up" immediately after receiving their first result.

## First-Pass Range Patterns

Use these patterns as applicable:

- execution and usage entry points: CLI, server bootstrap, app startup, route registration, plugin loading
- core logic: src/core, lib, engine, runtime, compiler, parser, service, domain modules
- setup and dependency structure: package/build files, config loading, environment handling, dependency injection
- external interfaces: API, CLI commands, UI, SDK, adapters, storage, network integrations
- tests/examples/docs: expected behavior, real usage, setup commands, contribution clues

## Subagent Prompt Template

```text
너는 codebase_mapper subagent다.

분석 범위:
<paths or modules>

확인할 질문:
<specific questions>

목표:
지정된 범위만 빠르게 분석해서, 이 범위가 전체 오픈소스 동작에서 어떤 역할을 하는지 설명해라.

규칙:
- 지정된 범위 밖으로 과도하게 확장하지 마라.
- 전체 코드를 읽으려 하지 마라.
- 취약점, 리팩터링, 스타일 개선 리뷰를 하지 마라.
- 실제 파일, 함수, 클래스, 설정 이름을 근거로 설명해라.
- 추측이 필요한 부분은 "추정" 또는 "확인 필요"로 표시해라.
- 범위 안에서 근거가 없는 항목은 추측하지 말고 "범위 내 단서 없음"이라고 적어라.
- 중요한 주장에는 가능한 한 "근거 파일/심볼"을 함께 적어라.
- 추가 분석이 필요해 보이면 직접 범위를 넓히지 말고 "추가 확인 후보"로만 제안해라. 2차 분석 여부는 메인 에이전트가 결정한다.
- codebase_mapper developer_instructions의 출력 형식을 따르되, 기본적으로 아래 출력 형식을 지켜라.

출력 형식:
분석 범위:
근거 파일/심볼:
이 범위의 목적:
프로젝트 유형/사용 방식과 관련된 단서:
핵심 기능:
실행/사용 진입점:
주요 파일과 책임:
핵심 개념과 용어:
입력/데이터/상태/제어 흐름:
설정 및 환경 구성:
의존성:
빌드/실행/테스트 관련 단서:
에러 처리와 디버깅 포인트:
확장/기여 시 봐야 할 구조:
처음 읽어야 할 파일:
다른 범위와 연결되는 지점:
추가 확인 후보:
확인 필요:
```

## Follow-Up Rule

The main agent owns the decision to run a second pass. When a result is incomplete, ask the same subagent thread if the question is still inside its original range:

```text
이전 분석 범위 안에서 추가 확인해줘.
<specific missing point>
전체를 다시 읽지 말고 관련 파일/심볼만 좁혀서 확인해라.
```

Use a new `codebase_mapper` only when the missing point belongs to a different range, the original thread is closed/unavailable, genuinely parallel extra work is needed, or the prior result is too incomplete for a focused follow-up.

## Subagent Lifecycle Rule

Keep subagent threads open while they may still answer same-range follow-up questions. Closing a thread is a finalization step, not a routine cleanup step.

Close a subagent only when all are true:
- its assigned range has no unresolved "확인 필요", conflict, or missing detail that needs more analysis
- any uncertainty from that range is either resolved or explicitly accepted as out-of-scope
- the final report already includes the relevant result
- the user has not asked for deeper same-range exploration

Do not close a subagent when:
- the report still says "추가 확인 필요" for that subagent's range
- you plan to ask a narrower question in the same files/modules
- the user is likely to ask for deeper follow-up on the same uncertainty
- you are closing only because the first pass returned successfully

Common failure this prevents: receiving a broad result, writing a report with unresolved questions, closing the subagent, then needing to spawn a new agent for the same range. That loses context and violates the follow-up rule.

## Report Storage

Unless the user asks otherwise, the main agent writes one final report to:

```text
analysis-reports/<target-repo-name>/overview.md
```

Do not write analysis reports into the cloned target repository unless the user explicitly requests it.

Subagents must not write report files. They return structured findings only. The main agent owns all report writing.

## Final Output

The final explanation must use these sections:

1. 이 프로젝트의 목적
2. 프로젝트 유형과 사용 방식
3. 핵심 기능
4. 실행/사용 진입점
5. 주요 모듈과 책임
6. 핵심 개념과 용어
7. 입력/데이터/상태/제어 흐름
8. 설정 및 환경 구성
9. 의존성 구조
10. 빌드/실행/테스트 방식
11. 에러 처리와 디버깅 포인트
12. 확장하거나 기여할 때 봐야 할 구조
13. 처음 기여자가 먼저 읽어야 할 파일
14. 아직 불확실하거나 추가 확인이 필요한 부분
