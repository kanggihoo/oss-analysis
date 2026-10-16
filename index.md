# Index

> Last updated: 2026-10-16
> 레포에 관한 분석은 모두 `reports/<repo>/`에 있다. 형식은 [SCHEMA.md](SCHEMA.md), 절차는 [OSS_ANALYSIS_WORKFLOW.md](OSS_ANALYSIS_WORKFLOW.md).

## 분석한 레포

| 레포 | 기준 SHA | 입구 | 기능 스펙 |
|---|---|---|---|
| claude-code-history-viewer | `9d86b46` | [overview](reports/claude-code-history-viewer/overview.md) | — |
| claude-devtools | `1486f20` | [overview](reports/claude-devtools/overview.md) | [claude-code-session-log-reading](reports/claude-devtools/capabilities/claude-code-session-log-reading.md) (draft) |
| cc-switch | `d35726e` | [overview](reports/cc-switch/overview.md) | — |
| codeburn | `9a40cc6` | [overview](reports/codeburn/overview.md) | — |
| codenotch | `414ceaf` | [overview](reports/codenotch/overview.md) | — |
| CodeWiki | `3e3d848` | [overview](reports/CodeWiki/overview.md) | — |
| e2e | `dbdec70` | [overview](reports/e2e/overview.md) | — |
| folo | `44f0e5d` | [overview](reports/folo/overview.md) | — |
| Graft | `f9e6539` | [overview](reports/Graft/overview.md) | — |
| jev-ultrafast | `1231850` | [overview](reports/jev-ultrafast/overview.md) | — |
| mitmproxy | `7735597` | [overview](reports/mitmproxy/overview.md) | — |
| pi | `4259686`, `ai`·`agent` 패키지는 `3874b3e` | [overview](reports/pi/overview.md) | — |
| rea | `60c0880` | [overview](reports/rea/overview.md) | — |
| rsshub | `0a4ecdb` | [overview](reports/rsshub/overview.md) | — |
| searxng | `0ce72dd` | [overview](reports/searxng/overview.md) | — |
| skills-manager | `e6dcedf` | [overview](reports/skills-manager/overview.md) | — |
| teamai-cli | `7ba8bcc` | [overview](reports/teamai-cli/overview.md) | — |
| Understand-Anything | `b05cc3b` | [overview](reports/Understand-Anything/overview.md) | — |

## 첫 수집만 한 레포 (overview 없음)

| 레포 | 기준 SHA | 입구 |
|---|---|---|
| Agent-Reach | — | [initial-capture](reports/Agent-Reach/initial-capture.md) |
| agent-browser | — | [initial-capture](reports/agent-browser/initial-capture.md) |
| defuddle | — | [initial-capture](reports/defuddle/initial-capture.md) |
| insane-search | — | [initial-capture](reports/insane-search/initial-capture.md) |
| knowledge-catalog | — | [initial-capture](reports/knowledge-catalog/initial-capture.md) |
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
