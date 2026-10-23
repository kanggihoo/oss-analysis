# Index

> Last updated: 2026-10-23
> 레포에 관한 분석은 모두 `reports/<repo>/`에 있다. 형식은 [SCHEMA.md](SCHEMA.md), 절차는 [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md).

## 분석한 레포

| 레포 | 기준 SHA | 입구 | 기능 스펙 |
|---|---|---|---|
| ai-job-search | `e16acee` | [overview](reports/ai-job-search/overview.md) | — |
| claude-code-history-viewer | `9d86b46` | [overview](reports/claude-code-history-viewer/overview.md) | — |
| claude-devtools | `1486f20` | [overview](reports/claude-devtools/overview.md) | [claude-code-session-log-reading](reports/claude-devtools/capabilities/claude-code-session-log-reading.md) (draft), [claude-code-session-picker](reports/claude-devtools/capabilities/claude-code-session-picker.md) (draft) |
| agent-skills | `aeac41d` | [overview](reports/agent-skills/overview.md) | — |
| cc-switch | `d35726e` | [overview](reports/cc-switch/overview.md) | — |
| codeburn | `9a40cc6` | [overview](reports/codeburn/overview.md) | — |
| codenotch | `414ceaf` | [overview](reports/codenotch/overview.md) | — |
| context-mode | `f8d4639` | [overview](reports/context-mode/overview.md) | — |
| defuddle | `556d74e` | [overview](reports/defuddle/overview.md) | — |
| Graft | `f9e6539` | [overview](reports/Graft/overview.md) | — |
| gpt-researcher | `3582a68` | [overview](reports/gpt-researcher/overview.md) | [research-pipeline](reports/gpt-researcher/capabilities/research-pipeline.md) (ready), [source-modes](reports/gpt-researcher/capabilities/source-modes.md) (ready), [retrievers](reports/gpt-researcher/capabilities/retrievers.md) (draft), [scrapers](reports/gpt-researcher/capabilities/scrapers.md) (draft), [context-selection](reports/gpt-researcher/capabilities/context-selection.md) (draft), [report-writing](reports/gpt-researcher/capabilities/report-writing.md) (ready), [detailed-report](reports/gpt-researcher/capabilities/detailed-report.md) (ready), [deep-research](reports/gpt-researcher/capabilities/deep-research.md) (draft), [mcp-client](reports/gpt-researcher/capabilities/mcp-client.md) (ready) |
| hyperframes | `b7fa007` | [overview](reports/hyperframes/overview.md) | — |
| mitmproxy | `7735597` | [overview](reports/mitmproxy/overview.md) | — |
| pi | `4259686`, `ai`·`agent` 패키지는 `3874b3e` | [overview](reports/pi/overview.md) | — |
| rea | `60c0880` | [overview](reports/rea/overview.md) | — |
| Scrapling | `7a68493` | [overview](reports/Scrapling/overview.md) | — |
| searxng | `0ce72dd` | [overview](reports/searxng/overview.md) | — |
| skills-manager | `e6dcedf` | [overview](reports/skills-manager/overview.md) | — |
| teamai-cli | `7ba8bcc` | [overview](reports/teamai-cli/overview.md) | — |
| Understand-Anything | `b05cc3b` | [overview](reports/Understand-Anything/overview.md) | — |
| herdr-bar (herdr-plugin/) | `261de9b` | [overview](herdr-plugin/reports/herdr-bar/overview.md) | — |
| herdr-projects (herdr-plugin/) | `8258d96` | [overview](herdr-plugin/reports/herdr-projects/overview.md) | — |
| herdr-nvim (herdr-plugin/) | `3ca8671` | [overview](herdr-plugin/reports/herdr-nvim/overview.md) | — |
| herdr-auto-title (herdr-plugin/) | `69d7182` | [overview](herdr-plugin/reports/herdr-auto-title/overview.md) | — |
| dspy (prompt-eval/) | `3fdb93f` | [overview](prompt-eval/reports/dspy/overview.md) | — (범위 제외) |
| promptfoo (prompt-eval/) | `dfe2d45` | [overview](prompt-eval/reports/promptfoo/overview.md), [next](prompt-eval/reports/promptfoo/next.md) | [provider-contract](prompt-eval/reports/promptfoo/capabilities/provider-contract.md), [skill-calls-metadata](prompt-eval/reports/promptfoo/capabilities/skill-calls-metadata.md), [eval-records](prompt-eval/reports/promptfoo/capabilities/eval-records.md), [default-providers](prompt-eval/reports/promptfoo/capabilities/default-providers.md), [config-loading](prompt-eval/reports/promptfoo/capabilities/config-loading.md), [assertion-family](prompt-eval/reports/promptfoo/capabilities/assertion-family.md), [model-graded-matchers](prompt-eval/reports/promptfoo/capabilities/model-graded-matchers.md), [agent-providers](prompt-eval/reports/promptfoo/capabilities/agent-providers.md), [response-cache](prompt-eval/reports/promptfoo/capabilities/response-cache.md), [script-bridges](prompt-eval/reports/promptfoo/capabilities/script-bridges.md), [generate-datasets](prompt-eval/reports/promptfoo/capabilities/generate-datasets.md), [eval-run](prompt-eval/reports/promptfoo/capabilities/eval-run.md), [results-store](prompt-eval/reports/promptfoo/capabilities/results-store.md), [prompt-optimize](prompt-eval/reports/promptfoo/capabilities/prompt-optimize.md), [web-ui](prompt-eval/reports/promptfoo/capabilities/web-ui.md) (모두 ready) |
| prompt-optimizer (prompt-eval/) | `a201f47` | [overview](prompt-eval/reports/prompt-optimizer/overview.md), [next](prompt-eval/reports/prompt-optimizer/next.md) | [template-rendering](prompt-eval/reports/prompt-optimizer/capabilities/template-rendering.md), [history-chain](prompt-eval/reports/prompt-optimizer/capabilities/history-chain.md), [prompt-optimize](prompt-eval/reports/prompt-optimizer/capabilities/prompt-optimize.md), [llm-evaluation](prompt-eval/reports/prompt-optimizer/capabilities/llm-evaluation.md), [iterate-rewrite](prompt-eval/reports/prompt-optimizer/capabilities/iterate-rewrite.md), [calibration-script](prompt-eval/reports/prompt-optimizer/capabilities/calibration-script.md) (모두 ready) |
| gbrain | `63f62b2` | [overview](reports/gbrain/overview.md) | — (범위 승인 대기) |

## 첫 수집만 한 레포 (overview 없음)

| 레포 | 기준 SHA | 입구 |
|---|---|---|
| Agent-Reach | — | [initial-capture](reports/Agent-Reach/initial-capture.md) |
| agent-browser | — | [initial-capture](reports/agent-browser/initial-capture.md) |
| insane-search | — | [initial-capture](reports/insane-search/initial-capture.md) |
| obsidian-clipper | — | [initial-capture](reports/obsidian-clipper/initial-capture.md) |
| peerjs | — | [initial-capture](reports/peerjs/initial-capture.md) |
| uptime-kuma | `b4ce005` | [initial-capture](reports/uptime-kuma/initial-capture.md) |


## reports 없이 wiki에만 있던 기록 (2026-10-16 삭제)

다시 분석할 때 참고용. 원문은 `git show b52364d:<경로>`. 삭제한 wiki 페이지 전체 목록은 `git ls-tree -r --name-only b52364d wiki/`.

- career-ops: `wiki/projects/career-ops.md`
- deeptutor: `wiki/projects/deeptutor.md`, `wiki/concepts/deeptutor-mode-workflows.md`, `wiki/concepts/stealable-pattern-learning-ai-agent-modules.md`
- graphify: `wiki/projects/graphify.md`, `wiki/concepts/graphify-*.md` (9개)
- ponytail: `wiki/projects/ponytail.md`
- tokscale: `wiki/projects/tokscale.md`, `wiki/concepts/tokscale-*.md` (7개)
