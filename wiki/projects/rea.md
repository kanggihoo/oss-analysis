---
title: rea
created: 2026-10-14
updated: 2026-10-14
type: project
tags: [open-source, project, mcp, architecture, evidence]
sources:
  - repos/rea/README.md
  - repos/rea/AGENTS.md
  - repos/rea/docs/architecture.mermaid
  - repos/rea/scripts/rea.mjs
  - repos/rea/src/application/javascript/JavaScriptApplicationService.ts
  - reports/rea/overview.md
confidence: medium
---

# rea

Local-only reverse-engineering toolkit (`rea-agents` 6.4.0, TS) exposed to agents through one MCP server and the same workflows via CLI. Analyzes native binaries (Hopper/Ghidra/IDA bring-your-own), JS/Electron, .NET, APK, websites, pcap, etc., and returns **Evidence** that separates observation / derivation / inference / unknown. (코드 확인: README, AGENTS.md)

## Structure (1차, 일부 미확인)
- `scripts/rea.mjs` dispatches to MCP (`dist/mcp/main.js`) or CLI — 코드 확인.
- Layering rule: domain/contracts → provider adapters → application workflows → CLI/MCP adapters; shared application layer serves both adapters — AGENTS.md 및 architecture.mermaid 기준 (import 단위 검증은 미확인).
- Representative flow `analyze_javascript_application`: server tool → `analyzeJavaScriptApplication` (zod parse → reconstruct → validate → hashed Evidence; cancel keeps partial Evidence) — 코드 확인.

Details: `reports/rea/overview.md` (diagrams in `reports/rea/diagrams/`); see also [[oss-analysis-workspace]], [[codewiki]]. Analyzed SHA `60c0880`.
