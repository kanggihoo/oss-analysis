# career-ops initial capture

Date: 2026-06-13 UTC
Repo: `https://github.com/santifer/career-ops`
Local checkout: `/Users/kkh/Desktop/oss-analysis/repos/career-ops`
Artifacts: `/Users/kkh/Desktop/oss-analysis/artifacts/career-ops`

## Completed capture work

- DeepWiki baseline extracted with `deepwiki_extract.py` into `artifacts/career-ops/deepwiki/`.
  - Manifest: `artifacts/career-ops/deepwiki/manifest.json`
  - TOC: `artifacts/career-ops/deepwiki/toc.md`
  - English Markdown pages: `artifacts/career-ops/deepwiki/pages-md/`
  - Per-page metadata: `artifacts/career-ops/deepwiki/pages-meta/`
- GitHub repo cloned into `repos/career-ops`.
- Git checkout metadata recorded in `artifacts/career-ops/repo-metadata.txt`.
- GitHub metadata captured from unauthenticated GitHub REST API in `artifacts/career-ops/github-metadata.json`.
- GitHub language bytes captured in `artifacts/career-ops/static-analysis/github-languages.json`.
- Local static language summary captured with `tokei` in:
  - `artifacts/career-ops/static-analysis/tokei.json`
  - `artifacts/career-ops/static-analysis/language-summary.md`

## DeepWiki extraction verification

Source: `artifacts/career-ops/deepwiki/manifest.json`

- DeepWiki URL: `https://deepwiki.com/santifer/career-ops`
- Fetch status: HTTP 200
- TOC count: 35
- Markdown chunks: 35
- Matched pages: 35
- Missing pages: 0

Filesystem verification via artifact directory listing:

- `artifacts/career-ops/deepwiki/pages-md/*.md`: 35 files
- `artifacts/career-ops/deepwiki/pages-meta/*.json`: 35 files

DeepWiki remains an external baseline / second opinion, not source-verified truth.

## Git checkout snapshot

Source: `artifacts/career-ops/repo-metadata.txt`

- Branch: `main`
- HEAD: `57b34c07e01cd106528936398507e1b4552ca295`
- Describe: `career-ops-v1.10.0-18-g57b34c0`
- Remote: `https://github.com/santifer/career-ops.git`
- Working tree status at capture: `0 changed files`
- Latest commit: `57b34c07e01cd106528936398507e1b4552ca295 Narash25 2026-06-13T02:56:42+08:00 feat(tracker): map tracker columns by header name (#954)`

## GitHub metadata snapshot

Source: `artifacts/career-ops/github-metadata.json`

- Full name: `santifer/career-ops`
- Description: `AI-powered job search system built on Claude Code. 14 skill modes, Go dashboard, PDF generation, batch processing.`
- URL: `https://github.com/santifer/career-ops`
- Default branch: `main`
- License: MIT
- Stars at capture: 53,509
- Forks at capture: 10,658
- Created: `2026-04-04T18:21:18Z`
- Pushed: `2026-06-12T18:57:27Z`
- Updated: `2026-06-13T20:55:43Z`

Note: `gh repo view` was unavailable because the Hermes shell was not authenticated with GitHub CLI, so metadata was captured with unauthenticated GitHub REST API instead.

## Local static summary

Source: `artifacts/career-ops/static-analysis/language-summary.md`

Top local code languages by `tokei` code lines:

| Language | Code | Comments | Blanks |
|---|---:|---:|---:|
| JavaScript | 9,103 | 1,956 | 1,302 |
| Go | 3,785 | 302 | 561 |
| YAML | 1,115 | 284 | 225 |
| Shell | 585 | 60 | 85 |
| JSON | 140 | 0 | 0 |
| Total | 15,941 | 13,912 | 6,445 |

GitHub language API byte summary is stored at `artifacts/career-ops/static-analysis/github-languages.json` and shows JavaScript, Go, Shell, HTML, TeX, Dockerfile, and Nix.

## Source-verified initial facts

These are verified against the local checkout, not just DeepWiki.

1. Career-Ops describes itself as a job-search command center that evaluates offers, generates tailored PDFs, scans portals, processes batches, and tracks everything in one source of truth.
   - Evidence: `repos/career-ops/README.md:97-109`

2. The Node package is named `career-ops`, version `1.10.0`, and is marked private. Its scripts expose doctor, verify, normalize/dedup/merge tracker operations, PDF generation, update, liveness, scan, tracker, patterns, and Gemini evaluation commands.
   - Evidence: `repos/career-ops/package.json:1-24`

3. Runtime Node dependencies include `@google/generative-ai`, `dotenv`, `js-yaml`, and `playwright`.
   - Evidence: `repos/career-ops/package.json:43-48`

4. Portal scanning is implemented as a zero-token, provider-plugin scanner. Providers are loaded from `providers/*.mjs`, underscore-prefixed helper modules are skipped, and provider resolution favors explicit `provider:`, then local parser, then provider auto-detection.
   - Evidence: `repos/career-ops/scan.mjs:3-21`, `repos/career-ops/scan.mjs:55-90`

5. PDF generation uses Playwright Chromium to render HTML to PDF and includes ATS-oriented Unicode normalization logic.
   - Evidence: `repos/career-ops/generate-pdf.mjs:3-13`, `repos/career-ops/generate-pdf.mjs:24-88`

6. The dashboard is a Go Bubble Tea TUI with pipeline, report viewer, and progress views; it loads application data and computes metrics from the data layer.
   - Evidence: `repos/career-ops/dashboard/main.go:10-15`, `repos/career-ops/dashboard/main.go:18-40`

7. The Go dashboard module is `github.com/santifer/career-ops/dashboard`, targets Go `1.24.2`, and depends directly on Bubble Tea, Lip Gloss, and Charmbracelet ANSI helpers.
   - Evidence: `repos/career-ops/dashboard/go.mod:1-9`

8. CI pull-request tests run on Ubuntu with Node `24`, Go `1.26`, `npm install`, and `node test-all.mjs --quick`.
   - Evidence: `repos/career-ops/.github/workflows/test.yml:1-20`

9. The architecture document frames the system around an AI coding CLI agent reading `AGENTS.md` and `modes/*.md`, with single evaluation, portal scan, and batch-processing paths converging into reports, PDF generation, tracker TSV, and `data/applications.md`.
   - Evidence: `repos/career-ops/docs/ARCHITECTURE.md:3-35`, `repos/career-ops/docs/ARCHITECTURE.md:37-53`

## DeepWiki baseline topics captured but not yet source-verified

The extracted DeepWiki TOC covers these baseline areas:

- Career-Ops overview, setup, configuration, examples
- AI agent modes, including evaluation, discovery/pipeline, application/outreach, career development, and i18n modes
- PDF and LaTeX generation engine
- Batch processing system
- Application tracker and data layer
- Go dashboard TUI
- Interview preparation and story bank
- Multi-agent/tool integration, agent routing, Gemini evaluator, and update/version management
- Infrastructure, CI/CD, release engineering, security, contributing, and glossary

These pages are stored under `artifacts/career-ops/deepwiki/pages-md/` and should be checked against `repos/career-ops/` before being used in final reports or wiki pages.

## Not done in this initial capture

- Did not run the full test suite locally.
- Did not run graphify or Understand-Anything.
- Did not update `wiki/` because the user request was capture/extraction plus clone, not a source-verified wiki synthesis.

## Suggested next steps

1. Run a standard source-verified architecture pass using the DeepWiki pages as hypotheses.
2. Run local analyzers, especially graphify, into `artifacts/career-ops/graphify/`.
3. Produce `reports/career-ops/architecture.md` and `reports/career-ops/deepwiki-comparison.md`.
4. If desired, reflect durable conclusions into `wiki/projects/career-ops.md` after source verification.
