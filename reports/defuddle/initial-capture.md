# kepano/defuddle initial capture

## Snapshot

- GitHub: <https://github.com/kepano/defuddle>
- Local checkout: `repos/defuddle/`
- Artifact root: `artifacts/defuddle/`
- Captured commit: `9db72600a0cfc568eafb31e85ef68ba16add072e` (`main`, `0.18.1-26-g9db7260`)
- DeepWiki baseline: `artifacts/defuddle/deepwiki/`

## Work completed

1. Ran the DeepWiki Markdown extractor against `kepano/defuddle`.
   - Initial extraction found 36 TOC entries and matched 35 pages.
   - The one missing TOC item, `6-platform-specific-extractors`, was repaired from the saved raw Next.js payload because DeepWiki's TOC title is `Platform-Specific Extractors` while the embedded Markdown H1 is `Site-Specific Extractors`.
   - After repair, `artifacts/defuddle/deepwiki/manifest.json` reports `matched_pages_count=36`, `missing_pages_count=0`.
2. Cloned the GitHub repository with `git clone https://github.com/kepano/defuddle.git repos/defuddle`.
3. Captured repository metadata and static language summary.
   - `artifacts/defuddle/repo-metadata.txt`
   - `artifacts/defuddle/github-metadata.json`
   - `artifacts/defuddle/static-analysis/language-summary.txt`

## Source-verified initial facts

- Defuddle is described as a work-in-progress library that extracts main content from web pages by removing clutter such as comments, sidebars, headers, and footers. Evidence: `repos/defuddle/README.md` lines 4-10.
- The README states it accepts URL/HTML input and returns cleaned HTML or Markdown, and that it was created for Obsidian Web Clipper while being designed to run in any environment. Evidence: `repos/defuddle/README.md` lines 8-18.
- The npm package is named `defuddle`, version `0.18.1`, exposes a CLI binary at `dist/cli.js`, and exports browser/default, `./full`, and `./node` entrypoints. Evidence: `repos/defuddle/package.json` lines 1-39.
- Build/test scripts include `build`, `test`, `test:jsdom`, and a local `playground`. Evidence: `repos/defuddle/package.json` lines 40-54.
- Runtime dependency is `commander`; optional dependencies include `linkedom`, `mathml-to-latex`, `temml`, and `turndown`. Evidence: `repos/defuddle/package.json` lines 75-83.
- The core parser class is `Defuddle` in `src/defuddle.ts`; `parse()` runs the main extraction path with retries for low word-count outputs before stripping unsafe elements. Evidence: `repos/defuddle/src/defuddle.ts` lines 36-180 and 212-251.
- Node integration is implemented in `src/node.ts` and accepts a DOM `Document`, HTML string, or JSDOM-like object before calling `parseAsync()` and optional Markdown conversion. Evidence: `repos/defuddle/src/node.ts` lines 5-45.
- CLI source `src/cli.ts` supports file path, URL, or stdin input and options including markdown, json, property, debug, language, and user-agent. Evidence: `repos/defuddle/src/cli.ts` lines 11-20 and 48-83.
- Site/platform-specific extractors are registered in `src/extractor-registry.ts` for targets including X/Twitter, Reddit, YouTube, Hacker News, ChatGPT, Claude, Grok, Gemini, GitHub, LinkedIn, Threads, Bluesky, Medium, C2 wiki, and Substack. Evidence: `repos/defuddle/src/extractor-registry.ts` lines 3-180.
- The web service path under `website/src/convert.ts` uses `parseLinkedomHTML`, `Defuddle`, Markdown conversion, fetch helpers, and route-specific logic for YouTube/Reddit style handling. Evidence: `repos/defuddle/website/src/convert.ts` lines 1-25 and 51-120.
- No `.github/` directory was found in this checkout during initial file search, so GitHub Actions/workflow configuration was not present locally.

## Static summary

`tokei` summary in `artifacts/defuddle/static-analysis/language-summary.txt` reports 487 files and 66,761 total lines in the checkout. The largest source categories are TypeScript, HTML fixtures, Markdown, and JSON.

## DeepWiki extraction caveat

DeepWiki content is saved as external baseline material only. The repaired `6-platform-specific-extractors.md` is still DeepWiki-derived content, not source-verified analysis. Its repair note records the TOC/H1 drift and the payload source used.

## Suggested next steps

1. Compare DeepWiki architecture pages against current source, especially `src/defuddle.ts`, `src/standardize.ts`, `src/removals/*`, `src/elements/*`, and `src/extractor-registry.ts`.
2. Run graphify after adding/validating `.graphifyignore` for generated output, dependency folders, fixtures if needed, and website build artifacts.
3. Produce `reports/defuddle/architecture.md`, `reports/defuddle/code-map.md`, and `reports/defuddle/deepwiki-comparison.md`.
4. Optionally install dependencies and run `npm test` / `npm run build` if execution-level verification is desired.
