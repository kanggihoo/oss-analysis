---
title: ponytail
created: 2026-06-21
updated: 2026-06-21
type: project
tags: [open-source, project, architecture, agent-framework, developer-tools, tooling, mcp, testing, ci-cd, evidence, judgment]
sources:
  - deepwiki-ko/ponytail/1-overview.md
  - deepwiki-ko/ponytail/1.1-the-ponytail-philosophy.md
  - deepwiki-ko/ponytail/1.2-agent-portability-and-supported-hosts.md
  - artifacts/ponytail/deepwiki/pages-md/1-overview.md
  - artifacts/ponytail/deepwiki/pages-md/1.1-the-ponytail-philosophy.md
  - artifacts/ponytail/deepwiki/pages-md/1.2-agent-portability-and-supported-hosts.md
  - reports/ponytail/initial-capture.md
  - repos/ponytail/AGENTS.md
  - repos/ponytail/README.md
  - repos/ponytail/docs/agent-portability.md
  - repos/ponytail/skills/ponytail/SKILL.md
  - repos/ponytail/hooks/ponytail-instructions.js
  - repos/ponytail/hooks/ponytail-runtime.js
  - repos/ponytail/pi-extension/index.js
  - repos/ponytail/.opencode/plugins/ponytail.mjs
  - repos/ponytail/ponytail-mcp/index.js
confidence: high
---

# ponytail

`ponytail`은 AI 코딩 에이전트에 “lazy senior developer” 모드를 주입하는 규칙/스킬/어댑터 모음이다. DeepWiki 번역본 `deepwiki-ko/ponytail/1-overview.md`, `1.1-the-ponytail-philosophy.md`, `1.2-agent-portability-and-supported-hosts.md`를 baseline으로 읽고, 현재 checkout `repos/ponytail`의 source at `6da37bfa7d0282522c7785759f4d2f1544015354`에서 핵심 구조를 확인했다.

## 한 줄 요약

Ponytail은 “덜 짜라”가 아니라 **필요한 최소 구현을 먼저 고르고, 안전/검증/접근성 같은 경계는 줄이지 않는** 에이전트용 설계 압력이다. 이 페이지는 [[deepwiki-first-baseline]]에서 시작했지만, durable claim은 source path로 검증했다는 점에서 [[evidence-backed-analysis]] 사례다.

## 핵심 철학: 사다리

핵심 규칙은 `AGENTS.md`와 `skills/ponytail/SKILL.md`에 반복된다. 코드를 쓰기 전에 다음 순서에서 요구사항을 만족하는 첫 번째 rung에 멈춘다.

```text
YAGNI → stdlib → native platform → installed dependency → one line → minimum custom code
```

Source verification:

- `repos/ponytail/AGENTS.md:5-12`는 여섯 단계 사다리를 압축 규칙으로 둔다.
- `repos/ponytail/skills/ponytail/SKILL.md:29-41`은 같은 사다리를 “reflex, not a research project”로 정의한다.
- `repos/ponytail/skills/ponytail/SKILL.md:64-75`는 `lite`, `full`, `ultra` 강도 차이를 정의하고, 기본은 `full`이다.

## 안전 경계

Ponytail의 “lazy”는 방임이 아니다. `repos/ponytail/AGENTS.md:24`와 `repos/ponytail/skills/ponytail/SKILL.md:77-93` 기준으로 다음은 줄이면 안 된다.

- trust boundary의 input validation
- data-loss를 막는 error handling
- security, accessibility
- 실제 하드웨어 calibration knob
- non-trivial logic의 최소 runnable check 하나
- 사용자가 명시적으로 요청한 full version

의도적 단순화는 `ponytail:` 주석으로 표시하고, shortcut에 ceiling이 있으면 upgrade path를 적는다. 이 규칙은 `repos/ponytail/AGENTS.md:22`와 `repos/ponytail/skills/ponytail/SKILL.md:51`에서 확인된다.

## 배포 구조: core rules + thin adapters

Ponytail의 architecture taste는 “한 규칙 소스, 여러 얇은 adapter”다. `repos/ponytail/docs/agent-portability.md:3-5`는 core behavior가 `skills/`에 있고 host-specific 파일은 load를 쉽게 하는 adapter라고 설명한다. `repos/ponytail/docs/agent-portability.md:27-31`은 adapter가 logic을 복제하지 말고 `skills/`와 `hooks/`를 가리키거나 `AGENTS.md`와 정렬된 복사본을 유지해야 한다고 못박는다.

주요 source-verified surface:

| Surface | 현재 소스 기준 역할 |
|---|---|
| `AGENTS.md` | skill 없는 agent용 compact always-on 규칙 (`repos/ponytail/docs/agent-portability.md:41`) |
| `skills/ponytail/SKILL.md` | lazy senior dev mode의 정식 규칙 (`repos/ponytail/docs/agent-portability.md:35`) |
| `.claude-plugin/plugin.json` | Claude plugin manifest; shared `hooks/claude-codex-hooks.json`를 가리킴 (`repos/ponytail/.claude-plugin/plugin.json:1-10`) |
| `.codex-plugin/plugin.json` | Codex plugin manifest; `skills`와 shared hooks를 노출 (`repos/ponytail/.codex-plugin/plugin.json:13-21`) |
| `gemini-extension.json` | Gemini extension이 `AGENTS.md`를 context file로 사용 (`repos/ponytail/gemini-extension.json:1-6`) |
| `.opencode/plugins/ponytail.mjs` | OpenCode system prompt transform으로 mode별 ruleset을 매 turn inject (`repos/ponytail/.opencode/plugins/ponytail.mjs:50-78`) |
| `pi-extension/index.js` | Pi command registration, mode persistence, `before_agent_start` prompt injection (`repos/ponytail/pi-extension/index.js:82-156`) |
| `ponytail-mcp/index.js` | MCP prompt와 `ponytail_instructions` read-only tool 제공 (`repos/ponytail/ponytail-mcp/index.js:19-48`) |

## Runtime mechanics

공유 instruction builder는 `repos/ponytail/hooks/ponytail-instructions.js:71-85`에서 `skills/ponytail/SKILL.md`를 읽고 mode별로 일부 table/example row를 필터링한다. 읽기에 실패하면 fallback instructions를 생성한다.

Mode state는 host별로 저장 위치가 달라진다. `repos/ponytail/hooks/ponytail-runtime.js:5-18`은 Claude 기본 config dir, Codex `PLUGIN_DATA`, Copilot `COPILOT_PLUGIN_DATA` 중 하나에 `.ponytail-active`를 쓴다. OpenCode는 자체 flag convention이 없어서 `.opencode/plugins/ponytail.mjs:23-28` 기준 `~/.config/opencode/.ponytail-active`를 사용한다.

## Test/CI surface

초기 capture에서 `npm test`를 실제 실행했고, pandas가 포함된 임시 venv를 `PATH`에 둔 후 root tests 56개와 `pi-extension` tests 12개가 모두 통과했다. 로그는 `artifacts/ponytail/static-analysis/npm-test.log`에 있다. CI도 Node 22, Python 3.12, pandas 설치, rule-copy check, `npm test`를 실행한다 (`repos/ponytail/.github/workflows/test.yml:14-29`, `reports/ponytail/initial-capture.md:90-99`).

## DeepWiki baseline에서 current source로 확정한 내용

- DeepWiki 번역본의 “Ponytail 철학”은 현재 `AGENTS.md`와 `skills/ponytail/SKILL.md`의 ladder/safety boundary와 대체로 일치한다.
- DeepWiki 번역본의 “Agent portability” 설명은 `docs/agent-portability.md`의 adapter table과 일치하며, 실제 manifest/plugin entrypoints도 존재한다.
- 다만 README의 benchmark 수치(예: LOC/비용 감소)는 현재 이 페이지에서 architecture fact로만 참조하지 않았다. 벤치마크 methodology는 `benchmarks/` 별도 검증 후 Taste Note나 comparison으로 승격하는 것이 안전하다.

## Taste Notes

### Responsibility Boundaries

- Core behavior: `skills/ponytail/SKILL.md`와 compact `AGENTS.md`.
- Shared prompt construction: `hooks/ponytail-instructions.js`.
- Host-specific activation/persistence: plugin manifests, hook runtime, OpenCode/Pi adapters.
- Optional context surface: `ponytail-mcp/`.

### Architecture Decision Taste

1. **Thin adapter rule** — host별 파일이 core rules를 복제하지 않고 참조한다. 대안은 adapter마다 규칙을 따로 유지하는 것이지만 drift 위험이 크다. Evidence: `docs/agent-portability.md:27-31`.
2. **Natural-language product as source-controlled artifact** — “철학”이 README prose에만 있지 않고 `SKILL.md`, `AGENTS.md`, rule files, tests로 배포된다. Trade-off는 문서/규칙 복사본 sync가 지속 관리 대상이 된다는 점이다.
3. **Mode persistence as simple file state** — host별 plugin data/config 위치에 `.ponytail-active`를 저장한다. 작고 이식성이 좋지만 same-turn switching 같은 세밀한 semantics는 adapter별 한계가 있다.
4. **Safety boundary inside minimalism rule** — minimal code pressure가 validation/security/accessibility를 침식하지 못하게 같은 rule source에서 명시한다. 이는 [[open-source-analysis-judgment-model]]의 좋은 “decision taste” 후보다.

### Trade-offs / Risks

- 여러 host를 지원하는 만큼 adapter drift와 copied rule drift가 핵심 유지보수 리스크다.
- benchmark 숫자는 설득력 있는 마케팅/검증 자료지만, durable wiki fact로 쓰려면 `benchmarks/` harness와 결과 파일을 별도 source verification해야 한다.
- instruction-tier host(Cursor/Copilot editor 등)는 hooks/mode switching 없이 rules만 적용하므로 full plugin host와 user experience가 다르다.

## 관련 페이지

- [[deepwiki-first-baseline]]
- [[evidence-backed-analysis]]
- [[workspace-boundaries]]
- [[open-source-analysis-judgment-model]]
