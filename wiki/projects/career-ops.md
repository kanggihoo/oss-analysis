---
title: Career-Ops
created: 2026-06-14
updated: 2026-06-14
type: project
tags: [open-source, project, architecture, agent-framework, cli, workflow, onboarding, deepwiki, evidence]
sources:
  - artifacts/career-ops/deepwiki/pages-md/1-career-ops-overview.md
  - artifacts/career-ops/deepwiki/pages-md/1.1-getting-started-and-setup.md
  - artifacts/career-ops/deepwiki/pages-md/1.2-configuration-reference.md
  - artifacts/career-ops/deepwiki/pages-md/1.3-examples-and-sample-files.md
  - repos/career-ops/README.md
  - repos/career-ops/AGENTS.md
  - repos/career-ops/DATA_CONTRACT.md
  - repos/career-ops/package.json
  - repos/career-ops/doctor.mjs
  - repos/career-ops/scaffolder/bin/cli.mjs
  - repos/career-ops/config/profile.example.yml
  - repos/career-ops/templates/portals.example.yml
  - repos/career-ops/modes/_shared.md
  - repos/career-ops/modes/auto-pipeline.md
  - repos/career-ops/modes/oferta.md
  - repos/career-ops/scan.mjs
  - repos/career-ops/generate-pdf.mjs
  - repos/career-ops/generate-latex.mjs
  - repos/career-ops/merge-tracker.mjs
  - repos/career-ops/dashboard/main.go
confidence: high
---

# Career-Ops

Career-Ops는 Claude Code, Gemini CLI, Codex, Qwen, OpenCode, Copilot 같은 AI coding CLI를 구직 커맨드 센터로 쓰게 만드는 로컬 우선 job-search automation 프로젝트다. DeepWiki의 overview/setup/config/examples 페이지를 baseline으로 삼았고, 아래 내용은 현재 checkout `repos/career-ops`에서 source path로 검증한 구조만 정리한다. 분석 원칙은 [[evidence-backed-analysis]]와 [[deepwiki-first-baseline]]의 경계를 따른다.

검증 기준 checkout: `repos/career-ops` at `57b34c07e01cd106528936398507e1b4552ca295`.

## What it optimizes for

- 대량 지원 자동 제출이 아니라, JD를 읽고 A-F 점수와 별도 Block G legitimacy를 붙여 “지원할 가치가 있는 공고”를 고르는 필터다. README도 4.0 미만에는 지원을 권하지 않는다고 명시한다. (`repos/career-ops/README.md:97-113`)
- 산출물은 평가 보고서, 맞춤형 CV PDF/LaTeX, tracker entry, cover letter draft, interview story bank로 이어진다. (`repos/career-ops/README.md:115-129`, `repos/career-ops/modes/auto-pipeline.md:31-87`)
- 사용자는 최종 제출을 직접 결정한다. 프로젝트는 AI가 지원서를 자동 제출하지 않는 human-in-the-loop 구조를 안전 경계로 둔다. (`repos/career-ops/README.md:128`, `repos/career-ops/modes/_shared.md:91-100`)

## Source-verified architecture map

```text
AI coding CLI / slash mode
→ modes/*.md prompt logic + user profile/context
→ JD extraction and liveness gate
→ A-F fit evaluation + Block G posting legitimacy
→ report, CV/cover PDF, tracker TSV/merge
→ data/applications.md + dashboard TUI + interview-prep story bank
```

| Area | Primary files | Verified role |
|---|---|---|
| Agent instruction layer | `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, `modes/*.md` | CLI-agnostic operating rules, onboarding, mode routing, scoring prompts. `AGENTS.md` is canonical for data contract and first-run behavior. |
| Personal context | `cv.md`, `config/profile.yml`, `modes/_profile.md`, `article-digest.md`, `writing-samples/` | Candidate identity, target roles, proof points, voice calibration. These are user-layer files, not system-update targets. |
| Evaluation pipeline | `modes/_shared.md`, `modes/oferta.md`, `modes/auto-pipeline.md` | Archetype detection, A-F scoring, liveness gate, Block G legitimacy, report save, PDF generation, tracker update. |
| Discovery scanner | `templates/portals.example.yml`, `portals.yml`, `scan.mjs`, `providers/*.mjs` | Portal config, title/location/salary filters, provider loading, URL dedup, `data/pipeline.md` writing. |
| Artifact generation | `modes/pdf.md`, `modes/latex.md`, `generate-pdf.mjs`, `generate-latex.mjs`, `templates/cv-template.*` | HTML→PDF via Playwright or LaTeX validation/compile via `tectonic`/`pdflatex`, selected by `cv.output_format`. |
| Tracker/data integrity | `data/applications.md`, `batch/tracker-additions/`, `merge-tracker.mjs`, `dedup-tracker.mjs`, `normalize-statuses.mjs` | Flat-file tracker is the work-state source. Batch additions are TSV; merge handles dedup/status/link normalization. |
| Dashboard | `dashboard/main.go`, `dashboard/internal/*` | Bubble Tea Go TUI reads application data, computes metrics, supports pipeline/report/progress views and inline status changes. |

## Initial setup paths

### Recommended one-command install

```bash
npx @santifer/career-ops init
cd career-ops
claude   # or gemini / codex / qwen / opencode / copilot
```

The npm scaffolder package exposes `career-ops` as `bin/cli.mjs`, requires Node `>=18`, clones `https://github.com/santifer/career-ops.git` at the latest release tag when available, runs `npm install`, and deliberately does **not** create `cv.md`, `config/profile.yml`, or `portals.yml`; their absence triggers conversational onboarding on first agent launch. (`repos/career-ops/scaffolder/package.json:1-15`, `repos/career-ops/scaffolder/bin/cli.mjs:1-8`, `repos/career-ops/scaffolder/bin/cli.mjs:102-143`)

### Manual setup

```bash
git clone https://github.com/santifer/career-ops.git
cd career-ops
npm install
npx playwright install chromium   # PDF/browser-driven flows
npm run doctor
cp config/profile.example.yml config/profile.yml
cp templates/portals.example.yml portals.yml
# create cv.md in the project root, then open the AI CLI in this directory
```

`package.json` verifies the current Node-side command surface: `doctor`, `verify`, `normalize`, `dedup`, `merge`, `pdf`, `sync-check`, `scan`, `tracker`, `patterns`, and `gemini:eval` are npm scripts over local `.mjs` utilities. Runtime dependencies are `@google/generative-ai`, `dotenv`, `js-yaml`, and `playwright`. (`repos/career-ops/package.json:6-24`, `repos/career-ops/package.json:43-48`)

## First-run onboarding contract

`doctor.mjs --json` is the deterministic cold-start gate. In the checked-out analysis copy it returned:

```json
{"onboardingNeeded":true,"missing":["cv.md","config/profile.yml","modes/_profile.md","portals.yml"],"warnings":["Playwright MCP tools not detected"]}
```

The source-defined prerequisite list is exactly four user files: `cv.md`, `config/profile.yml`, `modes/_profile.md`, and `portals.yml`. Human-readable `npm run doctor` additionally checks Node.js `>=18`, `node_modules`, Playwright Chromium, Playwright MCP warning state, fonts, and auto-creates `data/`, `output/`, and `reports/` if needed. (`repos/career-ops/doctor.mjs:26-68`, `repos/career-ops/doctor.mjs:111-144`, `repos/career-ops/doctor.mjs:185-216`, `repos/career-ops/doctor.mjs:253-267`)

Onboarding order in `AGENTS.md` is: create/convert `cv.md`; copy and fill `config/profile.yml`; copy/customize `portals.yml`; create `data/applications.md` if missing; then collect deeper preference/proof-point context. (`repos/career-ops/AGENTS.md:72-152`)

## Configuration model

Career-Ops is intentionally split into a user layer and a system layer.

- User layer: `cv.md`, `config/profile.yml`, `modes/_profile.md`, `article-digest.md`, `interview-prep/story-bank.md`, `portals.yml`, `data/*`, `reports/*`, `output/*`, `jds/*`, and user writing samples. Updates must not overwrite these. (`repos/career-ops/DATA_CONTRACT.md:5-25`)
- System layer: modes, CLI wrapper instructions, `.mjs` utilities, dashboard, templates, fonts, docs, version files, and system-owned writing-sample docs. These can be replaced by upstream updates. (`repos/career-ops/DATA_CONTRACT.md:27-68`)
- Practical correction to a casual README phrasing: README’s project tree says `_shared.md` is “customize this”, but the stricter current rule is in `AGENTS.md`/`DATA_CONTRACT.md`: user-specific archetypes, narrative, negotiation, location policy, and compensation targets belong in `modes/_profile.md` or `config/profile.yml`, not `modes/_shared.md`. (`repos/career-ops/README.md:313-346`, `repos/career-ops/AGENTS.md:11-23`)

`config/profile.example.yml` shows the core candidate schema: `candidate`, `target_roles`, `narrative`, `compensation`, `location`, `cv.output_format`, cover-letter settings, and optional `auto_pdf_score_threshold`. (`repos/career-ops/config/profile.example.yml:5-134`)

`templates/portals.example.yml` documents scanner customization: title positive/negative keywords, optional location and salary filters, tracked companies, and the preference for branded career URLs over raw ATS URLs. `scan.mjs` implements this with provider loading, `buildTitleFilter()`, `buildLocationFilter()`, `buildSalaryFilter()`, scan-history dedup, and pipeline writing. (`repos/career-ops/templates/portals.example.yml:1-120`, `repos/career-ops/scan.mjs:44-53`, `repos/career-ops/scan.mjs:55-90`, `repos/career-ops/scan.mjs:122-230`)

## Data and output lifecycle

1. Input enters via pasted JD/URL, `/career-ops scan`, or queued `data/pipeline.md`.
2. URL inputs go through a liveness gate before evaluation; dead/expired postings stop before Block A. (`repos/career-ops/modes/auto-pipeline.md:5-29`, `repos/career-ops/modes/oferta.md:5-17`)
3. Evaluation produces A-F fit blocks plus Block G legitimacy, with CV line matching, comp research, customization, interview STAR+R plan, and ethical legitimacy framing. (`repos/career-ops/modes/oferta.md:18-155`)
4. Reports are saved under `reports/{###}-{company-slug}-{YYYY-MM-DD}.md`; PDF generation reads `cv.output_format` and routes to HTML/PDF or LaTeX. (`repos/career-ops/modes/auto-pipeline.md:35-46`)
5. Tracker updates should flow through TSV additions and merge logic rather than ad-hoc direct editing. `merge-tracker.mjs` supports 8/9-column TSV and markdown-table rows, validates statuses, dedups by company/role/report number, normalizes report links, and uses a canonical tracker lock path. (`repos/career-ops/modes/_shared.md:115-116`, `repos/career-ops/merge-tracker.mjs:3-15`, `repos/career-ops/merge-tracker.mjs:26-69`)
6. The dashboard reads tracker data through Go models and supports reload, report preview, progress metrics, and status updates. (`repos/career-ops/dashboard/main.go:26-90`)

## Example mental model

The examples are not just sample files; they define the expected data shapes. `examples/cv-example.md` shows the Markdown CV sections that evaluation modes cite by line, while `examples/sample-report.md` shows the A-F report skeleton and keyword extraction. DeepWiki’s examples page correctly treats these as structural blueprints, but production personalization should be created in the user layer instead of copying example identities into live config. (`repos/career-ops/examples/cv-example.md:1-48`, `repos/career-ops/examples/sample-report.md:1-75`, `repos/career-ops/DATA_CONTRACT.md:5-25`)

## Related

- [[workspace-boundaries]] — why this wiki cites `repos/` source as authority and `artifacts/` DeepWiki pages as baselines.
- [[evidence-backed-analysis]] — verification policy used for this source-checked project note.
- [[deepwiki-first-baseline]] — how DeepWiki pages are ingested without treating them as final authority.
